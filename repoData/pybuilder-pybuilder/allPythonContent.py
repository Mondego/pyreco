__FILENAME__ = pdoc
import os
import subprocess

from pybuilder.core import task
from pybuilder.utils import assert_can_execute


@task
def pdoc_generate(project, logger):
    assert_can_execute(command_and_arguments=["pdoc", "--version"],
                       prerequisite="pdoc",
                       caller=pdoc_generate.__name__)

    logger.info("Generating pdoc documentation")

    command_and_arguments = ["pdoc", "--html", "pybuilder", "--all-submodules", "--overwrite", "--html-dir", "api-doc"]
    source_directory = project.get_property("dir_source_main_python")
    environment = {"PYTHONPATH": source_directory,
                   "PATH": os.environ["PATH"]}

    subprocess.check_call(command_and_arguments, shell=False, env=environment)

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python

#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import sys

sys.path.insert(0, 'src/main/python')  # This is only necessary in PyBuilder sources for bootstrap

from pybuilder import bootstrap
from pybuilder.core import Author, init, use_bldsup, use_plugin

bootstrap()

use_plugin("pypi:pybuilder_external_plugin_demo")
use_plugin("python.core")
use_plugin("python.pytddmon")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

use_plugin("copy_resources")
use_plugin("filter_resources")
use_plugin("source_distribution")

use_plugin("python.coverage")
use_plugin("python.unittest")
use_plugin("python.integrationtest")
use_plugin("python.flake8")
use_plugin("python.frosted")

if not sys.version_info[0:2] == (3, 2):
    use_plugin("python.cram")

use_plugin("python.pydev")
use_plugin("python.pycharm")
use_plugin("python.pytddmon")

use_bldsup()
use_plugin("pdoc")

summary = "An extensible, easy to use continuous build tool for Python"
description = """PyBuilder is a continuous build tool for multiple languages.

PyBuilder primarily targets Python projects but due to its extensible
nature it can be used for other languages as well.

PyBuilder features a powerful yet easy to use plugin mechanism which
allows programmers to extend the tool in an unlimited way.
"""

authors = [Author("Alexander Metzner", "alexander.metzner@gmail.com"),
           Author("Maximilien Riehl", "max@riehl.io"),
           Author("Michael Gruber", "aelgru@gmail.com"),
           Author("Udo Juettner", "udo.juettner@gmail.com")]
url = "http://pybuilder.github.io"
license = "Apache License"
version = "0.10.21"

default_task = ["analyze", "publish"]


@init
def initialize(project):
    project.build_depends_on("mockito-without-hardcoded-distribute-version")
    project.build_depends_on("mock")
    project.build_depends_on("pyfix")  # required test framework
    project.build_depends_on("pyassert")
    project.build_depends_on("wheel")
    project.build_depends_on("pdoc")
    project.build_depends_on("pygments")

    project.set_property("verbose", True)

    project.set_property("coverage_break_build", False)
    project.get_property("coverage_exceptions").append("pybuilder.cli")
    project.get_property("coverage_exceptions").append("pybuilder.plugins.core_plugin")

    project.set_property("copy_resources_target", "$dir_dist")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.get_property("filter_resources_glob").append("**/pybuilder/__init__.py")

    project.set_property('flake8_break_build', True)
    project.set_property('flake8_include_test_sources', True)
    project.set_property('flake8_include_scripts', True)

    project.set_property('flake8_max_line_length', 130)

    project.set_property('frosted_include_test_sources', True)
    project.set_property('frosted_include_scripts', True)

    project.get_property("source_dist_ignore_patterns").append(".project")
    project.get_property("source_dist_ignore_patterns").append(".pydevproject")
    project.get_property("source_dist_ignore_patterns").append(".settings")

    # enable this to build a bdist on vagrant
    # project.set_property("distutils_issue8876_workaround_enabled", True)
    project.get_property("distutils_commands").append("bdist_wheel")
    project.set_property("distutils_classifiers", [
                         'Programming Language :: Python',
                         'Programming Language :: Python :: Implementation :: CPython',
                         'Programming Language :: Python :: Implementation :: PyPy',
                         'Programming Language :: Python :: 2.6',
                         'Programming Language :: Python :: 2.7',
                         'Programming Language :: Python :: 3',
                         'Programming Language :: Python :: 3.2',
                         'Programming Language :: Python :: 3.3',
                         'Programming Language :: Python :: 3.4',
                         'Development Status :: 4 - Beta',
                         'Environment :: Console',
                         'Intended Audience :: Developers',
                         'License :: OSI Approved :: Apache Software License',
                         'Topic :: Software Development :: Build Tools',
                         'Topic :: Software Development :: Quality Assurance',
                         'Topic :: Software Development :: Testing'])

########NEW FILE########
__FILENAME__ = build
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pybuilder.core import task


@task
def say_hello(logger):
    logger.info("Hello, pybuilder")

########NEW FILE########
__FILENAME__ = build
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pybuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.pyfix_unittest")
use_plugin("python.coverage")
use_plugin("python.distutils")

default_task = "publish"

########NEW FILE########
__FILENAME__ = helloworld
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


def helloworld(out):
    out.write("Hello world of Python\n")

########NEW FILE########
__FILENAME__ = helloworld_pyfix_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from mockito import mock, verify
from pyfix import test

from helloworld import helloworld


@test
def should_issue_hello_world_message():
    out = mock()

    helloworld(out)

    verify(out).write("Hello world of Python\n")

########NEW FILE########
__FILENAME__ = build
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")


name = "pybuilder-external-plugin-demo"
version = "1.0"
default_task = "publish"


@init
def set_properties(project):
    project.set_property("coverage_break_build", False)

########NEW FILE########
__FILENAME__ = build
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pybuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.distutils")

default_task = "publish"

########NEW FILE########
__FILENAME__ = helloworld
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


def helloworld(out):
    out.write("Hello world of Python\n")

########NEW FILE########
__FILENAME__ = helloworld_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from mockito import mock, verify

from helloworld import helloworld


class HelloWorldTest(unittest.TestCase):
    def test_should_issue_hello_world_message(self):
        out = mock()

        helloworld(out)

        verify(out).write("Hello world of Python\n")

########NEW FILE########
__FILENAME__ = integrationtest_support
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import shutil
import stat
import tempfile
import unittest

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

from pybuilder.core import Logger
from pybuilder.cli import StdOutLogger
from pybuilder.execution import ExecutionManager
from pybuilder.reactor import Reactor


class IntegrationTestSupport(unittest.TestCase):
    def setUp(self):
        self.tmp_directory = tempfile.mkdtemp(prefix="IntegrationTestSupport")

    def tearDown(self):
        if self.tmp_directory and os.path.exists(self.tmp_directory):
            shutil.rmtree(self.tmp_directory)

    def full_path(self, name):
        parts = [self.tmp_directory] + name.split(os.sep)
        return os.path.join(*parts)

    def create_directory(self, name):
        os.makedirs(self.full_path(name))

    def write_file(self, name, *content):
        with open(self.full_path(name), "w") as file:
            file.writelines(content)

    def write_build_file(self, content):
        self.write_file("build.py", content)

    def assert_directory_exists(self, name):
        full_path = self.full_path(name)
        self.assertTrue(os.path.exists(full_path), msg="Directory does not exist: %s" % full_path)
        self.assertTrue(os.path.isdir(full_path), msg="Not a directory: %s" % full_path)

    def assert_file_does_not_exist(self, name):
        full_path = self.full_path(name)
        self.assertFalse(os.path.exists(full_path), msg="File should NOT exist: %s" % full_path)

    def assert_file_exists(self, name):
        full_path = self.full_path(name)
        self.assertTrue(os.path.exists(full_path), msg="File does not exist: %s" % full_path)
        self.assertTrue(os.path.isfile(full_path), msg="Not a file: %s" % full_path)

    def assert_file_permissions(self, expected_permissions, name):
        full_path = self.full_path(name)
        actual_file_permissions = stat.S_IMODE(os.stat(full_path).st_mode)
        self.assertEqual(oct(expected_permissions), oct(actual_file_permissions))

    def assert_file_empty(self, name):
        self.assert_file_exists(name)
        full_path = self.full_path(name)
        self.assertEquals(0, os.path.getsize(full_path), msg="File %s is not empty." % full_path)

    def assert_file_contains(self, name, expected_content_part):
        full_path = self.full_path(name)
        with open(full_path) as file:
            content = file.read()
            self.assertTrue(expected_content_part in content)

    def assert_file_content(self, name, expected_file_content):
        if expected_file_content == "":
            self.assert_file_empty(name)

        count_of_new_lines = expected_file_content.count("\n")

        if count_of_new_lines == 0:
            expected_lines = 1
        else:
            expected_lines = count_of_new_lines

        expected_content = StringIO(expected_file_content)
        actual_line_number = 0

        full_path = self.full_path(name)
        with open(full_path) as file:
            for actual_line in file:
                actual_line_number += 1
                actual_line_showing_escaped_new_line = actual_line.replace("\n", "\\n")

                expected_line = expected_content.readline()
                expected_line_showing_escaped_new_line = expected_line.replace("\n", "\\n")

                message = 'line {0} is not as expected.\n   expected: "{1}"\n    but got: "{2}"'.format(
                    actual_line_number, expected_line_showing_escaped_new_line, actual_line_showing_escaped_new_line)
                self.assertEquals(expected_line, actual_line, message)

        self.assertEqual(expected_lines, actual_line_number)

    def prepare_reactor(self):
        logger = StdOutLogger(threshold=Logger.DEBUG)
        execution_manager = ExecutionManager(logger)
        reactor = Reactor(logger, execution_manager)
        reactor.prepare_build(project_directory=self.tmp_directory)
        return reactor

########NEW FILE########
__FILENAME__ = should_build_pyfix_project_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("python.pyfix_unittest")

name = "integration-test"
default_task = "run_unit_tests"
""")
        self.create_directory("src/unittest/python")
        self.write_file("src/unittest/python/spam_pyfix_tests.py", """
import time

from pyfix import test

@test
def should_run_pyfix_test ():
    time.sleep(.1)
""")
        self.write_file("src/unittest/python/cheese_tests.py", """
import time

from pyfix import test

@test
def should_skip_test_sans_pyfix_test ():
    raise Exception("This test should not have run!")
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"failures": []')
        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"tests-run": 1')

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_build_simple_python_project_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("python.core")

name = "integration-test"
default_task = "publish"
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/__init__.py", "")
        self.write_file("src/main/python/spam/eggs.py", """
def spam ():
    pass
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists(
            "target/dist/integration-test-1.0-SNAPSHOT")
        self.assert_directory_exists(
            "target/dist/integration-test-1.0-SNAPSHOT/spam")
        self.assert_file_empty(
            "target/dist/integration-test-1.0-SNAPSHOT/spam/__init__.py")
        self.assert_file_content("target/dist/integration-test-1.0-SNAPSHOT/spam/eggs.py", """
def spam ():
    pass
""")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_filter_resources_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("copy_resources")
use_plugin("filter_resources")

@init
def init (project):
    project.get_property("copy_resources_glob").append("*")
    project.get_property("filter_resources_glob").append("spam")
        """)

        self.write_file("spam", "${version}")
        self.write_file("eggs", "${version}")

        reactor = self.prepare_reactor()
        reactor.build("package")

        self.assert_file_content("target/spam", "1.0-SNAPSHOT")
        self.assert_file_content("target/eggs", "${version}")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_invoke_initializer_when_environments_match_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import init, task

name = "integration-test"
default_task = "any_task"

@init(environments="test_environment")
def initialize (project):
    setattr(project, "INITIALIZER_EXECUTED", True)

@task
def any_task (project):
    if not hasattr(project, "INITIALIZER_EXECUTED"):
        raise Exception("Initializer has not been executed")

""")

        reactor = self.prepare_reactor()
        reactor.build(environments=["test_environment"])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_list_multiple_tasks_for_project_using_core_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin

use_plugin("core")
        """)
        reactor = self.prepare_reactor()

        tasks = reactor.get_tasks()

        self.assertEquals(8, len(tasks))

        task_names = list(map(lambda task: task.name, tasks))

        self.assertTrue("clean" in task_names)
        self.assertTrue("publish" in task_names)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_list_multiple_tasks_for_simple_project_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import task

@task
def another_task (): pass

@task("a_task_with_overridden_name")
def any_method_name (): pass

@task
def my_task (): pass
        """)
        reactor = self.prepare_reactor()

        actual_tasks = reactor.get_tasks()
        actual_task_names = [task.name for task in actual_tasks]

        self.assertEqual(
            ["a_task_with_overridden_name", "another_task", "my_task"], sorted(actual_task_names))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_list_single_task_for_simple_project_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import task

@task
def my_task (): pass
        """)
        reactor = self.prepare_reactor()

        tasks = reactor.get_tasks()
        self.assertEquals(1, len(tasks))
        self.assertEquals("my_task", tasks[0].name)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_not_invoke_initializer_when_environment_do_not_match_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import init, task

name = "integration-test"
default_task = "any_task"

@init(environments="test_environment")
def initialize ():
    raise Exception("Invoked although environment not defined")

@task
def any_task (): pass

""")

        reactor = self.prepare_reactor()
        reactor.build()

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_raise_exception_when_no_default_goal_is_given_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport

from pybuilder.errors import PyBuilderException


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import task

@task
def spam (): pass
        """)
        reactor = self.prepare_reactor()

        self.assertRaises(PyBuilderException, reactor.build)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_raise_exception_when_project_is_not_valid_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport

from pybuilder.errors import ProjectValidationFailedException


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import init

