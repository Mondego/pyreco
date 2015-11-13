__FILENAME__ = database
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from . import util, exceptions
from distlib.database import DistributionPath

import os


class Database(object):

    @classmethod
    def check_installed(cls, requirement):
        path = DistributionPath(include_egg=True)
        package_name = util.parse_requirement(requirement).name
        return path.get_distribution(package_name) is not None

    @classmethod
    def uninstall(self, requirement):
        # Currently we assume the distribution path contains only the last
        # version installed
        package_name = util.parse_requirement(requirement).name
        distribution = DistributionPath(include_egg=True).get_distribution(
            package_name)

        # Oh distlib, if the distribution doesn't exist, we'll get None here
        if not distribution:
            raise exceptions.PackageNotInstalled(
                "There's no package named {0} installed in your environment".format(
                    package_name))

        # Distlib is not that smart about paths for files inside of
        # distributions too, so to find the full path to the distribution
        # files, we'll have to concatenate them to this base path manually :/
        base = os.path.dirname(distribution.path)

        # Let's now remove all the installed files
        for path, hash_, size in distribution.list_installed_files():
            os.unlink(os.path.join(base, path))

        # Removing the package directories
        os.rmdir(distribution.path)

########NEW FILE########
__FILENAME__ = exceptions
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals


class CurdlingError(Exception):
    """Base exception for errors happening inside of curdling"""

    def __init__(self, message):
        super(CurdlingError, self).__init__(message)
        self.message = message


class ReportableError(CurdlingError):
    """Inform errors that happens inside of services

    This exception is raised by services that need to communicate that their
    run method failed. The only place I see this exception being caught is in
    the `services.Service._worker()` method. Although all the services might
    need to raise it.

    This exception should not be raised in any other scenarios.
    """


class UnknownURL(ReportableError):
    """Raised when the user feeds in the installer with an unknown URL"""


class TooManyRedirects(ReportableError):
    """Raised when a download exceeds the maximum number of redirects"""


class RequirementNotFound(ReportableError):
    """Raised when a requirement is not found by the finder"""


class UnpackingError(ReportableError):
    """Raised when a package can't be unpacked"""

class BuildError(ReportableError):
    """Raised when a package can't be built using the setup.py script"""


class BrokenDependency(ReportableError):
    """Raised to inform that a dependency couldn't be installed"""


class VersionConflict(ReportableError):
    """Raised when Maestro.best_version() can't find versions for all the requests"""


class NoSetupScriptFound(ReportableError):
    pass


class PackageNotInstalled(CurdlingError):
    pass

########NEW FILE########
__FILENAME__ = freeze
# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ast
import imp
import os
import sys
from distlib.database import DistributionPath
from .util import logger


class ImportVisitor(ast.NodeVisitor):

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        self.imports.append(node.names[0].name)

    def visit_ImportFrom(self, node):
        if node.level == 0:
            self.imports.append(node.module)


def find_imported_modules(code):
    visitor = ImportVisitor()
    visitor.visit(ast.parse(code))
    return visitor.imports


def get_module_path(module_name):
    module_path = imp.find_module(module_name)[1]
    possible_paths = ['']       # Avoid failure in max() if there's no
                                # prefix at all
    possible_paths.extend(path
        for path in sys.path
        if path in module_path)
    return os.path.splitext(module_path.replace(
        '{0}/'.format(max(possible_paths)), ''))[0]


def get_distribution_from_source_file(file_name):
    path = DistributionPath(include_egg=True)
    distribution = path.get_distribution(
        os.path.dirname(file_name) or file_name)
    return distribution


def get_requirements(code):
    requirements = []

    for module_name in find_imported_modules(code):
        print('module found: {0}'.format(module_name))
        path = get_module_path(module_name)

        # If we do have a module that matches tha name we still need
        # to know if it was installed as a package. If it was not, we
        # consider that the user is not interested in adding this
        # package to the requirements list, so we just skip it.
        distribution = get_distribution_from_source_file(path)
        if not distribution:
            continue

        # Let's build the output in a format that everybody
        # understands
        requirements.append('{0}=={1}'.format(
            distribution.name,
            distribution.version))

    return requirements


def find_python_files(path):
    source_files = []
    for root, directories, files in os.walk(path):
        for file_name in files:
            if file_name.endswith('.py'):
                found = os.path.join(root, file_name).replace(
                    '{0}/'.format(path), '')
                source_files.append(found)
    return source_files


class Freeze(object):

    def __init__(self, root_path):
        self.root_path = root_path
        self.logger = logger(__name__)

    def run(self):
        requirements = set()
        for file_path in find_python_files(self.root_path):
            self.logger.info('harvesting file %s', file_path)
            code = open(file_path).read()
            requirements |= set(find_imported_modules(code))

        for requirement in sorted(set(requirements).difference(sys.builtin_module_names)):
            print(requirement)

            # all_requirements.extend(file_requirements)
        # print('\n'.join(list(set(all_requirements))))

########NEW FILE########
__FILENAME__ = index
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from collections import defaultdict
from threading import RLock
from pkg_resources import parse_version
from .util import split_name, filehash, safe_name, parse_requirement

import os
import re
import shutil

FORMATS = ('whl', 'gz', 'bz', 'zip')

PKG_NAMES = [
    r'([\w\-\_\.]+)-([\d\.]+\d)[\.\-]',
    r'(\w+)-(.+)\.\w+$',
]


def pkg_name(name):
    for expr in PKG_NAMES:
        result = re.findall(expr, name)
        if result:
            return result[0]


def match_format(format_, name):
    ext = split_name(name)[1]
    if format_.startswith('~'):
        return format_[1:] != ext
    return format_ == ext


class PackageNotFound(Exception):
    def __init__(self, spec, formats):
        pkg = parse_requirement(spec)
        msg = ['The index does not have the requested package: ']
        msg.append(pkg.requirement)
        msg.append(formats and ' ({0})'.format(formats) or '')
        super(PackageNotFound, self).__init__(''.join(msg))


class Index(object):

    def __init__(self, base_path):
        self.base_path = base_path
        self.storage = defaultdict(lambda: defaultdict(list))
        self.lock = RLock()

    def scan(self):
        if not os.path.isdir(self.base_path):
            return

        for file_name in os.listdir(self.base_path):
            destination = os.path.join(self.base_path, file_name)
            self.index(destination)

    def ensure_path(self, destination):
        path = os.path.dirname(destination)
        with self.lock:
            if not os.path.isdir(path):
                os.makedirs(path)
        return destination

    def index(self, path):
        pkg = os.path.basename(path)
        name, version = pkg_name(pkg)
        self.storage[safe_name(name)][version].append(pkg)

    def from_file(self, path):
        # Moving the file around
        file_name = '.'.join(split_name(os.path.basename(path))[:2])
        destination = self.ensure_path(os.path.join(self.base_path, file_name))
        shutil.copy(path, destination)
        self.index(destination)
        return destination

    def from_data(self, path, data):
        # Build the name of the package based on its spec and extension
        file_name = '.'.join(split_name(os.path.basename(path))[:2])
        destination = self.ensure_path(os.path.join(self.base_path, file_name))
        with open(destination, 'wb') as fobj:
            fobj.write(data)
        self.index(destination)
        return destination

    def delete(self):
        shutil.rmtree(self.base_path)

    def list_packages(self):
        return self.storage.keys()

    def get_urlhash(self, url, fmt):
        """Returns the hash of the file of an internal url
        """
        with self.open(os.path.basename(url)) as f:
            return {'url': fmt(url), 'sha256': filehash(f, 'sha256')}

    def package_releases(self, package, url_fmt=lambda u: u):
        """List all versions of a package

        Along with the version, the caller also receives the file list with all
        the available formats.
        """
        return [{
            'name': package,
            'version': version,
            'urls': [self.get_urlhash(f, url_fmt) for f in files]
        } for version, files in self.storage.get(package, {}).items()]

    def open(self, fname, mode='r'):
        return open(os.path.abspath(os.path.join(
            self.base_path, os.path.basename(fname))), mode)

    def get(self, query):
        # Read both: "pkg==0.0.0" and "pkg==0.0.0,fmt"
        sym = ';'
        spec, format_ = (sym in query and (query.split(sym)) or (query, ''))
        requirement = parse_requirement(spec)

        # [First step] Looking up the package name parsed from the spec
        versions = self.storage.get(requirement.name)
        if not versions:
            raise PackageNotFound(spec, format_)

        # [Second step] Filter out versions incompatible with our spec
        parsed_versions = {}
        [parsed_versions.update({parse_version(v): v}) for v in versions.keys()]

        filter_cmp = lambda x: all({
            '<':  lambda v: x <  parse_version(v),
            '<=': lambda v: x <= parse_version(v),
            '!=': lambda v: x != parse_version(v),
            '==': lambda v: x == parse_version(v),
            '>=': lambda v: x >= parse_version(v),
            '>':  lambda v: x >  parse_version(v),
        }[op](v) for op, v in requirement.constraints or [])

        compat_versions = [c for c in parsed_versions.keys() if filter_cmp(c)]
        if not compat_versions:
            raise PackageNotFound(spec, format_)

        # [Third step] Find best version to match the given format
        files = []

        # We don't have version or format, so we'll get the latest. Also,
        # we'll bring the wheels preferably, if they're available
        latest_version = versions[parsed_versions[max(compat_versions)]]
        if format_:
            files = [n for n in latest_version if match_format(format_, n)]
        else:
            wheels = [n for n in latest_version if match_format('whl', n)]
            files = wheels or latest_version

        # Unlucky, we really don't have those files
        if not files:
            raise PackageNotFound(spec, format_)

        # Yay, let's return the full path to the user
        return os.path.join(self.base_path, files[0])

########NEW FILE########
__FILENAME__ = install
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps
from collections import defaultdict
from distlib.compat import queue

from .database import Database
from .index import PackageNotFound
from .mapping import Mapping
from .signal import SignalEmitter, Signal
from .util import logger, is_url, parse_requirement, safe_name
from .exceptions import VersionConflict

from .services.base import Service
from .services.downloader import Finder, Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import os
import sys
import time
import traceback
import math
import multiprocessing


PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, field):
    @wraps(func)
    def wrapper(requester, **data):
        if data.get(field, False):
            return func(requester, **data)
    return wrapper


def unique(func, install):
    @wraps(func)
    def wrapper(requester, **data):
        tarball = os.path.basename(data['url'])
        if tarball not in install.downloader.processing_packages:
            return func(requester, **data)
        else:
            install.mapping.repeated.append(data['requirement'])
            install.mapping.requirements.discard(data['requirement'])
    return wrapper


