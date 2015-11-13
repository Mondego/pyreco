__FILENAME__ = custom
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from tito.release import *


class DummyReleaser(Releaser):

    def __init__(self, name=None, version=None, tag=None, build_dir=None,
            config=None, user_config=None):
        Releaser.__init__(self, name, version, tag, build_dir,
                config, user_config)
        pass

    def release(self, dry_run=False):
        print("DUMMY RELEASE!!!!!!!!!!!!!!!!!")

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
#
# Copyright (c) 2008-2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Executes all tests.
"""

import sys
import os

# Make sure we run from the source, this is tricky because the functional
# tests need to find both the location of the 'tito' executable script,
# and the internal tito code needs to know where to find our auxiliary Perl
# scripts. Adding an environment variable hack to the actual code to
# accommodate this for now.

TEST_SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.normpath(os.path.join(TEST_SCRIPT_DIR, "src/"))
sys.path.insert(0, SRC_DIR)
SRC_BIN_DIR = os.path.abspath(os.path.join(TEST_SCRIPT_DIR, "bin/"))

os.environ['TITO_SRC_BIN_DIR'] = SRC_BIN_DIR

if __name__ == '__main__':
    import nose

    print("Using Python %s" % sys.version[0:3])
    print("Using nose %s" % nose.__version__[0:3])
    print("Running tito tests against: %s" % SRC_DIR)

    nose.main()

########NEW FILE########
__FILENAME__ = fetch
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import re
import os
import os.path
import shutil

from tito.builder.main import BuilderBase
from tito.config_object import ConfigObject
from tito.common import error_out, debug, get_spec_version_and_release, \
    get_class_by_name


class FetchBuilder(ConfigObject, BuilderBase):
    """
    A separate Builder class for projects whose source is not in git. Source
    is fetched via a configurable strategy, which also determines what version
    and release to insert into the spec file.

    Cannot build past tags.
    """
    # TODO: test only for now, setup a tagger to fetch sources and store in git annex,
    # then we can do official builds as well.
    REQUIRED_ARGS = []

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        BuilderBase.__init__(self, name=name, build_dir=build_dir,
                config=config,
                user_config=user_config, args=args, **kwargs)

        if tag:
            error_out("FetchBuilder does not support building "
                    "specific tags.")

        if not config.has_option("builder",
                "fetch_strategy"):
            print("WARNING: no fetch_strategy specified in tito.props"
                    ", assuming ArgSourceStrategy.")
            if not config.has_section("builder"):
                config.add_section("builder")
            config.set('builder', 'fetch_strategy',
                    'tito.builder.fetch.ArgSourceStrategy')

        self.build_tag = '%s-%s' % (self.project_name,
                get_spec_version_and_release(self.start_dir,
                    '%s.spec' % self.project_name))

    def tgz(self):
        self.ran_tgz = True
        self._create_build_dirs()

        print("Fetching sources...")
        source_strat_class = get_class_by_name(self.config.get(
            'builder', 'fetch_strategy'))
        source_strat = source_strat_class(self)
        source_strat.fetch()
        self.sources = source_strat.sources
        self.spec_file = source_strat.spec_file

    def _get_rpmbuild_dir_options(self):
        return ('--define "_topdir %s" --define "_sourcedir %s" --define "_builddir %s" '
            '--define "_srcrpmdir %s" --define "_rpmdir %s" ' % (
                self.rpmbuild_dir,
                self.rpmbuild_sourcedir, self.rpmbuild_builddir,
                self.rpmbuild_basedir, self.rpmbuild_basedir))


class SourceStrategy(object):
    """
    Base class for source strategies. These are responsible for fetching the
    sources the builder will use, and determining what version/release we're
    building.

    This is created and run in the tgz step of the builder. It will be passed
    a reference to the builder calling it, which will be important for accessing
    a lot of required information.

    Ideally sources and the spec file to be used should be copied into
    builder.rpmbuild_sourcedir, which will be cleaned up automatically after
    the builder runs.
    """
    def __init__(self, builder):
        """
        Defines fields that should be set when a sub-class runs fetch.
        """
        self.builder = builder

        # Full path to the spec file we'll actually use to build, should be a
        # copy, never a live spec file in a git repo as sometimes it will be
        # modified:
        self.spec_file = None

        # Will contain the full path to each source we gather:
        self.sources = []

        # The version we're building:
        self.version = None

        # The release we're building:
        self.release = None

    def fetch(self):
        raise NotImplementedError()


class ArgSourceStrategy(SourceStrategy):
    """
    Assumes the builder was passed an explicit argument specifying which source
    file(s) to use.
    """
    def fetch(self):

        # Assuming we're still in the start directory, get the absolute path
        # to all sources specified:
        # TODO: support passing of multiple sources here.
        # TODO: error out if not present
        manual_sources = [self.builder.args['source']]
        debug("Got sources: %s" % manual_sources)

        # Copy the live spec from our starting location. Unlike most builders,
        # we are not using a copy from a past git commit.
        self.spec_file = os.path.join(self.builder.rpmbuild_sourcedir,
                    '%s.spec' % self.builder.project_name)
        shutil.copyfile(
            os.path.join(self.builder.start_dir, '%s.spec' %
                self.builder.project_name),
            self.spec_file)
        print("  %s.spec" % self.builder.project_name)

        # TODO: Make this a configurable strategy:
        i = 0
        replacements = []
        for s in manual_sources:
            base_name = os.path.basename(s)
            dest_filepath = os.path.join(self.builder.rpmbuild_sourcedir,
                    base_name)
            shutil.copyfile(s, dest_filepath)
            self.sources.append(dest_filepath)

            # Add a line to replace in the spec for each source:
            source_regex = re.compile("^(source%s:\s*)(.+)$" % i, re.IGNORECASE)
            new_line = "Source%s: %s\n" % (i, base_name)
            replacements.append((source_regex, new_line))

        # Replace version and release in spec:
        version_regex = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)
        release_regex = re.compile("^(release:\s*)(.+)$", re.IGNORECASE)

        (self.version, self.release) = self._get_version_and_release()
        print("Building version: %s" % self.version)
        print("Building release: %s" % self.release)
        replacements.append((version_regex, "Version: %s\n" % self.version))
        replacements.append((release_regex, "Release: %s\n" % self.release))

        self.replace_in_spec(replacements)

    def _get_version_and_release(self):
        """
        Get the version and release from the builder.
        Sources are configured at this point.
        """
        # Assuming source0 is a tar.gz we can extract a version and possibly
        # release from:
        base_name = os.path.basename(self.sources[0])
        debug("Extracting version/release from: %s" % base_name)

        # usually a source tarball won't have a release, that is an RPM concept.
        # Don't forget dist!
        release = "1%{?dist}"

        # Example filename: tito-0.4.18.tar.gz:
        simple_version_re = re.compile(".*-(.*).(tar.gz|tgz|zip|bz2)")
        match = re.search(simple_version_re, base_name)
        if match:
            version = match.group(1)
        else:
            error_out("Unable to determine version from file: %s" % base_name)

        return (version, release)

    def replace_in_spec(self, replacements):
        """
        Replace lines in the spec file using the given replacements.

        Replacements are a tuple of a regex to look for, and a new line to
        substitute in when the regex matches.

        Replaces all lines with one pass through the file.
        """
        in_f = open(self.spec_file, 'r')
        out_f = open(self.spec_file + ".new", 'w')
        for line in in_f.readlines():
            for line_regex, new_line in replacements:
                match = re.match(line_regex, line)
                if match:
                    line = new_line
            out_f.write(line)

        in_f.close()
        out_f.close()
        shutil.move(self.spec_file + ".new", self.spec_file)

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

"""
Tito builders for a variety of common methods of building sources, srpms,
and rpms.
"""

import os
import sys
import re
import shutil
from pkg_resources import require
from distutils.version import LooseVersion as loose_version
from tempfile import mkdtemp

from tito.common import *
from tito.common import scl_to_rpm_option, get_latest_tagged_version, \
    find_wrote_in_rpmbuild_output
from tito.compat import *
from tito.exception import RunCommandException
from tito.release import *
from tito.exception import TitoException
from tito.config_object import ConfigObject


class BuilderBase(object):
    """
    A base class for all builders.

    Handles things we will *always* do, primarily handling temporary directories
    for rpmbuild.

    This class should *not* assume we're even using git.
    """
    # TODO: merge config into an object and kill the ConfigObject parent class
    def __init__(self, name=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        # Project directory where we started this build:
        self.start_dir = os.getcwd()

        self.project_name = name
        self.user_config = user_config
        self.args = args
        self.kwargs = kwargs
        self.config = config

        # Optional keyword arguments:
        self.dist = self._get_optional_arg(kwargs, 'dist', None)

        self.offline = self._get_optional_arg(kwargs, 'offline', False)
        self.auto_install = self._get_optional_arg(kwargs, 'auto_install',
                False)
        self.scl = self._get_optional_arg(args, 'scl', None) or \
                self._get_optional_arg(kwargs, 'scl', '')

        self.rpmbuild_options = self._get_optional_arg(kwargs,
                'rpmbuild_options', None)
        if not self.rpmbuild_options:
            self.rpmbuild_options = ''

        self.test = self._get_optional_arg(kwargs, 'test', False)
        # Allow a builder arg to override the test setting passed in, used by
        # releasers in their config sections.
        if args and 'test' in args:
            self.test = True

        # Location where we do all tito work and store resulting rpms:
        self.rpmbuild_basedir = build_dir
        # Location where we do actual rpmbuilds
        self.rpmbuild_dir = mkdtemp(dir=self.rpmbuild_basedir,
            prefix="rpmbuild-%s" % self.project_name)
        debug("Building in temp dir: %s" % self.rpmbuild_dir)
        self.rpmbuild_sourcedir = os.path.join(self.rpmbuild_dir, "SOURCES")
        self.rpmbuild_builddir = os.path.join(self.rpmbuild_dir, "BUILD")

        self._check_required_args()

        # Set to true once we've created/setup sources: (i.e. tar.gz)
        self.ran_tgz = False

        self.no_cleanup = False

        # List of full path to all sources for this package.
        self.sources = []

        # Artifacts we built:
        self.artifacts = []

    def _get_optional_arg(self, kwargs, arg, default):
        """
        Return the value of an optional keyword argument if it's present,
        otherwise the default provided.
        """
        if arg in kwargs:
            return kwargs[arg]
        return default

    def _check_required_args(self):
        for arg in self.REQUIRED_ARGS:
            if arg not in self.args:
                raise TitoException("Builder missing required argument: %s" %
                        arg)

    def run(self, options):
        """
        Perform the actions requested of the builder.

        NOTE: this method may do nothing if the user requested no build actions
        be performed. (i.e. only release tagging, etc)
        """
        print("Building package [%s]" % (self.build_tag))
        self.no_cleanup = options.no_cleanup

        # Reset list of artifacts on each call to run().
        self.artifacts = []

        try:
            try:
                if options.tgz:
                    self.tgz()
                if options.srpm:
                    self.srpm()
                if options.rpm:
                    # TODO: not protected anymore
                    self.rpm()
                    self._auto_install()
            except KeyboardInterrupt:
                print("Interrupted, cleaning up...")
        finally:
            self.cleanup()

        return self.artifacts

    def cleanup(self):
        """
        Remove all temporary files and directories.
        """
        if not self.no_cleanup:
            os.chdir('/')
            debug("Cleaning up [%s]" % self.rpmbuild_dir)
            getoutput("rm -rf %s" % self.rpmbuild_dir)
        else:
            print("WARNING: Leaving rpmbuild files in: %s" % self.rpmbuild_dir)

    def _check_build_dirs_access(self):
        """
        Ensure the build directories are writable.
        """
        if not os.access(self.rpmbuild_basedir, os.W_OK):
            error_out("%s is not writable." % self.rpmbuild_basedir)
        if not os.access(self.rpmbuild_dir, os.W_OK):
            error_out("%s is not writable." % self.rpmbuild_dir)
        if not os.access(self.rpmbuild_sourcedir, os.W_OK):
            error_out("%s is not writable." % self.rpmbuild_sourcedir)
        if not os.access(self.rpmbuild_builddir, os.W_OK):
            error_out("%s is not writable." % self.rpmbuild_builddir)

    def _create_build_dirs(self):
        """
        Create the build directories. Can safely be called multiple times.
        """
        getoutput("mkdir -p %s %s %s %s" % (
            self.rpmbuild_basedir, self.rpmbuild_dir,
            self.rpmbuild_sourcedir, self.rpmbuild_builddir))
        self._check_build_dirs_access()

    def srpm(self, dist=None):
        """
        Build a source RPM.
        """
        self._create_build_dirs()
        if not self.ran_tgz:
            self.tgz()

        if self.test:
            self._setup_test_specfile()

        debug("Creating srpm from spec file: %s" % self.spec_file)
        define_dist = ""
        if self.dist:
            debug("using self.dist: %s" % self.dist)
            define_dist = "--define 'dist %s'" % self.dist
        elif dist:
            debug("using dist: %s" % dist)
            define_dist = "--define 'dist %s'" % dist
        else:
            debug("*NOT* using dist at all")

        rpmbuild_options = self.rpmbuild_options + self._scl_to_rpmbuild_option()

        cmd = ('rpmbuild --define "_source_filedigest_algorithm md5"  --define'
            ' "_binary_filedigest_algorithm md5" %s %s %s --nodeps -bs %s' % (
                rpmbuild_options, self._get_rpmbuild_dir_options(),
                define_dist, self.spec_file))
        output = run_command_print(cmd)
        self.srpm_location = find_wrote_in_rpmbuild_output(output)[0]
        self.artifacts.append(self.srpm_location)

    def rpm(self):
        """ Build an RPM. """
        self._create_build_dirs()
        if not self.ran_tgz:
            self.tgz()

        define_dist = ""
        if self.dist:
            define_dist = "--define 'dist %s'" % self.dist

        rpmbuild_options = self.rpmbuild_options + self._scl_to_rpmbuild_option()

        cmd = ('rpmbuild --define "_source_filedigest_algorithm md5"  '
            '--define "_binary_filedigest_algorithm md5" %s %s %s --clean '
            '-ba %s' % (rpmbuild_options,
                self._get_rpmbuild_dir_options(), define_dist, self.spec_file))
        debug(cmd)
        try:
            output = run_command_print(cmd)
        except (KeyboardInterrupt, SystemExit):
            print("")
            exit(1)
        except RunCommandException:
            err = sys.exc_info()[1]
            msg = str(err)
            if (re.search('Failed build dependencies', err.output)):
                msg = "Please run 'yum-builddep %s' as root." % \
                    find_spec_file(self.relative_project_dir)
            error_out('%s' % msg)
        except Exception:
            err = sys.exc_info()[1]
            error_out('%s' % str(err))
        files_written = find_wrote_in_rpmbuild_output(output)
        if len(files_written) < 2:
            error_out("Error parsing rpmbuild output")
        self.srpm_location = files_written[0]
        self.artifacts.extend(files_written)

        print
        print("Successfully built: %s" % ' '.join(files_written))

    def _scl_to_rpmbuild_option(self):
        """ Returns rpmbuild option which disable or enable SC and print warning if needed """
        return scl_to_rpm_option(self.scl)

    def _auto_install(self):
        """
        If requested, auto install the RPMs we just built.
        """
        if self.auto_install:
            print
            print("Auto-installing packages:")
            print

            dont_install = []
            if 'NO_AUTO_INSTALL' in self.user_config:
                dont_install = self.user_config['NO_AUTO_INSTALL'].split(" ")
                debug("Will not auto-install any packages matching: %s" % dont_install)

            do_install = []
            for to_inst in self.artifacts:
                # Only install rpms:
                if not to_inst.endswith(".rpm") or to_inst.endswith(".src.rpm"):
                    continue

                install = True
                for skip in dont_install:
                    if skip in to_inst:
                        install = False
                        print("Skipping: %s" % to_inst)
                        break
                if install:
                    do_install.append(to_inst)

            print
            cmd = "sudo rpm -Uvh --force %s" % ' '.join(do_install)
            print("%s" % cmd)
            try:
                run_command(cmd)
                print
            except KeyboardInterrupt:
                pass


class Builder(ConfigObject, BuilderBase):
    """
    Parent builder class.

    Includes functionality for a standard Spacewalk package build. Packages
    which require other unusual behavior can subclass this to inject the
    desired behavior.
    """
    REQUIRED_ARGS = []

    # TODO: drop version
    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        """
        name - Package name that is being built.

        version - Version and release being built.

        tag - The git tag being built.

        build_dir - Temporary build directory where we can safely work.

        config - Merged configuration. (global plus package specific)

        user_config - User configuration from ~/.titorc.

        args - Optional arguments specific to each builder. Can be passed
        in explicitly by user on the CLI, or via a release target config
        entry. Only for things which vary on invocations of the builder,
        avoid using these if possible.
        """
        ConfigObject.__init__(self, config=config)
        BuilderBase.__init__(self, name=name, build_dir=build_dir, config=config,
                user_config=user_config, args=args, **kwargs)
        self.build_tag = tag

        self.build_version = self._get_build_version()

        if kwargs and 'options' in kwargs:
            print("WARNING: 'options' no longer a supported builder "
                    "constructor argument.")

        if self.config.has_section("requirements"):
            if self.config.has_option("requirements", "tito"):
                if loose_version(self.config.get("requirements", "tito")) > \
                        loose_version(require('tito')[0].version):
                    print("Error: tito version %s or later is needed to build this project." %
                            self.config.get("requirements", "tito"))
                    print("Your version: %s" % require('tito')[0].version)
                    sys.exit(-1)

        self.display_version = self._get_display_version()

        self.git_commit_id = get_build_commit(tag=self.build_tag,
            test=self.test)

        self.relative_project_dir = get_relative_project_dir(
            project_name=self.project_name, commit=self.git_commit_id)
        if self.relative_project_dir is None and self.test:
            sys.stderr.write("WARNING: rel-eng/packages/%s doesn't exist "
                "in git, using current directory\n" % self.project_name)
            self.relative_project_dir = get_relative_project_dir_cwd(
                self.git_root)

        tgz_base = self._get_tgz_name_and_ver()
        self.tgz_filename = tgz_base + ".tar.gz"
        self.tgz_dir = tgz_base
        self.artifacts = []

        # A copy of the git code from commit we're building:
        self.rpmbuild_gitcopy = os.path.join(self.rpmbuild_sourcedir,
                self.tgz_dir)

        # Used to make sure we only modify the spec file for a test build
        # once. The srpm method may be called multiple times during koji
        # releases to create the proper disttags, but we only want to modify
        # the spec file once.
        self.ran_setup_test_specfile = False

        # NOTE: These are defined later when/if we actually dump a copy of the
        # project source at the tag we're building. Only then can we search for
        # a spec file.
        self.spec_file_name = None
        self.spec_file = None

        # Set to path to srpm once we build one.
        self.srpm_location = None

    def _get_build_version(self):
        """
        Figure out the git tag and version-release we're building.
        """
        # Determine which package version we should build:
        build_version = None
        if self.build_tag:
            build_version = self.build_tag[len(self.project_name + "-"):]
        else:
            build_version = get_latest_tagged_version(self.project_name)
            if build_version is None:
                if not self.test:
                    error_out(["Unable to lookup latest package info.",
                            "Perhaps you need to tag first?"])
                sys.stderr.write("WARNING: unable to lookup latest package "
                    "tag, building untagged test project\n")
                build_version = get_spec_version_and_release(self.start_dir,
                    find_spec_file(in_dir=self.start_dir))
            self.build_tag = "%s-%s" % (self.project_name, build_version)

        if not self.test:
            check_tag_exists(self.build_tag, offline=self.offline)
        return build_version

    def tgz(self):
        """
        Create the .tar.gz required to build this package.

        Returns full path to the created tarball.
        """
        self._setup_sources()

        run_command("cp %s/%s %s/" %
                (self.rpmbuild_sourcedir, self.tgz_filename,
                    self.rpmbuild_basedir))

        self.ran_tgz = True
        full_path = os.path.join(self.rpmbuild_basedir, self.tgz_filename)
        print("Wrote: %s" % full_path)
        self.sources.append(full_path)
        self.artifacts.append(full_path)
        return full_path

    def rpm(self):
        """ Build an RPM. """
        self._create_build_dirs()
        if not self.ran_tgz:
            self.tgz()
        if self.test:
            self._setup_test_specfile()
        BuilderBase.rpm(self)

    def _setup_sources(self):
        """
        Create a copy of the git source for the project at the point in time
        our build tag was created.

        Created in the temporary rpmbuild SOURCES directory.
        """
        self._create_build_dirs()

        debug("Creating %s from git tag: %s..." % (self.tgz_filename,
            self.git_commit_id))
        create_tgz(self.git_root, self.tgz_dir, self.git_commit_id,
                self.relative_project_dir,
                os.path.join(self.rpmbuild_sourcedir, self.tgz_filename))

        # Extract the source so we can get at the spec file, etc.
        debug("Copying git source to: %s" % self.rpmbuild_gitcopy)
        run_command("cd %s/ && tar xzf %s" % (self.rpmbuild_sourcedir,
            self.tgz_filename))

        # Show contents of the directory structure we just extracted.
        debug('', 'ls -lR %s/' % self.rpmbuild_gitcopy)

        # NOTE: The spec file we actually use is the one exported by git
        # archive into the temp build directory. This is done so we can
        # modify the version/release on the fly when building test rpms
        # that use a git SHA1 for their version.
        self.spec_file_name = find_spec_file(in_dir=self.rpmbuild_gitcopy)
        self.spec_file = os.path.join(
            self.rpmbuild_gitcopy, self.spec_file_name)

    def _setup_test_specfile(self):
        if self.test and not self.ran_setup_test_specfile:
            # If making a test rpm we need to get a little crazy with the spec
            # file we're building off. (note that this is a temp copy of the
            # spec) Swap out the actual release for one that includes the git
            # SHA1 we're building for our test package:
            setup_specfile_script = get_script_path("test-setup-specfile.pl")
            cmd = "%s %s %s %s %s-%s %s" % \
                    (
                        setup_specfile_script,
                        self.spec_file,
                        self.git_commit_id[:7],
                        self.commit_count,
                        self.project_name,
                        self.display_version,
                        self.tgz_filename,
                    )
            run_command(cmd)
            self.build_version += ".git." + str(self.commit_count) + "." + str(self.git_commit_id[:7])
            self.ran_setup_test_specfile = True

    def _get_rpmbuild_dir_options(self):
        return ('--define "_topdir %s" --define "_sourcedir %s" --define "_builddir %s" --define '
            '"_srcrpmdir %s" --define "_rpmdir %s" ' % (
                self.rpmbuild_dir,
                self.rpmbuild_sourcedir, self.rpmbuild_builddir,
                self.rpmbuild_basedir, self.rpmbuild_basedir))

    def _get_tgz_name_and_ver(self):
        """
        Returns the project name for the .tar.gz to build. Normally this is
        just the project name, but in the case of Satellite packages it may
        be different.
        """
        return "%s-%s" % (self.project_name, self.display_version)

    def _get_display_version(self):
        """
        Get the package display version to build.

        Normally this is whatever is rel-eng/packages/. In the case of a --test
        build it will be the SHA1 for the HEAD commit of the current git
        branch.
        """
        if self.test:
            # should get latest commit for given directory *NOT* HEAD
            latest_commit = get_latest_commit(".")
            self.commit_count = get_commit_count(self.build_tag, latest_commit)
            version = "git-%s.%s" % (self.commit_count, latest_commit[:7])
        else:
            version = self.build_version.split("-")[0]
        return version


class NoTgzBuilder(Builder):
    """
    Builder for packages that do not require the creation of a tarball.
    Usually these packages have source tarballs checked directly into git.
    """

    def tgz(self):
        """ Override parent behavior, we already have a tgz. """
        # TODO: Does it make sense to allow user to create a tgz for this type
        # of project?
        self._setup_sources()
        self.ran_tgz = True

        debug("Scanning for sources.")
        cmd = "/usr/bin/spectool --list-files '%s' | awk '{print $2}' |xargs -l1 --no-run-if-empty basename " % self.spec_file
        result = run_command(cmd)
        self.sources = map(lambda x: os.path.join(self.rpmbuild_gitcopy, x), result.split("\n"))
        debug("  Sources: %s" % self.sources)

    def _get_rpmbuild_dir_options(self):
        """
        Override parent behavior slightly.

        These packages store tar's, patches, etc, directly in their project
        dir, use the git copy we create as the sources directory when
        building package so everything can be found:
        """
        return ('--define "_topdir %s" --define "_sourcedir %s" --define "_builddir %s" '
            '--define "_srcrpmdir %s" --define "_rpmdir %s" ' % (
                self.rpmbuild_dir,
                self.rpmbuild_gitcopy, self.rpmbuild_builddir,
                self.rpmbuild_basedir, self.rpmbuild_basedir))

    def _setup_test_specfile(self):
        """ Override parent behavior. """
        if self.test:
            # If making a test rpm we need to get a little crazy with the spec
            # file we're building off. (note that this is a temp copy of the
            # spec) Swap out the actual release for one that includes the git
            # SHA1 we're building for our test package:
            debug("setup_test_specfile:commit_count = %s" % str(self.commit_count))
            script = "test-setup-specfile.pl"
            cmd = "%s %s %s %s" % \
                    (
                        script,
                        self.spec_file,
                        self.git_commit_id[:7],
                        self.commit_count,
                    )
            run_command(cmd)


class GemBuilder(NoTgzBuilder):
    """
    Gem Builder

    Builder for packages whose sources are managed as gem source structures
    and the upstream project does not want to store gem files in git.
    """

    def _setup_sources(self):
        """
        Create a copy of the git source for the project at the point in time
        our build tag was created.

        Created in the temporary rpmbuild SOURCES directory.
        """
        self._create_build_dirs()

        debug("Creating %s from git tag: %s..." % (self.tgz_filename,
            self.git_commit_id))
        create_tgz(self.git_root, self.tgz_dir, self.git_commit_id,
                self.relative_project_dir,
                os.path.join(self.rpmbuild_sourcedir, self.tgz_filename))

        # Extract the source so we can get at the spec file, etc.
        debug("Copying git source to: %s" % self.rpmbuild_gitcopy)
        run_command("cd %s/ && tar xzf %s" % (self.rpmbuild_sourcedir,
            self.tgz_filename))

        # Find the gemspec
        gemspec_filename = find_gemspec_file(in_dir=self.rpmbuild_gitcopy)

        debug("Building gem: %s in %s" % (gemspec_filename,
            self.rpmbuild_gitcopy))
        # FIXME - this is ugly and should probably be handled better
        cmd = "gem_name=$(cd %s/ && gem build %s | awk '/File/ {print $2}'); \
            cp %s/$gem_name %s/" % (self.rpmbuild_gitcopy, gemspec_filename,
            self.rpmbuild_gitcopy, self.rpmbuild_sourcedir)

        run_command(cmd)

        # NOTE: The spec file we actually use is the one exported by git
        # archive into the temp build directory. This is done so we can
        # modify the version/release on the fly when building test rpms
        # that use a git SHA1 for their version.
        self.spec_file_name = find_spec_file(in_dir=self.rpmbuild_gitcopy)
        self.spec_file = os.path.join(
            self.rpmbuild_gitcopy, self.spec_file_name)


class UpstreamBuilder(NoTgzBuilder):
    """
    Builder for packages that are based off an upstream git tag.
    Commits applied in downstream git become patches applied to the
    upstream tarball.

    i.e. satellite-java-0.4.0-5 built from spacewalk-java-0.4.0-1 and any
    patches applied in satellite git.
    i.e. spacewalk-setup-0.4.0-20 built from spacewalk-setup-0.4.0-1 and any
    patches applied in satellite git.
    """

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        NoTgzBuilder.__init__(self, name=name, tag=tag,
                build_dir=build_dir, config=config,
                user_config=user_config,
                args=args, **kwargs)

        if not config or not config.has_option("buildconfig",
                "upstream_name"):
            # No upstream_name defined, assume we're keeping the project name:
            self.upstream_name = self.project_name
        else:
            self.upstream_name = config.get("buildconfig", "upstream_name")
        # Need to assign these after we've exported a copy of the spec file:
        self.upstream_version = None
        self.upstream_tag = None

    def tgz(self):
        """
        Override parent behavior, we need a tgz from the upstream spacewalk
        project we're based on.
        """
        # TODO: Wasteful step here, all we really need is a way to look for a
        # spec file at the point in time this release was tagged.
        NoTgzBuilder._setup_sources(self)
        # If we knew what it was named at that point in time we could just do:
        # Export a copy of our spec file at the revision to be built:
#        cmd = "git show %s:%s%s > %s" % (self.git_commit_id,
#                self.relative_project_dir, self.spec_file_name,
#                self.spec_file)
#        debug(cmd)
        self._create_build_dirs()

        self.upstream_version = self._get_upstream_version()
        self.upstream_tag = "%s-%s-1" % (self.upstream_name,
                self.upstream_version)

        print("Building upstream tgz for tag [%s]" % (self.upstream_tag))
        if self.upstream_tag != self.build_tag:
            check_tag_exists(self.upstream_tag, offline=self.offline)

        self.spec_file = os.path.join(self.rpmbuild_sourcedir,
                self.spec_file_name)
        run_command("cp %s %s" % (os.path.join(self.rpmbuild_gitcopy,
            self.spec_file_name), self.spec_file))

        # Create the upstream tgz:
        prefix = "%s-%s" % (self.upstream_name, self.upstream_version)
        tgz_filename = "%s.tar.gz" % prefix
        commit = get_build_commit(tag=self.upstream_tag)
        relative_dir = get_relative_project_dir(
            project_name=self.upstream_name, commit=commit)
        tgz_fullpath = os.path.join(self.rpmbuild_sourcedir, tgz_filename)
        print("Creating %s from git tag: %s..." % (tgz_filename, commit))
        create_tgz(self.git_root, prefix, commit, relative_dir,
                tgz_fullpath)
        self.ran_tgz = True
        self.sources.append(tgz_fullpath)

        # If these are equal then the tag we're building was likely created in
        # Spacewalk and thus we don't need to do any patching.
        if (self.upstream_tag == self.build_tag and not self.test):
            return

        self.patch_upstream()

    def _patch_upstream(self):
        """ Insert patches into the spec file we'll be building
            returns (patch_number, patch_insert_index, patch_apply_index, lines)
        """
        f = open(self.spec_file, 'r')
        lines = f.readlines()
        f.close()

        patch_pattern = re.compile('^Patch(\d+):')
        source_pattern = re.compile('^Source(\d+)?:')

        # Find the largest PatchX: line, or failing that SourceX:
        patch_number = 0  # What number should we use for our PatchX line
        patch_insert_index = 0  # Where to insert our PatchX line in the list
        patch_apply_index = 0  # Where to insert our %patchX line in the list
        array_index = 0  # Current index in the array
        for line in lines:
            match = source_pattern.match(line)
            if match:
                patch_insert_index = array_index + 1

            match = patch_pattern.match(line)
            if match:
                patch_insert_index = array_index + 1
                patch_number = int(match.group(1)) + 1

            if line.startswith("%prep"):
                # We'll apply patch right after prep if there's no %setup line
                patch_apply_index = array_index + 2
            elif line.startswith("%setup"):
                patch_apply_index = array_index + 2  # already added a line

            array_index += 1

        debug("patch_insert_index = %s" % patch_insert_index)
        debug("patch_apply_index = %s" % patch_apply_index)
        if patch_insert_index == 0 or patch_apply_index == 0:
            error_out("Unable to insert PatchX or %patchX lines in spec file")
        return (patch_number, patch_insert_index, patch_apply_index, lines)

    def patch_upstream(self):
        """
        Generate patches for any differences between our tag and the
        upstream tag, and apply them into an exported copy of the
        spec file.
        """
        patch_filename = "%s-to-%s-%s.patch" % (self.upstream_tag,
                self.project_name, self.build_version)
        patch_file = os.path.join(self.rpmbuild_gitcopy,
                patch_filename)
        patch_dir = self.git_root
        if self.relative_project_dir != "/":
            patch_dir = os.path.join(self.git_root,
                    self.relative_project_dir)
        os.chdir(patch_dir)
        debug("patch dir = %s" % patch_dir)
        print("Generating patch [%s]" % patch_filename)
        debug("Patch: %s" % patch_file)
        patch_command = "git diff --relative %s..%s > %s" % \
                (self.upstream_tag, self.git_commit_id,
                        patch_file)
        debug("Generating patch with: %s" % patch_command)
        output = run_command(patch_command)
        print(output)
        (status, output) = getstatusoutput(
            "grep 'Binary files .* differ' %s " % patch_file)
        if status == 0 and output != "":
            error_out("You are doomed. Diff contains binary files. You can not use this builder")

        # Creating two copies of the patch here in the temp build directories
        # just out of laziness. Some builders need sources in SOURCES and
        # others need them in the git copy. Being lazy here avoids one-off
        # hacks and both copies get cleaned up anyhow.
        run_command("cp %s %s" % (patch_file, self.rpmbuild_sourcedir))

        (patch_number, patch_insert_index, patch_apply_index, lines) = self._patch_upstream()

        lines.insert(patch_insert_index, "Patch%s: %s\n" % (patch_number,
            patch_filename))
        lines.insert(patch_apply_index, "%%patch%s -p1\n" % (patch_number))
        self._write_spec(lines)

    def _write_spec(self, lines):
        """ Write 'lines' to self.spec_file """
        # Now write out the modified lines to the spec file copy:
        f = open(self.spec_file, 'w')
        for line in lines:
            f.write(line)
        f.close()

    def _get_upstream_version(self):
        """
        Get the upstream version. Checks for "upstreamversion" in the spec file
        and uses it if found. Otherwise assumes the upstream version is equal
        to the version we're building.

        i.e. satellite-java-0.4.15 will be built on spacewalk-java-0.4.15
        with just the package release being incremented on rebuilds.
        """
        # Use upstreamversion if defined in the spec file:
        (status, output) = getstatusoutput(
            "cat %s | grep 'define upstreamversion' | "
            "awk '{ print $3 ; exit }'" % self.spec_file)
        if status == 0 and output != "":
            return output

        if self.test:
            return self.build_version.split("-")[0]
        # Otherwise, assume we use our version:
        else:
            return self.display_version

    def _get_rpmbuild_dir_options(self):
        """
        Override parent behavior slightly.

        These packages store tar's, patches, etc, directly in their project
        dir, use the git copy we create as the sources directory when
        building package so everything can be found:
        """
        return ('--define "_topdir %s" --define "_sourcedir %s" --define "_builddir %s" '
            '--define "_srcrpmdir %s" --define "_rpmdir %s" ' % (
                self.rpmbuild_dir,
                self.rpmbuild_sourcedir, self.rpmbuild_builddir,
                self.rpmbuild_basedir, self.rpmbuild_basedir))


# Legacy class name for backward compatability:
class SatelliteBuilder(UpstreamBuilder):
    pass


class MockBuilder(Builder):
    """
    Uses the mock tool to create a chroot for building packages for a different
    OS version than you may be currently using.
    """
    REQUIRED_ARGS = ['mock']

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        # Mock builders need to use the packages normally configured builder
        # to get at a proper SRPM:
        self.normal_builder = create_builder(name, tag, config,
                build_dir, user_config, args, **kwargs)

        Builder.__init__(self, name=name, tag=tag,
                build_dir=build_dir, config=config,
                user_config=user_config,
                args=args, **kwargs)

        self.mock_tag = args['mock']
        self.mock_cmd_args = ""
        if 'mock_config_dir' in args:
            mock_config_dir = args['mock_config_dir']
            if not mock_config_dir.startswith("/"):
                # If not an absolute path, assume below git root:
                mock_config_dir = os.path.join(self.git_root, mock_config_dir)
            if not os.path.exists(mock_config_dir):
                raise TitoException("No such mock config dir: %s" % mock_config_dir)
            self.mock_cmd_args = "%s --configdir=%s" % (self.mock_cmd_args, mock_config_dir)

        # Optional argument which will skip mock --init and add --no-clean
        # and --no-cleanup-after:
        self.speedup = False
        if 'speedup' in args:
            self.speedup = True
            self.mock_cmd_args = "%s --no-clean --no-cleanup-after" % \
                    (self.mock_cmd_args)

        if 'mock_args' in args:
            self.mock_cmd_args = "%s %s" % (self.mock_cmd_args, args['mock_args'])

        # TODO: error out if mock package is not installed

        # TODO: error out if user does not have mock group

    def srpm(self, dist=None):
        """
        Build a source RPM.

        MockBuilder will use an instance of the normal builder for a package
        internally just so we can generate a SRPM correctly before we pass it
        into mock.
        """
        self.normal_builder.srpm(dist)
        self.srpm_location = self.normal_builder.srpm_location
        self.artifacts.append(self.srpm_location)

    def rpm(self):
        """
        Uses the SRPM
        Override the base builder rpm method.
        """

        print("Creating rpms for %s-%s in mock: %s" % (
            self.project_name, self.display_version, self.mock_tag))
        if not self.srpm_location:
            self.srpm()
        print("Using srpm: %s" % self.srpm_location)
        self._build_in_mock()

    def _build_in_mock(self):
        if not self.speedup:
            print("Initializing mock...")
            output = run_command("mock %s -r %s --init" % (self.mock_cmd_args, self.mock_tag))
        else:
            print("Skipping mock --init due to speedup option.")

        print("Installing deps in mock...")
        output = run_command("mock %s -r %s %s" % (
            self.mock_cmd_args, self.mock_tag, self.srpm_location))
        print("Building RPMs in mock...")
        output = run_command('mock %s -r %s --rebuild %s' %
                (self.mock_cmd_args, self.mock_tag, self.srpm_location))
        mock_output_dir = os.path.join(self.rpmbuild_dir, "mockoutput")
        output = run_command("mock %s -r %s --copyout /builddir/build/RPMS/ %s" %
                (self.mock_cmd_args, self.mock_tag, mock_output_dir))

        # Copy everything mock wrote out to /tmp/tito:
        files = os.listdir(mock_output_dir)
        run_command("cp -v %s/*.rpm %s" %
                (mock_output_dir, self.rpmbuild_basedir))
        print
        print("Wrote:")
        for rpm in files:
            rpm_path = os.path.join(self.rpmbuild_basedir, rpm)
            print("  %s" % rpm_path)
            self.artifacts.append(rpm_path)
        print


class BrewDownloadBuilder(Builder):
    """
    A special case builder which uses pre-existing Brew builds and
    pulls down the resulting rpms locally. Useful in some cases when
    generating yum repositories during a release.
    """
    REQUIRED_ARGS = ['disttag']

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            args=None, **kwargs):

        Builder.__init__(self, name=name, tag=tag,
                build_dir=build_dir, config=config,
                user_config=user_config,
                args=args, **kwargs)

        self.dist_tag = args['disttag']

    def rpm(self):
        """
        Uses the SRPM
        Override the base builder rpm method.
        """

        print("Fetching rpms for %s.%s from brew:" % (
            self.build_tag, self.dist_tag))
        self._fetch_from_brew()

    def _fetch_from_brew(self):
        brew_nvr = "%s.%s" % (self.build_tag, self.dist_tag)
        debug("Brew NVR: %s" % brew_nvr)
        os.chdir(self.rpmbuild_dir)
        run_command("brew download-build %s" % brew_nvr)

        # Wipe out the src rpm for now:
        run_command("rm *.src.rpm")

        # Copy everything brew downloaded out to /tmp/tito:
        files = os.listdir(self.rpmbuild_dir)
        run_command("cp -v %s/*.rpm %s" %
                (self.rpmbuild_dir, self.rpmbuild_basedir))
        print
        print("Wrote:")
        for rpm in files:
            # Just incase anything slips into the build dir:
            if not rpm.endswith(".rpm"):
                continue
            rpm_path = os.path.join(self.rpmbuild_basedir, rpm)
            print("  %s" % rpm_path)
            self.artifacts.append(rpm_path)
        print


class GitAnnexBuilder(NoTgzBuilder):
    """
    Builder for packages with existing tarballs checked in using git-annex,
    e.g. referencing an external source (web remote).  This builder will
    "unlock" the source files to get the real contents, include them in the
    SRPM, then restore the automatic git-annex symlinks on completion.
    """

    def _setup_sources(self):
        super(GitAnnexBuilder, self)._setup_sources()

        old_cwd = os.getcwd()
        os.chdir(os.path.join(old_cwd, self.relative_project_dir))

        (status, output) = getstatusoutput("which git-annex")
        if status != 0:
            msg = "Please run 'yum install git-annex' as root."
            error_out('%s' % msg)

        run_command("git-annex lock")
        annexed_files = run_command("git-annex find --include='*'").splitlines()
        run_command("git-annex get")
        run_command("git-annex unlock")
        debug("  Annex files: %s" % annexed_files)

        for annex in annexed_files:
            debug("Copying unlocked file %s" % annex)
            os.remove(os.path.join(self.rpmbuild_gitcopy, annex))
            shutil.copy(annex, self.rpmbuild_gitcopy)

        os.chdir(old_cwd)

    def cleanup(self):
        if self._lock_force_supported(self._get_annex_version()):
            run_command("git-annex lock --force")
        else:
            run_command("git-annex lock")
        super(GitAnnexBuilder, self).cleanup()

    def _get_annex_version(self):
        # git-annex needs to support --force when locking files.
        ga_version = run_command('git-annex version').split('\n')
        if ga_version[0].startswith('git-annex version'):
            return ga_version[0].split()[-1]
        else:
            return 0

    def _lock_force_supported(self, version):
        return compare_version(version, '5.20131213') >= 0

########NEW FILE########
__FILENAME__ = buildparser
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from tito.exception import TitoException


class BuildTargetParser(object):
    """
    Parses build targets from a string in the format of:
        <branch1>:<target> <branch2>:<target> ...

    Each target must be associated with a valid branch.
    """

    def __init__(self, releaser_config, release_target, valid_branches):
        self.releaser_config = releaser_config
        self.release_target = release_target
        self.valid_branches = valid_branches

    def get_build_targets(self):
        build_targets = {}
        if not self.releaser_config.has_option(self.release_target, "build_targets"):
            return build_targets

        defined_build_targets = self.releaser_config.get(self.release_target,
                                                         "build_targets").split(" ")
        for build_target in defined_build_targets:
            # Ignore any empty from multiple spaces in the file.
            if not build_target:
                continue

            branch, target = self._parse_build_target(build_target)
            build_targets[branch] = target

        return build_targets

    def _parse_build_target(self, build_target):
        """ Parses a string in the format of branch:target """
        if not build_target:
            raise TitoException("Invalid build_target: %s. Format: <branch>:<target>"
                                % build_target)

        parts = build_target.split(":")
        if len(parts) != 2:
            raise TitoException("Invalid build_target: %s. Format: <branch>:<target>"
                                % build_target)
        branch = parts[0]
        if branch not in self.valid_branches:
            raise TitoException("Invalid build_target: %s. Unknown branch reference."
                                % build_target)
        target = parts[1]
        if not target:
            raise TitoException("Invalid build_target: %s. Empty target" % build_target)

        return (branch, target)

########NEW FILE########
__FILENAME__ = cli
# Copyright (c) 2008-2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Tito's Command Line Interface
"""

