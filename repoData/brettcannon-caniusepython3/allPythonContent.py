__FILENAME__ = command
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

import setuptools

import caniusepython3 as ciu
import caniusepython3.__main__ as ciu_main
from caniusepython3 import pypi


class Command(setuptools.Command):

    description = """Run caniusepython3 over a setup.py file."""

    user_options = []

    def _dependencies(self):
        projects = []
        for attr in ('install_requires', 'tests_require'):
            requirements = getattr(self.distribution, attr, None) or []
            for project in requirements:
                if not project:
                    continue
                projects.append(pypi.just_name(project))
        extras = getattr(self.distribution, 'extras_require', None) or {}
        for value in extras.values():
            projects.extend(map(pypi.just_name, value))
        return projects

    def initialize_options(self):
        pass

    def run(self):
        ciu_main.check(self._dependencies())

    def finalize_options(self):
        pass

########NEW FILE########
__FILENAME__ = dependencies
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

import distlib.locators

import caniusepython3 as ciu
from caniusepython3 import pypi

import concurrent.futures
import logging


class LowerDict(dict):

    def __getitem__(self, key):
        return super(LowerDict, self).__getitem__(key.lower())


def reasons_to_paths(reasons):
    """Calculate the dependency paths to the reasons of the blockers.

    Paths will be in reverse-dependency order (i.e. parent projects are in
    ascending order).

    """
    blockers = set(reasons.keys()) - set(reasons.values())
    paths = set()
    for blocker in blockers:
        path = [blocker]
        parent = reasons[blocker]
        while parent:
            path.append(parent)
            parent = reasons.get(parent)
        paths.add(tuple(path))
    return paths


def dependencies(project_name):
    """Get the dependencies for a project."""
    log = logging.getLogger('ciu')
    deps = []
    log.info('Locating {0}'.format(project_name))
    located = distlib.locators.locate(project_name, prereleases=True)
    if located is None:
        log.warning('{0} not found'.format(project_name))
        return None
    for dep in located.run_requires:
        # Drop any version details from the dependency name.
        deps.append(pypi.just_name(dep))
    return deps


def blocking_dependencies(projects, py3_projects):
    """Starting from 'projects', find all projects which are blocking Python 3 usage.

    Any project in 'py3_projects' is considered ported and thus will not have
    its dependencies searched. Version requirements are also ignored as it is
    assumed that if a project is updating to support Python 3 then they will be
    willing to update to the latest version of their dependencies. The only
    dependencies checked are those required to run the project.

    """
    log = logging.getLogger('ciu')
    check = []
    for project in projects:
        dist = distlib.locators.locate(project)
        if dist is None:
            log.warning('{0} not found'.format(project))
            continue
        project = dist.name.lower()  # PyPI can be forgiving about name formats.
        if project not in py3_projects:
            check.append(project)
    reasons = LowerDict((project, None) for project in check)
    thread_pool_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=ciu.CPU_COUNT)
    with thread_pool_executor as executor:
        while len(check) > 0:
            new_check = []
            for parent, deps in zip(check, executor.map(dependencies, check)):
                if deps is None:
                    # Can't find any results for a project, so ignore it so as
                    # to not accidentally consider indefinitely that a project
                    # can't port.
                    del reasons[parent]
                    continue
                for dep in deps:
                    if dep in py3_projects:
                        continue
                    reasons[dep] = parent
                    new_check.append(dep)
            check = new_check
    return reasons_to_paths(reasons)

########NEW FILE########
__FILENAME__ = pypi
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

import concurrent.futures
import contextlib
import json
import logging
import multiprocessing
import pkgutil
import re
try:
    import urllib.request as urllib_request
except ImportError:  #pragma: no cover
    import urllib2 as urllib_request
import xml.parsers.expat
try:
    import xmlrpc.client as xmlrpc_client
except ImportError:  #pragma: no cover
    import xmlrpclib as xmlrpc_client


try:
    CPU_COUNT = max(2, multiprocessing.cpu_count())
except NotImplementedError:  #pragma: no cover
    CPU_COUNT = 2

PROJECT_NAME = re.compile(r'[\w.-]+')


def just_name(supposed_name):
    """Strip off any versioning or restrictions metadata from a project name."""
    return PROJECT_NAME.match(supposed_name).group(0).lower()

