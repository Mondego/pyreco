__FILENAME__ = fabfile
import os.path
from fabric.api import local, env
from fabric.utils import fastprint
from prezi.fabric.s3 import CommonTasks, S3Deploy, NoopServiceManager

env.forward_agent = True
env.user = 'publisher'
env.roledefs = {'production': [], 'stage': [], 'local': []}



class SingleVirtualenvS3Deploy(S3Deploy):
    def __init__(self, app_name, buckets, revno):
        super(SingleVirtualenvS3Deploy, self).__init__(app_name, buckets, revno)
        self.service = NoopServiceManager(self)
        self.virtualenv = SingleVirtualenvService(self)


class SingleVirtualenvService(object):
    def __init__(self, deployer):
        self.deployer = deployer
        self.tarball_path = self.deployer.build_dir + '.tar'
        self.tarbz_path = self.tarball_path + '.bz2'
        self.tarbz_name = os.path.basename(self.tarbz_path)

    def build_tarbz(self):
        self.build_venv()
        self.compress_venv()

    def cleanup(self):
        local('rm -rf %s %s' % (self.tarbz_path, self.deployer.build_dir))

    def build_venv(self):
        fastprint('Building single virtualenv service in %s\n' % self.deployer.build_dir)
        # init + update pip submodule
        local('git submodule init; git submodule update')
        # builds venv
        self.run_virtualenv_cmd("--distribute --no-site-packages -p python2.7 %s" % self.deployer.build_dir)
        # installs app + dependencies
        local(' && '.join(
            ['. %s/bin/activate' % self.deployer.build_dir,
             'pip install --exists-action=s -e `pwd`/pip#egg=pip -e `pwd`@master#egg=snakebasket -r requirements-development.txt']
        ))
        # makes venv relocatable
        self.run_virtualenv_cmd("--relocatable -p python2.7 %s" % self.deployer.build_dir)

    def compress_venv(self):
        fastprint('Compressing virtualenv')
        local('tar -C %(build_dir)s/.. -cjf %(tarbz_path)s %(dirname)s' % {
            'build_dir': self.deployer.build_dir,
            'tarbz_path': self.tarbz_path,
            'dirname': os.path.basename(self.deployer.build_dir)
        })

    def run_virtualenv_cmd(self, args):
        if not isinstance(args, list):
            args = args.split()
        fastprint('Running virtualenv with args %s\n' % args)
        local("env VERSIONER_PYTHON_VERSION='' virtualenv %s" % ' '.join(args))

    @property
    def upload_source(self):
        return self.tarbz_path

    @property
    def upload_target(self):
        return self.tarbz_name


tasks = CommonTasks(SingleVirtualenvS3Deploy, 'snakebasket', None)
snakebasket_build = tasks.build
cleanup = tasks.cleanup

########NEW FILE########
__FILENAME__ = install
import sys
import os
from pip.req import InstallRequirement, InstallationError, _make_build_dir, parse_requirements, Requirements
from pip.commands.install import InstallCommand, RequirementSet
from pip.exceptions import BestVersionAlreadyInstalled, CommandError, DistributionNotFound
from pip.vcs import vcs
from urllib2 import HTTPError
import pkg_resources
from pip.log import logger
from pip.index import Link
import tempfile
import shutil
from pip.backwardcompat import home_lib
from pip.locations import virtualenv_no_global
from pip.util import dist_in_usersite
from pip.baseparser import create_main_parser 
from ..versions import  InstallReqChecker, PackageData

class ExtendedRequirements(Requirements):
    def __init__(self, *args, **kwargs):
        super(ExtendedRequirements, self).__init__(*args, **kwargs)

    def __delitem__(self, key, value):
        if key in self._keys:
            self._keys = [k for k in self._keys if k != key]
        del self._dict[key]

class RecursiveRequirementSet(RequirementSet):

    def __init__(self, *args, **kwargs):
        super(RecursiveRequirementSet, self).__init__(*args, **kwargs)
        self.options = None
        self.requirements = ExtendedRequirements()
        self.install_req_checker = InstallReqChecker(
            self.src_dir,
            self.requirements,
            self.successfully_downloaded)

    def set_options(self, value):
        self.options = value
        self.install_req_checker.prefer_pinned_revision = value.prefer_pinned_revision

    def prepare_files(self, finder, force_root_egg_info=False, bundle=False):

        """Prepare process. Create temp directories, download and/or unpack files."""
        unnamed = list(self.unnamed_requirements)
        reqs = list(self.requirements.values())
        while reqs or unnamed:
            if unnamed:
                req_to_install = unnamed.pop(0)
            else:
                req_to_install = reqs.pop(0)
            install = True
            best_installed = False
            not_found = None
            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()

                if req_to_install.satisfied_by:

                    substitute = self.install_req_checker.get_available_substitute(req_to_install)

                    # if the req_to_install is identified as the best available substitue
                    # AND
                    # ( no version with req_to_install.name has been installed 
                        # OR a different version of req_to_install.name has been installed
                    # )
                    # then set the self.upgrade flag to True to install req_to_install

                    if (
                        req_to_install == substitute.requirement
                        and
                        (
                            req_to_install.name not in self.install_req_checker.pre_installed
                            or
                            self.install_req_checker.pre_installed[req_to_install.name].requirement is not req_to_install
                        )
                    ):
                        self.upgrade = True 

                    if self.upgrade:
                        if not self.force_reinstall and not req_to_install.url:
                            try:
                                url = finder.find_requirement(
                                    req_to_install, self.upgrade)
                            except BestVersionAlreadyInstalled:
                                best_installed = True
                                install = False
                            except DistributionNotFound:
                                not_found = sys.exc_info()[1]
                            else:
                                # Avoid the need to call find_requirement again
                                req_to_install.url = url.url

                        if not best_installed:
                            #don't uninstall conflict if user install and conflict is not user install
                            if not (self.use_user_site and not dist_in_usersite(req_to_install.satisfied_by)):
                                req_to_install.conflicts_with = req_to_install.satisfied_by
                            req_to_install.satisfied_by = None
                    else:
                        install = False
                if req_to_install.satisfied_by:
                    if best_installed:
                        logger.notify('Requirement already up-to-date: %s'
                                      % req_to_install)
                    else:
                        logger.notify('Requirement already satisfied '
                                      '(use --upgrade to upgrade): %s'
                                      % req_to_install)
            if req_to_install.editable:
                logger.notify('Obtaining %s' % req_to_install)
            elif install:
                logger.notify('Downloading/unpacking %s' % req_to_install)
            logger.indent += 2
            try:
                is_bundle = False
                if req_to_install.editable:
                    if req_to_install.source_dir is None:
                        location = req_to_install.build_location(self.src_dir)
                        req_to_install.source_dir = location
                    else:
                        location = req_to_install.source_dir
                    if not os.path.exists(self.build_dir):
                        _make_build_dir(self.build_dir)
                    req_to_install.update_editable(not self.is_download)
                    if self.is_download:
                        req_to_install.run_egg_info()
                        req_to_install.archive(self.download_dir)
                    else:
                        req_to_install.run_egg_info()
                elif install:
                    ##@@ if filesystem packages are not marked
                    ##editable in a req, a non deterministic error
                    ##occurs when the script attempts to unpack the
                    ##build directory

                    # NB: This call can result in the creation of a temporary build directory
                    location = req_to_install.build_location(self.build_dir, not self.is_download)

                    ## FIXME: is the existance of the checkout good enough to use it?  I don't think so.
                    unpack = True
                    url = None
                    if not os.path.exists(os.path.join(location, 'setup.py')):
                        ## FIXME: this won't upgrade when there's an existing package unpacked in `location`
                        if req_to_install.url is None:
                            if not_found:
                                raise not_found
                            url = finder.find_requirement(req_to_install, upgrade=self.upgrade)
                        else:
                            ## FIXME: should req_to_install.url already be a link?
                            url = Link(req_to_install.url)
                            assert url
                        if url:
                            try:
                                self.unpack_url(url, location, self.is_download)
                            except HTTPError:
                                e = sys.exc_info()[1]
                                logger.fatal('Could not install requirement %s because of error %s'
                                             % (req_to_install, e))
                                raise InstallationError(
                                    'Could not install requirement %s because of HTTP error %s for URL %s'
                                    % (req_to_install, e, url))
                        else:
                            unpack = False
                    if unpack:
                        is_bundle = req_to_install.is_bundle
                        if is_bundle:
                            req_to_install.move_bundle_files(self.build_dir, self.src_dir)
                            for subreq in req_to_install.bundle_requirements():
                                reqs.append(subreq)
                                self.add_requirement(subreq)
                        elif self.is_download:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if url and url.scheme in vcs.all_schemes:
                                req_to_install.archive(self.download_dir)
                        else:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if force_root_egg_info:
                                # We need to run this to make sure that the .egg-info/
                                # directory is created for packing in the bundle
                                req_to_install.run_egg_info(force_root_egg_info=True)
                            req_to_install.assert_source_matches_version()
                            #@@ sketchy way of identifying packages not grabbed from an index
                            if bundle and req_to_install.url:
                                self.copy_to_build_dir(req_to_install)
                                install = False
                            # req_to_install.req is only avail after unpack for URL pkgs
                        # repeat check_if_exists to uninstall-on-upgrade (#14)
                        req_to_install.check_if_exists()
                        if req_to_install.satisfied_by:
                            if self.upgrade or self.ignore_installed:
                                #don't uninstall conflict if user install and and conflict is not user install
                                if not (self.use_user_site and not dist_in_usersite(req_to_install.satisfied_by)):
                                    req_to_install.conflicts_with = req_to_install.satisfied_by
                                req_to_install.satisfied_by = None
                            else:
                                install = False
                if not is_bundle:
                    ## FIXME: shouldn't be globally added:
                    finder.add_dependency_links(req_to_install.dependency_links)
                    if (req_to_install.extras):
                        logger.notify("Installing extra requirements: %r" % ','.join(req_to_install.extras))
                    if not self.ignore_dependencies:
                        for req in req_to_install.requirements(req_to_install.extras):
                            try:
                                name = pkg_resources.Requirement.parse(req).project_name
                            except ValueError:
                                e = sys.exc_info()[1]
                                ## FIXME: proper warning
                                logger.error('Invalid requirement: %r (%s) in requirement %s' % (req, e, req_to_install))
                                continue
                            if self.has_requirement(name):
                                ## FIXME: check for conflict
                                continue
                            subreq = InstallRequirement(req, req_to_install)
                            reqs.append(subreq)
                            self.add_requirement(subreq)
                        if req_to_install.editable and req_to_install.source_dir:
                            for subreq in self.install_requirements_txt(req_to_install):
                                if self.add_requirement(subreq):
                                    reqs.append(subreq)
                    if not self.has_requirement(req_to_install.name):
                        #'unnamed' requirements will get added here
                        self.add_requirement(req_to_install)
                    if self.is_download or req_to_install._temp_build_dir is not None:
                        self.reqs_to_cleanup.append(req_to_install)
                else:
                    self.reqs_to_cleanup.append(req_to_install)

                if install:
                    self.successfully_downloaded.append(req_to_install)
                    if bundle and (req_to_install.url and req_to_install.url.startswith('file:///')):
                        self.copy_to_build_dir(req_to_install)
            finally:
                logger.indent -= 2


    def add_requirement(self, install_req):
        name = install_req.name
        install_req.as_egg = self.as_egg
        install_req.use_user_site = self.use_user_site
        if not name:
            #url or path requirement w/o an egg fragment
            # make sure no list item has this same url:
            if install_req.url is None or len([i for i in self.unnamed_requirements if i.url == install_req.url]) == 0:
                self.unnamed_requirements.append(install_req)
            return True
        satisfied_by = self.install_req_checker.get_available_substitute(install_req)
        if satisfied_by is not None:
            logger.notify("Package %s already satisfied by %s" % (name, satisfied_by.__repr__()))
        else:
            self.requirements[name] = install_req
        for n in self.install_req_checker.get_all_aliases(name):
            self.requirement_aliases[n] = name
        return satisfied_by is None

    def install_requirements_txt(self, req_to_install):
        """If ENV is set, try to parse requirements-ENV.txt, falling back to requirements.txt if it exists."""
        rtxt_candidates = ["requirements.txt"]
        if self.options and self.options.env:
            rtxt_candidates.insert(0, "requirements-{0}.txt".format(self.options.env))
        for r in rtxt_candidates:
            fullpath = os.path.join(req_to_install.source_dir, r)
            if os.path.exists(fullpath):
                logger.notify("Found {0} in {1}, installing extra dependencies.".format(r, req_to_install.name))
                return parse_requirements(fullpath, req_to_install.name, None, self.options)
        return []