class Install(Service):

    def __init__(self, conf):
        super(Install, self).__init__()

        self.conf = conf
        self.index = self.conf.get('index')
        self.database = Database()
        self.logger = logger(__name__)

        # Used by the CLI tool
        self.update_retrieve_and_build = Signal()
        self.update_install = Signal()
        self.update_upload = Signal()

        # Track dependencies and requirements to be installed
        self.mapping = Mapping()

        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
        })

        cpu_count = multiprocessing.cpu_count()
        p = lambda n: max(int(math.floor((cpu_count / 8.0) * n)), 1)

        self.finder = Finder(size=p(1), **args)
        self.downloader = Downloader(size=p(2), **args)
        self.curdler = Curdler(size=p(4), **args)
        self.dependencer = Dependencer(size=p(1), **args)
        self.installer = Installer(size=cpu_count, **args)
        self.uploader = Uploader(size=cpu_count, **args)

    def pipeline(self):
        # Building the pipeline to [find -> download -> build -> find deps]
        self.finder.connect('finished', unique(self.downloader.queue, self))
        self.downloader.connect('finished', only(self.curdler.queue, 'directory'))
        self.downloader.connect('finished', only(self.curdler.queue, 'tarball'))
        self.downloader.connect('finished', only(self.dependencer.queue, 'wheel'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.queue)

        # Save the wheels that reached the end of the flow
        def queue_install(requester, **data):
            self.mapping.wheels[data['requirement']] = data['wheel']
        self.dependencer.connect('finished', queue_install)

        # Error report, let's just remember what happened
        def update_error_list(name, **data):
            package_name = parse_requirement(data['requirement']).name
            self.mapping.errors[package_name][data['requirement']] = {
                'exception': data['exception'],
                'dependency_of': [data.get('dependency_of')],
            }

        # Count how many packages we have in each place
        def update_count(name, **data):
            self.mapping.stats[name] += 1

        [(s.connect('finished', update_count),
          s.connect('failed', update_error_list)) for s in [
            self.finder, self.downloader, self.curdler,
            self.dependencer, self.installer, self.uploader,
        ]]

    def start(self):
        self.finder.start()
        self.downloader.start()
        self.curdler.start()
        self.dependencer.start()

    def set_url(self, data):
        requirement = data['requirement']
        if is_url(requirement):
            data['url'] = requirement
            return True
        return False

    def set_tarball(self, data):
        try:
            data['tarball'] = \
                self.index.get("{0};~whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def set_wheel(self, data):
        try:
            data['wheel'] = \
                self.index.get("{0};whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def handle(self, requester, **data):
        requirement = safe_name(data['requirement'])
        if not is_url(requirement) and parse_requirement(requirement).name in PACKAGE_BLACKLIST:
            return

        # Filter duplicated requirements
        if requirement in self.mapping.requirements:
            return
        # Filter previously primarily required packages
        if self.mapping.was_directly_required(requirement):
            return
        # Save the requirement and its requester for later
        self.mapping.requirements.add(requirement)
        self.mapping.dependencies[requirement].append(data.get('dependency_of'))

        # Defining which place we're moving our requirements
        service = self.finder
        if self.set_wheel(data):
            service = self.dependencer
        elif self.set_tarball(data):
            service = self.curdler
        elif self.set_url(data):
            service = self.downloader

        # Finally feeding the chosen service
        service.queue(requester, **data)

    def load_installer(self):
        # Look for the best version collected for each package.
        # Failures will be collected and forwarded to the caller.
        errors = defaultdict(dict)
        installable_packages = self.mapping.installable_packages()
        for package_name in installable_packages:
            try:
                _, chosen_requirement = self.mapping.best_version(package_name)
            except Exception as exc:
                self.logger.exception("best_version('%s'): %s:%d (%s) %s",
                    package_name, *traceback.extract_tb(sys.exc_info()[2])[0])
                for requirement in self.mapping.get_requirements_by_package_name(package_name):
                    previous_error = self.mapping.errors[package_name].get(requirement)
                    exception = previous_error['exception'] if previous_error else exc
                    errors[package_name][requirement] = {
                        'exception': exception,
                        'dependency_of': self.mapping.dependencies[requirement],
                    }
            else:
                # It's OK to queue each package without being sure
                # about the availability of all the requirements. The
                # Installer service will not be started until everything
                # is checked.
                self.installer.queue('main',
                    requirement=chosen_requirement,
                    wheel=self.mapping.wheels[chosen_requirement])

        # Check if the number of packages to install is the same as
        # the number of packages initially requested. If it's not
        # true, it means that a few packages could not be built.  We
        # might have valuable information about the possible failures
        # in the `self.errors` dictionary.
        if installable_packages != self.mapping.initially_required_packages():
            errors.update(self.mapping.errors)
        return installable_packages, errors

    def retrieve_and_build(self):
        # Wait until all the packages have the chance to be processed
        while True:
            # Walking over the whole list of requirements to
            # process.
            while True:
                try:
                    requester, sender_data = self._queue.get_nowait()
                    self.handle(requester, **sender_data)
                except queue.Empty:
                    break

            # No more requirements to process, let's take a look in
            # the current situation and see if we're finally ready to
            # bail out.
            total = len(self.mapping.requirements)
            retrieved = self.mapping.count('downloader') + len(self.mapping.repeated)
            built = self.mapping.count('dependencer')

            # Each package might have more than one requirement
            failed = sum(len(x) for x in self.mapping.errors.values())
            self.emit('update_retrieve_and_build',
                total, retrieved, built, failed)
            if total == built + failed:
                break
            time.sleep(0.5)

        # Walk through all the requested requirements and queue their best
        # version
        packages, errors = self.load_installer()
        if errors:
            self.emit('finished', errors)
            return []
        return packages

    def install(self, packages):
        self.installer.start()
        while True:
            total = len(packages)
            installed = self.mapping.count('installer')
            failed = sum(len(x) for x in self.mapping.errors.values())
            self.emit('update_install', total, installed, failed)
            if total == installed + failed:
                break
            time.sleep(0.5)

        # Signaling failures that happened during the installation
        if self.mapping.errors:
            self.emit('finished', self.mapping.errors)
            return []

    def load_uploader(self):
        failures = self.finder.get_servers_to_update()
        total = sum(len(v) for v in failures.values())
        if not total:
            return total

        self.uploader.start()
        for server, package_names in failures.items():
            for package_name in package_names:
                try:
                    _, requirement = self.mapping.best_version(package_name)
                except VersionConflict:
                    continue
                wheel = self.mapping.wheels[requirement]
                self.uploader.queue('main',
                    wheel=wheel, server=server, requirement=requirement)
        return total

    def upload(self):
        total = self.load_uploader()
        while total:
            uploaded = self.mapping.count('uploader')
            self.emit('update_upload', total, uploaded)
            if total == uploaded:
                break
            time.sleep(0.5)

    def run(self):
        packages = self.retrieve_and_build()
        if packages:
            self.install(packages)
        if not self.mapping.errors and self.conf.get('upload'):
            self.upload()
        return self.emit('finished')

########NEW FILE########
__FILENAME__ = mapping
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.version import LegacyMatcher, LegacyVersion

from . import util
from .exceptions import BrokenDependency, VersionConflict


def wheel_version(path):
    """Retrieve the version inside of a package data slot

    If there's no key `version` inside of the data dictionary, we'll
    try to guess the version number from the file name:

    ['forbiddenfruit', '0.1.1', 'cp27', 'none', 'macosx_10_8_x86_64.whl']
                          ^
    this is the guy we get in that crazy split!
    """
    return path.split('-')[1]


class Mapping(object):

    def __init__(self):
        self.requirements = set()
        self.dependencies = defaultdict(list)
        self.stats = defaultdict(int)
        self.errors = defaultdict(dict)
        self.wheels = {}
        self.repeated = []

    def count(self, service):
        return self.stats[service]

    def initially_required_packages(self):
        return set(util.parse_requirement(r).name for r in self.requirements)

    def installable_packages(self):
        # Load all the wheels we built so far into the mapping, so
        # we'll be able to narrow down all the versions collected for
        # each single package to the best one.
        return set(util.parse_requirement(r).name for r in self.wheels)

    def filed_packages(self):
        return list(set(util.parse_requirement(r).name for r in self.requirements))

    def get_requirements_by_package_name(self, package_name):
        return [x for x in self.requirements
            if util.parse_requirement(x).name == util.parse_requirement(package_name).name]

    def available_versions(self, package_name):
        return sorted(set(wheel_version(self.wheels[requirement])
            for requirement in self.requirements
                if self.wheels.get(requirement) and
                    util.parse_requirement(requirement).name == package_name),
                      reverse=True)

    def matching_versions(self, requirement):
        matcher = LegacyMatcher(requirement.replace('-', '_'))
        package_name = util.parse_requirement(requirement).name
        versions = self.available_versions(package_name)
        return [version for version in versions
            if matcher.match(version)]

    def was_directly_required(self, spec):
        for requirement in self.get_requirements_by_package_name(spec):
            if self.is_primary_requirement(requirement):
                return True
        return False

    def is_primary_requirement(self, requirement):
        return bool(self.dependencies[requirement].count(None))

    def best_version(self, requirement_or_package_name, debug=False):
        package_name = util.parse_requirement(requirement_or_package_name).name
        requirements = self.get_requirements_by_package_name(package_name)

        # Used to remember in which requirement we found each version
        requirements_by_version = {}
        get_requirement = lambda v: (v, requirements_by_version[v])

        # A helper that sorts the versions putting the newest ones first
        newest = lambda versions: sorted(versions, key=LegacyVersion, reverse=True)[0]

        # Gather all version info available inside of all requirements
        all_versions = []
        all_constraints = []
        primary_versions = []
        for requirement in requirements:
            if not self.wheels.get(requirement):
                continue
            version = wheel_version(self.wheels[requirement])
            requirements_by_version[version] = requirement
            if self.is_primary_requirement(requirement):
                primary_versions.append(version)

            versions = self.matching_versions(requirement)
            all_versions.extend(versions)
            all_constraints.append(util.safe_constraints(requirement))

        # List that will gather all the primary versions. This catches
        # duplicated first level requirements with different versions.
        if primary_versions:
            return get_requirement(newest(primary_versions))

        # Find all the versions that appear in all the requirements
        compatible_versions = [v for v in all_versions
            if all_versions.count(v) == len(requirements)]

        if not compatible_versions:
            # Format the constraints string like this: " (c [, c...])"
            constraints = ', '.join(sorted(filter(None,
                all_constraints), reverse=True))
            constraints = ' ({0})'.format(constraints) if constraints else ''
            available_versions = ', '.join(sorted(
                self.available_versions(package_name),
                reverse=True))

            # Just a nice message depending on finding any versions or
            # not
            raise VersionConflict(available_versions
                and 'Requirement: {0}{1}, Available versions: {2}'.format(
                    package_name,
                    constraints,
                    available_versions,
                )
                or 'Requirement: {0}{1}, no available versions were found'.format(
                    package_name,
                    constraints,
                )
            )

        return get_requirement(newest(compatible_versions))

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, print_function, unicode_literals
from ..signal import Signal, SignalEmitter
from ..util import logger
from distlib.compat import queue

import sys
import threading
import time
import traceback

# See `Service._worker()`. This is the sentinel that gently stops the iterator
# over there.
SENTINEL = (None, {})

# Number of threads that a service will spawn by default.
DEFAULT_CONCURRENCY = 2


class Service(SignalEmitter):

    def __init__(self, size=DEFAULT_CONCURRENCY, **args):
        super(Service, self).__init__()

        self.size = size
        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = logger(__name__)

        # Components to implement the thread pool
        self._queue = queue.Queue()
        self.pool = []

        # Declaring signals
        self.started = Signal()
        self.finished = Signal()
        self.failed = Signal()

    def queue(self, requester, **data):
        self.logger.debug('%s.queue(from="%s", data="%s")', self.name, requester, data)
        self._queue.put((requester, data))
        return self

    def start(self):
        self.logger.debug('%s.start()', self.name)
        for _ in range(self.size):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.pool.append(worker)
        return self

    def join(self):
        # We need to separate loops cause we can't actually tell which thread
        # got each sentinel
        for worker in self.pool:
            self._queue.put(SENTINEL)
        for worker in self.pool:
            worker.join()
        self.workers = []

    def handle(self, requester, sender_data):
        raise NotImplementedError(
            "The service subclass should override this method")

    def __call__(self, requester, **kwargs):
        return self.handle(requester, kwargs)

    # -- Private API --

    def _worker(self):
        name = '{0}[{1}]'.format(self.name, threading.current_thread().name)

        # If the service consumer invokes `.queue(None, None)` it causes the
        # worker to die elegantly by matching the following sentinel:
        for requester, sender_data in iter(self._queue.get, SENTINEL):
            self.logger.debug('%s.run(data="%s")', name, sender_data)
            try:
                self.emit('started', self.name, **sender_data)
                result = self(requester, **sender_data) or {}
                self._queue.task_done()
            except BaseException:
                fname, lineno, fn, text = traceback.extract_tb(sys.exc_info()[2])[0]
                self.logger.exception(
                    '%s.run(from="%s", data="%s") failed:\n'
                    '%s:%d (%s) %s',
                    name, requester, sender_data,
                    fname, lineno, fn, text,
                )
                sender_data.update(exception=sys.exc_info()[1])
                self.emit('failed', self.name, **sender_data)
            else:
                self.logger.debug('%s.run(data="%s"): %s', name, sender_data, result)
                self.emit('finished', self.name, **result)

########NEW FILE########
__FILENAME__ = curdler
from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import UnpackingError, BuildError, NoSetupScriptFound
from ..util import execute_command
from .base import Service

import io
import os
import re
import sys
import shutil
import tempfile
import zipfile
import tarfile


# We'll use it to call the `setup.py` script of packages we're building
PYTHON_EXECUTABLE = sys.executable.encode(sys.getfilesystemencoding())

# Those are the formats we know how to extract, if you need to add a new one
# here, please refer to the page[0] to check the magic bits of the file type
# you wanna add.
#
# [0] http://www.garykessler.net/library/file_sigs.html
SUPPORTED_FORMATS = {
    b"\x1f\x8b\x08": "gz",
    b"\x42\x5a\x68": "bz2",
    b"\x50\x4b\x03\x04": "zip"
}

# Must be greater than the length of the biggest key of `SUPPORTED_FORMATS`, to
# be used as the block size to `file.read()` in `guess_file_type()`
SUPPORTED_FORMATS_MAX_LEN = (max(len(x) for x in SUPPORTED_FORMATS) + 7) & ~7

# Matcher for egg-info directories
EGG_INFO_RE = re.compile(r'(-py\d\.\d)?\.egg-info', re.I)


def guess_file_type(filename):
    with io.open(filename, 'rb') as f:
        file_start = f.read(SUPPORTED_FORMATS_MAX_LEN)
    for magic, filetype in SUPPORTED_FORMATS.items():
        if file_start.startswith(magic):
            return filetype
    raise UnpackingError('Unknown compress format for file %s' % filename)


def unpack(package):
    file_type = guess_file_type(package)

    # The only extensions we currently support are `zip', `gz' and `bz2'
    if file_type in ('gz', 'bz2'):
        fp = tarfile.open(package, 'r')
        return fp, [x.name for x in fp.getmembers()]
    if file_type == 'zip':
        fp = zipfile.ZipFile(package)
        return fp, fp.namelist()
    raise UnpackingError('Unknown compress format for file %s' % package)


def find_setup_script(names):
    setup_scripts = [x for x in names if x.endswith('setup.py')]
    if not setup_scripts:
        raise NoSetupScriptFound('No setup.py script found')
    return sorted(setup_scripts, key=lambda e: len(e))[0]


def get_setup_from_package(package, destination):
    fp, namelist = unpack(package=package)
    try:
        setup_py = find_setup_script(namelist)
        fp.extractall(destination)
    finally:
        fp.close()
    return os.path.join(destination, setup_py)


def run_setup_script(path, command, *custom_args):
    # What we're gonna run
    cwd = os.path.dirname(path)
    script = os.path.basename(path)

    # Building the argument list starting from the interpreter path. This
    # weird we're doing here was copied from `pip` and it basically forces
    # the usage of setuptools instead of distutils or any other weird
    # library people might be using.
    args = ['-c']
    args.append(
        r"import setuptools;__file__=%r;"
        r"exec(compile(open(__file__).read().replace('\r\n', '\n'), __file__, 'exec'))" % script)
    args.append(command)
    args.extend(custom_args)

    # Boom! Executing the command.
    execute_command(PYTHON_EXECUTABLE, *args, cwd=cwd)

    # Directory where the wheel will be saved after building it, returning
    # the path pointing to the generated file
    output_dir = os.path.join(cwd, 'dist')
    return os.path.join(output_dir, os.listdir(output_dir)[0])


class Curdler(Service):

    def handle(self, requester, data):
        requirement = data['requirement']
        tarball = data.get('tarball')
        directory = data.get('directory')

        # Place used to unpack the wheel
        destination = tempfile.mkdtemp()

        # Unpackaging the file we just received. The unpack function will give
        # us the path for the setup.py script and building the wheel file with
        # the `bdist_wheel` command.
        try:
            #  may raise NoSetupScriptFound
            setup_py = (os.path.join(directory, 'setup.py') \
                if directory
                else get_setup_from_package(tarball, destination))
            wheel_file = run_setup_script(setup_py, 'bdist_wheel')
            return {
                'wheel': self.index.from_file(wheel_file),
                'requirement': requirement
            }
        except BaseException as exc:
            raise BuildError(str(exc))
        finally:
            shutil.rmtree(destination)

            # This folder was created by the downloader and it's a temporary
            # resource that we don't need anymore.
            if directory:
                shutil.rmtree(directory)

########NEW FILE########
__FILENAME__ = dependencer
from __future__ import absolute_import, unicode_literals, print_function
from ..signal import Signal
from .. import util
from .base import Service
from distlib.wheel import Wheel


class Dependencer(Service):

    def __init__(self, *args, **kwargs):
        super(Dependencer, self).__init__(*args, **kwargs)
        self.dependency_found = Signal()

    def handle(self, requester, data):
        requirement = data['requirement']
        dependencies = Wheel(data['wheel']).metadata.dependencies
        extra_sections = set(util.parse_requirement(requirement).extras or ())

        # Honor the `extras` section of the requirement we just received
        found = dependencies.get('install', [])
        for section, items in dependencies.get('extras', {}).items():
            if section in extra_sections:
                found.extend(items)

        # Telling the world about the dependencies we found
        for dependency in found:
            self.emit('dependency_found', self.name,
                      requirement=util.safe_name(dependency),
                      dependency_of=requirement)

        # Keep the message flowing
        return {'requirement': requirement, 'wheel': data['wheel']}

########NEW FILE########
__FILENAME__ = downloader
from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import RequirementNotFound, UnknownURL, TooManyRedirects, ReportableError
from .. import util
from .base import Service
from distlib import database, metadata, compat, locators

import os
import re
import json
import urllib3
import tempfile
import distlib.version


# Hardcoded vaue for the size of the http pool used a couple times in this
# module. Not the perfect place, though might fix the ClosedPoolError we're
# getting eventually.
POOL_MAX_SIZE = 10

# Number of max redirect follows. See `http_retrieve()` for details.
REDIRECT_LIMIT = 20


def get_locator(conf):
    curds = [CurdlingLocator(u) for u in conf.get('curdling_urls', [])]
    pypi = [PyPiLocator(u) for u in conf.get('pypi_urls', [])]
    return AggregatingLocator(*(curds + pypi), scheme='legacy')


def find_packages(locator, requirement, versions):
    scheme = distlib.version.get_scheme(locator.scheme)
    matcher = scheme.matcher(requirement.requirement)

    result = {}
    if versions:
        slist = []
        for v in versions:
            if matcher.match(matcher.version_class(v)):
                slist.append(v)
        slist = sorted(slist, key=scheme.key)
        if len(slist):
            result = versions[slist[-1]]

    return result


def update_url_credentials(base_url, other_url):
    base = compat.urlparse(base_url)
    other = compat.urlparse(other_url)

    # If they're not from the same server, we return right away without
    # trying to update anything
    if base.hostname != other.hostname or base.port != other.port:
        return other.geturl()

    # Update the `netloc` field and return the `other` url
    return other._replace(netloc=base.netloc).geturl()


def parse_url_and_revision(url):
    parsed_url = compat.urlparse(url)
    revision = None
    if '@' in parsed_url.path:
        path, revision = parsed_url.path.rsplit('@', 1)
        parsed_url = parsed_url._replace(path=path)
    return parsed_url.geturl(), revision


def http_retrieve(pool, url, attempt=0):
    if attempt >= REDIRECT_LIMIT:
        raise TooManyRedirects('Too many redirects')

    # Params to be passed to request. The `preload_content` must be set to
    # False, otherwise `read()` wont honor `decode_content`.
    params = {
        'headers': util.get_auth_info_from_url(url),
        'preload_content': False,
        'redirect': False,
    }

    # Request the url and ensure we've reached the final location
    response = pool.request('GET', url, **params)
    if 'location' in response.headers:
        location = response.headers['location']
        if location.startswith('/'):
            url = compat.urljoin(url, location)
        else:
            url = location
        return http_retrieve(pool, url, attempt=attempt + 1)
    return response, url


def get_opener():
    http_proxy = os.getenv('http_proxy')
    if http_proxy:
        parsed_url = compat.urlparse(http_proxy)
        proxy_headers = util.get_auth_info_from_url(
            http_proxy, proxy=True)
        return urllib3.ProxyManager(
            proxy_url=parsed_url.geturl(),
            proxy_headers=proxy_headers)
    return urllib3.PoolManager()


class ComparableLocator(object):
    def __eq__(self, other):
        return self.base_url == other.base_url

    def __repr__(self):
        return '{0}(\'{1}\')'.format(self.__class__.__name__, self.base_url)


class AggregatingLocator(locators.AggregatingLocator):

    def locate(self, requirement, prereleases=True):
        pkg = util.parse_requirement(requirement)
        for locator in self.locators:
            versions = locator.get_project(pkg.name)
            packages = find_packages(locator, pkg, versions)
            if packages:
                return packages


class PyPiLocator(locators.SimpleScrapingLocator, ComparableLocator):
    def __init__(self, url, **kwargs):
        super(PyPiLocator, self).__init__(url, **kwargs)
        self.opener = get_opener()

    def _get_project(self, name):
        # It sounds lame, but we're trying to match requirements with more than
        # one word separated with either `_` or `-`. Notice that we prefer
        # hyphens cause there is currently way more packages using hyphens than
        # underscores in pypi.p.o. Let's wait for the best here.
        options = [name]
        if '-' in name or '_' in name:
            options = (name.replace('_', '-'), name.replace('-', '_'))

        # Iterate over all the possible names a package can have.
        for package_name in options:
            url = compat.urljoin(self.base_url, '{0}/'.format(
                compat.quote(package_name)))
            found = self._fetch(url, package_name)
            if found:
                return found

    def _visit_link(self, project_name, link):
        self._seen.add(link)
        locators.logger.debug('_fetch() found link: %s', link)
        info = not self._is_platform_dependent(link) \
            and self.convert_url_to_download_info(link, project_name) \
            or None

        versions = {}
        if info:
            self._update_version_data(versions, info)
            return list(versions.items())[0]
        return None, None

    def _fetch(self, url, project_name, subvisit=False):
        locators.logger.debug('fetch(%s, %s)', url, project_name)
        versions = {}
        page = self.get_page(url)
        for link, rel in (page and page.links or []):
            # Let's instrospect one level down
            if self._should_queue(link, url, rel) and not subvisit:
                versions.update(self._fetch(link, project_name, subvisit=True))

            # Let's not see anything twice, I saw this check on distlib it
            # might be useful.
            if link not in self._seen:
                # Well, here we're ensuring that the first link of a given
                # version will be the one. Even if we find another package for
                # the same version, the first one will be used.
                version, distribution = self._visit_link(project_name, link)
                if version and version not in versions:
                    versions[version] = distribution
        return versions

    def get_page(self, url):
        # http://peak.telecommunity.com/DevCenter/EasyInstall#package-index-api
        scheme, netloc, path, _, _, _ = compat.urlparse(url)
        if scheme == 'file' and os.path.isdir(url2pathname(path)):
            url = compat.urljoin(ensure_slash(url), 'index.html')

        # The `retrieve()` method follows any eventual redirects, so the
        # initial url might be different from the final one
        try:
            response, final_url = http_retrieve(self.opener, url)
        except urllib3.exceptions.MaxRetryError:
            return

        content_type = response.headers.get('content-type', '')
        if locators.HTML_CONTENT_TYPE.match(content_type):
            data = response.data
            encoding = response.headers.get('content-encoding')
            if encoding:
                decoder = self.decoders[encoding]   # fail if not found
                data = decoder(data)
            encoding = 'utf-8'
            m = locators.CHARSET.search(content_type)
            if m:
                encoding = m.group(1)
            try:
                data = data.decode(encoding)
            except UnicodeError:
                data = data.decode('latin-1')    # fallback
            return locators.Page(data, final_url)


class CurdlingLocator(locators.Locator, ComparableLocator):

    def __init__(self, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.base_url = url
        self.url = url
        self.opener = get_opener()
        self.requirements_not_found = []

    def get_distribution_names(self):
        return json.loads(
            http_retrieve(self.opener,
                compat.urljoin(self.url, 'api'))[0].data)

    def _get_project(self, name):
        # Retrieve the info
        url = compat.urljoin(self.url, 'api/' + name)
        try:
            response, _ = http_retrieve(self.opener, url)
        except urllib3.exceptions.MaxRetryError:
            return None

        if response.status == 200:
            data = json.loads(response.data)
            return dict((v['version'], self._get_distribution(v)) for v in data)
        else:
            self.requirements_not_found.append(name)

    def _get_distribution(self, version):
        # Source url for the package
        source_url = version['urls'][0]  # TODO: prefer whl files

        # Build the metadata
        mdata = metadata.Metadata(scheme=self.scheme)
        mdata.name = version['name']
        mdata.version = version['version']
        mdata.download_url = source_url['url']

        # Building the dist and associating the download url
        distribution = database.Distribution(mdata)
        distribution.locator = self
        return distribution


class Finder(Service):

    def __init__(self, *args, **kwargs):
        super(Finder, self).__init__(*args, **kwargs)
        self.opener = get_opener()
        self.locator = get_locator(self.conf)

    def handle(self, requester, data):
        requirement = data['requirement']
        prereleases = self.conf.get('prereleases', True)
        distribution = self.locator.locate(requirement, prereleases)
        if not distribution:
            raise RequirementNotFound(
                'Requirement `{0}\' not found'.format(requirement))
        return {
            'requirement': data['requirement'],
            'url': distribution.metadata.download_url,
            'locator_url': distribution.locator.base_url,
        }

    def get_servers_to_update(self):
        failures = {}
        for locator in self.locator.locators:
            if isinstance(locator, CurdlingLocator) and locator.requirements_not_found:
                failures[locator.base_url] = locator.requirements_not_found
        return failures


class Downloader(Service):

    def __init__(self, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.opener = get_opener()
        self.locator = get_locator(self.conf)

        # List of packages that we're aware of, so people that want to send
        # jobs to the downloader can avoid duplications.
        self.processing_packages = set()

    def queue(self, requester, **data):
        self.processing_packages.add(os.path.basename(data['url']))
        super(Downloader, self).queue(requester, **data)

    def handle(self, requester, data):
        field_name, location = self.download(data['url'], data.get('locator_url'))
        return {
            'requirement': data['requirement'],
            field_name: location,
        }

    def download(self, url, locator_url=None):
        final_url = url

        # We're dealing with a requirement, not a link
        if locator_url:
            # The locator's URL might contain authentication credentials, while
            # the package URL might not (the scraper doesn't return with that
            # information)
            final_url = update_url_credentials(locator_url, url)

        # Find out the right handler for the given protocol present in the
        # download url.
        protocol_mapping = {
            re.compile('^https?'): self._download_http,
            re.compile('^git\+'): self._download_git,
            re.compile('^hg\+'): self._download_hg,
            re.compile('^svn\+'): self._download_svn,
        }

        try:
            handler = [i for i in protocol_mapping.keys() if i.findall(url)][0]
        except IndexError:
            raise UnknownURL(
                util.spaces(3, '\n'.join([
                    '"{0}"'.format(url),
                    '',
                    'Your URL looks wrong. Make sure it\'s a valid HTTP',
                    'link or a valid VCS link prefixed with the name of',
                    'the VCS of your choice. Eg.:',
                    '',
                    ' $ curd install https://pypi.python.org/simple/curdling/curdling-0.1.2.tar.gz\n'
                    ' $ curd install git+ssh://github.com/clarete/curdling.git\n'
                ])))

        # Remove the protocol prefix from the url before passing to
        # the handler which is not prepared to handle urls starting
        # with `vcs+`. This RE is smart enough to handle plus (+)
        # signs out of the scheme. Like in this example:
        #   https://launchpad.com/path/+download/dirspec-13.10.tar.gz
        url = re.sub('^([^\+]+)\+([^:]+\:)', r'\2', final_url)
        return protocol_mapping[handler](url)

    def _download_http(self, url):
        response, final_url = http_retrieve(self.opener, url)
        if final_url:
            url = final_url
        if response.status != 200:
            raise ReportableError(
                'Failed to download url `{0}\': {1} ({2})'.format(
                    url,
                    response.status,
                    compat.httplib.responses[response.status],
                ))

        # Define what kind of package we've got
        field_name = 'wheel' if url.endswith('.whl') else 'tarball'

        # Now that we're sure that our request was successful
        header = response.headers.get('content-disposition', '')
        file_name = re.findall(r'filename=\"?([^;\"]+)', header)
        return field_name, self.index.from_data(
            file_name and file_name[0] or url,
            response.read(cache_content=True, decode_content=False))

    def _download_git(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        util.execute_command('git', 'clone', url, destination)
        if revision:
            util.execute_command('git', 'reset', '--hard', revision,
                cwd=destination)
        return 'directory', destination

    def _download_hg(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        util.execute_command('hg', 'clone', url, destination)
        if revision:
            util.execute_command('hg', 'update', '-q', revision,
                cwd=destination)
        return 'directory', destination

    def _download_svn(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        params = ['svn', 'co', '-q']
        if revision:
            params.append('-r')
            params.append(revision)
        params += [url, destination]
        util.execute_command(*params)
        return 'directory', destination

########NEW FILE########
__FILENAME__ = installer
from __future__ import absolute_import, print_function, unicode_literals
from ..util import parse_requirement
from .base import Service
from distlib.wheel import Wheel

import sys
import os.path


PREFIX = os.path.normpath(sys.prefix)


def get_distribution_paths(name):
    """Return target paths where the package content should be installed"""
    pyver = 'python' + sys.version[:3]

    paths = {
        'prefix' : '{prefix}',
        'data'   : '{prefix}/lib/{pyver}/site-packages',
        'purelib': '{prefix}/lib/{pyver}/site-packages',
        'platlib': '{prefix}/lib/{pyver}/site-packages',
        'headers': '{prefix}/include/{pyver}/{name}',
        'scripts': '{prefix}/bin',
    }

    # pip uses a similar path as an alternative to the system's (read-only)
    # include directory:
    if hasattr(sys, 'real_prefix'):  # virtualenv
        paths['headers'] = os.path.abspath(
            os.path.join(sys.prefix, 'include', 'site', pyver, name))

    # Replacing vars
    for key, val in paths.items():
        paths[key] = val.format(prefix=PREFIX, name=name, pyver=pyver)
    return paths


class Installer(Service):

    def handle(self, requester, data):
        name = parse_requirement(data['requirement']).name
        wheel = Wheel(data['wheel'])
        wheel.install(get_distribution_paths(name))
        return data

########NEW FILE########
__FILENAME__ = uploader
from __future__ import absolute_import, print_function, unicode_literals
from .base import Service
from ..util import get_auth_info_from_url
from distlib import compat

import io
import os
import urllib3


class Uploader(Service):

    def __init__(self, *args, **kwargs):
        super(Uploader, self).__init__(*args, **kwargs)
        self.opener = urllib3.PoolManager()

    def handle(self, requester, data):
        # Preparing the url to PUT the file
        wheel = data.get('wheel')
        server = data.get('server')
        file_name = os.path.basename(wheel)
        url = compat.urljoin(server, 'p/{0}'.format(file_name))

        # Sending the file to the server. Both `method` and `url` parameters
        # for calling `request_encode_body()` must be `str()` instances, not
        # unicode.
        contents = io.open(wheel, 'rb').read()
        self.opener.request_encode_body(
            b'PUT', bytes(url), {file_name: (file_name, contents)},
            headers=get_auth_info_from_url(url))
        return {'upload_url': url, 'requirement': data['requirement']}

########NEW FILE########
__FILENAME__ = signal
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
import threading


class Signal(list):
    pass


class SignalEmitter(object):

    def __init__(self):
        self.lock = threading.RLock()

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def get_signal_or_explode(self, signal):
        try:
            with self.lock:
                return getattr(self, signal)
        except AttributeError:
            raise AttributeError(
                "There is no such signal ({0}) in this emitter ({1})".format(
                    signal, self.name))

    def connect(self, signal, callback):
        # Well, now we use the list-like interface of signal to file this new
        # callback under the previously retrieved signal container.
        self.get_signal_or_explode(signal).append(callback)

    def emit(self, signal, *args, **kwargs):
        for callback in self.get_signal_or_explode(signal):
            callback(*args, **kwargs)

########NEW FILE########
__FILENAME__ = uninstall
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals

from . import exceptions
from .database import Database
from .util import logger, parse_requirement


class Uninstall(object):

    def __init__(self, conf):
        self.conf = conf
        self.packages = []
        self.logger = logger(__name__)

    def report(self):
        pass

    def request_uninstall(self, requirement):
        self.packages.append(parse_requirement(requirement).name)

    def run(self):
        for package in self.packages:
            self.logger.info("Removing package %s", package)

            try:
                Database.uninstall(package)
            except exceptions.PackageNotInstalled:
                self.logger.error("Package %s does not exist, skipping", package)

########NEW FILE########
__FILENAME__ = util
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from distlib import compat, util
from base64 import b64encode

import io
import os
import re
import hashlib
import logging
import subprocess
import urllib3


INCLUDE_PATTERN = re.compile(r'-r\s*\b([^\b]+)')

LINK_PATTERN = re.compile(r'^([^\:]+):\/\/.+')

ROOT_LOGGER = logging.getLogger('curdling')


class Requirement(object):
    name = None


def is_url(requirement):
    return ':' in requirement


def safe_name(requirement):
    return requirement if is_url(requirement) \
        else safe_requirement(requirement)


def safe_requirement(requirement):
    safe = requirement.lower().replace('_', '-')
    parsed = util.parse_requirement(safe)
    output = parsed.name
    if parsed.extras:
        output += '[{0}]'.format(','.join(parsed.extras))
    if parsed.constraints:
        def c(operator, version):
            return version if operator == '==' \
                else '{0} {1}'.format(operator, version)
        output += ' ({0})'.format(
            ', '.join(c(*i) for i in parsed.constraints))
    return output


def safe_constraints(spec):
    if is_url(spec):
        return None
    constraints = util.parse_requirement(spec).constraints or ()
    constraint = lambda k, v: \
        ('{0} {1}'.format(k, v)
         .replace('== ', '')
         .replace('==', ''))
    return ', '.join(constraint(k, v) for k, v in constraints) or None


def parse_requirement(spec):
    if not is_url(spec):
        requirement = util.parse_requirement(spec)
        requirement.name = safe_name(requirement.name)
        requirement.requirement = safe_requirement(spec)
        requirement.is_link = False
    else:
        requirement = Requirement()
        requirement.name = spec
        requirement.requirement = spec
        requirement.constraints = ()
        requirement.is_link = True
        requirement.extras = ()
    return requirement


def split_name(fname):
    name, ext = os.path.splitext(fname)

    try:
        ext, frag = ext.split('#')
    except ValueError:
        frag = ''
    return name, ext[1:], frag


def expand_requirements(open_file):
    requirements = []

    for req in open_file.read().splitlines():
        req = req.split('#', 1)[0].strip()
        if not req:
            continue

        # Handling special lines that start with `-r`, so we can have files
        # including other files.
        include = INCLUDE_PATTERN.findall(req)
        if include:
            requirements.extend(expand_requirements(io.open(include[0])))
            continue

        # Finally, we're sure that it's just a package description
        requirements.append(safe_name(req))
    return requirements


def filehash(f, algo, block_size=2**20):
    algo = getattr(hashlib, algo)()
    while True:
        data = f.read(block_size)
        if not data:
            break
        algo.update(data)
    return algo.hexdigest()


def spaces(count, text):
    return '\n'.join('{0}{1}'.format(' ' * count, line)
        for line in text.splitlines())


def get_auth_info_from_url(url, proxy=False):
    parsed = compat.urlparse(url)
    if parsed.username:
        auth = '{0}:{1}'.format(parsed.username, parsed.password)

        # The caller is not interested in proxy headers
        if not proxy:
            return urllib3.util.make_headers(basic_auth=auth)

        # Proxy-Authentication support
        return {'proxy-authorization':
            'Basic ' + b64encode(auth.encode('utf-8')).decode('ascii')}
    return {}


def execute_command(name, *args, **kwargs):
    command = subprocess.Popen((name,) + args,
        env=os.environ,
        stderr=subprocess.PIPE, stdout=subprocess.PIPE,
        **kwargs)
    _, errors = command.communicate()
    if command.returncode != 0:
        raise Exception(errors)


def logger(name):
    logger_instance = logging.getLogger(name)
    logger_instance.parent = ROOT_LOGGER
    return logger_instance

########NEW FILE########
__FILENAME__ = version
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = '0.4.0'

########NEW FILE########
__FILENAME__ = __main__
from __future__ import absolute_import, print_function, unicode_literals
from curdling.web import Server

import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description='Share your cheese binaries with your folks')

    parser.add_argument(
        'curddir', metavar='DIRECTORY',
        help='Path for your cache directory')

    parser.add_argument(
        '-d', '--debug', action='store_true', default=False,
        help='Runs without gevent and enables debug')

    parser.add_argument(
        '-H', '--host', default='0.0.0.0',
        help='Host name to bind')

    parser.add_argument(
        '-p', '--port', type=int, default=8000,
        help='Port to bind')

    parser.add_argument(
        '-u', '--user-db',
        help='An htpasswd-compatible file saying who can access your curd server')

    return parser.parse_args()


def main():
    args = parse_args()
    server = Server(args.curddir, args.user_db)
    server.start(args.host, args.port, args.debug)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = wheel
# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import email
import zipfile
from .version import __version__


class TagBag(dict):
    def __init__(self, *args, **kwargs):
        super(TagBag, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def from_input(cls, value):
        return value \
            if hasattr(value, 'lower') and value.lower() not in ('any', 'none') \
            else None


class Wheel(object):

    def __init__(self):
        self.distribution = None
        self.version = None
        self.build = None
        self.tags = TagBag()

        # Store information about the archive itself. Information in
        # this field is stored/read from the WHEEL file inside of the
        # `.whl` archive.
        self.information = {}

    @classmethod
    def from_name(cls, name):
        name = name.replace('.whl', '')
        pieces = name.split('-')
        offset = 6 - len(pieces)

        instance = cls()
        instance.distribution = pieces[0]
        instance.version = pieces[1]
        instance.build = pieces[2] if not offset else None
        instance.tags.pyver = pieces[3 - offset]
        instance.tags.abi = TagBag.from_input(pieces[4 - offset])
        instance.tags.arch = TagBag.from_input(pieces[5 - offset])
        return instance

    @classmethod
    def from_file(cls, path):
        wheel = cls.from_name(os.path.basename(path))
        archive = zipfile.ZipFile(path)
        wheel.information.update(wheel.read_wheel_file(archive))
        return wheel

    def name(self):
        return '-'.join((
            self.distribution,
            self.version,
            self.build,
            self.tags.pyver,
            self.tags.abi or 'none',
            self.tags.arch or 'any',
        ))

    def expand_tags(self):
        return ['-'.join([
            pyver,
            self.tags.abi or 'none',
            self.tags.arch or 'any',
        ]) for pyver in self.tags.pyver.split('.')]

    def info(self):
        info = {
            'Wheel-Version': '1.0',  # Shamelessly hardcoded
            'Generator': 'Curdling {0}'.format(__version__),
            'Root-Is-Purelib': 'True',
            'Tag': self.expand_tags(),
        }

        # Add the build tag to the WHEEL file as well
        if self.build:
            info['Build'] = self.build

        info.update(self.information)
        return info

    def dist_info_path(self):
        return '{0}-{1}.dist-info'.format(
            self.distribution, self.version)

    def read_wheel_file(self, archive):
        content = archive.read(
            os.path.join(self.dist_info_path(), 'WHEEL'))

        # This hacky thing will prevent the `.decode()` method from
        # being called unless we actually have a bytes instance.
        # Which will never happen in python2.6, because bytes is just
        # an alias to `str`.
        message = email.message_from_string(
            content if str == bytes else content.decode('ascii'))

        # Tags might be repeated, dictionaries don't repeat keys
        fields = dict(message)
        fields.update({'Tag': message.get_all('Tag')})

        return fields

########NEW FILE########
__FILENAME__ = __main__
# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from curdling.tool import main
raise SystemExit(main())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Curdling documentation build configuration file, created by
# sphinx-quickstart on Sat Oct 26 23:21:28 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.pngmath',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Curdling'
copyright = u'2013, Lincoln Clarete'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.4'
# The full version, including alpha/beta/rc tags.
release = '0.3.4'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'curdling'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index':    ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Curdlingdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'Curdling.tex', u'Curdling Documentation',
   u'Lincoln Clarete', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'curdling', u'Curdling Documentation',
     [u'Lincoln Clarete'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Curdling', u'Curdling Documentation',
   u'Lincoln Clarete', 'Curdling', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = hello
import sure
import distlib

def blah():
    print(distlib.in_venv())

########NEW FILE########
__FILENAME__ = test_freeze
from curdling import freeze
from . import FIXTURE


def test_get_module_path():
    "freeze.get_module_path() Should return the file path of a module without importing it"

    # Given a module name
    module = 'sure'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('sure')


def test_get_distribution_from_source_file():
    "freeze.get_distribution_from_source_file(file_path) Should return the Distribution that contains `file_path`"

    # Given a path for a package
    path = 'sure/__init__.pyc'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see the right distribution was found
    distribution.name.should.equal('sure')


def test_get_distribution_from_source_file_file_path_being_a_directory():
    "freeze.get_distribution_from_source_file(file_path) Should support receiving relative directories in `file_path`"

    # Given a path for a package
    path = 'sure'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see the right distribution was found
    distribution.name.should.equal('sure')


def test_get_requirements():
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from distlib import util

print(util.in_venv())
'''

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['distlib==0.1.2'])  # Guaranteed in our requirements.txt


def test_get_requirements():
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from mock import Mock

print(Mock())
'''

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['mock==1.0.1'])  # Guaranteed in our requirements.txt


def test_find_python_files():
    "freeze.find_python_files(path) Should find all the python files under `path`"

    # Given the following directory
    codebase = FIXTURE('codebase1')

    # When I list all the available python files
    python_files = freeze.find_python_files(codebase)

    # Then I see the list with all the files present in that given
    # directory
    sorted(python_files).should.equal(sorted([
        'codebase1/__init__.py',
        'codebase1/hello.py',
    ]))

########NEW FILE########
__FILENAME__ = test_index
from __future__ import absolute_import, print_function, unicode_literals
from curdling.index import Index, PackageNotFound
from . import FIXTURE


def test_index_from_file():
    "It should be possible to index packages from files"

    # Given the following index
    index = Index(FIXTURE('index'))

    # When I index a file
    index.from_file(FIXTURE('storage1/gherkin-0.1.0.tar.gz'))

    # Then I see it inside of the index
    index.get('gherkin==0.1.0;gz').should.equal(
        FIXTURE('index/gherkin-0.1.0.tar.gz'),
    )

    # And that there's no wheel available yet
    index.get.when.called_with('gherkin==0.1.0;whl').should.throw(
        PackageNotFound,
    )

    # And I clean the mess
    index.delete()


def test_index_from_data():
    "It should be possible to index data from memory"

    # Given the following index
    index = Index(FIXTURE('index'))

    # When I index a file
    data = open(FIXTURE('storage1/gherkin-0.1.0.tar.gz'), 'rb').read()
    index.from_data(path='gherkin-0.1.0.tar.gz', data=data)

    # Then I see it inside of the index
    index.get('gherkin==0.1.0').should.equal(
        FIXTURE('index/gherkin-0.1.0.tar.gz'),
    )

    # And I clean the mess
    index.delete()


def test_index_scan():
    "It should be possible to scan for already existing folders"

    # Given that I have an index that points to a folder that already contains
    # packages
    index = Index(FIXTURE('storage1'))

    # When I scan the directory
    index.scan()

    # Then I can look for packages
    index.get('gherkin==0.1.0').should.equal(
        FIXTURE('storage1/gherkin-0.1.0.tar.gz'),
    )


def test_index_scan_when_there_is_no_dir():
    "Index.scan() should not fail when the dir does not exist"

    # Given that I have an index that points to a directory that already
    # contains packages
    index = Index('I know this directory does not exist')

    # When I scan the directory, I see it does not fail
    index.scan()

########NEW FILE########
__FILENAME__ = test_main
from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock
from nose.tools import nottest
import os
import errno

from curdling import util
from curdling.exceptions import ReportableError
from curdling.index import Index
from curdling.install import Install
from curdling.database import Database

from curdling.services.base import Service
from curdling.services.downloader import Downloader, Finder
from curdling.services.curdler import Curdler
from curdling.services.installer import Installer

from . import FIXTURE

DUMMY_PYPI = 'http://localhost:9000/simple/'

DUMMY_PYPI_URL = lambda path: '{0}{1}'.format(DUMMY_PYPI, path)


def test_downloader_with_no_sources():
    "It should be possible to download packages from pip repos with no sources"

    # Given the following downloader component with NO SOURCES
    finder = Finder()

    # When I try to retrieve a package from it, than I see it just blows up
    # with a nice exception
    finder.handle.when.called_with(
        'tests', {'requirement': 'gherkin==0.1.0'}).should.throw(
            ReportableError)


def test_downloader():
    "It should be possible to download packages from pip repos"

    # Given that I have a finder pointing to our local pypi server
    finder = Finder(**{
        'conf': {'pypi_urls': [DUMMY_PYPI]},
    })

    # And a downloader pointing to a temporary index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{'index': index})

    # When I find the link
    link = finder.handle('tests', {'requirement': 'gherkin (== 0.1.0)'})

    # And When I try to retrieve a package from it
    downloader.handle('main', link)

    # Then I see that the package was downloaded correctly to the storage
    index.get('gherkin==0.1.0').should_not.be.empty

    # And I cleanup the mess
    index.delete()


def test_finder_hyphen_on_pkg_name():
    "Finder#handle() should be able to locate packages with hyphens on the name"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': [DUMMY_PYPI]},
    })

    # When I try to retrieve a package from it
    url = finder.handle('main', {'requirement': 'fake-pkg (0.0.0)'})

    # Then I see that the package was downloaded correctly to the storage
    url.should.equal({
        'requirement': 'fake-pkg (0.0.0)',
        'locator_url': DUMMY_PYPI,
        'url': DUMMY_PYPI_URL('fake-pkg/fake-pkg-0.0.0.tar.gz'),
    })


def test_finder_underscore_on_pkg_name():
    "Finder#handle() should be able to locate packages with underscore on the name"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': [DUMMY_PYPI]},
    })

    # When I try to retrieve a package from it
    url = finder.handle('main', {'requirement': 'fake_pkg (0.0.0)'})

    # Then I see that the package was downloaded correctly to the storage
    url.should.equal({
        'requirement': 'fake_pkg (0.0.0)',
        'locator_url': DUMMY_PYPI,
        'url': DUMMY_PYPI_URL('fake-pkg/fake-pkg-0.0.0.tar.gz'),
    })


def test_finder_not_found():
    "Finder#handle() should raise `ReportableError` if it can't find the package"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': [DUMMY_PYPI]},
    })

    # When I try to retrieve a package from it
    finder.handle.when.called_with(
        'main', {'requirement': 'donotexist==0.1.0'}).should.throw(ReportableError,
            'Requirement `donotexist==0.1.0\' not found')


def test_curd_package():
    "It should possible to convert regular packages to wheels"

    # Given that I have a storage containing a package
    index = Index(FIXTURE('storage1'))
    index.scan()

    # And a curdling using that index
    curdling = Curdler(**{'index': index})

    # When I request a curd to be created
    package = curdling.handle('main', {
        'tarball': index.get('gherkin==0.1.0;~whl'),
        'requirement': 'gherkin (0.1.0)',
    })

    # Then I see it's a wheel package.
    package['wheel'].should.match(
        FIXTURE('storage1/gherkin-0.1.0-py\d+-none-any.whl'))

    # And that it's present in the index
    package = index.get('gherkin==0.1.0;whl')

    # And that the file was created in the file system
    os.path.exists(package).should.be.true

    # And I delete the file
    os.unlink(package)


def test_install_package():
    "It should possible to install wheels"

    # Given that I have an installer configured with a loaded index
    index = Index(FIXTURE('storage2'))
    index.scan()
    installer = Installer(**{'index': index})

    # When I request a curd to be created
    installer.handle('main', {
        'requirement': 'gherkin==0.1.0',
        'wheel': index.get('gherkin==0.1.0;whl'),
    })

    # Then I see that the package was installed
    Database.check_installed('gherkin==0.1.0').should.be.true

    # And I uninstall the package
    Database.uninstall('gherkin==0.1.0')



def test_retrieve_and_build():
    "Install#retrieve_and_build() "

    # Given that I have an installer with a working index
    index = Index(FIXTURE('tmp'))
    installer = Install(**{
        'conf': {
            'index': index,
            'pypi_urls': [DUMMY_PYPI]
        },
    })
    installer.pipeline()

    # And I handle the installer with a requirement
    installer.queue('tests', requirement='gherkin')

    # And start the installer
    installer.start()

    # When I run the retrieve and build loop
    packages = installer.retrieve_and_build()

    # Than I see that the package was retrieved
    packages.should.equal(set(['gherkin']))

    # And I clean the mess
    index.delete()

########NEW FILE########
__FILENAME__ = test_wheel
# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from curdling.wheel import Wheel
from . import FIXTURE


def test_read_basic_fields():
    "Wheel.from_file() Should parse a `.whl` archive"

    # Given the wheel present in our file system
    wheel_file = FIXTURE('storage2/gherkin-0.1.0-py27-none-any.whl')

    # When I parse it
    wheel = Wheel.from_file(wheel_file)

    # Then I see that the wheel file was successfuly read
    wheel.distribution.should.equal('gherkin')
    wheel.version.should.equal('0.1.0')
    wheel.build.should.be.none
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_read_basic_fields():
    """Wheel.from_file() Should parse the WHEEL file of the .whl archive

    The information inside of this file will be used as data source
    for the `Wheel.info()` method.
    """

    # Given the wheel present in our file system
    wheel_file = FIXTURE('storage2/gherkin-0.1.0-py27-none-any.whl')

    # When I parse it
    wheel = Wheel.from_file(wheel_file)

    # Then I see that
    # And then I also see that the file WHEEL was correctly parsed
    wheel.info().should.equal({
        'Wheel-Version': '1.0',
        'Generator': 'bdist_wheel (0.21.0)',
        'Root-Is-Purelib': 'true',
        'Tag': ['py27-none-any'],
    })

    # # Then I see it should contain the follo
    # files = {
    #     '/', ['blah.py']
    #     'dist-info': [
    #         'DESCRIPTION.rst',
    #         'pydist.json',
    #         'top_level.txt',
    #         'WHEEL',
    #         'METADATA',
    #         'RECORD',
    #     ]
    # }

########NEW FILE########
__FILENAME__ = test_command_install
from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock
from nose.tools import nottest

from curdling.exceptions import VersionConflict, ReportableError
from curdling.index import Index, PackageNotFound
from curdling.install import Install
from curdling import install


def test_decorator_only():
    "install@only() should not call the decorated function if `field` is set"

    callback = Mock(__name__=str('callback'))
    decorated = install.only(callback, 'tarball')

    decorated('tests', tarball='tarball.tar.gz')
    callback.assert_called_once_with(
        'tests', tarball='tarball.tar.gz')

    callback2 = Mock(__name__=str('callback2'))
    decorated = install.only(callback2, 'tarball')

    decorated('tests', directory='/path/to/a/package')
    callback2.called.should.be.false


def test_install_feed_when_theres_a_tarball_cached():
    "Install#feed() Should route the requirements that already have a tarball to the curdler"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.pipeline()
    env.downloader.queue = Mock()
    env.installer.queue = Mock()
    env.curdler.queue = Mock()

    # When I request an installation of a package
    env.handle('main', requirement='gherkin==0.1.0')

    # # Then I see that, since the package was not installed, the locall cache
    # # was queried and returned the right entry
    # env.database.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.curdler.queue.assert_called_once_with(
        'main',
        requirement='gherkin==0.1.0',
        tarball='storage1/gherkin-0.1.0.tar.gz')

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false
    env.installer.queue.called.should.be.false


def test_install_feed_when_theres_a_wheel_cached():
    "Install#feed() Should route the requirements that already have a wheel to the dependencer"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.pipeline()
    env.downloader.queue = Mock()
    env.dependencer.queue = Mock()
    env.curdler.queue = Mock()

    # When I request an installation of a package
    env.handle('tests', requirement='gherkin==0.1.0')

    # # Then I see that, since the package was not installed, the locall cache
    # # was queried and returned the right entry
    # env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.dependencer.queue.assert_called_once_with(
        'tests',
        requirement='gherkin==0.1.0',
        wheel='storage1/gherkin-0.1.0-py27-none-any.whl',
    )

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false


