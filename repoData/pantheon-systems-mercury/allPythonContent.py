__FILENAME__ = archive_file
import os
import sys

from optparse import OptionParser
from pantheon import backup
from pantheon import logger

# Set up logging.
log = logger.logging.getLogger("archiver")

def main():
    usage = "usage: %prog [options] PATH"
    parser = OptionParser(usage=usage, 
                          description="Archive a file to remote storage.")
    parser.add_option('-t', '--threshold', type="int", dest="threshold", default=4194304000, help='Filesize at which we switch to multipart upload.')
    parser.add_option('-c', '--chunksize', type="int", dest="chunksize", default=4194304000, help='The size to break multipart uploads into.')
    (options, args) = parser.parse_args()
    for arg in args:
        if os.path.isfile(arg):
            path = arg
            filename = os.path.basename(path)
            log.info('Moving archive to external storage.')
            try:
                backup.Archive(path, options.threshold, options.chunksize).submit()
            except:
                log.exception('Upload to remote storage unsuccessful.')
                raise
            else:
                log.info('Upload of %s to remote storage complete.' % 
                              filename)
        else:
            sys.exit('First arguement not a file path.')


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = argus
from fabric.api import *
from pantheon import ygg
import sys

configuration = ygg.get_config()
STORAGE = '/var/lib/jenkins/jobs/argus/workspace'
WEBKIT2PNG = '/opt/pantheon/fab/webkit2png.py'
LOG = '{0}/webkit2png.log'.format(STORAGE)

def main(project,env):
    if not project:
        for p in configuration:
            with settings(warn_only=True):
                local('mkdir -p {0}/{1}'.format(STORAGE, p))
            for e in configuration[p]['environments']:
                _screenshot(p,e)
    elif project and not env:
        with settings(warn_only=True):
            local('mkdir -p {0}/{1}'.format(STORAGE, project))
        for e in configuration[project]['environments']:
            _screenshot(project,e)
    elif project and env:
        with settings(warn_only=True):
            local('mkdir -p {0}/{1}'.format(STORAGE, project))
        _screenshot(project,env)

def _screenshot(p, e):
        alias = configuration[p]['environments'][e]['apache']['ServerAlias']
        url = 'http://{0}'.format(alias)
        fname = '{0}_{1}.png'.format(p, e)
        fpath = '{0}/{1}/{2}'.format(STORAGE, p, fname)
        local('xvfb-run --server-args="-screen 0, 640x480x24" python {0} --log="{1}" {2} > {3}'.format(WEBKIT2PNG, LOG, url, fpath))

if __name__ == '__main__':
    project = sys.argv[1] if len(sys.argv) >= 2 else None
    env = sys.argv[2] if len(sys.argv) == 3 else None
    main(project, env)

########NEW FILE########
__FILENAME__ = atlas_postback
import os

from pantheon import postback
from optparse import OptionParser

def main():
    print "DEBUG: atlas_postback.main"
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, description="Send information about a Jenkins job (and resulting data) back to Atlas.")
    parser.add_option('-c', '--check_changed_status', dest="check_changed_status", action="store_true", default=False, help='Postback only if the status of the build has changed from the previous run.')
    (options, args) = parser.parse_args()
    postback_atlas(options.check_changed_status)

def postback_atlas(check_changed_status=False):
    """ Send information about a Jenkins job (and resulting data) back to Atlas.
    check_changed_status: bool. If we want to only return data if the status of
                                the build has changed from the previous run.

    This should only be called from within a Jenkins Post-Build Action.

    """
    print "DEBUG: atlas_postback.postback_atlas"
    # Get job_name and build_number.
    job_name, build_number = postback.get_job_and_id()

    # Get build info: job_name, build_number, build_status, build_parameters.
    response = postback.get_build_info(job_name,
                                       build_number,
                                       check_changed_status)

    # If there is data we want to send back.
    if response:
        # Get build data from build actions (in jenkins workspace).
        response.update({'build_data': postback.get_build_data()})

        # Send response to Atlas.
        postback.postback(response)
    else:
        print('Build status has not changed. No postback performed.')


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = buildtools
import os

from fabric.api import local

from pantheon import pantheon
from pantheon import postback
from pantheon import jenkinstools

def clean_workspace():
    """Cleanup data files from build workspace.

    This should be run before any other processing is done.

    """
    workspace = jenkinstools.get_workspace()
    if os.path.exists(workspace):
        local('rm -f %s' % os.path.join(workspace, '*'))

def parse_build_data():
    """Output build messages/warnings/errors to stdout.

    """
    messages, warnings, errors = _get_build_messages()

    # Output messages to console to ease debugging.
    if messages:
        messages = '\n'.join(messages)
        print('\nBuild Messages: \n' + '=' * 30)
        print(messages)
    if warnings:
        warnings = '\n'.join(warnings)
        print('\nBuild Warnings: \n' + '=' * 30)
        print(warnings)
    if errors:
        print('\nBuild Error: \n' + '=' * 30)
        print(errors)

def _get_build_messages():
    """Return the build messages/warnings/errors.
    """
    data = postback.get_build_data()
    return (data.get('build_messages'),
            data.get('build_warnings'),
            data.get('build_error'))


########NEW FILE########
__FILENAME__ = chronos
from fabric.api import local, cd
import os

CHRONOS = "https://code.getpantheon.com/sites/self/code"

def sync_repo():
    os.environ["GIT_SSL_CERT"] = "/etc/pantheon/system.pem"
    project_directory = os.listdir("/var/git/projects/")[0]
    with cd("/var/git/projects/%s" % project_directory):
        local("git push --all %s" % CHRONOS, capture=False)
        local("git fetch %s" % CHRONOS, capture=False)

########NEW FILE########
__FILENAME__ = configure
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import update
import time
import urllib2
import json
from pantheon import ygg
from pantheon import logger

from fabric.api import *

from pantheon import pantheon
from pantheon.vars import *

#TODO: Move logging into the pantheon library
def configure():
    '''configure the Pantheon system.'''
    log = logger.logging.getLogger('pantheon.configure.configure')
    server = pantheon.PantheonServer()
    try:
        _test_for_previous_run()
        _check_connectivity(server)
        _configure_certificates()
        _configure_server(server)
        _configure_postfix(server)
        _restart_services(server)
        _configure_iptables(server)
        _configure_git_repo()
        _mark_incep(server)
        _report()
    except:
        log.exception('Configuration was unsuccessful.')
        raise
    else:
        log.info('Configuration was successful.')
        print('\n\n--- LOCAL CONFIGURATION ---')
        print('MERCURY_BRANCH: %s' % MERCURY_BRANCH)
        print('API_HOST: %s' % API_HOST)
        print('API_PORT: %s' % API_PORT)
        print('VM_CERTIFICATE: %s' % VM_CERTIFICATE)
        result = ygg._api_request('POST', '/sites/self/legacy-phone-home?phase=pantheon_config')

def _test_for_previous_run():
    if os.path.exists("/etc/pantheon/incep"):
        # If the server has a certificate, send an event.
        if os.path.exists("/etc/pantheon/system.pem"):
            ygg.send_event('Restart', 'This site\'s server was restarted, but it is already configured.')
        abort("Pantheon config has already run. Exiting.")

def _check_connectivity(server):
    # Rackspace occasionally has connectivity issues unless a server gets
    # rebooted after initial provisioning.
    try:
        urllib2.urlopen('http://pki.getpantheon.com/', timeout=10)
        print 'Connectivity to the PKI server seems to work.'
    except urllib2.URLError, e:
        print "Connectivity error: ", e
        # Bail if a connectivity reboot has already been attempted.
        if os.path.exists("/etc/pantheon/connectivity_reboot"):
            abort("A connectivity reboot has already been attempted. Exiting.")
        # Record the running of a connectivity reboot.
        with open('/etc/pantheon/connectivity_reboot', 'w') as f:
            f.write('Dear Rackspace: Fix this issue.')
        local('sudo reboot')


def _configure_certificates():
    # Just in case we're testing, we need to ensure this path exists.
    local('mkdir -p /etc/pantheon')

    pantheon.configure_root_certificate('http://pki.getpantheon.com')

    # Now Helios cert is OTS
    pki_server = 'https://pki.getpantheon.com'

    # Ask Helios about what to put into the certificate request.
    try:
        host_info = json.loads(urllib2.urlopen('%s/info' % pki_server).read())
        ou = host_info['ou']
        cn = host_info['cn']
        subject = '/C=US/ST=California/L=San Francisco/O=Pantheon Systems, Inc./OU=%s/CN=%s/emailAddress=hostmaster@%s/' % (ou, cn, cn)
    except ValueError:
        # This fails if Helios says "Could not find corresponding LDAP entry."
        return False

    # Generate a local key and certificate-signing request.
    local('openssl genrsa 4096 > /etc/pantheon/system.key')
    local('chmod 600 /etc/pantheon/system.key')
    local('openssl req -new -nodes -subj "%s" -key /etc/pantheon/system.key > /etc/pantheon/system.csr' % subject)

    # Have the PKI server sign the request.
    local('curl --silent -X POST -d"`cat /etc/pantheon/system.csr`" %s > /etc/pantheon/system.crt' % pki_server)

    # Combine the private key and signed certificate into a PEM file (for Apache and Pound).
    local('cat /etc/pantheon/system.crt /etc/pantheon/system.key > /etc/pantheon/system.pem')
    local('chmod 640 /etc/pantheon/system.pem')
    local('chgrp ssl-cert /etc/pantheon/system.pem')

    # Export cert in pkcs12 format
    local('openssl pkcs12 -export -password pass: -in /etc/pantheon/system.pem -out /etc/pantheon/system.p12')
    local('chmod 600 /etc/pantheon/system.p12')

    # Start pound, which has been waiting for system.pem
    local('/etc/init.d/pound start');

    # Update client config to use unique identifier
    local('sed -i "s/^user = .*/user = %s/g" /etc/bcfg2.conf' % cn)
    # Update BCFG2's client configuration to use the zone (a.k.a. OU) from the certificate
    local('sed -i "s/^bcfg2 = .*/bcfg2 = https:\/\/config.%s:6789/g" /etc/bcfg2.conf' % ou)

    # Wait 20 seconds so
    print 'Waiting briefly so slight clock skew does not affect certificate verification.'
    time.sleep(20)
    verification = local('openssl verify -verbose /etc/pantheon/system.crt')
    print verification

    ygg.send_event('Authorization', 'Certificate issued. Verification result:\n' + verification)

def _configure_server(server):
    ygg.send_event('Software updates', 'Configuration updates have started.')
    # Get any new packages.
    #server.update_packages()
    # Update pantheon code, run bcfg2, restart Jenkins.
    update.update_pantheon(postback=False)
    # Create the tunable files.
    local('cp /etc/pantheon/templates/tuneables /etc/pantheon/server_tuneables')
    local('chmod 755 /etc/pantheon/server_tuneables')
    ygg.send_event('Software updates', 'Configuration updates have finished.')

def _configure_postfix(server):
    ygg.send_event('Email delivery configuration', 'Postfix is now being configured.')

    hostname = server.get_hostname()
    with open('/etc/mailname', 'w') as f:
        f.write(hostname)
    local('/usr/sbin/postconf -e "myhostname = %s"' % hostname)
    local('/usr/sbin/postconf -e "mydomain = %s"' % hostname)
    local('/usr/sbin/postconf -e "mydestination = %s"' % hostname)
    local('/etc/init.d/postfix restart')

    ygg.send_event('Email delivery configuration', 'Postfix is now online.')

def _restart_services(server):
    server.restart_services()


def _configure_iptables(server):
    ygg.send_event('Firewall configuration', 'The kernel\'s iptables module is now being configured.')

    if server.distro == 'centos':
        local('sed -i "s/#-A/-A/g" /etc/sysconfig/iptables')
        local('/sbin/iptables-restore < /etc/sysconfig/iptables')
    else:
        local('sed -i "s/#-A/-A/g" /etc/iptables.rules')
        local('/sbin/iptables-restore < /etc/iptables.rules')

    rules = open('/etc/iptables.rules').read()
    ygg.send_event('Firewall configuration', 'The kernel\'s iptables module is now blocking unauthorized traffic. Rules in effect:\n' + rules)

def _configure_git_repo():
    ygg.send_event('Deployment configuration', 'The git version control tool is now being configured.')
    if os.path.exists('/var/git/projects'):
        local('rm -rf /var/git/projects')
    local('mkdir -p /var/git/projects')
    local("chmod g+s /var/git/projects")
    ygg.send_event('Deployment configuration', 'The git version control tool is now managing testing and deployments for this site.')

def _mark_incep(server):
    '''Mark incep date. This prevents us from ever running again.'''
    hostname = server.get_hostname()
    with open('/etc/pantheon/incep', 'w') as f:
        f.write(hostname)


def _report():
    '''Phone home - helps us to know how many users there are without passing \
    any identifying or personal information to us.

    '''

    print('##############################')
    print('#   Pantheon Setup Complete! #')
    print('##############################')

    local('echo "DEAR SYSADMIN: PANTHEON IS READY FOR YOU NOW." | wall')

    ygg.send_event('Platform configuration', 'The Pantheon platform is now running.')

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import env
from atlas_postback import *
from configure import *
from buildtools import *
from initialization import *
from monitoring import *
from permissions import *
from pantheon.status import *
from site_backup import *
from site_devel import *
from site_onramp import *
from site_install import *
from usage import *
from update import *
from chronos import *
env.hosts = ['pantheon@localhost']

########NEW FILE########
__FILENAME__ = filetest
import os
import random
import shutil
import string
import tempfile
import unittest

from pantheon import onramp
from fabric.api import settings, hide

