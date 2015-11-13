__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))
parser.add_option("--allow-site-packages",
                  action="store_true", default=False,
                  help=("Let bootstrap.py use existing site packages"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

try:
    if options.allow_site_packages:
        import setuptools
        import pkg_resources
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

ez = {}
exec(urlopen('https://bootstrap.pypa.io/ez_setup.py').read(), ez)

if not options.allow_site_packages:
    # ez_setup imports site, which adds site packages
    # this will remove them from the path to ensure that incompatible versions 
    # of setuptools are not in the path
    import site
    # inside a virtualenv, there is no 'getsitepackages'. 
    # We can't remove these reliably
    if hasattr(site, 'getsitepackages'):
        for sitepackage_path in site.getsitepackages():
            sys.path[:] = [x for x in sys.path if sitepackage_path not in x]

setup_args = dict(to_dir=tmpeggs, download_delay=0)
ez['use_setuptools'](**setup_args)
import setuptools
import pkg_resources

# This does not (always?) update the default working set.  We will
# do it.
for path in sys.path:
    if path not in pkg_resources.working_set.entries:
        pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setuptools_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s" % repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = dev
##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap the buildout project itself.

This is different from a normal boostrapping process because the
buildout egg itself is installed as a develop egg.
"""

import os, shutil, sys, subprocess

for d in 'eggs', 'develop-eggs', 'bin', 'parts':
    if not os.path.exists(d):
        os.mkdir(d)

if os.path.isdir('build'):
    shutil.rmtree('build')

######################################################################
# Make sure we have a relatively clean environment
try:
    import pkg_resources, setuptools
except ImportError:
    pass
else:
    raise SystemError(
        "Buildout development with a pre-installed setuptools or "
        "distribute is not supported.")

######################################################################
# Install distribute
ez = {}

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

# XXX use a more permanent ez_setup.py URL when available.
exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
            ).read(), ez)
ez['use_setuptools'](to_dir='eggs', download_delay=0)

import pkg_resources

######################################################################
# Install buildout
if subprocess.call(
    [sys.executable] +
    ['setup.py', '-q', 'develop', '-m', '-x', '-d', 'develop-eggs'],
    env=dict(os.environ, PYTHONPATH=os.path.dirname(pkg_resources.__file__))):
    raise RuntimeError("buildout build failed.")

pkg_resources.working_set.add_entry('src')

import zc.buildout.easy_install
zc.buildout.easy_install.scripts(
    ['zc.buildout'], pkg_resources.working_set , sys.executable, 'bin')

bin_buildout = os.path.join('bin', 'buildout')

if sys.platform.startswith('java'):
    # Jython needs the script to be called twice via sys.executable
    assert subprocess.Popen([sys.executable] + [bin_buildout]).wait() == 0

if sys.version_info < (2, 6):
    bin_buildout = [bin_buildout, '-c2.4.cfg']
sys.exit(subprocess.Popen(bin_buildout).wait())

########NEW FILE########
__FILENAME__ = buildout
##############################################################################
#
# Copyright (c) 2005-2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Buildout main script
"""

from zc.buildout.rmtree import rmtree
import zc.buildout.easy_install

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

try:
    from UserDict import DictMixin
except ImportError:
    from collections import MutableMapping as DictMixin

import zc.buildout.configparser
import copy
import datetime
import distutils.errors
import glob
import itertools
import logging
import os
import pkg_resources
import re
import shutil
import subprocess
import sys
import tempfile
import zc.buildout
import zc.buildout.download

def _print_options(sep=' ', end='\n', file=None):
    return sep, end, file

def print_(*args, **kw):
    sep, end, file = _print_options(**kw)
    if file is None:
        file = sys.stdout
    file.write(sep.join(map(str, args))+end)

realpath = zc.buildout.easy_install.realpath

pkg_resources_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match

class MissingOption(zc.buildout.UserError, KeyError):
    """A required option was missing.
    """

class MissingSection(zc.buildout.UserError, KeyError):
    """A required section is missing.
    """

    def __str__(self):
        return "The referenced section, %r, was not defined." % self.args[0]


def _annotate_section(section, note):
    for key in section:
        section[key] = (section[key], note)
    return section

def _annotate(data, note):
    for key in data:
        data[key] = _annotate_section(data[key], note)
    return data

def _print_annotate(data):
    sections = list(data.keys())
    sections.sort()
    print_()
    print_("Annotated sections")
    print_("="*len("Annotated sections"))
    for section in sections:
        print_()
        print_('[%s]' % section)
        keys = list(data[section].keys())
        keys.sort()
        for key in keys:
            value, notes = data[section][key]
            keyvalue = "%s= %s" % (key, value)
            print_(keyvalue)
            line = '   '
            for note in notes.split():
                if note == '[+]':
                    line = '+= '
                elif note == '[-]':
                    line = '-= '
                else:
                    print_(line, note)
                    line = '   '
    print_()


def _unannotate_section(section):
    for key in section:
        value, note = section[key]
        section[key] = value
    return section

def _unannotate(data):
    for key in data:
        data[key] = _unannotate_section(data[key])
    return data


def _format_picked_versions(picked_versions, required_by):
    output = ['[versions]']
    required_output = []
    for dist_, version in picked_versions:
        if dist_ in required_by:
            required_output.append('')
            required_output.append('# Required by:')
            for req_ in sorted(required_by[dist_]):
                required_output.append('# '+req_)
            target = required_output
        else:
            target = output
        target.append("%s = %s" % (dist_, version))
    output.extend(required_output)
    return output


_buildout_default_options = _annotate_section({
    'allow-hosts': '*',
    'allow-picked-versions': 'true',
    'bin-directory': 'bin',
    'develop-eggs-directory': 'develop-eggs',
    'eggs-directory': 'eggs',
    'executable': sys.executable,
    'find-links': '',
    'install-from-cache': 'false',
    'installed': '.installed.cfg',
    'log-format': '',
    'log-level': 'INFO',
    'newest': 'true',
    'offline': 'false',
    'parts-directory': 'parts',
    'prefer-final': 'true',
    'python': 'buildout',
    'show-picked-versions': 'false',
    'socket-timeout': '',
    'update-versions-file': '',
    'use-dependency-links': 'true',
    }, 'DEFAULT_VALUE')

class Buildout(DictMixin):

    def __init__(self, config_file, cloptions,
                 user_defaults=True,
                 command=None, args=()):

        __doing__ = 'Initializing.'

        # default options
        data = dict(buildout=_buildout_default_options.copy())
        self._buildout_dir = os.getcwd()

        if config_file and not _isurl(config_file):
            config_file = os.path.abspath(config_file)
            base = os.path.dirname(config_file)
            if not os.path.exists(config_file):
                if command == 'init':
                    self._init_config(config_file, args)
                elif command == 'setup':
                    # Sigh. This model of a buildout instance
                    # with methods is breaking down. :(
                    config_file = None
                    data['buildout']['directory'] = ('.', 'COMPUTED_VALUE')
                else:
                    raise zc.buildout.UserError(
                        "Couldn't open %s" % config_file)
            elif command == 'init':
                raise zc.buildout.UserError(
                    "%r already exists." % config_file)

            if config_file:
                data['buildout']['directory'] = (os.path.dirname(config_file),
                    'COMPUTED_VALUE')
        else:
            base = None


        cloptions = dict(
            (section, dict((option, (value, 'COMMAND_LINE_VALUE'))
                           for (_, option, value) in v))
            for (section, v) in itertools.groupby(sorted(cloptions),
                                                  lambda v: v[0])
            )
        override = cloptions.get('buildout', {}).copy()

        # load user defaults, which override defaults
        if user_defaults:
            if os.environ.get('BUILDOUT_HOME'):
                buildout_home = os.environ['BUILDOUT_HOME']
            else:
                buildout_home = os.path.join(
                    os.path.expanduser('~'), '.buildout')
            user_config = os.path.join(buildout_home, 'default.cfg')
            if os.path.exists(user_config):
                _update(data, _open(os.path.dirname(user_config), user_config,
                                    [], data['buildout'].copy(), override,
                                    set()))

        # load configuration files
        if config_file:
            _update(data, _open(os.path.dirname(config_file), config_file, [],
                                data['buildout'].copy(), override, set()))

        # apply command-line options
        _update(data, cloptions)

        # Set up versions section, if necessary
        if 'versions' not in data['buildout']:
            data['buildout']['versions'] = ('versions', 'DEFAULT_VALUE')
            if 'versions' not in data:
                data['versions'] = {}

        # Default versions:
        versions_section_name = data['buildout']['versions'][0]
        if versions_section_name:
            versions = data[versions_section_name]
        else:
            versions = {}
        versions.update(
            dict((k, (v, 'DEFAULT_VALUE'))
                 for (k, v) in (
                     # Prevent downgrading due to prefer-final:
                     ('zc.buildout',
                      '>='+pkg_resources.working_set.find(
                          pkg_resources.Requirement.parse('zc.buildout')
                          ).version),
                     # Use 2, even though not final
                     ('zc.recipe.egg', '>=2.0.0a3'),
                     )
                 if k not in versions
                 ))

        self._annotated = copy.deepcopy(data)
        self._raw = _unannotate(data)
        self._data = {}
        self._parts = []

        # provide some defaults before options are parsed
        # because while parsing options those attributes might be
        # used already (Gottfried Ganssauge)
        buildout_section = data['buildout']

        # Try to make sure we have absolute paths for standard
        # directories. We do this before doing substitutions, in case
        # a one of these gets read by another section.  If any
        # variable references are used though, we leave it as is in
        # _buildout_path.
        if 'directory' in buildout_section:
            self._buildout_dir = buildout_section['directory']
            for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
                d = self._buildout_path(buildout_section[name+'-directory'])
                buildout_section[name+'-directory'] = d

        # Attributes on this buildout object shouldn't be used by
        # recipes in their __init__.  It can cause bugs, because the
        # recipes will be instantiated below (``options = self['buildout']``)
        # before this has completed initializing.  These attributes are
        # left behind for legacy support but recipe authors should
        # beware of using them.  A better practice is for a recipe to
        # use the buildout['buildout'] options.
        links = buildout_section['find-links']
        self._links = links and links.split() or ()
        allow_hosts = buildout_section['allow-hosts'].split('\n')
        self._allow_hosts = tuple([host.strip() for host in allow_hosts
                                   if host.strip() != ''])
        self._logger = logging.getLogger('zc.buildout')
        self.offline = bool_option(buildout_section, 'offline')
        self.newest = ((not self.offline) and
                       bool_option(buildout_section, 'newest')
                       )

        ##################################################################
        ## WARNING!!!
        ## ALL ATTRIBUTES MUST HAVE REASONABLE DEFAULTS AT THIS POINT
        ## OTHERWISE ATTRIBUTEERRORS MIGHT HAPPEN ANY TIME FROM RECIPES.
        ## RECIPES SHOULD GENERALLY USE buildout['buildout'] OPTIONS, NOT
        ## BUILDOUT ATTRIBUTES.
        ##################################################################
        # initialize some attrs and buildout directories.
        options = self['buildout']

        # now reinitialize
        links = options.get('find-links', '')
        self._links = links and links.split() or ()

        allow_hosts = options['allow-hosts'].split('\n')
        self._allow_hosts = tuple([host.strip() for host in allow_hosts
                                   if host.strip() != ''])

        self._buildout_dir = options['directory']

        # Make sure we have absolute paths for standard directories.  We do this
        # a second time here in case someone overrode these in their configs.
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self._buildout_path(options[name+'-directory'])
            options[name+'-directory'] = d

        if options['installed']:
            options['installed'] = os.path.join(options['directory'],
                                                options['installed'])

        self._setup_logging()
        self._setup_socket_timeout()

        # finish w versions
        if versions_section_name:
            # refetching section name just to avoid a warning
            versions = self[versions_section_name]
        else:
            # remove annotations
            versions = dict((k, v[0]) for (k, v) in versions.items())
        options['versions'] # refetching section name just to avoid a warning
        self.versions = versions
        zc.buildout.easy_install.default_versions(versions)

        zc.buildout.easy_install.prefer_final(
            bool_option(options, 'prefer-final'))
        zc.buildout.easy_install.use_dependency_links(
            bool_option(options, 'use-dependency-links'))
        zc.buildout.easy_install.allow_picked_versions(
                bool_option(options, 'allow-picked-versions'))
        self.show_picked_versions = bool_option(options,
                                                'show-picked-versions')
        self.update_versions_file = options['update-versions-file']
        zc.buildout.easy_install.store_required_by(self.show_picked_versions or
                                                   self.update_versions_file)

        download_cache = options.get('download-cache')
        if download_cache:
            download_cache = os.path.join(options['directory'], download_cache)
            if not os.path.isdir(download_cache):
                raise zc.buildout.UserError(
                    'The specified download cache:\n'
                    '%r\n'
                    "Doesn't exist.\n"
                    % download_cache)
            download_cache = os.path.join(download_cache, 'dist')
            if not os.path.isdir(download_cache):
                os.mkdir(download_cache)

            zc.buildout.easy_install.download_cache(download_cache)

        if bool_option(options, 'install-from-cache'):
            if self.offline:
                raise zc.buildout.UserError(
                    "install-from-cache can't be used with offline mode.\n"
                    "Nothing is installed, even from cache, in offline\n"
                    "mode, which might better be called 'no-install mode'.\n"
                    )
            zc.buildout.easy_install.install_from_cache(True)

        # "Use" each of the defaults so they aren't reported as unused options.
        for name in _buildout_default_options:
            options[name]

        # Do the same for extends-cache which is not among the defaults but
        # wasn't recognized as having been used since it was used before
        # tracking was turned on.
        options.get('extends-cache')

        os.chdir(options['directory'])

    def _buildout_path(self, name):
        if '${' in name:
            return name
        return os.path.join(self._buildout_dir, name)

    def bootstrap(self, args):
        __doing__ = 'Bootstrapping.'

        self._setup_directories()

        # Now copy buildout and setuptools eggs, and record destination eggs:
        entries = []
        for name in 'setuptools', 'zc.buildout':
            r = pkg_resources.Requirement.parse(name)
            dist = pkg_resources.working_set.find(r)
            if dist.precedence == pkg_resources.DEVELOP_DIST:
                dest = os.path.join(self['buildout']['develop-eggs-directory'],
                                    name+'.egg-link')
                open(dest, 'w').write(dist.location)
                entries.append(dist.location)
            else:
                dest = os.path.join(self['buildout']['eggs-directory'],
                                    os.path.basename(dist.location))
                entries.append(dest)
                if not os.path.exists(dest):
                    if os.path.isdir(dist.location):
                        shutil.copytree(dist.location, dest)
                    else:
                        shutil.copy2(dist.location, dest)

        # Create buildout script
        ws = pkg_resources.WorkingSet(entries)
        ws.require('zc.buildout')
        options = self['buildout']
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            self['buildout']['bin-directory'],
            relative_paths = (
                bool_option(options, 'relative-paths', False)
                and options['directory']
                or ''),
            )

    def _init_config(self, config_file, args):
        print_('Creating %r.' % config_file)
        f = open(config_file, 'w')
        sep = re.compile(r'[\\/]')
        if args:
            eggs = '\n  '.join(a for a in args if not sep.search(a))
            sepsub = os.path.sep == '/' and '/' or re.escape(os.path.sep)
            paths = '\n  '.join(
                sep.sub(sepsub, a)
                for a in args if sep.search(a))
            f.write('[buildout]\n'
                    'parts = py\n'
                    '\n'
                    '[py]\n'
                    'recipe = zc.recipe.egg\n'
                    'interpreter = py\n'
                    'eggs =\n'
                    )
            if eggs:
                f.write('  %s\n' % eggs)
            if paths:
                f.write('extra-paths =\n  %s\n' % paths)
                for p in [a for a in args if sep.search(a)]:
                    if not os.path.exists(p):
                        os.mkdir(p)

        else:
            f.write('[buildout]\nparts =\n')
        f.close()

    def init(self, args):
        self.bootstrap(())
        if args:
            self.install(())

    def install(self, install_args):
        __doing__ = 'Installing.'

        self._load_extensions()
        self._setup_directories()

        # Add develop-eggs directory to path so that it gets searched
        # for eggs:
        sys.path.insert(0, self['buildout']['develop-eggs-directory'])

        # Check for updates. This could cause the process to be restarted
        self._maybe_upgrade()

        # load installed data
        (installed_part_options, installed_exists
         )= self._read_installed_part_options()

        # Remove old develop eggs
        self._uninstall(
            installed_part_options['buildout'].get(
                'installed_develop_eggs', '')
            )

        # Build develop eggs
        installed_develop_eggs = self._develop()
        installed_part_options['buildout']['installed_develop_eggs'
                                           ] = installed_develop_eggs

        if installed_exists:
            self._update_installed(
                installed_develop_eggs=installed_develop_eggs)

        # get configured and installed part lists
        conf_parts = self['buildout']['parts']
        conf_parts = conf_parts and conf_parts.split() or []
        installed_parts = installed_part_options['buildout']['parts']
        installed_parts = installed_parts and installed_parts.split() or []

        if install_args:
            install_parts = install_args
            uninstall_missing = False
        else:
            install_parts = conf_parts
            uninstall_missing = True

        # load and initialize recipes
        [self[part]['recipe'] for part in install_parts]
        if not install_args:
            install_parts = self._parts

        if self._log_level < logging.DEBUG:
            sections = list(self)
            sections.sort()
            print_()
            print_('Configuration data:')
            for section in sorted(self._data):
                _save_options(section, self[section], sys.stdout)
            print_()


        # compute new part recipe signatures
        self._compute_part_signatures(install_parts)

        # uninstall parts that are no-longer used or who's configs
        # have changed
        for part in reversed(installed_parts):
            if part in install_parts:
                old_options = installed_part_options[part].copy()
                installed_files = old_options.pop('__buildout_installed__')
                new_options = self.get(part)
                if old_options == new_options:
                    # The options are the same, but are all of the
                    # installed files still there?  If not, we should
                    # reinstall.
                    if not installed_files:
                        continue
                    for f in installed_files.split('\n'):
                        if not os.path.exists(self._buildout_path(f)):
                            break
                    else:
                        continue

                # output debugging info
                if self._logger.getEffectiveLevel() < logging.DEBUG:
                    for k in old_options:
                        if k not in new_options:
                            self._logger.debug("Part %s, dropped option %s.",
                                               part, k)
                        elif old_options[k] != new_options[k]:
                            self._logger.debug(
                                "Part %s, option %s changed:\n%r != %r",
                                part, k, new_options[k], old_options[k],
                                )
                    for k in new_options:
                        if k not in old_options:
                            self._logger.debug("Part %s, new option %s.",
                                               part, k)

            elif not uninstall_missing:
                continue

            self._uninstall_part(part, installed_part_options)
            installed_parts = [p for p in installed_parts if p != part]

            if installed_exists:
                self._update_installed(parts=' '.join(installed_parts))

        # Check for unused buildout options:
        _check_for_unused_options_in_section(self, 'buildout')

        # install new parts
        for part in install_parts:
            signature = self[part].pop('__buildout_signature__')
            saved_options = self[part].copy()
            recipe = self[part].recipe
            if part in installed_parts: # update
                need_to_save_installed = False
                __doing__ = 'Updating %s.', part
                self._logger.info(*__doing__)
                old_options = installed_part_options[part]
                old_installed_files = old_options['__buildout_installed__']

                try:
                    update = recipe.update
                except AttributeError:
                    update = recipe.install
                    self._logger.warning(
                        "The recipe for %s doesn't define an update "
                        "method. Using its install method.",
                        part)

                try:
                    installed_files = self[part]._call(update)
                except:
                    installed_parts.remove(part)
                    self._uninstall(old_installed_files)
                    if installed_exists:
                        self._update_installed(
                            parts=' '.join(installed_parts))
                    raise

                old_installed_files = old_installed_files.split('\n')
                if installed_files is None:
                    installed_files = old_installed_files
                else:
                    if isinstance(installed_files, str):
                        installed_files = [installed_files]
                    else:
                        installed_files = list(installed_files)

                    need_to_save_installed = [
                        p for p in installed_files
                        if p not in old_installed_files]

                    if need_to_save_installed:
                        installed_files = (old_installed_files
                                           + need_to_save_installed)

            else: # install
                need_to_save_installed = True
                __doing__ = 'Installing %s.', part
                self._logger.info(*__doing__)
                installed_files = self[part]._call(recipe.install)
                if installed_files is None:
                    self._logger.warning(
                        "The %s install returned None.  A path or "
                        "iterable os paths should be returned.",
                        part)
                    installed_files = ()
                elif isinstance(installed_files, str):
                    installed_files = [installed_files]
                else:
                    installed_files = list(installed_files)

            installed_part_options[part] = saved_options
            saved_options['__buildout_installed__'
                          ] = '\n'.join(installed_files)
            saved_options['__buildout_signature__'] = signature

            installed_parts = [p for p in installed_parts if p != part]
            installed_parts.append(part)
            _check_for_unused_options_in_section(self, part)

            if need_to_save_installed:
                installed_part_options['buildout']['parts'] = (
                    ' '.join(installed_parts))
                self._save_installed_options(installed_part_options)
                installed_exists = True
            else:
                assert installed_exists
                self._update_installed(parts=' '.join(installed_parts))

        if installed_develop_eggs:
            if not installed_exists:
                self._save_installed_options(installed_part_options)
        elif (not installed_parts) and installed_exists:
            os.remove(self['buildout']['installed'])

        if self.show_picked_versions or self.update_versions_file:
            self._print_picked_versions()
        self._unload_extensions()

    def _update_installed(self, **buildout_options):
        installed = self['buildout']['installed']
        f = open(installed, 'a')
        f.write('\n[buildout]\n')
        for option, value in list(buildout_options.items()):
            _save_option(option, value, f)
        f.close()

    def _uninstall_part(self, part, installed_part_options):
        # uninstall part
        __doing__ = 'Uninstalling %s.', part
        self._logger.info(*__doing__)

        # run uuinstall recipe
        recipe, entry = _recipe(installed_part_options[part])
        try:
            uninstaller = _install_and_load(
                recipe, 'zc.buildout.uninstall', entry, self)
            self._logger.info('Running uninstall recipe.')
            uninstaller(part, installed_part_options[part])
        except (ImportError, pkg_resources.DistributionNotFound):
            pass

        # remove created files and directories
        self._uninstall(
            installed_part_options[part]['__buildout_installed__'])

    def _setup_directories(self):
        __doing__ = 'Setting up buildout directories'

        # Create buildout directories
        for name in ('bin', 'parts', 'eggs', 'develop-eggs'):
            d = self['buildout'][name+'-directory']
            if not os.path.exists(d):
                self._logger.info('Creating directory %r.', d)
                os.mkdir(d)

    def _develop(self):
        """Install sources by running setup.py develop on them
        """
        __doing__ = 'Processing directories listed in the develop option'

        develop = self['buildout'].get('develop')
        if not develop:
            return ''

        dest = self['buildout']['develop-eggs-directory']
        old_files = os.listdir(dest)

        env = dict(os.environ, PYTHONPATH=pkg_resources_loc)
        here = os.getcwd()
        try:
            try:
                for setup in develop.split():
                    setup = self._buildout_path(setup)
                    files = glob.glob(setup)
                    if not files:
                        self._logger.warn("Couldn't develop %r (not found)",
                                          setup)
                    else:
                        files.sort()
                    for setup in files:
                        self._logger.info("Develop: %r", setup)
                        __doing__ = 'Processing develop directory %r.', setup
                        zc.buildout.easy_install.develop(setup, dest)
            except:
                # if we had an error, we need to roll back changes, by
                # removing any files we created.
                self._sanity_check_develop_eggs_files(dest, old_files)
                self._uninstall('\n'.join(
                    [os.path.join(dest, f)
                     for f in os.listdir(dest)
                     if f not in old_files
                     ]))
                raise

            else:
                self._sanity_check_develop_eggs_files(dest, old_files)
                return '\n'.join([os.path.join(dest, f)
                                  for f in os.listdir(dest)
                                  if f not in old_files
                                  ])

        finally:
            os.chdir(here)


    def _sanity_check_develop_eggs_files(self, dest, old_files):
        for f in os.listdir(dest):
            if f in old_files:
                continue
            if not (os.path.isfile(os.path.join(dest, f))
                    and f.endswith('.egg-link')):
                self._logger.warning(
                    "Unexpected entry, %r, in develop-eggs directory.", f)

    def _compute_part_signatures(self, parts):
        # Compute recipe signature and add to options
        for part in parts:
            options = self.get(part)
            if options is None:
                options = self[part] = {}
            recipe, entry = _recipe(options)
            req = pkg_resources.Requirement.parse(recipe)
            sig = _dists_sig(pkg_resources.working_set.resolve([req]))
            options['__buildout_signature__'] = ' '.join(sig)

    def _read_installed_part_options(self):
        old = self['buildout']['installed']
        if old and os.path.isfile(old):
            fp = open(old)
            sections = zc.buildout.configparser.parse(fp, old)
            fp.close()
            result = {}
            for section, options in sections.items():
                for option, value in options.items():
                    if '%(' in value:
                        for k, v in _spacey_defaults:
                            value = value.replace(k, v)
                        options[option] = value
                result[section] = self.Options(self, section, options)

            return result, True
        else:
            return ({'buildout': self.Options(self, 'buildout', {'parts': ''})},
                    False,
                    )

    def _uninstall(self, installed):
        for f in installed.split('\n'):
            if not f:
                continue
            f = self._buildout_path(f)
            if os.path.isdir(f):
                rmtree(f)
            elif os.path.isfile(f):
                try:
                    os.remove(f)
                except OSError:
                    if not (
                        sys.platform == 'win32' and
                        (realpath(os.path.join(os.path.dirname(sys.argv[0]),
                                               'buildout.exe'))
                         ==
                         realpath(f)
                         )
                        # Sigh. This is the executable used to run the buildout
                        # and, of course, it's in use. Leave it.
                        ):
                        raise

    def _install(self, part):
        options = self[part]
        recipe, entry = _recipe(options)
        recipe_class = pkg_resources.load_entry_point(
            recipe, 'zc.buildout', entry)
        installed = recipe_class(self, part, options).install()
        if installed is None:
            installed = []
        elif isinstance(installed, str):
            installed = [installed]
        base = self._buildout_path('')
        installed = [d.startswith(base) and d[len(base):] or d
                     for d in installed]
        return ' '.join(installed)


    def _save_installed_options(self, installed_options):
        installed = self['buildout']['installed']
        if not installed:
            return
        f = open(installed, 'w')
        _save_options('buildout', installed_options['buildout'], f)
        for part in installed_options['buildout']['parts'].split():
            print_(file=f)
            _save_options(part, installed_options[part], f)
        f.close()

    def _error(self, message, *args):
        raise zc.buildout.UserError(message % args)

    def _setup_socket_timeout(self):
        timeout = self['buildout']['socket-timeout']
        if timeout != '':
            try:
                timeout = int(timeout)
                import socket
                self._logger.info(
                    'Setting socket time out to %d seconds.', timeout)
                socket.setdefaulttimeout(timeout)
            except ValueError:
                self._logger.warning("Default socket timeout is used !\n"
                    "Value in configuration is not numeric: [%s].\n",
                    timeout)

    def _setup_logging(self):
        root_logger = logging.getLogger()
        self._logger = logging.getLogger('zc.buildout')
        handler = logging.StreamHandler(sys.stdout)
        log_format = self['buildout']['log-format']
        if not log_format:
            # No format specified. Use different formatter for buildout
            # and other modules, showing logger name except for buildout
            log_format = '%(name)s: %(message)s'
            buildout_handler = logging.StreamHandler(sys.stdout)
            buildout_handler.setFormatter(logging.Formatter('%(message)s'))
            self._logger.propagate = False
            self._logger.addHandler(buildout_handler)

        handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(handler)

        level = self['buildout']['log-level']
        if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            level = getattr(logging, level)
        else:
            try:
                level = int(level)
            except ValueError:
                self._error("Invalid logging level %s", level)
        verbosity = self['buildout'].get('verbosity', 0)
        try:
            verbosity = int(verbosity)
        except ValueError:
            self._error("Invalid verbosity %s", verbosity)

        level -= verbosity
        root_logger.setLevel(level)
        self._log_level = level

    def _maybe_upgrade(self):
        # See if buildout or setuptools need to be upgraded.
        # If they do, do the upgrade and restart the buildout process.
        __doing__ = 'Checking for upgrades.'

        if not self.newest:
            return

        ws = zc.buildout.easy_install.install(
            ('zc.buildout', 'setuptools'),
            self['buildout']['eggs-directory'],
            links = self['buildout'].get('find-links', '').split(),
            index = self['buildout'].get('index'),
            path = [self['buildout']['develop-eggs-directory']],
            allow_hosts = self._allow_hosts
            )

        upgraded = []
        for project in 'zc.buildout', 'setuptools':
            req = pkg_resources.Requirement.parse(project)
            project_location = pkg_resources.working_set.find(req).location
            if ws.find(req).location != project_location:
                upgraded.append(ws.find(req))

        if not upgraded:
            return

        __doing__ = 'Upgrading.'

        should_run = realpath(
            os.path.join(os.path.abspath(self['buildout']['bin-directory']),
                         'buildout')
            )
        if sys.platform == 'win32':
            should_run += '-script.py'

        if (realpath(os.path.abspath(sys.argv[0])) != should_run):
            self._logger.debug("Running %r.", realpath(sys.argv[0]))
            self._logger.debug("Local buildout is %r.", should_run)
            self._logger.warn("Not upgrading because not running a local "
                              "buildout command.")
            return

        self._logger.info("Upgraded:\n  %s;\nrestarting.",
                          ",\n  ".join([("%s version %s"
                                       % (dist.project_name, dist.version)
                                       )
                                      for dist in upgraded
                                      ]
                                     ),
                          )

        # the new dist is different, so we've upgraded.
        # Update the scripts and return True
        options = self['buildout']
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            self['buildout']['bin-directory'],
            relative_paths = (
                bool_option(options, 'relative-paths', False)
                and options['directory']
                or ''),
            )

        # Restart
        args = sys.argv[:]
        if not __debug__:
            args.insert(0, '-O')
        args.insert(0, sys.executable)
        sys.exit(subprocess.call(args))

    def _load_extensions(self):
        __doing__ = 'Loading extensions.'
        specs = self['buildout'].get('extensions', '').split()
        for superceded_extension in ['buildout-versions',
                                     'buildout.dumppickedversions']:
            if superceded_extension in specs:
                msg = ("Buildout now includes 'buildout-versions' (and part "
                       "of the older 'buildout.dumppickedversions').\n"
                       "Remove the extension from your configuration and "
                       "look at the 'show-picked-versions' option in "
                       "buildout's documentation.")
                raise zc.buildout.UserError(msg)
        if specs:
            path = [self['buildout']['develop-eggs-directory']]
            if self.offline:
                dest = None
                path.append(self['buildout']['eggs-directory'])
            else:
                dest = self['buildout']['eggs-directory']
                if not os.path.exists(dest):
                    self._logger.info('Creating directory %r.', dest)
                    os.mkdir(dest)

            zc.buildout.easy_install.install(
                specs, dest, path=path,
                working_set=pkg_resources.working_set,
                links = self['buildout'].get('find-links', '').split(),
                index = self['buildout'].get('index'),
                newest=self.newest, allow_hosts=self._allow_hosts)

            # Clear cache because extensions might now let us read pages we
            # couldn't read before.
            zc.buildout.easy_install.clear_index_cache()

            for ep in pkg_resources.iter_entry_points('zc.buildout.extension'):
                ep.load()(self)

    def _unload_extensions(self):
        __doing__ = 'Unloading extensions.'
        specs = self['buildout'].get('extensions', '').split()
        if specs:
            for ep in pkg_resources.iter_entry_points(
                'zc.buildout.unloadextension'):
                ep.load()(self)

    def _print_picked_versions(self):
        picked_versions, required_by = (zc.buildout.easy_install
                                        .get_picked_versions())
        if not picked_versions:
            # Don't print empty output.
            return

        output = _format_picked_versions(picked_versions, required_by)

        if self.show_picked_versions:
            print_("Versions had to be automatically picked.")
            print_("The following part definition lists the versions picked:")
            print_('\n'.join(output))

        if self.update_versions_file:
            # Write to the versions file.
            if os.path.exists(self.update_versions_file):
                output[:1] = [
                    '',
                    '# Added by buildout at %s' % datetime.datetime.now()
                ]
            output.append('')
            f = open(self.update_versions_file, 'a')
            f.write(('\n'.join(output)))
            f.close()
            print_("Picked versions have been written to " +
                   self.update_versions_file)

    def setup(self, args):
        if not args:
            raise zc.buildout.UserError(
                "The setup command requires the path to a setup script or \n"
                "directory containing a setup script, and its arguments."
                )
        setup = args.pop(0)
        if os.path.isdir(setup):
            setup = os.path.join(setup, 'setup.py')

        self._logger.info("Running setup script %r.", setup)
        setup = os.path.abspath(setup)

        fd, tsetup = tempfile.mkstemp()
        try:
            os.write(fd, (zc.buildout.easy_install.runsetup_template % dict(
                setuptools=pkg_resources_loc,
                setupdir=os.path.dirname(setup),
                setup=setup,
                __file__ = setup,
                )).encode())
            args = [sys.executable, tsetup] + args
            zc.buildout.easy_install.call_subprocess(args)
        finally:
            os.close(fd)
            os.remove(tsetup)

    runsetup = setup # backward compat.

    def annotate(self, args=None):
        _print_annotate(self._annotated)

    def print_options(self):
        for section in sorted(self._data):
            if section == 'buildout' or section == self['buildout']['versions']:
                continue
            print_('['+section+']')
            for k, v in sorted(self._data[section].items()):
                if '\n' in v:
                    v = '\n  ' + v.replace('\n', '\n  ')
                else:
                    v = ' '+v
                print_("%s =%s" % (k, v))

    def __getitem__(self, section):
        __doing__ = 'Getting section %s.', section
        try:
            return self._data[section]
        except KeyError:
            pass

        try:
            data = self._raw[section]
        except KeyError:
            raise MissingSection(section)

        options = self.Options(self, section, data)
        self._data[section] = options
        options._initialize()
        return options

    def __setitem__(self, name, data):
        if name in self._raw:
            raise KeyError("Section already exists", name)
        self._raw[name] = dict((k, str(v)) for (k, v) in data.items())
        self[name] # Add to parts

    def parse(self, data):
        try:
            from cStringIO import StringIO
        except ImportError:
            from io import StringIO
        import textwrap

        sections = zc.buildout.configparser.parse(
            StringIO(textwrap.dedent(data)), '', _default_globals)
        for name in sections:
            if name in self._raw:
                raise KeyError("Section already exists", name)
            self._raw[name] = dict((k, str(v))
                                   for (k, v) in sections[name].items())

        for name in sections:
            self[name] # Add to parts

    def __delitem__(self, key):
        raise NotImplementedError('__delitem__')

    def keys(self):
        return list(self._raw.keys())

    def __iter__(self):
        return iter(self._raw)

    def __len__(self):
        return len(self._raw)


