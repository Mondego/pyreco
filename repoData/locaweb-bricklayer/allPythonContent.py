__FILENAME__ = builder
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import re
import subprocess
import time
import ConfigParser
import shlex
import shutil
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.dirname(__file__))

from bricklayer.utils import pystache
import git

from twisted.internet import threads, reactor, defer
from config import BrickConfig
from projects import Projects

from builder_rpm import BuilderRpm
from builder_deb import BuilderDeb
from build_options import BuildOptions
from build_container import BuildContainer
from current_build import CurrentBuild

#from dreque import Dreque

config = BrickConfig()
redis_server = config.get('redis', 'redis-server')
log_file = config.get('log', 'file')

#queue = Dreque(redis_server)

logging.basicConfig(filename=log_file, level=logging.DEBUG)
log = logging.getLogger('builder')

@defer.inlineCallbacks
def build_project(kargs):
    builder = Builder(kargs['project'])
    kargs.pop('project')
    yield builder.build_project(**kargs)

class Builder(object):
    def __init__(self, project):
        self.project = Projects(project)
        self.templates_dir = BrickConfig().get('workspace', 'template_dir')
        self.git = git.Git(self.project)
        self.build_system = BrickConfig().get('build', 'system')
        self.build_options = BuildOptions(self.git.workdir)

        
        self.build_container = None
        self.workspace = "%s/%s" % (
            BrickConfig().get('workspace', 'dir'),
            self.project.name,
        )

        self.real_workspace = "%s/%s" % (
            BrickConfig().get('workspace', 'dir'), self.project.name
        )

        if self.build_system == 'rpm':
            self.mod_install_cmd = self.project.install_cmd.replace(
                'BUILDROOT', '%{buildroot}'
            )
        elif self.build_system == 'deb' or self.build_system == None:
            self.mod_install_cmd = self.project.install_cmd.replace(
                'BUILDROOT', 'debian/tmp'
            )            
        if not os.path.isdir(self.workspace):
            os.makedirs(self.workspace)

        if not os.path.isdir(os.path.join(self.workspace, 'log')):
            os.makedirs(os.path.join(self.workspace, 'log'))

        self.stdout = None
        self.stderr = self.stdout

    def _exec(self, cmd, *args, **kwargs):
        if True or self.build_options.not_found:
            return subprocess.Popen(cmd, *args, **kwargs)
        else:
            chroot_cmd = "chroot %s bash -c \"cd %s; %s\"" % (self.build_container.dir, self.real_workspace, " ".join(cmd))
            kwargs.update({'shell': True})
            kwargs["cwd"] = self.workdir
            return subprocess.Popen(chroot_cmd, *args, **kwargs)

    def build_project(self, branch=None, release=None, version=None, commit=None):

        if not self.project.is_building():
            self.project.start_building()
            try:
                if (release is not None and version is not None):
                    if (not self.git.pull()):
                        self.git.clone(branch)

                self.workdir = "%s-%s" % (self.git.workdir, release)
                self.real_workspace = "%s-%s" % (self.real_workspace, release)
                if (os.path.exists(self.workdir)):
                    shutil.rmtree(self.workdir, ignore_errors=True)
                shutil.copytree(self.git.workdir, self.workdir, True)

                if self.build_system == 'rpm':
                    self.package_builder = BuilderRpm(self)
                elif self.build_system == 'deb':
                    self.package_builder = BuilderDeb(self)

                # os.chdir(self.workdir)
                self.git.workdir = self.workdir
                self.git.checkout_branch(branch)

                if release == 'experimental' and self.build_options.changelog:
                    self.git.checkout_branch(branch)
                    self.package_builder.build(branch, release)
                    self.package_builder.upload(branch)
                if release != None and commit != None:
                    self.git.checkout_tag(commit)
                    self.package_builder.build(branch, force_version=version, force_release=release)
                    self.package_builder.upload(release)
                else:
                    self.project.last_tag(release, self.git.last_tag(release))
                    self.git.checkout_tag(self.project.last_tag(release))
                    self.package_builder.build(branch, self.project.last_tag(release))
                    self.package_builder.upload(release)
                self.git.checkout_branch('master')
            except Exception, e:
                log.exception("build failed: %s" % repr(e))
            finally:
                self.project.stop_building()
                # shutil.rmtree(self.workdir, ignore_errors=True)
                if self.build_container != None:
                    self.build_container.teardown()


########NEW FILE########
__FILENAME__ = builder_deb
import os
import sys
import shutil
import time
import re
import glob
import stat
import subprocess
import ftplib
import pystache
import logging
from urlparse import urlparse

from projects import Projects
from config import BrickConfig
from build_info import BuildInfo

log = logging.getLogger('builder')

class BuilderDeb():
    def __init__(self, builder):
        self.builder = builder
        self.project = self.builder.project
        log.info("Debian builder initialized: %s" % self.builder.workdir)
        log.info("Building [%s] with options: %s" % (
                self.project.name, 
                self.builder.build_options.options
                ))
    
    def configure_changelog(self, branch):
        template_data = {
                'name': self.project.name,
                'version': "%s" % (self.project.version(branch)),
                'build_cmd': self.project.build_cmd,
                'install_cmd': self.builder.mod_install_cmd,
                'username': self.project.username,
                'email': self.project.email,
                'date': time.strftime("%a, %d %h %Y %T %z"),
            }

        changelog = os.path.join(self.builder.workdir, 'debian', 'changelog')
        
        if hasattr(self.builder.build_options, 'changelog') and self.builder.build_options.changelog:
            if os.path.isfile(changelog):
                os.rename(changelog, "%s.save" % changelog)

            def read_file_data(f):
                with open(os.path.join(templates_dir, f)) as tmpfh:
                    templates[f] = pystache.template.Template(tmpfh.read()).render(context=template_data)

            if not os.path.isdir(self.debian_dir):

                map(read_file_data, ['changelog', 'control', 'rules'])

                os.makedirs( os.path.join(self.debian_dir, self.project.name, self.project.install_prefix))

                for filename, data in templates.iteritems():
                    with open(os.path.join(self.debian_dir, filename), 'w') as tmpfh:
                        tmpfh.write(data)

            changelog_entry = """%(name)s (%(version)s) %(branch)s; urgency=low

  * Latest commits
  %(commits)s

 -- %(username)s <%(email)s>  %(date)s
"""
            changelog_data = {
                    'name': self.project.name,
                    'version': self.project.version(branch),
                    'branch': branch,
                    'commits': '  '.join(self.builder.git.log()),
                    'username': self.project.username,
                    'email': self.project.email,
                    'date': time.strftime("%a, %d %h %Y %T %z"),
                }
            return (changelog_entry, changelog_data)

        else:
            return (None, None)

    def build_install_deps(self):
        p = self.builder._exec(["dpkg-checkbuilddeps"], stderr=subprocess.PIPE, close_fds=True)
        p.wait()
        out = p.stderr.read()
        if out != "":
            deps = re.findall("([a-z0-9\-]+\s|[a-z0-9\-]+$)", out.split("dependencies:")[1])
            deps = map(lambda x: x.strip(), deps)
            apt_cmd = "apt-get -y --force-yes install %s" % " ".join(deps)
            b = self.builder._exec(apt_cmd.split(), stdout=self.stdout, stderr=self.stderr, close_fds=True)
            b.wait()
            

    def build(self, branch, last_tag=None, force_version=None, force_release=None):
        templates = {}
        templates_dir = os.path.join(self.builder.templates_dir, 'deb')
        control_data_new = None

        self.build_info = BuildInfo(self.project.name)
        logfile = os.path.join(
                BrickConfig().get("workspace", "dir"), 'log', '%s.%s.log' % (
                    self.project.name, self.build_info.build_id
                    )
                )
        log.info("build log file: %s" % logfile)
        self.build_info.log(logfile)
        self.stdout = open(logfile, 'a+')
        self.stderr = self.stdout
        self.debian_dir = os.path.join(self.builder.workdir, 'debian')
        
        if last_tag is not None:
            os.environ.update({'BRICKLAYER_RELEASE': last_tag.split('_')[0]})
            os.environ.update({'BRICKLAYER_TAG': last_tag})

        # Not now
        #self.build_install_deps()

        if self.project.install_prefix is None:
            self.project.install_prefix = 'opt'

        if not self.project.install_cmd :
            self.project.install_cmd = 'cp -r \`ls | grep -v debian\` debian/tmp/%s' % (
                self.project.install_prefix
            )

        changelog_entry, changelog_data = self.configure_changelog(branch)

        if changelog_entry and changelog_data:
            if last_tag != None and last_tag.startswith('stable'):
                self.project.version('stable', last_tag.split('_')[1])
                changelog_data.update({'version': self.project.version('stable'), 'branch': 'stable'})
                self.build_info.version(self.project.version('stable'))
                self.build_info.release('stable')

            elif last_tag != None and last_tag.startswith('testing'):
                self.project.version('testing', last_tag.split('_')[1])
                changelog_data.update({'version': self.project.version('testing'), 'branch': 'testing'})
                self.build_info.version(self.project.version('testing'))
                self.build_info.release('testing')

            elif last_tag != None and last_tag.startswith('unstable'):
                self.project.version('unstable', last_tag.split('_')[1])
                changelog_data.update({'version': self.project.version('unstable'), 'branch': 'unstable'})
                self.build_info.version(self.project.version('unstable'))
                self.build_info.release('unstable')

            else:
                """
                otherwise it should change the distribution to experimental
                """
                version_list = self.project.version(branch).split('.')
                version_list[len(version_list) - 1] = str(int(version_list[len(version_list) - 1]) + 1)
                self.project.version(branch, '.'.join(version_list))
                
                changelog_data.update({'version': self.project.version(branch), 'branch': 'experimental'})
                self.build_info.version(self.project.version(branch))
                self.build_info.release('experimental:%s' % branch)
            
            with file(os.path.join(self.builder.workdir, 'debian', 'changelog'), 'w') as fh:
                fh.write(changelog_entry % changelog_data)

        else:
            self.build_info.version(force_version)
            self.build_info.release(force_release)
            self.project.version(branch, force_version)
            self.project.version(force_release, force_version)

        

        rvm_env = {}
        rvm_rc = os.path.join(self.builder.workdir, '.rvmrc')
        rvm_rc_example = rvm_rc +  ".example"
        has_rvm = False

        if os.path.isfile(rvm_rc):
            has_rvm = True
        elif os.path.isfile(rvm_rc_example):
            has_rvm = True
            rvm_rc = rvm_rc_example

        if has_rvm:
            with open(rvm_rc) as tmpfh:
                rvmexec = tmpfh.read()
            log.info("RVMRC: %s" % rvmexec)

            # I need the output not to log on file
            rvm_cmd = subprocess.Popen('/usr/local/rvm/bin/rvm info %s' % rvmexec.split()[1],
                    shell=True, stdout=subprocess.PIPE)
            rvm_cmd.wait()
            for line in rvm_cmd.stdout.readlines():
                if 'PATH' in line or 'HOME' in line:
                    name, value = line.split()
                    rvm_env[name.strip(':')] = value.strip('"')
            rvm_env['HOME'] = os.environ['HOME']

        if len(rvm_env.keys()) < 1:
            rvm_env = os.environ
        else:
            os_env = dict(os.environ)
            for k in ("PATH", "GEM_HOME", "BUNDLER_PATH"):
                if (k in os_env):
                    del(os_env[k])
            rvm_env.update(os_env)

	log.info(rvm_env)

        os.chmod(os.path.join(self.debian_dir, 'rules'), stat.S_IRWXU|stat.S_IRWXG|stat.S_IROTH|stat.S_IXOTH)
        dpkg_cmd = self.builder._exec(
                ['dpkg-buildpackage',  
                 '-rfakeroot', '-tc', '-k%s' % BrickConfig().get('gpg', 'keyid')],
                cwd=self.builder.workdir, env=rvm_env, stdout=self.stdout, stderr=self.stderr, close_fds=True)
        dpkg_cmd.wait()

        clean_cmd = self.builder._exec(['dh', 'clean'], 
                                       cwd=self.builder.workdir, 
                                       stdout=self.stdout, stderr=self.stderr, close_fds=True)
        clean_cmd.wait()


    def upload(self, branch):
        glob_str = '%s/%s_%s_*.changes' % (
                BrickConfig().get('workspace', 'dir'), 
                self.project.name, self.project.version(branch))
        changes_file = glob.glob(glob_str)
	log.info(changes_file)
        distribution, files = self.parse_changes(changes_file[0])

        try:
            self.upload_files(distribution, files)
            upload_file = changes_file[0].replace('.changes', '.upload')
            with open(upload_file, 'w') as tmpfh:
                tmpfh.write("done")
        except Exception, e:
            log.error("Package could not be uploaded: %s", e)

    def parse_changes(self, changes_file):
        with open(changes_file) as tmpfh:
            content = tmpfh.readlines()
        go = 0
        distribution = ""
        tmpfiles = [os.path.basename(changes_file)]
        for line in content:
            if line.startswith('Distribution'):
                distribution = line.strip('\n')
                distribution = distribution.split(':')[1].strip(' ')
            if line.startswith('File'):
                go = 1
            elif not line.startswith('\n') and go == 1:
                tmpname = line.split()
                pos = len(tmpname)
                tmpfiles.append(tmpname[pos-1])
            else:
                go = 0
        files = []
        for f in tmpfiles:
            filename = f.split()
            files.append(filename[len(filename) - 1])
	log.info(">>>>>")
	log.info(files)
        return distribution, files

    def local_repo(self, distribution, files):
        archive_conf_data = """Dir {
  ArchiveDir "%s/%s";
};

BinDirectory "dists/unstable" {
  Packages "dists/unstable/main/binary-amd64/Packages";
  SrcPackages "dists/unstable/main/source/Sources";
};

BinDirectory "dists/stable" {
  Packages "dists/stable/main/binary-amd64/Packages";
  SrcPackages "dists/stable/main/source/Sources";
};

BinDirectory "dists/testing" {
  Packages "dists/testing/main/binary-amd64/Packages";
  SrcPackages "dists/testing/main/source/Sources";
};

BinDirectory "dists/experimental" {
  Packages "dists/experimental/main/binary-amd64/Packages";
  SrcPackages "dists/experimental/main/source/Sources";
};"""
        repo_bin_path = os.path.join(BrickConfig().get("local_repo", "dir"), 
                self.project.group_name, 'dists/%s/main/binary-amd64/' % distribution)
        repo_src_path = os.path.join(BrickConfig().get("local_repo", "dir"), 
                self.project.group_name, 'dists/%s/main/source/' % distribution)

        archive_conf_file = os.path.join(
                BrickConfig().get("local_repo", "dir"), 
                self.project.group_name, 
                'archive.conf')

        if not os.path.isdir(repo_bin_path) or not os.path.isdir(repo_src_path):
            os.makedirs(repo_bin_path)
            os.makedirs(repo_src_path)

            if not os.path.isfile(archive_conf_file):
                with open(archive_conf_file, 'w') as tmpfh:
                    tmpfh.write(
                        archive_conf_data % (
                            BrickConfig().get("local_repo", "dir"), 
                            self.project.group_name
                        ))
        
        workspace = BrickConfig().get("workspace", "dir")
        for f in files:
            f = f.strip()
            if f.endswith('.dsc') or f.endswith('.tar.gz'):
                shutil.copy(os.path.join(workspace, f), os.path.join(repo_src_path, f))
            elif f.endswith('.deb'):
                shutil.copy(os.path.join(workspace, f), os.path.join(repo_bin_path, f))

        repo_base_path = os.path.join(BrickConfig().get('local_repo', 'dir'), self.project.group_name)
        

    def upload_files(self, distribution, files):
        repository_url, user, passwd = self.project.repository()
        if not repository_url:
            return 0
        # os.chdir(BrickConfig().get('workspace', 'dir'))
        workspace = BrickConfig().get('workspace', 'dir')
        ftp = ftplib.FTP(repository_url, user, passwd)
        try:
            ftp.cwd(distribution)
            for f in files:
                log.info("\t%s: " % os.path.join(workspace, f))
                with open(os.path.join(workspace, f), 'rb') as tmpfh:
                    ftp.storbinary("STOR %s" % f, tmpfh)
                log.info("done.")
        except Exception, e:
            log.info(repr(e))
        ftp.quit()

########NEW FILE########
__FILENAME__ = builder_rpm
import os
import sys
import shutil
import time
import re
import logging as log
import subprocess
import ftplib
import tarfile
import pystache

from projects import Projects
from config import BrickConfig
from build_info import BuildInfo

from git import Git
from glob import glob
from types import *

