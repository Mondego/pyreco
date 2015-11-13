__FILENAME__ = conf
# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'pbr'
copyright = '2013, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme_path = ["."]
html_theme = '_theme'
html_static_path = ['static']

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     '%s.tex' % project,
     '%s Documentation' % project,
     'OpenStack Foundation', 'manual'),
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = core
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

from distutils import core
from distutils import errors
import os
import sys
import warnings

from setuptools import dist

from pbr import util


core.Distribution = dist._get_unpatched(core.Distribution)
if sys.version_info[0] == 3:
    string_type = str
    integer_types = (int,)
else:
    string_type = basestring
    integer_types = (int, long)


def pbr(dist, attr, value):
    """Implements the actual pbr setup() keyword.  When used, this should be
    the only keyword in your setup() aside from `setup_requires`.

    If given as a string, the value of pbr is assumed to be the relative path
    to the setup.cfg file to use.  Otherwise, if it evaluates to true, it
    simply assumes that pbr should be used, and the default 'setup.cfg' is
    used.

    This works by reading the setup.cfg file, parsing out the supported
    metadata and command options, and using them to rebuild the
    `DistributionMetadata` object and set the newly added command options.

    The reason for doing things this way is that a custom `Distribution` class
    will not play nicely with setup_requires; however, this implementation may
    not work well with distributions that do use a `Distribution` subclass.
    """

    if not value:
        return
    if isinstance(value, string_type):
        path = os.path.abspath(value)
    else:
        path = os.path.abspath('setup.cfg')
    if not os.path.exists(path):
        raise errors.DistutilsFileError(
            'The setup.cfg file %s does not exist.' % path)

    # Converts the setup.cfg file to setup() arguments
    try:
        attrs = util.cfg_to_args(path)
    except Exception:
        e = sys.exc_info()[1]
        raise errors.DistutilsSetupError(
            'Error parsing %s: %s: %s' % (path, e.__class__.__name__, e))

    # Repeat some of the Distribution initialization code with the newly
    # provided attrs
    if attrs:
        # Skips 'options' and 'licence' support which are rarely used; may add
        # back in later if demanded
        for key, val in attrs.items():
            if hasattr(dist.metadata, 'set_' + key):
                getattr(dist.metadata, 'set_' + key)(val)
            elif hasattr(dist.metadata, key):
                setattr(dist.metadata, key, val)
            elif hasattr(dist, key):
                setattr(dist, key, val)
            else:
                msg = 'Unknown distribution option: %s' % repr(key)
                warnings.warn(msg)

    # Re-finalize the underlying Distribution
    core.Distribution.finalize_options(dist)

    # This bit comes out of distribute/setuptools
    if isinstance(dist.metadata.version, integer_types + (float,)):
        # Some people apparently take "version number" too literally :)
        dist.metadata.version = str(dist.metadata.version)

    # This bit of hackery is necessary so that the Distribution will ignore
    # normally unsupport command options (namely pre-hooks and post-hooks).
    # dist.command_options is normally a dict mapping command names to dicts of
    # their options.  Now it will be a defaultdict that returns IgnoreDicts for
    # the each command's options so we can pass through the unsupported options
    ignore = ['pre_hook.*', 'post_hook.*']
    dist.command_options = util.DefaultGetDict(lambda: util.IgnoreDict(ignore))

########NEW FILE########
__FILENAME__ = extra_files
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from distutils import errors
import os

_extra_files = []


def get_extra_files():
    global _extra_files
    return _extra_files


def set_extra_files(extra_files):
    # Let's do a sanity check
    for filename in extra_files:
        if not os.path.exists(filename):
            raise errors.DistutilsFileError(
                '%s from the extra_files option in setup.cfg does not '
                'exist' % filename)
    global _extra_files
    _extra_files[:] = extra_files[:]

########NEW FILE########
__FILENAME__ = find_package
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import setuptools


def smart_find_packages(package_list):
    """Run find_packages the way we intend."""
    packages = []
    for pkg in package_list.strip().split("\n"):
        pkg_path = pkg.replace('.', os.path.sep)
        packages.append(pkg)
        packages.extend(['%s.%s' % (pkg, f)
                         for f in setuptools.find_packages(pkg_path)])
    return "\n".join(set(packages))

########NEW FILE########
__FILENAME__ = backwards
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from pbr.hooks import base
from pbr import packaging


class BackwardsCompatConfig(base.BaseConfig):

    section = 'backwards_compat'

    def hook(self):
        self.config['include_package_data'] = 'True'
        packaging.append_text_list(
            self.config, 'dependency_links',
            packaging.parse_dependency_links())
        packaging.append_text_list(
            self.config, 'tests_require',
            packaging.parse_requirements(
                packaging.TEST_REQUIREMENTS_FILES))

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


class BaseConfig(object):

    section = None

    def __init__(self, config):
        self._global_config = config
        self.config = self._global_config.get(self.section, dict())
        self.pbr_config = config.get('pbr', dict())

    def run(self):
        self.hook()
        self.save()

    def hook(self):
        pass

    def save(self):
        self._global_config[self.section] = self.config

########NEW FILE########
__FILENAME__ = commands
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

from setuptools.command import easy_install

from pbr.hooks import base
from pbr import packaging


class CommandsConfig(base.BaseConfig):

    section = 'global'

    def __init__(self, config):
        super(CommandsConfig, self).__init__(config)
        self.commands = self.config.get('commands', "")

    def save(self):
        self.config['commands'] = self.commands
        super(CommandsConfig, self).save()

    def add_command(self, command):
        self.commands = "%s\n%s" % (self.commands, command)

    def hook(self):
        self.add_command('pbr.packaging.LocalEggInfo')
        self.add_command('pbr.packaging.LocalSDist')
        self.add_command('pbr.packaging.LocalInstallScripts')
        if os.name != 'nt':
            easy_install.get_script_args = packaging.override_get_script_args

        if packaging.have_sphinx():
            self.add_command('pbr.packaging.LocalBuildDoc')
            self.add_command('pbr.packaging.LocalBuildLatex')

        if os.path.exists('.testr.conf') and packaging.have_testr():
            # There is a .testr.conf file. We want to use it.
            self.add_command('pbr.packaging.TestrTest')
        elif self.config.get('nosetests', False) and packaging.have_nose():
            # We seem to still have nose configured
            self.add_command('pbr.packaging.NoseTest')

        use_egg = packaging.get_boolean_option(
            self.pbr_config, 'use-egg', 'PBR_USE_EGG')
        # We always want non-egg install unless explicitly requested
        if 'manpages' in self.pbr_config or not use_egg:
            self.add_command('pbr.packaging.LocalInstall')

########NEW FILE########
__FILENAME__ = files
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys

from pbr import find_package
from pbr.hooks import base


def get_manpath():
    manpath = 'share/man'
    if os.path.exists(os.path.join(sys.prefix, 'man')):
        # This works around a bug with install where it expects every node
        # in the relative data directory to be an actual directory, since at
        # least Debian derivatives (and probably other platforms as well)
        # like to symlink Unixish /usr/local/man to /usr/local/share/man.
        manpath = 'man'
    return manpath


def get_man_section(section):
    return os.path.join(get_manpath(), 'man%s' % section)


class FilesConfig(base.BaseConfig):

    section = 'files'

    def __init__(self, config, name):
        super(FilesConfig, self).__init__(config)
        self.name = name
        self.data_files = self.config.get('data_files', '')

    def save(self):
        self.config['data_files'] = self.data_files
        super(FilesConfig, self).save()

    def expand_globs(self):
        finished = []
        for line in self.data_files.split("\n"):
            if line.rstrip().endswith('*') and '=' in line:
                (target, source_glob) = line.split('=')
                source_prefix = source_glob.strip()[:-1]
                target = target.strip()
                if not target.endswith(os.path.sep):
                    target += os.path.sep
                for (dirpath, dirnames, fnames) in os.walk(source_prefix):
                    finished.append(
                        "%s = " % dirpath.replace(source_prefix, target))
                    finished.extend(
                        [" %s" % os.path.join(dirpath, f) for f in fnames])
            else:
                finished.append(line)

        self.data_files = "\n".join(finished)

    def add_man_path(self, man_path):
        self.data_files = "%s\n%s =" % (self.data_files, man_path)

    def add_man_page(self, man_page):
        self.data_files = "%s\n  %s" % (self.data_files, man_page)

    def get_man_sections(self):
        man_sections = dict()
        manpages = self.pbr_config['manpages']
        for manpage in manpages.split():
            section_number = manpage.strip()[-1]
            section = man_sections.get(section_number, list())
            section.append(manpage.strip())
            man_sections[section_number] = section
        return man_sections

    def hook(self):
        package = self.config.get('packages', self.name).strip()
        if os.path.isdir(package):
            self.config['packages'] = find_package.smart_find_packages(package)

        self.expand_globs()

        if 'manpages' in self.pbr_config:
            man_sections = self.get_man_sections()
            for (section, pages) in man_sections.items():
                manpath = get_man_section(section)
                self.add_man_path(manpath)
                for page in pages:
                    self.add_man_page(page)

########NEW FILE########
__FILENAME__ = metadata
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from pbr.hooks import base
from pbr import packaging


class MetadataConfig(base.BaseConfig):

    section = 'metadata'

    def hook(self):
        self.config['version'] = packaging.get_version(
            self.config['name'], self.config.get('version', None))
        packaging.append_text_list(
            self.config, 'requires_dist',
            packaging.parse_requirements())

    def get_name(self):
        return self.config['name']