def _install_and_load(spec, group, entry, buildout):
    __doing__ = 'Loading recipe %r.', spec
    try:
        req = pkg_resources.Requirement.parse(spec)

        buildout_options = buildout['buildout']
        if pkg_resources.working_set.find(req) is None:
            __doing__ = 'Installing recipe %s.', spec
            if buildout.offline:
                dest = None
                path = [buildout_options['develop-eggs-directory'],
                        buildout_options['eggs-directory'],
                        ]
            else:
                dest = buildout_options['eggs-directory']
                path = [buildout_options['develop-eggs-directory']]

            zc.buildout.easy_install.install(
                [spec], dest,
                links=buildout._links,
                index=buildout_options.get('index'),
                path=path,
                working_set=pkg_resources.working_set,
                newest=buildout.newest,
                allow_hosts=buildout._allow_hosts
                )

        __doing__ = 'Loading %s recipe entry %s:%s.', group, spec, entry
        return pkg_resources.load_entry_point(
            req.project_name, group, entry)

    except Exception:
        v = sys.exc_info()[1]
        buildout._logger.log(
            1,
            "Could't load %s entry point %s\nfrom %s:\n%s.",
            group, entry, spec, v)
        raise

class Options(DictMixin):

    def __init__(self, buildout, section, data):
        self.buildout = buildout
        self.name = section
        self._raw = data
        self._cooked = {}
        self._data = {}

    def _initialize(self):
        name = self.name
        __doing__ = 'Initializing section %s.', name

        if '<' in self._raw:
            self._raw = self._do_extend_raw(name, self._raw, [])

        # force substitutions
        for k, v in sorted(self._raw.items()):
            if '${' in v:
                self._dosub(k, v)

        if name == 'buildout':
            return # buildout section can never be a part

        if self.get('recipe'):
            self.initialize()
            self.buildout._parts.append(name)

    def initialize(self):
        reqs, entry = _recipe(self._data)
        buildout = self.buildout
        recipe_class = _install_and_load(reqs, 'zc.buildout', entry, buildout)

        name = self.name
        self.recipe = recipe_class(buildout, name, self)

    def _do_extend_raw(self, name, data, doing):
        if name == 'buildout':
            return data
        if name in doing:
            raise zc.buildout.UserError("Infinite extending loop %r" % name)
        doing.append(name)
        try:
            to_do = data.get('<', None)
            if to_do is None:
                return data
            __doing__ = 'Loading input sections for %r', name

            result = {}
            for iname in to_do.split('\n'):
                iname = iname.strip()
                if not iname:
                    continue
                raw = self.buildout._raw.get(iname)
                if raw is None:
                    raise zc.buildout.UserError("No section named %r" % iname)
                result.update(self._do_extend_raw(iname, raw, doing))

            result.update(data)
            result.pop('<', None)
            return result
        finally:
            assert doing.pop() == name

    def _dosub(self, option, v):
        __doing__ = 'Getting option %s:%s.', self.name, option
        seen = [(self.name, option)]
        v = '$$'.join([self._sub(s, seen) for s in v.split('$$')])
        self._cooked[option] = v

    def get(self, option, default=None, seen=None):
        try:
            return self._data[option]
        except KeyError:
            pass

        v = self._cooked.get(option)
        if v is None:
            v = self._raw.get(option)
            if v is None:
                return default

        __doing__ = 'Getting option %s:%s.', self.name, option

        if '${' in v:
            key = self.name, option
            if seen is None:
                seen = [key]
            elif key in seen:
                raise zc.buildout.UserError(
                    "Circular reference in substitutions.\n"
                    )
            else:
                seen.append(key)
            v = '$$'.join([self._sub(s, seen) for s in v.split('$$')])
            seen.pop()

        self._data[option] = v
        return v

    _template_split = re.compile('([$]{[^}]*})').split
    _simple = re.compile('[-a-zA-Z0-9 ._]+$').match
    _valid = re.compile('\${[-a-zA-Z0-9 ._]*:[-a-zA-Z0-9 ._]+}$').match
    def _sub(self, template, seen):
        value = self._template_split(template)
        subs = []
        for ref in value[1::2]:
            s = tuple(ref[2:-1].split(':'))
            if not self._valid(ref):
                if len(s) < 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "doesn't contain a colon."
                                                % ref)
                if len(s) > 2:
                    raise zc.buildout.UserError("The substitution, %s,\n"
                                                "has too many colons."
                                                % ref)
                if not self._simple(s[0]):
                    raise zc.buildout.UserError(
                        "The section name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)
                if not self._simple(s[1]):
                    raise zc.buildout.UserError(
                        "The option name in substitution, %s,\n"
                        "has invalid characters."
                        % ref)

            section, option = s
            if not section:
                section = self.name
            v = self.buildout[section].get(option, None, seen)
            if v is None:
                if option == '_buildout_section_name_':
                    v = self.name
                else:
                    raise MissingOption("Referenced option does not exist:",
                                        section, option)
            subs.append(v)
        subs.append('')

        return ''.join([''.join(v) for v in zip(value[::2], subs)])

    def __getitem__(self, key):
        try:
            return self._data[key]
        except KeyError:
            pass

        v = self.get(key)
        if v is None:
            raise MissingOption("Missing option: %s:%s" % (self.name, key))
        return v

    def __setitem__(self, option, value):
        if not isinstance(value, str):
            raise TypeError('Option values must be strings', value)
        self._data[option] = value

    def __delitem__(self, key):
        if key in self._raw:
            del self._raw[key]
            if key in self._data:
                del self._data[key]
            if key in self._cooked:
                del self._cooked[key]
        elif key in self._data:
            del self._data[key]
        else:
            raise KeyError(key)

    def keys(self):
        raw = self._raw
        return list(self._raw) + [k for k in self._data if k not in raw]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def copy(self):
        result = self._raw.copy()
        result.update(self._cooked)
        result.update(self._data)
        return result

    def _call(self, f):
        buildout_directory = self.buildout['buildout']['directory']
        self._created = []
        try:
            try:
                os.chdir(buildout_directory)
                return f()
            except:
                for p in self._created:
                    if os.path.isdir(p):
                        rmtree(p)
                    elif os.path.isfile(p):
                        os.remove(p)
                    else:
                        self.buildout._logger.warn("Couldn't clean up %r.", p)
                raise
        finally:
            self._created = None
            os.chdir(buildout_directory)

    def created(self, *paths):
        try:
            self._created.extend(paths)
        except AttributeError:
            raise TypeError(
                "Attempt to register a created path while not installing",
                self.name)
        return self._created

    def __repr__(self):
        return repr(dict(self))

Buildout.Options = Options

_spacey_nl = re.compile('[ \t\r\f\v]*\n[ \t\r\f\v\n]*'
                        '|'
                        '^[ \t\r\f\v]+'
                        '|'
                        '[ \t\r\f\v]+$'
                        )

_spacey_defaults = [
    ('%(__buildout_space__)s',   ' '),
    ('%(__buildout_space_n__)s', '\n'),
    ('%(__buildout_space_r__)s', '\r'),
    ('%(__buildout_space_f__)s', '\f'),
    ('%(__buildout_space_v__)s', '\v'),
    ]

def _quote_spacey_nl(match):
    match = match.group(0).split('\n', 1)
    result = '\n\t'.join(
        [(s
          .replace(' ', '%(__buildout_space__)s')
          .replace('\r', '%(__buildout_space_r__)s')
          .replace('\f', '%(__buildout_space_f__)s')
          .replace('\v', '%(__buildout_space_v__)s')
          .replace('\n', '%(__buildout_space_n__)s')
          )
         for s in match]
        )
    return result

def _save_option(option, value, f):
    value = _spacey_nl.sub(_quote_spacey_nl, value)
    if value.startswith('\n\t'):
        value = '%(__buildout_space_n__)s' + value[2:]
    if value.endswith('\n\t'):
        value = value[:-2] + '%(__buildout_space_n__)s'
    print_(option, '=', value, file=f)

def _save_options(section, options, f):
    print_('[%s]' % section, file=f)
    items = list(options.items())
    items.sort()
    for option, value in items:
        _save_option(option, value, f)

def _default_globals():
    """Return a mapping of default and precomputed expressions.
    These default expressions are convenience defaults available when eveluating
    section headers expressions.
    NB: this is wrapped in a function so that the computing of these expressions
    is lazy and done only if needed (ie if there is at least one section with 
    an expression) because the computing of some of these expressions can be 
    expensive. 
    """
    # partially derived or inspired from its.py
    # Copyright (c) 2012, Kenneth Reitz All rights reserved.
    # Redistribution and use in source and binary forms, with or without modification,
    # are permitted provided that the following conditions are met:
    # Redistributions of source code must retain the above copyright notice, this list
    # of conditions and the following disclaimer. Redistributions in binary form must
    # reproduce the above copyright notice, this list of conditions and the following
    # disclaimer in the documentation and/or other materials provided with the
    # distribution. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
    # CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    # LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
    # PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
    # CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    # OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
    # IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
    # OF SUCH DAMAGE.

    # default available modules, explicitly re-imported locally here on purpose
    import sys
    import os
    import platform
    import re

    globals_defs = {'sys': sys, 'os': os, 'platform': platform, 're': re,}

    # major python major_python_versions as python2 and python3
    major_python_versions = tuple(map(str, platform.python_version_tuple()))
    globals_defs.update({'python2': major_python_versions[0] == '2',
                         'python3': major_python_versions[0] == '3'})

    # minor python major_python_versions as python24, python25 ... python36
    minor_python_versions = ('24', '25', '26', '27',
                             '30', '31', '32', '33', '34', '35', '36')
    for v in minor_python_versions:
        globals_defs['python' + v] = ''.join(major_python_versions[:2]) == v

    # interpreter type
    sys_version = sys.version.lower()
    pypy = 'pypy' in sys_version
    jython = 'java' in sys_version
    ironpython ='iron' in sys_version
    # assume CPython, if nothing else.
    cpython = not any((pypy, jython, ironpython,))
    globals_defs.update({'cpython': cpython,
                         'pypy': pypy,
                         'jython': jython,
                         'ironpython': ironpython})

    # operating system
    sys_platform = str(sys.platform).lower()
    globals_defs.update({'linux': 'linux' in sys_platform,
                         'windows': 'win32' in sys_platform,
                         'cygwin': 'cygwin' in sys_platform,
                         'solaris': 'sunos' in sys_platform,
                         'macosx': 'darwin' in sys_platform,
                         'posix': 'posix' in os.name.lower()})

    #bits and endianness
    import struct
    void_ptr_size = struct.calcsize('P') * 8
    globals_defs.update({'bits32': void_ptr_size == 32,
                         'bits64': void_ptr_size == 64,
                         'little_endian': sys.byteorder == 'little',
                         'big_endian': sys.byteorder == 'big'})

    return globals_defs

def _open(base, filename, seen, dl_options, override, downloaded):
    """Open a configuration file and return the result as a dictionary,

    Recursively open other files based on buildout options found.
    """
    _update_section(dl_options, override)
    _dl_options = _unannotate_section(dl_options.copy())
    newest = bool_option(_dl_options, 'newest', 'false')
    fallback = newest and not (filename in downloaded)
    download = zc.buildout.download.Download(
        _dl_options, cache=_dl_options.get('extends-cache'),
        fallback=fallback, hash_name=True)
    is_temp = False
    if _isurl(filename):
        path, is_temp = download(filename)
        fp = open(path)
        base = filename[:filename.rfind('/')]
    elif _isurl(base):
        if os.path.isabs(filename):
            fp = open(filename)
            base = os.path.dirname(filename)
        else:
            filename = base + '/' + filename
            path, is_temp = download(filename)
            fp = open(path)
            base = filename[:filename.rfind('/')]
    else:
        filename = os.path.join(base, filename)
        fp = open(filename)
        base = os.path.dirname(filename)
    downloaded.add(filename)

    if filename in seen:
        if is_temp:
            fp.close()
            os.remove(path)
        raise zc.buildout.UserError("Recursive file include", seen, filename)

    root_config_file = not seen
    seen.append(filename)

    result = zc.buildout.configparser.parse(fp, filename, _default_globals)
    fp.close()
    if is_temp:
        os.remove(path)

    options = result.get('buildout', {})
    extends = options.pop('extends', None)
    if 'extended-by' in options:
        raise zc.buildout.UserError(
            'No-longer supported "extended-by" option found in %s.' %
            filename)

    result = _annotate(result, filename)

    if root_config_file and 'buildout' in result:
        dl_options = _update_section(dl_options, result['buildout'])

    if extends:
        extends = extends.split()
        eresult = _open(base, extends.pop(0), seen, dl_options, override,
                        downloaded)
        for fname in extends:
            _update(eresult, _open(base, fname, seen, dl_options, override,
                    downloaded))
        result = _update(eresult, result)

    seen.pop()
    return result


ignore_directories = '.svn', 'CVS', '__pycache__'
_dir_hashes = {}
def _dir_hash(dir):
    dir_hash = _dir_hashes.get(dir, None)
    if dir_hash is not None:
        return dir_hash
    hash = md5()
    for (dirpath, dirnames, filenames) in os.walk(dir):
        dirnames[:] = sorted(n for n in dirnames if n not in ignore_directories)
        filenames[:] = sorted(f for f in filenames
                              if (not (f.endswith('pyc') or f.endswith('pyo'))
                                  and os.path.exists(os.path.join(dirpath, f)))
                              )
        hash.update(' '.join(dirnames).encode())
        hash.update(' '.join(filenames).encode())
        for name in filenames:
            path = os.path.join(dirpath, name)
            if name == 'entry_points.txt':
                f = open(path)
                # Entry points aren't written in stable order. :(
                try:
                    sections = zc.buildout.configparser.parse(f, path)
                    data = repr([(sname, sorted(sections[sname].items()))
                                 for sname in sorted(sections)]).encode('utf-8')
                except Exception:
                    f.close()
                    f = open(path, 'rb')
                    data = f.read()
            else:
                f = open(path, 'rb')
                data = f.read()
            f.close()
            hash.update(data)
    _dir_hashes[dir] = dir_hash = hash.hexdigest()
    return dir_hash

def _dists_sig(dists):
    seen = set()
    result = []
    for dist in dists:
        if dist in seen:
            continue
        seen.add(dist)
        location = dist.location
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            result.append(dist.project_name + '-' + _dir_hash(location))
        else:
            result.append(os.path.basename(location))
    return result

def _update_section(s1, s2):
    # Base section 2 on section 1; section 1 is copied, with key-value pairs
    # in section 2 overriding those in section 1. If there are += or -=
    # operators in section 2, process these to add or substract items (delimited
    # by newlines) from the preexisting values.
    s2 = s2.copy() # avoid mutating the second argument, which is unexpected
    # Sort on key, then on the addition or substraction operator (+ comes first)
    for k, v in sorted(s2.items(), key=lambda x: (x[0].rstrip(' +'), x[0][-1])):
        v2, note2 = v
        if k.endswith('+'):
            key = k.rstrip(' +')
            # Find v1 in s2 first; it may have been defined locally too.
            v1, note1 = s2.get(key, s1.get(key, ("", "")))
            newnote = ' [+] '.join((note1, note2)).strip()
            s2[key] = "\n".join((v1).split('\n') +
                v2.split('\n')), newnote
            del s2[k]
        elif k.endswith('-'):
            key = k.rstrip(' -')
            # Find v1 in s2 first; it may have been set by a += operation first
            v1, note1 = s2.get(key, s1.get(key, ("", "")))
            newnote = ' [-] '.join((note1, note2)).strip()
            s2[key] = ("\n".join(
                [v for v in v1.split('\n')
                   if v not in v2.split('\n')]), newnote)
            del s2[k]

    s1.update(s2)
    return s1

def _update(d1, d2):
    for section in d2:
        if section in d1:
            d1[section] = _update_section(d1[section], d2[section])
        else:
            d1[section] = d2[section]
    return d1

def _recipe(options):
    recipe = options['recipe']
    if ':' in recipe:
        recipe, entry = recipe.split(':')
    else:
        entry = 'default'

    return recipe, entry

def _doing():
    _, v, tb = sys.exc_info()
    message = str(v)
    doing = []
    while tb is not None:
        d = tb.tb_frame.f_locals.get('__doing__')
        if d:
            doing.append(d)
        tb = tb.tb_next

    if doing:
        sys.stderr.write('While:\n')
        for d in doing:
            if not isinstance(d, str):
                d = d[0] % d[1:]
            sys.stderr.write('  %s\n' % d)

def _error(*message):
    sys.stderr.write('Error: ' + ' '.join(message) +'\n')
    sys.exit(1)

_internal_error_template = """
An internal error occurred due to a bug in either zc.buildout or in a
recipe being used:
"""

def _check_for_unused_options_in_section(buildout, section):
    options = buildout[section]
    unused = [option for option in sorted(options._raw)
              if option not in options._data]
    if unused:
        buildout._logger.warn("Unused options for %s: %s."
                              % (section, ' '.join(map(repr, unused)))
                              )

_usage = """\
Usage: buildout [options] [assignments] [command [command arguments]]

Options:

  -h, --help

     Print this message and exit.

  --version

     Print buildout version number and exit.

  -v

     Increase the level of verbosity.  This option can be used multiple times.

  -q

     Decrease the level of verbosity.  This option can be used multiple times.

  -c config_file

     Specify the path to the buildout configuration file to be used.
     This defaults to the file named "buildout.cfg" in the current
     working directory.

  -t socket_timeout

     Specify the socket timeout in seconds.

  -U

     Don't read user defaults.

  -o

    Run in off-line mode.  This is equivalent to the assignment
    buildout:offline=true.

  -O

    Run in non-off-line mode.  This is equivalent to the assignment
    buildout:offline=false.  This is the default buildout mode.  The
    -O option would normally be used to override a true offline
    setting in a configuration file.

  -n

    Run in newest mode.  This is equivalent to the assignment
    buildout:newest=true.  With this setting, which is the default,
    buildout will try to find the newest versions of distributions
    available that satisfy its requirements.

  -N

    Run in non-newest mode.  This is equivalent to the assignment
    buildout:newest=false.  With this setting, buildout will not seek
    new distributions if installed distributions satisfy it's
    requirements.

  -D

    Debug errors.  If an error occurs, then the post-mortem debugger
    will be started. This is especially useful for debuging recipe
    problems.

Assignments are of the form: section:option=value and are used to
provide configuration options that override those given in the
configuration file.  For example, to run the buildout in offline mode,
use buildout:offline=true.

Options and assignments can be interspersed.

Commands:

  install [parts]

    Install parts.  If no command arguments are given, then the parts
    definition from the configuration file is used.  Otherwise, the
    arguments specify the parts to be installed.

    Note that the semantics differ depending on whether any parts are
    specified.  If parts are specified, then only those parts will be
    installed. If no parts are specified, then the parts specified by
    the buildout parts option will be installed along with all of
    their dependencies.

  bootstrap

    Create a new buildout in the current working directory, copying
    the buildout and setuptools eggs and, creating a basic directory
    structure and a buildout-local buildout script.

  init

    Initialize a buildout, creating a buildout.cfg file if it doesn't
    exist and then performing the same actions as for the buildout
    command.

  setup script [setup command and options]

    Run a given setup script arranging that setuptools is in the
    script's path and and that it has been imported so that
    setuptools-provided commands (like bdist_egg) can be used even if
    the setup script doesn't import setuptools.

    The script can be given either as a script path or a path to a
    directory containing a setup.py script.

  annotate

    Display annotated sections. All sections are displayed, sorted
    alphabetically. For each section, all key-value pairs are displayed,
    sorted alphabetically, along with the origin of the value (file name or
    COMPUTED_VALUE, DEFAULT_VALUE, COMMAND_LINE_VALUE).

"""

def _help():
    print_(_usage)
    sys.exit(0)

def _version():
    version = pkg_resources.working_set.find(
                pkg_resources.Requirement.parse('zc.buildout')).version
    print_("buildout version %s" % version)
    sys.exit(0)

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    config_file = 'buildout.cfg'
    verbosity = 0
    options = []
    user_defaults = True
    debug = False
    while args:
        if args[0][0] == '-':
            op = orig_op = args.pop(0)
            op = op[1:]
            while op and op[0] in 'vqhWUoOnNDA':
                if op[0] == 'v':
                    verbosity += 10
                elif op[0] == 'q':
                    verbosity -= 10
                elif op[0] == 'U':
                    user_defaults = False
                elif op[0] == 'o':
                    options.append(('buildout', 'offline', 'true'))
                elif op[0] == 'O':
                    options.append(('buildout', 'offline', 'false'))
                elif op[0] == 'n':
                    options.append(('buildout', 'newest', 'true'))
                elif op[0] == 'N':
                    options.append(('buildout', 'newest', 'false'))
                elif op[0] == 'D':
                    debug = True
                else:
                    _help()
                op = op[1:]

            if op[:1] in  ('c', 't'):
                op_ = op[:1]
                op = op[1:]

                if op_ == 'c':
                    if op:
                        config_file = op
                    else:
                        if args:
                            config_file = args.pop(0)
                        else:
                            _error("No file name specified for option", orig_op)
                elif op_ == 't':
                    try:
                        timeout_string = args.pop(0)
                        timeout = int(timeout_string)
                        options.append(
                            ('buildout', 'socket-timeout', timeout_string))
                    except IndexError:
                        _error("No timeout value specified for option", orig_op)
                    except ValueError:
                        _error("Timeout value must be numeric", orig_op)
            elif op:
                if orig_op == '--help':
                    _help()
                elif orig_op == '--version':
                    _version()
                _error("Invalid option", '-'+op[0])
        elif '=' in args[0]:
            option, value = args.pop(0).split('=', 1)
            option = option.split(':')
            if len(option) == 1:
                option = 'buildout', option[0]
            elif len(option) != 2:
                _error('Invalid option:', option)
            section, option = option
            options.append((section.strip(), option.strip(), value.strip()))
        else:
            # We've run out of command-line options and option assignments
            # The rest should be commands, so we'll stop here
            break

    if verbosity:
        options.append(('buildout', 'verbosity', str(verbosity)))

    if args:
        command = args.pop(0)
        if command not in (
            'install', 'bootstrap', 'runsetup', 'setup', 'init',
            'annotate',
            ):
            _error('invalid command:', command)
    else:
        command = 'install'

    try:
        try:
            buildout = Buildout(config_file, options,
                                user_defaults, command, args)
            getattr(buildout, command)(args)
        except SystemExit:
            logging.shutdown()
            # Make sure we properly propagate an exit code from a restarted
            # buildout process.
            raise
        except Exception:
            v = sys.exc_info()[1]
            _doing()
            exc_info = sys.exc_info()
            import pdb, traceback
            if debug:
                traceback.print_exception(*exc_info)
                sys.stderr.write('\nStarting pdb:\n')
                pdb.post_mortem(exc_info[2])
            else:
                if isinstance(v, (zc.buildout.UserError,
                                  distutils.errors.DistutilsError
                                  )
                              ):
                    _error(str(v))
                else:
                    sys.stderr.write(_internal_error_template)
                    traceback.print_exception(*exc_info)
                    sys.exit(1)

    finally:
        logging.shutdown()


if sys.version_info[:2] < (2, 4):
    def reversed(iterable):
        result = list(iterable);
        result.reverse()
        return result

_bool_names = {'true': True, 'false': False, True: True, False: False}
def bool_option(options, name, default=None):
    value = options.get(name, default)
    if value is None:
        raise KeyError(name)
    try:
        return _bool_names[value]
    except KeyError:
        raise zc.buildout.UserError(
            'Invalid value for %r option: %r' % (name, value))

########NEW FILE########
__FILENAME__ = configparser
##############################################################################
#
# Copyright Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

# The following copied from Python 2 config parser because:
# - The py3 configparser isn't backward compatible
# - Both strip option values in undesirable ways
# - dict of dicts is a much simpler api

import re
import textwrap
import logging

logger = logging.getLogger('zc.buildout')

class Error(Exception):
    """Base class for ConfigParser exceptions."""

    def _get_message(self):
        """Getter for 'message'; needed only to override deprecation in
        BaseException."""
        return self.__message

    def _set_message(self, value):
        """Setter for 'message'; needed only to override deprecation in
        BaseException."""
        self.__message = value

    # BaseException.message has been deprecated since Python 2.6.  To prevent
    # DeprecationWarning from popping up over this pre-existing attribute, use
    # a new property that takes lookup precedence.
    message = property(_get_message, _set_message)

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__

class ParsingError(Error):
    """Raised when a configuration file does not follow legal syntax."""

    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        self.errors.append((lineno, line))
        self.message += '\n\t[line %2d]: %s' % (lineno, line)

class MissingSectionHeaderError(ParsingError):
    """Raised when a key-value pair is found before any section header."""

    def __init__(self, filename, lineno, line):
        Error.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%r' %
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

# This regex captures either sections headers with optional trailing comment
# separated by a semicolon or a hash.  Section headers can have an optional
# expression. Expressions and comments can contain brackets but no verbatim '#'
# and ';' : these need to be escaped.
# A title line with an expression has the general form:
#  [section_name: some Python expression] #; some comment
# This regex leverages the fact that the following is a valid Python expression:
#  [some Python expression] # some comment
# and that section headers are also delimited by [brackets] that are also [list]
# delimiters.
# So instead of doing complex parsing to balance brackets in an expression, we
# capture just enough from a header line to collect then remove the section_name
# and colon expression separator keeping only a list-enclosed expression and
# optional comments. The parsing and validation of this Python expression can be
# entirely delegated to Python's eval. The result of the evaluated expression is
# the always returned wrapped in a list with a single item that contains the
# original expression

section_header  = re.compile(
    r'(?P<head>\[)'
    r'\s*'
    r'(?P<name>[^\s#[\]:;{}]+)'
    r'\s*'
    r'(:(?P<expression>[^#;]*))?'
    r'\s*'
    r'(?P<tail>]'
    r'\s*'
    r'([#;].*)?$)'
    ).match

option_start = re.compile(
    r'(?P<name>[^\s{}[\]=:]+\s*[-+]?)'
    r'='
    r'(?P<value>.*)$').match

leading_blank_lines = re.compile(r"^(\s*\n)+")

def parse(fp, fpname, exp_globals=dict):
    """Parse a sectioned setup file.

    The sections in setup files contain a title line at the top,
    indicated by a name in square brackets (`[]'), plus key/value
    options lines, indicated by `name: value' format lines.
    Continuations are represented by an embedded newline then
    leading whitespace.  Blank lines, lines beginning with a '#',
    and just about everything else are ignored.

    The title line is in the form [name] followed by an optional trailing
    comment separated by a semicolon `;' or a hash `#' character.

    Optionally the title line can have the form `[name:expression]' where
    expression is an arbitrary Python expression. Sections with an expression
    that evaluates to False are ignored. Semicolon `;' an hash `#' characters
    must be string-escaped in expression literals.

    exp_globals is a callable returning a mapping of defaults used as globals
    during the evaluation of a section conditional expression.
    """
    sections = {}
    # the current section condition, possibly updated from a section expression
    section_condition = True
    context = None
    cursect = None                            # None, or a dictionary
    blockmode = None
    optname = None
    lineno = 0
    e = None                                  # None, or an exception
    while True:
        line = fp.readline()
        if not line:
            break # EOF

        lineno = lineno + 1

        if line[0] in '#;':
            continue # comment

        if line[0].isspace() and cursect is not None and optname:
            if not section_condition:
                #skip section based on its expression condition
                continue
            # continuation line
            if blockmode:
                line = line.rstrip()
            else:
                line = line.strip()
                if not line:
                    continue
            cursect[optname] = "%s\n%s" % (cursect[optname], line)
        else:
            header = section_header(line)
            if header:
                # reset to True when starting a new section
                section_condition = True
                sectname = header.group('name')

                head = header.group('head') # the starting [
                expression = header.group('expression')
                tail = header.group('tail') # closing ]and comment
                if expression:
                    # normalize tail comments to Python style
                    tail = tail.replace(';', '#') if tail else ''
                    # un-escape literal # and ; . Do not use a
                    # string-escape decode
                    expr = expression.replace(r'\x23','#').replace(r'x3b', ';')
                    # rebuild a valid Python expression wrapped in a list
                    expr = head + expr + tail
                    # lazily populate context only expression
                    if not context:
                        context = exp_globals()
                    # evaluated expression is in list: get first element
                    section_condition = eval(expr, context)[0]
                    # finally, ignore section when an expression
                    # evaluates to false
                    if not section_condition:
                        logger.debug(
                            'Ignoring section %(sectname)r with [expression]:'
                            ' %(expression)r' % locals())
                        continue

                if sectname in sections:
                    cursect = sections[sectname]
                else:
                    sections[sectname] = cursect = {}
                # So sections can't start with a continuation line
                optname = None
            elif cursect is None:
                if not line.strip():
                    continue
                # no section header in the file?
                raise MissingSectionHeaderError(fpname, lineno, line)
            else:
                mo = option_start(line)
                if mo:
                    if not section_condition:
                        # filter out options of conditionally ignored section
                        continue
                    # option start line
                    optname, optval = mo.group('name', 'value')
                    optname = optname.rstrip()
                    optval = optval.strip()
                    cursect[optname] = optval
                    blockmode = not optval
                elif not (optname or line.strip()):
                    # blank line after section start
                    continue
                else:
                    # a non-fatal parsing error occurred.  set up the
                    # exception but keep going. the exception will be
                    # raised at the end of the file and will contain a
                    # list of all bogus lines
                    if not e:
                        e = ParsingError(fpname)
                    e.append(lineno, repr(line))

    # if any parsing errors occurred, raise an exception
    if e:
        raise e

    for sectname in sections:
        section = sections[sectname]
        for name in section:
            value = section[name]
            if value[:1].isspace():
                section[name] = leading_blank_lines.sub(
                    '', textwrap.dedent(value.rstrip()))

    return sections

########NEW FILE########
__FILENAME__ = download
##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Buildout download infrastructure"""

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

try:
    # Python 3
    from urllib.request import FancyURLopener, URLopener, urlretrieve
    from urllib.parse import urlparse
    from urllib import request as urllib # for monkey patch below :(
except ImportError:
    # Python 2
    from urllib import FancyURLopener, URLopener, urlretrieve
    from urlparse import urlparse
    import urllib

class URLOpener(FancyURLopener):
    http_error_default = URLopener.http_error_default

urllib._urlopener = URLOpener() # Ook! Monkey patch!


from zc.buildout.easy_install import realpath
import logging
import os
import os.path
import re
import shutil
import sys
import tempfile
import zc.buildout

class ChecksumError(zc.buildout.UserError):
    pass

class Download(object):
    """Configurable download utility.

    Handles the download cache and offline mode.

    Download(options=None, cache=None, namespace=None,
             offline=False, fallback=False, hash_name=False, logger=None)

    options: mapping of buildout options (e.g. a ``buildout`` config section)
    cache: path to the download cache (excluding namespaces)
    namespace: namespace directory to use inside the cache
    offline: whether to operate in offline mode
    fallback: whether to use the cache as a fallback (try downloading first)
    hash_name: whether to use a hash of the URL as cache file name
    logger: an optional logger to receive download-related log messages

    """

    def __init__(self, options={}, cache=-1, namespace=None,
                 offline=-1, fallback=False, hash_name=False, logger=None):
        self.directory = options.get('directory', '')
        self.cache = cache
        if cache == -1:
            self.cache = options.get('download-cache')
        self.namespace = namespace
        self.offline = offline
        if offline == -1:
            self.offline = (options.get('offline') == 'true'
                            or options.get('install-from-cache') == 'true')
        self.fallback = fallback
        self.hash_name = hash_name
        self.logger = logger or logging.getLogger('zc.buildout')

    @property
    def download_cache(self):
        if self.cache is not None:
            return realpath(os.path.join(self.directory, self.cache))

    @property
    def cache_dir(self):
        if self.download_cache is not None:
            return os.path.join(self.download_cache, self.namespace or '')

    def __call__(self, url, md5sum=None, path=None):
        """Download a file according to the utility's configuration.

        url: URL to download
        md5sum: MD5 checksum to match
        path: where to place the downloaded file

        Returns the path to the downloaded file.

        """
        if self.cache:
            local_path, is_temp = self.download_cached(url, md5sum)
        else:
            local_path, is_temp = self.download(url, md5sum, path)

        return locate_at(local_path, path), is_temp

    def download_cached(self, url, md5sum=None):
        """Download a file from a URL using the cache.

        This method assumes that the cache has been configured. Optionally, it
        raises a ChecksumError if a cached copy of a file has an MD5 mismatch,
        but will not remove the copy in that case.

        """
        if not os.path.exists(self.download_cache):
            raise zc.buildout.UserError(
                'The directory:\n'
                '%r\n'
                "to be used as a download cache doesn't exist.\n"
                % self.download_cache)
        cache_dir = self.cache_dir
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        cache_key = self.filename(url)
        cached_path = os.path.join(cache_dir, cache_key)

        self.logger.debug('Searching cache at %s' % cache_dir)
        if os.path.exists(cached_path):
            is_temp = False
            if self.fallback:
                try:
                    _, is_temp = self.download(url, md5sum, cached_path)
                except ChecksumError:
                    raise
                except Exception:
                    pass

            if not check_md5sum(cached_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch for cached download '
                    'from %r at %r' % (url, cached_path))
            self.logger.debug('Using cache file %s' % cached_path)
        else:
            self.logger.debug('Cache miss; will cache %s as %s' %
                              (url, cached_path))
            _, is_temp = self.download(url, md5sum, cached_path)

        return cached_path, is_temp

    def download(self, url, md5sum=None, path=None):
        """Download a file from a URL to a given or temporary path.

        An online resource is always downloaded to a temporary file and moved
        to the specified path only after the download is complete and the
        checksum (if given) matches. If path is None, the temporary file is
        returned and the client code is responsible for cleaning it up.

        """
        # Make sure the drive letter in windows-style file paths isn't
        # interpreted as a URL scheme.
        if re.match(r"^[A-Za-z]:\\", url):
            url = 'file:' + url

        parsed_url = urlparse(url, 'file')
        url_scheme, _, url_path = parsed_url[:3]
        if url_scheme == 'file':
            self.logger.debug('Using local resource %s' % url)
            if not check_md5sum(url_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch for local resource at %r.' %
                    url_path)
            return locate_at(url_path, path), False

        if self.offline:
            raise zc.buildout.UserError(
                "Couldn't download %r in offline mode." % url)

        self.logger.info('Downloading %s' % url)
        handle, tmp_path = tempfile.mkstemp(prefix='buildout-')
        os.close(handle)
        try:
            tmp_path, headers = urlretrieve(url, tmp_path)
            if not check_md5sum(tmp_path, md5sum):
                raise ChecksumError(
                    'MD5 checksum mismatch downloading %r' % url)
        except IOError:
            e = sys.exc_info()[1]
            os.remove(tmp_path)
            raise zc.buildout.UserError("Error downloading extends for URL "
                              "%s: %s" % (url, e))
        except Exception:
            os.remove(tmp_path)
            raise

        if path:
            shutil.move(tmp_path, path)
            return path, False
        else:
            return tmp_path, True

    def filename(self, url):
        """Determine a file name from a URL according to the configuration.

        """
        if self.hash_name:
            return md5(url.encode()).hexdigest()
        else:
            if re.match(r"^[A-Za-z]:\\", url):
                url = 'file:' + url
            parsed = urlparse(url, 'file')
            url_path = parsed[2]

            if parsed[0] == 'file':
                while True:
                    url_path, name = os.path.split(url_path)
                    if name:
                        return name
                    if not url_path:
                        break
            else:
                for name in reversed(url_path.split('/')):
                    if name:
                        return name

            url_host, url_port = parsed[-2:]
            return '%s:%s' % (url_host, url_port)


def check_md5sum(path, md5sum):
    """Tell whether the MD5 checksum of the file at path matches.

    No checksum being given is considered a match.

    """
    if md5sum is None:
        return True

    f = open(path, 'rb')
    checksum = md5()
    try:
        chunk = f.read(2**16)
        while chunk:
            checksum.update(chunk)
            chunk = f.read(2**16)
        return checksum.hexdigest() == md5sum
    finally:
        f.close()


def remove(path):
    if os.path.exists(path):
        os.remove(path)


def locate_at(source, dest):
    if dest is None or realpath(dest) == realpath(source):
        return source

    if os.path.isdir(source):
        shutil.copytree(source, dest)
    else:
        try:
            os.link(source, dest)
        except (AttributeError, OSError):
            shutil.copyfile(source, dest)
    return dest

########NEW FILE########
__FILENAME__ = easy_install
#############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Python easy_install API

This module provides a high-level Python API for installing packages.
It doesn't install scripts.  It uses setuptools and requires it to be
installed.
"""

import distutils.errors
import errno
import glob
import logging
import os
import pkg_resources
import py_compile
import re
import setuptools.archive_util
import setuptools.command.easy_install
import setuptools.command.setopt
import setuptools.package_index
import shutil
import subprocess
import sys
import tempfile
import zc.buildout

_oprp = getattr(os.path, 'realpath', lambda path: path)
def realpath(path):
    return os.path.normcase(os.path.abspath(_oprp(path)))

default_index_url = os.environ.get(
    'buildout-testing-index-url',
    'http://pypi.python.org/simple',
    )

logger = logging.getLogger('zc.buildout.easy_install')

url_match = re.compile('[a-z0-9+.-]+://').match
is_source_encoding_line = re.compile('coding[:=]\s*([-\w.]+)').search
# Source encoding regex from http://www.python.org/dev/peps/pep-0263/

is_win32 = sys.platform == 'win32'
is_jython = sys.platform.startswith('java')

if is_jython:
    import java.lang.System
    jython_os_name = (java.lang.System.getProperties()['os.name']).lower()

# Make sure we're not being run with an older bootstrap.py that gives us
# setuptools instead of setuptools
has_distribute = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('distribute')) is not None
has_setuptools = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('setuptools')) is not None
if has_distribute and not has_setuptools:
    sys.exit("zc.buildout 2 needs setuptools, not distribute."
             "  Are you using an outdated bootstrap.py?  Make sure"
             " you have the latest version downloaded from"
             " http://downloads.buildout.org/2/bootstrap.py")

setuptools_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')
    ).location

# Include buildout and setuptools eggs in paths
buildout_and_setuptools_path = [
    setuptools_loc,
    pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.buildout')).location,
    ]

FILE_SCHEME = re.compile('file://', re.I).match

class _Monkey(object):
    def __init__(self, module, **kw):
        mdict = self._mdict = module.__dict__
        self._before = mdict.copy()
        self._overrides = kw

    def __enter__(self):
        self._mdict.update(self._overrides)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._mdict.clear()
        self._mdict.update(self._before)

class _NoWarn(object):
    def warn(self, *args, **kw):
        pass

_no_warn = _NoWarn()

class AllowHostsPackageIndex(setuptools.package_index.PackageIndex):
    """Will allow urls that are local to the system.

    No matter what is allow_hosts.
    """
    def url_ok(self, url, fatal=False):
        if FILE_SCHEME(url):
            return True
        # distutils has its own logging, which can't be hooked / suppressed,
        # so we monkey-patch the 'log' submodule to suppress the stupid
        # "Link to <URL> ***BLOCKED*** by --allow-hosts" message.
        with _Monkey(setuptools.package_index, log=_no_warn):
            return setuptools.package_index.PackageIndex.url_ok(
                                                self, url, False)


_indexes = {}
def _get_index(index_url, find_links, allow_hosts=('*',)):
    key = index_url, tuple(find_links)
    index = _indexes.get(key)
    if index is not None:
        return index

    if index_url is None:
        index_url = default_index_url
    if index_url.startswith('file://'):
        index_url = index_url[7:]
    index = AllowHostsPackageIndex(index_url, hosts=allow_hosts)

    if find_links:
        index.add_find_links(find_links)

    _indexes[key] = index
    return index

clear_index_cache = _indexes.clear

if is_win32:
    # work around spawn lamosity on windows
    # XXX need safe quoting (see the subproces.list2cmdline) and test
    def _safe_arg(arg):
        return '"%s"' % arg
else:
    _safe_arg = str

def call_subprocess(args, **kw):
    if subprocess.call(args, **kw) != 0:
        raise Exception(
            "Failed to run command:\n%s"
            % repr(args)[1:-1])


def _execute_permission():
    current_umask = os.umask(0o022)
    # os.umask only returns the current umask if you also give it one, so we
    # have to give it a dummy one and immediately set it back to the real
    # value...  Distribute does the same.
    os.umask(current_umask)
    return 0o777 - current_umask


_easy_install_cmd = 'from setuptools.command.easy_install import main; main()'

class Installer:

    _versions = {}
    _required_by = {}
    _picked_versions = {}
    _download_cache = None
    _install_from_cache = False
    _prefer_final = True
    _use_dependency_links = True
    _allow_picked_versions = True
    _store_required_by = False

    def __init__(self,
                 dest=None,
                 links=(),
                 index=None,
                 executable=sys.executable,
                 always_unzip=None, # Backward compat :/
                 path=None,
                 newest=True,
                 versions=None,
                 use_dependency_links=None,
                 allow_hosts=('*',)
                 ):
        assert executable == sys.executable, (executable, sys.executable)
        self._dest = dest
        self._allow_hosts = allow_hosts

        if self._install_from_cache:
            if not self._download_cache:
                raise ValueError("install_from_cache set to true with no"
                                 " download cache")
            links = ()
            index = 'file://' + self._download_cache

        if use_dependency_links is not None:
            self._use_dependency_links = use_dependency_links
        self._links = links = list(_fix_file_links(links))
        if self._download_cache and (self._download_cache not in links):
            links.insert(0, self._download_cache)

        self._index_url = index
        path = (path and path[:] or []) + buildout_and_setuptools_path
        if dest is not None and dest not in path:
            path.insert(0, dest)
        self._path = path
        if self._dest is None:
            newest = False
        self._newest = newest
        self._env = pkg_resources.Environment(path)
        self._index = _get_index(index, links, self._allow_hosts)

        if versions is not None:
            self._versions = normalize_versions(versions)

    def _satisfied(self, req, source=None):
        dists = [dist for dist in self._env[req.project_name] if dist in req]
        if not dists:
            logger.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))

            return None, self._obtain(req, source)

        # Note that dists are sorted from best to worst, as promised by
        # env.__getitem__

        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST):
                logger.debug('We have a develop egg: %s', dist)
                return dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            logger.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0], None

        if self._prefer_final:
            fdists = [dist for dist in dists
                      if _final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        if not self._newest:
            # We don't need the newest, so we'll use the newest one we
            # find, which is the first returned by
            # Environment.__getitem__.
            return dists[0], None

        best_we_have = dists[0] # Because dists are sorted from best to worst

        # We have some installed distros.  There might, theoretically, be
        # newer ones.  Let's find out which ones are available and see if
        # any are newer.  We only do this if we're willing to install
        # something, which is only true if dest is not None:

        best_available = self._obtain(req, source)

        if best_available is None:
            # That's a bit odd.  There aren't any distros available.
            # We should use the best one we have that meets the requirement.
            logger.debug(
                'There are no distros available that meet %r.\n'
                'Using our best, %s.',
                str(req), best_available)
            return best_we_have, None

        if self._prefer_final:
            if _final_version(best_available.parsed_version):
                if _final_version(best_we_have.parsed_version):
                    if (best_we_have.parsed_version
                        <
                        best_available.parsed_version
                        ):
                        return None, best_available
                else:
                    return None, best_available
            else:
                if (not _final_version(best_we_have.parsed_version)
                    and
                    (best_we_have.parsed_version
                     <
                     best_available.parsed_version
                     )
                    ):
                    return None, best_available
        else:
            if (best_we_have.parsed_version
                <
                best_available.parsed_version
                ):
                return None, best_available

        logger.debug(
            'We have the best distribution that satisfies %r.',
            str(req))
        return best_we_have, None

    def _load_dist(self, dist):
        dists = pkg_resources.Environment(dist.location)[dist.project_name]
        assert len(dists) == 1
        return dists[0]

    def _call_easy_install(self, spec, ws, dest, dist):

        tmp = tempfile.mkdtemp(dir=dest)
        try:
            path = setuptools_loc

            args = [sys.executable, '-c', _easy_install_cmd, '-mZUNxd', tmp]
            level = logger.getEffectiveLevel()
            if level > 0:
                args.append('-q')
            elif level < 0:
                args.append('-v')

            args.append(spec)

            if level <= logging.DEBUG:
                logger.debug('Running easy_install:\n"%s"\npath=%s\n',
                             '" "'.join(args), path)

            sys.stdout.flush() # We want any pending output first

            exit_code = subprocess.call(
                list(args),
                env=dict(os.environ, PYTHONPATH=path))

            dists = []
            env = pkg_resources.Environment([tmp])
            for project in env:
                dists.extend(env[project])

            if exit_code:
                logger.error(
                    "An error occurred when trying to install %s. "
                    "Look above this message for any errors that "
                    "were output by easy_install.",
                    dist)

            if not dists:
                raise zc.buildout.UserError("Couldn't install: %s" % dist)

            if len(dists) > 1:
                logger.warn("Installing %s\n"
                            "caused multiple distributions to be installed:\n"
                            "%s\n",
                            dist, '\n'.join(map(str, dists)))
            else:
                d = dists[0]
                if d.project_name != dist.project_name:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different project name.",
                                dist, d)
                if d.version != dist.version:
                    logger.warn("Installing %s\n"
                                "Caused installation of a distribution:\n"
                                "%s\n"
                                "with a different version.",
                                dist, d)

            result = []
            for d in dists:
                newloc = os.path.join(dest, os.path.basename(d.location))
                if os.path.exists(newloc):
                    if os.path.isdir(newloc):
                        shutil.rmtree(newloc)
                    else:
                        os.remove(newloc)
                os.rename(d.location, newloc)

                [d] = pkg_resources.Environment([newloc])[d.project_name]

                result.append(d)

            return result

        finally:
            shutil.rmtree(tmp)

    def _obtain(self, requirement, source=None):
        # initialize out index for this project:
        index = self._index

        if index.obtain(requirement) is None:
            # Nothing is available.
            return None

        # Filter the available dists for the requirement and source flag
        dists = [dist for dist in index[requirement.project_name]
                 if ((dist in requirement)
                     and
                     ((not source) or
                      (dist.precedence == pkg_resources.SOURCE_DIST)
                      )
                     )
                 ]

        # If we prefer final dists, filter for final and use the
        # result if it is non empty.
        if self._prefer_final:
            fdists = [dist for dist in dists
                      if _final_version(dist.parsed_version)
                      ]
            if fdists:
                # There are final dists, so only use those
                dists = fdists

        # Now find the best one:
        best = []
        bestv = ()
        for dist in dists:
            distv = dist.parsed_version
            if distv > bestv:
                best = [dist]
                bestv = distv
            elif distv == bestv:
                best.append(dist)

        if not best:
            return None

        if len(best) == 1:
            return best[0]

        if self._download_cache:
            for dist in best:
                if (realpath(os.path.dirname(dist.location))
                    ==
                    self._download_cache
                    ):
                    return dist

        best.sort()
        return best[-1]

    def _fetch(self, dist, tmp, download_cache):
        if (download_cache
            and (realpath(os.path.dirname(dist.location)) == download_cache)
            ):
            return dist

        new_location = self._index.download(dist.location, tmp)
        if (download_cache
            and (realpath(new_location) == realpath(dist.location))
            and os.path.isfile(new_location)
            ):
            # setuptools avoids making extra copies, but we want to copy
            # to the download cache
            shutil.copy2(new_location, tmp)
            new_location = os.path.join(tmp, os.path.basename(new_location))

        return dist.clone(location=new_location)

    def _get_dist(self, requirement, ws):

        __doing__ = 'Getting distribution for %r.', str(requirement)

        # Maybe an existing dist is already the best dist that satisfies the
        # requirement
        dist, avail = self._satisfied(requirement)

        if dist is None:
            if self._dest is None:
                raise zc.buildout.UserError(
                    "We don't have a distribution for %s\n"
                    "and can't install one in offline (no-install) mode.\n"
                    % requirement)

            logger.info(*__doing__)

            # Retrieve the dist:
            if avail is None:
                self._index.obtain(requirement)
                raise MissingDistribution(requirement, ws)

            # We may overwrite distributions, so clear importer
            # cache.
            sys.path_importer_cache.clear()

            tmp = self._download_cache
            if tmp is None:
                tmp = tempfile.mkdtemp('get_dist')

            try:
                dist = self._fetch(avail, tmp, self._download_cache)

                if dist is None:
                    raise zc.buildout.UserError(
                        "Couln't download distribution %s." % avail)

                if dist.precedence == pkg_resources.EGG_DIST:
                    # It's already an egg, just fetch it into the dest

                    newloc = os.path.join(
                        self._dest, os.path.basename(dist.location))

                    if os.path.isdir(dist.location):
                        # we got a directory. It must have been
                        # obtained locally.  Just copy it.
                        shutil.copytree(dist.location, newloc)
                    else:


                        setuptools.archive_util.unpack_archive(
                            dist.location, newloc)

                    redo_pyc(newloc)

                    # Getting the dist from the environment causes the
                    # distribution meta data to be read.  Cloning isn't
                    # good enough.
                    dists = pkg_resources.Environment([newloc])[
                        dist.project_name]
                else:
                    # It's some other kind of dist.  We'll let easy_install
                    # deal with it:
                    dists = self._call_easy_install(
                        dist.location, ws, self._dest, dist)
                    for dist in dists:
                        redo_pyc(dist.location)

            finally:
                if tmp != self._download_cache:
                    shutil.rmtree(tmp)

            self._env.scan([self._dest])
            dist = self._env.best_match(requirement, ws)
            logger.info("Got %s.", dist)

        else:
            dists = [dist]

        for dist in dists:
            if (dist.has_metadata('dependency_links.txt')
                and not self._install_from_cache
                and self._use_dependency_links
                ):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    link = link.strip()
                    if link not in self._links:
                        logger.debug('Adding find link %r from %s', link, dist)
                        self._links.append(link)
                        self._index = _get_index(self._index_url, self._links,
                                                 self._allow_hosts)

        for dist in dists:
            # Check whether we picked a version and, if we did, report it:
            if not (
                dist.precedence == pkg_resources.DEVELOP_DIST
                or
                (len(requirement.specs) == 1
                 and
                 requirement.specs[0][0] == '==')
                ):
                logger.debug('Picked: %s = %s',
                             dist.project_name, dist.version)
                self._picked_versions[dist.project_name] = dist.version

                if not self._allow_picked_versions:
                    raise zc.buildout.UserError(
                        'Picked: %s = %s' % (dist.project_name, dist.version)
                        )

        return dists

    def _maybe_add_setuptools(self, ws, dist):
        if dist.has_metadata('namespace_packages.txt'):
            for r in dist.requires():
                if r.project_name in ('setuptools', 'setuptools'):
                    break
            else:
                # We have a namespace package but no requirement for setuptools
                if dist.precedence == pkg_resources.DEVELOP_DIST:
                    logger.warn(
                        "Develop distribution: %s\n"
                        "uses namespace packages but the distribution "
                        "does not require setuptools.",
                        dist)
                requirement = self._constrain(
                    pkg_resources.Requirement.parse('setuptools')
                    )
                if ws.find(requirement) is None:
                    for dist in self._get_dist(requirement, ws):
                        ws.add(dist)


    def _constrain(self, requirement):
        constraint = self._versions.get(requirement.project_name.lower())
        if constraint:
            requirement = _constrained_requirement(constraint, requirement)
        return requirement

    def install(self, specs, working_set=None):

        logger.debug('Installing %s.', repr(specs)[1:-1])

        path = self._path
        dest = self._dest
        if dest is not None and dest not in path:
            path.insert(0, dest)

        requirements = [self._constrain(pkg_resources.Requirement.parse(spec))
                        for spec in specs]



        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            ws = working_set

        for requirement in requirements:
            for dist in self._get_dist(requirement, ws):
                ws.add(dist)
                self._maybe_add_setuptools(ws, dist)

        # OK, we have the requested distributions and they're in the working
        # set, but they may have unmet requirements.  We'll simply keep
        # trying to resolve requirements, adding missing requirements as they
        # are reported.
        #
        # Note that we don't pass in the environment, because we want
        # to look for new eggs unless what we have is the best that
        # matches the requirement.
        while 1:
            try:
                ws.resolve(requirements)
            except pkg_resources.DistributionNotFound:
                err = sys.exc_info()[1]
                [requirement] = err.args
                requirement = self._constrain(requirement)
                if dest:
                    logger.debug('Getting required %r', str(requirement))
                else:
                    logger.debug('Adding required %r', str(requirement))
                _log_requirement(ws, requirement)

                for dist in self._get_dist(requirement, ws):
                    ws.add(dist)
                    self._maybe_add_setuptools(ws, dist)
            except pkg_resources.VersionConflict:
                err = sys.exc_info()[1]
                raise VersionConflict(err, ws)
            else:
                break

        return ws

    def build(self, spec, build_ext):

        requirement = self._constrain(pkg_resources.Requirement.parse(spec))

        dist, avail = self._satisfied(requirement, 1)
        if dist is not None:
            return [dist.location]

        # Retrieve the dist:
        if avail is None:
            raise zc.buildout.UserError(
                "Couldn't find a source distribution for %r."
                % str(requirement))

        if self._dest is None:
            raise zc.buildout.UserError(
                "We don't have a distribution for %s\n"
                "and can't build one in offline (no-install) mode.\n"
                % requirement
                )

        logger.debug('Building %r', spec)

        tmp = self._download_cache
        if tmp is None:
            tmp = tempfile.mkdtemp('get_dist')

        try:
            dist = self._fetch(avail, tmp, self._download_cache)

            build_tmp = tempfile.mkdtemp('build')
            try:
                setuptools.archive_util.unpack_archive(dist.location,
                                                       build_tmp)
                if os.path.exists(os.path.join(build_tmp, 'setup.py')):
                    base = build_tmp
                else:
                    setups = glob.glob(
                        os.path.join(build_tmp, '*', 'setup.py'))
                    if not setups:
                        raise distutils.errors.DistutilsError(
                            "Couldn't find a setup script in %s"
                            % os.path.basename(dist.location)
                            )
                    if len(setups) > 1:
                        raise distutils.errors.DistutilsError(
                            "Multiple setup scripts in %s"
                            % os.path.basename(dist.location)
                            )
                    base = os.path.dirname(setups[0])

                setup_cfg = os.path.join(base, 'setup.cfg')
                if not os.path.exists(setup_cfg):
                    f = open(setup_cfg, 'w')
                    f.close()
                setuptools.command.setopt.edit_config(
                    setup_cfg, dict(build_ext=build_ext))

                dists = self._call_easy_install(
                    base, pkg_resources.WorkingSet(),
                    self._dest, dist)

                for dist in dists:
                    redo_pyc(dist.location)

                return [dist.location for dist in dists]
            finally:
                shutil.rmtree(build_tmp)

        finally:
            if tmp != self._download_cache:
                shutil.rmtree(tmp)


def normalize_versions(versions):
    """Return version dict with keys normalized to lowercase.

    PyPI is case-insensitive and not all distributions are consistent in
    their own naming.
    """
    return dict([(k.lower(), v) for (k, v) in versions.items()])


def default_versions(versions=None):
    old = Installer._versions
    if versions is not None:
        Installer._versions = normalize_versions(versions)
    return old

def download_cache(path=-1):
    old = Installer._download_cache
    if path != -1:
        if path:
            path = realpath(path)
        Installer._download_cache = path
    return old

def install_from_cache(setting=None):
    old = Installer._install_from_cache
    if setting is not None:
        Installer._install_from_cache = bool(setting)
    return old

def prefer_final(setting=None):
    old = Installer._prefer_final
    if setting is not None:
        Installer._prefer_final = bool(setting)
    return old

def use_dependency_links(setting=None):
    old = Installer._use_dependency_links
    if setting is not None:
        Installer._use_dependency_links = bool(setting)
    return old

def allow_picked_versions(setting=None):
    old = Installer._allow_picked_versions
    if setting is not None:
        Installer._allow_picked_versions = bool(setting)
    return old

def store_required_by(setting=None):
    old = Installer._store_required_by
    if setting is not None:
        Installer._store_required_by = bool(setting)
    return old

def get_picked_versions():
    picked_versions = sorted(Installer._picked_versions.items())
    required_by = Installer._required_by
    return (picked_versions, required_by)


def install(specs, dest,
            links=(), index=None,
            executable=sys.executable,
            always_unzip=None, # Backward compat :/
            path=None, working_set=None, newest=True, versions=None,
            use_dependency_links=None, allow_hosts=('*',),
            include_site_packages=None,
            allowed_eggs_from_site_packages=None,
            ):
    assert executable == sys.executable, (executable, sys.executable)
    assert include_site_packages is None
    assert allowed_eggs_from_site_packages is None

    installer = Installer(dest, links, index, sys.executable,
                          always_unzip, path,
                          newest, versions, use_dependency_links,
                          allow_hosts=allow_hosts)
    return installer.install(specs, working_set)


def build(spec, dest, build_ext,
          links=(), index=None,
          executable=sys.executable,
          path=None, newest=True, versions=None, allow_hosts=('*',)):
    assert executable == sys.executable, (executable, sys.executable)
    installer = Installer(dest, links, index, executable,
                          True, path, newest,
                          versions, allow_hosts=allow_hosts)
    return installer.build(spec, build_ext)



def _rm(*paths):
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)

def _copyeggs(src, dest, suffix, undo):
    result = []
    undo.append(lambda : _rm(*result))
    for name in os.listdir(src):
        if name.endswith(suffix):
            new = os.path.join(dest, name)
            _rm(new)
            os.rename(os.path.join(src, name), new)
            result.append(new)

    assert len(result) == 1, str(result)
    undo.pop()

    return result[0]

def develop(setup, dest,
            build_ext=None,
            executable=sys.executable):
    assert executable == sys.executable, (executable, sys.executable)
    if os.path.isdir(setup):
        directory = setup
        setup = os.path.join(directory, 'setup.py')
    else:
        directory = os.path.dirname(setup)

    undo = []
    try:
        if build_ext:
            setup_cfg = os.path.join(directory, 'setup.cfg')
            if os.path.exists(setup_cfg):
                os.rename(setup_cfg, setup_cfg+'-develop-aside')
                def restore_old_setup():
                    if os.path.exists(setup_cfg):
                        os.remove(setup_cfg)
                    os.rename(setup_cfg+'-develop-aside', setup_cfg)
                undo.append(restore_old_setup)
            else:
                f = open(setup_cfg, 'w')
                f.close()
                undo.append(lambda: os.remove(setup_cfg))
            setuptools.command.setopt.edit_config(
                setup_cfg, dict(build_ext=build_ext))

        fd, tsetup = tempfile.mkstemp()
        undo.append(lambda: os.remove(tsetup))
        undo.append(lambda: os.close(fd))

        os.write(fd, (runsetup_template % dict(
            setuptools=setuptools_loc,
            setupdir=directory,
            setup=setup,
            __file__ = setup,
            )).encode())

        tmp3 = tempfile.mkdtemp('build', dir=dest)
        undo.append(lambda : shutil.rmtree(tmp3))

        args = [executable,  tsetup, '-q', 'develop', '-mxN', '-d', tmp3]

        log_level = logger.getEffectiveLevel()
        if log_level <= 0:
            if log_level == 0:
                del args[2]
            else:
                args[2] == '-v'
        if log_level < logging.DEBUG:
            logger.debug("in: %r\n%s", directory, ' '.join(args))

        call_subprocess(args)

        return _copyeggs(tmp3, dest, '.egg-link', undo)

    finally:
        undo.reverse()
        [f() for f in undo]


def working_set(specs, executable, path=None,
                include_site_packages=None,
                allowed_eggs_from_site_packages=None):
    # Backward compat:
    if path is None:
        path = executable
    else:
        assert executable == sys.executable, (executable, sys.executable)
    assert include_site_packages is None
    assert allowed_eggs_from_site_packages is None

    return install(specs, None, path=path)

def scripts(reqs, working_set, executable, dest=None,
            scripts=None,
            extra_paths=(),
            arguments='',
            interpreter=None,
            initialization='',
            relative_paths=False,
            ):
    assert executable == sys.executable, (executable, sys.executable)

    path = [dist.location for dist in working_set]
    path.extend(extra_paths)
    # order preserving unique
    unique_path = []
    for p in path:
        if p not in unique_path:
            unique_path.append(p)
    path = list(map(realpath, unique_path))

    generated = []

    if isinstance(reqs, str):
        raise TypeError('Expected iterable of requirements or entry points,'
                        ' got string.')

    if initialization:
        initialization = '\n'+initialization+'\n'

    entry_points = []
    distutils_scripts = []
    for req in reqs:
        if isinstance(req, str):
            req = pkg_resources.Requirement.parse(req)
            dist = working_set.find(req)
            # regular console_scripts entry points
            for name in pkg_resources.get_entry_map(dist, 'console_scripts'):
                entry_point = dist.get_entry_info('console_scripts', name)
                entry_points.append(
                    (name, entry_point.module_name,
                     '.'.join(entry_point.attrs))
                    )
            # The metadata on "old-style" distutils scripts is not retained by
            # distutils/setuptools, except by placing the original scripts in
            # /EGG-INFO/scripts/.
            if dist.metadata_isdir('scripts'):
                for name in dist.metadata_listdir('scripts'):
                    if dist.metadata_isdir('scripts/' + name):
                        # Probably Python 3 __pycache__ directory.
                        continue
                    contents = dist.get_metadata('scripts/' + name)
                    distutils_scripts.append((name, contents))
        else:
            entry_points.append(req)

    for name, module_name, attrs in entry_points:
        if scripts is not None:
            sname = scripts.get(name)
            if sname is None:
                continue
        else:
            sname = name

        sname = os.path.join(dest, sname)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)

        generated.extend(
            _script(module_name, attrs, spath, sname, arguments,
                    initialization, rpsetup)
            )

    for name, contents in distutils_scripts:
        if scripts is not None:
            sname = scripts.get(name)
            if sname is None:
                continue
        else:
            sname = name

        sname = os.path.join(dest, sname)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)

        generated.extend(
            _distutils_script(spath, sname, contents, initialization, rpsetup)
            )

    if interpreter:
        sname = os.path.join(dest, interpreter)
        spath, rpsetup = _relative_path_and_setup(sname, path, relative_paths)
        generated.extend(_pyscript(spath, sname, rpsetup, initialization))

    return generated


def _relative_path_and_setup(sname, path, relative_paths):
    if relative_paths:
        relative_paths = os.path.normcase(relative_paths)
        sname = os.path.normcase(os.path.abspath(sname))
        spath = ',\n  '.join(
            [_relativitize(os.path.normcase(path_item), sname, relative_paths)
             for path_item in path]
            )
        rpsetup = relative_paths_setup
        for i in range(_relative_depth(relative_paths, sname)):
            rpsetup += "base = os.path.dirname(base)\n"
    else:
        spath = repr(path)[1:-1].replace(', ', ',\n  ')
        rpsetup = ''
    return spath, rpsetup


def _relative_depth(common, path):
    n = 0
    while 1:
        dirname = os.path.dirname(path)
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        if dirname == common:
            break
        n += 1
        path = dirname
    return n


def _relative_path(common, path):
    r = []
    while 1:
        dirname, basename = os.path.split(path)
        r.append(basename)
        if dirname == common:
            break
        if dirname == path:
            raise AssertionError("dirname of %s is the same" % dirname)
        path = dirname
    r.reverse()
    return os.path.join(*r)


def _relativitize(path, script, relative_paths):
    if path == script:
        raise AssertionError("path == script")
    common = os.path.dirname(os.path.commonprefix([path, script]))
    if (common == relative_paths or
        common.startswith(os.path.join(relative_paths, ''))
        ):
        return "join(base, %r)" % _relative_path(common, path)
    else:
        return repr(path)


relative_paths_setup = """
import os

join = os.path.join
base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
"""

def _script(module_name, attrs, path, dest, arguments, initialization, rsetup):
    if is_win32:
        dest += '-script.py'

    python = _safe_arg(sys.executable)

    contents = script_template % dict(
        python = python,
        path = path,
        module_name = module_name,
        attrs = attrs,
        arguments = arguments,
        initialization = initialization,
        relative_paths_setup = rsetup,
        )
    return _create_script(contents, dest)


def _distutils_script(path, dest, script_content, initialization, rsetup):
    if is_win32:
        dest += '-script.py'

    lines = script_content.splitlines(True)
    if not ('#!' in lines[0]) and ('python' in lines[0]):
        # The script doesn't follow distutil's rules.  Ignore it.
        return []
    lines = lines[1:]  # Strip off the first hashbang line.
    line_with_first_import = len(lines)
    for line_number, line in enumerate(lines):
        if not 'import' in line:
            continue
        if not (line.startswith('import') or line.startswith('from')):
            continue
        if '__future__' in line:
            continue
        line_with_first_import = line_number
        break

    before = ''.join(lines[:line_with_first_import])
    after = ''.join(lines[line_with_first_import:])

    python = _safe_arg(sys.executable)

    contents = distutils_script_template % dict(
        python = python,
        path = path,
        initialization = initialization,
        relative_paths_setup = rsetup,
        before = before,
        after = after
        )
    return _create_script(contents, dest)

def _file_changed(filename, old_contents, mode='r'):
    try:
        with open(filename, mode) as f:
            return f.read() != old_contents
    except EnvironmentError as e:
        if e.errno == errno.ENOENT:
            return True
        else:
            raise

def _create_script(contents, dest):
    generated = []
    script = dest

    changed = _file_changed(dest, contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        win32_exe = os.path.splitext(dest)[0] # remove ".py"
        if win32_exe.endswith('-script'):
            win32_exe = win32_exe[:-7] # remove "-script"
        win32_exe = win32_exe + '.exe' # add ".exe"
        try:
            new_data = setuptools.command.easy_install.get_win_launcher('cli')
        except AttributeError:
            # fall back for compatibility with older Distribute versions
            new_data = pkg_resources.resource_string('setuptools', 'cli.exe')

        if _file_changed(win32_exe, new_data, 'rb'):
            # Only write it if it's different.
            with open(win32_exe, 'wb') as f:
                f.write(new_data)
        generated.append(win32_exe)

    if changed:
        with open(dest, 'w') as f:
            f.write(contents)
        logger.info(
            "Generated script %r.",
            # Normalize for windows
            script.endswith('-script.py') and script[:-10] or script)

        try:
            os.chmod(dest, _execute_permission())
        except (AttributeError, os.error):
            pass

    generated.append(dest)
    return generated


if is_jython and jython_os_name == 'linux':
    script_header = '#!/usr/bin/env %(python)s'
else:
    script_header = '#!%(python)s'


script_template = script_header + '''\

%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s
import %(module_name)s

if __name__ == '__main__':
    sys.exit(%(module_name)s.%(attrs)s(%(arguments)s))
'''

distutils_script_template = script_header + '''
%(before)s
%(relative_paths_setup)s
import sys
sys.path[0:0] = [
  %(path)s,
  ]
%(initialization)s

%(after)s'''


def _pyscript(path, dest, rsetup, initialization=''):
    generated = []
    script = dest
    if is_win32:
        dest += '-script.py'

    python = _safe_arg(sys.executable)
    if path:
        path += ','  # Courtesy comma at the end of the list.

    contents = py_script_template % dict(
        python = python,
        path = path,
        relative_paths_setup = rsetup,
        initialization=initialization,
        )
    changed = _file_changed(dest, contents)

    if is_win32:
        # generate exe file and give the script a magic name:
        exe = script + '.exe'
        with open(exe, 'wb') as f:
            f.write(
                pkg_resources.resource_string('setuptools', 'cli.exe')
            )
        generated.append(exe)

    if changed:
        with open(dest, 'w') as f:
            f.write(contents)
        try:
            os.chmod(dest, _execute_permission())
        except (AttributeError, os.error):
            pass
        logger.info("Generated interpreter %r.", script)

    generated.append(dest)
    return generated

py_script_template = script_header + '''\

%(relative_paths_setup)s
import sys

sys.path[0:0] = [
  %(path)s
  ]
%(initialization)s

_interactive = True
if len(sys.argv) > 1:
    _options, _args = __import__("getopt").getopt(sys.argv[1:], 'ic:m:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec(_val)
        elif _opt == '-m':
            sys.argv[1:] = _args
            _args = []
            __import__("runpy").run_module(
                 _val, {}, "__main__", alter_sys=True)

    if _args:
        sys.argv[:] = _args
        __file__ = _args[0]
        del _options, _args
        with open(__file__, 'U') as __file__f:
            exec(compile(__file__f.read(), __file__, "exec"))

if _interactive:
    del _interactive
    __import__("code").interact(banner="", local=globals())
'''

runsetup_template = """
import sys
sys.path.insert(0, %(setupdir)r)
sys.path.insert(0, %(setuptools)r)

import os, setuptools

__file__ = %(__file__)r

os.chdir(%(setupdir)r)
sys.argv[0] = %(setup)r

with open(%(setup)r, 'U') as f:
    exec(compile(f.read(), %(setup)r, 'exec'))
"""


class VersionConflict(zc.buildout.UserError):

    def __init__(self, err, ws):
        ws = list(ws)
        ws.sort()
        self.err, self.ws = err, ws

    def __str__(self):
        existing_dist, req = self.err.args
        result = ["There is a version conflict.",
                  "We already have: %s" % existing_dist,
                  ]
        for dist in self.ws:
            if req in dist.requires():
                result.append("but %s requires %r." % (dist, str(req)))
        return '\n'.join(result)


class MissingDistribution(zc.buildout.UserError):

    def __init__(self, req, ws):
        ws = list(ws)
        ws.sort()
        self.data = req, ws

    def __str__(self):
        req, ws = self.data
        return "Couldn't find a distribution for %r." % str(req)

def _log_requirement(ws, req):
    if (not logger.isEnabledFor(logging.DEBUG) and
        not Installer._store_required_by):
        # Sorting the working set and iterating over it's requirements
        # is expensive, so short circuit the work if it won't even be
        # logged.  When profiling a simple buildout with 10 parts with
        # identical and large working sets, this resulted in a
        # decrease of run time from 93.411 to 15.068 seconds, about a
        # 6 fold improvement.
        return

    ws = list(ws)
    ws.sort()
    for dist in ws:
        if req in dist.requires():
            logger.debug("  required by %s." % dist)
            req_ = str(req)
            if req_ not in Installer._required_by:
                Installer._required_by[req_] = set()
            Installer._required_by[req_].add(str(dist.as_requirement()))

def _fix_file_links(links):
    for link in links:
        if link.startswith('file://') and link[-1] != '/':
            if os.path.isdir(link[7:]):
                # work around excessive restriction in setuptools:
                link += '/'
        yield link

_final_parts = '*final-', '*final'
def _final_version(parsed_version):
    for part in parsed_version:
        if (part[:1] == '*') and (part not in _final_parts):
            return False
    return True

def redo_pyc(egg):
    if not os.path.isdir(egg):
        return
    for dirpath, dirnames, filenames in os.walk(egg):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(dirpath, filename)
            if not (os.path.exists(filepath+'c')
                    or os.path.exists(filepath+'o')):
                # If it wasn't compiled, it may not be compilable
                continue

            # OK, it looks like we should try to compile.

            # Remove old files.
            for suffix in 'co':
                if os.path.exists(filepath+suffix):
                    os.remove(filepath+suffix)

            # Compile under current optimization
            try:
                py_compile.compile(filepath)
            except py_compile.PyCompileError:
                logger.warning("Couldn't compile %s", filepath)
            else:
                # Recompile under other optimization. :)
                args = [sys.executable]
                if __debug__:
                    args.append('-O')
                args.extend(['-m', 'py_compile', filepath])

                call_subprocess(args)

def _constrained_requirement(constraint, requirement):
    return pkg_resources.Requirement.parse(
        "%s[%s]%s" % (
            requirement.project_name,
            ','.join(requirement.extras),
            _constrained_requirement_constraint(constraint, requirement)
            )
        )

class IncompatibleConstraintError(zc.buildout.UserError):
    """A specified version is incompatible with a given requirement.
    """

IncompatibleVersionError = IncompatibleConstraintError # Backward compatibility

def bad_constraint(constraint, requirement):
    logger.error("The constraint, %s, is not consistent with the "
                 "requirement, %r.", constraint, str(requirement))
    raise IncompatibleConstraintError("Bad constraint", constraint, requirement)

_parse_constraint = re.compile(r'([<>]=?)\s*(\S+)').match
_comparef = {
    '>' : lambda x, y: x >  y,
    '>=': lambda x, y: x >= y,
    '<' : lambda x, y: x <  y,
    '<=': lambda x, y: x <= y,
    }
_opop = {'<': '>', '>': '<'}
_opeqop = {'<': '>=', '>': '<='}
def _constrained_requirement_constraint(constraint, requirement):

    # Simple cases:

    # No specs to merge with:
    if not requirement.specs:
        if not constraint[0] in '<=>':
            constraint = '==' + constraint
        return constraint

    # Simple single-version constraint:
    if constraint[0] not in '<>':
        if constraint.startswith('='):
            assert constraint.startswith('==')
            constraint = constraint[2:]
        if constraint in requirement:
            return '=='+constraint
        bad_constraint(constraint, requirement)


    # OK, we have a complex constraint (<. <=, >=, or >) and specs.
    # In many cases, the spec needs to filter constraints.
    # In other cases, the constraints need to limit the constraint.

    specs = requirement.specs
    cop, cv = _parse_constraint(constraint).group(1, 2)
    pcv = pkg_resources.parse_version(cv)

    # Special case, all of the specs are == specs:
    if not [op for (op, v) in specs if op != '==']:
        # There aren't any non-== specs.

        # See if any of the specs satisfy the constraint:
        specs = [op+v for (op, v) in specs
                 if _comparef[cop](pkg_resources.parse_version(v), pcv)]
        if specs:
            return ','.join(specs)

        bad_constraint(constraint, requirement)

    cop0 = cop[0]

    # Normalize specs by splitting >= and <= specs. We need to do this
    # because these have really weird semantics. Also cache parsed
    # versions, which we'll need for comparisons:
    specs = []
    for op, v in requirement.specs:
        pv = pkg_resources.parse_version(v)
        if op == _opeqop[cop0]:
            specs.append((op[0], v, pv))
            specs.append(('==', v, pv))
        else:
            specs.append((op, v, pv))

    # Error if there are opposite specs that conflict with the constraint
    # and there are no equal specs that satisfy the constraint:
    if [v for (op, v, pv) in specs
        if op == _opop[cop0] and _comparef[_opop[cop0]](pv, pcv)
        ]:
        eqspecs = [op+v for (op, v, pv) in specs
                   if _comparef[cop](pv, pcv)]
        if eqspecs:
            # OK, we do, use these:
            return ','.join(eqspecs)

        bad_constraint(constraint, requirement)

    # We have a combination of range constraints and eq specs that
    # satisfy the requirement.

    # Return the constraint + the filtered specs
    return ','.join(
        op+v
        for (op, v) in (
            [(cop, cv)] +
            [(op, v) for (op, v, pv) in specs if _comparef[cop](pv, pcv)]
            )
        )

########NEW FILE########
__FILENAME__ = rmtree
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################


import shutil
import os
import doctest

def rmtree (path):
    """
    A variant of shutil.rmtree which tries hard to be successful
    On windows shutil.rmtree aborts when it tries to delete a
    read only file.
    This tries to chmod the file to writeable and retries before giving up.

    >>> from tempfile import mkdtemp

    Let's make a directory ...

    >>> d = mkdtemp()

    and make sure it is actually there

    >>> os.path.isdir (d)
    1

    Now create a file ...

    >>> foo = os.path.join (d, 'foo')
    >>> _ = open (foo, 'w').write ('huhu')

    and make it unwriteable

    >>> os.chmod (foo, 256) # 0400

    rmtree should be able to remove it:

    >>> rmtree (d)

    and now the directory is gone

    >>> os.path.isdir (d)
    0
    """
    def retry_writeable (func, path, exc):
        os.chmod (path, 384) # 0600
        func (path)

    shutil.rmtree (path, onerror = retry_writeable)

def test_suite():
    return doctest.DocTestSuite()

if "__main__" == __name__:
    doctest.testmod()


########NEW FILE########
__FILENAME__ = testing
#############################################################################
#
# Copyright (c) 2004-2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Various test-support utility functions
"""

try:
    # Python 3
    from http.server    import HTTPServer, BaseHTTPRequestHandler
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urllib2        import urlopen

import errno
import logging
import os
import pkg_resources
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import zc.buildout.buildout
import zc.buildout.easy_install
from zc.buildout.rmtree import rmtree

print_ = zc.buildout.buildout.print_

fsync = getattr(os, 'fsync', lambda fileno: None)
is_win32 = sys.platform == 'win32'

setuptools_location = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

def cat(dir, *names):
    path = os.path.join(dir, *names)
    if (not os.path.exists(path)
        and is_win32
        and os.path.exists(path+'-script.py')
        ):
        path = path+'-script.py'
    with open(path) as f:
        print_(f.read(), end='')

def ls(dir, *subs):
    if subs:
        dir = os.path.join(dir, *subs)
    names = sorted(os.listdir(dir))
    for name in names:
        if os.path.isdir(os.path.join(dir, name)):
            print_('d ', end=' ')
        elif os.path.islink(os.path.join(dir, name)):
            print_('l ', end=' ')
        else:
            print_('- ', end=' ')
        print_(name)

def mkdir(*path):
    os.mkdir(os.path.join(*path))

def remove(*path):
    path = os.path.join(*path)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)