class RInstallCommand(InstallCommand):
    summary = 'Recursively install packages'

    def __init__(self, *args, **kw):
        super(RInstallCommand, self).__init__(*args, **kw)
        # Add env variable to specify which requirements.txt to run
        self.parser.add_option(
            '--env',
            dest='env',
            action='store',
            default=None,
            metavar='ENVIRONMENT',
            help='Specifies an environment (eg, production). This means requirements-ENV.txt will be evaluated by snakebasket.')
        self.parser.add_option(
            '--prefer-pinned-revision',
            dest='prefer_pinned_revision',
            action='store_true',
            default=False,
            help='When comparing editables with explicitly given version with the default (no-version data in URL), use the pinned version.')


    def run(self, options, args):
        if options.download_dir:
            options.no_install = True
            options.ignore_installed = True
        options.build_dir = os.path.abspath(options.build_dir)
        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
            if virtualenv_no_global():
                raise InstallationError("Can not perform a '--user' install. User site-packages are not visible in this virtualenv.")
            install_options.append('--user')
        if options.target_dir:
            options.ignore_installed = True
            temp_target_dir = tempfile.mkdtemp()
            options.target_dir = os.path.abspath(options.target_dir)
            if os.path.exists(options.target_dir) and not os.path.isdir(options.target_dir):
                raise CommandError("Target path exists but is not a directory, will not continue.")
            install_options.append('--home=' + temp_target_dir)
        global_options = options.global_options or []
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        finder = self._build_package_finder(options, index_urls)

        requirement_set = RecursiveRequirementSet(
            build_dir=options.build_dir,
            src_dir=options.src_dir,
            download_dir=options.download_dir,
            download_cache=options.download_cache,
            upgrade=options.upgrade,
            as_egg=options.as_egg,
            ignore_installed=options.ignore_installed,
            ignore_dependencies=options.ignore_dependencies,
            force_reinstall=options.force_reinstall,
            use_user_site=options.use_user_site)
        requirement_set.set_options(options)
        for name in args:
            requirement_set.add_requirement(
                InstallRequirement.from_line(name, None))
        for name in options.editables:
            requirement_set.add_requirement(
                InstallRequirement.from_editable(name, default_vcs=options.default_vcs))
        for filename in options.requirements:
            for req in parse_requirements(filename, finder=finder, options=options):
                requirement_set.add_requirement(req)
        if not requirement_set.has_requirements:
            if args or options.editables or options.requirements:
                msg = 'All requirements seem to be already satisfied.'
                logger.notify(msg)
            else:
                opts = {'name': self.name}
                if options.find_links:
                    msg = ('You must give at least one valid requirement to %(name)s '
                           '(maybe you meant "pip %(name)s %(links)s"?)' %
                           dict(opts, links=' '.join(options.find_links)))
                else:
                    msg = ('You must give at least one valid requirement '
                           'to %(name)s (see "pip help %(name)s")' % opts)
                logger.warn(msg)

            return

        if (options.use_user_site and
            sys.version_info < (2, 6)):
            raise InstallationError('--user is only supported in Python version 2.6 and newer')

        import setuptools
        if (options.use_user_site and
            requirement_set.has_editables and
            not getattr(setuptools, '_distribute', False)):

            raise InstallationError('--user --editable not supported with setuptools, use distribute')

        if not options.no_download:
            requirement_set.prepare_files(finder, force_root_egg_info=self.bundle, bundle=self.bundle)
        else:
            requirement_set.locate_files()

        if not options.no_install and not self.bundle:
            requirement_set.install(install_options, global_options, root=options.root_path)
            installed = ' '.join([req.name for req in
                                  requirement_set.successfully_installed])
            if installed:
                logger.notify('Successfully installed %s' % installed)
        elif not self.bundle:
            downloaded = ' '.join([req.name for req in
                                   requirement_set.successfully_downloaded])
            if downloaded:
                logger.notify('Successfully downloaded %s' % downloaded)
        elif self.bundle:
            requirement_set.create_bundle(self.bundle_filename)
            logger.notify('Created bundle in %s' % self.bundle_filename)
            # Clean up
        if not options.no_install or options.download_dir:
            requirement_set.cleanup_files(bundle=self.bundle)
        if options.target_dir:
            if not os.path.exists(options.target_dir):
                os.makedirs(options.target_dir)
            lib_dir = home_lib(temp_target_dir)
            for item in os.listdir(lib_dir):
                shutil.move(
                    os.path.join(lib_dir, item),
                    os.path.join(options.target_dir, item)
                )
            shutil.rmtree(temp_target_dir)
        return requirement_set
########NEW FILE########
__FILENAME__ = main
import sys
from pip import main as pip_main

def main(*args, **kwargs):
    install_pip_patches()
    return pip_main(*args, **kwargs)

def install_pip_patches():
    from snakebasket.commands import install
    sys.modules['pip'].commands['install'] = install.RInstallCommand
    return
    import pip.vcs.git
    from patches import patched_git_get_src_requirement
    sys.modules['pip.vcs.git'].Git.get_src_requirement = patched_git_get_src_requirement
########NEW FILE########
__FILENAME__ = patches

def patched_git_get_tag_revs(s, location):
    tags = s._get_all_tag_names(location)
    tag_revs = {}
    for line in tags.splitlines():
        tag = line.strip()
        rev = patched_git_get_revision_from_rev_parse(s, tag, location)
        tag_revs[tag] = rev.strip()
    return tag_revs

def patched_git_get_revision_from_rev_parse(s, name, location):
    from pip import call_subprocess
    ret = call_subprocess([s.cmd, 'show-ref', '--dereference', name],
        show_stdout=False, cwd=location)
    ret = ret.splitlines()[-1].split(" ")[0]
    return ret

def patched_git_get_src_requirement(self, dist, location, find_tags):
    repo = self.get_url(location)
    if not repo.lower().startswith('git:'):
        repo = 'git+' + repo
    egg_project_name = dist.egg_name().split('-', 1)[0]
    if not repo:
        return None
    current_rev = self.get_revision(location)
    tag_revs = patched_git_get_tag_revs(self, location)
    branch_revs = self.get_branch_revs(location)
    tag_name = None

    inverse_tag_revs = dict((tag_revs[key], key) for key in tag_revs.keys())
    if current_rev in inverse_tag_revs:
        # It's a tag
        tag_name = inverse_tag_revs[current_rev]
        full_egg_name = '%s' % (egg_project_name)
    elif (current_rev in branch_revs and
          branch_revs[current_rev] != 'origin/master'):
        # It's the head of a branch
        full_egg_name = '%s-%s' % (egg_project_name,
                                   branch_revs[current_rev].replace('origin/', ''))
    else:
        full_egg_name = '%s-dev' % egg_project_name

    return '%s@%s#egg=%s' % (repo, tag_name or current_rev, full_egg_name)