@init
def init (project):
    project.depends_on("spam")
    project.build_depends_on("spam")
        """)
        reactor = self.prepare_reactor()

        self.assertRaises(
            ProjectValidationFailedException, reactor.build, ["clean"])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_set_pyfix_glob_from_suffix_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import init
from pybuilder.core import task
from pybuilder.core import use_plugin

use_plugin("python.pyfix_unittest")

name = "integration-test"
default_task = ["run_unit_tests", "test_override"]

@task
def test_override(project):
    file_suffix = project.get_property("pyfix_unittest_file_suffix")
    module_glob = project.get_property("pyfix_unittest_module_glob")
    if module_glob != "*{0}".format(file_suffix)[:-3]:
        raise Exception("pyfix_unittest_file_suffix failed to override pyfix_unittest_module_glob")

@init
def init_should_set_pyfix_glob_from_suffix(project):
    project.set_property("pyfix_unittest_module_glob", "suffix will overwrite")
    project.set_property("pyfix_unittest_file_suffix", "_pyfix_tests.py")
""")
        self.create_directory("src/unittest/python")
        self.write_file("src/unittest/python/spam_pyfix_tests.py", """
from pyfix import test

@test
def should_run_pyfix_test ():
    return
""")
        self.write_file("src/unittest/python/cheese_tests.py", """
raise Exception("This test should not have run!")
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"failures": []')
        self.assert_file_contains(
            "target/reports/pyfix_unittest.json", '"tests-run": 1')

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = should_write_manifest_file_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from integrationtest_support import IntegrationTestSupport


class Test (IntegrationTestSupport):

    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin('python.core')
use_plugin('python.distutils')

name = 'integration-test'
default_task = 'publish'

@init
def init (project):
    project.include_file('spam', 'eggs')
    project.install_file('spam_dir', 'more_spam')
    project.install_file('eggs_dir', 'more_eggs')
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/eggs", "")
        self.write_file("src/main/python/more_spam", "")
        self.write_file("src/main/python/more_eggs", "")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists(
            "target/dist/integration-test-1.0-SNAPSHOT")
        self.assert_directory_exists(
            "target/dist/integration-test-1.0-SNAPSHOT/spam")
        self.assert_file_empty(
            "target/dist/integration-test-1.0-SNAPSHOT/spam/eggs")
        self.assert_file_empty(
            "target/dist/integration-test-1.0-SNAPSHOT/more_spam")
        self.assert_file_empty(
            "target/dist/integration-test-1.0-SNAPSHOT/more_eggs")

        manifest_in = "target/dist/integration-test-1.0-SNAPSHOT/MANIFEST.in"

        self.assert_file_exists(manifest_in)
        self.assert_file_permissions(0o664, manifest_in)
        self.assert_file_content(manifest_in, """include spam/eggs
include more_spam
include more_eggs
""")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = ci_server_interaction
from pybuilder.terminal import print_text


def test_proxy_for(project):
    if project.get_property('teamcity_output') and not project.get_property('__running_coverage'):
        return TeamCityTestProxy()
    else:
        return TestProxy()


def flush_text_line(text_line):
    print_text(text_line + '\n', flush=True)


class TestProxy(object):

    def __init__(self, test_name='not set'):
        self.test_name = test_name

    def and_test_name(self, test_name):
        self.test_name = test_name
        return self

    def test_starts(self):
        pass

    def test_finishes(self):
        pass

    def fails(self, reason):
        pass

    def __enter__(self, *args, **kwargs):
        self.test_starts()
        return self

    def __exit__(self, *args, **kwargs):
        self.test_finishes()


class TeamCityTestProxy(TestProxy):

    def test_starts(self):
        flush_text_line("##teamcity[testStarted name='{0}']".format(self.test_name))

    def test_finishes(self):
        flush_text_line("##teamcity[testFinished name='{0}']".format(self.test_name))

    def fails(self, reason):
        flush_text_line("##teamcity[testFailed name='{0}' message='See details' details='{1}']".format(
                        self.test_name,
                        reason
                        ))

########NEW FILE########
__FILENAME__ = cli
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder cli module.
    Contains the PyBuilder command-line entrypoint.
"""

import datetime
import optparse
import re
import sys
import traceback

from pybuilder import __version__
from pybuilder.core import Logger
from pybuilder.errors import PyBuilderException
from pybuilder.execution import ExecutionManager
from pybuilder.reactor import Reactor
from pybuilder.scaffolding import start_project
from pybuilder.terminal import (BOLD, BROWN, RED, GREEN, bold, styled_text,
                                fg, italic, print_text, print_text_line,
                                print_error, print_error_line, draw_line)
from pybuilder.utils import format_timestamp

PROPERTY_OVERRIDE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+=.*')


class CommandLineUsageException(PyBuilderException):

    def __init__(self, usage, message):
        super(CommandLineUsageException, self).__init__(message)
        self.usage = usage


class StdOutLogger(Logger):

    def _level_to_string(self, level):
        if Logger.DEBUG == level:
            return "[DEBUG]"
        if Logger.INFO == level:
            return "[INFO] "
        if Logger.WARN == level:
            return "[WARN] "
        return "[ERROR]"

    def _do_log(self, level, message, *arguments):
        formatted_message = self._format_message(message, *arguments)
        log_level = self._level_to_string(level)
        print_text_line("{0} {1}".format(log_level, formatted_message))


class ColoredStdOutLogger(StdOutLogger):

    def _level_to_string(self, level):
        if Logger.DEBUG == level:
            return italic("[DEBUG]")
        if Logger.INFO == level:
            return bold("[INFO] ")
        if Logger.WARN == level:
            return styled_text("[WARN] ", BOLD, fg(BROWN))
        return styled_text("[ERROR]", BOLD, fg(RED))


def parse_options(args):
    parser = optparse.OptionParser(usage="%prog [options] task1 [[task2] ...]",
                                   version="%prog " + __version__)

    def error(msg):
        raise CommandLineUsageException(
            parser.get_usage() + parser.format_option_help(), msg)

    parser.error = error

    parser.add_option("-t", "--list-tasks",
                      action="store_true",
                      dest="list_tasks",
                      default=False,
                      help="List tasks")

    parser.add_option("--start-project",
                      action="store_true",
                      dest="start_project",
                      default=False,
                      help="Initialize a build descriptor and python project structure.")

    parser.add_option("-v", "--verbose",
                      action="store_true",
                      dest="verbose",
                      default=False,
                      help="Enable verbose output")

    project_group = optparse.OptionGroup(
        parser, "Project Options", "Customizes the project to build.")

    project_group.add_option("-D", "--project-directory",
                             dest="project_directory",
                             help="Root directory to execute in",
                             metavar="<project directory>",
                             default=".")
    project_group.add_option("-E", "--environment",
                             dest="environments",
                             help="Activate the given environment for this build. Can be used multiple times",
                             metavar="<environment>",
                             action="append",
                             default=[])
    project_group.add_option("-P",
                             action="append",
                             dest="property_overrides",
                             default=[],
                             metavar="<property>=<value>",
                             help="Set/ override a property value")

    parser.add_option_group(project_group)

    output_group = optparse.OptionGroup(
        parser, "Output Options", "Modifies the messages printed during a build.")

    output_group.add_option("-X", "--debug",
                            action="store_true",
                            dest="debug",
                            default=False,
                            help="Print debug messages")
    output_group.add_option("-q", "--quiet",
                            action="store_true",
                            dest="quiet",
                            default=False,
                            help="Quiet mode; print only warnings and errors")
    output_group.add_option("-Q", "--very-quiet",
                            action="store_true",
                            dest="very_quiet",
                            default=False,
                            help="Very quiet mode; print only errors")
    output_group.add_option("-C", "--no-color",
                            action="store_true",
                            dest="no_color",
                            default=False,
                            help="Disable colored output")

    parser.add_option_group(output_group)

    options, arguments = parser.parse_args(args=list(args))

    property_overrides = {}
    for pair in options.property_overrides:
        if not PROPERTY_OVERRIDE_PATTERN.match(pair):
            parser.error("%s is not a property definition." % pair)
        key, val = pair.split("=")
        property_overrides[key] = val

    options.property_overrides = property_overrides

    if options.very_quiet:
        options.quiet = True

    return options, arguments


def init_reactor(logger):
    execution_manager = ExecutionManager(logger)
    reactor = Reactor(logger, execution_manager)
    return reactor


def should_colorize(options):
    return sys.stdout.isatty() and not options.no_color


def init_logger(options):
    threshold = Logger.INFO
    if options.debug:
        threshold = Logger.DEBUG
    elif options.quiet:
        threshold = Logger.WARN

    if not should_colorize(options):
        logger = StdOutLogger(threshold)
    else:
        logger = ColoredStdOutLogger(threshold)

    return logger


def print_build_summary(options, summary):
    print_text_line("Build Summary")
    print_text_line("%20s: %s" % ("Project", summary.project.name))
    print_text_line("%20s: %s" % ("Version", summary.project.version))
    print_text_line("%20s: %s" % ("Base directory", summary.project.basedir))
    print_text_line("%20s: %s" %
                    ("Environments", ", ".join(options.environments)))

    task_summary = ""
    for task in summary.task_summaries:
        task_summary += " %s [%d ms]" % (task.task, task.execution_time)

    print_text_line("%20s:%s" % ("Tasks", task_summary))


def print_styled_text(text, options, *style_attributes):
    if should_colorize(options):
        text = styled_text(text, *style_attributes)
    print_text(text)


def print_styled_text_line(text, options, *style_attributes):
    print_styled_text(text + "\n", options, *style_attributes)


def print_build_status(failure_message, options, successful):
    draw_line()
    if successful:
        print_styled_text_line("BUILD SUCCESSFUL", options, BOLD, fg(GREEN))
    else:
        print_styled_text_line(
            "BUILD FAILED - {0}".format(failure_message), options, BOLD, fg(RED))
    draw_line()


def print_elapsed_time_summary(start, end):
    time_needed = end - start
    millis = ((time_needed.days * 24 * 60 * 60) + time_needed.seconds) * \
        1000 + time_needed.microseconds / 1000
    print_text_line("Build finished at %s" % format_timestamp(end))
    print_text_line("Build took %d seconds (%d ms)" %
                    (time_needed.seconds, millis))


def print_summary(successful, summary, start, end, options, failure_message):
    print_build_status(failure_message, options, successful)

    if successful and summary:
        print_build_summary(options, summary)

    print_elapsed_time_summary(start, end)


def length_of_longest_string(list_of_strings):
    if len(list_of_strings) == 0:
        return 0

    result = 0
    for string in list_of_strings:
        length_of_string = len(string)
        if length_of_string > result:
            result = length_of_string

    return result


def print_list_of_tasks(reactor):
    print_text_line('Tasks found for project "%s":' % reactor.project.name)

    tasks = reactor.get_tasks()
    column_length = length_of_longest_string(
        list(map(lambda task: task.name, tasks)))
    column_length += 4

    for task in sorted(tasks):
        task_name = task.name.rjust(column_length)
        task_description = " ".join(
            task.description) or "<no description available>"
        print_text_line("{0} - {1}".format(task_name, task_description))

        if task.dependencies:
            whitespace = (column_length + 3) * " "
            depends_on_message = "depends on tasks: %s" % " ".join(
                task.dependencies)
            print_text_line(whitespace + depends_on_message)


def main(*args):
    try:
        options, arguments = parse_options(args)
    except CommandLineUsageException as e:
        print_error_line("Usage error: %s\n" % e)
        print_error(e.usage)
        return 1

    start = datetime.datetime.now()

    logger = init_logger(options)
    reactor = init_reactor(logger)

    if options.start_project:
        return start_project()

    if options.list_tasks:
        reactor.prepare_build(property_overrides=options.property_overrides,
                              project_directory=options.project_directory)

        print_list_of_tasks(reactor)
        return 0

    if not options.very_quiet:
        print_styled_text_line(
            "PyBuilder version {0}".format(__version__), options, BOLD)
        print_text_line("Build started at %s" % format_timestamp(start))
        draw_line()

    successful = True
    failure_message = None
    summary = None

    try:
        try:
            reactor.prepare_build(
                property_overrides=options.property_overrides,
                project_directory=options.project_directory)

            if options.verbose or options.debug:
                logger.debug("Verbose output enabled.\n")
                reactor.project.set_property("verbose", True)

            summary = reactor.build(
                environments=options.environments, tasks=arguments)

        except KeyboardInterrupt:
            raise PyBuilderException("Build aborted")

    except Exception as e:
        failure_message = str(e)
        if options.debug:
            traceback.print_exc(file=sys.stderr)
        successful = False

    finally:
        end = datetime.datetime.now()
        if not options.very_quiet:
            print_summary(
                successful, summary, start, end, options, failure_message)

        if not successful:
            return 1

        return 0

########NEW FILE########
__FILENAME__ = core
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder core module.
    Contains the most important classes and syntax used in a
    build.py project descriptor.
"""

import os
import string
import sys

from os.path import sep as PATH_SEPARATOR

from pybuilder.errors import MissingPropertyException
from .utils import as_list

INITIALIZER_ATTRIBUTE = "_python_builder_initializer"

ENVIRONMENTS_ATTRIBUTE = "_python_builder_environments"

NAME_ATTRIBUTE = "_python_builder_name"
ACTION_ATTRIBUTE = "_python_builder_action"
ONLY_ONCE_ATTRIBUTE = "_python_builder_action_only_once"
BEFORE_ATTRIBUTE = "_python_builder_before"
AFTER_ATTRIBUTE = "_python_builder_after"

TASK_ATTRIBUTE = "_python_builder_task"
DEPENDS_ATTRIBUTE = "_python_builder_depends"

DESCRIPTION_ATTRIBUTE = "_python_builder_description"


def init(*possible_callable, **additional_arguments):
    """
    Decorator for functions that wish to perform initialization steps.
    The decorated functions are called "initializers".

    Initializers are executed after all plugins and projects have been loaded
    but before any task is executed.

    Initializers may take an additional named argument "environments" which should contain a string or list of strings
    naming the environments this initializer applies for.

    Examples:

    @init
    def some_initializer(): pass

    @init()
    def some_initializer(): pass

    @init(environments="spam")
    def some_initializer(): pass

    @init(environments=["spam", "eggs"])
    def some_initializer(): pass
    """

    def do_decoration(callable):
        setattr(callable, INITIALIZER_ATTRIBUTE, True)

        if "environments" in additional_arguments:
            setattr(callable, ENVIRONMENTS_ATTRIBUTE, as_list(additional_arguments["environments"]))

        return callable

    if possible_callable:
        return do_decoration(possible_callable[0])

    return do_decoration


def task(callable_or_string):
    """
    Decorator for functions that should be used as tasks. Tasks are the main
    building blocks of projects.
    You can use this decorator either plain (no argument) or with
    a string argument, which overrides the default name.
    """
    if isinstance(callable_or_string, str):
        def set_name_and_task_attribute(callable):
            setattr(callable, TASK_ATTRIBUTE, True)
            setattr(callable, NAME_ATTRIBUTE, callable_or_string)
            return callable
        return set_name_and_task_attribute
    else:
        setattr(callable_or_string, TASK_ATTRIBUTE, True)
        return callable_or_string


class description(object):
    def __init__(self, description):
        self._description = description

    def __call__(self, callable):
        setattr(callable, DESCRIPTION_ATTRIBUTE, self._description)
        return callable


class depends(object):
    def __init__(self, *depends):
        self._depends = depends

    def __call__(self, callable):
        setattr(callable, DEPENDS_ATTRIBUTE, self._depends)
        return callable


class BaseAction(object):
    def __init__(self, attribute, only_once, tasks):
        self.tasks = tasks
        self.attribute = attribute
        self.only_once = only_once

    def __call__(self, callable):
        setattr(callable, ACTION_ATTRIBUTE, True)
        setattr(callable, self.attribute, self.tasks)
        if self.only_once:
            setattr(callable, ONLY_ONCE_ATTRIBUTE, True)

        return callable


class before(BaseAction):
    def __init__(self, tasks, only_once=False):
        super(before, self).__init__(BEFORE_ATTRIBUTE, only_once, tasks)


class after(BaseAction):
    def __init__(self, tasks, only_once=False):
        super(after, self).__init__(AFTER_ATTRIBUTE, only_once, tasks)


def use_bldsup(build_support_dir="bldsup"):
    """Specify a local build support directory for build specific extensions.

    use_plugin(name) and import will look for python modules in BUILD_SUPPORT_DIR.

    WARNING: The BUILD_SUPPORT_DIR must exist and must have an __init__.py file in it.
    """
    assert os.path.isdir(build_support_dir), "use_bldsup('{0}'): The {0} directory must exist!".format(build_support_dir)
    init_file = os.path.join(build_support_dir, "__init__.py")
    assert os.path.isfile(init_file), "use_bldsup('{0}'): The {1} file must exist!".format(build_support_dir, init_file)
    sys.path.insert(0, build_support_dir)


def use_plugin(name):
    from pybuilder.reactor import Reactor
    reactor = Reactor.current_instance()
    if reactor is not None:
        reactor.require_plugin(name)


class Author(object):
    def __init__(self, name, email=None, roles=None):
        self.name = name
        self.email = email
        self.roles = roles or []


class Dependency(object):
    """
    Defines a dependency to another module. Use the
        depends_on
    method from class Project to add a dependency to a project.
    """
    def __init__(self, name, version=None, url=None):
        self.name = name
        self.version = version
        self.url = url

    def __eq__(self, other):
        return self.name == other.name and self.version == other.version and self.url == other.url

    def __ne__(self, other):
        return not(self == other)

    def __hash__(self):
        return 13 * hash(self.name) + 17 * hash(self.version)

    def __lt__(self, other):
        return self.name < other.name


class Project(object):
    """
    Descriptor for a project to be built. A project has a number of attributes
    as well as some convenience methods to access these properties.
    """
    def __init__(self, basedir, version="1.0-SNAPSHOT", name=None):
        self.name = name
        self.version = version
        self.basedir = basedir
        if not self.name:
            self.name = os.path.basename(basedir)

        self.default_task = None

        self.summary = ""
        self.home_page = ""
        self.description = ""
        self.author = ""
        self.authors = []
        self.license = ""
        self.url = ""
        self._properties = {"verbose": False}
        self._install_dependencies = set()
        self._build_dependencies = set()
        self._manifest_included_files = []
        self._package_data = {}
        self._files_to_install = []

    def __str__(self):
        return "[Project name=%s basedir=%s]" % (self.name, self.basedir)

    def validate(self):
        """
        Validates the project returning a list of validation error messages if the project is not valid.
        Returns an empty list if the project is valid.
        """
        result = self.validate_dependencies()

        return result

    def validate_dependencies(self):
        result = []

        build_dependencies_found = {}

        for dependency in self.build_dependencies:
            if dependency.name in build_dependencies_found:
                if build_dependencies_found[dependency.name] == 1:
                    result.append("Build dependency '%s' has been defined multiple times." % dependency.name)
                build_dependencies_found[dependency.name] += 1
            else:
                build_dependencies_found[dependency.name] = 1

        runtime_dependencies_found = {}

        for dependency in self.dependencies:
            if dependency.name in runtime_dependencies_found:
                if runtime_dependencies_found[dependency.name] == 1:
                    result.append("Runtime dependency '%s' has been defined multiple times." % dependency.name)
                runtime_dependencies_found[dependency.name] += 1
            else:
                runtime_dependencies_found[dependency.name] = 1
            if dependency.name in build_dependencies_found:
                result.append("Runtime dependency '%s' has also been given as build dependency." % dependency.name)

        return result

    @property
    def properties(self):
        result = self._properties
        result["basedir"] = self.basedir
        return result

    @property
    def dependencies(self):
        return list(sorted(self._install_dependencies))

    @property
    def build_dependencies(self):
        return list(sorted(self._build_dependencies))

    def depends_on(self, name, version=None, url=None):
        self._install_dependencies.add(Dependency(name, version, url))

    def build_depends_on(self, name, version=None, url=None):
        self._build_dependencies.add(Dependency(name, version, url))

    @property
    def manifest_included_files(self):
        return self._manifest_included_files

    def _manifest_include(self, glob_pattern):
        if not glob_pattern or glob_pattern.strip() == "":
            raise ValueError("Missing glob_pattern argument.")

        self._manifest_included_files.append(glob_pattern)

    @property
    def package_data(self):
        return self._package_data

    def include_file(self, package_name, filename):
        if not package_name or package_name.strip() == "":
            raise ValueError("Missing argument package name.")

        if not filename or filename.strip() == "":
            raise ValueError("Missing argument filename.")

        full_filename = os.path.join(package_name, filename)
        self._manifest_include(full_filename)

        if package_name not in self._package_data:
            self._package_data[package_name] = [filename]
            return
        self._package_data[package_name].append(filename)

    @property
    def files_to_install(self):
        return self._files_to_install

    def install_file(self, destination, filename):
        if not destination:
            raise ValueError("Missing argument destination")

        if not filename or filename.strip() == "":
            raise ValueError("Missing argument filename")

        current_tuple = None
        for installation_tuple in self.files_to_install:
            destination_name = installation_tuple[0]

            if destination_name == destination:
                    current_tuple = installation_tuple

        if current_tuple:
            list_of_files_within_tuple = current_tuple[1]
            list_of_files_within_tuple.append(filename)
        else:
            initial_tuple = (destination, [filename])
            self.files_to_install.append(initial_tuple)

        self._manifest_include(filename)

    def expand(self, format_string):
        previous = None
        result = format_string
        while previous != result:
            try:
                previous = result
                result = string.Template(result).substitute(self.properties)
            except KeyError as e:
                raise MissingPropertyException(e)
        return result

    def expand_path(self, format_string, *additional_path_elements):
        elements = [self.basedir]
        elements += self.expand(format_string).split(PATH_SEPARATOR)
        elements += list(additional_path_elements)
        return os.path.join(*elements)

    def get_property(self, key, default_value=None):
        return self.properties.get(key, default_value)

    def get_mandatory_property(self, key):
        if not self.has_property(key):
            raise MissingPropertyException(key)
        return self.get_property(key)

    def has_property(self, key):
        return key in self.properties

    def set_property(self, key, value):
        self.properties[key] = value

    def set_property_if_unset(self, key, value):
        if not self.has_property(key):
            self.set_property(key, value)


class Logger(object):
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4

    def __init__(self, threshold=INFO):
        self.threshold = threshold

    def _do_log(self, level, message, *arguments):
        pass

    @staticmethod
    def _format_message(message, *arguments):
        if arguments:
            return message % arguments
        return message

    def log(self, level, message, *arguments):
        if level >= self.threshold:
            self._do_log(level, message, *arguments)

    def debug(self, message, *arguments):
        self.log(Logger.DEBUG, message, *arguments)

    def info(self, message, *arguments):
        self.log(Logger.INFO, message, *arguments)

    def warn(self, message, *arguments):
        self.log(Logger.WARN, message, *arguments)

    def error(self, message, *arguments):
        self.log(Logger.ERROR, message, *arguments)

########NEW FILE########
__FILENAME__ = errors
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder error module.
    Defines all possible errors that can arise during the execution of PyBuilder.
"""


class PyBuilderException(Exception):

    def __init__(self, message, *arguments):
        self._message = message
        self._arguments = arguments

    @property
    def message(self):
        return self._message % self._arguments

    def __str__(self):
        return self.message


class InvalidNameException(PyBuilderException):

    def __init__(self, name):
        super(InvalidNameException, self).__init__("Invalid name: %s", name)


class NoSuchTaskException(PyBuilderException):

    def __init__(self, name):
        super(NoSuchTaskException, self).__init__("No such task %s", name)


class CircularTaskDependencyException(PyBuilderException):

    def __init__(self, first, second=None):
        if second:
            super(
                CircularTaskDependencyException, self).__init__("Circular task dependency detected between %s and %s",
                                                                first,
                                                                second)
        self.first = first
        self.second = second


class MissingPrerequisiteException(PyBuilderException):

    def __init__(self, prerequisite, caller="n/a"):
        super(
            MissingPrerequisiteException, self).__init__("Missing prerequisite %s required by %s",
                                                         prerequisite, caller)


class MissingTaskDependencyException(PyBuilderException):

    def __init__(self, source, dependency):
        super(
            MissingTaskDependencyException, self).__init__("Missing task '%s' required for task '%s'",
                                                           dependency, source)


class MissingActionDependencyException(PyBuilderException):

    def __init__(self, source, dependency):
        super(
            MissingActionDependencyException, self).__init__("Missing task '%s' required for action '%s'",
                                                             dependency, source)


class MissingPluginException(PyBuilderException):

    def __init__(self, plugin, message=""):
        super(MissingPluginException, self).__init__(
            "Missing plugin '%s': %s", plugin, message)


class BuildFailedException(PyBuilderException):
    pass


class MissingPropertyException(PyBuilderException):

    def __init__(self, property):
        super(MissingPropertyException, self).__init__(
            "No such property: %s", property)


class ProjectValidationFailedException(BuildFailedException):

    def __init__(self, validation_messages):
        BuildFailedException.__init__(
            self, "Project validation failed: " + "\n-".join(validation_messages))
        self.validation_messages = validation_messages


class InternalException(PyBuilderException):
    pass


class DependenciesNotResolvedException(InternalException):
    def __init__(self):
        super(DependenciesNotResolvedException, self).__init__("Dependencies have not been resolved.")

########NEW FILE########
__FILENAME__ = execution
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder execution module.
    Deals with the execution of a PyBuilder process by
    running tasks, actions and initializers in the correct
    order regarding dependencies.
"""

import inspect
import re
import types

from pybuilder.errors import (CircularTaskDependencyException,
                              DependenciesNotResolvedException,
                              InvalidNameException,
                              MissingTaskDependencyException,
                              MissingActionDependencyException,
                              NoSuchTaskException)
from pybuilder.utils import as_list, Timer


def as_task_name_list(mixed):
    result = []
    for d in as_list(mixed):
        if isinstance(d, types.FunctionType):
            result.append(d.__name__)
        else:
            result.append(str(d))
    return result


class Executable(object):
    NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+$")

    def __init__(self, name, callable, description=""):
        if not Executable.NAME_PATTERN.match(name):
            raise InvalidNameException(name)

        self._name = name
        self.description = description
        self.callable = callable
        if hasattr(callable, "__module__"):
            self.source = callable.__module__
        else:
            self.source = "n/a"

        if isinstance(self.callable, types.FunctionType):
            self.parameters = inspect.getargspec(self.callable).args
        else:
            raise TypeError("Don't know how to handle callable %s" % callable)

    @property
    def name(self):
        return self._name

    def execute(self, argument_dict):
        arguments = []
        for parameter in self.parameters:
            if parameter not in argument_dict:
                raise ValueError("Invalid parameter '%s' for %s %s" % (parameter, self.__class__.__name__, self.name))
            arguments.append(argument_dict[parameter])

        self.callable(*arguments)


class Action(Executable):
    def __init__(self, name, callable, before=None, after=None, description="", only_once=False):
        super(Action, self).__init__(name, callable, description)
        self.execute_before = as_task_name_list(before)
        self.execute_after = as_task_name_list(after)
        self.only_once = only_once


class Task(object):
    def __init__(self, name, callable, dependencies=None, description=""):
        self.name = name
        self.executables = [Executable(name, callable, description)]
        self.dependencies = as_task_name_list(dependencies)
        self.description = [description]

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.name == other.name
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, Task):
            return self.name < other.name
        return self.name < other

    def extend(self, task):
        self.executables += task.executables
        self.dependencies += task.dependencies
        self.description += task.description

    def execute(self, logger, argument_dict):
        for executable in self.executables:
            logger.debug("Executing subtask from %s", executable.source)
            executable.execute(argument_dict)


class Initializer(Executable):
    def __init__(self, name, callable, environments=None, description=""):
        super(Initializer, self).__init__(name, callable, description)
        self.environments = environments

    def is_applicable(self, environments=None):
        if not self.environments:
            return True
        for environment in as_list(environments):
            if environment in self.environments:
                return True


class TaskExecutionSummary(object):
    def __init__(self, task, number_of_actions, execution_time):
        self.task = task
        self.number_of_actions = number_of_actions
        self.execution_time = execution_time


class ExecutionManager(object):
    def __init__(self, logger):
        self.logger = logger

        self._tasks = {}
        self._task_dependencies = {}

        self._actions = {}
        self._execute_before = {}
        self._execute_after = {}

        self._initializers = []

        self._dependencies_resolved = False
        self._actions_executed = []

    @property
    def initializers(self):
        return self._initializers

    @property
    def tasks(self):
        return list(self._tasks.values())

    @property
    def task_names(self):
        return sorted(self._tasks.keys())

    def register_initializer(self, initializer):
        self.logger.debug("Registering initializer '%s'", initializer.name)
        self._initializers.append(initializer)

    def register_action(self, action):
        self.logger.debug("Registering action '%s'", action.name)
        self._actions[action.name] = action

    def register_task(self, *tasks):
        for task in tasks:
            self.logger.debug("Registering task '%s'", task.name)
            if task.name in self._tasks:
                self._tasks[task.name].extend(task)
            else:
                self._tasks[task.name] = task

    def execute_initializers(self, environments=None, **keyword_arguments):
        for initializer in self._initializers:
            if not initializer.is_applicable(environments):
                message = "Not going to execute initializer '%s' from '%s' as environments do not match."
                self.logger.debug(message, initializer.name, initializer.source)

            else:
                self.logger.debug("Executing initializer '%s' from '%s'",
                                  initializer.name, initializer.source)
                initializer.execute(keyword_arguments)

    def assert_dependencies_resolved(self):
        if not self._dependencies_resolved:
            raise DependenciesNotResolvedException()

    def execute_task(self, task, **keyword_arguments):
        self.assert_dependencies_resolved()

        self.logger.debug("Executing task '%s'",
                          task.name)

        timer = Timer.start()
        number_of_actions = 0

        for action in self._execute_before[task.name]:
            if self.execute_action(action, keyword_arguments):
                number_of_actions += 1

        task.execute(self.logger, keyword_arguments)

        for action in self._execute_after[task.name]:
            if self.execute_action(action, keyword_arguments):
                number_of_actions += 1

        timer.stop()
        return TaskExecutionSummary(task.name, number_of_actions, timer.get_millis())

    def execute_action(self, action, arguments):
        if action.only_once and action in self._actions_executed:
            message = "Action %s has been executed before and is marked as only_once, so will not be executed again"
            self.logger.debug(message, action.name)
            return False

        self.logger.debug("Executing action '%s' from '%s' before task", action.name, action.source)
        action.execute(arguments)
        self._actions_executed.append(action)
        return True

    def execute_execution_plan(self, execution_plan, **keyword_arguments):
        self.assert_dependencies_resolved()

        summaries = []

        for task in execution_plan:
            summaries.append(self.execute_task(task, **keyword_arguments))

        return summaries

    def get_task(self, name):
        return self._tasks[name]

    def has_task(self, name):
        return name in self._tasks

    def build_execution_plan(self, task_names):
        self.assert_dependencies_resolved()

        execution_plan = []
        for name in as_list(task_names):
            self.enqueue_task(execution_plan, name)
        return execution_plan

    def enqueue_task(self, execution_plan, task_name, circular_check=None):
        if not self.has_task(task_name):
            raise NoSuchTaskException(task_name)

        task = self.get_task(task_name)

        if task == circular_check:
            raise CircularTaskDependencyException(task.name)

        if task in execution_plan:
            return

        try:
            for dependency in self._task_dependencies[task.name]:
                self.enqueue_task(execution_plan, dependency.name,
                                  circular_check=circular_check if circular_check else task)
        except CircularTaskDependencyException as e:
            if e.second:
                raise
            raise CircularTaskDependencyException(e.first, task.name)

        execution_plan.append(task)

    def resolve_dependencies(self):
        for task in self._tasks.values():
            self._execute_before[task.name] = []
            self._execute_after[task.name] = []
            self._task_dependencies[task.name] = []
            for d in task.dependencies:
                if not self.has_task(d):
                    raise MissingTaskDependencyException(task.name, d)
                self._task_dependencies[task.name].append(self.get_task(d))

        for action in self._actions.values():
            for task in action.execute_before:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_before[task].append(action)

            for task in action.execute_after:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_after[task].append(action)

        self._dependencies_resolved = True

########NEW FILE########
__FILENAME__ = external_command
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files
from pybuilder.utils import read_file


class ExternalCommandResult(object):

    def __init__(self, exit_code, report_file, report_lines, error_report_file, error_report_lines):
        self.exit_code = exit_code
        self.report_file = report_file
        self.report_lines = report_lines
        self.error_report_file = error_report_file
        self.error_report_lines = error_report_lines


class ExternalCommandBuilder(object):

    def __init__(self, command_name, project):
        self.command_name = command_name
        self.parts = [command_name]
        self.project = project

    def use_argument(self, argument):
        self.parts.append(argument)
        return self

    def formatted_with_property(self, property_name):
        property_value = self.project.get_property(property_name)
        self.parts[-1] = self.parts[-1].format(property_value)
        return self

    def formatted_with_truthy_property(self, property_name):
        return self.formatted_with_property(property_name).only_if_property_is_truthy(property_name)

    def only_if_property_is_truthy(self, property_name):
        property_value = self.project.get_property(property_name)
        if not property_value:
            del self.parts[-1]
        return self

    @property
    def as_string(self):
        return ' '.join(self.parts)

    def run_on_production_source_files(self, logger, include_test_sources=False, include_scripts=False):
        execution_result = execute_tool_on_source_files(project=self.project,
                                                        name=self.command_name,
                                                        command_and_arguments=self.parts,
                                                        include_test_sources=include_test_sources,
                                                        include_scripts=include_scripts,
                                                        logger=logger)
        exit_code, report_file = execution_result
        report_lines = read_file(report_file)
        error_report_file = '{0}.err'.format(report_file)  # TODO @mriehl not dry, execute_tool... should return this
        error_report_lines = read_file(error_report_file)
        return ExternalCommandResult(exit_code, report_file, report_lines, error_report_file, error_report_lines)

    def run_on_production_and_test_source_files(self, logger):
        return self.run_on_production_source_files(logger, include_test_sources=True)

    def run_on_production_and_test_source_files_and_scripts(self, logger):
        return self.run_on_production_source_files(logger, include_test_sources=True, include_scripts=True)

########NEW FILE########
__FILENAME__ = pluginloader
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder pluginloader module.
    Provides a mechanism to load PyBuilder plugins.
"""

import sys
import tempfile

from pybuilder.errors import MissingPluginException
from pybuilder.utils import execute_command, read_file


PYPI_PLUGIN_PROTOCOL = "pypi:"


class PluginLoader (object):

    def __init__(self, logger):
        self.logger = logger

    def load_plugin(self, project, name):
        pass


class BuiltinPluginLoader(PluginLoader):

    def load_plugin(self, project, name):
        self.logger.debug("Trying to load builtin plugin '%s'", name)
        builtin_plugin_name = "pybuilder.plugins.%s_plugin" % name
        try:
            __import__(builtin_plugin_name)
            self.logger.debug("Found builtin plugin '%s'", builtin_plugin_name)
            return sys.modules[builtin_plugin_name]
        except ImportError as import_error:
            raise MissingPluginException(name, import_error)


class ThirdPartyPluginLoader(PluginLoader):

    def load_plugin(self, project, name):
        thirdparty_plugin = name
        # Maybe we already installed this plugin from PyPI before
        if thirdparty_plugin.startswith(PYPI_PLUGIN_PROTOCOL):
            thirdparty_plugin = thirdparty_plugin.replace(PYPI_PLUGIN_PROTOCOL, "")
        self.logger.debug("Trying to load third party plugin '%s'", thirdparty_plugin)

        try:
            __import__(thirdparty_plugin)
            self.logger.debug("Found third party plugin '%s'", thirdparty_plugin)
            return sys.modules[thirdparty_plugin]
        except ImportError as import_error:
            raise MissingPluginException(name, import_error)


class DownloadingPluginLoader(ThirdPartyPluginLoader):

    def load_plugin(self, project, name):
        self.logger.info("Downloading missing plugin {0}".format(name))
        try:
            _install_external_plugin(name, self.logger)
            self.logger.info("Installed plugin {0}.".format(name))
        except MissingPluginException as e:
            self.logger.error("Could not install plugin {0}: {1}.".format(name, e))
            return None
        return ThirdPartyPluginLoader.load_plugin(self, project, name)


class DispatchingPluginLoader(PluginLoader):

    def __init__(self, logger, *loader):
        super(DispatchingPluginLoader, self).__init__(logger)
        self.loader = loader

    def load_plugin(self, project, name):
        last_problem = None
        for loader in self.loader:
            try:
                return loader.load_plugin(project, name)
            except MissingPluginException as e:
                last_problem = e
        raise last_problem


def _install_external_plugin(name, logger):
    if not name.startswith(PYPI_PLUGIN_PROTOCOL):
        message = "Only plugins starting with '{0}' are currently supported"
        raise MissingPluginException(name, message.format(PYPI_PLUGIN_PROTOCOL))
    plugin_name_on_pypi = name.replace(PYPI_PLUGIN_PROTOCOL, "")
    log_file = tempfile.NamedTemporaryFile(delete=False).name
    result = execute_command(
        'pip install {0}'.format(plugin_name_on_pypi),
        log_file,
        error_file_name=log_file,
        shell=True)
    if result != 0:
        logger.error("The following pip error was encountered:\n" + "".join(read_file(log_file)))
        message = "Failed to install from PyPI".format(plugin_name_on_pypi)
        raise MissingPluginException(name, message)

########NEW FILE########
__FILENAME__ = analysis_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from pybuilder.core import task, depends, description, use_plugin

use_plugin("core")


@task
@description("Execute analysis plugins.")
@depends("run_unit_tests")
def analyze():
    pass

########NEW FILE########
__FILENAME__ = copy_resources_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import shutil

from pybuilder.core import init, task, use_plugin
from pybuilder.utils import apply_on_files

use_plugin("core")


@init
def init_copy_resources_plugin(project):
    project.set_property_if_unset("copy_resources_target", "$dir_target")
    project.set_property_if_unset("copy_resources_glob", [])


@task
def package(project, logger):
    globs = project.get_mandatory_property("copy_resources_glob")
    if not globs:
        logger.warn("No resources to copy configured. Consider removing plugin.")
        return

    source = project.basedir
    target = project.expand_path("$copy_resources_target")
    logger.info("Copying resources matching '%s' from %s to %s", " ".join(globs), source, target)

    apply_on_files(source, copy_resource, globs, target, logger)


def copy_resource(absolute_file_name, relative_file_name, target, logger):
    logger.debug("Copying resource %s", relative_file_name)

    absolute_target_file_name = os.path.join(target, relative_file_name)
    parent = os.path.dirname(absolute_target_file_name)
    if not os.path.exists(parent):
        os.makedirs(parent)
    shutil.copy(absolute_file_name, absolute_target_file_name)

########NEW FILE########
__FILENAME__ = core_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import shutil

from pybuilder.core import init, task, description, depends


@init
def init(project):
    project.set_property("dir_target", "target")
    project.set_property("dir_reports", "$dir_target/reports")
    project.set_property("dir_logs", "$dir_target/logs")

    def write_report(file, *content):
        with open(project.expand_path("$dir_reports", file), "w") as report_file:
            report_file.writelines(content)
    project.write_report = write_report


@task
@description("Cleans the generated output.")
def clean(project, logger):
    target_directory = project.expand_path("$dir_target")
    logger.info("Removing target directory %s", target_directory)
    shutil.rmtree(target_directory, ignore_errors=True)


@task
@description("Prepares the project for building.")
def prepare(project, logger):
    target_directory = project.expand_path("$dir_target")
    if not os.path.exists(target_directory):
        logger.debug("Creating target directory %s", target_directory)
        os.mkdir(target_directory)

    reports_directory = project.expand_path("$dir_reports")
    if not os.path.exists(reports_directory):
        logger.debug("Creating reports directory %s", reports_directory)
        os.mkdir(reports_directory)


@task
@depends(prepare)
@description("Compiles source files that need compilation.")
def compile_sources():
    pass


@task
@depends(compile_sources)
@description("Runs all unit tests.")
def run_unit_tests():
    pass


@task
@depends(run_unit_tests)
@description("Packages the application.")
def package():
    pass


@task
@depends(package)
@description("Runs integration tests on the packaged application.")
def run_integration_tests():
    pass


@task
@depends(run_integration_tests)
@description("Verifies the project and possibly integration tests.")
def verify():
    pass


@task
@depends(verify)
@description("Publishes the project.")
def publish():
    pass

########NEW FILE########
__FILENAME__ = exec_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from pybuilder.core import task, use_plugin
from pybuilder.errors import BuildFailedException

import subprocess

use_plugin("core")


@task
def run_unit_tests(project, logger):
    run_command('run_unit_tests', project, logger)


@task
def run_integration_tests(project, logger):
    run_command('run_integration_tests', project, logger)


@task
def analyze(project, logger):
    run_command('analyze', project, logger)


@task
def package(project, logger):
    run_command('package', project, logger)


@task
def publish(project, logger):
    run_command('publish', project, logger)


def _write_command_report(project, stdout, stderr, command_line, phase, process_return_code):
        project.write_report('exec_%s' % phase, stdout)
        project.write_report('exec_%s.err' % phase, stderr)


def _log_quoted_output(logger, output_type, output, phase):
    separator = '-' * 5
    logger.info('{0} verbatim {1} output of {2} {0}'.format(separator, output_type, phase))
    for line in output.split('\n'):
        logger.info(line)
    logger.info('{0} end of verbatim {1} output {0}'.format(separator, output_type))


def run_command(phase, project, logger):
    command_line = project.get_property('%s_command' % phase)
    if not command_line:
        return

    process_handle = subprocess.Popen(
        command_line,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    (stdout, stderr) = process_handle.communicate()
    process_return_code = process_handle.returncode

    _write_command_report(project,
                          stdout,
                          stderr,
                          command_line,
                          phase,
                          process_return_code)

    if project.get_property('%s_propagate_stdout' % phase) and stdout:
        _log_quoted_output(logger, '', stdout, phase)

    if project.get_property('%s_propagate_stderr' % phase) and stderr:
        _log_quoted_output(logger, 'error', stderr, phase)

    if process_return_code != 0:
        raise BuildFailedException(
            'exec plugin command {0} for {1} exited with nonzero code {2}'.format(command_line,
                                                                                  phase,
                                                                                  process_return_code))

########NEW FILE########
__FILENAME__ = filter_resources_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import string

from pybuilder.core import init, after, use_plugin
from pybuilder.utils import apply_on_files, read_file, write_file

use_plugin("core")


@init
def init_filter_resources_plugin(project):
    project.set_property_if_unset("filter_resources_target", "$dir_target")
    project.set_property_if_unset("filter_resources_glob", [])


@after("package", only_once=True)
def filter_resources(project, logger):
    globs = project.get_mandatory_property("filter_resources_glob")
    if not globs:
        logger.warn("No resources to filter configured. Consider removing plugin.")
        return

    target = project.expand_path("$filter_resources_target")
    logger.info("Filter resources matching %s in %s", " ".join(globs), target)

    project_dict_wrapper = ProjectDictWrapper(project)

    apply_on_files(target, filter_resource, globs, project_dict_wrapper, logger)


def filter_resource(absolute_file_name, relative_file_name, dict, logger):
    logger.debug("Filtering resource %s", absolute_file_name)
    content = "".join(read_file(absolute_file_name))
    filtered = string.Template(content).safe_substitute(dict)
    write_file(absolute_file_name, filtered)


class ProjectDictWrapper(object):
    def __init__(self, project):
        self.project = project

    def __getitem__(self, key):
        if hasattr(self.project, key):
            return getattr(self.project, key)

        return self.project.get_property(key, key)

########NEW FILE########
__FILENAME__ = core_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import re
import shutil

from pybuilder.core import init, task, description, use_plugin

HIDDEN_FILE_NAME_PATTERN = re.compile(r'^\..*$')

PYTHON_SOURCES_PROPERTY = "dir_source_main_python"
SCRIPTS_SOURCES_PROPERTY = "dir_source_main_scripts"
DISTRIBUTION_PROPERTY = "dir_dist"
SCRIPTS_TARGET_PROPERTY = "dir_dist_scripts"

use_plugin("core")


@init
def init_python_directories(project):
    project.set_property_if_unset(PYTHON_SOURCES_PROPERTY, "src/main/python")
    project.set_property_if_unset(SCRIPTS_SOURCES_PROPERTY, "src/main/scripts")
    project.set_property_if_unset(SCRIPTS_TARGET_PROPERTY, None)
    project.set_property_if_unset(DISTRIBUTION_PROPERTY,
                                  "$dir_target/dist/{0}-{1}".format(project.name, project.version))

    def list_packages():
        source_path = project.expand_path("$dir_source_main_python")
        for root, dirnames, _ in os.walk(source_path):
            for directory in dirnames:
                full_path = os.path.join(root, directory)
                if os.path.exists(os.path.join(full_path, "__init__.py")):
                    package = full_path.replace(source_path, "")
                    package = package[1:].replace(os.sep, ".")
                    yield package

    def list_modules():
        source_path = project.expand_path("$dir_source_main_python")
        for potential_module_file in os.listdir(source_path):
            potential_module_path = os.path.join(source_path, potential_module_file)
            if os.path.isfile(potential_module_path) and potential_module_file.endswith(".py"):
                yield potential_module_file[:-len(".py")]

    project.list_packages = list_packages
    project.list_modules = list_modules

    def list_scripts():
        scripts_dir = project.expand_path("$dir_source_main_scripts")
        if not os.path.exists(scripts_dir):
            return
        for script in os.listdir(scripts_dir):
            if os.path.isfile(os.path.join(scripts_dir, script)):
                yield script

    project.list_scripts = list_scripts


@task
@description("Package a python application.")
def package(project, logger):
    init_dist_target(project, logger)

    logger.info("Building distribution in {0}".format(project.expand_path("$" + DISTRIBUTION_PROPERTY)))

    copy_python_sources(project, logger)
    copy_scripts(project, logger)


def copy_scripts(project, logger):
    scripts_target = project.expand_path("$" + DISTRIBUTION_PROPERTY)
    if project.get_property(SCRIPTS_TARGET_PROPERTY):
        scripts_target = project.expand_path("$" + DISTRIBUTION_PROPERTY + "/$" + SCRIPTS_TARGET_PROPERTY)

    if not os.path.exists(scripts_target):
        os.mkdir(scripts_target)

    logger.info("Copying scripts to %s", scripts_target)

    scripts_source = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY)
    if not os.path.exists(scripts_source):
        return
    for script in project.list_scripts():
        logger.debug("Copying script %s", script)
        source_file = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY, script)
        shutil.copy(source_file, scripts_target)


def copy_python_sources(project, logger):
    for package in os.listdir(project.expand_path("$" + PYTHON_SOURCES_PROPERTY)):
        if HIDDEN_FILE_NAME_PATTERN.match(package):
            continue
        logger.debug("Copying module/ package %s", package)
        source = project.expand_path("$" + PYTHON_SOURCES_PROPERTY, package)
        target = project.expand_path("$" + DISTRIBUTION_PROPERTY, package)
        if os.path.isdir(source):
            shutil.copytree(source, target,
                            symlinks=False,
                            ignore=shutil.ignore_patterns("*.pyc", ".*"))
        else:
            shutil.copyfile(source, target)


def init_dist_target(project, logger):
    dist_target = project.expand_path("$" + DISTRIBUTION_PROPERTY)

    if os.path.exists(dist_target):
        logger.debug("Removing preexisting distribution %s", dist_target)
        shutil.rmtree(dist_target)

    logger.debug("Creating directory %s", dist_target)
    os.makedirs(dist_target)

########NEW FILE########
__FILENAME__ = coverage_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import imp
import multiprocessing
import sys

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

from pybuilder.core import init, after, use_plugin
from pybuilder.utils import discover_modules, render_report
from pybuilder.errors import BuildFailedException

use_plugin("python.core")
use_plugin("analysis")


@init
def init_coverage_properties(project):
    project.build_depends_on("coverage")

    project.set_property_if_unset("coverage_threshold_warn", 70)
    project.set_property_if_unset("coverage_break_build", True)
    project.set_property_if_unset("coverage_reload_modules", True)
    project.set_property_if_unset("coverage_exceptions", [])
    project.set_property_if_unset("coverage_fork", False)


def start_coverage(coverage_module):
    coverage_module.erase()
    coverage_module.start()


def stop_coverage(coverage_module, project, logger):
    reimport_source_modules(project, logger)
    coverage_module.stop()


@after(("analyze", "verify"), only_once=True)
def verify_coverage(project, logger, reactor):
    logger.info("Collecting coverage information")

    if project.get_property("coverage_fork"):
        logger.debug("Forking process to do coverage analysis")
        process = multiprocessing.Process(target=do_coverage,
                                          args=(project, logger, reactor))
        process.start()
        process.join()
    else:
        do_coverage(project, logger, reactor)


def do_coverage(project, logger, reactor):
    import coverage

    start_coverage(coverage)
    project.set_property('__running_coverage', True)  # tell other plugins that we are not really unit testing right now
    reactor.execute_task("run_unit_tests")
    project.set_property('__running_coverage', False)

    stop_coverage(coverage, project, logger)

    coverage_too_low = False
    threshold = project.get_property("coverage_threshold_warn")
    exceptions = project.get_property("coverage_exceptions")

    report = {
        "module_names": []
    }

    sum_lines = 0
    sum_lines_not_covered = 0

    module_names = discover_modules_to_cover(project)
    modules = []
    for module_name in module_names:
        try:
            module = sys.modules[module_name]
        except KeyError:
            logger.warn("Module not imported: {0}. No coverage information available.".format(module_name))
            continue

        modules.append(module)

        module_report_data = build_module_report(coverage, module)

        sum_lines += module_report_data[0]
        sum_lines_not_covered += module_report_data[2]

        module_report = {
            "module": module_name,
            "coverage": module_report_data[4],
            "sum_lines": module_report_data[0],
            "lines": module_report_data[1],
            "sum_lines_not_covered": module_report_data[2],
            "lines_not_covered": module_report_data[3],
        }

        report["module_names"].append(module_report)

        if module_report_data[4] < threshold:
            msg = "Test coverage below %2d%% for %s: %2d%%" % (threshold, module_name, module_report_data[4])
            if module_name not in exceptions:
                logger.warn(msg)
                coverage_too_low = True
            else:
                logger.info(msg)

    if sum_lines == 0:
        overall_coverage = 0
    else:
        overall_coverage = (sum_lines - sum_lines_not_covered) * 100 / sum_lines
    report["overall_coverage"] = overall_coverage

    if overall_coverage < threshold:
        logger.warn("Overall coverage is below %2d%%: %2d%%", threshold, overall_coverage)
        coverage_too_low = True
    else:
        logger.info("Overall coverage is %2d%%", overall_coverage)

    project.write_report("coverage.json", render_report(report))

    write_summary_report(coverage, project, modules)

    if coverage_too_low and project.get_property("coverage_break_build"):
        raise BuildFailedException("Test coverage for at least one module is below %d%%", threshold)