def rmdir(*path):
    shutil.rmtree(os.path.join(*path))

def write(dir, *args):
    path = os.path.join(dir, *(args[:-1]))
    f = open(path, 'w')
    f.write(args[-1])
    f.flush()
    fsync(f.fileno())
    f.close()

def clean_up_pyc(*path):
    base, filename = os.path.join(*path[:-1]), path[-1]
    if filename.endswith('.py'):
        filename += 'c' # .py -> .pyc
    for path in (
        os.path.join(base, filename),
        os.path.join(base, '__pycache__'),
        ):
        if os.path.isdir(path):
            rmdir(path)
        elif os.path.exists(path):
            remove(path)

## FIXME - check for other platforms
MUST_CLOSE_FDS = not sys.platform.startswith('win')

def system(command, input='', with_exit_code=False):
    p = subprocess.Popen(command,
                         shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=MUST_CLOSE_FDS)
    i, o, e = (p.stdin, p.stdout, p.stderr)
    if input:
        i.write(input.encode())
    i.close()
    result = o.read() + e.read()
    o.close()
    e.close()
    output = result.decode()
    if with_exit_code:
        # Use the with_exit_code=True parameter when you want to test the exit
        # code of the command you're running.
        output += 'EXIT CODE: %s' % p.wait()
    return output