########NEW FILE########
__FILENAME__ = packaging
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
# Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Utilities with minimum-depends for use in setup.py
"""

from __future__ import unicode_literals

import email
import io
import os
import re
import subprocess
import sys

from distutils.command import install as du_install
import distutils.errors
from distutils import log
import pkg_resources
from setuptools.command import easy_install
from setuptools.command import egg_info
from setuptools.command import install
from setuptools.command import install_scripts
from setuptools.command import sdist

try:
    import cStringIO
except ImportError:
    import io as cStringIO

from pbr import extra_files

TRUE_VALUES = ('true', '1', 'yes')
REQUIREMENTS_FILES = ('requirements.txt', 'tools/pip-requires')
TEST_REQUIREMENTS_FILES = ('test-requirements.txt', 'tools/test-requires')
# part of the standard library starting with 2.7
# adding it to the requirements list screws distro installs
BROKEN_ON_27 = ('argparse', 'importlib', 'ordereddict')


def get_requirements_files():
    files = os.environ.get("PBR_REQUIREMENTS_FILES")
    if files:
        return tuple(f.strip() for f in files.split(','))
    # Returns a list composed of:
    # - REQUIREMENTS_FILES with -py2 or -py3 in the name
    #   (e.g. requirements-py3.txt)
    # - REQUIREMENTS_FILES
    return (list(map(('-py' + str(sys.version_info[0])).join,
                     map(os.path.splitext, REQUIREMENTS_FILES)))
            + list(REQUIREMENTS_FILES))


def append_text_list(config, key, text_list):
    """Append a \n separated list to possibly existing value."""
    new_value = []
    current_value = config.get(key, "")
    if current_value:
        new_value.append(current_value)
    new_value.extend(text_list)
    config[key] = '\n'.join(new_value)


def _pip_install(links, requires, root=None, option_dict=dict()):
    if get_boolean_option(
            option_dict, 'skip_pip_install', 'SKIP_PIP_INSTALL'):
        return
    cmd = [sys.executable, '-m', 'pip.__init__', 'install']
    if root:
        cmd.append("--root=%s" % root)
    for link in links:
        cmd.append("-f")
        cmd.append(link)

    # NOTE(ociuhandu): popen on Windows does not accept unicode strings
    _run_shell_command(
        cmd + requires,
        throw_on_error=True, buffer=False, env=dict(PIP_USE_WHEEL=b"true"))


def _any_existing(file_list):
    return [f for f in file_list if os.path.exists(f)]


# Get requirements from the first file that exists
def get_reqs_from_files(requirements_files):
    for requirements_file in _any_existing(requirements_files):
        with open(requirements_file, 'r') as fil:
            return fil.read().split('\n')
    return []


def parse_requirements(requirements_files=None):

    if requirements_files is None:
        requirements_files = get_requirements_files()

    def egg_fragment(match):
        # take a versioned egg fragment and return a
        # versioned package requirement e.g.
        # nova-1.2.3 becomes nova>=1.2.3
        return re.sub(r'([\w.]+)-([\w.-]+)',
                      r'\1>=\2',
                      match.group(1))

    requirements = []
    for line in get_reqs_from_files(requirements_files):
        # Ignore comments
        if (not line.strip()) or line.startswith('#'):
            continue

        # Handle nested requirements files such as:
        # -r other-requirements.txt
        if line.startswith('-r'):
            req_file = line.partition(' ')[2]
            requirements += parse_requirements([req_file])
            continue

        try:
            project_name = pkg_resources.Requirement.parse(line).project_name
        except ValueError:
            project_name = None

        # For the requirements list, we need to inject only the portion
        # after egg= so that distutils knows the package it's looking for
        # such as:
        # -e git://github.com/openstack/nova/master#egg=nova
        # -e git://github.com/openstack/nova/master#egg=nova-1.2.3
        if re.match(r'\s*-e\s+', line):
            line = re.sub(r'\s*-e\s+.*#egg=(.*)$', egg_fragment, line)
        # such as:
        # http://github.com/openstack/nova/zipball/master#egg=nova
        # http://github.com/openstack/nova/zipball/master#egg=nova-1.2.3
        elif re.match(r'\s*https?:', line):
            line = re.sub(r'\s*https?:.*#egg=(.*)$', egg_fragment, line)
        # -f lines are for index locations, and don't get used here
        elif re.match(r'\s*-f\s+', line):
            line = None
            reason = 'Index Location'
        elif (project_name and
                project_name in BROKEN_ON_27 and sys.version_info >= (2, 7)):
            line = None
            reason = 'Python 2.6 only dependency'

        if line is not None:
            requirements.append(line)
        else:
            log.info(
                '[pbr] Excluding %s: %s' % (project_name, reason))

    return requirements


def parse_dependency_links(requirements_files=None):
    if requirements_files is None:
        requirements_files = get_requirements_files()
    dependency_links = []
    # dependency_links inject alternate locations to find packages listed
    # in requirements
    for line in get_reqs_from_files(requirements_files):
        # skip comments and blank lines
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        # lines with -e or -f need the whole line, minus the flag
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))
        # lines that are only urls can go in unmolested
        elif re.match(r'\s*https?:', line):
            dependency_links.append(line)
    return dependency_links


def _run_git_command(cmd, git_dir, **kwargs):
    if not isinstance(cmd, (list, tuple)):
        cmd = [cmd]
    return _run_shell_command(
        ['git', '--git-dir=%s' % git_dir] + cmd, **kwargs)


def _run_shell_command(cmd, throw_on_error=False, buffer=True, env=None):
    if buffer:
        out_location = subprocess.PIPE
        err_location = subprocess.PIPE
    else:
        out_location = None
        err_location = None

    newenv = os.environ.copy()
    if env:
        newenv.update(env)

    output = subprocess.Popen(cmd,
                              stdout=out_location,
                              stderr=err_location,
                              env=newenv)
    out = output.communicate()
    if output.returncode and throw_on_error:
        raise distutils.errors.DistutilsError(
            "%s returned %d" % (cmd, output.returncode))
    if len(out) == 0 or not out[0] or not out[0].strip():
        return ''
    return out[0].strip().decode('utf-8')


def _get_git_directory():
    return _run_shell_command(['git', 'rev-parse', '--git-dir'])


def _git_is_installed():
    try:
        # We cannot use 'which git' as it may not be available
        # in some distributions, So just try 'git --version'
        # to see if we run into trouble
        _run_shell_command(['git', '--version'])
    except OSError:
        return False
    return True


def _get_highest_tag(tags):
    """Find the highest tag from a list.

    Pass in a list of tag strings and this will return the highest
    (latest) as sorted by the pkg_resources version parser.
    """
    return max(tags, key=pkg_resources.parse_version)


def get_boolean_option(option_dict, option_name, env_name):
    return ((option_name in option_dict
             and option_dict[option_name][1].lower() in TRUE_VALUES) or
            str(os.getenv(env_name)).lower() in TRUE_VALUES)


def write_git_changelog(git_dir=None, dest_dir=os.path.curdir,
                        option_dict=dict()):
    """Write a changelog based on the git changelog."""
    should_skip = get_boolean_option(option_dict, 'skip_changelog',
                                     'SKIP_WRITE_GIT_CHANGELOG')
    if not should_skip:
        new_changelog = os.path.join(dest_dir, 'ChangeLog')
        # If there's already a ChangeLog and it's not writable, just use it
        if (os.path.exists(new_changelog)
                and not os.access(new_changelog, os.W_OK)):
            return
        log.info('[pbr] Writing ChangeLog')
        if git_dir is None:
            git_dir = _get_git_directory()
        if git_dir:
            log_cmd = ['log', '--oneline', '--decorate']
            changelog = _run_git_command(log_cmd, git_dir)
            first_line = True
            with io.open(new_changelog, "w",
                         encoding="utf-8") as changelog_file:
                changelog_file.write("CHANGES\n=======\n\n")
                for line in changelog.split('\n'):
                    line_parts = line.split()
                    if len(line_parts) < 2:
                        continue
                    # Tags are in a list contained in ()'s. If a commit
                    # subject that is tagged happens to have ()'s in it
                    # this will fail
                    if line_parts[1].startswith('(') and ')' in line:
                        msg = line.split(')')[1].strip()
                    else:
                        msg = " ".join(line_parts[1:])

                    if "tag:" in line:
                        tags = [
                            tag.split(",")[0]
                            for tag in line.split(")")[0].split("tag: ")[1:]]
                        tag = _get_highest_tag(tags)

                        underline = len(tag) * '-'
                        if not first_line:
                            changelog_file.write('\n')
                        changelog_file.write(
                            ("%(tag)s\n%(underline)s\n\n" %
                             dict(tag=tag,
                                  underline=underline)))

                    if not msg.startswith("Merge "):
                        if msg.endswith("."):
                            msg = msg[:-1]
                        changelog_file.write(
                            ("* %(msg)s\n" % dict(msg=msg)))
                    first_line = False


def generate_authors(git_dir=None, dest_dir='.', option_dict=dict()):
    """Create AUTHORS file using git commits."""
    should_skip = get_boolean_option(option_dict, 'skip_authors',
                                     'SKIP_GENERATE_AUTHORS')
    if not should_skip:
        old_authors = os.path.join(dest_dir, 'AUTHORS.in')
        new_authors = os.path.join(dest_dir, 'AUTHORS')
        # If there's already an AUTHORS file and it's not writable, just use it
        if (os.path.exists(new_authors)
                and not os.access(new_authors, os.W_OK)):
            return
        log.info('[pbr] Generating AUTHORS')
        ignore_emails = '(jenkins@review|infra@lists|jenkins@openstack)'
        if git_dir is None:
            git_dir = _get_git_directory()
        if git_dir:
            authors = []

            # don't include jenkins email address in AUTHORS file
            git_log_cmd = ['log', '--format=%aN <%aE>']
            authors += _run_git_command(git_log_cmd, git_dir).split('\n')
            authors = [a for a in authors if not re.search(ignore_emails, a)]

            # get all co-authors from commit messages
            co_authors_out = _run_git_command('log', git_dir)
            co_authors = re.findall('Co-authored-by:.+', co_authors_out,
                                    re.MULTILINE)
            co_authors = [signed.split(":", 1)[1].strip()
                          for signed in co_authors if signed]

            authors += co_authors
            authors = sorted(set(authors))

            with open(new_authors, 'wb') as new_authors_fh:
                if os.path.exists(old_authors):
                    with open(old_authors, "rb") as old_authors_fh:
                        new_authors_fh.write(old_authors_fh.read())
                new_authors_fh.write(('\n'.join(authors) + '\n')
                                     .encode('utf-8'))


def _find_git_files(dirname='', git_dir=None):
    """Behave like a file finder entrypoint plugin.

    We don't actually use the entrypoints system for this because it runs
    at absurd times. We only want to do this when we are building an sdist.
    """
    file_list = []
    if git_dir is None and _git_is_installed():
        git_dir = _get_git_directory()
    if git_dir:
        log.info("[pbr] In git context, generating filelist from git")
        file_list = _run_git_command(['ls-files', '-z'], git_dir)
        file_list = file_list.split(b'\x00'.decode('utf-8'))
    return [f for f in file_list if f]


_rst_template = """%(heading)s
%(underline)s