def reimport_source_modules(project, logger):
    if project.get_property("coverage_reload_modules"):
        modules = discover_modules_to_cover(project)
        for module in modules:
            logger.debug("Reloading module %s", module)
            if module in sys.modules:
                imp.reload(sys.modules[module])


def build_module_report(coverage_module, module):
    analysis_result = coverage_module.analysis(module)

    lines_total = len(analysis_result[1])
    lines_not_covered = len(analysis_result[2])
    lines_covered = lines_total - lines_not_covered

    if lines_total == 0:
        code_coverage = 100
    elif lines_covered == 0:
        code_coverage = 0
    else:
        code_coverage = lines_covered * 100 / lines_total

    return (lines_total, analysis_result[1],
            lines_not_covered, analysis_result[2],
            code_coverage)


def write_summary_report(coverage_module, project, modules):
    summary = StringIO()
    coverage_module.report(modules, file=summary)
    project.write_report("coverage", summary.getvalue())
    summary.close()


def discover_modules_to_cover(project):
    return discover_modules(project.expand_path("$dir_source_main_python"))

########NEW FILE########
__FILENAME__ = cram_plugin
# cram Plugin for PyBuilder
#
# Copyright 2011-2014 PyBuilder Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    Plugin for Cram, a functional testing framework for command line
    applications.

    https://pypi.python.org/pypi/cram
"""

__author__ = 'Valentin Haenel'

import os

from pybuilder.core import after, task, init, use_plugin, depends, description
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, discover_files_matching, read_file
from pybuilder.plugins.python.python_plugin_helper import execute_command


use_plugin("python.core")


@init
def initialize_cram_plugin(project):
    project.build_depends_on("cram")
    project.set_property_if_unset('dir_source_cmdlinetest', "src/cmdlinetest")
    project.set_property("cram_test_file_glob", '*.t')


@after("prepare")
def assert_cram_is_executable(logger):
    """ Asserts that the cram script is executable. """
    logger.debug("Checking if cram is executable.")

    assert_can_execute(command_and_arguments=["cram", "--version"],
                       prerequisite="cram",
                       caller="plugin python.cram")


def _cram_command_for(project):
    command_and_arguments = ["cram"]
    if project.get_property("verbose"):
        command_and_arguments.append('--verbose')
    return command_and_arguments


def _find_files(project):
    cram_dir = project.get_property('dir_source_cmdlinetest')
    cram_test_file_glob = project.get_property("cram_test_file_glob")
    cram_files = discover_files_matching(cram_dir, cram_test_file_glob)
    return cram_files


def _report_file(project):
    return project.expand_path("$dir_reports/{0}".format('cram.err'))


def _prepend_path(env, variable, value):
    env[variable] = value + ":" + env.get(variable, '')


@task
@depends("prepare")
@description("Run Cram command line tests")
def run_cram_tests(project, logger):
    logger.info("Running Cram command line tests")

    command_and_arguments = _cram_command_for(project)
    command_and_arguments.extend(_find_files(project))
    report_file = _report_file(project)

    env = os.environ.copy()
    source_dir = project.expand_path("$dir_source_main_python")
    _prepend_path(env, "PYTHONPATH", source_dir)
    script_dir = project.expand_path('$dir_source_main_scripts')
    _prepend_path(env, "PATH", script_dir)

    execution_result = execute_command(command_and_arguments,
                                       report_file,
                                       env=env,
                                       error_file_name=report_file
                                       ), report_file

    report = read_file(report_file)
    result = report[-1][2:].strip()

    if execution_result[0] != 0:
        logger.error("Cram tests failed!")
        if project.get_property("verbose"):
            for line in report:
                logger.error(line.rstrip())
        else:
            logger.error(result)
        logger.error("See: '{0}' for details".format(report_file))
        raise BuildFailedException("Cram tests failed!")
    else:
        logger.info("Cram tests were fine")
        logger.info(result)


@task
def run_integration_tests(project, logger):
    run_cram_tests(project, logger)

########NEW FILE########
__FILENAME__ = distutils_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import string
import subprocess
import sys

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

from pybuilder.core import after, before, use_plugin, init
from pybuilder.errors import BuildFailedException
from pybuilder.utils import as_list

from .setuptools_plugin_helper import build_dependency_version_string

use_plugin("python.core")

DATA_FILES_PROPERTY = "distutils_data_files"
SETUP_TEMPLATE = string.Template("""#!/usr/bin/env python
$remove_hardlink_capabilities_for_shared_filesystems
from $module import setup

if __name__ == '__main__':
    setup(
          name = '$name',
          version = '$version',
          description = '''$summary''',
          long_description = '''$description''',
          author = "$author",
          author_email = "$author_email",
          license = '$license',
          url = '$url',
          scripts = $scripts,
          packages = $packages,
          py_modules = $modules,
          classifiers = $classifiers,
          $data_files   #  data files
          $package_data   # package data
          $dependencies
          $dependency_links
          zip_safe=True
    )
""")


def default(value, default=""):
    if value is None:
        return default
    return value


@init
def initialize_distutils_plugin(project):
    project.set_property_if_unset("distutils_commands", ["sdist", "bdist_dumb"])
    # Workaround for http://bugs.python.org/issue8876 , unable to build a bdist
    # on a filesystem that does not support hardlinks
    project.set_property_if_unset("distutils_issue8876_workaround_enabled", False)
    project.set_property_if_unset("distutils_classifiers", [
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python"
    ])
    project.set_property_if_unset("distutils_use_setuptools", True)


@after("package")
def write_setup_script(project, logger):
    setup_script = project.expand_path("$dir_dist/setup.py")
    logger.info("Writing setup.py as %s", setup_script)

    with open(setup_script, "w") as setup_file:
        setup_file.write(render_setup_script(project))

    os.chmod(setup_script, 0o755)


def render_setup_script(project):
    author = ", ".join(map(lambda a: a.name, project.authors))
    author_email = ", ".join(map(lambda a: a.email, project.authors))

    template_values = {
        "module": "setuptools" if project.get_property("distutils_use_setuptools") else "distutils.core",
        "name": project.name,
        "version": project.version,
        "summary": default(project.summary),
        "description": default(project.description),
        "author": author,
        "author_email": author_email,
        "license": default(project.license),
        "url": default(project.url),
        "scripts": build_scripts_string(project),
        "packages": str([package for package in project.list_packages()]),
        "modules": str([module for module in project.list_modules()]),
        "classifiers": project.get_property("distutils_classifiers"),
        "data_files": build_data_files_string(project),
        "package_data": build_package_data_string(project),
        "dependencies": build_install_dependencies_string(project),
        "dependency_links": build_dependency_links_string(project),
        "remove_hardlink_capabilities_for_shared_filesystems": (
            "import os\ndel os.link"
            if project.get_property("distutils_issue8876_workaround_enabled")
            else "")
    }

    return SETUP_TEMPLATE.substitute(template_values)


@after("package")
def write_manifest_file(project, logger):
    if len(project.manifest_included_files) == 0:
        logger.debug("No data to write into MANIFEST.in")
        return

    logger.debug("Files included in MANIFEST.in: %s" %
                 project.manifest_included_files)

    manifest_filename = project.expand_path("$dir_dist/MANIFEST.in")
    logger.info("Writing MANIFEST.in as %s", manifest_filename)

    with open(manifest_filename, "w") as manifest_file:
        manifest_file.write(render_manifest_file(project))

    os.chmod(manifest_filename, 0o664)


def render_manifest_file(project):
    manifest_content = StringIO()

    for included_file in project.manifest_included_files:
        manifest_content.write("include %s\n" % included_file)

    return manifest_content.getvalue()


@before("publish")
def build_binary_distribution(project, logger):
    reports_dir = project.expand_path("$dir_reports/distutils")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)

    setup_script = project.expand_path("$dir_dist/setup.py")

    logger.info("Building binary distribution in %s",
                project.expand_path("$dir_dist"))

    commands = as_list(project.get_property("distutils_commands"))

    for command in commands:
        logger.debug("Executing distutils command %s", command)
        with open(os.path.join(reports_dir, command), "w") as output_file:
            process = subprocess.Popen((sys.executable, setup_script, command),
                                       cwd=project.expand_path("$dir_dist"),
                                       stdout=output_file,
                                       stderr=output_file,
                                       shell=False)
            return_code = process.wait()
            if return_code != 0:
                raise BuildFailedException(
                    "Error while executing setup command %s", command)


def build_install_dependencies_string(project):
    dependencies = [
        dependency for dependency in project.dependencies if not dependency.url]
    if not dependencies:
        return ""

    def format_single_dependency(dependency):
        return '"%s%s"' % (dependency.name, build_dependency_version_string(dependency))

    result = "install_requires = [ "
    result += ", ".join(map(format_single_dependency, dependencies))
    result += " ],"
    return result


def build_dependency_links_string(project):
    dependency_links = [
        dependency for dependency in project.dependencies if dependency.url]
    if not dependency_links:
        return ""

    def format_single_dependency(dependency):
        return '"%s"' % dependency.url

    result = "dependency_links = [ "
    result += ", ".join(map(format_single_dependency, dependency_links))
    result += " ],"
    return result


def build_scripts_string(project):
    scripts = [script for script in project.list_scripts()]

    scripts_dir = project.get_property("dir_dist_scripts")
    if scripts_dir:
        scripts = map(lambda s: os.path.join(scripts_dir, s), scripts)

    return str(scripts)


def build_data_files_string(project):
    data_files = project.files_to_install

    if not len(data_files):
        return ""

    return "data_files = %s," % str(data_files)


def build_package_data_string(project):
    package_data = project.package_data
    if package_data == {}:
        return ""
    package_data_string = "package_data = {"

    sorted_keys = sorted(package_data.keys())
    last_element = sorted_keys[-1]

    for key in sorted_keys:
        package_data_string += "'%s': %s" % (key, str(package_data[key]))

        if key is not last_element:
            package_data_string += ", "

    package_data_string += "},"
    return package_data_string

########NEW FILE########
__FILENAME__ = django_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import sys

from pybuilder.core import use_plugin, task
from pybuilder.errors import PyBuilderException

use_plugin("python.core")


@task
def django_run_server(project, logger):
    django_module_name = project.get_mandatory_property("django_module")

    logger.info("Running Django development server for %s", django_module_name)

    settings_module_name = "{0}.settings".format(django_module_name)
    sys.path.append(project.expand_path("$dir_source_main_python"))
    try:
        __import__(settings_module_name)
    except ImportError as e:
        raise PyBuilderException("Error when importing settings module: " + str(e))

    from django import VERSION as DJANGO_VERSION
    if DJANGO_VERSION < (1, 4, 0):
        from django.core.management import execute_manager
        execute_manager(sys.modules[settings_module_name], ["", "runserver"])
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module_name)
        from django.core.management import execute_from_command_line
        execute_from_command_line(["", "runserver"])

########NEW FILE########
__FILENAME__ = flake8_plugin
#   Flake8 Plugin for PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
    Plugin for Tarek Ziade's flake8 script.
    Flake8 is a wrapper around: PyFlakes, pep8, Ned's McCabe script.

    https://bitbucket.org/tarek/flake8
"""

__author__ = 'Michael Gruber'

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder


use_plugin("python.core")


@init
def initialize_flake8_plugin(project):
    project.build_depends_on("flake8")
    project.set_property("flake8_break_build", False)
    project.set_property("flake8_max_line_length", 120)
    project.set_property("flake8_exclude_patterns", None)
    project.set_property("flake8_include_test_sources", False)
    project.set_property("flake8_include_scripts", False)


@after("prepare")
def assert_flake8_is_executable(logger):
    """ Asserts that the flake8 script is executable. """
    logger.debug("Checking if flake8 is executable.")

    assert_can_execute(command_and_arguments=["flake8", "--version"],
                       prerequisite="flake8",
                       caller="plugin python.flake8")


@task
@depends("prepare")
def analyze(project, logger):
    """ Applies the flake8 script to the sources of the given project. """
    logger.info("Executing flake8 on project sources.")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("flake8_verbose_output", verbose)

    command = ExternalCommandBuilder('flake8', project)
    command.use_argument('--ignore={0}').formatted_with_truthy_property('flake8_ignore')
    command.use_argument('--max-line-length={0}').formatted_with_property('flake8_max_line_length')
    command.use_argument('--exclude={0}').formatted_with_truthy_property('flake8_exclude_patterns')

    include_test_sources = project.get_property("flake8_include_test_sources")
    include_scripts = project.get_property("flake8_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts)

    count_of_warnings = len(result.report_lines)
    count_of_errors = len(result.error_report_lines)

    if count_of_errors > 0:
        logger.error('Errors while running flake8, see {0}'.format(result.error_report_file))

    if count_of_warnings > 0:
        if project.get_property("flake8_break_build"):
            error_message = "flake8 found {0} warning(s)".format(count_of_warnings)
            raise BuildFailedException(error_message)
        else:
            logger.warn("flake8 found %d warning(s).", count_of_warnings)

########NEW FILE########
__FILENAME__ = frosted_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
    Frosted is a fork of pyflakes (originally created by Phil Frost) that aims
    at more open contribution from the outside public, a smaller more
    maintainable code base, and a better Python checker for all.

    https://github.com/timothycrosley/frosted
"""

__author__ = 'Maximilien Riehl'

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder


use_plugin("python.core")


@init
def initialize_frosted_plugin(project):
    project.build_depends_on("frosted")
    project.set_property("frosted_break_build", False)
    project.set_property("frosted_include_test_sources", False)
    project.set_property("frosted_include_scripts", False)


@after("prepare")
def assert_frosted_is_executable(logger):
    """ Asserts that the frosted script is executable. """
    logger.debug("Checking if frosted is executable.")

    assert_can_execute(command_and_arguments=["frosted", "--version"],
                       prerequisite="frosted (PyPI)",
                       caller="plugin python.frosted")


@task
@depends("prepare")
def analyze(project, logger):
    """ Applies the frosted script to the sources of the given project. """
    logger.info("Executing frosted on project sources.")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("frosted_verbose_output", verbose)

    command = ExternalCommandBuilder('frosted', project)
    for ignored_error_code in project.get_property('frosted_ignore', []):
        command.use_argument('--ignore={0}'.format(ignored_error_code))

    include_test_sources = project.get_property("frosted_include_test_sources")
    include_scripts = project.get_property("frosted_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts)

    count_of_warnings = len(result.report_lines)
    count_of_errors = len(result.error_report_lines)

    if count_of_errors > 0:
        logger.error('Errors while running frosted, see {0}'.format(result.error_report_file))

    if count_of_warnings > 0:
        if project.get_property("frosted_break_build"):
            error_message = "frosted found {0} warning(s)".format(count_of_warnings)
            raise BuildFailedException(error_message)
        else:
            logger.warn("frosted found %d warning(s).", count_of_warnings)

########NEW FILE########
__FILENAME__ = install_dependencies_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import print_function

__author__ = "Alexander Metzner"

from pybuilder.core import before, after, task, description, use_plugin, init
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, execute_command, mkdir
from pybuilder.plugins.python.setuptools_plugin_helper import build_dependency_version_string
from pybuilder.terminal import print_file_content
use_plugin("core")


@init
def initialized_install_dependencies_plugin(project):
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")
    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_upgrade", False)


@after("prepare")
def check_pip_available(logger):
    logger.debug("Checking if pip is available")
    assert_can_execute("pip", "pip", "plugin python.install_dependencies")


@task
@description("Installs all (both runtime and build) dependencies specified in the build descriptor")
def install_dependencies(logger, project):
    logger.info("Installing all dependencies")
    install_build_dependencies(logger, project)
    install_runtime_dependencies(logger, project)


@task
@description("Installs all build dependencies specified in the build descriptor")
def install_build_dependencies(logger, project):
    logger.info("Installing build dependencies")
    for dependency in project.build_dependencies:
        install_dependency(logger, project, dependency)


@task
@description("Installs all runtime dependencies specified in the build descriptor")
def install_runtime_dependencies(logger, project):
    logger.info("Installing runtime dependencies")
    for dependency in project.dependencies:
        install_dependency(logger, project, dependency)


@task
@description("Displays all dependencies the project requires")
def list_dependencies(project):
    print("\n".join(map(lambda d: "{0}".format(as_pip_argument(d)), project.build_dependencies + project.dependencies)))


@before((install_build_dependencies, install_runtime_dependencies, install_dependencies), only_once=True)
def create_install_log_directory(logger, project):
    log_dir = project.expand("$dir_install_logs")

    logger.debug("Creating log directory '%s'", log_dir)
    mkdir(log_dir)


def install_dependency(logger, project, dependency):
    logger.info("Installing dependency '%s'%s", dependency.name, " from %s" % dependency.url if dependency.url else "")
    log_file = project.expand_path("$dir_install_logs", dependency.name)

    pip_command_line = "pip install {0}'{1}'".format(build_pip_install_options(project), as_pip_argument(dependency))
    exit_code = execute_command(pip_command_line, log_file, shell=True)
    if exit_code != 0:
        if project.get_property("verbose"):
            print_file_content(log_file)
            raise BuildFailedException("Unable to install dependency '%s'.", dependency.name)
        else:
            raise BuildFailedException("Unable to install dependency '%s'. See %s for details.",
                                       dependency.name,
                                       log_file)


def build_pip_install_options(project):
    options = []
    if project.get_property("install_dependencies_index_url"):
        options.append("--index-url " + project.get_property("install_dependencies_index_url"))
        if project.get_property("install_dependencies_extra_index_url"):
            options.append("--extra-index-url " + project.get_property("install_dependencies_extra_index_url"))

    if project.get_property("install_dependencies_upgrade"):
        options.append("--upgrade")

    result = " ".join(options)
    if result:
        result += " "
    return result


def as_pip_argument(dependency):
    if dependency.url:
        return dependency.url
    return "{0}{1}".format(dependency.name, build_dependency_version_string(dependency))

########NEW FILE########
__FILENAME__ = integrationtest_plugin
# -*- coding: utf-8 -*-
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import multiprocessing
import os
import sys

try:
    from queue import Empty
except ImportError:
    from Queue import Empty


from pybuilder.core import init, use_plugin, task, description
from pybuilder.utils import discover_files_matching, execute_command, Timer, read_file
from pybuilder.terminal import print_text_line, print_file_content, print_text
from pybuilder.plugins.python.test_plugin_helper import ReportsProcessor
from pybuilder.terminal import styled_text, fg, GREEN, MAGENTA, GREY

use_plugin("python.core")


@init
def init_test_source_directory(project):
    project.set_property_if_unset(
        "dir_source_integrationtest_python", "src/integrationtest/python")
    project.set_property_if_unset("integrationtest_file_glob", "*_tests.py")
    project.set_property_if_unset("integrationtest_file_suffix", None)  # deprecated, use integrationtest_file_glob.
    project.set_property_if_unset("integrationtest_additional_environment", {})
    project.set_property_if_unset("integrationtest_inherit_environment", False)


@task
@description("Runs integration tests based on Python's unittest module")
def run_integration_tests(project, logger):
    if not project.get_property("integrationtest_parallel"):
        reports, total_time = run_integration_tests_sequentially(
            project, logger)
    else:
        reports, total_time = run_integration_tests_in_parallel(
            project, logger)

    reports_processor = ReportsProcessor(project, logger)
    reports_processor.process_reports(reports, total_time)
    reports_processor.report_to_ci_server(project)
    reports_processor.write_report_and_ensure_all_tests_passed()


def run_integration_tests_sequentially(project, logger):
    logger.debug("Running integration tests sequentially")
    reports_dir = prepare_reports_directory(project)

    report_items = []

    total_time = Timer.start()

    for test in discover_integration_tests_for_project(project, logger):
        report_item = run_single_test(logger, project, reports_dir, test)
        report_items.append(report_item)

    total_time.stop()

    return report_items, total_time


def run_integration_tests_in_parallel(project, logger):
    logger.info("Running integration tests in parallel")
    tests = multiprocessing.Queue()
    reports = ConsumingQueue()
    reports_dir = prepare_reports_directory(project)
    cpu_scaling_factor = project.get_property(
        'integrationtest_cpu_scaling_factor', 4)
    cpu_count = multiprocessing.cpu_count()
    worker_pool_size = cpu_count * cpu_scaling_factor
    logger.debug(
        "Running integration tests in parallel with {0} processes ({1} cpus found)".format(
            worker_pool_size,
            cpu_count))

    total_time = Timer.start()
    # fail OSX has no sem_getvalue() implementation so no queue size
    total_tests_count = 0
    for test in discover_integration_tests_for_project(project, logger):
        tests.put(test)
        total_tests_count += 1
    progress = TaskPoolProgress(total_tests_count, worker_pool_size)

    def pick_and_run_tests_then_report(tests, reports, reports_dir, logger, project):
        while True:
            try:
                test = tests.get_nowait()
                report_item = run_single_test(
                    logger, project, reports_dir, test, not progress.can_be_displayed)
                reports.put(report_item)
            except Empty:
                break
            except Exception as e:
                logger.error("Failed to run test %r : %s" % (test, str(e)))
                failed_report = {
                    "test": test,
                    "test_file": test,
                    "time": 0,
                    "success": False,
                    "exception": str(e)
                }
                reports.put(failed_report)
                continue

    pool = []
    for i in range(worker_pool_size):
        p = multiprocessing.Process(
            target=pick_and_run_tests_then_report, args=(tests, reports, reports_dir, logger, project))
        pool.append(p)
        p.start()

    import time
    while not progress.is_finished:
        reports.consume_available_items()
        finished_tests_count = reports.size
        progress.update(finished_tests_count)
        progress.render_to_terminal()
        time.sleep(1)

    progress.mark_as_finished()

    total_time.stop()

    return reports.items, total_time


def discover_integration_tests(source_path, suffix=".py"):
    return discover_files_matching(source_path, "*{0}".format(suffix))


def discover_integration_tests_matching(source_path, file_glob):
    return discover_files_matching(source_path, file_glob)


def discover_integration_tests_for_project(project, logger=None):
    integrationtest_source_dir = project.expand_path(
        "$dir_source_integrationtest_python")
    integrationtest_suffix = project.get_property("integrationtest_file_suffix")
    if integrationtest_suffix is not None:
        if logger is not None:
            logger.warn(
                "integrationtest_file_suffix is deprecated, please use integrationtest_file_glob"
            )
        project.set_property("integrationtest_file_glob", "*{0}".format(integrationtest_suffix))
    integrationtest_glob = project.expand("$integrationtest_file_glob")
    return discover_files_matching(integrationtest_source_dir, integrationtest_glob)


def add_additional_environment_keys(env, project):
    additional_environment = project.get_property(
        "integrationtest_additional_environment", {})
    if not isinstance(additional_environment, dict):
        raise ValueError("Additional environment %r is not a map." %
                         additional_environment)
    for key in additional_environment:
        env[key] = additional_environment[key]


def inherit_environment(env, project):
    if project.get_property("integrationtest_inherit_environment", False):
        for key in os.environ:
            if key not in env:
                env[key] = os.environ[key]


def prepare_environment(project):
    env = {
        "PYTHONPATH": os.pathsep.join((project.expand_path("$dir_dist"),
                                       project.expand_path("$dir_source_integrationtest_python")))
    }

    inherit_environment(env, project)

    add_additional_environment_keys(env, project)

    return env


def prepare_reports_directory(project):
    reports_dir = project.expand_path("$dir_reports/integrationtests")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir


def run_single_test(logger, project, reports_dir, test, output_test_names=True):
    additional_integrationtest_commandline_text = project.get_property("integrationtest_additional_commandline", "")

    if additional_integrationtest_commandline_text:
        additional_integrationtest_commandline = tuple(additional_integrationtest_commandline_text.split(" "))
    else:
        additional_integrationtest_commandline = ()

    name, _ = os.path.splitext(os.path.basename(test))

    if output_test_names:
        logger.info("Running integration test %s", name)

    env = prepare_environment(project)
    test_time = Timer.start()
    command_and_arguments = (sys.executable, test)
    command_and_arguments += additional_integrationtest_commandline

    report_file_name = os.path.join(reports_dir, name)
    error_file_name = report_file_name + ".err"
    return_code = execute_command(
        command_and_arguments, report_file_name, env, error_file_name=error_file_name)
    test_time.stop()
    report_item = {
        "test": name,
        "test_file": test,
        "time": test_time.get_millis(),
        "success": True
    }
    if return_code != 0:

        logger.error("Integration test failed: %s", test)
        report_item["success"] = False

        if project.get_property("verbose"):
            print_file_content(report_file_name)
            print_text_line()
            print_file_content(error_file_name)
            report_item['exception'] = ''.join(read_file(error_file_name)).replace('\'', '')

    return report_item


class ConsumingQueue(object):

    def __init__(self):
        self._items = []
        self._queue = multiprocessing.Queue()

    def consume_available_items(self):
        try:
            while True:
                item = self.get_nowait()
                self._items.append(item)
        except Empty:
            pass

    def put(self, *args, **kwargs):
        return self._queue.put(*args, **kwargs)

    def get_nowait(self, *args, **kwargs):
        return self._queue.get_nowait(*args, **kwargs)

    @property
    def items(self):
        return self._items

    @property
    def size(self):
        return len(self.items)


class TaskPoolProgress(object):

    """
    Class that renders progress for a set of tasks run in parallel.
    The progress is based on
    * the amount of total tasks, which must be static
    * the amount of workers running in parallel.
    The bar can be updated with the amount of tasks that have been successfully
    executed and render its progress.
    """

    BACKSPACE = "\b"
    FINISHED_SYMBOL = "-"
    PENDING_SYMBOL = "/"
    WAITING_SYMBOL = "|"
    PACMAN_FORWARD = "ᗧ"
    NO_PACMAN = ""

    def __init__(self, total_tasks_count, workers_count):
        self.total_tasks_count = total_tasks_count
        self.finished_tasks_count = 0
        self.workers_count = workers_count
        self.last_render_length = 0

    def update(self, finished_tasks_count):
        self.finished_tasks_count = finished_tasks_count

    def render(self):
        pacman = self.pacman_symbol
        finished_tests_progress = styled_text(
            self.FINISHED_SYMBOL * self.finished_tasks_count, fg(GREEN))
        running_tasks_count = self.running_tasks_count
        running_tests_progress = styled_text(
            self.PENDING_SYMBOL * running_tasks_count, fg(MAGENTA))
        waiting_tasks_count = self.waiting_tasks_count
        waiting_tasks_progress = styled_text(
            self.WAITING_SYMBOL * waiting_tasks_count, fg(GREY))
        trailing_space = ' ' if not pacman else ''

        return "[%s%s%s%s]%s" % (finished_tests_progress, pacman, running_tests_progress, waiting_tasks_progress, trailing_space)

    def render_to_terminal(self):
        if self.can_be_displayed:
            text_to_render = self.render()
            characters_to_be_erased = self.last_render_length
            self.last_render_length = len(text_to_render)
            text_to_render = "%s%s" % (characters_to_be_erased * self.BACKSPACE, text_to_render)
            print_text(text_to_render, flush=True)

    def mark_as_finished(self):
        if self.can_be_displayed:
            print_text_line()

    @property
    def pacman_symbol(self):
        if self.is_finished:
            return self.NO_PACMAN
        else:
            return self.PACMAN_FORWARD

    @property
    def running_tasks_count(self):
        pending_tasks = (self.total_tasks_count - self.finished_tasks_count)
        if pending_tasks > self.workers_count:
            return self.workers_count
        return pending_tasks

    @property
    def waiting_tasks_count(self):
        return self.total_tasks_count - self.finished_tasks_count - self.running_tasks_count

    @property
    def is_finished(self):
        return self.finished_tasks_count == self.total_tasks_count

    @property
    def can_be_displayed(self):
        if sys.stdout.isatty():
            return True
        return False

########NEW FILE########
__FILENAME__ = pep8_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from pybuilder.core import use_plugin, task, after, init
from pybuilder.utils import assert_can_execute, read_file
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files

use_plugin("python.core")


@init
def init_pep8_properties(project):
    project.build_depends_on("pep8")


@after("prepare")
def check_pep8_available(logger):
    logger.debug("Checking availability of pep8")
    assert_can_execute(("pep8", ), "pep8", "plugin python.pep8")


@task
def analyze(project, logger):
    logger.info("Executing pep8 on project sources")
    _, report_file = execute_tool_on_source_files(project, "pep8", ["pep8"])

    reports = read_file(report_file)

    if len(reports) > 0:
        logger.warn("Found %d warning%s produced by pep8",
                    len(reports), "" if len(reports) == 1 else "s")

########NEW FILE########
__FILENAME__ = pycharm_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import string

from pybuilder.core import task, description

PROJECT_TEMPLATE = string.Template("""<?xml version="1.0" encoding="UTF-8"?>
<!-- This file has been generated by the PyBuilder PyCharm Plugin -->

<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$$MODULE_DIR$$">
      <sourceFolder url="file://$$MODULE_DIR$$/${source_dir}" isTestSource="false" />
      <excludeFolder url="file://$$MODULE_DIR$$/target" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
  <component name="PyDocumentationSettings">
    <option name="myDocStringFormat" value="Plain" />
  </component>
  <component name="TestRunnerService">
    <option name="projectConfiguration" value="Unittests" />
    <option name="PROJECT_TEST_RUNNER" value="Unittests" />
  </component>
</module>
""")


def _ensure_directory_present(directory):
    if os.path.exists(directory):
        return

    os.makedirs(directory)


@task
@description("Generates PyCharm development files")
def pycharm_generate(project, logger):
    logger.info("Generating PyCharm project files.")

    pycharm_directory = project.expand_path(".idea")
    project_file_name = "{0}.iml".format(project.name)

    _ensure_directory_present(pycharm_directory)

    project_metadata = PROJECT_TEMPLATE.substitute({
        "source_dir": project.get_property("dir_source_main_python")
    })

    project_file_path = os.path.join(pycharm_directory, project_file_name)

    with open(project_file_path, "w") as project_file:
        project_file.write(project_metadata)

########NEW FILE########
__FILENAME__ = pychecker_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import re

from pybuilder.core import use_plugin, after, init, task
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, read_file, render_report
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_modules


DEFAULT_PYCHECKER_ARGUMENTS = ["-Q"]
PYCHECKER_WARNING_PATTERN = re.compile(r'^(.+?):([0-9]+): (.+)$')


use_plugin("python.core")
use_plugin("analysis")


@init
def init_pychecker(project):
    project.set_property_if_unset("pychecker_break_build", True)
    project.set_property_if_unset("pychecker_break_build_threshold", 0)


@after("prepare")
def check_pychecker_available(logger):
    logger.debug("Checking availability of pychecker")
    assert_can_execute(("pychecker", ), "pychecker", "plugin python.pychecker")


def build_command_line(project):
    command_line = ["pychecker"]
    command_args = project.get_property("pychecker_args")

    if command_args:
        command_line += command_args
    else:
        command_line += DEFAULT_PYCHECKER_ARGUMENTS

    return command_line


@task("analyze")
def execute_pychecker(project, logger):
    command_line = build_command_line(project)
    logger.info("Executing pychecker on project sources: %s" % (' '.join(command_line)))

    _, report_file = execute_tool_on_modules(project, "pychecker", command_line, True)

    warnings = read_file(report_file)

    report = parse_pychecker_output(project, warnings)
    project.write_report("pychecker.json", render_report(report.to_json_dict()))

    if len(warnings) != 0:
        logger.warn("Found %d warning%s produced by pychecker. See %s for details.",
                    len(warnings),
                    "s" if len(warnings) != 1 else "",
                    report_file)

        threshold = project.get_property("pychecker_break_build_threshold")

        if project.get_property("pychecker_break_build") and len(warnings) > threshold:
            raise BuildFailedException("Found warnings produced by pychecker")


class PycheckerWarning(object):
    def __init__(self, message, line_number):
        self.message = message
        self.line_number = int(line_number)

    def to_json_dict(self):
        return {"message": self.message, "line_number": self.line_number}


class PycheckerModuleReport(object):
    def __init__(self, name):
        self.name = name
        self.warnings = []

    def add_warning(self, warning):
        self.warnings.append(warning)

    def to_json_dict(self):
        return {
            "name": self.name,
            "warnings": list(map(lambda w: w.to_json_dict(), self.warnings))
        }


class PycheckerReport(object):
    def __init__(self):
        self.module_reports = []

    def get_module_report(self, module):
        for module_report in self.module_reports:
            if module_report.name == module:
                return module_report

        module_report = PycheckerModuleReport(module)
        self.add_module_report(module_report)
        return module_report

    def add_module_report(self, module_report):
        self.module_reports.append(module_report)

    def to_json_dict(self):
        return {"modules": list(map(lambda m: m.to_json_dict(), self.module_reports))}


def parse_pychecker_output(project, warnings):
    report = PycheckerReport()

    sources_base_dir = project.expand_path("$dir_source_main_python")

    for warning in warnings:
        match = PYCHECKER_WARNING_PATTERN.match(warning)
        if not match:
            continue
        file_name = match.group(1)
        line_number = match.group(2)
        message = match.group(3)
        module = file_name.replace(sources_base_dir, "")[1:].replace(os.sep, ".")
        report.get_module_report(module).add_warning(PycheckerWarning(message, line_number))

    return report

########NEW FILE########
__FILENAME__ = pydev_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import string

from pybuilder.core import init, task, description

_DOT_PROJECT_TEMPLATE = string.Template("""<?xml version="1.0" encoding="UTF-8"?>

<!-- This file has been generated by the PyBuilder Pydev Plugin -->

<projectDescription>
    <name>${project_name}</name>
    <comment></comment>
    <projects>
    </projects>
    <buildSpec>
        <buildCommand>
            <name>org.python.pydev.PyDevBuilder</name>
            <arguments>
            </arguments>
        </buildCommand>
    </buildSpec>
    <natures>
        <nature>org.python.pydev.pythonNature</nature>
    </natures>
</projectDescription>
""")

_DOT_PYDEVPROJECT_PATH_LINE_TEMPLATE = string.Template("\t\t<path>/$project_name/$path</path>\n")

_DOT_PYDEVPROJECT_TEMPLATE = string.Template("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?eclipse-pydev version="1.0"?>

<!-- This file has been generated by the PyBuilder Pydev Plugin -->

<pydev_project>
    <pydev_property name="org.python.pydev.PYTHON_PROJECT_INTERPRETER">${interpreter}</pydev_property>
    <pydev_property name="org.python.pydev.PYTHON_PROJECT_VERSION">${version}</pydev_property>
    <pydev_pathproperty name="org.python.pydev.PROJECT_SOURCE_PATH">
$paths
    </pydev_pathproperty>
</pydev_project>
""")