import sys
import os
import random

from optparse import OptionParser

from tito.common import *
from tito.compat import *
from tito.exception import *

# Hack for Python 2.4, seems to require we import these so they get compiled
# before we try to dynamically import them based on a string name.
import tito.tagger

TITO_PROPS = "tito.props"
RELEASERS_CONF_FILENAME = "releasers.conf"
ASSUMED_NO_TAR_GZ_PROPS = """
[buildconfig]
builder = tito.builder.NoTgzBuilder
tagger = tito.tagger.ReleaseTagger
"""


class FauxConfigFile(object):
    """ Allows us to read config from a string. """
    def __init__(config_str):
        # We'll re-add the newline when returned:
        self.lines = config_str.split("\n")

    def readline(self):
        if len(self.lines) > 0:
            # Pop a line off the front of the list:
            line = self.lines[0]
            self.lines = self.lines[1:]
            return line + "\n"
        else:
            # Indicates end of file:
            return ''


class ConfigLoader(object):
    """
    Responsible for the sometimes complicated process of loading the repo's
    tito.props, and overriding it with package specific tito.props, sometimes
    from a past tag to ensure build consistency.
    """

    def __init__(self, package_name, output_dir, tag):
        self.package_name = package_name
        self.output_dir = output_dir
        self.tag = tag

    def load(self):
        self.config = self._read_config()
        self._read_project_config()
        self._check_required_config(self.config)
        return self.config

    def _read_config(self):
        """
        Read global build.py configuration from the rel-eng dir of the git
        repository we're being run from.

        NOTE: We always load the latest config file, not tito.props as it
        was for the tag being operated on.
        """
        # List of filepaths to config files we'll be loading:
        rel_eng_dir = os.path.join(find_git_root(), "rel-eng")
        filename = os.path.join(rel_eng_dir, TITO_PROPS)
        if not os.path.exists(filename):
            error_out("Unable to locate branch configuration: %s"
                "\nPlease run 'tito init'" % filename)

        # Load the global config. Later, when we know what tag/package we're
        # building, we may also load that and potentially override some global
        # settings.
        config = RawConfigParser()
        config.read(filename)

        self._check_legacy_globalconfig(config)
        return config

    def _check_legacy_globalconfig(self, config):
        # globalconfig renamed to buildconfig for better overriding in per-package
        # tito.props. If we see globalconfig, automatically rename it after
        # loading and warn the user.
        if config.has_section('globalconfig'):
            if not config.has_section('buildconfig'):
                config.add_section('buildconfig')
            print("WARNING: Please rename [globalconfig] to [buildconfig] in "
                "tito.props")
            for k, v in config.items('globalconfig'):
                if k == 'default_builder':
                    print("WARNING: please rename 'default_builder' to "
                        "'builder' in tito.props")
                    config.set('buildconfig', 'builder', v)
                elif k == 'default_tagger':
                    print("WARNING: please rename 'default_tagger' to "
                        "'tagger' in tito.props")
                    config.set('buildconfig', 'tagger', v)
                else:
                    config.set('buildconfig', k, v)
            config.remove_section('globalconfig')

    def _check_required_config(self, config):
        # Verify the config contains what we need from it:
        required_global_config = [
            (BUILDCONFIG_SECTION, DEFAULT_BUILDER),
            (BUILDCONFIG_SECTION, DEFAULT_TAGGER),
        ]
        for section, option in required_global_config:
            if not config.has_section(section) or not \
                config.has_option(section, option):
                    error_out("tito.props missing required config: %s %s" % (
                        section, option))

    def _read_project_config(self):
        """
        Read project specific tito config if it exists.

        If no tag is specified we use tito.props from the current HEAD.
        If a tag is specified, we try to load a tito.props from that
        tag.
        """
        debug("Determined package name to be: %s" % self.package_name)

        # Use the properties file in the current project directory, if it
        # exists:
        current_props_file = os.path.join(os.getcwd(), TITO_PROPS)
        if (os.path.exists(current_props_file)):
            self.config.read(current_props_file)
            print("Loaded package specific tito.props overrides")

        # Check for a tito.props back when this tag was created and use it
        # instead. (if it exists)
        if self.tag:
            relative_dir = get_relative_project_dir(self.package_name, self.tag)
            debug("Relative project dir: %s" % relative_dir)

            cmd = "git show %s:%s%s" % (self.tag, relative_dir,
                    TITO_PROPS)
            debug(cmd)
            (status, output) = getstatusoutput(cmd)

            if status == 0:
                faux_config_file = FauxConfigFile(output)
                config.read_fp(faux_config_file)
                print("Loaded package specific tito.props overrides from %s" %
                    self.tag)
                return

        debug("Unable to locate package specific config for this package.")