class FilePathTestCase(unittest.TestCase):
    """Test the import process of normalizing Drupal file paths.

    """

    def setUp(self):
        """Create a fake Drupal root and ImportTools object.

        """
        self.working_dir = tempfile.mkdtemp()
        self.test_import = self.TestImportTools(self.working_dir)

    def test_directory_defaultpath_defaultname(self):
        """sites/default/files."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/files',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist)

    def test_directory_defaultpath_othername(self):
        """sites/default/other."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/other',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_otherpath_defaultname(self):
        """sites/other/files."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/other/files',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_otherpath_othertname(self):
        """sites/other/other."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/other/other',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_rootpath(self):
        """files."""
        start_path, final_path = self.setup_environment(files_dir='files',
                                                        exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_nopath(self):
        """no path."""
        start_path, final_path = self.setup_environment(files_dir=None,
                                                        exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        dir_exists = os.path.exists(final_path)
        files_exist = len(os.listdir(final_path)) == 1 # just .gitignore
        self.assertTrue(dir_exists and files_exist)

    def test_symlink_broken_defaultpath(self):
        """sites/default/files is a broken symlink."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/files',
                                          exists=False,
                                          symlink=True,
                                          name='sites/default/files',
                                          target='foo')
        dir_exists = os.path.exists(final_path)
        files_exist = len(os.listdir(final_path)) == 1 # just .gitignore
        self.assertTrue(dir_exists and files_exist)

    def setup_environment(self, files_dir, exists, symlink=False,
                                                   name=None,
                                                   target=None):
        """Create the necessary directory tree then various import scenarios

        For regular directories you should pass in:
            files_dir: Drupal file_directory_path variable value
                       (e.g. sites/default/files)
            exists: Bool. If the directory should exist.

        For symlinks you should pass in:
            symlink: True
            files_dir: Drupal file_directory_path variable value
                       (e.g. sites/default/files)
            exists: Bool. True = valid symlink, False = broken symlink
            name: The name of the symlink.
            target: where the symlink is targeted. if exist==true a symlink
                    with a relational (valid) path will be created.
                    If exists==False, the symlink will be left as-is (broken).

        """

        # Fake a return value for database file_directory_path variable.
        self.test_import.files_dir = files_dir

        # Normal path
        if not symlink:
            if exists and files_dir is not None:
                self._makedir(files_dir)
                self._makefiles(files_dir)
        # Symlink
        else:
            # Create valid target location for symlink
            if exists:
                pass
            else:
                self._makelink(name=name, target=target)
                import pdb
                pdb.set_trace()

        # Run import processing, suppress fabric errors (mysql will barf)
        with settings(hide('everything'), warn_only=True):
            self.test_import.setup_files_dir()

        # Return (Starting path, Final Path)
        if files_dir:
            start_path = os.path.join(self.working_dir, files_dir)
        else:
            start_path = None
        final_path = os.path.join(self.working_dir, 'sites/default/files')
        return (start_path, final_path)

    def run_checks(self, start_path, final_path):
        # Final path shouls exist.
        dir_exists = os.path.exists(final_path)
        # Two test files and a .gitignore should exist.
        files_exist = len(os.listdir(final_path)) == 3
        # Symlink should exist in old location, pointing to new location.
        if start_path:
            symlink_exists = os.path.islink(start_path) and os.path.realpath(start_path) == final_path
        else:
            symlink_exists = False
        return dir_exists, files_exist, symlink_exists

    def tearDown(self):
        """Cleanup.

        """
        shutil.rmtree(self.working_dir)

    def _makedir(self, d):
        """Create directory 'd' in working_dir. Acts like "mkdir -P"

        """
        os.makedirs(os.path.join(self.working_dir, d))

    def _makelink(self, name, target):
        """Create a symlink with name --> target in working_dir

        """
        name = os.path.join(self.working_dir, name)
        target = os.path.join(self.working_dir, target)
        if not os.path.isdir(os.path.dirname(name)):
            os.makedirs(os.path.dirname(name))
        os.symlink(target,name)

    def _makefiles(self, directory):
        """Create files in the files directory.

        """
        base = os.path.join(self.working_dir, directory)
        for i in range(2):
            with open(os.path.join(base, 'tmp%s.txt' % i), 'w') as f:
                f.write('Test_%s' % i)


    class TestImportTools(onramp.ImportTools):
        """Wrapper to make ImportTools test friendly.

        """
        def __init__(self, working_dir):
            """Override default importtools init and set only necessary vals.

            """
            self.working_dir = working_dir
            # This should be an invalid project so mysql doesn't make changes.
            self.project = 'invalidproject'

        def _get_files_dir(self):
            """Override and return an already known value.
            self.files_dir gets set during setup_environment

            """
            return self.files_dir


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = initialization
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import tempfile

from fabric.api import *

import update
from pantheon import pantheon

def initialize(vps=None, bcfg2_host='config.getpantheon.com'):
    '''Initialize the Pantheon system.'''
    server = pantheon.PantheonServer()
    server.bcfg2_host = bcfg2_host

    _initialize_fabric()
    _initialize_root_certificate()
    _initialize_package_manager(server)
    _initialize_bcfg2(server)
    _initialize_iptables(server)
    _initialize_drush()
    _initialize_solr(server)
    _initialize_sudoers(server)
    _initialize_acl(server)
    _initialize_jenkins(server)
    _initialize_apache(server)

def init():
    '''Alias of "initialize"'''
    initialize()

def _initialize_fabric():
    """Make symlink of /usr/bin/fab -> /usr/local/bin/fab.

    This is because using pip to install fabric will install it to
    /usr/local/bin but we want to maintain compatibility with existing
    servers and jenkins jobs.

    """
    if not os.path.exists('/usr/bin/fab'):
        local('ln -s /usr/local/bin/fab /usr/bin/fab')

def _initialize_root_certificate():
    """Install the Pantheon root certificate.

    """
    pantheon.configure_root_certificate('http://pki.getpantheon.com')

def _initialize_package_manager(server):
    """Setup package repos and version preferences.

    """
    if server.distro == 'ubuntu':
        with cd(server.template_dir):
            local('cp apt.pantheon.list /etc/apt/sources.list.d/pantheon.list')
            local('cp apt.openssh.pin /etc/apt/preferences.d/openssh')
            local('apt-key add apt.ppakeys.txt')
            local('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')
            local('echo \'APT::Cache-Limit "20000000";\' >>  /etc/apt/apt.conf')

    elif server.distro == 'centos':
        local('rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/' + \
              '5/x86_64/ius-release-1.0-6.ius.el5.noarch.rpm')
        local('rpm -Uvh http://yum.fourkitchens.com/pub/centos/' + \
              '5/noarch/fourkitchens-release-5-6.noarch.rpm')
        local('rpm --import http://pkg.jenkins-ci.org/redhat/jenkins-ci.org.key')
        local('wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat/jenkins.repo')
        local('yum -y install git17 --enablerepo=ius-testing')
        arch = local('uname -m').rstrip('\n')
        if (arch == "x86_64"):
            exclude_arch = "*.i?86"
        elif (arch == "i386" or arch == "i586" or arch == "i686"):
            exclude_arch = "*.x86_64"
        if exclude_arch:
            local('echo "exclude=%s" >> /etc/yum.conf' % exclude_arch)

    # Update package metadata and download packages.
    server.update_packages()

def _initialize_bcfg2(server):
    """Install bcfg2 client and run for the first time.

    """
    if server.distro == 'ubuntu':
        local('apt-get install -y gamin python-gamin python-genshi bcfg2')
    elif server.distro == 'centos':
        local('yum -y install bcfg2 gamin gamin-python python-genshi ' + \
              'python-ssl python-lxml libxslt')
    template = pantheon.get_template('bcfg2.conf')
    bcfg2_conf = pantheon.build_template(template, {"bcfg2_host": server.bcfg2_host})
    with open('/etc/bcfg2.conf', 'w') as f:
        f.write(bcfg2_conf)

    # We use our own key/certs.
    local('rm -f /etc/bcfg2.key bcfg2.crt')
    # Run bcfg2
    local('/usr/sbin/bcfg2 -vqed', capture=False)

def _initialize_iptables(server):
    """Create iptable rules from template.

    """
    local('/sbin/iptables-restore < /etc/pantheon/templates/iptables')
    if server.distro == 'centos':
        local('cp /etc/pantheon/templates/iptables /etc/sysconfig/iptables')
        local('chkconfig iptables on')
        local('service iptables start')
    else:
        local('cp /etc/pantheon/templates/iptables /etc/iptables.rules')

def _initialize_drush():
    """Install Drush and Drush-Make.

    """
    with cd('/opt'):
        local('[ ! -d drush ] || rm -rf drush')
        local('git clone http://git.drupal.org/project/drush.git')
        with cd('drush'):
            local('git checkout tags/7.x-4.4')
        local('chmod 555 drush/drush')
        local('chown -R root: drush')
        local('mkdir -p /opt/drush/aliases')
        local('ln -sf /opt/drush/drush /usr/local/bin/drush')
        local('drush dl -y --default-major=6 drush_make')
        with open('/opt/drush/.gitignore', 'w') as f:
            f.write('.gitignore\naliases')

def _initialize_solr(server=pantheon.PantheonServer()):
    """Download Apache Solr.

    """
    temp_dir = tempfile.mkdtemp()
    with cd(temp_dir):
        local('wget http://apache.osuosl.org/lucene/solr/1.4.1/apache-solr-1.4.1.tgz')
        local('tar xvzf apache-solr-1.4.1.tgz')
        local('mkdir -p /var/solr')
        local('mv apache-solr-1.4.1/dist/apache-solr-1.4.1.war /var/solr/solr.war')
        local('chown -R ' + server.tomcat_owner + ':root /var/solr/')
    local('rm -rf ' + temp_dir)

def _initialize_sudoers(server):
    """Create placeholder sudoers files. Used for custom sudoer setup.

    """
    local('touch /etc/sudoers.d/003_pantheon_extra')
    local('chmod 0440 /etc/sudoers.d/003_pantheon_extra')

def _initialize_acl(server):
    """Allow the use of ACLs and ensure they remain after reboot.

    """
    local('sudo tune2fs -o acl /dev/sda1')
    local('sudo mount -o remount,acl /')
    # For after restarts
    local('sudo sed -i "s/noatime /noatime,acl /g" /etc/fstab')

def _initialize_jenkins(server):
    """Add a Jenkins user and grant it access to the directory that will contain the certificate.

    """
    # Create the user if it doesn't exist:
    with settings(warn_only=True):
        local('adduser --system --home /var/lib/jenkins --no-create-home --ingroup nogroup --disabled-password --shell /bin/bash jenkins')

    local('usermod -aG ssl-cert jenkins')
    local('apt-get install -y jenkins')

    # Grant it access:
    #local('setfacl --recursive --no-mask --modify user:jenkins:rx /etc/pantheon')
    #local('setfacl --recursive --modify default:user:jenkins:rx /etc/pantheon')

    # Review the permissions:
    #local('getfacl /etc/pantheon', capture=False)

def _initialize_apache(server):
    """Remove the default vhost and clear /var/www.

    """
    if server.distro == 'ubuntu':
        local('a2dissite default')
        local('rm -f /etc/apache2/sites-available/default*')
        local('rm -f /var/www/*')

########NEW FILE########
__FILENAME__ = monitoring
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import socket
import urllib
import ConfigParser

from pantheon import logger

from fabric.api import *

def _init_cfg():
    # Get our own logger
    log = logger.logging.getLogger('monitor')

    cfg = ConfigParser.ConfigParser()
    conf_file = '/etc/pantheon/services.conf'
    try:
        cfg.readfp(open(conf_file))
    except IOError:
        log.exception('There was an error while loading the configuration file.')
    except:
        log.exception('FATAL: Unhandled exception')
        raise
    return cfg

def check_load_average(limit=None):
    """ Check system load average.
    limit: int. Threshold

    """
    cfg = _init_cfg()
    section = 'load_average'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    loads = os.getloadavg()
    if (float(loads[0]) > float(limit)):
        log.warning('Load average is %s which is above the threshold of %s.' % 
                    (str(loads[0]), str(limit)))
    else:
        log.info('Load average is %s which is below the threshold of %s.' % 
                 (str(loads[0]), str(limit)))

def check_disk_space(path=None, limit=None):
    """ Check system disk usage.
    path: str. Path to check against
    limit: int. Threshold as percentage.

    """
    cfg = _init_cfg()
    section = 'disk_space'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    if not path:
        path = cfg.get(section, 'path')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = os.statvfs(path)
    usage = (s.f_blocks - s.f_bavail)/float(s.f_blocks) * 100
    if (float(usage) > float(limit)):
        log.warning('Disk usage of %s is at %s percent which is above the ' \
                    'threshold of %s percent.' % (path, str(usage), str(limit)))
    else:
        log.info('Disk usage of %s is at %s percent which is above the ' \
                 'threshold of %s percent.' % (path, str(usage), str(limit)))

def check_swap_usage(limit=None):
    """ Check system swap usage.
    limit: int. Threshold as percentage.

    """
    cfg = _init_cfg()
    section = 'swap_usage'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    swap_total = local("free | grep -i swap | awk '{print $2}'")
    swap_used = local("free | grep -i swap | awk '{print $3}'")
    usage = float(swap_used)/float(swap_total) * 100
    if (usage > float(limit)):
        log.warning('Swap usage is a %s percent which is above the ' \
                    'threshold of %s percent.' % (str(usage), str(limit)))
    else:
        log.info('Swap usage is a %s percent which is below the ' \
                 'threshold of %s percent.' % (str(usage), str(limit)))

def check_io_wait_time(limit=None):
    """ Check system io wait time.
    limit: int. Threshold as percentage.

    """
    cfg = _init_cfg()
    section = 'io_wait_time'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    iowait = local("vmstat | grep -v [a-z] | awk '{print $16}'").rstrip()
    if (float(iowait) > float(limit)):
        log.warning('IO wait times are at %s percent which is above the ' \
                    'threshold of %s percent.' % (str(iowait), str(limit)))
    else:
        log.info('IO wait times are at %s percent which is below the ' \
                 'threshold of %s percent.' % (str(iowait), str(limit)))

def check_mysql(slow_query_limit=None, memory_usage=None, innodb_memory_usage=None, threads=None):
    """ Check mysql status.
    sloq_query_limit: int. Threshold as percentage.
    memory_usage: int. Threshold as percentage.
    innodb_memory_usage: int. Threshold as percentage.
    thread: int. Threshold as percentage.

    """
    cfg = _init_cfg()
    section = 'mysql'
    if not slow_query_limit:
        slow_query_limit = cfg.getfloat(section, 'slow_query_limit')
    if not memory_usage:
        memory_usage = cfg.getfloat(section, 'memory_usage')
    if not innodb_memory_usage:
        innodb_memory_usage = cfg.getfloat(section, 'innodb_memory_usage')
    if not threads:
        threads = cfg.getfloat(section, 'threads')
    log = logger.logging.getLogger('monitor.%s' % section)

    with settings(warn_only=True):
        messages = list()
        report = local('mysqlreport')
        if report.failed:
            log.warning('mysql server does not appear to be running: %s' % 
                           report)
        else:
          for line in report.splitlines():
              #check for slow wait times:
              if ('Slow' in line and 'Log' in line):
                  if (float(line.split()[5]) > float(slow_query_limit)):
                      messages.append('MYSQL slow queries is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], str(slow_query_limit)))
                  else:
                      messages.append('MYSQL slow queries is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], str(slow_query_limit)))

              #check overall memory usage
              elif ('Memory usage' in line):
                  if (float(line.split()[6]) > float(memory_usage)):
                      messages.append('MYSQL memory usage is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[6], str(memory_usage)))
                  else:
                      messages.append('MYSQL memory usage is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[6], str(memory_usage)))

              #check InnoDB memory usage
              elif ('Usage' in line and 'Used' in line):
                  if (float(line.split()[5]) > float(innodb_memory_usage)):
                      messages.append('InnoDB memory usage is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], 
                                       str(innodb_memory_usage)))
                  else:
                      messages.append('InnoDB memory usage is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], 
                                       str(innodb_memory_usage)))

              #check thread usage
              elif ('Max used' in line):
                  if (float(line.split()[6]) > float(threads)):
                      messages.append('Thread usage is %s percent which is ' \
                                      'above the threshold of %s percent.' % 
                                      (line.split()[6], str(threads)))
                  else:
                      messages.append('Thread usage is %s percent which is ' \
                                      'below the threshold of %s percent.' % 
                                      (line.split()[6], str(threads)))
                 
          message = ' '.join(messages)
          if 'above' in message: 
              log.warning(message)
          else:
              log.info(message)

def check_apache(url=None):
    """ Check apache status.
    url: str. Url to test

    """
    cfg = _init_cfg()
    section = 'apache'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_varnish(url=None):
    """ Check varnish status.
    url: str. Url to test

    """
    cfg = _init_cfg()
    section = 'varnish'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_pound_via_apache(url=None):
    """ Check pound status.
    url: str. Url to test

    """
    cfg = _init_cfg()
    section = 'pound'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_pound_via_socket(port=None):
    """ Check pound status.
    port: str. Port to test

    """
    cfg = _init_cfg()
    section = 'pound'
    if not port:
        port = cfg.getint(section, 'port')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        log.exception('Cannot connect to Pound on %s at %s.' % 
                      ('localhost', str(port)))
    else:
        log.info('pound responded')

def check_memcached(port=None):
    """ Check memcached status.
    port: str. Port to test

    """
    cfg = _init_cfg()
    section = 'memcached'
    if not port:
        port = cfg.getint(section, 'port')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        log.exception('Cannot connect to Memcached on %s %s.' % 
                      ('localhost', str(port)))
    else:
        log.info('memcached responded')

def _test_url(url):
    """ Test url response code.
    url: str. Url to test

    """
    return urllib.urlopen(url).code

# TODO: figure out what to search for from the following output
#    print(connection.info())
#    print(connection.read())

########NEW FILE########
__FILENAME__ = backup
import base64
import hashlib
import httplib
import json
import os
import string
import sys
import tempfile

from configobj import ConfigObj
from fabric.api import *

import pantheon
import logger
import ygg
import rangeable_file
from vars import *

ARCHIVE_SERVER = "s3.amazonaws.com"

def remove(archive):
    """Remove a backup tarball from the server.
    archive: name of the archive to remove.

    """
    log = logger.logging.getLogger('pantheon.backup.remove')
    try:
        server = pantheon.PantheonServer()
        path = os.path.join(server.ftproot, archive)
        if os.path.exists(path):
            local('rm -f %s' % path)
    except:
        log.exception('Removal of local backup archive was unsuccessful.')
        raise
    else:
        log.debug('Removal of local backup archive successful.')

class PantheonBackup():

    def __init__(self, name, project):
        """Initialize Backup Object.
        name: name of backup (resulting file: name.tar.gz)
        project: name of project to backup.

        """
        self.server = pantheon.PantheonServer()
        self.project =  project
        self.environments = pantheon.get_environments()
        self.working_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.working_dir, self.project)
        self.name = name + '.tar.gz'
        self.log = logger.logging.getLogger('pantheon.backup.PantheonBackup')
        self.log = logger.logging.LoggerAdapter(self.log,
                                                {"project": project})

    def get_dev_code(self, user):
        """USED FOR REMOTE DEV: Clone of dev git repo.

        """
        self.log.info('Initialized archive of code.')
        try:
            server_name = _get_server_name(self.project)
            local('mkdir -p %s' % self.backup_dir)
            source = os.path.join(self.server.webroot, self.project, 'dev')
            destination = 'code'
            with cd(self.backup_dir):
                local('git clone %s -b %s %s' % (source,
                                                 self.project,
                                                 destination))
                # Manually set origin URL so remote pushes have a destination.
                with cd(destination):
                    local("sed -i 's/^.*url =.*$/\\turl = " + \
                    "%s@%s.gotpantheon.com:\/var\/git\/projects\/%s/' " \
                    ".git/config" % (user, server_name, self.project))
        except:
            self.log.exception('Archival of code was unsuccessful.')
            raise
        else:
            self.log.info('Archive of code successful.')

    def get_dev_files(self):
        """USED FOR REMOTE DEV: dev site files.

        """
        self.log.info('Initialized archive of files.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            source = os.path.join(self.server.webroot, self.project,
                                          'dev/sites/default/files')
            destination = self.backup_dir
            # If 'dev_code' exists in backup_dir,
            # this is a full dev-archive dump.
            # Place the files within the drupal site tree.
            if os.path.exists(os.path.join(self.backup_dir,
                                           'dev_code/sites/default')):
                destination = os.path.join(self.backup_dir,
                                           'dev_code/sites/default')
            local('rsync -avz %s %s' % (source, destination))
        except:
            self.log.exception('Archival of files was unsuccessful.')
            raise
        else:
            self.log.info('Archive of files successful.')

    def get_dev_data(self):
        """USED FOR REMOTE DEV: dev site data.

        """
        self.log.info('Initialized archive of data.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                                     self.project, 'dev'))
            destination = os.path.join(self.backup_dir, 'dev_database.sql')
            self._dump_data(destination, drupal_vars)
        except:
            self.log.exception('Archival of data was unsuccessful.')
            raise
        else:
            self.log.info('Archive of data successful.')


    def get_dev_drushrc(self, user):
        """USED FROM REMOTE DEV: create a drushrc file.

        """
        self.log.info('Initialized archive of drush.')
        try:
            server_name = _get_server_name(self.project)
            local('mkdir -p %s' % self.backup_dir)
            # Build the environment specific aliases
            env_aliases = ''
            template = string.Template(_get_env_alias())

            for env in self.environments:
                values = {'host': '%s.gotpantheon.com' % server_name,
                          'user': user,
                          'project': self.project,
                          'env': env,
                          'root': '/var/www/%s/%s' % (self.project, env)}
                env_aliases += template.safe_substitute(values)

            destination = os.path.join(self.backup_dir,
                                       '%s.aliases.drushrc.php' % self.project)

            with open(destination, 'w') as f:
                f.write('<?php\n%s\n' % env_aliases)
        except:
            self.log.exception('Archival of drush was unsuccessful.')
            raise
        else:
            self.log.info('Archive of drush successful.')

    def free_space(self):
        """Returns bool. True if free space is greater then backup size.

        """
        #Get the total free space
        fs = os.statvfs('/')
        fs = int(fs.f_bavail * fs.f_frsize / 1024)
        #Calc the disk usage of project webroot and git repo
        paths = [os.path.join(self.server.webroot, self.project),
                 os.path.join('/var/git/projects', self.project)]
        result = local('du -slc {0}'.format(' '.join(paths)))
        ns = int(result[result.rfind('\n')+1:result.rfind('\t')])
        #Calc the database size of each env
        for env in self.environments:
            result = local('mysql --execute=\'SELECT IFNULL(ROUND((' \
                'sum(DATA_LENGTH) + sum(INDEX_LENGTH) - sum(DATA_FREE))' \
                '/1024), 0) AS Size FROM INFORMATION_SCHEMA.TABLES where ' \
                'TABLE_SCHEMA =  "{0}_{1}"\G\''.format(self.project, env))
            ns += int(result[result.rfind(' ')+1:])
        #Double needed space to account for tarball
        return fs > (ns*2)

    def backup_files(self):
        """Backup all files for environments of a project.

        """
        self.log.info('Initialized backup of files.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            for env in self.environments:
                source = os.path.join(self.server.webroot, self.project, env)
                local('rsync -avz %s %s' % (source, self.backup_dir))
        except:
            self.log.exception('Backing up the files was unsuccessful.')
            raise
        else:
            self.log.info('Backup of files successful.')

    def backup_data(self):
        """Backup databases for environments of a project.

        """
        self.log.info('Initialized backup of data.')
        try:
            for env in self.environments:
                drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                                   self.project, env))
                dest = os.path.join(self.backup_dir, env, 'database.sql')
                self._dump_data(dest, drupal_vars)
        except:
            self.log.exception('Backing up the data was unsuccessful.')
            raise
        else:
            self.log.info('Backup of data successful.')

    def backup_repo(self):
        """Backup central repository for a project.

        """
        self.log.info('Initialized backup of repo.')
        try:
            dest = os.path.join(self.backup_dir, '%s.git' % (self.project))
            local('rsync -avz /var/git/projects/%s/ %s' % (self.project, dest))
        except:
            self.log.exception('Backing up the repo was unsuccessful.')
            raise
        else:
            self.log.info('Backup of repo successful.')

    def backup_config(self, version):
        """Write the backup config file.
        version: int. Backup schema version. Used to maintain backward
                 compatibility as backup formats could change.

        """
        self.log.info('Initialized backup of config.')
        try:
            config_file = os.path.join(self.backup_dir, 'pantheon.backup')
            config = ConfigObj(config_file)
            config['backup_version'] = version
            config['project'] = self.project
            config.write()
        except:
            self.log.exception('Backing up the config was unsuccessful.')
            raise
        else:
            self.log.info('Backup of config successful.')

    def finalize(self, destination=None):
        """ Create archive, move to destination, remove working dir.

        """
        try:
            self.make_archive()
            self.move_archive()
        except:
            self.log.error('Failure creating/storing backup.')

        self.cleanup()

    def make_archive(self):
        """Tar/gzip the files to be backed up.

        """
        self.log.info('Making archive.')
        try:
            with cd(self.working_dir):
                local('tar czf %s %s' % (self.name, self.project))
        except:
            self.log.exception('Making of the archive was unsuccessful.')
            raise
        else:
            self.log.info('Make archive successful.')

    def move_archive(self):
        """Move archive from temporary working dir to S3.

        """
        self.log.info('Moving archive to external storage.')
        path = '%s/%s' % (self.working_dir, self.name)
        try:
            Archive(path).submit()
        except:
            self.log.exception('Upload to remote storage unsuccessful.')
        else:
            self.log.info('Upload %s to remote storage complete.' % self.name)

    def cleanup(self):
        """ Remove working_dir """
        self.log.debug('Cleaning up.')
        try:
            local('rm -rf %s' % self.working_dir)
        except:
            self.log.exception('Cleanup unsuccessful.')
            raise
        else:
            self.log.debug('Cleanup successful.')


    def _dump_data(self, destination, db_dict):
        """Dump a database to a .sql file.
        destination: Full path to dump file.
        db_dict: db_username
                 db_password
                 db_name

        """
        result = local("mysqldump --single-transaction \
                                  --user='%s' --password='%s' %s > %s" % (
                                         db_dict.get('db_username'),
                                         db_dict.get('db_password'),
                                         db_dict.get('db_name'),
                                         destination))
        if result.failed:
            abort("Export of database '%s' failed." % db_dict.get('db_name'))

class Archive():
    def __init__(self, path, threshold=4194304000, chunk_size=4194304000):
        """Initiates an archivable file object

        Keyword arguements:
        path       -- the path to the file
        threshold  -- filesize at which we switch to multipart upload
        chunk_size -- the size to break multipart uploads into

        """
        self.connection = httplib.HTTPSConnection(
                                                  API_HOST,
                                                  API_PORT,
                                                  key_file = VM_CERTIFICATE,
                                                  cert_file = VM_CERTIFICATE)
        self.path = path
        self.filesize = os.path.getsize(path)
        self.threshold = threshold
        self.filename = os.path.basename(path)
        self.partno = 0
        self.parts = []
        self.chunk_size = chunk_size
        self.log = logger.logging.getLogger('pantheon.backup.Archive')

    def is_multipart(self):
        # Amazon S3 has a minimum upload size of 5242880
        assert self.filesize >= 5242880,"File size is too small."
        assert self.chunk_size >= 5242880,"Chunk size is too small."
        return True if self.filesize > self.threshold else False

    def submit(self):
        if self.filesize < self.threshold:
            # Amazon S3 has a maximum upload size of 5242880000
            assert self.threshold < 5242880000,"Threshold is too large."
            fo = open(self.path)
            info = json.loads(self._get_upload_header(fo))
            response = self._arch_request(fo, info)
            self._complete_upload()
        elif self.is_multipart():
            self.log.info('Large backup detected. Using multipart upload ' \
                          'method.')
            #TODO: Use boto to get upid after next release
            #self.upid = json.loads(self._initiate_multipart_upload())
            info = json.loads(self._initiate_multipart_upload())
            response = self._arch_request(None, info)
            from xml.etree import ElementTree
            self.upid = ElementTree.XML(response.read()).getchildren()[2].text
            for chunk in rangeable_file.fbuffer(self.path, self.chunk_size):
                info = json.loads(self._get_multipart_upload_header(chunk))
                self.log.info('Sending part {0}'.format(self.partno))
                response = self._arch_request(chunk, info)
                etag = response.getheader('etag')
                self.parts.append((self.partno, etag))
            self._complete_multipart_upload()
        self.connection.close()

    def _hash_file(self, fo):
        """ Return MD5 hash of file object

        Keyword arguements:
        fo -- the file object to hash

        """
        fo_hash = hashlib.md5()
        for chunk in iter(lambda: fo.read(128*fo_hash.block_size), ''):
            fo_hash.update(chunk)
        return base64.b64encode(fo_hash.digest())

    def _initiate_multipart_upload(self):
        """ Return the upload id from api."""
        # Get the authorization headers.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'initiate'}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _get_multipart_upload_header(self, part):
        """ Return multipart upload headers from api.

        Keyword arguements:
        part -- file object to get headers for

        """
        # Get the MD5 hash of the file.
        self.log.debug("Archiving file at path: %s" % self.path)
        part_hash = self._hash_file(part)
        self.log.debug("Hash of file is: %s" % part_hash)
        self.partno+=1
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash,
                   'multipart': 'upload',
                   'upload-id': self.upid,
                   'part-number': self.partno}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _get_upload_header(self, fo):
        """ Return upload headers from api.

        Keyword arguements:
        fo -- file object to get headers for

        """
        self.log.debug("Archiving file at path: %s" % self.path)
        part_hash = self._hash_file(fo)
        self.log.debug("Hash of file is: %s" % part_hash)
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    #TODO: re-work multipart upload completion into the rest api
    def _complete_multipart_upload(self):
        """ Return multipart upload completion response from api."""
        # Notify the event system of the completed transfer.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'complete',
                   'upload-id': self.upid,
                   'parts': self.parts}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _complete_upload(self):
        """ Return upload completion response from api."""
        path = "/sites/self/archive/{0}/complete".format(self.filename)
        return self._api_request(path)

    #TODO: Maybe refactored into the ygg library
    def _api_request(self, path, encoded_headers=None):
        """Returns encoded response data from api.

        Keyword arguements:
        path            -- api request path
        encoded_headers -- api request headers
        Make PUT request to config server.

        """
        self.connection.connect()
        if encoded_headers:
            self.connection.request("PUT", path, encoded_headers)
        else:
            self.connection.request("PUT", path)

        complete_response = self.connection.getresponse()
        if complete_response.status == 200:
            self.log.debug('Successfully obtained authorization.')
        else:
            self.log.error('Obtaining authorization failed.')
            raise Exception(complete_response.reason)
        encoded_info = complete_response.read()
        return encoded_info

    def _arch_request(self, data, info):
        """Returns encoded response data from archive server.

        Keyword arguements:
        data -- data to archive
        info -- api request headers
        Make PUT request to store data on archive server.

        """
        # Transfer the file to long-term storage.
        arch_connection = httplib.HTTPSConnection(info['hostname'])
        if data:
            data.seek(0,2)
            self.log.info('Sending %s bytes to remote storage' % data.tell())
            data.seek(0)
        arch_connection.request(info['verb'],
                                info['path'],
                                data,
                                info['headers'])
        arch_complete_response = arch_connection.getresponse()
        if arch_complete_response.status == 200:
            if data:
                self.log.info('Successfully pushed the file to remote storage.')
        else:
            self.log.error('Uploading file to remote storage failed.')
            raise Exception(arch_complete_response.reason)
        return arch_complete_response

def _get_server_name(project):
    """Return server name from apache alias "env.server_name.gotpantheon.com"
    """
    config = ygg.get_config()
    alias = config[project]['environments']['dev']['apache']['ServerAlias']
    return alias.split('.')[1]

def _get_env_alias():
    """Return slug of php for drushrc.

    """
    return """
$aliases['${project}_${env}'] = array(
  'remote-host' => '${host}',
  'remote-user' => '${user}',
  'uri' => 'default',
  'root' => '${root}',
);
"""

########NEW FILE########
__FILENAME__ = dbtools
import MySQLdb
import os
import pantheon
from fabric.api import local

def export_data(self, environment, destination):
    """Export the database for a particular project/environment to destination.

    Exported database will have a name in the form of:
        /destination/project_environment.sql

    """
    project = self.project
    filepath = os.path.join(destination, '%s_%s.sql' % (project, environment))
    username, password, db_name = pantheon.get_database_vars(self, environment)
    local("mysqldump --single-transaction --user='%s' \
                                          --password='%s' \
                                            %s > %s" % (username,
                                                       password,
                                                       db_name,
                                                       filepath))
    return filepath

def import_data(self, environment, source):
    """Create database then import from source.

    """
    (db_username, db_password, db_name) = pantheon.get_database_vars(self, environment)
    create_database(db_name)
    import_db_dump(source, db_name)

def create_database(database):
    """Drop database if it already exists, then create a new empty db.

    """
    db = MySQLConn()
    db.execute('DROP DATABASE IF EXISTS %s' % database)
    db.execute('CREATE DATABASE %s' % database)
    db.close()

def set_database_grants(database, username, password):
    """Grant ALL on database using username/password.

    """
    db = MySQLConn()
    db.execute("GRANT ALL ON %s.* TO '%s'@'localhost' \
                IDENTIFIED BY '%s';" % (database,
                                        username,
                                        password))
    db.close()

def import_db_dump(database_dump, database_name):
    """Import database_dump into database_name.
    database_dump: full path to the database dump.
    database_name: name of existing database to import into.

    """
    local('mysql -u root %s < "%s"' % (database_name, database_dump))

def convert_to_innodb(database):
    """Convert all table engines to InnoDB (if possible).

    """
    db = MySQLConn(cursor=MySQLdb.cursors.DictCursor)
    tables = db.execute("SELECT TABLE_NAME AS name, ENGINE AS engine " + \
                        "FROM information_schema.TABLES "+ \
                        "WHERE TABLE_SCHEMA = '%s'" % database)
    for table in tables:
        if table.get('engine') != 'InnoDB':
            db.execute("ALTER TABLE %s.%s ENGINE='InnoDB'" % (database,
                                                    table.get('name')),
                                                        warn_only=True)
    db.close()

def clear_cache_tables(database):
    """Clear Drupal cache tables.

    """
    db = MySQLConn(cursor=MySQLdb.cursors.DictCursor)
    # tuple of strings to match agains table_name.startswith()
    caches = ('cache_')
    # Other exact matches to look for and clear.
    other = ['ctools_object_cache',
             'accesslog',
             'watchdog']
    tables = db.execute("SELECT TABLE_NAME AS name " + \
                        "FROM information_schema.TABLES " + \
                        "WHERE TABLE_SCHEMA = '%s'" % database)
    for table in tables:
        table_name = table.get('name')
        if (table_name.startswith(caches)) or (table_name in other):
            db.execute('TRUNCATE %s.%s' % (database, table_name))
    db.close()


class MySQLConn(object):

    def __init__(self, username='root', password='', database=None, cursor=None):
        """Initialize generic MySQL connection object.
        If no database is specified, makes a connection with no default db.

        """
        self.connection = self._mysql_connect(database, username, password)
        self.cursor = self.connection.cursor(cursor)

    def execute(self, query, fetchall=True, warn_only=False):
        """Execute a command on the connection.
        query: SQL statement.

        """
        try:
            self.cursor.execute(query)
            self.connection.commit()
        except MySQLdb.Error, e:
            self.connection.rollback()
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            if not warn_only:
                raise
        except MySQLdb.Warning, w:
            print "MySQL Warning: %s" % (w)
        if fetchall:
            return self.cursor.fetchall()
        else:
            return self.cursor.fetchone()

    def vget(self, name):
        """Return the value of a Drupal variable.
        name: The variable name.

        """
        query = "SELECT value FROM variable WHERE name = '%s'" % name
        try:
            value = self.execute(query=query, fetchall=False)
            # Record found, unserialize value.
            if value is not None:
                result = _php_unserialize(value[0])
            # No record found.
            else:
                result = None
        except:
            print "ERROR: Unable to query for variable '%s'" % name
            result = False
        finally:
            # Use rollback in case values have changed elsewhere.
            self.connection.rollback()
            return result

    def vset(self, name, value):
        """Set the value of a Drupal variable.
        name: variable name to change
        value: The value to set (type sensitive).

        """
        result = self.vget(name)
        # If result is False, we couldn't query the DB.
        if result is not False:
            value = _php_serialize(value)
            # Update if variable exists.
            if result is not None:
                query = "UPDATE variable SET value='%s' WHERE name='%s'" % \
                        (value, name)
            # Insert if variable does not exist.
            else:
                query = "INSERT INTO variable (name, value) " + \
                        "VALUES ('%s','%s')" % (name, value)
            self.execute(query=query, fetchall=False)
            #print 'Variable [%s] set to: %s' % (name, value)

    def close(self):
        """Close database connection.

        """
        self.cursor.close()
        self.connection.close()

    def _mysql_connect(self, database, username, password):
        """Return a MySQL connection object.

        """
        try:
            conn = {'host': 'localhost',
                    'user': username,
                    'passwd': password}

            if database:
                conn.update({'db': database})

            return MySQLdb.connect(**conn)

        except MySQLdb.Error, e:
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            raise


def _php_serialize(data):
    """Convert data into php serialized format.
    data: data to convert (type sensitive)

    """
    vtype = type(data)
    # String
    if vtype is str:
        return 's:%s:"%s";' % (len(data), data)
    # Integer
    elif vtype is int:
        return 'i:%s;' % data
    # Float / Long
    elif vtype is long or vtype is float:
        return 'd:%f;'
    # Boolean
    elif vtype is bool:
        if data:
            return 'b:1;'
        else:
            return 'b:0;'
    # None
    elif vtype is None:
        return 'N;'
    # Dict
    elif vtype is dict:
        return 'a:%s:{%s}' % (len(data),
                              ''.join([_php_serialize(k) + \
                                       _php_serialize(v) \
                                       for k,v in data.iteritems()]))

def _php_unserialize(data):
    """Convert data from php serialize format to python data types.
    data: data to convert (string)

    Currently only supports converting serialized strings.

    """
    vtype = data[0:1]
    if vtype == 's':
        length, value = data[2:].rstrip(';').split(':', 1)
        return str(value)
    elif vtype == 'i':
        return int(data[2:-1])
    elif vtype == 'd':
        return float(data[2:-1])
    elif vtype == 'b':
        return bool(data[2:-1])
    elif vtype == 'N':
        return None
    elif vtype == 'a':
        #TODO fake it till you make it.
        return 'Array'
    else:
        return False



########NEW FILE########
__FILENAME__ = drupaltools
import os
import sys
import tempfile

from fabric.api import *
import MySQLdb

import pantheon

def updatedb(alias):
    with settings(warn_only=True):
        result = local('drush %s -by updb' % alias)
    return result

def get_drupal_update_status(project):
    """Return dictionary of Drupal/Pressflow version/update information.
    project: Name of project.

    """
    repo_path = os.path.join('/var/git/projects', project)
    project_path = os.path.join(pantheon.PantheonServer().webroot, project)
    environments = pantheon.get_environments()
    status = dict()

    with cd(repo_path):
        # Get upstream updates.
        local('git fetch origin')
        # Determine latest upstream version.
        latest_drupal_version = _get_latest_drupal_version()

    for env in environments:
        env_path = os.path.join(project_path, env)

        with cd(env_path):
            local('git fetch origin')

            drupal_version = get_drupal_version(env_path)

            # python -> json -> php boolean disagreements. Just use int.
            drupal_update = int(latest_drupal_version != drupal_version)

            # Determine if there have been any new commits.
            # NOTE: Removed reporting back with log entries, so using logs
            # to determine if there is an update is a little silly. However,
            # we may want to send back logs someday, so leaving for now.
            pantheon_log = local('git log refs/heads/%s' % project + \
                                 '..refs/remotes/origin/master').rstrip('\n')

            # If log is impty, no updates.
            pantheon_update = int(bool(pantheon_log))

            #TODO: remove the reference to platform once Atlas no longer uses it.
            status[env] = {'drupal_update': drupal_update,
                           'pantheon_update': pantheon_update,
                           'current': {'platform': 'DRUPAL',
                                       'drupal_version': drupal_version},
                           'available': {'drupal_version': latest_drupal_version,}}
    return status

def get_drupal_version(drupal_root):
    """Return the current drupal version.

    """
    # Drupal 6 uses system.module, drupal 7 uses bootstrap.inc
    locations = [os.path.join(drupal_root, 'modules/system/system.module'),
                 os.path.join(drupal_root, 'includes/bootstrap.inc')]

    version = None
    for location in locations:
        version = _parse_drupal_version(location)
        if version:
            break
    return version

def _get_latest_drupal_version():
    """Check master (upstream) files to determine newest drupal version.

    """
    locations = ['modules/system/system.module',
                 'includes/bootstrap.inc']
    version = None
    for location in locations:
        contents = local('git cat-file blob refs/heads/master:%s' % location)
        temp_file = tempfile.mkstemp()[1]
        with open(temp_file, 'w') as f:
            f.write(contents)
        version = _parse_drupal_version(temp_file)
        local('rm -f %s' % temp_file)
        if version:
            break
    return version

def _parse_drupal_version(location):
    """Parse file at location to determine the Drupal version.
    location: full path to file to parse.

    """
    version = local("awk \"/define\(\'VERSION\'/\" " + location + \
                 " | sed \"s_^.*'\([6,7]\{1\}\)\.\([0-9]\{1,2\}\).*_\\1-\\2_\""
                 ).rstrip('\n')
    if len(version) > 1 and version[0:1] in ['6', '7']:
        return version
    return None


########NEW FILE########
__FILENAME__ = gittools
import os
import sys

from fabric.api import *

import pantheon

def post_receive_hook(params):
    """Perform post-receive actions when changes are made to git repo.
    params: hook params from git stdin.

    NOTE: we use 'env -i' to clear environmental variables git has set when
    running hook operations.

    """
    (project, old_rev, new_rev) = _parse_hook_params(params)
    webroot = pantheon.PantheonServer().webroot
    dest = os.path.join(webroot, project, 'dev')

    # Check for development environment.
    if not os.path.exists(dest):
        print "\n\nWARNING: No development environment for " + \
              "'%s' was found.\n" % (project)
    # Development environment exists.
    else:
        with cd(dest):
            # Hide output from showing on git's report back to user.
                with settings(hide('running', 'warnings'), warn_only=True):
                    dev_update = local('env -i git pull')
                # Output status to the git push initiator.
                if dev_update.failed:
                    print "\n\nWARNING: The development environment could" + \
                    "not be updated. Please review any error messages, and " + \
                    "resolve any conflicts in /var/www/%s/dev\n" % project
                    print "ERROR:"
                    print dev_update.stderr + "\n\n"
                else:
                    print "\nDevelopment environment updated.\n"

        with hide('running'):
            # If not inside a jenkins job, send back data about repo and drupal.
            # Otherwise, we assume the job we are inside of will do this.
            if not os.environ.get('BUILD_TAG'):
                local('curl http://127.0.0.1:8090/job/post_hook_status/' + \
                      'buildWithParameters?project=%s' % project)

def _parse_hook_params(params):
    """Parse the params received during a git push.
    Return project name, old revision, new revision.

    """
    (revision_old, revision_new, refs) = params.split(' ')
    project = refs.split('/')[2].rstrip('\n')
    return (project, revision_old, revision_new)


class GitRepo():

    def __init__(self, project):
        self.project = project
        self.repo = os.path.join('/var/git/projects', self.project)
        self.server = pantheon.PantheonServer()
        self.project_path = os.path.join(self.server.webroot, self.project)

    def get_repo_status(self):
        """Return dict of dev/test and test/live diffs, and last 10 log entries.

        """
        head = self._get_last_commit('dev')
        test = self._get_last_commit('test')
        live = self._get_last_commit('live')

        #dev/test diff
        diff_dev_test = self._get_diff_stat(test, head)
        #test/live diff
        diff_test_live = self._get_diff_stat(live, test)
        #log
        log = self._get_log(10)

        return {'diff_dev_test':diff_dev_test,
                'diff_test_live':diff_test_live,
                'log':log}

    def _get_last_commit(self, env):
        """Get last commit or tag for the given environment.
        env: environment.

        returns commit hash for dev, or current tag for test/live.

        """
        with cd(os.path.join(self.project_path, env)):
            if env == 'dev':
                ref = local('git rev-parse refs/heads/%s' %  self.project)
            else:
                ref = local('git describe --tags %s' % self.project).rstrip('\n')
        return ref

    def _get_diff_stat(self, base, other):
        """return diff --stat of base/other.
        base: commit hash or tag
        other: commit hash or tag

        """
        with cd(self.repo):
            with settings(warn_only=True):
                diff = local('git diff --stat %s %s' % (base, other))
        return diff

    def _get_log(self, num_entries):
        """Return num_entries of git log.
        num_entries: int. Number of entries to return

        """
        with cd(self.repo):
            log = local('git log -n%s %s' % (num_entries, self.project))
        return log


########NEW FILE########
__FILENAME__ = install
import os
import random
import re
import string
import sys
import tempfile

from fabric.api import *

import drupaltools
import pantheon
import project

class InstallTools(project.BuildTools):

    def __init__(self, **kw):
        """ Initialize generic installation object & helper functions. """
        super(InstallTools, self).__init__()
        self.working_dir = tempfile.mkdtemp()
        self.author = 'Jenkins User <jenkins@pantheon>'
        self.destination = os.path.join(self.server.webroot, self.project)
        self.version = kw.get('version', 6)

    def setup_working_dir(self):
        super(InstallTools, self).setup_working_dir(self.working_dir)

    def process_gitsource(self, url):
        self.setup_project_repo(url)
        self.setup_project_branch()
        self.setup_working_dir()
        self.version = int(drupaltools.get_drupal_version(self.working_dir)[:1])

    def process_makefile(self, url):
        # Get makefile and store in a temporary location
        tempdir = tempfile.mkdtemp()
        makefile = os.path.join(tempdir, 'install.make')
        local('curl %s > %s' % (url, makefile))

        with open(makefile, 'r') as f:
            contents = f.read()

        # Determine core version. Default to 6.
        version = re.search('\s*core\s*=\s*([67])\..*', contents)
        if version is not None:
            try:
                self.version = int(version.group(1))
            except IndexError:
                self.version = 6
        else:
            self.version = 6

        # Now that we know the version, setup a local repository.
        super(InstallTools, self).setup_project_repo()

        # Comment out any pre-defined "core" as we will replace with pressflow.
        with cd(tempdir):
            # core defined like project[drupal] =
            local(r"sed -i 's/^\(.*projects\[drupal\].*\)/;\1/' install.make")
            # core defined like project[] =
            local(r"sed -i 's/^\(.*projects\[\]\s*=\s*[\s\"]drupal[\s\"].*\)/;\1/' install.make")

        # Replace 'core' with pressflow
        with open(makefile, 'a') as f:
            f.write('\nprojects[pressflow][type] = "core"')
            f.write('\nprojects[pressflow][download][type] = git')
            f.write('\nprojects[pressflow][download][url] = ' + \
            'git://github.com/pantheon-systems/pantheon%s.git\n' % self.version)

        # Remove the working directory, drush doesn't like it to exist.
        local('rmdir %s' % self.working_dir)
        local('drush make %s %s' % (makefile, self.working_dir), capture=False)

        # Makefiles could use vc repos as sources, remove all metadata.
        with cd(self.working_dir):
            with settings(hide('warnings'), warn_only=True):
                local("find . -depth -name .git -exec rm -fr {} \;")
                local("find . -depth -name .bzr -exec rm -fr {} \;")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")

        # Create a project branch
        with cd(os.path.join('/var/git/projects', self.project)):
            local('git branch %s' % self.project)

        # Get the .git data for the project repo, and put in the working_dir
        tempdir = tempfile.mkdtemp()
        local('git clone /var/git/projects/%s -b %s %s' % (self.project,
                                                           self.project,
                                                           tempdir))
        local('mv %s %s' % (os.path.join(tempdir, '.git'), self.working_dir))
        local('rm -r %s' % tempdir)

        # Commit the result of the makefile.
        with cd(self.working_dir):
            local('git add .')
            local("git commit -am 'Build from makefile'")

    def setup_database(self):
        """ Create a new database and set user grants. """
        for env in self.environments:
            super(InstallTools, self).setup_database(env, self.db_password)

    def setup_files_dir(self):
        """ Creates Drupal files directory and sets gitignore for all sub-files

        """
        path = os.path.join(self.working_dir, 'sites/default/files')
        local("mkdir -p %s " % path)
        with open('%s/.gitignore' % path, 'a') as f:
            f.write('*\n')
            f.write('!.gitignore\n')

    def setup_settings_file(self):
        """ Create settings.php and pantheon.settings.php

        """
        site_dir = os.path.join(self.working_dir, 'sites/default')
        super(InstallTools, self).setup_settings_file(site_dir)

    def setup_permissions(self):
        super(InstallTools, self).setup_permissions(handler='install')

    def push_to_repo(self):
        super(InstallTools, self).push_to_repo(tag='initialization')

    def cleanup(self):
        """ Remove working directory.

        """
        local('rm -rf %s' % self.working_dir)

    def build_makefile(self, makefile):
        """ Setup Drupal site using drush make
        makefile: full path to drush makefile

        """
        tempdir = tempfile.mkdtemp()
        local('rm -rf %s' % tempdir)
        local("drush make %s %s" % (makefile, tempdir))
        local('rm -rf %s/*' % self.working_dir)
        local('rsync -av %s/* %s' % (tempdir, self.working_dir))
        with cd(self.working_dir):
            local('git add -A .')
            local("git commit --author=\"%s\" -m 'Site from makefile'" % self.author)
        local('rm -rf %s' % tempdir)


########NEW FILE########
__FILENAME__ = jenkinstools
import os
from lxml import etree

class Junit():
    def __init__(self, suitename, casename):
        self.suitename = suitename.capitalize()
        self.casename = "test%s" % casename.capitalize()
        self.workspace = get_workspace()

    def success(self, msg):
        """ Create a junit file for a passed test
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        case.text = '\n'.join([case.text, msg]) if case.text else msg
        self._write_junit_file(suites)

    def fail(self, msg):
        """ Create a junit file for a failed test
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        fail = self._get_fail(case)
        fail.text = '\n'.join([fail.text, msg]) if fail.text else msg
        self._write_junit_file(suites)

    def error(self, msg):
        """ Create a junit file for a error
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        error = self._get_error(case)
        error.text = '\n'.join([error.text, msg]) if error.text else msg
        self._write_junit_file(suites)

    def _get_fail(self, case):
        fail = case.find("failure")
        if fail is None:
            return etree.SubElement(case, "failure")
        return fail

    def _get_error(self, case):
        error = case.find("error")
        if error is None:
            return etree.SubElement(case, "error")
        return error

    def _get_suite(self, suites):
        suite = suites.find("testsuite[@name='%s']" % self.suitename)
        if suite is None:
            return etree.SubElement(suites, "testsuite", name=self.suitename)
        return suite

    def _get_case(self, suite):
        case = suite.find("testcase[@name='%s']" % self.casename)
        if case is None:
            return etree.SubElement(suite, "testcase", name=self.casename)
        return case

    def _base_xml(self):
        """ Creates the base xml doc structure
            suitename: Name used for the testsuite.
        """
        try:
            f = open(os.path.join(self.workspace, "results.xml"), 'r')
        except:
            doc = etree.Element("testsuites")
            return doc
        else:
            doc = etree.parse(f)
            f.close()
            return doc.getroot()

    def _write_junit_file(self, doc):
        """ Write a new junit file
            doc: The Element Tree object to write to a file
        """
        doc = etree.ElementTree(doc)
        with open(os.path.join(self.workspace, "results.xml"), 'w') as f:
            doc.write(f, encoding='UTF-8', xml_declaration=True, 
                      pretty_print=True)

def get_workspace():
    """Return the workspace to store build data information.

    If being run from CLI (not jenkins) use alternate path (so data can still
    be sent back to Atlas, regardless of how job is run).

    """
    workspace = os.environ.get('WORKSPACE')
    if workspace:
        return workspace
    else:
        return '/etc/pantheon/jenkins/workspace'

########NEW FILE########
__FILENAME__ = logger
import logging
import logging.handlers
import logging.config
import ygg
import os
import ConfigParser
import jenkinstools

log = logging.getLogger("pantheon.logger")
certificate = '/etc/pantheon/system.pem'

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class ServiceHandler(logging.Handler):
    def emit(self, record):
        service = record.name.split('.')[-1]
        status_file = '/etc/pantheon/services.status'
        status = ''

        if record.levelname in ['ERROR']:
            status = 'ERR'
        if record.levelname in ['WARNING']:
            status = 'WARN'
        if record.levelname in ['INFO']:
            status = 'OK'

        cfg = ConfigParser.ConfigParser()
        try:
            cfg.readfp(open(status_file))
        except IOError as (errno, strerror):
            if errno == 2:
                log.debug('Status file not found. Writing to new file.')
            elif errno == 111:
                log.debug('Socket error: Connection refused.')
            else:
                log.exception('Uncaught exception in logging handler. {0}: {0}'.format(errno, strerror))
        except:
            log.exception('Uncaught exception in logging handler.')

        if not cfg.has_section(service):
            cfg.add_section(service)
        if not cfg.has_option(service, 'status'):
            saved_status = None
        else:
            saved_status = cfg.get(service, 'status')

        if status != saved_status:
            cfg.set(service, 'status', status)
            # Write configuration to file
            with open(status_file, 'wb') as cf:
                cfg.write(cf)
            send = {"status": status,
                    "message": record.msg,
                    "type" : record.levelname,
                    "timestamp": record.created}
            if os.path.isfile(certificate):
                # Set service status in ygg
                ygg.set_service(service, send)

class EventHandler(logging.Handler):
    def emit(self, record):
        if os.path.isfile(certificate):
            source = record.name.split('.')[0]
            # Check for task_id to determine if were running a jenkins job.
            thread = os.environ.get('task_id')
            if thread is None:
                thread = record.thread

            details = {"message": record.msg,
                       "type" : record.levelname,
                       "timestamp": record.created}
            labels = ['source-%s' % source, 'inbox', 'all']
            if hasattr(record, 'labels'):
                labels = list(set(labels).union(set(record.labels)))
            if hasattr(record, 'project'):
                details['project'] = record.project
            if hasattr(record, 'environment'):
                details['environment'] = record.environment
            if hasattr(record, 'command'):
                details['command'] = record.command
            if hasattr(record, 'job_complete'):
                details['job_complete'] = record.job_complete
            ygg.send_event(thread, details, labels, source=source)
        else:
            pass

class JunitHandler(logging.Handler):
    def emit(self, record):
        # Check for WORKSPACE to determine if were running a jenkins job.
        workspace = os.environ.get('WORKSPACE')
        if workspace is not None:
            suitename = record.name.split('.')[-1].capitalize()
            casename = record.funcName.capitalize()
            results = jenkinstools.Junit(suitename, casename)
            if record.levelname in ['ERROR', 'CRITICAL']:
                results.error(record.msg)
            if record.levelname in ['WARNING']:
                results.fail(record.msg)
            if record.levelname in ['INFO']:
                results.success(record.msg)
        else:
            pass

# register our custom handlers so they can be used by the config file
logging.handlers.ServiceHandler = ServiceHandler
logging.handlers.EventHandler = EventHandler
logging.handlers.JunitHandler = JunitHandler
logging.handlers.NullHandler = NullHandler

try:
    with open('/opt/pantheon/fab/pantheon/logging.conf', 'r') as f:
        logging.config.fileConfig(f)
except IOError:
    pass

########NEW FILE########
__FILENAME__ = onramp
import os
import tempfile

import dbtools
import drupaltools
import pantheon
import project
import postback
import logger

from fabric.api import *
#TODO: Improve the logging messages

def get_drupal_root(base):
    """Return the location of drupal root within 'base' dir tree.

    """
    log = logger.logging.getLogger('pantheon.onramp.drupalroot')
    for root, dirs, files in os.walk(base, topdown=True):
        if ('index.php' in files) and ('sites' in dirs):
            log.info('Drupal root found.')
            return root
    log.error('Cannot locate drupal install in archive.')
    postback.build_error('Cannot locate drupal install in archive.')

def download(url):
    if url.startswith('file:///'):
        # Local file - return path
        return url[7:]
    else:
        # Download remote file into temp location with known prefix.
        return pantheon.download(url, 'tmp_dl_')

def extract(tarball):
    """ tarball: full path to archive to extract."""

    # Extract the archive
    archive = pantheon.PantheonArchive(tarball)
    extract_location = archive.extract()
    archive.close()

    # In the case of very large sites, people will manually upload the
    # tarball to the machine. In these cases, we don't want to remove this
    # file. However if the import script downloaded the file from a remote
    # location, go ahead and remove it at the end of processing.
    archive_location = os.path.dirname(tarball)
    # Downloaded by import script (known location), remove after extract.
    if archive_location.startswith('/tmp/tmp_dl_'):
        local('rm -rf %s' % archive_location)

    return extract_location

def get_onramp_profile(base):
    """Determine what onramp profile to use (import or restore)

    """
    #TODO: make this more efficient. Could walk through a huge import.
    for root, dirs, files in os.walk(base, topdown=True):
        if ('pantheon.backup' in files) and ('live' in dirs):
            # Restore if a backup config file and a live folder exists.
            return 'restore'
    # Otherwise run the import profile.
    return 'import'


class ImportTools(project.BuildTools):

    def __init__(self, project):
        """Inherit install.InstallTools and initialize. Create addtional
        processing directory for import process.

        """
        self.log = logger.logging.getLogger('pantheon.onramp.ImportTools')
        super(ImportTools, self).__init__()

        self.author = 'Jenkins User <jenkins@pantheon>'
        self.destination = os.path.join(self.server.webroot, self.project)
        self.force_update = False

    def parse_archive(self, extract_location):
        """Get the site name and database dump file from archive to be imported.

        """
        # Find the Drupal installation and set it as the working_dir
        self.working_dir = get_drupal_root(extract_location)

        # Remove existing VCS files.
        with cd(self.working_dir):
            with settings(hide('warnings'), warn_only=True):
                local("find . -depth -name '._*' -exec rm -fr {} \;")
                local("find . -depth -name .git -exec rm -fr {} \;")
                local("find . -depth -name .bzr -exec rm -fr {} \;")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")
                # Comment any RewriteBase directives in .htaccess
                local("sed -i 's/^[^#]*RewriteBase/# RewriteBase/' .htaccess")

        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()
        self.version = int(drupaltools.get_drupal_version(self.working_dir)[0])

    def setup_database(self):
        """ Create a new database and import from dumpfile.

        """
        for env in self.environments:
            (db_username, db_password, db_name) = pantheon.get_database_vars(self, env)
            # The database is only imported into the dev environment initially
            # so that we can do all import processing in one place, then deploy
            # to the other environments.
            if env == 'dev':
                db_dump = os.path.join(self.working_dir, self.db_dump)
            else:
                db_dump = None

            super(ImportTools, self).setup_database(env,
                                                    db_password,
                                                    db_dump,
                                                    True)
        # Remove the database dump from processing dir after import.
        local('rm -f %s' % (os.path.join(self.working_dir, self.db_dump)))

    def import_site_files(self):
        """Create git branch of project at same revision and platform of
        imported site. Import files into this branch and setup default site.

        """
        # Get git metadata at correct branch/version point.
        temp_dir = tempfile.mkdtemp()
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              temp_dir))
        # Put the .git metadata on top of imported site.
        with cd(temp_dir):
            local('git checkout %s' % self.project)
            local('cp -R .git %s' % self.working_dir)
        with cd(self.working_dir):
            local('rm -f PRESSFLOW.txt')
            # Stomp on any changes to core.
            local('git reset --hard')
        local('rm -rf %s' % temp_dir)

        source = os.path.join(self.working_dir, 'sites/%s' % self.site)
        destination = os.path.join(self.working_dir, 'sites/default')

        # Move sites/site_dir to sites/default
        if self.site != 'default':
            if os.path.exists(destination):
                local('rm -rf %s' % destination)
            local('mv %s %s' % (source, destination))
            # Symlink site_dir to default
            with cd(os.path.join(self.working_dir,'sites')):
                local('ln -s %s %s' % ('default', self.site))

    def setup_files_dir(self):
        """Move site files to sites/default/files if they are not already.

        This will move the files from their former location, change the file
        path in the database (for all files and the variable itself), then
        create a symlink in their former location.

        """
        file_location = self._get_files_dir()
        if file_location:
            file_path = os.path.join(self.working_dir, file_location)
        else:
            file_path = None
        file_dest = os.path.join(self.working_dir, 'sites/default/files')

        # After moving site to 'default', does 'files' not exist?
        if not os.path.exists(file_dest):
            # Broken symlink at sites/default/files
            if os.path.islink(file_dest):
                local('rm -f %s' % file_dest)
                msg = 'File path was broken symlink. Site files may be missing'
                self.log.info(msg)
                postback.build_warning(msg)
            local('mkdir -p %s' % file_dest)

        # if files are not located in default location, move them there.
        if (file_path) and (file_location != 'sites/%s/files' % self.site):
            with settings(warn_only=True):
                local('cp -R %s/* %s' % (file_path, file_dest))
            local('rm -rf %s' % file_path)
            path = os.path.split(file_path)
            # Symlink from former location to sites/default/files
            if not os.path.islink(path[0]):
                # If parent folder for files path doesn't exist, create it.
                if not os.path.exists(path[0]):
                    local('mkdir -p %s' % path[0])
                rel_path = os.path.relpath(file_dest, path[0])
                local('ln -s %s %s' % (rel_path, file_path))

        # Change paths in the files table
        (db_username, db_password, db_name) = pantheon.get_database_vars(self, 'dev')

        if self.version == 6:
            file_var = 'file_directory_path'
            file_var_temp = 'file_directory_temp'
            # Change the base path in files table for Drupal 6
            local('mysql -u root %s -e "UPDATE files SET filepath = \
                   REPLACE(filepath,\'%s\',\'%s\');"'% (db_name,
                                                        file_location,
                                                        'sites/default/files'))
        elif self.version == 7:
            file_var = 'file_public_path'
            file_var_temp = 'file_temporary_path'

        # Change file path drupal variables
        db = dbtools.MySQLConn(database = db_name,
                               username = db_username,
                               password = db_password)
        db.vset(file_var, 'sites/default/files')
        db.vset(file_var_temp, '/tmp')
        db.close()

        # Ignore files directory
        with open(os.path.join(file_dest,'.gitignore'), 'a') as f:
            f.write('*\n')
            f.write('!.gitignore\n')

    def enable_pantheon_settings(self):
        """Enable required modules, and set Pantheon defaults.

        """
        if self.version == 6:
            required_modules = ['apachesolr',
                                'apachesolr_search',
                                'locale',
                                'pantheon_api',
                                'pantheon_login',
                                'syslog',
                                'varnish']
        elif self.version == 7:
            required_modules = ['apachesolr',
                                'apachesolr_search',
                                'syslog',
                                'pantheon_api',
                                'pantheon_login',
                                'pantheon_apachesolr']

        # Enable modules.
        with settings(hide('warnings'), warn_only=True):
            for module in required_modules:
                result = local('drush -by @working_dir en %s' % module)
                pantheon.log_drush_backend(result, self.log)
                if result.failed:
                    # If importing vanilla drupal, this module wont exist.
                    if module != 'cookie_cache_bypass':
                        message = 'Could not enable %s module.' % module
                        self.log.warning('%s\n%s' % (message, result.stderr))
                        postback.build_warning(message)
                        print message
                        print '\n%s module could not be enabled. ' % module + \
                              'Error Message:'
                        print '\n%s' % result.stderr
                else:
                    self.log.info('%s enabled.' % module)

        if self.version == 6:
            drupal_vars = {
                'apachesolr_search_make_default': 1,
                'apachesolr_search_spellcheck': 1,
                'cache': '3',
                'block_cache': '1',
                'page_cache_max_age': '900',
                'page_compression': '0',
                'preprocess_js': '1',
                'preprocess_css': '1'}

        elif self.version == 7:
            drupal_vars = {
                'cache': 1,
                'block_cache': 1,
                'cache_lifetime': "0",
                'page_cache_maximum_age': "900",
                'page_compression': 0,
                'preprocess_css': 1,
                'preprocess_js': 1,
                'search_active_modules': {
                    'apachesolr_search':'apachesolr_search',
                    'user': 'user',
                    'node': 0},
                'search_default_module': 'apachesolr_search'}

        # Set variables.
        (db_username, db_password, db_name) = pantheon.get_database_vars(self, 'dev')
        db = dbtools.MySQLConn(database = db_name,
                               username = db_username,
                               password = db_password)
        for key, value in drupal_vars.iteritems():
            db.vset(key, value)

        # apachesolr module for drupal 7 stores config in db.
        # TODO: use drush/drupal api to do this work.
        try:
            if self.version == 7:
                db.execute('TRUNCATE apachesolr_environment')
                for env in self.environments:
                    config = self.config['environments'][env]['solr']

                    env_id = '%s_%s' % (self.project, env)
                    name = '%s %s' % (self.project, env)
                    url = 'http://%s:%s%s' % (config['solr_host'],
                                              config['solr_port'],
                                              config['solr_path'])

                    # Populate the solr environments
                    db.execute('INSERT INTO apachesolr_environment ' + \
                        '(env_id, name, url) VALUES ' + \
                        '("%s", "%s", "%s")' % (env_id, name, url))

                    # Populate the solr environment variables
                    db.execute('INSERT INTO apachesolr_environment_variable '+\
                               '(env_id, name, value) VALUES ' + \
                               "('%s','apachesolr_read_only','s:1:\"0\"')" % (
                                                                      env_id))
        except Exception as mysql_error:
             self.log.error('Auto-configuration of ApacheSolr module failed: %s' % mysql_error)
             pass

        db.close()

        # D7: apachesolr config link will not display until cache cleared?
        with settings(warn_only=True):
            result = local('drush @working_dir -y cc all')
            pantheon.log_drush_backend(result, self.log)

        # Run updatedb
        drupaltools.updatedb(alias='@working_dir')

        # Remove temporary working_dir drush alias.
        alias_file = '/opt/drush/aliases/working_dir.alias.drushrc.php'
        if os.path.exists(alias_file):
            local('rm -f %s' % alias_file)

    def setup_settings_file(self):
        site_dir = os.path.join(self.working_dir, 'sites/default')
        super(ImportTools, self).setup_settings_file(site_dir)

    def setup_drush_alias(self):
        super(ImportTools, self).setup_drush_alias()

        # Create a temporary drush alias for the working_dir.
        # It will be removed after enable_pantheon_settings() finishes.
        lines = ["<?php",
                 "$_SERVER['db_name'] = '%s_%s';" % (self.project, 'dev'),
                 "$_SERVER['db_username'] = '%s';" % self.project,
                 "$_SERVER['db_password'] = '%s';" % self.db_password,
                 "$options['uri'] = 'default';",
                 "$options['root'] = '%s';" % self.working_dir]

        with open('/opt/drush/aliases/working_dir.alias.drushrc.php', 'w') as f:
            for line in lines:
                f.write(line + '\n')

    def setup_environments(self):
        super(ImportTools, self).setup_environments('import', self.working_dir)

    def setup_permissions(self):
        super(ImportTools, self).setup_permissions('import')

    def push_to_repo(self):
        super(ImportTools, self).push_to_repo('import')

    def cleanup(self):
        """ Remove leftover temporary import files..

        """
        local('rm -rf %s' % self.working_dir)
        local('rm -rf %s' % self.build_location)

    def _get_site_name(self):
        """Return the name of the site to be imported.

        A valid site is any directory under sites/ that contains a settings.php

        """
        root = os.path.join(self.working_dir, 'sites')
        sites =[s for s in os.listdir(root) \
                        if os.path.isdir(os.path.join(root,s)) and (
                           'settings.php' in os.listdir(os.path.join(root,s)))]

        # Unless only one site is found, post error and exit.
        site_count = len(sites)
        if site_count > 1:
            err = 'Multiple settings.php files were found:\n' + \
                  '\n'.join(sites)
            self.log.error(err)
            postback.build_error(err)
        elif site_count == 0:
            err = 'Error: No settings.php files were found.'
            self.log.error(err)
            postback.build_error(err)
        else:
            self.log.info('Site found.')
            return sites[0]

    def _get_database_dump(self):
        """Return the filename of the database dump.

        This will look for *.mysql or *.sql files in the root drupal directory.
        If more than one dump is found, the build will exit with an error.

        """
        sql_dump = [dump for dump in os.listdir(self.working_dir) \
                    if os.path.splitext(dump)[1] in ['.sql', '.mysql']]
        count = len(sql_dump)
        if count == 0:
            err = 'No database dump files were found (*.mysql or *.sql)'
            self.log.error(err)
            postback.build_error(err)
        elif count > 1:
            err = 'Multiple database dump files were found:\n' + \
                  '\n'.join(sql_dump)
            self.log.error(err)
            postback.build_error(err)
        else:
            self.log.info('MYSQL Dump found at %s' % sql_dump[0])
            return sql_dump[0]

    def _get_files_dir(self, environment='dev'):
        (db_username, db_password, db_name) = pantheon.get_database_vars(self, environment)
        # Get file_directory_path directly from database, as we don't have a working drush yet.
        return local("mysql -u %s -p'%s' %s --skip-column-names --batch -e \
                      \"SELECT value FROM variable WHERE name='file_directory_path';\" | \
                        sed 's/^.*\"\(.*\)\".*$/\\1/'" % (db_username,
                                                          db_password,
                                                          db_name)).rstrip('\n')