########NEW FILE########
__FILENAME__ = versions
"""
This file defines how versions of packages are compared.
Currently supported:
- comparing versions of editable (VCS) packages (if they're stored in git).
- comparing versions of non-editable packages.
Mixing the two results in the editable package always winning.

pip maintains a requirement set when processing a list of requirements to install.
When pip encounters a new requirement (by finding another requirements.txt for example),
that requirement is added to the requirement set. One by one, pip takes an element off the
requirement_set and installs it, adding any new dependencies to the requirement set if necessary.

The installation process is split into two steps. First, all packages and their dependencies are
downloaded. In the second step, the downloaded packages are all installed.

As pip moves through the process, packages can be:
* already installed before pip even started
* queued to be downloaded (in the requirement_set in pip lingo)
* already downloaded, but not yet installed
* just installed in this pip session
"""
from pip.exceptions import InstallationError
import re
from pip.util import call_subprocess
from pip.log import logger
import subprocess
import os, re, io
from pip.exceptions import InstallationError
from pip.vcs import subversion, git, bazaar, mercurial
import pkg_resources
from distutils.version import StrictVersion, LooseVersion
import itertools
import sys

__InstallationErrorMessage__ = 'Cannot be upgraded due to uncommitted git modifications'

class SeparateBranchException(Exception):
    def __init__(self, *args, **kwargs):
        self.candidates = args