def get(url):
    return str(urlopen(url).read().decode())

def _runsetup(setup, *args):
    if os.path.isdir(setup):
        setup = os.path.join(setup, 'setup.py')
    args = list(args)
    args.insert(0, '-q')
    here = os.getcwd()
    try:
        os.chdir(os.path.dirname(setup))
        zc.buildout.easy_install.call_subprocess(
            [sys.executable, setup] + args,
            env=dict(os.environ, PYTHONPATH=setuptools_location))
        if os.path.exists('build'):
            rmtree('build')
    finally:
        os.chdir(here)

def sdist(setup, dest):
    _runsetup(setup, 'sdist', '-d', dest, '--formats=zip')

def bdist_egg(setup, executable, dest=None):
    # Backward compat:
    if dest is None:
        dest = executable
    else:
        assert executable == sys.executable, (executable, sys.executable)
    _runsetup(setup, 'bdist_egg', '-d', dest)

def wait_until(label, func, *args, **kw):
    if 'timeout' in kw:
        kw = dict(kw)
        timeout = kw.pop('timeout')
    else:
        timeout = 30
    deadline = time.time()+timeout
    while time.time() < deadline:
        if func(*args, **kw):
            return
        time.sleep(0.01)
    raise ValueError('Timed out waiting for: '+label)

