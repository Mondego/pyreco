__FILENAME__ = command_center
#!/usr/bin/env python


"""The command center is where assault coordination takes place. A typical use
would be to initialize a bunch of micro instances and use them as siege cannons.

The interface is a prompt offering help and funcitons for building / controlling
the cannons. It is advised you double check the behavior of the system through
Amazon's web interface too.

Access to the cannon's is done via SSH inside eventlet greenpiles.

EC2 console: https://console.aws.amazon.com/ec2/
"""

import cmd
from microarmy.commands import CommandCenter
import sys

if __name__ == '__main__':
    try:
        CommandCenter().cmdloop()
    except KeyboardInterrupt:
       print 'bye'
       sys.exit(0)


########NEW FILE########
__FILENAME__ = commands
"""Command dispatcher and commands to run.

Look up the command from the command center, attempt to map it to a local method.

"""

from eventlet import patcher
patcher.monkey_patch(all=True)

import boto
import time
import datetime
import sys
import cmd

import settings
from microarmy.firepower import (init_cannons,
                                 terminate_cannons,
                                 reboot_cannons,
                                 setup_cannons,
                                 slam_host,
                                 setup_siege,
                                 setup_siege_urls,
                                 find_deployed_cannons,
                                 destroy_deployed_cannons)


class CommandCenter(cmd.Cmd):
    """Commands and helpers for command center."""


    def __init__(self):
        cmd.Cmd.__init__(self)
        self._cannons_deployed = False
        self._cannon_hosts = None
        self._cannon_infos = None
        self._bypass_urls = False
        self._siege_urls = settings.siege_urls or None
        self._siege_config = settings.siege_config or None
        self.prompt = 'microarmy> '

    def default(self, line):
        print
        print 'Cannot find command: "%s"' % line
        self.do_help(None)

    def emptyline(self):
        pass

    def do_EOF(self, line):
        print 'bye'
        return True

    def _write_siege_config(self, siegerc):
        """Write siege config to local disk before deploying"""

        file_data = None
        return_status = None

        for key, value in siegerc.iteritems():
            if file_data:
                file_data += "%s = %s\n" %(key, value)
            else:
                file_data = "%s = %s\n" %(key, value)

        try:
            siegerc_file = open('./env_scripts/siegerc', 'w')
            siegerc_file.write(file_data)
            siegerc_file.close()
            return_status = True
        except IOError:
            return_status = False

        return return_status

    def _write_siege_urls(self, urls):
        """Write siege urls to local disk before deploying"""

        file_data = None
        return_status = None

        for url in urls:
            if file_data:
                file_data += "%s\n" %(url)
            else:
                file_data = "%s\n" %(url)

        try:
            urls_file = open('./env_scripts/urls.txt', 'w')
            urls_file.write(file_data)
            urls_file.close()
            return_status = True
        except IOError:
            return_status = False

        return return_status

    def do_long_help(self, line):
        """Long help output"""
        print """
        long_help:    This.
        status:       Get info about current cannons
        deploy:       Deploys N cannons
        setup:        Runs the setup functions on each host
        config:       Allows a user to specify existing cannons
        config_siege: Create siege config from specified dictionary
        siege_urls:   Specify list of URLS to test against
        single_url:   Only hit one url when firing off your next test
        all_urls:     Revert to using configured urls (turns off single_url)
        fire:         Asks for a url and then fires the cannons
        mfire:        Runs `fire` multiple times and aggregates totals
        term:         Terminate cannons
        quit:         Exit command center
        """

    def do_deploy(self, line):
        """Deploy N cannons"""
        start_time = time.time()
        self._cannon_infos = init_cannons()
        print 'Time: %s' %(time.time()-start_time)

    def do_term(self, line):
        """Terminate cannons"""
        if not self._cannon_infos:
            print 'ERROR: No cannons defined, try "config" or "deploy"'
            return

        terminate_cannons([h[0] for h in self._cannon_infos])
        self._cannon_infos = None
        self._cannon_hosts = None
        self._cannons_deployed = False
        print 'Deployed cannons destroyed'

    def do_quit(self, line):
        """Exit command center"""
        print 'bye'
        sys.exit(0)

    def do_setup(self, line):
        """Setup system, deploy configs and urls"""
        if not self._cannon_infos:
            print 'ERROR: No cannons defined, try "config" or "deploy"'
            return

        start_time = time.time()
        print 'Setting up cannons'
        self._cannon_hosts = [h[1] for h in self._cannon_infos]
        status = setup_cannons(self._cannon_hosts)

        if self._siege_config:
            if self._write_siege_config(self._siege_config):
                print 'Siege config written, deploying to cannons'
                setup_siege(self._cannon_hosts)
            else:
                print 'ERROR: Cannot write new siege config'

        if self._siege_urls:
            if self._write_siege_urls(self._siege_urls):
                print 'Siege urls written, deploying to cannons'
                setup_siege_urls(self._cannon_hosts)
            else:
                print 'ERROR: Cannot write urls'

        print 'Finished setup - time: %s' % (time.time()-start_time)

        print 'Sending reboot message to cannons'
        reboot_cannons([h[0] for h in self._cannon_infos])
        self._cannons_deployed = True

    def do_config_siege(self, line):
        """Create siege config, deploy it to cannons"""
        if self._cannons_deployed:
            if self._siege_config:
                print '  Siege config detected in settings and will be automatically deployed with "setup"'
                answer = raw_input('  Continue? (y/n) ')
                if answer.lower() == 'n':
                   return

            siegerc = raw_input('  Enter siege config data: ')
            if self._write_siege_config(eval(siegerc)):
                print '  Siege config written, deploying to cannons'
                setup_siege(self._cannon_hosts)
                self._siege_config = eval(siegerc)
            else:
                print 'ERROR: Cannot write new siege config'
        else:
            print 'ERROR: Cannons not deployed yet'

    def do_siege_urls(self, line):
        """Create siege urls file, deploy it to cannons"""
        if self._cannons_deployed:
            if self._siege_urls:
                print '  Urls detected in settings and will be automatically deployed with "setup"'
                answer = raw_input('  Continue? (y/n) ')
                if answer == 'n':
                   return

            siege_urls = raw_input('  Enter urls: ')
            if self._write_siege_urls(eval(siege_urls)):
                print 'Urls written, deploying to cannons'
                setup_siege_urls(self._cannon_hosts)
                self._siege_urls = eval(siege_urls)
            else:
                print 'ERROR: Cannot write new urls'
        else:
            print 'ERROR: Cannons not deployed yet'

    def do_single_url(self, line):
        """Bypass configured urls, allowing to specify one dynamically"""
        self._bypass_urls = True
        print 'Bypassing configured urls'

    def do_all_urls(self, line):
        """Disable 'single_url' mode"""
        self._bypass_urls = False
        print 'Using configured urls'

    def do_status(self, line):
        """Get information about current cannons, siege configs and urls"""
        if not self._cannon_infos:
            print '  No cannons defined, try "config" or "deploy"'
            return
        for host in self._cannon_infos:
            iid, ihost = [h for h in host]
            print '  Cannon: %s:%s' %(iid, ihost)

        print '\n  Last written siege config: '
        print '  %s' % self._siege_config

        print '\n  Last written urls: '
        print '  %s' % self._siege_urls

    def do_config(self, line, cannon_data=None):
        """Allows a user to specify existing cannons"""
        if not cannon_data:
            cannon_data = raw_input('  Enter host data: ')
        if cannon_data != '':
            if isinstance(cannon_data, str):
                self._cannon_infos = eval(cannon_data)
            else:
                self._cannon_infos = cannon_data
            self._cannon_hosts = [h[1] for h in self._cannon_infos]
            self._cannons_deployed = True
        else:
            print 'ERROR: No host data specified'
        return

    def do_find_cannons(self, line):
        """Find all cannons deployed for microarmy"""
        hosts = find_deployed_cannons()
        if hosts:
            print 'Deployed cannons:', hosts
            answer = raw_input('Would you like to import these cannons now? (y/n) ')
            if answer.lower() == 'n':
                return
            self.do_config(None, hosts)
        else:
            print 'No cannons found'

    def do_cleanup(self, line):
        """Find all cannons we have deployed, destroy them all"""
        destroy_deployed_cannons()
        print 'Deployed cannons destroyed'

    def do_fire(self, line):
        """Fires the cannons, asks for URL if none are defined in settings"""
        if self._cannons_deployed:
            if self._siege_urls and not self._bypass_urls:
                report = slam_host(self._cannon_hosts, None)
            else:
                target = raw_input('  target: ')
                if target != '':
                    report = slam_host(self._cannon_hosts, target)
                else:
                    print 'ERROR: No target specified'
                    return

            if isinstance(report, str):
                print report
                return

            ### Ad-hoc CSV
            print 'Results ]------------------'
            print 'Num_Trans,Elapsed,Tran_Rate'
            total_trans = 0
            for idx in xrange(len(report['num_trans'])):
                total_trans = total_trans + int(report['num_trans'][idx])
                print '%s,%s,%s' % (report['num_trans'][idx],
                                    report['elapsed'][idx],
                                    report['tran_rate'][idx])
            print 'Total:', total_trans
        else:
            print 'ERROR: Cannons not deployed yet'

    def do_mfire(self, line):
        """Runs `fire` multiple times and aggregates totals"""
        if self._cannons_deployed:
            ### Get test arguments from user
            try:

                if not self._siege_urls and self._bypass_urls:
                    target =  raw_input('   target: ')

                n_times = raw_input('  n times: ')
                n_times = int(n_times)
            except:
                print '<target> must be a string.'
                print '<n_times> must be a number.'
                return

            print 'Results ]------------------'
            print 'Run ID,Sum Transactions,Sum Transaction Rate'
            total_transactions = 0
            for run_instance in xrange(n_times):
                report = slam_host(self._cannon_hosts, target)

                if isinstance(report, str):
                    print report
                    return

                ### Ad-hoc CSV
                sum_num_trans = 0.0
                sum_tran_rate = 0.0
                for idx in xrange(len(report['num_trans'])):
                    sum_num_trans = sum_num_trans + float(report['num_trans'][idx])
                    sum_tran_rate = sum_tran_rate + float(report['tran_rate'][idx])

                total_transactions = total_transactions + sum_num_trans
                print '%s,%s,%s' % (run_instance, sum_num_trans, sum_tran_rate)
            print 'Total:', total_transactions
        else:
            print 'ERROR: Cannons not deployed yet'

