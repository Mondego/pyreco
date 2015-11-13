__FILENAME__ = ec2_info
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get some grains information that is only available in Amazon AWS

Author: Erik Günther, J C Lawrence <claw@kanga.nu>

"""
import logging
import httplib
import socket
import json

# Set up logging
LOG = logging.getLogger(__name__)


def _call_aws(url):
    """
    Call AWS via httplib. Require correct path.
    Host: 169.254.169.254

    """
    conn = httplib.HTTPConnection("169.254.169.254", 80, timeout=1)
    conn.request('GET', url)
    response = conn.getresponse()
    if response.status == 200:
        return response.read()


def _get_ec2_hostinfo(path="", data={}):
    """
    Recursive function that walks the EC2 metadata available to each minion.
    :param path: URI fragment to append to /latest/meta-data/
    :param data: Dictionary containing the results from walking the AWS meta-data

    All EC2 variables are prefixed with "ec2_" so they are grouped as grains and to
    avoid collisions with other grain names.
    """
    for line in _call_aws("/latest/meta-data/%s" % path).split("\n"):
        if line[-1] != "/":
            call_response = _call_aws("/latest/meta-data/%s" % (path + line))
            if call_response is not None:
                data["ec2_" + path.replace("/", "_") + line] = call_response
            else:
                data["ec2_" + path.replace("/", "_")[:-1]] = line
        else:
            _get_ec2_hostinfo(path + line, data=data)


def _get_ec2_additional():
    """
    Recursive call in _get_ec2_hostinfo() does not retrieve some of
    the hosts information like region, availability zone or
    architecture.

    """
    data = _call_aws("/latest/dynamic/instance-identity/document")
    rc = dict()
    for pair in json.loads(data).items ():
        # De-camelcase the keys: availabilityZone -> availability-zone
        key = "".join((("-" + x.lower()) if x.isupper() else x) for x in pair[0])
        rc["ec2_" + key] = pair[1]
    return rc


def ec2_info():
    """
    Collect some extra host information
    """
    try:
        # First check that the AWS magic URL works. If it does
        # we are running in AWS and will try to get more data.
        _call_aws('/')
    except (socket.timeout, socket.error, IOError):
        return {}

    try:
        grains = _get_ec2_additional()
        _get_ec2_hostinfo(data=grains)
        return grains
    except socket.timeout, serr:
        LOG.info("Could not read EC2 data (timeout): %s" % (serr))
        return {}

    except socket.error, serr:
        LOG.info("Could not read EC2 data (error): %s" % (serr))
        return {}

    except IOError, serr:
        LOG.info("Could not read EC2 data (IOError): %s" % (serr))
        return {}

if __name__ == "__main__":
    print ec2_info()

########NEW FILE########
__FILENAME__ = ec2_tags
"""
ec2_tags.py - exports all EC2 tags in an 'ec2_tags' grain

To use it:

  1. Place ec2_tags.py in <salt_root>/_grains/
  2. Make sure boto version >= 2.8.0
  3. There are three ways of supplying AWS credentials used to fetch instance tags:

    i. Define them in AWS_CREDENTIALS below
    ii. Define AWS_ACCESS_KEY and AWS_SECRET_KEY environment variables
    iii. Provide them in the minion config like this:

        ec2_tags:
          aws:
            access_key: ABC123
            secret_key: abc123
    iv. Use IAM roles

  4. Test it

    $ salt '*' saltutil.sync_grains
    $ salt '*' grains.get tags