########NEW FILE########
__FILENAME__ = pantheon
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import random
import string
import tarfile
import tempfile
import time
import urllib2
import zipfile
import json
import re
import logger

import postback

from fabric.api import *

ENVIRONMENTS = set(['dev','test','live'])
TEMPLATE_DIR = '/opt/pantheon/fab/templates'

def get_environments():
    """ Return list of development environments.

    """
    return ENVIRONMENTS

def get_template(template):
    """Return full path to template file.
    template: template file name

    """
    return os.path.join(get_template_dir(), template)

def get_template_dir():
    """Return template directory.

    """
    return TEMPLATE_DIR

def copy_template(template, destination):
    """Copy template to destination.
    template: template file name
    destination: full path to destination

    """
    local('cp %s %s' % (get_template(template),
                        destination))

def build_template(template_file, values):
    """Return a template object of the template_file with substitued values.
    template_file: full path to template file
    values: dictionary of values to be substituted in template file

    """
    contents = local('cat %s' % template_file)
    template = string.Template(contents)
    template = template.safe_substitute(values)
    return template

def random_string(length):
    """ Create random string of ascii letters & digits.
    length: Int. Character length of string to return.

    """
    return ''.join(['%s' % random.choice (string.ascii_letters + \
                                          string.digits) \
                                          for i in range(length)])