def test_handle_requirement_finder():
    "Install#handle() should route all queued requirements to the finder"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I mock some service end-points
    install.finder.queue = Mock()

    # When I request the installation of a new requirement
    install.handle('tests', requirement='curdling')

    # Then I see the finder received a request
    install.finder.queue.assert_called_once_with(
        'tests', requirement='curdling')


def test_handle_link_download():
    "Install#handle() should route all queued links to the downloader"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I mock some service end-points
    install.downloader.queue = Mock()

    # When I request the installation of a new requirement
    install.handle('tests', requirement='http://srv/pkgs/curdling-0.1.tar.gz')

    # I see that the downloader received a request
    install.downloader.queue.assert_called_once_with(
        'tests',
        requirement='http://srv/pkgs/curdling-0.1.tar.gz',
        url='http://srv/pkgs/curdling-0.1.tar.gz')


def test_handle_filter_compatible_requirements():
    "Install#handle() Should skip requirements that already have compatible matches in the mapping"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the finder service end-point
    install.finder.queue = Mock()
    install.pipeline()

    # When I handle the installer with a requirement *without dependencies*
    install.handle('tests', requirement='package (1.0)')

    # And I handle the installer with another requirement for the same
    # package above, requested by `something-else`
    install.handle('tests', requirement='package (3.0)', dependency_of='something-else')

    # Then I see that the requirement without any dependencies
    # (primary requirement) is the chosen one
    install.finder.queue.assert_called_once_with('tests', requirement='package (1.0)')
    install.mapping.requirements.should.equal(set(['package (1.0)']))