Author: Emil Stenqvist <emsten@gmail.com>
Licensed under Apache License (https://raw.github.com/saltstack/salt/develop/LICENSE)

(Inspired by https://github.com/dginther/ec2-tags-salt-grain)
"""

import os
import logging
from distutils.version import StrictVersion

import boto.ec2
import boto.utils
import salt.log

log = logging.getLogger(__name__)

AWS_CREDENTIALS = {
    'access_key': None,
    'secret_key': None,
}

def _get_instance_info():
    identity = boto.utils.get_instance_identity()['document']
    return (identity['instanceId'], identity['region'])

def _on_ec2():
    m = boto.utils.get_instance_metadata(timeout=0.1, num_retries=1)
    return len(m.keys()) > 0

def _get_credentials():

    # 1. Get from static AWS_CREDENTIALS
    if AWS_CREDENTIALS['access_key'] and AWS_CREDENTIALS['secret_key']:
        return AWS_CREDENTIALS

    # 2. Get from minion config
    try:
        aws = __opts__.get['ec2_tags']['aws']
        return {
                'access_key': aws['access_key'],
                'secret_key': aws['secret_key'],}
    except (KeyError, NameError):
        pass

    # 3. Get from environment
    access_key = os.environ.get('AWS_ACCESS_KEY') or os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_KEY') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    if access_key and secret_key:
        return {
                'access_key': access_key,
                'secret_key': secret_key,}

    # 4. Leave as None to use roles
    return AWS_CREDENTIALS

def ec2_tags():

    boto_version = StrictVersion(boto.__version__)
    required_boto_version = StrictVersion('2.8.0')
    if boto_version < required_boto_version:
        log.error("%s: installed boto version %s < %s, can't find ec2_tags",
                __name__, boto_version, required_boto_version)
        return None

    if not _on_ec2():
        log.info("%s: not an EC2 instance, skipping", __name__)
        return None

    (instance_id, region) = _get_instance_info()
    credentials = _get_credentials()

    # Connect to EC2 and parse the Roles tags for this instance
    try:
        conn = boto.ec2.connect_to_region(region,
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'])
    except:
        if not (credentials['access_key'] and credentials['secret_key']):
            log.error("%s: no AWS credentials found, see documentation for how to provide them.", __name__)
            return None
        else:
            log.error("%s: invalid AWS credentials found, see documentation for how to provide them.", __name__)
            return None

    tags = {}
    try:
        _tags = conn.get_all_tags(filters={'resource-type': 'instance',
                'resource-id': instance_id})
        for tag in _tags:
            tags[tag.name] = tag.value
    except IndexError, e:
        log.error("Couldn't retrieve instance information: %s", e)
        return None

    return { 'ec2_tags': tags }

if __name__ == '__main__':
    print ec2_tags()

########NEW FILE########
__FILENAME__ = ec2_tag_roles
#!/usr/bin/env python

import os
import socket
import pprint
import boto.ec2
import httplib

def ec2_roles():
    # Get meta-data to determine which availability zone we are in
    httpconn = httplib.HTTPConnection("169.254.169.254", 80, 10 )
    httpconn.request('GET', "/latest/meta-data/placement/availability-zone")
    response = httpconn.getresponse()
    az = response.read()

    # Chop off the AZ letter to get the region
    region = az[:-1]

    # Get the hostname of the instance we're on
    hostname = socket.gethostname()

    # Connect to EC2 and parse the Roles tags for this instance
    conn = boto.ec2.connect_to_region(region, 
    aws_access_key_id='PUTACCESSKEYHERE',
    aws_secret_access_key='PUTSECRETACCESSKEYHERE')
    reservation = conn.get_all_instances(filters={"tag:Name": hostname})[0]
    instance = reservation.instances[0]
    tags = instance.tags.get('Roles','')

    # Initialize grains
    grains={}

    # Fill grains with tags
    grains['ec2_roles'] = tags.split(',')

    return grains

########NEW FILE########
__FILENAME__ = external_ip
# -*- coding: utf-8 -*-
'''
    :codeauthor: Jeff Frost
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    salt.grains.external_ip
    ~~~~~~~~~~~~~~~~~~~~~~~

    Return the external IP address reported by one of the following providers:

        * ipecho.net
        * externalip.net
        * ident.me

    Which ever reports a valid IP first
'''

# Import Python Libs
import contextlib
import socket
import urllib2

# Import salt libs
from salt.utils.validate.net import ipv4_addr as _ipv4_addr


def external_ip():
    '''
    Return the external IP address
    '''
    check_ips = ('http://ipecho.net/plain',
                 'http://api.externalip.net/ip',
                 'http://v4.ident.me')

    for url in check_ips:
        try:
            with contextlib.closing(urllib2.urlopen(url, timeout=3)) as req:
                ip_ = req.read().strip()
                if not _ipv4_addr(ip_):
                    continue
            return {'external_ip': ip_}
        except (urllib2.HTTPError,
                urllib2.URLError,
                socket.timeout):
            continue

    # Return an empty value as a last resort
    return {'external_ip': []}

########NEW FILE########
__FILENAME__ = facter
import salt.utils
import salt.modules.puppet
import salt.modules.cmdmod

import logging
import json

log = logging.getLogger(__name__)

__salt__ = {
    'cmd.run': salt.modules.cmdmod._run_quiet,
    'cmd.run_all': salt.modules.cmdmod._run_all_quiet
}


def _check_facter():
    '''
    Checks if facter is installed.
    '''
    salt.utils.check_or_die('facter')


def facter():
    '''
    Return facter facts as grains.
    '''
    _check_facter()

    grains = {}
    try:
        # -p: load puppet libraries, for puppet specific facts
        # -j: return json data
        output = __salt__['cmd.run']('facter -p -j')
        try:
            facts = json.loads(output)
        except (KeyError, ValueError):
            log.critical('Failed to load json facter data')
            return {}
        for key, value in facts.iteritems():
            # Prefix fact names with 'facter_', so it doesn't
            # conflict with existing or future grain names.
            grain = 'facter_{0}'.format(key)
            grains[grain] = value
        return grains
    except OSError:
        log.critical('Failed to run facter')
        return {}
    return {}

########NEW FILE########
__FILENAME__ = link_contrib
#!/usr/bin/env python
'''
Make developing using salt-contrib easier.

Symlinks the contents of salt-contrib onto other environments
for testing or deployment.  See ``link_contrib.py --help`` for
more info.

Linking against a development repo::

  git clone git://github.com/saltstack/salt.git
  git clone git@github.com:<me>/salt-contrib.git
  
  salt-contrib/link_contrib.py salt
  
  salt/tests/runtests.py -n contrib.tests -v
  
Linking against an actual state env::

  salt_contrib/link_contrib.py /srv/salt
  
Removing links:
  
  salt_contrib/link_contrib.py /srv/salt --uninstall

'''
import os
import logging
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

current_dir = os.path.realpath(os.path.dirname(__file__))

base_folders = ('grains', 'modules', 'renderers', 'runners', 'states')

unsafe_modules = ('ansible','drizzle')

def get_files(target, exclude, folders = base_folders):
    '''
    Returns a list of files to link
    '''
    for dirname, dirnames, filenames in os.walk(current_dir):
        rel = dirname[len(current_dir)+1:]
        parts = rel.split('/')
        
        if len(parts) == 0:
            continue
        
        if not parts[0] in folders:
            continue
        
        # filter out unwanted items
        def f(x):
            if x[:-3] in exclude:
                return False
            if x == '__init__.py':
                return False
            if x[-4:] == '.pyc':
                return False
            return True

        for module in filter(f, filenames):
            yield os.path.join(rel, module)

def link(source, dest):
    '''
    Creates symlinks.
    Also creates directories if required and tries to clean out old links
    '''
    source = os.path.realpath(source)
    
    d = os.path.dirname(dest)
    if not os.path.isdir(d):
        os.makedirs(d)
    
    # remove dead links (e.g. to old salt-contrib)
    if os.path.islink(dest) and os.path.realpath(dest) != source:
        logger.warning("Removing dead link: {0}".format(dest))
        os.unlink(dest)
    
    # link to dest
    if not os.path.islink(dest):
        logger.debug("Linking {0}".format(source))
        try:
            os.symlink(source, dest)
            return True
        except:
            logger.warning("Failed to created {0}".format(dest))
            
    return False
            
def install(target, opts):
    '''
    Link files in current directory to another environment
    for testing / deployment.
    '''
    # figure out what type of install to do
    if os.path.exists(os.path.join(target, 'top.sls')):
        active = True
        logger.info("Linking to active env")
    elif os.path.exists(os.path.join(target, 'salt', '__init__.py')):
        active = False
        logger.info("Linking to development repo")
    else:
        raise Exception("Expected either a top.sls file or a salt module")
    
    exclude = unsafe_modules + tuple(opts.exclude)
    logger.info("Excluding {0}".format(', '.join(exclude)))
    
    # python modules
    count = 0
    for source in get_files(target, exclude):
        if active:
            dest = os.path.join(target, '_{0}'.format(source))
        else:
            dest = os.path.join(target, 'salt', source)
        
        if link(os.path.join(current_dir, source), dest):
            count += 1
            
    sys.stderr.write("Linked {0} items\n".format(count))
    
    if active == False:
        # add the tests as well
        count = 0
        for source in get_files(target, exclude, ('tests',)):
            dest = os.path.join(target, source)
            
            if link(os.path.join(current_dir, source), dest):
                count += 1
                
        sys.stderr.write("Linked {0} test items\n".format(count))
    

def uninstall(target, opts):
    '''
    Finds files in target path linked to the current directory and removes them.
    '''
    count = 0

    for dirname, dirnames, filenames in os.walk(target):
        for filename in ["{0}/{1}".format(dirname, f) for f in filenames]:
            real = os.path.realpath(filename)
            if real.startswith(current_dir):
                logger.debug("Unlinking {0}".format(filename))
                os.unlink(filename)

                # get rid of bytecode
                if os.path.exists(filename + "c"):
                    os.unlink(filename + "c")

                count += 1

    sys.stderr.write("Unlinked {0} items\n".format(count))

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='Path to target, either a salt repo or an sls base')
    parser.add_argument('-u', '--uninstall', action='store_true', help='Remove symlinks from the environment')
    parser.add_argument('-r', '--refresh', action='store_true', help='Remove and re-apply links')
    parser.add_argument('-x', '--exclude', nargs='*', default=[], help='Exclude specific python modules')

    options = parser.parse_args()

    path = os.path.realpath(options.path)

    if options.refresh or options.uninstall:
        uninstall(path, options)
        
    if options.uninstall:
        return

    install(path, options)
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ansmod
"""Salt module that lets you invoke Ansible modules.

Requires Ansible installed on minion servers. (ie, the command:
"python -c 'import ansible'" should be successful)

See http://ansible.github.com/
"""
from __future__ import absolute_import
import os
import re
import logging
import tempfile
import subprocess
from subprocess import PIPE
from string import maketrans

log = logging.getLogger(__name__)

from ansible.utils import parse_json
import ansible.module_common as ans_common
import ansible.constants as ans_consts


# Module configuration. Set these in the minion configuration file.
__opts__ = {
    # Absolute path to the dir containing Ansible modules
    'ansible.modules_dir': ans_consts.DEFAULT_MODULE_PATH
}

__outputter__ = { 'run_mod': 'txt' }

# Path to the dir containing ansible module files.
ANSIBLE_MOD_DIR = '/Users/jkuan/work/ansible/library'

# Only ansible module names matching this pattern will be available in salt.
MOD_NAME_PATTERN = re.compile(r'[a-zA-Z][\w.-]*')

# Table for mapping illegal characters in an ansible module name to legal
# ones for a state function name.
MOD_NAME_TRANS_TABLE = maketrans('. -', '___')

# These are modules are not scripts and are handle specially by ansible.
VIRTUAL_MODS = set("shell fetch raw template".split())

# To keep track of the translated ansible module names and their original forms
STATE_NAMES = {} # { state_name: mod_name }

# These keys will be removed from the state call arguments dict before
# passing it as arguments to an ansible module.
SALT_KEYS = ['__id__', '__sls__', '__env__', 'order', 'name']


def __init__(opts):
    global ANSIBLE_MOD_DIR
    key = 'ansible.modules_dir'
    ANSIBLE_MOD_DIR = opts.get(key, __opts__[key])
    try:
        mods = [ os.path.basename(p) for p in os.listdir(ANSIBLE_MOD_DIR) ]
    except OSError:
        log.error("You might want to set `ansible.modules_dir' to "
                  "an Ansible modules directory in your minion config.")
        raise
    mods = filter(lambda name: \
                MOD_NAME_PATTERN.match(name) and name not in VIRTUAL_MODS,
                mods)
    for i, name in enumerate(mods):
        state = name.translate(MOD_NAME_TRANS_TABLE)
        STATE_NAMES[state] = name


def run(modpath, argline, argdict=None, raise_exc=False):
    """Run an Ansible module given its file path and arguments.

    modpath
      path to the ansible module.

    argline
      the arguments string for the ansible module.

    argdict
      a dict of argname=value that will be appended to argline.

    CLI Example::

    salt '*' ansmod.run /path/to/ansible/library/file "path=~/x.out mode=744"

    """
    if argdict:
        args = ' '.join('%s=%s' % (k, str(v)) for k, v in argdict.items())
    else:
        args = ''
    argline = (argline + " " + args).strip()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        with open(modpath) as modfile:
            tmp.write(modfile.read() \
                .replace(ans_common.REPLACER, ans_common.MODULE_COMMON) \
                .replace(ans_common.REPLACER_ARGS, repr(argline))
            )
        tmp.flush()
        os.chmod(tmp.name, 0700)
        proc = subprocess.Popen([tmp.name], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        data, err = proc.communicate(argline)
        if proc.returncode != 0 and raise_exc:
            raise subprocess.CalledProcessError(proc.returncode, modpath, err)
    return data


def _state_func(state, **kws):
    """Map salt state invocation to ansible module invocation."""

    state = kws.pop('fun')
    if __opts__['test']:
        return dict(result=None, changes={}, name=state,
                    comment='test is not supported by Ansible modules!')
    argline = kws.pop('args', '')
    for k in SALT_KEYS:
        del kws[k]

    # detect and translate argument 'name_' into 'name'
    NAME_ARG = 'name_'
    if NAME_ARG in kws:
        kws['name'] = kws[NAME_ARG]
        del kws[NAME_ARG]

    modpath = os.path.join(ANSIBLE_MOD_DIR, STATE_NAMES[state])
    output = parse_json(run(modpath, argline, kws, raise_exc=True))

    ret = dict(name=state, result=False, changes={}, comment='')

    if 'failed' not in output:
        ret['result'] = True
    if state in ('command', 'shell') and output['rc'] != 0:
        ret['result'] = False

    if 'msg' in output:
        ret['comment'] = output['msg']
    elif state in ('command', 'shell') and output['stderr']:
        ret['comment'] = output['stderr']

    if ret.get('changed', True):
        ret['changes'] = dict(ansible=output)
    return ret



########NEW FILE########
__FILENAME__ = awstats
'''
A module for managing awstats web statsicics in static mode

:maintainer: Brent Lambert <brent@enpraxis.net>
:maturity: new
:platform: RedHat, Debian Families
:depends: awstats cron

Assumes that the appropriate web server configuration and access
controls have already been configured. Will generate a script for
updating awstats static files, and will use it with cron to enable 
automatic updates.

'''

from subprocess import Popen, PIPE
import os
import re


# Script for updating awstats static pages

awstats_update = '''#!/bin/bash
SERVER={0}
TARGET_DIR={1}
BUILD_DATE=`date +"%Y-%m"`

{2} -config=$SERVER -update
{3} -config=$SERVER -dir=$TARGET_DIR -month=`date +"%m"` -year=`date +"%Y"` -builddate=$BUILD_DATE
if [ -L $TARGET_DIR/index.html ]
then
  rm -f $TARGET_DIR/index.html
fi
ln -s $TARGET_DIR/awstats.$SERVER.$BUILD_DATE.html $TARGET_DIR/index.html
'''

# Default paths

awstats_scr_path = '/usr/local/bin/awstats_update'
awstats_static = '/usr/share/awstats/tools/awstats_buildstaticpages.pl'
awstats_hourly = '/etc/cron.hourly/awstats'
awstats_daily = '/etc/cron.daily/awstats'


def __virtual__():
    '''
    Only supports RedHat and Debian OS Families for now
    '''
    return 'awstats' if __grains__['os_family'] in ['RedHat', 'Debian'] else False


def _runcmd(cmd):
    '''
    Run a command and return output, any error info and return code
    '''
    child = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = child.communicate()
    return child.returncode, out, err


def _remove(fpath):
    '''
    If a file exist remove it
    '''
    try:
        os.unlink(fpath)
    except OSError, e:
        # Ignore if file does not exist
        if e.errno != 2:
            raise OSError, e


def configure(domain, logfile, period="hourly"):
    '''
    Configure awstats to track a specific domain

    Parameters:

        domain
            The name of the web domain awstats should track
        logfile
            The logfile that contains web data for the above domain
        period
            Either 'hourly' or 'daily'

    CLI Example::

        salt 'server' awstats.configure domain=example.com \
          logfile=/var/log/nginx/access.log \
          period=daily

        salt 'server' awstats.configure domain=example.com \
          logfile=/var/log/httpd/example.com-access_log
    '''
    if domain and logfile:

        # Get OS specific values
        if __grains__['os_family'] == 'RedHat':
            awstats = '/usr/share/awstats/wwwroot/cgi-bin/awstats.pl'
            model = '/etc/awstats/awstats.model.conf'
            tdir = '/var/www/awstats'
        elif __grains__['os_family'] == 'Debian':
            awstats = '/usr/lib/cgi-bin/awstats.pl'
            model = '/etc/awstats/awstats.conf'
            tdir = '/var/awstats'
        else:
            return False

        sd = re.compile('^SiteDomain=.*$', re.MULTILINE)
        lf = re.compile('^LogFile=>*$', re.MULTILINE)
        awconfig = '/etc/awstats/awstats.{0}.conf'.format(domain)

        # Generate a valid awstats configuration file
        with open(model) as f:
            config = f.read()
            config = sd.sub('SiteDomain="{0}"'.format(domain), config)
            config = lf.sub('LogFile="{0}"'.format(logfile), config)
            with open(awconfig, 'w') as f1:
                f1.write(config)

        # Generate an appropriate update script, store in /usr/local/bin
        update = awstats_update.format(domain,
                                       tdir,
                                       awstats,
                                       awstats_static)

        with open(awstats_scr_path, 'w') as f:
            f.write(update)
            os.chmod(awstats_scr_path, 0700)
        
        # Set up cron
        if period == 'hourly':
            if not os.path.exists(awstats_hourly):
                os.symlink(awstats_scr_path, awstats_hourly)
        elif period == 'daily':
            if not os.path.exists(awstats_daily):
                os.symlink(awstats_scr_path, awstats_daily)

        return True

    return False


def disable():
    '''
    Disable automatic updates.

    CLI_Example::
    
        salt 'server' awstats.disable
    '''
    _remove(awstats_hourly)
    _remove(awstats_daily)
    return True


def update():
    '''
    Update awstats immediately.

    CLI_Example::

        salt 'server' awstats.update
    '''
    result = _runcmd(awstats_scr_path)
    if result[0]:
        # We have a return code, must be an error
        return False
    return True
    

########NEW FILE########
__FILENAME__ = aws_elb
#! /usr/bin/env python

import logging, os

try:
  import boto
  has_boto = "aws_elb"
except ImportError:
  has_boto = False

LOG = logging.getLogger (__name__)
AWS_CREDENTIALS = {
  "access_key": None,
  "secret_key": None,
}

def __virtual__ ():
  """Don't load if boto is not available."""
  return has_boto

def _get_credentials ():
  """
  Get AWS credentials:

    1) Hardcoded above in the AWS_CREDENTIALS dictionary.
    2) From the minion config ala:
        ec2_tags:
          aws:
            access_key: ABC123
            secret_key: abc123
    3) From the environment (AWS_ACCESS_KEY and AWS_SECRET_KEY).
    4) From the pillar (AWS_ACCESS_KEY and AWS_SECRET_KEY).

  """
  # 1. Get from static AWS_CREDENTIALS
  if AWS_CREDENTIALS["access_key"] and AWS_CREDENTIALS["secret_key"]:
    return AWS_CREDENTIALS
  try: # 2. Get from minion config
    aws = __opts__.get["ec2_tags"]["aws"]
    return {"access_key": aws["access_key"],
            "secret_key": aws["secret_key"],}
  except (KeyError, NameError, TypeError):
    try: # 3. Get from environment
      access_key = (os.environ.get ("AWS_ACCESS_KEY")
                    or os.environ.get ("AWS_ACCESS_KEY_ID"))
      secret_key = (os.environ.get ("AWS_SECRET_KEY")
                    or os.environ.get ("AWS_SECRET_ACCESS_KEY"))
      if access_key and secret_key:
        return {"access_key": access_key,
                "secret_key": secret_key,}
      raise KeyError
    except (KeyError, NameError):
      try: # 4. Get from pillar
        return {"access_key": __pillar__["AWS_ACCESS_KEY"],
                "secret_key": __pillar__["AWS_SECRET_KEY"],}
      except (KeyError, NameError):
        LOG.error ("No AWS credentials found.")
        return None

def _get_elb (name):
  """Get an ELB by name."""
  credentials = _get_credentials ()
  if not credentials:
    return None
  conn = boto.connect_elb (credentials["access_key"], credentials["secret_key"])
  for lb in conn.get_all_load_balancers ():
    if lb.name == name:
      return lb
  LOG.warning ("Failed to find ELB: %s", name)
  return None

def join (name, instance_id = None):
  """
  Add instance to the given ELB.  Requires 'ec2_instance-id' to be
  given or be part of the minion's grains.

  CLI Example:

    salt '*' aws_elb.join MyLoadBalancer-Production

    salt '*' aws_elb.join MyLoadBalancer-Production i-89393af9

  """
  if instance_id is None:
    try:
      instance_id = __grains__["ec2_instance-id"]
    except KeyError:
      return False
  lb = _get_elb (name)
  try:
    lb.register_instances ([instance_id,])
  except Exception:
    import traceback
    LOG.error ("ELB %s: Error while registering instance %s", name, instance_id)
    LOG.debug (traceback.format_exc ())
    return False
  LOG.debug ("ELB %s: Added instance %s", name, instance_id)
  return True

def leave (name, instance_id = None):
  """
  Removes instance from the given ELB.  Requires
  'ec2_instance-id' to be given or be part of the minion's grains.

  CLI Example:

    salt '*' aws_elb.leave MyLoadBalancer-Production

    salt '*' aws_elb.leave MyLoadBalancer-Production i-89393af9

  """
  if instance_id is None:
    try:
      instance_id = __grains__["ec2_instance-id"]
    except KeyError:
      return False
  lb = _get_elb (name)
  try:
    lb.deregister_instances ([instance_id,])
  except Exception:
    import traceback
    LOG.error ("ELB %s: Error while deregistering instance %s", name, instance_id)
    LOG.debug (traceback.format_exc ())
    return False
  LOG.debug ("ELB %s: Removed instance %s", name, instance_id)
  return True

if __name__ == "__main__":
  import sys
  logging.basicConfig (level = logging.DEBUG)
  print _get_elb (sys.argv[1])

########NEW FILE########
__FILENAME__ = basicauth
'''
Module for managing basic authentication password files

:maintainer: Brent Lambert <brent@enpraxis.net>
:maturity: new
:platform: Any
:depends: apache
:configuration: The basicauth password file to be managed 
    can be passed directly into the adduser and deleteuser 
    functions, or it can be set in the minion configuration 
    file as follows::

        basicauth.password_file: /etc/httpd/.htpasswd

    It can also be set in pillar data in a similar manner using
    a .sls file. If no options are specified it will be assumed that
    the htpassword file is located at /etc/.htpasswd

This module looks for the binary /usr/bin/htpasswd and will load
if it is found. Normally this binary is included in the apache
package. 

The htpasswd file must exist in order to successfully 
add and delete users. You can create a new empty file as follows::

    touch /etc/.htpasswd

Be sure to set the correct permissions on the file and configure
your web server accordingly. 
'''

from subprocess import Popen, PIPE
import os


def __virtual__():
    '''
    Must have htpasswd installed
    '''
    if os.path.exists('/usr/bin/htpasswd'):
        return 'basicauth'
    return False


def _runcmd(cmd):
    '''
    Run a command and return output, any error info and return code
    '''
    child = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = child.communicate()
    return child.returncode, out, err


def _getPasswordFile(path):
    '''
    Get the full path of the password file
    '''
    if path:
        # path has priority
        return path  
    elif __salt__['config.option']('basicauth.password_file'):
        # Module configuration next
        return __salt__['config.option']('basicauth.password_file')
    elif __pillar__.has_key('basicauth.password_file'):
        # look for pillar data
        return __pillar__['basicauth.password_file']
    else:
        # Specify some default neutral location
        return '/etc/.htpasswd'
    return ''


def adduser(user, passwd, path=None):
    '''
    Add a user and password to the htpasswd file. Password file must 
    already exist. Password file creation can be handled via states 
    or manually to handle permissions and ownership for specific use 
    cases. 

    Note:: Uses the -b option that passes a password via the command 
       line. Unfortunately this is necessary in order to set the 
       password in a non interactive manner. This is not generally 
       recommended and has security implications. Make sure you 
       understand these before you use this function.

    CLI_Example::

        salt 'server' basicauth.adduser bob test1234

        salt 'server' basicauth.adduser bob test1234 \
          /etc/httpd/.htpasswd
    '''
    if user and passwd:
        htpath = _getPasswordFile(path)
        cmd = '/usr/bin/htpasswd -b {0} {1} {2}'.format(htpath, 
                                                        user, 
                                                        passwd)
        result = _runcmd(cmd)
        if result[0] == 0:
            return True
    return False


def deleteuser(user, path=None):
    '''
    Delete user from the password file

    CLI_Example::

        salt 'server' basicauth.deleteuser bob

        salt 'server' basicauth.deleteuser bob /etc/.htpasswd
    '''
    if user:
        htpath = _getPasswordFile(path)
        cmd = '/usr/bin/htpasswd -D {0} {1}'.format(htpath, user)
        result = _runcmd(cmd)
        if result[0] == 0:
            return True
    return False

########NEW FILE########
__FILENAME__ = circus
"""
Support for Circus: process and socket manager.

:maintainer: Marconi Moreto <caketoad@gmail.com>
:maturity:   new
:platform:   all
"""

import salt.utils


@salt.utils.memoize
def __detect_os():
    return salt.utils.which('circusctl')


def __virtual__():
    """
    Only load the module if circus is installed.
    """
    return 'circus' if __detect_os() else False


def version():
    """
    Return circus version from circusctl --version

    CLI Example::

        salt '*' circus.version
    """
    cmd = '{0} --version'.format(__detect_os())
    out = __salt__['cmd.run'](cmd)
    return out.split(' ')[1]


def list(watcher=None):
    """
    Return list of watchers or active processes in a watcher.

    CLI Example::

        salt '*' circus.list
    """
    return _list(watcher)


def _list(watcher):
    arguments = '{0}'.format(watcher) if watcher else ''
    cmd = '{0} list {1}'.format(__detect_os(), arguments)
    return __salt__['cmd.run'](cmd).split(',')


def dstats():
    """
    Return statistics of circusd.

    CLI Example::

        salt '*' circus.dstats
    """
    cmd = '{0} dstats'.format(__detect_os())
    return __salt__['cmd.run'](cmd)


def stats(watcher=None, pid=None):
    """
    Return statistics of processes.

    CLI Example::

        salt '*' circus.stats mywatcher
    """
    if watcher and pid:
        arguments = '{0} {1}'.format(watcher, pid)
    elif watcher and not pid:
        arguments = '{0}'.format(watcher)
    else:
        arguments = ''

    cmd = '{0} stats {1}'.format(__detect_os(), arguments)
    out = __salt__['cmd.run'](cmd).splitlines()

    # return immediately when looking for specific process
    if pid:
        return out

    processes = _list(None)
    processes_dict = {}
    current_process = None
    for line in out:
        for process in processes:
            if process in line:
                processes_dict[process] = []
                current_process = process
        if current_process not in line:
            processes_dict[current_process].append(line)
    return processes_dict


def status(watcher=None):
    """
    Return status of a watcher or all watchers.

    CLI Example::

        salt '*' circus.status mywatcher
    """
    if watcher:
        arguments = ' status {0}'.format(watcher)
    else:
        arguments = ' status'

    cmd = __detect_os() + arguments
    out = __salt__['cmd.run'](cmd).splitlines()
    return dict([line.split(':') for line in out])


def signal(signal, opts=None):
    """
    Signals circus to start, stop, or restart.

    CLI Example::

        salt '*' circus.signal restart myworker
    """
    valid_signals = ('start', 'stop', 'restart', 'reload', 'quit')

    if signal not in valid_signals:
        return

    if opts:
        arguments = ' {0} {1}'.format(signal, opts)
    else:
        arguments = ' {0}'.format(signal)

    cmd = __detect_os() + arguments
    return __salt__['cmd.run'](cmd)

########NEW FILE########
__FILENAME__ = drizzle
'''
Drizzle is a MySQL fork optimized for Net and Cloud performance.
This module provides Drizzle compatibility to Salt execution

:Depends: MySQLdb python module
:Configuration: The following changes are to be made in
                /etc/salt/minion on respective minions

Example::
    drizzle.host: '127.0.0.1'
    drizzle.port: 4427
    drizzle.user: 'root'
    drizzle.passwd: ''
    drizzle.db: 'drizzle'

Configuration file can also be included such as::
    drizzle.default_file: '/etc/drizzle/config.cnf'
'''

# Importing the required libraries
import re
import salt.utils

try:
    import MySQLdb
    import MySQLdb.cursors
    has_mysqldb = True
except ImportError:
    has_mysqldb = False

# Salt Dictionaries
__outputter__ = {
    'ping': 'txt',
    'status': 'yaml',
    'version': 'yaml',
    'schemas': 'yaml',
    'schema_exists': 'txt',
    'schema_create': 'txt',
    'schema_drop': 'txt',
    'tables': 'yaml',
    'table_find': 'yaml',
    'query': 'txt'
}
__opts__ = __salt__['test.get_opts']()


# Check for loading the module
def __virtual__():
    '''
    This module is loaded only if the
    database and the libraries are present
    '''

    # Finding the path of the binary
    has_drizzle = False
    if salt.utils.which('drizzle'):
        has_drizzle = True

    # Determining load status of module
    if has_mysqldb and has_drizzle:
        return 'drizzle'
    return False


# Helper functions
def _connect(**dsn):
    '''
    This method is used to establish a connection
    and returns the connection
    '''

    # Initializing the required variables
    dsn_url = {}
    parameter = ['host', 'user', 'passwd', 'db', 'port']

    # Gathering the dsn information
    for param in parameter:
        if param in dsn:
            dsn_url[param] = dsn[param]
        else:
            dsn_url[param] = __opts__['drizzle.{0}'.format(param)]
    # Connecting to Drizzle!
    drizzle_db = MySQLdb.connect(**dsn_url)
    drizzle_db.autocommit(True)
    return drizzle_db


# Server functions
def status():
    '''
    Show the status of the Drizzle server
    as Variable_name and Value

    CLI Example::

        salt '*' drizzle.status
    '''

    # Initializing the required variables
    ret_val = {}
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Fetching status
    cursor.execute('SHOW STATUS')
    for iter in range(cursor.rowcount):
        status = cursor.fetchone()
        ret_val[status[0]] = status[1]

    cursor.close()
    drizzle_db.close()
    return ret_val


def version():
    '''
    Returns the version of Drizzle server
    that is running on the minion

    CLI Example::

        salt '*' drizzle.version
    '''

    drizzle_db = _connect()
    cursor = drizzle_db.cursor(MySQLdb.cursors.DictCursor)

    # Fetching version
    cursor.execute('SELECT VERSION()')
    version = cursor.fetchone()

    cursor.close()
    drizzle_db.close()
    return version


# Database functions
def schemas():
    '''
    Displays the schemas which are already
    present in the Drizzle server

    CLI Example::

        salt '*' drizzle.schemas
    '''

    # Initializing the required variables
    ret_val = {}
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Retriving the list of schemas
    cursor.execute('SHOW SCHEMAS')
    for iter, count in zip(range(cursor.rowcount),range(1,cursor.rowcount+1)):
        schema = cursor.fetchone()
        ret_val[count] = schema[0]

    cursor.close()
    drizzle_db.close()
    return ret_val


def schema_exists(schema):
    '''
    This method is used to find out whether
    the given schema already exists or not

    CLI Example::

        salt '*' drizzle.schema_exists
    '''

    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Checking for existance
    cursor.execute('SHOW SCHEMAS LIKE "{0}"'.format(schema))
    cursor.fetchall()
    if cursor.rowcount == 1:
        return True
    return False


def schema_create(schema):
    '''
    This method is used to create a schema.
    It takes the name of the schema as argument

    CLI Example::

        salt '*' drizzle.schema_create schema_name
    '''

    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Creating schema
    try:
        cursor.execute('CREATE SCHEMA {0}'.format(schema))
    except MySQLdb.ProgrammingError:
        return 'Schema already exists'

    cursor.close()
    drizzle_db.close()
    return True


def schema_drop(schema):
    '''
    This method is used to drop a schema.
    It takes the name of the schema as argument.

    CLI Example::

        salt '*' drizzle.schema_drop schema_name
    '''

    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Dropping schema
    try:
        cursor.execute('DROP SCHEMA {0}'.format(schema))
    except MySQLdb.OperationalError:
        return 'Schema does not exist'

    cursor.close()
    drizzle_db.close()
    return True


def tables(schema):
    '''
    Displays all the tables that are
    present in the given schema

    CLI Example::

        salt '*' drizzle.tables schema_name
    '''

    # Initializing the required variables
    ret_val = {}
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Fetching tables
    try:
        cursor.execute('SHOW TABLES IN {0}'.format(schema))
    except MySQLdb.OperationalError:
        return 'Unknown Schema'

    for iter,count in zip(range(cursor.rowcount),range(1,cursor.rowcount+1)):
        table = cursor.fetchone()
        ret_val[count] = table[0]

    cursor.close()
    drizzle_db.close()
    return ret_val


def table_find(table_to_find):
    '''
    Finds the schema in which the
    given table is present

    CLI Example::

        salt '*' drizzle.table_find table_name
    '''

    # Initializing the required variables
    ret_val = {}
    count = 1
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Finding the schema
    schema = schemas()
    for schema_iter in schema.iterkeys():
        table = tables(schema[schema_iter])
        for table_iter in table.iterkeys():
            if table[table_iter] == table_to_find:
                ret_val[count] = schema[schema_iter]
                count = count+1

    cursor.close()
    drizzle_db.close()
    return ret_val


# Plugin functions
def plugins():
    '''
    Fetches the plugins added to the database server

    CLI Example::

        salt '*' drizzle.plugins
    '''

    # Initializing the required variables
    ret_val = {}
    count = 1
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()

    # Fetching the plugins
    query = 'SELECT PLUGIN_NAME FROM DATA_DICTIONARY.PLUGINS WHERE IS_ACTIVE LIKE "YES"'
    cursor.execute(query)
    for iter,count in zip(range(cursor.rowcount),range(1,cursor.rowcount+1)):
        table = cursor.fetchone()
        ret_val[count] = table[0]

    cursor.close()
    drizzle_db.close()
    return ret_val

#TODO: Needs to add plugin_add() and plugin_remove() methods.
#      However, only some of the plugins are dynamic at the moment.
#      Remaining plugins need the server to be restarted.
#      Hence, these methods can be hacked in the future!


# Query functions
def query(schema, query):
    '''
    Query method is used to issue any query to the database.
    This method also supports multiple queries.

    CLI Example::

        salt '*' drizzle.query test_db 'select * from test_table'
        salt '*' drizzle.query test_db 'insert into test_table values (1,"test1")'
    '''

    # Initializing the required variables
    ret_val = {}
    result = {}
    drizzle_db = _connect()
    cursor = drizzle_db.cursor()
    columns = ()
    rows = ()
    tuples = {}
    queries = []
    _entry = True

    # Support for mutilple queries
    queries = query.split(";")

    # Using the schema
    try:
        cursor.execute('USE {0}'.format(schema))
    except MySQLdb.Error:
        return 'check your schema'

    # Issuing the queries
    for issue in queries:
        try:
            rows_affected = cursor.execute(issue)
        except MySQLdb.Error:
            return 'Error in your SQL statement'

        # Checking whether the query is a SELECT
        if re.search(r'\s*select',issue) is None:
            result['Rows affected:'] = rows_affected
            ret_val[issue.lower()] = result
            result = {}
            continue

        # Fetching the column names
        if _entry:
            attributes = cursor.description
            for column_names in attributes:
                columns += (column_names[0],)
            _entry = False
        result['columns'] = columns

        # Fetching the tuples
        count = 1
        for iter in range(cursor.rowcount):
            row = cursor.fetchone()
            result['row{0}'.format(count)] = row
            count += 1
        result['Rows selected:'] = count-1
        ret_val[issue.lower()] = result
        result = {}

    return ret_val


def ping():
    '''
    Checks whether Drizzle module is loaded or not
    '''
    return True

########NEW FILE########
__FILENAME__ = fahclient
'''
Support for FAHClient
'''

import os
import salt.utils

def __virtual__():
    '''
    Only load the module if FAHClient is installed
    '''
    if salt.utils.which('FAHClient'):
        return 'fahclient'
    return False


def version():
    '''
    Return FAHClient version
    
    CLI Example::

        salt '*' fahclient.version
    '''
    cmd = 'FAHClient --version'
    ret = __salt__['cmd.run'](cmd)
    return ret


def user(name):
    '''
    Configure FAHClient username
    
    CLI Example::

        salt '*' fahclient.username <username>
    '''
    filename = '/etc/fahclient/config.xml'
    if os.path.exists(filename):
        __salt__['file.sed'](filename, '<user value=".*"/>', 
            '<user value="{0}"/>'.format(name))
    return name
    

def team(team):
    '''
    Configure FAHClient team
    
    CLI Example::

        salt '*' fahclient.team <team number>
    '''
    filename = '/etc/fahclient/config.xml'
    if os.path.exists(filename):
        __salt__['file.sed'](filename, '<team value=".*"/>', 
            '<team value="{0}"/>'.format(team))
    return team


def passkey(passkey):
    '''
    Configure FAHClient passkey
    
    CLI Example::
    
        salt '*' fahclient.passkey <passkey>
    '''
    filename = '/etc/fahclient/config.xml'
    if os.path.exists(filename):
        __salt__['file.sed'](filename, '<passkey value=".*"/>', 
            '<passkey value="{0}"/>'.format(passkey))
    return passkey


def power(power):
    '''
    Configure FAHClient power setting
    
    CLI Example::
    
        salt '*' fahclient.power [<off>|<idle light>|<idle>|<light>|<medium>|<full>]
    '''
    filename = '/etc/fahclient/config.xml'
    if os.path.exists(filename):
        __salt__['file.sed'](filename, '<power value=".*"/>', 
            '<power value="{0}"/>'.format(power))
    return power


def start():
    '''
    Start the FAHClient
    
    CLI Example::

	    salt '*' fahclient.start
    '''
    ret = __salt__['service.start']('FAHClient')
    return ret


def stop():
    '''
    Stop the FAHClient
    
    CLI Example::

        salt '*' fahclient.stop
    '''
    ret = __salt__['service.stop']('FAHClient')
    return ret


def restart():
    '''
    Restart the FAHClient
    
    CLI Example::

        salt '*' fahclient.restart
    '''
    ret = __salt__['service.restart']('FAHClient')
    return ret


def reload():
    '''
    Restart the FAHClient
    
    CLI Example::

        salt '*' fahclient.reload
    '''
    ret = __salt__['service.reload']('FAHClient')
    return ret


def status():
    '''
    Restart the FAHClient
    
    CLI Example::

        salt '*' fahclient.status
    '''
    ret = __salt__['service.status']('FAHClient')
    return ret

########NEW FILE########
__FILENAME__ = flup_fcgi_client
#!/usr/bin/env python
# pylint: disable=W0622

# Copyright (c) 2006 Allan Saddi <allan@saddi.com>
# Copyright (c) 2011 Vladimir Rusinov <vladimir@greenmice.info>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# $Id$

__author__ = 'Allan Saddi <allan@saddi.com>'
__version__ = '$Revision$'

import select  # @UnresolvedImport
import struct
import socket
import errno
import types

__all__ = ['FCGIApp']

# Constants from the spec.
FCGI_LISTENSOCK_FILENO = 0

FCGI_HEADER_LEN = 8

FCGI_VERSION_1 = 1

FCGI_BEGIN_REQUEST = 1
FCGI_ABORT_REQUEST = 2
FCGI_END_REQUEST = 3
FCGI_PARAMS = 4
FCGI_STDIN = 5
FCGI_STDOUT = 6
FCGI_STDERR = 7
FCGI_DATA = 8
FCGI_GET_VALUES = 9
FCGI_GET_VALUES_RESULT = 10
FCGI_UNKNOWN_TYPE = 11
FCGI_MAXTYPE = FCGI_UNKNOWN_TYPE

FCGI_NULL_REQUEST_ID = 0

FCGI_KEEP_CONN = 1

FCGI_RESPONDER = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER = 3

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN = 1
FCGI_OVERLOADED = 2
FCGI_UNKNOWN_ROLE = 3

FCGI_MAX_CONNS = 'FCGI_MAX_CONNS'
FCGI_MAX_REQS = 'FCGI_MAX_REQS'
FCGI_MPXS_CONNS = 'FCGI_MPXS_CONNS'

FCGI_Header = '!BBHHBx'
FCGI_BeginRequestBody = '!HB5x'
FCGI_EndRequestBody = '!LB3x'
FCGI_UnknownTypeBody = '!B7x'

FCGI_BeginRequestBody_LEN = struct.calcsize(FCGI_BeginRequestBody)
FCGI_EndRequestBody_LEN = struct.calcsize(FCGI_EndRequestBody)
FCGI_UnknownTypeBody_LEN = struct.calcsize(FCGI_UnknownTypeBody)

if __debug__:
    import time

    # Set non-zero to write debug output to a file.
    DEBUG = 0
    DEBUGLOG = '/tmp/fcgi_app.log'

    def _debug(level, msg):
        # pylint: disable=W0702
        if DEBUG < level:
            return

        try:
            f = open(DEBUGLOG, 'a')
            f.write('%sfcgi: %s\n' % (time.ctime()[4:-4], msg))
            f.close()
        except:
            pass


def decode_pair(s, pos=0):
    """
    Decodes a name/value pair.

    The number of bytes decoded as well as the name/value pair
    are returned.
    """
    nameLength = ord(s[pos])
    if nameLength & 128:
        nameLength = struct.unpack('!L', s[pos:pos + 4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    valueLength = ord(s[pos])
    if valueLength & 128:
        valueLength = struct.unpack('!L', s[pos:pos + 4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    name = s[pos:pos + nameLength]
    pos += nameLength
    value = s[pos:pos + valueLength]
    pos += valueLength

    return (pos, (name, value))


def encode_pair(name, value):
    """
    Encodes a name/value pair.

    The encoded string is returned.
    """
    nameLength = len(name)
    if nameLength < 128:
        s = chr(nameLength)
    else:
        s = struct.pack('!L', nameLength | 0x80000000L)

    valueLength = len(value)
    if valueLength < 128:
        s += chr(valueLength)
    else:
        s += struct.pack('!L', valueLength | 0x80000000L)

    return s + name + value


class Record(object):
    """
    A FastCGI Record.

    Used for encoding/decoding records.
    """

    def __init__(self, typ=FCGI_UNKNOWN_TYPE, requestId=FCGI_NULL_REQUEST_ID):
        self.version = FCGI_VERSION_1
        self.type = typ
        self.requestId = requestId
        self.contentLength = 0
        self.paddingLength = 0
        self.contentData = ''

    def _recvall(sock, length):
        """
        Attempts to receive length bytes from a socket, blocking if necessary.
        (Socket may be blocking or non-blocking.)
        """
        dataList = []
        recvLen = 0
        while length:
            try:
                data = sock.recv(length)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([sock], [], [])
                    continue
                else:
                    raise
            if not data:  # EOF
                break
            dataList.append(data)
            dataLen = len(data)
            recvLen += dataLen
            length -= dataLen
        return ''.join(dataList), recvLen
    _recvall = staticmethod(_recvall)

    def read(self, sock):
        """Read and decode a Record from a socket."""
        try:
            header, length = self._recvall(sock, FCGI_HEADER_LEN)
        except:
            raise EOFError

        if length < FCGI_HEADER_LEN:
            raise EOFError

        self.version, self.type, self.requestId, self.contentLength, \
                      self.paddingLength = struct.unpack(FCGI_Header, header)

        if __debug__:
            _debug(9, 'read: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))

        if self.contentLength:
            try:
                self.contentData, length = self._recvall(sock,
                                                         self.contentLength)
            except:
                raise EOFError

            if length < self.contentLength:
                raise EOFError

        if self.paddingLength:
            try:
                self._recvall(sock, self.paddingLength)
            except:
                raise EOFError

    def _sendall(sock, data):
        """
        Writes data to a socket and does not return until all the data is sent.
        """
        length = len(data)
        while length:
            try:
                sent = sock.send(data)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([], [sock], [])
                    continue
                else:
                    raise
            data = data[sent:]
            length -= sent
    _sendall = staticmethod(_sendall)

    def write(self, sock):
        """Encode and write a Record to a socket."""
        self.paddingLength = - self.contentLength & 7

        if __debug__:
            _debug(9, 'write: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))

        header = struct.pack(FCGI_Header, self.version, self.type,
                             self.requestId, self.contentLength,
                             self.paddingLength)
        self._sendall(sock, header)
        if self.contentLength:
            self._sendall(sock, self.contentData)
        if self.paddingLength:
            self._sendall(sock, '\x00' * self.paddingLength)


class FCGIApp(object):

    def __init__(self, connect=None, host=None, port=None, filterEnviron=True):
        if host is not None:
            assert port is not None
            connect = (host, port)

        self._connect = connect
        self._filterEnviron = filterEnviron

    def __call__(self, environ, start_response=None):
        # For sanity's sake, we don't care about FCGI_MPXS_CONN
        # (connection multiplexing). For every request, we obtain a new
        # transport socket, perform the request, then discard the socket.
        # This is, I believe, how mod_fastcgi does things...

        sock = self._getConnection()

        # Since this is going to be the only request on this connection,
        # set the request ID to 1.
        requestId = 1

        # Begin the request
        rec = Record(FCGI_BEGIN_REQUEST, requestId)
        rec.contentData = struct.pack(FCGI_BeginRequestBody, FCGI_RESPONDER, 0)
        rec.contentLength = FCGI_BeginRequestBody_LEN
        rec.write(sock)

        # Filter WSGI environ and send it as FCGI_PARAMS
        if self._filterEnviron:
            params = self._defaultFilterEnviron(environ)
        else:
            params = self._lightFilterEnviron(environ)
        # TODO: Anything not from environ that needs to be sent also?
        self._fcgiParams(sock, requestId, params)
        self._fcgiParams(sock, requestId, {})

        # Transfer wsgi.input to FCGI_STDIN
        #content_length = int(environ.get('CONTENT_LENGTH') or 0)
        s = ''
        while True:
            #chunk_size = min(content_length, 4096)
            #s = environ['wsgi.input'].read(chunk_size)
            #content_length -= len(s)
            rec = Record(FCGI_STDIN, requestId)
            rec.contentData = s
            rec.contentLength = len(s)
            rec.write(sock)
            if not s:
                break

        # Empty FCGI_DATA stream
        rec = Record(FCGI_DATA, requestId)
        rec.write(sock)

        # Main loop. Process FCGI_STDOUT, FCGI_STDERR, FCGI_END_REQUEST
        # records from the application.
        result = []
        err = ''
        while True:
            inrec = Record()
            inrec.read(sock)
            if inrec.type == FCGI_STDOUT:
                if inrec.contentData:
                    result.append(inrec.contentData)
                else:
                    # TODO: Should probably be pedantic and no longer
                    # accept FCGI_STDOUT records?"
                    pass
            elif inrec.type == FCGI_STDERR:
                # Simply forward to wsgi.errors
                err += inrec.contentData
                #environ['wsgi.errors'].write(inrec.contentData)
            elif inrec.type == FCGI_END_REQUEST:
                # TODO: Process appStatus/protocolStatus fields?
                break

        # Done with this transport socket, close it. (FCGI_KEEP_CONN was not
        # set in the FCGI_BEGIN_REQUEST record we sent above. So the
        # application is expected to do the same.)
        sock.close()

        result = ''.join(result)

        # Parse response headers from FCGI_STDOUT
        status = '200 OK'
        headers = []
        pos = 0
        while True:
            eolpos = result.find('\n', pos)
            if eolpos < 0:
                break
            line = result[pos:eolpos - 1]
            pos = eolpos + 1

            # strip in case of CR. NB: This will also strip other
            # whitespace...
            line = line.strip()

            # Empty line signifies end of headers
            if not line:
                break

            # TODO: Better error handling
            header, value = line.split(':', 1)
            header = header.strip().lower()
            value = value.strip()

            if header == 'status':
                # Special handling of Status header
                status = value
                if status.find(' ') < 0:
                    # Append a dummy reason phrase if one was not provided
                    status += ' FCGIApp'
            else:
                headers.append((header, value))

        result = result[pos:]

        # Set WSGI status, headers, and return result.
        #start_response(status, headers)
        #return [result]

        return status, headers, result, err

    def _getConnection(self):
        if self._connect is not None:
            # The simple case. Create a socket and connect to the
            # application.
            if isinstance(self._connect, types.StringTypes):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self._connect)
            elif hasattr(socket, 'create_connection'):
                sock = socket.create_connection(self._connect)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(self._connect)
            return sock

        # To be done when I have more time...
        raise NotImplementedError(
            'Launching and managing FastCGI programs not yet implemented')

    def _fcgiGetValues(self, sock, vars):  # @ReservedAssignment
        # Construct FCGI_GET_VALUES record
        outrec = Record(FCGI_GET_VALUES)
        data = []
        for name in vars:
            data.append(encode_pair(name, ''))
        data = ''.join(data)
        outrec.contentData = data
        outrec.contentLength = len(data)
        outrec.write(sock)

        # Await response
        inrec = Record()
        inrec.read(sock)
        result = {}
        if inrec.type == FCGI_GET_VALUES_RESULT:
            pos = 0
            while pos < inrec.contentLength:
                pos, (name, value) = decode_pair(inrec.contentData, pos)
                result[name] = value
        return result

    def _fcgiParams(self, sock, requestId, params):
        #print params
        rec = Record(FCGI_PARAMS, requestId)
        data = []
        for name, value in params.items():
            data.append(encode_pair(name, value))
        data = ''.join(data)
        rec.contentData = data
        rec.contentLength = len(data)
        rec.write(sock)

    _environPrefixes = ['SERVER_', 'HTTP_', 'REQUEST_', 'REMOTE_', 'PATH_',
                        'CONTENT_', 'DOCUMENT_', 'SCRIPT_']
    _environCopies = ['SCRIPT_NAME', 'QUERY_STRING', 'AUTH_TYPE']
    _environRenames = {}

    def _defaultFilterEnviron(self, environ):
        result = {}
        for n in environ.keys():
            for p in self._environPrefixes:
                if n.startswith(p):
                    result[n] = environ[n]
            if n in self._environCopies:
                result[n] = environ[n]
            if n in self._environRenames:
                result[self._environRenames[n]] = environ[n]

        return result

    def _lightFilterEnviron(self, environ):
        result = {}
        for n in environ.keys():
            if n.upper() == n:
                result[n] = environ[n]
        return result
########NEW FILE########
__FILENAME__ = image
'''
Parse EXIF data from images using exiv2
'''

import salt.utils


def __virtual__():
    '''
    Only load the module if bluetooth is installed
    '''
    if salt.utils.which('exiv2'):
        return 'image'
    return False


def exif(image):
    '''
    Parse EXIF data from image file

    CLI Example::

        salt '*' image.exif /path/to/filename.jpg
    '''
    cmd = 'exiv2 {0}'.format(image)
    out = __salt__['cmd.run'](cmd).split('\n')
    ret = {}
    for line in out:
        comps = line.split(':')
        ret[comps[0].strip()] = comps[1].strip()
    return ret


########NEW FILE########
__FILENAME__ = iscsistorage
'''
A module to push the configuration for iSCSI shares to front end servers using
storage pools manged by libvirt.

:maintainer: Brent Lambert <brent@enpraxis.net>
:maturity: new
:depends: libvirt python API
:platform: all
:configuration: Default minion configuration is specified as follows::

    iscsistorage.iqn_base: 2000-01.com.mydomain
    iscsistorage.sip: <IP of your SAN>
    iscsistorage.sport: 3260

'''

import libvirt


# libvirt pool definintion

POOL = '''<pool type="iscsi">
  <name>{0}</name>
  <source>
    <host name="{1}" port="{2}" />
    <device path="{3}" />
  </source>
  <target>
    <path>/dev/disk/by-path</path>
  </target>
</pool>'''

CONNECT = 'qemu:///system'


# Helper functions

def _get_option(opt, kwargs):
    '''
    Return config options for iscsistorage
    '''
    if opt in kwargs:
        return kwargs[opt]
    return __salt__['config.option']('iscsistorage.{0}'.format(opt))


def add(name, **kwargs):
    '''
    Add an iSCSI share to a front end server's storage pool for use
    as a storage volume for a virtual server. The iSCSI target should
    already be created on the SAN and be ready to go.

    You can (and probably should) mount the target as a storage pool on
    all front end servers to facilitate live migration of virtual machines
    using the volume on your SAN. Note that you should never launch multipe
    virtual machines on different front end servers for the same target on
    the SAN, or very bad things will happen.

    name
      Name of the iSCSI target minus the IQN Base (required)

    iqn_base
      Override the iqn_base parameter specified in the minion config
      file (optional)

    sip
      Override the sip parameter specified in the minion config file
      (optional)

    sport
      Override the sport parameter specified in the minion config file
      (optional)

    CLI example::

        salt front* iscsistorage.add mytarget

        salt front* iscsistorage.add mytarget iqn_base=iqn.2000.01.com.altdomain

        salt front* iscsistorage.add mytarget sip=192.168.2.1 sport=43260

    '''
    iqn_base = _get_option('iqn_base', kwargs)
    niqn = '{0}:{1}'.format(iqn_base, name)
    sip = _get_option('sip', kwargs)
    sport = _get_option('sport', kwargs)

    pool_def = POOL.format(name, sip, sport, niqn)
    conn = libvirt.open(CONNECT)
    if conn:
        npool = conn.storagePoolDefineXML(pool_def, 0)
        if npool:
            npool.create(0)
            msg = {'Success': 'Created storage pool'}
        else:
            msg = {'Error': '(libvirt) could not create storage pool'}
    else:
        msg = {'Error': '(libvirt) could not connect'}

    return msg


def delete(name):
    '''
    Delete a storage pool from a front end server using libvirt.
    This will unmount the iSCSI Target from the front end server, but
    will not delete the iSCSI share from the SAN.

    name
      Name of iSCSI target derived from the IQN minus the IQN Base
      (required)


    CLI Example::

        salt front* iscsistorage.delete mytarget

    '''
    conn = libvirt.open(CONNECT)
    if conn:
        pool = conn.storagePoolLookupByName(name)
        if pool:
            if pool.isActive():
                pool.destroy()
            pool.undefine()
            msg = {'Success': 'Storage pool deleted'}
        else:
            msg = {'Error': '(libvirt) Could not delete storage pool'}
    else:
        msg = {'Error': '(libvirt) could not connect'}

    return msg

########NEW FILE########
__FILENAME__ = iscsitarget
'''
Module that provides functions to manipulate iSCSI Enterprise Targets
that are backed by LVM.

:maintainer: Brent Lambert <brent@enpraxis.net>
:maturity: new
:depends:    - iSCSI Enterprise Target (http://iscsitarget.sourceforge.net),
    LVM2
:platform: Linux
:configuration: Default configuration must be specified in the minion
    configuration file. A base IQN that will be used with the logical
    volume name to make a full IQN for the target must be specified. Also
    specify a default volume group that will contain the logical volumes
    created and deleted by this module. And lastly specify the default
    location of the config file for iSCSITarget, so that the module
    can update the static configuration, in case the server is rebooted::

        iscsitarget.iqn_base: 'iqn.2007-12.net.enpraxis'
        iscsitarget.volgroup: 'vg_spare'
        iscsitarget.config: '/etc/iet/ietd.conf'

ToDo::

    - Add function to set iSCSI Target parameters, users, security, etc.

'''

# System Imports
import logging

log = logging.getLogger(__name__)


# Helper functions

def _is_ietd_running():
    '''
    Check if the iSCSI daemon is running
    '''
    # TODO: Make this a virtual function
    cmd = 'pgrep -u root ietd'
    out = __salt__['cmd.run'](cmd)

    if not out:
        log.warn('iSCSI Daemon not running')
        return False

    return True


def _get_new_tid():
    '''
    Get a new Target ID, and make sure it is not in use
    '''
    tid = 1
    with open('/proc/net/iet/volume') as fd_:
        tids = [int(x__.split(' ')[0].split(':')[-1]) for x__ in fd_.readlines() if 'tid:' in x__]

        # Get a new ID based on the max
        # We avoid deleted TIDs as a stale iSCSI client may pick it up
        # If you have lots of TIDs and need to reuse deleted ones you may
        # want to alter this
        if tids:
            tid = max(tids) + 1

    return tid


def _get_tid_from_iqn(iqn):
    '''
    Get a target ID using a full IQN
    '''
    ret = 0
    with open('/proc/net/iet/volume') as fd_:
        lines = fd_.readlines()
        for x__ in lines:
            if iqn in x__:
                ret = int(x__.split(' ')[0].split(':')[-1])
                break
        else:
            log.error('Error: (proc/net/iet/volume) {0} not found'.format(iqn))

    return ret


def _get_volumes(iqn):
    '''
    Get all volumes associated with target
    '''
    with open('/proc/net/iet/volume') as fd_:
        lines = fd_.read()
        if iqn not in lines:
            return []
        config = lines.split(iqn)[-1]
        config = config.split('tid:')[0].split('\n')[1:-1]
        paths = []
        for x__ in config:
            paths.append(x__.split('path:')[-1].rstrip())

    return paths


def _get_params(kwargs):
    '''
    Get config params
    '''
    iqn = _get_param('iqn_base', kwargs)
    vg_ = _get_param('volgroup', kwargs)
    config = _get_param('config', kwargs)
    if 'opt' in kwargs:
        opts = kwargs['opt'].split(',')
    else:
        opts = []

    return iqn, vg_, config, opts


def _get_param(opt, kwargs):
    '''
    Get config option
    '''
    if opt in kwargs:
        return kwargs[opt]
    return __salt__['config.option']('iscsitarget.{0}'.format(opt))


def _rewrite_config(cf_, lines):
    '''
    Rewrite the configuration file
    '''
    cf_.seek(0)
    cf_.write(''.join(lines))
    cf_.truncate()


def _config_add_target(config, tid, fiqn):
    '''
    Add a target to the config file
    '''
    with open(config, 'a') as fd_:
        fd_.write('Target {0} {1}\n'.format(tid, fiqn))


def _config_delete_target(config, fiqn):
    '''
    Delete a target from the config file
    '''
    with open(config, 'r+') as fd_:
        clines = fd_.readlines()
        tgts = [x__ for x__ in range(len(clines)) if clines[x__].lstrip().startswith('Target')]
        # Find the Target
        tgt = [x__ for x__ in tgts if fiqn in clines[x__]]
        if tgt:
            # Delete the whole target
            t__ = tgt[0]
            while True:
                del clines[t__]
                # Delete until the end, or until the next Target definition
                if t__ >= len(clines) or clines[t__].lstrip().startswith('Target'):
                    break

        _rewrite_config(fd_, clines)


def _create_vol(name, size, vg_):
    '''
    Create the logical volume
    '''
    # Would use the lvm.lvcreate command, but it throws away the return
    # code, and it would be dangerous to think you have created a new
    # volume, but instead pass on one that was already created.
    cmd = 'lvcreate -n {0} {1} -L {2}'.format(name, vg_, size)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        log.error('lvcreate({0}) Could not create volume'.format(out))
        return False
    return True


def _delete_vol(name, vg_):
    '''
    Remove the logical volume
    '''
    # Use cmd.retcode to make sure it worked
    cmd = 'lvremove -f /dev/{0}/{1}'.format(vg_, name)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        log.error(
            'lvremove({0}) Could not delete volume /dev/{1}/{2})'.format(
                out, vg_, name
            )
        )
        return False
    return True


def _add_lun(tid, lun, path, iotype='blockio'):
    '''
    Add a LUN to a Target
    '''
    # Attach the logical volume to the target
    cmd = 'ietadm --op new --tid {0} --lun {1} --params Path={2},Type={3}'.format(
        tid, lun, path, iotype)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        log.error('ietadm({0}) Could not attach logical volume to target {1}'.format(
                out, path))
        return False
    return True


def _config_add_lun(config, fiqn, lun, vg_, name, iotype='blockio'):
    '''
    Add a LUN to a Target in the config file. If the Target does not exist
    create config for it.
    '''
    nlun = '\tLun {0} PATH=/dev/{1}/{2},Type={3}\n'.format(lun, vg_, name, iotype)

    with open(config, 'r+') as fd_:
        clines = fd_.readlines()
        tgts = [x__ for x__ in range(len(clines)) if clines[x__].lstrip().startswith('Target')]

        # find the target
        tgt = [x__ for x__ in tgts if fiqn in clines[x__]]
        if tgt:
            t__ = tgt[0] + 1
            while (t__ < len(clines) and clines[t__].lstrip().startswith('Lun')):
                t__ += 1
            clines.insert(t__, nlun)
        else:
            clines.append('Target {0}\n'.format(fiqn))
            clines.append(nlun)

        _rewrite_config(fd_, clines)


def _delete_lun(tid, lun):
    '''
    Delete a LUN from a Target
    '''
    # Remove the LUN from the target
    cmd = 'ietadm --op delete --tid {0} --lun {1}'.format(tid, lun)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        log.error('ietadm({0}) Could not delete LUN {1} on target {2}'.format(out, lun, tid))
        return False
    return True


def _config_delete_lun(config, fiqn, lun, rtarget=False):
    '''
    Delete a LUN configuration from a Target in the config file
    '''
    with open(config, 'r+') as fd_:
        clines = fd_.readlines()
        tgts = [x__ for x__ in range(len(clines)) if clines[x__].lstrip().startswith('Target')]
        # Find the Target
        tgt = [x__ for x__ in tgts if fiqn in clines[x__]]
        if tgt:
            # Delete just the LUN
            t__ = tgt[0] + 1
            while (t__ < len(clines) and clines[t__].lstrip().startswith('Lun')):
                if 'Lun {0}'.format(lun) in clines[t__]:
                    del clines[t__]
                else:
                    t__ += 1

        _rewrite_config(fd_, clines)


def add_target(name, **kwargs):
    '''
    Add an iSCSI target. A target ID will be chosen automatically and
    checked against /proc/net/iet/volume to make sure it is not in use.
    Must provide a name to be used with the IQN base parameter to generate
    a full IQN for use. Optional paramters include iqn_base, volgroup,
    and iet_config. The iqn_base, volgroup and iet_config settings will
    fall back to defaults configured in the minion configuration file if
    not specified on the command line.

    To add an iSCSI target on the SAN, you must first use this function to
    create a target, then add volumes to the target using the add_lun
    function.

    name
      Name of the new target that will be appended to the IQN base (required)

    iqn_base
      Override the default IQN Base parameter in the minion config file
      with this value (optional)

    volgroup
      Override the default volume group specified in the minion config file
      with this value (optionalP

    iet_config
      Override the default location of the ietd.conf file that is specified
      in the minion config file (optional)

    CLI_Examples::

        salt \* iscsitarget.add_target test

        salt \* iscsitarget.add_target test iqn_base=iqn.200i0-01.com.mydomain

        salt \* iscsitarget.add_target test volgroup=vg_storage

        salt \* iscsitarget.add_target test iet_config=/dev/iet/ietd.conf
    '''

    # Check that ietd is running first
    # We do this because if the SAN is running
    # in HA mode, then we only want to make
    # changes on the active SAN
    if not _is_ietd_running():
        return {'Error': '(ietd) ietd not active'}

    # Get Parameters
    iqn_base, vg_, config, opts = _get_params(kwargs)
    fiqn = '{0}:{1}'.format(iqn_base, name)
    tid = _get_new_tid()

    # Create the iscsi target
    cmd = 'ietadm --op new --tid {0} --params Name={1}'.format(tid, fiqn)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        return {
            'Error': 'ietadm({0}) Could not create iSCSI Target {1}'.format(
                out, fiqn
            )
        }

    # Add target to config
    _config_add_target(config, tid, fiqn)

    return name, fiqn


def delete_target(name, **kwargs):
    '''
    A function for deleting an iSCSI target definition. To prevent orphaned
    volumes, all LUNs should be deleted before this function is called. The
    name parameter is required and is the name used in conjunction with the
    IQN Base. Optional parameters are iqn_base, volgroup, iet_config. These
    will be read from the minion configuration file if not provided.

    name
      Name of the target minus the IQN Base (required)

    iqn_base
      Override the IQN Base parameter in the minion config file with this value
      instead (optional)

    volgroup
      Override the volume group specified in the minion config file with this
      value (optional)

    iet_config
      Override the path setting in the minion config file for the location of the
      ietd.conf file (optional)

    CLI Example::

        salt \* iscsitarget.delete_target test

        salt \* iscsitarget.delete_target test iqn_base=iqn-2000-01.com.mydomain

        salt \* iscsitarget.delete_target test volgroup=vg_storage

        salt \* iscsitarget.delete_target test 'iet_config=/etc/iet/ietd.conf'
    '''
    # Check that ietd is running
    # We do this because if the SAN is running
    # in HA mode, then we only want to make
    # changes on the active SAN
    if not _is_ietd_running():
        return 'Error: (ietd) ietd not active'

    # Get parameters
    iqn_base, vg_, config, opts = _get_params(kwargs)
    fiqn = '{0}:{1}'.format(iqn_base, name)
    path = '/dev/{0}/{1}'.format(vg_, name)
    tid = _get_tid_from_iqn(fiqn)
    if not tid:
        return 'Error: (proc/net/iet/volume) {0} not found'.format(fiqn)
    vols = _get_volumes(fiqn)

    # Remove the target
    cmd = 'ietadm --op delete --tid {0}'.format(tid)
    out = __salt__['cmd.retcode'](cmd)
    if out:
        return {
            'Error': 'ietadm({0}) Could not delete target {1}'.format(out, fiqn)
        }

    # Remove the configuration
    _config_delete_target(config, fiqn)

    return {'Success': 'Deleted target {0}'.format(fiqn)}


def add_lun(name, lun, size, **kwargs):
    '''
    Add a LUN to an existing target.

    name
      The name of the iSCSI share minus the IQN (required)

    lun
      The LUN for the new iSCSI share, Must be unique for this target
      (required)

    size
      Size of the share to attach to the LUN (required)

    CLI Example::

        salt '*' iscsirarget.add_lun test 1 10G
    '''

    # Check that ietd is running
    if not _is_ietd_running():
        return {'Error': '(ietd) ietd not active'}

    # Get Parameters
    iqn_base, vg_, config, opts = _get_params(kwargs)
    fiqn = '{0}:{1}'.format(iqn_base, name)
    vn_ = '{0}_{1}'.format(name, lun)
    path = '/dev/{0}/{1}'.format(vg_, vn_)
    tid = _get_tid_from_iqn(fiqn)
    if not tid:
        return {'Error': '(proc/net/iet/volume) {0} not found'.format(fiqn)}

    # Create a logical volume
    if not _create_vol(vn_, size, vg_):
        return {
            'Error': 'Could not create volume {0} in {1}'.format(vn_, vg_)
        }

    # Add to target
    if not _add_lun(tid, lun, path):
        return {
            'Error': 'Could not add lun {0} to target {1}'.format(lun, tid)
        }

    # Update config file
    _config_add_lun(config, fiqn, lun, vg_, name)

    return {'Success': 'Added lun {0} to {1}'.format(lun, vg_)}


def delete_lun(name, lun, **kwargs):
    '''
    Delete a LUN on an existing target

    name
      Name of the target that the LUN is configured in, minus the static IQN portion
      (required)

    lun
      The ID of the LUN in the target to delete (required)

    CLI Example::

        salt \* iscsitarget.delete_lun test 1
    '''

    # Check that ietd is running
    if not _is_ietd_running():
        return {'Error': '(ietd) ietd not active'}

    # Get Parameters
    iqn_base, vg_, config, opts = _get_params(kwargs)
    fiqn = '{0}:{1}'.format(iqn_base, name)
    vn_ = '{0}_{1}'.format(name, lun)
    path = '/dev/{0}/{1}'.format(vg_, vn_)
    tid = _get_tid_from_iqn(fiqn)
    if not tid:
        return {'Error': '(proc/net/iet/volume) {0} not found'.format(fiqn)}

    # Delete from target
    if not _delete_lun(tid, lun):
        return {
            'Error': 'Could not delete lun {0} from target {1}'.format(lun, tid)
        }

    # Update config file
    _config_delete_lun(config, fiqn, lun)

    # Remove logical volume
    if not _delete_vol(vn_, vg_):
        return {
            'Error': 'Could not delete volume {0} from {1}'.format(vn_, vg_)
        }

    return True


def list_volumes():
    '''
    Get iSCSI Target volume information

    CLI Example::

        salt \* iscsitarget.list_volumes
    '''
    # Directly return the contents of the kernel params
    # TODO: Parse the output and make it machine readable
    with open('/proc/net/iet/volume') as fd_:
        return fd_.read()


def list_sessions():
    '''
    Get iSCSI Target session information

    CLI Example::

        salt \* iscsitarget.list_sessions
    '''
    # Directly return the content of the kernel params
    # TODO: Parse the output and make it readable
    with open('/proc/net/iet/session') as fd_:
        return fd_.read()

########NEW FILE########
__FILENAME__ = keystone
'''
Module for handling openstack keystone calls.

:optdepends:    - keystoneclient Python adapter
:configuration: This module is not usable until the following are specified
    either in a pillar or in the minion's config file::

        keystone.user: admin
        keystone.password: verybadpass
        keystone.tenant: admin
        keystone.tenant_id: f80919baedab48ec8931f200c65a50df
        keystone.insecure: False   #(optional)
        keystone.auth_url: 'http://127.0.0.1:5000/v2.0/'
        
        OR (for token based authentication)

        keystone.token: 'ADMIN'
        keystone.endpoint: 'http://127.0.0.1:35357/v2.0'
'''

# Import third party libs
HAS_KEYSTONE = False
try:
    from keystoneclient.v2_0 import client
    from keystoneclient.exceptions import ClientException
    from keystoneclient.exceptions import NotFound
    HAS_KEYSTONE = True
except ImportError:
    pass

def __virtual__():
    '''
    Only load this module if keystone
    is installed on this minion.
    '''
    if HAS_KEYSTONE:
        return 'keystone'
    return False

__opts__ = {}


def auth():
    '''
    Set up keystone credentials.  

    Only intended to be used within Keystone-enabled modules.
    '''
    user = __salt__['config.option']('keystone.user')
    password = __salt__['config.option']('keystone.password')
    tenant = __salt__['config.option']('keystone.tenant')
    tenant_id = __salt__['config.option']('keystone.tenant_id')
    auth_url = __salt__['config.option']('keystone.auth_url')
    insecure = __salt__['config.option']('keystone.insecure')
    token = __salt__['config.option']('keystone.token')
    endpoint = __salt__['config.option']('keystone.endpoint')
    kwargs = {}
    if token:
        kwargs = {
                'token': token,
                'endpoint': endpoint,
                }
    else:
        kwargs = {
                'username': user,
                'password': password,
                'tenant_name': tenant,
                'tenant_id': tenant_id,
                'auth_url': auth_url,
                'insecure': insecure,
                }
    return client.Client(**kwargs)

def ec2_credentials_get(id=None,       # pylint: disable-msg=C0103
                        name=None,
                        access=None):  # pylint: disable-msg=C0103
    '''
    Return ec2_credentials for a user (keystone ec2-credentials-get)

    CLI Examples::

        salt '*' keystone.ec2_credentials_get c965f79c4f864eaaa9c3b41904e67082 access=722787eb540849158668370dc627ec5f
        salt '*' keystone.ec2_credentials_get id=c965f79c4f864eaaa9c3b41904e67082 access=722787eb540849158668370dc627ec5f
        salt '*' keystone.ec2_credentials_get name=nova access=722787eb540849158668370dc627ec5f
    '''
    kstone = auth()
    ret = {}
    if name:
        for user in kstone.users.list():
            if user.name == name:
                id = user.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve user id'}
    if not access:
        return {'Error': 'Access key is required'}
    ec2_credentials = kstone.ec2.get(user_id=id, access=access)
    ret[ec2_credentials.user_id] = {
            'user_id': ec2_credentials.user_id,
            'tenant': ec2_credentials.tenant_id,
            'access': ec2_credentials.access,
            'secret': ec2_credentials.secret,
            }
    return ret


def ec2_credentials_list(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Return a list of ec2_credentials for a specific user (keystone ec2-credentials-list)

    CLI Examples::

        salt '*' keystone.ec2_credentials_list 298ce377245c4ec9b70e1c639c89e654
        salt '*' keystone.ec2_credentials_list id=298ce377245c4ec9b70e1c639c89e654
        salt '*' keystone.ec2_credentials_list name=jack
    '''
    kstone = auth()
    ret = {}
    if name:
        for user in kstone.users.list():
            if user.name == name:
                id = user.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve user id'}
    for ec2_credential in kstone.ec2.list(id):
        ret[ec2_credential.user_id] = {
                'user_id': ec2_credential.user_id,
                'tenant_id': ec2_credential.tenant_id,
                'access': ec2_credential.access,
                'secret': ec2_credential.secret,
                }
    return ret


def endpoint_get(service):
    '''
    Return a specific endpoint (keystone endpoint-get)

    CLI Example::

        salt '*' keystone.endpoint_get ec2
    '''
    kstone = auth()
    return kstone.service_catalog.url_for(service_type=service)


def endpoint_list():
    '''
    Return a list of available endpoints (keystone endpoints-list)

    CLI Example::

        salt '*' keystone.endpoint_list
    '''
    kstone = auth()
    ret = {}
    for endpoint in kstone.endpoints.list():
        ret[endpoint.id] = {
                'id': endpoint.id,
                'region': endpoint.region,
                'adminurl': endpoint.adminurl,
                'internalurl': endpoint.internalurl,
                'publicurl': endpoint.publicurl,
                'service_id': endpoint.service_id,
                }
    return ret


def role_get(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Return a specific roles (keystone role-get)

    CLI Examples::

        salt '*' keystone.role_get c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.role_get id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.role_get name=nova
    '''
    kstone = auth()
    ret = {}
    if name:
        for role in kstone.roles.list():
            if role.name == name:
                id = role.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve role id'}
    role = kstone.roles.get(id)
    ret[role.name] = {
            'id': role.id,
            'name': role.name,
            }
    return ret

def role_create(name):
    '''
    Create a role (keystone role-create)

    CLI Examples::

        salt '*' keystone.role_create name=admin
    '''

    kstone = auth()
    item = kstone.roles.create(
            name=name,
            )
    return role_get(item.id)

def role_delete(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Delete a role (keystone role-delete)

    CLI Examples::

        salt '*' keystone.role_delete c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.role_delete id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.role_delete name=nova
    '''
    kstone = auth()
    if name:
        for role in kstone.roles.list():
            if role.name == name:
                id = role.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve tenant id'}
    kstone.roles.delete(id)
    ret = 'Role ID {0} deleted'.format(id)
    if name:
      ret += ' ({0})'.format(name)
    return ret

def role_list():
    '''
    Return a list of available roles (keystone role-list)

    CLI Example::

        salt '*' keystone.role_list
    '''
    kstone = auth()
    ret = {}
    for role in kstone.roles.list():
        ret[role.name] = {
                'id': role.id,
                'name': role.name,
                }
    return ret


def service_get(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Return a specific services (keystone service-get)

    CLI Examples::

        salt '*' keystone.service_get c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.service_get id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.service_get name=nova
    '''
    kstone = auth()
    ret = {}
    if name:
        for service in kstone.services.list():
            if service.name == name:
                id = service.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve service id'}
    service = kstone.services.get(id)
    ret[service.name] = {
            'id': service.id,
            'name': service.name,
            'type': service.type,
            'description': service.description,
            }
    return ret


def service_list():
    '''
    Return a list of available services (keystone services-list)

    CLI Example::

        salt '*' keystone.service_list
    '''
    kstone = auth()
    ret = {}
    for service in kstone.services.list():
        ret[service.name] = {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'type': service.type,
                }
    return ret


def tenant_get(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Return a specific tenants (keystone tenant-get)

    CLI Examples::

        salt '*' keystone.tenant_get c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.tenant_get id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.tenant_get name=nova
    '''
    kstone = auth()
    ret = {}
    if name:
        for tenant in kstone.tenants.list():
            if tenant.name == name:
                id = tenant.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve tenant id'}
    tenant = kstone.tenants.get(id)
    ret[tenant.name] = {
            'id': tenant.id,
            'name': tenant.name,
            'description': tenant.description,
            'enabled': tenant.enabled,
            }
    return ret

def tenant_create(name, description=None, enabled=True):
    '''
    Create a tenant (keystone tenant-create)

    CLI Examples::

        salt '*' keystone.tenant_create name=admin, description=None, enabled=True
    '''

    kstone = auth()
    item = kstone.tenants.create(
            tenant_name=name,
            description=description,
            enabled=enabled,
            )
    return tenant_get(item.id)

def tenant_delete(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Delete a tenant (keystone tenant-delete)

    CLI Examples::

        salt '*' keystone.tenant_delete c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.tenant_delete id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.tenant_delete name=nova
    '''
    kstone = auth()
    if name:
        for tenant in kstone.tenants.list():
            if tenant.name == name:
                id = tenant.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve tenant id'}
    kstone.tenants.delete(id)
    ret = 'Tenant ID {0} deleted'.format(id)
    if name:
      ret += ' ({0})'.format(name)
    return ret

def tenant_list():
    '''
    Return a list of available tenants (keystone tenants-list)

    CLI Example::

        salt '*' keystone.tenant_list
    '''
    kstone = auth()
    ret = {}
    for tenant in kstone.tenants.list():
        ret[tenant.name] = {
                'id': tenant.id,
                'name': tenant.name,
                'description': tenant.description,
                'enabled': tenant.enabled,
                }
    return ret


def token_get():
    '''
    Return the configured tokens (keystone token-get)

    CLI Example::

        salt '*' keystone.token_get c965f79c4f864eaaa9c3b41904e67082
    '''
    kstone = auth()
    token = kstone.service_catalog.get_token()
    return {
            'id': token['id'],
            'expires': token['expires'],
            'user_id': token['user_id'],
            'tenant_id': token['tenant_id'],
            }


def user_list():
    '''
    Return a list of available users (keystone user-list)

    CLI Example::

        salt '*' keystone.user_list
    '''
    kstone = auth()
    ret = {}
    for user in kstone.users.list():
        ret[user.name] = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'enabled': user.enabled,
                'tenant_id': user.tenantId,
                }
    return ret


def user_get(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Return a specific users (keystone user-get)

    CLI Examples::

        salt '*' keystone.user_get c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.user_get id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.user_get name=nova
    '''
    kstone = auth()
    ret = {}
    if name:
        for user in kstone.users.list():
            if user.name == name:
                id = user.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve user id'}
    user = kstone.users.get(id)
    ret[user.name] = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'enabled': user.enabled,
            'tenant_id': user.tenantId,
            }
    return ret


def user_create(name, password, email, tenant_id=None, enabled=True):
    '''
    Create a user (keystone user-create)

    CLI Examples::

        salt '*' keystone.user_create name=jack password=zero email=jack@halloweentown.org tenant_id=a28a7b5a999a455f84b1f5210264375e enabled=True
    '''
    kstone = auth()
    item = kstone.users.create(
        name=name,
        password=password,
        email=email,
        tenant_id=tenant_id,
        enabled=enabled,
        )
    return user_get(item.id)


def user_delete(id=None, name=None):  # pylint: disable-msg=C0103
    '''
    Delete a user (keystone user-delete)

    CLI Examples::

        salt '*' keystone.user_delete c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.user_delete id=c965f79c4f864eaaa9c3b41904e67082
        salt '*' keystone.user_delete name=nova
    '''
    kstone = auth()
    if name:
        for user in kstone.users.list():
            if user.name == name:
                id = user.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve user id'}
    kstone.users.delete(id)
    ret = 'User ID {0} deleted'.format(id)
    if name:
        ret += ' ({0})'.format(name)
    return ret


def user_update(id=None,        # pylint: disable-msg=C0103
                name=None,
                email=None,
                enabled=None):  # pylint: disable-msg=C0103
    '''
    Update a user's information (keystone user-update)
    The following fields may be updated: name, email, enabled.
    Because the name is one of the fields, a valid user id is required.

    CLI Examples::

        salt '*' keystone.user_update id=c965f79c4f864eaaa9c3b41904e67082 name=newname
        salt '*' keystone.user_update c965f79c4f864eaaa9c3b41904e67082 name=newname email=newemail@domain.com
    '''
    kstone = auth()
    if not id:
        return {'Error': 'Unable to resolve user id'}
    kstone.users.update(user=id, name=name, email=email, enabled=enabled)
    ret = 'Info updated for user ID {0}'.format(id)
    return ret


def user_password_update(id=None,         # pylint: disable-msg=C0103
                         name=None,
                         password=None):  # pylint: disable-msg=C0103
    '''
    Update a user's password (keystone user-password-update)

    CLI Examples::

        salt '*' keystone.user_delete c965f79c4f864eaaa9c3b41904e67082 password=12345
        salt '*' keystone.user_delete id=c965f79c4f864eaaa9c3b41904e67082 password=12345
        salt '*' keystone.user_delete name=nova pasword=12345
    '''
    kstone = auth()
    if name:
        for user in kstone.users.list():
            if user.name == name:
                id = user.id  # pylint: disable-msg=C0103
                continue
    if not id:
        return {'Error': 'Unable to resolve user id'}
    kstone.users.update_password(user=id, password=password)
    ret = 'Password updated for user ID {0}'.format(id)
    if name:
        ret += ' ({0})'.format(name)
    return ret


def user_role_list(user_id=None,
                   tenant_id=None,
                   user_name=None,
                   tenant_name=None):
    '''
    Return a list of available user_roles (keystone user_roles-list)

    CLI Examples::

        salt '*' keystone.user_role_list \
            user_id=298ce377245c4ec9b70e1c639c89e654 \
            tenant_id=7167a092ece84bae8cead4bf9d15bb3b
        salt '*' keystone.user_role_list user_name=admin tenant_name=admin
    '''
    kstone = auth()
    ret = {}
    if user_name:
        for user in kstone.users.list():
            if user.name == user_name:
                user_id = user.id
                continue
    if tenant_name:
        for tenant in kstone.tenants.list():
            if tenant.name == tenant_name:
                tenant_id = tenant.id
                continue
    if not user_id and not tenant_id:
        return {'Error': 'Unable to resolve user or tenant id'}
    try:
        for role in kstone.roles.roles_for_user(user=user_id, tenant=tenant_id):
            ret[role.name] = {
                    'id': role.id,
                    'name': role.name,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    }
    except NotFound:
        return {}

def user_role_add(user_id=None,
                   user_name=None,
                   role_id=None,
                   role_name=None,
                   tenant_id=None,
                   tenant_name=None):
    '''
    Add a role to a user (keystone user_roles-add)

    CLI Examples::

        salt '*' keystone.user_role_add \
            user_id=298ce377245c4ec9b70e1c639c89e654 \
            role_id=298ce377245c4ec9b70e1c639c89e654 \
            tenant_id=7167a092ece84bae8cead4bf9d15bb3b
        salt '*' keystone.user_role_add user_name=admin role_name=admin tenant_name=admin
    '''
    kstone = auth()
    ret = {}
    if user_name:
        for user in kstone.users.list():
            if user.name == user_name:
                user_id = user.id
                continue
    if role_name:
        for role in kstone.roles.list():
            if role.name == role_name:
                role_id = role.id
                continue
    if tenant_name:
        for tenant in kstone.tenants.list():
            if tenant.name == tenant_name:
                tenant_id = tenant.id
                continue
    if not user_id and not tenant_id and not role_id:
        return {'Error': 'Unable to resolve user, role or tenant id'}
    item = kstone.roles.add_user_role(user_id, role_id, tenant_id)
    return user_role_list(user_id = user_id, tenant_id = tenant_id)

def user_role_remove(user_id=None,
                   user_name=None,
                   role_id=None,
                   role_name=None,
                   tenant_id=None,
                   tenant_name=None):
    '''
    Removes a role for a user (keystone user_roles-remove)

    CLI Examples::

        salt '*' keystone.user_role_remove \
            user_id=298ce377245c4ec9b70e1c639c89e654 \
            role_id=298ce377245c4ec9b70e1c639c89e654 \
            tenant_id=7167a092ece84bae8cead4bf9d15bb3b
        salt '*' keystone.user_role_remove user_name=admin role_name=admin tenant_name=admin
    '''
    kstone = auth()
    ret = {}
    if user_name:
        for user in kstone.users.list():
            if user.name == user_name:
                user_id = user.id
                continue
    if role_name:
        for role in kstone.roles.list():
            if role.name == role_name:
                role_id = role.id
                continue
    if tenant_name:
        for tenant in kstone.tenants.list():
            if tenant.name == tenant_name:
                tenant_id = tenant.id
                continue
    if not user_id and not tenant_id and not role_id:
        return {'Error': 'Unable to resolve user, role or tenant id'}
    kstone.roles.remove_user_role(user_id, role_id, tenant_id)
    ret = 'User Role {0} '.format(role_id)
    if role_name:
        ret += '({0} '.format(role_name)
    ret += 'deleted for User {0} '.format(user_id)
    if user_name:
        ret += '({0}) '.format(user_name)
    ret += 'on {0}'.format(tenant_id)
    if tenant_name:
        ret += '({0}) '.format(tenant_name)
    return ret

def _item_list():
    '''
    Template for writing list functions
    Return a list of available items (keystone items-list)

    CLI Example::

        salt '*' keystone.item_list
    '''
    kstone = auth()
    ret = []
    for item in kstone.items.list():
        ret.append(item.__dict__)
        #ret[item.name] = {
        #        'id': item.id,
        #        'name': item.name,
        #        }
    return ret


    #The following is a list of functions that need to be incorporated in the
    #keystone module. This list should be updated as functions are added.
    #
    #ec2-credentials-create
    #                    Create EC2-compatibile credentials for user per tenant
    #ec2-credentials-delete
    #                    Delete EC2-compatibile credentials
    #endpoint-create     Create a new endpoint associated with a service
    #endpoint-delete     Delete a service endpoint
    #role-create         Create new role
    #role-delete         Delete role
    #service-create      Add service to Service Catalog
    #service-delete      Delete service from Service Catalog
    #tenant-update       Update tenant name, description, enabled status
    #user-role-add       Add role to user
    #user-role-remove    Remove role from user
    #discover            Discover Keystone servers and show authentication
    #                    protocols and
    #bootstrap           Grants a new role to a new user on a new tenant, after
    #                    creating each.

########NEW FILE########
__FILENAME__ = linux_netconfig
"""
Module to gather network configuration from Linux hosts
"""

import re
import subprocess

def __virtual__():
    """
    Only run on Linux systems
    """
    return 'netconfig' if __grains__['kernel'] == 'Linux' else False

# num name flags extra link addr brd
LINK_MATCHER = re.compile(r"""
    ^
            (?P<num>   [0-9]     +?) :
    \       (?P<name>  [^:]      +?) :
    \      <(?P<flags> [^>]      +?)>  # uppercase, comma-separated list of flags
    \       (?P<extra> .         *?)   # space-separated pairs of "key value"
    \ *\\\ *
    \ *link/(?P<link>  [^ ]      +?)
    \       (?P<addr>  [0-9a-f:] +?)
    \ brd\  (?P<brd>   [0-9a-f:] +?)
    $
    """, re.X | re.M)


# num name type addr brd? scope alias? extra?
ADDR_MATCHER = re.compile(r"""
    ^
             (?P<num>   [0-9]     +?) :
    \        (?P<name>  [^ ]       +)
    \ +
             (?P<type>  [^ ]       +)
    \        (?P<addr>  [^ ]       +)
    (?:
      \ brd\ (?P<brd>   [^ ]       +)
    )?
    \ scope\ (?P<scope> [^ ]       +)
    (?:
      \      (?P<alias> [^\\] [^ ] +)
    )?
    (?:
      \ \\\ +
             (?P<extra> .         *?)
    )?
    $
    """, re.X | re.M)

# addr dev lladdr? state?
NEIGH_MATCHER = re.compile(r"""
    ^
                (?P<addr> [^ ] +)
    \      dev\ (?P<dev>  [^ ] +)
    (?:
      \ lladdr\ (?P<lladdr> [^ ]+)
    )?
    \           (?P<state> [A-Z]+)?
    $
    """, re.X | re.M)



def _int_if_possible(string):
    """
    PRIVATE METHOD
    Tries to convert a string to an integer, falls back to the original value
    """
    try:
        return int(string)
    except ValueError:
        return string

def _dict_from_spaced_kv(string):
    """
    PRIVATE METHOD
    Turns a string "foo bar baz 0 trailing" into {'foo':'bar','baz':0}
    """
    list = string.split(' ')
    return dict([(list[n],_int_if_possible(list[n+1])) for n in range(0,len(list)/2*2,2)])

def _structured_link(match):
    """
    PRIVATE METHOD
    Turns a LINK_MATCHER match into structured data
    """

    res = (match.group('name'), {
        'num':   int(match.group('num')),
        'flags': match.group('flags').split(","),
        'link':  match.group('link'),
        'addr':  match.group('addr'),
        'brd':   match.group('brd') })

    extra = match.group('extra')
    if extra:
        res[1]['settings'] = _dict_from_spaced_kv(extra)

    return res

def _structured_addr(match):
    """
    PRIVATE METHOD
    Turns an ADDR_MATCHER match into structured data
    """

    res = (match.group('name'), {
        'addr':  match.group('addr'),
        'type':  match.group('type'),
        'scope': match.group('scope'),
    })

    brd   = match.group('brd')
    alias = match.group('alias')
    extra = match.group('extra')

    if brd:
        res[1]['brd'] = brd
    if alias:
        res[1]['alias'] = alias
    if extra:
        res[1]['settings'] = _dict_from_spaced_kv(extra)

    return res

def _structured_neigh(match):
    """
    PRIVATE METHOD
    Turns a NEIGH_MATCHER match into structured data
    """
    identifier = (match.group('addr'), match.group('dev'))
    infos = {}
    state  = match.group('state')
    lladdr = match.group('lladdr')
    if state:
        infos['state'] = state
    if lladdr:
        infos['lladdr'] = lladdr
    return identifier, infos

def _structured_links_output(output):
    """
    PRIVATE METHOD
    Return a dictionary mapping link names to link informations from the ip output
    """
    res = {}
    for line in iter(output.splitlines()):
        link_match = LINK_MATCHER.match(line)
        if link_match:
            name, infos = _structured_link(link_match)
            res[name] = infos

    return res

def _structured_addresses_output(output):
    """
    PRIVATE METHOD
    Return a dictionary mapping link names to addresses from the ip output
    """
    res = {}
    for line in iter(output.splitlines()):
        addr_match = ADDR_MATCHER.match(line)
        if addr_match:
            name, infos = _structured_addr(addr_match)
            res.setdefault(name, [])
            res[name].append(infos)

    return res

def _structured_neigh_output(output):
    """
    PRIVATE METHOD
    Return a dictionary mapping address and device to neighborhood information from the ip output
    """
    res = {}
    for line in iter(output.splitlines()):
        neigh_match = NEIGH_MATCHER.match(line)
        if neigh_match:
            identifier, infos = _structured_neigh(neigh_match)
            res[identifier] = infos

    return res

def links():
    """
    Return information about all network links on the system
    """
    output = __salt__['cmd.run']('ip -o link show')
    return _structured_links_output(output)

def link(name):
    """
    Return information about a given network link on the system
    """
    output = __salt__['cmd.run']('ip -o link show {0}'.format(name))
    match = LINK_MATCHER.match(output)
    if match:
        return _structured_link(LINK_MATCHER.match(output))

def addresses_with_options(options):
    """
    Return information about addresses for a given "ip addr show" set of options
    eg netconfig.addresses_with_options 'scope host'
    """
    output = __salt__['cmd.run']('ip -o addr show {0}'.format(options))
    return _structured_addresses_output(output)

def addresses():
    """
    Return information about addresses for all network links on the system
    """
    return addresses_with_options('')

def addresses_for(name):
    """
    Return information about addresses for a given network link on the system
    """
    parsed = addresses_with_options('dev {0}'.format(name))
    if parsed.has_key(name):
        return parsed[name]

def neighbours_with_options(options):
    """
    Return information about neighbours for a given "ip neigh show" set of options
    eg netconfig.neighbours_with_options 'nud noarp'
    """
    output = __salt__['cmd.run']('ip -o neigh show {0}'.format(options))
    return _structured_neigh_output(output)

def neighbours():
    """
    Return information about all known neighbours
    """
    return neighbours_with_options('')

def neighbours_for(name):
    """
    Return information about neighbours for a given network link on the system
    """
    return neighbours_with_options('dev {0}'.format(name))

def all_neighbours():
    """
    Return information about all attempted neighboors, including failed ones
    """
    return neighbours_with_options('nud all')

# TODO: brctl show
# TODO: ip maddr show
# TODO: ifenslave -a (not sure how parseable this is)

# For networking nerds:
#   TODO: brctl showmacs name
#   TODO: ip tunnel show
#   TODO: ip route show table all (looks like hell)
#   TODO: ip mroute show

########NEW FILE########
__FILENAME__ = linux_netstat
__virtualname__ = 'netconfig'

def __virtual__():
    """
    Only run on Linux systems
    """
    return 'netstat' if __grains__['kernel'] == 'Linux' else False

def s():
    """
    Return the statistics available in netstat -s.
    The netstat command is not needed: we use kernel-provided files directly.
    """
    stats = {}
    lines = open('/proc/net/netstat').readlines() + \
            open('/proc/net/snmp').readlines()

    currently_in_header_line = True
    for line in lines:
        sections = line.split(': ')
        prefix, list = sections[0], sections[1].strip()
        stats.setdefault(prefix, {})
        items = list.split(' ')
        if currently_in_header_line:
            headers = items
        else:
            for pos in range(len(headers)):
                stats[prefix][headers[pos]] = int(items[pos])
        currently_in_header_line = not currently_in_header_line

    return stats

########NEW FILE########
__FILENAME__ = nzbget
# -*- coding: utf-8 -*-
'''
Support for nzbget
'''

# Import salt libs
import salt.utils

__func_alias__ = {
    'list_': 'list'
}


def __virtual__():
    '''
    Only load the module if apache is installed
    '''
    cmd = 'nzbget'
    if salt.utils.which(cmd):
        return 'nzbget'
    return False


def version():
    '''
    Return version from nzbget -v.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.version
    '''
    cmd = 'nzbget -v'
    out = __salt__['cmd.run'](cmd).splitlines()
    ret = out[0].split(': ')
    return {'version': ret[1]}


def serverversion():
    '''
    Return server version from ``nzbget -V``. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.serverversion moe
    '''
    cmd = 'ps aux | grep "nzbget -D" | grep -v grep | cut -d " " -f 1'
    user = __salt__['cmd.run'](cmd)
    if not user:
        return 'Server not running'
    cmd = 'nzbget -V -c ~' + user + '/.nzbget | grep "server returned"'
    out = __salt__['cmd.run'](cmd).splitlines()
    ret = out[0].split(': ')
    return {'user': user,
            'version': ret[1], }


def start(user=None):
    '''
    Start nzbget as a daemon using -D option. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.start
    '''
    cmd = 'nzbget -D'
    if user:
        cmd = 'su - ' + user + ' -c "' + cmd + '"'
    out = __salt__['cmd.run'](cmd).splitlines()
    return out


def stop(user=None):
    '''
    Stop nzbget daemon using -Q option. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.stop curly
    '''
    cmd = 'nzbget -Q'
    if user:
        cmd = 'su - ' + user + ' -c "' + cmd + '"'
    out = __salt__['cmd.run'](cmd).splitlines()
    return out


def list_(user=None):
    '''
    Return list of active downloads using nzbget -L. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.list larry
    '''
    ret = {}
    inqueue = ''
    queuelist = []
    cmd = 'nzbget -L'
    if user:
        cmd = cmd + ' -c ~' + user + '/.nzbget'
    out = __salt__['cmd.run'](cmd).splitlines()
    for line in out:
        if 'Queue List' in line:
            inqueue = 1
        if '----------' in line:
            if inqueue == 1:
                inqueue = 2
            else:
                inqueue = ''
            continue
        if inqueue:
            queuelist.append(line)
            continue
        if ': ' not in line:
            continue
        comps = line.split(': ')
        ret[comps[0]] = comps[1]
    if queuelist:
        ret['Queue List'] = queuelist
    return ret


def pause(user=None):
    '''
    Pause nzbget daemon using -P option. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.pause shemp
    '''
    cmd = 'nzbget -P'
    if user:
        cmd = cmd + ' -c ~' + user + '/.nzbget'
    out = __salt__['cmd.run'](cmd).splitlines()
    return out


def unpause(user=None):
    '''
    Unpause nzbget daemon using -U option. Default user is root.

    CLI Example:

    .. code-block:: bash

        salt '*' nzbget.unpause shemp
    '''
    cmd = 'nzbget -U'
    if user:
        cmd = cmd + ' -c ~' + user + '/.nzbget'
    out = __salt__['cmd.run'](cmd).splitlines()
    return out

########NEW FILE########
__FILENAME__ = php_fpm
#!/usr/bin/python
'''
Get varyous php fpm statistic
'''

import flup_fcgi_client as fcgi_client
import salt.utils
from os import listdir
from ConfigParser import ConfigParser

def ping(baseConfigPath = None):
    '''
    Just used to make sure the php-fpm pool is up and responding
    Return PHP FPM status (UP/DOWN)

    CLI Example::

        salt '*' php_fpm.ping
        salt '*' php_fpm.ping baseConfigPath = '/etc/php5/fpm/pool.d/'
    '''

    config = _detect_fpm_configuration(baseConfigPath)
    result = []
    if len(config.sections()) == 0:
        result.append('Can not read PHP FPM config')    
    else:
        for pool_name in config.sections():
            if not config.has_option(pool_name, 'ping.path'):
                result.append('Ping path is not configured for pool:' + pool_name)    
            else:
                code, headers, out, err = _make_fcgi_request(config, pool_name, config.get(pool_name, 'ping.path'))

                response = 'pong'
                if config.has_option(pool_name, 'ping.response'):
                    response = config.get(pool_name, 'ping.response')
                
                if code.startswith('200') and out == response:
                    result.append('Pool: ' + pool_name + ' is UP')
                else:
                    result.append('Pool: ' + pool_name + ' is DOWN')

    return "\n".join(result)


def status(baseConfigPath=None):
    '''
    Try to get php-fpm real time statistic (if its available)
    Return PHP realtime statistic

    CLI Example::

        salt '*' php_fpm.status
        salt '*' php_fpm.status baseConfigPath = '/etc/php5/fpm/pool.d/'
    '''
    
    config = _detect_fpm_configuration(baseConfigPath)
    result = []
    if len(config.sections()) == 0:
        result.append('Can not read PHP FPM config')    
    else:
        for pool_name in config.sections():
            if not config.has_option(pool_name, 'pm.status_path'):
                result.append('Status path is not configured for pool:' + pool_name)    
            else:
                code, headers, out, err = _make_fcgi_request(config, pool_name, config.get(pool_name, 'pm.status_path'))
                if code.startswith('200'):
                    result.append(out)
                else:
                    result.append('Can not get PHP FPM status')    
    return "\n".join(result)

@salt.utils.memoize
def _detect_fpm_configuration(basePath):
    """ try to read php fpm config """
    configFiles = []

    if basePath is None:
        basePath = '/etc/php5/fpm/pool.d/'
    
    dirList= listdir(basePath)
    for fname in dirList:
        if fname[-5:] != '.conf':
            continue
        configFiles.append(basePath + fname)

    config = ConfigParser()
    config.read(configFiles)
    
    return config


def _make_fcgi_request(config, section, request_path):
    """ load fastcgi page """
    try:
        listen = config.get(section, 'listen')
        if listen[0] == '/': 
            #its unix socket
            fcgi = fcgi_client.FCGIApp(connect = listen)
        else:
            if listen.find(':') != -1:
                _listen = listen.split(':') 
                fcgi = fcgi_client.FCGIApp(host = _listen[0], port = _listen[1])
            else:
                fcgi = fcgi_client.FCGIApp(port = listen, host = '127.0.0.1')
            
        env = {
           'SCRIPT_FILENAME': request_path,
           'QUERY_STRING': '',
           'REQUEST_METHOD': 'GET',
           'SCRIPT_NAME': request_path,
           'REQUEST_URI': request_path,
           'GATEWAY_INTERFACE': 'CGI/1.1',
           'SERVER_SOFTWARE': 'ztc',
           'REDIRECT_STATUS': '200',
           'CONTENT_TYPE': '',
           'CONTENT_LENGTH': '0',
           #'DOCUMENT_URI': url,
           'DOCUMENT_ROOT': '/',
           'DOCUMENT_ROOT': '/var/www/'
           }
        ret = fcgi(env)
        return ret
    except Exception as e:
        print str(e)
        print "exception "
        return '500', [], '', str(e)

if __name__ == '__main__':
    print ping()

########NEW FILE########
__FILENAME__ = rabbitmq_plugins
# -*- coding: utf-8 -*-

'''
RabbitMQ plugins module
'''

import logging
import re

from salt import exceptions, utils

log = logging.getLogger(__name__)

def __virtual__():
    '''
    Verify RabbitMQ is installed.
    '''
    name = 'rabbitmq_plugins'
    try:
        utils.check_or_die('rabbitmq-plugins')
    except exceptions.CommandNotFoundError:
        name = False
    return name

def _convert_env(env):
    output = {}
    if env:
        for var in env.split():
            k, v = var.split('=')
            output[k] = v
    return output

def _rabbitmq_plugins(command, runas=None, env=()):
    cmdline = 'rabbitmq-plugins {command}'.format(command=command)
    ret = __salt__['cmd.run_all'](
        cmdline,
        runas=runas,
        env=_convert_env(env)
    )
    if ret['retcode'] == 0:
        return ret['stdout']
    else:
        return False

def list(runas=None, env=()):
    '''
    Return list of plugins: name, state and version
    '''
    regex = re.compile(
        r'^\[(?P<state>[a-zA-Z ])\] (?P<name>[^ ]+) +(?P<version>[^ ]+)$')
    plugins = {}
    res = __salt__['cmd.run']('rabbitmq-plugins list', runas=runas,
                              env=_convert_env(env))
    for line in res.splitlines():
        match = regex.match(line)
        if match:
            plugins[match.group('name')] = {
                'version': match.group('version'),
                'state': match.group('state'),
                }
        else:
            log.warning("line '%s' is invalid", line)
    return plugins

def enable(name, runas=None, env=()):
    '''
    Turn on a rabbitmq plugin
    '''
    return _rabbitmq_plugins('enable %s' % name, runas=runas, env=env)

def disable(name, runas=None, env=()):
    '''
    Turn off a rabbitmq plugin
    '''
    return _rabbitmq_plugins('disable %s' % name, runas=runas, env=env)

########NEW FILE########
__FILENAME__ = riak
'''
Support for riak
'''

import salt.utils

__outputter__ = {
    'signal': 'txt',
}

def __virtual__():
    '''
    Only load the module if riak is installed
    '''
    cmd = 'riak'
    if salt.utils.which(cmd):
        return cmd
    return False


def version():
    '''
    Return Riak node version

    CLI Example::

        salt '*' riak.version
    '''
    cmd = 'riak version'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    return msgs[0]


def ping():
    if is_up() == True:
        return "pong"
    else:
        return ""


def is_up():
    '''
    Ping a Riak node to check its status

    CLI Example::

        salt '*' riak.is_up
    '''
    cmd = 'riak ping'
    out = __salt__['cmd.run'](cmd).split('\n')
    if out[-1] == "pong":
        return True
    else:
        return False


def start():
    '''
    Start a Riak node. Returns True if the node is left in a running state.

    CLI Example::

        salt '*' riak.start
    '''
    cmd = 'riak start'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if len(msgs) == 0 or msgs[0] == "Node is already running!":
        return True
    else:
        return False


def stop():
    '''
    Stop a running Riak node. Returns True if the node is left in a stopped
    state.

    CLI Example::

        salt '*' riak.stop
    '''
    cmd = 'riak stop'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0] in ("ok", "Node is not running!"):
        return True
    else:
        return False


def restart():
    '''
    Stops and then starts the running Riak node without exiting the Erlang VM.
    Returns True if the node is left in a running state.

    CLI Example::

        salt '*' riak.restart
    '''
    cmd = 'riak restart'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0] == "ok":
        return True
    else:
        return False


def cluster_join(node):
    '''
    Join this node to the cluster containing <node>.

    node
        The full node name, in the form user@ip-address

    CLI Example::

        salt '*' riak.cluster_join <node>
    '''
    if len(node.split("@")) != 2:
        return False
    cmd = 'riak-admin cluster join %s' % node
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0].startswith("Success"):
        return True
    else:
        return msgs[0]


def cluster_leave(node=None, force=False):
    '''
    Instruct this node to hand off its data partitions, leave the cluster and 
    shutdown.

    node
        The full node name, in the form user@ip-address.
        If this is not supplied, the node will attempt to remove itself.

    force
        Remove <node> from the cluster without first handing off data 
        partitions. This command is designed for crashed, unrecoverable nodes, 
        and should be used with caution.

    CLI Example::

        salt '*' riak.cluster_leave <node> [<force>]
    '''
    if node is not None and len(node.split("@")) != 2:
        return False
    if force == False:
        cmd = 'riak-admin cluster leave'
    else:
        cmd = 'riak-admin cluster force-remove'
    if node is not None:
        cmd = '%s %s' % (cmd, node)
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0].startswith("Success"):
        return True
    else:
        return msgs[0]


def cluster_replace(node1, node2, force=False):
    '''
    Instruct <node1> to transfer all data partitions to <node2>, then leave the
    cluster and shutdown.

    node1
        The full node name, in the form user@ip-address

    node2
        The full node name, in the form user@ip-address

    force
        Remove <node> from the cluster without first handing off data 
        partitions. This command is designed for crashed, unrecoverable nodes, 
        and should be used with caution.

    CLI Example::

        salt '*' riak.cluster_replace <node>
    '''
    if len(node1.split("@")) != 2 and len(node2.split("@")) != 2:
        return False
    cmd = 'riak-admin cluster replace %s %s' % (node1, node2)
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0].startswith("Success"):
        return True
    else:
        return msgs[0]


def cluster_plan():
    '''
    Display the currently staged cluster changes.

    CLI Example::

        salt '*' riak.cluster_plan
    '''
    cmd = 'riak-admin cluster plan'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0] == "There are no staged changes":
        return None
    else:
        return msgs


def cluster_clear():
    '''
    Clear the currently staged cluster changes.

    CLI Example::

        salt '*' riak.cluster_clear
    '''
    cmd = 'riak-admin cluster clear'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0] == "Cleared staged cluster changes":
        return True
    else:
        return msgs[0]


def cluster_commit():
    '''
    Commit the currently staged cluster changes.

    CLI Example::

        salt '*' riak.cluster_commit
    '''
    cmd = 'riak-admin cluster commit'
    out = __salt__['cmd.run'](cmd).split('\n')
    msgs = [line for line in out if not line.startswith("!!!!")]
    if len(msgs) > 0 and msgs[0].startswith("Attempting"):
        del(msgs[0])
    if msgs[0].startswith("You must verify the plan"):
        return cluster_plan()
    else:
        return msgs[0]


def ringready():
    '''
    Checks whether all nodes in the cluster agree on the ring state.

    CLI Example::

        salt '*' riak.ringready
    '''
    cmd = 'riak-admin ringready'
    out = __salt__['cmd.run'](cmd).split('\n')
    if len(out) > 0 and out[0].startswith("TRUE"):
        return True
    else:
        return False


def ring_status():
    '''
    Outputs the current claimant, its status, ringready, pending ownership 
    handoffs and a list of unreachable nodes.

    CLI Example::

        salt '*' riak.ring_status
    '''
    cmd = 'riak-admin ring-status'
    out = __salt__['cmd.run'](cmd).split('\n')
    out = out[1:len(out)]
    ret = []
    for line in out:
        if len(line) > 0 and line[:1] != "=" and line[:1] != " ":
            ret.append(line)
    return ret


def member_status():
    '''
    Prints the current status of all cluster members.

    CLI Example::

        salt '*' riak.member_status
    '''
    cmd = 'riak-admin member-status'
    out = __salt__['cmd.run'](cmd).split('\n')
    out = out[1:len(out)]
    ret = []
    for line in out:
        if len(line) > 0 and line[:1] != "=" and line[:1] != "-":
            ret.append(line)
    return ret


def transfers():
    '''
    Identifies nodes that are awaiting transfer of one or more partitions.

    CLI Example::

        salt '*' riak.transfers
    '''
    cmd = 'riak-admin transfers'
    out = __salt__['cmd.run'](cmd).split('\n')
    if out[0] == "No transfers active":
        return out[0]
    else:
        return out


def diag():
    '''
    Run diagnostic checks against <node>.

    CLI Example::

        salt '*' riak.diag
    '''
    cmd = 'riak-admin diag'
    out = __salt__['cmd.run'](cmd).split('\n')
    if len(out) == 1 and len(out[0]) == 0:
        return "Nothing to report"
    else:
        return out


def status():
    '''
    Prints status information, including performance statistics, system health
    information, and version numbers.

    CLI Example::

        salt '*' riak.status
    '''
    cmd = 'riak-admin status'
    out = __salt__['cmd.run'](cmd).split('\n')
    ret = []
    for line in out:
        parts = line.split(" : ")
        if len(parts) == 2:
            ret.append({parts[0]: parts[1]})
    return ret

########NEW FILE########
__FILENAME__ = smx
'''
Salt Module to manage Apache Service Mix

The following grains should be set
smx:
  user: admin user name
  pass: password
  path: /absolute/path/to/servicemix/home

or use pillar:
smx.user: admin user name
smx.pass: password
smx.path: /absolute/path/to/servicemix/home

Note:
- if both pillar & grains settings exists -> grains wins
- Tested on apache-servicemix-full-4.4.2.tar.gz
- When a feature is being removed it will not recursivly remove its nested features
  But it will remove the bundles configure in the feature it self
'''

# libs
import time

def __virtual__():
    '''
    Load the module by default
    '''
    
    return 'smx'

def _parse_list(list=[]):
    '''
    Used to parse the result off the list commands.
    for example:
     run('osgi:list')
     run('features:list')
    '''
    ret = []
    for line in list:
        line = line.replace(']','')
        line = line.replace('[','')
        ret.append(line)
    
    return ret

def run(cmd='shell:logout'):
    '''
    execute a command in the servicemix console
    will return an array of the STDOUT
    
    CLI Examples::
        
        salt '*' smx.run 'osgi:list'
    '''
    
    # Get command from grains, if are not set default to modules.config.option
    try:
        user = __grains__['smx']['user']
        password = __grains__['smx']['pass']
        bin = __grains__['smx']['path'] + '/bin/client'
    except KeyError:
        try:
            user = __salt__['config.option']('smx.user')
            password = __salt__['config.option']('smx.pass')
            bin = __salt__['config.option']('smx.path')
            if user and password and bin:
                bin += '/bin/client'
            else:
                return []
        except Exception:
            return []
    
    ret = __salt__['cmd.run']( "'{0}' -u '{1}' -p '{2}' '{3}'".format(bin, user, password, cmd) ).splitlines()
    if len(ret) > 0 and ret[0].startswith('client: JAVA_HOME not set'):
        ret.pop(0)
    return ret

def status():
    '''
    Test if the servicemix daemon is running
    
    CLI Examples::
        
        salt '*' smx.status
    '''
    return run('osgi:list | head -n 1 | grep -c ^START') == ['1']

def is_repo(url):
    '''
    check if the URL is configured as a feature repository
    
    CLI Examples::
        
        salt '*' smx.is_repo http://salt/smxrepo/repo.xml
    '''
    
    return run('features:listurl | grep -c " {0}$"'.format(url)) == ['1']

def feature_addurl(url):
    '''
    Add the url as a feature repository
    
    CLI Examples::
        
        salt '*' smx.features_addurl http://salt/smxrepo/repo.xml
    '''
    
    if is_repo(url):
        return 'present'
    
    run('features:addurl {0}'.format(url))
    if is_repo(url):
        return 'new'
    else:
        return 'missing'

def feature_removeurl(url):
    '''
    Remove the url as a feature repository
    
    CLI Examples::
        
        salt '*' smx.feature_removeurl http://salt/smxrepo/repo.xml
    '''
        
    if is_repo(url) == False:
        return 'absent'.format(url)
    else:
        run('features:removeurl {0}'.format(url))
        if is_repo(url) == False:
            return 'removed'.format(url)
        else:
            return 'failed'.format(url)

def feature_refreshurls():
    '''
    Refresh all the feature repositories
    
    CLI Examples::
        
        salt '*' smx.feature_refreshurls
    '''
    
    for line in run('features:listurl | grep -v "^ Loaded"'):
        url = line.split()[1]
        if feature_refreshurl(url) != 'refreshed':
            return 'error refreshing {0}'.format(url)
    return 'refreshed'

def feature_refreshurl(url):
    '''
    Refresh the feature repository
    
    CLI Examples::
        
        salt '*' smx.feature_refreshurl http://salt/smxrepo/repo.xml
    '''
    if is_repo(url):
        run('features:refreshurl {0}'.format(url))
        return 'refreshed'
    else:
        return 'missing'.format(url)

def bundle_active(bundle):
    '''
    check if the bundle is active
    
    CLI Examples::
        
        salt '*' smx.bundle_active 'some.bundle.name'
    '''
    
    for line in _parse_list(run('osgi:list -s -u | grep Active')):
        lst = line.split()
        if bundle == lst[-1]:
             return True
    
    return False

def nonactive_bundles(bundles=''):
    '''
    return a list of non-active bundles from the csv list
    
    CLI Examples::
        
        salt '*' smx.nonactive_bundles 'some.bundle.name,some.other.name'
    '''
    
    ret = []
    for b in bundles.split(','):
        if bundle_active(b) == False:
            ret.append(b)
    return ','.join(ret)

def bundle_exists(bundle):
    '''
    check if the bundle exists
    
    CLI Examples::
        
        salt '*' smx.bundle_exists 'some.bundle.name'
    '''
    
    for line in _parse_list(run('osgi:list -s -u')):
        lst = line.split()
        if bundle == lst[-1]:
             return True
    
    return False

def bundle_start(bundle):
    '''
    start the bundle
    
    CLI Examples::
        
        salt '*' smx.bundle_start 'some.bundle.name'
    '''
    
    if bundle_exists(bundle) == False:
        return 'missing'
    
    run('osgi:start {0}'.format(bundle))
    
    if bundle_active(bundle):
        return 'active'
    else:
        return 'error'

def bundle_stop(bundle):
    '''
    stop the bundle
    
    CLI Examples::
        
        salt '*' smx.bundle_stop 'some.bundle.name'
    '''
    
    if bundle_exists(bundle) == False:
        return 'missing'
    
    run('osgi:stop {0}'.format(bundle))
    
    if bundle_active(bundle) == False:
        return 'stopped'
    else:
        return 'error'

def is_feature_installed(feature, version=''):
    '''
    check if the feature is installed
    
    CLI Examples::
        
        salt '*' smx.is_feature_installed 'myFeature'
        salt '*' smx.is_feature_installed 'myFeature' '1.1.0'
    '''
    
    for line in _parse_list(run('features:list -i')):
        lst = line.split()
        if version:
            if version == lst[1] and feature == lst[2]:
                return True
        else:
             if feature == lst[2]:
                 return True
    
    return False

def is_feature_installed_latest(feature):
    '''
    check if the feature is installed
    
    CLI Examples::
        
        salt '*' smx.is_feature_installed_latest 'myFeature'
    '''
    
    latest = '0'
    feature_refreshurls()
    for line in _parse_list(run('features:list')):
        lst = line.split()
        if lst[2] == feature:
            latest = max(str(lst[1]),latest)
    
    return is_feature_installed(feature, str(latest))

def feature_install(feature, version='', bundles='', wait4bundles=5):
    '''
    Install a feature.
    
    a third optional arguments is a csv list of bundle names
      that should be in Active mode after the feature installation to validate
      (in the format of osgi:list -s command)
    a forth argument is a time in seconds to check the bundles if active
    
    CLI Examples::
        
        salt '*' smx.feature_install 'myFeature'
        salt '*' smx.feature_install 'myFeature' '1.0.0'
        salt '*' smx.feature_install 'myFeature' '1.2.3' 'com.sun.jersey.core,some.other.bundle' 10
    '''
    
    if version:
        feature_fullname = '/'.join([feature, version])
    else:
        feature_fullname = feature
    
    if is_feature_installed(feature, version) == False:
        feature_refreshurls()
        run('features:install {0}'.format(feature_fullname))
        if is_feature_installed(feature, version) == False:
            return 'failed'
    
    if bundles != '':
        time.sleep(wait4bundles)
    errBundles = nonactive_bundles(bundles)
    
    if len(errBundles) == 0:
        return 'installed'
    else:
        return 'failed, non Active bundles: {0}'.format(','.join(errBundles))
    
def feature_remove(feature, version=''):
    '''
    Uninstall the feature
    
    CLI Examples::
        
        salt '*' smx.feature_remove name-of-feature
        salt '*' smx.feature_remove name-of-feature 1.1.1
    '''
        
    if is_feature_installed(feature, version) == False:
        return 'absent'
    
    if version:
        feature_fullname = '/'.join([feature, version])
    else:
        feature_fullname = feature
    
    run('features:uninstall {0}'.format(feature_fullname))
    if is_feature_installed(feature, version):
        return 'error'
    else:
        return 'removed'

def feature_remove_all_versions(feature):
    '''
    Uninstall the feature in all its versions
    
    CLI Examples::
        
        salt '*' smx.feature_remove_all_versions name-of-feature
    '''
    
    removed = ""
    for line in _parse_list(run('features:list -i')):
        lst = line.split()
        if lst[0] == 'installed' and lst[2] == feature:
            removed += " {0}".format(lst[1])
            if feature_remove(feature, lst[1]) == 'error':
                return 'error removing {0}'.format('/'.join([feature, lst[1]]))
    
    if removed:
        return 'removed: {0}'.format(removed)
    else:
        return 'no version removed'

########NEW FILE########
__FILENAME__ = sysbench
'''
The 'sysbench' module is used to analyse the
performance of the minions, right from the master!
It measures various system parameters such as
CPU, Memory, FileI/O, Threads and Mutex.
'''

import re
import salt.utils

__outputter__ = {
    'ping': 'txt',
    'cpu': 'yaml',
    'threads': 'yaml',
    'mutex': 'yaml',
    'memory': 'yaml',
    'fileio': 'yaml'
}


def __virtual__():
    '''
    loads the module, if only sysbench is installed
    '''
    # finding the path of the binary
    if salt.utils.which('sysbench'):
        return 'sysbench'
    return False


def _parser(result):
    '''
    parses the output into a dictionary
    '''

    # regexes to match
    _total_time = re.compile(r'total time:\s*(\d*.\d*s)')
    _total_execution = re.compile(r'event execution:\s*(\d*.\d*s)')
    _min_response_time = re.compile(r'min:\s*(\d*.\d*ms)')
    _max_response_time = re.compile(r'max:\s*(\d*.\d*ms)')
    _avg_response_time = re.compile(r'avg:\s*(\d*.\d*ms)')
    _per_response_time = re.compile(r'95 percentile:\s*(\d*.\d*ms)')

    # extracting data
    total_time = re.search(_total_time, result).group(1)
    total_execution = re.search(_total_execution, result).group(1)
    min_response_time = re.search(_min_response_time, result).group(1)
    max_response_time = re.search(_max_response_time, result).group(1)
    avg_response_time = re.search(_avg_response_time, result).group(1)
    per_response_time = re.search(_per_response_time, result)
    if per_response_time is not None:
        per_response_time = per_response_time.group(1)

    # returning the data as dictionary
    return {
           'total time            ': total_time,
           'total execution time  ': total_execution,
           'minimum response time ': min_response_time,
           'maximum response time ': max_response_time,
           'average response time ': avg_response_time,
           '95 percentile         ': per_response_time
           }


def cpu():
    '''
    Tests for the cpu performance of minions.

    CLI Examples::

        salt '*' sysbench.cpu
    '''

    # Test data
    max_primes = [500, 1000, 2500, 5000]

    # Initializing the test variables
    test_command = 'sysbench --test=cpu --cpu-max-prime={0} run'
    result = None
    ret_val = {}

    # Test beings!
    for primes in max_primes:
        key = 'Primer numbers limit: {0}'.format(primes)
        run_command = test_command.format(primes)
        result = __salt__['cmd.run'](run_command)
        ret_val[key] = _parser(result)

    return ret_val


def threads():
    '''
    This tests the performance of the processor's scheduler

    CLI Example::

        salt \* sysbench.threads
    '''

    # Test data
    thread_yields = [100, 200, 500, 1000]
    thread_locks = [2, 4, 8, 16]

    # Initializing the test variables
    test_command = 'sysbench --num-threads=64 --test=threads '
    test_command += '--thread-yields={0} --thread-locks={1} run '
    result = None
    ret_val = {}

    # Test begins!
    for yields, locks in zip(thread_yields, thread_locks):
        key = 'Yields: {0} Locks: {1}'.format(yields, locks)
        run_command = test_command.format(yields, locks)
        result = __salt__['cmd.run'](run_command)
        ret_val[key] = _parser(result)

    return ret_val


def mutex():
    '''
    Tests the implementation of mutex

    CLI Examples::

        salt \* sysbench.mutex
    '''

    # Test options and the values they take
    # --mutex-num = [50,500,1000]
    # --mutex-locks = [10000,25000,50000]
    # --mutex-loops = [2500,5000,10000]

    # Test data (Orthogonal test cases)
    mutex_num = [50, 50, 50, 500, 500, 500, 1000, 1000, 1000]
    locks = [10000, 25000, 50000, 10000, 25000, 50000, 10000, 25000, 50000]
    mutex_locks = []
    mutex_locks.extend(locks)
    mutex_loops = [2500, 5000, 10000, 10000, 2500, 5000, 5000, 10000, 2500]

    # Initializing the test variables
    test_command = 'sysbench --num-threads=250 --test=mutex '
    test_command += '--mutex-num={0} --mutex-locks={1} --mutex-loops={2} run '
    result = None
    ret_val = {}

    # Test begins!
    for num, locks, loops in zip(mutex_num, mutex_locks, mutex_loops):
        key = 'Mutex: {0} Locks: {1} Loops: {2}'.format(num, locks, loops)
        run_command = test_command.format(num, locks, loops)
        result = __salt__['cmd.run'](run_command)
        ret_val[key] = _parser(result)

    return ret_val


def memory():
    '''
    This tests the memory for read and write operations.

    CLI Examples::

        salt \* sysbench.memory
    '''

    # test defaults
    # --memory-block-size = 10M
    # --memory-total-size = 1G

    # We test memory read / write against global / local scope of memory
    # Test data
    memory_oper = ['read', 'write']
    memory_scope = ['local', 'global']

    # Initializing the test variables
    test_command = 'sysbench --num-threads=64 --test=memory '
    test_command += '--memory-oper={0} --memory-scope={1} '
    test_command += '--memory-block-size=1K --memory-total-size=32G run '
    result = None
    ret_val = {}

    # Test begins!
    for oper in memory_oper:
        for scope in memory_scope:
            key = 'Operation: {0} Scope: {1}'.format(oper, scope)
            run_command = test_command.format(oper, scope)
            result = __salt__['cmd.run'](run_command)
            ret_val[key] = _parser(result)

    return ret_val


def fileio():
    '''
    This tests for the file read and write operations
    Various modes of operations are
        sequential write
        sequential rewrite
        sequential read
        random read
        random write
        random read and write

    The test works with 32 files with each file being 1Gb in size
    The test consumes a lot of time. Be patient!

    CLI Examples::

        salt \* sysbench.fileio
    '''

    # Test data
    test_modes = ['seqwr', 'seqrewr', 'seqrd', 'rndrd', 'rndwr', 'rndrw']

    # Initializing the required variables
    test_command = 'sysbench --num-threads=16 --test=fileio '
    test_command += '--file-num=32 --file-total-size=1G --file-test-mode={0} '
    result = None
    ret_val = {}

    # Test begins!
    for mode in test_modes:
        key = 'Mode: {0}'.format(mode)

        # Prepare phase
        run_command = (test_command + 'prepare').format(mode)
        __salt__['cmd.run'](run_command)

        # Test phase
        run_command = (test_command + 'run').format(mode)
        result = __salt__['cmd.run'](run_command)
        ret_val[key] = _parser(result)

        # Clean up phase
        run_command = (test_command + 'cleanup').format(mode)
        __salt__['cmd.run'](run_command)

    return ret_val


def ping():

    return True

########NEW FILE########
__FILENAME__ = system
'''
Support for reboot, shutdown, etc
'''

import salt.utils

UNSUPPORTED = ('Windows')

def __virtual__():
    '''
    Only supported on POSIX-like systems
    '''
    if __grains__['os'] in UNSUPPORTED or not salt.utils.which('shutdown'):
        return False
    return 'system'


def halt():
    '''
    Halt a running system
    
    CLI Example::
    
        salt '*' system.halt
    '''
    cmd = 'halt'
    ret = __salt__['cmd.run'](cmd)
    return ret


def init(runlevel):
    '''
    Change the system runlevel on sysV compatible systems
    
    CLI Example::
    
        salt '*' system.init 3
    '''
    cmd = 'init {0}'.format(runlevel)
    ret = __salt__['cmd.run'](cmd)
    return ret


def poweroff():
    '''
    Poweroff a running system
    
    CLI Example::
    
        salt '*' system.poweroff
    '''
    cmd = 'poweroff'
    ret = __salt__['cmd.run'](cmd)
    return ret


def reboot():
    '''
    Reboot the system using the 'reboot' command
    
    CLI Example::
    
        salt '*' system.reboot
    '''
    cmd = 'reboot'
    ret = __salt__['cmd.run'](cmd)
    return ret


def shutdown():
    '''
    Shutdown a running system
    
    CLI Example::
    
        salt '*' system.shutdown
    '''
    cmd = 'shutdown'
    ret = __salt__['cmd.run'](cmd)
    return ret


########NEW FILE########
__FILENAME__ = vzctl
'''
Salt module to manage openvz hosts through vzctl and vzlist.
'''

import salt.utils

__outputter__ = {
                'version': 'txt',
                'vzlist': 'txt',
                'execute': 'txt',
                'start': 'txt',
                'stop': 'txt',
                'restart': 'txt'
                }

def __virtual__():
    '''
    Check to see if vzctl and vzlist are installed and load module
    '''
    if salt.utils.which('vzctl') and salt.utils.which('vzlist'):
        return 'vzctl'
    return False

def version():
    '''
    Return version from vzctl --version

    CLI Example::

    salt '*' vzctl.version
    ''' 
    out = __salt__['cmd.run']('vzctl --version')
    return out

def vzlist():
    '''
    Return list of containers from "vzlist -a"

    CLI Example::

    salt '*' vzctl.vzlist
    '''
    out = __salt__['cmd.run']('vzlist -a')
    return out

def execute(ctid=None,
          option=None):
    '''
    Execute a command on a container.

    CLI Example::

    salt '*' vzctl.execute 123 "df -h"
    '''
    if not ctid:
        return "Error: No container ID specified."
    if not option:
        return "Error: No option parameter specified."
	
    ret, error = _checkCtid(ctid)

    if ret:
        output = _runCommand(
                            "exec",
                            ctid,
                            option
                            )
        return output
    else:
        return error

def start(ctid=None,
        option=None):
    '''
    Start a container.

    CLI Example::

    salt '*' vzctl.start 123

    Can accept the wait or force arguments.

    For example::

    salt '*' vzctl.start 123 force
    '''
    if not ctid:
        return "Error: No container ID specified."
	
    ret, error = _checkCtid(ctid)

    if ret:
        output = _runCommand(
                             "start",
                             ctid,
                             option
                             )
        return output
    else:
        return error

def stop(ctid=None,
         option=None):
    '''
    Stop a container.

    CLI Example::

    salt '*' vzctl.stop 123

    Can accept the wait or skip-unmount arguments.

    For example::

    salt '*' vzctl.stop 123 skip-unmount
    '''
    if not ctid:
        return "Error: No container ID specified."
	
    ret, error = _checkCtid(ctid)

    if ret:
        output = _runCommand(
                            "stop",
                            ctid,
                            option
                            )
        return output
    else:
        return error

def restart(ctid=None,
            option=None):
    '''
    Restart a container.

    CLI Example::

    salt '*' vzctl.restart 123

    Can accept the wait, force or fast arguments.

    For example::

    salt '*' vzctl.restart 123 fast
    '''
    if not ctid:
        return "Error: No container ID specified."

    ret, error = _checkCtid(ctid)

    if ret:
        output = _runCommand(
                            "restart",
                            ctid,
                            option
                            )
        return output
    else:
        return error

def _checkCtid(ctid):
    '''
    Checks to see if the ctid is a valid number
    '''
    try:
        ctid = int(ctid)
        return True, None
    except:
        return False, "Error: ctid is not a number."

def _runCommand(
               command,
               ctid,
               option
               ):
    '''
    Use salt to run the command and output.
    '''
    if option is None:
        cmd = 'vzctl {0} {1}'.format(command,ctid)
        out = __salt__['cmd.run'](cmd)
        return out
    else:
        cmd = 'vzctl {0} {1} --{2}'.format(command,ctid,option)
        out = __salt__['cmd.run'](cmd)
        return out

########NEW FILE########
__FILENAME__ = webalizer
'''
A module for managing webalizer web statistics

:maintainer: Brent Lambert <brent@enpraxis.net>
:maturity: new
:platform: RedHat, Debian Families
:depends: webalizer cron

Assumes that the appropriate web server configuration and access 
controls have already been configured. Will generate a script 
for updating webalizer and will use it with cron to enable automatic 
updates.
'''

from subprocess import Popen, PIPE
import os
import re


# Scripts and paths

webalizer_update='''#!/bin/bash
/usr/bin/webalizer -c {0}
'''

webalizer_scr_path = '/usr/local/bin/webalizer_update'
webalizer_hourly = '/etc/cron.hourly/webalizer'
webalizer_daily = '/etc/cron.daily/webalizer'


def __virtual__():
    '''
    Only supports RedHat and Debian OS Families for now
    '''
    return 'webalizer' if __grains__['os_family'] in ['RedHat', 'Debian'] else False


def _runcmd(cmd):
    '''
    Run a command and return output, any error info and return code
    '''
    child = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = child.communicate()
    return child.returncode, out, err


def _remove(fpath):
    '''
    If a file exist remove it
    '''
    try:
        os.unlink(fpath)
    except OSError, e:
        # Ignore if file does not exist
        if e.errno != 2:
            raise OSError, e


def configure(domain, logfile, period='hourly'):
    '''
    Configure webalizer to track statisctics for a particular domain,
    using a particular log file.

    Parameters:

        domain
            The name of the web domain webalizer should track
        logfile
            The logfile that contains web data for the above domain
        period
            Either 'hourly' or 'daily'

    CLI_Example::

        salt 'server' webalizer.configure domain.com \
          /var/log/httpd/access_log \
          period=daily

        salt 'server' webalizer.configure domain.com \
          /var/log/nginx/access.log
    '''
    if domain and logfile:

        # Get OS specific values
        if __grains__['os_family'] == 'RedHat':
            wconf = '/etc/webalizer.conf'
            hns = r'^#HostName .*$'
        elif __grains__['os_family'] == 'Debian':
            wconf = '/etc/webalizer/webalizer.conf'
            hns = r'^HostName .*$'
        else:
            return False

        hn = re.compile(hns, re.MULTILINE)
        lf = re.compile('^LogFile .*$', re.MULTILINE)

        # Modify the configuration
        with open(wconf, 'r+') as f:
            config = f.read()
            config = hn.sub('HostName {0}'.format(domain), config)
            config = lf.sub('LogFile {0}'.format(logfile), config)
            f.seek(0)
            f.write(config)
            f.truncate()

        # Generate an appropriate update script, store in /usr/local/bin
        update = webalizer_update.format(wconf)
        with open(webalizer_scr_path, 'w') as f:
            f.write(update)
            os.chmod(webalizer_scr_path, 0700)
    
        # Set up cron
        if period == 'hourly':
            if not os.path.exists(webalizer_hourly):
                os.symlink(webalizer_scr_path, webalizer_hourly)
        elif period == 'daily':
            if not os.path.exists(webalizer_daily):
                os.symlink(webalizer_scr_path, webalizer_daily)

        return True

    return False
            
    
def disable():
    '''
    Disable automatic updates.

    CLI_Example::
    
        salt 'server' webalizer.disable
    '''
    _remove(webalizer_hourly)
    _remove(webalizer_daily)
    return True


def update():
    '''
    Update webalizer stats immediately.

    CLI_Example::
    
        salt 'server' webalizer.update
    '''
    result = _runcmd(webalizer_scr_path)
    if result[0]:
        # We have a return code, must be an error
        return False
    return True



########NEW FILE########
__FILENAME__ = win_update
# -*- coding: utf-8 -*-
'''
Module for running windows updates.

:depends:   - win32com
            - win32con
            - win32api
            - pywintypes

.. versionadded: (Helium)

Note about naming convention used internally to this module:
You will notice rather quickly that many of the names in this module have been named after various
aspects of the sport 'Quidditch' from the fantasy series 'Harry Potter'. If you are unfamiliar with
Quidditch, I addvise you go read about it on wikipedia as a basic knowledge of it will help you
to understand what is going on. 

Why did I do this you may ask? Clearity. Which sounds backwards. But variable names that are long
and not incredibly conceptually accurate 'searcher', 'updates found', 'updates downloaded', 
'updates to be downloaded','updates that are installed','updates that are downloaded, but not 
installed, but are going to be installed', etc. are not helpful.

So I provide you with a simple game of Quidditch to keep things understandable. here are roughly
what the variables I use are and what they do:

Quidditch: the instance of the python windows updater class.

Players:
Keeper: the master variable that manages the update session.
Seeker: the handle to the windows update agent (WUA) object responsible for doing the searches.
Chaser: the handle to the WUA object responsible for managing the download of updates.
Beater: the handle to the WUA object that is given the task of installing the windows updates to
        the system the script is run on. Name was partly choosen as a joke against windows.

golden_snitch: what the seeker seeks. So the results of the search from the WUA object.
quaffle: what the chasers chase. The list of updates to be downloaded.
Bluger: what the beaters beat. The list of updates that are ready to be installed.

points: the results of the download process. i.e. getting the quaffle through the hoop.
fouls: results of the installation process. i.e. hitting other players. still. joke against windows

'''

# Import Python libs
import logging
try:
        import win32com.client
        import win32api
        import win32con
        import pywintypes
        import threading
        import pythoncom
        HAS_DEPENDENCIES = True
except ImportError:
        HAS_DEPENDENCIES = False

import salt.utils

log = logging.getLogger(__name__)

__virtualname__ = 'win_update'

def __virtual__():
        '''
        Only works on Windows systems
        '''
        if salt.utils.is_windows() and HAS_DEPENDENCIES:
                return __virtualname__
        return False

#this is a convenience method to gather what categories of updates are available in any update
# collection it is passed. Typically though, the quaffle.
def _gather_update_categories(updateCollection):
        categories = []
        for i in range(updateCollection.Count):
                update = updateCollection.Item(i)
                for j in range(update.Categories.Count):
                        name = update.Categories.Item(j).Name
                        if name not in categories:
                                log.debug('found category: {0}'.format(name))
                                categories.append(name)
        return categories

# some known categories:
#       Updates
#       Windows 7
#       Critical Updates
#       Security Updates
#       Update Rollups

class PyWinUpdater:
        def __init__(self,categories=None,skipUI = True,skipDownloaded = True,
                        skipInstalled=True, skipReboot=False,skipPresent=True,
                        softwareUpdates=True, driverUpdates=False,skipHidden=True):
                log.debug('CoInitializing the pycom system')
                pythoncom.CoInitialize()
                
                self.skipUI = skipUI
                self.skipDownloaded = skipDownloaded
                self.skipInstalled = skipInstalled
                self.skipReboot = skipReboot
                self.skipPresent = skipPresent
                self.skipHidden = skipHidden
                
                self.softwareUpdates = softwareUpdates
                self.driverUpdates = driverUpdates
                
                #the list of categories that the user wants to be searched for.
                self.categories = categories
                
                #the list of categories that are present in the updates found.
                self.foundCategories = []
                
                #careful not to get those two confused.
                
                
                log.debug('dispatching keeper to keep the session object.')
                self.keeper = win32com.client.Dispatch('Microsoft.Update.Session')
                
                log.debug('keeper got. Now creating a seeker to seek out the updates')
                self.seeker = self.keeper.CreateUpdateSearcher()
                
                #list of updates that are applicable by current settings.
                self.quaffle = win32com.client.Dispatch('Microsoft.Update.UpdateColl')
                
                #list of updates to be installed.
                self.bludger = win32com.client.Dispatch('Microsoft.Update.UpdateColl')
                
                #the object responsible for fetching the actual downloads. 
                self.chaser = self.keeper.CreateUpdateDownloader()
                self.chaser.Updates = self.quaffle
                
                #the object responsible for the installing of the updates.
                self.beater = self.keeper.CreateUpdateInstaller()
                self.beater.Updates = self.bludger
                
                #the results of the download process
                self.points = None
                
                #the results of the installation process
                self.fouls = None

        def Search(self,searchString):
                try:
                        log.debug('beginning search of the passed string: {0}'.format(searchString))
                        self.golden_snitch = self.seeker.Search(searchString)
                        log.debug('search completed successfully.')
                except Exception as e:
                        log.info('search for updates failed. {0}'.format(str(e)))
                        return e
                
                log.debug('parsing results. {0} updates were found.'.format(
                    str(self.golden_snitch.Updates.Count)))
                
                try:
                        #step through the list of the updates to ensure that the updates match the
                        # features desired.
                        for update in self.golden_snitch.Updates:
                                #this skipps an update if UI updates are not desired.
                                if update.InstallationBehavior.CanRequestUserInput == True:
                                        log.debug('Skipped update {0}'.format(str(update)))
                                        continue
                                
                                #if this update is already downloaded, it doesn't need to be in 
                                # the quaffle. so skipping it unless the user mandates redownload.
                                if self.skipDownloaded and update.IsDownloaded:
                                        continue
                                
                                #check this update's categories aginst the ones desired.
                                for category in update.Categories:
                                        #this is a zero gaurd. these tests have to be in this order
                                        # or it will error out when the user tries to search for 
                                        # updates with out specifying categories.
                                        if self.categories == None or category.Name in self.categories:
                                                #adds it to the list to be downloaded.
                                                self.quaffle.Add(update)
                                                log.debug('added update {0}'.format(str(update)))
                                                #ever update has 2 categories. this prevents the
                                                #from being added twice.
                                                break;
                        log.debug('quaffle made. gathering found categories.')
                        
                        #gets the categories of the updates available in this collection of updates
                        self.foundCategories = _gather_update_categories(self.quaffle)
                        log.debug('found categories: {0}'.format(str(self.foundCategories)))
                        return True
                except Exception as e:
                        log.info('parsing updates failed. {0}'.format(str(e)))
                        return e
                        
        def AutoSearch(self):
                #this function generates a search string. simplifying the search function while
                #still providing as many features as possible.
                search_string = ''
                searchParams = []
                if self.skipInstalled: searchParams.append('IsInstalled=0')
                else: searchParams.append('IsInstalled=1')
                if self.skipHidden: searchParams.append('IsHidden=0')
                else: searchParams.append('IsHidden=1')
                if self.skipReboot: searchParams.append('RebootRequired=1')
                else: searchParams.append('RebootRequired=0')
                if self.skipPresent: searchParams.append('IsPresent=0')
                else: searchParams.append('IsPresent=1')
                if len(searchParams) > 1:
                        for i in searchParams:
                                search_string += '{0} and '.format(i)
                else:
                        search_string += '{0} and '.format(searchParams[1])
                
                if self.softwareUpdates and self.driverUpdates:
                        search_string += 'Type=\'Software\' or Type=\'Driver\''
                elif self.softwareUpdates:
                        search_string += 'Type=\'Software\''
                elif self.driverUpdates:
                        search_string += 'Type=\'Driver\''
                else:
                        return False ##if there is no type, the is nothing to search.
                log.debug('generated search string: {0}'.format(search_string))
                return self.Search(search_string)

        def Download(self):
                #chase the quaffle! do the actual download process.
                try:
                        #if the quaffle is empty. no need to download things.
                        if self.quaffle.Count != 0:
                                self.points = self.chaser.Download()
                        else:
                                log.debug('Skipped downloading, all updates were already cached.')
                        return True
                except Exception as e:
                        log.debug('failed in the downloading {0}.'.format(str(e)))
                        return e
                
        def Install(self):
                #beat those updates into place!
                try:
                        #this does not draw from the quaffle. important thing to know.
                        #the blugger is created regardless of what the quaffle has done. but it
                        #will only download those updates which have been downloaded and are ready.
                        for update in self.golden_snitch.Updates:
                                if update.IsDownloaded:
                                        self.bludger.Add(update)
                        log.debug('Updates prepared. beginning installation')
                except Exception as e:
                        log.info('Preparing install list failed: {0}'.format(str(e)))
                        return e
                
                #if the blugger is empty. no point it starting the install process.
                if self.bludger.Count != 0:
                        log.debug('Install list created, about to install')
                        updates = []
                        try:
                                #the call to install.
                                self.fouls = self.beater.Install()
                                log.info('Installation of updates complete')
                                return True
                        except Exception as e:
                                log.info('Installation failed: {0}'.format(str(e)))
                                return e
                else:
                        log.info('no new updates.')
                        return True
        
        #this gets results of installation process.
        def GetInstallationResults(self):
                #if the blugger is empty, the results are nil.
                log.debug('bluger has {0} updates in it'.format(str(self.bludger.Count)))
                if self.bludger.Count == 0:
                        return {}
                
                updates = []
                log.debug('reparing update list')
                for i in range(self.bludger.Count):
                        #this gets the result from fouls, but the title comes from the update
                        #collection bludger.
                        updates.append('{0}: {1}'.format(
                                str(self.fouls.GetUpdateResult(i).ResultCode),
                                str(self.bludger.Item(i).Title)))
                
                log.debug('Update results enumerated, now making a library to pass back')
                results = {}
                
                #translates the list of update results into a library that salt expects.
                for i,update in enumerate(updates):
                        results['update {0}'.format(i)] = update
                
                log.debug('Update information complied. returning')
                return results
        
        #converts the installation results into a pretty print.
        def GetInstallationResultsPretty(self):
                updates = self.GetInstallationResults()
                ret = 'The following are the updates and their return codes.\n'
                for i in updates.keys():
                        ret += '\t{0} : {1}\n'.format(str(updates[i].ResultCode),str(updates[i].Title))
                return ret

        def GetDownloadResults(self):
                for i in range(self.quaffle.Count):
                        updates.append('{0}: {1}'.format(
                                str(self.points.GetUpdateResult(i).ResultCode),
                                str(self.quaffle.Item(i).Title)))
                results = {}
                for i,update in enumerate(updates):
                        results['update {0}'.format(i)] = update
                return results
                
        def GetSearchResults(self):
                updates = []
                log.debug('parsing results. {0} updates were found.'.format(
                        str(self.quaffle.count)))
                
                for update in self.quaffle:
                        if update.InstallationBehavior.CanRequestUserInput == True:
                                log.debug('Skipped update {0}'.format(str(update)))
                                continue
                        updates.append(str(update))
                        log.debug('added update {0}'.format(str(update)))
                return updates
        
        def GetSearchResultsPretty(self):
                updates = self.GetSearchResults()
                ret = 'There are {0} updates. they are as follows:\n'.format(str(len(updates)))
                for update in updates:
                        ret += '\t{0}\n'.format(str(update))
                return ret

        def SetCategories(self,categories):
                self.categories = categories

        def GetCategories(self):
                return self.categories

        def GetAvailableCategories(self):
                return self.foundCategories

        def SetIncludes(self,includes):
                if includes:
                        for i in includes:
                                value = i[i.keys()[0]]
                                include = i.keys()[0]
                                self.SetInclude(include,value)
                                log.debug('was asked to set {0} to {1}'.format(include,value))

        def SetInclude(self,include,state):
                if include == 'UI': self.skipUI = state
                elif include == 'downloaded': self.skipDownloaded = state
                elif include == 'installed': self.skipInstalled = state
                elif include == 'reboot': self.skipReboot = state
                elif include == 'present': self.skipPresent = state
                elif include == 'software':self.softwareUpdates = state
                elif include == 'driver':self.driverUpdates = state
                log.debug('new search state: \n\tUI: {0}\n\tDownload: {1}\n\tInstalled: {2}\n\treboot :{3}\n\tPresent: {4}\n\tsoftware: {5}\n\tdriver: {6}'.format(
                        self.skipUI,self.skipDownloaded,self.skipInstalled,self.skipReboot,
                        self.skipPresent,self.softwareUpdates,self.driverUpdates))
        
        def __str__(self):
                updates = []
                results = 'There are {0} updates, by category there are:\n'.format(
                        str(self.quaffle.count))
                for category in self.foundCategories:
                        count = 0
                        for update in self.quaffle:
                                for c in update.Categories:
                                        if category == c.Name:
                                                count += 1
                        results += '\t{0}: {1}\n'.format(category,count)
                return results

#a wrapper method for the pywinupdater class. I might move this into the class, but right now,
#that is to much for one class I think.
def _search(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while passed != True:
                log.debug('Searching. tries left: {0}'.format(str(retries)))
                #let the updater make it's own search string. MORE POWER this way.
                passed = quidditch.AutoSearch()
                log.debug('Done searching: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed in the seeking/parsing process:\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,True,retries)
                        passed = False
        if clean:
                #bragging rights.
                comment += 'Search was done with out an error.\n'
        
        return (comment,True,retries)

#another wrapper method. 
def _download(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while not passed:
                log.debug('Downloading. tries left: {0}'.format(str(retries)))
                passed = quidditch.Download()
                log.debug('Done downloading: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed while trying to download updates:\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,False,retries)
        if clean:
                comment += 'Download was done without error.\n'
        return (comment,True,retries)

#and the last wrapper method. keeping things simple.
def _install(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while not passed:
                log.debug('quaffle is this long: {0}'.format(str(quidditch.bludger.Count)))
                log.debug('Installing. tries left: {0}'.format(str(retries)))
                passed = quidditch.Install()
                log.info('Done installing: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed while trying to install the updates.\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,False,retries)
        if clean:
                comment += 'Install was done without error.\n'
        return (comment,True,retries)

#this is where the actual functions available to salt begin.
def list_updates(verbose=False,includes=None,retries=5,categories=None):
        '''
        Returns a summary of available updates, grouped into their non-mutually
        exclusive categories. 
        
        To list the actual updates by name, add 'verbose' to the call.
        
        you can set the maximum number of retries to n in the search process by 
        adding: retries=n
        
        various aspects of the updates can be included or excluded. this feature is
        still indevelopment.
        
        You can also specify by category of update similarly to how you do includes:
        categories=['Windows 7','Security Updates']
        Some known categories:
                        Updates
                        Windows 7
                        Critical Updates
                        Security Updates
                        Update Rollups
        
        CLI Example:
        Normal Usage:
        .. code-block:: bash
                salt '*' win_updates.list_updates
        
        Find all critical updates list in detail:
        .. code-block:: bash
                salt '*' win_updates.list_updates categories=['Critical Updates'] verbose
        
        '''
        
        log.debug('categories to search for are: '.format(str(categories)))
        quidditch = PyWinUpdater()
        if categories:
                quidditch.SetCategories(categories)
        quidditch.SetIncludes(includes)
        
        
        ##this is where we be seeking the things! yar!
        comment, passed, retries = _search(quidditch,retries)
        if not passed:
                return (comment,str(passed))
        log.debug('verbose: {0}'.format(str(verbose)))
        if verbose:
                return str(quidditch.GetSearchResultsPretty())
        return str(quidditch)

def download_updates(includes=None,retries=5,categories=None):
        '''
        Downloads all available updates, skipping those that require user interaction.
        
        you can set the maximum number of retries to n in the search process by 
        adding: retries=n
        
        various aspects of the updates can be included or excluded. this feature is
        still indevelopment.
        
        You can also specify by category of update similarly to how you do includes:
        categories=['Windows 7','Security Updates']
        Some known categories:
                        Updates
                        Windows 7
                        Critical Updates
                        Security Updates
                        Update Rollups
        
        CLI Example:
        Normal Usage:
        .. code-block:: bash
                salt '*' win_updates.download_updates
        
        Find all critical updates list in detail:
        .. code-block:: bash
                salt '*' win_updates.download_updates categories=['Critical Updates'] verbose
        
        '''
        log.debug('categories to search for are: '.format(str(categories)))
        quidditch = PyWinUpdater()
        quidditch.SetCategories(categories)
        quidditch.SetIncludes(includes)
        
        
        ##this is where we be seeking the things! yar!
        comment, passed, retries = _search(quidditch,retries)
        if not passed:
                return (comment,str(passed))
        
        ##this is where we get all the things! i.e. download updates.
        comment, passed, retries = _download(quidditch,retries)
        if not passed:
                return (comment,str(passed))

        try:
                comment = quidditch.GetDownloadResults()
        except Exception as e:
                comment = 'could not get results, but updates were installed.'
        return 'Windows is up to date. \n{0}'.format(comment)

def install_updates(cached=None,includes=None,retries=5,categories=None):
        '''
        Downloads and installs all available updates, skipping those that require user interaction.
        
        Add 'cached' to only install those updates which have already been downloaded.
        
        you can set the maximum number of retries to n in the search process by 
        adding: retries=n
        
        various aspects of the updates can be included or excluded. this feature is
        still indevelopment.
        
        You can also specify by category of update similarly to how you do includes:
        categories=['Windows 7','Security Updates']
        Some known categories:
                        Updates
                        Windows 7
                        Critical Updates
                        Security Updates
                        Update Rollups
        
        CLI Example:
        Normal Usage:
        .. code-block:: bash
                salt '*' win_updates.install_updates
        
        Find all critical updates list in detail:
        .. code-block:: bash
                salt '*' win_updates.install_updates categories=['Critical Updates'] verbose
        
        '''
        
        log.debug('categories to search for are: '.format(str(categories)))
        quidditch = PyWinUpdater()
        quidditch.SetCategories(categories)
        quidditch.SetIncludes(includes)
        
        
        ##this is where we be seeking the things! yar!
        comment, passed, retries = _search(quidditch,retries)
        if not passed:
                return (comment,str(passed))
        
        ##this is where we get all the things! i.e. download updates.
        comment, passed, retries = _download(quidditch,retries)
        if not passed:
                return (comment,str(passed))

        ##this is where we put things in their place!
        comment, passed, retries = _install(quidditch,retries)
        if not passed:
                return (comment,str(passed))

        try:
                comment = quidditch.GetInstallationResultsPretty()
        except Exception as e:
                comment = 'could not get results, but updates were installed.'
        return 'Windows is up to date. \n{0}'.format(comment)
        
#To the King#

########NEW FILE########
__FILENAME__ = yumpkg_api
# -*- coding: utf-8 -*-
'''
Support for YUM

:depends:   - yum Python module
            - rpmUtils Python module

This module is no longer being developed and is not guaranteed to be
API-compatible with pkg states. Use at your own risk.

This module uses the python interface to YUM. Note that with a default
/etc/yum.conf, this will cause messages to be sent to sent to syslog on
/dev/log, with a log facility of :strong:`LOG_USER`. This is in addition to
whatever is logged to /var/log/yum.log. See the manpage for ``yum.conf(5)`` for
information on how to use the ``syslog_facility`` and ``syslog_device`` config
parameters to configure how syslog is handled, or take the above defaults into
account when configuring your syslog daemon.

.. note::

    As of version 2014.1.0 (Hydrogen), this module is only used for yum-based
    distros if the minion has the following config parameter set:

    .. code-block:: yaml

        yum_provider: yumpkg_api
'''

# NOTE: This is no longer being developed and is not guaranteed to be
# API-compatible with pkg states. Use at your own risk.

# Import python libs
import copy
import fnmatch
import logging
import re
import yaml

# Import salt libs
import salt.utils
from salt.exceptions import CommandExecutionError
from salt.utils import namespaced_function as _namespaced_function
from salt.modules.yumpkg import (
    _parse_repo_file, list_repos, mod_repo, get_repo, del_repo,
    expand_repo_def, __ARCHES
)

# Import third party libs
try:
    import yum
    import yum.logginglevels
    import rpmUtils.arch
    HAS_YUMDEPS = True

    class _YumLogger(yum.rpmtrans.RPMBaseCallback):
        '''
        A YUM callback handler that logs failed packages with their associated
        script output to the minion log, and logs install/remove/update/etc.
        activity to the yum log (usually /var/log/yum.log).

        See yum.rpmtrans.NoOutputCallBack in the yum package for base
        implementation.
        '''
        def __init__(self):
            yum.rpmtrans.RPMBaseCallback.__init__(self)
            self.messages = {}
            self.failed = []
            self.action = {
                yum.constants.TS_UPDATE: yum._('Updating'),
                yum.constants.TS_ERASE: yum._('Erasing'),
                yum.constants.TS_INSTALL: yum._('Installing'),
                yum.constants.TS_TRUEINSTALL: yum._('Installing'),
                yum.constants.TS_OBSOLETED: yum._('Obsoleted'),
                yum.constants.TS_OBSOLETING: yum._('Installing'),
                yum.constants.TS_UPDATED: yum._('Cleanup'),
                'repackaging': yum._('Repackaging')
            }
            # The fileaction are not translated, most sane IMHO / Tim
            self.fileaction = {
                yum.constants.TS_UPDATE: 'Updated',
                yum.constants.TS_ERASE: 'Erased',
                yum.constants.TS_INSTALL: 'Installed',
                yum.constants.TS_TRUEINSTALL: 'Installed',
                yum.constants.TS_OBSOLETED: 'Obsoleted',
                yum.constants.TS_OBSOLETING: 'Installed',
                yum.constants.TS_UPDATED: 'Cleanup'
            }
            self.logger = logging.getLogger(
                'yum.filelogging.RPMInstallCallback')

        def event(self, package, action, te_current, te_total, ts_current,
                  ts_total):
            # This would be used for a progress counter according to Yum docs
            pass

        def log_accumulated_errors(self):
            '''
            Convenience method for logging all messages from failed packages
            '''
            for pkg in self.failed:
                log.error('{0} {1}'.format(pkg, self.messages[pkg]))

        def errorlog(self, msg):
            # Log any error we receive
            log.error(msg)

        def filelog(self, package, action):
            if action == yum.constants.TS_FAILED:
                self.failed.append(package)
            else:
                if action in self.fileaction:
                    msg = '{0}: {1}'.format(self.fileaction[action], package)
                else:
                    msg = '{0}: {1}'.format(package, action)
                self.logger.info(msg)

        def scriptout(self, package, msgs):
            # This handler covers ancillary messages coming from the RPM script
            # Will sometimes contain more detailed error messages.
            self.messages[package] = msgs

    class _YumBase(yum.YumBase):
        def doLoggingSetup(self, debuglevel, errorlevel,
                           syslog_indent=None,
                           syslog_facility=None,
                           syslog_device='/dev/log'):
            '''
            This method is overridden in salt because we don't want syslog
            logging to happen.

            Additionally, no logging will be setup for yum.
            The logging handlers configure for yum were to ``sys.stdout``,
            ``sys.stderr`` and ``syslog``. We don't want none of those.
            Any logging will go through salt's logging handlers.
            '''

            # Just set the log levels to yum
            if debuglevel is not None:
                logging.getLogger('yum.verbose').setLevel(
                    yum.logginglevels.logLevelFromDebugLevel(debuglevel)
                )
            if errorlevel is not None:
                logging.getLogger('yum.verbose').setLevel(
                    yum.logginglevels.logLevelFromErrorLevel(errorlevel)
                )
            logging.getLogger('yum.filelogging').setLevel(logging.INFO)

except (ImportError, AttributeError):
    HAS_YUMDEPS = False

log = logging.getLogger(__name__)

# Define the module's virtual name
__virtualname__ = 'pkg'


def __virtual__():
    '''
    Only used if yum_provider is set to 'yumpkg_api'
    '''
    if __opts__.get('yum_provider') == 'yumpkg_api':
        global _parse_repo_file, list_repos, mod_repo, get_repo
        global del_repo, expand_repo_def
        _parse_repo_file = _namespaced_function(_parse_repo_file, globals())
        list_repos = _namespaced_function(list_repos, globals())
        mod_repo = _namespaced_function(mod_repo, globals())
        get_repo = _namespaced_function(get_repo, globals())
        del_repo = _namespaced_function(del_repo, globals())
        expand_repo_def = _namespaced_function(expand_repo_def, globals())
        return __virtualname__
    return False


def list_upgrades(refresh=True):
    '''
    Check whether or not an upgrade is available for all packages

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.list_upgrades
    '''
    if salt.utils.is_true(refresh):
        refresh_db()

    pkgs = list_pkgs()

    yumbase = _YumBase()
    versions_list = {}
    for pkgtype in ['updates']:
        pkglist = yumbase.doPackageLists(pkgtype)
        for pkg in pkgs:
            exactmatch, matched, unmatched = yum.packages.parsePackages(
                pkglist, [pkg]
            )
            for pkg in exactmatch:
                if pkg.arch in rpmUtils.arch.legitMultiArchesInSameLib() \
                        or pkg.arch == 'noarch':
                    versions_list[pkg['name']] = '-'.join(
                        [pkg['version'], pkg['release']]
                    )
    return versions_list


def _set_repo_options(yumbase, **kwargs):
    '''
    Accepts a _YumBase() object and runs member functions to enable/disable
    repos as needed.
    '''
    # Get repo options from the kwargs
    fromrepo = kwargs.get('fromrepo', '')
    repo = kwargs.get('repo', '')
    disablerepo = kwargs.get('disablerepo', '')
    enablerepo = kwargs.get('enablerepo', '')

    # Support old 'repo' argument
    if repo and not fromrepo:
        fromrepo = repo

    try:
        if fromrepo:
            log.info('Restricting to repo {0!r}'.format(fromrepo))
            yumbase.repos.disableRepo('*')
            yumbase.repos.enableRepo(fromrepo)
        else:
            if disablerepo:
                log.info('Disabling repo {0!r}'.format(disablerepo))
                yumbase.repos.disableRepo(disablerepo)
            if enablerepo:
                log.info('Enabling repo {0!r}'.format(enablerepo))
                yumbase.repos.enableRepo(enablerepo)
    except yum.Errors.RepoError as exc:
        return exc


def _pkg_arch(name):
    '''
    Returns a 2-tuple of the name and arch parts of the passed string. Note
    that packages that are for the system architecture should not have the
    architecture specified in the passed string.
    '''
    try:
        pkgname, pkgarch = name.rsplit('.', 1)
    except ValueError:
        return name, __grains__['osarch']
    else:
        if pkgarch not in __ARCHES:
            return name, __grains__['osarch']
        return pkgname, pkgarch


def latest_version(*names, **kwargs):
    '''
    Return the latest version of the named package available for upgrade or
    installation. If more than one package name is specified, a dict of
    name/version pairs is returned.

    If the latest version of a given package is already installed, an empty
    string will be returned for that package.

    A specific repo can be requested using the ``fromrepo`` keyword argument.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.latest_version <package name>
        salt '*' pkg.latest_version <package name> fromrepo=epel-testing
        salt '*' pkg.latest_version <package1> <package2> <package3> ...
    '''
    refresh = salt.utils.is_true(kwargs.pop('refresh', True))
    # FIXME: do stricter argument checking that somehow takes
    # _get_repo_options() into account

    if len(names) == 0:
        return ''
    ret = {}
    namearch_map = {}
    # Initialize the return dict with empty strings, and populate the namearch
    # dict
    for name in names:
        ret[name] = ''
        pkgname, pkgarch = _pkg_arch(name)
        namearch_map.setdefault(name, {})['name'] = pkgname
        namearch_map[name]['arch'] = pkgarch

    # Refresh before looking for the latest version available
    if refresh:
        refresh_db()

    yumbase = _YumBase()
    error = _set_repo_options(yumbase, **kwargs)
    if error:
        log.error(error)

    suffix_notneeded = rpmUtils.arch.legitMultiArchesInSameLib() + ['noarch']
    # look for available packages only, if package is already installed with
    # latest version it will not show up here.  If we want to use wildcards
    # here we can, but for now its exact match only.
    for pkgtype in ('available', 'updates'):
        pkglist = yumbase.doPackageLists(pkgtype)
        exactmatch, matched, unmatched = yum.packages.parsePackages(
            pkglist, [namearch_map[x]['name'] for x in names]
        )
        for name in names:
            for pkg in (x for x in exactmatch
                        if x.name == namearch_map[name]['name']):
                if (all(x in suffix_notneeded
                        for x in (namearch_map[name]['arch'], pkg.arch))
                        or namearch_map[name]['arch'] == pkg.arch):
                    ret[name] = '-'.join([pkg.version, pkg.release])

    # Return a string if only one package name passed
    if len(names) == 1:
        return ret[names[0]]
    return ret

# available_version is being deprecated
available_version = latest_version


def upgrade_available(name):
    '''
    Check whether or not an upgrade is available for a given package

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.upgrade_available <package name>
    '''
    return latest_version(name) != ''


def version(*names, **kwargs):
    '''
    Returns a string representing the package version or an empty string if not
    installed. If more than one package name is specified, a dict of
    name/version pairs is returned.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.version <package name>
        salt '*' pkg.version <package1> <package2> <package3> ...
    '''
    return __salt__['pkg_resource.version'](*names, **kwargs)


def list_pkgs(versions_as_list=False, **kwargs):
    '''
    List the packages currently installed in a dict::

        {'<package_name>': '<version>'}

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.list_pkgs
    '''
    versions_as_list = salt.utils.is_true(versions_as_list)
    # 'removed' not yet implemented or not applicable
    if salt.utils.is_true(kwargs.get('removed')):
        return {}

    if 'pkg.list_pkgs' in __context__:
        if versions_as_list:
            return __context__['pkg.list_pkgs']
        else:
            ret = copy.deepcopy(__context__['pkg.list_pkgs'])
            __salt__['pkg_resource.stringify'](ret)
            return ret

    ret = {}
    yb = _YumBase()
    for p in yb.rpmdb:
        name = p.name
        if __grains__.get('cpuarch', '') == 'x86_64' \
                and re.match(r'i\d86', p.arch):
            name += '.{0}'.format(p.arch)
        pkgver = p.version
        if p.release:
            pkgver += '-{0}'.format(p.release)
        __salt__['pkg_resource.add_pkg'](ret, name, pkgver)

    __salt__['pkg_resource.sort_pkglist'](ret)
    __context__['pkg.list_pkgs'] = copy.deepcopy(ret)
    if not versions_as_list:
        __salt__['pkg_resource.stringify'](ret)
    return ret


def list_repo_pkgs(*args, **kwargs):
    '''
    .. versionadded:: 2014.1.0 (Hydrogen)

    Returns all available packages. Optionally, package names can be passed and
    the results will be filtered to packages matching those names. This can be
    helpful in discovering the version or repo to specify in a pkg.installed
    state. The return data is a dictionary of repo names, with each repo having
    a list of dictionaries denoting the package name and version. An example of
    the return data would look like this:

    .. code-block:: python

        {
            '<repo_name>': [
                {'<package1>': '<version1>'},
                {'<package2>': '<version2>'},
                {'<package3>': '<version3>'}
            ]
        }

    fromrepo : None
        Only include results from the specified repo(s). Multiple repos can be
        specified, comma-separated.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.list_repo_pkgs
        salt '*' pkg.list_repo_pkgs foo bar baz
        salt '*' pkg.list_repo_pkgs 'samba4*' fromrepo=base,updates
    '''
    try:
        repos = tuple(x.strip() for x in kwargs.get('fromrepo').split(','))
    except AttributeError:
        # Search in all enabled repos
        repos = tuple(
            x for x, y in list_repos().iteritems()
            if str(y.get('enabled', '1')) == '1'
        )

    yb = yum.YumBase()
    yb.conf.cache = 1
    ret = {}
    suffix_notneeded = rpmUtils.arch.legitMultiArchesInSameLib() + ['noarch']
    for pkg in sorted(yb.pkgSack.returnPackages()):
        if pkg.repoid in repos:
            if pkg.arch in suffix_notneeded:
                name = pkg.name
            else:
                name = '.'.join((pkg.name, pkg.arch))
            version = '-'.join((pkg.version, pkg.release))
            if (not args) or any(fnmatch.fnmatch(name, x) for x in args):
                ret.setdefault(pkg.repoid, []).append({name: version})

    for reponame in ret:
        ret[reponame].sort()
    return ret


def check_db(*names, **kwargs):
    '''
    .. versionadded:: 0.17.0

    Returns a dict containing the following information for each specified
    package:

    1. A key ``found``, which will be a boolean value denoting if a match was
       found in the package database.
    2. If ``found`` is ``False``, then a second key called ``suggestions`` will
       be present, which will contain a list of possible matches.

    The ``fromrepo``, ``enablerepo``, and ``disablerepo`` arguments are
    supported, as used in pkg states.

    CLI Examples:

    .. code-block:: bash

        salt '*' pkg.check_db <package1> <package2> <package3>
        salt '*' pkg.check_db <package1> <package2> <package3> fromrepo=epel-testing
    '''
    yumbase = _YumBase()
    error = _set_repo_options(yumbase, **kwargs)
    if error:
        log.error(error)
        return {}

    ret = {}
    for name in names:
        pkgname, pkgarch = _pkg_arch(name)
        ret.setdefault(name, {})['found'] = bool(
            [x for x in yumbase.searchPackages(('name', 'arch'), (pkgname,))
             if x.name == pkgname and x.arch in (pkgarch, 'noarch')]
        )
        if ret[name]['found'] is False:
            provides = [
                x for x in yumbase.whatProvides(
                    pkgname, None, None
                ).returnPackages()
                if x.arch in (pkgarch, 'noarch')
            ]
            if provides:
                for pkg in provides:
                    ret[name].setdefault('suggestions', []).append(pkg.name)
            else:
                ret[name]['suggestions'] = []
    return ret


def refresh_db():
    '''
    Since yum refreshes the database automatically, this runs a yum clean,
    so that the next yum operation will have a clean database

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.refresh_db
    '''
    yumbase = _YumBase()
    yumbase.cleanMetadata()
    return True


def clean_metadata():
    '''
    Cleans local yum metadata.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.clean_metadata
    '''
    return refresh_db()


def group_install(name=None,
                  groups=None,
                  skip=None,
                  include=None,
                  **kwargs):
    '''
    Install the passed package group(s). This is basically a wrapper around
    pkg.install, which performs package group resolution for the user. This
    function is currently considered "experimental", and should be expected to
    undergo changes before it becomes official.

    name
        The name of a single package group to install. Note that this option is
        ignored if "groups" is passed.

    groups
        The names of multiple packages which are to be installed.

        CLI Example:

        .. code-block:: bash

            salt '*' pkg.group_install groups='["Group 1", "Group 2"]'

    skip
        The name(s), in a list, of any packages that would normally be
        installed by the package group ("default" packages), which should not
        be installed.

        CLI Examples:

        .. code-block:: bash

            salt '*' pkg.group_install 'My Group' skip='["foo", "bar"]'

    include
        The name(s), in a list, of any packages which are included in a group,
        which would not normally be installed ("optional" packages). Note that
        this will nor enforce group membership; if you include packages which
        are not members of the specified groups, they will still be installed.

        CLI Examples:

        .. code-block:: bash

            salt '*' pkg.group_install 'My Group' include='["foo", "bar"]'

    other arguments
        Because this is essentially a wrapper around pkg.install, any argument
        which can be passed to pkg.install may also be included here, and it
        will be passed along wholesale.
    '''
    pkg_groups = []
    if groups:
        pkg_groups = yaml.safe_load(groups)
    else:
        pkg_groups.append(name)

    skip_pkgs = []
    if skip:
        skip_pkgs = yaml.safe_load(skip)

    include = []
    if include:
        include = yaml.safe_load(include)

    pkgs = []
    for group in pkg_groups:
        group_detail = group_info(group)
        for package in group_detail.get('mandatory packages', {}):
            pkgs.append(package)
        for package in group_detail.get('default packages', {}):
            if package not in skip_pkgs:
                pkgs.append(package)
        for package in include:
            pkgs.append(package)

    install_pkgs = yaml.safe_dump(pkgs)
    return install(pkgs=install_pkgs, **kwargs)


def install(name=None,
            refresh=False,
            skip_verify=False,
            pkgs=None,
            sources=None,
            **kwargs):
    '''
    Install the passed package(s), add refresh=True to clean the yum database
    before package is installed.

    name
        The name of the package to be installed. Note that this parameter is
        ignored if either "pkgs" or "sources" is passed. Additionally, please
        note that this option can only be used to install packages from a
        software repository. To install a package file manually, use the
        "sources" option.

        32-bit packages can be installed on 64-bit systems by appending the
        architecture designation (``.i686``, ``.i586``, etc.) to the end of the
        package name.

        CLI Example:

        .. code-block:: bash

            salt '*' pkg.install <package name>

    refresh
        Whether or not to update the yum database before executing.

    skip_verify
        Skip the GPG verification check. (e.g., ``--nogpgcheck``)

    version
        Install a specific version of the package, e.g. 1.2.3-4.el6. Ignored
        if "pkgs" or "sources" is passed.


    Repository Options:

    fromrepo
        Specify a package repository (or repositories) from which to install.
        (e.g., ``yum --disablerepo='*' --enablerepo='somerepo'``)

    enablerepo
        Specify a disabled package repository (or repositories) to enable.
        (e.g., ``yum --enablerepo='somerepo'``)

    disablerepo
        Specify an enabled package repository (or repositories) to disable.
        (e.g., ``yum --disablerepo='somerepo'``)


    Multiple Package Installation Options:

    pkgs
        A list of packages to install from a software repository. Must be
        passed as a python list. A specific version number can be specified
        by using a single-element dict representing the package and its
        version.

        CLI Examples:

        .. code-block:: bash

            salt '*' pkg.install pkgs='["foo", "bar"]'
            salt '*' pkg.install pkgs='["foo", {"bar": "1.2.3-4.el6"}]'

    sources
        A list of RPM packages to install. Must be passed as a list of dicts,
        with the keys being package names, and the values being the source URI
        or local path to the package.

        CLI Example:

        .. code-block:: bash

            salt '*' pkg.install sources='[{"foo": "salt://foo.rpm"}, {"bar": "salt://bar.rpm"}]'


    Returns a dict containing the new package names and versions::

        {'<package>': {'old': '<old-version>',
                       'new': '<new-version>'}}
    '''
    if salt.utils.is_true(refresh):
        refresh_db()

    pkg_params, pkg_type = __salt__['pkg_resource.parse_targets'](name,
                                                                  pkgs,
                                                                  sources,
                                                                  **kwargs)
    if pkg_params is None or len(pkg_params) == 0:
        return {}

    old = list_pkgs()

    yumbase = _YumBase()
    setattr(yumbase.conf, 'assumeyes', True)
    setattr(yumbase.conf, 'gpgcheck', not skip_verify)

    version = kwargs.get('version')
    if version:
        if pkgs is None and sources is None:
            # Allow "version" to work for single package target
            pkg_params = {name: version}
        else:
            log.warning('"version" parameter will be ignored for multiple '
                        'package targets')

    error = _set_repo_options(yumbase, **kwargs)
    if error:
        log.error(error)
        return {}

    try:
        for pkgname in pkg_params:
            if pkg_type == 'file':
                log.info(
                    'Selecting "{0}" for local installation'.format(pkgname)
                )
                installed = yumbase.installLocal(pkgname)
                # if yum didn't install anything, maybe its a downgrade?
                log.debug('Added {0} transactions'.format(len(installed)))
                if len(installed) == 0 and pkgname not in old.keys():
                    log.info('Upgrade failed, trying local downgrade')
                    yumbase.downgradeLocal(pkgname)
            else:
                version = pkg_params[pkgname]
                if version is not None:
                    if __grains__.get('cpuarch', '') == 'x86_64':
                        try:
                            arch = re.search(r'(\.i\d86)$', pkgname).group(1)
                        except AttributeError:
                            arch = ''
                        else:
                            # Remove arch from pkgname
                            pkgname = pkgname[:-len(arch)]
                    else:
                        arch = ''
                    target = '{0}-{1}{2}'.format(pkgname, version, arch)
                else:
                    target = pkgname
                log.info('Selecting "{0}" for installation'.format(target))
                # Changed to pattern to allow specific package versions
                installed = yumbase.install(pattern=target)
                # if yum didn't install anything, maybe its a downgrade?
                log.debug('Added {0} transactions'.format(len(installed)))
                if len(installed) == 0 and target not in old.keys():
                    log.info('Upgrade failed, trying downgrade')
                    yumbase.downgrade(pattern=target)

        # Resolve Deps before attempting install. This needs to be improved by
        # also tracking any deps that may get upgraded/installed during this
        # process. For now only the version of the package(s) you request be
        # installed is tracked.
        log.info('Resolving dependencies')
        yumbase.resolveDeps()
        log.info('Processing transaction')
        yumlogger = _YumLogger()
        yumbase.processTransaction(rpmDisplay=yumlogger)
        yumlogger.log_accumulated_errors()
        yumbase.closeRpmDB()
    except Exception as e:
        log.error('Install failed: {0}'.format(e))

    __context__.pop('pkg.list_pkgs', None)
    new = list_pkgs()
    return salt.utils.compare_dicts(old, new)


def upgrade(refresh=True):
    '''
    Run a full system upgrade, a yum upgrade

    Return a dict containing the new package names and versions::

        {'<package>': {'old': '<old-version>',
                       'new': '<new-version>'}}

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.upgrade
    '''
    if salt.utils.is_true(refresh):
        refresh_db()

    yumbase = _YumBase()
    setattr(yumbase.conf, 'assumeyes', True)

    old = list_pkgs()

    try:
        # ideally we would look in the yum transaction and get info on all the
        # packages that are going to be upgraded and only look up old/new
        # version info on those packages.
        yumbase.update()
        log.info('Resolving dependencies')
        yumbase.resolveDeps()
        log.info('Processing transaction')
        yumlogger = _YumLogger()
        yumbase.processTransaction(rpmDisplay=yumlogger)
        yumlogger.log_accumulated_errors()
        yumbase.closeRpmDB()
    except Exception as e:
        log.error('Upgrade failed: {0}'.format(e))

    __context__.pop('pkg.list_pkgs', None)
    new = list_pkgs()
    return salt.utils.compare_dicts(old, new)


def remove(name=None, pkgs=None, **kwargs):
    '''
    Removes packages using python API for yum.

    name
        The name of the package to be deleted.


    Multiple Package Options:

    pkgs
        A list of packages to delete. Must be passed as a python list. The
        ``name`` parameter will be ignored if this option is passed.

    .. versionadded:: 0.16.0


    Returns a dict containing the changes.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.remove <package name>
        salt '*' pkg.remove <package1>,<package2>,<package3>
        salt '*' pkg.remove pkgs='["foo", "bar"]'
    '''

    pkg_params = __salt__['pkg_resource.parse_targets'](name, pkgs)[0]
    old = list_pkgs()
    targets = [x for x in pkg_params if x in old]
    if not targets:
        return {}

    yumbase = _YumBase()
    setattr(yumbase.conf, 'assumeyes', True)

    # same comments as in upgrade for remove.
    for target in targets:
        if __grains__.get('cpuarch', '') == 'x86_64':
            try:
                arch = re.search(r'(\.i\d86)$', target).group(1)
            except AttributeError:
                arch = None
            else:
                # Remove arch from pkgname
                target = target[:-len(arch)]
                arch = arch.lstrip('.')
        else:
            arch = None
        yumbase.remove(name=target, arch=arch)

    log.info('Performing transaction test')
    try:
        callback = yum.callbacks.ProcessTransNoOutputCallback()
        result = yumbase._doTestTransaction(callback)
    except yum.Errors.YumRPMCheckError as exc:
        raise CommandExecutionError('\n'.join(exc.__dict__['value']))

    log.info('Resolving dependencies')
    yumbase.resolveDeps()
    log.info('Processing transaction')
    yumlogger = _YumLogger()
    yumbase.processTransaction(rpmDisplay=yumlogger)
    yumlogger.log_accumulated_errors()
    yumbase.closeRpmDB()

    __context__.pop('pkg.list_pkgs', None)
    new = list_pkgs()
    return salt.utils.compare_dicts(old, new)


def purge(name=None, pkgs=None, **kwargs):
    '''
    Package purges are not supported by yum, this function is identical to
    :mod:`pkg.remove <salt.modules.yumpkg.remove>`.

    name
        The name of the package to be deleted.


    Multiple Package Options:

    pkgs
        A list of packages to delete. Must be passed as a python list. The
        ``name`` parameter will be ignored if this option is passed.

    .. versionadded:: 0.16.0


    Returns a dict containing the changes.

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.purge <package name>
        salt '*' pkg.purge <package1>,<package2>,<package3>
        salt '*' pkg.purge pkgs='["foo", "bar"]'
    '''
    return remove(name=name, pkgs=pkgs)


def verify(*package):
    '''
    Runs an rpm -Va on a system, and returns the results in a dict

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.verify
    '''
    return __salt__['lowpkg.verify'](*package)


def group_list():
    '''
    Lists all groups known by yum on this system

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.group_list
    '''
    ret = {'installed': [], 'available': [], 'available languages': {}}
    yumbase = _YumBase()
    (installed, available) = yumbase.doGroupLists()
    for group in installed:
        ret['installed'].append(group.name)
    for group in available:
        if group.langonly:
            ret['available languages'][group.name] = {
                'name': group.name,
                'language': group.langonly}
        else:
            ret['available'].append(group.name)
    return ret


def group_info(groupname):
    '''
    Lists packages belonging to a certain group

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.group_info 'Perl Support'
    '''
    yumbase = _YumBase()
    (installed, available) = yumbase.doGroupLists()
    for group in installed + available:
        if group.name.lower() == groupname.lower():
            return {'mandatory packages': group.mandatory_packages,
                    'optional packages': group.optional_packages,
                    'default packages': group.default_packages,
                    'conditional packages': group.conditional_packages,
                    'description': group.description}


def group_diff(groupname):
    '''
    Lists packages belonging to a certain group, and which are installed

    CLI Example:

    .. code-block:: bash

        salt '*' pkg.group_diff 'Perl Support'
    '''
    ret = {
        'mandatory packages': {'installed': [], 'not installed': []},
        'optional packages': {'installed': [], 'not installed': []},
        'default packages': {'installed': [], 'not installed': []},
        'conditional packages': {'installed': [], 'not installed': []},
    }
    pkgs = list_pkgs()
    yumbase = _YumBase()
    (installed, available) = yumbase.doGroupLists()
    for group in installed:
        if group.name == groupname:
            for pkg in group.mandatory_packages:
                if pkg in pkgs:
                    ret['mandatory packages']['installed'].append(pkg)
                else:
                    ret['mandatory packages']['not installed'].append(pkg)
            for pkg in group.optional_packages:
                if pkg in pkgs:
                    ret['optional packages']['installed'].append(pkg)
                else:
                    ret['optional packages']['not installed'].append(pkg)
            for pkg in group.default_packages:
                if pkg in pkgs:
                    ret['default packages']['installed'].append(pkg)
                else:
                    ret['default packages']['not installed'].append(pkg)
            for pkg in group.conditional_packages:
                if pkg in pkgs:
                    ret['conditional packages']['installed'].append(pkg)
                else:
                    ret['conditional packages']['not installed'].append(pkg)
            return {groupname: ret}


def file_list(*packages):
    '''
    List the files that belong to a package. Not specifying any packages will
    return a list of _every_ file on the system's rpm database (not generally
    recommended).

    CLI Examples:

    .. code-block:: bash

        salt '*' pkg.file_list httpd
        salt '*' pkg.file_list httpd postfix
        salt '*' pkg.file_list
    '''
    return __salt__['lowpkg.file_list'](*packages)


def file_dict(*packages):
    '''
    List the files that belong to a package, grouped by package. Not
    specifying any packages will return a list of _every_ file on the system's
    rpm database (not generally recommended).

    CLI Examples:

    .. code-block:: bash

        salt '*' pkg.file_list httpd
        salt '*' pkg.file_list httpd postfix
        salt '*' pkg.file_list
    '''
    return __salt__['lowpkg.file_dict'](*packages)

########NEW FILE########
__FILENAME__ = pyobjects
# -*- coding: utf-8 -*-
'''
Backport of Evan Borgstrom's pyobjects renderer.

Available (with full docs) in develop branch of Salt at
https://github.com/saltstack/salt/blob/develop/salt/renderers/pyobjects.py

To use, copy this file to the _renderers directory within your file roots
(e.g., /srv/salt/_renderers/pybojects.py) and execute:
'''

# Original file:
# https://github.com/saltstack/salt/blob/develop/salt/utils/pyobjects.py
'''
:maintainer: Evan Borgstrom <evan@borgstrom.ca>

Pythonic object interface to creating state data, see the pyobjects renderer
for more documentation.
'''
from collections import namedtuple

from salt.utils.odict import OrderedDict

REQUISITES = ('require', 'watch', 'use', 'require_in', 'watch_in', 'use_in')


class StateException(Exception):
    pass


class DuplicateState(StateException):
    pass


class InvalidFunction(StateException):
    pass


class StateRegistry(object):
    '''
    The StateRegistry holds all of the states that have been created.
    '''
    def __init__(self):
        self.empty()

    def empty(self):
        self.states = OrderedDict()
        self.requisites = []
        self.includes = []
        self.extends = OrderedDict()

    def include(self, *args):
        self.includes += args

    def salt_data(self):
        states = OrderedDict([
            (id_, state())
            for id_, state in self.states.iteritems()
        ])

        if self.includes:
            states['include'] = self.includes

        if self.extends:
            states['extend'] = OrderedDict([
                (id_, state())
                for id_, state in self.extends.iteritems()
            ])

        self.empty()

        return states

    def add(self, id_, state, extend=False):
        if extend:
            attr = self.extends
        else:
            attr = self.states

        if id_ in attr:
            raise DuplicateState("A state with id '%s' already exists" % id_)

        # if we have requisites in our stack then add them to the state
        if len(self.requisites) > 0:
            for req in self.requisites:
                if req.requisite not in state.kwargs:
                    state.kwargs[req.requisite] = []
                state.kwargs[req.requisite].append(req())

        attr[id_] = state

    def extend(self, id_, state):
        self.add(id_, state, extend=True)

    def make_extend(self, name):
        return StateExtend(name)

    def push_requisite(self, requisite):
        self.requisites.append(requisite)

    def pop_requisite(self):
        del self.requisites[-1]


class StateExtend(object):
    def __init__(self, name):
        self.name = name


class StateRequisite(object):
    def __init__(self, requisite, module, id_, registry):
        self.requisite = requisite
        self.module = module
        self.id_ = id_
        self.registry = registry

    def __call__(self):
        return {self.module: self.id_}

    def __enter__(self):
        self.registry.push_requisite(self)

    def __exit__(self, type, value, traceback):
        self.registry.pop_requisite()


class StateFactory(object):
    '''
    The StateFactory is used to generate new States through a natural syntax

    It is used by initializing it with the name of the salt module::

        File = StateFactory("file")

    Any attribute accessed on the instance returned by StateFactory is a lambda
    that is a short cut for generating State objects::

        File.managed('/path/', owner='root', group='root')

    The kwargs are passed through to the State object
    '''
    def __init__(self, module, registry, valid_funcs=None):
        self.module = module
        self.registry = registry
        if valid_funcs is None:
            valid_funcs = []
        self.valid_funcs = valid_funcs

    def __getattr__(self, func):
        if len(self.valid_funcs) > 0 and func not in self.valid_funcs:
            raise InvalidFunction("The function '%s' does not exist in the "
                                  "StateFactory for '%s'" % (func, self.module))

        def make_state(id_, **kwargs):
            return State(
                id_,
                self.module,
                func,
                registry=self.registry,
                **kwargs
            )
        return make_state

    def __call__(self, id_, requisite='require'):
        '''
        When an object is called it is being used as a requisite
        '''
        # return the correct data structure for the requisite
        return StateRequisite(requisite, self.module, id_,
                              registry=self.registry)


class State(object):
    '''
    This represents a single item in the state tree

    The id_ is the id of the state, the func is the full name of the salt
    state (ie. file.managed). All the keyword args you pass in become the
    properties of your state.

    The registry is where the state should be stored. It is optional and will
    use the default registry if not specified.
    '''

    def __init__(self, id_, module, func, registry, **kwargs):
        self.id_ = id_
        self.module = module
        self.func = func
        self.kwargs = kwargs
        self.registry = registry

        if isinstance(self.id_, StateExtend):
            self.registry.extend(self.id_.name, self)
            self.id_ = self.id_.name
        else:
            self.registry.add(self.id_, self)

        self.requisite = StateRequisite('require', self.module, self.id_,
                                        registry=self.registry)

    @property
    def attrs(self):
        kwargs = self.kwargs

        # handle our requisites
        for attr in REQUISITES:
            if attr in kwargs:
                # our requisites should all be lists, but when you only have a
                # single item it's more convenient to provide it without
                # wrapping it in a list. transform them into a list
                if not isinstance(kwargs[attr], list):
                    kwargs[attr] = [kwargs[attr]]

                # rebuild the requisite list transforming any of the actual
                # StateRequisite objects into their representative dict
                kwargs[attr] = [
                    req() if isinstance(req, StateRequisite) else req
                    for req in kwargs[attr]
                ]

        # build our attrs from kwargs. we sort the kwargs by key so that we
        # have consistent ordering for tests
        return [
            {k: kwargs[k]}
            for k in sorted(kwargs.iterkeys())
        ]

    @property
    def full_func(self):
        return "%s.%s" % (self.module, self.func)

    def __str__(self):
        return "%s = %s:%s" % (self.id_, self.full_func, self.attrs)

    def __call__(self):
        return {
            self.full_func: self.attrs
        }

    def __enter__(self):
        self.registry.push_requisite(self.requisite)

    def __exit__(self, type, value, traceback):
        self.registry.pop_requisite()


class SaltObject(object):
    '''
    Object based interface to the functions in __salt__

    .. code-block:: python
       :linenos:
        Salt = SaltObject(__salt__)
        Salt.cmd.run(bar)
    '''
    def __init__(self, salt):
        _mods = {}
        for full_func in salt:
            mod, func = full_func.split('.')

            if mod not in _mods:
                _mods[mod] = {}
            _mods[mod][func] = salt[full_func]

        # now transform using namedtuples
        self.mods = {}
        for mod in _mods:
            mod_object = namedtuple('%sModule' % mod.capitalize(),
                                    _mods[mod].keys())

            self.mods[mod] = mod_object(**_mods[mod])

    def __getattr__(self, mod):
        if mod not in self.mods:
            raise AttributeError

        return self.mods[mod]


# Original file:
# https://github.com/saltstack/salt/blob/develop/salt/renderers/pyobjects.py
'''
Python renderer that includes a Pythonic Object based interface

:maintainer: Evan Borgstrom <evan@borgstrom.ca>

Let's take a look at how you use pyobjects in a state file. Here's a quick
example that ensures the ``/tmp`` directory is in the correct state.

.. code-block:: python
   :linenos:
    #!pyobjects

    File.managed("/tmp", user='root', group='root', mode='1777')

Nice and Pythonic!

By using the "shebang" syntax to switch to the pyobjects renderer we can now
write our state data using an object based interface that should feel at home
to python developers. You can import any module and do anything that you'd
like (with caution, importing sqlalchemy, django or other large frameworks has
not been tested yet). Using the pyobjects renderer is exactly the same as
using the built-in Python renderer with the exception that pyobjects provides
you with an object based interface for generating state data.

Creating state data
^^^^^^^^^^^^^^^^^^^
Pyobjects takes care of creating an object for each of the available states on
the minion. Each state is represented by an object that is the CamelCase
version of it's name (ie. ``File``, ``Service``, ``User``, etc), and these
objects expose all of their available state functions (ie. ``File.managed``,
``Service.running``, etc).

The name of the state is split based upon underscores (``_``), then each part
is capitalized and finally the parts are joined back together.

Some examples:

* ``postgres_user`` becomes ``PostgresUser``
* ``ssh_known_hosts`` becomes ``SshKnownHosts``

Context Managers and requisites
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
How about something a little more complex. Here we're going to get into the
core of what makes pyobjects the best way to write states.

.. code-block:: python
   :linenos:
    #!pyobjects

    with Pkg.installed("nginx"):
        Service.running("nginx", enable=True)

        with Service("nginx", "watch_in"):
            File.managed("/etc/nginx/conf.d/mysite.conf",
                         owner='root', group='root', mode='0444',
                         source='salt://nginx/mysite.conf')


The objects that are returned from each of the magic method calls are setup to
be used a Python context managers (``with``) and when you use them as such all
declarations made within the scope will **automatically** use the enclosing
state as a requisite!

The above could have also been written use direct requisite statements as.

.. code-block:: python
   :linenos:
    #!pyobjects

    Pkg.installed("nginx")
    Service.running("nginx", enable=True, require=Pkg("nginx"))
    File.managed("/etc/nginx/conf.d/mysite.conf",
                 owner='root', group='root', mode='0444',
                 source='salt://nginx/mysite.conf',
                 watch_in=Service("nginx"))

You can use the direct requisite statement for referencing states that are
generated outside of the current file.

.. code-block:: python
   :linenos:
    #!pyobjects

    # some-other-package is defined in some other state file
    Pkg.installed("nginx", require=Pkg("some-other-package"))

The last thing that direct requisites provide is the ability to select which
of the SaltStack requisites you want to use (require, require_in, watch,
watch_in, use & use_in) when using the requisite as a context manager.

.. code-block:: python
   :linenos:
    #!pyobjects

    with Service("my-service", "watch_in"):
        ...

The above example would cause all declarations inside the scope of the context
manager to automatically have their ``watch_in`` set to
``Service("my-service")``.

Including and Extending
^^^^^^^^^^^^^^^^^^^^^^^

To include other states use the ``include()`` function. It takes one name per
state to include.

To extend another state use the ``extend()`` function on the name when creating
a state.

.. code-block:: python
   :linenos:
    #!pyobjects

    include('http', 'ssh')

    Service.running(extend('apache'),
                    watch=[{'file': '/etc/httpd/extra/httpd-vhosts.conf'}])

Salt object
^^^^^^^^^^^
In the spirit of the object interface for creating state data pyobjects also
provides a simple object interface to the ``__salt__`` object.

A function named ``salt`` exists in scope for your sls files and will dispatch
its attributes to the ``__salt__`` dictionary.

The following lines are functionally equivalent:

.. code-block:: python
   :linenos:
    #!pyobjects

    ret = salt.cmd.run(bar)
    ret = __salt__['cmd.run'](bar)

Pillar, grain & mine data
^^^^^^^^^^^^^^^^^^^^^^^^^
Pyobjects provides shortcut functions for calling ``pillar.get``,
``grains.get`` & ``mine.get`` on the ``__salt__`` object. This helps maintain
the readability of your state files.

Each type of data can be access by a function of the same name: ``pillar()``,
``grains()`` and ``mine()``.

The following pairs of lines are functionally equivalent:

.. code-block:: python
   :linenos:
    #!pyobjects

    value = pillar('foo:bar:baz', 'qux')
    value = __salt__['pillar.get']('foo:bar:baz', 'qux')

    value = grains('pkg:apache')
    value = __salt__['grains.get']('pkg:apache')

    value = mine('os:Fedora', 'network.interfaces', 'grain')
    value = __salt__['mine.get']('os:Fedora', 'network.interfaces', 'grain')


TODO
^^^^
* Interface for working with reactor files
'''

import logging
import sys


log = logging.getLogger(__name__)


def render(template, saltenv='base', sls='',
           tmplpath=None, rendered_sls=None,
           _states=None, **kwargs):

    _globals = {}
    _locals = {}

    _registry = StateRegistry()
    if _states is None:
        try:
            _states = __states__
        except NameError:
            from salt.loader import states
            __opts__['grains'] = __grains__
            __opts__['pillar'] = __pillar__
            _states = states(__opts__, __salt__)

    # build our list of states and functions
    _st_funcs = {}
    for func in _states:
        (mod, func) = func.split(".")
        if mod not in _st_funcs:
            _st_funcs[mod] = []
        _st_funcs[mod].append(func)

    # create our StateFactory objects
    _st_globals = {'StateFactory': StateFactory, '_registry': _registry}
    for mod in _st_funcs:
        _st_locals = {}
        _st_funcs[mod].sort()
        mod_camel = ''.join([
            part.capitalize()
            for part in mod.split('_')
        ])
        mod_cmd = "%s = StateFactory('%s', registry=_registry, valid_funcs=['%s'])" % (
            mod_camel, mod,
            "','".join(_st_funcs[mod])
        )
        if sys.version > 3:
            exec(mod_cmd, _st_globals, _st_locals)
        else:
            exec mod_cmd in _st_globals, _st_locals
        _globals[mod_camel] = _st_locals[mod_camel]

    # add our Include and Extend functions
    _globals['include'] = _registry.include
    _globals['extend'] = _registry.make_extend

    # for convenience
    try:
        _globals.update({
            # salt, pillar & grains all provide shortcuts or object interfaces
            'salt': SaltObject(__salt__),
            'pillar': __salt__['pillar.get'],
            'grains': __salt__['grains.get'],
            'mine': __salt__['mine.get'],

            # the "dunder" formats are still available for direct use
            '__salt__': __salt__,
            '__pillar__': __pillar__,
            '__grains__': __grains__
        })
    except NameError:
        pass

    if sys.version > 3:
        exec(template.read(), _globals, _locals)
    else:
        exec template.read() in _globals, _locals

    return _registry.salt_data()

########NEW FILE########
__FILENAME__ = ansible
# A salt ansible state module that lets you use ansible
# modules as salt states like this:
#
# test_1:
#   ansible.command:
#     - args: /bin/ls -la
#     - chdir: /Users/jkuan
#
# test_2:
#   ansible.shell:
#     - args: echo 'hohoho' > ~/hoho.txt
#
# test_3:
#   ansible:
#     - setup
#
# test_4:
#   ansible.file:
#     - path: /etc/hosts
#     - dest: ~/hhh.txt
#     - mode: 644
#
# test_5:
#   ansible.easy_install:
#     - name_: sphinx
#
# The special 'args' argument is used for specifying the arguments
# to the ansible module. 'name=value' arguments can also be specified
# separately as shown in the example(test_4). It's also possible to
# mix 'args' and '- name: value' in a state, and in which case, the
# name-value's will be appended to 'args' as 'name=value' pairs.
#
# To work around salt's use of '- name' in state specification, if
# an ansible module has a 'name' argument, then it must be written
# as 'name_' if it is to be specified separately from 'args'.
#
# See the ansmod.py salt module for more information.
#
# To set it up, you'll need ansible installed on minion machines
# so that salt can run ansible locally on the machines. Make sure
# cd / && python -c 'import ansible' succeeds.
#
# Currently, you might also need to define the ansible.modules_dir
# property in your minion configuration file. It should to be set
# to your ansible/library/, where the ansible modules resides.
#
# Note: Not all ansible modules will be available. Those that are
# handled specially(eg, template, fetch, raw, shell) by ansible
# won't be available, except for 'shell'.
#
#
__opts__ = {}

import logging
log = logging.getLogger(__name__)

def __init__(opts):
    """Generate a state function for each ansible module found. """

    # ask salt to load and initialize the ansmod salt module
    from salt.loader import _create_loader, loaded_base_name
    tag = 'module'
    modname = 'ansmod'
    load = _create_loader(opts, 'modules', tag)
    load.gen_module(modname, {})

    # get the loaded ansmod module
    import sys
    try:
        ansmod = sys.modules[loaded_base_name+'.'+tag+'.'+modname]
    except KeyError:
        log.warn("Make sure the %s salt module's been loaded correctly!" \
                  % modname)
    else:
        # populate the state functions in this module
        mod = globals()
        for state in ansmod.STATE_NAMES:
            mod[state] = ansmod._state_func

        # make the use of the shell module actually invokes the
        # command module instead.
        ansmod.STATE_NAMES['shell'] = 'command'


def shell(state, **kws):
    args = kws.pop('args', '')
    return command(state, args=args+'#USE_SHELL', **kws)
    # Note: command will be defined after module __init__


########NEW FILE########
__FILENAME__ = apt_repository
# -*- coding: utf-8 -*-
# author: Bruno Clermont <patate@fastmail.cn>

'''
APT repository states
=====================

Handle Debian, Ubuntu and other Debian based distribution APT repositories

'''


import urlparse

from salt import exceptions, utils


def __virtual__():
    '''
    Verify apt is installed.
    '''
    try:
        utils.check_or_die('apt-key')
        return 'apt_repository'
    except exceptions.CommandNotFoundError:
        return False


def present(address, components, distribution=None, source=False, key_id=None,
            key_server=None, in_sources_list_d=True, filename=None):
    '''
    Manage a APT repository such as an Ubuntu PPA

    .. code-block:: yaml

    rabbitmq-server:
      apt_repository:
        - present
        - address: http://www.rabbitmq.com/debian/
        - components:
          - main
        - distribution: testing
        - key_server: pgp.mit.edu
        - key_id: 056E8E56

    address
        Repository address, usually a HTTP or HTTPs URL

    components
        List of repository components, such as 'main'

    distribution:
        Set this to use a different distribution than the one the host that run
        this state.

    source
        Add source "deb-src" statement? not the default.

    key_id
        GnuPG/PGP key ID used to authenticate packages of this repository.

    key_server
        The address of the PGP key server.
        This argument is ignored if key_id is unset.

    in_sources_list_d
        In many distribution, there is a directory /etc/apt/sources.list.d/
        that is included when you run apt-get command.
        Create a file there instead of change /etc/apt/sources.list
        This is used by default.
    '''
    if distribution is None:
        distribution = __salt__['grains.item']('oscodename')['oscodename']

    if filename is None:
        url = urlparse.urlparse(address)
        if not url.scheme:
            return {'name': address, 'result': False, 'changes': {},
                    'comment': "Invalid address '{0}'".format(address)}
        filename = '-'.join((
            # address without port
            url.netloc.split(':')[0],
            # path with _ instead of /
            url.path.lstrip('/').rstrip('/').replace('/', '_'),
            distribution
        ))

    # deb http://ppa.launchpad.net/mercurial-ppa/releases/ubuntu precise main
    # without the deb
    line_content = [address, distribution]
    line_content.extend(components)

    if in_sources_list_d:
        apt_file = '/etc/apt/sources.list.d/{0}.list'.format(filename)
    else:
        apt_file = '/etc/apt/sources.list'

    text = [' '.join(['deb'] + line_content)]
    if source:
        text.append(' '.join(['deb-src'] + line_content))

    data = {
        filename: {
            'file': [
                'append',
                {
                    'name': apt_file
                },
                {
                    'text': text
                },
                {
                    'makedirs': True
                }
            ]
        }
    }

    if key_id:
        add_command = ['apt-key', 'adv', '--recv-keys']
        if key_server:
            add_command.extend(['--keyserver', key_server])
        add_command.extend([key_id])
        data[filename]['cmd'] = [
            'run',
            {'name': ' '.join(add_command)},
            {'unless': 'apt-key list | grep -q {0}'.format(key_id)}
        ]

    output = __salt__['state.high'](data)
    file_result, cmd_result = output.values()

    ret = {
        'name': filename,
        'result': file_result['result'] == cmd_result['result'] is True,
        'changes': file_result['changes'],
        'comment': ' and '.join((file_result['comment'], cmd_result['comment']))
    }
    if ret['result'] and ret['changes']:
        __salt__['pkg.refresh_db']()
    ret['changes'].update(cmd_result['changes'])
    return ret


def ubuntu_ppa(user, name, key_id, source=False, distribution=None):
    '''
    Manage an Ubuntu PPA repository

    user
        Launchpad username

    name
        Repository name owned by this user

    key_id
        Launchpad PGP key ID

    source
        Add source "deb-src" statement? not the default.

    distribution:
        Set this to use a different Ubuntu distribution than the host that run
        this state.

    For this PPA: https://launchpad.net/~pitti/+archive/postgresql
    the state must be:

    .. code-block:: yaml

        postgresql:
          apt_repository.ubuntu_ppa:
            - user: pitti
            - name: postgresql
            - key_id: 8683D8A2
    '''
    address = 'http://ppa.launchpad.net/{0}/{1}/ubuntu'.format(user, name)
    filename = '{0}-{1}-{2}'.format(
        user, name,
        __salt__['grains.item']('lsb_codename')['lsb_codename']
    )
    return present(address, ('main',), distribution, source, key_id,
                   'keyserver.ubuntu.com', True, filename)

########NEW FILE########
__FILENAME__ = archive
# -*- coding: utf-8 -*-
# author: Bruno Clermont <patate@fastmail.cn>

'''
Archive states
===================

'''

import logging
import os

log = logging.getLogger(__name__)

def extracted(name, source, archive_format, tar_options=None, source_hash=None,
              if_missing=None):
    '''
    State that make sure an archive is extracted in a directory.
    The downloaded archive is erased if succesfully extracted.
    The archive is downloaded only if necessary.

    .. code-block:: yaml

    graylog2-server:
      archive:
        - extracted
        - name: /opt/
        - source: https://github.com/downloads/Graylog2/graylog2-server/graylog2-server-0.9.6p1.tar.gz
        - source_hash: md5=499ae16dcae71eeb7c3a30c75ea7a1a6
        - archive_format: tar
        - tar_options: z
        - if_missing: /opt/graylog2-server-0.9.6p1/

    name
        Directory name where to extract the archive

    source
        Archive source, same syntax as file.managed source argument.

    archive_format
        tar, zip or rar

    if_missing
        Some archive, such as tar, extract themself in a subfolder.
        This directive can be used to validate if the archive had been
        previously extracted.

    tar_options
        Only used for tar format, it need to be the tar argument specific to
        this archive, such as 'j' for bzip2, 'z' for gzip, '' for uncompressed
        tar, 'J' for LZMA.
    '''
    ret = {'name': name, 'result': None, 'changes': {}, 'comment': ''}
    valid_archives = ('tar', 'rar', 'zip')

    if __opts__['test']:
        ret['comment'] = 'Archive {0} would have been extracted in {1}'.format(
            source, name)
        return ret

    if archive_format not in valid_archives:
        ret['result'] = False
        ret['comment'] = '{0} is not supported, valids: {1}'.format(
            name, ','.join(valid_archives))
        return ret

    if archive_format == 'tar' and tar_options is None:
        ret['result'] = False
        ret['comment'] = 'tar archive need argument tar_options'
        return ret

    if if_missing is None:
        if_missing = name
    if __salt__['file.directory_exists'](if_missing):
        ret['result'] = True
        ret['comment'] = '{0} already exists'.format(if_missing)
        return ret

    log.debug("Input seem valid so far")
    filename = os.path.join(__opts__['cachedir'],
                            '{0}.{1}'.format(if_missing.replace('/', '_'),
                                             archive_format))
    if not os.path.exists(filename):
        log.debug("Archive file {0} is not in cache, download it", source)
        data = {
            filename: {
                'file': [
                    'managed',
                    {'name': filename},
                    {'source': source},
                    {'source_hash': source_hash},
                    {'makedirs': True}
                ]
            }
        }
        file_result = __salt__['state.high'](data)
        log.debug("file.managed: %s", file_result)
        # get value of first key
        file_result = file_result[file_result.keys()[0]]
        if not file_result['result']:
            log.debug("failed to download %s", source)
            return file_result
    else:
        log.debug("Archive file {0} is already in cache", name)

    __salt__['file.makedirs'](name)
    __salt__['file.mkdir'](name)

    if archive_format in ('zip', 'rar'):
        log.debug("Extract %s in %s", filename, name)
        files = __salt__['archive.un{0}'.format(archive_format)](filename, name)
    else:
        log.debug("Untar %s in %s", filename, name)
        files = __salt__['archive.tar'](options='xv{0}f'.format(tar_options),
                            tarfile=filename, dest=name)
    if len(files) > 0:
        ret['result'] = True
        ret['changes']['directories_created'] = [name]
        if if_missing != name:
            ret['changes']['directories_created'].append(if_missing)
        ret['changes']['extracted_files'] = files
        ret['comment'] = "{0} extracted in {1}".format(source, name)
        os.unlink(filename)
    else:
        __salt__['file.remove'](if_missing)
        ret['result'] = False
        ret['comment'] = "Can't extract content of {0}".format(source)
    return ret

########NEW FILE########
__FILENAME__ = bacula
'''
Management of bacula File Daemon Configuration
==============================================

Configure Bacula file daemon to allow connections from a 
particular Bacula director, set password credentials, as well as 
the file daemon name and port that it runs on. Configure the 
messages that get returned to the director.

.. code-block:: yaml

    /etc/bacula/bacula-fd.conf:
      bacula:
        - fdconfig
        - dirname: bacula-dir
        - dirpasswd: test1234
        - fdname: bacula-fd
        - fdport: 9102
        - messages: bacula-dir = all, !skipped, !restored
'''
    
import re    


# Search Patterns
dirs = re.compile(r'Director {[^}]*}')
fd = re.compile(r'FileDaemon {[^}]*}')
msgs = re.compile(r'Messages {[^}]*}')


def _getConfig(pattern, config):
    '''
    Get Configuration block
    '''
    m = pattern.search(config)
    if m:
        return m.group()
    return None


def _getParam(pname, config):
    '''
    Get Param from config
    '''
    if pname == 'Password':
        search = '{0} = "(?P<{0}>.*)"'.format(pname)
    else:
        search = '{0} = (?P<{0}>.*)'.format(pname)
    mp = re.search(search, config)
    if mp:
        return mp.group(pname)
    return None
    

def _getConfigParams(config):
    '''
    Get configuration blocks for parameters
    '''
    cparams = {}

    dconfig = _getConfig(dirs, config)
    if not dconfig:
        return None

    cparams['dirname'] = _getParam('Name', dconfig)
    cparams['dirpasswd'] = _getParam('Password', dconfig)

    fdconfig = _getConfig(fd, config)
    if not fdconfig:
        return None

    cparams['fdname'] = _getParam('Name', fdconfig)
    cparams['fdport'] = _getParam('FDport', fdconfig)

    mconfig = _getConfig(msgs, config)
    if not mconfig:
        return None

    cparams['messages'] = _getParam('director', mconfig)
    
    return cparams


def fdconfig(name,
             dirname=None,
             dirpasswd=None,
             fdname=None,
             fdport=None,
             messages=None):
    '''
    Configure a bacula file daemon

    dirname
        The name of the director that is allowed to connect to the
        file daemon.

    dirpasswd
        The password that the director must use to successfully 
        connect to the file daemon.

    fdname
        The name of the file daemon

    fdport
        The port that the file daemon should run on

    messages
        Define how and what messages to send to a director.
    '''
    ret = {'name':name,
           'changes':{},
           'result':None,
           'comment':'',}

    config = ''
    with open(name) as f:
        config = f.read()

    if not config:
        ret['comment'] = config #'Could not find {0}\n'.format(name)
        ret['result'] = False
        return ret
    
    cparams = _getConfigParams(config)
    if not cparams:
        ret['comment'] += 'Could not find configuration information.\n'
        ret['result'] = False
        return ret

    changes = {}

    if dirname and dirname != cparams['dirname']:
        changes['dirname'] = dirname
    if dirpasswd and dirpasswd != cparams['dirpasswd']:
        changes['dirpasswd'] = dirpasswd
    if fdname and fdname != cparams['fdname']:
        changes['fdname'] = fdname
    if fdport and fdport != int(cparams['fdport']):
        changes['fdport'] = fdport
    if messages and messages != cparams['messages']:
        changes['messages'] = messages
        
    if not changes:
        ret['comment'] += 'Bacula file daemon configuration is up to date.\n'
        ret['result'] = True
        return ret

    if __opts__['test']:
        if changes.has_key('dirname'):
            ret['comment'] += \
                'Director Name set to be changed to {0}\n'.format(dirname)
        if changes.has_key('dirpasswd'):
            ret['comment'] += \
                'Director Password set to be changed to {0}\n'.format(dirpasswd)
        if changes.has_key('fdname'):
            ret['comment'] += \
                'File Daemon Name set to be changed to {0}\n'.format(fdname)
        if changes.has_key('fdport'):
            ret['comment'] += \
                'File Daemon Port set to be changed to {0}\n'.format(fdport)
        if changes.has_key('messages'):
            ret['comment'] += \
                'Messages Director set to be changed to {0}\n'.format(messages)
        return ret

    if changes.has_key('dirname') or changes.has_key('dirpasswd'):
        dconfig = _getConfig(dirs, config)
        if changes.has_key('dirname'):
            dconfig = re.sub(r'Name = (.*)', 
                             'Name = {0}'.format(dirname),
                             dconfig)
        if changes.has_key('dirpasswd'):
            dconfig = re.sub(r'Password = "(.*)"',
                             'Password = "{0}"'.format(dirpasswd),
                             dconfig)
        config = dirs.sub(dconfig, config)
        ret['changes']['Director'] = dconfig

    if changes.has_key('fdname') or changes.has_key('fdport'):
        fdconfig = _getConfig(fd, config)
        if changes.has_key('fdname'):
            fdconfig = re.sub(r'Name = (.*)',
                              'Name = {0}'.format(fdname),
                              fdconfig)
        if changes.has_key('fdport'):
            fdconfig = re.sub(r'FDport = (.*)',
                              'FDport = {0}'.format(fdport),
                              fdconfig)
        config = fd.sub(fdconfig, config)
        ret['changes']['FileDaemon'] = fdconfig

    if changes.has_key('messages'):
        mconfig = _getConfig(msgs, config)
        mconfig = re.sub(r'director = (.*)',
                         'director = {0}'. format(messages),
                         mconfig)
        ret['changes']['Messages'] = mconfig
        config = msgs.sub(mconfig, config)

    with open(name, 'w') as f:
        f.write(config)

    ret['comment'] += 'Updated bacula file daemon settings.\n'
    ret['result'] = True
    return ret

########NEW FILE########
__FILENAME__ = keystone_role
'''
Management of Keystone roles.
=============================

NOTE: This module requires the proper pillar values set. See
salt.modules.keystone for more information.

The keystone_role module is used to manage Keystone roles.

.. code-block:: yaml

    admin:
      keystone_role:
        - present
'''

def __virtual__():
    '''
    Only load if the keystone module is in __salt__
    '''
    return 'keystone_role' if 'keystone.role_create' in __salt__ else False

def present(name):
    '''
    Ensure that the named role is present

    name
        The name of the role to manage
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': 'Role {0} is already presant'.format(name)
            }
    #Check if the tenant exists
    if not ('Error' in (__salt__['keystone.role_get'](name=name))):
        return ret

    #The tenant is not present, make it!
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Role {0} is set to be added'.format(name)
        return ret
    if __salt__['keystone.role_create'](name):
        ret['comment'] = 'The role {0} has been added'.format(name)
        ret['changes'][name] = 'Present'
    else:
        ret['comment'] = 'Failed to create role {0}'.format(name)
        ret['result'] = False

    return ret

def absent(name):
    '''
    Ensure that the named role is absent

    name
        The name of the role to remove
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': ''
            }

    #Check if tenant exists and remove it
    if not ('Error' in (__salt__['keystone.role_get'](name=name))):
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Role {0} is set to be removed'.format(name)
            return ret
        if __salt__['keystone.role_delete'](name=name):
            ret['comment'] = 'Role {0} has been removed'.format(name)
            ret['changes'][name] = 'Absent'
            return ret
    #fallback
    ret['comment'] = (
            'Role {0} is not present, so it cannot be removed'
            ).format(name)
    return ret

########NEW FILE########
__FILENAME__ = keystone_tenant
'''
Management of Keystone tenants.
===============================

NOTE: This module requires the proper pillar values set. See
salt.modules.keystone for more information.

The keystone_tenant module is used to manage Keystone tenants.

.. code-block:: yaml

    admin:
      keystone_tenant:
        - present
'''

def __virtual__():
    '''
    Only load if the keystone module is in __salt__
    '''
    return 'keystone_tenant' if 'keystone.tenant_create' in __salt__ else False

def present(name):
    '''
    Ensure that the named tenant is present

    name
        The name of the tenant to manage
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': 'Tenant {0} is already presant'.format(name)
            }
    #Check if the tenant exists
    if not ('Error' in (__salt__['keystone.tenant_get'](name=name))):
        return ret

    #The tenant is not present, make it!
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Tenant {0} is set to be added'.format(name)
        return ret
    if __salt__['keystone.tenant_create'](name):
        ret['comment'] = 'The tenant {0} has been added'.format(name)
        ret['changes'][name] = 'Present'
    else:
        ret['comment'] = 'Failed to create tenant {0}'.format(name)
        ret['result'] = False

    return ret

def absent(name):
    '''
    Ensure that the named tenant is absent

    name
        The name of the tenant to remove
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': ''
            }

    #Check if tenant exists and remove it
    if not ('Error' in (__salt__['keystone.tenant_get'](name=name))):
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Tenant {0} is set to be removed'.format(name)
            return ret
        if __salt__['keystone.tenant_delete'](name=name):
            ret['comment'] = 'Tenant {0} has been removed'.format(name)
            ret['changes'][name] = 'Absent'
            return ret
    #fallback
    ret['comment'] = (
            'Tenant {0} is not present, so it cannot be removed'
            ).format(name)
    return ret

########NEW FILE########
__FILENAME__ = keystone_user
'''
Management of Keystone users.
=============================

NOTE: This module requires the proper pillar values set. See
salt.modules.keystone for more information.

The keystone_user module is used to manage Keystone users.

.. code-block:: yaml

    admin:
      keystone_user:
        - present
'''

def __virtual__():
    '''
    Only load if the keystone module is in __salt__
    '''
    return 'keystone_user' if 'keystone.user_create' in __salt__ else False

def present(name, password, email, tenant, enabled):
    '''
    Ensure that the named user is present

    name
        The name of the user to manage
    password
        The password the user should have
    email
        The email of the user
    tenant
        The name of the tenant the user should be associated with
    enabled
        Whether or not the user is enabled
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': ('User {0} is already presant, ').format(name)
            }
    #Check if the user exists
    if ('Error' in (__salt__['keystone.user_get'](name=name))):
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'User {0} is set to be added.'.format(name)
        elif __salt__['keystone.user_create'](
                name, 
                password, 
                email, 
                tenant_id = __salt__['keystone.tenant_get'](
                        name=tenant)[tenant]['id'], 
                enabled=enabled):
            ret['comment'] = 'The user {0} has been added.'.format(name)
            ret['changes'][name] = 'Present'
        else:
            ret['comment'] = 'Failed to create user {0}'.format(name)
            ret['result'] = False
            return ret

    #Check the rest of the settings:
    if __salt__['keystone.user_get'](name=name)[name]['email'] != email:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] += (
                    ' User {0} is set to have email updated to {1}.'
                    ).format(name, email)
        elif __salt__['keystone.user_update'](
                id = __salt__['keystone.user_get'](
                        name=name)[name]['id'],
                name = name,
                email = email,
                enabled = enabled,
                ):
            ret['comment'] += (
                    ' User {0} has had its email updated to {1}.'
                    ).format(name, email)
            ret['changes'][email] = 'Present'
        else:
            ret['comment'] = (
                    'Failed to update user {0}\'s email to {1}.'
                    ).format(name, email)
            ret['result'] = False
            return ret

    if __salt__['keystone.user_get'](name=name)[name]['enabled'] != enabled:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] += (
                    ' User {0} is set to have status updated to {1}.'
                    ).format(name, enabled)
        elif __salt__['keystone.user_update'](
                id = __salt__['keystone.user_get'](name=name)[name]['id'],
                name = name, 
                email = email, 
                enabled = enabled,
                ):
            ret['comment'] += (
                    'The user {0} has had its status updated to {1}'
                    ).format(name, enabled)
            ret['changes'][enabled] = 'Present'
        else:
            ret['comment'] = (
                    'Failed to update user {0}\'s status to {1}'
                    ).format(name, enabled)
            ret['result'] = False
            return ret

    return ret

def absent(name):
    '''
    Ensure that the named user is absent

    name
        The name of the user to remove
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': ''
            }

    #Check if user exists and remove it
    if not ('Error' in (__salt__['keystone.user_get'](name=name))):
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'User {0} is set to be removed'.format(name)
            return ret
        if __salt__['keystone.user_delete'](name=name):
            ret['comment'] = 'User {0} has been removed'.format(name)
            ret['changes'][name] = 'Absent'
            return ret
    #fallback
    ret['comment'] = (
            'User {0} is not present, so it cannot be removed'
            ).format(name)
    return ret

########NEW FILE########
__FILENAME__ = keystone_user_role
'''
Management of Keystone user-roles.
=============================

NOTE: This module requires the proper pillar values set. See
salt.modules.keystone for more information.

The keystone_user-role module is used to manage Keystone user-roles.

.. code-block:: yaml

    admin:
      keystone_user_role:
        - present
'''

def __virtual__():
    '''
    Only load if the keystone module is in __salt__
    '''
    return 'keystone_user_role' if 'keystone.user_role_add' in __salt__ else False

def present(name, role, tenant):
    '''
    Ensure that the named user role is present

    name
        The name of the user to manage
    role
        The name of the role to apply to the user
    tenant
        The name of the tenant 
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': 'Role {0} is already presant on user {1}'.format(
                    role, 
                    name,
                    )
            }
    #Check if the user-role exists
    for role_item in __salt__['keystone.user_role_list'](
              user_name = name,
              tenant_name = tenant,
              ):
        if role_item == role:
            return ret

    #The tenant is not present, make it!
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = (
                  'User {0} is set to have the role {1} added on {2}'
                  ).format(name, role, tenant)
        return ret
    if __salt__['keystone.user_role_add'](
              user_name = name,
              role_name = role,
              tenant_name = tenant,
              ):
        ret['comment'] = 'User {0} now has role {1} on {2}'.format(
                  name, role, tenant)
        ret['changes'][name] = 'Present'
    else:
        ret['comment'] = 'Failed to create User {0} role {1} on {2}'.format(
                  name, role, tenant)
        ret['result'] = False

    return ret

def absent(name, role, tenant):
    '''
    Ensure that the named role is absent

    name
        The name of the user to modify roles on
    role
        The role to remove from the user
    tenant
        The tenant to remove the users role from
    '''
    ret = {
            'name': name,
            'changes': {},
            'result': True,
            'comment': ''
            }

    #Check if role exists and remove it
    for role_item in __salt__['keystone.user_role_list'](
              user_name = name,
              tenant_name = tenant
              ):
        if role_item == role:
            if __opts__['test']:
                ret['result'] = None
                ret['comment'] = (
                          'User {0} role {1} is set to be removed from {2}'
                          ).format(name, role, tenant)
                return ret
                
            else:
                __salt__['keystone.user_role_remove'](
                      user_name = name,
                      role_name = role,
                      tenant_name = tenant,
                      )
                ret['comment'] = (
                          'User {0} has had role {1} removed from {2}'
                          ).format(name, role, tenant)
                ret['changes'][name] = 'Absent'
                return ret
    #fallback
    ret['comment'] = (
            'User {0}\'s role {1} is not present on {2}, so it cannot be \
            removed').format(name, role, tenant)
    return ret

########NEW FILE########
__FILENAME__ = rabbitmq_plugins
# -*- coding: utf-8 -*-
# author: Bruno Clermont <patate@fastmail.cn>

'''
RabbitMQ plugins state
'''

from salt import exceptions, utils

def __virtual__():
    '''
    Verify RabbitMQ is installed.
    '''
    name = 'rabbitmq_plugins'
    try:
        utils.check_or_die('rabbitmq-plugins')
    except exceptions.CommandNotFoundError:
        name = False
    return name

def disabled(name, runas=None, env=None):
    '''
    Make sure that a plugin is not enabled.

    name
        The name of the plugin to disable
    '''
    if __opts__['test']:
        ret['comment'] = 'The plugin {0} would have been disabled'.format(name)
        return ret

    ret = {'name': name, 'result': None, 'comment': '', 'changes': {}}
    plugins = __salt__['rabbitmq_plugins.list'](env=env, runas=runas)
    if name not in plugins:
        ret['result'] = True
        ret['comment'] = 'Plugin is not available to disable.'
        return ret

    if plugins[name]['state'] == ' ':
        ret['result'] = True
        ret['comment'] = 'Plugin is already disabled.'
        return ret

    if __salt__['rabbitmq_plugins.disable'](name, env=env, runas=runas):
        ret['result'] = True
        ret['changes'][name] = 'Disabled'
        ret['comment'] = 'Plugin was successfully disabled.'
    else:
        ret['result'] = False
        ret['comment'] = 'Could not disable plugin.'
    return ret

def enabled(name, runas=None, env=None):
    '''
    Make sure that a plugin is enabled.

    name
        The name of the plugin to enable
    '''
    if __opts__['test']:
        ret['comment'] = 'The plugin {0} would have been enabled'.format(name)
        return ret

    ret = {'name': name, 'result': None, 'comment': '', 'changes': {}}
    plugins = __salt__['rabbitmq_plugins.list'](env=env, runas=runas)
    if name not in plugins:
        ret['result'] = True
        ret['comment'] = 'Plugin is not available to enable.'
        return ret

    if plugins[name]['state'] != ' ':
        ret['result'] = True
        ret['comment'] = 'Plugin is already enabled.'
        return ret

    if __salt__['rabbitmq_plugins.enable'](name, env=env, runas=runas):
        ret['result'] = True
        ret['changes'][name] = 'Enabled'
        ret['comment'] = 'Plugin was successfully enabled.'
    else:
        ret['result'] = False
        ret['comment'] = 'Could not enable plugin.'
    return ret

########NEW FILE########
__FILENAME__ = riak
'''
Support for riak$
'''

import salt.utils

def __virtual__():
    '''
    Only load the module if riak is installed
    '''
    cmd = 'riak'
    if salt.utils.which(cmd):
        return cmd
    return False


def running():
    '''
    Verify that riak is running
    '''
    ret = {'name': 'riak', 'result': None, 'comment': '', 'changes': {}}
    is_up = __salt__['riak.is_up']()
    if is_up == False:
        if __salt__['riak.start']():
            ret['result'] = True
            ret['changes']['riak'] = "Riak started"
            ret['comment'] = "Riak started successfully"
        else:
            ret['result'] = False
            ret['comment'] = "Riak failed to start"
    else:
        ret['result'] = True
    return ret


def mod_watch():
    '''
    The Riak watcher, called to invoke the watch command.
    '''
    changes = {'riak': __salt__['riak.restart']()}
    return {'name': 'riak',
            'changes': changes,
            'result': True,
            'comment': 'Service riak started'}

########NEW FILE########
__FILENAME__ = smx
'''
Salt State to manage Apache Service Mix

The following grains should be set
smx:
  user: admin user name
  pass: password
  path: /absolute/path/to/servicemix/home

or use pillar:
smx.user: admin user name
smx.pass: password
smx.path: /absolute/path/to/servicemix/home

Note:
- if both pillar & grains settings exists -> grains wins
- Tested on apache-servicemix-full-4.4.2.tar.gz
- When a feature is being removed it will not recursivly remove its nested features
  But it will remove the bundles configure in the feature it self
'''

def __virtual__():
    '''
    Load the state only if smx module is loaded
    '''
    
    return 'smx' if 'smx.run' in __salt__ else False

def _get_latest_feature_version(feature):
    '''
    get the latest version available for this feature
    '''
    
    feature_refreshurls()
    ret = ''
    for line in _parse_list(run('features:list')):
        lst = line.split()
        if feature == lst[2]:
             ret = max(ret,lst[1])
    
    return ret

def feature_repository_present(name):
    '''
    Verifies that the repository url is configured and updated
    '''
    
    ret = {'name': name,
           'result': True,
           'changes': {},
           'comment': ''}
    
    if __salt__['smx.is_repo'](name):
        ret['comment'] = 'The repository {0} is already configured'.format(name)
        return ret
    
    if __opts__['test']:
        ret['changes'] = {'added': name}
        return ret
    
    if __salt__['smx.feature_addurl'](name) == 'missing':
        ret['result'] = False
        ret['comment'] = 'fail to configure {0} as a feature repository'.format(name)
    else:
        ret['changes'] = {'added': name}
    
    return ret

def feature_installed_latest(name, bundles=''):
    '''
    Verifies that the feature is installed in its latest version
    a second optional arguments is a csv list of bundle names
    that should be in Active mode after the feature installation
    (in the format of osgi:list -s -u command)
    
    Note: it won't start the bundles if the feature is already installed
    '''
    
    version = _get_latest_feature_version(name)
    if version:
        return feature_installed(name, version, bundles)
    else:
        return {'name': name,
           'result': False,
           'changes': {},
           'comment': 'could not get latest version of the feature'}

def feature_installed(name, version, bundles=''):
    '''
    Verifies that the feature is installed
    a third optional arguments is a csv list of bundle names
    that should be in Active mode after the feature installation
    (in the format of osgi:list -s -u command)
    
    Note: it won't start the bundles if the feature is already installed
    '''
    
    ret = {'name': name,
           'result': True,
           'changes': {},
           'comment': ''}
    
    # validate
    if version  == '':
        ret['result'] = False
        ret['comment'] = 'must specify a version'
        return ret
    
    # prepare
    feature_fullname = '/'.join([name, version])
    if __salt__['smx.is_feature_installed'](name, version):
            ret['comment'] = 'the feature is installed already'
            return ret
    
    # Test
    if __opts__['test']:
        ret['changes']['installed'] = feature_fullname
        ret['comment'] = 'if the feature is installed in other version it will be removed'
        return ret
    
    # remove old versions if needed
    msg = __salt__['smx.feature_remove_all_versions'](name)
    if msg.startswith('error'):
        ret['comment'] = msg
        ret['result'] = False
        return ret
    elif msg.startswith('removed'):
        ret['changes']['removed'] = msg
    
    # Install it
    instRes = __salt__['smx.feature_install'](name, version, bundles)
    if instRes == 'installed':
        ret['changes']['installed'] = feature_fullname
        if bundles != '':
            ret['comment'] += ', bundles are Active'
    elif instRes == 'failed':
        ret['result'] = False
        ret['comment'] += ', could not install feature'
    else:
        ret['result'] = False
        ret['comment'] += ', the following bundles are not Active {0}'.format(__salt__['smx.nonactive_bundles'](bundles))
    
    return ret

########NEW FILE########
__FILENAME__ = win_update
# -*- coding: utf-8 -*-
'''
Management of the windows update agent.
=======================================

.. versionadded: (Helium)

Set windows updates to run by category. Default behavior is to install
all updates that do not require user interaction to complete. 

Optionally set ``category`` to a category of your choosing to only
install certain updates. default is all available updates.

In the example below, will install all Security and Critical Updates,
and download but not install standard updates.

Example::
        updates:
                win_update.install:
                        - categories: 
                                - 'Critical Updates'
                                - 'Security Updates'
                win_update.downloaded:
                        - categories:
                                - 'Updates'

You can also specify a number of features about the update to have a 
fine grain approach to specific types of updates. These are the following
features/states of updates available for configuring:
        'UI' - User interaction required, skipped by default
        'downloaded' - Already downloaded, skipped by default (downloading)
        'present' - Present on computer, included by default (installing)
        'installed' - Already installed, skipped by default
        'reboot' - Reboot required, included by default
        'hidden' - skip those updates that have been hidden.
        
        'software' - Software updates, included by default
        'driver' - driver updates, skipped by defautl

This example installs all driver updates that don't require a reboot:
Example::
        gryffindor:
                win_update.install:
                        - includes:
                                - driver: True
                                - software: False
                                - reboot: False


tl;dr: want to just have your computers update? add this your sls:
updates:
        win_update.install
        

'''

# Import Python libs
import tempfile
import subprocess
import logging
try:
        import win32com.client
        import win32api
        import win32con
        import pywintypes
        import threading
        import pythoncom
        HAS_DEPENDENCIES = True
except ImportError:
        HAS_DEPENDENCIES = False

import salt.utils

log = logging.getLogger(__name__)

__virtualname__ = 'win_update'

def __virtual__():
        '''
        Only works on Windows systems
        '''
        if salt.utils.is_windows() and HAS_DEPENDENCIES:
                return __virtualname__
        return False

def _gather_update_categories(updateCollection):
        categories = []
        for i in range(updateCollection.Count):
                update = updateCollection.Item(i)
                for j in range(update.Categories.Count):
                        name = update.Categories.Item(j).Name
                        if name not in categories:
                                log.debug('found category: {0}'.format(name))
                                categories.append(name)
        return categories

# some known categories:
#       Updates
#       Windows 7
#       Critical Updates
#       Security Updates
#       Update Rollups

class PyWinUpdater:
        def __init__(self,categories=None,skipUI = True,skipDownloaded = True,
                        skipInstalled=True, skipReboot=False,skipPresent=True,
                        softwareUpdates=True, driverUpdates=False,skipHidden=True):
                log.debug('CoInitializing the pycom system')
                pythoncom.CoInitialize()
                
                self.skipUI = skipUI
                self.skipDownloaded = skipDownloaded
                self.skipInstalled = skipInstalled
                self.skipReboot = skipReboot
                self.skipPresent = skipPresent
                self.skipHidden = skipHidden
                
                self.softwareUpdates = softwareUpdates
                self.driverUpdates = driverUpdates
                self.categories = categories
                self.foundCategories = None
                
                
                log.debug('dispatching keeper to keep the session object.')
                self.keeper = win32com.client.Dispatch('Microsoft.Update.Session')
                
                log.debug('keeper got. Now creating a seeker to seek out the updates')
                self.seeker = self.keeper.CreateUpdateSearcher()
                
                #list of updates that are applicable by current settings.
                self.quaffle = win32com.client.Dispatch('Microsoft.Update.UpdateColl')
                
                #list of updates to be installed.
                self.bludger = win32com.client.Dispatch('Microsoft.Update.UpdateColl')
                
                #the object responsible for fetching the actual downloads. 
                self.chaser = self.keeper.CreateUpdateDownloader()
                self.chaser.Updates = self.quaffle
                
                #the object responsible for the installing of the updates.
                self.beater = self.keeper.CreateUpdateInstaller()
                self.beater.Updates = self.bludger
                
                #the results of the download process
                self.points = None
                
                #the results of the installation process
                self.fouls = None

        def Search(self,searchString):
                try:
                        log.debug('beginning search of the passed string: {0}'.format(searchString))
                        self.golden_snitch = self.seeker.Search(searchString)
                        log.debug('search completed successfully.')
                except Exception as e:
                        log.info('search for updates failed. {0}'.format(str(e)))
                        return e
                
                log.debug('parsing results. {0} updates were found.'.format(
                    str(self.golden_snitch.Updates.Count)))
                try:
                        for update in self.golden_snitch.Updates:
                                if update.InstallationBehavior.CanRequestUserInput == True:
                                        log.debug('Skipped update {0}'.format(str(update)))
                                        continue
                                for category in update.Categories:
                                        if self.skipDownloaded and update.IsDownloaded:
                                                continue
                                        if self.categories == None or category.Name in self.categories:
                                                self.quaffle.Add(update)
                                                log.debug('added update {0}'.format(str(update)))
                        self.foundCategories = _gather_update_categories(self.quaffle)
                        return True
                except Exception as e:
                        log.info('parsing updates failed. {0}'.format(str(e)))
                        return e
                        
        def AutoSearch(self):
                search_string = ''
                searchParams = []
                if self.skipInstalled: searchParams.append('IsInstalled=0')
                else: searchParams.append('IsInstalled=1')
                if self.skipHidden: searchParams.append('IsHidden=0')
                else: searchParams.append('IsHidden=1')
                if self.skipReboot: searchParams.append('RebootRequired=1')
                else: searchParams.append('RebootRequired=0')
                if self.skipPresent: searchParams.append('IsPresent=0')
                else: searchParams.append('IsPresent=1')
                if len(searchParams) > 1:
                        for i in searchParams:
                                search_string += '{0} and '.format(i)
                else:
                        search_string += '{0} and '.format(searchParams[1])
                
                if self.softwareUpdates and self.driverUpdates:
                        search_string += 'Type=\'Software\' or Type=\'Driver\''
                elif self.softwareUpdates:
                        search_string += 'Type=\'Software\''
                elif self.driverUpdates:
                        search_string += 'Type=\'Driver\''
                else:
                        return False ##if there is no type, the is nothing to search.
                log.debug('generated search string: {0}'.format(search_string))
                return self.Search(search_string)

        def Download(self):
                try:
                        if self.quaffle.Count != 0:
                                self.points = self.chaser.Download()
                        else:
                                log.debug('Skipped downloading, all updates were already cached.')
                        return True
                except Exception as e:
                        log.debug('failed in the downloading {0}.'.format(str(e)))
                        return e
                
        def Install(self):
                try:
                        for update in self.golden_snitch.Updates:
                                if update.IsDownloaded:
                                        self.bludger.Add(update)
                        log.debug('Updates prepared. beginning installation')
                except Exception as e:
                        log.info('Preparing install list failed: {0}'.format(str(e)))
                        return e
                
                if self.bludger.Count != 0:
                        log.debug('Install list created, about to install')
                        updates = []
                        try:
                                self.fouls = self.beater.Install()
                                log.info('Installation of updates complete')
                                return True
                        except Exception as e:
                                log.info('Installation failed: {0}'.format(str(e)))
                                return e
                else:
                        log.info('no new updates.')
                        return True
        
        def GetInstallationResults(self):
                log.debug('bluger has {0} updates in it'.format(str(self.bludger.Count)))
                if self.bludger.Count == 0:
                        return {}
                for i in range(self.bludger.Count):
                        updates.append('{0}: {1}'.format(
                                str(self.fouls.GetUpdateResult(i).ResultCode),
                                str(self.bludger.Item(i).Title)))
                
                log.debug('Update results enumerated, now making a list to pass back')
                results = {}
                for i,update in enumerate(updates):
                        results['update {0}'.format(i)] = update
                
                log.debug('Update information complied. returning')
                return results

        def GetDownloadResults(self):
                for i in range(self.quaffle.Count):
                        updates.append('{0}: {1}'.format(
                                str(self.points.GetUpdateResult(i).ResultCode),
                                str(self.quaffle.Item(i).Title)))
                results = {}
                for i,update in enumerate(updates):
                        results['update {0}'.format(i)] = update
                return results

        def SetCategories(self,categories):
                self.categories = categories

        def GetCategories(self):
                return self.categories

        def GetAvailableCategories(self):
                return self.foundCategories

        def SetIncludes(self,includes):
                if includes:
                        for i in includes:
                                value = i[i.keys()[0]]
                                include = i.keys()[0]
                                self.SetInclude(include,value)
                                log.debug('was asked to set {0} to {1}'.format(include,value))

        def SetInclude(self,include,state):
                if include == 'UI': self.skipUI = state
                elif include == 'downloaded': self.skipDownloaded = state
                elif include == 'installed': self.skipInstalled = state
                elif include == 'reboot': self.skipReboot = state
                elif include == 'present': self.skipPresent = state
                elif include == 'software':self.softwareUpdates = state
                elif include == 'driver':self.driverUpdates = state
                log.debug('new search state: \n\tUI: {0}\n\tDownload: {1}\n\tInstalled: {2}\n\treboot :{3}\n\tPresent: {4}\n\tsoftware: {5}\n\tdriver: {6}'.format(
                        self.skipUI,self.skipDownloaded,self.skipInstalled,self.skipReboot,
                        self.skipPresent,self.softwareUpdates,self.driverUpdates))

def _search(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while passed != True:
                log.debug('Searching. tries left: {0}'.format(str(retries)))
                passed = quidditch.AutoSearch()
                log.debug('Done searching: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed in the seeking/parsing process:\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,True,retries)
                        passed = False
        if clean:
                comment += 'Search was done with out an error.\n'
        return (comment,True,retries)

def _download(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while not passed:
                log.debug('Downloading. tries left: {0}'.format(str(retries)))
                passed = quidditch.Download()
                log.debug('Done downloading: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed while trying to download updates:\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,False,retries)
        if clean:
                comment += 'Download was done without error.\n'
        return (comment,True,retries)
        
def _install(quidditch,retries=5):
        passed = False
        clean = True
        comment = ''
        while not passed:
                log.debug('quaffle is this long: {0}'.format(str(quidditch.bludger.Count)))
                log.debug('Installing. tries left: {0}'.format(str(retries)))
                passed = quidditch.Install()
                log.info('Done installing: {0}'.format(str(passed)))
                if isinstance(passed,Exception):
                        clean = False
                        comment += 'Failed while trying to install the updates.\n\t\t{0}\n'.format(str(passed))
                        retries -= 1
                        if retries:
                                comment += '{0} tries to go. retrying\n'.format(str(retries))
                                passed = False
                        else:
                                comment += 'out of retries. this update round failed.\n'
                                return (comment,False,retries)
        if clean:
                comment += 'Install was done without error.\n'
        return (comment,True,retries)


def install(name,categories=None,includes=None,retries=10):
        '''
        Install specified windows updates.
        '''
        ret = {'name': name,
               'result': True,
               'changes': {},
               'comment': ''}
        log.debug('categories to search for are: '.format(str(categories)))
        quidditch = PyWinUpdater()
        quidditch.SetCategories(categories)
        quidditch.SetIncludes(includes)
        
        
        ##this is where we be seeking the things! yar!
        comment, passed, retries = _search(quidditch,retries)
        ret['comment'] += comment
        if not passed:
                ret['result'] = False
                return ret
        
        ##this is where we get all the things! i.e. download updates.
        comment, passed, retries = _download(quidditch,retries)
        ret['comment'] += comment
        if not passed:
                ret['result'] = False
                return ret

        ##this is where we put things in their place!
        comment, passed, retries = _install(quidditch,retries)
        ret['comment'] += comment
        if not passed:
                ret['result'] = False
                return ret

        try:
                ret['changes'] = quidditch.GetInstallationResults()
        except Exception as e:
                ret['comment'] += 'could not get results, but updates were installed.'
        return ret

def download(name,categories=None,includes=None,retries=10):
        '''
        Cache updates for later install. 
        '''
        ret = {'name': name,
               'result': True,
               'changes': {},
               'comment': ''}
        log.debug('categories to search for are: '.format(str(categories)))
        quidditch = PyWinUpdater()
        quidditch.SetCategories(categories)
        quidditch.SetIncludes(includes)
        
        ##this is where we be seeking the things! yar!
        comment, passed, retries = _search(quidditch,retries)
        ret['comment'] += comment
        if not passed:
                ret['result'] = False
                return ret
        
        ##this is where we get all the things! i.e. download updates.
        comment, passed, retries = _download(quidditch,retries)
        ret['comment'] += comment
        if not passed:
                ret['result'] = False
                return ret
        
        try:
                ret['changes'] = quidditch.GetDownloadResults()
        except Exception as e:
                ret['comment'] += 'could not get results, but updates were downloaded.'
                
        return ret

#To the King#

########NEW FILE########
__FILENAME__ = contrib
from salttesting import TestSuite, TestLoader
import os

tests = TestSuite()
loader = TestLoader()

# add some useful tests from the main suite
extra = ('integration.modules.sysmod', )
tests.addTest(loader.loadTestsFromNames(extra))

# this should resolve to the salt-contrib directory
# need to check if we are compiled or not!
current_file = __file__
if current_file[-4:] == '.pyc':
    current_file = current_file[:-1]

current_dir = os.path.dirname(os.path.realpath(current_file))

l = len(current_dir)

names = []
for dirname, dirs, files in os.walk(current_dir):
    parts = dirname[l:].split(os.sep)
    if len(parts) < 2:
        continue

    module = '.'.join(parts[1:])
    for f in files:
        if f[-3:] == '.py' and f != '__init__.py':
            names.append('{0}.{1}'.format(module, f[:-3]))

tests.addTest(loader.loadTestsFromNames(names))

########NEW FILE########