@contextlib.contextmanager
def pypi_client():
    client = xmlrpc_client.ServerProxy('http://pypi.python.org/pypi')
    try:
        yield client
    finally:
        try:
            client('close')()
        except xml.parsers.expat.ExpatError:  #pragma: no cover
            # The close hack is not in Python 2.6.
            pass


def overrides():
    """Load a set containing projects who are missing the proper Python 3 classifier.

    Project names are always lowercased.

    """
    raw_bytes = pkgutil.get_data(__name__, 'overrides.json')
    return json.loads(raw_bytes.decode('utf-8'))


def py3_classifiers():
    """Fetch the Python 3-related trove classifiers."""
    url = 'https://pypi.python.org/pypi?%3Aaction=list_classifiers'
    response = urllib_request.urlopen(url)
    try:
        try:
            status = response.status
        except AttributeError:  #pragma: no cover
            status = response.code
        if status != 200:  #pragma: no cover
            msg = 'PyPI responded with status {0} for {1}'.format(status, url)
            raise ValueError(msg)
        data = response.read()
    finally:
        response.close()
    classifiers = data.decode('utf-8').splitlines()
    base_classifier = 'Programming Language :: Python :: 3'
    return (classifier for classifier in classifiers
            if classifier.startswith(base_classifier))


def projects_matching_classifier(classifier):
    """Find all projects matching the specified trove classifier."""
    log = logging.getLogger('ciu')
    with pypi_client() as client:
        log.info('Fetching project list for {0!r}'.format(classifier))
        try:
            return frozenset(result[0].lower()
                             for result in client.browse([classifier]))
        except xml.parsers.expat.ExpatError:  #pragma: no cover
            # Python 2.6 doesn't like empty results.
            logging.getLogger('ciu').info("PyPI didn't return any results")
            return []


def all_py3_projects(manual_overrides=None):
    """Return the set of names of all projects ported to Python 3, lowercased."""
    log = logging.getLogger('ciu')
    projects = set()
    thread_pool_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=CPU_COUNT)
    with thread_pool_executor as executor:
        for result in map(projects_matching_classifier, py3_classifiers()):
            projects.update(result)
    if manual_overrides is None:
        manual_overrides = overrides()
    stale_overrides = projects.intersection(manual_overrides)
    log.info('Adding {0} overrides:'.format(len(manual_overrides)))
    for override in sorted(manual_overrides):
        msg = override
        try:
            msg += ' ({0})'.format(manual_overrides[override])
        except TypeError:
            # No reason a set can't be used.
            pass
        log.info('    ' + msg)
    if stale_overrides:  #pragma: no cover
        log.warning('Stale overrides: {0}'.format(stale_overrides))
    projects.update(manual_overrides)
    return projects


def all_projects():
    """Get the set of all projects on PyPI."""
    log = logging.getLogger('ciu')
    with pypi_client() as client:
        log.info('Fetching all project names from PyPI')
        return frozenset(name.lower() for name in client.list_packages())

########NEW FILE########
__FILENAME__ = test_check
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

import caniusepython3 as ciu

import tempfile
import unittest

EXAMPLE_METADATA = """Metadata-Version: 1.2
Name: TestingMetadata
Version: 0.5
Summary: testing
Home-page: http://github.com/brettcannon/caniusepython3
Author: Brett Cannon
Author-email: brett@python.org
License: Apache
Requires-Dist: paste
"""


class CheckTest(unittest.TestCase):

    # When testing input, make sure to use project names that **will** lead to
    # a False answer since unknown projects are skipped.

    def test_success(self):
        self.assertTrue(ciu.check(projects=['scipy', 'numpy', 'ipython']))

    def test_failure(self):
        self.assertFalse(ciu.check(projects=['paste']))

    def test_requirements(self):
        with tempfile.NamedTemporaryFile('w') as file:
            file.write('paste\n')
            file.flush()
            self.assertFalse(ciu.check(requirements_paths=[file.name]))

    def test_metadata(self):
        self.assertFalse(ciu.check(metadata=[EXAMPLE_METADATA]))

    def test_projects(self):
        # Implicitly done by test_success and test_failure.
        pass

    def test_case_insensitivity(self):
        self.assertFalse(ciu.check(projects=['PaStE']))

    def test_ignore_missing_projects(self):
        self.assertTrue(ciu.check(projects=['sdfsjdfsdlfk;jasdflkjasdfdsfsdf']))