def test_handle_filter_dups():
    "Install#handle() Should skip duplicated requirements"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the finder service end-point
    install.finder.queue = Mock()
    install.pipeline()

    # Handle the installer with the requirement
    install.handle('tests', requirement='package')
    install.finder.queue.assert_called_once_with('tests', requirement='package')
    install.mapping.requirements.should.equal(set(['package']))

    # When I fire the finder.finished() signal with proper data
    install.handle('tests', requirement='package')

    # Then I see the handle function just skipped this repeated requirement
    install.finder.queue.assert_called_once_with('tests', requirement='package')
    install.mapping.requirements.should.equal(set(['package']))


def test_handle_filter_blacklisted_packages():
    "Install#handle() Should skip blacklisted package names"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the finder service end-point
    install.finder.queue = Mock()
    install.pipeline()

    # When I handle the installer with the requirement
    install.handle('tests', requirement='setuptools')

    # Then I see it was just skipped
    install.finder.queue.called.should.be.false


def test_pipeline_update_mapping_stats():
    "Install#pipeline() Should update the Install#mapping#stats"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(return_value={
        'requirement': 'pkg',
        'url': 'pkg.tar.gz',
    })

    # When I handle the installer with a requirement
    install.handle('tests', requirement='pkg')
    install.finder.queue(None)
    install.finder._worker()

    install.mapping.count('finder').should.equal(1)


