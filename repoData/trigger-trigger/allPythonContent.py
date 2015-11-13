__FILENAME__ = autoacl
#!/usr/bin/env python
# -*- coding: utf-8 -*- 

"""
autoacl.py - This file controls when ACLs get auto-applied to network devices,
in addition to what is explicitly specified in :class:`~trigger.acl.db.AclsDB`.

After editing this file, run ``python autoacl.py`` to make sure the
syntax is ok.  Several things will break if you break this file.

You can also run this with '-v' to output the list of all devices
and what ACLs will be applied to them.  You can save this output
before editing and compare it to the output after your change.

Skip down a bit to find the part you should edit.
"""

import os
import sys

from twisted.python import log
from trigger.conf import settings
from trigger.acl import acl_exists


# Exports
__all__ = ('autoacl',)

#===============================
# BEGIN USER-SERVICEABLE PARTS
#===============================

log.msg('IN CUSTOM AUTOACL.PY FILE:', __file__)
OWNERS = settings.VALID_OWNERS

def autoacl(dev, explicit_acls=None):
    """
    Given a NetDevice object, returns a set of **implicit** (auto) ACLs. We require
    a device object so that we don't have circular dependencies between netdevices
    and autoacl.
    
    This function MUST return a set() of acl names or you will break the ACL
    associations. An empty set is fine, but it must be a set!

    :param dev: A :class:`~trigger.netdevices.NetDevice` object.
    :param explicit_acls: A set containing names of ACLs. Default: set()

    >>> dev = nd.find('test1-abc')
    >>> dev.vendor
    <Vendor: Juniper>
    >>> autoacl(dev)
    set(['juniper-router-protect', 'juniper-router.policer'])
    """
    # Explicitly pass a set of explicit_acls so that we can use it as a
    # dependency for assigning implicit_acls. Defaults to an empty set.
    if explicit_acls is None:
        log.msg('[%s]: explicit_acls unset' % dev)
        explicit_acls = set()

    # Skip anything not owned by valid groups
    if dev.owningTeam not in OWNERS:
        log.msg('[%s]: invalid owningTeam' % dev)
        return set()

    # Skip firewall devices
    if dev.deviceType == 'FIREWALL':
        log.msg('[%s]: firewall device' % dev)
        return set()

    # Prep acl set
    log.msg('[%s]: autoacls initialized' % dev)
    acls = set()

    # 
    # ACL Magic starts here
    # 
    if dev.vendor in ('brocade', 'cisco', 'foundry'):
        log.msg("[%s]: adding ACLs ('118', '119')")
        acls.add('118')
        acls.add('119')

    #
    # Other GSR acls
    #
    if dev.vendor == 'cisco':
        log.msg("[%s]: adding ACLs ('117')" % dev)
        acls.add('117')
        if dev.make == '12000 SERIES' and dev.nodeName.startswith('pop') or dev.nodeName.startswith('bb'):
            log.msg("[%s]: adding ACLs ('backbone-acl')" % dev)
            acls.add('backbone-acl')
        elif dev.make == '12000 SERIES':
            log.msg("[%s]: adding ACLs ('gsr-acl')" % dev)
            acls.add('gsr-acl')
    #
    # Juniper acls
    #
    if dev.vendor == 'juniper':
        if dev.deviceType == 'SWITCH':
            log.msg("[%s]: adding ACLs ('juniper-switch-protect')" % dev)
            acls.add('juniper-switch-protect')
        else:
            log.msg("[%s]: adding ACLs ('juniper-router-protect')" % dev)
            acls.add('juniper-router-protect')
            acls.add('juniper-router.policer')

    #
    # Explicit ACL example
    #
    # Only add acl '10' (or variants) to the device if 'acb123.special' is not
    # explicitly associated with the device.
    if '10.special' in explicit_acls:
        pass
    elif dev.deviceType == 'ROUTER':
        log.msg("[%s]: adding ACLs ('10')" % dev)
        acls.add('10')
    elif dev.deviceType == 'SWITCH':
        log.msg("[%s]: adding ACLs ('10.sw')" % dev)
        acls.add('10.sw')

    return acls

#===============================
# END USER-SERVICEABLE PARTS
#===============================

def main():
    """A simple syntax check and dump of all we see and know!"""
    print 'Syntax ok.'
    if len(sys.argv) > 1:
        from trigger.netdevices import NetDevices
        nd = NetDevices()
        names = sorted(nd)
        for name in names:
            dev = nd[name]
            if dev.deviceType not in ('ROUTER', 'SWITCH'):
                continue
            acls = sorted(dev.acls)
            print '%-39s %s' % (name, ' '.join(acls))

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = bounce
# -*- coding: utf-8 -*-

"""
This file controls when bounce windows get auto-applied to network devices.

This module is expected to provide a ``bounce()`` function that takes a
`~trigger.netdevice.NetDevice` as the mandatory first argument and returns a
`~trigger.changemgmt.BounceWindow` object. The ``bounce()`` function is
imported by `~trigger.changemgmt` and `~trigger.netdevices`.

This file should be placed in the location specified in Trigger's
``settings.py`` using the :setting:`BOUNCE_FILE`` setting, which defaults to
``/etc/trigger/bounce.py``.

How you decide to return the bounce window object is up to you, and therein
lies the fun! This is meant to be an example of how one might customize bounce
windows and map them to devices in their environment.
"""

from trigger.changemgmt import BounceWindow as BW

# Bounce windows for Backbone (all times US/Eastern)
BACKBONE = {
    'ABC': BW(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    'BBQ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
    'COW': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'FAP': BW(green='21-23', yellow='0-12, 19-20', red='13-18'),
    'FUN': BW(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    'OMG': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'XYZ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
}

# Bounce windows for Data Center (all times US/Eastern)
DATACENTER = {
    'ABC': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'BBQ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'FUN': BW(green='21-23', yellow='0-12, 17-20', red='13-16'),
    'OMG': BW(green='15-18', yellow='0-4, 19-23', red='5-14'),
    'XYZ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
}

# Out-of-band network (all times US/Eastern)
OOB = {
    'ABC': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'BBQ': BW(green='14-17', yellow='18-20', red='1-13, 21-23'),
    'OMG': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'XYZ': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
}

# Team definitions
TEAM_DC = 'Data Center'
TEAM_BB = 'Backbone'

# Mapping of team name to bounce windows
BOUNCE_MAP = {
    TEAM_DC: DATACENTER,
    TEAM_BB: BACKBONE,
}

# Defaults
DEFAULT_BOUNCE_SITE = 'ABC'
DEFAULT_BOUNCE_TEAM = TEAM_DC
DEFAULT_BOUNCE = BOUNCE_MAP[DEFAULT_BOUNCE_TEAM][DEFAULT_BOUNCE_SITE]

def bounce(device, default=DEFAULT_BOUNCE):
    """
    Return the bounce window for a given device.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param default:
        A `~trigger.changemgmt.BounceWindow` object.
    """

    # First try OOB, since it's special
    if 'ilo' in device.nodeName or 'oob' in device.nodeName:
        windows = OOB
    # Try to get the bounce windows by owningTeam
    else:
        windows = BOUNCE_MAP.get(device.owningTeam)

    # If we got nothin', return default
    if windows is None:
        return default

    # Try to get the bounce window by site, or fallback to default
    mybounce = windows.get(device.site, default)

    return mybounce

########NEW FILE########
__FILENAME__ = trigger_settings
# -*- coding: utf-8 -*-

# This is a sample settings.py that varies slightly from the default. Please see docs/configuration.rst or
# trigger/conf/global_settings.py for the complete list of default settings.

import IPy
import os
import socket

#===============================
# Global Settings
#===============================

# This is where Trigger should look for its files.
PREFIX = '/etc/trigger'

# Set to True to enable GPG Authentication
# Set to False to use the old .tackf encryption method.
# Should be False unless instructions/integration is ready for GPG
USE_GPG_AUTH = False

# This is used for old auth method. It sucks and needs to die.
# TODO (jathan): This is deprecated. Remove all references to this and make GPG
# the default and only method.
USER_HOME = os.getenv('HOME')
TACACSRC = os.getenv('TACACSRC', os.path.join(USER_HOME, '.tacacsrc'))
TACACSRC_KEYFILE = os.getenv('TACACSRC_KEYFILE', os.path.join(PREFIX, '.tackf'))
TACACSRC_PASSPHRASE = 'bacon is awesome, son.' # NYI

# Default login realm to store user credentials (username, password) for
# general use within the .tacacsrc
DEFAULT_REALM = 'aol'

# Location of firewall policies
FIREWALL_DIR = '/data/firewalls'

# Location of tftproot.
TFTPROOT_DIR = '/data/tftproot'

# Add internally owned networks here. All network blocks owned/operated and
# considered part of your network should be included.
INTERNAL_NETWORKS = [
    IPy.IP("10.0.0.0/8"),
    IPy.IP("172.16.0.0/12"),
    IPy.IP("192.168.0.0/16"),
]

# The tuple of supported vendors derived from the values of VENDOR_MAP
SUPPORTED_VENDORS = (
    'a10',
    'arista',
    'aruba',
    'brocade',
    'cisco',
    'citrix',
    'dell',
    'f5',
    'force10',
    'foundry',
    'juniper',
    'mrv',
    'netscreen',
    'paloalto',
)
VALID_VENDORS = SUPPORTED_VENDORS # For backwards compatibility

# A mapping of manufacturer attribute values to canonical vendor name used by
# Trigger. These single-word, lowercased canonical names are used throughout
# Trigger.
#
# If your internal definition differs from the UPPERCASED ones specified below
# (which they probably do), customize them here.
VENDOR_MAP = {
    'A10 NETWORKS': 'a10',
    'ARISTA NETWORKS': 'arista',
    'ARUBA NETWORKS': 'aruba',
    'BROCADE': 'brocade',
    'CISCO SYSTEMS': 'cisco',
    'CITRIX': 'citrix',
    'DELL': 'dell',
    'F5 NETWORKS': 'f5',
    'FORCE10': 'force10',
    'FOUNDRY': 'foundry',
    'JUNIPER': 'juniper',
    'MRV': 'mrv',
    'NETSCREEN TECHNOLOGIES': 'netscreen',
    'PALO ALTO NETWORKS': 'paloalto',
}

# A dictionary keyed by manufacturer name containing a list of the device types
# for each that is officially supported by Trigger.
SUPPORTED_PLATFORMS = {
    'a10': ['SWITCH'],
    'arista': ['SWITCH'],                         # Your "Cloud" network vendor
    'aruba': ['SWITCH'],                          # Wireless Controllers
    'brocade': ['ROUTER', 'SWITCH'],
    'cisco': ['ROUTER', 'SWITCH'],
    'citrix': ['SWITCH'],                         # Assumed to be NetScalers
    'dell': ['SWITCH'],
    'f5': ['LOAD BALANCING', 'SWITCH'],
    'force10': ['ROUTER', 'SWITCH'],
    'foundry': ['ROUTER', 'SWITCH'],
    'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],  # Any devices running Junos
    'mrv': ['CONSOLE SERVER', 'SWITCH'],
    'netscreen': ['FIREWALL'],                    # Pre-Juniper NetScreens
    'paloalto': ['FIREWALL'],
}

# The tuple of support device types
SUPPORTED_TYPES = ('CONSOLE SERVER', 'FIREWALL', 'DWDM', 'LOAD BALANCING',
                   'ROUTER', 'SWITCH')

# A mapping of of vendor names to the default device type for each in the
# event that a device object is created and the deviceType attribute isn't set
# for some reason.
DEFAULT_TYPES = {
    'a10': 'SWITCH',
    'arista': 'SWITCH',
    'aruba': 'SWITCH',
    'brocade': 'SWITCH',
    'citrix': 'SWITCH',
    'cisco': 'ROUTER',
    'dell': 'SWITCH',
    'f5': 'LOAD BALANCING',
    'force10': 'ROUTER',
    'foundry': 'SWITCH',
    'juniper': 'ROUTER',
    'mrv': 'CONSOLE SERVER',
    'netscreen': 'FIREWALL',
    'paloalto': 'FIREWALL',
}

# When a vendor is not explicitly defined within `DEFAULT_TYPES`, fallback to
# this type.
FALLBACK_TYPE = 'ROUTER'

#===============================
# Twister
#===============================

# Default timeout in seconds for commands executed during a session.  If a
# response is not received within this window, the connection is terminated.
DEFAULT_TIMEOUT = 5 * 60

# Default timeout in seconds for initial telnet connections.
TELNET_TIMEOUT  = 60

# Whether or not to allow telnet fallback
TELNET_ENABLED = True

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable interactive (pty) SSH sessions, such as when using
# bin/gong.
SSH_PTY_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable asynchronous (NON-interactive) SSH sessions, such as
# when using twister or Commando to remotely control a device.
SSH_ASYNC_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
    'foundry': ['SWITCH'], # Old Foundry switches only do SSHv1
}

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'a10',
    'arista',
    'aruba',
    'brocade',
    'cisco',
    'dell',
    'force10',
    'foundry',
)

# The file path where .gorc is expected to be found.
GORC_FILE = '~/.gorc'

# The only root commands that are allowed to be executed when defined within
# ``~.gorc``. They will be filtered # out by `~trigger.gorc.filter_commands()`.
GORC_ALLOWED_COMMANDS = (
    'cli',
    'enable',
    'exit',
    'get',
    'monitor',
    'ping',
    'quit',
    'set',
    'show',
    'start',
    'term',
    'terminal',
    'traceroute',
    'who',
    'whoami'
)

#===============================
# NetDevices
#===============================

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# A tuple of data loader classes, specified as strings. Optionally, a tuple can
# be used instead of a string. The first item in the tuple should be the
# Loader's module, subsequent items are passed to the Loader during
# initialization.
NETDEVICES_LOADERS = (
    'trigger.netdevices.loaders.filesystem.XMLLoader',
    'trigger.netdevices.loaders.filesystem.JSONLoader',
    'trigger.netdevices.loaders.filesystem.SQLiteLoader',
    'trigger.netdevices.loaders.filesystem.CSVLoader',
    'trigger.netdevices.loaders.filesystem.RancidLoader',
    # Example of a database loader where the db information is sent along as an
    # argument. The args can be anything you want.
    #['trigger.netdevices.loaders.mysql.Loader', {'dbuser': 'root', 'dbpass': 'abc123', 'dbhost': 'localhost', 'dbport': 3306}, 'bacon'],
)

# A path or URL to netdevices device metadata source data, which is used to
# populate trigger.netdevices.NetDevices. For more information on this, see
# NETDEVICES_LOADERS.
NETDEVICES_SOURCE = os.environ.get('NETDEVICES_SOURCE', os.path.join(PREFIX, 'netdevices.xml'))

# Assign NETDEVICES_SOURCE to NETDEVICES_FILE for backwards compatibility
NETDEVICES_FILE = NETDEVICES_SOURCE

# Whether to treat the RANCID root as a normal instance, or as the root to
# multiple instances. This is only checked when using RANCID as a data source.
RANCID_RECURSE_SUBDIRS = os.environ.get('RANCID_RECURSE_SUBDIRS', False)

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and should be
# changed to match your environment.
VALID_OWNERS = (
    'Data Center',
    'Backbone Engineering',
    'Enterprise Networking',
)

# Fields and values defined here will dictate which Juniper devices receive a
# ``commit-configuration full`` when populating ``NetDevice.commit_commands`.
# The fields and values must match the objects exactly or it will fallback to
# ``commit-configuration``.
JUNIPER_FULL_COMMIT_FIELDS = {
    'deviceType': 'SWITCH',
    'make': 'EX4200',
}

#===============================
# Prompt Patterns
#===============================
# Specially-defined, per-vendor prompt patterns. If a vendor isn't defined here,
# try to use IOSLIKE_PROMPT_PAT or fallback to DEFAULT_PROMPT_PAT.
PROMPT_PATTERNS = {
    'aruba': r'\(\S+\)(?: \(\S+\))?\s?#$', # ArubaOS 6.1
    #'aruba': r'\S+(?: \(\S+\))?\s?#\s$', # ArubaOS 6.2
    'citrix': r'\sDone\n$',
    'f5': r'.*\(tmos\).*?#\s{1,2}\r?$',
    'juniper': r'\S+\@\S+(?:\>|#)\s$',
    'mrv': r'\r\n?.*(?:\:\d{1})?\s\>\>?$',
    'netscreen': r'(\w+?:|)[\w().-]*\(?([\w.-])?\)?\s*->\s*$',
    'paloalto': r'\r\n\S+(?:\>|#)\s?$',
}

# When a pattern is not explicitly defined for a vendor, this is what we'll try
# next (since most vendors are in fact IOS-like)
IOSLIKE_PROMPT_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?#\s?$'
IOSLIKE_ENABLE_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?>\s?$'

# Generic prompt to match most vendors. It assumes that you'll be greeted with
# a "#" prompt.
DEFAULT_PROMPT_PAT = r'\S+#\s?$'

#===============================
# Bounce Windows/Change Mgmt
#===============================

# Path of the explicit module file for bounce.py containing custom bounce
# window mappings.
BOUNCE_FILE = os.environ.get('BOUNCE_FILE', os.path.join(PREFIX, 'bounce.py'))

# Default bounce timezone. All BounceWindow objects are configured using
# US/Eastern for now.
BOUNCE_DEFAULT_TZ = 'US/Eastern'

# The default fallback window color for bounce windows. Must be one of
# ('green', 'yellow', or 'red').
#
#     green: Low risk
#    yellow: Medium risk
#       red: High risk
BOUNCE_DEFAULT_COLOR = 'red'

#===============================
# Redis Settings
#===============================

# Redis master server. This will be used unless it is unreachable.
REDIS_HOST = '127.0.0.1'

# The Redis port. Default is 6379.
REDIS_PORT = 6379

# The Redis DB. Default is 0.
REDIS_DB = 0

#===============================
# Database Settings
#===============================

# These are self-explanatory, I hope. Use the ``init_task_db`` to initialize
# your database after you've created it! :)
DATABASE_ENGINE = 'mysql'   # Choose 'postgresql', 'mysql', 'sqlite3'
DATABASE_NAME = ''          # Or path to database file if using sqlite3
DATABASE_USER = ''          # Not used with sqlite3
DATABASE_PASSWORD = ''      # Not used with sqlite3
DATABASE_HOST = ''          # Set to '' for localhost. Not used with sqlite3
DATABASE_PORT = ''          # Set to '' for default. Not used with sqlite3.

#===============================
# ACL Management
#===============================
# Whether to allow multi-line comments to be used in Juniper firewall filters.
# Defaults to False.
ALLOW_JUNIPER_MULTILINE_COMMENTS = False

# FILTER names of ACLs that should be skipped or ignored by tools
# NOTE: These should be the names of the filters as they appear on devices. We
# want this to be mutable so it can be modified at runtime.
# TODO (jathan): Move this into Redis and maintain with 'acl' command?
IGNORED_ACLS = [
    'netflow',
    'massive-edge-filter',
    'antispoofing',
]

# FILE names ACLs that shall not be modified by tools
# NOTE: These should be the names of the files as they exist in FIREWALL_DIR.
# Trigger expects ACLs to be prefixed with 'acl.'.  These are examples and
# should be replaced.
NONMOD_ACLS  = [
    'acl.netflow',
    'acl.antispoofing',
    'acl.border-protect',
    'acl.route-engine-protect',
]

# Mapping of real IP to external NAT. This is used by load_acl in the event
# that a TFTP or connection from a real IP fails or explicitly when passing the
# --no-vip flag.
# format: {local_ip: external_ip}
VIPS = {
    '10.20.21.151': '5.60.17.81',
    '10.10.18.157': '5.60.71.81',
}

#===============================
# ACL Loading/Rate-Limiting
#===============================
# All of the following settings are currently only used in ``load_acl``.  If
# and when the load_acl functionality gets moved into the API, this might
# change.

# Any FILTER name (not filename) in this list will be skipped during automatic loads.
AUTOLOAD_BLACKLIST = [
    'route-engine-protect',
    'netflow',
    'antispoofing',
    'static-policy',
    'border-protect',
]

# Assign blacklist to filter for backwards compatibility
AUTOLOAD_FILTER = AUTOLOAD_BLACKLIST

# Modify this if you want to create a list that if over the specified number of
# routers will be treated as bulk loads.
# TODO (jathan): Provide examples so that this has more context/meaning. The
# current implementation is kind of broken and doesn't scale for data centers
# with a large of number of devices.
AUTOLOAD_FILTER_THRESH = {
    'route-engine-protect':3,
    'antispoofing':5,
    '12345':10,
}

# Any ACL applied on a number of devices >= to this number will be treated as
# bulk loads.
AUTOLOAD_BULK_THRESH = 10

# Add an acl:max_hits here if you want to override BULK_MAX_HITS_DEFAULT
# Keep in mind this number is PER EXECUTION of load_acl --auto (typically once
# per hour or 3 per bounce window).
#
# 1 per load_acl execution; ~3 per day, per bounce window
# 2 per load_acl execution; ~6 per day, per bounce window
# etc.
BULK_MAX_HITS = {
    'abc123': 3,
    'xyz246': 5,
    'border-protect': 5,
}

# If an ACL is bulk but not in BULK_MAX_HITS, use this number as max_hits
BULK_MAX_HITS_DEFAULT = 1

#===============================
# OnCall Engineer Display
#===============================
# This variable should be a function that returns data for your on-call engineer, or
# failing that None.  The function should return a dictionary that looks like
# this:
#
# {'username': 'joegineer',
#  'name': 'Joe Engineer',
#  'email': 'joe.engineer@example.notreal'}
def get_current_oncall():
    """fetch current on-call info"""
    # from somewhere import get_primary_oncall()

    try:
        ret = get_primary_oncall()
    except:
        return None

    return ret

# If you don't want to return this information, have it return None.
GET_CURRENT_ONCALL = lambda x=None: x
#GET_CURRENT_ONCALL = get_current_oncall

#===============================
# CM Ticket Creation
#===============================
# This should be a function that creates a CM ticket and returns the ticket
# number, or None.
# TODO (jathan): Improve this interface so that it is more intuitive.
def create_cm_ticket(acls, oncall, service='load_acl'):
    """Create a CM ticket and return the ticket number or None"""
    # from somewhere import create_cm_ticket

    devlist = ''
    for dev, aclset in acls.items():
        a = sorted(aclset)
        devlist += "%-32s %s\n" % (dev, ' '.join(a))

    oncall['devlist'] = devlist
    oncall['service'] = service

    return create_ticket(**oncall)

def _create_cm_ticket_stub(**args):
    return None

# If you don't want to use this feature, just have the function return None.
#CREATE_CM_TICKET = lambda a=None o, s: None
CREATE_CM_TICKET = _create_cm_ticket_stub

#===============================
# Notifications
#===============================
# Email sender for integrated toosl. Usually a good idea to make this a
# no-reply address.
EMAIL_SENDER = 'nobody@not.real'

# Who to email when things go well (e.g. load_acl --auto)
SUCCESS_EMAILS = [
    #'neteng@example.com',
]

# Who to email when things go not well (e.g. load_acl --auto)
FAILURE_EMAILS = [
    #'primarypager@example.com',
    #'secondarypager@example.com',
]

# The default sender for integrated notifications. This defaults to the fqdn
# for the localhost.
NOTIFICATION_SENDER = socket.gethostname()

# Destinations (hostnames, addresses) to notify when things go well.
SUCCESS_RECIPIENTS = [
    # 'foo.example.com',
]

# Destinations (hostnames, addresses) to notify when things go not well.
FAILURE_RECIPIENTS = [
    # socket.gethostname(), # The fqdn for the localhost
]

# This is a list of fully-qualified paths. Each path should end with a callable
# that handles a notification event and returns ``True`` in the event of a
# successful notification, or ``None``.
NOTIFICATION_HANDLERS = [
    'trigger.utils.notifications.handlers.email_handler',
]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# Use the new RTD theme
RTD_NEW_THEME = True

import os
import re
import sys
from datetime import datetime


# Custom ReST roles. (Thanks for Fabric for these awesome ideas)
from docutils.parsers.rst import roles
from docutils import nodes, utils
issue_types = ('bug', 'feature', 'support')


def issues_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Use: :issue|bug|feature|support:`ticket number`

    When invoked as :issue:, turns into just a "#NN" hyperlink to Github.

    When invoked otherwise, turns into "[Type] <#NN hyperlink>: ".
    """
    # Old-style 'just the issue link' behavior
    issue_no = utils.unescape(text)
    ref = "https://github.com/trigger/trigger/issues/" + issue_no
    link = nodes.reference(rawtext, '#' + issue_no, refuri=ref, **options)
    ret = [link]
    # Additional 'new-style changelog' stuff
    if name in issue_types:
        which = '[<span class="changelog-%s">%s</span>]' % (
            name, name.capitalize()
        )
        ret = [
            nodes.raw(text=which, format='html'),
            nodes.inline(text=" "),
            link,
            nodes.inline(text=":")
        ]
    return ret, []

for x in issue_types + ('issue',):
    roles.register_local_role(x, issues_role)

# Also ripped from Fabric, but we need to nail down the versioning and release process for Trigger before we start to use this.
'''
year_arg_re = re.compile(r'^(.+?)\s*(?<!\x00)<(.*?)>$', re.DOTALL)
def release_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Invoked as :release:`N.N.N <YYYY-MM-DD>`.

    Turns into: <b>YYYY-MM-DD</b>: released <b><a>Trigger N.N.N</a></b>, with
    the link going to the Github source page for the tag.
    """
    # Make sure year has been specified
    match = year_arg_re.match(text)
    if not match:
        msg = inliner.reporter.error("Must specify release date!")
        return [inliner.problematic(rawtext, rawtext, msg)], [msg]
    number, date = match.group(1), match.group(2)
    return [
        nodes.strong(text=date),
        nodes.inline(text=": released "),
        nodes.reference(
            text="Fabric %s" % number,
            refuri="https://github.com/fabric/fabric/tree/%s" % number,
            classes=['changelog-release']
        )
    ], []
roles.register_local_role('release', release_role)
'''

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))
this = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(this, "_ext"))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'triggerdocs']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Trigger'
copyright = u'2006-%s, AOL Inc' % datetime.now().year

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))
#from trigger import __version__ as trigger_version
from trigger import full_version, short_version

# The short X.Y version.
version = short_version
# The full version, including alpha/beta/rc tags.
release = full_version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None
default_role = 'obj'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'
#html_style = 'rtd.css'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Triggerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Trigger.tex', u'Trigger Documentation',
   u'Jathan McCollum, Eileen Tschetter, Mark Ellzey Thomas, Michael Shields', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = triggerdocs

# triggerdocs.py - Custom docs extension for Sphinx

def setup(app):
    # Create a :setting: cross-ref to link to configuration options
    app.add_crossref_type(
        directivename='setting',
        rolename='setting',
        indextemplate='pair: %s; setting',
    )

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

# This is a sample settings.py that varies slightly from the default. Please see docs/configuration.rst or
# trigger/conf/global_settings.py for the complete list of default settings.

import IPy
import os
import socket

#===============================
# Global Settings
#===============================

# This is where Trigger should look for its files.
PREFIX = '/etc/trigger'

# Set to True to enable GPG Authentication
# Set to False to use the old .tackf encryption method.
# Should be False unless instructions/integration is ready for GPG
USE_GPG_AUTH = False

# This is used for old auth method. It sucks and needs to die.
# TODO (jathan): This is deprecated. Remove all references to this and make GPG
# the default and only method.
TACACSRC_KEYFILE = os.path.join(PREFIX, '.tackf')
TACACSRC_PASSPHRASE = 'bacon is awesome, son.' # NYI

# Default login realm to store user credentials (username, password) for
# general use within the .tacacsrc
DEFAULT_REALM = 'aol'

# Location of firewall policies
FIREWALL_DIR = '/data/firewalls'

# Location of tftproot.
TFTPROOT_DIR = '/data/tftproot'

# Add internally owned networks here. All network blocks owned/operated and
# considered part of your network should be included.
INTERNAL_NETWORKS = [
    IPy.IP("10.0.0.0/8"),
    IPy.IP("172.16.0.0/12"),
    IPy.IP("192.168.0.0/16"),
]

# The tuple of supported vendors derived from the values of VENDOR_MAP
SUPPORTED_VENDORS = (
    'a10',
    'arista',
    'brocade',
    'cisco',
    'citrix',
    'dell',
    'foundry',
    'juniper',
    'netscreen'
)
VALID_VENDORS = SUPPORTED_VENDORS # For backwards compatibility

# A mapping of manufacturer attribute values to canonical vendor name used by
# Trigger. These single-word, lowercased canonical names are used throughout
# Trigger.
#
# If your internal definition differs from the UPPERCASED ones specified below
# (which they probably do, customize them here.
VENDOR_MAP = {
    'A10 NETWORKS': 'a10',
    'ARISTA NETWORKS': 'arista',
    'BROCADE': 'brocade',
    'CISCO SYSTEMS': 'cisco',
    'CITRIX': 'citrix',
    'DELL': 'dell',
    'FOUNDRY': 'foundry',
    'JUNIPER': 'juniper',
    'NETSCREEN TECHNOLOGIES': 'netscreen',
}

# A dictionary keyed by manufacturer name containing a list of the device types
# for each that is officially supported by Trigger.
SUPPORTED_PLATFORMS = {
    'a10': ['SWITCH'],
    'arista': ['SWITCH'],                         # Your "Cloud" network vendor
    'brocade': ['ROUTER', 'SWITCH'],
    'cisco': ['ROUTER', 'SWITCH'],
    'citrix': ['SWITCH'],                         # Assumed to be NetScalers
    'dell': ['SWITCH'],
    'foundry': ['ROUTER', 'SWITCH'],
    'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],  # Any devices running Junos
    'netscreen': ['FIREWALL'],                    # Pre-Juniper NetScreens
}

# The tuple of support device types
SUPPORTED_TYPES = ('FIREWALL', 'ROUTER', 'SWITCH')

# A mapping of of vendor names to the default device type for each in the
# event that a device object is created and the deviceType attribute isn't set
# for some reason.
DEFAULT_TYPES = {
    'a10': 'SWITCH',
    'arista': 'SWITCH',
    'brocade': 'SWITCH',
    'citrix': 'SWITCH',
    'cisco': 'ROUTER',
    'dell': 'SWITCH',
    'foundry': 'SWITCH',
    'juniper': 'ROUTER',
    'netscreen': 'FIREWALL',
}

# When a vendor is not explicitly defined within `DEFAULT_TYPES`, fallback to
# this type.
FALLBACK_TYPE = 'ROUTER'

#===============================
# Twister
#===============================

# Default timeout in seconds for commands executed during a session.  If a
# response is not received within this window, the connection is terminated.
DEFAULT_TIMEOUT = 5 * 60

# Default timeout in seconds for initial telnet connections. 
TELNET_TIMEOUT  = 60

# Whether or not to allow telnet fallback
TELNET_ENABLED = True

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable interactive (pty) SSH sessions, such as when using
# bin/gong.
SSH_PTY_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable asynchronous (NON-interactive) SSH sessions, such as
# when using twister or Commando to remotely control a device.
SSH_ASYNC_DISABLED = {
    'arista': ['SWITCH'],  # Known not to work w/ SSH ... yet
    'brocade': ['SWITCH'], # Namely the Brocade VDX =(
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'a10',
    'arista',
    'brocade',
    'cisco',
    'dell',
    'foundry',
)

#===============================
# NetDevices
#===============================

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# A tuple of data loader classes, specified as strings. Optionally, a tuple can
# be used instead of a string. The first item in the tuple should be the
# Loader's module, subsequent items are passed to the Loader during
# initialization.
NETDEVICES_LOADERS = (
    'trigger.netdevices.loaders.filesystem.XMLLoader',
    'trigger.netdevices.loaders.filesystem.JSONLoader',
    'trigger.netdevices.loaders.filesystem.SQLiteLoader',
    'trigger.netdevices.loaders.filesystem.CSVLoader',
    'trigger.netdevices.loaders.filesystem.RancidLoader',
    # Example of a database loader where the db information is sent along as an
    # argument. The args can be anything you want.
    #['trigger.netdevices.loaders.mysql.Loader', {'dbuser': 'root', 'dbpass': 'abc123', 'dbhost': 'localhost', 'dbport': 3306}, 'bacon'],
)

# A path or URL to netdevices device metadata source data, which is used to
# populate trigger.netdevices.NetDevices. For more information on this, see
# NETDEVICES_LOADERS.
NETDEVICES_SOURCE = os.environ.get('NETDEVICES_SOURCE', os.path.join(PREFIX, 'netdevices.xml'))

# Assign NETDEVICES_SOURCE to NETDEVICES_FILE for backwards compatibility
NETDEVICES_FILE = NETDEVICES_SOURCE

# Whether to treat the RANCID root as a normal instance, or as the root to
# multiple instances. This is only checked when using RANCID as a data source.
RANCID_RECURSE_SUBDIRS = os.environ.get('RANCID_RECURSE_SUBDIRS', False)

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and should be
# changed to match your environment.
VALID_OWNERS = (
    'Data Center',
    'Backbone Engineering',
    'Enterprise Networking',
)

# Fields and values defined here will dictate which Juniper devices receive a#
# ``commit-configuration full`` when populating ``NetDevice.commit_commands`.#
# The fields and values must match the objects exactly or it will fallback to
# ``commit-configuration``.
JUNIPER_FULL_COMMIT_FIELDS = {
    'deviceType': 'SWITCH',
    'make': 'EX4200',
}

#===============================
# Bounce Windows/Change Mgmt
#===============================

# Path of the explicit module file for bounce.py containing custom bounce
# window mappings.
BOUNCE_FILE = os.environ.get('BOUNCE_FILE', os.path.join(PREFIX, 'bounce.py'))

# Default bounce timezone. All BounceWindow objects are configured using
# US/Eastern for now.
BOUNCE_DEFAULT_TZ = 'US/Eastern'

# The default fallback window color for bounce windows. Must be one of
# ('green', 'yellow', or 'red').
#
#     green: Low risk
#    yellow: Medium risk
#       red: High risk
BOUNCE_DEFAULT_COLOR = 'red'

#===============================
# Redis Settings
#===============================

# Redis master server. This will be used unless it is unreachable.
REDIS_HOST = '127.0.0.1'

# The Redis port. Default is 6379.
REDIS_PORT = 6379

# The Redis DB. Default is 0.
REDIS_DB = 0

#===============================
# Database Settings
#===============================

# These are self-explanatory, I hope.
# TODO (jathan): Replace remaining db interaction w/ Redis.
DATABASE_NAME = 'trigger'
DATABASE_USER = 'trigger'
DATABASE_PASSWORD = 'abc123'
DATABASE_HOST = '127.0.0.1'
DATABASE_PORT = 3306

#===============================
# ACL Management
#===============================
# FILTER names of ACLs that should be skipped or ignored by tools
# NOTE: These should be the names of the filters as they appear on devices. We
# want this to be mutable so it can be modified at runtime.
# TODO (jathan): Move this into Redis and maintain with 'acl' command?
IGNORED_ACLS = [
    'netflow', 
    'massive-edge-filter',
    'antispoofing',
]

# FILE names ACLs that shall not be modified by tools
# NOTE: These should be the names of the files as they exist in FIREWALL_DIR.
# Trigger expects ACLs to be prefixed with 'acl.'.  These are examples and
# should be replaced.
NONMOD_ACLS  = [ 
    'acl.netflow', 
    'acl.antispoofing',
    'acl.border-protect',
    'acl.route-engine-protect',
]

# Mapping of real IP to external NAT. This is used by load_acl in the event
# that a TFTP or connection from a real IP fails or explicitly when passing the
# --no-vip flag.
# format: {local_ip: external_ip}
VIPS = {
    '10.20.21.151': '5.60.17.81',
    '10.10.18.157': '5.60.71.81',
}

#===============================
# ACL Loading/Rate-Limiting
#===============================
# All of the following settings are currently only used in ``load_acl``.  If
# and when the load_acl functionality gets moved into the API, this might
# change.

# Any FILTER name (not filename) in this list will be skipped during automatic loads.
AUTOLOAD_BLACKLIST = [
    'route-engine-protect',
    'netflow', 
    'antispoofing',
    'static-policy',
    'border-protect',
]

# Assign blacklist to filter for backwards compatibility
AUTOLOAD_FILTER = AUTOLOAD_BLACKLIST

# Modify this if you want to create a list that if over the specified number of
# routers will be treated as bulk loads.
# TODO (jathan): Provide examples so that this has more context/meaning. The
# current implementation is kind of broken and doesn't scale for data centers
# with a large of number of devices.
AUTOLOAD_FILTER_THRESH = {
    'route-engine-protect':3,
    'antispoofing':5,
    '12345':10,
}

# Any ACL applied on a number of devices >= to this number will be treated as
# bulk loads.
AUTOLOAD_BULK_THRESH = 10

# Add an acl:max_hits here if you want to override BULK_MAX_HITS_DEFAULT
# Keep in mind this number is PER EXECUTION of load_acl --auto (typically once
# per hour or 3 per bounce window).
#
# 1 per load_acl execution; ~3 per day, per bounce window
# 2 per load_acl execution; ~6 per day, per bounce window
# etc.
BULK_MAX_HITS = {
    'abc123': 3,
    'xyz246': 5,
    'border-protect': 5,
}

# If an ACL is bulk but not in BULK_MAX_HITS, use this number as max_hits
BULK_MAX_HITS_DEFAULT = 1

#===============================
# OnCall Engineer Display
#===============================
# This variable should be a function that returns data for your on-call engineer, or
# failing that None.  The function should return a dictionary that looks like
# this:
#
# {'username': 'joegineer', 
#  'name': 'Joe Engineer', 
#  'email': 'joe.engineer@example.notreal'}
def get_current_oncall():
    """fetch current on-call info"""
    # from somewhere import get_primary_oncall()

    try:
        ret = get_primary_oncall()
    except:
        return None

    return ret

# If you don't want to return this information, have it return None.
GET_CURRENT_ONCALL = lambda x=None: x
#GET_CURRENT_ONCALL = get_current_oncall

#===============================
# CM Ticket Creation
#===============================
# This should be a function that creates a CM ticket and returns the ticket
# number, or None. 
# TODO (jathan): Improve this interface so that it is more intuitive.
def create_cm_ticket(acls, oncall, service='load_acl'):
    """Create a CM ticket and return the ticket number or None"""
    # from somewhere import create_cm_ticket

    devlist = ''
    for dev, aclset in acls.items():
        a = sorted(aclset)
        devlist += "%-32s %s\n" % (dev, ' '.join(a))
        
    oncall['devlist'] = devlist
    oncall['service'] = service

    return create_ticket(**oncall)

def _create_cm_ticket_stub(**args):
    return None

# If you don't want to use this feature, just have the function return None.
#CREATE_CM_TICKET = lambda a=None o, s: None
CREATE_CM_TICKET = _create_cm_ticket_stub

#===============================
# Notifications
#===============================
# Email sender for integrated toosl. Usually a good idea to make this a
# no-reply address.
EMAIL_SENDER = 'nobody@not.real'

# Who to email when things go well (e.g. load_acl --auto)
SUCCESS_EMAILS = [
    #'neteng@example.com',
]

# Who to email when things go not well (e.g. load_acl --auto)
FAILURE_EMAILS = [
    #'primarypager@example.com',
    #'secondarypager@example.com',
]

# The default sender for integrated notifications. This defaults to the fqdn
# for the localhost.
NOTIFICATION_SENDER = socket.gethostname()

# Destinations (hostnames, addresses) to notify when things go well.
SUCCESS_RECIPIENTS = [
    # 'foo.example.com',
]

# Destinations (hostnames, addresses) to notify when things go not well.
FAILURE_RECIPIENTS = [
    # socket.gethostname(), # The fqdn for the localhost
]

# This is a list of fully-qualified paths. Each path should end with a callable
# that handles a notification event and returns ``True`` in the event of a
# successful notification, or ``None``.
NOTIFICATION_HANDLERS = [
    'trigger.utils.notifications.handlers.email_handler',
]

########NEW FILE########
__FILENAME__ = trigger_acceptance_tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/trigger_acceptance_test.py - Acceptance test suite that verifies trigger functionality
in very brief
"""

from trigger.netdevices import NetDevices
netdevices = NetDevices(with_acls=False)
nd=NetDevices(with_acls=False)
print nd.values()

__author__ = 'Murat Ezbiderli'
__maintainer__ = 'Salesforce'
__copyright__ = 'Copyright 2012-2013 Salesforce Inc.'
__version__ = '2.1'

import os
import unittest

from trigger.netdevices import NetDevices

class NetDevicesTest(unittest.TestCase):

    def setUp(self):
        self.nd = NetDevices(with_acls=False)
	print self.nd.values()
        self.nodename = self.nd.keys()[0]
        self.nodeobj = self.nd.values()[0]

    def testBasics(self):
        """Basic test of NetDevices functionality."""
        self.assertEqual(len(self.nd), 3)
        self.assertEqual(self.nodeobj.nodeName, self.nodename)
        self.assertEqual(self.nodeobj.manufacturer, 'JUNIPER')

    def testFind(self):
        """Test the find() method."""
        self.assertEqual(self.nd.find(self.nodename), self.nodeobj)
        nodebasename = self.nodename[:self.nodename.index('.')]
        self.assertEqual(self.nd.find(nodebasename), self.nodeobj)
        self.assertRaises(KeyError, lambda: self.nd.find(self.nodename[0:3]))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = autoacl
# Dummy version of autoacl.py, for test cases.

from twisted.python import log

DC_ONCALL_ID = '17'

def autoacl(dev, explicit_acls=None):
    """A simple test case. NYI"""
    acls = set()
    log.msg('[%s]: Adding auto ACLs' % dev)
    if dev.vendor == 'juniper':
        log.msg('[%s]: Adding 115j' % dev)
        acls.add('115j')
        if dev.onCallID == DC_ONCALL_ID:
            acls.add('router-protect.core')
            log.msg('[%s]: Adding router-protect.core' % dev)
        else:
            acls.add('router-protect')
            log.msg('[%s]: Adding router-protect' % dev)

    return acls

########NEW FILE########
__FILENAME__ = bounce
# -*- coding: utf-8 -*-

"""
This file controls when bounce windows get auto-applied to network devices.

This module is expected to provide a ``bounce()`` function that takes a
`~trigger.netdevice.NetDevice` as the mandatory first argument and returns a
`~trigger.changemgmt.BounceWindow` object. The ``bounce()`` function is
imported by `~trigger.changemgmt` and `~trigger.netdevices`.

This file should be placed in the location specified in Trigger's
``settings.py`` using the :setting:`BOUNCE_FILE`` setting, which defaults to
``/etc/trigger/bounce.py``.

How you decide to return the bounce window object is up to you, and therein
lies the fun! This is meant to be an example of how one might customize bounce
windows and map them to devices in their environment.
"""

from trigger.changemgmt import BounceWindow as BW

# Bounce windows for Backbone (all times US/Eastern)
BACKBONE = {
    'ABC': BW(green='0, 22-23', yellow='1-12, 19-21', red='13-18'),
    'BBQ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
    'COW': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'FAP': BW(green='21-23', yellow='0-12, 19-20', red='13-18'),
    'FUN': BW(green='2-4', yellow='0-1, 5-14, 21-23', red='15-20'),
    'OMG': BW(green='5-7', yellow='1-4, 8-18', red='0, 19-23'),
    'XYZ': BW(green='3-5', yellow='0-2, 6-11', red='12-23'),
}

# Bounce windows for Data Center (all times US/Eastern)
DATACENTER = {
    'ABC': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'BBQ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
    'FUN': BW(green='21-23', yellow='0-12, 17-20', red='13-16'),
    'OMG': BW(green='15-18', yellow='0-4, 19-23', red='5-14'),
    'XYZ': BW(green='5-7', yellow='0-4, 8-15', red='16-23'),
}

# Out-of-band network (all times US/Eastern)
OOB = {
    'ABC': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'BBQ': BW(green='14-17', yellow='18-20', red='1-13, 21-23'),
    'OMG': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
    'XYZ': BW(green='14-17', yellow='5-13, 18-20', red='1-4, 21-23'),
}

# Team definitions
TEAM_DC = 'Data Center'
TEAM_BB = 'Backbone'

# Mapping of team name to bounce windows
BOUNCE_MAP = {
    TEAM_DC: DATACENTER,
    TEAM_BB: BACKBONE,
}

# Defaults
DEFAULT_BOUNCE_SITE = 'ABC'
DEFAULT_BOUNCE_TEAM = TEAM_DC
DEFAULT_BOUNCE = BOUNCE_MAP[DEFAULT_BOUNCE_TEAM][DEFAULT_BOUNCE_SITE]

def bounce(device, default=DEFAULT_BOUNCE):
    """
    Return the bounce window for a given device.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param default:
        A `~trigger.changemgmt.BounceWindow` object.
    """

    # First try OOB, since it's special
    if 'ilo' in device.nodeName or 'oob' in device.nodeName:
        windows = OOB
    # Try to get the bounce windows by owningTeam
    else:
        windows = BOUNCE_MAP.get(device.owningTeam)

    # If we got nothin', return default
    if windows is None:
        return default

    # Try to get the bounce window by site, or fallback to default
    mybounce = windows.get(device.site, default)

    return mybounce

########NEW FILE########
__FILENAME__ = settings
import os

# Owners to use in testing...
VALID_OWNERS = ('Data Center',)

# Database stuff
DATABASE_ENGINE = 'sqlite3'

# The prefix is... ME! (Abs path to the current file)
PREFIX = os.path.dirname(os.path.abspath(__file__))

# .tacacsrc Stuff
DEFAULT_REALM = 'aol'
TACACSRC_KEYFILE = os.getenv('TACACSRC_KEYFILE', os.path.join(PREFIX, 'tackf'))
TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'tacacsrc'))
RIGHT_TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'right_tacacsrc'))
MEDIUMPW_TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'mediumpw_tacacsrc'))
LONGPW_TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'longpw_tacacsrc'))
BROKENPW_TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'brokenpw_tacacsrc'))
EMPTYPW_TACACSRC = os.getenv('TACACSRC', os.path.join(PREFIX, 'emptypw_tacacsrc'))


# Configs
NETDEVICES_SOURCE = os.environ.get('NETDEVICES_SOURCE',
                                   os.path.join(PREFIX, 'netdevices.xml'))
AUTOACL_FILE = os.environ.get('AUTOACL_FILE',
                              os.path.join(PREFIX, 'autoacl.py'))
BOUNCE_FILE = os.environ.get('BOUNCE_FILE', os.path.join(PREFIX, 'bounce.py'))

########NEW FILE########
__FILENAME__ = test_acl
#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0'

from StringIO import StringIO
import unittest
from trigger import acl, exceptions

EXAMPLES_FILE = 'tests/data/junos-examples.txt'

# Some representative match clauses:
ios_matches = ('tcp 192.0.2.0 0.0.0.255 any gt 65530',                # 1
               'udp any host 192.0.2.99 eq 80',                        # 2
               '16 any host 192.0.2.99',                        # 3
               'tcp any host 192.0.2.99 range 1 4 established',        # 4
               'icmp any any 13 37',                                # 5
               'icmp any any unreachable',                        # 6
               'icmp any any echo-reply',                        # 7
               'tcp 192.0.2.96 0.0.0.31 any eq 80',                # 8
               'ip any any')


class CheckRangeList(unittest.TestCase):
    """Test functionality of RangeList object"""
    def testDegenerateRange(self):
        """Make sure that the range x-x is the same as x."""
        r = acl.RangeList([(1024, 1024)])
        self.assertEqual(r, [1024])

    def testDuplicateProtocol(self):
        """Test duplicate protocols."""
        # Regression: These weren't suppresed because they are unique
        # objects, and so a Set can contain more than one of them.
        r = acl.RangeList([acl.Protocol(6), acl.Protocol(6)])
        self.assertEqual(r, [acl.Protocol(6)])

    def testAdjacentRanges(self):
        """See if adjacent ranges are coalesced into one."""
        r = acl.RangeList([(100, 199), (200, 299)])
        self.assertEqual(r, [(100, 299)])

    def testOverlappingRanges(self):
        """See if overlapping ranges are coalesced into one."""
        r = acl.RangeList([(100, 250), (200, 299)])
        self.assertEqual(r, [(100, 299)])

    def testOverlappingRangeAndInteger(self):
        """See if a single value that's also part of a range is elided."""
        r = acl.RangeList([(100, 199), 150])
        self.assertEqual(r, [(100, 199)])

    def testMultipleConstants(self):
        """See if several discrete values are collapsed correctly."""
        r = acl.RangeList([5, 5, 5, 8, 9, 10])
        self.assertEqual(r, [5, (8, 10)])

    def testNonIncrementable(self):
        """Make sure non-incrementable values can be stored."""
        r = acl.RangeList(['y', 'x'])
        self.assertEqual(r, ['x', 'y'])

    def testRangeListContains(self):
        """Check RangeList behavior as a container type."""
        r = acl.RangeList([1, (3, 6)])
        self.assertTrue(1 in r)
        self.assertTrue(5 in r)
        self.assertTrue(0 not in r)
        r = acl.RangeList([acl.TIP('10/8'), acl.TIP('172.16/12')])
        self.assertTrue(acl.TIP('10.1.1.1') in r)
        self.assertTrue(acl.TIP('192.168.1.1') not in r)

class CheckACLNames(unittest.TestCase):
    """Test ACL naming validation"""
    def testOkNames(self):
        """Test names that are valid in at least one vendor's ACLs"""
        names = ('101', '131mj', 'STR-MDC-ATM', 'with space', '3.14', None)
        for name in names:
            a = acl.ACL(name=name)

    def testBadNames(self):
        """Test names that are valid in no vendor's ACLs"""
        for name in ('', 'x'*25):
            try:
                a = acl.ACL(name=name)
            except exceptions.ACLNameError:
                pass
            else:
                self.fail('expected ACLNameError on "' + name + '"')

class CheckACLTerms(unittest.TestCase):
    """Test insertion of Term objects into an ACL object"""
    def testEmptyAnonymousTerms(self):
        """Test inserting multiple anonymous empty terms"""
        a = acl.ACL()
        for i in range(5):
            a.terms.append(acl.Term())
            self.assertEqual(a.terms[i].name, None)
        self.assertEqual(len(a.terms), 5)

    def testEmptyNamedTerms(self):
        """Test inserting multiple anonymous named terms"""
        a = acl.ACL()
        for i in range(5):
            name = 'term' + str(i)
            a.terms.append(acl.Term(name))
            self.assertEqual(a.terms[i].name, name)
        self.assertEqual(len(a.terms), 5)

class CheckTerms(unittest.TestCase):
    """Test validity and functionality of Term objects"""
    def testOkNames(self):
        """Test valid JunOS term names"""
        for name in ('101', 'T1337', 'sr12345', '3.1415926'):
            t = acl.Term(name=name)

    def testBadNames(self):
        """Test invalid JunOS term names"""
        for name in ('', 'x'*300):
            try:
                t = acl.Term(name=name)
            except exceptions.BadTermName:
                pass
            else:
                self.fail('expected BadTermNameon "' + name + '"')

    def testOkActions(self):
        """Test valid filter actions"""
        for action in (('next', 'term'), ('routing-instance', 'blah'),
                       ('reject', 'tcp-reset'), 'accept', 'discard'):
            t = acl.Term(action=action)
            if isinstance(action, tuple):
                self.assertEqual(t.action, action)
            else:
                self.assertEqual(t.action, (action,))
                t = acl.Term(action=(action,))
                self.assertEqual(t.action, (action,))
        for action in ('deny', 'reject',
                       ('reject', 'administratively-prohibited')):
            t = acl.Term(action=action)
            self.assertEqual(t.action, ('reject',))
        t = acl.Term(action='permit')
        self.assertEqual(t.action, ('accept',))

    def testBadActions(self):
        """Test invalid filter actions"""
        t = acl.Term()
        for action in ('blah', '', ('reject', 'because-I-said-so'),
                       ('routing-instance', 'x'*300), 'sample'):
            try:
                t = acl.Term(action=action)
            except exceptions.ActionError:
                pass
            else:
                self.fail('expected ActionError on "%s"' % str(action))

    def testOkModifiers(self):
        """Test valid filter action modifiers"""
        t = acl.Term(action='discard')
        for action in (('count', 'abc'), ('forwarding-class', 'abc'),
                       ('ipsec-sa', 'abc'), 'log', ('loss-priority', 'low'),
                       ('policer', 'abc'), 'sample', 'syslog'):
            t.set_action_or_modifier(action)
            if isinstance(action, tuple):
                self.assertEqual(t.modifiers[action[0]], action[1])
            else:
                self.assertEqual(t.modifiers[action], None)
                t.set_action_or_modifier((action,))
                self.assertEqual(t.modifiers[action], None)
        # Make sure none of these modified the primary action.
        self.assertEqual(t.action, ('discard',))

    def testBadModifiers(self):
        """Test invalid filter action modifiers"""
        for action in (('count', ''), ('count',), 'count', ('count', 'a-b-c'),
                       ('loss-priority', '17'), ('sample', 'abc')):
            try:
                t = acl.Term(action=action)
            except exceptions.ActionError:
                pass
            else:
                self.fail('expected ActionError on "%s"' % str(action))

    def testOkMatches(self):
        """Test valid match conditions"""
        t = acl.Term()
        t.match['destination-port'] = [25]
        self.assertEqual(t.match['destination-port'], [25])
        t.match['destination-port'] = range(100, 200)
        self.assertEqual(t.match['destination-port'], [(100, 199)])
        t.match['source-port'] = ['tftp']
        self.assertEqual(t.match['source-port'], [69])
        t.match['protocol'] = ['ospf', 6, 17]
        self.assertEqual(t.match['protocol'], [6, 17, 89])
        t.match['fragment-offset'] = [1337]
        self.assertEqual(t.match['fragment-offset'], [1337])
        t.match['icmp-type'] = ['unreachable']
        self.assertEqual(t.match['icmp-type'], [3])
        t.match['destination-address'] = ['192.0.2.0/24']
        self.assertEqual(str(t.match['destination-address'][0]), '192.0.2.0/24')
        t.match['source-prefix-list'] = ['blah']
        self.assertEqual(t.match['source-prefix-list'], ['blah'])

    def testBadMatches(self):
        """Test invalid match conditions"""
        t = acl.Term()
        # Valid match type with invalid arg.
        try:
            t.match['fragment-offset'] = [65536]
        except exceptions.BadMatchArgRange:
            pass
        else:
            self.fail('expected MatchError')
        # Valid match type with non-list argument.
        try:
            t.match['fragment-offset'] = 0
        except TypeError:
            pass
        else:
            self.fail('expected MatchError')
        # Valid match type with null arg.
        try:
            t.match['protocol'] = None
        except exceptions.MatchError:
            pass
        else:
            self.fail('expected MatchError')
        # Invalid match type.
        try:
            t.match['boogaloo'] = 1337
        except exceptions.MatchError:
            pass
        else:
            self.fail('expected MatchError')

class CheckProtocolClass(unittest.TestCase):
    """Test functionality of Protocol object"""
    def testKnownProto(self):
        """Test magic stringification of a known numeric protocol."""
        p = acl.Protocol(6)
        self.assertEqual(str(p), 'tcp')
        self.assertEqual(p, 'tcp')
        self.assertEqual(p, 6)

    def testNamedProto(self):
        """Test magic stringification of a named protocol."""
        p = acl.Protocol('tcp')
        self.assertEqual(str(p), 'tcp')
        self.assertEqual(p, 'tcp')
        self.assertEqual(p, 6)

    def testUnknownProto(self):
        """Test magic stringification of a numeric protocol."""
        p = acl.Protocol('99')
        self.assertEqual(str(p), '99')
        self.assertEqual(p, '99')
        self.assertEqual(p, 99)


class CheckOutput(unittest.TestCase):
    """Test .output() methods for various ACL vendors"""
    def setUp(self):
        super(CheckOutput, self).setUp()
        self.a = acl.ACL()
        self.t1 = acl.Term(name='p99')
        self.t1.match['protocol'] = [99]
        self.t1.action = 'accept'
        self.a.terms.append(self.t1)
        self.t2 = acl.Term(name='windows')
        self.t2.match['protocol'] = ['tcp']
        self.t2.match['source-address'] = ['192.0.2.0/24']
        self.t2.match['destination-port'] = range(135, 139) + [445]
        self.t2.action = 'reject'
        self.t2.modifiers['syslog'] = True
        self.a.terms.append(self.t2)

    def testJunOS(self):
        """Test conversion of ACLs and terms to JunOS format"""
        self.a.name = '100j'
        self.t1.modifiers['count'] = 'p99'
        output = """\
filter 100j {
    term p99 {
        from {
            protocol 99;
        }
        then {
            accept;
            count p99;
        }
    }
    term windows {
        from {
            source-address {
                192.0.2.0/24;
            }
            protocol tcp;
            destination-port [ 135-138 445 ];
        }
        then {
            reject;
            syslog;
        }
    }
}"""
        self.assertEqual(self.a.output_junos(), output.split('\n'))

    def testIOS(self):
        """Test conversion of ACLs and terms to IOS classic format"""
        self.a.name = 100
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        output = """\
access-list 100 permit 99 any any
access-list 100 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
access-list 100 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_ios(), output.split('\n'))

    def testIOSExtended(self):
        """Test conversion of ACLs and terms to IOS extended format"""
        self.a.name = 'BLAHBLAH'
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        output = """\
ip access-list extended BLAHBLAH
 permit 99 any any
 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_ios_named(), output.split('\n'))

    def testIOSXR(self):
        """Test conversion of ACLs and terms to IOS XR format"""
        self.a.name = 'BLAHBLAH'
        try:
            del self.t1.modifiers['count']
        except KeyError:
            pass
        self.t1.name = self.t2.name = None
        output = """\
ipv4 access-list BLAHBLAH
 10 permit 99 any any
 20 deny tcp 192.0.2.0 0.0.0.255 any range 135 138 log
 30 deny tcp 192.0.2.0 0.0.0.255 any eq 445 log"""
        self.assertEqual(self.a.output_iosxr(), output.split('\n'))

    def testMissingTermName(self):
        """Test conversion of anonymous terms to JunOS format"""
        self.assertRaises(exceptions.MissingTermName, acl.Term().output_junos)

    def testMissingACLName(self):
        """Test conversion of anonymous ACLs to JunOS format"""
        self.assertRaises(exceptions.MissingACLName, acl.ACL().output_junos)

    def testBadACLNames(self):
        """Test conversion of ACLs with vendor-invalid names"""
        a = acl.ACL()
        for bad_name in ('blah', '500', '1', '131dj'):
            a.name = bad_name
            self.assertRaises(exceptions.BadACLName, a.output_ios)

class CheckIOSParseAndOutput(unittest.TestCase):
    """Test parsing of IOS ACLs"""
    def testIOSACL(self):
        """Test parsing of IOS numbered ACLs."""
        text = '\n'.join(['access-list 100 permit ' + x for x in ios_matches])
        self.assertEqual('\n'.join(acl.parse(text).output_ios()), text)
        # Non-canonical forms:
        x = 'access-list 100 permit icmp any any log echo'
        y = 'access-list 100 permit icmp any any echo log'
        a = acl.parse(x)
        self.assertEqual(a.output_ios(), [y])
        self.assertEqual(a.format, 'ios')

    def testIOSNamedACL(self):
        """Test parsing of IOS named ACLs."""
        x = 'ip access-list extended foo\n'
        x += '\n'.join([' permit ' + x for x in ios_matches])
        a = acl.parse(x)
        self.assertEqual(a.output_ios_named(), x.split('\n'))
        self.assertEqual(a.format, 'ios_named')

    def testIOSNamedACLRemarks(self):
        """Test parsing of 'remark' lines in IOS named ACLs."""
        x = '''\
ip access-list extended foo
 permit nos any any
 remark Need more NOS!
 permit nos any any'''
        self.assertEqual(acl.parse(x).output_ios_named(), x.split('\n'))

    def testIOSACLDecoration(self):
        """Test IOS ACLs with comments, blank lines, and "end"."""
        x = '\n! comment\n\naccess-list 100 permit udp any any log ! ok\nend\n'
        y = ['! ok', '! comment', 'access-list 100 permit udp any any log']
        a = acl.parse(x)
        self.assertEqual(a.output_ios(), y)

    def testIOSACLNegation(self):
        """Test handling of "no access-list" command."""
        x = ['access-list 100 permit udp any any',
             'no access-list 100',
             'access-list 100 permit tcp any any']
        self.assertEqual(acl.parse('\n'.join(x)).output_ios(), x[-1:])

    def testIOSBadACL(self):
        """Test handling of a bad ACL."""
        text = 'access-list 145 permit tcp any any;\naccess-list 145 deny ip any any'
        self.assertRaises(exceptions.ParseError, lambda: acl.parse(text))

    def testIOSNonCanonical(self):
        """Test parsing of IOS match terms in non-output formats."""
        x = 'access-list 100 permit tcp any any eq ftp-data'
        y = 'access-list 100 permit tcp any any eq 20'
        self.assertEqual(acl.parse(x).output_ios(), [y])
        x = 'access-list 100 permit ip any 192.0.2.99 0.0.0.0'
        y = 'access-list 100 permit ip any host 192.0.2.99'
        self.assertEqual(acl.parse(x).output_ios(), [y])

    def testIOSLongComments(self):
        """Test long comments in IOS ACLs."""
        # Regression: naïve comment handling caused this to exceed the
        # maximum recursion depth.
        acl.parse('!'*200 + '\naccess-list 100 deny ip any any')

class CheckJunOSExamples(unittest.TestCase):
    """Test parsing of Junos ACLs"""
    def testJunOSExamples(self):
        """Test examples from JunOS documentation."""
        examples = file(EXAMPLES_FILE).read().expandtabs().split('\n\n')
        # Skip the last two because they use the unimplemented "except"
        # feature in address matches.
        for i in range(0, 14, 2):
            if examples[i+1].find('policer'):
                continue
            x = examples[i+1].split('\n')
            y = acl.parse(examples[i]).output_junos()
            self.assertEqual(x, y)
            self.assertEqual(y.format, 'junos')
            z = acl.parse('\n'.join(y)).output_junos()
            self.assertEqual(y, z)

class CheckMiscJunOS(unittest.TestCase):
    """Test misc. Junos-related ACL features"""
    def testFirewallReplace(self):
        """Test JunOS ACL with "firewall { replace:" around it."""
        acl.parse('''
firewall {
replace:
    filter blah {
        term foo { 
            then {
                accept;
            }
        }
    }
}''')

    def testTCPFlags(self):
        """Test tcp-established and is-fragment."""
        x = '''\
filter x {
    term y {
        from {
            is-fragment;
            tcp-established;
        }
        then {
            accept;
        }
    }
}'''
        self.assertEqual(x, '\n'.join(acl.parse(x).output_junos()))

    def testPacketLengthString(self):
        """Test packet-length as a string."""
        # Previous bug failed to parse this into an integer.
        t = acl.Term()
        t.match['packet-length'] = ['40']
        self.assertEqual(t.match['packet-length'], [40])

    def testInactiveTerm(self):
        """Test terms flagged as inactive."""
        x = '''\
filter 100 {
    term t1 {
        then {
            reject;
        }
    }
    inactive: term t2 {
        then {
            accept;
        }
    }
    term t3 {
        then {
            accept;
        }
    }
}'''
        y = acl.parse(x)
        self.assertEqual(y.output_junos(), x.split('\n'))
        self.assertRaises(exceptions.VendorSupportLacking, y.output_ios)

    def testInterfaceSpecific(self):
        """Test support of Juniper 'interface-specific statement"""
        x = '''filter x { interface-specific; term y { then accept; } }'''
        y = acl.parse(x)
        self.assertTrue(y.interface_specific)
        self.assertEqual(y.output_junos()[1], '    interface-specific;')

    def testShorthandIPv4(self):
        """Test incomplete IP blocks like "10/8" (vs. "10.0.0.0/8")."""
        x = '''filter x { term y { from { address { 10/8; } } } }'''
        y = acl.parse(x)
        self.assertEqual(y.terms[0].match['address'][0].strNormal(),
                         '10.0.0.0/8')

    def testModifierWithoutAction(self):
        """Test modifier without action."""
        x = '''filter x { term y { then { count z; } } }'''
        y = acl.parse(x)
        self.assertEqual(y.terms[0].action, ('accept',))

    def testNameTerms(self):
        """Test automatic naming of terms."""
        a = acl.ACL()
        a.terms.append(acl.Term())
        a.terms.append(acl.Term())
        a.terms.append(acl.Term(name='foo'))
        a.name_terms()
        self.assertNotEqual(a.terms[0].name, None)
        self.assertNotEqual(a.terms[0].name, a.terms[1].name)
        self.assertEqual(a.terms[2].name, 'foo')

    def testCommentStress(self):
        #'''Test pathological JunOS comments.'''
        '''Test pathological JunOS comments. We want this to error in order to pass.
        NO MULTI-LINE COMMENTS!!
        '''
        x = '''
filter 100 {
    /* one */  /* two */
    term/* */y {
        from /*{*/ /******/ {
            protocol tcp; /*
            */ destination-port 80/**/;
            /* tcp-established; */
        }
        /* /* /* */
    }
}'''
        self.assertRaises(exceptions.ParserSyntaxError, lambda: acl.parse(x))
        ###y = ['access-list 100 permit tcp any any eq 80']
        ###a = acl.parse(x)
        ###a.comments = a.terms[0].comments = []
        ###self.assertEqual(a.output_ios(), y)

    def testRanges(self):
        '''Test JunOS ICMP and protocol ranges (regression).'''
        x = '''
    filter 115j {
        term ICMP {
            from {
                protocol tcp-17;
                icmp-type [ echo-reply 10-11 ];
            }
            then {
                accept;
                count ICMP;
            }
        }
    }'''
        a = acl.parse(x)

    def testDoubleQuotes(self):
        '''Test JunOS double-quoted names (regression).'''
        x = '''\
filter test {
    term "awkward term name" {
        then {
            accept;
            count "awkward term name";
        }
    }
}'''
        a = acl.parse(x)
        self.assertEqual(a.terms[0].name, 'awkward term name')
        self.assertEqual('\n'.join(a.output_junos()), x)

    def testReplace(self):
        '''Test "firewall { replace:" addition.'''
        a = acl.ACL('test')
        self.assertEqual('\n'.join(a.output_junos(replace=True)), '''\
firewall {
replace:
    filter test {
    }
}''')

    def testNextTerm(self):
        '''Test "next term" action (regression).'''
        x = 'filter f { term t { then { next term; } } }'
        a = acl.parse(x)

    def testPolicer(self):
        '''test policer stuff.'''
        x = \
'''firewall {
replace:
    policer test {
        if-exceeding {
            bandwidth-limit 32000;
            burst-size-limit 32000;
        }
        then {
            discard;
        }
    }
    policer test2 {
        if-exceeding {
            bandwidth-limit 32000;
            burst-size-limit 32000;
        }
        then {
            discard;
        }
    }
}'''
        a = acl.parse(x)
        self.assertEqual(a.output(replace=True), x.split('\n'))
    
class CheckMiscIOS(unittest.TestCase):
    """Test misc. IOS-related ACL features"""
    def testICMPIOSNames(self):
        """Test stringification of ICMP types and codes into IOS format."""
        x = 'access-list 100 permit icmp 172.16.0.0 0.15.255.255 any 8'
        y = 'access-list 100 permit icmp 172.16.0.0 0.15.255.255 any echo'
        self.assertEqual(acl.parse(x).output_ios(), [y])
        self.assertEqual(acl.parse(y).output_ios(), [y])

    def testICMPRanges(self):
        """Test ICMP range conversions into IOS format."""
        types = [1, 111, 112, 113]
        t = acl.Term()
        t.match['protocol'] = ['icmp']
        t.match['icmp-type'] = types
        self.assertEqual(t.output_ios(),
                         map(lambda x: 'permit icmp any any %d' % x, types))

    def testCounterSuppression(self):
       """Test suppression of counters in IOS (since they are implicit)."""
       t = acl.Term()
       t.modifiers['count'] = 'xyz'
       t.output_ios()  # should not raise VendorSupportLacking

class CheckParseFile(unittest.TestCase):
    """Test ACL parsing from a file"""
    def testParseFile(self):
        """Make sure we can apply trigger.acl.parse() to file objects."""
        a = acl.parse(StringIO('access-list 100 deny ip any any'))
        self.assertEqual(a.name, '100')

class CheckTriggerIP(unittest.TestCase):
    """Test functionality of Trigger IP (TIP) objects."""
    def setUp(self):
        self.test_net = acl.TIP('1.2.3.0/24')

    def testRegular(self):
        """Test a normal IP object"""
        test = '1.2.3.4'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, False)
        self.assertEqual(obj.inactive, False)
        self.assertTrue(obj in self.test_net)

    def testNegated(self):
        """Test a negated IP object"""
        test = '1.2.3.4/32 except'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, True)
        self.assertEqual(obj.inactive, False)
        self.assertFalse(obj in self.test_net)

    def testInactive(self):
        """Test an inactive IP object"""
        test = 'inactive: 1.2.3.4/32'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, False)
        self.assertEqual(obj.inactive, True)
        # Until we fix inactive testing, this is legit
        self.assertTrue(obj in self.test_net)

    def testInactive(self):
        """Test an inactive IP object"""
        test = 'inactive: 1.2.3.4/32 except'
        obj = acl.TIP(test)
        self.assertEqual(str(obj), test)
        self.assertEqual(obj.negated, True)
        self.assertEqual(obj.inactive, True)
        # Inactive and negated is always negated
        self.assertFalse(obj in self.test_net)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_acl_db
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of `~trigger.acl.db` (aka ACLs.db)
"""

# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

# And now we can load the Trigger libs that call Redis
from trigger.netdevices import NetDevices
from trigger.acl.db import AclsDB
from trigger import exceptions
import unittest

# Globals
adb = AclsDB()
DEVICE_NAME = 'test1-abc.net.aol.com'
ACL_NAME = 'foo'

class TestAclsDB(unittest.TestCase):
    def setUp(self):
        self.nd = NetDevices()
        self.acl = ACL_NAME
        self.device = self.nd.find(DEVICE_NAME)
        self.implicit_acls = set(['115j', 'router-protect.core'])

    def test_01_add_acl_success(self):
        """Test associate ACL to device success"""
        exp = 'added acl %s to %s' % (self.acl, self.device)
        self.assertEqual(exp, adb.add_acl(self.device, self.acl))

    def test_02_add_acl_failure(self):
        """Test associate ACL to device failure"""
        exp = exceptions.ACLSetError
        self.assertRaises(exp, adb.add_acl, self.device, self.acl)

    def test_03_remove_acl_success(self):
        """Test remove ACL from device success"""
        exp = 'removed acl %s from %s' % (self.acl, self.device)
        self.assertEqual(exp, adb.remove_acl(self.device, self.acl))

    def test_04_remove_acl_failure(self):
        """Test remove ACL from device failure"""
        exp = exceptions.ACLSetError
        self.assertRaises(exp, adb.remove_acl, self.device, self.acl)

    def test_05_get_acl_dict(self):
        """Test get dict of associations"""
        exp = {'all': self.implicit_acls, 'explicit': set(),
               'implicit': self.implicit_acls}
        self.assertEqual(exp, adb.get_acl_dict(self.device))

    def test_06_get_acl_set_success(self):
        """Test get set of associations success"""
        exp = self.implicit_acls
        self.assertEqual(exp, adb.get_acl_set(self.device))

    def test_07_get_acl_set_failure(self):
        """Test get set of associations failure"""
        exp = exceptions.InvalidACLSet
        acl_set = 'bogus'
        self.assertRaises(exp, adb.get_acl_set, self.device, acl_set)

    def tearDown(self):
        NetDevices._Singleton = None

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_acl_queue
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of `~trigger.acl.queue` (aka task queue)

Only tests SQLite for now.
"""

import datetime
import os
import tempfile
from trigger.conf import settings

# Override the DB file we're going to use.
_, db_file = tempfile.mkstemp('.db')
settings.DATABASE_NAME = db_file

# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

# Now we can import from Trigger
from trigger.acl import queue
from trigger.acl.models import create_tables
from trigger.acl.db import AclsDB
from trigger.netdevices import NetDevices
from trigger.utils import get_user
from trigger import exceptions
import unittest

# Globals
DEVICE_NAME = 'test1-abc.net.aol.com'
ACL_NAME = 'foo'
USERNAME = get_user()

# Setup
create_tables()
adb = AclsDB()
nd = NetDevices()
# These must happen after we populate the dummy AclsDB

def _setup_aclsdb(nd, device_name=DEVICE_NAME, acl=ACL_NAME):
    """Add an explicit ACL to the dummy AclsDB"""
    #print 'Setting up ACLsdb: %s => %s' % (acl, device_name)
    dev = nd.find(device_name)
    if acl not in dev.acls:
        adb.add_acl(dev, acl)
    NetDevices._Singleton = None
    nd = NetDevices()

class TestAclQueue(unittest.TestCase):
    def setUp(self):
        self.nd = NetDevices()
        _setup_aclsdb(self.nd)
        self.q = queue.Queue(verbose=False)
        self.acl = ACL_NAME
        self.acl_list = [self.acl]
        self.device = self.nd.find(DEVICE_NAME)
        self.device_name = DEVICE_NAME
        self.device_list = [self.device_name]
        self.user = USERNAME

    #
    # Integrated queue tests
    #

    def test_01_insert_integrated_success(self):
        """Test insert success into integrated queue"""
        self.assertTrue(self.q.insert(self.acl, self.device_list) is None)

    def test_02_insert_integrated_failure_device(self):
        """Test insert invalid device"""
        self.assertRaises(exceptions.TriggerError, self.q.insert, self.acl, ['bogus'])

    def test_03_insert_integrated_failure_acl(self):
        """Test insert devices w/ no ACL association"""
        self.assertRaises(exceptions.TriggerError, self.q.insert, 'bogus',
                          self.device_list)

    def test_04_list_integrated_success(self):
        """Test listing integrated queue"""
        self.q.insert(self.acl, self.device_list)
        expected = [(u'test1-abc.net.aol.com', u'foo')]
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_05_complete_integrated(self):
        """Test mark task complete"""
        self.q.complete(self.device_name, self.acl_list)
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_06_delete_integrated_with_devices(self):
        """Test delete ACL from queue providing devices"""
        self.q.insert(self.acl, self.device_list)
        self.assertTrue(self.q.delete(self.acl, self.device_list))

    def test_07_delete_integrated_no_devices(self):
        """Test delete ACL from queue without providing devices"""
        self.q.insert(self.acl, self.device_list)
        self.assertTrue(self.q.delete(self.acl))

    def test_08_remove_integrated_success(self):
        """Test remove (set as loaded) ACL from integrated queue"""
        self.q.insert(self.acl, self.device_list)
        self.q.remove(self.acl, self.device_list)
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list()))

    def test_10_remove_integrated_failure(self):
        """Test remove (set as loaded) failure"""
        self.assertRaises(exceptions.ACLQueueError, self.q.remove, '', self.device_list)

    #
    # Manual queue tests
    #

    def test_11_insert_manual_success(self):
        """Test insert success into manual queue"""
        self.assertTrue(self.q.insert('manual task', None) is None)

    def test_12_list_manual_success(self):
        """Test list success of manual queue"""
        self.q.insert('manual task', None)
        expected = ('manual task', self.user)
        result = self.q.list('manual')
        actual = result[0][:2] # First tuple, items 0-1
        self.assertEqual(sorted(expected), sorted(actual))

    def test_13_delete_manual_success(self):
        """Test delete from manual queue"""
        self.q.delete('manual task')
        expected = []
        self.assertEqual(sorted(expected), sorted(self.q.list('manual')))

    #
    # Generic tests
    #

    def test_14_delete_failure(self):
        """Test delete of task not in queue"""
        self.assertFalse(self.q.delete('bogus'))

    def test_15_list_invalid(self):
        """Test list of invalid queue name"""
        self.assertFalse(self.q.list('bogus'))

    # Teardown

    def test_ZZ_cleanup_db(self):
        """Cleanup the temp database file"""
        self.assertTrue(os.remove(db_file) is None)

    def tearDown(self):
        NetDevices._Singleton = None

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_changemgmt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for bounce windows and the stuff that goes with them.
"""

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__copyright__ = 'Copyright 2013 Salesforce.com'
__version__ = '2.0'


# Make sure we load the mock redis library
from utils import mock_redis
mock_redis.install()

from datetime import datetime
from pytz import timezone, UTC
from trigger.changemgmt import BounceStatus, BounceWindow
from trigger.netdevices import NetDevices
import unittest


# Globals
EST = timezone('US/Eastern')
PST = timezone('US/Pacific')


class CheckBounceStatus(unittest.TestCase):
    def setUp(self):
        self.red = BounceStatus('red')
        self.green = BounceStatus('green')
        self.yellow = BounceStatus('yellow')

    def testComparison(self):
        """Test comparison of BounceStatus against BounceStatus."""
        self.assert_(self.red > self.yellow > self.green)
        self.assert_(self.red == self.red == BounceStatus('red'))
        self.assertNotEquals(self.red, self.yellow)

    def testString(self):
        """Test BounceStatus stringfication and string comparison."""
        self.assertEquals(str(self.red), 'red')
        self.assertEquals(self.red, 'red')
        self.assert_('red' > self.yellow > 'green')

class CheckBounceWindow(unittest.TestCase):
    def setUp(self):
        self.est = BounceWindow(green='5-7', yellow='8-11')
        self.pst = BounceWindow(green='2-4', yellow='5-7')

    def testStatus(self):
        """Test lookup of bounce window status."""
        # 00:00 UTC, 19:00 EST
        when = datetime(2006, 1, 3, tzinfo=UTC)
        self.assertEquals(self.est.status(when), 'red')
        # 06:00 PST, 14:00 UTC
        then = datetime(2013, 6, 3, tzinfo=PST)
        self.assertEquals(self.pst.status(then), 'green')

    def testNextOk(self):
        """Test bounce window next_ok() method."""
        when = datetime(2013, 1, 3, 22, 15, tzinfo=UTC)
        next_ok = self.pst.next_ok('yellow', when)
        # Did we get the right answer?  (2 am PST the next morning)
        self.assertEquals(next_ok.tzinfo, UTC)
        self.assertEquals(next_ok.astimezone(EST).hour, 2)
        self.assertEquals(next_ok, datetime(2013, 1, 4, 7, 0, tzinfo=UTC))
        self.assertEquals(self.pst.status(next_ok), 'green')
        # next_ok() should return current time if already ok.
        self.assertEquals(self.pst.next_ok('yellow', next_ok), next_ok)
        then = datetime(2013, 1, 3, 22, 15, tzinfo=UTC)
        self.assertEquals(self.pst.next_ok('red', then), then)

class CheckWeekend(unittest.TestCase):
    def testWeekend(self):
        """Test weekend moratorium."""
        when = datetime(2006, 1, 6, 20, tzinfo=UTC)
        next_ok = BounceWindow(green='5-7', yellow='8-11').next_ok('green', when)
        self.assertEquals(next_ok, datetime(2006, 1, 9, 10, tzinfo=UTC))

class CheckNetDevices(unittest.TestCase):
    def setUp(self):
        self.router = NetDevices()['test1-abc.net.aol.com']
        self.when = datetime(2006, 7, 24, 20, tzinfo=UTC)

    def testNetDevicesBounce(self):
        """Test integration of bounce windows with NetDevices."""
        self.assertEquals(self.router.bounce.status(self.when), 'red')

    def testAllowability(self):
        """Test allowability checks."""
        self.failIf(self.router.allowable('load-acl', self.when))
        morning = datetime(2006, 7, 25, 9, tzinfo=UTC)        # 5 am EDT
        self.assert_(self.router.allowable('load-acl', morning))
        self.assertEquals(self.router.next_ok('load-acl', self.when), morning)
        self.assertEquals(self.router.next_ok('load-acl', morning), morning)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_except
# a test for except processing
import sys, os
sys.path.append(os.path.realpath(
        os.path.join(os.path.dirname(__file__),'..')))
from trigger import acl

PARSIT = '''
filter fire1 {
    term 1 {
        from {
            source-address {
                192.168.5.0/24 except;
                192.168.6.0/24;
            }
        }
        then {
            count reject-pref1-1;
            log;
            reject;
        }
    }
    term 2 {
        then {
            count reject-pref1-2;
            log;
            accept;
        }
    }
}
'''
y = acl.parse(PARSIT)
print y.terms[0].match
print '\n'.join(acl.parse(PARSIT).output_junos())
# following should fail
#print '\n'.join(acl.parse(PARSIT).output_ios())

########NEW FILE########
__FILENAME__ = test_netdevices
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the functionality of NetDevice, NetDevices, and Vendor objects.

This uses the mockups of netdevices.xml, acls.db, and autoacls.py in
tests/data.
"""

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0'

import os
import unittest

# Make sure we load the mock redis library
from utils import captured_output
from utils import mock_redis
mock_redis.install()

# Now we can import from Trigger
from trigger.netdevices import NetDevices, NetDevice, Vendor
from trigger import changemgmt


# Constants
DEVICE_NAME = 'test1-abc.net.aol.com'
NETDEVICE_DUMP_EXPECTED = \
'\n\tHostname:          test1-abc.net.aol.com\n\tOwning Org.:       12345678 - Network Engineering\n\tOwning Team:       Data Center\n\tOnCall Team:       Data Center\n\n\tVendor:            Juniper (JUNIPER)\n\tMake:              M40 INTERNET BACKBONE ROUTER\n\tModel:             M40-B-AC\n\tType:              ROUTER\n\tLocation:          LAB CR10 16ZZ\n\n\tProject:           Test Lab\n\tSerial:            987654321\n\tAsset Tag:         0000012345\n\tBudget Code:       1234578 (Data Center)\n\n\tAdmin Status:      PRODUCTION\n\tLifecycle Status:  INSTALLED\n\tOperation Status:  MONITORED\n\tLast Updated:      2010-07-19 19:56:32.0\n\n'


def _reset_netdevices():
    """Reset the Singleton state of NetDevices class."""
    NetDevices._Singleton = None


class TestNetDevicesWithAcls(unittest.TestCase):
    """
    Test NetDevices with ``settings.WITH_ACLs set`` to ``True``.
    """
    def setUp(self):
        self.nd = NetDevices()
        self.nodename = self.nd.keys()[0]
        self.device = self.nd.values()[0]
        self.device.explicit_acls = set(['test1-abc-only'])

    def test_basics(self):
        """Basic test of NetDevices functionality."""
        self.assertEqual(len(self.nd), 1)
        self.assertEqual(self.device.nodeName, self.nodename)
        self.assertEqual(self.device.manufacturer, 'JUNIPER')

    def test_aclsdb(self):
        """Test acls.db handling."""
        self.assertTrue('test1-abc-only' in self.device.explicit_acls)

    def test_autoacls(self):
        """Test autoacls.py handling."""
        self.assertTrue('router-protect.core' in self.device.implicit_acls)

    def test_find(self):
        """Test the find() method."""
        self.assertEqual(self.nd.find(self.nodename), self.device)
        nodebasename = self.nodename[:self.nodename.index('.')]
        self.assertEqual(self.nd.find(nodebasename), self.device)
        self.assertRaises(KeyError, lambda: self.nd.find(self.nodename[0:3]))

    def test_all(self):
        """Test the all() method."""
        expected = [self.device]
        self.assertEqual(expected, self.nd.all())

    def test_search(self):
        """Test the search() method."""
        expected = [self.device]
        self.assertEqual(expected, self.nd.search(self.nodename))
        self.assertEqual(expected, self.nd.search('17', field='onCallID'))
        self.assertEqual(expected, self.nd.search('juniper', field='vendor'))

    def test_match(self):
        """Test the match() method."""
        expected = [self.device]
        self.assertEqual(expected, self.nd.match(nodename=self.nodename))
        self.assertEqual(expected, self.nd.match(vendor='juniper'))
        self.assertNotEqual(expected, self.nd.match(vendor='cisco'))

    def tearDown(self):
        NetDevices._Singleton = None

class TestNetDevicesWithoutAcls(unittest.TestCase):
    """
    Test NetDevices with ``settings.WITH_ACLs`` set to ``False``.
    """
    def setUp(self):
        self.nd = NetDevices(with_acls=False)
        self.nodename = self.nd.keys()[0]
        self.device = self.nd.values()[0]

    def test_aclsdb(self):
        """Test acls.db handling."""
        self.assertFalse('test1-abc-only' in self.device.explicit_acls)

    def test_autoacls(self):
        """Test autoacls.py handling."""
        expected = set()
        self.assertEqual(expected, self.device.implicit_acls)

    def tearDown(self):
        _reset_netdevices()

class TestNetDeviceObject(unittest.TestCase):
    """
    Test NetDevice object methods.
    """
    def setUp(self):
        self.nd = NetDevices()
        self.nodename = self.nd.keys()[0]
        self.device = self.nd.values()[0]

    def test_stringify(self):
        """Test casting NetDevice to string"""
        expected = DEVICE_NAME
        self.assertEqual(expected, str(self.device))

    def test_bounce(self):
        """Test .bounce property"""
        expected = changemgmt.BounceWindow
        self.assertTrue(isinstance(self.device.bounce, expected))

    def test_shortName(self):
        """Test .shortName property"""
        expected = self.nodename.split('.', 1)[0]
        self.assertEqual(expected, self.device.shortName)

    def test_allowable(self):
        """Test allowable() method"""
        # This is already tested in test_changemgmt.py, so this is a stub.
        pass

    def test_next_ok(self):
        """Test next_ok() method"""
        # This is already tested in test_changemgmt.py, so this is a stub.
        pass

    def test_identity(self):
        """Exercise NetDevice identity tests."""
        # It's a router...
        self.assertTrue(self.device.is_router())
        # And therefore none of these other things...
        self.assertFalse(self.device.is_switch())
        self.assertFalse(self.device.is_firewall())
        self.assertFalse(self.device.is_netscaler())
        self.assertFalse(self.device.is_netscreen())
        self.assertFalse(self.device.is_ioslike())
        self.assertFalse(self.device.is_brocade_vdx())

    def test_hash_ssh(self):
        """Exercise NetDevice ssh test."""
        # TODO (jathan): Mock SSH connections so we can test actual connectivity
        # Device won't be reachable, so this should always fail
        self.assertFalse(self.device.has_ssh())
        # Since there's no SSH, no aync
        self.assertFalse(self.device.can_ssh_pty())

    def test_reachability(self):
        """Exercise NetDevice ssh test."""
        # TODO (jathan): Mock SSH connections so we can test actual connectivity
        self.assertFalse(self.device.is_reachable())

    def test_dump(self):
        """Test the dump() method."""
        with captured_output() as (out, err):
            self.device.dump()
        expected = NETDEVICE_DUMP_EXPECTED
        output = out.getvalue()
        self.assertEqual(expected, output)

    def tearDown(self):
        _reset_netdevices()

class TestVendorObject(unittest.TestCase):
    """Test Vendor object"""
    def setUp(self):
        self.mfr = 'CISCO SYSTEMS'
        self.vendor = Vendor(self.mfr)

    def test_creation(self):
        """Test creation of a Vendor instance"""
        expected = 'cisco'
        self.assertEqual(expected, self.vendor)

    def test_string_operations(self):
        """Test string output and comparison behaviors"""
        # String comparisons
        expected = 'cisco'
        self.assertEqual(expected, self.vendor.normalized)
        self.assertEqual(expected, str(self.vendor))
        self.assertEqual(expected, Vendor(expected))
        # Title casing
        expected = 'Cisco'
        self.assertEqual(expected, self.vendor.title)
        self.assertEqual(expected.lower(), self.vendor.lower())
        # Mfr equates to object
        self.assertEqual(self.mfr, self.vendor)

    def test_membership(self):
        """Test membership w/ __eq__ and __contains__"""
        expected = 'cisco'
        self.assertTrue(expected in [self.vendor])
        self.assertTrue(self.vendor in [self.vendor])
        self.assertTrue(self.vendor in [expected])
        self.assertFalse(self.vendor in ['juniper', 'foundry'])

    def test_determine_vendor(self):
        """Test determine_vendor() method"""
        expected = 'cisco'
        self.assertEqual(expected, self.vendor.determine_vendor(self.mfr))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scripts
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tests/scripts.py

__author__ = 'Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.'
__version__ = '1.1'

import os
import unittest

ACLCONV = 'bin/aclconv'

os.environ['PYTHONPATH'] = os.getcwd()

# TODO (jathan): Add tests for all the scripts!!

class Aclconv(unittest.TestCase):
    # This should be expanded.
    def testI2J(self):
        """Convert IOS to JunOS."""
        child_in, child_out = os.popen2(ACLCONV + ' -j -')
        child_in.write('access-list 100 deny ip any any')
        self.assertEqual(child_in.close(), None)
        correct_output = '''\
firewall {
replace:
    filter 100j {
        term T1 {
            then {
                reject;
                count T1;
            }
        }
    }
}
'''
        self.assertEqual(child_out.read(), correct_output)
        self.assertEqual(child_out.close(), None)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tacacsrc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Jathan McCollum, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__copyright__ = 'Copyright 2005-2011 AOL Inc.; 2013 Salesforce.com'
__version__ = '2.0.1'


from StringIO import StringIO
import os
import unittest
import tempfile
from mock import patch
from trigger.conf import settings
from trigger.tacacsrc import Tacacsrc, Credentials


# Constants
aol = Credentials('jschmoe', 'abc123', 'aol')
AOL_TACACSRC = {
    'aol_uname_': 'jschmoe',
    'aol_pwd_': 'abc123',
}
RIGHT_PERMS = '0600'

MEDIUMPWCREDS = Credentials('MEDIUMPWCREDS', 'MEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUM', 'MEDIUMPWCREDS')
MEDIUMPW_TACACSRC = {
  'MEDIUMPWCREDS_uname_': 'MEDIUMPWCREDS',
  'MEDIUMPWCREDS_pwd_': 'MEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUMMEDIUM',
} 

LONGPWCREDS = Credentials('LONGPWCREDS', 'LONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONG', 'LONGPWCREDS')
LONGPW_TACACSRC = {
   'LONGPWCREDS_uname_': 'LONGPWCREDS',
   'LONGPWCREDS_pwd_': 'LONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONG',
}

EMPTYPWCREDS = Credentials('EMPTYPWCREDS', '', 'EMPTYPWCREDS')
EMPTYPW_TACACSRC = {
   'EMPTYPWCREDS_uname_': 'EMPTYPWCREDS',
   'EMPTYPWCREDS_pwd_': '',
}

LIST_OF_CREDS = ['aol', 'MEDIUMPWCREDS', 'LONGPWCREDS', ]  
LIST_OF_TACACSRC = [ AOL_TACACSRC, MEDIUMPW_TACACSRC, LONGPW_TACACSRC ]  
ALL_CREDS = [ (name,eval(name)) for name in LIST_OF_CREDS] 
ALL_TACACSRC = dict() 
[ALL_TACACSRC.update(x) for x in LIST_OF_TACACSRC]

def miniparser(data, tcrc):
    """Manually parse .tacacsrc lines into a dict"""
    lines = [line.strip() for line in data]
    lines = [line for line in lines if line and not line.startswith('#')]
    ret = {}
    for line in lines:
        k, _, v = line.partition(' = ')
        ret[k] = tcrc._decrypt_old(v)
    return ret

class Testing_Tacacsrc(Tacacsrc):
    def _get_key_nonce_old(self):
        '''Dependency injection'''
        return 'jschmoe\n'

class TacacsrcTest(unittest.TestCase):
    def testRead(self):
        """Test reading .tacacsrc."""
        t = Testing_Tacacsrc()
        for name,value in ALL_CREDS:
          self.assertEqual(t.version, '2.0')
          self.assertEqual(t.creds['%s' % name], value)

    def _get_perms(self, filename):
        """Get octal permissions for a filename"""
        # We only want the lower 4 bits (negative index)
        return oct(os.stat(filename).st_mode)[-4:]

    def testWrite(self):
        """Test writing .tacacsrc."""
        _, file_name = tempfile.mkstemp('_tacacsrc')
        t = Testing_Tacacsrc(generate_new=False)

        for name,value in ALL_CREDS:
          t.creds['%s' % name] = value
        # Overload the default file_name w/ our temp file or
        # create a new tacacsrc by setting file_name to 'tests/data/tacacsrc'
          t.file_name = file_name 
          t.write()

        # Read the file we wrote back in and check it against what we think it
        # should look like.
        self.maxDiff = None 
        output = miniparser(t._read_file_old(), t)
        self.assertEqual(output, ALL_TACACSRC) 

        # And then compare it against the manually parsed value using
        # miniparser()
        with open(settings.TACACSRC, 'r') as fd:
            lines = fd.readlines()
            self.assertEqual(output, miniparser(lines, t))
        os.remove(file_name)

    def test_brokenpw(self):
        self.assertRaises(ValueError, Testing_Tacacsrc, tacacsrc_file='tests/data/brokenpw_tacacsrc') 

    def test_emptypw(self):
        devnull = open(os.devnull, 'w')
        with patch('trigger.tacacsrc.prompt_credentials', side_effect=KeyError): 
          with patch('sys.stdout', devnull):
            self.assertRaises(KeyError, Testing_Tacacsrc, tacacsrc_file='tests/data/emptypw_tacacsrc') 

    def test_perms(self):
        """Test that permissions are being enforced."""
        t = Testing_Tacacsrc()
        fname = t.file_name
        # First make sure perms are set
        old_perms = self._get_perms(fname)
        self.assertEqual(old_perms, RIGHT_PERMS)
        os.chmod(fname, 0666) # Make it world-writable
        new_perms = self._get_perms(fname)
        self.assertNotEqual(new_perms, RIGHT_PERMS)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = misc
# -*- coding: utf-8 -*-

"""
Misc. utils for testing.
"""

from contextlib import contextmanager
from StringIO import StringIO
import sys

__all__ = ('captured_output',)

@contextmanager
def captured_output():
    """
    A context manager to capture output from things that print so you can
    compare them!

    Use it like this::

        with captured_output() as (out, err):
            foo()
        # This can go inside or outside the `with` block
        output = out.getvalue().strip()
        self.assertEqual(output, 'hello world!')

    Credit: Rob Kennedy
    Source: http://stackoverflow.com/a/17981937/194311
    """
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

########NEW FILE########
__FILENAME__ = mock_redis
# -*- coding: utf-8 -*-

"""
A mock py-redis (Redis) object for use in offline testing.

Licensed from John DeRosa, Source: http://bit.ly/19Lmnxx
Modified for Trigger by Jathan McCollum
"""
__all__ = ('Redis', 'MockRedis', 'install')


from collections import defaultdict
import re
import sys

class MockRedisLock(object):
    """
    Poorly imitate a Redis lock object so unit tests can run on our Hudson CI
    server without needing a real Redis server.
    """
    def __init__(self, redis, name, timeout=None, sleep=0.1):
        """Initialize the object."""
        self.redis = redis
        self.name = name
        self.acquired_until = None
        self.timeout = timeout
        self.sleep = sleep

    def acquire(self, blocking=True):  # pylint: disable=R0201,W0613
        """Emulate acquire."""
        return True

    def release(self):   # pylint: disable=R0201
        """Emulate release."""
        return None

class MockRedisPipeline(object):
    """
    Imitate a redis-python pipeline object so unit tests can run on our Hudson
    CI server without needing a real Redis server.
    """
    def __init__(self, redis):
        """Initialize the object."""
        self.redis = redis

    def execute(self):
        """
        Emulate the execute method. All piped commands are executed immediately
        in this mock, so this is a no-op.
        """
        pass

    def delete(self, key):
        """Emulate a pipelined delete."""

        # Call the MockRedis' delete method
        self.redis.delete(key)
        return self

    def srem(self, key, member):
        """Emulate a pipelined simple srem."""
        self.redis.redis[key].discard(member)
        return self

class MockRedis(object):
    """
    Imitate a Redis object so unit tests can run on our Hudson CI server without
    needing a real Redis server.
    """
    # The 'Redis' store
    redis = defaultdict(dict)

    def __init__(self):
        """Initialize the object."""
        pass

    def delete(self, key):  # pylint: disable=R0201
        """Emulate delete."""
        if key in MockRedis.redis:
            del MockRedis.redis[key]

    def exists(self, key):  # pylint: disable=R0201
        """Emulate get."""
        return key in MockRedis.redis

    def get(self, key):  # pylint: disable=R0201
        """Emulate get."""
        # Override the default dict
        result = '' if key not in MockRedis.redis else MockRedis.redis[key]
        return result

    def hget(self, hashkey, attribute):  # pylint: disable=R0201
        """Emulate hget."""
        # Return '' if the attribute does not exist
        result = MockRedis.redis[hashkey].get(attribute, '')
        return result

    def hgetall(self, hashkey):  # pylint: disable=R0201
        """Emulate hgetall."""
        return MockRedis.redis[hashkey]

    def hlen(self, hashkey):  # pylint: disable=R0201
        """Emulate hlen."""
        return len(MockRedis.redis[hashkey])

    def hmset(self, hashkey, value):  # pylint: disable=R0201
        """Emulate hmset."""
        # Iterate over every key:value in the value argument.
        for attributekey, attributevalue in value.items():
            MockRedis.redis[hashkey][attributekey] = attributevalue

    def hset(self, hashkey, attribute, value):  # pylint: disable=R0201
        """Emulate hset."""
        MockRedis.redis[hashkey][attribute] = value

    def keys(self, pattern):  # pylint: disable=R0201
        """Emulate keys."""

        # Make a regex out of pattern. The only special matching character we look for is '*'
        regex = '^' + pattern.replace('*', '.*') + '$'

        # Find every key that matches the pattern
        result = [key for key in MockRedis.redis.keys() if re.match(regex, key)]

        return result

    def lock(self, key, timeout=0, sleep=0):  # pylint: disable=W0613
        """Emulate lock."""
        return MockRedisLock(self, key)

    def pipeline(self):
        """Emulate a redis-python pipeline."""
        return MockRedisPipeline(self)

    def sadd(self, key, value):  # pylint: disable=R0201
        """Emulate sadd."""
        # Does the set at this key already exist?
        if key in MockRedis.redis:
            # Yes, add this to the set
            if value in MockRedis.redis[key]:
                return False
            MockRedis.redis[key].add(value)
        else:
            # No, override the defaultdict's default and create the set
            MockRedis.redis[key] = set([value])
        return True

    def srem(self, key, value):
        """Emulate srem."""
        # Does the set at this key already exist?
        if key in MockRedis.redis:
            # Yes, remove it from the set
            if value in MockRedis.redis[key]:
                MockRedis.redis[key].discard(value)
                return True
        return False

    def smembers(self, key):  # pylint: disable=R0201
        """Emulate smembers."""
        return MockRedis.redis[key]

    def save(self):
        """Emulate save"""
        return True

class Redis(MockRedis):
    """Redis object that supports kwargs"""
    def __init__(self, **kwargs):
        super(Redis, self).__init__()
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

def install():
    """Install into sys.modules as the Redis module"""
    for mod in ('redis', 'utils.mock_redis'):
        sys.modules.pop(mod, None)
    __import__('utils.mock_redis')
    sys.modules['redis'] = sys.modules['utils.mock_redis']

########NEW FILE########
__FILENAME__ = convert_tacacsrc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Converts old .tacacsrc to new .tacacsrc.gpg.

from trigger.tacacsrc import convert_tacacsrc

if __name__ == '__main__':
    convert_tacacsrc()

########NEW FILE########
__FILENAME__ = gen_tacacsrc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
gen_tacacsrc.py - Simple, stupid tool that creates a .tacacsrc if is not found.
"""

__author__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2011, AOL Inc.'
__version__ = '1.9'

from trigger.tacacsrc import *

t = Tacacsrc()
if hasattr(t, 'rawdata'):
    print 'You already have %s, bye!' % t.file_name
else:
    print '\nWrote %s!' % t.file_name

########NEW FILE########
__FILENAME__ = nd2json
#!/usr/bin/env python

# nd2json.py - Converts netdevices.xml to netdevices.json and reports
# performance stuff

from xml.etree.cElementTree import ElementTree, parse
try:
    import simplejson as json
except ImportError:
    import json
import sys
import time


if len(sys.argv) < 2:
    sys.exit("usage: %s </path/to/netdevices.xml>" % sys.argv[0])
else:
    ndfile = sys.argv[1]

print # Parse XML
print 'Parsing XML', ndfile
start = time.time()
nodes = parse(ndfile).findall('device')
print 'Done:', time.time() - start, 'seconds.'
devices = []

print # Convert to Python structure

print 'Converting to Python structure.'
start = time.time()
for node in nodes:
    dev = {}
    for e in node.getchildren():
        dev[e.tag] = e.text
    devices.append(dev)
print 'Done:', time.time() - start, 'seconds.'

print # Convert to JSON

'''
print 'Dumping to JSON...'
start = time.time()
jsondata = json.dumps(devices)
print 'Done:', time.time() - start, 'seconds.'
'''

print # Writing to file

outfile = 'netdevices.json'
with open(outfile, 'wb') as f:
    print 'Writing to disk...'
    start = time.time()
    json.dump(devices, f, ensure_ascii=False, check_circular=False, indent=4)
    #json.dump(devices, f, ensure_ascii=False, check_circular=False)
    #f.write(jsondata)
    print 'Done:', time.time() - start, 'seconds.'
    #print 'Wrote {0} bytes to {1}'.format(len(jsondata), outfile)

print # Reading from file

with open(outfile, 'rb') as g:
    print 'Reading from disk...'
    start = time.time()
    jsondata = json.load(g)
    print 'Done:', time.time() - start, 'seconds.'

########NEW FILE########
__FILENAME__ = nd2sqlite
#!/usr/bin/env python

# nd2sqlite.py - Converts netdevices.xml into a SQLite database and also prints
# some performance stuff

from xml.etree.cElementTree import ElementTree, parse
try:
    import simplejson as json
except ImportError:
    import json
import time
import sys
import sqlite3 as sqlite

if len(sys.argv) < 3:
    sys.exit("usage: %s </path/to/netdevices.xml> </path/to/sqlite-db-file>" % sys.argv[0])
else:
    ndfile = sys.argv[1]
    sqlitefile = sys.argv[2]

print # Parse XML
print 'Parsing XML', ndfile
start = time.time()
nodes = parse(ndfile).findall('device')
print 'Done:', time.time() - start, 'seconds.'
#devices = []

connection = sqlite.connect(sqlitefile)
cursor = connection.cursor()

print # Convert to Python structure

print 'Inserting into sqlite...'
start = time.time()
for node in nodes:
    keys = []
    vals = []
    for e in node.getchildren():
        keys.append(e.tag)
        vals.append(e.text)
    keystr = ', '.join(keys)
    valstr = ','.join('?' * len(vals))
    #sql = ''' INSERT INTO netdevices ( {0}) VALUES ( {1}); '''.format(keystr, valstr)
    sql = '''INSERT INTO netdevices ( {0} ) VALUES ( {1} )'''.format(keystr, valstr)
    cursor.execute(sql, vals)

connection.commit()

"""
colfetch  = cursor.execute('pragma table_info(netdevices)')
results = colfetch.fetchall()
columns = [r[1] for r in results]
devfetch = cursor.execute('select * from netdevices')
devrows = devfetch.fetchall()

for row in devrows:
    data = zip(columns, row)
    print data
"""

cursor.close()
connection.close()
print 'Done:', time.time() - start, 'seconds.'

########NEW FILE########
__FILENAME__ = tacacsrc2gpg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
tacacsrc2gpg.py - Converts clear-text .tacacsrc to GPG-encrypted .tacacsrc.gpg

Intended for use when migrating from clear-text .tacacsrc to GPG.
"""

import os
import pwd
import socket
import sys

from trigger.tacacsrc import Tacacsrc, get_device_password, convert_tacacsrc
from trigger.utils.cli import yesno

prompt = 'This will overwrite your .tacacsrc.gpg and all gnupg configuration, are you sure?'
if not yesno(prompt):
    sys.exit(1)

(username, err, uid, gid, name, homedir, shell) = pwd.getpwuid(os.getuid())

print '''
======== [ READ ME READ ME READ ME READ ME ] ================
The following settings must be configured:

Real name: %s
Email Address: %s@%s
Comment: First Last
=============================================================
''' % (username, username, socket.getfqdn())

os.system('gpg --gen-key')

prompt2 = 'Would you like to convert your OLD tacacsrc configuration file to your new one?'
if yesno(prompt2) and os.path.isfile(os.path.join(homedir, '.tacacsrc')):
    convert_tacacsrc()
else:
    print "Old tacacsrc not converted."
    get_device_password()

########NEW FILE########
__FILENAME__ = autoacl
# -*- coding: utf-8 -*-

"""
This module controls when ACLs get auto-applied to network devices,
in addition to what is specified in acls.db. 

This is primarily used by :class:`~trigger.acl.db.AclsDB` to populate the
**implicit** ACL-to-device mappings.

No changes should be made to this module. You must specify the path to the
autoacl logic inside of ``settings.py`` as ``AUTOACL_FILE``. This will be
exported as ``autoacl`` so that the module path for the :func:`autoacl()`
function will still be :func:`trigger.autoacl.autoacl`.

This trickery allows us to keep the business-logic for how ACLs are mapped to
devices out of the Trigger packaging.

If you do not specify a location for ``AUTOACL_FILE`` or the module cannot be
loaded, then a default :func:`autoacl()` function ill be used.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.'

from trigger.conf import settings
from trigger.utils.importlib import import_module_from_path
from twisted.python import log
import warnings

__all__ = ('autoacl',)

module_path = settings.AUTOACL_FILE


# In either case we're exporting a single name: autoacl().
try:
    # Placeholder for the custom autoacl module that will provide the autoacl()
    # function. Either of these operations will raise an ImportError if they
    # don't work, so it's safe to have them within the same try statement.
    _autoacl_module = import_module_from_path(module_path, '_autoacl_module')
    log.msg('Loading autoacl() from %s' % module_path)
    from _autoacl_module import autoacl
except ImportError:
    msg = 'Function autoacl() could not be found in %s, using default!' % module_path
    warnings.warn(msg, RuntimeWarning)
    def autoacl(dev, explicit_acls=None):
        """
        Given a NetDevice object, returns a set of **implicit** (auto) ACLs. We
        require a device object so that we don't have circular dependencies
        between netdevices and autoacl.

        This function MUST return a ``set()`` of acl names or you will break
        the ACL associations. An empty set is fine, but it must be a set!

        :param dev: A :class:`~trigger.netdevices.NetDevice` object.
        :param explicit_acls: A set containing names of ACLs. Default: set()

        >>> dev = nd.find('test1-abc')
        >>> dev.vendor
        <Vendor: Juniper>
        >>> autoacl(dev)
        set(['juniper-router-protect', 'juniper-router.policer'])

        NOTE: If the default function is returned it does nothing with the
        arguments and always returns an empty set.
        """
        return set()

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-

"""
Redis-based replacement of the legacy acls.db file. This is used for
interfacing with the explicit and automatic ACL-to-device mappings.

>>> from trigger.netdevices import NetDevices
>>> from trigger.acl.db import AclsDB
>>> nd = NetDevices()
>>> dev = nd.find('test1-abc')
>>> a = AclsDB()
>>> a.get_acl_set(dev)
set(['juniper-router.policer', 'juniper-router-protect', 'abc123'])
>>> a.get_acl_set(dev, 'explicit')
set(['abc123'])
>>> a.get_acl_set(dev, 'implicit')
set(['juniper-router.policer', 'juniper-router-protect'])
>>> a.get_acl_dict(dev)
{'all': set(['abc123', 'juniper-router-protect', 'juniper-router.policer']),
 'explicit': set(['abc123']),
  'implicit': set(['juniper-router-protect', 'juniper-router.policer'])}
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2010-2012, AOL Inc.; 2013 Salesforce.com'

from collections import defaultdict
import redis
import sys

from twisted.python import log
from trigger.acl.autoacl import autoacl
from trigger import exceptions
from trigger.conf import settings


ACLSDB_BACKUP = './acls.csv'
DEBUG = False

# The redis instance. It doesn't care if it can't reach Redis until you actually
# try to talk to Redis.
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                db=settings.REDIS_DB)

# Exports
__all__ = (
    # functions
    'get_matching_acls',
    'get_all_acls',
    'get_bulk_acls',
    'populate_bulk_acls',

    # classes
    'AclsDB',
)


# Classes
class AclsDB(object):
    """
    Container for ACL operations.

    add/remove operations are for explicit associations only.
    """
    def __init__(self):
        self.redis = r
        log.msg('ACLs database client initialized')

    def add_acl(self, device, acl):
        """
        Add explicit acl to device

        >>> dev = nd.find('test1-mtc')
        >>> a.add_acl(dev, 'acb123')
        'added acl abc123 to test1-mtc.net.aol.com'
        """
        try:
            rc = self.redis.sadd('acls:explicit:%s' % device.nodeName, acl)
        except redis.exceptions.ResponseError as err:
            return str(err)
        if rc != 1:
            raise exceptions.ACLSetError('%s already has acl %s' % (device.nodeName, acl))
        self.redis.save()

        return 'added acl %s to %s' % (acl, device)

    def remove_acl(self, device, acl):
        """
        Remove explicit acl from device.

        >>> a.remove_acl(dev, 'acb123')
        'removed acl abc123 from test1-mtc.net.aol.com'
        """
        try:
            rc = self.redis.srem('acls:explicit:%s' % device.nodeName, acl)
        except redis.exceptions.ResponseError as err:
            return str(err)
        if rc != 1:
            raise exceptions.ACLSetError('%s does not have acl %s' % (device.nodeName, acl))
        self.redis.save()

        return 'removed acl %s from %s' % (acl, device)

    def get_acl_dict(self, device):
        """
        Returns a dict of acl mappings for a @device, which is expected to
        be a NetDevice object.

        >>> a.get_acl_dict(dev)
        {'all': set(['115j', 'protectRE', 'protectRE.policer', 'test-bluej',
        'testgreenj', 'testops_blockmj']),
        'explicit': set(['test-bluej', 'testgreenj', 'testops_blockmj']),
        'implicit': set(['115j', 'protectRE', 'protectRE.policer'])}
        """
        acls = {}

        # Explicit (we want to make sure the key exists before we try to assign
        # a value)
        expl_key = 'acls:explicit:%s' % device.nodeName
        if self.redis.exists(expl_key):
            acls['explicit'] = self.redis.smembers(expl_key) or set()
        else:
            acls['explicit'] = set()

        # Implicit (automatically-assigned). We're passing the explicit_acls to
        # autoacl so that we can use them logically for auto assignments.
        acls['implicit'] = autoacl(device, explicit_acls=acls['explicit'])

        # All
        acls['all'] = acls['implicit'] | acls['explicit']

        return acls

    def get_acl_set(self, device, acl_set='all'):
        """
        Return an acl set matching @acl_set for a given device.  Match can be
        one of ['all', 'explicit', 'implicit']. Defaults to 'all'.

        >>> a.get_acl_set(dev)
        set(['testops_blockmj', 'testgreenj', '115j', 'protectRE',
        'protectRE.policer', 'test-bluej'])
        >>> a.get_acl_set(dev, 'explicit')
        set(['testops_blockmj', 'test-bluej', 'testgreenj'])
        >>> a.get_acl_set(dev, 'implicit')
        set(['protectRE', 'protectRE.policer', '115j'])
        """
        acls_dict = self.get_acl_dict(device)
        #ACL_SETS = ['all', 'explicit', 'implicit', 'bulk']
        ACL_SETS = acls_dict.keys()
        if DEBUG: print 'fetching', acl_set, 'acls for', device
        if acl_set not in ACL_SETS:
            raise exceptions.InvalidACLSet('match statement must be one of %s' % ACL_SETS)

        return acls_dict[acl_set]


# Functions
def populate_explicit_acls(aclsdb_file):
    """
    populate acls:explicit from legacy acls.db file.

    Format:

    '{unused},{hostname},{acls}\\n'

    - @unused is leftover from legacy and is not used
    - @hostname column is the fqdn of the device
    - @acls is a colon-separated list of ACL names

    Example:

    xx,test1-abc.net.aol.com,juniper-router.policer:juniper-router-protect:abc123
    xx,test2-abc.net.aol.com,juniper-router.policer:juniper-router-protect:abc123
    """
    import csv
    for row in csv.reader(open(aclsdb_file)):
        if not row[0].startswith('!'):
            [r.sadd('acls:explicit:%s' % row[1], acl) for acl in row[2].split(':')]
    r.save()

def backup_explicit_acls():
    """dumps acls:explicit:* to csv"""
    import csv
    out = csv.writer(file(ACLSDB_BACKUP, 'w'))
    for key in r.keys('acls:explicit:*'):
        out.writerow([key.split(':')[-1], ':'.join(map(str, r.smembers(key)))])

def populate_implicit_acls(nd=None):
    """populate acls:implicit (autoacls)"""
    nd = nd or get_netdevices()
    for dev in nd.all():
        [r.sadd('acls:implicit:%s' % dev.nodeName, acl) for acl in autoacl(dev)]
    r.save()

def get_netdevices(production_only=True, with_acls=True):
    """Shortcut to import, instantiate, and return a NetDevices instance."""
    from trigger.netdevices import NetDevices
    return NetDevices(production_only=production_only, with_acls=with_acls)

def get_all_acls(nd=None):
    """
    Returns a dict keyed by acl names whose containing a set of NetDevices
    objects to which each acl is applied.

    @nd can be your own NetDevices object if one is not supplied already

    >>> all_acls = get_all_acls()
    >>> all_acls['abc123']
    set([<NetDevice: test1-abc.net.aol.com>, <NetDevice: fw1-xyz.net.aol.com>])
    """
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    all_acls = defaultdict(set)
    for device in nd.all():
        [all_acls[acl].add(device) for acl in device.acls if acl != '']

    return all_acls

def get_bulk_acls(nd=None):
    """
    Returns a set of acls with an applied count over
    settings.AUTOLOAD_BULK_THRESH.
    """
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    all_acls = get_all_acls()
    bulk_acls = set([acl for acl, devs in all_acls.items() if
                     len(devs) >= settings.AUTOLOAD_BULK_THRESH])

    return bulk_acls

def populate_bulk_acls(nd=None):
    """
    Given a NetDevices instance, Adds bulk_acls attribute to NetDevice objects.
    """
    nd = nd or get_netdevices()
    bulk_acls = get_bulk_acls()
    for dev in nd.all():
        dev.bulk_acls = dev.acls.intersection(bulk_acls)

def get_matching_acls(wanted, exact=True, match_acl=True, match_device=False, nd=None):
    """
    Return a sorted list of the names of devices that have at least one
    of the wanted ACLs, and the ACLs that matched on each.  Without 'exact',
    match ACL name by startswith.

    To get a list of devices, matching the ACLs specified:

    >>> adb.get_matching_acls(['abc123'])
    [('fw1-xyz.net.aol.com', ['abc123']), ('test1-abc.net.aol.com', ['abc123'])]

    To get a list of ACLS matching the devices specified using an explicit
    match (default) by setting match_device=True:

    >>> adb.get_matching_acls(['test1-abc'], match_device=True)
    []
    >>> adb.get_matching_acls(['test1-abc.net.aol.com'], match_device=True)
    [('test1-abc.net.aol.com', ['abc123', 'juniper-router-protect',
    'juniper-router.policer'])]

    To get a list of ACLS matching the devices specified using a partial
    match. Not how it returns all devices starting with 'test1-mtc':

    >>> adb.get_matching_acls(['test1-abc'], match_device=True, exact=False)
    [('test1-abc.net.aol.com', ['abc123', 'juniper-router-protect',
    'juniper-router.policer'])]
    """
    found = []
    wanted_set = set(wanted)

    def match_exact(x):
        return x & wanted_set

    def match_begin(x):
        matched = set()
        for a in wanted_set:
            for b in x:
                if b.startswith(a):
                    matched.add(b)
        return matched

    match = exact and match_exact or match_begin

    # Return all the ACLs if matched by device, or the matched ACLs
    # if matched by ACL.
    #nd = nd or settings.get_netdevices()
    nd = nd or get_netdevices()
    for name, dev in nd.iteritems():
        hit = None
        if match_device:
            if exact and name in wanted:
                hit = dev.acls
            elif not exact:
                for x in wanted:
                    if name.startswith(x):
                        hit = dev.acls
                        break

        if hit is None and match_acl:
            hit = match(dev.acls)

        if hit:
            matched = list(hit)
            matched.sort()
            found.append((name, matched))

    found.sort()
    return found

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

"""
Database models for the task queue.
"""

import datetime
from trigger.conf import settings
from ..packages import peewee as pw

engine = settings.DATABASE_ENGINE
if not engine:
    raise RuntimeError('You must specify a database engine in settings.DATABASE_ENGINE')

# We're hard-coding support for the BIG THREE database solutions for now,
# because that's what the ``peewee`` library we are using as the ORM supports.
if engine == 'sqlite3':
    database = pw.SqliteDatabase(database=settings.DATABASE_NAME,
                                 threadlocals=True)
elif engine == 'mysql':
    if not settings.DATABASE_PORT:
        settings.DATABASE_PORT = 3306
    database = pw.MySQLDatabase(host=settings.DATABASE_HOST,
                                database=settings.DATABASE_NAME,
                                port=settings.DATABASE_PORT,
                                user=settings.DATABASE_USER,
                                passwd=settings.DATABASE_PASSWORD,
                                threadlocals=True)
elif engine == 'postgresql':
    database = pw.PostgresqlDatabase(host=settings.DATABASE_HOST,
                                     database=settings.DATABASE_NAME,
                                     port=settings.DATABASE_PORT,
                                     user=settings.DATABASE_USER,
                                     password=settings.DATABASE_PASSWORD,
                                     threadlocals=True)
else:
    raise RuntimeError('Unsupported database engine: %s' % engine)

class BaseModel(pw.Model):
    """
    Base model that inherits the database object determined above.
    """
    class Meta:
        database = database

class CharField(pw.CharField):
    """Overload default CharField to always return strings vs. UTF-8"""
    def coerce(self, value):
        return str(value or '')
pw.CharField = CharField

class IntegratedTask(BaseModel):
    """
    Tasks for "integrated" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -l``
    """
    id = pw.PrimaryKeyField()
    acl = pw.CharField(null=False, default='')
    router = pw.CharField(null=False, default='')
    queued = pw.DateTimeField(default=datetime.datetime.now)
    loaded = pw.DateTimeField(null=True)
    escalation = pw.BooleanField(default=False)

    class Meta:
        db_table = 'acl_queue'

class ManualTask(BaseModel):
    """
    Tasks for "manual" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -m``
    """
    q_id = pw.PrimaryKeyField()
    q_ts = pw.DateTimeField(default=datetime.datetime.now)
    q_name = pw.CharField(null=False)
    q_routers = pw.CharField(null=False, default='')
    done = pw.BooleanField(default=False)
    q_sr = pw.IntegerField(null=False, default=0)
    login = pw.CharField(null=False, default='')

    class Meta:
        db_table = 'queue'

MODEL_MAP = {
    'integrated': IntegratedTask,
    'manual': ManualTask,
}

def create_tables():
    """Connect to the database and create the tables for each model."""
    database.connect()
    IntegratedTask.create_table()
    ManualTask.create_table()

def confirm_tables():
    """Ensure the table exists for each model."""
    print 'Checking tables...'
    width = max(len(q_name) for q_name in MODEL_MAP)
    for q_name, model in MODEL_MAP.iteritems():
        print q_name.ljust(width),
        print model.table_exists()
    else:
        return True
    return False

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

"""
Parse and manipulate network access control lists.

This library doesn't completely follow the border of the valid/invalid ACL
set, which is determined by multiple vendors and not completely documented
by any of them.  We could asymptotically approach that with an enormous
amount of testing, although it would require a 'flavor' flag (vendor,
router model, software version) for full support.  The realistic goal
is to catch all the errors that we see in practice, and to accept all
the ACLs that we use in practice, rather than to try to reject *every*
invalid ACL and accept *every* valid ACL.

>>> from trigger.acl import parse
>>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
>>> aclobj.terms
[<Term: None>]
"""

__author__ = 'Jathan McCollum, Mike Biancaniello, Michael Harding, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathanism@aol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Saleforce.com'

import IPy
from simpleparse import objectgenerator
from simpleparse.common import comments, strings
from simpleparse.dispatchprocessor import (DispatchProcessor, dispatch,
                                           dispatchList)
from simpleparse.parser import Parser
import socket
from trigger import exceptions
from trigger.conf import settings



# Exports
__all__ = (
    # Constants,
    'ports',
    # Functions
    'check_range',
    'default_processor',
    'do_port_lookup',
    'do_protocol_lookup',
    'literals',
    'make_nondefault_processor',
    'parse',
    'strip_comments',
    'S',
    # Classes
    'ACL',
    'ACLParser',
    'ACLProcessor',
    'Comment',
    'Matches',
    'Policer',
    'PolicerGroup',
    'Protocol',
    'RangeList',
    'Remark',
    'Term',
    'TermList',
    'TIP',
)


# Proceed at your own risk. It's kind of a mess from here on out!
icmp_reject_codes = (
    'administratively-prohibited',
    'bad-host-tos',
    'bad-network-tos',
    'host-prohibited',
    'host-unknown',
    'host-unreachable',
    'network-prohibited',
    'network-unknown',
    'network-unreachable',
    'port-unreachable',
    'precedence-cutoff',
    'precedence-violation',
    'protocol-unreachable',
    'source-host-isolated',
    'source-route-failed',
    'tcp-reset')

icmp_types = {
    'echo-reply': 0,
    'echo-request': 8,
    'echo': 8,                # undocumented
    'info-reply': 16,
    'info-request': 15,
    'information-reply': 16,
    'information-request': 15,
    'mask-request': 17,
    'mask-reply': 18,
    'parameter-problem': 12,
    'redirect': 5,
    'router-advertisement': 9,
    'router-solicit': 10,
    'source-quench': 4,
    'time-exceeded': 11,
    'timestamp': 13,
    'timestamp-reply': 14,
    'unreachable': 3}

icmp_codes = {
    'ip-header-bad': 0,
    'required-option-missing': 1,
    'redirect-for-host': 1,
    'redirect-for-network': 0,
    'redirect-for-tos-and-host': 3,
    'redirect-for-tos-and-net': 2,
    'ttl-eq-zero-during-reassembly': 1,
    'ttl-eq-zero-during-transit': 0,
    'communication-prohibited-by-filtering': 13,
    'destination-host-prohibited': 10,
    'destination-host-unknown': 7,
    'destination-network-prohibited': 9,
    'destination-network-unknown': 6,
    'fragmentation-needed': 4,
    'host-precedence-violation': 14,
    'host-unreachable': 1,
    'host-unreachable-for-TOS': 12,
    'network-unreachable': 0,
    'network-unreachable-for-TOS': 11,
    'port-unreachable': 3,
    'precedence-cutoff-in-effect': 15,
    'protocol-unreachable': 2,
    'source-host-isolated': 8,
    'source-route-failed': 5}

# Cisco "ICMP message type names and ICMP message type and code names" from
# IOS 12.0 documentation.  Verified these against actual practice of 12.1(21),
# since documentation is incomplete.  For example, is 'echo' code 8, type 0
# or code 8, type any?  Experiment shows that it is code 8, type any.
ios_icmp_messages = {
    'administratively-prohibited': (3, 13),
    'alternate-address': (6,),
    'conversion-error': (31,),
    'dod-host-prohibited': (3, 10),
    'dod-net-prohibited': (3, 9),
    'echo': (8,),
    'echo-reply': (0,),
    'general-parameter-problem': (12, 0),
    'host-isolated': (3, 8),
    'host-precedence-unreachable': (3, 14),
    'host-redirect': (5, 1),
    'host-tos-redirect': (5, 3),
    'host-tos-unreachable': (3, 12),
    'host-unknown': (3, 7),
    'host-unreachable': (3, 1),
    'information-reply': (16,),
    'information-request': (15,),
    'mask-reply': (18,),
    'mask-request': (17,),
    'mobile-redirect': (32,),
    'net-redirect': (5, 0),
    'net-tos-redirect': (5, 2),
    'net-tos-unreachable': (3, 11),
    'net-unreachable': (3, 0),
    'network-unknown': (3, 6),
    'no-room-for-option': (12, 2),
    'option-missing': (12, 1),
    'packet-too-big': (3, 4),
    'parameter-problem': (12,),
    'port-unreachable': (3, 3),
    'precedence-unreachable': (3, 14),                # not (3, 15)
    'protocol-unreachable': (3, 2),
    'reassembly-timeout': (11, 1),                # not (11, 2)
    'redirect': (5,),
    'router-advertisement': (9,),
    'router-solicitation': (10,),
    'source-quench': (4,),
    'source-route-failed': (3, 5),
    'time-exceeded': (11,),
    'timestamp-reply': (14,),
    'timestamp-request': (13,),
    'traceroute': (30,),
    'ttl-exceeded': (11, 0),
    'unreachable': (3,) }
ios_icmp_names = dict([(v, k) for k, v in ios_icmp_messages.iteritems()])

# Not all of these are in /etc/services even as of RHEL 4; for example, it
# has 'syslog' only in UDP, and 'dns' as 'domain'.  Also, Cisco (according
# to the IOS 12.0 documentation at least) allows 'dns' in UDP and not TCP,
# along with other anomalies.  We'll be somewhat more generous in parsing
# input, and always output as integers.
ports = {
    'afs': 1483,        # JunOS
    'bgp': 179,
    'biff': 512,
    'bootpc': 68,
    'bootps': 67,
    'chargen': 19,
    'cmd': 514,                # undocumented IOS
    'cvspserver': 2401,        # JunOS
    'daytime': 13,
    'dhcp': 67,                # JunOS
    'discard': 9,
    'dns': 53,
    'dnsix': 90,
    'domain': 53,
    'echo': 7,
    'eklogin': 2105,        # JunOS
    'ekshell': 2106,        # JunOS
    'exec': 512,        # undocumented IOS
    'finger': 79,
    'ftp': 21,
    'ftp-data': 20,
    'gopher': 70,
    'hostname': 101,
    'http': 80,                # JunOS
    'https': 443,        # JunOS
    'ident': 113,        # undocumented IOS
    'imap': 143,        # JunOS
    'irc': 194,
    'isakmp': 500,        # undocumented IOS
    'kerberos-sec': 88,        # JunOS
    'klogin': 543,
    'kpasswd': 761,        # JunOS
    'kshell': 544,
    'ldap': 389,        # JunOS
    'ldp': 646,                # undocumented JunOS
    'login': 513,        # JunOS
    'lpd': 515,
    'mobile-ip': 434,
    'mobileip-agent': 434,  # JunOS
    'mobileip-mn': 435,        # JunOS
    'msdp': 639,        # JunOS
    'nameserver': 42,
    'netbios-dgm': 138,
    'netbios-ns': 137,
    'netbios-ssn': 139,        # JunOS
    'nfsd': 2049,        # JunOS
    'nntp': 119,
    'ntalk': 518,        # JunOS
    'ntp': 123,
    'pop2': 109,
    'pop3': 110,
    'pptp': 1723,        # JunOS
    'printer': 515,        # JunOS
    'radacct': 1813,        # JunOS
    'radius': 1812,        # JunOS and undocumented IOS
    'rip': 520,
    'rkinit': 2108,        # JunOS
    'smtp': 25,
    'snmp': 161,
    'snmptrap': 162,
    'snmp-trap': 162,        # undocumented IOS
    'snpp': 444,        # JunOS
    'socks': 1080,        # JunOS
    'ssh': 22,                # JunOS
    'sunrpc': 111,
    'syslog': 514,
    'tacacs': 49,        # undocumented IOS
    'tacacs-ds': 49,
    'talk': 517,
    'telnet': 23,
    'tftp': 69,
    'time': 37,
    'timed': 525,        # JunOS
    'uucp': 540,
    'who': 513,
    'whois': 43,
    'www': 80,
    'xdmcp': 177,
    'zephyr-clt': 2103,        # JunOS
    'zephyr-hm': 2104        # JunOS
}

dscp_names = {
    'be': 0,
    'cs0': 0,
    'cs1': 8,
    'af11': 10,
    'af12': 12,
    'af13': 14,
    'cs2': 16,
    'af21': 18,
    'af22': 20,
    'af23': 22,
    'cs3': 24,
    'af31': 26,
    'af32': 28,
    'af33': 30,
    'cs4': 32,
    'af41': 34,
    'af42': 36,
    'af43': 38,
    'cs5': 40,
    'ef': 46,
    'cs6': 48,
    'cs7': 56
}

precedence_names = {
    'critical-ecp': 0xa0,        # JunOS
    'critical': 0xa0,                # IOS
    'flash': 0x60,
    'flash-override': 0x80,
    'immediate': 0x40,
    'internet-control': 0xc0,        # JunOS
    'internet': 0xc0,                # IOS
    'net-control': 0xe0,        # JunOS
    'network': 0xe0,                # IOS
    'priority': 0x20,
    'routine': 0x00 }

ip_option_names = {
    'loose-source-route': 131,
    'record-route': 7,
    'router-alert': 148,
    'strict-source-route': 137,
    'timestamp': 68 }

fragment_flag_names = {
    'dont-fragment': 0x4000,
    'more-fragments': 0x2000,
    'reserved': 0x8000 }

tcp_flag_names = {
    'ack': 0x10,
    'fin': 0x01,
    'push': 0x08,
    'rst': 0x04,
    'syn': 0x02,
    'urgent': 0x20 }

tcp_flag_specials = {
    'tcp-established': '"ack | rst"',
    'tcp-initial': '"syn & !ack"' }
tcp_flag_rev = dict([(v, k) for k, v in tcp_flag_specials.iteritems()])

adrsbk = { 'svc':{'group':{}, 'book':{}}, 'addr':{'group':{},'book':{}} }

class MyDict(dict):
    """
    A dictionary subclass to collect common behavior changes used in container
    classes for the ACL components: Modifiers, Matches.
    """
    def __init__(self, d=None, **kwargs):
        if d:
            if not hasattr(d, 'keys'):
                d = dict(d)
            self.update(d)
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def __str__(self):
        return ', '.join(['%s %s' % (k, v) for k, v in self.iteritems()])

    def update(self, d):
        '''Force this to go through __setitem__.'''
        for k, v in d.iteritems():
            self[k] = v


def check_name(name, exc, max_len=255, extra_chars=' -_.'):
    """
    Test whether something is a valid identifier (for any vendor).
    This means letters, numbers, and other characters specified in the
    @extra_chars argument.  If the string is invalid, throw the specified
    exception.

    :param name: The name to test.
    :param exc: Exception type to raise if the name is invalid.
    :param max_len: Integer of the maximum length of the name.
    :param extra_chars: Extra non-alphanumeric characters to allow in the name.
    """
    if name is None:
        return
    if name == '':
        raise exc('Name cannot be null string')
    if len(name) > max_len:
        raise exc('Name "%s" cannot be longer than %d characters' % (name, max_len))
    for char in name:
        if not ((extra_chars is not None and char in extra_chars)
                or (char >= 'a' and char <= 'z')
                or (char >= 'A' and char <= 'Z')
                or (char >= '0' and char <= '9')):
            raise exc('Invalid character "%s" in name "%s"' % (char, name))


# Temporary resting place for comments, so the rest of the parser can
# ignore them.  Yes, this makes the library not thread-safe.
Comments = []


class RangeList(object):
    """
    A type which stores ordered sets, with efficient handling of
    ranges.  It can also store non-incrementable terms as an sorted set
    without collapsing into ranges.

    This is currently used to just store match conditions (e.g. protocols,
    ports), but could be fleshed out into a general-purpose class.  One
    thing to think about is how/whether to handle a list of tuples as distinct
    from a list of ranges.  Should we just store them as xrange objects?
    Should the object appear as discrete elements by default, for example
    in len(), with the collapsed view as a method, or should we keep it
    as it is now?  All the current uses of this class are in this file
    and have unit tests, so when we decided what the semantics of the
    generalized module ought to be, we can make it so without worry.
    """
    # Another way to implement this would be as a radix tree.
    def __init__(self, data=None):
        if data is None:
            data = []

        self.data = data
        self._do_collapse()

    def _cleanup(self, L):
        """
        Prepare a potential list of lists, tuples, digits for collapse. Does
        the following::

        1. Sort & Convert all inner lists to tuples
        2. Convert all tuples w/ only 1 item into single item
        3. Gather all single digits
        4. Convert to set to remove duplicates
        5. Return as a sorted list

        """
        ret = []

        # Get all list/tuples and return tuples
        tuples = [tuple(sorted(i)) for i in L if isinstance(i, (list, tuple))]
        singles = [i[0] for i in tuples if len(i) == 1] # Grab len of 1
        tuples = [i for i in tuples if len(i) == 2]     # Filter out len of 1
        digits = [i for i in L if isinstance(i, int)]   # Get digits

        ret.extend(singles)
        ret.extend(tuples)
        ret.extend(digits)

        if not ret:
            ret = L

        return sorted(set(ret))

    def _collapse(self, l):
        """
        Reduce a sorted list of elements to ranges represented as tuples;
        e.g. [1, 2, 3, 4, 10] -> [(1, 4), 10]
        """
        l = self._cleanup(l) # Remove duplicates

        # Don't bother reducing a single item
        if len(l) <= 1:
            return l

        # Make sure the elements are incrementable, or we can't reduce at all.
        try:
            l[0] + 1
        except (TypeError, AttributeError):
            return l
        '''
            try:
                l[0][0] + 1
            except (TypeError, AttributeError):
                return l
        '''

        # This last step uses a loop instead of pure functionalism because
        # it will be common to step through it tens of thousands of times,
        # for example in the case of (1024, 65535).
        # [x, x+1, ..., x+n] -> [(x, x+n)]
        n = 0
        try:
            while l[n] + 1 == l[n+1]:
                n += 1
        except IndexError:  # entire list collapses to one range
            return [(l[0], l[-1])]
        if n == 0:
            return [l[0]] + self._collapse(l[1:])
        else:
            return [(l[0], l[n])] + self._collapse(l[n+1:])

    def _do_collapse(self):
        self.data = self._collapse(self._expand(self.data))

    def _expand(self, l):
        """Expand a list of elements and tuples back to discrete elements.
        Opposite of _collapse()."""
        if not l:
            return l
        try:
            return range(l[0][0], l[0][1]+1) + self._expand(l[1:])
        except AttributeError:        # not incrementable
            return l
        except (TypeError, IndexError):
            return [l[0]] + self._expand(l[1:])

    def expanded(self):
        """Return a list with all ranges converted to discrete elements."""
        return self._expand(self.data)

    def __add__(self, y):
        for elt in y:
            self.append(elt)

    def append(self, obj):
        # We could make this faster.
        self.data.append(obj)
        self._do_collapse()

    def __cmp__(self, other):
        other = self._collapse(other)
        if self.data < other:
            return -1
        elif self.data > other:
            return 0
        else:
            return 0

    def __contains__(self, obj):
        """
        Performs voodoo to compare the following:
            * Compare single ports to tuples (i.e. 1700 in (1700, 1800))
            * Compare tuples to tuples (i.e. (1700,1800) in (0,65535))
            * Comparing tuple to integer ALWAYS returns False!!
        """
        for elt in self.data:
            if isinstance(elt, tuple):
                if isinstance(obj, tuple):
                    ## if obj is a tuple, see if it is within the range of elt
                    ## using xrange here is faster (add +1 to include elt[1])
                    ## otherwise you end up 1 digit short of max
                    rng = xrange(elt[0], elt[1] + 1)
                    if obj[0] in rng and obj[1] in rng:
                        return True
                else:
                    if elt[0] <= obj <= elt[1]:
                        return True

            elif hasattr(elt, '__contains__'):
                if obj in elt:
                    return True
            else:
                if elt == obj:
                    return True
        return False

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self.data))

    def __str__(self):
        return str(self.data)

    # Straight passthrough of these:
    def __hash__(self):
        return self.data.__hash__(self.data)
    def __len__(self):
        return len(self.data)
    def __getitem__(self, key):
        return self.data[key]
    def __setitem__(self, key, value):
        self.data[key] = value
    def __delitem__(self, key):
        del self.data[key]
    def __iter__(self):
        return self.data.__iter__()

class TIP(IPy.IP):
    """
    Class based on IPy.IP, but with extensions for Trigger.

    Currently, only the only extension is the ability to negate a network
    block. Only used internally within the parser, as it's not complete
    (doesn't interact well with IPy.IP objects). Does not handle IPv6 yet.
    """
    def __init__(self, data, **kwargs):
        # Insert logic to handle 'except' preserve negated flag if it exists
        # already
        negated = getattr(data, 'negated', False)

        # Handle 'inactive:' address objects by setting inactive flag
        inactive = getattr(data, 'inactive', False)

        # Is data a string?
        if isinstance(data, (str, unicode)):
            d = data.split()
            # This means we got something like "1.2.3.4 except" or "inactive:
            # 1.2.3.4'
            if len(d) == 2:
                # Check if last word is 'except', set negated=True
                if d[-1] == 'except':
                    negated = True
                    data = d[0]
                # Check if first word is 'inactive:', set inactive=True
                elif d[0] == 'inactive:':
                    inactive = True
                    data = d[1]
            elif len(d) == 3:
                if d[-1] == 'except':
                    negated = True
                if d[0] == 'inactive:':
                    inactive = True
                if inactive and negated:
                    data = d[1]

        self.negated = negated # Set 'negated' variable
        self.inactive = inactive # Set 'inactive' variable
        IPy.IP.__init__(self, data, **kwargs)

        # Make it print prefixes for /32, /128 if we're negated or inactive (and
        # therefore assuming we're being used in a Juniper ACL.)
        if self.negated or self.inactive:
            self.NoPrefixForSingleIp = False

    def __cmp__(self, other):
        # Regular IPy sorts by prefix length before network base, but Juniper
        # (our baseline) does not. We also need comparisons to be different for
        # negation. Following Juniper's sorting, use I Pcompare, and then break
        # ties where negated < not negated.
        diff = cmp(self.ip, other.ip)
        if diff == 0:
            # If the same IP, compare by prefixlen
            diff = cmp(self.prefixlen(), other.prefixlen())
        # If both negated, they're the same
        if self.negated == other.negated:
            return diff
        # Sort to make negated < not negated
        if self.negated:
            diff = -1
        else:
            diff = 1
        # Return the base comparison
        return diff

    def __repr__(self):
        # Just stick an 'except' at the end if except is set since we don't
        # code to accept this in the constructor really just provided, for now,
        # as a debugging aid.
        rs = IPy.IP.__repr__(self)
        if self.negated:
            # Insert ' except' into the repr. (Yes, it's a hack!)
            rs = rs.split("'")
            rs[1] += ' except'
            rs = "'".join(rs) # Restore original repr
        if self.inactive:
            # Insert 'inactive: ' into the repr. (Yes, it's also a hack!)
            rs = rs.split("'")
            rs[1] = 'inactive: ' + rs[1]
            rs = "'".join(rs) # Restore original repr
        return rs

    def __str__(self):
        # IPy is not a new-style class, so the following doesn't work:
        # return super(TIP, self).__str__()
        rs = IPy.IP.__str__(self)
        if self.negated:
            rs += ' except'
        if self.inactive:
            rs = 'inactive: ' + rs
        return rs

    def __contains__(self, item):
        """
        Containment logic, including except.
        """
        item = TIP(item)
        # Calculate XOR
        xor = self.negated ^ item.negated
        # If one item is negated, it's never contained.
        if xor:
            return False
        matched = IPy.IP.__contains__(self, item)
        return matched ^ self.negated

class Comment(object):
    """
    Container for inline comments.
    """
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, repr(self.data))

    def __str__(self):
        return self.data

    def __len__(self):
        '''Defining this method allows null comments to be false.'''
        return len(self.data)

    def __iter__(self):
        return self.data.__iter__()

    def __contains__(self, item):
        return item in self.data

    def output_junos(self):
        """Output the Comment to JunOS format."""
        return '/*%s*/' % self.data

    def output_ios(self):
        """Output the Comment to IOS traditional format."""
        if not self.data:
            return '!'

        data = self.data
        if data.startswith('!'):
            prefix = '!'
            data = prefix + data
        else:
            prefix = '! '
        lines = data.splitlines()

        return '\n'.join(prefix + line for line in lines)

    def output_ios_named(self):
        """Output the Comment to IOS named format."""
        return self.output_ios()

    def output_iosxr(self):
        """Output the Comment to IOS XR format."""
        return self.output_ios()

class Remark(Comment):
    """
    IOS extended ACL "remark" lines automatically become comments when
    converting to other formats of ACL.
    """
    def output_ios_named(self):
        """Output the Remark to IOS named format."""
        return ' remark ' + self.data

class PolicerGroup(object):
    """Container for Policer objects. Juniper only."""
    def __init__(self, format=None):
        self.policers = []
        self.format   = format
        global Comments
        self.comments = Comments
        Comments = []

    def output(self, format=None, *largs, **kwargs):
        if format is None:
            format = self.format
        return getattr(self,'output_' + format)(*largs, **kwargs)

    def output_junos(self, replace=False):
        output = []
        for ent in self.policers:
            for x in ent.output():
                output.append(x)

        if replace:
            return ['firewall {', 'replace:'] + ['    '+x for x in output] + ['}']
        else:
            return output

class ACL(object):
    """
    An abstract access-list object intended to be created by the :func:`parse`
    function.
    """
    def __init__(self, name=None, terms=None, format=None, family=None,
                 interface_specific=False):
        check_name(name, exceptions.ACLNameError, max_len=24)
        self.name = name
        self.family = family
        self.interface_specific = interface_specific
        self.format = format
        self.policers = []
        if terms:
            self.terms = terms
        else:
            self.terms = TermList()
        global Comments
        self.comments = Comments
        Comments = []

    def __repr__(self):
        return '<ACL: %s>' % self.name

    def __str__(self):
        return '\n'.join(self.output(format=self.format, family=self.family))

    def output(self, format=None, *largs, **kwargs):
        """
        Output the ACL data in the specified format.
        """
        if format is None:
            format = self.format
        return getattr(self, 'output_' + format)(*largs, **kwargs)

    def output_junos(self, replace=False, family=None):
        """
        Output the ACL in JunOS format.

        :param replace: If set the ACL is wrapped in a
            ``firewall { replace: ... }`` section.
        :param family: If set, the value is used to wrap the ACL in a
            ``family inet { ...}`` section.
        """
        if self.name == None:
            raise exceptions.MissingACLName('JunOS format requires a name')

        # Make sure we properly set 'family' so it's automatically used for
        # printing.
        if family is not None:
            assert family in ('inet', 'inet6')
        else:
            family = self.family

        # Prep the filter body
        out = ['filter %s {' % self.name]
        out += ['    ' + c.output_junos() for c in self.comments if c]

        # Add the policers
        if self.policers:
            for policer in self.policers:
                out += ['    ' + x for x in policer.output()]

        # Add interface-specific
        if self.interface_specific:
            out += ['    ' + 'interface-specific;']

        # Add the terms
        for t in self.terms:
            out += ['    ' + x for x in t.output_junos()]
        out += ['}']

        # Wrap in 'firewall {}' thingy.
        if replace:
            '''
            #out = ['firewall {', 'replace:'] + ['    '+x for x in out] + ['}']
            if family is None: # This happens more often
                out = ['firewall {', 'replace:'] + ['    '+x for x in out] + ['}']
            else:
                out = ['firewall {', family_head, 'replace:'] + ['    '+x for x in out] + [family_tail, '}']
            '''

            head = ['firewall {']
            body = ['replace:'] + ['    ' + x for x in out]
            tail = ['}']
            if family is not None:
                body = ['family %s {' % family] + body + tail
                body = ['    ' + x for x in body]
            out = head + body + tail

        return out

    def output_ios(self, replace=False):
        """
        Output the ACL in IOS traditional format.

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS format requires a name')
        try:
            x = int(self.name)
            if not (100 <= x <= 199 or 2000 <= x <= 2699):
                raise exceptions.BadACLName('IOS ACLs are 100-199 or 2000-2699')
        except (TypeError, ValueError):
            raise exceptions.BadACLName('IOS format requires a number as name')
        out = [c.output_ios() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no access-list ' + self.name)
        prefix = 'access-list %s ' % self.name
        for t in self.terms:
            out += [x for x in t.output_ios(prefix)]
        return out

    def output_ios_brocade(self, replace=False, receive_acl=False):
        """
        Output the ACL in Brocade-flavored IOS format.

        The difference between this and "traditional" IOS are:

            - Stripping of comments
            - Appending of ``ip rebind-acl`` or ``ip rebind-receive-acl`` line

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        :param receive_acl: If set the ACL is suffixed with a ``ip
            rebind-receive-acl' instead of ``ip rebind-acl``.
        """
        self.strip_comments()

        # Check if the is_receive_acl attr was set by the parser. This way we
        # don't always have to pass the argument.
        if hasattr(self, 'is_receive_acl') and not receive_acl:
            receive_acl = self.is_receive_acl

        out = self.output_ios(replace=replace)
        if receive_acl:
            out.append('ip rebind-receive-acl %s' % self.name)
        else:
            out.append('ip rebind-acl %s' % self.name)

        return out

    def output_ios_named(self, replace=False):
        """
        Output the ACL in IOS named format.

        :param replace: If set the ACL is preceded by a ``no access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS format requires a name')
        out = [c.output_ios_named() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no ip access-list extended ' + self.name)
        out.append('ip access-list extended %s' % self.name)
        for t in self.terms:
            out += [x for x in t.output_ios_named(' ')]
        return out

    def output_iosxr(self, replace=False):
        """
        Output the ACL in IOS XR format.

        :param replace: If set the ACL is preceded by a ``no ipv4 access-list`` line.
        """
        if self.name == None:
            raise exceptions.MissingACLName('IOS XR format requires a name')
        out = [c.output_iosxr() for c in self.comments]
        if self.policers:
            raise exceptions.VendorSupportLacking('policers not supported in IOS')
        if replace:
            out.append('no ipv4 access-list ' + self.name)
        out.append('ipv4 access-list ' + self.name)
        counter = 0        # 10 PRINT "CISCO SUCKS"  20 GOTO 10
        for t in self.terms:
            if t.name == None:
                for line in t.output_ios():
                    counter = counter + 10
                    out += [' %d %s' % (counter, line)]
            else:
                try:
                    counter = int(t.name)
                    if not 1 <= counter <= 2147483646:
                        raise exceptions.BadTermName('Term %d out of range' % counter)
                    line = t.output_iosxr()
                    if len(line) > 1:
                        raise exceptions.VendorSupportLacking('one name per line')
                    out += [' ' + line[0]]
                except ValueError:
                    raise exceptions.BadTermName('IOS XR requires numbered terms')
        return out

    def name_terms(self):
        """Assign names to all unnamed terms."""
        n = 1
        for t in self.terms:
            if t.name is None:
                t.name = 'T%d' % n
                n += 1

    def strip_comments(self):
        """Strips all comments from ACL header and all terms."""
        self.comments = []
        for term in self.terms:
            term.comments = []

class Term(object):
    """An individual term from which an ACL is made"""
    def __init__(self, name=None, action='accept', match=None, modifiers=None,
                 inactive=False, isglobal=False, extra=None):
        self.name = name
        self.action = action
        self.inactive = inactive
        self.isglobal = isglobal
        self.extra = extra
        self.makediscard = False # set to True if 'make discard' is used
        if match is None:
            self.match = Matches()
        else:
            self.match = match

        if modifiers is None:
            self.modifiers = Modifiers()
        else:
            self.modifiers = modifiers

        global Comments
        self.comments = Comments
        Comments = []

    def __repr__(self):
        return '<Term: %s>' % self.name

    def getname(self):
        return self.__name

    def setname(self, name):
        check_name(name, exceptions.BadTermName)
        self.__name = name

    def delname(self):
        self.name = None
    name = property(getname, setname, delname)

    def getaction(self):
        return self.__action

    def setaction(self, action):
        if action is None:
            action = 'accept'
        if action == 'next term':
            action = ('next', 'term')
        if isinstance(action, str):
            action = (action,)
        if len(action) > 2:
            raise exceptions.ActionError('too many arguments to action "%s"' %
                                         str(action))
        action = tuple(action)
        if action in (('accept',), ('discard',), ('reject',), ('next', 'term')):
            self.__action = action
        elif action == ('permit',):
            self.__action = ('accept',)
        elif action == ('deny',):
            self.__action = ('reject',)
        elif action[0] == 'reject':
            if action[1] not in icmp_reject_codes:
                raise exceptions.BadRejectCode('invalid rejection code ' + action[1])
            if action[1] == icmp_reject_codes[0]:
                action = ('reject',)
            self.__action = action
        elif action[0] == 'routing-instance':
            check_name(action[1], exceptions.BadRoutingInstanceName)
            self.__action = action
        else:
            raise exceptions.UnknownActionName('unknown action "%s"' % str(action))

    def delaction(self):
        self.action = 'accept'
    action = property(getaction, setaction, delaction)

    def set_action_or_modifier(self, action):
        """
        Add or replace a modifier, or set the primary action. This method exists
        for the convenience of parsers.
        """
        try:
            self.action = action
        except exceptions.UnknownActionName:
            if not isinstance(action, tuple):
                self.modifiers[action] = None
            else:
                if len(action) == 1:
                    self.modifiers[action[0]] = None
                else:
                    self.modifiers[action[0]] = action[1]

    def output(self, format, *largs, **kwargs):
        """
        Output the term to the specified format

        :param format: The desired output format.
        """
        return getattr(self, 'output_' + format)(*largs, **kwargs)

    def output_junos(self, *args, **kwargs):
        """Convert the term to JunOS format."""
        if self.name is None:
            raise exceptions.MissingTermName('JunOS requires terms to be named')
        out = ['%sterm %s {' %
                (self.inactive and 'inactive: ' or '', self.name)]
        out += ['    ' + c.output_junos() for c in self.comments if c]
        if self.extra:
            blah = str(self.extra)
            out += "/*",blah,"*/"
        if self.match:
            out.append('    from {')
            out += [' '*8 + x for x in self.match.output_junos()]
            out.append('    }')
        out.append('    then {')
        acttext = '        %s;' % ' '.join(self.action)
        # add a comment if 'make discard' is in use
        if self.makediscard:
            acttext += (" /* REALLY AN ACCEPT, MODIFIED BY"
                        " 'make discard' ABOVE */")
        out.append(acttext)
        out += [' '*8 + x for x in self.modifiers.output_junos()]
        out.append('    }')
        out.append('}')
        return out

    def _ioslike(self, prefix=''):
        if self.inactive:
            raise exceptions.VendorSupportLacking("inactive terms not supported by IOS")
        action = ''
        if self.action == ('accept',):
            action = 'permit '
        #elif self.action == ('reject',):
        elif self.action in (('reject',), ('discard',)):
            action = 'deny '
        else:
            raise VendorSupportLacking('"%s" action not supported by IOS' % ' '.join(self.action))
        suffix = ''
        for k, v in self.modifiers.iteritems():
            if k == 'syslog':
                suffix += ' log'
            elif k == 'count':
                pass        # counters are implicit in IOS
            else:
                raise exceptions.VendorSupportLacking('"%s" modifier not supported by IOS' % k)
        return [prefix + action + x + suffix for x in self.match.output_ios()]

    def output_ios(self, prefix=None, acl_name=None):
        """
        Output term to IOS traditional format.

        :param prefix: Prefix to use, default: 'access-list'
        :param acl_name: Name of access-list to display
        """
        comments = [c.output_ios() for c in self.comments]
        # If prefix isn't set, but name is, force the template
        if prefix is None and acl_name is not None:
            prefix = 'access-list %s ' % acl_name

        # Or if prefix is set, but acl_name isn't, make sure prefix ends with ' '
        elif prefix is not None and acl_name is None:
            if not prefix.endswith(' '):
                prefix += ' '

        # Or if both are set, use them
        elif prefix is not None and acl_name is not None:
            prefix = '%s %s ' % (prefix.strip(), acl_name.strip())

        # Otherwise no prefix
        else:
            prefix = ''

        return comments + self._ioslike(prefix)

    def output_ios_named(self, prefix='', *args, **kwargs):
        """Output term to IOS named format."""
        comments = [c.output_ios_named() for c in self.comments]
        return comments + self._ioslike(prefix)

    def output_iosxr(self, prefix='', *args, **kwargs):
        """Output term to IOS XR format."""
        comments = [c.output_iosxr() for c in self.comments]
        return comments + self._ioslike(prefix)

class TermList(list):
    """Container class for Term objects within an ACL object."""
    pass

class Modifiers(MyDict):
    """
    Container class for modifiers. These are only supported by JunOS format
    and are ignored by all others.
    """
    def __setitem__(self, key, value):
        # Handle argument-less modifiers first.
        if key in ('log', 'sample', 'syslog', 'port-mirror'):
            if value not in (None, True):
                raise exceptions.ActionError('"%s" action takes no argument' % key)
            super(Modifiers, self).__setitem__(key, None)
            return
        # Everything below requires an argument.
        if value is None:
            raise exceptions.ActionError('"%s" action requires an argument' %
                                         key)
        if key == 'count':
            # JunOS 7.3 docs say this cannot contain underscores and that
            # it must be 24 characters or less, but this appears to be false.
            # Doc bug filed 2006-02-09, doc-sw/68420.
            check_name(value, exceptions.BadCounterName, max_len=255)
        elif key == 'forwarding-class':
            check_name(value, exceptions.BadForwardingClassName)
        elif key == 'ipsec-sa':
            check_name(value, exceptions.BadIPSecSAName)
        elif key == 'loss-priority':
            if value not in ('low', 'high'):
                raise exceptions.ActionError('"loss-priority" must be "low" or "high"')
        elif key == 'policer':
            check_name(value, exceptions.BadPolicerName)
        else:
            raise exceptions.ActionError('invalid action: ' + str(key))
        super(Modifiers, self).__setitem__(key, value)

    def output_junos(self):
        """
        Output the modifiers to the only supported format!
        """
        keys = self.keys()
        keys.sort()
        return [k + (self[k] and ' '+str(self[k]) or '') + ';' for k in keys]

class Policer(object):
    """
    Container class for policer policy definitions. This is a dummy class for
    now, that just passes it through as a string.
    """
    def __init__(self, name, data):
        if not name:
            raise exceptions.ActionError("Policer requres name")
        self.name = name
        self.exceedings = []
        self.actions    = []
        for elt in data:
            for k,v in elt.iteritems():
                if k == 'if-exceeding':
                    for entry in v:
                        type, value = entry
                        if type == 'bandwidth-limit':
                            limit = self.str2bits(value)
                            if limit > 32000000000 or limit < 32000:
                                raise "bandwidth-limit must be between 32000bps and 32000000000bps"
                            self.exceedings.append((type, limit))
                        elif type == 'burst-size-limit':
                            limit = self.str2bits(value)
                            if limit > 100000000 or limit < 1500:
                                raise "burst-size-limit must be between 1500B and 100,000,000B"
                            self.exceedings.append((type, limit))
                        elif type == 'bandwidth-percent':
                            limit = int(value)
                            if limit < 1 or limit > 100:
                                raise "bandwidth-percent must be between 1 and 100"
                        else:
                            raise "Unknown policer if-exceeding tag: %s" % type
                elif k == 'action':
                    for i in v:
                        self.actions.append(i)

    def str2bits(self, str):
        try:
            val = int(str)
        except:
            if str[-1] == 'k':
                return int(str[0:-1]) * 1024
            if str[-1] == 'm':
                return int(str[0:-1]) * 1048576
            else:
                raise "invalid bit definition %s" % str
        return val

    def __repr__(self):
            return '<%s: %s>' % (self.__class__.__name__, repr(self.name))

    def __str__(self):
            return self.data

    def output(self):
        output = ['policer %s {' % self.name]
        if self.exceedings:
            output.append('    if-exceeding {')
        for x in self.exceedings:
            output.append('        %s %s;' % (x[0],x[1]))
        if self.exceedings:
            output.append('    }')
        if self.actions:
            output.append('    then {')
        for x in self.actions:
            output.append('        %s;' % x)

        if self.actions:
            output.append('    }')
        output.append('}')
        return output

class Protocol(object):
    """
    A protocol object used for access membership tests in :class:`Term` objects.
    Acts like an integer, but stringify into a name if possible.
    """
    num2name = {
        1: 'icmp',
        2: 'igmp',
        4: 'ipip',
        6: 'tcp',
        8: 'egp',
        17: 'udp',
        41: 'ipv6',
        #46: 'rsvp',
        47: 'gre',
        50: 'esp',
        51: 'ah',
        89: 'ospf',
        94: 'nos',
        103: 'pim',
        #112: 'vrrp' # Breaks Cisco compatibility
    }

    name2num = dict([(v, k) for k, v in num2name.iteritems()])
    name2num['ahp'] = 51    # undocumented Cisco special name

    def __init__(self, arg):
        if isinstance(arg, Protocol):
            self.value = arg.value
        elif arg in Protocol.name2num:
            self.value = Protocol.name2num[arg]
        else:
            self.value = int(arg)

    def __str__(self):
        if self.value in Protocol.num2name:
            return Protocol.num2name[self.value]
        else:
            return str(self.value)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def __cmp__(self, other):
        '''Protocol(6) == 'tcp' == 6 == Protocol('6').'''
        return self.value.__cmp__(Protocol(other).value)

    def __hash__(self):
        return hash(self.value)

    def __getattr__(self, name):
        '''Allow arithmetic operations to work.'''
        return getattr(self.value, name)

# Having this take the dictionary itself instead of a function is very slow.
def do_lookup(lookup_func, arg):
    if isinstance(arg, tuple):
        return tuple([do_lookup(lookup_func, elt) for elt in arg])

    try:
        return int(arg)
    except TypeError:
        return arg
    except ValueError:
        pass
    # Ok, look it up by name.
    try:
        return lookup_func(arg)
    except KeyError:
        raise exceptions.UnknownMatchArg('match argument "%s" not known' % arg)

def do_protocol_lookup(arg):
    if isinstance(arg, tuple):
        return (Protocol(arg[0]), Protocol(arg[1]))
    else:
        return Protocol(arg)

def do_port_lookup(arg):
    return do_lookup(lambda x: ports[x], arg)

def do_icmp_type_lookup(arg):
    return do_lookup(lambda x: icmp_types[x], arg)

def do_icmp_code_lookup(arg):
    return do_lookup(lambda x: icmp_codes[x], arg)

def do_ip_option_lookup(arg):
    return do_lookup(lambda x: ip_option_names[x], arg)

def do_dscp_lookup(arg):
    return do_lookup(lambda x: dscp_names[x], arg)

def check_range(values, min, max):
    for value in values:
        try:
            for subvalue in value:
                check_range([subvalue], min, max)
        except TypeError:
            if not min <= value <= max:
                raise exceptions.BadMatchArgRange('match arg %s must be between %d and %d'
                                                  % (str(value), min, max))


# Ordering for JunOS match clauses.  AOL style rules:
# 1. Use the order found in the IP header, except, put protocol at the end
#    so it is close to the port and tcp-flags.
# 2. General before specific.
# 3. Source before destination.
junos_match_ordering_list = (
    'source-mac-address',
    'destination-mac-address',
    'packet-length',
    'fragment-flags',
    'fragment-offset',
    'first-fragment',
    'is-fragment',
    'prefix-list',
    'address',
    'source-prefix-list',
    'source-address',
    'destination-prefix-list',
    'destination-address',
    'ip-options',
    'protocol',
    # TCP/UDP
    'tcp-flags',
    'port',
    'source-port',
    'destination-port',
    # ICMP
    'icmp-code',
    'icmp-type' )

junos_match_order = {}

for i, match in enumerate(junos_match_ordering_list):
    junos_match_order[match] = i*2
    junos_match_order[match+'-except'] = i*2 + 1

# These types of Juniper matches go in braces, not square brackets.
address_matches = set(['address', 'destination-address', 'source-address', 'prefix-list', 'source-prefix-list', 'destination-prefix-list'])
for match in list(address_matches):
    address_matches.add(match+'-except')

class Matches(MyDict):
    """
    Container class for Term.match object used for membership tests on
    access checks.
    """
    def __setitem__(self, key, arg):
        if key in ('ah-spi', 'destination-mac-address', 'ether-type',
                   'esp-spi', 'forwarding-class', 'interface-group',
                   'source-mac-address', 'vlan-ether-type',
                   'fragment-flags', 'source-class', 'destination-class'):
            raise NotImplementedError('match on %s not implemented' % key)

        if arg is None:
            raise exceptions.MatchError('match must have an argument')

        negated = False
        if key.endswith('-except'):
            negated = True
            key = key[:-7]

        if key in ('port', 'source-port', 'destination-port'):
            arg = map(do_port_lookup, arg)
            check_range(arg, 0, 65535)
        elif key == 'protocol':
            arg = map(do_protocol_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'fragment-offset':
            arg = map(do_port_lookup, arg)
            check_range(arg, 0, 8191)
        elif key == 'icmp-type':
            arg = map(do_icmp_type_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'icmp-code':
            arg = map(do_icmp_code_lookup, arg)
            check_range(arg, 0, 255)
        elif key == 'icmp-type-code':
            # Not intended for external use; this is for parser convenience.
            self['icmp-type'] = [arg[0]]
            try:
                self['icmp-code'] = [arg[1]]
            except IndexError:
                try:
                    del self['icmp-code']
                except KeyError:
                    pass
            return
        elif key == 'packet-length':
            arg = map(int, arg)
            check_range(arg, 0, 65535)
        elif key in ('address', 'source-address', 'destination-address'):
            arg = map(TIP, arg)
        elif key in ('prefix-list', 'source-prefix-list',
                     'destination-prefix-list'):
            for pl in arg:
                check_name(pl, exceptions.MatchError)
        elif key in tcp_flag_specials:
            # This cannot be the final form of how to represent tcp-flags.
            # Instead, we need to implement a real parser for it.
            # See: http://www.juniper.net/techpubs/software/junos/junos73/swconfig73-policy/html/firewall-config14.html
            arg = [tcp_flag_specials[key]]
            key = 'tcp-flags'
        elif key == 'tcp-flags':
            pass
        elif key == 'ip-options':
            arg = map(do_ip_option_lookup, arg)
            check_range(arg, 0, 255)
        elif key in ('first-fragment', 'is-fragment'):
            arg = []
        elif key == 'dscp':
            pass
        elif key == 'precedence':
            pass
        else:
            raise exceptions.UnknownMatchType('unknown match type "%s"' % key)

        arg = RangeList(arg)

        replacing = [key, key+'-except']
        for type in ('port', 'address', 'prefix-list'):
            if key == type:
                for sd in ('source', 'destination'):
                    replacing += [sd+'-'+type, sd+'-'+type+'-except']
        for k in replacing:
            try: del self[k]
            except KeyError: pass
        if (negated):
            super(Matches, self).__setitem__(key + '-except', arg)
        else:
            super(Matches, self).__setitem__(key, arg)

    def junos_str(self, pair):
        """
        Convert a 2-tuple into a hyphenated string, e.g. a range of ports. If
        not a tuple, tries to treat it as IPs or failing that, casts it to a
        string.

        :param pair:
            The 2-tuple to convert.
        """
        try:
            return '%s-%s' % pair # Tuples back to ranges.
        except TypeError:
            try:
                # Make it print prefixes for /32, /128
                pair.NoPrefixForSingleIp = False
            except AttributeError:
                pass
        return str(pair)

    def ios_port_str(self, ports):
        """
        Convert a list of tuples back to ranges, then to strings.

        :param ports:
            A list of port tuples, e.g. [(0,65535), (1,2)].
        """
        a = []
        for port in ports:
            try:
                if port[0] == 0:
                    # Omit ports if 0-65535
                    if port[1] == 65535:
                        continue
                    a.append('lt %s' % (port[1]+1))
                elif port[1] == 65535:
                    a.append('gt %s' % (port[0]-1))
                else:
                    a.append('range %s %s' % port)
            except TypeError:
                a.append('eq %s' % str(port))
        return a

    def ios_address_str(self, addrs):
        """
        Convert a list of addresses to IOS-style stupid strings.

        :param addrs:
            List of IP address objects.
        """
        a = []
        for addr in addrs:
            # xxx flag negated addresses?
            if addr.negated:
                raise exceptions.VendorSupportLacking(
                    'negated addresses are not supported in IOS')
            if addr.prefixlen() == 0:
                a.append('any')
            elif addr.prefixlen() == 32:
                a.append('host %s' % addr.net())
            else:
                inverse_mask = make_inverse_mask(addr.prefixlen())
                a.append('%s %s' % (addr.net(), inverse_mask))
        return a

    def output_junos(self):
        """Return a list that can form the ``from { ... }`` clause of the term."""
        a = []
        keys = self.keys()
        keys.sort(lambda x, y: cmp(junos_match_order[x], junos_match_order[y]))
        for s in keys:
            matches = map(self.junos_str, self[s])
            has_negated_addrs = any(m for m in matches if m.endswith(' except'))
            if s in address_matches:
                # Check to see if any of the added is any, and if so break out,
                # but only if none of the addresses is "negated".
                if '0.0.0.0/0' in matches and not has_negated_addrs:
                    continue
                a.append(s + ' {')
                a += ['    ' + x + ';' for x in matches]
                a.append('}')
                continue
            if s == 'tcp-flags' and len(self[s]) == 1:
                try:
                    a.append(tcp_flag_rev[self[s][0]] + ';')
                    continue
                except KeyError:
                    pass
            if len(matches) == 1:
                s += ' ' + matches[0]
            elif len(matches) > 1:
                s += ' [ ' + ' '.join(matches) + ' ]'
            a.append(s + ';')
        return a

    def output_ios(self):
        """Return a string of IOS ACL bodies."""
        # This is a mess!  Thanks, Cisco.
        protos = []
        sources = []
        dests = []
        sourceports = []
        destports = []
        trailers = []
        for key, arg in self.iteritems():
            if key == 'source-port':
                sourceports += self.ios_port_str(arg)
            elif key == 'destination-port':
                destports += self.ios_port_str(arg)
            elif key == 'source-address':
                sources += self.ios_address_str(arg)
            elif key == 'destination-address':
                dests += self.ios_address_str(arg)
            elif key == 'protocol':
                protos += map(str, arg)
            elif key == 'icmp-type':
                for type in arg.expanded():
                    if 'icmp-code' in self:
                        for code in self['icmp-code']:
                            try:
                                destports.append(ios_icmp_names[(type, code)])
                            except KeyError:
                                destports.append('%d %d' % (type, code))
                    else:
                        try:
                            destports.append(ios_icmp_names[(type,)])
                        except KeyError:
                            destports.append(str(type))
            elif key == 'icmp-code':
                if 'icmp-type' not in self:
                    raise exceptions.VendorSupportLacking('need ICMP code w/type')
            elif key == 'tcp-flags':
                if arg != [tcp_flag_specials['tcp-established']]:
                    raise exceptions.VendorSupportLacking('IOS supports only "tcp-flags established"')
                trailers += ['established']
            else:
                raise exceptions.VendorSupportLacking('"%s" not in IOS' % key)
        if not protos:
            protos = ['ip']
        if not sources:
            sources = ['any']
        if not dests:
            dests = ['any']
        if not sourceports:
            sourceports = ['']
        if not destports:
            destports = ['']
        if not trailers:
            trailers = ['']
        a = []

        # There is no mercy in this Dojo!!
        for proto in protos:
            for source in sources:
                for sourceport in sourceports:
                    for dest in dests:
                        for destport in destports:
                            for trailer in trailers:
                                s = proto + ' ' + source
                                if sourceport:
                                    s += ' ' + sourceport
                                s += ' ' + dest
                                if destport:
                                    s += ' ' + destport
                                if trailer:
                                    s += ' ' + trailer
                                a.append(s)
        return a


#
# Here begins the parsing code.  Break this into another file?
#

# Each production can be any of:
# 1. string
#    if no subtags: -> matched text
#    if single subtag: -> value of that
#    if list: -> list of the value of each tag
# 2. (string, object) -> object
# 3. (string, callable_object) -> object(arg)

subtagged = set()
def S(prod):
    """
    Wrap your grammar token in this to call your helper function with a list
    of each parsed subtag, instead of the raw text. This is useful for
    performing modifiers.

    :param prod: The parser product.
    """
    subtagged.add(prod)
    return prod

def literals(d):
    '''Longest match of all the strings that are keys of 'd'.'''
    keys = [str(key) for key in d]
    keys.sort(lambda x, y: len(y) - len(x))
    return ' / '.join(['"%s"' % key for key in keys])

def update(d, **kwargs):
    # Check for duplicate subterms, which is legal but too confusing to be
    # allowed at AOL.  For example, a Juniper term can have two different
    # 'destination-address' clauses, which means that the first will be
    # ignored.  This led to an outage on 2006-10-11.
    for key in kwargs.iterkeys():
        if key in d:
            raise exceptions.ParseError('duplicate %s' % key)
    d.update(kwargs)
    return d

def dict_sum(dlist):
    dsum = {}
    for d in dlist:
        for k, v in d.iteritems():
            if k in dsum:
                dsum[k] += v
            else:
                dsum[k] = v
    return dsum

## syntax error messages
errs = {
    'comm_start': '"comment missing /* below line %(line)s"',
    'comm_stop':  '"comment missing */ below line %(line)s"',
    'default':    '"expected %(expected)s line %(line)s"',
    'semicolon':  '"missing semicolon on line %(line)s"',
}

rules = {
    'digits':     '[0-9]+',
    '<digits_s>': '[0-9]+',
    '<ts>':       '[ \\t]+',
    '<ws>':       '[ \\t\\n]+',
    '<EOL>':      "('\r'?,'\n')/EOF",
    'alphanums':  '[a-zA-Z0-9]+',
    'word':       '[a-zA-Z0-9_.-]+',
    'anychar':    "[ a-zA-Z0-9.$:()&,/'_-]",
    'hex':        '[0-9a-fA-F]+',
    'ipchars':    '[0-9a-fA-F:.]+',

    'ipv4':       ('digits, (".", digits)*', TIP),
    'ipaddr':     ('ipchars', TIP),
    'cidr':       ('("inactive:", ws+)?, (ipaddr / ipv4), "/", digits, (ws+, "except")?', TIP),
    'macaddr':    'hex, (":", hex)+',
    'protocol':   (literals(Protocol.name2num) + ' / digits',
                   do_protocol_lookup),
    'tcp':        ('"tcp" / "6"', Protocol('tcp')),
    'udp':        ('"udp" / "17"', Protocol('udp')),
    'icmp':       ('"icmp" / "1"', Protocol('icmp')),
    'icmp_type':  (literals(icmp_types) + ' / digits', do_icmp_type_lookup),
    'icmp_code':  (literals(icmp_codes) + ' / digits', do_icmp_code_lookup),
    'port':       (literals(ports) + ' / digits', do_port_lookup),
    'dscp':       (literals(dscp_names) + ' / digits', do_dscp_lookup),
    'root':       'ws?, junos_raw_acl / junos_replace_family_acl / junos_replace_acl / junos_replace_policers / ios_acl, ws?',
}


#
# IOS-like ACLs.
#


def make_inverse_mask(prefixlen):
    """
    Return an IP object of the inverse mask of the CIDR prefix.

    :param prefixlen:
        CIDR prefix
    """
    inverse_bits = 2 ** (32 - prefixlen) - 1
    return TIP(inverse_bits)


# Build a table to unwind Cisco's weird inverse netmask.
# TODO (jathan): These don't actually get sorted properly, but it doesn't seem
# to have mattered up until now. Worth looking into it at some point, though.
inverse_mask_table = dict([(make_inverse_mask(x), x) for x in range(0, 33)])

def handle_ios_match(a):
    protocol, source, dest = a[:3]
    extra = a[3:]

    match = Matches()
    modifiers = Modifiers()

    if protocol:
        match['protocol'] = [protocol]

    for sd, arg in (('source', source), ('destination', dest)):
        if isinstance(arg, list):
            if arg[0] is not None:
                match[sd + '-address'] = [arg[0]]
            match[sd + '-port'] = arg[1]
        else:
            if arg is not None:
                match[sd + '-address'] = [arg]

    if 'log' in extra:
        modifiers['syslog'] = True
        extra.remove('log')

    if protocol == 'icmp':
        if len(extra) > 2:
            raise NotImplementedError(extra)
        if extra and isinstance(extra[0], tuple):
            extra = extra[0]
        if len(extra) >= 1:
            match['icmp-type'] = [extra[0]]
        if len(extra) >= 2:
            match['icmp-code'] = [extra[1]]
    elif protocol == 'tcp':
        if extra == ['established']:
            match['tcp-flags'] = [tcp_flag_specials['tcp-established']]
        elif extra:
            raise NotImplementedError(extra)
    elif extra:
        raise NotImplementedError(extra)

    return {'match': match, 'modifiers': modifiers}

def handle_ios_acl(rows):
    acl = ACL()
    for d in rows:
        if not d:
            continue
        for k, v in d.iteritems():
            if k == 'no':
                acl = ACL()
            elif k == 'name':
                if acl.name:
                    if v != acl.name:
                        raise exceptions.ACLNameError("Name '%s' does not match ACL '%s'" % (v, acl.name))
                else:
                    acl.name = v
            elif k == 'term':
                acl.terms.append(v)
            elif k == 'format':
                acl.format = v
            # Brocade receive-acl
            elif k == 'receive_acl':
                acl.is_receive_acl = True
            else:
                raise RuntimeError('unknown key "%s" (value %s)' % (k, v))
    # In traditional ACLs, comments that belong to the first ACE are
    # indistinguishable from comments that belong to the ACL.
    #if acl.format == 'ios' and acl.terms:
    if acl.format in ('ios', 'ios_brocade') and acl.terms:
        acl.comments += acl.terms[0].comments
        acl.terms[0].comments = []
    return acl

unary_port_operators = {
    'eq':   lambda x: [x],
    'le':   lambda x: [(0, x)],
    'lt':   lambda x: [(0, x-1)],
    'ge':   lambda x: [(x, 65535)],
    'gt':   lambda x: [(x+1, 65535)],
    'neq':  lambda x: [(0, x-1), (x+1, 65535)]
}

rules.update({
    'ios_ip':                    'kw_any / host_ipv4 / ios_masked_ipv4',
    'kw_any':                    ('"any"', None),
    'host_ipv4':            '"host", ts, ipv4',
    S('ios_masked_ipv4'):   ('ipv4, ts, ipv4_inverse_mask',
                             lambda (net, length): TIP('%s/%d' % (net, length))),
    'ipv4_inverse_mask':    (literals(inverse_mask_table),
                             lambda x: inverse_mask_table[TIP(x)]),

    'kw_ip':                    ('"ip"', None),
    S('ios_match'):            ('kw_ip / protocol, ts, ios_ip, ts, ios_ip, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_tcp_port_match'):('tcp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, established)?, (ts, ios_log)?',
                             handle_ios_match),
    S('ios_udp_port_match'):('udp, ts, ios_ip_port, ts, ios_ip_port, '
                             '(ts, ios_log)?',
                             handle_ios_match),
    S('ios_ip_port'):            'ios_ip, (ts, unary_port / ios_range)?',
    S('unary_port'):            ('unary_port_operator, ts, port',
                             lambda (op, arg): unary_port_operators[op](arg)),
    'unary_port_operator':  literals(unary_port_operators),
    S('ios_range'):            ('"range", ts, port, ts, port',
                             lambda (x, y): [(x, y)]),
    'established':            '"established"',
    S('ios_icmp_match'):    ('icmp, ts, ios_ip, ts, ios_ip, (ts, ios_log)?, '
                             '(ts, ios_icmp_message / '
                             ' (icmp_type, (ts, icmp_code)?))?, (ts, ios_log)?',
                             handle_ios_match),
    'ios_icmp_message':     (literals(ios_icmp_messages),
                             lambda x: ios_icmp_messages[x]),

    'ios_action':            '"permit" / "deny"',
    'ios_log':                    '"log-input" / "log"',
    S('ios_action_match'):  ('ios_action, ts, ios_tcp_port_match / '
                             'ios_udp_port_match / ios_icmp_match / ios_match',
                             lambda x: {'term': Term(action=x[0], **x[1])}),

    'ios_acl_line':            'ios_acl_match_line / ios_acl_no_line',
    S('ios_acl_match_line'):('"access-list", ts, digits, ts, ios_action_match',
                             lambda x: update(x[1], name=x[0], format='ios')),
    S('ios_acl_no_line'):   ('"no", ts, "access-list", ts, digits',
                             lambda x: {'no': True, 'name': x[0]}),

    'ios_ext_line':          ('ios_action_match / ios_ext_name_line / '
                             'ios_ext_no_line / ios_remark_line / '
                             'ios_rebind_acl_line / ios_rebind_receive_acl_line'),
    S('ios_ext_name_line'): ('"ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'name': x[0], 'format': 'ios_named'}),
    S('ios_ext_no_line'):   ('"no", ts, "ip", ts, "access-list", ts, '
                             '"extended", ts, word',
                             lambda x: {'no': True, 'name': x[0]}),
    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_acl_line'): ('"ip", ts, "rebind-acl", ts, word',
                              lambda x: {'name': x[0], 'format': 'ios_brocade'}),

    # Brocade "ip rebind-acl foo" or "ip rebind-receive-acl foo" syntax
    S('ios_rebind_receive_acl_line'): ('"ip", ts, "rebind-receive-acl", ts, word',
                                lambda x: {'name': x[0], 'format': 'ios_brocade',
                                           'receive_acl': True}),

    S('icomment'):            ('"!", ts?, icomment_body', lambda x: x),
    'icomment_body':            ('-"\n"*', Comment),
    S('ios_remark_line'):   ('("access-list", ts, digits_s, ts)?, "remark", ts, remark_body', lambda x: x),
    'remark_body':            ('-"\n"*', Remark),

    '>ios_line<':            ('ts?, (ios_acl_line / ios_ext_line / "end")?, '
                             'ts?, icomment?'),
    S('ios_acl'):            ('(ios_line, "\n")*, ios_line', handle_ios_acl),
})


#
# JunOS parsing
#


class QuotedString(str):
    def __str__(self):
        return '"' + self + '"'

def juniper_multiline_comments():
    """
    Return appropriate multi-line comment grammar for Juniper ACLs.

    This depends on ``settings.ALLOW_JUNIPER_MULTLIINE_COMMENTS``.
    """
    single = '-("*/" / "\n")*' # single-line comments only
    multi = '-"*/"*' # syntactically correct multi-line support
    if settings.ALLOW_JUNIPER_MULTILINE_COMMENTS:
        return multi
    return single

rules.update({
    'jword':                    'double_quoted / word',
    'double_quoted':            ('"\\"", -[\\"]+, "\\""',
                                 lambda x: QuotedString(x[1:-1])),

    #'>jws<':                    '(ws / jcomment)+',
    #S('jcomment'):              ('"/*", ws?, jcomment_body, ws?, "*/"',
    #                            lambda x: Comment(x[0])),
    #'jcomment_body':            '-(ws?, "*/")*',

    '>jws<':                    '(ws / jcomment)+',
    S('jcomment'):              ('jslashbang_comment',
                                 lambda x: Comment(x[0])),
    '<comment_start>':          '"/*"',
    '<comment_stop>':           '"*/"',
    '>jslashbang_comment<':     'comment_start, jcomment_body, !%s, comment_stop' % errs['comm_stop'],

    'jcomment_body':            juniper_multiline_comments(),

    # Errors on missing ';', ignores multiple ;; and normalizes to one.
    '<jsemi>':                  'jws?, [;]+!%s' % errs['semicolon'],

    'fragment_flag':            literals(fragment_flag_names),
    'ip_option':                "digits / " + literals(ip_option_names),
    'tcp_flag':                 literals(tcp_flag_names),
})

junos_match_types = []

def braced_list(arg):
    '''Returned braced output.  Will alert if comment is malformed.'''
    #return '("{", jws?, (%s, jws?)*, "}")' % arg
    return '("{", jws?, (%s, jws?)*, "}"!%s)' % (arg, errs['comm_start'])

def keyword_match(keyword, arg=None):
    for k in keyword, keyword+'-except':
        prod = 'junos_' + k.replace('-', '_')
        junos_match_types.append(prod)
        if arg is None:
            rules[prod] = ('"%s", jsemi' % k, {k: True})
        else:
            tokens = '"%s", jws, ' % k
            if k in address_matches:
                tokens += braced_list(arg + ', jsemi')
            else:
                tokens += arg + ', jsemi'
            rules[S(prod)] = (tokens, lambda x, k=k: {k: x})

keyword_match('address', 'cidr / ipaddr')
keyword_match('destination-address', 'cidr / ipaddr')
keyword_match('destination-prefix-list', 'jword')
keyword_match('first-fragment')
keyword_match('fragment-flags', 'fragment_flag')
keyword_match('ip-options', 'ip_option')
keyword_match('is-fragment')
keyword_match('prefix-list', 'jword')
keyword_match('source-address', 'cidr / ipaddr')
keyword_match('source-prefix-list', 'jword')
keyword_match('tcp-established')
keyword_match('tcp-flags', 'tcp_flag')
keyword_match('tcp-initial')

def range_match(key, arg):
    rules[S(arg+'_range')] = ('%s, "-", %s' % (arg, arg), tuple)
    match = '%s_range / %s' % (arg, arg)
    keyword_match(key, '%s / ("[", jws?, (%s, jws?)*, "]")' % (match, match))

range_match('ah-spi', 'alphanums')
range_match('destination-mac-address', 'macaddr')
range_match('destination-port', 'port')
range_match('dscp', 'dscp')
range_match('ether-type', 'alphanums')
range_match('esp-spi', 'alphanums')
range_match('forwarding-class', 'jword')
range_match('fragment-offset', 'port')
range_match('icmp-code', 'icmp_code')
range_match('icmp-type', 'icmp_type')
range_match('interface-group', 'digits')
range_match('packet-length', 'digits')
range_match('port', 'port')
range_match('precedence', 'jword')
range_match('protocol', 'protocol')
range_match('source-mac-address', 'macaddr')
range_match('source-port', 'port')
range_match('vlan-ether-type', 'alphanums')

def handle_junos_acl(x):
    """
    Parse JUNOS ACL and return an ACL object populated with Term and Policer
    objects.

    It's expected that x is a 2-tuple of (name, terms) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """
    a = ACL(name=x[0], format='junos')
    for elt in x[1:]:
        # Handle dictionary args we throw at the constructor
        if isinstance(elt, dict):
            a.__dict__.update(elt)
        elif isinstance(elt, Term):
            a.terms.append(elt)
        elif isinstance(elt, Policer):
            a.policers.append(elt)
        else:
            raise RuntimeError('Bad Object: %s' % repr(elt))
    return a

def handle_junos_family_acl(x):
    """
    Parses a JUNOS acl that contains family information and sets the family
    attribute for the ACL object.

    It's expected that x is a 2-tuple of (family, aclobj) returned from the
    parser.

    Don't forget to wrap your token in S()!
    """
    family, aclobj = x
    setattr(aclobj, 'family', family)
    return aclobj

def handle_junos_policers(x):
    """Parse JUNOS policers and return a PolicerGroup object"""
    p = PolicerGroup(format='junos')
    for elt in x:
        if isinstance(elt, Policer):
            p.policers.append(elt)
        else:
            raise RuntimeError('bad object: %s in policer' % repr(elt))
    return p

def handle_junos_term(d):
    """Parse a JUNOS term and return a Term object"""
    if 'modifiers' in d:
        d['modifiers'] = Modifiers(d['modifiers'])
    return Term(**d)


# Note there cannot be jws (including comments) before or after the "filter"
# section of the config.  It's wrong to do this anyway, since if you load
# that config onto the router, the comments will not remain in place on
# the next load of a similar config (e.g., another ACL).  I had a workaround
# for this but it made the parser substantially slower.
rules.update({
    S('junos_raw_acl'):         ('jws?, "filter", jws, jword, jws?, ' + \
                                 braced_list('junos_iface_specific / junos_term / junos_policer'),
                                 handle_junos_acl),
    'junos_iface_specific':     ('("interface-specific", jsemi)',
                                 lambda x: {'interface_specific': len(x) > 0}),
    'junos_replace_acl':        ('jws?, "firewall", jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}"'),
    S('junos_replace_family_acl'): ('jws?, "firewall", jws?, "{", jws?, junos_filter_family, jws?, "{", jws?, "replace:", jws?, (junos_raw_acl, jws?)*, "}", jws?, "}"',
                                 handle_junos_family_acl),
    S('junos_replace_policers'):('"firewall", jws?, "{", jws?, "replace:", jws?, (junos_policer, jws?)*, "}"',
                                    handle_junos_policers),
    'junos_filter_family':      ('"family", ws, junos_family_type'),
    'junos_family_type':        ('"inet" / "inet6" / "ethernet-switching"'),
    'opaque_braced_group':      ('"{", jws?, (jword / "[" / "]" / ";" / '
                                    'opaque_braced_group / jws)*, "}"',
                                    lambda x: x),
    S('junos_term'):            ('maybe_inactive, "term", jws, junos_term_name, '
                                    'jws?, ' + braced_list('junos_from / junos_then'),
                                    lambda x: handle_junos_term(dict_sum(x))),
    S('junos_term_name'):       ('jword', lambda x: {'name': x[0]}),
    'maybe_inactive':           ('("inactive:", jws)?',
                                    lambda x: {'inactive': len(x) > 0}),
    S('junos_from'):            ('"from", jws?, ' + braced_list('junos_match'),
                                    lambda x: {'match': Matches(dict_sum(x))}),
    S('junos_then'):            ('junos_basic_then / junos_braced_then', dict_sum),
    S('junos_braced_then'):     ('"then", jws?, ' +
                                    braced_list('junos_action/junos_modifier, jsemi'),
                                    dict_sum),
    S('junos_basic_then'):      ('"then", jws?, junos_action, jsemi', dict_sum),
    S('junos_policer'):         ('"policer", jws, junos_term_name, jws?, ' +
                                    braced_list('junos_exceeding / junos_policer_then'),
                                    lambda x: Policer(x[0]['name'], x[1:])),
    S('junos_policer_then'):    ('"then", jws?, ' +
                                    braced_list('junos_policer_action, jsemi')),
    S('junos_policer_action'):  ('junos_discard / junos_fwd_class / '\
                                    '("loss-priority", jws, jword)',
                                    lambda x: {'action':x}),
    'junos_discard':            ('"discard"'),
    'junos_loss_pri':           ('"loss-priority", jws, jword',
                                    lambda x: {'loss-priority':x[0]}),
    'junos_fwd_class':          ('"forwarding-class", jws, jword',
                                    lambda x: {'forwarding-class':x[0]}),
    'junos_filter_specific':    ('"filter-specific"'),
    S('junos_exceeding'):       ('"if-exceeding", jws?, ' +
                                    braced_list('junos_bw_limit/junos_bw_perc/junos_burst_limit'),
                                    lambda x: {'if-exceeding':x}),
    S('junos_bw_limit'):        ('"bandwidth-limit", jws, word, jsemi',
                                    lambda x: ('bandwidth-limit',x[0])),
    S('junos_bw_perc'):         ('"bandwidth-percent", jws, alphanums, jsemi',
                                    lambda x: ('bandwidth-percent',x[0])),
    S('junos_burst_limit'):     ('"burst-size-limit", jws, alphanums, jsemi',
                                    lambda x: ('burst-size-limit',x[0])),
    S('junos_match'):           (' / '.join(junos_match_types), dict_sum),

    S('junos_action'):          ('junos_one_action / junos_reject_action /'
                                    'junos_reject_action / junos_ri_action',
                                    lambda x: {'action': x[0]}),
    'junos_one_action':         ('"accept" / "discard" / "reject" / '
                                    '("next", jws, "term")'),
    'junos_reject_action':      ('"reject", jws, ' + literals(icmp_reject_codes),
                                    lambda x: ('reject', x)),
    S('junos_ri_action'):       ('"routing-instance", jws, jword',
                                    lambda x: ('routing-instance', x[0])),
    S('junos_modifier'):        ('junos_one_modifier / junos_arg_modifier',
                                    lambda x: {'modifiers': x}),
    'junos_one_modifier':       ('"log" / "sample" / "syslog" / "port-mirror"',
                                    lambda x: (x, True)),
    S('junos_arg_modifier'):    'junos_arg_modifier_kw, jws, jword',
    'junos_arg_modifier_kw':    ('"count" / "forwarding-class" / "ipsec-sa" /'
                                    '"loss-priority" / "policer"'),
})

#
# Parsing infrastructure
#

class ACLProcessor(DispatchProcessor):
    pass

def strip_comments(tags):
    if tags is None:
        return
    noncomments = []
    for tag in tags:
        if isinstance(tag, Comment):
            Comments.append(tag)
        else:
            noncomments.append(tag)
    return noncomments

def default_processor(self, (tag, start, stop, subtags), buffer):
    if not subtags:
        return buffer[start:stop]
    elif len(subtags) == 1:
        return dispatch(self, subtags[0], buffer)
    else:
        return dispatchList(self, subtags, buffer)

def make_nondefault_processor(action):
    if callable(action):
        def processor(self, (tag, start, stop, subtags), buffer):
            if tag in subtagged:
                results = [getattr(self, subtag[0])(subtag, buffer)
                           for subtag in subtags]
                return action(strip_comments(results))
            else:
                return action(buffer[start:stop])
    else:
        def processor(self, (tag, start, stop, subtags), buffer):
            return action

    return processor

grammar = []
for production, rule in rules.iteritems():
    if isinstance(rule, tuple):
        assert len(rule) == 2
        setattr(ACLProcessor, production, make_nondefault_processor(rule[1]))
        grammar.append('%s := %s' % (production, rule[0]))
    else:
        setattr(ACLProcessor, production, default_processor)
        grammar.append('%s := %s' % (production, rule))

grammar = '\n'.join(grammar)

class ACLParser(Parser):
    def buildProcessor(self):
        return ACLProcessor()

###parser = ACLParser(grammar)

def parse(input_data):
    """
    Parse a complete ACL and return an ACL object. This should be the only
    external interface to the parser.

    >>> from trigger.acl import parse
    >>> aclobj = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")
    >>> aclobj.terms
    [<Term: None>]

    :param input_data:
        An ACL policy as a string or file-like object.
    """
    parser = ACLParser(grammar)

    try:
        data = input_data.read()
    except AttributeError:
        data = input_data

    ## parse the acl
    success, children, nextchar = parser.parse(data)

    if success and nextchar == len(data):
        assert len(children) == 1
        return children[0]
    else:
        line = data[:nextchar].count('\n') + 1
        column = len(data[data[nextchar].rfind('\n'):nextchar]) + 1
        raise exceptions.ParseError('Could not match syntax.  Please report as a bug.', line, column)

########NEW FILE########
__FILENAME__ = queue
# -*- coding: utf-8 -*-

"""
Database interface for automated ACL queue. Used primarily by ``load_acl`` and
``acl``` commands for manipulating the work queue.

    >>> from trigger.acl.queue import Queue
    >>> q = Queue()
    >>> q.list()
    (('dc1-abc.net.aol.com', 'datacenter-protect'), ('dc2-abc.net.aol.com',
    'datacenter-protect'))
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__version__ = '2.0.1'


import datetime
import os
import sys
from trigger import exceptions
from trigger.conf import settings
from trigger.netdevices import NetDevices
from trigger.utils import get_user
from . import models


# Globals
QUEUE_NAMES = ('integrated', 'manual')


# Exports
__all__ = ('Queue',)


# Classes
class Queue(object):
    """
    Interacts with firewalls database to insert/remove items into the queue.

    :param verbose:
        Toggle verbosity

    :type verbose:
        Boolean
    """
    def __init__(self, verbose=True):
        self.nd = NetDevices()
        self.verbose = verbose
        self.login = get_user()

    def vprint(self, msg):
        """
        Print something if ``verbose`` instance variable is set.

        :param msg:
            The string to print
        """
        if self.verbose:
            print msg

    def get_model(self, queue):
        """
        Given a queue name, return its DB model.

        :param queue:
            Name of the queue whose object you want
        """
        return models.MODEL_MAP.get(queue, None)

    def create_task(self, queue, *args, **kwargs):
        """
        Create a task in the specified queue.

        :param queue:
            Name of the queue whose object you want
        """
        model = self.get_model(queue)
        taskobj = model.create(*args, **kwargs)

    def _normalize(self, arg, prefix=''):
        """
        Remove ``prefix`` from ``arg``, and set "escalation" bit.

        :param arg:
            Arg (typically an ACL filename) to trim

        :param prefix:
            Prefix to trim from arg
        """
        if arg.startswith(prefix):
            arg = arg[len(prefix):]
        escalation = False
        if arg.upper().endswith(' ESCALATION'):
            escalation = True
            arg = arg[:-11]
        return (escalation, arg)

    def insert(self, acl, routers, escalation=False):
        """
        Insert an ACL and associated devices into the ACL load queue.

        Attempts to insert into integrated queue. If ACL test fails, then
        item is inserted into manual queue.

        :param acl:
            ACL name

        :param routers:
            List of device names

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to insert into the queue')
        if not routers:
            routers = []

        escalation, acl = self._normalize(acl)
        if routers:
            for router in routers:
                try:
                    dev = self.nd.find(router)
                except KeyError:
                    msg = 'Could not find device %s' % router
                    raise exceptions.TriggerError(msg)

                if acl not in dev.acls:
                    msg = "Could not find %s in ACL list for %s" % (acl, router)
                    raise exceptions.TriggerError(msg)

                self.create_task(queue='integrated', acl=acl, router=router,
                                 escalation=escalation)

            self.vprint('ACL %s injected into integrated load queue for %s' %
                        (acl, ', '.join(dev[:dev.find('.')] for dev in routers)))

        else:
            self.create_task(queue='manual', q_name=acl, login=self.login)
            self.vprint('"%s" injected into manual load queue' % acl)

    def delete(self, acl, routers=None, escalation=False):
        """
        Delete an ACL from the firewall database queue.

        Attempts to delete from integrated queue. If ACL test fails
        or if routers are not specified, the item is deleted from manual queue.

        :param acl:
            ACL name

        :param routers:
            List of device names. If this is ommitted, the manual queue is used.

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to delete from the queue')

        escalation, acl = self._normalize(acl)
        m = self.get_model('integrated')

        if routers is not None:
            devs = routers
        else:
            self.vprint('Fetching routers from database')
            result = m.select(m.router).distinct().where(
                              m.acl == acl, m.loaded >> None).order_by(m.router)
            rows = result.tuples()
            devs = [row[0] for row in rows]

        if devs:
            for dev in devs:
                m.delete().where(m.acl == acl, m.router == dev,
                                 m.loaded >> None).execute()

            self.vprint('ACL %s cleared from integrated load queue for %s' %
                        (acl, ', '.join(dev[:dev.find('.')] for dev in devs)))
            return True

        else:
            m = self.get_model('manual')
            if m.delete().where(m.q_name == acl, m.done == False).execute():
                self.vprint('%r cleared from manual load queue' % acl)
                return True

        self.vprint('%r not found in any queues' % acl)
        return False

    def complete(self, device, acls):
        """
        Mark a device and its ACLs as complete using current timestamp.

        (Integrated queue only.)

        :param device:
            Device names

        :param acls:
            List of ACL names
        """
        m = self.get_model('integrated')
        for acl in acls:
            now = loaded=datetime.datetime.now()
            m.update(loaded=now).where(m.acl == acl, m.router == device,
                                       m.loaded >> None).execute()

        self.vprint('Marked the following ACLs as complete for %s:' % device)
        self.vprint(', '.join(acls))

    def remove(self, acl, routers, escalation=False):
        """
        Integrated queue only.

        Mark an ACL and associated devices as "removed" (loaded=0). Intended
        for use when performing manual actions on the load queue when
        troubleshooting or addressing errors with automated loads. This leaves
        the items in the database but removes them from the active queue.

        :param acl:
            ACL name

        :param routers:
            List of device names

        :param escalation:
            Whether this is an escalated task
        """
        if not acl:
            raise exceptions.ACLQueueError('You must specify an ACL to remove from the queue')

        m = self.get_model('integrated')
        loaded = 0
        if settings.DATABASE_ENGINE == 'postgresql':
            loaded = '-infinity' # See: http://bit.ly/15f0J3z
        for router in routers:
            m.update(loaded=loaded).where(m.acl == acl, m.router == router,
                                          m.loaded >> None).execute()

        self.vprint('Marked the following devices as removed for ACL %s: ' % acl)
        self.vprint(', '.join(routers))

    def list(self, queue='integrated', escalation=False, q_names=QUEUE_NAMES):
        """
        List items in the specified queue, defauls to integrated queue.

        :param queue:
            Name of the queue to list

        :param escalation:
            Whether this is an escalated task

        :param q_names:
            (Optional) List of valid queue names
        """
        if queue not in q_names:
            self.vprint('Queue must be one of %s, not: %s' % (q_names, queue))
            return False

        m = self.get_model(queue)

        if queue == 'integrated':
            result = m.select(m.router, m.acl).distinct().where(
                              m.loaded >> None, m.escalation == escalation)
        elif queue == 'manual':
            result = m.select(m.q_name, m.login, m.q_ts, m.done).where(
                              m.done == False)
        else:
            raise RuntimeError('This should never happen!!')

        all_data = list(result.tuples())
        return all_data

########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -*-

"""
Various tools for use in scripts or other modules. Heavy lifting from tools
that have matured over time have been moved into this module. 
"""

__author__ = 'Jathan McCollum, Eileen Tschetter'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2010-2011, AOL Inc.'

from collections import defaultdict
import datetime
import IPy
import os
import re
import sys
import tempfile
from trigger.acl.parser import *
from trigger.conf import settings


# Defaults
DEBUG = False
DATE_FORMAT = "%Y-%m-%d"
DEFAULT_EXPIRE = 6 * 30 # 6 months


# Exports
__all__ = ('create_trigger_term', 'create_access', 'check_access', 'ACLScript',
          'process_bulk_loads', 'get_bulk_acls', 'get_comment_matches', 
           'write_tmpacl', 'diff_files', 'worklog', 'insert_term_into_acl',
           'create_new_acl')


# Functions
def create_trigger_term(source_ips=[],
                       dest_ips=[],
                       source_ports=[],
                       dest_ports=[],
                       protocols=[], 
                       action=['accept'],
                       name="generated_term"):
    """Constructs & returns a Term object from constituent parts."""
    term = Term()
    term.action = action
    term.name = name
    for key, data in {'source-address': source_ips,
                     'destination-address': dest_ips,
                     'source-port': source_ports,
                     'destination-port': dest_ports,
                     'protocol': protocols}.iteritems():
        for n in data:
            if key in term.match:
                term.match[key].append(n)
            else:
                term.match[key] = [n] 
    return term

def check_access(terms_to_check, new_term, quiet=True, format='junos',
                 acl_name=None):
    """
    Determine whether access is permitted by a given ACL (list of terms).

    Tests a new term against a list of terms. Return True if access in new term
    is permitted, or False if not.

    Optionally displays the terms that apply and what edits are needed.

    :param terms_to_check:
        A list of Term objects to check

    :param new_term:
        The Term object used for the access test

    :param quiet:
        Toggle whether output is displayed

    :param format:
        The ACL format to use for output display

    :param acl_name:
        The ACL name to use for output display
    """
    permitted = None
    matches = {
        'source-address':       new_term.match.get('source-address',[]),
        'destination-address':  new_term.match.get('destination-address',[]),
        'protocol':             new_term.match.get('protocol',[]),
        'destination-port':     new_term.match.get('destination-port',[]),
        'source-port':          new_term.match.get('source-port',[]),
    }

    def _permitted_in_term(term, comment=' check_access: PERMITTED HERE'):
        """
        A little closure to re-use internally that returns a Boolean based
        on the given Term object's action.
        """
        action = term.action[0]
        if action == 'accept':
            is_permitted = True
            if not quiet:
                term.comments.append(Comment(comment))

        elif action in ('discard', 'reject'):
            is_permitted = False
            if not quiet:
                print '\n'.join(new_term.output(format, acl_name=acl_name))
        else:
            is_permitted = None

        return is_permitted

    for t in terms_to_check:
        hit = True
        complicated = False

        for comment in t.comments:
            if 'trigger: make discard' in comment:
                t.setaction('discard') #.action[0] = 'discard'
                t.makediscard = True # set 'make discard' flag

        for k,v in t.match.iteritems():

            if k not in matches or not matches[k]:
                complicated = True

            else:
                for test in matches[k]:
                    if test not in v:
                        hit = False
                        break

        if hit and not t.inactive:
            # Simple access check. Elegant!
            if not complicated and permitted is None:
                permitted = _permitted_in_term(t)

            # Complicated checks should set hit=False unless you want
            # them to display and potentially confuse end-users
            # TODO (jathan): Factor this into a "better way"
            else:
                # Does the term have 'port' defined?
                if 'port' in t.match:
                    port_match = t.match.get('port')
                    match_fields = (matches['destination-port'], matches['source-port'])

                    # Iterate the fields, and then the ports for each field. If
                    # one of the port numbers is within port_match, check if
                    # the action permits/denies and set the permitted flag.
                    for field in match_fields:
                        for portnum in field:
                            if portnum in port_match:
                                permitted = _permitted_in_term(t)
                            else:
                                hit = False

                # Other complicated checks would go here...

            # If a complicated check happened and was not a hit, skip to the
            # next term
            if complicated and not hit:
                continue

            if not quiet:
                print '\n'.join(t.output(format, acl_name=acl_name))

    return permitted

def create_access(terms_to_check, new_term):
    """
    Breaks a new_term up into separate constituent parts so that they can be 
    compared in a check_access test.
    
    Returns a list of terms that should be inserted.
    """
    protos      = new_term.match.get('protocol', ['any'])
    sources     = new_term.match.get('source-address', ['any'])
    dests       = new_term.match.get('destination-address', ['any'])
    sourceports = new_term.match.get('source-port', ['any'])
    destports   = new_term.match.get('destination-port', ['any'])
    
    ret = []
    for proto in protos:
        for source in sources:
            for sourceport in sourceports:
                for dest in dests:
                    for destport in destports:
                        t = Term()
                        if str(proto) != 'any':
                            t.match['protocol'] = [proto]
                        if str(source) != 'any':
                            t.match['source-address'] = [source]
                        if str(dest) != 'any':
                            t.match['destination-address'] = [dest]
                        if str(sourceport) != 'any':
                            t.match['source-port'] = [sourceport]
                        if str(destport) != 'any':
                            t.match['destination-port'] = [destport]
                        if not check_access(terms_to_check, t):
                            ret.append(t)

    return ret

# note, following code is -not currently used-
def insert_term_into_acl(new_term, aclobj, debug=False):
    """
    Return a new ACL object with the new_term added in the proper place based
    on the aclobj. Intended to recursively append to an interim ACL object
    based on a list of Term objects.

    It's safe to assume that this function is incomplete pending better
    documentation and examples.

    :param new_term:
        The Term object to use for comparison against aclobj

    :param aclobj:
        The original ACL object to use for creation of new_acl

    Example::

        import copy
        # terms_to_be_added is a list of Term objects that is to be added in
        # the "right place" into new_acl based on the contents of aclobj
        original_acl = parse(open('acl.original'))
        new_acl = copy.deepcopy(original_acl) # Dupe the original
        for term in terms_to_be_added:
            new_acl = generate_new_acl(term, new_acl)
    """
    new_acl = ACL() # ACL comes from trigger.acl.parser
    new_acl.policers = aclobj.policers
    new_acl.format   = aclobj.format
    new_acl.name     = aclobj.name
    already_added    = False

    for c in aclobj.comments:
        new_acl.comments.append(c)

    # The following logic is almost identical to that of check_access() except
    # that it tracks already_added and knows how to handle insertion of terms
    # before or after Terms with an action of 'discard' or 'reject'.
    for t in aclobj.terms:
        hit = True
        complicated = False
        permitted = None
        for k, v in t.match.iteritems():

            if debug:
                print "generate_new_acl(): k,v==",k,"and",v
            if k == 'protocol' and k not in new_term.match:
                continue
            if k not in new_term.match:
                complicated = True
                continue
            else:
                for test in new_term.match[k]:
                    if test not in v:
                        hit = False
                        break

            if not hit and k in ('source-port', 'destination-port',
                                 'source-address', 'destination-address'):
                # Here is where it gets odd: If we have multiple  IPs in this
                # new term, and one of them matches in a deny, we must set hit
                # to True.
                got_match = False
                if t.action[0] in ('discard', 'reject'):
                    for test in new_term.match[k]:
                        if test in v:
                            hit = True

        # Check whether access in new_term is permitted (a la check_access(),
        # track whether it's already been added into new_acl, and then add it
        # in the "right place".
        if hit and not t.inactive and already_added == False:
            if not complicated and permitted is None:
                for comment in t.comments:
                    if 'trigger: make discard' in comment and \
                        new_term.action[0] == 'accept':
                        new_acl.terms.append(new_term)
                        already_added = True
                        permitted = True
                if t.action[0] in ('discard','reject') and \
                   new_term.action[0] in ('discard','reject'):
                    permitted = False
                elif t.action[0] in ('discard','reject'):
                    permitted = False
                    new_acl.terms.append(new_term)
                    already_added = True
                elif t.action[0] == 'accept' and \
                     new_term.action[0] in ('discard', 'reject'):
                       permitted = False
                       new_acl.terms.append(new_term)
                       already_added = True
                elif t.action[0] == 'accept' and \
                     new_term.action[0] == 'accept':
                       permitted = True
        if debug:
            print "PERMITTED?", permitted

        # Original term is always appended as we move on
        new_acl.terms.append(t)

    return new_acl

def create_new_acl(old_file, terms_to_be_added):
    """Given a list of Term objects call insert_term_into_acl() to determine
    what needs to be added in based on the contents of old_file. Returns a new
    ACL object."""
    aclobj = parse(open(old_file)) # Start with the original ACL contents
    new_acl = None
    for new_term in terms_to_be_added:
        new_acl = insert_term_into_acl(new_term, aclobj)

    return new_acl

def get_bulk_acls():
    """
    Returns a dict of acls with an applied count over settings.AUTOLOAD_BULK_THRESH
    """
    from trigger.netdevices import NetDevices
    nd = NetDevices()
    all_acls = defaultdict(int)
    for dev in nd.all():
        for acl in dev.acls:
            all_acls[acl] += 1

    bulk_acls = {}
    for acl, count in all_acls.items():
        if count >= settings.AUTOLOAD_BULK_THRESH and acl != '':
            bulk_acls[acl] = count

    return bulk_acls

def process_bulk_loads(work, max_hits=settings.BULK_MAX_HITS_DEFAULT, force_bulk=False):
    """
    Formerly "process --ones".

    Processes work dict and determines tuple of (prefix, site) for each device.  Stores
    tuple as a dict key in prefix_hits. If prefix_hits[(prefix, site)] is greater than max_hits,
    remove all further matching devices from work dict.

    By default if a device has no acls flagged as bulk_acls, it is not removed from the work dict.

    Example:
        * Device 'foo1-xyz.example.com' returns ('foo', 'xyz') as tuple.
        * This is stored as prefix_hits[('foo', 'xyz')] = 1
        * All further devices matching that tuple increment the hits for that tuple
        * Any devices matching hit counter exceeds max_hits is removed from work dict

    You may override max_hits to increase the num. of devices on which to load a bulk acl.
    You may pass force_bulk=True to treat all loads as bulk loads.
    """

    prefix_pat = re.compile(r'^([a-z]+)\d{0,2}-([a-z0-9]+)')
    prefix_hits = defaultdict(int)
    import trigger.acl.db as adb
    bulk_acls = adb.get_bulk_acls()
    nd = adb.get_netdevices()

    if DEBUG:
        print 'DEVLIST:', sorted(work)

    # Sort devices numerically
    for dev in sorted(work):
        if DEBUG: print 'Doing', dev

        #testacls = dev.bulk_acls
        #if force_bulk:
        #    testacls = dev.acls
        testacls = dev.acls if force_bulk else dev.bulk_acls

        for acl in testacls:  #only look at each acl once, but look at all acls if bulk load forced
            if acl in work[dev]:
            #if acl in work[router]:
                if DEBUG: print 'Determining threshold for acl ', acl, ' on device ', dev, '\n'
                if acl in settings.BULK_MAX_HITS:
                    max_hits = settings.BULK_MAX_HITS[acl]

                try:
                    prefix_site = prefix_pat.findall(dev.nodeName)[0]
                except IndexError:
                    continue
                
                # Mark a hit for this tuple, and dump remaining matches
                prefix_hits[prefix_site] += 1

                if DEBUG: print prefix_site, prefix_hits[prefix_site]
                if prefix_hits[prefix_site] > max_hits:
                                
                    msg =  "Removing %s on %s from job queue: threshold of %d exceeded for " \
                           "'%s' devices in '%s'" % (acl, dev, max_hits, prefix_site[0], prefix_site[1])
                    print msg
                    if 'log' in globals():
                        log.msg(msg)

                    # Remove that acl from being loaded, but still load on that device
                    work[dev].remove(acl)
                    #work[router].remove(acl)

    #done with all the devices                
    return work

def get_comment_matches(aclobj, requests):
    """Given an ACL object and a list of ticket numbers return a list of matching comments."""
    matches = set()
    for t in aclobj.terms:
        for req in requests:
            for c in t.comments:
                if req in c:
                    matches.add(t)
            #[matches.add(t) for c in t.comments if req in c]

    return matches
    
def update_expirations(matches, numdays=DEFAULT_EXPIRE):
    """Update expiration dates on matching terms. This modifies mutable objects, so use cautiously."""
    print 'matching terms:', [term.name for term in matches]
    for term in matches:
        date = None
        for comment in term.comments:
            try:
                date = re.search(r'(\d{4}\-\d\d\-\d\d)', comment.data).group()
            except AttributeError:
                #print 'No date match in term: %s, comment: %s' % (term.name, comment)
                continue

            try:
                dstamp = datetime.datetime.strptime(date, DATE_FORMAT)
            except ValueError, err:
                print 'BAD DATE FOR THIS COMMENT:'
                print 'comment:', comment.data
                print 'bad date:', date
                print err
                print 'Fix the date and start the job again!'
                import sys
                sys.exit()
    
            new_date = dstamp + datetime.timedelta(days=numdays)
            #print 'Before:\n' + comment.data + '\n'
            print 'Updated date for term: %s' % term.name
            comment.data = comment.data.replace(date, datetime.datetime.strftime(new_date, DATE_FORMAT))
            #print 'After:\n' + comment.data

def write_tmpacl(acl, process_name='_tmpacl'):
    """Write a temporary file to disk from an Trigger acl.ACL object & return the filename"""
    tmpfile = tempfile.mktemp() + process_name
    f = open(tmpfile, 'w')
    for x in acl.output(acl.format, replace=True):
        f.write(x)
        f.write('\n')
    f.close()

    return tmpfile

def diff_files(old, new):
    """Return a unified diff between two files"""
    return os.popen('diff -Naur %s %s' % (old, new)).read()

def worklog(title, diff, log_string='updated by express-gen'):
    """Save a diff to the ACL worklog"""
    from time import strftime,localtime
    from trigger.utils.rcs import RCS

    date = strftime('%Y%m%d', localtime())
    file = os.path.join(settings.FIREWALL_DIR, 'workdocs', 'workdoc.' + date)
    rcs = RCS(file)

    if not os.path.isfile(file):
        print 'Creating new worklog %s' % file
        f = open(file,"w")
        f.write("# vi:noai:\n\n")
        f.close()
        rcs.checkin('.')

    print 'inserting the diff into the worklog %s' % file
    rcs.lock_loop()
    fd = open(file,"a")
    fd.write('"%s"\n' % title)
    fd.write(diff)
    fd.close()

    print 'inserting %s into the load queue' % title
    rcs.checkin(log_string)

    # Use acl to insert into queue, should be replaced with API call
    os.spawnlp(os.P_WAIT, 'acl', 'acl', '-i', title)


# Classes
class ACLScript:
    """
    Interface to generating or modifying access-lists. Intended for use in
    creating command-line utilities using the ACL API.
    """
    def __init__(self, acl=None, mode='insert', cmd='acl_script',
      show_mods=True, no_worklog=False, no_changes=False):
        self.source_ips   = []
        self.dest_ips     = []
        self.protocol     = []
        self.source_ports = []
        self.dest_ports   = []
        self.modify_terms = []
        self.bcomments    = []
        self.tempfiles    = []
        self.acl          = acl
        self.cmd          = cmd
        self.mode         = mode
        self.show_mods    = show_mods
        self.no_worklog   = no_worklog
        self.no_changes   = no_changes

    def cleanup(self):
        for file in self.tempfiles:
            os.remove(file)

    def genargs(self,interactive=False):
        if not self.acl:
            raise "need acl defined"

        argz = []
        argz.append('-a %s' % self.acl)

        if self.show_mods:
            argz.append('--show-mods')

        if self.no_worklog:
            argz.append('--no-worklog')

        if self.no_changes:
            argz.append('--no-changes')

        if not interactive:
            argz.append('--no-input')

        if self.mode == 'insert':
            argz.append('--insert-defined')

        elif self.mode == 'replace':
            argz.append('--replace-defined')

        else:
            raise "invalid mode"

        for k,v in {'--source-address-from-file':self.source_ips,
                    '--destination-address-from-file':self.dest_ips,
                   }.iteritems():
            if len(v) == 0:
                continue
            tmpf = tempfile.mktemp() + '_genacl'
            self.tempfiles.append(tmpf)
            try:
                f = open(tmpf,'w')
            except:
                print "UNABLE TO OPEN TMPFILE"
                raise "YIKES!"
            for x in v:
                f.write('%s\n' % x.strNormal())
            f.close()

            argz.append('%s %s' % (k,tmpf))

        for k,v in {'-p':self.source_ports,
                    '-P':self.dest_ports}.iteritems():

            if not len(v):
                continue

            for x in v:
                argz.append('%s %d' % (k,x))

        if len(self.modify_terms) and len(self.bcomments):
            print "Can only define either modify_terms or between comments"
            raise "Can only define either modify_terms or between comments"

        if self.modify_terms:
            for x in self.modify_terms:
                argz.append('-t %s' % x)
        else:
            for x in self.bcomments:
                (b,e) = x
                argz.append('-c "%s" "%s"' % (b,e))

        for proto in self.protocol:
            argz.append('--protocol %s' % proto)

        return argz

    def parselog(self, log):
        return log

    def run(self, interactive=False):
        args = self.genargs(interactive=interactive)
        log = []
        #print self.cmd + ' ' + ' '.join(args)
        if interactive:
            os.system(self.cmd + ' ' + ' '.join(args))
        else:
            f = os.popen(self.cmd + ' ' + ' '.join(args))
            line = f.readline()
            while line:
                line = line.rstrip()
                log.append(line)
                line = f.readline()
        return log

    def errors_from_log(self, log):
        errors = ''
        for l in log:
            if '%%ERROR%%' in l:
                l = l.spit('%%ERROR%%')[1]
                errors += l[1:] + '\n'
        return errors

    def diff_from_log(self, log):
        diff = ""
        for l in log:
            if '%%DIFF%%' in l:
                l = l.split('%%DIFF%%')[1]
                diff += l[1:] + '\n'
        return diff

    def set_acl(self, acl):
        self.acl=acl

    def _add_addr(self, to, src):
        if isinstance(src,list):
            for x in src:
                if IPy.IP(x) not in to:
                    to.append(IPy.IP(x))
        else:
            if IPy.IP(src) not in to:
                to.append(IPy.IP(src))

    def _add_port(self, to, src):
        if isinstance(src, list):
            for x in src:
                if x not in to:
                    to.append(int(x))
        else:
            if int(src) not in to:
                to.append(int(src))

    def add_protocol(self, src):
        to = self.protocol
        if isinstance(src, list):
            for x in src:
                if x not in to:
                    to.append(x)
        else:
            if src not in to:
                to.append(src)

    def add_src_host(self, data):
        self._add_addr(self.source_ips, data)

    def add_dst_host(self, data):
        self._add_addr(self.dest_ips, data)

    def add_src_port(self, data):
        self._add_port(self.source_ports, data)

    def add_dst_port(self, data):
        self._add_port(self.dest_ports, data)

    def add_modify_between_comments(self, begin, end):
        del self.modify_terms
        self.modify_terms = []
        self.bcomments.append((begin,end))

    def add_modify_term(self, term):
        del self.bcomments
        self.bcomments = []
        if term not in self.modify_terms:
            self.modify_terms.append(term)

    def get_protocols(self):
        return self.protocol

    def get_src_hosts(self):
        return self.source_ips

    def get_dst_hosts(self):
        return self.dest_ips

    def get_src_ports(self):
        return self.source_ports

    def get_dst_ports(self):
        return self.dest_ports

########NEW FILE########
__FILENAME__ = bounce
# -*- coding: utf-8 -*-

"""
This module controls how bounce windows get auto-applied to network devices.

This is primarily used by `~trigger.changemgmt`.

No changes should be made to this module. You must specify the path to the
bounce logic inside of ``settings.py`` as :setting:`BOUNCE_FILE`. This will be
exported as ``bounce()`` so that the module path for the :func:`bounce()`
function will still be `~trigger.changemgmt.bounce`.

This trickery allows us to keep the business-logic for how bounce windows are
mapped to devices out of the Trigger packaging.

If you do not specify a location for :setting:`BOUNCE_FILE`` or the module
cannot be loaded, then a default :func:`bounce()` function ill be used.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012, AOL Inc.'
__version__ = '0.1'


# Imports
from trigger.conf import settings
from trigger.utils.importlib import import_module_from_path
import warnings


# Exports
__all__ = ('bounce',)


# Load ``bounce()`` from the location of ``bounce.py``
bounce_mpath = settings.BOUNCE_FILE
try:
    _bounce_module = import_module_from_path(bounce_mpath, '_bounce_module')
    from _bounce_module import bounce
except ImportError:
    msg = 'Bounce mappings could not be found in %s. using default!' % bounce_mpath
    warnings.warn(msg, RuntimeWarning)
    from . import BounceWindow
    DEFAULT_BOUNCE = BounceWindow(green='5-7', yellow='0-4, 8-15', red='16-23')
    def bounce(device, default=DEFAULT_BOUNCE):
        """
        Return the bounce window for a given device.

        :param device:
            A `~trigger.netdevices.NetDevice` object.

        :param default:
            A `~trigger.changemgmt.BounceWindow` object.
        """
        return default

########NEW FILE########
__FILENAME__ = cmds
# -*- coding: utf-8 -*-

"""
This module abstracts the asynchronous execution of commands on multiple
network devices. It allows for integrated parsing and event-handling of return
data for rapid integration to existing or newly-created tools.

The `~trigger.cmds.Commando` class is designed to be extended but can still be
used as-is to execute commands and return the results as-is.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__copyright__ = 'Copyright 2009-2013, AOL Inc.; 2013 Salesforce.com'
__version__ = '2.3.1'

import collections
import datetime
import itertools
import os
import sys
from IPy import IP
from xml.etree.cElementTree import ElementTree, Element, SubElement
from twisted.python import log
from trigger.netdevices import NetDevices
from trigger.conf import settings
from trigger import exceptions


# Exports
__all__ = ('Commando', 'NetACLInfo')


# Default timeout in seconds for commands to return a result
DEFAULT_TIMEOUT = 30


# Classes
class Commando(object):
    """
    Execute commands asynchronously on multiple network devices.

    This class is designed to be extended but can still be used as-is to execute
    commands and return the results as-is.

    At the bare minimum you must specify a list of ``devices`` to interact with.
    You may optionally specify a list of ``commands`` to execute on those
    devices, but doing so will execute the same commands on every device
    regardless of platform.

    If ``commands`` are not specified, they will be expected to be emitted by
    the ``generate`` method for a given platform. Otherwise no commands will be
    executed.

    If you wish to customize the commands executed by device, you must define a
    ``to_{vendor_name}`` method containing your custom logic.

    If you wish to customize what is done with command results returned from a
    device, you must define a ``from_{vendor_name}`` method containing your
    custom logic.

    :param devices:
        A list of device hostnames or `~trigger.netdevices.NetDevice` objects

    :param commands:
        (Optional) A list of commands to execute on the ``devices``.

    :param creds:
        (Optional) A 3-tuple of (username, password, realm). If only (username,
        password) are provided, realm will be populated from
        :setting:`DEFAULT_REALM`. If unset it will fetch from ``.tacacsrc``.

    :param incremental:
        (Optional) A callback that will be called with an empty sequence upon
        connection and then called every time a result comes back from the
        device, with the list of all results.

    :param max_conns:
        (Optional) The maximum number of simultaneous connections to keep open.

    :param verbose:
        (Optional) Whether or not to display informational messages to the
        console.

    :param timeout:
        (Optional) Time in seconds to wait for each command executed to return a
        result. Set to ``None`` to disable timeout (not recommended).

    :param production_only:
        (Optional) If set, includes all devices instead of excluding any devices
        where ``adminStatus`` is not set to ``PRODUCTION``.

    :param allow_fallback:
        If set (default), allow fallback to base parse/generate methods when
        they are not customized in a subclass, otherwise an exception is raised
        when a method is called that has not been explicitly defined.

    :param with_errors:
        (Optional) Return exceptions as results instead of raising them. The
        default is to always return them.

    :param force_cli:
        (Optional) Juniper only. If set, sends commands using CLI instead of
        Junoscript.

    :param with_acls:
         Whether to load ACL associations (requires Redis). Defaults to whatever
         is specified in settings.WITH_ACLS
    """
    # Defaults to all supported vendors
    vendors = settings.SUPPORTED_VENDORS

    # Defaults to all supported platforms
    platforms = settings.SUPPORTED_PLATFORMS

    # The commands to run (defaults to [])
    commands = None

    # The timeout for commands to return results. We are setting this to 0
    # so that if it's not overloaded in a subclass, the timeout value passed to
    # the constructor will be preferred, especially if it is set to ``None``
    # which Twisted uses to disable timeouts completely.
    timeout = 0

    # How results are stored (defaults to {})
    results = None

    # How errors are stored (defaults to {})
    errors = None

    def __init__(self, devices=None, commands=None, creds=None,
                 incremental=None, max_conns=10, verbose=False,
                 timeout=DEFAULT_TIMEOUT, production_only=True,
                 allow_fallback=True, with_errors=True, force_cli=False,
                 with_acls=False):
        if devices is None:
            raise exceptions.ImproperlyConfigured('You must specify some `devices` to interact with!')

        self.devices = devices
        self.commands = self.commands or (commands or []) # Always fallback to []
        self.creds = creds
        self.incremental = incremental
        self.max_conns = max_conns
        self.verbose = verbose
        self.timeout = timeout if timeout != self.timeout else self.timeout
        self.nd = NetDevices(production_only=production_only, with_acls=with_acls)
        self.allow_fallback = allow_fallback
        self.with_errors = with_errors
        self.force_cli = force_cli
        self.curr_conns = 0
        self.jobs = []

        # Always fallback to {} for these
        self.errors = self.errors if self.errors is not None else {}
        self.results = self.results if self.results is not None else {}

        #self.deferrals = []
        self.supported_platforms = self._validate_platforms()
        self._setup_jobs()

    def _validate_platforms(self):
        """
        Determine the set of supported platforms for this instance by making
        sure the specified vendors/platforms for the class match up.
        """
        supported_platforms = {}
        for vendor in self.vendors:
            if vendor in self.platforms:
                types = self.platforms[vendor]
                if not types:
                    raise exceptions.MissingPlatform('No platforms specified for %r' % vendor)
                else:
                    #self.supported_platforms[vendor] = types
                    supported_platforms[vendor] = types
            else:
                raise exceptions.ImproperlyConfigured('Platforms for vendor %r not found. Please provide it at either the class level or using the arguments.' % vendor)

        return supported_platforms

    def _decrement_connections(self, data=None):
        """
        Self-explanatory. Called by _add_worker() as both callback/errback
        so we can accurately refill the jobs queue, which relies on the
        current connection count.
        """
        self.curr_conns -= 1
        return data

    def _increment_connections(self, data=None):
        """Increment connection count."""
        self.curr_conns += 1
        return True

    def _setup_jobs(self):
        """
        "Maps device hostnames to `~trigger.netdevices.NetDevice` objects and
        populates the job queue.
        """
        for dev in self.devices:
            log.msg('Adding', dev)
            if self.verbose:
                print 'Adding', dev

            # Make sure that devices are actually in netdevices and keep going
            try:
                devobj = self.nd.find(str(dev))
            except KeyError:
                msg = 'Device not found in NetDevices: %s' % dev
                log.err(msg)
                if self.verbose:
                    print 'ERROR:', msg

                # Track the errors and keep moving
                self.store_error(dev, msg)
                continue

            # We only want to add devices for which we've enabled support in
            # this class
            if devobj.vendor not in self.vendors:
                raise exceptions.UnsupportedVendor("The vendor '%s' is not specified in ``vendors``. Could not add %s to job queue. Please check the attribute in the class object." % (devobj.vendor, devobj))

            self.jobs.append(devobj)

    def select_next_device(self, jobs=None):
        """
        Select another device for the active queue.

        Currently only returns the next device in the job queue. This is
        abstracted out so that this behavior may be customized, such as for
        future support for incremental callbacks.

        :param jobs:
            (Optional) The jobs queue. If not set, uses ``self.jobs``.

        :returns:
            A `~trigger.netdevices.NetDevice` object
        """
        if jobs is None:
            jobs = self.jobs

        return jobs.pop()

    def _add_worker(self):
        """
        Adds devices to the work queue to keep it populated with the maximum
        connections as specified by ``max_conns``.
        """
        while self.jobs and self.curr_conns < self.max_conns:
            device = self.select_next_device()

            self._increment_connections()
            log.msg('connections:', self.curr_conns)
            log.msg('Adding work to queue...')
            if self.verbose:
                print 'connections:', self.curr_conns
                print 'Adding work to queue...'

            # Setup the async Deferred object with a timeout and error printing.
            commands = self.generate(device)
            async = device.execute(commands, creds=self.creds,
                                   incremental=self.incremental,
                                   timeout=self.timeout,
                                   with_errors=self.with_errors,
                                   force_cli=self.force_cli)

            # Add the parser callback for great justice!
            async.addCallback(self.parse, device)

            # If parse fails, still decrement and track the error
            async.addErrback(self.errback, device)

            # Make sure any further uncaught errors get logged
            async.addErrback(log.err)

            # Here we addBoth to continue on after pass/fail, decrement the
            # connections and move on.
            async.addBoth(self._decrement_connections)
            async.addBoth(lambda x: self._add_worker())

        # Do this once we've exhausted the job queue
        else:
            if not self.curr_conns and self.reactor_running:
                self._stop()
            elif not self.jobs and not self.reactor_running:
                log.msg('No work left.')
                if self.verbose:
                    print 'No work left.'

    def _lookup_method(self, device, method):
        """
        Base lookup method. Looks up stuff by device manufacturer like:

            from_juniper
            to_foundry

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param method:
            One of 'generate', 'parse'
        """
        METHOD_MAP = {
            'generate': 'to_%s',
            'parse': 'from_%s',
        }
        assert method in METHOD_MAP

        desired_attr = None

        # Select the desired vendor name.
        desired_vendor = device.vendor
        if device.is_netscreen(): # Workaround until we implement device drivers
            desired_vendor = 'netscreen'

        for vendor, types in self.platforms.iteritems():
            meth_attr = METHOD_MAP[method] % desired_vendor
            if device.deviceType in types:
                if hasattr(self, meth_attr):
                    desired_attr = meth_attr
                    break

        if desired_attr is None:
            if self.allow_fallback:
                desired_attr = METHOD_MAP[method] % 'base'
            else:
                raise exceptions.UnsupportedVendor("The vendor '%s' had no available %s method. Please check your ``vendors`` and ``platforms`` attributes in your class object." % (device.vendor, method))

        func = getattr(self, desired_attr)
        return func

    def generate(self, device, commands=None, extra=None):
        """
        Generate commands to be run on a device. If you don't provide
        ``commands`` to the class constructor, this will return an empty list.

        Define a 'to_{vendor_name}' method to customize the behavior for each
        platform.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param commands:
            (Optional) A list of commands to execute on the device. If not
            specified in they will be inherited from commands passed to the
            class constructor.

        :param extra:
            (Optional) A dictionary of extra data to send to the generate method for the
            device.
        """
        if commands is None:
            commands = self.commands
        if extra is None:
            extra = {}

        func = self._lookup_method(device, method='generate')
        return func(device, commands, extra)

    def parse(self, results, device):
        """
        Parse output from a device.

        Define a 'from_{vendor_name}' method to customize the behavior for each
        platform.

        :param results:
            The results of the commands executed on the device

        :param device:
            A `~trigger.netdevices.NetDevice` object
        """
        func = self._lookup_method(device, method='parse')
        return func(results, device)

    def errback(self, failure, device):
        """
        The default errback. Overload for custom behavior but make sure it
        always decrements the connections.

        :param failure:
            Usually a Twisted ``Failure`` instance.

        :param device:
            A `~trigger.netdevices.NetDevice` object
        """
        failure.trap(Exception)
        self.store_error(device, failure)
        #self._decrement_connections(failure)
        return failure

    def store_error(self, device, error):
        """
        A simple method for storing an error called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param error:
            The error to store. Anything you want really, but usually a Twisted
            ``Failure`` instance.
        """
        devname = str(device)
        self.errors[devname] = error
        return True

    def store_results(self, device, results):
        """
        A simple method for storing results called by all default
        parse/generate methods.

        If you want to customize the default method for storing results,
        overload this in your subclass.

        :param device:
            A `~trigger.netdevices.NetDevice` object

        :param results:
            The results to store. Anything you want really.
        """
        devname = str(device)
        log.msg("Storing results for %r: %r" % (devname, results))
        self.results[devname] = results
        return True

    def map_results(self, commands=None, results=None):
        """Return a dict of ``{command: result, ...}``"""
        if commands is None:
            commands = self.commands
        if results is None:
            results = []

        return dict(itertools.izip_longest(commands, results))

    @property
    def reactor_running(self):
        """Return whether reactor event loop is running or not"""
        from twisted.internet import reactor
        log.msg("Reactor running? %s" % reactor.running)
        return reactor.running

    def _stop(self):
        """Stop the reactor event loop"""
        log.msg('stopping reactor')
        if self.verbose:
            print 'stopping reactor'

        from twisted.internet import reactor
        reactor.stop()

    def _start(self):
        """Start the reactor event loop"""
        log.msg('starting reactor')
        if self.verbose:
            print 'starting reactor'

        if self.curr_conns:
            from twisted.internet import reactor
            reactor.run()
        else:
            msg = "Won't start reactor with no work to do!"
            log.msg(msg)
            if self.verbose:
                print msg

    def run(self):
        """
        Nothing happens until you execute this to perform the actual work.
        """
        self._add_worker()
        self._start()

    #=======================================
    # Base generate (to_)/parse (from_) methods
    #=======================================

    def to_base(self, device, commands=None, extra=None):
        commands = commands or self.commands
        log.msg('Sending %r to %s' % (commands, device))
        return commands

    def from_base(self, results, device):
        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, self.map_results(self.commands, results))

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================

    def to_juniper(self, device, commands=None, extra=None):
        """
        This just creates a series of ``<command>foo</command>`` elements to
        pass along to execute_junoscript()"""
        commands = commands or self.commands

        # If we've set force_cli, use to_base() instead
        if self.force_cli:
            return self.to_base(device, commands, extra)

        ret = []
        for command in commands:
            cmd = Element('command')
            cmd.text = command
            ret.append(cmd)

        return ret

class NetACLInfo(Commando):
    """
    Class to fetch and parse interface information. Exposes a config
    attribute which is a dictionary of devices passed to the constructor and
    their interface information.

    Each device is a dictionary of interfaces. Each interface field will
    default to an empty list if not populated after parsing.  Below is a
    skeleton of the basic config, with expected fields::

        config {
            'device1': {
                'interface1': {
                    'acl_in': [],
                    'acl_out': [],
                    'addr': [],
                    'description': [],
                    'subnets': [],
                }
            }
        }

    Interface field descriptions:

        :addr:
            List of ``IPy.IP`` objects of interface addresses

        :acl_in:
            List of inbound ACL names

        :acl_out:
            List of outbound ACL names

        :description:
            List of interface description(s)

        :subnets:
            List of ``IPy.IP`` objects of interface networks/CIDRs

    Example::

        >>> n = NetACLInfo(devices=['jm10-cc101-lab.lab.aol.net'])
        >>> n.run()
        Fetching jm10-cc101-lab.lab.aol.net
        >>> n.config.keys()
        [<NetDevice: jm10-cc101-lab.lab.aol.net>]
        >>> dev = n.config.keys()[0]
        >>> n.config[dev].keys()
        ['lo0.0', 'ge-0/0/0.0', 'ge-0/2/0.0', 'ge-0/1/0.0', 'fxp0.0']
        >>> n.config[dev]['lo0.0'].keys()
        ['acl_in', 'subnets', 'addr', 'acl_out', 'description']
        >>> lo0 = n.config[dev]['lo0.0']
        >>> lo0['acl_in']; lo0['addr']
        ['abc123']
        [IP('66.185.128.160')]

    This accepts all arguments from the `~trigger.cmds.Commando` parent class,
    as well as this one extra:

    :param skip_disabled:
        Whether to include interface names without any information. (Default:
        ``True``)
    """
    def __init__(self, **args):
        try:
            import pyparsing as pp
        except ImportError:
            raise RuntimeError("You must install ``pyparsing==1.5.7`` to use NetACLInfo")
        self.config = {}
        self.skip_disabled = args.pop('skip_disabled', True)
        super(NetACLInfo, self).__init__(**args)

    def IPsubnet(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.0/24').'''
        return IP(addr, make_net=True)

    def IPhost(self, addr):
        '''Given '172.20.1.4/24', return IP('172.20.1.4/32').'''
        return IP(addr[:addr.index('/')]) # Only keep before "/"

    #=======================================
    # Vendor-specific generate (to_)/parse (from_) methods
    #=======================================

    def to_cisco(self, dev, commands=None, extra=None):
        """This is the "show me all interface information" command we pass to
        IOS devices"""
        return ['show configuration | include ^(interface | ip address | ip access-group | description|!)']

    def to_arista(self, dev, commands=None, extra=None):
        """
        Similar to IOS, but:

           + Arista has no "show conf" so we have to do "show run"
           + The regex used in the CLI for Arista is more "precise" so we have
             to change the pattern a little bit compared to the on in
             generate_ios_cmd

        """
        return ['show running-config | include (^interface | ip address | ip acces-group | description |!)']

    def to_force10(self, dev, commands=None, extra=None):
        """
        Similar to IOS, but:
            + You only get the "grep" ("include" equivalent) when using "show
              run".
            + The regex must be quoted.
        """
        return ['show running-config | grep "^(interface | ip address | ip access-group | description|!)"']

    # Other IOS-like vendors are Cisco-enough
    to_brocade = to_cisco
    to_foundry = to_cisco

    def from_cisco(self, data, device):
        """Parse IOS config based on EBNF grammar"""
        self.results[device.nodeName] = data #"MY OWN IOS DATA"
        alld = data[0]

        log.msg('Parsing interface data (%d bytes)' % len(alld))
        self.config[device] = _parse_ios_interfaces(alld, skip_disabled=self.skip_disabled)

        return True

    # Other IOS-like vendors are Cisco-enough
    from_arista = from_cisco
    from_brocade = from_cisco
    from_foundry = from_cisco
    from_force10 = from_cisco

    def to_juniper(self, dev, commands=None, extra=None):
        """Generates an etree.Element object suitable for use with
        JunoScript"""
        cmd = Element('get-configuration',
            database='committed',
            inherit='inherit')

        SubElement(SubElement(cmd, 'configuration'), 'interfaces')

        self.commands = [cmd]
        return self.commands

    def __children_with_namespace(self, ns):
        return lambda elt, tag: elt.findall('./' + ns + tag)

    def from_juniper(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        self.results[device.nodeName] = data #"MY OWN JUNOS DATA"

        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        children = self.__children_with_namespace(ns)

        xml = data[0]
        dta = {}
        for interface in xml.getiterator(ns + 'interface'):

            basename = children(interface, 'name')[0].text

            description = interface.find(ns + 'description')
            desctext = []
            if description is not None:
                desctext.append(description.text)

            for unit in children(interface, 'unit'):
                ifname = basename + '.' + children(unit, 'name')[0].text
                dta[ifname] = {}
                dta[ifname]['addr'] = []
                dta[ifname]['subnets'] = []
                dta[ifname]['description'] = desctext
                dta[ifname]['acl_in'] = []
                dta[ifname]['acl_out'] = []

                # Iterating the "family/inet" tree. Seems ugly.
                for family in children(unit, 'family'):
                    for family2 in family:
                        if family2.tag != ns + 'inet':
                            continue
                        for inout in 'in', 'out':
                            dta[ifname]['acl_%s' % inout] = []

                            # Try basic 'filter/xput'...
                            acl = family2.find('%sfilter/%s%sput' % (ns, ns, inout))

                            # Junos 9.x changes to 'filter/xput/filter-name'
                            if acl is not None and "    " in acl.text:
                                 acl = family2.find('%sfilter/%s%sput/%sfilter-name' % (ns, ns, inout, ns))

                            # Pushes text as variable name.  Must be a better way to do this?
                            if acl is not None:
                                acl = acl.text

                            # If we couldn't match a single acl, try 'filter/xput-list'
                            if not acl:
                                #print 'trying filter list..'
                                acl = [i.text for i in family2.findall('%sfilter/%s%sput-list' % (ns, ns, inout))]
                                #if acl: print 'got filter list'

                            # Otherwise, making single acl into a list
                            else:
                                acl = [acl]

                            # Append acl list to dict
                            if acl:
                                dta[ifname]['acl_%s' % inout].extend(acl)

                        for node in family2.findall('%saddress/%sname' % (ns, ns)):
                            ip = node.text
                            dta[ifname]['subnets'].append(self.IPsubnet(ip))
                            dta[ifname]['addr'].append(self.IPhost(ip))

        self.config[device] = dta
        return True

def _parse_ios_interfaces(data, acls_as_list=True, auto_cleanup=True, skip_disabled=True):
    """
    Walks through a IOS interface config and returns a dict of parts.

    Intended for use by `~trigger.cmds.NetACLInfo.ios_parse()` but was written
    to be portable.

    :param acls_as_list:
        Whether you want acl names as strings instead of list members, e.g.

    :param auto_cleanup:
        Whether you want to pass results through cleanup_results(). Default: ``True``)
        "ABC123" vs. ['ABC123']. (Default: ``True``)

    :param skip_disabled:
        Whether to skip disabled interfaces. (Default: ``True``)
    """
    import pyparsing as pp

    # Setup
    bang = pp.Literal("!").suppress()
    anychar = pp.Word(pp.printables)
    nonbang = pp.Word(''.join([x for x in pp.printables if x != "!"]) + '\n\r\t ')
    comment = bang + pp.restOfLine.suppress()

    #weird things to ignore in foundries
    aaa_line = pp.Literal("aaa").suppress() + pp.restOfLine.suppress()
    module_line = pp.Literal("module").suppress() + pp.restOfLine.suppress()
    startup_line = pp.Literal("Startup").suppress() + pp.restOfLine.suppress()
    ver_line = pp.Literal("ver") + anychar#+ pp.restOfLine.suppress()
    #using SkipTO instead now

    #foundry example:
    #telnet@olse1-dc5#show  configuration | include ^(interface | ip address | ip access-group | description|!)
    #!
    #Startup-config data location is flash memory
    #!
    #Startup configuration:
    #!
    #ver 07.5.05hT53
    #!
    #module 1 bi-0-port-m4-management-module
    #module 2 bi-8-port-gig-module

    #there is a lot more that foundry is including in the output that should be ignored

    interface_keyword = pp.Keyword("interface")
    unwanted = pp.SkipTo(interface_keyword, include=False).suppress()

    #unwanted = pp.ZeroOrMore(bang ^ comment ^ aaa_line ^ module_line ^ startup_line ^ ver_line)

    octet = pp.Word(pp.nums, max=3)
    ipaddr = pp.Combine(octet + "." + octet + "." + octet + "." + octet)
    address = ipaddr
    netmask = ipaddr
    cidr = pp.Literal("/").suppress() + pp.Word(pp.nums, max=2)

    # Description
    desc_keyword = pp.Keyword("description")
    description = pp.Dict( pp.Group(desc_keyword + pp.Group(pp.restOfLine)) )

    # Addresses
    #cisco example:
    # ip address 172.29.188.27 255.255.255.224 secondary
    #
    #foundry example:
    # ip address 10.62.161.187/26

    ipaddr_keyword = pp.Keyword("ip address").suppress()
    secondary = pp.Literal("secondary").suppress()

    #foundry matches on cidr and cisco matches on netmask
    #netmask converted to cidr in cleanup
    ip_tuple = pp.Group(address + (cidr ^ netmask)).setResultsName('addr', listAllMatches=True)
    ip_address = ipaddr_keyword + ip_tuple + pp.Optional(secondary)

    addrs = pp.ZeroOrMore(ip_address)

    # ACLs
    acl_keyword = pp.Keyword("ip access-group").suppress()

    # acl_name to be [''] or '' depending on acls_as_list
    acl_name = pp.Group(anychar) if acls_as_list else anychar
    direction = pp.oneOf('in out').suppress()
    acl_in = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('in'))
    acl_in.setParseAction(pp.replaceWith('acl_in'))
    acl_out = acl_keyword + pp.FollowedBy(acl_name + pp.Literal('out'))
    acl_out.setParseAction(pp.replaceWith('acl_out'))

    acl = pp.Dict( pp.Group((acl_in ^ acl_out) + acl_name)) + direction
    acls = pp.ZeroOrMore(acl)

    # Interfaces
    iface_keyword = pp.Keyword("interface").suppress()
    foundry_awesome = pp.Literal(" ").suppress() + anychar
    #foundry exmaple:
    #!
    #interface ethernet 6/6
    # ip access-group 126 in
    # ip address 172.18.48.187 255.255.255.255

    #cisco example:
    #!
    #interface Port-channel1
    # description gear1-mtc : AE1 : iwslbfa1-mtc-sw0 :  : 1x1000 : 172.20.166.0/24 :  :  :
    # ip address 172.20.166.251 255.255.255.0


    interface = pp.Combine(anychar + pp.Optional(foundry_awesome))

    iface_body = pp.Optional(description) + pp.Optional(acls) + pp.Optional(addrs) + pp.Optional(acls)
    #foundry's body is acl then ip and cisco's is ip then acl

    iface_info = pp.Optional(unwanted) + iface_keyword +  pp.Dict( pp.Group(interface + iface_body) ) + pp.SkipTo(bang)
    #iface_info = unwanted +  pp.Dict( pp.Group(interface + iface_body) ) + pp.SkipTo(bang)

    interfaces = pp.Dict( pp.ZeroOrMore(iface_info) )

    # This is where the parsing is actually happening
    try:
        results = interfaces.parseString(data)
    except: # (ParseException, ParseFatalException, RecursiveGrammarException):
        results = {}

    if auto_cleanup:
        return _cleanup_interface_results(results, skip_disabled=skip_disabled)
    return results

def _cleanup_interface_results(results, skip_disabled=True):
    """
    Takes ParseResults dictionary-like object and returns an actual dict of
    populated interface details.  The following is performed:

        * Ensures all expected fields are populated
        * Down/un-addressed interfaces are skipped
        * Bare IP/CIDR addresses are converted to IPy.IP objects

    :param results:
        Interface results to parse

    :param skip_disabled:
        Whether to skip disabled interfaces. (Default: ``True``)
    """
    interfaces = sorted(results.keys())
    newdict = {}
    for interface in interfaces:
        iface_info = results[interface]

        # Maybe skip down interfaces
        if 'addr' not in iface_info and skip_disabled:
            continue

        # Ensure we have a dict to work with.
        if not iface_info:
            iface_info = collections.defaultdict(list)

        newdict[interface] = {}
        new_int = newdict[interface]

        new_int['addr'] = _make_ipy(iface_info.get('addr', []))
        new_int['subnets'] = _make_cidrs(iface_info.get('subnets', iface_info.get('addr', [])))
        new_int['acl_in'] = list(iface_info.get('acl_in', []))
        new_int['acl_out'] = list(iface_info.get('acl_out', []))
        new_int['description'] = list(iface_info.get('description', []))

    return newdict

def _make_ipy(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list of
    IP address objects"""
    return [IP(addr) for addr, mask in nets]

def _make_cidrs(nets):
    """Given a list of 2-tuples of (address, netmask), returns a list CIDR
    blocks"""
    return [IP(addr).make_net(mask) for addr, mask in nets]

def _dump_interfaces(idict):
    """Prints a dict of parsed interface results info for use in debugging"""
    for name, info in idict.items():
        print '>>>', name
        print '\t',
        if idict[name]:
            if hasattr(info, 'keys'):
                keys = info.keys()
                print keys
                for key in keys:
                    print '\t', key, ':', info[key]
            else:
                print str(info)
        else:
            print 'might be shutdown'
        print

########NEW FILE########
__FILENAME__ = global_settings
# Default Trigger settings. Override these with settings in the module
# pointed-to by the TRIGGER_SETTINGS environment variable. This is pretty much
# an exact duplication of how Django does this.

import IPy
import os
import socket

#===============================
# Global Settings
#===============================

# This is where Trigger should look for its files.
PREFIX = '/etc/trigger'

# Set to True to enable GPG Authentication
# Set to False to use the old .tackf encryption method.
# Should be False unless instructions/integration is ready for GPG
USE_GPG_AUTH = False

# This is used for old auth method. It sucks and needs to die.
# TODO (jathan): This is deprecated. Remove all references to this and make GPG
# the default and only method.
USER_HOME = os.getenv('HOME')
TACACSRC = os.getenv('TACACSRC', os.path.join(USER_HOME, '.tacacsrc'))
TACACSRC_KEYFILE = os.getenv('TACACSRC_KEYFILE', os.path.join(PREFIX, '.tackf'))
TACACSRC_PASSPHRASE = '' # NYI

# Default login realm to store user credentials (username, password) for
# general use within the .tacacsrc
DEFAULT_REALM = 'aol'

# List of plugins allowed to be importd by Commando. Plugins should be listed as
# strings depicting the absolute paths.
#
# e.g. ['trigger.contrib.config_device', 'trigger.contrib.show_clock', 'bacon.cool_plugin']
#
# Currently config_device and execute_commands are automatically imported.
BUILTIN_PLUGINS = [
    'trigger.contrib.commando.plugins.config_device',
    'trigger.contrib.commando.plugins.show_clock',
    'trigger.contrib.commando.plugins.show_version'
]
COMMANDO_PLUGINS = BUILTIN_PLUGINS

# Location of firewall policies
FIREWALL_DIR = '/data/firewalls'

# Location of tftproot.
TFTPROOT_DIR = '/data/tftproot'
TFTP_HOST = ''

# Add internally owned networks here. All network blocks owned/operated and
# considered part of your network should be included.
INTERNAL_NETWORKS = [
    IPy.IP("10.0.0.0/8"),
    IPy.IP("172.16.0.0/12"),
    IPy.IP("192.168.0.0/16"),
]

# The tuple of supported vendors derived from the values of VENDOR_MAP
SUPPORTED_VENDORS = (
    'a10',
    'arista',
    'aruba',
    'brocade',
    'cisco',
    'citrix',
    'dell',
    'f5',
    'force10',
    'foundry',
    'juniper',
    'mrv',
    'netscreen',
    'paloalto',
)
VALID_VENDORS = SUPPORTED_VENDORS # For backwards compatibility

# A mapping of manufacturer attribute values to canonical vendor name used by
# Trigger. These single-word, lowercased canonical names are used throughout
# Trigger.
#
# If your internal definition differs from the UPPERCASED ones specified below
# (which they probably do, customize them here.
VENDOR_MAP = {
    'A10 NETWORKS': 'a10',
    'ARISTA NETWORKS': 'arista',
    'ARUBA NETWORKS': 'aruba',
    'BROCADE': 'brocade',
    'CISCO SYSTEMS': 'cisco',
    'CITRIX': 'citrix',
    'DELL': 'dell',
    'F5 NETWORKS': 'f5',
    'FORCE10': 'force10',
    'FOUNDRY': 'foundry',
    'JUNIPER': 'juniper',
    'MRV': 'mrv',
    'NETSCREEN TECHNOLOGIES': 'netscreen',
}

# A dictionary keyed by manufacturer name containing a list of the device types
# for each that is officially supported by Trigger.
SUPPORTED_PLATFORMS = {
    'a10': ['SWITCH'],
    'arista': ['SWITCH'],                         # Your "Cloud" network vendor
    'aruba': ['SWITCH'],                          # Aruba Wi-Fi controllers
    'brocade': ['ROUTER', 'SWITCH'],
    'cisco': ['ROUTER', 'SWITCH'],
    'citrix': ['SWITCH'],                         # Assumed to be NetScalers
    'dell': ['SWITCH'],
    'f5': ['LOAD BALANCING', 'SWITCH'],
    'force10': ['ROUTER', 'SWITCH'],
    'foundry': ['ROUTER', 'SWITCH'],
    'juniper': ['FIREWALL', 'ROUTER', 'SWITCH'],  # Any devices running Junos
    'mrv': ['CONSOLE SERVER', 'SWITCH'],
    'netscreen': ['FIREWALL'],                    # Pre-Juniper NetScreens
    'paloalto': ['FIREWALL'],
}

# The tuple of support device types
SUPPORTED_TYPES = ('CONSOLE SERVER', 'FIREWALL', 'DWDM', 'LOAD BALANCING',
                   'ROUTER', 'SWITCH')

# A mapping of of vendor names to the default device type for each in the
# event that a device object is created and the deviceType attribute isn't set
# for some reason.
DEFAULT_TYPES = {
    'a10': 'SWITCH',
    'arista': 'SWITCH',
    'aruba': 'SWITCH',
    'brocade': 'SWITCH',
    'citrix': 'SWITCH',
    'cisco': 'ROUTER',
    'dell': 'SWITCH',
    'f5': 'LOAD BALANCING',
    'force10': 'ROUTER',
    'foundry': 'SWITCH',
    'juniper': 'ROUTER',
    'mrv': 'CONSOLE SERVER',
    'netscreen': 'FIREWALL',
    'paloalto': 'FIREWALL',
}

# When a vendor is not explicitly defined within `DEFAULT_TYPES`, fallback to
# this type.
FALLBACK_TYPE = 'ROUTER'

#===============================
# Twister
#===============================

# Default timeout in seconds for commands executed during a session.  If a
# response is not received within this window, the connection is terminated.
DEFAULT_TIMEOUT = 5 * 60

# Default timeout in seconds for initial telnet connections.
TELNET_TIMEOUT  = 60

# Whether or not to allow telnet fallback
TELNET_ENABLED = True

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable interactive (pty) SSH sessions, such as when using
# bin/gong.
SSH_PTY_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
}

# A mapping of vendors to the types of devices for that vendor for which you
# would like to disable asynchronous (NON-interactive) SSH sessions, such as
# when using twister or Commando to remotely control a device.
SSH_ASYNC_DISABLED = {
    'dell': ['SWITCH'],    # Dell SSH is just straight up broken
    'foundry': ['SWITCH'], # Old Foundry switches only do SSHv1
}

# Vendors that basically just emulate Cisco's IOS and can be treated
# accordingly for the sake of interaction.
IOSLIKE_VENDORS = (
    'a10',
    'arista',
    'aruba',
    'brocade',
    'cisco',
    'dell',
    'force10',
    'foundry',
)

# The file path where .gorc is expected to be found.
GORC_FILE = '~/.gorc'

# The only root commands that are allowed to be executed when defined within
# ``~.gorc``. They will be filtered out by `~trigger.gorc.filter_commands()`.
GORC_ALLOWED_COMMANDS = (
    'cli',
    'enable',
    'exit',
    'get',
    'monitor',
    'ping',
    'quit',
    'set',
    'show',
    'start',
    'term',
    'terminal',
    'traceroute',
    'who',
    'whoami'
)

#===============================
# NetDevices
#===============================

# Change this to False to skip the loading of ACLs globally
# (not recommended)
WITH_ACLS = True

# Path to the explicit module file for autoacl.py so that we can still perform
# 'from trigger.acl.autoacl import autoacl' without modifying sys.path.
AUTOACL_FILE = os.environ.get('AUTOACL_FILE', os.path.join(PREFIX, 'autoacl.py'))

# A tuple of data loader classes, specified as strings. Optionally, a tuple can
# be used instead of a string. The first item in the tuple should be the
# Loader's module, subsequent items are passed to the Loader during
# initialization.
NETDEVICES_LOADERS = (
    'trigger.netdevices.loaders.filesystem.XMLLoader',
    'trigger.netdevices.loaders.filesystem.JSONLoader',
    'trigger.netdevices.loaders.filesystem.SQLiteLoader',
    'trigger.netdevices.loaders.filesystem.RancidLoader',
    'trigger.netdevices.loaders.filesystem.CSVLoader',
)

# A path or URL to netdevices device metadata source data, which is used to
# populate trigger.netdevices.NetDevices. For more information on this, see
# NETDEVICES_LOADERS.
NETDEVICES_SOURCE = os.environ.get('NETDEVICES_SOURCE', os.path.join(PREFIX,
                                                                     'netdevices.xml'))
# Assign NETDEVICES_SOURCE to NETDEVICES_FILE for backwards compatibility
NETDEVICES_FILE = NETDEVICES_SOURCE

# Whether to treat the RANCID root as a normal instance, or as the root to
# multiple instances. This is only checked when using RANCID as a data source.
RANCID_RECURSE_SUBDIRS = os.environ.get('RANCID_RECURSE_SUBDIRS', False)

# Valid owning teams (e.g. device.owningTeam) go here. These are examples and should be
# changed to match your environment.
VALID_OWNERS = (
    #'Data Center',
    #'Backbone Engineering',
    #'Enterprise Networking',
)

# Fields and values defined here will dictate which Juniper devices receive a
# ``commit-configuration full`` when populating ``NetDevice.commit_commands`.
# The fields and values must match the objects exactly or it will fallback to
# ``commit-configuration``.
JUNIPER_FULL_COMMIT_FIELDS = {
    #'deviceType': 'SWITCH',
    #'make': 'EX4200',
}

#===============================
# Prompt Patterns
#===============================
# Specially-defined, per-vendor prompt patterns. If a vendor isn't defined here,
# try to use IOSLIKE_PROMPT_PAT or fallback to DEFAULT_PROMPT_PAT.
PROMPT_PATTERNS = {
    'aruba': r'\(\S+\)(?: \(\S+\))?\s?#$', # ArubaOS 6.1
    #'aruba': r'\S+(?: \(\S+\))?\s?#\s$', # ArubaOS 6.2
    'citrix': r'\sDone\n$',
    'f5': r'.*\(tmos\).*?#\s{1,2}\r?$',
    'juniper': r'\S+\@\S+(?:\>|#)\s$',
    'mrv': r'\r\n?.*(?:\:\d{1})?\s\>\>?$',
    'netscreen': r'(\w+?:|)[\w().-]*\(?([\w.-])?\)?\s*->\s*$',
    'paloalto': r'\r\n\S+(?:\>|#)\s?$',
}

# When a pattern is not explicitly defined for a vendor, this is what we'll try
# next (since most vendors are in fact IOS-like)
IOSLIKE_PROMPT_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?#\s?$'
IOSLIKE_ENABLE_PAT = r'\S+(\(config(-[a-z:1-9]+)?\))?>\s?$'

# Generic prompt to match most vendors. It assumes that you'll be greeted with
# a "#" prompt.
DEFAULT_PROMPT_PAT = r'\S+#\s?$'

#===============================
# Bounce Windows/Change Mgmt
#===============================

# Path of the explicit module file for bounce.py containing custom bounce
# window mappings.
BOUNCE_FILE = os.environ.get('BOUNCE_FILE', os.path.join(PREFIX, 'bounce.py'))

# Default bounce timezone. All BounceWindow objects are configured using
# US/Eastern for now.
BOUNCE_DEFAULT_TZ = 'US/Eastern'

# The default fallback window color for bounce windows. Must be one of
# ('green', 'yellow', or 'red').
#
#     green: Low risk
#    yellow: Medium risk
#       red: High risk
BOUNCE_DEFAULT_COLOR = 'red'

#===============================
# Redis Settings
#===============================

# Redis master server. This will be used unless it is unreachable.
REDIS_HOST = '127.0.0.1'

# The Redis port. Default is 6379.
REDIS_PORT = 6379

# The Redis DB. Default is 0.
REDIS_DB = 0

#===============================
# Database Settings
#===============================

# These are self-explanatory, I hope. Use the ``init_task_db`` to initialize
# your database after you've created it! :)
DATABASE_ENGINE = 'mysql'   # Choose 'postgresql', 'mysql', 'sqlite3'
DATABASE_NAME = ''          # Or path to database file if using sqlite3
DATABASE_USER = ''          # Not used with sqlite3
DATABASE_PASSWORD = ''      # Not used with sqlite3
DATABASE_HOST = ''          # Set to '' for localhost. Not used with sqlite3
DATABASE_PORT = ''          # Set to '' for default. Not used with sqlite3.

#===============================
# ACL Management
#===============================
# Whether to allow multi-line comments to be used in Juniper firewall filters.
# Defaults to False.
ALLOW_JUNIPER_MULTILINE_COMMENTS = False

# FILTER names of ACLs that should be skipped or ignored by tools
# NOTE: These should be the names of the filters as they appear on devices. We
# want this to be mutable so it can be modified at runtime.
# TODO (jathan): Move this into Redis and maintain with 'acl' command?
IGNORED_ACLS = []

# FILE names ACLs that shall not be modified by tools
# NOTE: These should be the names of the files as they exist in FIREWALL_DIR.
# Trigger expects ACLs to be prefixed with 'acl.'.  These are examples and
# should be replaced.
NONMOD_ACLS  = []

# Mapping of real IP to external NAT. This is used by load_acl in the event
# that a TFTP or connection from a real IP fails or explicitly when passing the
# --no-vip flag.
# format: {local_ip: external_ip}
VIPS = {}

#===============================
# ACL Loading/Rate-Limiting
#===============================
# All of the following settings are currently only used in ``load_acl``.  If
# and when the load_acl functionality gets moved into the API, this might
# change.

# Any FILTER name (not filename) in this list will be skipped during automatic loads.
AUTOLOAD_BLACKLIST = []

# Assign blacklist to filter for backwards compatibility
AUTOLOAD_FILTER = AUTOLOAD_BLACKLIST

# Modify this if you want to create a list that if over the specified number of
# routers will be treated as bulk loads.
# TODO (jathan): Provide examples so that this has more context/meaning. The
# current implementation is kind of broken and doesn't scale for data centers
# with a large of number of devices.
#
# Format:
# { 'filter_name': threshold_count }
AUTOLOAD_FILTER_THRESH = {}

# Any ACL applied on a number of devices >= to this number will be treated as
# bulk loads.
AUTOLOAD_BULK_THRESH = 10

# Add an acl:max_hits here if you want to override BULK_MAX_HITS_DEFAULT
# Keep in mind this number is PER EXECUTION of load_acl --auto (typically once
# per hour or 3 per bounce window).
#
# 1 per load_acl execution; ~3 per day, per bounce window
# 2 per load_acl execution; ~6 per day, per bounce window
# etc.
#
# Format:
# { 'filter_name': max_hits }
BULK_MAX_HITS = {}

# If an ACL is bulk but not in BULK_MAX_HITS, use this number as max_hits
BULK_MAX_HITS_DEFAULT = 1


#===============================
# Stage ACL changes
#===============================
# This variable should be a function that returns the contents of the ACL
# files that are being pushed and the tftp location for all of them
#
# input
# list of file names, optional log file and boolean for sanitizing
#
# return
# ([<list of string where each string is the entire contents of an acl file to push>],
#   [<list of the path to files on the tftp server to push>])
#
def _stage_acls(acls, log=None, sanitize_acl=False):
    """stage the new ACL files for load_acl"""

    import os
    from trigger.acl import parse as acl_parse

    acl_contents = []
    tftp_paths = []

    fails = []

    for acl in acls:
        nonce = os.urandom(8).encode('hex')
        source = FIREWALL_DIR + '/%s' % acl
        dest = TFTPROOT_DIR + '/%s.%s' % (acl, nonce)

        try:
            os.stat(dest)
        except OSError:
            try:
                shutil.copyfile(source, dest)
            except:
                fails.append("Unable to stage TFTP File %s" % str(acls))
                continue
            else:
                os.chmod(dest, 0644)

        file_contents = file(FIREWALL_DIR + '/' + acl).read()
        acl_contents.append(file_contents)

        tftp_paths.append("%s.%s" % (acl, nonce))

        #strip comments if brocade
        if (sanitize_acl):
            msg = 'Sanitizing ACL {0} as {1}'.format(source, dest)
            log.msg(msg)
            with open(source, 'r') as src_acl:
                acl = acl_parse(src_acl)
            acl.strip_comments()
            output = '\n'.join(acl.output(replace=True)) + '\n'
            with open(dest, 'w') as dst_acl:
                dst_acl.write(output)

    return acl_contents, tftp_paths, fails

STAGE_ACLS = _stage_acls


#===============================
# Get the TFTP source
#===============================
def _get_tftp_source(dev=None, no_vip=True): #False): #True):
    """
    Determine the right TFTP source-address to use (public vs. private)
    based on ``settings.VIPS``, and return that address.

    :param dev:
        A `~trigger.netdevices.NetDevice` object
    """
    import socket
    host = socket.gethostbyname(socket.getfqdn())
    if no_vip:
        return host
    elif host not in VIPS:
        return host
    ## hack to make broken routers work (This shouldn't be necessary.)
    for broken in 'ols', 'rib', 'foldr':
        if dev.nodeName.startswith(broken):
            return host
    return VIPS[host]

GET_TFTP_SOURCE = _get_tftp_source

#===============================
# OnCall Engineer Display
#===============================
# This variable should be a function that returns data for your on-call engineer, or
# failing that None.  The function should return a dictionary that looks like
# this:
#
# {'username': 'joegineer',
#  'name': 'Joe Engineer',
#  'email': 'joe.engineer@example.notreal'}
#
# If you don't want to return this information, have it return None.
GET_CURRENT_ONCALL = lambda x=None: x

#===============================
# CM Ticket Creation
#===============================
# This should be a function that creates a CM ticket and returns the ticket
# number, or None.
# TODO (jathan): Improve this interface so that it is more intuitive.
def _create_cm_ticket_stub(**args):
    return None

# If you don't want to use this feature, just have the function return None.
CREATE_CM_TICKET = _create_cm_ticket_stub

#===============================
# Notifications
#===============================
# Email sender for integrated toosl. Usually a good idea to make this a
# no-reply address.
EMAIL_SENDER = 'nobody@not.real'

# Who to email when things go well (e.g. load_acl --auto)
SUCCESS_EMAILS = [
    #'neteng@example.com',
]

# Who to email when things go not well (e.g. load_acl --auto)
FAILURE_EMAILS = [
    #'primarypager@example.com',
    #'secondarypager@example.com',
]

# The default sender for integrated notifications. This defaults to the fqdn
# for the localhost.
NOTIFICATION_SENDER = socket.gethostname()

# Destinations (hostnames, addresses) to notify when things go well.
SUCCESS_RECIPIENTS = [
    # 'foo.example.com',
]

# Destinations (hostnames, addresses) to notify when things go not well.
FAILURE_RECIPIENTS = [
    # socket.gethostname(), # The fqdn for the localhost
]

# This is a list of fully-qualified paths. Each path should end with a callable
# that handles a notification event and returns ``True`` in the event of a
# successful notification, or ``None``.
NOTIFICATION_HANDLERS = [
    'trigger.utils.notifications.handlers.email_handler',
]

########NEW FILE########
__FILENAME__ = config_device

import os.path
import re
from socket import getfqdn, gethostbyname
from twisted.python import log
from trigger.contrib.commando import CommandoApplication
from trigger.conf import settings
from trigger.utils import xmltodict, strip_juniper_namespace
import xml.etree.ElementTree as ET
from xml.etree.cElementTree import ElementTree, Element, SubElement

task_name = 'config_device'

if not hasattr(settings, 'TFTPROOT_DIR'):
    settings.TFTPROOT_DIR = ''
if not hasattr(settings, 'TFTP_HOST'):
    settings.TFTP_HOST = ''

def xmlrpc_config_device(*args, **kwargs):
    c = ConfigDevice(*args, **kwargs)
    d = c.run()
    return d

class ConfigDevice(CommandoApplication):
    tftp_dir = settings.TFTPROOT_DIR
    tftp_host = settings.TFTP_HOST
    tftp_ip = gethostbyname(tftp_host)

    def __init__(self, action='replace', files=None, commands=None, debug=False, **kwargs):
        if commands is None:
            commands = []
        if files is None:
            files = []
        self.data=[]
        self.commands = commands
        self.files = files
        self.action = action
        ##
        ## available actions:
        ##  replace
        ##  overwrite
        ##  merge
        ##  set
        ##
        self.debug = debug
        super(ConfigDevice, self).__init__(**kwargs)
    ##
    ## to_<vendor> methods
    ## 
    ## Used to construct the cmds sent to specific devices.
    ## The dev is passed to allow for creating different
    ## commands based on model and version!!

    def to_cisco(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        for fn in files:
            copytftpcmd = "copy tftp://%s/%s running-config" % (tftp_ip, fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds
    to_arista = to_cisco

    def to_brocade(self, dev, commands=None, extra=None):
        cmds = []
        action = self.action
        files = self.files
        if re.match(r"^BRMLXE", dev.make):
            log.msg('Device Type (%s %s) not supported' % (dev.vendor, dev.make))
            return []
        for fn in files:
            copytftpcmd = "copy tftp running-config %s %s" % (tftp_ip, fn)
            if action == 'overwrite':
                copytftpcmd += ' overwrite'
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_dell(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        if dev.make != 'POWERCONNECT':
            log.msg('Device Type (%s %s) not supported' % (dev.vendor, dev.make))
            return cmds
        for fn in files:
            copytftpcmd = "copy tftp://%s/%s running-config" % (tftp_ip, fn)
            cmds.append(copytftpcmd)
        cmds.append('copy running-config startup-config')
        return cmds

    def to_a10(self, dev, commands=None, extra=None):
        cmds = []
        files = self.files
        log.msg('Device Type (%s) not supported' % dev.vendor)
        return cmds

    def to_juniper(self, dev, commands=None, extra=None):
        if commands is None:
            commands = []
        cmds = [Element('lock-configuration')]
        files = self.files
        action = self.action
        if action == 'overwrite':
            action = 'override'
        for fname in files:
            #log.msg("fname: %s" % fname)
            filecontents = ''
            if not os.path.isfile(fname):
                fname = tftp_dir + fname
            try:
                filecontents = file(fname).read()
            except IOError as e:
                log.msg("Unable to open file: %s" % fname)
            if filecontents == '':
                continue
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = filecontents
            cmds.append(lc)
        if len(commands) > 0:
            lc = Element('load-configuration', action=action, format='text')
            body = SubElement(lc, 'configuration-text')
            body.text = "\n".join(commands)
            cmds.append(lc)
        cmds.append(Element('commit-configuration'))
        return cmds

    def from_juniper(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        #print 'device:', device
        #print 'data len:', len(data)
        self.raw = data
        results = []
        for xml in data:
            jdata = xmltodict.parse(
                ET.tostring(xml),
                postprocessor=strip_juniper_namespace,
                xml_attribs=False
            )
            ##
            ## Leaving jdata structure native until I have a chance
            ##  to look at it (and other vendors' results) and restructure 
            ##  into something sane.
            ## At that point, I will want to make sure that all vendors
            ##  return a dict with the same structure.
            ##
            self.data.append({'device':device, 'data':jdata})
            results.append(jdata)
        self.store_results(device, results)

########NEW FILE########
__FILENAME__ = show_clock

import datetime
from twisted.python import log
from trigger.utils import xmltodict, strip_juniper_namespace
from trigger.contrib.commando import CommandoApplication
import xml.etree.ElementTree as ET
from xml.etree.cElementTree import ElementTree, Element, SubElement

task_name = 'show_clock'

def xmlrpc_show_clock(*args, **kwargs):
    """Run 'show clock' on the specified list of `devices`"""
    log.msg('Creating ShowClock')
    sc = ShowClock(*args, **kwargs)
    d = sc.run()
    return d

class ShowClock(CommandoApplication):
    def to_cisco(self, dev, commands=None, extra=None):
        return ['show clock']
    to_brocade = to_cisco

    def to_arista(self, dev, commands=None, extra=None):
        return ['show clock','show uptime']

    def to_juniper(self, dev, commands=None, extra=None):
        """Generates an etree.Element object suitable for use with JunoScript"""
        cmd = Element('get-system-uptime-information')
        self.commands = [cmd]
        return self.commands

    def from_cisco(self, data, device):
        """Parse Cisco time"""
        # => '16:18:21.763 GMT Thu Jun 28 2012\n'
        fmt = '%H:%M:%S.%f %Z %a %b %d %Y\n'
        ## Need to structure this into a common json structure
        ## {"current-time":""}
        results = []
        for res in data:
            r = self._parse_datetime(res, fmt)
            jdata = {"current-time":r}
            results.append(jdata)
        self.store_results(device, results)

    def from_brocade(self, data, device):
        """
        Parse Brocade time. Brocade switches and routers behave
        differently...
        """
        if device.is_router():
            # => '16:42:04 GMT+00 Thu Jun 28 2012\r\n'
            fmt = '%H:%M:%S GMT+00 %a %b %d %Y\r\n'
        elif device.is_switch():
            # => 'rbridge-id 1: 2012-06-28 16:42:04 Etc/GMT+0\n'
            data = [res.split(': ', 1)[-1] for res in data]
            fmt = '%Y-%m-%d %H:%M:%S Etc/GMT+0\n'
        ## Need to structure this into a common json structure
        ## {"current-time":""}
        results=[]
        for res in data:
            r = self._parse_datetime(res, fmt)
            jdata = {"current-time":r}
            results.append(jdata)
        self.store_results(device, results)

    def from_juniper(self, data, device):
        """Do all the magic to parse Junos interfaces"""
        self.raw = data
        results=[]
        for xml in data:
            jdata = xmltodict.parse(
                ET.tostring(xml),
                postprocessor=strip_juniper_namespace,
                xml_attribs=False
            )
            # xml needs to die a quick, but painful death
            sysupinfo = None
            if 'system-uptime-information' in jdata['rpc-reply']:
                sysupinfo = jdata['rpc-reply']['system-uptime-information']
            elif 'multi-routing-engine-results' in jdata['rpc-reply']:
                try:
                    sysupinfo = jdata['rpc-reply']['multi-routing-engine-results']['multi-routing-engine-item']['system-uptime-information']
                except:
                    pass
            if sysupinfo == None:
                currtime = 'Unable to parse'
                ## need to turn this into an error
            else:
                currtime = sysupinfo['current-time']['date-time']
            # => '2013-02-20 21:41:40 UTC'
            fmt = '%Y-%m-%d %H:%M:%S %Z'
            r = self._parse_datetime(currtime, fmt)
            jdata = {'current-time':r}
            #self.data.append({'device':device,'data':jdata})
            results.append(jdata)
        self.store_results(device, results)
        ## UGH
        ## Some devices start with '{"system-uptime-information":{} }'
        ## Some devices start with '{"multi-routing-engine-results": {"multi-routing-engine-item": {"system-uptime-information":{} }}}'

    ##
    ##  This method should move to trigger.utils or elsewhere
    ##
    def _parse_datetime(self, datestr, fmt):
        """
        Given a date string and a format, try to parse and return
        datetime.datetime object.
        """
        try:
            d = datetime.datetime.strptime(datestr, fmt)
            dstr = d.isoformat()
            return dstr
        except ValueError:
            return datestr


########NEW FILE########
__FILENAME__ = show_version

from twisted.python import log
from trigger.contrib.commando import CommandoApplication
from trigger.utils import xmltodict, strip_juniper_namespace

task_name = 'show_version'

def xmlrpc_show_version(*args,**kwargs):
    """Run 'show version' on the specified list of `devices`"""
    log.msg('Creating ShowVersion')
    sc = ShowVersion(*args,**kwargs)
    d = sc.run()
    return d

class ShowVersion(CommandoApplication):
    """Simple example to run ``show version`` on devices."""
    commands = ['show version']

########NEW FILE########
__FILENAME__ = core
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Do It (Next Generation)

Uses Trigger framework to run commands or load configs on netdevices

This is the base module called by front-end scripts.

main() is never actually called from within here, and takes a single argument
the docommand class that needs to be instanced.

This base function exists so that tools using the module can maintain a consistent 
usability for arguments and output.

Scripts using this module are passed CLI arguments specifying the device(s) and 
command(s)/configuration line(s) desired to run/load.

The list of devices and configuration lines may be specified either directly on
the commandline (comma-separated values) or by specifying files containing these
lists. Any files containing configs *must* be located in a tftp directory.
Configs specified on commandline will either be written to a tftp directory in a
tmp file (future) or run directly on the devices (current)

Please see --help for details on how to construct your arguments

(not yet supported)
--device-path arg to specify directory containing configs.  
Each file would be named as the devname and 
contents would be the config you want loaded to that specific device.
**waiting on enhancements to Commando for implementation**

(not yet supported)
--match arg to allow matching on netdevices.xml fields to compile list of devices
**not waiting on anything, just not implemented in v1**
"""

__author__ = 'Jathan McCollum, Mike Biancianello'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__copyright__ = 'Copyright 2012-2013, AOL Inc.; 2013 Salesforce.com'
__version__ = '3.0'


# Imports
from optparse import OptionParser
import os
import re
import sys


# Globals
PROD_ONLY = False
DEBUG = False
VERBOSE = False
PUSH = False
TIMEOUT = 30


# Exports
__all__ = ('do_work', 'get_commands_from_opts', 'get_devices_from_opts',
           'get_devices_from_path', 'get_jobs', 'get_list_from_file', 'main',
           'parse_args', 'print_results', 'print_work', 'set_globals_from_opts',
           'stage_tftp', 'verify_opts')


# Functions
def main(action_class=None):
    """
    void = main(CommandoClass action_class)
    """
    if action_class is None:
        sys.exit("You must specify a docommand action class.")

    if os.getenv('DEBUG'):
        from twisted.python import log
        log.startLogging(sys.stdout, setStdout=False)

    # Description comes from a class attribute on the action_class
    opts, args = parse_args(sys.argv, description=action_class.description)
    work = get_jobs(opts)
    results = do_work(work, action_class)
    print_results(results)
    print '\nDone.'

def get_jobs(opts):
    """
    list jobs = get_jobs(dict opts)

    Based on which arguments are provided, figure out what is loaded/run on
    which devices and create a list of objects matching the 2::

        job = {'d': [],'c': [],'f': []}

    Is read as "load ALL configs listed in 'c' on ALL devs listed in 'd'". Each
    such grouping is a separate job.

    Future enhancements:
    
    + If multiple jobs exist for the same device we should regroup and optimize
      biggest optimization, though, will come after minor Commando enhancements
      would allow feeding entire list into a single run()
    """
    if DEBUG:
        print '-->get_jobs(%r)' % opts
    work = []
    if opts.device_path:
        # If using device-path, then each device gets a customized list of
        # commands so we have to iterate over the devices and call Commando for
        # each device.
        path = opts.device_path
        if VERBOSE:
            print 'getting devicelist from path: %s' % path

        # Normalize path variable
        if not re.search('/$', path):
            path = path + '/'
        devs = get_devices_from_path(path)

        if VERBOSE:
            print '\tfound %s devices' % len(devs)

        for dev in devs:
            cmds = []
            files = [path + dev]
            job = {'d': [dev], 'c': cmds, 'f': files}
            work.append(job)
    else:
        # If not using device-path, then devs and cmds are referenced on the
        # cmdline.
        devs = get_devices_from_opts(opts)
        cmds = opts.config
        files = opts.config_file
        work = [{'d': devs, 'c': cmds, 'f': files}]
    return work

def get_devices_from_path(path):
    """
    list devicenames = get_devices_from_path(str path)

    If path specified for devices/configs, then the list of filenames
    in dir will correspond to the list of devices.

    The contents of each file contain the config/commands to be loaded/run
    on the specific device.

    Future enhancements

    + verify that the filenames are fqdns
    + verify that the devnames exist in netdevices.xml
    """
    if DEBUG:
        print '-->get_devices_from_path(%r)' % path

    devs = os.listdir(path)
    return devs

def get_list_from_file(path):
    """
    list text = get_list_from_file(str path)

    Specified file (path) will contain a list of newline-separated items. This
    function is used for loading both configs/cmds as well as devices.
    """
    if DEBUG:
        print '-->get_list_from_file(%r)' % path
    ret = []
    with open(path, 'r') as fr:
        ret = fr.readlines()
    ret = [x.strip() for x in ret]
    return ret

def get_devices_from_opts(opts):
    """
    list devicenames = get_devices_from_opts(dict opts)

    User specified on cmdline either a path to a file containing a list of
    devices or an actual list. Return the list!
    """
    if DEBUG:
        print '-->get_devices_from_opts(%r)' % opts
    ret = []
    if len(opts.device_file) > 0:
        ret = []
        for df in opts.device_file:
            devlist = get_list_from_file(df)
            for dev in devlist:
                ret.append(dev)
    else:
        ret = opts.devices 
    if VERBOSE:
        print 'loaded %s devices' % len(ret)
    if DEBUG:
        print 'ret: %s' % ret
    return ret

def get_commands_from_opts(opts):
    """
    list commands = get_commands_from_opts(dict opts)

    User specified on cmdline either a path to a file containing a list of
    commands/config or an actual list. Return the list!
    """
    if DEBUG:
        print '-->get_commands_from_opts(%r)' % opts
    ret = []
    if len(opts.config_file) > 0:
        ret = []
        for cf in opts.config_file:
            cmdlist = get_list_from_file(cf)
            for cmd in cmdlist:
                ret.append(cmd)
    else:
        ret = opts.config
    if VERBOSE:
        print 'loaded %s commands' % len(ret)
    return ret

# https://gist.github.com/jathanism/4543974 for a possible solution.
def do_work(work=None, action_class=None):
    """list results = do_work(list work)"""
    '''
    Cycle through the list of jobs and then actually 
    load the config onto the devices.
    '''
    if work is None:
        work = []
    if DEBUG:
        print '-->do_work(%r)' % work
    #work = [{'d':[],'c':[],'f':[]}]
    ret = []
    if VERBOSE:
        print_work(work)
    for job in work:
        f = job['f']
        d = job['d']
        c = job['c']
        # **These next 2 lines do all the real work for this tool**
        # TODO: This will ultimately fail with a ReactorNotRestartable because calling each action class separately. We need to account for this. See
        n = action_class(devices=d, files=f, commands=c, verbose=VERBOSE,
                        debug=DEBUG, timeout=TIMEOUT, production_only=PROD_ONLY)
        if PUSH:
            if VERBOSE:
                print "running Commando"
            n.run()
        else:
            print "*** Dry-run mode; Skipping command execution***"
        for devname in n.data:
            data = n.data[devname]
            res = {'devname': devname, 'data': data}
            ret.append(res)
        del n
    return ret

def print_work(work=None):
    """
    void = do_work(list work)

    Cycle through the list of jobs and then display the work to be done.
    """
    if work is None:
        work = []
    if DEBUG:
        print "-->print_work(%r)" % work

    for i, job in enumerate(work):
        print "\n***JOB %s ***" % (i + 1)
        f = job['f']
        d = job['d']
        c = job['c']

        if len(d) > 0:
            print "\tDevices"
            for dev in d:
                print "\t\t" + dev

        if len(f) > 0:
            print "\tLoad From Files:"
            for file in f:
                print "\t\t" + file

        if len(c) > 0:
            print "\tRun Commands:"
            for cmd in c:
                print "\t\t" + cmd

    return True

def print_results(results=None):
    """binary success = print_results(list results)"""
    if results is None:
        results = []
    if DEBUG:
        print "-->print_results(%r)" % results
    for res in results:
        devname = res['devname']
        data = res['data']
        print
        print "###"
        print "# %s" % devname
        print "###"
        for d in data:
            cmd = d['cmd']
            out = d['out']
            device = d['dev']
            print '%s# %s\n%s' % (device.shortName, cmd, out),
    return True

def stage_tftp(acls, nonce):
    """
    Need to edit this for cmds, not just acls, but 
    the basic idea is borrowed from ``bin/load_acl``.
    """
    for device in devices:
        source = settings.FIREWALL_DIR + '/acl.%s' % acl
        dest = settings.TFTPROOT_DIR + '/acl.%s.%s' % (acl, nonce)
        try:
            os.stat(dest)
        except OSError:
            try:
                copyfile(source, dest)
                os.chmod(dest, 0644)
            except:
                return None
    return True

def parse_args(argv, description=None):
    if description is None:
        description = 'insert description here.'

    def comma_cb(option, opt_str, value, parser):
        '''OptionParser callback to handle comma-separated arguments.'''
        values = value.split(',') # Split on commas
        values = [v.strip() for v in values] # Strip trailing space from values
        try:
            getattr(parser.values, option.dest).extend(values)
        except AttributeError:
            setattr(parser.values, option.dest, values)

    parser = OptionParser(usage='%prog [options]', description=description,
                          version=__version__)
    # Options to collect lists of devices and commands
    parser.add_option('-d', '--devices', type='string', action='callback',
                      callback=comma_cb, default=[],
                      help='Comma-separated list of devices.')
    parser.add_option('-c', '--config', type='string', action='callback',
                      callback=comma_cb, default=[],
                      help='Comma-separated list of config statements.  '
                           'If your commands have spaces, either enclose the command in " or escape the '
                           'spaces with \\')
    parser.add_option('-D', '--device-file', type='string', action='callback',
                      callback=comma_cb, default=[],
                      help='Specify file with list of devices.')
    parser.add_option('-C', '--config-file', type='string', action='callback',
                      callback=comma_cb, default=[],
                      help='Specify file with list of config statements.  '
                           'The file MUST be in a tftp directory (/home/tftp/<subdir>). '
                           'The fully-qualified path MUST be specified in the argument. '
                           'Do NOT include "conf t" or "wr mem" in your file. '
                           '** If both -c and -C options specified, then -c will execute first, followed by -C')
    parser.add_option('-p', '--device-path', type='string', default=None,
                      help='Specify dir with a file named for each device. '
                           'Contents of each file must be list of commands. '
                           'that you want to run for the device that shares its name with the file. '
                           '** May NOT be used with -d,-c,-D,-C **')
    parser.add_option('-q', '--quiet', action='store_true',
                      help='suppress all standard output; errors/warnings still display.')
    '''
    parser.add_option('--exclude', '--except', type='string',
                      action='callback', callback=comma_cb, dest='exclude',
                      default=[],
                      help='***NOT YET IMPLEMENTED***  '
                           'skip over devices; shell-type patterns '
                           '(e.g., "edge?-[md]*") can be used for devices; for '
                           'multiple excludes, use commas or give this option '
                           'more than once.')
    '''
    parser.add_option('-j', '--jobs', type='int', default=5,
                      help='maximum simultaneous connections (default 5).')
    parser.add_option('-t', '--timeout', type='int', default=TIMEOUT,
                      help="""Time in seconds to wait for each command to
                      complete (default %s).""" % TIMEOUT)
    # Booleans below
    parser.add_option('-v','--verbose', action='store_true', default=False,
                      help='verbose output.')
    parser.add_option('-V','--debug', action='store_true', default=False,
                      help='debug output.')
    parser.add_option('--push', action='store_true', default=False,
                      help='actually do stuff.  Default is False.')

    opts, args = parser.parse_args(argv)

    # Validate option logic
    ok, err = verify_opts(opts)
    if not ok:
        print '\n', err
        sys.exit(1)
    if opts.quiet:
        sys.stdout = NullDevice()

    # Mutate some global sentinel values based on opts
    set_globals_from_opts(opts)

    return opts, args

def verify_opts(opts):
    """
    Validate opts and return whether they are ok.

    returns True if all is good, otherwise (False, errormsg)
    """
    ok = True
    err = ''
    isd = len(opts.devices) > 0
    isc = len(opts.config) > 0
    isdf = len(opts.device_file) > 0
    iscf = len(opts.config_file) > 0
    isp = opts.device_path is not None
    if isp:
        if not os.path.isdir(opts.device_path):
            return False, 'ERROR: %r is not a valid path\n' % path
        else:
            return True, ''
    elif isdf or iscf or isd or isc:
        #return False, "ERROR: Sorry, but only --device-path is supported at this time\n"
        pass

    # Validate opts.device_file
    if isdf:
        for df in opts.device_file:
            if not os.path.exists(df):
                ok = False
                err += 'ERROR: Device file %r does not exist\n' % df

    # Validate opts.config_file
    if iscf:
        for cf in opts.config_file:
            if not os.path.exists(cf):
                ok = False
                err += 'ERROR: Config file %r does not exist\n' % cf

    # If opts.devices is set, opts.device_file must also be set
    if not isd and not isdf:
        ok = False
        err += 'ERROR: You must specify at least one device\n'
    # If opts.config is set, opts.config_file must also be set
    if not isc and not iscf:
        ok = False
        err += 'ERROR: You must specify at least one command\n'

    # TODO: One option here would be to take opts.config, write to file, and
    # convert that to opts.config_file. That way, the rest of the script only
    # has to care about one type of input.
    return ok, err

# TODO: There's gotta be a better way.
def set_globals_from_opts(opts):
    global DEBUG
    global VERBOSE
    global PUSH
    global TIMEOUT
    DEBUG = opts.debug
    VERBOSE = opts.verbose
    PUSH = opts.push
    TIMEOUT = opts.timeout


########NEW FILE########
__FILENAME__ = server
"""
Trigger Twisted XMLRPC server with an SSH manhole. Supports SSL.

This provides a daemonized Twisted reactor loop, Trigger and client
applications do not have to co-habitate. Using the XMLRPC server model, all
Trigger compatibility tasks can be executed using simple XMLRPC clients that
call the appropriate method with arguments on the local XMLRPC server instance.

New methods can be added by way of plugins.

See ``examples/xmlrpc_server`` in the Trigger source distribution for a simple
usage example.
"""

import os
import sys
import types

from trigger.contrib.commando import CommandoApplication
from trigger.utils import importlib
from twisted.internet import defer
from twisted.python import log
from twisted.web import xmlrpc, server


# Enable Deferred debuging if ``DEBUG`` is set.
if os.getenv('DEBUG'):
    defer.setDebugging(True)


class TriggerXMLRPCServer(xmlrpc.XMLRPC):
    """
    Twisted XMLRPC server front-end for Commando
    """
    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        self.allowNone = True
        self.useDateTime = True

        self._handlers = []
        self._procedure_map = {}
        self.addHandlers(self._handlers)

    def lookupProcedure(self, procedurePath):
        """
        Lookup a method dynamically.

        1. First, see if it's provided by a sub-handler.
        2. Or try a self-defined method (prefixed with `xmlrpc_`)
        3. Lastly, try dynamically mapped methods.
        4. Or fail loudly.
        """
        log.msg("LOOKING UP:", procedurePath)

        if procedurePath.find(self.separator) != -1:
            prefix, procedurePath = procedurePath.split(self.separator, 1)
            handler = self.getSubHandler(prefix)
            if handler is None:
                raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                                            "no such subHandler %s" % prefix)
            return handler.lookupProcedure(procedurePath)

        # Try self-defined methods first...
        f = getattr(self, "xmlrpc_%s" % procedurePath, None)

        # Try mapped methods second...
        if f is None:
            f = self._procedure_map.get(procedurePath, None)

        if not f:
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "procedure %s not found" % procedurePath)
        elif not callable(f):
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "procedure %s not callable" % procedurePath)
        else:
            return f

    def addHandlers(self, handlers):
        """Add multiple handlers"""
        for handler in handlers:
            self.addHandler(handler)

    def addHandler(self, handler):
        """
        Add a handler and bind it to an XMLRPC procedure.

        Handler must a be a function or an instance of an object with handler
        methods.
        """
        # Register it
        log.msg("Adding handler: %s" % handler)
        self._handlers.append(handler)

        # If it's a function, bind it as its own internal name.
        if type(handler) in (types.BuiltinFunctionType, types.FunctionType):
            name = handler.__name__
            if name.startswith('xmlrpc_'):
                name = name[7:] # If it starts w/ 'xmlrpc_', slice it out!
            log.msg("Mapping function %s..." % name)
            self._procedure_map[name] = handler
            return None

        # Otherwise, walk the methods on any class objects and bind them by
        # their attribute name.
        for method in dir(handler):
            if not method.startswith('_'):
                log.msg("Mapping method %s..." % method)
                self._procedure_map[method] = getattr(handler, method)

    def listProcedures(self):
        """Return a list of the registered procedures"""
        return self._procedure_map.keys()

    def xmlrpc_add_handler(self, mod_name, task_name, force=False):
        """
        Add a handler object from a remote call.
        """
        module = None
        if mod_name in sys.modules:
            # Check if module is already loaded
            if force:
                log.msg("Forcing reload of handler: %r" % task_name)
                # Allow user to force reload of module
                module = reload(sys.modules[mod_name])
            else:
                # If not forcing reload, don't bother with the rest
                log.msg("%r already loaded" % mod_name)
                return None
        else:
            log.msg("Trying to add handler: %r" % task_name)
            try:
                module = importlib.import_module(mod_name, __name__)
            except NameError as msg:
                log.msg('NameError: %s' % msg)
            except:
                pass

        if not module:
            log.msg("    Unable to load module: %s" % mod_name)
            return None
        else:
            handler = getattr(module, 'xmlrpc_' + task_name)
            # XMLRPC methods will not accept kwargs. Instead, we pass 2 position
            # args: args and kwargs, to a shell method (dummy) that will explode
            # them when sending to the user defined method (handler).
            def dummy(self, args, kwargs):
                return handler(*args, **kwargs)

            # TODO (jathan): Make this work!!
            # This just simply does not work.  I am not sure why, but it results in a
            # "<Fault 8001: 'procedure config_device not found'>" error!
            # # Bind the dummy shell method to TriggerXMLRPCServer. The function's
            # # name will be used to map it to the "dummy" handler object.
            # dummy.__name__ = task_name
            # self.addHandler(dummy)

            # This does work.
            # Bind the dummy shell method to TriggerXMLRPCServer as 'xmlrpc_' + task_name
            setattr(TriggerXMLRPCServer, 'xmlrpc_' + task_name, dummy)

    def xmlrpc_list_subhandlers(self):
        return list(self.subHandlers)

    def xmlrpc_execute_commands(self, args, kwargs):
        """Execute ``commands`` on ``devices``"""
        c = CommandoApplication(*args, **kwargs)
        d = c.run()
        return d

    def xmlrpc_add(self, x, y):
        """Adds x and y"""
        return x + y

    def xmlrpc_fault(self):
        """
        Raise a Fault indicating that the procedure should not be used.
        """
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")

    def _ebRender(self, failure):
        """
        Custom exception rendering.
        Ref: https://netzguerilla.net/iro/dev/_modules/iro/view/xmlrpc.html
        """
        if isinstance(failure.value, Exception):
            msg = """%s: %s""" % (failure.type.__name__, failure.value.args[0])
            return xmlrpc.Fault(400, msg)
        return super(TriggerXMLRPCServer, self)._ebRender(self, failure)

# XXX (jathan): Note that this is out-of-sync w/ the twistd plugin and is
# probably broken.
def main():
    """To daemonize as a twistd plugin! Except this doesn't work and these"""
    from twisted.application.internet import TCPServer, SSLServer
    from twisted.application.service import Application
    from twisted.internet import ssl

    rpc = TriggerXMLRPCServer()
    xmlrpc.addIntrospection(rpc)

    server_factory = server.Site(rpc)
    application = Application('trigger_xmlrpc')

    #xmlrpc_service = TCPServer(8000, server_factory)
    ctx = ssl.DefaultOpenSSLContextFactory('server.key', 'cacert.pem')
    xmlrpc_service = SSLServer(8000, server_factory, ctx)
    xmlrpc_service.setServiceParent(application)

    return application

if __name__ == '__main__':
    # To run me as a daemon:
    # twistd -l server.log --pidfile server.pid -y server.py
    application = main()

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

"""
All custom exceptions used by Trigger. Where possible built-in exceptions are
used, but sometimes we need more descriptive errors.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

from simpleparse.error import ParserSyntaxError


class TriggerError(Exception):
    """A base exception for all Trigger-related errors."""

class ImproperlyConfigured(TriggerError):
    """Raised when something is improperly... configured..."""

#####################
# ACL Exceptions
#####################
class ACLError(TriggerError):
    """A base exception for all ACL-related errors."""

class ParseError(ACLError):
    """
    Raised when there is an error parsing/normalizing an ACL that tries to tell
    you where it failed.
    """
    def __init__(self, reason, line=None, column=None):
        self.reason = reason
        self.line = line
        self.column = column

    def __str__(self):
        s = self.reason
        if self.line is not None and self.line > 1:
            s += ' at line %d' % self.line
        return s

# ACL validation/formating errors
class BadTermName(ACLError):
    """
    Raised when an invalid name is assigned to a `~trigger.acl.parser.Term`
    object
    """

class MissingTermName(ACLError):
    """
    Raised when a an un-named Term is output to a format that requires Terms to
    be named (e.g. Juniper).
    """

class VendorSupportLacking(ACLError):
    """Raised when a feature is not supported by a given vendor."""

# ACL naming errors
class ACLNameError(ACLError):
    """A base exception for all ACL naming errors."""

class MissingACLName(ACLNameError):
    """Raised when an ACL object is missing a name."""

class BadACLName(ACLNameError):
    """Raised when an ACL object is assigned an invalid name."""

# Misc. action errors
class ActionError(ACLError):
    """A base exception for all `~trigger.acl.parser.Term` action errors."""

class UnknownActionName(ActionError):
    """Raised when an action assigned to a ~trigger.acl.parser.Term` object is unknown."""

class BadRoutingInstanceName(ActionError):
    """
    Raised when a routing-instance name specified in an action is invalid.
    """

class BadRejectCode(ActionError):
    """Raised when an invalid rejection code is specified."""

class BadCounterName(ActionError):
    """Raised when a counter name is invalid."""

class BadForwardingClassName(ActionError):
    """Raised when a forwarding-class name is invalid."""

class BadIPSecSAName(ActionError):
    """Raised when an IPSec SA name is invalid."""

class BadPolicerName(ActionError):
    """Raised when a policer name is invalid."""

# Argument matching errors
class MatchError(ACLError):
    """
    A base exception for all errors related to Term
    `~trigger.acl.parser.Matches` objects.
    """

class BadMatchArgRange(MatchError):
    """
    Raised when a match condition argument does not fall within a specified
    range.
    """

class UnknownMatchType(MatchError):
    """Raised when an unknown match condition is specified."""

class UnknownMatchArg(MatchError):
    """Raised when an unknown match argument is specified."""

# ACLs database errors
class ACLSetError(ACLError):
    """A base exception for all ACL Set errors."""

class InvalidACLSet(ACLSetError):
    """Raised when an invalid ACL set is specified."""

# ACL/task queue errors
class ACLQueueError(TriggerError):
    """Raised when we encounter errors communicating with the Queue"""

# ACL workflow errors
class ACLStagingFailed(ACLError):
    """Raised when we encounter errors staging a file for loading"""

#####################
# NetScreen Exceptions
#####################
class NetScreenError(TriggerError):
    """A general exception for NetScreen devices."""

class NetScreenParseError(NetScreenError):
    """Raised when a NetScreen policy cannot be parsed."""

#####################
# Commando Exceptions
#####################
class CommandoError(TriggerError):
    """A base exception for all Commando-related errors."""

class UnsupportedVendor(CommandoError):
    """Raised when a vendor is not supported by Trigger."""

class MissingPlatform(CommandoError):
    """Raised when a specific device platform is not supported."""

#####################
# Twister Exceptions
#####################
class TwisterError(TriggerError):
    """A base exception for all errors related to Twister."""

class LoginFailure(TwisterError):
    """Raised when authentication to a remote system fails."""

class LoginTimeout(LoginFailure):
    """Raised when login to a remote systems times out."""

class ConnectionFailure(TwisterError):
    """Raised when a connection attempt totally fails."""

class SSHConnectionLost(TwisterError):
    """Raised when an SSH connection is lost for any reason."""
    def __init__(self, code, desc):
        self.code = code
        TwisterError.__init__(self, desc)

class CommandTimeout(TwisterError):
    """Raised when a command times out while executing."""

class CommandFailure(TwisterError):
    """
    Raised when a command fails to execute, such as when it results in an
    error.
    """

class IoslikeCommandFailure(CommandFailure):
    """Raised when a command fails on an IOS-like device."""

class NetscalerCommandFailure(CommandFailure):
    """Raised when a command fails on a NetScaler device."""

class JunoscriptCommandFailure(CommandFailure):
    """Raised when a Junoscript command fails on a Juniper device."""
    def __init__(self, tag):
        self.tag = tag

    def __str__(self):
        s = 'JunOS XML command failure:\n'
        ns = '{http://xml.juniper.net/xnm/1.1/xnm}'
        for e in self.tag.findall('.//%serror' % ns):
            for e2 in e:
                s += '  %s: %s\n' % (e2.tag.replace(ns, ''), e2.text)
        return s

#####################
# NetDevices Exceptions
#####################
class NetDeviceError(TriggerError):
    """A base exception for all NetDevices related errors."""

class BadVendorName(NetDeviceError):
    """Raised when a Vendor object has a problem with the name."""

class LoaderFailed(NetDeviceError):
    """Raised when a metadata loader failed to load from data source."""

#####################
# Notification Exceptions
#####################
class NotificationFailure(TriggerError):
    """Raised when a notification fails and has not been silenced."""

#####################
# Bounce/Changemgmt Exceptions
#####################
class InvalidBounceWindow(TriggerError):
    """Raised when a BounceWindow object is kind of not good."""

########NEW FILE########
__FILENAME__ = gorc
# -*- coding: utf-8 -*-

"""
This is used by :doc:`../usage/scripts/go` to execute commands upon login to a
device. A user may specify a list of commands to execute for each vendor. If
the file is not found, or the syntax is bad, no commands will be passed to the
device.

By default, only a very limited subset of root commands are allowed to be
specified within the ``.gorc``. Any root commands not explicitly permitted will
be filtered out prior to passing them along to the device.

The only public interface to this module is `~trigger.gorc.get_init_commands`.
Given a ``.gorc`` That looks like this::

    cisco:
        term mon
        terminal length 0
        show clock

This is what is returned::

    >>> from trigger import gorc
    >>> gorc.get_init_commands('cisco')
    ['term mon', 'terminal length 0', 'show clock']

You may also pass a list of commands as the ``init_commands`` argument to the
`~trigger.twister.connect` function (or a `~trigger.netdevices.NetDevice`
object's method of the same name) to override anything specified in a user's
``.gorc``::

    >>> from trigger.netdevices import NetDevices
    >>> nd = NetDevices()
    >>> dev = nd.find('foo1-abc')
    >>> dev.connect(init_commands=['show clock', 'exit'])
    Connecting to foo1-abc.net.aol.com.  Use ^X to exit.

    Fetching credentials from /home/jathan/.tacacsrc
    foo1-abc#show clock
    22:48:24.445 UTC Sat Jun 23 2012
    foo1-abc#exit
    >>>

"""

# Imports
import ConfigParser
import os
import sys
from twisted.python import log
from trigger.conf import settings

# Constants
GORC_PATH = os.path.expanduser(settings.GORC_FILE)
INIT_COMMANDS_SECTION = 'init_commands'


# Exports
#__all__ = ('get_init_commands',)


# Functions
def read_config(filepath=GORC_PATH):
    """
    Read the .gorc file

    :param filepath: The path to the .gorc file
    :returns: A parsed ConfigParser object
    """
    config = ConfigParser.RawConfigParser()
    try:
        status = config.read(filepath)
        if filepath not in status:
            log.msg('File not found: %r' % filepath)
            return None
    except (ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError) as err:
        log.msg(err, debug=True)
        return None
    else:
        return config

    raise RuntimeError('Something went crazy wrong with read_config()')

def filter_commands(cmds, allowed_commands=None):
    """
    Filters root commands from ``cmds`` that are not explicitly allowed.

    Allowed commands are defined using :setting:`GORC_ALLOWED_COMMANDS`.

    :param cmds:
        A list of commands that should be filtered

    :param allowed_commands:
        A list of commands that are allowed

    :returns:
        Filtered list of commands
    """
    if allowed_commands is None:
        allowed_commands = settings.GORC_ALLOWED_COMMANDS
    ret = []
    for cmd in cmds:
        root = cmd.split()[0]
        if root in allowed_commands:
            ret.append(cmd)
        else:
            log.msg('init_command not allowed: %r' % cmd, debug=True)
    return ret

def parse_commands(vendor, section=INIT_COMMANDS_SECTION, config=None):
    """
    Fetch the init commands.

    :param vendors:
        A vendor name (e.g. 'juniper')

    :param section:
        The section of the config

    :param config:
        A parsed ConfigParser object

    :returns:
        List of commands
    """
    if config is None:
        log.msg('No config data, not sending init commands', debug=True)
        return []

    try:
        cmdstr = config.get(section, vendor)
    except ConfigParser.NoSectionError as err:
        log.msg('%s in %s' % (err, GORC_PATH), debug=True)
        return []
    except ConfigParser.NoOptionError as err:
        log.msg(err, debug=True)
        return []
    else:
        cmds = (c for c in cmdstr.splitlines() if c != '')
        cmds = filter_commands(cmds)
        return cmds

    raise RuntimeError('Something went crazy wrong with get_init_commands()')

def get_init_commands(vendor):
    """
    Return a list of init commands for a given vendor name. In all failure
    cases it will return an empty list.

    :param vendor:
        A vendor name (e.g. 'juniper')

    :returns:
        list of commands
    """
    config = read_config()
    return parse_commands(vendor, config=config)

if __name__ == '__main__':
    #os.environ['DEBUG'] = '1'
    if os.environ.get('DEBUG', None) is not None:
        log.startLogging(sys.stdout, setStdout=False)

    print get_init_commands('juniper')
    print get_init_commands('cisco')
    print get_init_commands('arista')
    print get_init_commands('foundry')

########NEW FILE########
__FILENAME__ = loader
"""
Wrapper for loading metadata from storage of some sort (e.g. filesystem,
database)

This uses NETDEVICE_LOADERS settings, which is a list of loaders to use.
Each loader is expected to have this interface::

    callable(data_source, **kwargs)

``data_source`` is typically a file path from which to load the metadata, but can
be also be a list/tuple of [data_source, *args]
``kwargs`` are any optional keyword arguments you wish to send along.

The loader must return an iterable of key/value pairs (dicts, 2-tuples, etc.).

Each loader should have an ``is_usable`` attribute set. This is a boolean that
specifies whether the loader can be used with this Python installation. Each
loader is responsible for setting this when it is initialized.

This code is based on Django's template loader code: http://bit.ly/WWOLU3
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2013, AOL Inc.'
__version__ = '1.0'

from trigger.exceptions import ImproperlyConfigured, LoaderFailed
from trigger.utils.importlib import import_module
from trigger.conf import settings
from twisted.python import log


# Exports
__all__ = ('BaseLoader', 'load_metadata')


# Classes
class BaseLoader(object):
    is_usable = False

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, data_source, **kwargs):
        return self.load_data(data_source, **kwargs)

    def load_data(self, data_source, **kwargs):
        data = self.load_data_source(data_source, **kwargs)
        return data

    def load_data_source(self, data_source, **kwargs):
        """
        Returns an iterable of key/value pairs for the given ``data_source``.
        """
        raise NotImplementedError

    def reset(self):
        """
        Resets any state maintained by the loader instance.
        """
        pass


# Functions
def find_data_loader(loader):
    """
    Given a ``loader`` string/list/tuple, try to unpack, load it, and return the
    callable loader object.

    If ``loader`` is specified as string, treat it as the fully-qualified
    Python path to the callable Loader object.

    Optionally, if `loader`` is a list/tuple, the first item in the tuple should be the
    Loader's module path, and subsequent items are passed to the Loader object
    during initialization. This could be useful in initializing a custom Loader
    for a database backend, for example.

    :param loader:
        A string represnting the Python path to a Loader object, or list/tuple
        of loader path and args to pass to the Loader.
    """
    if isinstance(loader, (tuple, list)):
        loader, args = loader[0], loader[1:]
    else:
        args = []

    log.msg("BUILDING LOADER: %s; WITH ARGS: %s" % (loader, args))
    err_template = "Error importing data source loader %s: '%s'"
    if isinstance(loader, basestring):
        module, attr = loader.rsplit('.', 1)
        try:
            mod = import_module(module)
        except ImportError as err:
            raise ImproperlyConfigured(err_template % (loader, err))

        try:
            DataLoader = getattr(mod, attr)
        except AttributeError as err:
            raise ImproperlyConfigured(err_template % (loader, err))

        if hasattr(DataLoader, 'load_data_source'):
            func = DataLoader(*args)
        else:
            # Try loading module the old-fashioned way where string is full
            # path to callabale.
            if args:
                raise ImproperlyConfigured("Error importing data source loader %s: Can't pass arguments to function-based loader!" % loader)
            func = DataLoader

        if not func.is_usable:
            import warnings
            warnings.warn("Your NETDEVICES_LOADERS setting includes %r, but your Python installation doesn't support that type of data loading. Consider removing that line from NETDEVICES_LOADERS." % loader)
            return None
        else:
            return func
    else:
        raise ImproperlyConfigured('Loader does not define a "load_data" callable data source loader.')

def load_metadata(data_source, **kwargs):
    """
    Iterate thru data loaders to load metadata.

    Loaders should return an iterable of dict/2-tuples or ``None``. It will try
    each one until it can return data. The first one to return data wins.

    :param data_source:
        Typically a file path, but it can be any data format you desire that
        can be passed onto a Loader object to retrieve metadata.

    :param kwargs:
        Optional keyword arguments you wish to pass to the Loader.
    """
    # Iterate and build a loader callables, call them, stop when we get data.
    tried = []
    log.msg('LOADING DATA FROM:', data_source)
    for loader_name in settings.NETDEVICES_LOADERS:
        loader = find_data_loader(loader_name)
        log.msg('TRYING LOADER:', loader)
        if loader is None:
            log.msg('CANNOT USE LOADER:', loader)
            continue

        try:
            # Pass the args to the loader!
            data = loader(data_source, **kwargs)
            log.msg('LOADER: SUCCESS!')
        except LoaderFailed as err:
            tried.append(loader)
            log.msg('LOADER - FAILURE: %s' % err)
            continue
        else:
            # Successfully parsed (we hope)
            if data is not None:
                log.msg('LOADERS TRIED: %r' % tried)
                return data
            else:
                tried.append(loader)
                continue

    # All loaders failed. We don't want to get to this point!
    raise RuntimeError('No data loaders succeeded. Tried: %r' % tried)

########NEW FILE########
__FILENAME__ = filesystem
"""
Built-in Loader objects for loading `~trigger.netdevices.NetDevice` metadata
from the filesystem.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2013, AOL Inc.'
__version__ = '1.1'

import itertools
import os
from trigger.conf import settings
from trigger.netdevices.loader import BaseLoader
from trigger import exceptions, rancid
from trigger.exceptions import LoaderFailed
try:
    import simplejson as json # Prefer simplejson because of SPEED!
except ImportError:
    import json
import xml.etree.cElementTree as ET

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

class JSONLoader(BaseLoader):
    """
    Wrapper for loading metadata via JSON from the filesystem.

    Parse 'netdevices.json' and return list of JSON objects.
    """
    is_usable = True

    def get_data(self, data_source):
        with open(data_source, 'r') as contents:
            # TODO (jathan): Can we somehow return an generator like the other
            # _parse methods? Maybe using JSONDecoder?
            data = json.load(contents)
        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class XMLLoader(BaseLoader):
    """
    Wrapper for loading metadata via XML from the filesystem.

    Parse 'netdevices.xml' and return a list of node 2-tuples (key, value).
    These are as good as a dict without the extra dict() call.
    """
    is_usable = True

    def get_data(self, data_source):
        #Parsing the complete file into a tree once and extracting outthe
        # device nodes is faster than using iterparse(). Curses!!
        xml = ET.parse(data_source).findall('device')

        # This is a generator within a generator. Trust me, it works in _populate()
        data = (((e.tag, e.text) for e in node.getchildren()) for node in xml)

        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class RancidLoader(BaseLoader):
    """
    Wrapper for loading metadata via RANCID from the filesystem.

    Parse RANCID's ``router.db`` and return a generator of node 2-tuples (key,
    value).
    """
    is_usable = True

    def get_data(self, data_source, recurse_subdirs=None):
        data = rancid.parse_rancid_data(data_source,
                                        recurse_subdirs=recurse_subdirs)
        return data

    def load_data_source(self, data_source, **kwargs):
        # We want to make sure that we've set this variable
        recurse_subdirs = kwargs.get('recurse_subdirs',
                                     settings.RANCID_RECURSE_SUBDIRS)
        try:
            return self.get_data(data_source, recurse_subdirs)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class SQLiteLoader(BaseLoader):
    """
    Wrapper for loading metadata via SQLite from the filesystem.

    Parse 'netdevices.sql' and return a list of stuff.
    """
    is_usable = SQLITE_AVAILABLE

    def get_data(self, data_source, table_name='netdevices'):
        connection = sqlite3.connect(data_source)
        cursor = connection.cursor()

        # Get the column names. This is a simple list strings.
        colfetch  = cursor.execute('pragma table_info(%s)' % table_name)
        results = colfetch.fetchall()
        columns = [r[1] for r in results]

        # And the devices. This is a list of tuples whose values match the indexes
        # of the column names.
        devfetch = cursor.execute('select * from %s' % table_name)
        devrows = devfetch.fetchall()

        # Another generator within a generator, which structurally is a list of
        # lists containing 2-tuples (key, value).
        data = (itertools.izip(columns, row) for row in devrows)

        return data

    def load_data_source(self, data_source, **kwargs):
        table_name = kwargs.get('table_name', 'netdevices')
        try:
            return self.get_data(data_source, table_name)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class CSVLoader(BaseLoader):
    """
    Wrapper for loading metadata via CSV from the filesystem.

    This leverages the functionality from the `~trigger.rancid`` library.

    At the bare minimum your CSV file must be populated with 2-tuples of
    "nodeName,manufacturer" (e.g. "test1-abc.net.aol.com,cisco"), separated by
    newlines. The ``deviceType`` will default to whatever is specified in
    :settings:`FALLBACK_TYPE` and ``deviceStatus`` will default to "up"
    ("PRODUCTION").

    At max you may provide "nodeName,vendor,deviceStatus,deviceType" just like
    what you'd expect from RANCID's ``router.db`` file format.
    """
    is_usable = True

    def get_data(self, data_source):
        root_dir, filename = os.path.split(data_source)
        data = rancid.parse_rancid_file(root_dir, filename, delimiter=',')
        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

########NEW FILE########
__FILENAME__ = netscreen
# -*- coding: utf-8 -*-

"""
Parses and manipulates firewall policy for Juniper NetScreen firewall devices.
Broken apart from acl.parser because the approaches are vastly different from each
other.
"""

__author__ = 'Jathan McCollum, Mark Thomas'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2007-2012, AOL Inc.'
__version__ = '1.2.2'

import IPy
from trigger.acl.parser import (Protocol, check_range, literals, TIP,
                                do_protocol_lookup, make_nondefault_processor,
                                ACLParser, ACLProcessor, default_processor, S)
from trigger.acl.tools import create_trigger_term
from trigger import exceptions


# TODO (jathan): Implement __all__
__all__ = ('NSRawPolicy', 'NSRawGroup', 'NetScreen', 'NSGroup',
           'NSServiceBook', 'NSAddressBook', 'NSAddress', 'NSService',
           'NSPolicy')

# Classes
class NetScreen(object):
    """
    Parses and generates NetScreen firewall policy.
    """
    def __init__(self):
        self.service_book   = NSServiceBook()
        self.address_book   = NSAddressBook()
        self.interfaces     = []
        self.address_groups = []
        self.service_groups = []
        self.policies       = []
        self.grammar        = []

        rules = {
            #
            # normal shiznitches.
            #
            'digits':    '[0-9]+',
            '<ts>':      '[ \\t]+',
            '<ws>':      '[ \\t\\n]+',
            '<EOL>':     "('\r'?,'\n')/EOF",
            'alphanums': '[a-zA-z0-9]+',
            'word':      '[a-zA-Z0-9_:./-]+',
            'anychar':   "[ a-zA-Z0-9.$:()&,/'_-]",
            'nonspace':  "[a-zA-Z0-9.$:()&,/'_-]+",
            'ipv4':      ('digits, (".", digits)*', TIP),
            'cidr':      ('ipv4, "/", digits', TIP),
            'macaddr':   '[0-9a-fA-F:]+',
            'protocol':  (literals(Protocol.name2num) + ' / digits',
                            do_protocol_lookup),
            'tcp':       ('"tcp" / "6"', Protocol('tcp')),
            'udp':       ('"udp" / "17"', Protocol('udp')),
            'icmp':      ('"icmp" / "1"', Protocol('icmp')),
            'root':      'ws?, netscreen, ws?',
            #
            # netscreen shiznit
            #
            'kw_address':      ('"address"'),
            'kw_service':      ('"service"'),
            'ns_word':         ('"\\\""?, word, "\\\""?'),
            'ns_nonspace':     ('"\\\""?, nonspace, "\\\""?'),
            'ns_quoted_word':  ('"\\\"",(word,ws?)+,"\\\""', lambda x: ''.join(x)[1:-1]),
            'ns_quoted_nonspace':  ('"\\\"",(nonspace,ws?)+,"\\\""', lambda x: ''.join(x)[1:-1]),
            S('netmask_conv'): ('(ipv4, ws, ipv4) / cidr',
                                    self.netmask2cidr),
            S('portrange'):    ('digits,"-",digits',
                                lambda (x,y):
                                    (int(x), int(y))),
            S('service'):      ('"set", ws, "service", ws, ns_word, ws,' \
                                '"protocol", ws, protocol, ws, "src-port", ws, portrange, ws,' \
                                '"dst-port", ws, portrange',
                                lambda x:
                                    NSService(name=x[0], protocol=x[1], source_port=x[2],
                                    destination_port=x[3])),
            S('address'):      ('"set", ws, "address", ws, ns_nonspace, ws, ' \
                                'ns_word, ws, netmask_conv, (ws, ns_quoted_word)?',
                                lambda x: NSAddress(zone=x[0], name=x[1], addr=x[2])),
            'kw_log':    ('"log"'),
            'kw_count':  ('"count"'),
            'kw_reject': ('"reject"'),
            'kw_permit': ('"permit"'),
            'modifiers': ('("deny"/"nat"/"permit"/"reject"/"tunnel"/"log"/"count"),ws?'),
            S('policy_rule'):  ('"from", ws, ns_word, ws, "to", ws, ns_word, ws, '\
                                'ns_word, ws, ns_word, ws, ns_word, ws, modifiers+',
                                lambda x:
                                    {'src-zone':x[0], 'dst-zone':x[1],
                                    'src-address':[x[2]], 'dst-address':[x[3]],
                                    'service':[x[4]]}),
            S('src_address'):  ('"src-address", ws, ns_word',
                                lambda x: {'src-address':x[0]}),
            S('dst_address'):  ('"dst-address", ws, ns_word',
                                lambda x: {'dst-address':x[0]}),
            S('service_short'):('"service", ws, ns_word',
                                lambda x: {'service':x[0]}),
            #S('name'):         ('"name", ws, ns_quoted_word',
            S('name'):         ('"name", ws, ns_quoted_nonspace',
                                lambda x: {'name':x[0]}),
            'global':          ('"global" / "Global"',
                                lambda x: {'global':1}),
            S('policy_set_id'):     ('"set", ws, src_address / service_short / dst_address'),
            # the thing inside a policy set id 0 stuff.
            S('policy_set_id_grp'): ('(policy_set_id, ws?)+, "exit", ws', self.concatenate_grp),
            S('policy_id'):        ('"id", ws, digits',
                                lambda x: {'id':int(x[0])}),
            'policy_id_null':  ('"id", ws, digits, ws, "exit"', lambda x: {}),
            # our main policy definition.
            S('policy'):       ('"set", ws, "policy", ws,' \
                                '((global, ws)?, (policy_id, ws)?, (name, ws)?)?,' \
                                'policy_set_id_grp / policy_rule / "exit"',
                                lambda x: NSRawPolicy(x)),
            'address_group':   ('kw_address, ws, ns_word, ws, ns_word, (ws, "add", ws, ns_word)?'),
            'service_group':   ('kw_service, ws, ns_word, (ws, "add", ws, ns_word)?'),
            S('group'):        ('"set", ws, "group", ws, address_group / service_group',
                                    lambda x:NSRawGroup(x[0])),
            '>line<':          ('ws?, service / address / group / policy, ws?'),
            S('netscreen'):    ('(line)+', self.handle_raw_netscreen)
        }

        for production, rule, in rules.iteritems():
            if isinstance(rule, tuple):
                assert len(rule) == 2
                setattr(ACLProcessor, production, make_nondefault_processor(rule[1]))
                self.grammar.append('%s := %s' % (production, rule[0]))
            else:
                setattr(ACLProcessor, production, default_processor)
                self.grammar.append('%s := %s' % (production, rule))

        self.grammar = '\n'.join(self.grammar)

    def parse(self, data):
        """Parse policy into list of NSPolicy objects."""
        parser = ACLParser(self.grammar)
        try:
            string = data.read()
        except AttributeError:
            string = data

        success, children, nextchar = parser.parse(string)

        if success and nextchar == len(string):
            assert len(children) == 1
            return children[0]
        else:
            line = string[:nextchar].count('\n') + 1
            column = len(string[string[nextchar].rfind('\n'):nextchar]) + 2
            print "Error at: ", string[nextchar:]
            raise exceptions.ParseError('Could not match syntax. Please report as a bug.', line, column)

    def concatenate_grp(self, x):
        """Used by NetScreen class when grouping policy members."""
        ret = {}
        for entry in x:
            for key, val in entry.iteritems():
                if key in ret:
                    ret[key].append(val)
                else:
                    ret[key] = [val]
        return ret

    def netmask2cidr(self, iptuple):
        """Converts dotted-quad netmask to cidr notation"""
        if len(iptuple) == 2:
            addr, mask = iptuple
            ipstr = addr.strNormal() + '/' + mask.strNormal()
            return TIP(ipstr)
        return TIP(iptuple[0].strNormal())

    def handle_raw_netscreen(self,rows):
        """
        The parser will hand it's final output to this function, which decodes
        and puts everything in the right place.
        """
        for node in rows:
            if isinstance(node, NSAddress):
                self.address_book.append(node)
            elif isinstance(node, NSService):
                self.service_book.append(node)
            elif isinstance(node, NSGroup):
                if node.type == 'address':
                    self.address_book.append(node)
                elif node.type == 'service':
                    self.service_book.append(node)
                else:
                    raise "Unknown NSGroup type: %s" % node.type
            elif isinstance(node, NSRawGroup):
                # take a raw parsed group entry,
                # try to find it's entry in either the addressbook,
                # or the service book. update and append to the group
                # with the proper addresses/services
                zone = None
                type = None
                name = None
                entry = None

                if len(node) == 4:
                    (type, zone, name, entry) = node
                else:
                    (type, name, entry) = node

                if entry == None:
                    continue

                if type =='address':
                    address_find = self.address_book.find(entry, zone)
                    group_find   = self.address_book.find(name, zone)
                    # does the thing being added have an entry?
                    if not address_find:
                        raise "GROUP ADD: no address book entry for %s" % (entry)

                    if group_find:
                        # we already have an entry for this group? if so
                        # just append.
                        group_find.append(address_find)
                    else:
                        # else we have to create a new group
                        new_group = NSGroup(name=name, type='address',
                          zone=zone)
                        # insert the address entry into the group
                        new_group.append(address_find)
                        # insert the new group into the address book
                        self.address_book.append(new_group)

                elif type == 'service':
                    # do the same for service groups.
                    if not self.service_book.has_key(entry):
                        raise "GROUP ADD: no service entry for %s" % (entry)
                    found = None
                    if self.service_book.has_key(name):
                        found = self.service_book[name]
                    if not found:
                        new_grp = NSGroup(name=name, type='service')
                        new_grp.append(self.service_book[entry])
                        self.service_book.append(new_grp)
                    else:
                        found.append(self.service_book[entry])
                else:
                    raise "Unknown group type"

            elif isinstance(node, NSRawPolicy):
                policy_id = node.data.get('id', 0)
                rules     = node.data.get('rules', {})
                isglobal  = node.data.get('global', 0)

                source_zone = node.data.get('src-zone', None)
                dest_zone   = node.data.get('dst-zone', None)
                source_addr = node.data.get('src-address', [])
                dest_addr   = node.data.get('dst-address', [])
                service     = node.data.get('service', [])
                name        = node.data.get('name', None)

                found = None
                subset = False

                if policy_id and not source_zone and not dest_zone:
                    # we have an sub-addition to a policy..
                    subset = True
                    for i in self.policies:
                        if i.id == policy_id:
                            found = i
                            break
                    if not found:
                        raise "Sub policy before policy defined"
                else:
                    # create a new policy
                    found = NSPolicy(id=policy_id, isglobal=isglobal, name=name)

                if source_zone:
                    found.source_zone = source_zone

                if dest_zone:
                    found.destination_zone = dest_zone

                if source_addr:
                    for entry in source_addr:
                        t = self.address_book.find(entry, found.source_zone)
                        if t is None:
                            msg = "No address entry: %s, zone: %s, policy: %s" \
                                  % (entry, found.source_zone, found.id)
                            raise exceptions.NetScreenParseError(msg)

                        if (t.zone and found.source_zone) and t.zone != found.source_zone:
                            raise "%s has a zone of %s, while the source zone" \
                                " of the policy is %s" % (t.name, t.zone, found.source_zone)
                        found['src-address'].append(t)

                if dest_addr:
                    for entry in dest_addr:
                        t = self.address_book.find(entry, found.destination_zone)
                        if t is None:
                            msg = "No address entry: %s, zone: %s, policy: %s" \
                                  % (entry, found.destination_zone, found.id)
                            raise exceptions.NetScreenParseError(msg)

                        if (t.zone and found.destination_zone) and t.zone != found.destination_zone:
                            raise "%s has a zone of %s, while the destination zone" \
                                " of the policy is %s" % (t.name, t.zone, found.destination_zone)

                        found['dst-address'].append(t)

                if service:
                    for entry in service:
                        found['service'].append(self.service_book[entry])

                if subset == False:
                    self.policies.append(found)
            else:
                raise "Unknown node type %s" % str(type(node))

    def output(self):
        ret = []
        for ent in self.address_book.output():
            ret.append(ent)
        for ent in self.service_book.output():
            ret.append(ent)
        for ent in self.policies:
            for line in ent.output():
                ret.append(line)
        return ret

    def output_terms(self):
        ret = []
        for ent in self.policies:
            for term in ent.output_terms():
                ret.append(term)
        return ret

############################
# Policy/Service/Group stuff
############################
class NSRawGroup(object):
    """
    Container for group definitions.
    """
    def __init__(self, data):
        if data[0] == 'address' and len(data) == 3:
            data.append(None)
        if data[0] == 'service' and len(data) == 2:
            data.append(None)

        self.data = data
    def __iter__(self):
        return self.data.__iter__()
    def __len__(self):
        return self.data.__len__()

class NSGroup(NetScreen):
    """
    Container for address/service groups.
    """
    def __init__(self, name=None, group_type='address', zone=None):
        self.nodes = []
        self.name = name
        self.type = group_type
        self.zone = zone

    def append(self, item):
        return getattr(self, 'add_' + self.type)(item)

    def add_address(self, addr):
        assert self.type == 'address'
        if not isinstance(addr, NSAddress):
            raise "add_address requires NSAddress object"
        # make sure the entry hasn't already been added, and
        # that all the zones are in the same zone
        for i in self.nodes:
            if i.zone != addr.zone:
                raise "zone %s did not equal others in group" % addr.zone
            if i.name == addr.name:
                return
        self.nodes.append(addr)

    def add_service(self, svc):
        assert self.type == 'service'
        if not isinstance(svc, NSService):
            raise "add_service requires NSService object"
        for i in self.nodes:
            if i.name == svc.name:
                return
        self.nodes.append(svc)

    def set_name(self, name):
        self.name = name

    def __getitem__(self, key):
        # allow people to find things in groups via a dict style
        for i in self.nodes:
            if i.name == key:
                return i
        raise KeyError

    def __iter__(self):
        return self.nodes.__iter__()

    def output_crap(self):
        ret = ''
        for i in self.nodes:
            ret += i.output_crap()
        return ret

    def get_real(self):
        ret = []
        for i in self.nodes:
            for real in i.get_real():
                ret.append(real)
        return ret

    def output(self):
        ret = []
        for i in self.nodes:
            zone = ''
            if self.zone:
                zone = "\"%s\"" % self.zone
            ret.append('set group %s %s "%s" add "%s"' % (self.type, zone, self.name, i.name))
        return ret

class NSServiceBook(NetScreen):
    """
    Container for built-in service entries and their defaults.

    Example:
        service = NSService(name="stupid_http")
        service.set_source_port((1,65535))
        service.set_destination_port(80)
        service.set_protocol('tcp')
        print service.output()
    """
    def __init__(self, entries=None):
        self.entries = entries or []
        if entries:
            self.entries = entries

        defaults = [
            ('HTTP', 'tcp', (0, 65535), (80, 80)),
            ('HTTPS','tcp', (0, 65535), (443, 443)),
            ('FTP',  'tcp', (0, 65535), (21, 21)),
            ('SSH',  'tcp', (0, 65535), (22, 22)),
            ('SNMP', 'udp', (0, 65535), (161, 162)),
            ('DNS',  'udp', (0, 65535), (53, 53)),
            ('NTP',  'udp', (0, 65535), (123, 123)),
            ('PING', 'icmp', 0, 8),
            ('SYSLOG','udp', (0, 65535), (514, 514)),
            ('MAIL','tcp', (0, 65535), (25, 25)),
            ('SMTP','tcp', (0, 65535), (25, 25)),
            ('LDAP', 'tcp', (0, 65535), (389, 389)),
            ('TFTP', 'udp', (0, 65535), (69, 69)),
            ('TRACEROUTE', 'udp', (0, 65535), (33400, 34000)),
            ('DHCP-Relay', 'udp', (0, 65535), (67, 68)),
            ('ANY',  0, (0,65535), (0, 65535)),
            ('TCP-ANY', 'tcp', (0, 65535), (0, 65535)),
            ('UDP-ANY', 'udp', (0, 65535), (0, 65535)),
            ('ICMP-ANY', 'icmp', (0, 65535), (0, 65535)),
        ]

        for (name,proto,src,dst) in defaults:
            self.entries.append(NSService(name=name, protocol=proto,
                source_port=src, destination_port=dst, predefined=True))

    def has_key(self, key):
        for entry in self.entries:
            if key == entry.name:
                return True
        return False

    def __iter__(self):
        return self.entries.__iter__()

    def __getitem__(self, item):

        for entry in self.entries:
            if item == entry.name:
                return entry

        raise KeyError("%s", item)

    def append(self, item):
        if isinstance(item, NSService):
            return self.entries.append(item)
        if isinstance(item, NSGroup) and item.type == 'service':
            return self.entries.append(item)
        raise "item inserted into NSServiceBook, not an NSService or " \
            "NSGroup.type='service' object"

    def output(self):
        ret = []
        for ent in self.entries:
            for line in ent.output():
                ret.append(line)
        return ret

class NSAddressBook(NetScreen):
    """
    Container for address book entries.
    """
    def __init__(self, name="ANY", zone=None):
        self.entries = {}
        self.any = NSAddress(name="ANY")

    def find(self, address, zone):

        if not self.entries.has_key(zone):
            return None

        for nsaddr in self.entries[zone]:
            if isinstance(address, IPy.IP):
                if nsaddr.addr == address:
                    return nsaddr
            elif isinstance(address, str):
                isany = address.lower()
                if isany == 'any':
                    return self.any
                if nsaddr.name == address:
                    return nsaddr

        return None

    def append(self, item):
        if not isinstance(item, NSAddress) and \
          ((not isinstance(item, NSGroup)) and item.type != 'address'):
            raise "Item inserted int NSAddress not correct type"

        zone = item.zone

        if not self.entries.has_key(item.zone):
            self.entries[item.zone] = [ ]

        return self.entries[item.zone].append(item)

    def name2ips(self, name, zone):
        for entry in self.entries:
            if entry.name == name:
                if isinstance(entry, NSAddress):
                    return [entry.addr]
                if isinstance(entry, NSGroup):
                    ret = []
                    for ent in entry:
                        ret.append(ent.addr)
                    return ret

    def output(self):
        ret = []
        for zone, addrs in self.entries.iteritems():
            for addr in addrs:
                for x in addr.output():
                    ret.append(x)
        return ret

class NSAddress(NetScreen):
    """
    Container for individual address items.
    """
    def __init__(self, name=None, zone=None, addr=None, comment=None):
        self.name = None
        self.zone = None
        self.addr = TIP('0.0.0.0/0')
        self.comment = ''
        if name:
            self.set_name(name)
        if zone:
            self.set_zone(zone)
        if addr:
            self.set_address(addr)
        if comment:
            self.set_comment(comment)

    def set_address(self, addr):
        try:
            a = TIP(addr)
        except Exception, e:
            raise e
        self.addr = a

    def set_zone(self, zone):
        self.zone = zone

    def set_name(self, name):
        self.name = name

    def set_comment(self, comment):
        comment = '"%s"' % comment
        self.comment = comment

    def get_real(self):
        return [self.addr]

    def output_crap(self):
        return "[(Z:%s)%s]" % (self.zone, self.addr.strNormal())

    def output(self):
        tmpl = 'set address "%s" "%s" %s %s %s'
        output = tmpl % (self.zone, self.name, self.addr.strNormal(0),
                          self.addr.netmask(), self.comment)
        return [output]

class NSService(NetScreen):
    """
    Container for individual service items.
    """
    def __init__(self, name=None, protocol=None, source_port=(1,65535),
                 destination_port=(1,65535), timeout=0, predefined=False):
        self.protocol         = protocol
        self.source_port      = source_port
        self.destination_port = destination_port
        self.timeout          = timeout
        self.name             = name
        self.predefined       = predefined
        self.initialize()

    def initialize(self):
        self.set_name(self.name)
        self.set_protocol(self.protocol)
        self.set_source_port(self.source_port)
        self.set_destination_port(self.destination_port)
        self.set_timeout(self.timeout)

    def __cmp__(self, other):
        if not isinstance(other, NSService):
            return -1

        for a,b in {
            self.protocol:other.protocol,
            self.source_port:other.source_port,
            self.destination_port:other.destination_port}.iteritems():

            if a < b:
                return -1
            if a > b:
                return 1

        return 0

    def set_name(self, arg):
        self.name = arg

    def set_source_port(self, ports):
        if isinstance(ports, int):
            check_range([ports], 0, 65535)
            self.source_port = (ports, ports)
        elif isinstance(ports, tuple):
            check_range(ports, 0, 65535)
            self.source_port = ports
        else:
            raise "add_source_port needs int or tuple argument"

    def set_destination_port(self, ports):
        if isinstance(ports, int):
            check_range([ports], 0, 65535)
            self.destination_port = (ports, ports)
        elif isinstance(ports, tuple):
            check_range(ports, 0, 65535)
            self.destination_port = ports
        else:
            raise "add_destination_port needs int or tuple argument"

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_protocol(self, protocol):
        if isinstance(protocol, str) or isinstance(protocol, int):
            self.protocol = Protocol(protocol)
        if isinstance(protocol, Protocol):
            self.protocol = protocol

    def output_crap(self):
        return "[Service: %s (%d-%d):(%d-%d)]" % (self.protocol,
            self.source_port[0], self.source_port[1],
            self.destination_port[0], self.destination_port[1])

    def get_real(self):
        return [(self.source_port, self.destination_port, self.protocol)]

    def output(self):
        if self.predefined:
            return []
        ret = 'set service "%s" protocol %s src-port %d-%d ' \
              'dst-port %d-%d' % (self.name, self.protocol,
                self.source_port[0], self.source_port[1],
                self.destination_port[0], self.destination_port[1])
        if self.timeout:
            ret += ' timeout %d' % (self.timeout)
        return [ret]

class NSRawPolicy(object):
    """
    Container for policy definitions.
    """
    def __init__(self, data, isglobal=0):
        self.isglobal = isglobal
        self.data = {}

        for entry in data:
            for key,val in entry.iteritems():
                self.data[key] = val

class NSPolicy(NetScreen):
    """
    Container for individual policy definitions.
    """
    def __init__(self, name=None, address_book=NSAddressBook(),
                 service_book=NSServiceBook(), address_groups=None,
                 service_groups=None, source_zone="Untrust",
                 destination_zone="Trust", id=0, action='permit',
                 isglobal=False):
        self.service_book     = service_book
        self.address_book     = address_book
        self.service_groups   = service_groups or []
        self.address_groups   = address_groups or []
        self.source_zone      = source_zone
        self.destination_zone = destination_zone
        self.source_addresses      = []
        self.destination_addresses = []
        self.services              = []
        self.action                = action

        self.id   = id
        self.name = name
        self.isglobal = isglobal

    def add_address(self, address, zone, address_book, addresses):
        addr = TIP(address)
        found = address_book.find(addr, zone)
        if not found:
            if addr.prefixlen() == 32:
                name = 'h%s' % (addr.strNormal(0))
            else:
                name = 'n%s' % (addr.strNormal())

            found = NSAddress(name=name, zone=zone, addr=addr.strNormal())

            address_book.append(found)
        addresses.append(found)

    def add_source_address(self, address):
        self.add_address(address, self.source_zone,
            self.address_book, self.source_addresses)

    def add_destination_address(self, address):
        self.add_address(address, self.destination_zone,
            self.address_book, self.destination_addresses)

    def add_service(self, protocol, source_port=(1, 65535), destination_port=(1, 65535)):
        found = None
        if not protocol:
            raise "no protocol defined in add_service"

        if isinstance(destination_port, tuple):
            sname = "%s%d-%d" % (protocol, destination_port[0],
                destination_port[1])
        else:
            sname = "%s%d" % (protocol, destination_port)

        test_service = NSService(name=sname, source_port=source_port,
                                 destination_port=destination_port,
                                 protocol=protocol)

        for svc in self.service_book:
            if svc == test_service:
                found = svc
                break

        if not found:
            self.service_book.append(test_service)
            found = test_service
        self.services.append(found)

    def __getitem__(self, key):
        if key == 'dst-address':
            return self.destination_addresses
        if key == 'src-address':
            return self.source_addresses
        if key == 'service':
            return self.services
        raise KeyError

    def output_crap(self):
        out = []
        for service in self.services:
            for src in self.source_addresses:
                for dst in self.destination_addresses:
                    print src.output_crap(),"->",dst.output_crap(),":",service.output_crap()

    def output_human(self):
        source_addrs = []
        dest_addrs   = []
        dest_serv    = []
        serv_hash    = {}

        for i in self.source_addresses:
            for addr in i.get_real():
                source_addrs.append(addr)

        for i in self.destination_addresses:
            for addr in i.get_real():
                dest_addrs.append(addr)

        for i in self.services:
            for serv in i.get_real():
                #(1, 65535), (80, 80), <Protocol: tcp>
                (s,d,p) = serv

                if not serv_hash.has_key(p):
                    serv_hash[p] = {s:[d]}

                else:
                    if not serv_hash[p].has_key(s):
                        serv_hash[p][s] = [d]
                    else:
                        serv_hash[p][s].append(d)

                dest_serv.append(serv)

        for protocol in serv_hash:
            print "protocol %s" % protocol
            for source_ports in serv_hash[protocol]:
                print " source ports", source_ports
                dest_ports = serv_hash[protocol][source_ports]
                #for dest_ports in serv_hash[protocol][source_ports]:
                print "  dest ports", dest_ports
                term = create_trigger_term(
                        source_ips   = source_addrs,
                        dest_ips     = dest_addrs,
                        source_ports = [source_ports],
                        dest_ports   = dest_ports,
                        protocols    = [protocol])
                for line in term.output(format='junos'):
                    print line


        print "SOURCES",source_addrs
        print "DESTINATIONS",dest_addrs
        print "SERVICES", serv_hash

    def output_terms(self):
        source_addrs = []
        dest_addrs   = []
        dest_serv    = []
        terms        = []
        serv_hash    = {}

        for i in self.source_addresses:
            for addr in i.get_real():
                source_addrs.append(addr)

        for i in self.destination_addresses:
            for addr in i.get_real():
                dest_addrs.append(addr)

        for i in self.services:
            for serv in i.get_real():
                (s,d,p) = serv
                if not serv_hash.has_key(p):
                    serv_hash[p] = {s:[d]}
                else:
                    if not serv_hash[p].has_key(s):
                        serv_hash[p] = {s:[d]}
                    else:
                        serv_hash[p][s].append(d)

                dest_serv.append(serv)

        for protocol in serv_hash:
            for source_ports in serv_hash[protocol]:
                dest_ports = serv_hash[protocol][source_ports]
                term = create_trigger_term(
                        source_ips   = source_addrs,
                        dest_ips     = dest_addrs,
                        source_ports = [source_ports],
                        dest_ports   = dest_ports,
                        protocols    = [protocol])
                terms.append(term)
        return terms

    def output(self):
        toret = []
        num_saddrs   = len(self.source_addresses)
        num_daddrs   = len(self.destination_addresses)
        num_services = len(self.services)
        ret = 'set policy '
        if self.isglobal:
            ret += 'global '
        if self.id:
            ret += 'id %d ' % (self.id)
        if self.name:
            ret += 'name "%s" ' % (self.name)
        ret += 'from "%s" to "%s" ' % (self.source_zone, self.destination_zone)
        for setter in [self.source_addresses,
                       self.destination_addresses,
                       self.services]:
            if not len(setter):
                ret += '"ANY" '
            else:
                ret += '"%s" ' % (setter[0].name)
        ret += '%s' % self.action
        toret.append(ret)

        if num_saddrs > 1 or num_daddrs > 1 or num_services > 1:
            toret.append("set policy id %d" % (self.id))
            for k,v in {'src-address':self.source_addresses[1:],
                        'dst-address':self.destination_addresses[1:],
                        'service':self.services[1:]}.iteritems():
                for item in v:
                    toret.append(' set %s "%s"' % (k, item.name))
            toret.append('exit')
        return toret

########NEW FILE########
__FILENAME__ = peewee
"""
peewee - a small, expressive ORM
Source: https://raw.github.com/coleifer/peewee/2.1.4/peewee.py
License: BSD
Integrated into Trigger 2013-09-12
"""
#     (\
#     (  \  /(o)\     caw!
#     (   \/  ()/ /)
#      (   `;.))'".)
#       `(/////.-'
#    =====))=))===()
#      ///'
#     //
#    '
from __future__ import with_statement
import datetime
import decimal
import logging
import operator
import re
import sys
import threading
from collections import deque
from collections import namedtuple
from copy import deepcopy
from inspect import isclass

__all__ = [
    'BigIntegerField',
    'BlobField',
    'BooleanField',
    'CharField',
    'Clause',
    'CompositeKey',
    'DateField',
    'DateTimeField',
    'DecimalField',
    'DoesNotExist',
    'DoubleField',
    'DQ',
    'Entity',
    'Field',
    'FloatField',
    'fn',
    'ForeignKeyField',
    'ImproperlyConfigured',
    'IntegerField',
    'JOIN_FULL',
    'JOIN_INNER',
    'JOIN_LEFT_OUTER',
    'Model',
    'MySQLDatabase',
    'PostgresqlDatabase',
    'prefetch',
    'PrimaryKeyField',
    'R',
    'SqliteDatabase',
    'TextField',
    'TimeField',
]

# Python 2/3 compat
def with_metaclass(meta, base=object):
    return meta("NewBase", (base,), {})

PY3 = sys.version_info[0] == 3
if PY3:
    import builtins
    from collections import Callable
    from functools import reduce
    callable = lambda c: isinstance(c, Callable)
    unicode_type = str
    string_type = bytes
    basestring = str
    print_ = getattr(builtins, 'print')
    binary_construct = lambda s: bytes(s.encode('raw_unicode_escape'))
else:
    unicode_type = unicode
    string_type = basestring
    binary_construct = buffer
    def print_(s):
        sys.stdout.write(s)
        sys.stdout.write('\n')

# DB libraries
try:
    import sqlite3
except ImportError:
    sqlite3 = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import MySQLdb as mysql
except ImportError:
    try:
        import pymysql as mysql
    except ImportError:
        mysql = None

class ImproperlyConfigured(Exception): pass

if sqlite3 is None and psycopg2 is None and mysql is None:
    raise ImproperlyConfigured('Either sqlite3, psycopg2 or MySQLdb must be '
                               'installed')

if sqlite3:
    sqlite3.register_adapter(decimal.Decimal, str)
    sqlite3.register_adapter(datetime.date, str)
    sqlite3.register_adapter(datetime.time, str)

SQLITE_DT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d',
    '%H:%M:%S',
    '%H:%M:%S.%f',
    '%H:%M')
DT_PARTS = ['year', 'month', 'day', 'hour', 'minute', 'second']
DT_LOOKUPS = set(DT_PARTS)

def _sqlite_date_part(lookup_type, datetime_string):
    assert lookup_type in DT_LOOKUPS
    dt = format_date_time(datetime_string, SQLITE_DT_FORMATS)
    return getattr(dt, lookup_type)

if psycopg2:
    import psycopg2.extensions
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Peewee
logger = logging.getLogger('peewee')

OP_AND = 'and'
OP_OR = 'or'

OP_ADD = '+'
OP_SUB = '-'
OP_MUL = '*'
OP_DIV = '/'
OP_BIN_AND = '&'
OP_BIN_OR = '|'
OP_XOR = '^'
OP_MOD = '%'

OP_EQ = '='
OP_LT = '<'
OP_LTE = '<='
OP_GT = '>'
OP_GTE = '>='
OP_NE = '!='
OP_IN = 'in'
OP_IS = 'is'
OP_LIKE = 'like'
OP_ILIKE = 'ilike'
OP_BETWEEN = 'between'

DJANGO_MAP = {
    'eq': OP_EQ,
    'lt': OP_LT,
    'lte': OP_LTE,
    'gt': OP_GT,
    'gte': OP_GTE,
    'ne': OP_NE,
    'in': OP_IN,
    'is': OP_IS,
    'like': OP_LIKE,
    'ilike': OP_ILIKE,
}

JOIN_INNER = 'inner'
JOIN_LEFT_OUTER = 'left outer'
JOIN_FULL = 'full'

def dict_update(orig, extra):
    new = {}
    new.update(orig)
    new.update(extra)
    return new

def returns_clone(func):
    def inner(self, *args, **kwargs):
        clone = self.clone()
        func(clone, *args, **kwargs)
        return clone
    inner.call_local = func
    return inner

def not_allowed(fn):
    def inner(self, *args, **kwargs):
        raise NotImplementedError('%s is not allowed on %s instances' % (
            fn, type(self).__name__))
    return inner


class Node(object):
    def __init__(self):
        self._negated = False
        self._alias = None
        self._ordering = None

    def clone_base(self):
        return type(self)()

    def clone(self):
        inst = self.clone_base()
        inst._negated = self._negated
        inst._alias = self._alias
        return inst

    @returns_clone
    def __invert__(self):
        self._negated = not self._negated

    @returns_clone
    def alias(self, a=None):
        self._alias = a

    @returns_clone
    def asc(self):
        self._ordering = 'ASC'

    @returns_clone
    def desc(self):
        self._ordering = 'DESC'

    def _e(op, inv=False):
        def inner(self, rhs):
            if inv:
                return Expression(rhs, op, self)
            return Expression(self, op, rhs)
        return inner
    __and__ = _e(OP_AND)
    __or__ = _e(OP_OR)

    __add__ = _e(OP_ADD)
    __sub__ = _e(OP_SUB)
    __mul__ = _e(OP_MUL)
    __div__ = _e(OP_DIV)
    __xor__ = _e(OP_XOR)
    __radd__ = _e(OP_ADD, inv=True)
    __rsub__ = _e(OP_SUB, inv=True)
    __rmul__ = _e(OP_MUL, inv=True)
    __rdiv__ = _e(OP_DIV, inv=True)
    __rand__ = _e(OP_AND, inv=True)
    __ror__ = _e(OP_OR, inv=True)
    __rxor__ = _e(OP_XOR, inv=True)

    __eq__ = _e(OP_EQ)
    __lt__ = _e(OP_LT)
    __le__ = _e(OP_LTE)
    __gt__ = _e(OP_GT)
    __ge__ = _e(OP_GTE)
    __ne__ = _e(OP_NE)
    __lshift__ = _e(OP_IN)
    __rshift__ = _e(OP_IS)
    __mod__ = _e(OP_LIKE)
    __pow__ = _e(OP_ILIKE)

    bin_and = _e(OP_BIN_AND)
    bin_or = _e(OP_BIN_OR)

    def between(self, low, high):
        return Expression(self, OP_BETWEEN, Clause(low, R('AND'), high))

class Expression(Node):
    def __init__(self, lhs, op, rhs):
        super(Expression, self).__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def clone_base(self):
        return Expression(self.lhs, self.op, self.rhs)

class DQ(Node):
    def __init__(self, **query):
        super(DQ, self).__init__()
        self.query = query

    def clone_base(self):
        return DQ(**self.query)

class Param(Node):
    def __init__(self, value):
        self.value = value
        super(Param, self).__init__()

    def clone_base(self):
        return Param(self.value)

class R(Node):
    def __init__(self, value):
        self.value = value
        super(R, self).__init__()

    def clone_base(self):
        return R(self.value)

class Func(Node):
    def __init__(self, name, *nodes):
        self.name = name
        self.nodes = nodes
        super(Func, self).__init__()

    def clone_base(self):
        return Func(self.name, *self.nodes)

    def __getattr__(self, attr):
        def dec(*args, **kwargs):
            return Func(attr, *args, **kwargs)
        return dec

fn = Func(None)

class Clause(Node):
    def __init__(self, *nodes):
        super(Clause, self).__init__()
        self.nodes = nodes

    def clone_base(self):
        return Clause(*self.nodes)

class Entity(Node):
    def __init__(self, *path):
        super(Entity, self).__init__()
        self.path = path

    def clone_base(self):
        return Entity(*self.path)

    def __getattr__(self, attr):
        return Entity(*self.path + (attr,))

Join = namedtuple('Join', ('model_class', 'join_type', 'on'))

class FieldDescriptor(object):
    def __init__(self, field):
        self.field = field
        self.att_name = self.field.name

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance._data.get(self.att_name)
        return self.field

    def __set__(self, instance, value):
        instance._data[self.att_name] = value

class Field(Node):
    _field_counter = 0
    _order = 0
    db_field = 'unknown'
    template = '%(column_type)s'
    template_extra = ''

    def __init__(self, null=False, index=False, unique=False,
                 verbose_name=None, help_text=None, db_column=None,
                 default=None, choices=None, primary_key=False, sequence=None,
                 *args, **kwargs):
        self.null = null
        self.index = index
        self.unique = unique
        self.verbose_name = verbose_name
        self.help_text = help_text
        self.db_column = db_column
        self.default = default
        self.choices = choices
        self.primary_key = primary_key
        self.sequence = sequence

        self.attributes = self.field_attributes()
        self.attributes.update(kwargs)

        Field._field_counter += 1
        self._order = Field._field_counter

        self._is_bound = False
        super(Field, self).__init__()

    def clone_base(self, **kwargs):
       inst = type(self)(
           null=self.null,
           index=self.index,
           unique=self.unique,
           verbose_name=self.verbose_name,
           help_text=self.help_text,
           db_column=self.db_column,
           default=self.default,
           choices=self.choices,
           primary_key=self.primary_key,
           sequence=self.sequence,
           **kwargs
       )
       inst.attributes = dict(self.attributes)
       if self._is_bound:
           inst.name = self.name
           inst.model_class = self.model_class
       return inst

    def add_to_class(self, model_class, name):
        self.name = name
        self.model_class = model_class
        self.db_column = self.db_column or self.name
        if not self.verbose_name:
            self.verbose_name = re.sub('_+', ' ', name).title()

        model_class._meta.fields[self.name] = self
        model_class._meta.columns[self.db_column] = self

        setattr(model_class, name, FieldDescriptor(self))
        self._is_bound = True

    def get_database(self):
        return self.model_class._meta.database

    def field_attributes(self):
        return {}

    def get_db_field(self):
        return self.db_field

    def get_template(self):
        return self.template

    def coerce(self, value):
        return value

    def db_value(self, value):
        return value if value is None else self.coerce(value)

    def python_value(self, value):
        return value if value is None else self.coerce(value)

    def __hash__(self):
        return hash(self.name + '.' + self.model_class.__name__)

class IntegerField(Field):
    db_field = 'int'
    coerce = int

class BigIntegerField(IntegerField):
    db_field = 'bigint'

class PrimaryKeyField(IntegerField):
    db_field = 'primary_key'

    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        super(PrimaryKeyField, self).__init__(*args, **kwargs)

class FloatField(Field):
    db_field = 'float'
    coerce = float

class DoubleField(FloatField):
    db_field = 'double'

class DecimalField(Field):
    db_field = 'decimal'
    template = '%(column_type)s(%(max_digits)d, %(decimal_places)d)'

    def field_attributes(self):
        return {
            'max_digits': 10,
            'decimal_places': 5,
            'auto_round': False,
            'rounding': decimal.DefaultContext.rounding,
        }

    def db_value(self, value):
        D = decimal.Decimal
        if not value:
            return value if value is None else D(0)
        if self.attributes['auto_round']:
            exp = D(10) ** (-self.attributes['decimal_places'])
            rounding = self.attributes['rounding']
            return D(str(value)).quantize(exp, rounding=rounding)
        return value

    def python_value(self, value):
        if value is not None:
            if isinstance(value, decimal.Decimal):
                return value
            return decimal.Decimal(str(value))

def format_unicode(s, encoding='utf-8'):
    if isinstance(s, unicode_type):
        return s
    elif isinstance(s, string_type):
        return s.decode(encoding)
    return unicode_type(s)

class CharField(Field):
    db_field = 'string'
    template = '%(column_type)s(%(max_length)s)'

    def field_attributes(self):
        return {'max_length': 255}

    def coerce(self, value):
        return format_unicode(value or '')

class TextField(Field):
    db_field = 'text'

    def coerce(self, value):
        return format_unicode(value or '')

class BlobField(Field):
    db_field = 'blob'

    def db_value(self, value):
        if isinstance(value, basestring):
            return binary_construct(value)
        return value

def format_date_time(value, formats, post_process=None):
    post_process = post_process or (lambda x: x)
    for fmt in formats:
        try:
            return post_process(datetime.datetime.strptime(value, fmt))
        except ValueError:
            pass
    return value

def _date_part(date_part):
    def dec(self):
        return self.model_class._meta.database.extract_date(date_part, self)
    return dec

class DateTimeField(Field):
    db_field = 'datetime'

    def field_attributes(self):
        return {
            'formats': [
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
            ]
        }

    def python_value(self, value):
        if value and isinstance(value, basestring):
            return format_date_time(value, self.attributes['formats'])
        return value

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))
    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))

class DateField(Field):
    db_field = 'date'

    def field_attributes(self):
        return {
            'formats': [
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
            ]
        }

    def python_value(self, value):
        if value and isinstance(value, basestring):
            pp = lambda x: x.date()
            return format_date_time(value, self.attributes['formats'], pp)
        elif value and isinstance(value, datetime.datetime):
            return value.date()
        return value

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))

class TimeField(Field):
    db_field = 'time'

    def field_attributes(self):
        return {
            'formats': [
                '%H:%M:%S.%f',
                '%H:%M:%S',
                '%H:%M',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
            ]
        }

    def python_value(self, value):
        if value and isinstance(value, basestring):
            pp = lambda x: x.time()
            return format_date_time(value, self.attributes['formats'], pp)
        elif value and isinstance(value, datetime.datetime):
            return value.time()
        return value

    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))

class BooleanField(Field):
    db_field = 'bool'
    coerce = bool

class RelationDescriptor(FieldDescriptor):
    def __init__(self, field, rel_model):
        self.rel_model = rel_model
        super(RelationDescriptor, self).__init__(field)

    def get_object_or_id(self, instance):
        rel_id = instance._data.get(self.att_name)
        if rel_id is not None or self.att_name in instance._obj_cache:
            if self.att_name not in instance._obj_cache:
                obj = self.rel_model.get(
                    self.rel_model._meta.primary_key == rel_id)
                instance._obj_cache[self.att_name] = obj
            return instance._obj_cache[self.att_name]
        elif not self.field.null:
            raise self.rel_model.DoesNotExist
        return rel_id

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.get_object_or_id(instance)
        return self.field

    def __set__(self, instance, value):
        if isinstance(value, self.rel_model):
            instance._data[self.att_name] = value.get_id()
            instance._obj_cache[self.att_name] = value
        else:
            instance._data[self.att_name] = value

class ReverseRelationDescriptor(object):
    def __init__(self, field):
        self.field = field
        self.rel_model = field.model_class

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.rel_model.select().where(self.field==instance.get_id())
        return self

class ForeignKeyField(IntegerField):
    def __init__(self, rel_model, null=False, related_name=None, cascade=False,
                 extra=None, *args, **kwargs):
        self.rel_model = rel_model
        self._related_name = related_name
        self.cascade = cascade
        self.extra = extra

        kwargs.update(dict(
            cascade='ON DELETE CASCADE' if self.cascade else '',
            extra=extra or ''))

        super(ForeignKeyField, self).__init__(null=null, *args, **kwargs)

    def clone_base(self):
         return super(ForeignKeyField, self).clone_base(
            rel_model=self.rel_model,
            related_name=self.related_name,
            cascade=self.cascade,
            extra=self.extra)

    def add_to_class(self, model_class, name):
        self.name = name
        self.model_class = model_class
        self.db_column = self.db_column or '%s_id' % self.name
        if not self.verbose_name:
            self.verbose_name = re.sub('_+', ' ', name).title()

        model_class._meta.fields[self.name] = self
        model_class._meta.columns[self.db_column] = self

        model_name = model_class._meta.name
        self.related_name = self._related_name or '%s_set' % (model_name)

        if self.rel_model == 'self':
            self.rel_model = self.model_class
        if self.related_name in self.rel_model._meta.fields:
            error = ('Foreign key: %s.%s related name "%s" collision with '
                     'field of the same name.')
            params = self.model_class._meta.name, self.name, self.related_name
            raise AttributeError(error % params)
        if self.related_name in self.rel_model._meta.reverse_rel:
            error = ('Foreign key: %s.%s related name "%s" collision with '
                     'foreign key using same related_name.')
            params = self.model_class._meta.name, self.name, self.related_name
            raise AttributeError(error % params)

        fk_descriptor = RelationDescriptor(self, self.rel_model)
        backref_descriptor = ReverseRelationDescriptor(self)
        setattr(model_class, name, fk_descriptor)
        setattr(self.rel_model, self.related_name, backref_descriptor)
        self._is_bound = True

        model_class._meta.rel[self.name] = self
        self.rel_model._meta.reverse_rel[self.related_name] = self

    def get_db_field(self):
        to_pk = self.rel_model._meta.primary_key
        if not isinstance(to_pk, PrimaryKeyField):
            return to_pk.get_db_field()
        return super(ForeignKeyField, self).get_db_field()

    def coerce(self, value):
        return self.rel_model._meta.primary_key.coerce(value)

    def db_value(self, value):
        if isinstance(value, self.rel_model):
            value = value.get_id()
        return self.rel_model._meta.primary_key.db_value(value)


class CompositeKey(object):
    sequence = None

    def __init__(self, *fields):
        self.fields = fields

    def add_to_class(self, model_class, name):
        self.name = name
        setattr(model_class, name, self)

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return [getattr(instance, field) for field in self.fields]
        return self

    def __set__(self, instance, value):
        pass


class QueryCompiler(object):
    field_map = {
        'bigint': 'BIGINT',
        'blob': 'BLOB',
        'bool': 'SMALLINT',
        'date': 'DATE',
        'datetime': 'DATETIME',
        'decimal': 'DECIMAL',
        'double': 'REAL',
        'float': 'REAL',
        'int': 'INTEGER',
        'primary_key': 'INTEGER',
        'string': 'VARCHAR',
        'text': 'TEXT',
        'time': 'TIME',
    }

    op_map = {
        OP_EQ: '=',
        OP_LT: '<',
        OP_LTE: '<=',
        OP_GT: '>',
        OP_GTE: '>=',
        OP_NE: '!=',
        OP_IN: 'IN',
        OP_IS: 'IS',
        OP_BIN_AND: '&',
        OP_BIN_OR: '|',
        OP_LIKE: 'LIKE',
        OP_ILIKE: 'ILIKE',
        OP_BETWEEN: 'BETWEEN',
        OP_ADD: '+',
        OP_SUB: '-',
        OP_MUL: '*',
        OP_DIV: '/',
        OP_XOR: '#',
        OP_AND: 'AND',
        OP_OR: 'OR',
        OP_MOD: '%',
    }

    join_map = {
        JOIN_INNER: 'INNER',
        JOIN_LEFT_OUTER: 'LEFT OUTER',
        JOIN_FULL: 'FULL',
    }

    def __init__(self, quote_char='"', interpolation='?', field_overrides=None,
                 op_overrides=None):
        self.quote_char = quote_char
        self.interpolation = interpolation
        self._field_map = dict_update(self.field_map, field_overrides or {})
        self._op_map = dict_update(self.op_map, op_overrides or {})

    def quote(self, s):
        return s.join((self.quote_char, self.quote_char))

    def get_field(self, f):
        return self._field_map[f]

    def get_op(self, q):
        return self._op_map[q]

    def _max_alias(self, am):
        max_alias = 0
        if am:
            for a in am.values():
                i = int(a.lstrip('t'))
                if i > max_alias:
                    max_alias = i
        return max_alias + 1

    def _parse(self, node, alias_map, conv):
        # By default treat the incoming node as a raw value that should be
        # parameterized.
        sql = self.interpolation
        params = [node]
        unknown = False
        if isinstance(node, Expression):
            if isinstance(node.lhs, Field):
                conv = node.lhs
            lhs, lparams = self.parse_node(node.lhs, alias_map, conv)
            rhs, rparams = self.parse_node(node.rhs, alias_map, conv)
            sql = '(%s %s %s)' % (lhs, self.get_op(node.op), rhs)
            params = lparams + rparams
        elif isinstance(node, Field):
            sql = self.quote(node.db_column)
            if alias_map and node.model_class in alias_map:
                sql = '.'.join((alias_map[node.model_class], sql))
            params = []
        elif isinstance(node, Func):
            sql, params = self.parse_node_list(node.nodes, alias_map, conv)
            sql = '%s(%s)' % (node.name, sql)
        elif isinstance(node, Clause):
            sql, params = self.parse_node_list(
                node.nodes, alias_map, conv, ' ')
        elif isinstance(node, Param):
            params = [node.value]
        elif isinstance(node, R):
            sql = node.value
            params = []
        elif isinstance(node, SelectQuery):
            max_alias = self._max_alias(alias_map)
            alias_copy = alias_map and alias_map.copy() or None
            clone = node.clone()
            if not node._explicit_selection:
                clone._select = (clone.model_class._meta.primary_key,)
            sub, params = self.generate_select(clone, max_alias, alias_copy)
            sql = '(%s)' % sub
        elif isinstance(node, (list, tuple)):
            sql, params = self.parse_node_list(node, alias_map, conv)
            sql = '(%s)' % sql
        elif isinstance(node, Model):
            sql = self.interpolation
            params = [node.get_id()]
        elif isinstance(node, Entity):
            sql = '.'.join(map(self.quote, node.path))
            params = []
        elif isclass(node) and issubclass(node, Model):
            sql = self.quote(node._meta.db_table)
            params = []
        else:
            unknown = True
        return sql, params, unknown

    def parse_node(self, node, alias_map=None, conv=None):
        sql, params, unknown = self._parse(node, alias_map, conv)
        if unknown and conv and params:
            params = [conv.db_value(i) for i in params]

        if isinstance(node, Node):
            if node._negated:
                sql = 'NOT %s' % sql
            if node._alias:
                sql = ' '.join((sql, 'AS', node._alias))
            if node._ordering:
                sql = ' '.join((sql, node._ordering))
        return sql, params

    def parse_node_list(self, nodes, alias_map, conv=None, glue=', '):
        sql = []
        params = []
        for node in nodes:
            node_sql, node_params = self.parse_node(node, alias_map, conv)
            sql.append(node_sql)
            params.extend(node_params)
        return glue.join(sql), params

    def parse_field_dict(self, d):
        sets, params = [], []
        for field, value in d.items():
            field_sql, _ = self.parse_node(field)
            # because we don't know whether to call db_value or parse_node
            # first, we'd prefer to call parse_node since its more general, but
            # it does special things with lists -- it treats them as if it were
            # buliding up an IN query. for some things we don't want that, so
            # here, if the node is *not* a special object, we'll pass thru
            # parse_node and let db_value handle it
            if not isinstance(value, (Node, Model, Query)):
                value = Param(value)  # passthru to the field's db_value func
            val_sql, val_params = self.parse_node(value)
            val_params = [field.db_value(vp) for vp in val_params]
            sets.append((field_sql, val_sql))
            params.extend(val_params)
        return sets, params

    def parse_query_node(self, node, alias_map):
        if node is not None:
            return self.parse_node(node, alias_map)
        return '', []

    def calculate_alias_map(self, query, start=1):
        alias_map = {query.model_class: 't%s' % start}
        for model, joins in query._joins.items():
            if model not in alias_map:
                start += 1
                alias_map[model] = 't%s' % start
            for join in joins:
                if join.model_class not in alias_map:
                    start += 1
                    alias_map[join.model_class] = 't%s' % start
        return alias_map

    def generate_joins(self, joins, model_class, alias_map):
        sql = []
        params = []
        seen = set()
        q = [model_class]
        while q:
            curr = q.pop()
            if curr not in joins or curr in seen:
                continue
            seen.add(curr)
            for join in joins[curr]:
                src = curr
                dest = join.model_class
                if isinstance(join.on, Expression):
                    # Clear any alias on the join expression.
                    join_node = join.on.clone().alias()
                else:
                    field = src._meta.rel_for_model(dest, join.on)
                    if field:
                        left_field = field
                        right_field = dest._meta.primary_key
                    else:
                        field = dest._meta.rel_for_model(src, join.on)
                        left_field = src._meta.primary_key
                        right_field = field
                    join_node = (left_field == right_field)

                join_type = join.join_type or JOIN_INNER
                join_sql, join_params = self.parse_node(join_node, alias_map)

                sql.append('%s JOIN %s AS %s ON %s' % (
                    self.join_map[join_type],
                    self.quote(dest._meta.db_table),
                    alias_map[dest],
                    join_sql))
                params.extend(join_params)

                q.append(dest)
        return sql, params

    def generate_select(self, query, start=1, alias_map=None):
        model = query.model_class
        db = model._meta.database

        alias_map = alias_map or {}
        alias_map.update(self.calculate_alias_map(query, start))

        parts = ['SELECT']
        params = []

        if query._distinct:
            parts.append('DISTINCT')

        select, s_params = self.parse_node_list(query._select, alias_map)
        parts.append(select)
        params.extend(s_params)

        parts.append('FROM %s AS %s' % (
            self.quote(model._meta.db_table),
            alias_map[model]))

        joins, j_params = self.generate_joins(query._joins, model, alias_map)
        if joins:
            parts.append(' '.join(joins))
            params.extend(j_params)

        where, w_params = self.parse_query_node(query._where, alias_map)
        if where:
            parts.append('WHERE %s' % where)
            params.extend(w_params)

        if query._group_by:
            group, g_params = self.parse_node_list(query._group_by, alias_map)
            parts.append('GROUP BY %s' % group)
            params.extend(g_params)

        if query._having:
            having, h_params = self.parse_query_node(query._having, alias_map)
            parts.append('HAVING %s' % having)
            params.extend(h_params)

        if query._order_by:
            order, o_params = self.parse_node_list(query._order_by, alias_map)
            parts.append('ORDER BY %s' % order)
            params.extend(o_params)

        if query._limit or (query._offset and db.limit_max):
            limit = query._limit or db.limit_max
            parts.append('LIMIT %s' % limit)
        if query._offset:
            parts.append('OFFSET %s' % query._offset)
        if query._for_update:
            parts.append('FOR UPDATE')

        return ' '.join(parts), params

    def generate_update(self, query):
        model = query.model_class

        parts = ['UPDATE %s SET' % self.quote(model._meta.db_table)]
        sets, params = self.parse_field_dict(query._update)

        parts.append(', '.join('%s=%s' % (f, v) for f, v in sets))

        where, w_params = self.parse_query_node(query._where, None)
        if where:
            parts.append('WHERE %s' % where)
            params.extend(w_params)
        return ' '.join(parts), params

    def generate_insert(self, query):
        model = query.model_class

        parts = ['INSERT INTO %s' % self.quote(model._meta.db_table)]
        sets, params = self.parse_field_dict(query._insert)

        if sets:
            parts.append('(%s)' % ', '.join(s[0] for s in sets))
            parts.append('VALUES (%s)' % ', '.join(s[1] for s in sets))

        return ' '.join(parts), params

    def generate_delete(self, query):
        model = query.model_class

        parts = ['DELETE FROM %s' % self.quote(model._meta.db_table)]
        params = []

        where, w_params = self.parse_query_node(query._where, None)
        if where:
            parts.append('WHERE %s' % where)
            params.extend(w_params)

        return ' '.join(parts), params

    def field_sql(self, field):
        attrs = field.attributes
        attrs['column_type'] = self.get_field(field.get_db_field())
        template = field.get_template()

        if isinstance(field, ForeignKeyField):
            to_pk = field.rel_model._meta.primary_key
            if not isinstance(to_pk, PrimaryKeyField):
                template = to_pk.get_template()
                attrs.update(to_pk.attributes)

        parts = [self.quote(field.db_column), template]
        if not field.null:
            parts.append('NOT NULL')
        if field.primary_key:
            parts.append('PRIMARY KEY')
        if field.template_extra:
            parts.append(field.template_extra)
        if isinstance(field, ForeignKeyField):
            ref_mc = (
                self.quote(field.rel_model._meta.db_table),
                self.quote(field.rel_model._meta.primary_key.db_column))
            parts.append('REFERENCES %s (%s)' % ref_mc)
            parts.append('%(cascade)s%(extra)s')
        elif field.sequence:
            parts.append("DEFAULT NEXTVAL('%s')" % self.quote(field.sequence))
        return ' '.join(p % attrs for p in parts)

    def create_table_sql(self, model_class, safe=False):
        parts = ['CREATE TABLE']
        if safe:
            parts.append('IF NOT EXISTS')
        meta = model_class._meta
        parts.append(self.quote(meta.db_table))
        columns = map(self.field_sql, meta.get_fields())
        if isinstance(meta.primary_key, CompositeKey):
            pk_cols = map(self.quote, (
                meta.fields[f].db_column for f in meta.primary_key.fields))
            columns.append('PRIMARY KEY (%s)' % ', '.join(pk_cols))
        parts.append('(%s)' % ', '.join(columns))
        return parts

    def create_table(self, model_class, safe=False):
        return ' '.join(self.create_table_sql(model_class, safe))

    def drop_table(self, model_class, fail_silently=False, cascade=False):
        parts = ['DROP TABLE']
        if fail_silently:
            parts.append('IF EXISTS')
        parts.append(self.quote(model_class._meta.db_table))
        if cascade:
            parts.append('CASCADE')
        return ' '.join(parts)

    def create_index_sql(self, model_class, fields, unique):
        tbl_name = model_class._meta.db_table
        colnames = [f.db_column for f in fields]
        parts = ['CREATE %s' % ('UNIQUE INDEX' if unique else 'INDEX')]
        parts.append(self.quote('%s_%s' % (tbl_name, '_'.join(colnames))))
        parts.append('ON %s' % self.quote(tbl_name))
        parts.append('(%s)' % ', '.join(map(self.quote, colnames)))
        return parts

    def create_index(self, model_class, fields, unique):
        return ' '.join(self.create_index_sql(model_class, fields, unique))

    def create_sequence(self, sequence_name):
        return 'CREATE SEQUENCE %s;' % self.quote(sequence_name)

    def drop_sequence(self, sequence_name):
        return 'DROP SEQUENCE %s;' % self.quote(sequence_name)


class QueryResultWrapper(object):
    """
    Provides an iterator over the results of a raw Query, additionally doing
    two things:
    - converts rows from the database into python representations
    - ensures that multiple iterations do not result in multiple queries
    """
    def __init__(self, model, cursor, meta=None):
        self.model = model
        self.cursor = cursor

        self.__ct = 0
        self.__idx = 0

        self._result_cache = []
        self._populated = False
        self._initialized = False

        if meta is not None:
            self.column_meta, self.join_meta = meta
        else:
            self.column_meta = self.join_meta = None

    def __iter__(self):
        self.__idx = 0

        if not self._populated:
            return self
        else:
            return iter(self._result_cache)

    def process_row(self, row):
        return row

    def iterate(self):
        row = self.cursor.fetchone()
        if not row:
            self._populated = True
            raise StopIteration
        elif not self._initialized:
            self.initialize(self.cursor.description)
            self._initialized = True
        return self.process_row(row)

    def iterator(self):
        while True:
            yield self.iterate()

    def next(self):
        if self.__idx < self.__ct:
            inst = self._result_cache[self.__idx]
            self.__idx += 1
            return inst

        obj = self.iterate()
        self._result_cache.append(obj)
        self.__ct += 1
        self.__idx += 1
        return obj
    __next__ = next

    def fill_cache(self, n=None):
        n = n or float('Inf')
        if n < 0:
            raise ValueError('Negative values are not supported.')
        self.__idx = self.__ct
        while not self._populated and (n > self.__ct):
            try:
                self.next()
            except StopIteration:
                break

class ExtQueryResultWrapper(QueryResultWrapper):
    def initialize(self, description):
        model = self.model
        conv = []
        identity = lambda x: x
        for i in range(len(description)):
            column = description[i][0]
            func = identity
            if column in model._meta.columns:
                field_obj = model._meta.columns[column]
                column = field_obj.name
                func = field_obj.python_value
            elif self.column_meta is not None:
                select_column = self.column_meta[i]
                # Special-case handling aggregations.
                if (isinstance(select_column, Func) and
                        isinstance(select_column.nodes[0], Field)):
                    func = select_column.nodes[0].python_value
            conv.append((i, column, func))
        self.conv = conv

class TuplesQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        return tuple([self.conv[i][2](col) for i, col in enumerate(row)])

class NaiveQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        instance = self.model()
        for i, column, func in self.conv:
            setattr(instance, column, func(row[i]))
        instance.prepared()
        return instance

class DictQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        res = {}
        for i, column, func in self.conv:
            res[column] = func(row[i])
        return res

class ModelQueryResultWrapper(QueryResultWrapper):
    def initialize(self, description):
        column_map = []
        join_map = []
        models = set([self.model])
        for i, node in enumerate(self.column_meta):
            attr = conv = None
            if isinstance(node, Field):
                if isinstance(node, FieldProxy):
                    key = node._model_alias
                    constructor = node.model
                else:
                    key = constructor = node.model_class
                attr = node.name
                conv = node.python_value
            else:
                key = constructor = self.model
                if isinstance(node, Expression) and node._alias:
                    attr = node._alias
            column_map.append((key, constructor, attr, conv))
            models.add(key)

        joins = self.join_meta
        stack = [self.model]
        while stack:
            current = stack.pop()
            if current not in joins:
                continue

            for join in joins[current]:
                join_model = join.model_class
                if join_model in models:
                    fk_field = current._meta.rel_for_model(join_model)
                    if not fk_field:
                        if isinstance(join.on, Expression):
                            fk_name = join.on._alias or join.on.lhs.name
                        else:
                            # Patch the joined model using the name of the
                            # database table.
                            fk_name = join_model._meta.db_table
                    else:
                        fk_name = fk_field.name

                    stack.append(join_model)
                    join_map.append((current, fk_name, join_model))

        self.column_map, self.join_map = column_map, join_map

    def process_row(self, row):
        collected = self.construct_instance(row)
        instances = self.follow_joins(collected)
        for i in instances:
            i.prepared()
        return instances[0]

    def construct_instance(self, row):
        collected_models = {}
        for i, (key, constructor, attr, conv) in enumerate(self.column_map):
            value = row[i]
            if key not in collected_models:
                collected_models[key] = constructor()
            instance = collected_models[key]
            if attr is None:
                attr = self.cursor.description[i][0]
            if conv is not None:
                value = conv(value)
            setattr(instance, attr, value)

        return collected_models

    def follow_joins(self, collected):
        prepared = [collected[self.model]]
        for (lhs, attr, rhs) in self.join_map:
            inst = collected[lhs]
            joined_inst = collected[rhs]

            if joined_inst.get_id() is None and attr in inst._data:
                joined_inst.set_id(inst._data[attr])

            setattr(inst, attr, joined_inst)
            prepared.append(joined_inst)

        return prepared


class Query(Node):
    require_commit = True

    def __init__(self, model_class):
        super(Query, self).__init__()

        self.model_class = model_class
        self.database = model_class._meta.database

        self._dirty = True
        self._query_ctx = model_class
        self._joins = {self.model_class: []} # adjacency graph
        self._where = None

    def __repr__(self):
        sql, params = self.sql()
        return '%s %s %s' % (self.model_class, sql, params)

    def clone(self):
        query = type(self)(self.model_class)
        return self._clone_attributes(query)

    def _clone_attributes(self, query):
        if self._where is not None:
            query._where = self._where.clone()
        query._joins = self._clone_joins()
        query._query_ctx = self._query_ctx
        return query

    def _clone_joins(self):
        return dict(
            (mc, list(j)) for mc, j in self._joins.items()
        )

    def _build_tree(self, initial, expressions):
        reduced = reduce(operator.and_, expressions)
        if initial is None:
            return reduced
        return initial & reduced

    @returns_clone
    def where(self, *expressions):
        self._where = self._build_tree(self._where, expressions)

    @returns_clone
    def join(self, model_class, join_type=None, on=None):
        if not self._query_ctx._meta.rel_exists(model_class) and on is None:
            raise ValueError('No foreign key between %s and %s' % (
                self._query_ctx, model_class,
            ))
        if on and isinstance(on, basestring):
            on = self._query_ctx._meta.fields[on]
        self._joins.setdefault(self._query_ctx, [])
        self._joins[self._query_ctx].append(Join(model_class, join_type, on))
        self._query_ctx = model_class

    @returns_clone
    def switch(self, model_class=None):
        self._query_ctx = model_class or self.model_class

    def ensure_join(self, lm, rm, on=None):
        ctx = self._query_ctx
        for join in self._joins.get(lm, []):
            if join.model_class == rm:
                return self
        query = self.switch(lm).join(rm, on=on).switch(ctx)
        return query

    def convert_dict_to_node(self, qdict):
        accum = []
        joins = []
        relationship = (ForeignKeyField, ReverseRelationDescriptor)
        for key, value in sorted(qdict.items()):
            curr = self.model_class
            if '__' in key and key.rsplit('__', 1)[1] in DJANGO_MAP:
                key, op = key.rsplit('__', 1)
                op = DJANGO_MAP[op]
            else:
                op = OP_EQ
            for piece in key.split('__'):
                model_attr = getattr(curr, piece)
                if isinstance(model_attr, relationship):
                    curr = model_attr.rel_model
                    joins.append(model_attr)
            accum.append(Expression(model_attr, op, value))
        return accum, joins

    def filter(self, *args, **kwargs):
        # normalize args and kwargs into a new expression
        dq_node = Node()
        if args:
            dq_node &= reduce(operator.and_, [a.clone() for a in args])
        if kwargs:
            dq_node &= DQ(**kwargs)

        # dq_node should now be an Expression, lhs = Node(), rhs = ...
        q = deque([dq_node])
        dq_joins = set()
        while q:
            curr = q.popleft()
            if not isinstance(curr, Expression):
                continue
            for side, piece in (('lhs', curr.lhs), ('rhs', curr.rhs)):
                if isinstance(piece, DQ):
                    query, joins = self.convert_dict_to_node(piece.query)
                    dq_joins.update(joins)
                    expression = reduce(operator.and_, query)
                    # Apply values from the DQ object.
                    expression._negated = piece._negated
                    expression._alias = piece._alias
                    setattr(curr, side, expression)
                else:
                    q.append(piece)

        dq_node = dq_node.rhs

        query = self.clone()
        for field in dq_joins:
            if isinstance(field, ForeignKeyField):
                lm, rm = field.model_class, field.rel_model
                field_obj = field
            elif isinstance(field, ReverseRelationDescriptor):
                lm, rm = field.field.rel_model, field.rel_model
                field_obj = field.field
            query = query.ensure_join(lm, rm, field_obj)
        return query.where(dq_node)

    def compiler(self):
        return self.database.compiler()

    def sql(self):
        raise NotImplementedError

    def _execute(self):
        sql, params = self.sql()
        return self.database.execute_sql(sql, params, self.require_commit)

    def execute(self):
        raise NotImplementedError

    def scalar(self, as_tuple=False, convert=False):
        if convert:
            row = self.tuples().first()
        else:
            row = self._execute().fetchone()
        if row and not as_tuple:
            return row[0]
        else:
            return row

class RawQuery(Query):
    def __init__(self, model, query, *params):
        self._sql = query
        self._params = list(params)
        self._qr = None
        self._tuples = False
        self._dicts = False
        super(RawQuery, self).__init__(model)

    def clone(self):
        query = RawQuery(self.model_class, self._sql, *self._params)
        query._tuples = self._tuples
        query._dicts = self._dicts
        return query

    join = not_allowed('joining')
    where = not_allowed('where')
    switch = not_allowed('switch')

    @returns_clone
    def tuples(self, tuples=True):
        self._tuples = tuples

    @returns_clone
    def dicts(self, dicts=True):
        self._dicts = dicts

    def sql(self):
        return self._sql, self._params

    def execute(self):
        if self._qr is None:
            if self._tuples:
                ResultWrapper = TuplesQueryResultWrapper
            elif self._dicts:
                ResultWrapper = DictQueryResultWrapper
            else:
                ResultWrapper = NaiveQueryResultWrapper
            self._qr = ResultWrapper(self.model_class, self._execute(), None)
        return self._qr

    def __iter__(self):
        return iter(self.execute())

class SelectQuery(Query):
    def __init__(self, model_class, *selection):
        super(SelectQuery, self).__init__(model_class)
        self.require_commit = self.database.commit_select
        self._explicit_selection = len(selection) > 0
        selection = selection or model_class._meta.get_fields()
        self._select = self._model_shorthand(selection)
        self._group_by = None
        self._having = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._distinct = False
        self._for_update = False
        self._naive = False
        self._tuples = False
        self._dicts = False
        self._alias = None
        self._qr = None

    def _clone_attributes(self, query):
        query = super(SelectQuery, self)._clone_attributes(query)
        query._explicit_selection = self._explicit_selection
        query._select = list(self._select)
        if self._group_by is not None:
            query._group_by = list(self._group_by)
        if self._having:
            query._having = self._having.clone()
        if self._order_by is not None:
            query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset
        query._distinct = self._distinct
        query._for_update = self._for_update
        query._naive = self._naive
        query._tuples = self._tuples
        query._dicts = self._dicts
        query._alias = self._alias
        return query

    def _model_shorthand(self, args):
        accum = []
        for arg in args:
            if isinstance(arg, Node):
                accum.append(arg)
            elif isinstance(arg, Query):
                accum.append(arg)
            elif isinstance(arg, ModelAlias):
                accum.extend(arg.get_proxy_fields())
            elif isclass(arg) and issubclass(arg, Model):
                accum.extend(arg._meta.get_fields())
        return accum

    @returns_clone
    def group_by(self, *args):
        self._group_by = self._model_shorthand(args)

    @returns_clone
    def having(self, *expressions):
        self._having = self._build_tree(self._having, expressions)

    @returns_clone
    def order_by(self, *args):
        self._order_by = list(args)

    @returns_clone
    def limit(self, lim):
        self._limit = lim

    @returns_clone
    def offset(self, off):
        self._offset = off

    @returns_clone
    def paginate(self, page, paginate_by=20):
        if page > 0:
            page -= 1
        self._limit = paginate_by
        self._offset = page * paginate_by

    @returns_clone
    def distinct(self, is_distinct=True):
        self._distinct = is_distinct

    @returns_clone
    def for_update(self, for_update=True):
        self._for_update = for_update

    @returns_clone
    def naive(self, naive=True):
        self._naive = naive

    @returns_clone
    def tuples(self, tuples=True):
        self._tuples = tuples

    @returns_clone
    def dicts(self, dicts=True):
        self._dicts = dicts

    @returns_clone
    def alias(self, alias=None):
        self._alias = alias

    def annotate(self, rel_model, annotation=None):
        if annotation is None:
            annotation = fn.Count(rel_model._meta.primary_key).alias('count')
        query = self.clone()
        query = query.ensure_join(query._query_ctx, rel_model)
        if not query._group_by:
            query._group_by = [x.alias() for x in query._select]
        query._select = tuple(query._select) + (annotation,)
        return query

    def _aggregate(self, aggregation=None):
        if aggregation is None:
            aggregation = fn.Count(self.model_class._meta.primary_key)
        query = self.order_by()
        query._select = [aggregation]
        return query

    def aggregate(self, aggregation=None, convert=True):
        return self._aggregate(aggregation).scalar(convert=convert)

    def count(self):
        if self._distinct or self._group_by:
            return self.wrapped_count()

        # defaults to a count() of the primary key
        return self.aggregate(convert=False) or 0

    def wrapped_count(self):
        clone = self.order_by()
        clone._limit = clone._offset = None

        sql, params = clone.sql()
        wrapped = 'SELECT COUNT(1) FROM (%s) AS wrapped_select' % sql
        rq = RawQuery(self.model_class, wrapped, *params)
        return rq.scalar() or 0

    def exists(self):
        clone = self.paginate(1, 1)
        clone._select = [self.model_class._meta.primary_key]
        return bool(clone.scalar())

    def get(self):
        clone = self.paginate(1, 1)
        try:
            return clone.execute().next()
        except StopIteration:
            raise self.model_class.DoesNotExist(
                'Instance matching query does not exist:\nSQL: %s\nPARAMS: %s'
                % self.sql())

    def first(self):
        res = self.execute()
        res.fill_cache(1)
        try:
            return res._result_cache[0]
        except IndexError:
            pass

    def sql(self):
        return self.compiler().generate_select(self)

    def verify_naive(self):
        model_class = self.model_class
        for node in self._select:
            if isinstance(node, Field) and node.model_class != model_class:
                return False
        return True

    def execute(self):
        if self._dirty or not self._qr:
            model_class = self.model_class
            query_meta = [self._select, self._joins]
            if self._tuples:
                ResultWrapper = TuplesQueryResultWrapper
            elif self._dicts:
                ResultWrapper = DictQueryResultWrapper
            elif self._naive or not self._joins or self.verify_naive():
                ResultWrapper = NaiveQueryResultWrapper
            else:
                ResultWrapper = ModelQueryResultWrapper
            self._qr = ResultWrapper(model_class, self._execute(), query_meta)
            self._dirty = False
            return self._qr
        else:
            return self._qr

    def __iter__(self):
        return iter(self.execute())

    def iterator(self):
        return iter(self.execute().iterator())

    def __getitem__(self, value):
        start = end = None
        res = self.execute()
        if isinstance(value, slice):
            res.fill_cache(value.stop)
        else:
            res.fill_cache(value)
        return res._result_cache[value]

class UpdateQuery(Query):
    def __init__(self, model_class, update=None):
        self._update = update
        super(UpdateQuery, self).__init__(model_class)

    def _clone_attributes(self, query):
        query._update = dict(self._update)
        return query

    join = not_allowed('joining')

    def sql(self):
        return self.compiler().generate_update(self)

    def execute(self):
        return self.database.rows_affected(self._execute())

class InsertQuery(Query):
    def __init__(self, model_class, insert=None):
        mm = model_class._meta
        defaults = mm.get_default_dict()
        query = dict((mm.fields[f], v) for f, v in defaults.items())
        query.update(insert)
        self._insert = query
        super(InsertQuery, self).__init__(model_class)

    def _clone_attributes(self, query):
        query._insert = dict(self._insert)
        return query

    join = not_allowed('joining')
    where = not_allowed('where clause')

    def sql(self):
        return self.compiler().generate_insert(self)

    def execute(self):
        return self.database.last_insert_id(self._execute(), self.model_class)

class DeleteQuery(Query):
    join = not_allowed('joining')

    def sql(self):
        return self.compiler().generate_delete(self)

    def execute(self):
        return self.database.rows_affected(self._execute())


class Database(object):
    commit_select = False
    compiler_class = QueryCompiler
    field_overrides = {}
    for_update = False
    interpolation = '?'
    limit_max = None
    op_overrides = {}
    quote_char = '"'
    reserved_tables = []
    sequences = False
    subquery_delete_same_table = True

    def __init__(self, database, threadlocals=False, autocommit=True,
                 fields=None, ops=None, **connect_kwargs):
        self.init(database, **connect_kwargs)

        if threadlocals:
            self.__local = threading.local()
        else:
            self.__local = type('DummyLocal', (object,), {})

        self._conn_lock = threading.Lock()
        self.autocommit = autocommit

        self.field_overrides = dict_update(self.field_overrides, fields or {})
        self.op_overrides = dict_update(self.op_overrides, ops or {})

    def init(self, database, **connect_kwargs):
        self.deferred = database is None
        self.database = database
        self.connect_kwargs = connect_kwargs

    def connect(self):
        with self._conn_lock:
            if self.deferred:
                raise Exception('Error, database not properly initialized '
                                'before opening connection')
            self.__local.conn = self._connect(
                self.database,
                **self.connect_kwargs)
            self.__local.closed = False

    def close(self):
        with self._conn_lock:
            if self.deferred:
                raise Exception('Error, database not properly initialized '
                                'before closing connection')
            self._close(self.__local.conn)
            self.__local.closed = True

    def get_conn(self):
        if not hasattr(self.__local, 'closed') or self.__local.closed:
            self.connect()
        return self.__local.conn

    def is_closed(self):
        return getattr(self.__local, 'closed', True)

    def get_cursor(self):
        return self.get_conn().cursor()

    def _close(self, conn):
        conn.close()

    def _connect(self, database, **kwargs):
        raise NotImplementedError

    @classmethod
    def register_fields(cls, fields):
        cls.field_overrides = dict_update(cls.field_overrides, fields)

    @classmethod
    def register_ops(cls, ops):
        cls.op_overrides = dict_update(cls.op_overrides, ops)

    def last_insert_id(self, cursor, model):
        if model._meta.auto_increment:
            return cursor.lastrowid

    def rows_affected(self, cursor):
        return cursor.rowcount

    def sql_error_handler(self, exception, sql, params, require_commit):
        raise exception

    def compiler(self):
        return self.compiler_class(
            self.quote_char, self.interpolation, self.field_overrides,
            self.op_overrides)

    def execute_sql(self, sql, params=None, require_commit=True):
        logger.debug((sql, params))
        cursor = self.get_cursor()
        try:
            res = cursor.execute(sql, params or ())
        except Exception as exc:
            logger.error('Error executing query %s (%s)' % (sql, params))
            return self.sql_error_handler(exc, sql, params, require_commit)
        if require_commit and self.get_autocommit():
            self.commit()
        return cursor

    def begin(self):
        pass

    def commit(self):
        self.get_conn().commit()

    def rollback(self):
        self.get_conn().rollback()

    def set_autocommit(self, autocommit):
        self.__local.autocommit = autocommit

    def get_autocommit(self):
        if not hasattr(self.__local, 'autocommit'):
            self.set_autocommit(self.autocommit)
        return self.__local.autocommit

    def transaction(self):
        return transaction(self)

    def commit_on_success(self, func):
        def inner(*args, **kwargs):
            orig = self.get_autocommit()
            self.set_autocommit(False)
            self.begin()
            try:
                res = func(*args, **kwargs)
                self.commit()
            except:
                self.rollback()
                raise
            else:
                return res
            finally:
                self.set_autocommit(orig)
        return inner

    def get_tables(self):
        raise NotImplementedError

    def get_indexes_for_table(self, table):
        raise NotImplementedError

    def sequence_exists(self, seq):
        raise NotImplementedError

    def create_table(self, model_class, safe=False):
        qc = self.compiler()
        return self.execute_sql(qc.create_table(model_class, safe))

    def create_index(self, model_class, fields, unique=False):
        qc = self.compiler()
        if not isinstance(fields, (list, tuple)):
            raise ValueError('Fields passed to "create_index" must be a list '
                             'or tuple: "%s"' % fields)
        fobjs = [
            model_class._meta.fields[f] if isinstance(f, basestring) else f
            for f in fields]
        return self.execute_sql(qc.create_index(model_class, fobjs, unique))

    def create_foreign_key(self, model_class, field):
        if not field.primary_key:
            return self.create_index(model_class, [field], field.unique)

    def create_sequence(self, seq):
        if self.sequences:
            qc = self.compiler()
            return self.execute_sql(qc.create_sequence(seq))

    def drop_table(self, model_class, fail_silently=False):
        qc = self.compiler()
        return self.execute_sql(qc.drop_table(model_class, fail_silently))

    def drop_sequence(self, seq):
        if self.sequences:
            qc = self.compiler()
            return self.execute_sql(qc.drop_sequence(seq))

    def extract_date(self, date_part, date_field):
        return fn.EXTRACT(Clause(date_part, R('FROM'), date_field))

class SqliteDatabase(Database):
    limit_max = -1
    op_overrides = {
        OP_LIKE: 'GLOB',
        OP_ILIKE: 'LIKE',
    }
    if sqlite3:
        ConnectionError = sqlite3.OperationalError

    def _connect(self, database, **kwargs):
        if not sqlite3:
            raise ImproperlyConfigured('sqlite3 must be installed on the system')
        conn = sqlite3.connect(database, **kwargs)
        conn.create_function('date_part', 2, _sqlite_date_part)
        return conn

    def get_indexes_for_table(self, table):
        res = self.execute_sql('PRAGMA index_list(%s);' % self.quote(table))
        rows = sorted([(r[1], r[2] == 1) for r in res.fetchall()])
        return rows

    def get_tables(self):
        res = self.execute_sql('select name from sqlite_master where '
                               'type="table" order by name;')
        return [r[0] for r in res.fetchall()]

    def extract_date(self, date_part, date_field):
        return fn.date_part(date_part, date_field)

class PostgresqlDatabase(Database):
    commit_select = True
    field_overrides = {
        'blob': 'BYTEA',
        'bool': 'BOOLEAN',
        'datetime': 'TIMESTAMP',
        'decimal': 'NUMERIC',
        'double': 'DOUBLE PRECISION',
        'primary_key': 'SERIAL',
    }
    for_update = True
    interpolation = '%s'
    reserved_tables = ['user']
    sequences = True

    def _connect(self, database, **kwargs):
        if not psycopg2:
            raise ImproperlyConfigured('psycopg2 must be installed.')
        return psycopg2.connect(database=database, **kwargs)

    def last_insert_id(self, cursor, model):
        seq = model._meta.primary_key.sequence
        if seq:
            cursor.execute("SELECT CURRVAL('\"%s\"')" % (seq))
            return cursor.fetchone()[0]
        elif model._meta.auto_increment:
            cursor.execute("SELECT CURRVAL('\"%s_%s_seq\"')" % (
                model._meta.db_table, model._meta.primary_key.db_column))
            return cursor.fetchone()[0]

    def get_indexes_for_table(self, table):
        res = self.execute_sql("""
            SELECT c2.relname, i.indisprimary, i.indisunique
            FROM
                pg_catalog.pg_class c,
                pg_catalog.pg_class c2,
                pg_catalog.pg_index i
            WHERE
                c.relname = %s AND c.oid = i.indrelid AND i.indexrelid = c2.oid
            ORDER BY i.indisprimary DESC, i.indisunique DESC, c2.relname""",
            (table,))
        return sorted([(r[0], r[1]) for r in res.fetchall()])

    def get_tables(self):
        res = self.execute_sql("""
            SELECT c.relname
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'v', '')
                AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                AND pg_catalog.pg_table_is_visible(c.oid)
            ORDER BY c.relname""")
        return [row[0] for row in res.fetchall()]

    def sequence_exists(self, sequence):
        res = self.execute_sql("""
            SELECT COUNT(*)
            FROM pg_class, pg_namespace
            WHERE relkind='S'
                AND pg_class.relnamespace = pg_namespace.oid
                AND relname=%s""", (sequence,))
        return bool(res.fetchone()[0])

    def set_search_path(self, *search_path):
        path_params = ','.join(['%s'] * len(search_path))
        self.execute_sql('SET search_path TO %s' % path_params, search_path)

class MySQLDatabase(Database):
    commit_select = True
    field_overrides = {
        'bool': 'BOOL',
        'decimal': 'NUMERIC',
        'double': 'DOUBLE PRECISION',
        'float': 'FLOAT',
        'primary_key': 'INTEGER AUTO_INCREMENT',
        'text': 'LONGTEXT',
    }
    for_update = True
    interpolation = '%s'
    limit_max = 2 ** 64 - 1  # MySQL quirk
    op_overrides = {
        OP_LIKE: 'LIKE BINARY',
        OP_ILIKE: 'LIKE',
        OP_XOR: 'XOR',
    }
    quote_char = '`'
    subquery_delete_same_table = False

    def _connect(self, database, **kwargs):
        if not mysql:
            raise ImproperlyConfigured('MySQLdb must be installed.')
        conn_kwargs = {
            'charset': 'utf8',
            'use_unicode': True,
        }
        conn_kwargs.update(kwargs)
        return mysql.connect(db=database, **conn_kwargs)

    def create_foreign_key(self, model_class, field):
        compiler = self.compiler()
        framing = """
            ALTER TABLE %(table)s ADD CONSTRAINT %(constraint)s
            FOREIGN KEY (%(field)s) REFERENCES %(to)s(%(to_field)s)%(cascade)s;
        """
        db_table = model_class._meta.db_table
        constraint = 'fk_%s_%s_%s' % (
            db_table,
            field.rel_model._meta.db_table,
            field.db_column,
        )

        quote = compiler.quote
        query = framing % {
            'table': quote(db_table),
            'constraint': quote(constraint),
            'field': quote(field.db_column),
            'to': quote(field.rel_model._meta.db_table),
            'to_field': quote(field.rel_model._meta.primary_key.db_column),
            'cascade': ' ON DELETE CASCADE' if field.cascade else ''}

        self.execute_sql(query)
        return super(MySQLDatabase, self).create_foreign_key(
            model_class, field)

    def get_indexes_for_table(self, table):
        res = self.execute_sql('SHOW INDEXES IN `%s`;' % table)
        rows = sorted([(r[2], r[1] == 0) for r in res.fetchall()])
        return rows

    def get_tables(self):
        res = self.execute_sql('SHOW TABLES;')
        return [r[0] for r in res.fetchall()]

    def extract_date(self, date_part, date_field):
        assert date_part.lower() in DT_LOOKUPS
        return fn.EXTRACT(Clause(R(date_part), R('FROM'), date_field))


class transaction(object):
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self._orig = self.db.get_autocommit()
        self.db.set_autocommit(False)
        self.db.begin()

    def __exit__(self, exc_type, exc_val, exc_tb):
        success = True
        if exc_type:
            self.db.rollback()
            success = False
        else:
            self.db.commit()
        self.db.set_autocommit(self._orig)
        return success


class FieldProxy(Field):
    def __init__(self, alias, field_instance):
        self._model_alias = alias
        self.model = self._model_alias.model_class
        self.field_instance = field_instance

    def clone_base(self):
        return FieldProxy(self._model_alias, self.field_instance)

    def __getattr__(self, attr):
        if attr == 'model_class':
            return self._model_alias
        return getattr(self.field_instance, attr)

class ModelAlias(object):
    def __init__(self, model_class):
        self.__dict__['model_class'] = model_class

    def __getattr__(self, attr):
        model_attr = getattr(self.model_class, attr)
        if isinstance(model_attr, Field):
            return FieldProxy(self, model_attr)
        return model_attr

    def __setattr__(self, attr, value):
        raise AttributeError('Cannot set attributes on ModelAlias instances')

    def get_proxy_fields(self):
        return [
            FieldProxy(self, f) for f in self.model_class._meta.get_fields()]


class DoesNotExist(Exception): pass

default_database = SqliteDatabase('peewee.db')

class ModelOptions(object):
    def __init__(self, cls, database=None, db_table=None, indexes=None,
                 order_by=None, primary_key=None, **kwargs):
        self.model_class = cls
        self.name = cls.__name__.lower()
        self.fields = {}
        self.columns = {}
        self.defaults = {}

        self.database = database or default_database
        self.db_table = db_table
        self.indexes = list(indexes or [])
        self.order_by = order_by
        self.primary_key = primary_key

        self.auto_increment = None
        self.rel = {}
        self.reverse_rel = {}

        for key, value in kwargs.items():
            setattr(self, key, value)
        self._additional_keys = set(kwargs.keys())

    def prepared(self):
        for field in self.fields.values():
            if field.default is not None:
                self.defaults[field] = field.default

        if self.order_by:
            norm_order_by = []
            for clause in self.order_by:
                field = self.fields[clause.lstrip('-')]
                if clause.startswith('-'):
                    norm_order_by.append(field.desc())
                else:
                    norm_order_by.append(field.asc())
            self.order_by = norm_order_by

    def get_default_dict(self):
        dd = {}
        for field, default in self.defaults.items():
            if callable(default):
                dd[field.name] = default()
            else:
                dd[field.name] = default
        return dd

    def get_sorted_fields(self):
        key = lambda i: (i[1] is self.primary_key and 1 or 2, i[1]._order)
        return sorted(self.fields.items(), key=key)

    def get_field_names(self):
        return [f[0] for f in self.get_sorted_fields()]

    def get_fields(self):
        return [f[1] for f in self.get_sorted_fields()]

    def rel_for_model(self, model, field_obj=None):
        for field in self.get_fields():
            if isinstance(field, ForeignKeyField) and field.rel_model == model:
                if field_obj is None or field_obj.name == field.name:
                    return field

    def reverse_rel_for_model(self, model):
        return model._meta.rel_for_model(self.model_class)

    def rel_exists(self, model):
        return self.rel_for_model(model) or self.reverse_rel_for_model(model)


class BaseModel(type):
    inheritable = set(['database', 'indexes', 'order_by', 'primary_key'])

    def __new__(cls, name, bases, attrs):
        if not bases:
            return super(BaseModel, cls).__new__(cls, name, bases, attrs)

        meta_options = {}
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        model_pk = getattr(meta, 'primary_key', None)
        parent_pk = None

        # inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them
        for b in bases:
            if not hasattr(b, '_meta'):
                continue

            base_meta = getattr(b, '_meta')
            if parent_pk is None:
                parent_pk = deepcopy(base_meta.primary_key)
            all_inheritable = cls.inheritable | base_meta._additional_keys
            for (k, v) in base_meta.__dict__.items():
                if k in all_inheritable and k not in meta_options:
                    meta_options[k] = v

            for (k, v) in b.__dict__.items():
                if isinstance(v, FieldDescriptor) and k not in attrs:
                    if not v.field.primary_key:
                        attrs[k] = deepcopy(v.field)

        # initialize the new class and set the magic attributes
        cls = super(BaseModel, cls).__new__(cls, name, bases, attrs)
        cls._meta = ModelOptions(cls, **meta_options)
        cls._data = None
        cls._meta.indexes = list(cls._meta.indexes)

        # replace fields with field descriptors, calling the add_to_class hook
        for name, attr in list(cls.__dict__.items()):
            if isinstance(attr, Field):
                attr.add_to_class(cls, name)
                if attr.primary_key and model_pk:
                    raise ValueError('primary key is overdetermined.')
                elif attr.primary_key:
                    model_pk = attr

        if model_pk is None:
            if parent_pk:
                model_pk, name = parent_pk, parent_pk.name
            else:
                model_pk, name = PrimaryKeyField(primary_key=True), 'id'
            model_pk.add_to_class(cls, name)
        elif isinstance(model_pk, CompositeKey):
            model_pk.add_to_class(cls, '_composite_key')

        cls._meta.primary_key = model_pk
        cls._meta.auto_increment = (
            isinstance(model_pk, PrimaryKeyField) or
            bool(model_pk.sequence))
        if not cls._meta.db_table:
            cls._meta.db_table = re.sub('[^\w]+', '_', cls.__name__.lower())

        # create a repr and error class before finalizing
        if hasattr(cls, '__unicode__'):
            setattr(cls, '__repr__', lambda self: '<%s: %r>' % (
                cls.__name__, self.__unicode__()))

        exc_name = '%sDoesNotExist' % cls.__name__
        exception_class = type(exc_name, (DoesNotExist,), {})
        cls.DoesNotExist = exception_class
        cls._meta.prepared()

        return cls

class Model(with_metaclass(BaseModel)):
    def __init__(self, *args, **kwargs):
        self._data = self._meta.get_default_dict()
        self._obj_cache = {} # cache of related objects

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def alias(cls):
        return ModelAlias(cls)

    @classmethod
    def select(cls, *selection):
        query = SelectQuery(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    @classmethod
    def update(cls, **update):
        fdict = dict((cls._meta.fields[f], v) for f, v in update.items())
        return UpdateQuery(cls, fdict)

    @classmethod
    def insert(cls, **insert):
        fdict = dict((cls._meta.fields[f], v) for f, v in insert.items())
        return InsertQuery(cls, fdict)

    @classmethod
    def delete(cls):
        return DeleteQuery(cls)

    @classmethod
    def raw(cls, sql, *params):
        return RawQuery(cls, sql, *params)

    @classmethod
    def create(cls, **query):
        inst = cls(**query)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def get(cls, *query, **kwargs):
        sq = cls.select().naive()
        if query:
            sq = sq.where(*query)
        if kwargs:
            sq = sq.filter(**kwargs)
        return sq.get()

    @classmethod
    def get_or_create(cls, **kwargs):
        sq = cls.select().filter(**kwargs)
        try:
            return sq.get()
        except cls.DoesNotExist:
            return cls.create(**kwargs)

    @classmethod
    def filter(cls, *dq, **query):
        return cls.select().filter(*dq, **query)

    @classmethod
    def table_exists(cls):
        return cls._meta.db_table in cls._meta.database.get_tables()

    @classmethod
    def create_table(cls, fail_silently=False):
        if fail_silently and cls.table_exists():
            return

        db = cls._meta.database
        pk = cls._meta.primary_key
        if db.sequences and pk.sequence:
            if not db.sequence_exists(pk.sequence):
                db.create_sequence(pk.sequence)

        db.create_table(cls)
        cls._create_indexes()

    @classmethod
    def _create_indexes(cls):
        db = cls._meta.database
        for field_name, field_obj in cls._meta.fields.items():
            if isinstance(field_obj, ForeignKeyField):
                db.create_foreign_key(cls, field_obj)
            elif field_obj.index or field_obj.unique:
                db.create_index(cls, [field_obj], field_obj.unique)

        if cls._meta.indexes:
            for fields, unique in cls._meta.indexes:
                db.create_index(cls, fields, unique)

    @classmethod
    def drop_table(cls, fail_silently=False):
        cls._meta.database.drop_table(cls, fail_silently)

    def get_id(self):
        return getattr(self, self._meta.primary_key.name)

    def set_id(self, id):
        setattr(self, self._meta.primary_key.name, id)

    def pk_expr(self):
        return self._meta.primary_key == self.get_id()

    def prepared(self):
        pass

    def _prune_fields(self, field_dict, only):
        new_data = {}
        for field in only:
            if field.name in field_dict:
                new_data[field.name] = field_dict[field.name]
        return new_data

    def save(self, force_insert=False, only=None):
        field_dict = dict(self._data)
        pk = self._meta.primary_key
        if only:
            field_dict = self._prune_fields(field_dict, only)
        if self.get_id() is not None and not force_insert:
            field_dict.pop(pk.name, None)
            self.update(**field_dict).where(self.pk_expr()).execute()
        else:
            pk = self.get_id()
            ret_pk = self.insert(**field_dict).execute()
            if ret_pk is not None:
                pk = ret_pk
            self.set_id(pk)

    def dependencies(self, search_nullable=False):
        query = self.select().where(self.pk_expr())
        stack = [(type(self), query)]
        seen = set()

        while stack:
            klass, query = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            for rel_name, fk in klass._meta.reverse_rel.items():
                rel_model = fk.model_class
                node = fk << query
                if not fk.null or search_nullable:
                    stack.append((rel_model, rel_model.select().where(node)))
                yield (node, fk)

    def delete_instance(self, recursive=False, delete_nullable=False):
        if recursive:
            dependencies = self.dependencies(delete_nullable)
            for query, fk in reversed(list(dependencies)):
                model = fk.model_class
                if fk.null and not delete_nullable:
                    model.update(**{fk.name: None}).where(query).execute()
                else:
                    model.delete().where(query).execute()
        return self.delete().where(self.pk_expr()).execute()

    def __eq__(self, other):
        return (
            other.__class__ == self.__class__ and
            self.get_id() is not None and
            other.get_id() == self.get_id())

    def __ne__(self, other):
        return not self == other


def prefetch_add_subquery(sq, subqueries):
    fixed_queries = [(sq, None)]
    for i, subquery in enumerate(subqueries):
        if not isinstance(subquery, Query) and issubclass(subquery, Model):
            subquery = subquery.select()
        subquery_model = subquery.model_class
        fkf = None
        for j in reversed(range(i + 1)):
            last_query = fixed_queries[j][0]
            fkf = subquery_model._meta.rel_for_model(last_query.model_class)
            if fkf:
                break
        if not fkf:
            raise AttributeError('Error: unable to find foreign key for '
                                 'query: %s' % subquery)
        fixed_queries.append((subquery.where(fkf << last_query), fkf))

    return fixed_queries

def prefetch(sq, *subqueries):
    if not subqueries:
        return sq
    fixed_queries = prefetch_add_subquery(sq, subqueries)

    deps = {}
    rel_map = {}
    for query, foreign_key_field in reversed(fixed_queries):
        query_model = query.model_class
        deps[query_model] = {}
        id_map = deps[query_model]
        has_relations = bool(rel_map.get(query_model))

        for result in query:
            if foreign_key_field:
                fk_val = result._data[foreign_key_field.name]
                id_map.setdefault(fk_val, [])
                id_map[fk_val].append(result)
            if has_relations:
                for rel_model, rel_fk in rel_map[query_model]:
                    rel_name = '%s_prefetch' % rel_fk.related_name
                    rel_instances = deps[rel_model].get(result.get_id(), [])
                    for inst in rel_instances:
                        setattr(inst, rel_fk.name, result)
                    setattr(result, rel_name, rel_instances)
        if foreign_key_field:
            rel_model = foreign_key_field.rel_model
            rel_map.setdefault(rel_model, [])
            rel_map[rel_model].append((query_model, foreign_key_field))

    return query

def create_model_tables(models, **create_table_kwargs):
    """Create tables for all given models (in the right order)."""
    for m in sort_models_topologically(models):
        m.create_table(**create_table_kwargs)

def drop_model_tables(models, **drop_table_kwargs):
    """Drop tables for all given models (in the right order)."""
    for m in reversed(sort_models_topologically(models)):
        m.drop_table(**drop_table_kwargs)

def sort_models_topologically(models):
    """Sort models topologically so that parents will precede children."""
    models = set(models)
    seen = set()
    ordering = []
    def dfs(model):
        if model in models and model not in seen:
            seen.add(model)
            for foreign_key in model._meta.reverse_rel.values():
                dfs(foreign_key.model_class)
            ordering.append(model)  # parent will follow descendants
    # order models by name and table initially to guarantee a total ordering
    names = lambda m: (m._meta.name, m._meta.db_table)
    for m in sorted(models, key=names, reverse=True):
        dfs(m)
    return list(reversed(ordering))  # want parents first in output ordering

########NEW FILE########
__FILENAME__ = TftpClient
"""This module implements the TFTP Client functionality. Instantiate an
instance of the client, and then use its upload or download method. Logging is
performed via a standard logging object set in TftpShared."""

import types
from TftpShared import *
from TftpPacketTypes import *
from TftpContexts import TftpContextClientDownload, TftpContextClientUpload

class TftpClient(TftpSession):
    """This class is an implementation of a tftp client. Once instantiated, a
    download can be initiated via the download() method, or an upload via the
    upload() method."""

    def __init__(self, host, port, options={}):
        TftpSession.__init__(self)
        self.context = None
        self.host = host
        self.iport = port
        self.filename = None
        self.options = options
        if self.options.has_key('blksize'):
            size = self.options['blksize']
            tftpassert(types.IntType == type(size), "blksize must be an int")
            if size < MIN_BLKSIZE or size > MAX_BLKSIZE:
                raise TftpException, "Invalid blksize: %d" % size

    def download(self, filename, output, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp download from the configured remote
        host, requesting the filename passed. It saves the file to a local
        file specified in the output parameter. If a packethook is provided,
        it must be a function that takes a single parameter, which will be a
        copy of each DAT packet received in the form of a TftpPacketDAT
        object. The timeout parameter may be used to override the default
        SOCK_TIMEOUT setting, which is the amount of time that the client will
        wait for a receive packet to arrive.

        Note: If output is a hyphen then stdout is used."""
        # We're downloading.
        log.debug("Creating download context with the following params:")
        log.debug("host = %s, port = %s, filename = %s, output = %s"
            % (self.host, self.iport, filename, output))
        log.debug("options = %s, packethook = %s, timeout = %s"
            % (self.options, packethook, timeout))
        self.context = TftpContextClientDownload(self.host,
                                                 self.iport,
                                                 filename,
                                                 output,
                                                 self.options,
                                                 packethook,
                                                 timeout)
        self.context.start()
        # Download happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Download complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info("Downloaded %.2f bytes in %.2f seconds" % (metrics.bytes, metrics.duration))
            log.info("Average rate: %.2f kbps" % metrics.kbps)
        log.info("%.2f bytes in resent data" % metrics.resent_bytes)
        log.info("Received %d duplicate packets" % metrics.dupcount)

    def upload(self, filename, input, packethook=None, timeout=SOCK_TIMEOUT):
        """This method initiates a tftp upload to the configured remote host,
        uploading the filename passed.  If a packethook is provided, it must
        be a function that takes a single parameter, which will be a copy of
        each DAT packet sent in the form of a TftpPacketDAT object. The
        timeout parameter may be used to override the default SOCK_TIMEOUT
        setting, which is the amount of time that the client will wait for a
        DAT packet to be ACKd by the server.

        The input option is the full path to the file to upload, which can
        optionally be '-' to read from stdin.

        Note: If output is a hyphen then stdout is used."""
        self.context = TftpContextClientUpload(self.host,
                                                 self.iport,
                                                 filename,
                                                 input,
                                                 self.options,
                                                 packethook,
                                                 timeout)
        self.context.start()
        # Upload happens here
        self.context.end()

        metrics = self.context.metrics

        log.info('')
        log.info("Upload complete.")
        if metrics.duration == 0:
            log.info("Duration too short, rate undetermined")
        else:
            log.info("Uploaded %d bytes in %.2f seconds" % (metrics.bytes, metrics.duration))
            log.info("Average rate: %.2f kbps" % metrics.kbps)
        log.info("%.2f bytes in resent data" % metrics.resent_bytes)
        log.info("Resent %d packets" % metrics.dupcount)

########NEW FILE########
__FILENAME__ = TftpContexts
"""This module implements all contexts for state handling during uploads and
downloads, the main interface to which being the TftpContext base class.

The concept is simple. Each context object represents a single upload or
download, and the state object in the context object represents the current
state of that transfer. The state object has a handle() method that expects
the next packet in the transfer, and returns a state object until the transfer
is complete, at which point it returns None. That is, unless there is a fatal
error, in which case a TftpException is returned instead."""

from TftpShared import *
from TftpPacketTypes import *
from TftpPacketFactory import TftpPacketFactory
from TftpStates import *
import socket, time, sys

###############################################################################
# Utility classes
###############################################################################

class TftpMetrics(object):
    """A class representing metrics of the transfer."""
    def __init__(self):
        # Bytes transferred
        self.bytes = 0
        # Bytes re-sent
        self.resent_bytes = 0
        # Duplicate packets received
        self.dups = {}
        self.dupcount = 0
        # Times
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        # Rates
        self.bps = 0
        self.kbps = 0
        # Generic errors
        self.errors = 0

    def compute(self):
        # Compute transfer time
        self.duration = self.end_time - self.start_time
        if self.duration == 0:
            self.duration = 1
        log.debug("TftpMetrics.compute: duration is %s" % self.duration)
        self.bps = (self.bytes * 8.0) / self.duration
        self.kbps = self.bps / 1024.0
        log.debug("TftpMetrics.compute: kbps is %s" % self.kbps)
        for key in self.dups:
            self.dupcount += self.dups[key]

    def add_dup(self, pkt):
        """This method adds a dup for a packet to the metrics."""
        log.debug("Recording a dup of %s" % pkt)
        s = str(pkt)
        if self.dups.has_key(s):
            self.dups[s] += 1
        else:
            self.dups[s] = 1
        tftpassert(self.dups[s] < MAX_DUPS, "Max duplicates reached")

###############################################################################
# Context classes
###############################################################################

class TftpContext(object):
    """The base class of the contexts."""

    def __init__(self, host, port, timeout, dyn_file_func=None):
        """Constructor for the base context, setting shared instance
        variables."""
        self.file_to_transfer = None
        self.fileobj = None
        self.options = None
        self.packethook = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.timeout = timeout
        self.state = None
        self.next_block = 0
        self.factory = TftpPacketFactory()
        # Note, setting the host will also set self.address, as it's a property.
        self.host = host
        self.port = port
        # The port associated with the TID
        self.tidport = None
        # Metrics
        self.metrics = TftpMetrics()
        # Fluag when the transfer is pending completion.
        self.pending_complete = False
        # Time when this context last received any traffic.
        # FIXME: does this belong in metrics?
        self.last_update = 0
        # The last packet we sent, if applicable, to make resending easy.
        self.last_pkt = None
        self.dyn_file_func = dyn_file_func
        # Count the number of retry attempts.
        self.retry_count = 0

    def getBlocksize(self):
        """Fetch the current blocksize for this session."""
        return int(self.options.get('blksize', 512))

    def __del__(self):
        """Simple destructor to try to call housekeeping in the end method if
        not called explicitely. Leaking file descriptors is not a good
        thing."""
        self.end()

    def checkTimeout(self, now):
        """Compare current time with last_update time, and raise an exception
        if we're over the timeout time."""
        log.debug("checking for timeout on session %s" % self)
        if now - self.last_update > self.timeout:
            raise TftpTimeout, "Timeout waiting for traffic"

    def start(self):
        raise NotImplementedError, "Abstract method"

    def end(self):
        """Perform session cleanup, since the end method should always be
        called explicitely by the calling code, this works better than the
        destructor."""
        log.debug("in TftpContext.end")
        if self.fileobj is not None and not self.fileobj.closed:
            log.debug("self.fileobj is open - closing")
            self.fileobj.close()

    def gethost(self):
        "Simple getter method for use in a property."
        return self.__host

    def sethost(self, host):
        """Setter method that also sets the address property as a result
        of the host that is set."""
        self.__host = host
        self.address = socket.gethostbyname(host)

    host = property(gethost, sethost)

    def setNextBlock(self, block):
        if block >= 2 ** 16:
            log.debug("Block number rollover to 0 again")
            block = 0
        self.__eblock = block

    def getNextBlock(self):
        return self.__eblock

    next_block = property(getNextBlock, setNextBlock)

    def cycle(self):
        """Here we wait for a response from the server after sending it
        something, and dispatch appropriate action to that response."""
        try:
            (buffer, (raddress, rport)) = self.sock.recvfrom(MAX_BLKSIZE)
        except socket.timeout:
            log.warn("Timeout waiting for traffic, retrying...")
            raise TftpTimeout, "Timed-out waiting for traffic"

        # Ok, we've received a packet. Log it.
        log.debug("Received %d bytes from %s:%s"
                        % (len(buffer), raddress, rport))
        # And update our last updated time.
        self.last_update = time.time()

        # Decode it.
        recvpkt = self.factory.parse(buffer)

        # Check for known "connection".
        if raddress != self.address:
            log.warn("Received traffic from %s, expected host %s. Discarding"
                        % (raddress, self.host))

        if self.tidport and self.tidport != rport:
            log.warn("Received traffic from %s:%s but we're "
                        "connected to %s:%s. Discarding."
                        % (raddress, rport,
                        self.host, self.tidport))

        # If there is a packethook defined, call it. We unconditionally
        # pass all packets, it's up to the client to screen out different
        # kinds of packets. This way, the client is privy to things like
        # negotiated options.
        if self.packethook:
            self.packethook(recvpkt)

        # And handle it, possibly changing state.
        self.state = self.state.handle(recvpkt, raddress, rport)
        # If we didn't throw any exceptions here, reset the retry_count to
        # zero.
        self.retry_count = 0

class TftpContextServer(TftpContext):
    """The context for the server."""
    def __init__(self, host, port, timeout, root, dyn_file_func=None):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout,
                             dyn_file_func
                             )
        # At this point we have no idea if this is a download or an upload. We
        # need to let the start state determine that.
        self.state = TftpStateServerStart(self)
        self.root = root
        self.dyn_file_func = dyn_file_func

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self, buffer):
        """Start the state cycle. Note that the server context receives an
        initial packet in its start method. Also note that the server does not
        loop on cycle(), as it expects the TftpServer object to manage
        that."""
        log.debug("In TftpContextServer.start")
        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)
        # And update our last updated time.
        self.last_update = time.time()

        pkt = self.factory.parse(buffer)
        log.debug("TftpContextServer.start() - factory returned a %s" % pkt)

        # Call handle once with the initial packet. This should put us into
        # the download or the upload state.
        self.state = self.state.handle(pkt,
                                       self.host,
                                       self.port)

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()

class TftpContextClientUpload(TftpContext):
    """The upload context for the client during an upload.
    Note: If input is a hyphen, then we will use stdin."""
    def __init__(self,
                 host,
                 port,
                 filename,
                 input,
                 options,
                 packethook,
                 timeout):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout)
        self.file_to_transfer = filename
        self.options = options
        self.packethook = packethook
        if input == '-':
            self.fileobj = sys.stdin
        else:
            self.fileobj = open(input, "rb")

        log.debug("TftpContextClientUpload.__init__()")
        log.debug("file_to_transfer = %s, options = %s" %
            (self.file_to_transfer, self.options))

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self):
        log.info("Sending tftp upload request to %s" % self.host)
        log.info("    filename -> %s" % self.file_to_transfer)
        log.info("    options -> %s" % self.options)

        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)

        # FIXME: put this in a sendWRQ method?
        pkt = TftpPacketWRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = "octet" # FIXME - shouldn't hardcode this
        pkt.options = self.options
        self.sock.sendto(pkt.encode().buffer, (self.host, self.port))
        self.next_block = 1
        self.last_pkt = pkt
        # FIXME: should we centralize sendto operations so we can refactor all
        # saving of the packet to the last_pkt field?

        self.state = TftpStateSentWRQ(self)

        while self.state:
            try:
                log.debug("State is %s" % self.state)
                self.cycle()
            except TftpTimeout, err:
                log.error(str(err))
                self.retry_count += 1
                if self.retry_count >= TIMEOUT_RETRIES:
                    log.debug("hit max retries, giving up")
                    raise
                else:
                    log.warn("resending last packet")
                    self.state.resendLast()

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()

class TftpContextClientDownload(TftpContext):
    """The download context for the client during a download.
    Note: If output is a hyphen, then the output will be sent to stdout."""
    def __init__(self,
                 host,
                 port,
                 filename,
                 output,
                 options,
                 packethook,
                 timeout):
        TftpContext.__init__(self,
                             host,
                             port,
                             timeout)
        # FIXME: should we refactor setting of these params?
        self.file_to_transfer = filename
        self.options = options
        self.packethook = packethook
        # FIXME - need to support alternate return formats than files?
        # File-like objects would be ideal, ala duck-typing.
        # If the filename is -, then use stdout
        if output == '-':
            self.fileobj = sys.stdout
        else:
            self.fileobj = open(output, "wb")

        log.debug("TftpContextClientDownload.__init__()")
        log.debug("file_to_transfer = %s, options = %s" %
            (self.file_to_transfer, self.options))

    def __str__(self):
        return "%s:%s %s" % (self.host, self.port, self.state)

    def start(self):
        """Initiate the download."""
        log.info("Sending tftp download request to %s" % self.host)
        log.info("    filename -> %s" % self.file_to_transfer)
        log.info("    options -> %s" % self.options)

        self.metrics.start_time = time.time()
        log.debug("Set metrics.start_time to %s" % self.metrics.start_time)

        # FIXME: put this in a sendRRQ method?
        pkt = TftpPacketRRQ()
        pkt.filename = self.file_to_transfer
        pkt.mode = "octet" # FIXME - shouldn't hardcode this
        pkt.options = self.options
        self.sock.sendto(pkt.encode().buffer, (self.host, self.port))
        self.next_block = 1
        self.last_pkt = pkt

        self.state = TftpStateSentRRQ(self)

        while self.state:
            try:
                log.debug("State is %s" % self.state)
                self.cycle()
            except TftpTimeout, err:
                log.error(str(err))
                self.retry_count += 1
                if self.retry_count >= TIMEOUT_RETRIES:
                    log.debug("hit max retries, giving up")
                    raise
                else:
                    log.warn("resending last packet")
                    self.state.resendLast()

    def end(self):
        """Finish up the context."""
        TftpContext.end(self)
        self.metrics.end_time = time.time()
        log.debug("Set metrics.end_time to %s" % self.metrics.end_time)
        self.metrics.compute()

########NEW FILE########
__FILENAME__ = TftpPacketFactory
"""This module implements the TftpPacketFactory class, which can take a binary
buffer, and return the appropriate TftpPacket object to represent it, via the
parse() method."""

from TftpShared import *
from TftpPacketTypes import *

class TftpPacketFactory(object):
    """This class generates TftpPacket objects. It is responsible for parsing
    raw buffers off of the wire and returning objects representing them, via
    the parse() method."""
    def __init__(self):
        self.classes = {
            1: TftpPacketRRQ,
            2: TftpPacketWRQ,
            3: TftpPacketDAT,
            4: TftpPacketACK,
            5: TftpPacketERR,
            6: TftpPacketOACK
            }

    def parse(self, buffer):
        """This method is used to parse an existing datagram into its
        corresponding TftpPacket object. The buffer is the raw bytes off of
        the network."""
        log.debug("parsing a %d byte packet" % len(buffer))
        (opcode,) = struct.unpack("!H", buffer[:2])
        log.debug("opcode is %d" % opcode)
        packet = self.__create(opcode)
        packet.buffer = buffer
        return packet.decode()

    def __create(self, opcode):
        """This method returns the appropriate class object corresponding to
        the passed opcode."""
        tftpassert(self.classes.has_key(opcode),
                   "Unsupported opcode: %d" % opcode)

        packet = self.classes[opcode]()

        return packet

########NEW FILE########
__FILENAME__ = TftpPacketTypes
"""This module implements the packet types of TFTP itself, and the
corresponding encode and decode methods for them."""

import struct
from TftpShared import *

class TftpSession(object):
    """This class is the base class for the tftp client and server. Any shared
    code should be in this class."""
    # FIXME: do we need this anymore?
    pass

class TftpPacketWithOptions(object):
    """This class exists to permit some TftpPacket subclasses to share code
    regarding options handling. It does not inherit from TftpPacket, as the
    goal is just to share code here, and not cause diamond inheritance."""

    def __init__(self):
        self.options = {}

    def setoptions(self, options):
        log.debug("in TftpPacketWithOptions.setoptions")
        log.debug("options: " + str(options))
        myoptions = {}
        for key in options:
            newkey = str(key)
            myoptions[newkey] = str(options[key])
            log.debug("populated myoptions with %s = %s"
                         % (newkey, myoptions[newkey]))

        log.debug("setting options hash to: " + str(myoptions))
        self._options = myoptions

    def getoptions(self):
        log.debug("in TftpPacketWithOptions.getoptions")
        return self._options

    # Set up getter and setter on options to ensure that they are the proper
    # type. They should always be strings, but we don't need to force the
    # client to necessarily enter strings if we can avoid it.
    options = property(getoptions, setoptions)

    def decode_options(self, buffer):
        """This method decodes the section of the buffer that contains an
        unknown number of options. It returns a dictionary of option names and
        values."""
        format = "!"
        options = {}

        log.debug("decode_options: buffer is: " + repr(buffer))
        log.debug("size of buffer is %d bytes" % len(buffer))
        if len(buffer) == 0:
            log.debug("size of buffer is zero, returning empty hash")
            return {}

        # Count the nulls in the buffer. Each one terminates a string.
        log.debug("about to iterate options buffer counting nulls")
        length = 0
        for c in buffer:
            #log.debug("iterating this byte: " + repr(c))
            if ord(c) == 0:
                log.debug("found a null at length %d" % length)
                if length > 0:
                    format += "%dsx" % length
                    length = -1
                else:
                    raise TftpException, "Invalid options in buffer"
            length += 1

        log.debug("about to unpack, format is: %s" % format)
        mystruct = struct.unpack(format, buffer)

        tftpassert(len(mystruct) % 2 == 0,
                   "packet with odd number of option/value pairs")

        for i in range(0, len(mystruct), 2):
            log.debug("setting option %s to %s" % (mystruct[i], mystruct[i+1]))
            options[mystruct[i]] = mystruct[i+1]

        return options

class TftpPacket(object):
    """This class is the parent class of all tftp packet classes. It is an
    abstract class, providing an interface, and should not be instantiated
    directly."""
    def __init__(self):
        self.opcode = 0
        self.buffer = None

    def encode(self):
        """The encode method of a TftpPacket takes keyword arguments specific
        to the type of packet, and packs an appropriate buffer in network-byte
        order suitable for sending over the wire.

        This is an abstract method."""
        raise NotImplementedError, "Abstract method"

    def decode(self):
        """The decode method of a TftpPacket takes a buffer off of the wire in
        network-byte order, and decodes it, populating internal properties as
        appropriate. This can only be done once the first 2-byte opcode has
        already been decoded, but the data section does include the entire
        datagram.

        This is an abstract method."""
        raise NotImplementedError, "Abstract method"

class TftpPacketInitial(TftpPacket, TftpPacketWithOptions):
    """This class is a common parent class for the RRQ and WRQ packets, as
    they share quite a bit of code."""
    def __init__(self):
        TftpPacket.__init__(self)
        TftpPacketWithOptions.__init__(self)
        self.filename = None
        self.mode = None

    def encode(self):
        """Encode the packet's buffer from the instance variables."""
        tftpassert(self.filename, "filename required in initial packet")
        tftpassert(self.mode, "mode required in initial packet")

        ptype = None
        if self.opcode == 1: ptype = "RRQ"
        else:                ptype = "WRQ"
        log.debug("Encoding %s packet, filename = %s, mode = %s"
                     % (ptype, self.filename, self.mode))
        for key in self.options:
            log.debug("    Option %s = %s" % (key, self.options[key]))

        format = "!H"
        format += "%dsx" % len(self.filename)
        if self.mode == "octet":
            format += "5sx"
        else:
            raise AssertionError, "Unsupported mode: %s" % mode
        # Add options.
        options_list = []
        if self.options.keys() > 0:
            log.debug("there are options to encode")
            for key in self.options:
                # Populate the option name
                format += "%dsx" % len(key)
                options_list.append(key)
                # Populate the option value
                format += "%dsx" % len(str(self.options[key]))
                options_list.append(str(self.options[key]))

        log.debug("format is %s" % format)
        log.debug("options_list is %s" % options_list)
        log.debug("size of struct is %d" % struct.calcsize(format))

        self.buffer = struct.pack(format,
                                  self.opcode,
                                  self.filename,
                                  self.mode,
                                  *options_list)

        log.debug("buffer is " + repr(self.buffer))
        return self

    def decode(self):
        tftpassert(self.buffer, "Can't decode, buffer is empty")

        # FIXME - this shares a lot of code with decode_options
        nulls = 0
        format = ""
        nulls = length = tlength = 0
        log.debug("in decode: about to iterate buffer counting nulls")
        subbuf = self.buffer[2:]
        for c in subbuf:
            log.debug("iterating this byte: " + repr(c))
            if ord(c) == 0:
                nulls += 1
                log.debug("found a null at length %d, now have %d"
                             % (length, nulls))
                format += "%dsx" % length
                length = -1
                # At 2 nulls, we want to mark that position for decoding.
                if nulls == 2:
                    break
            length += 1
            tlength += 1

        log.debug("hopefully found end of mode at length %d" % tlength)
        # length should now be the end of the mode.
        tftpassert(nulls == 2, "malformed packet")
        shortbuf = subbuf[:tlength+1]
        log.debug("about to unpack buffer with format: %s" % format)
        log.debug("unpacking buffer: " + repr(shortbuf))
        mystruct = struct.unpack(format, shortbuf)

        tftpassert(len(mystruct) == 2, "malformed packet")
        self.filename = mystruct[0]
        self.mode = mystruct[1].lower() # force lc - bug 17
        log.debug("set filename to %s" % self.filename)
        log.debug("set mode to %s" % self.mode)

        self.options = self.decode_options(subbuf[tlength+1:])
        return self

class TftpPacketRRQ(TftpPacketInitial):
    """
::

            2 bytes    string   1 byte     string   1 byte
            -----------------------------------------------
    RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
    WRQ     -----------------------------------------------
    """
    def __init__(self):
        TftpPacketInitial.__init__(self)
        self.opcode = 1

    def __str__(self):
        s = 'RRQ packet: filename = %s' % self.filename
        s += ' mode = %s' % self.mode
        if self.options:
            s += '\n    options = %s' % self.options
        return s

class TftpPacketWRQ(TftpPacketInitial):
    """
::

            2 bytes    string   1 byte     string   1 byte
            -----------------------------------------------
    RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
    WRQ     -----------------------------------------------
    """
    def __init__(self):
        TftpPacketInitial.__init__(self)
        self.opcode = 2

    def __str__(self):
        s = 'WRQ packet: filename = %s' % self.filename
        s += ' mode = %s' % self.mode
        if self.options:
            s += '\n    options = %s' % self.options
        return s

class TftpPacketDAT(TftpPacket):
    """
::

            2 bytes    2 bytes       n bytes
            ---------------------------------
    DATA  | 03    |   Block #  |    Data    |
            ---------------------------------
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 3
        self.blocknumber = 0
        self.data = None

    def __str__(self):
        s = 'DAT packet: block %s' % self.blocknumber
        if self.data:
            s += '\n    data: %d bytes' % len(self.data)
        return s

    def encode(self):
        """Encode the DAT packet. This method populates self.buffer, and
        returns self for easy method chaining."""
        if len(self.data) == 0:
            log.debug("Encoding an empty DAT packet")
        format = "!HH%ds" % len(self.data)
        self.buffer = struct.pack(format,
                                  self.opcode,
                                  self.blocknumber,
                                  self.data)
        return self

    def decode(self):
        """Decode self.buffer into instance variables. It returns self for
        easy method chaining."""
        # We know the first 2 bytes are the opcode. The second two are the
        # block number.
        (self.blocknumber,) = struct.unpack("!H", self.buffer[2:4])
        log.debug("decoding DAT packet, block number %d" % self.blocknumber)
        log.debug("should be %d bytes in the packet total"
                     % len(self.buffer))
        # Everything else is data.
        self.data = self.buffer[4:]
        log.debug("found %d bytes of data"
                     % len(self.data))
        return self

class TftpPacketACK(TftpPacket):
    """
::

            2 bytes    2 bytes
            -------------------
    ACK   | 04    |   Block #  |
            --------------------
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 4
        self.blocknumber = 0

    def __str__(self):
        return 'ACK packet: block %d' % self.blocknumber

    def encode(self):
        log.debug("encoding ACK: opcode = %d, block = %d"
                     % (self.opcode, self.blocknumber))
        self.buffer = struct.pack("!HH", self.opcode, self.blocknumber)
        return self

    def decode(self):
        self.opcode, self.blocknumber = struct.unpack("!HH", self.buffer)
        log.debug("decoded ACK packet: opcode = %d, block = %d"
                     % (self.opcode, self.blocknumber))
        return self

class TftpPacketERR(TftpPacket):
    """
::

            2 bytes  2 bytes        string    1 byte
            ----------------------------------------
    ERROR | 05    |  ErrorCode |   ErrMsg   |   0  |
            ----------------------------------------

    Error Codes

    Value     Meaning

    0         Not defined, see error message (if any).
    1         File not found.
    2         Access violation.
    3         Disk full or allocation exceeded.
    4         Illegal TFTP operation.
    5         Unknown transfer ID.
    6         File already exists.
    7         No such user.
    8         Failed to negotiate options
    """
    def __init__(self):
        TftpPacket.__init__(self)
        self.opcode = 5
        self.errorcode = 0
        # FIXME: We don't encode the errmsg...
        self.errmsg = None
        # FIXME - integrate in TftpErrors references?
        self.errmsgs = {
            1: "File not found",
            2: "Access violation",
            3: "Disk full or allocation exceeded",
            4: "Illegal TFTP operation",
            5: "Unknown transfer ID",
            6: "File already exists",
            7: "No such user",
            8: "Failed to negotiate options"
            }

    def __str__(self):
        s = 'ERR packet: errorcode = %d' % self.errorcode
        s += '\n    msg = %s' % self.errmsgs.get(self.errorcode, '')
        return s

    def encode(self):
        """Encode the DAT packet based on instance variables, populating
        self.buffer, returning self."""
        format = "!HH%dsx" % len(self.errmsgs[self.errorcode])
        log.debug("encoding ERR packet with format %s" % format)
        self.buffer = struct.pack(format,
                                  self.opcode,
                                  self.errorcode,
                                  self.errmsgs[self.errorcode])
        return self

    def decode(self):
        "Decode self.buffer, populating instance variables and return self."
        buflen = len(self.buffer)
        tftpassert(buflen >= 4, "malformed ERR packet, too short")
        log.debug("Decoding ERR packet, length %s bytes" % buflen)
        if buflen == 4:
            log.debug("Allowing this affront to the RFC of a 4-byte packet")
            format = "!HH"
            log.debug("Decoding ERR packet with format: %s" % format)
            self.opcode, self.errorcode = struct.unpack(format,
                                                        self.buffer)
        else:
            log.debug("Good ERR packet > 4 bytes")
            format = "!HH%dsx" % (len(self.buffer) - 5)
            log.debug("Decoding ERR packet with format: %s" % format)
            self.opcode, self.errorcode, self.errmsg = struct.unpack(format,
                                                                     self.buffer)
        log.error("ERR packet - errorcode: %d, message: %s"
                     % (self.errorcode, self.errmsg))
        return self

class TftpPacketOACK(TftpPacket, TftpPacketWithOptions):
    """
::

    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    |  opc  |  opt1  | 0 | value1 | 0 |  optN  | 0 | valueN | 0 |
    +-------+---~~---+---+---~~---+---+---~~---+---+---~~---+---+
    """
    def __init__(self):
        TftpPacket.__init__(self)
        TftpPacketWithOptions.__init__(self)
        self.opcode = 6

    def __str__(self):
        return 'OACK packet:\n    options = %s' % self.options

    def encode(self):
        format = "!H" # opcode
        options_list = []
        log.debug("in TftpPacketOACK.encode")
        for key in self.options:
            log.debug("looping on option key %s" % key)
            log.debug("value is %s" % self.options[key])
            format += "%dsx" % len(key)
            format += "%dsx" % len(self.options[key])
            options_list.append(key)
            options_list.append(self.options[key])
        self.buffer = struct.pack(format, self.opcode, *options_list)
        return self

    def decode(self):
        self.options = self.decode_options(self.buffer[2:])
        return self

    def match_options(self, options):
        """This method takes a set of options, and tries to match them with
        its own. It can accept some changes in those options from the server as
        part of a negotiation. Changed or unchanged, it will return a dict of
        the options so that the session can update itself to the negotiated
        options."""
        for name in self.options:
            if options.has_key(name):
                if name == 'blksize':
                    # We can accept anything between the min and max values.
                    size = self.options[name]
                    if size >= MIN_BLKSIZE and size <= MAX_BLKSIZE:
                        log.debug("negotiated blksize of %d bytes" % size)
                        options[blksize] = size
                else:
                    raise TftpException, "Unsupported option: %s" % name
        return True

########NEW FILE########
__FILENAME__ = TftpServer
"""This module implements the TFTP Server functionality. Instantiate an
instance of the server, and then run the listen() method to listen for client
requests. Logging is performed via a standard logging object set in
TftpShared."""

import socket, os, time
import select
from TftpShared import *
from TftpPacketTypes import *
from TftpPacketFactory import TftpPacketFactory
from TftpContexts import TftpContextServer

class TftpServer(TftpSession):
    """This class implements a tftp server object. Run the listen() method to
    listen for client requests.  It takes two optional arguments. tftproot is
    the path to the tftproot directory to serve files from and/or write them
    to. dyn_file_func is a callable that must return a file-like object to
    read from during downloads. This permits the serving of dynamic
    content."""

    def __init__(self, tftproot='/tftpboot', dyn_file_func=None):
        self.listenip = None
        self.listenport = None
        self.sock = None
        # FIXME: What about multiple roots?
        self.root = os.path.abspath(tftproot)
        self.dyn_file_func = dyn_file_func
        # A dict of sessions, where each session is keyed by a string like
        # ip:tid for the remote end.
        self.sessions = {}

        if os.path.exists(self.root):
            log.debug("tftproot %s does exist" % self.root)
            if not os.path.isdir(self.root):
                raise TftpException, "The tftproot must be a directory."
            else:
                log.debug("tftproot %s is a directory" % self.root)
                if os.access(self.root, os.R_OK):
                    log.debug("tftproot %s is readable" % self.root)
                else:
                    raise TftpException, "The tftproot must be readable"
                if os.access(self.root, os.W_OK):
                    log.debug("tftproot %s is writable" % self.root)
                else:
                    log.warning("The tftproot %s is not writable" % self.root)
        else:
            raise TftpException, "The tftproot does not exist."

    def listen(self,
               listenip="",
               listenport=DEF_TFTP_PORT,
               timeout=SOCK_TIMEOUT):
        """Start a server listening on the supplied interface and port. This
        defaults to INADDR_ANY (all interfaces) and UDP port 69. You can also
        supply a different socket timeout value, if desired."""
        tftp_factory = TftpPacketFactory()

        # Don't use new 2.5 ternary operator yet
        # listenip = listenip if listenip else '0.0.0.0'
        if not listenip: listenip = '0.0.0.0'
        log.info("Server requested on ip %s, port %s"
                % (listenip, listenport))
        try:
            # FIXME - sockets should be non-blocking
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((listenip, listenport))
        except socket.error, err:
            # Reraise it for now.
            raise

        log.info("Starting receive loop...")
        while True:
            # Build the inputlist array of sockets to select() on.
            inputlist = []
            inputlist.append(self.sock)
            for key in self.sessions:
                inputlist.append(self.sessions[key].sock)

            # Block until some socket has input on it.
            log.debug("Performing select on this inputlist: %s" % inputlist)
            readyinput, readyoutput, readyspecial = select.select(inputlist,
                                                                  [],
                                                                  [],
                                                                  SOCK_TIMEOUT)

            deletion_list = []

            # Handle the available data, if any. Maybe we timed-out.
            for readysock in readyinput:
                # Is the traffic on the main server socket? ie. new session?
                if readysock == self.sock:
                    log.debug("Data ready on our main socket")
                    buffer, (raddress, rport) = self.sock.recvfrom(MAX_BLKSIZE)

                    log.debug("Read %d bytes" % len(buffer))

                    # Forge a session key based on the client's IP and port,
                    # which should safely work through NAT.
                    key = "%s:%s" % (raddress, rport)

                    if not self.sessions.has_key(key):
                        log.debug("Creating new server context for "
                                     "session key = %s" % key)
                        self.sessions[key] = TftpContextServer(raddress,
                                                               rport,
                                                               timeout,
                                                               self.root,
                                                               self.dyn_file_func)
                        try:
                            self.sessions[key].start(buffer)
                        except TftpException, err:
                            deletion_list.append(key)
                            log.error("Fatal exception thrown from "
                                      "session %s: %s" % (key, str(err)))
                    else:
                        log.warn("received traffic on main socket for "
                                 "existing session??")
                    log.info("Currently handling these sessions:")
                    for session_key, session in self.sessions.items():
                        log.info("    %s" % session)

                else:
                    # Must find the owner of this traffic.
                    for key in self.sessions:
                        if readysock == self.sessions[key].sock:
                            log.info("Matched input to session key %s"
                                % key)
                            try:
                                self.sessions[key].cycle()
                                if self.sessions[key].state == None:
                                    log.info("Successful transfer.")
                                    deletion_list.append(key)
                            except TftpException, err:
                                deletion_list.append(key)
                                log.error("Fatal exception thrown from "
                                          "session %s: %s"
                                          % (key, str(err)))
                            # Break out of for loop since we found the correct
                            # session.
                            break

                    else:
                        log.error("Can't find the owner for this packet. "
                                  "Discarding.")

            log.debug("Looping on all sessions to check for timeouts")
            now = time.time()
            for key in self.sessions:
                try:
                    self.sessions[key].checkTimeout(now)
                except TftpTimeout, err:
                    log.error(str(err))
                    self.sessions[key].retry_count += 1
                    if self.sessions[key].retry_count >= TIMEOUT_RETRIES:
                        log.debug("hit max retries on %s, giving up"
                            % self.sessions[key])
                        deletion_list.append(key)
                    else:
                        log.debug("resending on session %s"
                            % self.sessions[key])
                        self.sessions[key].state.resendLast()

            log.debug("Iterating deletion list.")
            for key in deletion_list:
                log.info('')
                log.info("Session %s complete" % key)
                if self.sessions.has_key(key):
                    log.debug("Gathering up metrics from session before deleting")
                    self.sessions[key].end()
                    metrics = self.sessions[key].metrics
                    if metrics.duration == 0:
                        log.info("Duration too short, rate undetermined")
                    else:
                        log.info("Transferred %d bytes in %.2f seconds"
                            % (metrics.bytes, metrics.duration))
                        log.info("Average rate: %.2f kbps" % metrics.kbps)
                    log.info("%.2f bytes in resent data" % metrics.resent_bytes)
                    log.info("%d duplicate packets" % metrics.dupcount)
                    log.debug("Deleting session %s" % key)
                    del self.sessions[key]
                    log.debug("Session list is now %s" % self.sessions)
                else:
                    log.warn("Strange, session %s is not on the deletion list"
                        % key)

########NEW FILE########
__FILENAME__ = TftpShared
"""This module holds all objects shared by all other modules in tftpy."""

import logging

LOG_LEVEL = logging.NOTSET
MIN_BLKSIZE = 8
DEF_BLKSIZE = 512
MAX_BLKSIZE = 65536
SOCK_TIMEOUT = 5
MAX_DUPS = 20
TIMEOUT_RETRIES = 5
DEF_TFTP_PORT = 69

# A hook for deliberately introducing delay in testing.
DELAY_BLOCK = 0

# Initialize the logger.
logging.basicConfig()
# The logger used by this library. Feel free to clobber it with your own, if you like, as
# long as it conforms to Python's logging.
log = logging.getLogger('tftpy')

def tftpassert(condition, msg):
    """This function is a simple utility that will check the condition
    passed for a false state. If it finds one, it throws a TftpException
    with the message passed. This just makes the code throughout cleaner
    by refactoring."""
    if not condition:
        raise TftpException, msg

def setLogLevel(level):
    """This function is a utility function for setting the internal log level.
    The log level defaults to logging.NOTSET, so unwanted output to stdout is
    not created."""
    global log
    log.setLevel(level)

class TftpErrors(object):
    """This class is a convenience for defining the common tftp error codes,
    and making them more readable in the code."""
    NotDefined = 0
    FileNotFound = 1
    AccessViolation = 2
    DiskFull = 3
    IllegalTftpOp = 4
    UnknownTID = 5
    FileAlreadyExists = 6
    NoSuchUser = 7
    FailedNegotiation = 8

class TftpException(Exception):
    """This class is the parent class of all exceptions regarding the handling
    of the TFTP protocol."""
    pass

class TftpTimeout(TftpException):
    """This class represents a timeout error waiting for a response from the
    other end."""
    pass

########NEW FILE########
__FILENAME__ = TftpStates
"""This module implements all state handling during uploads and downloads, the
main interface to which being the TftpState base class. 

The concept is simple. Each context object represents a single upload or
download, and the state object in the context object represents the current
state of that transfer. The state object has a handle() method that expects
the next packet in the transfer, and returns a state object until the transfer
is complete, at which point it returns None. That is, unless there is a fatal
error, in which case a TftpException is returned instead."""

from TftpShared import *
from TftpPacketTypes import *
import os

###############################################################################
# State classes
###############################################################################

class TftpState(object):
    """The base class for the states."""

    def __init__(self, context):
        """Constructor for setting up common instance variables. The involved
        file object is required, since in tftp there's always a file
        involved."""
        self.context = context

    def handle(self, pkt, raddress, rport):
        """An abstract method for handling a packet. It is expected to return
        a TftpState object, either itself or a new state."""
        raise NotImplementedError, "Abstract method"

    def handleOACK(self, pkt):
        """This method handles an OACK from the server, syncing any accepted
        options."""
        if pkt.options.keys() > 0:
            if pkt.match_options(self.context.options):
                log.info("Successful negotiation of options")
                # Set options to OACK options
                self.context.options = pkt.options
                for key in self.context.options:
                    log.info("    %s = %s" % (key, self.context.options[key]))
            else:
                log.error("Failed to negotiate options")
                raise TftpException, "Failed to negotiate options"
        else:
            raise TftpException, "No options found in OACK"

    def returnSupportedOptions(self, options):
        """This method takes a requested options list from a client, and
        returns the ones that are supported."""
        # We support the options blksize and tsize right now.
        # FIXME - put this somewhere else?
        accepted_options = {}
        for option in options:
            if option == 'blksize':
                # Make sure it's valid.
                if int(options[option]) > MAX_BLKSIZE:
                    log.info("Client requested blksize greater than %d "
                             "setting to maximum" % MAX_BLKSIZE)
                    accepted_options[option] = MAX_BLKSIZE
                elif int(options[option]) < MIN_BLKSIZE:
                    log.info("Client requested blksize less than %d "
                             "setting to minimum" % MIN_BLKSIZE)
                    accepted_options[option] = MIN_BLKSIZE
                else:
                    accepted_options[option] = options[option]
            elif option == 'tsize':
                log.debug("tsize option is set")
                accepted_options['tsize'] = 1
            else:
                log.info("Dropping unsupported option '%s'" % option)
        log.debug("Returning these accepted options: %s" % accepted_options)
        return accepted_options

    def serverInitial(self, pkt, raddress, rport):
        """This method performs initial setup for a server context transfer,
        put here to refactor code out of the TftpStateServerRecvRRQ and
        TftpStateServerRecvWRQ classes, since their initial setup is
        identical. The method returns a boolean, sendoack, to indicate whether
        it is required to send an OACK to the client."""
        options = pkt.options
        sendoack = False
        if not self.context.tidport:
            self.context.tidport = rport
            log.info("Setting tidport to %s" % rport)

        log.debug("Setting default options, blksize")
        self.context.options = { 'blksize': DEF_BLKSIZE }

        if options:
            log.debug("Options requested: %s" % options)
            supported_options = self.returnSupportedOptions(options)
            self.context.options.update(supported_options)
            sendoack = True

        # FIXME - only octet mode is supported at this time.
        if pkt.mode != 'octet':
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, \
                "Only octet transfers are supported at this time."

        # test host/port of client end
        if self.context.host != raddress or self.context.port != rport:
            self.sendError(TftpErrors.UnknownTID)
            log.error("Expected traffic from %s:%s but received it "
                            "from %s:%s instead."
                            % (self.context.host,
                               self.context.port,
                               raddress,
                               rport))
            # FIXME: increment an error count?
            # Return same state, we're still waiting for valid traffic.
            return self

        log.debug("Requested filename is %s" % pkt.filename)
        # There are no os.sep's allowed in the filename.
        # FIXME: Should we allow subdirectories?
        if pkt.filename.find(os.sep) >= 0:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "%s found in filename, not permitted" % os.sep

        self.context.file_to_transfer = pkt.filename

        return sendoack

    def sendDAT(self):
        """This method sends the next DAT packet based on the data in the
        context. It returns a boolean indicating whether the transfer is
        finished."""
        finished = False
        blocknumber = self.context.next_block
        # Test hook
        if DELAY_BLOCK and DELAY_BLOCK == blocknumber:
            import time
            log.debug("Deliberately delaying 10 seconds...")
            time.sleep(10)
        tftpassert( blocknumber > 0, "There is no block zero!" )
        dat = None
        blksize = self.context.getBlocksize()
        buffer = self.context.fileobj.read(blksize)
        log.debug("Read %d bytes into buffer" % len(buffer))
        if len(buffer) < blksize:
            log.info("Reached EOF on file %s"
                % self.context.file_to_transfer)
            finished = True
        dat = TftpPacketDAT()
        dat.data = buffer
        dat.blocknumber = blocknumber
        self.context.metrics.bytes += len(dat.data)
        log.debug("Sending DAT packet %d" % dat.blocknumber)
        self.context.sock.sendto(dat.encode().buffer,
                                 (self.context.host, self.context.tidport))
        if self.context.packethook:
            self.context.packethook(dat)
        self.context.last_pkt = dat
        return finished

    def sendACK(self, blocknumber=None):
        """This method sends an ack packet to the block number specified. If
        none is specified, it defaults to the next_block property in the
        parent context."""
        log.debug("In sendACK, passed blocknumber is %s" % blocknumber)
        if blocknumber is None:
            blocknumber = self.context.next_block
        log.info("Sending ack to block %d" % blocknumber)
        ackpkt = TftpPacketACK()
        ackpkt.blocknumber = blocknumber
        self.context.sock.sendto(ackpkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = ackpkt

    def sendError(self, errorcode):
        """This method uses the socket passed, and uses the errorcode to
        compose and send an error packet."""
        log.debug("In sendError, being asked to send error %d" % errorcode)
        errpkt = TftpPacketERR()
        errpkt.errorcode = errorcode
        self.context.sock.sendto(errpkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = errpkt

    def sendOACK(self):
        """This method sends an OACK packet with the options from the current
        context."""
        log.debug("In sendOACK with options %s" % self.context.options)
        pkt = TftpPacketOACK()
        pkt.options = self.context.options
        self.context.sock.sendto(pkt.encode().buffer,
                                 (self.context.host,
                                  self.context.tidport))
        self.context.last_pkt = pkt

    def resendLast(self):
        "Resend the last sent packet due to a timeout."
        log.warn("Resending packet %s on sessions %s"
            % (self.context.last_pkt, self))
        self.context.metrics.resent_bytes += len(self.context.last_pkt.buffer)
        self.context.metrics.add_dup(self.context.last_pkt)
        self.context.sock.sendto(self.context.last_pkt.encode().buffer,
                                 (self.context.host, self.context.tidport))
        if self.context.packethook:
            self.context.packethook(self.context.last_pkt)

    def handleDat(self, pkt):
        """This method handles a DAT packet during a client download, or a
        server upload."""
        log.info("Handling DAT packet - block %d" % pkt.blocknumber)
        log.debug("Expecting block %s" % self.context.next_block)
        if pkt.blocknumber == self.context.next_block:
            log.debug("Good, received block %d in sequence"
                        % pkt.blocknumber)

            self.sendACK()
            self.context.next_block += 1

            log.debug("Writing %d bytes to output file"
                        % len(pkt.data))
            self.context.fileobj.write(pkt.data)
            self.context.metrics.bytes += len(pkt.data)
            # Check for end-of-file, any less than full data packet.
            if len(pkt.data) < self.context.getBlocksize():
                log.info("End of file detected")
                return None

        elif pkt.blocknumber < self.context.next_block:
            if pkt.blocknumber == 0:
                log.warn("There is no block zero!")
                self.sendError(TftpErrors.IllegalTftpOp)
                raise TftpException, "There is no block zero!"
            log.warn("Dropping duplicate block %d" % pkt.blocknumber)
            self.context.metrics.add_dup(pkt)
            log.debug("ACKing block %d again, just in case" % pkt.blocknumber)
            self.sendACK(pkt.blocknumber)

        else:
            # FIXME: should we be more tolerant and just discard instead?
            msg = "Whoa! Received future block %d but expected %d" \
                % (pkt.blocknumber, self.context.next_block)
            log.error(msg)
            raise TftpException, msg

        # Default is to ack
        return TftpStateExpectDAT(self.context)

class TftpStateServerRecvRRQ(TftpState):
    """This class represents the state of the TFTP server when it has just
    received an RRQ packet."""
    def handle(self, pkt, raddress, rport):
        "Handle an initial RRQ packet as a server."
        log.debug("In TftpStateServerRecvRRQ.handle")
        sendoack = self.serverInitial(pkt, raddress, rport)
        path = self.context.root + os.sep + self.context.file_to_transfer
        log.info("Opening file %s for reading" % path)
        if os.path.exists(path):
            # Note: Open in binary mode for win32 portability, since win32
            # blows.
            self.context.fileobj = open(path, "rb")
        elif self.context.dyn_file_func:
            log.debug("No such file %s but using dyn_file_func" % path)
            self.context.fileobj = \
                self.context.dyn_file_func(self.context.file_to_transfer)

            if self.context.fileobj is None:
                log.debug("dyn_file_func returned 'None', treating as "
                          "FileNotFound")
                self.sendError(TftpErrors.FileNotFound)
                raise TftpException, "File not found: %s" % path
        else:
            self.sendError(TftpErrors.FileNotFound)
            raise TftpException, "File not found: %s" % path

        # Options negotiation.
        if sendoack:
            # Note, next_block is 0 here since that's the proper
            # acknowledgement to an OACK.
            # FIXME: perhaps we do need a TftpStateExpectOACK class...
            self.sendOACK()
            # Note, self.context.next_block is already 0.
        else:
            self.context.next_block = 1
            log.debug("No requested options, starting send...")
            self.context.pending_complete = self.sendDAT()
        # Note, we expect an ack regardless of whether we sent a DAT or an
        # OACK.
        return TftpStateExpectACK(self.context)

        # Note, we don't have to check any other states in this method, that's
        # up to the caller.

class TftpStateServerRecvWRQ(TftpState):
    """This class represents the state of the TFTP server when it has just
    received a WRQ packet."""
    def handle(self, pkt, raddress, rport):
        "Handle an initial WRQ packet as a server."
        log.debug("In TftpStateServerRecvWRQ.handle")
        sendoack = self.serverInitial(pkt, raddress, rport)
        path = self.context.root + os.sep + self.context.file_to_transfer
        log.info("Opening file %s for writing" % path)
        if os.path.exists(path):
            # FIXME: correct behavior?
            log.warn("File %s exists already, overwriting..." % self.context.file_to_transfer)
        # FIXME: I think we should upload to a temp file and not overwrite the
        # existing file until the file is successfully uploaded.
        self.context.fileobj = open(path, "wb")

        # Options negotiation.
        if sendoack:
            log.debug("Sending OACK to client")
            self.sendOACK()
        else:
            log.debug("No requested options, expecting transfer to begin...")
            self.sendACK()
        # Whether we're sending an oack or not, we're expecting a DAT for
        # block 1
        self.context.next_block = 1
        # We may have sent an OACK, but we're expecting a DAT as the response
        # to either the OACK or an ACK, so lets unconditionally use the
        # TftpStateExpectDAT state.
        return TftpStateExpectDAT(self.context)

        # Note, we don't have to check any other states in this method, that's
        # up to the caller.

class TftpStateServerStart(TftpState):
    """The start state for the server. This is a transitory state since at
    this point we don't know if we're handling an upload or a download. We
    will commit to one of them once we interpret the initial packet."""
    def handle(self, pkt, raddress, rport):
        """Handle a packet we just received."""
        log.debug("In TftpStateServerStart.handle")
        if isinstance(pkt, TftpPacketRRQ):
            log.debug("Handling an RRQ packet")
            return TftpStateServerRecvRRQ(self.context).handle(pkt,
                                                               raddress,
                                                               rport)
        elif isinstance(pkt, TftpPacketWRQ):
            log.debug("Handling a WRQ packet")
            return TftpStateServerRecvWRQ(self.context).handle(pkt,
                                                               raddress,
                                                               rport)
        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, \
                "Invalid packet to begin up/download: %s" % pkt

class TftpStateExpectACK(TftpState):
    """This class represents the state of the transfer when a DAT was just
    sent, and we are waiting for an ACK from the server. This class is the
    same one used by the client during the upload, and the server during the
    download."""
    def handle(self, pkt, raddress, rport):
        "Handle a packet, hopefully an ACK since we just sent a DAT."
        if isinstance(pkt, TftpPacketACK):
            log.info("Received ACK for packet %d" % pkt.blocknumber)
            # Is this an ack to the one we just sent?
            if self.context.next_block == pkt.blocknumber:
                if self.context.pending_complete:
                    log.info("Received ACK to final DAT, we're done.")
                    return None
                else:
                    log.debug("Good ACK, sending next DAT")
                    self.context.next_block += 1
                    log.debug("Incremented next_block to %d"
                        % (self.context.next_block))
                    self.context.pending_complete = self.sendDAT()

            elif pkt.blocknumber < self.context.next_block:
                log.debug("Received duplicate ACK for block %d"
                    % pkt.blocknumber)
                self.context.metrics.add_dup(pkt)

            else:
                log.warn("Oooh, time warp. Received ACK to packet we "
                         "didn't send yet. Discarding.")
                self.context.metrics.errors += 1
            return self
        elif isinstance(pkt, TftpPacketERR):
            log.error("Received ERR packet from peer: %s" % str(pkt))
            raise TftpException, \
                "Received ERR packet from peer: %s" % str(pkt)
        else:
            log.warn("Discarding unsupported packet: %s" % str(pkt))
            return self

class TftpStateExpectDAT(TftpState):
    """Just sent an ACK packet. Waiting for DAT."""
    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an ACK, which should be a DAT."""
        if isinstance(pkt, TftpPacketDAT):
            return self.handleDat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, TftpPacketACK):
            # Umm, we ACK, you don't.
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ACK from peer when expecting DAT"

        elif isinstance(pkt, TftpPacketWRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received WRQ from peer when expecting DAT"

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from peer: " + str(pkt)

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from peer: " + str(pkt)

class TftpStateSentWRQ(TftpState):
    """Just sent an WRQ packet for an upload."""
    def handle(self, pkt, raddress, rport):
        """Handle a packet we just received."""
        if not self.context.tidport:
            self.context.tidport = rport
            log.debug("Set remote port for session to %s" % rport)

        # If we're going to successfully transfer the file, then we should see
        # either an OACK for accepted options, or an ACK to ignore options.
        if isinstance(pkt, TftpPacketOACK):
            log.info("Received OACK from server")
            try:
                self.handleOACK(pkt)
            except TftpException:
                log.error("Failed to negotiate options")
                self.sendError(TftpErrors.FailedNegotiation)
                raise
            else:
                log.debug("Sending first DAT packet")
                self.context.pending_complete = self.sendDAT()
                log.debug("Changing state to TftpStateExpectACK")
                return TftpStateExpectACK(self.context)

        elif isinstance(pkt, TftpPacketACK):
            log.info("Received ACK from server")
            log.debug("Apparently the server ignored our options")
            # The block number should be zero.
            if pkt.blocknumber == 0:
                log.debug("Ack blocknumber is zero as expected")
                log.debug("Sending first DAT packet")
                self.context.pending_complete = self.sendDAT()
                log.debug("Changing state to TftpStateExpectACK")
                return TftpStateExpectACK(self.context)
            else:
                log.warn("Discarding ACK to block %s" % pkt.blocknumber)
                log.debug("Still waiting for valid response from server")
                return self

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from server: " + str(pkt)

        elif isinstance(pkt, TftpPacketRRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received RRQ from server while in upload"

        elif isinstance(pkt, TftpPacketDAT):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received DAT from server while in upload"

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from server: " + str(pkt)

        # By default, no state change.
        return self

class TftpStateSentRRQ(TftpState):
    """Just sent an RRQ packet."""
    def handle(self, pkt, raddress, rport):
        """Handle the packet in response to an RRQ to the server."""
        if not self.context.tidport:
            self.context.tidport = rport
            log.info("Set remote port for session to %s" % rport)

        # Now check the packet type and dispatch it properly.
        if isinstance(pkt, TftpPacketOACK):
            log.info("Received OACK from server")
            try:
                self.handleOACK(pkt)
            except TftpException, err:
                log.error("Failed to negotiate options: %s" % str(err))
                self.sendError(TftpErrors.FailedNegotiation)
                raise
            else:
                log.debug("Sending ACK to OACK")

                self.sendACK(blocknumber=0)

                log.debug("Changing state to TftpStateExpectDAT")
                return TftpStateExpectDAT(self.context)

        elif isinstance(pkt, TftpPacketDAT):
            # If there are any options set, then the server didn't honour any
            # of them.
            log.info("Received DAT from server")
            if self.context.options:
                log.info("Server ignored options, falling back to defaults")
                self.context.options = { 'blksize': DEF_BLKSIZE }
            return self.handleDat(pkt)

        # Every other packet type is a problem.
        elif isinstance(pkt, TftpPacketACK):
            # Umm, we ACK, the server doesn't.
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ACK from server while in download"

        elif isinstance(pkt, TftpPacketWRQ):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received WRQ from server while in download"

        elif isinstance(pkt, TftpPacketERR):
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received ERR from server: " + str(pkt)

        else:
            self.sendError(TftpErrors.IllegalTftpOp)
            raise TftpException, "Received unknown packet type from server: " + str(pkt)

        # By default, no state change.
        return self

########NEW FILE########
__FILENAME__ = rancid
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parse RANCID db files so they can be converted into Trigger NetDevice objects.

.. versionadded:: 1.2

Far from complete. Very early in development. Here is a basic example.

    >>> from trigger import rancid
    >>> rancid_root = '/path/to/rancid/data'
    >>> r = Rancid(rancid_root)
    >>> dev = r.devices.get('test1-abc.net.aol.com')
    >>> dev
    RancidDevice(nodeName='test-abc.net.aol.com', manufacturer='juniper', deviceStatus='up', deviceType=None)

Another option if you want to get the parsed RANCID data directly without
having to create an object is as simple as this::

    >>> parsed = rancid.parse_rancid_data('/path/to/dancid/data')

Or using multiple RANCID instances within a single root::

    >>> multi_parsed = rancid.parse_rancid_data('/path/to/rancid/data', recurse_subdirs=True)

"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.; 2013 Salesforce.com'
__version__ = '0.1.1'

import collections
import copy
import csv
import datetime
import itertools
import os
import sys

__all__ = ('parse_rancid_file', 'parse_devices', 'walk_rancid_subdirs',
           'parse_rancid_data', 'gather_devices', 'Rancid', 'RancidDevice')

# Constants
CONFIG_DIRNAME = 'configs'
RANCID_DB_FILE = 'router.db'
RANCID_ALL_FILE = 'routers.all'
RANCID_DOWN_FILE = 'routers.down'
RANCID_UP_FILE = 'routers.up'
NETDEVICE_FIELDS = ['nodeName', 'manufacturer', 'deviceStatus', 'deviceType']


# Functions
def _parse_delimited_file(root_dir, filename, delimiter=':'):
    """
    Parse a colon-delimited file and return the contents as a list of lists.

    Intended to be used for parsing of all RANCID files.

    :param root_dir:
        Where to find the file

    :param filename:
        Name of the file to parse

    :param delimiter:
        (Optional) Field delimiter
    """
    filepath = os.path.join(root_dir, filename)
    with open(filepath, 'r') as f:
        reader = csv.reader(f, delimiter=delimiter)
        return [r for r in reader if len(r) > 1] # Skip unparsed lines

    return None

def parse_rancid_file(rancid_root, filename=RANCID_DB_FILE, fields=None,
                      delimiter=':'):
    """
    Parse a RANCID file and return generator representing a list of lists
    mapped  to the ``fields``.

    :param rancid_root:
        Where to find the file

    :param filename:
        Name of the file to parse (e.g. ``router.db``)

    :param fields:
        (Optional) A list of field names used to map to the device data

    :param delimiter:
        (Optional) Field delimiter
    """
    device_data = _parse_delimited_file(rancid_root, filename, delimiter)
    if not device_data:
        return None # Always return None if there are no results

    # Make sure fields is not null and is some kind of iterable
    if not fields:
        fields = NETDEVICE_FIELDS
    else:
        if not isinstance(fields, collections.Iterable):
            raise RuntimeError('`fields` must be iterable')

    # Map fields to generator of generators (!!)
    metadata = (itertools.izip_longest(fields, vals) for vals in device_data)

    return metadata

def walk_rancid_subdirs(rancid_root, config_dirname=CONFIG_DIRNAME,
                        fields=None):
    """
    Walk the ``rancid_root`` and parse the included RANCID files.

    Returns a dictionary keyed by the name of the subdirs with values set to
    the parsed data for each RANCID file found inside.

        >>> from trigger import rancid
        >>> subdirs = rancid.walk_rancid_subdirs('/data/rancid')
        >>> subdirs.get('network-security')
        {'router.db': <generator object <genexpr> at 0xa5b852c>,
         'routers.all': <generator object <genexpr> at 0xa5a348c>,
         'routers.down': <generator object <genexpr> at 0xa5be9dc>,
         'routers.up': <generator object <genexpr> at 0xa5bea54>}

    :param rancid_root:
        Where to find the file

    :param config_dirname:
        If the 'configs' dir is named something else

    :param fields:
        (Optional) A list of field names used to map to the device data
    """
    walker = os.walk(rancid_root)
    baseroot, basedirs, basefiles = walker.next() # First item is base

    results = {}
    for root, dirnames, filenames in walker:
        # Skip any path with CVS in it
        if 'CVS' in root:
            #print 'skipping CVS:', root
            continue

        # Don't visit CVS directories
        if 'CVS' in dirnames:
            dirnames.remove('CVS')

        # Skip directories with nothing in them
        if not filenames or not dirnames:
            continue

        # Only walk directories in which we also have configs
        if config_dirname in dirnames:
            owner = os.path.basename(root)
            results[owner] = {}
            for file_ in filenames:
                results[owner][file_] = parse_rancid_file(root, file_, fields)

    return results

def parse_rancid_data(rancid_root, filename=RANCID_DB_FILE, fields=None,
                      config_dirname=CONFIG_DIRNAME, recurse_subdirs=False):
    """
    Parse single or multiple RANCID instances and return an iterator of the
    device metadata.

    A single instance expects to find 'router.db' in ``rancid_root``.

    If you set ``recurise_subdirs``, multiple instances will be expected, and a
    `router.db` will be expected to be found in each subdirectory.

    :param rancid_root:
        Where to find the file

    :param filename:
        Name of the file to parse (e.g. ``router.db``)

    :param fields:
        (Optional) A list of field names used to map to the device data

    :param config_dirname:
        If the 'configs' dir is named something else

    :param recurse_subdirs:
        Whether to recurse directories (e.g. multiple instances)
    """
    if recurse_subdirs:
        subdirs = walk_rancid_subdirs(rancid_root, config_dirname, fields)
        metadata = gather_devices(subdirs, filename)
    else:
        metadata = parse_rancid_file(rancid_root, filename, fields)

    return metadata

def parse_devices(metadata, parser):
    """
    Iterate device ``metadata`` to use ``parser`` to create and return a
    list of network device objects.

    :param metadata:
        A collection of key/value pairs (Generally returned from
        `~trigger.rancid.parse_rancid_file`)

    :param parser:
        A callabale used to create your objects
    """

    # Two tees of `metadata` iterator, in case a TypeError is encountered, we
    # aren't losing the first item.
    md_original, md_backup = itertools.tee(metadata)
    try:
        # Try to parse using the generator (most efficient)
        return [parser(d) for d in md_original]
    except TypeError:
        # Try to parse by unpacking a dict into kwargs
        return [parser(**dict(d)) for d in md_backup]
    except Exception as err:
        # Or just give up
        print "Parser failed with this error: %r" % repr(err)
        return None
    else:
        raise RuntimeError('This should never happen!')

def gather_devices(subdir_data, rancid_db_file=RANCID_DB_FILE):
    """
    Returns a chained iterator of parsed RANCID data, based from the results of
    `~trigger.rancid.walk_rancid_subdirs`.

    This iterator is suitable for consumption by
    `~trigger.rancid.parse_devices` or Trigger's
    `~trigger.netdevices.NetDevices`.

    :param rancid_root:
        Where to find your RANCID files (router.db, et al.)

    :param rancid_db_file:
        If it's named other than ``router.db``
    """
    iters = []
    for rdir, files in subdir_data.iteritems():
        # Only carry on if we find 'router.db' or it's equivalent
        metadata = files.get(rancid_db_file)
        if metadata is None:
            continue

        iters.append(metadata)

    return itertools.chain(*iters)

def _parse_config_file(rancid_root, filename, parser=None,
                       config_dirname=CONFIG_DIRNAME, max_lines=30):
    """Parse device config file for metadata (make, model, etc.)"""
    filepath = os.path.join(rancid_root, config_dirname, filename)
    try:
        with open(filepath, 'r') as f:
            config = []
            for idx, line in enumerate(f):
                if idx >= max_lines:
                    break
    
                if any([line.startswith('#'), line.startswith('!') and len(line) > 2]):
                    config.append(line.strip())

            return config

    except IOError:
        return None

def _parse_config_files(devices, rancid_root, config_dirname=CONFIG_DIRNAME):
    '''Parse multiple device config files'''
    return_data = {}
    for dev in devices:
        return_data[dev.nodeName] = _parse_config_file(rancid_root,
                                                       dev.nodeName,
                                                       config_dirname)
    return return_data

def _parse_cisco(config):
    """NYI - Parse Cisco config to get metadata"""

def _parse_juniper(config):
    """NYI - Parse Juniper config to get metadata"""

def _parse_netscreen(config):
    """NYI - Parse NetScreen config to get metadata"""

def massage_data(device_list):
    """"
    Given a list of objects, try to fixup their metadata based on thse rules.

    INCOMPLETE.
    """
    devices = device_list

    netdevices = {}
    for idx, dev in enumerate(devices):
        if dev.manufacturer == 'netscreen':
            dev.manufacturer = 'juniper'
            dev.deviceType = 'FIREWALL'

        elif dev.manufacturer == 'cisco':
            dev.deviceType= 'ROUTER'

        elif dev.manufacturer == 'juniper':
            dev.deviceType = 'ROUTER'
        else:
            print 'WTF', dev.nodeName, 'requires no massaging!'

        """
        # Asset
        dev.serialNumber = dev.assetID = None
        dev.lastUpdate = datetime.datetime.today()
        """
        netdevices[dev.nodeName] = dev

    return netdevices


# Classes
class RancidDevice(collections.namedtuple("RancidDevice", NETDEVICE_FIELDS)):
    """
    A simple subclass of namedtuple to store contents of parsed RANCID files.

    Designed to support all router.* files. The field names are intended to be
    compatible with Trigger's NetDevice objects.

    :param nodeName:
        Hostname of device

    :param manufacturer:
        Vendor/manufacturer name of device

    :param deviceStatus:
        (Optional) Up/down status of device

    :param deviceType:
        (Optional) The device type... determined somehow
    """
    __slots__ = ()

    def __new__(cls, nodeName, manufacturer, deviceStatus=None, deviceType=None):
        return super(cls, RancidDevice).__new__(cls, nodeName, manufacturer,
                                                deviceStatus, deviceType)

class Rancid(object):
    """
    Holds RANCID data. INCOMPLETE.

    Defaults to a single RANID instance specified as ``rancid_root``. It will
    parse the file found at ``rancid_db_file`` and use this to populate the
    ``devices`` dictionary with instances of ``device_class``.

    If you set ``recurse_subdirs``, it is assumed that ``rancid_root`` holds
    one or more individual RANCID instances and will attempt to walk them,
    parse them, and then aggregate all of the resulting device instances into
    the ``devices`` dictionary.

    Still needs:

    + Config parsing for metadata (make, model, type, serial, etc.)
    + Recursive Config file population/parsing when ``recurse_subdirs`` is set

    :param rancid_root:
        Where to find your RANCID files (router.db, et al.)

    :param rancid_db_file:
        If it's named other than ``router.db``

    :param config_dir:
        If it's named other than ``configs``

    :param device_fields:
        A list of field names used to map to the device data. These must match
        the attributes expected by ``device_class``.

    :param device_class:
        If you want something other than ``RancidDevice``

    :param recurse_subdirs:
        Whether you want to recurse directories.
    """
    def __init__(self, rancid_root, rancid_db_file=RANCID_DB_FILE,
                 config_dirname=CONFIG_DIRNAME, device_fields=None,
                 device_class=None, recurse_subdirs=False):
        if device_class is None:
            device_class = RancidDevice

        self.rancid_root = rancid_root
        self.rancid_db_file = rancid_db_file
        self.config_dirname = config_dirname
        self.device_fields = device_fields
        self.device_class = device_class
        self.recurse_subdirs = recurse_subdirs
        self.configs = {}
        self.data = {}
        self.devices = {}
        self._populate()

    def _populate(self):
        """Fired after init, does all the stuff to populate RANCID data."""
        self._populate_devices()

    def _populate_devices(self):
        """
        Read router.db or equivalent and populate ``devices`` dictionary
        with objects.
        """
        metadata = parse_rancid_data(self.rancid_root,
                                     filename=self.rancid_db_file,
                                     fields=self.device_fields,
                                     config_dirname=self.config_dirname,
                                     recurse_subdirs=self.recurse_subdirs)

        objects = parse_devices(metadata, self.device_class)
        self.devices = dict((d.nodeName, d) for d in objects)

    def _populate_configs(self):
        """NYI - Read configs"""
        self.configs = _parse_config_files(self.devices.itervalues(),
                                           self.rancid_root)

    def _populate_data(self):
        """NYI - Maybe keep the other metadata but how?"""
        #self.data['routers.all'] = parse_rancid_file(root, RANCID_ALL_FILE)
        #self.data['routers.down'] = parse_rancid_file(root, RANCID_DOWN_FILE)
        #self.data['routers.up'] = parse_rancid_file(root, RANCID_UP_FILE)
        pass

    def __repr__(self):
        return 'Rancid(%r, recurse_subdirs=%s)' % (self.rancid_root,
                                                   self.recurse_subdirs)

########NEW FILE########
__FILENAME__ = tacacsrc
# -*- coding: utf-8 -*-

"""Abstract interface to .tacacsrc credentials file.

Designed to interoperate with the legacy DeviceV2 implementation, but
provide a reasonable API on top of that.  The name and format of the
.tacacsrc file are not ideal, but compatibility matters.
"""

__author__ = 'Jathan McCollum, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jmccollum@salesforce.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.; 2013 Salesforce.com'

from base64 import decodestring, encodestring
from collections import namedtuple
from Crypto.Cipher import DES3
from distutils.version import LooseVersion
import getpass
from time import strftime, localtime
import os
import pwd
import sys
from twisted.python import log
from trigger.conf import settings

# Exports
__all__ = ('get_device_password', 'prompt_credentials', 'convert_tacacsrc',
           'update_credentials', 'validate_credentials', 'Credentials', 'Tacacsrc')

# Credential object stored in Tacacsrc.creds
Credentials = namedtuple('Credentials', 'username password realm')

# Exceptions
class TacacsrcError(Exception): pass
class CouldNotParse(TacacsrcError): pass
class MissingPassword(TacacsrcError): pass
class MissingRealmName(TacacsrcError): pass
class VersionMismatch(TacacsrcError): pass


# Functions
def get_device_password(device=None, tcrc=None):
    """
    Fetch the password for a device/realm or create a new entry for it.
    If device is not passed, ``settings.DEFAULT_REALM`` is used, which is default
    realm for most devices.

    :param device:
        Realm or device name to updated

    :param device:
        Optional `~trigger.tacacsrc.Tacacsrc` instance
    """
    if tcrc is None:
        tcrc = Tacacsrc()

    # If device isn't passed, assume we are initializing the .tacacsrc.
    try:
        creds = tcrc.creds[device]
    except KeyError:
        print '\nCredentials not found for device/realm %r, prompting...' % device
        creds = prompt_credentials(device)
        tcrc.creds[device] = creds
        tcrc.write()

    return creds

def prompt_credentials(device, user=None):
    """
    Prompt for username, password and return them as Credentials namedtuple.

    :param device: Device or realm name to store
    :param user: (Optional) If set, use as default username
    """
    if not device:
        raise MissingRealmName('You must specify a device/realm name.')

    creds = ()
    # Make sure we can even get tty i/o!
    if sys.stdin.isatty() and sys.stdout.isatty():
        print '\nUpdating credentials for device/realm %r' % device

        user_default = ''
        if user:
            user_default = ' [%s]' % user

        username = getpass._raw_input('Username%s: ' % user_default) or user
        if username == '':
            print '\nYou must specify a username, try again!'
            return prompt_credentials(device, user=user)

        passwd = getpass.getpass('Password: ')
        passwd2 = getpass.getpass('Password (again): ')
        if not passwd:
            print '\nPassword cannot be blank, try again!'
            return prompt_credentials(device, user=username)

        if passwd != passwd2:
            print '\nPasswords did not match, try again!'
            return prompt_credentials(device, user=username)

        creds = Credentials(username, passwd, device)

    return creds

def update_credentials(device, username=None):
    """
    Update the credentials for a given device/realm. Assumes the same username
    that is already cached unless it is passed.

    This may seem redundant at first compared to Tacacsrc.update_creds() but we
    need this factored out so that we don't end up with a race condition when
    credentials are messed up.

    Returns True if it actually updated something or None if it didn't.

    :param device: Device or realm name to update
    :param username: Username for credentials
    """
    tcrc = Tacacsrc()
    if tcrc.creds_updated:
        return None

    mycreds = tcrc.creds.get(device, tcrc.creds[settings.DEFAULT_REALM])
    if username is None:
        username = mycreds.username

    tcrc.update_creds(tcrc.creds, mycreds.realm, username)
    tcrc.write()

    return True

def validate_credentials(creds=None):
    """
    Given a set of credentials, try to return a `~trigger.tacacsrc.Credentials`
    object.

    If ``creds`` is unset it will fetch from ``.tacacsrc``.

    Expects either a 2-tuple of (username, password) or a 3-tuple of (username,
    password, realm). If only (username, password) are provided, realm will be populated from
    :setting:`DEFAULT_REALM`.

    :param creds:
        A tuple of credentials.

    """
    realm = settings.DEFAULT_REALM

    # If it isn't set or it's a string, or less than 1 or more than 3 items,
    # get from .tacacsrc
    if (not creds) or (type(creds) == str) or (len(creds) not in (2, 3)):
        log.msg('Creds not valid, fetching from .tacacsrc...')
        tcrc = Tacacsrc()
        return tcrc.creds.get(realm, get_device_password(realm, tcrc))

    # If it's a dict, get the values
    if hasattr(creds, 'values'):
        log.msg('Creds is a dict, converting to values...')
        creds = creds.values()

    # If it's missing realm, add it.
    if len(creds) == 2:
        log.msg('Creds is a 2-tuple, making into namedtuple...')
        username, password = creds
        return Credentials(username, password, realm)

    # Or just make it go...
    elif len(creds) == 3:
        log.msg('Creds is a 3-tuple, making into namedtuple...')
        return Credentials(*creds)

    raise RuntimeError('THIS SHOULD NOT HAVE HAPPENED!!')

def convert_tacacsrc():
    """Converts old .tacacsrc to new .tacacsrc.gpg."""
    print "Converting old tacacsrc to new kind :)"
    tco = Tacacsrc(old=True)
    tcn = Tacacsrc(old=False, gen=True)
    tcn.creds = tco.creds
    tcn.write()

def _perl_unhex_old(c):
    """
    Emulate Crypt::TripleDES's bizarre handling of keys, which relies on
    the fact that you can pass Perl's pack('H*') a string that contains
    anything, not just hex digits.  "The result for bytes "g".."z" and
    "G".."Z" is not well-defined", says perlfunc(1).  Smash!

    This function can be safely removed once GPG is fully supported.
    """
    if 'a' <= c <= 'z':
        return (ord(c) - ord('a') + 10) & 0xf
    if 'A' <= c <= 'Z':
        return (ord(c) - ord('A') + 10) & 0xf
    return ord(c) & 0xf

def _perl_pack_Hstar_old(s):
    """
    Used with _perl_unhex_old(). Ghetto hack.

    This function can be safely removed once GPG is fully supported.
    """
    r = ''
    while len(s) > 1:
        r += chr((_perl_unhex_old(s[0]) << 4) | _perl_unhex_old(s[1]))
        s = s[2:]
    if len(s) == 1:
        r += _perl_unhex_old(s[0])
    return r


# Classes
class Tacacsrc(object):
    """
    Encrypts, decrypts and returns credentials for use by network devices and
    other tools.

    Pass use_gpg=True to force GPG, otherwise it relies on
    settings.USE_GPG_AUTH

    `*_old` functions should be removed after everyone is moved to the new
    system.
    """
    def __init__(self, tacacsrc_file=None, use_gpg=settings.USE_GPG_AUTH,
                 generate_new=False):
        """
        Open .tacacsrc (tacacsrc_file or $TACACSRC or ~/.tacacsrc), or create
        a new file if one cannot be found on disk.

        If settings.USE_GPG_AUTH is enabled, tries to use GPG (.tacacsrc.gpg).
        """
        self.file_name = tacacsrc_file
        self.use_gpg = use_gpg
        self.generate_new = generate_new
        self.userinfo = pwd.getpwuid(os.getuid())
        self.username = self.userinfo.pw_name
        self.user_home = self.userinfo.pw_dir
        self.data = []
        self.creds = {}
        self.creds_updated = False
        self.version = LooseVersion('2.0')

        # If we're not generating a new file and gpg is enabled, turn it off if
        # the right files can't be found.
        if not self.generate_new:
            if self.use_gpg and not self.user_has_gpg():
                log.msg(".tacacsrc.gpg not setup, disabling GPG", debug=True)
                self.use_gpg = False

        log.msg("Using GPG method: %r" % self.use_gpg, debug=True)
        log.msg("Got username: %r" % self.username, debug=True)

        # Set the .tacacsrc file location
        if self.file_name is None:
            self.file_name = settings.TACACSRC

            # GPG uses '.tacacsrc.gpg'
            if self.use_gpg:
                self.file_name += '.gpg'

        # Check if the file exists
        if not os.path.exists(self.file_name):
            print '%s not found, generating a new one!' % self.file_name
            self.generate_new = True

        if self.use_gpg:
            if not self.generate_new:
                self.rawdata = self._decrypt_and_read()
                self.creds = self._parse()
            else:
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(device='tacacsrc')
                self.write()
        else:
            self.key = self._get_key_old(settings.TACACSRC_KEYFILE)

            if not self.generate_new:
                self.rawdata = self._read_file_old()
                self.creds = self._parse_old()
                if self.creds_updated: # _parse_old() might set this flag
                    log.msg('creds updated, writing to file', debug=True)
                    self.write()
            else:
                self.creds[settings.DEFAULT_REALM] = prompt_credentials(device='tacacsrc')
                self.write()

    def _get_key_nonce_old(self):
        """Yes, the key nonce is the userid.  Awesome, right?"""
        return pwd.getpwuid(os.getuid())[0] + '\n'

    def _get_key_old(self, keyfile):
        '''Of course, encrypting something in the filesystem using a key
        in the filesystem really doesn't buy much.  This is best referred
        to as obfuscation of the .tacacsrc.'''
        with open(keyfile, 'r') as kf:
            key = kf.readline()
        if key[-1].isspace():
            key = key[:-1]
        key += self._get_key_nonce_old()
        key = _perl_pack_Hstar_old((key + (' ' * 48))[:48])
        assert(len(key) == 24)

        return key

    def _parse_old(self):
        """Parses .tacacsrc and returns dictionary of credentials."""
        data = {}
        creds = {}

        # Cleanup the rawdata
        for idx, line in enumerate(self.rawdata):
            line = line.strip() # eat \n
            lineno = idx + 1 # increment index for actual lineno

            # Skip blank lines and comments
            if any((line.startswith('#'), line == '')):
                log.msg('skipping %r' % line, debug=True)
                continue
            #log.msg('parsing %r' % line, debug=True)

            if line.count(' = ') > 1:
                raise CouldNotParse("Malformed line %r at line %s" % (line, lineno))

            key, sep, val = line.partition(' = ')
            if val == '':
                continue # Don't add a key with a missing value
                raise CouldNotParse("Missing value for key %r at line %s" % (key, lineno))

            # Check for version
            if key == 'version':
                if val != self.version:
                    raise VersionMismatch('Bad .tacacsrc version (%s)' % v)
                continue

            # Make sure tokens can be parsed
            realm, token, end = key.split('_')
            if end != '' or (realm, token) in data:
                raise CouldNotParse("Could not parse %r at line %s" % (line, lineno))

            data[(realm, token)] = self._decrypt_old(val)
            del key, val, line

        # Store the creds, if a password is empty, try to prompt for it.
        for (realm, key), val in data.iteritems():
            if key == 'uname':
                try:
                    #creds[realm] = Credentials(val, data[(realm, 'pwd')])
                    creds[realm] = Credentials(val, data[(realm, 'pwd')], realm)
                except KeyError:
                    print '\nMissing password for %r, initializing...' % realm
                    self.update_creds(creds=creds, realm=realm, user=val)
                    #raise MissingPassword('Missing password for %r' % realm)
            elif key == 'pwd':
                pass
            else:
                raise CouldNotParse('Unknown .tacacsrc entry (%s_%s)' % (realm, val))

        self.data = data
        return creds

    def update_creds(self, creds, realm, user=None):
        """
        Update username/password for a realm/device and set self.creds_updated
        bit to trigger .write().

        :param creds: Dictionary of credentials keyed by realm
        :param realm: The realm to update within the creds dict
        :param user: (Optional) Username passed to prompt_credentials()
        """
        creds[realm] = prompt_credentials(realm, user)
        log.msg('setting self.creds_updated flag', debug=True)
        self.creds_updated = True
        new_user = creds[realm].username
        print '\nCredentials updated for user: %r, device/realm: %r.' % \
              (new_user, realm)

    def _encrypt_old(self, s):
        """Encodes using the old method. Adds a newline for you."""
        cryptobj = DES3.new(self.key, DES3.MODE_ECB)
        # Crypt::TripleDES pads with *spaces*!  How 1960. Pad it so the
        # length is a multiple of 8.
        padding = len(s) % 8 and ' ' * (8 - len(s) % 8) or ''

        # We need to return a newline if a field is empty so as not to break
        # .tacacsrc parsing (trust me, this is easier)
        return (encodestring(cryptobj.encrypt(s + padding)).replace('\n', '') or '' ) + '\n'

    def _decrypt_old(self, s):
        """Decodes using the old method. Strips newline for you."""
        cryptobj = DES3.new(self.key, DES3.MODE_ECB)
        # rstrip() to undo space-padding; unfortunately this means that
        # passwords cannot end in spaces.
        return cryptobj.decrypt(decodestring(s)).rstrip(' ')

    def _read_file_old(self):
        """Read old style file and return the raw data."""
        self._update_perms()
        with open(self.file_name, 'r') as f:
            return f.readlines()

    def _write_old(self):
        """Write old style to disk. Newlines provided by _encrypt_old(), so don't fret!"""
        out = ['# Saved by %s at %s\n\n' % \
            (self.__module__, strftime('%Y-%m-%d %H:%M:%S %Z', localtime()))]

        for realm, (uname, pwd, _) in self.creds.iteritems():
            #log.msg('encrypting %r' % ((uname, pwd),), debug=True)
            out.append('%s_uname_ = %s' % (realm, self._encrypt_old(uname)))
            out.append('%s_pwd_ = %s' % (realm, self._encrypt_old(pwd)))

        with open(self.file_name, 'w+') as fd:
            fd.writelines(out)

        self._update_perms()

    def _decrypt_and_read(self):
        """Decrypt file using GPG and return the raw data."""
        ret = []
        for x in os.popen('gpg2 --no-tty --quiet -d %s' % self.file_name):
            x = x.rstrip()
            ret.append(x)

        return ret

    def _encrypt_and_write(self):
        """Encrypt using GPG and dump password data to disk."""
        (fin,fout) = os.popen2('gpg2 --yes --quiet -r %s -e -o %s' % (self.username, self.file_name))
        for line in self.rawdata:
            print >>fin, line

    def _write_new(self):
        """Replace self.rawdata with current password details."""
        out = ['# Saved by %s at %s\n\n' % \
            (self.__module__, strftime('%Y-%m-%d %H:%M:%S %Z', localtime()))]

        for realm, (uname, pwd, _) in self.creds.iteritems():
            out.append('%s_uname_ = %s' % (realm, uname))
            out.append('%s_pwd_ = %s' % (realm, pwd))

        self.rawdata = out
        self._encrypt_and_write()
        self._update_perms()

    def write(self):
        """Writes .tacacsrc(.gpg) using the accurate method (old vs. new)."""
        if self.use_gpg:
            return self._write_new()

        return self._write_old()

    def _update_perms(self):
        """Enforce -rw------- on the creds file"""
        os.chmod(self.file_name, 0600)

    def _parse(self):
        """Parses .tacacsrc.gpg and returns dictionary of credentials."""
        data = {}
        creds = {}
        for line in self.rawdata:
            if line.find('#') != -1:
                line = line[:line.find('#')]
            line = line.strip()
            if len(line):
                k, v = line.split(' = ')
                if k == 'version':
                    if v != self.version:
                        raise VersionMismatch('Bad .tacacsrc version (%s)' % v)
                else:
                    realm, s, junk = k.split('_')
                    #assert(junk == '')
                    assert((realm, s) not in data)
                    data[(realm, s)] = v#self._decrypt(v)

        for (realm, k), v in data.iteritems():
            if k == 'uname':
                #creds[realm] = (v, data[(realm, 'pwd')])
                #creds[realm] = Credentials(v, data[(realm, 'pwd')])
                creds[realm] = Credentials(v, data[(realm, 'pwd')], realm)
            elif k == 'pwd':
                pass
            else:
                raise CouldNotParse('Unknown .tacacsrc entry (%s_%s)' % (realm, v))

        return creds

    def user_has_gpg(self):
        """Checks if user has .gnupg directory and .tacacsrc.gpg file."""
        gpg_dir = os.path.join(self.user_home, '.gnupg')
        tacacsrc_gpg = os.path.join(self.user_home, '.tacacsrc.gpg')

        # If not generating new .tacacsrc.gpg, we want both to be True
        if os.path.isdir(gpg_dir) and os.path.isfile(tacacsrc_gpg):
            return True

        return False

########NEW FILE########
__FILENAME__ = twister
# -*- coding: utf-8 -*-

"""
Login and basic command-line interaction support using the Twisted asynchronous
I/O framework. The Trigger Twister is just like the Mersenne Twister, except not at all.
"""

__author__ = 'Jathan McCollum, Eileen Tschetter, Mark Thomas, Michael Shields'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2013, AOL Inc.; 2013 Salesforce.com'

import copy
import fcntl
import os
import re
import signal
import socket
import struct
import sys
import tty
from xml.etree.ElementTree import (Element, ElementTree, XMLTreeBuilder,
                                   tostring)
from twisted.conch.ssh import channel, common, session, transport, userauth
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch import telnet
from twisted.internet import defer, error, protocol, reactor, stdio
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log

from trigger.conf import settings
from trigger import tacacsrc, exceptions
from trigger.utils import network, cli

# Exports
# TODO (jathan): Setting this prevents everything from showing up in the Sphinx
# docs; so let's make sure we account for that ;)
#__all__ = ('connect', 'execute', 'stop_reactor')


# Constants
# Prompts sent by devices that indicate the device is awaiting user
# confirmation. The last one is very specific because we want to make sure bad
# things don't happen.
CONTINUE_PROMPTS = [
    'continue?',
    'proceed?',
    '(y/n):',
    '[y/n]:',
    '[confirm]',
    # Very specific to ensure bad things don't happen!
    'overwrite file [startup-config] ?[yes/press any key for no]....'
]

# Functions
#==================
# Helper functions
#==================
def has_junoscript_error(tag):
    """Test whether an Element contains a Junoscript xnm:error."""
    if ElementTree(tag).find('.//{http://xml.juniper.net/xnm/1.1/xnm}error'):
        return True
    return False

def has_juniper_error(s):
    """Test whether a string seems to contain an Juniper error."""
    tests = (
        'unknown command.' in s,
        'syntax error, ' in s,
        'invalid value.' in s,
        'missing argument.' in s,
    )
    return any(tests)

def has_ioslike_error(s):
    """Test whether a string seems to contain an IOS-like error."""
    tests = (
        s.startswith('%'),                 # Cisco, Arista
        '\n%' in s,                        # A10, Aruba, Foundry
        'syntax error: ' in s.lower(),     # Brocade VDX, F5 BIGIP
        s.startswith('Invalid input -> '), # Brocade MLX
        s.endswith('Syntax Error'),        # MRV
    )
    return any(tests)

def has_netscaler_error(s):
    """Test whether a string seems to contain a NetScaler error."""
    tests = (
        s.startswith('ERROR: '),
        '\nERROR: ' in s,
        s.startswith('Warning: '),
        '\nWarning: ' in s,
    )
    return any(tests)

def is_awaiting_confirmation(prompt):
    """
    Checks if a prompt is asking for us for confirmation and returns a Boolean.

    :param prompt:
        The prompt string to check
    """
    prompt = prompt.lower()
    matchlist = CONTINUE_PROMPTS
    return any(prompt.endswith(match) for match in matchlist)

def requires_enable(proto_obj, data):
    """
    Check if a device requires enable.

    :param proto_obj:
        A Protocol object such as an SSHChannel

    :param data:
        The channel data to check for an enable prompt
    """
    if not proto_obj.device.is_ioslike():
        log.msg('[%s] Not IOS-like, setting enabled flag' % proto_obj.device)
        proto_obj.enabled = True
        return None
    match = proto_obj.enable_prompt.search(data)
    if match is not None:
        log.msg('[%s] Enable prompt detected: %r' % (proto_obj.device,
                                                     match.group()))
    return match

def send_enable(proto_obj):
    """
    Send 'enable' and enable password to device.

    :param proto_obj:
        A Protocol object such as an SSHChannel
    """
    log.msg('[%s] Enable required, sending enable commands' % proto_obj.device)

    # Get enable password from env. or device object
    device_pw = getattr(proto_obj.device, 'enablePW', None)
    enable_pw = os.getenv('TRIGGER_ENABLEPW') or device_pw
    if enable_pw is not None:
        log.msg('[%s] Enable password detected, sending...' % proto_obj.device)
        proto_obj.data = '' # Zero out the buffer before sending the password
        proto_obj.write('enable' + proto_obj.device.delimiter)
        proto_obj.write(enable_pw + proto_obj.device.delimiter)
        proto_obj.enabled = True
    else:
        log.msg('[%s] Enable password not found, not enabling.' %
                proto_obj.device)

def stop_reactor():
    """Stop the reactor if it's already running."""
    from twisted.internet import reactor
    if reactor.running:
        log.msg('Stopping reactor')
        reactor.stop()

#==================
# PTY functions
#==================
def pty_connect(device, action, creds=None, display_banner=None,
                ping_test=False, init_commands=None):
    """
    Connect to a ``device`` and log in. Use SSHv2 or telnet as appropriate.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param action:
        A Twisted ``Protocol`` instance (not class) that will be activated when
        the session is ready.

    :param creds:
        A 2-tuple (username, password). By default, credentials from
        ``.tacacsrc`` will be used according to ``settings.DEFAULT_REALM``.
        Override that here.

    :param display_banner:
        Will be called for SSH pre-authentication banners. It will receive two
        args, ``banner`` and ``language``. By default, nothing will be done
        with the banner.

    :param ping_test:
        If set, the device is pinged and must succeed in order to proceed.

    :param init_commands:
        A list of commands to execute upon logging into the device.

    :returns: A Twisted ``Deferred`` object
    """
    d = defer.Deferred()

    # Only proceed if ping succeeds
    if ping_test:
        log.msg('Pinging %s' % device, debug=True)
        if not network.ping(device.nodeName):
            log.msg('Ping to %s failed' % device, debug=True)
            return None

    # SSH?
    if device.can_ssh_pty():
        log.msg('[%s] SSH connection test PASSED' % device)
        if hasattr(sys, 'ps1') or not sys.stderr.isatty() \
         or not sys.stdin.isatty() or not sys.stdout.isatty():
            # Shell not in interactive mode.
            pass

        else:
            if not creds and device.is_firewall():
                creds = tacacsrc.get_device_password(device.nodeName)

        factory = TriggerSSHPtyClientFactory(d, action, creds, display_banner,
                                             init_commands, device=device)
        log.msg('Trying SSH to %s' % device, debug=True)
        port = 22

    # or Telnet?
    elif settings.TELNET_ENABLED:
        log.msg('[%s] SSH connection test FAILED, falling back to telnet' %
                device)
        factory = TriggerTelnetClientFactory(d, action, creds,
                                             init_commands=init_commands, device=device)
        log.msg('Trying telnet to %s' % device, debug=True)
        port = 23
    else:
        log.msg('[%s] SSH connection test FAILED, telnet fallback disabled' % device)
        return None

    reactor.connectTCP(device.nodeName, port, factory)
    # TODO (jathan): There has to be another way than calling Tacacsrc
    # construtor AGAIN...
    print '\nFetching credentials from %s' % tacacsrc.Tacacsrc().file_name

    return d

login_failed = None
def handle_login_failure(failure):
    """
    An errback to try detect a login failure

    :param failure:
        A Twisted ``Failure`` instance
    """
    global login_failed
    login_failed = failure

def connect(device, init_commands=None, output_logger=None, login_errback=None,
            reconnect_handler=None):
    """
    Connect to a network device via pty for an interactive shell.

    :param device:
        A `~trigger.netdevices.NetDevice` object.

    :param init_commands:
        (Optional) A list of commands to execute upon logging into the device.
        If not set, they will be attempted to be read from ``.gorc``.

    :param output_logger:
        (Optional) If set all data received by the device, including user
        input, will be written to this logger. This logger must behave like a
        file-like object and a implement a `.write()` method. Hint: Use
        ``StringIO``.

    :param login_errback:
        (Optional) An callable to be used as an errback that will handle the
        login failure behavior. If not set the default handler will be used.

    :param reconnect_handler:
        (Optional) A callable to handle the behavior of an authentication
        failure after a login has failed. If not set default handler will be
        used.
    """
    # Need to pass ^C through to the router so we can abort traceroute, etc.
    print 'Connecting to %s.  Use ^X to exit.' % device

    # Fetch the initial commands for the device
    if init_commands is None:
        from trigger import gorc
        init_commands = gorc.get_init_commands(device.vendor.name)

    # Sane defaults
    if login_errback is None:
        login_errback = handle_login_failure
    if reconnect_handler is None:
        reconnect_handler = cli.update_password_and_reconnect

    try:
        d = pty_connect(device, Interactor(log_to=output_logger),
                        init_commands=init_commands)
        d.addErrback(login_errback)
        d.addErrback(log.err)
        d.addCallback(lambda x: stop_reactor())
    except AttributeError as err:
        log.msg(err)
        sys.stderr.write('Could not connect to %s.\n' % device)
        return 2 # Bad exit code

    cli.setup_tty_for_pty(reactor.run)

    # If there is a login failure stop the reactor so we can take raw_input(),
    # ask the user if they, want to update their cached credentials, and
    # prompt them to connect. Otherwise just display the error message and
    # exit.
    if login_failed is not None:
        stop_reactor()

        #print '\nLogin failed for the following reason:\n'
        print '\nConnection failed for the following reason:\n'
        print '%s\n' % login_failed.value

        if login_failed.type == exceptions.LoginFailure:
            reconnect_handler(device.nodeName)

        print 'BYE'

    return 0 # Good exit code

#==================
# Execute Factory functions
#==================
def _choose_execute(device, force_cli=False):
    """
    Return the appropriate execute_ function for the given ``device`` based on
    platform and SSH/Telnet availability.

    :param device:
        A `~trigger.netdevices.NetDevice` object.
    """
    if device.is_ioslike():
        _execute = execute_ioslike
    elif device.is_netscaler():
        _execute = execute_netscaler
    elif device.is_netscreen():
        _execute = execute_netscreen
    elif device.vendor == 'juniper':
        if force_cli:
            _execute = execute_async_pty_ssh
        else:
            _execute = execute_junoscript
    else:
        _execute = execute_async_pty_ssh

    return _execute

def execute(device, commands, creds=None, incremental=None, with_errors=False,
            timeout=settings.DEFAULT_TIMEOUT, command_interval=0, force_cli=False):
    """
    Connect to a ``device`` and sequentially execute all the commands in the
    iterable ``commands``.

    Returns a Twisted ``Deferred`` object, whose callback will get a sequence
    of all the results after the connection is finished.

    ``commands`` is usually just a list, however, you can have also make it a
    generator, and have it and ``incremental`` share a closure to some state
    variables. This allows you to determine what commands to execute
    dynamically based on the results of previous commands. This implementation
    is experimental and it might be a better idea to have the ``incremental``
    callback determine what command to execute next; it could then be a method
    of an object that keeps state.

        BEWARE: Your generator cannot block; you must immediately
        decide what next command to execute, if any.

    Any ``None`` in the command sequence will result in a ``None`` being placed in
    the output sequence, with no command issued to the device.

    If any command returns an error, the connection is dropped immediately and
    the errback will fire with the failed command. You may set ``with_errors``
    to get the exception objects in the list instead.

    Connection failures will still fire the errback.

    `~trigger.exceptions.LoginTimeout` errors are always possible if the login
    process takes longer than expected and cannot be disabled.

    :param device:
        A `~trigger.netdevices.NetDevice` object

    :param commands:
        An iterable of commands to execute (without newlines).

    :param creds:
        (Optional) A 2-tuple of (username, password). If unset it will fetch it
        from ``.tacacsrc``.

    :param incremental:
        (Optional) A callback that will be called with an empty sequence upon
        connection and then called every time a result comes back from the
        device, with the list of all results.

    :param with_errors:
        (Optional) Return exceptions as results instead of raising them

    :param timeout:
        (Optional) Command response timeout in seconds. Set to ``None`` to
        disable. The default is in ``settings.DEFAULT_TIMEOUT``.
        `~trigger.exceptions.CommandTimeout` errors will result if a command seems
        to take longer to return than specified.

    :param command_interval:
        (Optional) Amount of time in seconds to wait between sending commands.

    :param force_cli:
        (Optional) Juniper-only: Force use of CLI instead of Junoscript.

    :returns: A Twisted ``Deferred`` object
    """
    execute_func = _choose_execute(device, force_cli=force_cli)
    return execute_func(device=device, commands=commands, creds=creds,
                        incremental=incremental, with_errors=with_errors,
                        timeout=timeout, command_interval=command_interval)

def execute_generic_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0, channel_class=None,
                        prompt_pattern=None, method='Generic',
                        connection_class=None):
    """
    Use default SSH channel to execute commands on a device. Should work with
    anything not wonky.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    d = defer.Deferred()

    # Fallback to sane defaults if they aren't specified
    if channel_class is None:
        channel_class = TriggerSSHGenericChannel
    if prompt_pattern is None:
        prompt_pattern = device.vendor.prompt_pattern
    if connection_class is None:
        connection_class = TriggerSSHConnection

    factory = TriggerSSHChannelFactory(d, commands, creds, incremental,
                                       with_errors, timeout, channel_class,
                                       command_interval, prompt_pattern,
                                       device, connection_class)

    log.msg('Trying %s SSH to %s' % (method, device), debug=True)
    reactor.connectTCP(device.nodeName, 22, factory)
    return d

def execute_exec_ssh(device, commands, creds=None, incremental=None,
                     with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                     command_interval=0):
    """
    Use multiplexed SSH 'exec' command channels to execute commands.

    This will maintain a single SSH connection and run each new command in a
    separate channel after the previous command completes.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    channel_class = TriggerSSHCommandChannel
    prompt_pattern = ''
    method = 'Exec'
    connection_class = TriggerSSHMultiplexConnection
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method,
                               connection_class)

def execute_junoscript(device, commands, creds=None, incremental=None,
                       with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                       command_interval=0):
    """
    Connect to a Juniper device and enable Junoscript XML mode. All commands
    are expected to be XML commands (ElementTree.Element objects suitable for
    wrapping in ``<rpc>`` elements). Errors are expected to be of type
    ``xnm:error``. Note that prompt detection is not used here.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.vendor == 'juniper'

    channel_class = TriggerSSHJunoscriptChannel
    prompt_pattern = ''
    method = 'Junoscript'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method)

def execute_ioslike(device, commands, creds=None, incremental=None,
                    with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                    command_interval=0, loginpw=None, enablepw=None):
    """
    Execute commands on a Cisco/IOS-like device. It will automatically try to
    connect using SSH if it is available and not disabled in ``settings.py``.
    If SSH is unavailable, it will fallback to telnet unless that is also
    disabled in the settings. Otherwise it will fail, so you should probably
    make sure one or the other is enabled!

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    # Try SSH if it's available and enabled
    if device.can_ssh_async():
        log.msg('execute_ioslike: SSH ENABLED for %s' % device.nodeName)
        return execute_ioslike_ssh(device=device, commands=commands,
                                   creds=creds, incremental=incremental,
                                   with_errors=with_errors, timeout=timeout,
                                   command_interval=command_interval)

    # Fallback to telnet if it's enabled
    elif settings.TELNET_ENABLED:
        log.msg('execute_ioslike: TELNET ENABLED for %s' % device.nodeName)
        return execute_ioslike_telnet(device=device, commands=commands,
                                      creds=creds, incremental=incremental,
                                      with_errors=with_errors, timeout=timeout,
                                      command_interval=command_interval,
                                      loginpw=loginpw, enablepw=enablepw)

    else:
        msg = 'Both SSH and telnet either failed or are disabled.'
        log.msg('[%s]' % device, msg)
        e = exceptions.ConnectionFailure(msg)
        return defer.fail(e)

def execute_ioslike_telnet(device, commands, creds=None, incremental=None,
                           with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                           command_interval=0, loginpw=None, enablepw=None):
    """
    Execute commands via telnet on a Cisco/IOS-like device.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_ioslike()

    d = defer.Deferred()
    action = IoslikeSendExpect(device, commands, incremental, with_errors,
                               timeout, command_interval)
    factory = TriggerTelnetClientFactory(d, action, creds, loginpw, enablepw)

    log.msg('Trying IOS-like scripting to %s' % device, debug=True)
    reactor.connectTCP(device.nodeName, 23, factory)
    return d

def execute_async_pty_ssh(device, commands, creds=None, incremental=None,
                          with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                          command_interval=0, prompt_pattern=None):
    """
    Execute via SSH for a device that requires shell + pty-req.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    channel_class = TriggerSSHAsyncPtyChannel
    method = 'Async PTY'
    if prompt_pattern is None:
        prompt_pattern = device.vendor.prompt_pattern

    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, prompt_pattern, method)

def execute_ioslike_ssh(device, commands, creds=None, incremental=None,
                        with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                        command_interval=0):
    """
    Execute via SSH for IOS-like devices with some exceptions.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_ioslike()

    # Test if device requires shell + pty-req
    if device.requires_async_pty:
        return execute_async_pty_ssh(device, commands, creds, incremental,
                                     with_errors, timeout, command_interval)
    # Or fallback to generic
    else:
        method = 'IOS-like'
        return execute_generic_ssh(device, commands, creds, incremental,
                                   with_errors, timeout, command_interval,
                                   method=method)

def execute_netscreen(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Execute commands on a NetScreen device running ScreenOS. For NetScreen
    devices running Junos, use `~trigger.twister.execute_junoscript`.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_netscreen()

    # We live in a world where not every NetScreen device is local and can use
    # TACACS, so we must store unique credentials for each NetScreen device.
    if not creds:
        creds = tacacsrc.get_device_password(device.nodeName)

    channel_class = TriggerSSHGenericChannel
    method = 'NetScreen'
    prompt_pattern = settings.PROMPT_PATTERNS['netscreen'] # This sucks
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, method=method,
                               prompt_pattern=prompt_pattern)

def execute_netscaler(device, commands, creds=None, incremental=None,
                      with_errors=False, timeout=settings.DEFAULT_TIMEOUT,
                      command_interval=0):
    """
    Execute commands on a NetScaler device.

    Please see `~trigger.twister.execute` for a full description of the
    arguments and how this works.
    """
    assert device.is_netscaler()

    channel_class = TriggerSSHNetscalerChannel
    method = 'NetScaler'
    return execute_generic_ssh(device, commands, creds, incremental,
                               with_errors, timeout, command_interval,
                               channel_class, method=method)


# Classes
#==================
# Client Factories
#==================
class TriggerClientFactory(protocol.ClientFactory, object):
    """
    Factory for all clients. Subclass me.
    """
    def __init__(self, deferred, creds=None, init_commands=None):
        self.d = deferred
        self.creds = tacacsrc.validate_credentials(creds)
        self.results = []
        self.err = None

        # Setup and run the initial commands
        if init_commands is None:
            init_commands = [] # We need this to be a list
        self.init_commands = init_commands
        log.msg('INITIAL COMMANDS: %r' % self.init_commands, debug=True)
        self.initialized = False

    def clientConnectionFailed(self, connector, reason):
        """Do this when the connection fails."""
        log.msg('Client connection failed. Reason: %s' % reason)
        self.d.errback(reason)

    def clientConnectionLost(self, connector, reason):
        """Do this when the connection is lost."""
        log.msg('Client connection lost. Reason: %s' % reason)
        if self.err:
            log.msg('Got err: %r' % self.err)
            #log.err(self.err)
            self.d.errback(self.err)
        else:
            log.msg('Got results: %r' % self.results)
            self.d.callback(self.results)

    def stopFactory(self):
        # IF we're out of channels, shut it down!
        log.msg('All done!')

    def _init_commands(self, protocol):
        """
        Execute any initial commands specified.

        :param protocol: A Protocol instance (e.g. action) to which to write
        the commands.
        """
        if not self.initialized:
            log.msg('Not initialized, sending init commands', debug=True)
            for next_init in self.init_commands:
                log.msg('Sending: %r' % next_init, debug=True)
                protocol.write(next_init + '\r\n')
            else:
                self.initialized = True

    def connection_success(self, conn, transport):
        log.msg('Connection success.')
        self.conn = conn
        self.transport = transport
        log.msg('Connection information: %s' % self.transport)

class TriggerSSHChannelFactory(TriggerClientFactory):
    """
    Intended to be used as a parent of automated SSH channels (e.g. Junoscript,
    NetScreen, NetScaler) to eliminate boiler plate in those subclasses.
    """
    def __init__(self, deferred, commands, creds=None, incremental=None,
                 with_errors=False, timeout=None, channel_class=None,
                 command_interval=0, prompt_pattern=None, device=None,
                 connection_class=None):

        # Fallback to sane defaults if they aren't specified
        if channel_class is None:
            channel_class = TriggerSSHGenericChannel
        if connection_class is None:
            connection_class = TriggerSSHConnection
        if prompt_pattern is None:
            prompt_pattern = settings.DEFAULT_PROMPT_PAT

        self.protocol = TriggerSSHTransport
        self.display_banner = None
        self.commands = commands
        self.commanditer = iter(commands)
        self.initialized = False
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.channel_class = channel_class
        self.command_interval = command_interval
        self.prompt = re.compile(prompt_pattern)
        self.device = device
        self.connection_class = connection_class
        TriggerClientFactory.__init__(self, deferred, creds)

    def buildProtocol(self, addr):
        self.protocol = self.protocol()
        self.protocol.factory = self
        return self.protocol

class TriggerSSHPtyClientFactory(TriggerClientFactory):
    """
    Factory for an interactive SSH connection.

    'action' is a Protocol that will be connected to the session after login.
    Use it to interact with the user and pass along commands.
    """
    def __init__(self, deferred, action, creds=None, display_banner=None,
                 init_commands=None, device=None):
        self.protocol = TriggerSSHTransport
        self.action = action
        self.action.factory = self
        self.device = device
        self.display_banner = display_banner
        self.channel_class = TriggerSSHPtyChannel
        self.connection_class = TriggerSSHConnection
        self.commands = []
        self.command_interval = 0
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)

#==================
# SSH Basics
#==================
class TriggerSSHTransport(transport.SSHClientTransport, object):
    """
    SSH transport with Trigger's defaults.

    Call with magic factory attributes ``creds``, a tuple of login
    credentials, and ``connection_class``, the class of channel to open, and
    ``commands``, the list of commands to pass to the connection.
    """
    def verifyHostKey(self, pubKey, fingerprint):
        """Verify host key, but don't actually verify. Awesome."""
        return defer.succeed(True)

    def connectionSecure(self):
        """Once we're secure, authenticate."""
        ua = TriggerSSHUserAuth(self.factory.creds.username,
                                self.factory.connection_class(self.factory.commands))
        self.requestService(ua)

    def receiveError(self, reason, desc):
        """Do this when we receive an error."""
        log.msg('Received an error, reason: %s, desc: %s)' % (reason, desc))
        self.sendDisconnect(reason, desc)

    def connectionLost(self, reason):
        """
        Detect when the transport connection is lost, such as when the
        remote end closes the connection prematurely (hosts.allow, etc.)
        """
        super(TriggerSSHTransport, self).connectionLost(reason)
        log.msg('Transport connection lost: %s' % reason.value)

    def sendDisconnect(self, reason, desc):
        """Trigger disconnect of the transport."""
        log.msg('Got disconnect request, reason: %r, desc: %r' % (reason, desc))

        # Only throw an error if this wasn't user-initiated (reason: 10)
        if reason == transport.DISCONNECT_CONNECTION_LOST:
            pass
        # Protocol errors should result in login failures
        elif reason == transport.DISCONNECT_PROTOCOL_ERROR:
            self.factory.err = exceptions.LoginFailure(desc)
        # Fallback to connection lost
        else:
            # Emulate the most common OpenSSH reason for this to happen
            if reason == transport.DISCONNECT_HOST_NOT_ALLOWED_TO_CONNECT:
                desc = 'ssh_exchange_identification: Connection closed by remote host'
            self.factory.err = exceptions.SSHConnectionLost(reason, desc)

        super(TriggerSSHTransport, self).sendDisconnect(reason, desc)

class TriggerSSHUserAuth(userauth.SSHUserAuthClient):
    """Perform user authentication over SSH."""
    # We are not yet in a world where network devices support publickey
    # authentication, so these are it.
    preferredOrder = ['password', 'keyboard-interactive']

    def getPassword(self, prompt=None):
        """Send along the password."""
        log.msg('Performing password authentication', debug=True)
        return defer.succeed(self.transport.factory.creds.password)

    def getGenericAnswers(self, name, information, prompts):
        """
        Send along the password when authentication mechanism is not 'password'.
        This is most commonly the case with 'keyboard-interactive', which even
        when configured within self.preferredOrder, does not work using default
        getPassword() method.
        """
        log.msg('Performing interactive authentication', debug=True)
        log.msg('Prompts: %r' % prompts, debug=True)

        # The response must always a sequence, and the length must match that
        # of the prompts list
        response = [''] * len(prompts)
        for idx, prompt_tuple in enumerate(prompts):
            prompt, echo = prompt_tuple # e.g. [('Password: ', False)]
            if 'assword' in prompt:
                log.msg("Got password prompt: %r, sending password!" % prompt,
                        debug=True)
                response[idx] = self.transport.factory.creds.password

        return defer.succeed(response)

    def ssh_USERAUTH_BANNER(self, packet):
        """Display SSH banner."""
        if self.transport.factory.display_banner:
            banner, language = common.getNS(packet)
            self.transport.factory.display_banner(banner, language)

    def ssh_USERAUTH_FAILURE(self, packet):
        """
        An almost exact duplicate of SSHUserAuthClient.ssh_USERAUTH_FAILURE
        modified to forcefully disconnect. If we receive authentication
        failures, instead of looping until the server boots us and performing a
        sendDisconnect(), we raise a `~trigger.exceptions.LoginFailure` and
        call loseConnection().

        See the base docstring for the method signature.
        """
        canContinue, partial = common.getNS(packet)
        partial = ord(partial)
        log.msg('Previous method: %r ' % self.lastAuth, debug=True)

        # If the last method succeeded, track it. If network devices ever start
        # doing second-factor authentication this might be useful.
        if partial:
            self.authenticatedWith.append(self.lastAuth)
        # If it failed, track that too...
        else:
            log.msg('Previous method failed, skipping it...', debug=True)
            self.authenticatedWith.append(self.lastAuth)

        def orderByPreference(meth):
            """
            Invoked once per authentication method in order to extract a
            comparison key which is then used for sorting.

            @param meth: the authentication method.
            @type meth: C{str}

            @return: the comparison key for C{meth}.
            @rtype: C{int}
            """
            if meth in self.preferredOrder:
                return self.preferredOrder.index(meth)
            else:
                # put the element at the end of the list.
                return len(self.preferredOrder)

        canContinue = sorted([meth for meth in canContinue.split(',')
                              if meth not in self.authenticatedWith],
                             key=orderByPreference)

        log.msg('Can continue with: %s' % canContinue)
        log.msg('Already tried: %s' % self.authenticatedWith, debug=True)
        return self._cbUserauthFailure(None, iter(canContinue))

    def _cbUserauthFailure(self, result, iterator):
        """Callback for ssh_USERAUTH_FAILURE"""
        if result:
            return
        try:
            method = iterator.next()
        except StopIteration:
            #self.transport.sendDisconnect(
            #    transport.DISCONNECT_NO_MORE_AUTH_METHODS_AVAILABLE,
            #    'no more authentication methods available')
            self.transport.factory.err = exceptions.LoginFailure(
                'No more authentication methods available')
            self.transport.loseConnection()
        else:
            d = defer.maybeDeferred(self.tryAuth, method)
            d.addCallback(self._cbUserauthFailure, iterator)
            return d

class TriggerSSHConnection(SSHConnection, object):
    """
    Used to manage, you know, an SSH connection.

    Optionally takes a list of commands that may be passed on.
    """
    def __init__(self, commands=None, *args, **kwargs):
        super(TriggerSSHConnection, self).__init__()
        self.commands = commands

    def serviceStarted(self):
        """Open the channel once we start."""
        log.msg('channel = %r' % self.transport.factory.channel_class)
        self.channel_class = self.transport.factory.channel_class
        self.command_interval = self.transport.factory.command_interval
        self.transport.factory.connection_success(self, self.transport)

        # Abstracted out so we can do custom stuff with self.openChannel
        self._channelOpener()

    def _channelOpener(self):
        """This is what calls ``self.channelOpen()``"""
        # Default behavior: Single channel/conn
        self.openChannel(self.channel_class(conn=self))

    def channelClosed(self, channel):
        """
        Forcefully close the transport connection when a channel closes
        connection. This is assuming only one channel is open.
        """
        log.msg('Forcefully closing transport connection!')
        self.transport.loseConnection()

class TriggerSSHMultiplexConnection(TriggerSSHConnection):
    """
    Used for multiplexing SSH 'exec' channels on a single connection.

    Opens a new channel for each command in the stack once the previous channel
    has closed. In this pattern the Connection and the Channel are intertwined.
    """
    def _channelOpener(self):
        log.msg('Multiplex connection started')
        self.work = list(self.commands) # Make sure this is a list :)
        self.send_command()

    def channelClosed(self, channel):
        """Close the channel when we're done. But not the transport connection"""
        log.msg('CHANNEL %s closed' % channel.id)
        SSHConnection.channelClosed(self, channel)

    def send_command(self):
        """
        Send the next command in the stack once the previous channel has closed.
        """
        try:
            command = self.work.pop(0)
        except IndexError:
            log.msg('ALL COMMANDS HAVE FINISHED!')
            return None

        def command_completed(result, chan):
            log.msg('Command completed: %r' % chan.command)
            return result

        def command_failed(failure, chan):
            log.msg('Command failed: %r' % chan.command)
            return failure

        def log_status(result):
            log.msg('COMMANDS LEN: %s' % len(self.commands))
            log.msg(' RESULTS LEN: %s' % len(self.transport.factory.results))
            return result

        log.msg('SENDING NEXT COMMAND: %s' % command)

        # Send the command to the channel
        chan = self.channel_class(command, conn=self)

        d = defer.Deferred()
        reactor.callLater(self.command_interval, d.callback, self.openChannel(chan))
        d.addCallback(command_completed, chan)
        d.addErrback(command_failed, chan)
        d.addBoth(log_status)
        return d

#==================
# SSH PTY Stuff
#==================
class Interactor(protocol.Protocol):
    """
    Creates an interactive shell.

    Intended for use as an action with pty_connect(). See gong for an example.
    """
    def __init__(self, log_to=None):
        self._log_to = log_to
        self.enable_prompt = re.compile(settings.IOSLIKE_ENABLE_PAT)
        self.enabled = False
        self.initialized = False

    def _log(self, data):
        if self._log_to is not None:
            self._log_to.write(data)

    def connectionMade(self):
        """Fire up stdin/stdout once we connect."""
        c = protocol.Protocol()
        c.dataReceived = self.write
        self.stdio = stdio.StandardIO(c)
        self.device = self.factory.device # Attach the device object

    def dataReceived(self, data):
        """And write data to the terminal."""
        # Check whether we need to send an enable password.
        if not self.enabled and requires_enable(self, data):
            send_enable(self)

        # Setup and run the initial commands
        if data and not self.initialized:
            self.factory._init_commands(protocol=self)
            self.initialized = True

        self._log(data)
        self.stdio.write(data)

class TriggerSSHPtyChannel(channel.SSHChannel):
    """
    Used by pty_connect() to turn up an interactive SSH pty channel.
    """
    name = 'session'

    def channelOpen(self, data):
        """Setup the terminal when the channel opens."""
        pr = session.packRequest_pty_req(os.environ['TERM'],
                                         self._get_window_size(), '')
        self.conn.sendRequest(self, 'pty-req', pr)
        self.conn.sendRequest(self, 'shell', '')
        signal.signal(signal.SIGWINCH, self._window_resized)

        # Pass control to the action.
        self.factory = self.conn.transport.factory
        action = self.factory.action
        action.write = self.write
        self.dataReceived = action.dataReceived
        self.extReceived = action.dataReceived
        self.connectionLost = action.connectionLost
        action.connectionMade()
        action.dataReceived(data)

    def _window_resized(self, *args):
        """Triggered when the terminal is rezied."""
        win_size = self._get_window_size()
        new_size = win_size[1], win_size[0], win_size[2], win_size[3]
        self.conn.sendRequest(self, 'window-change',
                              struct.pack('!4L', *new_size))

    def _get_window_size(self):
        """Measure the terminal."""
        stdin_fileno = sys.stdin.fileno()
        winsz = fcntl.ioctl(stdin_fileno, tty.TIOCGWINSZ, '12345678')
        return struct.unpack('4H', winsz)

#==================
# SSH Channels
#==================
class TriggerSSHChannelBase(channel.SSHChannel, TimeoutMixin, object):
    """
    Base class for SSH channels.

    The method self._setup_channelOpen() should be called by channelOpen() in
    the subclasses. Before you subclass, however, see if you can't just use
    TriggerSSHGenericChannel as-is!
    """
    name = 'session'

    def _setup_channelOpen(self):
        """
        Call me in your subclass in self.channelOpen()::

            def channelOpen(self, data):
                self._setup_channelOpen()
                self.conn.sendRequest(self, 'shell', '')
                # etc.
        """
        self.factory = self.conn.transport.factory
        self.commanditer = self.factory.commanditer
        self.results = self.factory.results
        self.with_errors = self.factory.with_errors
        self.incremental = self.factory.incremental
        self.command_interval = self.factory.command_interval
        self.prompt = self.factory.prompt
        self.setTimeout(self.factory.timeout)
        self.device = self.factory.device
        log.msg('[%s] COMMANDS: %r' % (self.device, self.factory.commands))
        self.data = ''
        self.initialized = self.factory.initialized
        self.startup_commands = copy.copy(self.device.startup_commands)
        log.msg('[%s] My startup commands: %r' % (self.device,
                                                  self.startup_commands))

        # For IOS-like devices that require 'enable'
        self.enable_prompt = re.compile(settings.IOSLIKE_ENABLE_PAT)
        self.enabled = False

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self._setup_channelOpen()
        d = self.conn.sendRequest(self, 'shell', '', wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

        # Don't call _send_next() here, since we (might) expect to see a
        # prompt, which will kick off initialization.

    def _gotResponse(self, response):
        """
        Potentially useful if you want to do something after the shell is
        initialized.

        If the shell never establishes, this won't be called.
        """
        log.msg('[%s] Got channel request response!' % self.device)

    def _ebShellOpen(self, reason):
        log.msg('[%s] Channel request failed: %s' % (self.device, reason))

    def dataReceived(self, bytes):
        """Do this when we receive data."""
        # Append to the data buffer
        self.data += bytes
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        #log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft, self.localMaxPacket, len(bytes),
        #         len(self.data)))

        # Keep going til you get a prompt match
        m = self.prompt.search(self.data)
        if not m:
            # Do we need to send an enable password?
            if not self.enabled and requires_enable(self, self.data):
                send_enable(self)
                return None

            # Check for confirmation prompts
            # If the prompt confirms set the index to the matched bytes
            if is_awaiting_confirmation(self.data):
                log.msg('[%s] Got confirmation prompt: %r' % \
                        (self.device, self.data))
                prompt_idx = self.data.find(bytes)
            else:
                return None
        else:
            # Or just use the matched regex object...
            log.msg('[%s] STATE: prompt %r' % (self.device, m.group()))
            prompt_idx = m.start()

        # Strip the prompt from the match result
        result = self.data[:prompt_idx]
        result = result[result.find('\n')+1:]

        # Only keep the results once we've sent any startup_commands
        if self.initialized:
            self.results.append(result)

        # By default we're checking for IOS-like or Juniper errors because most
        # vendors # fall under this category.
        if (has_ioslike_error(result) or has_juniper_error(result)) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.CommandFailure(result)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            reactor.callLater(self.command_interval, self._send_next)

    def _send_next(self):
        """Send the next command in the stack."""
        # Reset the timeout and the buffer for each new command
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            log.msg('[%s] Not initialized; sending startup commands' %
                    self.device)
            if self.startup_commands:
                next_init = self.startup_commands.pop(0)
                log.msg('[%s] Sending initialize command: %r' % (self.device,
                                                                 next_init))
                self.write(next_init.strip() + self.device.delimiter)
                return None
            else:
                log.msg('[%s] Successfully initialized for command execution' %
                        self.device)
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('[%s] CHANNEL: out of commands, closing connection...' %
                    self.device)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('[%s] Sending SSH command %r' % (self.device,
                                                     next_command))
            self.write(next_command + self.device.delimiter)

    def loseConnection(self):
        """
        Terminate the connection. Link this to the transport method of the same
        name.
        """
        log.msg('[%s] Forcefully closing transport connection' % self.device)
        self.conn.transport.loseConnection()

    def timeoutConnection(self):
        """
        Do this when the connection times out.
        """
        log.msg('[%s] Timed out while sending commands' % self.device)
        self.factory.err = exceptions.CommandTimeout('Timed out while sending commands')
        self.loseConnection()

    def request_exit_status(self, data):
        status = struct.unpack('>L', data)[0]
        log.msg('[%s] Exit status: %s' % (self.device, status))

class TriggerSSHGenericChannel(TriggerSSHChannelBase):
    """
    An SSH channel using all of the Trigger defaults to interact with network
    devices that implement SSH without any tricks.

    Currently A10, Cisco, Brocade, NetScreen can simply use this. Nice!

    Before you create your own subclass, see if you can't use me as-is!
    """

class TriggerSSHAsyncPtyChannel(TriggerSSHChannelBase):
    """
    An SSH channel that requests a non-interactive pty intended for async
    usage.

    Some devices won't allow a shell without a pty, so we have to do a
    'pty-req'.

    This is distinctly different from ~trigger.twister.TriggerSSHPtyChannel`
    which is intended for interactive end-user sessions.
    """
    def channelOpen(self, data):
        self._setup_channelOpen()

        # Request a pty even tho we are not actually using one.
        pr = session.packRequest_pty_req(os.environ['TERM'], (80, 24, 0, 0), '')
        self.conn.sendRequest(self, 'pty-req', pr)
        d = self.conn.sendRequest(self, 'shell', '', wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

class TriggerSSHCommandChannel(TriggerSSHChannelBase):
    """
    Run SSH commands on a system using 'exec'

    This will multiplex channels over a single connection. Because of the
    nature of the multiplexing setup, the master list of commands is stored on
    the SSH connection, and the state of each command is stored within each
    individual channel which feeds its result back to the factory.
    """
    def __init__(self, command, *args, **kwargs):
        super(TriggerSSHCommandChannel, self).__init__(*args, **kwargs)
        self.command = command
        self.result = None
        self.data = ''

    def channelOpen(self, data):
        """Do this when the channel opens."""
        self._setup_channelOpen()
        log.msg('[%s] Channel was opened' % self.device)
        d = self.conn.sendRequest(self, 'exec', common.NS(self.command),
                                  wantReply=True)
        d.addCallback(self._gotResponse)
        d.addErrback(self._ebShellOpen)

    def _gotResponse(self, _):
        """
        If the shell never establishes, this won't be called.
        """
        log.msg('[%s] CHANNEL %s: Exec finished.' % (self.device, self.id))
        self.conn.sendEOF(self)

    def _ebShellOpen(self, reason):
        log.msg('[%s] CHANNEL %s: Channel request failed: %s' % (self.device,
                                                                 reason,
                                                                 self.id))

    def dataReceived(self, bytes):
        self.data += bytes
        #log.msg('BYTES INFO: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft, self.localMaxPacket, len(bytes), len(self.data)))
        log.msg('[%s] BYTES RECV: %r' % (self.device, bytes))

    def eofReceived(self):
        log.msg('[%s] CHANNEL %s: EOF received.' % (self.device, self.id))
        result = self.data

        # By default we're checking for IOS-like errors because most vendors
        # fall under this category.
        if has_ioslike_error(result) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.CommandFailure(result)

        # Honor the command_interval and then send the next command
        else:
            self.result = result
            self.conn.transport.factory.results.append(self.result)
            self.send_next_command()

    def send_next_command(self):
        """Send the next command in the stack stored on the connection"""
        log.msg('[%s] CHANNEL %s: sending next command!' % (self.device, self.id))
        self.conn.send_command()

    def closeReceived(self):
        log.msg('[%s] CHANNEL %s: Close received.' % (self.device, self.id))
        self.loseConnection()

    def loseConnection(self):
        """Default loseConnection"""
        log.msg("[%s] LOSING CHANNEL CONNECTION" % self.device)
        channel.SSHChannel.loseConnection(self)

    def closed(self):
        log.msg('[%s] Channel %s closed' % (self.device, self.id))
        log.msg('[%s] CONN CHANNELS: %s' % (self.device,
                                            len(self.conn.channels)))

        # If we're out of channels, shut it down!
        if len(self.conn.transport.factory.results) == len(self.conn.commands):
            log.msg('[%s] RESULTS MATCHES COMMANDS SENT.' % self.device)
            self.conn.transport.loseConnection()

    def request_exit_status(self, data):
        exitStatus = int(struct.unpack('>L', data)[0])
        log.msg('[%s] Exit status: %s' % (self.device, exitStatus))

class TriggerSSHJunoscriptChannel(TriggerSSHChannelBase):
    """
    An SSH channel to execute Junoscript commands on a Juniper device running
    Junos.

    This completely assumes that we are the only channel in the factory (a
    TriggerJunoscriptFactory) and walks all the way back up to the factory for
    its arguments.
    """
    def channelOpen(self, data):
        """Do this when channel opens."""
        self._setup_channelOpen()
        self.conn.sendRequest(self, 'exec', common.NS('junoscript'))
        _xml = '<?xml version="1.0" encoding="us-ascii"?>\n'
        # TODO (jathan): Make the release version dynamic at some point
        _xml += '<junoscript version="1.0" hostname="%s" release="7.6R2.9">\n' % socket.getfqdn()
        self.write(_xml)
        self.xmltb = IncrementalXMLTreeBuilder(self._endhandler)

        self._send_next()

    def dataReceived(self, data):
        """Do this when we receive data."""
        log.msg('[%s] BYTES: %r' % (self.device, data))
        self.xmltb.feed(data)

    def _send_next(self):
        """Send the next command in the stack."""
        self.resetTimeout()

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
            log.msg('[%s] COMMAND: next command %s' % (self.device,
                                                       next_command))

        except StopIteration:
            log.msg('[%s] CHANNEL: out of commands, closing connection...' %
                    self.device)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            rpc = Element('rpc')
            rpc.append(next_command)
            ElementTree(rpc).write(self)

    def _endhandler(self, tag):
        """Do this when the XML stream ends."""
        if tag.tag != '{http://xml.juniper.net/xnm/1.1/xnm}rpc-reply':
            return None # hopefully it's interior to an <rpc-reply>
        self.results.append(tag)

        if has_junoscript_error(tag) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, tag))
            self.factory.err = exceptions.JunoscriptCommandFailure(tag)
            self.loseConnection()
            return None

        # Honor the command_interval and then send the next command in the
        # stack
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            reactor.callLater(self.command_interval, self._send_next)

class TriggerSSHNetscalerChannel(TriggerSSHChannelBase):
    """
    An SSH channel to interact with Citrix NetScaler hardware.

    It's almost a generic SSH channel except that we must check for errors
    first, because a prompt is not returned when an error is received. This had
    to be accounted for in the ``dataReceived()`` method.
    """
    def dataReceived(self, bytes):
        """Do this when we receive data."""
        self.data += bytes
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        #log.msg('BYTES: (left: %r, max: %r, bytes: %r, data: %r)' %
        #        (self.remoteWindowLeft, self.localMaxPacket, len(bytes), len(self.data)))

        # We have to check for errors first, because a prompt is not returned
        # when an error is received like on other systems.
        if has_netscaler_error(self.data):
            err = self.data
            if not self.with_errors:
                log.msg('[%s] Command failed: %r' % (self.device, err))
                self.factory.err = exceptions.CommandFailure(err)
                self.loseConnection()
                return None
            else:
                self.results.append(err)
                self._send_next()

        m = self.prompt.search(self.data)
        if not m:
            #log.msg('STATE: prompt match failure', debug=True)
            return None
        log.msg('[%s] STATE: prompt %r' % (self.device, m.group()))

        result = self.data[:m.start()] # Strip ' Done\n' from results.

        if self.initialized:
            self.results.append(result)

        if self.command_interval:
            log.msg('[%s] Waiting %s seconds before sending next command' %
                    (self.device, self.command_interval))
        reactor.callLater(self.command_interval, self._send_next)

#==================
# XML Stuff (for Junoscript)
#==================
class IncrementalXMLTreeBuilder(XMLTreeBuilder):
    """
    Version of XMLTreeBuilder that runs a callback on each tag.

    We need this because JunoScript treats the entire session as one XML
    document. IETF NETCONF fixes that.
    """
    def __init__(self, callback, *args, **kwargs):
        self._endhandler = callback
        XMLTreeBuilder.__init__(self, *args, **kwargs)

    def _end(self, tag):
        """Do this when we're out of XML!"""
        return self._endhandler(XMLTreeBuilder._end(self, tag))

#==================
# Telnet Channels
#==================
class TriggerTelnetClientFactory(TriggerClientFactory):
    """
    Factory for a telnet connection.
    """
    def __init__(self, deferred, action, creds=None, loginpw=None,
                 enablepw=None, init_commands=None, device=None):
        self.protocol = TriggerTelnet
        self.action = action
        self.loginpw = loginpw
        self.enablepw = os.getenv('TRIGGER_ENABLEPW', enablepw)
        self.device = device
        self.action.factory = self
        TriggerClientFactory.__init__(self, deferred, creds, init_commands)

class TriggerTelnet(telnet.Telnet, telnet.ProtocolTransportMixin, TimeoutMixin):
    """
    Telnet-based session login state machine. Primarily used by IOS-like type
    devices.
    """
    def __init__(self, timeout=settings.TELNET_TIMEOUT):
        self.protocol = telnet.TelnetProtocol()
        self.waiting_for = [
            ('Username: ', self.state_username),                  # Most
            ('Please Enter Login Name  : ', self.state_username), # OLD Foundry
            ('User Name:', self.state_username),                  # Dell
            ('login: ', self.state_username),                     # Arista, Juniper
            ('Password: ', self.state_login_pw),
        ]
        self.data = ''
        self.applicationDataReceived = self.login_state_machine
        self.timeout = timeout
        self.setTimeout(self.timeout)
        telnet.Telnet.__init__(self)

    def enableRemote(self, option):
        """
        Allow telnet clients to enable options if for some reason they aren't
        enabled already (e.g. ECHO). (Ref: http://bit.ly/wkFZFg) For some reason
        Arista Networks hardware is the only vendor that needs this method
        right now.
        """
        #log.msg('[%s] enableRemote option: %r' % (self.host, option))
        log.msg('enableRemote option: %r' % option)
        return True

    def login_state_machine(self, bytes):
        """Track user login state."""
        self.host = self.transport.connector.host
        log.msg('[%s] CONNECTOR HOST: %s' % (self.host,
                                             self.transport.connector.host))
        self.data += bytes
        log.msg('[%s] STATE:  got data %r' % (self.host, self.data))
        for (text, next_state) in self.waiting_for:
            log.msg('[%s] STATE:  possible matches %r' % (self.host, text))
            if self.data.endswith(text):
                log.msg('[%s] Entering state %r' % (self.host,
                                                    next_state.__name__))
                self.resetTimeout()
                next_state()
                self.data = ''
                break

    def state_username(self):
        """After we've gotten username, check for password prompt."""
        self.write(self.factory.creds.username + '\n')
        self.waiting_for = [
            ('Password: ', self.state_password),
            ('Password:', self.state_password),  # Dell
        ]

    def state_password(self):
        """After we got password prompt, check for enabled prompt."""
        self.write(self.factory.creds.password + '\n')
        self.waiting_for = [
            ('#', self.state_logged_in),
            ('>', self.state_enable),
            ('> ', self.state_logged_in),             # Juniper
            ('\n% ', self.state_percent_error),
            ('# ', self.state_logged_in),             # Dell
            ('\nUsername: ', self.state_raise_error), # Cisco
            ('\nlogin: ', self.state_raise_error),    # Arista, Juniper
        ]

    def state_logged_in(self):
        """
        Once we're logged in, exit state machine and pass control to the
        action.
        """
        self.setTimeout(None)
        data = self.data.lstrip('\n')
        log.msg('[%s] state_logged_in, DATA: %r' % (self.host, data))
        del self.waiting_for, self.data

        # Run init_commands
        self.factory._init_commands(protocol=self) # We are the protocol

        # Control passed here :)
        action = self.factory.action
        action.transport = self
        self.applicationDataReceived = action.dataReceived
        self.connectionLost = action.connectionLost
        action.write = self.write
        action.loseConnection = self.loseConnection
        action.connectionMade()
        action.dataReceived(data)

    def state_enable(self):
        """
        Special Foundry breakage because they don't do auto-enable from
        TACACS by default. Use 'aaa authentication login privilege-mode'.
        Also, why no space after the Password: prompt here?
        """
        log.msg("[%s] ENABLE: Sending command: enable" % self.host)
        self.write('enable\n')
        self.waiting_for = [
            ('Password: ', self.state_enable_pw), # Foundry
            ('Password:', self.state_enable_pw),  # Dell
        ]

    def state_login_pw(self):
        """Pass the login password from the factory or NetDevices"""
        if self.factory.loginpw:
            pw = self.factory.loginpw
        else:
            from trigger.netdevices import NetDevices
            pw = NetDevices().find(self.host).loginPW

        # Workaround to avoid TypeError when concatenating 'NoneType' and
        # 'str'. This *should* result in a LoginFailure.
        if pw is None:
            pw = ''

        #log.msg('Sending password %s' % pw)
        self.write(pw + '\n')
        self.waiting_for = [('>', self.state_enable),
                            ('#', self.state_logged_in),
                            ('\n% ', self.state_percent_error),
                            ('incorrect password.', self.state_raise_error)]

    def state_enable_pw(self):
        """Pass the enable password from the factory or NetDevices"""
        if self.factory.enablepw:
            pw = self.factory.enablepw
        else:
            from trigger.netdevices import NetDevices
            pw = NetDevices().find(self.host).enablePW
        #log.msg('Sending password %s' % pw)
        self.write(pw + '\n')
        self.waiting_for = [('#', self.state_logged_in),
                            ('\n% ', self.state_percent_error),
                            ('incorrect password.', self.state_raise_error)]

    def state_percent_error(self):
        """
        Found a % error message. Don't return immediately because we
        don't have the error text yet.
        """
        self.waiting_for = [('\n', self.state_raise_error)]

    def state_raise_error(self):
        """Do this when we get a login failure."""
        self.waiting_for = []
        log.msg('Failed logging into %s' % self.transport.connector.host)
        self.factory.err = exceptions.LoginFailure('%r' % self.data.rstrip())
        self.loseConnection()

    def timeoutConnection(self):
        """Do this when we timeout logging in."""
        log.msg('[%s] Timed out while logging in' % self.transport.connector.host)
        self.factory.err = exceptions.LoginTimeout('Timed out while logging in')
        self.loseConnection()

class IoslikeSendExpect(protocol.Protocol, TimeoutMixin):
    """
    Action for use with TriggerTelnet as a state machine.

    Take a list of commands, and send them to the device until we run out or
    one errors. Wait for a prompt after each.
    """
    def __init__(self, device, commands, incremental=None, with_errors=False,
                 timeout=None, command_interval=0):
        self.device = device
        self._commands = commands
        self.commanditer = iter(commands)
        self.incremental = incremental
        self.with_errors = with_errors
        self.timeout = timeout
        self.command_interval = command_interval
        self.prompt =  re.compile(settings.IOSLIKE_PROMPT_PAT)
        self.startup_commands = copy.copy(self.device.startup_commands)
        log.msg('[%s] My initialize commands: %r' % (self.device,
                                                     self.startup_commands))
        self.initialized = False

    def connectionMade(self):
        """Do this when we connect."""
        self.setTimeout(self.timeout)
        self.results = self.factory.results = []
        self.data = ''
        log.msg('[%s] connectionMade, data: %r' % (self.device, self.data))

        # Don't call _send_next, since we expect to see a prompt, which
        # will kick off initialization.

    def dataReceived(self, bytes):
        """Do this when we get data."""
        log.msg('[%s] BYTES: %r' % (self.device, bytes))
        self.data += bytes

        # See if the prompt matches, and if it doesn't, see if it is waiting
        # for more input (like a [y/n]) prompt), and continue, otherwise return
        # None
        m = self.prompt.search(self.data)
        if not m:
            # If the prompt confirms set the index to the matched bytes,
            if is_awaiting_confirmation(self.data):
                log.msg('[%s] Got confirmation prompt: %r' % (self.device,
                                                              self.data))
                prompt_idx = self.data.find(bytes)
            else:
                return None
        else:
            # Or just use the matched regex object...
            prompt_idx = m.start()

        result = self.data[:prompt_idx]
        # Trim off the echoed-back command.  This should *not* be necessary
        # since the telnet session is in WONT ECHO.  This is confirmed with
        # a packet trace, and running self.transport.dont(ECHO) from
        # connectionMade() returns an AlreadyDisabled error.  What's up?
        log.msg('[%s] result BEFORE: %r' % (self.device, result))
        result = result[result.find('\n')+1:]
        log.msg('[%s] result AFTER: %r' % (self.device, result))

        if self.initialized:
            self.results.append(result)

        if has_ioslike_error(result) and not self.with_errors:
            log.msg('[%s] Command failed: %r' % (self.device, result))
            self.factory.err = exceptions.IoslikeCommandFailure(result)
            self.loseConnection()
        else:
            if self.command_interval:
                log.msg('[%s] Waiting %s seconds before sending next command' %
                        (self.device, self.command_interval))
            reactor.callLater(self.command_interval, self._send_next)

    def _send_next(self):
        """Send the next command in the stack."""
        self.data = ''
        self.resetTimeout()

        if not self.initialized:
            log.msg('[%s] Not initialized, sending startup commands' %
                    self.device)
            if self.startup_commands:
                next_init = self.startup_commands.pop(0)
                log.msg('[%s] Sending initialize command: %r' % (self.device,
                                                                 next_init))
                self.write(next_init.strip() + self.device.delimiter)
                return None
            else:
                log.msg('[%s] Successfully initialized for command execution' %
                        self.device)
                self.initialized = True

        if self.incremental:
            self.incremental(self.results)

        try:
            next_command = self.commanditer.next()
        except StopIteration:
            log.msg('[%s] No more commands to send, disconnecting...' %
                    self.device)
            self.loseConnection()
            return None

        if next_command is None:
            self.results.append(None)
            self._send_next()
        else:
            log.msg('[%s] Sending command %r' % (self.device, next_command))
            self.write(next_command + self.device.delimiter)

    def timeoutConnection(self):
        """Do this when we timeout."""
        log.msg('[%s] Timed out while sending commands' % self.device)
        self.factory.err = exceptions.CommandTimeout('Timed out while sending commands')
        self.loseConnection()

########NEW FILE########
__FILENAME__ = cli
#coding=utf-8

"""
Command-line interface utilities for Trigger tools. Intended for re-usable
pieces of code like user prompts, that don't fit in other utils modules.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2006-2012, AOL Inc.; 2013 Salesforce.com'

import datetime
from fcntl import ioctl
import os
import pwd
from pytz import timezone
import struct
import sys
import termios
import time
import tty

# Exports
__all__ = ('yesno', 'get_terminal_width', 'get_terminal_size', 'Whirlygig',
           'NullDevice', 'print_severed_head', 'min_sec', 'pretty_time',
           'proceed', 'get_user')


# Functions
def yesno(prompt, default=False, autoyes=False):
    """
    Present a yes-or-no prompt, get input, and return a boolean.

    The ``default`` argument is ignored if ``autoyes`` is set.

    :param prompt:
        Prompt text

    :param default:
        Yes if True; No if False

    :param autoyes:
        Automatically return True

    Default behavior (hitting "enter" returns ``False``)::

        >>> yesno('Blow up the moon?')
        Blow up the moon? (y/N)
        False

    Reversed behavior (hitting "enter" returns ``True``)::

        >>> yesno('Blow up the moon?', default=True)
        Blow up the moon? (Y/n)
        True

    Automatically return ``True`` with ``autoyes``; no prompt is displayed::

        >>> yesno('Blow up the moon?', autoyes=True)
        True
    """
    if autoyes:
        return True

    sys.stdout.write(prompt)
    if default:
        sys.stdout.write(' (Y/n) ')
    else:
        sys.stdout.write(' (y/N) ')
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    attr = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        yn = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, attr)
        print ''

    if yn in ('y', 'Y'):
        return True
    elif yn in ('n', 'N'):
        return False
    else:
        return default

def proceed():
    """Present a proceed prompt. Return ``True`` if Y, else ``False``"""
    return raw_input('\nDo you wish to proceed? [y/N] ').lower().startswith('y')

def get_terminal_width():
    """Find and return stdout's terminal width, if applicable."""
    try:
        width = struct.unpack("hhhh", ioctl(1, termios.TIOCGWINSZ, ' '*8))[1]
    except IOError:
        width = sys.maxint

    return width

def get_terminal_size():
    """Find and return stdouts terminal size as (height, width)"""
    rows, cols = os.popen('stty size', 'r').read().split()
    return rows, cols

def get_user():
    """Return the name of the current user."""
    return pwd.getpwuid(os.getuid())[0]

def print_severed_head():
    """
    Prints a demon holding a severed head. Best used when things go wrong, like
    production-impacting network outages caused by fat-fingered ACL changes.

    Thanks to Jeff Sullivan for this best error message ever.
    """
    print r"""

                                                                _( (~\
         _ _                        /                          ( \> > \
     -/~/ / ~\                     :;                \       _  > /(~\/
    || | | /\ ;\                   |l      _____     |;     ( \/    > >
    _\\)\)\)/ ;;;                  `8o __-~     ~\   d|      \      //
   ///(())(__/~;;\                  "88p;.  -. _\_;.oP        (_._/ /
  (((__   __ \\   \                  `>,% (\  (\./)8"         ;:'  i
  )))--`.'-- (( ;,8 \               ,;%%%:  ./V^^^V'          ;.   ;.
  ((\   |   /)) .,88  `: ..,,;;;;,-::::::'_::\   ||\         ;[8:   ;
   )|  ~-~  |(|(888; ..``'::::8888oooooo.  :\`^^^/,,~--._    |88::  |
   |\ -===- /|  \8;; ``:.      oo.8888888888:`((( o.ooo8888Oo;:;:'  |
   |_~-___-~_|   `-\.   `        `o`88888888b` )) 888b88888P""'     ;
   ; ~~~~;~~         "`--_`.       b`888888888;(.,"888b888"  ..::;-'
     ;      ;              ~"-....  b`8888888:::::.`8888. .:;;;''
        ;    ;                 `:::. `:::OOO:::::::.`OO' ;;;''
   :       ;                     `.      "``::::::''    .'
      ;                           `.   \_              /
    ;       ;                       +:   ~~--  `:'  -';    ACL LOADS FAILED
                                     `:         : .::/
        ;                            ;;+_  :::. :..;;;         YOU LOSE
                                     ;;;;;;,;;;;;;;;,;

"""

def pretty_time(t):
    """
    Print a pretty version of timestamp, including timezone info. Expects
    the incoming datetime object to have proper tzinfo.

    :param t:
        A ``datetime.datetime`` object

    >>> import datetime
    >>> from pytz import timezone
    >>> localzone = timezone('US/Eastern')
    <DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>
    >>> t = datetime.datetime.now(localzone)
    >>> print t
    2011-07-19 12:40:30.820920-04:00
    >>> print pretty_time(t)
    09:40 PDT
    >>> t = datetime.datetime(2011,07,20,04,13,tzinfo=localzone)
    >>> print t
    2011-07-20 04:13:00-05:00
    >>> print pretty_time(t)
    tomorrow 02:13 PDT
    """
    from trigger.conf import settings
    localzone = timezone(os.environ.get('TZ', settings.BOUNCE_DEFAULT_TZ))
    t = t.astimezone(localzone)
    midnight = datetime.datetime.combine(datetime.datetime.now(), datetime.time(tzinfo=localzone))
    midnight += datetime.timedelta(1)
    if t < midnight:
        return t.strftime('%H:%M %Z')
    elif t < midnight + datetime.timedelta(1):
        return t.strftime('tomorrow %H:%M %Z')
    elif t < midnight + datetime.timedelta(6):
        return t.strftime('%A %H:%M %Z')
    else:
        return t.strftime('%Y-%m-%d %H:%M %Z')

def min_sec(secs):
    """
    Takes an epoch timestamp and returns string of minutes:seconds.

    :param secs:
        Timestamp (in seconds)

    >>> import time
    >>> start = time.time()  # Wait a few seconds
    >>> finish = time.time()
    >>> min_sec(finish - start)
    '0:11'
    """
    secs = int(secs)
    return '%d:%02d' % (secs / 60, secs % 60)

def setup_tty_for_pty(func):
    """
    Sets up tty for raw mode while retaining original tty settings and then
    starts the reactor to connect to the pty. Upon exiting pty, restores
    original tty settings.

    :param func:
        The callable to run after the tty is ready, such as ``reactor.run``
    """
    # Preserve original tty settings
    stdin_fileno = sys.stdin.fileno()
    old_ttyattr = tty.tcgetattr(stdin_fileno)

    try:
        # Enter raw mode on the local tty.
        tty.setraw(stdin_fileno)
        raw_ta = tty.tcgetattr(stdin_fileno)
        raw_ta[tty.LFLAG] |= tty.ISIG
        raw_ta[tty.OFLAG] |= tty.OPOST | tty.ONLCR

        # Pass ^C through so we can abort traceroute, etc.
        raw_ta[tty.CC][tty.VINTR] = '\x18'  # ^X is the new ^C

        # Ctrl-Z is used by a lot of vendors to exit config mode
        raw_ta[tty.CC][tty.VSUSP] = 0       # disable ^Z
        tty.tcsetattr(stdin_fileno, tty.TCSANOW, raw_ta)

        # Execute our callable here
        func()

    finally:
        # Restore original tty settings
        tty.tcsetattr(stdin_fileno, tty.TCSANOW, old_ttyattr)

def update_password_and_reconnect(hostname):
    """
    Prompts the user to update their password and reconnect to the target
    device

    :param hostname: Hostname of the device to connect to.
    """
    if yesno('Authentication failed, would you like to update your password?',
             default=True):
        from trigger import tacacsrc
        tacacsrc.update_credentials(hostname)
        if yesno('\nReconnect to %s?' % hostname, default=True):
            # Replaces the current process w/ same pid
            args = [sys.argv[0]]
            for arg in ('-o', '--oob'):
                if arg in sys.argv:
                    idx = sys.argv.index(arg)
                    args.append(sys.argv[idx])
                    break
            args.append(hostname)
            os.execl(sys.executable, sys.executable, *args)

# Classes
class NullDevice(object):
    """
    Used to supress output to ``sys.stdout`` (aka ``print``).

    Example::

        >>> from trigger.utils.cli import NullDevice
        >>> import sys
        >>> print "1 - this will print to STDOUT"
        1 - this will print to STDOUT
        >>> original_stdout = sys.stdout  # keep a reference to STDOUT
        >>> sys.stdout = NullDevice()     # redirect the real STDOUT
        >>> print "2 - this won't print"
        >>>
        >>> sys.stdout = original_stdout  # turn STDOUT back on
        >>> print "3 - this will print to SDTDOUT"
        3 - this will print to SDTDOUT
    """
    def write(self, s): pass

class Whirlygig(object):
    """
    Prints a whirlygig for use in displaying pending operation in a command-line tool.
    Guaranteed to make the user feel warm and fuzzy and be 1000% bug-free.

    :param start_msg: The status message displayed to the user (e.g. "Doing stuff:")
    :param done_msg: The completion message displayed upon completion (e.g. "Done.")
    :param max: Integer of the number of whirlygig repetitions to perform

    Example::

        >>> Whirlygig("Doing stuff:", "Done.", 12).run()
    """

    def __init__(self, start_msg="", done_msg="", max=100):
        self.unbuff = os.fdopen(sys.stdout.fileno(), 'w', 0)
        self.start_msg = start_msg
        self.done_msg = done_msg
        self.max = max
        self.whirlygig = ['|', '/', '-', '\\']
        self.whirl    = self.whirlygig[:]
        self.first = False

    def do_whirl(self, whirl):
        if not self.first:
            self.unbuff.write(self.start_msg + "  ")
            self.first = True
        self.unbuff.write('\b%s' % whirl.pop(0))

    def run(self):
        """Executes the whirlygig!"""
        cnt = 1
        while cnt <= self.max:
            try:
                self.do_whirl(self.whirl)
            except IndexError:
                self.whirl = self.whirlygig[:]
            time.sleep(.1)
            cnt += 1
        print '\b' + self.done_msg

########NEW FILE########
__FILENAME__ = importlib
# -*- coding: utf-8 -*-

"""
Utils to import modules.

Taken verbatim from ``django.utils.importlib`` in Django 1.4.
"""

import os
import sys


# Exports
__all__ = ('import_module', 'import_module_from_path')


# Functions
def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)

def import_module(name, package=None):
    """
    Import a module and return the module object.

    The ``package`` argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

def import_module_from_path(full_path, global_name):
    """
    Import a module from a file path and return the module object.

    Allows one to import from anywhere, something ``__import__()`` does not do.
    The module is added to ``sys.modules`` as ``global_name``.

    :param full_path:
        The absolute path to the module .py file

    :param global_name:
        The name assigned to the module in sys.modules. To avoid
        confusion, the global_name should be the same as the variable to which
        you're assigning the returned module.
    """
    path, filename = os.path.split(full_path)
    module, ext = os.path.splitext(filename)
    sys.path.append(path)

    try:
        mymodule = __import__(module)
        sys.modules[global_name] = mymodule
    except ImportError:
        raise ImportError('Module could not be imported from %s.' % full_path)
    finally:
        del sys.path[-1]

    return mymodule

########NEW FILE########
__FILENAME__ = network
# -*- coding: utf-8 -*-

"""
Functions that perform network-based things like ping, port tests, etc.
"""

__author__ = 'Jathan McCollum, Eileen Watson'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2013, AOL Inc.; 2013-2014 Salesforce.com'

import commands
import re
import socket
import telnetlib
from trigger.conf import settings


VALID_HOST_RE = re.compile("^[a-z0-9\-\.]+$")


# Exports
__all__ = ('ping', 'test_tcp_port', 'test_ssh', 'address_is_internal')


# Functions
def ping(host, count=1, timeout=5):
    """
    Returns pass/fail for a ping. Supports POSIX only.

    :param host:
        Hostname or address

    :param count:
        Repeat count

    :param timeout:
        Timeout in seconds

    >>> from trigger.utils import network
    >>> network.ping('aol.com')
    True
    >>> network.ping('192.168.199.253')
    False
    """
    # Make the command silent even for bad input
    if not VALID_HOST_RE.findall(host):
        return False

    ping_command = "ping -q -c%d -W%d %s" % (count, timeout, host)
    status, results = commands.getstatusoutput(ping_command)

    # Linux RC: 0 = success, 256 = failure, 512 = unknown host
    # Darwin RC: 0 = success, 512 = failure, 17408 = unknown host
    return status == 0

def test_tcp_port(host, port=23, timeout=5, check_result=False,
                  expected_result=''):
    """
    Attempts to connect to a TCP port. Returns a Boolean.

    If ``check_result`` is set, the first line of output is retreived from the
    connection and the starting characters must match ``expected_result``.

    :param host:
        Hostname or address

    :param port:
        Destination port

    :param timeout:
        Timeout in seconds

    :param check_result:
        Whether or not to do a string check (e.g. version banner)

    :param expected_result:
        The expected result!

    >>> test_tcp_port('aol.com', 80)
    True
    >>> test_tcp_port('aol.com', 12345)
    False
    """
    try:
        t = telnetlib.Telnet(host, port, timeout)
        if check_result:
            result = t.read_some()
            t.close()
            return result.startswith(expected_result)
    except (socket.timeout, socket.error):
        return False

    t.close()
    return True

def test_ssh(host, port=22, timeout=5, version=('SSH-1.99', 'SSH-2.0')):
    """
    Connect to a TCP port and confirm the SSH version. Defaults to SSHv2.

    Note that the default of ('SSH-1.99', 'SSH-2.0') both indicate SSHv2 per
    RFC 4253. (Ref: http://en.wikipedia.org/wiki/Secure_Shell#Version_1.99)

    :param host:
        Hostname or address

    :param port:
        Destination port

    :param timeout:
        Timeout in seconds

    :param version:
        The SSH version prefix (e.g. "SSH-2.0"). This may also be a tuple of
        prefixes.

    >>> test_ssh('localhost')
    True
    >>> test_ssh('localhost', version='SSH-1.5')
    False
    """
    return test_tcp_port(host, port, timeout, check_result=True,
                         expected_result=version)

def address_is_internal(ip):
    """
    Determines if an IP address is internal to your network. Relies on
    networks specified in :mod:`settings.INTERNAL_NETWORKS`.

    :param ip:
        IP address to test.

    >>> address_is_internal('1.1.1.1')
    False
    """
    for i in settings.INTERNAL_NETWORKS:
        if ip in i:
            return True
    return False

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
Basic functions for sending notifications.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

from . import handlers


# Exports
__all__ = ('send_email', 'send_notification')


# Functions
def send_email(addresses, subject, body, sender, mailhost='localhost'):
    """
    Sends an email to a list of recipients. Returns ``True`` when done.

    :param addresses:
        List of email recipients

    :param subject:
        The email subject

    :param body:
        The email body

    :param sender:
        The email sender

    :param mailhost:
        (Optional) Mail server address
    """
    import smtplib
    for email in addresses:
        header = 'From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n' % \
            (sender, email, subject )
        message = header + body
        server = smtplib.SMTP(mailhost)
        server.sendmail(sender, email, message)
        server.quit()

    return True

def send_notification(*args, **kwargs):
    """
    Simple entry point into `~trigger.utils.notifications.handlers.notify` that
    takes any arguments and tries to handle them to send a notification.

    This relies on handlers to be definied within
    ``settings.NOTIFICATION_HANDLERS``.
    """
    return handlers.notify(*args, **kwargs)

########NEW FILE########
__FILENAME__ = events
# -*- coding: utf-8 -*-

"""
Event objects for the notification system.

These are intended to be used within event handlers such as
`~trigger.utils.notifications.handlers.email_handler()`.

If not customized within :setting:`NOTIFICATION_HANDLERS`, the default
notification type is an `~trigger.utils.notification.events.EmailEvent` that is
handled by `~trigger.utils.notifications.handlers.email_handler`.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

import socket
from trigger.conf import settings


# Exports
__all__ = ('Event', 'Notification', 'EmailEvent')


# Classes
class Event(object):
    """
    Base class for events.
   
    It just populates the attribute dict with all keyword arguments thrown at
    the constructor.

    All ``Event`` objects are expected to have a ``.handle()`` method that
    willl be called by a handler function. Any user-defined event objects must
    have a working ``.handle()`` method that returns ``True`` upon success or
    ``None`` upon a failure when handling the event passed to it.

    If you specify ``required_args``, these must have a value other than
    ``None`` when passed to the constructor.
    """
    required_args = ()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs) # Brute force wins!
        local_vars = self.__dict__
        for var, value in local_vars.iteritems():
            if var in self.required_args and value is None:
                raise SyntaxError('`%s` is a required argument' % var)

    def __repr__(self):
        return '<%s>' % self.__class__.__name__

    def handle(self):
        raise NotImplementedError('Define me in your subclass!')

class Notification(Event):
    """
    Base class for notification events.

    The ``title`` and ``message`` arguments are the only two that are required.
    This is to simplify the interface when sending notifications and will cause
    notifications to send from the default ``sender to the default
    ``recipients`` that are specified withing the global settings.

    If ``sender`` or ``recipients`` are specified, they will override the
    global defaults.

    Note that this base class has no ``.handle()`` method defined.

    :param title:
        The title/subject of the notification
  
    :param message:
        The message/body of the notification

    :param sender:
        A string representing the sender of the notification (such as an email
        address or a hostname)
  
    :param recipients:
        An iterable containing strings representing the recipients of of the
        notification (such as a list of emails or hostnames)
  
    :param event_status:
        Whether this event is a `failure` or a `success`
    """
    required_args = ('title', 'message')
    status_map = {
            'success': settings.SUCCESS_RECIPIENTS,
            'failure': settings.FAILURE_RECIPIENTS,
    }
    default_sender = settings.NOTIFICATION_SENDER

    def __init__(self, title=None, message=None, sender=None, recipients=None,
                 event_status='failure', **kwargs):
        self.title = title
        self.message = message

        # If the sender isn't specified, use the global sender
        if sender is None:
            sender = self.default_sender
        self.sender = sender

        # We want to know whether we're sending a failure or success email
        if event_status not in self.status_map:
            raise SyntaxError('`event_status` must be in `status_map`')
        self.event_status = event_status

        # If recipients aren't specified, use the global success/failure
        # recipients
        if recipients is None:
            recipients = self.status_map.get(self.event_status)
        self.recipients = recipients

        super(Notification, self).__init__(**kwargs)
        self.kwargs = kwargs

class EmailEvent(Notification):
    """
    An email notification event.
    """
    default_sender = settings.EMAIL_SENDER
    status_map = {
            'success': settings.SUCCESS_EMAILS,
            'failure': settings.FAILURE_EMAILS,
    }
    mailhost = 'localhost'

    def handle(self):
        from trigger.utils.notifications import send_email
        try:
            # This should return True upon successfully sending email
            e = self
            return send_email(addresses=e.recipients, subject=e.title,
                              body=e.message, sender=e.sender,
                              mailhost=e.mailhost)
        except Exception as err:
            print 'Got exception', err
            return None

########NEW FILE########
__FILENAME__ = handlers
# -*- coding: utf-8 -*-

"""
Handlers for event notifications.

Handlers are specified by full module path within
``settings.NOTIFICATION_HANDLERS``. These are then imported and registered
internally in this module.

The primary public interface to this module is
`~trigger.utils.notifications.handlers.notify` which is in turn called by
`~trigger.utils.notifications.send_notification` to send notifications.

Handlers should return ``True`` if they have performed the desired action
or ``None`` if they have not.

A handler can either define its own custom behavior, or leverage a custom
`~trigger.utils.notifications.events.Event` object. The goal was to provide a
simple public interface to customizing event notifications.

If not customized within :setting:`NOTIFICATION_HANDLERS`, the default
notification type is an `~trigger.utils.notification.events.EmailEvent` that is
handled by `~trigger.utils.notifications.handlers.email_handler`.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2012, AOL Inc.'

from trigger import exceptions
from trigger.utils.importlib import import_module
from . import events

# Globals
# This is where handler functions are stored.
_registered_handlers = []

# And whether they've been successfully registered
HANDLERS_REGISTERED = False


# Exports
__all__ = ('email_handler', 'notify')


# Functions
def email_handler(*args, **kwargs):
    """
    Default email notification handler.
    """
    try:
        event = events.EmailEvent(*args, **kwargs)
    except Exception as err:
        return None
    else:
        return event.handle()

def _register_handlers():
    """
    Walk thru the handlers specified in ``settings.NOTIFICATION_HANDLERS`` and
    register them internally.

    Any built-in event handlers need to be defined above this function.
    """
    global HANDLERS_REGISTERED
    from trigger.conf import settings

    for handler_path in settings.NOTIFICATION_HANDLERS:
        # Get the module and func name
        try:
            h_module, h_funcname = handler_path.rsplit('.', 1)
        except ValueError:
            raise exceptions.ImproperlyConfigured("%s isn't a handler module" % handler_path)

        # Import the module and get the module object
        try:
            mod = import_module(h_module)
        except ImportError as err:
            raise exceptions.ImproperlyConfigured('Error importing handler %s: "%s"' % (h_module, err))

        # Get the handler function
        try:
            handler = getattr(mod, h_funcname)
        except AttributeError:
            raise exceptions.ImproperlyConfigured('Handler module "%s" does not define a "%s" function' % (h_module, h_funcname))

        # Register the handler function
        if handler not in _registered_handlers:
            _registered_handlers.append(handler)

    HANDLERS_REGISTERED = True
_register_handlers() # Do this on init

def notify(*args, **kwargs):
    """
    Iterate thru registered handlers to handle events and send notifications.

    Handlers should return ``True`` if they have performed the desired action
    or ``None`` if they have not.
    """
    if not HANDLERS_REGISTERED:
        _register_handlers()

    for handler in _registered_handlers:
        # Pass the event args to the handler
        #print 'Sending %s, %s to %s' % (args, kwargs, handler)
        try:
            result = handler(*args, **kwargs)
        except Exception as err:
            #print 'Got exception: %s' % err
            continue
        else:
            if result is not None:
                return True # Event was handled!
            else:
                continue
            
    # We don't want to get to this point
    raise RuntimeError('No handlers succeeded for this event: %s' % event)

########NEW FILE########
__FILENAME__ = rcs
#coding=utf-8

"""
Provides a CVS like wrapper for local RCS (Revision Control System) with common commands.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2009-2011, AOL Inc.'

import commands
import os
import time


# Exports
__all__ = ('RCS',)


# Classes
class RCS(object):
    """
    Simple wrapper for CLI ``rcs`` command. An instance is bound to a file.

    :param file: The filename (or path) to use
    :param create: If set, create the file if it doesn't exist

    >>> from trigger.utils.rcs import RCS
    >>> rcs = RCS('foo')
    >>> rcs.lock()
    True
    >>> f = open('foo', 'w')
    >>> f.write('bar\\n')
    >>> f.close()
    >>> rcs.checkin('This is my commit message')
    True
    >>> print rcs.log()
    RCS file: RCS/foo,v
    Working file: foo
    head: 1.2
    branch:
    locks: strict
    access list:
    symbolic names:
    keyword substitution: kv
    total revisions: 2;     selected revisions: 2
    description:
    ----------------------------
    revision 1.2
    date: 2011/07/08 21:01:28;  author: jathan;  state: Exp;  lines: +1 -0
    This is my commit message
    ----------------------------
    revision 1.1
    date: 2011/07/08 20:56:53;  author: jathan;  state: Exp;
    first commit
    """
    def __init__(self, filename, create=True):
        self.locked = False
        self.filename = filename

        if not os.path.exists(filename):
            if not create:
                self.filename = None
                return None
            try:
                f = open(self.filename, 'w')
            except:
                return None
            f.close()
            if not self.checkin(initial=True):
                return None

    def checkin(self, logmsg='none', initial=False, verbose=False):
        """
        Perform an RCS checkin. If successful this also unlocks the file, so
        there is no need to unlock it afterward.

        :param logmsg: The RCS commit message
        :param initial: Initialize a new RCS file, but do not deposit any revision
        :param verbose: Print command output

        >>> rcs.checkin('This is my commit message')
        True
        """
        if initial:
            cmd = 'ci -m"first commit" -t- -i %s' % self.filename
        else:
            cmd = 'ci -u -m"%s" %s' % (logmsg, self.filename)
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False

        return True

    def lock(self, verbose=False):
        """
        Perform an RCS checkout with lock. Returns boolean of whether lock
        was sucessful.

        :param verbose: Print command output

        >>> rcs.lock()
        True
        """
        cmd = 'co -f -l %s' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False
        
        self.locked = True
        return True

    def unlock(self, verbose=False):
        """
        Perform an RCS checkout with unlock (for cancelling changes).

        :param verbose: Print command output

        >>> rcs.unlock()
        True
        """
        cmd = 'co -f -u %s' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if verbose:
            print output

        if status > 0:
            return False
        
        self.locked = False
        return True

    def lock_loop(self, callback=None, timeout=5, verbose=False):
        """
        Keep trying to lock the file until a lock is obtained.

        :param callback: The function to call after lock is complete
        :param timeout: How long to sleep between lock attempts
        :param verbose: Print command output

        Default:
            >>> rcs.lock_loop(timeout=1) 
            Sleeping to wait for the lock on the file: foo
            Sleeping to wait for the lock on the file: foo

        Verbose:
            >>> rcs.lock_loop(timeout=1, verbose=True)
            RCS/foo,v  -->  foo
            co: RCS/foo,v: Revision 1.2 is already locked by joe.
            Sleeping to wait for the lock on the file: foo
            RCS/foo,v  -->  foo
            co: RCS/foo,v: Revision 1.2 is already locked by joe.
        """
        while not self.lock(verbose=verbose):
            print 'Sleeping to wait for the lock on the file: %s' % self.filename
            time.sleep(timeout)
            if callback:
                callback()
        return True

    def log(self):
        """Returns the RCS log as a string (see above)."""
        cmd = 'rlog %s 2>&1' % self.filename
        status, output = commands.getstatusoutput(cmd)

        if status > 0:
            return None

        return output

########NEW FILE########
__FILENAME__ = url
"""
Utilities for parsing/handling URLs
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2013, AOL Inc.'
__version__ = '0.1'

from urllib import unquote
from urlparse import urlparse
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

def _parse_url(url):
    """
    Guts for `~trigger.utils.url.parse_url`.

    Based on Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH
    """
    parts = urlparse(url)
    scheme = parts.scheme
    port = parts.port or None
    hostname = parts.hostname
    path = parts.path or ''
    virtual_host = path[1:] if path and path[0] == '/' else path
    return (scheme, unquote(hostname or '') or None, port,
            unquote(parts.username or '') or None,
            unquote(parts.password or '') or None,
            unquote(path or '') or None,
            unquote(virtual_host or '') or None,
            unquote(parts.query or '') or None,
            dict(dict(parse_qsl(parts.query))))

def parse_url(url):
    """
    Given a ``url`` returns, a dict of its constituent parts.

    Based on Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH

    :param url:
        Any standard URL. (file://, https://, etc.)
    """
    scheme, host, port, user, passwd, path, vhost, qs, qs_dict = _parse_url(url)
    return dict(scheme=scheme, hostname=host, port=port, username=user,
                password=passwd, path=path, virtual_host=vhost,
                query=qs, **qs_dict)

if __name__ == '__main__':
    tests = (
        "https://username:password@myhost.aol.com:12345?limit=10&vendor=cisco#develop",
        "file:///usr/local/etc/netdevices.xml",
        '/usr/local/etc/netdevices.xml',
        'mysql://dbuser:dbpass@dbhost.com:3306/',
        'http://jathan:password@api.foo.com/netdevices/?limit=10&device_type=switch&vendor=cisco&format=json',
    )

    import pprint
    for test in tests:
        print test
        pprint.pprint(parse_url(test))
        print

########NEW FILE########
__FILENAME__ = xmltodict
#!/usr/bin/env python
"Makes working with XML feel like you are working with JSON"

from xml.parsers import expat
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
try: # pragma no cover
    from cStringIO import StringIO
except ImportError: # pragma no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
try: # pragma no cover
    from collections import OrderedDict
except ImportError: # pragma no cover
    OrderedDict = dict

try: # pragma no cover
    _basestring = basestring
except NameError: # pragma no cover
    _basestring = str
try: # pragma no cover
    _unicode = unicode
except NameError: # pragma no cover
    _unicode = str

__author__ = 'Martin Blech'
__version__ = '0.4.6'
__license__ = 'MIT'

class ParsingInterrupted(Exception): pass

class _DictSAXHandler(object):
    def __init__(self,
                 item_depth=0,
                 item_callback=lambda *args: True,
                 xml_attribs=True,
                 attr_prefix='@',
                 cdata_key='#text',
                 force_cdata=False,
                 cdata_separator='',
                 postprocessor=None,
                 dict_constructor=OrderedDict,
                 strip_whitespace=True):
        self.path = []
        self.stack = []
        self.data = None
        self.item = None
        self.item_depth = item_depth
        self.xml_attribs = xml_attribs
        self.item_callback = item_callback
        self.attr_prefix = attr_prefix
        self.cdata_key = cdata_key
        self.force_cdata = force_cdata
        self.cdata_separator = cdata_separator
        self.postprocessor = postprocessor
        self.dict_constructor = dict_constructor
        self.strip_whitespace = strip_whitespace

    def startElement(self, name, attrs):
        attrs = self.dict_constructor(zip(attrs[0::2], attrs[1::2]))
        self.path.append((name, attrs or None))
        if len(self.path) > self.item_depth:
            self.stack.append((self.item, self.data))
            if self.xml_attribs:
                attrs = self.dict_constructor(
                    (self.attr_prefix+key, value)
                    for (key, value) in attrs.items())
            else:
                attrs = None
            self.item = attrs or None
            self.data = None

    def endElement(self, name):
        if len(self.path) == self.item_depth:
            item = self.item
            if item is None:
                item = self.data
            should_continue = self.item_callback(self.path, item)
            if not should_continue:
                raise ParsingInterrupted()
        if len(self.stack):
            item, data = self.item, self.data
            self.item, self.data = self.stack.pop()
            if self.strip_whitespace and data is not None:
                data = data.strip() or None
            if data and self.force_cdata and item is None:
                item = self.dict_constructor()
            if item is not None:
                if data:
                    self.push_data(item, self.cdata_key, data)
                self.item = self.push_data(self.item, name, item)
            else:
                self.item = self.push_data(self.item, name, data)
        else:
            self.item = self.data = None
        self.path.pop()

    def characters(self, data):
        if not self.data:
            self.data = data
        else:
            self.data += self.cdata_separator + data

    def push_data(self, item, key, data):
        if self.postprocessor is not None:
            result = self.postprocessor(self.path, key, data)
            if result is None:
                return item
            key, data = result
        if item is None:
            item = self.dict_constructor()
        try:
            value = item[key]
            if isinstance(value, list):
                value.append(data)
            else:
                item[key] = [value, data]
        except KeyError:
            item[key] = data
        return item

def parse(xml_input, encoding='utf-8', *args, **kwargs):
    """Parse the given XML input and convert it into a dictionary.

    `xml_input` can either be a `string` or a file-like object.

    If `xml_attribs` is `True`, element attributes are put in the dictionary
    among regular child elements, using `@` as a prefix to avoid collisions. If
    set to `False`, they are just ignored.

    Simple example::

        >>> doc = xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>
        ... \"\"\")
        >>> doc['a']['@prop']
        u'x'
        >>> doc['a']['b']
        [u'1', u'2']

    If `item_depth` is `0`, the function returns a dictionary for the root
    element (default behavior). Otherwise, it calls `item_callback` every time
    an item at the specified depth is found and returns `None` in the end
    (streaming mode).

    The callback function receives two parameters: the `path` from the document
    root to the item (name-attribs pairs), and the `item` (dict). If the
    callback's return value is false-ish, parsing will be stopped with the
    :class:`ParsingInterrupted` exception.

    Streaming example::

        >>> def handle(path, item):
        ...     print 'path:%s item:%s' % (path, item)
        ...     return True
        ...
        >>> xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>\"\"\", item_depth=2, item_callback=handle)
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:1
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:2

    The optional argument `postprocessor` is a function that takes `path`, `key`
    and `value` as positional arguments and returns a new `(key, value)` pair
    where both `key` and `value` may have changed. Usage example::

        >>> def postprocessor(path, key, value):
        ...     try:
        ...         return key + ':int', int(value)
        ...     except (ValueError, TypeError):
        ...         return key, value
        >>> xmltodict.parse('<a><b>1</b><b>2</b><b>x</b></a>',
        ...                 postprocessor=postprocessor)
        OrderedDict([(u'a', OrderedDict([(u'b:int', [1, 2]), (u'b', u'x')]))])

    """
    handler = _DictSAXHandler(*args, **kwargs)
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.StartElementHandler = handler.startElement
    parser.EndElementHandler = handler.endElement
    parser.CharacterDataHandler = handler.characters
    try:
        parser.ParseFile(xml_input)
    except (TypeError, AttributeError):
        if isinstance(xml_input, _unicode):
            xml_input = xml_input.encode(encoding)
        parser.Parse(xml_input, True)
    return handler.item

def _emit(key, value, content_handler,
          attr_prefix='@',
          cdata_key='#text',
          root=True,
          preprocessor=None):
    if preprocessor is not None:
        result = preprocessor(key, value)
        if result is None:
            return
        key, value = result
    if not isinstance(value, (list, tuple)):
        value = [value]
    if root and len(value) > 1:
        raise ValueError('document with multiple roots')
    for v in value:
        if v is None:
            v = OrderedDict()
        elif not isinstance(v, dict):
            v = _unicode(v)
        if isinstance(v, _basestring):
            v = OrderedDict(((cdata_key, v),))
        cdata = None
        attrs = OrderedDict()
        children = []
        for ik, iv in v.items():
            if ik == cdata_key:
                cdata = iv
                continue
            if ik.startswith(attr_prefix):
                attrs[ik[len(attr_prefix):]] = iv
                continue
            children.append((ik, iv))
        content_handler.startElement(key, AttributesImpl(attrs))
        for child_key, child_value in children:
            _emit(child_key, child_value, content_handler,
                  attr_prefix, cdata_key, False, preprocessor)
        if cdata is not None:
            content_handler.characters(cdata)
        content_handler.endElement(key)

def unparse(item, output=None, encoding='utf-8', **kwargs):
    ((key, value),) = item.items()
    must_return = False
    if output == None:
        output = StringIO()
        must_return = True
    content_handler = XMLGenerator(output, encoding)
    content_handler.startDocument()
    _emit(key, value, content_handler, **kwargs)
    content_handler.endDocument()
    if must_return:
        value = output.getvalue()
        try: # pragma no cover
            value = value.decode(encoding)
        except AttributeError: # pragma no cover
            pass
        return value

if __name__ == '__main__': # pragma: no cover
    import sys
    import marshal

    (item_depth,) = sys.argv[1:]
    item_depth = int(item_depth)

    def handle_item(path, item):
        marshal.dump((path, item), sys.stdout)
        return True

    try:
        root = parse(sys.stdin,
                     item_depth=item_depth,
                     item_callback=handle_item,
                     dict_constructor=dict)
        if item_depth == 0:
            handle_item([], root)
    except KeyboardInterrupt:
        pass


########NEW FILE########
__FILENAME__ = trigger_xmlrpc
# -*- coding: utf-8 -*-

"""
# trigger_xmlrpc.py - Twisted twistd server plugin for Trigger
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2013, AOL Inc.'

from zope.interface import implements
from twisted.application.internet import TCPServer, SSLServer
from twisted.application.service import IServiceMaker, MultiService
from twisted.conch.manhole_tap import makeService as makeConsoleService
from twisted.plugin import IPlugin
from twisted.python.rebuild import rebuild
from twisted.python import usage, log
from twisted.web import server, xmlrpc
import warnings

try:
    from twisted.internet import ssl
except ImportError:
    # If no ssl, complain loudly.
    warnings.warn('SSL support disabled for Trigger XMLRPC Server: PyOpenSSL required.',
                  RuntimeWarning)
    ssl = None

from trigger.contrib.xmlrpc.server import TriggerXMLRPCServer


# Defaults
XML_PORT = 8000
SSH_PORT = 8001
SSH_USERS = 'users.txt'
SSL_KEYFILE = 'server.key'
SSL_CERTFILE = 'cacert.pem'


class Options(usage.Options):
    optParameters = [
        ['port', 'p', XML_PORT, 'Listening port for XMLRPC'],
        ['ssh-port', 's', SSH_PORT, 'Listening port for SSH manhole'],
        ['ssh-users', 'u', SSH_USERS,
         'Path to a passwd(5)-format username/password file'],
        ['ssl-keyfile', 'k', SSL_KEYFILE,
         'Path to a file containing a private key'],
        ['ssl-certfile', 'c', SSL_CERTFILE,
         'Path to a file containing a CA certificate'],
    ]

class TriggerXMLRPCServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = 'trigger-xmlrpc'
    description = 'Trigger XMLRPC Server'
    options = Options

    def makeService(self, options):
        rpc = TriggerXMLRPCServer(allowNone=True, useDateTime=True)
        xmlrpc.addIntrospection(rpc)
        site_factory = server.Site(rpc)

        # Try to setup SSL
        if ssl is not None:
            ctx = ssl.DefaultOpenSSLContextFactory(options['ssl-keyfile'],
                                                   options['ssl-certfile'])
            xmlrpc_service = SSLServer(int(options['port']), site_factory, ctx)
        # Or fallback to clear-text =(
        else:
            xmlrpc_service = TCPServer(int(options['port']), site_factory)

        # SSH Manhole service
        console_service = makeConsoleService(
            {
                'sshPort': 'tcp:%s' % options['ssh-port'],
                'telnetPort': None,
                'passwd': options['ssh-users'],
                'namespace': {
                    'service': rpc,
                    'rebuild': rebuild,
                    'factory': site_factory,
                }
            }
        )

        svc = MultiService()
        xmlrpc_service.setServiceParent(svc)
        console_service.setServiceParent(svc)
        return svc

serviceMaker = TriggerXMLRPCServiceMaker()

########NEW FILE########