def parse_vhost(path):
    """Helper method that returns environment variables from a vhost file.
    path: full path to vhost file.
    returns: dict of all vhost SetEnv variables.

    """
    env_vars = dict()
    with open(path, 'r') as f:
       vhost = f.readlines()
    for line in vhost:
        line = line.strip()
        if line.find('SetEnv') != -1:
            var = line.split()
            env_vars[var[1]] = var[2]
    return env_vars

def is_drupal_installed(self, environment):
    """Return True if the Drupal installation process has been completed.
       project: project name
       environment: environment name.

    """
    (username, password, db_name) = get_database_vars(self, environment)
    with hide('running'):
        status = local("mysql -u %s -p%s %s -e 'show tables;' | \
                        awk '/system/'" % (username, password, db_name))
    # If any data is in status, assume site is installed.
    return bool(status)

def download(url, prefix='tmp'):
    """Download url to temporary directory and return path to file.
    url: fully qualified url of file to download.
    prefix: optional prefix to use for the temporary directory name.
    returns: full path to downloaded file.

    """
    download_dir = tempfile.mkdtemp(prefix=prefix)
    filebase = os.path.basename(url)
    filename = os.path.join(download_dir, filebase)

    curl(url, filename)
    return filename

def curl(url, destination):
    """Use curl to save url to destination.
    url: url to download
    destination: full path/ filename to save curl output.

    """
    local('curl "%s" -o "%s"' % (url, destination))

def jenkins_running():
    """Check if jenkins is running. Returns True if http code == 200.

    """
    try:
        result = urllib2.urlopen('http://127.0.0.1:8090').code
    except:
        return False
    return result == 200

def jenkins_queued():
    """Returns number of jobs Jenkins currently has in its queue. -1 if unknown.

    """
    try:
        result = urllib2.urlopen('http://127.0.0.1:8090/queue/api/python')
    except:
        return -1
    if result.code != 200:
        return -1
    return len(eval(result.read()).get('items'))