########NEW FILE########
__FILENAME__ = test_cli
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

import caniusepython3.__main__ as ciu_main

import io
import logging
import tempfile
import unittest
try:
    from unittest import mock
except ImportError:
    import mock


EXAMPLE_REQUIREMENTS = """
# From
#  http://www.pip-installer.org/en/latest/reference/pip_install.html#requirement-specifiers
# but without the quotes for shell protection.
FooProject >= 1.2
Fizzy [foo, bar]
PickyThing<1.6,>1.9,!=1.9.6,<2.0a0,==2.4c1
Hello
-e git+https://github.com/brettcannon/caniusepython3#egg=caniusepython3
file:../caniusepython3#egg=caniusepython3
# Docs say to specify an #egg argument, but apparently it's optional.
file:../../lib/project
"""

EXAMPLE_EXTRA_REQUIREMENTS = """
testingstuff
"""

EXAMPLE_METADATA = """Metadata-Version: 1.2
Name: CLVault
Version: 0.5
Summary: Command-Line utility to store and retrieve passwords
Home-page: http://bitbucket.org/tarek/clvault
Author: Tarek Ziade
Author-email: tarek@ziade.org
License: PSF
Keywords: keyring,password,crypt
Requires-Dist: foo; sys.platform == 'okook'
Requires-Dist: bar
Platform: UNKNOWN
"""

EXAMPLE_EXTRA_METADATA = """Metadata-Version: 1.2
Name: ExtraTest
Version: 0.5
Summary: Just for testing
Home-page: nowhere
Author: nobody
License: Apache
Requires-Dist: baz
"""

class CLITests(unittest.TestCase):

    expected_requirements = frozenset(['FooProject', 'Fizzy', 'PickyThing',
                                       'Hello'])
    expected_extra_requirements = frozenset(['testingstuff'])
    expected_metadata = frozenset(['foo', 'bar'])
    expected_extra_metadata = frozenset(['baz'])

    def setUp(self):
        log = logging.getLogger('ciu')
        self._prev_log_level = log.getEffectiveLevel()
        logging.getLogger('ciu').setLevel(1000)

    def tearDown(self):
        logging.getLogger('ciu').setLevel(self._prev_log_level)

    def test_requirements(self):
        with tempfile.NamedTemporaryFile('w') as file:
            file.write(EXAMPLE_REQUIREMENTS)
            file.flush()
            got = ciu_main.projects_from_requirements([file.name])
        self.assertEqual(set(got), self.expected_requirements)

    def test_multiple_requirements_files(self):
        with tempfile.NamedTemporaryFile('w') as f1:
            f1.write(EXAMPLE_REQUIREMENTS)
            f1.flush()
            with tempfile.NamedTemporaryFile('w') as f2:
                f2.write(EXAMPLE_EXTRA_REQUIREMENTS)
                f2.flush()
                got = ciu_main.projects_from_requirements([f1.name, f2.name])
        want = self.expected_requirements.union(self.expected_extra_requirements)
        self.assertEqual(set(got), want)

    def test_metadata(self):
        got = ciu_main.projects_from_metadata([EXAMPLE_METADATA])
        self.assertEqual(set(got), self.expected_metadata)

    def test_multiple_metadata(self):
        got = ciu_main.projects_from_metadata([EXAMPLE_METADATA,
                                               EXAMPLE_EXTRA_METADATA])
        want = self.expected_metadata.union(self.expected_extra_metadata)
        self.assertEqual(set(got), want)

    def test_cli_for_requirements(self):
        with tempfile.NamedTemporaryFile('w') as file:
            file.write(EXAMPLE_REQUIREMENTS)
            file.flush()
            args = ['--requirements', file.name]
            got = ciu_main.projects_from_cli(args)
        self.assertEqual(set(got), self.expected_requirements)

    def test_cli_for_metadata(self):
        with tempfile.NamedTemporaryFile('w') as file:
            file.write(EXAMPLE_METADATA)
            file.flush()
            args = ['--metadata', file.name]
            got = ciu_main.projects_from_cli(args)
        self.assertEqual(set(got), self.expected_metadata)

    def test_cli_for_projects(self):
        args = ['--projects', 'foo', 'bar']
        got = ciu_main.projects_from_cli(args)
        self.assertEqual(set(got), frozenset(['foo', 'bar']))

    def test_message_plural(self):
        blockers = [['A'], ['B']]
        messages = ciu_main.message(blockers)
        self.assertEqual(2, len(messages))
        want = 'You need 2 projects to transition to Python 3.'
        self.assertEqual(messages[0], want)
        want = ('Of those 2 projects, 2 have no direct dependencies blocking '
                'their transition:')
        self.assertEqual(messages[1], want)

    def test_message_singular(self):
        blockers = [['A']]
        messages = ciu_main.message(blockers)
        self.assertEqual(2, len(messages))
        want = 'You need 1 project to transition to Python 3.'
        self.assertEqual(messages[0], want)
        want = ('Of that 1 project, 1 has no direct dependencies blocking '
                'its transition:')
        self.assertEqual(messages[1], want)

    def test_message_no_blockers(self):
        messages = ciu_main.message([])
        self.assertEqual(
            ['You have 0 projects blocking you from using Python 3!'],
            messages)

    def test_pprint_blockers(self):
        simple = [['A']]
        fancy = [['A', 'B']]
        nutty = [['A', 'B', 'C']]
        repeated = [['A', 'C'], ['B']]  # Also tests sorting.
        got = ciu_main.pprint_blockers(simple)
        self.assertEqual(list(got), ['A'])
        got = ciu_main.pprint_blockers(fancy)
        self.assertEqual(list(got), ['A (which is blocking B)'])
        got = ciu_main.pprint_blockers(nutty)
        self.assertEqual(list(got),
                         ['A (which is blocking B, which is blocking C)'])
        got = ciu_main.pprint_blockers(repeated)
        self.assertEqual(list(got), ['B', 'A (which is blocking C)'])

    @mock.patch('argparse.ArgumentParser.error')
    def test_projects_must_be_specified(self, parser_error):
        ciu_main.projects_from_cli([])
        self.assertEqual(
            mock.call("Missing 'requirements', 'metadata', or 'projects'"),
            parser_error.call_args)

    def test_verbose_output(self):
        ciu_main.projects_from_cli(['-v', '-p', 'ipython'])
        self.assertTrue(logging.getLogger('ciu').isEnabledFor(logging.INFO))