class TestOptions(zc.buildout.buildout.Options):

    def initialize(self):
        pass

class Buildout(zc.buildout.buildout.Buildout):

    def __init__(self):
        zc.buildout.buildout.Buildout.__init__(
            self, '', [('buildout', 'directory', os.getcwd())])

    Options = TestOptions

def buildoutSetUp(test):

    test.globs['__tear_downs'] = __tear_downs = []
    test.globs['register_teardown'] = register_teardown = __tear_downs.append

    prefer_final = zc.buildout.easy_install.prefer_final()
    register_teardown(
        lambda: zc.buildout.easy_install.prefer_final(prefer_final)
        )

    here = os.getcwd()
    register_teardown(lambda: os.chdir(here))

    handlers_before_set_up = logging.getLogger().handlers[:]
    def restore_root_logger_handlers():
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in handlers_before_set_up:
            root_logger.addHandler(handler)
    register_teardown(restore_root_logger_handlers)

    base = tempfile.mkdtemp('buildoutSetUp')
    base = os.path.realpath(base)
    register_teardown(lambda base=base: rmtree(base))

    old_home = os.environ.get('HOME')
    os.environ['HOME'] = os.path.join(base, 'bbbBadHome')
    def restore_home():
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
    register_teardown(restore_home)

    base = os.path.join(base, '_TEST_')
    os.mkdir(base)

    tmp = tempfile.mkdtemp('buildouttests')
    register_teardown(lambda: rmtree(tmp))

    zc.buildout.easy_install.default_index_url = 'file://'+tmp
    os.environ['buildout-testing-index-url'] = (
        zc.buildout.easy_install.default_index_url)

    def tmpdir(name):
        path = os.path.join(base, name)
        mkdir(path)
        return path

    sample = tmpdir('sample-buildout')

    os.chdir(sample)

    # Create a basic buildout.cfg to avoid a warning from buildout:
    with open('buildout.cfg', 'w') as f:
        f.write("[buildout]\nparts =\n")

    # Use the buildout bootstrap command to create a buildout
    zc.buildout.buildout.Buildout(
        'buildout.cfg',
        [('buildout', 'log-level', 'WARNING'),
         # trick bootstrap into putting the buildout develop egg
         # in the eggs dir.
         ('buildout', 'develop-eggs-directory', 'eggs'),
         ]
        ).bootstrap([])



    # Create the develop-eggs dir, which didn't get created the usual
    # way due to the trick above:
    os.mkdir('develop-eggs')

    def start_server(path):
        port, thread = _start_server(path, name=path)
        url = 'http://localhost:%s/' % port
        register_teardown(lambda: stop_server(url, thread))
        return url

    cdpaths = []
    def cd(*path):
        path = os.path.join(*path)
        cdpaths.append(os.path.abspath(os.getcwd()))
        os.chdir(path)

    def uncd():
        os.chdir(cdpaths.pop())

    test.globs.update(dict(
        sample_buildout = sample,
        ls = ls,
        cat = cat,
        mkdir = mkdir,
        rmdir = rmdir,
        remove = remove,
        tmpdir = tmpdir,
        write = write,
        system = system,
        get = get,
        cd = cd, uncd = uncd,
        join = os.path.join,
        sdist = sdist,
        bdist_egg = bdist_egg,
        start_server = start_server,
        buildout = os.path.join(sample, 'bin', 'buildout'),
        wait_until = wait_until,
        print_ = print_,
        clean_up_pyc = clean_up_pyc,
        ))

    zc.buildout.easy_install.prefer_final(prefer_final)

def buildoutTearDown(test):
    for f in test.globs['__tear_downs']:
        f()

class Server(HTTPServer):

    def __init__(self, tree, *args):
        HTTPServer.__init__(self, *args)
        self.tree = os.path.abspath(tree)

    __run = True
    def serve_forever(self):
        while self.__run:
            self.handle_request()

    def handle_error(self, *_):
        self.__run = False

class Handler(BaseHTTPRequestHandler):

    Server.__log = False

    def __init__(self, request, address, server):
        self.__server = server
        self.tree = server.tree
        BaseHTTPRequestHandler.__init__(self, request, address, server)

    def do_GET(self):
        if '__stop__' in self.path:
            raise SystemExit

        def k():
            self.send_response(200)
            out = '<html><body>k</body></html>\n'.encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(out)

        if self.path == '/enable_server_logging':
            self.__server.__log = True
            return k()

        if self.path == '/disable_server_logging':
            self.__server.__log = False
            return k()

        path = os.path.abspath(os.path.join(self.tree, *self.path.split('/')))
        if not (
            ((path == self.tree) or path.startswith(self.tree+os.path.sep))
            and
            os.path.exists(path)
            ):
            self.send_response(404, 'Not Found')
            #self.send_response(200)
            out = '<html><body>Not Found</body></html>'.encode()
            #out = '\n'.join(self.tree, self.path, path)
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(out)
            return

        self.send_response(200)
        if os.path.isdir(path):
            out = ['<html><body>\n']
            names = sorted(os.listdir(path))
            for name in names:
                if os.path.isdir(os.path.join(path, name)):
                    name += '/'
                out.append('<a href="%s">%s</a><br>\n' % (name, name))
            out.append('</body></html>\n')
            out = ''.join(out).encode()
            self.send_header('Content-Length', str(len(out)))
            self.send_header('Content-Type', 'text/html')
        else:
            with open(path, 'rb') as f:
                out = f.read()
            self.send_header('Content-Length', len(out))
            if path.endswith('.egg'):
                self.send_header('Content-Type', 'application/zip')
            elif path.endswith('.gz'):
                self.send_header('Content-Type', 'application/x-gzip')
            elif path.endswith('.zip'):
                self.send_header('Content-Type', 'application/x-gzip')
            else:
                self.send_header('Content-Type', 'text/html')

        self.end_headers()

        self.wfile.write(out)

    def log_request(self, code):
        if self.__server.__log:
            print_('%s %s %s' % (self.command, code, self.path))

def _run(tree, port):
    server_address = ('localhost', port)
    httpd = Server(tree, server_address, Handler)
    httpd.serve_forever()

def get_port():
    for i in range(10):
        port = random.randrange(20000, 30000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                s.connect(('localhost', port))
            except socket.error:
                return port
        finally:
            s.close()
    raise RuntimeError("Can't find port")

def _start_server(tree, name=''):
    port = get_port()
    thread = threading.Thread(target=_run, args=(tree, port), name=name)
    thread.setDaemon(True)
    thread.start()
    wait(port, up=True)
    return port, thread

def start_server(tree):
    return _start_server(tree)[0]

def stop_server(url, thread=None):
    try:
        urlopen(url+'__stop__')
    except Exception:
        pass
    if thread is not None:
        thread.join() # wait for thread to stop

def wait(port, up):
    addr = 'localhost', port
    for i in range(120):
        time.sleep(0.25)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(addr)
            s.close()
            if up:
                break
        except socket.error:
            e = sys.exc_info()[1]
            if e[0] not in (errno.ECONNREFUSED, errno.ECONNRESET):
                raise
            s.close()
            if not up:
                break
    else:
        if up:
            raise
        else:
            raise SystemError("Couln't stop server")

def install(project, destination):
    if not isinstance(destination, str):
        destination = os.path.join(destination.globs['sample_buildout'],
                                   'eggs')

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(project))
    if dist.location.endswith('.egg'):
        destination = os.path.join(destination,
                                   os.path.basename(dist.location),
                                   )
        if os.path.isdir(dist.location):
            shutil.copytree(dist.location, destination)
        else:
            shutil.copyfile(dist.location, destination)
    else:
        # copy link
        with open(os.path.join(destination, project+'.egg-link'), 'w') as f:
            f.write(dist.location)

def install_develop(project, destination):
    if not isinstance(destination, str):
        destination = os.path.join(destination.globs['sample_buildout'],
                                   'develop-eggs')

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(project))
    with open(os.path.join(destination, project+'.egg-link'), 'w') as f:
        f.write(dist.location)

def _normalize_path(match):
    path = match.group(1)
    if os.path.sep == '\\':
        path = path.replace('\\\\', '/')
        if path.startswith('\\'):
            path = path[1:]
    return '/' + path.replace(os.path.sep, '/')

normalize_path = (
    re.compile(
        r'''[^'" \t\n\r]+\%(sep)s_[Tt][Ee][Ss][Tt]_\%(sep)s([^"' \t\n\r]+)'''
        % dict(sep=os.path.sep)),
    _normalize_path,
    )

normalize_endings = re.compile('\r\n'), '\n'

normalize_script = (
    re.compile('(\n?)-  ([a-zA-Z_.-]+)-script.py\n-  \\2.exe\n'),
    '\\1-  \\2\n')

if sys.version_info > (2, ):
    normalize___pycache__ = (
        re.compile('(\n?)d  __pycache__\n'), '\\1')
else:
    normalize___pycache__ = (
        re.compile('(\n?)-  \S+\.pyc\n'), '\\1')

normalize_egg_py = (
    re.compile('-py\d[.]\d(-\S+)?.egg'),
    '-pyN.N.egg',
    )

normalize_exception_type_for_python_2_and_3 = (
    re.compile(r'^(\w+\.)*([A-Z][A-Za-z0-9]+Error: )'),
    '\2')

not_found = (re.compile(r'Not found: [^\n]+/(\w|\.)+/\r?\n'), '')

# Setuptools now pulls in dependencies when installed.
adding_find_link = (re.compile(r"Adding find link '[^']+'"
                               r" from setuptools .*\r?\n"), '')

ignore_not_upgrading = (
    re.compile(
    'Not upgrading because not running a local buildout command.\n'
    ), '')

########NEW FILE########
__FILENAME__ = testrecipes
from zc.buildout.buildout import print_

class Debug:

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

    def install(self):
        items = list(self.options.items())
        items.sort()
        for option, value in items:
            print_("  %s=%r" % (option, value))
        return ()

    update = install

########NEW FILE########
__FILENAME__ = tests
##############################################################################
#
# Copyright (c) 2004-2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from zc.buildout.buildout import print_
from zope.testing import renormalizing

import doctest
import manuel.capture
import manuel.doctest
import manuel.testing
import os
import pkg_resources
import re
import shutil
import sys
import tempfile
import unittest
import zc.buildout.easy_install
import zc.buildout.testing
import zipfile

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2


def develop_w_non_setuptools_setup_scripts():
    """
We should be able to deal with setup scripts that aren't setuptools based.

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... '''
    ... from distutils.core import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    """

def develop_verbose():
    """
We should be able to deal with setup scripts that aren't setuptools based.

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')+' -vv'), end='')
    ... # doctest: +ELLIPSIS
    Installing...
    Develop: '/sample-buildout/foo'
    ...
    Installed /sample-buildout/foo
    ...

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    >>> print_(system(join('bin', 'buildout')+' -vvv'), end='')
    ... # doctest: +ELLIPSIS
    Installing...
    Develop: '/sample-buildout/foo'
    in: '/sample-buildout/foo'
    ... -q develop -mxN -d /sample-buildout/develop-eggs/...


    """

def buildout_error_handling():
    r"""Buildout error handling

Asking for a section that doesn't exist, yields a missing section error:

    >>> import os
    >>> os.chdir(sample_buildout)
    >>> import zc.buildout.buildout
    >>> buildout = zc.buildout.buildout.Buildout('buildout.cfg', [])
    >>> buildout['eek']
    Traceback (most recent call last):
    ...
    MissingSection: The referenced section, 'eek', was not defined.

Asking for an option that doesn't exist, a MissingOption error is raised:

    >>> buildout['buildout']['eek']
    Traceback (most recent call last):
    ...
    MissingOption: Missing option: buildout:eek

It is an error to create a variable-reference cycle:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... x = ${buildout:y}
    ... y = ${buildout:z}
    ... z = ${buildout:x}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    ... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
      Getting option buildout:y.
      Getting option buildout:z.
      Getting option buildout:x.
    Error: Circular reference in substitutions.

It is an error to use funny characters in variable references:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${bui$ldout:y}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The section name in substitution, ${bui$ldout:y},
    has invalid characters.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y{z}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The option name in substitution, ${buildout:y{z},
    has invalid characters.

and too have too many or too few colons:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${parts}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The substitution, ${parts},
    doesn't contain a colon.

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data_dir debug
    ... x = ${buildout:y:z}
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Initializing.
      Getting section buildout.
      Initializing section buildout.
      Getting option buildout:x.
    Error: The substitution, ${buildout:y:z},
    has too many colons.

All parts have to have a section:

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Installing.
      Getting section x.
    Error: The referenced section, 'x', was not defined.

and all parts have to have a specified recipe:


    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ...
    ... [x]
    ... foo = 1
    ... ''')

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')),
    ...        end='')
    While:
      Installing.
    Error: Missing option: x:recipe

"""

make_dist_that_requires_setup_py_template = """
from setuptools import setup
setup(name=%r, version=%r,
      install_requires=%r,
      )
"""

def make_dist_that_requires(dest, name, requires=[], version=1, egg=''):
    os.mkdir(os.path.join(dest, name))
    open(os.path.join(dest, name, 'setup.py'), 'w').write(
        make_dist_that_requires_setup_py_template
        % (name, version, requires)
        )

def show_who_requires_when_there_is_a_conflict():
    """
It's a pain when we require eggs that have requirements that are
incompatible. We want the error we get to tell us what is missing.

Let's make a few develop distros, some of which have incompatible
requirements.

    >>> make_dist_that_requires(sample_buildout, 'sampley',
    ...                         ['demoneeded ==1.0'])
    >>> make_dist_that_requires(sample_buildout, 'samplez',
    ...                         ['demoneeded ==1.1'])

Now, let's create a buildout that requires y and z:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplez
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = sampley
    ...        samplez
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Installing eggs.
    Getting distribution for 'demoneeded==1.1'.
    Got demoneeded 1.1.
    While:
      Installing eggs.
    Error: There is a version conflict.
    We already have: demoneeded 1.1
    but sampley 1 requires 'demoneeded==1.0'.

Here, we see that sampley required an older version of demoneeded. What
if we hadn't required sampley ourselves:

    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplez samplea sampleb
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ...        samplez
    ... ''' % globals())

If we use the verbose switch, we can see where requirements are coming from:

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    We have a develop egg: zc.buildout 1.0.0
    We have the best distribution that satisfies 'setuptools'.
    Picked: setuptools = 0.7
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Develop: '/sample-buildout/samplea'
    Develop: '/sample-buildout/sampleb'
    ...Installing eggs.
    Installing 'samplea', 'samplez'.
    We have a develop egg: samplea 1
    We have a develop egg: samplez 1
    Getting required 'demoneeded==1.1'
      required by samplez 1.
    We have the distribution that satisfies 'demoneeded==1.1'.
    Getting required 'sampleb'
      required by samplea 1.
    We have a develop egg: sampleb 1
    Getting required 'sampley'
      required by sampleb 1.
    We have a develop egg: sampley 1
    While:
      Installing eggs.
    Error: There is a version conflict.
    We already have: demoneeded 1.1
    but sampley 1 requires 'demoneeded==1.0'.
    """

def show_who_requires_missing_distributions():
    """

When working with a lot of eggs, which require eggs recursively, it
can be hard to tell why we're requiring things we can't
find. Fortunately, buildout will tell us who's asking for something
that we can't find. when run in verbose mode

    >>> make_dist_that_requires(sample_buildout, 'sampley', ['demoneeded'])
    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sampley samplea sampleb
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''')

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing ...
    Installing 'samplea'.
    We have a develop egg: samplea 1
    Getting required 'sampleb'
      required by samplea 1.
    We have a develop egg: sampleb 1
    Getting required 'sampley'
      required by sampleb 1.
    We have a develop egg: sampley 1
    Getting required 'demoneeded'
      required by sampley 1.
    We have no distributions for demoneeded that satisfies 'demoneeded'.
    ...
    While:
      Installing eggs.
      Getting distribution for 'demoneeded'.
    Error: Couldn't find a distribution for 'demoneeded'.
    """

def show_who_requires_picked_versions():
    """

The show-picked-versions prints the versions, but it also prints who
required the picked distributions.
We do not need to run in verbose mode for that to work:

    >>> make_dist_that_requires(sample_buildout, 'sampley', ['setuptools'])
    >>> make_dist_that_requires(sample_buildout, 'samplea', ['sampleb'])
    >>> make_dist_that_requires(sample_buildout, 'sampleb',
    ...                         ['sampley', 'samplea'])
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... show-picked-versions = true
    ... develop = sampley samplea sampleb
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: ...
    Installing eggs.
    Versions had to be automatically picked.
    The following part definition lists the versions picked:
    [versions]
    <BLANKLINE>
    # Required by:
    # sampley==1
    setuptools = 0.7
    """

def test_comparing_saved_options_with_funny_characters():
    """
If an option has newlines, extra/odd spaces or a %, we need to make sure
the comparison with the saved value works correctly.

    >>> mkdir(sample_buildout, 'recipes')
    >>> write(sample_buildout, 'recipes', 'debug.py',
    ... '''
    ... class Debug:
    ...     def __init__(self, buildout, name, options):
    ...         options['debug'] = \"\"\"  <zodb>
    ...
    ...   <filestorage>
    ...     path foo
    ...   </filestorage>
    ...
    ... </zodb>
    ...      \"\"\"
    ...         options['debug1'] = \"\"\"
    ... <zodb>
    ...
    ...   <filestorage>
    ...     path foo
    ...   </filestorage>
    ...
    ... </zodb>
    ... \"\"\"
    ...         options['debug2'] = '  x  '
    ...         options['debug3'] = '42'
    ...         options['format'] = '%3d'
    ...
    ...     def install(self):
    ...         open('t', 'w').write('t')
    ...         return 't'
    ...
    ...     update = install
    ... ''')


    >>> write(sample_buildout, 'recipes', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(
    ...     name = "recipes",
    ...     entry_points = {'zc.buildout': ['default = debug:Debug']},
    ...     )
    ... ''')

    >>> write(sample_buildout, 'recipes', 'README.txt', " ")

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = debug
    ...
    ... [debug]
    ... recipe = recipes
    ... ''')

    >>> os.chdir(sample_buildout)
    >>> buildout = os.path.join(sample_buildout, 'bin', 'buildout')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing debug.

If we run the buildout again, we shoudn't get a message about
uninstalling anything because the configuration hasn't changed.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating debug.
"""

def finding_eggs_as_local_directories():
    r"""
It is possible to set up find-links so that we could install from
a local directory that may contained unzipped eggs.

    >>> src = tmpdir('src')
    >>> write(src, 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='demo', py_modules=[''],
    ...    zip_safe=False, version='1.0', author='bob', url='bob',
    ...    author_email='bob')
    ... ''')

    >>> write(src, 't.py', '#\n')
    >>> write(src, 'README.txt', '')
    >>> _ = system(join('bin', 'buildout')+' setup ' + src + ' bdist_egg')

Install it so it gets unzipped:

    >>> d1 = tmpdir('d1')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], d1, links=[join(src, 'dist')],
    ...     )

    >>> ls(d1)
    d  demo-1.0-py2.4.egg

Then try to install it again:

    >>> d2 = tmpdir('d2')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo'], d2, links=[d1],
    ...     )

    >>> ls(d2)
    d  demo-1.0-py2.4.egg

    """