########NEW FILE########
__FILENAME__ = communications
import paramiko
import os
import getpass

from settings import (
    ec2_ssh_key,
    ec2_ssh_key_password,
    ec2_ssh_username,
)

###
### SSH funcitons
###

def ssh_connect(host, port=22):
    """Helper function to initiate an ssh connection to a host."""
    transport = paramiko.Transport((host, port))
    
    if os.path.exists(os.path.expanduser(ec2_ssh_key)):
        try:
            rsa_key = paramiko.RSAKey.from_private_key_file(os.path.expanduser(ec2_ssh_key))
        
        # an exception is thrown if the ssh private key is encrypted
        except paramiko.PasswordRequiredException:

            # if the password wasn't defined in settings, ask for it
            if not ec2_ssh_key_password:
                rsa_key_password = getpass.getpass(prompt='\nFound an encrypted private SSH key, please enter your decryption password: ')
            else:
                rsa_key_password = ec2_ssh_key_password

            # setup the pkey object by reading the file from disk, with a decryption password
            rsa_key = paramiko.RSAKey.from_private_key_file(os.path.expanduser(ec2_ssh_key), password=rsa_key_password)

        # pass pkey object to connection
        transport.connect(username=ec2_ssh_username, pkey=rsa_key)
            
    else:
        raise TypeError("Incorrect private key path")
    
    return transport