class GitVersionComparator(object):

    LT = -1
    EQ = 0
    GT = 1
    version_re = re.compile(r'@([^/#@]*)#')
    commit_hash_re = re.compile("[a-z0-9]{5,40}")

    def __init__(self, pkg_repo_dir, prefer_pinned_revision=False):
        self.checkout_dir = pkg_repo_dir
        self.prefer_pinned_revision = prefer_pinned_revision

    def compare_versions(self, ver1, ver2):
        # short-circuit the comparison in the trivial case
        if ver1 == ver2:
            return self.EQ
        response = None
        versions = [ver1, ver2]
        # Both versions can't be None, because would would have already returned self.EQ then.
        pinned_versions = [v for v in versions if v is not None]
        if len(pinned_versions) == 1 and self.prefer_pinned_revision:
            versions = [pinned_versions[0], pinned_versions[0]]
        else:
            versions = ["HEAD" if v is None else v for v in versions]
        commithashes = [ver if self.is_valid_commit_hash(ver) else self.get_commit_hash_of_version_string(ver) for ver in versions]
        if commithashes[0] == commithashes[1]:
            response = self.EQ
        elif self.is_parent_of(commithashes[0], commithashes[1]):
            response = self.LT
        elif self.is_parent_of(commithashes[1], commithashes[0]):
            response = self.GT
        if response is None:
            raise SeparateBranchException((ver1, commithashes[0]), (ver2, commithashes[1]))
        return response

    def is_valid_commit_hash(self, hash_candidate):
        if re.match(self.commit_hash_re, hash_candidate) is None:
            return False
        try:
            ret = call_subprocess(['git', 'log', '-n', '1', hash_candidate, '--pretty=oneline'],
                show_stdout=False, cwd=self.checkout_dir)
            return ret.split(" ")[0] == hash_candidate
        except InstallationError:
            # call_subprocess returns raises an InstallationError when the return value of a command is not 0.
            # In this case it just means the given commit is not in the git repo.
            return False

    @staticmethod
    def do_fetch(repodir):
        call_subprocess(['git', 'fetch', '-q'], cwd=repodir)

    @staticmethod
    def do_checkout(remote_repository, checkout_dir, revision):
        git.Git(remote_repository).switch(checkout_dir, remote_repository, revision)

    # copied from tests/local_repos.py
    @staticmethod
    def checkout_pkg_repo(remote_repository, checkout_dir):
        vcs_classes = {'svn': subversion.Subversion,
                       'git': git.Git,
                       'bzr': bazaar.Bazaar,
                       'hg': mercurial.Mercurial}
        default_vcs = 'svn'
        if '+' not in remote_repository:
            remote_repository = '%s+%s' % (default_vcs, remote_repository)
        vcs, repository_path = remote_repository.split('+', 1)
        vcs_class = vcs_classes[vcs]
        vcs_class(remote_repository).obtain(checkout_dir)
        return checkout_dir

    @classmethod
    def get_version_string_from_url(cls, req_url):
        """Extract editable requirement version from it's URL. A version is a git object (commit hash, tag or branch). """
        version = cls.version_re.search(req_url)
        if version is not None and len(version.groups()) == 1:
            version_string = version.groups()[0]
            if len(version_string) > 0:
                return version_string
        return None

    def get_commit_hash_of_version_string(self, version_string):
        ret = call_subprocess(['git', 'show-ref', '--dereference', version_string],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.splitlines()[-1].split(" ")[0]

    def is_parent_of(self, parent, child):
        ret = call_subprocess(['git', 'merge-base', parent, child],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.rstrip() == parent


class PackageData(object):

    # states
    UNKNOWN = 0
    PREINSTALLED = 1
    SELECTED = 2
    OBTAINED = 3

    def __init__(self, name, url=None, editable=False, location=None, version=None, comes_from=None, requirement=None):
        self.name = name
        self.url = url
        self.editable = editable
        self.location = location
        self.version = version
        self.comes_from = comes_from
        self.state = PackageData.UNKNOWN
        # The original InstallRequirement for FrozenRequirement from which this data was extracted
        self.requirement = requirement

    def __repr__(self):
        str = "%s %s" % (
            "(unnamed package)" if self.name is None else self.name,
            "(no version)" if self.version is None else "(version %s)" % self.version
        )
        if self.url is not None:
            str = str + " from %s" % self.url
        if self.editable:
            str = str + " [Editable]"
        return str

    def __cmp__(self, other):
        if self.version is None or other.version is None:
            # cannot compare None version
            raise Exception("Unable to compare None versions")
        try:
            sv = StrictVersion()
            sv.parse(self.version)
            return sv.__cmp__(other.version)
        except Exception:
            return LooseVersion(self.version).__cmp__(LooseVersion(other.version))

    def clone_dir(self, src_dir):
        # This method should only be run on editable InstallRequirement objects.
        if self.requirement is not None and hasattr(self.requirement, "build_location"):
            return self.requirement.build_location(src_dir)
        raise Exception("Cant't find build_location")

    @classmethod
    def from_dist(cls, dist, pre_installed=False):
        # dist is either an InstallRequirement or a FrozenRequirement.
        # We have to deal with installs from a URL (no name), pypi installs (with and without explicit versions)
        # and editable installs from git.
        name = None if not hasattr(dist, 'name') else dist.name
        editable = False if not hasattr(dist, 'editable') else dist.editable
        comes_from = None if not hasattr(dist, 'comes_from') else dist.comes_from
        url = None
        location = None
        version = None

        if comes_from is None and pre_installed:
            comes_from = "[already available]"

        if hasattr(dist, 'req'):
            if type(dist.req) == str:
                url = dist.req
                version = GitVersionComparator.get_version_string_from_url(url)
            elif hasattr(dist.req, 'specs') and len(dist.req.specs) == 1 and len(dist.req.specs[0]) == 2 and dist.req.specs[0][0] == '==':
                version = dist.req.specs[0][1]
        if url is None and hasattr(dist, 'url'):
            url = dist.url
        if hasattr(dist, 'location'):
            location = dist.location
        elif name is not None and url is not None and editable:
            location_candidate = os.path.join(sys.prefix, 'src', dist.name, '.git')
            if os.path.exists(location_candidate):
                location = location_candidate
                if hasattr(dist, 'url') and dist.url:
                    version = GitVersionComparator.get_version_string_from_url(dist.url)
                if version is None:
                    ret = call_subprocess(['git', 'log', '-n', '1', '--pretty=oneline'], show_stdout=False, cwd=location)
                    version = ret.split(" ")[0]
        pd = cls(
            name=name,
            url=url,
            location=location,
            editable=editable,
            version=version,
            comes_from=comes_from,
            requirement=dist)
        if pre_installed:
            pd.state = PackageData.PREINSTALLED
        return pd


class InstallReqChecker(object):

    def __init__(self, src_dir, requirements, successfully_downloaded):
        self.src_dir = src_dir
        self.comparison_cache = ({}, {})  # two maps, one does a->b, the other one does b->a
        self.pre_installed = {}  # maps name -> PackageData
        self.repo_up_to_date = {}  # maps local git clone path -> boolean
        self.requirements = requirements
        self.successfully_downloaded = successfully_downloaded
        try:
            self.load_installed_distributions()
        except Exception, e:
            logger.notify("Exception loading installed distributions " + str(e))
            raise
        self.prefer_pinned_revision = False

    def load_installed_distributions(self):
        import pip
        from pip.util import get_installed_distributions
        for dist in get_installed_distributions(local_only=True, skip=[]):
            dist_as_req = dist.as_requirement()
            # if pip patches an earlier version of setuptools as distribute, skip it
            if (dist_as_req.project_name == 'distribute' and dist_as_req.specs == []):
                continue
            pd = PackageData.from_dist(pip.FrozenRequirement.from_dist(dist, [], find_tags=True), pre_installed=True)
            if pd.editable and pd.location is not None:
                self.repo_up_to_date[pd.location] = False
            self.pre_installed[pd.name] = pd

    def checkout_if_necessary(self, pd):
        if pd.location is None:
            pd.location = GitVersionComparator.checkout_pkg_repo(pd.url, pd.clone_dir(self.src_dir))
            self.repo_up_to_date[pd.location] = True
        # self.repo_up_to_date[pd.location] is False if the git repo existed before this
        # snakebasket run, and has not yet been fetched (therefore may contain old data).
        elif self.repo_up_to_date.get(pd.location, True) == False:
            try:
                GitVersionComparator.do_fetch(pd.location)
                logger.notify("Not performing git fetch in pre-existing directory %s, because %s is already fetched" % (pd.location, pd.version))
            except:
                # Do a git fetch for repos which were not checked out recently.
                logger.notify("Performing git fetch in pre-existing directory %s" % pd.location)
                GitVersionComparator.do_fetch(pd.location)
                self.repo_up_to_date[pd.location] = True
        return pd.location

    def check_for_uncommited_git_changes(self, working_directory):

        # Check for modifications
        git_status = subprocess.Popen(['git', 'status', '-s'], cwd=working_directory, stdout=subprocess.PIPE)

        listed_modifications = git_status.stdout.read().splitlines()

        # Strip out non-source-controlled .egg-info directory
        egg_info_regex = re.compile('[.]egg-info/')
        actual_modifications = [change for change in listed_modifications if not egg_info_regex.search(change) ]
        number_of_changes = len(actual_modifications)

        # Return True if at least one modification has been made
        return (number_of_changes > 0)


    # Both directions are saved, but the outcome is the opposite, eg:
    # 0.1.2 vs 0.1.1 -> GT
    # 0.1.1 vs 0.1.2 -> LT
    def get_cached_comparison_result(self, a, b):
        if self.comparison_cache[0].has_key(a) and self.comparison_cache[0].get(a).has_key(b):
            return self.comparison_cache[0][a][b]
        if self.comparison_cache[1].has_key(a) and self.comparison_cache[1][a].has_key(b):
            return self.comparison_cache[1][a][b]
        return None

    def save_comparison_result(self, a, b, result):
        if not self.comparison_cache[0].has_key(a):
            self.comparison_cache[0][a] = {}
        self.comparison_cache[0][a][b] = result
        if not self.comparison_cache[1].has_key(b):
            self.comparison_cache[1][b] = {}
        self.comparison_cache[1][b][a] = result * -1

    def get_all_aliases(self, name):
        return [
            name,
            name.lower(),
            name.upper(),
            name.replace("-", "_"),
            name.replace("_", "-"),
            name[0].upper() + name[1:]]

    def filter_for_aliases(self, name, req_list):
        return

    def find_potential_substitutes(self, name):
        """
        Returns other versions of the given package in requirement/downloaded/installed states without examining their
        version.
        """
        aliases = self.get_all_aliases(name)
        for package_name in aliases:
            if package_name in self.requirements:
                return PackageData.from_dist(self.requirements[package_name])
        downloaded = list(itertools.chain(*[
            [r for r in self.successfully_downloaded if r.name == pkg_resources] for package_name in aliases]))
        if downloaded:
            return PackageData.from_dist(downloaded[0])
        for package_name in aliases:
            if self.pre_installed.has_key(package_name):
                return self.pre_installed[package_name]

    def get_available_substitute(self, install_req):
        """Find an available substitute for the given package.
           Returns a PackageData object.
        """
        global __InstallationErrorMessage__

        new_candidate_package_data = PackageData.from_dist(install_req)
        if new_candidate_package_data.name is None:
            # cannot find alternative versions without a name.
            return None

        existing_package_data = self.find_potential_substitutes(new_candidate_package_data.name)
        if existing_package_data is None:
            return None

        packages_in_conflict = [new_candidate_package_data, existing_package_data]
        editables = [p for p in packages_in_conflict if p.editable]
        if len(editables) == 2:

            local_editable_path = os.path.join(sys.prefix, 'src', existing_package_data.name)
            if os.path.isdir(local_editable_path):

                if self.check_for_uncommited_git_changes(local_editable_path):                    
                    raise InstallationError("{message}. In path: {path}".format(
                                            message=__InstallationErrorMessage__,
                                            path=local_editable_path))

            # This is an expensive comparison, so let's cache results
            competing_version_urls = [str(r.url) for r in packages_in_conflict]
            cmp_result = self.get_cached_comparison_result(*competing_version_urls)
            if cmp_result is None:
                # We're comparing two versions of an editable because we know we're going to use the software in
                # the given repo (its just the version that's not decided yet).
                # So let's check out the repo into the src directory. Later (when we have the version) update_editable
                # will use the correct version anyway.
                repo_dir = self.checkout_if_necessary(new_candidate_package_data)
                cmp = GitVersionComparator(repo_dir, self.prefer_pinned_revision)
                try:
                    versions = [GitVersionComparator.get_version_string_from_url(r.url) for r in packages_in_conflict]
                    if len([v for v in versions if v == None]) == 2:
                        # if either the existing requirement or the new candidate has no version info and is editable,
                        # we better update our clone and re-run setup.
                        return existing_package_data  # OPTIMIZE return with the installed version
                    cmp_result = cmp.compare_versions(*versions)

                    self.save_comparison_result(competing_version_urls[0], competing_version_urls[1], cmp_result)
                except SeparateBranchException, exc:
                    raise InstallationError(
                        "%s: Conflicting versions cannot be compared as they are not direct descendants according to git. Exception: %s, Package data: %s." % (
                        new_candidate_package_data.name,
                        str([p.__dict__ for p in packages_in_conflict]),
                        str(exc.args)))
            else:
                logger.debug("using cached comparison: %s %s -> %s" % (competing_version_urls[0], competing_version_urls[1], cmp_result))
            return None if cmp_result == GitVersionComparator.GT else existing_package_data
        elif len(editables) == 0:
            versioned_packages = [p for p in packages_in_conflict if p.version is not None]
            if len(versioned_packages) == 0:
                if new_candidate_package_data.url == existing_package_data.url:
                    # It doesn't matter which InstallationRequirement object we use, they represent the same dependency.
                    return existing_package_data
                else:
                    raise InstallationError("%s: Package installed with no version information from different urls: %s and %s" % (new_candidate_package_data.name, new_candidate_package_data.url, existing_package_data.url))
            elif len(versioned_packages) == 1:

                # if the package to be installed is the versioned package
                if(new_candidate_package_data is versioned_packages[0]):
                    return None if self.prefer_pinned_revision else existing_package_data

                # else the versioned package is the one already installed
                else:
                    return existing_package_data if self.prefer_pinned_revision else None

            else:
                return None if new_candidate_package_data > existing_package_data else existing_package_data
        else:  # mixed case
            logger.notify("Conflicting requirements for %s, using editable version" % install_req.name)
            return editables[0]

########NEW FILE########
__FILENAME__ = excluded_tests
excluded_tests = [
    # Temporarily excluded until migrated to pip 1.3.x
    '-e', 'test_uninstall_namespace_package',
    # Pip tests excluded because of changed mirror architecture, we're using a pip too old for that
    '-e', 'test_install_from_mirrors',
    '-e', 'test_sb_install_from_mirrors_with_specific_mirrors',
    # Excluded because snakebasket doesn't support Mercurial nor Subversion
    '-e', 'test_install_editable_from_hg',
    '-e', 'test_cleanup_after_install_editable_from_hg',
    '-e', 'test_freeze_mercurial_clone',
    '-e', 'test_install_dev_version_from_pypi',
    '-e', 'test_obtain_should_recognize_auth_info_in_url',
    '-e', 'test_export_should_recognize_auth_info_in_url',
    '-e', 'test_install_subversion_usersite_editable_with_setuptools_fails',
    '-e', 'test_vcs_url_final_slash_normalization',
    '-e', 'test_install_global_option_using_editable',
    '-e', 'test_install_editable_from_svn',
    '-e', 'test_download_editable_to_custom_path',
    '-e', 'test_editable_no_install_followed_by_no_download',
    '-e', 'test_create_bundle',
    '-e', 'test_cleanup_after_create_bundle',
    '-e', 'test_freeze_svn',
    '-e', 'test_multiple_requirements_files',
    '-e', 'test_uninstall_editable_from_svn',
    '-e', 'test_uninstall_from_reqs_file',
    '-e', 'test_install_subversion_usersite_editable_with_distribute',
    '-e', 'test_freeze_bazaar_clone',
    # Pip tests excluded because of different functionality in snakebasket  
    '-e', 'test_install_from_mirrors_with_specific_mirrors',
    '-e', 'test_no_upgrade_unless_requested',
    '-e', 'test_upgrade_to_specific_version',
    '-e', 'test_install_user_conflict_in_globalsite',
    '-e', 'test_install_user_conflict_in_globalsite_and_usersite',
    '-e', 'test_install_user_conflict_in_usersite',
    '-e', 'test_upgrade_user_conflict_in_globalsite',
    '-e', 'test_install_user_in_global_virtualenv_with_conflict_fails',
    # Pip tests excluded because of incompatibility with current `pip search` results format  
    '-e', 'test_search',
    '-e', 'test_multiple_search'
]

########NEW FILE########
__FILENAME__ = git_submodule_helpers
../pip/tests/git_submodule_helpers.py
########NEW FILE########
__FILENAME__ = local_repos
../pip/tests/local_repos.py
########NEW FILE########
__FILENAME__ = path
../pip/tests/path.py
########NEW FILE########
__FILENAME__ = pypi_server
../pip/tests/pypi_server.py
########NEW FILE########
__FILENAME__ = runtests
import email
import os
import sys
import xmlrpclib
from pkg_resources import load_entry_point
import nose.tools

def add_dir_to_pythonpath(d):
    sys.path.insert(0, d)

# remove site-packages pip from python path and sys.modules
import re
mre = re.compile(".*pip.*")
sys.modules = dict((k,v) for k,v in sys.modules.iteritems() if re.match(mre, k) is None)
dre = re.compile(".*site-packages/pip-.*")
sys.path = [d for d in sys.path if re.match(dre, d) is None]

import nose.selector
def patched_getpackage(filename):
    return os.path.splitext(os.path.basename(filename))[0]
sys.modules['nose.selector'].getpackage = patched_getpackage
if __name__ == '__main__':

    import excluded_tests

    sys.argv.extend(excluded_tests.excluded_tests)
    sys.exit(
        load_entry_point('nose==1.2.1', 'console_scripts', 'nosetests')()
    )

########NEW FILE########
__FILENAME__ = test_all_pip
../pip/tests/test_all_pip.py
########NEW FILE########
__FILENAME__ = test_basic
../pip/tests/test_basic.py
########NEW FILE########
__FILENAME__ = test_bundle
../pip/tests/test_bundle.py
########NEW FILE########
__FILENAME__ = test_cleanup
../pip/tests/test_cleanup.py
########NEW FILE########
__FILENAME__ = test_compat
../pip/tests/test_compat.py
########NEW FILE########
__FILENAME__ = test_completion
../pip/tests/test_completion.py
########NEW FILE########
__FILENAME__ = test_config
../pip/tests/test_config.py
########NEW FILE########
__FILENAME__ = test_download
../pip/tests/test_download.py
########NEW FILE########
__FILENAME__ = test_extras
../pip/tests/test_extras.py
########NEW FILE########
__FILENAME__ = test_finder
../pip/tests/test_finder.py
########NEW FILE########
__FILENAME__ = test_find_links
../pip/tests/test_find_links.py
########NEW FILE########
__FILENAME__ = test_freeze
../pip/tests/test_freeze.py
########NEW FILE########
__FILENAME__ = test_hashes
../pip/tests/test_hashes.py
########NEW FILE########
__FILENAME__ = test_help
../pip/tests/test_help.py
########NEW FILE########
__FILENAME__ = test_index
../pip/tests/test_index.py
########NEW FILE########
__FILENAME__ = test_install_requirement
../pip/tests/test_install_requirement.py
########NEW FILE########
__FILENAME__ = test_list
../pip/tests/test_list.py
########NEW FILE########
__FILENAME__ = test_locations
../pip/tests/test_locations.py
########NEW FILE########
__FILENAME__ = test_pip
#!/usr/bin/env python
import os
import sys
import re
import tempfile
import shutil
import glob
import atexit
import textwrap
import site
import imp

from scripttest import TestFileEnvironment, FoundDir
from tests.path import Path, curdir, u

pyversion = sys.version[:3]
# the directory containing all the tests
here = Path(__file__).abspath.folder
# the directory containing all the tests
src_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../pip'))

# the root of this pip source distribution
download_cache = tempfile.mkdtemp(prefix='pip-test-cache')
site_packages_suffix = site.USER_SITE[len(site.USER_BASE) + 1:]

# Tweak the path so we can find up-to-date pip sources
# (http://bitbucket.org/ianb/pip/issue/98)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pip'))

from pip.util import rmtree

def path_to_url(path):
    """
    Convert a path to URI. The path will be made absolute and
    will not have quoted path parts.
    (adapted from pip.util)
    """
    path = os.path.normpath(os.path.abspath(path))
    drive, path = os.path.splitdrive(path)
    filepath = path.split(os.path.sep)
    url = '/'.join(filepath)
    if drive:
        return 'file:///' + drive + url
    return 'file://' +url


def demand_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path)




def create_virtualenv(where, distribute=False):
    import virtualenv
    if sys.version_info[0] > 2:
        distribute = True
    virtualenv.create_environment(
        where, use_distribute=distribute, unzip_setuptools=True)

    return virtualenv.path_locations(where)


def relpath(root, other):
    """a poor man's os.path.relpath, since we may not have Python 2.6"""
    prefix = root+Path.sep
    assert other.startswith(prefix)
    return Path(other[len(prefix):])

if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']


try:
    any
except NameError:

    def any(seq):
        for item in seq:
            if item:
                return True
        return False


def clear_environ(environ):
    return dict(((k, v) for k, v in environ.items()
                if not k.lower().startswith('pip_')))


def install_setuptools(env):
    easy_install = os.path.join(env.bin_path, 'easy_install')
    version = 'setuptools==0.6c11'
    if sys.platform != 'win32':
        return env.run(easy_install, version)

    tempdir = tempfile.mkdtemp()
    try:
        for f in glob.glob(easy_install+'*'):
            shutil.copy2(f, tempdir)
        return env.run(os.path.join(tempdir, 'easy_install'), version)
    finally:
        rmtree(tempdir)


env = None


def reset_env(environ=None, use_distribute=None, system_site_packages=False, sitecustomize=None):
    """Return a test environment.

    Keyword arguments:
    environ: an environ object to use.
    use_distribute: use distribute, not setuptools.
    system_site_packages: create a virtualenv that simulates --system-site-packages.
    sitecustomize: a string containing python code to add to sitecustomize.py.
    """

    global env
    # FastTestPipEnv reuses env, not safe if use_distribute specified
    if use_distribute is None and not system_site_packages:
        env = FastTestPipEnvironment(environ, sitecustomize=sitecustomize)
    else:
        env = TestPipEnvironment(environ, use_distribute=use_distribute, sitecustomize=sitecustomize)

    if system_site_packages:
        #testing often occurs starting from a private virtualenv (e.g. with tox)
        #from that context, you can't successfully use virtualenv.create_environment
        #to create a 'system-site-packages' virtualenv
        #hence, this workaround
        (env.lib_path/'no-global-site-packages.txt').rm()

    return env


class TestFailure(AssertionError):
    """

    An "assertion" failed during testing.

    """
    pass


#
# This cleanup routine prevents the __del__ method that cleans up the tree of
# the last TestPipEnvironment from firing after shutil has already been
# unloaded.  It also ensures that FastTestPipEnvironment doesn't leave an
# environment hanging around that might confuse the next test run.
#
def _cleanup():
    global env
    del env
    rmtree(download_cache, ignore_errors=True)
    rmtree(fast_test_env_root, ignore_errors=True)
    rmtree(fast_test_env_backup, ignore_errors=True)

atexit.register(_cleanup)


class TestPipResult(object):

    def __init__(self, impl, verbose=False):
        self._impl = impl

        if verbose:
            print(self.stdout)
            if self.stderr:
                print('======= stderr ========')
                print(self.stderr)
                print('=======================')

    def __getattr__(self, attr):
        return getattr(self._impl, attr)

    if sys.platform == 'win32':

        @property
        def stdout(self):
            return self._impl.stdout.replace('\r\n', '\n')

        @property
        def stderr(self):
            return self._impl.stderr.replace('\r\n', '\n')

        def __str__(self):
            return str(self._impl).replace('\r\n', '\n')
    else:
        # Python doesn't automatically forward __str__ through __getattr__

        def __str__(self):
            return str(self._impl)

    def assert_installed(self, pkg_name, with_files=[], without_files=[], without_egg_link=False, use_user_site=False):
        e = self.test_env

        pkg_dir = e.venv/ 'src'/ pkg_name.lower()

        if use_user_site:
            egg_link_path = e.user_site / pkg_name + '.egg-link'
        else:
            egg_link_path = e.site_packages / pkg_name + '.egg-link'
        if without_egg_link:
            if egg_link_path in self.files_created:
                raise TestFailure('unexpected egg link file created: '\
                                  '%r\n%s' % (egg_link_path, self))
        else:
            if not egg_link_path in self.files_created:
                raise TestFailure('expected egg link file missing: '\
                                  '%r\n%s' % (egg_link_path, self))

            egg_link_file = self.files_created[egg_link_path]

            if not (# FIXME: I don't understand why there's a trailing . here
                    egg_link_file.bytes.endswith('.')
                and egg_link_file.bytes[:-1].strip().endswith(pkg_dir)):
                raise TestFailure(textwrap.dedent(u('''\
                Incorrect egg_link file %r
                Expected ending: %r
                ------- Actual contents -------
                %s
                -------------------------------''' % (
                        egg_link_file,
                        pkg_dir + u('\n.'),
                        egg_link_file.bytes))))

        if use_user_site:
            pth_file = Path.string(e.user_site / 'easy-install.pth')
        else:
            pth_file = Path.string(e.site_packages / 'easy-install.pth')

        if (pth_file in self.files_updated) == without_egg_link:
            raise TestFailure('%r unexpectedly %supdated by install' % (
                pth_file, (not without_egg_link and 'not ' or '')))

        if (pkg_dir in self.files_created) == (curdir in without_files):
            raise TestFailure(textwrap.dedent('''\
            expected package directory %r %sto be created
            actually created:
            %s
            ''') % (
                Path.string(pkg_dir),
                (curdir in without_files and 'not ' or ''),
                sorted(self.files_created.keys())))

        for f in with_files:
            if not (pkg_dir/f).normpath in self.files_created:
                raise TestFailure('Package directory %r missing '\
                                  'expected content %f' % (pkg_dir, f))

        for f in without_files:
            if (pkg_dir/f).normpath in self.files_created:
                raise TestFailure('Package directory %r has '\
                                  'unexpected content %f' % (pkg_dir, f))


class TestPipEnvironment(TestFileEnvironment):
    """A specialized TestFileEnvironment for testing pip"""

    #
    # Attribute naming convention
    # ---------------------------
    #
    # Instances of this class have many attributes representing paths
    # in the filesystem.  To keep things straight, absolute paths have
    # a name of the form xxxx_path and relative paths have a name that
    # does not end in '_path'.

    # The following paths are relative to the root_path, and should be
    # treated by clients as instance attributes.  The fact that they
    # are defined in the class is an implementation detail

    # where we'll create the virtual Python installation for testing
    #
    # Named with a leading dot to reduce the chance of spurious
    # results due to being mistaken for the virtualenv package.
    venv = Path('.virtualenv')

    # The root of a directory tree to be used arbitrarily by tests
    scratch = Path('scratch')

    exe = sys.platform == 'win32' and '.exe' or ''

    verbose = False

    def __init__(self, environ=None, use_distribute=None, sitecustomize=None):

        self.root_path = Path(tempfile.mkdtemp('-piptest'))

        # We will set up a virtual environment at root_path.
        self.scratch_path = self.root_path / self.scratch

        self.venv_path = self.root_path / self.venv

        if not environ:
            environ = os.environ.copy()
            environ = clear_environ(environ)
            environ['PIP_DOWNLOAD_CACHE'] = str(download_cache)

        environ['PIP_NO_INPUT'] = '1'
        environ['PIP_LOG_FILE'] = str(self.root_path/'pip-log.txt')

        super(TestPipEnvironment, self).__init__(
            self.root_path, ignore_hidden=False,
            environ=environ, split_cmd=False, start_clear=False,
            cwd=self.scratch_path, capture_temp=True, assert_no_temp=True)

        demand_dirs(self.venv_path)
        demand_dirs(self.scratch_path)

        if use_distribute is None:
            use_distribute = os.environ.get('PIP_TEST_USE_DISTRIBUTE', False)
        self.use_distribute = use_distribute

        # Create a virtualenv and remember where it's putting things.
        virtualenv_paths = create_virtualenv(self.venv_path, distribute=self.use_distribute)

        assert self.venv_path == virtualenv_paths[0] # sanity check

        for id, path in zip(('venv', 'lib', 'include', 'bin'), virtualenv_paths):
            #fix for virtualenv issue #306
            if hasattr(sys, "pypy_version_info") and id == 'lib':
                path = os.path.join(self.venv_path, 'lib-python', pyversion)
            setattr(self, id+'_path', Path(path))
            setattr(self, id, relpath(self.root_path, path))

        assert self.venv == TestPipEnvironment.venv # sanity check

        if hasattr(sys, "pypy_version_info"):
            self.site_packages = self.venv/'site-packages'
        else:
            self.site_packages = self.lib/'site-packages'
        self.user_base_path = self.venv_path/'user'
        self.user_site_path = self.venv_path/'user'/site_packages_suffix

        self.user_site = relpath(self.root_path, self.user_site_path)
        demand_dirs(self.user_site_path)
        self.environ["PYTHONUSERBASE"] = self.user_base_path

        # create easy-install.pth in user_site, so we always have it updated instead of created
        open(self.user_site_path/'easy-install.pth', 'w').close()

        # put the test-scratch virtualenv's bin dir first on the PATH
        self.environ['PATH'] = Path.pathsep.join((self.bin_path, self.environ['PATH']))

        # test that test-scratch virtualenv creation produced sensible venv python
        result = self.run('python', '-c', 'import sys; print(sys.executable)')
        pythonbin = result.stdout.strip()

        if Path(pythonbin).noext != self.bin_path/'python':
            raise RuntimeError(
                "Oops! 'python' in our test environment runs %r"
                " rather than expected %r" % (pythonbin, self.bin_path/'python'))

        # make sure we have current setuptools to avoid svn incompatibilities
        if not self.use_distribute:
            install_setuptools(self)

        # Uninstall whatever version of pip came with the virtualenv.
        # Earlier versions of pip were incapable of
        # self-uninstallation on Windows, so we use the one we're testing.
        self.run('python', '-c',
                 '"import sys; sys.path.insert(0, %r); import pip; sys.exit(pip.main());"' % os.path.dirname(here),
                 'uninstall', '-vvv', '-y', 'pip')

        # Install this version instead
        self.run('python', 'setup.py', 'install', cwd=src_folder, expect_stderr=True)
        # Install snakebasket as well
        self.run('python', 'setup.py', 'install', cwd=os.path.abspath(os.path.join(src_folder, '../')), expect_stderr=True)

        #create sitecustomize.py and add patches
        self._create_empty_sitecustomize()
        self._use_cached_pypi_server()
        if sitecustomize:
            self._add_to_sitecustomize(sitecustomize)

        # Ensure that $TMPDIR exists  (because we use start_clear=False, it's not created for us)
        if self.temp_path and not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)

    def _ignore_file(self, fn):
        if fn.endswith('__pycache__') or fn.endswith(".pyc"):
            result = True
        else:
            result = super(TestPipEnvironment, self)._ignore_file(fn)
        return result

    def run(self, *args, **kw):
        if self.verbose:
            print('>> running %s %s' % (args, kw))
        cwd = kw.pop('cwd', None)
        run_from = kw.pop('run_from', None)
        assert not cwd or not run_from, "Don't use run_from; it's going away"
        cwd = Path.string(cwd or run_from or self.cwd)
        assert not isinstance(cwd, Path)
        return TestPipResult(super(TestPipEnvironment, self).run(cwd=cwd, *args, **kw), verbose=self.verbose)

    def __del__(self):
        rmtree(str(self.root_path), ignore_errors=True)

    def _use_cached_pypi_server(self):
        # previously, this was handled in a pth file, and not in sitecustomize.py
        # pth processing happens during the construction of sys.path.
        # 'import pypi_server' ultimately imports pkg_resources (which intializes pkg_resources.working_set based on the current state of sys.path)
        # pkg_resources.get_distribution (used in pip.req) requires an accurate pkg_resources.working_set
        # therefore, 'import pypi_server' shouldn't occur in a pth file.
        official_pip_tests_dir = os.path.abspath(os.path.join(str(here), '../pip/tests'))

        patch = """
            import sys
            sys.path.insert(0, %r)
            import pypi_server
            pypi_server.PyPIProxy.setup()
            sys.path.remove(%r)""" % (official_pip_tests_dir, official_pip_tests_dir)
        self._add_to_sitecustomize(patch)

    def _create_empty_sitecustomize(self):
        "Create empty sitecustomize.py."
        sitecustomize_path = self.lib_path / 'sitecustomize.py'
        sitecustomize = open(sitecustomize_path, 'w')
        sitecustomize.close()

    def _add_to_sitecustomize(self, snippet):
        "Adds a python code snippet to sitecustomize.py."
        sitecustomize_path = self.lib_path / 'sitecustomize.py'
        sitecustomize = open(sitecustomize_path, 'a')
        sitecustomize.write(textwrap.dedent('''
                               %s
        ''' %snippet))
        sitecustomize.close()