class BuilderRpm():

    def __init__(self, builder):
        self.builder = builder
        self.project = self.builder.project
        self.distribution = None
        self.version = None

    def dos2unix(self, file):
        f = open(file, 'r').readlines()
        new_file = open(file, "w+")
        match = re.compile('\r\n')
        for line in f:
            new_file.write(match.sub('\n', line))
        new_file.close()

    def build(self, branch, last_tag=None):
        templates_dir = os.path.join(self.builder.templates_dir, 'rpm')
        rpm_dir = os.path.join(self.builder.workdir, 'redhat')
        spec_filename = os.path.join(rpm_dir, 'SPECS', "%s.spec" % self.project.name)

        self.build_info = BuildInfo(self.project.name)
        logfile = os.path.join(self.builder.workspace, 'log', '%s.%s.log' % (self.project.name, self.build_info.build_id))
        self.build_info.log(logfile)
        self.stdout = open(logfile, 'a+')
        self.stderr = self.stdout

        if last_tag != None and last_tag.startswith('stable'):
            self.project.version('stable', last_tag.split('_')[1])
            self.build_info.version(self.project.version('stable'))
            self.version = self.project.version('stable')
            self.distribution = 'stable'

        elif last_tag != None and last_tag.startswith('testing'):
            self.project.version('testing', last_tag.split('_')[1])
            self.build_info.version(self.project.version('testing'))
            self.version = self.project.version('testing')
            self.distribution = 'testing'

        elif last_tag != None and last_tag.startswith('unstable'):
            self.project.version('unstable', last_tag.split('_')[1])
            self.build_info.version(self.project.version('unstable'))
            self.version = self.project.version('unstable')
            self.distribution = 'unstable'

        else:
            """
            otherwise it should change the distribution to unstable
            """
            if self.project.version(branch):
                version_list = self.project.version(branch).split('.')
                version_list[len(version_list) - 1] = str(int(version_list[len(version_list) - 1]) + 1)
                self.project.version(branch, '.'.join(version_list))
                self.build_info.version(self.project.version(branch))
                self.version = self.project.version(branch)
                self.distribution = 'experimental'

        dir_prefix = "%s-%s" % (self.project.name, self.version)

        for dir in ('SOURCES', 'SPECS', 'RPMS', 'SRPMS', 'BUILD', 'TMP'):
            if os.path.isdir(os.path.join(rpm_dir, dir)):
                shutil.rmtree(os.path.join(rpm_dir, dir))
            os.makedirs(os.path.join(rpm_dir, dir))

        build_dir = os.path.join(rpm_dir, 'TMP', self.project.name)
        os.makedirs(build_dir)

        if os.path.isdir(os.path.join(rpm_dir, dir_prefix)):
            shutil.rmtree(os.path.join(rpm_dir, dir_prefix))
        os.makedirs(os.path.join(rpm_dir, dir_prefix))

        subprocess.call(["cp -rP `ls -a | grep -Ev '\.$|\.\.$|debian$|redhat$'` %s" %
            os.path.join(rpm_dir, dir_prefix)],
            cwd=self.builder.workdir,
            shell=True
        )

        cur_dir = os.getcwd()
        os.chdir(rpm_dir)

        source_file = os.path.join(rpm_dir, 'SOURCES', '%s.tar.gz' % dir_prefix)
        tar = tarfile.open(source_file, 'w:gz')
        tar.add(dir_prefix)
        tar.close()
        shutil.rmtree(dir_prefix)
        os.chdir(cur_dir)

        if self.project.install_prefix is None:
            self.project.install_prefix = 'opt'

        if not self.project.install_cmd:

            self.project.install_cmd = 'cp -r \`ls -a | grep -Ev "\.$|\.\.$|debian$"\` %s/%s/%s' % (
                    build_dir,
                    self.project.install_prefix,
                    self.project.name
                )

        template_data = {
                'name': self.project.name,
                'version': self.version,
                'build_dir': build_dir,
                'build_cmd': self.project.build_cmd,
                'install_cmd': self.builder.mod_install_cmd,
                'username': self.project.username,
                'email': self.project.email,
                'date': time.strftime("%a %h %d %Y"),
                'git_url': self.project.git_url,
                'source': source_file,
            }

        rvm_rc = os.path.join(self.builder.workdir, '.rvmrc')
        rvm_rc_example = rvm_rc +  ".example"
        has_rvm = False

        environment = None

        if os.path.isfile(rvm_rc):
            has_rvm = True
        elif os.path.isfile(rvm_rc_example):
            has_rvm = True
            rvm_rc = rvm_rc_example

        if has_rvm:
            rvmexec = open(rvm_rc).read()
            log.info("RVMRC: %s" % rvmexec)

            # I need the output not to log on file
            rvm_cmd = subprocess.Popen('/usr/local/rvm/bin/rvm info %s' % rvmexec.split()[1],
                    shell=True, stdout=subprocess.PIPE)
            rvm_cmd.wait()

            rvm_env = {}
            for line in rvm_cmd.stdout.readlines():
                if 'PATH' in line or 'HOME' in line:
                    name, value = line.split()
                    rvm_env[name.strip(':')] = value.strip('"')
            rvm_env['HOME'] = os.environ['HOME']

            if len(rvm_env.keys()) < 1:
                rvm_env = os.environ
            else:
                try:
                    os.environ.pop('PATH')
                    os.environ.pop('GEM_HOME')
                    os.environ.pop('BUNDLER_PATH')
                except Exception, e:
                    pass
                for param in os.environ.keys():
                    if param.find('PROXY') != -1:
                        rvm_env[param] = os.environ[param]
                rvm_env.update(os.environ)

            environment = rvm_env
            log.info(environment)

        if os.path.isfile(os.path.join(self.builder.workdir, 'rpm', "%s.spec" % self.project.name)):
            self.dos2unix(os.path.join(self.builder.workdir, 'rpm', "%s.spec" % self.project.name))
            template_fd = open(os.path.join(self.builder.workdir, 'rpm', "%s.spec" % self.project.name))
        else:
            template_fd = open(os.path.join(templates_dir, 'project.spec'))

        rendered_template = open(spec_filename, 'w+')
        rendered_template.write(pystache.template.Template(template_fd.read()).render(context=template_data))
        template_fd.close()
        rendered_template.close()

        rendered_template = open(spec_filename, 'a')
        rendered_template.write("* %(date)s %(username)s <%(email)s> - %(version)s-1\n" % template_data)

        for git_log in self.builder.git.log():
            rendered_template.write('- %s' % git_log)
        rendered_template.close()

        self.project.save()

        if type(environment) is NoneType:
            environment = os.environ

        rpm_cmd = self.builder._exec([ "rpmbuild", "--define", "_topdir %s" % rpm_dir, "-ba", spec_filename ],
            cwd=self.builder.workdir, env=environment, stdout=self.stdout, stderr=self.stderr
        )

        rpm_cmd.wait()

        for path, dirs, files in os.walk(rpm_dir):
            if os.path.isdir(path):
                for file in (os.path.join(path, file) for file in files):
                    try:
                        if os.path.isfile(file) and file.endswith('.rpm'):
                            shutil.copy(file, self.builder.workspace)
                    except Exception, e:
                        log.error(e)

        shutil.rmtree(rpm_dir)

    def upload(self, branch):
        repository_url, user, passwd = self.project.repository()
        repository_dir = self.distribution

        files = glob(os.path.join(self.builder.workspace,
            '%s-%s%s' % (self.project.name,
                self.version,
                '*.rpm')
            )
        )

        if len(files) > 0:
            if repository_dir != None:
                ftp = ftplib.FTP()
                try:
                    ftp.connect(repository_url)
                    log.error('Repository: %s' % repository_url)
                    ftp.login(user, passwd)
                    ftp.cwd(repository_dir)
                except ftplib.error_reply, e:
                    log.error('Cannot conect to ftp server %s' % e)

                for file in files:
                    filename = os.path.basename(file)
                    try:
                        if os.path.isfile(file):
                            f = open(file, 'rb')
                            ftp.storbinary('STOR %s' % filename, f)
                            f.close()
                            log.info("File %s has been successfully sent to repository_url %s" % (filename, repository_url))
                    except ftplib.error_reply, e:
                        log.error(e)

            ftp.quit()


########NEW FILE########
__FILENAME__ = build_consumer
import sys
import os
import bricklayer
sys.path.append(os.path.join(os.path.dirname(bricklayer.__file__), 'utils'))
sys.path.append(os.path.dirname(bricklayer.__file__))

from bricklayer.builder import build_project
from bricklayer.config import BrickConfig
from dreque import DrequeWorker

def main():
    brickconfig = BrickConfig()
    worker = DrequeWorker(['build'], brickconfig.get('redis', 'redis-server'))
    worker.work()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = build_container
import subprocess
import shutil
import os

from bricklayer.config import BrickConfig