#@unittest.skip('faster testing')
class NetworkTests(unittest.TestCase):

    @mock.patch('sys.stdout', io.StringIO())
    def test_e2e(self):
        # Make sure at least one project that will never be in Python 3 is
        # included.
        args = '--projects', 'numpy', 'scipy', 'matplotlib', 'ipython', 'paste'
        ciu_main.main(args)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_command
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

from caniusepython3 import command

from distutils import dist
import unittest

def make_command(requires):
    return command.Command(dist.Distribution(requires))

class RequiresTests(unittest.TestCase):

    def verify_cmd(self, requirements):
        requires = {requirements: ['pip']}
        cmd = make_command(requires)
        got = cmd._dependencies()
        self.assertEqual(frozenset(got), frozenset(['pip']))
        return cmd

    def test_install_requires(self):
        self.verify_cmd('install_requires')

    def test_tests_require(self):
        self.verify_cmd('tests_require')

    def test_extras_require(self):
        cmd = make_command({'extras_require': {'testing': ['pip']}})
        got = frozenset(cmd._dependencies())
        self.assertEqual(got, frozenset(['pip']))


class OptionsTests(unittest.TestCase):

    def test_finalize_options(self):
        # Don't expect anything to happen.
        make_command({}).finalize_options()


class NetworkTests(unittest.TestCase):

    def test_run(self):
        make_command({'install_requires': ['pip']}).run()

########NEW FILE########
__FILENAME__ = test_dependencies
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

from caniusepython3 import dependencies

import io
import unittest


class GraphResolutionTests(unittest.TestCase):

    def test_all_projects_okay(self):
        # A, B, and C are fine on their own.
        self.assertEqual(set(), dependencies.reasons_to_paths({}))

    def test_leaf_okay(self):
        # A -> B where B is okay.
        reasons = {'A': None}
        self.assertEqual(frozenset([('A',)]),
                         dependencies.reasons_to_paths(reasons))

    def test_leaf_bad(self):
        # A -> B -> C where all projects are bad.
        reasons = {'A': None, 'B': 'A', 'C': 'B'}
        self.assertEqual(frozenset([('C', 'B', 'A')]),
                         dependencies.reasons_to_paths(reasons))