.. automodule:: %(module)s
  :members:
  :undoc-members:
  :show-inheritance:
"""


def _find_modules(arg, dirname, files):
    for filename in files:
        if filename.endswith('.py') and filename != '__init__.py':
            arg["%s.%s" % (dirname.replace('/', '.'),
                           filename[:-3])] = True


class LocalInstall(install.install):
    """Runs python setup.py install in a sensible manner.

    Force a non-egg installed in the manner of
    single-version-externally-managed, which allows us to install manpages
    and config files.

    Because non-egg installs bypass the depend processing machinery, we
    need to do our own. Because easy_install is evil, just use pip to
    process our requirements files directly, which means we don't have to
    do crazy extra processing.

    Bypass installation if --single-version-externally-managed is given,
    so that behavior for packagers remains the same.
    """

    command_name = 'install'

    def run(self):
        option_dict = self.distribution.get_option_dict('pbr')
        if (not self.single_version_externally_managed
                and self.distribution.install_requires):
            _pip_install(
                self.distribution.dependency_links,
                self.distribution.install_requires, self.root,
                option_dict=option_dict)

        return du_install.install.run(self)


def _newer_requires_files(egg_info_dir):
    """Check to see if any of the requires files are newer than egg-info."""
    for target, sources in (('requires.txt', get_requirements_files()),
                            ('test-requires.txt', TEST_REQUIREMENTS_FILES)):
        target_path = os.path.join(egg_info_dir, target)
        for src in _any_existing(sources):
            if (not os.path.exists(target_path) or
                    os.path.getmtime(target_path)
                    < os.path.getmtime(src)):
                return True
    return False


def _copy_test_requires_to(egg_info_dir):
    """Copy the requirements file to egg-info/test-requires.txt."""
    with open(os.path.join(egg_info_dir, 'test-requires.txt'), 'w') as dest:
        for source in _any_existing(TEST_REQUIREMENTS_FILES):
            dest.write(open(source, 'r').read().rstrip('\n') + '\n')


class _PipInstallTestRequires(object):
    """Mixin class to install test-requirements.txt before running tests."""

    def install_test_requirements(self):

        links = parse_dependency_links(TEST_REQUIREMENTS_FILES)
        if self.distribution.tests_require:
            option_dict = self.distribution.get_option_dict('pbr')
            _pip_install(
                links, self.distribution.tests_require,
                option_dict=option_dict)

    def pre_run(self):
        self.egg_name = pkg_resources.safe_name(self.distribution.get_name())
        self.egg_info = "%s.egg-info" % pkg_resources.to_filename(
            self.egg_name)
        if (not os.path.exists(self.egg_info) or
                _newer_requires_files(self.egg_info)):
            ei_cmd = self.get_finalized_command('egg_info')
            ei_cmd.run()
            self.install_test_requirements()
            _copy_test_requires_to(self.egg_info)

try:
    from pbr import testr_command

    class TestrTest(testr_command.Testr, _PipInstallTestRequires):
        """Make setup.py test do the right thing."""

        command_name = 'test'

        def run(self):
            self.pre_run()
            # Can't use super - base class old-style class
            testr_command.Testr.run(self)

    _have_testr = True

except ImportError:
    _have_testr = False


def have_testr():
    return _have_testr

try:
    from nose import commands

    class NoseTest(commands.nosetests, _PipInstallTestRequires):
        """Fallback test runner if testr is a no-go."""

        command_name = 'test'

        def run(self):
            self.pre_run()
            # Can't use super - base class old-style class
            commands.nosetests.run(self)

    _have_nose = True

except ImportError:
    _have_nose = False


def have_nose():
    return _have_nose


_script_text = """# PBR Generated from %(group)r

import sys

from %(module_name)s import %(import_target)s


if __name__ == "__main__":
    sys.exit(%(invoke_target)s())
"""


def override_get_script_args(
        dist, executable=os.path.normpath(sys.executable), is_wininst=False):
    """Override entrypoints console_script."""
    header = easy_install.get_script_header("", executable, is_wininst)
    for group in 'console_scripts', 'gui_scripts':
        for name, ep in dist.get_entry_map(group).items():
            if not ep.attrs or len(ep.attrs) > 2:
                raise ValueError("Script targets must be of the form "
                                 "'func' or 'Class.class_method'.")
            script_text = _script_text % dict(
                group=group,
                module_name=ep.module_name,
                import_target=ep.attrs[0],
                invoke_target='.'.join(ep.attrs),
            )
            yield (name, header + script_text)


class LocalInstallScripts(install_scripts.install_scripts):
    """Intercepts console scripts entry_points."""
    command_name = 'install_scripts'

    def run(self):
        if os.name != 'nt':
            get_script_args = override_get_script_args
        else:
            get_script_args = easy_install.get_script_args

        import distutils.command.install_scripts

        self.run_command("egg_info")
        if self.distribution.scripts:
            # run first to set up self.outfiles
            distutils.command.install_scripts.install_scripts.run(self)
        else:
            self.outfiles = []
        if self.no_ep:
            # don't install entry point scripts into .egg file!
            return

        ei_cmd = self.get_finalized_command("egg_info")
        dist = pkg_resources.Distribution(
            ei_cmd.egg_base,
            pkg_resources.PathMetadata(ei_cmd.egg_base, ei_cmd.egg_info),
            ei_cmd.egg_name, ei_cmd.egg_version,
        )
        bs_cmd = self.get_finalized_command('build_scripts')
        executable = getattr(
            bs_cmd, 'executable', easy_install.sys_executable)
        is_wininst = getattr(
            self.get_finalized_command("bdist_wininst"), '_is_running', False
        )
        for args in get_script_args(dist, executable, is_wininst):
            self.write_script(*args)


class LocalManifestMaker(egg_info.manifest_maker):
    """Add any files that are in git and some standard sensible files."""

    def _add_pbr_defaults(self):
        for template_line in [
            'include AUTHORS',
            'include ChangeLog',
            'exclude .gitignore',
            'exclude .gitreview',
            'global-exclude *.pyc'
        ]:
            self.filelist.process_template_line(template_line)

    def add_defaults(self):
        option_dict = self.distribution.get_option_dict('pbr')

        sdist.sdist.add_defaults(self)
        self.filelist.append(self.template)
        self.filelist.append(self.manifest)
        self.filelist.extend(extra_files.get_extra_files())
        should_skip = get_boolean_option(option_dict, 'skip_git_sdist',
                                         'SKIP_GIT_SDIST')
        if not should_skip:
            rcfiles = _find_git_files()
            if rcfiles:
                self.filelist.extend(rcfiles)
        elif os.path.exists(self.manifest):
            self.read_manifest()
        ei_cmd = self.get_finalized_command('egg_info')
        self._add_pbr_defaults()
        self.filelist.include_pattern("*", prefix=ei_cmd.egg_info)


class LocalEggInfo(egg_info.egg_info):
    """Override the egg_info command to regenerate SOURCES.txt sensibly."""

    command_name = 'egg_info'

    def find_sources(self):
        """Generate SOURCES.txt only if there isn't one already.

        If we are in an sdist command, then we always want to update
        SOURCES.txt. If we are not in an sdist command, then it doesn't
        matter one flip, and is actually destructive.
        """
        manifest_filename = os.path.join(self.egg_info, "SOURCES.txt")
        if not os.path.exists(manifest_filename) or 'sdist' in sys.argv:
            log.info("[pbr] Processing SOURCES.txt")
            mm = LocalManifestMaker(self.distribution)
            mm.manifest = manifest_filename
            mm.run()
            self.filelist = mm.filelist
        else:
            log.info("[pbr] Reusing existing SOURCES.txt")
            self.filelist = egg_info.FileList()
            for entry in open(manifest_filename, 'r').read().split('\n'):
                self.filelist.append(entry)


class LocalSDist(sdist.sdist):
    """Builds the ChangeLog and Authors files from VC first."""

    command_name = 'sdist'

    def run(self):
        option_dict = self.distribution.get_option_dict('pbr')
        write_git_changelog(option_dict=option_dict)
        generate_authors(option_dict=option_dict)
        # sdist.sdist is an old style class, can't use super()
        sdist.sdist.run(self)

try:
    from sphinx import apidoc
    from sphinx import application
    from sphinx import config
    from sphinx import setup_command

    class LocalBuildDoc(setup_command.BuildDoc):

        command_name = 'build_sphinx'
        builders = ['html', 'man']

        def _get_source_dir(self):
            option_dict = self.distribution.get_option_dict('build_sphinx')
            if 'source_dir' in option_dict:
                source_dir = os.path.join(option_dict['source_dir'][1], 'api')
            else:
                source_dir = 'doc/source/api'
            if not os.path.exists(source_dir):
                os.makedirs(source_dir)
            return source_dir

        def generate_autoindex(self):
            log.info("[pbr] Autodocumenting from %s"
                     % os.path.abspath(os.curdir))
            modules = {}
            source_dir = self._get_source_dir()
            for pkg in self.distribution.packages:
                if '.' not in pkg:
                    for dirpath, dirnames, files in os.walk(pkg):
                        _find_modules(modules, dirpath, files)
            module_list = list(modules.keys())
            module_list.sort()
            autoindex_filename = os.path.join(source_dir, 'autoindex.rst')
            with open(autoindex_filename, 'w') as autoindex:
                autoindex.write(""".. toctree::
   :maxdepth: 1