def sftp_connect(transport):
    """Helper function to create an SFTP connection from an SSH connection.

    Once a connection is established, a user can use conn.get(remotepath)
    or conn.put(localpath, remotepath) to transfer files.
    """
    return paramiko.SFTPClient.from_transport(transport)

def exec_command(transport, command, return_stderr=False):
    """Executes a command on the same server as the provided transport.
    Returns (True, ...) for success and (False, ...) for failure.
    """
    channel = transport.open_session()
    channel.exec_command(command)
    output = channel.makefile('rb', -1).readlines()
    if not return_stderr and output:
        return output
    else:
        return channel.makefile_stderr('rb', -1).readlines()

def put_file(transport, local_path, remote_path):
    """Short hand for transmitting a single file"""
    return put_files(transport, [(local_path, remote_path)])

def put_files(transport, paths):
    """Paths is expected to be a list of 2-tuples. The first element is the
    local filepath. Second is the remote path, eg. where you're putting the
    file.

        paths = [('local_file.py', '/var/www/web/local_file.py'),
                 ('/some/where/is/a/file.html', '/var/www/web/file.html')]
    """
    sftp_conn = sftp_connect(transport)
    for (local,remote) in paths:
        sftp_conn.put(local, remote)
    sftp_conn.close()


########NEW FILE########
__FILENAME__ = firepower
import eventlet
import boto
import time
import os
import yaml