def read_user_config():
    config = {}
    file_loc = os.path.expanduser("~/.spacewalk-build-rc")
    try:
        f = open(file_loc)
    except:
        file_loc = os.path.expanduser("~/.titorc")
        try:
            f = open(file_loc)
        except:
            # File doesn't exist but that's ok because it's optional.
            return config

    for line in f.readlines():
        if line.strip() == "":
            continue
        tokens = line.split("=")
        if len(tokens) != 2:
            raise Exception("Error parsing ~/.spacewalk-build-rc: %s" % line)
        config[tokens[0]] = tokens[1].strip()
    return config


def lookup_build_dir(user_config):
    """
    Read build_dir in from ~/.spacewalk-build-rc if it exists, otherwise
    return the current working directory.
    """
    build_dir = DEFAULT_BUILD_DIR

    if 'RPMBUILD_BASEDIR' in user_config:
        build_dir = user_config["RPMBUILD_BASEDIR"]

    return build_dir


class CLI(object):
    """
    Parent command line interface class.

    Simply delegated to sub-modules which group appropriate command line
    options together.
    """

    def main(self, argv):
        if len(argv) < 1 or not argv[0] in CLI_MODULES.keys():
            self._usage()
            sys.exit(1)

        module_class = CLI_MODULES[argv[0]]
        module = module_class()
        return module.main(argv)

    def _usage(self):
        print("Usage: tito MODULENAME --help")
        print("Supported modules:")
        print("   build    - Build packages.")
        print("   init     - Initialize directory for use by tito.")
        print("   release  - Build and release to yum repos")
        print("   report   - Display various reports on the repo.")
        print("   tag      - Tag package releases.")


class BaseCliModule(object):
    """ Common code used amongst all CLI modules. """

    def __init__(self, usage):
        self.parser = OptionParser(usage)
        self.config = None
        self.options = None
        self.user_config = read_user_config()

        self._add_common_options()

    def _add_common_options(self):
        """
        Add options to the command line parser which are relevant to all
        modules.
        """
        # Options used for many different activities:
        self.parser.add_option("--debug", dest="debug", action="store_true",
                help="print debug messages", default=False)
        self.parser.add_option("--offline", dest="offline",
            action="store_true",
            help="do not attempt any remote communication (avoid using " +
                "this please)",
            default=False)

        default_output_dir = lookup_build_dir(self.user_config)
        if not os.path.exists(default_output_dir):
            print("Creating output directory: %s" % default_output_dir)
            run_command("mkdir %s" % default_output_dir)

        self.parser.add_option("-o", "--output", dest="output_dir",
                metavar="OUTPUTDIR", default=default_output_dir,
                help="Path to write temp files, tarballs and rpms to. "
                    "(default %s)"
                    % default_output_dir)

    def main(self, argv):
        (self.options, self.args) = self.parser.parse_args(argv)

        self._validate_options()

        if len(argv) < 1:
            print(self.parser.error("Must supply an argument. "
                "Try -h for help."))

    def load_config(self, package_name, build_dir, tag):
        self.config = ConfigLoader(package_name, build_dir, tag).load()

        if self.config.has_option(BUILDCONFIG_SECTION,
                "offline"):
            self.options.offline = True

        # TODO: Not ideal:
        if self.options.debug:
            os.environ['DEBUG'] = "true"

        # Check if config defines a custom lib dir, if so we add it
        # to the python path allowing users to specify custom builders/taggers
        # in their config:
        if self.config.has_option(BUILDCONFIG_SECTION,
                "lib_dir"):
            lib_dir = self.config.get(BUILDCONFIG_SECTION,
                    "lib_dir")
            if lib_dir[0] != '/':
                # Looks like a relative path, assume from the git root:
                lib_dir = os.path.join(find_git_root(), lib_dir)

            if os.path.exists(lib_dir):
                sys.path.append(lib_dir)
                debug("Added lib dir to PYTHONPATH: %s" % lib_dir)
            else:
                print("WARNING: lib_dir specified but does not exist: %s" %
                    lib_dir)

    def _validate_options(self):
        """
        Subclasses can implement if they need to check for any
        incompatible cmd line options.
        """
        pass


class BuildModule(BaseCliModule):

    def __init__(self):
        BaseCliModule.__init__(self, "usage: %prog build [options]")

        self.parser.add_option("--tgz", dest="tgz", action="store_true",
                help="Build .tar.gz")
        self.parser.add_option("--srpm", dest="srpm", action="store_true",
                help="Build srpm")
        self.parser.add_option("--rpm", dest="rpm", action="store_true",
                help="Build rpm")
        self.parser.add_option("-i", "--install", dest="auto_install",
                action="store_true", default=False,
                help="Install any binary rpms being built. (WARNING: " +
                    "uses sudo rpm -Uvh --force)")
        self.parser.add_option("--dist", dest="dist", metavar="DISTTAG",
                help="Dist tag to apply to srpm and/or rpm. (i.e. .el5)")

        self.parser.add_option("--test", dest="test", action="store_true",
                help="use current branch HEAD instead of latest package tag")
        self.parser.add_option("--no-cleanup", dest="no_cleanup",
                action="store_true",
                help="do not clean up temporary build directories/files")
        self.parser.add_option("--tag", dest="tag", metavar="PKGTAG",
                help="build a specific tag instead of the latest version " +
                    "(i.e. spacewalk-java-0.4.0-1)")

        self.parser.add_option("--builder", dest="builder",
                help="Override the normal builder by specifying a full class "
                    "path or one of the pre-configured shortcuts.")

        self.parser.add_option("--arg", dest="builder_args",
                action="append",
                help="Custom arguments specific to a particular builder."
                    " (key=value)")

        self.parser.add_option("--list-tags", dest="list_tags",
                action="store_true",
                help="List tags for which we build this package",
                )

        self.parser.add_option("--rpmbuild-options", dest='rpmbuild_options',
                default='',
                metavar="OPTIONS", help="Options to pass to rpmbuild.")
        self.parser.add_option("--scl", dest='scl',
                default='',
                metavar="COLLECTION", help="Build package for software collection.")

    def main(self, argv):
        BaseCliModule.main(self, argv)

        build_dir = os.path.normpath(os.path.abspath(self.options.output_dir))
        package_name = get_project_name(tag=self.options.tag)

        build_tag = self.options.tag

        self.load_config(package_name, build_dir, self.options.tag)

        args = self._parse_builder_args()
        kwargs = {
            'dist': self.options.dist,
            'test': self.options.test,
            'offline': self.options.offline,
            'auto_install': self.options.auto_install,
            'rpmbuild_options': self.options.rpmbuild_options,
            'scl': self.options.scl,
        }

        builder = create_builder(package_name, build_tag,
                self.config,
                build_dir, self.user_config, args,
                builder_class=self.options.builder, **kwargs)
        return builder.run(self.options)

    def _validate_options(self):
        if self.options.srpm and self.options.rpm:
            error_out("Cannot combine --srpm and --rpm")
        if self.options.test and self.options.tag:
            error_out("Cannot build test version of specific tag.")

    def _parse_builder_args(self):
        """
        Builder args are sometimes needed for builders that require runtime
        data.

        On the CLI this is specified with multiple uses of:

            --arg key=value

        This method parses any --arg's given and splits the key/value
        pairs out into a dict.
        """
        args = {}
        if self.options.builder_args is None:
            return args

        for arg in self.options.builder_args:
            if '=' in arg:
                key, value = arg.split("=")
                args[key] = value
            else:
                # Allow no value args such as 'myscript --auto'
                args[arg] = ''
        return args


class ReleaseModule(BaseCliModule):

    # Maps a releaser key (used on CLI) to the actual releaser class to use.
    # Projects can point to their own releasers in their tito.props.

    def __init__(self):
        BaseCliModule.__init__(self, "usage: %prog release [options] TARGET")

        self.parser.add_option("--no-cleanup", dest="no_cleanup",
                action="store_true",
                help="do not clean up temporary build directories/files")
        self.parser.add_option("--tag", dest="tag", metavar="PKGTAG",
                help="build a specific tag instead of the latest version " +
                    "(i.e. spacewalk-java-0.4.0-1)")

        self.parser.add_option("--dry-run", dest="dry_run",
                action="store_true", default=False,
                help="Do not actually commit/push anything during release.")

        self.parser.add_option("--all", action="store_true",
                help="Run all release targets configured.")

        self.parser.add_option("--test", action="store_true",
                help="use current branch HEAD instead of latest package tag")

        self.parser.add_option("-y", "--yes", dest="auto_accept", action="store_true",
                help="Do not require input, just accept commits and builds")

        self.parser.add_option("--all-starting-with", dest="all_starting_with",
                help="Run all release targets starting with the given string.")

        self.parser.add_option("-l", "--list", dest="list_releasers",
                action="store_true",
                help="List all configured release targets.")

        self.parser.add_option("--no-build", dest="no_build",
                action="store_true", default=False,
                help="Do not perform a build after a DistGit commit")

        self.parser.add_option("-s", "--scratch", dest="scratch",
                action="store_true",
                help="Perform a scratch build in Koji")
        self.parser.add_option("--arg", dest="builder_args",
                action="append",
                help="Custom arguments to pass to the builder."
                    " (key=value)")

#        self.parser.add_option("--list-tags", dest="list_tags",
#                action="store_true",
#                help="List tags for which we build this package",
#                )
        # These are specific only to Koji releaser, what can we do?
#        self.parser.add_option("--only-tags", dest="only_tags",
#                action="append", metavar="KOJITAG",
#                help="Build in koji only for specified tags",
#                )

    def _validate_options(self):

        if self.options.all and self.options.all_starting_with:
            error_out("Cannot combine --all and --all-starting-with.")

        if (self.options.all or self.options.all_starting_with) and \
                len(self.args) > 1:
            error_out("Cannot use explicit release targets with "
                    "--all or --all-starting-with.")

    def _read_releaser_config(self):
        """
        Read the releaser targets from rel-eng/releasers.conf.
        """
        rel_eng_dir = os.path.join(find_git_root(), "rel-eng")
        filename = os.path.join(rel_eng_dir, RELEASERS_CONF_FILENAME)
        config = RawConfigParser()
        config.read(filename)
        return config

    def _legacy_builder_hack(self, releaser_config):
        """
        Support the old style koji builds when config is still in global
        tito.props, as opposed to the new releasers.conf.
        """
        # Handle koji:
        if self.config.has_section("koji") and not \
                releaser_config.has_section("koji"):
            print("WARNING: legacy 'koji' section in tito.props, please "
                    "consider creating a target in releasers.conf.")
            print("Simulating 'koji' release target for now.")
            releaser_config.add_section('koji')
            releaser_config.set('koji', 'releaser', 'tito.release.KojiReleaser')
            releaser_config.set('koji', 'autobuild_tags',
                    self.config.get('koji', 'autobuild_tags'))

            # TODO: find a way to get koji builds going through the new release
            # target config file, tricky as each koji tag gets it's own
            # section in tito.props. They should probably all get their own
            # target.

            # for opt in ["autobuild_tags", "disttag", "whitelist", "blacklist"]:
            #     if self.config.has_option("koji", opt):
            #         releaser_config.set('koji', opt, self.config.get(
            #             "koji", opt))

    def _print_releasers(self, releaser_config):
        print("Available release targets:")
        for section in releaser_config.sections():
            print("  %s" % section)

    def _calc_release_targets(self, releaser_config):
        targets = []
        if self.options.all_starting_with:
            for target in releaser_config.sections():
                if target.startswith(self.options.all_starting_with):
                    targets.append(target)
        elif self.options.all:
            for target in releaser_config.sections():
                targets.append(target)
        else:
            targets = self.args[1:]
        return targets

    def main(self, argv):
        BaseCliModule.main(self, argv)

        releaser_config = self._read_releaser_config()

        if self.options.list_releasers:
            self._print_releasers(releaser_config)
            sys.exit(1)

        # First arg is sub-command 'release', the rest should be our release
        # targets:
        if len(self.args) < 2 and (self.options.all_starting_with is None) and \
                (self.options.all is None):
            error_out("You must supply at least one release target.")

        build_dir = os.path.normpath(os.path.abspath(self.options.output_dir))
        package_name = get_project_name(tag=self.options.tag)

        self.load_config(package_name, build_dir, self.options.tag)
        self._legacy_builder_hack(releaser_config)

        targets = self._calc_release_targets(releaser_config)
        print("Will release to the following targets: %s" % ", ".join(targets))

        orig_cwd = os.getcwd()

        # Create an instance of the releaser we intend to use:
        for target in targets:
            print("Releasing to target: %s" % target)
            if not releaser_config.has_section(target):
                error_out("No such releaser configured: %s" % target)
            releaser_class = get_class_by_name(releaser_config.get(target, "releaser"))
            debug("Using releaser class: %s" % releaser_class)
            builder_args = {}
            if self.options.builder_args and len(self.options.builder_args) > 0:
                for arg in self.options.builder_args:
                    key, val = arg.split('=')
                    debug("Passing builder arg: %s = %s" % (key, val))
                    # TODO: support list values
                    builder_args[key] = val
            kwargs = {
                'builder_args': builder_args,
                'offline': self.options.offline
            }

            releaser = releaser_class(
                name=package_name,
                tag=self.options.tag,
                build_dir=build_dir,
                config=self.config,
                user_config=self.user_config,
                target=target,
                releaser_config=releaser_config,
                no_cleanup=self.options.no_cleanup,
                test=self.options.test,
                auto_accept=self.options.auto_accept,
                **kwargs)

            try:
                try:
                    releaser.release(dry_run=self.options.dry_run,
                            no_build=self.options.no_build,
                            scratch=self.options.scratch)
                except KeyboardInterrupt:
                    print("Interrupted, cleaning up...")
            finally:
                releaser.cleanup()

            # Make sure we go back to where we started, otherwise multiple
            # builders gets very confused:
            os.chdir(orig_cwd)
            print


class TagModule(BaseCliModule):

    def __init__(self):
        BaseCliModule.__init__(self, "usage: %prog tag [options]")

        # Options for tagging new package releases:
        # NOTE: deprecated and no longer needed:
        self.parser.add_option("--tag-release", dest="tag_release",
                action="store_true",
                help="Deprecated, no longer required.")
        self.parser.add_option("--keep-version", dest="keep_version",
                action="store_true",
                help=("Use spec file version/release exactly as "
                    "specified in spec file to tag package."))
        self.parser.add_option("--use-version", dest="use_version",
                help=("Update the spec file with the specified version."))

        self.parser.add_option("--no-auto-changelog", action="store_true",
                default=False,
                help=("Don't automatically create a changelog "
                    "entry for this tag if none is found"))
        self.parser.add_option("--accept-auto-changelog", action="store_true",
                default=False,
                help=("Automatically accept the generated changelog."))

        self.parser.add_option("--auto-changelog-message",
                dest="auto_changelog_msg", metavar="MESSAGE",
                help=("Use MESSAGE as the default changelog message for "
                      "new packages"))

        self.parser.add_option("--undo", "-u", dest="undo", action="store_true",
                help="Undo the most recent (un-pushed) tag.")

    def main(self, argv):
        BaseCliModule.main(self, argv)

        build_dir = os.path.normpath(os.path.abspath(self.options.output_dir))
        package_name = get_project_name(tag=None)

        self.load_config(package_name, build_dir, None)
        if self.config.has_option(BUILDCONFIG_SECTION,
                "block_tagging"):
            debug("block_tagging defined in tito.props")
            error_out("Tagging has been disabled in this git branch.")

        tagger_class = None
        if self.options.use_version:
            tagger_class = get_class_by_name("tito.tagger.ForceVersionTagger")
        elif self.config.has_option("buildconfig", "tagger"):
            tagger_class = get_class_by_name(self.config.get("buildconfig",
                "tagger"))
        else:
            tagger_class = get_class_by_name(self.config.get(
                BUILDCONFIG_SECTION, DEFAULT_TAGGER))
        debug("Using tagger class: %s" % tagger_class)

        tagger = tagger_class(config=self.config,
                user_config=self.user_config,
                keep_version=self.options.keep_version,
                offline=self.options.offline)

        try:
            return tagger.run(self.options)
        except TitoException:
            e = sys.exc_info()[1]
            error_out(e.message)

    def _validate_options(self):
        if self.options.keep_version and self.options.use_version:
            error_out("Cannot combine --keep-version and --use-version")


class InitModule(BaseCliModule):
    """ CLI Module for initializing a project for use with tito. """

    def __init__(self):
        BaseCliModule.__init__(self, "usage: %prog init [options]")

    def main(self, argv):
        # DO NOT CALL BaseCliModule.main(self)
        # we are initializing tito to work in this module and
        # calling main will result in a configuration error.
        should_commit = False

        rel_eng_dir = os.path.join(find_git_root(), "rel-eng")
        print("Creating tito metadata in: %s" % rel_eng_dir)

        propsfile = os.path.join(rel_eng_dir, TITO_PROPS)
        if not os.path.exists(propsfile):
            if not os.path.exists(rel_eng_dir):
                getoutput("mkdir -p %s" % rel_eng_dir)
                print("   - created %s" % rel_eng_dir)

            # write out tito.props
            out_f = open(propsfile, 'w')
            out_f.write("[buildconfig]\n")
            out_f.write("builder = %s\n" % 'tito.builder.Builder')
            out_f.write(
                "tagger = %s\n" % 'tito.tagger.VersionTagger')
            out_f.write("changelog_do_not_remove_cherrypick = 0\n")
            out_f.write("changelog_format = %s (%ae)\n")
            out_f.close()
            print("   - wrote %s" % TITO_PROPS)

            getoutput('git add %s' % propsfile)
            should_commit = True

        # prep the packages metadata directory
        pkg_dir = os.path.join(rel_eng_dir, "packages")
        readme = os.path.join(pkg_dir, '.readme')

        if not os.path.exists(readme):
            if not os.path.exists(pkg_dir):
                getoutput("mkdir -p %s" % pkg_dir)
                print("   - created %s" % pkg_dir)

            # write out readme file explaining what pkg_dir is for
            readme = os.path.join(pkg_dir, '.readme')
            out_f = open(readme, 'w')
            out_f.write("the rel-eng/packages directory contains metadata files\n")
            out_f.write("named after their packages. Each file has the latest tagged\n")
            out_f.write("version and the project's relative directory.\n")
            out_f.close()
            print("   - wrote %s" % readme)

            getoutput('git add %s' % readme)
            should_commit = True

        if should_commit:
            getoutput('git commit -m "Initialized to use tito. "')
            print("   - committed to git")

        print("Done!")
        return []


class ReportModule(BaseCliModule):
    """ CLI Module For Various Reports. """

    def __init__(self):
        BaseCliModule.__init__(self, "usage: %prog report [options]")

        self.parser.add_option("--untagged-diffs", dest="untagged_report",
                action="store_true",
                help="%s %s %s" % (
                    "Print out diffs for all packages with changes between",
                    "their most recent tag and HEAD. Useful for determining",
                    "which packages are in need of a re-tag.",
                ))
        self.parser.add_option("--untagged-commits", dest="untagged_commits",
                action="store_true",
                help="%s %s %s" % (
                    "Print out the list for all packages with changes between",
                    "their most recent tag and HEAD. Useful for determining",
                    "which packages are in need of a re-tag.",
                ))

    def main(self, argv):
        BaseCliModule.main(self, argv)

        if self.options.untagged_report:
            self._run_untagged_report(self.config)
            sys.exit(1)

        if self.options.untagged_commits:
            self._run_untagged_commits(self.config)
            sys.exit(1)
        return []

    def _run_untagged_commits(self, config):
        """
        Display a report of all packages with differences between HEAD and
        their most recent tag, as well as a patch for that diff. Used to
        determine which packages are in need of a rebuild.
        """
        print("Scanning for packages that may need to be tagged...")
        print("")
        git_root = find_git_root()
        rel_eng_dir = os.path.join(git_root, "rel-eng")
        os.chdir(git_root)
        package_metadata_dir = os.path.join(rel_eng_dir, "packages")
        for root, dirs, files in os.walk(package_metadata_dir):
            for md_file in files:
                if md_file[0] == '.':
                    continue
                f = open(os.path.join(package_metadata_dir, md_file))
                (version, relative_dir) = f.readline().strip().split(" ")

                # Hack for single project git repos:
                if relative_dir == '/':
                    relative_dir = ""

                project_dir = os.path.join(git_root, relative_dir)
                self._print_log(config, md_file, version, project_dir)

    def _run_untagged_report(self, config):
        """
        Display a report of all packages with differences between HEAD and
        their most recent tag, as well as a patch for that diff. Used to
        determine which packages are in need of a rebuild.
        """
        print("Scanning for packages that may need to be tagged...")
        print("")
        git_root = find_git_root()
        rel_eng_dir = os.path.join(git_root, "rel-eng")
        os.chdir(git_root)
        package_metadata_dir = os.path.join(rel_eng_dir, "packages")
        for root, dirs, files in os.walk(package_metadata_dir):
            for md_file in files:
                if md_file[0] == '.':
                    continue
                f = open(os.path.join(package_metadata_dir, md_file))
                (version, relative_dir) = f.readline().strip().split(" ")

                # Hack for single project git repos:
                if relative_dir == '/':
                    relative_dir = ""

                project_dir = os.path.join(git_root, relative_dir)
                self._print_diff(config, md_file, version, project_dir,
                        relative_dir)

    def _print_log(self, config, package_name, version, project_dir):
        """
        Print the log between the most recent package tag and HEAD, if
        necessary.
        """
        last_tag = "%s-%s" % (package_name, version)
        try:
            os.chdir(project_dir)
            patch_command = ("git log --pretty=oneline "
                "--relative %s..%s -- %s" % (last_tag, "HEAD", "."))
            output = run_command(patch_command)
            if (output):
                print("-" * (len(last_tag) + 8))
                print("%s..%s:" % (last_tag, "HEAD"))
                print(output)
        except:
            print("%s no longer exists" % project_dir)

    def _print_diff(self, config, package_name, version,
            full_project_dir, relative_project_dir):
        """
        Print a diff between the most recent package tag and HEAD, if
        necessary.
        """
        last_tag = "%s-%s" % (package_name, version)
        os.chdir(full_project_dir)
        patch_command = "git diff --relative %s..%s" % \
                (last_tag, "HEAD")
        output = run_command(patch_command)

        # If the diff contains 1 line then there is no diff:
        linecount = len(output.split("\n"))
        if linecount == 1:
            return

        name_and_version = "%s   %s" % (package_name, relative_project_dir)
        # Otherwise, print out info on the diff for this package:
        print("#" * len(name_and_version))
        print(name_and_version)
        print("#" * len(name_and_version))
        print("")
        print(patch_command)
        print("")
        print(output)
        print("")
        print("")
        print("")
        print("")
        print("")


CLI_MODULES = {
    "build": BuildModule,
    "tag": TagModule,
    "release": ReleaseModule,
    "report": ReportModule,
    "init": InitModule,
}