""")
                for module in module_list:
                    output_filename = os.path.join(source_dir,
                                                   "%s.rst" % module)
                    heading = "The :mod:`%s` Module" % module
                    underline = "=" * len(heading)
                    values = dict(module=module, heading=heading,
                                  underline=underline)

                    log.info("[pbr] Generating %s"
                             % output_filename)
                    with open(output_filename, 'w') as output_file:
                        output_file.write(_rst_template % values)
                    autoindex.write("   %s.rst\n" % module)

        def _sphinx_tree(self):
                source_dir = self._get_source_dir()
                apidoc.main(['apidoc', '.', '-H', 'Modules', '-o', source_dir])

        def _sphinx_run(self):
            if not self.verbose:
                status_stream = cStringIO.StringIO()
            else:
                status_stream = sys.stdout
            confoverrides = {}
            if self.version:
                confoverrides['version'] = self.version
            if self.release:
                confoverrides['release'] = self.release
            if self.today:
                confoverrides['today'] = self.today
            sphinx_config = config.Config(self.config_dir, 'conf.py', {}, [])
            sphinx_config.init_values()
            if self.builder == 'man' and len(sphinx_config.man_pages) == 0:
                return
            app = application.Sphinx(
                self.source_dir, self.config_dir,
                self.builder_target_dir, self.doctree_dir,
                self.builder, confoverrides, status_stream,
                freshenv=self.fresh_env, warningiserror=True)

            try:
                app.build(force_all=self.all_files)
            except Exception as err:
                from docutils import utils
                if isinstance(err, utils.SystemMessage):
                    sys.stder.write('reST markup error:\n')
                    sys.stderr.write(err.args[0].encode('ascii',
                                                        'backslashreplace'))
                    sys.stderr.write('\n')
                else:
                    raise

            if self.link_index:
                src = app.config.master_doc + app.builder.out_suffix
                dst = app.builder.get_outfilename('index')
                os.symlink(src, dst)

        def run(self):
            option_dict = self.distribution.get_option_dict('pbr')
            tree_index = get_boolean_option(option_dict,
                                            'autodoc_tree_index_modules',
                                            'AUTODOC_TREE_INDEX_MODULES')
            auto_index = get_boolean_option(option_dict,
                                            'autodoc_index_modules',
                                            'AUTODOC_INDEX_MODULES')
            if not os.getenv('SPHINX_DEBUG'):
                #NOTE(afazekas): These options can be used together,
                # but they do a very similar thing in a difffernet way
                if tree_index:
                    self._sphinx_tree()
                if auto_index:
                    self.generate_autoindex()

            for builder in self.builders:
                self.builder = builder
                self.finalize_options()
                self.project = self.distribution.get_name()
                self.version = self.distribution.get_version()
                self.release = self.distribution.get_version()
                if 'warnerrors' in option_dict:
                    self._sphinx_run()
                else:
                    setup_command.BuildDoc.run(self)

        def finalize_options(self):
            # Not a new style class, super keyword does not work.
            setup_command.BuildDoc.finalize_options(self)
            # Allow builders to be configurable - as a comma separated list.
            if not isinstance(self.builders, list) and self.builders:
                self.builders = self.builders.split(',')

    class LocalBuildLatex(LocalBuildDoc):
        builders = ['latex']
        command_name = 'build_sphinx_latex'

    _have_sphinx = True

except ImportError:
    _have_sphinx = False


def have_sphinx():
    return _have_sphinx


def _get_revno(git_dir):
    """Return the number of commits since the most recent tag.

    We use git-describe to find this out, but if there are no
    tags then we fall back to counting commits since the beginning
    of time.
    """
    describe = _run_git_command(['describe', '--always'], git_dir)
    if "-" in describe:
        return describe.rsplit("-", 2)[-2]

    # no tags found
    revlist = _run_git_command(
        ['rev-list', '--abbrev-commit', 'HEAD'], git_dir)
    return len(revlist.splitlines())


def _get_version_from_git(pre_version):
    """Return a version which is equal to the tag that's on the current
    revision if there is one, or tag plus number of additional revisions
    if the current revision has no tag.
    """

    git_dir = _get_git_directory()
    if git_dir:
        if pre_version:
            try:
                return _run_git_command(
                    ['describe', '--exact-match'], git_dir,
                    throw_on_error=True).replace('-', '.')
            except Exception:
                sha = _run_git_command(
                    ['log', '-n1', '--pretty=format:%h'], git_dir)
                return "%s.dev%s.g%s" % (pre_version, _get_revno(git_dir), sha)
        else:
            return _run_git_command(
                ['describe', '--always'], git_dir).replace('-', '.')
    # If we don't know the version, return an empty string so at least
    # the downstream users of the value always have the same type of
    # object to work with.
    try:
        return unicode()
    except NameError:
        return ''


def _get_version_from_pkg_info(package_name):
    """Get the version from PKG-INFO file if we can."""
    try:
        pkg_info_file = open('PKG-INFO', 'r')
    except (IOError, OSError):
        return None
    try:
        pkg_info = email.message_from_file(pkg_info_file)
    except email.MessageError:
        return None
    # Check to make sure we're in our own dir
    if pkg_info.get('Name', None) != package_name:
        return None
    return pkg_info.get('Version', None)


def get_version(package_name, pre_version=None):
    """Get the version of the project. First, try getting it from PKG-INFO, if
    it exists. If it does, that means we're in a distribution tarball or that
    install has happened. Otherwise, if there is no PKG-INFO file, pull the
    version from git.

    We do not support setup.py version sanity in git archive tarballs, nor do
    we support packagers directly sucking our git repo into theirs. We expect
    that a source tarball be made from our git repo - or that if someone wants
    to make a source tarball from a fork of our repo with additional tags in it
    that they understand and desire the results of doing that.
    """
    version = os.environ.get(
        "PBR_VERSION",
        os.environ.get("OSLO_PACKAGE_VERSION", None))
    if version:
        return version
    version = _get_version_from_pkg_info(package_name)
    if version:
        return version
    version = _get_version_from_git(pre_version)
    # Handle http://bugs.python.org/issue11638
    # version will either be an empty unicode string or a valid
    # unicode version string, but either way it's unicode and needs to
    # be encoded.
    if sys.version_info[0] == 2:
        version = version.encode('utf-8')
    if version:
        return version
    raise Exception("Versioning for this project requires either an sdist"
                    " tarball, or access to an upstream git repository."
                    " Are you sure that git is installed?")

########NEW FILE########
__FILENAME__ = testr_command
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (c) 2013 Testrepository Contributors
#
# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

"""setuptools/distutils commands to run testr via setup.py

Currently provides 'testr' which runs tests using testr. You can pass
--coverage which will also export PYTHON='coverage run --source <your package>'
and automatically combine the coverage from each testr backend test runner
after the run completes.