def create_sections_on_command_line():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... x = ${foo:bar}
    ... ''')

    >>> print_(system(buildout + ' foo:bar=1 -vv'), end='')
    ...        # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    [foo]
    bar = 1
    ...

    """

def test_help():
    """
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')+' -h'))
    ... # doctest: +ELLIPSIS
    Usage: buildout [options] [assignments] [command [command arguments]]
    <BLANKLINE>
    Options:
    <BLANKLINE>
      -h, --help
    ...

    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              +' --help'))
    ... # doctest: +ELLIPSIS
    Usage: buildout [options] [assignments] [command [command arguments]]
    <BLANKLINE>
    Options:
    <BLANKLINE>
      -h, --help
    ...
    """

def test_version():
    """
    >>> buildout = os.path.join(sample_buildout, 'bin', 'buildout')
    >>> print_(system(buildout+' --version'))
    ... # doctest: +ELLIPSIS
    buildout version ...

    """

def test_bootstrap_with_extension():
    """
We had a problem running a bootstrap with an extension.  Let's make
sure it is fixed.  Basically, we don't load extensions when
bootstrapping.

    >>> d = tmpdir('sample-bootstrap')

    >>> write(d, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... extensions = some_awsome_extension
    ... parts =
    ... ''')

    >>> os.chdir(d)
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              + ' bootstrap'), end='')
    Creating directory '/sample-bootstrap/bin'.
    Creating directory '/sample-bootstrap/parts'.
    Creating directory '/sample-bootstrap/eggs'.
    Creating directory '/sample-bootstrap/develop-eggs'.
    Generated script '/sample-bootstrap/bin/buildout'.
    """


def bug_92891_bootstrap_crashes_with_egg_recipe_in_buildout_section():
    """
    >>> d = tmpdir('sample-bootstrap')

    >>> write(d, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = buildout
    ... eggs-directory = eggs
    ...
    ... [buildout]
    ... recipe = zc.recipe.egg
    ... eggs = zc.buildout
    ... scripts = buildout=buildout
    ... ''')

    >>> os.chdir(d)
    >>> print_(system(os.path.join(sample_buildout, 'bin', 'buildout')
    ...              + ' bootstrap'), end='')
    Creating directory '/sample-bootstrap/bin'.
    Creating directory '/sample-bootstrap/parts'.
    Creating directory '/sample-bootstrap/eggs'.
    Creating directory '/sample-bootstrap/develop-eggs'.
    Generated script '/sample-bootstrap/bin/buildout'.

    >>> print_(system(os.path.join('bin', 'buildout')), end='')
    Unused options for buildout: 'scripts' 'eggs'.

    """

def removing_eggs_from_develop_section_causes_egg_link_to_be_removed():
    '''
    >>> cd(sample_buildout)

Create a develop egg:

    >>> mkdir('foo')
    >>> write('foo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='foox')
    ... """)
    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foox.egg-link
    -  zc.recipe.egg.egg-link

Create another:

    >>> mkdir('bar')
    >>> write('bar', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='fooy')
    ... """)
    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo bar
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'
    Develop: '/sample-buildout/bar'

    >>> ls('develop-eggs')
    -  foox.egg-link
    -  fooy.egg-link
    -  zc.recipe.egg.egg-link

Remove one:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = bar
    ... parts =
    ... """)
    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/bar'

It is gone

    >>> ls('develop-eggs')
    -  fooy.egg-link
    -  zc.recipe.egg.egg-link

Remove the other:

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... parts =
    ... """)
    >>> print_(system(join('bin', 'buildout')), end='')

All gone

    >>> ls('develop-eggs')
    -  zc.recipe.egg.egg-link
    '''


def add_setuptools_to_dependencies_when_namespace_packages():
    '''
Often, a package depends on setuptools solely by virtue of using
namespace packages. In this situation, package authors often forget to
declare setuptools as a dependency. This is a mistake, but,
unfortunately, a common one that we need to work around.  If an egg
uses namespace packages and does not include setuptools as a dependency,
we will still include setuptools in the working set.  If we see this for
a develop egg, we will also generate a warning.

    >>> mkdir('foo')
    >>> mkdir('foo', 'src')
    >>> mkdir('foo', 'src', 'stuff')
    >>> write('foo', 'src', 'stuff', '__init__.py',
    ... """__import__('pkg_resources').declare_namespace(__name__)
    ... """)
    >>> mkdir('foo', 'src', 'stuff', 'foox')
    >>> write('foo', 'src', 'stuff', 'foox', '__init__.py', '')
    >>> write('foo', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='foox',
    ...       namespace_packages = ['stuff'],
    ...       package_dir = {'': 'src'},
    ...       packages = ['stuff', 'stuff.foox'],
    ...       )
    ... """)
    >>> write('foo', 'README.txt', '')

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

Now, if we generate a working set using the egg link, we will get a warning
and we will get setuptools included in the working set.

    >>> import logging, zope.testing.loggingsupport
    >>> handler = zope.testing.loggingsupport.InstalledHandler(
    ...        'zc.buildout.easy_install', level=logging.WARNING)
    >>> logging.getLogger('zc.buildout.easy_install').propagate = False

    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['foox'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['foox', 'setuptools']

    >>> print_(handler)
    zc.buildout.easy_install WARNING
      Develop distribution: foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.

    >>> handler.clear()

On the other hand, if we have a regular egg, rather than a develop egg:

    >>> os.remove(join('develop-eggs', 'foox.egg-link'))

    >>> _ = system(join('bin', 'buildout') + ' setup foo bdist_egg -d'
    ...            + join(sample_buildout, 'eggs'))

    >>> ls('develop-eggs')
    -  zc.recipe.egg.egg-link

    >>> ls('eggs') # doctest: +ELLIPSIS
    -  foox-0.0.0-py2.4.egg
    d  setuptools.eggpyN.N.egg
    ...

We do not get a warning, but we do get setuptools included in the working set:

    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['foox'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['foox', 'setuptools']

    >>> print_(handler, end='')

We get the same behavior if the it is a dependency that uses a
namespace package.


    >>> mkdir('bar')
    >>> write('bar', 'setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name='bar', install_requires = ['foox'])
    ... """)
    >>> write('bar', 'README.txt', '')

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = foo bar
    ... parts =
    ... """)

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'
    Develop: '/sample-buildout/bar'

    >>> [dist.project_name
    ...  for dist in zc.buildout.easy_install.working_set(
    ...    ['bar'], sys.executable,
    ...    [join(sample_buildout, 'eggs'),
    ...     join(sample_buildout, 'develop-eggs'),
    ...     ])]
    ['bar', 'foox', 'setuptools']

    >>> print_(handler, end='')
    zc.buildout.easy_install WARNING
      Develop distribution: foox 0.0.0
    uses namespace packages but the distribution does not require setuptools.


    >>> logging.getLogger('zc.buildout.easy_install').propagate = True
    >>> handler.uninstall()

    '''

def develop_preserves_existing_setup_cfg():
    """

See "Handling custom build options for extensions in develop eggs" in
easy_install.txt.  This will be very similar except that we'll have an
existing setup.cfg:

    >>> write(extdemo, "setup.cfg",
    ... '''
    ... # sampe cfg file
    ...
    ... [foo]
    ... bar = 1
    ...
    ... [build_ext]
    ... define = X,Y
    ... ''')

    >>> mkdir('include')
    >>> write('include', 'extdemo.h',
    ... '''
    ... #define EXTDEMO 42
    ... ''')

    >>> dest = tmpdir('dest')
    >>> zc.buildout.easy_install.develop(
    ...   extdemo, dest,
    ...   {'include-dirs': os.path.join(sample_buildout, 'include')})
    '/dest/extdemo.egg-link'

    >>> ls(dest)
    -  extdemo.egg-link

    >>> cat(extdemo, "setup.cfg")
    <BLANKLINE>
    # sampe cfg file
    <BLANKLINE>
    [foo]
    bar = 1
    <BLANKLINE>
    [build_ext]
    define = X,Y

"""

def uninstall_recipes_used_for_removal():
    r"""
Uninstall recipes need to be called when a part is removed too:

    >>> mkdir("recipes")
    >>> write("recipes", "setup.py",
    ... '''
    ... from setuptools import setup
    ... setup(name='recipes',
    ...       entry_points={
    ...          'zc.buildout': ["demo=demo:Install"],
    ...          'zc.buildout.uninstall': ["demo=demo:uninstall"],
    ...          })
    ... ''')

    >>> write("recipes", "demo.py",
    ... r'''
    ... import sys
    ... class Install:
    ...     def __init__(*args): pass
    ...     def install(self):
    ...         sys.stdout.write('installing\n')
    ...         return ()
    ... def uninstall(name, options):
    ...     sys.stdout.write('uninstalling\n')
    ... ''')

    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Installing demo.
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts = demo
    ... [demo]
    ... recipe = recipes:demo
    ... x = 1
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling demo.
    Running uninstall recipe.
    uninstalling
    Installing demo.
    installing


    >>> write('buildout.cfg', '''
    ... [buildout]
    ... develop = recipes
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling demo.
    Running uninstall recipe.
    uninstalling

"""

def extensions_installed_as_eggs_work_in_offline_mode():
    '''
    >>> mkdir('demo')

    >>> write('demo', 'demo.py',
    ... r"""
    ... import sys
    ... def print_(*args):
    ...     sys.stdout.write(' '.join(map(str, args)) + '\\n')
    ... def ext(buildout):
    ...     print_('ext', sorted(buildout))
    ... """)

    >>> write('demo', 'setup.py',
    ... """
    ... from setuptools import setup
    ...
    ... setup(
    ...     name = "demo",
    ...     py_modules=['demo'],
    ...     entry_points = {'zc.buildout.extension': ['ext = demo:ext']},
    ...     )
    ... """)

    >>> bdist_egg(join(sample_buildout, "demo"), sys.executable,
    ...           join(sample_buildout, "eggs"))

    >>> write(sample_buildout, 'buildout.cfg',
    ... """
    ... [buildout]
    ... extensions = demo
    ... parts =
    ... offline = true
    ... """)

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    ext ['buildout', 'versions']


    '''

def changes_in_svn_or_CVS_dont_affect_sig():
    """

If we have a develop recipe, it's signature shouldn't be affected to
changes in .svn or CVS directories.

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default=foo:Foo']})
    ... ''')
    >>> write('recipe', 'foo.py',
    ... '''
    ... class Foo:
    ...     def __init__(*args): pass
    ...     def install(*args): return ()
    ...     update = install
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')


    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> mkdir('recipe', '.svn')
    >>> mkdir('recipe', 'CVS')
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    >>> write('recipe', '.svn', 'x', '1')
    >>> write('recipe', 'CVS', 'x', '1')

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    """

if hasattr(os, 'symlink'):
    def bug_250537_broken_symlink_doesnt_affect_sig():
        """
If we have a develop recipe, it's signature shouldn't be affected by
broken symlinks, and better yet, computing the hash should not break
because of the missing target file.

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default=foo:Foo']})
    ... ''')
    >>> write('recipe', 'foo.py',
    ... '''
    ... class Foo:
    ...     def __init__(*args): pass
    ...     def install(*args): return ()
    ...     update = install
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')


    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> write('recipe', 'some-file', '1')
    >>> os.symlink(join('recipe', 'some-file'),
    ...            join('recipe', 'another-file'))
    >>> remove('recipe', 'some-file')

    >>> print_(system(join(sample_buildout, 'bin', 'buildout')), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    """

def o_option_sets_offline():
    """
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')+' -vvo'), end='')
    ... # doctest: +ELLIPSIS
    <BLANKLINE>
    ...
    offline = true
    ...
    """

def recipe_upgrade():
    r"""

The buildout will upgrade recipes in newest (and non-offline) mode.

Let's create a recipe egg

    >>> mkdir('recipe')
    >>> write('recipe', 'recipe.py',
    ... r'''
    ... import sys
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         sys.stdout.write('recipe v1\n')
    ...         return ()
    ...     update = install
    ... ''')

    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe', version='1', py_modules=['recipe'],
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')

    >>> write('recipe', 'README', '')

    >>> print_(system(buildout+' setup recipe bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'recipe/setup.py'.
    ...

    >>> rmdir('recipe', 'build')

And update our buildout to use it.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = %s
    ...
    ... [foo]
    ... recipe = recipe
    ... ''' % join('recipe', 'dist'))

    >>> print_(system(buildout), end='')
    Getting distribution for 'recipe'.
    Got recipe 1.
    Installing foo.
    recipe v1

Now, if we update the recipe egg:

    >>> write('recipe', 'recipe.py',
    ... r'''
    ... import sys
    ... class Recipe:
    ...     def __init__(*a): pass
    ...     def install(self):
    ...         sys.stdout.write('recipe v2\n')
    ...         return ()
    ...     update = install
    ... ''')

    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe', version='2', py_modules=['recipe'],
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')


    >>> print_(system(buildout+' setup recipe bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'recipe/setup.py'.
    ...

We won't get the update if we specify -N:

    >>> print_(system(buildout+' -N'), end='')
    Updating foo.
    recipe v1

or if we use -o:

    >>> print_(system(buildout+' -o'), end='')
    Updating foo.
    recipe v1

But we will if we use neither of these:

    >>> print_(system(buildout), end='')
    Getting distribution for 'recipe'.
    Got recipe 2.
    Uninstalling foo.
    Installing foo.
    recipe v2

We can also select a particular recipe version:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = %s
    ...
    ... [foo]
    ... recipe = recipe ==1
    ... ''' % join('recipe', 'dist'))

    >>> print_(system(buildout), end='')
    Uninstalling foo.
    Installing foo.
    recipe v1

    """

def update_adds_to_uninstall_list():
    """

Paths returned by the update method are added to the list of paths to
uninstall

    >>> mkdir('recipe')
    >>> write('recipe', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='recipe',
    ...       entry_points={'zc.buildout': ['default = recipe:Recipe']},
    ...       )
    ... ''')

    >>> write('recipe', 'recipe.py',
    ... '''
    ... import os
    ... class Recipe:
    ...     def __init__(*_): pass
    ...     def install(self):
    ...         r = ('a', 'b', 'c')
    ...         for p in r: os.mkdir(p)
    ...         return r
    ...     def update(self):
    ...         r = ('c', 'd', 'e')
    ...         for p in r:
    ...             if not os.path.exists(p):
    ...                os.mkdir(p)
    ...         return r
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipe
    ... parts = foo
    ...
    ... [foo]
    ... recipe = recipe
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipe'
    Installing foo.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipe'
    Updating foo.

    >>> cat('.installed.cfg') # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    [buildout]
    ...
    [foo]
    __buildout_installed__ = a
    	b
    	c
    	d
    	e
    __buildout_signature__ = ...

"""

def log_when_there_are_not_local_distros():
    """
    >>> from zope.testing.loggingsupport import InstalledHandler
    >>> handler = InstalledHandler('zc.buildout.easy_install')
    >>> import logging
    >>> logger = logging.getLogger('zc.buildout.easy_install')
    >>> old_propogate = logger.propagate
    >>> logger.propagate = False

    >>> dest = tmpdir('sample-install')
    >>> import zc.buildout.easy_install
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], dest,
    ...     links=[link_server], index=link_server+'index/')

    >>> print_(handler) # doctest: +ELLIPSIS
    zc.buildout.easy_install DEBUG
      Installing 'demo==0.2'.
    zc.buildout.easy_install DEBUG
      We have no distributions for demo that satisfies 'demo==0.2'.
    ...

    >>> handler.uninstall()
    >>> logger.propagate = old_propogate

    """

def internal_errors():
    """Internal errors are clearly marked and don't generate tracebacks:

    >>> mkdir(sample_buildout, 'recipes')

    >>> write(sample_buildout, 'recipes', 'mkdir.py',
    ... '''
    ... class Mkdir:
    ...     def __init__(self, buildout, name, options):
    ...         self.name, self.options = name, options
    ...         options['path'] = os.path.join(
    ...                               buildout['buildout']['directory'],
    ...                               options['path'],
    ...                               )
    ... ''')

    >>> write(sample_buildout, 'recipes', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name = "recipes",
    ...       entry_points = {'zc.buildout': ['mkdir = mkdir:Mkdir']},
    ...       )
    ... ''')

    >>> write(sample_buildout, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = data-dir
    ...
    ... [data-dir]
    ... recipe = recipes:mkdir
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: '/sample-buildout/recipes'
    While:
      Installing.
      Getting section data-dir.
      Initializing section data-dir.
    <BLANKLINE>
    An internal error occurred due to a bug in either zc.buildout or in a
    recipe being used:
    Traceback (most recent call last):
    ...
    NameError: global name 'os' is not defined
    """

def whine_about_unused_options():
    '''

    >>> write('foo.py',
    ... """
    ... class Foo:
    ...
    ...     def __init__(self, buildout, name, options):
    ...         self.name, self.options = name, options
    ...         options['x']
    ...
    ...     def install(self):
    ...         self.options['y']
    ...         return ()
    ... """)

    >>> write('setup.py',
    ... """
    ... from setuptools import setup
    ... setup(name = "foo",
    ...       entry_points = {'zc.buildout': ['default = foo:Foo']},
    ...       )
    ... """)

    >>> write('buildout.cfg',
    ... """
    ... [buildout]
    ... develop = .
    ... parts = foo
    ... a = 1
    ...
    ... [foo]
    ... recipe = foo
    ... x = 1
    ... y = 1
    ... z = 1
    ... """)

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/.'
    Unused options for buildout: 'a'.
    Installing foo.
    Unused options for foo: 'z'.
    '''

def abnormal_exit():
    """
People sometimes hit control-c while running a builout. We need to make
sure that the installed database Isn't corrupted.  To test this, we'll create
some evil recipes that exit uncleanly:

    >>> mkdir('recipes')
    >>> write('recipes', 'recipes.py',
    ... '''
    ... import os
    ...
    ... class Clean:
    ...     def __init__(*_): pass
    ...     def install(_): return ()
    ...     def update(_): pass
    ...
    ... class EvilInstall(Clean):
    ...     def install(_): os._exit(1)
    ...
    ... class EvilUpdate(Clean):
    ...     def update(_): os._exit(1)
    ... ''')

    >>> write('recipes', 'setup.py',
    ... '''
    ... import setuptools
    ... setuptools.setup(name='recipes',
    ...    entry_points = {
    ...      'zc.buildout': [
    ...          'clean = recipes:Clean',
    ...          'evil_install = recipes:EvilInstall',
    ...          'evil_update = recipes:EvilUpdate',
    ...          'evil_uninstall = recipes:Clean',
    ...          ],
    ...       },
    ...     )
    ... ''')

Now let's look at 3 cases:

1. We exit during installation after installing some other parts:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:evil_install
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating p1.
    Updating p2.
    Installing p3.

    >>> print_(system(buildout+' buildout:parts='), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p2.
    Uninstalling p1.

2. We exit while updating:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:evil_update
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.
    Installing p4.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Updating p1.
    Updating p2.
    Updating p3.

    >>> print_(system(buildout+' buildout:parts='), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p2.
    Uninstalling p1.
    Uninstalling p4.
    Uninstalling p3.

3. We exit while installing or updating after uninstalling:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:evil_update
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Installing p1.
    Installing p2.
    Installing p3.
    Installing p4.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:evil_update
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... x = 1
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p4.
    Updating p1.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = recipes
    ... parts = p1 p2 p3 p4
    ...
    ... [p1]
    ... recipe = recipes:clean
    ...
    ... [p2]
    ... recipe = recipes:clean
    ...
    ... [p3]
    ... recipe = recipes:clean
    ...
    ... [p4]
    ... recipe = recipes:clean
    ... ''')

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/recipes'
    Uninstalling p1.
    Installing p1.
    Updating p2.
    Updating p3.
    Installing p4.

    """

def install_source_dist_with_bad_py():
    r"""

    >>> mkdir('badegg')
    >>> mkdir('badegg', 'badegg')
    >>> write('badegg', 'badegg', '__init__.py', '#\\n')
    >>> mkdir('badegg', 'badegg', 'scripts')
    >>> write('badegg', 'badegg', 'scripts', '__init__.py', '#\\n')
    >>> write('badegg', 'badegg', 'scripts', 'one.py',
    ... '''
    ... return 1
    ... ''')

    >>> write('badegg', 'setup.py',
    ... '''
    ... from setuptools import setup, find_packages
    ... setup(
    ...     name='badegg',
    ...     version='1',
    ...     packages = find_packages('.'),
    ...     zip_safe=False)
    ... ''')

    >>> print_(system(buildout+' setup badegg sdist'), end='') # doctest: +ELLIPSIS
    Running setup script 'badegg/setup.py'.
    ...

    >>> dist = join('badegg', 'dist')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs bo
    ... find-links = %(dist)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = badegg
    ...
    ... [bo]
    ... recipe = zc.recipe.egg
    ... eggs = zc.buildout
    ... scripts = buildout=bo
    ... ''' % globals())

    >>> print_(system(buildout));print_('X') # doctest: +ELLIPSIS
    Installing eggs.
    Getting distribution for 'badegg'.
    Got badegg 1.
    Installing bo.
    ...
    SyntaxError: ...'return' outside function...
    ...
    SyntaxError: ...'return' outside function...
    ...

    >>> ls('eggs') # doctest: +ELLIPSIS
    d  badegg-1-py2.4.egg
    ...

    >>> ls('bin')
    -  bo
    -  buildout
    """

def version_requirements_in_build_honored():
    '''

    >>> update_extdemo()
    >>> dest = tmpdir('sample-install')
    >>> mkdir('include')
    >>> write('include', 'extdemo.h',
    ... """
    ... #define EXTDEMO 42
    ... """)

    >>> zc.buildout.easy_install.build(
    ...   'extdemo ==1.4', dest,
    ...   {'include-dirs': os.path.join(sample_buildout, 'include')},
    ...   links=[link_server], index=link_server+'index/',
    ...   newest=False)
    ['/sample-install/extdemo-1.4-py2.4-linux-i686.egg']

    '''

def bug_105081_Specific_egg_versions_are_ignored_when_newer_eggs_are_around():
    """
    Buildout might ignore a specific egg requirement for a recipe:

    - Have a newer version of an egg in your eggs directory
    - Use 'recipe==olderversion' in your buildout.cfg to request an
      older version

    Buildout will go and fetch the older version, but it will *use*
    the newer version when installing a part with this recipe.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... find-links = %(sample_eggs)s
    ...
    ... [x]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Installing x.
    Getting distribution for 'demo'.
    Got demo 0.3.
    Getting distribution for 'demoneeded'.
    Got demoneeded 1.1.
    Generated script '/sample-buildout/bin/demo'.

    >>> print_(system(join('bin', 'demo')), end='')
    3 1

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = x
    ... find-links = %(sample_eggs)s
    ...
    ... [x]
    ... recipe = zc.recipe.egg
    ... eggs = demo ==0.1
    ... ''' % globals())

    >>> print_(system(buildout), end='')
    Uninstalling x.
    Installing x.
    Getting distribution for 'demo==0.1'.
    Got demo 0.1.
    Generated script '/sample-buildout/bin/demo'.

    >>> print_(system(join('bin', 'demo')), end='')
    1 1
    """

if sys.version_info > (2, 4):
    def test_exit_codes():
        """
        >>> import subprocess
        >>> def call(s):
        ...     p = subprocess.Popen(s, stdin=subprocess.PIPE,
        ...                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ...     p.stdin.close()
        ...     print_(p.stdout.read().decode())
        ...     print_('Exit:', bool(p.wait()))

        >>> call(buildout)
        <BLANKLINE>
        Exit: False

        >>> write('buildout.cfg',
        ... '''
        ... [buildout]
        ... parts = x
        ... ''')

        >>> call(buildout) # doctest: +NORMALIZE_WHITESPACE
        While:
          Installing.
          Getting section x.
        Error: The referenced section, 'x', was not defined.
        <BLANKLINE>
        Exit: True

        >>> write('setup.py',
        ... '''
        ... from setuptools import setup
        ... setup(name='zc.buildout.testexit', entry_points={
        ...    'zc.buildout': ['default = testexitrecipe:x']})
        ... ''')

        >>> write('testexitrecipe.py',
        ... '''
        ... x y
        ... ''')

        >>> write('buildout.cfg',
        ... '''
        ... [buildout]
        ... parts = x
        ... develop = .
        ...
        ... [x]
        ... recipe = zc.buildout.testexit
        ... ''')

        >>> call(buildout) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Develop: '/sample-buildout/.'
        While:
          Installing.
          Getting section x.
          Initializing section x.
          Loading zc.buildout recipe entry zc.buildout.testexit:default.
        <BLANKLINE>
        An internal error occurred due to a bug in either zc.buildout or in a
        recipe being used:
        Traceback (most recent call last):
        ...
             x y
               ^
         SyntaxError: invalid syntax
        <BLANKLINE>
        Exit: True
        """

def bug_59270_recipes_always_start_in_buildout_dir():
    r"""
    Recipes can rely on running from buildout directory

    >>> mkdir('bad_start')
    >>> write('bad_recipe.py',
    ... r'''
    ... import os, sys
    ... def print_(*args):
    ...     sys.stdout.write(' '.join(map(str, args)) + '\n')
    ... class Bad:
    ...     def __init__(self, *_):
    ...         print_(os.getcwd())
    ...     def install(self):
    ...         sys.stdout.write(os.getcwd()+'\n')
    ...         os.chdir('bad_start')
    ...         sys.stdout.write(os.getcwd()+'\n')
    ...         return ()
    ... ''')

    >>> write('setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='bad.test',
    ...       entry_points={'zc.buildout': ['default=bad_recipe:Bad']},)
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = .
    ... parts = b1 b2
    ... [b1]
    ... recipe = bad.test
    ... [b2]
    ... recipe = bad.test
    ... ''')

    >>> os.chdir('bad_start')
    >>> print_(system(join(sample_buildout, 'bin', 'buildout')
    ...              +' -c '+join(sample_buildout, 'buildout.cfg')), end='')
    Develop: '/sample-buildout/.'
    /sample-buildout
    /sample-buildout
    Installing b1.
    /sample-buildout
    /sample-buildout/bad_start
    Installing b2.
    /sample-buildout
    /sample-buildout/bad_start
    """

def bug_61890_file_urls_dont_seem_to_work_in_find_dash_links():
    """

    This bug arises from the fact that setuptools is overly restrictive
    about file urls, requiring that file urls pointing at directories
    must end in a slash.

    >>> dest = tmpdir('sample-install')
    >>> import zc.buildout.easy_install
    >>> sample_eggs = sample_eggs.replace(os.path.sep, '/')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], dest,
    ...     links=['file://'+sample_eggs], index=link_server+'index/')


    >>> for dist in ws:
    ...     print_(dist)
    demo 0.2
    demoneeded 1.1

    >>> ls(dest)
    d  demo-0.2-py2.4.egg
    d  demoneeded-1.1-py2.4.egg

    """

def bug_75607_buildout_should_not_run_if_it_creates_an_empty_buildout_cfg():
    """
    >>> remove('buildout.cfg')
    >>> print_(system(buildout), end='')
    While:
      Initializing.
    Error: Couldn't open /sample-buildout/buildout.cfg



    """

def dealing_with_extremely_insane_dependencies():
    r"""

    There was a problem with analysis of dependencies taking a long
    time, in part because the analysis would get repeated every time a
    package was encountered in a dependency list.  Now, we don't do
    the analysis any more:

    >>> import os
    >>> for i in range(5):
    ...     p = 'pack%s' % i
    ...     deps = [('pack%s' % j) for j in range(5) if j is not i]
    ...     if i == 4:
    ...         deps.append('pack5')
    ...     mkdir(p)
    ...     write(p, 'setup.py',
    ...           'from setuptools import setup\n'
    ...           'setup(name=%r, install_requires=%r,\n'
    ...           '      url="u", author="a", author_email="e")\n'
    ...           % (p, deps))

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = pack0 pack1 pack2 pack3 pack4
    ... parts = pack1
    ...
    ... [pack1]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = pack0
    ... ''')

    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Develop: '/sample-buildout/pack0'
    Develop: '/sample-buildout/pack1'
    Develop: '/sample-buildout/pack2'
    Develop: '/sample-buildout/pack3'
    Develop: '/sample-buildout/pack4'
    Installing pack1.
    ...
    While:
      Installing pack1.
      Getting distribution for 'pack5'.
    Error: Couldn't find a distribution for 'pack5'.

    However, if we run in verbose mode, we can see why packages were included:

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    We have a develop egg: zc.buildout 1.0.0
    We have the best distribution that satisfies 'setuptools'.
    Picked: setuptools = 0.7
    Develop: '/sample-buildout/pack0'
    Develop: '/sample-buildout/pack1'
    Develop: '/sample-buildout/pack2'
    Develop: '/sample-buildout/pack3'
    Develop: '/sample-buildout/pack4'
    ...Installing pack1.
    Installing 'pack0'.
    We have a develop egg: pack0 0.0.0
    Getting required 'pack4'
      required by pack0 0.0.0.
    We have a develop egg: pack4 0.0.0
    Getting required 'pack3'
      required by pack0 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack3 0.0.0
    Getting required 'pack2'
      required by pack0 0.0.0.
      required by pack3 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack2 0.0.0
    Getting required 'pack1'
      required by pack0 0.0.0.
      required by pack2 0.0.0.
      required by pack3 0.0.0.
      required by pack4 0.0.0.
    We have a develop egg: pack1 0.0.0
    Getting required 'pack5'
      required by pack4 0.0.0.
    We have no distributions for pack5 that satisfies 'pack5'.
    ...
    While:
      Installing pack1.
      Getting distribution for 'pack5'.
    Error: Couldn't find a distribution for 'pack5'.
    """

def read_find_links_to_load_extensions():
    r"""
We'll create a wacky buildout extension that just announces itself when used:

    >>> src = tmpdir('src')
    >>> write(src, 'wacky_handler.py',
    ... '''
    ... import sys
    ... def install(buildout=None):
    ...     sys.stdout.write("I am a wacky extension\\n")
    ... ''')
    >>> write(src, 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='wackyextension', version='1',
    ...       py_modules=['wacky_handler'],
    ...       entry_points = {'zc.buildout.extension':
    ...             ['default = wacky_handler:install']
    ...             },
    ...       )
    ... ''')
    >>> print_(system(buildout+' setup '+src+' bdist_egg'), end='')
    ... # doctest: +ELLIPSIS
    Running setup ...
    creating 'dist/wackyextension-1-...