########NEW FILE########
__FILENAME__ = common
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Common operations.
"""
import os
import re
import sys
import traceback
import subprocess
import shlex

from tito.compat import *
from tito.exception import RunCommandException

DEFAULT_BUILD_DIR = "/tmp/tito"
DEFAULT_BUILDER = "builder"
DEFAULT_TAGGER = "tagger"
BUILDCONFIG_SECTION = "buildconfig"
SHA_RE = re.compile(r'\b[0-9a-f]{30,}\b')

# Define some shortcuts to fully qualified Builder classes to make things
# a little more concise for CLI users. Mock is probably the only one this
# is relevant for at this time.
BUILDER_SHORTCUTS = {
    'mock': 'tito.builder.MockBuilder'
}


def extract_sources(spec_file_lines):
    """
    Returns a list of sources from the given spec file.

    Some of these will be URL's, which is fine they will be ignored.
    We're really just after relative filenames that might live in the same
    location as the spec file, mostly used with NoTgzBuilder packages.
    """
    filenames = []
    source_pattern = re.compile('^Source\d+?:\s*(.*)')
    for line in spec_file_lines:
        match = source_pattern.match(line)
        if match:
            filenames.append(match.group(1))
    return filenames


def extract_bzs(output):
    """
    Parses the output of CVS diff or a series of git commit log entries,
    looking for new lines which look like a commit of the format:

    ######: Commit message

    Returns a list of lines of text similar to:

    Resolves: #XXXXXX - Commit message
    """
    regex = re.compile(r"^- (\d*)\s?[:-]+\s?(.*)")
    diff_regex = re.compile(r"^(\+- )+(\d*)\s?[:-]+\s?(.*)")
    bzs = []
    for line in output.split("\n"):
        match = re.match(regex, line)
        match2 = re.match(diff_regex, line)
        if match:
            bzs.append((match.group(1), match.group(2)))
        elif match2:
            bzs.append((match2.group(2), match2.group(3)))

    output = []
    for bz in bzs:
        output.append("Resolves: #%s - %s" % (bz[0], bz[1]))
    return output


def error_out(error_msgs):
    """
    Print the given error message (or list of messages) and exit.
    """
    print
    if isinstance(error_msgs, list):
        for line in error_msgs:
            print("ERROR: %s" % line)
    else:
        print("ERROR: %s" % error_msgs)
    print
#    if 'DEBUG' in os.environ:
#        traceback.print_stack()
    sys.exit(1)


def create_builder(package_name, build_tag,
        config, build_dir, user_config, args,
        builder_class=None, **kwargs):
    """
    Create (but don't run) the builder class. Builder object may be
    used by other objects without actually having run() called.
    """

    # Allow some shorter names for builders for CLI users.
    if builder_class in BUILDER_SHORTCUTS:
        builder_class = BUILDER_SHORTCUTS[builder_class]

    if builder_class is None:
        debug("---- Builder class is None")
        if config.has_option("buildconfig", "builder"):
            builder_class = get_class_by_name(config.get("buildconfig",
                "builder"))
        else:
            debug("---- Global config")
            builder_class = get_class_by_name(config.get(
                BUILDCONFIG_SECTION, DEFAULT_BUILDER))
    else:
        # We were given an explicit builder class as a str, get the actual
        # class reference:
        builder_class = get_class_by_name(builder_class)
    debug("Using builder class: %s" % builder_class)

    # Instantiate the builder:
    builder = builder_class(
        name=package_name,
        tag=build_tag,
        build_dir=build_dir,
        config=config,
        user_config=user_config,
        args=args,
        **kwargs)
    return builder


def find_file_with_extension(in_dir=None, suffix=None):
    """ Find the file with given extension in the current directory. """
    if in_dir is None:
        in_dir = os.getcwd()
    file_name = None
    debug("Looking for %s in %s" % (suffix, in_dir))
    for f in os.listdir(in_dir):
        if f.endswith(suffix):
            if file_name is not None:
                error_out("At least two %s files in directory: %s and %s" % (suffix, file_name, f))
            file_name = f
            debug("Using file: %s" % f)
    if file_name is None:
        error_out("Unable to locate a %s file in %s" % (suffix, in_dir))
    else:
        return file_name


def find_spec_file(in_dir=None):
    """
    Find the first spec file in the current directory.

    Returns only the file name, rather than the full path.
    """
    return find_file_with_extension(in_dir, '.spec')


def find_gemspec_file(in_dir=None):
    """
    Find the first spec file in the current directory.

    Returns only the file name, rather than the full path.
    """
    return find_file_with_extension(in_dir, '.gemspec')


def find_git_root():
    """
    Find the top-level directory for this git repository.

    Returned as a full path.
    """
    (status, cdup) = getstatusoutput("git rev-parse --show-cdup")
    if status > 0:
        error_out(["%s does not appear to be within a git checkout." %
                os.getcwd()])

    if cdup.strip() == "":
        cdup = "./"
    return os.path.abspath(cdup)


def extract_sha1(output):
    match = SHA_RE.search(output)
    if match:
        return match.group(0)
    else:
        return ""


def run_command(command, print_on_success=False):
    """
    Run command.
    If command fails, print status code and command output.
    """
    (status, output) = getstatusoutput(command)
    if status > 0:
        sys.stderr.write("\n########## ERROR ############\n")
        sys.stderr.write("Error running command: %s\n" % command)
        sys.stderr.write("Status code: %s\n" % status)
        sys.stderr.write("Command output: %s\n" % output)
        raise RunCommandException(command, status, output)
    elif print_on_success:
        print("Command: %s\n" % command)
        print("Status code: %s\n" % status)
        print("Command output: %s\n" % output)
    return output


def run_command_print(command):
    """
    Simliar to run_command but prints each line of output on the fly.
    """
    output = []
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    p = subprocess.Popen(shlex.split(command),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        universal_newlines=True)
    for line in run_subprocess(p):
        line = line.rstrip('\n')
        print(line)
        output.append(line)
    print("\n"),
    if p.poll() > 0:
        raise RunCommandException(command, p.poll(), "\n".join(output))
    return '\n'.join(output)


def run_subprocess(p):
    while(True):
        retcode = p.poll()
        line = p.stdout.readline()
        if len(line) > 0:
            yield line
        if(retcode is not None):
            break


def tag_exists_locally(tag):
    (status, output) = getstatusoutput("git tag | grep %s" % tag)
    if status > 0:
        return False
    else:
        return True


def tag_exists_remotely(tag):
    """ Returns True if the tag exists in the remote git repo. """
    try:
        get_git_repo_url()
    except:
        sys.stderr.write('Warning: remote.origin do not exist. Assuming --offline, for remote tag checking.\n')
        return False
    sha1 = get_remote_tag_sha1(tag)
    debug("sha1 = %s" % sha1)
    if sha1 == "":
        return False
    return True


def get_local_tag_sha1(tag):
    tag_sha1 = run_command(
        "git ls-remote ./. --tag %s | awk '{ print $1 ; exit }'"
        % tag)
    tag_sha1 = extract_sha1(tag_sha1)
    return tag_sha1


def head_points_to_tag(tag):
    """
    Ensure the current git head is the same commit as tag.

    For some reason the git commands we normally use to fetch SHA1 for a tag
    do not work when comparing to the HEAD SHA1. Using a different command
    for now.
    """
    debug("Checking that HEAD commit is %s" % tag)
    head_sha1 = run_command("git rev-list --max-count=1 HEAD")
    tag_sha1 = run_command("git rev-list --max-count=1 %s" % tag)
    debug("   head_sha1 = %s" % head_sha1)
    debug("   tag_sha1 = %s" % tag_sha1)
    return head_sha1 == tag_sha1


def undo_tag(tag):
    """
    Executes git commands to delete the given tag and undo the most recent
    commit. Assumes you have taken necessary precautions to ensure this is
    what you want to do.
    """
    # Using --merge here as it appears to undo the changes in the commit,
    # but preserve any modified files:
    output = run_command("git tag -d %s && git reset --merge HEAD^1" % tag)
    print(output)


def get_remote_tag_sha1(tag):
    """
    Get the SHA1 referenced by this git tag in the remote git repo.
    Will return "" if the git tag does not exist remotely.
    """
    # TODO: X11 forwarding messages can appear in this output, find a better way
    repo_url = get_git_repo_url()
    print("Checking for tag [%s] in git repo [%s]" % (tag, repo_url))
    cmd = "git ls-remote %s --tag %s | awk '{ print $1 ; exit }'" % \
            (repo_url, tag)
    upstream_tag_sha1 = run_command(cmd)
    upstream_tag_sha1 = extract_sha1(upstream_tag_sha1)
    return upstream_tag_sha1


def check_tag_exists(tag, offline=False):
    """
    Check that the given git tag exists in a git repository.
    """
    if not tag_exists_locally(tag):
        error_out("Tag does not exist locally: [%s]" % tag)

    if offline:
        return

    tag_sha1 = get_local_tag_sha1(tag)
    debug("Local tag SHA1: %s" % tag_sha1)

    try:
        repo_url = get_git_repo_url()
    except:
        sys.stderr.write('Warning: remote.origin do not exist. Assuming --offline, for remote tag checking.\n')
        return
    upstream_tag_sha1 = get_remote_tag_sha1(tag)
    if upstream_tag_sha1 == "":
        error_out(["Tag does not exist in remote git repo: %s" % tag,
            "You must tag, then git push and git push --tags"])

    debug("Remote tag SHA1: %s" % upstream_tag_sha1)

    if upstream_tag_sha1 != tag_sha1:
        error_out("Tag %s references %s locally but %s upstream." % (tag,
            tag_sha1, upstream_tag_sha1))


def debug(text, cmd=None):
    """
    Print the text if --debug was specified.
    If cmd is specified, run the command and print its output after text.
    """
    if 'DEBUG' in os.environ:
        print(text)
        if cmd:
            run_command(cmd, True)


def get_spec_version_and_release(sourcedir, spec_file_name):
    command = ("""rpm -q --qf '%%{version}-%%{release}\n' --define """
        """"_sourcedir %s" --define 'dist %%undefined' --specfile """
        """%s 2> /dev/null | grep -e '^$' -v | head -1""" % (sourcedir, spec_file_name))
    return run_command(command)


def scl_to_rpm_option(scl, silent=None):
    """ Returns rpm option which disable or enable SC and print warning if needed """
    rpm_options = ""
    cmd = "rpm --eval '%scl'"
    output = run_command(cmd).rstrip()
    if scl:
        if (output != scl) and (output != "%scl") and not silent:
            print("Warning: Meta package of software collection %s installed, but --scl defines %s" % (output, scl))
            print("         Redefining scl macro to %s for this package." % scl)
        rpm_options += " --define 'scl %s'" % scl
    else:
        if (output != "%scl") and (not silent):
            print("Warning: Meta package of software collection %s installed, but --scl is not present." % output)
            print("         Undefining scl macro for this package.")
        # can be replaced by "--undefined scl" when el6 and fc17 is retired
        rpm_options += " --eval '%undefine scl'"
    return rpm_options


def get_project_name(tag=None, scl=None):
    """
    Extract the project name from the specified tag or a spec file in the
    current working directory. Error out if neither is present.
    """
    if tag is not None:
        p = re.compile('(.*?)-(\d.*)')
        m = p.match(tag)
        if not m:
            error_out("Unable to determine project name in tag: %s" % tag)
        return m.group(1)
    else:
        spec_file_path = os.path.join(os.getcwd(), find_spec_file())
        if not os.path.exists(spec_file_path):
            error_out("spec file: %s does not exist" % spec_file_path)

        output = run_command(
            "rpm -q --qf '%%{name}\n' %s --specfile %s 2> /dev/null | grep -e '^$' -v | head -1" %
            (scl_to_rpm_option(scl, silent=True), spec_file_path))
        if not output:
            error_out(["Unable to determine project name from spec file: %s" % spec_file_path,
                "Try rpm -q --specfile %s" % spec_file_path,
                "Try rpmlint -i %s" % spec_file_path])
        return output


def replace_version(line, new_version):
    """
    Attempts to replace common setup.py version formats in the given line,
    and return the modified line. If no version is present the line is
    returned as is.

    Looking for things like version="x.y.z" with configurable case,
    whitespace, and optional use of single/double quotes.
    """
    # Mmmmm pretty regex!
    ver_regex = re.compile("(\s*)(version)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)",
            re.IGNORECASE)
    m = ver_regex.match(line)
    if m:
        result_tuple = list(m.group(1, 2, 3, 4, 5, 6))
        result_tuple.append(new_version)
        result_tuple.extend(list(m.group(8, 9)))
        new_line = "%s%s%s%s%s%s%s%s%s\n" % tuple(result_tuple)
        return new_line
    else:
        return line


def get_relative_project_dir(project_name, commit):
    """
    Return the project's sub-directory relative to the git root.

    This could be a different directory than where the project currently
    resides, so we export a copy of the project's metadata from
    rel-eng/packages/ at the point in time of the tag we are building.
    """
    cmd = "git show %s:rel-eng/packages/%s" % (commit,
            project_name)
    (status, pkg_metadata) = getstatusoutput(cmd)
    tokens = pkg_metadata.strip().split(" ")
    debug("Got package metadata: %s" % tokens)
    if status != 0:
        return None
    return tokens[1]


def get_relative_project_dir_cwd(git_root):
    """
    Returns the patch to the project we're working with relative to the
    git root using the cwd.

    *MUST* be called before doing any os.cwd().

    i.e. java/, satellite/install/Spacewalk-setup/, etc.
    """
    current_dir = os.getcwd()
    relative = current_dir[len(git_root) + 1:] + "/"
    if relative == "/":
        relative = "./"
    return relative


def get_build_commit(tag, test=False):
    """ Return the git commit we should build. """
    if test:
        return get_latest_commit(".")
    else:
        tag_sha1 = run_command(
            "git ls-remote ./. --tag %s | awk '{ print $1 ; exit }'"
            % tag)
        tag_sha1 = extract_sha1(tag_sha1)
        commit_id = run_command('git rev-list --max-count=1 %s' % tag_sha1)
        return commit_id


def get_commit_count(tag, commit_id):
    """ Return the number of commits between the tag and commit_id"""
    # git describe returns either a tag-commitcount-gSHA1 OR
    # just the tag.
    #
    # so we need to pass in the tag as well.
    # output = run_command("git describe --match=%s %s" % (tag, commit_id))
    # if tag == output:
    #     return 0
    # else:
    #     parse the count from the output
    (status, output) = getstatusoutput(
        "git describe --match=%s %s" % (tag, commit_id))

    debug("tag - %s" % tag)
    debug("output - %s" % output)

    if status != 0:
        debug("git describe of tag %s failed (%d)" % (tag, status))
        return 0

    if tag != output:
        # tag-commitcount-gSHA1, we want the penultimate value
        cnt = output.split("-")[-2]
        return cnt

    return 0


def get_latest_commit(path="."):
    """ Return the latest git commit for the given path. """
    commit_id = run_command("git log --pretty=format:%%H --max-count=1 %s" % path)
    return commit_id


def get_commit_timestamp(sha1_or_tag):
    """
    Get the timestamp of the git commit or tag we're building. Used to
    keep the hash the same on all .tar.gz's we generate for a particular
    version regardless of when they are generated.
    """
    output = run_command(
        "git rev-list --timestamp --max-count=1 %s | awk '{print $1}'"
        % sha1_or_tag)
    return output


def create_tgz(git_root, prefix, commit, relative_dir,
    dest_tgz):
    """
    Create a .tar.gz from a projects source in git.
    """
    os.chdir(os.path.abspath(git_root))
    timestamp = get_commit_timestamp(commit)

    timestamp_script = get_script_path("tar-fixup-stamp-comment.pl")

    # Accomodate standalone projects with specfile i root of git repo:
    relative_git_dir = "%s" % relative_dir
    if relative_git_dir in ['/', './']:
        relative_git_dir = ""

    # command to generate a git-archive
    git_archive_cmd = 'git archive --format=tar --prefix=%s/ %s:%s' % (
        prefix, commit, relative_git_dir)

    # Run git-archive separately if --debug was specified.
    # This allows us to detect failure early.
    # On git < 1.7.4-rc0, `git archive ... commit:./` fails!
    debug('git-archive fails if relative dir is not in git tree',
        '%s > /dev/null' % git_archive_cmd)

    # If we're still alive, the previous command worked
    archive_cmd = ('%s | %s %s %s | gzip -n -c - > %s' % (
        git_archive_cmd, timestamp_script,
        timestamp, commit, dest_tgz))
    debug(archive_cmd)
    return run_command(archive_cmd)


def get_git_repo_url():
    """
    Return the url of this git repo.

    Uses ~/.git/config remote origin url.
    """
    return run_command("git config remote.origin.url")


def get_latest_tagged_version(package_name):
    """
    Return the latest git tag for this package in the current branch.
    Uses the info in rel-eng/packages/package-name.

    Returns None if file does not exist.
    """
    git_root = find_git_root()
    rel_eng_dir = os.path.join(git_root, "rel-eng")
    file_path = "%s/packages/%s" % (rel_eng_dir, package_name)
    debug("Getting latest package info from: %s" % file_path)
    if not os.path.exists(file_path):
        return None

    output = run_command("awk '{ print $1 ; exit }' %s" % file_path)
    if output is None or output.strip() == "":
        error_out("Error looking up latest tagged version in: %s" % file_path)

    return output


def normalize_class_name(name):
    """
    Just a hack to accomodate tito config files with builder/tagger
    classes referenced in the spacewalk.releng namespace, which has
    since been renamed to just tito.
    """
    look_for = "spacewalk.releng."
    if name.startswith(look_for):
        sys.stderr.write("Warning: spacewalk.releng.* namespace in tito.props is obsolete. Use tito.* instead.\n")
        name = "%s%s" % ("tito.", name[len(look_for):])
    return name


def get_script_path(scriptname):
    """
    Hack to accomodate functional tests running from source, rather than
    requiring tito to actually be installed. This variable is only set by
    test scripts, normally we assume scripts are on PATH.
    """
    # TODO: Would be nice to get rid of this hack.
    scriptpath = scriptname  # assume on PATH by default
    if 'TITO_SRC_BIN_DIR' in os.environ:
        bin_dir = os.environ['TITO_SRC_BIN_DIR']
        scriptpath = os.path.join(bin_dir, scriptname)
    return scriptpath


def get_class_by_name(name):
    """
    Get a Python class specified by it's fully qualified name.

    NOTE: Does not actually create an instance of the object, only returns
    a Class object.
    """
    name = normalize_class_name(name)
    # Split name into module and class name:
    tokens = name.split(".")
    class_name = tokens[-1]
    module = '.'.join(tokens[0:-1])

    debug("Importing %s" % name)
    mod = __import__(module, globals(), locals(), [class_name])
    return getattr(mod, class_name)


def increase_version(version_string):
    regex = re.compile(r"^(%.*)|(.+\.)?([0-9]+)(\..*|_.*|%.*|$)")
    match = re.match(regex, version_string)
    if match:
        matches = list(match.groups())
        # Increment the number in the third match group, if there is one
        if matches[2]:
            matches[2] = str(int(matches[2]) + 1)
        # Join everything back up, skipping match groups with None
        return "".join([x for x in matches if x])

    # If no match, return the original string
    return version_string


def reset_release(release_string):
    regex = re.compile(r"(^|\.)([.0-9]+)(\.|%|$)")
    return regex.sub(r"\g<1>1\g<3>", release_string)


def increase_zstream(release_string):
    # If we do not have zstream, create .0 and then bump the version
    regex = re.compile(r"^(.*%{\?dist})$")
    bumped_string = regex.sub(r"\g<1>.0", release_string)
    return increase_version(bumped_string)


def find_wrote_in_rpmbuild_output(output):
    """
    Parse the output from rpmbuild looking for lines beginning with
    "Wrote:". Return a list of file names for each path found.
    """
    paths = []
    look_for = "Wrote: "
    for line in output.split('\n'):
        if line.startswith(look_for):
            paths.append(line[len(look_for):])
            debug("Found wrote line: %s" % paths[-1])
    if not paths:
        error_out("Unable to locate 'Wrote: ' lines in rpmbuild output: '%s'" % output)
    return paths


def compare_version(version1, version2):
    """
    Compare two version strings, returning negative if version1 is < version2,
    zero when equal and positive when version1 > version2.
    """
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]
    a = normalize(version1)
    b = normalize(version2)
    return (a > b) - (a < b)

########NEW FILE########
__FILENAME__ = compat
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Compatibility library for Python 2.4 up through Python 3.
"""
import os
import sys
ENCODING = sys.getdefaultencoding()
PY2 = sys.version_info[0] == 2
if PY2:
    import commands
    from ConfigParser import NoOptionError
    from ConfigParser import RawConfigParser
    from StringIO import StringIO
else:
    import subprocess
    from configparser import NoOptionError
    from configparser import RawConfigParser
    from io import StringIO


def getstatusoutput(cmd):
    """
    Returns (status, output) of executing cmd in a shell.
    Supports Python 2.4 and 3.x.
    """
    if PY2:
        return commands.getstatusoutput(cmd)
    else:
        return subprocess.getstatusoutput(cmd)


def getoutput(cmd):
    """
    Returns output of executing cmd in a shell.
    Supports Python 2.4 and 3.x.
    """
    return getstatusoutput(cmd)[1]


def dictionary_override(d1, d2):
    """
    Return a new dictionary object where
    d2 elements override d1 elements.
    """
    if PY2:
        overrides = d1.items() + d2.items()
    else:
        overrides = d1.items() | d2.items()
    return dict(overrides)


def write(fd, str):
    """
    A version of os.write that
    supports Python 2.4 and 3.x.
    """
    if PY2:
        os.write(fd, str)
    else:
        os.write(fd, bytes(str, ENCODING))

########NEW FILE########
__FILENAME__ = config_object
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Shared code for builder and tagger class
"""

import os
from tito.common import find_git_root


class ConfigObject(object):
    """
    Perent class for Builder and Tagger with shared code
    """

    def __init__(self, config=None):
        """
        config - Merged configuration. (global plus package specific)
        """
        self.config = config

        # Override global configurations using local configurations
        for section in config.sections():
            for options in config.options(section):
                if not self.config.has_section(section):
                    self.config.add_section(section)
                self.config.set(section, options,
                        config.get(section, options))

        self.git_root = find_git_root()
        self.rel_eng_dir = os.path.join(self.git_root, "rel-eng")

########NEW FILE########
__FILENAME__ = distributionbuilder
import os

from tito.builder import UpstreamBuilder
from tito.common import debug, run_command, error_out
from tito.compat import *


class DistributionBuilder(UpstreamBuilder):
    """ This class is used for building packages for distributions.
    Parent class UpstreamBuilder build one big patch from upstream and create e.g.:
      Patch0: foo-1.2.13-1-to-foo-1.2.13-3-sat.patch
    This class create one patch per each release. E.g.:
      Patch0: foo-1.2.13-1-to-foo-1.2.13-2-sat.patch
      Patch1: foo-1.2.13-2-to-foo-1.2.13-3-sat.patch
    """
    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None, args=None, **kwargs):
        UpstreamBuilder.__init__(self, name, tag, build_dir, config,
                user_config, args, **kwargs)
        self.patch_files = []

    def patch_upstream(self):
        """ Create one patch per each release """
        ch_dir = self.git_root
        if self.relative_project_dir != "/":
            ch_dir = os.path.join(self.git_root,
                    self.relative_project_dir)
        os.chdir(ch_dir)
        debug("Running /usr/bin/generate-patches.pl -d %s %s %s-1 %s %s"
               % (self.rpmbuild_gitcopy, self.project_name, self.upstream_version, self.build_version, self.git_commit_id))
        output = run_command("/usr/bin/generate-patches.pl -d %s %s %s-1 %s %s"
               % (self.rpmbuild_gitcopy, self.project_name, self.upstream_version, self.build_version, self.git_commit_id))
        self.patch_files = output.split("\n")
        for p_file in self.patch_files:
            (status, output) = getstatusoutput(
                "grep 'Binary files .* differ' %s/%s " % (self.rpmbuild_gitcopy, p_file))
            if status == 0 and output != "":
                error_out("You are doomed. Diff contains binary files. You can not use this builder")

            run_command("cp %s/%s %s" % (self.rpmbuild_gitcopy, p_file, self.rpmbuild_sourcedir))

        (patch_number, patch_insert_index, patch_apply_index, lines) = self._patch_upstream()

        for patch in self.patch_files:
            lines.insert(patch_insert_index, "Patch%s: %s\n" % (patch_number, patch))
            lines.insert(patch_apply_index, "%%patch%s -p1\n" % (patch_number))
            patch_number += 1
            patch_insert_index += 1
            patch_apply_index += 2
        self._write_spec(lines)

########NEW FILE########
__FILENAME__ = exception
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

"""
Tito Exceptions
"""


class TitoException(Exception):
    """
    Base Tito exception.

    Does nothing but indicate that this is a custom Tito error.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "TitoException: %s" % self.message


class RunCommandException(Exception):
    """ Raised by run_command() """
    def __init__(self, command, status, output):
        Exception.__init__(self, "Error running command: %s" % command)
        self.command = command
        self.status = status
        self.output = output

########NEW FILE########
__FILENAME__ = copr
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import os.path

from tito.common import run_command
from tito.release import KojiReleaser


class CoprReleaser(KojiReleaser):
    """ Releaser for Copr using copr-cli command """

    REQUIRED_CONFIG = ['project_name', 'upload_command', 'remote_location']
    cli_tool = "copr-cli"
    NAME = "Copr"

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):
        KojiReleaser.__init__(self, name, tag, build_dir, config,
                user_config, target, releaser_config, no_cleanup, test,
                auto_accept, **kwargs)

        self.copr_project_name = \
            self.releaser_config.get(self.target, "project_name")
        self.srpm_submitted = False

    def autobuild_tags(self):
        """ will return list of project for which we are building """
        result = self.releaser_config.get(self.target, "project_name")
        return result.strip().split(" ")

    def _koji_release(self):
        self.srpm_submitted = False
        if not self.builder.config.has_section(self.copr_project_name):
            self.builder.config.add_section(self.copr_project_name)
        KojiReleaser._koji_release(self)

    def _submit_build(self, executable, koji_opts, tag, srpm_location):
        """ Copy srpm to remote destination and submit it to Copr """
        cmd = self.releaser_config.get(self.target, "upload_command")
        url = self.releaser_config.get(self.target, "remote_location")
        if self.srpm_submitted:
            srpm_location = self.srpm_submitted
        srpm_base_name = os.path.basename(srpm_location)

        # e.g. "scp %(srpm)s my.web.com:public_html/my_srpm/"
        cmd_upload = cmd % {'srpm': srpm_location}
        cmd_submit = "/usr/bin/copr-cli build %s %s%s" % (self.releaser_config.get(self.target, "project_name"),
            url, srpm_base_name)

        if self.dry_run:
            self.print_dry_run_warning(cmd_upload)
            self.print_dry_run_warning(cmd_submit)
            return
        # TODO: no error handling when run_command fails:
        if not self.srpm_submitted:
            print("Uploading src.rpm.")
            print(run_command(cmd_upload))
            self.srpm_submitted = srpm_location
        print("Submiting build into %s." % self.NAME)
        print(run_command(cmd_submit))

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Code for submitting builds for release.
"""

import copy
import os
import sys
import tempfile
import subprocess
import rpm

from tempfile import mkdtemp
import shutil

from tito.common import *
from tito.compat import *
from tito.buildparser import BuildTargetParser
from tito.exception import TitoException
from tito.config_object import ConfigObject

DEFAULT_KOJI_OPTS = "build --nowait"

# List of files to protect when syncing:
PROTECTED_BUILD_SYS_FILES = ('branch', 'Makefile', 'sources', ".git", ".gitignore", ".osc")

RSYNC_USERNAME = 'RSYNC_USERNAME'  # environment variable name


def extract_task_info(output):
    """ Extracts task ID and URL from koji/brew build output. """
    task_lines = []
    for line in output.splitlines():
        if "Created task" in line:
            task_lines.append(line)
        elif "Task info" in line:
            task_lines.append(line)
    return task_lines


class Releaser(ConfigObject):
    """
    Parent class of all releasers.

    Can't really be used by itself, need to use one of the sub-classes.
    """
    GLOBAL_REQUIRED_CONFIG = ['releaser']
    REQUIRED_CONFIG = []
    OPTIONAL_CONFIG = []

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):

        ConfigObject.__init__(self, config=config)
        config_builder_args = self._parse_builder_args(releaser_config, target)
        if test:
            config_builder_args['test'] = True  # builder must know to build from HEAD

        # Override with builder args from command line if any were given:
        if 'builder_args' in kwargs:
            # (in case of dupes, last one wins)
            self.builder_args = dictionary_override(
                config_builder_args,
                kwargs['builder_args']
            )
        else:
            self.builder_args = config_builder_args

        # While we create a builder here, we don't actually call run on it
        # unless the releaser needs to:
        self.offline = False
        if 'offline' in kwargs:
            self.offline = kwargs['offline']
        self.builder = create_builder(name, tag,
                config,
                build_dir, user_config, self.builder_args, offline=self.offline)
        self.project_name = self.builder.project_name

        self.working_dir = mkdtemp(dir=self.builder.rpmbuild_basedir,
                prefix="release-%s" % self.builder.project_name)
        print("Working in: %s" % self.working_dir)

        # Config for all releasers:
        self.releaser_config = releaser_config

        # The actual release target we're building:
        self.target = target

        self.dry_run = False
        self.test = test  # releaser must know to use builder designation rather than tag
        self.auto_accept = auto_accept  # don't ask for input, just go ahead
        self.no_cleanup = no_cleanup

        self._check_releaser_config()

    def _ask_yes_no(self, prompt="Y/N? ", default_auto_answer=True):
        if self.auto_accept:
            return default_auto_answer
        else:
            answer = raw_input(prompt)
            return answer.lower() in ['y', 'yes', 'ok', 'sure']

    def _check_releaser_config(self):
        """
        Verify this release target has all the config options it needs.
        """
        for opt in self.GLOBAL_REQUIRED_CONFIG:
            if not self.releaser_config.has_option(self.target, opt):
                raise TitoException(
                    "Release target '%s' missing required option '%s'" %
                    (self.target, opt))
        for opt in self.REQUIRED_CONFIG:
            if not self.releaser_config.has_option(self.target, opt):
                raise TitoException(
                    "Release target '%s' missing required option '%s'" %
                    (self.target, opt))

        # TODO: accomodate 'builder.*' for yum releaser and we can use this:
        # for opt in self.releaser_config.options(self.target):
        #    if opt not in self.GLOBAL_REQUIRED_CONFIG and \
        #            opt not in self.REQUIRED_CONFIG and \
        #            opt not in self.OPTIONAL_CONFIG:
        #        raise TitoException(
        #                "Release target '%s' has unknown option '%s'" %
        #                (self.target, opt))

    def _parse_builder_args(self, releaser_config, target):
        """
        Any properties found in a releaser target section starting with
        "builder." are assumed to be builder arguments.

        i.e.:

        builder.mock = epel-6-x86_64

        Would indicate that we need to pass an argument "mock" to whatever
        builder is configured.
        """
        args = {}
        for opt in releaser_config.options(target):
            if opt.startswith("builder."):
                args[opt[len("builder."):]] = releaser_config.get(target, opt)
        debug("Parsed custom builder args: %s" % args)
        return args

    def release(self, dry_run=False, no_build=False, scratch=False):
        pass

    def cleanup(self):
        if not self.no_cleanup:
            debug("Cleaning up [%s]" % self.working_dir)
            run_command("rm -rf %s" % self.working_dir)

            if self.builder:
                self.builder.cleanup()
        else:
            print("WARNING: leaving %s (--no-cleanup)" % self.working_dir)

    def print_dry_run_warning(self, command_that_would_be_run_otherwise):
        print
        print("WARNING: Skipping command due to --dry-run: %s" %
                command_that_would_be_run_otherwise)
        print

    def _sync_files(self, files_to_copy, dest_dir):
        debug("Copying files: %s" % files_to_copy)
        debug("   to: %s" % dest_dir)
        os.chdir(dest_dir)

        # Need a list of just the filenames for a set comparison later:
        filenames_to_copy = []
        for filename in files_to_copy:
            filenames_to_copy.append(os.path.basename(filename))

        # Base filename for entirely new files:
        new_files = []

        # Base filenames for pre-existing files we copied over:
        copied_files = []

        # Base filenames that need to be removed by the caller:
        old_files = []

        for copy_me in files_to_copy:
            base_filename = os.path.basename(copy_me)
            dest_path = os.path.join(dest_dir, base_filename)

            if not os.path.exists(dest_path):
                print("   adding: %s" % base_filename)
                new_files.append(base_filename)
            else:
                print("   copying: %s" % base_filename)
                copied_files.append(base_filename)

            cmd = "cp %s %s" % (copy_me, dest_path)
            run_command(cmd)

        # Track filenames that will need to be deleted by the caller.
        for filename in os.listdir(dest_dir):
            if filename not in PROTECTED_BUILD_SYS_FILES and \
                    filename not in filenames_to_copy:
                print("   deleting: %s" % filename)
                old_files.append(filename)

        return new_files, copied_files, old_files


class RsyncReleaser(Releaser):
    """
    A releaser which will rsync from a remote host, build the desired packages,
    plug them in, and upload to server.

    Building of the packages is done via mock.

    WARNING: This will not work in all
    situations, depending on the current OS, and the mock target you
    are attempting to use.
    """
    REQUIRED_CONFIG = ['rsync', 'builder']

    # Default list of packages to copy
    filetypes = ['rpm', 'srpm', 'tgz']

    # By default run rsync with these paramaters
    rsync_args = "-rlvz"

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False,
            prefix="temp_dir=", **kwargs):
        Releaser.__init__(self, name, tag, build_dir, config,
                user_config, target, releaser_config, no_cleanup, test,
                auto_accept, **kwargs)

        self.build_dir = build_dir
        self.prefix = prefix

        # Use the builder from the release target, rather than the default
        # one defined for this git repo or sub-package:
        # TODO: this is a little sketchy, creating two builders?
        self.builder = create_builder(name, tag,
                config,
                build_dir, user_config, self.builder_args,
                builder_class=self.releaser_config.get(self.target, 'builder'),
                offline=self.offline)
        if self.releaser_config.has_option(self.target, "scl"):
            sys.stderr.write("WARNING: please rename 'scl' to "
                "'builder.scl' in releasers.conf\n")
            self.builder.scl = self.releaser_config.get(self.target, "scl")

    def release(self, dry_run=False, no_build=False, scratch=False):
        self.dry_run = dry_run

        # Should this run?
        self.builder.no_cleanup = self.no_cleanup
        self.builder.tgz()
        self.builder.srpm()
        self.builder.rpm()
        self.builder.cleanup()

        if self.releaser_config.has_option(self.target, 'rsync_args'):
            self.rsync_args = self.releaser_config.get(self.target, 'rsync_args')

        rsync_locations = self.releaser_config.get(self.target, 'rsync').split(" ")
        for rsync_location in rsync_locations:
            if RSYNC_USERNAME in os.environ:
                print("%s set, using rsync username: %s" % (RSYNC_USERNAME,
                        os.environ[RSYNC_USERNAME]))
                rsync_location = "%s@%s" % (os.environ[RSYNC_USERNAME], rsync_location)

            # Make a temp directory to sync the existing repo contents into:
            temp_dir = mkdtemp(dir=self.build_dir, prefix=self.prefix)

            self._rsync_from_remote(self.rsync_args, rsync_location, temp_dir)
            self._copy_files_to_temp_dir(temp_dir)
            self.process_packages(temp_dir)
            self.rsync_to_remote(self.rsync_args, temp_dir, rsync_location)

    def _rsync_from_remote(self, rsync_args, rsync_location, temp_dir):
        os.chdir(temp_dir)
        print("rsync %s %s %s" % (rsync_args, rsync_location, temp_dir))
        output = run_command("rsync %s %s %s" % (rsync_args, rsync_location, temp_dir))
        debug(output)

    def rsync_to_remote(self, rsync_args, temp_dir, rsync_location):
        print("rsync %s --delete %s/ %s" % (rsync_args, temp_dir, rsync_location))
        os.chdir(temp_dir)
        # TODO: configurable rsync options?
        cmd = "rsync %s --delete %s/ %s" % (rsync_args, temp_dir, rsync_location)
        if self.dry_run:
            self.print_dry_run_warning(cmd)
        else:
            output = run_command(cmd)
            debug(output)
        if not self.no_cleanup:
            debug("Cleaning up [%s]" % temp_dir)
            os.chdir("/")
            shutil.rmtree(temp_dir)
        else:
            print("WARNING: leaving %s (--no-cleanup)" % temp_dir)

    def _copy_files_to_temp_dir(self, temp_dir):
        os.chdir(temp_dir)

        # overwrite default self.filetypes if filetypes option is specified in config
        if self.releaser_config.has_option(self.target, 'filetypes'):
            self.filetypes = self.releaser_config.get(self.target, 'filetypes').split(" ")

        for artifact in self.builder.artifacts:
            if artifact.endswith('.tar.gz'):
                artifact_type = 'tgz'
            elif artifact.endswith('src.rpm'):
                artifact_type = 'srpm'
            elif artifact.endswith('.rpm'):
                artifact_type = 'rpm'
            else:
                continue

            if artifact_type in self.filetypes:
                print("copy: %s > %s" % (artifact, temp_dir))
                shutil.copy(artifact, temp_dir)

    def process_packages(self, temp_dir):
        """ no-op. This will be overloaded by a subclass if needed. """
        pass

    def cleanup(self):
        """ No-op, we clean up during self.release() """
        pass


class YumRepoReleaser(RsyncReleaser):
    """
    A releaser which will rsync down a yum repo, build the desired packages,
    plug them in, update the repodata, and push the yum repo back out.

    Building of the packages is done via mock.

    WARNING: This will not work in all
    situations, depending on the current OS, and the mock target you
    are attempting to use.
    """

    # Default list of packages to copy
    filetypes = ['rpm']

    # By default run createrepo without any paramaters
    createrepo_command = "createrepo ."

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):
        RsyncReleaser.__init__(self, name, tag, build_dir, config,
                user_config, target, releaser_config, no_cleanup, test, auto_accept,
                prefix="yumrepo-", **kwargs)

    def _read_rpm_header(self, ts, new_rpm_path):
        """
        Read RPM header for the given file.
        """
        fd = os.open(new_rpm_path, os.O_RDONLY)
        header = ts.hdrFromFdno(fd)
        os.close(fd)
        return header

    def process_packages(self, temp_dir):
        self.prune_other_versions(temp_dir)
        print("Refreshing yum repodata...")
        if self.releaser_config.has_option(self.target, 'createrepo_command'):
            self.createrepo_command = self.releaser_config.get(self.target, 'createrepo_command')
        os.chdir(temp_dir)
        output = run_command(self.createrepo_command)
        debug(output)

    def prune_other_versions(self, temp_dir):
        """
        Cleanout any other version of the package we just built.

        Both older and newer packages will be removed (can be used
        to downgrade the contents of a yum repo).
        """
        os.chdir(temp_dir)
        rpm_ts = rpm.TransactionSet()
        self.new_rpm_dep_sets = {}
        for artifact in self.builder.artifacts:
            if artifact.endswith(".rpm") and not artifact.endswith(".src.rpm"):
                try:
                    header = self._read_rpm_header(rpm_ts, artifact)
                except rpm.error:
                    continue
                self.new_rpm_dep_sets[header['name']] = header.dsOfHeader()

        # Now cleanout any other version of the package we just built,
        # both older or newer. (can be used to downgrade the contents
        # of a yum repo)
        for filename in os.listdir(temp_dir):
            if not filename.endswith(".rpm"):
                continue
            full_path = os.path.join(temp_dir, filename)
            try:
                hdr = self._read_rpm_header(rpm_ts, full_path)
            except rpm.error:
                e = sys.exc_info()[1]
                print("error reading rpm header in '%s': %s" % (full_path, e))
                continue
            if hdr['name'] in self.new_rpm_dep_sets:
                dep_set = hdr.dsOfHeader()
                if dep_set.EVR() < self.new_rpm_dep_sets[hdr['name']].EVR():
                    print("Deleting old package: %s" % filename)
                    run_command("rm %s" % os.path.join(temp_dir,
                        filename))


class FedoraGitReleaser(Releaser):

    REQUIRED_CONFIG = ['branches']
    cli_tool = "fedpkg"

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):
        Releaser.__init__(self, name, tag, build_dir, config,
                user_config, target, releaser_config, no_cleanup, test,
                auto_accept, **kwargs)

        self.git_branches = \
            self.releaser_config.get(self.target, "branches").split(" ")

        if self.config.has_option(self.target, "remote_git_name"):
            overwrite_checkout = self.config.get(self.target, "remote_git_name")
        else:
            overwrite_checkout = None
        if overwrite_checkout:
            self.project_name = overwrite_checkout

        self.package_workdir = os.path.join(self.working_dir,
                self.project_name)

        build_target_parser = BuildTargetParser(self.releaser_config, self.target,
                                                self.git_branches)
        self.build_targets = build_target_parser.get_build_targets()

        # Files we should copy to git during a release:
        self.copy_extensions = (".spec", ".patch")

    def release(self, dry_run=False, no_build=False, scratch=False):
        self.dry_run = dry_run
        self.no_build = no_build
        self._git_release()

    def _get_build_target_for_branch(self, branch):
        if branch in self.build_targets:
            return self.build_targets[branch]
        return None

    def _git_release(self):

        getoutput("mkdir -p %s" % self.working_dir)
        os.chdir(self.working_dir)
        run_command("%s clone %s" % (self.cli_tool, self.project_name))

        project_checkout = os.path.join(self.working_dir, self.project_name)
        os.chdir(project_checkout)
        run_command("%s switch-branch %s" % (self.cli_tool, self.git_branches[0]))

        self.builder.tgz()
        if self.test:
            self.builder._setup_test_specfile()

        self._git_sync_files(project_checkout)
        self._git_upload_sources(project_checkout)
        self._git_user_confirm_commit(project_checkout)

    def _confirm_commit_msg(self, diff_output):
        """
        Generates a commit message in a temporary file, gives the user a
        chance to edit it, and returns the filename to the caller.
        """

        fd, name = tempfile.mkstemp()
        debug("Storing commit message in temp file: %s" % name)
        write(fd, "Update %s to %s\n" % (self.project_name,
            self.builder.build_version))
        # Write out Resolves line for all bugzillas we see in commit diff:
        for line in extract_bzs(diff_output):
            write(fd, line + "\n")

        print("")
        print("##### Commit message: #####")
        print("")

        os.lseek(fd, 0, 0)
        file = os.fdopen(fd)
        for line in file.readlines():
            print(line)
        file.close()

        print("")
        print("###############################")
        print("")
        if self._ask_yes_no("Would you like to edit this commit message? [y/n] ", False):
            debug("Opening editor for user to edit commit message in: %s" % name)
            editor = 'vi'
            if "EDITOR" in os.environ:
                editor = os.environ["EDITOR"]
            subprocess.call(editor.split() + [name])

        return name

    def _git_user_confirm_commit(self, project_checkout):
        """ Prompt user if they wish to proceed with commit. """
        print("")
        text = "Running 'git diff' in: %s" % project_checkout
        print("#" * len(text))
        print(text)
        print("#" * len(text))
        print("")

        main_branch = self.git_branches[0]

        os.chdir(project_checkout)

        # Newer versions of git don't seem to want --cached here? Try both:
        (status, diff_output) = getstatusoutput("git diff --cached")
        if diff_output.strip() == "":
            debug("git diff --cached returned nothing, falling back to git diff.")
            (status, diff_output) = getstatusoutput("git diff")

        if diff_output.strip() == "":
            print("No changes in main branch, skipping commit for: %s" % main_branch)
        else:
            print(diff_output)
            print("")
            print("##### Please review the above diff #####")
            if not self._ask_yes_no("Do you wish to proceed with commit? [y/n] "):
                print("Fine, you're on your own!")
                self.cleanup()
                sys.exit(1)

            print("Proceeding with commit.")
            commit_msg_file = self._confirm_commit_msg(diff_output)
            cmd = '%s commit -F %s' % (self.cli_tool,
                    commit_msg_file)
            debug("git commit command: %s" % cmd)
            print
            if self.dry_run:
                self.print_dry_run_warning(cmd)
            else:
                print("Proceeding with commit.")
                os.chdir(self.package_workdir)
                output = run_command(cmd)

            os.unlink(commit_msg_file)

        cmd = "%s push" % self.cli_tool
        if self.dry_run:
            self.print_dry_run_warning(cmd)
        else:
            # Push
            print(cmd)
            run_command(cmd)

        if not self.no_build:
            self._build(main_branch)

        for branch in self.git_branches[1:]:
            print("Merging branch: '%s' -> '%s'" % (main_branch, branch))
            run_command("%s switch-branch %s" % (self.cli_tool, branch))
            self._merge(main_branch)

            cmd = "git push origin %s:%s" % (branch, branch)
            if self.dry_run:
                self.print_dry_run_warning(cmd)
            else:
                print(cmd)
                run_command(cmd)

            if not self.no_build:
                self._build(branch)

            print

    def _merge(self, main_branch):
        try:
            run_command("git merge %s" % main_branch)
        except:
            print
            print("WARNING!!! Conflicts occurred during merge.")
            print
            print("You are being dropped to a shell in the working directory.")
            print
            print("Please resolve this by doing the following:")
            print
            print("  1. List the conflicting files: git ls-files --unmerged")
            print("  2. Edit each resolving the conflict and then: git add FILENAME")
            print("  4. Commit the result when you are done: git commit")
            print("  4. Return to the tito release: exit")
            print
            # TODO: maybe prompt y/n here
            os.system(os.environ['SHELL'])

    def _build(self, branch):
        """ Submit a Fedora build from current directory. """
        target_param = ""
        build_target = self._get_build_target_for_branch(branch)
        if build_target:
            target_param = "--target %s" % build_target

        build_cmd = "%s build --nowait %s" % (self.cli_tool, target_param)

        if self.dry_run:
            self.print_dry_run_warning(build_cmd)
            return

        print("Submitting build: %s" % build_cmd)
        (status, output) = getstatusoutput(build_cmd)
        if status > 0:
            if "already been built" in output:
                print("Build has been submitted previously, continuing...")
            else:
                sys.stderr.write("ERROR: Unable to submit build.\n")
                sys.stderr.write("  Status code: %s\n" % status)
                sys.stderr.write("  Output: %s\n" % output)
                sys.exit(1)

        # Print the task ID and URL:
        for line in extract_task_info(output):
            print(line)

    def _git_upload_sources(self, project_checkout):
        """
        Upload any tarballs to the lookaside directory. (if necessary)
        Uses the "fedpkg new-sources" command.
        """
        if not self.builder.sources:
            debug("No sources need to be uploaded.")
            return

        print("Uploading sources to lookaside:")
        os.chdir(project_checkout)
        cmd = '%s new-sources %s' % (self.cli_tool, " ".join(self.builder.sources))
        debug(cmd)

        if self.dry_run:
            self.print_dry_run_warning(cmd)
            return

        output = run_command(cmd)
        debug(output)
        debug("Removing write-only permission on:")
        for filename in self.builder.sources:
            run_command("chmod u+w %s" % filename)

    def _list_files_to_copy(self):
        """
        Returns a list of the full file paths for each file that should be
        copied from our git project into the build system checkout. This
        is used to sync files to git during a release.

        i.e. spec file, .patches.

        It is assumed that any file found in the build system checkout
        but not in this list, and not in the protected files list, should
        probably be cleaned up.
        """
        # Include the spec file explicitly, in the case of SatelliteBuilder
        # we modify and then use a spec file copy from a different location.
        files_to_copy = [self.builder.spec_file]  # full paths

        f = open(self.builder.spec_file, 'r')
        lines = f.readlines()
        f.close()
        source_filenames = extract_sources(lines)
        debug("Watching for source filenames: %s" % source_filenames)

        for filename in os.listdir(self.builder.rpmbuild_gitcopy):
            full_filepath = os.path.join(self.builder.rpmbuild_gitcopy, filename)
            if os.path.isdir(full_filepath):
                # skip it
                continue
            if filename in PROTECTED_BUILD_SYS_FILES:
                debug("   skipping:  %s (protected file)" % filename)
                continue
            elif filename.endswith(".spec"):
                # Skip the spec file, we already copy this explicitly as it
                # can come from a couple different locations depending on which
                # builder is in use.
                continue

            # Check if file looks like it matches a Source line in the spec file:
            if filename in source_filenames:
                debug("   copying:   %s" % filename)
                files_to_copy.append(full_filepath)
                continue

            # Check if file ends with something this builder subclass wants
            # to copy:
            copy_it = False
            for extension in self.copy_extensions:
                if filename.endswith(extension):
                    copy_it = True
                    continue
            if copy_it:
                debug("   copying:   %s" % filename)
                files_to_copy.append(full_filepath)

        return files_to_copy

    def _git_sync_files(self, project_checkout):
        """
        Copy files from our git into each git build branch and add them.

        A list of safe files is used to protect critical files both from
        being overwritten by a git file of the same name, as well as being
        deleted after.
        """

        # Build the list of all files we will copy:
        debug("Searching for files to copy to build system git:")
        files_to_copy = self._list_files_to_copy()

        os.chdir(project_checkout)

        new, copied, old =  \
                self._sync_files(files_to_copy, project_checkout)

        os.chdir(project_checkout)

        # Git add everything:
        for add_file in (new + copied):
            run_command("git add %s" % add_file)

        # Cleanup obsolete files:
        for cleanup_file in old:
            # Can't delete via full path, must not chdir:
            run_command("git rm %s" % cleanup_file)


class DistGitReleaser(FedoraGitReleaser):
    cli_tool = "rhpkg"


class KojiReleaser(Releaser):
    """
    Releaser for the Koji build system.

    WARNING: this is more of use to people running their own Koji instance.
    Fedora projects will most likely want to use the Fedora git releaser.
    """

    REQUIRED_CONFIG = ['autobuild_tags']
    NAME = "Koji"

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):
        Releaser.__init__(self, name, tag, build_dir, config,
                user_config, target, releaser_config, no_cleanup, test, auto_accept,
                **kwargs)

        self.only_tags = []
        if 'ONLY_TAGS' in os.environ:
            self.only_tags = os.environ['ONLY_TAGS'].split(' ')

        self.skip_srpm = False

    def release(self, dry_run=False, no_build=False, scratch=False):
        self.dry_run = dry_run
        self.scratch = scratch

        self._koji_release()

    def autobuild_tags(self):
        """ will return list of tags for which we are building """
        result = self.releaser_config.get(self.target, "autobuild_tags")
        return result.strip().split(" ")

    def _koji_release(self):
        """
        Lookup autobuild Koji tags from global config, create srpms with
        appropriate disttags, and submit builds to Koji.
        """
        koji_tags = self.autobuild_tags()
        print("Building release in %s..." % self.NAME)
        debug("%s tags: %s" % (self.NAME, koji_tags))

        koji_opts = DEFAULT_KOJI_OPTS
        if 'KOJI_OPTIONS' in self.builder.user_config:
            koji_opts = self.builder.user_config['KOJI_OPTIONS']

        if self.scratch or ('SCRATCH' in os.environ and os.environ['SCRATCH'] == '1'):
            koji_opts = ' '.join([koji_opts, '--scratch'])

        # TODO: need to re-do this metaphor to use release targets instead:
        for koji_tag in koji_tags:
            if self.only_tags and koji_tag not in self.only_tags:
                continue
            scl = None
            if self.builder.config.has_option(koji_tag, "scl"):
                scl = self.builder.config.get(koji_tag, "scl")
            # Lookup the disttag configured for this Koji tag:
            if self.builder.config.has_option(koji_tag, "disttag"):
                disttag = self.builder.config.get(koji_tag, "disttag")
            else:
                disttag = ''
            if self.builder.config.has_option(koji_tag, "whitelist"):
                # whitelist implies only those packages can be built to the
                # tag,regardless if blacklist is also defined.
                if not self.__is_whitelisted(koji_tag, scl):
                    print("WARNING: %s not specified in whitelist for %s" % (
                        self.project_name, koji_tag))
                    print("   Package *NOT* submitted to %s." % self.NAME)
                    continue
            elif self.__is_blacklisted(koji_tag, scl):
                print("WARNING: %s specified in blacklist for %s" % (
                    self.project_name, koji_tag))
                print("   Package *NOT* submitted to %s." % self.NAME)
                continue

            # Getting tricky here, normally Builder's are only used to
            # create one rpm and then exit. Here we're going to try
            # to run multiple srpm builds:
            builder = self.builder
            if not self.skip_srpm:
                if scl:
                    builder = copy.copy(self.builder)
                    builder.scl = scl
                builder.srpm(dist=disttag)

            self._submit_build("koji", koji_opts, koji_tag, builder.srpm_location)

    def __is_whitelisted(self, koji_tag, scl):
        """ Return true if package is whitelisted in tito.props"""
        return self.builder.config.has_option(koji_tag, "whitelist") and \
            get_project_name(self.builder.build_tag, scl) in self.builder.config.get(koji_tag,
                        "whitelist").strip().split()

    def __is_blacklisted(self, koji_tag, scl):
        """ Return true if package is blacklisted in tito.props"""
        return self.builder.config.has_option(koji_tag, "blacklist") and \
            get_project_name(self.builder.build_tag, scl) in self.builder.config.get(koji_tag,
                        "blacklist").strip().split()

    def _submit_build(self, executable, koji_opts, tag, srpm_location):
        """ Submit srpm to brew/koji. """
        cmd = "%s %s %s %s" % (executable, koji_opts, tag, srpm_location)
        print("\nSubmitting build with: %s" % cmd)

        if self.dry_run:
            self.print_dry_run_warning(cmd)
            return

        output = run_command(cmd)
        print(output)


class KojiGitReleaser(KojiReleaser):
    """
    A derivative of the Koji releaser which uses a git repository to build off,
    rather than submitting srpms.
    """

    REQUIRED_CONFIG = ['autobuild_tags', 'git_url']

    def _koji_release(self):
        self.skip_srpm = True
        KojiReleaser._koji_release(self)

    def _submit_build(self, executable, koji_opts, tag, srpm_location):
        """
        Submit build to koji using the git URL from config. We will ignore
        srpm_location here.

        NOTE: overrides KojiReleaser._submit_build.
        """
        cmd = "%s %s %s %s/#%s" % \
                (executable, koji_opts, tag,
                        self.releaser_config.get(self.target, 'git_url'),
                        self.builder.build_tag)
        print("\nSubmitting build with: %s" % cmd)

        if self.dry_run:
            self.print_dry_run_warning(cmd)
            return

        output = run_command(cmd)
        print(output)

########NEW FILE########
__FILENAME__ = obs
# Copyright (c) 2008-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import tempfile
import subprocess
import sys

from tito.common import run_command, debug, extract_bzs
from tito.compat import *
from tito.release import Releaser


class ObsReleaser(Releaser):
    """ Releaser for Open Build System using osc command """

    REQUIRED_CONFIG = ['project_name']
    cli_tool = "osc"

    def __init__(self, name=None, tag=None, build_dir=None,
            config=None, user_config=None,
            target=None, releaser_config=None, no_cleanup=False,
            test=False, auto_accept=False, **kwargs):
        Releaser.__init__(self, name, tag, build_dir,
                user_config, target, releaser_config, no_cleanup, test, auto_accept)

        self.obs_project_name = \
            self.releaser_config.get(self.target, "project_name")

        if self.config.has_option(self.target, "package_name"):
            self.obs_package_name = self.config.get(self.target, "package_name")
        else:
            self.obs_package_name = self.project_name

        self.package_workdir = os.path.join(self.working_dir, self.obs_project_name,
                self.project_name)

    def release(self, dry_run=False, no_build=False, scratch=False):
        self.dry_run = dry_run
        self.no_build = no_build

        getoutput("mkdir -p %s" % self.working_dir)
        os.chdir(self.working_dir)
        run_command("%s co %s %s" % (self.cli_tool, self.obs_project_name, self.obs_package_name))

        os.chdir(self.package_workdir)

        self.builder.tgz()
        if self.test:
            self.builder._setup_test_specfile()

        self._obs_sync_files(self.package_workdir)
        self._obs_user_confirm_commit(self.package_workdir)

    def _confirm_commit_msg(self, diff_output):
        """
        Generates a commit message in a temporary file, gives the user a
        chance to edit it, and returns the filename to the caller.
        """

        fd, name = tempfile.mkstemp()
        debug("Storing commit message in temp file: %s" % name)
        write(fd, "Update %s to %s\n" % (self.obs_package_name,
            self.builder.build_version))
        # Write out Resolves line for all bugzillas we see in commit diff:
        for line in extract_bzs(diff_output):
            write(fd, line + "\n")

        print("")
        print("##### Commit message: #####")
        print("")

        os.lseek(fd, 0, 0)
        commit_file = os.fdopen(fd)
        for line in commit_file.readlines():
            print(line)
        commit_file.close()

        print("")
        print("###############################")
        print("")
        if self._ask_yes_no("Would you like to edit this commit message? [y/n] ", False):
            debug("Opening editor for user to edit commit message in: %s" % name)
            editor = 'vi'
            if "EDITOR" in os.environ:
                editor = os.environ["EDITOR"]
            subprocess.call(editor.split() + [name])

        return name

    def _obs_user_confirm_commit(self, project_checkout):
        """ Prompt user if they wish to proceed with commit. """
        print("")
        text = "Running '%s diff' in: %s" % (self.cli_tool, project_checkout)
        print("#" * len(text))
        print(text)
        print("#" * len(text))
        print("")

        os.chdir(project_checkout)

        (status, diff_output) = getstatusoutput("%s diff" % self.cli_tool)

        if diff_output.strip() == "":
            print("No changes in main branch, skipping commit.")
        else:
            print(diff_output)
            print("")
            print("##### Please review the above diff #####")
            if not self._ask_yes_no("Do you wish to proceed with commit? [y/n] "):
                print("Fine, you're on your own!")
                self.cleanup()
                sys.exit(1)

            print("Proceeding with commit.")
            commit_msg_file = self._confirm_commit_msg(diff_output)
            cmd = '%s commit -F %s' % (self.cli_tool,
                    commit_msg_file)
            debug("obs commit command: %s" % cmd)
            print
            if self.dry_run:
                self.print_dry_run_warning(cmd)
            else:
                print("Proceeding with commit.")
                os.chdir(self.package_workdir)
                print(run_command(cmd))

            os.unlink(commit_msg_file)

        if self.no_build:
            getstatusoutput("%s abortbuild %s %s" % (
                self.cli_tool, self.obs_project_name, self.obs_package_name))
            print("Aborting automatic rebuild because --no-build has been specified.")

    def _obs_sync_files(self, project_checkout):
        """
        Copy files from our obs checkout into each obs checkout and add them.

        A list of safe files is used to protect critical files both from
        being overwritten by a osc file of the same name, as well as being
        deleted after.
        """

        # Build the list of all files we will copy:
        debug("Searching for files to copy to build system osc checkout:")
        files_to_copy = self._list_files_to_copy()

        os.chdir(project_checkout)

        self._sync_files(files_to_copy, project_checkout)

        os.chdir(project_checkout)

        # Add/remove everything:
        run_command("%s addremove" % (self.cli_tool))

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2008-2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Code for tagging Spacewalk/Satellite packages.
"""