from microarmy.communications import (
    ssh_connect,
    exec_command,
    put_file,
)

### Override any defaults in config.py with a local_config.py
from settings import (
    aws_access_key,
    aws_secret_key,
    security_groups,
    key_pair_name,
    num_cannons,
    placement,
    ami_key,
    instance_type,
    enable_cloud_init,
    env_scripts_dir,
    ec2_ssh_username,
)

pool = eventlet.GreenPool()


class UnparsableData(Exception):

    def __init__(self, value):
        self.data = value
    def __str__(self):
        return repr(self.data)

###
### Cannon functions
###

CANNON_INIT_SCRIPT = 'build_cannon.sh'
SIEGE_CONFIG = 'siegerc'
URLS = 'urls.txt'
CLOUD_INIT_DATA ={
    'apt_update': True,
    'packages':['siege'],
        #'python-dev', 'build-essential', 'autoconf', 'automake', 'libtool',
        #'uuid-dev', 'git-core', 'mercurial', 'python-pip'],
    'runcmd': [
        ['bash', '-c', 'echo fs.file-max = 1000000 | tee -a /etc/sysctl.conf'],
        ['bash', '-c', 'echo ' + ec2_ssh_username + '  soft  nofile  1000000 | tee -a /etc/security/limits.conf'],
        ['bash', '-c', 'echo ' + ec2_ssh_username + '  hard  nofile  1000000 | tee -a /etc/security/limits.conf'],
        ['sysctl', '-n', '-p'],
    ]
}

def _prepare_user_data():
    '''if cloud-init is enabled, return formatted user-data variable.'''
    if enable_cloud_init:
        return '#cloud-config\n' + yaml.dump(CLOUD_INIT_DATA)
    else:
        return None