class BuildContainer(object):

    def __init__(self, project):
        self.type = BrickConfig().get('container', 'container_type')
        self.container_base = BrickConfig().get('container', '%s_base' % self.type)
        self.project = project
        self.workspace = '%s-%s%s' % (self.container_base, self.project.name, BrickConfig().get('workspace', 'dir'))

        if not os.path.isdir("%s-%s" % (self.container_base, self.project.name)):
            shutil.copytree(self.container_base, "%s-%s" % (self.container_base, self.project.name))
            self.dir = "%s-%s" % (self.container_base, self.project.name)
        

    def setup(self):
        for mount in ['proc', 'sys']:
            p = subprocess.Popen(
                ['mount', '-o', 'bind', mount, '%s/%s' % (self.project.name, mount)], 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            p.wait()

            if not os.path.isdir(self.workspace):
                os.makedirs(self.workspace)

                p = subprocess.Popen(
                    [
                        'mount',
                        '-o',
                        'bind',
                        BrickConfig().get('workspace', 'dir'),
                        self.workspace,
                        ]
                    )
                p.wait()

    def teardown(self):
        for mount in ['proc', 'sys']:
            p = subprocess.Popen(
                ['umount', '%s/%s' % (self.project.name, mount)], 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            p.wait()

            p = subprocess.Popen(['umount', '-l', self.workspace], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            p.wait()
            print p.stdout.read(), p.stderr.read()

    def destroy(self):
        pass

########NEW FILE########
__FILENAME__ = build_info
import redis
import time
from bricklayer.model_base import transaction

class BuildInfo:

    def __init__(self, project='', build_id=0):
        self.redis_cli = self.connect()
        self.project = project
        if project and build_id == 0:
            self.build_id = self.redis_cli.incr('build:%s' % project)
            self.redis_cli.rpush('build:%s:list' % project, self.build_id)
            self.redis_cli.set('build:%s:%s:time' % (self.project, self.build_id), time.strftime('%d/%m/%Y %H:%M', time.localtime(time.time())))
        if build_id > 0:
            self.build_id = build_id

    def __dir__(self):
        return []
    
    @transaction
    def time(self, version=''):
        return self.redis_cli.get('build:%s:%s:time' % (self.project, self.build_id))

    @transaction
    def version(self, version=''):
        if version:
            return self.redis_cli.set('build:%s:%s:version' % (self.project, self.build_id), version) 
        return self.redis_cli.get('build:%s:%s:version' % (self.project, self.build_id))

    @transaction
    def release(self, release=''):
        if release:
            return self.redis_cli.set('build:%s:%s:release' % (self.project, self.build_id), release) 
        return self.redis_cli.get('build:%s:%s:release' % (self.project, self.build_id))


    @transaction
    def log(self, logfile=''):
        if logfile:
            return self.redis_cli.set('build:%s:%s:log' % (self.project, self.build_id), logfile) 
        return self.redis_cli.get('build:%s:%s:log' % (self.project, self.build_id))

    @transaction
    def builds(self):
        builds = self.redis_cli.lrange('build:%s:list' % self.project, 0, self.redis_cli.llen('build:%s:list' % self.project))
        return builds

    @transaction
    def building(self, is_building=None):
        if is_building != None:
            if is_building:
                self.redis_cli.incr('build:%s:%s:status' % (self.project, self.build_id))
            else:
                self.redis_cli.decr('build:%s:%s:status' % (self.project, self.build_id))
            return is_building
        else:
            if self.redis_cli.get('build:%s:%s:status' % (self.project, self.build_id)) > 0:
                return True
            else:
                return False

    def connect(self):
        return redis.Redis()    

########NEW FILE########
__FILENAME__ = build_options
import os
import yaml

class BuildOptions(object):
	options = {'changelog': True, 'experimental': False, 'rvm': 'system', 'not_found': False }

	def __init__(self, wdir):
		if os.path.isfile(os.path.join(wdir, '.bricklayer.yml')):
			bricklayer_yml = open(os.path.join(wdir, '.bricklayer.yml')).read()
			self.options.update(yaml.load(bricklayer_yml))
		else:
			self.options.update({'not_found': True})


	def __dir__(self):
		return self.options.keys()

	def __getattr__(self, attr):
		return self.options[attr]

########NEW FILE########
__FILENAME__ = config
import os
import ConfigParser

class BrickConfigImpl:
    _instance = None
    config_file = None

    def __init__(self):
        self.config_parse = ConfigParser.ConfigParser()
        self.config_parse.read([self.config_file])

    def get(self, section, name):
        return self.config_parse.get(section, name)

def BrickConfig(config_file=None):
    if not BrickConfigImpl._instance:
        BrickConfigImpl.config_file = resolve_config_file(config_file)
        BrickConfigImpl._instance = BrickConfigImpl()

    return BrickConfigImpl._instance

def resolve_config_file(config_file):
    if config_file == None:
        if "BRICKLAYERCONFIG" in os.environ.keys():
            config_file = os.environ['BRICKLAYERCONFIG']
        else:
            config_file = '/etc/bricklayer/bricklayer.ini'

    check_config_file(config_file)
    return config_file

def check_config_file(config_file):
    if not os.path.exists(config_file) and not os.path.isfile(config_file):
        print "You need to set BRICKLAYERCONFIG or create /etc/bricklayer/bricklayer.ini"
        exit(1)
########NEW FILE########
__FILENAME__ = current_build
import redis
from model_base import ModelBase, transaction

class CurrentBuild(ModelBase):
    namespace = 'current_build'
  
    def __init__(self, name=''):
        self.name = name
        self.populate(self.name)

    def __dir__(self):
        return ['name']
   
    @classmethod
    def get_all(self):
        connection_obj = CurrentBuild()
        redis_cli = connection_obj.connect()
        keys = redis_cli.keys('%s:*' % self.namespace)
        currents = []
        for key in keys:
            key = key.replace('%s:' % self.namespace, '')
            currents.append(CurrentBuild(key)) 
        return currents   

    @classmethod
    def delete_all(self):
        connection_obj = CurrentBuild()
        redis_cli = connection_obj.connect()
        keys = redis_cli.keys('%s:*' % self.namespace)
        for key in keys:
            redis_cli.delete(key)
        return True

########NEW FILE########
__FILENAME__ = git
import os 
import subprocess
import re
import shutil
import logging as log
from config import BrickConfig

devnull = open('/dev/null', 'w')

class Git(object):
    def __init__(self, project, workdir=None):
        _workdir = workdir
        if not _workdir:
            _workdir = BrickConfig().get('workspace', 'dir')

        self.workdir = os.path.join(_workdir, project.name)
        self.project = project

    def _exec_git(self, cmd=[], cwd=None, stdout=None):
        if stdout is None:
            stdout = devnull
        if (cwd is None):
            cwd = BrickConfig().get('workspace', 'dir')
        return subprocess.Popen(" ".join(cmd), shell=True, stdout=stdout, stderr=stdout, close_fds=True, cwd=cwd)

    def clone(self, branch=None):
        try:
            if (os.path.exists(self.workdir)):
                shtuil.rmtree(self.workdir, ignore_errors=True)
            log.info("Git clone %s %s" % (self.project.git_url, self.workdir))
            git_cmd = self._exec_git(['git', 'clone', self.project.git_url, self.workdir], stdout=subprocess.PIPE)
            status = git_cmd.wait() == 0
            if branch:
                self.checkout_branch(branch)
        except Exception, e:
            log.info("error running git clone: %s" % str(e))
            status = False
        if (not status):
            shutil.rmtree(self.workdir, ignore_errors=True)
        return(status)

    def reset(self):
        git_cmd = self._exec_git(['git', 'reset', 'HEAD'], cwd=self.workdir)
        git_cmd.wait()
    
    def pull(self):
        status = True
        try:
            for cmd in [['timeout', '300', 'git', 'pull', '--ff-only'], ['timeout', '300', 'git', 'fetch', '--tags']]:
                git_cmd = self._exec_git(cmd, cwd=self.workdir)
                status  = status and (git_cmd.wait() == 0)
        except:
            log.info("error running git pull")
            status = False
        if (not status):
            shutil.rmtree(self.workdir, ignore_errors=True)
        return(status)
    
    def checkout_tag(self, tag='master'):
        git_cmd = self._exec_git(['git', 'checkout', '-f', tag], stdout=subprocess.PIPE, cwd=self.workdir)
        s = git_cmd.wait()
        if s != 0:
            log.info("Checkout fail: %s" % git_cmd.stderr.read())

    def checkout_branch(self, branch):
        if branch in self.branches():
            git_cmd = self._exec_git(['git', 'checkout', branch], cwd=self.workdir)
            git_cmd.wait()

    def checkout_remote_branch(self, branch):
        git_cmd = self._exec_git(
                ['git', 'checkout', '-b', branch, '--track', 'origin/%s' % branch], 
                cwd=self.workdir
            )
        git_cmd.wait()

    def branches(self, remote=False):
        if remote:
            git_cmd = self._exec_git("git branch -r".split(), stdout=subprocess.PIPE, cwd=self.workdir) 
        else:
            git_cmd = self._exec_git("git branch".split(), stdout=subprocess.PIPE, cwd=self.workdir) 
        branch_list = git_cmd.stdout.readlines()
        
        return map(lambda x: x.strip(), branch_list)

    def clear_repo(self):
        try:
            shutil.rmtree(self.workdir)
        except Exception, e:
            log.info("could not remove folders but I'm ignoring it")
            

    def last_commit(self, branch='master'):
        cf = os.path.join(self.workdir, '.git', 'refs', 'heads', branch)
        if os.path.exists(cf):
            with file(cf, "r") as fh:
                return(fh.read())

    def last_tag(self, tag_type):
        tags = self.tags(tag_type)
        check = []
        for tag in tags:
            if re.match("(\w+)_(\d+\.\d+\.\d+)", tag):
                tag_v = tag.split('_')[1].split("-")[0]
                check.append(map(int, tag_v.split('.')))
            else:
                continue
        if len(check) > 0:
            return tag_type + "_%d.%d.%d" % tuple(max(check))
        else:
            return ''    

    def tags(self, tag_type):
        try:
            git_cmd = self._exec_git(['git', 'tag', '-l'], stdout=subprocess.PIPE, cwd=self.workdir)
            git_cmd.wait()
            tags = git_cmd.stdout.readlines()
            result = []
            if tag_type:
                for t in tags:
                    if t.startswith(tag_type):
                        result.append(t.strip('\n'))
            else:
                for t in tags:
                    result.append(t.strip('\n'))
            return result

        except Exception, e:
            log.exception(repr(e))
            return []

    def create_tag(self, tag=''):
        git_cmd = self._exec_git(['git', 'tag', str(tag)], cwd=self.workdir)
        git_cmd.wait()

    def create_branch(self, branch=''):
        git_cmd = self._exec_git(['git', 'checkout', '-b', branch], cwd=self.workdir)
        git_cmd.wait()

    def log(self, number=3):
        git_cmd = self._exec_git(['git', 'log', '-n', str(number),
             '--pretty=oneline', '--abbrev-commit'], cwd=self.workdir, stdout=subprocess.PIPE)
        git_cmd.wait()
        return git_cmd.stdout.readlines()

    def push_tags(self):
        git_cmd = self._exec_git(['git', 'push', '--tags'], cwd=self.workdir)
        git_cmd.wait()

########NEW FILE########
__FILENAME__ = groups
import redis
from model_base import ModelBase, transaction

class Groups(ModelBase):
    namespace = 'group'
  
    def __init__(self, group_name='', repo_addr='', repo_user='', repo_passwd=''):
        self.name = group_name
        self.repo_addr = repo_addr
        self.repo_user = repo_user
        self.repo_passwd = repo_passwd
        self.populate(self.name)

    def __dir__(self):
        return ['name', 'repo_addr', 'repo_user', 'repo_passwd']
   
    @classmethod
    def get_all(self):
        connection_obj = Groups()
        redis_cli = connection_obj.connect()
        keys = redis_cli.keys('%s:*' % self.namespace)
        groups = []
        for key in keys:
            key = key.replace('%s:' % self.namespace, '')
            groups.append(Groups(key)) 
        return groups

########NEW FILE########
__FILENAME__ = model_base
import redis

def transaction(method):
    def new(*args, **kwargs):
        conn = redis.Redis()
        args[0].redis_cli = conn
        try:
            ret = method(*args, **kwargs)
            if ret == None:
                ret = ""
            return ret
        finally:
            if (hasattr(conn, "connection")):
                conn.connection.disconnect()
            if (hasattr(conn.connection_pool, "disconnect")):
                conn.connection_pool.disconnect()
    return new

class ModelBase:
    
    redis_cli = None
    namespace = ''

    def connect(self):
        return redis.Redis()

    @transaction
    def save(self):
        data = {}
        for attr in self.__dir__():
            data[attr] = getattr(self, attr)
        self.redis_cli.hmset("%s:%s" % (self.namespace, self.name), data)
        self.populate(self.name)
    
    @transaction
    def populate(self, name):
        res = self.redis_cli.hgetall("%s:%s" % (self.namespace, name))
        for key, val in res.iteritems():
            key = key.replace('%s:' % self.namespace, '')
            setattr(self, key, val)

    @transaction
    def exists(self):
        res = self.redis_cli.exists('%s:%s' % (self.namespace, self.name))
        return res

    @transaction
    def delete(self):
        project_keys = self.redis_cli.keys("*:%s" % self.name)
        for key in project_keys:
            self.redis_cli.delete(key)

        project_keys = self.redis_cli.keys("*:%s:*" % self.name)
        for key in project_keys:
            self.redis_cli.delete(key)

########NEW FILE########
__FILENAME__ = projects
import shutil
import redis
from model_base import ModelBase, transaction
from groups import Groups
from git import Git

class Projects(ModelBase):
    
    namespace = 'project'

    def __init__(self, name='', git_url='', install_cmd='', build_cmd='', version='', release='', group_name='', experimental=1):
        self.name = name
        self.git_url = git_url
        self.install_cmd = install_cmd
        self.build_cmd = build_cmd
        self.group_name = group_name
        if version:
            self.version(version=version)
        self.release = release
        self.experimental = experimental
        self.email = 'bricklayer@locaweb.com.br'
        self.username = 'Bricklayer Builder'
        self.install_prefix = ''
        self.populate(self.name)

    def __dir__(self):
        return ['name', 'git_url', 'install_cmd', 'build_cmd', 'email', 'username', 'release', 'group_name', 'experimental']
   
    @transaction
    def start_building(self):
        self.redis_cli.setex('build_lock:%s' % self.name, 3600, 1)

    @transaction
    def is_building(self):
        build_lock = self.redis_cli.get('build_lock:%s' % self.name)
        if build_lock and int(build_lock) > 0:
            return True
        return False

    @transaction
    def stop_building(self):
        self.redis_cli.decr('build_lock:%s' % self.name)

    @transaction
    def add_branch(self, branch):
        self.redis_cli.rpush('branches:%s' % self.name, branch)
     
    @transaction
    def remove_branch(self, branch):
        index = self.redis_cli.lindex('branches:%s' % self.name, branch)
        self.redis_cli.lrem('branches:%s' % self.name, index)
    
    @transaction
    def repository(self):
        group = Groups(self.group_name)
        res = []
        for attr in ('repo_addr', 'repo_user', 'repo_passwd'):
            res.append(getattr(group, attr))
        return res

    @transaction
    def branches(self):
        res = self.redis_cli.lrange('branches:%s' % self.name, 0, self.redis_cli.llen('branches:%s' % self.name) - 1)
        if len(res) == 0:
            res.append('master')
        return res

    @transaction
    def last_commit(self, branch='master', commit=''):
        if commit == '':
            res = self.redis_cli.get('branches:%s:%s:last_commit' % (self.name, branch))
        else:
            res = self.redis_cli.set('branches:%s:%s:last_commit' % (self.name, branch), commit)
        return res

    @transaction
    def last_tag(self, tag_type='', tag=''):
        if tag:
            res = self.redis_cli.set('tags:%s:%s:last_tag' % (self.name, tag_type), tag)
        else:
            res = self.redis_cli.get('tags:%s:%s:last_tag' % (self.name, tag_type))
        return res

    @transaction
    def version(self, branch='master', version=''):
        if version == '':
            res = self.redis_cli.get('branch:%s:%s:version' % (self.name, branch))
        else:
            res = self.redis_cli.set('branch:%s:%s:version' % (self.name, branch), version)
        return res

    @classmethod
    def get_all(self):
        connection_obj = Projects()
        redis_cli = connection_obj.connect()
        keys = redis_cli.keys('%s:*' % self.namespace)
        projects = []
        for key in keys:
            key = key.replace('%s:' % self.namespace, '')
            projects.append(Projects(key)) 
        return projects
    
    def clear_branches(self):
        git = Git(self)
        for b in self.branches():
            try:
                shutil.rmtree("%s-%s" % (git.workdir, b))
            except Exception, e:
                pass # ignore if files does not exist

########NEW FILE########
__FILENAME__ = rest
import os
import signal
import sys
import json

sys.path.append(os.path.dirname(__file__))
from projects import Projects
from groups import Groups
from git import Git
from builder import Builder, build_project
from build_info import BuildInfo
from current_build import CurrentBuild
from config import BrickConfig

import cyclone.web
import cyclone.escape
from twisted.internet import reactor
from twisted.python import log
from twisted.application import service, internet

brickconfig = BrickConfig()

class Project(cyclone.web.RequestHandler):
    def post(self, *args):
        if len(args) >= 1:
            name = args[0]
            project = Projects(name)
            for key, value in self.request.arguments.iteritems():
                if key in ("git_url", "version", "build_cmd", "install_cmd"):
                    setattr(project, key, value[0])
            project.save()

        try:
            if not Projects(self.get_argument('name')).exists():
                raise
        except Exception, e:
            project = Projects()
            project.name = self.get_argument('name')[0]
            project.git_url = self.get_argument('git_url')[0]
            for name, parm in self.request.arguments.iteritems():
                if name not in ('branch', 'version'):
                    setattr(project, str(name), parm[0])
            try:
                project.add_branch(self.get_argument('branch'))
                project.version(self.get_argument('branch'), self.get_argument('version'))
                project.group_name = self.get_argument('group_name')
                project.save()
                log.msg('Project created:', project.name)
                
                self.write(cyclone.escape.json_encode({'status': 'ok'}))
            except Exception, e:
                log.err()
                self.write(cyclone.escape.json_encode({'status': "fail"}))

        else:
            self.write(cyclone.escape.json_encode({'status':  "Project already exists"}))

    def put(self, name):
        project = Projects(name)
        try:
            for aname, arg in self.request.arguments.iteritems():
                if aname in ('branch'):
                    branch = arg
                else:
                    setattr(project, aname, arg[0])
            
            json_data = json.loads(self.request.body)
            if len(json_data.keys()) > 0:
                for k, v in json_data.iteritems():
                    setattr(project, k, v)
            
            project.save()
        except Exception, e:
            log.err(e)
            self.finish(cyclone.escape.json_encode({'status': 'fail'}))
        self.finish(cyclone.escape.json_encode({'status': 'modified %s' % name}))

    def get(self, name='', branch='master'):
        try:
            if name:
                    project = Projects(name)
                    reply = {'name': project.name,
                            'branch': project.branches(),
                            'experimental': int(project.experimental),
                            'group_name': project.group_name,
                            'git_url': project.git_url,
                            'version': project.version(),
                            'last_tag_testing': project.last_tag(tag_type='testing'),
                            'last_tag_stable': project.last_tag(tag_type='stable'),
                            'last_tag_unstable': project.last_tag(tag_type='unstable'),
                            'last_commit': project.last_commit(branch)}


            else:
                projects = Projects.get_all()
                reply = []
                for project in projects:
                    reply.append(
                            {'name': project.name,
                            'branch': project.branches(),
                            'experimental': int(project.experimental),
                            'group_name': project.group_name,
                            'git_url': project.git_url,
                            'version': project.version(),
                            'last_tag_testing': project.last_tag(tag_type='testing'),
                            'last_tag_stable': project.last_tag(tag_type='stable'),
                            'last_tag_unstable': project.last_tag(tag_type='unstable'),
                            'last_commit': project.last_commit(branch)
                            })

            self.write(cyclone.escape.json_encode(reply))
        except Exception, e:
            self.write(cyclone.escape.json_encode("%s No project found" % e))


    def delete(self, name):
        log.msg("deleting project %s" % name)
        try:
            project = Projects(name)
            git = Git(project)
            git.clear_repo()
            project.clear_branches()
            project.delete()
            self.write(cyclone.escape.json_encode({'status': 'project deleted'}))
        except Exception, e:
            log.err(e)
            self.write(cyclone.escape.json_encode({'status': 'failed to delete %s' % str(e)}))


class Branch(cyclone.web.RequestHandler):
    def get(self, project_name):
        project = Projects(project_name)
        git = Git(project)
        branches = git.branches(remote=True)
        self.write(cyclone.escape.json_encode({'branches': branches}))

    def post(self, project_name):
        branch = self.get_argument('branch')
        project = Projects(project_name)
        if branch in project.branches():
            self.write(cyclone.escape.json_encode({'status': 'failed: branch already exist'}))
        else:
            project.add_branch(branch)
            project.version(branch, '0.1')
            reactor.callInThread(build_project, {'project': project.name, 'branch': self.get_argument('branch'), 'release': 'experimental'})
            self.write(cyclone.escape.json_encode({'status': 'ok'}))

    def delete(self, project_name):
        project = Projects(project_name)
        branch = self.get_argument('branch')
        project.remove_branch(branch)
        self.write(cyclone.escape.json_encode({'status': 'ok'}))

class Build(cyclone.web.RequestHandler):
    def post(self, project_name):
        project = Projects(project_name)
        release = self.get_argument('tag')
        version = self.get_argument('version')
        commit = self.get_argument('commit', default='HEAD')

        reactor.callInThread(build_project, {
                    'project': project.name, 
                    'branch' : 'master', 
                    'release': release, 
                    'version': version,
                    'commit' : commit,
        })

        self.write(cyclone.escape.json_encode({'status': 'build of branch %s scheduled' % release}))

    def get(self, project_name):
        project = project_name
        build_ids = BuildInfo(project, -1).builds()
        builds = []
        for bid in build_ids[-10:]:
            build = BuildInfo(project, bid)
            builds.append({'build': int(bid), 'log': os.path.basename(build.log()), 'version': build.version(), 'release': build.release(), 'date': build.time()})
        self.write(cyclone.escape.json_encode(builds))

class Log(cyclone.web.RequestHandler):
    def get(self, project, bid):
        build_info = BuildInfo(project, bid)
        if os.path.isfile(build_info.log()):
            self.write(open(build_info.log()).read())

class Check(cyclone.web.RequestHandler):
    def post(self, project_name):
        project = Projects(project_name)
        builder = Builder(project_name)
        builder.build_project()

class Clear(cyclone.web.RequestHandler):
    def post(self, project_name):
        try:
            project = Projects(project_name)
            git = Git(project)
            git.clear_repo()
            self.write(cyclone.escape.json_encode({'status': 'ok'}))
        except Exception, e:
            self.write(cyclone.escape.json_encode({'status': 'fail', 'error': str(e)}))


class Group(cyclone.web.RequestHandler):
    def post(self, *args):
        try:
            if len(args) > 0:
                name = args[0]
                group = Groups(name)
                for key, value in self.request.arguments.iteritems():
                    if key in ("repo_addr", "repo_user", "repo_passwd"):
                        setattr(group, key, value[0])
                group.save()
            else:
                group = Groups(self.get_argument('name'))
                group.repo_addr = self.get_argument('repo_addr')
                group.repo_user = self.get_argument('repo_user')
                group.repo_passwd = self.get_argument('repo_passwd')
                group.save()
            self.write(cyclone.escape.json_encode({'status': 'ok'}))
        except Exception, e:
            self.write(cyclone.escape.json_encode({'status': 'fail', 'error': str(e)}))

    def get(self, *args):
        groups_json = []
        groups = []

        if len(args) > 1:
            name = args[0]
            groups = [Groups(name)]
        else:
            groups = Groups.get_all()

        for group in groups:
            group_json = {}
            for attr in ('name', 'repo_addr', 'repo_user', 'repo_passwd'):
                group_json.update({attr: getattr(group, attr)})
            groups_json.append(group_json)
        self.write(cyclone.escape.json_encode(groups_json))

class Current(cyclone.web.RequestHandler):
    def get(self):
        response = []
        currents = CurrentBuild.get_all()
        for current in currents:
            response.append({"name":current.name})
        self.set_header("Content-Type", "application/json")
        self.write(cyclone.escape.json_encode(response))

    def delete(self):
        CurrentBuild.delete_all()
        self.write(cyclone.escape.json_encode("ok"))

class Main(cyclone.web.RequestHandler):
    def get(self):
        self.redirect('/static/index.html')


restApp = cyclone.web.Application([
    (r'/project', Project),
    (r'/project/?(.*)', Project),
    (r'/branch/(.*)', Branch),
    (r'/clear/(.*)', Clear),
    (r'/build/current', Current),
    (r'/build/(.*)', Build),
    (r'/group', Group),
    (r'/group/?(.*)', Group),
    (r'/log/(.*)/+(.*)', Log),
    (r'/static/(.*)', cyclone.web.StaticFileHandler, {'path': brickconfig.get('static', 'dir')}),
    (r'/repo/(.*)', cyclone.web.StaticFileHandler, {'path': brickconfig.get('local_repo', 'dir')}),
    (r'/', Main),
])

application = service.Application("bricklayer_rest")
server = internet.TCPServer(int(brickconfig.get('server', 'port')), restApp, interface="0.0.0.0")
server.setServiceParent(application)

########NEW FILE########
__FILENAME__ = service
import sys
import os
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
import pystache

from twisted.application import internet, service
from twisted.internet import protocol, task, threads, reactor, defer
from twisted.protocols import basic
from twisted.python import log

from bricklayer import builder
from bricklayer.builder import Builder, build_project
from bricklayer.projects import Projects
from bricklayer.git import Git
from bricklayer.config import BrickConfig
from bricklayer.rest import restApp

class BricklayerService(service.Service):

    def __init__(self):
        log.msg("scheduler: init")
        self.sched_task = task.LoopingCall(self.sched_builder)
    
    def send_job(self, project_name, branch, release, version):
        log.msg('sched build: %s [%s:%s]' % (project_name, release, version))
        brickconfig = BrickConfig()
        #queue = Dreque(brickconfig.get('redis', 'redis-server'))
        #queue.enqueue('build', 'builder.build_project', {
        builder.build_project({
            'project': project_name, 
            'branch': branch, 
            'release': release, 
            'version': version,
            })

    def sched_builder(self):
        for project in sorted(Projects.get_all(), key=lambda p: p.name):
            if (project.name == ""):
                continue
            try:
                log.msg("checking project: %s" % project.name)
                if project.is_building():
                    log.msg("project %s still building, skip" % project.name)
                    continue
                branch = "master"
                git = Git(project)
                if os.path.isdir(git.workdir):
                    git.checkout_branch(branch)
                    git.pull()
                else:
                    git.clone(branch)

                if not os.path.isdir(git.workdir):
                    continue

                for remote_branch in git.branches(remote=True):
                    git.checkout_remote_branch(remote_branch.replace('origin/', ''))

                for release in ('stable', 'testing', 'unstable'):
                    if project.last_tag(release) != git.last_tag(release):
                        try:
                            _, version = git.last_tag(release).split('_')
                            log.msg("new %s tag, building version: %s" % (release, version))
                            d = threads.deferToThread(self.send_job, project.name, branch, release, version)
                        except Exception, e:
                            log.msg("tag not parsed: %s:%s" % (project.name, git.last_tag(release)))
                
                #if int(project.experimental) == 1:
                #    for branch in project.branches():
                #        git.checkout_remote_branch(branch)
                #        git.checkout_branch(branch)
                #        git.pull()
                #        if project.last_commit(branch) != git.last_commit(branch):
                #            project.last_commit(branch, git.last_commit(branch))
                #            d = threads.deferToThread(self.send_job, project.name, branch, 'experimental', None)
                # 
                #        git.checkout_branch("master")

            except Exception, e:
                log.err(e)
                

    def startService(self):
        service.Service.startService(self)
        log.msg("scheduler: start %s" % self.sched_task)
        self.sched_task.start(10.0)

    @defer.inlineCallbacks
    def stopService(self):
        service.Service.stopService(self)
        yield self.sched_task.stop()


brickService = BricklayerService()

application = service.Application("Bricklayer")
brickService.setServiceParent(application)

########NEW FILE########
__FILENAME__ = base

try:
    import json
except ImportError:
    import simplejson as json
import logging
import time
from redis import Redis, ResponseError

from dreque import serializer
from dreque.stats import StatsCollector

class Dreque(object):
    def __init__(self, server, db=None, key_prefix="dreque:", serializer=serializer):
        self.log = logging.getLogger("dreque")

        if isinstance(server, (tuple, list)):
            host, port = server
            self.redis = Redis(server[0], server[1], db=db)
        elif isinstance(server, basestring):
            host = server
            port = 6379
            if ':' in server:
                host, port = server.split(':')
            self.redis = Redis(host, port, db=db)
        else:
            self.redis = server

        self.key_prefix = key_prefix
        self.watched_queues = set()
        self.stats = StatsCollector(self.redis, self.key_prefix)
        self.serializer = serializer

    # Low level

    def push(self, queue, item, delay=None):
        self.watch_queue(queue)

        if delay:
            if delay < 31536000:
                delay = int(delay + time.time())
            # TODO: In Redis>=1.1 can use an ordered set: zadd(delayed, delay, encoded_item)
            self.redis.lpush(self._delayed_key(queue), "%.12x:%s" % (delay, self.encode(item)))
        else:
            self.redis.lpush(self._queue_key(queue), self.encode(item))

    def check_delayed(self, queue, num=10):
        """Check for available jobs in the delayed queue and move them to the live queue"""
        # TODO: In Redis>=1.1 can use an ordered set: zrangebyscore(delayed, 0, current_time)
        delayed_key = self._delayed_key(queue)
        queue_key = self._queue_key(queue)
        try:
            jobs = self.redis.sort(delayed_key, start=0, num=num, alpha=True) or []
        except ResponseError, exc:
            if str(exc) != "no such key":
                raise
            return
        now = time.time()
        for j in jobs:
            available, encoded_job = j.split(':', 1)
            available = int(available, 16)
            if available < now:
                if self.redis.lrem(delayed_key, j) > 0:
                    # Only copy the job if it still exists.. nobody else got to it first
                    self.redis.lpush(queue_key, encoded_job)

    def pop(self, queue):
        self.check_delayed(queue)
        msg = self.redis.rpop(self._queue_key(queue))
        return self.decode(msg) if msg else None

    def poppush(self, source_queue, dest_queue):
        msg = self.redis.poppush(self._queue_key(source_queue), self._queue_key(dest_queue))
        return self.decode(msg) if msg else None

    def size(self, queue):
        return self.redis.llen(self._queue_key(queue))

    def peek(self, queue, start=0, count=1):
        return self.list_range(self._queue_key(queue), start, count)

    def list_range(self, key, start=0, count=1):
        if count == 1:
            return self.decode(self.redis.lindex(key, start))
        else:
            return [self.decode(x) for x in self.redis.lrange(key, start, start+count-1)]

    # High level

    def enqueue(self, queue, func, *args, **kwargs):
        delay = kwargs.pop('_delay', None)
        max_retries = kwargs.pop('_max_retries', 5)
        if not isinstance(func, basestring):
            func = "%s.%s" % (func.__module__, func.__name__)
        self.push(queue, dict(func=func, args=args, kwargs=kwargs, retries_left=max_retries), delay=delay)

    def dequeue(self, queues, worker_queue=None):
        now = time.time()
        for q in queues:
            if worker_queue:
                msg = self.redis.poppush(self._queue_key(source_queue), self._redis_key(dest_queue))
                if msg:
                    msg = self.decode(msg)
            else:
                msg = self.pop(q)
            if msg:
                msg['queue'] = q
                return msg
 
    # Queue methods

    def queues(self):
        return self.redis.smembers(self._queue_set_key())

    def remove_queue(self, queue):
        self.watched_queues.discard(queue)
        self.redis.srem(self._queue_set_key(), queue)
        self.redis.delete(self._queue_key(queue))
        self.redis.delete(self._delayed_key(queue))

    def watch_queue(self, queue):
        if queue not in self.watched_queues:
            self.watched_queues.add(queue)
            self.redis.sadd(self._queue_set_key(), queue)

    #

    def encode(self, value):
        return self.serializer.dumps(value)

    def decode(self, value):
        return self.serializer.loads(value)

    def _queue_key(self, queue):
        return self._redis_key("queue:" + queue)

    def _queue_set_key(self):
        return self._redis_key("queues")

    def _delayed_key(self, queue):
        return self._redis_key("delayed:" + queue)

    def _redis_key(self, key):
        return self.key_prefix + key

########NEW FILE########
__FILENAME__ = serializer
import sys
import datetime
import zlib
import decimal
if sys.version_info[:2] >= (2, 6):
    import json
else:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%s %s" % (DATE_FORMAT, TIME_FORMAT)

class AttributeDict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.date) and not isinstance(o, datetime.datetime):
            return {'__type': 'date', '__value': o.strftime(DATE_FORMAT)}
        elif isinstance(o, datetime.datetime):
            value = o.strftime(DATETIME_FORMAT)
            if o.microsecond:
                value += ".%d" % o.microsecond
            return {'__type': 'datetime', '__value': value}
        elif isinstance(o, datetime.time):
            value = o.strftime(TIME_FORMAT)
            if o.microsecond:
                value += ".%d" % o.microsecond
            return {'__type': 'time', '__value': o.strftime(value)}
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif type(o).__name__ == "__proxy__": # Django's proxy for translatable strings
            return unicode(o)
        return super(JSONEncoder, self).default(o)

class JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self._object_hook
        super(JSONDecoder, self).__init__(*args, **kwargs)

    def _object_hook(self, o):
        typ = o.get('__type')
        if typ:
            value = o.get('__value')
            if typ == 'datetime':
                dt = datetime.datetime.strptime(value.split('.')[0], DATETIME_FORMAT)
                if '.' in value:
                    dt = dt.replace(microsecond=int(value.split('.')[-1]))
                return dt
            elif typ == 'date':
                return datetime.datetime.strptime(value, DATE_FORMAT).date()
            elif typ == 'time':
                dt = datetime.datetime.strptime(value.split('.')[0], TIME_FORMAT).time()
                if '.' in value:
                    dt = dt.replace(microsecond=int(value.split('.')[-1]))
                return dt
            raise TypeError("Unable to deserialize unknown type %s" % typ)
        return AttributeDict(o)

def dumps(*args, **kwargs):
    kwargs['cls'] = JSONEncoder
    kwargs['indent'] = False
    st = json.dumps(*args, **kwargs)
    return zlib.compress(st)

def loads(st, *args, **kwargs):
    st = zlib.decompress(st)
    kwargs['cls'] = JSONDecoder
    return json.loads(st, *args, **kwargs)
    
########NEW FILE########
__FILENAME__ = stats

class StatsCollector(object):
    def __init__(self, store, prefix=''):
        self.store = store
        self.prefix = prefix

    def incr(self, key, delta=1):
        key = self._key(key)
        try:
            return int(self.store.incr(key, delta))
        except ValueError:
            if not self.store.add(key, 1):
                # Someone set the value before us
                return int(self.store.incr(key, delta))

    def decr(self, key, delta=1):
        key = self._key(key)
        try:
            return int(self.store.decr(key, delta))
        except ValueError:
            if not self.store.add(key, 0):
                # Someone set the value before us
                return int(self.store.decr(key, delta))

    def get(self, key):
        try:
            return int(self.store.get(self._key(key)))
        except TypeError:
            return None

    def set(self, key, value):
        self.store.set(self._key(key), value)

    def clear(self, key):
        self.store.delete(self._key(key))

    def _key(self, key):
        return "%sstat:%s" % (self.prefix, key)

########NEW FILE########
__FILENAME__ = utils
try:
     import procname
     setprocname = procname.setprocname
     getprocname = procname.getprocname
except ImportError:
    try:
        from ctypes import cdll, byref, create_string_buffer
        libc = cdll.LoadLibrary('libc.so.6')
        def setprocname(name):
            buff = create_string_buffer(len(name)+1)
            buff.value = name
            libc.prctl(15, byref(buff), 0, 0, 0)
            # FreeBSD: libc.setproctitle(name)
        def getprocname():
            libc = cdll.LoadLibrary('libc.so.6')
            buff = create_string_buffer(128)
            # 16 == PR_GET_NAME from <linux/prctl.h>
            libc.prctl(16, byref(buff), 0, 0, 0)
            return buff.value
    except (OSError, ImportError):
        def setprocname(name):
            pass
        def getprocname():
            import sys
            return sys.argv[0]

########NEW FILE########
__FILENAME__ = worker

import copy
import os
import logging
import signal
import socket
import time
from multiprocessing import Process

from dreque.base import Dreque
from dreque.utils import setprocname

SUPPORTED_DISPATCHERS = ("nofork", "fork") # "pool"

class DrequeWorker(Dreque):
    def __init__(self, queues, server, db=None, dispatcher="fork"):
        self.queues = queues
        self.function_cache = {}
        super(DrequeWorker, self).__init__(server, db)
        self.log = logging.getLogger("dreque.worker")
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.worker_id = "%s:%d" % (self.hostname, self.pid)
        self.dispatcher = dispatcher
        self.child = None
        self._shutdown = None
        if dispatcher not in SUPPORTED_DISPATCHERS:
            raise TypeError("Unsupported dispatcher %s" % dispatcher)

    def work(self, interval=5):
        self.register_worker()
        self.register_signal_handlers()

        setprocname("dreque: Starting")

        self._shutdown = None
        try:
            while not self._shutdown:
                worked = self.work_once()
                if interval == 0:
                    break

                if not worked:
                    setprocname("dreque: Waiting for %s" % ",".join(self.queues))
                    time.sleep(interval)
        finally:
            self.unregister_worker()

    def work_once(self):
        job = self.dequeue(self.queues)
        if not job:
            return False

        try:
            self.working_on(job)
            self.process(job)
        except Exception, exc:
            import traceback
            self.log.warning("Job failed (%s): %s\n%s" % (job, str(exc), traceback.format_exc()))
            # Requeue
            queue = job.pop("queue")
            if 'fail' not in job:
                job['fail'] = [str(exc)]
            else:
                job['fail'].append(str(exc))
            job['retries_left'] = job.get('retries_left', 1) - 1
            if job['retries_left'] > 0:
                self.push(queue, job, 2**len(job['fail']))
                self.stats.incr("retries")
                self.stats.incr("retries:" + self.worker_id)
            else:
                self.failed()
        else:
            self.done_working()

        return True

    def process(self, job):
        if self.dispatcher == "fork":
            child = Process(target=self.dispatch_child, args=(job,))
            child.start()
            self.child = child
            setprocname("dreque: Forked %d at %d" % (child.pid, time.time()))
            while True:
                try:
                    child.join()
                except OSError, exc:
                    if 'Interrupted system call' not in exc:
                        raise
                    continue
                break
            self.child = None

            if child.exitcode != 0:
                raise Exception("Job failed with exitcode %d" % child.exitcode)
        else: # nofork
            self.dispatch(copy.deepcopy(job))

    def dispatch_child(self, job):
        self.reset_signal_handlers()
        self.dispatch(job)

    def dispatch(self, job):
        setprocname("dreque: Processing %s since %d" % (job['queue'], time.time()))
        func = self.lookup_function(job['func'])
        kwargs = dict((str(k), v) for k, v in job['kwargs'].items())
        func(*job['args'], **kwargs)

    #

    def register_signal_handlers(self):
        signal.signal(signal.SIGTERM, lambda signum,frame:self.shutdown())
        signal.signal(signal.SIGINT, lambda signum,frame:self.shutdown())
        signal.signal(signal.SIGQUIT, lambda signum,frame:self.graceful_shutdown())
        signal.signal(signal.SIGUSR1, lambda signum,frame:self.kill_child())

    def reset_signal_handlers(self):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGQUIT, signal.SIG_DFL)
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

    def shutdown(self, signum=None, frame=None):
        """Shutdown immediately without waiting for job to complete"""
        self.log.info("Worker %s shutting down" % self.worker_id)
        self._shutdown = "forced"
        self.kill_child()

    def graceful_shutdown(self, signum=None, frame=None):
        """Shutdown gracefully waiting for job to finish"""
        self.log.info("Worker %s shutting down gracefully" % self.worker_id)
        self._shutdown = "graceful"

    def kill_child(self):
        if self.child:
            self.log.info("Killing child %s" % self.child)
            if self.child.is_alive():
                self.child.terminate()
            self.child = None

    #

    def register_worker(self):
        self.redis.sadd(self._redis_key("workers"), self.worker_id)

    def unregister_worker(self):
        self.redis.srem(self._redis_key("workers"), self.worker_id)
        self.redis.delete(self._redis_key("worker:%s:started" % self.worker_id))
        self.stats.clear("processed:"+self.worker_id)
        self.stats.clear("failed:"+self.worker_id)

    def working_on(self, job):
        self.redis.set(self._redis_key("worker:"+self.worker_id),
            dict(
                queue = job['queue'],
                func = job['func'],
                args = job['args'],
                kwargs = job['kwargs'],
                run_at = time.time(),
            ))

    def done_working(self):
        self.processed()
        self.redis.delete(self._redis_key("worker:"+self.worker_id))

    def processed(self):
        self.stats.incr("processed")
        self.stats.incr("processed:" + self.worker_id)

    def failed(self):
        self.stats.incr("failed")
        self.stats.incr("failed:" + self.worker_id)

    def started(self):
        self.redis.set("worker:%s:started" % self.worker_id, time.time())

    def lookup_function(self, name):
        try:
            return self.function_cache[name]
        except KeyError:
            mod_name, func_name = name.rsplit('.', 1)
            mod = __import__(str(mod_name), {}, {}, [str(func_name)])
            func = getattr(mod, func_name)
            self.function_cache[name] = func
        return func

    #

    def workers(self):
        return self.redis.smembers(self._redis_key("workers"))

    def working(self):
        workers = self.list_workers()
        if not workers:
            return []

        keys = [self._redis_key("worker:"+x) for x in workers]
        return dict((x, y) for x, y in zip(self.redis.mget(workers, keys)))

    def worker_exists(self, worker_id):
        return self.redis.sismember(self._redis_key("workers"), worker_id)

########NEW FILE########
__FILENAME__ = hotqueue
# -*- coding: utf-8 -*-

"""HotQueue is a Python library that allows you to use Redis as a message queue
within your Python programs.
"""

from functools import wraps
try:
    import cPickle as pickle
except ImportError:
    import pickle

from redis import Redis


__all__ = ['HotQueue']

__version__ = '0.2.3'


def key_for_name(name):
    """Return the key name used to store the given queue name in Redis."""
    return 'hotqueue:%s' % name


class HotQueue(object):
    
    """Simple FIFO message queue stored in a Redis list. Example:

    >>> from hotqueue import HotQueue
    >>> queue = HotQueue("myqueue", host="localhost", port=6379, db=0)
    
    :param name: name of the queue
    :param serializer: the class or module to serialize msgs with, must have
        methods or functions named ``dumps`` and ``loads``,
        `pickle <http://docs.python.org/library/pickle.html>`_ will be used
        if ``None`` is given
    :param kwargs: additional kwargs to pass to :class:`Redis`, most commonly
        :attr:`host`, :attr:`port`, :attr:`db`
    """
    
    def __init__(self, name, serializer=None, **kwargs):
        self.name = name
        if serializer is not None:
            self.serializer = serializer
        else:
            self.serializer = pickle
        self.__redis = Redis(**kwargs)
    
    def __len__(self):
        return self.__redis.llen(self.key)
    
    def __repr__(self):
        return ('<HotQueue: \'%s\', host=\'%s\', port=%d, db=%d>' %
            (self.name, self.__redis.host, self.__redis.port, self.__redis.db))
    
    @property
    def key(self):
        """Return the key name used to store this queue in Redis."""
        return key_for_name(self.name)
    
    def clear(self):
        """Clear the queue of all messages, deleting the Redis key."""
        self.__redis.delete(self.key)
    
    def consume(self, **kwargs):
        """Return a generator that yields whenever a message is waiting in the
        queue. Will block otherwise. Example:

        >>> for msg in queue.consume(timeout=1):
        ...     print msg
        my message
        another message
        
        :param kwargs: any arguments that :meth:`~hotqueue.HotQueue.get` can
            accept (:attr:`block` will default to ``True`` if not given)
        """
        kwargs.setdefault('block', True)
        try:
            while True:
                msg = self.get(**kwargs)
                if msg is None:
                    break
                yield msg
        except KeyboardInterrupt:
            print; return
    
    def get(self, block=False, timeout=None):
        """Return a message from the queue. Example:
    
        >>> queue.get()
        'my message'
        >>> queue.get()
        'another message'
        
        :param block: whether or not to wait until a msg is available in
            the queue before returning; ``False`` by default
        :param timeout: when using :attr:`block`, if no msg is available
            for :attr:`timeout` in seconds, give up and return ``None``
        """
        if block:
            if timeout is None:
                timeout = 0
            msg = self.__redis.blpop(self.key, timeout=timeout)
            if msg is not None:
                msg = msg[1]
        else:
            msg = self.__redis.lpop(self.key)
        if msg is not None:
            msg = self.serializer.loads(msg)
        return msg
    
    def put(self, *msgs):
        """Put one or more messages onto the queue. Example:
    
        >>> queue.put("my message")
        >>> queue.put("another message")
        """
        for msg in msgs:
            msg = self.serializer.dumps(msg)
            self.__redis.rpush(self.key, msg)
    
    def worker(self, *args, **kwargs):
        """Decorator for using a function as a queue worker. Example:
    
        >>> @queue.worker(timeout=1)
        ... def printer(msg):
        ...     print msg
        >>> printer()
        my message
        another message
        
        You can also use it without passing any keyword arguments:
        
        >>> @queue.worker
        ... def printer(msg):
        ...     print msg
        >>> printer()
        my message
        another message
        
        :param kwargs: any arguments that :meth:`~hotqueue.HotQueue.get` can
            accept (:attr:`block` will default to ``True`` if not given)
        """
        def decorator(worker):
            @wraps(worker)
            def wrapper():
                for msg in self.consume(**kwargs):
                    worker(msg)
            return wrapper
        if args:
            return decorator(*args)
        return decorator


########NEW FILE########
__FILENAME__ = template
import re
import cgi

modifiers = {}
def modifier(symbol):
    """Decorator for associating a function with a Mustache tag modifier.

    @modifier('P')
    def render_tongue(self, tag_name=None, context=None):
        return ":P %s" % tag_name

    {{P yo }} => :P yo
    """
    def set_modifier(func):
        modifiers[symbol] = func
        return func
    return set_modifier

class Template(object):
    # The regular expression used to find a #section
    section_re = None

    # The regular expression used to find a tag.
    tag_re = None

    # Opening tag delimiter
    otag = '{{'

    # Closing tag delimiter
    ctag = '}}'

    def __init__(self, template, context=None):
        self.template = template
        self.context = context or {}
        self.compile_regexps()

    def render(self, template=None, context=None, encoding=None):
        """Turns a Mustache template into something wonderful."""
        template = template or self.template
        context = context or self.context

        template = self.render_sections(template, context)
        result = self.render_tags(template, context)
        if encoding is not None:
            result = result.encode(encoding)
        return result

    def compile_regexps(self):
        """Compiles our section and tag regular expressions."""
        tags = { 'otag': re.escape(self.otag), 'ctag': re.escape(self.ctag) }

        section = r"%(otag)s[\#|^]([^\}]*)%(ctag)s\s*(.+?)\s*%(otag)s/\1%(ctag)s"
        self.section_re = re.compile(section % tags, re.M|re.S)

        tag = r"%(otag)s(#|=|&|!|>|\{)?(.+?)\1?%(ctag)s+"
        self.tag_re = re.compile(tag % tags)

    def render_sections(self, template, context):
        """Expands sections."""
        while 1:
            match = self.section_re.search(template)
            if match is None:
                break

            section, section_name, inner = match.group(0, 1, 2)
            section_name = section_name.strip()

            it = context.get(section_name, None)
            replacer = ''
            if it and hasattr(it, '__call__'):
                replacer = it(inner)
            elif it and not hasattr(it, '__iter__'):
                if section[2] != '^':
                    replacer = inner
            elif it:
                insides = []
                for item in it:
                    insides.append(self.render(inner, item))
                replacer = ''.join(insides)
            elif not it and section[2] == '^':
                replacer = inner

            template = template.replace(section, replacer)

        return template

    def render_tags(self, template, context):
        """Renders all the tags in a template for a context."""
        while 1:
            match = self.tag_re.search(template)
            if match is None:
                break

            tag, tag_type, tag_name = match.group(0, 1, 2)
            tag_name = tag_name.strip()
            func = modifiers[tag_type]
            replacement = func(self, tag_name, context)
            template = template.replace(tag, replacement)

        return template

    @modifier(None)
    def render_tag(self, tag_name, context):
        """Given a tag name and context, finds, escapes, and renders the tag."""
        raw = context.get(tag_name, '')
        if not raw and raw is not 0:
            return ''
        return cgi.escape(unicode(raw))

    @modifier('!')
    def render_comment(self, tag_name=None, context=None):
        """Rendering a comment always returns nothing."""
        return ''

    @modifier('{')
    @modifier('&')
    def render_unescaped(self, tag_name=None, context=None):
        """Render a tag without escaping it."""
        return unicode(context.get(tag_name, ''))

    @modifier('>')
    def render_partial(self, tag_name=None, context=None):
        """Renders a partial within the current context."""
        # Import view here to avoid import loop
        from pystache.view import View

        view = View(context=context)
        view.template_name = tag_name

        return view.render()

    @modifier('=')
    def render_delimiter(self, tag_name=None, context=None):
        """Changes the Mustache delimiter."""
        self.otag, self.ctag = tag_name.split(' ')
        self.compile_regexps()
        return ''

########NEW FILE########
__FILENAME__ = view
from pystache import Template
import os.path
import re

class View(object):
    # Path where this view's template(s) live
    template_path = '.'

    # Extension for templates
    template_extension = 'mustache'

    # The name of this template. If none is given the View will try
    # to infer it based on the class name.
    template_name = None

    # Absolute path to the template itself. Pystache will try to guess
    # if it's not provided.
    template_file = None

    # Contents of the template.
    template = None
    
    # Character encoding of the template file. If None, Pystache will not
    # do any decoding of the template.
    template_encoding = None

    def __init__(self, template=None, context=None, **kwargs):
        self.template = template
        self.context = context or {}

        # If the context we're handed is a View, we want to inherit
        # its settings.
        if isinstance(context, View):
            self.inherit_settings(context)

        if kwargs:
            self.context.update(kwargs)

    def inherit_settings(self, view):
        """Given another View, copies its settings."""
        if view.template_path:
            self.template_path = view.template_path

        if view.template_name:
            self.template_name = view.template_name

    def __contains__(self, needle):
        return hasattr(self, needle)

    def __getitem__(self, attr):
        return getattr(self, attr)()

    def load_template(self):
        if self.template:
            return self.template
        
        if self.template_file:
            return self._load_template()
        
        name = self.get_template_name() + '.' + self.template_extension
        
        if isinstance(self.template_path, basestring):
            self.template_file = os.path.join(self.template_path, name)
            return self._load_template()
        
        for path in self.template_path:
            self.template_file = os.path.join(path, name)
            if os.path.exists(self.template_file):
                return self._load_template()
        
        raise IOError('"%s" not found in "%s"' % (name, ':'.join(self.template_path),))

    
    def _load_template(self):
        f = open(self.template_file, 'r')
        try:
            template = f.read()
            if self.template_encoding:
                template = unicode(template, self.template_encoding)
        finally:
            f.close()
        return template

    def get_template_name(self, name=None):
        """TemplatePartial => template_partial
        Takes a string but defaults to using the current class' name or
        the `template_name` attribute
        """
        if self.template_name:
            return self.template_name

        if not name:
            name = self.__class__.__name__

        def repl(match):
            return '_' + match.group(0).lower()

        return re.sub('[A-Z]', repl, name)[1:]

    def get(self, attr, default):
        attr = self.context.get(attr, getattr(self, attr, default))

        if hasattr(attr, '__call__'):
            return attr()
        else:
            return attr

    def render(self, encoding=None):
        template = self.load_template()
        return Template(template, self).render(encoding=encoding)

    def __str__(self):
        return self.render()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# bricklayer documentation build configuration file, created by
# sphinx-quickstart on Wed Aug  1 14:40:54 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.mathjax', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bricklayer'
copyright = u'2012, Rodrigo Sampaio Vaz, Locaweb'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = "2.3.0"
# The full version, including alpha/beta/rc tags.
release = version

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
exclude_patterns = ["**/README.rst", "README.rst"]

# The reST default role (used for this markup: `text`) to use for all documents.
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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx-bootstrap'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'analytics_code': 'UA-00000000-1',
    'github_user': 'locaweb',
    'github_repo': 'bricklayer',
    'home_url': 'http://bricklayer.rtfd.org',
    'bootstrap_theme': 'http://locastyle.locaweb.com.br/assets/application-e7ba404862b7d5783463257cae9438e3.css'
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_themes"]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = '_static/locaweb.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'bricklayer'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
'papersize': 'a4paper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'bricklayer.tex', u'Bricklayer Documentation',
   u'Rodrigo Sampaio Vaz, Locaweb', 'manual'),
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


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bricklayer', u'Bricklayer Documentation',
     [u'Rodrigo Sampaio Vaz, Locaweb'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'bricklayer', u'Bricklayer Documentation',
   u'Rodrigo Sampaio Vaz, Locaweb', 'Bricklayer', 'Package build system',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Bricklayer'
epub_author = u'Rodrigo Sampaio Vaz, Locaweb'
epub_publisher = u'Rodrigo Sampaio Vaz, Locaweb'
epub_copyright = u'2012, Rodrigo Sampaio Vaz. Locaweb'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
# intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = mocker
"""
Mocker

Graceful platform for test doubles in Python: mocks, stubs, fakes, and dummies.

Copyright (c) 2007-2010, Gustavo Niemeyer <gustavo@niemeyer.net>

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the copyright holder nor the names of its
      contributors may be used to endorse or promote products derived from
      this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import __builtin__
import tempfile
import unittest
import inspect
import shutil
import types
import sys
import os
import re
import gc


if sys.version_info < (2, 4):
    from sets import Set as set # pragma: nocover


__all__ = ["Mocker", "Expect", "expect", "IS", "CONTAINS", "IN", "MATCH",
           "ANY", "ARGS", "KWARGS", "MockerTestCase"]


__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "BSD"
__version__ = "1.1"


ERROR_PREFIX = "[Mocker] "


# --------------------------------------------------------------------
# Exceptions

class MatchError(AssertionError):
    """Raised when an unknown expression is seen in playback mode."""


# --------------------------------------------------------------------
# Helper for chained-style calling.

class expect(object):
    """This is a simple helper that allows a different call-style.

    With this class one can comfortably do chaining of calls to the
    mocker object responsible by the object being handled. For instance::

        expect(obj.attr).result(3).count(1, 2)

    Is the same as::

        obj.attr
        mocker.result(3)
        mocker.count(1, 2)

    """

    __mocker__ = None

    def __init__(self, mock, attr=None):
        self._mock = mock
        self._attr = attr

    def __getattr__(self, attr):
        return self.__class__(self._mock, attr)

    def __call__(self, *args, **kwargs):
        mocker = self.__mocker__
        if not mocker:
            mocker = self._mock.__mocker__
        getattr(mocker, self._attr)(*args, **kwargs)
        return self


def Expect(mocker):
    """Create an expect() "function" using the given Mocker instance.

    This helper allows defining an expect() "function" which works even
    in trickier cases such as:

        expect = Expect(mymocker)
        expect(iter(mock)).generate([1, 2, 3])

    """
    return type("Expect", (expect,), {"__mocker__": mocker})


# --------------------------------------------------------------------
# Extensions to Python's unittest.

class MockerTestCase(unittest.TestCase):
    """unittest.TestCase subclass with Mocker support.

    @ivar mocker: The mocker instance.

    This is a convenience only.  Mocker may easily be used with the
    standard C{unittest.TestCase} class if wanted.

    Test methods have a Mocker instance available on C{self.mocker}.
    At the end of each test method, expectations of the mocker will
    be verified, and any requested changes made to the environment
    will be restored.

    In addition to the integration with Mocker, this class provides
    a few additional helper methods.
    """

    def __init__(self, methodName="runTest"):
        # So here is the trick: we take the real test method, wrap it on
        # a function that do the job we have to do, and insert it in the
        # *instance* dictionary, so that getattr() will return our
        # replacement rather than the class method.
        test_method = getattr(self, methodName, None)
        if test_method is not None:
            def test_method_wrapper():
                try:
                    result = test_method()
                except:
                    raise
                else:
                    if (self.mocker.is_recording() and
                        self.mocker.get_events()):
                        raise RuntimeError("Mocker must be put in replay "
                                           "mode with self.mocker.replay()")
                    if (hasattr(result, "addCallback") and
                        hasattr(result, "addErrback")):
                        def verify(result):
                            self.mocker.verify()
                            return result
                        result.addCallback(verify)
                    else:
                        self.mocker.verify()
                        self.mocker.restore()
                    return result
            # Copy all attributes from the original method..
            for attr in dir(test_method):
                # .. unless they're present in our wrapper already.
                if not hasattr(test_method_wrapper, attr) or attr == "__doc__":
                    setattr(test_method_wrapper, attr,
                            getattr(test_method, attr))
            setattr(self, methodName, test_method_wrapper)

        # We could overload run() normally, but other well-known testing
        # frameworks do it as well, and some of them won't call the super,
        # which might mean that cleanup wouldn't happen.  With that in mind,
        # we make integration easier by using the following trick.
        run_method = self.run
        def run_wrapper(*args, **kwargs):
            try:
                return run_method(*args, **kwargs)
            finally:
                self.__cleanup()
        self.run = run_wrapper

        self.mocker = Mocker()
        self.expect = Expect(self.mocker)

        self.__cleanup_funcs = []
        self.__cleanup_paths = []

        super(MockerTestCase, self).__init__(methodName)

    def __call__(self, *args, **kwargs):
        # This is necessary for Python 2.3 only, because it didn't use run(),
        # which is supported above.
        try:
            super(MockerTestCase, self).__call__(*args, **kwargs)
        finally:
            if sys.version_info < (2, 4):
                self.__cleanup()

    def __cleanup(self):
        for path in self.__cleanup_paths:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        self.mocker.reset()
        for func, args, kwargs in self.__cleanup_funcs:
            func(*args, **kwargs)

    def addCleanup(self, func, *args, **kwargs):
        self.__cleanup_funcs.append((func, args, kwargs))

    def makeFile(self, content=None, suffix="", prefix="tmp", basename=None,
                 dirname=None, path=None):
        """Create a temporary file and return the path to it.

        @param content: Initial content for the file.
        @param suffix: Suffix to be given to the file's basename.
        @param prefix: Prefix to be given to the file's basename.
        @param basename: Full basename for the file.
        @param dirname: Put file inside this directory.

        The file is removed after the test runs.
        """
        if path is not None:
            self.__cleanup_paths.append(path)
        elif basename is not None:
            if dirname is None:
                dirname = tempfile.mkdtemp()
                self.__cleanup_paths.append(dirname)
            path = os.path.join(dirname, basename)
        else:
            fd, path = tempfile.mkstemp(suffix, prefix, dirname)
            self.__cleanup_paths.append(path)
            os.close(fd)
            if content is None:
                os.unlink(path)
        if content is not None:
            file = open(path, "w")
            file.write(content)
            file.close()
        return path

    def makeDir(self, suffix="", prefix="tmp", dirname=None, path=None):
        """Create a temporary directory and return the path to it.

        @param suffix: Suffix to be given to the file's basename.
        @param prefix: Prefix to be given to the file's basename.
        @param dirname: Put directory inside this parent directory.

        The directory is removed after the test runs.
        """
        if path is not None:
            os.makedirs(path)
        else:
            path = tempfile.mkdtemp(suffix, prefix, dirname)
        self.__cleanup_paths.append(path)
        return path

    def failUnlessIs(self, first, second, msg=None):
        """Assert that C{first} is the same object as C{second}."""
        if first is not second:
            raise self.failureException(msg or "%r is not %r" % (first, second))

    def failIfIs(self, first, second, msg=None):
        """Assert that C{first} is not the same object as C{second}."""
        if first is second:
            raise self.failureException(msg or "%r is %r" % (first, second))

    def failUnlessIn(self, first, second, msg=None):
        """Assert that C{first} is contained in C{second}."""
        if first not in second:
            raise self.failureException(msg or "%r not in %r" % (first, second))

    def failUnlessStartsWith(self, first, second, msg=None):
        """Assert that C{first} starts with C{second}."""
        if first[:len(second)] != second:
            raise self.failureException(msg or "%r doesn't start with %r" %
                                               (first, second))

    def failIfStartsWith(self, first, second, msg=None):
        """Assert that C{first} doesn't start with C{second}."""
        if first[:len(second)] == second:
            raise self.failureException(msg or "%r starts with %r" %
                                               (first, second))

    def failUnlessEndsWith(self, first, second, msg=None):
        """Assert that C{first} starts with C{second}."""
        if first[len(first)-len(second):] != second:
            raise self.failureException(msg or "%r doesn't end with %r" %
                                               (first, second))

    def failIfEndsWith(self, first, second, msg=None):
        """Assert that C{first} doesn't start with C{second}."""
        if first[len(first)-len(second):] == second:
            raise self.failureException(msg or "%r ends with %r" %
                                               (first, second))

    def failIfIn(self, first, second, msg=None):
        """Assert that C{first} is not contained in C{second}."""
        if first in second:
            raise self.failureException(msg or "%r in %r" % (first, second))

    def failUnlessApproximates(self, first, second, tolerance, msg=None):
        """Assert that C{first} is near C{second} by at most C{tolerance}."""
        if abs(first - second) > tolerance:
            raise self.failureException(msg or "abs(%r - %r) > %r" %
                                        (first, second, tolerance))

    def failIfApproximates(self, first, second, tolerance, msg=None):
        """Assert that C{first} is far from C{second} by at least C{tolerance}.
        """
        if abs(first - second) <= tolerance:
            raise self.failureException(msg or "abs(%r - %r) <= %r" %
                                        (first, second, tolerance))

    def failUnlessMethodsMatch(self, first, second):
        """Assert that public methods in C{first} are present in C{second}.

        This method asserts that all public methods found in C{first} are also
        present in C{second} and accept the same arguments.  C{first} may
        have its own private methods, though, and may not have all methods
        found in C{second}.  Note that if a private method in C{first} matches
        the name of one in C{second}, their specification is still compared.

        This is useful to verify if a fake or stub class have the same API as
        the real class being simulated.
        """
        first_methods = dict(inspect.getmembers(first, inspect.ismethod))
        second_methods = dict(inspect.getmembers(second, inspect.ismethod))
        for name, first_method in first_methods.iteritems():
            first_argspec = inspect.getargspec(first_method)
            first_formatted = inspect.formatargspec(*first_argspec)

            second_method = second_methods.get(name)
            if second_method is None:
                if name[:1] == "_":
                    continue # First may have its own private methods.
                raise self.failureException("%s.%s%s not present in %s" %
                    (first.__name__, name, first_formatted, second.__name__))

            second_argspec = inspect.getargspec(second_method)
            if first_argspec != second_argspec:
                second_formatted = inspect.formatargspec(*second_argspec)
                raise self.failureException("%s.%s%s != %s.%s%s" %
                    (first.__name__, name, first_formatted,
                     second.__name__, name, second_formatted))

    def failUnlessRaises(self, excClass, *args, **kwargs):
        """
        Fail unless an exception of class excClass is thrown by callableObj
        when invoked with arguments args and keyword arguments kwargs. If a
        different type of exception is thrown, it will not be caught, and the
        test case will be deemed to have suffered an error, exactly as for an
        unexpected exception. It returns the exception instance if it matches
        the given exception class.

        This may also be used as a context manager when provided with a single
        argument, as such:

        with self.failUnlessRaises(ExcClass):
            logic_which_should_raise()
        """
        return self.failUnlessRaisesRegexp(excClass, None, *args, **kwargs)

    def failUnlessRaisesRegexp(self, excClass, regexp, *args, **kwargs):
        """
        Fail unless an exception of class excClass is thrown by callableObj
        when invoked with arguments args and keyword arguments kwargs, and
        the str(error) value matches the provided regexp. If a different type
        of exception is thrown, it will not be caught, and the test case will
        be deemed to have suffered an error, exactly as for an unexpected
        exception. It returns the exception instance if it matches the given
        exception class.

        This may also be used as a context manager when provided with a single
        argument, as such:

        with self.failUnlessRaisesRegexp(ExcClass, "something like.*happened"):
            logic_which_should_raise()
        """
        def match_regexp(error):
            error_str = str(error)
            if regexp is not None and not re.search(regexp, error_str):
                raise self.failureException("%r doesn't match %r" %
                                            (error_str, regexp))
        excName = self.__class_name(excClass)
        if args:
            callableObj = args[0]
            try:
                result = callableObj(*args[1:], **kwargs)
            except excClass, e:
                match_regexp(e)
                return e
            else:
                raise self.failureException("%s not raised (%r returned)" %
                                            (excName, result))
        else:
            test = self
            class AssertRaisesContextManager(object):
                def __enter__(self):
                    return self
                def __exit__(self, type, value, traceback):
                    self.exception = value
                    if value is None:
                        raise test.failureException("%s not raised" % excName)
                    elif isinstance(value, excClass):
                        match_regexp(value)
                        return True
            return AssertRaisesContextManager()

    def __class_name(self, cls):
        return getattr(cls, "__name__", str(cls))

    def failUnlessIsInstance(self, obj, cls, msg=None):
        """Assert that isinstance(obj, cls)."""
        if not isinstance(obj, cls):
            if msg is None:
                msg = "%r is not an instance of %s" % \
                      (obj, self.__class_name(cls))
            raise self.failureException(msg)

    def failIfIsInstance(self, obj, cls, msg=None):
        """Assert that isinstance(obj, cls) is False."""
        if isinstance(obj, cls):
            if msg is None:
                msg = "%r is an instance of %s" % \
                      (obj, self.__class_name(cls))
            raise self.failureException(msg)

    assertIs = failUnlessIs
    assertIsNot = failIfIs
    assertIn = failUnlessIn
    assertNotIn = failIfIn
    assertStartsWith = failUnlessStartsWith
    assertNotStartsWith = failIfStartsWith
    assertEndsWith = failUnlessEndsWith
    assertNotEndsWith = failIfEndsWith
    assertApproximates = failUnlessApproximates
    assertNotApproximates = failIfApproximates
    assertMethodsMatch = failUnlessMethodsMatch
    assertRaises = failUnlessRaises
    assertRaisesRegexp = failUnlessRaisesRegexp
    assertIsInstance = failUnlessIsInstance
    assertIsNotInstance = failIfIsInstance
    assertNotIsInstance = failIfIsInstance # Poor choice in 2.7/3.2+.

    # The following are missing in Python < 2.4.
    assertTrue = unittest.TestCase.failUnless
    assertFalse = unittest.TestCase.failIf

    # The following is provided for compatibility with Twisted's trial.
    assertIdentical = assertIs
    assertNotIdentical = assertIsNot
    failUnlessIdentical = failUnlessIs
    failIfIdentical = failIfIs


# --------------------------------------------------------------------
# Mocker.

class classinstancemethod(object):

    def __init__(self, method):
        self.method = method

    def __get__(self, obj, cls=None):
        def bound_method(*args, **kwargs):
            return self.method(cls, obj, *args, **kwargs)
        return bound_method


class MockerBase(object):
    """Controller of mock objects.

    A mocker instance is used to command recording and replay of
    expectations on any number of mock objects.

    Expectations should be expressed for the mock object while in
    record mode (the initial one) by using the mock object itself,
    and using the mocker (and/or C{expect()} as a helper) to define
    additional behavior for each event.  For instance::

        mock = mocker.mock()
        mock.hello()
        mocker.result("Hi!")
        mocker.replay()
        assert mock.hello() == "Hi!"
        mock.restore()
        mock.verify()

    In this short excerpt a mock object is being created, then an
    expectation of a call to the C{hello()} method was recorded, and
    when called the method should return the value C{10}.  Then, the
    mocker is put in replay mode, and the expectation is satisfied by
    calling the C{hello()} method, which indeed returns 10.  Finally,
    a call to the L{restore()} method is performed to undo any needed
    changes made in the environment, and the L{verify()} method is
    called to ensure that all defined expectations were met.

    The same logic can be expressed more elegantly using the
    C{with mocker:} statement, as follows::

        mock = mocker.mock()
        mock.hello()
        mocker.result("Hi!")
        with mocker:
            assert mock.hello() == "Hi!"

    Also, the MockerTestCase class, which integrates the mocker on
    a unittest.TestCase subclass, may be used to reduce the overhead
    of controlling the mocker.  A test could be written as follows::

        class SampleTest(MockerTestCase):

            def test_hello(self):
                mock = self.mocker.mock()
                mock.hello()
                self.mocker.result("Hi!")
                self.mocker.replay()
                self.assertEquals(mock.hello(), "Hi!")
    """

    _recorders = []

    # For convenience only.
    on = expect

    class __metaclass__(type):
        def __init__(self, name, bases, dict):
            # Make independent lists on each subclass, inheriting from parent.
            self._recorders = list(getattr(self, "_recorders", ()))

    def __init__(self):
        self._recorders = self._recorders[:]
        self._events = []
        self._recording = True
        self._ordering = False
        self._last_orderer = None

    def is_recording(self):
        """Return True if in recording mode, False if in replay mode.

        Recording is the initial state.
        """
        return self._recording

    def replay(self):
        """Change to replay mode, where recorded events are reproduced.

        If already in replay mode, the mocker will be restored, with all
        expectations reset, and then put again in replay mode.

        An alternative and more comfortable way to replay changes is
        using the 'with' statement, as follows::

            mocker = Mocker()
            <record events>
            with mocker:
                <reproduce events>

        The 'with' statement will automatically put mocker in replay
        mode, and will also verify if all events were correctly reproduced
        at the end (using L{verify()}), and also restore any changes done
        in the environment (with L{restore()}).

        Also check the MockerTestCase class, which integrates the
        unittest.TestCase class with mocker.
        """
        if not self._recording:
            for event in self._events:
                event.restore()
        else:
            self._recording = False
        for event in self._events:
            event.replay()

    def restore(self):
        """Restore changes in the environment, and return to recording mode.

        This should always be called after the test is complete (succeeding
        or not).  There are ways to call this method automatically on
        completion (e.g. using a C{with mocker:} statement, or using the
        L{MockerTestCase} class.
        """
        if not self._recording:
            self._recording = True
            for event in self._events:
                event.restore()

    def reset(self):
        """Reset the mocker state.

        This will restore environment changes, if currently in replay
        mode, and then remove all events previously recorded.
        """
        if not self._recording:
            self.restore()
        self.unorder()
        del self._events[:]

    def get_events(self):
        """Return all recorded events."""
        return self._events[:]

    def add_event(self, event):
        """Add an event.

        This method is used internally by the implementation, and
        shouldn't be needed on normal mocker usage.
        """
        self._events.append(event)
        if self._ordering:
            orderer = event.add_task(Orderer(event.path))
            if self._last_orderer:
                orderer.add_dependency(self._last_orderer)
            self._last_orderer = orderer
        return event

    def verify(self):
        """Check if all expectations were met, and raise AssertionError if not.

        The exception message will include a nice description of which
        expectations were not met, and why.
        """
        errors = []
        for event in self._events:
            try:
                event.verify()
            except AssertionError, e:
                error = str(e)
                if not error:
                    raise RuntimeError("Empty error message from %r"
                                       % event)
                errors.append(error)
        if errors:
            message = [ERROR_PREFIX + "Unmet expectations:", ""]
            for error in errors:
                lines = error.splitlines()
                message.append("=> " + lines.pop(0))
                message.extend([" " + line for line in lines])
                message.append("")
            raise AssertionError(os.linesep.join(message))

    def mock(self, spec_and_type=None, spec=None, type=None,
             name=None, count=True):
        """Return a new mock object.

        @param spec_and_type: Handy positional argument which sets both
                     spec and type.
        @param spec: Method calls will be checked for correctness against
                     the given class.
        @param type: If set, the Mock's __class__ attribute will return
                     the given type.  This will make C{isinstance()} calls
                     on the object work.
        @param name: Name for the mock object, used in the representation of
                     expressions.  The name is rarely needed, as it's usually
                     guessed correctly from the variable name used.
        @param count: If set to false, expressions may be executed any number
                     of times, unless an expectation is explicitly set using
                     the L{count()} method.  By default, expressions are
                     expected once.
        """
        if spec_and_type is not None:
            spec = type = spec_and_type
        return Mock(self, spec=spec, type=type, name=name, count=count)

    def proxy(self, object, spec=True, type=True, name=None, count=True,
              passthrough=True):
        """Return a new mock object which proxies to the given object.
 
        Proxies are useful when only part of the behavior of an object
        is to be mocked.  Unknown expressions may be passed through to
        the real implementation implicitly (if the C{passthrough} argument
        is True), or explicitly (using the L{passthrough()} method
        on the event).

        @param object: Real object to be proxied, and replaced by the mock
                       on replay mode.  It may also be an "import path",
                       such as C{"time.time"}, in which case the object
                       will be the C{time} function from the C{time} module.
        @param spec: Method calls will be checked for correctness against
                     the given object, which may be a class or an instance
                     where attributes will be looked up.  Defaults to the
                     the C{object} parameter.  May be set to None explicitly,
                     in which case spec checking is disabled.  Checks may
                     also be disabled explicitly on a per-event basis with
                     the L{nospec()} method.
        @param type: If set, the Mock's __class__ attribute will return
                     the given type.  This will make C{isinstance()} calls
                     on the object work.  Defaults to the type of the
                     C{object} parameter.  May be set to None explicitly.
        @param name: Name for the mock object, used in the representation of
                     expressions.  The name is rarely needed, as it's usually
                     guessed correctly from the variable name used.
        @param count: If set to false, expressions may be executed any number
                     of times, unless an expectation is explicitly set using
                     the L{count()} method.  By default, expressions are
                     expected once.
        @param passthrough: If set to False, passthrough of actions on the
                            proxy to the real object will only happen when
                            explicitly requested via the L{passthrough()}
                            method.
        """
        if isinstance(object, basestring):
            if name is None:
                name = object
            import_stack = object.split(".")
            attr_stack = []
            while import_stack:
                module_path = ".".join(import_stack)
                try:
                    __import__(module_path)
                except ImportError:
                    attr_stack.insert(0, import_stack.pop())
                    if not import_stack:
                        raise
                    continue
                else:
                    object = sys.modules[module_path]
                    for attr in attr_stack:
                        object = getattr(object, attr)
                    break
        if isinstance(object, types.UnboundMethodType):
            object = object.im_func
        if spec is True:
            spec = object
        if type is True:
            type = __builtin__.type(object)
        return Mock(self, spec=spec, type=type, object=object,
                    name=name, count=count, passthrough=passthrough)

    def replace(self, object, spec=True, type=True, name=None, count=True,
                passthrough=True):
        """Create a proxy, and replace the original object with the mock.

        On replay, the original object will be replaced by the returned
        proxy in all dictionaries found in the running interpreter via
        the garbage collecting system.  This should cover module
        namespaces, class namespaces, instance namespaces, and so on.

        @param object: Real object to be proxied, and replaced by the mock
                       on replay mode.  It may also be an "import path",
                       such as C{"time.time"}, in which case the object
                       will be the C{time} function from the C{time} module.
        @param spec: Method calls will be checked for correctness against
                     the given object, which may be a class or an instance
                     where attributes will be looked up.  Defaults to the
                     the C{object} parameter.  May be set to None explicitly,
                     in which case spec checking is disabled.  Checks may
                     also be disabled explicitly on a per-event basis with
                     the L{nospec()} method.
        @param type: If set, the Mock's __class__ attribute will return
                     the given type.  This will make C{isinstance()} calls
                     on the object work.  Defaults to the type of the
                     C{object} parameter.  May be set to None explicitly.
        @param name: Name for the mock object, used in the representation of
                     expressions.  The name is rarely needed, as it's usually
                     guessed correctly from the variable name used.
        @param passthrough: If set to False, passthrough of actions on the
                            proxy to the real object will only happen when
                            explicitly requested via the L{passthrough()}
                            method.
        """
        mock = self.proxy(object, spec, type, name, count, passthrough)
        event = self._get_replay_restore_event()
        event.add_task(ProxyReplacer(mock))
        return mock

    def patch(self, object, spec=True):
        """Patch an existing object to reproduce recorded events.

        @param object: Class or instance to be patched.
        @param spec: Method calls will be checked for correctness against
                     the given object, which may be a class or an instance
                     where attributes will be looked up.  Defaults to the
                     the C{object} parameter.  May be set to None explicitly,
                     in which case spec checking is disabled.  Checks may
                     also be disabled explicitly on a per-event basis with
                     the L{nospec()} method.

        The result of this method is still a mock object, which can be
        used like any other mock object to record events.  The difference
        is that when the mocker is put on replay mode, the *real* object
        will be modified to behave according to recorded expectations.

        Patching works in individual instances, and also in classes.
        When an instance is patched, recorded events will only be
        considered on this specific instance, and other instances should
        behave normally.  When a class is patched, the reproduction of
        events will be considered on any instance of this class once
        created (collectively).

        Observe that, unlike with proxies which catch only events done
        through the mock object, *all* accesses to recorded expectations
        will be considered;  even these coming from the object itself
        (e.g. C{self.hello()} is considered if this method was patched).
        While this is a very powerful feature, and many times the reason
        to use patches in the first place, it's important to keep this
        behavior in mind.

        Patching of the original object only takes place when the mocker
        is put on replay mode, and the patched object will be restored
        to its original state once the L{restore()} method is called
        (explicitly, or implicitly with alternative conventions, such as
        a C{with mocker:} block, or a MockerTestCase class).
        """
        if spec is True:
            spec = object
        patcher = Patcher()
        event = self._get_replay_restore_event()
        event.add_task(patcher)
        mock = Mock(self, object=object, patcher=patcher,
                    passthrough=True, spec=spec)
        patcher.patch_attr(object, '__mocker_mock__', mock)
        return mock

    def act(self, path):
        """This is called by mock objects whenever something happens to them.

        This method is part of the interface between the mocker
        and mock objects.
        """
        if self._recording:
            event = self.add_event(Event(path))
            for recorder in self._recorders:
                recorder(self, event)
            return Mock(self, path)
        else:
            # First run events that may run, then run unsatisfied events, then
            # ones not previously run. We put the index in the ordering tuple
            # instead of the actual event because we want a stable sort
            # (ordering between 2 events is undefined).
            events = self._events
            order = [(events[i].satisfied()*2 + events[i].has_run(), i)
                     for i in range(len(events))]
            order.sort()
            postponed = None
            for weight, i in order:
                event = events[i]
                if event.matches(path):
                    if event.may_run(path):
                        return event.run(path)
                    elif postponed is None:
                        postponed = event
            if postponed is not None:
                return postponed.run(path)
            raise MatchError(ERROR_PREFIX + "Unexpected expression: %s" % path)

    def get_recorders(cls, self):
        """Return recorders associated with this mocker class or instance.

        This method may be called on mocker instances and also on mocker
        classes.  See the L{add_recorder()} method for more information.
        """
        return (self or cls)._recorders[:]
    get_recorders = classinstancemethod(get_recorders)

    def add_recorder(cls, self, recorder):
        """Add a recorder to this mocker class or instance.

        @param recorder: Callable accepting C{(mocker, event)} as parameters.

        This is part of the implementation of mocker.

        All registered recorders are called for translating events that
        happen during recording into expectations to be met once the state
        is switched to replay mode.

        This method may be called on mocker instances and also on mocker
        classes.  When called on a class, the recorder will be used by
        all instances, and also inherited on subclassing.  When called on
        instances, the recorder is added only to the given instance.
        """
        (self or cls)._recorders.append(recorder)
        return recorder
    add_recorder = classinstancemethod(add_recorder)

    def remove_recorder(cls, self, recorder):
        """Remove the given recorder from this mocker class or instance.

        This method may be called on mocker classes and also on mocker
        instances.  See the L{add_recorder()} method for more information.
        """
        (self or cls)._recorders.remove(recorder)
    remove_recorder = classinstancemethod(remove_recorder)

    def result(self, value):
        """Make the last recorded event return the given value on replay.
        
        @param value: Object to be returned when the event is replayed.
        """
        self.call(lambda *args, **kwargs: value)

    def generate(self, sequence):
        """Last recorded event will return a generator with the given sequence.

        @param sequence: Sequence of values to be generated.
        """
        def generate(*args, **kwargs):
            for value in sequence:
                yield value
        self.call(generate)

    def throw(self, exception):
        """Make the last recorded event raise the given exception on replay.

        @param exception: Class or instance of exception to be raised.
        """
        def raise_exception(*args, **kwargs):
            raise exception
        self.call(raise_exception)

    def call(self, func, with_object=False):
        """Make the last recorded event cause the given function to be called.

        @param func: Function to be called.
		@param with_object: If True, the called function will receive the
		    patched or proxied object so that its state may be used or verified
			in checks.

        The result of the function will be used as the event result.
        """
        event = self._events[-1]
        if with_object and event.path.root_object is None:
            raise TypeError("Mock object isn't a proxy")
        event.add_task(FunctionRunner(func, with_root_object=with_object))

    def count(self, min, max=False):
        """Last recorded event must be replayed between min and max times.

        @param min: Minimum number of times that the event must happen.
        @param max: Maximum number of times that the event must happen.  If
                    not given, it defaults to the same value of the C{min}
                    parameter.  If set to None, there is no upper limit, and
                    the expectation is met as long as it happens at least
                    C{min} times.
        """
        event = self._events[-1]
        for task in event.get_tasks():
            if isinstance(task, RunCounter):
                event.remove_task(task)
        event.prepend_task(RunCounter(min, max))

    def is_ordering(self):
        """Return true if all events are being ordered.

        See the L{order()} method.
        """
        return self._ordering

    def unorder(self):
        """Disable the ordered mode.
        
        See the L{order()} method for more information.
        """
        self._ordering = False
        self._last_orderer = None

    def order(self, *path_holders):
        """Create an expectation of order between two or more events.

        @param path_holders: Objects returned as the result of recorded events.

        By default, mocker won't force events to happen precisely in
        the order they were recorded.  Calling this method will change
        this behavior so that events will only match if reproduced in
        the correct order.

        There are two ways in which this method may be used.  Which one
        is used in a given occasion depends only on convenience.

        If no arguments are passed, the mocker will be put in a mode where
        all the recorded events following the method call will only be met
        if they happen in order.  When that's used, the mocker may be put
        back in unordered mode by calling the L{unorder()} method, or by
        using a 'with' block, like so::

            with mocker.ordered():
                <record events>

        In this case, only expressions in <record events> will be ordered,
        and the mocker will be back in unordered mode after the 'with' block.

        The second way to use it is by specifying precisely which events
        should be ordered.  As an example::

            mock = mocker.mock()
            expr1 = mock.hello()
            expr2 = mock.world
            expr3 = mock.x.y.z
            mocker.order(expr1, expr2, expr3)

        This method of ordering only works when the expression returns
        another object.

        Also check the L{after()} and L{before()} methods, which are
        alternative ways to perform this.
        """
        if not path_holders:
            self._ordering = True
            return OrderedContext(self)

        last_orderer = None
        for path_holder in path_holders:
            if type(path_holder) is Path:
                path = path_holder
            else:
                path = path_holder.__mocker_path__
            for event in self._events:
                if event.path is path:
                    for task in event.get_tasks():
                        if isinstance(task, Orderer):
                            orderer = task
                            break
                    else:
                        orderer = Orderer(path)
                        event.add_task(orderer)
                    if last_orderer:
                        orderer.add_dependency(last_orderer)
                    last_orderer = orderer
                    break

    def after(self, *path_holders):
        """Last recorded event must happen after events referred to.

        @param path_holders: Objects returned as the result of recorded events
                             which should happen before the last recorded event

        As an example, the idiom::

            expect(mock.x).after(mock.y, mock.z)

        is an alternative way to say::

            expr_x = mock.x
            expr_y = mock.y
            expr_z = mock.z
            mocker.order(expr_y, expr_x)
            mocker.order(expr_z, expr_x)

        See L{order()} for more information.
        """
        last_path = self._events[-1].path
        for path_holder in path_holders:
            self.order(path_holder, last_path)

    def before(self, *path_holders):
        """Last recorded event must happen before events referred to.

        @param path_holders: Objects returned as the result of recorded events
                             which should happen after the last recorded event

        As an example, the idiom::

            expect(mock.x).before(mock.y, mock.z)

        is an alternative way to say::

            expr_x = mock.x
            expr_y = mock.y
            expr_z = mock.z
            mocker.order(expr_x, expr_y)
            mocker.order(expr_x, expr_z)

        See L{order()} for more information.
        """
        last_path = self._events[-1].path
        for path_holder in path_holders:
            self.order(last_path, path_holder)

    def nospec(self):
        """Don't check method specification of real object on last event.

        By default, when using a mock created as the result of a call to
        L{proxy()}, L{replace()}, and C{patch()}, or when passing the spec
        attribute to the L{mock()} method, method calls on the given object
        are checked for correctness against the specification of the real
        object (or the explicitly provided spec).

        This method will disable that check specifically for the last
        recorded event.
        """
        event = self._events[-1]
        for task in event.get_tasks():
            if isinstance(task, SpecChecker):
                event.remove_task(task)

    def passthrough(self, result_callback=None):
        """Make the last recorded event run on the real object once seen.

        @param result_callback: If given, this function will be called with
            the result of the *real* method call as the only argument.

        This can only be used on proxies, as returned by the L{proxy()}
        and L{replace()} methods, or on mocks representing patched objects,
        as returned by the L{patch()} method.
        """
        event = self._events[-1]
        if event.path.root_object is None:
            raise TypeError("Mock object isn't a proxy")
        event.add_task(PathExecuter(result_callback))

    def __enter__(self):
        """Enter in a 'with' context.  This will run replay()."""
        self.replay()
        return self

    def __exit__(self, type, value, traceback):
        """Exit from a 'with' context.

        This will run restore() at all times, but will only run verify()
        if the 'with' block itself hasn't raised an exception.  Exceptions
        in that block are never swallowed.
        """
        self.restore()
        if type is None:
            self.verify()
        return False

    def _get_replay_restore_event(self):
        """Return unique L{ReplayRestoreEvent}, creating if needed.

        Some tasks only want to replay/restore.  When that's the case,
        they shouldn't act on other events during replay.  Also, they
        can all be put in a single event when that's the case.  Thus,
        we add a single L{ReplayRestoreEvent} as the first element of
        the list.
        """
        if not self._events or type(self._events[0]) != ReplayRestoreEvent:
            self._events.insert(0, ReplayRestoreEvent())
        return self._events[0]


class OrderedContext(object):

    def __init__(self, mocker):
        self._mocker = mocker

    def __enter__(self):
        return None

    def __exit__(self, type, value, traceback):
        self._mocker.unorder()


class Mocker(MockerBase):
    __doc__ = MockerBase.__doc__

# Decorator to add recorders on the standard Mocker class.
recorder = Mocker.add_recorder


# --------------------------------------------------------------------
# Mock object.

class Mock(object):

    def __init__(self, mocker, path=None, name=None, spec=None, type=None,
                 object=None, passthrough=False, patcher=None, count=True):
        self.__mocker__ = mocker
        self.__mocker_path__ = path or Path(self, object)
        self.__mocker_name__ = name
        self.__mocker_spec__ = spec
        self.__mocker_object__ = object
        self.__mocker_passthrough__ = passthrough
        self.__mocker_patcher__ = patcher
        self.__mocker_replace__ = False
        self.__mocker_type__ = type
        self.__mocker_count__ = count

    def __mocker_act__(self, kind, args=(), kwargs={}, object=None):
        if self.__mocker_name__ is None:
            self.__mocker_name__ = find_object_name(self, 2)
        action = Action(kind, args, kwargs, self.__mocker_path__)
        path = self.__mocker_path__ + action
        if object is not None:
            path.root_object = object
        try:
            return self.__mocker__.act(path)
        except MatchError, exception:
            root_mock = path.root_mock
            if (path.root_object is not None and
                root_mock.__mocker_passthrough__):
                return path.execute(path.root_object)
            # Reinstantiate to show raise statement on traceback, and
            # also to make the traceback shown shorter.
            raise MatchError(str(exception))
        except AssertionError, e:
            lines = str(e).splitlines()
            message = [ERROR_PREFIX + "Unmet expectation:", ""]
            message.append("=> " + lines.pop(0))
            message.extend([" " + line for line in lines])
            message.append("")
            raise AssertionError(os.linesep.join(message))

    def __getattribute__(self, name):
        if name.startswith("__mocker_"):
            return super(Mock, self).__getattribute__(name)
        if name == "__class__":
            if self.__mocker__.is_recording() or self.__mocker_type__ is None:
                return type(self)
            return self.__mocker_type__
        if name == "__length_hint__":
            # This is used by Python 2.6+ to optimize the allocation
            # of arrays in certain cases.  Pretend it doesn't exist.
            raise AttributeError("No __length_hint__ here!")
        return self.__mocker_act__("getattr", (name,))

    def __setattr__(self, name, value):
        if name.startswith("__mocker_"):
            return super(Mock, self).__setattr__(name, value)
        return self.__mocker_act__("setattr", (name, value))

    def __delattr__(self, name):
        return self.__mocker_act__("delattr", (name,))

    def __call__(self, *args, **kwargs):
        return self.__mocker_act__("call", args, kwargs)

    def __contains__(self, value):
        return self.__mocker_act__("contains", (value,))

    def __getitem__(self, key):
        return self.__mocker_act__("getitem", (key,))

    def __setitem__(self, key, value):
        return self.__mocker_act__("setitem", (key, value))

    def __delitem__(self, key):
        return self.__mocker_act__("delitem", (key,))

    def __len__(self):
        # MatchError is turned on an AttributeError so that list() and
        # friends act properly when trying to get length hints on
        # something that doesn't offer them.
        try:
            result = self.__mocker_act__("len")
        except MatchError, e:
            raise AttributeError(str(e))
        if type(result) is Mock:
            return 0
        return result

    def __nonzero__(self):
        try:
            result = self.__mocker_act__("nonzero")
        except MatchError, e:
            return True
        if type(result) is Mock:
            return True
        return result

    def __iter__(self):
        # XXX On py3k, when next() becomes __next__(), we'll be able
        #     to return the mock itself because it will be considered
        #     an iterator (we'll be mocking __next__ as well, which we
        #     can't now).
        result = self.__mocker_act__("iter")
        if type(result) is Mock:
            return iter([])
        return result

    # When adding a new action kind here, also add support for it on
    # Action.execute() and Path.__str__().


def find_object_name(obj, depth=0):
    """Try to detect how the object is named on a previous scope."""
    try:
        frame = sys._getframe(depth+1)
    except:
        return None
    for name, frame_obj in frame.f_locals.iteritems():
        if frame_obj is obj:
            return name
    self = frame.f_locals.get("self")
    if self is not None:
        try:
            items = list(self.__dict__.iteritems())
        except:
            pass
        else:
            for name, self_obj in items:
                if self_obj is obj:
                    return name
    return None


# --------------------------------------------------------------------
# Action and path.

class Action(object):

    def __init__(self, kind, args, kwargs, path=None):
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.path = path
        self._execute_cache = {}

    def __repr__(self):
        if self.path is None:
            return "Action(%r, %r, %r)" % (self.kind, self.args, self.kwargs)
        return "Action(%r, %r, %r, %r)" % \
               (self.kind, self.args, self.kwargs, self.path)

    def __eq__(self, other):
        return (self.kind == other.kind and
                self.args == other.args and
                self.kwargs == other.kwargs)

    def __ne__(self, other):
        return not self.__eq__(other)

    def matches(self, other):
        return (self.kind == other.kind and
                match_params(self.args, self.kwargs, other.args, other.kwargs))

    def execute(self, object):
        # This caching scheme may fail if the object gets deallocated before
        # the action, as the id might get reused.  It's somewhat easy to fix
        # that with a weakref callback.  For our uses, though, the object
        # should never get deallocated before the action itself, so we'll
        # just keep it simple.
        if id(object) in self._execute_cache:
            return self._execute_cache[id(object)]
        execute = getattr(object, "__mocker_execute__", None)
        if execute is not None:
            result = execute(self, object)
        else:
            kind = self.kind
            if kind == "getattr":
                result = getattr(object, self.args[0])
            elif kind == "setattr":
                result = setattr(object, self.args[0], self.args[1])
            elif kind == "delattr":
                result = delattr(object, self.args[0])
            elif kind == "call":
                result = object(*self.args, **self.kwargs)
            elif kind == "contains":
                result = self.args[0] in object
            elif kind == "getitem":
                result = object[self.args[0]]
            elif kind == "setitem":
                result = object[self.args[0]] = self.args[1]
            elif kind == "delitem":
                del object[self.args[0]]
                result = None
            elif kind == "len":
                result = len(object)
            elif kind == "nonzero":
                result = bool(object)
            elif kind == "iter":
                result = iter(object)
            else:
                raise RuntimeError("Don't know how to execute %r kind." % kind)
        self._execute_cache[id(object)] = result
        return result


class Path(object):

    def __init__(self, root_mock, root_object=None, actions=()):
        self.root_mock = root_mock
        self.root_object = root_object
        self.actions = tuple(actions)
        self.__mocker_replace__ = False

    def parent_path(self):
        if not self.actions:
            return None
        return self.actions[-1].path
    parent_path = property(parent_path)
 
    def __add__(self, action):
        """Return a new path which includes the given action at the end."""
        return self.__class__(self.root_mock, self.root_object,
                              self.actions + (action,))

    def __eq__(self, other):
        """Verify if the two paths are equal.
        
        Two paths are equal if they refer to the same mock object, and
        have the actions with equal kind, args and kwargs.
        """
        if (self.root_mock is not other.root_mock or
            self.root_object is not other.root_object or
            len(self.actions) != len(other.actions)):
            return False
        for action, other_action in zip(self.actions, other.actions):
            if action != other_action:
                return False
        return True

    def matches(self, other):
        """Verify if the two paths are equivalent.
        
        Two paths are equal if they refer to the same mock object, and
        have the same actions performed on them.
        """
        if (self.root_mock is not other.root_mock or
            len(self.actions) != len(other.actions)):
            return False
        for action, other_action in zip(self.actions, other.actions):
            if not action.matches(other_action):
                return False
        return True

    def execute(self, object):
        """Execute all actions sequentially on object, and return result.
        """
        for action in self.actions:
            object = action.execute(object)
        return object

    def __str__(self):
        """Transform the path into a nice string such as obj.x.y('z')."""
        result = self.root_mock.__mocker_name__ or "<mock>"
        for action in self.actions:
            if action.kind == "getattr":
                result = "%s.%s" % (result, action.args[0])
            elif action.kind == "setattr":
                result = "%s.%s = %r" % (result, action.args[0], action.args[1])
            elif action.kind == "delattr":
                result = "del %s.%s" % (result, action.args[0])
            elif action.kind == "call":
                args = [repr(x) for x in action.args]
                items = list(action.kwargs.iteritems())
                items.sort()
                for pair in items:
                    args.append("%s=%r" % pair)
                result = "%s(%s)" % (result, ", ".join(args))
            elif action.kind == "contains":
                result = "%r in %s" % (action.args[0], result)
            elif action.kind == "getitem":
                result = "%s[%r]" % (result, action.args[0])
            elif action.kind == "setitem":
                result = "%s[%r] = %r" % (result, action.args[0],
                                          action.args[1])
            elif action.kind == "delitem":
                result = "del %s[%r]" % (result, action.args[0])
            elif action.kind == "len":
                result = "len(%s)" % result
            elif action.kind == "nonzero":
                result = "bool(%s)" % result
            elif action.kind == "iter":
                result = "iter(%s)" % result
            else:
                raise RuntimeError("Don't know how to format kind %r" %
                                   action.kind)
        return result


class SpecialArgument(object):
    """Base for special arguments for matching parameters."""

    def __init__(self, object=None):
        self.object = object

    def __repr__(self):
        if self.object is None:
            return self.__class__.__name__
        else:
            return "%s(%r)" % (self.__class__.__name__, self.object)

    def matches(self, other):
        return True

    def __eq__(self, other):
        return type(other) == type(self) and self.object == other.object


class ANY(SpecialArgument):
    """Matches any single argument."""

ANY = ANY()


class ARGS(SpecialArgument):
    """Matches zero or more positional arguments."""

ARGS = ARGS()


class KWARGS(SpecialArgument):
    """Matches zero or more keyword arguments."""

KWARGS = KWARGS()


class IS(SpecialArgument):

    def matches(self, other):
        return self.object is other

    def __eq__(self, other):
        return type(other) == type(self) and self.object is other.object


class CONTAINS(SpecialArgument):

    def matches(self, other):
        try:
            other.__contains__
        except AttributeError:
            try:
                iter(other)
            except TypeError:
                # If an object can't be iterated, and has no __contains__
                # hook, it'd blow up on the test below.  We test this in
                # advance to prevent catching more errors than we really
                # want.
                return False
        return self.object in other


class IN(SpecialArgument):

    def matches(self, other):
        return other in self.object


class MATCH(SpecialArgument):

    def matches(self, other):
        return bool(self.object(other))

    def __eq__(self, other):
        return type(other) == type(self) and self.object is other.object


def match_params(args1, kwargs1, args2, kwargs2):
    """Match the two sets of parameters, considering special parameters."""

    has_args = ARGS in args1
    has_kwargs = KWARGS in args1

    if has_kwargs:
        args1 = [arg1 for arg1 in args1 if arg1 is not KWARGS]
    elif len(kwargs1) != len(kwargs2):
        return False

    if not has_args and len(args1) != len(args2):
        return False

    # Either we have the same number of kwargs, or unknown keywords are
    # accepted (KWARGS was used), so check just the ones in kwargs1.
    for key, arg1 in kwargs1.iteritems():
        if key not in kwargs2:
            return False
        arg2 = kwargs2[key]
        if isinstance(arg1, SpecialArgument):
            if not arg1.matches(arg2):
                return False
        elif arg1 != arg2:
            return False

    # Keywords match.  Now either we have the same number of
    # arguments, or ARGS was used.  If ARGS wasn't used, arguments
    # must match one-on-one necessarily.
    if not has_args:
        for arg1, arg2 in zip(args1, args2):
            if isinstance(arg1, SpecialArgument):
                if not arg1.matches(arg2):
                    return False
            elif arg1 != arg2:
                return False
        return True

    # Easy choice. Keywords are matching, and anything on args is accepted.
    if (ARGS,) == args1:
        return True

    # We have something different there. If we don't have positional
    # arguments on the original call, it can't match.
    if not args2:
        # Unless we have just several ARGS (which is bizarre, but..).
        for arg1 in args1:
            if arg1 is not ARGS:
                return False
        return True

    # Ok, all bets are lost.  We have to actually do the more expensive
    # matching.  This is an algorithm based on the idea of the Levenshtein
    # Distance between two strings, but heavily hacked for this purpose.
    args2l = len(args2)
    if args1[0] is ARGS:
        args1 = args1[1:]
        array = [0]*args2l
    else:
        array = [1]*args2l
    for i in range(len(args1)):
        last = array[0]
        if args1[i] is ARGS:
            for j in range(1, args2l):
                last, array[j] = array[j], min(array[j-1], array[j], last)
        else:
            array[0] = i or int(args1[i] != args2[0])
            for j in range(1, args2l):
                last, array[j] = array[j], last or int(args1[i] != args2[j])
        if 0 not in array:
            return False
    if array[-1] != 0:
        return False
    return True


# --------------------------------------------------------------------
# Event and task base.

class Event(object):
    """Aggregation of tasks that keep track of a recorded action.

    An event represents something that may or may not happen while the
    mocked environment is running, such as an attribute access, or a
    method call.  The event is composed of several tasks that are
    orchestrated together to create a composed meaning for the event,
    including for which actions it should be run, what happens when it
    runs, and what's the expectations about the actions run.
    """

    def __init__(self, path=None):
        self.path = path
        self._tasks = []
        self._has_run = False

    def add_task(self, task):
        """Add a new task to this task."""
        self._tasks.append(task)
        return task

    def prepend_task(self, task):
        """Add a task at the front of the list."""
        self._tasks.insert(0, task)
        return task

    def remove_task(self, task):
        self._tasks.remove(task)

    def replace_task(self, old_task, new_task):
        """Replace old_task with new_task, in the same position."""
        for i in range(len(self._tasks)):
            if self._tasks[i] is old_task:
                self._tasks[i] = new_task
        return new_task

    def get_tasks(self):
        return self._tasks[:]

    def matches(self, path):
        """Return true if *all* tasks match the given path."""
        for task in self._tasks:
            if not task.matches(path):
                return False
        return bool(self._tasks)

    def has_run(self):
        return self._has_run

    def may_run(self, path):
        """Verify if any task would certainly raise an error if run.

        This will call the C{may_run()} method on each task and return
        false if any of them returns false.
        """
        for task in self._tasks:
            if not task.may_run(path):
                return False
        return True

    def run(self, path):
        """Run all tasks with the given action.

        @param path: The path of the expression run.

        Running an event means running all of its tasks individually and in
        order.  An event should only ever be run if all of its tasks claim to
        match the given action.

        The result of this method will be the last result of a task
        which isn't None, or None if they're all None.
        """
        self._has_run = True
        result = None
        errors = []
        for task in self._tasks:
            if not errors or not task.may_run_user_code():
                try:
                    task_result = task.run(path)
                except AssertionError, e:
                    error = str(e)
                    if not error:
                        raise RuntimeError("Empty error message from %r" % task)
                    errors.append(error)
                else:
                    # XXX That's actually a bit weird.  What if a call() really
                    # returned None?  This would improperly change the semantic
                    # of this process without any good reason. Test that with two
                    # call()s in sequence.
                    if task_result is not None:
                        result = task_result
        if errors:
            message = [str(self.path)]
            if str(path) != message[0]:
                message.append("- Run: %s" % path)
            for error in errors:
                lines = error.splitlines()
                message.append("- " + lines.pop(0))
                message.extend(["  " + line for line in lines])
            raise AssertionError(os.linesep.join(message))
        return result

    def satisfied(self):
        """Return true if all tasks are satisfied.

        Being satisfied means that there are no unmet expectations.
        """
        for task in self._tasks:
            try:
                task.verify()
            except AssertionError:
                return False
        return True

    def verify(self):
        """Run verify on all tasks.

        The verify method is supposed to raise an AssertionError if the
        task has unmet expectations, with a one-line explanation about
        why this item is unmet.  This method should be safe to be called
        multiple times without side effects.
        """
        errors = []
        for task in self._tasks:
            try:
                task.verify()
            except AssertionError, e:
                error = str(e)
                if not error:
                    raise RuntimeError("Empty error message from %r" % task)
                errors.append(error)
        if errors:
            message = [str(self.path)]
            for error in errors:
                lines = error.splitlines()
                message.append("- " + lines.pop(0))
                message.extend(["  " + line for line in lines])
            raise AssertionError(os.linesep.join(message))

    def replay(self):
        """Put all tasks in replay mode."""
        self._has_run = False
        for task in self._tasks:
            task.replay()

    def restore(self):
        """Restore the state of all tasks."""
        for task in self._tasks:
            task.restore()


class ReplayRestoreEvent(Event):
    """Helper event for tasks which need replay/restore but shouldn't match."""

    def matches(self, path):
        return False


class Task(object):
    """Element used to track one specific aspect on an event.

    A task is responsible for adding any kind of logic to an event.
    Examples of that are counting the number of times the event was
    made, verifying parameters if any, and so on.
    """

    def matches(self, path):
        """Return true if the task is supposed to be run for the given path.
        """
        return True

    def may_run(self, path):
        """Return false if running this task would certainly raise an error."""
        return True

    def may_run_user_code(self):
        """Return true if there's a chance this task may run custom code.

        Whenever errors are detected, running user code should be avoided,
        because the situation is already known to be incorrect, and any
        errors in the user code are side effects rather than the cause.
        """
        return False

    def run(self, path):
        """Perform the task item, considering that the given action happened.
        """

    def verify(self):
        """Raise AssertionError if expectations for this item are unmet.

        The verify method is supposed to raise an AssertionError if the
        task has unmet expectations, with a one-line explanation about
        why this item is unmet.  This method should be safe to be called
        multiple times without side effects.
        """

    def replay(self):
        """Put the task in replay mode.

        Any expectations of the task should be reset.
        """

    def restore(self):
        """Restore any environmental changes made by the task.

        Verify should continue to work after this is called.
        """


# --------------------------------------------------------------------
# Task implementations.

class OnRestoreCaller(Task):
    """Call a given callback when restoring."""

    def __init__(self, callback):
        self._callback = callback

    def restore(self):
        self._callback()


class PathMatcher(Task):
    """Match the action path against a given path."""

    def __init__(self, path):
        self.path = path

    def matches(self, path):
        return self.path.matches(path)

def path_matcher_recorder(mocker, event):
    event.add_task(PathMatcher(event.path))

Mocker.add_recorder(path_matcher_recorder)


class RunCounter(Task):
    """Task which verifies if the number of runs are within given boundaries.
    """

    def __init__(self, min, max=False):
        self.min = min
        if max is None:
            self.max = sys.maxint
        elif max is False:
            self.max = min
        else:
            self.max = max
        self._runs = 0

    def replay(self):
        self._runs = 0

    def may_run(self, path):
        return self._runs < self.max

    def run(self, path):
        self._runs += 1
        if self._runs > self.max:
            self.verify()

    def verify(self):
        if not self.min <= self._runs <= self.max:
            if self._runs < self.min:
                raise AssertionError("Performed fewer times than expected.")
            raise AssertionError("Performed more times than expected.")


class ImplicitRunCounter(RunCounter):
    """RunCounter inserted by default on any event.

    This is a way to differentiate explicitly added counters and
    implicit ones.
    """

def run_counter_recorder(mocker, event):
    """Any event may be repeated once, unless disabled by default."""
    if event.path.root_mock.__mocker_count__:
        # Rather than appending the task, we prepend it so that the
        # issue is raised before any other side-effects happen.
        event.prepend_task(ImplicitRunCounter(1))

Mocker.add_recorder(run_counter_recorder)

def run_counter_removal_recorder(mocker, event):
    """
    Events created by getattr actions which lead to other events
    may be repeated any number of times. For that, we remove implicit
    run counters of any getattr actions leading to the current one.
    """
    parent_path = event.path.parent_path
    for event in mocker.get_events()[::-1]:
        if (event.path is parent_path and
            event.path.actions[-1].kind == "getattr"):
            for task in event.get_tasks():
                if type(task) is ImplicitRunCounter:
                    event.remove_task(task)

Mocker.add_recorder(run_counter_removal_recorder)


class MockReturner(Task):
    """Return a mock based on the action path."""

    def __init__(self, mocker):
        self.mocker = mocker

    def run(self, path):
        return Mock(self.mocker, path)

def mock_returner_recorder(mocker, event):
    """Events that lead to other events must return mock objects."""
    parent_path = event.path.parent_path
    for event in mocker.get_events():
        if event.path is parent_path:
            for task in event.get_tasks():
                if isinstance(task, MockReturner):
                    break
            else:
                event.add_task(MockReturner(mocker))
            break

Mocker.add_recorder(mock_returner_recorder)


class FunctionRunner(Task):
    """Task that runs a function everything it's run.

    Arguments of the last action in the path are passed to the function,
    and the function result is also returned.
    """

    def __init__(self, func, with_root_object=False):
        self._func = func
        self._with_root_object = with_root_object

    def may_run_user_code(self):
        return True

    def run(self, path):
        action = path.actions[-1]
        if self._with_root_object:
            return self._func(path.root_object, *action.args, **action.kwargs)
        else:
            return self._func(*action.args, **action.kwargs)


class PathExecuter(Task):
    """Task that executes a path in the real object, and returns the result."""

    def __init__(self, result_callback=None):
        self._result_callback = result_callback

    def get_result_callback(self):
        return self._result_callback

    def run(self, path):
        result = path.execute(path.root_object)
        if self._result_callback is not None:
            self._result_callback(result)
        return result


class Orderer(Task):
    """Task to establish an order relation between two events.

    An orderer task will only match once all its dependencies have
    been run.
    """

    def __init__(self, path):
        self.path = path
        self._run = False 
        self._dependencies = []

    def replay(self):
        self._run = False

    def has_run(self):
        return self._run

    def may_run(self, path):
        for dependency in self._dependencies:
            if not dependency.has_run():
                return False
        return True

    def run(self, path):
        for dependency in self._dependencies:
            if not dependency.has_run():
                raise AssertionError("Should be after: %s" % dependency.path)
        self._run = True

    def add_dependency(self, orderer):
        self._dependencies.append(orderer)

    def get_dependencies(self):
        return self._dependencies


class SpecChecker(Task):
    """Task to check if arguments of the last action conform to a real method.
    """

    def __init__(self, method):
        self._method = method
        self._unsupported = False

        if method:
            try:
                self._args, self._varargs, self._varkwargs, self._defaults = \
                    inspect.getargspec(method)
            except TypeError:
                self._unsupported = True
            else:
                if self._defaults is None:
                    self._defaults = ()
                if type(method) is type(self.run):
                    self._args = self._args[1:]

    def get_method(self):
        return self._method

    def _raise(self, message):
        spec = inspect.formatargspec(self._args, self._varargs,
                                     self._varkwargs, self._defaults)
        raise AssertionError("Specification is %s%s: %s" %
                             (self._method.__name__, spec, message))

    def verify(self):
        if not self._method:
            raise AssertionError("Method not found in real specification")

    def may_run(self, path):
        try:
            self.run(path)
        except AssertionError:
            return False
        return True

    def run(self, path):
        if not self._method:
            raise AssertionError("Method not found in real specification")
        if self._unsupported:
            return # Can't check it. Happens with builtin functions. :-(
        action = path.actions[-1]
        obtained_len = len(action.args)
        obtained_kwargs = action.kwargs.copy()
        nodefaults_len = len(self._args) - len(self._defaults)
        for i, name in enumerate(self._args):
            if i < obtained_len and name in action.kwargs:
                self._raise("%r provided twice" % name)
            if (i >= obtained_len and i < nodefaults_len and
                name not in action.kwargs):
                self._raise("%r not provided" % name)
            obtained_kwargs.pop(name, None)
        if obtained_len > len(self._args) and not self._varargs:
            self._raise("too many args provided")
        if obtained_kwargs and not self._varkwargs:
            self._raise("unknown kwargs: %s" % ", ".join(obtained_kwargs))

def spec_checker_recorder(mocker, event):
    spec = event.path.root_mock.__mocker_spec__
    if spec:
        actions = event.path.actions
        if len(actions) == 1:
            if actions[0].kind == "call":
                method = getattr(spec, "__call__", None)
                event.add_task(SpecChecker(method))
        elif len(actions) == 2:
            if actions[0].kind == "getattr" and actions[1].kind == "call":
                method = getattr(spec, actions[0].args[0], None)
                event.add_task(SpecChecker(method))

Mocker.add_recorder(spec_checker_recorder)


class ProxyReplacer(Task):
    """Task which installs and deinstalls proxy mocks.

    This task will replace a real object by a mock in all dictionaries
    found in the running interpreter via the garbage collecting system.
    """

    def __init__(self, mock):
        self.mock = mock
        self.__mocker_replace__ = False

    def replay(self):
        global_replace(self.mock.__mocker_object__, self.mock)

    def restore(self):
        global_replace(self.mock, self.mock.__mocker_object__)


def global_replace(remove, install):
    """Replace object 'remove' with object 'install' on all dictionaries."""
    for referrer in gc.get_referrers(remove):
        if (type(referrer) is dict and
            referrer.get("__mocker_replace__", True)):
            for key, value in list(referrer.iteritems()):
                if value is remove:
                    referrer[key] = install


class Undefined(object):

    def __repr__(self):
        return "Undefined"

Undefined = Undefined()


class Patcher(Task):

    def __init__(self):
        super(Patcher, self).__init__()
        self._monitored = {} # {kind: {id(object): object}}
        self._patched = {}

    def is_monitoring(self, obj, kind):
        monitored = self._monitored.get(kind)
        if monitored:
            if id(obj) in monitored:
                return True
            cls = type(obj)
            if issubclass(cls, type):
                cls = obj
            bases = set([id(base) for base in cls.__mro__])
            bases.intersection_update(monitored)
            return bool(bases)
        return False

    def monitor(self, obj, kind):
        if kind not in self._monitored:
            self._monitored[kind] = {}
        self._monitored[kind][id(obj)] = obj

    def patch_attr(self, obj, attr, value):
        original = obj.__dict__.get(attr, Undefined)
        self._patched[id(obj), attr] = obj, attr, original
        setattr(obj, attr, value)

    def get_unpatched_attr(self, obj, attr):
        cls = type(obj)
        if issubclass(cls, type):
            cls = obj
        result = Undefined
        for mro_cls in cls.__mro__:
            key = (id(mro_cls), attr)
            if key in self._patched:
                result = self._patched[key][2]
                if result is not Undefined:
                    break
            elif attr in mro_cls.__dict__:
                result = mro_cls.__dict__.get(attr, Undefined)
                break
        if isinstance(result, object) and hasattr(type(result), "__get__"):
            if cls is obj:
                obj = None
            return result.__get__(obj, cls)
        return result

    def _get_kind_attr(self, kind):
        if kind == "getattr":
            return "__getattribute__"
        return "__%s__" % kind

    def replay(self):
        for kind in self._monitored:
            attr = self._get_kind_attr(kind)
            seen = set()
            for obj in self._monitored[kind].itervalues():
                cls = type(obj)
                if issubclass(cls, type):
                    cls = obj
                if cls not in seen:
                    seen.add(cls)
                    unpatched = getattr(cls, attr, Undefined)
                    self.patch_attr(cls, attr,
                                    PatchedMethod(kind, unpatched,
                                                  self.is_monitoring))
                    self.patch_attr(cls, "__mocker_execute__",
                                    self.execute)

    def restore(self):
        for obj, attr, original in self._patched.itervalues():
            if original is Undefined:
                delattr(obj, attr)
            else:
                setattr(obj, attr, original)
        self._patched.clear()

    def execute(self, action, object):
        attr = self._get_kind_attr(action.kind)
        unpatched = self.get_unpatched_attr(object, attr)
        try:
            return unpatched(*action.args, **action.kwargs)
        except AttributeError:
            type, value, traceback = sys.exc_info()
            if action.kind == "getattr":
                # The normal behavior of Python is to try __getattribute__,
                # and if it raises AttributeError, try __getattr__.   We've
                # tried the unpatched __getattribute__ above, and we'll now
                # try __getattr__.
                try:
                    __getattr__ = unpatched("__getattr__")
                except AttributeError:
                    pass
                else:
                    return __getattr__(*action.args, **action.kwargs)
            raise type, value, traceback


class PatchedMethod(object):

    def __init__(self, kind, unpatched, is_monitoring):
        self._kind = kind
        self._unpatched = unpatched
        self._is_monitoring = is_monitoring

    def __get__(self, obj, cls=None):
        object = obj or cls
        if not self._is_monitoring(object, self._kind):
            return self._unpatched.__get__(obj, cls)
        def method(*args, **kwargs):
            if self._kind == "getattr" and args[0].startswith("__mocker_"):
                return self._unpatched.__get__(obj, cls)(args[0])
            mock = object.__mocker_mock__
            return mock.__mocker_act__(self._kind, args, kwargs, object)
        return method

    def __call__(self, obj, *args, **kwargs):
        # At least with __getattribute__, Python seems to use *both* the
        # descriptor API and also call the class attribute directly.  It
        # looks like an interpreter bug, or at least an undocumented
        # inconsistency.  Coverage tests may show this uncovered, because
        # it depends on the Python version.
        return self.__get__(obj)(*args, **kwargs)


def patcher_recorder(mocker, event):
    mock = event.path.root_mock
    if mock.__mocker_patcher__ and len(event.path.actions) == 1:
        patcher = mock.__mocker_patcher__
        patcher.monitor(mock.__mocker_object__, event.path.actions[0].kind)

Mocker.add_recorder(patcher_recorder)

########NEW FILE########
__FILENAME__ = test_builder
import sys
import os
from nose import *

from bricklayer.projects import Projects
from bricklayer.builder import Builder
from bricklayer.build_info import BuildInfo


def setup():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

class TestBuilder:
    def build_init_test(self):
        print os.path.abspath(os.path.curdir)
        p = Projects('test_build')
        p.git_url = 'test/test_repo'
        p.group = 'test_group'
        p.version = '0.100.0'
        p.save()

        b = Builder(p.name)
        pre_build_id = BuildInfo(p)
        b.build_project(branch='master', release='testing', version='0.0.1', commit=None)
        
        assert( BuildInfo(p).build_id != pre_build_id)

########NEW FILE########
__FILENAME__ = test_config
from bricklayer.config import BrickConfig


class TestConfig:
	pass
########NEW FILE########
__FILENAME__ = test_git
import os
import sys
import shutil
import mocker

sys.path.append('..')
sys.path.append('../utils')

from nose.tools import *
from bricklayer.git import Git

def teardown():
    if os.path.isdir('tests/workspace'):
        shutil.rmtree('tests/workspace', ignore_errors=True)

    
class TestGit:
    def __init__(self):
        self.project = mocker.Mocker()
        self.project.name = 'test_repo'
        self.project.git_url = 'tests/test_repo'
        self.project.version = '1.0'
        self.project.branch = 'master'
        self.project.last_tag = ''
        self.project.last_commit = ''
        self.project.build_cmd = 'python setup.py build'
        self.project.install_cmd = 'python setup.py install --root=BUILDROOT'
        self.project.replay()
        self.git = Git(self.project, workdir=os.path.join(os.path.dirname(__file__), 'workspace'))

        if not os.path.isdir(self.git.workdir):
            self.git.clone(self.project.branch)

    def clone_test(self):
        assert os.path.isdir(self.git.workdir)
        assert os.path.isdir(os.path.join(self.git.workdir, '.git'))

    def checkout_tag_test(self):
        self.git.checkout_tag('testing_0.0.1')
        assert_true(os.path.isfile(os.path.join(self.git.workdir, 'a')))
        assert_false(os.path.isfile(os.path.join(self.git.workdir, 'c')))
        self.git.checkout_tag('testing_0.0.2')
        assert_true(os.path.isfile(os.path.join(self.git.workdir, 'c')))
    
    def last_tag_test(self):
        assert_equal(self.git.last_tag('testing'), 'testing_0.0.2')

########NEW FILE########
__FILENAME__ = test_main
import sys
from nose import *

sys.path.append('../bricklayer')

class main_test():
    def main_test(self):
        pass

########NEW FILE########
__FILENAME__ = test_projects
import sys
import os
import ConfigParser
from nose.tools import *

sys.path.append('../bricklayer')
sys.path.append('../bricklayer/utils')

from bricklayer.projects import Projects
from bricklayer.config import BrickConfig

class TestProjects:
    def create_test(self):
        p = Projects('test')
        p.git_url = 'test/test_repo'
        p.group = 'test_group'
        p.save()

        p = Projects('test')
        assert p.name == 'test'
        assert p.git_url == 'test/test_repo'

    def exist_test(self):
        p = Projects('test')
        assert p.name == 'test'

    def delete_test(self):
        p = Projects('test')
        p.delete()
        assert Projects('test').git_url == ''

    def add_branch_test(self):
        p = Projects('test')
        p.add_branch('test_branch')
        assert 'test_branch' in p.branches()
########NEW FILE########
__FILENAME__ = txbricklayer
from zope.interface import implements
from twisted.python import usage
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
import bricklayer

class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    options = usage.Options
    tapname = "bricklayer"
    description = "Bricklayer service."
    
    def makeService(self, config):
        print bricklayer.__file__
        return bricklayer.service.BricklayerService()

serviceMaker = MyServiceMaker()

########NEW FILE########
__FILENAME__ = txbricklayer_web
from zope.interface import implements
from twisted.python import usage
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
import bricklayer.rest

class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    options = usage.Options
    tapname = "bricklayer_web"
    description = "Bricklayer WebService."
    
    def makeService(self, config):
        print bricklayer.__file__
        return bricklayer.rest.server

serviceMaker = MyServiceMaker()

########NEW FILE########