import os
import re
import rpm
import shutil
import subprocess
import tempfile
import textwrap
import sys

from string import Template

from time import strftime

from tito.common import (debug, error_out, run_command,
        find_spec_file, get_project_name, get_latest_tagged_version,
        get_spec_version_and_release, replace_version,
        tag_exists_locally, tag_exists_remotely, head_points_to_tag, undo_tag,
        increase_version, reset_release, increase_zstream,
        BUILDCONFIG_SECTION, get_relative_project_dir_cwd)
from tito.compat import *
from tito.exception import TitoException
from tito.config_object import ConfigObject


class VersionTagger(ConfigObject):
    """
    Standard Tagger class, used for tagging packages built from source in
    git. (as opposed to packages which commit a tarball directly into git).

    Releases will be tagged by incrementing the package version,
    and the actual RPM "release" will always be set to 1.
    """

    def __init__(self, config=None, keep_version=False, offline=False, user_config=None):
        ConfigObject.__init__(self, config=config)
        self.user_config = user_config

        self.full_project_dir = os.getcwd()
        self.spec_file_name = find_spec_file()
        self.project_name = get_project_name(tag=None)

        self.relative_project_dir = get_relative_project_dir_cwd(
            self.git_root)  # i.e. java/

        self.spec_file = os.path.join(self.full_project_dir,
                self.spec_file_name)
        self.keep_version = keep_version

        self.today = strftime("%a %b %d %Y")
        (self.git_user, self.git_email) = self._get_git_user_info()
        git_email = self.git_email
        if git_email is None:
            git_email = ''
        self.changelog_regex = re.compile('\\*\s%s\s%s(\s<%s>)?' % (self.today,
            self.git_user, git_email.replace("+", "\+").replace(".", "\.")))

        self._no_auto_changelog = False
        self._accept_auto_changelog = False
        self._new_changelog_msg = "new package built with tito"
        self.offline = offline

    def run(self, options):
        """
        Perform the actions requested of the tagger.

        NOTE: this method may do nothing if the user requested no build actions
        be performed. (i.e. only release tagging, etc)
        """
        if options.tag_release:
            print("WARNING: --tag-release option no longer necessary,"
                " 'tito tag' will accomplish the same thing.")
        if options.no_auto_changelog:
            self._no_auto_changelog = True
        if options.accept_auto_changelog:
            self._accept_auto_changelog = True
        if options.auto_changelog_msg:
            self._new_changelog_msg = options.auto_changelog_msg
        if options.use_version:
            self._use_version = options.use_version

        self.check_tag_precondition()

        # Only two paths through the tagger module right now:
        if options.undo:
            self._undo()
        else:
            self._tag_release()

    def check_tag_precondition(self):
        if self.config.has_option("tagconfig", "require_package"):
            packages = self.config.get("tagconfig", "require_package").split(',')
            ts = rpm.TransactionSet()
            missing_packages = []
            for p in packages:
                p = p.strip()
                mi = ts.dbMatch('name', p)
                if not mi:
                    missing_packages.append(p)
            if missing_packages:
                raise TitoException("To tag this package, you must first install: %s" %
                    ', '.join(missing_packages))

    def _tag_release(self):
        """
        Tag a new version of the package. (i.e. x.y.z+1)
        """
        self._make_changelog()
        new_version = self._bump_version()
        self._check_tag_does_not_exist(self._get_new_tag(new_version))
        self._update_changelog(new_version)
        self._update_setup_py(new_version)
        self._update_package_metadata(new_version)

    def _undo(self):
        """
        Undo the most recent tag.

        Tag commit must be the most recent commit, and the tag must not
        exist in the remote git repo, otherwise we report and error out.
        """
        tag = "%s-%s" % (self.project_name,
                get_latest_tagged_version(self.project_name))
        print("Undoing tag: %s" % tag)
        if not tag_exists_locally(tag):
            raise TitoException(
                "Cannot undo tag that does not exist locally.")
        if not self.offline and tag_exists_remotely(tag):
            raise TitoException("Cannot undo tag that has been pushed.")

        # Tag must be the most recent commit.
        if not head_points_to_tag(tag):
            raise TitoException("Cannot undo if tag is not the most recent commit.")

        # Everything looks good:
        print
        undo_tag(tag)

    def _changelog_remove_cherrypick(self, line):
        """
        remove text "(cherry picked from commit ..." from line unless
        changelog_do_not_remove_cherrypick is specified in [BUILDCONFIG_SECTION]
        """
        if not (self.config.has_option(BUILDCONFIG_SECTION, "changelog_do_not_remove_cherrypick")
            and self.config.get(BUILDCONFIG_SECTION, "changelog_do_not_remove_cherrypick")
            and self.config.get(BUILDCONFIG_SECTION, "changelog_do_not_remove_cherrypick").strip() != '0'):
            m = re.match("(.+)(\(cherry picked from .*\))", line)
            if m:
                line = m.group(1)
        return line

    def _changelog_format(self):
        """
        If you have set changelog_format in [BUILDCONFIG_SECTION], it will return
        that string.  Otherwise, return one of two defaults:

        - '%s (%ae)', if changelog_with_email is unset or evaluates to True
        - '%s', if changelog_with_email is set and evaluates to False
        """
        result = ''
        if self.config.has_option(BUILDCONFIG_SECTION, "changelog_format"):
            result = self.config.get(BUILDCONFIG_SECTION, "changelog_format")
        else:
            with_email = ''
            if (self.config.has_option(BUILDCONFIG_SECTION, "changelog_with_email")
                and (self.config.get(BUILDCONFIG_SECTION, "changelog_with_email")) not in ['0', '']) or \
                not self.config.has_option(BUILDCONFIG_SECTION, "changelog_with_email"):
                with_email = ' (%ae)'
            result = "%%s%s" % with_email
        return result

    def _generate_default_changelog(self, last_tag):
        """
        Run git-log and will generate changelog, which still can be edited by user
        in _make_changelog.
        """
        patch_command = "git log --pretty='format:%s'" \
                         " --relative %s..%s -- %s" % (self._changelog_format(), last_tag, "HEAD", ".")
        output = run_command(patch_command)
        result = []
        for line in output.split('\n'):
            line = line.replace('%', '%%')
            result.extend([self._changelog_remove_cherrypick(line)])
        return '\n'.join(result)

    def _make_changelog(self):
        """
        Create a new changelog entry in the spec, with line items from git
        """
        if self._no_auto_changelog:
            debug("Skipping changelog generation.")
            return

        in_f = open(self.spec_file, 'r')
        out_f = open(self.spec_file + ".new", 'w')

        found_changelog = False
        for line in in_f.readlines():
            out_f.write(line)

            if not found_changelog and line.startswith("%changelog"):
                found_changelog = True

                old_version = get_latest_tagged_version(self.project_name)

                # don't die if this is a new package with no history
                if old_version is not None:
                    last_tag = "%s-%s" % (self.project_name, old_version)
                    output = self._generate_default_changelog(last_tag)
                else:
                    output = self._new_changelog_msg

                fd, name = tempfile.mkstemp()
                write(fd, "# Create your changelog entry below:\n")
                if self.git_email is None or (('HIDE_EMAIL' in self.user_config) and
                        (self.user_config['HIDE_EMAIL'] not in ['0', ''])):
                    header = "* %s %s\n" % (self.today, self.git_user)
                else:
                    header = "* %s %s <%s>\n" % (self.today, self.git_user,
                       self.git_email)

                write(fd, header)

                for cmd_out in output.split("\n"):
                    write(fd, "- ")
                    write(fd, "\n  ".join(textwrap.wrap(cmd_out, 77)))
                    write(fd, "\n")

                write(fd, "\n")

                if not self._accept_auto_changelog:
                    # Give the user a chance to edit the generated changelog:
                    editor = 'vi'
                    if "EDITOR" in os.environ:
                        editor = os.environ["EDITOR"]
                    subprocess.call(editor.split() + [name])

                os.lseek(fd, 0, 0)
                file = os.fdopen(fd)

                for line in file.readlines():
                    if not line.startswith("#"):
                        out_f.write(line)

                output = file.read()

                file.close()
                os.unlink(name)

        if not found_changelog:
            print("WARNING: no %changelog section find in spec file. Changelog entry was not appended.")

        in_f.close()
        out_f.close()

        shutil.move(self.spec_file + ".new", self.spec_file)

    def _update_changelog(self, new_version):
        """
        Update the changelog with the new version.
        """
        # Not thrilled about having to re-read the file here but we need to
        # check for the changelog entry before making any modifications, then
        # bump the version, then update the changelog.
        f = open(self.spec_file, 'r')
        buf = StringIO()
        found_match = False
        for line in f.readlines():
            match = self.changelog_regex.match(line)
            if match and not found_match:
                buf.write("%s %s\n" % (match.group(), new_version))
                found_match = True
            else:
                buf.write(line)
        f.close()

        # Write out the new file contents with our modified changelog entry:
        f = open(self.spec_file, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()

    def _update_setup_py(self, new_version):
        """
        If this project has a setup.py, attempt to update it's version.
        """
        self._update_version_file(new_version)

        setup_file = os.path.join(self.full_project_dir, "setup.py")
        if not os.path.exists(setup_file):
            return

        debug("Found setup.py, attempting to update version.")

        # We probably don't want version-release in setup.py as release is
        # an rpm concept. Hopefully this assumption on
        py_new_version = new_version.split('-')[0]

        f = open(setup_file, 'r')
        buf = StringIO()
        for line in f.readlines():
            buf.write(replace_version(line, py_new_version))
        f.close()

        # Write out the new setup.py file contents:
        f = open(setup_file, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()

        run_command("git add %s" % setup_file)

    def _bump_version(self, release=False, zstream=False, force=False):
        """
        Bump up the package version in the spec file.

        Set release to True to bump the package release instead.

        Checks for the keep version option and if found, won't actually
        bump the version or release.
        """
        old_version = get_latest_tagged_version(self.project_name)
        if old_version is None:
            old_version = "untagged"
        if not self.keep_version:
            version_regex = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)
            release_regex = re.compile("^(release:\s*)(.+)$", re.IGNORECASE)

            in_f = open(self.spec_file, 'r')
            out_f = open(self.spec_file + ".new", 'w')

            for line in in_f.readlines():
                if release:
                    match = re.match(release_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        increase_version(match.group(2)),
                                        "\n"
                        ))
                elif zstream:
                    match = re.match(release_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        increase_zstream(match.group(2)),
                                        "\n"
                        ))
                elif force:
                    match = re.match(version_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        self._use_version,
                                        "\n"
                        ))

                    match = re.match(release_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        reset_release(match.group(2)),
                                        "\n"
                        ))
                else:
                    match = re.match(version_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        increase_version(match.group(2)),
                                        "\n"
                        ))

                    match = re.match(release_regex, line)
                    if match:
                        line = "".join((match.group(1),
                                        reset_release(match.group(2)),
                                        "\n"
                        ))

                out_f.write(line)

            in_f.close()
            out_f.close()
            shutil.move(self.spec_file + ".new", self.spec_file)

        new_version = get_spec_version_and_release(self.full_project_dir,
                self.spec_file_name)
        if new_version.strip() == "":
            msg = "Error getting bumped package version, try: \n"
            msg = msg + "  'rpm -q --specfile %s'" % self.spec_file
            error_out(msg)
        print("Tagging new version of %s: %s -> %s" % (self.project_name,
            old_version, new_version))
        return new_version

    def release_type(self):
        """ return short string which explain type of release.
            e.g. 'minor release
            Child classes probably want to override this.
        """
        return "release"

    def _update_package_metadata(self, new_version):
        """
        We track package metadata in the rel-eng/packages/ directory. Each
        file here stores the latest package version (for the git branch you
        are on) as well as the relative path to the project's code. (from the
        git root)
        """
        self._clear_package_metadata()

        suffix = ""
        # If global config specifies a tag suffix, use it:
        if self.config.has_option(BUILDCONFIG_SECTION, "tag_suffix"):
            suffix = self.config.get(BUILDCONFIG_SECTION, "tag_suffix")

        new_version_w_suffix = "%s%s" % (new_version, suffix)
        # Write out our package metadata:
        metadata_file = os.path.join(self.rel_eng_dir, "packages",
                self.project_name)
        f = open(metadata_file, 'w')
        f.write("%s %s\n" % (new_version_w_suffix, self.relative_project_dir))
        f.close()

        # Git add it (in case it's a new file):
        run_command("git add %s" % metadata_file)
        run_command("git add %s" % os.path.join(self.full_project_dir,
            self.spec_file_name))

        run_command('git commit -m "Automatic commit of package ' +
                '[%s] %s [%s]."' % (self.project_name, self.release_type(),
                    new_version_w_suffix))

        tag_msg = "Tagging package [%s] version [%s] in directory [%s]." % \
                (self.project_name, new_version_w_suffix,
                        self.relative_project_dir)

        new_tag = self._get_new_tag(new_version)
        run_command('git tag -m "%s" %s' % (tag_msg, new_tag))
        print
        print("Created tag: %s" % new_tag)
        print("   View: git show HEAD")
        print("   Undo: tito tag -u")
        print("   Push: git push && git push origin %s" % new_tag)

    def _check_tag_does_not_exist(self, new_tag):
        status, output = getstatusoutput(
            'git tag -l %s|grep ""' % new_tag)
        if status == 0:
            raise Exception("Tag %s already exists!" % new_tag)

    def _clear_package_metadata(self):
        """
        Remove all rel-eng/packages/ files that have a relative path
        matching the package we're tagging a new version of. Normally
        this just removes the previous package file but if we were
        renaming oldpackage to newpackage, this would git rm
        rel-eng/packages/oldpackage and add
        rel-eng/packages/spacewalk-newpackage.
        """
        metadata_dir = os.path.join(self.rel_eng_dir, "packages")
        for filename in os.listdir(metadata_dir):
            metadata_file = os.path.join(metadata_dir, filename)  # full path

            if os.path.isdir(metadata_file) or filename.startswith("."):
                continue

            temp_file = open(metadata_file, 'r')
            (version, relative_dir) = temp_file.readline().split(" ")
            relative_dir = relative_dir.strip()  # sometimes has a newline

            if relative_dir == self.relative_project_dir:
                debug("Found metadata for our prefix: %s" %
                        metadata_file)
                debug("   version: %s" % version)
                debug("   dir: %s" % relative_dir)
                if filename == self.project_name:
                    debug("Updating %s with new version." %
                            metadata_file)
                else:
                    print("WARNING: %s also references %s" % (filename,
                            self.relative_project_dir))
                    print("Assuming package has been renamed and removing it.")
                    run_command("git rm %s" % metadata_file)

    def _get_git_user_info(self):
        """ Return the user.name and user.email git config values. """
        try:
            name = run_command('git config --get user.name')
        except:
            sys.stderr.write('Warning: user.name in ~/.gitconfig not set.\n')
            name = 'Unknown name'
        try:
            email = run_command('git config --get user.email')
        except:
            sys.stderr.write('Warning: user.email in ~/.gitconfig not set.\n')
            email = None
        return (name, email)

    def _get_new_tag(self, new_version):
        """ Returns the actual tag we'll be creating. """
        suffix = ""
        # If global config specifies a tag suffix, use it:
        if self.config.has_option(BUILDCONFIG_SECTION, "tag_suffix"):
            suffix = self.config.get(BUILDCONFIG_SECTION, "tag_suffix")
        return "%s-%s%s" % (self.project_name, new_version, suffix)

    def _update_version_file(self, new_version):
        """
        land this new_version in the designated file
        and stages that file for a git commit
        """
        version_file = self._version_file_path()
        if not version_file:
            debug("No destination version file found, skipping.")
            return

        debug("Found version file to write: %s" % version_file)
        version_file_template = self._version_file_template()
        if version_file_template is None:
            error_out("Version file specified but without corresponding template.")

        t = Template(version_file_template)
        f = open(version_file, 'w')
        (new_ver, new_rel) = new_version.split('-')
        f.write(t.safe_substitute(
            version=new_ver,
            release=new_rel))
        f.close()

        run_command("git add %s" % version_file)

    def _version_file_template(self):
        """
        provide a configuration in tito.props to a file that is a
        python string.Template conforming blob, like
            [version]
            template_file = ./rel-eng/templates/my_java_properties

        variables defined inside the template are $version and $release

        see also http://docs.python.org/2/library/string.html#template-strings
        """
        if self.config.has_option("version_template", "template_file"):
            f = open(os.path.join(self.git_root,
                self.config.get("version_template", "template_file")), 'r')
            buf = f.read()
            f.close()
            return buf
        return None

    def _version_file_path(self):
        """
        provide a version file to write in tito.props, like
            [version]
            file = ./foo.rb
        """
        if self.config.has_option("version_template", "destination_file"):
            return self.config.get("version_template", "destination_file")
        return None