def test_pipeline_update_mapping_errors():
    "Install#pipeline() Should update Install#mapping#errors whenever an error occurs"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(side_effect=Exception('P0wned!'))

    # When I handle the installer with a requirement
    install.handle('tests', requirement='pkg (0.1)')
    install.finder.queue(None)
    install.finder._worker()

    install.mapping.errors.should.have.length_of(1)
    str(install.mapping.errors['pkg']['pkg (0.1)']['exception']).should.equal('P0wned!')


def test_pipeline_update_mapping_wheels():
    "Install#pipeline() Should update the list Install#mapping#wheels every time we process a dependency"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # When the dependencer runs
    install.dependencer.emit(
        'finished',             # signal name
        'tests',                # requester
        requirement='pkg (0.1)',
        wheel='pkg.whl')

    # Than I see that the `Install.mapping.wheels` property was updated
    # properly
    install.mapping.wheels.should.equal({
        'pkg (0.1)': 'pkg.whl',
    })


def test_pipeline_finder_found_downloader():
    "Install#pipeline() should route the finder output to the downloader"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the downloader service end-point
    install.finder.queue = Mock(__name__=str('queue'))
    install.downloader.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Handle the installer with the requirement
    install.finder.queue = Mock()
    install.handle('tests', requirement='package')
    install.handle('tests', requirement='package (0.0.1)')

    # When I fire the finder.finished() signal with proper data
    install.finder.emit('finished',
        'finder',
        requirement='package',
        url='http://srv.com/package.tar.gz',
        locator_url='http://usr:passwd@srv.com/simple',
    )

    # And manually add the first package to the `processing_packages` set,
    # because we mock `queue`, the component that actually does that for us.
    install.downloader.processing_packages.add('package.tar.gz')

    # And When I fire another finished signal with a different requirement but
    # the same url
    install.finder.emit('finished',
        'finder',
        requirement='package (0.0.1)',
        url='http://another.srv.com/package.tar.gz',
        locator_url='http://srv.com/simple',
    )

    # Then I see that the downloader received a single request. The second one
    # was duplicated
    install.downloader.queue.assert_called_once_with(
        'finder',
        requirement='package',
        url='http://srv.com/package.tar.gz',
        locator_url='http://usr:passwd@srv.com/simple',
    )


def test_pipeline_downloader_tarzip_curdler():
    "Install#pipeline() should route all the tar/zip files to the curdler"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.curdler.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Handle the installer with the requirement
    install.finder.queue = Mock()
    install.handle('tests', requirement='curdling')

    # When I fire the download.finished() signal with proper data
    install.downloader.emit('finished',
        'downloader',
        requirement='curdling',
        tarball='curdling-0.1.tar.gz')

    # Than I see that the curdler received a request
    install.curdler.queue.assert_called_once_with(
        'downloader',
        requirement='curdling',
        tarball='curdling-0.1.tar.gz')