@init
def init_pydev_plugin(project):
    project.set_property_if_unset("pydev_interpreter_name", "Default")
    project.set_property_if_unset("pydev_version", "python 2.7")


@task
@description("Generates eclipse-pydev development files")
def pydev_generate(project, logger):
    logger.info("Generating Eclipse/ Pydev project files.")

    paths = []
    add_property_value_if_present(paths, project, "dir_source_main_python")
    add_property_value_if_present(paths, project, "dir_source_main_scripts")
    add_property_value_if_present(paths, project, "dir_source_unittest_python")
    add_property_value_if_present(paths, project, "dir_source_integrationtest_python")

    paths_string = ""
    for path in paths:
        if os.path.exists(path):
            placeholders = {"project_name": project.name,
                            "path": path}
            paths_string += _DOT_PYDEVPROJECT_PATH_LINE_TEMPLATE.substitute(placeholders)

    values = {
        "project_name": project.name,
        "interpreter": project.expand("$pydev_interpreter_name"),
        "version": project.expand("$pydev_version"),
        "paths": paths_string
    }

    with open(project.expand_path(".project"), "w") as project_file:
        logger.debug("Writing %s", project_file.name)
        project_file.write(_DOT_PROJECT_TEMPLATE.substitute(values))

    with open(project.expand_path(".pydevproject"), "w") as pydevproject_file:
        logger.debug("Writing %s", pydevproject_file.name)
        pydevproject_file.write(_DOT_PYDEVPROJECT_TEMPLATE.substitute(values))


def add_property_value_if_present(list, project, property_name):
    if project.has_property(property_name):
        list.append(project.get_property(property_name))

########NEW FILE########
__FILENAME__ = pyfix_plugin_impl
__author__ = "Alexander Metzner"


import sys

from pyfix.testcollector import TestCollector
from pyfix.testrunner import TestRunner, TestRunListener

from pybuilder.errors import BuildFailedException
from pybuilder.utils import discover_modules_matching, render_report


def run_unit_tests(project, logger):
    sys.path.append(project.expand_path("$dir_source_main_python"))
    test_dir = project.expand_path("$dir_source_unittest_python")
    sys.path.append(test_dir)

    pyfix_unittest_file_suffix = project.get_property("pyfix_unittest_file_suffix")
    if pyfix_unittest_file_suffix is not None:
        logger.warn("pyfix_unittest_file_suffix is deprecated, please use pyfix_unittest_module_glob")
        module_glob = "*{0}".format(pyfix_unittest_file_suffix)
        if module_glob.endswith(".py"):
            module_glob = module_glob[:-3]
        project.set_property("pyfix_unittest_module_glob", module_glob)
    else:
        module_glob = project.get_property("pyfix_unittest_module_glob")

    logger.info("Executing pyfix unittest Python modules in %s", test_dir)
    logger.debug("Including files matching '%s.py'", module_glob)

    try:
        result = execute_tests_matching(logger, test_dir, module_glob)
        if result.number_of_tests_executed == 0:
            logger.warn("No pyfix executed")
        else:
            logger.info("Executed %d pyfix unittests", result.number_of_tests_executed)

        write_report(project, result)

        if not result.success:
            raise BuildFailedException("%d pyfix unittests failed", result.number_of_failures)

        logger.info("All pyfix unittests passed")
    except ImportError as e:
        logger.error("Error importing pyfix unittest: %s", e)
        raise BuildFailedException("Unable to execute unit tests.")


class TestListener(TestRunListener):
    def __init__(self, logger):
        self._logger = logger

    def before_suite(self, test_definitions):
        self._logger.info("Running %d pyfix tests", len(test_definitions))

    def before_test(self, test_definition):
        self._logger.debug("Running pyfix test '%s'", test_definition.name)

    def after_test(self, test_results):
        for test_result in test_results:
            if not test_result.success:
                self._logger.warn("Test '%s' failed: %s", test_result.test_definition.name, test_result.message)


def import_modules(test_modules):
    return [__import__(module_name) for module_name in test_modules]


def execute_tests(logger, test_source, suffix):
    return execute_tests_matching(logger, test_source, "*{0}".format(suffix))


def execute_tests_matching(logger, test_source, module_glob):
    test_module_names = discover_modules_matching(test_source, module_glob)
    test_modules = import_modules(test_module_names)

    test_collector = TestCollector()

    for test_module in test_modules:
        test_collector.collect_tests(test_module)

    test_runner = TestRunner()
    test_runner.add_test_run_listener(TestListener(logger))
    return test_runner.run_tests(test_collector.test_suite)


def write_report(project, test_results):
    report = {"tests-run": test_results.number_of_tests_executed,
              "time_in_millis": test_results.execution_time,
              "failures": []}
    for test_result in test_results.test_results:
        if test_result.success:
            continue
        report["failures"].append({"test": test_result.test_definition.name, "message": test_result.message,
                                   "traceback": test_result.traceback_as_string})

    project.write_report("pyfix_unittest.json", render_report(report))

########NEW FILE########
__FILENAME__ = pyfix_unittest_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

__author__ = "Alexander Metzner"

from pybuilder.core import init, task, description, use_plugin

use_plugin("python.core")


@init
def init_test_source_directory(project):
    project.build_depends_on("pyfix")

    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("pyfix_unittest_module_glob", "*_pyfix_tests")
    project.set_property_if_unset("pyfix_unittest_file_suffix", None)  # deprecated, use pyfix_unittest_module_glob.


@task
@description("Runs unit tests written using the pyfix test framework")
def run_unit_tests(project, logger):
    import pybuilder.plugins.python.pyfix_plugin_impl

    pybuilder.plugins.python.pyfix_plugin_impl.run_unit_tests(project, logger)

########NEW FILE########
__FILENAME__ = pylint_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pybuilder.core import use_plugin, after, init, task
from pybuilder.utils import assert_can_execute
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_modules

use_plugin("python.core")
use_plugin("analysis")

DEFAULT_PYLINT_OPTIONS = ["--max-line-length=100", "--no-docstring-rgx=.*"]


@init
def init_pylint(project):
    project.build_depends_on("pylint")
    project.set_property_if_unset("pylint_options", DEFAULT_PYLINT_OPTIONS)


@after("prepare")
def check_pylint_availability(logger):
    logger.debug("Checking availability of pychecker")
    assert_can_execute(("pylint", ), "pylint", "plugin python.pylint")
    logger.debug("pylint has been found")


@task("analyze")
def execute_pylint(project, logger):
    logger.info("Executing pylint on project sources")

    execute_tool_on_modules(project, "pylint", "pylint", True)

########NEW FILE########
__FILENAME__ = pymetrics_plugin
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os

from pybuilder.core import use_plugin, after, task
from pybuilder.utils import assert_can_execute, execute_command

use_plugin("python.core")
use_plugin("analysis")


@after("prepare")
def check_pymetrics_available(logger):
    logger.debug("Checking availability of pymetrics")
    assert_can_execute(("pymetrics", "--nosql", "--nocsv"), "pymetrics", "plugin python.pymetrics")
    logger.debug("pymetrics has been found")


@task("analyze")
def execute_pymetrics(project, logger):
    logger.info("Executing pymetrics on project sources")
    source_dir = project.expand_path("$dir_source_main_python")

    files_to_scan = []
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            if file_name.endswith(".py"):
                files_to_scan.append(os.path.join(root, file_name))

    csv_file = project.expand_path("$dir_reports/pymetrics.csv")

    command = ["pymetrics", "--nosql", "-c", csv_file] + files_to_scan

    report_file = project.expand_path("$dir_reports/pymetrics")

    env = {"PYTHONPATH": source_dir}
    execute_command(command, report_file, env=env)

########NEW FILE########
__FILENAME__ = pytddmon_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import subprocess

from pybuilder.core import use_plugin, task, init, description

use_plugin('python.core')


@init
def init_pytddmon_plugin(project):
    project.build_depends_on('pytddmon', '>=1.0.2')


@task
@description('Start monitoring tests.')
def pytddmon(project, logger):
    import os
    unittest_directory = project.get_property('dir_source_unittest_python')
    environment = os.environ.copy()
    python_path_relative_to_basedir = project.get_property('dir_source_main_python')
    absolute_python_path = os.path.join(project.basedir, python_path_relative_to_basedir)
    environment['PYTHONPATH'] = absolute_python_path

    # necessary because of windows newlines in the pytddmon shebang - must fix upstream first
    python_interpreter = subprocess.check_output('which python', shell=True).rstrip('\n')
    pytddmon_script = subprocess.check_output('which pytddmon.py', shell=True).rstrip('\n')

    subprocess.Popen([python_interpreter, pytddmon_script, '--no-pulse'], shell=False, cwd=unittest_directory, env=environment)

########NEW FILE########
__FILENAME__ = python_plugin_helper
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import itertools

from pybuilder.utils import (discover_modules,
                             discover_files_matching,
                             execute_command,
                             as_list,
                             read_file)


def log_report(logger, name, report_lines):
    count_of_warnings = len(report_lines)
    if count_of_warnings > 0:
        for report_line in report_lines:
            logger.warn(name + ': ' + report_line[:-1])


def discover_python_files(directory):
    return discover_files_matching(directory, "*.py")


def discover_affected_files(include_test_sources, include_scripts, project):
    source_dir = project.get_property("dir_source_main_python")
    files = discover_python_files(source_dir)

    if include_test_sources:
        if project.get_property("dir_source_unittest_python"):
            unittest_dir = project.get_property("dir_source_unittest_python")
            files = itertools.chain(files, discover_python_files(unittest_dir))
        if project.get_property("dir_source_integrationtest_python"):
            integrationtest_dir = project.get_property("dir_source_integrationtest_python")
            files = itertools.chain(files, discover_python_files(integrationtest_dir))
    if include_scripts and project.get_property("dir_source_main_scripts"):
        scripts_dir = project.get_property("dir_source_main_scripts")
        files = itertools.chain(files, discover_files_matching(scripts_dir, "*"))  # we have no idea how scripts might look
    return files


def execute_tool_on_source_files(project, name, command_and_arguments, logger=None,
                                 include_test_sources=False, include_scripts=False):
    files = discover_affected_files(include_test_sources, include_scripts, project)

    command = as_list(command_and_arguments) + [f for f in files]

    report_file = project.expand_path("$dir_reports/{0}".format(name))

    execution_result = execute_command(command, report_file), report_file

    report_file = execution_result[1]
    report_lines = read_file(report_file)

    if project.get_property(name + "_verbose_output") and logger:
        log_report(logger, name, report_lines)

    return execution_result


def execute_tool_on_modules(project, name, command_and_arguments, extend_pythonpath=True):
    source_dir = project.expand_path("$dir_source_main_python")
    modules = discover_modules(source_dir)
    command = as_list(command_and_arguments) + modules

    report_file = project.expand_path("$dir_reports/%s" % name)

    env = os.environ
    if extend_pythonpath:
        env["PYTHONPATH"] = source_dir
    return execute_command(command, report_file, env=env), report_file

########NEW FILE########
__FILENAME__ = test_plugin_helper
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from pybuilder.errors import BuildFailedException
from pybuilder.utils import render_report
from pybuilder.ci_server_interaction import test_proxy_for


class ReportsProcessor(object):

    def __init__(self, project, logger):
        self.project = project
        self.logger = logger
        self.tests_failed = 0
        self.tests_executed = 0

    def process_reports(self, reports, total_time):
        self.reports = reports
        self.total_time = total_time
        for report in reports:
            if not report['success']:
                self.tests_failed += 1
            self.tests_executed += 1

    @property
    def test_report(self):
        return {
            "time": self.total_time.get_millis(),
            "success": self.tests_failed == 0,
            "num_of_tests": self.tests_executed,
            "tests_failed": self.tests_failed,
            "tests": self.reports
        }

    def write_report_and_ensure_all_tests_passed(self):
        self.project.write_report("integrationtest.json", render_report(self.test_report))
        self.logger.info("Executed %d integration tests.", self.tests_executed)
        if self.tests_failed:
            raise BuildFailedException("%d of %d integration tests failed." % (self.tests_failed, self.tests_executed))

    def report_to_ci_server(self, project):
        for report in self.reports:
            test_name = report['test']
            test_failed = report['success'] is not True
            with test_proxy_for(project).and_test_name('Integrationtest.%s' % test_name) as test:
                if test_failed:
                    test.fails(report['exception'])

########NEW FILE########
__FILENAME__ = unittest_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

import sys
import unittest

from pybuilder.core import init, task, description, use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.utils import discover_modules_matching, render_report
from pybuilder.ci_server_interaction import test_proxy_for
from pybuilder.terminal import print_text_line
use_plugin("python.core")

if sys.version_info < (2, 7):
    TextTestResult = unittest._TextTestResult  # brought to you by 2.6
else:
    TextTestResult = unittest.TextTestResult


class TestNameAwareTextTestRunner(unittest.TextTestRunner):

    def __init__(self, logger, stream):
        self.logger = logger
        super(TestNameAwareTextTestRunner, self).__init__(stream=stream)

    def _makeResult(self):
        return TestNameAwareTestResult(self.logger, self.stream, self.descriptions, self.verbosity)