class NetworkTests(unittest.TestCase):

    def test_blocking_dependencies(self):
        got = dependencies.blocking_dependencies(['pastescript'], {'paste': ''})
        want = frozenset([('pastedeploy', 'pastescript')])
        self.assertEqual(frozenset(got), want)

    def test_dependencies(self):
        got = dependencies.dependencies('pastescript')
        self.assertEqual(set(got), frozenset(['pastedeploy', 'paste']))

    def test_dependencies_no_project(self):
        got = dependencies.dependencies('sdflksjdfsadfsadfad')
        if hasattr(self, 'assertIsNone'):
            self.assertIsNone(got)
        else:
            self.assertTrue(got is None)

    def test_blocking_dependencies_no_project(self):
        got = dependencies.blocking_dependencies(['asdfsadfdsfsdffdfadf'], {})
        self.assertEqual(got, frozenset())

    def test_top_level_project_normalization(self):
        py3 = {'wsgi_intercept': ''}
        abnormal_name = 'WSGI-intercept'  # Note dash instead of underscore.
        got = dependencies.blocking_dependencies([abnormal_name], py3)
        self.assertEqual(got, frozenset())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pypi
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals

from caniusepython3 import pypi

import unittest


class NameTests(unittest.TestCase):

    def test_simple(self):
        want = 'simple-name_with.everything-separator_known'
        got = pypi.just_name(want)
        self.assertEqual(got, want)

    def test_requirements(self):
        want = 'project.name'
        got = pypi.just_name(want + '>=2.0.1')
        self.assertEqual(got, want)

    def test_bad_requirements(self):
        # From the OpenStack requirements file:
        # https://raw2.github.com/openstack/requirements/master/global-requirements.txt
        want = 'warlock'
        got = pypi.just_name(want + '>1.01<2')
        self.assertEqual(got, want)

    def test_metadata(self):
        want = 'foo'
        got = pypi.just_name("foo; sys.platform == 'okook'")
        self.assertEqual(got, want)


class OverridesTests(unittest.TestCase):

    def test_all_lowercase(self):
        for name in pypi.overrides():
            self.assertEqual(name, name.lower())


class NetworkTests(unittest.TestCase):

    def py3_classifiers(self):
        key_classifier = 'Programming Language :: Python :: 3'
        classifiers = frozenset(pypi.py3_classifiers())
        if hasattr(self, 'assertIn'):
            self.asssertIn(key_classifier, classifiers)
        else:
            self.assertTrue(key_classifier in classifiers)
        if hasattr(self, 'assertGreaterEqual'):
            self.assertGreaterEqual(len(classifiers), 5)
        else:
            self.assertTrue(len(classifiers) >= 5)
        for classifier in classifiers:
            self.assertTrue(classifier.startswith(key_classifier))


    def test_all_py3_projects(self):
        projects = pypi.all_py3_projects()
        if hasattr(self, 'assertGreater'):
            self.assertGreater(len(projects), 3000)
        else:
            self.assertTrue(len(projects) > 3000)
        self.assertTrue(all(project == project.lower() for project in projects))
        self.assertTrue(frozenset(pypi.overrides().keys()).issubset(projects))

    def test_all_py3_projects_explicit_overrides(self):
        added_port = 'asdfasdfasdfadsffffdasfdfdfdf'
        projects = pypi.all_py3_projects(set([added_port]))
        if hasattr(self, 'assertIn'):
            self.assertIn(added_port, projects)
        else:
            self.assertTrue(added_port in projects)

    def test_all_projects(self):
        projects = pypi.all_projects()
        self.assertTrue(all(project == project.lower() for project in projects))
        if hasattr(self, 'assertGreaterEqual'):
            self.assertGreaterEqual(len(projects), 40000)
        else:
            self.assertTrue(len(projects) >= 40000)

########NEW FILE########
__FILENAME__ = __main__
# Copyright 2014 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from __future__ import unicode_literals

import caniusepython3 as ciu
from caniusepython3 import pypi
from caniusepython3 import dependencies

import distlib.metadata
import pip.req

import argparse
import io
import logging
import sys