def test_pipeline_downloader_wheel_dependencer():
    "Install#pipeline() should route all the wheel files to the dependencer"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.dependencer.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Handle the installer with the requirement
    install.finder.queue = Mock()
    install.handle('tests', requirement='curdling')

    # When I fire the download.finished() signal with proper data
    install.downloader.emit('finished',
        'downloader',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')

    # Than I see that the curdler received a request
    install.dependencer.queue.assert_called_once_with(
        'downloader',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')


def test_pipeline_curdler_wheel_dependencer():
    "Install#pipeline() should route all the wheel files from the curdler to the dependencer"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.dependencer.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Handle the installer with the requirement
    install.finder.queue = Mock()
    install.handle('tests', requirement='curdling')

    # When I fire the curdler.finished() signal with proper data
    install.curdler.emit('finished',
        'curdler',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')

    # Than I see that the dependencer received a request
    install.dependencer.queue.assert_called_once_with(
        'curdler',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')


def test_pipeline_dependencer_queue():
    "Install#pipeline() should route all the requirements from the dependencer to Install#handle()"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.queue = Mock(__name__=str('handle'))
    install.pipeline()

    # When I fire the download.finished() signal with proper data
    install.dependencer.emit('dependency_found', 'dependencer', requirement='curdling (0.3.0)')

    # Than I see that the curdler received a request
    install.queue.assert_called_once_with(
        'dependencer', requirement='curdling (0.3.0)')



def test_load_installer():
    "Install#load_installer() should load all the wheels collected in Install#wheels and add them to the installer queue"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # And a few packages inside of the `Install.wheels` attribute
    install.mapping.requirements = set(['package (0.1)', 'another-package (0.1)'])
    install.mapping.wheels = {
        'package (0.1)': 'package-0.1-py27-none-any.whl',
        'another-package (0.1)': 'another_package-0.1-py27-none-any.whl',
    }

    # When I load the installer
    names, errors = install.load_installer()

    # Then I see no errors
    errors.should.be.empty

    # And Then I see the list of all successfully processed packages
    names.should.equal(set(['package', 'another-package']))

    # And Then I see that the installer should be loaded will all the
    # requested packages; This nasty `sorted` call is here to make it
    # work on python3. The order of the call list I build manually to
    # compare doesn't match the order of `call_args_list` from our
    # mock on py3 :/
    sorted(install.installer.queue.call_args_list, key=lambda i: i[1]['wheel']).should.equal([
        call('main',
             wheel='another_package-0.1-py27-none-any.whl',
             requirement='another-package (0.1)'),
        call('main',
             wheel='package-0.1-py27-none-any.whl',
             requirement='package (0.1)'),
    ])


def test_load_installer_handle_version_conflicts():
    "Install#load_installer() should return conflicts in all requirements being installed"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # And two conflicting packages requested
    install.mapping.requirements = set(['package (0.1)', 'package (0.2)'])
    install.mapping.wheels = {
        'package (0.1)': 'package-0.1-py27-none-any.whl',
        'package (0.2)': 'package-0.2-py27-none-any.whl',
    }

    # And I know it is a corner case for non-primary packages
    install.mapping.dependencies = {
        'package (0.1)': ['blah'],
        'package (0.2)': ['bleh'],
    }

    # When I load the installer
    names, errors = install.load_installer()

    # Then I see the list of all successfully processed packages
    names.should.equal(set(['package']))

    # And Then I see that the error list was filled properly
    errors.should.have.length_of(1)
    errors.should.have.key('package').with_value.being.a(dict)
    errors['package'].should.have.length_of(2)

    errors['package']['package (0.1)']['dependency_of'].should.equal(['blah'])
    errors['package']['package (0.1)']['exception'].should.be.a(VersionConflict)
    str(errors['package']['package (0.1)']['exception']).should.equal(
        'Requirement: package (0.2, 0.1), Available versions: 0.2, 0.1')

    errors['package']['package (0.2)']['dependency_of'].should.equal(['bleh'])
    errors['package']['package (0.2)']['exception'].should.be.a(VersionConflict)
    str(errors['package']['package (0.2)']['exception']).should.equal(
        'Requirement: package (0.2, 0.1), Available versions: 0.2, 0.1')


def test_load_installer_forward_errors():
    "Install#load_installer() Should forward errors from other services when `installable_packages` != `initial_requirements`"

    # Given that I have the install command with an empty index
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I handle the installer with a requirement
    install.queue('tests', requirement='package')

    # And I cause an error in the download worker
    install.downloader.handle = Mock(side_effect=Exception('Beep-Bop'))

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # When I try to retrieve and build all the requirements
    install.start()
    install.retrieve_and_build()

    # And When I load the installer
    names, errors = install.load_installer()

    # Then I see the list of all successfully processed packages
    names.should.be.empty

    # And Then I see that the error list was filled properly
    errors.should.have.length_of(1)
    errors.should.have.key('package').with_value.being.a(dict)
    errors['package'].should.have.length_of(1)

    errors['package']['package']['dependency_of'].should.equal([None])
    errors['package']['package']['exception'].should.be.a(ReportableError)
    str(errors['package']['package']['exception']).should.equal(
        'Requirement `package\' not found')

########NEW FILE########
__FILENAME__ = test_database
from __future__ import absolute_import, print_function, unicode_literals
from mock import patch, Mock
from curdling.database import Database


@patch('curdling.database.DistributionPath')
def test_check_installed(DistributionPath):
    "It should be possible to check if a certain package is currently installed"

    DistributionPath.return_value.get_distribution.return_value = Mock()
    Database.check_installed('gherkin==0.1.0').should.be.true

    DistributionPath.return_value.get_distribution.return_value = None
    Database.check_installed('gherkin==0.1.0').should.be.false

########NEW FILE########
__FILENAME__ = test_freeze
# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from curdling import freeze
from mock import patch, Mock


def test_find_imported_modules():
    "freeze.find_imported_modules() Should find all the imported modules in a string with Python code"

    # Given the following snipet
    code = '''
import curdling

def blah(): pass

import math

print(curdling)
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code
    names.should.equal(['curdling', 'math'])


def test_find_imported_modules2():
    "freeze.find_imported_modules() Should also find imports declared with 'from x import y' syntax"

    # Given the following snipet
    code = '''
from PIL import Image

def blah(): pass

import functools

print(curdling)
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code
    names.should.equal(['PIL', 'functools'])


def test_find_imported_modules4():
    "freeze.find_imported_modules() Should filter the module path when it has more than one level"

    # Given the following snipet
    code = '''
from .relative import stuff
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code, skipping the local modules (.)
    names.should.equal([])


def test_find_imported_modules3():
    "freeze.find_imported_modules() Should skip any local imports (from . import x)"

    # Given the following snipet
    code = '''
from . import Image
import functools
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code, skipping the local modules (.)
    names.should.equal(['functools'])


@patch('curdling.freeze.imp')
@patch('curdling.freeze.sys')
def test_get_module_path(sys, imp):
    "freeze.get_module_path() Should return the file path of a module without importing it"

    sys.path = ['/u/l/p/site-packages']
    imp.find_module.return_value = ['', '/u/l/p/site-packages/sure']

    # Given a module name
    module = 'sure'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('sure')


@patch('curdling.freeze.imp')
@patch('curdling.freeze.sys')
def test_get_module_path2(sys, imp):
    "freeze.get_module_path() Should return the file path without the .py[cO] extension"

    sys.path = ['/u/l/p/site-packages']
    imp.find_module.return_value = ['', '/u/l/p/site-packages/mock.py']

    # Given a module name
    module = 'mock'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('mock')


@patch('curdling.freeze.DistributionPath')
def test_get_distribution_from_source_file(DistributionPath):
    "freeze.get_distribution_from_source_file(file_path) Should return the Distribution that contains `file_path`"

    # Given a path for a package
    path = 'sure/__init__.pyc'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see that the function tried to use the module name as the
    # package name.
    DistributionPath.return_value.get_distribution.assert_called_once_with(
        'sure',
    )


@patch('curdling.freeze.DistributionPath')
def test_get_distribution_from_source_file_file_path_being_a_directory(DistributionPath):
    "freeze.get_distribution_from_source_file(file_path) Should support receiving relative directories in `file_path`"

    # Given a path for a package
    path = 'sure'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see that the function tried to use the module name as the
    # package name.
    DistributionPath.return_value.get_distribution.assert_called_once_with(
        'sure',
    )


@patch('curdling.freeze.get_module_path', Mock())
@patch('curdling.freeze.get_distribution_from_source_file')
def test_get_requirements(get_distribution_from_source_file):
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from distlib import util

print(util.in_venv())
'''

    # And a fake distribution
    distribution = Mock()
    distribution.name = 'distlib'
    distribution.version = '0.1.2'
    get_distribution_from_source_file.return_value = distribution

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['distlib==0.1.2'])

########NEW FILE########
__FILENAME__ = test_index
# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from curdling.index import Index, PackageNotFound
from mock import patch
import os


@patch('curdling.index.os')
def test_index_ensure_path(patched_os):
    "Test utility method Index.ensure_path()"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that doesn't seem
    # to exist, it should try to create the directory for the resource
    patched_os.path.isdir.return_value = False
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.assert_called_once_with('path/to/my')


@patch('curdling.index.os')
def test_index_ensure_path_for_existing_dirs(patched_os):
    "Test utility method Index.ensure_path() for existing directories"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that exists to
    # exists, it *SHOULD NOT* try to create the directory
    patched_os.path.isdir.return_value = True
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.called.should.be.false


def test_index_feed_backend():
    "It should be possible to save package paths granularly"

    # Given the following index
    index = Index('')

    # When I index a couple files
    index.index('http://localhost:800/p/gherkin-0.1.0-py27-none-any.whl')
    index.index('gherkin-0.1.0.tar.gz')
    index.index('Gherkin-0.1.5.tar.gz')  # I know, weird right?
    index.index('a/weird/dir/gherkin-0.2.0.tar.gz')
    index.index('package.name-0.1.0.tar.gz')

    # Then I see that the backend structure looks right
    dict(index.storage).should.equal({
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'Gherkin-0.1.5.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0-py27-none-any.whl',
                'gherkin-0.1.0.tar.gz',
            ],
        },
        'package.name': {
            '0.1.0': [
                'package.name-0.1.0.tar.gz',
            ]
        }
    })


def test_index_get():
    "It should be possible to search for packages using different criterias"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.1': [
                'gherkin-0.1.1.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0.tar.gz',
                'gherkin-0.1.0-py27-none-any.whl',
            ],
        }
    }

    # Let's do some random assertions

    # No version: Always brings the newest
    index.get('gherkin').should.equal('gherkin-0.2.0.tar.gz')

    # With a range of versions: Always brings the newest
    index.get('gherkin (> 0.1.0)').should.equal('gherkin-0.2.0.tar.gz')

    # With a handful of version specs: Find the matching version and prefer whl
    index.get('gherkin (>= 0.1.0, < 0.1.5, != 0.1.1)').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version: Always prefers the wheel
    index.get('gherkin (== 0.1.0, <= 0.2.0)').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version and format: Prefers anything but `whl'
    index.get('gherkin (== 0.1.0);~whl').should.equal('gherkin-0.1.0.tar.gz')

    # With version range and no format: Finds the highest version with the :)
    index.get.when.called_with('gherkin (== 0.1.1);whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (0.1.1) (whl)"))

    # With version and a format that is not available: Blows up! :)
    index.get.when.called_with('gherkin (== 0.1.1);whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (0.1.1) (whl)"))

    # With a version we simply don't have: Blows up! :)
    index.get.when.called_with('gherkin (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (0.2.1)"))

    # With a package we simply don't have: Blows up! :)
    index.get.when.called_with('nonexisting (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "nonexisting (0.2.1)"))

    # Case insensitive
    index.get('Gherkin').should.equal('gherkin-0.2.0.tar.gz')



def test_index_get_corner_case_pkg_name():
    "It should be possible to search for packages that contain `_` in their name"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'python-gherkin': {
            '0.1.0': [
                'python_gherkin-0.1.0.tar.gz',
            ]
        }
     }

    index.get('python-gherkin==0.1.0;~whl').should.equal('python_gherkin-0.1.0.tar.gz')

########NEW FILE########
__FILENAME__ = test_mapping
from __future__ import absolute_import, print_function, unicode_literals
from curdling.mapping import Mapping
from curdling import exceptions


def test_filed_packages():
    """Mapping#filed_packages() should return all packages requested based on all requirements we have.

    It will retrieve a unique list of packages, even when the requirement is
    filed more than once.
    """
    # Given that I have a mapping with a few repeated and unique requirements
    mapping = Mapping()
    mapping.requirements.add('sure (1.2.1)')
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I list the filed packages
    packages = sorted(mapping.filed_packages())

    # I see that a list with the all package names was returned without
    # duplications
    packages.should.equal(['forbiddenfruit', 'sure'])


def test_get_requirements_by_package_name():
    "Mapping#get_requirements_by_package_name() Should return a list of requirements that match a given package name"

    # Given that I have a mapping with some repeated requirements
    mapping = Mapping()
    mapping.requirements.add('sure (1.2.1)')
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I filter by the package name 'forbiddenfruit'
    sorted(mapping.get_requirements_by_package_name('forbiddenfruit')).should.equal([
        'forbiddenfruit (0.1.1)',
        'forbiddenfruit (>= 0.0.5, < 0.0.7)',
    ])


def test_available_versions():
    "Mapping#available_versions() should list versions of all wheels for a certain package"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()

    # 0.1.1
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.wheels['forbiddenfruit (0.1.1)'] = 'forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.6
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')
    mapping.wheels['forbiddenfruit (>= 0.0.5, < 0.0.7)'] = 'forbiddenfruit-0.0.6-cp27-none-macosx_10_8_x86_64.whl'

    # 0.1.1; repeated
    mapping.requirements.add('forbiddenfruit (>= 0.1.0, < 2.0)')
    mapping.wheels['forbiddenfruit (>= 0.1.0, < 2.0)'] = 'forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.9
    mapping.requirements.add('forbiddenfruit (<= 0.0.9)')
    mapping.wheels['forbiddenfruit (<= 0.0.9)'] = 'forbiddenfruit-0.0.9-cp27-none-macosx_10_8_x86_64.whl'

    # And I add another random package to the maestrro
    mapping.requirements.add('sure')

    # When I list all the available versions of forbidden fruit; Then I see it
    # found all the wheels related to that package. Newest first!
    mapping.available_versions('forbiddenfruit').should.equal(['0.1.1', '0.0.9', '0.0.6'])


def test_matching_versions():
    "Mapping#matching_versions() should list versions requirements compatible with a given version"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()

    # 0.1.1
    mapping.requirements.add('pkg (0.1.1)')
    mapping.wheels['pkg (0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.6
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'

    # 0.1.1; repeated
    mapping.requirements.add('pkg (>= 0.1.0, < 2.0)')
    mapping.wheels['pkg (>= 0.1.0, < 2.0)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.9
    mapping.requirements.add('pkg (<= 0.0.9)')
    mapping.wheels['pkg (<= 0.0.9)'] = 'pkg-0.0.9-cp27-none-macosx_10_8_x86_64.whl'

    # When I query which versions should be listed based on a requirement; Then
    # I see that only the versions that match with the informed requirement
    # were returned (and again, newest first)
    mapping.matching_versions('pkg (>= 0.0.6, <= 0.1.0)').should.equal([
         '0.0.9', '0.0.6',
    ])

def test_matching_versions_with_hyphen():
    "Mapping#matching_versions() Should be aware of hyphens in the version info"

    # Given that I have a mapping that contains a package with hyphens in the
    # version info
    mapping = Mapping()

    # 0.1.1-RC1
    mapping.requirements.add('pkg (0.1.1-RC1)')
    mapping.wheels['pkg (0.1.1-RC1)'] = 'pkg-0.1.1_RC1-cp27-none-macosx_10_8_x86_64.whl'

    # When I filter the matching versions
    mapping.matching_versions('pkg (0.1.1-RC1)').should.equal([
        '0.1.1_RC1',
    ])


def test_was_directly_required():
    """Mapping#was_directly_required() Should be True for requirements required directly by the user

    This method ignores the version of the received requirement and
    looks for previously added requirements with the same package name
    and check each one trying to find any directly required entries.
    """

    # Given that I have a mapping
    mapping = Mapping()

    # And a primary requirement
    mapping.requirements.add('sure (1.2.1)')
    mapping.dependencies['sure (1.2.1)'] = [None]

    # And a secondary requirement
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.dependencies['forbiddenfruit (0.1.1)'] = ['sure (1.2.1)']

    # Then I can confirm I previously added a primary requirement
    mapping.was_directly_required('sure (3.9)').should.be.true

    mapping.was_directly_required('forbiddenfruit (0.1.1)').should.be.false


def test_is_primary_requirement():
    """Mapping#is_primary_requirement() True for requirements directly requested by the user

    Either from the command line or from the requirements file informed through
    the `-r` parameter;

    The `secondary` requirements are all the requirements we install without
    asking the user, IOW, dependencies of the primary requirements.
    """

    # Given that I have a mapping with two requirements filed
    mapping = Mapping()

    mapping.requirements.add('sure (1.2.1)')
    mapping.dependencies['sure (1.2.1)'] = [None]

    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.dependencies['forbiddenfruit (0.1.1)'] = ['sure (1.2.1)']

    # When I test if the above requirements are primary
    mapping.is_primary_requirement('sure (1.2.1)').should.be.true
    mapping.is_primary_requirement('forbiddenfruit (0.1.1)').should.be.false


def test_best_version():
    """Mapping#best_version() Should choose the newest compatible version of a requirement to be installed

    By compatible, I mean that this version will match all the other
    requirements present in the mapping.

    """

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()
    mapping.requirements.add('pkg (<= 0.1.1)')
    mapping.wheels['pkg (<= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    mapping.requirements.add('pkg (>= 0.0.5)')
    mapping.wheels['pkg (>= 0.0.5)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    version, requirement = mapping.best_version('pkg')

    # Then I see that the newest dependency was chosen
    version.should.equal('0.1.1')
    requirement.should.equal('pkg (<= 0.1.1)')


def test_best_version_with_conflicts():
    "Mapping#best_version() Should raise blow up if no version matches all the filed requirements"

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()
    mapping.requirements.add('pkg (>= 0.1.1)')
    mapping.dependencies['pkg (>= 0.1.1)'] = ['blah']
    mapping.wheels['pkg (>= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    # And the second version is older
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.dependencies['pkg (>= 0.0.5, < 0.0.7)'] = ['bleh']
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    mapping.best_version.when.called_with('pkg').should.throw(
        exceptions.VersionConflict,
        'Requirement: pkg (>= 0.1.1, >= 0.0.5, < 0.0.7), '
        'Available versions: 0.1.1, 0.0.6'
    )


def test_best_version_with_explicit_requirement():
    """Mapping#best_version() Should always prioritize versions directly specified by the user

    The other versions might have been added by dependencies. So, to manually
    fix craziness between dependencies of dependencies, the user can just force
    a specific version for a package from the command line or from a
    requirements file informed with the `-r` parameter.
    """

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()

    mapping.requirements.add('pkg (>= 0.1.1)')
    mapping.dependencies['pkg (>= 0.1.1)'] = ['other_pkg (0.1)']
    mapping.wheels['pkg (>= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    # And the second version is older, but has no dependencies
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.dependencies['pkg (>= 0.0.5, < 0.0.7)'] = [None]
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    version = mapping.best_version('pkg', debug=True)

    # Then I see that we retrieved the oldest version, just because the package
    # is not a dependency.
    version.should.equal(('0.0.6', 'pkg (>= 0.0.5, < 0.0.7)'))


def test_best_version_no_strict_requirements_but_strict_version():
    "Mapping#best_version() should still work for requirements without version info"

    # Given that I have a mapping with two requirements
    mapping = Mapping()
    mapping.requirements.add('forbiddenfruit')
    mapping.dependencies['forbiddenfruit'] = ['sure (== 0.2.1)']
    mapping.wheels['forbiddenfruit'] = 'forbiddenfruit-0.1.0-cp27.whl'

    # When I retrieve the best match
    version = mapping.best_version('forbiddenfruit')

    # Then I see that I still got the version number even though my requirement
    # didn't have version info
    version.should.equal(('0.1.0', 'forbiddenfruit'))


def test_best_version_with_no_wheels():
    "Mapping#best_version() Should not take uncompiled packages into account"

    # Given that I have a mapping with a package that was not compiled
    mapping = Mapping()
    mapping.requirements.add('pkg (>= 0.1.1)')
    mapping.dependencies['pkg (>= 0.1.1)'] = ['blah']

    # When I retrieve the best match
    mapping.best_version.when.called_with('pkg').should.throw(
        exceptions.VersionConflict,
        'Requirement: pkg, no available versions were found'
    )

########NEW FILE########
__FILENAME__ = test_services
from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock, ANY, call
from curdling.services.base import Service


def test_service():
    "Service#_worker() should stop when hitting the sentinel"

    # Given the following service
    class MyService(Service):
        pass

    callback = Mock()
    service = MyService()
    service.connect('failed', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('tests')
    service.queue(None)
    service._worker()

    # Then I see that the package is indeed processed but the service dies
    # properly when it receives the sentinel.
    callback.assert_called_once_with('myservice', exception=ANY)

    # And that in the `path` parameter we receive an exception (Unfortunately
    # we can't compare NotImplementedError() instances :(
    str(callback.call_args_list[0][1]['exception']).should.equal(
        'The service subclass should override this method'
    )


def test_service_success():
    "Service#_worker() should execute self#handler() method successfully"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, sender_data):
            return {'package': 'processed-package'}

    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('tests')
    service.queue(None)
    service._worker()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with('myservice', package='processed-package')


def test_service_start_join():
    "Service#join() should hang until the service is finished"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, sender_data):
            return {'package': 'processed-package'}

    # And a callback connected to the 'finished' signal
    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue the package, start and join the service
    service.queue('main')
    service.start()
    service.join()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with('myservice', package='processed-package')


def test_service_call():
    "Service#__call__ should forward the execution parameters to the #handle() method"

    # Given the following service
    class MyService(Service): pass
    instance = MyService()
    instance.handle = Mock()

    # When I call an instance
    instance('service', p1='v1', p2='v2')

    # Then I see the parameters were forwarded correctly
    instance.handle.assert_called_once_with(
        'service', {'p2': 'v2', 'p1': 'v1'})

########NEW FILE########
__FILENAME__ = test_services_curdler
from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling.services import curdler


@patch('curdling.services.curdler.io')
def test_guess_file_type(io):
    "guess_file_type() Should return the format of the archive if such is supported by curdling"

    # Given an archive
    io.open.return_value.__enter__.return_value.read.return_value = \
        io.open.return_value.read.return_value = b"\x1f\x8b\x08"

    # When I try to guess the file type
    file_type = curdler.guess_file_type('pkg.tgz')

    # Then I see that the right file type was found, despite the
    # disguising extension
    file_type.should.equal('gz')


@patch('curdling.services.curdler.io')
def test_guess_file_type_no_matching_type(io):
    "guess_file_type() Should raise UnpackingError if the format is unknown"

    # Given an archive
    with io.open() as patched_io:
        patched_io.read.return_value = b"unsupported format"

        # When I try to guess the file type; Then I see it raises an exception
        curdler.guess_file_type.when.called_with('pkg.tgz').should.throw(
            curdler.UnpackingError, 'Unknown compress format for file pkg.tgz'
        )


@patch('curdling.services.curdler.guess_file_type')
@patch('curdling.services.curdler.zipfile.ZipFile')
def test_unpack(ZipFile, guess_file_type):
    "unpack() Should unpack zip files and return the names inside of the archive"

    # Given a zip package
    guess_file_type.return_value = 'zip'
    ZipFile.return_value.namelist.return_value = ['file.py', 'setup.py']

    # When I try to unpack a file
    open_archive, namelist = curdler.unpack('package.zip')

    # Then I see it returned an open archive
    open_archive.should.equal(ZipFile.return_value)

    # Then I see the right name list being returned
    namelist.should.equal(['file.py', 'setup.py'])


@patch('curdling.services.curdler.guess_file_type')
@patch('curdling.services.curdler.tarfile.open')
def test_unpack_tarball(tarfile_open, guess_file_type):
    "unpack() Should unpack .gz files and return the names inside of the archive"

    # Given a zip package
    guess_file_type.return_value = 'gz'
    file1, file2 = Mock(), Mock()
    file1.name, file2.name = 'file.py', 'setup.py'
    tarfile_open.return_value.getmembers.return_value = [file1, file2]

    # When I try to unpack a file
    open_archive, namelist = curdler.unpack('package.tar.gz')

    # Then I see it returned an open archive
    open_archive.should.equal(tarfile_open.return_value)

    # Then I see the right name list being returned
    namelist.should.equal(['file.py', 'setup.py'])



@patch('curdling.services.curdler.guess_file_type')
def test_unpack_error(guess_file_type):
    "unpack() Should raise `UnpackingError` on unknown files"

    guess_file_type.return_value = None

    # When I try to guess the file type; Then I see it raises an exception
    curdler.unpack.when.called_with('pkg.abc').should.throw(
        curdler.UnpackingError, 'Unknown compress format for file pkg.abc'
    )


def test_find_setup_script():
    "find_setup_script() Should return the setup.py script in the root of an archive's file list"

    # Given the following contents of an archive
    namelist = [
        'pkg-0.1/Makefile',
        'pkg-0.1/README.md',
        'pkg-0.1/setup.py',     # Here's our guy!
        'pkg-0.1/pkg/__init__.py',
        'pkg-0.1/pkg/setup.py',
        'pkg-0.1/pkg/api.py',
    ]

    # When I look for the setup.py script
    script = curdler.find_setup_script(namelist)

    # Then I see that the right script was found
    script.should.equal('pkg-0.1/setup.py')


def test_cant_find_setup_script():
    "find_setup_script() Should raise an exception when there's no setup.py script in namelist"

    # Given the following contents of an archive
    namelist = [
        'pkg-0.1/Makefile',
        'pkg-0.1/README.md',
        'pkg-0.1/pkg/__init__.py',
        'pkg-0.1/pkg/api.py',
    ]

    # When I look for the setup.py script; Then I see it raises an exception
    script = curdler.find_setup_script.when.called_with(namelist).should.throw(
        curdler.NoSetupScriptFound,
        'No setup.py script found'
    )


@patch('curdling.services.curdler.unpack')
def test_get_setup_from_package(unpack):
    "get_setup_from_package() Should unpack a tarball or zip file and return its setup.py script"

    # Given the following name list of a package
    fp = Mock()
    unpack.return_value = fp, ['pkg-0.1/setup.py', 'pkg-0.1/pkg.py']

    # When I try to retrieve the setup script
    setup_py = curdler.get_setup_from_package('I am a package', '/tmp')

    # Then I see that the package was extracted and that the setup
    # script was found
    setup_py.should.equal('/tmp/pkg-0.1/setup.py')



@patch('curdling.services.curdler.os.listdir')
@patch('curdling.services.curdler.execute_command')
def test_run_script(execute_command, listdir):
    "run_setup_script() Should be able to run the setup.py script"

    # Given a patch for `os.listdir` and `execute_command` (see @patch
    # usage in this functions signature)
    listdir.return_value = ['wheel-file']

    # When I run the setup script
    wheel = curdler.run_setup_script("/tmp/pkg/setup.py", 'bdist_wheel', '-h')

    # Then I see that the execute command was called with the right
    # parameters
    execute_command.assert_called_once_with(
        ANY, '-c', ANY, 'bdist_wheel', '-h', cwd='/tmp/pkg')

    # And that the wheel was generated in the right directory
    wheel.should.equal('/tmp/pkg/dist/wheel-file')


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.get_setup_from_package')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service(rmtree, run_setup_script, get_setup_from_package, mkdtemp):
    "Curdler.handle() Should unpack and build packages"

    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # When I execute the service
    service.handle('tests', {
        'requirement': 'pkg',
        'tarball': 'pkg.tar.gz',
    })

    # Then I see that the `setup.py` script was retrieved using the
    # helper `get_setup_from_package()`.
    get_setup_from_package.assert_called_once_with('pkg.tar.gz', destination)

    # And then I see that the `setup.py` script was run
    run_setup_script.assert_called_once_with(
        get_setup_from_package.return_value, 'bdist_wheel')

    # And then I see that the wheel file should indexed
    service.index.from_file.assert_called_once_with(
        run_setup_script.return_value)

    # And then the temporary destination is removed afterwards
    rmtree.assert_called_once_with(destination)


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service_build_directory(rmtree, run_setup_script, mkdtemp):
    
    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # When I execute the service
    service.handle('tests', {
        'requirement': 'pkg',
        'directory': '/tmp/pkg',
    })

    # And then I see that the `setup.py` script was run
    run_setup_script.assert_called_once_with(
        '/tmp/pkg/setup.py', 'bdist_wheel')

    # And then I see that the wheel file should indexed
    service.index.from_file.assert_called_once_with(
        run_setup_script.return_value)

    # And then I see that the temporary destination and the package
    # directory are removed afterwards
    list(rmtree.call_args_list).should.equal([
        call(destination),
        call('/tmp/pkg'),
    ])


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service_error(rmtree, run_setup_script, mkdtemp):

    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # And then I create a problem in the `run_setup_script` to
    # simulate a build error
    run_setup_script.side_effect = Exception('P0wned!!1')

    # When I execute the service; Then I see that the right exception
    # is raised
    service.handle.when.called_with('tests', {
        'requirement': 'pkg',
        'directory': '/tmp/pkg',
    }).should.throw(Exception, 'P0wned!!1')

    # And then I see that the temporary destination and the package
    # directory are removed afterwards
    list(rmtree.call_args_list).should.equal([
        call(destination),
        call('/tmp/pkg'),
    ])

########NEW FILE########
__FILENAME__ = test_services_dependencer
from mock import call, patch, Mock
from curdling.services.dependencer import Dependencer


@patch('curdling.services.dependencer.Wheel')
def test_dependencer(Wheel):
    "Dependencer#handle() should emit the signal dependency_found when scanning a new package"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # And that the package to test the service will have the following
    # dependencies:
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'install': ['forbiddenfruit (0.1.1)'],
        'extras': {},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='sure', wheel='forbiddenfruit-0.1-cp27.whl')
    dependencer.queue(None)
    dependencer._worker()

    # Than I see that the signal was called for the dependency with the right
    # parameters
    callback.assert_called_once_with(
        'dependencer',
        requirement='forbiddenfruit (0.1.1)',
        dependency_of='sure')


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_package_with_no_deps(Wheel):
    "Dependencer#handle() should emit the signal built for packages with no dependencies"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('finished', callback)

    # And that the package to test the service will have no
    # dependencies:
    Wheel.return_value = Mock(metadata=Mock(dependencies={}))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='sure', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Than I see that the signal was called for the dependency with the right
    # parameters
    callback.assert_called_once_with(
        'dependencer',
        requirement='sure',
        wheel='path-to-the-wheel'
    )


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_install_extras(Wheel):
    "Dependencer#handle() Should install extra sets of dependencies"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # When I queue a dependency from an extra section the user didn't
    # request
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'install': ['lxml (>= 2.1)'],
        'extras': {'tests': ['sure (1.2.1)']},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='curdling[tests]', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Then I see no dependencies were actually found, since the extra
    # section doesn't match.
    list(callback.call_args_list).should.equal([
        call('dependencer', requirement=u'lxml (>= 2.1)', dependency_of='curdling[tests]'),
        call('dependencer', requirement=u'sure (1.2.1)', dependency_of='curdling[tests]')
    ])


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_skip_not_required_extras(Wheel):
    "Dependencer#handle() Should skip dependencies from extra sets that the user didn't require"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # When I queue a dependency from an extra section the user didn't
    # request
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'extras': {'development': 'sure'},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='curdling', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Then I see no dependencies were actually found, since the extra
    # section doesn't match.
    callback.called.should.be.false

########NEW FILE########
__FILENAME__ = test_services_downloader
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock, patch, call
from distlib import database

from curdling.exceptions import UnknownURL, TooManyRedirects, ReportableError
from curdling.services import downloader

import urllib3


def test_locators_should_be_comparable():
    "PyPiLocator() and CurdlingLocator() Should be comparable between each other"

    # When I compare locators from the same type with the same URL,
    # they should equal
    downloader.PyPiLocator('url1').should.equal(downloader.PyPiLocator('url1'))
    downloader.PyPiLocator('url1').should_not.equal(downloader.PyPiLocator('url2'))

    # And the same is true for the CurdlingLocator class
    downloader.CurdlingLocator('url1').should.equal(downloader.CurdlingLocator('url1'))
    downloader.CurdlingLocator('url1').should_not.equal(downloader.CurdlingLocator('url2'))

    # When I compare locators from different types; they should not equal
    downloader.CurdlingLocator('url1').should_not.equal(downloader.PyPiLocator('url1'))


def test_get_locator():
    "get_locator() Should an AggregatingLocator fed with all curd and pypi locators informed in `conf`"

    # Given the following configuration
    conf = {
        'pypi_urls': ['http://pypi.py.o/simple'],
        'curdling_urls': ['http://curd.clarete.li', 'http://curd.falcao.it'],
    }

    # When I try to retrieve a locator
    locator = downloader.get_locator(conf)

    # Than I see all the above locator URLs present inside of the main
    # one
    locator.should.be.a(downloader.AggregatingLocator)
    locator.locators.should.equal((
        downloader.CurdlingLocator('http://curd.clarete.li'),
        downloader.CurdlingLocator('http://curd.falcao.it'),
        downloader.PyPiLocator('http://pypi.py.o/simple'),
    ))


def test_get_opener():
    "get_opener() Should return an HTTP retriever class from urllib3"

    # When I need a regular opener; Then I should get a Pool Manager
    downloader.get_opener().should.be.a(urllib3.PoolManager)


@patch('os.getenv')
def test_get_opener_with_proxy(getenv):
    "get_opener() Should return a Proxy Manager from urllib3 when `http_proxy` is available"

    # Given the following proxy server set in the http_proxy variable
    getenv.return_value = 'http://user:pwd@srv.prx:8123'

    # When I request the opener
    opener = downloader.get_opener()

    # Then I get a Proxy Manager
    opener.should.be.a(urllib3.ProxyManager)

    # And I check that the proxy URL is right
    '{0}://{1}@{2}:{3}'.format(*tuple(opener.proxy)).should.equal('http://user:pwd@srv.prx:8123')

    # And that the authentication header is present
    opener.proxy_headers.should.equal(
        {'proxy-authorization': 'Basic dXNlcjpwd2Q='})


class TestPyPiLocator(downloader.PyPiLocator):
    def __init__(self, *args, **kw):
        super(TestPyPiLocator, self).__init__(*args, **kw)
        self.opener = Mock()


@patch('curdling.services.downloader.distlib')
def test_find_packages(distlib):
    ("find_packages should use the scheme from the "
     "locator to match the best result")
    # Background
    # The scheme is mocked
    scheme = distlib.version.get_scheme.return_value
    # As well as the matcher
    matcher = scheme.matcher.return_value
    # And a version class
    version_class = matcher.version_class.return_value

    # Given a locator
    locator = Mock()

    # And a requirement
    requirement = Mock()

    # And a versions dictionary
    distribution = Mock()
    versions = {
        '1.0': distribution
    }

    # When I invoke find_packages
    result = downloader.find_packages(locator, requirement, versions)
    # Then the result should be the expected distribution
    result.should.equal(distribution)
    # And the method calls should be correct (sorry for this sad test,
    # I'm still getting to know the codebase)
    matcher.match.assert_called_once_with(version_class)
    scheme.matcher.assert_called_once_with(requirement.requirement)
    distlib.version.get_scheme.assert_called_once_with(locator.scheme)


def test_update_url_credentials():
    "update_url_credentials() should update URL2 using auth info from URL1"

    # Given that I have a URL with authentication info
    url1 = 'http://user:almost-safe-password@domain.com/path/to/resource.html'

    # And another URL without auth info
    url2 = 'http://domain.com/another/path/to/a/cooler/resource.html'

    # When I update the second one based on the first one
    final_url = downloader.update_url_credentials(url1, url2)

    # Then I see that the final URL version is just the second URL with the auth
    # info from the first one
    final_url.should.equal(
        'http://user:almost-safe-password@domain.com/another/path/to/a/cooler/resource.html')


def test_update_url_credentials_not_from_the_same_server():
    "update_url_credentials() Should just use the second URL if the URLS are pointing to different services"

    # Given that I have a URL with authentication info from domain1.com
    url1 = 'http://user:passwd@domain1.com/resource1.html'

    # And another URL without auth info from domain2.com
    url2 = 'http://domain2.com/resource2.html'

    # When I update the second one based on the first one
    final_url = downloader.update_url_credentials(url1, url2)

    # Then I see that the final URL is just a copy of the second URL
    final_url.should.equal(url2)


@patch('curdling.services.downloader.util')
def test_pool_retrieve_no_redirect(util):
    ("http_retrieve() Should retrieve a URL and return a tuple "
     "containing the response and the final URL of the retrieved resource")

    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {'foo': 'bar'}

    # Given a mocked response
    pool = Mock()
    pool.request.return_value = Mock(headers={})

    # When I retrieve a URL
    _, url = downloader.http_retrieve(pool, 'http://github.com')

    # Then the url should be the same as requested
    url.should.equal('http://github.com')
    util.get_auth_info_from_url.assert_called_once_with('http://github.com')

    # And that the request should be executed with the correct
    # parameters
    pool.request.assert_called_once_with(
        'GET', 'http://github.com',
        headers={'foo': 'bar'},
        preload_content=False,
        redirect=False,
    )


@patch('curdling.services.downloader.util')
def test_http_retrieve(util):
    "http_retrieve() Should follow redirects and return the final URL"

    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {}

    # Given a mocked response
    pool = Mock()
    pool.request.side_effect = [
        Mock(headers={'location': 'http://bitbucket.com'}),
        Mock(headers={}),
    ]

    # When I retrieve a URL
    response, url = downloader.http_retrieve(pool, 'http://github.com')

    # Then the url should be the output of the redirect
    url.should.equal('http://bitbucket.com')

    # Even though we originally requested a different one
    list(pool.request.call_args_list).should.equal([
        call('GET', 'http://github.com', redirect=False, headers={}, preload_content=False),
        call('GET', 'http://bitbucket.com', redirect=False, headers={}, preload_content=False),
    ])


@patch('curdling.services.downloader.util')
def test_http_retrieve_max_redirects(util):
    "http_retrieve() Should limit the number of redirects"

    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {}

    # Given a mocked response that *always* returns a resource that
    # redirects to a different URL
    pool = Mock()
    pool.request.return_value = Mock(headers={'location': 'http://see-the-other-side.com'})

    # When I retrieve a URL with an infinite redirect flow; I see that
    # the downloader notices that and raises the proper exception
    downloader.http_retrieve.when.called_with(pool, 'http://see-the-other-side.com').should.throw(
        TooManyRedirects, 'Too many redirects'
    )

    # And that the limit of redirects is fixed manually to
    pool.request.call_args_list.should.have.length_of(20)


@patch('curdling.services.downloader.util')
def test_http_retrieve_relative_location(util):
    "http_retrieve() Should deal with relative paths on Location"

    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {}

    # Given a mocked response that returns a relative Location URL
    pool = Mock()
    pool.request.side_effect = [
        Mock(headers={'location': '/a/relative/url'}),
        Mock(headers={}),
    ]

    # When I check that
    downloader.http_retrieve(pool, 'http://bitbucket.com/')

    list(pool.request.call_args_list).should.equal([
        call('GET', 'http://bitbucket.com/', headers={}, preload_content=False, redirect=False),
        call('GET', 'http://bitbucket.com/a/relative/url', headers={}, preload_content=False, redirect=False),
    ])


@patch('curdling.services.downloader.util')
@patch('curdling.services.downloader.find_packages')
def test_aggregating_locator_locate(find_packages, util):
    ("AggregatingLocator#locate should return the first package "
     "that matches the given version")
    # Background:

    # parse_requirement is mocked and will return a mocked pkg
    pkg = util.parse_requirement.return_value

    # find_packages will return a package right away
    find_packages.return_value = 'the awesome "foo" package :)'


    # Specification:

    # Given a mocked locator
    locator = Mock()

    # And that the AggregatingLocator has a list containing that one locator
    class TestLocator(downloader.AggregatingLocator):
        def __init__(self):
            self.locators = [locator]

    # And an instance of AggregatingLocator
    instance = TestLocator()

    # When I try to locate a package with certain requirement
    found = instance.locate("foo==1.1.1")

    # Then it should be the expected package
    found.should.equal('the awesome "foo" package :)')


def test_pypilocator_get_project():
    ("PyPiLocator#_get_project should fetch based on the base_url")
    # Given an instance of PyPiLocator that mocks out the _fetch method
    instance = TestPyPiLocator("http://github.com")
    instance._fetch = Mock()

    # When _get_project gets called
    response = instance._get_project("forbiddenfruit")

    # Then it should have called _fetch
    instance._fetch.assert_called_once_with(
        u'http://github.com/forbiddenfruit/',
        u'forbiddenfruit',
    )


def test_visit_link_when_platform_dependent():
    ("PyPiLocator#_visit_link() should return (None, None) "
     "if link is platform dependent")

    # Given an instance of PyPiLocator
    instance = TestPyPiLocator("http://github.com")
    # And that calling _is_platform_dependent will return True
    instance._is_platform_dependent = Mock(return_value=True)

    # When I call _visit_link
    result = instance._visit_link("github", "some-link")

    # Then it should be a tuple with 2 `None` items
    result.should.equal((None, None))


def test_visit_link_when_not_platform_dependent():
    ("PyPiLocator#_visit_link() should return ('package-name', 'version') "
     "when link is not platform dependent")

    # Given an instance of PyPiLocator that mocks out the expected
    # private method calls
    class PyPiLocatorMock(TestPyPiLocator):
        _is_platform_dependent = Mock(return_value=False)
        def convert_url_to_download_info(self, link, project_name):
            return "HELLO, I AM A PROJECT INFO"

        def _update_version_data(self, versions, info):
            versions['sure'] = '4.0'
            info.should.equal('HELLO, I AM A PROJECT INFO')

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I call _visit_link
    result = instance._visit_link('package-name', 'some-link')

    # Then it should be a tuple with 2
    result.should.equal(('sure', '4.0'))


def test_pypilocator_fetch_when_page_is_falsy():
    ("PyPiLocator#_fetch() should return empty if "
     "get_page returns a falsy value")

    # Given an instance of PyPiLocator that mocks the get_page method
    # so it returns None
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=None)

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should be an empty dictionary
    response.should.be.a(dict)
    response.should.be.empty


def test_pypilocator_fetch_when_page_links_are_falsy():
    ("PyPiLocator#_fetch() should return empty if "
     "get_page returns a page with no links")

    # Given a page that has no links
    page = Mock(links=[])

    # And that PyPiLocator#get_page returns that page
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=page)

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should be an empty dictionary
    response.should.be.a(dict)
    response.should.be.empty


def test_pypilocator_fetch_when_not_seen():
    ("PyPiLocator#_fetch() should visit an unseen link and "
     "grab its distribution into a dict")

    # Given a page that has one link
    page = Mock(links=[('http://someserver.com/package.tgz', 'some-rel')])

    # Given an instance of PyPiLocator that mocks the get_page method
    # to return a page with no links
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=page)
        _visit_link = Mock(return_value=('0.0.1', 'distribution'))

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should equal the existing distribution
    response.should.equal({
        '0.0.1': 'distribution'
    })


def test_finder_handle():
    "Finder#handle() should be able to find requirements"

    # Given that I have a Finder instance that returns the given distribution
    service = downloader.Finder(index=Mock())
    distribution = Mock(
        metadata=Mock(download_url='http://srv.com/pkg-0.1.zip'),
        locator=Mock(base_url='http://usr:passwd@srv.com/simple'))
    service.locator = Mock(locate=Mock(return_value=distribution))

    # When I call the service handler with a URL requirement
    service.handle('tests', {'requirement': 'pkg'}).should.equal({
        'requirement': 'pkg',
        'locator_url': 'http://usr:passwd@srv.com/simple',
        'url': 'http://srv.com/pkg-0.1.zip'
    })


def test_finder_handle_not_found():
    "Finder#handle() should raise ReportableError when it doesn't find the requirement"

    # Given that I have a Downloader instance
    service = downloader.Finder(index=Mock())
    service.locator = Mock(locate=Mock(return_value=None))

    # When I call the service handler with a URL requirement
    service.handle.when.called_with('tests', {'requirement': 'package'}).should.throw(
        ReportableError, 'Requirement `package\' not found'
    )


def test_downloader_handle():
    "Downloader#handle() should return the `tarball' path"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())
    service._download_http = Mock(return_value=('tarball', 'package-0.1.zip'))

    # When I call the service handler with a URL requirement
    tarball = service.handle('tests', {
        'requirement': 'package (0.1)',
        'url': 'http://host/path/package-0.1.zip',
    })

    # Then I see that the right tarball name was returned
    tarball.should.equal({
        'requirement': 'package (0.1)',
        'tarball': 'package-0.1.zip',
    })


def test_downloader_handle_return_wheel():
    "Downloader#handle() should return the `wheel' path when it downloads a whl file"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())
    service._download_http = Mock(
        return_value=('wheel', 'package-0.1-cp27-none-macosx_10_8_x86_64.whl'))

    # When I call the service handler with a URL requirement
    tarball = service.handle('tests', {
        'requirement': 'package (0.1)',
        'url': 'http://host/path/package-0.1-cp27-none-macosx_10_8_x86_64.whl',
    })

    # Then I see that the right tarball name was returned
    tarball.should.equal({
        'requirement': 'package (0.1)',
        'wheel': 'package-0.1-cp27-none-macosx_10_8_x86_64.whl',
    })


def test_downloader_download():
    "Downloader#download() Should call the right handler given the protocol of the link being processed"

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # And I mock all the actual protocol handlers (`_download_*()`)
    service._download_http = Mock()
    service._download_git = Mock()
    service._download_hg = Mock()
    service._download_svn = Mock()

    # When I try to download certain URLs
    service.download('http://source.com/blah')
    service.download('git+ssh://github.com/clarete/curdling.git')
    service.download('hg+http://hg.python.org.com/cpython')
    service.download('svn+http://svn.oldschool.com/repo')

    # Then I see that the right handlers were called. Notice that the vcs
    # prefixes will be stripped out
    service._download_http.assert_called_once_with('http://source.com/blah')
    service._download_git.assert_called_once_with('ssh://github.com/clarete/curdling.git')
    service._download_hg.assert_called_once_with('http://hg.python.org.com/cpython')
    service._download_svn.assert_called_once_with('http://svn.oldschool.com/repo')


def test_downloader_download_with_locator():
    "Downloader#download() should reuse the authentication information present in the locator's URL"

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # And I mock all the actual HTTP handler
    service._download_http = Mock()

    # When I download an HTTP link with a locator
    service.download('http://source.com/blah', 'http://user:passwd@source.com')

    # Then I see URL forwarded to the handler still have the authentication info
    service._download_http.assert_called_once_with('http://user:passwd@source.com/blah')


def test_downloader_download_bad_url():
    "Downloader#download() Should raise an exception if we can't handle the link"

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # When I try to download a weird link
    service.download.when.called_with('weird link').should.throw(
        UnknownURL,
        '''\
   "weird link"
   
   Your URL looks wrong. Make sure it's a valid HTTP
   link or a valid VCS link prefixed with the name of
   the VCS of your choice. Eg.:
   
    $ curd install https://pypi.python.org/simple/curdling/curdling-0.1.2.tar.gz
    $ curd install git+ssh://github.com/clarete/curdling.git''')


@patch('curdling.services.downloader.http_retrieve')
def test_downloader_download_http_handler(http_retrieve):
    "Downloader#_download_http() should download HTTP links"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())

    # And I patch the opener so we'll just pretend the HTTP IO is happening
    response = Mock(status=200)
    response.headers.get.return_value = ''
    http_retrieve.return_value = (response, None)

    # When I download an HTTP link
    service._download_http('http://blah/package.tar.gz')

    # Then I see that the URL was properly forward to the indexer
    service.index.from_data.assert_called_once_with(
        'http://blah/package.tar.gz',
        response.read.return_value)

    # And Then I see that the response was read raw to avoid problems with
    # gzipped packages; The curdler component will do that!
    response.read.assert_called_once_with(
        cache_content=True, decode_content=False)


@patch('curdling.services.downloader.http_retrieve')
def test_downloader_download_http_handler_blow_up_on_error(http_retrieve):
    "Downloader#_download_http() should handle HTTP status != 200"

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # And I patch the opener so we'll just pretend the HTTP IO is happening
    response = Mock(status=500)
    response.headers.get.return_value = ''
    http_retrieve.return_value = response, None

    # When I download an HTTP link
    service._download_http.when.called_with('http://blah/package.tar.gz').should.throw(
        ReportableError,
        'Failed to download url `http://blah/package.tar.gz\': 500 (Internal Server Error)'
    )


@patch('curdling.services.downloader.http_retrieve')
def test_downloader_download_http_handler_use_right_url_on_redirect(http_retrieve):
    "Downloader#_download_http() should handle HTTP status = 302"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())

    # And I patch the opener so we'll just pretend the HTTP IO is happening
    response = Mock(status=200)
    response.headers.get.side_effect = {}.get
    http_retrieve.return_value = response, 'pkg-0.1.tar.gz'

    # When I download an HTTP link that redirects to another location
    service._download_http('http://pkg.io/download')

    # Then I see the package name being read from the redirected URL,
    # not from the original one.
    service.index.from_data.assert_called_once_with(
        'pkg-0.1.tar.gz', response.read.return_value,
    )


@patch('curdling.services.downloader.http_retrieve')
def test_downloader_download_http_handler_use_content_disposition(http_retrieve):
    "Downloader#_download_http() should know how to use the header Content-Disposition to name the new file"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())

    # And I patch the opener so we'll just pretend the HTTP IO is happening
    response = Mock(status=200)
    response.headers.get.return_value = 'attachment; filename=sure-0.1.1.tar.gz'
    http_retrieve.return_value = response, None

    # When I download an HTTP link
    service._download_http('http://blah/package.tar.gz')

    # Then I see the file name forward to the index was the one found in the header
    service.index.from_data.assert_called_once_with(
        'sure-0.1.1.tar.gz', response.read.return_value)


@patch('curdling.services.downloader.http_retrieve')
def test_downloader_download_http_handler_use_content_disposition_with_quotes(http_retrieve):
    "Downloader#_download_http() should know how to use the header Content-Disposition to name the new file and strip the quotes"

    # Given that I have a Downloader instance
    service = downloader.Downloader(index=Mock())

    # And I patch the opener so we'll just pretend the HTTP IO is happening
    response = Mock(status=200)
    response.headers.get.return_value = 'attachment; filename="sure-0.1.1.tar.gz"'
    http_retrieve.return_value = response, None

    # When I download an HTTP link
    service._download_http('http://blah/package.tar.gz')

    # Then I see the file name forward to the index was the one found in the header
    service.index.from_data.assert_called_once_with(
        'sure-0.1.1.tar.gz', response.read.return_value)


@patch('curdling.services.downloader.tempfile')
@patch('curdling.services.downloader.util')
def test_downloader_download_vcs_handlers(util, tempfile):
    "Downloader#_download_{git,hg,svn}() should call their respective shell commands to retrieve a VCS URL"

    tempfile.mkdtemp.return_value = 'tmp'

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # When I call the VCS handlers
    service._download_git('git-url')
    service._download_hg('hg-url')
    service._download_svn('svn-url')

    # Then I see that all the calls for the shell commands were done properly
    list(util.execute_command.call_args_list).should.equal([
        call('git', 'clone', 'git-url', 'tmp'),
        call('hg', 'clone', 'hg-url', 'tmp'),
        call('svn', 'co', '-q', 'svn-url', 'tmp'),
    ])


@patch('curdling.services.downloader.tempfile')
@patch('curdling.services.downloader.util')
def test_downloader_download_vcs_handlers_with_rev(util, tempfile):
    "Downloader#_download_{git,hg,svn}() Should find the revision informed in the URL and point the retrieved code to it"

    tempfile.mkdtemp.return_value = 'tmp'

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # When I call the VCS handlers with a revision
    service._download_git('git-url@rev')
    service._download_hg('hg-url@rev')
    service._download_svn('svn-url@rev')

    # Then I see that all the calls for the shell commands were done properly
    list(util.execute_command.call_args_list).should.equal([
        call('git', 'clone', 'git-url', 'tmp'),
        call('git', 'reset', '--hard', 'rev', cwd='tmp'),
        call('hg', 'clone', 'hg-url', 'tmp'),
        call('hg', 'update', '-q', 'rev', cwd='tmp'),
        call('svn', 'co', '-q', '-r', 'rev', 'svn-url', 'tmp'),
    ])

########NEW FILE########
__FILENAME__ = test_signals
from mock import Mock
from curdling.signal import Signal, SignalEmitter


def test_signal():
    "It should possible to emit signals"

    # Given that I have a button that emits signals
    class Button(SignalEmitter):
        clicked = Signal()

    # And a content to store results of the callback function associated with
    # the `clicked` signal in the next lines
    callback = Mock()

    # And an instance of that button class
    b = Button()
    b.connect('clicked', callback)

    # When button instance gets clicked (IOW: when we emit the `clicked`
    # signal)
    b.emit('clicked', a=1, b=2)

    # Then we see that the  dictionary was populated as expected
    callback.assert_called_once_with(a=1, b=2)


def test_signal_that_does_not_exist():
    "AttributeError must be raised if a given signal does not exist"

    # Given that I have a button that emits signals, but with no signals
    class Button(SignalEmitter):
        pass

    # And an instance of that button class
    b = Button()

    # When I try to connect an unknown signal to the instance, Then I see
    # things just explode with a nice message.
    b.connect.when.called_with('clicked', lambda *a: a).should.throw(
        AttributeError,
        'There is no such signal (clicked) in this emitter (button)',
    )



########NEW FILE########
__FILENAME__ = test_tool
from __future__ import absolute_import, print_function, unicode_literals

import io
import logging
import mock

from collections import namedtuple
from curdling import tool


def test_get_packages_from_empty_args():
    "get_packages_from_args() Should return an empty list when no package spec can be found in `args' "

    # Given that I have an argument bag with no package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=None, requirements=None)

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got nothing!
    packages.should.be.empty


def test_get_packages_from_args():
    "get_packages_from_args() Should find out all the package names specified in `packages`"

    # Given that I have an argument bag with package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=['sure', 'milieu'], requirements=None)

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got the packages I specified
    packages.should.equal(['sure', 'milieu'])


def test_get_packages_requirement_from_args():
    "get_packages_from_args() Should expand all the packages specified in `requirements`"

    requirements = io.StringIO('sure==0.2.1\nmilieu==0.1.7')
    requirements2 = io.StringIO('python-dateutil')

    # Given that I have an argument bag with package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=None, requirements=[requirements, requirements2])

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got the packages I specified
    packages.should.equal([
        'sure (0.2.1)', 'milieu (0.1.7)', 'python-dateutil'])


def test_initialize_logging():
    """This test just ensures tool.initialize_logging does not raise an
    exception, as happened on Python 2.6 before ab7fc12f
    """
    with mock.patch.object(logging, 'getLogger'):
        tool.initialize_logging(
            log_file=mock.sentinel.log_file,
            log_level=logging.DEBUG,
            log_name=mock.sentinel.log_name,
        )

########NEW FILE########
__FILENAME__ = test_util
from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling import util
import io


def test_is_url():
    "is_url() Should tell if a given string is a URL or not"
    util.is_url('http://gnu.org').should.be.true
    util.is_url('just-a-name').should.be.false


def test_safe_name():
    "safe_name() Should normalize the requirement name"
    util.safe_name('package_name 2.0').should.equal('package-name (2.0)')
    util.safe_name('package_name>=2.1,<=3.0').should.equal('package-name (>= 2.1, <= 3.0)')
    util.safe_name('package[dev,test]==2.0').should.equal('package[dev,test] (2.0)')


@patch('io.open')
def test_expand_requirements(open_func):
    "It should be possible to include other files inside"

    # Given that I have a file called "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = \
        '-r requirements.txt\nsure==0.2.1\n'

    # And a file called "requirements_txt"
    open_func.return_value.read.return_value = 'gherkin==0.1.0\n\n\n'

    # When I expand the file "development.txt"
    requirements = util.expand_requirements(development_txt)

    # Then I see that the requirement present in "development.txt" was
    # included, as well as the one present in "requirements.txt",
    # referenced using the '-r' option
    requirements.should.equal([
        'gherkin (0.1.0)',
        'sure (0.2.1)',
    ])


def test_expand_commented_requirements():
    "expand_requirements() should skip commented lines"

    # Given the file "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = (
        '# -r requirements.txt\n\n'
        'gherkin==0.1.0\n\n\n'
    )

    # When I expand the file
    requirements = util.expand_requirements(development_txt)

    # Then I see that all the required files were retrieved and the
    # comments were omitted
    requirements.should.equal([
        'gherkin (0.1.0)',
    ])