class TestNameAwareTestResult(TextTestResult):

    def __init__(self, logger, stream, descriptions, verbosity):
        self.test_names = []
        self.failed_test_names_and_reasons = {}
        self.logger = logger
        super(TestNameAwareTestResult, self).__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        self.test_names.append(test)
        self.logger.debug("starting %s", test)
        super(TestNameAwareTestResult, self).startTest(test)

    def addError(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        super(TestNameAwareTestResult, self).addError(test, err)

    def addFailure(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        super(TestNameAwareTestResult, self).addFailure(test, err)


@init
def init_test_source_directory(project):
    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("unittest_module_glob", "*_tests")
    project.set_property_if_unset("unittest_file_suffix", None)  # deprecated, use unittest_module_glob.
    project.set_property_if_unset("unittest_test_method_prefix", None)


@task
@description("Runs unit tests based on Python's unittest module")
def run_unit_tests(project, logger):
    test_dir = _register_test_and_source_path_and_return_test_dir(project, sys.path)

    unittest_file_suffix = project.get_property("unittest_file_suffix")
    if unittest_file_suffix is not None:
        logger.warn("unittest_file_suffix is deprecated, please use unittest_module_glob")
        module_glob = "*{0}".format(unittest_file_suffix)
        if module_glob.endswith(".py"):
            WITHOUT_DOT_PY = slice(None, -3)
            module_glob = module_glob[WITHOUT_DOT_PY]
        project.set_property("unittest_module_glob", module_glob)
    else:
        module_glob = project.get_property("unittest_module_glob")

    logger.info("Executing unittest Python modules in %s", test_dir)
    logger.debug("Including files matching '%s'", module_glob)

    try:
        test_method_prefix = project.get_property("unittest_test_method_prefix")
        result, console_out = execute_tests_matching(logger, test_dir, module_glob, test_method_prefix)

        if result.testsRun == 0:
            logger.warn("No unittests executed.")
        else:
            logger.info("Executed %d unittests", result.testsRun)

        write_report("unittest", project, logger, result, console_out)

        if not result.wasSuccessful():
            raise BuildFailedException("There were %d test error(s) and %d failure(s)"
                                       % (len(result.errors), len(result.failures)))
        logger.info("All unittests passed.")
    except ImportError as e:
        import traceback
        _, _, import_error_traceback = sys.exc_info()
        file_with_error, error_line, _, statement_causing_error = traceback.extract_tb(import_error_traceback)[-1]
        logger.error("Import error in unittest file {0}, due to statement '{1}' on line {2}".format(
            file_with_error, statement_causing_error, error_line))
        logger.error("Error importing unittests: %s", e)
        raise BuildFailedException("Unable to execute unit tests.")


def execute_tests(logger, test_source, suffix, test_method_prefix=None):
    return execute_tests_matching(logger, test_source, "*{0}".format(suffix), test_method_prefix)


def execute_tests_matching(logger, test_source, file_glob, test_method_prefix=None):
    output_log_file = StringIO()

    try:
        test_modules = discover_modules_matching(test_source, file_glob)
        loader = unittest.defaultTestLoader
        if test_method_prefix:
            loader.testMethodPrefix = test_method_prefix
        tests = loader.loadTestsFromNames(test_modules)
        result = TestNameAwareTextTestRunner(logger, output_log_file).run(tests)
        return result, output_log_file.getvalue()
    finally:
        output_log_file.close()


def _register_test_and_source_path_and_return_test_dir(project, system_path):
    test_dir = project.expand_path("$dir_source_unittest_python")
    system_path.insert(0, test_dir)
    system_path.insert(0, project.expand_path("$dir_source_main_python"))

    return test_dir


def write_report(name, project, logger, result, console_out):
    project.write_report("%s" % name, console_out)

    report = {"tests-run": result.testsRun,
              "errors": [],
              "failures": []}

    for error in result.errors:
        report["errors"].append({"test": error[0].id(),
                                 "traceback": error[1]})
        logger.error("Test has error: %s", error[0].id())

        if project.get_property("verbose"):
            print_text_line(error[1])

    for failure in result.failures:
        report["failures"].append({"test": failure[0].id(),
                                   "traceback": failure[1]})
        logger.error("Test failed: %s", failure[0].id())

        if project.get_property("verbose"):
            print_text_line(failure[1])

    project.write_report("%s.json" % name, render_report(report))

    report_to_ci_server(project, result)


def report_to_ci_server(project, result):
    for test_name in result.test_names:
        with test_proxy_for(project).and_test_name(test_name) as test:
            if test_name in result.failed_test_names_and_reasons:
                test.fails(result.failed_test_names_and_reasons.get(test_name))

########NEW FILE########
__FILENAME__ = ronn_manpage_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import errno

from pybuilder.core import init, task, use_plugin, description, depends, after
from pybuilder.utils import assert_can_execute, execute_command

use_plugin("core")


@init
def init_ronn_manpage_plugin(project):
    project.set_property_if_unset("dir_manpages", "docs/man")
    project.set_property_if_unset("manpage_source", "README.md")
    project.set_property_if_unset("manpage_section", 1)


@after("prepare")
def assert_ronn_is_executable(logger):
    """
        Asserts that the ronn script is executable.
    """
    logger.debug("Checking if ronn is executable.")

    assert_can_execute(command_and_arguments=["ronn", "--version"],
                       prerequisite="ronn",
                       caller="plugin ronn_manpage_plugin")


@after("prepare")
def assert_gzip_is_executable(logger):
    """
        Asserts that the gzip program is executable.
    """
    logger.debug("Checking if gzip is executable.")

    assert_can_execute(command_and_arguments=["gzip", "--version"],
                       prerequisite="gzip",
                       caller="plugin ronn_manpage_plugin")


@task
@depends("prepare")
@description("Generates manpages using ronn.")
def generate_manpages(project, logger):
    """
        Uses the ronn script to convert a markdown source to a gzipped manpage.
    """
    logger.info('Generating manpages')
    try:
        os.makedirs(project.get_property('dir_manpages'))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    ronn_report_file = project.expand_path("$dir_reports/{0}".format('generate_manpage'))
    generate_manpages_command = build_generate_manpages_command(project)
    execute_command(generate_manpages_command, ronn_report_file, shell=True)


def build_generate_manpages_command(project):
    ronn_pipe_command = 'ronn -r --pipe %s' % project.get_property('manpage_source')
    compressed_manpage_file = '%s.%d.gz' % (project.name, project.get_property('manpage_section'))
    compress_command = 'gzip -9 > %s' % os.path.join(project.get_property('dir_manpages'), compressed_manpage_file)
    generate_manpages_command = '%s | %s' % (ronn_pipe_command, compress_command)
    return generate_manpages_command

########NEW FILE########
__FILENAME__ = source_distribution_plugin
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import shutil

from pybuilder.core import init, task, use_plugin, description

use_plugin("core")


@init
def init_source_distribution(project):
    source_distribution_directory = "$dir_target/dist/%s-%s-src" % (project.name, project.version)
    project.set_property_if_unset("dir_source_dist", source_distribution_directory)
    project.set_property_if_unset("source_dist_ignore_patterns", ["*.pyc", ".hg*", ".svn", ".CVS"])


@task
@description("Bundles a source distribution for shipping.")
def build_source_distribution(project, logger):
    source_distribution_directory = project.expand_path("$dir_source_dist")
    logger.info("Building source distribution in {0}".format(source_distribution_directory))

    if os.path.exists(source_distribution_directory):
        shutil.rmtree(source_distribution_directory)

    ignore_patterns = ["target"]
    configured_patterns = project.get_property("source_dist_ignore_patterns")
    if configured_patterns:
        ignore_patterns += configured_patterns

    shutil.copytree(project.basedir,
                    source_distribution_directory,
                    ignore=shutil.ignore_patterns(*ignore_patterns))

########NEW FILE########
__FILENAME__ = reactor
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder reactor module.
    Operates a build process by instrumenting an ExecutionManager from the
    execution module.
"""

import imp
import os.path

from pybuilder.core import (TASK_ATTRIBUTE, DEPENDS_ATTRIBUTE,
                            DESCRIPTION_ATTRIBUTE, AFTER_ATTRIBUTE,
                            BEFORE_ATTRIBUTE, INITIALIZER_ATTRIBUTE,
                            ACTION_ATTRIBUTE, ONLY_ONCE_ATTRIBUTE,
                            Project, NAME_ATTRIBUTE, ENVIRONMENTS_ATTRIBUTE)
from pybuilder.errors import PyBuilderException, ProjectValidationFailedException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    ThirdPartyPluginLoader,
                                    DownloadingPluginLoader)
from pybuilder.utils import as_list
from pybuilder.execution import Action, Initializer, Task


class BuildSummary(object):

    def __init__(self, project, task_execution_summaries):
        self.project = project
        self.task_summaries = task_execution_summaries


class Reactor(object):
    _current_instance = None

    @staticmethod
    def current_instance():
        return Reactor._current_instance

    def __init__(self, logger, execution_manager, plugin_loader=None):
        self.logger = logger
        self.execution_manager = execution_manager
        if not plugin_loader:
            builtin_plugin_loader = BuiltinPluginLoader(self.logger)
            installed_thirdparty_plugin_loader = ThirdPartyPluginLoader(self.logger)
            downloading_thirdparty_plugin_loader = DownloadingPluginLoader(self.logger)
            self.plugin_loader = DispatchingPluginLoader(
                self.logger, builtin_plugin_loader, installed_thirdparty_plugin_loader, downloading_thirdparty_plugin_loader)
        else:
            self.plugin_loader = plugin_loader
        self._plugins = []
        self.project = None

    def require_plugin(self, plugin):
        if plugin not in self._plugins:
            try:
                self._plugins.append(plugin)
                self.import_plugin(plugin)
            except:  # NOQA
                self._plugins.remove(plugin)
                raise

    def get_plugins(self):
        return self._plugins

    def get_tasks(self):
        return self.execution_manager.tasks

    def validate_project(self):
        validation_messages = self.project.validate()
        if len(validation_messages) > 0:
            raise ProjectValidationFailedException(validation_messages)

    def prepare_build(self,
                      property_overrides=None,
                      project_directory=".",
                      project_descriptor="build.py"):
        if not property_overrides:
            property_overrides = {}
        Reactor._current_instance = self

        project_directory, project_descriptor = self.verify_project_directory(
            project_directory, project_descriptor)

        self.logger.debug("Loading project module from %s", project_descriptor)

        self.project = Project(basedir=project_directory)

        self.project_module = self.load_project_module(project_descriptor)

        self.apply_project_attributes()
        self.override_properties(property_overrides)

        self.logger.debug("Have loaded plugins %s", ", ".join(self._plugins))

        self.collect_tasks_and_actions_and_initializers(self.project_module)

        self.execution_manager.resolve_dependencies()

    def build(self, tasks=None, environments=None):
        if not tasks:
            tasks = []
        if not environments:
            environments = []
        Reactor._current_instance = self

        if environments:
            self.logger.info(
                "Activated environments: %s", ", ".join(environments))

        self.execution_manager.execute_initializers(
            environments, logger=self.logger, project=self.project)

        self.log_project_properties()

        self.validate_project()

        tasks = as_list(tasks)

        if not len(tasks):
            if self.project.default_task:
                tasks += as_list(self.project.default_task)
            else:
                raise PyBuilderException("No default task given.")

        execution_plan = self.execution_manager.build_execution_plan(tasks)
        self.logger.debug("Execution plan is %s", ", ".join(
            [task.name for task in execution_plan]))

        self.logger.info(
            "Building %s version %s", self.project.name, self.project.version)
        self.logger.info("Executing build in %s", self.project.basedir)

        if len(tasks) == 1:
            self.logger.info("Going to execute task %s", tasks[0])
        else:
            list_of_tasks = ", ".join(tasks)
            self.logger.info("Going to execute tasks: %s", list_of_tasks)

        task_execution_summaries = self.execution_manager.execute_execution_plan(
            execution_plan,
            logger=self.logger,
            project=self.project,
            reactor=self)

        return BuildSummary(self.project, task_execution_summaries)

    def execute_task(self, task_name):
        execution_plan = self.execution_manager.build_execution_plan(task_name)

        self.execution_manager.execute_execution_plan(execution_plan,
                                                      logger=self.logger,
                                                      project=self.project,
                                                      reactor=self)

    def override_properties(self, property_overrides):
        for property_override in property_overrides:
            self.project.set_property(
                property_override, property_overrides[property_override])

    def log_project_properties(self):
        formatted = ""
        for key in sorted(self.project.properties):
            formatted += "\n%40s : %s" % (key, self.project.get_property(key))
        self.logger.debug("Project properties: %s", formatted)

    def import_plugin(self, plugin):
        self.logger.debug("Loading plugin '%s'", plugin)
        plugin_module = self.plugin_loader.load_plugin(self.project, plugin)
        self.collect_tasks_and_actions_and_initializers(plugin_module)

    def collect_tasks_and_actions_and_initializers(self, project_module):
        for name in dir(project_module):
            candidate = getattr(project_module, name)

            if hasattr(candidate, NAME_ATTRIBUTE):
                name = getattr(candidate, NAME_ATTRIBUTE)
            elif hasattr(candidate, "__name__"):
                name = candidate.__name__
            description = getattr(candidate, DESCRIPTION_ATTRIBUTE) if hasattr(
                candidate, DESCRIPTION_ATTRIBUTE) else ""

            if hasattr(candidate, TASK_ATTRIBUTE) and getattr(candidate, TASK_ATTRIBUTE):
                dependencies = getattr(candidate, DEPENDS_ATTRIBUTE) if hasattr(
                    candidate, DEPENDS_ATTRIBUTE) else None

                self.logger.debug("Found task %s", name)
                self.execution_manager.register_task(
                    Task(name, candidate, dependencies, description))

            elif hasattr(candidate, ACTION_ATTRIBUTE) and getattr(candidate, ACTION_ATTRIBUTE):
                before = getattr(candidate, BEFORE_ATTRIBUTE) if hasattr(
                    candidate, BEFORE_ATTRIBUTE) else None
                after = getattr(candidate, AFTER_ATTRIBUTE) if hasattr(
                    candidate, AFTER_ATTRIBUTE) else None

                only_once = False
                if hasattr(candidate, ONLY_ONCE_ATTRIBUTE):
                    only_once = getattr(candidate, ONLY_ONCE_ATTRIBUTE)

                self.logger.debug("Found action %s", name)
                self.execution_manager.register_action(
                    Action(name, candidate, before, after, description, only_once))

            elif hasattr(candidate, INITIALIZER_ATTRIBUTE) and getattr(candidate, INITIALIZER_ATTRIBUTE):
                environments = []
                if hasattr(candidate, ENVIRONMENTS_ATTRIBUTE):
                    environments = getattr(candidate, ENVIRONMENTS_ATTRIBUTE)

                self.execution_manager.register_initializer(
                    Initializer(name, candidate, environments, description))

    def apply_project_attributes(self):
        self.propagate_property("name")
        self.propagate_property("version")
        self.propagate_property("default_task")
        self.propagate_property("summary")
        self.propagate_property("home_page")
        self.propagate_property("description")
        self.propagate_property("authors")
        self.propagate_property("license")
        self.propagate_property("url")

    def propagate_property(self, property):
        if hasattr(self.project_module, property):
            value = getattr(self.project_module, property)
            setattr(self.project, property, value)

    @staticmethod
    def load_project_module(project_descriptor):
        try:
            return imp.load_source("build", project_descriptor)
        except ImportError as e:
            raise PyBuilderException(
                "Error importing project descriptor %s: %s" % (project_descriptor, e))

    @staticmethod
    def verify_project_directory(project_directory, project_descriptor):
        project_directory = os.path.abspath(project_directory)

        if not os.path.exists(project_directory):
            raise PyBuilderException(
                "Project directory does not exist: %s", project_directory)

        if not os.path.isdir(project_directory):
            raise PyBuilderException(
                "Project directory is not a directory: %s", project_directory)

        project_descriptor_full_path = os.path.join(
            project_directory, project_descriptor)

        if not os.path.exists(project_descriptor_full_path):
            raise PyBuilderException(
                "Project directory does not contain descriptor file: %s",
                project_descriptor_full_path)

        if not os.path.isfile(project_descriptor_full_path):
            raise PyBuilderException(
                "Project descriptor is not a file: %s", project_descriptor_full_path)

        return project_directory, project_descriptor_full_path

########NEW FILE########
__FILENAME__ = scaffolding
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
import string

from pybuilder.terminal import print_text_line

try:
    _input = raw_input
except NameError:
    _input = input


DEFAULT_SOURCE_DIRECTORY = 'src/main/python'
DEFAULT_UNITTEST_DIRECTORY = 'src/unittest/python'
DEFAULT_SCRIPTS_DIRECTORY = 'src/main/scripts'
PLUGINS_TO_SUGGEST = ['python.flake8', 'python.coverage', 'python.distutils']


def prompt_user(description, default):
    message = "{0} (default: '{1}') : ".format(description, default)
    return _input(message)


def collect_project_information():
    default_project_name = os.path.basename(os.getcwd())
    project_name = prompt_user('Project name', default_project_name) or default_project_name
    scaffolding = PythonProjectScaffolding(project_name)

    dir_source_main_python = prompt_user('Source directory', DEFAULT_SOURCE_DIRECTORY)
    dir_source_unittest_python = prompt_user(
        'Unittest directory', DEFAULT_UNITTEST_DIRECTORY)
    dir_source_main_scripts = prompt_user("Scripts directory", DEFAULT_SCRIPTS_DIRECTORY)

    plugins = suggest_plugins(PLUGINS_TO_SUGGEST)
    scaffolding.add_plugins(plugins)

    if dir_source_main_python:
        scaffolding.dir_source_main_python = dir_source_main_python
    if dir_source_unittest_python:
        scaffolding.dir_source_unittest_python = dir_source_unittest_python
    if dir_source_main_scripts:
        scaffolding.dir_source_main_scripts = dir_source_main_scripts

    return scaffolding


def suggest_plugins(plugins):
    chosen_plugins = [plugin for plugin in [suggest(plugin) for plugin in plugins] if plugin]
    return chosen_plugins


def suggest(plugin):
    choice = prompt_user('Use plugin %s (Y/n)?' % plugin, 'y')
    plugin_enabled = not choice or choice.lower() == 'y'
    return plugin if plugin_enabled else None


def start_project():
    try:
        scaffolding = collect_project_information()
    except KeyboardInterrupt:
        print_text_line('\nCanceled.')
        return 1

    descriptor = scaffolding.render_build_descriptor()

    with open('build.py', 'w') as build_descriptor_file:
        build_descriptor_file.write(descriptor)

    scaffolding.set_up_project()
    return 0


class PythonProjectScaffolding(object):

    DESCRIPTOR_TEMPLATE = string.Template("""\
from pybuilder.core import $core_imports

$activated_plugins


name = "${project_name}"
default_task = "publish"


$initializer
""")

    INITIALIZER_HEAD = '''@init
def set_properties(project):
'''

    def __init__(self, project_name):
        self.project_name = project_name
        self.dir_source_main_python = DEFAULT_SOURCE_DIRECTORY
        self.dir_source_unittest_python = DEFAULT_UNITTEST_DIRECTORY
        self.dir_source_main_scripts = DEFAULT_SCRIPTS_DIRECTORY
        self.core_imports = ['use_plugin']
        self.plugins = ['python.core', 'python.unittest', 'python.install_dependencies']
        self.initializer = ''

    def add_plugins(self, plugins):
        self.plugins.extend(plugins)

    def render_build_descriptor(self):
        self.build_initializer()
        self.build_imports()
        self.core_imports = ', '.join(self.core_imports)
        return self.DESCRIPTOR_TEMPLATE.substitute(self.__dict__)

    def build_imports(self):
        self.activated_plugins = '\n'.join(['use_plugin("%s")' % plugin for plugin in self.plugins])

    def build_initializer(self):
        self.core_imports.append('init')

        properties_to_set = []
        if not self.is_default_source_main_python:
            properties_to_set.append(('dir_source_main_python', self.dir_source_main_python))
        if not self.is_default_source_unittest_python:
            properties_to_set.append(('dir_source_unittest_python', self.dir_source_unittest_python))
        if not self.is_default_source_main_scripts:
            properties_to_set.append(('dir_source_main_scripts', self.dir_source_main_scripts))

        initializer_body = self._build_initializer_body_with_properties(properties_to_set)

        self.initializer = self.INITIALIZER_HEAD + initializer_body

    @property
    def is_default_source_main_python(self):
        return self.dir_source_main_python == DEFAULT_SOURCE_DIRECTORY

    @property
    def is_default_source_unittest_python(self):
        return self.dir_source_unittest_python == DEFAULT_UNITTEST_DIRECTORY

    @property
    def is_default_source_main_scripts(self):
        return self.dir_source_main_scripts == DEFAULT_SCRIPTS_DIRECTORY

    def set_up_project(self):
        for needed_directory in (self.dir_source_main_python,
                                 self.dir_source_unittest_python,
                                 self.dir_source_main_scripts):
            if not os.path.exists(needed_directory):
                os.makedirs(needed_directory)

    @staticmethod
    def _build_initializer_body_with_properties(properties_to_set):
        initializer_body = ''
        initializer_body += '\n'.join(
            ['    project.set_property("{0}", "{1}")'.format(k, v) for k, v in properties_to_set])

        if not initializer_body:
            initializer_body += '    pass'

        return initializer_body

########NEW FILE########
__FILENAME__ = terminal
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder terminal module.
    Python module providing easy to use text styling for terminals
    being able to understand standard escape sequences.

    Sample usages:

        print styled_text("spam", fg(RED))
        print styled_text("spam", fg(BLACK), bg(GREY))

        print bold("eggs")
        print underline(bold("eggs"))
"""

import sys

_ESCAPE_SEQUENCE_PATTERN = "\033[%sm"
_ESCAPE_SEQUENCE_SEPARATOR = ";"

_BACKGROUND_COLOR = "4"
_FOREGROUND_COLOR = "3"

BLACK = "0"
RED = "1"
GREEN = "2"
BROWN = "3"
BLUE = "4"
MAGENTA = "5"
CYAN = "6"
GREY = "7"
COLOR_DEFAULT = "9"

RESET_TEXT_ATTRIBUTES = "0"
BOLD = "1"
ITALIC = "2"
UNDERLINE = "4"


def bg(color):
    """ Returns the color code to use the given color as a background color. """
    return _BACKGROUND_COLOR + str(int(color))


def fg(color):
    """ Returns the color code to use the given color as a foreground color. """
    return _FOREGROUND_COLOR + str(int(color))


def styled_text(text, *style_attributes):
    """
        Applies all the given style attributes to the given text and returns
        as string which contains
        - the application of the style attributes
        - the text itself
        - a reset of all style attributes
    """
    return "%s%s%s" % (
        _ESCAPE_SEQUENCE_PATTERN % (_ESCAPE_SEQUENCE_SEPARATOR.join(style_attributes)),
        text,
        _ESCAPE_SEQUENCE_PATTERN % "0;0")


def bold(text):
    """
        Convenience function to format the given text in bold font face.
        Equivalent to
            styled_text(text, BOLD)
    """
    return styled_text(text, BOLD)


def italic(text):
    """
        Convenience function to format the given text in italic font face.
        Equivalent to
            styled_text(text, ITALIC)
    """
    return styled_text(text, ITALIC)


def underline(text):
    """
        Convenience function to format the given text with an underline.
        Equivalent to
            styled_text(text, UNDERLINE)
    """
    return styled_text(text, UNDERLINE)


def print_text(text, flush=False):
    sys.stdout.write(text)
    if flush:
        sys.stdout.flush()


def print_text_line(text=""):
    print_text(text)
    print_text("\n")


def draw_line():
    return print_text("-" * 60 + "\n")


def print_error(text):
    sys.stderr.write(text)


def print_error_line(text=""):
    print_error(text)
    print_error("\n")


def print_file_content(file_name, line_prefix="    "):
    print_text_line("File {0}:".format(file_name))

    for line in open(file_name):
        print_text(line_prefix + line)

########NEW FILE########
__FILENAME__ = utils
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
    The PyBuilder utils module.
    Provides generic utilities that can be used by plugins.
"""

import fnmatch
import json
import os
import re
import subprocess
import tempfile
import time

from pybuilder.errors import MissingPrerequisiteException, PyBuilderException


def render_report(report_dict):
    return json.dumps(report_dict, indent=2, sort_keys=True)


def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def timedelta_in_millis(timedelta):
    return((timedelta.days * 24 * 60 * 60) + timedelta.seconds) * 1000 + round(timedelta.microseconds / 1000)


def as_list(*whatever):
    """
        Returns a list containing all values given in whatever.
        Each list or tuple will be "unpacked", all other elements
        are added to the resulting list.

        Examples given

        >>> as_list('spam')
        ['spam']

        >>> as_list('spam', 'eggs')
        ['spam', 'eggs']

        >>> as_list(('spam', 'eggs'))
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'])
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'], ('spam', 'eggs'), 'foo', 'bar')
        ['spam', 'eggs', 'spam', 'eggs', 'foo', 'bar']
    """
    result = []

    for w in whatever:
        if w is None:
            continue
        elif isinstance(w, list):
            result += w
        elif isinstance(w, tuple):
            result += w
        else:
            result.append(w)
    return result


def remove_leading_slash_or_dot_from_path(path):
    if path.startswith('/') or path.startswith('.'):
            return path[1:]
    return path


def remove_python_source_suffix(file_name):
    if file_name.endswith(".py"):
        return file_name[0:-len(".py")]
    return file_name


def discover_modules(source_path, suffix=".py"):
    return discover_modules_matching(source_path, "*{0}".format(suffix))


def discover_modules_matching(source_path, module_glob):
    result = []
    if not module_glob.endswith(".py"):
        module_glob += ".py"
    for module_file_path in discover_files_matching(source_path, module_glob):
        relative_module_file_path = module_file_path.replace(source_path, "")
        relative_module_file_path = relative_module_file_path.replace(os.sep, ".")
        module_file = remove_leading_slash_or_dot_from_path(relative_module_file_path)
        module_name = remove_python_source_suffix(module_file)
        if module_name.endswith(".__init__"):
            module_name = module_name.replace(".__init__", "")
        result.append(module_name)
    return result


def discover_files(start_dir, suffix):
    return discover_files_matching(start_dir, "*{0}".format(suffix))


def discover_files_matching(start_dir, file_glob):
    for root, _, files in os.walk(start_dir):
        for file_name in files:
            if fnmatch.fnmatch(file_name, file_glob):
                yield os.path.join(root, file_name)


def execute_command(command_and_arguments, outfile_name, env=None, cwd=None, error_file_name=None, shell=False):
    if error_file_name is None:
        error_file_name = outfile_name + ".err"

    with open(outfile_name, "w") as out_file:
        with open(error_file_name, "w") as error_file:
            process = subprocess.Popen(command_and_arguments,
                                       stdout=out_file,
                                       stderr=error_file,
                                       env=env,
                                       cwd=cwd,
                                       shell=shell)
            return process.wait()


def assert_can_execute(command_and_arguments, prerequisite, caller):
    fd, outfile = tempfile.mkstemp()
    f = open(outfile, "w")
    try:
        process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False)
        process.wait()
    except OSError:
        raise MissingPrerequisiteException(prerequisite, caller)
    finally:
        f.close()
        os.close(fd)
        os.unlink(outfile)


def read_file(file_name):
    with open(file_name, "r") as file_handle:
        return file_handle.readlines()


def write_file(file_name, *lines):
    with open(file_name, "w") as file_handle:
        file_handle.writelines(lines)


class Timer(object):
    @staticmethod
    def start():
        return Timer()

    def __init__(self):
        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        self.end_time = time.time()

    def get_millis(self):
        if self.end_time is None:
            raise PyBuilderException("Timer is running.")
        return int((self.end_time - self.start_time) * 1000)


def apply_on_files(start_directory, closure, globs, *additional_closure_arguments, **keyword_closure_arguments):
    glob_expressions = list(map(lambda g: GlobExpression(g), globs))

    for root, _, file_names in os.walk(start_directory):
        for file_name in file_names:
            absolute_file_name = os.path.join(root, file_name)
            relative_file_name = absolute_file_name.replace(start_directory, "")[1:]

            for glob_expression in glob_expressions:
                if glob_expression.matches(relative_file_name):
                    closure(absolute_file_name,
                            relative_file_name,
                            *additional_closure_arguments,
                            **keyword_closure_arguments)


class GlobExpression(object):
    def __init__(self, expression):
        self.expression = expression
        self.regex = "^" + expression.replace("**", ".+").replace("*", "[^/]*") + "$"
        self.pattern = re.compile(self.regex)

    def matches(self, path):
        if self.pattern.match(path):
            return True
        return False


def mkdir(directory):
    """
    Tries to create the directory denoted by the given name. If it exists and is a directory, nothing will be created
    and no error is raised. If it exists as a file a PyBuilderException is raised. Otherwise the directory incl.
    all parents is created.
    """

    if os.path.exists(directory):
        if os.path.isfile(directory):
            message = "Unable to created directory '%s': A file with that name already exists"
            raise PyBuilderException(message, directory)
        return
    os.makedirs(directory)

########NEW FILE########
__FILENAME__ = ci_server_interaction_tests
import unittest
from mock import patch, call

from pybuilder.core import Project
from pybuilder.ci_server_interaction import (test_proxy_for,
                                             TeamCityTestProxy,
                                             TestProxy)


class TestProxyTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('basedir')

    def test_should_use_teamcity_proxy_if_project_property_is_set(self):
        self.project.set_property('teamcity_output', True)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TeamCityTestProxy)

    def test_should_use_default_proxy_if_project_property_is_not_set(self):
        self.project.set_property('teamcity_output', False)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TestProxy)

    def test_should_use_default_proxy_if_project_property_is_set_but_coverage_is_running(self):
        self.project.set_property('teamcity_output', True)
        self.project.set_property('__running_coverage', True)

        proxy = test_proxy_for(self.project)

        self.assertEquals(type(proxy), TestProxy)


class TeamCityProxyTests(unittest.TestCase):

    @patch('pybuilder.ci_server_interaction.flush_text_line')
    def test_should_output_happypath_test_for_teamcity(self, output):
        with TeamCityTestProxy().and_test_name('important-test'):
            pass

        self.assertEqual(output.call_args_list,
                         [
                             call("##teamcity[testStarted name='important-test']"),
                             call("##teamcity[testFinished name='important-test']")
                         ])

    @patch('pybuilder.ci_server_interaction.flush_text_line')
    def test_should_output_failed_test_for_teamcity(self, output):
        with TeamCityTestProxy().and_test_name('important-test') as test:
            test.fails('booom')

        self.assertEqual(output.call_args_list,
                         [
                             call("##teamcity[testStarted name='important-test']"),
                             call("##teamcity[testFailed name='important-test' message='See details' details='booom']"),
                             call("##teamcity[testFinished name='important-test']")
                         ])

########NEW FILE########
__FILENAME__ = cli_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from pybuilder.cli import parse_options, ColoredStdOutLogger, CommandLineUsageException, StdOutLogger, \
    length_of_longest_string
from pybuilder.core import Logger


class StdOutLoggerTest (unittest.TestCase):

    def setUp(self):
        self.stdout_logger = StdOutLogger(Logger)

    def test_should_return_debug_message_when_debug_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.DEBUG)
        self.assertEqual(actual_message, "[DEBUG]")

    def test_should_return_info_message_when_info_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.INFO)
        self.assertEqual(actual_message, "[INFO] ")

    def test_should_return_warning_message_when_warning_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.WARN)
        self.assertEqual(actual_message, "[WARN] ")

    def test_should_return_error_message_when_any_not_defined_level_given(self):
        actual_message = self.stdout_logger._level_to_string(-1)
        self.assertEqual(actual_message, "[ERROR]")


class ColoredStdOutLoggerTest (unittest.TestCase):

    def setUp(self):
        self.colored_stdout_logger = ColoredStdOutLogger(Logger)

    def test_should_return_italic_debug_message_when_debug_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.DEBUG)
        self.assertEqual(actual_message, "\x1b[2m[DEBUG]\x1b[0;0m")

    def test_should_return_bold_info_message_when_info_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.INFO)
        self.assertEqual(actual_message, "\x1b[1m[INFO] \x1b[0;0m")

    def test_should_return_brown_and_bold_warning_message_when_warning_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.WARN)
        self.assertEqual(actual_message, "\x1b[1;33m[WARN] \x1b[0;0m")

    def test_should_return_bold_and_red_error_message_when_any_not_defined_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(-1)
        self.assertEqual(actual_message, "\x1b[1;31m[ERROR]\x1b[0;0m")


class ParseOptionsTest (unittest.TestCase):

    def assert_options(self, options, **overrides):
        self.assertEquals(options.project_directory,
                          overrides.get("project_directory", "."))
        self.assertEquals(options.debug,
                          overrides.get("debug", False))
        self.assertEquals(options.quiet,
                          overrides.get("quiet", False))
        self.assertEquals(options.list_tasks,
                          overrides.get("list_tasks", False))
        self.assertEquals(options.no_color,
                          overrides.get("no_color", False))
        self.assertEquals(options.property_overrides,
                          overrides.get("property_overrides", {}))
        self.assertEquals(options.start_project,
                          overrides.get("start_project", False))

    def test_should_parse_empty_arguments(self):
        options, arguments = parse_options([])

        self.assert_options(options)
        self.assertEquals([], arguments)

    def test_should_parse_task_list_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEquals(["clean", "spam"], arguments)

    def test_should_parse_start_project_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEquals(["clean", "spam"], arguments)

    def test_should_parse_empty_arguments_with_option(self):
        options, arguments = parse_options(["-X"])

        self.assert_options(options, debug=True)
        self.assertEquals([], arguments)

    def test_should_parse_arguments_and_option(self):
        options, arguments = parse_options(["-X", "-D", "spam", "eggs"])

        self.assert_options(options, debug=True, project_directory="spam")
        self.assertEquals(["eggs"], arguments)

    def test_should_set_property(self):
        options, arguments = parse_options(["-P", "spam=eggs"])

        self.assert_options(options, property_overrides={"spam": "eggs"})
        self.assertEquals([], arguments)

    def test_should_set_multiple_properties(self):
        options, arguments = parse_options(["-P", "spam=eggs",
                                            "-P", "foo=bar"])

        self.assert_options(options, property_overrides={"spam": "eggs",
                                                         "foo": "bar"})
        self.assertEquals([], arguments)

    def test_should_abort_execution_when_property_definition_has_syntax_error(self):
        self.assertRaises(
            CommandLineUsageException, parse_options, ["-P", "spam"])

    def test_should_parse_single_environment(self):
        options, arguments = parse_options(["-E", "spam"])

        self.assert_options(options, environments=["spam"])
        self.assertEquals([], arguments)

    def test_should_parse_multiple_environments(self):
        options, arguments = parse_options(["-E", "spam", "-E", "eggs"])

        self.assert_options(options, environments=["spam", "eggs"])
        self.assertEquals([], arguments)

    def test_should_parse_empty_environments(self):
        options, arguments = parse_options([])

        self.assert_options(options, environments=[])
        self.assertEquals([], arguments)


class LengthOfLongestStringTests(unittest.TestCase):

    def test_should_return_zero_when_list_is_empty(self):
        self.assertEqual(0, length_of_longest_string([]))

    def test_should_return_one_when_list_contains_string_with_single_character(self):
        self.assertEqual(1, length_of_longest_string(['a']))

    def test_should_return_four_when_list_contains_egg_and_spam(self):
        self.assertEqual(4, length_of_longest_string(['egg', 'spam']))

    def test_should_return_four_when_list_contains_foo_bar_egg_and_spam(self):
        self.assertEqual(
            4, length_of_longest_string(['egg', 'spam', 'foo', 'bar']))

########NEW FILE########
__FILENAME__ = core_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
import types
import unittest

from pyassert import assert_that
from mockito import when, verify, unstub

from pybuilder.core import Project, Logger, init, INITIALIZER_ATTRIBUTE, ENVIRONMENTS_ATTRIBUTE
from pybuilder.errors import MissingPropertyException


class ProjectTest (unittest.TestCase):

    def setUp(self):
        self.project = Project(basedir="/imaginary", name="Unittest")

    def test_should_pick_directory_name_for_project_name_when_name_is_not_given(self):
        try:
            when(os.path).basename("/imaginary").thenReturn("imaginary")

            project = Project(basedir="/imaginary")

            self.assertEquals("imaginary", project.name)
            verify(os.path).basename("/imaginary")
        finally:
            unstub()

    def test_get_property_should_return_default_value_when_property_is_not_set(self):
        self.assertEquals("spam", self.project.get_property("spam", "spam"))

    def test_get_property_should_return_property_value_when_property_is_set(self):
        self.project.set_property("spam", "eggs")
        self.assertEquals("eggs", self.project.get_property("spam", "spam"))

    def test_has_property_should_return_false_when_property_is_not_set(self):
        self.assertFalse(self.project.has_property("spam"))

    def test_has_property_should_return_true_when_property_is_set(self):
        self.project.set_property("spam", "eggs")
        self.assertTrue(self.project.has_property("spam"))

    def test_set_property_if_unset_should_set_property_when_property_is_not_set(self):
        self.project.set_property_if_unset("spam", "spam")
        self.assertEquals("spam", self.project.get_property("spam"))

    def test_set_property_if_unset_should_not_set_property_when_property_is_already_set(self):
        self.project.set_property("spam", "eggs")
        self.project.set_property_if_unset("spam", "spam")
        self.assertEquals("eggs", self.project.get_property("spam"))

    def test_expand_should_raise_exception_when_property_is_not_set(self):
        self.assertRaises(
            MissingPropertyException, self.project.expand, "$spam")

    def test_expand_should_return_expanded_string_when_property_is_set(self):
        self.project.set_property("spam", "eggs")
        self.assertEquals("eggs", self.project.expand("$spam"))

    def test_expand_should_return_expanded_string_when_two_properties_are_found_and_set(self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals(
            "spam and eggs", self.project.expand("$spam and $eggs"))

    def test_expand_should_expand_property_with_value_being_an_property_expression(self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "$spam")
        self.assertEquals("spam", self.project.expand("$eggs"))

    def test_expand_should_raise_exception_when_first_expansion_leads_to_property_reference_and_property_is_undefined(self):
        self.project.set_property("eggs", "$spam")
        self.assertRaises(
            MissingPropertyException, self.project.expand, "$eggs")

    def test_expand_path_should_return_expanded_path(self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals(os.path.join("/imaginary", "spam", "eggs"),
                          self.project.expand_path("$spam/$eggs"))

    def test_expand_path_should_return_expanded_path_and_additional_parts_when_additional_parts_are_given(self):
        self.project.set_property("spam", "spam")
        self.project.set_property("eggs", "eggs")
        self.assertEquals(
            os.path.join("/imaginary", "spam", "eggs", "foo", "bar"),
            self.project.expand_path("$spam/$eggs", "foo", "bar"))

    def test_should_raise_exception_when_getting_mandatory_propert_and_property_is_not_found(self):
        self.assertRaises(MissingPropertyException,
                          self.project.get_mandatory_property, "i_dont_exist")

    def test_should_return_property_value_when_getting_mandatory_propert_and_property_exists(self):
        self.project.set_property("spam", "spam")
        self.assertEquals("spam", self.project.get_mandatory_property("spam"))

    def test_should_add_runtime_dependency_with_name_only(self):
        self.project.depends_on("spam")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals(None, self.project.dependencies[0].version)

    def test_should_add_dependency_with_name_and_version(self):
        self.project.depends_on("spam", "0.7")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals("0.7", self.project.dependencies[0].version)

    def test_should_add_dependency_with_name_and_version_only_once(self):
        self.project.depends_on("spam", "0.7")
        self.project.depends_on("spam", "0.7")
        self.assertEquals(1, len(self.project.dependencies))
        self.assertEquals("spam", self.project.dependencies[0].name)
        self.assertEquals("0.7", self.project.dependencies[0].version)


class ProjectManifestTests(unittest.TestCase):

    def setUp(self):
        self.project = Project(basedir="/imaginary", name="Unittest")

    def test_should_raise_exception_when_given_glob_pattern_is_none(self):
        self.assertRaises(ValueError, self.project._manifest_include, None)

    def test_should_raise_exception_when_given_glob_pattern_is_empty_string(self):
        self.assertRaises(
            ValueError, self.project._manifest_include, "       \n")

    def test_should_add_filename_to_list_of_included_files(self):
        self.project._manifest_include("spam")
        self.assertEquals(["spam"], self.project.manifest_included_files)

    def test_should_add_filenames_in_correct_order_to_list_of_included_files(self):
        self.project._manifest_include("spam")
        self.project._manifest_include("egg")
        self.project._manifest_include("yadt")
        self.assertEquals(
            ["spam", "egg", "yadt"], self.project.manifest_included_files)


class ProjectPackageDataTests(unittest.TestCase):

    def setUp(self):
        self.project = Project(basedir="/imaginary", name="Unittest")

    def test_should_raise_exception_when_package_name_not_given(self):
        self.assertRaises(ValueError, self.project.include_file, None, "spam")

    def test_should_raise_exception_when_filename_not_given(self):
        self.assertRaises(
            ValueError, self.project.include_file, "my_package", None)

    def test_should_raise_exception_when_package_name_is_empty_string(self):
        self.assertRaises(
            ValueError, self.project.include_file, "    \n", "spam")

    def test_should_raise_exception_when_filename_is_empty_string(self):
        self.assertRaises(
            ValueError, self.project.include_file, "eggs", "\t    \n")

    def test_should_package_data_dictionary_is_empty(self):
        self.assertEquals({}, self.project.package_data)

    def test_should_add_filename_to_list_of_included_files_for_package_spam(self):
        self.project.include_file("spam", "eggs")

        self.assertEquals({"spam": ["eggs"]}, self.project.package_data)

    def test_should_add_two_filenames_to_list_of_included_files_for_package_spam(self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("spam", "ham")

        self.assertEquals({"spam": ["eggs", "ham"]}, self.project.package_data)

    def test_should_add_two_filenames_to_list_of_included_files_for_two_different_packages(self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("monty", "ham")

        self.assertEquals(
            {"monty": ["ham"], "spam": ["eggs"]}, self.project.package_data)

    def test_should_add_two_filenames_to_list_of_included_files_and_to_manifest(self):
        self.project.include_file("spam", "eggs")
        self.project.include_file("monty", "ham")

        self.assertEquals(
            {"monty": ["ham"], "spam": ["eggs"]}, self.project.package_data)
        self.assertEquals(
            ["spam/eggs", "monty/ham"], self.project.manifest_included_files)


class ProjectDataFilesTests(unittest.TestCase):

    def setUp(self):
        self.project = Project(basedir="/imaginary", name="Unittest")

    def test_should_return_empty_list_for_property_files_to_install(self):
        self.assertEquals([], self.project.files_to_install)

    def test_should_return_file_to_install(self):
        self.project.install_file("destination", "filename")

        self.assertEquals(
            [("destination", ["filename"])], self.project.files_to_install)

    def test_should_raise_exception_when_no_destination_given(self):
        self.assertRaises(
            ValueError, self.project.install_file, None, "Hello world.")

    def test_should_raise_exception_when_no_filename_given(self):
        self.assertRaises(
            ValueError, self.project.install_file, "destination", None)

    def test_should_raise_exception_when_filename_empty(self):
        self.assertRaises(
            ValueError, self.project.install_file, "destination", "\t   \n")

    def test_should_return_files_to_install_into_same_destination(self):
        self.project.install_file("destination", "filename1")
        self.project.install_file("destination", "filename2")

        self.assertEquals(
            [("destination", ["filename1", "filename2"])], self.project.files_to_install)

    def test_should_return_files_to_install_into_different_destinations(self):
        self.project.install_file("destination_a", "filename_a_1")
        self.project.install_file("destination_a", "filename_a_2")
        self.project.install_file("destination_b", "filename_b")

        self.assertEquals([("destination_a", ["filename_a_1", "filename_a_2"]),
                           ("destination_b", ["filename_b"])], self.project.files_to_install)

    def test_should_return_files_to_install_into_different_destinations_and_add_them_to_manifest(self):
        self.project.install_file("destination_a", "somepackage1/filename1")
        self.project.install_file("destination_a", "somepackage2/filename2")
        self.project.install_file("destination_b", "somepackage3/filename3")

        self.assertEquals(
            [("destination_a", ["somepackage1/filename1", "somepackage2/filename2"]),
             ("destination_b", ["somepackage3/filename3"])], self.project.files_to_install)
        self.assertEquals(
            ["somepackage1/filename1", "somepackage2/filename2", "somepackage3/filename3"], self.project.manifest_included_files)


class ProjectValidationTest(unittest.TestCase):

    def setUp(self):
        self.project = Project(basedir="/imaginary", name="Unittest")

    def test_should_validate_empty_project(self):
        validation_messages = self.project.validate()
        assert_that(validation_messages).is_empty()

    def test_should_not_validate_project_with_duplicate_dependency_but_different_versions(self):
        self.project.depends_on('spam', version='1')
        self.project.depends_on('spam', version='2')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_dependency_when_version_is_given_for_one(self):
        self.project.depends_on('spam')
        self.project.depends_on('spam', version='2')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_dependency_when_urls_are_different(self):
        self.project.depends_on('spam', url='y')
        self.project.depends_on('spam', url='x')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_dependency_when_url_is_given_for_one(self):
        self.project.depends_on('spam')
        self.project.depends_on('spam', url='x')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_dependency_for_more_than_two_times(self):
        self.project.depends_on('spam', version='1')
        self.project.depends_on('spam', version='2')
        self.project.depends_on('spam', version='3')
        validation_messages = self.project.validate()

        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has been defined multiple times.")
        assert_that(len(validation_messages)).equals(1)

    def test_should_not_validate_project_with_duplicate_build_dependency_but_different_versions(self):
        self.project.build_depends_on('spam', version='1')
        self.project.build_depends_on('spam', version='2')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Build dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_build_dependency_when_version_is_given_for_one(self):
        self.project.build_depends_on('spam')
        self.project.build_depends_on('spam', version='2')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Build dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_build_dependency_when_urls_are_different(self):
        self.project.build_depends_on('spam', url='y')
        self.project.build_depends_on('spam', url='x')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Build dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_build_dependency_when_url_is_given_for_one(self):
        self.project.build_depends_on('spam')
        self.project.build_depends_on('spam', url='x')
        validation_messages = self.project.validate()
        assert_that(validation_messages).contains(
            "Build dependency 'spam' has been defined multiple times.")

    def test_should_not_validate_project_with_duplicate_build_dependency_for_more_than_two_times(self):
        self.project.build_depends_on('spam', version='1')
        self.project.build_depends_on('spam', version='2')
        self.project.build_depends_on('spam', version='3')
        validation_messages = self.project.validate()

        assert_that(validation_messages).contains(
            "Build dependency 'spam' has been defined multiple times.")
        assert_that(len(validation_messages)).equals(1)

    def test_should_not_validate_project_with_runtime_dependency_being_also_given_as_build_dependency(self):
        self.project.depends_on('spam')
        self.project.build_depends_on('spam')
        validation_messages = self.project.validate()

        assert_that(validation_messages).contains(
            "Runtime dependency 'spam' has also been given as build dependency.")
        assert_that(len(validation_messages)).equals(1)


class LoggerTest(unittest.TestCase):

    class LoggerMock(Logger):

        def __init__(self, threshold):
            super(LoggerTest.LoggerMock, self).__init__(threshold)
            self._logged = []

        def _do_log(self, level, message, *arguments):
            self._logged.append((level, message, arguments))

        def assert_not_logged(self, level, message, *arguments):
            if (level, message, arguments) in self._logged:
                raise AssertionError(
                    "Logged %s %s %s" % (level, message, arguments))

        def assert_logged(self, level, message, *arguments):
            if (level, message, arguments) not in self._logged:
                raise AssertionError(
                    "Not logged %s %s %s" % (level, message, arguments))

    def test_should_log_debug_message_without_arguments(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message")
        logger.assert_logged(Logger.DEBUG, "message")

    def test_should_log_debug_message_without_arguments_but_percent_sign(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message with %s")
        logger.assert_logged(Logger.DEBUG, "message with %s")

    def test_should_log_debug_message(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.debug("message", "argument one", "argument two")
        logger.assert_logged(
            Logger.DEBUG, "message", "argument one", "argument two")

    def test_should_log_info_message(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.info("message", "argument one", "argument two")
        logger.assert_logged(
            Logger.INFO, "message", "argument one", "argument two")

    def test_should_log_warn_message(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.warn("message", "argument one", "argument two")
        logger.assert_logged(
            Logger.WARN, "message", "argument one", "argument two")

    def test_should_log_error_message(self):
        logger = LoggerTest.LoggerMock(Logger.DEBUG)
        logger.error("message", "argument one", "argument two")
        logger.assert_logged(
            Logger.ERROR, "message", "argument one", "argument two")

    def test_should_not_not_log_info_message_when_threshold_is_set_to_warn(self):
        logger = LoggerTest.LoggerMock(Logger.WARN)
        logger.info("message", "argument one", "argument two")
        logger.assert_not_logged(
            Logger.INFO, "message", "argument one", "argument two")


def is_callable(function_or_object):
    return isinstance(function_or_object, types.FunctionType) or hasattr(function_or_object, "__call__")


class InitTest(unittest.TestCase):

    def test_ensure_that_init_can_be_used_without_invocation_parenthesis(self):
        @init
        def fun():
            pass

        self.assertTrue(hasattr(fun, INITIALIZER_ATTRIBUTE))
        self.assertTrue(is_callable(fun))

    def test_ensure_that_init_can_be_used_with_invocation_parenthesis(self):
        @init()
        def fun():
            pass

        self.assertTrue(hasattr(fun, INITIALIZER_ATTRIBUTE))
        self.assertTrue(is_callable(fun))

    def test_ensure_that_init_can_be_used_with_named_arguments(self):
        @init(environments="spam")
        def fun():
            pass

        self.assertTrue(hasattr(fun, INITIALIZER_ATTRIBUTE))
        self.assertTrue(hasattr(fun, ENVIRONMENTS_ATTRIBUTE))
        self.assertTrue(getattr(fun, ENVIRONMENTS_ATTRIBUTE), ["spam"])

        self.assertTrue(is_callable(fun))

########NEW FILE########
__FILENAME__ = errors_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from pybuilder.errors import PyBuilderException


class PyBuilderExceptionTest(unittest.TestCase):
    def test_should_format_exception_message_without_arguments(self):
        self.assertEquals("spam and eggs", str(PyBuilderException("spam and eggs")))

    def test_should_format_exception_message_with_arguments(self):
        self.assertEquals("spam and eggs", str(PyBuilderException("%s and %s", "spam", "eggs")))

########NEW FILE########
__FILENAME__ = execution_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from mockito import verify, unstub, any, times, when
import unittest
from test_utils import mock

from pybuilder.errors import MissingTaskDependencyException, CircularTaskDependencyException, NoSuchTaskException,\
    MissingActionDependencyException, InvalidNameException
from pybuilder.core import Logger
from pybuilder.execution import as_task_name_list, Action, Executable, ExecutionManager, Task,\
    DependenciesNotResolvedException, Initializer


class AsTaskNameList(unittest.TestCase):

    def test_should_return_list_of_strings_when_string_given(self):
        self.assertEquals(["spam"], as_task_name_list("spam"))

    def test_should_return_list_of_strings_when_list_of_strings_given(self):
        self.assertEquals(
            ["spam", "eggs"], as_task_name_list(["spam", "eggs"]))

    def test_should_return_list_of_strings_when_function_given(self):
        def spam():
            pass

        self.assertEquals(["spam"], as_task_name_list(spam))

    def test_should_return_list_of_strings_when_list_of_functions_given(self):
        def spam():
            pass

        def eggs():
            pass

        self.assertEquals(["spam", "eggs"], as_task_name_list([spam, eggs]))


class ExecutableTest(unittest.TestCase):

    def test_should_raise_exception_when_passing_non_function_to_constructor(self):
        self.assertRaises(TypeError, Executable, "callable", "spam")

    def test_should_raise_exception_when_executable_name_is_invalid(self):
        def callable():
            pass

        self.assertRaises(InvalidNameException, Executable, "a-b", callable)
        self.assertRaises(InvalidNameException, Executable, "88aa", callable)
        self.assertRaises(
            InvalidNameException, Executable, "l asd ll", callable)
        self.assertRaises(InvalidNameException, Executable, "@", callable)
        self.assertRaises(InvalidNameException, Executable, "$", callable)
        self.assertRaises(InvalidNameException, Executable, "%", callable)

    def test_should_execute_callable_without_arguments(self):
        def callable():
            callable.called = True

        callable.called = False

        Executable("callable", callable).execute({})

        self.assertTrue(callable.called)

    def test_should_execute_callable_with_single_arguments(self):
        def callable(spam):
            callable.called = True
            callable.spam = spam

        callable.called = False

        Executable("callable", callable).execute({"spam": "spam"})

        self.assertTrue(callable.called)
        self.assertEquals("spam", callable.spam)

    def test_should_raise_exception_when_callable_argument_cannot_be_satisfied(self):
        def callable(spam):
            pass

        executable = Executable("callable", callable)
        self.assertRaises(ValueError, executable.execute, {})


class ActionTest(unittest.TestCase):

    def test_should_initialize_fields(self):
        def callable():
            pass

        action = Action("callable", callable, "before", "after", "description")

        self.assertEquals(["before"], action.execute_before)
        self.assertEquals(["after"], action.execute_after)
        self.assertEquals("description", action.description)


class TaskTest(unittest.TestCase):

    def test_should_sort_tasks_by_name(self):
        task_a = Task("a_name", lambda: None, "dependency", "description")
        task_b = Task("b_name", lambda: None, "dependency", "description")

        task_list = [task_b, task_a]

        self.assertEquals(["a_name", "b_name"], [
                          task.name for task in sorted(task_list)])

    def test_should_initialize_fields(self):
        def callable():
            pass

        task = Task("callable", callable, "dependency", "description")

        self.assertEquals(["dependency"], task.dependencies)
        self.assertEquals(["description"], task.description)

    def test_should_execute_callable_without_arguments(self):
        def callable():
            callable.called = True

        callable.called = False

        Task("callable", callable).execute(mock(), {})

        self.assertTrue(callable.called)

    def test_should_execute_callable_with_single_arguments(self):
        def callable(spam):
            callable.called = True
            callable.spam = spam

        callable.called = False

        Task("callable", callable).execute(mock(), {"spam": "spam"})

        self.assertTrue(callable.called)
        self.assertEquals("spam", callable.spam)

    def test_should_raise_exception_when_callable_argument_cannot_be_satisfied(self):
        def callable(spam):
            pass

        executable = Task("callable", callable)
        self.assertRaises(ValueError, executable.execute, mock(), {})


class TaskExtensionTest(unittest.TestCase):

    def test_should_extend_task_with_values_from_other_task(self):
        def callable_one():
            pass

        def callable_two(param):
            pass

        task = Task("task", callable_one, "dependency", "description")
        replacement = Task("replacement", callable_two,
                           "another_dependency", "replacement description")

        task.extend(replacement)

        self.assertEquals("task", task.name)
        self.assertEquals(
            ["dependency", "another_dependency"], task.dependencies)
        self.assertEquals(
            ["description", "replacement description"], task.description)

    def test_should_execute_both_callables_when_extending_task(self):
        def callable_one():
            callable_one.called = True

        callable_one.called = False

        def callable_two(param):
            callable_two.called = True

        callable_two.called = False

        task_one = Task("task", callable_one)
        task_two = Task("task", callable_two)
        task_one.extend(task_two)

        task_one.execute(mock(), {"param": "spam"})

        self.assertTrue(callable_one.called)
        self.assertTrue(callable_two.called)


class InitializerTest(unittest.TestCase):

    def setUp(self):
        def callable():
            pass

        self.callable = callable

    def test_should_return_true_when_invoking_is_applicable_without_environment_and_initializer_does_not_define_environments(
            self):
        initializer = Initializer("initialzer", self.callable)
        self.assertTrue(initializer.is_applicable())

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_does_not_define_environments(
            self):
        initializer = Initializer("initialzer", self.callable)
        self.assertTrue(initializer.is_applicable("any_environment"))

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer(
            "initialzer", self.callable, "any_environment")
        self.assertTrue(initializer.is_applicable("any_environment"))

    def test_should_return_true_when_invoking_is_applicable_with_environments_and_initializer_defines_environment(
            self):
        initializer = Initializer(
            "initialzer", self.callable, "any_environment")
        self.assertTrue(initializer.is_applicable(
            ["any_environment", "any_other_environment"]))

    def test_should_return_false_when_invoking_is_applicable_with_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer(
            "initialzer", self.callable, "any_environment")
        self.assertFalse(initializer.is_applicable("any_other_environment"))

    def test_should_return_false_when_invoking_is_applicable_without_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer(
            "initialzer", self.callable, "any_environment")
        self.assertFalse(initializer.is_applicable())

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_defines_multiple_environments(
            self):
        initializer = Initializer(
            "initialzer", self.callable, ["any_environment", "any_other_environment"])
        self.assertTrue(initializer.is_applicable(["any_environment"]))


class ExecutionManagerTestBase(unittest.TestCase):

    def setUp(self):
        self.execution_manager = ExecutionManager(Logger())

    def tearDown(self):
        unstub()


class ExecutionManagerInitializerTest(ExecutionManagerTestBase):

    def test_ensure_that_initializer_is_added_when_calling_register_initializer(self):
        initializer = mock()
        self.execution_manager.register_initializer(initializer)
        self.assertEquals([initializer], self.execution_manager.initializers)

    def test_ensure_that_registered_initializers_are_executed_when_calling_execute_initializers(self):
        initializer_1 = mock()
        when(initializer_1).is_applicable(any()).thenReturn(True)
        self.execution_manager.register_initializer(initializer_1)

        initializer_2 = mock()
        when(initializer_2).is_applicable(any()).thenReturn(True)
        self.execution_manager.register_initializer(initializer_2)

        self.execution_manager.execute_initializers(a=1)

        verify(initializer_1).execute({"a": 1})
        verify(initializer_2).execute({"a": 1})

    def test_ensure_that_registered_initializers_are_not_executed_when_environments_do_not_match(self):
        initializer = mock()
        when(initializer).is_applicable(any()).thenReturn(False)

        self.execution_manager.register_initializer(initializer)

        environments = []
        self.execution_manager.execute_initializers(environments, a=1)

        verify(initializer).is_applicable(environments)
        verify(initializer, 0).execute(any())


class ExecutionManagerTaskTest(ExecutionManagerTestBase):

    def test_ensure_task_is_added_when_calling_register_task(self):
        task = mock()
        self.execution_manager.register_task(task)
        self.assertEquals([task], self.execution_manager.tasks)

    def test_ensure_task_is_replaced_when_registering_two_tasks_with_same_name(self):
        original = mock(name="spam")
        replacement = mock(name="spam")

        self.execution_manager.register_task(original)
        self.execution_manager.register_task(replacement)

        verify(original).extend(replacement)

    def test_should_raise_exception_when_calling_execute_task_before_resolve_dependencies(self):
        self.assertRaises(DependenciesNotResolvedException,
                          self.execution_manager.execute_task,
                          mock())

    def test_ensure_task_is_executed_when_calling_execute_task(self):
        task = mock(name="spam", dependencies=[])

        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task, a=1)

        verify(task).execute(any(), {"a": 1})

    def test_ensure_before_action_is_executed_when_task_is_executed(self):
        task = mock(name="task", dependencies=[])
        action = mock(name="action", execute_before=["task"], execute_after=[])

        self.execution_manager.register_action(action)
        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task)

        verify(action).execute({})
        verify(task).execute(any(), {})

    def test_ensure_after_action_is_executed_when_task_is_executed(self):
        task = mock(name="task", dependencies=[])
        action = mock(name="action", execute_before=[], execute_after=["task"])

        self.execution_manager.register_action(action)
        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task)

        verify(action).execute({})
        verify(task).execute(any(), {})

    def test_should_return_single_task_name(self):
        self.execution_manager.register_task(mock(name="spam"))
        self.assertEquals(["spam"], self.execution_manager.task_names)

    def test_should_return_all_task_names(self):
        self.execution_manager.register_task(
            mock(name="spam"), mock(name="eggs"))
        self.assertEquals(["eggs", "spam"], self.execution_manager.task_names)


class ExecutionManagerActionTest(ExecutionManagerTestBase):

    def test_ensure_action_is_registered(self):
        action = mock(name="action")
        self.execution_manager.register_action(action)
        self.assertEquals({"action": action}, self.execution_manager._actions)

    def test_ensure_action_registered_for_two_tasks_is_executed_two_times(self):
        spam = mock(name="spam", dependencies=[])
        eggs = mock(name="eggs", dependencies=[])
        self.execution_manager.register_task(spam, eggs)

        action = mock(name="action",
                      execute_before=[],
                      execute_after=["spam", "eggs"],
                      only_once=False)
        self.execution_manager.register_action(action)

        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([spam, eggs])

        verify(action, times(2)).execute(any())

    def test_ensure_action_registered_for_two_tasks_is_executed_only_once_if_single_attribute_is_present(self):
        spam = mock(name="spam", dependencies=[])
        eggs = mock(name="eggs", dependencies=[])
        self.execution_manager.register_task(spam, eggs)

        action = mock(name="action",
                      execute_before=[],
                      execute_after=["spam", "eggs"],
                      only_once=True)
        self.execution_manager.register_action(action)

        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([spam, eggs])

        verify(action, times(1)).execute(any())


class ExecutionManagerResolveDependenciesTest(ExecutionManagerTestBase):

    def test_ensure_that_dependencies_are_resolved_when_no_task_is_given(self):
        self.execution_manager.resolve_dependencies()
        self.assertTrue(self.execution_manager._dependencies_resolved)

    def test_ensure_that_dependencies_are_resolved_when_single_task_is_given(self):
        task = mock(dependencies=[])

        self.execution_manager.register_task(task)

        self.execution_manager.resolve_dependencies()
        self.assertTrue(self.execution_manager._dependencies_resolved)

    def test_should_raise_exception_when_task_depends_on_task_not_found(self):
        task = mock(dependencies=["not_found"])

        self.execution_manager.register_task(task)

        self.assertRaises(MissingTaskDependencyException,
                          self.execution_manager.resolve_dependencies)

    def test_should_raise_exception_when_before_action_depends_on_task_not_found(self):
        action = mock(execute_before=["not_found"], execute_after=[])

        self.execution_manager.register_action(action)

        self.assertRaises(MissingActionDependencyException,
                          self.execution_manager.resolve_dependencies)

    def test_should_raise_exception_when_after_action_depends_on_task_not_found(self):
        action = mock(execute_before=[], execute_after=["not_found"])

        self.execution_manager.register_action(action)

        self.assertRaises(MissingActionDependencyException,
                          self.execution_manager.resolve_dependencies)

    def test_ensure_that_dependencies_are_resolved_when_simple_dependency_is_found(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)

        self.execution_manager.resolve_dependencies()

        self.assertEquals(
            [], self.execution_manager._task_dependencies.get("one"))
        self.assertEquals(
            [one], self.execution_manager._task_dependencies.get("two"))

    def test_ensure_that_dependencies_are_resolved_when_task_depends_on_multiple_tasks(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])
        three = mock(name="three", dependencies=["one", "two"])

        self.execution_manager.register_task(one, two, three)

        self.execution_manager.resolve_dependencies()

        self.assertEquals(
            [], self.execution_manager._task_dependencies.get("one"))
        self.assertEquals(
            [one], self.execution_manager._task_dependencies.get("two"))
        self.assertEquals(
            [one, two], self.execution_manager._task_dependencies.get("three"))


class ExecutionManagerBuildExecutionPlanTest(ExecutionManagerTestBase):

    def test_should_raise_exception_when_building_execution_plan_and_dependencies_are_not_resolved(self):
        self.assertRaises(DependenciesNotResolvedException,
                          self.execution_manager.build_execution_plan, ("boom",))

    def test_should_raise_exception_when_building_execution_plan_for_task_not_found(self):
        self.execution_manager.resolve_dependencies()
        self.assertRaises(
            NoSuchTaskException, self.execution_manager.build_execution_plan, ("boom",))

    def test_should_return_execution_plan_with_single_task_when_single_task_is_to_be_executed(self):
        one = mock(name="one", dependencies=[])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertEqual(
            [one], self.execution_manager.build_execution_plan(["one"]))

    def test_should_return_execution_plan_with_two_tasks_when_two_tasks_are_to_be_executed(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=[])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual(
            [one, two], self.execution_manager.build_execution_plan(["one", "two"]))

    def test_ensure_that_dependencies_are_executed_before_root_task(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual(
            [one, two], self.execution_manager.build_execution_plan(["two"]))

    def test_ensure_that_tasks_are_not_executed_multiple_times(self):
        one = mock(name="one", dependencies=[])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertEqual(
            [one], self.execution_manager.build_execution_plan(["one", "one"]))

    def test_ensure_that_tasks_are_not_executed_multiple_times_when_being_dependencies(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual(
            [one, two], self.execution_manager.build_execution_plan(["one", "two"]))

    def test_should_raise_exception_when_circular_reference_is_detected_on_single_task(self):
        one = mock(name="one", dependencies=["one"])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException,
                          self.execution_manager.build_execution_plan, ["one"])

    def test_should_raise_exception_when_circular_reference_is_detected_on_two_tasks(self):
        one = mock(name="one", dependencies=["two"])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)

        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException,
                          self.execution_manager.build_execution_plan, ["one"])

    def test_should_raise_exception_when_circular_reference_is_detected_on_three_tasks(self):
        one = mock(name="one", dependencies=["three"])
        two = mock(name="two", dependencies=["one"])
        three = mock(name="three", dependencies=["one", "two"])

        self.execution_manager.register_task(one, two, three)

        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException,
                          self.execution_manager.build_execution_plan, ["one"])


class ExecutionManagerExecuteExecutionPlanTest(ExecutionManagerTestBase):

    def test_should_raise_exception_when_dependencies_are_not_resolved(self):
        self.assertRaises(DependenciesNotResolvedException,
                          self.execution_manager.execute_execution_plan, ["boom"])

    def test_ensure_tasks_are_executed(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=[])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([one, two])

        verify(one).execute(any(), {})
        verify(two).execute(any(), {})

########NEW FILE########
__FILENAME__ = external_command_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from mock import Mock, patch, call

from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from pybuilder.core import Project


class ExternalCommandBuilderTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('/base/dir')
        self.command = ExternalCommandBuilder('command-name', self.project)

    def test_should_only_use_command_name_by_default(self):
        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_unconditional_argument_to_command(self):
        self.command.use_argument('--foo=bar')

        self.assertEqual(self.command.as_string, 'command-name --foo=bar')

    def test_should_add_conditional_argument_when_property_is_truthy(self):
        self.project.set_property('verbose', True)
        self.command.use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy(self):
        self.project.set_property('verbose', False)
        self.command.use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_conditional_argument_when_property_is_truthy_after_unconditional_argument(self):
        self.project.set_property('verbose', True)
        self.command.use_argument('--cool').use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy_after_unconditional_argument(self):
        self.project.set_property('verbose', False)
        self.command.use_argument('--cool').use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool')

    def test_should_format_unconditional_argument_with_property_when_given(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_include_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.project.set_property('falsy', None)
        self.command.use_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('falsy')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_include_conditional_argument_with_truthy_formatting(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_falsy_formatting(self):
        self.project.set_property('name', None)
        self.command.use_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name')


class ExternalCommandExecutionTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('/base/dir')
        self.command = ExternalCommandBuilder('command-name', self.project)
        self.command.use_argument('--foo').use_argument('--bar')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_on_production_source_files(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        logger = Mock()
        self.command.run_on_production_source_files(logger)

        execution.assert_called_with(
            include_test_sources=False,
            include_scripts=False,
            project=self.project,
            logger=logger,
            command_and_arguments=['command-name', '--foo', '--bar'],
            name='command-name')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_on_production_and_test_source_files(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        logger = Mock()
        self.command.run_on_production_and_test_source_files(logger)

        execution.assert_called_with(
            include_test_sources=True,
            include_scripts=False,
            project=self.project,
            logger=logger,
            command_and_arguments=['command-name', '--foo', '--bar'],
            name='command-name')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_and_return_execution_result(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        read.side_effect = lambda argument: {
            '/tmp/reports/command-name': ['Running...', 'OK all done!'],
            '/tmp/reports/command-name.err': ['Oh no! I am not python8 compatible!', 'I will explode now.']
        }[argument]
        logger = Mock()

        result = self.command.run_on_production_source_files(logger)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report_file, '/tmp/reports/command-name')
        self.assertEqual(read.call_args_list[0], call('/tmp/reports/command-name'))
        self.assertEqual(result.report_lines, ['Running...', 'OK all done!'])
        self.assertEqual(result.error_report_file, '/tmp/reports/command-name.err')
        self.assertEqual(read.call_args_list[1], call('/tmp/reports/command-name.err'))
        self.assertEqual(result.error_report_lines, ['Oh no! I am not python8 compatible!', 'I will explode now.'])

########NEW FILE########
__FILENAME__ = pluginloader_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest
import sys

builtin_module = None
try:
    import __builtin__
    builtin_module = __builtin__
except ImportError as e:
    import builtins
    builtin_module = builtins

from mockito import when, verify, unstub, never  # TODO @mriehl get rid of mockito here
from mock import patch, Mock, ANY
from test_utils import mock  # TODO @mriehl WTF is this sorcery?!

from pybuilder.errors import MissingPluginException
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    ThirdPartyPluginLoader,
                                    DownloadingPluginLoader,
                                    _install_external_plugin)


class ThirdPartyPluginLoaderTest(unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.loader = ThirdPartyPluginLoader(mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self):
        when(builtin_module).__import__(
            "spam").thenRaise(ImportError())

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(builtin_module).__import__("spam")

    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_third_party(self):
        old_module = sys.modules.get("spam")
        try:
            plugin_module = mock()
            sys.modules["spam"] = plugin_module
            when(builtin_module).__import__(
                "spam").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("spam")
        finally:
            del sys.modules["spam"]
            if old_module:
                sys.modules["spam"] = old_module

    def test_should_remove_pypi_protocol_when_importing(self):
        old_module = sys.modules.get("spam")
        try:
            plugin_module = mock()
            sys.modules["spam"] = plugin_module
            when(builtin_module).__import__(
                "pypi:spam").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("spam")
        finally:
            del sys.modules["spam"]
            if old_module:
                sys.modules["spam"] = old_module


class DownloadingPluginLoaderTest(unittest.TestCase):

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_download_module_from_pypi(self, install, _):
        logger = Mock()
        DownloadingPluginLoader(logger).load_plugin(Mock(), "pypi:external_plugin")

        install.assert_called_with("pypi:external_plugin", logger)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_load_module_after_downloading_when_download_succeeds(self, _, load):
        project = Mock()
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(project, "pypi:external_plugin")

        load.assert_called_with(downloader, project, "pypi:external_plugin")
        self.assertEquals(plugin, load.return_value)

    @patch("pybuilder.pluginloader.ThirdPartyPluginLoader.load_plugin")
    @patch("pybuilder.pluginloader._install_external_plugin")
    def test_should_not_load_module_after_downloading_when_download_fails(self, install, load):
        install.side_effect = MissingPluginException("BOOM")
        downloader = DownloadingPluginLoader(Mock())
        plugin = downloader.load_plugin(Mock(), "pypi:external_plugin")

        self.assertFalse(load.called)
        self.assertEquals(plugin, None)


class InstallExternalPluginTests(unittest.TestCase):

    def test_should_raise_error_when_protocol_is_invalid(self):
        self.assertRaises(MissingPluginException, _install_external_plugin, "some-plugin", Mock())

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pluginloader.execute_command")
    def test_should_install_plugin(self, execute, _, read_file):
        read_file.return_value = ["no problems", "so far"]
        execute.return_value = 0

        _install_external_plugin("pypi:some-plugin", Mock())

        execute.assert_called_with('pip install some-plugin', ANY, shell=True, error_file_name=ANY)

    @patch("pybuilder.pluginloader.read_file")
    @patch("pybuilder.pluginloader.tempfile")
    @patch("pybuilder.pluginloader.execute_command")
    def test_should_raise_error_when_install_from_pypi_fails(self, execute, _, read_file):
        read_file.return_value = ["something", "went wrong"]
        execute.return_value = 1

        self.assertRaises(MissingPluginException, _install_external_plugin, "pypi:some-plugin", Mock())


class BuiltinPluginLoaderTest(unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.loader = BuiltinPluginLoader(mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_requiring_plugin_and_plugin_is_not_found(self):
        when(builtin_module).__import__(
            "pybuilder.plugins.spam_plugin").thenRaise(ImportError())

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")

    def test_should_import_plugin_when_requiring_plugin_and_plugin_is_found_as_builtin(self):
        old_module = sys.modules.get("pybuilder.plugins.spam_plugin")
        try:
            plugin_module = mock()
            sys.modules["pybuilder.plugins.spam_plugin"] = plugin_module
            when(builtin_module).__import__(
                "pybuilder.plugins.spam_plugin").thenReturn(plugin_module)

            self.loader.load_plugin(self.project, "spam")

            verify(builtin_module).__import__("pybuilder.plugins.spam_plugin")
        finally:
            del sys.modules["pybuilder.plugins.spam_plugin"]
            if old_module:
                sys.modules["pybuilder.plugins.spam_plugin"] = old_module


class DispatchingPluginLoaderTest (unittest.TestCase):

    def setUp(self):
        self.project = mock()
        self.fist_delegatee = mock()
        self.second_delegatee = mock()

        self.loader = DispatchingPluginLoader(
            mock, self.fist_delegatee, self.second_delegatee)

    def test_should_raise_exception_when_all_delgatees_raise_exception(self):
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))

        self.assertRaises(
            MissingPluginException, self.loader.load_plugin, self.project, "spam")

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_should_return_module_returned_by_second_loader_when_first_delgatee_raises_exception(self):
        result = "result"
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenRaise(MissingPluginException("spam"))
        when(self.second_delegatee).load_plugin(
            self.project, "spam").thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee).load_plugin(self.project, "spam")

    def test_ensure_second_delegatee_is_not_trie_when_first_delegatee_loads_plugin(self):
        result = "result"
        when(self.fist_delegatee).load_plugin(
            self.project, "spam").thenReturn(result)

        self.assertEquals(
            result, self.loader.load_plugin(self.project, "spam"))

        verify(self.fist_delegatee).load_plugin(self.project, "spam")
        verify(self.second_delegatee, never).load_plugin(self.project, "spam")

########NEW FILE########
__FILENAME__ = filter_resources_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from mockito import when, verify, never
from test_utils import mock

from pybuilder.core import Project
from pybuilder.plugins.filter_resources_plugin import ProjectDictWrapper


class ProjectDictWrapperTest (unittest.TestCase):

    def test_should_return_project_property_when_property_is_defined(self):
        project_mock = mock(Project, name="my name")

        self.assertEquals("my name", ProjectDictWrapper(project_mock)["name"])

        verify(project_mock, never).get_property("name", "name")

    def test_should_delegate_to_project_get_property_when_attribute_is_not_defined(self):
        project_mock = Project(".")
        when(project_mock).get_property("spam", "spam").thenReturn("eggs")

        self.assertEquals("eggs", ProjectDictWrapper(project_mock)["spam"])

        verify(project_mock).get_property("spam", "spam")

########NEW FILE########
__FILENAME__ = core_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from mock import patch

from pybuilder.plugins.python.core_plugin import init_python_directories
from pybuilder.plugins.python.core_plugin import (DISTRIBUTION_PROPERTY,
                                                  PYTHON_SOURCES_PROPERTY,
                                                  SCRIPTS_SOURCES_PROPERTY,
                                                  SCRIPTS_TARGET_PROPERTY)
from pybuilder.core import Project


class InitPythonDirectoriesTest (unittest.TestCase):

    def greedy(self, generator):
        return [element for element in generator]

    def setUp(self):
        self.project = Project(".")

    @patch("pybuilder.plugins.python.core_plugin.os.listdir")
    @patch("pybuilder.plugins.python.core_plugin.os.path.isfile")
    def test_should_set_list_modules_function_with_project_modules(self, _, source_listdir):
        source_listdir.return_value = ["foo.py", "bar.py", "some-package"]

        init_python_directories(self.project)

        self.assertEquals(
            ['foo', 'bar'],
            self.greedy(self.project.list_modules())
        )

    def test_should_set_python_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals(
            "src/main/python", self.project.get_property(PYTHON_SOURCES_PROPERTY, "caboom"))

    def test_should_set_scripts_sources_property(self):
        init_python_directories(self.project)
        self.assertEquals(
            "src/main/scripts", self.project.get_property(SCRIPTS_SOURCES_PROPERTY, "caboom"))

    def test_should_set_dist_scripts_property(self):
        init_python_directories(self.project)
        self.assertEquals(
            None, self.project.get_property(SCRIPTS_TARGET_PROPERTY, "caboom"))

    def test_should_set_dist_property(self):
        init_python_directories(self.project)
        self.assertEquals("$dir_target/dist/.-1.0-SNAPSHOT",
                          self.project.get_property(DISTRIBUTION_PROPERTY, "caboom"))

########NEW FILE########
__FILENAME__ = cram_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from mock import patch, Mock, call

from pybuilder.core import Project
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.cram_plugin import (
    _cram_command_for,
    _find_files,
    _report_file,
    run_cram_tests,
)


class CramPluginTests(unittest.TestCase):

    def test_command_respects_no_verbose(self):
        project = Project('.')
        project.set_property('verbose', False)
        expected = ['cram']
        received = _cram_command_for(project)
        self.assertEquals(expected, received)

    def test_command_respects_verbose(self):
        project = Project('.')
        project.set_property('verbose', True)
        expected = ['cram', '--verbose']
        received = _cram_command_for(project)
        self.assertEquals(expected, received)

    @patch('pybuilder.plugins.python.cram_plugin.discover_files_matching')
    def test_find_files(self, discover_mock):
        project = Project('.')
        project.set_property('dir_source_cmdlinetest', '/any/dir')
        project.set_property('cram_test_file_glob', '*.t')
        expected = ['/any/dir/test.cram']
        discover_mock.return_value = expected
        received = _find_files(project)
        self.assertEquals(expected, received)
        discover_mock.assert_called_once_with('/any/dir', '*.t')

    def test_report(self):
        project = Project('.')
        project.set_property('dir_reports', '/any/dir')
        expected = './any/dir/cram.err'
        received = _report_file(project)
        self.assertEquals(expected, received)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('os.environ')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    @patch('pybuilder.plugins.python.cram_plugin.execute_command')
    def test_running_plugin(self,
                            execute_mock,
                            read_file_mock,
                            os_mock,
                            report_mock,
                            find_files_mock,
                            command_mock
                            ):
        project = Project('.')
        project.set_property('verbose', False)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        logger = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        os_mock.copy.return_value = {}
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 0

        run_cram_tests(project, logger)
        execute_mock.assert_called_once_with(
            ['cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': './python:', 'PATH': './scripts:'}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               call('Cram tests were fine'),
                               call('results'),
                               ]
        self.assertEquals(expected_info_calls, logger.info.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('os.environ')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    @patch('pybuilder.plugins.python.cram_plugin.execute_command')
    def test_running_plugin_fails(self,
                                  execute_mock,
                                  read_file_mock,
                                  os_mock,
                                  report_mock,
                                  find_files_mock,
                                  command_mock
                                  ):
        project = Project('.')
        project.set_property('verbose', False)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        logger = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        os_mock.copy.return_value = {}
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 1

        self.assertRaises(BuildFailedException, run_cram_tests, project, logger)
        execute_mock.assert_called_once_with(
            ['cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': './python:', 'PATH': './scripts:'}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               ]
        expected_error_calls = [call('Cram tests failed!'),
                                call('results'),
                                call("See: 'report_file' for details"),
                                ]
        self.assertEquals(expected_info_calls, logger.info.call_args_list)
        self.assertEquals(expected_error_calls, logger.error.call_args_list)

    @patch('pybuilder.plugins.python.cram_plugin._cram_command_for')
    @patch('pybuilder.plugins.python.cram_plugin._find_files')
    @patch('pybuilder.plugins.python.cram_plugin._report_file')
    @patch('os.environ')
    @patch('pybuilder.plugins.python.cram_plugin.read_file')
    @patch('pybuilder.plugins.python.cram_plugin.execute_command')
    def test_running_plugin_fails_with_verbose(self,
                                               execute_mock,
                                               read_file_mock,
                                               os_mock,
                                               report_mock,
                                               find_files_mock,
                                               command_mock
                                               ):
        project = Project('.')
        project.set_property('verbose', True)
        project.set_property('dir_source_main_python', 'python')
        project.set_property('dir_source_main_scripts', 'scripts')
        logger = Mock()

        command_mock.return_value = ['cram']
        find_files_mock.return_value = ['test1.cram', 'test2.cram']
        report_mock.return_value = 'report_file'
        os_mock.copy.return_value = {}
        read_file_mock.return_value = ['test failes for file', '# results']
        execute_mock.return_value = 1

        self.assertRaises(BuildFailedException, run_cram_tests, project, logger)
        execute_mock.assert_called_once_with(
            ['cram', 'test1.cram', 'test2.cram'], 'report_file',
            error_file_name='report_file',
            env={'PYTHONPATH': './python:', 'PATH': './scripts:'}
        )
        expected_info_calls = [call('Running Cram command line tests'),
                               ]
        expected_error_calls = [call('Cram tests failed!'),
                                call('test failes for file'),
                                call('# results'),
                                call("See: 'report_file' for details"),
                                ]
        self.assertEquals(expected_info_calls, logger.info.call_args_list)
        self.assertEquals(expected_error_calls, logger.error.call_args_list)

########NEW FILE########
__FILENAME__ = distutils_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from test_utils import PyBuilderTestCase
from pybuilder.core import Project, Author
from pybuilder.plugins.python.distutils_plugin import (build_data_files_string,
                                                       build_dependency_links_string,
                                                       build_install_dependencies_string,
                                                       build_package_data_string,
                                                       default,
                                                       render_manifest_file,
                                                       render_setup_script)


class InstallDependenciesTest(unittest.TestCase):

    def setUp(self):
        self.project = Project(".")

    def test_should_return_empty_string_when_no_dependency_is_given(self):
        self.assertEqual("", build_install_dependencies_string(self.project))

    def test_should_return_single_dependency_string(self):
        self.project.depends_on("spam")
        self.assertEqual(
            'install_requires = [ "spam" ],', build_install_dependencies_string(self.project))

    def test_should_return_single_dependency_string_with_version(self):
        self.project.depends_on("spam", "0.7")
        self.assertEqual(
            'install_requires = [ "spam>=0.7" ],', build_install_dependencies_string(self.project))

    def test_should_return_multiple_dependencies_string_with_versions(self):
        self.project.depends_on("spam", "0.7")
        self.project.depends_on("eggs")
        self.assertEqual(
            'install_requires = [ "eggs", "spam>=0.7" ],', build_install_dependencies_string(self.project))

    def test_should_not_insert_url_dependency_into_install_requires(self):
        self.project.depends_on("spam")
        self.project.depends_on(
            "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")

        self.assertEqual(
            'install_requires = [ "spam" ],', build_install_dependencies_string(self.project))

    def test_should_not_insert_default_version_operator_when_project_contains_operator_in_version(self):
        self.project.depends_on("spam", "==0.7")
        self.assertEqual(
            'install_requires = [ "spam==0.7" ],', build_install_dependencies_string(self.project))


class DependencyLinksTest(unittest.TestCase):

    def setUp(self):
        self.project = Project(".")

    def test_should_return_empty_string_when_no_link_dependency_is_given(self):
        self.assertEqual("", build_dependency_links_string(self.project))

    def test_should_return_dependency_link(self):
        self.project.depends_on(
            "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
        self.assertEqual(
            'dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz" ],',
            build_dependency_links_string(self.project))

    def test_should_return_dependency_links(self):
        self.project.depends_on("pyassert1",
                                url="https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz")
        self.project.depends_on("pyassert2",
                                url="https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz")
        self.assertEqual('dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz",'
                         ' "https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz" ],',
                         build_dependency_links_string(self.project))


class DefaultTest(unittest.TestCase):

    def test_should_return_empty_string_as_default_when_given_value_is_none(self):
        self.assertEqual("", default(None))

    def test_should_return_given_default_when_given_value_is_none(self):
        self.assertEqual("default", default(None, default="default"))

    def test_should_return_value_string_when_value_given(self):
        self.assertEqual("value", default("value"))

    def test_should_return_value_string_when_value_and_default_given(self):
        self.assertEqual("value", default("value", default="default"))


class BuildDataFilesStringTest(unittest.TestCase):

    def setUp(self):
        self.project = Project(".")

    def test_should_return_empty_data_files_string(self):
        self.assertEqual("", build_data_files_string(self.project))

    def test_should_return_data_files_string_including_several_files(self):
        self.project.install_file("bin", "activate")
        self.project.install_file("bin", "command-stub")
        self.project.install_file("bin", "rsync")
        self.project.install_file("bin", "ssh")

        self.assertEqual(
            "data_files = [('bin', ['activate', 'command-stub', 'rsync', 'ssh'])],",
            build_data_files_string(self.project))

    def test_should_return_data_files_string_with_files_to_be_installed_in_several_destinations(self):
        self.project.install_file("/usr/bin", "pyb")
        self.project.install_file("/etc", "pyb.cfg")
        self.project.install_file("data", "pyb.dat")
        self.project.install_file("data", "howto.txt")
        self.assertEqual("data_files = [('/usr/bin', ['pyb']), ('/etc', ['pyb.cfg']),"
                         " ('data', ['pyb.dat', 'howto.txt'])],",
                         build_data_files_string(self.project))


class BuildPackageDataStringTest(unittest.TestCase):

    def setUp(self):
        self.project = Project('.')

    def test_should_return_empty_package_data_string_when_no_files_to_include_given(self):
        self.assertEqual('', build_package_data_string(self.project))

    def test_should_return_package_data_string_when_including_file(self):
        self.project.include_file("spam", "egg")

        self.assertEqual(
            "package_data = {'spam': ['egg']},", build_package_data_string(self.project))

    def test_should_return_package_data_string_when_including_three_files(self):
        self.project.include_file("spam", "egg")
        self.project.include_file("ham", "eggs")
        self.project.include_file("monty", "python")

        self.assertEqual("package_data = {'ham': ['eggs'], 'monty': ['python'], "
                         "'spam': ['egg']},", build_package_data_string(self.project))

    def test_should_return_package_data_string_with_keys_in_alphabetical_order(self):
        self.project.include_file("b", "beta")
        self.project.include_file("m", "Mu")
        self.project.include_file("e", "epsilon")
        self.project.include_file("k", "Kappa")
        self.project.include_file("p", "psi")
        self.project.include_file("z", "Zeta")
        self.project.include_file("i", "Iota")
        self.project.include_file("a", "alpha")
        self.project.include_file("d", "delta")
        self.project.include_file("t", "theta")
        self.project.include_file("l", "lambda")
        self.project.include_file("x", "chi")

        self.assertEqual("package_data = {'a': ['alpha'], 'b': ['beta'], 'd': ['delta'], "
                         "'e': ['epsilon'], 'i': ['Iota'], 'k': ['Kappa'], 'l': ['lambda'], "
                         "'m': ['Mu'], 'p': ['psi'], 't': ['theta'], 'x': ['chi'], "
                         "'z': ['Zeta']},", build_package_data_string(self.project))


class RenderSetupScriptTest(PyBuilderTestCase):

    def setUp(self):
        self.project = create_project()

    def test_should_remove_hardlink_capabilities_when_workaround_is_enabled(self):
        self.project.set_property("distutils_issue8876_workaround_enabled", True)

        actual_setup_script = render_setup_script(self.project)

        self.assertTrue("import os\ndel os.link\n" in actual_setup_script)

    def test_should_not_remove_hardlink_capabilities_when_workaround_is_disabled(self):
        self.project.set_property("distutils_issue8876_workaround_enabled", False)

        actual_setup_script = render_setup_script(self.project)

        self.assertFalse("import os\ndel os.link\n" in actual_setup_script)

    def test_should_render_setup_file(self):
        actual_setup_script = render_setup_script(self.project)

        self.assert_line_by_line_equal("""#!/usr/bin/env python

from distutils.core import setup

if __name__ == '__main__':
    setup(
          name = 'Spam and Eggs',
          version = '1.2.3',
          description = '''This is a simple integration-test for distutils plugin.''',
          long_description = '''As you might have guessed we have nothing to say here.''',
          author = "Udo Juettner, Michael Gruber",
          author_email = "udo.juettner@gmail.com, aelgru@gmail.com",
          license = 'WTFPL',
          url = 'http://github.com/pybuilder/pybuilder',
          scripts = ['spam', 'eggs'],
          packages = ['spam', 'eggs'],
          py_modules = ['spam', 'eggs'],
          classifiers = ['Development Status :: 5 - Beta', 'Environment :: Console'],
          data_files = [('dir', ['file1', 'file2'])],   #  data files
          package_data = {'spam': ['eggs']},   # package data
          install_requires = [ "sometool" ],
          dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz" ],
          zip_safe=True
    )
""", actual_setup_script)


class RenderManifestFileTest(unittest.TestCase):

    def test_should_render_manifest_file(self):
        project = create_project()

        actual_manifest_file = render_manifest_file(project)

        self.assertEqual("""include file1
include file2
include spam/eggs
""", actual_manifest_file)


def create_project():
    project = Project("/")
    project.build_depends_on("testingframework")
    project.depends_on("sometool")
    project.depends_on(
        "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
    project.name = "Spam and Eggs"
    project.version = "1.2.3"
    project.summary = "This is a simple integration-test for distutils plugin."
    project.description = "As you might have guessed we have nothing to say here."
    project.authors = [
        Author("Udo Juettner", "udo.juettner@gmail.com"), Author("Michael Gruber", "aelgru@gmail.com")]
    project.license = "WTFPL"
    project.url = "http://github.com/pybuilder/pybuilder"

    def return_dummy_list():
        return ["spam", "eggs"]

    project.list_scripts = return_dummy_list
    project.list_packages = return_dummy_list
    project.list_modules = return_dummy_list

    project.set_property("distutils_classifiers", [
                         "Development Status :: 5 - Beta", "Environment :: Console"])
    project.install_file("dir", "file1")
    project.install_file("dir", "file2")
    project.include_file("spam", "eggs")

    return project

########NEW FILE########
__FILENAME__ = install_dependencies_plugin_tests
#  This file is part of pybuilder
#
#  Copyright 2011 The pybuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

__author__ = "Alexander Metzner"

import unittest

from mockito import mock, when, verify, unstub, any as any_value

from pybuilder.core import Project, Logger, Dependency
from pybuilder.plugins.python.install_dependencies_plugin import (
    install_runtime_dependencies,
    install_build_dependencies,
    install_dependencies,
    install_dependency)

import pybuilder.plugins.python.install_dependencies_plugin


class InstallDependencyTest(unittest.TestCase):

    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.logger = mock(Logger)
        when(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command(any_value(), any_value(),
                                                                                  shell=True).thenReturn(0)

    def tearDown(self):
        unstub()

    def test_should_install_dependency_without_version(self):
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        verify(pybuilder.plugins.python.install_dependencies_plugin).execute_command(
            "pip install 'spam'", any_value(), shell=True)

    def test_should_install_dependency_using_custom_index_url(self):
        self.project.set_property(
            "install_dependencies_index_url", "some_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        verify(pybuilder.plugins.python.install_dependencies_plugin).execute_command(
            "pip install --index-url some_index_url 'spam'", any_value(), shell=True)

    def test_should_not_use_extra_index_url_when_index_url_is_not_set(self):
        self.project.set_property(
            "install_dependencies_extra_index_url", "some_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        verify(pybuilder.plugins.python.install_dependencies_plugin).execute_command(
            "pip install 'spam'", any_value(), shell=True)

    def test_should_not_use_index_and_extra_index_url_when_index_and_extra_index_url_are_set(self):
        self.project.set_property(
            "install_dependencies_index_url", "some_index_url")
        self.project.set_property(
            "install_dependencies_extra_index_url", "some_extra_index_url")
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        verify(pybuilder.plugins.python.install_dependencies_plugin).execute_command(
            "pip install --index-url some_index_url --extra-index-url some_extra_index_url 'spam'", any_value(
            ), shell=True)

    def test_should_upgrade_dependencies(self):
        self.project.set_property("install_dependencies_upgrade", True)
        dependency = Dependency("spam")

        install_dependency(self.logger, self.project, dependency)

        verify(pybuilder.plugins.python.install_dependencies_plugin).execute_command(
            "pip install --upgrade 'spam'", any_value(), shell=True)

    def test_should_install_dependency_with_version(self):
        dependency = Dependency("spam", "0.1.2")

        install_dependency(self.logger, self.project, dependency)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'spam>=0.1.2'",
                                                                                  any_value(), shell=True)

    def test_should_install_dependency_with_version_and_operator(self):
        dependency = Dependency("spam", "==0.1.2")

        install_dependency(self.logger, self.project, dependency)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'spam==0.1.2'",
                                                                                  any_value(), shell=True)

    def test_should_install_dependency_with_url(self):
        dependency = Dependency("spam", url="some_url")

        install_dependency(self.logger, self.project, dependency)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'some_url'",
                                                                                  any_value(), shell=True)

    def test_should_install_dependency_with_url_even_if_version_is_given(self):
        dependency = Dependency("spam", version="0.1.2", url="some_url")

        install_dependency(self.logger, self.project, dependency)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'some_url'",
                                                                                  any_value(), shell=True)


class InstallRuntimeDependenciesTest(unittest.TestCase):

    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.logger = mock(Logger)
        when(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command(any_value(), any_value(),
                                                                                  shell=True).thenReturn(0)

    def tearDown(self):
        unstub()

    def test_should_install_multiple_dependencies(self):
        self.project.depends_on("spam")
        self.project.depends_on("eggs")

        install_runtime_dependencies(self.logger, self.project)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'spam'",
                                                                                  any_value(), shell=True)
        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'eggs'",
                                                                                  any_value(), shell=True)


class InstallBuildDependenciesTest(unittest.TestCase):

    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.logger = mock(Logger)
        when(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command(any_value(), any_value(),
                                                                                  shell=True).thenReturn(0)

    def tearDown(self):
        unstub()

    def test_should_install_multiple_dependencies(self):
        self.project.build_depends_on("spam")
        self.project.build_depends_on("eggs")

        install_build_dependencies(self.logger, self.project)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'spam'",
                                                                                  any_value(), shell=True)
        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'eggs'",
                                                                                  any_value(), shell=True)


class InstallDependenciesTest(unittest.TestCase):

    def setUp(self):
        self.project = Project("unittest", ".")
        self.project.set_property("dir_install_logs", "any_directory")
        self.logger = mock(Logger)
        when(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command(any_value(), any_value(),
                                                                                  shell=True).thenReturn(0)

    def tearDown(self):
        unstub()

    def test_should_install_single_dependency_without_version(self):
        self.project.depends_on("spam")
        self.project.build_depends_on("eggs")

        install_dependencies(self.logger, self.project)

        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'spam'",
                                                                                  any_value(), shell=True)
        verify(
            pybuilder.plugins.python.install_dependencies_plugin).execute_command("pip install 'eggs'",
                                                                                  any_value(), shell=True)

########NEW FILE########
__FILENAME__ = integrationtest_plugin_tests
# -*- coding: utf-8 -*-

#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest
try:
    from queue import Empty
except ImportError:
    from Queue import Empty

from mock import patch

from pybuilder.core import Project
from pybuilder.plugins.python.integrationtest_plugin import (TaskPoolProgress,
                                                             add_additional_environment_keys,
                                                             ConsumingQueue)


class TaskPoolProgressTests(unittest.TestCase):

    def setUp(self):
        self.progress = TaskPoolProgress(42, 8)

    def test_should_create_new_progress(self):
        self.assertEqual(self.progress.workers_count, 8)
        self.assertEqual(self.progress.finished_tasks_count, 0)
        self.assertEqual(self.progress.total_tasks_count, 42)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_workers(self):
        self.assertEqual(self.progress.running_tasks_count, 8)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks(self):
        progress = TaskPoolProgress(2, 4)

        self.assertEqual(progress.running_tasks_count, 2)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks_after_updating(self):
        self.progress.update(40)

        self.assertEqual(self.progress.running_tasks_count, 2)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting(self):
        self.assertEqual(self.progress.waiting_tasks_count, 42 - 8)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting_after_updating(self):
        self.progress.update(2)

        self.assertEqual(self.progress.waiting_tasks_count, 40 - 8)

    def test_should_not_be_finished_when_tasks_are_still_todo(self):
        self.assertFalse(self.progress.is_finished)

    def test_should_not_be_finished_when_tasks_are_still_running(self):
        progress = TaskPoolProgress(1, 1)

        self.assertFalse(progress.is_finished)

    def test_should_be_finished_when_all_tasks_are_finished(self):
        progress = TaskPoolProgress(1, 1)
        progress.update(1)

        self.assertTrue(progress.is_finished)

    @patch('pybuilder.plugins.python.integrationtest_plugin.sys.stdout')
    def test_should_be_displayed_when_tty_given(self, stdout):
        stdout.isatty.return_value = True

        self.assertTrue(self.progress.can_be_displayed)

    @patch('pybuilder.plugins.python.integrationtest_plugin.sys.stdout')
    def test_should_not_be_displayed_when_no_tty_given(self, stdout):
        stdout.isatty.return_value = False

        self.assertFalse(self.progress.can_be_displayed)

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    def test_should_render_progress(self, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(3)

        self.assertEqual(progress.render(),
                         '[---ᗧ//|||]')

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    def test_should_not_render_pacman_when_finished(self, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(8)

        self.assertEqual(progress.render(),
                         '[--------] ')

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    @patch('pybuilder.plugins.python.integrationtest_plugin.print_text')
    @patch('pybuilder.plugins.python.integrationtest_plugin.TaskPoolProgress.can_be_displayed')
    def test_should_erase_previous_progress_on_subsequent_renders(self, _, print_text, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(2)

        progress.render_to_terminal()
        print_text.assert_called_with('[--ᗧ//||||]', flush=True)
        progress.render_to_terminal()
        print_text.assert_called_with(
            '\b' * (10 + len('ᗧ')) + '[--ᗧ//||||]', flush=True)


class IntegrationTestConfigurationTests(unittest.TestCase):

    def test_should_merge_additional_environment_into_current_one(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', {'foo': 'bar'})
        environment = {'bar': 'baz'}

        add_additional_environment_keys(environment, project)

        self.assertEqual(environment,
                         {
                             'foo': 'bar',
                             'bar': 'baz'
                         })

    def test_should_override_current_environment_keys_with_additional_environment(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', {'foo': 'mooh'})
        environment = {'foo': 'bar'}

        add_additional_environment_keys(environment, project)

        self.assertEqual(environment,
                         {
                             'foo': 'mooh'
                         })

    def test_should_fail_when_additional_environment_is_not_a_map(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', 'meow')
        self.assertRaises(
            ValueError, add_additional_environment_keys, {}, project)


class ConsumingQueueTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_no_items_when_underlying_queue_empty(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            raise Empty()

        underlying_nowait_get.side_effect = empty_queue_get_nowait

        queue.consume_available_items()

        self.assertEqual(queue.items, [])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_one_item_when_underlying_queue_has_one(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield "any-item"
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.items, ['any-item'])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_many_items_when_underlying_queue_has_them(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield "any-item"
            yield "any-other-item"
            yield "some stuff"
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.items, ['any-item',
                                       'any-other-item',
                                       'some stuff'])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_give_item_size_of_zero_when_underlying_queue_is_empty(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            raise Empty()

        # not a generator, beware!!!!
        underlying_nowait_get.side_effect = empty_queue_get_nowait

        queue.consume_available_items()

        self.assertEqual(queue.size, 0)

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_give_item_size_of_n_when_underlying_queue_has_n_elements(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield 'first'
            yield 'second'
            yield 'third'
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.size, 3)

########NEW FILE########
__FILENAME__ = pycharm_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

try:
    TYPE_FILE = file
except NameError:
    from io import FileIO as TYPE_FILE


import unittest
from mock import patch, Mock, MagicMock

from pybuilder.core import Project
from pybuilder.plugins.python.pycharm_plugin import (
    pycharm_generate,
    _ensure_directory_present
)


class PycharmPluginTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.pycharm_plugin.os')
    def test_should_create_pycharm_directory_if_not_present(self, os):
        os.path.exists.return_value = False

        _ensure_directory_present('foo')

        os.makedirs.assert_called_with('foo')

    @patch('pybuilder.plugins.python.pycharm_plugin.os')
    def test_should_not_create_pycharm_directory_if_present(self, os):
        os.path.exists.return_value = True

        _ensure_directory_present('foo')

        self.assertFalse(os.makedirs.called)

    @patch('pybuilder.plugins.python.pycharm_plugin.open', create=True)
    @patch('pybuilder.plugins.python.pycharm_plugin.os')
    def test_should_write_pycharm_file(self, os, mock_open):
        project = Project('basedir', name='pybuilder')
        project.set_property('dir_source_main_python', 'src/main/python')
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        os.path.join.side_effect = lambda first, second: first + '/' + second

        pycharm_generate(project, Mock())

        mock_open.assert_called_with('basedir/.idea/pybuilder.iml', 'w')
        metadata_file = mock_open.return_value.__enter__.return_value
        metadata_file.write.assert_called_with("""<?xml version="1.0" encoding="UTF-8"?>
<!-- This file has been generated by the PyBuilder PyCharm Plugin -->

<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
      <sourceFolder url="file://$MODULE_DIR$/src/main/python" isTestSource="false" />
      <excludeFolder url="file://$MODULE_DIR$/target" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
  <component name="PyDocumentationSettings">
    <option name="myDocStringFormat" value="Plain" />
  </component>
  <component name="TestRunnerService">
    <option name="projectConfiguration" value="Unittests" />
    <option name="PROJECT_TEST_RUNNER" value="Unittests" />
  </component>
</module>
""")

########NEW FILE########
__FILENAME__ = pychecker_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from mockito import mock, when

from pybuilder.plugins.python.pychecker_plugin import (PycheckerModuleReport,
                                                       PycheckerWarning,
                                                       PycheckerReport,
                                                       parse_pychecker_output)


class PycheckerWarningTest (unittest.TestCase):

    def test_to_json_dict(self):
        expected = {
            "message": "any message",
            "line_number": 17
        }
        self.assertEquals(
            expected, PycheckerWarning("any message", 17).to_json_dict())


class PycheckerModuleReportTest (unittest.TestCase):

    def test_to_json_dict(self):
        report = PycheckerModuleReport("any.module")
        report.add_warning(PycheckerWarning("warning 1", 1))
        report.add_warning(PycheckerWarning("warning 2", 2))

        expected = {
            "name": "any.module",
            "warnings": [{"message": "warning 1", "line_number": 1},
                         {"message": "warning 2", "line_number": 2}]
        }
        self.assertEquals(expected, report.to_json_dict())


class PycheckerReportTest (unittest.TestCase):

    def test_to_json_dict(self):

        module_report_one = PycheckerModuleReport("any.module")
        module_report_one.add_warning(PycheckerWarning("warning 1", 1))
        module_report_one.add_warning(PycheckerWarning("warning 2", 2))

        module_report_two = PycheckerModuleReport("any.other.module")
        module_report_two.add_warning(PycheckerWarning("warning 1", 3))
        module_report_two.add_warning(PycheckerWarning("warning 2", 4))

        report = PycheckerReport()
        report.add_module_report(module_report_one)
        report.add_module_report(module_report_two)

        expected = {
            "modules": [
                {
                    "name": "any.module",
                    "warnings": [{"message": "warning 1", "line_number": 1},
                                 {"message": "warning 2", "line_number": 2}]
                },
                {
                    "name": "any.other.module",
                    "warnings": [{"message": "warning 1", "line_number": 3},
                                 {"message": "warning 2", "line_number": 4}]
                }
            ]
        }

        self.assertEquals(expected, report.to_json_dict())


class ParsePycheckerOutputTest (unittest.TestCase):

    def test_should_parse_report(self):
        project = mock()
        when(project).expand_path(
            "$dir_source_main_python").thenReturn("/path/to")

        warnings = [
            "/path/to/package/module_one:2: Sample warning",
            "/path/to/package/module_one:4: Another sample warning",
            "",
            "/path/to/package/module_two:33: Another sample warning",
            "/path/to/package/module_two:332: Yet another sample warning"
        ]

        report = parse_pychecker_output(project, warnings)

        self.assertEquals(2, len(report.module_reports))

        self.assertEquals("package.module_one", report.module_reports[0].name)
        self.assertEquals(2, len(report.module_reports[0].warnings))
        self.assertEquals(
            "Sample warning", report.module_reports[0].warnings[0].message)
        self.assertEquals(2, report.module_reports[0].warnings[0].line_number)
        self.assertEquals("Another sample warning",
                          report.module_reports[0].warnings[1].message)
        self.assertEquals(4, report.module_reports[0].warnings[1].line_number)

        self.assertEquals("package.module_two", report.module_reports[1].name)
        self.assertEquals(2, len(report.module_reports[1].warnings))
        self.assertEquals("Another sample warning",
                          report.module_reports[1].warnings[0].message)
        self.assertEquals(33, report.module_reports[1].warnings[0].line_number)
        self.assertEquals("Yet another sample warning",
                          report.module_reports[1].warnings[1].message)
        self.assertEquals(
            332, report.module_reports[1].warnings[1].line_number)

########NEW FILE########
__FILENAME__ = pydev_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

try:
    TYPE_FILE = file
except NameError:
    from io import FileIO as TYPE_FILE


import unittest
from mock import patch, Mock, MagicMock, call

from pybuilder.core import Project
from pybuilder.plugins.python.pydev_plugin import (
    pydev_generate,
    init_pydev_plugin
)


class PydevPluginTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.pydev_plugin.open', create=True)
    @patch('pybuilder.plugins.python.pydev_plugin.os')
    def test_should_write_pydev_files(self, os, mock_open):
        project = Project('basedir', name='pybuilder')
        project.set_property('dir_source_main_python', 'src/main/python')
        init_pydev_plugin(project)
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        os.path.join.side_effect = lambda first, second: first + '/' + second

        pydev_generate(project, Mock())

        self.assertEqual(mock_open.call_args_list,
                         [call('basedir/.project', 'w'), call('basedir/.pydevproject', 'w')])
        metadata_file = mock_open.return_value.__enter__.return_value

        self.assertEqual(metadata_file.write.call_args_list,
                         [call("""<?xml version="1.0" encoding="UTF-8"?>

<!-- This file has been generated by the PyBuilder Pydev Plugin -->

<projectDescription>
    <name>pybuilder</name>
    <comment></comment>
    <projects>
    </projects>
    <buildSpec>
        <buildCommand>
            <name>org.python.pydev.PyDevBuilder</name>
            <arguments>
            </arguments>
        </buildCommand>
    </buildSpec>
    <natures>
        <nature>org.python.pydev.pythonNature</nature>
    </natures>
</projectDescription>
"""),
                          call("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?eclipse-pydev version="1.0"?>

<!-- This file has been generated by the PyBuilder Pydev Plugin -->

<pydev_project>
    <pydev_property name="org.python.pydev.PYTHON_PROJECT_INTERPRETER">Default</pydev_property>
    <pydev_property name="org.python.pydev.PYTHON_PROJECT_VERSION">python 2.7</pydev_property>
    <pydev_pathproperty name="org.python.pydev.PROJECT_SOURCE_PATH">
\t\t<path>/pybuilder/src/main/python</path>

    </pydev_pathproperty>
</pydev_project>
""")])