def get_database_vars(self, env):
    """Helper method that returns database variables for a project/environment.
    project: project name
    environment: environment name.
    returns: Tuple: (username, password, db_name)

    """
    config = self.config['environments'][env]['mysql']
    return (config['db_username'],
            config['db_password'],
            config['db_name'])

def configure_root_certificate(pki_server):
    """Helper function that connects to pki.getpantheon.com and configures the
    root certificate used throughout the infrastructure."""

    # Download and install the root CA.
    local('curl %s | sudo tee /usr/share/ca-certificates/pantheon.crt' % pki_server)
    local('echo "pantheon.crt" | sudo tee -a /etc/ca-certificates.conf')
    #local('cat /etc/ca-certificates.conf | sort | uniq | sudo tee /etc/ca-certificates.conf') # Remove duplicates.
    local('sudo update-ca-certificates')

def jenkins_restart():
    local('curl -X POST http://localhost:8090/safeRestart')

def jenkins_quiet():
    urllib2.urlopen('http://localhost:8090/quietDown')

def parse_drush_backend(drush_backend):
    """ Return drush backend json as a dictionary.
    drush_backend: drush backend json output.
    """
    # Create the patern
    pattern = re.compile('DRUSH_BACKEND_OUTPUT_START>>>%s<<<DRUSH_BACKEND_OUTPUT_END' % '(.*)')

    # Match the patern, returning None if not found.
    match = pattern.match(drush_backend)

    if match:
        return json.loads(match.group(1))

    return None

def log_drush_backend(data, log=None, context={}):
    """ Iterate through the log messages and handle them appropriately
    data: drush backend json output.
    log: object. the logger object to use for logging.
    context: a dict containing the project and environment
    """
    if not log:
        log = logger.logging.getLogger('pantheon.pantheon.drush')

    # Drush outputs the drupal root and the command being run in its logs
    # unforunately they are buried in log messages.
    data = parse_drush_backend(data)
    if (data == None) or (data['error_status'] == 1):
        log.error('Drush command could not be completed successfully.')
        log.debug(str(data))
        return None
    if 'command' not in context:
        p1 = re.compile('Found command: %s \(commandfile' % '(.*)')
    no_dupe = set()
    for entry in data['log']:
        # message is already used by a records namespace
        if type(entry['message']) == dict:
            context['drush_message'] = entry['message']['0']
        else:
            context['drush_message'] = entry['message']
        del entry['message']
        if 'command' not in context:
            m = p1.match(context['drush_message'])
            if m:
                context['command'] = m.group(1)
        if ('command' in context) and (context['drush_message'] not in no_dupe):
            context = dict(context, **entry)

            if context['type'] in ('error', 'critical', 'failure', 'fatal'):
                log.error(context['drush_message'], extra=context)
            elif context['type'] in ('warning'):
                log.warning(context['drush_message'], extra=context)
            elif context['type'] in ('ok', 'success'):
                log.info(context['drush_message'], extra=context)
            else:
                log.debug(context['drush_message'], extra=context)
        no_dupe.add(context['drush_message'])

#TODO: Add more logging for better coverage
class PantheonServer:

    def __init__(self):
        # Ubuntu / Debian
        if os.path.exists('/etc/debian_version'):
            self.distro = 'ubuntu'
            self.mysql = 'mysql'
            self.owner = 'root'
            self.web_group = 'www-data'
            self.jenkins_group = 'nogroup'
            self.tomcat_owner = 'tomcat6'
            self.tomcat_version = '6'
            self.webroot = '/var/www/'
            self.ftproot = '/srv/ftp/pantheon/'
            self.vhost_dir = '/etc/apache2/sites-available/'
        # Centos
        elif os.path.exists('/etc/redhat-release'):
            self.distro = 'centos'
            self.mysql = 'mysqld'
            self.owner = 'root'
            self.web_group = 'apache'
            self.jenkins_group = 'jenkins'
            self.tomcat_owner = 'tomcat'
            self.tomcat_version = '5'
            self.webroot = '/var/www/html/'
            self.ftproot = '/var/ftp/pantheon/'
            self.vhost_dir = '/etc/httpd/conf/vhosts/'
        #global
        self.template_dir = get_template_dir()

    def get_hostname(self):
        return local('hostname').rstrip('\n')

    def update_packages(self):
        if (self.distro == "centos"):
            local('yum clean all', capture=False)
            local('yum -y update', capture=False)
        else:
            local('apt-get -y update', capture=False)
            local('apt-get -y --force-yes dist-upgrade', capture=False)

    def restart_services(self):
        if self.distro == 'ubuntu':
            local('/etc/init.d/apache2 restart')
            local('/etc/init.d/memcached restart')
            with settings(warn_only=True):
                local('/bin/bash -x /etc/init.d/tomcat6 stop', capture=False)
                local('/bin/bash -x /etc/init.d/tomcat6 start', capture=False)
            local('/etc/init.d/varnish restart')
            local('/etc/init.d/mysql restart')
        elif self.distro == 'centos':
            local('/etc/init.d/httpd restart')
            local('/etc/init.d/memcached restart')
            local('/etc/init.d/tomcat5 restart')
            local('/etc/init.d/varnish restart')
            local('/etc/init.d/mysqld restart')

    def setup_iptables(self, file):
        local('/sbin/iptables-restore < ' + file)
        local('/sbin/iptables-save > /etc/iptables.rules')

    def create_drush_alias(self, drush_dict):
        """ Create an alias.drushrc.php file.
        drush_dict: project:
                    environment:
                    root: full path to drupal installation

        """
        alias_template = get_template('drush.alias.drushrc.php')
        alias_file = '/opt/drush/aliases/%s_%s.alias.drushrc.php' % (
                                            drush_dict.get('project'),
                                            drush_dict.get('environment'))
        template = build_template(alias_template, drush_dict)
        with open(alias_file, 'w') as f:
            f.write(template)

    def create_solr_index(self, project, environment, version):
        """ Create solr index in: /var/solr/project/environment.
        project: project name
        environment: development environment
        version: major drupal version

        """

        # Create project directory
        project_dir = '/var/solr/%s/' % project
        if not os.path.exists(project_dir):
            local('mkdir %s' % project_dir)
        local('chown %s:%s %s' % (self.tomcat_owner,
                                  self.tomcat_owner,
                                  project_dir))

        # Create data directory from sample solr data.
        data_dir = os.path.join(project_dir, environment)
        if os.path.exists(data_dir):
            local('rm -rf ' + data_dir)
        data_dir_template = os.path.join(get_template_dir(),
                                         'solr%s' % version)
        local('cp -R %s %s' % (data_dir_template, data_dir))
        local('chown -R %s:%s %s' % (self.tomcat_owner,
                                     self.tomcat_owner,
                                     data_dir))

        # Tell Tomcat where indexes are located.
        tomcat_template = get_template('tomcat_solr_home.xml')
        values = {'solr_path': '%s/%s' % (project, environment)}
        template = build_template(tomcat_template, values)
        tomcat_file = "/etc/tomcat%s/Catalina/localhost/%s_%s.xml" % (
                                                      self.tomcat_version,
                                                      project,
                                                      environment)
        with open(tomcat_file, 'w') as f:
            f.write(template)
        local('chown %s:%s %s' % (self.tomcat_owner,
                                  self.tomcat_owner,
                                  tomcat_file))


    def create_drupal_cron(self, project, environment):
        """ Create Jenkins drupal cron job.
        project: project name
        environment: development environment

        """
        # Create job directory
        jobdir = '/var/lib/jenkins/jobs/cron_%s_%s/' % (project, environment)
        if not os.path.exists(jobdir):
            local('mkdir -p ' + jobdir)

        # Create job from template
        values = {'drush_alias':'@%s_%s' % (project, environment)}
        cron_template = get_template('jenkins.drupal.cron')
        template = build_template(cron_template, values)
        with open(jobdir + 'config.xml', 'w') as f:
            f.write(template)

        # Set Perms
        local('chown -R %s:%s %s' % ('jenkins', self.jenkins_group, jobdir))


    def get_vhost_file(self, project, environment):
        """Helper method that returns the full path to the vhost file for a
        particular project/environment.
        project: project name
        environment: environment name.

        """
        filename = '%s_%s' % (project, environment)
        if environment == 'live':
            filename = '000_' + filename
        if self.distro == 'ubuntu':
            return '/etc/apache2/sites-available/%s' % filename
        elif self.distro == 'centos':
            return '/etc/httpd/conf/vhosts/%s' % filename

    def get_ldap_group(self):
        """Helper method to pull the ldap group we authorize.
        Helpful in keeping filesystem permissions correct.

        /etc/pantheon/ldapgroup is written as part of the configure_ldap job.

        """
        with open('/etc/pantheon/ldapgroup', 'r') as f:
            return f.readline().rstrip("\n")

    def set_ldap_group(self, require_group):
        """Helper method to pull the ldap group we authorize.
        Helpful in keeping filesystem permissions correct.

        /etc/pantheon/ldapgroup is written as part of the configure_ldap job.

        """
        with open('/etc/pantheon/ldapgroup', 'w') as f:
            f.write('%s' % require_group)

#TODO: Add more logging for better coverage
class PantheonArchive(object):
    def __init__(self, path):
        self.log = logger.logging.getLogger('pantheon.pantheon.PantheonArchive')
        self.path = path
        self.filetype = self._get_archive_type()
        self.archive = self._open_archive()

    def extract(self):
        """Extract a tar/tar.gz/zip archive into a temporary directory.

        """
        destination = tempfile.mkdtemp()
        self.archive.extractall(destination)
        return destination

    def close(self):
        """Close the archive file object.

        """
        self.archive.close()

    def _get_archive_type(self):
        """Return the generic type of archive (tar/zip).

        """
        if tarfile.is_tarfile(self.path):
            self.log.info('Tar archive found.')
            return 'tar'
        elif zipfile.is_zipfile(self.path):
            self.log.info('Zip archive found.')
            return 'zip'
        else:
            err = 'Error: Not a valid tar/zip archive.'
            self.log.error(err)
            postback.build_error(err)

    def _open_archive(self):
        """Return an opened archive file object.

        """
        if self.filetype == 'tar':
            return tarfile.open(self.path, 'r')
        elif self.filetype == 'zip':
            return zipfile.ZipFile(self.path, 'r')


########NEW FILE########
__FILENAME__ = postback
import cPickle
import httplib
import json
import os
import sys
import urllib2
import uuid
import jenkinstools

from fabric.api import local

def postback(cargo, command='atlas'):
    """Send data back to Atlas.
    cargo: dict of data to send.
    task_id: uuid of requesting job.
    command: Prometheus command.

    """
    print "DEBUG: postback.postback"
    try:
        task_id = cargo.get('build_parameters').get('task_id')
    except Exception:
        task_id = None

    return _send_response({'id': str(uuid.uuid4()),
                           'command':command,
                           'method':'POST',
                           'response': cargo,
                           'response_to': {'task_id': task_id}})

def get_job_and_id():
    """Return the job name and build number.
    These are set (and retrieved) as environmental variables during Jenkins jobs.

    """
    print "DEBUG: postback.get_job_and_id"
    return (os.environ.get('JOB_NAME'), os.environ.get('BUILD_NUMBER'))

def get_build_info(job_name, build_number, check_previous):
    """Return a dictionary of Jenkins build information.
    job_name: jenkins job name.
    build_number: jenkins build number.
    check_previous: bool. If we should return data only if there is a change in
                          build status.

    """
    print "DEBUG: postback.get_build_info"
    data = _get_jenkins_data(job_name, build_number)

    # If we care, determine if status changed from previous run.
    if check_previous and not _status_changed(job_name, data):
        return None

    # Either we dont care if status changed, or there were changes.
    return {'job_name': job_name,
            'build_number': build_number,
            'build_status': data.get('result'),
            'build_parameters': _get_build_parameters(data)}

def get_build_data():
    """ Return a dict of build data, messages, warnings, errors.

    """
    data = dict()
    data['build_messages'] = list()
    data['build_warnings'] = list()
    data['build_error'] = ''

    build_data_path = os.path.join(jenkinstools.get_workspace(), 'build_data.txt')
    if os.path.isfile(build_data_path):
        with open(build_data_path, 'r') as f:
            while True:
                try:
                    # Read a single item from the file, and get response type.
                    var = cPickle.load(f)
                    response_type = var.keys()[0]
                    # If it is a message, add to list of messages.
                    if response_type == 'build_message':
                        data['build_messages'].append(var.get('build_message'))
                    # If it is a warning, add to list of warnings.
                    elif response_type == 'build_warning':
                        data['build_warnings'].append(var.get('build_warning'))
                    # Can only have one error (fatal). 
                    elif response_type == 'build_error':
                        data['build_error'] = var.get('build_error')
                    # General build data. Update data dict.
                    else:
                        data.update(var)
                except (EOFError, ImportError, IndexError):
                    break
    return data

def write_build_data(response_type, data):
    """ Write pickled data to workspace for jenkins job_name.

    response_type: The type of response data (generally a job name). May not
               be the same as the initiating jenkins job (multiple responses).
    data: Info to be written to file for later retrieval in Atlas postback.

    """
    build_data_path = os.path.join(jenkinstools.get_workspace(), 'build_data.txt')

    with open(build_data_path, 'a') as f:
        cPickle.dump({response_type:data}, f)

def build_message(message):
    """Writes messages to file that will be sent back to Atlas,
    message: string. Message to send back to Atlas/user.

    """
    write_build_data('build_message', message)

def build_warning(message):
    """Writes warning to file that will be parsed at the end of a build.
    data: string. Warning message to be written to build_data file.

    Warnings will cause the Jenkins build to be marked as unstable.

    """
    write_build_data('build_warning', message)

def build_error(message):
    """Writes error message to file. Sets build as unstable. Exists Job.
    message: string. Error message that will be written to build_data file.

    """
    write_build_data('build_error', message)
    print "\nEncountered a build error. Error message:"
    print message + '\n\n'
    sys.exit(0)

def _status_changed(job_name, data):
    """Returns True if the build status changed from the previous run.
    Will also return true if there is no previous status.
    job_name: jenkins job name.
    data: dict from jenkinss python api for the current build.

    """
    print "DEBUG: postback._status_changed"
    prev_build_number = int(data.get('number')) - 1
    # Valid previous build exists.
    if prev_build_number > 0:
        result = data.get('result')
        prev_result = _get_jenkins_data(job_name, prev_build_number).get('result')
        return result != prev_result
    else:
        # First run, status has changed from "none" to something.
        return True

def _get_build_parameters(data):
    """Return the build parameters from Jenkins build API data.

    """
    print "DEBUG: postback._get_build_parameters"
    ret = dict()
    parameters = data.get('actions')[0].get('parameters')
    try:
      for param in parameters:
          ret[param['name']] = param['value']
    except Exception:
      print "WARNING: No build parameters found.";

    return ret

def _get_jenkins_data(job, build_id):
    """Return API data for a Jenkins build.

    """
    print "DEBUG: postback._get_jenkins_data"
    try:
        req = urllib2.Request('http://localhost:8090/job/%s/%s/api/python' % (
                                                               job, build_id))
        return eval(urllib2.urlopen(req).read())
    except urllib2.URLError:
        return None

def _send_response(responsedict):
    """POST data to Prometheus.
    responsedict: fully formed dict of response data.

    """
    print "DEBUG: postback._send_response"
    host = 'jobs.getpantheon.com'
    certificate = '/etc/pantheon/system.pem'
    celery = 'atlas.notify'
    headers = {'Content-Type': 'application/json'}

    connection = httplib.HTTPSConnection(host,
                                         key_file = certificate,
                                         cert_file = certificate)

    connection.request('POST', '/%s/' % celery,
                       json.dumps(responsedict),
                       headers)

    response = connection.getresponse()
    return response


########NEW FILE########
__FILENAME__ = project
import os
import tempfile

import dbtools
import drupaltools
import pantheon
import ygg
from vars import *

from fabric.api import *