To use, just use setuptools/distribute and depend on testr, and it should be
picked up automatically (as the commands are exported in the testrepository
package metadata.
"""

from distutils import cmd
import distutils.errors
import logging
import os
import sys

from testrepository import commands

logger = logging.getLogger(__name__)


class Testr(cmd.Command):

    description = "Run unit tests using testr"

    user_options = [
        ('coverage', None, "Replace PYTHON with coverage and merge coverage "
         "from each testr worker."),
        ('testr-args=', 't', "Run 'testr' with these args"),
        ('omit=', 'o', "Files to omit from coverage calculations"),
        ('coverage-package-name=', None, "Use this name for coverage package"),
        ('slowest', None, "Show slowest test times after tests complete."),
        ('no-parallel', None, "Run testr serially"),
        ('log-level=', 'l', "Log level (default: info)"),
    ]

    boolean_options = ['coverage', 'slowest', 'no_parallel']

    def _run_testr(self, *args):
        logger.debug("_run_testr called with args = %r", args)
        return commands.run_argv([sys.argv[0]] + list(args),
                                 sys.stdin, sys.stdout, sys.stderr)

    def initialize_options(self):
        self.testr_args = None
        self.coverage = None
        self.omit = ""
        self.slowest = None
        self.coverage_package_name = None
        self.no_parallel = None
        self.log_level = 'info'

    def finalize_options(self):
        self.log_level = getattr(
            logging,
            self.log_level.upper(),
            logging.INFO)
        logging.basicConfig(level=self.log_level)
        logger.debug("finalize_options called")
        if self.testr_args is None:
            self.testr_args = []
        else:
            self.testr_args = self.testr_args.split()
        if self.omit:
            self.omit = "--omit=%s" % self.omit
        logger.debug("finalize_options: self.__dict__ = %r", self.__dict__)

    def run(self):
        """Set up testr repo, then run testr"""
        logger.debug("run called")
        if not os.path.isdir(".testrepository"):
            self._run_testr("init")

        if self.coverage:
            self._coverage_before()
        if not self.no_parallel:
            testr_ret = self._run_testr("run", "--parallel", *self.testr_args)
        else:
            testr_ret = self._run_testr("run", *self.testr_args)
        if testr_ret:
            raise distutils.errors.DistutilsError(
                "testr failed (%d)" % testr_ret)
        if self.slowest:
            print("Slowest Tests")
            self._run_testr("slowest")
        if self.coverage:
            self._coverage_after()

    def _coverage_before(self):
        logger.debug("_coverage_before called")
        package = self.distribution.get_name()
        if package.startswith('python-'):
            package = package[7:]

        # Use this as coverage package name
        if self.coverage_package_name:
            package = self.coverage_package_name
        options = "--source %s --parallel-mode" % self.coverage_package_name
        os.environ['PYTHON'] = ("coverage run %s" % options)
        logger.debug("os.environ['PYTHON'] = %r", os.environ['PYTHON'])

    def _coverage_after(self):
        logger.debug("_coverage_after called")
        os.system("coverage combine")
        os.system("coverage html -d ./cover %s" % self.omit)

########NEW FILE########
__FILENAME__ = base
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

"""Common utilities used in testing"""

import os
import shutil
import subprocess
import sys

import fixtures
import testresources
import testtools

from pbr import packaging


class DiveDir(fixtures.Fixture):
    """Dive into given directory and return back on cleanup.

    :ivar path: The target directory.
    """

    def __init__(self, path):
        self.path = path

    def setUp(self):
        super(DiveDir, self).setUp()
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.path)


class BaseTestCase(testtools.TestCase, testresources.ResourcedTestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 30)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid, fail hard.
            print("OS_TEST_TIMEOUT set to invalid value"
                  " defaulting to no timeout")
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        if os.environ.get('OS_STDOUT_CAPTURE') in packaging.TRUE_VALUES:
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if os.environ.get('OS_STDERR_CAPTURE') in packaging.TRUE_VALUES:
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))
        self.log_fixture = self.useFixture(
            fixtures.FakeLogger('pbr'))

        # Older git does not have config --local, so create a temporary home
        # directory to permit using git config --global without stepping on
        # developer configuration.
        self.useFixture(fixtures.TempHomeDir())
        self.useFixture(fixtures.NestedTempfile())
        self.useFixture(fixtures.FakeLogger())
        self.useFixture(fixtures.EnvironmentVariable('PBR_VERSION', '0.0'))

        self.temp_dir = self.useFixture(fixtures.TempDir()).path
        self.package_dir = os.path.join(self.temp_dir, 'testpackage')
        shutil.copytree(os.path.join(os.path.dirname(__file__), 'testpackage'),
                        self.package_dir)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.package_dir)
        self.addCleanup(self._discard_testpackage)

    def _discard_testpackage(self):
        # Remove pbr.testpackage from sys.modules so that it can be freshly
        # re-imported by the next test
        for k in list(sys.modules):
            if (k == 'pbr_testpackage' or
                    k.startswith('pbr_testpackage.')):
                del sys.modules[k]

    def run_setup(self, *args, **kwargs):
        return self._run_cmd(sys.executable, ('setup.py',) + args, **kwargs)

    def _run_cmd(self, cmd, args=[], allow_fail=True):
        """Run a command in the root of the test working copy.

        Runs a command, with the given argument list, in the root of the test
        working copy--returns the stdout and stderr streams and the exit code
        from the subprocess.
        """
        result = _run_cmd([cmd] + list(args), cwd=self.package_dir)
        if result[2] and not allow_fail:
            raise Exception("Command failed retcode=%s" % result[2])
        return result


def _run_cmd(args, cwd):
    """Run the command args in cwd.

    :param args: The command to run e.g. ['git', 'status']
    :param cwd: The directory to run the comamnd in.
    :return: ((stdout, stderr), returncode)
    """
    p = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    streams = tuple(s.decode('latin1').strip() for s in p.communicate())
    for content in streams:
        print(content)
    return (streams) + (p.returncode,)

########NEW FILE########
__FILENAME__ = cmd
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import print_function


def main():
    print("PBR Test Command")


class Foo(object):

    @classmethod
    def bar(self):
        print("PBR Test Command - with class!")

########NEW FILE########
__FILENAME__ = test_commands
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

from testtools import content

from pbr.tests import base


class TestCommands(base.BaseTestCase):
    def test_custom_build_py_command(self):
        """Test custom build_py command.

        Test that a custom subclass of the build_py command runs when listed in
        the commands [global] option, rather than the normal build command.
        """

        stdout, stderr, return_code = self.run_setup('build_py')
        self.addDetail('stdout', content.text_content(stdout))
        self.addDetail('stderr', content.text_content(stderr))
        self.assertIn('Running custom build_py command.', stdout)
        self.assertEqual(return_code, 0)

########NEW FILE########
__FILENAME__ = test_core
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

import glob
import os
import tarfile

import fixtures

from pbr.tests import base


class TestCore(base.BaseTestCase):

    cmd_names = ('pbr_test_cmd', 'pbr_test_cmd_with_class')

    def check_script_install(self, install_stdout):
        for cmd_name in self.cmd_names:
            install_txt = 'Installing %s script to %s' % (cmd_name,
                                                          self.temp_dir)
            self.assertIn(install_txt, install_stdout)

            cmd_filename = os.path.join(self.temp_dir, cmd_name)

            script_txt = open(cmd_filename, 'r').read()
            self.assertNotIn('pkg_resources', script_txt)

            stdout, _, return_code = self._run_cmd(cmd_filename)
            self.assertIn("PBR", stdout)

    def test_setup_py_keywords(self):
        """setup.py --keywords.

        Test that the `./setup.py --keywords` command returns the correct
        value without balking.
        """

        self.run_setup('egg_info')
        stdout, _, _ = self.run_setup('--keywords')
        assert stdout == 'packaging,distutils,setuptools'

    def test_sdist_extra_files(self):
        """Test that the extra files are correctly added."""

        stdout, _, return_code = self.run_setup('sdist', '--formats=gztar')

        # There can be only one
        try:
            tf_path = glob.glob(os.path.join('dist', '*.tar.gz'))[0]
        except IndexError:
            assert False, 'source dist not found'

        tf = tarfile.open(tf_path)
        names = ['/'.join(p.split('/')[1:]) for p in tf.getnames()]

        self.assertIn('extra-file.txt', names)

    def test_console_script_install(self):
        """Test that we install a non-pkg-resources console script."""

        if os.name == 'nt':
            self.skipTest('Windows support is passthrough')

        stdout, _, return_code = self.run_setup(
            'install_scripts', '--install-dir=%s' % self.temp_dir)

        self.useFixture(
            fixtures.EnvironmentVariable('PYTHONPATH', '.'))

        self.check_script_install(stdout)

    def test_console_script_develop(self):
        """Test that we develop a non-pkg-resources console script."""

        if os.name == 'nt':
            self.skipTest('Windows support is passthrough')

        self.useFixture(
            fixtures.EnvironmentVariable(
                'PYTHONPATH', ".:%s" % self.temp_dir))

        stdout, _, return_code = self.run_setup(
            'develop', '--install-dir=%s' % self.temp_dir)

        self.check_script_install(stdout)


class TestGitSDist(base.BaseTestCase):

    def setUp(self):
        super(TestGitSDist, self).setUp()

        stdout, _, return_code = self._run_cmd('git', ('init',))
        if return_code:
            self.skipTest("git not installed")

        stdout, _, return_code = self._run_cmd('git', ('add', '.'))
        stdout, _, return_code = self._run_cmd(
            'git', ('commit', '-m', 'Turn this into a git repo'))

        stdout, _, return_code = self.run_setup('sdist', '--formats=gztar')

    def test_sdist_git_extra_files(self):
        """Test that extra files found in git are correctly added."""
        # There can be only one
        tf_path = glob.glob(os.path.join('dist', '*.tar.gz'))[0]
        tf = tarfile.open(tf_path)
        names = ['/'.join(p.split('/')[1:]) for p in tf.getnames()]

        self.assertIn('git-extra-file.txt', names)

########NEW FILE########
__FILENAME__ = test_files
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import print_function

import os

import fixtures

from pbr.hooks import files
from pbr.tests import base


class FilesConfigTest(base.BaseTestCase):

    def setUp(self):
        super(FilesConfigTest, self).setUp()

        pkg_fixture = fixtures.PythonPackage(
            "fake_package", [
                ("fake_module.py", b""),
                ("other_fake_module.py", b""),
            ])
        self.useFixture(pkg_fixture)
        pkg_etc = os.path.join(pkg_fixture.base, 'etc')
        pkg_sub = os.path.join(pkg_etc, 'sub')
        subpackage = os.path.join(
            pkg_fixture.base, 'fake_package', 'subpackage')
        os.makedirs(pkg_sub)
        os.makedirs(subpackage)
        with open(os.path.join(pkg_etc, "foo"), 'w') as foo_file:
            foo_file.write("Foo Data")
        with open(os.path.join(pkg_sub, "bar"), 'w') as foo_file:
            foo_file.write("Bar Data")
        with open(os.path.join(subpackage, "__init__.py"), 'w') as foo_file:
            foo_file.write("# empty")

        self.useFixture(base.DiveDir(pkg_fixture.base))

    def test_implicit_auto_package(self):
        config = dict(
            files=dict(
            )
        )
        files.FilesConfig(config, 'fake_package').run()
        self.assertIn('subpackage', config['files']['packages'])

    def test_auto_package(self):
        config = dict(
            files=dict(
                packages='fake_package',
            )
        )
        files.FilesConfig(config, 'fake_package').run()
        self.assertIn('subpackage', config['files']['packages'])

    def test_data_files_globbing(self):
        config = dict(
            files=dict(
                data_files="\n  etc/pbr = etc/*"
            )
        )
        files.FilesConfig(config, 'fake_package').run()
        self.assertIn(
            '\netc/pbr/ = \n etc/foo\netc/pbr/sub = \n etc/sub/bar',
            config['files']['data_files'])

########NEW FILE########
__FILENAME__ = test_hooks
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

import os
import textwrap

from testtools.matchers import Contains

from pbr.tests import base
from pbr.tests import util


class TestHooks(base.BaseTestCase):
    def setUp(self):
        super(TestHooks, self).setUp()
        with util.open_config(
                os.path.join(self.package_dir, 'setup.cfg')) as cfg:
            cfg.set('global', 'setup-hooks',
                    'pbr_testpackage._setup_hooks.test_hook_1\n'
                    'pbr_testpackage._setup_hooks.test_hook_2')
            cfg.set('build_ext', 'pre-hook.test_pre_hook',
                    'pbr_testpackage._setup_hooks.test_pre_hook')
            cfg.set('build_ext', 'post-hook.test_post_hook',
                    'pbr_testpackage._setup_hooks.test_post_hook')

    def test_global_setup_hooks(self):
        """Test setup_hooks.

        Test that setup_hooks listed in the [global] section of setup.cfg are
        executed in order.
        """

        stdout, _, return_code = self.run_setup('egg_info')
        assert 'test_hook_1\ntest_hook_2' in stdout
        assert return_code == 0

    def test_command_hooks(self):
        """Test command hooks.

        Simple test that the appropriate command hooks run at the
        beginning/end of the appropriate command.
        """

        stdout, _, return_code = self.run_setup('egg_info')
        assert 'build_ext pre-hook' not in stdout
        assert 'build_ext post-hook' not in stdout
        assert return_code == 0

        stdout, _, return_code = self.run_setup('build_ext')
        assert textwrap.dedent("""
            running build_ext
            running pre_hook pbr_testpackage._setup_hooks.test_pre_hook for command build_ext
            build_ext pre-hook
        """) in stdout  # flake8: noqa
        assert stdout.endswith('build_ext post-hook')
        assert return_code == 0

    def test_custom_commands_known(self):
        stdout, _, return_code = self.run_setup('--help-commands')
        self.assertFalse(return_code)
        self.assertThat(stdout, Contains(" testr "))

########NEW FILE########
__FILENAME__ = test_packaging
# Copyright (c) 2013 New Dream Network, LLC (DreamHost)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

import os
import tempfile

import fixtures
import mock

from pbr import packaging
from pbr.tests import base


class TestRepo(fixtures.Fixture):
    """A git repo for testing with.

    Use of TempHomeDir with this fixture is strongly recommended as due to the
    lack of config --local in older gits, it will write to the users global
    configuration without TempHomeDir.
    """

    def __init__(self, basedir):
        super(TestRepo, self).__init__()
        self._basedir = basedir

    def setUp(self):
        super(TestRepo, self).setUp()
        base._run_cmd(['git', 'init', '.'], self._basedir)
        base._run_cmd(
            ['git', 'config', '--global', 'user.email', 'example@example.com'],
            self._basedir)
        base._run_cmd(['git', 'add', '.'], self._basedir)

    def commit(self):
        base._run_cmd(['git', 'commit', '-m', 'test commit'], self._basedir)


class TestPackagingInGitRepoWithCommit(base.BaseTestCase):

    def setUp(self):
        super(TestPackagingInGitRepoWithCommit, self).setUp()
        repo = self.useFixture(TestRepo(self.package_dir))
        repo.commit()
        self.run_setup('sdist', allow_fail=False)

    def test_authors(self):
        # One commit, something should be in the authors list
        with open(os.path.join(self.package_dir, 'AUTHORS'), 'r') as f:
            body = f.read()
        self.assertNotEqual(body, '')

    def test_changelog(self):
        with open(os.path.join(self.package_dir, 'ChangeLog'), 'r') as f:
            body = f.read()
        # One commit, something should be in the ChangeLog list
        self.assertNotEqual(body, '')


class TestPackagingInGitRepoWithoutCommit(base.BaseTestCase):

    def setUp(self):
        super(TestPackagingInGitRepoWithoutCommit, self).setUp()
        self.useFixture(TestRepo(self.package_dir))
        self.run_setup('sdist', allow_fail=False)

    def test_authors(self):
        # No commits, no authors in list
        with open(os.path.join(self.package_dir, 'AUTHORS'), 'r') as f:
            body = f.read()
        self.assertEqual(body, '\n')

    def test_changelog(self):
        # No commits, nothing should be in the ChangeLog list
        with open(os.path.join(self.package_dir, 'ChangeLog'), 'r') as f:
            body = f.read()
        self.assertEqual(body, 'CHANGES\n=======\n\n')


class TestPackagingInPlainDirectory(base.BaseTestCase):

    def setUp(self):
        super(TestPackagingInPlainDirectory, self).setUp()
        self.run_setup('sdist', allow_fail=False)

    def test_authors(self):
        # Not a git repo, no AUTHORS file created
        filename = os.path.join(self.package_dir, 'AUTHORS')
        self.assertFalse(os.path.exists(filename))

    def test_changelog(self):
        # Not a git repo, no ChangeLog created
        filename = os.path.join(self.package_dir, 'ChangeLog')
        self.assertFalse(os.path.exists(filename))


class TestPresenceOfGit(base.BaseTestCase):

    def testGitIsInstalled(self):
        with mock.patch.object(packaging,
                               '_run_shell_command') as _command:
            _command.return_value = 'git version 1.8.4.1'
            self.assertEqual(True, packaging._git_is_installed())

    def testGitIsNotInstalled(self):
        with mock.patch.object(packaging,
                               '_run_shell_command') as _command:
            _command.side_effect = OSError
            self.assertEqual(False, packaging._git_is_installed())


class TestNestedRequirements(base.BaseTestCase):

    def test_nested_requirement(self):
        tempdir = tempfile.mkdtemp()
        requirements = os.path.join(tempdir, 'requirements.txt')
        nested = os.path.join(tempdir, 'nested.txt')
        with open(requirements, 'w') as f:
            f.write('-r ' + nested)
        with open(nested, 'w') as f:
            f.write('pbr')
        result = packaging.parse_requirements([requirements])
        self.assertEqual(result, ['pbr'])

########NEW FILE########
__FILENAME__ = test_version
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc.
# Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from pbr.tests import base
from pbr import version


class DeferredVersionTestCase(base.BaseTestCase):

    def test_cached_version(self):
        class MyVersionInfo(version.VersionInfo):
            def _get_version_from_pkg_resources(self):
                return "5.5.5.5"

        deferred_string = MyVersionInfo("openstack").\
            cached_version_string()
        self.assertEqual("5.5.5.5", deferred_string)

########NEW FILE########
__FILENAME__ = util
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

import contextlib
import os
import shutil
import stat

try:
    import ConfigParser as configparser
except ImportError:
    import configparser


@contextlib.contextmanager
def open_config(filename):
    cfg = configparser.ConfigParser()
    cfg.read(filename)
    yield cfg
    with open(filename, 'w') as fp:
        cfg.write(fp)


def rmtree(path):
    """shutil.rmtree() with error handler.

    Handle 'access denied' from trying to delete read-only files.
    """

    def onerror(func, path, exc_info):
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise

    return shutil.rmtree(path, onerror=onerror)

########NEW FILE########
__FILENAME__ = util
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (C) 2013 Association of Universities for Research in Astronomy
#                    (AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#        endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS

"""The code in this module is mostly copy/pasted out of the distutils2 source
code, as recommended by Tarek Ziade.  As such, it may be subject to some change
as distutils2 development continues, and will have to be kept up to date.

I didn't want to use it directly from distutils2 itself, since I do not want it
to be an installation dependency for our packages yet--it is still too unstable
(the latest version on PyPI doesn't even install).
"""

# These first two imports are not used, but are needed to get around an
# irritating Python bug that can crop up when using ./setup.py test.
# See: http://www.eby-sarna.com/pipermail/peak/2010-May/003355.html
try:
    import multiprocessing  # flake8: noqa
except ImportError:
    pass
import logging  # flake8: noqa

import os
import re
import sys
import traceback

from collections import defaultdict

import distutils.ccompiler

from distutils import log
from distutils.errors import (DistutilsOptionError, DistutilsModuleError,
                              DistutilsFileError)
from setuptools.command.egg_info import manifest_maker
from setuptools.dist import Distribution
from setuptools.extension import Extension

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from pbr import extra_files
import pbr.hooks

# A simplified RE for this; just checks that the line ends with version
# predicates in ()
_VERSION_SPEC_RE = re.compile(r'\s*(.*?)\s*\((.*)\)\s*$')


# Mappings from setup() keyword arguments to setup.cfg options;
# The values are (section, option) tuples, or simply (section,) tuples if
# the option has the same name as the setup() argument
D1_D2_SETUP_ARGS = {
    "name": ("metadata",),
    "version": ("metadata",),
    "author": ("metadata",),
    "author_email": ("metadata",),
    "maintainer": ("metadata",),
    "maintainer_email": ("metadata",),
    "url": ("metadata", "home_page"),
    "description": ("metadata", "summary"),
    "keywords": ("metadata",),
    "long_description": ("metadata", "description"),
    "download-url": ("metadata",),
    "classifiers": ("metadata", "classifier"),
    "platforms": ("metadata", "platform"),  # **
    "license": ("metadata",),
    # Use setuptools install_requires, not
    # broken distutils requires
    "install_requires": ("metadata", "requires_dist"),
    "setup_requires": ("metadata", "setup_requires_dist"),
    "provides": ("metadata", "provides_dist"),  # **
    "obsoletes": ("metadata", "obsoletes_dist"),  # **
    "package_dir": ("files", 'packages_root'),
    "packages": ("files",),
    "package_data": ("files",),
    "namespace_packages": ("files",),
    "data_files": ("files",),
    "scripts": ("files",),
    "py_modules": ("files", "modules"),   # **
    "cmdclass": ("global", "commands"),
    # Not supported in distutils2, but provided for
    # backwards compatibility with setuptools
    "use_2to3": ("backwards_compat", "use_2to3"),
    "zip_safe": ("backwards_compat", "zip_safe"),
    "tests_require": ("backwards_compat", "tests_require"),
    "dependency_links": ("backwards_compat",),
    "include_package_data": ("backwards_compat",),
}

# setup() arguments that can have multiple values in setup.cfg
MULTI_FIELDS = ("classifiers",
                "platforms",
                "install_requires",
                "provides",
                "obsoletes",
                "namespace_packages",
                "packages",
                "package_data",
                "data_files",
                "scripts",
                "py_modules",
                "dependency_links",
                "setup_requires",
                "tests_require",
                "cmdclass")

# setup() arguments that contain boolean values
BOOL_FIELDS = ("use_2to3", "zip_safe", "include_package_data")


CSV_FIELDS = ("keywords",)


def resolve_name(name):
    """Resolve a name like ``module.object`` to an object and return it.

    Raise ImportError if the module or name is not found.
    """

    parts = name.split('.')
    cursor = len(parts) - 1
    module_name = parts[:cursor]
    attr_name = parts[-1]

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name), fromlist=[attr_name])
            break
        except ImportError:
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]
            attr_name = parts[cursor]
            ret = ''

    for part in parts[cursor:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            raise ImportError(name)

    return ret


def cfg_to_args(path='setup.cfg'):
    """ Distutils2 to distutils1 compatibility util.

        This method uses an existing setup.cfg to generate a dictionary of
        keywords that can be used by distutils.core.setup(kwargs**).

        :param file:
            The setup.cfg path.
        :raises DistutilsFileError:
            When the setup.cfg file is not found.

    """

    # The method source code really starts here.
    parser = configparser.RawConfigParser()
    if not os.path.exists(path):
        raise DistutilsFileError("file '%s' does not exist" %
                                 os.path.abspath(path))
    parser.read(path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser.items(section))

    # Run setup_hooks, if configured
    setup_hooks = has_get_option(config, 'global', 'setup_hooks')
    package_dir = has_get_option(config, 'files', 'packages_root')

    # Add the source package directory to sys.path in case it contains
    # additional hooks, and to make sure it's on the path before any existing
    # installations of the package
    if package_dir:
        package_dir = os.path.abspath(package_dir)
        sys.path.insert(0, package_dir)

    try:
        if setup_hooks:
            setup_hooks = [
                hook for hook in split_multiline(setup_hooks)
                if hook != 'pbr.hooks.setup_hook']
            for hook in setup_hooks:
                hook_fn = resolve_name(hook)
                try :
                    hook_fn(config)
                except SystemExit:
                    log.error('setup hook %s terminated the installation')
                except:
                    e = sys.exc_info()[1]
                    log.error('setup hook %s raised exception: %s\n' %
                              (hook, e))
                    log.error(traceback.format_exc())
                    sys.exit(1)

        # Run the pbr hook
        pbr.hooks.setup_hook(config)

        kwargs = setup_cfg_to_setup_kwargs(config)

        # Set default config overrides
        kwargs['include_package_data'] = True
        kwargs['zip_safe'] = False

        register_custom_compilers(config)

        ext_modules = get_extension_modules(config)
        if ext_modules:
            kwargs['ext_modules'] = ext_modules

        entry_points = get_entry_points(config)
        if entry_points:
            kwargs['entry_points'] = entry_points

        wrap_commands(kwargs)

        # Handle the [files]/extra_files option
        files_extra_files = has_get_option(config, 'files', 'extra_files')
        if files_extra_files:
            extra_files.set_extra_files(split_multiline(files_extra_files))

    finally:
        # Perform cleanup if any paths were added to sys.path
        if package_dir:
            sys.path.pop(0)

    return kwargs


def setup_cfg_to_setup_kwargs(config):
    """Processes the setup.cfg options and converts them to arguments accepted
    by setuptools' setup() function.
    """

    kwargs = {}

    for arg in D1_D2_SETUP_ARGS:
        if len(D1_D2_SETUP_ARGS[arg]) == 2:
            # The distutils field name is different than distutils2's.
            section, option = D1_D2_SETUP_ARGS[arg]

        elif len(D1_D2_SETUP_ARGS[arg]) == 1:
            # The distutils field name is the same thant distutils2's.
            section = D1_D2_SETUP_ARGS[arg][0]
            option = arg

        in_cfg_value = has_get_option(config, section, option)
        if not in_cfg_value:
            # There is no such option in the setup.cfg
            if arg == "long_description":
                in_cfg_value = has_get_option(config, section,
                                              "description_file")
                if in_cfg_value:
                    in_cfg_value = split_multiline(in_cfg_value)
                    value = ''
                    for filename in in_cfg_value:
                        description_file = open(filename)
                        try:
                            value += description_file.read().strip() + '\n\n'
                        finally:
                            description_file.close()
                    in_cfg_value = value
            else:
                continue

        if arg in CSV_FIELDS:
            in_cfg_value = split_csv(in_cfg_value)
        if arg in MULTI_FIELDS:
            in_cfg_value = split_multiline(in_cfg_value)
        elif arg in BOOL_FIELDS:
            # Provide some flexibility here...
            if in_cfg_value.lower() in ('true', 't', '1', 'yes', 'y'):
                in_cfg_value = True
            else:
                in_cfg_value = False

        if in_cfg_value:
            if arg in ('install_requires', 'tests_require'):
                # Replaces PEP345-style version specs with the sort expected by
                # setuptools
                in_cfg_value = [_VERSION_SPEC_RE.sub(r'\1\2', pred)
                                for pred in in_cfg_value]
            elif arg == 'package_dir':
                in_cfg_value = {'': in_cfg_value}
            elif arg in ('package_data', 'data_files'):
                data_files = {}
                firstline = True
                prev = None
                for line in in_cfg_value:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key, value = (key.strip(), value.strip())
                        if key in data_files:
                            # Multiple duplicates of the same package name;
                            # this is for backwards compatibility of the old
                            # format prior to d2to1 0.2.6.
                            prev = data_files[key]
                            prev.extend(value.split())
                        else:
                            prev = data_files[key.strip()] = value.split()
                    elif firstline:
                        raise DistutilsOptionError(
                            'malformed package_data first line %r (misses '
                            '"=")' % line)
                    else:
                        prev.extend(line.strip().split())
                    firstline = False
                if arg == 'data_files':
                    # the data_files value is a pointlessly different structure
                    # from the package_data value
                    data_files = data_files.items()
                in_cfg_value = data_files
            elif arg == 'cmdclass':
                cmdclass = {}
                dist = Distribution()
                for cls in in_cfg_value:
                    cls = resolve_name(cls)
                    cmd = cls(dist)
                    cmdclass[cmd.get_command_name()] = cls
                in_cfg_value = cmdclass

        kwargs[arg] = in_cfg_value

    return kwargs


def register_custom_compilers(config):
    """Handle custom compilers; this has no real equivalent in distutils, where
    additional compilers could only be added programmatically, so we have to
    hack it in somehow.
    """

    compilers = has_get_option(config, 'global', 'compilers')
    if compilers:
        compilers = split_multiline(compilers)
        for compiler in compilers:
            compiler = resolve_name(compiler)

            # In distutils2 compilers these class attributes exist; for
            # distutils1 we just have to make something up
            if hasattr(compiler, 'name'):
                name = compiler.name
            else:
                name = compiler.__name__
            if hasattr(compiler, 'description'):
                desc = compiler.description
            else:
                desc = 'custom compiler %s' % name

            module_name = compiler.__module__
            # Note; this *will* override built in compilers with the same name
            # TODO: Maybe display a warning about this?
            cc = distutils.ccompiler.compiler_class
            cc[name] = (module_name, compiler.__name__, desc)

            # HACK!!!!  Distutils assumes all compiler modules are in the
            # distutils package
            sys.modules['distutils.' + module_name] = sys.modules[module_name]


def get_extension_modules(config):
    """Handle extension modules"""

    EXTENSION_FIELDS = ("sources",
                        "include_dirs",
                        "define_macros",
                        "undef_macros",
                        "library_dirs",
                        "libraries",
                        "runtime_library_dirs",
                        "extra_objects",
                        "extra_compile_args",
                        "extra_link_args",
                        "export_symbols",
                        "swig_opts",
                        "depends")

    ext_modules = []
    for section in config:
        if ':' in section:
            labels = section.split(':', 1)
        else:
            # Backwards compatibility for old syntax; don't use this though
            labels = section.split('=', 1)
        labels = [l.strip() for l in labels]
        if (len(labels) == 2) and (labels[0] == 'extension'):
            ext_args = {}
            for field in EXTENSION_FIELDS:
                value = has_get_option(config, section, field)
                # All extension module options besides name can have multiple
                # values
                if not value:
                    continue
                value = split_multiline(value)
                if field == 'define_macros':
                    macros = []
                    for macro in value:
                        macro = macro.split('=', 1)
                        if len(macro) == 1:
                            macro = (macro[0].strip(), None)
                        else:
                            macro = (macro[0].strip(), macro[1].strip())
                        macros.append(macro)
                    value = macros
                ext_args[field] = value
            if ext_args:
                if 'name' not in ext_args:
                    ext_args['name'] = labels[1]
                ext_modules.append(Extension(ext_args.pop('name'),
                                             **ext_args))
    return ext_modules


def get_entry_points(config):
    """Process the [entry_points] section of setup.cfg to handle setuptools
    entry points.  This is, of course, not a standard feature of
    distutils2/packaging, but as there is not currently a standard alternative
    in packaging, we provide support for them.
    """

    if not 'entry_points' in config:
        return {}

    return dict((option, split_multiline(value))
                for option, value in config['entry_points'].items())


def wrap_commands(kwargs):
    dist = Distribution()

    # This should suffice to get the same config values and command classes
    # that the actual Distribution will see (not counting cmdclass, which is
    # handled below)
    dist.parse_config_files()

    for cmd, _ in dist.get_command_list():
        hooks = {}
        for opt, val in dist.get_option_dict(cmd).items():
            val = val[1]
            if opt.startswith('pre_hook.') or opt.startswith('post_hook.'):
                hook_type, alias = opt.split('.', 1)
                hook_dict = hooks.setdefault(hook_type, {})
                hook_dict[alias] = val
        if not hooks:
            continue

        if 'cmdclass' in kwargs and cmd in kwargs['cmdclass']:
            cmdclass = kwargs['cmdclass'][cmd]
        else:
            cmdclass = dist.get_command_class(cmd)

        new_cmdclass = wrap_command(cmd, cmdclass, hooks)
        kwargs.setdefault('cmdclass', {})[cmd] = new_cmdclass


def wrap_command(cmd, cmdclass, hooks):
    def run(self, cmdclass=cmdclass):
        self.run_command_hooks('pre_hook')
        cmdclass.run(self)
        self.run_command_hooks('post_hook')

    return type(cmd, (cmdclass, object),
                {'run': run, 'run_command_hooks': run_command_hooks,
                 'pre_hook': hooks.get('pre_hook'),
                 'post_hook': hooks.get('post_hook')})


def run_command_hooks(cmd_obj, hook_kind):
    """Run hooks registered for that command and phase.

    *cmd_obj* is a finalized command object; *hook_kind* is either
    'pre_hook' or 'post_hook'.
    """

    if hook_kind not in ('pre_hook', 'post_hook'):
        raise ValueError('invalid hook kind: %r' % hook_kind)

    hooks = getattr(cmd_obj, hook_kind, None)

    if hooks is None:
        return

    for hook in hooks.values():
        if isinstance(hook, str):
            try:
                hook_obj = resolve_name(hook)
            except ImportError:
                err = sys.exc_info()[1] # For py3k
                raise DistutilsModuleError('cannot find hook %s: %s' %
                                           (hook,err))
        else:
            hook_obj = hook

        if not hasattr(hook_obj, '__call__'):
            raise DistutilsOptionError('hook %r is not callable' % hook)

        log.info('running %s %s for command %s',
                 hook_kind, hook, cmd_obj.get_command_name())

        try :
            hook_obj(cmd_obj)
        except:
            e = sys.exc_info()[1]
            log.error('hook %s raised exception: %s\n' % (hook, e))
            log.error(traceback.format_exc())
            sys.exit(1)


def has_get_option(config, section, option):
    if section in config and option in config[section]:
        return config[section][option]
    elif section in config and option.replace('_', '-') in config[section]:
        return config[section][option.replace('_', '-')]
    else:
        return False


def split_multiline(value):
    """Special behaviour when we have a multi line options"""

    value = [element for element in
             (line.strip() for line in value.split('\n'))
             if element]
    return value


def split_csv(value):
    """Special behaviour when we have a comma separated options"""

    value = [element for element in
             (chunk.strip() for chunk in value.split(','))
             if element]
    return value


def monkeypatch_method(cls):
    """A function decorator to monkey-patch a method of the same name on the
    given class.
    """

    def wrapper(func):
        orig = getattr(cls, func.__name__, None)
        if orig and not hasattr(orig, '_orig'):  # Already patched
            setattr(func, '_orig', orig)
            setattr(cls, func.__name__, func)
        return func

    return wrapper


# The following classes are used to hack Distribution.command_options a bit
class DefaultGetDict(defaultdict):
    """Like defaultdict, but the get() method also sets and returns the default
    value.
    """

    def get(self, key, default=None):
        if default is None:
            default = self.default_factory()
        return super(DefaultGetDict, self).setdefault(key, default)


class IgnoreDict(dict):
    """A dictionary that ignores any insertions in which the key is a string
    matching any string in `ignore`.  The ignore list can also contain wildcard
    patterns using '*'.
    """

    def __init__(self, ignore):
        self.__ignore = re.compile(r'(%s)' % ('|'.join(
                                   [pat.replace('*', '.*')
                                    for pat in ignore])))

    def __setitem__(self, key, val):
        if self.__ignore.match(key):
            return
        super(IgnoreDict, self).__setitem__(key, val)

########NEW FILE########
__FILENAME__ = version

#    Copyright 2012 OpenStack Foundation
#    Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Utilities for consuming the version from pkg_resources.
"""

import pkg_resources


class VersionInfo(object):

    def __init__(self, package):
        """Object that understands versioning for a package

        :param package: name of the python package, such as glance, or
                        python-glanceclient
        """
        self.package = package
        self.release = None
        self.version = None
        self._cached_version = None

    def __str__(self):
        """Make the VersionInfo object behave like a string."""
        return self.version_string()

    def __repr__(self):
        """Include the name."""
        return "pbr.version.VersionInfo(%s:%s)" % (
            self.package, self.version_string())

    def _get_version_from_pkg_resources(self):
        """Obtain a version from pkg_resources or setup-time logic if missing.

        This will try to get the version of the package from the pkg_resources
        record associated with the package, and if there is no such record
        falls back to the logic sdist would use.
        """
        try:
            requirement = pkg_resources.Requirement.parse(self.package)
            provider = pkg_resources.get_provider(requirement)
            return provider.version
        except pkg_resources.DistributionNotFound:
            # The most likely cause for this is running tests in a tree
            # produced from a tarball where the package itself has not been
            # installed into anything. Revert to setup-time logic.
            from pbr import packaging
            return packaging.get_version(self.package)

    def release_string(self):
        """Return the full version of the package.

        This including suffixes indicating VCS status.
        """
        if self.release is None:
            self.release = self._get_version_from_pkg_resources()

        return self.release

    def version_string(self):
        """Return the short version minus any alpha/beta tags."""
        if self.version is None:
            parts = []
            for part in self.release_string().split('.'):
                if part[0].isdigit():
                    parts.append(part)
                else:
                    break
            self.version = ".".join(parts)

        return self.version

    # Compatibility functions
    canonical_version_string = version_string
    version_string_with_vcs = release_string

    def cached_version_string(self, prefix=""):
        """Return a cached version string.

        This will return a cached version string if one is already cached,
        irrespective of prefix. If none is cached, one will be created with
        prefix and then cached and returned.
        """
        if not self._cached_version:
            self._cached_version = "%s%s" % (prefix,
                                             self.version_string())
        return self._cached_version

########NEW FILE########