########NEW FILE########
__FILENAME__ = pytddmon_plugin_tests
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
from mock import Mock, patch, ANY

from pybuilder.core import Project
from pybuilder.plugins.python import pytddmon_plugin


class PytddmonPluginTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.pytddmon_plugin.subprocess')
    def test_should_run_pytddmon(self, subprocess):
        subprocess.check_output.side_effect = lambda *args, **kwargs: ' '.join(a for a in args)
        project = Project('/path/to/project', name='pybuilder')
        project.set_property('dir_source_main_python', 'path/to/source')
        project.set_property(
            'dir_source_unittest_python', 'src/unittest/python')

        pytddmon_plugin.pytddmon(project, Mock())

        subprocess.Popen.assert_called_with(
            ['which python', 'which pytddmon.py', '--no-pulse'], shell=False, cwd='src/unittest/python', env=ANY)

########NEW FILE########
__FILENAME__ = python_plugin_helper_tests
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
from mock import Mock, call, patch

from pybuilder.plugins.python.python_plugin_helper import (log_report,
                                                           discover_affected_files,
                                                           execute_tool_on_source_files)


class LogReportsTest(unittest.TestCase):

    def test_should_not_warn_when_report_lines_is_empty(self):
        logger = Mock()
        log_report(logger, 'name', [])

        self.assertFalse(logger.warn.called)

    def test_should_warn_when_report_lines_present(self):
        logger = Mock()
        log_report(logger, 'name', ['line1 ', 'line 2 '])

        self.assertEqual(logger.warn.call_args_list,
                         [call('name: line1'), call('name: line 2')])