class BuildTools(object):
    """ Generic Pantheon project installation helper functions.

    This is generally used as a base object, inherited by other project
    building classes (install, import, and restore). The child classes
    can use these methods directly or override/expand base processes.

    """
    def __init__(self):
        """ Initialize generic project installation object & helper functions.
        project: the name of the project to be built.

        """
        config = ygg.get_config()
        self.server = pantheon.PantheonServer()

        self.project = str(config.keys()[0])
        self.config = config[self.project]
        self.environments = set(self.config['environments'].keys())
        self.project_path = os.path.join(self.server.webroot, self.project)
        self.db_password = self.config\
                ['environments']['live']['mysql']['db_password']
        self.version = None

    def bcfg2_project(self):
        local('bcfg2 -vqedb projects', capture=False)

    def remove_project(self):
        """ Remove a project and all related files/configs from the server.

        """
        locations = list()

        # Git repository
        locations.append(os.path.join('/var/git/projects', self.project))
        # Project webroot
        locations.append(self.project_path)

        # TODO: We also need to remove the following:
        # Solr Index
        # Apache vhost
        # Jenkins cron
        # Drush alias
        # Databases

        for location in locations:
            if os.path.exists(location):
                local('rm -rf %s' % location)

    def setup_project_repo(self, upstream_repo=None):
        """ Create a new project repo, and download pantheon/drupal core.

        """
        project_repo = os.path.join('/var/git/projects', self.project)
        dev_branch = None

        # If this is a development server check MERCURY_BRANCH for source.
        if MERCURY_BRANCH != 'master':
            dev_branch = MERCURY_BRANCH

        # For imports, no upstream is set. But self.version is known.
        if upstream_repo is None:
            # Is this a development branch?
            if dev_branch:
                upstream_repo = 'git://github.com/pantheon-systems/' + \
                                '%s-%s.git' % (self.version, dev_branch)
            else:
                upstream_repo = 'git://git.getpantheon.com/pantheon/%s.git' %(
                                                                 self.version)
        else:
            # If this is a development server, make sure the upstream has
            # not been changed to some other source before modifying. Mostly
            # because we make hackish assumptions about determining version
            # and destination.
            if dev_branch and upstream_repo.startswith(
                                 'git://git.getpantheon.com'):
                self.version = upstream_repo[-5]
                upstream_repo = 'git://github.com/pantheon-systems/' + \
                                '%s-%s.git' % (self.version, dev_branch)

        # Get Pantheon core
        local('git clone --mirror %s %s' % (upstream_repo, project_repo))

        with cd(project_repo):
            # Repo config
            local('git config core.sharedRepository group')
            # Group write.
            local('chmod -R g+w .')

        # post-receive-hook
        post_receive_hook = os.path.join(project_repo,
                                         'hooks/post-receive')
        pantheon.copy_template('git.hook.post-receive', post_receive_hook)
        local('chmod +x %s' % post_receive_hook)

    def setup_project_branch(self):
        """ Create a branch of the project.

        """
        project_repo = os.path.join('/var/git/projects', self.project)
        with cd(project_repo):
            local('git branch %s' % self.project)

    def setup_working_dir(self, working_dir):
        """ Clone a project to a working directory for processing.
        working_dir: temp directory for project processing (import/restore)

        """
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              working_dir))

    def setup_database(self, environment, password, db_dump=None, onramp=False):
        """ Create a new database based on project_environment, using password.
        environment: the environment name (dev/test/live) in which to create db
        password: password to identify user (username is same as project name).
        db_dump (optional): full path to database dump to import into db.
        onramp (optional): bool. perform additional prep during import process.

        """
        username = self.config['environments'][environment]['mysql']['db_username']
        database = self.config['environments'][environment]['mysql']['db_name']
        password = self.config['environments'][environment]['mysql']['db_password']

        dbtools.create_database(database)
        dbtools.set_database_grants(database, username, password)
        if db_dump:
            dbtools.import_db_dump(db_dump, database)
            if onramp:
                dbtools.clear_cache_tables(database)
                dbtools.convert_to_innodb(database)

    def setup_settings_file(self, site_dir):
        """ Setup pantheon.settings.php and settings.php.
        site_dir: path to the site directory. E.g. /var/www/sites/default

        """
        settings_file = os.path.join(site_dir, 'settings.php')
        settings_default = os.path.join(site_dir, 'default.settings.php')
        settings_pantheon = 'pantheon%s.settings.php' % self.version
        os.path.join(self.project_path, settings_pantheon)

        # Stomp on changes to default.settings.php - no need to conflict here.
        local('git --git-dir=/var/git/projects/%s cat-file ' % self.project + \
           'blob refs/heads/master:sites/default/default.settings.php > %s' % (
                                                             settings_default))
        # Make sure settings.php exists.
        if not os.path.isfile(settings_file):
            local('cp %s %s' % (settings_default, settings_file))

        # Comment out $base_url entries.
        local("sed -i 's/^[^#|*]*\$base_url/# $base_url/' %s" % settings_file)

        # Create pantheon.settings.php
        if not os.path.isfile(os.path.join(self.project_path,
                                           settings_pantheon)):
            self.bcfg2_project()

        # Import needs a valid settings file in the tmp directory
        if hasattr(self, 'working_dir'):
            tmp_file_dir = os.path.abspath(os.path.join(self.working_dir, '..'))
            local("cp %s %s" %
                  (os.path.join(self.project_path, settings_pantheon),
                   tmp_file_dir))
            vhost_file = '/etc/apache2/sites-available/%s_dev' % self.project
            local("sed -i -e 's|($vhost_file)|(\"%s\")|' %s/%s" %
                  (vhost_file, tmp_file_dir, settings_pantheon))

        # Include pantheon.settings.php at the end of settings.php
        with open(os.path.join(site_dir, 'settings.php'), 'a') as f:
            f.write("""
/* Added by Pantheon */
if (file_exists('../pantheon%s.settings.php')) {
    include_once '../pantheon%s.settings.php';
}
""" % (self.version, self.version))

    def setup_drush_alias(self):
        """ Create drush aliases for each environment in a project.

        """
        for env in self.environments:
            root = os.path.join(self.server.webroot, self.project, env)
            drush_dict = {'project': self.project,
                          'environment': env,
                          'root': root}
            self.server.create_drush_alias(drush_dict)

    def setup_solr_index(self):
        """ Create solr index for each environment in a project.

        """
        for env in self.environments:
            self.server.create_solr_index(self.project, env, self.version)

    def setup_drupal_cron(self):
        """ Create drupal cron jobs in jenkins for each environment.

        """
        for env in self.environments:
            self.server.create_drupal_cron(self.project, env)

    def setup_environments(self, handler=None, working_dir=None):
        """ Send code/data/files from processing to destination (dev/test/live)
        All import and restore processing is done in temp directories. Once
        processing is complete, it is pushed out to the final destination.

        handler: 'import' or None. If import, complete extra import processing.
        working_dir: If handler is import, also needs full path to working_dir.

        """

        # During import, only run updates/import processes a single database.
        # Once complete, we import this 'final' database into each environment.
        if handler == 'import':
            tempdir = tempfile.mkdtemp()
            dump_file = dbtools.export_data(self, 'dev', tempdir)

        for env in self.environments:
            # Code
            destination = os.path.join(self.project_path, env)
            local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                                 self.project,
                                                                 destination))
            # On import setup environment data and files.
            if handler == 'import':
                # Data (already exists in 'dev' - import into other envs)
                if env != 'dev':
                    dbtools.import_data(self, env, dump_file)

                # Files
                source = os.path.join(working_dir, 'sites/default/files')
                file_dir = os.path.join(self.project_path, env,
                                                'sites/default')
                local('rsync -av %s %s' % (source, file_dir))

        # Cleanup
        if handler == 'import':
            local('rm -rf %s' % tempdir)

    def push_to_repo(self, tag):
        """ Commit changes in working directory and push to central repo.

        """
        with cd(self.working_dir):
            local('git checkout %s' % self.project)
            # Set up .gitignore
            pantheon.copy_template('git.ignore', os.path.join(self.working_dir, '.gitignore'))
            local('git add -A .')
            local("git commit --author=\"%s\" -m 'Initialize Project: %s'" % (
                                                   self.author, self.project))
            local('git tag %s.%s' % (self.project, tag))
            local('git push')
            local('git push --tags')

    def setup_permissions(self, handler, environment=None):
        """ Set permissions on project directory, settings.php, and files dir.

        handler: one of: 'import','restore','update','install'. How the
        permissions are set is determined by the handler.

        environment: In most cases this is left to None, as we will be
        processing all environments using self.environments. However,
        if handler='update' we need to know the specific environment for which
        the update is being run. We do this so we are not forcing permissions
        updates on files that have not changed.

        """
        # Get  owner
        #TODO: Allow non-getpantheon users to set a default user.
        if os.path.exists("/etc/pantheon/ldapgroup"):
            owner = self.server.get_ldap_group()
        else:
            owner = self.server.web_group

        # During code updates, we only make changes in one environment.
        # Otherwise, we are modifying all environments.
        environments = list()
        if handler == 'update':
            #Single environment during update.
            environments.append(environment)
        else:
            #All environments for install/import/restore.
            environments = self.environments


        """
        Project directory and sub files/directories

        """

        # installs / imports / restores.
        if handler in ['install', 'import', 'restore']:
            # setup shared repo config and set gid
            for env in environments:
                with cd(os.path.join(self.server.webroot, self.project, env)):
                    local('git config core.sharedRepository group')
            with cd(self.server.webroot):
                local('chown -R %s:%s %s' % (owner, owner, self.project))


        """
        Files directory and sub files/directories

        """

        # For installs, just set 770 on files dir.
        if handler == 'install':
            for env in environments:
                site_dir = os.path.join(self.project_path,
                                        env,
                                        'sites/default')
                with cd(site_dir):
                    local('chmod 770 files')
                    local('chown %s:%s files' % (self.server.web_group,
                                                 self.server.web_group))

        # For imports or restores: 770 on files dir (and subdirs). 660 on files
        elif handler in ['import', 'restore']:
            for env in environments:
                file_dir = os.path.join(self.project_path, env,
                                        'sites/default/files')
                with cd(file_dir):
                    local("chmod 770 .")
                    # All sub-files
                    local("find . -type d -exec find '{}' -type f \; | \
                           while read FILE; do chmod 660 \"$FILE\"; done")
                    # All sub-directories
                    local("find . -type d -exec find '{}' -type d \; | \
                          while read DIR; do chmod 770 \"$DIR\"; done")
                    # Apache should own files/*
                    local("chown -R %s:%s ." % (self.server.web_group,
                                                self.server.web_group))

        # For updates, set apache as owner of files dir.
        elif handler == 'update':
            site_dir = os.path.join(self.project_path,
                                    environments[0],
                                    'sites/default')
            with cd(site_dir):
                local('chown %s:%s files' % (self.server.web_group,
                                             self.server.web_group))


        """
        settings.php & pantheon.settings.php

        """

        #TODO: We could split this up based on handler, but changing perms on
        # two files is fast. Ignoring for now, and treating all the same.
        for env in environments:
            if pantheon.is_drupal_installed(self, env):
                # Drupal installed, Apache does not need to own settings.php
                settings_perms = '440'
                settings_owner = owner
                settings_group = self.server.web_group
            else:
                # Drupal is NOT installed. Apache must own settings.php
                settings_perms = '660'
                settings_owner = self.server.web_group
                settings_group = self.server.web_group

            site_dir = os.path.join(self.project_path, env, 'sites/default')
            with cd(site_dir):
                # settings.php
                local('chmod %s settings.php' % settings_perms)
                local('chown %s:%s settings.php' % (settings_owner,
                                                    settings_group))
                # TODO: New sites will not have a pantheon.settings.php in their
                # repos. However, existing backups will, and if the settings
                # file exists, we need it to have correct permissions.
                if os.path.exists(os.path.join(site_dir,
                                               'pantheon.settings.php')):
                    local('chmod 440 pantheon.settings.php')
                    local('chown %s:%s pantheon.settings.php' % (owner,
                                                       settings_group))
        if not self.version:
            self.version = drupaltools.get_drupal_version('%s/dev' %
                                                          self.project_path)[0]
        with cd(self.project_path):
            # pantheon.settings.php
            local('chmod 440 pantheon%s.settings.php' % self.version)
            local('chown %s:%s pantheon%s.settings.php' % (owner,
                                                           settings_group,
                                                           self.version))


########NEW FILE########
__FILENAME__ = rangeable_file
import os

class RangeableFileObject():
    """File object wrapper to enable raw range handling.

    This object effectively makes a file object look like it consists only 
    of a range of bytes in the stream.

    """
    
    def __init__(self, fo, rangetup):
        """Create a RangeableFileObject.

        fo       -- a file like object.
        rangetup -- a (firstbyte,lastbyte) tuple specifying the range to 
                    work over.
        The file object provided is assumed to be at byte offset 0.

        """
        fo.seek(0,2)
        self.fsize = fo.tell()
        self.fo = fo
        (self.firstbyte, self.lastbyte) = range_tuple_normalize(rangetup)
        self.realpos = 0
        self._do_seek(self.firstbyte)
        
    def __getattr__(self, name):
        """Any attribute not found in _this_ object will be searched for
        in self.fo.

        name -- name of attribute to search for.
        This includes methods.

        """
        if hasattr(self.fo, name):
            return getattr(self.fo, name)
        raise AttributeError, name

    def read(self, size=None):
        """Read and return within the range.

        size -- the size of the provided range
        This method will limit the size read based on the range.

        """
        size = self._read_size(size) if size else \
               self._read_size(self.__len__())
        rslt = self.fo.read(size)
        self.realpos += len(rslt)
        return rslt

    def _read_size(self, size):
        """Return actual size to be read

        size -- Length of the current range
        Handles calculating the amount of data to read based on the range.

        """
        if self.lastbyte:
            if size > -1:
                if ((self.realpos + size) >= self.lastbyte):
                    size = (self.lastbyte - self.realpos)
            else:
                size = (self.lastbyte - self.realpos)
        return size

    def __len__(self):
        """Returns the length of the given range in bytes"""
        return self.lastbyte - self.firstbyte 

    def _do_seek(self,offset):
        """Seek based on whether wrapped object supports seek().
        offset -- is relative to the current position (self.realpos).
        """
        assert (self.realpos + offset) >= 0
        self.fo.seek(self.realpos + offset)
        self.realpos+= offset

    def tell(self):
        """Return the position within the range.

        This is different from fo.seek in that position 0 is the 
        first byte position of the range tuple. For example, if
        this object was created with a range tuple of (500,899),
        tell() will return 0 when at byte position 500 of the file.

        """
        return (self.realpos - self.firstbyte)

    def seek(self,offset,whence=0):
        """Seek within the byte range.

        offset -- The byte to seek to
        whence -- Switch between relative and absolute seeking (default 0)
        Positioning is identical to that described under tell().

        """
        assert whence in (0, 1, 2)
        if whence == 0:   # absolute seek
            realoffset = self.firstbyte + offset
        elif whence == 1: # relative seek
            realoffset = self.realpos + offset
        elif whence == 2: # absolute from end of file
            realoffset = self.fsize + offset
            # XXX: are we raising the right Error here?
            #raise IOError('seek from end of file not supported.')
        
        # do not allow seek past lastbyte in range
        if self.lastbyte and (realoffset >= self.lastbyte):
            realoffset = self.lastbyte
        
        self._do_seek(realoffset - self.realpos)

def range_tuple_normalize(range_tup):
    """Normalize a (first_byte,last_byte) range tuple.
    Return a tuple whose first element is guaranteed to be an int
    and whose second element will be '' (meaning: the last byte) or 
    an int. Finally, return None if the normalized tuple == (0,'')
    as that is equivelant to retrieving the entire file.
    """
    if range_tup is None: return None
    # handle first byte
    fb = range_tup[0]
    if fb in (None,''): fb = 0
    else: fb = int(fb)
    # handle last byte
    try: lb = range_tup[1]
    except IndexError: lb = ''
    else:  
        if lb is None: lb = ''
        elif lb != '': lb = int(lb)
    # check if range is over the entire file
    if (fb,lb) == (0,''): return None
    # check that the range is valid
    if lb < fb: raise RangeError(9, 'Invalid byte range: %s-%s' % (fb,lb))
    return (fb,lb)

def fbuffer(fpath, chunk_size):
    """ Yield rangeable file object

    Keyword arguements:
    fpath      -- path to the file
    chunk_size -- size of the chunk to buffer
    Generator that yields a rangeable file object of a given chunk_size

    """
    fsize = os.path.getsize(fpath)
    byte = 0
    for i in range(fsize/chunk_size):
        if (fsize > chunk_size):
            rfo = RangeableFileObject(file(fpath), (byte, byte + chunk_size))
            yield rfo
            rfo.close()
            byte += chunk_size
    else:
        rfo = RangeableFileObject(file(fpath), (byte, fsize))
        yield rfo
        rfo.close()

""" Test code
import httplib
import sys
filepath = sys.argv[1]
chunksize = 804
connection = httplib.HTTPConnection(
    'www.postbin.org',
)

for chunk in fbuffer(filepath, chunksize):
    connection.connect()
    connection.request("POST", '/1jskuz1', chunk)
    complete_response = connection.getresponse()
    connection.close()
#    print(chunk.read())
"""


########NEW FILE########
__FILENAME__ = restore
import os
import re

import drupaltools
import project

from fabric.api import local
from fabric.api import cd

class RestoreTools(project.BuildTools):

    def __init__(self, project):
        """ Initialize Restore object. Inherits base methods from BuildTools.

        """
        super(RestoreTools, self).__init__()
        self.destination = os.path.join(self.server.webroot, self.project)

    def parse_backup(self, location):
        """ Get project name from extracted backup.

        """
        self.working_dir = location
        self.backup_project = os.listdir(self.working_dir)[0]
        self.version = drupaltools.get_drupal_version(os.path.join(
                                                          self.working_dir,
                                                          self.backup_project,
                                                          'dev'))[0]

    def setup_database(self):
        """ Restore databases from backup.

        """
        for env in self.environments:
            db_dump = os.path.join(self.working_dir,
                                   self.backup_project,
                                   env,
                                   'database.sql')
            # Create database and import from dumpfile.
            super(RestoreTools, self).setup_database(env,
                                                     self.db_password,
                                                     db_dump,
                                                     False)
            # Cleanup dump file before copying files over.
            local('rm -f %s' % db_dump)

    def restore_site_files(self):
        """ Restore code from backup.

        """
        for env in self.environments:
            if os.path.exists('%s/%s' % (self.destination, env)):
                local('rm -rf %s/%s' % (self.destination, env))
            with cd(os.path.join(self.working_dir, self.backup_project)):
                local('rsync -avz %s %s' % (env, self.destination))
            # It's possible that the backup is from a different project.
            # If so: rename branch, set remote, and set merge refs.
            with cd(os.path.join(self.destination, env)):
                self.old_branch = local('git name-rev --name-only HEAD').strip()
                if self.old_branch != self.project:
                    local('git branch -m %s %s' % (self.old_branch, self.project))
                    local('git remote set-url origin /var/git/projects/%s' % self.project)
                    local('git config branch.%s.remote origin' % self.project)
                    local('git config branch.%s.merge refs/heads/%s' % (self.project, self.project))

    def restore_repository(self):
        """ Restore GIT repo from backup.

        """
        project_repo = os.path.join('/var/git/projects', self.project)
        backup_repo = os.path.join(self.working_dir,
                                   self.backup_project,
                                   '%s.git' % self.backup_project)
        if os.path.exists(project_repo):
            local('rm -rf %s' % project_repo)
        local('rsync -avz %s/ %s/' % (backup_repo, project_repo))
        local('chmod -R g+w %s' % project_repo)

        # Enforce a specific origin remote
        with cd(project_repo):
            # Get version from existing origin. 
            # TODO: One day we can remove this, but this ensures restored sites
            #       will point to the correct origin.
            pattern = re.compile('^origin.*([6,7])\.git.*')
            remotes = local('git remote -v').split('\n')
            for remote in remotes:
                match = pattern.search(remote)
                if match and match.group(1) in ['6', '7']:
                    local('git remote rm origin')
                    local('git remote add --mirror origin ' + \
                          'git://git.getpantheon.com/pantheon/%s.git' % match.group(1))
                    break

            # If restoring into a new project name.    
            if self.old_branch != self.project:
                local('git branch -m %s %s' % (self.old_branch, self.project))

    def setup_permissions(self):
        """ Set permissions on project, and repo using the 'restore' handler.

        """
        super(RestoreTools, self).setup_permissions(handler='restore')

    def cleanup(self):
        """ Remove working_dir.

        """
        local('rm -rf %s' % self.working_dir)


########NEW FILE########
__FILENAME__ = status
import drupaltools
import gittools
import postback
import logger

from fabric.api import *

def git_repo_status(project):
    """Post back to Atlas with the status of the project Repo.

    """
    log = logger.logging.getLogger('pantheon.status.repo')
    log.info('Updating status of the projects repository.')
    try:
        repo = gittools.GitRepo(project)
        status = repo.get_repo_status()
    except:
        log.exception('Repository status update unsuccessful.')
        raise
    else:
        log.info('Project repository status updated.')
        postback.write_build_data('git_repo_status', {'status': status})

def drupal_update_status(project):
    """Return drupal/pantheon update status for each environment.

    """
    log = logger.logging.getLogger('pantheon.status.environments')
    log.info('Updating status of the drupal environments.')
    try:
        status = drupaltools.get_drupal_update_status(project)
    except:
        log.exception('Environments status update unsuccessful.')
        raise
    else:
        log.info('Drupal environment status updated.')
        postback.write_build_data('drupal_core_status', {'status': status})



########NEW FILE########
__FILENAME__ = update
import httplib
import json
import os
import tempfile

import dbtools
import pantheon
import project
import postback
import logger
import drupaltools

from fabric.api import *

class Updater(project.BuildTools):

    def __init__(self, environment=None):
        super(Updater, self).__init__()

        self.log = logger.logging.getLogger('pantheon.update.Updater')
        context = {"project":self.project}
        if environment:
            assert environment in self.environments, \
                   'Environment not found in project: {0}'.format(self.project)
            context['environment'] = environment
            self.update_env = environment
            self.author = 'Jenkins User <jenkins@pantheon>'
            self.env_path = os.path.join(self.project_path, environment)
        self.log = logger.logging.LoggerAdapter(self.log, context)

    def core_update(self, keep=None):
        """Update core in dev environment.

        keep: Option when merge fails:
              'ours': Keep local changes when there are conflicts.
              'theirs': Keep upstream changes when there are conflicts.
              'force': Leave failed merge in working-tree (manual resolve).
              None: Reset to ORIG_HEAD if merge fails.

        """
        self.log.info('Initialized core update.')
        # Update pantheon core master branch
        with cd('/var/git/projects/%s' % self.project):
            local('git fetch origin master')

        # Commit all changes in dev working-tree.
        self.code_commit('Core Update: Automated Commit.')

        with cd(os.path.join(self.project_path, 'dev')):
            with settings(warn_only=True):
                # Merge latest pressflow.
                merge = local('git pull origin master')
                self.log.info(merge)

            # Handle failed merges
            if merge.failed:
                self.log.error('Merge failed.')
                if keep == 'ours':
                    self.log.info('Re-merging - keeping local changes on ' \
                                  'conflict.')
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xours origin master')
                    self.log.info(merge)
                    local('git push')
                elif keep == 'theirs':
                    self.log.info('Re-merging - keeping upstream changes on ' \
                                  'conflict.')
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xtheirs origin ' \
                                  'master')
                    self.log.info(merge)
                    local('git push')
                elif keep == 'force':
                    self.log.info('Leaving merge conflicts. Please manually ' \
                                  'resolve.')
                else:
                    #TODO: How do we want to report this back to user?
                    self.log.info('Rolling back failed changes.')
                    local('git reset --hard ORIG_HEAD')
                    return {'merge':'fail','log':merge}
            # Successful merge.
            else:
                local('git push')
                self.log.info('Merge successful.')
        self.log.info('Core update successful.')
        return {'merge':'success','log':merge}


    def code_update(self, tag, message):
        self.log.info('Initialized code update.')
        try:
            # Update code in 'dev' (Only used when updating from remote push)
            if self.update_env == 'dev':
                with cd(self.env_path):
                    local('git pull')

            # Update code in 'test' (commit & tag in 'dev', fetch in 'test')
            elif self.update_env == 'test':
                self.code_commit(message)
                self._tag_code(tag, message)
                self._fetch_and_reset(tag)

            # Update code in 'live' (get latest tag from 'test', fetch in
            # 'live')
            elif self.update_env == 'live':
                with cd(os.path.join(self.project_path, 'test')):
                    tag = local('git describe --tags --abbrev=0').rstrip('\n')
                self._fetch_and_reset(tag)
        except:
            self.log.exception('Code update encountered a fatal error.')
            raise
        else:
            self.log.info('Code update successful.')
        self.log.info('Gracefully restarting apache.')
        local("apache2ctl -k graceful", capture=False)

    def code_commit(self, message):
        try:
            with cd(os.path.join(self.project_path, 'dev')):
                local('git checkout %s' % self.project)
                local('git add -A .')
                with settings(warn_only=True):
                    local('git commit --author="%s" -m "%s"' % (
                          self.author, message), capture=False)
                local('git push')
        except:
            self.log.exception('Code commit encountered a fatal error.')
            raise
        else:
            self.log.info('Code commit successful.')

    def data_update(self, source_env):
        self.log.info('Initialized data sync')
        try:
            tempdir = tempfile.mkdtemp()
            export = dbtools.export_data(self, source_env, tempdir)
            dbtools.import_data(self, self.update_env, export)
            local('rm -rf %s' % tempdir)
        except:
            self.log.exception('Data sync encountered a fatal error.')
            raise
        else:
            self.log.info('Data sync successful.')

    def files_update(self, source_env):
        self.log.info('Initialized file sync')
        try:
            self.log.info('Attempting Rsync...')
            source = os.path.join(self.project_path,
                                  '%s/sites/default/files' % source_env)
            dest = os.path.join(self.project_path,
                                '%s/sites/default/' % self.update_env)
            local('rsync -av --delete %s %s' % (source, dest))
        except:
            self.log.exception('File sync encountered a fatal error.')
            raise
        else:
            self.log.info('File sync successful.')

    def drupal_updatedb(self):
        self.log.info('Initiated Updatedb.')
        try:
            alias = '@%s_%s' % (self.project, self.update_env)
            result = drupaltools.updatedb(alias)
        except:
            self.log.exception('Updatedb encountered a fatal error.')
            raise
        else:
            self.log.info('Updatedb complete.')
            pantheon.log_drush_backend(result, self.log)

    def run_cron(self):
        self.log.info('Initialized cron.')
        try:
            with settings(warn_only=True):
                result = local("drush @%s_%s -b cron" %
                               (self.project, self.update_env))
        except:
            self.log.exception('Cron encountered a fatal error.')
            raise
        else:
            pantheon.log_drush_backend(result, self.log)

    def solr_reindex(self):
        self.log.info('Initialized solr-reindex.')
        try:
            with settings(warn_only=True):
                result = local("drush @%s_%s -b solr-reindex" %
                               (self.project, self.update_env))
        except:
            self.log.exception('Solr-reindex encountered a fatal error.')
            raise
        else:
            pantheon.log_drush_backend(result, self.log)

    def restart_varnish(self):
        self.log.info('Restarting varnish.')
        try:
            with settings(warn_only=True):
                local("/etc/init.d/varnish restart")
        except:
            self.log.exception('Encountered an error during restart.')
            raise

    def permissions_update(self):
        self.log.info('Initialized permissions update.')
        try:
            self.setup_permissions('update', self.update_env)
        except Exception as e:
            self.log.exception('Permissions update encountered a fatal error.')
            raise
        else:
            self.log.info('Permissions update successful.')

    def run_command(self, command):
        try:
            with cd(self.env_path):
                local(command, capture=False)
        except:
            self.log.exception('Encountered a fatal error while running %s' %
                               command)
            raise

    def test_tag(self, tag):
        try:
            #test of existing tag
            with cd(self.env_path):
                with settings(warn_only=True):
                    count = local('git tag | grep -c ' + tag)
                    if count.strip() != "0":
                        abort('warning: tag ' + tag + ' already exists!')
        except:
            self.log.exception('Encountered a fatal error while tagging code.')
            raise

    def _tag_code(self, tag, message):
        try:
            with cd(os.path.join(self.project_path, 'dev')):
                local('git checkout %s' % self.project)
                local('git tag "%s" -m "%s"' % (tag, message), capture=False)
                local('git push --tags')
        except:
            self.log.exception('Encountered a fatal error while tagging code.')
            raise

    def _fetch_and_reset(self, tag):
        try:
            with cd(os.path.join(self.project_path, self.update_env)):
                local('git checkout %s' % self.project)
                local('git fetch -t')
                local('git reset --hard "%s"' % tag)
        except:
            self.log.exception('Fetch and reset encountered a fatal error.')
            raise