Now we'll create a buildout that uses this extension to load other packages:

    >>> wacky_server = link_server.replace('http', 'wacky')
    >>> dist = 'file://' + join(src, 'dist').replace(os.path.sep, '/')
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... extensions = wackyextension
    ... find-links = %(dist)s
    ... ''' % globals())

When we run the buildout. it will load the extension from the dist
directory and then use the wacky extension to load the demo package

    >>> print_(system(buildout), end='')
    Getting distribution for 'wackyextension'.
    Got wackyextension 1.
    I am a wacky extension

    """

def distributions_from_local_find_links_make_it_to_download_cache():
    """

If we specify a local directory in find links, distros found there
need to make it to the download cache.

    >>> mkdir('test')
    >>> write('test', 'setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='foo')
    ... ''')

    >>> print_(system(buildout+' setup test bdist_egg')) # doctest: +ELLIPSIS
    Running setup script 'test/setup.py'.
    ...


    >>> mkdir('cache')
    >>> old_cache = zc.buildout.easy_install.download_cache('cache')
    >>> list(zc.buildout.easy_install.install(['foo'], 'eggs',
    ...          links=[join('test', 'dist')])) # doctest: +ELLIPSIS
    [foo 0.0.0 ...

    >>> ls('cache')
    -  foo-0.0.0-py2.4.egg

    >>> _ = zc.buildout.easy_install.download_cache(old_cache)

    """

def create_egg(name, version, dest, install_requires=None,
               dependency_links=None):
    d = tempfile.mkdtemp()
    if dest=='available':
        extras = dict(x=['x'])
    else:
        extras = {}
    if dependency_links:
        links = 'dependency_links = %s, ' % dependency_links
    else:
        links = ''
    if install_requires:
        requires = 'install_requires = %s, ' % install_requires
    else:
        requires = ''
    try:
        open(os.path.join(d, 'setup.py'), 'w').write(
            'from setuptools import setup\n'
            'setup(name=%r, version=%r, extras_require=%r, zip_safe=True,\n'
            '      %s %s py_modules=["setup"]\n)'
            % (name, str(version), extras, requires, links)
            )
        zc.buildout.testing.bdist_egg(d, sys.executable, os.path.abspath(dest))
    finally:
        shutil.rmtree(d)

def prefer_final_permutation(existing, available):
    for d in ('existing', 'available'):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.mkdir(d)
    for version in existing:
        create_egg('spam', version, 'existing')
    for version in available:
        create_egg('spam', version, 'available')

    zc.buildout.easy_install.clear_index_cache()
    [dist] = list(
        zc.buildout.easy_install.install(['spam'], 'existing', ['available'])
        )

    if dist.extras:
        print_('downloaded', dist.version)
    else:
        print_('had', dist.version)
    sys.path_importer_cache.clear()

def prefer_final():
    """
This test tests several permutations:

Using different version numbers to work around zip importer cache problems. :(

- With prefer final:

    - no existing and newer dev available
    >>> prefer_final_permutation((), [1, '2a1'])
    downloaded 1

    - no existing and only dev available
    >>> prefer_final_permutation((), ['3a1'])
    downloaded 3a1

    - final existing and only dev acailable
    >>> prefer_final_permutation([4], ['5a1'])
    had 4

    - final existing and newer final available
    >>> prefer_final_permutation([6], [7])
    downloaded 7

    - final existing and same final available
    >>> prefer_final_permutation([8], [8])
    had 8

    - final existing and older final available
    >>> prefer_final_permutation([10], [9])
    had 10

    - only dev existing and final available
    >>> prefer_final_permutation(['12a1'], [11])
    downloaded 11

    - only dev existing and no final available newer dev available
    >>> prefer_final_permutation(['13a1'], ['13a2'])
    downloaded 13a2

    - only dev existing and no final available older dev available
    >>> prefer_final_permutation(['15a1'], ['14a1'])
    had 15a1

    - only dev existing and no final available same dev available
    >>> prefer_final_permutation(['16a1'], ['16a1'])
    had 16a1

- Without prefer final:

    >>> _ = zc.buildout.easy_install.prefer_final(False)

    - no existing and newer dev available
    >>> prefer_final_permutation((), [18, '19a1'])
    downloaded 19a1

    - no existing and only dev available
    >>> prefer_final_permutation((), ['20a1'])
    downloaded 20a1

    - final existing and only dev acailable
    >>> prefer_final_permutation([21], ['22a1'])
    downloaded 22a1

    - final existing and newer final available
    >>> prefer_final_permutation([23], [24])
    downloaded 24

    - final existing and same final available
    >>> prefer_final_permutation([25], [25])
    had 25

    - final existing and older final available
    >>> prefer_final_permutation([27], [26])
    had 27

    - only dev existing and final available
    >>> prefer_final_permutation(['29a1'], [28])
    had 29a1

    - only dev existing and no final available newer dev available
    >>> prefer_final_permutation(['30a1'], ['30a2'])
    downloaded 30a2

    - only dev existing and no final available older dev available
    >>> prefer_final_permutation(['32a1'], ['31a1'])
    had 32a1

    - only dev existing and no final available same dev available
    >>> prefer_final_permutation(['33a1'], ['33a1'])
    had 33a1

    >>> _ = zc.buildout.easy_install.prefer_final(True)

    """

def buildout_prefer_final_option():
    """
The prefer-final buildout option can be used for override the default
preference for newer distributions.

The default is prefer-final = true:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.3
    ...
    Picked: demoneeded = 1.1

Here we see that the final versions of demo and demoneeded are used.
We get the same behavior if we add prefer-final = true

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = true
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.3
    ...
    Picked: demoneeded = 1.1

If we specify prefer-final = false, we'll get the newest
distributions:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = false
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    Installing 'zc.buildout', 'setuptools'.
    ...
    Picked: demo = 0.4c1
    ...
    Picked: demoneeded = 1.2c1

We get an error if we specify anything but true or false:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ... prefer-final = no
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg:eggs
    ... eggs = demo
    ... ''' % globals())

    >>> print_(system(buildout+' -v'), end='') # doctest: +ELLIPSIS
    While:
      Initializing.
    Error: Invalid value for 'prefer-final' option: 'no'
    """

def wont_downgrade_due_to_prefer_final():
    r"""
    If we install a non-final buildout version, we don't want to
    downgrade just bcause we prefer-final.  If a buildout version
    isn't specified using a versions entry, then buildout's version
    requirement gets set to >=CURRENT_VERSION.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... ''')

    >>> [v] = [l.split('= >=', 1)[1].strip()
    ...        for l in system(buildout+' -vv').split('\n')
    ...        if l.startswith('zc.buildout = >=')]
    >>> v == pkg_resources.working_set.find(
    ...         pkg_resources.Requirement.parse('zc.buildout')
    ...         ).version
    True

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... [versions]
    ... zc.buildout = >.1
    ... ''')
    >>> [str(l.split('= >', 1)[1].strip())
    ...        for l in system(buildout+' -vv').split('\n')
    ...        if l.startswith('zc.buildout =')]
    ['.1']

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... versions = versions
    ... [versions]
    ... zc.buildout = 43
    ... ''')
    >>> print_(system(buildout), end='') # doctest: +ELLIPSIS
    Getting distribution for 'zc.buildout==43'.
    ...

    """

def develop_with_modules():
    """
Distribution setup scripts can import modules in the distribution directory:

    >>> mkdir('foo')
    >>> write('foo', 'bar.py',
    ... '''# empty
    ... ''')

    >>> write('foo', 'setup.py',
    ... '''
    ... import bar
    ... from setuptools import setup
    ... setup(name="foo")
    ... ''')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... develop = foo
    ... parts =
    ... ''')

    >>> print_(system(join('bin', 'buildout')), end='')
    Develop: '/sample-buildout/foo'

    >>> ls('develop-eggs')
    -  foo.egg-link
    -  zc.recipe.egg.egg-link

    """

def dont_pick_setuptools_if_version_is_specified_when_required_by_src_dist():
    """
When installing a source distribution, we got setuptools without
honoring our version specification.

    >>> mkdir('dist')
    >>> write('setup.py',
    ... '''
    ... from setuptools import setup
    ... setup(name='foo', version='1', py_modules=['foo'], zip_safe=True)
    ... ''')
    >>> write('foo.py', '')
    >>> _ = system(buildout+' setup . sdist')

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo
    ... find-links = dist
    ... versions = versions
    ... allow-picked-versions = false
    ...
    ... [versions]
    ... setuptools = %s
    ... foo = 1
    ...
    ... [foo]
    ... recipe = zc.recipe.egg
    ... eggs = foo
    ... ''' % pkg_resources.working_set.find(
    ...    pkg_resources.Requirement.parse('setuptools')).version)

    >>> print_(system(buildout), end='')
    Installing foo.
    Getting distribution for 'foo==1'.
    Got foo 1.

    """

def pyc_and_pyo_files_have_correct_paths():
    r"""

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = demo
    ... interpreter = py
    ... ''' % globals())

    >>> _ = system(buildout)

    >>> write('t.py',
    ... r'''
    ... import eggrecipedemo, eggrecipedemoneeded, sys
    ... if sys.version_info > (3,):
    ...     code = lambda f: f.__code__
    ... else:
    ...     code = lambda f: f.func_code
    ... sys.stdout.write(code(eggrecipedemo.main).co_filename+'\n')
    ... sys.stdout.write(code(eggrecipedemoneeded.f).co_filename+'\n')
    ... ''')

    >>> print_(system(join('bin', 'py')+ ' t.py'), end='')
    /sample-buildout/eggs/demo-0.3-py2.4.egg/eggrecipedemo.py
    /sample-buildout/eggs/demoneeded-1.1-py2.4.egg/eggrecipedemoneeded.py
    """

def dont_mess_with_standard_dirs_with_variable_refs():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... eggs-directory = ${buildout:directory}/develop-eggs
    ... parts =
    ... ''' % globals())
    >>> print_(system(buildout), end='')

    """

def expand_shell_patterns_in_develop_paths():
    """
    Sometimes we want to include a number of eggs in some directory as
    develop eggs, without explicitly listing all of them in our
    buildout.cfg

    >>> make_dist_that_requires(sample_buildout, 'sampley')
    >>> make_dist_that_requires(sample_buildout, 'samplez')

    Now, let's create a buildout that has a shell pattern that matches
    both:

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = sample*
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = sampley
    ...        samplez
    ... ''' % globals())

    We can see that both eggs were found:

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/sampley'
    Develop: '/sample-buildout/samplez'
    Installing eggs.

    """

def warn_users_when_expanding_shell_patterns_yields_no_results():
    """
    Sometimes shell patterns do not match anything, so we want to warn
    our users about it...

    >>> make_dist_that_requires(sample_buildout, 'samplea')

    So if we have 2 patterns, one that has a matching directory, and
    another one that does not

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = eggs
    ... develop = samplea grumble*
    ... find-links = %(link_server)s
    ...
    ... [eggs]
    ... recipe = zc.recipe.egg
    ... eggs = samplea
    ... ''' % globals())

    We should get one of the eggs, and a warning for the pattern that
    did not match anything.

    >>> print_(system(buildout), end='')
    Develop: '/sample-buildout/samplea'
    Couldn't develop '/sample-buildout/grumble*' (not found)
    Installing eggs.

    """

def make_sure_versions_dont_cancel_extras():
    """
    There was a bug that caused extras in requirements to be lost.

    >>> _ = open('setup.py', 'w').write('''
    ... from setuptools import setup
    ... setup(name='extraversiondemo', version='1.0',
    ...       url='x', author='x', author_email='x',
    ...       extras_require=dict(foo=['demo']), py_modules=['t'])
    ... ''')
    >>> open('README', 'w').close()
    >>> open('t.py', 'w').close()

    >>> sdist('.', sample_eggs)
    >>> mkdir('dest')
    >>> ws = zc.buildout.easy_install.install(
    ...     ['extraversiondemo[foo]'], 'dest', links=[sample_eggs],
    ...     versions = dict(extraversiondemo='1.0')
    ... )
    >>> sorted(dist.key for dist in ws)
    ['demo', 'demoneeded', 'extraversiondemo']
    """

def increment_buildout_options():
    r"""
    >>> write('b1.cfg', '''
    ... [buildout]
    ... parts = p1
    ... x = 1
    ... y = a
    ...     b
    ...
    ... [p1]
    ... recipe = zc.buildout:debug
    ... foo = ${buildout:x} ${buildout:y}
    ... ''')

    >>> write('buildout.cfg', '''
    ... [buildout]
    ... extends = b1.cfg
    ... parts += p2
    ... x += 2
    ... y -= a
    ...
    ... [p2]
    ... <= p1
    ... ''')

    >>> print_(system(buildout), end='')
    Installing p1.
      foo='1\n2 b'
      recipe='zc.buildout:debug'
    Installing p2.
      foo='1\n2 b'
      recipe='zc.buildout:debug'
    """

def increment_buildout_with_multiple_extended_files_421022():
    r"""
    >>> write('foo.cfg', '''
    ... [buildout]
    ... foo-option = foo
    ... [other]
    ... foo-option = foo
    ... ''')
    >>> write('bar.cfg', '''
    ... [buildout]
    ... bar-option = bar
    ... [other]
    ... bar-option = bar
    ... ''')
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... parts = p other
    ... extends = bar.cfg foo.cfg
    ... bar-option += baz
    ... foo-option += ham
    ...
    ... [other]
    ... recipe = zc.buildout:debug
    ... bar-option += baz
    ... foo-option += ham
    ...
    ... [p]
    ... recipe = zc.buildout:debug
    ... x = ${buildout:bar-option} ${buildout:foo-option}
    ... ''')

    >>> print_(system(buildout), end='')
    Installing p.
      recipe='zc.buildout:debug'
      x='bar\nbaz foo\nham'
    Installing other.
      bar-option='bar\nbaz'
      foo-option='foo\nham'
      recipe='zc.buildout:debug'
    """

def increment_on_command_line():
    r"""
    >>> write('buildout.cfg', '''
    ... [buildout]
    ... parts = p1
    ... x = 1
    ... y = a
    ...     b
    ...
    ... [p1]
    ... recipe = zc.buildout:debug
    ... foo = ${buildout:x} ${buildout:y}
    ...
    ... [p2]
    ... <= p1
    ... ''')

    >>> print_(system(buildout+' buildout:parts+=p2 p1:foo+=bar'), end='')
    Installing p1.
      foo='1 a\nb\nbar'
      recipe='zc.buildout:debug'
    Installing p2.
      foo='1 a\nb\nbar'
      recipe='zc.buildout:debug'
    """

def test_constrained_requirement():
    """
    zc.buildout.easy_install._constrained_requirement(constraint, requirement)

    Transforms an environment by applying a constraint.

    Here's a table of examples:

    >>> from zc.buildout.easy_install import IncompatibleConstraintError
    >>> examples = [
    ... # original, constraint, transformed
    ... ('x',        '1',        'x==1'),
    ... ('x>1',      '2',        'x==2'),
    ... ('x>3',      '2',        IncompatibleConstraintError),
    ... ('x>1',      '>2',       'x>2'),
    ... ('x>1',      '> 2',      'x>2'),
    ... ('x>1',      '>=2',      'x>=2'),
    ... ('x<1',      '>2',       IncompatibleConstraintError),
    ... ('x<=1',     '>=1',      'x>=1,<1,==1'),
    ... ('x<3',      '>1',       'x>1,<3'),
    ... ('x==2',     '>1',       'x==2'),
    ... ('x==2',     '>=2',      'x==2'),
    ... ('x[y]',     '1',        'x[y]==1'),
    ... ('x[y]>1',   '2',        'x[y]==2'),
    ... ('x<3',      '2',        'x==2'),
    ... ('x<1',      '2',        IncompatibleConstraintError),
    ... ('x<3',      '<2',       'x<2'),
    ... ('x<3',      '< 2',      'x<2'),
    ... ('x<3',      '<=2',      'x<=2'),
    ... ('x<3',      '<= 2',     'x<=2'),
    ... ('x>3',      '<2',       IncompatibleConstraintError),
    ... ('x>=1',     '<=1',      'x<=1,>1,==1'),
    ... ('x<3',      '>1',       'x>1,<3'),
    ... ('x==2',     '<3',       'x==2'),
    ... ('x==2',     '<=2',      'x==2'),
    ... ('x[y]<3',      '2',     'x[y]==2'),
    ... ]
    >>> from zc.buildout.easy_install import _constrained_requirement
    >>> for o, c, e in examples:
    ...     try:
    ...         o = pkg_resources.Requirement.parse(o)
    ...         if isinstance(e, str):
    ...             e = pkg_resources.Requirement.parse(e)
    ...         g = _constrained_requirement(c, o)
    ...     except IncompatibleConstraintError:
    ...         g = IncompatibleConstraintError
    ...     if str(g) != str(e):
    ...         print_('failed', o, c, g, '!=', e)
    """

def test_distutils_scripts_using_import_are_properly_parsed():
    """
    zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):

    Creates a script for a distutils based project. In this example for a
    hypothetical code quality checker called 'pyflint' that uses an import
    statement to import its code.

    >>> pyflint_script = '''#!/path/to/bin/python
    ... import pyflint.do_something
    ... pyflint.do_something()
    ... '''
    >>> import sys
    >>> original_executable = sys.executable
    >>> sys.executable = 'python'

    >>> from zc.buildout.easy_install import _distutils_script
    >>> _distutils_script('\\'/path/test/\\'', 'bin/pyflint', pyflint_script, '', '')
    ['bin/pyflint']
    >>> cat('bin/pyflint')
    #!python
    <BLANKLINE>
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '/path/test/',
      ]
    <BLANKLINE>
    <BLANKLINE>
    import pyflint.do_something
    pyflint.do_something()

    >>> sys.executable = original_executable
    """

def test_distutils_scripts_using_from_are_properly_parsed():
    """
    zc.buildout.easy_install._distutils_script(path, dest, script_content, initialization, rsetup):

    Creates a script for a distutils based project. In this example for a
    hypothetical code quality checker called 'pyflint' that uses a from
    statement to import its code.

    >>> pyflint_script = '''#!/path/to/bin/python
    ... from pyflint import do_something
    ... do_something()
    ... '''
    >>> import sys
    >>> original_executable = sys.executable
    >>> sys.executable = 'python'

    >>> from zc.buildout.easy_install import _distutils_script
    >>> _distutils_script('\\'/path/test/\\'', 'bin/pyflint', pyflint_script, '', '')
    ['bin/pyflint']
    >>> cat('bin/pyflint')
    #!python
    <BLANKLINE>
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      '/path/test/',
      ]
    <BLANKLINE>
    <BLANKLINE>
    from pyflint import do_something
    do_something()

    >>> sys.executable = original_executable
    """


def want_new_zcrecipeegg():
    """
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = egg
    ... [egg]
    ... recipe = zc.recipe.egg <2dev
    ... eggs = demo
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    The constraint, >=2.0.0a3,...
    While:
      Installing.
      Getting section egg.
      Initializing section egg.
      Installing recipe zc.recipe.egg <2dev.
    Error: Bad constraint >=2.0.0a3 zc.recipe.egg<2dev
    """

def macro_inheritance_bug():
    """

There was a bug preventing a section from using another section as a macro
if that section was extended with macros, and both sections were listed as
parts (phew!).  The following contrived example demonstrates that this
now works.

    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = foo bar
    ... [base]
    ... recipe = zc.recipe.egg
    ... [foo]
    ... <=base
    ... eggs = zc.buildout
    ... interpreter = python
    ... [bar]
    ... <=foo
    ... interpreter = py
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    Installing foo.
    ...
    Installing bar.
    ...
    >>> ls("./bin")
    -  buildout
    -  py
    -  python
    """

def bootstrap_honors_relative_paths():
    """
    >>> working = tmpdir('working')
    >>> cd(working)
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... relative-paths = true
    ... ''')
    >>> _ = system(buildout+' bootstrap')
    >>> cat('bin', 'buildout') # doctest: +ELLIPSIS
    #!/usr/local/bin/python2.7
    <BLANKLINE>
    import os
    <BLANKLINE>
    join = os.path.join
    base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    base = os.path.dirname(base)
    <BLANKLINE>
    import sys
    sys.path[0:0] = [
      join(base, 'eggs/setuptools-0.7-py2.7.egg'),
      ...
      ]
    <BLANKLINE>
    import zc.buildout.buildout
    <BLANKLINE>
    if __name__ == '__main__':
        sys.exit(zc.buildout.buildout.main())
    """

def cant_use_install_from_cache_and_offline_together():
    r"""
    >>> write('buildout.cfg',
    ... '''
    ... [buildout]
    ... parts =
    ... offline = true
    ... install-from-cache = true
    ... ''')
    >>> print_(system(join('bin', 'buildout')), end='') # doctest: +ELLIPSIS
    While:
      Initializing.
    Error: install-from-cache can't be used with offline mode.
    Nothing is installed, even from cache, in offline
    mode, which might better be called 'no-install mode'.
    <BLANKLINE>
    """

def error_installing_in_offline_mode_if_dont_have_needed_dist():
    r"""
    >>> import zc.buildout.easy_install
    >>> ws = zc.buildout.easy_install.install(
    ...     ['demo==0.2'], None,
    ...     links=[link_server], index=link_server+'index/')
    Traceback (most recent call last):
    ...
    UserError: We don't have a distribution for demo==0.2
    and can't install one in offline (no-install) mode.
    <BLANKLINE>
    """

def error_building_in_offline_mode_if_dont_have_needed_dist():
    r"""
    >>> zc.buildout.easy_install.build(
    ...   'extdemo', None,
    ...   {}, links=[link_server], index=link_server+'index/')
    Traceback (most recent call last):
    ...
    UserError: We don't have a distribution for extdemo
    and can't build one in offline (no-install) mode.
    <BLANKLINE>
    """

def test_buildout_section_shorthand_for_command_line_assignments():
    r"""
    >>> write('buildout.cfg', '')
    >>> print_(system(buildout+' parts='), end='') # doctest: +ELLIPSIS
    """

def buildout_honors_umask():
    """

    For setting the executable permission, the user's umask is honored:

    >>> orig_umask = os.umask(0o077)  # Only user gets permissions.
    >>> zc.buildout.easy_install._execute_permission() == 0o700
    True
    >>> tmp = os.umask(0o022)  # User can write, the rest not.
    >>> zc.buildout.easy_install._execute_permission() == 0o755
    True
    >>> tmp = os.umask(orig_umask)  # Reset umask to the original value.
    """

def parse_with_section_expr():
    r"""
    >>> class Recipe:
    ...     def __init__(self, buildout, *_):
    ...         buildout.parse('''
    ...             [foo : sys.version_info[0] > 0]
    ...             x = 1
    ...             ''')

    >>> buildout = zc.buildout.testing.Buildout()
    >>> buildout.parse('''
    ...     [foo : sys.version_info[0] > 0]
    ...     x = 1
    ...     ''')
    >>> buildout.print_options()
    [foo]
    x = 1

    """

if sys.platform == 'win32':
    del buildout_honors_umask # umask on dohs is academic

######################################################################

def create_sample_eggs(test, executable=sys.executable):
    assert executable == sys.executable, (executable, sys.executable)
    write = test.globs['write']
    dest = test.globs['sample_eggs']
    tmp = tempfile.mkdtemp()
    try:
        write(tmp, 'README.txt', '')

        for i in (0, 1, 2):
            write(tmp, 'eggrecipedemoneeded.py', 'y=%s\ndef f():\n  pass' % i)
            c1 = i==2 and 'c1' or ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demoneeded', py_modules=['eggrecipedemoneeded'],"
                " zip_safe=True, version='1.%s%s', author='bob', url='bob', "
                "author_email='bob')\n"
                % (i, c1)
                )
            zc.buildout.testing.sdist(tmp, dest)

        write(
            tmp, 'distutilsscript',
            '#!/usr/bin/python\n'
            '# -*- coding: utf-8 -*-\n'
            '"""Module docstring."""\n'
            'from __future__ import print_statement\n'
            'import os\n'
            'import sys; sys.stdout.write("distutils!\\n")\n'
            )
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='other', zip_safe=False, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='du_zipped', zip_safe=True, version='1.0', "
            "scripts=['distutilsscript'],"
            "py_modules=['eggrecipedemoneeded'])\n"
            )
        zc.buildout.testing.bdist_egg(tmp, executable, dest)

        os.remove(os.path.join(tmp, 'distutilsscript'))
        os.remove(os.path.join(tmp, 'eggrecipedemoneeded.py'))

        for i in (1, 2, 3, 4):
            write(
                tmp, 'eggrecipedemo.py',
                'import eggrecipedemoneeded, sys\n'
                'def print_(*a):\n'
                '    sys.stdout.write(" ".join(map(str, a))+"\\n")\n'
                'x=%s\n'
                'def main():\n'
                '   print_(x, eggrecipedemoneeded.y)\n'
                % i)
            c1 = i==4 and 'c1' or ''
            write(
                tmp, 'setup.py',
                "from setuptools import setup\n"
                "setup(name='demo', py_modules=['eggrecipedemo'],"
                " install_requires = 'demoneeded',"
                " entry_points={'console_scripts': "
                     "['demo = eggrecipedemo:main']},"
                " zip_safe=True, version='0.%s%s')\n" % (i, c1)
                )
            zc.buildout.testing.bdist_egg(tmp, dest)

        write(tmp, 'eggrecipebigdemo.py', 'import eggrecipedemo')
        write(
            tmp, 'setup.py',
            "from setuptools import setup\n"
            "setup(name='bigdemo', "
            " install_requires = 'demo',"
            " py_modules=['eggrecipebigdemo'], "
            " zip_safe=True, version='0.1')\n"
            )
        zc.buildout.testing.bdist_egg(tmp, sys.executable, dest)

    finally:
        shutil.rmtree(tmp)

extdemo_c2 = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

PyMODINIT_FUNC
initextdemo(void)
{
    PyObject *m;
    m = Py_InitModule3("extdemo", methods, "");
#ifdef TWO
    PyModule_AddObject(m, "val", PyInt_FromLong(2));
#else
    PyModule_AddObject(m, "val", PyInt_FromLong(EXTDEMO));
#endif
}
"""