fast_test_env_root = here / 'tests_cache' / 'test_ws'
fast_test_env_backup = here / 'tests_cache' / 'test_ws_backup'


class FastTestPipEnvironment(TestPipEnvironment):
    def __init__(self, environ=None, sitecustomize=None):
        import virtualenv

        self.root_path = fast_test_env_root
        self.backup_path = fast_test_env_backup

        self.scratch_path = self.root_path / self.scratch

        # We will set up a virtual environment at root_path.
        self.venv_path = self.root_path / self.venv

        if not environ:
            environ = os.environ.copy()
            environ = clear_environ(environ)
            environ['PIP_DOWNLOAD_CACHE'] = str(download_cache)

        environ['PIP_NO_INPUT'] = '1'
        environ['PIP_LOG_FILE'] = str(self.root_path/'pip-log.txt')

        TestFileEnvironment.__init__(self,
            self.root_path, ignore_hidden=False,
            environ=environ, split_cmd=False, start_clear=False,
            cwd=self.scratch_path, capture_temp=True, assert_no_temp=True)

        virtualenv_paths = virtualenv.path_locations(self.venv_path)

        for id, path in zip(('venv', 'lib', 'include', 'bin'), virtualenv_paths):
            #fix for virtualenv issue #306
            if hasattr(sys, "pypy_version_info") and id == 'lib':
                path = os.path.join(self.venv_path, 'lib-python', pyversion)
            setattr(self, id+'_path', Path(path))
            setattr(self, id, relpath(self.root_path, path))

        assert self.venv == TestPipEnvironment.venv # sanity check

        if hasattr(sys, "pypy_version_info"):
            self.site_packages = self.venv/'site-packages'
        else:
            self.site_packages = self.lib/'site-packages'
        self.user_base_path = self.venv_path/'user'
        self.user_site_path = self.venv_path/'user'/'lib'/self.lib.name/'site-packages'

        self.user_site = relpath(self.root_path, self.user_site_path)

        self.environ["PYTHONUSERBASE"] = self.user_base_path

        # put the test-scratch virtualenv's bin dir first on the PATH
        self.environ['PATH'] = Path.pathsep.join((self.bin_path, self.environ['PATH']))

        self.use_distribute = os.environ.get('PIP_TEST_USE_DISTRIBUTE', False)

        if self.root_path.exists:
            rmtree(self.root_path)
        if self.backup_path.exists:
            shutil.copytree(self.backup_path, self.root_path, True)
        else:
            demand_dirs(self.venv_path)
            demand_dirs(self.scratch_path)

            # Create a virtualenv and remember where it's putting things.
            create_virtualenv(self.venv_path, distribute=self.use_distribute)

            demand_dirs(self.user_site_path)

            # create easy-install.pth in user_site, so we always have it updated instead of created
            open(self.user_site_path/'easy-install.pth', 'w').close()

            # test that test-scratch virtualenv creation produced sensible venv python
            result = self.run('python', '-c', 'import sys; print(sys.executable)')
            pythonbin = result.stdout.strip()

            if Path(pythonbin).noext != self.bin_path/'python':
                raise RuntimeError(
                    "Oops! 'python' in our test environment runs %r"
                    " rather than expected %r" % (pythonbin, self.bin_path/'python'))

            # make sure we have current setuptools to avoid svn incompatibilities
            if not self.use_distribute:
                install_setuptools(self)

            # Uninstall whatever version of pip came with the virtualenv.
            # Earlier versions of pip were incapable of
            # self-uninstallation on Windows, so we use the one we're testing.
            self.run('python', '-c',
                     '"import sys; sys.path.insert(0, %r); import pip; sys.exit(pip.main());"' % os.path.dirname(here),
                     'uninstall', '-vvv', '-y', 'pip')

            # Install this version instead
            self.run('python', 'setup.py', 'install', cwd=src_folder, expect_stderr=True)
            # Install snakebasket as well
            self.run('python', 'setup.py', 'install', cwd=os.path.abspath(os.path.join(src_folder, '../')), expect_stderr=True)
            # Backup up test dir
            shutil.copytree(self.root_path, self.backup_path, True)
        #create sitecustomize.py and add patches
        self._create_empty_sitecustomize()
        self._use_cached_pypi_server()
        if sitecustomize:
            self._add_to_sitecustomize(sitecustomize)

        assert self.root_path.exists

        # Ensure that $TMPDIR exists (because we use start_clear=False, it's not created for us)
        if self.temp_path and not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path)

    def __del__(self):
        pass # shutil.rmtree(str(self.root_path), ignore_errors=True)