class ReleaseTagger(VersionTagger):
    """
    Tagger which increments the spec file release instead of version.

    Used for:
      - Packages we build from a tarball checked directly into git.
      - Satellite packages built on top of Spacewalk tarballs.
    """

    def _tag_release(self):
        """
        Tag a new release of the package. (i.e. x.y.z-r+1)
        """
        self._make_changelog()
        new_version = self._bump_version(release=True)

        self._check_tag_does_not_exist(self._get_new_tag(new_version))
        self._update_changelog(new_version)
        self._update_package_metadata(new_version)

    def release_type(self):
        """ return short string "minor release" """
        return "minor release"


class ForceVersionTagger(VersionTagger):
    """
    Tagger which forcibly updates the spec file to a version provided on the
    command line by the --use-version option.
    TODO: could this be merged into main taggers?
    """

    def _tag_release(self):
        """
        Tag a new release of the package.
        """
        self._make_changelog()
        new_version = self._bump_version(force=True)
        self._check_tag_does_not_exist(self._get_new_tag(new_version))
        self._update_changelog(new_version)
        self._update_setup_py(new_version)
        self._update_package_metadata(new_version)

########NEW FILE########
__FILENAME__ = rheltagger
import re
from tito.common import run_command
from tito.tagger import ReleaseTagger