extdemo_c3 = """
#include <Python.h>
#include <extdemo.h>

static PyMethodDef methods[] = {{NULL}};

#define MOD_DEF(ob, name, doc, methods) \
	  static struct PyModuleDef moduledef = { \
	    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
	  ob = PyModule_Create(&moduledef);

#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)

MOD_INIT(extdemo)
{
    PyObject *m;

    MOD_DEF(m, "extdemo", "", methods);

#ifdef TWO
    PyModule_AddObject(m, "val", PyLong_FromLong(2));
#else
    PyModule_AddObject(m, "val", PyLong_FromLong(EXTDEMO));
#endif

    return m;
}
"""

extdemo_c = sys.version_info[0] < 3 and extdemo_c2 or extdemo_c3

extdemo_setup_py = r"""
import os, sys
from distutils.core import setup, Extension

if os.environ.get('test-variable'):
    print("Have environment test-variable: %%s" %% os.environ['test-variable'])

setup(name = "extdemo", version = "%s", url="http://www.zope.org",
      author="Demo", author_email="demo@demo.com",
      ext_modules = [Extension('extdemo', ['extdemo.c'])],
      )
"""

def add_source_dist(test, version=1.4):
    if 'extdemo' not in test.globs:
        test.globs['extdemo'] = test.globs['tmpdir']('extdemo')

    tmp = test.globs['extdemo']
    write = test.globs['write']
    try:
        write(tmp, 'extdemo.c', extdemo_c);
        write(tmp, 'setup.py', extdemo_setup_py % version);
        write(tmp, 'README', "");
        write(tmp, 'MANIFEST.in', "include *.c\n");
        test.globs['sdist'](tmp, test.globs['sample_eggs'])
    except:
        shutil.rmtree(tmp)

def easy_install_SetUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    test.globs['sample_eggs'] = sample_eggs
    os.mkdir(os.path.join(sample_eggs, 'index'))
    create_sample_eggs(test)
    add_source_dist(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])
    test.globs['update_extdemo'] = lambda : add_source_dist(test, 1.5)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def buildout_txt_setup(test):
    zc.buildout.testing.buildoutSetUp(test)
    mkdir = test.globs['mkdir']
    eggs = os.environ['buildout-testing-index-url'][7:]
    test.globs['sample_eggs'] = eggs
    create_sample_eggs(test)

    for name in os.listdir(eggs):
        if '-' in name:
            pname = name.split('-')[0]
            if not os.path.exists(os.path.join(eggs, pname)):
                mkdir(eggs, pname)
            shutil.move(os.path.join(eggs, name),
                        os.path.join(eggs, pname, name))

    dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zc.recipe.egg'))
    mkdir(eggs, 'zc.recipe.egg')
    zc.buildout.testing.sdist(
        os.path.dirname(dist.location),
        os.path.join(eggs, 'zc.recipe.egg'),
        )

egg_parse = re.compile('([0-9a-zA-Z_.]+)-([0-9a-zA-Z_.]+)-py(\d[.]\d).egg$'
                       ).match
def makeNewRelease(project, ws, dest, version='99.99'):
    dist = ws.find(pkg_resources.Requirement.parse(project))
    eggname, oldver, pyver = egg_parse(
        os.path.basename(dist.location)
        ).groups()
    dest = os.path.join(dest, "%s-%s-py%s.egg" % (eggname, version, pyver))
    if os.path.isfile(dist.location):
        shutil.copy(dist.location, dest)
        zip = zipfile.ZipFile(dest, 'a')
        zip.writestr(
            'EGG-INFO/PKG-INFO',
            ((zip.read('EGG-INFO/PKG-INFO').decode()
              ).replace("Version: %s" % oldver,
                        "Version: %s" % version)
             ).encode()
            )
        zip.close()
    else:
        shutil.copytree(dist.location, dest)
        info_path = os.path.join(dest, 'EGG-INFO', 'PKG-INFO')
        info = open(info_path).read().replace("Version: %s" % oldver,
                                              "Version: %s" % version)
        open(info_path, 'w').write(info)

def getWorkingSetWithBuildoutEgg(test):
    sample_buildout = test.globs['sample_buildout']
    eggs = os.path.join(sample_buildout, 'eggs')

    # If the zc.buildout dist is a develop dist, convert it to a
    # regular egg in the sample buildout
    req = pkg_resources.Requirement.parse('zc.buildout')
    dist = pkg_resources.working_set.find(req)
    if dist.precedence == pkg_resources.DEVELOP_DIST:
        # We have a develop egg, create a real egg for it:
        here = os.getcwd()
        os.chdir(os.path.dirname(dist.location))
        zc.buildout.easy_install.call_subprocess(
            [sys.executable,
             os.path.join(os.path.dirname(dist.location), 'setup.py'),
             '-q', 'bdist_egg', '-d', eggs],
            env=dict(os.environ,
                     PYTHONPATH=pkg_resources.working_set.find(
                         pkg_resources.Requirement.parse('setuptools')
                         ).location,
                     ),
            )
        os.chdir(here)
        os.remove(os.path.join(eggs, 'zc.buildout.egg-link'))

        # Rebuild the buildout script
        ws = pkg_resources.WorkingSet([eggs])
        ws.require('zc.buildout')
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            os.path.join(sample_buildout, 'bin'))
    else:
        ws = pkg_resources.working_set
    return ws

def updateSetup(test):
    zc.buildout.testing.buildoutSetUp(test)
    new_releases = test.globs['tmpdir']('new_releases')
    test.globs['new_releases'] = new_releases
    ws = getWorkingSetWithBuildoutEgg(test)
    # now let's make the new releases
    makeNewRelease('zc.buildout', ws, new_releases)
    os.mkdir(os.path.join(new_releases, 'zc.buildout'))
    makeNewRelease('setuptools', ws, new_releases)
    os.mkdir(os.path.join(new_releases, 'setuptools'))

bootstrap_py = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(__file__)))),
    'bootstrap', 'bootstrap.py')

def bootstrapSetup(test):
    buildout_txt_setup(test)
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])
    sample_eggs = test.globs['sample_eggs']
    ws = getWorkingSetWithBuildoutEgg(test)
    makeNewRelease('zc.buildout', ws, sample_eggs, '2.0.0')
    makeNewRelease('zc.buildout', ws, sample_eggs, '22.0.0')
    os.environ['bootstrap-testing-find-links'] = test.globs['link_server']
    test.globs['bootstrap_py'] = bootstrap_py

normalize_bang = (
    re.compile(re.escape('#!'+
                         zc.buildout.easy_install._safe_arg(sys.executable))),
    '#!/usr/local/bin/python2.7',
    )

normalize_S = (
    re.compile(r'#!/usr/local/bin/python2.7 -S'),
    '#!/usr/local/bin/python2.7',
    )

def test_suite():
    test_suite = [
        manuel.testing.TestSuite(
            manuel.doctest.Manuel() + manuel.capture.Manuel(),
            'configparser.test'),
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                checker=renormalizing.RENormalizing([
                    zc.buildout.testing.normalize_path,
                    zc.buildout.testing.normalize_endings,
                    zc.buildout.testing.normalize_script,
                    zc.buildout.testing.normalize_egg_py,
                    zc.buildout.testing.not_found,
                    zc.buildout.testing.adding_find_link,
                    # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
                    (re.compile('__buildout_signature__ = recipes-\S+'),
                     '__buildout_signature__ = recipes-SSSSSSSSSSS'),
                    (re.compile('executable = [\S ]+python\S*', re.I),
                     'executable = python'),
                    (re.compile('[-d]  (setuptools|setuptools)-\S+[.]egg'),
                     'setuptools.egg'),
                    (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                     'zc.buildout.egg'),
                    (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
                    (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
                    (re.compile('Picked: (\S+) = \S+'),
                     'Picked: \\1 = V.V'),
                    (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                     'We have a develop egg: zc.buildout X.X.'),
                    (re.compile(r'\\[\\]?'), '/'),
                    (re.compile('WindowsError'), 'OSError'),
                    (re.compile(r'\[Error \d+\] Cannot create a file '
                                r'when that file already exists: '),
                     '[Errno 17] File exists: '
                     ),
                    (re.compile('setuptools'), 'setuptools'),
                    (re.compile('Got zc.recipe.egg \S+'), 'Got zc.recipe.egg'),
                    (re.compile(r'zc\.(buildout|recipe\.egg)\s*= >=\S+'),
                     'zc.\1 = >=1.99'),
                    ])
                ) + manuel.capture.Manuel(),
            'buildout.txt', 'meta-recipes.txt',
            setUp=buildout_txt_setup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            ),
        doctest.DocFileSuite(
            'runsetup.txt', 'repeatable.txt', 'setup.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.testing.not_found,
               zc.buildout.testing.adding_find_link,
               # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
               # (re.compile(r"Getting distribution for 'zc.buildout >=\S+"),
               #  ''),
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
               (re.compile('Picked: (\S+) = \S+'),
                'Picked: \\1 = V.V'),
               (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                'We have a develop egg: zc.buildout X.X.'),
               (re.compile(r'\\[\\]?'), '/'),
               (re.compile('WindowsError'), 'OSError'),
               (re.compile('setuptools = \S+'), 'setuptools = 0.7.99'),
               (re.compile(r'\[Error 17\] Cannot create a file '
                           r'when that file already exists: '),
                '[Errno 17] File exists: '
                ),
               (re.compile('executable = %s' % re.escape(sys.executable)),
                'executable = python'),
               (re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}'),
                'YYYY-MM-DD hh:mm:ss.dddddd'),
               ]),
            ),
        doctest.DocFileSuite(
            'debugging.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
                zc.buildout.testing.not_found,
                zc.buildout.testing.adding_find_link,
                (re.compile('zc.buildout.buildout.MissingOption'),
                 'MissingOption'),
                (re.compile(r'\S+buildout.py'), 'buildout.py'),
                (re.compile(r'line \d+'), 'line NNN'),
                (re.compile(r'py\(\d+\)'), 'py(NNN)'),
                ])
            ),

        doctest.DocFileSuite(
            'update.txt',
            setUp=updateSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                (re.compile(r'(zc.buildout|setuptools)-\d+[.]\d+\S*'
                            '-py\d.\d.egg'),
                 '\\1.egg'),
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.not_found,
                zc.buildout.testing.adding_find_link,
                normalize_bang,
                normalize_S,
                # (re.compile(r"Installing 'zc.buildout >=\S+"), ''),
                (re.compile(r"Getting distribution for 'zc.buildout>=\S+"),
                 ''),
                (re.compile('99[.]99'), 'NINETYNINE.NINETYNINE'),
                (re.compile(
                    r'(zc.buildout|setuptools)( version)? \d+[.]\d+\S*'),
                 '\\1 V.V'),
                (re.compile('[-d]  setuptools'), '-  setuptools'),
                (re.compile(re.escape(os.path.sep)+'+'), '/'),
               ])
            ),

        doctest.DocFileSuite(
            'easy_install.txt', 'downloadcache.txt', 'dependencylinks.txt',
            'allowhosts.txt',
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
                zc.buildout.testing.adding_find_link,
                zc.buildout.testing.not_found,
                normalize_bang,
                normalize_S,
                (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
                (re.compile(r'\\[\\]?'), '/'),
                (re.compile('(\n?)-  ([a-zA-Z_.-]+)\n-  \\2.exe\n'),
                 '\\1-  \\2\n'),
                ]+(sys.version_info < (2, 5) and [
                  (re.compile('.*No module named runpy.*', re.S), ''),
                  (re.compile('.*usage: pdb.py scriptfile .*', re.S), ''),
                  (re.compile('.*Error: what does not exist.*', re.S), ''),
                  ] or [])),


            ),

        doctest.DocFileSuite(
            'download.txt', 'extends-cache.txt',
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=renormalizing.RENormalizing([
              zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
              zc.buildout.testing.not_found,
              zc.buildout.testing.adding_find_link,
              (re.compile(' at -?0x[^>]+'), '<MEM ADDRESS>'),
              (re.compile('http://localhost:[0-9]{4,5}/'),
               'http://localhost/'),
              (re.compile('[0-9a-f]{32}'), '<MD5 CHECKSUM>'),
              zc.buildout.testing.normalize_path,
              zc.buildout.testing.ignore_not_upgrading,
              ]),
            ),

        doctest.DocTestSuite(
            setUp=easy_install_SetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.normalize_script,
                zc.buildout.testing.normalize_egg_py,
                zc.buildout.testing.normalize___pycache__,
                zc.buildout.testing.not_found,
                zc.buildout.testing.normalize_exception_type_for_python_2_and_3,
                zc.buildout.testing.adding_find_link,
                normalize_bang,
                (re.compile(r'^(\w+\.)*(Missing\w+: )'), '\2'),
                (re.compile("buildout: Running \S*setup.py"),
                 'buildout: Running setup.py'),
                (re.compile('setuptools-\S+-'),
                 'setuptools.egg'),
                (re.compile('zc.buildout-\S+-'),
                 'zc.buildout.egg'),
                (re.compile('setuptools = \S+'), 'setuptools = 0.7.99'),
                (re.compile('File "\S+one.py"'),
                 'File "one.py"'),
                (re.compile(r'We have a develop egg: (\S+) (\S+)'),
                 r'We have a develop egg: \1 V'),
                (re.compile('Picked: setuptools = \S+'),
                 'Picked: setuptools = V'),
                (re.compile('[-d]  setuptools'), '-  setuptools'),
                (re.compile(r'\\[\\]?'), '/'),
                (re.compile(
                    '-q develop -mxN -d "/sample-buildout/develop-eggs'),
                 '-q develop -mxN -d /sample-buildout/develop-eggs'
                 ),
                (re.compile(r'^[*]...'), '...'),
                # for
                # bug_92891
                # bootstrap_crashes_with_egg_recipe_in_buildout_section
                (re.compile(r"Unused options for buildout: 'eggs' 'scripts'\."),
                 "Unused options for buildout: 'scripts' 'eggs'."),
                ]),
            ),
        zc.buildout.rmtree.test_suite(),
        doctest.DocFileSuite(
            'windows.txt',
            setUp=zc.buildout.testing.buildoutSetUp,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.testing.not_found,
               zc.buildout.testing.adding_find_link,
               (re.compile('__buildout_signature__ = recipes-\S+'),
                '__buildout_signature__ = recipes-SSSSSSSSSSS'),
               (re.compile('[-d]  setuptools-\S+[.]egg'), 'setuptools.egg'),
               (re.compile('zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('creating \S*setup.cfg'), 'creating setup.cfg'),
               (re.compile('hello\%ssetup' % os.path.sep), 'hello/setup'),
               (re.compile('Picked: (\S+) = \S+'),
                'Picked: \\1 = V.V'),
               (re.compile(r'We have a develop egg: zc.buildout (\S+)'),
                'We have a develop egg: zc.buildout X.X.'),
               (re.compile(r'\\[\\]?'), '/'),
               (re.compile('WindowsError'), 'OSError'),
               (re.compile(r'\[Error 17\] Cannot create a file '
                           r'when that file already exists: '),
                '[Errno 17] File exists: '
                ),
               ])
            ),
        doctest.DocFileSuite(
            'testing_bugfix.txt'),
    ]

    # adding bootstrap.txt doctest to the suite
    # only if bootstrap.py is present
    if os.path.exists(bootstrap_py):
        test_suite.append(doctest.DocFileSuite(
            'bootstrap.txt', 'bootstrap_cl_settings.test',
            setUp=bootstrapSetup,
            tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.not_found,
               normalize_bang,
               zc.buildout.testing.adding_find_link,
               (re.compile('Downloading.*setuptools.*egg\n'), ''),
               ]),
            ))

    return unittest.TestSuite(test_suite)

########NEW FILE########
__FILENAME__ = custom
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Install packages as eggs
"""

import logging
import os
import re
import sys
import zc.buildout.easy_install
import zipfile

logger = logging.getLogger(__name__)


class Base:

    def __init__(self, buildout, name, options):
        self.name, self.options = name, options

        options['_d'] = buildout['buildout']['develop-eggs-directory']

        self.build_ext = build_ext(buildout, options)

    def update(self):
        return self.install()


class Custom(Base):

    def __init__(self, buildout, name, options):
        Base.__init__(self, buildout, name, options)

        links = options.get('find-links',
                            buildout['buildout'].get('find-links'))
        if links:
            links = links.split()
            options['find-links'] = '\n'.join(links)
        else:
            links = ()
        self.links = links

        index = options.get('index', buildout['buildout'].get('index'))
        if index is not None:
            options['index'] = index
        self.index = index

        environment_section = options.get('environment')
        if environment_section:
            self.environment = buildout[environment_section]
        else:
            self.environment = {}
        environment_data = list(self.environment.items())
        environment_data.sort()
        options['_environment-data'] = repr(environment_data)

        options['_e'] = buildout['buildout']['eggs-directory']

        if buildout['buildout'].get('offline') == 'true':
            self.install = lambda: ()

        self.newest = buildout['buildout'].get('newest') == 'true'

    def install(self):
        options = self.options
        distribution = options.get('egg')
        if distribution is None:
            distribution = options.get('eggs')
            if distribution is None:
                distribution = self.name
            else:
                logger.warn("The eggs option is deprecated. Use egg instead")


        distribution = options.get('egg', options.get('eggs', self.name)
                                   ).strip()
        self._set_environment()
        try:
            return zc.buildout.easy_install.build(
                distribution, options['_d'], self.build_ext,
                self.links, self.index, sys.executable,
                [options['_e']], newest=self.newest,
                )
        finally:
            self._restore_environment()


    def _set_environment(self):
        self._saved_environment = {}
        for key, value in list(self.environment.items()):
            if key in os.environ:
                self._saved_environment[key] = os.environ[key]
            # Interpolate value with variables from environment. Maybe there
            # should be a general way of doing this in buildout with something
            # like ${environ:foo}:
            os.environ[key] = value % os.environ

    def _restore_environment(self):
        for key in self.environment:
            if key in self._saved_environment:
                os.environ[key] = self._saved_environment[key]
            else:
                try:
                    del os.environ[key]
                except KeyError:
                    pass


class Develop(Base):

    def __init__(self, buildout, name, options):
        Base.__init__(self, buildout, name, options)
        options['setup'] = os.path.join(buildout['buildout']['directory'],
                                        options['setup'])

    def install(self):
        options = self.options
        return zc.buildout.easy_install.develop(
            options['setup'], options['_d'], self.build_ext)


def build_ext(buildout, options):
    result = {}
    for be_option in ('include-dirs', 'library-dirs', 'rpath'):
        value = options.get(be_option)
        if value is None:
            continue
        value = [
            os.path.join(
                buildout['buildout']['directory'],
                v.strip()
                )
            for v in value.strip().split('\n')
            if v.strip()
        ]
        result[be_option] = os.pathsep.join(value)
        options[be_option] = os.pathsep.join(value)

    swig = options.get('swig')
    if swig:
        options['swig'] = result['swig'] = os.path.join(
            buildout['buildout']['directory'],
            swig,
            )

    for be_option in ('define', 'undef', 'libraries', 'link-objects',
                      'debug', 'force', 'compiler', 'swig-cpp', 'swig-opts',
                      ):
        value = options.get(be_option)
        if value is None:
            continue
        result[be_option] = value

    return result

########NEW FILE########
__FILENAME__ = egg
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Install packages as eggs
"""

import logging
import os
import re
import sys
import zc.buildout.easy_install
import zipfile

class Eggs(object):

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        b_options = buildout['buildout']
        links = options.get('find-links', b_options['find-links'])
        if links:
            links = links.split()
            options['find-links'] = '\n'.join(links)
        else:
            links = ()
        self.links = links

        index = options.get('index', b_options.get('index'))
        if index is not None:
            options['index'] = index
        self.index = index

        allow_hosts = b_options['allow-hosts']
        allow_hosts = tuple([host.strip() for host in allow_hosts.split('\n')
                               if host.strip()!=''])
        self.allow_hosts = allow_hosts

        options['eggs-directory'] = b_options['eggs-directory']
        options['_e'] = options['eggs-directory'] # backward compat.
        options['develop-eggs-directory'] = b_options['develop-eggs-directory']
        options['_d'] = options['develop-eggs-directory'] # backward compat.

    def working_set(self, extra=()):
        """Separate method to just get the working set

        This is intended for reuse by similar recipes.
        """
        options = self.options
        b_options = self.buildout['buildout']

        # Backward compat. :(
        options['executable'] = sys.executable

        distributions = [
            r.strip()
            for r in options.get('eggs', self.name).split('\n')
            if r.strip()]
        orig_distributions = distributions[:]
        distributions.extend(extra)

        if self.buildout['buildout'].get('offline') == 'true':
            ws = zc.buildout.easy_install.working_set(
                distributions,
                [options['develop-eggs-directory'], options['eggs-directory']]
                )
        else:
            ws = zc.buildout.easy_install.install(
                distributions, options['eggs-directory'],
                links=self.links,
                index=self.index,
                path=[options['develop-eggs-directory']],
                newest=self.buildout['buildout'].get('newest') == 'true',
                allow_hosts=self.allow_hosts)

        return orig_distributions, ws

    def install(self):
        reqs, ws = self.working_set()
        return ()

    update = install

class Scripts(Eggs):

    def __init__(self, buildout, name, options):
        super(Scripts, self).__init__(buildout, name, options)

        options['bin-directory'] = buildout['buildout']['bin-directory']
        options['_b'] = options['bin-directory'] # backward compat.

        self.extra_paths = [
            os.path.join(buildout['buildout']['directory'], p.strip())
            for p in options.get('extra-paths', '').split('\n')
            if p.strip()
            ]
        if self.extra_paths:
            options['extra-paths'] = '\n'.join(self.extra_paths)


        relative_paths = options.get(
            'relative-paths',
            buildout['buildout'].get('relative-paths', 'false')
            )
        if relative_paths == 'true':
            options['buildout-directory'] = buildout['buildout']['directory']
            self._relative_paths = options['buildout-directory']
        else:
            self._relative_paths = ''
            assert relative_paths == 'false'

    parse_entry_point = re.compile(
        '([^=]+)=(\w+(?:[.]\w+)*):(\w+(?:[.]\w+)*)$'
        ).match
    def install(self):
        reqs, ws = self.working_set()
        options = self.options

        scripts = options.get('scripts')
        if scripts or scripts is None:
            if scripts is not None:
                scripts = scripts.split()
                scripts = dict([
                    ('=' in s) and s.split('=', 1) or (s, s)
                    for s in scripts
                    ])

            for s in options.get('entry-points', '').split():
                parsed = self.parse_entry_point(s)
                if not parsed:
                    logging.getLogger(self.name).error(
                        "Cannot parse the entry point %s.", s)
                    raise zc.buildout.UserError("Invalid entry point")
                reqs.append(parsed.groups())

            if get_bool(options, 'dependent-scripts'):
                # Generate scripts for all packages in the working set,
                # except setuptools.
                reqs = list(reqs)
                for dist in ws:
                    name = dist.project_name
                    if name != 'setuptools' and name not in reqs:
                        reqs.append(name)

            return zc.buildout.easy_install.scripts(
                reqs, ws, sys.executable, options['bin-directory'],
                scripts=scripts,
                extra_paths=self.extra_paths,
                interpreter=options.get('interpreter'),
                initialization=options.get('initialization', ''),
                arguments=options.get('arguments', ''),
                relative_paths=self._relative_paths,
                )

        return ()

    update = install

def get_bool(options, name, default=False):
    value = options.get(name)
    if not value:
        return default
    if value == 'true':
        return True
    elif value == 'false':
        return False
    else:
        raise zc.buildout.UserError(
            "Invalid value for %s option: %s" % (name, value))

Egg = Scripts

########NEW FILE########
__FILENAME__ = tests
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from zope.testing import renormalizing
import doctest
import os
import re
import shutil
import sys
import zc.buildout.tests
import zc.buildout.testing

import unittest

os_path_sep = os.path.sep
if os_path_sep == '\\':
    os_path_sep *= 2

def dirname(d, level=1):
    if level == 0:
        return d
    return dirname(os.path.dirname(d), level-1)

def setUp(test):
    zc.buildout.tests.easy_install_SetUp(test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

def test_suite():
    suite = unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.normalize_script,
               zc.buildout.testing.normalize_egg_py,
               zc.buildout.tests.normalize_bang,
               zc.buildout.tests.normalize_S,
               zc.buildout.testing.not_found,
               (re.compile('[d-]  zc.buildout(-\S+)?[.]egg(-link)?'),
                'zc.buildout.egg'),
               (re.compile('[d-]  setuptools-[^-]+-'), 'setuptools-X-'),
               (re.compile(r'eggs\\\\demo'), 'eggs/demo'),
               (re.compile(r'[a-zA-Z]:\\\\foo\\\\bar'), '/foo/bar'),
               ])
            ),
        doctest.DocFileSuite(
            'api.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
               zc.buildout.testing.normalize_path,
               zc.buildout.testing.normalize_endings,
               zc.buildout.testing.not_found,
               (re.compile('__buildout_signature__ = '
                           'sample-\S+\s+'
                           'zc.recipe.egg-\S+\s+'
                           'setuptools-\S+\s+'
                           'zc.buildout-\S+\s*'
                           ),
                '__buildout_signature__ = sample- zc.recipe.egg-'),
               (re.compile('find-links = http://localhost:\d+/'),
                'find-links = http://localhost:8080/'),
               (re.compile('index = http://localhost:\d+/index'),
                'index = http://localhost:8080/index'),
               ])
            ),
        doctest.DocFileSuite(
            'custom.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_endings,
                zc.buildout.testing.not_found,
                (re.compile("(d  ((ext)?demo(needed)?|other)"
                            "-\d[.]\d-py)\d[.]\d(-\S+)?[.]egg"),
                 '\\1V.V.egg'),
                (re.compile('extdemo.c\n.+\\extdemo.exp\n'), ''),
                (re.compile(
                    r'zip_safe flag not set; analyzing archive contents.*\n'),
                 ''),
                (re.compile(
                    r'\n.*module references __file__'),
                 ''),
                (re.compile(''), ''),
                (re.compile(
                    "extdemo[.]c\n"
                    "extdemo[.]obj : warning LNK4197: "
                    "export 'initextdemo' specified multiple times; "
                    "using first specification\n"
                    "   Creating library build\\\\temp[.]win-amd64-2[.]"
                    "[4567]\\\\Release\\\\extdemo[.]lib and object "
                    "build\\\\temp[.]win-amd64-2[.][4567]\\\\Re"
                    "lease\\\\extdemo[.]exp\n"),
                 ''),
                ]),
            ),
        ))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

########NEW FILE########