def init_cannons():
    """Creates the ec2 instances and returns a list of publicly accessible
    dns names, mapped to each instance.
    """
    ec2_conn = boto.connect_ec2(aws_access_key, aws_secret_key)

    ### Track down an image for our AMI
    images = ec2_conn.get_all_images(ami_key)
    image = images[0]

    ### if cloud-init is enabled, prepare yaml for user-data
    user_data = _prepare_user_data()

    ### Will need unbuffered output
    print 'Deploying cannons...\n',

    ### Display yaml sent to user-data
    if user_data:
        print 'cloud-init configuration sent to EC2 API:\n' + user_data

    ### Create n instances
    try:
        r = image.run(min_count=num_cannons,
                      max_count=num_cannons,
                      placement=placement,
                      security_groups=security_groups,
                      key_name=key_pair_name,
                      instance_type=instance_type,
                      user_data=user_data)
    except boto.exception.EC2ResponseError, e:
        print 'ERROR: Deploy failed: %s' % e
        return

    hosts = []
    running = False
    while not running:
        time.sleep(5)
        [i.update() for i in r.instances]
        status = [i.state for i in r.instances]
        if status.count('running') == len(r.instances):
            running = True
            print 'Done!'
            for i in r.instances:
                if not i.tags:
                    ec2_conn.create_tags([i.id], {'microarmy': '1'})
                hosts.append((i.id, i.public_dns_name))
    print 'Hosts config:', hosts
    return hosts

def find_deployed_cannons():
    """Find all cannons deployed for our purposes"""
    ec2_conn = boto.connect_ec2(aws_access_key, aws_secret_key)

    reservations = ec2_conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]

    hosts = []
    for i in instances:
        if not i.tags:
            continue
        else:
            if 'microarmy' in i.tags and i.state == 'running':
                hosts.append((i.id, i.public_dns_name))

    return hosts

def destroy_deployed_cannons():
    """Find and destroy all our deployed cannons"""
    hosts = find_deployed_cannons()
    terminate_cannons([h[0] for h in hosts])

def terminate_cannons(host_ids):
    """
    """
    ec2_conn = boto.connect_ec2(aws_access_key, aws_secret_key)
    ec2_conn.terminate_instances(host_ids)

def reboot_cannons(host_ids):
    """
    """
    ec2_conn = boto.connect_ec2(aws_access_key, aws_secret_key)
    ec2_conn.reboot_instances(host_ids)

def _setup_a_cannon(hostname):
    """Connects to the hostname and installs all the tools required for the
    load test.

    Returns a boolean for successful setup.
    """
    ssh_conn = ssh_connect(hostname)
    
    # copy script to cannon and make it executable
    script_path = env_scripts_dir + '/' + CANNON_INIT_SCRIPT
    put_file(ssh_conn, script_path, CANNON_INIT_SCRIPT)
    response = exec_command(ssh_conn, 'chmod 755 ~/%s' % CANNON_INIT_SCRIPT)
    if response: # response would be error output
        print 'Unable to chmod cannon script: %s' % (CANNON_INIT_SCRIPT)
        print response
        return False

    # execute the setup script (expect this call to take a while)
    response = exec_command(ssh_conn, 'sudo ./%s' % CANNON_INIT_SCRIPT)
    return (hostname, response)    

def _setup_siege_config(hostname):
    """Connects to the hostname and configures siege

    """
    ssh_conn = ssh_connect(hostname)

    script_path = env_scripts_dir + '/' + SIEGE_CONFIG
    put_file(ssh_conn, script_path, '.siegerc')

def _setup_siege_urls(hostname):
    """Connects to the hostname and configures siege

    """
    ssh_conn = ssh_connect(hostname)

    script_path = env_scripts_dir + '/' + URLS
    put_file(ssh_conn, script_path, 'urls.txt')

def setup_cannons(hostnames):
    """Launches a coroutine to configure each host and waits for them to
    complete before compiling a list of responses
    """
    print '  Loading cannons... ',
    pile = eventlet.GreenPile(pool)
    for h in hostnames:
        pile.spawn(_setup_a_cannon, h)
    responses = list(pile)
    print 'Done!'
    return responses