########NEW FILE########
__FILENAME__ = vars
# Set up some vars to use.

try:
    API_HOST = open("/opt/api_host.txt").read().strip()
except IOError:
    API_HOST = "api.getpantheon.com"

try:
    API_PORT = open("/opt/api_port.txt").read().strip()
except IOError:
    API_PORT = 8443

try:
    MERCURY_BRANCH = open("/opt/branch.txt").read().strip()
except IOError:
    MERCURY_BRANCH = "master"

try:
    VM_CERTIFICATE =  open("/opt/vm_certificate.txt").read().strip()
except IOError:
    VM_CERTIFICATE = "/etc/pantheon/system.pem"

########NEW FILE########
__FILENAME__ = ygg
import httplib
import json
from vars import *

# Note: Same call structure as in the Prometheus httprequest module.
# TODO: Unify
def send_event(thread, details, labels=['source-cloud'], site='self', source='cloud'):
    """ Send event.
    thread: string. Aggregates events from the same site together.
    details: dict. Contains data to send
    labels: list. Additional labels for listing the thread the event is in.
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/events/' % (site)

    details = {'source': source, source: details}

    request = {'thread': thread,
               'details': details,
               'labels': labels}
    return _api_request('POST', path, request)

def get_config(site='self'):
    """Return a dictionary of configuration data.
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/configuration' % (site)
    return _api_request('GET', path)

def get_service(service='', site='self'):
    """ Get service information.
    service: string. Service to query. An empty string returns all services.
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/services/%s' % (site, service)
    return _api_request('GET', path)

def set_service(service, data, site='self'):
    """ Update service indicator.
    service: string. Service to query. An empty string returns all services.
    data: dict. Contains data to store
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/services/%s' % (site, service)
    return _api_request('PUT', path, data)

def _api_request(method, path, data = None):
    """Make GET or PUT request to config server.
    Returns dict of response data.

    """
    headers = {}

    if method == 'PUT' or method == 'POST':
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(data)

    connection = httplib.HTTPSConnection(API_HOST,
                                         API_PORT,
                                         key_file = VM_CERTIFICATE,
                                         cert_file = VM_CERTIFICATE)

    connection.request(method, path, data, headers)
    response = connection.getresponse()

    if response.status == 404:
        return None
    if response.status == 403:
        return False

    if method == 'PUT' or method == 'POST':
        return True

    try:
        return json.loads(response.read())
    except:
        print('Response code: %s' % response.status)
        raise


########NEW FILE########
__FILENAME__ = permissions
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import string
import tempfile

from fabric.api import *
from pantheon import pantheon
from pantheon import logger
from pantheon import ygg

#TODO: Move logging into pantheon libraries for better coverage.
def configure_permissions(base_domain = "example.com",
                          require_group = None,
                          server_host = None):
    log = logger.logging.getLogger('pantheon.permissions.configure')
    log.info('Initialized permissions configuration.')
    try:
        server = pantheon.PantheonServer()

        if not server_host:
            server_host = "auth." + base_domain

        ldap_domain = _ldap_domain_to_ldap(base_domain)
        values = {'ldap_domain':ldap_domain,'server_host':server_host}

        template = pantheon.get_template('ldap-auth-config.preseed.cfg')
        ldap_auth_conf = pantheon.build_template(template, values)
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(ldap_auth_conf)
            temp_file.seek(0)
            local("sudo debconf-set-selections " + temp_file.name)

        # /etc/ldap/ldap.conf
        template = pantheon.get_template('openldap.ldap.conf')
        openldap_conf = pantheon.build_template(template, values)
        with open('/etc/ldap/ldap.conf', 'w') as f:
            f.write(openldap_conf)

        # /etc/ldap.conf
        template = pantheon.get_template('pam.ldap.conf')
        ldap_conf = pantheon.build_template(template, values)
        with open('/etc/ldap.conf', 'w') as f:
            f.write(ldap_conf)

        # Restrict by group
        allow = ['root', 'sudo', 'hermes']
        if require_group:
            allow.append(require_group)

        with open('/etc/ssh/sshd_config', 'a') as f:
            f.write('\nAllowGroups %s\n' % (' '.join(allow)))
            f.write('UseLPK yes\n')
            f.write('LpkLdapConf /etc/ldap.conf\n')

        local("auth-client-config -t nss -p lac_ldap")

        with open('/etc/sudoers.d/002_pantheon_users', 'w') as f:
            f.write("# This file was generated by PANTHEON.\n")
            f.write("# PLEASE DO NOT EDIT THIS FILE DIRECTLY.\n#\n")
            f.write("# Additional sudoer directives can be added in: " + \
                    "/etc/sudoers.d/003_pantheon_extra\n")
            f.write("\n%" + '%s ALL=(ALL) ALL' % require_group)
        local('chmod 0440 /etc/sudoers.d/002_pantheon_users')

        # Add LDAP user to www-data, and ssl-cert groups.
        ssl_group = "ssl-cert"
        local('usermod -aG %s,%s %s' % (server.web_group, ssl_group, require_group))
        # Use sed because usermod may fail if the user does not already exist.
        #local('sudo sed -i "s/' + ssl_group + ':x:[0-9]*:/\\0' + require_group + ',/g" /etc/group')

        # Restart after ldap is configured so openssh-lpk doesn't choke.
        local("/etc/init.d/ssh restart")

        # Write the group to a file for later reference.
        server.set_ldap_group(require_group)

        # Make the git repo and www directories writable by the group
        local("chown -R %s:%s /var/git/projects" % (require_group, require_group))
        local("chmod -R g+w /var/git/projects")

        # Make the git repo and www directories writable by the group
        local("chown -R %s:%s /var/www" % (require_group, require_group))
        local("chmod -R g+w /var/www")

        # Set ACLs
        set_acl_groupwritability(require_group, '/var/www')
        set_acl_groupwritability(require_group, '/var/git/projects')
    except:
        log.exception('Permission configuration unsuccessful.')
        raise
    else:
        log.info('Permissions configuration successful.')
        ygg._api_request('POST', '/sites/self/legacy-phone-home?phase=configure_permissions')

def _ldap_domain_to_ldap(domain):
    return ','.join(['dc=%s' % part.lower() for part in domain.split('.')])

def set_acl_groupwritability(require_group, directory):
    """Set up ACLs for a directory."""
    local('setfacl --recursive --remove-all %s' % directory)
    local('setfacl --recursive --no-mask --modify mask:rwx %s' % directory)
    local('setfacl --recursive --no-mask --modify group:%s:rwx %s' % (require_group, directory))
    local('setfacl --recursive --modify default:mask:rwx %s' % directory)
    local('setfacl --recursive --modify default:group:%s:rwx %s' % (require_group, directory))


########NEW FILE########
__FILENAME__ = site_backup
from pantheon import backup
from pantheon import logger

def backup_site(archive_name, project='pantheon'):
    log = logger.logging.getLogger('pantheon.site_backup')
    archive = backup.PantheonBackup(archive_name, project)
    log.info('Calculating necessary disk space.')
    if archive.free_space():
        log.info('Sufficient disk space found.')
        archive.backup_files()
        archive.backup_data()
        archive.backup_repo()
        archive.backup_config(version=0)
        archive.finalize()
    else:
        log.error('Insufficient disk space to perform archive.')
        raise IOError('Insufficient disk space to perform archive.')

def remove_backup(archive):
    backup.remove(archive)


########NEW FILE########
__FILENAME__ = site_devel
from pantheon import backup

DESTINATION = '/srv/dev_downloads'

def get_dev_downloads(resource, project, user=None):
    """Wapper method for a Jenkins job to get development resources.
    resource: type of download you want (all/files/data/code/drushrc)
    project: project name
    server_name: getpantheon server name.
    user: user that has ssh access to box.

    """
    archive_name = 'local_dev_%s' % resource
    resource_handler = {'all': _dev_all,
                        'files': _dev_files,
                        'data': _dev_data,
                        'code': _dev_code,
                        'drushrc': _dev_drushrc}
    resource_handler[resource](archive_name, project, user)

def _dev_all(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)

    # Only create archive of development environment data.
    archive.get_dev_files()
    archive.get_dev_data()
    archive.get_dev_code(user)
    archive.get_dev_drushrc(user)

    # Create the tarball and move to final location.
    archive.finalize(_get_destination())

def _dev_files(archive_name, project, *args):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_files()
    archive.finalize(_get_destination())

def _dev_data(archive_name, project, *args):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_data()
    archive.finalize(_get_destination())