class RHELTagger(ReleaseTagger):
    """
    Tagger which is based on ReleaseTagger and use Red Hat Enterprise Linux
    format of Changelog:
    - Resolves: #1111 - description
    or
    - Related: #1111 - description
    if BZ number was already mentioned in this changelog

    Used for:
        - Red Hat Enterprise Linux

    If you want it put in tito.pros:
    [buildconfig]
    tagger = tito.rheltagger.RHELTagger
    """

    def _generate_default_changelog(self, last_tag):
        """
        Run git-log and will generate changelog, which still can be edited by user
        in _make_changelog.
        use format:
        - Resolves: #1111 - description
        """
        patch_command = "git log --pretty='format:%%s%s'" \
                         " --relative %s..%s -- %s" % (self._changelog_email(), last_tag, "HEAD", ".")
        output = run_command(patch_command)
        BZ = {}
        result = None
        for line in reversed(output.split('\n')):
            line = self._changelog_remove_cherrypick(line)
            line = line.replace('%', '%%')

            # prepend Related/Resolves if subject contains BZ number
            m = re.match("(\d+)\s+-\s+(.*)", line)
            if m:
                bz_number = m.group(1)
                if bz_number in BZ:
                    line = "Related: #%s - %s" % (bz_number, m.group(2))
                else:
                    line = "Resolves: #%s - %s" % (bz_number, m.group(2))
                    BZ[bz_number] = 1
            if result:
                result = line + "\n" + result
            else:
                result = line
        return result

########NEW FILE########
__FILENAME__ = zstreamtagger
from tito.tagger import VersionTagger


class zStreamTagger(VersionTagger):
    """
    Tagger which increments the spec file zstream number instead of version.

    Used for:
        - Red Hat Service Packs (zstream)
    """

    def _tag_release(self):
        """
        Tag a new zstream of the package. (i.e. x.y.z-r%{dist}.Z+1)
        """
        self._make_changelog()
        new_version = self._bump_version(release=True)

        self._check_tag_does_not_exist(self._get_new_tag(new_version))
        self._update_changelog(new_version)
        self._update_package_metadata(new_version)

    def release_type(self):
        """ return short string "zstream release" """
        return "zstream release"

########NEW FILE########
__FILENAME__ = builder_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import tempfile
from os.path import join
from tito.builder import Builder
from tito.common import *
from functional.fixture import TitoGitTestFixture, tito

PKG_NAME = "titotestpkg"


class BuilderTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)
        os.chdir(self.repo_dir)

        self.config = RawConfigParser()
        self.output_dir = tempfile.mkdtemp("-titotestoutput")

    def test_scl_from_options(self):
        self.create_project(PKG_NAME)
        builder = Builder(PKG_NAME, None, self.output_dir,
            self.config, {}, {'scl': 'ruby193'}, **{'offline': True})
        self.assertEqual('ruby193', builder.scl)

    def test_scl_from_kwargs(self):
        self.create_project(PKG_NAME)
        builder = Builder(PKG_NAME, None, self.output_dir,
            self.config, {}, {}, **{'offline': True, 'scl': 'ruby193'})
        self.assertEqual('ruby193', builder.scl)

    def test_untagged_test_version(self):
        self.create_project(PKG_NAME, tag=False)
        self.assertEqual("", run_command("git tag -l").strip())

        builder = Builder(PKG_NAME, None, self.output_dir,
            self.config, {}, {}, **{'offline': True, 'test': True})
        self.assertEqual('0.0.1-1', builder.build_version)

    def test_untagged_test_build(self):
        self.create_project(PKG_NAME, tag=False)
        self.assertEqual("", run_command("git tag -l").strip())
        tito('build --srpm --test')

########NEW FILE########
__FILENAME__ = build_gitannex_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Functional Tests for the GitAnnexBuilder.
"""

import os
import glob
import tempfile
import shutil
from nose.plugins.skip import SkipTest
from os.path import join

from functional.fixture import TitoGitTestFixture, tito

from tito.compat import *
from tito.common import run_command
from tito.builder import GitAnnexBuilder

PKG_NAME = "extsrc"
GIT_ANNEX_MINIMUM_VERSION = '3.20130207'


class GitAnnexBuilderTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)

        # Guess based on python version.
        # Do not use anything based on uname in case we are in container.
        # Do not use `lsb_release` to avoid dependencies.
        if sys.version[0:3] == '2.4':
            raise SkipTest('git-annex is not available in epel-5')

        status, ga_version = getstatusoutput('rpm -q git-annex')
        if status != 0:
            raise SkipTest("git-annex is missing")

        # Setup test config:
        self.config = RawConfigParser()
        self.config.add_section("buildconfig")
        self.config.set("buildconfig", "builder",
                "tito.builder.GitAnnexBuilder")
        self.config.set("buildconfig", "offline",
                "true")

        os.chdir(self.repo_dir)
        spec = join(os.path.dirname(__file__), "specs/extsrc.spec")
        self.create_project_from_spec(PKG_NAME, self.config,
                spec=spec)
        self.source_filename = 'extsrc-0.0.2.tar.gz'

        # Make a fake source file, do we need something more real?
        run_command('touch %s' % self.source_filename)
        print(run_command('git-annex init'))

        self.output_dir = tempfile.mkdtemp("-titotestoutput")

    def tearDown(self):
        run_command('chmod -R u+rw %s' % self.output_dir)
        shutil.rmtree(self.output_dir)
        TitoGitTestFixture.tearDown(self)

    def test_simple_build(self):
        run_command('git annex add %s' % self.source_filename)
        run_command('git commit -a -m "Add source."')
        # This will create 0.0.2:
        tito('tag --debug --accept-auto-changelog')
        builder = GitAnnexBuilder(PKG_NAME, None, self.output_dir,
            self.config, {}, {}, **{'offline': True})
        builder.rpm()
        self.assertEquals(1, len(list(builder.sources)))

        self.assertEquals(2, len(builder.artifacts))
        self.assertEquals(1, len(glob.glob(join(self.output_dir,
            "extsrc-0.0.2-1.*src.rpm"))))
        self.assertEquals(1, len(glob.glob(join(self.output_dir, 'noarch',
            "extsrc-0.0.2-1.*.noarch.rpm"))))
        builder.cleanup()

    def test_lock_force_supported(self):
        tito('tag --debug --accept-auto-changelog')
        builder = GitAnnexBuilder(PKG_NAME, None, self.output_dir,
            self.config, {}, {}, **{'offline': True})

        self.assertTrue(builder._lock_force_supported('5.20140107'))
        self.assertTrue(builder._lock_force_supported('5.20131213'))
        self.assertFalse(builder._lock_force_supported('5.20131127.1'))
        self.assertFalse(builder._lock_force_supported('3.20120522'))

########NEW FILE########
__FILENAME__ = build_tito_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
'''
Functional tests to build tito with tito.
This can catch indirect omissions within tito itself.
'''

import os
import shutil
import tempfile
import unittest

from functional.fixture import tito
from glob import glob
from os.path import join


class BuildTitoTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        'Run tito build before _all_ tests in this class.'
        self.output_dir = tempfile.mkdtemp("-titotestoutput")
        os.chdir(os.path.abspath(join(__file__, '..', '..', '..')))
        self.artifacts = tito(
            'build --rpm --test --output=%s --offline --no-cleanup --debug' %
            self.output_dir
        )

    @classmethod
    def tearDownClass(self):
        'Clean up after _all_ tests in this class unless any test fails.'
        shutil.rmtree(self.output_dir)

    def test_build_tito(self):
        'Tito creates three artifacts'
        self.assertEqual(3, len(self.artifacts))

    def test_find_srpm(self):
        'One artifact is an SRPM'
        srpms = glob(join(self.output_dir, 'tito-*src.rpm'))
        self.assertEqual(1, len(srpms))

    def test_find_rpm(self):
        'One artifact is a noarch RPM'
        rpms = glob(join(self.output_dir, 'noarch', 'tito-*noarch.rpm'))
        self.assertEqual(1, len(rpms))

    def test_find_tgz(self):
        'One artifact is a tarball'
        tgzs = glob(join(self.output_dir, 'tito-*tar.gz'))
        self.assertEqual(1, len(tgzs))

########NEW FILE########
__FILENAME__ = fetch_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Functional Tests for the FetchBuilder.
"""

import glob
import os
import shutil
import tempfile

from os.path import join

from tito.common import run_command
from tito.compat import *
from functional.fixture import TitoGitTestFixture, tito

EXT_SRC_PKG = "extsrc"

RELEASER_CONF = """
[yum-test]
releaser = tito.release.YumRepoReleaser
builder = tito.builder.FetchBuilder
rsync = %s
"""


class FetchBuilderTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)
        self.pkg_dir = join(self.repo_dir, EXT_SRC_PKG)
        spec = join(os.path.dirname(__file__), "specs/extsrc.spec")

        # Setup test config:
        self.config = RawConfigParser()
        self.config.add_section("buildconfig")
        self.config.set("buildconfig", "builder",
                "tito.builder.FetchBuilder")

        self.config.add_section('builder')
        self.config.set('builder', 'fetch_strategy',
                'tito.builder.fetch.ArgSourceStrategy')

        self.create_project_from_spec(EXT_SRC_PKG, self.config,
                pkg_dir=self.pkg_dir, spec=spec)
        self.source_filename = 'extsrc-0.0.2.tar.gz'
        os.chdir(self.pkg_dir)

        # Make a fake source file, do we need something more real?
        run_command('touch %s' % self.source_filename)

        self.output_dir = tempfile.mkdtemp("-titotestoutput")

    def tearDown(self):
        TitoGitTestFixture.tearDown(self)
        # Git annex restricts permissions, change them before we remove:
        shutil.rmtree(self.output_dir)

    def test_simple_build_no_tag(self):
        # We have not tagged here. Build --rpm should just work:
        self.assertFalse(os.path.exists(
            join(self.pkg_dir, 'rel-eng/packages/extsrc')))

        tito('build --rpm --output=%s --no-cleanup --debug --arg=source=%s ' %
                (self.output_dir, self.source_filename))
        self.assertEquals(1, len(glob.glob(join(self.output_dir,
            "extsrc-0.0.2-1.*src.rpm"))))
        self.assertEquals(1, len(glob.glob(join(self.output_dir,
            "noarch/extsrc-0.0.2-1.*noarch.rpm"))))

    def test_tag_rejected(self):
        self.assertRaises(SystemExit, tito,
                'build --tag=extsrc-0.0.1-1 --rpm --output=%s --arg=source=%s ' %
                (self.output_dir, self.source_filename))

    def _setup_fetchbuilder_releaser(self, yum_repo_dir):
        self.write_file(join(self.repo_dir, 'rel-eng/releasers.conf'),
                RELEASER_CONF % yum_repo_dir)

    def test_with_releaser(self):
        yum_repo_dir = os.path.join(self.output_dir, 'yum')
        run_command('mkdir -p %s' % yum_repo_dir)
        self._setup_fetchbuilder_releaser(yum_repo_dir)
        tito('release --debug yum-test --arg source=%s' %
                self.source_filename)

        self.assertEquals(1, len(glob.glob(join(yum_repo_dir,
            "extsrc-0.0.2-1.*noarch.rpm"))))
        self.assertEquals(1, len(glob.glob(join(yum_repo_dir,
            "repodata/repomd.xml"))))

########NEW FILE########
__FILENAME__ = fixture
#
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import shutil
import tempfile
import unittest

from tito.cli import CLI
from tito.common import run_command

# NOTE: No Name in test spec file as we re-use it for several packages.
# Name must be written first.
TEST_SPEC = """
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Version:        0.0.1
Release:        1%{?dist}
Summary:        Tito test package.
URL:            https://example.com
Group:          Applications/Internet
License:        GPLv2
BuildRoot:      %{_tmppath}/%{name}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python-devel
BuildRequires:  python-setuptools
Source0:        %{name}-%{version}.tar.gz

%description
Nobody cares.

%prep
#nothing to do here
%setup -q -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
rm -f $RPM_BUILD_ROOT%{python_sitelib}/*egg-info/requires.txt

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
#%dir %{python_sitelib}/%{name}
%{python_sitelib}/%{name}-*.egg-info

%changelog
"""

TEST_SETUP_PY = """
from setuptools import setup, find_packages

setup(
    name="%s",
    version='1.0',
    description='tito test project',
    author='Nobody Knows',
    author_email='tito@example.com',
    url='http://rm-rf.ca/tito',
    license='GPLv2+',

    package_dir={
        '%s': 'src/',
    },
    packages = find_packages('src'),
    include_package_data = True,

    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],
)
"""

TEST_PYTHON_SRC = """
class Empty(object):
    pass
"""


def tito(argstring):
    """ Run Tito from source with given arguments. """
    return CLI().main(argstring.split(' '))


class TitoGitTestFixture(unittest.TestCase):
    """
    Fixture providing setup/teardown and utilities for all tests requiring
    an actual git repository.
    """
    def setUp(self):
        # Create a temporary directory for our test git repository:
        self.repo_dir = tempfile.mkdtemp("-titotest")
        print
        print
        print("Testing in: %s" % self.repo_dir)
        print

        # Initialize the repo:
        os.chdir(self.repo_dir)
        run_command('git init')

        # Next we tito init:
        tito("init")
        run_command('echo "offline = true" >> rel-eng/tito.props')
        run_command('git add rel-eng/tito.props')
        run_command("git commit -m 'set offline in tito.props'")

    def tearDown(self):
        run_command('chmod -R u+rw %s' % self.repo_dir)
        shutil.rmtree(self.repo_dir)
        pass

    def write_file(self, path, contents):
        out_f = open(path, 'w')
        out_f.write(contents)
        out_f.close()

    def create_project_from_spec(self, pkg_name, config,
            pkg_dir='', spec=None):
        """
        Create a sample tito project and copy the given test spec file over.
        """
        full_pkg_dir = os.path.join(self.repo_dir, pkg_dir)
        run_command('mkdir -p %s' % full_pkg_dir)
        os.chdir(full_pkg_dir)

        shutil.copyfile(spec, os.path.join(full_pkg_dir, os.path.basename(spec)))

        # Write the config object we were given out to the project repo:
        configfile = open(os.path.join(full_pkg_dir, 'tito.props'), 'w')
        config.write(configfile)
        configfile.close()

    def create_project(self, pkg_name, pkg_dir='', tag=True):
        """
        Create a test project at the given location, assumed to be within
        our test repo, but possibly within a sub-directory.
        """
        full_pkg_dir = os.path.join(self.repo_dir, pkg_dir)
        run_command('mkdir -p %s' % full_pkg_dir)
        os.chdir(full_pkg_dir)

        # TODO: Test project needs work, doesn't work in some scenarios
        # like UpstreamBuilder:
        self.write_file(os.path.join(full_pkg_dir, 'a.txt'), "BLERG\n")

        # Write the test spec file:
        self.write_file(os.path.join(full_pkg_dir, "%s.spec" % pkg_name),
            "Name: %s\n%s" % (pkg_name, TEST_SPEC))

        # Write test setup.py:
        self.write_file(os.path.join(full_pkg_dir, "setup.py"),
            TEST_SETUP_PY % (pkg_name, pkg_name))

        # Write test source:
        run_command('mkdir -p %s' % os.path.join(full_pkg_dir, "src"))
        self.write_file(os.path.join(full_pkg_dir, "src", "module.py"),
            TEST_PYTHON_SRC)

        files = [os.path.join(pkg_dir, 'a.txt'),
                os.path.join(pkg_dir, 'setup.py'),
                os.path.join(pkg_dir, '%s.spec' % pkg_name),
                os.path.join(pkg_dir, 'src/module.py')
        ]
        run_command('git add %s' % ' '.join(files))
        run_command("git commit -m 'initial commit'")

        if tag:
            tito('tag --keep-version --debug --accept-auto-changelog')

########NEW FILE########
__FILENAME__ = multiproject_tests
#
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Functional Tests for Tito at the CLI level.

NOTE: These tests require a makeshift git repository created in /tmp.
"""

import os
from os.path import join

from tito.common import run_command, \
    get_latest_tagged_version, tag_exists_locally
from functional.fixture import *

# A location where we can safely create a test git repository.
# WARNING: This location will be destroyed if present.

TEST_PKG_1 = 'titotestpkg'

TEST_PKG_2 = 'titotestpkg2'

TEST_PKG_3 = 'titotestpkg3'

TEST_PKGS = [TEST_PKG_1, TEST_PKG_2, TEST_PKG_3]


def release_bumped(initial_version, new_version):
    first_release = initial_version.split('-')[-1]
    new_release = new_version.split('-')[-1]
    return new_release == str(int(first_release) + 1)

TEMPLATE_TAGGER_TITO_PROPS = """
[buildconfig]
tagger = tito.tagger.VersionTagger
builder = tito.builder.Builder