def run_pip(*args, **kw):
    result = env.run('sb', *args, **kw)
    ignore = []
    for path, f in result.files_before.items():
        # ignore updated directories, often due to .pyc or __pycache__
        if (path in result.files_updated and
            isinstance(result.files_updated[path], FoundDir)):
            ignore.append(path)
    for path in ignore:
        del result.files_updated[path]
    import re
    # remove "snakebasket==1.0.0" from result.stdout
    result._impl.stdout = re.sub("snakebasket==[0-9a-zA-Z-_\.]*\n", '', result._impl.stdout)
    # replace "sb " with "pip "
    result._impl.args[0] = result._impl.args[0].replace('sb', 'pip')
    return result


def write_file(filename, text, dest=None):
    """Write a file in the dest (default=env.scratch_path)

    """
    env = get_env()
    if dest:
        complete_path = dest/ filename
    else:
        complete_path = env.scratch_path/ filename
    f = open(complete_path, 'w')
    f.write(text)
    f.close()


def mkdir(dirname):
    os.mkdir(os.path.join(get_env().scratch_path, dirname))


def get_env():
    if env is None:
        reset_env()
    return env


# FIXME ScriptTest does something similar, but only within a single
# ProcResult; this generalizes it so states can be compared across
# multiple commands.  Maybe should be rolled into ScriptTest?
def diff_states(start, end, ignore=None):
    """
    Differences two "filesystem states" as represented by dictionaries
    of FoundFile and FoundDir objects.

    Returns a dictionary with following keys:

    ``deleted``
        Dictionary of files/directories found only in the start state.

    ``created``
        Dictionary of files/directories found only in the end state.

    ``updated``
        Dictionary of files whose size has changed (FIXME not entirely
        reliable, but comparing contents is not possible because
        FoundFile.bytes is lazy, and comparing mtime doesn't help if
        we want to know if a file has been returned to its earlier
        state).

    Ignores mtime and other file attributes; only presence/absence and
    size are considered.

    """
    ignore = ignore or []

    def prefix_match(path, prefix):
        if path == prefix:
            return True
        prefix = prefix.rstrip(os.path.sep) + os.path.sep
        return path.startswith(prefix)

    start_keys = set([k for k in start.keys()
                      if not any([prefix_match(k, i) for i in ignore])])
    end_keys = set([k for k in end.keys()
                    if not any([prefix_match(k, i) for i in ignore])])
    deleted = dict([(k, start[k]) for k in start_keys.difference(end_keys)])
    created = dict([(k, end[k]) for k in end_keys.difference(start_keys)])
    updated = {}
    for k in start_keys.intersection(end_keys):
        if (start[k].size != end[k].size):
            updated[k] = end[k]
    return dict(deleted=deleted, created=created, updated=updated)