def test_expand_requirements_parse_http_links():
    "It should be possible to parse files with http links"

    # Given the file "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = (
        'sure==0.2.1\nhttp://python.org'
    )

    # When I expand the file
    requirements = util.expand_requirements(development_txt)

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'sure (0.2.1)',
        'http://python.org',
    ])


def test_filehash():
    "filehash() should return the hash file objects"

    # Given that I have a file instance
    fp = io.BytesIO(b'My Content')

    # When I call the filehash function
    hashed = util.filehash(fp, 'md5')

    # Then I see the hash was right
    hashed.should.equal('a86c5dea3ad44078a1f79f9cf2c6786d')


def test_spaces():
    "spaces() should add spaces to paragraphs"

    # Given that I have a paragraph of text
    text = '''phrase 1
phrase 2
phrase 3'''

    # When I add spaces to the above text
    spaced = util.spaces(4, text)

    # Then I see each line starting with the right amount of spaces
    spaced.should.equal('''    phrase 1
    phrase 2
    phrase 3''')


def test_get_auth_info_from_url():
    "get_auth_info_from_url() should be able to extract authentication data from a URL"

    # Given that I have a URL that contains authentication info
    url = "http://user:password@domain.org"

    # When I try to get the authentication information
    authentication_information = util.get_auth_info_from_url(url)

    # Then I see both user and password are correct
    authentication_information.should.equal({
        'authorization': 'Basic dXNlcjpwYXNzd29yZA=='})