class DiscoverAffectedFilesTest(unittest.TestCase):

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_not_included(self, discover_python_files):
        project = Mock()
        project.get_property.return_value = 'source_directory'
        discover_python_files.return_value = ['foo.py', 'bar.py']

        files = discover_affected_files(False, False, project)
        discover_python_files.assert_called_with('source_directory')
        self.assertEqual(files, ['foo.py', 'bar.py'])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included(self, discover_python_files):
        project = Mock()

        project.get_property.side_effect = lambda _property: _property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python'),
                          call('dir_source_integrationtest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_files_matching')
    def test_should_discover_source_files_when_scripts_are_included(self, discover_files_matching, _):
        project = Mock()

        project.get_property.return_value = True
        project.get_property.side_effect = lambda _property: _property

        discover_affected_files(False, True, project)

        discover_files_matching.assert_called_with('dir_source_main_scripts', '*')

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_only_unittests(self, discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_integrationtest_python':
                return None
            return property
        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_unittest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_only_integrationtests(self, discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_unittest_python':
                return None
            return property
        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python'),
                          call('dir_source_integrationtest_python')])

    @patch('pybuilder.plugins.python.python_plugin_helper.discover_python_files')
    def test_should_discover_source_files_when_test_sources_are_included_and_no_tests(self, discover_python_files):
        project = Mock()

        def get_property(property):
            if property == 'dir_source_main_python':
                return property
            return None
        project.get_property.side_effect = get_property

        discover_affected_files(True, False, project)

        self.assertEqual(discover_python_files.call_args_list,
                         [call('dir_source_main_python')])


class ExecuteToolOnSourceFilesTest(unittest.TestCase):

    @patch('pybuilder.plugins.python.python_plugin_helper.log_report')
    @patch('pybuilder.plugins.python.python_plugin_helper.read_file')
    @patch('pybuilder.plugins.python.python_plugin_helper.execute_command')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_affected_files')
    def test_should_execute_tool_on_source_files(self, affected,
                                                 execute, read, log):
        project = Mock()
        project.expand_path.return_value = '/path/to/report'
        affected.return_value = ['file1', 'file2']

        execute_tool_on_source_files(project, 'name', 'foo --bar')

        execute.assert_called_with(['foo --bar', 'file1', 'file2'], '/path/to/report')

    @patch('pybuilder.plugins.python.python_plugin_helper.log_report')
    @patch('pybuilder.plugins.python.python_plugin_helper.read_file')
    @patch('pybuilder.plugins.python.python_plugin_helper.execute_command')
    @patch('pybuilder.plugins.python.python_plugin_helper.discover_affected_files')
    def test_should_give_verbose_output(self, affected,
                                        execute, read, log):
        project = Mock()
        project.get_property.return_value = True  # flake8_verbose_output == True
        logger = Mock()
        read.return_value = ['error', 'warning']

        execute_tool_on_source_files(project, 'flake8', 'foo --bar', logger)

        log.assert_called_with(logger, 'flake8', ['error', 'warning'])

########NEW FILE########
__FILENAME__ = test_plugin_helper_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest
from mockito import mock, unstub, any, verify, when

import pybuilder
from pybuilder.plugins.python.test_plugin_helper import ReportsProcessor
from pybuilder.errors import BuildFailedException