def assert_all_changes(start_state, end_state, expected_changes):
    """
    Fails if anything changed that isn't listed in the
    expected_changes.

    start_state is either a dict mapping paths to
    scripttest.[FoundFile|FoundDir] objects or a TestPipResult whose
    files_before we'll test.  end_state is either a similar dict or a
    TestPipResult whose files_after we'll test.

    Note: listing a directory means anything below
    that directory can be expected to have changed.
    """
    start_files = start_state
    end_files = end_state
    if isinstance(start_state, TestPipResult):
        start_files = start_state.files_before
    if isinstance(end_state, TestPipResult):
        end_files = end_state.files_after

    diff = diff_states(start_files, end_files, ignore=expected_changes)
    if list(diff.values()) != [{}, {}, {}]:
        raise TestFailure('Unexpected changes:\n' + '\n'.join(
            [k + ': ' + ', '.join(v.keys()) for k, v in diff.items()]))

    # Don't throw away this potentially useful information
    return diff


def _create_test_package(env):
    mkdir('version_pkg')
    version_pkg_path = env.scratch_path/'version_pkg'
    write_file('version_pkg.py', textwrap.dedent('''\
                                def main():
                                    print('0.1')
                                '''), version_pkg_path)
    write_file('setup.py', textwrap.dedent('''\
                        from setuptools import setup, find_packages
                        setup(name='version_pkg',
                              version='0.1',
                              packages=find_packages(),
                              py_modules=['version_pkg'],
                              entry_points=dict(console_scripts=['version_pkg=version_pkg:main']))
                        '''), version_pkg_path)
    env.run('git', 'init', cwd=version_pkg_path)
    env.run('git', 'add', '.', cwd=version_pkg_path)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'initial version', cwd=version_pkg_path)
    return version_pkg_path


def _change_test_package_version(env, version_pkg_path):
    write_file('version_pkg.py', textwrap.dedent('''\
        def main():
            print("some different version")'''), version_pkg_path)
    env.run('git', 'clean', '-qfdx', cwd=version_pkg_path, expect_stderr=True)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'messed version',
            cwd=version_pkg_path, expect_stderr=True)


def assert_raises_regexp(exception, reg, run, *args, **kwargs):
    """Like assertRaisesRegexp in unittest"""
    try:
        run(*args, **kwargs)
        assert False, "%s should have been thrown" %exception
    except Exception:
        e = sys.exc_info()[1]
        p = re.compile(reg)
        assert p.search(str(e)), str(e)

if __name__ == '__main__':
    sys.stderr.write("Run pip's tests using nosetests. Requires virtualenv, ScriptTest, mock, and nose.\n")
    sys.exit(1)

########NEW FILE########
__FILENAME__ = test_proxy
../pip/tests/test_proxy.py
########NEW FILE########
__FILENAME__ = test_requirements
../pip/tests/test_requirements.py
########NEW FILE########
__FILENAME__ = test_sb_basic
import re
import os
import filecmp
import textwrap
import sys
from os.path import abspath, join, curdir, pardir

from nose.tools import assert_raises

from pip.util import rmtree, find_command
from pip.exceptions import BadCommand

from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)

def test_sb_install_from_mirrors_with_specific_mirrors():
    """
    Test installing a package from a specific PyPI mirror.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--use-mirrors', '--mirrors', "http://b.pypi.python.org/", '--no-index', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)

########NEW FILE########
__FILENAME__ = test_sb_checkouts
from snakebasket import versions
from nose.tools import assert_equal, assert_raises
from pip.exceptions import InstallationError
from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from mock import Mock

# Only planned tests in this file right now

def test_pre_existing_editable_dir_get_git_pull_before_use():
    """ Not implemented yet: pre-existing editable distributions should get a git fetch before use for comparisons """
    assert True

def test_update_pulls_on_existing_checkout():
    """ Not implemented yet: sb --upgrade will pull on existing repos, not create a new clone. """
    assert True

def test_pre_existing_clones_used():
    """ Not implemented yet: clones present in the virtualenv prior to sb install running are used by sb install for version comparison and installation. """
    assert True

########NEW FILE########
__FILENAME__ = test_sb_packagedata

########NEW FILE########
__FILENAME__ = test_sb_recursive_install
import re
import os
import filecmp
import textwrap
import sys
from os.path import abspath, join, curdir, pardir

from nose.tools import assert_raises
from mock import patch

from pip.util import rmtree, find_command
from pip.exceptions import BadCommand

from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from tests.path import Path

def test_install_requirements_txt_processed():
    """
    Test requirements.txt is installed from repository.
    Note that we only test git, since that's all we use.
    """
    reset_env()
    args = ['install']
    args.extend(['-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    result.assert_installed('pip-test-package', with_files=['.git'])

def test_install_requirements_with_env_processed():
    """
    Test requirements-ENV.txt is installed from repository if ENV is set and exists.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'local', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_install_requirements_recursive_env():
    """
    Test --env is propagated when installing requirements of requirements.
    """
    reset_env()
    args = ['install', '--env', 'local', '-e', 'git+http://github.com/prezi/sb-test-package.git@recursive-env-test#egg=recursive-env-test']
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('recursive-env-test', with_files=['.git'])
    result.assert_installed('sb-test-package', with_files=['.git'])
    result.assert_installed('pip-test-package', with_files=['.git'])
    # recursive-env-test's requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_install_requirements_with_env_processed_recursive():
    """
    Test requirements-ENV.txt is installed from repository if ENV is set and exists.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'local', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_git_with_editable_with_no_requirements_for_env():
    """
    Snakebasket should revert to using requirements.txt if --env is specified but
    requirements-ENV.txt is not found.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'badenv', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements.txt references 0.1.2 of pip-test-package
    assert 'Adding pip-test-package 0.1.2' in result.stdout