[version_template]
destination_file = version.txt
template_file = rel-eng/templates/version.rb
"""

VERSION_TEMPLATE_FILE = """
module Iteng
    module Util
      VERSION = "$version-$release"
    end
  end
"""


class MultiProjectTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)

        self.create_project(TEST_PKG_1, os.path.join(self.repo_dir, 'pkg1'))
        self.create_project(TEST_PKG_2, os.path.join(self.repo_dir, 'pkg2'))
        self.create_project(TEST_PKG_3, os.path.join(self.repo_dir, 'pkg3'))

        # For second test package, use a tito.props to override and use the
        # ReleaseTagger:
        filename = os.path.join(self.repo_dir, 'pkg2', "tito.props")
        out_f = open(filename, 'w')
        out_f.write("[buildconfig]\n")
        out_f.write("tagger = tito.tagger.ReleaseTagger\n")
        out_f.write("builder = tito.builder.Builder\n")
        out_f.close()

        os.chdir(self.repo_dir)
        run_command('git add pkg2/tito.props')
        run_command("git commit -m 'add tito.props for pkg2'")

    def test_template_version_tagger(self):
        """
        Make sure the template is applied and results in the correct file
        being included in the tag.
        """
        pkg_dir = join(self.repo_dir, 'pkg3')
        filename = join(pkg_dir, "tito.props")
        self.write_file(filename, TEMPLATE_TAGGER_TITO_PROPS)
        run_command('mkdir -p %s' % join(self.repo_dir, 'rel-eng/templates'))
        self.write_file(join(self.repo_dir,
            'rel-eng/templates/version.rb'), VERSION_TEMPLATE_FILE)

        os.chdir(self.repo_dir)
        run_command('git add pkg3/tito.props')
        run_command("git commit -m 'add tito.props for pkg3'")

        # Create another pkg3 tag and make sure we got a generated
        # template file.
        os.chdir(os.path.join(self.repo_dir, 'pkg3'))
        tito('tag --debug --accept-auto-changelog')
        new_ver = get_latest_tagged_version(TEST_PKG_3)
        self.assertEquals("0.0.2-1", new_ver)

        dest_file = os.path.join(self.repo_dir, 'pkg3', "version.txt")
        self.assertTrue(os.path.exists(dest_file))

        f = open(dest_file, 'r')
        contents = f.read()
        f.close()

        self.assertTrue("VERSION = \"0.0.2-1\"" in contents)

    def test_initial_tag_keep_version(self):
        # Tags were actually created in setup code:
        for pkg_name in TEST_PKGS:
            self.assertTrue(tag_exists_locally("%s-0.0.1-1" % pkg_name))
            self.assertTrue(os.path.exists(os.path.join(self.repo_dir,
                "rel-eng/packages", pkg_name)))

    def test_release_tagger(self):
        os.chdir(os.path.join(self.repo_dir, 'pkg2'))
        start_ver = get_latest_tagged_version(TEST_PKG_2)
        tito('tag --debug --accept-auto-changelog')
        new_ver = get_latest_tagged_version(TEST_PKG_2)
        self.assertTrue(release_bumped(start_ver, new_ver))

    def test_build_tgz(self):
        os.chdir(os.path.join(self.repo_dir, 'pkg1'))
        artifacts = tito('build --tgz')
        self.assertEquals(1, len(artifacts))
        self.assertEquals('%s-0.0.1.tar.gz' % TEST_PKG_1,
                os.path.basename(artifacts[0]))

    def test_build_rpm(self):
        os.chdir(os.path.join(self.repo_dir, 'pkg1'))
        artifacts = tito('build --rpm')
        self.assertEquals(3, len(artifacts))

########NEW FILE########
__FILENAME__ = release_copr_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Functional Tests for the CoprReleaser.
"""

from functional.fixture import TitoGitTestFixture

from tito.compat import *
from tito.release import CoprReleaser

PKG_NAME = "releaseme"

RELEASER_CONF = """
[test]
releaser = tito.release.CoprReleaser
builder = tito.builder.Builder
"""


class CoprReleaserTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)
        self.create_project(PKG_NAME)

        # Setup test config:
        self.config = RawConfigParser()
        self.config.add_section("buildconfig")
        self.config.set("buildconfig", "builder",
                "tito.builder.Builder")
        self.config.set("buildconfig", "offline",
                "true")

        self.releaser_config = RawConfigParser()
        self.releaser_config.add_section('test')
        self.releaser_config.set('test', 'releaser',
            'tito.release.CoprReleaser')
        self.releaser_config.set('test', 'builder',
            'tito.builder.Builder')
        self.releaser_config.set('test', 'project_name', PKG_NAME)
        self.releaser_config.set('test', 'upload_command',
            'scp %(srpm)s example.com/public_html/my_srpm/')
        self.releaser_config.set('test', 'remote_location',
            'http://example.com/~someuser/my_srpm/')

    def test_with_releaser(self):
        releaser = CoprReleaser(PKG_NAME, None, '/tmp/tito/',
            self.config, {}, 'test', self.releaser_config, False,
            False, False, **{'offline': True})
        releaser.release(dry_run=True)
        self.assertTrue(releaser.srpm_submitted is not None)

########NEW FILE########
__FILENAME__ = release_yum_tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
Functional Tests for the YumReleaser.
"""

import glob
import os
import shutil
import tempfile

from os.path import join

from functional.fixture import TitoGitTestFixture, tito

from tito.compat import *
from tito.common import run_command

PKG_NAME = "releaseme"

RELEASER_CONF = """
[yum-test]
releaser = tito.release.YumRepoReleaser
builder = tito.builder.Builder
rsync = %s
"""


class YumReleaserTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)
        self.create_project(PKG_NAME)

        # Setup test config:
        self.config = RawConfigParser()
        self.config.add_section("buildconfig")
        self.config.set("buildconfig", "builder",
                "tito.builder.Builder")
        self.config.set("buildconfig", "offline",
                "true")

        self.output_dir = tempfile.mkdtemp("-titotestoutput")

    def tearDown(self):
        TitoGitTestFixture.tearDown(self)
        shutil.rmtree(self.output_dir)
        pass

    def _setup_fetchbuilder_releaser(self, yum_repo_dir):
        self.write_file(join(self.repo_dir, 'rel-eng/releasers.conf'),
                RELEASER_CONF % yum_repo_dir)

    def test_with_releaser(self):
        yum_repo_dir = os.path.join(self.output_dir, 'yum')
        run_command('mkdir -p %s' % yum_repo_dir)
        self._setup_fetchbuilder_releaser(yum_repo_dir)
        tito('release --debug yum-test')

        self.assertEquals(1, len(glob.glob(join(yum_repo_dir,
            "releaseme-0.0.1-1.*noarch.rpm"))))
        self.assertEquals(1, len(glob.glob(join(yum_repo_dir,
            "repodata/repomd.xml"))))

########NEW FILE########
__FILENAME__ = singleproject_tests
#
# Copyright (c) 2008-2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
from tito.common import *
from functional.fixture import TitoGitTestFixture, tito

PKG_NAME = "titotestpkg"


class SingleProjectTests(TitoGitTestFixture):

    def setUp(self):
        TitoGitTestFixture.setUp(self)

        self.create_project(PKG_NAME)
        os.chdir(self.repo_dir)

    def test_init_worked(self):
        # Not actually running init here, just making sure it worked when
        # run during setup.
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "rel-eng")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "rel-eng",
            "packages")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "rel-eng",
            "tito.props")))

    def test_initial_tag(self):
        self.assertTrue(tag_exists_locally("%s-0.0.1-1" % PKG_NAME))

    def test_tag(self):
        tito("tag --accept-auto-changelog --debug")
        check_tag_exists("%s-0.0.2-1" % PKG_NAME, offline=True)

    def test_tag_with_version(self):
        tito("tag --accept-auto-changelog --debug --use-version 9.0.0")
        check_tag_exists("%s-9.0.0-1" % PKG_NAME, offline=True)

    def test_undo_tag(self):
        os.chdir(self.repo_dir)
        original_head = getoutput('git show-ref -s refs/heads/master')

        # Create tito tag, which adds a new commit and moves head.
        tito("tag --accept-auto-changelog --debug")
        tag = "%s-0.0.2-1" % PKG_NAME
        check_tag_exists(tag, offline=True)
        new_head = getoutput('git show-ref -s refs/heads/master')
        self.assertNotEqual(original_head, new_head)

        # Undo tito tag, which rewinds one commit to original head.
        tito("tag -u")
        self.assertFalse(tag_exists_locally(tag))
        new_head = getoutput('git show-ref -s refs/heads/master')
        self.assertEqual(original_head, new_head)

    def test_latest_tgz(self):
        tito("build --tgz -o %s" % self.repo_dir)

    def test_build_tgz_tag(self):
        tito("build --tgz --tag=%s-0.0.1-1 -o %s" % (PKG_NAME,
            self.repo_dir))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir,
            "%s-0.0.1.tar.gz" % PKG_NAME)))

    def test_build_latest_srpm(self):
        tito("build --srpm")

    def test_build_srpm_tag(self):
        tito("build --srpm --tag=%s-0.0.1-1 -o %s" % (PKG_NAME, self.repo_dir))

    def test_build_latest_rpm(self):
        tito("build --rpm -o %s" % self.repo_dir)

    def test_build_rpm_tag(self):
        tito("build --rpm --tag=%s-0.0.1-1 -o %s" % (PKG_NAME,
            self.repo_dir))

########NEW FILE########
__FILENAME__ = common-tests
#
# Copyright (c) 2008-2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

""" Pure unit tests for tito's common module. """

from tito.common import *
from tito import common

import unittest

from mock import Mock


class CommonTests(unittest.TestCase):

    def test_normalize_class_name(self):
        """ Test old spacewalk.releng namespace is converted to tito. """
        self.assertEquals("tito.builder.Builder",
                normalize_class_name("tito.builder.Builder"))
        self.assertEquals("tito.builder.Builder",
                normalize_class_name("spacewalk.releng.builder.Builder"))
        self.assertEquals("tito.tagger.VersionTagger",
                normalize_class_name("spacewalk.releng.tagger.VersionTagger"))

    def test_replace_version_leading_whitespace(self):
        line = "    version='1.0'\n"
        expected = "    version='2.5.3'\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_no_whitespace(self):
        line = "version='1.0'\n"
        expected = "version='2.5.3'\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_some_whitespace(self):
        line = "version = '1.0'\n"
        expected = "version = '2.5.3'\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_double_quote(self):
        line = 'version="1.0"\n'
        expected = 'version="2.5.3"\n'
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_trailing_chars(self):
        line = "version = '1.0', blah blah blah\n"
        expected = "version = '2.5.3', blah blah blah\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_crazy_old_version(self):
        line = "version='1.0asjhd82371kjsdha98475h87asd7---asdai.**&'\n"
        expected = "version='2.5.3'\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_crazy_new_version(self):
        line = "version='1.0'\n"
        expected = "version='91asj.;]][[a]sd[]'\n"
        self.assertEquals(expected, replace_version(line,
            "91asj.;]][[a]sd[]"))

    def test_replace_version_uppercase(self):
        line = "VERSION='1.0'\n"
        expected = "VERSION='2.5.3'\n"
        self.assertEquals(expected, replace_version(line, "2.5.3"))

    def test_replace_version_no_match(self):
        line = "this isn't a version fool.\n"
        self.assertEquals(line, replace_version(line, "2.5.3"))

    def test_extract_sha1(self):
        ls_remote_output = "Could not chdir to home directory\n" + \
                           "fe87e2b75ed1850718d99c797cc171b88bfad5ca ref/origin/sometag"
        self.assertEquals("fe87e2b75ed1850718d99c797cc171b88bfad5ca",
                          extract_sha1(ls_remote_output))

    def test_compare_version(self):
        self.assertEquals(0, compare_version("1", "1"))
        self.assertTrue(compare_version("2.1", "2.2") < 0)
        self.assertTrue(compare_version("3.0.4.10", "3.0.4.2") > 0)
        self.assertTrue(compare_version("4.08", "4.08.01") < 0)
        self.assertTrue(compare_version("3.2.1.9.8144", "3.2") > 0)
        self.assertTrue(compare_version("3.2", "3.2.1.9.8144") < 0)
        self.assertTrue(compare_version("1.2", "2.1") < 0)
        self.assertTrue(compare_version("2.1", "1.2") > 0)
        self.assertTrue(compare_version("1.0", "1.0.1") < 0)
        self.assertTrue(compare_version("1.0.1", "1.0") > 0)
        self.assertEquals(0, compare_version("5.6.7", "5.6.7"))
        self.assertEquals(0, compare_version("1.01.1", "1.1.1"))
        self.assertEquals(0, compare_version("1.1.1", "1.01.1"))
        self.assertEquals(0, compare_version("1", "1.0"))
        self.assertEquals(0, compare_version("1.0", "1"))
        self.assertEquals(0, compare_version("1.0.2.0", "1.0.2"))

    def test_run_command_print(self):
        self.assertEquals('', run_command_print("sleep 0.1"))


class VersionMathTest(unittest.TestCase):
    def test_increase_version_minor(self):
        line = "1.0.0"
        expected = "1.0.1"
        self.assertEquals(expected, increase_version(line))

    def test_increase_version_major(self):
        line = "1.0"
        expected = "1.1"
        self.assertEquals(expected, increase_version(line))

    def test_increase_release(self):
        line = "1"
        expected = "2"
        self.assertEquals(expected, increase_version(line))

    def test_underscore_release(self):
        line = "1_PG5"
        expected = "2_PG5"
        self.assertEquals(expected, increase_version(line))

    def test_increase_versionless(self):
        line = "%{app_version}"
        expected = "%{app_version}"
        self.assertEquals(expected, increase_version(line))

    def test_increase_release_with_rpm_cruft(self):
        line = "1%{?dist}"
        expected = "2%{?dist}"
        self.assertEquals(expected, increase_version(line))

    def test_increase_release_with_zstream(self):
        line = "1%{?dist}.1"
        expected = "1%{?dist}.2"
        self.assertEquals(expected, increase_version(line))

    def test_unknown_version(self):
        line = "somethingstrange"
        expected = "somethingstrange"
        self.assertEquals(expected, increase_version(line))

    def test_empty_string(self):
        line = ""
        expected = ""
        self.assertEquals(expected, increase_version(line))

    def test_increase_zstream(self):
        line = "1%{?dist}"
        expected = "1%{?dist}.1"
        self.assertEquals(expected, increase_zstream(line))

    def test_increase_zstream_already_appended(self):
        line = "1%{?dist}.1"
        expected = "1%{?dist}.2"
        self.assertEquals(expected, increase_zstream(line))

    def test_reset_release_with_rpm_cruft(self):
        line = "2%{?dist}"
        expected = "1%{?dist}"
        self.assertEquals(expected, reset_release(line))

    def test_reset_release_with_more_rpm_cruft(self):
        line = "2.beta"
        expected = "1.beta"
        self.assertEquals(expected, reset_release(line))

    def test_reset_release(self):
        line = "2"
        expected = "1"
        self.assertEquals(expected, reset_release(line))


class ExtractBugzillasTest(unittest.TestCase):

    def test_single_line(self):
        commit_log = "- 123456: Did something interesting."
        results = extract_bzs(commit_log)
        self.assertEquals(1, len(results))
        self.assertEquals("Resolves: #123456 - Did something interesting.",
                results[0])

    def test_single_with_dash(self):
        commit_log = "- 123456 - Did something interesting."
        results = extract_bzs(commit_log)
        self.assertEquals(1, len(results))
        self.assertEquals("Resolves: #123456 - Did something interesting.",
                results[0])

    def test_single_with_no_spaces(self):
        commit_log = "- 123456-Did something interesting."
        results = extract_bzs(commit_log)
        self.assertEquals(1, len(results))
        self.assertEquals("Resolves: #123456 - Did something interesting.",
                results[0])

    def test_diff_format(self):
        commit_log = "+- 123456: Did something interesting."
        results = extract_bzs(commit_log)
        self.assertEquals(1, len(results))
        self.assertEquals("Resolves: #123456 - Did something interesting.",
                results[0])

    def test_single_line_no_bz(self):
        commit_log = "- Did something interesting."
        results = extract_bzs(commit_log)
        self.assertEquals(0, len(results))

    def test_multi_line(self):
        commit_log = "- 123456: Did something interesting.\n- Another commit.\n" \
            "- 456789: A third commit."
        results = extract_bzs(commit_log)
        self.assertEquals(2, len(results))
        self.assertEquals("Resolves: #123456 - Did something interesting.",
                results[0])
        self.assertEquals("Resolves: #456789 - A third commit.",
                results[1])

    def test_rpmbuild_cailms_to_be_successul(self):
        succeeded_result = "success"
        output = "Wrote: %s" % succeeded_result

        success_line = find_wrote_in_rpmbuild_output(output)

        self.assertEquals(succeeded_result, success_line[0])

    def test_rpmbuild_which_ended_with_error_is_described_with_the_analyzed_line(self):
        output = "some error output from rpmbuild\n" \
            "next error line"

        common.error_out = Mock()

        find_wrote_in_rpmbuild_output(output)

        common.error_out.assert_called_once_with("Unable to locate 'Wrote: ' lines in rpmbuild output: '%s'" % output)

########NEW FILE########
__FILENAME__ = fixture
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
import os
import unittest

from tito.compat import *

UNIT_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_DIR = os.path.join(UNIT_DIR, '..', '..')


class TitoUnitTestFixture(unittest.TestCase):
    """
    Fixture providing setup/teardown and utilities for unit tests.
    """
    def setUp(self):
        print
        print
        print("Testing in: %s" % REPO_DIR)
        print

########NEW FILE########
__FILENAME__ = pep8-tests
#
# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

"""
Use pep8 to check for errors or deprecations that can cause Python 3 to fail.
source: https://github.com/jcrocholl/pep8
docs:   http://pep8.readthedocs.org/en/latest/intro.html

Python 3 is picky about indentation:
http://docs.python.org/3.3/reference/lexical_analysis.html
"""

import pep8
from unit.fixture import *


class TestPep8(TitoUnitTestFixture):
    def setUp(self):
        TitoUnitTestFixture.setUp(self)

    def test_conformance(self):
        tests = [
            # http://pep8.readthedocs.org/en/latest/intro.html#error-codes
            'E101',  # indentation contains mixed spaces and tabs
            'E111',  # indentation is not a multiple of four
            'E112',  # expected an indented block
            'E113',  # unexpected indentation
            'E121',  # continuation line indentation is not a multiple of four
            'E122',  # continuation line missing indentation or outdented
            'E126',  # continuation line over-indented for hanging indent
            'E2',    # whitespace errors
            'E3',    # blank line errors
            'E4',    # import errors
            'E502',  # the backslash is redundant between brackets
            'E7',    # statement errors
            'E9',    # runtime errors (SyntaxError, IndentationError, IOError)
            'W1',    # indentation warnings
            'W2',    # whitespace warnings
            'W3',    # blank line warnings
            'W6',    # deprecated features
        ]

        try:
            checker = pep8.StyleGuide(select=tests, paths=[REPO_DIR])
            result = checker.check_files().total_errors
        except AttributeError:
            # We don't have pep8.StyleGuide, so we must be
            # using pep8 older than git tag 1.1-72-gf20d656.
            os.chdir(REPO_DIR)
            checks = ','.join(tests)
            cmd = "pep8 --select=%s %s | wc -l" % (checks, '.')
            result = int(getoutput(cmd))

        self.assertEqual(result, 0,
            "Found PEP8 errors that may break your code in Python 3.")


class UglyHackishTest(TitoUnitTestFixture):
    def setUp(self):
        TitoUnitTestFixture.setUp(self)
        os.chdir(REPO_DIR)

    def test_exceptions_2_dot_4(self):
        # detect 'except rpm.error as e:'
        regex = "'^[[:space:]]*except .* as .*:'"
        cmd = "find . -type f -regex '.*\.py$' -exec egrep %s {} + | wc -l" % regex
        result = int(getoutput(cmd))
        self.assertEqual(result, 0, "Found except clause not supported in Python 2.4")

    def test_exceptions_3(self):
        # detect 'except rpm.error, e:'
        regex = "'^[[:space:]]*except [^,]+,[[:space:]]*[[:alpha:]]+:'"
        cmd = "find . -type f -regex '.*\.py$' -exec egrep %s {} + | wc -l" % regex
        result = int(getoutput(cmd))
        self.assertEqual(result, 0, "Found except clause not supported in Python 3")

    def test_import_commands(self):
        cmd = "find . -type f -regex '.*\.py$' -exec egrep '^(import|from) commands\.' {} + | grep -v 'compat\.py' | wc -l"
        result = int(getoutput(cmd))
        self.assertEqual(result, 0, "Found commands module (not supported in Python 3)")

    def test_use_commands(self):
        cmd = "find . -type f -regex '.*\.py$' -exec egrep 'commands\.' {} + | grep -v 'compat\.py' | wc -l"
        result = int(getoutput(cmd))
        self.assertEqual(result, 0, "Found commands module (not supported in Python 3)")

    def test_print_function(self):
        cmd = "find . -type f -regex '.*\.py$' -exec grep '^[[:space:]]*print .*' {} + | wc -l"
        result = int(getoutput(cmd))
        self.assertEqual(result, 0, "Found print statement (not supported in Python 3)")

########NEW FILE########
__FILENAME__ = test_build_target_parser

import unittest
from tito.buildparser import BuildTargetParser
from tito.compat import *
from tito.exception import TitoException


class BuildTargetParserTests(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.valid_branches = ["branch1", "branch2"]

        self.release_target = "project-x.y.z"
        self.releasers_config = RawConfigParser()
        self.releasers_config.add_section(self.release_target)
        self.releasers_config.set(self.release_target, "build_targets",
                                  "branch1:project-x.y.z-candidate")

    def test_parser_gets_correct_targets(self):
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        release_targets = parser.get_build_targets()
        self.assertTrue("branch1" in release_targets)
        self.assertEqual("project-x.y.z-candidate", release_targets["branch1"])
        self.assertFalse("branch2" in release_targets)

    def test_invalid_branch_raises_exception(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  "invalid-branch:project-x.y.z-candidate")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        self.assertRaises(TitoException, parser.get_build_targets)

    def test_missing_semicolon_raises_exception(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  "invalid-branchproject-x.y.z-candidate")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        self.assertRaises(TitoException, parser.get_build_targets)

    def test_empty_branch_raises_exception(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  ":project-x.y.z-candidate")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        self.assertRaises(TitoException, parser.get_build_targets)

    def test_empty_target_raises_exception(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  "branch1:")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        self.assertRaises(TitoException, parser.get_build_targets)

    def test_multiple_spaces_ok(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  "       branch1:project-x.y.z-candidate      ")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        release_targets = parser.get_build_targets()
        self.assertEqual(1, len(release_targets))
        self.assertTrue("branch1" in release_targets)
        self.assertEqual("project-x.y.z-candidate", release_targets["branch1"])

    def test_multiple_branches_supported(self):
        self.releasers_config.set(self.release_target, "build_targets",
                                  "branch1:project-x.y.z-candidate branch2:second-target")
        parser = BuildTargetParser(self.releasers_config, self.release_target,
                                   self.valid_branches)
        release_targets = parser.get_build_targets()
        self.assertEquals(2, len(release_targets))
        self.assertTrue("branch1" in release_targets)
        self.assertEqual("project-x.y.z-candidate", release_targets["branch1"])
        self.assertTrue("branch2" in release_targets)
        self.assertEqual("second-target", release_targets['branch2'])

########NEW FILE########