def test_get_auth_info_from_url_no_auth_info():
    "get_auth_info_from_url() Should return an empty dictionary if no authentication info is found in the URL"

    # Given that I have a URL that contains authentication info
    url = "http://domain.org"

    # When I try to get the authentication information
    authentication_information = util.get_auth_info_from_url(url)

    # Then I see that the authentication information is just empty
    authentication_information.should.equal({})


def test_get_auth_info_from_url_for_proxy():
    "get_auth_info_from_url() Should return the Proxy-Authorization header when proxy=True"

    # Given that I have a URL that contains authentication info
    url = "http://user:password@domain.org"

    # When I try to get the authentication information for a proxy
    authentication_information = util.get_auth_info_from_url(url, proxy=True)

    # Then I see both user and password are correct
    authentication_information.should.equal({
        'proxy-authorization': 'Basic dXNlcjpwYXNzd29yZA=='})


@patch('curdling.util.subprocess')
def test_execute_command(subprocess):
    "execute_command() Should return None when the subprocess runs successfully"

    # Given that my process will definitely fail
    subprocess.Popen.return_value.returncode = 0
    subprocess.Popen.return_value.communicate.return_value = ["stdout", "stderr"]

    # When I execute the command; Then I see it raises the right exception
    # containing the stderr of the command we tried to run
    util.execute_command('ls').should.be.none


@patch('curdling.util.subprocess')
def test_execute_command_when_it_fails(subprocess):
    "execute_command() Should raise an exception if the command fails"

    # Given that my process will definitely fail
    subprocess.Popen.return_value.returncode = 1
    subprocess.Popen.return_value.communicate.return_value = ["stdout", "stderr"]

    # When I execute the command; Then I see it raises the right exception
    # containing the stderr of the command we tried to run
    util.execute_command.when.called_with('ls').should.throw(Exception, "stderr")


def test_safe_constraints():
    "safe_constraints() Should return a string with all the constraints of a requirement separated by comma"

    util.safe_constraints('curdling (== 0.3.3, >= 0.3.2)').should.equal(
        '0.3.3, >= 0.3.2')

    util.safe_constraints('curdling').should.be.none

    util.safe_constraints('http://codeload.github.com/clarete/curdling').should.be.none

########NEW FILE########
__FILENAME__ = test_wheel
from mock import Mock
from curdling.wheel import Wheel
from curdling.version import __version__


def test_from_name():
    "Wheel.from_name() Should return an instance of `Wheel` with all attributes from the received wheel name"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27-none-any'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_from_name_with_ext():
    "Wheel.from_name() Should also work if the name has the '.whl' extension"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27-none-any.whl'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_from_name_with_ext():
    "Wheel.from_name() Should also expand compressed tags in the file name"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27.py33-none-any.whl'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27.py33')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_name():
    "Wheel.name() Should use the attributes associated to the Wheel instance to build a valid wheel file name"

    # Given the following wheel
    wheel = Wheel()
    wheel.distribution = 'curdzz'
    wheel.version = '0.1.2'
    wheel.build = '1'
    wheel.tags.pyver = 'py27'
    wheel.tags.abi = None
    wheel.tags.arch = None

    # Then I see that the tags property was properly filled out as well
    dict(wheel.tags).should.equal({
        'pyver': 'py27',
        'abi': None,
        'arch': None,
    })

    # And when I generate the file name; Then I see that it uses all
    # the previously associated metadata
    wheel.name().should.equal('curdzz-0.1.2-1-py27-none-any')


def test_info():

    # Given the following wheel
    wheel = Wheel.from_name('sure-0.1.2-1x-py27.py33-none-any')

    # When I try to access the info related to that wheel
    info = wheel.info()

    # Then I see it matches all the data described in the wheel file
    # name
    info.should.equal({
        'Wheel-Version': '1.0',
        'Generator': 'Curdling {0}'.format(__version__),
        'Root-Is-Purelib': 'True',
        'Build': '1x',
        'Tag': [
            'py27-none-any',
            'py33-none-any',
        ],
    })


def test_read_wheel_file():
    "Wheel.read_wheel_file() Should parse the WHEEL file of an archive into a dictionary"

    # Given the following WHEEL file of a fake archive
    archive = Mock()
    archive.read.return_value = b'''\
Wheel-Version: 1.0
Generator: bdist_wheel (0.21.0)
Root-Is-Purelib: true
Tag: py27-none-any
Tag: py3-none-any
'''

    # When it is parsed
    information = Wheel().read_wheel_file(archive)

    # Then I see that the information was parsed correctly
    information.should.equal({
        'Wheel-Version': '1.0',
        'Generator': 'bdist_wheel (0.21.0)',
        'Root-Is-Purelib': 'true',
        'Tag': ['py27-none-any', 'py3-none-any']
    })

########NEW FILE########