def test_reinstall_interrupted_install_with_missing_deps():
    """
    When the installation phase of an sb run is interrupted, some of the dependencies won't be installed
    Later, when sb runs again, it will refuse to reinstall the package claiming it's already install and up-to-date.
    The solution is to add the dependencies of the project to a file in the egg directory.
    To find the egg dir, do:
    import pkg_resources
    a = pkg_resources.AvailableDistributions()
    a['snakebasket'][0].egg_info
    """
    assert True


def test_non_editable_version_conflict_no_versions():
    """ STUB: Non-editable packages could potentially have
    no version information in the downloaded state.
    """
    assert True
########NEW FILE########
__FILENAME__ = test_sb_upgrade
from nose.tools import nottest, assert_raises
from tests.test_pip import (here, reset_env, run_pip, assert_all_changes,
                            write_file, pyversion, _create_test_package,
                            _change_test_package_version)
from tests.local_repos import local_checkout
from snakebasket import versions
import subprocess
import os, re, io

def test_no_upgrade_pypi_if_prefer_pinned():
    """
    No upgrade of pypi package if 1)--prefer-pinned-revision is True and 2) previously installed version is pinned.

    """
    reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install','--prefer-pinned-revision', 'INITools', expect_error=True)
    assert not result.files_created, 'pip install INITools upgraded when it should not have'

def test_upgrade_pypi_if_no_prefer_pinned():
    """
    Upgrade pypi package if 1)--prefer-pinned-revision is False (default) and 2) previously installed version is pinned.

    """
    env = reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install', 'INITools', expect_error=True)
    assert result.files_created, 'pip install --upgrade did not upgrade'
    assert env.site_packages/'INITools-0.1-py%s.egg-info' % pyversion not in result.files_created

def test_no_upgrade_editable_if_prefer_pinned():
    """
    No upgrade of editable if 1)--prefer-pinned-revision is True and 2) previously installed version is pinned.

    """
    reset_env()

    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')

    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url]

    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')

    args = ['install',
        '--prefer-pinned-revision',
        # unpinned newer version
        '-e', '%s#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})

    # worrysome_files_created are all files that aren't located in .git/, created by the comparison `git fetch`
    expected_files_regex = re.compile('[.]git')
    worrysome_files_created = [file_path for file_path in result.files_created.keys() if not expected_files_regex.search(file_path)]

    assert not worrysome_files_created, 'sb install sb-test-package upgraded when it should not have'

def test_upgrade_editable_if_no_prefer_pinned():
    """
    Upgrade editable if 1)--prefer-pinned-revision is False (default) and 2) previously installed version is pinned and not the latest version.

    """
    reset_env()

    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')

    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url]

    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')

    args = ['install',
        # unpinned newer version
        '-e', '%s#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})

    # worrysome_files_created are all files that aren't located in .git/, created by the comparison `git fetch`
    expected_files_regex = re.compile('[.]git')
    new_files_created = [file_path for file_path in result.files_created.keys() if not expected_files_regex.search(file_path)]

    # new_files_created should contain a file that appears in versions >=0.2.1, but not in 0.2.2
    assert new_files_created, 'sb install sb-test-package did not upgrade when it should have'

def test_no_upgrade_editable_if_uncommitted_change():
    """
    No upgrade of editable if there are uncommitted local changes.

    """
    env = reset_env()

    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')

    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url]

    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')

    # Make modification to an existing file
    with open(os.path.join(env.venv_path, 'src/sb-test-package', 'requirements.txt'), 'a') as file:
        file.write('local modification!') 

    # Attempt to install a new version
    args = ['install',
        # unpinned newer version
        '-e', '%s#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})
    assert versions.__InstallationErrorMessage__ in result.stdout

def test_no_upgrade_editable_if_uncommitted_new_file():
    """
    No upgrade of editable if there are uncommitted local changes.

    """
    env = reset_env()

    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')

    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url]

    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')

    # Create a new file that isn't in source control
    subprocess.Popen(['touch', 'new_file.txt'], cwd=os.path.join(env.venv_path, 'src/sb-test-package'), stdout=subprocess.PIPE)

    # Attempt to install a new version
    args = ['install',
        # unpinned newer version
        '-e', '%s#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})
    assert versions.__InstallationErrorMessage__ in result.stdout

    # # worrysome_files_created are all files that aren't located in .git/, created by the comparison `git fetch`
    # expected_files_regex = re.compile('[.]git')
    # worrysome_files_created = [file_path for file_path in result.files_created.keys() if not expected_files_regex.search(file_path)]

    # assert not worrysome_files_created, 'sb install sb-test-package upgraded when it should not have'

########NEW FILE########
__FILENAME__ = test_sb_versions
from snakebasket import versions
from nose.tools import assert_equal, assert_raises
from pip.exceptions import InstallationError
from pip.req import Requirements, InstallRequirement
from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from mock import Mock

def test_comparison():
    """ Comparison of version strings works for editable git repos """
    url_template = "git+http://github.com/prezi/sb-test-package.git@%s#egg=sb-test-package"
    test_project_name = "sb-test-package" 

    def make_install_req(ver=None):
        req = Mock()
        req.project_name = test_project_name
        if ver:
            req.url = url_template % str(ver)
            req.specs = [('==', ver)]
        else:
            req.url = url_template.replace('@','') % ''
            req.specs = []

        install_requirement = InstallRequirement(req, None, editable = True, url = req.url)

        return install_requirement

    reset_env()

    older_ver = '0.1'
    older_commit = '6e513083955aded92f1833ff460dc233062a7292'

    current_ver = '0.1.1'
    current_commit = 'bd814b468924af1d41e9651f6b0d4fe0dc484a1e'

    newer_ver = '0.1.2'
    newer_commit = '2204077f795580d2f8d6df82caee34126aaf87eb'

    head_alias = 'HEAD'
    master_alias = 'master'

    def new_req_checker(default_requirment):
        requirements = Requirements()
        requirements[default_requirment.name] = default_requirment
        checker = versions.InstallReqChecker('../sb-venv/source/%s' % test_project_name, requirements, [])
        return checker

    # version tags are compared as they should be:
    older_req = make_install_req(older_ver)
    current_req = make_install_req(current_ver)
    newer_req = make_install_req(newer_ver)

    checker = new_req_checker(current_req)

        # there should be an available substitute (current_req) for an older version
    assert_equal(
        current_ver,
        checker.get_available_substitute(older_req).version
    )
        # there souldn't be a substitute for a newer version 
    assert_equal(
        None,
        checker.get_available_substitute(newer_req)
    )

    # commit hashes are compared has they should be:
    older_req = make_install_req(older_commit)
    current_req = make_install_req(current_commit)
    newer_req = make_install_req(newer_commit)

    checker = new_req_checker(current_req)

        # there should be an available substitute (current_req) for an older version
    assert_equal(
        current_commit,
        checker.get_available_substitute(older_req).version
    )
        # there souldn't be a substitute for a newer version 
    assert_equal(
        None,
        checker.get_available_substitute(newer_req)
    )

    # different aliases of the same commit id appear to be equal:
    head_req = make_install_req(head_alias)
    master_req = make_install_req(master_alias)

    checker = new_req_checker(head_req)
    assert_equal(
        head_alias,
        checker.get_available_substitute(master_req).version
    )

    checker = new_req_checker(master_req)
    assert_equal(
        master_alias,
        checker.get_available_substitute(head_req).version
    )

    # Divergent branches should not be able to be compared
    def compare_two_different_branches():
        branch_a_req = make_install_req('test_branch_a')
        branch_b_req = make_install_req('test_branch_b')

        checker = new_req_checker(branch_a_req)
        checker.get_available_substitute(branch_b_req)

    assert_raises(InstallationError, compare_two_different_branches)

    # two unpinned versions of the same requirement should be equal:

    unpinned_req_1 = make_install_req()
    unpinned_req_2 = make_install_req()
    checker = new_req_checker(unpinned_req_1)

    assert checker.get_available_substitute(unpinned_req_2)

def test_requirement_set_will_include_correct_version():
    """ Out of two versions of the same package, the requirement set will contain the newer one. """
    reset_env()
    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')
    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url,
        # newer version
        '-e', '%s@0.2.1#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')
    v020 = 'sb-test-package 0.2.0'
    v021 = 'sb-test-package 0.2.1'
    assert not (v020 in result.stdout)
    assert v021 in result.stdout

def test_editable_reqs_override_pypi_packages():
    """ Not Implemented: If a conflicing editable and pypi package are given, the editable will be installed. """
    pass
########NEW FILE########
__FILENAME__ = test_search
../pip/tests/test_search.py
########NEW FILE########
__FILENAME__ = test_show
../pip/tests/test_show.py
########NEW FILE########
__FILENAME__ = test_ssl
../pip/tests/test_ssl.py
########NEW FILE########
__FILENAME__ = test_test
../pip/tests/test_test.py
########NEW FILE########
__FILENAME__ = test_unicode
../pip/tests/test_unicode.py
########NEW FILE########
__FILENAME__ = test_uninstall
../pip/tests/test_uninstall.py
########NEW FILE########
__FILENAME__ = test_upgrade
../pip/tests/test_upgrade.py
########NEW FILE########
__FILENAME__ = test_user_site
../pip/tests/test_user_site.py
########NEW FILE########
__FILENAME__ = test_util
../pip/tests/test_util.py
########NEW FILE########
__FILENAME__ = test_vcs_backends
../pip/tests/test_vcs_backends.py
########NEW FILE########
__FILENAME__ = test_vcs_bazaar
../pip/tests/test_vcs_bazaar.py
########NEW FILE########
__FILENAME__ = test_vcs_git
../pip/tests/test_vcs_git.py
########NEW FILE########
__FILENAME__ = test_vcs_subversion
../pip/tests/test_vcs_subversion.py
########NEW FILE########
