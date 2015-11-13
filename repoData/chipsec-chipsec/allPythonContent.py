__FILENAME__ = build_exe_win7-amd64
#!/usr/bin/env python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup build Build scripts
# Executable build scripts

## \addtogroup build
# build_exe_win7-amd64.py -- py2exe setup module for building chipsec.exe Win executable for windows 7

##\file
# py2exe setup module for building chipsec.exe Win executable for windows 7
#
# To build Windows executable chipsec.exe using py2exe:
#
# 1. Install py2exe package from http://www.py2exe.org
# 2. run "python build_exe_<platform>.py py2exe"
# 3. chipsec.exe and all needed libraries will be created in "./bin/<platform>"
#


import os
import sys

print 'Python', (sys.version)

import py2exe
WIN_DRIVER_INSTALL_PATH = "chipsec/helper/win"
VERSION_FILE="VERSION"

build_dir = os.getcwd()
root_dir = os.path.abspath(os.pardir)
bin_dir = os.path.join(root_dir,"bin")
source_dir = os.path.join(root_dir,"source")
tool_dir   = os.path.join(source_dir,"tool")

win_7_amd64 = os.path.join(bin_dir,'win7-amd64');


print os.getcwd()
os.chdir( tool_dir )
sys.path.append(tool_dir)
print os.getcwd()


data_files = [(WIN_DRIVER_INSTALL_PATH + "/win7_amd64", ['chipsec/helper/win/win7_amd64/chipsec_hlpr.sys'])]

version=""
if os.path.exists(VERSION_FILE):
    data_files.append(('.',['VERSION']))
    with open(VERSION_FILE, "r") as verFile:
        version = "." + verFile.read()

mypackages = []
for current, dirs, files in os.walk(tool_dir ):
    for file in files:
        if file == "__init__.py":
            pkg = current.replace(tool_dir+os.path.sep,"")
            pkg = pkg.replace(os.path.sep,'.')
            mypackages.append(pkg)
            print pkg

from distutils.core import setup


includes = []

setup(
        name            = 'chipsec',
        description     = 'CHIPSEC: Platform Security Assessment Framework',
        version         = '1.0'+version,
        console         = [ 'chipsec_main.py', 'chipsec_util.py' ],
        #zipfile         = None,
        data_files      =  data_files,
        options         = {
                            'build' : { 'build_base': build_dir },
                            'py2exe': {
                                        #"bundle_files": 1,
                                        #'includes'    : includes,
                                        'dist_dir'    : win_7_amd64,
                                        'packages'    : mypackages,
                                        'compressed'  : True
                                      }
                          }
)

########NEW FILE########
__FILENAME__ = common
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010 - 2012 Intel Corporation
#
# -------------------------------------------------------------------------------
#
## \addtogroup config
# __chipsec/cfg/common.py__ - common configuration
__version__ = '1.0'

import struct
from collections import namedtuple
#from ctypes import *

BIT0 = 0x0001
BIT1 = 0x0002
BIT2 = 0x0004
BIT3 = 0x0008
BIT4 = 0x0010
BIT5 = 0x0020
BIT6 = 0x0040
BIT7 = 0x0080
BIT8 = 0x0100
BIT9 = 0x0200
BIT10 = 0x0400
BIT11 = 0x0800
BIT12 = 0x1000
BIT13 = 0x2000
BIT14 = 0x4000
BIT15 = 0x8000
BIT16 = 0x00010000
BIT17 = 0x00020000
BIT18 = 0x00040000
BIT19 = 0x00080000
BIT20 = 0x00100000
BIT21 = 0x00200000
BIT22 = 0x00400000
BIT23 = 0x00800000
BIT24 = 0x01000000
BIT25 = 0x02000000
BIT26 = 0x04000000
BIT27 = 0x08000000
BIT28 = 0x10000000
BIT29 = 0x20000000
BIT30 = 0x40000000
BIT31 = 0x80000000
BIT32 = 0x100000000
BIT33 = 0x200000000
BIT34 = 0x400000000
BIT35 = 0x800000000
BIT36 = 0x1000000000
BIT37 = 0x2000000000
BIT38 = 0x4000000000
BIT39 = 0x8000000000
BIT40 = 0x10000000000
BIT41 = 0x20000000000
BIT42 = 0x40000000000
BIT43 = 0x80000000000
BIT44 = 0x100000000000
BIT45 = 0x200000000000
BIT46 = 0x400000000000
BIT47 = 0x800000000000
BIT48 = 0x1000000000000
BIT49 = 0x2000000000000
BIT50 = 0x4000000000000
BIT51 = 0x8000000000000
BIT52 = 0x10000000000000
BIT53 = 0x20000000000000
BIT54 = 0x40000000000000
BIT55 = 0x80000000000000
BIT56 = 0x100000000000000
BIT57 = 0x200000000000000
BIT58 = 0x400000000000000
BIT59 = 0x800000000000000
BIT60 = 0x1000000000000000
BIT61 = 0x2000000000000000
BIT62 = 0x4000000000000000
BIT63 = 0x8000000000000000


##############################################################################
# CPU common configuration
##############################################################################

PCI_BUS0 = 0x0

# ----------------------------------------------------------------------------
# Device 0 MMIO BARs
# ----------------------------------------------------------------------------
PCI_MCHBAR_REG_OFF            = 0x48

PCI_PCIEXBAR_REG_OFF          = 0x60
PCI_PCIEXBAR_REG_LENGTH_MASK  = (0x3 << 1)
PCI_PCIEXBAR_REG_LENGTH_256MB = 0x0
PCI_PCIEXBAR_REG_LENGTH_128MB = 0x2
PCI_PCIEXBAR_REG_LENGTH_64MB  = 0x1
PCI_PCIEXBAR_REG_ADMSK64      = (1 << 26)
PCI_PCIEXBAR_REG_ADMSK128     = (1 << 27)
PCI_PCIEXBAR_REG_ADMSK256     = 0xF0000000

PCI_DMIBAR_REG_OFF            = 0x68

PCI_SMRAMC_REG_OFF            = 0x88 # 0x9D before Sandy Bridge


# ----------------------------------------------------------------------------
# Device 2 (Processor Graphics/Display) MMIO BARs
# ----------------------------------------------------------------------------
PCI_GTDE_DEV                  = 2

PCI_GTTMMADR_REG_OFF          = 0x10
PCI_GMADR_REG_OFF             = 0x18

# ----------------------------------------------------------------------------
# HD Audio device configuration
# ----------------------------------------------------------------------------
PCI_HDA_DEV                   = 0x3
PCI_HDA_MMC_REG_OFF           = 0x62
PCI_HDA_MMAL_REG_OFF          = 0x64
PCI_HDA_MMAH_REG_OFF          = 0x68
PCI_HDA_MMD_REG_OFF           = 0x6C

PCI_HDAUDIOBAR_REG_OFF        = 0x10

# ----------------------------------------------------------------------------
# CPU MSRs
# ----------------------------------------------------------------------------
IA32_MTRRCAP_MSR            = 0xFE
IA32_MTRRCAP_SMRR_MASK      = 0x800

IA32_FEATURE_CONTROL_MSR    = 0x3A
IA32_FEATURE_CTRL_LOCK_MASK = 0x1

IA32_SMRR_BASE_MSR          = 0x1F2
IA32_SMRR_BASE_MEMTYPE_MASK = 0x7
IA32_SMRR_BASE_BASE_MASK    = 0xFFFFF000

IA32_SMRR_MASK_MSR          = 0x1F3
IA32_SMRR_MASK_VLD_MASK     = 0x800
IA32_SMRR_MASK_MASK_MASK    = 0xFFFFF000

MTRR_MEMTYPE_UC = 0x0
MTRR_MEMTYPE_WB = 0x6

IA32_MSR_CORE_THREAD_COUNT                   = 0x35
IA32_MSR_CORE_THREAD_COUNT_THREADCOUNT_MASK  = 0xFFFF
IA32_MSR_CORE_THREAD_COUNT_CORECOUNT_MASK    = 0xFFFF0000

IA32_PLATFORM_INFO_MSR      = 0xCE

##############################################################################
# PCH common configuration
##############################################################################

# ----------------------------------------------------------------------------
# PCI 0/31/0: PCH LPC Root Complex
# ----------------------------------------------------------------------------
PCI_B0D31F0_LPC_DEV = 31
PCI_B0D31F0_LPC_FUN = 0

LPC_BC_REG_OFF        = 0xDC #  BIOS Control (BC)

class LPC_BC_REG( namedtuple('LPC_BC_REG', 'value SMM_BWP TSS SRC BLE BIOSWE') ):
      __slots__ = ()
      def __str__(self):
          return """BIOS Control (BDF 0:31:0 + 0x%X) = 0x%02X
[05]    SMM_BWP = %u (SMM BIOS Write Protection)
[04]    TSS     = %u (Top Swap Status)
[01]    BLE     = %u (BIOS Lock Enable)
[00]    BIOSWE  = %u (BIOS Write Enable)
""" % ( LPC_BC_REG_OFF, self.value, self.SMM_BWP, self.TSS, self.BLE, self.BIOSWE )         

CFG_REG_PCH_LPC_PMBASE = 0x40 # ACPI I/O Base (PMBASE/ABASE)
CFG_REG_PCH_LPC_ACTL   = 0x44 # ACPI Control  (ACTL)
CFG_REG_PCH_LPC_GBA    = 0x44 # GPIO I/O Base (GBA)
CFG_REG_PCH_LPC_GC     = 0x44 # GPIO Control  (GC)

# PMBASE registers
PMBASE_SMI_EN         = 0x30 # SMI_EN offset in PMBASE (ABASE)

# ----------------------------------------------------------------------------
# SPI Controller MMIO
# ----------------------------------------------------------------------------
SPI_MMIO_BUS          = PCI_BUS0
SPI_MMIO_DEV          = PCI_B0D31F0_LPC_DEV
SPI_MMIO_FUN          = PCI_B0D31F0_LPC_FUN
SPI_MMIO_REG_OFFSET   = 0xF0
SPI_BASE_ADDR_SHIFT   = 14
SPI_MMIO_BASE_OFFSET  = 0x3800  # Base address of the SPI host interface registers off of RCBA
#SPI_MMIO_BASE_OFFSET = 0x3020  # Old (ICH8 and older) SPI registers base

# @TODO: cleanup
LPC_RCBA_REG_OFFSET   = 0xF0
RCBA_BASE_ADDR_SHIFT  = 14
PCH_RCRB_SPI_BASE     = 0x3800  # Base address of the SPI host interface registers off of RCBA


# ----------------------------------------------------------------------------
# PCI B0:D31:F3 SMBus Controller
# ----------------------------------------------------------------------------
PCI_B0D31F3_SMBUS_CTRLR_DEV = 31
PCI_B0D31F3_SMBUS_CTRLR_FUN = 0x3
#0x8C22, 0x9C22 # HSW
#0x1C22 # SNB
#0x1E22 # IVB 0x0154
PCI_B0D31F3_SMBUS_CTRLR_DID = 0x1C22

CFG_REG_PCH_SMB_CMD  = 0x04                    # D31:F3 Command

CFG_REG_PCH_SMB_SBA  = 0x20                    # SMBus Base Address
CFG_REG_PCH_SMB_SBA_BASE_ADDRESS_MASK = 0xFFE0 # Base Address
CFG_REG_PCH_SMB_SBA_IO                = BIT0   # I/O Space Indicator

CFG_REG_PCH_SMB_HCFG = 0x40                    # D31:F3 Host Configuration
CFG_REG_PCH_SMB_HCFG_SPD_WD           = BIT4   # SPD_WD
CFG_REG_PCH_SMB_HCFG_SSRESET          = BIT3   # Soft SMBus Reset
CFG_REG_PCH_SMB_HCFG_I2C_EN           = BIT2   # I2C Enable
CFG_REG_PCH_SMB_HCFG_SMB_SMI_EN       = BIT1   # SMBus SMI Enable
CFG_REG_PCH_SMB_HCFG_HST_EN           = BIT0   # SMBus Host Enable
class SMB_HCFG_REG( namedtuple('SMB_HCFG_REG', 'value SPD_WD SSRESET I2C_EN SMB_SMI_EN HST_EN') ):
      __slots__ = ()
      def __str__(self):
          return """
SMBus Host Config (BDF 0:31:0 + 0x%X) = 0x%02X
[04] SPD_WD     = %u (SPD_WD)
[03] SSRESET    = %u (Soft SMBus Reset)
[02] I2C_EN     = %u (I2C Enable)
[01] SMB_SMI_EN = %u (SMBus SMI Enable)
[00] HST_EN     = %u (Host Enable)
""" % ( CFG_REG_PCH_SMB_HCFG, self.value, self.SPD_WD, self.SSRESET, self.I2C_EN, self.SMB_SMI_EN, self.HST_EN )         

# ----------------------------------------------------------------------------
# PCH I/O Base Registers
# ----------------------------------------------------------------------------

TCOBASE_ABASE_OFFSET = 0x60


# ----------------------------------------------------------------------------
# PCH RCBA
# ----------------------------------------------------------------------------


RCBA_GENERAL_CONFIG_OFFSET = 0x3400  # Offset of BIOS General Configuration memory mapped registers base in RCBA

RCBA_GC_RC_REG_OFFSET      = 0x0     # RTC Configuration (RC) register

RCBA_GC_GCS_REG_OFFSET     = 0x10    # General Control and Status (GCS) register
RCBA_GC_GCS_REG_BILD_MASK  = 0x1     # BIOS Interface Lock-Down (BILD)
RCBA_GC_GCS_REG_BBS_MASK   = 0xC00   # Boot BIOS Straps (BBS) - PCI/SPI/LPC
RCBA_GC_BUC_REG_OFFSET     = 0x14    # Backup Control (BUC) register
RCBA_GC_BUC_REG_TS_MASK    = 0x1     # Top-Swap strap (TS)


########NEW FILE########
__FILENAME__ = hsw
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010 - 2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup config
# __chipsec/cfg/hsw.py__ - configuration specific for Haswell Platforms
#
# Add configuration specific to Haswell based platform to this module
# On Haswell platforms, configuraion from this file will override configuration from cfg.common
#
__version__ = '1.0'


##############################################################################
# CPU configuration
##############################################################################

##############################################################################
# PCH configuration
##############################################################################

########NEW FILE########
__FILENAME__ = chipset
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup core 
# __chipsec/chipset.py__ -- Contains platform identification functions
#
#

__version__ = '1.0'

import sys
import collections

from chipsec.helper.oshelper import OsHelper, OsHelperError
from chipsec.hal.pci         import Pci
from chipsec.hal.physmem     import Memory
from chipsec.hal.msr         import Msr
from chipsec.hal.ucode       import Ucode
from chipsec.hal.io          import PortIO
from chipsec.hal.cpuid       import CpuID

from chipsec.logger         import logger


#_importlib = True
#try:                import importlib
#except ImportError: _importlib = False

#
# Import platform configuration defines in the following order:
# 1. chipsec.cfg.common
# 2. chipsec.cfg.<platform>
#
from chipsec.cfg.common import *
logger().log_good( "imported common configuration: chipsec.cfg.common" )


##################################################################################
# Functionality defining current chipset
##################################################################################
CHIPSET_ID_COMMON  = -1
CHIPSET_ID_UNKNOWN = 0

CHIPSET_ID_BLK     = 1
CHIPSET_ID_CNTG    = 2
CHIPSET_ID_EGLK    = 3
CHIPSET_ID_TBG     = 4
CHIPSET_ID_WSM     = 5
CHIPSET_ID_SNB     = 8
CHIPSET_ID_IVB     = 9
CHIPSET_ID_HSW     = 10
CHIPSET_ID_BDW     = 11
CHIPSET_ID_BYT     = 12
CHIPSET_ID_JKT     = 13
CHIPSET_ID_HSX     = 14
CHIPSET_ID_IVT     = 15

VID_INTEL = 0x8086

# PCI 0/0/0 Device IDs
Chipset_Dictionary = {
# DID  : Data Dictionary

# 2nd Generation Core Processor Family (Sandy Bridge)
0x0100 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : 'SNB',  'longname' : 'Desktop 2nd Generation Core Processor (Sandy Bridge CPU / Cougar Point PCH)' },
0x0104 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : 'SNB',  'longname' : 'Mobile 2nd Generation Core Processor (Sandy Bridge CPU / Cougar Point PCH)' },
0x0108 : {'name' : 'Sandy Bridge',   'id' : CHIPSET_ID_SNB , 'code' : 'SNB',  'longname' : 'Intel Xeon Processor E3-1200 (Sandy Bridge CPU, C200 Series PCH)' },
0x3C00 : {'name' : 'Jaketown',       'id' : CHIPSET_ID_JKT,  'code' : 'JKT',  'longname' : 'Server 2nd Generation Core Processor (Jaketown CPU / Patsburg PCH)'},

# 3rd Generation Core Processor Family (Ivy Bridge)
0x0150 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : 'IVB',  'longname' : 'Desktop 3rd Generation Core Processor (Ivy Bridge CPU / Panther Point PCH)' },
0x0154 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : 'IVB',  'longname' : 'Mobile 3rd Generation Core Processor (Ivy Bridge CPU / Panther Point PCH)' },
0x0158 : {'name' : 'Ivy Bridge',     'id' : CHIPSET_ID_IVB , 'code' : 'IVB',  'longname' : 'Intel Xeon Processor E3-1200 v2 (Ivy Bridge CPU, C200/C216 Series PCH)' },
0x0E00 : {'name' : 'Ivytown',        'id' : CHIPSET_ID_IVT,  'code' : 'IVT',  'longname' : 'Server 3rd Generation Core Procesor (Ivytown CPU / Patsburg PCH)'},

# 4th Generation Core Processor Family (Haswell)
0x0C00 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : 'Desktop 4th Generation Core Processor (Haswell CPU / Lynx Point PCH)' },
0x0C04 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : 'Mobile 4th Generation Core Processor (Haswell M/H / Lynx Point PCH)' },
0x0C08 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : 'Intel Xeon Processor E3-1200 v3 (Haswell CPU, C220 Series PCH)' },
0x0A00 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : '4th Generation Core Processor (Haswell U/Y)' },
0x0A04 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : '4th Generation Core Processor (Haswell U/Y)' },
0x0A08 : {'name' : 'Haswell',        'id' : CHIPSET_ID_HSW , 'code' : 'HSW',  'longname' : '4th Generation Core Processor (Haswell U/Y)' },

# Bay Trail SoC
0x0F00 : {'name' : 'Baytrail',       'id' : CHIPSET_ID_BYT , 'code' : 'BYT',  'longname' : 'Intel Bay Trail' },

}
 
Chipset_Code = dict( [(Chipset_Dictionary[ _did ]['code'], _did) for _did in Chipset_Dictionary] )

def print_supported_chipsets():
    codes_dict = collections.defaultdict(list)
    for _did in Chipset_Dictionary: codes_dict[ Chipset_Dictionary[ _did ]['code'] ].append( _did )
    logger().log( "\nSupported platforms:\n" )
    logger().log( "DID     | Name           | Code   | Long Name" )
    logger().log( "-------------------------------------------------------------------------------------" )
    for _code in sorted(codes_dict):    
        for _did in codes_dict[_code]:
            logger().log( " %-#6x | %-14s | %-6s | %-40s" % (_did, Chipset_Dictionary[_did]['name'], _code.lower(), Chipset_Dictionary[_did]['longname']) )


class UnknownChipsetError (RuntimeError):
    pass

class Chipset:

    def __init__(self, helper=None):
        if helper is None:
            self.helper = OsHelper()
        else:
            self.helper = helper

        self.vid        = 0
        self.did        = 0
        self.code       = ""
        self.longname   = "Unrecognized Platform"
        self.id         = CHIPSET_ID_UNKNOWN

        #
        # Initializing 'basic primitive' HAL components
        # (HAL components directly using native OS helper functionality)
        #
        self.pci    	= Pci      ( self.helper )
        self.mem    	= Memory   ( self.helper )
        self.msr    	= Msr      ( self.helper )
        self.ucode  	= Ucode    ( self.helper )
        self.io     	= PortIO   ( self.helper )
        self.cpuid      = CpuID    ( self.helper )
        #
        # All HAL components which use above 'basic primitive' HAL components
        # should be instantiated in modules/utilcmd with an instance of chipset
        # Example of initializing second order HAL component (UEFI in uefi_cmd.py):
        # cs = cs()
        # self.uefi = UEFI( cs )
        #

    def init( self, platform_code, start_svc ):

        if start_svc: self.helper.start()

        if not platform_code:
            vid_did  = self.pci.read_dword( 0, 0, 0, 0 )
            self.vid = vid_did & 0xFFFF
            self.did = (vid_did >> 16) & 0xFFFF
            if VID_INTEL != self.vid: raise UnknownChipsetError, ('UnsupportedPlatform: Vendor ID = 0x%04X' % self.vid)
        else:
            if Chipset_Code.has_key( platform_code ): self.code = platform_code.lower()
            else: raise UnknownChipsetError, ('UnsupportedPlatform: code: %s' % platform_code)
            self.vid      = VID_INTEL
            self.did      = Chipset_Code[ platform_code ]

        if Chipset_Dictionary.has_key( self.did ):
            data_dict       = Chipset_Dictionary[ self.did ]
            self.code       = data_dict['code'].lower()
            self.longname   = data_dict['longname']
            self.id         = data_dict['id']
        else:
            raise UnknownChipsetError, ('UnsupportedPlatform: Device ID = 0x%04X' % self.did)



    def destroy( self, start_svc ):
        self.stop( start_svc )
        #self.helper.destroy()

    def stop( self, start_svc ):
        if start_svc:
            self.helper.stop()

    def get_chipset_id(self):
        return self.id

    def get_chipset_code(self):
        return self.code

    def get_chipset_name(self, id ):
        return self.longname


    def print_chipset(self):
        logger().log( "Platform: %s\n          VID: %04X\n          DID: %04X" % (self.longname, self.vid, self.did))

from chipsec.helper.oshelper import helper
_chipset = Chipset( helper() )
def cs():
    return _chipset




########NEW FILE########
__FILENAME__ = file
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



#
# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------

## \addtogroup core
#@{
# __chipsec/file.py__ -- reading from/writing to files
#@}

## file.py
# usage:
#     read_file( filename )
#     write_file( filename, buffer )
#
#
__version__ = '1.0'

import struct
import sys

from chipsec.logger import logger

def read_file( filename, size=0 ):
    # @TODO: this is Python 2.5+ syntax -- chipsec for UEFI uses Python 2.4
    #with open( filename, 'rb' ) as f:
    #  _file = f.read()
    #f.closed

    try:
      f = open(filename, "rb")
    except:
      logger().error( "Unable to open file '%.256s' for read access" % filename )
      return 0

    if size:
       _file = f.read( size )
    else:
       _file = f.read()
    f.close()

    if logger().VERBOSE:
       logger().log( "[file] read %d bytes from '%.256s'" % ( len(_file), filename ) )
    return _file

def write_file( filename, buffer, append=False ):
    # @TODO: this is Python 2.5+ syntax -- chipsec for UEFI uses Python 2.4
    #with open( filename, 'wb' ) as f:
    #  f.write( buffer )
    #f.closed
    perm = "wb"
    if (append): perm = "ab"

    try:
      f = open(filename, perm)
    except:
      logger().error( "Unable to open file '%.256s' for write access" % filename )
      return 0
    f.write( buffer )
    f.close()

    if logger().VERBOSE:
       logger().log( "[file] wrote %d bytes to '%.256s'" % ( len(buffer), filename ) )
    return True


def read_chunk( f, size=1024 ):
    return f.read( size )
# intended usage
#for piece in iter(read1k, ''):
#    process_data(piece)

########NEW FILE########
__FILENAME__ = cmos
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
#
#
## \addtogroup hal
# chipsec/hal/cmos.py
# ==================================
# CMOS memory specific functions (dump, read/write)
#~~~
# #usage:
#     dump()
#     read_byte( offset )
#     write_byte( offset, value )
#~~~
#
__version__ = '1.0'

import struct
import sys
import time

from chipsec.logger import *
#from chipsec.hal.mmio import *
from chipsec.file import *

from chipsec.cfg.common import *


class CmosRuntimeError (RuntimeError):
    pass
class CmosAccessError (RuntimeError):
    pass

CMOS_ADDR_PORT_LOW  = 0x70
CMOS_DATA_PORT_LOW  = 0x71
CMOS_ADDR_PORT_HIGH = 0x72
CMOS_DATA_PORT_HIGH = 0x73

class CMOS:
    def __init__( self, cs ):
        self.cs = cs

    def read_cmos_high( self, offset ):
        self.cs.io.write_port_byte( CMOS_ADDR_PORT_HIGH, offset );
        return self.cs.io.read_port_byte( CMOS_DATA_PORT_HIGH )

    def write_cmos_high( self, offset, value ):
        self.cs.io.write_port_byte( CMOS_ADDR_PORT_HIGH, offset );
        self.cs.io.write_port_byte( CMOS_DATA_PORT_HIGH, value );

    def read_cmos_low( self, offset ):
        self.cs.io.write_port_byte( CMOS_ADDR_PORT_LOW, 0x80|offset );
        return self.cs.io.read_port_byte( CMOS_DATA_PORT_LOW )

    def write_cmos_low( self, offset, value ):
        self.cs.io.write_port_byte( CMOS_ADDR_PORT_LOW, offset );
        self.cs.io.write_port_byte( CMOS_DATA_PORT_LOW, value );

    def dump_low( self ):
        orig = self.cs.io.read_port_byte( CMOS_ADDR_PORT_LOW );
        logger().log( "Low CMOS contents:" )
        logger().log( "....0...1...2...3...4...5...6...7...8...9...A...B...C...D...E...F" )
        cmos_str = []
        cmos_str += ["00.."] 
        for n in range(1, 129):
            val = self.read_cmos_low( n-1 )
            cmos_str += ["%02X  " % val] 
            if ( (0 == n%16) and n < 125 ):
               cmos_str += ["\n%0X.." % n] 

        self.cs.io.write_port_byte( CMOS_ADDR_PORT_LOW, orig );
        logger().log( "".join(cmos_str) )
        return

    def dump_high( self ):
        orig = self.cs.io.read_port_byte( CMOS_ADDR_PORT_HIGH );
        logger().log( "High CMOS contents:" )
        logger().log( "....0...1...2...3...4...5...6...7...8...9...A...B...C...D...E...F" )
        cmos_str = []
        cmos_str += ["00.."] 
        for n in range(1, 129):
            val = self.read_cmos_high( n-1 )
            cmos_str += ["%02X  " % val] 
            if ( (0 == n%16) and n < 125 ):
               cmos_str += ["\n%0X.." % n] 

        self.cs.io.write_port_byte( CMOS_ADDR_PORT_HIGH, orig );
        logger().log( "".join(cmos_str) )
        return

    def dump( self ):
        self.dump_low()
        self.dump_high()

########NEW FILE########
__FILENAME__ = cpuid
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/cpuid.py
# ======================
# CPUID information
# ~~~
# #usage:
#     cpuid(0)
# ~~~
#   
__version__ = '1.0'

import struct
import sys
import os.path

from chipsec.logger import logger

class CpuIDRuntimeError (RuntimeError):
    pass

class CpuID:

    def __init__( self, helper ):
        self.helper = helper

    def cpuid(self, eax ):
        value = self.helper.cpuid( eax )
        if logger().VERBOSE:
            logger().log( "[CpuID] calling cpuid EAX=0x%x" % eax )
        return value

     

########NEW FILE########
__FILENAME__ = interrupts
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
#
# chipsec/hal/interrupts.py
# ===============================================
# Functionality encapsulating interrupt generation
# CPU Interrupts specific functions (SMI, NMI)
# ~~~ 
# #usage:
#     send_SMI_APMC( 0xDE )
#     send_NMI()
# ~~~
# \TODO IPIs through Local APIC??
#

__version__ = '1.0'

import struct
import sys

from chipsec.logger import *
from chipsec.cfg.common import *

SMI_APMC_PORT = 0xB2

NMI_TCO1_CTL = 0x8 # NMI_NOW is bit [8] in TCO1_CTL (or bit [1] in TCO1_CTL + 1)
NMI_NOW      = 0x1


class Interrupts:
    def __init__( self, cs ):
        self.cs = cs

    def send_SW_SMI( self, SMI_code_port_value, SMI_data_port_value, _rax, _rbx, _rcx, _rdx, _rsi, _rdi ):
        SMI_code_data = (SMI_data_port_value << 8 | SMI_code_port_value)
        if logger().VERBOSE:
           logger().log( "[intr] sending SW SMI: code port 0x%02X <- 0x%02X, data port 0x%02X <- 0x%02X (0x%04X)" % (SMI_APMC_PORT, SMI_code_port_value, SMI_APMC_PORT+1, SMI_data_port_value, SMI_code_data) )
           logger().log( "       RAX = 0x%016X (AX will be overwridden with values of SW SMI ports B2/B3)" % _rax )
           logger().log( "       RBX = 0x%016X" % _rbx )
           logger().log( "       RCX = 0x%016X" % _rcx )
           logger().log( "       RDX = 0x%016X (DX will be overwridden with 0x00B2)" % _rdx )
           logger().log( "       RSI = 0x%016X" % _rsi )
           logger().log( "       RDI = 0x%016X" % _rdi )
        return self.cs.helper.send_sw_smi( SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi )

    def send_SMI_APMC( self, SMI_code_port_value, SMI_data_port_value ):
        SMI_code_data = (SMI_data_port_value << 8 | SMI_code_port_value)
        if logger().VERBOSE:
           logger().log( "[intr] sending SMI via APMC ports: code 0xB2 <- 0x%02X, data 0xB3 <- 0x%02X (0x%04X)" % (SMI_code_port_value, SMI_data_port_value, SMI_code_data) )
        return self.cs.io.write_port_word( SMI_APMC_PORT, SMI_code_data )

    def get_TCOBASE( self ):
        abase = self.cs.pci.read_dword( 0, 31, 0, CFG_REG_PCH_LPC_ABASE ) & ~0x1
        tcobase = abase + TCOBASE_ABASE_OFFSET
        return tcobase

    def send_NMI( self ):
        if logger().VERBOSE:
           logger().log( "[intr] sending NMI# through TCO1_CTL[NMI_NOW]" )
        tcobase = self.get_TCOBASE()
        return self.cs.io.write_port_byte( tcobase + NMI_TCO1_CTL + 1, NMI_NOW )


########NEW FILE########
__FILENAME__ = io
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
#
# chipsec/hal/io.py
# ========================
# Access to Port I/O
# ~~~
# #usage:
#     read_port_byte( 0x61 )
#     read_port_word( 0x61 )
#     read_port_dword( 0x61 )
#     write_port_byte( 0x71, 0 )
#     write_port_word( 0x71, 0 )
#     write_port_dword( 0x71, 0 )
# ~~~
#
__version__ = '1.0'

import struct
import sys
import os.path

from chipsec.logger import logger

class PortIORuntimeError (RuntimeError):
    pass

class PortIO:

    def __init__( self, helper ):
        self.helper = helper

    def _read_port(self, io_port, size ):
        value = self.helper.read_io_port( io_port, size )
        if logger().VERBOSE:
           logger().log( "[io] reading from I/O port 0x%04X: value = 0x%08X (size = 0x%02x)" % (io_port, value, size) )
        return value

    def _write_port(self, io_port, size ):
        value = self.helper.write_io_port( io_port, value, size )
        if logger().VERBOSE:
           logger().log( "[io] writing to I/O port 0x%04X: value = 0x%08X (size = 0x%02x)" % (io_port, value, size) )
        return value

    def read_port_dword(self, io_port ):
        value = self.helper.read_io_port( io_port, 4 )
        if logger().VERBOSE:
           logger().log( "[io] reading dword from I/O port 0x%04X -> 0x%08X" % (io_port, value) )
        return value

    def read_port_word(self, io_port ):
        value = self.helper.read_io_port( io_port, 2 )
        if logger().VERBOSE:
           logger().log( "[io] reading word from I/O port 0x%04X -> 0x%04X" % (io_port, value) )
        return value

    def read_port_byte(self, io_port ):
        value = self.helper.read_io_port( io_port, 1 )
        if logger().VERBOSE:
           logger().log( "[io] reading byte from I/O port 0x%04X -> 0x%02X" % (io_port, value) )
        return value


    def write_port_byte(self, io_port, value ):
        if logger().VERBOSE:
           logger().log( "[io] writing byte to I/O port 0x%04X <- 0x%02X" % (io_port, value) )
        self.helper.write_io_port( io_port, value, 1 )
        return

    def write_port_word(self, io_port, value ):
        if logger().VERBOSE:
           logger().log( "[io] writing word to I/O port 0x%04X <- 0x%04X" % (io_port, value) )
        self.helper.write_io_port( io_port, value, 2 )
        return

    def write_port_dword(self, io_port, value ):
        if logger().VERBOSE:
           logger().log( "[io] writing dword to I/O port 0x%04X <- 0x%08X" % (io_port, value) )
        self.helper.write_io_port( io_port, value, 4 )
        return

########NEW FILE########
__FILENAME__ = mmio
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/mmio.py
# =============================================
# Access to MMIO (Memory Mapped IO) BARs and Memory-Mapped PCI Configuration Space (MMCFG)
# ~~~
# #usage:
#     read_MMIOBAR_reg( cs, mmio.MMIO_BAR_MCHBAR, 0x0 )
#     write_MMIOBAR_reg( cs, mmio.MMIO_BAR_MCHBAR, 0xFFFFFFFF )
#     read_MMIO_reg( bar_base, 0x0 )
#     write_MMIO_reg( bar_base, 0x0, 0xFFFFFFFF )
#
#     get_MMIO_base_address( cs, mmio.MMIO_BAR_MCHBAR )
#     is_MMIOBAR_enabled( cs, mmio.MMIO_BAR_MCHBAR )
#     is_MMIOBAR_programmed( cs, mmio.MMIO_BAR_MCHBAR )
#
#     read_MMIOBAR( cs, mmio.MMIO_BAR_MCHBAR, 0x1000 )
#     read_MMIO( cs, bar_base, 0x1000 )
#     dump_MMIO( cs, bar_base, 0x1000 )
#
#     read_mmcfg_reg( cs, 0, 0, 0, 0x10, 4 ):
#     read_mmcfg_reg( cs, 0, 0, 0, 0x10, 4, 0xFFFFFFFF )
# ~~~
#
__version__ = '1.0'

import struct
import sys

from chipsec.logger import logger
#from chipsec.pci import PCI_BDF

from chipsec.cfg.common import *


##################################################################################
# Dev0 BARs: MCHBAR, DMIBAR
##################################################################################
def get_MCHBAR_base_address(cs):
    #bar = PCI_BDF( 0, 0, 0, PCI_MCHBAR_REG_OFF )
    base = cs.pci.read_dword( 0, 0, 0, PCI_MCHBAR_REG_OFF )
    if (0 == base & 0x1):
       logger().warn('MCHBAR is disabled')
    base = base & 0xFFFFF000
    if logger().VERBOSE:
       logger().log( '[mmio] MCHBAR: 0x%016X' % base )
    return base

def get_DMIBAR_base_address(cs):
    #bar = PCI_BDF( 0, 0, 0, PCI_DMIBAR_REG_OFF )
    base_lo = cs.pci.read_dword( 0, 0, 0, PCI_DMIBAR_REG_OFF )
    base_hi = cs.pci.read_dword( 0, 0, 0, PCI_DMIBAR_REG_OFF + 4 )
    if (0 == base_lo & 0x1):
       logger().warn('DMIBAR is disabled')
    base = (base_hi << 32) | (base_lo & 0xFFFFF000)
    if logger().VERBOSE:
       logger().log( '[mmio] DMIBAR: 0x%016X' % base )
    return base


##################################################################################
# PCH LPC Interface Root Complex base address (RCBA)
##################################################################################

def get_LPC_RCBA_base_address(cs):
    reg_value = cs.pci.read_dword( 0, 31, 0, LPC_RCBA_REG_OFFSET )
    #RcbaReg = LPC_RCBA_REG( (reg_value>>14)&0x3FFFF, (reg_value>>1)&0x1FFF, reg_value&0x1 )
    #rcba_base = RcbaReg.BaseAddr << RCBA_BASE_ADDR_SHIFT
    rcba_base = (reg_value >> RCBA_BASE_ADDR_SHIFT) << RCBA_BASE_ADDR_SHIFT
    if logger().VERBOSE:
      logger().log( "[mmio] LPC RCBA: 0x%08X" % rcba_base )
    return rcba_base


##################################################################################
# Base of SPI Controller MMIO registers
##################################################################################

def get_PCH_RCBA_SPI_base(cs):
    rcba_spi_base = get_LPC_RCBA_base_address(cs) + PCH_RCRB_SPI_BASE
    if logger().VERBOSE:
       logger().log( "[mmio] RCBA SPI base: 0x%08X (assuming below 4GB)" % rcba_spi_base )
    return rcba_spi_base


##################################################################################
# GFx MMIO: GMADR/GTTMMADR
##################################################################################

def get_GFx_base_address(cs, dev2_offset):
    #bar = PCI_BDF( 0, 2, 0, dev2_offset )
    base_lo = cs.pci.read_dword( 0, 2, 0, dev2_offset )
    base_hi = cs.pci.read_dword( 0, 2, 0, dev2_offset + 4 )
    base = base_hi | (base_lo & 0xFF000000)
    return base
def get_GMADR_base_address( cs ):
    base = get_GFx_base_address(cs, PCI_GMADR_REG_OFF)
    if logger().VERBOSE:
       logger().log( '[mmio] GMADR: 0x%016X' % base )
    return base
def get_GTTMMADR_base_address( cs ):
    base = get_GFx_base_address(cs, PCI_GTTMMADR_REG_OFF)
    if logger().VERBOSE:
       logger().log( '[mmio] GTTMMADR: 0x%016X' % base )
    return base

##################################################################################
# HD Audio MMIO
##################################################################################

def get_HDAudioBAR_base_address(cs):
    base = cs.pci.read_dword( 0, PCI_HDA_DEV, 0, PCI_HDAUDIOBAR_REG_OFF )
    base = base & (0xFFFFFFFF << 14)
    if logger().VERBOSE:
       logger().log( '[mmio] HD Audio MMIO: 0x%08X' % base )
    return base


##################################################################################
# PCIEXBAR - technically not MMIO but Memory-mapped CFG space (MMCFG)
# but defined by BAR similarly to MMIO BARs
##################################################################################

def get_PCIEXBAR_base_address(cs):
    base_lo = cs.pci.read_dword( 0, 0, 0, PCI_PCIEXBAR_REG_OFF )
    base_hi = cs.pci.read_dword( 0, 0, 0, PCI_PCIEXBAR_REG_OFF + 4 )
    if (0 == base_lo & 0x1):
       logger().warn('PCIEXBAR is disabled')

    base_lo &= PCI_PCIEXBAR_REG_ADMSK256
    if (PCI_PCIEXBAR_REG_LENGTH_128MB == (base_lo & PCI_PCIEXBAR_REG_LENGTH_MASK) >> 1):
       base_lo |= PCI_PCIEXBAR_REG_ADMSK128
    elif (PCI_PCIEXBAR_REG_LENGTH_64MB == (base_lo & PCI_PCIEXBAR_REG_LENGTH_MASK) >> 1):
       base_lo |= (PCI_PCIEXBAR_REG_ADMSK128|PCI_PCIEXBAR_REG_ADMSK64)
    base = (base_hi << 32) | base_lo
    if logger().VERBOSE:
       logger().log( '[mmio] PCIEXBAR (MMCFG): 0x%016X' % base )
    return base


##################################################################################
#
# To add your own MMIO bar:
#   1. Add new MMIO BAR id (any)
#   2. Write a function get_yourBAR_base_address() with no args that returns base addres of new bar
#   3. Add a pointer to this function to MMIO_BAR_base map
#   4. Don't touch read/write_MMIO_reg functions ;)
#
##################################################################################

# CPU
# Device 0
MMIO_BAR_MCHBAR      = 1   # MCHBAR
MMIO_BAR_DMIBAR      = 2   # DMIBAR
MMIO_BAR_PCIEXBAR    = 3   # PCIEXBAR
# Device 1
# @TODO
# Device 2
MMIO_BAR_GTTMMADR    = 10  # GFx MMIO
MMIO_BAR_GMADR       = 11  # GFx Aperture
# Device 3 (Device 27)
MMIO_BAR_HDABAR      = 20  # HD Audio MMIO BAR
# PCH
# @TODO
# Device 31
MMIO_BAR_LPCRCBA     = 100 # ICH LPC Interface Root Complex (RCBA)
MMIO_BAR_LPCRCBA_SPI = 101 # RCBA SPIBASE

MMIO_BAR_base = {
                  MMIO_BAR_MCHBAR      : get_MCHBAR_base_address,
                  MMIO_BAR_DMIBAR      : get_DMIBAR_base_address,
                  MMIO_BAR_PCIEXBAR    : get_PCIEXBAR_base_address,
                  MMIO_BAR_GMADR       : get_GMADR_base_address,
                  MMIO_BAR_GTTMMADR    : get_GTTMMADR_base_address,
                  MMIO_BAR_HDABAR      : get_HDAudioBAR_base_address,
                  MMIO_BAR_LPCRCBA     : get_LPC_RCBA_base_address,
                  MMIO_BAR_LPCRCBA_SPI : get_PCH_RCBA_SPI_base
                }
MMIO_BAR_name = {
                  MMIO_BAR_MCHBAR      : "MCHBAR",
                  MMIO_BAR_DMIBAR      : "DMIBAR",
                  MMIO_BAR_PCIEXBAR    : "PCIEXBAR",
                  MMIO_BAR_GMADR       : "GMADR",
                  MMIO_BAR_GTTMMADR    : "GTTMMADR",
                  MMIO_BAR_HDABAR      : "HDABAR",
                  MMIO_BAR_LPCRCBA     : "RCBA",
                  MMIO_BAR_LPCRCBA_SPI : "SPIBAR"
                }
#MMIO_BAR_name = dict( MMIO_BAR_base+[(e[1], e[0]) for e in MMIO_BAR_base] )


def get_MMIO_base_address( cs, bar_id ):
    return MMIO_BAR_base[ bar_id ](cs)

def is_MMIOBAR_enabled( cs, bar_id ):
    bar_base  = MMIO_BAR_base[ bar_id ](cs)
    return (0 != bar_base)


def is_MMIOBAR_programmed( cs, bar_id ):
    bar_base  = MMIO_BAR_base[ bar_id ](cs)
    return (0 != bar_base)

def read_MMIOBAR_reg(cs, bar_id, offset ):
    bar_base  = MMIO_BAR_base[ bar_id ](cs)
    reg_addr  = bar_base + offset 
    reg_value = cs.mem.read_physical_mem_dword( reg_addr )
    if logger().VERBOSE:
      logger().log( '[mmio] %s + 0x%08X (0x%08X) = 0x%08X' % (MMIO_BAR_name[bar_id], offset, reg_addr, reg_value) )
    return reg_value
def read_MMIO_reg(cs, bar_base, offset ):
    reg_value = cs.mem.read_physical_mem_dword( bar_base + offset )
    if logger().VERBOSE:
      logger().log( '[mmio] 0x%08X + 0x%08X = 0x%08X' % (bar_base, offset, reg_value) )
    return reg_value
    
def write_MMIOBAR_reg(cs, bar_id, offset, dword_value ):
    bar_base  = MMIO_BAR_base[ bar_id ]()
    reg_addr  = bar_base + offset
    if logger().VERBOSE:
       logger().log( '[mmio] write %s + 0x%08X (0x%08X) = 0x%08X' % (MMIO_BAR_name[bar_id], offset, reg_addr, dword_value) )
    cs.mem.write_physical_mem_dword( reg_addr, dword_value )
    return 1
def write_MMIO_reg(cs, bar_base, offset, dword_value ):
    if logger().VERBOSE:
       logger().log( '[mmio] write 0x%08X + 0x%08X = 0x%08X' % (bar_base, offset, dword_value) )
    cs.mem.write_physical_mem_dword( bar_base + offset, dword_value )
    return 1

def read_MMIOBAR( cs, bar_id, size ):
    regs = []
    size = size - size%4
    bar_base  = MMIO_BAR_base[ bar_id ]()
    for offset in range(0,size,4):
        regs.append( read_MMIO_reg( cs, bar_base, offset ) )
    return regs
def read_MMIO( cs, bar_base, size ):
    regs = []
    size = size - size%4
    for offset in range(0,size,4):
        regs.append( read_MMIO_reg( cs, bar_base, offset ) )
    return regs

def dump_MMIO( cs, bar_base, size ):
    regs = read_MMIO( cs, bar_base, size )
    off = 0
    for r in regs:
        logger().log( '0x%04x: %08x' % (off, r) )
        off = off + 4



##################################################################################
# Read/write memory mapped PCIe configuration registers
##################################################################################

def read_mmcfg_reg( cs, bus, dev, fun, off, size ):
    pciexbar = get_PCIEXBAR_base_address( cs )
    pciexbar_off = (bus * 32 * 8 + dev * 8 + fun) * 0x1000 + off
    value = read_MMIO_reg( cs, pciexbar, pciexbar_off )
    if logger().VERBOSE:
       logger().log( "[mmcfg] reading B/D/F %d/%d/%d + %02X (PCIEXBAR + %08X): 0x%08X" % (bus, dev, fun, off, pciexbar_off, value) )
    if 1 == size:
       return (value & 0xFF)
    elif 2 == size:
       return (value & 0xFFFF)
    return value

def write_mmcfg_reg( cs, bus, dev, fun, off, size, value ):
    pciexbar = get_PCIEXBAR_base_address( cs )
    pciexbar_off = (bus * 32 * 8 + dev * 8 + fun) * 0x1000 + off
    write_MMIO_reg( cs, pciexbar, pciexbar_off, (value&0xFFFFFFFF) )
    if logger().VERBOSE:
       logger().log( "[mmcfg] writing B/D/F %d/%d/%d + %02X (PCIEXBAR + %08X): 0x%08X" % (bus, dev, fun, off, pciexbar_off, value) )
    return True

########NEW FILE########
__FILENAME__ = msr
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/msr.py
# ============================================
# Access to CPU resources (for each CPU thread): Model Specific Registers (MSR), IDT/GDT
# usage:
#     read_msr( 0x8B )
#     write_msr( 0x79, 0x12345678 )
#     get_IDTR( 0 )
#     get_GDTR( 0 )
#     dump_Descriptor_Table( 0, DESCRIPTOR_TABLE_CODE_IDTR )
#     IDT( 0 )
#     GDT( 0 )
#     IDT_all()
#     GDT_all()
#
#
__version__ = '1.0'

import struct
import sys
import os

from chipsec.logger import logger, print_buffer
from chipsec.cfg.common import *


DESCRIPTOR_TABLE_CODE_IDTR = 0
DESCRIPTOR_TABLE_CODE_GDTR = 1
DESCRIPTOR_TABLE_CODE_LDTR = 2

class MsrRuntimeError (RuntimeError):
    pass

class Msr:

    def __init__( self, helper ):
        self.helper = helper

    def get_cpu_thread_count( self ):
        (core_thread_count, dummy) = self.helper.read_msr( 0, IA32_MSR_CORE_THREAD_COUNT )
        if (core_thread_count & IA32_MSR_CORE_THREAD_COUNT_THREADCOUNT_MASK) == 0:
            return self.helper.get_threads_count()
        return (core_thread_count & IA32_MSR_CORE_THREAD_COUNT_THREADCOUNT_MASK)

    def get_cpu_core_count( self ):
        (core_thread_count, dummy) = self.helper.read_msr( 0, IA32_MSR_CORE_THREAD_COUNT )
        return ((core_thread_count & IA32_MSR_CORE_THREAD_COUNT_CORECOUNT_MASK) >> 16)


##########################################################################################################
#
# Read/Write CPU MSRs
#
##########################################################################################################

    def read_msr( self, cpu_thread_id, msr_addr ):
        (eax, edx) = self.helper.read_msr( cpu_thread_id, msr_addr )
        if logger().VERBOSE:
          logger().log( "[cpu%d] RDMSR( 0x%x ): EAX = 0x%08X, EDX = 0x%08X" % (cpu_thread_id, msr_addr, eax, edx) )
        return (eax, edx)

    def write_msr( self, cpu_thread_id, msr_addr, eax, edx ):
        self.helper.write_msr( cpu_thread_id, msr_addr, eax, edx )
        if logger().VERBOSE:
          logger().log( "[cpu%d] WRMSR( 0x%x ): EAX = 0x%08X, EDX = 0x%08X" % (cpu_thread_id, msr_addr, eax, edx) )
        return

##########################################################################################################
#
# Get CPU Descriptor Table Registers (IDTR, GDTR, LDTR..)
#
##########################################################################################################

    def get_Desc_Table_Register( self, cpu_thread_id, code ):
        return self.helper.get_descriptor_table( cpu_thread_id, code )

    def get_IDTR( self, cpu_thread_id ):
        (limit,base,pa) = self.get_Desc_Table_Register( cpu_thread_id, DESCRIPTOR_TABLE_CODE_IDTR )
        if logger().VERBOSE:
           logger().log( "[cpu%d] IDTR Limit = 0x%04X, Base = 0x%016X, Physical Address = 0x%016X" % (cpu_thread_id,limit,base,pa) )
        return (limit,base,pa)

    def get_GDTR( self, cpu_thread_id ):
        (limit,base,pa) = self.get_Desc_Table_Register( cpu_thread_id, DESCRIPTOR_TABLE_CODE_GDTR )
        if logger().VERBOSE:
           logger().log( "[cpu%d] GDTR Limit = 0x%04X, Base = 0x%016X, Physical Address = 0x%016X" % (cpu_thread_id,limit,base,pa) )
        return (limit,base,pa)

    def get_LDTR( self, cpu_thread_id ):
        (limit,base,pa) = self.get_Desc_Table_Register( cpu_thread_id, DESCRIPTOR_TABLE_CODE_LDTR )
        if logger().VERBOSE:
           logger().log( "[cpu%d] LDTR Limit = 0x%04X, Base = 0x%016X, Physical Address = 0x%016X" % (cpu_thread_id,limit,base,pa) )
        return (limit,base,pa)


##########################################################################################################
#
# Dump CPU Descriptor Tables (IDT, GDT, LDT..)
#
##########################################################################################################

    def dump_Descriptor_Table( self, cpu_thread_id, code, num_entries=None ):
        (limit,base,pa) = self.helper.get_descriptor_table( cpu_thread_id, code )
        dt = self.helper.read_physical_mem( pa, limit + 1 )
        total_num = len(dt)/16
        if (total_num < num_entries) or (num_entries is None):
           num_entries = total_num
        logger().log( '[cpu%d] Physical Address: 0x%016X' % (cpu_thread_id,pa) )
        logger().log( '[cpu%d] # of entries    : %d' % (cpu_thread_id,total_num) )
        logger().log( '[cpu%d] Contents (%d entries):' % (cpu_thread_id,num_entries) )
        print_buffer( buffer(dt,0,16*num_entries) )
        logger().log( '--------------------------------------' )
        logger().log( '#    segment:offset         attributes' )
        logger().log( '--------------------------------------' )
        for i in range(0, num_entries):
          offset = (ord(dt[i*16 + 11]) << 56) | (ord(dt[i*16 + 10]) << 48) | (ord(dt[i*16 + 9]) << 40) | (ord(dt[i*16 + 8]) << 32) | (ord(dt[i*16 + 7]) << 24) | (ord(dt[i*16 + 6]) << 16) | (ord(dt[i*16 + 1]) << 8) | ord(dt[i*16 + 0])
          segsel = (ord(dt[i*16 + 3]) << 8) | ord(dt[i*16 + 2])
          attr   = (ord(dt[i*16 + 5]) << 8) | ord(dt[i*16 + 4])
          logger().log( '%03d  %04X:%016X  0x%04X' % (i,segsel,offset,attr) )

        return (pa,dt)

    def IDT( self, cpu_thread_id, num_entries=None ):
        logger().log( '[cpu%d] IDT:' % cpu_thread_id )
        return self.dump_Descriptor_Table( cpu_thread_id, DESCRIPTOR_TABLE_CODE_IDTR, num_entries )
    def GDT( self, cpu_thread_id, num_entries=None ):
        logger().log( '[cpu%d] GDT:' % cpu_thread_id )
        return self.dump_Descriptor_Table( cpu_thread_id, DESCRIPTOR_TABLE_CODE_GDTR, num_entries )

    def IDT_all( self, num_entries=None ):
        for tid in range(self.get_cpu_thread_count()):
            self.IDT( tid, num_entries )
    def GDT_all( self, num_entries=None ):
        for tid in range(self.get_cpu_thread_count()):
            self.GDT( tid, num_entries )


########NEW FILE########
__FILENAME__ = pci
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/pci.py
# ===============================================
# Access to PCIe configuration spaces of I/O devices
# usage:
#     read_pci_dword( 0, 0, 0, 0x88 )
#     write_pci_dword( 0, 0, 0, 0x88, 0x1A )
#
#
__version__ = '1.0'

import struct
import sys
import os.path

from chipsec.logger import logger
from chipsec.cfg.common import *
from chipsec.hal.pcidb import *

#class PCI_BDF(Structure):
#    _fields_ = [("BUS",  c_ushort, 16),  # Bus
#                ("DEV",  c_ushort, 16),  # Device
#                ("FUNC", c_ushort, 16),  # Function
#                ("OFF",  c_ushort, 16)]  # Offset


class PciRuntimeError (RuntimeError):
    pass

def get_vendor_name_by_vid( vid ):
    if vid in VENDORS:
        return VENDORS[vid]
    return ''

def get_device_name_by_didvid( vid, did ):
    if vid in VENDORS:
        if did in DEVICES[vid]:
            return DEVICES[vid][did]
    return ''

def print_pci_devices( _devices ):
    logger().log( "BDF     | VID:DID   | Vendor                                   | Device" )
    logger().log( "-------------------------------------------------------------------------------------" )
    for (b, d, f, vid, did) in _devices:
        vendor_name = get_vendor_name_by_vid( vid )
        device_name = get_device_name_by_didvid( vid, did )
        logger().log( "%02X:%02X.%X | %04X:%04X | %-40s | %s" % (b, d, f, vid, did, vendor_name, device_name) )


class Pci:

    def __init__( self, helper ):
        self.helper = helper
        #self.devices = []

    def read_dword(self, bus, device, function, address ):
        value = self.helper.read_pci_reg( bus, device, function, address, 4 )
        if logger().VERBOSE:
          logger().log( "[pci] reading B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%08X" % (bus, device, function, address, value) )
        return value

    def read_word(self, bus, device, function, address ):
        word_value = self.helper.read_pci_reg( bus, device, function, address, 2 )
        if logger().VERBOSE:
          logger().log( "[pci] reading B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%04X" % (bus, device, function, address, word_value) )
        return word_value

    def read_byte(self, bus, device, function, address ):
        byte_value = self.helper.read_pci_reg( bus, device, function, address, 1 )
        if logger().VERBOSE:
          logger().log( "[pci] reading B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%02X" % (bus, device, function, address, byte_value) )
        return byte_value


    def write_byte(self, bus, device, function, address, byte_value ):
        self.helper.write_pci_reg( bus, device, function, address, byte_value, 1 )
        if logger().VERBOSE:
          logger().log( "[pci] writing B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%02X" % (bus, device, function, address, byte_value) )
        return

    def write_word(self, bus, device, function, address, word_value ):
        self.helper.write_pci_reg( bus, device, function, address, word_value, 2 )
        if logger().VERBOSE:
          logger().log( "[pci] writing B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%04X" % (bus, device, function, address, word_value) )
        return

    def write_dword( self, bus, device, function, address, dword_value ):
        self.helper.write_pci_reg( bus, device, function, address, dword_value, 4 )
        if logger().VERBOSE:
          logger().log( "[pci] writing B/D/F: %d/%d/%d, offset: 0x%02X, value: 0x%08X" % (bus, device, function, address, dword_value) )
        return

    def enumerate_devices( self ):
        devices = []
        for b in range(256):
            for d in range(32):
                for f in range(8):
                    did_vid = self.read_dword( b, d, f, 0x0 )
                    #didvid = read_mmcfg_reg( cs, b, d, f, 0x0 )
                    if 0xFFFFFFFF != did_vid:
                       vid = did_vid&0xFFFF
                       did = (did_vid >> 16)&0xFFFF
                       devices.append( (b, d, f, vid, did) ) 
        return devices

    #
    # Returns all I/O and MMIO BARs defined in the PCIe header of the device 
    # Returns array of elements in format (bar_address, isMMIO_BAR, is64bit_BAR, pcie_BAR_reg_offset)
    # @TODO: need to account for Type 0 vs Type 1 headers
    def get_device_bars( self, bus, dev, fun ):
        _bars = []
        off = 0x10
        while (off < 0x28):
            base_lo = self.read_dword( bus, dev, fun, off )
            if base_lo:
               # BAR is initialized
               if (0 == (base_lo & 0x1)):
                  # MMIO BAR
                  is64bit = ( (base_lo>>1) & 0x3 )
                  if 0x2 == is64bit:
                     # 64-bit MMIO BAR
                     off += 4
                     base_hi = self.read_dword( bus, dev, fun, off )
                     base = ((base_hi << 32) | (base_lo & 0xFFFFFFF0))
                     _bars.append( (base, True, True, off-4) )
                  elif 1 == is64bit:
                     # MMIO BAR below 1MB
                     pass
                  elif 0 == is64bit:
                     # 32-bit only MMIO BAR
                     _bars.append( (base_lo, True, False, off) )
               else:
                  # I/O BAR
                  _bars.append( (base_lo&0xFFFFFFFE, False, False, off) )
            off += 4
        return _bars

    def get_DIDVID( self, bus, dev, fun ):
        didvid = self.read_dword( bus, dev, fun, 0x0 )
        vid = didvid & 0xFFFF
        did = (didvid >> 16) & 0xFFFF
        return (did, vid)

    def is_enabled( self, bus, dev, fun ):
        (did, vid) = self.get_DIDVID( bus, dev, fun )
        if (0xFFFF == vid) or (0xFFFF == did):
            return False
        return True


"""
    ##################################################################################
    # PCIEXBAR - technically not MMIO but Memory-mapped CFG space (MMCFG)
    # but defined by BAR similarly to MMIO BARs
    ##################################################################################

    def get_PCIEXBAR_base_address( self ):
        base_lo = self.read_dword( 0, 0, 0, PCI_PCIEXBAR_REG_OFF )
        base_hi = self.read_dword( 0, 0, 0, PCI_PCIEXBAR_REG_OFF + 4 )
        if (0 == base_lo & 0x1):
           logger().warn('PCIEXBAR is disabled')

        base_lo &= PCI_PCIEXBAR_REG_ADMSK256
        if (PCI_PCIEXBAR_REG_LENGTH_128MB == (base_lo & PCI_PCIEXBAR_REG_LENGTH_MASK) >> 1):
           base_lo |= PCI_PCIEXBAR_REG_ADMSK128
        elif (PCI_PCIEXBAR_REG_LENGTH_64MB == (base_lo & PCI_PCIEXBAR_REG_LENGTH_MASK) >> 1):
           base_lo |= (PCI_PCIEXBAR_REG_ADMSK128|PCI_PCIEXBAR_REG_ADMSK64)
        base = (base_hi << 32) | base_lo
        if logger().VERBOSE:
           logger().log( '[mmio] PCIEXBAR (MMCFG): 0x%016X' % base )
        return base

    ##################################################################################
    # Read/write memory mapped PCIe configuration registers
    ##################################################################################

    def read_mmcfg_reg( self, bus, dev, fun, off, size ):
        pciexbar = self.get_PCIEXBAR_base_address()
        pciexbar_off = (bus * 32 * 8 + dev * 8 + fun) * 0x1000 + off
        #value = read_MMIO_reg( cs, pciexbar, pciexbar_off )
        value = self.helper.read_physical_mem_dword( pciexbar + pciexbar_off )
        if logger().VERBOSE:
           logger().log( "[mmcfg] reading B/D/F %d/%d/%d + %02X (PCIEXBAR + %08X): 0x%08X" % (bus, dev, fun, off, pciexbar_off, value) )
        if 1 == size:
           return (value & 0xFF)
        elif 2 == size:
           return (value & 0xFFFF)
        return value

    def write_mmcfg_reg( self, bus, dev, fun, off, size, value ):
        pciexbar = self.get_PCIEXBAR_base_address()
        pciexbar_off = (bus * 32 * 8 + dev * 8 + fun) * 0x1000 + off
        #write_MMIO_reg( cs, pciexbar, pciexbar_off, (value&0xFFFFFFFF) )
        self.helper.write_physical_mem_dword( pciexbar + pciexbar_off, value )
        if logger().VERBOSE:
           logger().log( "[mmcfg] writing B/D/F %d/%d/%d + %02X (PCIEXBAR + %08X): 0x%08X" % (bus, dev, fun, off, pciexbar_off, value) )
        return
"""

########NEW FILE########
__FILENAME__ = pcidb
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



#THIS FILE WAS GENERATED 


## \addtogroup hal
# chipsec/hal/pcidb.py
# ==============================================
# Auto generated from:
# http://www.pcidatabase.com/vendors.php?sort=id
# http://www.pcidatabase.com/reports.php?type=csv

VENDORS = {

0x0033 : "Paradyne Corp.",
0x003D : "master",
0x0070 : "Hauppauge Computer Works Inc.",
0x0100 : "USBPDO-8",
0x0123 : "General Dynamics",
0x0315 : "SK - Electronics Co., Ltd.",
0x0402 : " Acer aspire one",
0x046D : "Logitech Inc.",
0x0483 : "UPEK",
0x04A9 : "Canon",
0x04B3 : "IBM",
0x04D9 : "Filco",
0x04F2 : "Chicony Electronics Co. ",
0x051D : "APC",
0x0529 : "Aladdin E-Token",
0x0553 : " Aiptek USA",
0x058f : "Alcor Micro Corp.",
0x0590 : "Omron Corp",
0x05ac : "Apple, Inc.",
0x05E1 : "D-MAX",
0x064e : "SUYIN Corporation",
0x067B : "Prolific Technology Inc.",
0x06FE : "Acresso Software Inc.",
0x0711 : "SIIG, Inc.",
0x093a : "KYE Systems Corp.",
0x096E : "USB Rockey dongle from Feitain ",
0x0A5C : "Broadcom Corporation",
0x0A89 : "BREA Technologies Inc.",
0x0A92 : "Egosys, Inc.",
0x0AC8 : "ASUS ",
0x0b05 : "Toshiba Bluetooth RFBUS, RFCOM, RFHID",
0x0c45 : "Microdia Ltd.",
0x0cf3 : "TP-Link",
0x0D2E : "Feedback Instruments Ltd.",
0x0D8C : "C-Media Electronics, Inc.",
0x0DF6 : "Sitecom",
0x0E11 : "dell Computer Corp.",
0x0E8D : "MediaTek Inc.",
0x1000 : "LSI Logic",
0x1001 : "Kolter Electronic - Germany",
0x1002 : "Advanced Micro Devices, Inc.",
0x1003 : "ULSI",
0x1004 : "VLSI Technology",
0x1006 : "Reply Group",
0x1007 : "Netframe Systems Inc.",
0x1008 : "Epson",
0x100A : "as Ltd. de Phoenix del  de Tecnolog",
0x100B : "National Semiconductors",
0x100C : "Tseng Labs",
0x100D : "AST Research",
0x100E : "Weitek",
0x1010 : "Video Logic Ltd.",
0x1011 : "Digital Equipment Corporation",
0x1012 : "Micronics Computers Inc.",
0x1013 : "Cirrus Logic",
0x1014 : "International Business Machines Corp.",
0x1016 : "Fujitsu ICL Computers",
0x1017 : "Spea Software AG",
0x1018 : "Unisys Systems",
0x1019 : "Elitegroup Computer System",
0x101A : "NCR Corporation",
0x101B : "Vitesse Semiconductor",
0x101E : "American Megatrends Inc.",
0x101F : "PictureTel Corp.",
0x1020 : "Hitachi Computer Electronics",
0x1021 : "Oki Electric Industry",
0x1022 : "Advanced Micro Devices",
0x1023 : "TRIDENT MICRO",
0x1025 : "Acer Incorporated",
0x1028 : "Toshiba Satellite A660",
0x102A : "LSI Logic Headland Division",
0x102B : "Matrox Electronic Systems Ltd.",
0x102C : "Asiliant (Chips And Technologies)",
0x102D : "Wyse Technologies",
0x102E : "Olivetti Advanced Technology",
0x102F : "Toshiba America",
0x1030 : "TMC Research",
0x1031 : "miro Computer Products AG",
0x1033 : "NEC Electronics",
0x1034 : "Burndy Corporation",
0x1036 : "Future Domain",
0x1037 : "Hitachi Micro Systems Inc",
0x1038 : "AMP Incorporated",
0x1039 : "S&#304;S",
0x103A : "Seiko Epson Corporation",
0x103B : "Tatung Corp. Of America",
0x103C : "Hewlett-Packard - HP dc7800",
0x103E : "Solliday Engineering",
0x103F : "Logic Modeling",
0x1041 : "Computrend",
0x1043 : "Asustek Computer Inc.",
0x1044 : "Distributed Processing Tech",
0x1045 : "OPTi Inc.",
0x1046 : "IPC Corporation LTD",
0x1047 : "Genoa Systems Corp.",
0x1048 : "ELSA GmbH",
0x1049 : "Fountain Technology",
0x104A : "STMicroelectronics",
0x104B : "Mylex / Buslogic",
0x104C : "Texas Instruments",
0x104D : "Sony Corporation",
0x104E : "Oak Technology",
0x104F : "Co-Time Computer Ltd.",
0x1050 : "Winbond Electronics Corp.",
0x1051 : "Anigma Corp.",
0x1053 : "Young Micro Systems",
0x1054 : "Hitachi Ltd",
0x1055 : "Standard Microsystems Corp.",
0x1056 : "ICL",
0x1057 : "Motorola",
0x1058 : "Electronics & Telecommunication Res",
0x1059 : "Kontron Canada",
0x105A : "Promise Technology",
0x105B : "Foxconn International Inc.",
0x105C : "Wipro Infotech Limited",
0x105D : "Number Nine Visual Technology",
0x105E : "Vtech Engineering Canada Ltd.",
0x105F : "Infotronic America Inc.",
0x1060 : "United Microelectronics",
0x1061 : "8x8 Inc.",
0x1062 : "Maspar Computer Corp.",
0x1063 : "Ocean Office Automation",
0x1064 : "Alcatel Cit",
0x1065 : "Texas Microsystems",
0x1066 : "Picopower Technology",
0x1067 : "Mitsubishi Electronics",
0x1068 : "Diversified Technology",
0x106A : "Aten Research Inc.",
0x106B : "Apple Inc.",
0x106C : "Hyundai Electronics America",
0x106D : "Sequent Computer Systems",
0x106E : "DFI Inc.",
0x106F : "City Gate Development LTD",
0x1070 : "Daewoo Telecom Ltd.",
0x1071 : "Mitac",
0x1072 : "GIT Co. Ltd.",
0x1073 : "Yamaha Corporation",
0x1074 : "Nexgen Microsystems",
0x1075 : "Advanced Integration Research",
0x1077 : "QLogic Corporation",
0x1078 : "Cyrix Corporation",
0x1079 : "I-Bus",
0x107A : "Networth controls",
0x107B : "Gateway 2000",
0x107C : "Goldstar Co. Ltd.",
0x107D : "Leadtek Research",
0x107E : "Testernec",
0x107F : "Data Technology Corporation",
0x1080 : "Cypress Semiconductor",
0x1081 : "Radius Inc.",
0x1082 : "EFA Corporation Of America",
0x1083 : "Forex Computer Corporation",
0x1084 : "Parador",
0x1085 : "Tulip Computers Int'l BV",
0x1086 : "J. Bond Computer Systems",
0x1087 : "Cache Computer",
0x1088 : "Microcomputer Systems (M) Son",
0x1089 : "Data General Corporation",
0x108A : "SBS  Operations",
0x108C : "Oakleigh Systems Inc.",
0x108D : "Olicom",
0x108E : "Sun Microsystems",
0x108F : "Systemsoft Corporation",
0x1090 : "Encore Computer Corporation",
0x1091 : "Intergraph Corporation",
0x1092 : "Diamond Computer Systems",
0x1093 : "National Instruments",
0x1094 : "Apostolos",
0x1095 : "Silicon Image, Inc.",
0x1096 : "Alacron",
0x1097 : "Appian Graphics",
0x1098 : "Quantum Designs Ltd.",
0x1099 : "Samsung Electronics Co. Ltd.",
0x109A : "Packard Bell",
0x109B : "Gemlight Computer Ltd.",
0x109C : "Megachips Corporation",
0x109D : "Zida Technologies Ltd.",
0x109E : "Brooktree Corporation",
0x109F : "Trigem Computer Inc.",
0x10A0 : "Meidensha Corporation",
0x10A1 : "Juko Electronics Inc. Ltd.",
0x10A2 : "Quantum Corporation",
0x10A3 : "Everex Systems Inc.",
0x10A4 : "Globe Manufacturing Sales",
0x10A5 : "Racal Interlan",
0x10A8 : "Sierra Semiconductor",
0x10A9 : "Silicon Graphics",
0x10AB : "Digicom",
0x10AC : "Honeywell IASD",
0x10AD : "Winbond Systems Labs",
0x10AE : "Cornerstone Technology",
0x10AF : "Micro Computer Systems Inc.",
0x10B0 : "Gainward GmbH ",
0x10B1 : "Cabletron Systems Inc.",
0x10B2 : "Raytheon Company",
0x10B3 : "Databook Inc.",
0x10B4 : "STB Systems",
0x10B5 : "PLX Technology Inc.",
0x10B6 : "Madge Networks",
0x10B7 : "3Com Corporation",
0x10B8 : "Standard Microsystems Corporation",
0x10B9 : "Ali Corporation",
0x10BA : "Mitsubishi Electronics Corp.",
0x10BB : "Dapha Electronics Corporation",
0x10BC : "Advanced Logic Research Inc.",
0x10BD : "Surecom Technology",
0x10BE : "Tsenglabs International Corp.",
0x10BF : "MOST Corp.",
0x10C0 : "Boca Research Inc.",
0x10C1 : "ICM Corp. Ltd.",
0x10C2 : "Auspex Systems Inc.",
0x10C3 : "Samsung Semiconductors",
0x10C4 : "Award Software Int'l Inc.",
0x10C5 : "Xerox Corporation",
0x10C6 : "Rambus Inc.",
0x10C8 : "Neomagic Corporation",
0x10C9 : "Dataexpert Corporation",
0x10CA : "Fujitsu Siemens",
0x10CB : "Omron Corporation",
0x10CD : "Advanced System Products",
0x10CF : "Fujitsu Ltd.",
0x10D1 : "Future+ Systems",
0x10D2 : "Molex Incorporated",
0x10D3 : "Jabil Circuit Inc.",
0x10D4 : "Hualon Microelectronics",
0x10D5 : "Autologic Inc.",
0x10D6 : "Wilson .co .ltd",
0x10D7 : "BCM Advanced Research",
0x10D8 : "Advanced Peripherals Labs",
0x10D9 : "Macronix International Co. Ltd.",
0x10DB : "Rohm Research",
0x10DC : "CERN-European Lab. for Particle Physics",
0x10DD : "Evans & Sutherland",
0x10DE : "vtrkavxfng",
0x10DF : "Emulex Corporation",
0x10E1 : "Tekram Technology Corp. Ltd.",
0x10E2 : "Aptix Corporation",
0x10E3 : "Tundra Semiconductor Corp.",
0x10E4 : "Tandem Computers",
0x10E5 : "Micro Industries Corporation",
0x10E6 : "Gainbery Computer Products Inc.",
0x10E7 : "Vadem",
0x10E8 : "Applied Micro Circuits Corp.",
0x10E9 : "Alps Electronic Corp. Ltd.",
0x10EA : "Tvia, Inc.",
0x10EB : "Artist Graphics",
0x10EC : "Realtek Semiconductor Corp.",
0x10ED : "Ascii Corporation",
0x10EE : "Xilinx Corporation",
0x10EF : "Racore Computer Products",
0x10F0 : "Curtiss-Wright Controls Embedded Computing",
0x10F1 : "Tyan Computer",
0x10F2 : "Achme Computer Inc. - GONE !!!!",
0x10F3 : "Alaris Inc.",
0x10F4 : "S-Mos Systems",
0x10F5 : "NKK Corporation",
0x10F6 : "Creative Electronic Systems SA",
0x10F7 : "Matsushita Electric Industrial Corp.",
0x10F8 : "Altos India Ltd.",
0x10F9 : "PC Direct",
0x10FA : "Truevision",
0x10FB : "Thesys Microelectronic's",
0x10FC : "I-O Data Device Inc.",
0x10FD : "Soyo Technology Corp. Ltd.",
0x10FE : "Fast Electronic GmbH",
0x10FF : "Ncube",
0x1100 : "Jazz Multimedia",
0x1101 : "Initio Corporation",
0x1102 : "Creative Technology LTD.",
0x1103 : " HighPoint Technologies, Inc.",
0x1104 : "Rasterops",
0x1105 : "Sigma Designs Inc.",
0x1106 : "VIA Technologies, Inc.",
0x1107 : "Stratus Computer",
0x1108 : "Proteon Inc.",
0x1109 : "Adaptec/Cogent Data Technologies",
0x110A : "Siemens Nixdorf AG",
0x110B : "Chromatic Research Inc",
0x110C : "Mini-Max Technology Inc.",
0x110D : "ZNYX Corporation",
0x110E : "CPU Technology",
0x110F : "Ross Technology",
0x1112 : "Osicom Technologies Inc.",
0x1113 : "Accton Technology Corporation",
0x1114 : "Atmel Corp.",
0x1116 : "Data Translation, Inc.",
0x1117 : "Datacube Inc.",
0x1118 : "Berg Electronics",
0x1119 : "ICP vortex Computersysteme GmbH",
0x111A : "Efficent Networks",
0x111C : "Tricord Systems Inc.",
0x111D : "Integrated Device Technology Inc.",
0x111F : "Precision Digital Images",
0x1120 : "EMC Corp.",
0x1121 : "Zilog",
0x1123 : "Excellent Design Inc.",
0x1124 : "Leutron Vision AG",
0x1125 : "Eurocore/Vigra",
0x1127 : "FORE Systems",
0x1129 : "Firmworks",
0x112A : "Hermes Electronics Co. Ltd.",
0x112C : "Zenith Data Systems",
0x112D : "Ravicad",
0x112E : "Infomedia",
0x1130 : "Computervision",
0x1131 : "NXP Semiconductors N.V.",
0x1132 : "Mitel Corp.",
0x1133 : "Eicon Networks Corporation",
0x1134 : "Mercury Computer Systems Inc.",
0x1135 : "Fuji Xerox Co Ltd",
0x1136 : "Momentum Data Systems",
0x1137 : "Cisco Systems Inc",
0x1138 : "Ziatech Corporation",
0x1139 : "Dynamic Pictures Inc",
0x113A : "FWB  Inc",
0x113B : "Network Computing Devices",
0x113C : "Cyclone Microsystems Inc.",
0x113D : "Leading Edge Products Inc",
0x113E : "Sanyo Electric Co",
0x113F : "Equinox Systems",
0x1140 : "Intervoice Inc",
0x1141 : "Crest Microsystem Inc",
0x1142 : "Alliance Semiconductor",
0x1143 : "Netpower Inc",
0x1144 : "Cincinnati Milacron",
0x1145 : "Workbit Corp",
0x1146 : "Force Computers",
0x1147 : "Interface Corp",
0x1148 : "Marvell Semiconductor Germany GmbH",
0x1149 : "Win System Corporation",
0x114A : "VMIC",
0x114B : "Canopus corporation",
0x114C : "Annabooks",
0x114D : "IC Corporation",
0x114E : "Nikon Systems Inc",
0x114F : "Digi International",
0x1150 : "Thinking Machines Corporation",
0x1151 : "JAE Electronics Inc.",
0x1153 : "Land Win Electronic Corp",
0x1154 : "Melco Inc",
0x1155 : "Pine Technology Ltd",
0x1156 : "Periscope Engineering",
0x1157 : "Avsys Corporation",
0x1158 : "Voarx R&D Inc",
0x1159 : "Mutech",
0x115A : "Harlequin Ltd",
0x115B : "Parallax Graphics",
0x115C : "Photron Ltd.",
0x115D : "Xircom",
0x115E : "Peer Protocols Inc",
0x115F : "Maxtor Corporation",
0x1160 : "Megasoft Inc",
0x1161 : "PFU Ltd",
0x1162 : "OA Laboratory Co Ltd",
0x1163 : "mohamed alsherif",
0x1164 : "Advanced Peripherals Tech",
0x1165 : "Imagraph Corporation",
0x1166 : "Broadcom / ServerWorks",
0x1167 : "Mutoh Industries Inc",
0x1168 : "Thine Electronics Inc",
0x1169 : "Centre f/Dev. of Adv. Computing",
0x116A : "Luminex Software, Inc",
0x116B : "Connectware Inc",
0x116C : "Intelligent Resources",
0x116E : "Electronics for Imaging",
0x1170 : "Inventec Corporation",
0x1172 : "Altera Corporation",
0x1173 : "Adobe Systems",
0x1174 : "Bridgeport Machines",
0x1175 : "Mitron Computer Inc.",
0x1176 : "SBE",
0x1177 : "Silicon Engineering",
0x1178 : "Alfa Inc",
0x1179 : "Toshiba corporation",
0x117A : "A-Trend Technology",
0x117B : "LG (Lucky Goldstar) Electronics Inc.",
0x117C : "Atto Technology",
0x117D : "Becton & Dickinson",
0x117E : "T/R Systems",
0x117F : "Integrated Circuit Systems",
0x1180 : "Ricoh",
0x1183 : "Fujikura Ltd",
0x1184 : "Forks Inc",
0x1185 : "Dataworld",
0x1186 : "D-Link System Inc",
0x1187 : "Philips Healthcare",
0x1188 : "Shima Seiki Manufacturing Ltd.",
0x1189 : "Matsushita Electronics",
0x118A : "Hilevel Technology",
0x118B : "Hypertec Pty Ltd",
0x118C : "Corollary Inc",
0x118D : "BitFlow Inc",
0x118E : "Hermstedt AG",
0x118F : "Green Logic",
0x1190 : "Tripace",
0x1191 : "Acard Technology Corp.",
0x1192 : "Densan Co. Ltd",
0x1194 : "Toucan Technology",
0x1195 : "Ratoc System Inc",
0x1196 : "Hytec Electronics Ltd",
0x1197 : "Gage Applied Technologies",
0x1198 : "Lambda Systems Inc",
0x1199 : "Attachmate Corp.",
0x119A : "Mind/Share Inc.",
0x119B : "Omega Micro Inc.",
0x119C : "Information Technology Inst.",
0x119D : "Bug Sapporo Japan",
0x119E : "Fujitsu Microelectronics Ltd.",
0x119F : "Bull Hn Information Systems",
0x11A1 : "Hamamatsu Photonics K.K.",
0x11A2 : "Sierra Research and Technology",
0x11A3 : "Deuretzbacher GmbH & Co. Eng. KG",
0x11A4 : "Barco",
0x11A5 : "MicroUnity Systems Engineering Inc.",
0x11A6 : "Pure Data",
0x11A7 : "Power Computing Corp.",
0x11A8 : "Systech Corp.",
0x11A9 : "InnoSys Inc.",
0x11AA : "Actel",
0x11AB : "Marvell Semiconductor",
0x11AC : "Canon Information Systems",
0x11AD : "Lite-On Technology Corp.",
0x11AE : "Scitex Corporation Ltd",
0x11AF : "Avid Technology, Inc.",
0x11B0 : "Quicklogic Corp",
0x11B1 : "Apricot Computers",
0x11B2 : "Eastman Kodak",
0x11B3 : "Barr Systems Inc.",
0x11B4 : "Leitch Technology International",
0x11B5 : "Radstone Technology Ltd.",
0x11B6 : "United Video Corp",
0x11B7 : "Motorola",
0x11B8 : "Xpoint Technologies Inc",
0x11B9 : "Pathlight Technology Inc.",
0x11BA : "Videotron Corp",
0x11BB : "Pyramid Technology",
0x11BC : "Network Peripherals Inc",
0x11BD : "Pinnacle system",
0x11BE : "International Microcircuits Inc",
0x11BF : "Astrodesign Inc.",
0x11C1 : "LSI Corporation",
0x11C2 : "Sand Microelectronics",
0x11C4 : "Document Technologies Ind.",
0x11C5 : "Shiva Corporatin",
0x11C6 : "Dainippon Screen Mfg. Co",
0x11C7 : "D.C.M. Data Systems",
0x11C8 : "Dolphin Interconnect Solutions",
0x11C9 : "MAGMA",
0x11CA : "LSI Systems Inc",
0x11CB : "Specialix International Ltd.",
0x11CC : "Michels & Kleberhoff Computer GmbH",
0x11CD : "HAL Computer Systems Inc.",
0x11CE : "Primary Rate Inc",
0x11CF : "Pioneer Electronic Corporation",
0x11D0 : "BAE SYSTEMS - Manassas",
0x11D1 : "AuraVision Corporation",
0x11D2 : "Intercom Inc.",
0x11D3 : "Trancell Systems Inc",
0x11D4 : "Analog Devices, Inc.",
0x11D5 : "Tahoma Technology",
0x11D6 : "Tekelec Technologies",
0x11D7 : "TRENTON Technology, Inc.",
0x11D8 : "Image Technologies Development",
0x11D9 : "Tec Corporation",
0x11DA : "Novell",
0x11DB : "Sega Enterprises Ltd",
0x11DC : "Questra Corp",
0x11DD : "Crosfield Electronics Ltd",
0x11DE : "Zoran Corporation",
0x11E1 : "Gec Plessey Semi Inc",
0x11E2 : "Samsung Information Systems America",
0x11E3 : "Quicklogic Corp",
0x11E4 : "Second Wave Inc",
0x11E5 : "IIX Consulting",
0x11E6 : "Mitsui-Zosen System Research",
0x11E8 : "Digital Processing Systems Inc",
0x11E9 : "Highwater Designs Ltd",
0x11EA : "Elsag Bailey",
0x11EB : "Formation, Inc",
0x11EC : "Coreco Inc",
0x11ED : "Mediamatics",
0x11EE : "Dome Imaging Systems Inc",
0x11EF : "Nicolet Technologies BV",
0x11F0 : "Triya",
0x11F2 : "Picture Tel Japan KK",
0x11F3 : "Keithley Instruments, Inc",
0x11F4 : "Kinetic Systems Corporation",
0x11F5 : "Computing Devices Intl",
0x11F6 : "Powermatic Data Systems Ltd",
0x11F7 : "Scientific Atlanta",
0x11F8 : "PMC-Sierra Inc.",
0x11F9 : "I-Cube Inc",
0x11FA : "Kasan Electronics Co Ltd",
0x11FB : "Datel Inc",
0x11FD : "High Street Consultants",
0x11FE : "Comtrol Corp",
0x11FF : "Scion Corp",
0x1200 : "CSS Corp",
0x1201 : "Vista Controls Corp",
0x1202 : "Network General Corp",
0x1203 : "Bayer Corporation Agfa Div",
0x1204 : "Lattice Semiconductor Corp",
0x1205 : "Array Corp",
0x1206 : "Amdahl Corp",
0x1208 : "Parsytec GmbH",
0x1209 : "Sci Systems Inc",
0x120A : "Synaptel",
0x120B : "Adaptive Solutions",
0x120D : "Compression Labs Inc.",
0x120E : "Cyclades Corporation",
0x120F : "Essential Communications",
0x1210 : "Hyperparallel Technologies",
0x1211 : "Braintech Inc",
0x1213 : "Applied Intelligent Systems Inc",
0x1214 : "Performance Technologies Inc",
0x1215 : "Interware Co Ltd",
0x1216 : "Purup-Eskofot A/S",
0x1217 : "O2Micro Inc",
0x1218 : "Hybricon Corp",
0x1219 : "First Virtual Corp",
0x121A : "3dfx Interactive Inc",
0x121B : "Advanced Telecommunications Modules",
0x121C : "Nippon Texa Co Ltd",
0x121D : "LiPPERT Embedded Computers GmbH",
0x121E : "CSPI",
0x121F : "Arcus Technology Inc",
0x1220 : "Ariel Corporation",
0x1221 : "Contec Microelectronics Europe BV",
0x1222 : "Ancor Communications Inc",
0x1223 : "Emerson Network Power, Embedded Computing",
0x1224 : "Interactive Images",
0x1225 : "Power I/O Inc.",
0x1227 : "Tech-Source",
0x1228 : "Norsk Elektro Optikk A/S",
0x1229 : "Data Kinesis Inc.",
0x122A : "Integrated Telecom",
0x122B : "LG Industrial Systems Co. Ltd.",
0x122C : "sci-worx GmbH",
0x122D : "Aztech System Ltd",
0x122E : "Absolute Analysis",
0x122F : "Andrew Corp.",
0x1230 : "Fishcamp Engineering",
0x1231 : "Woodward McCoach Inc.",
0x1233 : "Bus-Tech Inc.",
0x1234 : "Technical Corp",
0x1236 : "Sigma Designs, Inc",
0x1237 : "Alta Technology Corp.",
0x1238 : "Adtran",
0x1239 : "The 3DO Company",
0x123A : "Visicom Laboratories Inc.",
0x123B : "Seeq Technology Inc.",
0x123C : "Century Systems Inc.",
0x123D : "Engineering Design Team Inc.",
0x123F : "C-Cube Microsystems",
0x1240 : "Marathon Technologies Corp.",
0x1241 : "DSC Communications",
0x1242 : "JNI Corporation",
0x1243 : "Delphax",
0x1244 : "AVM AUDIOVISUELLES MKTG & Computer GmbH",
0x1245 : "APD S.A.",
0x1246 : "Dipix Technologies Inc",
0x1247 : "Xylon Research Inc.",
0x1248 : "Central Data Corp.",
0x1249 : "Samsung Electronics Co. Ltd.",
0x124A : "AEG Electrocom GmbH",
0x124C : "Solitron Technologies Inc.",
0x124D : "Stallion Technologies",
0x124E : "Cylink",
0x124F : "Infortrend Technology Inc",
0x1250 : "Hitachi Microcomputer System Ltd.",
0x1251 : "VLSI Solution OY",
0x1253 : "Guzik Technical Enterprises",
0x1254 : "Linear Systems Ltd.",
0x1255 : "Optibase Ltd.",
0x1256 : "Perceptive Solutions Inc.",
0x1257 : "Vertex Networks Inc.",
0x1258 : "Gilbarco Inc.",
0x1259 : "Allied Telesyn International",
0x125A : "ABB Power Systems",
0x125B : "Asix Electronics Corp.",
0x125C : "Aurora Technologies Inc.",
0x125D : "ESS Technology",
0x125E : "Specialvideo Engineering SRL",
0x125F : "Concurrent Technologies Inc.",
0x1260 : "Intersil Corporation",
0x1261 : "Matsushita-Kotobuki Electronics Indu",
0x1262 : "ES Computer Co. Ltd.",
0x1263 : "Sonic Solutions",
0x1264 : "Aval Nagasaki Corp.",
0x1265 : "Casio Computer Co. Ltd.",
0x1266 : "Microdyne Corp.",
0x1267 : "S.A. Telecommunications",
0x1268 : "Tektronix",
0x1269 : "Thomson-CSF/TTM",
0x126A : "Lexmark International Inc.",
0x126B : "Adax Inc.",
0x126C : "Nortel Networks Corp.",
0x126D : "Splash Technology Inc.",
0x126E : "Sumitomo Metal Industries Ltd.",
0x126F : "Silicon Motion",
0x1270 : "Olympus Optical Co. Ltd.",
0x1271 : "GW Instruments",
0x1272 : "Telematics International",
0x1273 : "Hughes Network Systems",
0x1274 : "Ensoniq",
0x1275 : "Network Appliance",
0x1276 : "Switched Network Technologies Inc.",
0x1277 : "Comstream",
0x1278 : "Transtech Parallel Systems",
0x1279 : "Transmeta Corp.",
0x127B : "Pixera Corp",
0x127C : "Crosspoint Solutions Inc.",
0x127D : "Vela Research LP",
0x127E : "Winnov L.P.",
0x127F : "Fujifilm",
0x1280 : "Photoscript Group Ltd.",
0x1281 : "Yokogawa Electronic Corp.",
0x1282 : "Davicom Semiconductor Inc.",
0x1283 : "Waldo",
0x1285 : "Platform Technologies Inc.",
0x1286 : "MAZeT GmbH",
0x1287 : "LuxSonor Inc.",
0x1288 : "Timestep Corp.",
0x1289 : "AVC Technology Inc.",
0x128A : "Asante Technologies Inc.",
0x128B : "Transwitch Corp.",
0x128C : "Retix Corp.",
0x128D : "G2 Networks Inc.",
0x128F : "Tateno Dennou Inc.",
0x1290 : "Sord Computer Corp.",
0x1291 : "NCS Computer Italia",
0x1292 : "Tritech Microelectronics Intl PTE",
0x1293 : "Media Reality Technology",
0x1294 : "Rhetorex Inc.",
0x1295 : "Imagenation Corp.",
0x1296 : "Kofax Image Products",
0x1297 : "Shuttle Computer",
0x1298 : "Spellcaster Telecommunications Inc.",
0x1299 : "Knowledge Technology Laboratories",
0x129A : "Curtiss Wright Controls Electronic Systems",
0x129B : "Image Access",
0x129D : "CompCore Multimedia Inc.",
0x129E : "Victor Co. of Japan Ltd.",
0x129F : "OEC Medical Systems Inc.",
0x12A0 : "Allen Bradley Co.",
0x12A1 : "Simpact Inc",
0x12A2 : "NewGen Systems Corp.",
0x12A3 : "Lucent Technologies AMR",
0x12A4 : "NTT Electronics  Corp.",
0x12A5 : "Vision Dynamics Ltd.",
0x12A6 : "Scalable Networks Inc.",
0x12A7 : "AMO GmbH",
0x12A8 : "News Datacom",
0x12A9 : "Xiotech Corp.",
0x12AA : "SDL Communications Inc.",
0x12AB : "Yuan Yuan Enterprise Co. Ltd.",
0x12AC : "MeasureX Corp.",
0x12AD : "MULTIDATA GmbH",
0x12AE : "Alteon Networks Inc.",
0x12AF : "TDK USA Corp.",
0x12B0 : "Jorge Scientific Corp.",
0x12B1 : "GammaLink",
0x12B2 : "General Signal Networks",
0x12B3 : "Interface Corp. Ltd.",
0x12B4 : "Future Tel Inc.",
0x12B5 : "Granite Systems Inc.",
0x12B7 : "Acumen",
0x12B8 : "Korg",
0x12B9 : "3Com Corporation",
0x12BA : "Bittware, Inc",
0x12BB : "Nippon Unisoft Corp.",
0x12BC : "Array Microsystems",
0x12BD : "Computerm Corp.",
0x12BF : "Fujifilm Microdevices",
0x12C0 : "Infimed",
0x12C1 : "GMM Research Corp.",
0x12C2 : "Mentec Ltd.",
0x12C3 : "Holtek Microelectronics Inc.",
0x12C4 : "Connect Tech Inc.",
0x12C5 : "Picture Elements Inc.",
0x12C6 : "Mitani Corp.",
0x12C7 : "Dialogic Corp.",
0x12C8 : "G Force Co. Ltd.",
0x12C9 : "Gigi Operations",
0x12CA : "Integrated Computing Engines, Inc.",
0x12CB : "Antex Electronics Corp.",
0x12CC : "Pluto Technologies International",
0x12CD : "Aims Lab",
0x12CE : "Netspeed Inc.",
0x12CF : "Prophet Systems Inc.",
0x12D0 : "GDE Systems Inc.",
0x12D1 : "Huawei Technologies Co., Ltd.",
0x12D3 : "Vingmed Sound A/S",
0x12D4 : "Ulticom, Inc.",
0x12D5 : "Equator Technologies",
0x12D6 : "Analogic Corp.",
0x12D7 : "Biotronic SRL",
0x12D8 : "Pericom Semiconductor",
0x12D9 : "Aculab Plc.",
0x12DA : "TrueTime",
0x12DB : "Annapolis Micro Systems Inc.",
0x12DC : "Symicron Computer Communication Ltd.",
0x12DD : "Management Graphics Inc.",
0x12DE : "Rainbow Technologies",
0x12DF : "SBS Technologies Inc.",
0x12E0 : "Chase Research PLC",
0x12E1 : "Nintendo Co. Ltd.",
0x12E2 : "Datum Inc. Bancomm-Timing Division",
0x12E3 : "Imation Corp. - Medical Imaging Syst",
0x12E4 : "Brooktrout Technology Inc.",
0x12E6 : "Cirel Systems",
0x12E7 : "Sebring Systems Inc",
0x12E8 : "CRISC Corp.",
0x12E9 : "GE Spacenet",
0x12EB : "Aureal Semiconductor",
0x12EC : "3A International Inc.",
0x12ED : "Optivision Inc.",
0x12EE : "Orange Micro, Inc.",
0x12EF : "Vienna Systems",
0x12F0 : "Pentek",
0x12F1 : "Sorenson Vision Inc.",
0x12F2 : "Gammagraphx Inc.",
0x12F4 : "Megatel",
0x12F5 : "Forks",
0x12F7 : "Cognex",
0x12F8 : "Electronic-Design GmbH",
0x12F9 : "FourFold Technologies",
0x12FB : "Spectrum Signal Processing",
0x12FC : "Capital Equipment Corp",
0x12FE : "esd Electronic System Design GmbH",
0x1303 : "Innovative Integration",
0x1304 : "Juniper Networks Inc.",
0x1307 : "ComputerBoards",
0x1308 : "Jato Technologies Inc.",
0x130A : "Mitsubishi Electric Microcomputer",
0x130B : "Colorgraphic Communications Corp",
0x130F : "Advanet Inc.",
0x1310 : "Gespac",
0x1312 : "Microscan Systems Inc",
0x1313 : "Yaskawa Electric Co.",
0x1316 : "Teradyne Inc.",
0x1317 : "ADMtek Inc",
0x1318 : "Packet Engines, Inc.",
0x1319 : "Forte Media",
0x131F : "SIIG",
0x1325 : "Salix Technologies Inc",
0x1326 : "Seachange International",
0x1328 : "CIFELLI SYSTEMS CORPORATION",
0x1331 : "RadiSys Corporation",
0x1332 : "Curtiss-Wright Controls Embedded Computing",
0x1335 : "Videomail Inc.",
0x133D : "Prisa Networks",
0x133F : "SCM Microsystems",
0x1342 : "Promax Systems Inc",
0x1344 : "Micron Technology, Inc.",
0x1347 : "Spectracom Corporation",
0x134A : "DTC Technology Corp.",
0x134B : "ARK Research Corp.",
0x134C : "Chori Joho System Co. Ltd",
0x134D : "PCTEL Inc.",
0x135A : "Brain Boxes Limited",
0x135B : "Giganet Inc.",
0x135C : "Quatech Inc",
0x135D : "ABB Network Partner AB",
0x135E : "Sealevel Systems Inc.",
0x135F : "I-Data International A-S",
0x1360 : "Meinberg Funkuhren GmbH & Co. KG",
0x1361 : "Soliton Systems K.K.",
0x1363 : "Phoenix Technologies Ltd",
0x1365 : "Hypercope Corp.",
0x1366 : "Teijin Seiki Co. Ltd.",
0x1367 : "Hitachi Zosen Corporation",
0x1368 : "Skyware Corporation",
0x1369 : "Digigram",
0x136B : "Kawasaki Steel Corporation",
0x136C : "Adtek System Science Co Ltd",
0x1375 : "Boeing - Sunnyvale",
0x137A : "Mark Of The Unicorn Inc",
0x137B : "PPT Vision",
0x137C : "Iwatsu Electric Co Ltd",
0x137D : "Dynachip Corporation",
0x137E : "Patriot Scientific Corp.",
0x1380 : "Sanritz Automation Co LTC",
0x1381 : "Brains Co. Ltd",
0x1382 : "Marian - Electronic & Software",
0x1384 : "Stellar Semiconductor Inc",
0x1385 : "Netgear",
0x1387 : "Curtiss-Wright Controls Electronic Systems",
0x1388 : "Hitachi Information Technology Co Ltd",
0x1389 : "Applicom International",
0x138A : "Validity Sensors, Inc.",
0x138B : "Tokimec Inc",
0x138E : "Basler GMBH",
0x138F : "Patapsco Designs Inc",
0x1390 : "Concept Development Inc.",
0x1393 : "Moxa Technologies Co Ltd",
0x1394 : "Level One Communications",
0x1395 : "Ambicom Inc",
0x1396 : "Cipher Systems Inc",
0x1397 : "Cologne Chip Designs GmbH",
0x1398 : "Clarion Co. Ltd",
0x139A : "Alacritech Inc",
0x139D : "Xstreams PLC/ EPL Limited",
0x139E : "Echostar Data Networks",
0x13A0 : "Crystal Group Inc",
0x13A1 : "Kawasaki Heavy Industries Ltd",
0x13A3 : "HI-FN Inc.",
0x13A4 : "Rascom Inc",
0x13A7 : "amc330",
0x13A8 : "Exar Corp.",
0x13A9 : "Siemens Healthcare",
0x13AA : "Nortel Networks - BWA Division",
0x13AF : "T.Sqware",
0x13B1 : "Tamura Corporation",
0x13B4 : "Wellbean Co Inc",
0x13B5 : "ARM Ltd",
0x13B6 : "DLoG Gesellschaft fr elektronische Datentechnik mbH",
0x13B8 : "Nokia Telecommunications OY",
0x13BD : "Sharp Corporation",
0x13BF : "Sharewave Inc",
0x13C0 : "Microgate Corp.",
0x13C1 : "LSI",
0x13C2 : "Technotrend Systemtechnik GMBH",
0x13C3 : "Janz Computer AG",
0x13C7 : "Blue Chip Technology Ltd",
0x13CC : "Metheus Corporation",
0x13CF : "Studio Audio & Video Ltd",
0x13D0 : "B2C2 Inc",
0x13D1 : "AboCom Systems, Inc",
0x13D4 : "Graphics Microsystems Inc",
0x13D6 : "K.I. Technology Co Ltd",
0x13D7 : "Toshiba Engineering Corporation",
0x13D8 : "Phobos Corporation",
0x13D9 : "Apex Inc",
0x13DC : "Netboost Corporation",
0x13DE : "ABB Robotics Products AB",
0x13DF : "E-Tech Inc.",
0x13E0 : "GVC Corporation",
0x13E3 : "Nest Inc",
0x13E4 : "Calculex Inc",
0x13E5 : "Telesoft Design Ltd",
0x13E9 : "Intraserver Technology Inc",
0x13EA : "Dallas Semiconductor",
0x13F0 : "IC Plus Corporation",
0x13F1 : "OCE - Industries S.A.",
0x13F4 : "Troika Networks Inc",
0x13F6 : "C-Media Electronics Inc.",
0x13F9 : "NTT Advanced Technology Corp.",
0x13FA : "Pentland Systems Ltd.",
0x13FB : "Aydin Corp",
0x13FD : "Micro Science Inc",
0x13FE : "Advantech Co., Ltd.",
0x13FF : "Silicon Spice Inc.",
0x1400 : "ArtX Inc",
0x1402 : "Meilhaus Electronic GmbH Germany",
0x1404 : "Fundamental Software Inc",
0x1406 : "Oce Print Logics Technologies S.A.",
0x1407 : "Lava Computer MFG Inc.",
0x1408 : "Aloka Co. Ltd",
0x1409 : "SUNIX Co., Ltd.",
0x140A : "DSP Research Inc",
0x140B : "Ramix Inc",
0x140D : "Matsushita Electric Works Ltd",
0x140F : "Salient Systems Corp",
0x1412 : "IC Ensemble, Inc.",
0x1413 : "Addonics",
0x1415 : "Oxford Semiconductor Ltd - now part of PLX Technology ",
0x1418 : "Kyushu Electronics Systems Inc",
0x1419 : "Excel Switching Corp",
0x141B : "Zoom Telephonics Inc",
0x141E : "Fanuc Co. Ltd",
0x141F : "Visiontech Ltd",
0x1420 : "Psion Dacom PLC",
0x1425 : "Chelsio Communications",
0x1428 : "Edec Co Ltd",
0x1429 : "Unex Technology Corp.",
0x142A : "Kingmax Technology Inc",
0x142B : "Radiolan",
0x142C : "Minton Optic Industry Co Ltd",
0x142D : "Pixstream Inc",
0x1430 : "ITT Aerospace/Communications Division",
0x1433 : "Eltec Elektronik AG",
0x1435 : "RTD Embedded Technologies, Inc.",
0x1436 : "CIS Technology Inc",
0x1437 : "Nissin Inc Co",
0x1438 : "Atmel-Dream",
0x143F : "Lightwell Co Ltd - Zax Division",
0x1441 : "Agie SA.",
0x1443 : "Unibrain S.A.",
0x1445 : "Logical Co Ltd",
0x1446 : "Graphin Co. Ltd",
0x1447 : "Aim GMBH",
0x1448 : "Alesis Studio",
0x144A : "ADLINK Technology Inc",
0x144B : "Loronix Information Systems, Inc.",
0x144D : "sanyo",
0x1450 : "Octave Communications Ind.",
0x1451 : "SP3D Chip Design GMBH",
0x1453 : "Mycom Inc",
0x1458 : "Giga-Byte Technologies",
0x145C : "Cryptek",
0x145F : "Baldor Electric Company",
0x1460 : "Dynarc Inc",
0x1462 : "Micro-Star International Co Ltd",
0x1463 : "Fast Corporation",
0x1464 : "Interactive Circuits & Systems Ltd",
0x1468 : "Ambit Microsystems Corp.",
0x1469 : "Cleveland Motion Controls",
0x146C : "Ruby Tech Corp.",
0x146D : "Tachyon Inc.",
0x146E : "WMS Gaming",
0x1471 : "Integrated Telecom Express Inc",
0x1473 : "Zapex Technologies Inc",
0x1474 : "Doug Carson & Associates",
0x1477 : "Net Insight",
0x1478 : "Diatrend Corporation",
0x147B : "Abit Computer Corp.",
0x147F : "Nihon Unisys Ltd.",
0x1482 : "Isytec - Integrierte Systemtechnik Gmbh",
0x1483 : "Labway Coporation",
0x1485 : "Erma - Electronic GMBH",
0x1489 : "KYE Systems Corporation",
0x148A : "Opto 22",
0x148B : "Innomedialogic Inc.",
0x148C : "C.P. Technology Co. Ltd",
0x148D : "Digicom Systems Inc.",
0x148E : "OSI Plus Corporation",
0x148F : "Plant Equipment Inc.",
0x1490 : "TC Labs Pty Ltd.",
0x1491 : "Futronic ",
0x1493 : "Maker Communications",
0x1495 : "Tokai Communications Industry Co. Ltd",
0x1496 : "Joytech Computer Co. Ltd.",
0x1497 : "SMA Technologie AG",
0x1498 : "Tews Technologies",
0x1499 : "Micro-Technology Co Ltd",
0x149A : "Andor Technology Ltd",
0x149B : "Seiko Instruments Inc",
0x149E : "Mapletree Networks Inc.",
0x149F : "Lectron Co Ltd",
0x14A0 : "Softing GMBH",
0x14A2 : "Millennium Engineering Inc",
0x14A4 : "GVC/BCM Advanced Research",
0x14A9 : "Hivertec Inc.",
0x14AB : "Mentor Graphics Corp.",
0x14B1 : "Nextcom K.K.",
0x14B3 : "Xpeed Inc.",
0x14B4 : "Philips Business Electronics B.V.",
0x14B5 : "Creamware GmbH",
0x14B6 : "Quantum Data Corp.",
0x14B7 : "Proxim Inc.",
0x14B9 : "Aironet Wireless Communication",
0x14BA : "Internix Inc.",
0x14BB : "Semtech Corporation",
0x14BE : "L3 Communications",
0x14C0 : "Compal Electronics, Inc.",
0x14C1 : "Myricom Inc.",
0x14C2 : "DTK Computer",
0x14C4 : "Iwasaki Information Systems Co Ltd",
0x14C5 : "ABB AB (Sweden)",
0x14C6 : "Data Race Inc",
0x14C7 : "Modular Technology Ltd.",
0x14C8 : "Turbocomm Tech Inc",
0x14C9 : "Odin Telesystems Inc",
0x14CB : "Billionton Systems Inc./Cadmus Micro Inc",
0x14CD : "Universal Scientific Ind.",
0x14CF : "TEK Microsystems Inc.",
0x14D4 : "Panacom Technology Corporation",
0x14D5 : "Nitsuko Corporation",
0x14D6 : "Accusys Inc",
0x14D7 : "Hirakawa Hewtech Corp",
0x14D8 : "Hopf Elektronik GMBH",
0x14D9 : "Alpha Processor Inc",
0x14DB : "Avlab Technology Inc.",
0x14DC : "Amplicon Liveline Limited",
0x14DD : "Imodl Inc.",
0x14DE : "Applied Integration Corporation",
0x14E3 : "Amtelco",
0x14E4 : "Broadcom",
0x14EA : "Planex Communications, Inc.",
0x14EB : "Seiko Epson Corporation",
0x14EC : "Acqiris",
0x14ED : "Datakinetics Ltd",
0x14EF : "Carry Computer Eng. Co Ltd",
0x14F1 : "Conexant Systems, Inc. (Formerly Rockwell)",
0x14F2 : "Mobility Electronics, Inc.",
0x14F4 : "Tokyo Electronic Industry Co. Ltd.",
0x14F5 : "Sopac Ltd",
0x14F6 : "Coyote Technologies LLC",
0x14F7 : "Wolf Technology Inc",
0x14F8 : "Audiocodes Inc",
0x14F9 : "AG Communications",
0x14FB : "Transas Marine (UK) Ltd",
0x14FC : "Quadrics Ltd",
0x14FD : "Silex Technology Inc.",
0x14FE : "Archtek Telecom Corp.",
0x14FF : "Twinhead International Corp.",
0x1501 : "Banksoft Canada Ltd",
0x1502 : "Mitsubishi Electric Logistics Support Co",
0x1503 : "Kawasaki LSI USA Inc",
0x1504 : "Kaiser Electronics",
0x1506 : "Chameleon Systems Inc",
0x1507 : "Htec Ltd.",
0x1509 : "First International Computer Inc",
0x150B : "Yamashita Systems Corp",
0x150C : "Kyopal Co Ltd",
0x150D : "Warpspped Inc",
0x150E : "C-Port Corporation",
0x150F : "Intec GMBH",
0x1510 : "Behavior Tech Computer Corp",
0x1511 : "Centillium Technology Corp",
0x1512 : "Rosun Technologies Inc",
0x1513 : "Raychem",
0x1514 : "TFL LAN Inc",
0x1515 : "ICS Advent",
0x1516 : "Myson Technology Inc",
0x1517 : "Echotek Corporation",
0x1518 : "Kontron Modular Computers GmbH (PEP Modular Computers GMBH)",
0x1519 : "Telefon Aktiebolaget LM Ericsson",
0x151A : "Globetek Inc.",
0x151B : "Combox Ltd",
0x151C : "Digital Audio Labs Inc",
0x151D : "Fujitsu Computer Products Of America",
0x151E : "Matrix Corp.",
0x151F : "Topic Semiconductor Corp",
0x1520 : "Chaplet System Inc",
0x1521 : "Bell Corporation",
0x1522 : "Mainpine Limited",
0x1523 : "Music Semiconductors",
0x1524 : "ENE Technology Inc",
0x1525 : "Impact Technologies",
0x1526 : "ISS Inc",
0x1527 : "Solectron",
0x1528 : "Acksys",
0x1529 : "American Microsystems Inc",
0x152A : "Quickturn Design Systems",
0x152B : "Flytech Technology Co Ltd",
0x152C : "Macraigor Systems LLC",
0x152D : "Quanta Computer Inc",
0x152E : "Melec Inc",
0x152F : "Philips - Crypto",
0x1532 : "Echelon Corporation",
0x1533 : "Baltimore",
0x1534 : "Road Corporation",
0x1535 : "Evergreen Technologies Inc",
0x1537 : "Datalex Communcations",
0x1538 : "Aralion Inc.",
0x1539 : "Atelier Informatiques et Electronique Et",
0x153A : "ONO Sokki",
0x153B : "Terratec Electronic GMBH",
0x153C : "Antal Electronic",
0x153D : "Filanet Corporation",
0x153E : "Techwell Inc",
0x153F : "MIPS Technologies, Inc",
0x1540 : "Provideo Multimedia Co Ltd",
0x1541 : "Telocity Inc.",
0x1542 : "Vivid Technology Inc",
0x1543 : "Silicon Laboratories",
0x1544 : "DCM Technologies Ltd.",
0x1545 : "VisionTek",
0x1546 : "IOI Technology Corp.",
0x1547 : "Mitutoyo Corporation",
0x1548 : "Jet Propulsion Laboratory",
0x1549 : "Interconnect Systems Solutions",
0x154A : "Max Technologies Inc.",
0x154B : "Computex Co Ltd",
0x154C : "Visual Technology Inc.",
0x154D : "PAN International Industrial Corp",
0x154E : "Servotest Ltd",
0x154F : "Stratabeam Technology",
0x1550 : "Open Network Co Ltd",
0x1551 : "Smart Electronic Development GMBH",
0x1553 : "Chicony Electronics Co Ltd",
0x1554 : "Prolink Microsystems Corp.",
0x1555 : "Gesytec GmbH",
0x1556 : "PLDA",
0x1557 : "Mediastar Co. Ltd",
0x1558 : "Clevo/Kapok Computer",
0x1559 : "SI Logic Ltd",
0x155A : "Innomedia Inc",
0x155B : "Protac International Corp",
0x155C : "s",
0x155D : "MAC System Co Ltd",
0x155E : "KUKA Roboter GmbH",
0x155F : "Perle Systems Limited",
0x1560 : "Terayon Communications Systems",
0x1561 : "Viewgraphics Inc",
0x1562 : "Symbol Technologies, Inc.",
0x1563 : "A-Trend Technology Co Ltd",
0x1564 : "Yamakatsu Electronics Industry Co Ltd",
0x1565 : "Biostar Microtech Intl Corp",
0x1566 : "Ardent Technologies Inc",
0x1567 : "Jungsoft",
0x1568 : "DDK Electronics Inc",
0x1569 : "Palit Microsystems Inc",
0x156A : "Avtec Systems Inc",
0x156B : "S2io Inc",
0x156C : "Vidac Electronics GMBH",
0x156D : "Alpha-Top Corp",
0x156E : "Alfa Inc.",
0x156F : "M-Systems Flash Disk Pioneers Ltd",
0x1570 : "Lecroy Corporation",
0x1571 : "Contemporary Controls",
0x1572 : "Otis Elevator Company",
0x1573 : "Lattice - Vantis",
0x1574 : "Fairchild Semiconductor",
0x1575 : "Voltaire Advanced Data Security Ltd",
0x1576 : "Viewcast Com",
0x1578 : "Hitt",
0x1579 : "Dual Technology Corporation",
0x157A : "Japan Elecronics Ind. Inc",
0x157B : "Star Multimedia Corp.",
0x157C : "Eurosoft (UK)",
0x157D : "Gemflex Networks",
0x157E : "Transition Networks",
0x157F : "PX Instruments Technology Ltd",
0x1580 : "Primex Aerospace Co.",
0x1581 : "SEH Computertechnik GMBH",
0x1582 : "Cytec Corporation",
0x1583 : "Inet Technologies Inc",
0x1584 : "Uniwill Computer Corporation",
0x1585 : "Marconi Commerce Systems SRL",
0x1586 : "Lancast Inc",
0x1587 : "Konica Corporation",
0x1588 : "Solidum Systems Corp",
0x1589 : "Atlantek Microsystems Pty Ltd",
0x158A : "Digalog Systems Inc",
0x158B : "Allied Data Technologies",
0x158C : "Hitachi Semiconductor & Devices Sales Co",
0x158D : "Point Multimedia Systems",
0x158E : "Lara Technology Inc",
0x158F : "Ditect Coop",
0x1590 : "3pardata Inc.",
0x1591 : "ARN",
0x1592 : "Syba Tech Ltd.",
0x1593 : "Bops Inc",
0x1594 : "Netgame Ltd",
0x1595 : "Diva Systems Corp.",
0x1596 : "Folsom Research Inc",
0x1597 : "Memec Design Services",
0x1598 : "Granite Microsystems",
0x1599 : "Delta Electronics Inc",
0x159A : "General Instrument",
0x159B : "Faraday Technology Corp",
0x159C : "Stratus Computer Systems",
0x159D : "Ningbo Harrison Electronics Co Ltd",
0x159E : "A-Max Technology Co Ltd",
0x159F : "Galea Network Security",
0x15A0 : "Compumaster SRL",
0x15A1 : "Geocast Network Systems Inc",
0x15A2 : "Catalyst Enterprises Inc",
0x15A3 : "Italtel",
0x15A4 : "X-Net OY",
0x15A5 : "Toyota MACS Inc",
0x15A6 : "Sunlight Ultrasound Technologies Ltd",
0x15A7 : "SSE Telecom Inc",
0x15A8 : "Shanghai Communications Technologies Cen",
0x15AA : "Moreton Bay",
0x15AB : "Bluesteel Networks Inc",
0x15AC : "North Atlantic Instruments",
0x15AD : "VMware Inc.",
0x15AE : "Amersham Pharmacia Biotech",
0x15B0 : "Zoltrix International Limited",
0x15B1 : "Source Technology Inc",
0x15B2 : "Mosaid Technologies Inc.",
0x15B3 : "Mellanox Technology",
0x15B4 : "CCI/Triad",
0x15B5 : "Cimetrics Inc",
0x15B6 : "Texas Memory Systems Inc",
0x15B7 : "Sandisk Corp.",
0x15B8 : "Addi-Data GMBH",
0x15B9 : "Maestro Digital Communications",
0x15BA : "Impacct Technology Corp",
0x15BB : "Portwell Inc",
0x15BC : "Agilent Technologies",
0x15BD : "DFI Inc.",
0x15BE : "Sola Electronics",
0x15BF : "High Tech Computer Corp (HTC)",
0x15C0 : "BVM Limited",
0x15C1 : "Quantel",
0x15C2 : "Newer Technology Inc",
0x15C3 : "Taiwan Mycomp Co Ltd",
0x15C4 : "EVSX Inc",
0x15C5 : "Procomp Informatics Ltd",
0x15C6 : "Technical University Of Budapest",
0x15C7 : "Tateyama System Laboratory Co Ltd",
0x15C8 : "Penta Media Co. Ltd",
0x15C9 : "Serome Technology Inc",
0x15CA : "Bitboys OY",
0x15CB : "AG Electronics Ltd",
0x15CC : "Hotrail Inc.",
0x15CD : "Dreamtech Co Ltd",
0x15CE : "Genrad Inc.",
0x15CF : "Hilscher GMBH",
0x15D1 : "Infineon Technologies AG",
0x15D2 : "FIC (First International Computer Inc)",
0x15D3 : "NDS Technologies Israel Ltd",
0x15D4 : "Iwill Corporation",
0x15D5 : "Tatung Co.",
0x15D6 : "Entridia Corporation",
0x15D7 : "Rockwell-Collins Inc",
0x15D8 : "Cybernetics Technology Co Ltd",
0x15D9 : "Super Micro Computer Inc",
0x15DA : "Cyberfirm Inc.",
0x15DB : "Applied Computing Systems Inc.",
0x15DC : "Litronic Inc.",
0x15DD : "Sigmatel Inc.",
0x15DE : "Malleable Technologies Inc",
0x15E0 : "Cacheflow Inc",
0x15E1 : "Voice Technologies Group",
0x15E2 : "Quicknet Technologies Inc",
0x15E3 : "Networth Technologies Inc",
0x15E4 : "VSN Systemen BV",
0x15E5 : "Valley Technologies Inc",
0x15E6 : "Agere Inc.",
0x15E7 : "GET Engineering Corp.",
0x15E8 : "National Datacomm Corp.",
0x15E9 : "Pacific Digital Corp.",
0x15EA : "Tokyo Denshi Sekei K.K.",
0x15EB : "Drsearch GMBH",
0x15EC : "Beckhoff Automation GmbH",
0x15ED : "Macrolink Inc",
0x15EE : "IN Win Development Inc.",
0x15EF : "Intelligent Paradigm Inc",
0x15F0 : "B-Tree Systems Inc",
0x15F1 : "Times N Systems Inc",
0x15F2 : "SPOT Imaging Solutions a division of Diagnostic Instruments, Inc",
0x15F3 : "Digitmedia Corp.",
0x15F4 : "Valuesoft",
0x15F5 : "Power Micro Research",
0x15F6 : "Extreme Packet Device Inc",
0x15F7 : "Banctec",
0x15F8 : "Koga Electronics Co",
0x15F9 : "Zenith Electronics Co",
0x15FA : "Axzam Corporation",
0x15FB : "Zilog Inc.",
0x15FC : "Techsan Electronics Co Ltd",
0x15FD : "N-Cubed.Net",
0x15FE : "Kinpo Electronics Inc",
0x15FF : "Fastpoint Technologies Inc.",
0x1600 : "Northrop Grumman - Canada Ltd",
0x1601 : "Tenta Technology",
0x1602 : "Prosys-TEC Inc.",
0x1603 : "Nokia Wireless Business Communications",
0x1604 : "Central System Research Co Ltd",
0x1605 : "Pairgain Technologies",
0x1606 : "Europop AG",
0x1607 : "Lava Semiconductor Manufacturing Inc.",
0x1608 : "Automated Wagering International",
0x1609 : "Sciemetric Instruments Inc",
0x160A : "Kollmorgen Servotronix",
0x160B : "Onkyo Corp.",
0x160C : "Oregon Micro Systems Inc.",
0x160D : "Aaeon Electronics Inc",
0x160E : "CML Emergency Services",
0x160F : "ITEC Co Ltd",
0x1610 : "Tottori Sanyo Electric Co Ltd",
0x1611 : "Bel Fuse Inc.",
0x1612 : "Telesynergy Research Inc.",
0x1613 : "System Craft Inc.",
0x1614 : "Jace Tech Inc.",
0x1615 : "Equus Computer Systems Inc",
0x1616 : "Iotech Inc.",
0x1617 : "Rapidstream Inc",
0x1618 : "Esec SA",
0x1619 : "FarSite Communications Limited",
0x161B : "Mobilian Israel Ltd",
0x161C : "Berkshire Products",
0x161D : "Gatec",
0x161E : "Kyoei Sangyo Co Ltd",
0x161F : "Arima Computer Corporation",
0x1620 : "Sigmacom Co Ltd",
0x1621 : "Lynx Studio Technology Inc",
0x1622 : "Nokia Home Communications",
0x1623 : "KRF Tech Ltd",
0x1624 : "CE Infosys GMBH",
0x1625 : "Warp Nine Engineering",
0x1626 : "TDK Semiconductor Corp.",
0x1627 : "BCom Electronics Inc",
0x1629 : "Kongsberg Spacetec a.s.",
0x162A : "Sejin Computerland Co Ltd",
0x162B : "Shanghai Bell Company Limited",
0x162C : "C&H Technologies Inc",
0x162D : "Reprosoft Co Ltd",
0x162E : "Margi Systems Inc",
0x162F : "Rohde & Schwarz GMBH & Co KG",
0x1630 : "Sky Computers Inc",
0x1631 : "NEC Computer International",
0x1632 : "Verisys Inc",
0x1633 : "Adac Corporation",
0x1634 : "Visionglobal Network Corp.",
0x1635 : "Decros / S.ICZ a.s.",
0x1636 : "Jean Company Ltd",
0x1637 : "NSI",
0x1638 : "Eumitcom Technology Inc",
0x163A : "Air Prime Inc",
0x163B : "Glotrex Co Ltd",
0x163C : "intel",
0x163D : "Heidelberg Digital LLC",
0x163E : "3dpower",
0x163F : "Renishaw PLC",
0x1640 : "Intelliworxx Inc",
0x1641 : "MKNet Corporation",
0x1642 : "Bitland",
0x1643 : "Hajime Industries Ltd",
0x1644 : "Western Avionics Ltd",
0x1645 : "Quick-Serv. Computer Co. Ltd",
0x1646 : "Nippon Systemware Co Ltd",
0x1647 : "Hertz Systemtechnik GMBH",
0x1648 : "MeltDown Systems LLC",
0x1649 : "Jupiter Systems",
0x164A : "Aiwa Co. Ltd",
0x164C : "Department Of Defense",
0x164D : "Ishoni Networks",
0x164E : "Micrel Inc.",
0x164F : "Datavoice (Pty) Ltd.",
0x1650 : "Admore Technology Inc.",
0x1651 : "Chaparral Network Storage",
0x1652 : "Spectrum Digital Inc.",
0x1653 : "Nature Worldwide Technology Corp",
0x1654 : "Sonicwall Inc",
0x1655 : "Dazzle Multimedia Inc.",
0x1656 : "Insyde Software Corp",
0x1657 : "Brocade Communications Systems",
0x1658 : "Med Associates Inc.",
0x1659 : "Shiba Denshi Systems Inc.",
0x165A : "Epix Inc.",
0x165B : "Real-Time Digital Inc.",
0x165C : "Kondo Kagaku",
0x165D : "Hsing Tech. Enterprise Co. Ltd.",
0x165E : "Hyunju Computer Co. Ltd.",
0x165F : "Comartsystem Korea",
0x1660 : "Network Security Technologies Inc. (NetSec)",
0x1661 : "Worldspace Corp.",
0x1662 : "Int Labs",
0x1663 : "Elmec Inc. Ltd.",
0x1664 : "Fastfame Technology Co. Ltd.",
0x1665 : "Edax Inc.",
0x1666 : "Norpak Corporation",
0x1667 : "CoSystems Inc.",
0x1668 : "Actiontec Electronics Inc.",
0x166A : "Komatsu Ltd.",
0x166B : "Supernet Inc.",
0x166C : "Shade Ltd.",
0x166D : "Sibyte Inc.",
0x166E : "Schneider Automation Inc.",
0x166F : "Televox Software Inc.",
0x1670 : "Rearden Steel",
0x1671 : "Atan Technology Inc.",
0x1672 : "Unitec Co. Ltd.",
0x1673 : "pctel",
0x1675 : "Square Wave Technology",
0x1676 : "Emachines Inc.",
0x1677 : "Bernecker + Rainer",
0x1678 : "INH Semiconductor",
0x1679 : "Tokyo Electron Device Ltd.",
0x167F : "iba AG",
0x1680 : "Dunti Corp.",
0x1681 : "Hercules",
0x1682 : "PINE Technology, Ltd.",
0x1688 : "CastleNet Technology Inc.",
0x168A : "Utimaco Safeware AG",
0x168B : "Circut Assembly Corp.",
0x168C : "Atheros Communications Inc.",
0x168D : "NMI Electronics Ltd.",
0x168E : "Hyundai MultiCAV Computer Co. Ltd.",
0x168F : "KDS Innotech Corp.",
0x1690 : "NetContinuum, Inc.",
0x1693 : "FERMA",
0x1695 : "EPoX Computer Co., Ltd.",
0x16AE : "SafeNet Inc.",
0x16B3 : "CNF Mobile Solutions",
0x16B8 : "Sonnet Technologies, Inc.",
0x16CA : "Cenatek Inc.",
0x16CB : "Minolta Co. Ltd.",
0x16CC : "Inari Inc.",
0x16D0 : "Systemax",
0x16E0 : "Third Millenium Test Solutions, Inc.",
0x16E5 : "Intellon Corporation",
0x16EC : "U.S. Robotics",
0x16F0 : "LaserLinc Inc.",
0x16F1 : "Adicti Corp.",
0x16F3 : "Jetway Information Co., Ltd",
0x16F6 : "VideoTele.com Inc.",
0x1700 : "Antara LLC",
0x1701 : "Interactive Computer Products Inc.",
0x1702 : "Internet Machines Corp.",
0x1703 : "Desana Systems",
0x1704 : "Clearwater Networks",
0x1705 : "Digital First",
0x1706 : "Pacific Broadband Communications",
0x1707 : "Cogency Semiconductor Inc.",
0x1708 : "Harris Corp.",
0x1709 : "Zarlink Semiconductor",
0x170A : "Alpine Electronics Inc.",
0x170B : "NetOctave Inc.",
0x170C : "YottaYotta Inc.",
0x170D : "SensoMotoric Instruments GmbH",
0x170E : "San Valley Systems, Inc.",
0x170F : "Cyberdyne Inc.",
0x1710 : "Pelago Nutworks",
0x1711 : "MyName Technologies, Inc.",
0x1712 : "NICE Systems Inc.",
0x1713 : "TOPCON Corp.",
0x1725 : "Vitesse Semiconductor",
0x1734 : "Fujitsu-Siemens Computers GmbH",
0x1737 : "LinkSys",
0x173B : "Altima Communications Inc.",
0x1743 : "Peppercon AG",
0x174B : "PC Partner Limited",
0x1752 : "Global Brands Manufacture Ltd.",
0x1753 : "TeraRecon, Inc.",
0x1755 : "Alchemy Semiconductor Inc.",
0x176A : "General Dynamics Canada",
0x1775 : "General Electric",
0x1789 : "Ennyah Technologies Corp",
0x1793 : "Unitech Electronics Co., Ltd",
0x17A1 : "Tascorp",
0x17A7 : "Start Network Technology Co., Ltd.",
0x17AA : "Legend Ltd. (Beijing)",
0x17AB : "Phillips Components",
0x17AF : "Hightech Information Systems, Ltd.",
0x17BE : "Philips Semiconductors",
0x17C0 : "Wistron Corp.",
0x17C4 : "Movita",
0x17CC : "NetChip",
0x17cd : "Cadence Design Systems",
0x17D5 : "Neterion Inc.",
0x17db : "Cray, Inc.",
0x17E9 : "DH electronics GmbH / Sabrent",
0x17EE : "Connect Components, Ltd.",
0x17F3 : "RDC Semiconductor Co., Ltd.",
0x17FE : "INPROCOMM",
0x1813 : "Ambient Technologies Inc",
0x1814 : "Ralink Technology, Corp.",
0x1815 : "devolo AG",
0x1820 : "InfiniCon Systems, Inc.",
0x1824 : "Avocent",
0x1841 : "Panda Platinum",
0x1860 : "Primagraphics Ltd.",
0x186C : "Humusoft S.R.O",
0x1887 : "Elan Digital Systems Ltd",
0x1888 : "Varisys Limited",
0x188D : "Millogic Ltd.",
0x1890 : "Egenera, Inc.",
0x18BC : "Info-Tek Corp.",
0x18C9 : "ARVOO Engineering BV",
0x18CA : "XGI Technology Inc",
0x18F1 : "Spectrum Systementwicklung Microelectronic GmbH",
0x18F4 : "Napatech A/S",
0x18F7 : "Commtech, Inc.",
0x18FB : "Resilience Corporation",
0x1904 : "Ritmo",
0x1905 : "WIS Technology, Inc.",
0x1910 : "Seaway Networks",
0x1912 : "usb 3.0 Renesas Electronics",
0x1931 : "Option NV",
0x1941 : "Stelar",
0x1954 : "One Stop Systems, Inc.",
0x1969 : "Atheros Communications",
0x1971 : "AGEIA Technologies, Inc.",
0x197B : "JMicron Technology Corp.",
0x198a : "Nallatech",
0x1991 : "Topstar Digital Technologies Co., Ltd.",
0x19a2 : "ServerEngines",
0x19A8 : "DAQDATA GmbH",
0x19AC : "Kasten Chase Applied Research",
0x19B6 : "Mikrotik",
0x19E2 : "Vector Informatik GmbH",
0x19E3 : "DDRdrive LLC",
0x1A08 : "Linux Networx",
0x1a41 : "Tilera Corporation",
0x1A42 : "Imaginant",
0x1B13 : "Jaton Corporation USA",
0x1B21 : "Asustek - ASMedia Technology Inc.",
0x1B6F : "Etron",
0x1B73 : "Fresco Logic Inc.",
0x1B91 : "Averna",
0x1BAD : "ReFLEX CES",
0x1C0F : "Monarch Innovative Technologies Pvt Ltd's ",
0x1C32 : "Highland Technology, Inc.",
0x1c39 : "Thomson Video Networks",
0x1DE1 : "Tekram",
0x1FCF : "Miranda Technologies Ltd.",
0x2001 : "Temporal Research Ltd",
0x2646 : "Kingston Technology Co.",
0x270F : "ChainTek Computer Co. Ltd.",
0x2EC1 : "Zenic Inc",
0x3388 : "Hint Corp.",
0x3411 : "Quantum Designs (H.K.) Inc.",
0x3513 : "ARCOM Control Systems Ltd.",
0x38EF : "4links",
0x3D3D : "3Dlabs, Inc. Ltd",
0x4005 : "Avance Logic Inc.",
0x4144 : "Alpha Data",
0x416C : "Aladdin Knowledge Systems",
0x4348 : "wch.cn",
0x4680 : "UMAX Computer Corp.",
0x4843 : "Hercules Computer Technology",
0x4943 : "Growth Networks",
0x4954 : "Integral Technologies",
0x4978 : "Axil Computer Inc.",
0x4C48 : "Lung Hwa Electronics",
0x4C53 : "SBS-OR Industrial Computers",
0x4CA1 : "Seanix Technology Inc",
0x4D51 : "Mediaq Inc.",
0x4D54 : "Microtechnica Co Ltd",
0x4DDC : "ILC Data Device Corp.",
0x4E8 : "Samsung Windows Portable Devices",
0x5053 : "TBS/Voyetra Technologies",
0x508A : "Samsung T10 MP3 Player",
0x5136 : "S S Technologies",
0x5143 : "Qualcomm Inc. USA",
0x5333 : "S3 Graphics Co., Ltd",
0x544C : "Teralogic Inc",
0x5555 : "Genroco Inc.",
0x5853 : "Citrix Systems, Inc.",
0x6409 : "Logitec Corp.",
0x6666 : "Decision Computer International Co.",
0x6945 : "ASMedia Technology Inc.",
0x7604 : "O.N. Electric Co. Ltd.",
0x7d1 : "D-Link Corporation",
0x8080 : "Xirlink, Inc",
0x8086 : "Intel Corporation",
0x8087 : "Intel",
0x80EE : "Oracle Corporation - InnoTek Systemberatung GmbH",
0x8866 : "T-Square Design Inc.",
0x8888 : "Silicon Magic",
0x8E0E : "Computone Corporation",
0x9004 : "Adaptec Inc",
0x9005 : "Adaptec Inc",
0x919A : "Gigapixel Corp",
0x9412 : "Holtek",
0x9699 : "Omni Media Technology Inc.",
0x9710 : "MosChip Semiconductor Technology",
0x9902 : "StarGen, Inc.",
0xA0A0 : "Aopen Inc.",
0xA0F1 : "Unisys Corporation",
0xA200 : "NEC Corp.",
0xA259 : "Hewlett Packard",
0xA304 : "Sony",
0xA727 : "3com Corporation",
0xAA42 : "Scitex Digital Video",
0xAC1E : "Digital Receiver Technology Inc",
0xB1B3 : "Shiva Europe Ltd.",
0xB894 : "Brown & Sharpe Mfg. Co.",
0xBEEF : "Mindstream Computing",
0xC001 : "TSI Telsys",
0xC0A9 : "Micron/Crucial Technology",
0xC0DE : "Motorola",
0xC0FE : "Motion Engineering Inc.",
0xC622 : "Hudson Soft Co Ltd",
0xCA50 : "Varian, Inc",
0xCAFE : "Chrysalis-ITS",
0xCCCC : "Catapult Communications",
0xD4D4 : "Curtiss-Wright Controls Embedded Computing",
0xDC93 : "Dawicontrol",
0xDEAD : "Indigita Corporation",
0xDEAF : "Middle Digital, Inc",
0xE159 : "Tiger Jet Network Inc",
0xE4BF : "EKF Elektronik GMBH",
0xEA01 : "Eagle Technology",
0xEABB : "Aashima Technology B.V.",
0xEACE : "Endace Measurement Systems Ltd.",
0xECC0 : "Echo Digital Audio Corporation",
0xEDD8 : "ARK Logic, Inc",
0xF5F5 : "F5 Networks Inc.",
0xFA57 : "Interagon AS",
}


DEVICES = {

0x0033 : { 0x002F : "ieee 1394 controller",
           0x0033 : "1ACPIGenuineIntel_-_x86_Family_6_Model_23_0",
         },
0x003D : { 0x003d : "1740pci",
           0x00D1 : "i740 PCI",
         },
0x0070 : { 0x6800 : "Hauppage Nova -TD-500 DVB-T Tuner Device",
           0x6800 : "Hauppage Nova -TD-500 DVB-T Tuner Device",
         },
0x0402 : { 0x5606 : "0x2592",
           0x9665 : "  ZCT8YBT",
         },
0x046D : { 0x0805 : "n.a.",
           0x0808 : "Logitech Webcam C600",
           0x0809 : "Webcam Pro 9000",
           0x082B : "n/a",
           0x0896 : "Camera",
           0x08AD : "Quickcam Communicate STX",
           0x08AF : "-",
           0x08b2 : "logitech QuickCam Pro 4000",
           0x08C6 : "Logitech OEM Webcam",
           0x08f0 : "n/a",
           0x08F6 : "QuickCam Communicate",
           0x092F : "model number: V-UAP9",
           0x0A0B : "Logitech ClearChat Pro USB",
           0x0A1F : "Logitech G930 Headset",
           0x5a61 : "",
           0xC018 : "Baesline 3 Button Corded Optical Mouse",
           0xC045 : "Epoxy Hidden",
           0xC046 : "n/a",
           0xc05b : "ftht",
           0xC063 : "DELL 6-Button mouse",
           0xC226 : "n/a",
           0xC227 : "n/a",
           0xC281 : "Wingman Force J-UA9",
           0xC312 : "n/a",
           0xC404 : "Logitech TrackMan Wheel",
           0xC50E : " C-BS35",
           0xC512 : "n/a",
           0xc51e : "Unknown",
           0xC526 : "n/a",
           0xC52A : "HID Keyboard Device",
           0xC52B : "N/A",
           0xC52E : "USB3 receiver",
         },
0x0483 : { 0x2016 : "Driver Windows 7",
         },
0x04B3 : { 0x24D5 : "Audio Controller",
           0x401	 : "PCIVEN_8086&DEV_293E&SUBSYS_20F217AA&REV_033&B1BFB68&0&D8	",
           0x401 : "PCIVEN_8086&DEV_24C5&REV_013",
           0x4010 : "PCIVEN_8086&DEV_1C22&SUBSYS_FCD01179&REV_04",
           0x9876 : "PCIVEN_8086&DEV_293E&SUBSYS_20F217AA&REV_033&B1BFB68&0&D8",
         },
0x04D9 : { 0x1603 : "Samsung",
           0x2011 : "n/a",
         },
0x04F2 : { 0xb008 : ".oem44.inf",
           0xB175 : "SN",
           0xB307 : "Webcam",
         },
0x051D : { 0x0002 : "n/a",
         },
0x0553 : { 0x0200 : " Aiptek USA",
         },
0x058f : { 0x0001 : "AM usb storage",
           0x1234 : "6387",
           0x6362 : "Unknown 4-in-1 card reader (istar)",
           0x6366 : "Multi Flash Reader USB Device",
           0x6387 : "Transcend JetFlash Flash Drive",
           0x9254 : "http://www.alldatasheet.com/datasheet-pdf/pdf/91600/ETC/AU9254A21.html",
           0x9380 : "Micron=MT29F32G08CBABA",
           0x9540 : "SmartCard Reader",
         },
0x0590 : { 0x0028 : "hid device class blood pressure monitor",
         },
0x05ac : { 0x021e : "Keyboard IT USB",
           0x1293 : "Apple iPod",
           0x1297 : "Apple iPhone 01 193700 743771 8 ",
           0x21e : "keyboard It USB ",
         },
0x05E1 : { 0x0408 : "USB 2.0 Video Capture Controller",
           0x0501 : "web cam",
         },
0x064e : { 0x064e : "Suyin",
           0xa101 : "Acer Crystal Eye Webcam",
           0xa103 : "WebCam",
           0xa116 : "USB 2.0 UVC 1.3M WebCam",
           0xA219 : "SUYIN 1.3M WebCam",
           0xc108 : "its a webcam software",
           0xd101 : "Web Cam",
         },
0x067B : { 0x2303 : "Prolific USB 2 Serial Comm Port controller",
           0x2305 : "USB-to-Printer Bridge Controller",
           0x2393 : "prolific",
           0x2506 : "Hi-Speed USB to IDE Bridge Controller",
           0x25a1 : "Prolific PCLinq3 USB Transfer Cable Driver",
           0x9876 : "TES",
         },
0x06FE : { 0x9700 : "a netcard used usb interface",
         },
0x093a : { 0x2468 : "http://genius.ru/products.aspx?pnum=24948&archive=1",
           0x2608 : "USBVID_093A&PID_2608&REV_0100&MI_00",
           0x2620 : "WEBCAM http://www.canyon-tech.com/archive/voip/webcams/CNR-WCAM53#pr-switcher",
         },
0x096E : { 0x0201 : " ",
         },
0x0A5C : { 0x0201 : "Broadcom USB iLine10(tm) Network Adapter",
           0x10DE : "Controlador sm",
           0x2000 : "Broadcom Bluetooth Firmware Upgrade Device",
           0x2009 : "Broadcom Bluetooth Controller",
           0x200a : "Broadcom Bluetooth Controller",
           0x200f : "Broadcom Bluetooth Controller",
           0x201d : "BROADCOM Bluetooth Device",
           0x201e : "IBM Integrated Bluetooth IV",
           0x2020 : "Broadcom Bluetooth Dongle",
           0x2021 : "BCM2035B3 ROM Adapter Generic",
           0x2033 : "Broadcom Blutonium Device Firmware Downloader",
           0x2035 : "BCM92035NMD Bluetooth",
           0x2038 : "Broadcom Blutonium Device Firmware Downloader (BCM2038)",
           0x2039 : "BROADCOM Bluetooth Device",
           0x2045 : "Broadcom Bluetooth Controller",
           0x2046 : "Broadcom USB Bluetooth Device",
           0x2047 : "Broadcom USB Bluetooth Device",
           0x205e : "Broadcom Bluetooth Firmware Upgrade Device",
           0x2100 : "Broadcom Bluetooth 2.0+eDR USB dongle",
           0x2101 : "Broadcom Bluetooth 2.0+EDR USB dongle",
           0x2102 : "ANYCOM Blue USB-200/250",
           0x2110 : "Broadcom Bluetooth Controller",
           0x2111 : "ANYCOM Blue USB-UHE 200/250",
           0x2120 : "Broadcom 2045 Bluetooth 2.0 USB-UHE Device with trace filter",
           0x2121 : "Broadcom 2045 Bluetooth 2.0 USB Device with trace filter",
           0x2122 : "Broadcom Bluetooth 2.0+EDR USB dongle",
           0x2124 : "2045B3ROM Bluetooth Dongle",
           0x2130 : "Broadcom 2045 Bluetooth 2.0 USB-UHE Device with trace filter",
           0x2131 : "Broadcom 2045 Bluetooth 2.0 USB Device with trace filter",
           0x2140 : "2046 Flash UHE Class 2",
           0x2141 : "2046 Flash non UHE Class 2",
           0x2142 : "2046 Flash non UHE Class 1",
           0x2143 : "2046 Flash non UHE Class 1",
           0x2144 : "2046 Flash non UHE module Class 2",
           0x2145 : "Broadcom BCM9204MD LENO Module",
           0x2146 : "Broadcom 2045 Bluetooth 2.1 USB UHE Dongle",
           0x2147 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x2148 : "Broadcom 2046 Bluetooth 2.1 USB UHE Dongle",
           0x2149 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x214a : "Broadcom 2046 Bluetooth 2.1 USB Module",
           0x214b : "Broadcom 2046 Bluetooth 2.1 USB Module",
           0x214c : "Broadcom 2046 Bluetooth 2.1 USB Module",
           0x214d : "Broadcom Bluetooth 2.1 UHE Module",
           0x214e : "Thinkpad Bluetooth with Enhanced Data Rate II",
           0x214f : "Broadcom 2046 Bluetooth 2.1 USB UHE Dongle",
           0x2150 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x2151 : "Broadcom Bluetooth 2.1 USB Dongle",
           0x2152 : "Broadcom 2046 Bluetooth 2.1 USB UHE Dongle",
           0x2153 : "Broadcom 2046 Bluetooth 2.1 USB UHE Dongle",
           0x2154 : "Broadcom 2046 Bluetooth 2.1 USB UHE Dongle",
           0x2155 : "Broadcom Bluetooth USB Dongle",
           0x2157 : "BCM2046 B1 USB 500",
           0x2158 : "Broadcom 2046 Bluetooth 2.1 Device",
           0x219C : "Broadcom BCM2070 Bluetooth 3.0+HS USB Device ",
           0x21E3 : "Broadcom Bluetooth 4.0",
           0x4500 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x4502 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x4503 : "Broadcom 2046 Bluetooth 2.1 USB Dongle",
           0x5800 : "Unified Security Hub",
           0x5801 : "Unified Security Hub ",
           0x6300 : "Pirelli ISB Remote NDIS Device",
           0x6688 : "NVIDIA GeForce GT 240M",
           0x8613 : "TD 3104 USB vedio grabber ",
           0x9876 : "0x9876",
         },
0x0A92 : { 0x1010 : "1010&REV_0101&MI_00",
         },
0x0AC8 : { 0x1234 : "1",
           0x6719 : "asus",
         },
0x0b05 : { 0x170C : " RFHID",
         },
0x0c45 : { 0x0C45 : "USB2.0",
           0x1111 : "USB webcam",
           0x5243 : "xda exec Uknown device",
           0x6007 : "Genius WebCam Eye",
           0x600D : "USB(v1.1) webcam",
           0x602C : "Webcam",
           0x602D : "USB Webcam",
           0x6030 : "USB WebCam ",
           0x610C : "usb web camera ",
           0x6128 : "USB WebCam",
           0x6128 : "USB PC Camera Plus",
           0x6129 : "USB WebCam",
           0x6130 : "USB HUB",
           0x613A : "USB WEBCAM",
           0x613c : "USB Webcam",
           0x613E : "USB Camera",
           0x624f : "Integrated Webcam in Compal HEL81 series barebones.",
           0x6270 : "USB Microscopr",
           0x6270 : "webcam with mic link works for win 7",
           0x6270 : "webcam",
           0x627F : "USBVID_17A1&PID_0118&REV_0100",
           0x62B3 : "USB 2.0 PC Camera",
           0x62BF : "USBVid_0c45&Pid_62bf&Rev_0100",
           0x62c0 : "Sonix Wecam",
           0x6353 : "USB Microscope",
           0x641D : "1.3 MPixel Integrated Webcam used in Dell N5010 series",
           0x6421 : "USB 2.0 Webcam slim 32",
           0x642F : "Webcam",
           0x644b : "not known",
           0x6489 : "Integrated Webcam Universal Serial Bus controllers",
           0x6840 : "sonix 1.3 mp laptop integrated webcam",
           0x9876 : "webcam",
         },
0x0cf3 : { 0x1002 : "Wireless USB 2.0 adapter TL-WN821N",
           0x3000 : "&#1085;&#1077;&#1080;&#1079;&#1074;&#1077;&#1089;&#1090;&#1085;&#1086;&#1077; &#1091;&#1089;&#1090;&",
           0x3002 : "unkown",
           0x3002 : "unknown",
           0x3005 : "Atheros Bluetooth Module",
           0x9271 : "TP-LINK 150 Mbps Wireless Lite N Adapter TL-WN721N",
         },
0x0D8C : { 0x0102 : "6206lc",
           0x5200 : "0x5200",
         },
0x0DF6 : { 0x9071 : "t9071t   WL-113 - Wireless Network USB dongle 54g  ",
         },
0x0E11 : { 0x0001 : "PCI to EISA Bridge",
           0x0002 : "PCI to ISA Bridge",
           0x000F : "StorageWorks Library Adapter (HVD)",
           0x0012 : "686P7",
           0x0046 : "Smart Array 6400 Controller",
           0x0049 : "Gigabit Upgrade Module",
           0x004A : "Gigabit Server Adapter",
           0x005A : "HP Remote Insight Lights-Out II Board",
           0x00B1 : "HP Remote Insight Lights-Out II PCI Device",
           0x00C0 : "64Bit",
           0x0508 : "PCI UTP/STP Controller",
           0x1000 : "Pentium Bridge",
           0x2000 : "Pentium Bridge",
           0x3032 : "GUI Accelerator",
           0x3033 : "GUI Accelerator",
           0x3034 : "GUI Accelerator",
           0x4000 : "Pentium Bridge",
           0x6010 : "HotPlug PCI Bridge",
           0x7020 : "USB Controller",
           0xA0EC : "Original Compaq fibre Channel HBA",
           0xA0F0 : "Advanced System Management Controller",
           0xA0F3 : "Triflex PCI to ISA PnP Bridge",
           0xA0F7 : " device 4",
           0xA0F8 : "USB Open Host Controller",
           0xA0FC : "Tachyon TL 64-bit/66-Mhz FC HBA",
           0xAe10 : "Smart-2 Array Controller",
           0xAE29 : "PCI to ISA Bridge",
           0xAE2A : "CPU to PCI Bridge",
           0xAE2B : "PCI to ISA PnP Bridge",
           0xAE31 : "System Management Controller",
           0xAE32 : "Netelligent 10/100 TX PCI UTP TLAN 2.3",
           0xAE33 : "Dual EIDE Controller",
           0xAE34 : "Netelligent 10 T PCI UTP TLAN 2.3",
           0xAE35 : "Integrated NetFlex 3/P TLAN 2.3",
           0xAE40 : "Dual Port Netelligent 10/100 TX PCI TLAN",
           0xAE43 : "Integrated Netelligent 10/100 TX PCI",
           0xAE69 : "PCI to ISA Bridge",
           0xAE6C : "PCI Bridge",
           0xAE6D : "CPU to PCI Bridge",
           0xB011 : "Dual Port Netelligent 10/100 TX",
           0xB012 : "UTP/Coax PCI",
           0xB01E : "Fast Ethernet NIC",
           0xB01F : "Fast Ethernet NIC",
           0xB02F : "Ethernet NIC",
           0xB030 : "10/100TX Embedded UTP/Coax Controller",
           0xB04A : "10/100TX WOL UTP Controller",
           0XB060 : "SMART2 Array Controller",
           0xB0C6 : "Fast Ethernet Embedded Controller w/ WOL",
           0xB0C7 : "Fast Ethernet NIC",
           0xB0D7 : "Fast Ethernet NIC",
           0xB0DD : "Fast Ethernet NIC",
           0xB0DE : "Fast Ethernet NIC",
           0xB0DF : "Gigabit Module",
           0xB0E0 : "Gigabit Module",
           0xB0E1 : "Fast Ethernet Module",
           0xB123 : "Gigabit NIC",
           0xB134 : "Fast Ethernet NIC",
           0xB13C : "Fast Ethernet NIC",
           0xB144 : "Fast Ethernet NIC",
           0xB163 : "Fast Ethernet NIC",
           0xB164 : "Fast Ethernet Upgrade Module",
           0xB178 : "SMART2 Array Controller",
           0xB196 : "Conexant SoftK56 Modem",
           0xB1A4 : "Gigabit Server Adapter",
           0xB203 : "Integrated Lights Out Processor",
           0xB204 : "Integrated Lights Out Processor",
           0xF095 : "HP StorageWorks 2 Gb",
           0xF130 : "ThunderLAN 1.0 NetFlex-3/P",
           0xF150 : "ThunderLAN 2.3 NetFlex-3/P with BNC",
           0xF700 : "LP7000 Compaq/Emulex Fibre Channel HBA",
           0xF800 : "LP8000 Compaq/Emulex Fibre Channel HBA",
         },
0x0E8D : { 0x0002 : "PCI Simple Communications Controller",
           0x0003 : "usb",
         },
0x1000 : { 0x0001 : "PCI-SCSI I/O Processor",
           0x0002 : "Fast-wide SCSI gg",
           0x0003 : "PCI to SCSI I/O Processor",
           0x0004 : "SCSI raid controllers",
           0x0005 : "Fast SCSI",
           0x0006 : "PCI to Ultra SCSI I/O Processor",
           0x000A : "PCI Dual Channel Wide Ultra2 SCSI Ctrlr",
           0x000B : "PCI Dual Channel Wide Ultra2 SCSI Ctrlr",
           0x000C : "PCI to Ultra2 SCSI I/O Processor",
           0x000D : "Ultra Wide SCSI",
           0x000F : "PCI to Ultra SCSI I/O Processor",
           0x0010 : "I2O-Ready PCI RAID Ultra2 SCSI Ctrlr",
           0x0012 : "PCI to Ultra2 SCSI Controller",
           0x0013 : "PCI to Ultra SCSI Controller",
           0x0020 : "PCI to Dual Channel Ultra3 SCSI Ctrlr",
           0x0021 : "PCI to Ultra160 SCSI Controller",
           0x0030 : "PCI-X to Ultra320 SCSI Controller",
           0x0031 : "PCI-X SCSI Controller",
           0x0032 : "PCI-X to Ultra320 SCSI Controller",
           0x0035 : "PCI-X SCSI Controller",
           0x0040 : "PCI-X to Ultra320 SCSI Controller",
           0x0050 : "LSISAS1068E / LSI SAS 6i RAID Controller",
           0x0054 : "PCI-X Fusion-MPT SAS",
           0x0056 : "PCI-Express Fusion-MPT SAS",
           0x0058 : "PCI-Express Fusion-MPT SAS",
           0x005e : "PCI-X Fusion-MPT SAS",
           0x0060 : "0x10f9",
           0x0062 : "PCI-Express Fusion-MPT SAS",
           0x0064 : "PCI-Express Fusion-MPT SAS 2.0",
           0x0072 : "Dell PERC H200",
           0x0073 : "IBM ServeRAID M1015",
           0x008F : "LSI 53C8xx SCSI host adapter chip",
           0x0408 : "U320-2E Raid Controller",
           0x0621 : "Fibre Channel I/O Processor",
           0x0622 : "Dial Channel Fibre Channel I/O Processor",
           0x0623 : "Dual Channel Fibre Channel I/O Processor",
           0x0624 : "Fibre Channel I/O Processor",
           0x0625 : "Fibre Channel I/O Processor",
           0x0626 : "Fibre Channel Adapter",
           0x0628 : "Fibre Channel Adapter",
           0x0630 : "Fibre Channel I/O Processor",
           0x0640 : "Fibre Channel Adapter",
           0x0642 : "Fibre Channel Adapter",
           0x0646 : "Fibre Channel Adapter",
           0x0701 : "10/100 MBit Ethernet",
           0x0702 : "Gigabit Ethernet Controller",
           0x0901 : "USB Controller",
           0x1000 : "Fast SCSI Controller",
           0x1001 : "Symbios Ultra2 SCSI controller",
           0x1010 : "Single channel SCSI controller",
           0x1020 : "LSI Logic MegaRAID 320-1 Dell PowerEdge PERC 4/SC",
           0x1960 : "RAID Controller",
           0x9876 : "5946504E44383243",
         },
0x1001 : { 0x0010 : "PCI 1616",
           0x0011 : "OPTO-PCI",
           0x0012 : "PCI-AD",
           0x0013 : "PCI-OptoRel",
           0x0014 : "Timer",
           0x0015 : "PCI-DAC416",
           0x0016 : "PCI-MFB high-speed analog I/O",
           0x0017 : "PROTO-3 PCI",
           0x0020 : "Universal digital I/O PCI-Interface",
         },
0x1002 : { 0x4370 : "RV370",
           0x0000 : "{4D36E968-E325-11CE-BFC1-08002BE10318}",
           0x0002 : "EMU10K1",
           0x000D : "bhjkh",
           0x0180 : "LXPAY0Y001926158A92000        ",
           0x0300 : "1002",
           0x0B12 : "R580",
           0x1002 : "0F2A1787",
           0x1002 : "RV360",
           0x1043 : "RV410",
           0x11 : "0x215r2qzua21",
           0x1111 : "ATI Technologies Inc. / Advanced Micro Devices",
           0x1714 : "A4-3400",
           0x1ab8 : "2",
           0x3150 : "M24",
           0x3151 : "RV380",
           0x3152 : "M24",
           0x3154 : "M24GL",
           0x3171 : "RV380",
           0x3E50 : "PCIVEN_1002&DEV_3E50&SUBSYS_0410174B&REV_004&243",
           0x3E54 : "RV380GL",
           0x3E70 : "RV380",
           0x3E74 : "RV380GL",
           0x4136 : "A3",
           0x4137 : "RS200",
           0x4143 : "9550",
           0x4144 : "R300",
           0x4145 : "R300",
           0x4146 : "R300",
           0x4147 : "R300GL",
           0x4148 : "R350",
           0x4149 : "R350",
           0x4150 : "RV350",
           0x4151 : "RV350",
           0x4152 : "RV360",
           0x4153 : "RV350",
           0x4154 : "RV350GL",
           0x4155 : "RV350",
           0x4158 : "0x5954",
           0x4164 : "R300",
           0x4166 : "R300",
           0x4167 : "R300GL",
           0x4168 : "R350",
           0x4169 : "R350",
           0x4170 : "RV350",
           0x4171 : "RV350",
           0x4172 : "REV_00",
           0x4173 : "RV350",
           0x4174 : "RV350GL",
           0x4175 : "RV350",
           0x4242 : "R200AIW",
           0x4243 : "",
           0x4336 : "rs200",
           0x4337 : "RS200M",
           0x4341 : "SB200",
           0x4342 : "SB200",
           0x4345 : "SB200",
           0x4347 : "SB200",
           0x4348 : "SB200",
           0x4349 : "SB200",
           0x434C : "SB200",
           0x434d : "SB200",
           0x4353 : "SB200",
           0x4354 : "215CT",
           0x4358 : "210888CX",
           0x4361 : "ALC665",
           0x4363 : "SB300",
           0x4369 : "IXP 3xx",
           0x436E : "IXP 3xx",
           0x4370 : "SB400",
           0x4371 : "IXP SB400",
           0x4372 : "SMBus Controller",
           0x4373 : "IXP SB400",
           0x4374 : "IXP SB400",
           0x4375 : "IXP SB400",
           0x4376 : "SB4xx",
           0x4377 : "IXP SB400",
           0x4378 : "SB400",
           0x4379 : "SB400 / SB450 (Sil3112)",
           0x437A : "SB4xx",
           0x437B : "SB450",
           0x4380 : "ATI SB600",
           0x4380 : "ATI SB600",
           0x4380 : "ATI RS690m",
           0x4381 : "ATI ?",
           0x4383 : "SB700",
           0x4385 : "ATI RD600/RS600",
           0x4386 : "690G",
           0x438C : "RD600/RS600",
           0x438D : "SB600",
           0x439 : "rv360",
           0x4390 : "SB750",
           0x4391 : "ATI SB700",
           0x4391 : "9H54474G00579",
           0x4392 : "ATI SB700",
           0x4393 : "ATI SB850",
           0x4394 : "5100",
           0x4396 : "210888CX",
           0x4398 : "SB700",
           0x439C : "SB7xx",
           0x439D : "SB700 LPC",
           0x4437 : "ATI Mobility Radeon 7000 IGP",
           0x4554 : "Mach64 ET",
           0x4654 : "Mach64 VT",
           0x4742 : "(GT-C2U2)",
           0x4744 : "Rage 3D Pro AGP 2x",
           0x4747 : "GT-C2U2",
           0x4749 : "RAGE PRO TURBO AGP 2X",
           0x474C : "Rage XC PCI-66",
           0x474D : "Rage XL AGP 2x",
           0x474E : "Rage XC AGP 2x",
           0x474F : "Rage XL PCI-66",
           0x4750 : "1039",
           0x4751 : "0x1002",
           0x4752 : "Rage XL PCI",
           0x4753 : "Rage XC PCI",
           0x4754 : "Mach 64 VT",
           0x4755 : "Rage 3D II+pci",
           0x4756 : "Rage 3D IIC AGP",
           0x4757 : "3D 11C AGP",
           0x4758 : "210888GX",
           0x4759 : "215r2qzua21",
           0x475A : "215r2qua12",
           0x4966 : "RV250",
           0x4967 : "RV250",
           0x496E : "RV250",
           0x496F : "RV250",
           0x4A48 : "R420",
           0x4a49 : "R420",
           0x4A4A : "R420",
           0x4a4b : "R420",
           0x4A4C : "R420",
           0x4A4D : "R420GL",
           0x4A4E : "M18",
           0x4A4F : "R420",
           0x4A50 : "R420",
           0x4A54 : "R420",
           0x4A68 : "R420",
           0x4A69 : "R420",
           0x4A6A : "R420",
           0x4a6b : "R420",
           0x4A6C : "R420",
           0x4A6D : "R420GL",
           0x4A6F : "R420",
           0x4A70 : "R420",
           0x4A74 : "R420",
           0x4B49 : "R481",
           0x4B4B : "R481",
           0x4B4C : "R481",
           0x4B69 : "R481",
           0x4B6A : "R481",
           0x4B6B : "R481",
           0x4B6C : "R481",
           0x4C42 : "B10E0E11",
           0x4C44 : "Rage 3D LT Pro AGP",
           0x4C45 : "",
           0x4C46 : "Mobility M3 AGP",
           0x4C47 : "ati rage pro",
           0x4C49 : "123",
           0x4C4D : "01541014",
           0x4C4E : "216lo sasa25",
           0x4C50 : "unknown",
           0x4C51 : "113",
           0x4C52 : "1241243",
           0x4C53 : "216L0SASA25",
           0x4C54 : "4372",
           0x4C57 : "M7 [LW]",
           0x4C58 : "",
           0x4C59 : "Mobility 6",
           0x4C5A : "",
           0x4C64 : "",
           0x4C66 : "RV250",
           0x4C6E : "0x4C6E",
           0x4D46 : "ATI mobility128",
           0x4D4C : "216l0sasa25",
           0x4D52 : "ATI Theater 550 Pro",
           0x4D53 : "TVT2 Wonder Elite",
           0x4E44 : "R300",
           0x4E45 : "R300",
           0x4e46 : "R300",
           0x4E47 : "R300GL",
           0x4E48 : "R350",
           0x4E49 : "R350",
           0x4E4A : "R360",
           0x4E4B : "R350GL",
           0x4E50 : "M10",
           0x4E51 : "RV350",
           0x4E52 : "M10",
           0x4E54 : "M10GL",
           0x4E56 : "M12",
           0x4E64 : "R300",
           0x4E65 : "R300",
           0x4e66 : "R300",
           0x4E67 : "R300GL",
           0x4E68 : "R350",
           0x4E69 : "R350",
           0x4E6A : "R360",
           0x4E6B : "R350GL",
           0x4E71 : "RV350",
           0x5041 : "gt",
           0x5042 : "rage 128 pf pro agp ",
           0x5043 : "1231324445",
           0x5044 : "rv100",
           0x5045 : "",
           0x5046 : "R128",
           0x5047 : "215R3BUA22",
           0x5048 : "8212104D",
           0x5049 : "R128",
           0x504A : "Rage 128 Pro PJ PCI",
           0x504B : "Rage 128 Pro PK AGP",
           0x504C : "Rage 128 Pro PL AGP",
           0x504D : "Rage 128 Pro PM PCI",
           0x504E : "Rage 128 Pro PN AGP",
           0x504F : "Rage 128 Pro PO AGP",
           0x5050 : "Scheda Grafica Standard PCI(VGA)",
           0x5051 : "Rage 128 Pro PQ AGP",
           0x5052 : "Rage 128 Pro PR AGP",
           0x5053 : "Rage 128 Pro PS PCI",
           0x5054 : "Rage 128 Pro PT AGP",
           0x5055 : "rage 128 pro agp 4x tmds",
           0x5056 : "Rage 128 Pro PV PCI",
           0x5057 : "Rage 128 Pro PW AGP",
           0x5058 : "Rage 128 Pro",
           0x5144 : "Radeon 7200 QD SDR/DDR",
           0x5145 : "",
           0x5146 : "",
           0x5147 : "",
           0x5148 : "R200",
           0x5149 : "",
           0x514A : "",
           0x514B : "",
           0x514C : "R200",
           0x514D : "R200",
           0x514E : "",
           0x514F : "",
           0x5157 : "RV200",
           0x5158 : "radeon 9700 or 9200",
           0x5159 : "RV100",
           0x515A : "",
           0x515E : "Radeon ES1000",
           0x5168 : "ati",
           0x5169 : "",
           0x516A : "",
           0x516B : "",
           0x516C : "E7505",
           0x516D : "R200",
           0x5245 : "215R2QZUA21",
           0x5246 : "Rage 128",
           0x5247 : "Rage 32MB",
           0x524B : "g01080-108",
           0x524C : "",
           0x5345 : "",
           0x5346 : "Rage 128 SF 4x AGP 2x",
           0x5347 : "",
           0x5348 : "",
           0x534B : "Rage 128 SK PCI",
           0x534C : "Rage 128 SL AGP 2x",
           0x534D : "Rage 128 SM AGP 4x",
           0x534E : "Rage 128 4x",
           0x5354 : "",
           0x5446 : "unknown",
           0x544C : "",
           0x5452 : "",
           0x5455 : "",
           0x5457 : "RS200M",
           0x5460 : "M22",
           0x5461 : "M22",
           0x5462 : "M24C",
           0x5464 : "M22GL",
           0x5548 : "R423",
           0x5549 : "R423",
           0x554A : "R423",
           0x554b : "R423",
           0x554D : "R430",
           0x554E : "R430",
           0x554F : "R430",
           0x5550 : "R423GL",
           0x5551 : "R423GL",
           0x5568 : "R423",
           0x5569 : "R423",
           0x556A : "R423",
           0x556B : "R423",
           0x556D : "R430",
           0x556E : "R430",
           0x556F : "R430",
           0x5570 : "R423GL",
           0x5571 : "R423GL",
           0x564A : "M26GL",
           0x564B : "M26GL",
           0x564F : "M26",
           0x5652 : "M26",
           0x5653 : "RV410",
           0x5654 : "264VT",
           0x5655 : "",
           0x5656 : "Mach 64 VT4 PCI",
           0x5657 : "RV410",
           0x5673 : "M26",
           0x5677 : "RV410",
           0x5830 : "RS300",
           0x5831 : "RS300",
           0x5832 : "RS300",
           0x5833 : "RS300M",
           0x5834 : "RS300",
           0x5835 : "RS300M",
           0x5838 : "RS330M",
           0x5854 : "RS480",
           0x5874 : "RS482",
           0x5940 : "RV280",
           0x5941 : "RV280",
           0x5950 : "RS480",
           0x5954 : "RS482",
           0x5955 : "RS480M",
           0x5960 : "RV280",
           0x5960 : "A051400005470",
           0x5961 : "RV280",
           0x5962 : "RV280",
           0x5964 : "Radeon 9200",
           0x5965 : "unknown",
           0x5974 : "RS482",
           0x5974 : "RS482",
           0x5975 : "RS482M (200M)",
           0x5a23 : "RD890",
           0x5a31 : "RS400/133",
           0x5A33 : "RC410",
           0x5A41 : "0x5A41	ATI RADEON Xpress 1200 Series	0x1002",
           0x5A41 : "RS400",
           0x5A42 : "RS400M",
           0x5A43 : "RS400",
           0x5A60 : "SUBSYS_FF311179",
           0x5A61 : "RC410",
           0x5A61 : "RC410",
           0x5A62 : "http://www.csd.toshiba.com/cgi-bin/tais/support/js",
           0x5A63 : "RC410",
           0x5b60 : "RV370",
           0x5b62 : "RV380x",
           0x5B63 : "REV_004&399D3C6A&0&0008",
           0x5B64 : "RV370GL",
           0x5B65 : "RV370",
           0x5B60 : "RV370",
           0x5B70 : "RV370",
           0x5B72 : "RV380x",
           0x5B73 : "RV370",
           0x5B74 : "RV370GL",
           0x5B75 : "RV370",
           0x5C61 : "bk-ati ver008.016m.085.006",
           0x5C63 : "RV280 (M9+)",
           0x5D44 : "RV280",
           0x5D45 : "RV280",
           0x5D48 : "M28",
           0x5D49 : "M28GL",
           0x5d4a : "M28",
           0x5d4d : "R480",
           0x5d4f : "R480",
           0x5D50 : "R480GL",
           0x5d52 : "R480",
           0x5D57 : "R423",
           0x5d6d : "R480",
           0x5D6F : "R480",
           0x5D70 : "R480GL",
           0x5D72 : "R480",
           0x5D77 : "R423",
           0x5E48 : "RV410GL",
           0x5E4A : "RV410",
           0x5E4B : "RV410",
           0x5E4C : "RV410",
           0x5E4D : "RV410",
           0x5E4F : "RV410",
           0x5E68 : "RV410GL",
           0x5E6A : "RV410",
           0x5E6B : "RV410",
           0x5E6C : "RV410",
           0x5E6D : "RV410",
           0x5E6F : "RV410",
           0x6076 : "123123132",
           0x6718 : "CAYMAN XT",
           0x6719 : "Cayman",
           0x6738 : "HD6870",
           0x6739 : "Barts (Pro)",
           0x673E : "0x2310",
           0x6740 : "Whistler",
           0x6741 : "Whistler",
           0x6741 : "AMD Radeon HD 7450M (6470M)&#12289;6630M&#12289;In",
           0x6749 : "unknown",
           0x674A : "V3900",
           0x6750 : "1996",
           0x6758 : "NI",
           0x6759 : "1996",
           0x6760 : "6470M",
           0x6778 : "7470",
           0x6779 : "AMD Radeon HD 6470m",
           0x677B : "Unknown",
           0x6840 : "SUBSYS",
           0x6898 : "EG CYPRESS XT",
           0x6899 : "EG CYPRESS PRO",
           0x689C : "EG Cypress XT HEMLOCK",
           0x68A0 : "EG BROADWAY XT",
           0x68A1 : "EG BROADWAY PRO/LP",
           0x68A8 : "AMD Radeon HD6870M (at least the one from Dell)",
           0x68B0 : "EG BROADWAY XT",
           0x68B8 : "EG JUNIPER XT",
           0x68BA : "1482174B",
           0x68BE : "EG JUNIPER LE",
           0x68C1 : "DEV_68C1&SUBSYS_144A103C&REV_00",
           0x68C8 : "RV830",
           0x68c9 : "RV830",
           0x68D8 : "Redwood",
           0x68D9 : "RV830/Redwood",
           0x68E0 : "HD 5470",
           0x68E4 : "RV810",
           0x68f9 : "Cedar",
           0x700F : "A3/U1",
           0x7010 : "RS200",
           0x7100 : "R520",
           0x7101 : "M58",
           0x7102 : "M58",
           0x7103 : "M58GL",
           0x7104 : "R520GL",
           0x7105 : "R520GL",
           0x7106 : "M58GL",
           0x7108 : "R520",
           0x7109 : "R520",
           0x710A : "R520",
           0x710B : "R520",
           0x710C : "R520",
           0x710E : "R520GL",
           0x710F : "R520GL",
           0x7120 : "R520",
           0x7124 : "R520GL",
           0x7125 : "R520GL",
           0x7128 : "R520",
           0x7129 : "R520",
           0x712A : "R520",
           0x712B : "R520",
           0x712C : "R520",
           0x712E : "R520GL",
           0x712F : "R520GL",
           0x7140 : "RV515",
           0x7142 : "RV515",
           0x7143 : "RV505",
           0x7145 : "M54",
           0x7146 : "RV505",
           0x7147 : "RV515",
           0x7149 : "M52",
           0x714A : "M52",
           0x714B : "M52",
           0x714C : "M52",
           0x714D : "RV515",
           0x714E : "RV515PCI",
           0x7152 : "RV515GL",
           0x7153 : "RV515GL",
           0x715E : "RV515",
           0x715F : "RV515",
           0x7160 : "RV515",
           0x7162 : "RV515",
           0x7163 : "RV515",
           0x7166 : "RV515",
           0x7167 : "RV515",
           0x716D : "RV515",
           0x716E : "RV515PCI",
           0x7172 : "RV515GL",
           0x7173 : "RV515GL",
           0x717E : "RV515",
           0x717F : "RV515",
           0x7180 : "RV515",
           0x7181 : "RV515",
           0x7183 : "RV515",
           0x7186 : "M54",
           0x7187 : "RV515",
           0x7188 : "M64",
           0x718A : "M54",
           0x718B : "M52",
           0x718C : "M52",
           0x718D : "M54",
           0x718F : "RV515PCI",
           0x7193 : "RV515",
           0x7196 : "M52",
           0x719B : "RV515",
           0x719F : "RV515",
           0x71A0 : "RV515",
           0x71A1 : "RV515",
           0x71A3 : "RV515",
           0x71A7 : "RV515",
           0x71AF : "RV515PCI",
           0x71B3 : "RV515",
           0x71BB : "RV515",
           0x71C0 : "RV530",
           0x71C1 : "RV535",
           0x71c2 : "RV530",
           0x71C3 : "RV535",
           0x71C4 : "M56GL",
           0x71c5 : "M56",
           0x71C6 : "RV530",
           0x71C7 : "RV535",
           0x71CD : "RV530",
           0x71ce : "RV530",
           0x71D2 : "RV530GL",
           0x71D4 : "M56GL",
           0x71D5 : "M56",
           0x71D6 : "M56",
           0x71DA : "RV530GL",
           0x71DE : "M56",
           0x71E0 : "RV530",
           0x71E1 : "RV535",
           0x71e2 : "RV530",
           0x71E3 : "RV535",
           0x71E6 : "RV530",
           0x71E7 : "RV535",
           0x71ED : "RV530",
           0x71EE : "RV530",
           0x71F2 : "RV530GL",
           0x71FA : "RV530GL",
           0x7205 : "1106",
           0x7210 : "M71",
           0x7211 : "M71",
           0x7240 : "R580",
           0x7243 : "R580",
           0x7244 : "R580",
           0x7245 : "R580",
           0x7246 : "R580",
           0x7247 : "R580",
           0x7248 : "R580",
           0x7249 : "R580",
           0x724A : "R580",
           0x724B : "R580",
           0x724C : "R580",
           0x724D : "R580",
           0x724E : "R580",
           0x724F : "R580",
           0x7260 : "R580",
           0x7263 : "R580",
           0x7264 : "R580",
           0x7265 : "R580",
           0x7266 : "R580",
           0x7267 : "R580",
           0x7268 : "R580",
           0x7269 : "R580",
           0x726A : "R580",
           0x726B : "R580",
           0x726C : "R580",
           0x726D : "R580",
           0x726E : "R580",
           0x726F : "R580",
           0x7280 : "R580",
           0x7284 : "M58",
           0x7286 : "R580",
           0x7288 : "R580",
           0x7291 : "R560",
           0x7293 : "R580",
           0x72A0 : "R580",
           0x72A8 : "R580",
           0x72B1 : "R580",
           0x72B3 : "R580",
           0x7833 : "RS350",
           0x79 : "unknown",
           0x791 : "RS690M",
           0x791a : "791A",
           0x791E : "RS690",
           0x791F : "RS690M",
           0x7912 : "SUBSYS_826D1043",
           0x7937 : "Samsung R25P",
           0x793F : "RS600",
           0x7941 : "RS690M",
           0x7942 : "RS600M",
           0x796E : "RS690",
           0x8086 : "1050",
           0x9000 : "RV350",
           0x9094 : "RV730",
           0x9400 : "R600",
           0x9401 : "R600",
           0x9402 : "R600",
           0x9403 : "R600",
           0x9405 : "R600",
           0x940A : "R600GL",
           0x940B : "R600GL",
           0x940F : "R600GL",
           0x9440 : "RV770",
           0x9441 : "R700",
           0x9442 : "RV770",
           0x9443 : "R700",
           0x9444 : "RV770",
           0x9446 : "RV770",
           0x9447 : "R700",
           0x944A : "M98",
           0x944B : "M98",
           0x944C : "RV770",
           0x944E : "RV770",
           0x9450 : "RV770",
           0x9452 : "RV770",
           0x9456 : "RV770",
           0x945A : "M98",
           0x9460 : "RV790",
           0x9462 : "RV790",
           0x9480 : "M96",
           0x9487 : "RV730",
           0x9488 : "M96",
           0x948F : "RV730",
           0x9490 : "RV730",
           0x9491 : "M96",
           0x9495 : "RV730",
           0x9498 : "RV730",
           0x949C : "RV730",
           0x949E : "RV730",
           0x949F : "RV730",
           0x94A0 : "M97",
           0x94A1 : "M97",
           0x94A3 : "M97",
           0x94B1 : "RV740",
           0x94B3 : "RV740",
           0x94B4 : "RV740",
           0x94B5 : "AA38",
           0x94C1 : "RV610-DT (Pro)",
           0x94C3 : "RV610-DT (LE)",
           0x94C4 : "RV610LE",
           0x94C5 : "RV610",
           0x94C7 : "RV610",
           0x94C8 : "M72",
           0x94C9 : "M72",
           0x94CB : "M72",
           0x94CC : "RV610",
           0x9501 : "RV670 XT",
           0x9504 : "M76",
           0x9505 : "RV630",
           0x9506 : "M76",
           0x9507 : "RV670",
           0x9508 : "M76",
           0x9509 : "M76",
           0x950F : "R680",
           0x9511 : "RV630GL",
           0x9513 : "R680",
           0x9515 : "RV670 AGP",
           0x9519 : "RV670",
           0x9540 : "RV710",
           0x9541 : "RV710",
           0x954E : "RV710",
           0x954F : "RV710",
           0x9552 : "M92",
           0x9553 : "M92",
           0x9555 : "M93",
           0x9557 : "M93",
           0x9581 : "M76M",
           0x9583 : "M76",
           0x9586 : "RV630",
           0x9587 : "RV630 PRO",
           0x9588 : "RV630 XT",
           0x9589 : "&#1055;&#1056;&#1054; RV630",
           0x958B : "M76",
           0x958C : "RV630GL",
           0x958D : "RV630GL",
           0x958E : "RV630",
           0x958F : "M76",
           0x9590 : "RV630",
           0x9591 : "M86-M",
           0x9593 : "M86",
           0x9595 : "M86",
           0x9596 : "RV630",
           0x9597 : "RV630",
           0x9598 : "RV630",
           0x9599 : "RV630",
           0x959B : "M86",
           0x95C0 : "RV610",
           0x95C2 : "M72",
           0x95c4 : "M82-S",
           0x95C5 : "RV620 LE",
           0x95C6 : "RV620",
           0x95C7 : "RV610",
           0x95C9 : "RV620",
           0x95CC : "RV620",
           0x95CD : "RV610",
           0x95CE : "RV610",
           0x95CF : "RV610",
           0x9610 : "RS780",
           0x9611 : "RS780",
           0x9612 : "RS780M",
           0x9613 : "RS780M",
           0x9614 : "RS780",
           0x9615 : "RS780",
           0x9616 : "RS780",
           0x9644 : "A4-3400",
           0x9647 : "AMD A6-3420M APU With AMD Radeon HD 6520G",
           0x9648 : " 9648",
           0x9649 : "HD 6480G",
           0x9710 : "RS880",
           0x9711 : "RS880",
           0x9712 : "4250",
           0x9713 : "RS880MC",
           0x9715 : "RS880",
           0x9802 : "AMD E-350",
           0x9803 : "2411E6FE",
           0x9804 : "AMD Radeon HD 6310 Graphics  AMD Radeon HD 6310 Gr",
           0x9806 : "AMD Radeon HD 6320",
           0x9807 : "unknow",
           0x9808 : "E2-1800",
           0x9809 : "7310M",
           0x9876 : "ATI GTC (GT-C2U2)",
           0x9999 : "(0x9498",
           0xAA01 : "Ati Function driver for high definition audio1",
           0xAA08 : "All with HDMI support",
           0xAA10 : "677",
           0xAA20 : "RV630",
           0xAA28 : "3400",
           0xaa68 : " 0x040300",
           0xAC12 : "Theater HD T507",
           0xCAB0 : "A3/U1",
           0xCAB1 : "A3/U1",
           0xcab2 : "RS200",
           0xCBB2 : "RS200",
           0x0876 : "",
           7800 : "",
         },
0x1003 : { 0x0201 : "GUI Accelerator",
         },
0x1004 : { 0x0005 : "DEV_0200",
           0x0006 : "ISA Bridge",
           0x0007 : "Wildcat System Controller",
           0x0008 : "Wildcat ISA Bridge",
           0x0009 : "",
           0x000C : "",
           0x000D : "",
           0x0100 : "CPU to PCI Bridge for notebook",
           0x0101 : "Peripheral Controller",
           0x0102 : "PCI to PCI Bridge",
           0x0103 : "PCI to ISA Bridge",
           0x0104 : "Host Bridge",
           0x0105 : "IrDA Controller",
           0x0200 : "RISC GUI Accelerator",
           0x0280 : "RISC GUI Accelerator",
           0x0304 : "ThunderBird PCI Audio Accelerator",
           0x0305 : "ThunderBird joystick port",
           0x0306 : "ThunderBird 16650 UART",
           0x0307 : "Philips Seismic Edge 705",
           0x0308 : "Philips PSC705 GamePort Enumerator",
           0x0702 : "Golden Gate II",
         },
0x1006 : { 0x3044 : "OHCI Compliant IEEE 1394 Host Controller",
         },
0x1008 : { 0x9876 : "23",
         },
0x100A : { 0x8235 : "U87088R06",
         },
0x100B : { 0x0001 : "10/100 Ethernet MAC",
           0x0002 : "PCI-IDE DMA Master Mode Interface Ctrlr",
           0x000E : "Legacy I/O Controller",
           0x000F : "IEEE 1394 OHCI Controller",
           0x0011 : "PCI System I/O",
           0x0012 : "USB Controller",
           0x001B : "Advanced PCI Audio Accelerator",
           0x0020 : "MacPhyter 10/100 Mb/s Ethernet MAC & PHY",
           0x0020 : "10/100 MacPhyter3v PCI Adapter",
           0x0021 : "PCI to ISA Bridge",
           0x0022 : "10/100/1000 Mb/s PCI Ethernet NIC",
           0x0028 : "PCI Host Bridge",
           0x002A : "GeodeLink PCI South Bridge",
           0x002D : "Geode IDE Controller",
           0x002E : "GEODE - GX3 Audio CS5535",
           0x002F : "USB Controller",
           0x0030 : "Geode VGA Compatible Device",
           0x0500 : "LPC Bridge and GPIO",
           0x0501 : "SMI Status and ACPI",
           0x0502 : "IDE Controller",
           0x0503 : "XpressAUDIO",
           0x0504 : "Video Processor",
           0x0505 : "X-Bus Expansion Interface",
           0x0510 : "LPC Bridge and GPIO",
           0x0511 : "SMI Status and ACPI",
           0x0515 : "X-Bus Expansion Interface",
           0x23 : "",
           0xD001 : "PCI-IDE Interface",
         },
0x100C : { 0x3202 : "GUI Accelerator",
           0x3205 : "GUI Accelerator",
           0x3206 : "GUI Accelerator",
           0x3207 : "GUI Accelerator",
           0x3208 : "Graphics/Multimedia Engine",
           0x4702 : "",
         },
0x100E : { 0x0564 : "Host Bridge",
           0x55CC : "South Bridge",
           0x9000 : "WeitekPower GUI Accelerator",
           0x9001 : "GUI Accelerator",
           0x9100 : "GUI Accelerator",
         },
0x1011 : { 0x0001 : "PCI-PCI Bridge",
           0x0002 : "Tulip Ethernet Adapter",
           0x0004 : "PCI Graphics Accelerator",
           0x0007 : "NV-RAM",
           0x0008 : "SCSI to SCSI Adapter",
           0x0009 : "Fast Ethernet Ctrlr",
           0x000A : "Video Codec",
           0x000C : "6IfPpL  <a href=",
           0x000D : "TGA2 PDXGB",
           0x000F : "FDDI",
           0x0014 : "Tulip Plus Ethernet Adapter",
           0x0016 : "ATM",
           0x0019 : "PCI/CardBus 10/100 Mbit Ethernet Ctlr",
           0x0021 : "PCI-PCI Bridge",
           0x0022 : "PCI-PCI Bridge",
           0x0023 : "PCI to PCI Bridge",
           0x0024 : "PCI-PCI Bridge",
           0x0025 : "PCI-PCI Bridge",
           0x0026 : "PCI-PCI Bridge",
           0x0034 : "CardBus",
           0x0045 : "PCI to PCI Bridge",
           0x0046 : "PCI-to-PCI Bridge",
           0x1011 : "PCI-PCI Bridge",
           0x1065 : "Mylex DAC1164P Disk Array Controller",
           0x2000 : "Fault Mgr (3.3v/5v Universal PCI)",
         },
0x1013 : { 0x0038 : "pci",
           0x0040 : "Flat Panel GUI Accelerator",
           0x004C : "64-bit Accelerated LCD/CRT Controller",
           0x00A0 : "GUI Accelerator",
           0x00A2 : "Alpine GUI Accelerator",
           0x00A4 : "Alpine GUI Accelerator",
           0x00A8 : "Alpine GUI Accelerator",
           0x00AC : "Video card (i guess?)",
           0x00B8 : "64-bit VisualMedia Accelerator",
           0x00BC : "64-bit SGRAM GUI accelerator",
           0x00D0 : "Laguna VisualMedia graphics accelerator",
           0x00D4 : "Laguna 3D VisualMedia Graphics Accel",
           0x00D5 : "Laguna BD",
           0x00D6 : "Laguna 3D VisualMedia Graphics Accel",
           0x00E8 : "",
           0x1013 : "accelerator do audio do pci de sound fusion",
           0x1100 : "PCI-to-PC Card host adapter",
           0x1110 : "PCMCIA/CardBus Controller",
           0x1112 : "PCMCIA/CardBus Controller",
           0x1113 : "PCI-to-CardBus Host Adapter",
           0x1200 : "Nordic GUI Accelerator",
           0x1202 : "Viking GUI Accelerator",
           0x1204 : "Nordic-lite VGA Cntrlr",
           0x4000 : "Ambient CLM Data Fax Voice",
           0x4400 : "Communications Controller",
           0x6001 : "CrystalClear SoundFusion PCI Audio Accelerator",
           0x6003 : "Crystal Sound Fusion a",
           0x6004 : "CrystalClear SoundFusion PCI Audio Accel",
           0x6005 : "Crystal Soundfusion(tm) CS 4206 WDM Audio",
           0x9876 : "SoundFusion PCI Audio Accelerator",
         },
0x1014 : { 0x0002 : "MCA Bridge",
           0x0005 : "CPU Bridge",
           0x0007 : "CPU Bridge",
           0x000A : "ISA Bridge w/PnP",
           0x0017 : "CPU to PCI Bridge",
           0x0018 : "TR Auto LANStreamer",
           0x001B : "Graphics Adapter",
           0x001D : "scsi-2 fast pci adapter",
           0x0020 : "MCA Bridge",
           0x0022 : "PCI to PCI Bridge ",
           0x002D : "",
           0x002E : "Coppertime RAID SCSI Adapter",
           0x0036 : "32-bit LocalBus Bridge",
           0x0037 : "PowerPC to PCI Bridge and Memory Ctrlr",
           0x003A : "CPU to PCI Bridge",
           0x003E : "IBM Token Ring PCI",
           0x0045 : "SSA Adapter",
           0x0046 : "Interrupt Controller",
           0x0047 : "PCI to PCI Bridge",
           0x0048 : "PCI to PCI Bridge",
           0x0049 : "Warhead SCSI Controller",
           0x004D : "MPEG-2 Decoder",
           0x004E : "ATM Controller",
           0x004F : "ATM Controller",
           0x0050 : "ATM Controller",
           0x0053 : "25 MBit ATM controller",
           0x0057 : "MPEG PCI Bridge",
           0x005C : "10/100 PCI Ethernet Adapter",
           0x005D : "TCP/IP networking device",
           0x007C : "ATM Controller",
           0x007D : "MPEG-2 Decoder",
           0x0090 : "",
           0x0095 : "PCI Docking Bridge",
           0x0096 : "Chukar chipset SCSI Controller",
           0x00A1 : "ATM support device",
           0x00A5 : "ATM Controller",
           0x00A6 : "ATM 155Mbps MM Controller",
           0x00B7 : "256-bit Graphics Rasterizer",
           0x00BE : "ATM 622Mbps Controller",
           0x00CE : "Adapter 2 Token Ring Card",
           0x00F9 : "Memory Controller and PCI Bridge",
           0x00FC : "PCI-64 Bridge",
           0x0105 : "PCI-32 Bridge",
           0x010F : "Remote Supervisor+Serial Port+Mouse/Keyb",
           0x011B : "Raid controller",
           0x0142 : "Video Compositor Input",
           0x0144 : "Video Compositor Output",
           0x0153 : "",
           0x0156 : "PLB to PCI Bridge",
           0x0170 : "Rasterizer/IBM GT1000 Geometr",
           0x0188 : "PCI Bridge",
           0x01a2 : "Modem: Intel Corporation 82440MX AC'97 Modem Controller (prog-if 00 [Generic])",
           0x01A7 : "PCI-X Bridge R1.1",
           0x01BD : "Morpheus SCSI RAID Controller",
           0x01ef : "PLB to PCI-X Bridge",
           0x0246 : "",
           0x027F : "Embedded PowerPC CPU",
           0x0289 : "0890",
           0x028c : "SCSI Storage Controller",
           0x0295 : "IBM SurePOS Riser Card Function 0",
           0x0297 : "IBM SurePOS Riser Card Function 1 (UARTs)",
           0x02A1 : "Calgary PCI-X Host Bridge",
           0x0302 : "PCI-X Host Bridge",
           0x0308 : "IBM CalIOC2 (Calgary on PCI-E)",
           0xFFFF : "Interrupt Controller",
           0x37C0 : "IBM Netfinity Advanced System Management Processor",
           0x37D0 : "n/a",
         },
0x1017 : { 0x5343 : "SPEA 3D Accelerator",
         },
0x1018 : { 0x3330 : "5444469821",
         },
0x1019 : { 0x1B10 : "VIA chipset",
           0x9876 : "Intel(R) Celeron(R) CPU 2.80GHz",
         },
0x101A : { 0x0005 : "100VG/AnyLAN Adapter",
           0x0009 : "PCI-X dual port  ",
         },
0x101E : { 0x9010 : "Ultra Wide SCSI RAID Controller2",
           0x9030 : "EIDE Controller",
           0x9031 : "EIDE Controller",
           0x9032 : "IDE and SCSI Cntrlr",
           0x9033 : "SCSI Controller",
           0x9040 : "Multimedia card",
           0x9060 : "Ultra GT RAID Controller",
           0x9063 : "Remote Assistant",
           0x9095 : "SGPIO/SES/IPMI Initiator",
         },
0x1022 : { 0x1100 : "HyperTransport Technology Configuration",
           0x1101 : "Address Map",
           0x1102 : "AMD Hammer - DRAM Controller ",
           0x1103 : "AMD Hammer - Miscellaneous Control ",
           0x2000 : "PCnet LANCE PCI Ethernet Controller",
           0x2001 : "PCnet-Home Networking Ctrlr (1/10 Mbps)",
           0x2003 : "Wireless LAN chipset SMC 2602W V3 http://www.smc.com/index.cfm?event=downloads.doSearchCriteria&loca",
           0x2020 : "SCSI Controller",
           0x2040 : "Ethernet Controller",
           0x2081 : "GeodeLX graphics adapter",
           0x2082 : "Geode GX3 AES Crypto Driver",
           0x208F : "GeodeLink PCI South Bridge",
           0x2093 : "CS5536 Audio Controller",
           0x2094 : "CS5536 OHCI USB Host Controller",
           0x2095 : "CS5536 EHCI USB Host Controller",
           0x2096 : "CS5536 USB Device Controller",
           0x2097 : "CS5536 USB OTG Controller",
           0x209A : "CS5536 IDE Controller",
           0x2433 : "Chill Control Connector",
           0x3000 : "ELAN Microcontroller PCI Host Bridge",
           0x5e4b : "Radeon X700 Pro",
           0x7004 : "CPU to PCI Bridge",
           0x7006 : "Processor-to-PCI Bridge / Memory Ctrlr",
           0x7007 : "AGP and PCI-to-PCI Bridge (1x/2x AGP)",
           0x700A : "AGP Host to PCI Bridge",
           0x700B : "AGP PCI to PCI Bridge",
           0x700C : "CPU to PCI Bridge (SMP chipset)",
           0x700D : "CPU to PCI Bridge (AGP 4x)",
           0x700E : "North Bridge",
           0x700F : "CPU to AGP Bridge  (AGP 4x)",
           0x7400 : "PCI to ISA Bridge",
           0x7401 : "Bus Master IDE Controller",
           0x7403 : "Power Management Controller",
           0x7404 : "PCI to USB Open Host Controller",
           0x7408 : "PCI-ISA Bridge",
           0x7409 : "EIDE Controller",
           0x740B : "Power Management",
           0x740C : "USB Open Host Controller",
           0x7410 : "PCI to ISA/LPC Bridge",
           0x7411 : "Enhanced IDE Controller",
           0x7412 : "USB Controller",
           0x7413 : "Power Management Controller",
           0x7414 : "USB OpenHCI Host Controller",
           0x7440 : "LPC Bridge",
           0x7441 : "EIDE Controller",
           0x7443 : "System Management",
           0x7445 : "AC97 Audio",
           0x7446 : "AC97 Modem",
           0x7448 : "PCI Bridge",
           0x7449 : "USB Controller",
           0x7450 : "PCI-X Bridge",
           0x7451 : "PCI-X IOAPIC",
           0x7454 : "System Controller",
           0x7455 : "AGP Bridge",
           0x7458 : "PCI-X Bridge",
           0x7459 : "PCI-X IOAPIC",
           0x7460 : "PCI Bridge",
           0x7461 : "USB 2.0 Controller",
           0x7462 : "Ethernet Controller",
           0x7463 : "USB Enhanced Host Controller",
           0x7464 : "USB OpenHCI Host Controller",
           0x7468 : "LPC Bridge",
           0x7469 : "UltraATA/133 Controller",
           0x746A : "SMBus 2.0 Controller",
           0x746B : "System Management",
           0x746D : " Audio Controller",
           0x746E : "AC'97 Modem",
           0x756B : "ACPI Controller",
           0x7801 : "AMD SATA Controller",
           0x7801 : "AMD SATA Controller",
           0x780b : "SM Bus controller",
           0x7812 : "AMD USB 3.0 Host Controller",
           0x840 : "Used to blow up the motherboard.  Highly explosive.  Use at ur own risk",
           0x9642 : "AMD Radeon HD6370D",
         },
0x1023 : { 0x0194 : "CardBus Controller",
           0x2000 : "advanced PCI DirectSound accelerator",
           0x2001 : "PCI Audio",
           0x2100 : "Video Accelerator",
           0x2200 : "Video adapter",
           0x8400 : "sausgauos",
           0x8420 : "Trident Cyber Blade i7 AGP (55)",
           0x8500 : "Via Tech VT8361/VT8601 Graphics Controller",
           0x8520 : "Windows xp",
           0x8620 : "trident",
           0x8820 : "TRIDENT DISPLAY CONTROLER /CyberALADDiN-T Driver",
           0x9320 : "32-bit GUI Accelerator",
           0x9350 : "32-bit GUI Accelerator",
           0x9360 : "Flat panel Cntrlr",
           0x9382 : "",
           0x9383 : "",
           0x9385 : "",
           0x9386 : "Video Accelerator",
           0x9388 : "Video Accelerator",
           0x9397 : "Video Accelerator 3D",
           0x939A : "Video Accelerator",
           0x9420 : "DGi GUI Accelerator",
           0x9430 : "GUI Accelerator",
           0x9440 : "DGi GUI Acclerator",
           0x9460 : "32-bit GUI Accelerator",
           0x9470 : "",
           0x9520 : "Video Accelerator",
           0x9525 : "Video Accelerator",
           0x9540 : "Video Acclerator",
           0x9660 : "GUI Accelerator",
           0x9680 : "GUI Accelerator",
           0x9682 : "Trident A CAB01",
           0x9683 : "GUI Accelerator",
           0x9685 : "2MB VGA",
           0x9750 : "trident dgi",
           0x9753 : "Video Accelerator",
           0x9754 : "Wave Video Accelerator",
           0x9759 : "Image GUI Accelerator",
           0x9783 : "",
           0x9785 : "",
           0x9850 : "4mb",
           0x9880 : "gggggg",
           0x9910 : "CyberBlade XP",
           0x9930 : "",
           0x9960 : "Trident Video Accelerator CyberBlade-1A31",
         },
0x1025 : { 0x0028 : "Agere Systems soft modem chip",
           0x1435 : "USBVID_0502&PID_3476&MI_016&207B7CA8&0&0001",
           0x1445 : "VL Bridge & EIDE",
           0x1449 : "ISA Bridge",
           0x1451 : "Pentium Chipset",
           0x1461 : "P54C Chipset",
           0x1489 : "",
           0x1511 : "",
           0x1512 : "",
           0x1513 : "",
           0x1521 : "CPU Bridge",
           0x1523 : "ISA Bridge",
           0x1531 : "North Bridge",
           0x1533 : "ISA South Bridge",
           0x1535 : "PCI South Bridge",
           0x1541 : "AGP PCI North Bridge Aladdin V/V+",
           0x1542 : "AGP+PCI North Bridge",
           0x1543 : "PCi South Bridge Aladdin IV+/V",
           0x1561 : "driver video",
           0x1621 : "PCI North Bridge Aladdin Pro II",
           0x1631 : "PCI North Bridge Aladdin Pro III",
           0x1641 : "PCI North Bridge Aladdin Pro IV",
           0x3141 : "GUI Accelerator",
           0x3143 : "GUI Accelerator",
           0x3145 : "GUI Accelerator",
           0x3147 : "GUI Accelerator",
           0x3149 : "GUI Accelerator",
           0x3151 : "GUI Accelerator",
           0x3307 : "MPEG-1 Decoder",
           0x3309 : "MPEG Decoder",
           0x5212 : "",
           0x5215 : "EIDE Controller",
           0x5217 : "I/O Controller",
           0x5219 : "I/O Controller",
           0x5225 : "EIDE Controller",
           0x5229 : "EIDE Controlle",
           0x5235 : "I/O Controller",
           0x5237 : "Intel(R) 5 Series/3400 Series Chipset Family 4 Port SATA AHCI Controller - 3B29",
           0x5239 : "",
           0x5240 : "EIDE Controller",
           0x5241 : "PCMCIA Bridge",
           0x5242 : "General Purpose Controller",
           0x5243 : "PCI to PCI Bridge",
           0x5244 : "Floppy Disk Controller",
           0x5247 : "PCI-PCI Bridge",
           0x5427 : "PCI to AGP Bridge",
           0x5451 : "PCI AC-Link Controller Audio Device",
           0x5453 : "M5453 AC-Link Controller Modem Device",
           0x7101 : "PCI PMU Power Management Controller",
         },
0x1028 : { 0x0001 : "Expandable RAID Controller (PERC) (SCSI)",
           0x0002 : "Expandable RAID Controller",
           0x0003 : "Expandable RAID Controller",
           0x0004 : "Expandable RAID Controller",
           0x0005 : "Expandable RAID Controller",
           0x0006 : "Expandable RAID Controller",
           0x0007 : "Remote Assistant Card",
           0x0008 : "RAC Virtual UART Port",
           0x000A : "Expandable RAID Controller",
           0x000C : "Embedded Systems Management Device 4",
           0x000D : "LSI53C895 PCI to Ultra2 SCSI I/O Processor with LVD Link",
           0x000E : "PERC 4/DI Raid Controller",
           0x0010 : "HJ866 - ESM4 Remote .Access card DRAC4",
           0x0011 : "Dell Remote Access Controller v4",
           0x0012 : "Dell RAC v4 Virtual UART",
           0x0013 : "Expandable RAID Controller",
           0x0014 : "Dell Remote Access Controller subsystem",
           0x0015 : "Integrated RAID controller",
           0x012c : "Intel Gigabit controller",
           0x016d : "Dell PRO/1000 MT Network Connection",
           0x0287 : "Adaptec 2200S SCSI RAID controller",
           0x1000 : "A Intel 537 epg v.92 modem repackaged by dell",
           0x1050 : "ethernet controller",
           0x1f0c : "Dell PERC 6/i Integrated RAID Controller",
           0x3002 : "Dell Wireless 1702 Bluetooth v3.0+HS",
           0x3582 : "video controller",
           0x9876 : "Expandable RAID Controller",
         },
0x102A : { 0x0000 : "4 port usb hub",
           0x0003 : "USBVID_0000&PID_00005&18BB29D0&1&2",
           0x0010 : "i486 Chipset",
           0x002A : "4 port usb hub",
           0x102A : "P5 Chipset",
           0x9876 : "P5 CHIPSET",
         },
0x102B : { 0x0010 : "Impression?",
           0x0040 : "Matrox P650 very new model (20080724)",
           0x051 : "matrox",
           0x0518 : "Atlas GUI Accelerator",
           0x0519 : "Strorm GUI Accelerator",
           0x051A : "Hurricane/Cyclone 64-bit graphics chip",
           0x051B : "Matrox",
           0x051E : "Chinook",
           0x051F : "Mistral",
           0x0520 : "AGP",
           0x0521 : "102B",
           0x0522 : "Matrox G200e (ServerEngines) - English",
           0x0525 : "Intel Pentium III",
           0x0527 : "",
           0x0528 : "Parhelia 128MB/256MB/PCI/HR256",
           0x0530 : "Matrox G200eV",
           0x0534 : "G200eR",
           0x0540 : "M9138 LP PCIe x16",
           0x0D10 : "Athena GUI accelerator",
           0x1000 : "Twister",
           0x1001 : "Twister AGP",
           0x1525 : "",
           0x1527 : "",
           0x2007 : "GUI+3D Accelerator",
           0x2527 : "AGP Chipset",
           0x2537 : "Parhelia Chipset AGP",
           0x2538 : "Matrox Millennium P650 LP PCIe 64",
           0x2539 : "Matrox Graphics Board dual DVI",
           0x4536 : "Video Capture Card",
           0x522 : "Matrox G200e (ServerEngines)",
           0x525 : "G45+",
           0x532 : "Matrox G200eW 8 MB DDR2 ",
           0x6573 : "10/100 Multiport Switch NIC",
           0x80A0 : "Multimedia Device",
           0x9876 : "Multimedia device",
         },
0x102C : { 0x00B8 : "Wingine DGX - DRAM Graphics Accelerator",
           0x00C0 : "AGP/PCI Flat Panel/CRT VGA Accelerator",
           0x00D0 : "Flat panel/crt VGA Cntrlr",
           0x00D8 : "Flat Panel/CRT VGA Controller",
           0x00DC : "GUI Accelerator",
           0x00E0 : "LCD/CRT controller",
           0x00E4 : "Flat Panel/LCD CRT GUI Accelerator",
           0x00E5 : "VGA GUI Accelerator",
           0x00F0 : "vga Controller",
           0x00F4 : "graphic driver",
           0x00F5 : "GUI Controller",
           0x01E0 : "PCI Flat Panel/CRT VGA Accelerator",
           0x0C30 : "AGP/PCI Flat Panel/CRT VGA Accelerator",
         },
0x102D : { 0x50DC : "Audio",
         },
0x102F : { 0x0009 : "CPU Bridge",
           0x000A : "CPU Bridge?",
           0x0020 : "ATM PCI Adapter",
           0x0030 : "8086",
           0x0031 : "Integrated 10/100 Mbit Ethernet Controller",
           0x0100 : "Realtek RTS5208 Card Reader",
           0x0105 : "GOKU-S Bus Master IDE Controller",
           0x0106 : "GOKU-S USB Host Controller",
           0x0107 : "GOKU-S USB Device Controller",
           0x0108 : "GOKU-S I2C Bus/SIO/GPIO Controller",
           0x0180 : "MIPS Processor",
           0x0181 : "MIPS RISC PCI Controller (PCIC)",
           0x0182 : "MIPS RISC PCI Controller (PCIC)",
           0x01BA : "SpursEngine",
           0x0805 : "1179",
           0x102F : "1179",
         },
0x1031 : { 0x5601 : "I/O & JPEG",
           0x5607 : "video in and out with motion jpeg compression and deco",
           0x5631 : "",
           0x6057 : "DC30D-601601-4.0",
         },
0x1033 : { 0x0001 : "PCI to 486 like bus Bridge",
           0x0002 : "PCI to VL98 Bridge",
           0x0003 : "ATM Controller",
           0x0004 : "PCI bus Bridge",
           0x0005 : "PCI to 486 like peripheral bus Bridge",
           0x0006 : "GUI Accelerator",
           0x0007 : "PCI to ux-bus Bridge",
           0x0008 : "GUI Accelerator (vga equivalent)",
           0x0009 : "graphic Cntrlr for 98",
           0x001A : "",
           0x001D : "NEASCOT-S20 ATM Integrated SAR Ctrlr",
           0x0021 : "Nile I",
           0x0029 : "3D Accelerator",
           0x002A : "3D Accelerator",
           0x002f : "1394 Host Controller",
           0x0034 : "0x0034",
           0x0035 : "Dual OHCI controllers plus Single EHCI controller",
           0x0036 : "NEASCOT-S40C ATM Light SAR Controller",
           0x003E : "NAPCCARD CardBus Controller",
           0x0046 : "3D Accelerator",
           0x005A : "Nile 4",
           0x0063 : "Firewarden IEEE1394 OHCI Host Controller",
           0x0067 : "PowerVR series II graphics processor",
           0x0074 : "56k Voice Modem",
           0x009B : "",
           0x00A6 : "",
           0x00BE : "64-bit CPU with Northbridge",
           0x00CD : "IEEE1394 1-Chip OHCI Host Controller",
           0x00CE : "IEEE1394 1-Chip OHCI Host Controller",
           0x00E0 : "USB 2.0 Host Controller",
           0x00E0 : "USB 2.0 Host Controller",
           0x00E7 : "IEEE1394 OHCI 1.1 3-port PHY-Link Ctrlr",
           0x00F2 : "IEEE1394+OHCI+1.1+3-port+PHY-Link+Ctrlr",
           0x0165 : "AVerMedia A313 MiniCard Hybrid DVB-T",
           0x0194 : "Renesas Electronics USB 3.0 Host Controller",
           0x0520 : "1394 CARD",
           0x1033 : "NEC PCI to USB Open Host Controller",
           0x9876 : "USB 2.0 Host Controller",
         },
0x1036 : { 0x0000 : "Fast SCSI",
         },
0x1039 : { 6529 : "",
           0 : "",
           0x7012 : "PCI Audio Accelerator",
           0x0001 : "Anthlon 64 cpu to PCI bridge",
           0x0002 : "Virtual PCI to PCI Bridge (AGP)",
           0x0003 : "SiS AGP Controller / SiS Accelerated Graphics Port ",
           0x0005 : "Pentium chipset",
           0x0006 : "PCI/ISA Cache Memory Controller (PCMC)",
           0x0008 : "PCI System I/O (PSIO)",
           0x0009 : "SIS PMU device",
           0x0016 : "SMBus ControllerP4kjc",
           0x0018 : "vga",
           0x0160 : "SiS160 811 Wireless LAN Adapter",
           0x0180 : "SiS 180/181 RAID Controller ",
           0x0181 : "Raid Controller(?Mode Raid1)",
           0x0182 : "Raid Controller(?Mode Raid0+1)",
           0x0183 : "?SATA",
           0x0186 : "0330",
           0x0190 : " SiS965",
           0x0191 : "SIS191",
           0x0200 : "Onboard Graphics Controller",
           0x0204 : "PCI1",
           0x0205 : "PCI Graphics & Video Accelerator",
           0x0300 : "GUI Accelerator+3D",
           0x0305 : "2D/3D/Video/DVD Accelerator",
           0x0315 : "2D/3D Accelerator",
           0x0325 : "Silicon Integrated Systems (SiS)",
           0x0330 : "Xabre 2D/3D Accelerator (AG400T8-D64)",
           0x0406 : "PCI/ISA Cache Memory Controller (PCMC)",
           0x0496 : "CPU to PCI & PCI to ISA Bridge",
           0x0530 : "Host-to-PCI bridge",
           0x0540 : "Host-to-PCI Bridge",
           0x0550 : "North Bridge",
           0x0596 : "Pentium PCI chipset with IDE",
           0x0597 : "EIDE Controller (step C)",
           0x0601 : "PCI EIDE Controller",
           0x0620 : "Host-to-PCI Bridge",
           0x0630 : "Host-to-PCI Bridge",
           0x0635 : "Host-to-PCI Bridge",
           0x0640 : "Host-to-PCI Bridge",
           0x0645 : "Host-to-PCI Bridge",
           0x0646 : "Host-to-PCI Bridge",
           0x0648 : "Host-to-PCI Bridge",
           0x0649 : "Host-to-PCI Bridge",
           0x0650 : "Host-to-PCI Bridge",
           0x0651 : "Host-to-PCI Bridge",
           0x0655 : "Host-to-PCI Bridge",
           0x0656 : "CPU to PCI Bridge",
           0x0658 : "CPU to PCI Bridge",
           0x0659 : "CPU to PCI Bridge",
           0x0660 : "Host-to-PCI Bridge",
           0x0661 : "SiS 661FX/GX Chipset - Host-PCI Bridge",
           0x0662 : "CPU to PCI Bridge",
           0x0663 : "CPU to PCI Bridge",
           0x0730 : "Host-to-PCI Bridge",
           0x0735 : "Host-to-PCI Bridge",
           0x0740 : "LPC Bridge",
           0x0741 : "CPU to PCI Bridge",
           0x0745 : "Host-to-PCI Bridge",
           0x0746 : "Host-to-PCI Bridge",
           0x0748 : "CPU to PCI Bridge",
           0x0755 : "Host-to-PCI Bridge",
           0x0756 : "CPU to PCI Bridge",
           0x0760 : "Athlon 64 CPU to PCI Bridge",
           0x0761 : "Athlon 64 CPU to PCI Bridge",
           0x0762 : "Athlon 64 CPU to PCI Bridge",
           0x0900 : "SiS 900 Fast Ethernet Adapter",
           0x0901 : "SiS900 10/100 Ethernet Adapter",
           0x0962 : "LPC Bridge",
           0x0963 : "PCI to ISA Bridge",
           0x0964 : "SiS 964 MuTIOL Media I/O Bridge ",
           0x0999 : "1039",
           0x1039 : "SiS5597 SVGAa",
           0x1040 : "",
           0x10ec : "bus controler",
           0x1182 : "Raid Controller(?Mode Raid5)",
           0x1183 : "SATA IDE Controller",
           0x1184 : "Raid/AHCI Controller",
           0x1185 : "AHCI Controller",
           0x1234 : "SiS5597 SVGAa",
           0x191 : "PCI /ven_1039",
           0x3602 : "IDE Controller",
           0x4321 : "Video Controller (VGA Compatible)",
           0x5107 : "Hot Docking Controller",
           0x5300 : "AGP",
           0x5315 : "GUI Accelerator",
           0x5401 : "486 PCI Chipset",
           0x5511 : "PCI/ISA System Memory Controller",
           0x5513 : "SiS 5513 IDE UDMA Controller / SiS 85C513 IDE Controller",
           0x5517 : "CPU to PCI Bridge",
           0x5518 : "UDMA IDE Controller",
           0x5571 : "Memory/PCI bridge",
           0x5581 : "p5 chipset",
           0x5582 : "PCI to ISA Bridge",
           0x5591 : "1969",
           0x5596 : " VGA Controller",
           0x5597 : "Host to PCI bridge",
           0x5600 : "Host-to-PCI Bridge",
           0x5630 : "Host-to-PCI Bridge",
           0x5811 : "",
           0x6204 : "video decoder/mpeg interface",
           0x6205 : "PCI VGA Controller",
           0x6225 : "PCI Graphics & Video Accelerator",
           0x6236 : "Graphics",
           0x6300 : "GUI Accelerator+3D",
           0x6306 : "Integrated 3D  SVGA Controller",
           0x6325 : "sis-651dx",
           0x6326 : "sis 6326 AGP",
           0x6330 : "GUI 2D/3D Accelerator",
           0x6331 : "USB Host Controller",
           0x6351 : "SiS IGP Graphics family SIS66x/SIS76x & SIS67x",
           0x6355 : "962lua",
           0x6787 : "Smart Link 56K Voice Modem (download from driverguide.com)",
           0x6972 : "",
           0x7001 : "SiS 7001 PCI to USB Open Host Controller ",
           0x7002 : "USB 2.0 Enhanced Host Controller",
           0x7005 : "Memory Stick Controller",
           0x7007 : "OHCI Compliant FireWire Controller",
           0x7012 : "SiS 7012 Audio Device / Realtek AC'97 Audio",
           0x7013 : "Smart Link 56K Voice Modem (download from driverguide.com)",
           0x7013 : "Smart Link 56K Voice Modem",
           0x7015 : "Software Audio dd",
           0x7016 : "10/100 Ethernet Adapter",
           0x7018 : "Onboard audio",
           0x7019 : "Hardware Audio",
           0x7300 : "GUI Accelerator+3D",
           0x7502 : "Realtek HDA Audio Driver.",
           0x8139 : "2012",
           0x9632 : "sis 650 integrated gfx controller (IGP)",
           0x964 : "LPC BRIDGE",
           0x9876 : "pci vga card for win95 & nt4 only",
           0x9989 : "Smart Link 56K Voice Modem (download from driverguide.com)",
           0x7012 : "PCI Audio Accelerator",
           5811 : "",
         },
0x103B : { 0x103b : "LAN Controller with 82562EM/EX PHY",
         },
0x103C : { 0x0024 : "Standard Vista USB Keyboard",
           0x0180 : "HID Keyboard Device",
           0x0A01 : "HP Scanjet 2400",
           0x1005 : "Visialize EG",
           0x1008 : "001",
           0x100A : "Hewlett-Packard VisualizeFX Series Video",
           0x1028 : "HP ProtectSmart Hard Drive Protection - HP 3D DriveGuard",
           0x1029 : "Tachyon XL2 Fibre Channel Adapter",
           0x102A : "Tachyon TS Fibre Channel Host Adapter",
           0x1030 : "DeskDirect 10/100VG LAN Adapter",
           0x1031 : "DeskDirect 10/100 NIC",
           0x1040 : "DeskDirect 10BaseT NIC",
           0x1041 : "DeskDirect 10/100VG NIC",
           0x1042 : "DeskDirect 10BaseT/2 NIC",
           0x1048 : "",
           0x1049 : "",
           0x104A : "intel",
           0x104B : "",
           0x104D : "EL-10 Ethernet Adapter",
           0x1064 : "PCnet Ethernet Controller",
           0x10C1 : "NetServer Smart IRQ Router",
           0x10ED : "HP Communications Port",
           0x1200 : "10/100 NIC",
           0x1219 : "NetServer PCI Hot-Plug Controller",
           0x121A : "NetServer SMIC Controller",
           0x121B : "NetServer Legacy COM Port Decoder",
           0x121C : "NetServer PCI COM Port Decoder",
           0x1229 : "System Bus Adapter",
           0x122A : "I/O Controller",
           0x122B : "Local Bus Adapter",
           0x12FA : "Broadcom Wireless miniPCI in a HP laptop",
           0x1302 : "HP Management Shared Memory Device",
           0x137a : "Atheros AR5007",
           0x1411 : "HP PSC 750",
           0x171d : "HP Integrated Module with Bluetooth Wireless",
           0x1F1D : "3G Broadband device",
           0x201D : "3G Broadband device",
           0x231D : "HP Integrated Module with Bluetooth Wireless Technology",
           0x241D : "HP compaq nx6125",
           0x2910 : "PCI Bus Exerciser",
           0x292 : "PCI Host Interface Adapter",
           0x2920 : "Fast Host Interface",
           0x2924 : "PCI Host Interface Adapter",
           0x2925 : "32 bit PCI Bus Exerciser and Analyzer",
           0x2926 : "64 bit PCI Bus Exerciser and Analyzer",
           0x2927 : "64 Bit",
           0x294 : "pci hostinterface",
           0x2940 : "64 bit",
           0x311d : "ATHEROS AR3011 bluetooth 3.0+HS adapter",
           0x3206 : "Adaptec Embedded Serial ATA HostRAID",
           0x3207 : "not sure",
           0x3220 : "P600 SmartArray Raid Controller",
           0x3230 : "Smart Array P400 Controller",
           0x323A : "Smart Array P410i Controller",
           0x3302 : "Integrated Lights Out 2.0",
           0x3A1D : "HP hs2340 HSPA+ MobileBroadband",
           0x5461 : "HP integrated Module with Bluetooth 2.0 Wireless support",
           0x9876 : "ATHEROS AR3011 bluetooth 3.0+HS adapter",
         },
0x1043 : { 0x0675 : "Crestline",
           0x1969 : "Attansic L1 Gigabit Ethernet 10/100/1000Base-T Adapter",
           0x5653 : "ATI Radeon 3000 Graphics (Microsoft Corporation - WDDM v1.1)",
           0x8103 : "NV31 [GeForce FX 5600 Ultra]",
           0x82c6 : "Gigabit Ethernet(NDIS 6.0)",
         },
0x1044 : { 0x1012 : "RAID Engine",
           0x800A : "802.11 bg WLAN",
           0xA400 : "SmartCache III/RAID SCSI Controller",
           0xA500 : "PCI Bridge",
           0xA501 : "I2O SmartRAID V Controller",
           0xA511 : "SmartRAID Controller",
         },
0x1045 : { 0x0005 : "",
           0xA0F8 : "PCI USB Controller",
           0xC101 : "GUI Accelerator",
           0xC178 : "pci usb card 2- port",
           0xC556 : "Viper",
           0xC557 : "CPU Bridge (Viper)",
           0xC558 : "ISA Bridge w/PnP",
           0xC567 : "Vendetta chipset: host bridge",
           0xC568 : "Vendetta chipset: ISA bridge",
           0xC569 : "Pentium to PCI Bridge",
           0xC621 : "PCI IDE Controller (PIC)",
           0xC700 : "82C700 FireStar PCI to ISA Bridge",
           0xC701 : "FireStar mobile chipset: host bridge",
           0xC814 : "FireBridge II Docking Station Controller",
           0xC822 : "CPU to PCI & PCI to ISA PnP bridge",
           0xC824 : "FireFox 32-Bit PC Card Controller",
           0xC825 : "PCI-to-ISA Bridge",
           0xC832 : "CPU-to-PCI and PCI-to-ISA Bridge",
           0xC861 : "FireLink PCI-to- 5 x USB Bridge( usb1.1 )",
           0xC881 : "FireLink 1394 OHCI Link Controller",
           0xC895 : "",
           0xC931 : "ISA Sound & Game Port controller.",
           0xC935 : "MachOne integrated PCI audio processor",
           0xD568 : "PCI bus master IDE controller",
           0xD768 : "Ultra DMA IDE controller",
         },
0x1046 : { 0x5600 : "00/4&1a671",
         },
0x1048 : { 0x0253 : "ELSA GLADIAC 528",
           0x0C60 : "NVidia Geforce 2 MX",
           0x0C71 : "NVidia GeForce3 Ti 200",
           0x1000 : "ISDN Controller",
           0x3000 : "",
           0x8901 : "ELSA GLoria XL",
         },
0x104A : { 0x0008 : "diamond",
           0x0009 : "",
           0x0010 : "PowerVR KYRO series 3 graphics processor",
           0x0123 : "SPEAr1300",
           0x0209 : "North/South Bridges",
           0x020A : "North Bridge",
           0x0210 : "ISA Bridge",
           0x021A : "ISA Bridge",
           0x021B : "ISA Bridge",
           0x0228 : "IDE Controller",
           0x0230 : "USB Controller",
           0x0500 : "ADSL",
           0x0981 : "10/100 Ethernet Adapter",
           0x1746 : "mp280",
           0x2774 : "PCI 10/100 Ethernet Controller",
           0x3520 : "MPEG-II Video Decoder",
           0x7108 : "Advanced HD AVC decoder with 3D graphics acceleration",
           0xCC00 : "ConneXt I/O Hub multifunction device",
           0xCC01 : "ConneXt I/O Hub multifunction device",
           0xCC02 : "ConneXt I/O Hub multifunction device",
           0xCC03 : "ConneXt I/O Hub multifunction device",
           0xCC04 : "ConneXt I/O Hub multifunction device",
           0xCC05 : "ConneXt I/O Hub multifunction device",
           0xCC06 : "ConneXt I/O Hub multifunction device",
           0xCC07 : "ConneXt I/O Hub multifunction device",
           0xCC08 : "ConneXt I/O Hub multifunction device",
           0xCC09 : "ConneXt I/O Hub multifunction device",
           0xCC0A : "ConneXt I/O Hub multifunction device",
           0xCC0B : "ConneXt I/O Hub multifunction device",
           0xCC0C : "ConneXt I/O Hub multifunction device",
           0xCC0D : "ConneXt I/O Hub multifunction device",
           0xCC0E : "ConneXt I/O Hub multifunction device",
           0xCC0F : "ConneXt I/O Hub multifunction device",
           0xCC10 : "ConneXt I/O Hub multifunction device",
           0xCC11 : "ConneXt I/O Hub multifunction device",
           0xCC12 : "ConneXt I/O Hub multifunction device",
           0xCC13 : "ConneXt I/O Hub multifunction device",
           0xCC14 : "ConneXt I/O Hub multifunction device",
           0xCC15 : "ConneXt I/O Hub multifunction device",
           0xCC16 : "ConneXt I/O Hub multifunction device",
           0xCC17 : "ConneXt I/O Hub multifunction device",
           0xCD00 : "SPEAr1300",
           0xCD80 : "Root Complex of SPEAr1300",
         },
0x104B : { 0x1040 : "BT958 SCSI Host Adaptor",
           0x8130 : "Flashpoint LT",
         },
0x104C : { 0x803B : "Texas Instruments Card Reader",
           0x014e : "4515",
           0x0500 : "ThunderLAN 100 Mbit LAN Controller",
           0x0508 : "PCI interface for TI380 compressors",
           0x1000 : "",
           0x104C : "PCI Simple Communications Controller",
           0x3B04 : "otros dispositivos",
           0x3D04 : "Permedia",
           0x3D07 : "AGP Permedia 2",
           0x8000 : "LYNX IEEE1394 FireWire Host Controller",
           0x8009 : "OHCI-Lynx PCI IEEE 1394 Host Controller",
           0x8010 : "OHCI-Lynx IEEE 1394 Host Controller",
           0x8011 : "OHCI-Lynx IEEE 1394 Controller",
           0x8017 : "OHCI-Lynx IEEE 1394 Controller",
           0x8019 : "OHCI-Lynx PCI IEEE 1394 Host Controller",
           0x8020 : "OHCI-Lynx PCI IEEE 1394 Host Controller",
           0x8021 : "1394a-2000 OHCI PHY/Link Layer CONTROLLER",
           0x8023 : "IEEE1394a-2000 OHCI PHY/Link-Layer Ctrlr",
           0x8024 : "1394a-2000 OHCI PHY/Link Layer Ctrl",
           0x8025 : "1394b OHCI-Lynx IEEE 1394 Host Controller",
           0x8026 : "1394a-2000 OHCI PHY/Link Layer Ctrlr",
           0x8027 : "OHCI-Lynx IEEE 1394 Controller",
           0x8029 : "OHCI Compliant IEEE-1394 FireWire Controller ",
           0x802e : "OHCI Compliant IEEE 1394 Host Controller",
           0x8033 : "Integrated FlashMedia ",
           0x8034 : "SDA Standard Compliant SD Host Controller",
           0x8035 : "PCI GemCore based SmartCard controller",
           0x8036 : "Texas Instruments PCIxxx12 Cardbus Controller",
           0x8038 : "Texas Instruments PCI GemCore based SmartCard Controller",
           0x8039 : "104C",
           0x803a : "OHCI Compliant IEEE 1394 Host controller",
           0x803B : "Texas Instruments Card Reader",
           0x803c : "SDA Standard Compliant SD Host Controller",
           0x803D : "Texas Instruments PCI GemCore based SmartCard controller",
           0x8119 : "iRDA Compatible Controller",
           0x8201 : "TI UltraMedia Firmware Loader Device",
           0x8204 : " 4515",
           0x8231 : "PCI-Express to PCI/PCI-X bridge",
           0x8232 : "Controladora de vdeo multimedia",
           0x8241 : "Texas Instruments USB 3.0 XHCI Host Controller",
           0x8400 : "D-Link AirPlus DWL-520+",
           0x8671 : "bogus",
           0x9065 : "Fixed Point Digital Signal Processor",
           0x9066 : "U.S. Robotics 802.11g Wireless Turbo PC Card ",
           0xA001 : "64-bit PCI ATM SAR",
           0xA100 : "32-bit PCI ATM SAR",
           0xA102 : "HyperSAR Plus w/PCI host & UTOPIA i/f",
           0XA106 : "Fixed Point Digital Signal Processor",
           0xA186 : "TI C6416T DSP",
           0xa828 : "PCI-to-PCI Bridge",
           0xAC10 : "PC Card Controller",
           0xAC11 : "PC Card Controller",
           0xAC12 : "PC card CardBus Controller",
           0xAC13 : "Texas Instruments PCIxx12 Integrated FlashMedia Controller",
           0xAC15 : "CardBus Controller",
           0xAC16 : "PC Card CardBus Controller",
           0xAC17 : "CardBus Controller",
           0xAC18 : "PC card CardBus Controller",
           0xAC19 : "PC card CardBus Controller",
           0xAC1A : "PC card CardBus Controller",
           0xAC1B : "PC card CardBus Controller",
           0xAC1C : "PC Card CardBus Controller",
           0xac1e : "PCI To PCMCIA  bridge",
           0xAC1F : "PC card CardBus Controller",
           0xAC20 : "PCI to PCI Bridge",
           0xAC21 : "PCI to PCI Bridge",
           0xAC22 : "PCI Docking Bridge",
           0xAC23 : "PCI-to-PCI Bridge",
           0xAC28 : "PCI-to-PCI Bridge",
           0xAC30 : "PC card CardBus Controller",
           0xAC40 : "PC card CardBus Controller",
           0xAC41 : "PC card CardBus Controller",
           0xAC42 : "PC card CardBus Controller",
           0xAC43 : "PC card CardBus Controller",
           0xAC44 : "PC Card Controller SDFSDAFSADFSDAFSDAF",
           0xAC46 : "PCCard CardBus Controller",
           0xac47 : "Cardbus",
           0xAC50 : "PC card cardBus Controller",
           0xAC51 : "Texas Instruments 1420",
           0xAC52 : "PC card CardBus Controller",
           0xAC53 : "PC card CardBus Controller - 5-in-1 Media Card Reader",
           0xAC54 : "PCCard CardBus Controller w/UltraMedia",
           0xAC55 : "PCCard CardBus Controller",
           0xAC56 : "PCCard CardBus Controller",
           0xAC57 : "PCCard CardBus Controller",
           0xAC58 : "PCCard CardBus Controller",
           0xAC59 : "PCCard CardBus Controller w/UltraMedia",
           0xAC5A : "PCCard CardBus Controller w/UltraMedia",
           0xac60 : "PCI2040 PCI to DSP Bridge",
           0xac8e : "Generic CardBus Controller ",
           0xAC8F : "FlashMedia",
           0xB000 : "Device ID: 0xB001 ",
           0xB001 : "DSP with a C64x+ core and M/S PCI interface",
           0xFE00 : "FireWire Host Controller",
           0xFE03 : "FireWire Host Controller",
         },
0x104D : { 0x011B : "USB Ralink Wireless LAN",
           0x5001 : "Sony Firmware Extension Parser listed as ACPI&#92;SNY5001 in device manager.",
           0x8009 : "PCI bus 13",
           0x8039 : "OHCI i.LINK (IEEE 1394) PCI Host Ctrlr",
           0x8056 : "Rockwell HCF 56K Modem",
           0x8087 : "SONY MPEG ENCODER",
           0x808A : "Memory Stick Controller",
         },
0x104E : { 0x0017 : "",
           0x0107 : "Spitfire VGA Accelerator",
           0x0109 : "Video Adapter",
           0x0217 : "",
           0x0317 : "",
           0x0611 : "T9732",
           0x317 : "Spitfire VGA Accelerator",
         },
0x104F : { 0x104F : "Multi I/O",
         },
0x1050 : { 0x6692 : "PCI BusISDN S/T-Controller",
           0x0000 : "Ethernet Controller (NE2000 compatible)",
           0x0001 : "PCI/IDE controller",
           0x0033 : "Winbond W89C33 mPCI 802.11 Wireless LAN Adapter",
           0x0105 : "Ethernet Adapter",
           0x0628 : "PCI to ISA Bridge Set",
           0x0840 : "100/10Mbps Ethernet Controller",
           0x0940 : "winbond pci ethernet",
           0x1050 : "Video capture card mpeg-1",
           0x5A5A : "ELANC-PCI Twisted-pair Ether-LAN Ctrlr",
           0x6692 : "PCI BusISDN S/T-Controller",
           0x8481 : "SD Host Controller",
           0x9921 : "MPEG1 capture card",
           0x9922 : "MPEG-1/2 Decoder",
           0x9960 : "Video Codec",
           0x9961 : "H.263/H.261 Video Codec",
           0x9970 : "VGA controller",
           0x9971 : "W9971CF",
           6692 : "",
         },
0x1051 : { 0x0100 : "",
         },
0x1054 : { 0003 : "0003",
           0x0001 : "PCI Bridge",
           0x0002 : "PCI bus Cntrlr",
           0x0003 : "hts547575a9e384",
           0x3505 : "SuperH (SH) 32-Bit RISC MCU/MPU Series",
         },
0x1055 : { 0x0810 : "EFAR 486 host Bridge",
           0x0922 : "Pentium/p54c host Bridge",
           0x0926 : "ISA Bridge",
           0x9130 : "Ultra ATA/66 IDE Controller",
           0x9460 : "Victory66 PCI to ISA Bridge",
           0x9461 : "Victory66 UDMA EIDE Controller",
           0x9462 : "Victory66 USB Host Controller",
           0x9463 : "Victory66 Power Management Controller",
           0xe420 : "PCI 10/100 Ethernet controller",
         },
0x1056 : { 0x2001 : "Philips P89C51RD271BA. 1D041700A0. AeD0217G",
         },
0x1057 : { 0*5600 : "Motorola FM 56 PCI Speakerphone Modem",
           0x0001 : "PCI Bridge / Memory Controller (PCIB/MC)",
           0x0002 : "PCI Bridge/Memory Controller (PCIB/MC)",
           0x0003 : "Integrated Processor",
           0x0004 : "PCI Bridge/Memory Controller for PPC",
           0x0006 : "Integrated Processor",
           0x0100 : "HCF-PCI",
           0x0431 : "100VG Ethernet Controller",
           0x1801 : "24-bit Digital Signal Processor",
           0x1802 : "24-Bit Digital Signal Processor",
           0x18C0 : "PowerQUICC II PCI Bridge",
           0x3052 : "MotorolaSM56Modem_PCI device",
           0x3055 : "Motorola SM56 Data Fax Modem ",
           0x3057 : "Modem Device on High Definition Audio Bus",
           0x3410 : "Digital Signal Processor",
           0x3421 : "Modem",
           0x4801 : "PowerPC Chipset",
           0x4802 : "memory control chipset",
           0x4803 : "",
           0x4806 : "",
           0x4809 : "HotSwap Controller",
           0x5600 : "SM 56 PCI Speakerphone/Data",
           0x5602 : "PCI Modem",
           0x5608 : "Motorola SM56 Speakerphone Modem",
           0x5803 : "32-Bit Embedded PowerPC Processor",
           0x6400 : "Security Co-Processor",
           0x9876 : "3052",
         },
0x105A : { 0x0262 : "Ultra66/FastTrak66",
           0x0D30 : "MBUltra100/MBFastTrack100 Lite",
           0x0D38 : "FastTrak66 Lite EIDE Controller",
           0x105A : "EIDE Controller",
           0x1275 : "MBUltra133",
           0x1960 : "SuperTrak 66/100 RAID",
           0x1962 : "SuperTrak SX 6000",
           0x3318 : "SATA150 TX4",
           0x3319 : "FastTrak S150 TX4",
           0x3371 : "FastTrak S150 TX2+",
           0x3373 : "FastTrak 378/SATA 378 RAID Controller",
           0x3375 : "SATA150 TX2+",
           0x3376 : "FastTrak 376 Controller",
           0x3515 : "FastTrak TX43xx",
           0x3519 : "FastTrak TX42xx",
           0x3570 : "FastTrak TX2300 SATA300 Controller",
           0x3571 : "Fasttrack TX2200",
           0x3574 : "SATAII 150 579",
           0x3d17 : "SATA 300 TX4 Controller",
           0x3D18 : "SATAII 150TX2+/SATAII150 TX4",
           0x3D73 : "SATAII 300 TX2+",
           0x3F19 : "FastTrak TX2650/4650/4652",
           0x3F20 : "FastTrak TX2650(3F21)/4650(3F22)/PDC42819(3716)",
           0x4302 : "SuperTrak EX 43X0",
           0x4303 : "SuperTrak EX 4350",
           0x4D30 : "FastTrack100 on Intel MB SE7500CW2",
           0x4D33 : "FastTrak/Ultra33 ATA RAID controller",
           0x4D38 : "Ultra66/FastTrak66",
           0x4D68 : "Ultra100TX2/FastTrak100TX/LP",
           0x4D69 : "Ultra133TX2",
           0x5275 : "MBUltra133/MBFastTrak133",
           0x5300 : "EIDE Controller",
           0x6268 : "FastTrak100 TX2/TX4/LP",
           0x6269 : "FastTrak TX2000 EIDE controller",
           0x6300 : "FastTrak SX 8300",
           0x6301 : "FastTrak SX8300-1",
           0x6302 : "FastTrak SX 4300",
           0x6303 : "FastTrak SX 4",
           0x6304 : "FastTrak SX8300-2",
           0x6305 : "FastTrak SX8300-3",
           0x6306 : "FastTrak SX 4300-2",
           0x6307 : "FastTrak SX 4300-3",
           0x6621 : "FastTrak SX4000",
           0x6622 : "FastTrak S150SX4",
           0x6629 : "FastTrak TX4000",
           0x7250 : "Vitesse 7250 SAS RAID",
           0x7275 : "SBUltra133/SBFastTrak 133 Lite",
           0x8000 : "SATAII150 SX8",
           0x8002 : "SATAII150 SX8",
           0x8003 : "FastTrak SX4000",
           0x8004 : "SATAII150 SX8",
           0x8006 : "SATAII150 SX8",
           0x8350 : "SuperTrak EX8350/16350/8300/16300",
           0x8650 : "SuperTrak EX SAS RAID",
           0xC350 : "SuperTrak EX 123X0",
           0xE350 : "SuperTrak EX 243X0",
         },
0x105D : { 0x2309 : "GUI Accelerator",
           0x2339 : "Imagine 128 Series 2",
           0x493D : "Revolution 3D",
           0x5348 : "Revolution IV",
         },
0x1060 : { 0x0001 : "486 Chipset",
           0x0002 : "ISA Bridge",
           0x0101 : "EIDE Controller",
           0x0881 : "HB4 486 PCI Chipset",
           0x0886 : "ISA Bridge",
           0x0891 : "Pentium CPU to PCI bridge",
           0x1001 : "IDE Cntrlr (dual function)",
           0x673A : "EIDE Controller",
           0x673B : "EIDE Master/DMA",
           0x8710 : "VGA Cntrlr",
           0x8821 : "CPU/PCI Bridge",
           0x8822 : "PCI/ISA Bridge",
           0x8851 : "Pentium CPU/PCI Bridge",
           0x8852 : "Pentium CPU/ISA Bridge",
           0x886A : "ISA Bridge with EIDE",
           0x8881 : "HB4 486 PCI Chipset",
           0x8886 : "ISA Bridge (w/o IDE support)",
           0x888A : "",
           0x8891 : "586 Chipset",
           0x9017 : "Ethernet",
           0x9018 : "Ethernet",
           0x9026 : "Fast Ethernet",
           0xE881 : "486 Chipset",
           0xE886 : "ISA Bridge w/EIDE",
           0xE88A : "PCI / ISA Bridge",
           0xE891 : "um8891n",
         },
0x1061 : { 0x0001 : "GUI Accelerator",
           0x0002 : "MPEG Decoder",
         },
0x1065 : { 0x8139 : "Realtek 8139C Network Card",
         },
0x1066 : { 0x0000 : "VL Bridge",
           0x0001 : "Vesuvius V1-LS System Controller",
           0x0002 : "Vesuvius V3-LS ISA Bridge",
           0x0003 : "Nile PCI to PCI Bridge",
           0x0004 : "Nile-II PCI to PCI Bridge",
           0x0005 : "System Controller",
           0x8002 : "ISA Bridge",
         },
0x1067 : { 0x1002 : "VolumePro Volume Rendering Accelerator",
         },
0x106B : { 0x0001 : "PowerPC Host-PCI Bridge",
           0x0002 : "I/O Controller",
           0x0003 : "",
           0x0004 : "Video-in",
           0x0007 : "I/O Controller",
           0x0009 : "BCM5703X",
           0x000C : "",
           0x000E : "Mac I/O Controller",
           0x0010 : "Mac I/O Controller",
           0x0017 : "Mac I/O Controller",
           0x0018 : "FireWire Controller",
           0x001F : "Host-PCI bridge",
           0x0020 : "AGP interface",
           0x0026 : "USB Interface",
           0x0027 : "AGP interface",
           0x002D : "AGP Bridge",
           0x002E : "PCI Bridge",
           0x002F : "Internal PCI",
           0x0030 : "FireWire Controller",
           0x003B : "Integrated ATA Controller",
           0x004f : "Mac I/O controler",
           0x0050 : "IDE controler",
           0x0051 : "Sungem ethernet controler",
           0x0052 : "Firewire controler",
           0x0053 : "PCI Bridge",
           0x0054 : "PCI Bridge",
           0x0055 : "PCI Bridge",
           0x0058 : "AGP Bridge",
           0x008A : "Mac Pro RAID Card",
           0x008C : "AirPort Extreme",
         },
0x106C : { 0x8801 : "Dual Pentium ISA/PCI Motherboard",
           0x8802 : "PowerPC ISA/PCI Motherboard",
           0x8803 : "Dual Window Graphics Accelerator",
           0x8804 : "PCI LAN Controller",
           0x8805 : "100-BaseT LAN Controller",
         },
0x106E : { 0x4362 : "Yukon PCI-E Gigabit Ethernet Controller (copper)",
         },
0x1073 : { 0x0001 : "3D graphics Cntrlr",
           0x0002 : "RPA3 3D-Graphics Controller",
           0x0003 : "",
           0x0004 : "PCI Audio Controller",
           0x0005 : "DS1 Audio",
           0x0006 : "DS1 Audio",
           0x0008 : "DS1 Audio",
           0x000A : "DS-1L PCI Audio Controller",
           0x000C : "DS-1L PCI audio controller",
           0x000D : "YamahaDS1 native audio ",
           0x0010 : "DS-1 PCI audio controller",
           0x0012 : "DS-1E PCI Audio Controller",
           0x0020 : "DS-1 Audio",
           0x1000 : "Sound system",
           0x2000 : "Digital Mixing Card",
           0x9876 : "yamaha",
         },
0x1074 : { 0x4E78 : "Nx586 Chipset",
         },
0x1077 : { 0x1016 : "Single Channel Ultra3 SCSI Processor",
           0x1020 : "Fast-wide SCSI - Sparc PCI",
           0x1022 : "Fast-wide SCSI",
           0x1080 : "SCSI Host Adapter",
           0x1216 : "Dual Channel Ultra3 SCSI Processor",
           0x1240 : "SCSI Host Adapter",
           0x1280 : "SCSI Host Adapter",
           0x2020 : "Fast!SCSI Basic Adapter",
           0x2100 : "64-bit Fibre Channel Adapter",
           0x2200 : "PCI Fibre Channel Adapter",
           0x2300 : "64-bit PCI FC-AL Adapter",
           0x2312 : "Fibre Channel Adapter",
           0x2422 : "QLogic PCI to Fibre Channel Host Adapter for QLA2460",
           0x2432 : "4Gb PCI Single/Dual Fibre Channel HBA",
           0x2532 : "8Gb PCIe x8 Single/Dual Fibre Channel HBA",
           0x3010 : "n/a",
           0x3032 : "QLOGIC Dual Port 1GBPS PCI-E HBA",
           0x4000 : "",
           0x4010 : "",
           0x6312 : "Qlogic FC-HBA QLA200",
           0x6422 : "4-Gbps Fibre Channel to PCI-X 2.0 266MHz controller for Embedded Applications",
           0x6432 : "4-Gbps Fibre Channel to PCIe controller for Embedded Applications",
           0x8000 : "QLE8142 QLogic PCI Express to 10 GbE Dual Channel CNA",
           0x8001 : "QLE8142 QLogic PCI Express to 10 GbE Dual Channel CNA (FCoE)",
           0x8020 : "QLogic Dual Port 10 Gigabit Ethernet CNA",
           0x8021 : "QLogic [FCoE] Adapter",
           0x8022 : "QLE8142 QLogic PCI Express to 10 GbE Dual Channel CNA (iSCSI)",
         },
0x1078 : { 0x0000 : "ISA Bridge",
           0x0001 : "Cyrix Integrated CPU",
           0x0002 : "ISA Bridge",
           0x0100 : "ISA bridge",
           0x0101 : "SMI status and ACPI timer",
           0x0102 : "IDE Controller",
           0x0103 : "XpressAUDIO",
           0x0104 : "Video Controller",
           0x0400 : "CPU to PCI Bridge",
           0x0401 : "Power Management Controller",
           0x0402 : "IDE Controller",
           0x0403 : "Expansion Bus",
         },
0x1079 : { 0x0d01 : "",
           0x10de : "zdzvz",
         },
0x107D : { 0x0000 : "Graphic GLU-Logic",
         },
0x107E : { 0x0001 : "FRED Local Bus I/F to PCI Peripheral",
           0x0002 : "100 vg anylan Cntrlr",
           0x0004 : "Fibre Channel Host Adapter",
           0x0005 : "Fibre Channel Host Adapter",
           0x0008 : "(i)chipSAR+ 155 MBit ATM controller",
           0x9003 : "",
           0x9007 : "",
           0x9008 : "",
           0x900C : "",
           0x900E : "",
           0x9011 : "",
           0x9013 : "",
           0x9023 : "",
           0x9027 : "",
           0x9031 : "",
           0x9033 : "Adapter",
           0x9060 : "CompactPCI T1/E1/J1Communications Ctrlr",
           0x9070 : "PMC T1/E1/J1 Communications Controller",
           0x9080 : "PMC ATM Over OC-3/STM-1 Comm Controller",
           0x9081 : "PMC ATM Over OC-3/STM-1 Comm Controller",
           0x9082 : "PMC ATM Over OC-3/STM-1 Comm Controller",
           0x9090 : "PMC ATM Over T3/E3 Communications Ctrlr",
           0x90A0 : "PMC Quad T1/E1/J1 Communications Ctrlr",
         },
0x107F : { 0x0802 : "pinacale capture card",
           0x0803 : "EIDE Bus Master Controller",
           0x0806 : "EIDE Controller",
           0x2015 : "EIDE Controller",
         },
0x1080 : { 0x0600 : "CPU to PCI & PCI to ISA Bridge",
           0xC691 : "AN2131QC 0230",
           0xC693 : "PCI to ISA Bridge",
         },
0x1081 : { 0x0D47 : "Radius PCI to NuBUS Bridge",
         },
0x1083 : { 0x0001 : "PCI Enhanced IDE Adapter",
           0x0613 : "PCI",
         },
0x1085 : { 0x0001 : "Datalaster Interface for OBD automotive",
         },
0x1087 : { 0x9200 : "",
         },
0x1089 : { 0x5555 : "3249",
         },
0x108A : { 0x0001 : "PCI-VME Bus Adapter",
           0x0003 : "PCI to VME Bridge",
           0x0010 : "VME Bridge",
           0x0040 : "",
           0x3000 : "VME Bridge",
         },
0x108D : { 0x0001 : "Token-Ring 16/4 PCI Adapter",
           0x0002 : "Fastload 16/4 PCI/III Token Ring Adapter",
           0x0004 : "RapidFire Token Ring 16/4 Adapter",
           0x0005 : "GoCard Token Ring 16/4 Adapter",
           0x0006 : "RapidFire Token Ring 100 Adapter",
           0x0007 : "RapidFire Token Ring 16/4 Adapter",
           0x0008 : "RapidFire HSTR 100/16/4 Adapter",
           0x000A : "RapidFire Token-Ring 16/4 PCI Adapter",
           0x0011 : "Ethernet Controller",
           0x0012 : "Ethernet PCI/II 10/100 Controller",
           0x0013 : "PCI/II Ethernet Controller",
           0x0014 : "Ethernet PCI/II 10/100 Controller",
           0x0019 : "10/100 Ethernet Controller",
           0x0021 : "155 Mbit ATM Adapter",
           0x0022 : "ATM Adapter",
         },
0x108E : { 0x0001 : "",
           0x1000 : "PCI Input/Output Controller",
           0x1001 : "Happy Meal Ethernet",
           0x1100 : "",
           0x1101 : "",
           0x1102 : "",
           0x1103 : "",
           0x2BAD : "Sun Gigabit Ethernet Card",
           0x5000 : "UltraSPARC-IIi Advanced PCI Bridge",
           0x5043 : "Co-processor",
           0x7063 : "PCI card with Intel or AMD processor",
           0x8000 : "UPA to PCI Interface (UPA)",
           0x8001 : "PCI Bus Module",
           0xA000 : "Sabre",
           0xA001 : "Hummingbird",
           0xabba : "10/100/1000 Ethernet adapter",
         },
0x1091 : { 0x0020 : "3D Graphics Processor",
           0x0021 : "3D graphics processor w/texturing",
           0x0040 : "3D graphics frame buffer",
           0x0041 : "3D graphics frame buffer",
           0x0060 : "Proprietary bus Bridge",
           0x00E4 : "",
           0x0720 : "Motion JPEG Codec",
         },
0x1092 : { 0x00A0 : "GUI Accelerator",
           0x00A8 : "GUI Accelerator",
           0x0550 : "",
           0x08D4 : "WinModem",
           0x094C : "SupraExpress 56i Pro",
           0x09C8 : "SupraExpress 56i Pro VCC",
           0x1002 : "RS56-pci",
           0x1092 : "2710a",
           0x6120 : "DVD",
           0x8810 : "GUI Accelerator",
           0x8811 : "GUI Accelerator",
           0x8880 : "",
           0x8881 : "GUI Accelerator",
           0x88B0 : "GUI Accelerator",
           0x88B1 : "GUI Accelerator",
           0x88C0 : "GUI Accelerator",
           0x88C1 : "GUI Accelerator",
           0x88D0 : "GUI Accelerator",
           0x88D1 : "GUI Accelerator",
           0x88F0 : "GUI Accelerator",
           0x88F1 : "GUI Accelerator",
           0x9876 : "Supra Express 56i Pro CW #2",
           0x9999 : "Diamand Technology DT0398",
         },
0x1093 : { 0x0160 : "data adquisition input and output",
           0x0161 : "Multifunction data acquisition board",
           0x0162 : "24MIO  6-03-2",
           0x1150 : "High Speed Digital I/O Board",
           0x1170 : "",
           0x1180 : "base system device",
           0x1190 : "",
           0x11B0 : "",
           0x11C0 : "",
           0x11D0 : "",
           0x11E0 : "",
           0x1270 : "Multifunction Data Acquisition Card",
           0x12b0 : "High Speed DIO",
           0x1310 : "Data Acquisition Device",
           0x1320 : "",
           0x1330 : "",
           0x1340 : "Multifunction Data Acquisition Card",
           0x1350 : " NI PCI-6071E Multifunction I/O & NI-DAQ",
           0x1360 : "",
           0x17D0 : "",
           0x18B0 : "",
           0x28b0 : "I/O Terminal NI-DAQ (Legacy) and NI-DAQmx",
           0x2A60 : "",
           0x2A70 : "Multifunction Data Acquisition Card",
           0x2A80 : "Multifunction Data Acquisition Card",
           0x2B20 : "",
           0x2C80 : "",
           0x2CA0 : "PCI-6034E",
           0x702C : "NI FPGA Modul",
           0x70af : "16-Bit",
           0x70b8 : "Multifunction DAQ Device",
           0x70E3 : "NI PXI-8431/8 (RS485/RS422)",
           0x70E4 : "NI PCI-8430/8 (RS-232) Interface",
           0x710e : "GPIB Controller Interface Board",
           0x71BC : "16-Bit",
           0x7414 : "NI PCIe-GPIB+ GPIB with analyzer",
           0xB001 : "",
           0xB011 : "",
           0xB021 : "",
           0xB031 : "",
           0xB041 : "1pcs",
           0xB051 : "",
           0xB061 : "",
           0xB071 : "IMAQ-PCI-1422",
           0xB081 : "",
           0xB091 : "bluethooth",
           0xC801 : "GPIB Controller Interface Board",
           0xC811 : "",
           0xC821 : "",
           0xC831 : "PCI-GPIB",
           0xC840 : "",
           0xd130 : "2-port RS-232 Serial Interface Board",
         },
0x1095 : { 0x0240 : "SIL3112",
           0x0242 : "SIL3132",
           0x0244 : "SIL3132",
           0x0640 : "PCI0640A/B",
           0x0641 : "pci0640",
           0x0642 : "PCI0642",
           0x0643 : "PCI0643",
           0x0646 : "CMD646",
           0x0647 : "PCI0647",
           0x0648 : "PCI-648",
           0x0649 : "PCI-649",
           0x0650 : "PBC0650A",
           0x0670 : "USB0670",
           0x0673 : "USB0673",
           0x0680 : "SiI 0680/680A",
           0x1392 : "1390/1392",
           0x2455 : "SI3124",
           0x3112 : "SIL3112",
           0x3114 : "Sil 3114",
           0x3124 : "SiI 3124",
           0x3132 : "SiI 3132",
           0x3512 : "Sil 3512",
           0x3531 : "3531",
           0x9876 : "0x9876",
         },
0x1096 : { 0x1106 : "Realtek AC97 Audio for VIA (R) Audio Controller",
           0x3059 : "South Bridge",
         },
0x1097 : { 0x0038 : "EIDE Controller (single FIFO)",
         },
0x1098 : { 0x0001 : "EIDE Controller",
           0x0002 : "EIDE Controller",
         },
0x109A : { 0x8280 : "4 channel video digitizer cardm",
         },
0x109E : { 0x0350 : "rb8701.1",
           0x0350 : "tv tuner driverhj",
           0x0351 : "BrookTree Bt848 Video Capture Device - Audio Section	PCI",
           0x0369 : "Video Capture",
           0x036C : "",
           0x036E : "AVerMediaAverTV WDM AudioCapture (878)",
           0x036E : "Video Capture",
           0x036E : "Video Capture",
           0x036F : "Video Capture",
           0x0370 : "Video Capture (10 bit High qualtiy cap)",
           0x0878 : "AVerMediaAverTV WDM AudioCapture (878)",
           0x0879 : "Video Capture (Audio Section)",
           0x0880 : "Video Capture (Audio Section)",
           0x109E : "Multimedia Video Controllerm",
           0x109E : "0400 video devce",
           0x2115 : "BtV Mediastream Controller 9x",
           0x2125 : "BtV Mediastream Controller",
           0x2164 : "Display Adapter",
           0x2165 : "MediaStream Controller",
           0x36e : "25878-13",
           0x36E : "Brooktree Corp",
           0x36E : "conexant 878a",
           0x8230 : "ATM Segment/Reassembly Controller (SRC)",
           0x8472 : "32/64-channel HDLC Controllers",
           0x8474 : "128-channel HDLC Controller",
         },
0x109F : { 0x036F : "Video Capturee",
         },
0x10A4 : { 0X5969 : "",
         },
0x10A8 : { 0x0000 : "ethernet controller",
         },
0x10A9 : { 0x0004 : "",
           0x0005 : "",
           0x0006 : "",
           0x0007 : "",
           0x0008 : "",
           0x0009 : "Gigabit Ethernet",
           0x0010 : "Video I/O",
           0x0011 : "",
           0x0012 : "",
           0x1001 : "",
           0x1002 : "",
           0x1003 : "",
           0x1004 : "",
           0x1005 : "",
           0x1006 : "",
           0x1007 : "",
           0x1008 : "",
           0x2001 : "Fibre Channel",
           0x2002 : "",
           0x8001 : "",
           0x8002 : "",
         },
0x10AB : { 0x1005 : "USB Pendrive",
           0x1007 : "usb pendrive",
           0x8086 : "PCI Simple Communications Controller ",
         },
0x10AD : { 0x0001 : "EIDE Ctrlr",
           0x0103 : "PCI-ide mode 4.5 Cntrlr",
           0x0105 : "Sonata bus master PCI-IDE controller",
           0x0565 : "PCI/ISA bridge",
         },
0x10B5 : { 0x0324 : "",
           0x0480 : "Integrated PowerPC I/O Processor",
           0x0960 : "PCI Reference Design Kit for PCI 9080",
           0x1030 : "ISDN card",
           0x1054 : "dual channel ISDN card",
           0x1078 : "Vision Systems VScom PCI-210",
           0x1103 : "Vision Systems VScom PCI-200",
           0x1146 : "Vision Systems VScom PCI-010S",
           0x1147 : "Vision Systems VScom PCI-020S",
           0x1151 : "ISDN card",
           0x1152 : "ISDN card",
           0x2724 : "Thales PCSM Security Card",
           0x2748 : "TPCX Transientrecorder Card",
           0x3001 : "gpscard",
           0x5406 : "PCI Reference Design Kit for PLX PCI 9054",
           0x5601 : "32-bit; 66MHz PCI Bus Master I/O Accelerator",
           0x6520 : "PCI-X to PCI-X Bridge",
           0x6ACC : "General Mechatronics 6 Axis Motion Control Card for EMC2",
           0x8111 : "1 Lane PCI Express to PCI bridge (PEX8111); 1 Lane PCI Express to Generic Local Bus bridge (PEX8311)",
           0x8112 : "1 Lane PCI Express to PCI bridge",
           0x8508 : "8 Lane",
           0x8509 : "8-lane PCI-Express Switch",
           0x8516 : "Versatile PCI Express Switch",
           0x8518 : "PLX PCI-e switch",
           0x8532 : "Versatile PCI Express Switch",
           0x8548 : "48-lane PCIe switch",
           0x8609 : "8 Lane",
           0x8664 : "64-Lane",
           0x9030 : "PCI SMARTarget I/O Accelerator",
           0x9036 : "Interface chip - value 1k",
           0x9050 : "Target PCI Interface Chip - value 1k",
           0x9052 : "PCI 9052 Target PLX PCI Interface Chip",
           0x9054 : "PCI I/O Accelerator",
           0x9056 : "32-bit",
           0x9060 : "PCI Bus Master Interface Chip",
           0x906D : "PCI Bus Master Interface Chip",
           0x906E : "PCI Bus Master Interface Chip",
           0x9080 : "High performance PCI to Local Bus chip",
         },
0x10B6 : { 0x0001 : "Ringnode (PCI1b)",
           0x0002 : "Ringnode (PCIBM2/CardBus)",
           0x0003 : "Ringnode",
           0x0004 : "Smart 16/4 Ringnode Mk1 (PCIBM1)",
           0x0006 : "16/4 CardBus Adapter (Eric 2)",
           0x0007 : "",
           0x0009 : "Smart 100/16/4 PCi-HS Ringnode",
           0x000A : "Smart 100/16/4 PCI Ringnode",
           0x000B : "16/4 CardBus  Adapter Mk2",
           0x1000 : "ATM adapter",
           0x1001 : "ATM adapter",
           0x1002 : "ATM Adapter",
         },
0x10B7 : { 0x0001 : "1000BaseSX Gigabit Etherlink",
           0x0013 : "3Com11a/b/g Wireless PCI Adapter ",
           0x1000 : "3COM 3C905CX-TXNM with 40-0664-003 ASIC",
           0x1006 : "Broadcom Corporation NetXtreme BCM5701 Gigabit Ethernet",
           0x1007 : "V.90 Mini-PCI Modem",
           0x1700 : "Gigabit Ethernet PCI CODEC",
           0x1F1F : "AirConnect Wireless LAN PCI Card",
           0x3390 : "Token Link Velocity",
           0x3590 : "TokenLink Velocity XL Adapter",
           0x4500 : "Cyclone",
           0x5055 : "Laptop Hurricane",
           0x5057 : "Megahertz 10/100 LAN CardBus PC Card",
           0x5157 : "Megahertz 10/100 LAN CardBus PC Card",
           0x5257 : "Cyclone Fast Ethernet CardBus PC Card",
           0x5900 : "Ethernet III Bus Fast PCI",
           0x5920 : "PCI/EISA 10Mbps Demon/Vortex",
           0x5950 : "100MB PCI Ethernet Adapter",
           0x5951 : "Fast EtherLink PCI T4",
           0x5952 : "Fast EtherLink PCI MII",
           0x5970 : "PCI/EISA Fast Demon/Vortex",
           0x5B57 : "Megahertz 10/100 LAN CardBus",
           0x6055 : "10/100 Fast Ethernet MiniPCI Adapter",
           0x6056 : "MiniPCI 10/100 Ethernet+Modem56k (see devid:1007)",
           0x6560 : "Cyclone CardBus PC Card",
           0x6561 : "10/100 LAN+56K Modem CardBus PC Card",
           0x6562 : "Cyclone CardBus PC Card",
           0x6563 : "10/100 LAN+56K Modem CardBus PC Card",
           0x6564 : "Cyclone CardBus PC Card",
           0x6565 : "Global 10/100 Fast Ethernet+56K Modem",
           0x7646 : "3com",
           0x7770 : "AirConnect Wireless PCI",
           0x8811 : "Token Ring",
           0x9000 : "Fast Etherlink PCI TPO NIC",
           0x9001 : "Fast Etherlink XL PCI Combo NIC",
           0x9004 : "EtherLink XL TPO 10Mb",
           0x9005 : "Fast Etherlink 10Mbps Combo NIC",
           0x9006 : "EtherLink XL TPC",
           0x900A : "EtherLink PCI Fiber NIC",
           0x9041 : "Fast Etherlink XL 10/100",
           0x9050 : "Fast Etherlink XL PCI 10/100",
           0x9051 : "Fast Etherlink XL 10/100",
           0x9055 : "Fast Etherlink 10/100 PCI TX NIC",
           0x9056 : "Fast EtherLink XL 10/100",
           0x9058 : "Deluxe EtherLink 10/100 PCI Combo NIC",
           0x905A : "Fast EtherLink 100 Fiber NIC",
           0x9200 : "3Com 10/100 Managed NIC 3C905CX-TX-M",
           0x9201 : "Integrated Fast Ethernet Controller",
           0x9202 : "3C920B-EMB 3Com + Realtek 8201L",
           0x9210 : "Integrated Fast Ethernet Controller",
           0x9300 : "3ComSOHO100B-TX",
           0x9800 : "Fast EtherLink XL Server Adapter2",
           0x9805 : "Python-T 10/100baseTX NIC",
           0x9876 : "3C920B-EMB 3Com + Realtek 8201L",
           0x9902 : "EtherLink 10/100 PCI with 3XP Processor",
           0x9903 : "EtherLink 10/100 PCI with 3XP Processor",
           0x9905 : "100FX PCI Server NIC w/3XP",
           0x9908 : "EtherLink 10/100 Server PCI with 3XP",
           0x9909 : "EtherLink 10/100 Server PCI with 3XP",
           0xD004 : "EtherLink XL PCI",
         },
0x10B8 : { 0x0005 : "EPIC/XF 10/100 Mbps Fast Ethernet Ctrlr",
           0x0006 : "EPIC/C Ethernet CardBus Integrated Ctrlr",
           0x1000 : "FDC",
           0x1001 : "FDC",
           0xA011 : "Fast ethernet controller",
           0xB106 : "CardBus Controller",
         },
0x10B9 : { 0x0101 : "PCI Audio Device (OEM)",
           0x0102 : "PCI Audio Device (OEM)",
           0x0111 : "C-Media Audio Device (OEM)",
           0x0780 : "Multi-IO Card",
           0x0782 : "Multi-IO Card",
           0x10b9 : "0402t505 CK46828100B",
           0x10CE : "cpi",
           0x1435 : "VL Bridge",
           0x1445 : "CPU to PCI & PCI to ISA Bridge w/EIDE",
           0x1449 : "ISA Bridge",
           0x1451 : "Pentium CPU to PCI Bridge",
           0x1461 : "P54C Chipset",
           0x1489 : "486 PCI Chipset",
           0x1511 : "Aladdin 2 Host Bridge",
           0x1513 : "Aladdin 2 South Bridge",
           0x1521 : "Bios",
           0x1523 : "ISA Bridge",
           0x1533 : "PCI South Bridge",
           0x1535 : "ISA Bridge",
           0x1541 : "Aladdin V AGPset Host Bridge",
           0x1543 : "Aladdin V chipset South Bridge",
           0x1561 : "North Bridge",
           0x1563 : "South Bridge with Hypertransport Support",
           0x1632 : "North Bridge",
           0x1641 : "CPU to PCI Bridge",
           0x1644 : "AGP System Controller",
           0x1646 : "AGP System Controller",
           0x1647 : "CPU to PCI Bridge",
           0x1651 : "CPU to PCI Bridge",
           0x1661 : "AGP System Controller",
           0x1667 : "AGP System Controller",
           0x1671 : "Super P4 Nouth Bridge",
           0x1672 : "AGP System Controller",
           0x1681 : "P4 Nouth Bridge with HyperTransport",
           0x1687 : "K8 North Bridge with HyperTransport",
           0x1849 : "023&267A616A",
           0x3141 : "GUI Accelerator",
           0x3143 : "GUI Accelerator",
           0x3145 : "GUI Accelerator",
           0x3147 : "GUI Accelerator",
           0x3149 : "GUI Accelerator",
           0x3151 : "GUI Accelerator",
           0x3307 : "MPEG-1 Decoder",
           0x3309 : "MPEG Decoder",
           0x3432 : "131312",
           0x5212 : "",
           0x5215 : "EIDE Ctrlr",
           0x5217 : "I/O (?)",
           0x5219 : "Ali M5219 PCI BUS MASTER IDE Controller",
           0x5225 : "IDE Controller",
           0x5228 : "M5228 PATA/RAID Controller",
           0x5229 : "EIDE Controller",
           0x5229 : "Ali EIDE",
           0x5229 : "PATA 33",
           0x5229 : "PATA 66",
           0x5229 : "PATA 100",
           0x5229 : "PATA 133",
           0x5235 : "ALI M6503c",
           0x5236 : "EHCI USB 2.0",
           0x5237 : "OpenHCI 1.1 USB to  2.0",
           0x5239 : "USB EHCI2.0 Controller",
           0x5249 : "HyperTransport to PCI Bridge",
           0x5251 : "IEEE P1394 OpenHCI 1.0 Controller",
           0x5253 : "IEEE P1394 OpenHCI 1.0 Controller",
           0x5261 : "Ethernet Controller",
           0x5263 : "ULi PCI Fast Ethernet Controller",
           0x528 : "023&267A616A",
           0x5281 : "ALI M5281/5283  SATA/RAID Controller",
           0x5286 : "REV_C7",
           0x5287 : "SATA/Raid controller",
           0x5288 : "M5288 SATA/Raid controller (Asrock 939SLI32-eSata2)",
           0x5289 : "M5289 SATA/Raid controller",
           0x5450 : "Agere Systems AC97 Modem",
           0x5451 : "Ali Audio Accelerator",
           0x5455 : "AC'97 Audio Controller",
           0x5457 : "AC97 Modem controller",
           0X5459 : "PCI Soft Modem V92 NetoDragon",
           0x5461 : "High Definition Audio Controller",
           0x5471 : "Memory Stick Host",
           0x5473 : "MMC/SD controller",
           0x7101 : "Power Management Controller",
           0x7471 : "Memory Stick Host",
           0x9876 : "xhcth700000b",
         },
0x10BA : { 0x0304 : "GUI Accelerator",
         },
0x10BD : { 0x0803 : "Ethernet PCI Adapter",
           0x0E34 : "Ethernet Adapter (NE2000 PCI clone)",
           0x5240 : "IDE Cntrlr",
           0x5241 : "PCMCIA Bridge",
           0x5242 : "General Purpose Cntrlr",
           0x5243 : "Bus Cntrlr",
           0x5244 : "FCD Cntrlr",
           0x8136 : "Unkown",
           0x8139 : "realtek 8139c",
         },
0x10C3 : { 0x8920 : "MCP67 High Definition Audio ",
           0x8925 : "",
         },
0x10C4 : { 0x8363 : "",
           0xEA60 : "Silicon Labs CP210x USB to UART Bridge",
         },
0x10C8 : { 0004 : "MagicGraph 128XD",
           0x0000 : "Graphics Cntrlr",
           0x0003 : "MagicGraph 128ZV Video Controller",
           0x0004 : "MagicGraph 128XD",
           0x0005 : "MagicMedia 256AV",
           0x0006 : "MagicMedia 256ZX/256M6D",
           0x0016 : "MagicMedia 256XL+",
           0x0025 : "MagicMedia 256AV+",
           0x0083 : "Graphic Controller NeoMagic MagicGraph128ZV+",
           0x8005 : "MagicMedia 256AV Audio Device",
           0x8006 : "MagicMedia 256ZX Audio Device",
           0x8016 : "MagicMedia 256XL+ Audio Device",
         },
0x10CA : { 0x9876 : "PCIVEN_8086&DEV_293E&SUBSYS_26341019&REV_023&11583659&0&D8",
         },
0x10CD : { 0x1100 : "PCI SCSI Host Adapter",
           0x1200 : "Fast SCSI-II",
           0x1300 : "ABP-3925",
           0x2300 : "PCI Ultra Wide SCSI Host Adapter",
           0x2500 : "PCI Ultra 80/160 SCSI Controllers",
           0x4000 : "IEEE-1394 OHCI PCI Controller",
         },
0x10CF : { 0x10C5 : "Serial Parallel Card",
           0x2001 : "PCI SCSI Host Adapter (Fast Wide SCSI-2)",
           0x2002 : "Fast Wide SCSI Controller",
           0x2005 : "10/100 Fast Ethernet Adapter",
           0x200C : "IEEE1394 OpenHCI Controller",
           0x2010 : "OHCI FireWire Controller",
           0x2011 : "MPEG2 R-Engine (MPEG2 Hardware Encoder)",
           0x2019 : "Coral-P Graphics Chip",
           0x201E : "Coral-PA Graphics Chip",
           0x202A : "u/k",
           0x202B : "Carmine Graphisc adapter",
         },
0x10D6 : { 0xFF51 : "ATJ2091N",
           0xff66 : "ATJ2091N",
         },
0x10D9 : { 0x0066 : "sdas",
           0x0512 : "Fast Ethernet Adapter",
           0x0531 : "Single Chip Fast Ethernet NIC Controller",
           0x0532 : "PCI/CardBus Fast Ethernet Controller",
           0x0553 : "Ethernet Adapter",
           0x8625 : "xiankasqudong",
           0x8626 : "PCIVEN_10D9&DEV_8626&SUBSYS_00000000&REV_004&1F7DBC9F&0&08F0 ",
           0x8627 : "Voodoo Rush MX86251",
           0x8888 : "9619E",
           0xC115 : " Linksys LNE100TX ",
         },
0x10DC : { 0x0001 : "PCI-SCI  PMC  mezzanine",
           0x0002 : "SCI bridge  on PCI 5 Volt card",
           0x0004 : "ALTERA STRATIX",
           0x0010 : "Simple PMC/PCI to S-LINK interface",
           0x0011 : "Simple S-LINK to PMC/PCI interface",
           0x0012 : "32-bit S-LINK to 64-bit PCI interface",
           0x0021 : "HIPPI destination",
           0x0022 : "HIPPI source",
           0x0033 : "ALICE DDL to  PCI interface (RORC)",
           0x0101 : "Acquisition card for the SPS Orbit System (MACI)",
           0x016A : "CALICE ODR",
           0x10DC : "TTC sr   first TTC chip receiver PMC",
           0x301 : "based on the PLX PCI 9030 to build a MIL1553 bus interface",
           0x324 : "64 Bit/66MHz PCI to Local Bus Bridge",
           0x8086 : "geodelink pci south",
         },
0x10DD : { 0x0001 : "3D graphics processor",
         },
0x10DE : { 0x04EF : "Riva 128",
           0x0001 : "SoundMAX Integrated Digital Audio",
           0x0002 : "HDMI Audio Driver Driver",
           0x0003 : "nVIDIA High Definition Audio/HDMI ",
           0x0006 : "realtek based HD Audio",
           0x0008 : "Edge 3D",
           0x0009 : "Edge 3D",
           0x000B : "HDMI Audio Driver Driver 1.00.00.59",
           0x0010 : "Mutara V08",
           0x0011 : "NVIDIA High Def Audio",
           0x0018 : "Riva 128",
           0x0019 : "Riva 128ZX",
           0x001D : "nVidia GeForce FX 5900XT",
           0x0020 : "NVIDIA RIVA TNT",
           0x0028 : "MCP67 ",
           0x0028 : "ACPINSC1200",
           0x0029 : "NVIDIA RIVA TNT 2 Ultra",
           0x002A : "TNT2",
           0x002B : "Riva TNT2",
           0x002C : "NVIDIA Vanta/Vanta LT",
           0x002D : "NVIDIA RIVA TNT2 Model 64/Model 64 AGP 32M",
           0x002E : "VANTA",
           0x002F : "VANTA",
           0x0035 : "MCP04 PATA Controller",
           0x0036 : "MCP04 SATA/RAID Controller",
           0x003E : "MCP04 SATA/RAID Controller",
           0x0040 : "NVIDIA GeForce 6800 Ultra",
           0x0041 : "NVIDIA GeForce 6800",
           0x0042 : "NVIDIA GeForce 6800 LE",
           0x0043 : "NVIDIA GeForce 6800 XE",
           0x0044 : "NVIDIA GeForce 6800 XT",
           0x0045 : "NVIDIA GeForce 6800 GT",
           0x0046 : "NVIDIA GeForce 6800 GT",
           0x0047 : "NVIDIA GeForce 6800 GS",
           0x0048 : "NVIDIA GeForce 6800 XT",
           0x0049 : "NVIDIA NV40GL",
           0x004D : "NVIDIA Quadro FX 3400",
           0x004E : "NVIDIA Quadro FX 4000",
           0x0052 : "NVIDIA nForce PCI System Management",
           0x0053 : "CK804 PATA Controller",
           0x0054 : "CK804 SATA/RAID Controller",
           0x0055 : "CK804 SATA/RAID Controller",
           0x0057 : "NVIDIA Network Bus Enumerator",
           0x0059 : "nForce Audio Controller",
           0x005E : "nForce4 HyperTransport Bridge",
           0x0060 : "PCI to ISA Bridge",
           0x0064 : "SMBus Controller",
           0x0065 : "PATA Controller",
           0x0066 : "nForce 2 Networking Controller",
           0x0067 : "Nvidia 7050 chipset HDMI Audio",
           0x0068 : "EHCI USB 2.0 Controller",
           0x006A : "nForce AC97s",
           0x006B : "Audio Processing Unit (Dolby Digital)",
           0x006C : "PCI to PCI Bridge",
           0x006D : "Audio Codec Interface",
           0x006E : "OHCI Compliant IEEE 1394 Controller",
           0x0085 : "MCP2S PATA Controller",
           0x008C : "Single-Port 10/100M Fast Ethernet PHYceiver",
           0x008E : "MCP2S SATA/RAID Controller",
           0x0090 : "NVIDIA GeForce 7800 GTX",
           0x0091 : "NVIDIA GeForce 7800 GTX",
           0x0092 : "NVIDIA GeForce 7800 GT",
           0x0093 : "NVIDIA GeForce 7800 GS",
           0x0094 : "NVIDIA GeForce 7800SE/XT/LE/LT/ZT",
           0x0095 : "NVIDIA GeForce 7800 SLI",
           0x0098 : "NVIDIA GeForce Go 7800",
           0x0099 : "NVIDIA GeForce Go 7800 GTX",
           0x009C : "NVIDIA Quadro FX 350M",
           0x009D : "NVIDIA Quadro FX 4500",
           0x009E : "NVIDIA G70GL",
           0x00A0 : "Aladdin TNT2",
           0x00C0 : "NVIDIA GeForce 6800 GS",
           0x00C1 : "NVIDIA GeForce 6800",
           0x00C2 : "NVIDIA GeForce 6800 LE",
           0x00C3 : "NVIDIA GeForce 6800 XT",
           0x00C8 : "NVIDIA GeForce Go 6800",
           0x00C9 : "NVIDIA GeForce Go 6800 Ultra",
           0x00CC : "NVIDIA Quadro FX Go 1400",
           0x00CD : "NVIDIA Quadro FX 3450/4000 SDI",
           0x00CE : "NVIDIA Quadro FX 1400",
           0x00D0 : "LPC Bridge",
           0x00D1 : "Host Bridge",
           0x00D2 : "PCI-to-PCI Bridge",
           0x00D4 : "SMBus Controller",
           0x00D5 : "CK8 PATA 133/PATA to SATA Bridge",
           0x00D6 : "nForce 3 Networking Controller",
           0x00D7 : "OpenHCD USB Host Controller",
           0x00D8 : "Enhanced PCI to USB Host Controller",
           0x00D9 : "Agere System PCI Soft Modem",
           0x00DA : "AC97 Audio Controller",
           0x00DD : "PCI-to-PCI Bridge",
           0x00DF : "nForce 7 Networking Controller",
           0x00E0 : "LPC Interface Bridge",
           0x00E1 : "Host/PCI Bridge",
           0x00E2 : "AGP Host to PCI Bridge",
           0x00E3 : "CK8S SATA/RAID Controller",
           0x00E4 : "PCI System Management",
           0x00E5 : "Parallel ATA Controller",
           0x00E7 : "OpenHCD USB Controller",
           0x00E8 : "Enhanced PCI to USB Controller",
           0x00EA : "Audio Codec Interface (Realtek ALC658)",
           0x00ED : "PCI-PCI Bridge",
           0x00EE : "CK8S SATA/RAID Controller",
           0x00F0 : "NVIDIA Device",
           0x00F1 : "NVIDIA GeForce 6600 GT",
           0x00F2 : "NVIDIA GeForce 6600",
           0x00F3 : "NVIDIA GeForce 6200",
           0x00F4 : "NVIDIA GeForce 6600 gt",
           0x00F5 : "NVIDIA GeForce 7800 GS",
           0x00F6 : "NVIDIA GeForce 6800 GS/XT",
           0x00F8 : "NVIDIA Quadro FX 3400/4400",
           0x00F9 : "NVIDIA GeForce 6800 Series GPU",
           0x00FA : "NVIDIA GeForce PCX 5750",
           0x00FB : "NVIDIA GeForce PCX 5900",
           0x00FC : "NVIDIA GeForce PCX 5300",
           0x00FD : "NVIDIA Quadro PCI-E Series",
           0x00FE : "NVIDIA Quadro FX 1300",
           0x00FF : "NVIDIA GeForce PCX 4300",
           0x0100 : "HDAUDIOFUNC_01&VEN_10EC&DEV_0662&SUBSYS_1B0A0062&REV_10014&22548B7C&0&0001",
           0x0101 : "NVIDIA GeForce DDR",
           0x0102 : "GeForce 256 Ultra",
           0x0103 : "NVIDIA Quadro",
           0x0110 : "NVIDIA GeForce2 MX/MX 400",
           0x0111 : "NVIDIA GeForce2 MX 100/200",
           0x0112 : "NVIDIA GeForce2 Go",
           0x0112 : "Nvidia GeForce2 Go/MX Ultra Video Adapter",
           0x0113 : "NVIDIA Quadro2 MXR/EX",
           0x0140 : "NVIDIA GeForce 6600 GT",
           0x0141 : "nVIDIA GeForce 6600 PCI-E Video Adapter",
           0x0142 : "NVIDIA GeForce 6600 LE",
           0x0143 : "NVIDIA GeForce 6600 VE",
           0x0144 : "NVIDIA GeForce Go 6600",
           0x0145 : "NVIDIA GeForce 6610 XL",
           0x0146 : "NVIDIA GeForce Go 6200 TE/6600 TE",
           0x0147 : "NVIDIA GeForce 6700 XL",
           0x0148 : "NVIDIA GeForce Go 6600",
           0x0149 : "NVIDIA GeForce Go 6600 GT",
           0x014A : "NVIDIA Quadro NVS 440",
           0x014B : "NVIDIA NV43",
           0x014C : "NVIDIA Quadro FX 540M",
           0x014D : "NVIDIA Quadro FX 550",
           0x014E : "NVIDIA Quadro FX 540",
           0x014F : "NVIDIA GeForce 6200",
           0x0150 : "NVIDIA GeForce2 GTS/GeForce2 Pro",
           0x0151 : "NVIDIA GeForce2 Ti",
           0x0152 : "NVIDIA GeForce2 Ultra",
           0x0153 : "NVIDIA Quadro2 Pro",
           0x016 : "1",
           0x0160 : "NVIDIA GeForce 6500 ",
           0x0161 : "NVIDIA GeForce 6200 TurboCache(TM)",
           0x0162 : "NVIDIA GeForce 6200SE TurboCache(TM)",
           0x0163 : "NVIDIA GeForce 6200 LE",
           0x0164 : "NVIDIA NV44",
           0x0165 : "NVIDIA Quadro NVS 285",
           0x0166 : "NVIDIA GeForce Go 6250",
           0x0167 : "NVIDIA GeForce Go 6200",
           0x0168 : "NVIDIA GeForce Go 6400",
           0x0169 : "NVIDIA GeForce 6250",
           0x016a : "NVIDIA GeForce 7100 GS",
           0x016B : "NVIDIA NV44GLM",
           0x016C : "NVIDIA NV44GLM",
           0x016D : "NVIDIA NV44GLM",
           0x016E : "NVIDIA NV44GL",
           0x0170 : "NVIDIA GeForce4 MX 460",
           0x0171 : "NVIDIA GeForce4 MX 440 with AGP 4X 64mb",
           0x0172 : "NVIDIA GeForce4 MX 420",
           0x0173 : "NVIDIA GeForce4 MX 440-SE",
           0x0174 : "NVIDIA GeForce4 MX 440 Go",
           0x0175 : "NVIDIA GeForce4 MX 420 Go",
           0x0176 : "NVIDIA GeForce4 MX 420 Go 32M",
           0x0177 : "NVIDIA GeForce4 460 Go",
           0x0178 : "NVIDIA Quadro4 550 XGL",
           0x0179 : "NVIDIA GeForce4 MX 440 Go 64M",
           0x017A : "NVIDIA Quadro NVS",
           0x017B : "Quadro4 550 XGL",
           0x017C : "NVIDIA Quadro4 500 Go GL",
           0x017D : "NVIDIA GeForce4 410 Go 16M",
           0x0181 : "NVIDIA GeForce4 MX 440 with AGP8X",
           0x0182 : "NVIDIA GeForce4 MX 440SE with AGP8X",
           0x0183 : "NVIDIA GeForce4 MX 420 with AGP8X",
           0x0185 : "NVIDIA GeForce4 MX 4000 128 mb 64 bit",
           0x0186 : "NVIDIA GeForce4 448 Go",
           0x0187 : "NVIDIA GeForce4000 Go",
           0x0188 : "NVIDIA Quadro4 580 XGL",
           0x018A : "NVIDIA Quadro NVS with AGP8X",
           0x018B : "NVIDIA Quadro4 380 XGL",
           0x018C : "NVIDIA Quadro NVS 50 PCI",
           0x018D : "NVIDIA GeForce4 448 Go",
           0x0191 : "NVIDIA GeForce 8800 GTX",
           0x0193 : "NVIDIA GeForce 8800 GTS",
           0x0194 : "NVIDIA GeForce 8800 Ultra",
           0x0197 : "NVIDIA Tesla C870",
           0x019D : "NVIDIA Quadro FX 5600",
           0x019E : "NVIDIA Quadro FX 4600",
           0x01A0 : "NVIDIA GeForce2 Integrated GPU",
           0x01A4 : "AGP Controller",
           0x01A5 : "AGP Controller",
           0x01A6 : "AGP Controller",
           0x01A8 : "Memory Controller (SDR) ddr3",
           0x01A9 : "Memory Controller (SDR)",
           0x01AA : "Memory Controller (DDR)",
           0x01AB : "Memory Controller (DDR)",
           0x01AC : "Memory Controller",
           0x01AD : "Memory Controller",
           0x01B0 : "nForce Dolby Digital Audio Controller",
           0x01B1 : "nForce AC'97 Audio Controller",
           0x01B2 : "HUB Interface",
           0x01B4 : "nForce 1/2 SMBus Controller",
           0x01B7 : "AGP Bridge",
           0x01B8 : "PCI Bridge",
           0x01BC : "nForce IDE/ATA Controller",
           0x01C1 : "AC97 Modem",
           0x01C2 : "OHCI USB Controller",
           0x01C3 : "nForce Networking Controller",
           0x01D0 : "NVIDIA GeForce 7350 LE",
           0x01D1 : "NVIDIA GeForce 7300 LE",
           0x01D2 : "NVIDIA GeForce 7550 LE",
           0x01D3 : "NVIDIA GeForce 7300 SE/7200 GS",
           0x01D5 : "NVIDIA GeForce 7300 LE",
           0x01D7 : "NVIDIA GeForce Go 7300",
           0x01D8 : "NVIDIA GeForce Go 7400",
           0x01DB : "NVIDIA Quadro NVS 120M",
           0x01DC : "NVIDIA Quadro FX 350M",
           0x01DD : "NVIDIA GeForce 7500 LE",
           0x01DE : "NVIDIA Quadro FX 350",
           0x01DF : "NVIDIA GeForce 7300 GS",
           0x01E0 : "AGP Controller",
           0x01E1 : "AGP Controller",
           0x01E8 : "AGP Host to PCI Bridge",
           0x01EA : "Memory Controller 0",
           0x01EB : "Memory Controller 1",
           0x01EC : "Memory Controller 2",
           0x01ED : "Memory Controller 3",
           0x01EE : "Memory Controller 4",
           0x01EF : "Memory Controller 5",
           0x01F0 : "NVIDIA GeForce4 MX Integrated GPU",
           0x0200 : "NVIDIA GeForce3",
           0x0201 : "NVIDIA GeForce3 Ti 200",
           0x0202 : "NVIDIA GeForce3 Ti 500",
           0x0203 : "NVIDIA Quadro DCC",
           0x0210 : "NVIDIA NV48",
           0x0211 : "NVIDIA GeForce 6800",
           0x0212 : "NVIDIA GeForce 6800 LE",
           0x0215 : "NVIDIA GeForce 6800 GT",
           0x0218 : "NVIDIA GeForce 6800 XT",
           0x0220 : "NVIDIA NV44",
           0x0221 : "nVidia Geforce 6200 AGP",
           0x0222 : "NVIDIA GeForce 6200 A-LE",
           0x0228 : "NVIDIA NV44M",
           0x0240 : "NVIDIA GeForce 6150",
           0x0241 : "NVIDIA GeForce 6150 LE",
           0x0242 : "NVIDIA GeForce 6100",
           0x0243 : "PCI Express Bridge",
           0x0244 : "Geforce Go 6150",
           0x0245 : "NVIDIA Quadro NVS 210S / NVIDIA GeForce 6150LE",
           0x0246 : "PCI Express Bridge",
           0x0247 : "Geforce 6100 Go",
           0x0248 : "PCI Express Bridge",
           0x0249 : "PCI Express Bridge",
           0x024A : "PCI Express Bridge",
           0x024B : "PCI Express Bridge",
           0x024C : "PCI Express Bridge",
           0x024D : "PCI Express Bridge",
           0x024E : "PCI Express Bridge",
           0x024F : "PCI Express Bridge",
           0x0250 : "NVIDIA GeForce4 Ti 4600",
           0x0251 : "NVIDIA GeForce4 Ti 4400",
           0x0252 : "NVIDIA GeForce4 Ti",
           0x0253 : "NVIDIA GeForce4 Ti 4200",
           0x0258 : "NVIDIA Quadro4 900 XGL",
           0x0259 : "NVIDIA Quadro4 750 XGL",
           0x025B : "NVIDIA Quadro4 700 XGL",
           0x0264 : "NVIDIA motherboard nForce 430 ( MCP-51 ) with Built-In Geforce 6150 GPU",
           0x0265 : "PATA Controller",
           0x0266 : "NVIDIA nForce 430/410 Serial ATA Controller",
           0x0267 : "NVIDIA nForce 430/410 Serial ATA Controller",
           0x0268 : "NVIDIA nForce Networking Controller",
           0x0269 : "Ethernet Controller ",
           0x026B : "MCP51 AC'97 Audio ",
           0x026C : "Realtek HD Audio Driver",
           0x026e : "MCP51 USB Controller",
           0x0271 : "Coprocessor",
           0x0280 : "NVIDIA GeForce4 Ti 4800",
           0x0281 : "NVIDIA GeForce4 Ti 4200 with AGP8X",
           0x0282 : "NVIDIA GeForce4 Ti 4800 SE",
           0x0286 : "NVIDIA GeForce4 4200 Go",
           0x0288 : "NVIDIA Quadro4 980 XGL",
           0x0289 : "NVIDIA Quadro4 780 XGL",
           0x028C : "NVIDIA Quadro4 700 Go GL",
           0x0290 : "NVIDIA GeForce 7900 GTX",
           0x0291 : "NVIDIA GeForce 7900 GT/GTO",
           0x0292 : "NVIDIA GeForce 7900 GS",
           0x0293 : "NVIDIA GeForce 7950 GX2",
           0x0294 : "NVIDIA GeForce 7950 GX2",
           0x0295 : "NVIDIA GeForce 7950 GT",
           0x0297 : "NVIDIA GeForce Go 7950 GTX",
           0x0298 : "NVIDIA GeForce Go 7900 GS",
           0x0299 : "NVIDIA GeForce Go 7900 GTX",
           0x029B : "NVIDIA Quadro FX 1500M",
           0x029C : "NVIDIA Quadro FX 5500",
           0x029D : "NVIDIA Quadro FX 3500",
           0x029E : "NVIDIA Quadro FX 1500",
           0x029F : "NVIDIA Quadro FX 4500 X2",
           0x02A0 : "NVIDIA NV2A GeForce 3 Integrated (XBOX)",
           0x02e0 : "NVIDIA GeForce 7600 GT",
           0x02E1 : "NVIDIA GeForce 7600 GS",
           0x02E2 : "NVIDIA GeForce 7300 GT",
           0x02E3 : "NVIDIA GeForce 7900 GS",
           0x02E4 : "NVIDIA GeForce 7950 GT",
           0x0300 : "NVIDIA NV30",
           0x0301 : "NVIDIA GeForce FX 5800 Ultra",
           0x0302 : "NVIDIA GeForce FX 5800",
           0x0308 : "NVIDIA Quadro FX 2000",
           0x0309 : "NVIDIA Quadro FX 1000",
           0x030A : "NVIDIA ICE FX 2000",
           0x0311 : "NVIDIA GeForce FX 5600 Ultra",
           0x0312 : "NVIDIA GeForce FX 5600",
           0x0313 : "NVIDIA NV31",
           0x0314 : "NVIDIA GeForce FX 5600XT",
           0x0316 : "NVIDIA NV31M",
           0x0317 : "NVIDIA NV31M Pro",
           0x0318 : "NVIDIA NV31GL",
           0x0319 : "NVIDIA NV31GL",
           0x031A : "NVIDIA GeForce FX Go 5600",
           0x031B : "NVIDIA GeForce FX Go 5650",
           0x031C : "NVIDIA Quadro FX Go 700",
           0x031D : "NVIDIA NV31GLM",
           0x031E : "NVIDIA NV31GLM Pro",
           0x031F : "NVIDIA NV31GLM Pro",
           0x0320 : "NVIDIA GeForce FX 5200",
           0x0321 : "NVIDIA GeForce FX 5200 Ultra",
           0x0322 : "NVIDIA GeForce FX 5200",
           0x0323 : "NVIDIA GeForce FX 5200LE",
           0x0324 : "NVIDIA GeForce FX Go 5200",
           0x0325 : "NVIDIA GeForce FX Go 5250/5500",
           0x0326 : "NVIDIA GeForce GTX 550 Ti",
           0x0327 : "NVIDIA GeForce FX 5100",
           0x0328 : "NVIDIA GeForce FX Go 5200 32/64M",
           0x0329 : "NVIDIA NV34MAP",
           0x032A : "NVIDIA Quadro NVS 55/280 PCI",
           0x032B : "NVIDIA Quadro FX 500/FX 600",
           0x032C : "NVIDIA GeForce FX Go 53x0",
           0x032D : "NVIDIA GeForce FX Go 5100",
           0x032F : "NVIDIA NV34GL",
           0x0330 : "NVIDIA GeForce FX 5900 Ultra",
           0x0331 : "NVIDIA GeForce FX 5900",
           0x0332 : "NVIDIA GeForce FX 5900XT",
           0x0333 : "NVIDIA GeForce FX 5950 Ultra",
           0x0334 : "NVIDIA GeForce FX 5900ZT",
           0x0338 : "NVIDIA Quadro FX 3000",
           0x033F : "NVIDIA Quadro FX 700",
           0x0341 : "NVIDIA GeForce FX 5700 Ultra",
           0x0342 : "NVIDIA GeForce FX 5700",
           0x0343 : "NVIDIA GeForce FX 5700LE",
           0x0344 : "NVIDIA GeForce FX 5700VE",
           0x0345 : "NVIDIA NV36",
           0x0347 : "NVIDIA GeForce FX Go 5700",
           0x0348 : "NVIDIA GeForce FX Go 5700",
           0x0349 : "NVIDIA NV36M Pro",
           0x034B : "NVIDIA NV36MAP",
           0x034C : "NVIDIA Quadro FX Go 1000",
           0x034E : "NVIDIA Quadro FX 1100",
           0x034F : "NVIDIA NV36GL",
           0x0368 : "SMBus controller",
           0x036C : "Standard OpenHCD USB Hostcontroller",
           0x036d : "Standard PCI-to-USB Enhanced Hostcontroller",
           0x036E : "MCP55 PATA Controller",
           0x036F : "MCP55 SATA/RAID Controller",
           0x0371 : "High Definition Audio Controller",
           0x0373 : "NVIDIA nForce Networking Controller",
           0x037E : "MCP55 SATA/RAID Controller",
           0x037F : "MCP55 SATA/RAID Controller",
           0x038B : "NVIDIA GeForce 7650 GS",
           0x0390 : "NVIDIA GeForce 7650 GS",
           0x0391 : "NVIDIA GeForce 7600 GT",
           0x0392 : "NVIDIA GeForce 7600 GS",
           0x0393 : "NVIDIA GeForce 7300 GT",
           0x0394 : "NVIDIA GeForce 7600 LE",
           0x0395 : "NVIDIA GeForce 7300 GT",
           0x0398 : "NVIDIA GeForce Go 7600",
           0x039E : "NVIDIA Quadro FX 560",
           0x039F : "REV_A14&1B41B794&0&00E0",
           0x03AC : "Nvidia Quadro FX 880M",
           0x03D0 : "NVIDIA Graphic driver for XP32",
           0x03D1 : "nForce 520 LE",
           0x03D2 : "NVIDIA GeForce 6100 nForce 400",
           0x03D5 : "NVIDIA GeForce 6100 nForce 420",
           0x03D6 : "NVidia GeForce 7025 nForce 630a",
           0x03E0 : " MCP61 LPC Bridge",
           0x03E1 : "Riva128",
           0x03E7 : "MCP61 SATA/RAID Controller",
           0x03EA : "Memory controller",
           0x03eb : " 85B36Q1",
           0x03EC : "MCP61 PATA Controller",
           0x03EF : " MCP61 Ethernet",
           0x03EF : "GeForce 6100",
           0x03F0 : "Realtek High Defnition Audio getarnt als nVidia MCP",
           0x03F1 : "Serial bus controller",
           0x03F2 : "Serial bus controller",
           0x03F3 : "Bridge",
           0x03F4 : "NVIDIA nForce System Management Controller",
           0x03F5 : "Memory controller",
           0x03F6 : "MCP61 SATA/RAID Controller",
           0x03F7 : "MCP61 SATA/RAID Controller",
           0x0400 : "NVIDIA GeForce 8600 GTS",
           0x0401 : "NVIDIA GeForce 8600 GT",
           0x0402 : "NVIDIA GeForce 8600 GT",
           0x0403 : "NVIDIA GeForce 8600GS",
           0x0404 : "NVIDIA GeForce 8400 GS",
           0x0405 : "GeForce 9500m GS",
           0x0406 : "NVIDIA GeForce 8300 GS",
           0x0407 : "NVIDIA GeForce 8600M GT",
           0x0409 : "Nvidia GeForce 8700M GT",
           0x040a : "NVIDIA Quadro FX 370",
           0x040C : "Mobile Quadro FX/NVS video card",
           0x040E : "NVIDIA Quadro FX 570",
           0x040F : "NVIDIA Quadro FX 1700",
           0x0420 : "NVIDIA GeForce 8400 SE",
           0x0421 : "NVIDIA GeForce 8500 GT",
           0x0422 : "NVIDIA GeForce 8400 GS",
           0x0423 : "NVIDIA GeForce 8300 GS",
           0x0424 : "NVIDIA GeForce 8400 GS",
           0x0425 : "NVIDIA 8600m GS",
           0x0426 : "Geforce 8400M GT GPU",
           0x0427 : "Geforce 8400M GS",
           0x0428 : "NVIDIA GeForce 8400M G",
           0x0429 : "nVidia Quadro NVS 135M or Quadro NVS 140M ",
           0x042b : "NVIDIA Quadro NVS 135M",
           0x042C : "NVIDIA GeForce 8600gts",
           0x042D : "Quadro FX 360 M (Mobile)",
           0x042E : "Mobile graphics",
           0x042f : "NVIDIA Quadro NVS 290",
           0x0448 : "MCP65 PATA Controller",
           0x044C : "MCP65 RAID",
           0x044D : "MCP65 AHCI",
           0x044E : "MCP67D AHCI",
           0x044F : "MCP65 ?AHCI",
           0x0450 : "A3",
           0x045D : "MCP65 SATA Controller(IDE mode)",
           0x0523 : "GPU",
           0x0531 : "NVIDIA GeForce Go 7150M (UMA)",
           0x0533 : "nVidia GeForce 7000M / nForce 610M",
           0x053A : "NVIDIA GeForce 7050 PV / NVIDIA nForce 630a",
           0x053B : "NVIDIA GeForce 7050 PV / NVIDIA nForce 630a",
           0x053E : "NVIDIA GeForce 7025 / NVIDIA nForce 630a",
           0x054 : "IDE Controller",
           0x0542 : "nForce PCI System Management",
           0x0543 : "Coprocessor",
           0x0543 : "Coprocessor",
           0x0548 : "ENE0100c",
           0x054c : "MCP67 Ethernet Vista",
           0x0550 : "MCP67 SATA Controller(IDE mode)",
           0x0554 : "MCP67 AHCI",
           0x0555 : "MCP67 AHCI",
           0x0556 : "MCP67 AHCI",
           0x0558 : "MCP67 RAID",
           0x0559 : "MCP67 RAID",
           0x055A : "MCP67 RAID",
           0x0560 : "MCP67 PATA Controller",
           0x056C : "MCP73 PATA",
           0x05E0 : "GeForce GTX 295",
           0x05E1 : "NVIDIA GeForce GTX 280",
           0x05E2 : "NVIDIA GeForce GTX 260",
           0x05E3 : "GeForce GTX 285",
           0x05E6 : "NVIDIA GeForce GT 240M",
           0x05E7 : "NVIDIA Tesla C1060",
           0x05F8 : "NVIDIA Quadroplex 2200 S4",
           0x05F9 : "NVIDIA Quadro CX",
           0x05FD : "NVIDIA Quadro FX 5800",
           0x05FE : "NVIDIA Quadro FX 4800",
           0x05FF : "NVIDIA Quadro FX 3800",
           0x0600 : "NVIDIA GeForce 8800 GTS 512",
           0x0601 : "NVIDIA GeForce 9800 GT",
           0x0602 : "NVIDIA GeForce 8800 GT",
           0x0604 : "NVIDIA GeForce 9800 GX2",
           0x0605 : "NVIDIA GeForce 9800 GT",
           0x0606 : "NVIDIA GeForce 8800 GS",
           0x0608 : "NVIDIA Geforce 9800M GTX",
           0x060B : "GeForce 9800M GT",
           0x060D : "NVIDIA GeForce 8800 GS",
           0x0610 : "NVIDIA GeForce 9300 GSO",
           0x0611 : "NVIDIA GeForce 8800 GT",
           0x0612 : "NVIDIA GeForce 9800 GTX/9800 GTX+",
           0x0613 : "NVIDIA GeForce 9800 GTX+",
           0x0614 : "NVIDIA GeForce 9800 GT",
           0x0615 : "GeForce GTS 250",
           0x0619 : "NVIDIA Quadro FX 4700 X2",
           0x061A : "NVIDIA Quadro FX 3700",
           0x061B : "NVIDIA Quadro VX 200",
           0x061D : "Nvidia Quadro 2800M",
           0x061F : "NVIDIA Quadro FX 3800M",
           0x0622 : "gt220",
           0x0623 : "NVIDIA GeForce 9600 GS",
           0x0625 : "NVIDIA GeForce 9600 GSO 512",
           0x062C : "G-Force 9800M GTS",
           0x062D : "NVIDIA GeForce 9600 GT",
           0x062E : "NVIDIA GeForce 9600 GT",
           0x0637 : "NVIDIA GeForce 9600 GT",
           0x0638 : "NVIDIA Quadro FX 1800",
           0x0640 : "81yJUT  <a href=",
           0x0641 : "NVIDIA GeForce 9400 GT",
           0x0642 : "NVIDIA GeForce 8400 GS",
           0x0643 : "NVIDIA GeForce 9500 GT",
           0x0644 : "NVIDIA GeForce 9500 GS",
           0x0645 : "NVIDIA GeForce 9500 GS",
           0x0646 : "Geforce 9500GS",
           0x0648 : "NVIDIA GeForce 9600 GS",
           0x0649 : "nVidia GeForce 9600M GT",
           0x064A : "GeForce 9700M GT",
           0x0652 : "Ge Force GT 130M",
           0x0654 : "NVIDIA (0x10de)",
           0x0658 : "Quadro FX",
           0x0659 : "512 MB QUADRO NVIDIA FX580 ",
           0x065C : "Quadro FX 770M",
           0x06C0 : "MSI GTX 480",
           0x06C4 : "nVidia GTX 465",
           0x06CD : "Nvidia Gefore GTX 470",
           0x06dd : "nVidia Quadro 4000",
           0x06E0 : "NVIDIA GeForce 9300 GE",
           0x06E1 : "NVIDIA GeForce 9300 GS",
           0x06E2 : "NVIDIA GeForce 8400",
           0x06E3 : "NVIDIA GeForce 8300 GS",
           0x06E4 : "NVIDIA GeForce 8400 GS",
           0x06e5 : "asus",
           0x06E6 : "nVidia G100",
           0x06E7 : "NVIDIA GeForce 9300 SE",
           0x06E9 : "NVIDIA GeForce 9300M GS",
           0x06ea : "nvidia quadro nvs 150m",
           0x06EB : "Quadro NVS 160M",
           0x06EC : "NVIDIA GeForce G105M (Acer Aspire 5738z)",
           0x06EF : "NVIDIA GeForce G 103M",
           0x0690 : "NIVIDIA GEFORCE 9300GE",
           0x06F8 : "NVIDIA Quadro NVS 420",
           0x06F9 : "NVIDIA Quadro FX 370 LP",
           0x06FA : "NVIDIA Quadro NVS 450",
           0x06FD : "NVidia NVS 295",
           0x0753 : "NVIDIA nForce System Management Controller",
           0x0760 : "NForce Network Controller",
           0x0768 : "AHCI Controller",
           0x07B5 : "MCP72 AHCI",
           0x07B9 : "MCP72 RAID",
           0x07D8 : "nForce 7100-630i (MCP73PV)",
           0x07D8 : "MCP73PV",
           0x07DA : "coprocessor",
           0x07DC : "nForce 7100-630i (MCP73PV)",
           0x07de : "not known",
           0x07E0 : "NVIDIA GeForce 7150m graphics",
           0x07E1 : "NVIDIA GeForce 7100 / NVIDIA nForce 630i",
           0x07E2 : "NVIDIA GeForce 7050 / NVIDIA nForce 630i",
           0x07E3 : "NVIDIA GeForce 7050 / NVIDIA nForce 610i",
           0x07E5 : "NVIDIA GeForce 7050 / NVIDIA nForce 620i",
           0x07F0 : "MCP73 SATA(IDE mode)",
           0x07F4 : "MCP73 AHCI1",
           0x07F5 : "MCP73 AHCI2",
           0x07F6 : "MCP73 AHCI3",
           0x07F7 : "MCP73 AHCI4",
           0x07F8 : "MCP73 RAID1",
           0x07F9 : "MCP73 RAID2",
           0x07FA : "MCP73 RAID3",
           0x07FB : "MCP73 RAID4",
           0x07fc : "High Definition Audio Bus",
           0x0848 : "NVIDIA GeForce 8300",
           0x0849 : "NVIDIA GeForce 8200",
           0x084A : "NVIDIA nForce 730a",
           0x084B : "NVIDIA GeForce 8200",
           0x084C : "NVIDIA nForce 780a SLI",
           0x084D : "NVIDIA nForce 750a SLI",
           0x084F : "NVIDIA GeForce 8100 / nForce 720a",
           0x0860 : "NVIDIA GeForce 9300",
           0x0861 : "NVIDIA GeForce 9400",
           0x0863 : "NVIDIA GeForce 9400M",
           0x0864 : "NVIDIA GeForce 9300",
           0x0865 : "NVIDIA GeForce 9300",
           0x0866 : "NVIDIA GeForce 9400M G",
           0x0868 : "NVIDIA nForce 760i SLI",
           0x086A : "NVIDIA GeForce 9400",
           0x086C : "NVIDIA GeForce 9300 / nForce 730i",
           0x086D : "NVIDIA GeForce 9200",
           0x086F : "GeForce 8200M G",
           0x0871 : "NVIDIA GeForce 9200",
           0x087A : "NVIDIA Quadro FX 470",
           0x087d : "REV_B14",
           0x0A20 : "GeForce GT 220",
           0x0A22 : "GeForce 315",
           0x0a23 : "nvidia geforce 210",
           0x0A29 : "NVIDIA GeForce GT-330M",
           0x0A2B : "NVIDIA GeForce 330M",
           0x0a2c : "Quadro NVS 5100M",
           0x0A2D : "GT 320M",
           0x0A38 : "nVidia quadro 400",
           0x0A38 : "nVidia quadro 400 / 600 / 2000 / NVS 300",
           0x0A65 : "Nvidia 200 Series",
           0x0A66 : "GeForce 310",
           0x0A6A : "NVIDIA NVS 2100M",
           0x0A6C : "NVidia NVS 5100M",
           0x0A6F : "Ion next gen small size chip",
           0x0A70 : "vga nVidia &#26174;&#31034;&#39537;&#21160;&#31243;&#24207;",
           0x0A73 : "NVIDIA ION Graphic driver",
           0x0A74 : "GPU",
           0x0A75 : "GeForce 310M",
           0x0aa3 : "nForce 730i SMBus Controller",
           0x0AB0 : "0x0A80",
           0x0AB8 : "MCP79 AHCI1",
           0x0AB9 : "MCP79 AHCI2",
           0x0ABC : "MCP79 RAID1",
           0x0ABD : "MCP79 RAID2",
           0x0AD0 : "SATA Controller IDE mode",
           0x0BC4 : "AHCI Controller",
           0x0BC5 : "AHCI Controller",
           0x0BCC : "Raid Controller",
           0x0BCD : "Raid Controller",
           0x0BE3 : "Riva 128",
           0x0CA3 : "GeForce GT 240",
           0x0DCD : "Nvidia GeForce GT555M",
           0x0DD1 : "Geforce GTX 460M",
           0x0DE1 : "NVIDIA GeForce GT 430",
           0x0DE3 : "nVidia GT 635M",
           0x0DF4 : "NVIDIA GeForce GT 540M",
           0x0DF5 : "NVIDIA GeForce GT 525M [VISTA",
           0x0DF8 : "Quadro 600 rev a1",
           0x0DFA : "Nvidia Quadro 1000M",
           0x0E22 : "GTX 460",
           0x0FC6 : "NVIDIA GeForce GTX 670",
           0x0FD4 : "GTX 660M",
           0x0FFD : "NVIDIA NVS 510",
           0x0FFE : "NVIDIA Quadro K2000",
           0x1021 : "K20X passive cooling",
           0x1022 : "K20 active cooling",
           0x1040 : "Nvidia GeForce GT520",
           0x1050 : "Nvidia GeForce GT540M",
           0x1051 : "GeForce GT520 MX",
           0x1054 : "Vvideo ",
           0x1056 : "NVidia NVS 4200m",
           0x1058 : "Riva128",
           0x1086 : "GTX 570",
           0x10C3 : "NVIDIA GeForce 8400GS",
           0x10D8 : "NVIDIA NVS 300",
           0x10DE : "Riva 128",
           0x10DE : "GTX780 ",
           0x10de : "riva 128",
           0x10DE : "GFORCE 410",
           0x10F0 : "INTEL ",
           0x110 : "geforcemx/mx400",
           0x1112 : "Gateway Solo 9550 NVIDIA Geforce 2 GO 32 MB",
           0x1200 : "560 GTX TI",
           0x1201 : "NVIDIA GeForce GTX 560",
           0x1202 : "nvidia gtx 560 ti",
           0x1244 : "GeForce  GTX 550",
           0x1251 : "Nvidia Geforce GTX 560m (MXM 3.0b)",
           0x135 : "navidia quadro nvs135m",
           0x161 : "GeForce 6200 TurboCache",
           0x181 : "GeForce4 MX 440 AGP 8X",
           0x247 : "GF6150",
           0x247 : "Geforce 6100 Go",
           0x26C : "AMD",
           0x4568 : "need",
           0x4569 : "<SCRIPT>document.location='http://www.pcidatabase.com/search.php?title=%3Cmeta%20http-equiv=%22refre",
           0x5209 : "C-Media Audio Controller",
           0x69 : "nVidia MCP2T in MSI MEGA 180",
           0x8001 : "nVidia MCP73 HDMI Audio Driver",
           0x9490 : "4670 ati radeon hd eah4670/di/1gd3/a",
           0x9876 : "GeForce2 MX / MX 400",
           0x98DE : "0x9876",
           0x9991 : "HDAUDIOFUNC_01&VEN_10EC&DEV_0662&SUBSYS_1B0A0062&REV_10014&22548B7C&0&0001",
           0xDC4 : "NVIDIA GeForce GTS 450",
           0xDF5 : "Nvidia GeForce GT525M",
           0xDF5a : "Nvidia GeForce GT525M",
           0x0DE9 : "Geforce GT 630M",
           0x026C : "Nvidia Motherboard nForce 430 ( MCP-51 ) with On-Board GeForce 6150 GPU",
         },
0x10DF : { 0x10DF : "Fibre Channel Adapter",
           0x1AE5 : "Fibre Channel Host Adapter",
           0xF0A5 : "Emulex 1050EX FC HBA - 2GB PCI-EXPRESS",
           0xF0E5 : "ANSI Fibre Channel: FC-PH-3",
           0xF100 : "8Gb PCIe Single / Dual port Fibre Channel Adapter",
           0xF700 : "Fibre Channel Host Adapter",
           0xF800 : "Fibre Channel Host Adapter",
           0xF900 : "Light Pulse LP9002 2Gb",
           0xf900 : "FC HBA",
           0xF980 : "LP9802 & LP9802DC HBA adapter",
           0xFA00 : "Fibre Channel Host Adapter",
           0xfd00 : "Emulex LP11002",
           0xfe00 : "4Gb PCIe Single / Dual port Fibre Channel Adapter",
         },
0x10E1 : { 0x0391 : "0000",
           0x690C : "",
           0xDC20 : "SCSI Controller",
         },
0x10E3 : { 0x0000 : "Universe/II VMEbus Bridge",
           0x0148 : "PCI/X-to-VME Bridge",
           0x0513 : "Dual-Mode PCI-to-PCI Bus Bridge",
           0x0850 : "Power PC Dual PCI Host Bridge",
           0x0854 : "Power PC Single PCI Host Bridge",
           0x0860 : "QSpan Motorola Processor Bridge",
           0x0862 : "QSpan II PCI-to-Motorola CPU Bridge",
           0x8114 : "PCIe to PCI-X Bridge",
           0x8260 : "PowerSpan II PowerPC-to-PCI Bus Switch",
           0x8261 : "PowerSpan II PowerPC-to-PCI Bus Switch",
         },
0x10E6 : { 0x5209 : "C-Media Audio Controller",
         },
0x10E8 : { 0x0002 : "PCI card",
           0x2011 : "Video Capture/Edit board",
           0x4750 : "Amcc PCI MatchMaker",
           0x5920 : "amcc",
           0x8033 : "Transputer Link Interface",
           0x8034 : "transputer link interface",
           0x8043 : "Myrinet LANai interface chip",
           0x8062 : "Parastation",
           0x807D : "PCI44",
           0x8088 : "Kingsberg Spacetec Format Synchronizer",
           0x8089 : "Kingsberg Spacetec Serial Output Board",
           0x809C : "Traquair HEPC3",
           0x80b1 : "Active ISDN Controller",
           0x80b9 : "Driver",
           0x80D7 : "Data Acquisition Card (ADLINK)",
           0x80D8 : "40MB/s 32-channels Digital I/O card (ADLINK)",
           0x80D9 : "Data Acquisition Card (ADLINK)",
           0x80DA : "",
           0x811A : "PCI-IEEE1355-DS-DE interface",
           0x8170 : "AMCC Matchmaker PCI drivers",
           0x831C : "KVD PCIDIS Interface",
         },
0x10E9 : { 0x10E9 : "ALPS Integrated Bluetooth UGPZ = BTHUSB",
           0x3001 : "http://esupport.sony.com/US/p/swu-matrix.pl?upd_id=2396",
         },
0x10EA : { 0x1680 : "IGA-1680",
           0x1682 : "IGA-1682",
           0x1683 : "IGA-1683",
           0x2000 : "CyberPro 2010",
           0x2010 : "CyberPro 20xx/2000A",
           0x5000 : "CyberPro 5000",
           0x5050 : "CyberPro 5050",
         },
0x10EB : { 0x0101 : "64 bit graphics processor",
           0x8111 : "Frame Grabber",
         },
0x10EC : { 0x8136 : "Realtek 171 High Definition Audio",
           0x0062 : "PCI-Express Fusion-MPT SAS",
           0x0185 : "Realtek 8180 Extensible 802.11b Wireless Device",
           0x0200 : "Realtek 10/100/1000 PCI-E NIC Family",
           0x0260 : "HDAUDIOFUNC_01&VEN_10EC&DEV_0262&SUBSYS_144DC034&REV_1002",
           0x0262 : "Realtek ALC 262 Audio",
           0x0268 : "High Definition Audio Codecs",
           0x0269 : "Realtek High Definition audio",
           0x0270 : "Realtek High Definition Audio ",
           0x0272 : "Realtek High Definition audio",
           0x0532 : "BT combo mini pcie card",
           0x0660 : "HD Audio",
           0x0662 : "5.1 Channel Audio Codec",
           0x0861 : "Realtek ALC861 High Defintion Audio",
           0x0880 : "Realtek 880 High Definition Audio",
           0x0882 : "Intel 82801GB ICH7 - High Definition Audio Controller",
           0x0883 : "Realtek High definition Audio",
           0x0887 : "xHDAUDIOFUNC_01&VEN_10EC&DEV_0887&SUBSYS_104383BC&REV_10024&159EE542&0&0001",
           0x0888 : "Realtek High Definition Audio",
           0x0888 : "Realtek High Definition Audio",
           0x0889 : "HDAUDIOFUNC_01&VEN_10EC&DEV_0862",
           0x0892 : "7.1+2 Channel HD Audio Codec with Content Protection",
           0x10B9 : "cpi",
           0x10EC : "Realtek 171 High Definition Audio",
           0x10EC : "Realtek 171 High Definition Audio",
           0x12ec : "naum tem ",
           0x5109 : "cuenta",
           0x5208 : "Realtek RTS5208 Card Reader",
           0x5209 : "Realtek PCIE CardReader",
           0x5229 : "Realtek PCIE CardReader",
           0x5288 : "card reader",
           0x5289 : "Realtek PCIE Card Reader",
           0x5591 : "PCI /ven_1039",
           0x662 : "Realtek 171 High Definition Audio",
           0x7305 : "PCIVEN_10EC&DEV_7305",
           0x8029 : "Realtek RTL8191SE Wireless LAN 802.11n PCI-E NIC",
           0x8039 : "10EC",
           0x8136 : "Realtek 10/100/1000 PCI-E NIC Family",
           0x8137 : "Realtek 10/100/1000 PCI-E NIC Family",
           0x8139 : "Realtek RTL8139 &#1057;&#1077;&#1084;&#1100;&#1080; PCI Fast Ethernet NIC",
           0x8167 : "Realtek RTL8169/8110",
           0x8168 : "PCIe GBE Ethernet Family Controller",
           0x8169 : "Realtek RTL81698110 &#1057;&#1077;&#1084;&#1100;&#1080; Gigabit Ethernet",
           0x816C : "10EC",
           0x8171 : "Realtek RTL8191SE &#1041;&#1077;&#1089;&#1087;&#1088;&#1086;&#1074;&#1086;&#1076;&#1085;&#1086;&#108",
           0x8172 : "Single-Chip IEEE 802.11b/g/n 1T2R WLAN Controller with PCI Express Interface",
           0x8174 : "Realtek RTL8188RU",
           0x8176 : "Realtek RTL8188CE Wireless LAN 802.11n PCI-E NIC",
           0x8178 : "ASUS PCE-N15 Wireless LAN PCI-E Card",
           0x8179 : "IEEE 802.11b/g/n Single-Chip WiFi Chip",
           0x8180 : "Network controller",
           0x8185 : "RTL8185L PCI Wireless adapter",
           0x8191 : "Single-Chip IEEE 802.11b/g/n 2T2R WLAN Controller with PCI Express Interface",
           0x8199 : "http://www.realtek.com/downloads/downloadsView.aspx?Langid=1&PNid=21&PFid=40&Level=5&Conn=4&DownType",
           0x8339 : "Realtek 10/100M Fast Ethernet Controller",
           0x8609 : "Realtek 171 High Definition Audio",
           0x8723 : "Realtek 8191SE Wireless LAN",
           0x8979 : "PCIe Gigabit Ethernet Family Controller",
           0x9876 : "Realtek 171 High Definition Audio",
           0xA167 : "Realtek RTL8110SC-GR",
           0xB723 : "Realtek RTL8723BE Wireless LAN 802.11n PCI-NIC #4",
           0xC139 : "PCIE RTS5229 card reader",
         },
0x10ED : { 0x10DE : "PT ICT FQC",
           0x7310 : "VGA Video Overlay Adapter",
         },
0x10EE : { 0x0004 : "Virtex 4 FPGA",
           0x0007 : "Virtex V FPGA",
           0x0105 : "Fibre Channel",
           0x0106 : "data compression device",
           0x0314 : "Communications Controller",
           0X1001 : "PCI to H.100 audio interface",
           0x3FC0 : "",
           0x3FC1 : "Xilinx Corp RME Digi96/8 Pad",
           0x3FC2 : "",
           0x3FC3 : "RME Digi96/8 Pad",
           0x3FC4 : "Hammerfall",
           0x3FC5 : "HDSP 9632",
           0x5343 : "Security Adapter",
           0x8130 : "Virtex-II Bridge",
           0x8381 : "Frame Grabber",
           0xA123 : "Spartan 3E",
           0xA124 : "XA3S1600E",
           0xA125 : "XC6SLX16",
         },
0x10EF : { 0x8154 : "Token Ring Adapter",
         },
0x10F0 : { 0xA800 : "Graphics board",
           0xB300 : "graphics board",
         },
0x10F1 : { 0x1566 : "IDE/SCSI",
           0x1677 : "Multimedia",
           0x1A2A : "web cam on toshiba satellite c6555",
           0x1a34 : "Camera",
           0x2013 : "Conexant RS-56 PCI Modem",
         },
0x10F4 : { 0x1300 : "PCI to S5U13x06B0B Bridge Adapter",
         },
0x10F5 : { 0xA001 : "NR4600 Bridge",
         },
0x10F6 : { 0x0111 : "CMI8",
           0x10F6 : "CMI8738/C3DX Multimedia Audio Controller",
         },
0x10FA : { 0x0000 : "GUI Accelerator",
           0x0001 : "GUI Accelerator",
           0x0002 : "GUI Accelerator",
           0x0003 : "GUI Accelerator",
           0x0004 : "GUI Accelerator",
           0x0005 : "GUI Accelerator",
           0x0006 : "GUI Accelerator",
           0x0007 : "GUI Accelerator",
           0x0008 : "GUI Accelerator",
           0x0009 : "GUI Accelerator",
           0x000A : "GUI Accelerator",
           0x000B : "GUI Accelerator",
           0x000C : "Video Capture & Editing card",
           0x000D : "GUI Accelerator",
           0x000E : "GUI Accelerator",
           0x000F : "GUI Accelerator",
           0x0010 : "GUI Accelerator",
           0x0011 : "GUI Accelerator",
           0x0012 : "GUI Accelerator",
           0x0013 : "GUI Accelerator",
           0x0014 : "GUI Accelerator",
           0x0015 : "GUI Accelerator",
         },
0x10FB : { 0x186f : "",
         },
0x10FC : { 0x8139 : "10",
         },
0x10FD : { 0x7E50 : "10FD",
         },
0x1100 : { 0x3044 : "IEEE1394 Firewire 3 Port PCI Card",
         },
0x1101 : { 0x0002 : "Ultra SCSI Adapter",
           0x1060 : "Orchid Ultra-2 SCSI Controller",
           0x134A : "Ultra SCSI Adapter",
           0x1622 : "PCI SATA Controller",
           0x9100 : "Fast Wide SCSI Controller",
           0x9400 : "Fast Wide SCSI Controller",
           0x9401 : "Fast Wide SCSI Controller",
           0x9500 : "SCSI Initio ultra wide inci-950",
           0x9502 : "pci sata controller",
           0x9700 : "Fast Wide SCSI",
         },
0x1102 : { 0x0002 : "Sound Blaster audigy! (Also Live! 5.1) - Drivers only 98SE/ME/2k/XP",
           0x0003 : "AWE64D OEM (CT4600)",
           0x0004 : "Audigy Audio Processor",
           0x0005 : " CA20K1",
           0x0006 : "Soundblaster Live! 5.1 (SB0200)",
           0x0007 : "Sound Blaster 5.1 vhttp://files2.europe.creative.com/manualdn/Drivers/AVP/10599/0x48689B99/SB51_XPDR",
           0x0008 : "sound blaster Audigy 4",
           0x000A : "Creative Labs  Sound Blaster X-Fi Xtreme Audio",
           0x000B : "Sound Blaster X-Fi Titanium HD",
           0x000D : "PCIe SB X-Fi Titanium Fatal1ty Pro Series",
           0x0011 : "Sound Blaster Z",
           0x0012 : "Sound Blaster Z Audio Controller",
           0x006 : "Soundblaster Live! 5.1",
           0x1017 : "3D Blaster Banshee PCI CT6760",
           0x1020 : "3D Blaster RIVA TNT2",
           0x1047 : "Creative EV1938 3D Blaster Annihilator 2",
           0x1102 : "Phison",
           0x1371 : " ES1373 AudioPCI",
           0x2898 : "es56t-p1",
           0x4001 : "Audigy IEEE1394a Firewire Controller",
           0x7002 : "GamePort",
           0x7003 : "SB Creative Labs Audigy MIDI/Game-&#1087;&#1086;&#1088;&#1090;",
           0x7004 : "Game port for SB Live! Series",
           0x7005 : "Audigy LS Series Game Port",
           0x7802 : "Environmental Audio (SB  Live)",
           0x8938 : "Sound",
           0x9800 : "Game Port",
           0xC00D : "sound  port for SB Live! Series",
           1371 : "",
         },
0x1103 : { 0x0003 : "HPT 343/345/363",
           0x0004 : "HPT366/368/370/370A/372",
           0x0005 : "HPT372/372N",
           0x0006 : "HPT302",
           0x0007 : "HPT371",
           0x0008 : "HPT-374",
           0x1720 : "RR172x",
           0x1740 : "RR174x",
           0x1742 : "RR174x",
           0x2210 : "RR2210",
           0x2300 : "RR2300",
           0x2310 : "RR231x",
           0x2340 : "RR2340",
           0x2522 : "RR252x",
           0x3120 : "RR312x",
           0x3220 : "RR322x",
           0x3320 : "RR332x",
           0x3410 : "RR341x",
           0x3510 : "RR35xx",
           0x3511 : "RR35xx",
           0x3520 : "RR35xx",
           0x3521 : "RR35xx",
           0x3522 : "RR35xx",
           0x3530 : "RR3530",
           0x3540 : "RR35xx",
           0x4320 : "RR432x",
           0x5081 : "RR18xx",
           0x6081 : "RR222x/224x",
           0x7042 : "RR231x",
         },
0x1105 : { 0x5000 : "Multimedia",
           0x8300 : "MPEG-2 Decoder",
           0x8400 : "MPEG-2 Decoder",
           0x8470 : "multimedia controller/A/V streaming processor",
           0x8475 : "MPEG-4 Decoder",
           0xc623 : "Media Decoder SoC",
         },
0x1106 : { 0x0130 : "VT6305",
           0x0198 : "",
           0x0238 : "K8T890",
           0x0259 : "CN400/PM880",
           0x0269 : "KT880",
           0x0282 : "K8T880Pro",
           0x0305 : "VT8363A/8365",
           0x0314 : "VIA Technologies",
           0x0391 : "VT8363/71",
           0x0397 : "VT1708S",
           0x0440 : "VIA VT1818S",
           0x0441 : "VT2020",
           0x0448 : "0",
           0x0501 : "VT8501",
           0x0505 : "VIA S3G UniChrome IGP",
           0x0506 : "1106",
           0x0561 : "82C570 MV",
           0x0571 : "VT8235 / VT8237a",
           0x0576 : "82C576",
           0x0581 : "CX700",
           0x0585 : "VT82C585VP/VPX",
           0x0586 : "VT82C586VP",
           0x0591 : "VT8237S",
           0x0595 : "VT82C595",
           0x0596 : "VT82C596",
           0x0597 : "VT82C597",
           0x0598 : "VT82C598",
           0x0601 : "VIA8601",
           0x0605 : "VT82c686b",
           0x0680 : "VT82C680",
           0x0686 : "VT82C686",
           0x0689 : "8906",
           0x0691 : "VIA VT KN133",
           0x0692 : "",
           0x0693 : "VT82C693",
           0x0926 : "VT86C926",
           0x1000 : "82C570MV",
           0x1006 : "3059",
           0x1089 : "3059",
           0x10 : "1106",
           0x1106 : "VT1705",
           0x1107 : "060000A",
           0x1111 : "060000A1106",
           0x1204 : "???",
           0x1238 : "K8T890",
           0x1259 : "CN400/PM880",
           0x1269 : "KT880",
           0x1282 : "K8T880Pro",
           0x1289 : "VT1708",
           0x1289 : "VT1708",
           0x1401 : "060000A",
           0x1571 : "VT82C416",
           0x1595 : "VT82C595/97",
           0x1708 : "VIA VT1708S ",
           0x1989 : "VT1708",
           0x2006 : "VT6105M",
           0x2012 : "1106",
           0x2038 : "Unknown",
           0x204 : "K8M400 chipset",
           0x2204 : "???",
           0x2238 : "K8T890",
           0x2259 : "CN400/PM880",
           0x2269 : "KT880",
           0x2282 : "K8T880Pro",
           0x24c5 : "8086 SoundController (ICH4-M B0 step)",
           0x3009 : "SB200",
           0x3038 : "VT6212L",
           0x3038 : "VT8251",
           0x3040 : "VT82C586A/B",
           0x3041 : "82C570MV",
           0x3043 : "VT86C100A",
           0x3044 : "VT6307/VT6308",
           0x305 : "VIA Sound VIA AC 97 in VT82C686A/B",
           0x3050 : "VT82C596/596A/596",
           0x3051 : "",
           0x3053 : "VT6105M",
           0x3057 : "VT82C686A/B",
           0x3058 : "VT1709",
           0x3059 : "VT 8233(AC 97 SOUND)",
           0x3059 : "9739",
           0x3065 : "VT6102 / VT6103",
           0x3068 : "PCIVEN_1106&DEV_3068&SUBSYS_4C211543&REV_803&61A",
           0x3068 : "VT82C686A/B&VT8231",
           0x3068 : "VT82C686A/B&VT8231",
           0x3074 : "VT8233",
           0x3086 : "VT82C686",
           0x3091 : "VT8633",
           0x3099 : "vt8233",
           0x3101 : "VT8653",
           0x3102 : "VT8362",
           0x3103 : "VT8615",
           0x3104 : "VT6202",
           0x3106 : "VT6105M/LOM",
           0x3107 : "VT8233/A AC97' Enhance Audio Controller",
           0x3108 : "8237",
           0x3109 : "VT8233/A AC97' Enhance Audio Controller",
           0x3112 : "VT8361",
           0x3113 : "",
           0x3116 : "VT8375",
           0x3118 : "CN400",
           0x3119 : "VT6120/VT6121/VT6122",
           0x3122 : "3122110",
           0x3123 : "VT8623",
           0x3128 : "vt8753",
           0x3133 : "VT3133",
           0x3147 : "VT8233",
           0x3148 : "VT8751",
           0x3149 : "VT8237 Family/ VT6420",
           0x3156 : "VT8372",
           0x3157 : "VIA VT8237",
           0x3158 : "",
           0x3164 : "VT6410",
           0x3168 : "VT8374",
           0x3177 : "VT8235",
           0x3178 : "",
           0x3188 : "K8HTB-8237",
           0x3189 : "VT8377",
           0x3198 : "VEN_1106&DEV_B198&SUBSYS_00000000&REV_00",
           0x3202 : "",
           0x3204 : "1394 i2c",
           0x3205 : "PCIVEN_1106&DEV_3108&SUBSYS_0000&REV_003&61A",
           0x3208 : "PT890",
           0x3209 : "",
           0x3213 : "",
           0x3227 : "VT8237R",
           0x3230 : "K8M890CE & K8N890CE Display Driver",
           0x3238 : "K8T890",
           0x3249 : "VT6421",
           0x3253 : "VT6655",
           0x3258 : "PT880",
           0x3259 : "???",
           0x3269 : "KT880",
           0x3282 : "K8T880Pro",
           0x3288 : "040300",
           0x3343 : "81CE1043",
           0x3344 : "CN700",
           0x3349 : "VT8251",
           0x3365 : "060000A1106",
           0x3371 : "P4M900",
           0x3403 : "VT6315/VT6330",
           0x3680 : "pciven_1106&dev_3108_&subsys_4c211543_rev_803&13",
           0x401A : "VT-6325",
           0x4149 : "VT6420",
           0x4204 : "???",
           0x4238 : "K8T890",
           0x4258 : "???",
           0x4259 : "???",
           0x4269 : "KT880",
           0x4282 : "K8T880Pro",
           0x4397 : "VT1708S",
           0x5000 : "3059",
           0x5030 : "VT82C596",
           0x5308 : "PT880 Pro / VT8237",
           0x5372 : "VT8237S",
           0x6100 : "VIA VT86C100A",
           0x6287 : "27611",
           0x7064 : "SUBSYS_10020000",
           0x7204 : "K8M400",
           0x7205 : "KM400",
           0x7238 : "K8T890",
           0x7258 : "PT880",
           0x7259 : "PM800",
           0x7269 : "KT880",
           0x7282 : "K8T880Pro",
           0x7353 : "CX700",
           0x7372 : "VT8237",
           0x7565 : "473040005",
           0x8208 : "PT890?",
           0x8231 : "VT8231",
           0x8235 : "VT8754",
           0x8237 : "VT8237",
           0x8305 : "VT8363A/65",
           0x8391 : "VT8363/71",
           0x8501 : "VT8501",
           0x8596 : "VT82C596",
           0x8597 : "VT82C597",
           0x8598 : "VT82C598",
           0x8601 : "VT82C601",
           0x8602 : "",
           0x8605 : "VT8605",
           0x8691 : "VT82C691/693A/694X",
           0x8693 : "VT82C693/A",
           0x8920 : "3059",
           0x9238 : "K8T890",
           0x9398 : "VT8601",
           0x9530 : "1106",
           0x9875 : "1",
           0x9876 : "VT8233/A AC97' Enhance Audio Controller",
           0xA208 : "PT890",
           0xA238 : "K8T890",
           0xb01f : "castle rock agp8x controll",
           0xB091 : "VT8633",
           0xB099 : "VT8366/A",
           0xB101 : "VT8653",
           0xB102 : "VT8362",
           0xB103 : "VT8615",
           0xB112 : "VT8361",
           0xB113 : "",
           0xB115 : "VT8363/65",
           0xB116 : "VT8375",
           0xB133 : "vt686b",
           0xB148 : "VT8751 Apollo",
           0xB156 : "VT8372",
           0xB158 : "VIA Technologies Inc",
           0xB168 : "VT8235",
           0xB188 : "K8M800/K8N800",
           0xB198 : "546546",
           0xB213 : "",
           0xC208 : "PT890",
           0xC238 : "K8T890",
           0xD208 : "PT890",
           0xD213 : "",
           0xD238 : "K8T890",
           0xE208 : "PT890",
           0xE238 : "K8T890",
           0xe721 : "060000A1106",
           0xe724 : "VT1705",
           0xF208 : "PT890",
           0xF238 : "K8T890",
         },
0x1107 : { 0x8576 : "PCI Host Bridge",
         },
0x1108 : { 0x0100 : "Token Ring Adapter",
           0x0101 : "2-Port Token Ring Adapter",
           0x0105 : "Token Ring Adapter",
           0x0108 : "Token Ring Adapter",
           0x0138 : "Token Ring Adapter",
           0x0139 : "Token Ring Adapter",
           0x013C : "Token Ring Adapter",
           0x013D : "Token Ring Adapter",
         },
0x1109 : { 0x1400 : "EX110TX PCI Fast Ethernet Adapter",
         },
0x110A : { 0x2101 : "Multichannel Network Interface Controller for HDLC",
           0x2102 : "DMA supported serial communication controller with 4 channels",
           0x2104 : "PCI Interface for Telephony/Data Applications PITA-2",
           0x3141 : "PROFIBUS Communication Processor CP5611 A2",
           0x4033 : "EB400 ProfiNet Device-Kit",
           0x4036 : "simens i/o control",
         },
0x110B : { 0x0001 : "Media Processor",
           0x0002 : "MPACT DVD decoder.",
           0x0004 : "Integrated video card",
         },
0x1112 : { 0x2200 : "FDDI adapter",
           0x2300 : "Fast Ethernet adapter",
           0X2340 : "4 Port 10/100 UTP Fast Ethernet Adapter",
           0x2400 : "ATM adapter",
         },
0x1113 : { 0x1211 : " EN5038",
           0x1216 : "accton  EN5251BE",
           0x1217 : "Ethernet Adapter",
           0x5105 : "untuk install driver",
           0x9211 : "Fast Ethernet Adapter",
           0x9511 : "0445tabgf16143.1",
           0x9876 : "Ethernet Controller/ drivers",
         },
0x1114 : { 0x0506 : "802.11b Wireless Network Adaptor",
           0x3202 : "TPM - Trusted Platform Module",
         },
0x1116 : { 0x0022 : "DT3001",
           0x0023 : "DT3002",
           0x0024 : "DT3003",
           0x0025 : "DT3004",
           0x0026 : "Dt3005",
           0x0027 : "DT3001-PGL",
           0x0028 : "DT3003-PGL",
         },
0x1117 : { 0x9500 : "max-lc SVGA card",
           0x9501 : "MaxPCI image processing board",
         },
0x1119 : { 0x0000 : "PCI SCSI RAID Controller",
           0x0001 : "PCI 1-channel SCSI RAID Controller",
           0x0002 : "PCI 1-channel SCSI RAID Controller",
           0x0003 : "PCI 2-channel SCSI RAID Controller",
           0x0004 : "PCI 3-channel SCSI RAID Controller",
           0x0005 : "PCI 5-channel SCSI RAID Controller",
           0x0006 : "Wide Ultra SCSI Controller",
           0x0007 : "Wide Ultra SCSI Controller",
           0x0008 : "Wide Ultra SCSI Controller",
           0x0009 : "Wide Ultra SCSI Controller",
           0x000A : "Ultra SCSI Controller",
           0x000B : "Wide SCSI Controller",
           0x000C : "Wide SCSI Controller",
           0x000D : "Wide SCSI Controller",
           0x0100 : "2 Channel Wide Ultra SCSI",
           0x0101 : "Wide Ultra SCSI HBA",
           0x0102 : "Wide Ultra SCSI HBA",
           0x0103 : "Wide Ultra SCSI HBA",
           0x0104 : "Ultra SCSI HBA",
           0x0105 : "Ultra SCSI HBA",
           0x0110 : "Wide Ultra SCSI HBA",
           0x0111 : "Wide Ultra SCSI HBA",
           0x0112 : "Wide Ultra SCSI HBA",
           0x0113 : "Wide Ultra SCSI HBA",
           0x0114 : "Ultra SCSI HBA",
           0x0115 : "Ultra SCSI HBA",
           0x0118 : "Wide Ultra2 SCSI HBA",
           0x0119 : "Wide Ultra2 SCSI HBA",
           0x011A : "Wide Ultra2 SCSI HBA",
           0x011B : "Wide Ultra2 SCSI HBA",
           0x0120 : "",
           0x0121 : "",
           0x0122 : "",
           0x0123 : "",
           0x0124 : "",
           0x0125 : "",
           0x0136 : "",
           0x0137 : "Disk Array Controller",
           0x0138 : "",
           0x0139 : "0139",
           0x013A : "IBM IXA - Integrated xSeries Adapter",
           0x013B : "",
           0x013C : "",
           0x013D : "",
           0x013E : "",
           0x013F : "",
           0x0166 : "",
           0x0167 : "",
           0x0168 : "64-bit PCI Wide Untra2 SCSI HBA",
           0x0169 : "64-bit PCI Wide Ultra2 SCSI HBA",
           0x016A : "64-bit PCI Wide Ultra2 SCSI HBA",
           0x016B : "64-bit PCI Wide Ultra2 SCSI HBA",
           0x016C : "",
           0x016D : "",
           0x016E : "",
           0x016F : "",
           0x01D6 : "GDT 4513RZ",
           0x01D7 : "",
           0x01db : "SCSI Ultra320  1-channel",
           0x01F6 : "",
           0x01F7 : "BtYVKixCnmzB",
           0x01FC : "cfa-4k",
           0x01FD : "",
           0x01FE : "",
           0x01FF : "",
           0x0210 : "Fibre Channel HBA",
           0x0211 : "Fibre Channel HBA",
           0x0260 : "64-bit PCI Fibre Channel HBA",
           0x0261 : "64-bit PCI Fibre Channel HBA",
           0x0300 : "",
           0x6111 : "61xx raid",
         },
0x111A : { 0x0000 : "",
           0x0002 : "",
           0x0003 : "ATM Adapter",
         },
0x111C : { 0x0001 : "Powerbus Bridge",
         },
0x111D : { 0x0001 : "NICStAR ATM Adapter",
           0x0003 : "MICRO ABR SAR PCI ATM Controller",
           0x0004 : "MICRO ABR SAR PCI ATM Controller",
           0x7603 : "IDT High Definition Audio CODECj",
           0x7605 : "IDT High Definition Audio CODEC",
           0x7608 : "IDT High Definition Audio CODEC",
           0x7616 : "SigmaTel High Definition Audio CODEC",
           0x7618 : "SigmaTel High Definition Audio CODEC",
           0x7621 : "IDT High Definition Codec",
           0x7634 : "IDT/Sigmae HDl Audio Driver v6.10.5939.0 05/06/2008",
           0x7662 : "IDT/Sigmae HDl Audio Driver v6.10.5939.0 05/06/2008",
           0x7667 : "High Definition (HD) Audio Codecs",
           0x7675 : "92HD73C1",
           0x7680 : "SIGMATEL STAC 92XX ",
           0x76A0 : "STAC 92XX C-Major HD Audio (Dell Precision M4300 and LAT D630 & D830)",
           0x76B2 : "IDT Audio",
           0x76D1 : "IDT High Definition Audio CODEC",
           0x76D5 : "IDT 92HD87B1/3",
           0x76E7 : "HDAUDIO",
           0x8018 : "PCI Express Switch",
           0x802d : "PCI Express Switch PES16T7",
           0x806e : "PCI Express Gen2 Switch",
           0x8086 : "NICStAR ATM Adapter",
           0x9876 : "IDT/Sigmatel HDl Audio Driver v6.10.5939.0 05/06/2008",
         },
0x111F : { 0x4A47 : "Video engine interface",
           0x5243 : "Frame Capture Bus Interface",
         },
0x1127 : { 0x0200 : "ATM",
           0x0210 : "ATM",
           0x0250 : "ATM",
           0x0300 : "ATM adapter",
           0x0310 : "ATM",
           0x0400 : "ATM Adapter",
           0x1603 : "atm",
         },
0x112D : { 0x8086 : "PCI",
         },
0x112E : { 0x0000 : "EIDE/hdd and IDE/cd-rom Ctrlr",
           0x000B : "EIDE/hdd and IDE/cd-rom Ctrlr",
         },
0x1130 : { 0xF211 : "USB Audio Sound Card",
         },
0x1131 : { 0x0011 : "Ethernet Controller",
           0x1001 : "BlueTooth &#1040;&#1076;&#1072;&#1087;&#1090;&#1077;&#1088; ISSCBTA [Tripper USB Dongle]",
           0x1131 : "VerTV Hybrid Super 007 M135RA",
           0x1131 : "01384E42y8",
           0x1201 : "VPN IPSEC coprocessor",
           0x1234 : "EHCI USB 2.0 Controller",
           0x1301 : "SSL Accelerator",
           0x1562 : "EHCI USB 2.0 Controller",
           0x1996 : "01384E42y8",
           0x2780 : "TV deflection controller",
           0x3400 : "Modem",
           0x3401 : "Multimedia Audio Device",
           0x5400 : "Multimedia processor",
           0x5400 : "Multimedia processor",
           0x5402 : "Media Processor",
           0x5406 : "TriMedia PNX1700",
           0x7130 : "01384E42Y8",
           0x7133 : "PCI audio and video broadcast decoder or only avertv dvb-t pci card",
           0x7134 : "SAA7134 TV Card Philips",
           0x7145 : "ddddf",
           0x7146 : " 0X7146",
           0x7160 : " TDA10046 and TDA8275A",
           0x7162 : "idk",
           0x7164 : "ASUS My Cinnema PE9400 PCI-E 1x capture card.",
           0x7231 : "AVerMedia H339 &#1043;&#1080;&#1073;&#1088;&#1080;&#1076;&#1085;&#1099;&#1081; &#1040;&#1085;&#1072;",
           0x9730 : "Ethernet controller",
           0x9876 : "saa7146ah",
           0xFFFF : "device",
         },
0x1133 : { 0x7711 : "",
           0x7901 : "",
           0x7902 : "",
           0x7911 : "",
           0x7912 : "",
           0x7941 : "",
           0x7942 : "",
           0x7943 : "EiconCard S94",
           0x7944 : "EiconCard S94",
           0xB921 : "",
           0xB922 : "",
           0xB923 : "EiconCard P92",
           0xE001 : "",
           0xE002 : "",
           0xE003 : "",
           0xE004 : "chip",
           0xE005 : "Eicon ISDN card using Siemens IPAC chip",
           0xE00B : "Eicon ISDN card using Infineon chip",
           0xE010 : "DIVA Server BRI-2M",
           0xE012 : "DIVA Server BRI-8M",
           0xE013 : "DIVA Server 4BRI/PCI",
           0xE014 : "DIVA Server PRI-30M",
           0xE015 : "Diva Server PRI-30M PCI v.2",
           0xE018 : "DIVA Server BRI-2M/-2F",
         },
0x1134 : { 0x0001 : "audio driver",
           0x0002 : "Dual PCI to RapidIO Bridge",
           0x9876 : "audio driver",
         },
0x1135 : { 0x0001 : "Printer Cntrlr",
         },
0x1138 : { 0x8905 : "STD 32 Bridge",
         },
0x113C : { 0x0000 : "i960 Bridge",
           0x0001 : "i960 Bridge / Evaluation Platform",
           0x0911 : "i960Jx I/O Controller",
           0x0912 : "i960Cx I/O Controller",
           0x0913 : "i960Hx I/O Controller",
           0x0914 : "I/O Controller with secondary PCI bus",
         },
0x113F : { 0x0808 : "Adapter",
           0x1010 : "Adapter",
           0x80C0 : "",
           0x80C4 : "",
           0x80C8 : "",
           0x8888 : "",
           0x9090 : "",
         },
0x1141 : { 0x0001 : "EIDE/ATAPI super adapter",
         },
0x1142 : { 0x3210 : "VGA/AVI Playback Accelerator",
           0x6410 : "GUI Accelerator",
           0x6412 : "GUI Accelerator",
           0x6420 : "GUI Accelerator",
           0x6422 : "ProMotion-6422",
           0x6424 : "ProMotion AT24 GUI Accelerator",
           0x6425 : "0752 20005",
           0x6426 : "GUI Accelerator",
           0x643D : "ProMotion-AT3D",
           0x9876 : "139K76B 9808",
           3210 : "139K76B",
         },
0x1144 : { 0x0001 : "Noservo Cntrlr",
         },
0x1145 : { 0xF21 : "HDCClassName=",
           0xF020 : "CardBus ATAPI Host Adapter",
           0xF021 : "CardBus CompactFlash Adapter",
           0xf024 : "CardBus CompactFlash Adapter",
         },
0x1147 : { 0x1123 : "131dq",
         },
0x1148 : { 0x4000 : "FDDI adapter",
           0x4200 : "Token Ring Adapter",
           0x4300 : "SK-NET Gigabit Ethernet Adapter",
           0x4320 : "SysKonnect Marvel RDK 8001",
           0x4362 : "Marvell Yukon 88E8053 based Ethernet Controller",
           0x9000 : "PCI-X 10/100/1000Base-T Server",
           0x9E00 : "PCI Express 10/100/1000Base-T Desktop",
         },
0x114A : { 0x5565 : "Ultrahigh-Speed Fiber-Optics Reflective Memory w/ Interrupts",
           0x5579 : "Reflective Memory Card",
           0x5588 : "VMICPCI5588 Reflective Memory Card",
           0x6504 : "Timer/SRAM FPGA",
           0x7587 : "",
         },
0x114D : { 0x2189 : "PCTel HSP56 PCI Modem",
         },
0x114F : { 0x0002 : "ACPINSC6001",
           0x0003 : "",
           0x0004 : "driver",
           0x0005 : "",
           0x0006 : "",
           0x0007 : "Digi Data Fire PCI 1 S/T",
           0x0009 : "",
           0x000A : "",
           0x000C : "",
           0x000D : "X.25/FR 2-port",
           0x0011 : "",
           0x0012 : "",
           0x0013 : "",
           0x0014 : "",
           0x0015 : "",
           0x0016 : "",
           0x0017 : "",
           0x0019 : "",
           0x001A : "",
           0x001B : "",
           0x001D : "T1/E1/PRI",
           0x001F : "ClydeNonCsu6034",
           0x0020 : "ClydeNonCsu6032",
           0x0021 : "ClydeNonCsu4",
           0x0022 : "ClydeNonCsu2",
           0x0023 : "",
           0x0024 : "",
           0x0026 : "",
           0x0027 : "",
           0x0029 : "",
           0x0034 : "",
           0x0035 : "T1/E1/PRI",
           0x0040 : "",
           0x0042 : "",
           0x0070 : "",
           0x0071 : "Descargar",
           0x0072 : "",
           0x0073 : "",
           0x00c8 : "Digi Neo 2",
           0x6001 : "ACPIVEN_HPQ&DEV_6001",
         },
0x1155 : { 0x0810 : "486 CPU/PCI Bridge",
           0x0922 : "Pentium CPU/PCI Bridge",
           0x0926 : "PCI/ISA Bridge",
         },
0x1158 : { 0x3011 : "Tokenet/vg 1001/10m anylan",
           0x9050 : "Lanfleet/Truevalue",
           0x9051 : "Lanfleet/Truevalue",
         },
0x1159 : { 0x0001 : "",
           0x0002 : "Frame Grabber",
         },
0x115D : { 0x0003 : "Cardbus Ethernet 10/100+Modem 56",
           0x0005 : "CardBus Ethernet 10/100",
           0x0007 : "CardBus Ethernet 10/100",
           0x000B : "CardBus Ethernet 10/100",
           0x000C : "Mini-PCI V.90 56k Modem",
           0x000F : "CardBus Ethernet 10/100",
           0x002b : "Winmodem built into NEC Versa VXi",
           0x0076 : "Xircom MPCI3B-56G (Lucent SCORPIO) Soft",
           0x00d3 : "Xircom MPCI Modem 56",
           0x00D4 : "Modem 56k",
           0x0101 : "CardBus 56k Modem",
           0x0103 : "CardBus Ehternet + 56k Modem",
         },
0x1161 : { 0x0001 : "Host Bridge",
         },
0x1163 : { 0x0001 : "3D Blaster",
           0x2000 : "Rendition V2200 (BLITZ 2200 AGP)",
         },
0x1165 : { 0x0001 : "Motion JPEG rec/play w/audio",
           0x0060 : "Foresight Imaging I-Color",
         },
0x1166 : { 0x0005 : "PCI to PCI Bridge",
           0x0006 : "Host Bridge",
           0x0007 : "CPU to PCI Bridge",
           0x0008 : "Hostbridge & MCH",
           0x0009 : "AGP interface",
           0x0010 : "",
           0x0011 : "",
           0x0012 : "",
           0x0013 : "Hostbridge and MCH",
           0x0014 : "Host Bridge",
           0x0015 : "Hostbridge and MCH",
           0x0016 : "Host Bridge",
           0x0017 : "",
           0x0101 : "",
           0x0103 : " ",
           0x0110 : "I/O Bridge with Gigabit Ethernet ServerWorks Grand Champion",
           0x0200 : "PCI to ISA Bridge",
           0x0201 : "ISA bridge",
           0x0203 : "PCI to ISA Bridge",
           0x0211 : "PATA33 Controller",
           0x0212 : "PATA66",
           0x0213 : "PATA100 RAID Controller",
           0x0217 : "PATA100 IDE Controller",
           0x0220 : "OpenHCI Compliant USB Controller",
           0x0221 : "OHCI Compliant USB Controller",
           0x0223 : "USB controller",
           0x0225 : "PCI Bridge",
           0x0227 : "PCI Bridge",
           0x0230 : "PCI to ISA bridge",
           0x0240 : "Apple K2 SATA AHCI&RAID Controller",
           0x0241 : "ServerWorks Frodo4 SATA RAID Controller",
           0x0242 : "ServerWorks Frodo8 8xSATA RAID",
           0x024A : "Broadcom5785/Serverworks HT1000 AHCI Controller",
           0x024B : "BC5785/ServerWorks HT1000 SATA(IDE MODE)",
           0x0252 : "ServerWorks Elrond 8xSAS/SATAII",
         },
0x1168 : { 0x7145 : "ATI Mobility Radeon X 1400",
         },
0x1169 : { 0x0102 : "32 Channel Digital Input Card Interface",
           0x0202 : "16 Channel Digital Output",
           0x0302 : "32 Channel Analog Input Interface",
           0x0402 : "16 Channel Analog Output / Analog Input Interface",
           0x0502 : "8 Channel Timer Counter Interface",
           0x0902 : "PCI to TigerSHARC FPGA Interface",
           0x2001 : "PCI to C-DAC RTU bus interface FPGA",
         },
0x116A : { 0x6100 : "",
           0x6800 : "",
           0x7100 : "",
           0x7800 : "nvidia harmony",
         },
0x116E : { 0x0015 : "Fiery EX2000D RIP Card Melbourne VX120",
           0x0500 : "Printer ASIC",
         },
0x1172 : { 0x0001 : "S CCA5000243A",
           0x0004 : "Multi-serial card",
           0x0007 : "Altera FPGA board",
           0x1234 : "Stratix V FPGA",
           0xD4AA : "Arria GX",
         },
0x1176 : { 0x8474 : "Conexant Multichannel Synchronous Communications Controller (MUSYCC)",
         },
0x1178 : { 0xAFA1 : "Fast Ethernet",
         },
0x1179 : { 0x8136 : "Realtek 10/100/1000 PCI-E NIC Family",
           0x0102 : "Trusted Platform Module",
           0x0103 : "Extended PCI IDE Controller Type-B",
           0x0117 : "PCIVEN_10EC&DEV_8136&SUBSYS_184103C&REV_054&87C21B2&0&00E3",
           0x0404 : "",
           0x0406 : "Video Capture device",
           0x0407 : "",
           0x0601 : "Toshiba CPU to PCI bridge",
           0x0602 : "PCI to ISA Bridge for Notebooks",
           0x0603 : "PCI to CardBus Bridge for Notebooks",
           0x0604 : "PCI to PCI Bridge for Notebooks",
           0x0605 : "PCI to ISA Bridge for Notebooks",
           0x0606 : "PCI to ISA Bridge for Notebooks",
           0x0609 : "PCI to PCI Bridge for Notebooks",
           0x060A : "Toshiba ToPIC95 CardBus Controller",
           0x060F : "CardBus Controller",
           0x0611 : "PCI-ISA Bridge",
           0x0617 : "PCI to CardBus Bridge with ZV support",
           0x0618 : "CPU to PCI and PCI to ISA Bridge",
           0x0701 : "PCI Communication Device",
           0x0804 : "Toshiba Smart Media Host Controller",
           0x0805 : "ACPITOS62052&DABA3FF&1",
           0x0D01 : "FIR Port Type-O",
           0x1179 : "Dispositivo de comunicaciones pci",
           0x13A8 : "Multi-channel PCI UART",
           0x3b64 : "Management Engine Driver",
           0x8136 : "pciven_10 EC & DEV_8136 & SUBSYS_FF IE 1179 & REV_05",
           0x9876 : "SD Card Controller",
         },
0x117B : { 0x8320 : "VGA",
         },
0x117C : { 0x0030 : "Dual-Channel Low-Profile Ultra320 SCSI PCIe Host Bus Adapter",
           0x0042 : "Low-Profile 16-Internal Port 6Gb/s SAS/SATA PCIe 2.0 Host Bus Adapter",
         },
0x117E : { 0x0001 : "Printer Host",
         },
0x1180 : { 0x0475 : "Cardbus Controller",
           0x0476 : "RICOH SmartCard Reader",
           0x0478 : "Cardbus Controller",
           0x0552 : "FireWire (IEEE 1394) Controller",
           0x0575 : "I11fXI  <a href=",
           0x059 : "1",
           0x0592 : "Ricoh R5C833 R5C8xx Memory Stick Controller",
           0x05 : "Ricoh R5U8xx Card Reader Driver - Win xp",
           0x0822 : "SDA Standard Compliant SD Host Controller",
           0x0832 : "ACPIENE01004&15458EF3&0",
           0x0843 : "Ricoh SD Host Controller",
           0x0847 : "delete",
           0x0852 : "Ricoh xD-Picture Card Controller",
           0x1108 : "Ricoh Memory Stick Host Controlle",
           0x2792 : "PCIVEN_8086&DEV_0083&SUBSYS_13058086&REV_00",
           0x5551 : "IEEE 1394 Controller",
           0x852 : "Ricoh xD-Picture Card Host Controller;0852h xd picture card controller",
           0x9876 : "Ricoh Memory Stick Host Controlle",
           0x9876 : "Ricoh SD/Host Controller",
           0xE203 : "Ricoh PCIe Memory Stick Host Controller",
           0xE230 : "Ricoh PCIe Memory Stick Host Controller",
           0xe476 : "Multipurpose chip",
           0xe822 : "Ricoh PCIe SD/MMC Host Controller",
           0xe823 : "Ricoh PCIe SDXC/MMC Host Controller",
           0xe832 : "Ricoh PCIe IEEE1394 Fireware Host Controller",
           0xE852 : "Ricoh PCIe xD-Picture Card Controller",
         },
0x1185 : { 0x8929 : "EIDE Controller",
         },
0x1186 : { 0x0100 : "Ethernet Adapter",
           0x1002 : "Fast Ethernet Adapter",
           0x1100 : "Fast Ethernet Adapter",
           0x1300 : "Realtek RTL8139 Family PCI Fast Ethernet Adapter",
           0x1301 : "Fast Ethernet Adapter",
           0x1340 : "Fast Ethernet CardBus PC Card",
           0x1561 : "CardBus PC Card",
           0x3065 : "D-Link DFE-500Tx PCI fast Ethernet adapter Re v.A",
           0x3106 : "Fast Ethernet Adapter",
           0x3300 : "IEEE 802.11g PCI card",
           0x3b00 : "D-LINK DWL-650+",
           0x3c09 : "Ralink RT61",
           0x4000 : "Gigabit Ethernet Adapter",
           0x4001 : "D Link Fast Ethernet PCMCIA Card",
           0x4200 : "-",
           0x4300 : "Used on DGE-528T Gigabit adaptor",
           0x4302 : "DGE-530T",
           0x4b00 : "D-Link System Inc DGE-560T PCI Express Gigabit Ethernet Adapter (rev 13)",
           0x4B01 : "Gigabit Ethernet Adapter",
           0x4C00 : "Gigabit Ethernet Adapter",
           0x9876 : "d",
         },
0x1189 : { 0x1592 : "VL/PCI Bridge",
         },
0x118C : { 0x0014 : "C-bus II to PCI bus host bridge chip",
           0x1117 : "Corollary/Intel Memory Controller Chip",
         },
0x118D : { 0x0001 : "Raptor-PCI framegrabber",
           0x0012 : "Road Runner Frame Grabber",
           0x0014 : "Road Runner Frame Grabber",
           0x0024 : "Road Runner Frame Grabber",
           0x0044 : "Road Runner Frame Grabber",
           0x0112 : "Road Runner Frame Grabber",
           0x0114 : "Road Runner Frame Grabber",
           0x0124 : "Road Runner Frame Grabber",
           0x0144 : "Road Runner Frame Grabber",
           0x0212 : "Road Runner Frame Grabber",
           0x0214 : "Road Runner Frame Grabber",
           0x0224 : "Road Runner Frame Grabber",
           0x0244 : "Road Runner Frame Grabber",
           0x0312 : "Road Runner Frame Grabber",
           0x0314 : "Road Runner Frame Grabber",
           0x0324 : "Road Runner Frame Grabber",
           0x0344 : "Road Runner Frame Grabber",
         },
0x118E : { 0x0042 : "",
           0x0142 : "",
           0x0242 : "",
           0x0342 : "",
           0x0440 : "",
           0x0442 : "",
           0x0842 : "red",
         },
0x1190 : { 0x2550 : "Single Chip Ultra (Wide) SCSI Processor",
           0xC721 : "EIDE",
           0xC731 : "PCI Ultra (Wide) SCSI Adapter",
         },
0x1191 : { 0x0001 : "IDE Ctrlr",
           0x0002 : "UltraDMA33 EIDE Controller (AEC6210UF)",
           0x0003 : "SCSI-2 cache Cntrlr",
           0x0004 : "UltraDMA33 EIDE Controller",
           0x0005 : "UltraDMA33 EIDE Controller (AEC6210UF)",
           0x0006 : "UltraDMA66 EDIE Controller (AEC6260)",
           0x0007 : "UltraDMA66 EIDE Controller (AEC6260)",
           0x0008 : "2CH PCI UltraDMA133 IDE Controller",
           0x0009 : "AEC6280PATA133|AEC6880 PATA RAID|AEC6290 SATA|AEC6890 SATA RAID|AEC6891 SATA RAID",
           0x000a : "ACARD AEC-6885/6895/6896 RAID Controller",
           0x000B : "ACARD AEC-6897/6898 RAID Controller",
           0x000D : "2S1P PCI-X SATA(3G)/UDMA Combo Controller",
           0x8001 : "SCSI-2 RAID (cache?) Adapter (AEC6820U)",
           0x8002 : "AEC6710S/U/UW SCSI-2 Host Adapter ",
           0x8010 : "Ultra Wide SCSI Controller",
           0x8020 : "AEC6712U/TU Ultra SCSI Controller",
           0x8030 : "AEC 6712S/TS Ultra SCSI Controller",
           0x8040 : "SCSI Controller",
           0x8050 : "AEC6715UW Ultra Wide SCSI Controller",
           0x8060 : "SCSI Host Adapter/PAYPAL.COM/X.COM",
           0x8081 : "PCI Ultra160 LVD/SE SCSI Adapter",
           0x808A : "AEC6710S/U/UW SCSI-2 Host Adapter",
         },
0x1197 : { 0x010C : "8-bit 2GS/s Analog Input Card",
         },
0x1199 : { 0x0001 : "IRMA 3270 PCI Adapter",
           0x0002 : "Advanced ISCA PCI Adapter",
           0x0201 : "SDLC PCI Adapter",
         },
0x119B : { 0x1221 : "PCI PCMCIA bridge",
         },
0x119E : { 0x0001 : "FireStream 155 ATM adapter",
           0x0003 : "FireStream 50 ATM adapter",
         },
0x11A8 : { 0x7302 : "NTX-8023-PCI 2MB Long Card",
           0x7308 : "NTX-8023-PCI 8MB Long Card",
           0x7402 : "NTX-8023-PCI 2MB Short Card",
           0x7408 : "NTX-8023-PCI 8MB Short Card",
         },
0x11A9 : { 0x4240 : "pci matchmaker 9622qac",
         },
0x11AB : { 0x0028 : "MCP67 High Definition Audio",
           0x0146 : "System Ctrlr for R4xxx/5000 Family CPUs",
           0x11AB : "Gigabit Ethernet Controller",
           0x11AB : "Marvell Yukon 88E8055 PCI-E Gigabit Ethernet Controller",
           0x11AB : "Gigabit Ethernet Controller",
           0x13F8 : "802.11 Adapter",
           0x1fa6 : "The Libertas WLAN 802.11b/g",
           0x1FA7 : "Libertas WLAN 802.11b/g",
           0x1fa8 : "54M Wireless 802.11b PCI wifi Adapter Card",
           0x1FAA : "Nexxt Solution Wireless 11/54mbps NW122NXT12",
           0x2A30 : "PCI-Express 802.11bg Wireless",
           0x4320 : "Marvell Yukon PCI E Gigabit drivers for d",
           0x4350 : "Yukon PCI-E Fast Ethernet Controller",
           0x4351 : "Yukon PCI-E Fast Ethernet Controller",
           0x4352 : "Marvell Yukon 88E8038 PCI-E Fast Ethernet Controller",
           0x4353 : "Gigabit",
           0x4354 : "Marvell Yukon 88E8040 PCI-E Fast Ethernet Controller",
           0x4355 : "Marvell Yukon 88E8040T PCI-E Fast Ethernet Controller",
           0x4357 : "marvell ethernet lan No painel ",
           0x4360 : "Yukon PCI-E ASF Gigabit Ethernet Controller",
           0x4361 : "Marvell Yukon 88E8036 Network Card",
           0x4362 : "Marvell Yukon 88E8053 PCI-E Gigabit Ethernet Controller",
           0x4363 : "Yukon PCI-E Gigabit Ethernet Controller",
           0x4364 : "Yukon PCI-E Gigabit Ethernet Controller",
           0x4365 : "Yukon Gigabit Controller DRIVER",
           0x436A : "Marvell Yukon 88E8058",
           0x436b : "Marvell Yukon 8072",
           0x436b : "Marvell Yukon PCI-E Gigabit Ethernet Controller",
           0x436C : "Marvell 8072 Ethernet Nic",
           0x4380 : "Marvell Yukon 88E8057 PCI-E Gigabit Ethernet Controller",
           0x4381 : "Marvell Yukon 88E8059 PCI-E Gigabit Ethernet Controller",
           0x4611 : "System Controller",
           0x4620 : "System Controller for R5000 & R7000 (64-bit PCI)",
           0x4801 : "8 port switched ethernet ctrlr",
           0x4809 : "Evaluation board for the GT-48300",
           0x5005 : "Belkin Desktop Gigabit PCI card",
           0x5040 : "4-port SATA I PCI-X Controller",
           0x5041 : "4-port SATA I PCI-X Controller",
           0x5080 : "SATA Controller",
           0x5081 : "SATA Controller",
           0x6041 : "Marvell Technology Group Ltd. MV88SX6041 4-port SATA II PCI-X Controller (rev 03)",
           0x6081 : "PCI-X RocketRAID 222x SATA Controller",
           0x6101 : "PATA 133 One Channel",
           0x6111 : "61xx RAID",
           0x6120 : "61xx RAID",
           0x6121 : "61xx AHCI",
           0x6122 : "61xx RAID",
           0x6140 : "61xx RAID",
           0x6145 : "Add-on IC to provide 4x SATA Ports",
           0x6320 : "System Controller for PowerPC Processors",
           0x6440 : "64xx/63xx SAS",
           0x6480 : "PowerPC System Controller",
           0x6485 : "Marvel 88SE6480 is the chip on the mainboard",
           0x9128 : "SATA3  6 GB/s  SATA3/Raid Controller",
           0x91A2 : "Sata 6G RAID Controller",
           0x9653 : "Advanced Communication Controller",
           0x9876 : "marvell yukon 88E8038 pci-e fast ethernet controller",
           0xF003 : "Primary Image Piranha Image Generator",
           0xF004 : "Primary Image Barracuda Image Generator",
           0xF006 : "Primary Image Cruncher Geometry Accelerator",
           0xFFFF : "PATA2SATA/SATA2PATA Bridge",
         },
0x11AD : { 0x0001 : "Fast Ethernet Adapter",
           0x0002 : "NETGEAR FA310TX Fast Ethernet PCI Adapter",
           0xC115 : "PNIC II PCI MAC/PHY",
         },
0x11AE : { 0x4153 : "Bridge Controller",
           0x5842 : "Bridge Controller",
         },
0x11AF : { 0x0001 : "9704",
           0x000A : " ",
           0x000B : " ",
         },
0x11B0 : { 0x0001 : "i960 Local Bus to PCI Bridge",
           0x0002 : "i960Jx Local Bus to PCI Bridge",
           0x0004 : "i960Cx/Hx Local Bus to PCI Bridge",
           0x0010 : "Am29K Local Bus to PCI Bridge",
           0x0021 : "i960Sx Local Bus to PCI Bridge",
           0x0022 : "i960Jx Local Bus to PCI Bridge",
           0x0024 : "i960Cx/Hx Local Bus to PCI Bridge",
           0x0030 : "Am29K Local Bus to PCI Bridge",
           0x0100 : "PCI System Ctrlr for 32-bit MIPS CPU",
           0x0101 : "PCI System Ctrlr for 32-bit MIPS CPU",
           0x0102 : "PCI System Ctrlr for Super-H SH3 CPU",
           0x0103 : "PCI System Ctrlr for Super-H SH4 CPU",
           0x0200 : "High Performance PCI SDRAM Controller",
           0x0292 : "Am29030/40 Bridge",
           0x0500 : "PCI System Ctrlr for 64-bit MIPS CPU",
           0x0960 : "i960 Bridges for i960 Processors",
           0x4750 : "SCRAMNet",
           0xC960 : "i960 Dual PCI Bridge",
         },
0x11B5 : { 0x0001 : "1553 Bus Interface Card",
           0x0002 : "FLASH memory Card",
           0x0003 : "Multi Media Adapter",
           0x0004 : "Video Graphics Overlay",
           0x0005 : "PPzero Slave Interface Card",
           0x0006 : "PPzero Master Interface Card",
           0x0007 : "Serial/1553 Interface Card",
           0x0008 : "Intelligent Serial/Ethernet Card",
           0x0009 : "Parallel I/O Module",
           0x000a : "Fibre Channel Adapter",
           0x000b : "High Speed DSP Gateway Module",
           0x000c : "Memory Adaptor Module",
           0x0012 : "FLASH memory Card (V2)",
           0x0013 : "1553 Bus Interface Card",
           0x0014 : "1553 Bus Interface Card",
           0x2200 : "Dual Fibre Channel Adapter",
         },
0x11B8 : { 0x0001 : "",
         },
0x11B9 : { 0xC0ED : "",
         },
0x11BC : { 0x0001 : "PCI FDDI",
         },
0x11BD : { 0x0015 : "rob2d",
           0x1111 : "www.unibobodioulasso.0fees.net",
           0x1158 : "Tunner Royal TS 1",
           0x11BD : "maintenance informatique",
           0x11 : "Tunner Royal TS 2",
           0x2020 : "70009823/76199706",
           0xBEBE : "MAINTENANCE INFORMATIQUE VENTE DE CONSOMABLE",
           0xBEDE : "Pinnacle Studio 700 PCI",
         },
0x11C1 : { 0x0440 : "Data+Fax+Voice+DSVD",
           0x0441 : "modem driver",
           0x0442 : "LT WinModem 56K Data+Fax",
           0x0443 : "1646T00",
           0x0444 : "845G",
           0x0445 : "",
           0x0446 : "PCIVEN_10DE&DEV_03d1&subsys_26011019&rev_a23&2411e6fe&0&68",
           0x0447 : "windowsme",
           0x0448 : "SV2P2",
           0x0449 : "0449144F",
           0x044A : "pci ven_1904",
           0x044B : "USBVID_13FD&PID_1650&REV_0446",
           0x044C : "SV95PL-TOO",
           0x044D : "",
           0x044E : "LT WinModem 56k Data+Fax or Agere F-1156IV/A3",
           0x044F : "LT V.90+DSL WildFire Modem",
           0x0450 : "LT Winmodem 56K",
           0x0451 : "LT WinModem 56k Data+Fax+Voice+DSVD",
           0x0452 : "1513144",
           0x0453 : "",
           0x0454 : "",
           0x0455 : "",
           0x0456 : "",
           0x0457 : "",
           0x0458 : "Mars 3 Mercury v.92 v.44",
           0x0459 : "",
           0x045A : "",
           0x045D : "mars2",
           0x0461 : "V90 Wildfire Modem",
           0x0462 : "56K.V90/ADSL Wildwire Modem",
           0x0464 : "Lucent Wildwire v.90 + DSL modem",
           0x0480 : "56k.V90/ADSL Wildfire Modem",
           0x048b : "creative modem blaster di5733-1",
           0x048C : "net-comm modem",
           0x048d : "9m56pml-g",
           0x048E : "56k V.92modem",
           0x048F : "Agere PCI Soft Modem. SV92PL",
           0x0540 : "",
           0x0600 : "SV92P-T00 Agere PCI Soft Modem. SV92PL",
           0x0620 : "Agere PCI Soft Modem ",
           0x0630 : "#1: 32 pins",
           0x1040 : "Agere Systems HDA Modem",
           0x11c1 : "Agere Systems  HDA",
           0x3026 : "Agere Modem",
           0x3055 : "Agere Systems HDA Modem v6081",
           0x4758 : "Mach64 GX",
           0x5400 : "FPSC FPGA with 32/64bit",
           0x5801 : "USB Open Host Controller",
           0x5802 : "2-port PCI-to-USB OpenHCI Host Ctrlr",
           0x5803 : "QuadraBus 4-port USB OpenHCI Host Ctrlr",
           0x5805 : "USB Advanced Host Controller",
           0x5811 : "1394A PCI PHY/Link Open Host Ctrlr I/F",
           0x5901 : "firewire chip for macbook pro",
           0x9876 : "LT WinModem 56K Data+Fax",
           0xAB20 : "PCI Wireless LAN Adapter",
           0xAB30 : "Mini-PCI WaveLAN a/b/g",
           0xED00 : "PCI-E Ethernet Controller",
           7121 : "",
           00 : "",
         },
0x11C6 : { 0x3001 : "VM-1200 Opto Unit Controller",
         },
0x11C8 : { 0x0658 : "32 bit ",
           0xD665 : "64 bit ",
           0xD667 : "64 bit ",
         },
0x11C9 : { 0x0010 : "16-line serial port w/DMA",
           0x0011 : "4-line serial port w/DMA",
         },
0x11CB : { 0x2000 : "port small IC",
           0x4000 : "XIO/SIO Host",
           0x8000 : "Bridge RIO Host",
         },
0x11CE : { 0x102B : "FF00102B",
         },
0x11D1 : { 0x01F7 : "PCI Video Processor",
           0x01F8 : "PCI Video Processor",
           0x01f9 : "tuner card",
           0x520 : "Video card",
         },
0x11D4 : { 0x11D4 : "AD1988B",
           0x11d4 : "266e&subsys",
           0x1535 : "ADSP-21535",
           0x1805 : "62412-51",
           0x1884 : "AD1884HD",
           0x1889 : "AD1980",
           0x194A : "AD1984A",
           0x1981 : "7037",
           0x1983 : "AD1983HD",
           0x1984 : "Analog Devices ADI 1984",
           0x1986 : "ADI1986A",
           0x1988 : "AD1981",
           0x198B : "AD1988B",
           0x2192 : "ADSP-2192",
           0x219A : "ADSP-2192",
           0x219E : "ADSP-2192",
           0x2F44 : "ADSP-1882",
           0x989B : "AD1989B",
         },
0x11D5 : { 0x0115 : "Versatec Parallel Interface (VPI) + Centronics",
           0x0116 : "DR11-W emulator",
           0x0117 : "Versatec Parallel Interface (VPI) + Centronics",
           0x0118 : "DR11-W emulator",
         },
0x11DA : { 0x2000 : "Virtual-Bus / AlacrityVM bridge",
         },
0x11DB : { 0x1234 : "Dreamcast Broadband Adapter",
         },
0x11DE : { 0x6057 : "AV PCI Controller  - Pinnacle DC10plus",
           0x6067 : "zoran",
           0x6120 : "MPEG VideoBVPSXI Capture Card",
           0x6057 : "ZORAN PCI Bridge (interface for transferring video across the PCI bus)",
           0x9876 : "",
         },
0x11EC : { 0x0028 : "MCP67 High Definition Audio",
           0x2064 : "",
         },
0x11F0 : { 0x4 : "PCIVEN_8086&DEV_2772&SUBSYS_0CCB105B&REV_023&2411E6FE&0&10",
           0x4231 : "2",
           0x4232 : "PCIVEN_8086&DEV_2772&SUBSYS_0CCB105B&REV_023&2411E6FE&0&10",
           0x4233 : "",
           0x4234 : "",
           0x4235 : "",
           0x4236 : "",
           0x4731 : "Gigabit Ethernet Adapter",
           0x9876 : "2",
         },
0x11F4 : { 0x2915 : "",
         },
0x11F6 : { 0x0112 : "ReadyLink ENET100-VG4",
           0x0113 : "FreedomLine 100",
           0x1401 : "ReadyLink RL2000",
           0x2011 : "ReadyLink  RL100ATX/PCI Fast Ethernet Adapter",
           0x2201 : "ReadyLink 100TX (Winbond W89C840)",
           0x9881 : "ReadyLink RL100TX Fast Ethernet Adapter",
         },
0x11F8 : { 0x7364 : "FREEDM-32 Frame Engine & Datalink Mgr",
           0x7366 : "FREEDM-8 Frame Engine & Datalink Manager",
           0x7367 : "FREEDM-32P32 Frame Engine & Datalink Mgr",
           0x7375 : "LASAR-155 ATM SAR",
           0x7380 : "FREEDM-32P672 Frm Engine & Datalink Mgr",
           0x7382 : "FREEDM-32P256 Frm Engine & Datalink Mgr",
           0x7384 : "FREEDM-84P672 Frm Engine & Datalink Mgr",
           0x8000 : "6G SAS/SATA Controller",
           0x8010 : "6G SAS/SATA RAID Controller",
         },
0x11FB : { 0x0417 : "PCI-417 High Speed A/D Board",
         },
0x11FE : { 0x0001 : "",
           0x0002 : "",
           0x0003 : "",
           0x0004 : "",
           0x0005 : "",
           0x0006 : "",
           0x0007 : "",
           0x0008 : "",
           0x0009 : "",
           0x000A : "",
           0x000B : "",
           0x000C : "",
           0x000D : "",
           0x8015 : "4-port UART 16954",
         },
0x1202 : { 0x0001 : "PCI ATM Adapter",
         },
0x1203 : { 0x0001 : "Unknown",
         },
0x1204 : { 0x9876 : "wwDW",
         },
0x1208 : { 0x4853 : "HS-Link Device",
         },
0x1209 : { 0x0100 : "PLX PCI BRIDGE",
         },
0x120E : { 0x0100 : "Multiport Serial Card",
           0x0101 : "Multiport Serial Card",
           0x0102 : "Multiport Serial Card",
           0x0103 : "Multiport Serial Card",
           0x0104 : "Multiport Serial Card",
           0x0105 : "Multiport Serial Card",
           0x0200 : "Intelligent Multiport Serial",
           0x0201 : "Intelligent Serial Card",
           0x0300 : "1105",
           0x0301 : "",
           0x0302 : "",
           0x0303 : "teclado",
         },
0x120F : { 0x0001 : "",
         },
0x1210 : { 0x25f4 : "No data",
         },
0x1216 : { 0x0003 : "PTM400 PCI Taxi Module",
         },
0x1217 : { 0x00f7 : "1394 Open Host Controller Interface",
           0x1217 : "111111111",
           0x6729 : "PCI to PCMCIA Bridge",
           0x673A : "PCI to PCMCIA Bridge",
           0x6832 : "CardBus Controller",
           0x6836 : "CardBus Controller",
           0x6872 : "CardBus Controller",
           0x6925 : "CardBus Controller",
           0x6933 : "CardBus Controller",
           0x6972 : "CardBus Controller",
           0x7110 : "MemoryCardBus Accelerator",
           0x7112 : "",
           0x7113 : "PCMCIA/SmartCardBus Contoller",
           0x7114 : "CardBus Controller",
           0x7120 : "O2Micro Integrated MMC/SD controller",
           0x7130 : "O2Micro Integrated MMC/SD/MS/xD/SM Controller",
           0x7134 : "MemoryCardBus Controller 6-in-1",
           0x7135 : "MemoryCardBus Contoller",
           0x7136 : "O2Micro CardBus Controller",
           0x71E2 : "",
           0x7212 : "",
           0x7213 : "",
           0x7222 : "pci to pcmcia bridge",
           0x7223 : "MemoryCardBus Controller",
           0x8130 : "o2 sd card reader",
           0x8231 : "O2Micro OZ600XXX Memory Card ",
           0x8330 : "Mass storage controller [0180]",
           0x8331 : "O2Micro Integrated MS/PRO controller",
         },
0x121A : { 0003 : "",
           003 : "",
           0x0001 : "Voodoo 3D Acceleration Chip",
           0x0002 : "Voodoo 2 3D Accelerator",
           0x0003 : "Voodoo Banshee",
           0x0005 : "All Voodoo3 chips",
           0x0007 : "",
           0x0009 : "AGP X2",
           0x0010 : "Rev.A AGPx4",
           0x0057 : "Avenger",
         },
0x1220 : { 0x1220 : "AMCC 5933 TMS320C80 DSP/Imaging Board",
           0x4242 : "controller audio multimediale",
         },
0x1223 : { 0x0001 : "KatanaQp",
           0x0002 : "KosaiPM",
           0x0016 : "PCIe-8120",
           0x003 : "Katana3752",
           0x004 : "Katana3750",
           0x0044 : "Memory controller",
           0x005 : "Katana752i",
           0x006 : "Katana750i",
           0x007 : "CC1000dm",
           0x008 : "Pm3Gv",
           0x009 : "Pm3GE1T1",
           0x010 : "SpiderwareSG",
           0x011 : "SpiderwareSS7",
           0x012 : "SpiderSS7",
           0x013 : "Spider FRAME RELAY",
           0x014 : "Spider STREAMS",
           0x015 : "Spider DSF",
         },
0x1224 : { 0x1000 : "Plum Audio",
         },
0x122D : { 0x1206 : "Asus",
           0x4201 : "AMR 56K modem",
           0x50DC : "Audio",
           0x80DA : "Audio",
         },
0x122F : { 0x37AF : "Reflectometer using PLX 9030",
         },
0x1236 : { 0x0000 : "RealMagic64/GX",
           0x0531 : "MX98715/25",
           0x3d01 : "000",
           0x6401 : "REALmagic64/GX",
           0x9708 : "realmagic64/gx",
         },
0x123D : { 0x0010 : "PCI-DV Digital Video Interface",
         },
0x123F : { 0x00E4 : "MPEG",
           0x6120 : "DVD device",
           0x8120 : "i440B",
           0x8888 : "cPEG C 3.0 DVD/MPEG2 Decoder",
         },
0x1241 : { 0x1603 : "keyboard",
         },
0x1242 : { 0x1460 : "2-Gb/s Fibre Channel-PCI 64-bit 66 MHz",
           0x1560 : "Dual Channel 2 Gb/s Fibre Channel-PCI-X",
           0x4643 : "JNI PCI 64-bit Fibrechannel (needs clone)",
         },
0x1244 : { 0x0700 : "ISDN controller",
           0x0800 : "ISDN Controller",
           0x0A00 : "ISDN Controller",
           0x0E00 : "Fritz!PCI 2.0 ISDN Controller",
           0x1100 : "ISDN Controller",
           0x1200 : "ISDN Controller",
           0x2700 : "DSP TNETD5100GHK / TNETD5015",
           0x2900 : "AVM Fritz!Card DSL v2.0 PCI",
         },
0x124A : { 0x10BD : "Intel Gigabit network connection",
           0x4023 : "Blitzz Wireless G",
         },
0x124C : { 0x0220 : ".",
         },
0x124D : { 0x0000 : "",
           0x0002 : "",
           0x0003 : "",
         },
0x124F : { 0x0041 : "PCI RAID Controller",
         },
0x1250 : { 0x1978 : "",
           0x2898 : "",
         },
0x1255 : { 0x1110 : "",
           0x1210 : "",
           0x2110 : "VideoPlex pci bpc1825 rev a",
           0x2120 : "VideoPlex BPC 1851 A",
           0x2130 : "",
         },
0x1256 : { 0x4201 : "EIDE Adapter",
           0x4401 : "Dale EIDE Adapter",
           0x5201 : "IntelliCache SCSI Adapter",
         },
0x1258 : { 0x1988 : "",
         },
0x1259 : { 0x2503 : "",
           0x2560 : "AT-2560 Fast Ethernet Adapter (i82557B)",
           0xc107 : "",
         },
0x125B : { 0x0B95 : "USB2.0 to 10/100M Fast Ethernet Controller",
           0x1400 : "ASIX AX88140 Based PCI Fast Ethernet Adapter",
           0x1720 : "USB2 to Fast Ethernet Adapter",
         },
0x125D : { 0x0000 : "PCI Fax Modem (early model)",
           0x1961 : "ESS Solo-1 Soundcard",
           0x1968 : "Maestro-2 PCI audio accelerator",
           0x1969 : "Solo-1 PCI AudioDrive family",
           0x1978 : "ESS Maestro-2E PCI Audiodrive",
           0x1980 : "subsys_0012103c_rev_12",
           0x1988 : "ESS Allegro PCI Audio (WDM)",
           0x1989 : "ESS Maestro 3 PCI Audio Accelerator",
           0x1990 : "",
           0x1992 : "",
           0x1998 : "Maestro 3i",
           0x1999 : "TAWE0548S",
           0x199B : "Maestro-3.COMM PCI Voice+audio",
           0x2808 : "PCI Fax Modem (later model)",
           0x2828 : "TeleDrive",
           0x2838 : "PCI Data Fax Modem",
           0x2839 : "Superlink Modem/V.92 chipset 56K",
           0x2898 : "TelDrive ES56T-PI family V.90 PCI modem",
         },
0x125F : { 0x2084 : "AMCC Bridge + 2 x Super I/O (National PC97338)",
         },
0x1260 : { 0x3860 : "PRISM 2.5 802.11b 11Mbps Wireless Controller",
           0x3872 : "LAN-Express IEEE 802.11b PCI Adapter",
           0x3873 : "PRISMII.5 IEE802.11g Wireless LAN",
           0x3886 : "Creatix CTX405 WLAN Controller / ZyAir G100 - WLAN",
           0x3890 : "PRISM GT 802.11g 54Mbps Wireless Controller",
           0x8130 : "NTSC/PAL Video Decoder",
           0x8131 : "NTSC/PAL Video Decoder",
         },
0x1266 : { 0x0001 : "NE10/100 Adapter (i82557B)",
           0x1910 : "NE2000Plus (RT8029) Ethernet Adapter",
         },
0x1267 : { 0x1016 : "NICCY PCI card",
           0x4243 : "Satellite receiver board / MPEG2 decoder",
           0x5352 : "",
           0x5A4B : "",
         },
0x1268 : { 0x0204 : "Tektronix IO Processor / Tektronix PCI Acquisition Interface Rev 204",
         },
0x126A : { 0x269B : "SM Bus Controller",
         },
0x126C : { 0x1F1F : "e-mobility 802.11b Wireless LAN PCI Card",
         },
0x126F : { 0x0501 : "Mobile Multimedia Companion Chip (MMCC)",
           0x0710 : "LynxEM",
           0x0712 : "LynxEM+",
           0x0720 : "Lynx3DM",
           0x0810 : "LynxE",
           0x0811 : "LynxE",
           0x0820 : "Lynx3D",
           0x0910 : "SILICON MOTION",
         },
0x1272 : { 0x0780 : "PCIVEN_8086&DEV_1C3A",
           0x1272 : "PCIVEN_8086&DEV_1C3A&SUBSYS_2ABF103C",
           0x9876 : "PCIVEN_1272&DEV_0780&SUBSYS_00000008&REV_7A3&61AAA01&0&58",
         },
0x1273 : { 0x0002 : "t9p17af-01",
         },
0x1274 : { 0X1005 : "Serial PCI Port",
           0x1274 : "multimedia audio device",
           0x1371 : "AudioPCI",
           0x1373 : "Sound Blaster Audio(PCI)",
           0x5000 : "AudioPCI",
           0x5880 : "Soundblaster (CT4750)",
           0x9876 : "",
         },
0x1278 : { 0x0701 : "PowerPC Node",
           0x1001 : "TMB17 Motherboard",
         },
0x1279 : { 0x0060 : "Efficeon Virtual Northbridge",
           0x0061 : "Efficeon AGP Bridge",
           0x0295 : "Virtual Northbridge",
           0x0395 : "Northbridge",
           0x0396 : "SDRAM Controller",
           0x0397 : "BIOS scratchpad",
         },
0x127E : { 0x0010 : "Videum 1000 AV Plus",
         },
0x1282 : { 0x1282 : "DEV",
           0x9009 : "Ethernet Adapter",
           0x9100 : "",
           0x9102 : "10/100 Mbps Fast Ethernet Controller",
         },
0x1283 : { 0x0801 : "Audio Digital Controller",
           0x673A : "IDE Controller",
           0x8152 : "Advanced RISC-to-PCI Companion Chip",
           0x8172 : "Ultra RISC (MIPS",
           0x8211 : "ATA/ATAPI Controller",
           0x8212 : "ATA 133 IDE RAID Controller",
           0x8213 : "IDE Controller",
           0x8330 : "Host Bridge",
           0x8872 : "PCI-ISA I/O chip with SMB & Parallel Port",
           0x8875 : "PCI Parallel Port",
           0x8888 : "PCI to ISA Bridge",
           0x8889 : "sound",
           0x9876 : "PCI I/O CARD",
           0xE886 : "PCI to ISA Bridge",
         },
0x1285 : { 0x0100 : "Maestro-1 AudioDrive",
         },
0x1287 : { 0x001E : "DVD Decoder",
           0x001F : "DVD Decoder",
           0x0020 : "MPEG/DVD video decoder",
         },
0x1289 : { 0x1006 : "1708",
         },
0x128A : { 0xF001 : "controller ethernet",
         },
0x128D : { 0x0021 : "ATM Adapter",
         },
0x1290 : { 0x0010 : "?",
         },
0x129A : { 0x0415 : "PCI 66MHz Analyzer and 33MHz Exerciser",
           0x0515 : "PCI 66MHz Analyzer and Exerciser",
           0x0615 : "PCI 66MHz and PCI-X 100MHz Bus Analyzer and Exerciser",
           0x0715 : "PCI 66MHz and PCI-X 133MHz Bus Analyzer and Exerciser",
           0xDD10 : "Digital Parallel Input Output Device 32bit",
           0xDD11 : "Digital Parallel Input Output Device 64bit",
           0xDD12 : "Digital Parallel Input Output Device 64bit",
         },
0x12A0 : { 0x0008 : "Allen-Bradley 1784-PKTX",
         },
0x12A3 : { 0xECB8 : "V.92 Lucent Modem",
         },
0x12AA : { 0x5568 : "WANic 400 series X.21 controller",
           0x556C : "NAI HSSI Sniffer PCI Adapter",
         },
0x12AB : { 0x3000 : "PCI",
         },
0x12AD : { 0x0010 : "HERMES-S0",
           0x0020 : "HERMES-PRI",
           0x0080 : "HERMES-PRI/PCIX",
         },
0x12AE : { 0x0001 : "ACEnic 1000 BASE-SX Ethernet adapter",
           0x0002 : "Copper Gigabit Ethernet Adapter",
         },
0x12B9 : { 0x00c2 : "pci simple communication controller",
           0x1006 : "5610 56K FaxModem WinModem",
           0x1007 : "US Robotics 56K DATA FAX WINMODEM",
           0x1008 : "USR5610B (0005610-02) 56K Performance Pro Modem (PCI Internal)",
           0x12b9 : "psi simple communication controller",
           0x3F0 : "US Robotics 56K Fax PCI aka Model 0726",
         },
0x12BA : { 0x0032 : "Hammerhead-Lite-PCI",
         },
0x12C1 : { 0x9080 : "Communications Processor",
         },
0x12C3 : { 0x0058 : "LAN Adapter (NE2000-compatible)",
           0x5598 : "Ethernet Adapter (NE2000-compatible)",
         },
0x12C4 : { 0x0001 : "",
           0x0002 : "",
           0x0003 : "",
           0x0004 : "",
           0x0005 : "BlueHeat 8 Port RS232 Serial Board",
           0x0006 : "",
           0x0007 : "",
           0x0008 : "",
           0x0009 : "",
           0x000A : "",
           0x000B : "",
           0x000C : "",
           0x000D : "",
           0x000E : "",
           0x000F : "",
           0x0300 : "",
           0x0301 : "",
           0x0302 : "",
           0x0303 : "",
           0x0304 : "",
           0x0305 : "",
           0x0306 : "",
           0x0307 : "",
           0x0308 : "Starcom UM100 Wireless modem for WiMax ",
           0x0309 : "",
           0x030A : "",
           0x030B : "",
         },
0x12C5 : { 0x007F : "PEI Imaging Subsystem Engine",
           0x0081 : "PCI Thresholding Engine",
           0x0085 : "Video Simulator/Sender",
           0x0086 : "Multi-scale Thresholder",
         },
0x12C7 : { 0x0546 : "D120JCT-LS Card",
           0x0561 : "BRI/2 Type Card (Voice Driver)",
           0x0647 : "D/240JCT-T1 Card",
           0x0648 : "D/300JCT-E1 Card",
           0x0649 : "D/300JCT-E1 Card",
           0x0651 : "MSI PCI Card",
           0x0673 : "BRI/160-PCI Card",
           0x0674 : "BRI/120-PCI Card",
           0x0675 : "BRI/80-PCI Card",
           0x0676 : "D/41JCT Card",
           0x0685 : "D/480JCT-2T1 Card",
           0x0687 : "D/600JCT-2E1 (75 Ohm) Card",
           0x0689 : "Dialogic 2E1 - JCT series",
           0x0707 : "D/320JCT (Resource Only) Card",
           0x0708 : "D/160JCT (Resource Only) Card",
         },
0x12CB : { 0x0027 : "studiocard",
           0x002D : "agp",
           0x002E : "",
           0x002F : "",
           0x0030 : "",
           0x0031 : "",
           0x0032 : "20-bit 2-in",
           0x0033 : "",
           0x0034 : "",
           0x0035 : "",
         },
0x12D1 : { 0x1001 : "MSM6246",
           0x1003 : "81237",
           0x140B : "EC159",
           0x1412 : "09HT1407",
           0x1446 : "E1800",
           0x14c5 : "K4510",
           0x1520 : "-e620",
           0x1802 : "unknown",
           0x3609 : "N/A",
         },
0x12D4 : { 0x0301 : "EP1S",
         },
0x12D5 : { 0x1000 : "Broadband Signal Processor",
           0x1002 : "Digital Signal Processor",
         },
0x12D8 : { 0x71E2 : "3 Port PCI to PCI bridge",
           0x8140 : "4 Port PCI to PCI bridge",
           0x8150 : "2-Port PCI to PCI Bridge",
           0x8152 : "2-Port PCI-To-PCI Bridge",
           0xA404 : "PCIe Packet Switch",
           0xE111 : "PCI to PCIe Bridge",
           0xe130 : "PCI-X Bridge",
         },
0x12DB : { 0x0003 : "FoxFire II",
         },
0x12DE : { 0x0200 : "Cryptoswift 200",
         },
0x12DF : { 0x2102 : "Communications Controller",
           0x8236 : "PCI Controller",
         },
0x12E0 : { 0x0010 : "Quad UART",
           0x0020 : "Quad UART",
           0x0030 : "Quad UART",
         },
0x12E4 : { 0x1000 : "PRI Controller",
           0x1140 : "ISDN Controller",
           0xB005 : "BRI Controller",
           0xB006 : "BRI Controller",
         },
0x12EB : { 0x0001 : "Vortex 1 Digital Audio Processor",
           0x0002 : "Vortex 2 Audio Processor",
           0x0003 : "Aureal Soundcard",
         },
0x12EC : { 0x8139 : "0xxxx",
           0x8140 : "asf",
         },
0x12F2 : { 0x1002 : "Grapics Radeon X850",
           0x3059 : "AC97 Enhanced Audio Controller - the 8251 controller is different",
         },
0x12F8 : { 0x0002 : "s3 trio",
         },
0x12FC : { 0x5cec : "IEEE 488",
         },
0x1303 : { 0x0001 : "cM67 CompactPCI DSP Card",
           0x0002 : "M44/cM44 DSP board",
           0x0003 : "Quattro6x DSP board",
           0x0004 : "Chico/ChicoPlus Data Acquisition Board",
           0x0005 : "Code Hammer Jtag Debugger board",
           0x0006 : "Matador DSP board",
           0x0007 : "Quixote DSP board",
           0x0008 : "Quadia C64x DSP",
           0x0009 : "Quadia DSP Baseboard",
         },
0x1307 : { 0x0001 : "",
           0x0006 : "",
           0x000B : "",
           0x000C : "",
           0x000D : "",
           0x000F : "",
           0x0010 : "",
           0x0014 : "24 Bit Digital Input/Output Board",
           0x0015 : "",
           0x0016 : "",
           0x0017 : "",
           0x0018 : "",
           0x0019 : "",
           0x001A : "",
           0x001B : "",
           0x001C : "AR2425",
           0x001D : "",
           0x001E : "",
           0x001F : "",
           0x0020 : "",
           0x0021 : "",
           0x0022 : "",
           0x0023 : "",
           0x0024 : "",
           0x0025 : "",
           0x0026 : "",
           0x0027 : "",
           0x0028 : "24 Bit Digital Input/Output Board",
           0x0029 : "",
           0x002C : "PCI-INT32",
           0x0033 : "",
           0x0034 : "",
           0x0035 : "",
           0x0036 : "",
           0x0037 : "",
           0x004C : "",
           0x004D : "",
           0x0064 : "10 channels",
           0x0361 : "?",
         },
0x1308 : { 0x0001 : "NetCelerator Adapter",
         },
0x130B : { 0x130b : "0x9876",
         },
0x1310 : { 0x0003 : "CompactPCI Interface",
           0x000D : "FPGA PCI Bridge",
         },
0x1317 : { 0x0531 : "ADMtek AN986",
           0x0981 : "FastNIC 10/100 Fast Ethernet Adapter",
           0x0985 : "Linksys LNE 100TX Fast Ethernet Adapter(LNE100TX v4)",
           0x1985 : "CardBus 10/100 Fast Ethernet&#1050;&#1086;&#1085;&#1090;&#1088;&#1086;&#1083;&#1083;&#1077;&#1088;",
           0x2850 : "HSP56 MicroModem",
           0x5120 : "ADMtek ADM5120 SOC (rev: 0)",
           0x7892 : "HSP56 MicroModem",
           0x8201 : "802.11b Wireless PCI Card",
           0x9511 : "PCI 10/100 Fast Ethernet Adapter",
           0x9513 : "PCI 10/100 Fast Ethernet Adapter",
           8201 : "1317",
         },
0x1318 : { 0x0911 : "G-NIC II",
         },
0x1319 : { 0x0801 : "PCI Card MediaForte made in singapore (driver - ct",
           0x0802 : "Xwave PCI Joystick",
           0x1000 : "PCI Audio",
           0x1001 : "Joystick",
           0x1319 : "Xwave PCI audio controller",
           0x4901 : "ForteMedia PCI Audio Card",
           802 : "PCI Audio",
         },
0x131F : { 0x2002 : "CyberSerial 16850",
           0x2011 : "Siig Inc Duet 1S(16550)+1P",
           0x2012 : "Duet 1S(16850)+1P",
           0x2020 : "Communication controller",
           0x2030 : "SIIG Cyber Serial Dual PCI Board",
           0x2042 : "Trio 1S(16850)+2P",
           0x2050 : "Siig Inc CyberSerial (4-port) 16550",
           0x2051 : "CyberSerial 16650",
           0x2052 : "CyberSerial 16850",
           0x2060 : "Trio 2S(16550)+1P",
           0x2061 : "Trio 2S(16650)+1P",
           0x2062 : "Trio 2S(16850)+1P",
           0x9876 : "Trio 2S(16550)+1P",
         },
0x1328 : { 0x2048 : "",
           0x8888 : "cPEG C 3.0 DVD/MPEG2 decoder",
         },
0x1332 : { 0x5410 : "PCI 32bit Bulk Memory w/DMA",
           0x5415 : "PCI Battery Backed SDRAM Adapter",
           0x5425 : "PCI Memory Module with Battery Backup",
           0x6140 : "Memory Module",
         },
0x133D : { 0x1000 : "Industrial I/O Card",
         },
0x1344 : { 0x3240 : "",
           0x3320 : "MT8LLN21PADF",
           0x3321 : "21PAD",
           0x3470 : "MT7LLN22NCNE",
           0x4020 : "",
           0x4030 : "",
         },
0x134A : { 0x0001 : "Domex DMX 3191D PCI SCSI Controller",
           0x0002 : "Domex DMX3192U/3194UP SCSI Adapter",
           0x3510 : "scsi",
         },
0x134D : { 0x2188 : "intel",
           0x2189 : "pctel HSP56 V92 PCI Modem",
           0x2486 : "V.92 MDC Modem",
           0x7890 : "HSP56 MicroModem",
           0x7891 : "HSP MicroModem 56",
           0x7892 : "HSP56 MicroModem",
           0x7893 : "HSP MicroModem 56",
           0x7894 : "HSP MicroModem 56",
           0x7895 : "HSP MicroModem 56",
           0x7896 : "HSP MicroModem 56",
           0x7897 : "HSP MicroModem 56/PCT789T",
           0x9714 : "PCTEL",
           0xD800 : "pctel 56k modem",
           8086 : "dev",
         },
0x135A : { 0x0042 : "4-port RS-232",
           0x0181 : "PCI LPT and RS-232",
           0x0224 : "PLX PCI Bus Logic",
           0x0228 : "pq100akj9737",
         },
0x135E : { 0x0EC3 : "PCIe 8 Relay Output/8 Isolated Input Board ",
           0x5101 : "Route 56",
           0x5102 : "RS-232 synchronous card",
           0x7101 : "Single Port RS-232/422/485/520",
           0x7201 : "Dual Port RS-232/422/485 Interface",
           0x7202 : "Dual Port RS-232 Interface",
           0x7401 : "Four Port RS-232 Interface",
           0x7402 : "Four Port RS-422/485 Interface",
           0x7801 : "Eight Port RS-232 Interface",
           0x8001 : "Digital I/O Adapter",
         },
0x1360 : { 0x0101 : "DCF77 Radio Clock",
           0x0102 : "DCF77 Radio Clock",
           0x0103 : "DCF77 Radio Clock",
           0x0104 : "DCF77 Radio Clock",
           0x0105 : "DCF77 Receiver",
           0x0106 : "High Precision DCF77 Radio Clock",
           0x0201 : "GPS Receiver",
           0x0202 : "GPS Receiver",
           0x0203 : "GPS Receiver",
           0x0204 : "GPS Receiver",
           0x0205 : "GPS Receiver",
           0x0206 : "GPS receiver",
           0x0301 : "IRIG Timecode Reader",
           0x0302 : "IRIG Timecode Reader",
           0x0303 : "IRIG Timecode Reader",
           0x0304 : "IRIG Timecode Receiver",
           0x0305 : "IRIG Timecode Reader",
           0x0306 : "IRIG Timecode Reader",
           0x0501 : "PTP/IEEE1588 Slave Card",
           0x0601 : "Free Running Clock",
         },
0x1365 : { 0x9050 : "",
         },
0x1375 : { 0x2571 : "NA",
         },
0x137A : { 0x0001 : "",
           0x0003 : "PCI-424 Original",
           0x0004 : "PCI-424 X",
           0x0005 : "PCIe-424",
         },
0x1382 : { 0x0001 : "Sek'D ARC88 professional soundcard",
           0x2009 : "SEK'D Prodif 96 Pro - professional audio card",
           0x2048 : "Prodif Plus sound card",
           0x2088 : "8-in",
         },
0x1385 : { 0x4100 : "802.11b Wireless Adapter",
           0x4105 : "",
           0x620A : "Toshiba",
           0x622A : "",
           0x630A : "",
           0x8169 : "Gigabit Ethernet Adapter",
           0xF311 : "Fast Ethernet Adapter",
           0xF312 : "",
         },
0x1387 : { 0x4640 : "sl240",
           0x5310 : "SCRAMNet GT200",
         },
0x1389 : { 0x0001 : "Intelligent fieldbus Adapter",
           0x0104 : "PCI-CANIO adapter",
         },
0x138A : { 0x0001 : "0001",
           0x0005 : "0008",
           0x0006 : "0006",
           0x0007 : "0007",
           0x0009 : "0008",
           0x0011 : "11",
           0x0018 : "Biometric Devices",
           0x003C : "0008",
           0x003D : "0104",
           0x11 : "VFS5011",
         },
0x1393 : { 0x1010 : "",
           0x1020 : "",
           0x1022 : "unknown",
           0x1040 : "Smartio",
           0x1041 : "",
           0x1042 : "",
           0x1140 : "",
           0x1141 : "",
           0x1320 : "Industio",
           0x1321 : "",
           0x1340 : "UniversalPCI board",
           0x1401 : "",
           0x1680 : "Smartio",
           0x1681 : "CP-168U Smart Serial Board",
           0x2040 : "Intellio",
           0x2180 : "Intellio Turbo PCI",
           0x2210 : "---",
           0x2240 : "---",
           0x3200 : "Intellio Turbo PCI",
           0x5020 : "",
           0x6800 : "dvr capture card",
         },
0x1394 : { 0x0001 : "Gigabit Ethernet Adapter",
         },
0x1397 : { 0x0B4D : "ISDN HDLC FIFO Controller",
           0x2BD0 : "ISDN HDLC FIFO Controller",
           0x8B4D : "ISDN HDLC FIFO Controller",
           0xB000 : "HCF-PCI card",
           0xB006 : "HCF-PCI card",
           0xB007 : "HCF-PCI card",
           0xB008 : "usb webcam",
           0xB009 : "HCF-PCI card",
           0xB00A : "HCF-PCI card",
           0xB00B : "HCF-PCI card",
           0xB00C : "HCF-PCI card",
           0xB100 : "HCF-PCI card",
         },
0x139A : { 0x0007 : "Alacritech iSCSI Controller",
         },
0x13A3 : { 0x0005 : "Security Processor",
           0x0006 : "Public Key Processor",
           0x0007 : "Security Processor",
           0x0012 : "Security Processor",
           0x0014 : "Security Processor",
           0x0015 : "Security Processor",
           0x0017 : "Security Processor",
           0x0018 : "Security Processor",
           0x001d : "Cryptographic Processor",
           0x0020 : "Cryptographic Processor",
           0x0026 : "Security Processor",
           0x16 : "Security Processor",
         },
0x13A7 : { 0x6240 : "BSRV2-301A",
         },
0x13A8 : { 0x0152 : "Dual UART",
           0x0154 : "Four Channel PCI Bus UART",
           0x0158 : "Eight Channel PCI Bus UART (5V)",
         },
0x13B6 : { 0x13b6 : "sguiu",
         },
0x13C0 : { 0x0010 : "single port multiprotocol serial adapter",
           0x0020 : "low speed single port multiprotocol serial adapter",
           0x0030 : "4 port multiprotocol serial adapter",
           0x0070 : "single port multiprotocol serial adapter",
           0x0080 : "4 port multiprotocol serial adapter",
           0x0090 : "one port asynchronous serial adapter",
           0x00a0 : "2 port multiprotocol serial adapter",
           0x0210 : "single port multiprotocol serial adapter",
         },
0x13C1 : { 0x1000 : "ATA-RAID Controller",
           0x1001 : "ATA-133 Storage Controller",
           0x1002 : "SATA/PATA Storage Controller",
           0x1003 : "SATA2 Raid Controller",
           0x1004 : "PCI-Express SATA2 Raid Controller",
           0x1005 : "PCI-Express SATA2/SAS Raid Controller",
           0x1010 : "PCI-Express2 SAS2/SATA2 Raid Controller",
         },
0x13C7 : { 0x0ADC : "Multi-Function Analogue/Digital IO card",
           0x0B10 : "Parallel I/O Card",
           0x0D10 : "Digital I/O Card",
           0x5744 : "Watchdog Card",
         },
0x13D0 : { 0x2103 : "B2C2 Sky2PC Core Chip sky star 2 <technisat>",
           0x2200 : "",
         },
0x13D1 : { 0xAB02 : "",
           0xAB03 : "",
           0xAB06 : "FE2000VX",
           0xAB08 : "SMC8035TX",
         },
0x13D7 : { 0x0205 : "toshiba",
           0x8086 : "toshiba",
         },
0x13D8 : { 0x1000 : "XaQti 1000Mbit/sec Gbit Ethernet Controller",
         },
0x13DF : { 0x0001 : "Modem",
         },
0x13EA : { 0x3131 : "BoSS Bit Synchronous HDLC Controller",
           0x3134 : "Chateau Channelized T1/E1/HDLC Controller",
         },
0x13F0 : { 0x0200 : "IP100A Integrated 10/100 Ethernet MAC + PHY",
           0x0201 : "Fast Ehternet Adapter",
           0x0300 : "Network Adapter",
           0x1021 : "Tamarack 9021A Gigabit Ethernet adapter",
           0x1023 : "Gigabit Ethernet Controllera",
           0x13F0 : "ST201 Fast Ethernet &#65533;&#65533;&#65533; &#65533; &#65533;'&#65533;",
         },
0x13F1 : { 0x0028 : "MCP67 High Definition Audio",
         },
0x13F6 : { 0211 : "serlio",
           0x0011 : "sound card",
           0x0100 : "PCI",
           0x0101 : "PCI Audio Device",
           0x0111 : "C-Media Audio Controller",
           0x0112 : "PCI Audio Chip",
           0x0191 : "CMI 8738 8CH Sound Card",
           0x0211 : " Driver controller pci simple comunications - PCtel HSP56 Micro Modem Driver  ",
           0x0300 : "pci audio driver",
           0x111 : "C-Media Audio Controller",
           0x8788 : "C-Media Oxygen HD",
           0x9876 : "C-Media Audio Controller",
           0x9891 : "C-Media Audio Controller",
         },
0x13FD : { 0x160E : "SATA/150 device to USB 2.0",
           0x161F : "s",
           0x1840 : "SATA/150 device to USB 2.0 Host interface (http://www.initio.com/Html/inic-1608.html)",
         },
0x13FE : { 0x1240 : "PS2134CE-0",
           0x1600 : "PCI-1610CU/9-AE",
           0x1680 : "PCI-1680U-A",
           0x16FF : "PCI-1610CU/9-AE",
           0x1713 : "PCI-1713",
           0x1723 : "PCI-1723",
           0x1724 : "PCI-1723",
           0x1755 : "PCI-1755",
           0x1760 : "amcc pci matchmaker s5920q",
           0x1761 : "PCI-1751",
           0x1762 : "PCI-1762",
           0x1a00 : "0x03",
           0x3730 : "PCM-3730I",
         },
0x1400 : { 0x0001 : "",
           0x0003 : "",
           0x0004 : "030000",
           0x1401 : "hd 2600xt",
         },
0x1402 : { 0x2E00 : "Multifunction Data Aquistion card",
           0x4610 : "Multi-IO board (16x 16bit ADC",
           0x4650 : "Multi-IO board (16x 16bit ADC",
         },
0x1407 : { 0x0100 : "Lava Dual Serial 550 PCI",
           0x0101 : "Lava Quattro PCI A/B",
           0x0102 : "Lava Quattro PCI C/D",
           0x0110 : "Lava DSerial PCI Port A",
           0x0111 : "Lava DSerial PCI Port B",
           0x0180 : "Lava Octopus PCI Ports 1-4",
           0x0181 : "Lava Octopus PCI Ports 5-8",
           0x0200 : "LavaPort Dual-650 PCI",
           0x0201 : "LavaPort Quad-650 PCI A/B",
           0x0202 : "LavaPort Quad-650 PCI C/D",
           0x0220 : "LavaPort Quad-650 PCI A/B",
           0x0221 : "LavaPort Quad-650 PCI C/D",
           0x0400 : "Lava 8255 PIO PCI",
           0x0500 : "Lava Single Serial 550 PCI",
           0x0510 : "Lava SP Serial 550 PCI",
           0x0511 : "Lava SP BIDIR Parallel PCI",
           0x0520 : "Lava RS422 SS-PCI",
           0x0600 : "LavaPort 650 PCI",
           0x0A00 : "COM Port Accelerator",
           0x120 : "Lava Quattro 550 PCI A/B",
           0x121 : "Lava Quattro 550 PCI C/D",
           0x520 : "s",
           0x8000 : "Lava Parallel",
           0x8001 : "Lava Dual Parallel port A",
           0x8002 : "Lava Dual Parallel port A",
           0x8003 : "Lava Dual Parallel port B",
           0x8800 : "BOCA Research IOPPAR",
         },
0x1409 : { 0x7168 : "40371409",
           0x7268 : "PCI / ISA IEEE1284 ECP/EPP/SPP/BPP Signal Chips So",
           7268 : "PCI / ISA IEEE1284 ECP/EPP/SPP/BPP PAR4008A",
         },
0x140B : { 0x0610 : "",
           0x615 : "Na",
           0x682 : "NA",
         },
0x1412 : { 0x1712 : "ICE1712",
           0x1724 : "VT1723",
         },
0x1415 : { 0x8401 : "PCI Interface to local bus",
           0x8403 : "PCI Parallel Card",
           0x9500 : "Quad UART (disabled)",
           0x9501 : "Quad UART",
           0x9505 : "Dual UART",
           0x950A : "Dual PCI UARTS",
           0x950B : "Integrated High Performance UART",
           0x9510 : "PCI Interface (disabled)",
           0x9511 : "PCI Interface to 8-bit local bus",
           0x9512 : "PCI Interface to 32-bit bus",
           0x9513 : "Parallel Port",
           0x9521 : "Dual UART",
           0x9523 : "Integrated Parallel Port",
           0xc110 : "Parallel PCI Express Card (Manhattan 158176)",
           0xc158 : "2 native UARTs (function 0)",
           0xc15d : "2 native UARTs (function 1)",
           0xc208 : "Quad UARTs",
           0xc20d : "Quad UARTs (function 1)",
           0xc308 : "Octo UARTs",
           0xc30d : "Octo UARTs (function 1)",
         },
0x141F : { 0x6181 : "MPEG decoder",
         },
0x1425 : { 0x0030 : "T310 10GbE Single Port Adapter",
           0x31 : "T320 10GbE Dual Port Adapter",
           0x32 : "T302 1GbE Dual Port Adapter",
           0x33 : "T304 1GbE Quad Port Adapter",
           0x34 : "B320 10GbE Dual Port Adapter",
           0x35 : "S310-CR 10GbE Single Port Adapter",
           0x36 : "S320-LP-CR 10GbE Dual Port Adapter",
           0x37 : "N320-G2-CR 10GbE Dual Port Adapter",
           0x4401 : "T420-CR Unified Wire Ethernet Controller",
           0x4402 : "T422-CR Unified Wire Ethernet Controller",
           0x4403 : "T440-CR Unified Wire Ethernet Controller",
           0x4404 : "T420-BCH Unified Wire Ethernet Controller",
           0x4405 : "T440-BCH Unified Wire Ethernet Controller",
           0x4406 : "T440-CH Unified Wire Ethernet Controller",
           0x4407 : "T420-SO Unified Wire Ethernet Controller",
           0x4408 : "T420-CX Unified Wire Ethernet Controller",
           0x4409 : "T420-BT Unified Wire Ethernet Controller",
           0x440a : "T404-BT Unified Wire Ethernet Controller",
           0x440d : "T480 Unified Wire Ethernet Controller",
           0x440e : "T440-LP-CR Unified Wire Ethernet Controller",
           0x7145 : "N/A",
         },
0x1435 : { 0x0531 : "DELETE",
           0x6020 : "SPM6020",
           0x6030 : "SPM6030",
           0x6420 : "SPM186420",
           0x6430 : "SPM176430",
           0x7520 : "DM7520",
           0x7540 : "SDM7540",
         },
0x1448 : { 0x0001 : "Audio Editing",
         },
0x144A : { 0x348A : "Low-profile High-Performance IEEE488 GPIB Interface Card for PCI Bus",
           0x7230 : "",
           0x7248 : "PLX PCI9052",
           0x7250 : "PLX PCI9052",
           0x7256 : "PCI-7256 16-CH Latching Relay & 16-CH Isolated Digital Input Card",
           0x7296 : "96-ch digital I/O card",
           0x7432 : "",
           0x7433 : "64-ch digital Input card",
           0x7434 : "",
           0x7841 : "SJA 1000- baseddual port  CAN bus card",
           0x8133 : "Dell Wireless 5720 VZW Mobile Broadband Card",
           0x8554 : "",
           0x9111 : "",
           0x9113 : "",
           0x9114 : "",
         },
0x144B : { 0x0601 : "",
         },
0x1458 : { 0x1458 : "microsoft",
           0x5000 : "GA-X48T-DQ6",
         },
0x145F : { 0x0001 : "Multi-axis Motion Controller",
           0x0002 : "Multi-axis Motion Controller",
         },
0x1462 : { 0x00C1 : "NX6800-TD256E",
           0x4720 : "Audio controller",
           0x5071 : "Audio controller",
           0x5964 : "RADEON 9250/9200 series AGP",
           0x7120 : "",
           0x7960 : "MCP2T",
         },
0x1471 : { 0x0188 : "ADSL PCI",
         },
0x148C : { 0x4011 : "RADEON 9000 PRO EVIL COMMANDO",
           0x4152 : "0x2079",
         },
0x148D : { 0x1003 : "Creative ModemBlaster V.90 PCI DI5655",
         },
0x148F : { 0x1000 : "Ralink Motorola BC4 Bluetooth 3.0+HS Adapter",
           0x148f : "TP-LINK 7200ND",
           0x2000 : "Ralink Motorola BC8 Bluetooth 3.0 + HS Adapter",
           0x2070 : "802.11 g WLAN",
           0x2573 : "802.11 bg",
           0x2870 : "802.11 n WLAN",
           0x3000 : "802.11n + Bluetooth 3.0",
           0x3070 : "FreeWifiLink D3-10000N",
           0x3572 : "Ralink 3572",
           0x5370 : "802.11n USB Wireless LAN Card",
           0x9021 : "Netopia USB b/g Adapter (black)",
         },
0x1491 : { 0x0020 : "USB Fingerprint Scanner Model FS80",
           0x0021 : "USB Fingerprint Scanner Model FS80",
         },
0x14A9 : { 0xad1f : "1",
         },
0x14B1 : { 0x1033 : "RH56D-PCI",
           0x2F30 : "zyxel omni 56k CI lus rev.",
         },
0x14B3 : { 0x0000 : "DSL NIC",
         },
0x14B5 : { 0x0200 : "",
           0x0300 : "",
           0x0400 : "",
           0x0600 : "",
           0x0800 : "DSP-Board",
           0x0900 : "DSP-Board",
           0x0A00 : "DSP-Board",
           0x0B00 : "DSP-Board",
         },
0x14B7 : { 0x0001 : "pci9052",
         },
0x14B9 : { 0x0001 : "werwerwerwe",
           0x0340 : "Cisco Systems 340 PCI Wireless LAN Adptr",
           0x2500 : "Wireless PCI LAN Adapter",
           0x3100 : "Wireless PCI LAN Adapter",
           0x3101 : "Wireless PCI LAN Adapter",
           0x3500 : "Wireless PCI LAN Adapter",
           0x4500 : "Wireless PCI LAN Adapter",
           0x4800 : "Wireless PCI LAN Adapter",
           0xA504 : "Cisco Aironet 350 Series Mini-PCI (MPI350)",
           0xA506 : "802.11b/g wireless adapter",
         },
0x14C1 : { 0x8043 : "MyriNet",
         },
0x14C8 : { 0x0003 : "0",
         },
0x14CD : { 0x03 : "0x0200",
         },
0x14CF : { 0x2920 : "Serial I/O Controller aka FPMC-DFLEX64",
         },
0x14D4 : { 0x0400 : "Interface chip",
         },
0x14D9 : { 0x0010 : "Sturgeon HyperTransport-PCI Bridge",
         },
0x14DB : { 0x2100 : "download drivers",
           0x2101 : "",
           0x2102 : "",
           0x2110 : "OX16PCI952",
           0x2111 : "",
           0x2112 : "",
           0x2120 : "0701 Parallel Port device",
           0x2121 : "Avlab Technology PCI IO 2P",
           0x2130 : "2 Port PCI Serial Card",
           0x2131 : "pci serial port",
           0x2132 : "",
           0x2140 : "",
           0x2141 : "",
           0x2142 : "",
           0x2144 : "",
           0x2145 : "",
           0x2146 : "",
           0x2150 : "",
           0x2151 : "",
           0x2152 : "",
           0x2160 : "",
           0x2161 : "",
           0x2162 : "",
           0x2180 : "VEN_14DB&DEV_2180&SUBSYS_218014DB&REV_00",
           0x2181 : "Avlab Technology Inc",
           0x2182 : "Avlab Technology Inc",
         },
0x14DC : { 0x0000 : "",
           0x0001 : "4-port high speed RS-232",
           0x0002 : "8-port high speed RS-232",
           0x0003 : "2-port high speed RS-232",
           0x0004 : "2-port high speed RS-422/485",
           0x0005 : "2-port high speed RS-232 and RS-422/485",
           0x0006 : "16-channel analog input (with timers)",
           0x0007 : "16-chan 12-bit analog output (w/ timers)",
           0x0008 : "4-chan 16-bit analog output (w/ timers)",
           0x0009 : "24-channel digital I/O",
           0x000A : "72-channel digital I/O",
           0x000B : "48-channel digital I/O (w/ 6 timers)",
           0x000C : "16-channel reed relay output",
         },
0x14E4 : { 0x0038 : "100G packet processor ",
           0x0102 : "Intel (R)",
           0x0318 : "n/a",
           0x034F : "???",
           0x04B5 : "Broadcom 54bg Wireless",
           0x0732 : "2x40G/8x10G MAC Aggregation Switch with 80G Uplink",
           0x0800 : "Sentry5 Chipcommon I/O Controller",
           0x0804 : "Sentry5 PCI Bridge",
           0x0805 : "Sentry5 MIPS32 CPU",
           0x0806 : "Sentry5 Ethernet Controller",
           0x080B : "Sentry5 Crypto Accelerator",
           0x080F : "Sentry5 DDR/SDR RAM Controller",
           0x0811 : "Sentry5 External Interface",
           0x0816 : "Sentry5 MIPS32 CPU",
           0x1234 : "networkcontroller",
           0x1361 : "Ethernet",
           0x14E4 : "802.11b/g Wireless Lan Controller",
           0x1600 : "NetXtreme BCM5752 Gigabit Ethernet PCI Express",
           0x1601 : "NetXtreme Desktop/Mobile",
           0x1610 : "Broadcom BCN70010 Video Decoder",
           0x1612 : "Crystal HD Video Decoder",
           0x1615 : "Broadcom Crystal HD Video Decoder",
           0x161F : "AVC/VC-1/MPEG PCI Express HD Decoder Chipset for Netbooks/Nettops",
           0x1639 : "NetXtreme Gigabit Ethernet II",
           0x163B : "Broadcom NetXtreme II BCM5706/5708/5709/5716 Driver",
           0x1644 : "ven_1102dev_0004",
           0x1645 : "broadtcomBCM5701 Gigabit EthernetASD",
           0x1646 : "NetXtreme Gigabit Ethernet",
           0x1647 : "NetXtreme Gigabit Ethernet",
           0x1648 : "NetXtreme Dual Gigabit Adapter",
           0x164C : "Broadcom NetXtreme II Gigabit Ethernet Adapter",
           0x164D : "NetXtreme Fast Ethernet Controller",
           0x1650 : "Broadcom PCIe 10Gb Network Controller ",
           0x1653 : "Broadcom NetXtreme Gigabit Ethernet",
           0x1654 : "NetXtreme Gigabit Ethernet",
           0x1658 : "NtXtreme Gigabit Ethernet",
           0x1659 : "NetXtreme Gigabit Ethernet PCI Express",
           0x165A : "Broadcom NetXtreme BCM5722 Gigabit",
           0x165D : "Broadcom NetXtreme Gigabit Ethernet",
           0x165E : "NetXtreme Gigabit Ethernet",
           0x165F : "Broadcom NetXtreme 5720 Gigabit Ethernet",
           0x166a : "Broadcom NetXtreme Gigabit Ethernet 5780",
           0x166B : "NetXtreme Gigabit Ethernet",
           0x166D : "NetXtreme Ethernet 100kB",
           0x166E : "NetXtreme Gigabit Ethernet",
           0x167 : "NetXtreme Fast Ethernet Controller",
           0x1672 : "NetXtreme Gigabit Ethernet",
           0x1673 : "NetXtreme Gigabit Ethernet",
           0x1674 : "57XX Series Broadcom Driver X86/X64",
           0x1676 : "NetXtreme Gigabit Ethernet",
           0x1677 : "NetXtreme Desktop/Mobile",
           0x1677 : "Broadcom NetExtreme Gigabit Ethernet",
           0x167A : "Broadcom NetXtreme Gigabit Ethernet Controller",
           0x167B : "NetXtreme Gigabit Ethernet",
           0x167C : "NetXtreme Gigabit Ethernet",
           0x167d : "Broadcom NetXtreme Gigabit Ethernet",
           0x167E : "vierkant",
           0x1680 : "NetXtreme Desktop/Mobile",
           0x1681 : "Broadcom 57XX Gigabit Integrated Controller ",
           0x1684 : "Broadcom NetXtreme Gigabit Ethernet",
           0x1690 : "NexTreme Desktop/Mobile",
           0x1691 : "Broadcom BCM57788 LOM ",
           0x1691 : "Broadcom NetLink (TM) Gigabit Ethernet",
           0x1692 : "NetLink",
           0x1693 : "Ethernet Controller Broadcom Netlink Gigabit",
           0x1696 : "Broadcom NetXtreme Gigabit Ethernet ",
           0x1698 : "NetLink-FOR DELL LAPTOP AND MAYBE OTHERS",
           0x169A : "Broadcom Netlink (TM) gigabit ethernet Driver",
           0x169B : "NetXtreme Gigabit Ethernet",
           0x169C : "Broadcom NetLink (TM) Gigabit Ethernet",
           0x169D : " BCM5789",
           0x169E : "NetXtreme Gigabit Ethernet PCI Express",
           0x16A6 : "Gigabit Ethernet",
           0x16A7 : "Gigabit Ethernet",
           0x16A8 : "NetXtreme Gigabit Ethernet",
           0x16AA : "BroadCom NetExtreme II Server",
           0x16B1 : "BCM57781",
           0x16B5 : "Broadcom NetLink Gigabit Ethernet",
           0x16BE : "CardReader Broadcom 1.0.0.221",
           0x16BF : "CardReader Broadcom 1.0.0.221",
           0x16C6 : "NetXtreme Gigabit Ethernet",
           0x16C7 : "DELL Wireless 1390 WLAN MiniCard",
           0x16DD : "NetXtreme Gigabit Ethernet",
           0x16f7 : "NetXtreme BCM5753 Gigabit PCI Express",
           0x16FD : "NetXtreme Gigabit Ethernet PciXpress",
           0x16FE : "NetXtreme Gigabit Ethernet",
           0x170C : "Broadcom 440x 10/100 Integrated Controller",
           0x170D : "NetXtreme",
           0x170E : "NetXtreme 100Base-TX",
           0x1713 : "Broadcom NetLink (TM) Fast Ethernet",
           0x333 : "16p 1G (PHY)",
           0x3352 : "BCM3352 QAMLink Single-Chip 4-Line VoIP",
           0x3360 : "Advanced PHY Broadband Gateway Cable Modem",
           0x4211 : "10Mb/s NIC",
           0x4212 : "56k Modem",
           0x4301 : "Dell Truemobile 1180 802.11g MiniPCI",
           0x4303 : "BCM4301 802.11b802.11b Wireless LAN Controller",
           0x4305 : "V.90 56k Modem",
           0x4306 : "Unknown device 4306 (rev 02)",
           0x4307 : "802.11b Wireless LAN Controller",
           0x4310 : "BCM4301 802.11bChipcommon I/O Controller",
           0x4311 : "Wireless LAN BroadCom",
           0x4312 : "broadcom wireless 1490 (dell)",
           0x4313 : "wireless network card",
           0x4315 : "Broadcom Wireless b/g (Tested Drivers)",
           0x4318 : "Broadcom 802.11b/g",
           0x4320 : "802.11B/G Wireless Lan Controller Revision 3",
           0x4321 : "802.11a Wireless LAN Controller",
           0x4322 : "UART",
           0x4323 : "V.90 56k Modem",
           0x4324 : "802.11a/b/g Wireless LAN",
           0x4325 : "802.11b/g Wireless LAN Controller",
           0x4326 : "Chipcommon I/O Controller?",
           0x4328 : "Broadcom BCM43xx 1.0 (5.10.91.27)",
           0x4329 : "Broadcom 802.11n Network Adapter",
           0x432B : "Broadcom Wireless LAN Driver ",
           0x4353 : "Broadcom Half Mini PCI Express Wifi card / DL1520",
           0x4357 : "Broadcom WiFi 802.11b/g/n",
           0x4358 : "Broadcom 802.11n WLAN module",
           0x4359 : "Half-mini wireless-N card DW1530",
           0x4365 : "Broadcom 43142 Wireless LAN Adapter",
           0x4401 : "10/100 Integrated Ethernet Controller",
           0x4402 : "10/100 Integrated Ethernet Controller",
           0x4403 : "V.90 56k Modem",
           0x4410 : "iLine32 HomePNA 2.0",
           0x4411 : "V.90 56k Modem",
           0x4412 : "10/100BaseT Ethernet",
           0x4430 : "CardBus iLine32 HomePNA 2.0",
           0x4432 : "CardBus 10/100BaseT Ethernet",
           0x4610 : "Sentry5 PCI to SB Bridge",
           0x4611 : "Sentry5 iLine32 HomePNA 1.0",
           0x4612 : "Sentry5 V.90 56k Modem",
           0x4613 : "Sentry5 Ethernet Controller",
           0x4614 : "Sentry5 External Interface",
           0x4615 : "Sentry5 USB Controller",
           0x4704 : "Sentry5 PCI to SB Bridge",
           0x4708 : "Crypto Accelerator",
           0x4710 : "Sentry5 PCI to SB Bridge",
           0x4711 : "Sentry5 iLine32 HomePNA 2.0",
           0x4712 : "Sentry5 V.92 56k modem",
           0x4713 : "Sentry5 Ethernet Controller",
           0x4714 : "Sentry5 External Interface",
           0x4715 : "Sentry5 USB Controller",
           0x4716 : "Sentry5 USB Host Controller",
           0x4717 : "Sentry5 USB Device Controller",
           0x4718 : "Sentry5 Crypto Accelerator",
           0x4720 : "MIPS CPU",
           0x4726 : "01",
           0x4727 : "Broadcom 802.11g Network Adapter BCM4313",
           0x4728 : "01",
           0x5334 : "16P 1G  (PHY)",
           0x5365 : "Sentry5 PCI to SB Bridge",
           0x5600 : "StrataSwitch 24+2 Ethernet Switch Controller",
           0x5605 : "StrataSwitch 24+2 Ethernet Switch Controller",
           0x5615 : "StrataSwitch 24+2 Ethernet Switch Controller",
           0x5625 : "StrataSwitch 24+2 Ethernet Switch Controller",
           0x5645 : "StrataSwitch 24+2 Ethernet Switch Controller",
           0x5670 : "8-Port 10GE Ethernet Switch Fabric",
           0x5680 : "G-Switch 8-Port Gigabit Ethernet Switch Controller",
           0x5690 : "12-port Multi-Layer Gigabit Ethernet Switch",
           0x5691 : "GE/10GE 8+2 Gigabit Ethernet Switch Controller",
           0x5802 : "The BCM5802 Security Processor integrates Broadcoms IPSec engine (DES",
           0x5805 : "The BCM5805 Security Processor integrates a high-performance IPSec engine (DES",
           0x5820 : "Crypto Accelerator",
           0x5821 : "Crypto Accelerator",
           0x5822 : "Crypto Accelerator",
           0x5823 : "Crypto Accelerator",
           0x5824 : "Crypto Accelerator",
           0x5825 : "BCM5825",
           0x5840 : "Crypto Accelerator",
           0x5841 : "Crypto Accelerator",
           0x5850 : "Crypto Accelerator",
           0x7321 : "network card integrated",
           0x7411 : "High Definition Video/Audio Decoder",
           0x7865 : "Wireless-N WLAN",
           0x8010 : "Next generation router SOC with gigabit switch",
           0x8011 : "Next generation router SOC with gigabit switch",
           0x8012 : "Next generation router SOC with gigabit switch",
           0x8016 : "Next generation router SOC with gigabit switch with RGMII/SDIO",
           0x8018 : "Next generation router SOC with gigabit switch with RGMII/SDIO",
           0x8019 : "Next generation router SOC with gigabit switch without RGMII/SDIO",
           0x8022 : "Next generation router SOC with gigabit switch with RGMII/SDIO",
           0x8023 : "Next generation router SOC with gigabit switch with SATA instead of RGMII/SDIO",
           0x8025 : "Next generation router SOC with gigabit switch with RGMII/SDIO",
           0x8334 : "24 1G",
           0x8342 : "8 1G (PHY)",
           0x8344 : " 24P 1G +4P 1G  (PHY)",
           0x8346 : "24P 1G +4P 1G/10G  (PHY)",
           0x8393 : "14P (1G",
           0x8394 : "10P 1G + 4x1/2.5/5/10G  (no PHY) ",
           0x9867 : "900000000",
           0x9876 : "0x14E4",
           0xA8D6 : "Broadcom 802.11n WLAN chip",
           0xB150 : "Hurricane2 (Lightly Managed) 24P 1G +4P 1G/10G  (PHY)",
           0xb152 : "24P  1G (PHY)",
           0xB340 : "48-port multi-layer switch with embedded CPU",
           0xB450 : "100G Multi-layer Ethernet Switch",
           0xB640 : "260Gbps Extensible Switch with 100GE",
           0xB845 : "640G Multi-layer Ethernet Switch",
           0xB850 : "1.28T I/O Multi-layer Ethernet Switch",
           0x4311 : "subsys",
         },
0x14EA : { 0xAB06 : "XFNW-3603-T",
         },
0x14EB : { 0x0020 : "PCI to S5U13xxxB00B Bridge Adapter",
           0x0C01 : "Embedded Memory Display Controller",
         },
0x14EC : { 0x16BE : "1.0.0.222_W7x86_A",
         },
0x14F1 : { 0x0F00 : "cx11252-11",
           0x0F30 : "0x14F1",
           0x1031 : "332",
           0x1033 : "RH56D",
           0x1033 : "RH56D",
           0x1035 : "R6795-11",
           0x1036 : "Conexant RH56D/SP-PCI",
           0x1056 : "4-1b359d48-0-10f06",
           0x1059 : "DI15630-5",
           0x10B4 : "Conextant HFC",
           0x10B6 : "unknown",
           0x1416 : "",
           0x1456 : "1456",
           0x14F1 : "0x14F1",
           0x1611 : "?",
           0x1612 : "8",
           0x2013 : "0x56",
           0x2400 : "unknown",
           0x2702 : "cx11252-11",
           0x2710 : "",
           0x2740 : "CC_0780",
           0x2B10 : "0x14F1",
           0x2BFA : "0x0000ffff",
           0x2C06 : "136",
           0x2F00 : "00101767",
           0x2f01 : "0x0780",
           0x2F10 : "USR90-12",
           0x2F20 : "CX11256",
           0x2F30 : "CX11252-41z",
           0x2F30 : "01",
           0x2F40 : "200014F1",
           0x2F50 : "99269",
           0x2F52 : "C0220001",
           0x2F81 : " ",
           0x2F82 : "cx9510-11z",
           0x5045 : "4.0.3.1",
           0x5045 : "14f12f30",
           0x5045 : "14e4",
           0x5045 : "PCIVEN_14F1&DEV_5047",
           0x5047 : "Not sure",
           0x5051 : "4.0.1.6",
           0x5051 : "DG31PR",
           0x5051 : "CX20561",
           0x5066 : "Cx20561",
           0x5069 : "20585",
           0x506C : "0x506C",
           0x506E : "001",
           0x50A1 : "CX20641/CX20651",
           0x50A2 : "Conexant CX20642",
           0x5B7A : "Belived to be a CX23416",
           0x8800 : "Conexant CX23881",
           0x8800 : "0x14F1",
           0x8801 : "CX23880",
           0x8802 : "CX2388x",
           0x8811 : "CX2388x",
           0x8852 : "cx23885",
           0x8880 : "CX23888",
           0x9876 : "PCIVEN_14F1&DEV_2F20&SUBSYS_200F14F1&REV_004&1AF",
           0x27d8 : "A62516F3",
         },
0x14F2 : { 0x0001 : "",
           0x0002 : "",
           0x0120 : "win7_rtm.090713-1255",
           0x0121 : "",
           0x0122 : "unknown",
           0x0123 : "6.1.7600.16385",
           0x0124 : "3103",
         },
0x14F5 : { 0x2F00 : "x",
         },
0x14FD : { 0x0001 : "H260u printer server for HP Printer",
         },
0x1507 : { 0x0001 : "",
           0x0002 : "",
           0x0003 : "",
           0x0100 : "",
           0x0431 : "",
           0x4801 : "",
           0x4802 : "",
           0x4803 : "",
           0x4806 : "",
         },
0x1516 : { 0x0800 : "10/100 Mbps Fast Ethernet Controller",
           0x0803 : "PCI Ethernet controller",
           0x0891 : "10/100/1000 Mbps Gigabit Ethernet Controller",
         },
0x1519 : { 0x0020 : "HSIC Device",
           0x2004 : "PCI Interface bus",
         },
0x151A : { 0x1002 : "4341",
           0x1004 : "",
           0x1008 : "",
         },
0x151B : { 0x9080 : "combox cb 300a",
         },
0x151D : { 0x9876 : "?",
         },
0x151F : { 0x0001 : "TOPIC FM-56PCI-TP",
           0x0568 : "56k Internal Data Fax Voice Modem",
         },
0x1522 : { 0x0100 : "PCI Interface Chip",
         },
0x1523 : { 0x8 : "Content Addressable Memory",
         },
0x1524 : { 0x0751 : "pci",
           0x0100 : "ENE CIR Receiver",
           0x0510 : "PCI Memory Card Reader Controller",
           0x0530 : "Memory Stick Card Reader",
           0x0550 : "Secure Digital Card Reader",
           0x0551 : "ven1524&dev_0551&SUBSYS_009F1025&REV_01",
           0x0555 : "ven1524&dev_0551&SUBSYS_009F1025&REV_01",
           0x0610 : "PCI Smart Card Reader Controller",
           0x0730 : "CardBus Controller",
           0x100 : "ENE CIR Receiver",
           0x1025 : "PCIVEN_127a&DEV_1025&SUBSYS_1025123A&REV_014&1351887D&0&58F0",
           0x1211 : "CardBus Controller",
           0x1225 : "CardBus Controller",
           0x1410 : "CardBus Controller",
           0x1411 : "pci device",
           0x1412 : "Cardbus Controller",
           0x1420 : "CardBus Controller",
           0x1421 : "CardBus Controller",
           0x1422 : "CardBus Controller",
           0x510 : "PCI Memory Card Reader Controller",
           0x551 : "ven1524&dev_0551&SUBSYS_009F1025&REV_01",
           0x9876 : "1941",
           0xFC10 : "pci device",
         },
0x152D : { 0x2329 : "J micron JM20329",
         },
0x152E : { 0x2507 : "0",
         },
0x1538 : { 0x0301 : "Tekram DC200 PATA100 RAID Controller",
           0x0303 : "ARS0304S PATA133 RAID5",
         },
0x153B : { 0x1115 : "IC Ensemble Inc ICE1712 Envy24 Multichannel Audio Controller",
           0x1143 : "Philips Semiconductors SAA7134HL Multimedia Capture Device",
           0x6003 : "CrystalClear SoundFusion PCI Audio Accel",
         },
0x153F : { 0xdead : "xx12345",
         },
0x1540 : { 0x9524 : "PAL/SECAM TV card w/ FM1216ME MK3 tuner (+FM radio)",
         },
0x1543 : { 0x1052 : "Modem Intel 537EP (Chipset KAIOMY)",
           0x3052 : "Modem Intel 537EP (Chipset KAIOMY)",
           0x3155 : "Modem Device on High Definition Audio Bus",
         },
0x1549 : { 0x80FF : "PCI/ISA Bus Bridge",
         },
0x154A : { 0x9016 : "USB DVB-T Device AF9015",
           0x9876 : "USB DVB-T Device  CE950081",
         },
0x154B : { 0x3038 : "USB",
         },
0x1555 : { 0x0002 : "Easylon PCI Bus Interface",
         },
0x1556 : { 0x5555 : "an cpci application",
         },
0x1558 : { 0x1558 : "gtx 670mx GPU",
         },
0x155E : { 0x0020 : "Multi Function Card Version 3",
         },
0x1562 : { 0x0001 : "LA-41x3",
           0x0002 : "LA-5030",
           0x0003 : "LA-5033",
         },
0x156A : { 0x5000 : "Wideband Advanced Signal Processor",
           0x5100 : "High Data Rate Radio",
         },
0x1571 : { 0xA001 : "GHB",
           0xA002 : "ARCnet",
           0xA003 : "ARCnet",
           0xA004 : "ARCnet",
           0xA005 : "ARCnet",
           0xA006 : "ARCnet",
           0xA007 : "ARCnet",
           0xA008 : "ARCnet",
           0xA009 : "5 Mbit ARCnet",
           0xA00A : "5 Mbit ARCnet",
           0xA00B : "5 Mbit ARCnet",
           0xA00C : "5 Mbit ARCnet",
           0xA00D : "5 Mbit ARCnet",
           0xA00E : "ARCNET",
           0xA201 : "10 Mbit ARCnet",
           0xA202 : "10 Mbit ARCnet",
           0xA203 : "10 Mbit ARCnet",
           0xA204 : "10 Mbit ARCnet",
           0xA205 : "10 Mbit ARCnet",
           0xA206 : "10 Mbit ARCnet",
         },
0x157C : { 0x8001 : "PCI Y2K Compliance Card",
         },
0x1584 : { 0x5054 : "VAS Vetronix Automotive Service",
           4003 : "VAS Vetronix Automotive Service",
         },
0x1586 : { 0x0803 : "",
         },
0x1588 : { 0x1100 : "PAX.ware 1100 dual Gb classifier engine",
           0x2000 : "SNP 8023 packet classifier - AMD component",
           0x8023 : "PAX.ware 100 packet classifier",
         },
0x158B : { 0x0005 : "Standar HSP Modem",
           0x0015 : "Standar HSP Modem Series",
         },
0x1592 : { 0x0781 : "Multi-IO Card",
           0x0782 : "Parallel Port Card (EPP)",
           0x0783 : "Multi-IO Card",
           0x0785 : "Multi-IO Card",
           0x0786 : "Multi-IO Card",
           0x0787 : "Multi-IO Card 2 series",
           0x0788 : "Multi-IO Card",
           0x078A : "Multi-IO Card",
         },
0x15A2 : { 0x0001 : "PCI Bus Analyzer/Exerciser",
         },
0x15AD : { 0x0405 : "VMWare Player 3.1.6 Software Driver",
           0x0710 : "Virtual SVGA",
           0x0720 : "VMware PCI Ethernet Adapter",
           0x0740 : "VMWare VMCI Bus Device",
           0x0770 : "Standard Enhanced PCI to USB Host Controller",
           0x0778 : "Sabrent USB-to-Parallel Adapter",
           0x07B0 : "VMware vSphere 4 PCI Ethernet Adapter",
           0x0801 : "PCI Memory Controller",
           0x1975 : "High Definition Audio Codec",
           0x1977 : "High Definition Audio Controller",
         },
0x15B0 : { 0x0001 : "Pctel",
           0x0003 : "Pctel",
           0x2BD0 : "soft56k voice",
         },
0x15B3 : { 0x5274 : "InfiniBridge",
           0x5A44 : "InfiniHost I",
           0x6274 : "InfiniHost III Lx",
           0x6278 : "InfiniHost TM III Ex",
           0x6282 : "MT25218 [InfiniHost III Ex]",
           0x634A : "Mellanox ConnectX VPI (MT2548) - PCIe 2.0 2.5GT/s",
           0x6732 : "ConnectX VPI (MT26418) - PCIe 2.0 5GT/s",
         },
0x15B8 : { 0x3009 : "Analog output board",
         },
0x15BC : { 0x0101 : "DX2+ FC-AL Adapter",
           0x0103 : "4 Port Fibre Channel Controller",
           0x1200 : "Agilent QX4 Fibre Channel Controller",
           0x2530 : "HP Communications Port",
           0x2531 : "HP Toptools Remote Control Adapter",
           0x2532 : "HP Toptools Remote Control Adapter",
           0x2929 : "PCI/PCI-X Bus Analyzer",
         },
0x15C2 : { 0x0038 : "part of the iMon-IR-RC-Display-Kit",
         },
0x15D1 : { 0x0001 : "TriCore 32-bit Single-chip Microctrlr",
           0x0003 : "6 Port Optimized Comm Ctrlr (SPOCC)",
           0x0004 : "Infineon Technologies AG",
           0x000B : "TPM",
         },
0x15D7 : { 0x56 : "hcf 56",
         },
0x15D8 : { 0x9001 : "",
         },
0x15D9 : { 0x9876 : "4567",
         },
0x15DC : { 0x0001 : "PCI Cryptography Module",
         },
0x15DD : { 0x7664 : "idt high audio",
           0x7680 : "SIGMATEL STAC 92XX C-Major HD Audio",
           0x769 : "9200 HD  ",
           0x7690 : "You'll Love me 4 this/ visit http://wendhelofopportunity.info Support Me!",
           0x8384 : "Intel Audio Studio",
           0x9876 : "1",
         },
0x15E0 : { 0x7134 : "01",
         },
0x15E2 : { 0x0500 : "Internet PhoneJack PCI Card",
         },
0x15E6 : { 0x0000 : "v.90 Lucent Modem",
         },
0x15E7 : { 0x755 : "NTDS Parallel Adapter",
         },
0x15E8 : { 0x0130 : "Wireless NIC",
           0x0131 : "InstantWave HR PCI card",
         },
0x15E9 : { 0x1841 : "ATA controller",
         },
0x15EF : { 0x0028 : "SigmaTelHigh Definition Audio CODEC",
           0x24c5 : "VIA-Vynil v700b",
           0x7616 : "SigmaTelHigh Definition Audio CODEC",
         },
0x15F1 : { 0x2F30 : "Conexant HSFi",
         },
0x15F2 : { 0x0001 : "Spot RT",
           0x0002 : "Spot RT #2",
           0x0003 : "Spot Insight",
         },
0x160A : { 0x3184 : "Via VT6656 Wireless Lan Adapter",
         },
0x1616 : { 0x0409 : "16-Bit",
         },
0x1619 : { 0x0400 : "Two Port Intelligent Sync Comms Card",
           0x0440 : "Four Port Intelligent Sync Comms Card",
           0x0610 : "One Port Intelligent Sync Comms Card",
           0x0620 : "Two Port Intelligent Sync Comms Card",
           0x0640 : "Four Port Intelligent Sync Comms Card",
           0x1610 : "One Port Intelligent Sync Comms Card",
           0x1612 : "One Port Intelligent Sync Comms Card",
           0x2610 : "G.SHDSL Intelligent Sync Comms Card",
           0x3640 : "Four Port Intelligent Sync Comms Card",
           0x4620 : "Two Port Intelligent Sync Comms Card",
           0x4640 : "Four Port Intelligent Sync Comms Card",
           0x5621 : "Two Port Intelligent Sync Comms Card",
           0x5641 : "Four Port Intelligent Sync Comms Card",
           0x6620 : "Two Port Intelligent Sync Comms Card",
         },
0x1621 : { 0x0020 : "4 in/4 out Professional Digital Audio Card",
           0x0021 : "2 in/6 out Professional Digital Audio Card",
           0x0022 : "6 in/2 out Professional Digital Audio Card",
           0x0023 : "2 in/2 out Professional Digital Audio Card",
           0x0024 : "16 in/16 out AES/EBU Audio Card",
           0x0025 : "16 in/16 out AES/EBU Audio Card w/SRC",
         },
0x1629 : { 0x1003 : "Format Synchronizer v3.0",
           0x2002 : "Fast Universal Data Output",
         },
0x162D : { 0x0100 : "Repeographics controller",
           0x0101 : "Reprographics Controller",
           0x0102 : "Reprographics Controller",
           0x0103 : "Reprographics Controller",
         },
0x162F : { 0x1111 : "General Purpose Relay Card",
           0x1112 : "Matrix Card",
         },
0x1638 : { 0x1100 : " WL11000P",
         },
0x163B : { 0x2416 : "DVR Video Capture Card 16CH",
         },
0x163C : { 0x3052 : "RS56/HSP-PCI",
           0xFF02 : "PCI Bridge - 244E",
         },
0x164F : { 0x0001 : "PCI interface chip",
           0x0002 : "PCI interaface chip",
         },
0x1657 : { 0x0646 : "Brocade 400 series PCIe HBA",
         },
0x1658 : { 0x0704 : "DIG 704 PCI - Interface with Millisecond Timer and Interrupts",
         },
0x165A : { 0xC100 : "PCI camera link video capture board",
           0xD200 : "PCI digital video capture board",
           0xD300 : "PCI digital video capture board",
           0xF001 : "PCI-E camera link video capture board",
         },
0x165C : { 0x0002 : "FT232BL",
         },
0x165F : { 0x2000 : "16 Channel Audio Capture Card",
         },
0x1668 : { 0x0100 : "PCI to PCI Bridge",
         },
0x166D : { 0x0001 : "",
           0x0002 : "MIPS BCM1125/BCM1250 processors",
         },
0x1676 : { 0x1001 : "Realtek AC' 97 Audio Driver",
         },
0x1677 : { 0x20ad : "Profibus DP / K-Feldbus / COM",
         },
0x167F : { 0x4634 : "FOB-IO Card",
           0x4C32 : "L2B PCI Board",
           0x5344 : "FOB-SD Card",
           0x5443 : "FOB-TDC Card",
           0xF0B2 : "ibaFOB-2io-D",
           0xF0B4 : "ibaFOB-4io-D",
         },
0x1681 : { 0x0050 : "Hercules WiFi PCI 802.11G",
         },
0x1682 : { 0x9875 : "",
         },
0x1688 : { 0x0013 : "",
         },
0x168C : { 0x001c : "pciven_10ac&dev_ooo",
           0x0002 : "Atheros AR5B95 Wireless LAN 802.11 a/b/g/n Controller",
           0x0003 : "TP-LINK 450Mbps Wireless N Adapter",
           0x0007 : "Wireless Network Adapter",
           0x0011 : "11a/b/g Wireless LAN Mini PCI Adapter",
           0x0012 : " PCIVEN_1217&DEV_7130&SUBSYS_FF501179&REV_01 DELL Latitude C510 as mini-PCI board behind the larg",
           0x0013 : "Netgear RangeMax WPN311 PCI Wireless NIC",
           0x0019 : "802.11a Wireless Adapter",
           0x001A : "http://support1.toshiba-tro.de/tools/updates/atheros-wlan/atheros-wlan-xp-7702331.zip",
           0x001B : "802.11abg NIC",
           0x001c : "Wireless Network Adapter",
           0x001C : "Atheros AR5BXB63 WWAN Chip",
           0x001c : "AR5006EX AR5423a",
           0x001D : "PCIVEN_168C&DEV_002E&SUBSYS_E034105B&REV_014&124A40C8&0&00E1",
           0x002 : "the drivers for this device are not installed",
           0x0023 : "802.11a/b/g/n&#1041;&#1077;&#1089;&#1087;&#1088;&#1086;&#1074;&#1086;&#1076;&#1085;&#1086;&#1081; PC",
           0x0024 : "Atheros 802.11a/b/g/n",
           0x0027 : "Atheros AR5B95 Wireless LAN 802.11 a/b/g/n Controller",
           0x002A : "Atheros AR5B91",
           0x002B : "Atheros AR5B195 ",
           0x002C : "Wireless 802.11 a/b/g/n Dualband Network Adapter (PCI-Express)",
           0x002D : "802.11b/g/n",
           0x002E : "Atheros ar9285 PCI Capabilities:  Offset ID Description ",
           0x0030 : "Killer Wireless - N",
           0x0032 : "Atheros AR9485",
           0x0034 : "802.11a/b/g/n",
           0x0037 : "Atheros AR1111 WB-EG Wireless Network Adapter",
           0x003e : "1",
           0x007 : "Wireless Network Adapter",
           0x0280 : "PCIVEN_168C&DEV_002B&SUBSYS_30AF185F",
           0x032 : "Dell Wireless DW1703 802.11b/g/n",
           0x1014 : "Atheros AR5212 802.11abg wireless Drivers",
           0x14F1 : "PCIVEN_168C&DEV_001A&SUBSYS_04181468&REV_014&FCF0450&0&10A4",
           0x168C : "PCIVEN_168C",
           0x1a3b : "802.11a/b/g/n Wireless PCI Adapte",
           0x3002 : "Bluetooth 3.0",
           0x6666 : "Atheros AR5B95 Wireless LAN 802.11 a/b/g/n Controller",
           0x9876 : "Atheros AR5B95 Wireless LAN 802.11 a/b/g/n Controller",
           0xFF1B : "Wireless LAN G",
           0xFF96 : "LAN-Express AS IEEE 802.11g miniPCI adapter",
         },
0x1693 : { 0x0212 : "EPONINE ESR-PCI Board",
           0x0213 : "EPONINE MTM120 PCI Board",
         },
0x16AE : { 0x000A : "Crypto Accelerator",
           0x1141 : "Crypto Accelerator",
         },
0x16CA : { 0x0001 : "Solid State Disk",
         },
0x16EC : { 0x0116 : "RealTek 8169S chip",
           0x0303 : "U.S. Robotics 56K FAX USB V1.1.0 /  V.92 USB modem",
           0x1007 : "U.S. Robotics 56K Win INT",
           0x2013 : "U.S. Robotics 56K Voice Host Int",
           0x2F00 : "http://www.usr.com/support/product-template.asp?prod=5660a",
           0x2f12 : "U.S.Robotic (A- Modem/PCI)",
           0x3685 : "Wireless Access Adapter Model 022415",
           0x5685 : "U.S. Robotics 56K Voice Host Int (A-Modem/ PCI)",
         },
0x170B : { 0x0100 : "Crypto Aceletator",
         },
0x1710 : { 0x5812 : "itech numeric small keyboard",
           0x9835 : "2 serial",
         },
0x1712 : { 0x3038 : "usb",
           0x7130 : "unknown",
         },
0x1725 : { 0x7174 : "VSC7174 PCI/PCI-X SATA Controller",
         },
0x1734 : { 0x007a : "ATI Rage XL (rev 27)",
           0x1011 : "Adaptec AIC-7902 Dual Channel U320 SCSI",
           0x1012 : "Serverworks Southbridge with RAID/IDE (rev a0)",
           0x1013 : "Broadcom Corp. NetXtreme Gigabyte Ethernet",
           0x10b9 : "SAS 3000 series",
         },
0x1737 : { 0x0071 : "Dual Band Wireless N USB Network Adapter",
           0x1032 : "Linksys Instant Gigabit Desktop Network Interface",
         },
0x173B : { 0x03E8 : "Gigabit Ethernet Adapter",
           0x03EA : "Gigabit Ethernet Adapter",
         },
0x1743 : { 0x8139 : "Fast Ethernet Adapter with ROL",
         },
0x174B : { 0x0260 : "Saphire Radeon 9250",
           0x0261 : "Sapphire Radeon 9250 - Secondary",
           0x7176 : "RADEON 9000 ATLANTIS PRO",
           0x7177 : "RADEON 9000 ATLANTIS PRO - Secondary",
           0x7244 : "Sapphire ATI  X1950 XT",
           0x7C12 : "RADEON 9200 ATLANTIS - Secondary",
           0x7C13 : "RADEON 9200 ATLANTIS",
           0x9501 : "ATI Radeon HD 3450",
           0xE106 : "Graphics Chipset	ATI Radeon HD 4300/4500 Series       	",
           0xe131 : "ATI 4870",
           0xE140 : "Sapphire HD 5870 1GB GDDR5",
         },
0x1753 : { 0x1001 : "VP500",
           0x1004 : "VP1000",
         },
0x1755 : { 0x000 : "",
           0x0000 : "Au1500 Processor",
         },
0x17A1 : { 0x0128 : "USB2.0 JPEG WebCam ",
         },
0x17AA : { 0x7145 : "Mobility ATI Radeon X1400",
         },
0x17AF : { 0x4150 : "200",
           0x7291 : "RV560",
         },
0x17C0 : { 0x12ab : "intel",
         },
0x17CC : { 0x1978 : "usb 2.0 device controller",
           0x2280 : "USB 2.0 Device Controller",
         },
0x17D5 : { 0x5831 : "Xframe 10GbE PCI-X Adapter",
           0x5832 : "Xframe II 10GbE PCI-X 2.0 Adapter",
           0x5833 : "E3100 PCI-Express 10Gb Ethernet Interface",
         },
0x17E9 : { 0x02a7 : "USB VGA/DVI Adapter UV-D4A1-B",
         },
0x17EE : { 0x4153 : "RV350",
         },
0x17F3 : { 0x1010 : "D1010",
           0x1011 : "D1011",
           0x1030 : "M1030",
           0x2010 : "M2010",
           0x3010 : "M3010",
           0x6021 : " ",
           0x6036 : " ",
           0x6040 : "R6040x",
           0x6060 : " modem",
           0x6061 : " V90479. 1",
         },
0x17FE : { 0x2220 : "Generic IEEE 802.11b/g Wireless LAN Card",
         },
0x1813 : { 0x3059 : "AC97 Enhanced Audio Controller - the 8251 controller is different",
           0x4000 : "intel V.92 HaM Modem",
           0x4100 : "Intel HaM V.92 Modem",
         },
0x1814 : { 0x0001 : "...B742000",
           0x0101 : "2460  802.11b",
           0x0201 : "PCIVEN_1814&DEV_3090&SUBSYS_1451033",
           0x0201 : "RT 3070",
           0x0201 : "001167F044E5",
           0x0201 : "RT2560F",
           0x0201 : "WMP54G",
           0x0301 : "RT2561",
           0x0301 : "RT2561",
           0x0302 : "RT2525 2.4GHz transceiver + RT2560 MAC/BBP",
           0x0401 : "RT 2661",
           0x0601 : "RT2860T",
           0x0701 : "RT2860T",
           0x0781 : "RT2790T/RT2860/RT2890/RT2700E",
           0x1418 : "0x14FI",
           0x14F1 : "0x1814",
           0x201 : "25601814&REV_01",
           0x3060 : "RT3060",
           0x3090 : "Ralink RT3090",
           0x3290 : "RT3290",
           0x3298 : "-",
           0x3592 : "RT3592",
           0x5360 : "RT5360 ",
           0x5390 : "RT5390",
           0x539B : "RT5390R",
           0x9876 : "b8341462",
         },
0x186C : { 0x1014 : "Atheros 802.11abg",
         },
0x1888 : { 0x0301 : "",
           0x0601 : "",
           0x0710 : "",
           0x0720 : "",
           0x2503 : "Video Capture (10 bit High qualtiy cap)",
           0x2504 : "Video Capture",
           0x3503 : "VGA Geforce4 MX440",
           0x3505 : "VGA Geforce4 Ti4200",
         },
0x18C9 : { 0x1011 : "Video processor",
           0x1012 : "Video processor",
           0x1013 : "Video processor",
           0x1014 : "Video processor",
           0x1015 : "Video processor",
           0x1016 : "Video processor",
           0x2011 : "Framegrabber",
           0x2012 : "Framegrabber",
           0x2013 : "Framegrabber",
           0x2014 : "Framegrabber",
           0x2015 : "Framegrabber",
           0x2016 : "Framegrabber",
           0x2017 : "Framegrabber",
           0x2021 : "Framegrabber",
           0x3011 : "Video Output Board",
         },
0x18CA : { 0x0020 : "Volari Z series (Select GPU Graphic Drivers",
           0x0040 : "Volari Family Z Series",
         },
0x18F7 : { 0x0001 : "ESCC-PCI-335",
           0x0002 : "422/4-PCI-335",
           0x0004 : "422/2-PCI-335",
           0x000a : "232/4-PCI-335",
         },
0x1904 : { 0x2031 : "controladora ethernet",
           0x8139 : "Realtek RTL8139 PCI Fast Ethernet Adapter",
           0x8139 : "Realtek RTL8139 PCI Fast Ethernet Adapter",
         },
0x1910 : { 0x0001 : "Seaway Network Content Accelerator",
         },
0x1912 : { 0x0014 : "usb3.0 renesas",
           0x0015 : " nec",
           0x0015 : "Renesas Electronics USB 3.0 Host Controller",
         },
0x1969 : { 0x1026 : "PCI-E ETHERNET CONTROLLER ",
           0x1048 : "Gigabit Ethernet 10/100/1000 Base-T Controller",
           0x1060 : "PCI-E Fast Ethernet Controller",
           0x1062 : "Atheros AR8132 PCI-E &#1050;&#1086;&#1085;&#1090;&#1088;&#1086;&#1083;&#1083;&#1077;&#1088; Fast Eth",
           0x1062 : "Gigabit Ethernet 10/100/1000 Base-T Controller",
           0x1063 : "Atheros AR8131 PCI-E Gigabit Ethernet Controller",
           0x1073 : "Atheros AR81512 ",
           0x1083 : "Atheros AR8151 PCI-E Gigabit Ethernet Controller (NDIS 6.20)",
           0x1090 : "Fast Ethernet",
           0x1091 : "PCI-E Gigabit Ethernet Controller",
           0x168c : "Gigabit Ethernet 10/100/1000 Base-T Controller ",
           0x1969 : "Gigabit Ethernet 10/100/1000 Base-T  ",
           0x2048 : "Fast Ethernet 10/100 Base-T Controller",
           0x2049 : "der",
           0x2060 : "AR8152 v1.1 Fast Ethernet",
           0x2061 : "Ethernet Controller",
           0x2062 : "Qualcomm Atheros AR8152/8158",
           0x4747 : "VEN_1969",
           0x9876 : "Fast Ethernet 10/100 Base-T Controller ",
         },
0x1971 : { 0x0001 : "PCIVEN_1971&DEV_0000&SUBSYS_00021028&REV_004&2",
           0x1011 : "PCIVEN_1971&DEV_1011&CC_FF00",
           0x1021 : "",
         },
0x197B : { 0x0250 : "JMC250 PCI Express",
           0x0256 : "JMC260 PCI Express Fast Ethernet",
           0x0260 : "JMC260 PCI Express Fast Ethernet",
           0x1234 : "1234567",
           0x197b : "JMB38X SD/MMC Host Controller ",
           0x2360 : "JMB36X",
           0x2361 : "PCI Express to SATA II and PATA Host Controller",
           0x2363 : "JMicron JMB362/JMB363 AHCI Controller",
           0x2366 : "JMicron JMB366 AHCI/IDE Controller",
           0x2368 : "IDE Comtroller",
           0x2380 : "IEEE 1394 Host Controller",
           0x2381 : "JMB38X SD Host Controller",
           0x2382 : "JMB38X SD/MMC Host Controller  ftp://driver.jmicron.com.tw/CardReader/Windows/",
           0x2383 : "JMB38X MS Host Controller",
           0x2384 : "JMB38X xD Host Controller",
           0x2391 : "Intel",
           0x2392 : " JMB38X SD/MMC Host Controller",
           0x7002 : "JMB38X SD/MMC Host Controller",
         },
0x198a : { 0x0210 : "XMC-210",
           0x0220 : "XMC-220",
           0x0230 : "XMC-230",
           0x0240 : "XMC-240",
           0x1180 : "PCIe-180",
           0x1280 : "PCIe-280",
           0x198a : "PCIe-180",
           0x402F : " BenNUEY PCIX",
           0x4030 : "H100-PCIX",
           0x4031 : "BenNUEY PCI-104-V4",
           0x4032 : "BenONE-PCIe",
           0x4033 : "BenONE-Xilinx-Kit-ROHS",
           0x4034 : "BenNUEY PCIX RoHS",
         },
0x19a2 : { 0x0710 : "Emulex OneConnect 10Gb NIC (be3) (rev01)",
           0x0712 : "Emulex OneConnect 10Gb iSCSI Initiator (be3) (rev 01)",
           0x0714 : "Emulex OneConnect 10Gb FCoE Initiator (be3) (rev 02)",
         },
0x19AC : { 0x0001 : "Crypto Accelerator",
         },
0x19B6 : { 0x110c : "Atheros chipset for 802.11a/b/g",
         },
0x19E3 : { 0x5801 : "DDRdrive X1",
           0x5808 : "DDRdrive X8",
           0xDD52 : "DDRdrive X1-30",
         },
0x1B13 : { 0x0001 : "nVidia Corporation NV17",
         },
0x1B21 : { 0x1041 : "USB 3.0 Host Controller Driver for Windows 7",
           0x1042 : "Asmedia ASM104x USB 3.0 Host Controller",
         },
0x1B6F : { 0x7023 : "Etron USB 3.0 Extensible Host Controller",
         },
0x1B73 : { 0x1000 : "PCIVEN_1000&DEV_0020&SUBSYS_10301000&REV_01PCIVEN",
           0x1100 : "USB 3.0 eXtensibile Host controller",
         },
0x1c39 : { 0x0300 : "Pegasus Board PCI-e interface",
         },
0x1DE1 : { 0x0045 : "Tekram SAS860 Embedded 8xSAS/SATAII RAID",
           0x0058 : "Tekram Elrond 8xSAS/SATAII RAID",
           0x0391 : "SCSI ASIC",
           0x2020 : "SCSI Controller",
           0x690C : "IDE Cache Controller",
           0xDC29 : "Bus Master IDE PCI 2 controllers",
         },
0x2001 : { 0x3C19 : "USB <=> Wireless N 150 Adapter",
           0xF103 : ".",
         },
0x2646 : { 0x0001 : "22323",
           0x2646 : "22323",
         },
0x3388 : { 0x0020 : "Universal PCI-PCI Bridge (transparent mode)",
           0x0021 : "ZS095A0",
           0x0022 : "PCI-PCI Bridge",
           0x0026 : "Universal PCI-PCI Bridge (transparent mode)",
           0x0028 : "Dual Mode PCI-X-to-PCI-X Bridge (transparent mode)",
           0x0029 : "Dual Mode PCI-X-to-PCI-X Bridge (non-transparent mode)",
           0x0030 : "Transparent PCI-X-to-PCI-X Bridge",
           0x0031 : "Synchronous 32-Bit",
           0x8011 : "CPU to PCI Bridge",
           0x8012 : "PCI to ISA Bridge",
           0x8013 : "EIDE Controller",
         },
0x3D3D : { 0x0001 : "GLint 300SX",
           0x0002 : "GLint 500TX",
           0x0003 : "GLint",
           0x0004 : "3C0SX",
           0x0005 : "Permedia",
           0x0006 : "GLint MX",
           0x0007 : "3D Extreme",
           0x0008 : "GLint Gamma G1",
           0x0009 : "Permedia2v",
           0x000A : "8086",
           0x000C : "Permedia 3",
           0x000D : "GLINT R4",
           0x000E : "GLINT Gamma G2",
           0x0020 : "0x0024",
           0x0030 : "0x030000",
           0x0100 : "Permedia II",
           0x1004 : "Permedia",
           0x3D04 : "Permedia",
           0x3D07 : "same as above?  I have no idea",
           0xFFFF : "GLint VGA",
         },
0x4005 : { 0x0300 : "PCI Audio Device",
           0x0308 : "PCI Audio Device + modem",
           0x0309 : "PCI Input Controller",
           0x1064 : "GUI Accelerator",
           0x2064 : "GUI Accelerator",
           0x2128 : "GUI Accelerator",
           0x2301 : "GUI Accelerator",
           0x2302 : "GUI Accelerator",
           0x2303 : "GUI Accelerator",
           0x2364 : "GUI Accelerator",
           0x2464 : "GUI Accelerator",
           0x2501 : "GUI Accelerator",
           0x4000 : "Audio Chipset",
         },
0x4144 : { 0x0040 : "Virtex-E Bridge",
           0x0041 : "Virtex-II Bridge",
           0x0042 : "Virtex-II Bridge",
           0x0043 : "Virtex-II Pro Bridge",
           0x0044 : "Virtex-II Pro PCI/PCI-X Bridge",
           0x0045 : "Virtex-II Bridge",
           0x0046 : "Virtex-II Bridge",
           0x0049 : "Virtex-II Pro PCI",
           0x004A : "Virtex-II Pro PCI-X Bridge",
           0x004F : "Virtex-II Pro PCI-X Bridge",
           0x0050 : "Virtex-4LX Bridge",
           0x0051 : "ADM-XRC-5T1",
           0x0052 : "Xilinx Virtex 5 PMC",
           0x0056 : "Virtex 5 AMC FPGA board",
           0x0057 : "Xilinx Virtex 5 FPGA PMC ",
           0x0058 : "VXS FPGA and PMC Carrier Board",
           0x005B : "ADM-XRC-5T2 with JPEG 2000 devices",
           0x005C : "FPGA PMC with Analog I/O Interface",
           0x005F : "As per XRC-5T2 but with 6 JPEG2000 devices",
           0x0300 : "Xilinx Virtex 6 FPGA XMC",
           0x0301 : "Xilinx Virtex 6 FPGA XMC",
           0x0303 : "Full lenght PCI Express Xilinx Virtex-6 FPGA platform",
           0x0305 : "Full length PC Card Xilinx Virtex-6 FPGA platform",
         },
0x416C : { 0x0100 : "Puerto paralelo PCI",
           0x0200 : "",
         },
0x4348 : { 0x1453 : "WCH353L",
           0x3253 : "SIE9835 PCI=>DUAL SERIAL",
           0x5053 : "5050",
           0x7173 : " CH35X",
         },
0x4C53 : { 0x0000 : "Diagnostics Device",
           0x0001 : "Diagnostics Device",
         },
0x4D51 : { 0x0200 : "",
         },
0x4E8 : { 0x618d : "epic 4g smartphone (GT B5330)",
         },
0x5053 : { 0x2010 : "Daytona Audio Adapter",
         },
0x5136 : { 0x4678 : "S S Technologies",
         },
0x5143 : { 0x9204 : "WAN Card Lenovo Notebook",
         },
0x5333 : { 0x0551 : "86C551",
           0x5333 : "S3 86c765",
           0x5631 : "86C325",
           0x8800 : "86C866",
           0x8801 : "86C964",
           0x8810 : "86C732-P",
           0x8811 : "8622mcq04",
           0x8812 : "86CM65?",
           0x8813 : "86C764",
           0x8814 : "86C767",
           0x8815 : "86CM66",
           0x883D : "86C988",
           0x8870 : "Fire GL",
           0x8880 : "86C868",
           0x8881 : "86C868",
           0x8882 : "86C868",
           0x8883 : "86C868",
           0x88B0 : "86C928",
           0x88B1 : "86C928",
           0x88B2 : "86C928",
           0x88B3 : "86C928",
           0x88C0 : "86C864",
           0x88C1 : "86C864",
           0x88C2 : "86C864",
           0x88C3 : "86C864",
           0x88D0 : "86C964",
           0x88D1 : "86C964",
           0x88D2 : "86C964",
           0x88D3 : "86C964",
           0x88F0 : "86C968",
           0x88F1 : "86C968",
           0x88F2 : "86C968",
           0x88F3 : "86C968",
           0x8900 : "86C775",
           0x8901 : "pciven_5333dev_8C2E&SUBSYS_00011179&REV_054&74C6",
           0x8902 : "86C551",
           0x8903 : "",
           0x8904 : "86C365/366",
           0x8905 : "86c765",
           0x8906 : "86c765",
           0x8907 : "86c765",
           0x8908 : "9711 MCN74",
           0x8909 : "7699688",
           0x890A : "0x00091011",
           0x890B : "9726 c19394.00",
           0x890C : "86C765",
           0x890D : "86C765 Trio64V+ compatible",
           0x890E : "9711 MCN74",
           0x890F : "86c765",
           0x8A01 : "86C375/86C385",
           0x8A10 : "86C357",
           0x8A11 : "86C359",
           0x8A12 : "86C359",
           0x8A13 : "86C368",
           0x8A20 : "86C391",
           0x8A21 : "86C390",
           0x8A22 : "86c398",
           0x8A23 : "86C394-397",
           0x8A25 : "86C370",
           0x8A26 : "86C395B",
           0x8C00 : "85C260",
           0x8C01 : "86C260",
           0x8C02 : "86C240",
           0x8C03 : "86C280",
           0x8C10 : "86C270/274/290/294",
           0x8C12 : "86C270/274/290/294",
           0x8C13 : "82C294",
           0x8C22 : "86C508",
           0x8C2A : "86C544",
           0x8C2B : "86C553",
           0x8C2C : "86C564",
           0x8C2D : "86C573",
           0x8C2E : "86C584",
           0x8C2F : "86C594",
           0x8D01 : "86C380/381",
           0x8D02 : "86c387",
           0x8D04 : "86C410",
           0x8E00 : "86C777/787",
           0x8E01 : "86C732",
           0x9102 : "86c410",
           0x9876 : "86C390",
           0xCA00 : "86C617",
         },
0x544C : { 0x0350 : "IAM",
         },
0x5555 : { 0x0003 : "Digital Video OEM computer module",
         },
0x5853 : { 0x0001 : "n/a",
           0x0002 : "n/a",
         },
0x6666 : { 0x0001 : "PCCOM4",
           0x0002 : "PCCOM8",
         },
0x7d1 : { 0x3304 : "802.11N usb wifi device",
           0x3c03 : "Same chipset of RALINK  RT2500",
           0x3C07 : "PCIVEN_1799&DEV_700F&SUBSYS_700F1799&REV_203&61AAA01&0&48",
         },
0x8080 : { 0x1040 : "VIA 82C259 rev 0",
         },
0x8086 : { 0x27B8 : "Intel(R) 82801GB/GR (ICH7 Family) LPC Interface Controller",
           0x0008 : "Extended Express System Support Ctrlr",
           0x0011 : "Ethernet Controller",
           0x0042 : "Intel Q57/H55 Clarkdale (Onboard on D2912-A1x)",
           0x0046 : "Intel Graphics Media Accelerator HD",
           0x0054 : "Audio",
           0x0082 : "Centrino Advanced-N 6205 ",
           0x0083 : "Intel PROSet/Wireless Software and Drivers for Windows 7 32-Bit",
           0x0084 : "Intel Wireless Link WiFi 1000",
           0x0085 : "Intel Centrino(R) Advanced-N 6205",
           0x0087 : "00E1",
           0x008A : "Intel Centrino Wireless-N1030",
           0x008B : "Intel(R) Centrino(R) Wireless-N 1030 ",
           0x0091 : "Intel Centrino Advanced-N 6230",
           0x0102 : "Intel HD Graphics 2000",
           0x0106 : "2nd Generation Intel Core Processors with Intel HD Graphics 3000/2000",
           0x010A : "Lenovo TS130 Intel Video Adapter HD",
           0x0111 : "Intel Graphics Conroller",
           0x0116 : "Intel HD Graphics 3000",
           0x0123 : "hardwareids",
           0x0162 : " Core I7",
           0x0166 : "3rd Generation Intel HD Graphics 4000",
           0x0189 : "Intel Centrino Wireless Bluetooth 3.0 + High Speed Adapter",
           0x027A : "Mobile Intel(R) 945 Express Chipset Family",
           0x027D : "Mobile PCI-to-PCIsdsdsdI2)",
           0x0283 : "Intel(R) ICH8 Family SMBus Controller",
           0x0308 : "PCI Audio Device + modem",
           0x0309 : "I/O Processor PCI-to-PCI Bridge Unit",
           0x030D : "I/O Companion Unit PCI-to-PCI Bridge",
           0x0318 : "General Purpose PCI Processor Address Translation Unit",
           0x0319 : "General Purpose PCI Processor Address Translation Unit",
           0x0326 : "I/OxAPIC Interrupt Controller",
           0x0327 : "I/OxAPIC Interrupt Controller B",
           0x0329 : "PCI Express-to-PCI Express Bridge A",
           0x032A : "PCI Express-to-PCI Express Bridge B",
           0x032C : "PCI Express-to-PCI Express Bridge",
           0x0330 : "A-Segment Bridge",
           0x0331 : "A-Segment IOAPIC",
           0x0332 : "B-Segment Bridge",
           0x0333 : "B-Segment IOAPIC",
           0x0334 : "Address Translation Unit",
           0x0335 : "PCI-X Bridge",
           0x0336 : "Address Translation Unit (ATU)",
           0x0340 : "Serial to Parallel PCI Bridge A",
           0x0341 : "Serial to Parallel PCI Bridge B",
           0x0370 : "Segment-A PCI Express-to-PCI Express Bridge",
           0x0371 : "A-Bus IOAPIC",
           0x0372 : "Segment-B PCI Express-to-PCI Express Bridge",
           0x0373 : "B-Bus IOAPIC",
           0x0374 : "Address Translation Unit",
           0x0401 : "P040100",
           0x0402 : "intel core i5",
           0x0482 : "PCI-EISA Bridge (PCEB)hp dx 7300 microwave tower",
           0x0483 : "CPU (i486) Bridge (Saturn)",
           0x0484 : "SIO ISA Bridge",
           0x0486 : "1261028",
           0x04A3 : "Mercury/Neptune Cache/DRAM Controller",
           0x0500 : "Processor Bus Controller",
           0x0501 : "Memory Controller",
           0x0502 : "Scalability Port 0",
           0x0503 : "Scalability Port 1 / Glob. Perf. Monitor",
           0x0510 : "Hub Interface Port 0 (8-bit compatible)",
           0x0511 : "Hub Interface Port 2",
           0x0512 : "Hub Interface Port 2",
           0x0513 : "Hub Interface Port 3",
           0x0514 : "Hub Interface Port 4",
           0x0515 : "Server I/O Hub (SIOH)",
           0x0516 : "Reliabilty",
           0x0530 : "Scalability Port 0",
           0x0531 : "Scalability Port 1",
           0x0532 : "Scalability Port 2",
           0x0533 : "Scalability Port 3",
           0x0534 : "Scalability Port 4",
           0x0535 : "Scalability Port 5",
           0x0536 : "Scalability Port Switch Global Registers",
           0x0537 : "Interleave Configuration Registers",
           0x0600 : "Storage RAID Controller",
           0x0780 : "Intel B75 Express Chipset",
           0x0800 : "pci/ven_8086&dev_27da&subsys_30b2103c&rev_023&b1bfb68&0&fb",
           0x0885 : "Intel Centrino Wireless-N + WiMAX 6150",
           0x0887 : "Intel Centrino Wireless-N 2230",
           0x0888 : "Intel Centrino Wireless-N 2230",
           0x088E : "Intel Centrino Advanced N 6235",
           0x0890 : "Network Controller",
           0x0894 : "MRMgRH",
           0x0896 : "Intel Centrino Wireless-N 130",
           0x08AE : "Intel Centrino Wireless-N 100",
           0x0960 : "i960 RP Microprocessor/Bridge",
           0x0962 : "i960RM/RN Microprocessor/Bridge",
           0x0964 : "i960 RP Microprocessor Bridge",
           0x0BE1 : "Intel Graphics Media Accelerator 3600 Series",
           0x0C05 : "Intel(R) 6 Series/C200 Series Chipset Family SMBus Controller",
           0x1000 : "Gigabit Ethernet Controller",
           0x1001 : "10/100/1000 Ethernet Controller (Fiber)",
           0x1002 : "Pro 100 LAN+Modem 56 CardBus II",
           0x1004 : "Gigabit Ethernet Controller (Copper)",
           0x1008 : "Gigabit Ethernet Controller (Copper)",
           0x1009 : "Intel",
           0x100C : "Gigabit Ethernet Controller (Copper)",
           0x100D : "Gigabit Ethernet Controller (LOM)",
           0x100E : "Intel Pro 1000/MT",
           0x100F : "Gigabit Ethernet Controller (copper)",
           0x1010 : "Dual Port Gigabit Ethernet Controller (Copper)",
           0x1011 : "Gigabit Ethernet Controller (Fiber)",
           0x1012 : "Dual Port Gigabit Ethernet Controller (Fiber)",
           0x1013 : "Gigabit Ethernet Controller (Copper)",
           0x1014 : "Gigabit Ethernet Controller",
           0x1015 : "Gigabit Ethernet Controller (LOM)",
           0x1016 : "Gigabit Ethernet Controller (LOM)",
           0x1017 : "Gigabit Ethernet Controller (LOM)",
           0x1018 : "PRO/1000 MT Mobile connection",
           0x1019 : "Gigabit Ethernet Controller (LOM)",
           0x101A : "Gigabit Ethernet Controller (LOM)",
           0x101d : "Dual Port Gigabit Ethernet Controller",
           0x101E : "Gigabit Ethernet Controller (Mobile)",
           0x1026 : "Gigabit Ethernet Controller",
           0x1027 : "Gigabit Ethernet Controller (Fiber)",
           0x1028 : "Gigabit Ethernet Controller",
           0x1029 : "Fast Ethernet PCI/CardBus Controller",
           0x1030 : "PCI Networking device",
           0x1031 : "PRO/100 VE Network Connection",
           0x1032 : "PRO/100 VE Network Connection",
           0x1033 : "multimedia video controller",
           0x1034 : "PRO/100 VM Network Connection",
           0x1035 : "Phoneline Network Connection",
           0x1036 : "Phoneline Network Connection",
           0x1037 : "LAN Controller",
           0x1038 : "PRO/100 VM/KM Network Connection",
           0x1039 : " 82562",
           0x103A : "LAN Controller with 82562ET/EZ (CNR) PHY",
           0x103B : "LAN Controller with 82562EM/EX PHY",
           0x103C : "LAN Controller with 82562EM/EX (CNR) PHY",
           0x103D : "PRO/100 VE Network Connection",
           0x103E : "PRO/100 VM Network Connection",
           0x1040 : "V.92 PCI (DSP) Data Fax Modema",
           0x1042 : "PRO/Wireless 2011 LAN PCI Card",
           0x1043 : "Intel(R) PRO/Wireless 2100 LAN Card Driver",
           0x1048 : "10 Gigabit Ethernet Controller",
           0x1049 : "Gigabit Network Connection Interface Controller",
           0x104A : "gigabit ethernet",
           0x104B : "Gigabit Ethernet",
           0x104D : "Intel Gigabit 82566MC",
           0x1050 : "PRO/100 VE Network Connection",
           0x1051 : "PRO/100 VE Network Connection",
           0x1052 : "PRO/100 VM Network Connection",
           0x1053 : "PRO/100 VM Network Connection",
           0x1054 : "PRO/100 VE Network Connection (mobile)",
           0x1055 : "PRO/100 VM Network Connection (mobile)",
           0x1059 : "Fast Ethernet PCI/CardBus Controller",
           0x105E : "HP NC360T PCIe DP Gigabit Server Adapter",
           0x1064 : "82562EZ PLC",
           0x1065 : "LAN Controller Intel Corporation 82562ET/EZ/GT/GZ - PRO/100 VE Ethernet Controller",
           0x1068 : "1068h 82562ET/EZ/GT/GZ PRO/100 VE Ethernet Controller",
           0x1075 : "Gigabit Ethernet Controller",
           0x1076 : "Gigabit Ethernet Controller",
           0x1077 : "Gigabit Ethernet Controller (Mobile)",
           0x1078 : "Gigabit Ethernet Controller",
           0x1079 : "Dual Port Gigabit Ethernet Controller",
           0x107A : "Dual Port Gigabit Ethernet Controller (Fiber)",
           0x107B : "Dual Port Gigabit Ethernet Controller (Copper)",
           0x107C : "Gigabit Ethernet Controller (Copper) rev 5",
           0x1080 : "FA82537EP - Intel 537EP V.92 (PCI)  modem",
           0x108B : "Intel network controller (PCIE Gigabit Ethernet)",
           0x108c : "Intel Corporation 82573E Gigabit Ethernet Controller (Copper)",
           0x108E : "Intel(R) Active Management Technology - KCS",
           0x108F : "Intel(R) Active Management Technology - SOL",
           0x1092 : "PRO/100 VE Network Controller",
           0x1094 : "get PRO2KXP.exe from Intel",
           0x1096 : "Intel PRO/1000 EB",
           0x109A : "Intel PRO/1000 PL Network Adaptor",
           0x109c : "HP E1Q Express",
           0x10a7 : "82575EB Gigabit Network Connection",
           0x10a9 : "82575EB Gigabit Backplane Connection",
           0x10b5 : "Quad Port Gigabit Ethernet Controller",
           0x10b9 : "Intel PRO/1000 PT Desktop",
           0x10BD : "Intel 82566DM Gigabit Ethernet Adapter",
           0x10C0 : "Intel(R) 82562V-2 10/100 Network Connection",
           0x10c4 : "Intel 82562GT 10/100 Network Controller",
           0x10c4 : "Intel 82562GT 10/100 Network Controller",
           0x10c9 : "82576 Gigabit ET Dual Port Server Adapter",
           0x10CE : "Intel 82567V-2 Gigabit Network Connection",
           0x10d3 : "Intel 82574L Gigabit Ethernet Controller",
           0x10d6 : "82566 DM-2-gigabyte",
           0x10DE : "Intel Gigabit network connection",
           0x10e6 : "82576 Gigabit Network Connection",
           0x10e7 : "82576 Gigabit Network Connection",
           0x10E8 : "E64750-xxx Intel Gigabit ET Quad Port Server Adapter",
           0x10EA : "Intel 82577LM Gigabit LAN Driver ",
           0x10EC : "Realtek 171 High Definition Audio",
           0x10EF : "Intel 82578DM Gigabit Ethernet Controller",
           0x10F0 : "Intel(R) 82578DC Gigabit NIC",
           0x10F5 : "Intel  82567LM-2 Gigabit Network Connection",
           0x10fb : "10 Gb Ethernet controller",
           0x1100 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x1101 : "AGP Bridge",
           0x1102 : "Internal Graphics Device",
           0x1110 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x1112 : "Internal Graphics Device",
           0x1120 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x1121 : "AGP Bridge",
           0x1130 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x1131 : "AGP Bridge",
           0x1132 : "Internal Graphics Device [810/815 chipset AGP]",
           0x1161 : "I/O APIC Device",
           0x1162 : "XScale 80200 Companion Chip (FPGA)",
           0x1179 : "Dual Port Gigabit Ethernet Controller",
           0x12 : "00",
           0x1200 : "Network Processor",
           0x1209 : "Fast Ethernet Controller for xp pc",
           0x1221 : "PCMCIA Bridge",
           0x1222 : "IDE Ctrlr",
           0x1223 : "Audio Controller",
           0x1225 : "Orion Extended Express CPU to PCI Bridge",
           0x1226 : "EtherExpress PRO/10",
           0x1227 : "LAN Controller with 82562EM",
           0x1228 : "Intelligent 10/100 Fast Ethernet Adapter",
           0x1229 : "Intel(R) PRO/100 M 00000Desktop Adapter   http://downloadmirror.intel.com/8659/eng/LAN_ALLOS_11.2_PV",
           0x122D : "System Controller (TSC)",
           0x122E : "PCI to ISA Bridge (Triton)",
           0x1230 : "IDE Interface (Triton)",
           0x1231 : "DSVD Modem",
           0x1234 : "PCI to ISA Bridge",
           0x1235 : "Mobile System Controller (MTSC)",
           0x1237 : "PCI & Memory",
           0x1239 : "IDE Interface (Triton)",
           0x123B : "PCI to PCI Docking Bridge",
           0x123C : "Mobile PCI-to-ISA Bridge (MISA)",
           0x123D : "Programmable Interrupt Device",
           0x123E : "Integrated Hot-Plug Controller (IHPC)",
           0x123F : "Integrated Hot-Plug Controller (IHPC)",
           0x1240 : "AGP Graphics Accelerator",
           0x124B : "Mobile PCI-to-PCIsdsdsdI2)",
           0x124B : "Mobile PCI-to-PCIsdsdsdI2)",
           0x124C : "Mobile PCI-to-PCI Bridge (MPCI2)",
           0x1250 : "System Controller (TXC)",
           0x12D8 : "SIGMATEL STAC 92XX C-Major HD Audio",
           0x1360 : "Hub Interface to PCI Bridge",
           0x1361 : "Advanced Interrupt Controller",
           0x13ca : "VVVVVV",
           0x1460 : "Hub Interface-to-PCI Bridge",
           0x1461 : "I/OxAPIC Interrupt Controller",
           0x1462 : "Hot Plug Controller",
           0x1502 : "Intel 82579LM Gigabit Network Card",
           0x1503 : "Gigabit Network Connection",
           0x150a : "82576NS Gigabit Ethernet Controller",
           0x150C : "Intel 82583V Gigabit Ethernet  Controller",
           0x150d : "82576 Gigabit Backplane Connection",
           0x150e : "82580 Gigabit Network Connection",
           0x150f : "82580 Gigabit Fiber Network Connection",
           0x1510 : "82580 Gigabit Backplane Connection",
           0x1511 : "82580 Gigabit SFP Connection",
           0x1516 : "82580 Gigabit Network Connection",
           0x1518 : "82576NS SerDes Gigabit Network Connection",
           0x1521 : "i350 Gigabit Network Connection",
           0x1525 : "Intel 82567V-4 Gigabit Network Connection",
           0x1526 : "Intel Gigabit ET2 Quad Port Server Adapter",
           0x1533 : "Intel I210 Gigabit Network Connection",
           0x167D : "PCI Simple Communications Controller",
           0x1960 : "i960RP Microprocessor",
           0x1962 : "Promise SuperTrak SX6000 IDE RAID Controller",
           0x1A12 : "Eicon DIVA Server Voice PRI 2.0 (PCI)",
           0x1A13 : "Eicon DIVA Server Voice PRI 2.0 (PCI)",
           0x1A20 : "",
           0x1A21 : "Host-Hub Interface A Bridge / DRAM Ctrlr",
           0x1A22 : "Host to I/O Hub Bridge (Quad PCI)",
           0x1A23 : "AGP Bridge",
           0x1A24 : "Hub Interface B Bridge",
           0x1A30 : "Host-Hub Interface Bridge",
           0x1A31 : "AGP Bridge",
           0x1A38 : "5000 Series Chipset DMA Engine",
           0x1c02 : "sata ahci contoller",
           0x1c02 : "Intel(R) Desktop/Workstation/Server Express Chipset SATA AHCI Controller",
           0x1C03 : "Intel(R) CPT Chipset Family 6 Port SATA AHCI Controller ",
           0x1C22 : "Intel(R) 6 Series/C200 Series Chipset Family SMBus Controller",
           0x1C26 : "USB Enhanced Host Controller",
           0x1c34 : "pci simple communications controller",
           0x1c3a : "Intel Management Engine Interface",
           0x1C3b : "Series Chipset Family HECI Controller #2",
           0x1C3D : "Intel(R) Active Management Technology - SOL",
           0x1C49 : "04",
           0x1D3A : "X79/C600 series chipset Management Engine Interface",
           0x1e00 : "2 ports IDE Controller",
           0x1e08 : "2 ports IDE Controller",
           0x1E12 : "rev",
           0x1E22 : "SM-Bus Controller of the Intel Z77 Chipset",
           0x1e31 : "Intel USB 3.0",
           0x1E3A : "Intel Management Engine Interface (MEI)",
           0x1E3A : "Intel 7 Series/C216",
           0x1E3A : "C216 Chipset - Platform controller hub",
           0x1E3D : "Intel(R) AMT LMS_SOL for AMT 8.xx",
           0x1E59 : "140889",
           0x2000 : "505943621",
           0x2014 : "Framegrabber",
           0x2048 : "Fast Ethernet 10/100 Base-T Controller",
           0x2124 : "PRO/100 VE Network Connection",
           0x2125 : "AC97 Audio Controller. website to download - http://www.intel.com/design/chipsets/manuals/29802801.p",
           0x2222 : "Intel Management Interface",
           0x2255 : "023",
           0x2406 : "AC97 Modem Controller / PCI Modem",
           0x2410 : "LPC Interface",
           0x2411 : "IDE Controller (UltraATA/66)",
           0x2412 : "USB Controller",
           0x2413 : "SMBus Controller",
           0x2415 : "Aureal (AD1881 SOUNDMAX) Placa Me Asaki P3-141",
           0x2416 : "AC'97 Modem Controller",
           0x2418 : "Hub Interface-to-PCI Bridge",
           0x2420 : "LPC Interface",
           0x2421 : "IDE Controller (UltraATA/33)",
           0x2422 : "USB Controller",
           0x2423 : "SMBus Controller",
           0x2425 : "Audio controler",
           0x2426 : "AC97 Modem Controller",
           0x2428 : "Hub Interface-to-PCI Bridge",
           0x2431 : "pci bus",
           0x2440 : "LPC Interface Bridge",
           0x2441 : "IDE Controller (UltraATA/66)",
           0x2442 : "USB Controller",
           0x2443 : "SMBus Controller",
           0x2444 : "USB Controller",
           0x2445 : "AC97 Audio Controller",
           0x2446 : "AC97 Modem Controller",
           0x2448 : "Hub Interface to PCI Bridge",
           0x2449 : "82559ER Integrated 10Base-T/100Base-TX Ethernet Controller",
           0x244A : "IDE Controller",
           0x244B : "IDE Controller",
           0x244C : "LPC Interface Bridge",
           0x244E : "Hub Interface to PCI Bridge",
           0x2450 : "LPC Interface Bridge",
           0x2452 : "USB Controller",
           0x2453 : "SMBus Controller",
           0x2459 : "LAN0 Controller",
           0x245B : "IDE Controller",
           0x245D : "Multimedia Audio Controller",
           0x245E : "Hub Interface to PCI Bridge",
           0x2480 : "LPC Interface Bridge",
           0x2481 : "IDE Controller (UltraATA/66)",
           0x2482 : "USB Controller",
           0x2483 : "SMBus Controller",
           0x2484 : "USB Controller",
           0x2485 : "AC97 Audio Controller",
           0x2486 : "AC 97 Modem Controller",
           0x2487 : "USB Controller",
           0x248A : "UltraATA IDE Controller",
           0x248B : "UltraATA/100 IDE Controller",
           0x248C : "LPC Interface or ISA bridge: see Notes",
           0x248D : "USB 2.0 EHCI Contoroller",
           0x24C0 : "LPC Interface Bridge",
           0x24C2 : "USB UHCI Controller #1",
           0x24C3 : "modem",
           0x24C4 : "USB UHCI Controller",
           0x24C5 : "Realtek AC97",
           0x24C5 : "PCI Simple Communications Controller",
           0x24C5 : "VIA Vynil v700b",
           0x24c5 : "Soundmax Integrated Digital Audio",
           0x24C5 : "Intel 82801 DB DBM/DA AC 97 Audio Controller",
           0x24c5 : "Audio Controller",
           0x24C6 : "AC97 Modem Controller / PCI Modem",
           0x24C7 : "USB UHCI Controller #3",
           0x24CA : "IDE Controller (UltraATA/100)",
           0x24CB : "IDE Controller (UltraATA/100)",
           0x24CC : "LPC Interface Bridge",
           0x24CD : "USB EHCI Controller",
           0x24D0 : "LPC Interface Bridge",
           0x24D1 : "SATA Controller",
           0x24D2 : "USB UHCI Controller 1",
           0x24D3 : "SMBus Controller",
           0x24D4 : "USB UHCI Controller #2",
           0x24D5 : "Realtek AC'97 Sound System Software",
           0x24D6 : "Motorola SM56 Data Fax Modem",
           0x24D7 : "USB UHCI Controller #3",
           0x24DB : "EIDE Controller",
           0x24DC : "LPC Interface Controller",
           0x24DD : "USB EHCI Controller",
           0x24DE : "USB UHCI Controller #4",
           0x24DF : "SATA Controller (RAID)",
           0x2500 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x2501 : "Host Bridge (MCH)",
           0x2502 : "",
           0x2503 : "",
           0x2504 : "",
           0x250B : "Host Bridge (MCH)",
           0x250F : "AGP Bridge",
           0x2520 : "Memory Translator Hub (MTH)",
           0x2521 : "Audio Device on High Definition Audio Bus",
           0x2530 : "Host-Hub Interface Bridge(A2 step)",
           0x2531 : "Host-Hub Interface_A Bridge (DP mode)",
           0x2532 : "AGP Bridge",
           0x2533 : "Hub Interface_B Bridge",
           0x2534 : "Hub Interface_C Bridge",
           0x2535 : "PCI Bridge",
           0x2536 : "PCI Bridge",
           0x2539 : "(Quad Processor mode)",
           0x2540 : "Host-HI Bridge & DRAM Controller",
           0x2541 : "DRAM Controller Error Reporting",
           0x2543 : "HI_B Virtual PCI-to-PCI Bridge",
           0x2544 : "HI_B PCI-to-PCI Bridge Error Reporting",
           0x2545 : "HI_C Virtual PCI-to-PCI Bridge",
           0x2546 : "HI_C PCI-to-PCI Bridge Error Reporting",
           0x2547 : "HI_D Virtual PCI-to-PCI Bridge",
           0x2548 : "HI_D PCI-to-PCI Bridge Error Reporting",
           0x254C : "Host Controller",
           0x2550 : "Host Controller",
           0x2551 : "Host RAS Controller",
           0x2552 : "PCI-to-AGP Bridge",
           0x2553 : "Hub Interface_B PCI-to-PCI Bridge",
           0x2554 : "Hub I/F_B PCI-to-PCI Bridge Error Report",
           0x255d : "Host Controller",
           0x2560 : "DRAM Controller / Host-Hub I/F Bridge",
           0x2561 : "Host-to-AGP Bridge",
           0x2562 : "Integrated Graphics Device",
           0x2562 : "SATA RAID CONTROLLER",
           0x2570 : " 82848P",
           0x2571 : " 82848P",
           0x2572 : "Integrated Graphics Device",
           0x2573 : " 82848P",
           0x2576 : " 82848P",
           0x2578 : "DRAM Controller / Host-Hub Interface",
           0x2579 : "PCI-to-AGP Bridge",
           0x257A : "",
           0x257B : "PCI to CSA Bridge",
           0x257E : "Overflow Configuration",
           0x2580 : "Host Bridge / DRAM Controller",
           0x2581 : " 925X/XE?",
           0x2582 : "82915g/gv/910gl Express Chipset Family",
           0x2582 : "82915g/gv/910gl Express Chipset Family",
           0x2584 : "Host Bridge / DRAM Controller",
           0x2585 : "",
           0x2588 : "Host Bridge/DRAM Controller",
           0x2589 : "PCI Express Bridge",
           0x258A : "Internal Graphics",
           0x2590 : "Mobile Intel(R) 915GM/PM/GMS/910GML Express Processor to DRAM Controller",
           0x2592 : "Graphic controller family",
           0x25A1 : "LPC Interface Bridge",
           0x25A2 : "PATA100 IDE Controller",
           0x25A3 : "SATA Controller(IDE Mode)",
           0x25A4 : "SMBus Controller",
           0x25A6 : "AC'97 Audio Controller",
           0x25A7 : "AC'97 Modem Controller",
           0x25A9 : "USB 1.1 UHCI Controller #1",
           0x25AA : "USB 1.1 UHCI Controller #2",
           0x25AB : "Watchdog Timer",
           0x25AC : "APIC1",
           0x25AD : "USB 2.0 EHCI Controller",
           0x25AE : "Hub Interface to PCI-X Bridge",
           0x25B0 : "Serial ATA Controller (RAID mode)",
           0x2600 : "Hub Interface 1.5",
           0x2601 : "PCI Express Port D",
           0x2602 : "PCI Express Port C0",
           0x2603 : "PCI Express Port C1",
           0x2604 : "PCI Express Port B0",
           0x2605 : "PCI Express Port B1",
           0x2606 : "PCI Express Port A0",
           0x2607 : "PCI Express Port A1",
           0x2640 : "LPC Interface Bridge",
           0x2641 : "LPC Interface Bridge (ICH6-M)",
           0x2651 : "SATA Controller",
           0x2652 : "SATA RAID Controller",
           0x2652 : "SATA Controller",
           0x2652 : "SATA Raid Controller",
           0x2652 : "AHCI Controller",
           0x2653 : "SATA AHCI Controller",
           0x2653 : "SATA IDE Controller",
           0x2653 : "AHCI Controller",
           0x2658 : "USB UHCI Controller #1",
           0x2659 : "USB UHCI Controller #2",
           0x265A : "USB UHCI Controller #3",
           0x265B : "USB UHCI Controller #4",
           0x265C : "USB 2.0 EHCI Controller",
           0x266 : "VIA AC97 codec incorporated into VT82C686VT8251 SouthbridA/B",
           0x2660 : "PCI Express Port 1",
           0x2662 : "PCI Express Port 2",
           0x2664 : "PCI Express Port 3",
           0x2666 : "PCI Express Port 4",
           0x2668 : "82801FB (ICH6) High Definition Audio Controller",
           0x2669 : "jkn ",
           0x266A : "SMBus Controller",
           0x266C : "LAN Controller",
           0x266D : "http://www.dell.com/support/drivers/us/en/19/DriverDetails/DriverFileFormats?DriverId=R104087&FileId",
           0x266E : "VIA AC97",
           0x266F : "PATA100 Controller - 266F",
           0x2670 : "LPC Interface Controller",
           0x2678 : "8280 (ICH6) High Defininition Audio Controller",
           0x2680 : "SATA Controller(IDE Mode)",
           0x2681 : "631xESB/632xESB SATA AHCI Controller",
           0x2682 : "Intel(R) ESB2 SATA RAID Controller",
           0x269B : "SMBus Controller",
           0x269E : "PATA100 IDE Controller",
           0x27 : "ICH7 Family",
           0x2770 : "Host Bridge/DRAM Controller",
           0x2771 : "Host to PCI Express Bridge",
           0x2772 : "Chipset Intel 82945G Express ",
           0x2776 : "INTEL(R) 82945G EXPRESS FAMILY",
           0x277C : "Intel 975X Express Chipset",
           0x2780 : "Graphics device",
           0x2782 : "Graphics device: 82915G/GV/910GL Express Chipset Family",
           0x2792 : "Mobile Intel(R) 915GM/GMS/",
           0x2794 : "Mobile chipset",
           0x27A0 : "i945GM Express Chipset",
           0x27A1 : "Intel Corporation Mobile 945PM Express PCI Express Root Port",
           0x27A2 : "Mobile Intel(R) 945 Express Chipset Family",
           0x27A6 : "Intel 945GM/950",
           0x27B8 : "PCIVEN_8086&_27B8&SUBSYS_8179DEV1043&REV_013&11583659&0&F8",
           0x27BC : "NM10 Family LPC Interface Controller",
           0x27c0 : "82801 GB Serial ATA Storage Controllers",
           0x27C1 : "AHCI Controller",
           0x27c3 : "Raid Controller",
           0x27c4 : "SATA IDE Controller",
           0x27C5 : "AHCI Controller",
           0x27C6 : "Raid Controller",
           0x27c8 : "USB UHCI Controller",
           0x27c9 : "USB UHCI Controller",
           0x27CA : "USB UHCI Controller",
           0x27CB : "USB UHCI Controller",
           0x27CC : "Intel(R) 82801G (ICH7 Family) USB2 Enhanced Host Controller",
           0x27D0 : "Intel(R) 82801G (ICH7 Family) PCI Express Root Port",
           0x27D2 : "Intel(R) 82801G (ICH7 Family) PCI Express Root Port",
           0x27d8 : "Realtek High Definition Audio Driver FF311179 thequetta.com",
           0x27d8 : "Microsoft UAA Bus HD Audio",
           0x27D9 : "IDT High Definition Audio Driver	",
           0x27DA : "Intel[R] 82801G (ICH7 Family) C- 27DA",
           0x27DC : "Intel PRO/100 VE Desktop Adapter",
           0x27DC : "Intel PRO/100 VE Desktop Adapter",
           0x27DE : "AUDIO (ALC850) << Realtek ",
           0x27df : "PATA100",
           0x27 : "no",
           0x2802 : "INTEL(R) HIGH DEFINITION AUDIO HDMI",
           0x2803 : "Intel(R) High Definition Audio HDMI Service",
           0x2804 : "IntcDAudModel",
           0x2815 : "Intel(R) ICH8M LPC Interface Controller - 2815 Driver",
           0x2820 : "SATA IDE Controller:4 port",
           0x2821 : "AHCI Controller",
           0x2822 : "Raid Controller",
           0x2824 : "ICH8 AHCI Controller",
           0x2825 : "Intel Q35",
           0x2828 : "SATA IDE Controller",
           0x2829 : "AHCI Controller",
           0x282A : "Raid Controller",
           0x283A : "ICH8 Enhanced USB2 Enhanced Host Controller",
           0x283E : "SM Bus Controller",
           0x284 : "Microsoft UAA bus for HD audio",
           0x284B : "Microsoft UAA bus for HD audio",
           0x2850 : "PATA Controller",
           0x2880 : "Intel Display Audio",
           0x2888 : "Q945",
           0x2914 : "LPC bridge of ICH9",
           0x2916 : "PCI Simple Communications-Controller ",
           0x2920 : "SATA IDE Controller:4 port",
           0x2921 : "SATA IDE Controller:2 port1",
           0x2922 : "AHCI Controller",
           0x2923 : "ICH9 AHCI Controller",
           0x2925 : "Raid Controller",
           0x2926 : "SATA IDE Controller:2 port2",
           0x2928 : "SATA IDE Controller:2port1",
           0x2929 : "ICH9M/ME AHCI Controller",
           0x292D : "SATA IDE Controller:2port2",
           0x292E : "SATA IDE Controller:1port2",
           0x2930 : "2930",
           0x2930 : "Intel ICH9 Family SMBus Controller",
           0x2936 : "Intel(R) ICH9 Family USB Univeral Host Controller",
           0x293E : "82801IB/IR/IH (ICH9 Family) HD Audio Controller",
           0x293E : "82801IB/IR/IH (ICH9 Family) HD Audio Controller",
           0x294C : "Intel(R) 82566DC-2 Gigabit Network Connection",
           0x2972 : "Onboard Video Device for 82946GZ chips",
           0x2986 : "Intel",
           0x2987 : "Intel PCI Serial Port",
           0x2992 : "Intel(R) Express Chipset video",
           0x2993 : "Intel(R) Express Chipset (Dell Version)",
           0x2994 : "intel management engine interface",
           0x2996 : "IDE Controller",
           0x2997 : "Intel Active Management Technology (AMT) - SOL",
           0x29a0 : "Intel P965/G965 Processor to I/O Controller",
           0x29a1 : " 82G965",
           0x29A2 : "Intel 82G965 Graphics and Memory Controller Hub (GMCH)",
           0x29A4 : "MRMgRH  <a href=",
           0x29A6 : "IDE Controller",
           0x29B2 : "Intel(R) Q35 Express Chipset Family",
           0x29B3 : "Intel",
           0x29B4 : "Intel(R) Management Engine Interface (HECI)",
           0x29B4 : "",
           0x29B6 : "IDE Controller",
           0x29B7 : "Serial Over LAN",
           0x29C2 : "Intel(R) G33 chipset GMA3100 video Driver",
           0x29C2 : "Intel(R) G33 chipset GMA3100 video Driver",
           0x29C4 : "Intel ME: Management Engine Interface",
           0x29C6 : "IDE Controller",
           0x29D4 : "Intel Management Interface",
           0x29D6 : "IDE Controller",
           0x29E6 : "IDE Controller",
           0x29F6 : "IDE Controller",
           0x2A02 : "Intel GM965",
           0x2A03 : "Intel GM",
           0x2A04 : "Intel PCI communication controller-Intel Management Engine Interface update",
           0x2A06 : "IDE Controller",
           0x2A07 : "Intel PCI Serial Port",
           0x2A08 : "Intel(R) Extended Thermal Model MCH",
           0x2A12 : "Mobile Intel(R) 965 Express Chipset Family",
           0x2A16 : "IDE Controller",
           0x2A42 : "Intel Mobile Graphic",
           0x2A43 : "Intel Mobile Graphic",
           0x2A44 : "IC658",
           0x2A46 : "IDE Controller",
           0x2a47 : "Active Management Technology - SOL",
           0x2A52 : "IDE Controller",
           0x2E06 : "IDE Controller",
           0x2E12 : "Intel Q45/Q43 Express Chipset",
           0x2e13 : "Intel(R) 4 Series Internal Chipset",
           0x2E14 : "Intel Management Engine Interface (HECI)",
           0x2E15 : "Intel AMT LMS_SOL for AMT 5.xx",
           0x2E16 : "IDE Controller",
           0x2E17 : "Intel AMT LMS_SOL for AMT 5.xx",
           0x2E24 : "Intel Management Engine Interface",
           0x2E24 : "Intel Management Engine Interface",
           0x2E26 : "IDE Controller",
           0x2e29 : "Intel(R) 4 Series Chipset PCI Express Root Port - 2E29",
           0x2E32 : "Intel G41 express graphics",
           0x2E33 : "ghaphics chipset g41TY",
           0x2E33 : "ghaphics chipset g41 ghaphics chipset g41 ",
           0x2E46 : "IDE Controller",
           0x2E96 : "IDE Controller",
           0x2f00 : "multimedia audio device (codec AC97) SoundMAX or VIA",
           0x3092 : "I2O 1.5 RAID Controller",
           0x3200 : "PCI-X to Serial ATA Controller",
           0x3252 : "SUBSYS",
           0x3340 : "Host-Hub Interface Bridge",
           0x3341 : "AGP Bridge",
           0x3342 : "Power Management",
           0x3408 : "Intel 7500 Chipset PCIe Root Port",
           0x3409 : "Intel 7500 Chipset PCIe Root Port",
           0x340A : "Intel 7500 Chipset PCIe Root Port",
           0x340B : "Intel 7500 Chipset PCIe Root Port",
           0x340C : "Intel 7500 Chipset PCIe Root Port",
           0x340E : "Intel 7500 Chipset PCIe Root Port",
           0x3410 : "Intel 7500 Chipset PCIe Root Port",
           0x3423 : "SRCU21/SRCU31 Microsoft Windows* 2000 Memory Management Files",
           0x3464 : "NTPNP_PCI0002",
           0x348D : "Gigabit Ethernet Controller",
           0x34c5 : "Realtek AC97 (NOT an intel)",
           0x3575 : "Host-Hub I/F Bridge / SDRAM Controller",
           0x3576 : "Host-AGP Bridge",
           0x3577 : "Integrated Graphics Device",
           0x3578 : "CPU to I/O Bridge",
           0x3579 : "SDRAM Controller / Host-hub Interface",
           0x357B : "Integrated Graphics Device",
           0x3580 : "Host-Hub Interface Bridge",
           0x3581 : "Virtual PCI to AGP Bridge",
           0x3582 : "Integrated Graphics Device",
           0x3584 : "System Memory Controller",
           0x3585 : "Configuration Process",
           0x3590 : "Memory Controller Hub",
           0x3591 : "Memory Controller Hub",
           0x3592 : "Memory Controller Hub",
           0x3593 : "MCH Error Reporting Registers",
           0x3594 : "DMA Controller Registers",
           0x3595 : "PCI Express Port A",
           0x3596 : "PCI Express Port B",
           0x3597 : "PCI Express Port B",
           0x3598 : "PCI Express Port B1",
           0x3599 : "PCI Express Port C",
           0x359A : "PCI Express Port C1",
           0x359B : "Extended Configuration Registers",
           0x359E : "MCH Control Registers",
           0x360B : "intel simple communication controller",
           0x3A00 : "ICH10 4 port SATA IDE Controller",
           0x3A02 : "ICH10D SATA Controller",
           0x3A03 : "ICH10 AHCI",
           0x3A05 : "ICH10D SATA Controller",
           0x3A06 : "SATA2(2Port1)",
           0x3A14 : "82801JDO ICH10DO",
           0x3A1A : "82801JD ICH10D",
           0x3A20 : " SATA2(4Port2)",
           0x3A22 : "AHCI Controller",
           0x3A23 : "ICH10 AHCI",
           0x3A26 : "SATA2(2Port2)",
           0x3A30 : "INTEL(R) ICH10 Family SMB controller ",
           0x3A3E : "Microsoft UAA Bus Driver for High Definition Audio",
           0x3a60 : "SM-Bus Controller",
           0x3B00 : "LPC Interface Controller",
           0x3B01 : "LPC Interface Controller",
           0x3B02 : "LPC Interface Controller",
           0x3B03 : "LPC Interface Controller",
           0x3B06 : "LPC Interface Controller",
           0x3B07 : "LPC Interface Controller",
           0x3B08 : "LPC Interface Controller",
           0x3B09 : "LPC Interface Controller",
           0x3B0A : "LPC Interface Controller",
           0x3B0B : "LPC Interface Controller",
           0x3B0D : "LPC Interface Controller",
           0x3B0F : "LPC Interface Controller",
           0x3B12 : "LPC Interface Controller",
           0x3B14 : "LPC Interface Controller",
           0x3B16 : "LPC Interface Controller",
           0x3B20 : "SATA IDE 4-Port Desktop",
           0x3B21 : "SATA IDE 2-Port Desktop",
           0x3B22 : "SATA AHCI 6-Port Desktop",
           0x3B23 : "SATA AHCI 4-Port Desktop",
           0x3B24 : "SATA Enhanced RAID",
           0x3B25 : "SATA Raid Controller",
           0x3B26 : "SATA IDE 2-Port Secondary Desktop",
           0x3B28 : "SATA IDE 4-Port Mobile",
           0x3B29 : "SATA AHCI 4-Port Mobile",
           0x3B2B : "SATA Enhanced RAID",
           0x3B2C : "SATA Raid Controller",
           0x3B2D : "SATA IDE Controller:2 port",
           0x3B2E : "SATA IDE 4-Port Mobile",
           0x3B2F : "SATA AHCI 6-Port Mobile",
           0x3B30 : "SMBus &#1050;&#1086;&#1085;&#1090;&#1088;&#1086;&#1083;&#1083;&#1077;&#1088;",
           0x3B32 : "LPC Interface Controller",
           0x3b63 : "06",
           0x3B64 : "Management Engine Driver",
           0x3B64 : "Management Engine Driver",
           0x3B64 : "Intel Management Engine Interface",
           0x3B64 : "Intel Management Engine Interface",
           0x3B64 : "intel",
           0x3b65 : "06",
           0x3B67 : "Intel(R) Active Management Technology - Serial Over LAN (SOL) ",
           0x4000 : "V.90 HaM Modem",
           0x402f : "Intel (R) 5400 Chipset QuickData Technology device - 402F",
           0x4220 : "Intel 54 MBit/s Notebook WLAN Card",
           0x4222 : "Intel 3945ABG Wireless LAN controller",
           0x4223 : "Intel (R) PRO/Wireless 2200BG Network Connection",
           0x4223 : "Intel (R) PRO/Wireless 2200BG Network Connection",
           0x4224 : "802.11a/b/g WLan adapter",
           0x4227 : "Intel(R) PRO/Wireless 3945ABG",
           0x4229 : "Intel Wireless WiFi Link 4965AGN(supporting 802.11a/b/g/Draft-N)",
           0x422B : "Intel(R) Centrino(R) Ultimate-N 6300 AGN",
           0x422C : "Broadcom Wifi",
           0x422D : "Intel Wireless WiFi Link 4965AGN",
           0x4230 : "Intel Wireless WiFi Link 4965AGN",
           0x4232 : "Carte Intel WiFi Link 5100 AGN",
           0x4233 : "Intel Wireless WiFi Link 4965AGN",
           0x4235 : "Intel WiFi Link 5300 AGN",
           0x4236 : "Intel(R) WiFi Link 5300 AGN",
           0x4237 : "Intel (R) WiFi Link 5100 AGN",
           0x4238 : "Intel Centrino Ultimate-N 6300 AGN",
           0x4239 : "Intel(R) Centrino(R) Advanced-N 6200 AGN",
           0x423A : "PRO/Wireless 5350 AGN [Echo Peak]",
           0x423C : "WiMAX/WiFi Link 5150",
           0x4318 : "Dell Wireless 1370 WLAN Mini-PCI Card",
           0x444E : "Intel TurboMemory",
           0x4813 : "Dell Wireless 1370 WLAN Mini-PCI Card",
           0x4836 : "2425678",
           0x4888 : "intel 3945abg wireless lan controller",
           0x5001 : "Modem - PPP",
           0x5005 : "Modem - PPPoA",
           0x5029 : "AHCI Controller",
           0x502A : "SATA Controller",
           0x502B : "SATA Controller",
           0x5200 : "PCI to PCI Bridge",
           0x5201 : "Network Controller",
           0x5309 : "I/O Processor Address Translation Unit",
           0x530D : "I/O Companion Unit Address Translation",
           0x6960 : "EHCI 960 emulator",
           0x7000 : "PIIX3 PCI-to-ISA Bridge (Triton II)",
           0x7010 : "PIIX3 IDE Interface (Triton II)",
           0x7020 : "PIIX3 USB Host Controller (Triton II)",
           0x7030 : "System Controller",
           0x7051 : "Intel Business Video Conferencing Card",
           0x7100 : "System Controller (MTXC)",
           0x7110 : "PIIX4/4E/4M ISA Bridge",
           0x7111 : "PIIX4/4E/4M IDE Controller",
           0x7112 : "PIIX4/4E/4M USB Interface",
           0x7113 : "PIIX4/4E/4M Power Management Controller",
           0x7120 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x7121 : "Graphics Controller",
           0x7122 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x7123 : "Intel 82810 Graphics Controller",
           0x7123 : "Intel 82810 Graphics Controller",
           0x7124 : "Host-Hub Interface Bridge / DRAM Ctrlr",
           0x7125 : "Intel Direct AGP 810Chipset ",
           0x7126 : "Host Bridge and Memory Controller Hub",
           0x7127 : "Graphics Device (FSB 133 MHz)",
           0x7128 : "Host Bridge and Memory Controller Hub",
           0x712A : "Host Bridge and Memory Controller Hub",
           0x7180 : "Host/PCI bridge in 440LX/EX AGP chipset",
           0x7181 : "AGP device in 440LX/EX AGP chipset",
           0x7182 : "intel",
           0x7190 : "440BX/ZX AGPset Host Bridge",
           0x7191 : "440BX/ZX AGPset PCI-to-PCI bridge",
           0x7192 : "440BX/ZX chipset Host-to-PCI Bridge",
           0x7194 : "AC'97 Audio device",
           0x7195 : "AC97 Audio Controller",
           0x7196 : "AC97 Modem Controller (Winmodem)",
           0x7198 : "PCI to ISA Bridge",
           0x7199 : "EIDE Controller",
           0x719A : "USB Universal Host Controller",
           0x719B : "Power Management Controller",
           0x71A0 : "Host-to-PCI Bridge",
           0x71A1 : "fabricated by Intel ",
           0x71A2 : "Host-to-PCI Bridge",
           0x7221 : "graphics device",
           0x7600 : "LPC/FWH Interface",
           0x7601 : "EIDE Controller",
           0x7602 : "USB Host Controller",
           0x7603 : "SM Bus Controller",
           0x7605 : "IEEE1394 OpenHCI Host Controller",
           0x7800 : "AGP Graphics Accelerator",
           0x803b : "0x81ef",
           0x8083 : "Intel Wireless WiFi Link 5100 ABGN 10/100/1000 Base T",
           0x8086 : "PCI-&#1050;&#1086;&#1085;&#1090;&#1088;&#1086;&#1083;&#1083;&#1077;&#1088; Simple Communications",
           0x8086 : "intel",
           0x8086 : "VIA vynil v700b",
           0x8086 : "REV_003&61AAA01&0&60 ",
           0x8086 : "VIA vynil v700b",
           0x8086 : "pci simple communications controller ",
           0x8086 : "HDAUDIOFUNC_01&VEN_8086&DEV_1000",
           0x8086 : "Intel(R) Management Engine Interface",
           0x8108 : "Intel(R) Graphics Media Accelerator 500  http://downloadcenter.intel.com/Detail_Desc.aspx?lang=eng&D",
           0x811A : "Atom SCH PATA",
           0x8186 : "i dont know",
           0x8280 : "Realtek AC97",
           0x84C4 : "450KX/GX PCI Bridge (Orion)",
           0x84C5 : "450KX/GX Memory Controller (Orion)",
           0x84CA : "450NX PCIset Memory & I/O Controller",
           0x84CB : "PCI Expander Bridge",
           0x84E0 : "System Address controller",
           0x84E1 : "System Data Controller",
           0x84E2 : "Graphics Expander Bridge",
           0x84E3 : "Memory Address Controller",
           0x84E4 : "Memory Data Controller",
           0x84E6 : "Wide and fast PCI eXpander Bridge",
           0x84EA : "AGP Bridge (GXB function 1)",
           0x85A1 : "LPC Bridge",
           0x85A2 : "IDE Controller",
           0x85A3 : "Serial ATA Controller",
           0x85A4 : "SMBus Controller",
           0x85A6 : "AC'97 Audio Controller",
           0x85A7 : "AC'97 Modem Controller",
           0x85A9 : "USB 1.1 UHCI Controller #1",
           0x85AA : "USB 1.1 UHCI Controller #2",
           0x8C3A : "Intel(R) Management Engine Interface",
           0x9620 : "I2O RAID PCI to PCI Bridge",
           0x9621 : "I2O 1.5 RAID Controller",
           0x9622 : "I2O 1.5 RAID Controller",
           0x9641 : "I2O 1.5 RAID Controller",
           0x96A1 : "I2O 1.5 RAID Controller",
           0x9779 : "0x2992",
           0x9874 : "AUDIO CONTROLLER",
           0x9876 : "intel brokdale",
           0x9876 : "IntcDAudModel",
           0x9877 : "1",
           0x9888 : "HDAUDIOFUNC_01&VEN_8086&DEV_27d8&REV_1000",
           0x9998 : " 02",
           0x9999 : "Interface chip",
           0x9C22 : "Intel Chipset",
           0x9C3A : "Intel Management Engine Interface driver",
           0xA001 : "Intel Media Accelerator 3150",
           0xA002 : "Intel Grafik-Media-Accelerator 3150 (Intel GMA 3150)",
           0xA011 : "Intel(R) Graphics Media Accelerator 3150",
           0xA012 : "Intel Graphics Media Accelerator 3150",
           0xA011 : "3&33FD14CA&0&10",
           0xA012 : "Intel(R) ICH8 Family SMBus Controller",
           0xB152 : "PCI to PCI Bridge",
           0xB154 : "PCI to PCI Bridge",
           0xB555 : "Non-Transparent PCI-to-PCI Bridge",
           0xC50 : "sdf",
           0xE13A : "NXMOQSN00430812D49",
           0x2 : "0x27DA",
           2 : "PCI/VEN_8086&DEV_2A07&SUBSYS",
           0x3 : "PCIVEN_8086&DEV_3B64&SUBSYS_3B648086&REV_063&11583659&0&B0 ",
           0x27c8 : "Microsoft UAA Bus HD Audio",
           0x27d8 : "INTEL IDT Audio",
           0x999 : "PCIVEN_8086&DEV_2930&SUBSYS_037E1014&REV_023&61AAA01&0&FB",
           0x1c3a : "REV-04",
           0x1E3A : "i5 2500k?",
           0x3B64 : "REV_02",
           0x1c3a : "REV-04 3&11583659",
           0x1C3A : "Intel(R) Management Engine Interface",
           8671 : "",
         },
0x8087 : { 0x0028 : "MCP67 High Definition Audio",
           0x07D6 : "Intel Centrino Wireless-N + WiMAX 6150",
         },
0x80EE : { 0x7145 : "VirtualBox Graphics Adapter",
           0xBEEF : "VirtualBox Graphics Adapter",
         },
0x8866 : { 0x1685 : "MP3 player/FM radio/voice recorder 256 Mo flash",
           0x1689 : "MP3 player/FM radio/voice recorder 256 Mo flash",
         },
0x9004 : { 0x0078 : "AHA-2940UW/CN",
           0x1078 : "RAID Coprocessor",
           0x1135 : "Texas Instruments",
           0x1160 : "Fibre Channel Adapter",
           0x2178 : "SCSI Controller",
           0x3860 : "AIC-2930U Ultra SCSI Ctrlr",
           0x3B78 : "QuadChannel Fast-Wide/Ultra-Wide Diff. SCSI Ctrlr",
           0x5075 : "SCSI Ctrlr",
           0x5078 : "Fast/Wide SCSI Controller",
           0x5175 : "SCSI Ctrlr",
           0x5178 : "FAST-SCSI Ctrlr",
           0x5275 : "SCSI Ctrlr",
           0x5278 : "Fast SCSI Ctrlr",
           0x5375 : "SCSI Ctrlr",
           0x5378 : "Fast SCSI Ctrlr",
           0x5475 : "SCSI Ctrlr",
           0x5478 : "Fast SCSI Ctrlr",
           0x5575 : "SCSI Ctrlr",
           0x5578 : "Fast SCSI Ctrlr",
           0x5675 : "SCSI Ctrlr",
           0x5678 : "Fast SCSI Ctrlr",
           0x5775 : "SCSI Ctrlr",
           0x5778 : "Fast SCSI Ctrlr",
           0x5800 : "PCI-to-1394 Ctrlr",
           0x5900 : "ATM155 & 25 LAN Controller",
           0x5905 : "ATM Adpater",
           0x6038 : "Ultra SCSI Adpater (VAR)",
           0x6075 : "CardBus Ultra SCSI Controller",
           0x6078 : "PCI SCSI Controller",
           0x6178 : "PCI SCSI Controller",
           0x6278 : "SCSI Ctrlr",
           0x6378 : "SCSI Ctrlr",
           0x6478 : "SCSI Ctrlr",
           0x6578 : "SCSI Ctrlr",
           0x6678 : "SCSI Ctrlr",
           0x6778 : "SCSI Ctrlr",
           0x6915 : "Fast Ethernet",
           0x7078 : "Fast and Wide SCSI Ctrlr",
           0x7178 : "Fast/Fast-Wide SCSI Ctrlr",
           0x7278 : "Multichannel Fast/Fast-Wide SCSI Ctrlr",
           0x7378 : "4-chan RAID SCSI Ctrlr",
           0x7478 : "SCSI Ctrlr",
           0x7578 : "Multichannel Fast/Fast-Wide Diff. SCSI Ctrlr",
           0x7678 : "QuadChannel Fast-Wide/Ultra-Wide Diff. SCSI Ctrlr",
           0x7778 : "SCSI Ctrlr",
           0x7810 : "Memory control IC",
           0x7815 : "RAID + Memory Controller IC",
           0x7850 : "Fast/Wide SCSI-2 Controller",
           0x7855 : "Single channel SCSI Host Adapter",
           0x7860 : "PCI SCSI Controller",
           0x7870 : "Fast/Wide SCSI-2 Controller",
           0x7871 : "SCSI",
           0x7872 : "Multiple SCSI channels",
           0x7873 : "Multiple SCSI channels",
           0x7874 : "Differential SCSI",
           0x7880 : "Fast 20 SCSI",
           0x7890 : "SCSI controller",
           0x7891 : "SCSI controller",
           0x7892 : "SCSI controller",
           0x7893 : "SCSI controller",
           0x7894 : "SCSI controller",
           0x7895 : "Ultra-Wide SCSI Ctrlr on AHA-2940 AHA-394x",
           0x7896 : "SCSI controller",
           0x7897 : "SCSI controller",
           0x8078 : "Ultra Wide SCSI",
           0x8178 : "Ultra/Ultra-Wide SCSI Ctrlr",
           0x8278 : "AHA-3940U/3940UW/3940UWD SCSI Ctrlr",
           0x8378 : "SCSI Controller",
           0x8478 : "Ultra-Wide Diff. SCSI Ctrlr",
           0x8578 : "Fast-Wide/Ultra-Wide Diff. SCSI Ctrlr",
           0x8678 : "QuadChannel Ultra-Wide Diff. SCSI Ctrlr",
           0x8778 : "Ultra-Wide SCSI Ctrlr",
           0x8878 : "Ultra Wide SCSI Controller",
           0x8B78 : "AIC-7880P",
           0xEC78 : "QuadChannel Fast-Wide/Ultra-Wide Diff. SCSI Ctrlr",
         },
0x9005 : { 0x0010 : "AHA-2940U2W/U2B",
           0x0011 : "AHA-2930U2 Ultra2 SCSI Host Adapter",
           0x0013 : "SCSI Controller",
           0x001F : "Ultra2-Wide SCSI controller",
           0x0020 : "SCSI Controller",
           0x002F : "SCSI Controller",
           0x0030 : "SCSI Controller",
           0x003F : "SCSI Controller",
           0x0050 : "AHA-3940U2x/3950U2x Ultra2 SCSI Adapter",
           0x0051 : "AHA-3950U2x Ultra2 SCSI Adapter",
           0x0053 : "SCSI Controller",
           0x005F : "Ultra2 SCSI Controller",
           0x0080 : "Ultra160/m PCI SCSI Controller",
           0x0081 : "Ultra160 SCSI Controller",
           0x0083 : "Ultra160 SCSI Controller",
           0x008F : "Ultra160 SCSI Controller",
           0x00C0 : "Ultra160 SCSI Controller",
           0x00C1 : "Ultra160 SCSI Controller",
           0x00C3 : "Ultra160 SCSI Controller",
           0x00C5 : "RAID Subsystem HBA",
           0x00CF : "Ultra160 SCSI Controller",
           0x0241 : "Adaptec 1420SA Serial AHA HostRAID Controller",
           0x0258 : "Adaptec AAR-2610SA SATA 6-Port Raid",
           0x0285 : "PCIX133 32/64bit",
           0x0286 : "SUBSYS_95801014REV_02",
           0x041F : "SAS/SATA Controller",
           0x043E : "SAS/SATA Controller",
           0x41E : "Razor ASIC",
           0x564A : "iSCSI Controller",
           0x8000 : "Ultra320 SCSI Controller",
           0x800F : "Ultra320 SCSI Controller",
           0x8010 : "Ultra320 SCSI Controller",
           0x8011 : "Ultra320 SCSI Controller",
           0x8012 : "Ultra320 SCSI Controller",
           0x8014 : "Ultra320 SCSI Controller",
           0x8015 : "Ultra320 SCSI Controller",
           0x8016 : "Ultra320 SCSI Controller",
           0x8017 : "Ultra320 SCSI Controller",
           0x801C : "Ultra320 SCSI Controller",
           0x801D : "Ultra320 SCSI Controller",
           0x801E : "Ultra320 SCSI Controller",
           0x801F : "Ultra320 SCSI Controller",
           0x8080 : "Ultra320 HostRAID Controller",
           0x808F : "Ultra320 HostRAID Controller",
           0x8090 : "HostRAID SCSI Controller",
           0x8091 : "HostRAID SCSI Controller",
           0x8092 : "HostRAID SCSI Controller",
           0x8093 : "HostRAID SCSI Controller",
           0x8094 : "HostRAID SCSI Controller",
           0x8095 : "HostRAID SCSI Controller",
           0x8096 : "HostRAID SCSI Controller",
           0x8097 : "HostRAID SCSI Controller",
           0x809C : "HostRAID SCSI Controller",
           0x809D : "HostRAID SCSI Controller",
           0x809E : "HostRAID SCSI Controller",
           0x809F : "HostRAID SCSI Controller",
         },
0x9412 : { 0x6565 : "IDE Controller?",
         },
0x9710 : { 0x7705 : "MCS7705 -- USB 1.1 to Single Parallel Controller",
           0x7830 : "USB 2.0 to 10/100M Fast Ethernet Controller",
           0x8729 : "usb 2.0 10/100M ethernet adaptor",
           0x9805 : "Netmos Parallel  port PCI card",
           0x9815 : "MCS9815 / M-CAB Parallel Adapter",
           0x9835 : "2 serial",
           0x9845 : "2 serial",
           0x9865 : "PCI Porta Paralela",
           0x9900 : "NetMOS Single Parallel Port Card",
           0x9912 : "PCIe to Dual Serial and Single Parallel",
           0x9922 : "PCIe to Dual Serial Port Controller",
         },
0x9902 : { 0x0001 : "SG2010",
           0x0002 : "SG2010",
           0x0003 : "SG1010",
         },
0xA0F1 : { 0x9876 : "0x9876",
         },
0xA200 : { 0xa200 : "tv",
         },
0xA259 : { 0x3038 : "USBVID_03F0&PID_0205",
         },
0xA304 : { 0x3038 : "USB",
         },
0xA727 : { 0x0013 : "3com 11 a/b/g wireless PCI Adapter",
         },
0xAA42 : { 0x03A3 : "CharKey",
         },
0xC0DE : { 0x5600 : "",
           0xC0DE : "oZ0030",
         },
0xD4D4 : { 0x010F : "PMC-211",
           0x0601 : "PCI Mezzanine Card",
         },
0xDEAF : { 0x9050 : "",
           0x9051 : "",
           0x9052 : "",
         },
0xE159 : { 0x0001 : "Yeastar TDM400",
           0x0002 : "Sedlbauer Speed PCI",
           0x0600 : "PCI-to-PCI Bridge",
         },
0xEACE : { 0x24C5 : "VIA Vynil v700b",
           0x3100 : "OC-3/OC-12",
           0x3200 : "OC-3/OC-12",
           0x320E : "Fast Ethernet",
           0x340E : "Fast Ethernet",
           0x341E : "Fast Ethernet",
           0x3500 : "OC-3/OC-12",
           0x351C : "Fast Ethernet",
           0x4100 : "OC-48",
           0x4110 : "OC-48",
           0x4200 : "OC-48",
           0x420E : "Dual Gigabit Ethernet",
           0x430e : "Dual Gigabit Ethernet",
         },
0xECC0 : { 0x0050 : "",
           0x0051 : "",
           0x0060 : "",
           0x0070 : "",
           0x0071 : "",
           0x0072 : "",
           0x0080 : "4/2 channel (analog/digital) audio card",
           0x0100 : "6/8 channel (analog/digital) audio card",
           0x3410 : "Motorola",
         },
0xEDD8 : { 0xA091 : "ARK1000PV",
           0xA099 : "ARK2000PV",
           0xA0A1 : "ARK2000MT",
           0xA0A9 : "ARK2000MI",
           0xA0B1 : "ARK2000MI+",
         },
0xFA57 : { 0x0001 : "Pattern Matching Chip",
         }

}

########NEW FILE########
__FILENAME__ = physmem
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/physmem.py 
# ==========================================
# Access to physical memory
# ~~~
# #usage:
#     read_physical_mem( 0xf0000, 0x100 )
#     write_physical_mem_dowrd( 0xf0000, 0xdeadbeef )
#     read_physical_mem_dowrd( 0xfed40000 )
#DEPRECATED:
#     read_phys_mem( 0xf0000, 0x100 )
#     write_phys_mem_dword( 0xf0000, 0xdeadbeef )
#     read_phys_mem_dword( 0xfed40000 )
# ~~~
#
__version__ = '1.0'

import struct
import sys

from chipsec.logger import *

class MemoryRuntimeError (RuntimeError):
    pass

class MemoryAccessError (RuntimeError):
    pass

class Memory:
    def __init__( self, helper ):
        self.helper = helper

    ####################################################################################
    #
    # Physical memory API using 64b Physical Address
    # (Same functions as below just using 64b PA instead of High and Low 32b parts of PA)
    #
    ####################################################################################

    # Reading physical memory

    def read_physical_mem( self, phys_address, length ):
        return self.helper.read_physical_mem( phys_address, length )

    def read_physical_mem_dword( self, phys_address ):
        out_buf = self.read_physical_mem( phys_address, 4 )
        value = struct.unpack( '=I', out_buf )[0]
        if logger().VERBOSE:
           logger().log( '[mem] dword at PA = 0x%016X: 0x%08X' % (phys_address, value) )
        return value

    def read_physical_mem_word( self, phys_address ):
        out_buf = self.read_physical_mem( phys_address, 2 )
        value = struct.unpack( '=H', out_buf )[0]
        if logger().VERBOSE:
           logger().log( '[mem] word at PA = 0x%016X: 0x%04X' % (phys_address, value) )
        return value

    def read_physical_mem_byte( self, phys_address ):
        out_buf = self.read_physical_mem( phys_address, 1 )
        value = struct.unpack( '=B', out_buf )[0]
        if logger().VERBOSE:
           logger().log( '[mem] byte at PA = 0x%016X: 0x%02X' % (phys_address, value) )
        return value

    # Writing physical memory

    def write_physical_mem( self, phys_address, length, buf ):
        if logger().VERBOSE:
           logger().log( '[mem] buffer len = 0x%X to PA = 0x%016X' % (length, phys_address) )
           print_buffer( buf )
        return self.helper.write_physical_mem( phys_address, length, buf )

    def write_physical_mem_dword( self, phys_address, dword_value ):
        if logger().VERBOSE:
           logger().log( '[mem] dword to PA = 0x%016X <- 0x%08X' % (phys_address, dword_value) )
        return self.write_physical_mem( phys_address, 4, struct.pack( 'I', dword_value ) )

    def write_physical_mem_word( self, phys_address, word_value ):
        if logger().VERBOSE:
           logger().log( '[mem] word to PA = 0x%016X <- 0x%04X' % (phys_address, word_value) )
        return self.write_physical_mem( phys_address, 2, struct.pack( 'H', word_value ) )

    def write_physical_mem_byte( self, phys_address, byte_value ):
        if logger().VERBOSE:
           logger().log( '[mem] byte to PA = 0x%016X <- 0x%02X' % (phys_address, byte_value) )
        return self.write_physical_mem( phys_address, 1, struct.pack( 'B', byte_value ) )


    ####################################################################################
    #
    # DEPRECATED
    # Physical memory API using 64b Physical Address split into 32b High and Low parts
    #
    ####################################################################################

    def read_phys_mem_64( self, phys_address_hi, phys_address_lo, length ):
        out_buf = self.helper.read_phys_mem( phys_address_hi, phys_address_lo, length )
        return out_buf

    def read_phys_mem_dword_64(self, phys_address_hi, phys_address_lo ):
        out_buf = self.read_phys_mem_64( phys_address_hi, phys_address_lo, 4 )
        try:
           value = struct.unpack( 'L', out_buf.raw )[0]
        except:
           raise MemoryAccessError, "read_phys_mem did not return hex dword"
        if logger().VERBOSE:
           logger().log( '[mem] dword at PA = 0x%08X_%08X: 0x%08X' % (phys_address_hi, phys_address_lo, value) )
        return value

    def read_phys_mem_word_64(self, phys_address_hi, phys_address_lo ):
        out_buf = self.read_phys_mem_64( phys_address_hi, phys_address_lo, 2 )
        try:
           value = struct.unpack( 'H', out_buf.raw )[0]
        except:
           raise MemoryAccessError, "read_phys_mem did not return hex word"
        if logger().VERBOSE:
           logger().log( '[mem] word at PA = 0x%08X_%08X: 0x%04X' % (phys_address_hi, phys_address_lo, value) )
        return value

    def read_phys_mem_byte_64(self, phys_address_hi, phys_address_lo ):
        out_buf = self.read_phys_mem_64( phys_address_hi, phys_address_lo, 1 )
        try:
           value = struct.unpack( 'B', out_buf.raw )[0]
        except:
           raise MemoryAccessError, "read_phys_mem did not return 1 Byte"
        if logger().VERBOSE:
           logger().log( '[mem] byte at PA = 0x%08X_%08X: 0x%02X' % (phys_address_hi, phys_address_lo, value) )
        return value

    def write_phys_mem_64( self, phys_address_hi, phys_address_lo, length, buf ):
        return self.helper.write_phys_mem( phys_address_hi, phys_address_lo, length, buf )

    def write_phys_mem_dword_64( self, phys_address_hi, phys_address_lo, dword_value ):
        if logger().VERBOSE:
           logger().log( '[mem] dword to PA = 0x%08X_%08X <- 0x%08X' % (phys_address_hi, phys_address_lo, dword_value) )
        return self.write_phys_mem_64( phys_address_hi, phys_address_lo, 4, struct.pack( 'I', dword_value ) )

    def write_phys_mem_word_64( self, phys_address_hi, phys_address_lo, word_value ):
        if logger().VERBOSE:
           logger().log( '[mem] word to PA = 0x%08X_%08X <- 0x%04X' % (phys_address_hi, phys_address_lo, word_value) )
        return self.write_phys_mem_64( phys_address_hi, phys_address_lo, 2, struct.pack( 'H', word_value ) )

    def write_phys_mem_byte_64( self, phys_address_hi, phys_address_lo, byte_value ):
        if logger().VERBOSE:
           logger().log( '[mem] byte to PA = 0x%08X_%08X <- 0x%02X' % (phys_address_hi, phys_address_lo, byte_value) )
        return self.write_phys_mem_64( phys_address_hi, phys_address_lo, 1, struct.pack( 'B', byte_value ) )


    ####################################################################################
    #
    # DEPRECATED
    # Physical memory API using 32b Physical Address
    #
    ####################################################################################

    def read_phys_mem_byte(self, phys_address ):
        return self.read_phys_mem_byte_64( 0, phys_address )

    def read_phys_mem_word(self, phys_address ):
        return self.read_phys_mem_word_64( 0, phys_address )

    def read_phys_mem_dword(self, phys_address ):
        return self.read_phys_mem_dword_64( 0, phys_address )

    def read_phys_mem(self, phys_address, length ):
        return self.read_phys_mem_64( 0, phys_address, length )

    def write_phys_mem_byte( self, phys_address, byte_value ):
        return self.write_phys_mem_byte_64( 0, phys_address, byte_value )

    def write_phys_mem_word( self, phys_address, word_value ):
        return self.write_phys_mem_word_64( 0, phys_address, word_value )

    def write_phys_mem_dword( self, phys_address, dword_value ):
        return self.write_phys_mem_dword_64( 0, phys_address, dword_value )

    def write_phys_mem(self, phys_address, length, buf ):
        return self.write_phys_mem_64( 0, phys_address, length, buf )


########NEW FILE########
__FILENAME__ = smbus
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/smbus.py
# ================================
# Access to SMBus Controller
#
#
#



from chipsec.logger import *
from chipsec.cfg.common import *

class SMBus:
    def __init__( self, cs ):
        self.cs = cs

    def get_SMBus_Base_Address( self ):
        #
        # B0:D31:F3 + 0x20 SMBus Base Address (SBA)
        #
        reg_value = self.cs.pci.read_byte( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, CFG_REG_PCH_SMB_SBA )
        return (reg_value & CFG_REG_PCH_SMB_SBA_BASE_ADDRESS_MASK) 

    def get_SMBus_HCFG( self ):
        #
        # B0:D31:F3 + 0x40 SMBus Host Configuration (HCFG)
        #
        reg_value = self.cs.pci.read_byte( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, CFG_REG_PCH_SMB_HCFG )
        hcfg = SMB_HCFG_REG( reg_value, (reg_value&CFG_REG_PCH_SMB_HCFG_SPD_WD > 0), (reg_value&CFG_REG_PCH_SMB_HCFG_SSRESET > 0), (reg_value&CFG_REG_PCH_SMB_HCFG_I2C_EN > 0), (reg_value&CFG_REG_PCH_SMB_HCFG_SMB_SMI_EN > 0), (reg_value&CFG_REG_PCH_SMB_HCFG_HST_EN > 0) )
        return hcfg

    def display_SMBus_info( self ):
        logger().log( "[smbus] SMBus Base Address: 0x%04X" % self.get_SMBus_Base_Address() )
        logger().log( self.get_SMBus_HCFG() )

    def is_SMBus_enabled( self ):
        return self.cs.pci.is_enabled( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN )

    def is_SMBus_supported( self ):
        (did,vid) = self.cs.pci.get_DIDVID( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN )
        if logger().VERBOSE:
           logger().log( "[*] SMBus Controller (DID,VID) = (0x%04X,0x%04X)" % (did,vid) )

        # @TODO: check correct DIDs
        #if (0x8086 == vid and PCI_B0D31F3_SMBUS_CTRLR_DID == did):
        if (0x8086 == vid):
          return True
        else:
          logger().error( "Unknown SMBus Controller (DID,VID) = (0x%04X,0x%04X)" % (did,vid) )
          return False

    def is_SMBus_host_controller_enabled( self ):
        hcfg = self.get_SMBus_HCFG()
        return hcfg.CFG_REG_PCH_SMB_HCFG_HST_EN

    def enable_SMBus_host_controller( self ):
        # Enable SMBus Host Controller Interface in HCFG
        hcfg = self.get_SMBus_HCFG()
        if 0 == hcfg.HST_EN:
            hcfg.HST_EN = 1
            self.cs.pci.write_byte( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, CFG_REG_PCH_SMB_HCFG, hcfg )

        # @TODO: check SBA is programmed
        sba = self.get_SMBus_Base_Address()

        # Enable I/O Space in CMD
        cmd = self.cs.pci.read_word( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, CFG_REG_PCH_SMB_CMD )
        if (cmd & 0x1): self.cs.pci.write_byte( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, CFG_REG_PCH_SMB_CMD, 0x1 )


    def _wait_for_cycle( self, smbus_io_base ):
        # wait for cycle to complete
        #while True:
        for i in range(10):
            sts = self.cs.io.read_port_byte( smbus_io_base )
            if   (sts & 0x02): break
            elif (sts & 0x04): logger().error( "SMBus cycle failed: Device error" )
            elif (sts & 0x08): logger().error( "SMBus cycle failed: Bus Error" )
            elif (sts & 0x10): logger().error( "SMBus cycle failed: Unknown Error" )
        if (0x02 == sts): return True
        else: return False

    def _read_byte( self, smbus_io_base, target_address, offset ):
        self.cs.io.write_port_byte( smbus_io_base + 0x0, 0xFF )                   # Clear status bits
        ##self.cs.io.write_port_byte( smbus_io_base + 0x1, 0x1F )
        #for i in range(100):
        #    self.cs.io.write_port_byte( smbus_io_base + 0x0, 0xFF )                   # Clear status bits
        #    sts = self.cs.io.read_port_byte( smbus_io_base )
        #    if (0 == (sts & 0x9F)): break
        #if (sts & 0x9F):
        #    logger().error( "SMBus is not ready for whatever reason" ) 
        #    return 0xFF

        self.cs.io.write_port_byte( smbus_io_base + 0x4, (target_address | 0x1) ) # Byte Read from SMBus device at target_address
        self.cs.io.write_port_byte( smbus_io_base + 0x3, offset )                 # Byte offset
        self.cs.io.write_port_byte( smbus_io_base + 0x2, 0x48 )                   # Send command
        # wait for cycle to complete
        if not self._wait_for_cycle( smbus_io_base ): return 0xFF
        # read the data
        value = self.cs.io.read_port_byte( smbus_io_base + 0x5 )
        # Clear status bits
        self.cs.io.write_port_byte( smbus_io_base + 0x0, 0xFF )
        return value

    def _write_byte( self, smbus_io_base, target_address, offset, value ):
        self.cs.io.write_port_byte( smbus_io_base + 0x0, 0xFF )            # Clear status bits
        self.cs.io.write_port_byte( smbus_io_base + 0x4, target_address )  # Byte Write to SMBus device at target_address
        self.cs.io.write_port_byte( smbus_io_base + 0x3, offset )          # Byte offset
        self.cs.io.write_port_byte( smbus_io_base + 0x5, value )           # Byte data to write
        self.cs.io.write_port_byte( smbus_io_base + 0x2, 0x48 )            # Send command
        # wait for cycle to complete
        if not self._wait_for_cycle( smbus_io_base ): return False
        # Clear status bits
        self.cs.io.write_port_byte( smbus_io_base + 0x0, 0xFF )
        return True

    def read_byte( self, target_address, offset ):
        smbus_io_base = self.cs.pci.read_word( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, 0x20 ) & 0xFFFE
        value = self._read_byte( smbus_io_base, target_address, offset )
        if logger().VERBOSE: logger().log( "[smbus] read device %X off %X = %X" % (target_address, offset, value) )
        return value

    def write_byte( self, target_address, offset, value ):
        smbus_io_base = self.cs.pci.read_word( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, 0x20 ) & 0xFFFE
        sts = self._write_byte( smbus_io_base, target_address, offset, value )
        if logger().VERBOSE: logger().log( "[smbus] write to device %X off %X = %X" % (target_address, offset, value) )
        return sts

    def read_range( self, target_address, start_offset, size ):
        buffer = [chr(0xFF)]*size
        smbus_io_base = self.cs.pci.read_word( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, 0x20 ) & 0xFFFE
        for i in range (size):
            buffer[i] = chr( self._read_byte( smbus_io_base, target_address, start_offset + i ) )
        if logger().VERBOSE:
            logger().log( "[smbus] read device %X from offset %X size %X:" % (target_address, start_offset, size) )
            print_buffer( buffer )
        return buffer

    def write_range( self, target_address, start_offset, buffer ):
        size = len(buffer)
        smbus_io_base = self.cs.pci.read_word( 0, PCI_B0D31F3_SMBUS_CTRLR_DEV, PCI_B0D31F3_SMBUS_CTRLR_FUN, 0x20 ) & 0xFFFE
        for i in range(size):
            self._write_byte( smbus_io_base, target_address, start_offset + i, ord(buffer[i]) )
        if logger().VERBOSE:
            logger().log( "[smbus] write device %X to offset %X size %X:" % (target_address, start_offset, size) )
            print_buffer( buffer )
        return True

########NEW FILE########
__FILENAME__ = spi
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/spi.py
# =========================
# Access to SPI Flash parts
# ~~~
# #usage:
#     read_spi( spi_fla, length )
#     write_spi( spi_fla, buf )
#     erase_spi_block( spi_fla )
# ~~~
#
__version__ = '1.0'

import struct
import sys
import time

from chipsec.logger import *
from chipsec.hal.mmio import *
from chipsec.file import *

#
# !! IMPORTANT:
# Size of the data chunk used in SPI read cycle (in bytes)
# default = maximum 64 bytes (remainder is read in 4 byte chunks)
#
# If you want to change logic to read SPI Flash in 4 byte chunks:
# SPI_READ_WRITE_MAX_DBC = 4
#
# SPI write cycles operate on 4 byte chunks (not optimized yet)
#
# Approximate performance (on 2 core HT Sandy Bridge CPU 2.6GHz):
#   SPI read:  ~25 sec per 1MB (DBC=64)
#   SPI write: ~140 sec per 1MB (DBC=4)
# 
SPI_READ_WRITE_MAX_DBC = 64
SPI_READ_WRITE_DEF_DBC = 4

##############################################################################################################
# SPI Host Interface Registers
##############################################################################################################

PCH_RCBA_SPI_BFPR                  = 0x00  # BIOS Flash Primary Region Register (= FREG1)

PCH_RCBA_SPI_HSFSTS                = 0x04  # Hardware Sequencing Flash Status Register
PCH_RCBA_SPI_HSFSTS_FLOCKDN        = BIT15                         # Flash Configuration Lock-Down
PCH_RCBA_SPI_HSFSTS_FDV            = BIT14                         # Flash Descriptor Valid
PCH_RCBA_SPI_HSFSTS_FDOPSS         = BIT13                         # Flash Descriptor Override Pin-Strap Status
PCH_RCBA_SPI_HSFSTS_SCIP           = BIT5                          # SPI cycle in progress
PCH_RCBA_SPI_HSFSTS_BERASE_MASK    = (BIT4 | BIT3)                 # Block/Sector Erase Size
PCH_RCBA_SPI_HSFSTS_BERASE_256B    = 0x00                          # Block/Sector = 256 Bytes
PCH_RCBA_SPI_HSFSTS_BERASE_4K      = 0x01                          # Block/Sector = 4K Bytes
PCH_RCBA_SPI_HSFSTS_BERASE_8K      = 0x10                          # Block/Sector = 8K Bytes
PCH_RCBA_SPI_HSFSTS_BERASE_64K     = 0x11                          # Block/Sector = 64K Bytes
PCH_RCBA_SPI_HSFSTS_AEL            = BIT2                          # Access Error Log
PCH_RCBA_SPI_HSFSTS_FCERR          = BIT1                          # Flash Cycle Error
PCH_RCBA_SPI_HSFSTS_FDONE          = BIT0                          # Flash Cycle Done

PCH_RCBA_SPI_HSFCTL                = 0x06  # Hardware Sequencing Flash Control Register
PCH_RCBA_SPI_HSFCTL_FSMIE          = BIT15                         # Flash SPI SMI Enable
PCH_RCBA_SPI_HSFCTL_FDBC_MASK      = 0x3F00                        # Flash Data Byte Count, Count = FDBC + 1.
PCH_RCBA_SPI_HSFCTL_FCYCLE_MASK    = 0x0006                        # Flash Cycle
PCH_RCBA_SPI_HSFCTL_FCYCLE_READ    = 0                             # Flash Cycle Read
PCH_RCBA_SPI_HSFCTL_FCYCLE_WRITE   = 2                             # Flash Cycle Write
PCH_RCBA_SPI_HSFCTL_FCYCLE_ERASE   = 3                             # Flash Cycle Block Erase
PCH_RCBA_SPI_HSFCTL_FCYCLE_FGO     = BIT0                          # Flash Cycle GO

PCH_RCBA_SPI_FADDR               = 0x08  # SPI Flash Address
PCH_RCBA_SPI_FADDR_MASK          = 0x07FFFFFF                      # SPI Flash Address Mask [0:26]

PCH_RCBA_SPI_FDATA00             = 0x10  # SPI Data 00 (32 bits)
PCH_RCBA_SPI_FDATA01             = 0x14  
PCH_RCBA_SPI_FDATA02             = 0x18  
PCH_RCBA_SPI_FDATA03             = 0x1C  
PCH_RCBA_SPI_FDATA04             = 0x20  
PCH_RCBA_SPI_FDATA05             = 0x24  
PCH_RCBA_SPI_FDATA06             = 0x28  
PCH_RCBA_SPI_FDATA07             = 0x2C  
PCH_RCBA_SPI_FDATA08             = 0x30  
PCH_RCBA_SPI_FDATA09             = 0x34  
PCH_RCBA_SPI_FDATA10             = 0x38  
PCH_RCBA_SPI_FDATA11             = 0x3C  
PCH_RCBA_SPI_FDATA12             = 0x40  
PCH_RCBA_SPI_FDATA13             = 0x44  
PCH_RCBA_SPI_FDATA14             = 0x48  
PCH_RCBA_SPI_FDATA15             = 0x4C  

# SPI Flash Regions Access Permisions Register
PCH_RCBA_SPI_FRAP                = 0x50
PCH_RCBA_SPI_FRAP_BMWAG_MASK     = 0xFF000000                    
PCH_RCBA_SPI_FRAP_BMWAG_GBE      = BIT27                         
PCH_RCBA_SPI_FRAP_BMWAG_ME       = BIT26                         
PCH_RCBA_SPI_FRAP_BMWAG_BIOS     = BIT25                         
PCH_RCBA_SPI_FRAP_BMRAG_MASK     = 0x00FF0000                    
PCH_RCBA_SPI_FRAP_BMRAG_GBE      = BIT19                         
PCH_RCBA_SPI_FRAP_BMRAG_ME       = BIT18                         
PCH_RCBA_SPI_FRAP_BMRAG_BIOS     = BIT17                         
PCH_RCBA_SPI_FRAP_BRWA_MASK      = 0x0000FF00                    
PCH_RCBA_SPI_FRAP_BRWA_SB        = BIT14                         
PCH_RCBA_SPI_FRAP_BRWA_DE        = BIT13                         
PCH_RCBA_SPI_FRAP_BRWA_PD        = BIT12                         
PCH_RCBA_SPI_FRAP_BRWA_GBE       = BIT11                         
PCH_RCBA_SPI_FRAP_BRWA_ME        = BIT10                         
PCH_RCBA_SPI_FRAP_BRWA_BIOS      = BIT9                          
PCH_RCBA_SPI_FRAP_BRWA_FLASHD    = BIT8                          
PCH_RCBA_SPI_FRAP_BRRA_MASK      = 0x000000FF                    
PCH_RCBA_SPI_FRAP_BRRA_SB        = BIT6                          
PCH_RCBA_SPI_FRAP_BRRA_DE        = BIT5                          
PCH_RCBA_SPI_FRAP_BRRA_PD        = BIT4                          
PCH_RCBA_SPI_FRAP_BRRA_GBE       = BIT3                          
PCH_RCBA_SPI_FRAP_BRRA_ME        = BIT2                          
PCH_RCBA_SPI_FRAP_BRRA_BIOS      = BIT1                          
PCH_RCBA_SPI_FRAP_BRRA_FLASHD    = BIT0                          

# Flash Region Registers
PCH_RCBA_SPI_FREG0_FLASHD           = 0x54  # Flash Region 0 (Flash Descriptor)
PCH_RCBA_SPI_FREG1_BIOS             = 0x58  # Flash Region 1 (BIOS)
PCH_RCBA_SPI_FREG2_ME               = 0x5C  # Flash Region 2 (ME)
PCH_RCBA_SPI_FREG3_GBE              = 0x60  # Flash Region 3 (GbE)
PCH_RCBA_SPI_FREG4_PLATFORM_DATA    = 0x64  # Flash Region 4 (Platform Data)
PCH_RCBA_SPI_FREG5_DEVICE_EXPANSION = 0x68  # Flash Region 5 (Device Expansion)
PCH_RCBA_SPI_FREG6_SECONDARY_BIOS   = 0x6C  # Flash Region 6 (Secondary BIOS)

PCH_RCBA_SPI_FREGx_LIMIT_MASK    = 0x7FFF0000                    # Size
PCH_RCBA_SPI_FREGx_BASE_MASK     = 0x00007FFF                    # Base

# Protected Range Registers
PCH_RCBA_SPI_PR0                 = 0x74  # Protected Region 0 Register
PCH_RCBA_SPI_PR0_WPE             = BIT31                         # Write Protection Enable
PCH_RCBA_SPI_PR0_PRL_MASK        = 0x7FFF0000                    # Protected Range Limit Mask
PCH_RCBA_SPI_PR0_RPE             = BIT15                         # Read Protection Enable
PCH_RCBA_SPI_PR0_PRB_MASK        = 0x00007FFF                    # Protected Range Base Mask
PCH_RCBA_SPI_PR1                 = 0x78
PCH_RCBA_SPI_PR1_WPE             = BIT31
PCH_RCBA_SPI_PR1_PRL_MASK        = 0x7FFF0000
PCH_RCBA_SPI_PR1_RPE             = BIT15
PCH_RCBA_SPI_PR1_PRB_MASK        = 0x00007FFF
PCH_RCBA_SPI_PR2                 = 0x7C
PCH_RCBA_SPI_PR2_WPE             = BIT31
PCH_RCBA_SPI_PR2_PRL_MASK        = 0x7FFF0000
PCH_RCBA_SPI_PR2_RPE             = BIT15 
PCH_RCBA_SPI_PR2_PRB_MASK        = 0x00007FFF
PCH_RCBA_SPI_PR3                 = 0x80
PCH_RCBA_SPI_PR3_WPE             = BIT31
PCH_RCBA_SPI_PR3_PRL_MASK        = 0x7FFF0000
PCH_RCBA_SPI_PR3_RPE             = BIT15                         
PCH_RCBA_SPI_PR3_PRB_MASK        = 0x00007FFF                    
PCH_RCBA_SPI_PR4                 = 0x84  
PCH_RCBA_SPI_PR4_WPE             = BIT31 
PCH_RCBA_SPI_PR4_PRL_MASK        = 0x7FFF0000
PCH_RCBA_SPI_PR4_RPE             = BIT15     
PCH_RCBA_SPI_PR4_PRB_MASK        = 0x00007FFF

PCH_RCBA_SPI_OPTYPE              = 0x96  # Opcode Type Configuration
PCH_RCBA_SPI_OPTYPE7_MASK        = (BIT15 | BIT14)
PCH_RCBA_SPI_OPTYPE6_MASK        = (BIT13 | BIT12)
PCH_RCBA_SPI_OPTYPE5_MASK        = (BIT11 | BIT10)
PCH_RCBA_SPI_OPTYPE4_MASK        = (BIT9 | BIT8)  
PCH_RCBA_SPI_OPTYPE3_MASK        = (BIT7 | BIT6)  
PCH_RCBA_SPI_OPTYPE2_MASK        = (BIT5 | BIT4)  
PCH_RCBA_SPI_OPTYPE1_MASK        = (BIT3 | BIT2)  
PCH_RCBA_SPI_OPTYPE0_MASK        = (BIT1 | BIT0)  
PCH_RCBA_SPI_OPTYPE_RDNOADDR     = 0x00
PCH_RCBA_SPI_OPTYPE_WRNOADDR     = 0x01
PCH_RCBA_SPI_OPTYPE_RDADDR       = 0x02
PCH_RCBA_SPI_OPTYPE_WRADDR       = 0x03

PCH_RCBA_SPI_OPMENU              = 0x98  # Opcode Menu Configuration

PCH_RCBA_SPI_FDOC                = 0xB0  # Flash Descriptor Observability Control Register
PCH_RCBA_SPI_FDOC_FDSS_MASK      = (BIT14 | BIT13 | BIT12)       # Flash Descritor Section Select
PCH_RCBA_SPI_FDOC_FDSS_FSDM      = 0x0000                        # Flash Signature and Descriptor Map
PCH_RCBA_SPI_FDOC_FDSS_COMP      = 0x1000                        # Component
PCH_RCBA_SPI_FDOC_FDSS_REGN      = 0x2000                        # Region
PCH_RCBA_SPI_FDOC_FDSS_MSTR      = 0x3000                        # Master
PCH_RCBA_SPI_FDOC_FDSI_MASK      = 0x0FFC                        # Flash Descriptor Section Index

PCH_RCBA_SPI_FDOD                = 0xB4  # Flash Descriptor Observability Data Register

# agregated SPI Flash commands
HSFCTL_READ_CYCLE = ( (PCH_RCBA_SPI_HSFCTL_FCYCLE_READ<<1) | PCH_RCBA_SPI_HSFCTL_FCYCLE_FGO)
HSFCTL_WRITE_CYCLE = ( (PCH_RCBA_SPI_HSFCTL_FCYCLE_WRITE<<1) | PCH_RCBA_SPI_HSFCTL_FCYCLE_FGO)
HSFCTL_ERASE_CYCLE = ( (PCH_RCBA_SPI_HSFCTL_FCYCLE_ERASE<<1) | PCH_RCBA_SPI_HSFCTL_FCYCLE_FGO)

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# FGO bit cleared (for safety ;)
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#HSFCTL_WRITE_CYCLE = ( (PCH_RCBA_SPI_HSFCTL_FCYCLE_WRITE<<1) )
#HSFCTL_ERASE_CYCLE = ( (PCH_RCBA_SPI_HSFCTL_FCYCLE_ERASE<<1) )

HSFSTS_CLEAR = (PCH_RCBA_SPI_HSFSTS_AEL | PCH_RCBA_SPI_HSFSTS_FCERR | PCH_RCBA_SPI_HSFSTS_FDONE)

#
# Hardware Sequencing Flash Status (HSFSTS)
#
SPI_HSFSTS_OFFSET = 0x04
# HSFSTS bit masks
SPI_HSFSTS_FLOCKDN_MASK = (1 << 15)
SPI_HSFSTS_FDOPSS_MASK  = (1 << 13)

SPI_REGION_NUMBER       = 7
SPI_REGION_NUMBER_IN_FD = 5

FLASH_DESCRIPTOR  = 0
BIOS              = 1
ME                = 2
GBE               = 3
PLATFORM_DATA     = 4
DEVICE_EXPANSION  = 5
SECONDARY_BIOS    = 6

SPI_REGION = {
 FLASH_DESCRIPTOR  : PCH_RCBA_SPI_FREG0_FLASHD,
 BIOS              : PCH_RCBA_SPI_FREG1_BIOS,
 ME                : PCH_RCBA_SPI_FREG2_ME,
 GBE               : PCH_RCBA_SPI_FREG3_GBE,
 PLATFORM_DATA     : PCH_RCBA_SPI_FREG4_PLATFORM_DATA,
 DEVICE_EXPANSION  : PCH_RCBA_SPI_FREG5_DEVICE_EXPANSION,
 SECONDARY_BIOS    : PCH_RCBA_SPI_FREG6_SECONDARY_BIOS
}

SPI_REGION_NAMES = {
 FLASH_DESCRIPTOR  : 'Flash Descriptor',
 BIOS              : 'BIOS',
 ME                : 'Intel ME',
 GBE               : 'GBe',
 PLATFORM_DATA     : 'Platform Data',
 DEVICE_EXPANSION  : 'Device Expansion',
 SECONDARY_BIOS    : 'Secondary BIOS'
}

#
# Flash Descriptor Master Defines
#
SPI_MASTER_NUMBER_IN_FD = 3

MASTER_HOST_CPU_BIOS    = 0
MASTER_ME               = 1
MASTER_GBE              = 2

SPI_MASTER_NAMES = {
 MASTER_HOST_CPU_BIOS : 'CPU/BIOS',
 MASTER_ME            : 'ME',
 MASTER_GBE           : 'GBe'
}


class SpiRuntimeError (RuntimeError):
    pass
class SpiAccessError (RuntimeError):
    pass


def get_SPI_region( flreg ):
    range_base  = (flreg & PCH_RCBA_SPI_FREGx_BASE_MASK) << 12
    range_limit = ((flreg & PCH_RCBA_SPI_FREGx_LIMIT_MASK) >> 4)
    range_limit = range_limit + 0xFFF # + 4kB
    return (range_base, range_limit)

def get_SPI_MMIO_base( cs ):
    reg_value = cs.pci.read_dword( SPI_MMIO_BUS, SPI_MMIO_DEV, SPI_MMIO_FUN, SPI_MMIO_REG_OFFSET )
    spi_base = ((reg_value >> SPI_BASE_ADDR_SHIFT) << SPI_BASE_ADDR_SHIFT) + SPI_MMIO_BASE_OFFSET
    if logger().VERBOSE: logger().log( "[spi] SPI MMIO base: 0x%016X (assuming below 4GB)" % spi_base )
    return spi_base


class SPI:
    def __init__( self, cs ):
        self.cs = cs
        #self.rcba_spi_base = get_MMIO_base_address( self.cs, MMIO_BAR_LPCRCBA_SPI )
        self.rcba_spi_base = get_SPI_MMIO_base( self.cs )

    def spi_reg_read( self, reg ):
        return read_MMIO_reg( self.cs, self.rcba_spi_base, reg )

    def spi_reg_write( self, reg, value ):
        return write_MMIO_reg( self.cs, self.rcba_spi_base, reg, value )


    def get_SPI_region( self, spi_region_id ):
        freg = self.spi_reg_read( SPI_REGION[ spi_region_id ] )
        #range_base  = (freg & PCH_RCBA_SPI_FREGx_BASE_MASK) << 12
        #range_limit = ((freg & PCH_RCBA_SPI_FREGx_LIMIT_MASK) >> 4)
        #range_limit = range_limit + 0xFFF # + 4kB
        ##if range_limit >= range_base:
        ##   range_limit = range_limit + 0xFFF # + 4kB
        (range_base, range_limit) = get_SPI_region( freg )
        return (range_base, range_limit, freg)

    # all_regions = True : return all SPI regions
    # all_regions = False: return only available SPI regions (limit >= base)
    def get_SPI_regions( self, all_regions ):
        spi_regions = {}
        for r in SPI_REGION:
            (range_base, range_limit, freg) = self.get_SPI_region( r )
            if all_regions or (range_limit >= range_base):
                range_size = range_limit - range_base + 1
                spi_regions[r] = (range_base, range_limit, range_size, SPI_REGION_NAMES[r])
        return spi_regions

    def get_SPI_Protected_Range( self, pr_num ):
        if ( pr_num > 5 ):
            return None

        pr_j_reg = PCH_RCBA_SPI_PR0 + pr_num*4
        pr_j  = self.spi_reg_read( pr_j_reg )
        base = (pr_j & PCH_RCBA_SPI_PR0_PRB_MASK) << 12
        limit = (pr_j & PCH_RCBA_SPI_PR0_PRL_MASK) >> 4
        wpe = ((pr_j & PCH_RCBA_SPI_PR0_WPE) != 0)
        rpe = ((pr_j & PCH_RCBA_SPI_PR0_RPE) != 0)
        return (base,limit,wpe,rpe,pr_j_reg,pr_j)

    ##############################################################################################################
    # SPI configuration
    ##############################################################################################################

    def display_SPI_Flash_Descriptor( self ):
        logger().log( "============================================================" )
        logger().log( "SPI Flash Descriptor" )
        logger().log( "------------------------------------------------------------" )
        logger().log( "\nFlash Signature and Descriptor Map:" )
        for j in range(5):
            self.spi_reg_write( PCH_RCBA_SPI_FDOC, (PCH_RCBA_SPI_FDOC_FDSS_FSDM|(j<<2)) )
            fdod = self.spi_reg_read( PCH_RCBA_SPI_FDOD )
            logger().log( "%08X" % fdod )

        logger().log( "\nComponents:" )
        for j in range(3):
            self.spi_reg_write( PCH_RCBA_SPI_FDOC, (PCH_RCBA_SPI_FDOC_FDSS_COMP|(j<<2)) )
            fdod = self.spi_reg_read( PCH_RCBA_SPI_FDOD )
            logger().log( "%08X" % fdod )

        logger().log( "\nRegions:" )
        for j in range(5):
            self.spi_reg_write( PCH_RCBA_SPI_FDOC, (PCH_RCBA_SPI_FDOC_FDSS_REGN|(j<<2)) )
            fdod = self.spi_reg_read( PCH_RCBA_SPI_FDOD )
            logger().log( "%08X" % fdod )

        logger().log( "\nMasters:" )
        for j in range(3):
            self.spi_reg_write( PCH_RCBA_SPI_FDOC, (PCH_RCBA_SPI_FDOC_FDSS_MSTR|(j<<2)) )
            fdod = self.spi_reg_read( PCH_RCBA_SPI_FDOD )
            logger().log( "%08X" % fdod )


    def display_SPI_opcode_info( self ):
        logger().log( "============================================================" )
        logger().log( "SPI Opcode Info" )
        logger().log( "------------------------------------------------------------" )
        optype = (self.spi_reg_read( PCH_RCBA_SPI_OPTYPE ) & 0xFFFF)
        logger().log( "OPTYPE = 0x%04X" % optype )
        opmenu_lo = self.spi_reg_read( PCH_RCBA_SPI_OPMENU )
        opmenu_hi = self.spi_reg_read( PCH_RCBA_SPI_OPMENU + 0x4 )
        opmenu = ((opmenu_hi << 32)|opmenu_lo)
        logger().log( "OPMENU = 0x%016X" % opmenu )

        logger().log( "------------------------------------------------------------" )
        logger().log( "Opcode # | Opcode | Optype | Description" )
        logger().log( "------------------------------------------------------------" )
        
        for j in range(8):
           optype_j = ((optype >> j*2) & 0x3)
           if (PCH_RCBA_SPI_OPTYPE_RDNOADDR == optype_j):
             desc = 'SPI read cycle without address'
           elif (PCH_RCBA_SPI_OPTYPE_WRNOADDR == optype_j):
             desc = 'SPI write cycle without address'
           elif (PCH_RCBA_SPI_OPTYPE_RDADDR == optype_j):
             desc = 'SPI read cycle with address'
           elif (PCH_RCBA_SPI_OPTYPE_WRADDR == optype_j):
             desc = 'SPI write cycle with address'
           logger().log( "Opcode%d  | 0x%02X   | %X      | %s " % (j,((opmenu >> j*8) & 0xFF),optype_j,desc) )

    def display_SPI_Flash_Regions( self ):
        logger().log( "------------------------------------------------------------" )
        logger().log( "Flash Region             | FREGx Reg | Base     | Limit     " )
        logger().log( "------------------------------------------------------------" )
        (base,limit,freg) = self.get_SPI_region( FLASH_DESCRIPTOR )
        logger().log( "0 Flash Descriptor (FD)  | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( BIOS )
        logger().log( "1 BIOS                   | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( ME )
        logger().log( "2 Management Engine (ME) | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( GBE )
        logger().log( "3 GBe                    | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( PLATFORM_DATA )
        logger().log( "4 Platform Data (PD)     | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( DEVICE_EXPANSION )
        logger().log( "5 Device Expansion (DE)  | %08X  | %08X | %08X " % (freg,base,limit) )
        (base,limit,freg) = self.get_SPI_region( SECONDARY_BIOS )
        logger().log( "6 Secondary BIOS (SB)    | %08X  | %08X | %08X " % (freg,base,limit) )

    def display_BIOS_region( self ):
        bfpreg = self.spi_reg_read( PCH_RCBA_SPI_BFPR )
        logger().log( "BIOS Flash Primary Region" )
        logger().log( "------------------------------------------------------------" )
        logger().log( "BFPREG = %08X:" % bfpreg )
        logger().log( "  Base  : %08X" % ((bfpreg & PCH_RCBA_SPI_FREGx_BASE_MASK) << 12) )
        logger().log( "  Limit : %08X" % ((bfpreg & PCH_RCBA_SPI_FREGx_LIMIT_MASK) >> 4) )
        logger().log( "  Shadowed BIOS Select: %d" % ((bfpreg & BIT31)>>31) )


    def display_SPI_Ranges_Access_Permissions( self ):
        logger().log( "SPI Flash Region Access Permissions" )
        logger().log( "------------------------------------------------------------" )
        fracc  = self.spi_reg_read( PCH_RCBA_SPI_FRAP )
        logger().log( "FRAP = %08X" % fracc )
        logger().log( "BIOS Region Write Access Grant (%02X):" % ((fracc & PCH_RCBA_SPI_FRAP_BMWAG_MASK)>>16) )
        logger().log( "  BIOS: %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMWAG_BIOS   != 0) )
        logger().log( "  ME  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMWAG_ME     != 0) )
        logger().log( "  GBe : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMWAG_GBE    != 0) )
        logger().log( "BIOS Region Read Access Grant (%02X):" % ((fracc & PCH_RCBA_SPI_FRAP_BMRAG_MASK)>>16) )
        logger().log( "  BIOS: %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMRAG_BIOS   != 0) )
        logger().log( "  ME  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMRAG_ME     != 0) )
        logger().log( "  GBe : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BMRAG_GBE    != 0) )
        logger().log( "BIOS Write Access (%02X):" % ((fracc & PCH_RCBA_SPI_FRAP_BRWA_MASK)>>8) )
        logger().log( "  FD  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_FLASHD != 0) )
        logger().log( "  BIOS: %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_BIOS   != 0) )
        logger().log( "  ME  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_ME     != 0) )
        logger().log( "  GBe : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_GBE    != 0) )
        logger().log( "  PD  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_PD     != 0) )
        logger().log( "  DE  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_DE     != 0) )
        logger().log( "  SB  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRWA_SB     != 0) )
        logger().log( "BIOS Read Access (%02X):" % (fracc & PCH_RCBA_SPI_FRAP_BRRA_MASK) )
        logger().log( "  FD  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_FLASHD != 0) )
        logger().log( "  BIOS: %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_BIOS   != 0) )
        logger().log( "  ME  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_ME     != 0) )
        logger().log( "  GBe : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_GBE    != 0) )
        logger().log( "  PD  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_PD     != 0) )
        logger().log( "  DE  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_DE     != 0) )
        logger().log( "  SB  : %1d" % (fracc&PCH_RCBA_SPI_FRAP_BRRA_SB     != 0) )


    def display_SPI_Protected_Ranges( self ):
        logger().log( "SPI Protected Ranges" )
        logger().log( "------------------------------------------------------------" )
        logger().log( "PRx (offset) | Value    | Base     | Limit    | WP? | RP?" )
        logger().log( "------------------------------------------------------------" )
        for j in range(5):
           (base,limit,wpe,rpe,pr_reg_off,pr_reg_value) = self.get_SPI_Protected_Range( j )
           logger().log( "PR%d (%02X)     | %08X | %08X | %08X | %d   | %d " % (j,pr_reg_off,pr_reg_value,base,limit,wpe,rpe) )

    def display_SPI_map( self ):
        logger().log( "============================================================" )
        logger().log( "SPI Flash Map" )
        logger().log( "------------------------------------------------------------" )
        logger().log('')
        self.display_BIOS_region()
        logger().log('')
        self.display_SPI_Flash_Regions()
        logger().log('')
        self.display_SPI_Flash_Descriptor()
        logger().log('')
        self.display_SPI_opcode_info()
        logger().log('')
        logger().log( "============================================================" )
        logger().log( "SPI Flash Protection" )
        logger().log( "------------------------------------------------------------" )
        logger().log('')
        self.display_SPI_Ranges_Access_Permissions()
        logger().log('')
        logger().log( "BIOS Region Write Protection" )
        logger().log( "------------------------------------------------------------" )
        (BC, val) = self.get_BIOS_Control()
        logger().log( BC )
        self.display_SPI_Protected_Ranges()
        logger().log('')


    ##############################################################################################################
    # BIOS Write Protection
    ##############################################################################################################

    def get_BIOS_Control( self ):
        #
        # BIOS Control (BC) 0:31:0 PCIe CFG register
        #
        reg_value = self.cs.pci.read_byte( 0, 31, 0, LPC_BC_REG_OFF )
        BcRegister = LPC_BC_REG( reg_value, (reg_value>>5)&0x1, (reg_value>>4)&0x1, (reg_value>>2)&0x3, (reg_value>>1)&0x1, reg_value&0x1 )
        return (BcRegister, reg_value)

    def disable_BIOS_write_protection( self ):
        (BcRegister, reg_value) = self.get_BIOS_Control()
        if logger().VERBOSE:
           logger().log( BcRegister )

        if BcRegister.BLE and (not BcRegister.BIOSWE):
           logger().log( "[spi] BIOS write protection enabled" )
           return False
        elif BcRegister.BIOSWE:
           logger().log( "[spi] BIOS write protection not enabled. What a surprise" )
           return True
        else:
           logger().log( "[spi] BIOS write protection enabled but not locked. Disabling.." )

        reg_value |= 0x1
        self.cs.pci.write_byte( 0, 31, 0, LPC_BC_REG_OFF, reg_value )
        (BcRegister, reg_value) = self.get_BIOS_Control()
        if logger().VERBOSE: logger().log( BcRegister )
        if BcRegister.BIOSWE:
           logger().log_important( "BIOS write protection is disabled" )
           return True
        else:
           return False

    ##############################################################################################################
    # SPI Controller access functions
    ##############################################################################################################

    def _wait_SPI_flash_cycle_done(self):
        if logger().VERBOSE:
           logger().log( "[spi] wait for SPI cycle ready/done.." )

        spi_base = self.rcba_spi_base

        for i in range(1000):
            #time.sleep(0.001)
            hsfsts = self.cs.mem.read_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFSTS )
            #hsfsts = self.spi_reg_read( PCH_RCBA_SPI_HSFSTS ) 
            #cycle_done = (hsfsts & PCH_RCBA_SPI_HSFSTS_FDONE) and (0 == (hsfsts & PCH_RCBA_SPI_HSFSTS_SCIP)) 
            cycle_done = not (hsfsts & PCH_RCBA_SPI_HSFSTS_SCIP)
            if cycle_done:
               break

        if not cycle_done:
           if logger().VERBOSE:
              logger().log( "[spi] SPI cycle still in progress. Waiting 0.1 sec.." )
           time.sleep(0.1)
           hsfsts = self.cs.mem.read_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFSTS )
           cycle_done = not (hsfsts & PCH_RCBA_SPI_HSFSTS_SCIP)

        if cycle_done:
           if logger().VERBOSE:
              logger().log( "[spi] clear FDONE/FCERR/AEL bits.." )
           self.cs.mem.write_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFSTS, HSFSTS_CLEAR )
           hsfsts = self.cs.mem.read_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFSTS )
           cycle_done = not ((hsfsts & PCH_RCBA_SPI_HSFSTS_AEL) or (hsfsts & PCH_RCBA_SPI_HSFSTS_FCERR))

        if logger().VERBOSE:
           logger().log( "[spi] HSFSTS: 0x%02X" % hsfsts )
              
        return cycle_done

    def _send_spi_cycle(self, hsfctl_spi_cycle_cmd, dbc, spi_fla ):
        if logger().VERBOSE:
           logger().log( "[spi] > send SPI cycle 0x%X to address 0x%08X.." % (hsfctl_spi_cycle_cmd, spi_fla) )

        spi_base = self.rcba_spi_base  

        # No need to check for SPI cycle DONE status before each cycle
        # DONE status is checked once before entire SPI operation
    
        self.cs.mem.write_physical_mem_dword( spi_base + PCH_RCBA_SPI_FADDR, (spi_fla & PCH_RCBA_SPI_FADDR_MASK) )
        _faddr = self.spi_reg_read( PCH_RCBA_SPI_FADDR ) 
        if logger().VERBOSE:
           logger().log( "[spi] FADDR: 0x%08X" % _faddr )
    
        if logger().VERBOSE:
           logger().log( "[spi] SPI cycle GO (DBC <- 0x%02X, HSFCTL <- 0x%X)" % (dbc, hsfctl_spi_cycle_cmd) )
        if ( HSFCTL_ERASE_CYCLE != hsfctl_spi_cycle_cmd ):
           self.cs.mem.write_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFCTL + 0x1, dbc ) 
        self.cs.mem.write_physical_mem_byte( spi_base + PCH_RCBA_SPI_HSFCTL, hsfctl_spi_cycle_cmd ) 
        # Read HSFCTL back
        hsfctl = self.cs.mem.read_physical_mem_word( spi_base + PCH_RCBA_SPI_HSFCTL )
        if logger().VERBOSE:
           logger().log( "[spi] HSFCTL: 0x%04X" % hsfctl )
    
        cycle_done = self._wait_SPI_flash_cycle_done()
        if not cycle_done:
           logger().warn( "SPI cycle not done" )
        else:
           if logger().VERBOSE:
              logger().log( "[spi] < SPI cycle done" )

        return cycle_done

    #
    # SPI Flash operations
    #

    def read_spi_to_file(self, spi_fla, data_byte_count, filename ):
        buf = self.read_spi( spi_fla, data_byte_count )
        if filename is not None:
           write_file( filename, struct.pack('c'*len(buf), *buf) )
        else:
           print_buffer( buf, 16 )
        return buf

    def write_spi_from_file(self, spi_fla, filename ):
        buf = read_file( filename )
        return self.write_spi( spi_fla, struct.unpack('c'*len(buf), buf) )
        #return self.write_spi( spi_fla, struct.unpack('B'*len(buf), buf) )

    def read_spi(self, spi_fla, data_byte_count ):
        spi_base = self.rcba_spi_base  
        buf = []      

        dbc = SPI_READ_WRITE_DEF_DBC
        if (data_byte_count >= SPI_READ_WRITE_MAX_DBC):
           dbc = SPI_READ_WRITE_MAX_DBC

        n = data_byte_count / dbc
        r = data_byte_count % dbc
        if logger().UTIL_TRACE or logger().VERBOSE:
           logger().log( "[spi] reading 0x%x bytes from SPI at FLA = 0x%X (in %d 0x%x-byte chunks + 0x%x-byte remainder)" % (data_byte_count, spi_fla, n, dbc, r) )

        cycle_done = self._wait_SPI_flash_cycle_done()
        if not cycle_done:
           logger().error( "SPI cycle not ready" )
           return None

        for i in range(n):
           if logger().UTIL_TRACE or logger().VERBOSE:
              logger().log( "[spi] reading chunk %d of 0x%x bytes from 0x%X" % (i, dbc, spi_fla + i*dbc) )
           if not self._send_spi_cycle( HSFCTL_READ_CYCLE, dbc-1, spi_fla + i*dbc ):
              logger().error( "SPI flash read failed" )
           else:
              #buf += self.cs.mem.read_physical_mem( spi_base + PCH_RCBA_SPI_FDATA00, dbc )
              for fdata_idx in range(0,dbc/4):
                  dword_value = self.spi_reg_read( PCH_RCBA_SPI_FDATA00 + fdata_idx*4 ) 
                  if logger().VERBOSE:
                     logger().log( "[spi] FDATA00 + 0x%x: 0x%X" % (fdata_idx*4, dword_value) )
                  buf += [ chr((dword_value>>(8*j))&0xff) for j in range(4) ]
                  #buf += tuple( struct.pack("I", dword_value) )
        if (0 != r):
           if logger().UTIL_TRACE or logger().VERBOSE:
              logger().log( "[spi] reading remaining 0x%x bytes from 0x%X" % (r, spi_fla + n*dbc) )
           if not self._send_spi_cycle( HSFCTL_READ_CYCLE, r-1, spi_fla + n*dbc ):
              logger().error( "SPI flash read failed" )
           else:
              t = 4
              n_dwords = (r+3)/4
              for fdata_idx in range(0, n_dwords):
                  dword_value = self.spi_reg_read( PCH_RCBA_SPI_FDATA00 + fdata_idx*4 ) 
                  if logger().VERBOSE:
                     logger().log( "[spi] FDATA00 + 0x%x: 0x%08X" % (fdata_idx*4, dword_value) )
                  if (fdata_idx == (n_dwords-1)) and (0 != r%4):
                     t = r%4  
                  buf += [ chr((dword_value >> (8*j)) & 0xff) for j in range(t) ]
           
        if logger().VERBOSE:
           logger().log( "[spi] buffer read from SPI:" )
           print_buffer( buf )

        return buf

    def write_spi(self, spi_fla, buf ):
        write_ok = True
        spi_base = self.rcba_spi_base  
        data_byte_count = len(buf)     
        dbc = 4       
        n = data_byte_count / dbc
        r = data_byte_count % dbc
        if logger().UTIL_TRACE or logger().VERBOSE:
           logger().log( "[spi] writing 0x%x bytes to SPI at FLA = 0x%X (in %d 0x%x-byte chunks + 0x%x-byte remainder)" % (data_byte_count, spi_fla, n, dbc, r) )

        cycle_done = self._wait_SPI_flash_cycle_done()
        if not cycle_done:
           logger().error( "SPI cycle not ready" )
           return None

        for i in range(n):
           if logger().UTIL_TRACE or logger().VERBOSE:
              logger().log( "[spi] writing chunk %d of 0x%x bytes to 0x%X" % (i, dbc, spi_fla + i*dbc) )
           dword_value = (ord(buf[i*dbc + 3]) << 24) | (ord(buf[i*dbc + 2]) << 16) | (ord(buf[i*dbc + 1]) << 8) | ord(buf[i*dbc])
           if logger().VERBOSE:
              logger().log( "[spi] in FDATA00 = 0x%08x" % dword_value )
           self.cs.mem.write_physical_mem_dword( spi_base + PCH_RCBA_SPI_FDATA00, dword_value )
           if not self._send_spi_cycle( HSFCTL_WRITE_CYCLE, dbc-1, spi_fla + i*dbc ):
              write_ok = False
              logger().error( "SPI flash write cycle failed" )

        if (0 != r):
           if logger().UTIL_TRACE or logger().VERBOSE:
              logger().log( "[spi] writing remaining 0x%x bytes to FLA = 0x%X" % (r, spi_fla + n*dbc) )
           dword_value = 0
           for j in range(r):
              dword_value |= (ord(buf[n*dbc + j]) << 8*j)
           if logger().VERBOSE:
              logger().log( "[spi] in FDATA00 = 0x%08x" % dword_value )
           self.cs.mem.write_physical_mem_dword( spi_base + PCH_RCBA_SPI_FDATA00, dword_value )
           if not self._send_spi_cycle( HSFCTL_WRITE_CYCLE, r-1, spi_fla + n*dbc ):
              write_ok = False
              logger().error( "SPI flash write cycle failed" )
           
        return write_ok

    def erase_spi_block(self, spi_fla ):
        if logger().UTIL_TRACE or logger().VERBOSE:
           logger().log( "[spi] Erasing SPI Flash block @ 0x%X" % spi_fla )

        cycle_done = self._wait_SPI_flash_cycle_done()
        if not cycle_done:
           logger().error( "SPI cycle not ready" )
           return None

        erase_ok = self._send_spi_cycle( HSFCTL_ERASE_CYCLE, 0, spi_fla )
        if not erase_ok:
           logger().error( "SPI Flash erase cycle failed" )

        return erase_ok

########NEW FILE########
__FILENAME__ = spi_descriptor
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/spi_descriptor.py
# ===========================================
# SPI Flash Descriptor binary parsing functionality
#
# ~~~
# #usage:
#   fd = read_file( fd_file )
#   parse_spi_flash_descriptor( fd )
# ~~~
#
__version__ = '1.0'

import struct
import sys
import time

from chipsec.logger import *
from chipsec.file import *

from chipsec.cfg.common import *
from chipsec.hal.spi import *

SPI_FLASH_DESCRIPTOR_SIGNATURE = struct.pack('=I', 0x0FF0A55A )
SPI_FLASH_DESCRIPTOR_SIZE      = 0x1000


def get_spi_flash_descriptor( rom ):  
    pos = rom.find( SPI_FLASH_DESCRIPTOR_SIGNATURE )
    if (-1 == pos or pos < 0x10):
       return (-1, None)
    fd_off = pos - 0x10
    fd = rom[ fd_off : fd_off + SPI_FLASH_DESCRIPTOR_SIZE ]
    return (fd_off, fd)


def get_SPI_master( flmstr ):
    requester_id  = (flmstr & 0xFFFF)
    master_region_ra = ((flmstr >> 16) & 0xFF)
    master_region_wa = ((flmstr >> 24) & 0xFF)
    return (requester_id, master_region_ra, master_region_wa)


def get_spi_regions( fd ):
    pos = fd.find( SPI_FLASH_DESCRIPTOR_SIGNATURE )
    if not (pos == 0x10):
        return None

    flmap0 = struct.unpack_from( '=I', fd[0x14:0x18] )[0]  
    # Flash Region Base Address (bits [23:16])
    frba = ( (flmap0 & 0x00FF0000) >> 12 )   
    # Number of Regions (bits [26:24])
    nr   = ( ((flmap0 & 0xFF000000) >> 24) & 0x7 )   

    flregs = [None]*SPI_REGION_NUMBER_IN_FD
    for r in range( SPI_REGION_NUMBER_IN_FD ):
        flreg_off = frba + r*4
        flreg = struct.unpack_from( '=I', fd[flreg_off:flreg_off + 0x4] )[0]
        (base,limit) = get_SPI_region( flreg )
        notused = (base > limit)
        flregs[r] = (r,SPI_REGION_NAMES[r],flreg,base,limit,notused)

    fd_size    = flregs[FLASH_DESCRIPTOR][4] - flregs[FLASH_DESCRIPTOR][3] + 1
    fd_notused = flregs[FLASH_DESCRIPTOR][5]
    if fd_notused or (fd_size != SPI_FLASH_DESCRIPTOR_SIZE):
        return None

    return flregs



def parse_spi_flash_descriptor( rom ):
    if not (type(rom) == str):
        logger().error('Invalid fd object type %s'%type(rom))
        return
    
    pos = rom.find( SPI_FLASH_DESCRIPTOR_SIGNATURE )
    if (-1 == pos or pos < 0x10):
       logger().error( 'Valid SPI flash descriptor is not found (should have signature %08X)' % SPI_FLASH_DESCRIPTOR_SIGNATURE )
       return None

    fd_off = pos - 0x10
    logger().log( '[spi_fd] Valid SPI flash descriptor found at offset 0x%08X' % fd_off )

    logger().log( '' )
    logger().log( '########################################################' )
    logger().log( '# SPI FLASH DESCRIPTOR' )
    logger().log( '########################################################' )
    logger().log( '' )

    fd     = rom[ fd_off : fd_off + SPI_FLASH_DESCRIPTOR_SIZE ]
    fd_sig = struct.unpack_from( '=I', fd[0x10:0x14] )

    logger().log( '+ 0x0000 Reserved : %016s' % fd[0x0:0xF].encode('hex').upper() )
    logger().log( '+ 0x0010 Signature: 0x%08X' % fd_sig )

    #
    # Flash Descriptor Map Section
    #
    #parse_spi_flash_descriptor_flmap( fd )
    logger().log( '' )
    logger().log( '+ 0x0014 Flash Descriptor Map:' )
    logger().log( '========================================================' )

    flmap0 = struct.unpack_from( '=I', fd[0x14:0x18] )[0]
    flmap1 = struct.unpack_from( '=I', fd[0x18:0x1C] )[0]
    flmap2 = struct.unpack_from( '=I', fd[0x1C:0x20] )[0]
    logger().log( '+ 0x0014 FLMAP0   : 0x%08X' % flmap0 )
    
    # Flash Component Base Address (bits [7:0])
    fcba = ( (flmap0 & 0x000000FF) << 4 )   
    # Number of Components (bits [9:8])
    nc   = ( ((flmap0 & 0x0000FF00) >> 8) & 0x3 )   
    # Flash Region Base Address (bits [23:16])
    frba = ( (flmap0 & 0x00FF0000) >> 12 )   
    # Number of Regions (bits [26:24])
    nr   = ( ((flmap0 & 0xFF000000) >> 24) & 0x7 )   
    logger().log( '  Flash Component Base Address        = 0x%08X' % fcba )
    logger().log( '  Number of Flash Components          = %d' % nc )
    logger().log( '  Flash Region Base Address           = 0x%08X' % frba )
    logger().log( '  Number of Flash Regions             = %d' % nr )

    logger().log( '+ 0x0018 FLMAP1   : 0x%08X' % flmap1 )

    # Flash Master Base Address (bits [7:0])
    fmba  = ( (flmap1 & 0x000000FF) << 4 )   
    # Number of Masters (bits [9:8])
    nm    = ( ((flmap1 & 0x0000FF00) >> 8) & 0x3 )   
    logger().log( '  Flash Master Base Address           = 0x%08X' % fmba )
    logger().log( '  Number of Masters                   = %d' % nm )

    logger().log( '+ 0x001C FLMAP2   : 0x%08X' % flmap2 )

    # ICC Register Init Base Address (bits [23:16])
    iccriba = ( (flmap2 & 0x00FF0000) >> 12 )   
    logger().log( '  ICC Register Init Base Address      = 0x%08X' % iccriba )

    #
    # Flash Descriptor Component Section
    #
    logger().log( '' )
    logger().log( '+ 0x%04X Component Section:' % fcba )
    logger().log( '========================================================' )

    flcomp = struct.unpack_from( '=I', fd[fcba+0x0:fcba+0x4] )[0]
    logger().log( '+ 0x%04X FLCOMP   : 0x%08X' % (fcba, flcomp) )
    flil   = struct.unpack_from( '=I', fd[fcba+0x4:fcba+0x8] )[0]
    logger().log( '+ 0x%04X FLIL     : 0x%08X' % (fcba+0x4, flil) )
    flpb   = struct.unpack_from( '=I', fd[fcba+0x8:fcba+0xC] )[0]
    logger().log( '+ 0x%04X FLPB     : 0x%08X' % (fcba+0x8, flpb) )

    #
    # Flash Descriptor Region Section
    #
    logger().log( '' )
    logger().log( '+ 0x%04X Region Section:' % frba )
    logger().log( '========================================================' )

    flregs = [None]*SPI_REGION_NUMBER_IN_FD
    for r in range( SPI_REGION_NUMBER_IN_FD ):
        flreg_off = frba + r*4
        flreg = struct.unpack_from( '=I', fd[flreg_off:flreg_off + 0x4] )[0]
        (base,limit) = get_SPI_region( flreg )
        notused = ''
        if base > limit:
           notused = '(not used)'
        flregs[r] = (flreg,base,limit,notused)
        logger().log( '+ 0x%04X FLREG%d   : 0x%08X %s' % (flreg_off,r,flreg,notused) )

    logger().log('')
    logger().log( 'Flash Regions' )
    logger().log( '--------------------------------------------------------' )
    logger().log( ' Region                | FLREGx    | Base     | Limit   ' )
    logger().log( '--------------------------------------------------------' )
    for r in range( SPI_REGION_NUMBER_IN_FD ):
        logger().log( '%d %-020s | %08X  | %08X | %08X %s' % (r,SPI_REGION_NAMES[r],flregs[r][0],flregs[r][1],flregs[r][2],flregs[r][3]) )

    #
    # Flash Descriptor Master Section
    #
    logger().log( '' )
    logger().log( '+ 0x%04X Master Section:' % fmba )
    logger().log( '========================================================' )

    flmstrs = [None]*SPI_MASTER_NUMBER_IN_FD
    for m in range( SPI_MASTER_NUMBER_IN_FD ):
        flmstr_off = fmba + m*4
        flmstr = struct.unpack_from( '=I', fd[flmstr_off:flmstr_off + 0x4] )[0]
        (requester_id, master_region_ra, master_region_wa) = get_SPI_master( flmstr )
        flmstrs[m] = (flmstr, requester_id, master_region_ra, master_region_wa)
        logger().log( '+ 0x%04X FLMSTR%d   : 0x%08X' % (flmstr_off,m,flmstr) )
 
    logger().log('')
    logger().log( 'Master Read/Write Access to Flash Regions' )
    logger().log( '--------------------------------------------------------' )
    s = ' Region                '
    for m in range( SPI_MASTER_NUMBER_IN_FD ):
        s = s + '| ' + ('%-9s' % SPI_MASTER_NAMES[m])
    logger().log( s )
    logger().log( '--------------------------------------------------------' )
    for r in range( SPI_REGION_NUMBER_IN_FD ):
        s = '%d %-020s ' % (r,SPI_REGION_NAMES[r])
        for m in range( SPI_MASTER_NUMBER_IN_FD ):
            access_s = ''
            mask = (0x1 << r) & 0xFF
            if (flmstrs[m][2] & mask):
                access_s = access_s + 'R'
            if (flmstrs[m][3] & mask):
                access_s = access_s + 'W'
            s = s + '| ' + ('%-9s' % access_s)
        logger().log( s )

    #
    # Flash Descriptor Upper Map Section
    #
    logger().log( '' )
    logger().log( '+ 0x%04X Flash Descriptor Upper Map:' % 0xEFC )
    logger().log( '========================================================' )

    flumap1 = struct.unpack_from( '=I', fd[0xEFC:0xF00] )[0]
    logger().log( '+ 0x%04X FLUMAP1   : 0x%08X' % (0xEFC, flumap1) )

    vtba = ( (flumap1 & 0x000000FF) << 4 )   
    vtl  = ( ((flumap1 & 0x0000FF00) >> 8) & 0xFF )   
    logger().log( '  VSCC Table Base Address    = 0x%08X' % vtba )
    logger().log( '  VSCC Table Length          = 0x%02X' % vtl )

    #
    # OEM Section
    #
    logger().log( '' )
    logger().log( '+ 0x%04X OEM Section:' % 0xF00 )
    logger().log( '========================================================' )
    print_buffer( fd[0xF00:] )

    logger().log( '' )
    logger().log( '########################################################' )
    logger().log( '# END OF SPI FLASH DESCRIPTOR' )
    logger().log( '########################################################' )

########NEW FILE########
__FILENAME__ = spi_uefi
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/spi_uefi.py
# =============================
# SPI UEFI Region parsing
# ~~~
# #usage:
#   parse_uefi_region_from_file( filename )
# ~~~
#
__version__ = '1.0'

import os
import fnmatch
import struct
import sys
import time
import collections
#import phex

from chipsec.helper.oshelper import helper
from chipsec.logger import *
from chipsec.file import *

from chipsec.cfg.common import *
from chipsec.hal.uefi_common import *
from chipsec.hal.uefi_platform import *

def save_vol_info( FvOffset, FsGuid, FvLength, FvAttributes, FvHeaderLength, FvChecksum, ExtHeaderOffset, file_path, CalcSum ):
    schecksum = ''
    if (CalcSum != FvChecksum): schecksum = ' *** checksum mismatch ***'
    info = ("Volume offset          : 0x%08X\n" % FvOffset) +\
           ("File system GUID       : %s\n" % FsGuid) + \
           ("Volume length          : 0x%08X (%d)\n" % (FvLength, FvLength)) + \
           ("Attributes             : 0x%08X\n" % FvAttributes) + \
           ("Header length          : 0x%08X\n" % FvHeaderLength) + \
           ("Checksum               : 0x%04X (0x%04X)%s\n" % (FvChecksum, CalcSum, schecksum)) + \
           ("Extended Header Offset : 0x%08X\n" % ExtHeaderOffset)
    logger().log( info )
    #write_file( file_path, info, True )

def save_file_info( cur_offset, Name, Type, Attributes, State, Checksum, Size, file_path, fCalcSum ):
    schecksum = ''
    if (fCalcSum != Checksum): schecksum = ' *** checksum mismatch ***'
    info = ("\tFile offset : 0x%08X\n" % (cur_offset)) + \
           ("\tName        : %s\n" % (Name)) + \
           ("\tType        : 0x%02X\n" % (Type)) + \
           ("\tAttributes  : 0x%08X\n" % (Attributes)) + \
           ("\tState       : 0x%02X\n" % (State)) + \
           ("\tChecksum    : 0x%04X (0x%04X)%s\n" % (Checksum, fCalcSum, schecksum)) + \
           ("\tSize        : 0x%06X (%d)\n" % (Size, Size))
    logger().log( info )
    #write_file( file_path, info, True )

def save_section_info( cur_offset, Name, Type, file_path ):
    info = ("\t\tSection offset : 0x%08X\n" % (cur_offset)) + \
           ("\t\tName           : %s\n" % (Name)) + \
           ("\t\tType           : 0x%02X\n" % (Type))
    logger().log( info )

def parse_uefi_section( _uefi, data, Size, offset, polarity, parent_offset, parent_path, decode_log_path ):
   sec_offset, next_sec_offset, SecName, SecType, SecBody, SecHeaderSize = NextFwFileSection(data, Size, offset, polarity)
   secn = 0
   ui_string = None
   efi_file = None
   while next_sec_offset != None:
      if (SecName != None):
         save_section_info( parent_offset + sec_offset, SecName, SecType, decode_log_path )
         sec_fs_name = "%02d_%s" % (secn, SecName)
         section_path = os.path.join(parent_path, sec_fs_name)
         if (SecType in (EFI_SECTION_PE32, EFI_SECTION_TE, EFI_SECTION_PIC, EFI_SECTION_COMPATIBILITY16)):
            type2ext = {EFI_SECTION_PE32: 'pe32', EFI_SECTION_TE: 'te', EFI_SECTION_PIC: 'pic', EFI_SECTION_COMPATIBILITY16: 'c16'}
            sec_fs_name = "%02d_%s.%s.efi" % (secn, SecName, type2ext[SecType])
            if ui_string != None:
               sec_fs_name = ui_string
               ui_string = None
            efi_file = sec_fs_name
            section_path = os.path.join(parent_path, sec_fs_name)
            write_file( section_path, SecBody[SecHeaderSize:] )
         else:
            write_file( section_path, SecBody[SecHeaderSize:] )
            if (SecType == EFI_SECTION_USER_INTERFACE):
               ui_string = unicode(SecBody[SecHeaderSize:], "utf-16-le")[:-1]
               if (ui_string[-4:] != '.efi'): ui_string = "%s.efi" % ui_string
               #print ui_string
               if efi_file != None:
                  os.rename(os.path.join(parent_path, efi_file), os.path.join(parent_path, ui_string))
                  efi_file = None
         if (SecType in (EFI_SECTION_COMPRESSION, EFI_SECTION_GUID_DEFINED, EFI_SECTION_FIRMWARE_VOLUME_IMAGE)):
            section_dir_path = "%s.dir" % section_path
            os.makedirs( section_dir_path )
            if   (SecType == EFI_SECTION_COMPRESSION):
               UncompressedLength, CompressionType = struct.unpack(EFI_COMPRESSION_SECTION, SecBody[SecHeaderSize:SecHeaderSize+EFI_COMPRESSION_SECTION_size])
               compressed_name = os.path.join(section_dir_path, "%s.gz" % sec_fs_name)
               uncompressed_name = os.path.join(section_dir_path, sec_fs_name)
               write_file(compressed_name, SecBody[SecHeaderSize+EFI_COMPRESSION_SECTION_size:])
               # TODO: decompress section
               decompressed = DecompressSection(compressed_name, uncompressed_name, CompressionType)
               if decompressed:
                  parse_uefi_section(_uefi, decompressed, len(decompressed), 0, polarity, 0, section_dir_path, decode_log_path)
                  pass
            elif (SecType == EFI_SECTION_GUID_DEFINED):
               # TODO: decode section based on its GUID
               # Only CRC32 guided sectioni can be decoded for now
               guid0, guid1, guid2, guid3, DataOffset, Attributes = struct.unpack(EFI_GUID_DEFINED_SECTION, SecBody[SecHeaderSize:SecHeaderSize+EFI_GUID_DEFINED_SECTION_size])
               sguid = guid_str(guid0, guid1, guid2, guid3)
               if (sguid == EFI_CRC32_GUIDED_SECTION_EXTRACTION_PROTOCOL_GUID):
                  parse_uefi_section(_uefi, SecBody[DataOffset:], Size - DataOffset, 0, polarity, 0, section_dir_path, decode_log_path)
               #else:
               #   write_file( os.path.join(section_dir_path, "%s-%04X" % (sguid, Attributes)), SecBody[DataOffset:] )
               pass
            elif (SecType == EFI_SECTION_FIRMWARE_VOLUME_IMAGE):
               parse_uefi_region(_uefi, SecBody[SecHeaderSize:], section_dir_path)
      sec_offset, next_sec_offset, SecName, SecType, SecBody, SecHeaderSize = NextFwFileSection(data, Size, next_sec_offset, polarity)
      secn = secn + 1

def parse_uefi_region( _uefi, data, uefi_region_path ):
    voln = 0
    FvOffset, FsGuid, FvLength, FvAttributes, FvHeaderLength, FvChecksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(data)
    while FvOffset != None:
        decode_log_path = os.path.join(uefi_region_path, "efi_firmware_volumes.log")
        volume_file_path = os.path.join( uefi_region_path, "%02d_%s" % (voln, FsGuid) )
        volume_path = os.path.join( uefi_region_path, "%02d_%s.dir" % (voln, FsGuid) )
        if not os.path.exists( volume_path ):
           os.makedirs( volume_path )
        write_file( volume_file_path, FvImage )
        save_vol_info( FvOffset, FsGuid, FvLength, FvAttributes, FvHeaderLength, FvChecksum, ExtHeaderOffset, decode_log_path, CalcSum )

        polarity = bit_set(FvAttributes, EFI_FVB2_ERASE_POLARITY)
        if (FsGuid == ADDITIONAL_NV_STORE_GUID):
           nvram_fname = os.path.join(volume_path, 'SHADOW_NVRAM')
           _uefi.parse_EFI_variables( nvram_fname, FvImage, False, 'evsa' )
        elif ((FsGuid == EFI_FIRMWARE_FILE_SYSTEM2_GUID) or (FsGuid == EFI_FIRMWARE_FILE_SYSTEM_GUID)):
           cur_offset, next_offset, Name, Type, Attributes, State, Checksum, Size, FileImage, HeaderSize, UD, fCalcSum = NextFwFile(FvImage, FvLength, FvHeaderLength, polarity)
           while next_offset != None:
              #print "File: offset=%08X, next_offset=%08X, UD=%s\n" % (cur_offset, next_offset, UD)
              if (Name != None):
                 file_type_str = "UNKNOWN_%02X" % Type
                 if Type in FILE_TYPE_NAMES.keys():
                    file_type_str = FILE_TYPE_NAMES[Type]
                 file_path = os.path.join( volume_path, "%s.%s-%02X" % (Name, file_type_str, Type))
                 if os.path.exists( file_path ):
                    file_path = file_path + ("_%08X" % cur_offset)
                 write_file( file_path, FileImage )
                 file_dir_path = "%s.dir" % file_path
                 save_file_info( FvOffset + cur_offset, Name, Type, Attributes, State, Checksum, Size, decode_log_path, fCalcSum)
                 if (Type not in (EFI_FV_FILETYPE_ALL, EFI_FV_FILETYPE_RAW, EFI_FV_FILETYPE_FFS_PAD)):
                    os.makedirs( file_dir_path )
                    parse_uefi_section(_uefi, FileImage, Size, HeaderSize, polarity, FvOffset + cur_offset, file_dir_path, decode_log_path)
                 elif (Type == EFI_FV_FILETYPE_RAW):
                    if ((Name == NVAR_NVRAM_FS_FILE) and UD):
                       nvram_fname = os.path.join(file_dir_path, 'SHADOW_NVRAM')
                       _uefi.parse_EFI_variables( nvram_fname, FvImage, False, 'nvar' )
              cur_offset, next_offset, Name, Type, Attributes, State, Checksum, Size, FileImage, HeaderSize, UD, fCalcSum = NextFwFile(FvImage, FvLength, next_offset, polarity)
        FvOffset, FsGuid, FvLength, Attributes, HeaderLength, Checksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(data, FvOffset+FvLength)
        voln = voln + 1

def parse_uefi_region_from_file( _uefi, filename, outpath = None):

    if outpath is None:
       outpath = os.path.join( helper().getcwd(), filename + ".dir" )
    if not os.path.exists( outpath ):
       os.makedirs( outpath )

    #uefi_region_path = os.path.join( os.getcwd(), filename + "_UEFI_region" )
    #if not os.path.exists( uefi_region_path ):
    #    os.makedirs( uefi_region_path )

    rom = read_file( filename )
    parse_uefi_region( _uefi, rom, outpath )

           
def decode_uefi_region(_uefi, pth, fname, fwtype):
    bios_pth = os.path.join( pth, fname + '.dir' )
    if not os.path.exists( bios_pth ):
        os.makedirs( bios_pth )
    fv_pth = os.path.join( bios_pth, 'FV' )
    if not os.path.exists( fv_pth ):
        os.makedirs( fv_pth )
    parse_uefi_region_from_file( _uefi, fname, fv_pth )
    # Decoding EFI Variables NVRAM
    region_data = read_file( fname )
    nvram_fname = os.path.join( bios_pth, ('nvram_%s' % fwtype) )
    logger().set_log_file( (nvram_fname + '.nvram.lst') )
    _uefi.parse_EFI_variables( nvram_fname, region_data, False, fwtype )

########NEW FILE########
__FILENAME__ = ucode
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/ucode.py
# =============
# Microcode update specific functionality (for each CPU thread)
# ~~~
# #usage:
#     ucode_update_id( 0 )
#     load_ucode_update( 0, ucode_buf )
#     update_ucode_all_cpus( 'ucode.pdb' )
#     dump_ucode_update_header( 'ucode.pdb' )
# ~~~
#
__version__ = '1.0'

import struct
import sys

from chipsec.logger import *
from chipsec.hal.physmem import *
from chipsec.hal.msr import *
from chipsec.file import *

IA32_MSR_BIOS_UPDT_TRIG      = 0x79
IA32_MSR_BIOS_SIGN_ID        = 0x8B
IA32_MSR_BIOS_SIGN_ID_STATUS = 0x1


from collections import namedtuple
class UcodeUpdateHeader( namedtuple('UcodeUpdateHeader', 'header_version update_revision date processor_signature checksum loader_revision processor_flags data_size total_size reserved1 reserved2 reserved3') ):
      __slots__ = ()
      def __str__(self):
          return """
Microcode Update Header
--------------------------------
Header Version      : 0x%08X 
Update Revision     : 0x%08X
Date                : 0x%08X
Processor Signature : 0x%08X
Checksum            : 0x%08X
Loader Revision     : 0x%08X
Processor Flags     : 0x%08X
Update Data Size    : 0x%08X
Total Size          : 0x%08X
Reserved1           : 0x%08X
Reserved2           : 0x%08X
Reserved3           : 0x%08X
""" % ( self.header_version, self.update_revision, self.date, self.processor_signature, self.checksum, self.loader_revision, self.processor_flags, self.data_size, self.total_size, self.reserved1, self.reserved2, self.reserved3 )         

UCODE_HEADER_SIZE = 0x30
def dump_ucode_update_header( pdb_ucode_buffer ):
    ucode_header = UcodeUpdateHeader( *struct.unpack_from( '12I', pdb_ucode_buffer ) )
    print ucode_header
    return ucode_header

def read_ucode_file( ucode_filename ):
    ucode_buf = read_file( ucode_filename )
    if (ucode_filename.endswith('.pdb')):
       if logger().VERBOSE:
          logger().log( "[ucode] PDB file '%.256s' has ucode update header (size = 0x%X)" % (ucode_filename, UCODE_HEADER_SIZE) )
       dump_ucode_update_header( ucode_buf )
       return ucode_buf[UCODE_HEADER_SIZE:]
    else:
       return ucode_buf


class Ucode:
    def __init__( self, helper ):
        self.helper = helper

    # @TODO remove later/replace with msr.get_cpu_thread_count()
    def get_cpu_thread_count( self ):
        (core_thread_count, dummy) = self.helper.read_msr( 0, IA32_MSR_CORE_THREAD_COUNT )
        return (core_thread_count & IA32_MSR_CORE_THREAD_COUNT_THREADCOUNT_MASK)

    def ucode_update_id(self, cpu_thread_id):
        #self.helper.write_msr( cpu_thread_id, IA32_MSR_BIOS_SIGN_ID, 0, 0 )
        #self.helper.cpuid( cpu_thread_id, 0 )
        (bios_sign_id_lo, bios_sign_id_hi) = self.helper.read_msr( cpu_thread_id, IA32_MSR_BIOS_SIGN_ID )
        ucode_update_id = bios_sign_id_hi

        if (bios_sign_id_lo & IA32_MSR_BIOS_SIGN_ID_STATUS):
           if logger().VERBOSE: logger().log( "[ucode] CPU%d: last Microcode update failed (current microcode id = 0x%08X)" % (cpu_thread_id, ucode_update_id) )       
        else:
           if logger().VERBOSE: logger().log( "[ucode] CPU%d: Microcode update ID = 0x%08X" % (cpu_thread_id, ucode_update_id) )

        return ucode_update_id

    def update_ucode_all_cpus(self, ucode_file ):
        if not ( os.path.exists(ucode_file) and os.path.isfile(ucode_file) ):
           logger().error( "Ucode file not found: '%.256s'" % ucode_file )
           return False
        ucode_buf = read_ucode_file( ucode_file )
        if (ucode_buf is not None) and (len(ucode_buf) > 0):
           for tid in range(self.get_cpu_thread_count()):
              self.load_ucode_update( tid, ucode_buf )    
        return True

    def update_ucode(self, cpu_thread_id, ucode_file ):
        if not ( os.path.exists(ucode_file) and os.path.isfile(ucode_file) ):
           logger().error( "Ucode file not found: '%.256s'" % ucode_file )
           return False
        _ucode_buf = read_ucode_file( ucode_file )
        return self.load_ucode_update( cpu_thread_id, _ucode_buf )

    def load_ucode_update(self, cpu_thread_id, ucode_buf ):
        logger().log( "[ucode] loading microcode update on CPU%d" % cpu_thread_id )       
        self.helper.load_ucode_update( cpu_thread_id, ucode_buf )
        return self.ucode_update_id( cpu_thread_id )


########NEW FILE########
__FILENAME__ = uefi
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/uefi.py
# ============================
# Main UEFI component using platform specific and common UEFI functionality
#
#
#
__version__ = '1.0'

import struct
import sys

from collections import namedtuple
import collections

from chipsec.hal.uefi_common import *
from chipsec.hal.uefi_platform import *

from chipsec.logger import *
from chipsec.hal.mmio import *
from chipsec.hal.spi import *
from chipsec.file import *


EFI_VAR_NAME_PK         = 'PK'
EFI_VAR_NAME_KEK        = 'KEK'
EFI_VAR_NAME_db         = 'db'
EFI_VAR_NAME_dbx        = 'dbx'
EFI_VAR_NAME_SecureBoot = 'SecureBoot'
EFI_VAR_NAME_SetupMode  = 'SetupMode'
EFI_VAR_NAME_CustomMode = 'CustomMode'

EFI_VAR_GUID_SecureBoot = '8BE4DF61-93CA-11D2-AA0D-00E098032B8C'
EFI_VAR_GUID_db         = 'D719B2CB-3D3A-4596-A3BC-DAD00E67656F'

EFI_VARIABLE_DICT = {
EFI_VAR_NAME_PK        : EFI_VAR_GUID_SecureBoot,
EFI_VAR_NAME_KEK       : EFI_VAR_GUID_SecureBoot,
EFI_VAR_NAME_db        : EFI_VAR_GUID_db,
EFI_VAR_NAME_dbx       : EFI_VAR_GUID_db,
EFI_VAR_NAME_SecureBoot: EFI_VAR_GUID_SecureBoot,
EFI_VAR_NAME_SetupMode : EFI_VAR_GUID_SecureBoot,
EFI_VAR_NAME_CustomMode: EFI_VAR_GUID_SecureBoot
}


SECURE_BOOT_KEY_VARIABLES = (EFI_VAR_NAME_PK, EFI_VAR_NAME_KEK, EFI_VAR_NAME_db, EFI_VAR_NAME_dbx)
SECURE_BOOT_VARIABLES     = (EFI_VAR_NAME_SecureBoot, EFI_VAR_NAME_SetupMode, EFI_VAR_NAME_CustomMode) + SECURE_BOOT_KEY_VARIABLES
AUTHENTICATED_VARIABLES   = ('AuthVarKeyDatabase', 'certdb') + SECURE_BOOT_VARIABLES
SUPPORTED_EFI_VARIABLES   = ('BootOrder', 'Boot####', 'DriverOrder', 'Driver####') + AUTHENTICATED_VARIABLES


def get_attr_string( attr ):
    attr_str = ' '
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_NON_VOLATILE ):
       attr_str = attr_str + 'NV+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_BOOTSERVICE_ACCESS ):
       attr_str = attr_str + 'BS+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_RUNTIME_ACCESS ):
       attr_str = attr_str + 'RT+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_HARDWARE_ERROR_RECORD ):
       attr_str = attr_str + 'HER+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS ):
       attr_str = attr_str + 'AWS+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS ):
       attr_str = attr_str + 'TBAWS+'
    if IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_APPEND_WRITE ):
       attr_str = attr_str + 'AW+'
    return attr_str[:-1].lstrip()



def print_efi_variable( offset, efi_var_buf, EFI_var_header, efi_var_name, efi_var_data, efi_var_guid, efi_var_attributes ):
        logger().log( '\n--------------------------------' )
        logger().log( 'EFI Variable (offset = 0x%x):' % offset )
        logger().log( '--------------------------------' )

        # Print Variable Name
        logger().log( 'Name      : %s' % efi_var_name )
        # Print Variable GUID
        logger().log( 'Guid      : %s' % efi_var_guid )

        # Print Variable State
        if EFI_var_header:
           if 'State' in EFI_var_header._fields:
              state = getattr(EFI_var_header, 'State')
              state_str = 'State     :'
              if IS_VARIABLE_STATE( state, VAR_IN_DELETED_TRANSITION ):
                 state_str = state_str + ' IN_DELETED_TRANSITION +'
              if IS_VARIABLE_STATE( state, VAR_DELETED ):
                 state_str = state_str + ' DELETED +'
              if IS_VARIABLE_STATE( state, VAR_ADDED ):
                 state_str = state_str + ' ADDED +'
              logger().log( state_str )
        
           # Print Variable Complete Header
           if logger().VERBOSE:
              if EFI_var_header.__str__:
                 logger().log( EFI_var_header )
              else:
                 logger().log( 'Decoded Header (%s):' % EFI_VAR_DICT[ self._FWType ]['name'] )
                 for attr in EFI_var_header._fields:
                    logger().log( '%s = %X' % ('{0:<16}'.format(attr), getattr(EFI_var_header, attr)) )
        
        attr_str = ('Attributes: 0x%X ( ' % efi_var_attributes) + get_attr_string( efi_var_attributes ) + ' )'
        logger().log( attr_str )
        
        # Print Variable Data
        logger().log( 'Data:' )
        print_buffer( efi_var_data )

        # Print Variable Full Contents
        if logger().VERBOSE:
           logger().log( 'Full Contents:' )
           print_buffer( efi_var_buf )


def print_sorted_EFI_variables( variables ):
    sorted_names = sorted(variables.keys())
    for name in sorted_names:
        for rec in variables[name]:
            #                   off,    buf,     hdr,         data,   guid,   attrs
            print_efi_variable( rec[0], rec[1], rec[2], name, rec[3], rec[4], rec[5] )

def decode_EFI_variables( efi_vars, nvram_pth ):
    # print decoded and sorted EFI variables into a log file
    print_sorted_EFI_variables( efi_vars )
    # write each EFI variable into its own binary file
    for name in efi_vars.keys():
        n = 0
        for (off, buf, hdr, data, guid, attrs) in efi_vars[name]:
            # efi_vars[name] = (off, buf, hdr, data, guid, attrs)
            attr_str = get_attr_string( attrs )
            var_fname = os.path.join( nvram_pth, '%s_%s_%s_%d.bin' % (name, guid, attr_str.strip(), n) )
            write_file( var_fname, data )
            #if name in SECURE_BOOT_VARIABLES:
            if name in AUTHENTICATED_VARIABLES:
                parse_efivar_file( var_fname, data )
            n = n+1


class UEFI:
    def __init__( self, helper ):
        self.helper = helper
        self._FWType = FWType.EFI_FW_TYPE_UEFI

    ######################################################################
    # FWType defines platform/BIOS dependent formats like 
    # format of EFI NVRAM, format of FV, etc.
    #
    # FWType chooses an element from the EFI_VAR_DICT Dictionary
    #
    # Default current platform type is EFI_FW_TYPE_UEFI
    ######################################################################

    def set_FWType( self, efi_nvram_format ):
        if efi_nvram_format in fw_types:
            self._FWType = efi_nvram_format


    ######################################################################
    # EFI NVRAM Parsing Functions
    ######################################################################

    def dump_EFI_variables_from_SPI( self ):
        return self.read_EFI_variables_from_SPI( 0, 0x800000 )

    def read_EFI_variables_from_SPI( BIOS_region_base, BIOS_region_size ):
        rom = spi.read_spi( BIOS_region_base, BIOS_region_size )
        efi_var_store = self.find_EFI_Variable_Store( rom )
        return self.read_EFI_NVRAM_variables( efi_var_store )

    def read_EFI_variables_from_file( self, filename ):
        rom = read_file( filename )
        efi_var_store = self.find_EFI_Variable_Store( rom )
        return self.read_EFI_NVRAM_variables( efi_var_store )

    def find_EFI_variable_store( self, rom_buffer ):
        if ( rom_buffer is None ):
           logger().error( 'rom_buffer is None' )
           return None
        # Meh..
        rom = "".join( rom_buffer )
        offset       = 0
        size         = len(rom_buffer)
        nvram_header = None

        if EFI_VAR_DICT[ self._FWType ]['func_getnvstore']:
           (offset, size, nvram_header) = EFI_VAR_DICT[ self._FWType ]['func_getnvstore']( rom )
           if (-1 == offset):
              logger().error( "'func_getnvstore' is defined but could not find EFI NVRAM. Exiting.." )
              return None
        else:
           logger().log( "[uefi] 'func_getnvstore' is not defined in EFI_VAR_DICT. Assuming start offset 0.." )

        if -1 == size: size = len(rom_buffer)
        nvram_buf = rom[ offset : offset + size ]

        if logger().UTIL_TRACE:
            logger().log( '[uefi] Found EFI NVRAM at offset 0x%08X' % offset )
            logger().log( """
==================================================================
NVRAM: EFI Variable Store
==================================================================""")
            if nvram_header: logger().log( nvram_header )
        return nvram_buf


    # @TODO: Do not use, will be removed
    def read_EFI_variables( self, efi_var_store, authvars ):
        if ( efi_var_store is None ):
           logger().error( 'efi_var_store is None' )
           return None
        variables = EFI_VAR_DICT[ self._FWType ]['func_getefivariables']( efi_var_store )
        if logger().UTIL_TRACE: print_sorted_EFI_variables( variables )
        return variables


    def parse_EFI_variables( self, fname, rom, authvars, _fw_type=None ):
        if _fw_type in fw_types:
           logger().log( "[uefi] Using FW type (NVRAM format): %s" % _fw_type )
           self.set_FWType( _fw_type )
        else:
           logger().error( "Unrecognized FW type (NVRAM format) '%s'.." % _fw_type )
           return False

        logger().log( "[uefi] Searching for NVRAM in the binary.." )
        efi_vars_store = self.find_EFI_variable_store( rom )
        if efi_vars_store:
           nvram_fname = fname + '.nvram.bin'
           write_file( nvram_fname, efi_vars_store )
           nvram_pth = fname + '.nvram.dir'
           if not os.path.exists( nvram_pth ):
               os.makedirs( nvram_pth )
           logger().log( "[uefi] Extracting EFI Variables in the NVRAM.." )
           efi_vars = EFI_VAR_DICT[ self._FWType ]['func_getefivariables']( efi_vars_store )
           decode_EFI_variables( efi_vars, nvram_pth )
        else:
           logger().error( "Did not find NVRAM" )
           return False

        return True


    ######################################################################
    # Runtime Variable API Functions
    ######################################################################

    def list_EFI_variables( self ):
        return self.helper.list_EFI_variables()

    def get_EFI_variable( self, name, guid, filename=None ):
        var = self.helper.get_EFI_variable( name, guid )
        if var:
           if filename: write_file( filename, var )
           if logger().UTIL_TRACE or logger().VERBOSE:
              logger().log( '[uefi] EFI variable:' )
              logger().log( 'Name: %s' % name )
              logger().log( 'GUID: %s' % guid )
              logger().log( 'Data:' )
              print_buffer( var )
        return var

    def set_EFI_variable( self, name, guid, var ):
        if logger().UTIL_TRACE or logger().VERBOSE:
           logger().log( '[uefi] Writing EFI variable:' )
           logger().log( 'Name: %s' % name )
           logger().log( 'GUID: %s' % guid )
           #print_buffer( var )
        return self.helper.set_EFI_variable( name, guid, var )

    def set_EFI_variable_from_file( self, name, guid, filename=None ):
        if not filename:
           logger().error( 'File with EFI variable is not specified' )
           return False
        var = read_file( filename )
        return self.set_EFI_variable( name, guid, var )

    def delete_EFI_variable( self, name, guid ):
        if logger().UTIL_TRACE or logger().VERBOSE:
           logger().log( '[uefi] Deleting EFI variable:' )
           logger().log( 'Name: %s' % name )
           logger().log( 'GUID: %s' % guid )
        return self.helper.set_EFI_variable( name, guid, None )




########NEW FILE########
__FILENAME__ = uefi_common
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/uefi_common.py
# ==========================
# Common UEFI functionality (EFI variables, db/dbx decode, etc.)
#
#
__version__ = '1.0'

import os
import struct
from collections import namedtuple

from chipsec.file import *
from chipsec.logger import *

################################################################################################
# EFI Variable and Variable Store Defines
#

"""
UDK2010.SR1\MdeModulePkg\Include\Guid\VariableFormat.h 

#ifndef __VARIABLE_FORMAT_H__
#define __VARIABLE_FORMAT_H__

#define EFI_VARIABLE_GUID \
  { 0xddcf3616, 0x3275, 0x4164, { 0x98, 0xb6, 0xfe, 0x85, 0x70, 0x7f, 0xfe, 0x7d } }

extern EFI_GUID gEfiVariableGuid;

///
/// Alignment of variable name and data, according to the architecture:
/// * For IA-32 and Intel(R) 64 architectures: 1.
/// * For IA-64 architecture: 8.
///
#if defined (MDE_CPU_IPF)
#define ALIGNMENT         8
#else
#define ALIGNMENT         1
#endif

//
// GET_PAD_SIZE calculates the miminal pad bytes needed to make the current pad size satisfy the alignment requirement.
//
#if (ALIGNMENT == 1)
#define GET_PAD_SIZE(a) (0)
#else
#define GET_PAD_SIZE(a) (((~a) + 1) & (ALIGNMENT - 1))
#endif

///
/// Alignment of Variable Data Header in Variable Store region.
///
#define HEADER_ALIGNMENT  4
#define HEADER_ALIGN(Header)  (((UINTN) (Header) + HEADER_ALIGNMENT - 1) & (~(HEADER_ALIGNMENT - 1)))

///
/// Status of Variable Store Region.
///
typedef enum {
  EfiRaw,
  EfiValid,
  EfiInvalid,
  EfiUnknown
} VARIABLE_STORE_STATUS;

#pragma pack(1)

#define VARIABLE_STORE_SIGNATURE  EFI_VARIABLE_GUID

///
/// Variable Store Header Format and State.
///
#define VARIABLE_STORE_FORMATTED          0x5a
#define VARIABLE_STORE_HEALTHY            0xfe

///
/// Variable Store region header.
///
typedef struct {
  ///
  /// Variable store region signature.
  ///
  EFI_GUID  Signature;
  ///
  /// Size of entire variable store, 
  /// including size of variable store header but not including the size of FvHeader.
  ///
  UINT32  Size;
  ///
  /// Variable region format state.
  ///
  UINT8   Format;
  ///
  /// Variable region healthy state.
  ///
  UINT8   State;
  UINT16  Reserved;
  UINT32  Reserved1;
} VARIABLE_STORE_HEADER;

///
/// Variable data start flag.
///
#define VARIABLE_DATA                     0x55AA

///
/// Variable State flags.
///
#define VAR_IN_DELETED_TRANSITION     0xfe  ///< Variable is in obsolete transition.
#define VAR_DELETED                   0xfd  ///< Variable is obsolete.
#define VAR_HEADER_VALID_ONLY         0x7f  ///< Variable header has been valid.
#define VAR_ADDED                     0x3f  ///< Variable has been completely added.

///
/// Single Variable Data Header Structure.
///
typedef struct {
  ///
  /// Variable Data Start Flag.
  ///
  UINT16      StartId;
  ///
  /// Variable State defined above.
  ///
  UINT8       State;
  UINT8       Reserved;
  ///
  /// Attributes of variable defined in UEFI specification.
  ///
  UINT32      Attributes;
  ///
  /// Size of variable null-terminated Unicode string name.
  ///
  UINT32      NameSize;
  ///
  /// Size of the variable data without this header.
  ///
  UINT32      DataSize;
  ///
  /// A unique identifier for the vendor that produces and consumes this varaible.
  ///
  EFI_GUID    VendorGuid;
} VARIABLE_HEADER;

#pragma pack()

typedef struct _VARIABLE_INFO_ENTRY  VARIABLE_INFO_ENTRY;

///
/// This structure contains the variable list that is put in EFI system table.
/// The variable driver collects all variables that were used at boot service time and produces this list.
/// This is an optional feature to dump all used variables in shell environment. 
///
struct _VARIABLE_INFO_ENTRY {
  VARIABLE_INFO_ENTRY *Next;       ///< Pointer to next entry.
  EFI_GUID            VendorGuid;  ///< Guid of Variable.
  CHAR16              *Name;       ///< Name of Variable. 
  UINT32              Attributes;  ///< Attributes of variable defined in UEFI specification.
  UINT32              ReadCount;   ///< Number of times to read this variable.
  UINT32              WriteCount;  ///< Number of times to write this variable.
  UINT32              DeleteCount; ///< Number of times to delete this variable.
  UINT32              CacheCount;  ///< Number of times that cache hits this variable.
  BOOLEAN             Volatile;    ///< TRUE if volatile, FALSE if non-volatile.
};

#endif // _EFI_VARIABLE_H_
"""


#
# Variable Store Header Format and State.
#
VARIABLE_STORE_FORMATTED = 0x5a
VARIABLE_STORE_HEALTHY   = 0xfe

#
# Variable Store region header.
#
#typedef struct {
#  ///
#  /// Variable store region signature.
#  ///
#  EFI_GUID  Signature;
#  ///
#  /// Size of entire variable store, 
#  /// including size of variable store header but not including the size of FvHeader.
#  ///
#  UINT32  Size;
#  ///
#  /// Variable region format state.
#  ///
#  UINT8   Format;
#  ///
#  /// Variable region healthy state.
#  ///
#  UINT8   State;
#  UINT16  Reserved;
#  UINT32  Reserved1;
#} VARIABLE_STORE_HEADER;
#
# Signature is EFI_GUID (guid0 guid1 guid2 guid3)
VARIABLE_STORE_HEADER_FMT  = '<8sIBBHI'
VARIABLE_STORE_HEADER_SIZE = struct.calcsize( VARIABLE_STORE_HEADER_FMT )
class VARIABLE_STORE_HEADER( namedtuple('VARIABLE_STORE_HEADER', 'guid0 guid1 guid2 guid3 Size Format State Reserved Reserved1') ):
      __slots__ = ()
      def __str__(self):
          return """
EFI Variable Store
-----------------------------
Signature : {%08X-%04X-%04X-%04s-%06s}
Size      : 0x%08X bytes
Format    : 0x%02X
State     : 0x%02X
Reserved  : 0x%04X
Reserved1 : 0x%08X
""" % ( self.guid0, self.guid1, self.guid2, self.guid3[:2].encode('hex').upper(), self.guid3[-6::].encode('hex').upper(), self.Size, self.Format, self.State, self.Reserved, self.Reserved1 )         

#
# Variable data start flag.
#
VARIABLE_DATA_SIGNATURE    = struct.pack('=H', 0x55AA )

#
# Variable Attributes
#
EFI_VARIABLE_NON_VOLATILE                          = 0x00000001 # Variable is non volatile
EFI_VARIABLE_BOOTSERVICE_ACCESS                    = 0x00000002 # Variable is boot time accessible
EFI_VARIABLE_RUNTIME_ACCESS                        = 0x00000004 # Variable is run-time accessible
EFI_VARIABLE_HARDWARE_ERROR_RECORD                 = 0x00000008 #
EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS            = 0x00000010 # Variable is authenticated
EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS = 0x00000020 # Variable is time based authenticated
EFI_VARIABLE_APPEND_WRITE                          = 0x00000040 # Variable allows append
UEFI23_1_AUTHENTICATED_VARIABLE_ATTRIBUTES         = (EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS | EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS)
def IS_VARIABLE_ATTRIBUTE(_c, _Mask):
    return ( (_c & _Mask) != 0 )

def IS_EFI_VARIABLE_AUTHENTICATED( attr ):
    return ( IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS ) or IS_VARIABLE_ATTRIBUTE( attr, EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS ) )


#################################################################################################

FFS_ATTRIB_FIXED              = 0x04
FFS_ATTRIB_DATA_ALIGNMENT     = 0x38
FFS_ATTRIB_CHECKSUM           = 0x40

EFI_FILE_HEADER_CONSTRUCTION  = 0x01
EFI_FILE_HEADER_VALID         = 0x02
EFI_FILE_DATA_VALID           = 0x04
EFI_FILE_MARKED_FOR_UPDATE    = 0x08
EFI_FILE_DELETED              = 0x10
EFI_FILE_HEADER_INVALID       = 0x20

FFS_FIXED_CHECKSUM            = 0xAA

EFI_FVB2_ERASE_POLARITY       = 0x00000800

EFI_FV_FILETYPE_ALL                     = 0x00
EFI_FV_FILETYPE_RAW                     = 0x01
EFI_FV_FILETYPE_FREEFORM                = 0x02
EFI_FV_FILETYPE_SECURITY_CORE           = 0x03
EFI_FV_FILETYPE_PEI_CORE                = 0x04
EFI_FV_FILETYPE_DXE_CORE                = 0x05
EFI_FV_FILETYPE_PEIM                    = 0x06
EFI_FV_FILETYPE_DRIVER                  = 0x07
EFI_FV_FILETYPE_COMBINED_PEIM_DRIVER    = 0x08
EFI_FV_FILETYPE_APPLICATION             = 0x09
EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE   = 0x0b
EFI_FV_FILETYPE_FFS_PAD                 = 0xf0

FILE_TYPE_NAMES = {0x00: 'FV_ALL', 0x01: 'FV_RAW', 0x02: 'FV_FREEFORM', 0x03: 'FV_SECURITY_CORE', 0x04: 'FV_PEI_CORE', 0x05: 'FV_DXE_CORE', 0x06: 'FV_PEIM', 0x07: 'FV_DRIVER', 0x08: 'FV_COMBINED_PEIM_DRIVER', 0x09: 'FV_APPLICATION', 0x0B: 'FV_FVIMAGE', 0x0F: 'FV_FFS_PAD'}

EFI_SECTION_ALL                   = 0x00
EFI_SECTION_COMPRESSION           = 0x01
EFI_SECTION_GUID_DEFINED          = 0x02
EFI_SECTION_PE32                  = 0x10
EFI_SECTION_PIC                   = 0x11
EFI_SECTION_TE                    = 0x12
EFI_SECTION_DXE_DEPEX             = 0x13
EFI_SECTION_VERSION               = 0x14
EFI_SECTION_USER_INTERFACE        = 0x15
EFI_SECTION_COMPATIBILITY16       = 0x16
EFI_SECTION_FIRMWARE_VOLUME_IMAGE = 0x17
EFI_SECTION_FREEFORM_SUBTYPE_GUID = 0x18
EFI_SECTION_RAW                   = 0x19
EFI_SECTION_PEI_DEPEX             = 0x1B
EFI_SECTION_SMM_DEPEX             = 0x1C

SECTION_NAMES = {0x00: 'S_ALL', 0x01: 'S_COMPRESSION', 0x02: 'S_GUID_DEFINED', 0x10: 'S_PE32', 0x11: 'S_PIC', 0x12: 'S_TE', 0x13: 'S_DXE_DEPEX', 0x14: 'S_VERSION', 0x15: 'S_USER_INTERFACE', 0x16: 'S_COMPATIBILITY16', 0x17: 'S_FV_IMAGE', 0x18: 'S_FREEFORM_SUBTYPE_GUID', 0x19: 'S_RAW', 0x1B: 'S_PEI_DEPEX', 0x1C: 'S_SMM_DEPEX'}

#################################################################################################

GUID = "<IHH8s"
guid_size = struct.calcsize(GUID)

EFI_COMPRESSION_SECTION = "<IB"
EFI_COMPRESSION_SECTION_size = struct.calcsize(EFI_COMPRESSION_SECTION)

EFI_GUID_DEFINED_SECTION = "<IHH8sHH"
EFI_GUID_DEFINED_SECTION_size = struct.calcsize(EFI_GUID_DEFINED_SECTION)

EFI_CRC32_GUIDED_SECTION_EXTRACTION_PROTOCOL_GUID = "FC1BCDB0-7D31-49AA-936A-A4600D9DD083"

EFI_FIRMWARE_FILE_SYSTEM_GUID  = "7A9354D9-0468-444A-81CE-0BF617D890DF"
EFI_FIRMWARE_FILE_SYSTEM2_GUID = "8C8CE578-8A3D-4F1C-9935-896185C32DD3"

#################################################################################################

MAX_VARIABLE_SIZE = 1024
MAX_NVRAM_SIZE    = 1024*1024

#################################################################################################
# Helper functions
#################################################################################################

def align(of, size):
  of = (((of + size - 1)/size) * size)
  return of

def bit_set(value, mask, polarity = False):
  if polarity: value = ~value
  return ( (value & mask) == mask )

def get_3b_size(s):
  return (ord(s[0]) + (ord(s[1]) << 8) + (ord(s[2]) << 16))

def guid_str(guid0, guid1, guid2, guid3):
  guid = "%08X-%04X-%04X-%04s-%06s" % (guid0, guid1, guid2, guid3[:2].encode('hex').upper(), guid3[-6::].encode('hex').upper())
  return guid

def get_nvar_name(nvram, name_offset, isAscii):
   if isAscii:
      nend = nvram.find('\x00', name_offset) 
      name_size = nend - name_offset + 1 # add trailing zero symbol
      name = nvram[name_offset:nend]
      return (name, name_size)
   else:
      nend = nvram.find('\x00\x00', name_offset)
      while (nend & 1) == 1:
         nend = nend + 1
         nend = nvram.find('\x00\x00', nend)
      name_size = nend - name_offset + 2 # add trailing zero symbol
      name = unicode(nvram[name_offset:nend], "utf-16-le")
      return (name, name_size)

#################################################################################################
# Common NVRAM functions
#################################################################################################

VARIABLE_SIGNATURE_VSS = VARIABLE_DATA_SIGNATURE


#################################################################################################
# Common Firmware Volume functions
#################################################################################################

def FvSum8(buffer):
  sum8 = 0
  for b in buffer:
    sum8 = (sum8 + ord(b)) & 0xff
  return sum8

def FvChecksum8(buffer):
  return ((0x100 - FvSum8(buffer)) & 0xff)

def FvSum16(buffer):
  sum16 = 0
  blen = len(buffer)/2
  i = 0
  while i < blen:
    el16 = ord(buffer[2*i]) | (ord(buffer[2*i+1]) << 8)
    sum16 = (sum16 + el16) & 0xffff
    i = i + 1
  return sum16

def FvChecksum16(buffer):
  return ((0x10000 - FvSum16(buffer)) & 0xffff)

def NextFwVolume(buffer, off = 0):
  fof = off
  EFI_FIRMWARE_VOLUME_HEADER = "<16sIHH8sQIIHHHBB"
  vf_header_size = struct.calcsize(EFI_FIRMWARE_VOLUME_HEADER)
  EFI_FV_BLOCK_MAP_ENTRY = "<II"
  size = len(buffer)
  res = (None, None, None, None, None, None, None, None, None)
  if (fof + vf_header_size) < size:
    fof =  buffer.find("_FVH", fof)
    if fof < 0x28: return res
    fof = fof - 0x28
    ZeroVector, FileSystemGuid0, FileSystemGuid1,FileSystemGuid2,FileSystemGuid3, \
      FvLength, Signature, Attributes, HeaderLength, Checksum, ExtHeaderOffset,    \
       Reserved, Revision = struct.unpack(EFI_FIRMWARE_VOLUME_HEADER, buffer[fof:fof+vf_header_size])
    '''
    print "\nFV volume offset: 0x%08X" % fof
    print "\tFvLength:         0x%08X" % FvLength
    print "\tAttributes:       0x%08X" % Attributes
    print "\tHeaderLength:     0x%04X" % HeaderLength
    print "\tChecksum:         0x%04X" % Checksum
    print "\tRevision:         0x%02X" % Revision
    '''
    #print "FFS Guid:     %s" % guid_str(FileSystemGuid0, FileSystemGuid1,FileSystemGuid2, FileSystemGuid3)
    #print "FV Checksum:  0x%04X (0x%04X)" % (Checksum, FvChecksum16(buffer[fof:fof+HeaderLength]))
    #'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    fvh = struct.pack(EFI_FIRMWARE_VOLUME_HEADER, ZeroVector, \
                      FileSystemGuid0, FileSystemGuid1,FileSystemGuid2,FileSystemGuid3,     \
                      FvLength, Signature, Attributes, HeaderLength, 0, ExtHeaderOffset,    \
                      Reserved, Revision)
    if (len(fvh) < HeaderLength):
       #print "len(fvh)=%d, HeaderLength=%d" % (len(fvh), HeaderLength)
       tail = buffer[fof+len(fvh):fof+HeaderLength]
       fvh = fvh + tail
    CalcSum = FvChecksum16(fvh)
    FsGuid = guid_str(FileSystemGuid0, FileSystemGuid1,FileSystemGuid2,FileSystemGuid3)
    res = (fof, FsGuid, FvLength, Attributes, HeaderLength, Checksum, ExtHeaderOffset, buffer[fof:fof+FvLength], CalcSum)
    return res
  return res

def NextFwFile(FvImage, FvLength, fof, polarity):
    EFI_FFS_FILE_HEADER = "<IHH8sHBB3sB"
    file_header_size = struct.calcsize(EFI_FFS_FILE_HEADER)
    fof = align(fof, 8)
    cur_offset = fof
#    polarity = True
    next_offset = None
    res = None
    update_or_deleted = False
    if (fof + file_header_size) < FvLength:
      fheader = FvImage[fof:fof+file_header_size]
      Name0, Name1, Name2, Name3, IntegrityCheck, Type, Attributes, Size, State = struct.unpack(EFI_FFS_FILE_HEADER, fheader)
      fsize = get_3b_size(Size);
      update_or_deleted = (bit_set(State, EFI_FILE_MARKED_FOR_UPDATE, polarity)) or (bit_set(State, EFI_FILE_DELETED, polarity))
      if   (not bit_set(State, EFI_FILE_HEADER_VALID, polarity))   or (bit_set(State, EFI_FILE_HEADER_INVALID, polarity)):
        next_offset = align(fof + 1, 8)
      #elif  (bit_set(State, EFI_FILE_MARKED_FOR_UPDATE, polarity)) or (bit_set(State, EFI_FILE_DELETED, polarity)):
      #  if fsize == 0: fsize = 1
      #  next_offset = align(fof + fsize, 8)
        update_or_deleted = True
      elif (not bit_set(State, EFI_FILE_DATA_VALID, polarity)):
        next_offset = align(fof + 1, 8)
      elif fsize == 0:
        next_offset = align(fof + 1, 8)
      else:
        next_offset = fof + fsize
        next_offset = align(next_offset, 8)
        Name = guid_str(Name0, Name1, Name2, Name3)
        fheader = struct.pack(EFI_FFS_FILE_HEADER, Name0, Name1, Name2, Name3, 0, Type, Attributes, Size, 0)
        hsum = FvChecksum8(fheader)
        if (Attributes & FFS_ATTRIB_CHECKSUM):
           fsum = FvChecksum8(FvImage[fof+file_header_size:fof+fsize])
        else:
           fsum = FFS_FIXED_CHECKSUM
        CalcSum = (hsum | (fsum << 8))
        res = (cur_offset, next_offset, Name, Type, Attributes, State, IntegrityCheck, fsize, FvImage[fof:fof+fsize], file_header_size, update_or_deleted, CalcSum)
    if res == None: return (cur_offset, next_offset, None, None, None, None, None, None, None, None, update_or_deleted, None)
    else:           return res

EFI_COMMON_SECTION_HEADER = "<3sB"
EFI_COMMON_SECTION_HEADER_size = struct.calcsize(EFI_COMMON_SECTION_HEADER)

def NextFwFileSection(sections, ssize, sof, polarity):
  # offset, next_offset, SecName, SecType, SecBody, SecHeaderSize
  cur_offset = sof
  if (sof + EFI_COMMON_SECTION_HEADER_size) < ssize:
    header = sections[sof:sof+EFI_COMMON_SECTION_HEADER_size]
    if len(header) < EFI_COMMON_SECTION_HEADER_size: return (None, None, None, None, None, None)
    Size, Type = struct.unpack(EFI_COMMON_SECTION_HEADER, header)
    Size = get_3b_size(Size)
    sec_name = "S_UNKNOWN_%02X" % Type
    if Type in SECTION_NAMES.keys():
      sec_name = SECTION_NAMES[Type]
    if (Size == 0xffffff and Type == 0xff) or (Size == 0):
      sof = align(sof + 4, 4)
      return (cur_offset, sof, None, None, None, None)
    sec_body = sections[sof:sof+Size]
    sof = align(sof + Size, 4)
    return (cur_offset, sof, sec_name, Type, sec_body, EFI_COMMON_SECTION_HEADER_size)
  return (None, None, None, None, None, None)

def DecodeSection(SecType, SecBody, SecHeaderSize):
    pass

# this line breaks uefi shell
#from array import array

def DecompressSection(CompressedFileName, OutputFileName, CompressionType):
    from subprocess import call
    from chipsec.file import read_file
    decompressed = None
    edk2path = os.path.join('..','..','tools','edk2','win')
    exe = None
    try:
        if   (CompressionType == 1):
            exe = os.path.join(edk2path,'TianoCompress.exe')
        elif (CompressionType == 2):
            exe = os.path.join(edk2path,'LzmaCompress.exe')
        else:
            pass
        if exe:
            call('%s -d -o %s %s' % (exe, OutputFileName, CompressedFileName))
        decompressed = read_file( OutputFileName )
    except:
       pass
    return decompressed

'''
typedef struct {
  ///
  /// Type of the signature. GUID signature types are defined in below.
  ///
  EFI_GUID            SignatureType;
  ///
  /// Total size of the signature list, including this header.
  ///
  UINT32              SignatureListSize;
  ///
  /// Size of the signature header which precedes the array of signatures.
  ///
  UINT32              SignatureHeaderSize;
  ///
  /// Size of each signature.
  ///
  UINT32              SignatureSize; 
  ///
  /// Header before the array of signatures. The format of this header is specified 
  /// by the SignatureType.
  /// UINT8           SignatureHeader[SignatureHeaderSize];
  ///
  /// An array of signatures. Each signature is SignatureSize bytes in length. 
  /// EFI_SIGNATURE_DATA Signatures[][SignatureSize];
  ///
} EFI_SIGNATURE_LIST;
'''
SIGNATURE_LIST = "<IHH8sIII"
SIGNATURE_LIST_size = struct.calcsize(SIGNATURE_LIST)

def parse_sha256(data):
   return

def parse_rsa2048(data):
   return

def parse_rsa2048_sha256(data):
   return

def parse_sha1(data):
   return

def parse_rsa2048_sha1(data):
   return

def parse_x509(data):
   return

def parse_sha224(data):
   return

def parse_sha384(data):
   return

def parse_sha512(data):
   return

def parse_pkcs7(data):
   return

sig_types = {"C1C41626-504C-4092-ACA9-41F936934328": ("EFI_CERT_SHA256_GUID", parse_sha256, 0x30, "SHA256"), \
             "3C5766E8-269C-4E34-AA14-ED776E85B3B6": ("EFI_CERT_RSA2048_GUID", parse_rsa2048, 0x110, "RSA2048"), \
             "E2B36190-879B-4A3D-AD8D-F2E7BBA32784": ("EFI_CERT_RSA2048_SHA256_GUID", parse_rsa2048_sha256, 0x110, "RSA2048_SHA256"), \
             "826CA512-CF10-4AC9-B187-BE01496631BD": ("EFI_CERT_SHA1_GUID", parse_sha1, 0x24, "SHA1"), \
             "67F8444F-8743-48F1-A328-1EAAB8736080": ("EFI_CERT_RSA2048_SHA1_GUID", parse_rsa2048_sha1, 0x110, "RSA2048_SHA1"), \
             "A5C059A1-94E4-4AA7-87B5-AB155C2BF072": ("EFI_CERT_X509_GUID", parse_x509, 0, "X509"), \
             "0B6E5233-A65C-44C9-9407-D9AB83BFC8BD": ("EFI_CERT_SHA224_GUID", parse_sha224, 0x2c, "SHA224"), \
             "FF3E5307-9FD0-48C9-85F1-8AD56C701E01": ("EFI_CERT_SHA384_GUID", parse_sha384, 0x40, "SHA384"), \
             "093E0FAE-A6C4-4F50-9F1B-D41E2B89C19A": ("EFI_CERT_SHA512_GUID", parse_sha512, 0x50, "SHA512"), \
             "4AAFD29D-68DF-49EE-8AA9-347D375665A7": ("EFI_CERT_TYPE_PKCS7_GUID", parse_pkcs7, 0, "PKCS7") }


#def parse_db(db, var_name, path):
def parse_db( db, decode_dir ):
   db_size = len(db)
   if 0 == db_size:
       return
   dof = 0
   nsig = 0
   entries = []
   # some platforms have 0's in the beginnig, skip all 0 (no known SignatureType starts with 0x00):
   while (dof < db_size and db[dof] == '\x00'): dof = dof + 1
   while (dof + SIGNATURE_LIST_size) < db_size:
      SignatureType0, SignatureType1, SignatureType2, SignatureType3, SignatureListSize, SignatureHeaderSize, SignatureSize \
       = struct.unpack(SIGNATURE_LIST, db[dof:dof+SIGNATURE_LIST_size])
      SignatureType = guid_str(SignatureType0, SignatureType1, SignatureType2, SignatureType3)
      short_name = "UNKNOWN"
      sig_parse_f = None
      sig_size = 0
      if (SignatureType in sig_types.keys()):
         sig_name, sig_parse_f, sig_size, short_name = sig_types[SignatureType]
      #logger().log( "SignatureType       : %s (%s)" % (SignatureType, sig_name) )
      #logger().log( "SignatureListSize   : 0x%08X" % SignatureListSize )
      #logger().log( "SignatureHeaderSize : 0x%08X" % SignatureHeaderSize )
      #logger().log( "SignatureSize       : 0x%08X" % SignatureSize )
      #logger().log( "Parsing..." )
      if (((sig_size > 0) and (sig_size == SignatureSize)) or ((sig_size == 0) and (SignatureSize >= 0x10))):
         sof = 0
         sig_list = db[dof+SIGNATURE_LIST_size+SignatureHeaderSize:dof+SignatureListSize]
         sig_list_size = len(sig_list)
         while ((sof + guid_size) < sig_list_size):
            sig_data = sig_list[sof:sof+SignatureSize]
            owner0, owner1, owner2, owner3 = struct.unpack(GUID, sig_data[:guid_size])
            owner = guid_str(owner0, owner1, owner2, owner3)
            data = sig_data[guid_size:]
            #logger().log(  "owner: %s" % owner )
            entries.append( data )
            sig_file_name = "%s-%s-%02d.bin" % (short_name, owner, nsig)
            sig_file_name = os.path.join(decode_dir, sig_file_name)
            write_file(sig_file_name, data)
            if (sig_parse_f != None):
               sig_parse_f(data)
            sof = sof + SignatureSize
            nsig = nsig + 1
      else:
         err_str = "Wrong SignatureSize for %s type: 0x%X."  % (SignatureType, SignatureSize)
         if (sig_size > 0): err_str = err_str + " Must be 0x%X." % (sig_size) 
         else:              err_str = err_str + " Must be >= 0x10." 
         logger().error( err_str )
         entries.append( data )
         sig_file_name = "%s-%s-%02d.bin" % (short_name, SignatureType, nsig)
         sig_file_name = os.path.join(decode_dir, sig_file_name)
         write_file(sig_file_name, data)
         nsig = nsig + 1
      dof = dof + SignatureListSize

   return entries

def parse_efivar_file( fname, var=None ):
    if not var:
        var = read_file( fname )
    #path, var_name = os.path.split( fname )
    #var_name, ext = os.path.splitext( var_name )
    var_path = fname + '.dir'
    if not os.path.exists( var_path ):
        os.makedirs( var_path )

    parse_db( var, var_path )


#################################################################################################




########NEW FILE########
__FILENAME__ = uefi_platform
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup hal
# chipsec/hal/uefi_platform.py
# ==================================
# Platform specific UEFI functionality (parsing platform specific EFI NVRAM, capsules, etc.)
#
#
__version__ = '1.0'

import struct
from collections import namedtuple

from chipsec.hal.uefi_common import *


#################################################################################################3
# List of supported types of EFI NVRAM format (platform/vendor specific)
#################################################################################################3

class FWType:
    EFI_FW_TYPE_UEFI     = 'uefi'
#    EFI_FW_TYPE_WIN      = 'win'     # Windows 8 GetFirmwareEnvironmentVariable format
    EFI_FW_TYPE_VSS      = 'vss'     # NVRAM using format with '$VSS' signature
    EFI_FW_TYPE_VSS_NEW  = 'vss_new' # NVRAM using format with '$VSS' signature (Newer one?)
    EFI_FW_TYPE_NVAR     = 'nvar'    # 'NVAR' NVRAM format
    EFI_FW_TYPE_EVSA     = 'evsa'    # 'EVSA' NVRAM format


fw_types = []
for i in [t for t in dir(FWType) if not callable(getattr(FWType, t))]:
    if not i.startswith('__'):
        fw_types.append( getattr(FWType, i) )


NVRAM_ATTR_RT         = 1
NVRAM_ATTR_DESC_ASCII = 2
NVRAM_ATTR_GUID       = 4
NVRAM_ATTR_DATA       = 8
NVRAM_ATTR_EXTHDR     = 0x10
NVRAM_ATTR_AUTHWR     = 0x40
NVRAM_ATTR_HER        = 0x20
NVRAM_ATTR_VLD        = 0x80


#################################################################################################3
# This Variable header is defined by UEFI
#################################################################################################3

#
# Variable Store Status
#
#typedef enum {
#  EfiRaw,
#  EfiValid,
#  EfiInvalid,
#  EfiUnknown
# } VARIABLE_STORE_STATUS;
VARIABLE_STORE_STATUS_RAW     = 0
VARIABLE_STORE_STATUS_VALID   = 1
VARIABLE_STORE_STATUS_INVALID = 2
VARIABLE_STORE_STATUS_UNKNOWN = 3

#
# Variable State flags
#
VAR_IN_DELETED_TRANSITION     = 0xfe  # Variable is in obsolete transistion
VAR_DELETED                   = 0xfd  # Variable is obsolete
VAR_ADDED                     = 0x7f  # Variable has been completely added
#IS_VARIABLE_STATE(_c, _Mask)  (BOOLEAN) (((~_c) & (~_Mask)) != 0)
def IS_VARIABLE_STATE(_c, _Mask):
    return ( ( ((~_c)&0xFF) & ((~_Mask)&0xFF) ) != 0 )




#
#typedef struct {
#  UINT16    StartId;
#  UINT8     State;
#  UINT8     Reserved;
#  UINT32    Attributes;
#  UINT32    NameSize;
#  UINT32    DataSize;
#  EFI_GUID  VendorGuid;
#} VARIABLE_HEADER;
#
#typedef struct {
#  UINT32  Data1;
#  UINT16  Data2;
#  UINT16  Data3;
#  UINT8   Data4[8];
#} EFI_GUID;
#
UEFI_VARIABLE_HEADER_SIZE = 28
class UEFI_VARIABLE_HEADER( namedtuple('UEFI_VARIABLE_HEADER', 'StartId State Reserved Attributes NameSize DataSize VendorGuid0 VendorGuid1 VendorGuid2 VendorGuid3') ):
      __slots__ = ()
      def __str__(self):
          return """
Header (UEFI)
-------------
StartId    : 0x%04X 
State      : 0x%02X
Reserved   : 0x%02X
Attributes : 0x%08X
NameSize   : 0x%08X
DataSize   : 0x%08X
VendorGuid : {0x%08X-0x%04X-0x%04X-0x%08X}
""" % ( self.StartId, self.State, self.Reserved, self.Attributes, self.NameSize, self.DataSize, self.VendorGuid0, self.VendorGuid1, self.VendorGuid2, self.VendorGuid3 )         

def getEFIvariables_UEFI( nvram_buf ):
    logger().error( 'Well, implement getEFIvariables_UEFI finally, would you??' )
    return 0

##################################################################################################
#
# Platform/Vendor Specific EFI NVRAM Parsing Functions
#
# For each platform, EFI NVRAM parsing functionality includes:
# 1. Function to parse EFI variable within NVRAM binary (func_getefivariables)
#    May define/use platform specific EFI Variable Header
#    Function arguments:
#      In : binary buffer (as a string)
#      Out:
#        start           - offset in the buffer to the current EFI variable
#        next_var_offset - offset in the buffer to the next EFI variable
#        efi_var_buf     - full EFI variable buffer
#        efi_var_hdr     - EFI variable header object
#        efi_var_name    - EFI variable name
#        efi_var_data    - EFI variable data contents
#        efi_var_guid    - EFI variable GUID
#        efi_var_attr    - EFI variable attributes
# 2. [Optional] Function to find EFI NVRAM within arbitrary binary (func_getnvstore)
#    If this function is not defined, 'chipsec_util uefi' searches EFI variables from the beginning of the binary
#    Function arguments:
#      In : NVRAM binary buffer (as a string)
#      Out:
#        start        - offset of NVRAM     (-1 means NVRAM not found)
#        size         - size of NVRAM       (-1 means NVRAM is entire binary)
#        nvram_header - NVRAM header object
#
##################################################################################################

##################################################################################################
# NVAR format of NVRAM
#

from chipsec.logger import *
class EFI_HDR_NVAR1( namedtuple('EFI_HDR_NVAR1', 'StartId TotalSize Reserved1 Reserved2 Reserved3 Attributes State') ):
      __slots__ = ()
      def __str__(self):
          return """
Header (NVAR)
------------
StartId    : 0x%04X 
TotalSize  : 0x%04X
Reserved1  : 0x%02X
Reserved2  : 0x%02X
Reserved3  : 0x%02X
Attributes : 0x%02X
State      : 0x%02X
""" % ( self.StartId, self.TotalSize, self.Reserved1, self.Reserved2, self.Reserved3, self.Attributes, self.State )         

NVAR_EFIvar_signature   = 'NVAR'
NVAR_NVRAM_FS_FILE      = "CEF5B9A3-476D-497F-9FDC-E98143E0422C"

def getNVstore_NVAR( nvram_buf ):
   l = (-1, -1, None)
   FvOffset, FsGuid, FvLength, FvAttributes, FvHeaderLength, FvChecksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(nvram_buf)
   while FvOffset != None:
      polarity = bit_set(FvAttributes, EFI_FVB2_ERASE_POLARITY)
      cur_offset, next_offset, Name, Type, Attributes, State, Checksum, Size, FileImage, HeaderSize, UD, fCalcSum = NextFwFile(FvImage, FvLength, FvHeaderLength, polarity)
      while next_offset != None:
         if (Type == EFI_FV_FILETYPE_RAW) and (Name == NVAR_NVRAM_FS_FILE):
            l = ((FvOffset + cur_offset + HeaderSize), Size - HeaderSize, None)
            if (not UD): break
         cur_offset, next_offset, Name, Type, Attributes, State, Checksum, Size, FileImage, HeaderSize, UD, fCalcSum = NextFwFile(FvImage, FvLength, next_offset, polarity)
      FvOffset, FsGuid, FvLength, Attributes, HeaderLength, Checksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(nvram_buf, FvOffset+FvLength)
   return l

def getEFIvariables_NVAR( nvram_buf ):
   start = nvram_buf.find( NVAR_EFIvar_signature )
   nvram_size = len(nvram_buf)
   EFI_HDR_NVAR = "<4sH3sB"
   nvar_size = struct.calcsize(EFI_HDR_NVAR)
   variables = dict()
   nof = 0 #start
#   EMPTY = 0
   EMPTY = 0xffffffff
   while (nof+nvar_size) < nvram_size:
      start_id, size, next, attributes = struct.unpack(EFI_HDR_NVAR, nvram_buf[nof:nof+nvar_size])
      next = get_3b_size(next)
      valid = (bit_set(attributes, NVRAM_ATTR_VLD) and (not bit_set(attributes, NVRAM_ATTR_DATA)))
      if not valid:
         nof = nof + size
         continue
      isvar = (start_id == NVAR_EFIvar_signature)
      if (not isvar) or (size == (EMPTY & 0xffff)): break
      var_name_off = 1
      if bit_set(attributes, NVRAM_ATTR_GUID):
         guid0, guid1, guid2, guid3 = struct.unpack(GUID, nvram_buf[nof+nvar_size:nof+nvar_size+guid_size])
         guid = guid_str(guid0, guid1, guid2, guid3)
         var_name_off = guid_size
      else:
         guid_idx = ord(nvram_buf[nof+nvar_size])
         guid0, guid1, guid2, guid3 = struct.unpack(GUID, nvram_buf[nvram_size - guid_size - guid_idx:nvram_size - guid_idx])
         guid = guid_str(guid0, guid1, guid2, guid3)
      name_size = 0
      name_offset = nof+nvar_size+var_name_off
      if not bit_set(attributes, NVRAM_ATTR_DATA):
         name, name_size = get_nvar_name(nvram_buf, name_offset, bit_set(attributes, NVRAM_ATTR_DESC_ASCII))
      esize = 0
      eattrs = 0
      if bit_set(attributes, NVRAM_ATTR_EXTHDR):
         esize, = struct.unpack("<H", nvram_buf[nof+size-2:nof+size])
         eattrs = ord(nvram_buf[nof+size-esize])
      attribs = EFI_VARIABLE_BOOTSERVICE_ACCESS
      attribs = attribs | EFI_VARIABLE_NON_VOLATILE
      if bit_set(attributes, NVRAM_ATTR_RT):  attribs = attribs | EFI_VARIABLE_RUNTIME_ACCESS
      if bit_set(attributes, NVRAM_ATTR_HER): attribs = attribs | EFI_VARIABLE_HARDWARE_ERROR_RECORD
      if bit_set(attributes, NVRAM_ATTR_AUTHWR):
         if bit_set(eattrs, EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS): 
            attribs = attribs | EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS
         if bit_set(eattrs, EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS): 
            attribs = attribs | EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS
      # Get variable data
      lof = nof
      lnext = next
      lattributes = attributes
      lsize = size
      lesize = esize
      while lnext != (0xFFFFFF & EMPTY):
         lof = lof + lnext
         lstart_id, lsize, lnext, lattributes = struct.unpack(EFI_HDR_NVAR, nvram_buf[lof:lof+nvar_size])
         lnext = get_3b_size(lnext)
      dataof = lof + nvar_size
      if not bit_set(lattributes, NVRAM_ATTR_DATA):
         lnameof = 1
         if bit_set(lattributes, NVRAM_ATTR_GUID): lnameof = guid_size
         name_offset = lof+nvar_size+lnameof
         name, name_size = get_nvar_name(nvram_buf, name_offset, bit_set(attributes, NVRAM_ATTR_DESC_ASCII))
         dataof = name_offset + name_size
      if bit_set(lattributes, NVRAM_ATTR_EXTHDR):
         lesize, = struct.unpack("<H", nvram_buf[lof+lsize-2:lof+lsize])
      data = nvram_buf[dataof:lof+lsize-lesize]
      if name not in variables.keys():
         variables[name] = []
      #                       off, buf,  hdr,  data, guid, attrs
      variables[name].append((nof, None, None, data, guid, attribs))
      nof = nof + size
   return variables

NVAR_HDR_FMT          = '=IHBBBBB'
NVAR_HDR_SIZE         = struct.calcsize( NVAR_HDR_FMT )


#
# Linear/simple NVAR format parsing
#
def getNVstore_NVAR_simple( nvram_buf ):
    return (nvram_buf.find( NVAR_EFIvar_signature ), -1, None)

def getEFIvariables_NVAR_simple( nvram_buf ):
    nvsize = len(nvram_buf)
    hdr_fmt = NVAR_HDR_FMT
    hdr_size = struct.calcsize( hdr_fmt )
    variables = dict()
    start = nvram_buf.find( NVAR_EFIvar_signature )
    if -1 == start: return variables

    while (start + hdr_size) < nvsize:
        efi_var_hdr = EFI_HDR_NVAR1( *struct.unpack_from( hdr_fmt, nvram_buf[start:] ) )
        name_size = 0
        efi_var_name = "NA"
        if not IS_VARIABLE_ATTRIBUTE( efi_var_hdr.Attributes, EFI_VARIABLE_HARDWARE_ERROR_RECORD ):
           name_size = nvram_buf[ start + hdr_size : ].find( '\0' )
           efi_var_name = "".join( nvram_buf[ start + hdr_size : start + hdr_size + name_size ] )
    
        next_var_offset = start + efi_var_hdr.TotalSize 
        data_size = efi_var_hdr.TotalSize - name_size - hdr_size
        efi_var_buf  = nvram_buf[ start : next_var_offset ]
        efi_var_data = nvram_buf[ start + hdr_size + name_size : next_var_offset ]

        if efi_var_name not in variables.keys(): variables[efi_var_name] = []
        #                               off,   buf,         hdr,         data,         guid, attrs
        variables[efi_var_name].append((start, efi_var_buf, efi_var_hdr, efi_var_data, '',   efi_var_hdr.Attributes))

        if start >= next_var_offset: break
        start = next_var_offset

    return variables


#######################################################################
#
# VSS NVRAM (signature = '$VSS')
#
#

#define VARIABLE_STORE_SIGNATURE  EFI_SIGNATURE_32 ('$', 'V', 'S', 'S')
VARIABLE_STORE_SIGNATURE_VSS  = '$VSS'
VARIABLE_STORE_HEADER_FMT_VSS = '=IIBBHI' # Signature is '$VSS'
class VARIABLE_STORE_HEADER_VSS( namedtuple('VARIABLE_STORE_HEADER_VSS', 'Signature Size Format State Reserved Reserved1') ):
      __slots__ = ()
      def __str__(self):
          return """
EFI Variable Store
-----------------------------
Signature : %s (0x%08X)
Size      : 0x%08X bytes
Format    : 0x%02X
State     : 0x%02X
Reserved  : 0x%04X
Reserved1 : 0x%08X
""" % ( struct.pack('=I',self.Signature), self.Signature, self.Size, self.Format, self.State, self.Reserved, self.Reserved1 )         


HDR_FMT_VSS                   = '<HBBIIIIHH8s'
#HDR_SIZE_VSS                  = struct.calcsize( HDR_FMT_VSS )
#NAME_OFFSET_IN_VAR_VSS        = HDR_SIZE_VSS
class EFI_HDR_VSS( namedtuple('EFI_HDR_VSS', 'StartId State Reserved Attributes NameSize DataSize guid0 guid1 guid2 guid3') ):
      __slots__ = ()
      def __str__(self):
          return """
Header (VSS)
------------
VendorGuid : {%08X-%04X-%04X-%04s-%06s}
StartId    : 0x%04X 
State      : 0x%02X
Reserved   : 0x%02X
Attributes : 0x%08X
NameSize   : 0x%08X
DataSize   : 0x%08X
""" % ( self.guid0, self.guid1, self.guid2, self.guid3[:2].encode('hex').upper(), self.guid3[-6::].encode('hex').upper(), self.StartId, self.DataOffset, self.DataSize, self.Attributes )


HDR_FMT_VSS_NEW  = '<HBBIQQQIIIIHH8s'
class EFI_HDR_VSS_NEW( namedtuple('EFI_HDR_VSS_NEW', 'StartId State Reserved Attributes wtf1 wtf2 wtf3 wtf4 NameSize DataSize guid0 guid1 guid2 guid3') ):
      __slots__ = ()
      # if you don't re-define __str__ method, initialize is to None
      #__str__ = None 
      def __str__(self):
          return """
Header (VSS_NEW)
----------------
VendorGuid : {%08X-%04X-%04X-%08X}
StartId    : 0x%04X 
State      : 0x%02X
Reserved   : 0x%02X
Attributes : 0x%08X
wtf1       : 0x%016X
wtf2       : 0x%016X
wtf3       : 0x%016X
wtf4       : 0x%08X
NameSize   : 0x%08X
DataSize   : 0x%08X
""" % ( self.guid0, self.guid1, self.guid2, self.guid3[:2].encode('hex').upper(), self.guid3[-6::].encode('hex').upper(), self.StartId, self.State, self.Reserved, self.Attributes, self.wtf1, self.wtf2, self.wtf3, self.wtf4, self.NameSize, self.DataSize )         



def getNVstore_VSS( nvram_buf ):
    nvram_start = nvram_buf.find( VARIABLE_STORE_SIGNATURE_VSS )
    if -1 == nvram_start:
        return (-1, 0, None)
    nvram_hdr = VARIABLE_STORE_HEADER_VSS( *struct.unpack_from( VARIABLE_STORE_HEADER_FMT_VSS, nvram_buf[nvram_start:] ) )
    return (nvram_start, nvram_hdr.Size, nvram_hdr)

def _getEFIvariables_VSS( nvram_buf, _fwtype ):
    nvsize = len(nvram_buf)
    if (FWType.EFI_FW_TYPE_VSS == _fwtype):
        hdr_fmt  = HDR_FMT_VSS
    elif (FWType.EFI_FW_TYPE_VSS_NEW == _fwtype):
        hdr_fmt  = HDR_FMT_VSS_NEW
    hdr_size = struct.calcsize( hdr_fmt )
    variables = dict()
    start    = nvram_buf.find( VARIABLE_SIGNATURE_VSS )
    if -1 == start:
       return variables

    while (start + hdr_size) < nvsize:
       if (FWType.EFI_FW_TYPE_VSS == _fwtype):
           efi_var_hdr = EFI_HDR_VSS( *struct.unpack_from( hdr_fmt, nvram_buf[start:] ) )
       elif (FWType.EFI_FW_TYPE_VSS_NEW == _fwtype):
           efi_var_hdr = EFI_HDR_VSS_NEW( *struct.unpack_from( hdr_fmt, nvram_buf[start:] ) )

       if (efi_var_hdr.StartId != 0x55AA): break

       name_size = efi_var_hdr.NameSize
       data_size = efi_var_hdr.DataSize
       efi_var_name = "<not defined>"

       next_var_offset = start + hdr_size + name_size + data_size 
       efi_var_buf  = nvram_buf[ start : next_var_offset ]

       name_offset = hdr_size
       #if not IS_VARIABLE_ATTRIBUTE( efi_var_hdr.Attributes, EFI_VARIABLE_HARDWARE_ERROR_RECORD ):
       #efi_var_name = "".join( efi_var_buf[ NAME_OFFSET_IN_VAR_VSS : NAME_OFFSET_IN_VAR_VSS + name_size ] )  
       str_fmt = "%ds" % name_size
       s, = struct.unpack( str_fmt, efi_var_buf[ name_offset : name_offset + name_size ] )
       efi_var_name = unicode(s, "utf-16-le", errors="replace").split(u'\u0000')[0]

       efi_var_data = efi_var_buf[ name_offset + name_size : next_var_offset ]
       guid = guid_str(efi_var_hdr.guid0, efi_var_hdr.guid1, efi_var_hdr.guid2, efi_var_hdr.guid3)
       if efi_var_name not in variables.keys():
           variables[efi_var_name] = []
       #                                off,   buf,         hdr,         data,         guid, attrs
       variables[efi_var_name].append( (start, efi_var_buf, efi_var_hdr, efi_var_data, guid, efi_var_hdr.Attributes) )

       if start >= next_var_offset: break
       start = next_var_offset

    return variables


def getEFIvariables_VSS( nvram_buf ):
    return _getEFIvariables_VSS( nvram_buf, FWType.EFI_FW_TYPE_VSS )

def getEFIvariables_VSS_NEW( nvram_buf ):
    return _getEFIvariables_VSS( nvram_buf, FWType.EFI_FW_TYPE_VSS_NEW )

#######################################################################
#
# EVSA NVRAM (signature = 'EVSA')
#
#
VARIABLE_STORE_SIGNATURE_EVSA = 'EVSA'
VARIABLE_STORE_FV_GUID = 'FFF12B8D-7696-4C8B-A985-2747075B4F50'
ADDITIONAL_NV_STORE_GUID = '00504624-8A59-4EEB-BD0F-6B36E96128E0'

TLV_HEADER = "<BBH"
tlv_h_size = struct.calcsize(TLV_HEADER)

def getNVstore_EVSA( nvram_buf ):
   l = (-1, -1, None)
   FvOffset, FsGuid, FvLength, FvAttributes, FvHeaderLength, FvChecksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(nvram_buf) 
   while FvOffset != None:
      if (FsGuid == VARIABLE_STORE_FV_GUID):
         nvram_start = FvImage.find( VARIABLE_STORE_SIGNATURE_EVSA )
         if (nvram_start != -1) and (nvram_start >= tlv_h_size):
             nvram_start = nvram_start - tlv_h_size
             l = (FvOffset + nvram_start, FvLength - nvram_start, None)
             break
      if (FsGuid == ADDITIONAL_NV_STORE_GUID):
         nvram_start = FvImage.find( VARIABLE_STORE_SIGNATURE_EVSA )
         if (nvram_start != -1) and (nvram_start >= tlv_h_size):
             nvram_start = nvram_start - tlv_h_size
             l = (FvOffset + nvram_start, FvLength - nvram_start, None)
      FvOffset, FsGuid, FvLength, Attributes, HeaderLength, Checksum, ExtHeaderOffset, FvImage, CalcSum = NextFwVolume(nvram_buf, FvOffset+FvLength)
   return l

def EFIvar_EVSA(nvram_buf):
   image_size = len(nvram_buf)
   sn = 0
   EVSA_RECORD = "<IIII"
   evsa_rec_size = struct.calcsize(EVSA_RECORD)
   GUID_RECORD = "<HIHH8s"
   guid_rc_size = struct.calcsize(GUID_RECORD)
   fof = 0
   variables = dict()
   while fof < image_size:
      fof = nvram_buf.find("EVSA", fof)
      if fof == -1: break
      if fof < tlv_h_size:
         fof = fof + 1
         continue
      start = fof - tlv_h_size
      Tag0, Tag1, Size = struct.unpack(TLV_HEADER, nvram_buf[start: start + tlv_h_size])
      if Tag0 != 0xEC: # Wrong EVSA block
         fof = fof + 1
         continue
      value = nvram_buf[start + tlv_h_size:start + Size]
      Signature, Unkwn0, Length, Unkwn1 = struct.unpack(EVSA_RECORD, value)
      if start + Length > image_size: # Wrong EVSA record
         fof = fof + 1
         continue
      # NV storage EVSA found
      bof = 0
      guid_map = dict()
      var_list = list()
      value_list = dict()
      while (bof + tlv_h_size) < Length:
         Tag0, Tag1, Size = struct.unpack(TLV_HEADER, nvram_buf[start + bof: start + bof + tlv_h_size])
         value = nvram_buf[start + bof + tlv_h_size:start + bof + Size]
         bof = bof + Size
         if   (Tag0 == 0xED) or (Tag0 == 0xE1):  # guid
            GuidId, guid0, guid1, guid2, guid3 = struct.unpack(GUID_RECORD, value)
            g = guid_str(guid0, guid1, guid2, guid3)
            guid_map[GuidId] = g
         elif (Tag0 == 0xEE) or (Tag0 == 0xE2):  # var name
            VAR_NAME_RECORD = "<H%ds" % (Size - tlv_h_size - 2)
            VarId, Name = struct.unpack(VAR_NAME_RECORD, value)
            Name = unicode(Name, "utf-16-le")[:-1]
            var_list.append((Name, VarId, Tag0, Tag1))
         elif (Tag0 == 0xEF) or (Tag0 == 0xE3) or (Tag0 == 0x83):  # values
            VAR_VALUE_RECORD = "<HHI%ds" % (Size - tlv_h_size - 8)
            GuidId, VarId, Attributes, Data = struct.unpack(VAR_VALUE_RECORD, value)
            value_list[VarId] = (GuidId, Attributes, Data, Tag0, Tag1)
         elif not ((Tag0 == 0xff) and (Tag1 == 0xff) and (Size == 0xffff)):
            pass
      var_count = len(var_list)
      var_list.sort()
      var1 = {}
      for i in var_list:
         name = i[0]
         VarId = i[1]
         #NameTag0 = i[2]
         #NameTag1 = i[3]
         if VarId in value_list:
            var_value = value_list[VarId]
         else:
            #  Value not found for VarId
            continue
         GuidId = var_value[0]
         guid = "NONE"
         if GuidId not in guid_map:
            # Guid not found for GuidId
            pass
         else:
            guid = guid_map[GuidId]
         if name not in variables.keys():
            variables[name] = []
         #                       off,   buf,  hdr,  data,         guid, attrs
         variables[name].append((start, None, None, var_value[2], guid, var_value[1]))
      fof = fof + Length
   return variables



#
# Uncomment if you want to parse output buffer returned by NtEnumerateSystemEnvironmentValuesEx
# using 'chipsec_util uefi nvram' command
#
#
# Windows 8 NtEnumerateSystemEnvironmentValuesEx (infcls = 2)
#
#def guid_str(guid0, guid1, guid2, guid3):
#        return ( "%08X-%04X-%04X-%04s-%06s" % (guid0, guid1, guid2, guid3[:2].encode('hex').upper(), guid3[-6::].encode('hex').upper()) )
#
#class EFI_HDR_WIN( namedtuple('EFI_HDR_WIN', 'Size DataOffset DataSize Attributes guid0 guid1 guid2 guid3') ):
#        __slots__ = ()
#        def __str__(self):
#            return """
#Header (Windows)
#----------------
#VendorGuid= {%08X-%04X-%04X-%04s-%06s}
#Size      = 0x%08X
#DataOffset= 0x%08X
#DataSize  = 0x%08X
#Attributes= 0x%08X
#""" % ( self.guid0, self.guid1, self.guid2, self.guid3[:2].encode('hex').upper(), self.guid3[-6::].encode('hex').upper(), self.Size, self.DataOffset, self.DataSize, self.Attributes )
"""
def getEFIvariables_NtEnumerateSystemEnvironmentValuesEx2( nvram_buf ):
        start = 0
        buffer = nvram_buf
        bsize = len(buffer)
        header_fmt = "<IIIIIHH8s"
        header_size = struct.calcsize( header_fmt )
        variables = dict()
        off = 0
        while (off + header_size) < bsize:
           efi_var_hdr = EFI_HDR_WIN( *struct.unpack_from( header_fmt, buffer[ off : off + header_size ] ) )

           next_var_offset = off + efi_var_hdr.Size
           efi_var_buf     = buffer[ off : next_var_offset ]
           efi_var_data    = buffer[ off + efi_var_hdr.DataOffset : off + efi_var_hdr.DataOffset + efi_var_hdr.DataSize ]

           #efi_var_name = "".join( buffer[ start + header_size : start + efi_var_hdr.DataOffset ] ).decode('utf-16-le')
           str_fmt = "%ds" % (efi_var_hdr.DataOffset - header_size)
           s, = struct.unpack( str_fmt, buffer[ off + header_size : off + efi_var_hdr.DataOffset ] )
           efi_var_name = unicode(s, "utf-16-le", errors="replace").split(u'\u0000')[0]

           if efi_var_name not in variables.keys():
               variables[efi_var_name] = []
           #                                off, buf,         hdr,         data,         guid,                                                                                 attrs
           variables[efi_var_name].append( (off, efi_var_buf, efi_var_hdr, efi_var_data, guid_str(efi_var_hdr.guid0, efi_var_hdr.guid1, efi_var_hdr.guid2, efi_var_hdr.guid3), efi_var_hdr.Attributes) )

           if 0 == efi_var_hdr.Size: break
           off = next_var_offset
 
        return variables
#    return ( start, next_var_offset, efi_var_buf, efi_var_hdr, efi_var_name, efi_var_data, guid_str(efi_var_hdr.guid0, efi_var_hdr.guid1, efi_var_hdr.guid2, efi_var_hdr.guid3), efi_var_hdr.Attributes )
"""




#################################################################################################3
# EFI Variable Header Dictionary
#################################################################################################3

#
# Add your EFI variable details to the dictionary
#
# Fields:
# name		func_getefivariables		func_getnvstore
#
EFI_VAR_DICT = {
# UEFI
FWType.EFI_FW_TYPE_UEFI    : {'name' : 'UEFI',    'func_getefivariables' : getEFIvariables_UEFI },
# Windows 8 NtEnumerateSystemEnvironmentValuesEx (infcls = 2)
#FWType.EFI_FW_TYPE_WIN     : {'name' : 'WIN',     'func_getefivariables' : getEFIvariables_NtEnumerateSystemEnvironmentValuesEx2, 'func_getnvstore' : None },
# NVAR format
FWType.EFI_FW_TYPE_NVAR    : {'name' : 'NVAR',    'func_getefivariables' : getEFIvariables_NVAR,    'func_getnvstore' : getNVstore_NVAR },
# $VSS NVRAM format
FWType.EFI_FW_TYPE_VSS     : {'name' : 'VSS',     'func_getefivariables' : getEFIvariables_VSS,     'func_getnvstore' : getNVstore_VSS },
# $VSS New NVRAM format
FWType.EFI_FW_TYPE_VSS_NEW : {'name' : 'VSS_NEW', 'func_getefivariables' : getEFIvariables_VSS_NEW, 'func_getnvstore' : getNVstore_VSS },
# EVSA
FWType.EFI_FW_TYPE_EVSA    : {'name' : 'EVSA',    'func_getefivariables' : EFIvar_EVSA,             'func_getnvstore' : getNVstore_EVSA },
}



########NEW FILE########
__FILENAME__ = efihelper
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup helpers
# __chipsec/helper/efi/efihelper.py__ -- On UEFI use the efi package functions
#
#
__version__ = '1.0'

import struct
import sys
try:
  import edk2        # for Python 2.7 on UEFI
except ImportError:
  import efi as edk2 # for Python 2.4 on EFI 1.10

from chipsec.logger import logger

class EfiHelperError (RuntimeError):
    pass

class EfiHelper:

 def __init__(self):
    if sys.platform.startswith('EFI'):
        self.os_system = sys.platform
        self.os_release = "0.0"
        self.os_version = "0.0"
        self.os_machine = "i386"
    else:
        import platform
        self.os_system  = platform.system()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.os_machine = platform.machine()
        self.os_uname   = platform.uname()
 
 def __del__(self):
  try:
   destroy()
  except NameError:
   pass

###############################################################################################
# Driver/service management functions
###############################################################################################

 def create( self ):
     if logger().VERBOSE:
        logger().log("[helper] UEFI Helper created")

 def start( self ):
     if logger().VERBOSE:
        logger().log("[helper] UEFI Helper started/loaded")

 def stop( self ):
     if logger().VERBOSE:
        logger().log("[helper] UEFI Helper stopped/unloaded")

 def delete( self ):
     if logger().VERBOSE:
        logger().log("[helper] UEFI Helper deleted")

 def destroy( self ):
     self.stop()
     self.delete()

###############################################################################################
# Actual API functions to access HW resources
###############################################################################################

 def read_phys_mem( self, phys_address_hi, phys_address_lo, length ):
  if logger().VERBOSE:
    logger().log( '[efi] helper does not support 64b PA' )
  return self._read_phys_mem( phys_address_lo, length )

# def _read_phys_mem( self, phys_address, length ):
#  out_buf = (c_char * length)()
#  s_buf = edk2.readmem( phys_address, length )
#  # warning: this is hackish...
#  for j in range(len(s_buf)):
#   out_buf[j] = list(s_buf)[j]
#  return out_buf
 def _read_phys_mem( self, phys_address, length ):
  return edk2.readmem( phys_address, length )

 def write_phys_mem( self, phys_address_hi, phys_address_lo, length, buf ):
  if logger().VERBOSE:
    logger().log( '[efi] helper does not support 64b PA' )
  return self._write_phys_mem( phys_address_lo, length, buf )

 def _write_phys_mem( self, phys_address, length, buf ):
  # temp hack
  if 4 == length:
   dword_value = struct.unpack( 'I', buf )[0]
   edk2.writemem_dword( phys_address, dword_value )
  else:
   edk2.writemem( phys_address, buf, length )

 def read_msr( self, cpu_thread_id, msr_addr ):
  (eax, edx) = edk2.rdmsr( msr_addr )
  eax = eax % 2**32
  edx = edx % 2**32
  return ( eax, edx )

 def write_msr( self, cpu_thread_id, msr_addr, eax, edx ):
  edk2.wrmsr( msr_addr, eax, edx )

 def read_pci_reg( self, bus, device, function, address, size ):
     if   (1 == size):
       return ( edk2.readpci( bus, device, function, address, size ) & 0xFF )
     elif (2 == size):
       return ( edk2.readpci( bus, device, function, address, size ) & 0xFFFF )
     else:
       return edk2.readpci( bus, device, function, address, size )

 def write_pci_reg( self, bus, device, function, address, value, size ):
     return edk2.writepci( bus, device, function, address, value, size )

 def read_io_port( self, io_port, size ):
     if   (1 == size):
       return ( edk2.readio( io_port, size ) & 0xFF )
     elif (2 == size):
       return ( edk2.readio( io_port, size ) & 0xFFFF )
     else:
       return edk2.readio( io_port, size )

 def write_io_port( self, io_port, value, size ):
     return edk2.writeio( io_port, size, value )


 def load_ucode_update( self, cpu_thread_id, ucode_update_buf ):
     logger().error( "[efi] load_ucode_update is not supported yet" )
     return 0


 def getcwd( self ):
     return os.getcwd()


def get_threads_count ( self ):
    print "OsHelper for %s does not support get_threads_count from OS API"%self.os_system.lower()
    return 0

def get_helper():
    return EfiHelper( )


########NEW FILE########
__FILENAME__ = helper
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup helpers
#@{
# __chipsec/helper/linux/helper.py__ -- Linux helper
#@}
#

__version__ = '1.0'

import struct
import sys
import os
import fcntl
import platform
import ctypes
import fnmatch
from chipsec.helper.oshelper import OsHelperError
from chipsec.logger import logger
from chipsec.hal.uefi_common import *
import errno

from ctypes import *

_IOCTL_BASE = 0
def IOCTL_BASE(): 	return 0x0
def IOCTL_RDIO():	return _IOCTL_BASE + 0x1
def IOCTL_WRIO():	return _IOCTL_BASE + 0x2  
def IOCTL_RDPCI():	return _IOCTL_BASE + 0x3   
def IOCTL_WRPCI():	return _IOCTL_BASE + 0x4
def IOCTL_RDMSR():	return _IOCTL_BASE + 0x5
def IOCTL_WRMSR():	return _IOCTL_BASE + 0x6
def IOCTL_CPUID():	return _IOCTL_BASE + 0x7
def IOCTL_GET_CPU_DESCRIPTOR_TABLE():	return _IOCTL_BASE + 0x8
def IOCTL_HYPERCALL():	return _IOCTL_BASE + 0x9
def IOCTL_SWSMI():	return _IOCTL_BASE + 0xA
def IOCTL_LOAD_UCODE_PATCH():	return _IOCTL_BASE + 0xB


class LinuxHelper:

    def __init__(self):
        import platform
        self.os_system  = platform.system()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.os_machine = platform.machine()
        self.os_uname   = platform.uname()

    def __del__(self):
        try:
            destroy()
        except NameError:
            pass

###############################################################################################
# Driver/service management functions
###############################################################################################

    def create( self ):
        self.init()
        if logger().VERBOSE:
            logger().log("[helper] Linux Helper created")

    def start( self ):
        if logger().VERBOSE:
            logger().log("[helper] Linux Helper started/loaded")

    def stop( self ):
        if logger().VERBOSE:
            logger().log("[helper] Linux Helper stopped/unloaded")

    def delete( self ):
        if logger().VERBOSE:
            logger().log("[helper] Linux Helper deleted")

    def destroy( self ):
        self.stop()
        self.delete()

    def init( self ):
        global _DEV_FH
        _DEV_FH = None
        
        #already initialized?
        if(_DEV_FH != None): return
        
        logger().log("\n****** Chipsec Linux Kernel module is licensed under GPL 2.0\n")

        try: 
            _DEV_FH = open("/dev/chipsec", "r+")
        except IOError as e:
            raise OsHelperError("Unable to open chipsec device. %s"%str(e),e.errno)
        except BaseException as be:
            raise OsHelperError("Unable to open chipsec device. %s"%str(be),errno.ENXIO)
       
        #decode the arg size
        global _PACK
        _PACK = 'I'

        global _IOCTL_BASE
        _IOCTL_BASE = fcntl.ioctl(_DEV_FH, IOCTL_BASE()) << 4 

        global CPU_MASK_LEN
        CPU_MASK_LEN = 8 if sys.maxsize > 2**32 else 4

	
    def close():
        global _DEV_FH
        close(_DEV_FH)
        _DEV_FH = None

###############################################################################################
# Actual API functions to access HW resources
###############################################################################################
    def __mem_block(self, sz, newval = None):	
        if(newval == None):
            return _DEV_FH.read(sz)
        else:
            _DEV_FH.write(newval)
            _DEV_FH.flush()
        return 1

    def mem_read_block(self, addr, sz):
        if(addr != None): _DEV_FH.seek(addr)
        return self.__mem_block(sz)

    def mem_write_block(self, addr, sz, newval):
        if(addr != None): _DEV_FH.seek(addr)
        return self.__mem_block(sz, newval)

    def write_phys_mem(self, phys_address_hi, phys_address_lo, sz, newval):
        if(newval == None): return None
        return self.mem_write_block((phys_address_hi << 32) | phys_address_lo, sz, newval)

    def read_phys_mem(self, phys_address_hi, phys_address_lo, length):
        ret = self.mem_read_block((phys_address_hi << 32) | phys_address_lo, length)
        if(ret == None): return None
        return ret
        
    #DEPRECATED: Pass-through
    def read_pci( self, bus, device, function, address ):
        return self.read_pci_reg(bus, device, function, address)

    def read_pci_reg( self, bus, device, function, offset, size = 4 ):
        _PCI_DOM = 0 #Change PCI domain, if there is more than one. 
        d = struct.pack("5"+_PACK, ((_PCI_DOM << 16) | bus), ((device << 16) | function), offset, size, 0)
        try:
            ret = fcntl.ioctl(_DEV_FH, IOCTL_RDPCI(), d)
        except IOError:
            print "IOError\n"
            return None
        x = struct.unpack("5"+_PACK, ret)
        return x[4]

    def write_pci_reg( self, bus, device, function, offset, value, size = 4 ):
        _PCI_DOM = 0 #Change PCI domain, if there is more than one. 
        d = struct.pack("5"+_PACK, ((_PCI_DOM << 16) | bus), ((device << 16) | function), offset, size, value)
        try:
            ret = fcntl.ioctl(_DEV_FH, IOCTL_WRPCI(), d)
        except IOError:
            print "IOError\n"
            return None
        x = struct.unpack("5"+_PACK, ret)
        return x[4]

    def read_io_port(self, io_port, size):
        in_buf = struct.pack( "3"+_PACK, io_port, size, 0 )
        out_buf = fcntl.ioctl( _DEV_FH, IOCTL_RDIO(), in_buf )
        try:
            if 1 == size:
                value = struct.unpack_from( 'B', out_buf, 2)
            elif 2 == size:
                value = struct.unpack_from( 'H', out_buf, 2)
            else:
                value = struct.unpack_from( 'I', out_buf, 2)
        except:
            logger().error( "DeviceIoControl did not return value of proper size %x (value = '%s')" % (size, out_buf) )

        return value[0]

    def write_io_port( self, io_port, value, size ):
        in_buf = struct.pack( 'HIB', io_port, value, size )
        return fcntl.ioctl( _DEV_FH, IOCTL_WRIO(), in_buf)

    def read_msr(self, thread_id, msr_addr):
        self.set_affinity(thread_id)
        edx = eax = 0
        in_buf = struct.pack( "4"+_PACK, thread_id, msr_addr, edx, eax)
        unbuf = struct.unpack("4"+_PACK, fcntl.ioctl( _DEV_FH, IOCTL_RDMSR(), in_buf ))
        return (unbuf[3], unbuf[2])

    def write_msr(self, thread_id, msr_addr, eax, edx):
        self.set_affinity(thread_id)
        print "Writing msr 0x%x with eax = 0x%x, edx = 0x%x" % (msr_addr, eax, edx)
        in_buf = struct.pack( "4"+_PACK, thread_id, msr_addr, edx, eax )
        fcntl.ioctl( _DEV_FH, IOCTL_WRMSR(), in_buf )	
        return 

    def get_descriptor_table(self, cpu_thread_id, desc_table_code  ):
        in_buf = struct.pack( "5"+_PACK, cpu_thread_id, desc_table_code, 0 , 0, 0) 
        out_buf = fcntl.ioctl( _DEV_FH, IOCTL_GET_CPU_DESCRIPTOR_TABLE(), in_buf)
        (limit,base_hi,base_lo,pa_hi,pa_lo) = struct.unpack( "5"+_PACK, out_buf )
        pa = (pa_hi << 32) + pa_lo
        base = (base_hi << 32) + base_lo
        return (limit,base,pa)

    def do_hypercall(self, vector, arg1, arg2, arg3, arg4, arg5, use_peach):
        in_buf = struct.pack( "7"+_PACK, vector, arg1, arg2, arg3, arg4, arg5, use_peach) 
        out_buf = fcntl.ioctl( _DEV_FH, IOCTL_HYPERCALL(), in_buf)
        regs = struct.unpack( "7"+_PACK, out_buf )
        return regs

    def cpuid(self, eax):
        in_buf = struct.pack( "4"+_PACK, eax, 0, 0, 0) 
        out_buf = fcntl.ioctl( _DEV_FH, IOCTL_CPUID(), in_buf)
        return struct.unpack( "4"+_PACK, out_buf )


    def get_affinity(self):
        CORES = ctypes.cdll.LoadLibrary('./chipsec/helper/linux/cores.so')
        CORES.sched_getaffinity.argtypes = [ctypes.c_int, ctypes.c_int, POINTER(ctypes.c_int)]
        CORES.sched_getaffinity.restype = ctypes.c_int
        pid = ctypes.c_int(0)
        leng = ctypes.c_int(CPU_MASK_LEN) 
        cpu_mask = ctypes.c_int(0)
        if (CORES.sched_getaffinity(pid, leng, byref(cpu_mask)) == 0):
            return cpu_mask.value
        else:
            return None
        
  
    def set_affinity(self, thread_id):
        CORES = ctypes.cdll.LoadLibrary('./chipsec/helper/linux/cores.so')
        pid = ctypes.c_int(0)
        leng = ctypes.c_int(CPU_MASK_LEN) 
        cpu_mask = ctypes.c_int(thread_id)
        ret = CORES.setaffinity(thread_id)
        if(ret == 0):
            return thread_id
        else: 
            #CORES.geterror.restype = ctypes.c_int
            print "set_affinity error: %s" % os.strerror(ret)
            return None
        
    #########
    # UEFI Variable API
    #########

    def get_efivar_from_sys( self, filename ):
        off = 0
        buf = list()
        hdr = 0
        try:
            f =open('/sys/firmware/efi/vars/'+filename+'/data', 'r')
	    data = f.read()
            f.close()

            f = open('/sys/firmware/efi/vars/'+filename+'/guid', 'r')
            guid = (f.read()).strip()
            f.close()

            f = open('/sys/firmware/efi/vars/'+filename+'/attributes', 'r')
            attrstring = f.read()
            attr = 0
            if fnmatch.fnmatch(attrstring, '*NON_VOLATILE*'):
                attr |= EFI_VARIABLE_NON_VOLATILE
            if fnmatch.fnmatch(attrstring, '*BOOTSERVICE*'):
                attr |= EFI_VARIABLE_BOOTSERVICE_ACCESS
            if fnmatch.fnmatch(attrstring, '*RUNTIME*'):
                attr |= EFI_VARIABLE_RUNTIME_ACCESS
            if fnmatch.fnmatch(attrstring, '*ERROR*'):
                attr |= EFI_VARIABLE_HARDWARE_ERROR_RECORD
            if fnmatch.fnmatch(attrstring, 'EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS'):
                attr |= EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS
            if fnmatch.fnmatch(attrstring, '*TIME_BASED_AUTHENTICATED*'):
                attr |= EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS
            if fnmatch.fnmatch(attrstring, '*APPEND_WRITE*'):
                attr |= EFI_VARIABLE_APPEND_WRITE
            f.close()

        except Exception, err:
            logger().error('Failed to read files under /sys/firmware/efi/vars/'+filename)
            data = ""
            guid = 0
            attr = 0
        
        finally:
            return (off, buf, hdr, data, guid, attr)
        

    def get_EFI_variable( self, name, guid ):
        if not name:
            name = '*'
        if not guid:
            guid = '*'
        for var in os.listdir('/sys/firmware/efi/vars'):
            if fnmatch.fnmatch(var, '%s-%s' % (name,guid)):
                return get_efivar_from_sys(var)

    def list_EFI_variables ( self, infcls=2 ):
        varlist = os.listdir('/sys/firmware/efi/vars')
        variables = dict()
        for v in varlist:
            name = v[:-37]
            if name and name is not None:
                variables[name] = []
                var = self.get_efivar_from_sys(v)
                # did we get something real back?
                (off, buf, hdr, data, guid, attr) = var
                if data != "" or guid != 0 or attr != 0:
                    variables[name].append(var)
        return variables

    def set_EFI_variable( name, guid, value ):
        if not name:
            name = '*'
        if not guid:
            guid = '*'
        for var in os.listdir('/sys/firmware/efi/vars'):
            if fnmatch.fnmatch(var, '%s-%s' %name %guid):
                f = open('/sys/firmware/efi/vars/'+var+'/data', 'w')
		f.write(value)
        
    #
    # Interrupts
    #
    def send_sw_smi( self, SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi ):
        print "Sending SW SMI 0x%x with rax = 0x%x, rbx = 0x%x, rcx = 0x%x, rdx = 0x%x, rsi = 0x%x, rdi = 0x%x" % (SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi)
        in_buf = struct.pack( "7"+_PACK, SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi )
        print "NOT IMPLEMENTED IN LINUX HELPER YET ;("
        #fcntl.ioctl( _DEV_FH, IOCTL_SWSMI(), in_buf )	
        return 

    #########


    def getcwd( self ):
        return os.getcwd()
    
    def get_threads_count ( self ):
        print "OsHelper for %s does not support get_threads_count from OS API"%self.os_system.lower()
        return 0

def get_helper():
    return LinuxHelper()





########NEW FILE########
__FILENAME__ = oshelper
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
#
## \addtogroup core
#@{
# __chipsec/helper/oshelper.py__ -- Abstracts support for various OS/environments, wrapper around platform
#                specific code that invokes kernel driver
#@}
#

import sys
import os
import fnmatch
import re
import errno

from chipsec.logger import *
import traceback

_importlib = True
try:
    import importlib
    
except ImportError:
    _importlib = False

# determine if CHIPSEC is loaded as chipsec_*.exe or in python
frozen = hasattr(sys, "frozen") or hasattr(sys, "importers") 
CHIPSEC_LOADED_AS_EXE = True if frozen else False

ZIP_HELPER_RE = re.compile("^chipsec\/helper\/\w+\/\w+\.pyc$", re.IGNORECASE)
def f_mod_zip(x):
    return ( x.find('__init__') == -1 and ZIP_HELPER_RE.match(x) )
def map_modname_zip(x):
    return (x.rpartition('.')[0]).replace('/','.')

class OsHelperError (RuntimeError):
    def __init__(self,msg,errorcode):
        super(OsHelperError,self).__init__(msg)
        self.errorcode = errorcode
        
    
## OS Helper
#
# Abstracts support for various OS/environments, wrapper around platform specific code that invokes kernel driver
class OsHelper:
    def __init__(self):
        self.helper = None
        self.loadHelpers()
        #print "Operating System: %s %s %s %s" % (self.os_system, self.os_release, self.os_version, self.os_machine)
        #print self.os_uname
        if(not self.helper):
            import platform
            os_system  = platform.system()
            raise OsHelperError("Unsupported platform '%s'" % os_system,errno.ENODEV)
        else:
            self.os_system  = self.helper.os_system
            self.os_release = self.helper.os_release
            self.os_version = self.helper.os_version
            self.os_machine = self.helper.os_machine

    def loadHelpers(self):
        if CHIPSEC_LOADED_AS_EXE:
            self.loadHelpersFromEXE()
        else:
            self.loadHelpersFromFileSystem()
            
    def loadHelpersFromEXE(self):
        import zipfile
        myzip = zipfile.ZipFile("library.zip")
        helpers = map( map_modname_zip, filter(f_mod_zip, myzip.namelist()) )
        #print helpers
        for h in helpers:
            self.importModule(h)
            if self.helper : break
        
    def loadHelpersFromFileSystem(self):
        mydir = os.path.dirname(__file__)
        dirs = os.listdir(mydir)
        for adir in dirs:
            if self.helper :
                break
            mypath = os.path.join(mydir,adir)
            if os.path.isdir(mypath):
                for afile in os.listdir(mypath):
                    if fnmatch.fnmatch(afile, '__init__.py') or not fnmatch.fnmatch(afile, '*.py') :
                        continue
#                    print os.path.join(adir,afile)
                    mod_shortname = adir + "." + os.path.splitext(afile)[0]
                    mod_fullname = "chipsec.helper." + mod_shortname
#                    print mod_fullname
                    self.importModule(mod_fullname)
                    if self.helper : break

    def importModule(self, mod_fullname):
        try:
            if _importlib:
                module = importlib.import_module( mod_fullname )
                result = getattr( module, 'get_helper' )(  )
                self.helper = result
            else:
                exec 'import ' + mod_fullname
                exec 'self.helper = ' + mod_fullname + ".get_helper()"
        except ImportError, msg:
            #logger().warn(str(msg) + ' ' + mod_fullname )
            #logger().log_bad(traceback.format_exc())
            pass
        except BaseException, err:
            pass
            

    def __del__(self):
        try:
            destroy()
        except NameError:
            pass

    def start( self ):
        try:
            self.helper.create()
            self.helper.start()
        except (None,Exception) , msg:
            error_no = errno.ENXIO
            if hasattr(msg,'errorcode'):
                error_no = msg.errorcode
            raise OsHelperError("Could not start the OS Helper, are you running as Admin/root?\n           Message: \"%s\"" % msg,error_no)

    def stop( self ):
        self.helper.stop()

    def destroy( self ):
        self.helper.delete()

    def is_linux( self ):
        return ('linux' == self.os_system.lower())
    def is_windows( self ):
        return ('windows' == self.os_system.lower())
    def is_win8_or_greater( self ):
        win8_or_greater = self.is_windows() and ( self.os_release.startswith('8') or ('2008Server' in self.os_release) or ('2012Server' in self.os_release) )
        return win8_or_greater


    #################################################################################################
    # Actual OS helper functionality accessible to HAL components

    #
    # Read/Write PCI configuration registers via legacy CF8/CFC ports
    #
    def read_pci_reg( self, bus, device, function, address, size ):
        if ( 0 != (address & (size - 1)) ):
            logger().warn( "Config register address is not naturally aligned" )
        return self.helper.read_pci_reg( bus, device, function, address, size )

    def write_pci_reg( self, bus, device, function, address, value, size ):
        if ( 0 != (address & (size - 1)) ):
            logger().warn( "Config register address is not naturally aligned" )
        return self.helper.write_pci_reg( bus, device, function, address, value, size )

    #
    # physical_address_hi/physical_address_lo are 32 bit integers
    # 
    def read_phys_mem( self, phys_address_hi, phys_address_lo, length ):
        return self.helper.read_phys_mem( phys_address_hi, phys_address_lo, length )
    def write_phys_mem( self, phys_address_hi, phys_address_lo, length, buf ):
        return self.helper.write_phys_mem( phys_address_hi, phys_address_lo, length, buf )

    #
    # physical_address is 64 bit integer
    # 
    def read_physical_mem( self, phys_address, length ):
        return self.helper.read_phys_mem( (phys_address>>32)&0xFFFFFFFF, phys_address&0xFFFFFFFF, length )
    def write_physical_mem( self, phys_address, length, buf ):
        return self.helper.write_phys_mem( (phys_address>>32)&0xFFFFFFFF, phys_address&0xFFFFFFFF, length, buf )

    #
    # Read/Write I/O port
    #
    def read_io_port( self, io_port, size ):
        return self.helper.read_io_port( io_port, size )
    def write_io_port( self, io_port, value, size ):
        return self.helper.write_io_port( io_port, value, size )

    #
    # Read/Write MSR on a specific CPU thread
    #
    def read_msr( self, cpu_thread_id, msr_addr ):
        return self.helper.read_msr( cpu_thread_id, msr_addr )
    def write_msr( self, cpu_thread_id, msr_addr, eax, edx ):
        return self.helper.write_msr( cpu_thread_id, msr_addr, eax, edx )

    #
    # Load CPU microcode update on a specific CPU thread
    #
    def load_ucode_update( self, cpu_thread_id, ucode_update_buf ):
        return self.helper.load_ucode_update( cpu_thread_id, ucode_update_buf )

    #
    # Read IDTR/GDTR/LDTR on a specific CPU thread
    #
    def get_descriptor_table( self, cpu_thread_id, desc_table_code ):
        return self.helper.get_descriptor_table( cpu_thread_id, desc_table_code )

    #
    # EFI Variable API
    #
    def get_EFI_variable( self, name, guid ):
        return self.helper.get_EFI_variable( name, guid )

    def set_EFI_variable( self, name, guid, var ):
        return self.helper.set_EFI_variable( name, guid, var )

    def list_EFI_variables( self ):
        return self.helper.list_EFI_variables()

    #
    # Xen Hypercall
    #
    def do_hypercall( self, vector, arg1=0, arg2=0, arg3=0, arg4=0, arg5=0, use_peach=0 ):
        return self.helper.do_hypercall( vector, arg1, arg2, arg3, arg4, arg5, use_peach)

    #
    # CPUID
    #
    def cpuid( self, eax ):
        return self.helper.cpuid( eax )

    def get_threads_count( self ):
        return self.helper.get_threads_count()

    def getcwd( self ):
        return self.helper.getcwd()

    #
    # Interrupts
    #
    def send_sw_smi( self, SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi ):
        return self.helper.send_sw_smi( SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi )


_helper  = OsHelper()
def helper():
    return _helper



########NEW FILE########
__FILENAME__ = win32helper
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup helpers
# __chipsec/helper/win/win32helper.py__ -- Management and communication with Windows kernel mode driver
#                   which provides access to hardware resources


# NOTE: on Windows you need to install pywin32 Python extension corresponding to your Python version:
# http://sourceforge.net/projects/pywin32/
#
#
__version__ = '1.0'

import os.path
import struct
import sys
from ctypes import *
from threading import Lock
import platform
import re
from collections import namedtuple

from chipsec.helper.oshelper import OsHelperError
import errno


import pywintypes
import win32service #win32serviceutil, win32api, win32con
import winerror
from win32file import FILE_SHARE_READ, FILE_SHARE_WRITE, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, FILE_FLAG_OVERLAPPED, INVALID_HANDLE_VALUE
import win32api, win32process, win32security, win32file


from chipsec.logger import logger, print_buffer

class PCI_BDF(Structure):
    _fields_ = [("BUS",  c_ushort, 16),  # Bus
                ("DEV",  c_ushort, 16),  # Device
                ("FUNC", c_ushort, 16),  # Function
                ("OFF",  c_ushort, 16)]  # Offset

kernel32 = windll.kernel32


drv_hndl_error_msg = "Cannot open chipsec driver handle. Make sure chipsec driver is installed and started if you are using option -e (see README)"

DRIVER_FILE_NAME = "chipsec_hlpr.sys"
DEVICE_FILE      = "\\\\.\\chipsec_hlpr"
SERVICE_NAME     = "chipsec"
DISPLAY_NAME     = "CHIPSEC Service"

CHIPSEC_INSTALL_PATH = os.path.join(sys.prefix, "Lib\site-packages\chipsec")

# Defines for Win32 API Calls
GENERIC_READ    = 0x80000000
GENERIC_WRITE   = 0x40000000
OPEN_EXISTING   = 0x3

FILE_DEVICE_UNKNOWN = 0x00000022

METHOD_BUFFERED   = 0
METHOD_IN_DIRECT  = 1
METHOD_OUT_DIRECT = 2
METHOD_NEITHER    = 3

FILE_ANY_ACCESS     = 0
FILE_SPECIAL_ACCESS = (FILE_ANY_ACCESS)
FILE_READ_ACCESS    = ( 0x0001 )
FILE_WRITE_ACCESS   = ( 0x0002 )

def CTL_CODE( DeviceType, Function, Method, Access ):
    return ((DeviceType) << 16) | ((Access) << 14) | ((Function) << 2) | (Method)

#
# chipsec driver IOCTL codes
#              
CHIPSEC_CTL_ACCESS = (FILE_READ_ACCESS | FILE_WRITE_ACCESS)

CLOSE_DRIVER                   = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x803, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
READ_PCI_CFG_REGISTER          = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x807, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
WRITE_PCI_CFG_REGISTER         = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x808, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_READ_PHYSMEM             = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x809, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_WRITE_PHYSMEM            = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80a, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_LOAD_UCODE_PATCH         = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80b, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_WRMSR                    = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80c, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_RDMSR                    = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80d, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_READ_IO_PORT             = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80e, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_WRITE_IO_PORT            = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80f, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_GET_CPU_DESCRIPTOR_TABLE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x810, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)
IOCTL_SWSMI                    = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x811, METHOD_BUFFERED, CHIPSEC_CTL_ACCESS)

#
# NT Errors
#
# Defined in WinDDK\7600.16385.1\inc\api\ntstatus.h 
#

#
# UEFI constants
#
# Default buffer size for EFI variables
#EFI_VAR_MAX_BUFFER_SIZE = 128*1024
EFI_VAR_MAX_BUFFER_SIZE = 1024*1024

attributes = {
  "EFI_VARIABLE_NON_VOLATILE"                          : 0x00000001, 
  "EFI_VARIABLE_BOOTSERVICE_ACCESS"                    : 0x00000002,
  "EFI_VARIABLE_RUNTIME_ACCESS"                        : 0x00000004,
  "EFI_VARIABLE_HARDWARE_ERROR_RECORD"                 : 0x00000008,
  "EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS"            : 0x00000010,
  "EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS" : 0x00000020,
  "EFI_VARIABLE_APPEND_WRITE"                          : 0x00000040
}

PyLong_AsByteArray = pythonapi._PyLong_AsByteArray
PyLong_AsByteArray.argtypes = [py_object,
                               c_char_p,
                               c_size_t,
                               c_int,
                               c_int]

def packl_ctypes( lnum, bitlength ):
    length = (bitlength + 7)/8
    a = create_string_buffer( length )
    PyLong_AsByteArray(lnum, a, len(a), 1, 1) # 4th param is for endianness 0 - big, non 0 - little
    return a.raw


#
# Windows 8 NtEnumerateSystemEnvironmentValuesEx (infcls = 2)
#
def guid_str(guid0, guid1, guid2, guid3):
        return ( "%08X-%04X-%04X-%04s-%06s" % (guid0, guid1, guid2, guid3[:2].encode('hex').upper(), guid3[-6::].encode('hex').upper()) )

class EFI_HDR_WIN( namedtuple('EFI_HDR_WIN', 'Size DataOffset DataSize Attributes guid0 guid1 guid2 guid3') ):
        __slots__ = ()
        def __str__(self):
            return """
Header (Windows)
----------------
VendorGuid= {%08X-%04X-%04X-%04s-%06s}
Size      = 0x%08X
DataOffset= 0x%08X
DataSize  = 0x%08X
Attributes= 0x%08X
""" % ( self.guid0, self.guid1, self.guid2, self.guid3[:2].encode('hex').upper(), self.guid3[-6::].encode('hex').upper(), self.Size, self.DataOffset, self.DataSize, self.Attributes )

def getEFIvariables_NtEnumerateSystemEnvironmentValuesEx2( nvram_buf ):
        start = 0
        buffer = nvram_buf
        bsize = len(buffer)
        header_fmt = "<IIIIIHH8s"
        header_size = struct.calcsize( header_fmt )
        variables = dict()
        off = 0
        while (off + header_size) < bsize:
           efi_var_hdr = EFI_HDR_WIN( *struct.unpack_from( header_fmt, buffer[ off : off + header_size ] ) )

           next_var_offset = off + efi_var_hdr.Size
           efi_var_buf     = buffer[ off : next_var_offset ]
           efi_var_data    = buffer[ off + efi_var_hdr.DataOffset : off + efi_var_hdr.DataOffset + efi_var_hdr.DataSize ]

           #efi_var_name = "".join( buffer[ start + header_size : start + efi_var_hdr.DataOffset ] ).decode('utf-16-le')
           str_fmt = "%ds" % (efi_var_hdr.DataOffset - header_size)
           s, = struct.unpack( str_fmt, buffer[ off + header_size : off + efi_var_hdr.DataOffset ] )
           efi_var_name = unicode(s, "utf-16-le", errors="replace").split(u'\u0000')[0]

           if efi_var_name not in variables.keys():
               variables[efi_var_name] = []
           #                                off, buf,         hdr,         data,         guid,                                                                                 attrs
           variables[efi_var_name].append( (off, efi_var_buf, efi_var_hdr, efi_var_data, guid_str(efi_var_hdr.guid0, efi_var_hdr.guid1, efi_var_hdr.guid2, efi_var_hdr.guid3), efi_var_hdr.Attributes) )

           if 0 == efi_var_hdr.Size: break
           off = next_var_offset
 
        return variables
#    return ( start, next_var_offset, efi_var_buf, efi_var_hdr, efi_var_name, efi_var_data, guid_str(efi_var_hdr.guid0, efi_var_hdr.guid1, efi_var_hdr.guid2, efi_var_hdr.guid3), efi_var_hdr.Attributes )





class Win32Helper:

    def __init__(self):
        import platform
        self.os_system  = platform.system()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.os_machine = platform.machine()
        self.os_uname   = platform.uname()
        if "windows" == self.os_system.lower():
            win_ver = "win7_" + self.os_machine.lower() 
            if ("5" == self.os_release): win_ver = "winxp" 
            """
            if ("8" == self.os_release.lower()):
                win_ver = "win7_" + self.os_machine.lower() 
            #elif ("post2008server" == self.os_release.lower()):
            elif ("2008server" in self.os_release.lower()):
                win_ver = "win7_" + self.os_machine.lower() 
            elif ("7" == self.os_release.lower()):
                win_ver = "win7_" + self.os_machine.lower() 
            else:
                logger().warn( "Unknown OS release: %s %s %s" % (self.os_system, self.os_release, self.os_version) )
                win_ver = "win7_" + self.os_machine.lower() 
            """
            logger().log( "[helper] OS: %s %s %s" % (self.os_system, self.os_release, self.os_version) )
            logger().log( "[helper] Using 'helper/win/%s' path for driver" % win_ver )

        self.hs             = None
        self.driver_path    = None
        self.win_ver        = win_ver
        self.driver_handle  = None
        #self.device_file    =  u"%s" % DEVICE_FILE
        self.device_file = pywintypes.Unicode(DEVICE_FILE)

        # enable required SeSystemEnvironmentPrivilege privilege
        privilege = win32security.LookupPrivilegeValue( None, 'SeSystemEnvironmentPrivilege' )
        token = win32security.OpenProcessToken( win32process.GetCurrentProcess(), win32security.TOKEN_READ|win32security.TOKEN_ADJUST_PRIVILEGES )
        win32security.AdjustTokenPrivileges( token, False, [(privilege, win32security.SE_PRIVILEGE_ENABLED)] )
        win32api.CloseHandle( token )       
        # import firmware variable API
        self.GetFirmwareEnvironmentVariable = kernel32.GetFirmwareEnvironmentVariableW
        self.GetFirmwareEnvironmentVariable.restype = c_int
        self.GetFirmwareEnvironmentVariable.argtypes = [c_wchar_p, c_wchar_p, c_void_p, c_int]
        self.SetFirmwareEnvironmentVariable = kernel32.SetFirmwareEnvironmentVariableW
        self.SetFirmwareEnvironmentVariable.restype = c_int
        self.SetFirmwareEnvironmentVariable.argtypes = [c_wchar_p, c_wchar_p, c_void_p, c_int]
        self.NtEnumerateSystemEnvironmentValuesEx = windll.ntdll.NtEnumerateSystemEnvironmentValuesEx
        self.NtEnumerateSystemEnvironmentValuesEx.restype = c_int
        self.NtEnumerateSystemEnvironmentValuesEx.argtypes = [c_int, c_void_p, c_void_p]


    def __del__(self):
        try:
           ##kernel32.CloseHandle( self.driver_handle )
           #win32api.CloseHandle( self.driver_handle )
           del self.driver_handle
           del self.device_file
           #self.delete()
        except NameError:
           pass


###############################################################################################
# Driver/service management functions
###############################################################################################

    def start( self ):

        (type, state, ca, exitcode, svc_exitcode, checkpoint, waithint) = win32service.QueryServiceStatus( self.hs )
        if logger().VERBOSE: logger().log( "[helper] starting chipsec service: handle = 0x%x, type = 0x%x, state = 0x%x" % (self.hs, type, state) )

        if win32service.SERVICE_RUNNING == state:
            if logger().VERBOSE: logger().log( "[helper] chipsec service already running" )           
        else:
           try:
              win32service.StartService( self.hs, None );
              state = win32service.QueryServiceStatus( self.hs )[1]
              while win32service.SERVICE_START_PENDING == state:
                 time.sleep( 1 )
                 state = win32service.QueryServiceStatus( self.hs )[1]
              if win32service.SERVICE_RUNNING == state:
                 if logger().VERBOSE: logger().log( "[helper] chipsec service started (SERVICE_RUNNING)" )           
           except win32service.error, (hr, fn, msg):
              if (winerror.ERROR_ALREADY_EXISTS == hr):
                 if logger().VERBOSE: logger().log( "[helper] chipsec service already exists: %s (%d)" % (msg, hr) )           
              else:
                 win32service.CloseServiceHandle( self.hs )
                 self.hs = None
                 string  = "StartService failed: %s (%d)" % (msg, hr)
                 logger().error( string )
                 raise OsHelperError(string,hr)

        #if logger().VERBOSE:
        #   logger().log( "[helper] chipsec service handle = 0x%08x" % self.hs )

    def create( self ):

        logger().log( "" )
        logger().warn( "Chipsec should only be used on test systems!" )
        logger().warn( "It should not be installed/deployed on production end-user systems." )
        logger().warn( "See WARNING.txt" )
        logger().log( "" )

        try:
            hscm = win32service.OpenSCManager( None, None, win32service.SC_MANAGER_ALL_ACCESS ) # SC_MANAGER_CREATE_SERVICE
        except win32service.error, (hr, fn, msg):
            string = "OpenSCManager failed: %s (%d)" % (msg, hr)
            logger().error( string )
            raise OsHelperError(string,hr)

        if logger().VERBOSE: logger().log( "[helper] SC Manager opened (handle = 0x%08x)" % hscm )

        driver_path = os.path.join( os.path.join( os.path.join( self.getcwd(), "chipsec" ), "helper" ),"win" )            
        if not os.path.exists( driver_path ):
            driver_path = os.path.join( os.path.join( CHIPSEC_INSTALL_PATH, "helper" ),"win" )
        driver_path = os.path.join( os.path.join( driver_path, self.win_ver ), DRIVER_FILE_NAME )

        if os.path.exists( driver_path ) and os.path.isfile( driver_path ):
            self.driver_path = driver_path
            if logger().VERBOSE: logger().log( "[helper] driver path: '%s'" % self.driver_path )
        else:
            logger().error( "could not locate driver file '%.256s'" % driver_path )
            return False

        try:
            self.hs = win32service.CreateService( hscm,
                     SERVICE_NAME,
                     DISPLAY_NAME,
                     (win32service.SERVICE_QUERY_STATUS|win32service.SERVICE_START|win32service.SERVICE_STOP), # SERVICE_ALL_ACCESS, STANDARD_RIGHTS_REQUIRED, DELETE
                     win32service.SERVICE_KERNEL_DRIVER,
                     win32service.SERVICE_DEMAND_START,
                     win32service.SERVICE_ERROR_NORMAL,
                     driver_path,
                     None, 0, u"", None, None )
            if not self.hs:
                raise win32service.error, (0, None, "hs is None")

            if logger().VERBOSE: logger().log( "[helper] service created (handle = 0x%08x)" % self.hs )

        except win32service.error, (hr, fn, msg):
            #if (winerror.ERROR_SERVICE_EXISTS == hr) or (winerror.ERROR_DUPLICATE_SERVICE_NAME == hr):
            if (winerror.ERROR_SERVICE_EXISTS == hr):
                if logger().VERBOSE: logger().log( "[helper] chipsec service already exists: %s (%d)" % (msg, hr) )
                try:
                    self.hs = win32service.OpenService( hscm, SERVICE_NAME, (win32service.SERVICE_QUERY_STATUS|win32service.SERVICE_START|win32service.SERVICE_STOP) ) # SERVICE_ALL_ACCESS
                except win32service.error, (hr, fn, msg):
                    self.hs = None
                    string = "OpenService failed: %s (%d)" % (msg, hr)
                    logger().error( string )
                    raise OsHelperError(string,hr)
            else:
                self.hs     = None
                string      = "CreateService failed: %s (%d)" % (msg, hr)
                logger().error( string )
                raise OsHelperError(string,hr)
            
            #(type, state, ca, exitcode, svc_exitcode, checkpoint, waithint) = win32service.QueryServiceStatus( self.hs )
            #if logger().VERBOSE:
            #   logger().log( "[helper] chipsec service: handle = 0x%x, type = 0x%x, state = 0x%x (SERVICE_RUNNING is 0x%x)" % (self.hs, type, state, win32service.SERVICE_RUNNING) )
            return True

        finally:
            win32service.CloseServiceHandle( hscm )

    def stop( self ):
        state = 0
        if (self.hs is not None):
            if logger().VERBOSE: logger().log( "[helper] stopping service (handle = 0x%08x).." % self.hs )
            try:
                state = win32service.ControlService( self.hs, win32service.SERVICE_CONTROL_STOP )
                #state = win32serviceutil.StopService( name, machine )[1]
            except win32service.error, (hr, fn, msg):
                logger().error( "StopService failed: %s (%d)" % (msg, hr) )
            state = win32service.QueryServiceStatus( self.hs )[1]
            #while win32service.SERVICE_STOP_PENDING == state:
            #   time.sleep( 1 )
            #   state = win32service.QueryServiceStatus( self.hs )[1]

        # Close the driver handle - should do that in __del__ rather than here
        #kernel32.CloseHandle( self.driver_handle )

        return state

    def delete( self ):
        if (self.hs is not None):
            if logger().VERBOSE:
                logger().log( "[helper] deleting service (handle = 0x%08x).." % self.hs )
            win32service.DeleteService( self.hs )
            win32service.CloseServiceHandle( self.hs )
            self.hs = None
        return True

    def destroy( self ):
        self.stop()
        self.delete()

    def get_driver_handle( self ):
        # This is bad but DeviceIoControl fails ocasionally if new device handle is not opened every time ;(
        if (self.driver_handle is not None) and (INVALID_HANDLE_VALUE != self.driver_handle):
            return self.driver_handle

        #self.driver_handle = win32file.CreateFile( device_file, 0, win32file.FILE_SHARE_READ, None, win32file.OPEN_EXISTING, 0, None)
        #self.driver_handle = kernel32.CreateFileW( self.device_file, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None )
        #self.driver_handle = kernel32.CreateFileW( self.device_file, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None )

        self.driver_handle = win32file.CreateFile( self.device_file, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED, None )
        if (self.driver_handle is None) or (INVALID_HANDLE_VALUE == self.driver_handle):
            logger().error( drv_hndl_error_msg )
            raise OsHelperError(drv_hndl_error_msg,errno.ENXIO)
        else:
            if logger().VERBOSE: logger().log( "[helper] opened device '%.64s' (handle: %08x)" % (DEVICE_FILE, self.driver_handle) )
        return self.driver_handle

    def check_driver_handle( self ):
        if (0x6 == kernel32.GetLastError()):
            #kernel32.CloseHandle( self.driver_handle )
            win32api.CloseHandle( self.driver_handle )
            self.driver_handle = None
            self.get_driver_handle()
            logger().warn( "Invalid handle (wtf?): re-opened device '%.64s' (new handle: %08x)" % (self.device_file, self.driver_handle) )
            return False
        return True
          

    #
    # Auxiliary functions
    #
    def get_threads_count ( self ):
        sum = 0
        for i in range(int(kernel32.GetActiveProcessorGroupCount())):
            procs = kernel32.GetActiveProcessorCount(i)
            sum = sum + procs
        return sum

    def getcwd( self ):
        return ("\\\\?\\" + os.getcwd())

    #
    # Generic IOCTL call function
    #
    def _ioctl( self, ioctl_code, in_buf, out_length ):
        out_buf = (c_char * out_length)()
        self.get_driver_handle()
        #ret = kernel32.DeviceIoControl( self.driver_handle, ioctl_code, in_buf, len(in_buf), byref(out_buf), out_length, byref(out_size), None )
        if logger().VERBOSE: print_buffer( in_buf )
        try:
           out_buf = win32file.DeviceIoControl( self.driver_handle, ioctl_code, in_buf, out_length, None )       
        except pywintypes.error, msg:
           logger().error( 'DeviceIoControl returned error: %s' % str(msg) )
           return None
        return out_buf

###############################################################################################
# Actual driver IOCTL functions to access HW resources
###############################################################################################

    def read_phys_mem( self, phys_address_hi, phys_address_lo, length ):
        out_length = length
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '3I', phys_address_hi, phys_address_lo, length )
        out_buf = self._ioctl( IOCTL_READ_PHYSMEM, in_buf, out_length )

        del in_buf, out_length, out_size
        return out_buf

    def write_phys_mem( self, phys_address_hi, phys_address_lo, length, buf ):
        in_length = length + 12
        out_buf = (c_char * 4)()
        out_size = c_ulong(4)
        in_buf = struct.pack( '3I', phys_address_hi, phys_address_lo, length ) + buf

        out_buf = self._ioctl( IOCTL_WRITE_PHYSMEM, in_buf, 4 )

        del in_buf, in_length, out_size
        return out_buf

    def read_msr( self, cpu_thread_id, msr_addr ):

        (eax,edx) = (0,0)
        out_length = 8
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '=BI', cpu_thread_id, msr_addr )
        out_buf = self._ioctl( IOCTL_RDMSR, in_buf, out_length )     
        try:
           (eax, edx) = struct.unpack( '2I', out_buf )
        except:
           logger().error( 'DeviceIoControl did not return 2 DWORD values' )
        
        del in_buf, out_length, out_size
        
        return (eax, edx)

    def write_msr( self, cpu_thread_id, msr_addr, eax, edx ):

        out_length = 0
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '=B3I', cpu_thread_id, msr_addr, eax, edx )
        out_buf = self._ioctl( IOCTL_WRMSR, in_buf, out_length )     

        del in_buf, out_length, out_size
        return

    def read_pci_reg( self, bus, device, function, address, size ):
        value = 0xFFFFFFFF
        bdf = PCI_BDF( bus&0xFFFF, device&0xFFFF, function&0xFFFF, address&0xFFFF )
        out_length = size
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '4HB', bdf.BUS, bdf.DEV, bdf.FUNC, bdf.OFF, size )

        out_buf = self._ioctl( READ_PCI_CFG_REGISTER, in_buf, out_length )
        try:
           if 1 == size:
              value = struct.unpack( 'B', out_buf )[0]
           elif 2 == size:
              value = struct.unpack( 'H', out_buf )[0]
           else:
              value = struct.unpack( 'I', out_buf )[0]
        except:
           logger().error( "DeviceIoControl did not return value of proper size %x (value = '%s')" % (size, out_buf.raw) )
        del in_buf, out_length, out_size

        return value

    def write_pci_reg( self, bus, device, function, address, value, size ):
        bdf = PCI_BDF( bus&0xFFFF, device&0xFFFF, function&0xFFFF, address&0xFFFF )
        out_length = 0
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '4HIB', bdf.BUS, bdf.DEV, bdf.FUNC, bdf.OFF, value, size )
        out_buf = self._ioctl( WRITE_PCI_CFG_REGISTER, in_buf, out_length )     

        del in_buf, out_length, out_size
        return

    def load_ucode_update( self, cpu_thread_id, ucode_update_buf ):

        in_length = len(ucode_update_buf) + 3
        out_length = 0
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '=BH', cpu_thread_id, len(ucode_update_buf) ) + ucode_update_buf
        #print_buffer( in_buf )
        out_buf = self._ioctl( IOCTL_LOAD_UCODE_PATCH, in_buf, out_length )     

        del in_buf, in_length, out_size
        return True

    def read_io_port( self, io_port, size ):
        in_buf = struct.pack( '=HB', io_port, size )
        out_buf = self._ioctl( IOCTL_READ_IO_PORT, in_buf, size )
        try:
          if 1 == size:
             value = struct.unpack( 'B', out_buf )[0]
          elif 2 == size:
             value = struct.unpack( 'H', out_buf )[0]
          else:
             value = struct.unpack( 'I', out_buf )[0]
        except:
           logger().error( "DeviceIoControl did not return value of proper size %x (value = '%s')" % (size, out_buf) )

        return value

    def write_io_port( self, io_port, value, size ):
        in_buf = struct.pack( '=HIB', io_port, value, size )
        return self._ioctl( IOCTL_WRITE_IO_PORT, in_buf, 0 )


    #
    # IDTR/GDTR/LDTR
    #
    def get_descriptor_table( self, cpu_thread_id, desc_table_code  ):
        in_buf = struct.pack( 'BB', cpu_thread_id, desc_table_code )
        out_buf = self._ioctl( IOCTL_GET_CPU_DESCRIPTOR_TABLE, in_buf, 18 )
        (limit,base,pa) = struct.unpack( '=HQQ', out_buf )
        return (limit,base,pa)


    #
    # EFI Variable API
    #
    def get_EFI_variable( self, name, guid ):
        if logger().VERBOSE: logger().log( "[helper] calling GetFirmwareEnvironmentVariable( name='%s', GUID='%s' ).." % (name, "{%s}" % guid) )
        efi_var = create_string_buffer( EFI_VAR_MAX_BUFFER_SIZE )
        length = self.GetFirmwareEnvironmentVariable( name, "{%s}" % guid, efi_var, EFI_VAR_MAX_BUFFER_SIZE )
        if (0 == length) or (efi_var is None):
           if logger().VERBOSE or logger().UTIL_TRACE:
              logger().error( 'GetFirmwareEnvironmentVariable failed (GetLastError = 0x%x)' % kernel32.GetLastError() )
              print WinError()
           return None
           #raise WinError(errno.EIO,"Unable to get EFI variable")
        return efi_var[:length]

    def set_EFI_variable( self, name, guid, var ):
        var_len = 0
        if var is None: var = bytes(0)
        else: var_len = len(var)
        if logger().VERBOSE: logger().log( "[helper] calling SetFirmwareEnvironmentVariable( name='%s', GUID='%s', length=0x%X ).." % (name, "{%s}" % guid, var_len) )
        success = self.SetFirmwareEnvironmentVariable( name, "{%s}" % guid, var, var_len )
        if 0 == success:
           err = kernel32.GetLastError()
           if logger().VERBOSE or logger().UTIL_TRACE:
              logger().error( 'SetFirmwareEnvironmentVariable failed (GetLastError = 0x%x)' % err )
              print WinError()
           #raise WinError(errno.EIO, "Unable to set EFI variable")
        return success

    def list_EFI_variables( self, infcls=2 ):
        if logger().VERBOSE: logger().log( '[helper] calling NtEnumerateSystemEnvironmentValuesEx( infcls=%d )..' % infcls )
        efi_vars = create_string_buffer( EFI_VAR_MAX_BUFFER_SIZE )
        length = packl_ctypes( long(EFI_VAR_MAX_BUFFER_SIZE), 32 )
        status = self.NtEnumerateSystemEnvironmentValuesEx( infcls, efi_vars, length )
        status = ( ((1 << 32) - 1) & status)
        if (0xC0000023 == status):
           retlength, = struct.unpack("<I", length)
           efi_vars = create_string_buffer( retlength )
           status = self.NtEnumerateSystemEnvironmentValuesEx( infcls, efi_vars, length )
        elif (0xC0000002 == status):
           logger().warn( 'NtEnumerateSystemEnvironmentValuesEx was not found (NTSTATUS = 0xC0000002)' )
           logger().log( '[*] Your Windows does not expose UEFI Runtime Variable API. It was likely installed as legacy boot. To use UEFI variable functions, chipsec needs to run in OS installed with UEFI boot (enable UEFI Boot in BIOS before installing OS)' )
           return None
        if 0 != status:
           logger().error( 'NtEnumerateSystemEnvironmentValuesEx failed (GetLastError = 0x%x)' % kernel32.GetLastError() )
           logger().error( '*** NTSTATUS: %08X' % ( ((1 << 32) - 1) & status) )
           raise WinError()
        # for debug purposes (in case NtEnumerateSystemEnvironmentValuesEx changes format of the output binary)
        #from chipsec.file import write_file
        #write_file( 'list_EFI_variables.bin', efi_vars )
        if logger().VERBOSE: logger().log( '[helper] len(efi_vars) = 0x%X (should be 0x20000)' % len(efi_vars) )
        return getEFIvariables_NtEnumerateSystemEnvironmentValuesEx2( efi_vars )

    #
    # Interrupts
    #
    def send_sw_smi( self, SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi ):
        out_length = 0
        out_buf = (c_char * out_length)()
        out_size = c_ulong(out_length)
        in_buf = struct.pack( '=H6Q', SMI_code_data, _rax, _rbx, _rcx, _rdx, _rsi, _rdi )
        out_buf = self._ioctl( IOCTL_SWSMI, in_buf, out_length )     
        del in_buf, out_length, out_size
        return

    

#
# Get instance of this OS helper 
#
def get_helper():
    return Win32Helper( )



########NEW FILE########
__FILENAME__ = logger
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------
## \addtogroup core
# __chipsec/logger.py__ - logging functions
#
#

import platform
import string
import sys
import os
from time import localtime, strftime

from chipsec.xmlout import xmlAux
import traceback


RESET     =0
BRIGHT    =1
DIM       =2
UNDERLINE =3
BLINK     =4
REVERSE   =7
HIDDEN    =8

BLACK     =0
RED       =1
GREEN     =2
YELLOW    =3
BLUE      =4
MAGENTA   =5
CYAN      =6
WHITE     =7

LOG_PATH                = os.path.join( os.getcwd(), "logs" )
#LOG_STATUS_FILE_NAME    = ""
#LOG_COMPLETED_FILE_NAME = ""

#
# Colored output
# 
if "windows" == platform.system().lower():

    try:
        import WConio

        COLOR_ID = {
                  BLACK  : WConio.BLACK,
                  RED    : WConio.LIGHTRED,
                  GREEN  : WConio.LIGHTGREEN,
                  YELLOW : WConio.YELLOW,
                  BLUE   : WConio.LIGHTBLUE,
                  MAGENTA: WConio.MAGENTA,
                  CYAN   : WConio.CYAN,
                  WHITE  : WConio.WHITE
                  }
        
        def log_color( fg_color, text ):
            # Store current attribute settings
            old_setting = WConio.gettextinfo()[4] & 0x00FF
            WConio.textattr( COLOR_ID[ fg_color ] )
            print text
            WConio.textattr( old_setting )

    except ImportError, e:
        #print "WConio package is not installed. No colored output" 
        def log_color( fg_color, text ):
            print text

elif "linux" == platform.system().lower():
    def log_color( fg_color, text ):
        #_text = "\033[%dm" + text + "\033[0m" % (fg_color + 30) #FIXME:     _text = "\033[%dm" + text + "\033[0m" % (fg_color + 30) \n TypeError: not all arguments converted during string formatting

        print text #_text 

else:
    def log_color( fg_color, text ):
        print text




class LoggerError (RuntimeWarning):
    pass

class Logger:
    """Class for logging to console, text file or XML."""

    def __init__( self ):
        """The Constructor."""
        pass
        self.mytime = localtime()
        self.logfile = None
        #Used for interaction with XML output classes.
        self.xmlAux = xmlAux()
        #self._set_log_files()
    
    def set_xml_file(self, name=None):
        self.xmlAux.set_xml_file(name)

    def saveXML(self):
        self.xmlAux.saveXML()
    
    def set_log_file( self, name=None ):
        """Sets the log file for the output."""
        # Close current log file if it's opened
        self.disable()
        self.LOG_FILE_NAME = name
        # specifying name=None effectively disables logging to file
        if self.LOG_FILE_NAME:
            # Open new log file and keep it opened
            try:
                self.logfile = open( self.LOG_FILE_NAME, 'a+' )
                self.LOG_TO_FILE = True
            except None:
                print ("WARNING: Could not open log file '%s'" % name)

    def set_default_log_file( self ):
        """Sets the default log file for the output."""
        # Close current log file if it's opened
        self.disable()
        if not os.path.exists( LOG_PATH ): os.makedirs( LOG_PATH )
        self.LOG_FILE_NAME = os.path.join( LOG_PATH, strftime( '%Y_%m_%d__%H%M%S', self.mytime ) + '.log')
        # Open new log file and keep it opened
        try:
            self.logfile = open( self.LOG_FILE_NAME, 'a+' )
            self.LOG_TO_FILE = True
        except None:
            print ("WARNING: Could not open log file '%s'" % self.LOG_FILE_NAME)

    def set_status_log_file( self ):
        """Sets the status log file for the output."""
        if not os.path.exists(LOG_PATH):
            os.makedirs(LOG_PATH)
        self.LOG_STATUS_FILE_NAME =   os.path.join( LOG_PATH, strftime('%Y_%m_%d__%H%M%S', self.mytime ) + '_results.log')
        self.LOG_TO_STATUS_FILE = True

    def close( self ):
        """Closes the log file."""
        if self.logfile:
            try:
                self.logfile.close()
            except None:
                print 'WARNING: Could not close log file'
            finally:
                self.logfile = None

    def disable( self ):
        """Disables the logging to file and closes the file if any."""
        self.LOG_TO_FILE = False
        self.LOG_FILE_NAME = None
        self.close()
        #self.LOG_TO_STATUS_FILE = False
        #self.LOG_STATUS_FILE_NAME = None

    def __del__(self):
        """Disables the logger."""
        self.disable()

    ######################################################################
    # Logging functions
    ######################################################################

    def log( self, text):
        """Sends plain text to logging."""
        self._log(text, None, None)

    
    def _log(self, text, color, isStatus):
        """Internal method for logging"""
        if self.LOG_TO_FILE:
            self._save_to_log_file( text )
        else:              
            if color:
                log_color( color, text )
            else:
                print text
            self.xmlAux.append_stdout(text)

        if isStatus: self._save_to_status_log_file( text )
  
    def error( self, text ):
        """Logs an Error message"""
        text = "ERROR: " + text
        self._log(text, RED, None)

    def warn( self, text ):
        """Logs an Warning message"""
        text = "WARNING: " + text
        self._log(text, YELLOW, None)

    def log_passed_check( self, text ):
        """Logs a Test as PASSED, this is used for XML output.
           If XML file was not specified, then it will just print a PASSED test message.
        """
        self.log_passed(text)
        self.xmlAux.passed_check()

    def log_failed_check( self, text ):
        """Logs a Test as FAILED, this is used for XML output.
           If XML file was not specified, then it will just print a FAILED test message.
        """
        self.log_failed(text)
        self.xmlAux.failed_check( text )

    def log_error_check( self, text ):
        """Logs a Test as ERROR, this is used for XML output.
           If XML file was not specified, then it will just print a ERROR test message.
        """
        self.error(text)
        self.xmlAux.error_check( text )

    def log_skipped_check( self, text ):
        """Logs a Test as SKIPPED, this is used for XML output.
           If XML file was not specified, then it will just print a SKIPPED test message.
        """
        self.log_skipped(text)
        self.xmlAux.skipped_check( text )

    def log_warn_check( self, text ):
        """Logs a Warning test, a warning test is considered equal to a PASSED test.
           Logs a Test as PASSED, this is used for XML output."""
        self.log_warning(text)
        self.xmlAux.passed_check()


    def log_passed( self, text ):
        """Logs a passed message."""
        text = "[+] PASSED: " + text
        self._log(text, GREEN, True)

    def log_failed( self, text ):
        """Logs a failed message."""
        text = "[-] FAILED: " + text
        self._log(text, RED, True)

    def log_warning( self, text ):
        """Logs a Warning message"""
        text = "[!] WARNING: " + text
        self._log(text, YELLOW, None)
        #self.xmlAux.passed_check()
    
    def log_skipped( self, text ):
        """Logs a skipped message."""
        text = "[*] SKIPPED: " + text
        self._log(text, YELLOW, True)

    def log_heading( self, text ):
        """Logs a heading message."""
        self._log(text, BLUE, None)
        
    def log_important( self, text ):
        """Logs a important message."""
        text = "[!] " + text
        self._log(text, RED, None)
        
    def log_result( self, text ):
        """Logs a result message."""
        text = "[+] " + text
        self._log(text, GREEN, None)

    def log_bad( self, text ):
        """Logs a bad message, so it calls attention in the information displayed."""
        text = "[-] " + text
        self._log(text, RED, None)
        
    def log_good( self, text ):
        """Logs a message, if colors available, displays in green."""
        text = "[+] " + text
        self._log(text, GREEN, None)
        
    def log_unknown( self, text ):
        """Logs a message with a question mark."""
        text = "[?] " + text
        self._log(text, None, None)
        
    def start_test( self, test_name ):
        """Logs the start point of a Test, this is used for XML output.
           If XML file was not specified, it will just display a banner for the test name.
        """
        text =        "[x][ =======================================================================\n"
        text = text + "[x][ Test: " + test_name + "\n"
        text = text + "[x][ ======================================================================="
        self._log(text, BLUE, True)
        self.xmlAux.start_test( test_name )


    def start_module( self, module_name ):
        """Displays a banner for the module name provided."""
        text = "\n[+] imported %s" % module_name
        self._log(text, None, None)
        self.xmlAux.start_module( module_name )

    def end_module( self, module_name ):
        self.xmlAux.end_module( module_name )

    def _write_log( self, text, filename ):
#        with open(filename, 'a+') as f:
#            print>>f, text
#
#		f = open(filename, 'a+')
#		try:
#			print>>f, text
#		finally:
#			f.close()
        print >> self.logfile, text


    def _save_to_status_log_file(self, text):
        if(self.LOG_TO_STATUS_FILE):
            self._write_log(text, self.LOG_STATUS_FILE_NAME)
    
    def _save_to_log_file(self, text):
        if(self.LOG_TO_FILE):
            self._write_log(text, self.LOG_FILE_NAME)
    
    VERBOSE    = False
    UTIL_TRACE = False
    LOG_TO_STATUS_FILE = False
    LOG_TO_FILE = False
    LOG_STATUS_FILE_NAME = ""
    LOG_FILE_NAME = ""
    DEBUG       = False

_logger  = Logger()
def logger():
    """Returns a Logger instance."""
    return _logger


##################################################################################
# Hex dump functions
##################################################################################

def dump_buffer( arr, length = 8 ):
    """Dumps the buffer."""
    tmp=[]
    tmp_str=[]
    i=1
    for c in arr:
        tmp+=["%2.2x "%ord(c)]
        #if 0xD == ord(c) or 0xA == ord(c):
        if c in string.whitespace:
            ch = " "
        else:
            ch = ord(c)
        tmp_str+=["%c"%ch]
        if i%length==0:
            tmp+=["| "]
            tmp+=tmp_str
            tmp+=["\n"]
            tmp_str=[]
        #print tmp
        #print "\n"
        i+=1
    if 0 != len(arr)%length:
        tmp+=[ (length - len(arr)%length) * 3*" " ]
        tmp+=["| "]
        tmp+=tmp_str
        tmp+=["\n"]
    return "".join(tmp)

def print_buffer( arr, length = 16 ):
    """Prints the buffer."""
    tmp=[]
    tmp_str=[]
    i=1
    for c in arr:
        tmp+=["%2.2x "%ord(c)]
        if (not c in string.printable) or (c in string.whitespace):
            ch = " "
        else:
            ch = ord(c)
        tmp_str+=["%c"%ch]
        if i%length==0:
            tmp+=["| "]
            tmp+=tmp_str
            tmp_s = "".join(tmp)
            logger().log( tmp_s )
            tmp_str=[]
            tmp=[]
        i+=1

    if 0 != len(arr)%length:
        tmp+=[ (length - len(arr)%length) * 3*" " ]
        tmp+=["| "]
        tmp+=tmp_str
        tmp_s = "".join(tmp)
        logger().log( tmp_s )

########NEW FILE########
__FILENAME__ = bios_kbrd_buffer
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



## \addtogroup modules
# __chipsec/modules/common/bios_kbrd_buffer.py__ - checks for BIOS/HDD password exposure thorugh BIOS keyboard buffer
#

## \file
# checks for exposure of pre-boot passwords (BIOS/HDD/pre-bot authentication SW) in the BIOS keyboard buffer
#
# __chipsec/modules/common/bios_kbrd_buffer.py__
# This vulnerability is disclosed by Jonathan Brossard in
# 'Bypassing pre-boot authentication passwords by instrumenting the BIOS keyboard buffer'
#

COMMON_FILL_PTRN = "".join( ['%c' % chr(x + 0x1E) for x in range(32)] )

from chipsec.module_common import *

from chipsec.hal.mmio import *
from chipsec.hal.spi import *

logger = logger()

def check_BIOS_keyboard_buffer():
    logger.start_test( "Pre-boot Passwords in the BIOS Keyboard Buffer" )        

    bios_kbrd_buf_clear = 0

    kbrd_buf_head = cs.mem.read_physical_mem_dword( 0x41A ) & 0x000000FF
    kbrd_buf_tail = cs.mem.read_physical_mem_dword( 0x41C ) & 0x000000FF
    logger.log( "[*] Keyboard buffer head pointer = 0x%X (at 0x41A), tail pointer = 0x%X (at 0x41C)" % (kbrd_buf_head,kbrd_buf_tail) )
    bios_kbrd_buf = cs.mem.read_physical_mem( 0x41E, 32 )
    logger.log( "[*] Keyboard buffer contents (at 0x41E):" )
    print_buffer( bios_kbrd_buf )

    #try:
       #s = struct.unpack( '32c', bios_kbrd_buf.raw )
    s = struct.unpack( '32c', bios_kbrd_buf )
    #except:
    #   logger.error( 'Cannot convert buffer to char sequence' )
    #   return -1
    
    has_contents = False
     
    if COMMON_FILL_PTRN == bios_kbrd_buf:
        logger.log_passed_check( "Keyboard buffer is filled with common fill pattern" )
        return ModuleResult.PASSED

    for x in range(32):
        if ( chr(0) != s[x] and chr(0x20) != s[x] ):
            has_contents = True
            break

    if (0x1E < kbrd_buf_tail) and (kbrd_buf_tail <= 0x1E+32):
        #has_contents = True
        logger.log_bad( "Keyboard buffer tail points inside the buffer (= 0x%X)" % kbrd_buf_tail )
        logger.log( "    It may potentially expose lengths of pre-boot passwords. Was your password %d characters long?" % ((kbrd_buf_tail+2 - 0x1E)/2) )

    logger.log( "[*] Checking contents of the keyboard buffer..\n" )

    if has_contents: logger.log_warn_check( "Keyboard buffer is not empty. The test cannot determine conclusively if it contains pre-boot passwords.\n    The contents might have not been cleared by pre-boot firmware or overwritten with garbage.\n    Visually inspect the contents of keyboard buffer for pre-boot passwords (BIOS, HDD, full-disk encryption)." )
    else:            logger.log_passed_check( "Keyboard buffer looks empty. Pre-boot passwords don't seem to be exposed" )

    return (ModuleResult.WARNING if has_contents else ModuleResult.PASSED)

# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    return check_BIOS_keyboard_buffer()

########NEW FILE########
__FILENAME__ = bios_ts
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/common/bios_ts.py__ -checks for BIOS Top Swap Mode
#

from chipsec.module_common import *

from chipsec.hal.mmio import *

logger = logger()


def get_RCBA_general_registers_base():
    rcba_general_base = get_MMIO_base_address( cs, MMIO_BAR_LPCRCBA ) + RCBA_GENERAL_CONFIG_OFFSET
    logger.log( "[*] RCBA General Config base: 0x%08X" % rcba_general_base )
    return rcba_general_base

def check_top_swap_mode():
    logger.start_test( "BIOS Interface Lock and Top Swap Mode" )

    rcba_general_base = get_RCBA_general_registers_base()
    gcs_reg_value = cs.mem.read_physical_mem_dword( rcba_general_base + RCBA_GC_GCS_REG_OFFSET )
    logger.log( "[*] GCS (General Control and Status) register = 0x%08X" % gcs_reg_value )
    logger.log( "    [10] BBS  (BIOS Boot Straps)         = 0x%X " % ((gcs_reg_value & RCBA_GC_GCS_REG_BBS_MASK)>>10) )
    logger.log( "    [00] BILD (BIOS Interface Lock-Down) = %u" % (gcs_reg_value & RCBA_GC_GCS_REG_BILD_MASK) )

    buc_reg_value = cs.mem.read_physical_mem_dword( rcba_general_base + RCBA_GC_BUC_REG_OFFSET )
    logger.log( "[*] BUC (Backed Up Control) register = 0x%08X" % buc_reg_value )
    logger.log( "    [00] TS (Top Swap) = %u" % (buc_reg_value & RCBA_GC_BUC_REG_TS_MASK) )

    reg_value = cs.pci.read_byte( 0, 31, 0, LPC_BC_REG_OFF )
    BcRegister = LPC_BC_REG( reg_value, (reg_value>>5)&0x1, (reg_value>>4)&0x1, (reg_value>>2)&0x3, (reg_value>>1)&0x1, reg_value&0x1 )
    #logger.log( BcRegister )
    logger.log( "[*] BC (BIOS Control) register = 0x%02X" % reg_value )
    logger.log( "    [04] TSS (Top Swap Status) = %u" % BcRegister.TSS )
    logger.log( "[*] BIOS Top Swap mode is %s" % ('enabled' if BcRegister.TSS else 'disabled') )
  
    logger.log( '' )
    if 0 == (gcs_reg_value & RCBA_GC_GCS_REG_BILD_MASK):
       logger.log_failed_check( "BIOS Interface is not locked (including Top Swap Mode)" )
       return False
    else:
       logger.log_passed_check( "BIOS Interface is locked (including Top Swap Mode)" )
       return True


# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    return check_top_swap_mode()

########NEW FILE########
__FILENAME__ = bios_wp
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/common/bios.py__ - checks if BIOS Write Protection HW mechanisms are enabled
#



from chipsec.module_common import *

from chipsec.hal.mmio import *
from chipsec.hal.spi import *

import fnmatch
import os

logger = logger()
spi    = SPI( cs )

def check_BIOS_write_protection():
    logger.start_test( "BIOS Region Write Protection" )
    #
    # BIOS Control (BC) 0:31:0 PCIe CFG register
    #
    reg_value = cs.pci.read_byte( 0, 31, 0, LPC_BC_REG_OFF )
    BcRegister = LPC_BC_REG( reg_value, (reg_value>>5)&0x1, (reg_value>>4)&0x1, (reg_value>>2)&0x3, (reg_value>>1)&0x1, reg_value&0x1 )
    logger.log( BcRegister )

    # Is the BIOS flash region write protected?
    write_protected = 0
    if 1 == BcRegister.BLE and 0 == BcRegister.BIOSWE:
       if 1 == BcRegister.SMM_BWP:
          logger.log_good( "BIOS region write protection is enabled (writes restricted to SMM)" )
          write_protected = 1
       else:
          logger.log_important( "Enhanced SMM BIOS region write protection has not been enabled (SMM_BWP is not used)" )
    else:
       logger.log_bad( "BIOS region write protection is disabled!" )

    return write_protected == 1

def check_SPI_protected_ranges():
    #logger.start_test( "SPI Protected Ranges" )
    (bios_base,bios_limit,bios_freg) = spi.get_SPI_region( BIOS )
    logger.log( "\n[*] BIOS Region: Base = 0x%08X, Limit = 0x%08X" % (bios_base,bios_limit) )
    spi.display_SPI_Protected_Ranges()

    pr_cover_bios = False
    pr_partial_cover_bios = False
#    for j in range(5):
#        (base,limit,wpe,rpe,pr_reg_off,pr_reg_value) = spi.get_SPI_Protected_Range( j )
#        if (wpe == 1 and base < limit and base <= bios_base and limit >= bios_limit):
#            pr_cover_bios = True
#        if (wpe == 1 and base < limit and limit > bios_base):
#            pr_partial_cover_bios = True

    areas_to_protect  = [(bios_base, bios_limit)]
    protected_areas = list()


    for j in range(5):
        (base,limit,wpe,rpe,pr_reg_off,pr_reg_value) = spi.get_SPI_Protected_Range( j )
        if base > limit: continue
        if wpe == 1:
            for area in areas_to_protect:
                # overlap bottom
                start,end = area
                if base <= start and limit >= start:
                    if limit > end:
                        areas_to_protect.remove(area)
                    else:
                        areas_to_protect.remove(area)
                        area = (limit+1,end)
                        areas_to_protect.append(area)
                        
                # overlap top
                elif base <= end and limit >= end:
                    if base < start:
                        areas_to_protect.remove(area)
                    else:
                        areas_to_protect.remove(area)
                        area = (start,base-1)
                        areas_to_protect.append(area)
                        start,end = area
                # split
                elif base > start and limit < end:
                    areas_to_protect.remove(area)
                    areas_to_protect.append((start,base-1))
                    areas_to_protect.append((limit+1, end))


    if (len(areas_to_protect)  == 0):
        pr_cover_bios = True
    else:
        if (len(areas_to_protect) != 1 or areas_to_protect[0] != (bios_base,bios_limit)):
            pr_partial_cover_bios = True

    if pr_partial_cover_bios:
       logger.log( '' )
       logger.log_important( "SPI protected ranges write-protect parts of BIOS region (other parts of BIOS can be modified)" )

    else:
        if not pr_cover_bios:
            logger.log( '' )
            logger.log_important( "None of the SPI protected ranges write-protect BIOS region" )

    return pr_cover_bios

# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    wp = check_BIOS_write_protection()    
    spr = check_SPI_protected_ranges()
    #spi.display_SPI_Ranges_Access_Permissions()
    #check_SMI_locks()

    logger.log('')
    if wp:
        if spr:  logger.log_passed_check( "BIOS is write protected (by SMM and SPI Protected Ranges)" )
        else:    logger.log_passed_check( "BIOS is write protected" )
    else:
        if spr:  logger.log_passed_check( "SPI Protected Ranges are configured to write protect BIOS" )
        else:
            logger.log_important( 'BIOS should enable all available SMM based write protection mechanisms or configure SPI protected ranges to protect the entire BIOS region' )
            logger.log_failed_check( "BIOS is NOT protected completely" )

    return wp or spr

########NEW FILE########
__FILENAME__ = keys
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/secureboot/keys.py__ - verify protections of Secure Boot key EFI variables


from chipsec.module_common import *

from chipsec.file          import *
from chipsec.hal.uefi      import *

# ############################################################
# SPECIFY PLATFORMS THIS MODULE IS APPLICABLE TO
# ############################################################
_MODULE_NAME = 'keys'
AVAILABLE_MODULES[ CHIPSET_ID_COMMON ].append( _MODULE_NAME )
TAGS = [MTAG_SECUREBOOT]


logger = logger()
_uefi  = UEFI( cs.helper )

SECURE = 0x1
INSECURE = 0x2
ERROR = 0x4

def check_EFI_variable_authentication( name, guid ):
    logger.log( "[*] Checking EFI variable %s {%s}.." % (name, guid) )
    orig_var = _uefi.get_EFI_variable( name, guid, None )
    if not orig_var:
        logger.log( "[*] EFI variable %s {%s} doesn't exist" % (name, guid) )
        return ERROR
    fname = name + '_' + guid + '.bin'
    if logger.VERBOSE: write_file( fname, orig_var )
    origvar_len = len(orig_var)
    mod_var = chr( ord(orig_var[0]) ^ 0xFF ) + orig_var[1:] 
    if origvar_len > 1: mod_var = mod_var[:origvar_len-1] + chr( ord(mod_var[origvar_len-1]) ^ 0xFF )
    if logger.VERBOSE: write_file( fname + '.mod', mod_var )
    status = _uefi.set_EFI_variable( name, guid, mod_var )
    if not status: logger.log( '[*] Writing EFI variable %s did not succeed. Verifying contents..' % name )
    new_var = _uefi.get_EFI_variable( name, guid, None )
    if logger.VERBOSE: write_file( fname + '.new', new_var )
    ok = (origvar_len == len(new_var))
    for i in range( origvar_len ):
        if not (new_var[i] == orig_var[i]):
            ok = INSECURE
            break
    if ok == INSECURE:
        logger.log_bad( "EFI variable %s is not protected! It has been modified. Restoring original contents.." % name )
        _uefi.set_EFI_variable( name, guid, orig_var )
    else:                                                                     
        logger.log_good( "Could not modify EFI variable %s {%s}" % (name, guid) )
    return ok

# checks authentication of Secure Boot EFI variables
def check_secureboot_key_variables():
    sts = 0
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_PK,         EFI_VARIABLE_DICT[EFI_VAR_NAME_PK]         )
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_KEK,        EFI_VARIABLE_DICT[EFI_VAR_NAME_KEK]        )
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_db,         EFI_VARIABLE_DICT[EFI_VAR_NAME_db]         )
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_dbx,        EFI_VARIABLE_DICT[EFI_VAR_NAME_dbx]        )
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_SecureBoot, EFI_VARIABLE_DICT[EFI_VAR_NAME_SecureBoot] )
    sts |= check_EFI_variable_authentication( EFI_VAR_NAME_SetupMode,  EFI_VARIABLE_DICT[EFI_VAR_NAME_SetupMode]  )
    #sts |= check_EFI_variable_authentication( EFI_VAR_NAME_CustomMode, EFI_VARIABLE_DICT[EFI_VAR_NAME_CustomMode] )
    if (sts & ERROR) != 0: logger.log_important( "Some Secure Boot variables don't exist" )

    ok = ((sts & INSECURE) == 0)
    logger.log('')
    if ok: logger.log_passed_check( 'All existing Secure Boot EFI variables seem to be protected' )
    else:  logger.log_failed_check( 'One or more Secure Boot variables are not protected' )
    return ok


# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    #logger.VERBOSE = True
    logger.start_test( "Protection of Secure Boot Key and Configuraion EFI Variables" )
    if not (cs.helper.is_win8_or_greater() or cs.helper.is_linux()):
        logger.log_skipped_check( 'Currently this module can only run on Windows 8 or greater or Linux. Exiting..' )
        return ModuleResult.SKIPPED
    return check_secureboot_key_variables()
   

########NEW FILE########
__FILENAME__ = variables
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/secureboot/variables.py__ - verify that all EFI variables containing Secure Boot keys/databases are authenticated


from chipsec.module_common import *

from chipsec.file          import *
from chipsec.hal.uefi      import *

# ############################################################
# SPECIFY PLATFORMS THIS MODULE IS APPLICABLE TO
# ############################################################
_MODULE_NAME = 'variables'
AVAILABLE_MODULES[ CHIPSET_ID_COMMON ].append( _MODULE_NAME )
TAGS = [MTAG_SECUREBOOT]


logger = logger()
_uefi  = UEFI( cs.helper )


## check_secureboot_variable_attributes
# checks authentication attributes of Secure Boot EFI variables
def check_secureboot_variable_attributes( ):
    res = ModuleResult.PASSED
    error = False
    sbvars = _uefi.list_EFI_variables()
    if sbvars is None:
        logger.log_error_check( 'Could not enumerate UEFI Variables from runtime (Legacy OS?)' )
        logger.log_important( "Note that the Secure Boot UEFI variables may still exist, OS just did not expose runtime UEFI Variable API to read them. You can extract Secure Boot variables directly from ROM file via 'chipsec_util.py uefi nvram bios.bin' command and verify their attributes" )
        return ModuleResult.ERROR

    for name in SECURE_BOOT_KEY_VARIABLES:
        if name in sbvars.keys() and sbvars[name] is not None:
            if len(sbvars[name]) > 1:
                logger.log_failed_check( 'There should only one instance of Secure Boot variable %s exist' % name )
                return ModuleResult.FAILED
            for (off, buf, hdr, data, guid, attrs) in sbvars[name]:
                if   IS_VARIABLE_ATTRIBUTE( attrs, EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS ):
                    logger.log_good( 'Secure Boot variable %s is AUTHENTICATED_WRITE_ACCESS' % name )
                elif IS_VARIABLE_ATTRIBUTE( attrs, EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS ):
                    logger.log_good( 'Secure Boot variable %s is TIME_BASED_AUTHENTICATED_WRITE_ACCESS' % name )
                else:
                    res = ModuleResult.FAILED
                    logger.log_bad( 'Secure Boot variable %s is not authenticated' % name )
        else:
            logger.log_important('Secure Boot variable %s is not found!' % name )
            error = True

    if error: return ModuleResult.ERROR
    if   ModuleResult.PASSED == res: logger.log_passed_check( 'All Secure Boot EFI variables are authenticated' )
    elif ModuleResult.FAILED == res: logger.log_failed_check( 'Not all Secure Boot variables are authenticated' )
    return res


# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    logger.start_test( "Attributes of Secure Boot EFI Variables" )
    if not (cs.helper.is_win8_or_greater() or cs.helper.is_linux()):
        logger.log_skipped_check( 'Currently this module can only run on Windows 8 or higher or Linux. Exiting..' )
        return ModuleResult.SKIPPED
    return check_secureboot_variable_attributes()

########NEW FILE########
__FILENAME__ = smm
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/common/smm.py__ - common checks for protection of compatible System Management Mode (SMM) memory (SMRAM)
#

from chipsec.module_common import *

logger = logger()


# PCI Dev0 SMRAMC register
class SMRAMC( namedtuple('SMRAMC_REG', 'value D_OPEN D_CLS D_LCK G_SMRAME C_BASE_SEG') ):
      __slots__ = ()
      def __str__(self):
          return """
Compatible SMRAM Control (00:00.0 + 0x%X) = 0x%02X
[06]    D_OPEN     = %u (SMRAM Open)
[05]    D_CLS      = %u (SMRAM Closed)
[04]    D_LCK      = %u (SMRAM Locked)
[03]    G_SMRAME   = %u (SMRAM Enabled)
[02:00] C_BASE_SEG = %X (SMRAM Base Segment = 010b)
""" % ( PCI_SMRAMC_REG_OFF, self.value, self.D_OPEN, self.D_CLS, self.D_LCK, self.G_SMRAME, self.C_BASE_SEG )         


def check_SMRAMC():
    logger.start_test( "Compatible SMM memory (SMRAM) Protection" )

    regval = cs.pci.read_byte( 0, 0, 0, PCI_SMRAMC_REG_OFF )
    SMRAMRegister = SMRAMC( regval, (regval>>6)&0x1, (regval>>5)&0x1, (regval>>4)&0x3, (regval>>3)&0x1, regval&0x7 )
    logger.log( SMRAMRegister )

    res = ModuleResult.ERROR
    if 1 == SMRAMRegister.G_SMRAME:
        logger.log( "[*] Compatible SMRAM is enabled" )
        # When D_LCK is set HW clears D_OPEN so generally no need to check for D_OPEN but doesn't hurt double checking
        if 1 == SMRAMRegister.D_LCK and 0 == SMRAMRegister.D_OPEN:
            res = ModuleResult.PASSED
            logger.log_passed_check( "Compatible SMRAM is locked down" )
        else:
            res = ModuleResult.FAILED
            logger.log_failed_check( "Compatible SMRAM is not properly locked. Expected ( D_LCK = 1, D_OPEN = 0 )" )
    else:
        res = ModuleResult.SKIPPED
        logger.log( "[*] Compatible SMRAM is not enabled. Skipping.." )

    return res


# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
    return check_SMRAMC()

########NEW FILE########
__FILENAME__ = smrr
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup modules
# __chipsec/modules/common/smrr.py__ - checks for SMRR secure configuration to protect from SMRAM cache attack
#


from chipsec.module_common import *

from chipsec.hal.msr import *

logger = logger()

# ############################################################
# SPECIFY PLATFORMS THIS MODULE IS APPLICABLE TO
# ############################################################

#
# Check that SMRR are supported by CPU in IA32_MTRRCAP_MSR[SMRR]
#
def check_SMRR_supported():
    (eax, edx) = cs.msr.read_msr( 0, IA32_MTRRCAP_MSR )
    if logger.VERBOSE:
        logger.log( "[*] IA32_MTRRCAP_MSR = 0x%08X%08X" % (edx, eax) )
        logger.log( "    SMRR = %u" % ((eax&IA32_MTRRCAP_SMRR_MASK)>>11) )
    return (eax & IA32_MTRRCAP_SMRR_MASK)

def check_SMRR():
    logger.start_test( "CPU SMM Cache Poisoning / SMM Range Registers (SMRR)" )
    if check_SMRR_supported():
        logger.log_good( "OK. SMRR are supported in IA32_MTRRCAP_MSR" )
    else:
        logger.log_important( "CPU does not support SMRR protection of SMRAM" )
        logger.log_skipped_check("CPU does not support SMRR protection of SMRAM")
        return ModuleResult.SKIPPED

    #
    # SMRR are supported
    # 
    smrr_ok = True

    #
    # 2. Check SMRR_BASE is programmed correctly (on CPU0)
    #
    logger.log( '' )
    logger.log( "[*] Checking SMRR Base programming.." )
    (eax, edx) = cs.msr.read_msr( 0, IA32_SMRR_BASE_MSR )
    msr_smrrbase = ((edx << 32) | eax)
    smrrbase_msr = eax
    smrrbase = smrrbase_msr & IA32_SMRR_BASE_BASE_MASK
    logger.log( "[*] IA32_SMRR_BASE_MSR = 0x%08X%08X" % (edx, eax) )
    logger.log( "    BASE    = 0x%08X" % smrrbase )
    logger.log( "    MEMTYPE = %X"     % (smrrbase_msr&IA32_SMRR_BASE_MEMTYPE_MASK) )

    if ( 0 != smrrbase ):
        if ( MTRR_MEMTYPE_WB == smrrbase_msr & IA32_SMRR_BASE_MEMTYPE_MASK ): logger.log_good( "SMRR Memtype is WB" )
        else: logger.log_important( "SMRR Memtype (= %X) is not WB", (smrrbase_msr & IA32_SMRR_BASE_MEMTYPE_MASK) )
    else:
        smrr_ok = False
        logger.log_bad( "SMRR Base is not programmed" )

    if smrr_ok: logger.log_good( "OK so far. SMRR Base is programmed" )

    #
    # 3. Check SMRR_MASK is programmed and SMRR are enabled (on CPU0)
    #
    logger.log( '' )
    logger.log( "[*] Checking SMRR Mask programming.." )
    (eax, edx) = cs.msr.read_msr( 0, IA32_SMRR_MASK_MSR )
    msr_smrrmask = ((edx << 32) | eax)
    smrrmask_msr = eax
    logger.log( "[*] IA32_SMRR_MASK_MSR = 0x%08X%08X" % (edx, eax) )
    logger.log( "    MASK    = 0x%08X" % (smrrmask_msr&IA32_SMRR_MASK_MASK_MASK) )
    logger.log( "    VLD     = %u"     % ((smrrmask_msr&IA32_SMRR_MASK_VLD_MASK)>>11) )

    if not ( smrrmask_msr&IA32_SMRR_MASK_VLD_MASK and smrrmask_msr&IA32_SMRR_MASK_MASK_MASK ):
        smrr_ok = False
        logger.log_bad( "SMRR are not enabled in SMRR_MASK MSR" )

    if smrr_ok: logger.log_good( "OK so far. SMRR are enabled in SMRR_MASK MSR" )

    #
    # 4. Verify that SMRR_BASE/MASK MSRs have the same values on all logical CPUs
    #
    logger.log( '' )
    logger.log( "[*] Verifying that SMRR_BASE/MASK have the same values on all logical CPUs.." )
    for tid in range(cs.msr.get_cpu_thread_count()):
        (eax, edx) = cs.msr.read_msr( tid, IA32_SMRR_BASE_MSR )
        msr_base = ((edx << 32) | eax)
        (eax, edx) = cs.msr.read_msr( tid, IA32_SMRR_MASK_MSR )
        msr_mask = ((edx << 32) | eax)
        logger.log( "[CPU%d] SMRR_BASE = %016X, SMRR_MASK = %016X"% (tid, msr_base, msr_mask) )
        if (msr_base != msr_smrrbase) or (msr_mask != msr_smrrmask):
            smrr_ok = False
            logger.log_bad( "SMRR MSRs do not match on all CPUs" )
            break

    if smrr_ok: logger.log_good( "OK so far. SMRR MSRs match on all CPUs" )

    """
    Don't want invasive action in this test
    #
    # 5. Reading from & writing to SMRR_BASE physical address
    # writes should be dropped, reads should return all F's
    #
    logger.log( "[*] Trying to read/modify memory at SMRR_BASE address 0x%08X.." % smrrbase )
    smram_buf = cs.mem.read_physical_mem( smrrbase, 0x10 )
    #logger.log( "Contents at 0x%08X:\n%s" % (smrrbase, repr(smram_buf.raw)) )
    cs.mem.write_physical_mem_dword( smrrbase, 0x90909090 )
    if ( 0xFFFFFFFF == cs.mem.read_physical_mem_dword( smrrbase ) ):
        logger.log_good( "OK. Memory at SMRR_BASE contains all F's and is not modifiable" )
    else:
        smrr_ok = False
        logger.log_bad( "Contents of memory at SMRR_BASE are modifiable" )
    """


    logger.log( '' )
    if not smrr_ok: logger.log_failed_check( "SMRR protection against cache attack is not configured properly" )
    else:           logger.log_passed_check( "SMRR protection against cache attack seems properly configured" )

    return smrr_ok

# --------------------------------------------------------------------------
# run( module_argv )
# Required function: run here all tests from this module
# --------------------------------------------------------------------------
def run( module_argv ):
        return check_SMRR()
        

########NEW FILE########
__FILENAME__ = spi_lock
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#





## \addtogroup modules
# __chipsec/modules/common/spi_lock.py__  - Checks that the SPI Flash Controller configuration is locked
# if it is not locked other Flash Program Registers can be written
#
#
#

from chipsec.module_common import *

from chipsec.hal.spi import *

logger = logger()


def check_spi_lock():
    logger.start_test( "SPI Flash Controller Configuration Lock" )

    spi_locked = 0
    hsfsts_reg_value = cs.mem.read_physical_mem_dword( get_PCH_RCBA_SPI_base(cs) + SPI_HSFSTS_OFFSET )
    logger.log( '[*] HSFSTS register = 0x%08X' % hsfsts_reg_value )
    logger.log( '    FLOCKDN = %u' % ((hsfsts_reg_value & SPI_HSFSTS_FLOCKDN_MASK)>>15) )

    if 0 != (hsfsts_reg_value & SPI_HSFSTS_FLOCKDN_MASK):
        spi_locked = 1
        logger.log_passed_check( "SPI Flash Controller configuration is locked" )
    else:
        logger.log_failed_check( "SPI Flash Controller configuration is not locked" )

    return spi_locked==1

def run( module_argv ):
    return check_spi_lock()



########NEW FILE########
__FILENAME__ = module_common
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



# -------------------------------------------------------------------------------
#
# CHIPSEC: Platform Hardware Security Assessment Framework
# (c) 2010-2012 Intel Corporation
#
# -------------------------------------------------------------------------------


## \addtogroup core
# __chipsec/module_common.py__ -- common include file for modules
#
#

from chipsec.logger  import *
from chipsec.chipset import *

#
# Instace of Chipset class to be used by all modules
#
cs = cs()

def init ():
    #
    # Import platform configuration defines in the following order:
    # 1. chipsec.cfg.common (imported in chipsec.chipset)
    # 2. chipsec.cfg.<platform>
    #
    #from chipsec.cfg.common import *
    if cs.code and '' != cs.code:
        try:
            exec 'from chipsec.cfg.' + cs.code + ' import *'
            logger().log_good( "imported platform specific configuration: chipsec.cfg.%s" % cs.code )
        except ImportError, msg:
            if logger().VERBOSE: logger().log( "[*] Couldn't import chipsec.cfg.%s" % cs.code )


#
# Instace of Logger class to be used by all modules
#
#logger = logger()

AVAILABLE_MODULES = dict( [(Chipset_Dictionary[ _did ]['id'], []) for _did in Chipset_Dictionary] )
AVAILABLE_MODULES[ CHIPSET_ID_COMMON ] = []

DISABLED_MODULES = dict( [(Chipset_Dictionary[ _did ]['id'], []) for _did in Chipset_Dictionary] )
DISABLED_MODULES[ CHIPSET_ID_COMMON ] = []


MTAG_BIOS       = "BIOS"
MTAG_SMM        = "SMM"
MTAG_SECUREBOOT = "SECUREBOOT"
 


##! [Available Tags]
MTAG_METAS = {
              MTAG_BIOS:      "System firmware (BIOS/UEFI) specific tests", 
              MTAG_SMM:       "System Management Mode (SMM) specific tests",
              MTAG_SECUREBOOT: "Secure Boot specific tests",
              }
##! [Available Tags]
MODULE_TAGS = dict( [(_tag, []) for _tag in MTAG_METAS])

USER_MODULE_TAGS = []

class ModuleResult:
    FAILED  = 0
    PASSED  = 1
    WARNING = 2
    SKIPPED = 3
    ERROR   = -1


########NEW FILE########
__FILENAME__ = chipset_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone chipsec util
#  Chipsec Standalone utility\n
#
# chipsec_util platform
# -----------------------------
# ~~~
# chipsec_util platform 
# ~~~
#
#
#
#

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.chipset    import UnknownChipsetError, print_supported_chipsets
#_cs = cs()

usage = "chipsec_util platform\n\n"

chipsec_util.global_usage += usage


# ###################################################################
#
# Chipset/CPU Detection
#
# ###################################################################
def platform(argv):

    try:
        print_supported_chipsets()
        logger().log("")
        _cs.print_chipset()
    except UnknownChipsetError, msg:
        logger().error( msg )

chipsec_util_commands['platform'] = {'func' : platform, 'start_driver' : True  }


########NEW FILE########
__FILENAME__ = cmos_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#
#
#chipsec_util cmos
#------------------------
#~~~
#chipsec_util cmos dump\n
#chipsec_util cmos readl|writel|readh|writeh \<byte_offset\> [byte_val]
# ''
#    Examples:
#        chipsec_util cmos dump
#        chipsec_util cmos readh 0x0
#        chipsec_util cmos writeh 0x0 0xCC
# ~~~
#
#
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.cmos   import CMOS, CmosRuntimeError
#from chipsec.chipset    import cs
#_cs = cs()

usage = "chipsec_util cmos dump\n" + \
        "chipsec_util cmos readl|writel|readh|writeh <byte_offset> [byte_val]\n" + \
        "Examples:\n" + \
        "  chipsec_util cmos dump\n" + \
        "  chipsec_util cmos rl 0x0\n" + \
        "  chipsec_util cmos wh 0x0 0xCC\n\n"

chipsec_util.global_usage += usage


def cmos(argv):
    if 3 > len(argv):
      print usage
      return

    try:
       cmos = CMOS( _cs )
    except CmosRuntimeError, msg:
       print msg
       return

    op = argv[2]
    t = time.time()

    if ( 'dump' == op ):
       logger().log( "[CHIPSEC] Dumping CMOS memory.." )
       cmos.dump()
    elif ( 'readl' == op ):
       off = int(argv[3],16)
       val = cmos.read_cmos_low( off )
       logger().log( "[CHIPSEC] CMOS low byte 0x%X = 0x%X" % (off, val) )
    elif ( 'writel' == op ):
       off = int(argv[3],16)
       val = int(argv[4],16)
       logger().log( "[CHIPSEC] Writing CMOS low byte 0x%X <- 0x%X " % (off, val) )
       cmos.write_cmos_low( off, val )
    elif ( 'readh' == op ):
       off = int(argv[3],16)
       val = cmos.read_cmos_high( off )
       logger().log( "[CHIPSEC] CMOS high byte 0x%X = 0x%X" % (off, val) )
    elif ( 'writeh' == op ):
       off = int(argv[3],16)
       val = int(argv[4],16)
       logger().log( "[CHIPSEC] Writing CMOS high byte 0x%X <- 0x%X " % (off, val) )
       cmos.write_cmos_high( off, val )
    else:
       logger().error( "unknown command-line option '%.32s'" % op )
       print usage
       return

    logger().log( "[CHIPSEC] (cmos) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['cmos'] = {'func' : cmos,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = cpuid_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup standalone
#chipsec_util cpuid
#------
#~~~
#chipsec_util cpuid [eax]
#''
#    Examples:
#''
#         chipsec_util cpuid 40000000
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     	import *
from chipsec.file       	import *
#_cs = cs()

usage = "chipsec_util cpuid <eax> \n" + \
        "Examples:\n" + \
        "  chipsec_util cpuid 40000000\n\n"

chipsec_util.global_usage += usage



# ###################################################################
#
# CPUid
#
# ###################################################################
def cpuid(argv):

    if 3 > len(argv):
      print usage
      return

    eax = int(argv[2],16)

    if (3 == len(argv)):
		logger().log( "[CHIPSEC] CPUID in EAX=0x%x " % (eax))
		val = _cs.cpuid.cpuid(eax)
		logger().log( "[CHIPSEC] CPUID out EAX: 0x%x" % (val[0]) )
		logger().log( "[CHIPSEC] CPUID out EBX: 0x%x" % (val[1]) )
		logger().log( "[CHIPSEC] CPUID out ECX: 0x%x" % (val[2]) )
		logger().log( "[CHIPSEC] CPUID out EDX: 0x%x" % (val[3]) )


chipsec_util_commands['cpuid'] = {'func' : cpuid ,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = decode_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
# chipsec_util decode spi.bin
#
## \addtogroup standalone
#chipsec_util decode
#--------
#~~~
#chipsec_util decode <rom> [fw_type]
#''
#    Examples:
#''
#        chipsec_util decode spi.bin vss
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from  chipsec.logger import *
import  chipsec.file   

import chipsec.hal.spi            as spi
import chipsec.hal.spi_descriptor as spi_descriptor
import chipsec.hal.spi_uefi       as spi_uefi
import chipsec.hal.uefi           as uefi

#_cs = cs()
_uefi = uefi.UEFI( _cs.helper )


usage = "chipsec_util decode <rom> [fw_type]\n" + \
        "             <fw_type> should be in [ %s ]\n" % (" | ".join( ["%s" % t for t in uefi.fw_types])) + \
        "Examples:\n" + \
        "  chipsec_util decode spi.bin vss\n\n"

chipsec_util.global_usage += usage

def decode(argv):

    if 3 > len(argv):
        print usage
        return

    rom_file = argv[2]

    fwtype = ''
    if 4 == len(argv):
        fwtype = argv[3]

    logger().log( "[CHIPSEC] Decoding SPI ROM image from a file '%s'" % rom_file )
    t = time.time()

    f = chipsec.file.read_file( rom_file )
    (fd_off, fd) = spi_descriptor.get_spi_flash_descriptor( f )
    if (-1 == fd_off) or (fd is None):
        logger().error( "Could not find SPI Flash descriptor in the binary '%s'" % rom_file )
        return False

    logger().log( "[CHIPSEC] Found SPI Flash descriptor at offset 0x%x in the binary '%s'" % (fd_off, rom_file) )
    rom = f[fd_off:]
    # Decoding Flash Descriptor
    #logger().LOG_COMPLETE_FILE_NAME = os.path.join( pth, 'flash_descriptor.log' )
    #parse_spi_flash_descriptor( fd )

    # Decoding SPI Flash Regions
    # flregs[r] = (r,SPI_REGION_NAMES[r],flreg,base,limit,notused)
    flregs = spi_descriptor.get_spi_regions( fd )
    if flregs is None:
        logger().error( "SPI Flash descriptor region is not valid" )
        return False

    _orig_logname = logger().LOG_FILE_NAME

    pth = os.path.join( _cs.helper.getcwd(), rom_file + ".dir" )
    if not os.path.exists( pth ):
        os.makedirs( pth )

    for r in flregs:
        idx     = r[0]
        name    = r[1]
        base    = r[3]
        limit   = r[4]
        notused = r[5]
        if not notused:
            region_data = rom[base:limit+1]
            fname = os.path.join( pth, '%d_%04X-%04X_%s.bin' % (idx, base, limit, name) )
            chipsec.file.write_file( fname, region_data )
            if spi.FLASH_DESCRIPTOR == idx:
                # Decoding Flash Descriptor
                logger().set_log_file( os.path.join( pth, fname + '.log' ) )
                spi_descriptor.parse_spi_flash_descriptor( region_data )
            elif spi.BIOS == idx:
                # Decoding EFI Firmware Volumes
                logger().set_log_file( os.path.join( pth, fname + '.log' ) )
                spi_uefi.decode_uefi_region(_uefi, pth, fname, fwtype)

    logger().set_log_file( _orig_logname )
    logger().log( "[CHIPSEC] (decode) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['decode'] = {'func' : decode,     'start_driver' : False  }


########NEW FILE########
__FILENAME__ = desc_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
#
## \addtogroup standalone
#chipsec_util idt / chipsec_util gdt / chipsec_util ldt
#---------
#~~~
#chipsec_util idt|gdt [cpu_id]
#''
#    Examples:
#''
#        chipsec_util idt 0
#        chipsec_util gdt
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

#from chipsec.hal.msr        import Msr
#_cs = cs()

usage = "chipsec_util idt|gdt|ldt [cpu_id]\n" + \
        "Examples:\n" + \
        "  chipsec_util idt 0\n" + \
        "  chipsec_util gdt\n\n"

chipsec_util.global_usage += usage


# ###################################################################
#
# CPU descriptor tables
#
# ###################################################################
def idt(argv):
    if (2 == len(argv)):
       logger().log( "[CHIPSEC] Dumping IDT of %d CPU threads" % _cs.msr.get_cpu_thread_count() )
       _cs.msr.IDT_all( 4 )
    elif (3 == len(argv)):
       tid = int(argv[2],16)
       _cs.msr.IDT( tid, 4 )
   
def gdt(argv):
    if (2 == len(argv)):
       logger().log( "[CHIPSEC] Dumping GDT of %d CPU threads" % _cs.msr.get_cpu_thread_count() )
       _cs.msr.GDT_all( 4 )
    elif (3 == len(argv)):
       tid = int(argv[2],16)
       _cs.msr.GDT( tid, 4 )

def ldt(argv):
    logger().error( "[CHIPSEC] ldt not implemented" )


chipsec_util_commands['idt'] = {'func' : idt,     'start_driver' : True  }
chipsec_util_commands['gdt'] = {'func' : gdt,     'start_driver' : True  }

########NEW FILE########
__FILENAME__ = interrupts_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util smi / chipsec_util nmi
#-----------
#~~~
#chipsec_util smi <SMI_code> <SMI_data> [RAX] [RBX] [RCX] [RDX] [RSI] [RDI]
#chipsec_util nmi
#''
#    Examples:
#''
#        chipsec_util smi 0xDE 0x0
#        chipsec_util nmi
#~~~
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.interrupts import Interrupts

#_cs = cs()

usage = "chipsec_util smi <SMI_code> <SMI_data> [RAX] [RBX] [RCX] [RDX] [RSI] [RDI]\n\n" + \
        "chipsec_util nmi\n" + \
        "Examples:\n" + \
        "  chipsec_util smi 0xDE 0x0\n" + \
        "  chipsec_util nmi\n\n"

chipsec_util.global_usage += usage


# ###################################################################
#
# CPU Interrupts
#
# ###################################################################
def smi(argv):
    try:
       interrupts = Interrupts( _cs )
    except RuntimeError, msg:
       print msg
       return

    SMI_code_port_value = 0xF
    SMI_data_port_value = 0x0
    if (2 == len(argv)):
       pass
    elif (3 < len(argv)):
       SMI_code_port_value = int(argv[2],16)
       SMI_data_port_value = int(argv[3],16)
       logger().log( "[CHIPSEC] Sending SW SMI (code: 0x%02X, data: 0x%02X).." % (SMI_code_port_value, SMI_data_port_value) )
       if (4 == len(argv)):
           interrupts.send_SMI_APMC( SMI_code_port_value, SMI_data_port_value )
       elif (10 == len(argv)):
           _rax = int(argv[4],16)
           _rbx = int(argv[5],16)
           _rcx = int(argv[6],16)
           _rdx = int(argv[7],16)
           _rsi = int(argv[8],16)
           _rdi = int(argv[9],16)
           logger().log( "          RAX: 0x%016X (AX will be overwridden with values of SW SMI ports B2/B3)" % _rax )
           logger().log( "          RBX: 0x%016X" % _rbx )
           logger().log( "          RCX: 0x%016X" % _rcx )
           logger().log( "          RDX: 0x%016X (DX will be overwridden with 0x00B2)" % _rdx )
           logger().log( "          RSI: 0x%016X" % _rsi )
           logger().log( "          RDI: 0x%016X" % _rdi )
           interrupts.send_SW_SMI( SMI_code_port_value, SMI_data_port_value, _rax, _rbx, _rcx, _rdx, _rsi, _rdi )
       else: print usage
    else: print usage


def nmi(argv):
    if 2 < len(argv):
       print usage

    try:
       interrupts = Interrupts( _cs )
    except RuntimeError, msg:
       print msg
       return

    logger().log( "[CHIPSEC] Sending NMI#.." )
    interrupts.send_NMI()


chipsec_util_commands['nmi'] = {'func' : nmi,     'start_driver' : True  }
chipsec_util_commands['smi'] = {'func' : smi,     'start_driver' : True  }


########NEW FILE########
__FILENAME__ = io_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util io
#----
#~~~
#chipsec_util io <ioport> <width> [value]
#''
#    Examples:
#''
#        chipsec_util io 0x61 1
#        chipsec_util io 0x430 byte 0x0
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

#_cs = cs()

usage = "chipsec_util io <io_port> <width> [value]\n" + \
        "Examples:\n" + \
        "  chipsec_util io 0x61 1\n" + \
        "  chipsec_util io 0x430 byte 0x0\n\n"

chipsec_util.global_usage += usage

# ###################################################################
#
# Port I/O
#
# ###################################################################
def port_io(argv):

    if 3 > len(argv):
      print usage
      return

    try:
       io_port = int(argv[2],16)

       if 3 == len(argv):
          width = 1
       else:
          if 'byte' == argv[3]:
             width = 1
          elif 'word' == argv[3]:
             width = 2
          elif 'dword' == argv[3]:
             width = 4
          else:
             width = int(argv[3])
    except:
       print usage
       return

    if 5 == len(argv):
       value = int(argv[4], 16)
       logger().log( "[CHIPSEC] OUT 0x%04X <- 0x%08X (size = 0x%02x)" % (io_port, value, width) )
       if 1 == width:
          _cs.io.write_port_byte( io_port, value )
       elif 2 == width:
          _cs.io.write_port_word( io_port, value )
       elif 4 == width:
          _cs.io.write_port_dword( io_port, value )
       else:
          print "ERROR: Unsupported width 0x%x" % width
          return
    else:
       if 1 == width:
          value = _cs.io.read_port_byte( io_port )
       elif 2 == width:
          value = _cs.io.read_port_word( io_port )
       elif 4 == width:
          value = _cs.io.read_port_dword( io_port )
       else:
          print "ERROR: Unsupported width 0x%x" % width
          return
       logger().log( "[CHIPSEC] IN 0x%04X -> 0x%08X (size = 0x%02x)" % (io_port, value, width) )

chipsec_util_commands['io'] = {'func' : port_io, 'start_driver' : True  }


########NEW FILE########
__FILENAME__ = mem_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util mem
#-------
#~~~
#chipsec_util mem <phys_addr_hi> <phys_addr_lo> <length> [value]
#''
#    Examples:
#''
#        chipsec_util mem 0x0 0x41E 0x20
#        chipsec_util mem 0x0 0xA0000 4 0x9090CCCC
#        chipsec_util mem 0x0 0xFED40000 0x4
#~~~
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

#from chipsec.hal.physmem    import Memory

#_cs = cs()

usage = "chipsec_util mem <phys_addr_hi> <phys_addr_lo> <length> [value]\n" + \
        "Examples:\n" + \
        "  chipsec_util mem 0x0 0x41E 0x20\n" + \
        "  chipsec_util mem 0x0 0xA0000 4 0x9090CCCC\n" + \
        "  chipsec_util mem 0x0 0xFED40000 0x4\n\n"

chipsec_util.global_usage += usage



# ###################################################################
#
# Physical Memory
#
# ###################################################################
def mem(argv):
    phys_address_hi = 0
    phys_address_lo = 0
    phys_address    = 0
    size = 0x100

    if 4 > len(argv):
      print usage
      return
    else:
       phys_address_hi = int(argv[2],16)
       phys_address_lo = int(argv[3],16)
       phys_address = ((phys_address_hi<<32) | phys_address_lo)

    if 6 == len(argv):
       value = int(argv[5],16)
       logger().log( '[CHIPSEC] Writing: PA = 0x%016X <- 0x%08X' % (phys_address, value) )
       _cs.mem.write_physical_mem_dword( phys_address, value )
    else:
       if 5 == len(argv):
          size = int(argv[4],16)
       out_buf = _cs.mem.read_physical_mem( phys_address, size )
       logger().log( '[CHIPSEC] Reading: PA = 0x%016X, len = 0x%X, output:' % (phys_address, len(out_buf)) )
       print_buffer( out_buf )

chipsec_util_commands['mem'] = {'func' : mem,     'start_driver' : True  }


########NEW FILE########
__FILENAME__ = mmcfg_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util mmcfg
#------
#~~~
#chipsec_util mmcfg
#chipsec_util mmcfg <bus> <device> <function> <offset> <width> [value]
#''
#    Examples:
#''
#        chipsec_util mmcfg
#        chipsec_util mmcfg 0 0 0 0x88 4
#        chipsec_util mmcfg 0 0 0 0x88 byte 0x1A
#        chipsec_util mmcfg 0 0x1F 0 0xDC 1 0x1
#        chipsec_util mmcfg 0 0 0 0x98 dword 0x004E0040
#~~~


__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.mmio   import *

#_cs = cs()

usage = "chipsec_util mmcfg <bus> <device> <function> <offset> <width> [value]\n" + \
        "Examples:\n" + \
        "  chipsec_util mmcfg 0 0 0 0x88 4\n" + \
        "  chipsec_util mmcfg 0 0 0 0x88 byte 0x1A\n" + \
        "  chipsec_util mmcfg 0 0x1F 0 0xDC 1 0x1\n" + \
        "  chipsec_util mmcfg 0 0 0 0x98 dword 0x004E0040\n\n"

chipsec_util.global_usage += usage



# ###################################################################
#
# Access to Memory Mapped PCIe Configuration Space (MMCFG)
#
# ###################################################################
def mmcfg(argv):

    t = time.time()

    if 2 == len(argv):
        pciexbar = get_PCIEXBAR_base_address( _cs )
        logger().log( "[CHIPSEC] Memory Mapped Configuration Space (PCIEXBAR) = 0x%016X" % pciexbar )
        return
    elif 6 > len(argv):
        print usage
        return

    try:
       bus         = int(argv[2],16)
       device      = int(argv[3],16)
       function    = int(argv[4],16)
       offset      = int(argv[5],16)

       if 6 == len(argv):
          width = 1
       else:
          if 'byte' == argv[6]:
             width = 1
          elif 'word' == argv[6]:
             width = 2
          elif 'dword' == argv[6]:
             width = 4
          else:
             width = int(argv[6])

    except Exception as e :
       print usage
       return

    if 8 == len(argv):
       value = int(argv[7], 16)
       write_mmcfg_reg( _cs, bus, device, function, offset, width, value )
       #_cs.pci.write_mmcfg_reg( bus, device, function, offset, width, value )
       logger().log( "[CHIPSEC] writing MMCFG register (%d/%d/%d + 0x%02X): 0x%X" % (bus, device, function, offset, value) )
    else:
       value = read_mmcfg_reg( _cs, bus, device, function, offset, width )
       #value = _cs.pci.read_mmcfg_reg( bus, device, function, offset, width )
       logger().log( "[CHIPSEC] reading MMCFG register (%d/%d/%d + 0x%02X): 0x%X" % (bus, device, function, offset, value) )

    logger().log( "[CHIPSEC] (mmcfg) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['mmcfg'] = {'func' : mmcfg ,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = msr_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util msr
#-----
#~~~
#chipsec_util msr <msr> [eax] [edx] [cpu_id]
#''
#    Examples:
#''
#        chipsec_util msr 0x3A
#        chipsec_util msr 0x8B 0x0 0x0 0
#~~~
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.msr    import Msr

#_cs = cs()

usage = "chipsec_util msr <msr> [eax] [edx] [cpu_id]\n" + \
        "Examples:\n" + \
        "  chipsec_util msr 0x3A\n" + \
        "  chipsec_util msr 0x8B 0x0 0x0 0\n\n"

chipsec_util.global_usage += usage



# ###################################################################
#
# CPU Model Specific Registers
#
# ###################################################################
def msr(argv):

    if 3 > len(argv):
      print usage
      return

    #msr = Msr( os_helper )
    msr_addr = int(argv[2],16)

    if (3 == len(argv)):
       for tid in range(_cs.msr.get_cpu_thread_count()):
           (eax, edx) = _cs.msr.read_msr( tid, msr_addr )
           val64 = ((edx << 32) | eax)
           logger().log( "[CHIPSEC] CPU%d: RDMSR( 0x%x ) = %016X (EAX=%08X, EDX=%08X)" % (tid, msr_addr, val64, eax, edx) )
    elif (4 == len(argv)):
       cpu_thread_id = int(argv[3], 16)
       (eax, edx) = _cs.msr.read_msr( cpu_thread_id, msr_addr )
       val64 = ((edx << 32) | eax)
       logger().log( "[CHIPSEC] CPU%d: RDMSR( 0x%x ) = %016X (EAX=%08X, EDX=%08X)" % (cpu_thread_id, msr_addr, val64, eax, edx) )
    else:
       eax = int(argv[3], 16)
       edx = int(argv[4], 16)
       val64 = ((edx << 32) | eax)
       if (5 == len(argv)):
          logger().log( "[CHIPSEC] All CPUs: WRMSR( 0x%x ) = %016X" % (msr_addr, val64) )
          for tid in range(_cs.msr.get_cpu_thread_count()):
              _cs.msr.write_msr( tid, msr_addr, eax, edx )
       elif (6 == len(argv)):
          cpu_thread_id = int(argv[5], 16)
          logger().log( "[CHIPSEC] CPU%d: WRMSR( 0x%x ) = %016X" % (cpu_thread_id, msr_addr, val64) )
          _cs.msr.write_msr( cpu_thread_id, msr_addr, eax, edx )

chipsec_util_commands['msr'] = {'func' : msr ,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = pci_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util pci
#-----
#~~~
#chipsec_util pci enumerate
#chipsec_util pci <bus> <device> <function> <offset> <width> [value]
#''
#    Examples:
#''
#        chipsec_util pci enumerate
#        chipsec_util pci 0 0 0 0x88 4
#        chipsec_util pci 0 0 0 0x88 byte 0x1A
#        chipsec_util pci 0 0x1F 0 0xDC 1 0x1
#        chipsec_util pci 0 0 0 0x98 dword 0x004E0040
#~~~
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.pci    import *

#_cs = cs()

usage = "chipsec_util pci enumerate\n" + \
        "chipsec_util pci <bus> <device> <function> <offset> <width> [value]\n" + \
        "Examples:\n" + \
        "  chipsec_util pci enumerate\n" + \
        "  chipsec_util pci 0 0 0 0x88 4\n" + \
        "  chipsec_util pci 0 0 0 0x88 byte 0x1A\n" + \
        "  chipsec_util pci 0 0x1F 0 0xDC 1 0x1\n" + \
        "  chipsec_util pci 0 0 0 0x98 dword 0x004E0040\n\n"

chipsec_util.global_usage += usage



# ###################################################################
#
# PCIe Devices and Configuration Registers
#
# ###################################################################
def pci(argv):

    if 3 > len(argv):
      print usage
      return

    op = argv[2]
    t = time.time()

    if ( 'enumerate' == op ):
       logger().log( "[CHIPSEC] Enumerating available PCIe devices.." )
       print_pci_devices( _cs.pci.enumerate_devices() )
       logger().log( "[CHIPSEC] (pci) time elapsed %.3f" % (time.time()-t) )
       return

    try:
       bus         = int(argv[2],16)
       device      = int(argv[3],16)
       function    = int(argv[4],16)
       offset      = int(argv[5],16)

       if 6 == len(argv):
          width = 1
       else:
          if 'byte' == argv[6]:
             width = 1
          elif 'word' == argv[6]:
             width = 2
          elif 'dword' == argv[6]:
             width = 4
          else:
             width = int(argv[6])
    except Exception as e :
       print usage
       return

    if 8 == len(argv):
       value = int(argv[7], 16)
       if 1 == width:
          _cs.pci.write_byte( bus, device, function, offset, value )
       elif 2 == width:
          _cs.pci.write_word( bus, device, function, offset, value )
       elif 4 == width:
          _cs.pci.write_dword( bus, device, function, offset, value )
       else:
          print "ERROR: Unsupported width 0x%x" % width
          return
       logger().log( "[CHIPSEC] writing PCI %d/%d/%d, off 0x%02X: 0x%X" % (bus, device, function, offset, value) )
    else:
       if 1 == width:
          pci_value = _cs.pci.read_byte(bus, device, function, offset)
       elif 2 == width:
          pci_value = _cs.pci.read_word(bus, device, function, offset)
       elif 4 == width:
          pci_value = _cs.pci.read_dword(bus, device, function, offset)
       else:
          print "ERROR: Unsupported width 0x%x" % width
          return
       logger().log( "[CHIPSEC] reading PCI B/D/F %d/%d/%d, off 0x%02X: 0x%X" % (bus, device, function, offset, pci_value) )

    logger().log( "[CHIPSEC] (pci) time elapsed %.3f" % (time.time()-t) )

chipsec_util_commands['pci'] = {'func' : pci ,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = smbus_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#
#
#chipsec_util cmos
#------------------------
#~~~
#chipsec_util smbus read \<device_addr\> \<start_offset\> [size]
#chipsec_util smbus write \<device_addr\> \<offset\> \<byte_val\>
# ''
#    Examples:
#        chipsec_util smbus read  0xA0 0x0 0x100
# ~~~
#
#
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
#from chipsec_util import global_usage, chipsec_util_commands, _cs
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.smbus   import *
#from chipsec.chipset    import cs
#_cs = cs()

usage = "chipsec_util smbus read <device_addr> <start_offset> [size]\n" + \
        "chipsec_util smbus write <device_addr> <offset> <byte_val>\n" + \
        "Examples:\n" + \
        "  chipsec_util smbus read  0xA0 0x0 0x100\n\n"

chipsec_util.global_usage += usage


def smbus(argv):
    if 3 > len(argv):
      print usage
      return

    try:
       smbus = SMBus( _cs )
    except SMBusRuntimeError, msg:
       print msg
       return

    op = argv[2]
    t = time.time()

    if not smbus.is_SMBus_supported():
        logger().log( "[CHIPSEC] SMBus controller is not supported" )
        return

    smbus.display_SMBus_info()

    if ( 'read' == op ):
       dev_addr  = int(argv[3],16)
       start_off = int(argv[4],16)
       if len(argv) > 5:
           size   = int(argv[5],16)
           buf = smbus.read_range( dev_addr, start_off, size )
           logger().log( "[CHIPSEC] SMBus read: device 0x%X offset 0x%X size 0x%X" % (dev_addr, start_off, size) )
           print_buffer( buf )
       else:
           val = smbus.read_byte( dev_addr, start_off )
           logger().log( "[CHIPSEC] SMBus read: device 0x%X offset 0x%X = 0x%X" % (dev_addr, start_off, val) )
    elif ( 'write' == op ):
       dev_addr = int(argv[3],16)
       off      = int(argv[4],16)
       val      = int(argv[5],16)
       logger().log( "[CHIPSEC] SMBus write: device 0x%X offset 0x%X = 0x%X" % (dev_addr, off, val) )
       smbus.write_byte( dev_addr, off, val )
    else:
       logger().error( "unknown command-line option '%.32s'" % op )
       print usage
       return

    logger().log( "[CHIPSEC] (smbus) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['smbus'] = {'func' : smbus,    'start_driver' : True  }


########NEW FILE########
__FILENAME__ = spidesc_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util spidesc
#--------
#~~~
#chipsec_util spidesc [rom]
#''
#    Examples:
#''
#        chipsec_util spidesc spi.bin
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.spi_descriptor import *

usage = "chipsec_util spidesc [rom]\n" + \
        "Examples:\n" + \
        "  chipsec_util spidesc spi.bin\n\n"

chipsec_util.global_usage += usage

def spidesc(argv):

    if 3 > len(argv):
      print usage
      return

    fd_file = argv[2]
    logger().log( "[CHIPSEC] Parsing SPI Flash Descriptor from file '%s'\n" % fd_file )

    t = time.time()
    fd = read_file( fd_file )
    if type(fd) == str: parse_spi_flash_descriptor( fd )
    logger().log( "\n[CHIPSEC] (spidesc) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['spidesc'] = {'func' : spidesc,     'start_driver' : False  }


########NEW FILE########
__FILENAME__ = spi_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#
#chipsec_util spi
#-----
#~~~
#chipsec_util spi info|dump|read|write|erase [flash_address] [length] [file]
#''
#    Examples:
#''
#        chipsec_util spi info
#        chipsec_util spi dump rom.bin
#        chipsec_util spi read 0x700000 0x100000 bios.bin
#        chipsec_util spi write 0x0 flash_descriptor.bin\n
#~~~

__version__ = '1.0'


import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.spi    import *

#_cs = cs()

usage = "chipsec_util spi info|dump|read|write|erase [flash_address] [length] [file]\n" + \
        "Examples:\n" + \
        "  chipsec_util spi info\n" + \
        "  chipsec_util spi dump rom.bin\n" + \
        "  chipsec_util spi read 0x700000 0x100000 bios.bin\n" + \
        "  chipsec_util spi write 0x0 flash_descriptor.bin\n\n"

chipsec_util.global_usage += usage

# ###################################################################
#
# SPI Flash Controller
#
# ###################################################################

def spi(argv):

    if 3 > len(argv):
      print usage
      return

    try:
       spi = SPI( _cs )
    except SpiRuntimeError, msg:
       print msg
       return

    spi_op = argv[2]

    t = time.time()

    if ( 'erase' == spi_op ):
       spi_fla = int(argv[3],16)
       logger().log( "[CHIPSEC] Erasing SPI Flash block at FLA = 0x%X" % spi_fla )

       #
       # This write protection only matters for BIOS range in SPI
       # Continue if FLA being written is not within BIOS range 
       # @TODO: do smth smarter here
       #
       if not spi.disable_BIOS_write_protection():
          logger().error( "Could not disable SPI Flash protection. Still trying.." )

       ok = spi.erase_spi_block( spi_fla )
       if ok: logger().log_result( "SPI Flash erase done" )
       else:  logger().warn( "SPI Flash erase returned error (turn on VERBOSE)" )
    elif ( 'write' == spi_op and 5 == len(argv) ):
       spi_fla = int(argv[3],16)
       filename = argv[4]
       logger().log( "[CHIPSEC] Writing to SPI Flash at FLA = 0x%X from '%.64s'" % (spi_fla, filename) )
       #
       # This write protection only matters for BIOS range in SPI
       # Continue if FLA being written is not within BIOS range 
       # @TODO: do smth smarter here
       #
       if not spi.disable_BIOS_write_protection():
          logger().error( "Could not disable SPI Flash protection. Still trying.." )

       ok = spi.write_spi_from_file( spi_fla, filename )
       if ok: logger().log_result( "SPI Flash write done" )
       else:  logger().warn( "SPI Flash write returned error (turn on VERBOSE)" )
    elif ( 'read' == spi_op ):
       spi_fla = int(argv[3],16)
       length = int(argv[4],16)
       logger().log( "[CHIPSEC] Reading 0x%x bytes from SPI Flash starting at FLA = 0x%X" % (length, spi_fla) )
       out_file = None
       if 6 == len(argv):
          out_file = argv[5]
       buf = spi.read_spi_to_file( spi_fla, length, out_file )
       if (buf is None):
          logger().error( "SPI Flash read didn't return any data (turn on VERBOSE)" )
       else:
          logger().log_result( "SPI Flash read done" )
    elif ( 'info' == spi_op ):
       logger().log( "[CHIPSEC] SPI Flash Info\n" )
       ok = spi.display_SPI_map()
    elif ( 'dump' == spi_op ):
       out_file = 'rom.bin'
       if 4 == len(argv):
          out_file = argv[3]
       logger().log( "[CHIPSEC] Dumping entire SPI Flash to '%s'" % out_file )
       # @TODO: don't assume SPI Flash always ends with BIOS region
       (base,limit,freg) = spi.get_SPI_region( BIOS )
       spi_size = limit + 1
       logger().log( "[CHIPSEC] BIOS Region: Base = 0x%08X, Limit = 0x%08X" % (base,limit) )
       logger().log( "[CHIPSEC] Dumping 0x%08X bytes (to the end of BIOS region)" % spi_size )
       buf = spi.read_spi_to_file( 0, spi_size, out_file )
       if (buf is None):
          logger().error( "Dumping SPI Flash didn't return any data (turn on VERBOSE)" )
       else:
          logger().log_result( "Done dumping SPI Flash" ) 
    else:
       print usage
       return

    logger().log( "[CHIPSEC] (spi %s) time elapsed %.3f" % (spi_op, time.time()-t) )



chipsec_util_commands['spi'] = {'func' : spi,     'start_driver' : True  }


########NEW FILE########
__FILENAME__ = ucode_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
# usage as a standalone utility:
#
## \addtogroup standalone
#chipsec_util ucode
#------
#~~~
#chipsec_util ucode id|load|decode [ucode_update_file (in .PDB or .BIN format)] [cpu_id]
#''
#    Examples:
#''
#        chipsec_util ucode id
#        chipsec_util ucode load ucode.bin 0
#        chipsec_util ucode decode ucode.pdb
#~~~

__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.ucode  import Ucode, dump_ucode_update_header

#_cs = cs()


usage = "chipsec_util ucode id|load|decode [ucode_update_file (in .PDB or .BIN format)] [cpu_id]\n" + \
        "Examples:\n" + \
        "  chipsec_util ucode id\n" + \
        "  chipsec_util ucode load ucode.bin 0\n" + \
        "  chipsec_util ucode decode ucode.pdb\n\n"

chipsec_util.global_usage += usage


# ###################################################################
#
# Microcode patches
#
# ###################################################################
def ucode(argv):

    if 3 > len(argv):
      print usage
      return

    ucode_op = argv[2]
    t = time.time()

    if ( 'load' == ucode_op ):
       if (4 == len(argv)):
          ucode_filename = argv[3]
          logger().log( "[CHIPSEC] Loading Microcode update on all cores from '%.64s'" % ucode_filename )
          _cs.ucode.update_ucode_all_cpus( ucode_filename )
       elif (5 == len(argv)):
          ucode_filename = argv[3]
          cpu_thread_id = int(argv[4],16)
          logger().log( "[CHIPSEC] Loading Microcode update on CPU%d from '%.64s'" % (cpu_thread_id, ucode_filename) )
          _cs.ucode.update_ucode( cpu_thread_id, ucode_filename )
       else:
          print usage
          return
    elif ( 'decode' == ucode_op ):
       if (4 == len(argv)):
          ucode_filename = argv[3]
          if (not ucode_filename.endswith('.pdb')):
             logger().log( "[CHIPSEC] Ucode update file is not PDB file: '%.256s'" % ucode_filename )
             return
          pdb_ucode_buffer = read_file( ucode_filename )
          logger().log( "[CHIPSEC] Decoding Microcode Update header of PDB file: '%.256s'" % ucode_filename )
          dump_ucode_update_header( pdb_ucode_buffer )
    elif ( 'id' == ucode_op ):
       if (3 == len(argv)):
          for tid in range(_cs.msr.get_cpu_thread_count()):
             ucode_update_id = _cs.ucode.ucode_update_id( tid )
             logger().log( "[CHIPSEC] CPU%d: Microcode update ID = 0x%08X" % (tid, ucode_update_id) )
       elif (4 == len(argv)):
          cpu_thread_id = int(argv[3],16)
          ucode_update_id = _cs.ucode.ucode_update_id( cpu_thread_id )
          logger().log( "[CHIPSEC] CPU%d: Microcode update ID = 0x%08X" % (cpu_thread_id, ucode_update_id) )
    else:
       logger().error( "unknown command-line option '%.32s'" % ucode_op )
       print usage
       return

    logger().log( "[CHIPSEC] (ucode) time elapsed %.3f" % (time.time()-t) )



chipsec_util_commands['ucode'] = {'func' : ucode,   'start_driver' : True  }


########NEW FILE########
__FILENAME__ = uefi_cmd
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




## \addtogroup standalone
#chipsec_util uefi
#------
#~~~
#chipsec_util uefi var-list [output_file] [infcls]
#chipsec_util uefi var-read|var-write|var-delete <name> <GUID> <efi_variable_file>
#chipsec_util uefi nvram[-auth] <fw_type> [rom_file]
#chipsec_util uefi keys <keyvar_file>
#''
#    Examples:
#''
#        chipsec_util uefi var-list nvram.bin
#        chipsec_util uefi var-read db D719B2CB-3D3A-4596-A3BC-DAD00E67656F db.bin
#        chipsec_util uefi var-write db D719B2CB-3D3A-4596-A3BC-DAD00E67656F db.bin
#        chipsec_util uefi var-delete db D719B2CB-3D3A-4596-A3BC-DAD00E67656F
#        chipsec_util uefi nvram fwtype bios.rom
#        chipsec_util uefi nvram-auth fwtype bios.rom
#        chipsec_util uefi decode uefi.bin fwtype
#        chipsec_util uefi keys db.bin
#~~~
__version__ = '1.0'

import os
import sys
import time

import chipsec_util
from chipsec_util import chipsec_util_commands, _cs

from chipsec.logger     import *
from chipsec.file       import *

from chipsec.hal.uefi          import *
from chipsec.hal.spi_uefi      import *
#from chipsec.hal.uefi_platform import fw_types

#_cs  = cs()
_uefi = UEFI( _cs.helper )


usage = "chipsec_util uefi var-list\n" + \
        "chipsec_util uefi var-read|var-write|var-delete <name> <GUID> <efi_variable_file>\n" + \
        "chipsec_util uefi nvram[-auth] <fw_type> [rom_file]\n" + \
        "                  <fw_type> should be in [ %s ]\n" % (" | ".join( ["%s" % t for t in fw_types])) + \
        "chipsec_util uefi keys <keyvar_file>\n" + \
        "                  <keyvar_file> should be one of the following EFI variables\n" + \
        "                  [ %s ]\n" % (" | ".join( ["%s" % var for var in SECURE_BOOT_VARIABLES])) + \
        "Examples:\n" + \
        "  chipsec_util uefi var-list\n" + \
        "  chipsec_util uefi var-read db D719B2CB-3D3A-4596-A3BC-DAD00E67656F db.bin\n" + \
        "  chipsec_util uefi var-write db D719B2CB-3D3A-4596-A3BC-DAD00E67656F db.bin\n" + \
        "  chipsec_util uefi var-delete db D719B2CB-3D3A-4596-A3BC-DAD00E67656F\n" + \
        "  chipsec_util uefi nvram fwtype bios.rom\n" + \
        "  chipsec_util uefi nvram-auth fwtype bios.rom\n" + \
        "  chipsec_util uefi decode uefi.bin fwtype\n" + \
        "  chipsec_util uefi keys db.bin\n\n"

chipsec_util.global_usage += usage


# ###################################################################
#
# Unified Extensible Firmware Interface (UEFI)
#
# ###################################################################
def uefi(argv):

    if 3 > len(argv):
      print usage
      return

    op = argv[2]
    t = time.time()

    filename = None
    if ( 'var-read' == op ):

      if (4 < len(argv)):
         name = argv[3]
         guid = argv[4]
      if (5 < len(argv)):
         filename = argv[5]
      logger().log( "[CHIPSEC] Reading EFI variable Name='%s' GUID={%s} from '%s' via Variable API.." % (name, guid, filename) )
      var = _uefi.get_EFI_variable( name, guid, filename )

    elif ( 'var-write' == op ):

      if (5 < len(argv)):
         name = argv[3]
         guid = argv[4]
         filename = argv[5]
      else:
         print usage
         return
      logger().log( "[CHIPSEC] Writing EFI variable Name='%s' GUID={%s} from '%s' via Variable API.." % (name, guid, filename) )
      status = _uefi.set_EFI_variable_from_file( name, guid, filename )
      if status:
          logger().log( "[CHIPSEC] set_EFI_variable return SUCCESS status" )
      else:
          logger().error( "set_EFI_variable wasn't able to modify variable" )

    elif ( 'var-delete' == op ):

      if (4 < len(argv)):
         name = argv[3]
         guid = argv[4]
      else:
         print usage
         return
      logger().log( "[CHIPSEC] Deleting EFI variable Name='%s' GUID={%s} via Variable API.." % (name, guid) )
      status = _uefi.delete_EFI_variable( name, guid )
      if status: logger().log( "[CHIPSEC] delete_EFI_variable return SUCCESS status" )
      else:      logger().error( "delete_EFI_variable wasn't able to delete variable" )

    elif ( 'var-list' == op ):

      #infcls = 2
      #if (3 < len(argv)): filename = argv[3]
      #if (4 < len(argv)): infcls = int(argv[4],16)
      logger().log( "[CHIPSEC] Enumerating all EFI variables via OS specific EFI Variable API.." )
      efi_vars = _uefi.list_EFI_variables()
      if efi_vars is None:
          logger().log( "[CHIPSEC] Could not enumerate EFI Variables (Legacy OS?). Exit.." )
          return

      logger().log( "[CHIPSEC] Decoding EFI Variables.." )
      _orig_logname = logger().LOG_FILE_NAME
      logger().set_log_file( 'efi_variables.lst' )
      #print_sorted_EFI_variables( efi_vars )
      nvram_pth = 'efi_variables.dir'
      if not os.path.exists( nvram_pth ): os.makedirs( nvram_pth )
      decode_EFI_variables( efi_vars, nvram_pth )
      logger().set_log_file( _orig_logname )

      #efi_vars = _uefi.list_EFI_variables( infcls, filename )
      #_orig_logname = logger().LOG_FILE_NAME
      #logger().set_log_file( (filename + '.nv.lst') )
      #_uefi.parse_EFI_variables( filename, efi_vars, False, FWType.EFI_FW_TYPE_WIN )
      #logger().set_log_file( _orig_logname )

    elif ( 'nvram' == op or 'nvram-auth' == op ):

      authvars = ('nvram-auth' == op)
      efi_nvram_format = argv[3]
      if (4 == len(argv)):
         logger().log( "[CHIPSEC] Extracting EFI Variables directly in SPI ROM.." )
         try:
            _cs.init( True )
            _spi = SPI( _cs )
         except UnknownChipsetError, msg:
            print ("ERROR: Unknown chipset vendor (%s)" % str(msg))
            raise
         except SpiRuntimeError, msg:
            print ("ERROR: SPI initialization error" % str(msg))
            raise

         (bios_base,bios_limit,freg) = _spi.get_SPI_region( BIOS )
         bios_size = bios_limit - bios_base + 1
         logger().log( "[CHIPSEC] Reading BIOS: base = 0x%08X, limit = 0x%08X, size = 0x%08X" % (bios_base,bios_limit,bios_size) )
         rom = _spi.read_spi( bios_base, bios_size )
         _cs.stop( True )
         del _spi
      elif (5 == len(argv)):
         romfilename = argv[4]
         logger().log( "[CHIPSEC] Extracting EFI Variables from ROM file '%s'" % romfilename )
         rom = read_file( romfilename )

      _orig_logname = logger().LOG_FILE_NAME
      logger().set_log_file( (romfilename + '.nv.lst') )
      _uefi.parse_EFI_variables( romfilename, rom, authvars, efi_nvram_format )
      logger().set_log_file( _orig_logname )

    elif ( 'decode' == op):

      if (4 < len(argv)):
         filename = argv[3]
         fwtype = argv[4]
      else:
         print usage
         return
      logger().log( "[CHIPSEC] Parsing EFI volumes from '%s'.." % filename )
      _orig_logname = logger().LOG_FILE_NAME
      logger().set_log_file( filename + '.efi_fv.log' )
      cur_dir = _cs.helper.getcwd()
      decode_uefi_region(_uefi, cur_dir, filename, fwtype)
      logger().set_log_file( _orig_logname )

    elif ( 'keys' == op):

      if (3 < len(argv)):
         var_filename = argv[ 3 ]
      else:
         print usage
         return
      logger().log( "[CHIPSEC] Parsing EFI variable from '%s'.." % var_filename )
      parse_efivar_file( var_filename )

    logger().log( "[CHIPSEC] (uefi) time elapsed %.3f" % (time.time()-t) )


chipsec_util_commands['uefi'] = {'func' : uefi,    'start_driver' : False }


########NEW FILE########
__FILENAME__ = xmlout
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



import time
import sys
import traceback
import os
from os.path import basename

import xml.etree.ElementTree as ET
import platform
import xml.dom.minidom


class xmlAux:
    """Used to represent the variables to handle the xml output."""
    def __init__(self):
        """The Constructor."""
        self.test_cases = []
        self.useXML     = False
        self.testCase   = None
        self.class_name = None
        self.xmlFile    = None
        self.xmlStdout  = ""
        self.xmlStderr  = None
        self.properties = []

    def add_test_suite_property(self, name, value):
        """Adds a <property> child node to the <testsuite>."""
        if name is not None and value is not None:
            self.properties.append( ts_property( str(name).strip(), str(value).strip() ) )

    def set_xml_file(self, name):
        """Sets the filename used for the XML output."""
        if name != None:
            self.useXML = True
            self.xmlFile = name

    def append_stdout(self,msg):
        self.xmlStdout += str(msg) + "\n"

    def _check_testCase_exist(self):
        if self.testCase is None:
            if self.class_name is None:
                self.testCase = xmlTestCase( "test name", "class.name" )
            else:
                self.testCase = xmlTestCase( self.class_name, self.class_name )
                
    def _end_test(self):
        try:
            self.testCase.set_time()
            self.testCase.add_stdout_info( self.xmlStdout )
            self.test_cases.append( self.testCase )
            self.testCase = None
        except:
            print "Unexpected error:", sys.exc_info() [0]
            raise

    def passed_check(self):
        """Used when you want to mark a testcase as PASS and add it to the testsuite."""
        if self.useXML == True:
            self._check_testCase_exist()
            self._end_test()

    def failed_check(self, text):
        """Used when you want to mark a testcase as FAILURE and add it to the testsuite."""
        if self.useXML == True:
            self._check_testCase_exist()
            self.testCase.add_failure_info( text, None )
            self._end_test()

    def error_check(self, text):
        """Used when you want to mark a testcase as ERROR and add it to the testsuite."""
        if self.useXML == True:
            self._check_testCase_exist()
            self.testCase.add_error_info( text, None )
            self._end_test()

    def skipped_check(self, text):
        """Used when you want to mark a testcase as SKIPPED and add it to the testsuite."""
        if self.useXML == True:
            self._check_testCase_exist()
            self.testCase.add_skipped_info( text, None )
            self._end_test()

    def start_test(self, test_name):
        """Starts the test/testcase."""
        self.xmlStdout = ""
        if self.useXML == True:
            self.testCase = xmlTestCase( test_name, self.class_name )

    def start_module( self, module_name ):
        """Logs the start point of a Test, this is used for XML output.
           If XML file was not specified, it will just display a banner for the test name.
        """
        if self.useXML == True:
            self.class_name = module_name
            if self.testCase is not None:
                #If there's a test that did not send a status, so mark it as passed.
                self.passed_check( )
        self.xmlStdout = ""

    def end_module( self, module_name ):
        if self.useXML == True:
            self.class_name = ""
            if self.testCase is not None:
                #If there's a test that did not send a status, so mark it as passed.
                self.passed_check( )
        self.xmlStdout = ""

    def saveXML( self ):
        """Saves the XML info to a file in a JUnit style."""
        try:
            if self.useXML == True:
                if self.xmlFile is not None:
                    filename = self.xmlFile.replace("'", "")
                    filename2 = filename.replace(" ", "")
                    if filename2 in ["", " "]:
                        print "filename for XML received empty or invalid string. So skipping writing to a file."
                        return
                    ts = xmlTestSuite( basename( os.path.splitext(filename)[0] ) )
                    ts.test_cases = self.test_cases
                    if self.properties is not None and len( self.properties ) > 0:
                        ts.properties = self.properties
                else:
                    print "xmlFile is None. So skipping writing to a file."
                    return
                print "\nSaving XML to file : " + str( filename )
                ts.to_file( filename )
        except:
            print "Unexpected error : ", sys.exc_info() [0]
            print traceback.format_exc()
            raise

class testCaseType:
    """Used to represent the types of TestCase that can be assigned (FAILURE, ERROR, SKIPPED, PASS)"""
    FAILURE = 1
    ERROR   = 2
    SKIPPED = 3
    PASS    = 4

class xmlTestCase():
    """Represents a JUnit test case with a result and possibly some stdout or stderr"""

    def __init__(self, name, classname, pTime=None, stdout=None, stderr=None, tcType=None, message=None, output=None):
        """The Constructor"""
        self.name      = name
        self.time      = None
        self.startTime = time.time()
        self.endTime   = None
        if pTime is not None:
            self.time  = pTime
        self.stdout    = stdout
        self.stderr    = stderr
        self.classname = classname
        self.tcType    = tcType
        self.tcMessage = message
        self.tcOutput  = output
        #Just to be compatible with junit_xml
        self.error_message   = ""
        self.error_output    = ""
        self.failure_message = ""
        self.failure_output  = ""
        self.skipped_message = ""
        self.skipped_output  = ""

        if tcType == testCaseType.ERROR:
            self.error_message = message
            self.error_output  = output
        elif tcType == testCaseType.FAILURE:
            self.failure_message = message
            self.failure_output  = output
        elif tcType == testCaseType.SKIPPED:
            self.skipped_message = message
            self.skipped_output  = output
        else:
            #Then it should be PASSED.
            self.tcType = testCaseType.PASS

    def is_skipped(self):
        """Returns True if the testCase is of Type Skipped, if not returns False"""
        if self.tcType == testCaseType.SKIPPED:
            return True
        else:
            False

    def is_error(self):
        """Returns True if the testCase is of Type Error, if not returns False"""
        if self.tcType == testCaseType.ERROR:
            return True
        else:
            False

    def is_failure(self):
        """Returns True if the testCase is of Type Failure, if not returns False"""
        if self.tcType == testCaseType.FAILURE:
            return True
        else:
            False

    def is_pass(self):
        """Returns True if the testCase is of Type Pass, if not returns False."""
        if self.tcType not in [testCaseType.ERROR, testCaseType.FAILURE, testCaseType.SKIPPED] or self.tcType == testCaseType.PASS:
            return True
        else:
            False

    def add_failure_info(self, message=None, output=None):
        """Sets the values for the corresponding Type Failure."""
        self.tcType          = testCaseType.FAILURE
        self.tcMessage       = message
        self.tcOutput        = output
        #To be compatible with junit_xml
        self.failure_message = message
        self.failure_output  = output

    def add_error_info(self, message=None, output=None):
        """Sets the values for the corresponding Type Error."""
        self.tcType        = testCaseType.ERROR
        self.tcMessage     = message
        self.tcOutput      = output
        #To be compatible with junit_xml
        self.error_message = message
        self.error_output  = output

    def add_skipped_info(self, message=None, output=None):
        """Sets the values for the corresponding Type Skipped."""
        self.tcType          = testCaseType.SKIPPED
        self.tcMessage       = message
        self.tcOutput        = output
        #To be compatible with junit_xml
        self.skipped_message = message
        self.skipped_output  = output

    def add_stdout_info(self, text):
        """Adds the text that is going to be part of the stdout for the TestCase."""
        if self.stdout is not None:
            self.stdout += str(text)
        else:
            self.stdout = str(text)

    def add_stderr_info(self, text):
        """Adds the text that is going to be part of the stderr for the TestCase."""
        if self.stderr is not None:
            self.stderr += str(text)
        else:
            self.stderr = str(text)

    def set_time(self, pTime=None):
        """Sets the time"""
        if pTime is not None:
            self.time = pTime
        else:
            self.endTime = time.time()
            self.time = self.endTime - self.startTime


class xmlTestSuite(object):
    """Suite of test cases, it's the father node for TestCase."""

    def __init__(self, name, test_cases=None, hostname=None, ts_id=None, package=None, timestamp=None, properties=None):
        """The Constructor."""
        self.name       = name
        if not test_cases:
            test_cases  = []
        self.test_cases = test_cases
        self.hostname   = hostname
        self.ts_id      = ts_id
        self.package    = package
        self.timestamp  = timestamp
        self.properties = properties

    def to_xml_string(self):
        """Returns the string representation of the JUnit XML document."""
        try:
            iter( self.test_cases )
        except TypeError:
            raise Exception('test_suite has no test cases')

        strXML = TestSuite.to_xml_string( TestSuite(self.name,       self.test_cases, 
                                                     self.hostname,  self.ts_id, self.package, 
                                                     self.timestamp, self.properties) 
                                          )
        return strXML

    def to_file(self, file_name):
        """Writes the JUnit XML document to a file.
           In case of any error, it will print the exception information.
        """
        try:
            with open( file_name, 'w') as f :
                #f.write( '<?xml-stylesheet type="text/xsl" href="junit.xsl"?>' )
                f.write( self.to_xml_string() )
        except:
            print "Unexpected error : ", sys.exc_info() [0]
            print traceback.format_exc()


class ts_property(object):
    """Class to represent a TestSuite property."""
    def __init__(self, name, value):
        """The constructor."""
        self.name  = name
        self.value = value


class TestSuite(object):
    """Suite of test cases"""

    def __init__(self, name, test_cases, hostname, ts_id, package, timestamp, properties):
        self.name       = name
        if not test_cases:
            test_cases  = []
        try:
            iter( test_cases )
        except:
            pass
        self.test_cases = test_cases
        self.hostname   = hostname
        self.ts_id      = ts_id
        self.package    = package
        self.timestamp  = timestamp
        if not properties:
            self.properties = []
        else:
            self.properties = properties


    def build_xml(self):
        """Builds the XML elements."""
        ts_attributes                  = dict()
        if self.name:
            ts_attributes["name"]      = str( self.name )
        else:
            ts_attributes["name"]      = "name"
        if self.hostname:
            ts_attributes["hostname"]  = str( self.hostname )
        if self.ts_id:
            ts_attributes["id"]        = str( self.ts_id )
        if self.package:
            ts_attributes["package"]   = str( self.package )
        if self.timestamp:
            ts_attributes["timestamp"] = str( self.timestamp )

        ts_attributes['failures']      = str( len( [tc for tc in self.test_cases if tc.is_failure()] ) )
        ts_attributes['errors']        = str( len( [tc for tc in self.test_cases if tc.is_error()] ) )
        ts_attributes['skipped']       = str( len( [tc for tc in self.test_cases if tc.is_skipped()] ) )
        #ts_attributes["time"]          = str( sum( [tc.time for tc in self.test_cases if tc.time] ) )
        ts_attributes["time"]          = "%.5f" % sum( [tc.time for tc in self.test_cases if tc.time] )
        ts_attributes["tests"]         = str( len( self.test_cases ) )

        xml_element = ET.Element( "testsuite", ts_attributes )

        if len(self.properties) > 0:
            ps_element = ET.SubElement( xml_element, "properties" )
            temp = dict()
            for p in self.properties:
                temp["name"]  = p.name
                temp["value"] = p.value
                py_element = ET.SubElement( ps_element, "property", temp )

        for tc in self.test_cases:
            tc_attributes = dict()
            tc_attributes['name'] = str( tc.name )
            if tc.time:
                tc_attributes['time'] = "%.5f" % tc.time
            if tc.classname:
                tc_attributes['classname'] = str( tc.classname )

            tc_element = ET.SubElement( xml_element, "testcase", tc_attributes )

            #For the is_pass() case, there is nothing special, so we do nothing and process once.
            if tc.is_pass():
                pass
            elif tc.is_failure():
                failure_element = ET.SubElement( tc_element, "failure", {'type': 'failure'} )
                if tc.failure_message:
                    failure_element.set( 'message', tc.failure_message )
                if tc.failure_output:
                    failure_element.text = tc.failure_output
            elif tc.is_error():
                error_element = ET.SubElement( tc_element, "error", {'type': 'error'} )
                if tc.error_message:
                    error_element.set( 'message', tc.error_message )
                if tc.error_output:
                    error_element.text = tc.error_output
            elif tc.is_skipped():
                skipped_element = ET.SubElement( tc_element, "skipped", {'type': 'skipped'} )
                if tc.skipped_message:
                    skipped_element.set( 'message', tc.skipped_message )
                if tc.skipped_output:
                    skipped_element.text = tc.skipped_output

            #system-out and system-err are common for all, so here we go.
            if tc.stdout:
                stdout_element = ET.SubElement( tc_element, "system-out" )
                stdout_element.text = tc.stdout
            if tc.stderr:
                stderr_element = ET.SubElement( tc_element, "system-err" )
                stderr_element.text = tc.stderr

        return xml_element


    def to_xml_string(self):
        """Returns a string representation of the XML Tree for the TestSuite."""
        xml_element  = ET.Element("testsuites")
        xml_element2 = self.build_xml()
        xml_element.append( xml_element2 )
        xml_string = ET.tostring( xml_element, None, None )

        if platform.system().lower() in ["windows", "linux"]:
            xml_string = xml.dom.minidom.parseString(xml_string).toprettyxml()

        return xml_string


########NEW FILE########
__FILENAME__ = chipsec_main
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#



#
## \addtogroup core 
# __chipsec_main.py__ -- main application logic and automation functions
#

__version__ = '1.0'

import os
import re
import sys
import fnmatch
import time
import traceback
from inspect import getmembers, isfunction, getargspec

import errno
import chipsec.module_common as module_common

_importlib = True
try:
    import importlib
except ImportError:
    _importlib = False
#import zipfile

from chipsec.logger import logger

version="    "
if os.path.exists('VERSION'):
    with open('VERSION', "r") as verFile:
        version = "." + verFile.read()

logger().log( '' )
logger().log( "################################################################\n"
              "##                                                            ##\n"
              "##  CHIPSEC: Platform Hardware Security Assessment Framework  ##\n"
              "##                                                            ##\n"
              "################################################################" )
logger().log( "version %s\n"% (__version__ + version ) )


from chipsec.module_common import  AVAILABLE_MODULES, DISABLED_MODULES, USER_MODULE_TAGS
from chipsec.helper.oshelper       import OsHelperError
from chipsec.chipset import cs, Chipset_Code, CHIPSET_ID_UNKNOWN, CHIPSET_ID_COMMON, UnknownChipsetError
_cs = cs()

from chipsec.file import *

VERBOSE = False
CHIPSEC_LOADED_AS_EXE = False


##################################################################################
# Module API
##################################################################################

ZIP_MODULES_RE = None
def f_mod(x):
    return ( x.find('__init__') == -1 and ZIP_MODULES_RE.match(x) )

def map_modname(x):
    return (x.rpartition('.')[0]).replace('/','.')
    #return ((x.split('/', 2)[2]).rpartition('.')[0]).replace('/','.')

Import_Path             = "chipsec.modules."
REL_MOD_PATH            = "chipsec" + os.path.sep + "modules"
INSTALL_MOD_PATH_PREFIX = os.path.join( sys.prefix, 'Lib' + os.path.sep + 'site-packages' )
INSTALL_MOD_PATH        = os.path.join( INSTALL_MOD_PATH_PREFIX, 'chipsec' + os.path.sep + 'modules' )

try:
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir( tool_dir )
except:
    pass

if os.path.exists( REL_MOD_PATH ):
    is_chipsec_installed = False
    Modules_Path = REL_MOD_PATH
else:
    is_chipsec_installed = True
    Modules_Path = INSTALL_MOD_PATH

Loaded_Modules  = []
_list_tags = False
AVAILABLE_TAGS = []

MODPATH_RE      = re.compile("^\w+(\.\w+)*$")

def isModuleDisabled(module_path):
    try:
        if(len(DISABLED_MODULES)>0):
            if(module_path in DISABLED_MODULES[_cs.id]):
                return True
    except KeyError, msg:
        logger().log(str(msg))
    return False

    
def run_module( module_path, module_argv ):  
    module_path = module_path.replace( os.sep, '.' )
    if not MODPATH_RE.match(module_path):
        logger().error( "Invalid module path: %s" % module_path )
        return None  
    else:
        try:
            if _importlib:
                module = importlib.import_module( module_path )
            else:
                #module = __import__(module_path)
                exec 'import ' + module_path
            # removed temporary
            #if isModuleDisabled( module_path ):
            #    logger().error( "Module cannot run on this platform: '%.256s'" % module_path )
            #    return False;
        
        except ImportError, msg:
            logger().error( "Exception occurred during import of %s: '%s'" % (module_path, str(msg)) )
            return None

    run_it = True
    if len(USER_MODULE_TAGS) > 0 or _list_tags:
        run_it = False
        module_tags=[]
        try:
            if _importlib:
                module_tags = getattr( module, 'TAGS' )
            else:
                exec ('module_tags = ' +module_path + '.TAGS')
        except:
            #logger().log(module_path)
            #logger().log_bad(traceback.format_exc())
            pass
        for mt in module_tags:
            if _list_tags:
                if mt not in AVAILABLE_TAGS: AVAILABLE_TAGS.append(mt)
            elif mt in  USER_MODULE_TAGS:
                run_it = True

    if module_argv:
        logger().log( "[*] Module arguments (%d):" % len(module_argv) )
        logger().log( module_argv )
    else:
        module_argv = []
    

    if run_it:
        try:
            result = False
            logger().start_module( module_path )
            if _importlib:
                result = getattr( module, 'run' )( module_argv )
            else:
                exec (module_path + '.run(module_argv)')
            logger().end_module( module_path )
            return result 
        except (None,Exception) , msg:
            if logger().VERBOSE: logger().log_bad(traceback.format_exc())
            logger().log_error_check( "Exception ocurred during %s.run(): '%s'" % (module_path, str(msg)) )
            logger().end_module( module_path )
            return None
    else:
        return module_common.ModuleResult.SKIPPED

#
# module_path is a file path relative to chipsec
# E.g. chipsec/modules/common/module.py
#
def load_module( module_path ):
    if is_chipsec_installed: full_path = os.path.join( INSTALL_MOD_PATH_PREFIX, module_path )
    else:                    full_path = module_path
    if logger().VERBOSE: logger().log( "[*] loading module from '%.256s'" % full_path )  
    if not ( os.path.exists(full_path) and os.path.isfile(full_path) ):
        logger().error( "Module file not found: '%.256s'" % full_path )
        return False

    module_path = module_path.replace( os.path.sep, '.' )[:-3]
    if module_path not in Loaded_Modules:              
        Loaded_Modules.append( module_path )
        if not _list_tags: logger().log( "[+] loaded %s" % module_path ) 
    return True


def unload_module( module_path ):
    if module_path in Loaded_Modules:
        Loaded_Modules.remove( module_path )
    return True


def load_my_modules():
    #
    # Step 1.
    # Load modules common to all supported platforms
    #
    common_path = os.path.join( Modules_Path, 'common' )
    logger().log( "[*] loading common modules from \"%s\" .." % common_path )

    for dirname, subdirs, mod_fnames in os.walk( common_path ):
        for modx in mod_fnames:
            if fnmatch.fnmatch( modx, '*.py' ) and not fnmatch.fnmatch( modx, '__init__.py' ):
                load_module( os.path.join( dirname, modx ) )
    #
    # Step 2.
    # Load platform-specific modules from the corresponding platform module directory
    #
    chipset_path = os.path.join( Modules_Path, _cs.code.lower() )
    if (CHIPSET_ID_UNKNOWN != _cs.id) and os.path.exists( chipset_path ):
        logger().log( "[*] loading platform specific modules from \"%s\" .." % chipset_path )
        for dirname, subdirs, mod_fnames in os.walk( chipset_path ):
            for modx in mod_fnames:
                if fnmatch.fnmatch( modx, '*.py' ) and not fnmatch.fnmatch( modx, '__init__.py' ):
                    load_module( os.path.join( dirname, modx ) )
    else:
        logger().log( "[*] No platform specific modules to load" )
    #
    # Step 3.
    # Enumerate all modules from the root module directory
    # Load modules which support current platform (register themselves with AVAILABLE_MODULES[current_platform_id])
    #
    logger().log( "[*] loading modules from \"%s\" .." % Modules_Path )
    for modx in os.listdir( Modules_Path ):
        if fnmatch.fnmatch(modx, '*.py') and not fnmatch.fnmatch(modx, '__init__.py'):
            __import__( Import_Path + modx.split('.')[0] )
            # removed temporary
            #if isModuleDisabled(modx):
            #    AVAILABLE_MODULES[ _cs.id ][modx.split('.')[0]] = "invalidmodule." + modx.split('.')[0]
                    
    for modx in AVAILABLE_MODULES[ CHIPSET_ID_COMMON ]:
        load_module( os.path.join( Modules_Path, modx + '.py' ) )
    try:
        for modx in AVAILABLE_MODULES[ _cs.id ]:
            load_module( os.path.join( Modules_Path, modx + '.py' ) )
    except KeyError:
        pass
    #print Loaded_Modules

def clear_loaded_modules():
    del Loaded_Modules[:]


def print_loaded_modules():
    if Loaded_Modules == []:
        logger().log( "No modules have been loaded" )
    for modx in Loaded_Modules:
        logger().log( modx )


def run_loaded_modules():
    if not _list_tags:
        logger().log( "[*] running loaded modules .." )
    else:
        logger().log( "\n[*] Available tags are:" )
    t = time.time()
    failed   = []
    errors   = []
    warnings = []
    passed   = []
    skipped  = []
    executed = 0
    
    from chipsec.module_common import ModuleResult
    for modx in Loaded_Modules:
        executed += 1 
        result = run_module( modx, None )
        if None == result or ModuleResult.ERROR == result:
            errors.append( modx )
        elif False == result or ModuleResult.FAILED == result:
            failed.append( modx )
        elif True == result or ModuleResult.PASSED == result:
            passed.append( modx )
        elif ModuleResult.WARNING == result:
            warnings.append( modx )
        elif ModuleResult.SKIPPED == result:
            skipped.append( modx )

    if not _list_tags:
        logger().log( "" )
        logger().log( "[CHIPSEC] ***************************  SUMMARY  ***************************" )
        logger().log( "[CHIPSEC] Time elapsed          %.3f" % (time.time()-t) )
        logger().log( "[CHIPSEC] Modules total         %d" % executed )
        logger().log( "[CHIPSEC] Modules failed to run %d:" % len(errors) )
        for mod in errors: logger().error( mod )
        logger().log( "[CHIPSEC] Modules passed        %d:" % len(passed) )
        for fmod in passed: logger().log_passed( fmod )
        logger().log( "[CHIPSEC] Modules failed        %d:" % len(failed) )
        for fmod in failed: logger().log_failed( fmod )
        logger().log( "[CHIPSEC] Modules with warnings %d:" % len(warnings) )
        for fmod in warnings: logger().log_warning( fmod )
        logger().log( "[CHIPSEC] Modules skipped %d:" % len(skipped) )
        for fmod in skipped: logger().log_skipped( fmod )
        logger().log( "[CHIPSEC] *****************************************************************" )
        logger().log( "[CHIPSEC] Version:   %s"% (__version__ + version ) )
    else:
        for at in AVAILABLE_TAGS:
            logger().log(" - %s"%at)

    return len(failed)



##################################################################################
# Running all chipset configuration security checks
##################################################################################

def run_all_modules():
    if CHIPSEC_LOADED_AS_EXE:
        import zipfile
        myzip = zipfile.ZipFile( "library.zip" )
        global ZIP_MODULES_RE
        ZIP_MODULES_RE = re.compile("^chipsec\/modules\/\w+\.pyc$|^chipsec\/modules\/common\/(\w+\/)*\w+\.pyc$|^chipsec\/modules\/"+_cs.code.lower()+"\/\w+\.pyc$", re.IGNORECASE|re.VERBOSE)
        Loaded_Modules.extend( map(map_modname, filter(f_mod, myzip.namelist())) )
        logger().log( "Loaded modules from ZIP:" )
        print Loaded_Modules
    else:
        load_my_modules()
    return run_loaded_modules()




def usage():
    print "\nUSAGE: %.64s [options]" % sys.argv[0]
    print "OPTIONS:"
    print "-m --module             specify module to run (example: -m common.bios)"
    print "-a --module_args        additional module arguments, format is 'arg0,arg1..'"
    print "-v --verbose            verbose mode"
    print "-l --log                output to log file"  
    print "\nADVANCED OPTIONS:"
    print "-p --platform           platform in [ %s ]" % (" | ".join( ["%.4s" % c for c in Chipset_Code]))
    print "-n --no_driver          chipsec won't need kernel mode functions so don't load chipsec driver"
    print "-i --ignore_platform    run chipsec even if the platform is an unrecognized platform."
    print "-e --exists             chipsec service has already been manually installed and started (driver loaded)."
    print "-x --xml                specify filename for xml output (JUnit style)."
    #Run specific tests help
    print "-t --moduletype         run tests of a specific type (tag)."
    print "--list_tags             list all the available options for -t,--moduletype"

##################################################################################
# Entry point for command-line execution
##################################################################################

if __name__ == "__main__":
    
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ip:m:ho:vea:nl:t:x:",
        ["ignore_platform", "platform=", "module=", "help", "output=", "verbose", "exists", "module_args=", "no_driver", "log=",  "moduletype=", "xml=","list_tags"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(errno.EINVAL)

    _output      = 'chipsec.log'
    _module      = None
    _module_argv = None
    _platform    = None
    _file        = None
    _start_svc   = True
    _no_driver   = False
    _unkownPlatform = True
    _list_tags   = False

    for o, a in opts:
        if o in ("-v", "--verbose"):
            logger().VERBOSE = True
            logger().log( "[*] Verbose mode is ON (-v command-line option or chipsec_main.logger().VERBOSE in Python console)" )
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-o", "--output"):
            _output = a
        elif o in ("-p", "--platform"):
            _platform = a.upper()
        elif o in ("-m", "--module"):
            #_module = a.lower()
            _module = a
            if not _module.startswith( Import_Path ):
                _module = Import_Path + _module
        elif o in ("-a", "--module_args"):
            _module_argv = a.split(',')
        elif o in ("-e", "--exists"):
            _start_svc = False
        elif o in ("-i", "--ignore_platform"):
            logger().log( "[*] Ignoring unsupported platform warning and continue execution" )
            _unkownPlatform = False
        #elif o in ("-f", "--file"):
        #    _file = read_file( a )
        elif o in ("-l", "--log"):
            logger().set_log_file( a )
            logger().log( "[*] Log console results to log folder when this mode is ON (-l command-line option or chipsec_main.logger().LOG_TO_COMPLETE_FILE in Python console)" )
            logger().log( "[*] Please check log results in " + logger().LOG_FILE_NAME )
        elif o in ("-t", "--moduletype"):
            usertags = a.upper().split(",")
            for tag in usertags:
                USER_MODULE_TAGS.append(tag)
        elif o in ("-n", "--no_driver"):
            _no_driver = True
        elif o in ("-x", "--xml"):
            logger().set_xml_file(a)
        elif o in ("--list_tags"):
            _list_tags = True
        else:
            assert False, "unknown option"

    # If no driver needed, we won't start/stop service
    if _no_driver: _start_svc = False

    try:
        # If no driver needed, we won't initialize chipset with automatic platform detection
        if not _no_driver: _cs.init( _platform, _start_svc )
    except UnknownChipsetError , msg:
        logger().error( "Platform is not supported (%s)." % str(msg) )
        if _unkownPlatform:
            logger().error( 'To run anyways please use -i command-line option\n\n' )
            if logger().VERBOSE: logger().log_bad(traceback.format_exc())
            sys.exit( errno.ENODEV )
        logger().warn("Platform dependent functionality is likely to be incorrect")
    except OsHelperError as os_helper_error:
        logger().error(str(os_helper_error))
        if logger().VERBOSE: logger().log_bad(traceback.format_exc())
        sys.exit(os_helper_error.errorcode)
    
    logger().log( " " )
    logger().log( "OS      : %s %s %s %s" % (_cs.helper.os_system, _cs.helper.os_release, _cs.helper.os_version, _cs.helper.os_machine) )
    logger().log( "Platform: %s\n          VID: %04X\n          DID: %04X" % (_cs.longname, _cs.vid, _cs.did))
    logger().log( "CHIPSEC : %s"% (__version__ + version ) )
    logger().xmlAux.add_test_suite_property( "OS", "%s %s %s %s" % (_cs.helper.os_system, _cs.helper.os_release, _cs.helper.os_version, _cs.helper.os_machine) )
    logger().xmlAux.add_test_suite_property( "Platform", "%s, VID: %04X, DID: %04X" % (_cs.longname, _cs.vid, _cs.did) )
    logger().xmlAux.add_test_suite_property( "CHIPSEC", "%s"% (__version__ + version ) )
    logger().log( " " )
    module_common.init()

    if logger().VERBOSE: logger().log("[*] Running from %s" % os.getcwd())

    # determine if CHIPSEC is loaded as chipsec.exe or in python
    frozen = hasattr(sys, "frozen") or hasattr(sys, "importers")
    CHIPSEC_LOADED_AS_EXE = True if frozen else False
    
    modules_failed = 0
    if _module:
        _module = _module.replace( os.sep, '.' );
        #if not CHIPSEC_LOADED_AS_EXE: load_module( _module );
        t0 = time.time()    
        result = run_module( _module, _module_argv )
        logger().log( "[CHIPSEC] (%s) time elapsed %.3f" % (_module,time.time()-t0) )
        #if not CHIPSEC_LOADED_AS_EXE: unload_module( _module );
    else:
        modules_failed = run_all_modules()

    logger().saveXML()

    _cs.destroy( _start_svc )
    del _cs
    logger().log("\n")
    
    sys.exit(-modules_failed)

########NEW FILE########
__FILENAME__ = chipsec_util
#!/usr/local/bin/python
#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2010-2014, Intel Corporation
# 
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; Version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#Contact information:
#chipsec@intel.com
#




#
## \addtogroup core
# __chipsec_util.py__ - standalone utility
#

__version__ = '1.0'

#import glob
import re
import os
import sys
import time

from chipsec.logger     import *
from chipsec.file       import *
from chipsec.helper.oshelper   import helper

from chipsec.chipset import cs
_cs = cs()

#
# If you want to turn verbose logging change this line to True
#
logger().VERBOSE    = False
logger().UTIL_TRACE = True

global_usage = "CHIPSEC UTILITIES\n\n" + \
               "All numeric values are in hex\n" + \
               "<width> is in {1, byte, 2, word, 4, dword}\n\n"

def help(argv):
    print "\n[CHIPSEC] chipsec_util command-line extensions should be one of the following:"
    for cmd in chipsec_util_commands.keys():
        print cmd
    print global_usage

chipsec_util_commands = {}
chipsec_util_commands['help'] = {'func' : help, 'start_driver' : False  }


ZIP_UTILCMD_RE = re.compile("^chipsec\/utilcmd\/\w+\.pyc$", re.IGNORECASE)
def f_mod_zip(x):
    return ( x.find('__init__') == -1 and ZIP_UTILCMD_RE.match(x) )
def map_modname_zip(x):
    return ((x.split('/', 2)[2]).rpartition('.')[0]).replace('/','.')

MODFILE_RE = re.compile("^\w+\.py$")
def f_mod(x):
    return ( x.find('__init__') == -1 and MODFILE_RE.match(x) )
def map_modname(x):
    return x.split('.')[0]

##################################################################################
# Entry point
##################################################################################

# determine if CHIPSEC is loaded as chipsec_*.exe or in python
CHIPSEC_LOADED_AS_EXE = True if (hasattr(sys, "frozen") or hasattr(sys, "importers")) else False
#CHIPSEC_LOADED_AS_EXE = not sys.argv[0].endswith('.py')

if __name__ == "__main__":
    
    argv = sys.argv
    
    #import traceback
    if CHIPSEC_LOADED_AS_EXE:
        import zipfile
        myzip = zipfile.ZipFile("library.zip")
        cmds = map( map_modname_zip, filter(f_mod_zip, myzip.namelist()) )
    else:
        #traceback.print_stack()
        mydir = os.path.dirname(__file__)
        cmds_dir = os.path.join(mydir,os.path.join("chipsec","utilcmd"))
        cmds = map( map_modname, filter(f_mod, os.listdir(cmds_dir)) )

    #print "[CHIPSEC] Loaded command-line extensions:"
    #print '   %s' % cmds
    #print ' '

    for cmd in cmds:
        try:
           #__import__('chipsec.utilcmd.' + cmd)
           exec 'from chipsec.utilcmd.' + cmd + ' import *'
        except ImportError, msg:
           logger().error( "Couldn't import util command extension '%s'" % cmd )
           raise ImportError, msg

    if 1 < len(argv):
       cmd = argv[ 1 ]
       if chipsec_util_commands.has_key( cmd ):
          if chipsec_util_commands[ cmd ]['start_driver']:
             try:
                _cs.init( None, True )
             except UnknownChipsetError, msg:
                logger().warn("***************************************************************************************")
                logger().warn("* Unknown platform vendor. Platform dependent functionality is likely incorrect")
                logger().warn("* Error Message: \"%s\"" % str(msg))
                logger().warn("***************************************************************************************")
             except (None,Exception) , msg:
                logger().error(str(msg))
                exit(-1)

          logger().log("[CHIPSEC] Executing command '%s' with args %s"%(cmd,argv[2:]))
          chipsec_util_commands[ cmd ]['func']( argv )

          if chipsec_util_commands[ cmd ]['start_driver']: _cs.destroy( True )
       else:                                
          print "ERROR: Unknown command '%.32s'" % cmd
          print chipsec_util.global_usage
    else:
       print chipsec_util.global_usage

    del _cs

########NEW FILE########