class ReportsProcessorTests(unittest.TestCase):

    def setUp(self):
        self.reports_processor = ReportsProcessor(mock(), mock())
        self.reports_processor.process_reports([], mock())

    def tearDown(self):
        unstub()

    def test_should_raise_exception_when_not_all_tests_pass(self):

        self.reports_processor.tests_failed = 1

        self.assertRaises(
            BuildFailedException, self.reports_processor.write_report_and_ensure_all_tests_passed)

    def test_should_not_raise_exception_when_all_tests_pass(self):
        self.reports_processor.tests_failed = 0

        self.reports_processor.write_report_and_ensure_all_tests_passed()

    def test_should_write_report(self):
        when(pybuilder.plugins.python.test_plugin_helper).render_report(
            any()).thenReturn('rendered-report')

        self.reports_processor.write_report_and_ensure_all_tests_passed()

        verify(self.reports_processor.project).write_report(
            "integrationtest.json", 'rendered-report')

    def test_should_parse_reports(self):
        reports = [
            {'test': 'name1', 'test_file':
                'file1', 'success': False, 'time': 1},
            {'test': 'name2', 'test_file':
                'file2', 'success': False, 'time': 2},
            {'test': 'name3', 'test_file':
                'file3', 'success': True, 'time': 3},
            {'test': 'name4', 'test_file': 'file4', 'success': True, 'time': 4}
        ]
        self.reports_processor.process_reports(reports, mock())

        self.assertEqual(self.reports_processor.tests_failed, 2)
        self.assertEqual(self.reports_processor.tests_executed, 4)

    def test_should_create_test_report_with_attributes(self):
        mock_time = mock()
        when(mock_time).get_millis().thenReturn(42)

        self.reports_processor.process_reports([], mock_time)
        self.reports_processor.tests_failed = 4
        self.reports_processor.tests_executed = 42
        self.reports_processor.reports = ['a', 'b', 'c']

        self.assertEqual(self.reports_processor.test_report,
                         {
                             'num_of_tests': 42,
                             'success': False,
                             'tests': ['a', 'b', 'c'],
                             'tests_failed': 4,
                             'time': 42
                         }
                         )

########NEW FILE########
__FILENAME__ = unittest_plugin_tests
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

__author__ = 'Michael Gruber'

from unittest import TestCase

from mock import Mock, patch
from pybuilder.core import Project
from pybuilder.plugins.python.unittest_plugin import (execute_tests, execute_tests_matching,
                                                      _register_test_and_source_path_and_return_test_dir,
                                                      report_to_ci_server)


class PythonPathTests(TestCase):

    def setUp(self):
        self.project = Project('/path/to/project')
        self.project.set_property('dir_source_unittest_python', 'unittest')
        self.project.set_property('dir_source_main_python', 'src')

    def test_should_register_source_paths(self):
        system_path = ['some/python/path']

        _register_test_and_source_path_and_return_test_dir(self.project, system_path)

        self.assertTrue('/path/to/project/unittest' in system_path)
        self.assertTrue('/path/to/project/src' in system_path)

    def test_should_put_project_sources_before_other_sources(self):
        system_path = ['irrelevant/sources']

        _register_test_and_source_path_and_return_test_dir(self.project, system_path)

        test_sources_index_in_path = system_path.index('/path/to/project/unittest')
        main_sources_index_in_path = system_path.index('/path/to/project/src')
        irrelevant_sources_index_in_path = system_path.index('irrelevant/sources')
        self.assertTrue(test_sources_index_in_path < irrelevant_sources_index_in_path and
                        main_sources_index_in_path < irrelevant_sources_index_in_path)


class ExecuteTestsTests(TestCase):

    def setUp(self):
        self.mock_result = Mock()
        self.mock_logger = Mock()

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_suffix(self, mock_discover_modules_matching, mock_unittest, runner):

        execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_discover_modules_by_glob(self, mock_discover_modules_matching, mock_unittest, runner):

        execute_tests_matching(self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_discover_modules_matching.assert_called_with('/path/to/test/sources', '*_tests.py')

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.plugins.python.unittest_plugin.discover_modules_matching')
    def test_should_load_tests_from_discovered_modules(self, mock_discover_modules_matching, mock_unittest, runner):

        mock_modules = Mock()
        mock_discover_modules_matching.return_value = mock_modules

        execute_tests_matching(self.mock_logger, '/path/to/test/sources', '*_tests.py')

        mock_unittest.defaultTestLoader.loadTestsFromNames.assert_called_with(mock_modules)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_run_discovered_and_loaded_tests(self, mock_discover_modules, mock_unittest, runner):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests

        execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        runner.return_value.run.assert_called_with(mock_tests)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_return_actual_test_results(self, mock_discover_modules, mock_unittest, runner):

        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py')

        self.assertEqual(self.mock_result, actual)

    @patch('pybuilder.plugins.python.unittest_plugin.TestNameAwareTextTestRunner')
    @patch('pybuilder.plugins.python.unittest_plugin.unittest')
    @patch('pybuilder.utils.discover_modules')
    def test_should_set_test_method_prefix_when_given(self, mock_discover_modules, mock_unittest, runner):
        mock_tests = Mock()
        mock_unittest.defaultTestLoader.loadTestsFromNames.return_value = mock_tests
        runner.return_value.run.return_value = self.mock_result

        actual, _ = execute_tests(self.mock_logger, '/path/to/test/sources', '_tests.py', test_method_prefix='should_')

        self.assertEqual('should_', mock_unittest.defaultTestLoader.testMethodPrefix)


class CIServerInteractionTests(TestCase):

    @patch('pybuilder.ci_server_interaction.TestProxy')
    def test_should_report_passed_tests_to_ci_server(self, proxy):
        project = Project('basedir')
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ['test1', 'test2', 'test3']
        result.failed_test_names_and_reasons = {}

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_not_called()

    @patch('pybuilder.ci_server_interaction.TestProxy')
    def test_should_report_failed_tests_to_ci_server(self, proxy):
        project = Project('basedir')
        mock_proxy = Mock()
        proxy.return_value = mock_proxy
        mock_proxy.and_test_name.return_value = mock_proxy
        mock_proxy.__enter__ = Mock(return_value=mock_proxy)
        mock_proxy.__exit__ = Mock(return_value=False)
        result = Mock()
        result.test_names = ['test1', 'test2', 'test3']
        result.failed_test_names_and_reasons = {
            'test2': 'Something went very wrong'
        }

        report_to_ci_server(project, result)

        mock_proxy.fails.assert_called_with('Something went very wrong')

########NEW FILE########
__FILENAME__ = ronn_manpage_plugin_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest
from pybuilder.core import Project
from pybuilder.plugins.ronn_manpage_plugin import build_generate_manpages_command


class RonnManpagePluginTests(unittest.TestCase):

    def test_should_generate_command_abiding_to_configuration(self):
        project = Project('egg')
        project.set_property("dir_manpages", "docs/man")
        project.set_property("manpage_source", "README.md")
        project.set_property("manpage_section", 1)

        self.assertEqual(build_generate_manpages_command(project), 'ronn -r --pipe README.md | gzip -9 > docs/man/egg.1.gz')

########NEW FILE########
__FILENAME__ = reactor_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import imp
import os
import unittest

from mockito import when, verify, unstub, any, times, contains
from mockito.matchers import Matcher
from test_utils import mock  # TODO @mriehl SORCERY!!!!! BURN IT WITH FIRE!!!!

from pybuilder.core import (ACTION_ATTRIBUTE,
                            AFTER_ATTRIBUTE,
                            BEFORE_ATTRIBUTE,
                            ENVIRONMENTS_ATTRIBUTE,
                            INITIALIZER_ATTRIBUTE,
                            NAME_ATTRIBUTE,
                            ONLY_ONCE_ATTRIBUTE,
                            TASK_ATTRIBUTE,
                            Project)
from pybuilder.errors import MissingPluginException, PyBuilderException, ProjectValidationFailedException
from pybuilder.reactor import Reactor
from pybuilder.execution import Task, Action, Initializer, ExecutionManager
from pybuilder.pluginloader import PluginLoader


class TaskNameMatcher (Matcher):

    def __init__(self, task_name):
        self.task_name = task_name

    def matches(self, arg):
        if not isinstance(arg, Task):
            return False
        return arg.name == self.task_name

    def repr(self):
        return "Task with name %s" % self.task_name


class ReactorTest (unittest.TestCase):

    def setUp(self):
        self.plugin_loader_mock = mock(PluginLoader)
        self.logger = mock()
        self.execution_manager = mock(ExecutionManager)
        self.reactor = Reactor(
            self.logger, self.execution_manager, self.plugin_loader_mock)

    def tearDown(self):
        unstub()

    def test_should_return_tasks_from_execution_manager_when_calling_get_tasks(self):
        self.execution_manager.tasks = ["spam"]
        self.assertEquals(["spam"], self.reactor.get_tasks())

    def test_should_raise_exception_when_importing_plugin_and_plugin_not_found(self):
        when(self.plugin_loader_mock).load_plugin(
            any(), "not_found").thenRaise(MissingPluginException("not_found"))

        self.assertRaises(
            MissingPluginException, self.reactor.import_plugin, "not_found")

        verify(self.plugin_loader_mock).load_plugin(any(), "not_found")

    def test_should_collect_single_task(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)

        module = mock()
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_task(TaskNameMatcher("task"))

    def test_should_collect_single_task_with_overridden_name(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)
        setattr(task, NAME_ATTRIBUTE, "overridden_name")

        module = mock()
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_task(
            TaskNameMatcher("overridden_name"))

    def test_should_collect_multiple_tasks(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)

        def task2():
            pass
        setattr(task2, TASK_ATTRIBUTE, True)

        module = mock()
        module.task = task
        module.task2 = task2

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager, times(2)).register_task(any(Task))

    def test_should_collect_single_before_action(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, BEFORE_ATTRIBUTE, "spam")

        module = mock()
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_action(any(Action))

    def test_should_collect_single_after_action(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, AFTER_ATTRIBUTE, "spam")

        module = mock()
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_action(any(Action))

    def test_should_collect_single_after_action_with_only_once_flag(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, AFTER_ATTRIBUTE, "spam")
        setattr(action, ONLY_ONCE_ATTRIBUTE, True)

        module = mock()
        module.task = action

        def register_action(action):
            if not action.only_once:
                raise AssertionError("Action is not marked as only_once")

        self.execution_manager.register_action = register_action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

    def test_should_collect_single_initializer(self):
        def init():
            pass
        setattr(init, INITIALIZER_ATTRIBUTE, True)

        module = mock()
        module.task = init

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_initializer(any(Initializer))

    def test_should_collect_single_initializer_with_environments(self):
        def init():
            pass
        setattr(init, INITIALIZER_ATTRIBUTE, True)
        setattr(init, ENVIRONMENTS_ATTRIBUTE, ["any_environment"])

        module = mock()
        module.task = init

        class ExecutionManagerMock (object):

            def register_initializer(self, initializer):
                self.initializer = initializer

        execution_manager_mock = ExecutionManagerMock()
        self.reactor.execution_manager = execution_manager_mock

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(
            execution_manager_mock.initializer.environments, ["any_environment"])

    def test_should_raise_exception_when_verifying_project_directory_and_directory_does_not_exist(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")

    def test_should_raise_exception_when_verifying_project_directory_and_directory_is_not_a_directory(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")

    def test_should_raise_exception_when_verifying_project_directory_and_build_descriptor_does_not_exist(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(True)
        when(os.path).join("spam", "eggs").thenReturn("spam/eggs")
        when(os.path).exists("spam/eggs").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")
        verify(os.path).join("spam", "eggs")
        verify(os.path).exists("spam/eggs")

    def test_should_raise_exception_when_verifying_project_directory_and_build_descriptor_is_not_a_file(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(True)
        when(os.path).join("spam", "eggs").thenReturn("spam/eggs")
        when(os.path).exists("spam/eggs").thenReturn(True)
        when(os.path).isfile("spam/eggs").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")
        verify(os.path).join("spam", "eggs")
        verify(os.path).exists("spam/eggs")
        verify(os.path).isfile("spam/eggs")

    def test_should_return_directory_and_full_path_of_descriptor_when_verifying_project_directory(self):
        when(os.path).abspath("spam").thenReturn("/spam")
        when(os.path).exists("/spam").thenReturn(True)
        when(os.path).isdir("/spam").thenReturn(True)
        when(os.path).join("/spam", "eggs").thenReturn("/spam/eggs")
        when(os.path).exists("/spam/eggs").thenReturn(True)
        when(os.path).isfile("/spam/eggs").thenReturn(True)

        self.assertEquals(
            ("/spam", "/spam/eggs"), self.reactor.verify_project_directory("spam", "eggs"))

        verify(os.path).abspath("spam")
        verify(os.path).exists("/spam")
        verify(os.path).isdir("/spam")
        verify(os.path).join("/spam", "eggs")
        verify(os.path).exists("/spam/eggs")
        verify(os.path).isfile("/spam/eggs")

    def test_should_raise_exception_when_loading_project_module_and_import_raises_exception(self):
        when(imp).load_source("build", "spam").thenRaise(ImportError("spam"))

        self.assertRaises(
            PyBuilderException, self.reactor.load_project_module, "spam")

        verify(imp).load_source("build", "spam")

    def test_should_return_module_when_loading_project_module_and_import_raises_exception(self):
        module = mock()
        when(imp).load_source("build", "spam").thenReturn(module)

        self.assertEquals(module, self.reactor.load_project_module("spam"))

        verify(imp).load_source("build", "spam")

    def test_ensure_project_attributes_are_set_when_instantiating_project(self):
        module = mock(version="version",
                      default_task="default_task",
                      summary="summary",
                      home_page="home_page",
                      description="description",
                      authors="authors",
                      license="license",
                      url="url")

        self.reactor.project = mock()
        self.reactor.project_module = module

        self.reactor.apply_project_attributes()

        self.assertEquals("version", self.reactor.project.version)
        self.assertEquals("default_task", self.reactor.project.default_task)
        self.assertEquals("summary", self.reactor.project.summary)
        self.assertEquals("home_page", self.reactor.project.home_page)
        self.assertEquals("description", self.reactor.project.description)
        self.assertEquals("authors", self.reactor.project.authors)
        self.assertEquals("license", self.reactor.project.license)
        self.assertEquals("url", self.reactor.project.url)

    def test_ensure_project_name_is_set_from_attribute_when_instantiating_project(self):
        module = mock(name="name")

        self.reactor.project = mock()
        self.reactor.project_module = module
        self.reactor.apply_project_attributes()

        self.assertEquals("name", self.reactor.project.name)

    def test_should_import_plugin_only_once(self):
        plugin_module = mock()
        when(self.plugin_loader_mock).load_plugin(
            any(), "spam").thenReturn(plugin_module)

        self.reactor.require_plugin("spam")
        self.reactor.require_plugin("spam")

        self.assertEquals(["spam"], self.reactor.get_plugins())

        verify(self.plugin_loader_mock).load_plugin(any(), "spam")

    def test_ensure_project_properties_are_logged_when_calling_log_project_properties(self):
        project = Project("spam")
        project.set_property("spam", "spam")
        project.set_property("eggs", "eggs")

        self.reactor.project = project
        self.reactor.log_project_properties()

        verify(self.logger).debug(
            "Project properties: %s", contains("basedir : spam"))
        verify(self.logger).debug(
            "Project properties: %s", contains("eggs : eggs"))
        verify(self.logger).debug(
            "Project properties: %s", contains("spam : spam"))

    def test_should_raise_exception_when_project_is_not_valid(self):
        self.reactor.project = mock(properties={})
        when(self.reactor.project).validate().thenReturn(["spam"])

        self.assertRaises(ProjectValidationFailedException, self.reactor.build)

########NEW FILE########
__FILENAME__ = scaffolding_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/PLICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from mock import patch, call
from unittest import TestCase

from pybuilder.scaffolding import (PythonProjectScaffolding,
                                   collect_project_information,
                                   suggest,
                                   suggest_plugins)


class PythonProjectScaffoldingTests(TestCase):

    def test_should_set_up_scaffolding_with_defaults(self):
        scaffolding = PythonProjectScaffolding('some-project')

        self.assertEqual(scaffolding.dir_source_main_python, 'src/main/python')
        self.assertEqual(
            scaffolding.dir_source_unittest_python, 'src/unittest/python')
        self.assertEqual(
            scaffolding.dir_source_main_scripts, 'src/main/scripts')

    def test_should_build_empty_initializer_when_defaults_are_used(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    pass''')

    def test_should_build_initializer_for_custom_source_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_main_python = 'src'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")''')

    def test_should_build_initializer_for_custom_test_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_unittest_python", "test")''')

    def test_should_build_initializer_for_custom_test_and_source_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.dir_source_main_python = 'src'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")
    project.set_property("dir_source_unittest_python", "test")''')

    def test_should_render_build_descriptor_with_custom_dirs(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.dir_source_main_python = 'src'

        self.assertEqual(scaffolding.render_build_descriptor(), '''\
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")


name = "some-project"
default_task = "publish"


@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")
    project.set_property("dir_source_unittest_python", "test")
''')

    def test_should_render_build_descriptor_without_custom_dirs(self):
        scaffolding = PythonProjectScaffolding('some-project')

        self.assertEqual(scaffolding.render_build_descriptor(), '''\
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")


name = "some-project"
default_task = "publish"


@init
def set_properties(project):
    pass
''')

    def test_should_render_build_descriptor_with_additional_imports(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.add_plugins(['foo', 'bar'])

        self.assertTrue('\nuse_plugin("foo")\nuse_plugin("bar")\n' in scaffolding.render_build_descriptor())

    @patch('pybuilder.scaffolding.os')
    def test_should_set_up_project_when_directories_missing(self, mock_os):
        scaffolding = PythonProjectScaffolding('some-project')
        mock_os.path.exists.return_value = False

        scaffolding.set_up_project()

        self.assertEqual(mock_os.makedirs.call_args_list,
                         [
                             call('src/main/python'),
                             call('src/unittest/python'),
                             call('src/main/scripts')
                         ])

    @patch('pybuilder.scaffolding.os')
    def test_should_set_up_project_when_directories_present(self, mock_os):
        scaffolding = PythonProjectScaffolding('some-project')
        mock_os.path.exists.return_value = True

        scaffolding.set_up_project()

        self.assertFalse(mock_os.called)


class CollectProjectInformationTests(TestCase):

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_prompt_user_with_defaults(self, prompt, os):
        os.path.basename.return_value = 'project'
        collect_project_information()

        self.assertEqual(prompt.call_args_list,
                         [
                             call('Project name', 'project'),
                             call('Source directory', 'src/main/python'),
                             call('Unittest directory', 'src/unittest/python'),
                             call('Scripts directory', 'src/main/scripts'),
                             call('Use plugin python.flake8 (Y/n)?', 'y'),
                             call('Use plugin python.coverage (Y/n)?', 'y'),
                             call('Use plugin python.distutils (Y/n)?', 'y')
                         ])

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_project_name(self, prompt, os):
        prompt.return_value = 'project'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.project_name, 'project')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_source_dir(self, prompt, os):
        prompt.return_value = 'src'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_main_python, 'src')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_test_dir(self, prompt, os):
        prompt.return_value = 'test'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_unittest_python, 'test')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_scripts_dir(self, prompt, os):
        prompt.return_value = 'scripts'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_main_scripts, 'scripts')


class PluginSuggestionTests(TestCase):

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_filter_out_plugins_that_were_not_chosen(self, prompt):
        prompt.side_effect = ['', 'n', 'y', 'N', 'Y']
        chosen_plugins = suggest_plugins(['plugin-1', 'plugin-2', 'plugin-3', 'plugin-4', 'plugin-5'])

        self.assertEqual(chosen_plugins, ['plugin-1', 'plugin-3', 'plugin-5'])

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_choice_is_skipped(self, prompt):
        prompt.return_value = ''

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_plugin_is_chosen_lowercase(self, prompt):
        prompt.return_value = 'y'

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_plugin_is_chosen_uppercase(self, prompt):
        prompt.return_value = 'Y'

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_non_when_plugin_is_refused_lowercase(self, prompt):
        prompt.return_value = 'n'

        self.assertEqual(suggest('plugin'), None)

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_non_when_plugin_is_refused_uppercase(self, prompt):
        prompt.return_value = 'N'

        self.assertEqual(suggest('plugin'), None)

########NEW FILE########
__FILENAME__ = test_utils
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from unittest import TestCase
import mockito


def mock(mocked_obj=None, **keyword_arguments):
    result = mockito.mock(mocked_obj)
    for key in keyword_arguments:
        setattr(result, key, keyword_arguments[key])
    return result


class PyBuilderTestCase(TestCase):

    def assert_line_by_line_equal(self, expected_multi_line_string, actual_multi_line_string):
        expected_lines = expected_multi_line_string.split("\n")
        actual_lines = actual_multi_line_string.split("\n")
        for i in range(len(expected_lines)):
            expected_line = expected_lines[i]
            actual_line = actual_lines[i]
            message = """Multi line strings are not equal in line ${line_number}
  expected: "{expected_line}"
   but got: "{actual_line}"
""".format(line_number=i, expected_line=expected_line, actual_line=actual_line)

            self.assertEqual(expected_line, actual_line, message)

########NEW FILE########
__FILENAME__ = utils_tests
#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0(the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import datetime
import os
import re
import tempfile
import time
import unittest
import shutil

from json import loads
from mockito import when, verify, unstub, any

import pybuilder.utils
from pybuilder.utils import (GlobExpression,
                             Timer,
                             apply_on_files,
                             as_list,
                             discover_files,
                             discover_files_matching,
                             discover_modules,
                             discover_modules_matching,
                             format_timestamp,
                             mkdir,
                             render_report,
                             timedelta_in_millis)
from pybuilder.errors import PyBuilderException


class TimerTest(unittest.TestCase):

    def test_ensure_that_start_starts_timer(self):
        timer = Timer.start()
        self.assertTrue(timer.start_time > 0)
        self.assertFalse(timer.end_time)

    def test_should_raise_exception_when_fetching_millis_of_running_timer(self):
        timer = Timer.start()
        self.assertRaises(PyBuilderException, timer.get_millis)

    def test_should_return_number_of_millis(self):
        timer = Timer.start()
        time.sleep(1)
        timer.stop()
        self.assertTrue(timer.get_millis() > 0)


class RenderReportTest(unittest.TestCase):

    def test_should_render_report(self):
        report = {
            "eggs": ["foo", "bar"],
            "spam": "baz"
        }

        actual_report_as_json_string = render_report(report)

        actual_report = loads(actual_report_as_json_string)
        actual_keys = sorted(actual_report.keys())

        self.assertEquals(actual_keys, ['eggs', 'spam'])
        self.assertEquals(actual_report['eggs'], ["foo", "bar"])
        self.assertEquals(actual_report['spam'], "baz")


class FormatTimestampTest(unittest.TestCase):

    def assert_matches(self, regex, actual, message=None):
        if not re.match(regex, actual):
            if not message:
                message = "'%s' does not match '%s'" % (actual, regex)

            self.fail(message)

    def test_should_format_timestamp(self):
        self.assert_matches(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
                            format_timestamp(datetime.datetime.now()))


class AsListTest(unittest.TestCase):

    def test_should_return_empty_list_when_no_argument_is_given(self):
        self.assertEquals([], as_list())

    def test_should_return_empty_list_when_none_is_given(self):
        self.assertEquals([], as_list(None))

    def test_should_wrap_single_string_as_list(self):
        self.assertEquals(["spam"], as_list("spam"))

    def test_should_wrap_two_strings_as_list(self):
        self.assertEquals(["spam", "eggs"], as_list("spam", "eggs"))

    def test_should_unwrap_single_list(self):
        self.assertEquals(["spam", "eggs"], as_list(["spam", "eggs"]))

    def test_should_unwrap_multiple_lists(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar"], as_list(["spam", "eggs"], ["foo", "bar"]))

    def test_should_unwrap_single_tuple(self):
        self.assertEquals(["spam", "eggs"], as_list(("spam", "eggs")))

    def test_should_unwrap_multiple_tuples(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar"], as_list(("spam", "eggs"), ("foo", "bar")))

    def test_should_unwrap_mixed_tuples_and_lists_and_strings(self):
        self.assertEquals(["spam", "eggs", "foo", "bar", "foobar"],
                          as_list(("spam", "eggs"), ["foo", "bar"], "foobar"))

    def test_should_unwrap_mixed_tuples_and_lists_and_strings_and_ignore_none_values(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar", "foobar"], as_list(None, ("spam", "eggs"),
                                                              None, ["foo", "bar"],
                                                              None, "foobar", None))

    def test_should_return_list_of_function(self):
        def foo():
            pass
        self.assertEquals([foo], as_list(foo))


class TimedeltaInMillisTest(unittest.TestCase):

    def assertMillis(self, expected_millis, **timedelta_constructor_args):
        self.assertEquals(expected_millis, timedelta_in_millis(
            datetime.timedelta(**timedelta_constructor_args)))

    def test_should_return_number_of_millis_for_timedelta_with_microseconds_less_than_one_thousand(self):
        self.assertMillis(0, microseconds=500)

    def test_should_return_number_of_millis_for_timedelta_with_microseconds(self):
        self.assertMillis(1, microseconds=1000)

    def test_should_return_number_of_millis_for_timedelta_with_seconds(self):
        self.assertMillis(5000, seconds=5)

    def test_should_return_number_of_millis_for_timedelta_with_minutes(self):
        self.assertMillis(5 * 60 * 1000, minutes=5)

    def test_should_return_number_of_millis_for_timedelta_with_hours(self):
        self.assertMillis(5 * 60 * 60 * 1000, hours=5)

    def test_should_return_number_of_millis_for_timedelta_with_days(self):
        self.assertMillis(5 * 24 * 60 * 60 * 1000, days=5)


class DiscoverFilesTest(unittest.TestCase):
    fake_dir_contents = ["README.md", ".gitignore", "spam.py", "eggs.py", "eggs.py~"]

    def tearDown(self):
        unstub()

    def test_should_only_return_py_suffix(self):
        when(os).walk("spam").thenReturn([("spam", [], self.fake_dir_contents)])
        expected_result = ["spam/spam.py", "spam/eggs.py"]
        actual_result = set(discover_files("spam", ".py"))
        self.assertEquals(set(expected_result), actual_result)
        verify(os).walk("spam")

    def test_should_only_return_py_glob(self):
        when(os).walk("spam").thenReturn([("spam", [], self.fake_dir_contents)])
        expected_result = ["spam/README.md"]
        actual_result = set(discover_files_matching("spam", "README.?d"))
        self.assertEquals(set(expected_result), actual_result)
        verify(os).walk("spam")


class DiscoverModulesTest(unittest.TestCase):

    def tearDown(self):
        unstub()

    def test_should_return_empty_list_when_directory_contains_single_file_not_matching_suffix(self):
        when(os).walk("spam").thenReturn([("spam", [], ["eggs.pi"])])
        self.assertEquals([], discover_modules("spam", ".py"))
        verify(os).walk("spam")

    def test_should_return_list_with_single_module_when_directory_contains_single_file(self):
        when(os).walk("spam").thenReturn([("spam", [], ["eggs.py"])])
        self.assertEquals(["eggs"], discover_modules("spam", ".py"))
        verify(os).walk("spam")

    def test_should_only_match_py_files_regardless_of_glob(self):
        when(os).walk("pet_shop").thenReturn([("pet_shop", [],
                                               ["parrot.txt", "parrot.py", "parrot.pyc", "parrot.py~", "slug.py"])])
        expected_result = ["parrot"]
        actual_result = discover_modules_matching("pet_shop", "*parrot*")
        self.assertEquals(set(expected_result), set(actual_result))
        verify(os).walk("pet_shop")

    def test_glob_should_return_list_with_single_module_when_directory_contains_single_file(self):
        when(os).walk("spam").thenReturn([("spam", [], ["eggs.py"])])
        self.assertEquals(["eggs"], discover_modules_matching("spam", "*"))
        verify(os).walk("spam")

    def test_glob_should_return_list_with_single_module_when_directory_contains_package(self):
        when(os).walk("spam").thenReturn([("spam", ["eggs"], []),
                                         ("spam/eggs", [], ["__init__.py"])])

        self.assertEquals(["eggs"], discover_modules_matching("spam", "*"))

        verify(os).walk("spam")

    def test_should_not_eat_first_character_of_modules_when_source_path_ends_with_slash(self):
        when(pybuilder.utils).discover_files_matching(any(), any()).thenReturn(['/path/to/tests/reactor_tests.py'])

        self.assertEquals(["reactor_tests"], discover_modules_matching("/path/to/tests/", "*"))

    def test_should_honor_suffix_without_stripping_it_from_module_names(self):
        when(pybuilder.utils).discover_files_matching(any(), any()).thenReturn(['/path/to/tests/reactor_tests.py'])

        self.assertEquals(["reactor_tests"], discover_modules_matching("/path/to/tests/", "*_tests"))


class GlobExpressionTest(unittest.TestCase):

    def test_static_expression_should_match_exact_file_name(self):
        self.assertTrue(GlobExpression("spam.eggs").matches("spam.eggs"))

    def test_static_expression_should_not_match_different_file_name(self):
        self.assertFalse(GlobExpression("spam.eggs").matches("spam.egg"))

    def test_dynamic_file_expression_should_match_any_character(self):
        self.assertTrue(GlobExpression("spam.egg*").matches("spam.eggs"))

    def test_dynamic_file_expression_should_match_no_character(self):
        self.assertTrue(GlobExpression("spam.egg*").matches("spam.egg"))

    def test_dynamic_file_expression_should_not_match_different_file_part(self):
        self.assertFalse(GlobExpression("spam.egg*").matches("foo.spam.egg"))

    def test_dynamic_file_expression_should_not_match_directory_part(self):
        self.assertFalse(GlobExpression("*spam.egg").matches("foo/spam.egg"))

    def test_dynamic_directory_expression_should_match_file_in_directory(self):
        self.assertTrue(GlobExpression("**/spam.egg").matches("foo/spam.egg"))
        self.assertTrue(GlobExpression("**/spam.egg").matches("bar/spam.egg"))


class ApplyOnFilesTest(unittest.TestCase):

    def setUp(self):
        self.old_os_path_join = os.path.join

        def join(*elements):
            return "/".join(elements)
        os.path.join = join

    def tearDown(self):
        os.path.join = self.old_os_path_join
        unstub()

    def test_should_apply_callback_to_all_files_when_expression_matches_all_files(self):
        when(os).walk("spam").thenReturn([("spam", [], ["a", "b", "c"])])

        absolute_file_names = []
        relative_file_names = []

        def callback(absolute_file_name, relative_file_name):
            absolute_file_names.append(absolute_file_name)
            relative_file_names.append(relative_file_name)

        apply_on_files("spam", callback, "*")
        self.assertEquals(["spam/a", "spam/b", "spam/c"], absolute_file_names)
        self.assertEquals(["a", "b", "c"], relative_file_names)

        verify(os).walk("spam")

    def test_should_apply_callback_to_one_file_when_expression_matches_one_file(self):
        when(os).walk("spam").thenReturn([("spam", [], ["a", "b", "c"])])

        called_on_file = []

        def callback(absolute_file_name, relative_file_name):
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a")
        self.assertEquals(["spam/a"], called_on_file)

        verify(os).walk("spam")

    def test_should_pass_additional_arguments_to_closure(self):
        when(os).walk("spam").thenReturn([("spam", [], ["a"])])

        called_on_file = []

        def callback(absolute_file_name, relative_file_name, additional_argument):
            self.assertEquals("additional argument", additional_argument)
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a", "additional argument")
        self.assertEquals(["spam/a"], called_on_file)

        verify(os).walk("spam")


class MkdirTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(self.__class__.__name__)
        self.any_directory = os.path.join(self.basedir, "any_dir")

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_should_make_directory_if_it_does_not_exist(self):
        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_should_make_directory_with_parents_if_it_does_not_exist(self):
        self.any_directory = os.path.join(self.any_directory, "any_child")

        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_should_not_make_directory_if_it_already_exists(self):
        os.mkdir(self.any_directory)

        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_raise_exception_when_file_with_dirname_already_exists(self):
        with open(self.any_directory, "w") as existing_file:
            existing_file.write("caboom")

        self.assertRaises(PyBuilderException, mkdir, self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertFalse(os.path.isdir(self.any_directory))

########NEW FILE########