def _dev_code(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_code(user)
    archive.finalize(_get_destination())

def _dev_drushrc(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_drushrc(user)
    archive.finalize(_get_destination())

def _get_destination():
    return DESTINATION


########NEW FILE########
__FILENAME__ = site_install
from pantheon import install
from pantheon import status
from pantheon import logger

def install_site(project='pantheon', version=6, profile='pantheon'):
    """ Create a new Pantheon Drupal installation.

    """
    data = {'profile': profile,
            'project': project,
            'version': int(version)}

    _installer(**data)

def install_project(url=None, profile='gitsource'):
    """ Create a new Installation from a git source.

    """
    data = {'url': url,
            'profile': profile}

    _installer(**data)

def _installer(**kw):
    #TODO: Move logging into pantheon libraries for better coverage.
    log = logger.logging.getLogger('pantheon.install.site')
    log = logger.logging.LoggerAdapter(log, kw)
    log.info('Site installation of project %s initiated.' % kw.get('project'))
    try:
        installer = install.InstallTools(**kw)

        # Remove existing project.
        installer.remove_project()

        # Create a new project
        if kw['profile'] == 'pantheon':
            installer.setup_project_repo()
            installer.setup_project_branch()
            installer.setup_working_dir()
        elif kw['profile'] == 'makefile':
            installer.process_makefile(kw['url'])
        elif kw['profile'] == 'gitsource':
            installer.process_gitsource(kw['url'])

        # Run bcfg2 project bundle.
        installer.bcfg2_project()

        # Setup project
        installer.setup_database()
        installer.setup_files_dir()
        installer.setup_settings_file()

        # Push changes from working directory to central repo
        installer.push_to_repo()

        # Build non-code site features.
        installer.setup_solr_index()
        installer.setup_drupal_cron()
        installer.setup_drush_alias()

        # Clone project to all environments
        installer.setup_environments()

        # Cleanup and restart services
        installer.cleanup()
        installer.server.restart_services()

        # Send back repo status.
        status.git_repo_status(installer.project)
        status.drupal_update_status(installer.project)

        # Set permissions on project
        installer.setup_permissions()

    except:
        log.exception('Site installation was unsuccessful')
        raise
    else:
        log.info('Site installation successful')


########NEW FILE########
__FILENAME__ = site_onramp
from pantheon import onramp
from pantheon import pantheon
from pantheon import restore
from pantheon import status
from pantheon import logger

def onramp_site(project='pantheon', url=None, profile=None, **kw):
    """Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    #TODO: Move logging into pantheon libraries for better coverage.
    log = logger.logging.getLogger('pantheon.onramp.site')
    log = logger.logging.LoggerAdapter(log,
                                       {"project": project})
    archive = onramp.download(url)
    location = onramp.extract(archive)
    handler = _get_handler(profile, project, location)

    log.info('Initiated site build.')
    try:
        handler.build(location)
    except:
        log.exception('Site build encountered an exception.')
        raise
    else:
        log.info('Site build was successful.')

def _get_handler(profile, project, location):
    """Return instantiated profile object.
    profile: name of the installation profile.

    To define additional profile handlers:
        1. Create a new profile class (example below)
        2. Add profile & class name to profiles dict in _get_profile_handler().

    """
    profiles = {'import': _ImportProfile,
                'restore': _RestoreProfile}

    # If the profile is not pre-defined try to determine if it is a restore
    # or an import (we may not know if they are uploading a pantheon backup or
    # their own existing site). Defaults to 'onramp'.
    if profile not in profiles.keys():
        profile = onramp.get_onramp_profile(location)

    return profiles[profile](project)


class _ImportProfile(onramp.ImportTools):
    """Generic Pantheon Import Profile.

    """
    def build(self, location):

        self.build_location = location
        # Parse the extracted archive.
        self.parse_archive(location)

        # Remove existing project.
        self.remove_project()

        # Create a new project
        self.setup_project_repo()
        self.setup_project_branch()

        # Run bcfg2 project bundle.
        self.bcfg2_project()

         # Import existing site into the project.
        self.setup_database()
        self.import_site_files()
        self.setup_files_dir()
        self.setup_settings_file()

        # Push imported project from working directory to central repo
        self.push_to_repo()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        # Turn on modules, set variables
        self.enable_pantheon_settings()

        # Clone project to all environments
        self.setup_environments()

        # Set permissions on project.
        self.setup_permissions()

        # Cleanup and restart services.
        self.cleanup()
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)


class _RestoreProfile(restore.RestoreTools):
    """Generic Pantheon Restore Profile.

    """
    def build(self, location):

        # Parse the backup.
        self.parse_backup(location)

        # Run bcfg2 project bundle.
        self.bcfg2_project()

        self.setup_database()
        self.restore_site_files()
        self.restore_repository()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        self.setup_permissions()
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)


########NEW FILE########
__FILENAME__ = update
# vim: tabstop=4 shiftwidth=4 softtabstop=4
import datetime
import tempfile
import time
import os
import string

from pantheon import logger
from pantheon import pantheon
from pantheon import postback
from pantheon import status
from pantheon import update
from pantheon.vars import *
from optparse import OptionParser

from fabric.api import *

def main():
    usage = "usage: %prog [options] *environments"
    parser = OptionParser(usage=usage, description="Update pantheon code and " \
                                                   "server configurations.")
    parser.add_option('-p', '--postback', dest="postback", action="store_true",
                      default=False, help='Postback to atlas.')
    parser.add_option('-d', '--debug', dest="debug", action="store_true",
                      default=False, help='Include debug output.')
    parser.add_option('-u', '--updatedb', dest="updatedb", action="store_true",
                      default=False, help='Run updatedb on an environment.')
    parser.add_option('-s', '--solr-reindex', dest="solr_reindex",
                      action="store_true", default=False,
                      help='Run solr-reindex on an environment.')
    parser.add_option('-c', '--cron', dest="cron", action="store_true",
                      default=False, help='Run cron on an environment.')
    parser.add_option('-v', '--varnish', dest="varnish", action="store_true",
                      default=False, help='Restart varnish.')
    (options, args) = parser.parse_args()
    log = logger.logging.getLogger('pantheon.update')

    if options.debug:
        log.setLevel(10)
    if len(args) == 0:
        update_pantheon(options.postback)
    elif len(args) > 0:
        for env in args:
            site = update.Updater(env)
            if options.updatedb:
                log.info('Running updatedb on {0}.'.format(env))
                site.drupal_updatedb()
            if options.solr_reindex:
                log.info('Running solr-reindex on {0}.'.format(env))
                # The server has a 2min delay before re-indexing
                site.solr_reindex()
            if options.cron:
                log.info('Running cron on {0}.'.format(env))
                site.run_cron()
            if options.varnish:
                log.info('Restarting varnish.')
                site.restart_varnish()
        log.info('Update complete.', extra=dict({"job_complete": 1}))

def update_pantheon(postback=True):
    """Update pantheon code and server configurations.

    postback: bool. If this is being called from the configure job, then it
    is the first boot, we don't need to wait for jenkins or send back update
    data.

    Otherwise:

    This script is run from a cron job because it may update Jenkins (and
    therefor cannot be run inside jenkins.)

    """
    log = logger.logging.getLogger('pantheon.update')
    if postback:
        log.info('Initiated pantheon update.')

    try:
        # Ensure the JDK is properly installed.
        local('apt-get install -y default-jdk')
        # Nightly security package updates disabled.

        try:
            log.debug('Putting jenkins into quietDown mode.')
            pantheon.jenkins_quiet()
            # TODO: Actually get security upgrades.
            # Get package security updates.
            #log.debug('Checking for security releases')
            #local('aptitude update')
            # Update pantheon code.
            log.debug('Checking which branch to use.')
            log.debug('Using branch %s.' % MERCURY_BRANCH)
            log.debug('Updating from repo.')
            with cd('/opt/pantheon'):
                local('git fetch --prune origin', capture=False)
                local('git checkout --force %s' % MERCURY_BRANCH, capture=False)
                local('git reset --hard origin/%s' % MERCURY_BRANCH, capture=False)
            # Run bcfg2.
            local('/usr/sbin/bcfg2 -vqed', capture=False)
        except:
            log.exception('Pantheon update encountered a fatal error.')
            raise
        finally:
            for x in range(12):
                if pantheon.jenkins_running():
                    break
                else:
                    log.debug('Waiting for jenkins to respond.')
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 2 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.debug('Restarting jenkins.')
            pantheon.jenkins_restart()

        # If this is not the first boot, send back update data.
        if postback:
            """
            We have to check for both queued jobs then the jenkins restart.
            This is because jobs could have been queued before the update
            was started, and a check on 'jenkins_running' would return True
            because the restart hasn't occured yet (safeRestart). This way,
            we first make sure the queue is 0 or jenkins is unreachable, then
            wait until it is back up.

            """
            log.debug('Not first boot, recording update data.')
            while True:
                queued = pantheon.jenkins_queued()
                if queued == 0:
                    # No more jobs, give jenkins a few seconds to begin restart.
                    time.sleep(5)
                    break
                # Jenkins is unreachable (already in restart process)
                elif queued == -1:
                    break
                else:
                    log.debug('Waiting for queued jobs to finish.')
                    time.sleep(5)
            # wait for jenkins to restart.
            for x in range(30):
                if pantheon.jenkins_running():
                    break
                else:
                    log.debug('Waiting for jenkins to respond.')
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 5 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.info('Pantheon update completed successfully.')
        else:
            log.info('Pantheon update completed successfully.')
    except:
        log.exception('Pantheon update encountered a fatal error.')
        raise

def update_site_core(project='pantheon', keep=None, taskid=None):
    """Update Drupal core (from Drupal or Pressflow, to latest Pressflow).
       keep: Option when merge fails:
             'ours': Keep local changes when there are conflicts.
             'theirs': Keep upstream changes when there are conflicts.
             'force': Leave failed merge in working-tree (manual resolve).
             None: Reset to ORIG_HEAD if merge fails.
    """
    updater = update.Updater('dev')
    result = updater.core_update(keep)
    if result['merge'] == 'success':
        # Send drupal version information.
        status.drupal_update_status(project)
        status.git_repo_status(project)
        updater.permissions_update()
        postback.write_build_data('update_site_core', result)

    else:
        log = logger.logging.getLogger('pantheon.update_site_core')
        updater.permissions_update()
        log.error('Upstream merge did not succeed. Review conflicts.')


def update_code(project, environment, tag=None, message=None, taskid=None):
    """ Update the working-tree for project/environment.

    """
    if not tag:
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not message:
        message = 'Tagging as %s for release.' % tag

    updater = update.Updater(environment)
    updater.test_tag(tag)
    updater.code_update(tag, message)
    updater.permissions_update()

    # Send back repo status and drupal update status
    status.git_repo_status(project)
    status.drupal_update_status(project)

def rebuild_environment(project, environment):
    """Rebuild the project/environment with files and data from 'live'.

    """
    updater = update.Updater(environment)
    updater.files_update('live')
    updater.data_update('live')

def update_data(project, environment, source_env, updatedb='True', taskid=None):
    """Update the data in project/environment using data from source_env.

    """
    updater = update.Updater(environment)
    updater.data_update(source_env)

def update_files(project, environment, source_env, taskid=None):
    """Update the files in project/environment using files from source_env.

    """
    updater = update.Updater(environment)
    updater.files_update(source_env)

def git_diff(project, environment, revision_1, revision_2=None):
    """Return git diff

    """
    updater = update.Updater(environment)
    if not revision_2:
           updater.run_command('git diff %s' % revision_1)
    else:
           updater.run_command('git diff %s %s' % (revision_1, revision_2))

def git_status(project, environment):
    """Return git status

    """
    updater = update.Updater(environment)
    updater.run_command('git status')

def upgrade_drush(tag='7.x-4.4',make_tag='6.x-2.2'):
    """Git clone Drush and download Drush-Make.

    tag: the drush version tag to checkout

    """
    drush_path = '/opt/drush'
    commands_path = os.path.join(drush_path, 'commands')
    alias_path = os.path.join(drush_path, 'aliases')
    if not os.path.exists(os.path.join(drush_path, '.git')):
        with cd('/opt'):
            local('[ ! -d drush ] || rm -rf drush')
            local('git clone http://git.drupal.org/project/drush.git')
    with cd('/opt'):
        with cd(drush_path):
            local('git checkout -f tags/{0}'.format(tag))
            local('git reset --hard')
        local('chmod 555 drush/drush')
        local('chown -R root: drush')
        local('ln -sf {0} /usr/local/bin/drush'.format(os.path.join(drush_path,
                                                                    'drush')))
        local('drush dl --package-handler=git_drupalorg -y ' \
              '--destination={0} ' \
              '--default-major=6 drush_make'.format(commands_path))
        with cd(os.path.join(commands_path,'drush_make')):
            local('git checkout -f tags/{0}'.format(make_tag))
            local('git reset --hard')
    local('mkdir -p {0}'.format(alias_path))
    update.Updater().setup_drush_alias()
    with open(os.path.join(drush_path, '.gitignore'), 'w') as f:
        f.write('\n'.join(['.gitignore','aliases','commands/drush_make','']))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = usage
import httplib
import subprocess
import datetime
import json
import time
from pantheon.vars import *

connection = httplib.HTTPSConnection(
    API_HOST,
    API_PORT,
    key_file = VM_CERTIFICATE,
    cert_file = VM_CERTIFICATE
)


def get_nearest_hour(unix_timestamp):
    return unix_timestamp - (unix_timestamp % 3600)

def get_nearest_day(unix_timestamp):
    return unix_timestamp - (unix_timestamp % 86400)

def _set_batch_usage(batch_post):
    body = json.dumps(batch_post)
    connection.request("POST", "/sites/self/usage/", body)
    complete_response = connection.getresponse()
    # Read the response to allow subsequent requests.
    complete_response.read()
    if complete_response.status != 200:
        raise Exception('Could not set usage.')


def _set_bandwidth(now):
    command = ["/usr/bin/vnstat", "--hours", "--dumpdb"]
    lines = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0].split("\n")
    batch_post = []

    print("Recent bandwidth (inbound/outbound KiB):")

    for line in lines:
        # Ignore blank or non-hour lines.
        if line == "" or not line.startswith("h;"):
            continue
        parts = line.split(";")
        hour = get_nearest_hour(int(parts[2]))

        # Ignore data that's younger than an hour or older than an hour and a day.
        if (now - hour) <= 3600 or (now - hour) > (86400 + 3600) or hour == 0:
            continue
        inbound_kib = parts[3]
        outbound_kib = parts[4]

        stamp = datetime.datetime.utcfromtimestamp(hour)
        print("[%s] %s/%s" % (stamp.strftime("%Y-%m-%d %H:%M:%S"), inbound_kib, outbound_kib))

        batch_post.append({"metric": "bandwidth_in",
                           "start": hour,
                           "duration": 3600,
                           "amount": inbound_kib})
        batch_post.append({"metric": "bandwidth_out",
                           "start": hour,
                           "duration": 3600,
                           "amount": outbound_kib})
    print("Publishing bandwidth in/out to the Pantheon API...")
    _set_batch_usage(batch_post)

def _set_ram(now):
    batch_post = []
    memfile = open('/proc/meminfo')
    for line in memfile.readlines():
        line=line.strip()
        if (line[:8] == 'MemTotal'):
            ram = line.rstrip('kB').lstrip('MemTotal:').strip()

    print("MemTotal: %s kB" % ram)

    day = get_nearest_day(now)
    batch_post.append({"metric": "memory",
                       "start": day,
                       "duration": 86400,
                       "amount": ram})
    print("Publishing MemTotal to the Pantheon API...")
    _set_batch_usage(batch_post)

def publish_usage():
    now = time.time()
    _set_bandwidth(now)
    _set_ram(now)

########NEW FILE########
__FILENAME__ = webkit2png
#!/usr/bin/env python
#
# webkit2png.py
#
# Creates screenshots of webpages using by QtWebkit.
#
# Copyright (c) 2008 Roland Tapken <roland@dau-sicher.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#
# Nice ideas "todo":
#  - Add QTcpSocket support to create a "screenshot daemon" that
#    can handle multiple requests at the same time.

import sys
import signal
import os
import logging
import time
import urlparse

from optparse import OptionParser

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4.QtNetwork import *

VERSION="20091224"
LOG_FILENAME = 'webkit2png.log'
logger = logging.getLogger('webkit2png');

# Class for Website-Rendering. Uses QWebPage, which
# requires a running QtGui to work.
class WebkitRenderer(QObject):
    """A class that helps to create 'screenshots' of webpages using
    Qt's QWebkit. Requires PyQt4 library.

    Use "render()" to get a 'QImage' object, render_to_bytes() to get the
    resulting image as 'str' object or render_to_file() to write the image
    directly into a 'file' resource.

    These methods have to be called from within Qt's main (GUI) thread.
    An example on how to use this is the __qt_main() method at the end
    of the libraries source file. More generic examples:

def qt_main():
    while go_on():
        do_something_meaningful()
        while QApplication.hasPendingEvents():
             QApplication.processEvents()
    QApplication.quit()

app = init_qtgui()
QTimer.singleShot(0, qt_main)
sys.exit(app.exec_())

    Or let Qt handle event processing using a QTimer instance:

        def qt_main_loop():
            if not go_on():
                QApplication.quit()
                return
            do_something_meaningful()
 
        app = init_qtgui()
        main_timer = QTimer()
        QObject.connect(main_timer, QtCore.SIGNAL("timeout()"), qt_main_loop)
        sys.exit(app.exec_())

    Avaible properties:
    width -- The width of the "browser" window. 0 means autodetect (default).
    height -- The height of the window. 0 means autodetect (default).
    timeout -- Seconds after that the request is aborted (default: 0)
    wait -- Seconds to wait after loading has been finished (default: 0)
    scaleToWidth -- The resulting image is scaled to this width.
    scaleToHeight -- The resulting image is scaled to this height.
    scaleRatio -- The image is scaled using this method. Possible values are:
      keep
      expand
      crop
      ignore
    grabWhileWindow -- If this is True a screenshot of the whole window is taken. Otherwise only the current frame is rendered. This is required for plugins to be visible, but it is possible that another window overlays the current one while the screenshot is taken. To reduce this possibility, the window is activated just before it is rendered if this property is set to True (default: False).
    qWebSettings -- Settings that should be assigned to the created QWebPage instance. See http://doc.trolltech.com/4.6/qwebsettings.html for possible keys. Defaults:
      JavascriptEnabled: False
      PluginsEnabled: False
      PrivateBrowsingEnabled: True
      JavascriptCanOpenWindows: False
    """

    def __init__(self,**kwargs):
        """Sets default values for the properties."""

        if not QApplication.instance():
            raise RuntimeError(self.__class__.__name__ + " requires a running QApplication instance")
        QObject.__init__(self)

        # Initialize default properties
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.timeout = kwargs.get('timeout', 0)
        self.wait = kwargs.get('wait', 0)
        self.scaleToWidth = kwargs.get('scaleToWidth', 0)
        self.scaleToHeight = kwargs.get('scaleToHeight', 0)
        self.scaleRatio = kwargs.get('scaleRatio', 'keep')
        # Set this to true if you want to capture flash.
        # Not that your desktop must be large enough for
        # fitting the whole window.
        self.grabWholeWindow = kwargs.get('grabWholeWindow', False) 
        self.renderTransparentBackground = kwargs.get('renderTransparentBackground', False)
        
        # Set some default options for QWebPage
        self.qWebSettings = {
            QWebSettings.JavascriptEnabled : False,
            QWebSettings.PluginsEnabled : False,
            QWebSettings.PrivateBrowsingEnabled : True,
            QWebSettings.JavascriptCanOpenWindows : False
        }


    def render(self, url):
        """Renders the given URL into a QImage object"""
        # We have to use this helper object because
        # QApplication.processEvents may be called, causing
        # this method to get called while it has not returned yet.
        helper = _WebkitRendererHelper(self)
        image = helper.render(url)

        # Bind helper instance to this image to prevent the
        # object from being cleaned up (and with it the QWebPage, etc)
        # before the data has been used.
        image.helper = helper

        return image

    def render_to_file(self, url, file):
        """Renders the image into a File resource.
        Returns the size of the data that has been written.
        """
        format = self.format # this may not be constant due to processEvents()
        image = self.render(url)
        qBuffer = QBuffer()
        image.save(qBuffer, format)
        file.write(qBuffer.buffer().data())
        return qBuffer.size()

    def render_to_bytes(self, url):
        """Renders the image into an object of type 'str'"""
        format = self.format # this may not be constant due to processEvents()
        image = self.render(url)
        qBuffer = QBuffer()
        image.save(qBuffer, format)
        return qBuffer.buffer().data()

class _WebkitRendererHelper(QObject):
    """This helper class is doing the real work. It is required to 
    allow WebkitRenderer.render() to be called "asynchronously"
    (but always from Qt's GUI thread).
    """

    def __init__(self, parent):
        """Copies the properties from the parent (WebkitRenderer) object,
        creates the required instances of QWebPage, QWebView and QMainWindow
        and registers some Slots.
        """
        QObject.__init__(self)

        # Copy properties from parent
        for key,value in parent.__dict__.items():
            setattr(self,key,value)

        # Create and connect required PyQt4 objects
        self._page = QWebPage()
        self._view = QWebView()
        self._view.setPage(self._page)
        self._window = QMainWindow()
        self._window.setCentralWidget(self._view)

        # Import QWebSettings
        for key, value in self.qWebSettings.iteritems():
            self._page.settings().setAttribute(key, value)

        # Connect required event listeners
        self.connect(self._page, SIGNAL("loadFinished(bool)"), self._on_load_finished)
        self.connect(self._page, SIGNAL("loadStarted()"), self._on_load_started)
        self.connect(self._page.networkAccessManager(), SIGNAL("sslErrors(QNetworkReply *,const QList<QSslError>&)"), self._on_ssl_errors)

        # The way we will use this, it seems to be unesseccary to have Scrollbars enabled
        self._page.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self._page.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self._page.settings().setUserStyleSheetUrl(QUrl("data:text/css,html,body{overflow-y:hidden !important;}"))

        # Show this widget
        self._window.show()

    def __del__(self):
        """Clean up Qt4 objects. """
        self._window.close()
        del self._window
        del self._view
        del self._page

    def render(self, url):
        """The real worker. Loads the page (_load_page) and awaits
        the end of the given 'delay'. While it is waiting outstanding
        QApplication events are processed.
        After the given delay, the Window or Widget (depends
        on the value of 'grabWholeWindow' is drawn into a QPixmap
        and postprocessed (_post_process_image).
        """
        self._load_page(url, self.width, self.height, self.timeout)
        # Wait for end of timer. In this time, process
        # other outstanding Qt events.
        if self.wait > 0:
            logger.debug("Waiting %d seconds " % self.wait)
            waitToTime = time.time() + self.wait
            while time.time() < waitToTime:
                while QApplication.hasPendingEvents():
                    QApplication.processEvents()

        # Paint this frame into an image
        #self._window.repaint()
        while QApplication.hasPendingEvents():
            QApplication.processEvents()

        if self.renderTransparentBackground:
            # Another possible drawing solution
            image = QImage(self._page.viewportSize(), QImage.Format_ARGB32)
            image.fill(QColor(255,0,0,0).rgba())

            # http://ariya.blogspot.com/2009/04/transparent-qwebview-and-qwebpage.html
            palette = self._view.palette()
            palette.setBrush(QPalette.Base, Qt.transparent)
            self._page.setPalette(palette)
            self._view.setAttribute(Qt.WA_OpaquePaintEvent, False)

            painter = QPainter(image)
            painter.setBackgroundMode(Qt.TransparentMode)
            self._page.mainFrame().render(painter)
            painter.end()
        else:
            if self.grabWholeWindow:
                # Note that this does not fully ensure that the
                # window still has the focus when the screen is
                # grabbed. This might result in a race condition.
                self._view.activateWindow()
                image = QPixmap.grabWindow(self._window.winId())
            else:
                image = QPixmap.grabWidget(self._window)
        

        return self._post_process_image(image)

    def _load_page(self, url, width, height, timeout):
        """
        This method implements the logic for retrieving and displaying 
        the requested page.
        """

        # This is an event-based application. So we have to wait until
        # "loadFinished(bool)" raised.
        cancelAt = time.time() + timeout
        self.__loading = True
        self.__loadingResult = False # Default
        # TODO: fromEncoded() needs to be used in some situations.  Some
        # sort of flag should be passed in to WebkitRenderer maybe?
        #self._page.mainFrame().load(QUrl.fromEncoded(url))
        self._page.mainFrame().load(QUrl(url))
        while self.__loading:
            if timeout > 0 and time.time() >= cancelAt:
                raise RuntimeError("Request timed out on %s" % url)
            while QApplication.hasPendingEvents():
                QCoreApplication.processEvents()

        logger.debug("Processing result")

        if self.__loading_result == False:
            logger.warning("Failed to load %s" % url)

        # Set initial viewport (the size of the "window")
        size = self._page.mainFrame().contentsSize()
        logger.debug("contentsSize: %s", size)
        if width > 0:
            size.setWidth(width)
        if height > 0:
            size.setHeight(height)

        self._window.resize(size)

    def _post_process_image(self, qImage):
        """If 'scaleToWidth' or 'scaleToHeight' are set to a value
        greater than zero this method will scale the image
        using the method defined in 'scaleRatio'.
        """
        if self.scaleToWidth > 0 or self.scaleToHeight > 0:
            # Scale this image
            if self.scaleRatio == 'keep':
                ratio = Qt.KeepAspectRatio
            elif self.scaleRatio in ['expand', 'crop']:
                ratio = Qt.KeepAspectRatioByExpanding
            else: # 'ignore'
                ratio = Qt.IgnoreAspectRatio
            qImage = qImage.scaled(self.scaleToWidth, self.scaleToHeight, ratio)
            if self.scaleRatio == 'crop':
                qImage = qImage.copy(0, 0, self.scaleToWidth, self.scaleToHeight)
        return qImage

    # Eventhandler for "loadStarted()" signal
    def _on_load_started(self):
        """Slot that sets the '__loading' property to true."""
        logger.debug("loading started")
        self.__loading = True

    # Eventhandler for "loadFinished(bool)" signal
    def _on_load_finished(self, result):
        """Slot that sets the '__loading' property to false and stores
        the result code in '__loading_result'.
        """
        logger.debug("loading finished with result %s", result)
        self.__loading = False
        self.__loading_result = result

    # Eventhandler for "sslErrors(QNetworkReply *,const QList<QSslError>&)" signal
    def _on_ssl_errors(self, reply, errors):
        """Slot that writes SSL warnings into the log but ignores them."""
        for e in errors:
            logger.warn("SSL: " + e.errorString())
        reply.ignoreSslErrors()


def init_qtgui(display=None, style=None, qtargs=[]):
    """Initiates the QApplication environment using the given args."""
    if QApplication.instance():
        logger.debug("QApplication has already been instantiated. \
                        Ignoring given arguments and returning existing QApplication.")
        return QApplication.instance()
    
    qtargs2 = [sys.argv[0]]
    
    if display:
        qtargs2.append('-display')
        qtargs2.append(display)
        # Also export DISPLAY var as this may be used
        # by flash plugin
        os.environ["DISPLAY"] = display
    
    if style:
        qtargs2.append('-style')
        qtargs2.append(style)
    
    qtargs2.extend(qtargs)
    
    return QApplication(qtargs2)


if __name__ == '__main__':
    # This code will be executed if this module is run 'as-is'.

    # Enable HTTP proxy
    if 'http_proxy' in os.environ:
        proxy_url = urlparse.urlparse(os.environ.get('http_proxy'))
        proxy = QNetworkProxy(QNetworkProxy.HttpProxy, proxy_url.hostname, proxy_url.port)
        QNetworkProxy.setApplicationProxy(proxy)
    
    # Parse command line arguments.
    # Syntax:
    # $0 [--xvfb|--display=DISPLAY] [--debug] [--output=FILENAME] <URL>

    description = "Creates a screenshot of a website using QtWebkit." \
                + "This program comes with ABSOLUTELY NO WARRANTY. " \
                + "This is free software, and you are welcome to redistribute " \
                + "it under the terms of the GNU General Public License v2."

    parser = OptionParser(usage="usage: %prog [options] <URL>",
                          version="%prog " + VERSION + ", Copyright (c) Roland Tapken",
                          description=description, add_help_option=True)
    parser.add_option("-x", "--xvfb", nargs=2, type="int", dest="xvfb",
                      help="Start an 'xvfb' instance with the given desktop size.", metavar="WIDTH HEIGHT")
    parser.add_option("-g", "--geometry", dest="geometry", nargs=2, default=(0, 0), type="int",
                      help="Geometry of the virtual browser window (0 means 'autodetect') [default: %default].", metavar="WIDTH HEIGHT")
    parser.add_option("-o", "--output", dest="output",
                      help="Write output to FILE instead of STDOUT.", metavar="FILE")
    parser.add_option("-f", "--format", dest="format", default="png",
                      help="Output image format [default: %default]", metavar="FORMAT")
    parser.add_option("--scale", dest="scale", nargs=2, type="int",
                      help="Scale the image to this size", metavar="WIDTH HEIGHT")
    parser.add_option("--aspect-ratio", dest="ratio", type="choice", choices=["ignore", "keep", "expand", "crop"],
                      help="One of 'ignore', 'keep', 'crop' or 'expand' [default: %default]")
    parser.add_option("-F", "--feature", dest="features", action="append", type="choice",
                      choices=["javascript", "plugins"],
                      help="Enable additional Webkit features ('javascript', 'plugins')", metavar="FEATURE")
    parser.add_option("-w", "--wait", dest="wait", default=0, type="int",
                      help="Time to wait after loading before the screenshot is taken [default: %default]", metavar="SECONDS")
    parser.add_option("-t", "--timeout", dest="timeout", default=0, type="int",
                      help="Time before the request will be canceled [default: %default]", metavar="SECONDS")
    parser.add_option("-W", "--window", dest="window", action="store_true",
                      help="Grab whole window instead of frame (may be required for plugins)", default=False)
    parser.add_option("-T", "--transparent", dest="transparent", action="store_true",
                      help="Render output on a transparent background (Be sure to have a transparent background defined in the html)", default=False)
    parser.add_option("", "--style", dest="style",
                      help="Change the Qt look and feel to STYLE (e.G. 'windows').", metavar="STYLE")
    parser.add_option("-d", "--display", dest="display",
                      help="Connect to X server at DISPLAY.", metavar="DISPLAY")
    parser.add_option("--debug", action="store_true", dest="debug",
                      help="Show debugging information.", default=False)
    parser.add_option("--log", action="store", dest="logfile", default=LOG_FILENAME,
                      help="Select the log output file",)

    # Parse command line arguments and validate them (as far as we can)
    (options,args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")
    if options.display and options.xvfb:
        parser.error("options -x and -d are mutually exclusive")
    options.url = args[0]

    logging.basicConfig(filename=options.logfile,level=logging.WARN,)

    # Enable output of debugging information
    if options.debug:
        logger.setLevel(logging.DEBUG)

    if options.xvfb:
        # Start 'xvfb' instance by replacing the current process
        server_num = int(os.getpid() + 1e6)
        newArgs = ["xvfb-run", "--auto-servernum", "--server-num", str(server_num), "--server-args=-screen 0, %dx%dx24" % options.xvfb, sys.argv[0]]
        skipArgs = 0
        for i in range(1, len(sys.argv)):
            if skipArgs > 0:
                skipArgs -= 1
            elif sys.argv[i] in ["-x", "--xvfb"]:
                skipArgs = 2 # following: width and height
            else:
                newArgs.append(sys.argv[i])
        logger.debug("Executing %s" % " ".join(newArgs))
        os.execvp(newArgs[0],newArgs[1:])
        
    # Prepare outout ("1" means STDOUT)
    if options.output == None:
        options.output = sys.stdout
    else:
        options.output = open(options.output, "w")

    logger.debug("Version %s, Python %s, Qt %s", VERSION, sys.version, qVersion());

    # Technically, this is a QtGui application, because QWebPage requires it
    # to be. But because we will have no user interaction, and rendering can
    # not start before 'app.exec_()' is called, we have to trigger our "main"
    # by a timer event.
    def __main_qt():
        # Render the page.
        # If this method times out or loading failed, a
        # RuntimeException is thrown
        try:
            # Initialize WebkitRenderer object
            renderer = WebkitRenderer()
            renderer.width = options.geometry[0]
            renderer.height = options.geometry[1]
            renderer.timeout = options.timeout
            renderer.wait = options.wait
            renderer.format = options.format
            renderer.grabWholeWindow = options.window
            renderer.renderTransparentBackground = options.transparent

            if options.scale:
                renderer.scaleRatio = options.ratio
                renderer.scaleToWidth = options.scale[0]
                renderer.scaleToHeight = options.scale[1]

            if options.features:
                if "javascript" in options.features:
                    renderer.qWebSettings[QWebSettings.JavascriptEnabled] = True
                if "plugins" in options.features:
                    renderer.qWebSettings[QWebSettings.PluginsEnabled] = True

            renderer.render_to_file(url=options.url, file=options.output)
            options.output.close()
            QApplication.exit(0)
        except RuntimeError, e:
            logger.error("main: %s" % e)
            print >> sys.stderr, e
            QApplication.exit(1)

    # Initialize Qt-Application, but make this script
    # abortable via CTRL-C
    app = init_qtgui(display = options.display, style=options.style)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    QTimer.singleShot(0, __main_qt)
    sys.exit(app.exec_())

########NEW FILE########