def projects_from_requirements(requirements):
    """Extract the project dependencies from a Requirements specification."""
    log = logging.getLogger('ciu')
    valid_reqs = []
    for requirements_path in requirements:
        reqs = pip.req.parse_requirements(requirements_path)
        for req in reqs:
            if not req.name:
                log.warning('A requirement lacks a name '
                            '(e.g. no `#egg` on a `file:` path)')
            elif req.editable:
                log.warning(
                    'Skipping {0}: editable projects unsupported'.format(req.name))
            elif req.url and req.url.startswith('file:'):
                log.warning(
                    'Skipping {0}: file-specified projects unsupported'.format(req.name))
            else:
                valid_reqs.append(req.name)
    return valid_reqs


def projects_from_metadata(metadata):
    """Extract the project dependencies from a metadata spec."""
    projects = []
    for data in metadata:
        meta = distlib.metadata.Metadata(fileobj=io.StringIO(data))
        projects.extend(pypi.just_name(project) for project in meta.run_requires)
    return projects


def projects_from_cli(args):
    """Take arguments through the CLI can create a list of specified projects."""
    description = ('Determine if a set of project dependencies will work with '
                   'Python 3')
    parser = argparse.ArgumentParser(description=description)
    req_help = 'path(s) to a pip requirements file (e.g. requirements.txt)'
    parser.add_argument('--requirements', '-r', nargs='+', default=(),
                        help=req_help)
    meta_help = 'path(s) to a PEP 426 metadata file (e.g. PKG-INFO, pydist.json)'
    parser.add_argument('--metadata', '-m', nargs='+', default=(),
                        help=meta_help)
    parser.add_argument('--projects', '-p', nargs='+', default=(),
                        help='name(s) of projects to test for Python 3 support')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='verbose output (e.g. list compatibility overrides)')
    parsed = parser.parse_args(args)

    if not (parsed.requirements or parsed.metadata or parsed.projects):
        parser.error("Missing 'requirements', 'metadata', or 'projects'")

    projects = []
    if parsed.verbose:
        logging.getLogger('ciu').setLevel(logging.INFO)
    projects.extend(projects_from_requirements(parsed.requirements))
    metadata = []
    for metadata_path in parsed.metadata:
        with io.open(metadata_path) as file:
            metadata.append(file.read())
    projects.extend(projects_from_metadata(metadata))
    projects.extend(parsed.projects)

    return projects


def message(blockers):
    """Create a sequence of key messages based on what is blocking."""
    if not blockers:
        return ['You have 0 projects blocking you from using Python 3!']
    flattened_blockers = set()
    for blocker_reasons in blockers:
        for blocker in blocker_reasons:
            flattened_blockers.add(blocker)
    need = 'You need {0} project{1} to transition to Python 3.'
    formatted_need = need.format(len(flattened_blockers),
                      's' if len(flattened_blockers) != 1 else '')
    can_port = ('Of {0} {1} project{2}, {3} {4} no direct dependencies '
                'blocking {5} transition:')
    formatted_can_port = can_port.format(
            'those' if len(flattened_blockers) != 1 else 'that',
            len(flattened_blockers),
            's' if len(flattened_blockers) != 1 else '',
            len(blockers),
            'have' if len(blockers) != 1 else 'has',
            'their' if len(blockers) != 1 else 'its')
    return formatted_need, formatted_can_port


def pprint_blockers(blockers):
    """Pretty print blockers into a sequence of strings.

    Results will be sorted by top-level project name. This means that if a
    project is blocking another project then the dependent project will be
    what is used in the sorting, not the project at the bottom of the
    dependency graph.

    """
    pprinted = []
    for blocker in sorted(blockers, key=lambda x: tuple(reversed(x))):
        buf = [blocker[0]]
        if len(blocker) > 1:
            buf.append(' (which is blocking ')
            buf.append(', which is blocking '.join(blocker[1:]))
            buf.append(')')
        pprinted.append(''.join(buf))
    return pprinted


def check(projects):
    """Check the specified projects for Python 3 compatibility."""
    log = logging.getLogger('ciu')
    log.info('{0} top-level projects to check'.format(len(projects)))
    print('Finding and checking dependencies ...')
    blockers = dependencies.blocking_dependencies(projects, pypi.all_py3_projects())

    print('')
    for line in message(blockers):
        print(line)

    print('')
    for line in pprint_blockers(blockers):
        print(' ', line)


def main(args=sys.argv[1:]):
    # Without this, the 'ciu' logger will emit nothing.
    logging.basicConfig(format='[%(levelname)s] %(message)s')
    check(projects_from_cli(args))


if __name__ == '__main__':  #pragma: no cover
    main()

########NEW FILE########