def setup_siege(hostnames):
    """Launches a coroutine to write a siege config based on user input."""
    print '  Configuring siege... ',
    pile = eventlet.GreenPile(pool)
    for h in hostnames:
        pile.spawn(_setup_siege_config, h)
    responses = list(pile)
    print 'Done!'
    return responses

def setup_siege_urls(hostnames):
    """Launches a coroutine to write siege urls based on user input."""
    print '  Configuring urls... ',
    pile = eventlet.GreenPile(pool)
    for h in hostnames:
        pile.spawn(_setup_siege_urls, h)
    responses = list(pile)
    print 'Done!'
    return responses

def fire_cannon(cannon_host, target):
    """Handles the details of telling a host to fire"""
    ssh_conn = ssh_connect(cannon_host)

    # check to see if the siege file has been created, if not fire the canon
    # with some reasonable defaults. os.path.expanduser will return the ec2
    # user's homedir, most likely /home/ubuntu
    if os.path.isfile("%s/.siegerc" % (os.path.expanduser('~' + ec2_ssh_username)) ):
        siege_options = '--rc %s/.siegerc' % (os.path.expanduser('~' + ec2_ssh_username))
    else:
        siege_options = '-c200 -t60s'

    # run the siege command
    if target:
        remote_command = 'siege %s %s' % (siege_options, target)
    else:
        remote_command = 'siege %s -f ~/urls.txt' % (siege_options)

    # Siege writes stats to stderr
    response = exec_command(ssh_conn, remote_command, return_stderr=True)
    return response

def slam_host(cannon_hosts, target):
    """Coordinates `cannon_hosts` to use the specified siege coordates on
    `target` and report back the performance.
    """
    pile = eventlet.GreenPile(pool)
    for h in cannon_hosts:
        pile.spawn(fire_cannon, h, target)
    responses = list(pile)

    try:
        report = parse_responses(responses)
    except UnparsableData, e:
        return "Unable to parse data properly: %s" % e

    return report

def parse_responses(responses):
    """Quick and dirty."""
    aggregate_dict = {
        'num_trans': [],
        'elapsed': [],
        'tran_rate': [],
    }

    for response in responses:
        try:
            num_trans = response[4].split('\t')[2].strip()[:-5]
            elapsed = response[6].split('\t')[2].strip()[:-5]
            tran_rate = response[9].split('\t')[1].strip()[:-10]
        except IndexError:
            raise UnparsableData(response)

        aggregate_dict['num_trans'].append(num_trans)
        aggregate_dict['elapsed'].append(elapsed)
        aggregate_dict['tran_rate'].append(tran_rate)

    return aggregate_dict

########NEW FILE########
__FILENAME__ = settings
# Override any keys below by putting them in a local_settings.py. Some
# overrides are required, signaled by a #* on the same line.

import os

### Get these from: http://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key
aws_access_key = None #*
aws_secret_key = None #*

### aws security config
security_groups = None #*

### key pair name
key_pair_name = None #*

### path to ssh private key
### Will resolve ~
ec2_ssh_key = None #*
ec2_ssh_username = 'ubuntu' # ami specific
ec2_ssh_key_password = None # only required if your ssh key is encrypted

### five cannons is a healthy blast
num_cannons = 5

### Availbility zones: http://alestic.com/2009/07/ec2-availability-zones
placement = 'us-east-1a'

### ami key from: http://uec-images.ubuntu.com/releases/11.10/release/
ami_key = 'ami-a7f539ce'
instance_type = 't1.micro'

### enable cloud init, so that a second deploy step is not required
enable_cloud_init = True

### scripts for building environments
env_scripts_dir = os.path.abspath(os.path.dirname('./env_scripts/'))

### Siege config settings
siege_config = {
    'connection': 'close',
    'concurrency': 200,
    'internet': 'true',
    'time': '5M'
}

### Siege urls
# siege_urls = [
#     'http://localhost',
#     'http://localhost/test'
# ]

try:
    from local_settings import *
except:
    pass

########NEW FILE########
