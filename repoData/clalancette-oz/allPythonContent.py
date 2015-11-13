__FILENAME__ = Debian
# Copyright (C) 2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Debian installation
"""

import shutil
import os
import re

import oz.Guest
import oz.ozutil
import oz.OzException

class DebianGuest(oz.Guest.CDGuest):
    """
    Class for Debian 5, 6 and 7 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk,
                                  netdev, None, None, diskbus, True, False,
                                  macaddress)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        self.log.debug("Copying preseed file")
        oz.ozutil.mkdir_p(os.path.join(self.iso_contents, "preseed"))

        outname = os.path.join(self.iso_contents, "preseed", "customiso.seed")

        if self.default_auto_file():
            def _preseed_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Debian.
                """
                if re.match('d-i passwd/root-password password', line):
                    return 'd-i passwd/root-password password ' + self.rootpw + '\n'
                elif re.match('d-i passwd/root-password-again password', line):
                    return 'd-i passwd/root-password-again password ' + self.rootpw + '\n'
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _preseed_sub)
        else:
            shutil.copy(self.auto, outname)

        if self.tdl.arch == "x86_64":
            installdir = "/install.amd"
        else:
            # arch == i386
            installdir = "/install.386"

        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(self.iso_contents, "isolinux", "isolinux.cfg")
        extra = ""
        if self.tdl.update in ["7"]:
            extra = "auto=true "

        with open(isolinuxcfg, 'w') as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  menu label ^Customiso
  menu default
  kernel %s/vmlinuz
  append file=/cdrom/preseed/customiso.seed %sdebian-installer/locale=en_US console-setup/layoutcode=us netcfg/choose_interface=auto priority=critical initrd=%s/initrd.gz --
""" % (installdir, extra, installdir))

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-l", "-no-emul-boot",
                                           "-b", "isolinux/isolinux.bin",
                                           "-c", "isolinux/boot.cat",
                                           "-boot-load-size", "4",
                                           "-cache-inodes", "-boot-info-table",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Debian installs.
    """
    if tdl.update in ["5", "6", "7"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return DebianGuest(tdl, config, auto, output_disk, netdev, diskbus,
                           macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Debian: 5, 6, 7"

########NEW FILE########
__FILENAME__ = Fedora
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013,2014  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Fedora installation
"""

import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class FedoraGuest(oz.RedHat.RedHatLinuxCDYumGuest):
    """
    Class for Fedora 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, and 20 installation.
    """
    def __init__(self, tdl, config, auto, nicmodel, haverepo, diskbus,
                 brokenisomethod, output_disk=None, macaddress=None,
                 assumed_update=None):
        directkernel = "cpio"
        if tdl.update in ["16", "17"]:
            directkernel = None
        self.assumed_update = assumed_update

        oz.RedHat.RedHatLinuxCDYumGuest.__init__(self, tdl, config, auto,
                                                 output_disk, nicmodel, diskbus,
                                                 True, True, directkernel,
                                                 macaddress)

        if self.assumed_update is not None:
            self.log.warning("==== WARN: TDL contains Fedora update %s, which is newer than Oz knows about; pretending this is Fedora %s, but this may fail ====" % (tdl.update, assumed_update))

        self.haverepo = haverepo
        self.brokenisomethod = brokenisomethod

    def _modify_iso(self):
        """
        Method to modify the ISO for autoinstallation.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        if self.tdl.update in ["17", "18", "19", "20"]:
            initrdline = "  append initrd=initrd.img ks=cdrom:/dev/cdrom:/ks.cfg"
        else:
            initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg"
        if self.tdl.installtype == "url":
            if self.haverepo:
                initrdline += " repo="
            else:
                initrdline += " method="
            initrdline += self.url + "\n"
        else:
            # if the installtype is iso, then due to a bug in anaconda we leave
            # out the method completely
            if not self.brokenisomethod:
                initrdline += " method=cdrom:/dev/cdrom"
            initrdline += "\n"
        self._modify_isolinux(initrdline)

    def generate_diskimage(self, size=10, force=False):
        """
        Method to generate a diskimage.  By default, a blank diskimage of
        10GB will be created; the caller can override this with the size
        parameter, specified in GB.  If force is False (the default), then
        a diskimage will not be created if a cached JEOS is found.  If
        force is True, a diskimage will be created regardless of whether a
        cached JEOS exists.  See the oz-install man page for more
        information about JEOS caching.
        """
        createpart = False
        if self.tdl.update in ["11", "12"]:
            # If given a blank diskimage, Fedora 11/12 stops very early in
            # install with a message about losing all of your data on the
            # drive (it differs between them).
            #
            # To avoid that message, just create a partition table that spans
            # the entire disk
            createpart = True
        return self._internal_generate_diskimage(size, force, createpart)

    def get_auto_path(self):
        """
        Method to create the correct path to the Fedora kickstart files.
        """
        # If we are doing our best with an unknown Fedora update, use the
        # newest known auto file; otherwise, do the usual thing.
        if self.assumed_update is not None:
            return oz.ozutil.generate_full_auto_path(self.tdl.distro + self.assumed_update + ".auto")
        else:
            return oz.ozutil.generate_full_auto_path(self.tdl.distro + self.tdl.update + ".auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Fedora installs.
    """
    newer_distros = ["18", "19", "20"]

    if int(tdl.update) > int(newer_distros[-1]):
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return FedoraGuest(tdl, config, auto, netdev, True, diskbus, False,
                           output_disk, macaddress, newer_distros[-1])

    if tdl.update in newer_distros:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return FedoraGuest(tdl, config, auto, netdev, True, diskbus, False,
                           output_disk, macaddress, None)

    if tdl.update in ["10", "11", "12", "13", "14", "15", "16", "17"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return FedoraGuest(tdl, config, auto, netdev, True, diskbus, True,
                           output_disk, macaddress, None)

    if tdl.update in ["7", "8", "9"]:
        return FedoraGuest(tdl, config, auto, netdev, False, diskbus, False,
                           output_disk, macaddress, None)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Fedora: 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20"

########NEW FILE########
__FILENAME__ = FedoraCore
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Fedora Core installation
"""

import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class FedoraCoreGuest(oz.RedHat.RedHatLinuxCDGuest):
    """
    Class for Fedora Core 1, 2, 3, 4, 5, and 6 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        initrdtype = "cpio"
        if tdl.update in ["1", "2", "3"]:
            initrdtype = "ext2"
        oz.RedHat.RedHatLinuxCDGuest.__init__(self, tdl, config, auto,
                                              output_disk, netdev, diskbus,
                                              True, True, initrdtype,
                                              macaddress)

        # FIXME: if doing an ISO install, we have to check that the ISO passed
        # in is the DVD, not the CD (since we can't change disks midway)

    def _modify_iso(self):
        """
        Method to modify the ISO for autoinstallation.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method="
        if self.tdl.installtype == "url":
            initrdline += self.url + "\n"
        else:
            initrdline += "cdrom:/dev/cdrom\n"
        self._modify_isolinux(initrdline)

    def get_auto_path(self):
        """
        Method to create the correct path to the Fedora Core kickstart files.
        """
        return oz.ozutil.generate_full_auto_path("FedoraCore" + self.tdl.update + ".auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Fedora Core installs.
    """
    if tdl.update in ["1", "2", "3", "4", "5", "6"]:
        return FedoraCoreGuest(tdl, config, auto, output_disk, netdev, diskbus,
                               macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Fedora Core: 1, 2, 3, 4, 5, 6"

########NEW FILE########
__FILENAME__ = FreeBSD
# Copyright (C) 2013  harmw <harm@weites.com>
# Copyright (C) 2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
FreeBSD installation
"""

import os

import oz.Guest
import oz.ozutil
import oz.OzException

class FreeBSD(oz.Guest.CDGuest):
    """
    Class for FreeBSD 10.0 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
	oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk,
                                  netdev, "localtime", "usb", diskbus, True,
                                  False, macaddress)

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.debug("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage",
                                           "-R", "-no-emul-boot",
                                           "-b", "boot/cdboot", "-v",
                                           "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

	def _replace(line):
            keys = {
                '#ROOTPW#': self.rootpw,
            }
            for key, val in keys.iteritems():
                line = line.replace(key, val)
            return line

        # Copy the installconfig file to /etc/ on the iso image so bsdinstall(8)
        # can use that to do an unattended installation. This rules file
        # contains both setup rules and a post script. This stage also prepends
        # the post script with additional commands so it's possible to install
        # extra	packages specified in the .tdl file.

	outname = os.path.join(self.iso_contents, "etc", "installerconfig")
	oz.ozutil.copy_modify_file(self.auto, outname, _replace)

        # Make sure the iso can be mounted at boot, otherwise this error shows
        # up after booting the kernel:
        #  mountroot: waiting for device /dev/iso9660/FREEBSD_INSTALL ...
	#  Mounting from cd9660:/dev/iso9660/FREEBSD_INSTALL failed with error 19.

	loaderconf = os.path.join(self.iso_contents, "boot", "loader.conf")
	with open(loaderconf, 'w') as conf:
            conf.write('vfs.root.mountfrom="cd9660:/dev/cd0"\n')

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for FreeBSD installs.
    """
    if tdl.update in ["10.0"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
    return FreeBSD(tdl, config, auto, output_disk, netdev, diskbus,
                   macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "FreeBSD: 10"

########NEW FILE########
__FILENAME__ = Guest
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Main class for guest installation
"""

import uuid
import libvirt
import os
import fcntl
import subprocess
import shutil
import time
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse
import stat
import lxml.etree
import logging
import random
import guestfs
import socket
import struct
import tempfile
import M2Crypto
import base64
import hashlib
import errno
import re

import oz.ozutil
import oz.OzException

class Guest(object):
    """
    Main class for guest installation.
    """
    def _discover_libvirt_type(self):
        """
        Internal method to discover the libvirt type (qemu, kvm, etc) that
        we should use, if not specified by the user.
        """
        if self.libvirt_type is None:
            doc = lxml.etree.fromstring(self.libvirt_conn.getCapabilities())

            if len(doc.xpath("/capabilities/guest/arch/domain[@type='kvm']")) > 0:
                self.libvirt_type = 'kvm'
            elif len(doc.xpath("/capabilities/guest/arch/domain[@type='qemu']")) > 0:
                self.libvirt_type = 'qemu'
            else:
                raise oz.OzException.OzException("This host does not support virtualization type kvm or qemu")

        self.log.debug("Libvirt type is %s" % (self.libvirt_type))

    def _discover_libvirt_bridge(self):
        """
        Internal method to discover a libvirt bridge (if necessary).
        """
        if self.bridge_name is None:
            # otherwise, try to detect a private libvirt bridge
            for netname in self.libvirt_conn.listNetworks():
                network = self.libvirt_conn.networkLookupByName(netname)

                xml = network.XMLDesc(0)
                doc = lxml.etree.fromstring(xml)

                forward = doc.xpath('/network/forward')
                if len(forward) != 1:
                    self.log.warn("Libvirt network without a forward element, skipping")
                    continue

                if forward[0].get('mode') == 'nat':
                    ips = doc.xpath('/network/ip')
                    if len(ips) == 0:
                        self.log.warn("Libvirt network without an IP, skipping")
                        continue
                    for ip in ips:
                        family = ip.get("family")
                        if family is None or family == "ipv4":
                            self.bridge_name = network.bridgeName()
                            break

        if self.bridge_name is None:
            raise oz.OzException.OzException("Could not find a libvirt bridge.  Please run 'virsh net-start default' to start the default libvirt network, or see http://github.com/clalancette/oz/wiki/Oz-Network-Configuration for more information")

        self.log.debug("libvirt bridge name is %s" % (self.bridge_name))

    def connect_to_libvirt(self):
        """
        Method to connect to libvirt and detect various things about the
        environment.
        """
        def _libvirt_error_handler(ctxt, err):
            """
            Error callback to suppress libvirt printing to stderr by default.
            """
            pass

        libvirt.registerErrorHandler(_libvirt_error_handler, 'context')
        self.libvirt_conn = libvirt.open(self.libvirt_uri)
        self._discover_libvirt_bridge()
        self._discover_libvirt_type()

    def __init__(self, tdl, config, auto, output_disk, nicmodel, clockoffset,
                 mousetype, diskbus, iso_allowed, url_allowed, macaddress):
        self.tdl = tdl

        # for backwards compatibility
        self.name = self.tdl.name

        if self.tdl.arch != "i386" and self.tdl.arch != "x86_64":
            raise oz.OzException.OzException("Unsupported guest arch " + self.tdl.arch)

        if os.uname()[4] in ["i386", "i586", "i686"] and self.tdl.arch == "x86_64":
            raise oz.OzException.OzException("Host machine is i386, but trying to install x86_64 guest; this cannot work")

        self.log = logging.getLogger('%s.%s' % (__name__,
                                                self.__class__.__name__))
        self.uuid = uuid.uuid4()
        if macaddress is None:
            self.macaddr = oz.ozutil.generate_macaddress()
        else:
            self.macaddr = macaddress

        # configuration from 'paths' section
        self.output_dir = oz.ozutil.config_get_path(config, 'paths',
                                                    'output_dir',
                                                    oz.ozutil.default_output_dir())

        oz.ozutil.mkdir_p(self.output_dir)

        self.data_dir = oz.ozutil.config_get_path(config, 'paths',
                                                  'data_dir',
                                                  oz.ozutil.default_data_dir())

        self.screenshot_dir = oz.ozutil.config_get_path(config, 'paths',
                                                        'screenshot_dir',
                                                        oz.ozutil.default_screenshot_dir())

        self.sshprivkey = oz.ozutil.config_get_path(config, 'paths',
                                                    'sshprivkey',
                                                    oz.ozutil.default_sshprivkey())

        # configuration from 'libvirt' section
        self.libvirt_uri = oz.ozutil.config_get_key(config, 'libvirt', 'uri',
                                                    'qemu:///system')
        self.libvirt_type = oz.ozutil.config_get_key(config, 'libvirt', 'type',
                                                     None)
        self.bridge_name = oz.ozutil.config_get_key(config, 'libvirt',
                                                    'bridge_name', None)
        self.install_cpus = oz.ozutil.config_get_key(config, 'libvirt', 'cpus',
                                                     1)
        # the memory in the configuration file is specified in megabytes, but
        # libvirt expects kilobytes, so multiply by 1024
        self.install_memory = int(oz.ozutil.config_get_key(config, 'libvirt',
                                                           'memory', 1024)) * 1024
        self.image_type = oz.ozutil.config_get_key(config, 'libvirt',
                                                   'image_type', 'raw')

        # configuration from 'cache' section
        self.cache_original_media = oz.ozutil.config_get_boolean_key(config,
                                                                     'cache',
                                                                     'original_media',
                                                                     True)
        self.cache_modified_media = oz.ozutil.config_get_boolean_key(config,
                                                                     'cache',
                                                                     'modified_media',
                                                                     False)
        self.cache_jeos = oz.ozutil.config_get_boolean_key(config, 'cache',
                                                           'jeos', False)

        self.jeos_cache_dir = os.path.join(self.data_dir, "jeos")

        # configuration of "safe" ICICLE generation option
        self.safe_icicle_gen = oz.ozutil.config_get_boolean_key(config,
                                                                'icicle',
                                                                'safe_generation',
                                                                False)

        # only pull a cached JEOS if it was built with the correct image type
        if self.image_type == 'raw':
            # backwards compatible
            jeos_extension = 'dsk'
        else:
            jeos_extension = self.image_type

        self.jeos_filename = os.path.join(self.jeos_cache_dir,
                                          self.tdl.distro + self.tdl.update + self.tdl.arch + '.' + jeos_extension)

        self.diskimage = output_disk
        if self.diskimage is None:
            ext = "." + self.image_type
            # compatibility with older versions of Oz
            if self.image_type == 'raw':
                ext = '.dsk'
            self.diskimage = os.path.join(self.output_dir, self.tdl.name + ext)

        if not os.path.isabs(self.diskimage):
            raise oz.OzException.OzException("Output disk image must be an absolute path")

        self.icicle_tmp = os.path.join(self.data_dir, "icicletmp",
                                       self.tdl.name)
        self.listen_port = random.randrange(1024, 65535)

        self.connect_to_libvirt()

        self.nicmodel = nicmodel
        if self.nicmodel is None:
            self.nicmodel = "rtl8139"
        self.clockoffset = clockoffset
        if self.clockoffset is None:
            self.clockoffset = "utc"
        self.mousetype = mousetype
        if self.mousetype is None:
            self.mousetype = "ps2"
        if diskbus is None or diskbus == "ide":
            self.disk_bus = "ide"
            self.disk_dev = "hda"
        elif diskbus == "virtio":
            self.disk_bus = "virtio"
            self.disk_dev = "vda"
        else:
            raise oz.OzException.OzException("Unknown diskbus type " + diskbus)

        self.rootpw = self.tdl.rootpw
        if self.rootpw is None:
            self.rootpw = "ozrootpw"

        try:
            self.url = self._check_url(iso=iso_allowed, url=url_allowed)
        except:
            self.log.debug("Install URL validation failed:", exc_info=True)
            raise

        oz.ozutil.mkdir_p(self.icicle_tmp)

        self.disksize = self.tdl.disksize
        if self.disksize is None:
            self.disksize = 10
        else:
            self.disksize = int(self.disksize)

        self.auto = auto
        if self.auto is None:
            self.auto = self.get_auto_path()

        self.log.debug("Name: %s, UUID: %s" % (self.tdl.name, self.uuid))
        self.log.debug("MAC: %s, distro: %s" % (self.macaddr, self.tdl.distro))
        self.log.debug("update: %s, arch: %s, diskimage: %s" % (self.tdl.update, self.tdl.arch, self.diskimage))
        self.log.debug("nicmodel: %s, clockoffset: %s" % (self.nicmodel, self.clockoffset))
        self.log.debug("mousetype: %s, disk_bus: %s, disk_dev: %s" % (self.mousetype, self.disk_bus, self.disk_dev))
        self.log.debug("icicletmp: %s, listen_port: %d" % (self.icicle_tmp, self.listen_port))

    def image_name(self):
        """
        Name of the image being built.
        """
        return self.name

    def output_image_path(self):
        """
        Path to the created image file.
        """
        return self.diskimage

    def get_auto_path(self):
        """
        Base method used to generate the path to the automatic installation
        file (kickstart, preseed, winnt.sif, etc).  Some subclasses override
        override this method to provide support for additional aliases.
        """
        return oz.ozutil.generate_full_auto_path(self.tdl.distro + self.tdl.update + ".auto")

    def default_auto_file(self):
        """
        Method to determine if the auto file is the default one or
        user-provided.
        """
        return self.auto == self.get_auto_path()

    def cleanup_old_guest(self):
        """
        Method to completely clean up an old guest, including deleting the
        disk file.  Use with caution!
        """
        self.log.info("Cleaning up guest named %s" % (self.tdl.name))
        try:
            dom = self.libvirt_conn.lookupByName(self.tdl.name)
            try:
                dom.destroy()
            except libvirt.libvirtError:
                pass
            dom.undefine()
        except libvirt.libvirtError:
            pass

        try:
            os.unlink(self.diskimage)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise

    def check_for_guest_conflict(self):
        """
        Method to check if any of our future actions will conflict with an
        already existing guest.  In particular, if a guest with the same
        name, UUID, or diskimage already exists, this throws an exception.
        """
        self.log.info("Checking for guest conflicts with %s" % (self.tdl.name))

        try:
            self.libvirt_conn.lookupByName(self.tdl.name)
            raise oz.OzException.OzException("Domain with name %s already exists" % (self.tdl.name))
        except libvirt.libvirtError:
            pass

        try:
            self.libvirt_conn.lookupByUUID(str(self.uuid))
            raise oz.OzException.OzException("Domain with UUID %s already exists" % (self.uuid))
        except libvirt.libvirtError:
            pass

        if os.access(self.diskimage, os.F_OK):
            raise oz.OzException.OzException("Diskimage %s already exists" % (self.diskimage))

    # the next 4 methods are intended to be overridden by the individual
    # OS backends; raise an error if they are called but not implemented

    def generate_install_media(self, force_download=False,
                               customize_or_icicle=False):
        """
        Base method for generating the install media for operating system
        installation.  This is expected to be overridden by all subclasses.
        """
        raise oz.OzException.OzException("Install media for %s%s is not implemented, install cannot continue" % (self.tdl.distro, self.tdl.update))

    def customize(self, libvirt_xml):
        """
        Base method for customizing the operating system.  This is expected
        to be overridden by subclasses that support customization.
        """
        raise oz.OzException.OzException("Customization for %s%s is not implemented" % (self.tdl.distro, self.tdl.update))

    def generate_icicle(self, libvirt_xml):
        """
        Base method for generating the ICICLE manifest from the operating
        system.  This is expect to be overridden by subclasses that support
        ICICLE generation.
        """
        raise oz.OzException.OzException("ICICLE generation for %s%s is not implemented" % (self.tdl.distro, self.tdl.update))

    # this method is intended to be an optimization if the user wants to do
    # both customize and generate_icicle
    def customize_and_generate_icicle(self, libvirt_xml):
        """
        Base method for doing operating system customization and ICICLE
        generation.  This is an optimization over doing the two steps
        separately for those classes that support customization and ICICLE
        generation.
        """
        raise oz.OzException.OzException("Customization and ICICLE generate for %s%s is not implemented" % (self.tdl.distro, self.tdl.update))

    class _InstallDev(object):
        """
        Class to hold information about an installation device.
        """
        def __init__(self, devicetype, path, bus):
            self.devicetype = devicetype
            self.path = path
            self.bus = bus

    def lxml_subelement(self, root, name, text=None, attributes=None):
        tmp = lxml.etree.SubElement(root, name)
        if text is not None:
            tmp.text = text
        if attributes is not None:
            for k, v in attributes.items():
                tmp.set(k, v)
        return tmp

    def _generate_serial_xml(self, devices):
        """
        Method to generate the serial portion of the libvirt XML.
        """
        serial = self.lxml_subelement(devices, "serial", None, {'type':'tcp'})
        self.lxml_subelement(serial, "source", None,
                             {'mode':'bind', 'host':'127.0.0.1', 'service':str(self.listen_port)})
        self.lxml_subelement(serial, "protocol", None, {'type':'raw'})
        self.lxml_subelement(serial, "target", None, {'port':'1'})

    def _generate_xml(self, bootdev, installdev, kernel=None, initrd=None,
                      cmdline=None):
        """
        Method to generate libvirt XML useful for installation.
        """
        self.log.info("Generate XML for guest %s with bootdev %s" % (self.tdl.name, bootdev))

        # top-level domain element
        domain = lxml.etree.Element("domain", type=self.libvirt_type)
        # name element
        self.lxml_subelement(domain, "name", self.tdl.name)
        # memory elements
        self.lxml_subelement(domain, "memory", str(self.install_memory))
        self.lxml_subelement(domain, "currentMemory", str(self.install_memory))
        # uuid
        self.lxml_subelement(domain, "uuid", str(self.uuid))
        # clock offset
        self.lxml_subelement(domain, "clock", None, {'offset':self.clockoffset})
        # vcpu
        self.lxml_subelement(domain, "vcpu", str(self.install_cpus))
        # features
        features = self.lxml_subelement(domain, "features")
        self.lxml_subelement(features, "acpi")
        self.lxml_subelement(features, "apic")
        self.lxml_subelement(features, "pae")
        # os
        osNode = self.lxml_subelement(domain, "os")
        self.lxml_subelement(osNode, "type", "hvm")
        if bootdev:
            self.lxml_subelement(osNode, "boot", None, {'dev':bootdev})
        if kernel:
            self.lxml_subelement(osNode, "kernel", kernel)
        if initrd:
            self.lxml_subelement(osNode, "initrd", initrd)
        if cmdline:
            self.lxml_subelement(osNode, "cmdline", cmdline)
        # poweroff, reboot, crash
        self.lxml_subelement(domain, "on_poweroff", "destroy")
        self.lxml_subelement(domain, "on_reboot", "destroy")
        self.lxml_subelement(domain, "on_crash", "destroy")
        # devices
        devices = self.lxml_subelement(domain, "devices")
        # graphics
        self.lxml_subelement(devices, "graphics", None, {'port':'-1', 'type':'vnc'})
        # network
        interface = self.lxml_subelement(devices, "interface", None, {'type':'bridge'})
        self.lxml_subelement(interface, "source", None, {'bridge':self.bridge_name})
        self.lxml_subelement(interface, "mac", None, {'address':self.macaddr})
        self.lxml_subelement(interface, "model", None, {'type':self.nicmodel})
        # input
        mousedict = {'bus':self.mousetype}
        if self.mousetype == "ps2":
            mousedict['type'] = 'mouse'
        elif self.mousetype == "usb":
            mousedict['type'] = 'tablet'
        self.lxml_subelement(devices, "input", None, mousedict)
        # serial console pseudo TTY
        console = self.lxml_subelement(devices, "serial", None, {'type':'pty'})
        self.lxml_subelement(console, "target", None, {'port':'0'})
        # serial
        self._generate_serial_xml(devices)
        # boot disk
        bootDisk = self.lxml_subelement(devices, "disk", None, {'device':'disk', 'type':'file'})
        self.lxml_subelement(bootDisk, "target", None, {'dev':self.disk_dev, 'bus':self.disk_bus})
        self.lxml_subelement(bootDisk, "source", None, {'file':self.diskimage})
        self.lxml_subelement(bootDisk, "driver", None, {'name':'qemu', 'type':self.image_type})
        # install disk (if any)
        if not installdev:
            installdev_list = []
        elif not type(installdev) is list:
            installdev_list = [installdev]
        else:
            installdev_list = installdev
        for installdev in installdev_list:
            install = self.lxml_subelement(devices, "disk", None, {'type':'file', 'device':installdev.devicetype})
            self.lxml_subelement(install, "source", None, {'file':installdev.path})
            self.lxml_subelement(install, "target", None, {'dev':installdev.bus})

        xml = lxml.etree.tostring(domain, pretty_print=True)
        self.log.debug("Generated XML:\n%s" % (xml))

        return xml

    def _internal_generate_diskimage(self, size=10, force=False,
                                     create_partition=False,
                                     image_filename=None,
                                     backing_filename=None):
        """
        Internal method to generate a diskimage.
        Set image_filename to override the default selection of self.diskimage
        Set backing_filename to force diskimage to be a writeable qcow2 snapshot
        backed by "backing_filename" which can be either a raw image or a
        qcow2 image.
        """
        if not force and os.access(self.jeos_filename, os.F_OK):
            # if we found a cached JEOS, we don't need to do anything here;
            # we'll copy the JEOS itself later on
            return

        self.log.info("Generating %dGB diskimage for %s" % (size,
                                                            self.tdl.name))

        if image_filename:
            diskimage = image_filename
        else:
            diskimage = self.diskimage
        directory = os.path.dirname(diskimage)
        filename = os.path.basename(diskimage)

        pool = lxml.etree.Element("pool", type="dir")
        self.lxml_subelement(pool, "name", "oztempdir" + str(uuid.uuid4()))
        target = self.lxml_subelement(pool, "target")
        self.lxml_subelement(target, "path", directory)
        pool_xml = lxml.etree.tostring(pool, pretty_print=True)

        vol = lxml.etree.Element("volume", type="file")
        self.lxml_subelement(vol, "name", filename)
        self.lxml_subelement(vol, "allocation", "0")
        target = self.lxml_subelement(vol, "target")
        if backing_filename:
            # Only qcow2 supports image creation using a backing file
            self.lxml_subelement(target, "format", None, {"type":"qcow2"})
        else:
            self.lxml_subelement(target, "format", None, {"type":self.image_type})
        # FIXME: this makes the permissions insecure, but is needed since
        # libvirt launches guests as qemu:qemu
        permissions = self.lxml_subelement(target, "permissions")
        self.lxml_subelement(permissions, "mode", "0666")

        capacity = size
        if backing_filename:
            # FIXME: Revisit as BZ 958510 evolves
            # At the moment libvirt forces us to specify a size rather than
            # assuming we want to inherit the size of our backing file.
            # It may be possible to avoid this inspection step if libvirt
            # allows creation without an explicit capacity element.
            qcow_size = oz.ozutil.check_qcow_size(backing_filename)
            if qcow_size:
                capacity = qcow_size / 1024 / 1024 / 1024
                backing_format = 'qcow2'
            else:
                capacity = os.path.getsize(backing_filename) / 1024 / 1024 / 1024
                backing_format = 'raw'
            backing = self.lxml_subelement(vol, "backingStore")
            self.lxml_subelement(backing, "path", backing_filename)
            self.lxml_subelement(backing, "format", None,
                                 {"type":backing_format})

        self.lxml_subelement(vol, "capacity", str(capacity), {'unit':'G'})
        vol_xml = lxml.etree.tostring(vol, pretty_print=True)

        # sigh.  Yes, this is racy; if a pool is defined during this loop, we
        # might miss it.  I'm not quite sure how to do it better, and in any
        # case we don't expect that to happen often
        started = False
        found = False
        for poolname in self.libvirt_conn.listDefinedStoragePools() + self.libvirt_conn.listStoragePools():
            pool = self.libvirt_conn.storagePoolLookupByName(poolname)
            doc = lxml.etree.fromstring(pool.XMLDesc(0))
            res = doc.xpath('/pool/target/path')
            if len(res) != 1:
                continue
            if res[0].text == directory:
                # OK, this pool manages that directory; make sure it is running
                found = True
                if not pool.isActive():
                    pool.create(0)
                    started = True
                break

        if not found:
            pool = self.libvirt_conn.storagePoolCreateXML(pool_xml, 0)
            started = True

        pool.refresh(0)

        # this is a bit complicated, because of the cases that can
        # happen.  The cases are:
        #
        # 1.  The volume did not exist.  In this case, storageVolLookupByName()
        #     throws an exception, which we just ignore.  We then go on to
        #     create the volume
        # 2.  The volume did exist.  In this case, storageVolLookupByName()
        #     returns a valid volume object, and then we delete the volume
        try:
            try:
                vol = pool.storageVolLookupByName(filename)
                vol.delete(0)
            except libvirt.libvirtError as e:
                if e.get_error_code() != libvirt.VIR_ERR_NO_STORAGE_VOL:
                    raise

            try:
                pool.createXML(vol_xml, 0)
            except libvirt.libvirtError as e:
                raise
        finally:
            if started:
                pool.destroy()

        if create_partition and backing_filename:
            self.log.warning("Asked to create partition against a copy-on-write snapshot - ignoring")
        elif create_partition:
            g_handle = guestfs.GuestFS()
            g_handle.add_drive_opts(self.diskimage, format=self.image_type, readonly = 0)
            g_handle.launch()
            devices = g_handle.list_devices()
            g_handle.part_init(devices[0], "msdos")
            g_handle.part_add(devices[0], 'p', 1, 2)
            g_handle.close()

    def generate_diskimage(self, size=10, force=False):
        """
        Method to generate a diskimage.  By default, a blank diskimage of
        10GB will be created; the caller can override this with the size
        parameter, specified in GB.  If force is False (the default), then
        a diskimage will not be created if a cached JEOS is found.  If
        force is True, a diskimage will be created regardless of whether a
        cached JEOS exists.  See the oz-install man page for more
        information about JEOS caching.
        """
        return self._internal_generate_diskimage(size, force, False)

    def _get_disks_and_interfaces(self, libvirt_dom):
        """
        Method to figure out the disks and interfaces attached to a domain.
        The method returns two lists: the first is a list of disk devices (like
        hda, hdb, etc), and the second is a list of network devices (like vnet0,
        vnet1, etc).
        """
        doc = lxml.etree.fromstring(libvirt_dom.XMLDesc(0))
        disktargets = doc.xpath("/domain/devices/disk/target")
        if len(disktargets) < 1:
            raise oz.OzException.OzException("Could not find disk target")
        disks = []
        for target in disktargets:
            disks.append(target.get('dev'))
        if not disks:
            raise oz.OzException.OzException("Could not find disk target device")
        inttargets = doc.xpath("/domain/devices/interface/target")
        if len(inttargets) < 1:
            raise oz.OzException.OzException("Could not find interface target")
        interfaces = []
        for target in inttargets:
            interfaces.append(target.get('dev'))
        if not interfaces:
            raise oz.OzException.OzException("Could not find interface target device")

        return disks, interfaces

    def _get_disk_and_net_activity(self, libvirt_dom, disks, interfaces):
        """
        Method to collect the disk and network activity by the domain.  The
        method returns two numbers: the first is the sum of all disk activity
        from all disks, and the second is the sum of all network traffic from
        all network devices.
        """
        total_disk_req = 0
        for dev in disks:
            rd_req, rd_bytes, wr_req, wr_bytes, errs = libvirt_dom.blockStats(dev)
            total_disk_req += rd_req + wr_req

        total_net_bytes = 0
        for dev in interfaces:
            rx_bytes, rx_packets, rx_errs, rx_drop, tx_bytes, tx_packets, tx_errs, tx_drop = libvirt_dom.interfaceStats(dev)
            total_net_bytes += rx_bytes + tx_bytes

        return total_disk_req, total_net_bytes

    def _wait_for_clean_shutdown(self, libvirt_dom, saved_exception):
        """
        Internal method to wait for a clean shutdown of a libvirt domain that
        is suspected to have cleanly quit.  If that domain did cleanly quit,
        then we will hit a libvirt VIR_ERR_NO_DOMAIN exception on the very
        first libvirt call and return with no delay.  If no exception, or some
        other exception occurs, we wait up to 10 seconds for the domain to go
        away.  If the domain is still there after 10 seconds then we raise the
        original exception that was passed in.
        """
        count = 10
        while count > 0:
            self.log.debug("Waiting for %s to complete shutdown, %d/10" % (self.tdl.name, count))
            try:
                libvirt_dom.info()
            except libvirt.libvirtError as e:
                if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                    break
            count -= 1
            time.sleep(1)

        if count == 0:
            # Got something other than the expected exception even after 10
            # seconds - re-raise
            if saved_exception:
                self.log.debug("Libvirt Domain Info Failed:")
                self.log.debug(" code is %d" % saved_exception.get_error_code())
                self.log.debug(" domain is %d" % saved_exception.get_error_domain())
                self.log.debug(" message is %s" % saved_exception.get_error_message())
                self.log.debug(" level is %d" % saved_exception.get_error_level())
                self.log.debug(" str1 is %s" % saved_exception.get_str1())
                self.log.debug(" str2 is %s" % saved_exception.get_str2())
                self.log.debug(" str3 is %s" % saved_exception.get_str3())
                self.log.debug(" int1 is %d" % saved_exception.get_int1())
                self.log.debug(" int2 is %d" % saved_exception.get_int2())
                raise saved_exception
            else:
                # the passed in exception was None, just raise a generic error
                raise oz.OzException.OzException("Unknown libvirt error")

    def _wait_for_install_finish(self, libvirt_dom, count,
                                 inactivity_timeout=300):
        """
        Method to wait for an installation to finish.  This will wait around
        until either the VM has gone away (at which point it is assumed the
        install was successful), or until the timeout is reached (at which
        point it is assumed the install failed and raise an exception).
        """

        disks, interfaces = self._get_disks_and_interfaces(libvirt_dom)

        last_disk_activity = 0
        last_network_activity = 0
        inactivity_countdown = inactivity_timeout
        origcount = count
        saved_exception = None
        while count > 0 and inactivity_countdown > 0:
            if count % 10 == 0:
                self.log.debug("Waiting for %s to finish installing, %d/%d" % (self.tdl.name, count, origcount))
            try:
                total_disk_req, total_net_bytes = self._get_disk_and_net_activity(libvirt_dom, disks, interfaces)
            except libvirt.libvirtError as e:
                # we save the exception here because we want to raise it later
                # if this was a "real" exception
                saved_exception = e
                break

            # rd_req and wr_req are the *total* number of disk read requests and
            # write requests ever made for this domain.  Similarly rd_bytes and
            # wr_bytes are the total number of network bytes read or written
            # for this domain

            # we define activity as having done a read or write request on the
            # install disk, or having done at least 4KB of network transfers in
            # the last second.  The thinking is that if the installer is putting
            # bits on disk, there will be disk activity, so we should keep
            # waiting.  On the other hand, the installer might be downloading
            # bits to eventually install on disk, so we look for network
            # activity as well.  We say that transfers of at least 4KB must be
            # made, however, to try to reduce false positives from things like
            # ARP requests

            if (total_disk_req == last_disk_activity) and (total_net_bytes < (last_network_activity + 4096)):
                # if we saw no read or write requests since the last iteration,
                # decrement our activity timer
                inactivity_countdown -= 1
            else:
                # if we did see some activity, then we can reset the timer
                inactivity_countdown = inactivity_timeout

            last_disk_activity = total_disk_req
            last_network_activity = total_net_bytes
            count -= 1
            time.sleep(1)

        # We get here because of a libvirt exception, an absolute timeout, or
        # an I/O timeout; we sort this out below
        if count == 0:
            # if we timed out, then let's make sure to take a screenshot.
            screenshot_text = self._capture_screenshot(libvirt_dom)
            raise oz.OzException.OzException("Timed out waiting for install to finish.  %s" % (screenshot_text))
        elif inactivity_countdown == 0:
            # if we saw no disk or network activity in the countdown window,
            # we presume the install has hung.  Fail here
            screenshot_text = self._capture_screenshot(libvirt_dom)
            raise oz.OzException.OzException("No disk activity in %d seconds, failing.  %s" % (inactivity_timeout, screenshot_text))

        # We get here only if we got a libvirt exception
        self._wait_for_clean_shutdown(libvirt_dom, saved_exception)

        self.log.info("Install of %s succeeded" % (self.tdl.name))

    def _wait_for_guest_shutdown(self, libvirt_dom, count=90):
        """
        Method to wait around for orderly shutdown of a running guest.  Returns
        True if the guest shutdown in the specified time, False otherwise.
        """
        origcount = count
        saved_exception = None
        while count > 0:
            if count % 10 == 0:
                self.log.debug("Waiting for %s to shutdown, %d/%d" % (self.tdl.name, count, origcount))
            try:
                libvirt_dom.info()
            except libvirt.libvirtError as e:
                saved_exception = e
                break
            count -= 1
            time.sleep(1)

        # Timed Out
        if count == 0:
            return False

        # We get here only if we got a libvirt exception
        self._wait_for_clean_shutdown(libvirt_dom, saved_exception)

        return True

    def _get_csums(self, original_url, outdir, outputfd):
        """
        Internal method to fetch the checksum file and compute the checksum
        on the downloaded data.
        """
        if self.tdl.iso_md5_url:
            url = self.tdl.iso_md5_url
            hashname = 'md5'
        elif self.tdl.iso_sha1_url:
            url = self.tdl.iso_sha1_url
            hashname = 'sha1'
        elif self.tdl.iso_sha256_url:
            url = self.tdl.iso_sha256_url
            hashname = 'sha256'
        else:
            return True

        originalname = os.path.basename(urlparse.urlparse(original_url)[2])

        csumname = os.path.join(outdir,
                                self.tdl.distro + self.tdl.update + self.tdl.arch + "-CHECKSUM")
        csumfd = os.open(csumname, os.O_WRONLY|os.O_CREAT|os.O_TRUNC)

        try:
            self.log.debug("Attempting to get the lock for %s" % (csumname))
            fcntl.lockf(csumfd, fcntl.LOCK_EX)
            self.log.debug("Got the lock, doing the download")

            self.log.debug("Checksum requested, fetching %s file" % (hashname))
            oz.ozutil.http_download_file(url, csumfd, False, self.log)
        finally:
            os.close(csumfd)

        upstream_sum = getattr(oz.ozutil,
                               'get_' + hashname + 'sum_from_file')(csumname, originalname)

        os.unlink(csumname)

        if not upstream_sum:
            raise oz.OzException.OzException("Could not find checksum for original file " + originalname)

        self.log.debug("Calculating checksum of downloaded file")
        os.lseek(outputfd, 0, os.SEEK_SET)

        local_sum = getattr(hashlib, hashname)()

        buf = oz.ozutil.read_bytes_from_fd(outputfd, 4096)
        while buf != '':
            local_sum.update(buf)
            buf = oz.ozutil.read_bytes_from_fd(outputfd, 4096)

        return local_sum.hexdigest() == upstream_sum

    def _get_original_media(self, url, output, force_download):
        """
        Method to fetch the original media from url.  If the media is already
        cached locally, the cached copy will be used instead.
        """
        self.log.info("Fetching the original media")

        outdir = os.path.dirname(output)
        oz.ozutil.mkdir_p(outdir)

        fd = os.open(output, os.O_RDWR|os.O_CREAT)

        # from this point forward, we need to close fd on success or failure
        try:
            self.log.debug("Attempting to get the lock for %s" % (output))
            fcntl.lockf(fd, fcntl.LOCK_EX)
            self.log.debug("Got the lock, doing the download")

            # if we reach here, the open and lock succeeded and we can download

            info = oz.ozutil.http_get_header(url)

            if not 'HTTP-Code' in info or info['HTTP-Code'] >= 400 or not 'Content-Length' in info or info['Content-Length'] < 0:
                raise oz.OzException.OzException("Could not reach destination to fetch boot media")

            content_length = int(info['Content-Length'])

            if content_length == 0:
                raise oz.OzException.OzException("Install media of 0 size detected, something is wrong")

            if not force_download:
                if content_length == os.fstat(fd)[stat.ST_SIZE]:
                    if self._get_csums(url, outdir, fd):
                        self.log.info("Original install media available, using cached version")
                        return
                    else:
                        self.log.info("Original available, but checksum mis-match; re-downloading")

            # before fetching everything, make sure that we have enough
            # space on the filesystem to store the data we are about to download
            devdata = os.statvfs(outdir)
            if (devdata.f_bsize*devdata.f_bavail) < content_length:
                raise oz.OzException.OzException("Not enough room on %s for install media" % (outdir))

            # at this point we know we are going to download something.  Make
            # sure to truncate the file so no stale data is left on the end
            os.ftruncate(fd, 0)

            self.log.info("Fetching the original install media from %s" % (url))
            oz.ozutil.http_download_file(url, fd, True, self.log)

            filesize = os.fstat(fd)[stat.ST_SIZE]

            if filesize != content_length:
                # if the length we downloaded is not the same as what we
                # originally saw from the headers, something went wrong
                raise oz.OzException.OzException("Expected to download %d bytes, downloaded %d" % (content_length, filesize))

            if not self._get_csums(url, outdir, fd):
                raise oz.OzException.OzException("Checksum for downloaded file does not match!")
        finally:
            os.close(fd)

    def _capture_screenshot(self, libvirt_dom):
        """
        Method to capture a screenshot of the VM.
        """
        oz.ozutil.mkdir_p(self.screenshot_dir)
        # create a new stream
        st = libvirt_dom.connect().newStream(0)

        # start the screenshot
        mimetype = libvirt_dom.screenshot(st, 0, 0)

        if mimetype == "image/x-portable-pixmap":
            ext = ".ppm"
        elif mimetype == "image/png":
            ext = ".png"
        else:
            return "Unknown screenshot type, failed to take screenshot"

        try:
            screenshot = os.path.realpath(os.path.join(self.screenshot_dir,
                                                       self.tdl.name + "-" + str(time.time()) + ext))

            def sink(stream, buf, opaque):
                """
                Function that is called back from the libvirt stream.
                """
                # opaque is the open file object
                return oz.ozutil.write_bytes_to_fd(opaque, buf)

            fd = os.open(screenshot, os.O_RDWR|os.O_CREAT)
            try:
                st.recvAll(sink, fd)
            finally:
                os.close(fd)

            st.finish()
            text = "Check screenshot at %s for more detail" % (screenshot)
        except:
            text = "Failed to take screenshot"

        return text

    def _guestfs_handle_setup(self, libvirt_xml):
        """
        Method to setup a guestfs handle to the guest disks.
        """
        input_doc = lxml.etree.fromstring(libvirt_xml)
        namenode = input_doc.xpath('/domain/name')
        if len(namenode) != 1:
            raise oz.OzException.OzException("invalid libvirt XML with no name")
        input_name = namenode[0].text
        disks = input_doc.xpath('/domain/devices/disk')
        if len(disks) != 1:
            self.log.warning("Oz given a libvirt domain with more than 1 disk; using the first one parsed")
        source = disks[0].xpath('source')
        if len(source) != 1:
            raise oz.OzException.OzException("invalid <disk> entry without a source")
        input_disk = source[0].get('file')
        driver = disks[0].xpath('driver')
        if len(driver) == 0:
            input_disk_type = 'raw'
        elif len(driver) == 1:
            input_disk_type = driver[0].get('type')
        else:
            raise oz.OzException.OzException("invalid <disk> entry without a driver")

        for domid in self.libvirt_conn.listDomainsID():
            try:
                doc = lxml.etree.fromstring(self.libvirt_conn.lookupByID(domid).XMLDesc(0))
            except:
                self.log.debug("Could not get XML for domain ID (%s) - it may have disappeared (continuing)" % (domid))
                continue

            namenode = doc.xpath('/domain/name')
            if len(namenode) != 1:
                # hm, odd, a domain without a name?
                raise oz.OzException.OzException("Saw a domain without a name, something weird is going on")
            if input_name == namenode[0].text:
                raise oz.OzException.OzException("Cannot setup ICICLE generation on a running guest")
            disks = doc.xpath('/domain/devices/disk')
            if len(disks) < 1:
                # odd, a domain without a disk, but don't worry about it
                continue
            for guestdisk in disks:
                for source in guestdisk.xpath("source"):
                    # FIXME: this will only work for files; we can make it work
                    # for other things by following something like:
                    # http://git.annexia.org/?p=libguestfs.git;a=blob;f=src/virt.c;h=2c6be3c6a2392ab8242d1f4cee9c0d1445844385;hb=HEAD#l169
                    filename = str(source.get('file'))
                    if filename == input_disk:
                        raise oz.OzException.OzException("Cannot setup ICICLE generation on a running disk")


        self.log.info("Setting up guestfs handle for %s" % (self.tdl.name))
        g = guestfs.GuestFS()

        self.log.debug("Adding disk image %s" % (input_disk))
        # NOTE: we use "add_drive_opts" here so we can specify the type
        # of the diskimage.  Otherwise it might be possible for an attacker
        # to fool libguestfs with a specially-crafted diskimage that looks
        # like a qcow2 disk (thanks to rjones for the tip)
        g.add_drive_opts(input_disk, format=input_disk_type)

        self.log.debug("Launching guestfs")
        g.launch()

        self.log.debug("Inspecting guest OS")
        roots = g.inspect_os()

        if len(roots) == 0:
            raise oz.OzException.OzException("No operating systems found on the disk")

        self.log.debug("Getting mountpoints")
        for root in roots:
            self.log.debug("Root device: %s" % root)

            # the problem here is that the list of mountpoints returned by
            # inspect_get_mountpoints is in no particular order.  So if the
            # diskimage contains /usr and /usr/local on different devices,
            # but /usr/local happened to come first in the listing, the
            # devices would get mapped improperly.  The clever solution here is
            # to sort the mount paths by length; this will ensure that they
            # are mounted in the right order.  Thanks to rjones for the hint,
            # and the example code that comes from the libguestfs.org python
            # example page.
            mps = g.inspect_get_mountpoints(root)
            def _compare(a, b):
                """
                Method to sort disks by length.
                """
                if len(a[0]) > len(b[0]):
                    return 1
                elif len(a[0]) == len(b[0]):
                    return 0
                else:
                    return -1
            mps.sort(_compare)
            for mp_dev in mps:
                try:
                    g.mount_options('', mp_dev[1], mp_dev[0])
                except:
                    if mp_dev[0] == '/':
                        # If we cannot mount root, we may as well give up
                        raise
                    else:
                        # some custom guests may have fstab content with
                        # "nofail" as a mount option.  For example, images
                        # built for EC2 with ephemeral mappings.  These
                        # fail at this point.  Allow things to continue.
                        # Profound failures will trigger later on during
                        # the process.
                        self.log.warning("Unable to mount (%s) on (%s) - trying to continue" % (mp_dev[1], mp_dev[0]))
        return g

    def _guestfs_remove_if_exists(self, g_handle, path):
        """
        Method to remove a file if it exists in the disk image.
        """
        if g_handle.exists(path):
            g_handle.rm_rf(path)

    def _guestfs_move_if_exists(self, g_handle, orig_path, replace_path):
        """
        Method to move a file if it exists in the disk image.
        """
        if g_handle.exists(orig_path):
            g_handle.mv(orig_path, replace_path)

    def _guestfs_path_backup(self, g_handle, orig):
        """
        Method to backup a file in the disk image.
        """
        self._guestfs_move_if_exists(g_handle, orig, orig + ".ozbackup")

    def _guestfs_path_restore(self, g_handle, orig):
        """
        Method to restore a backup file in the disk image.
        """
        backup = orig + ".ozbackup"
        self._guestfs_remove_if_exists(g_handle, orig)
        self._guestfs_move_if_exists(g_handle, backup, orig)

    def _guestfs_handle_cleanup(self, g_handle):
        """
        Method to cleanup a handle previously setup by __guestfs_handle_setup.
        """
        self.log.info("Cleaning up guestfs handle for %s" % (self.tdl.name))
        self.log.debug("Syncing")
        g_handle.sync()

        self.log.debug("Unmounting all")
        g_handle.umount_all()

    def _modify_libvirt_xml_for_serial(self, libvirt_xml):
        """
        Internal method to take input libvirt XML (which may have been provided
        by the user) and add an appropriate serial section so that guest
        announcement works properly.
        """
        input_doc = lxml.etree.fromstring(libvirt_xml)
        serialNode = input_doc.xpath("/domain/devices/serial")

        # we first go looking through the existing <serial> elements (if any);
        # if any exist on port 1, we delete it from the working XML and re-add
        # it below
        for serial in serialNode:
            target = serial.xpath('target')
            if len(target) != 1:
                raise oz.OzException.OzException("libvirt XML has a serial port with %d target(s), it is invalid" % (len(target)))
            if target[0].get('port') == "1":
                serial.getparent().remove(serial)
                break

        # at this point, the XML should be clean of any serial port=1 entries
        # and we can add the one we want
        devices = input_doc.xpath("/domain/devices")
        devlen = len(devices)
        if devlen == 0:
            raise oz.OzException.OzException("No devices section specified, something is wrong with the libvirt XML")
        elif devlen > 1:
            raise oz.OzException.OzException("%d devices sections specified, something is wrong with the libvirt XML" % (devlen))

        self._generate_serial_xml(devices[0])

        xml = lxml.etree.tostring(input_doc, pretty_print=True)
        self.log.debug("Generated XML:\n%s" % (xml))
        return xml

    def _modify_libvirt_xml_diskimage(self, libvirt_xml, new_diskimage,
                                      image_type):
        """
        Internal method to take input libvirt XML and replace the existing disk
        image details with a new disk image file and, potentially, disk image
        type.  Used in safe ICICLE generation to replace the "real" disk image
        file with a temporary writeable snapshot.
        """
        self.log.debug("Modifying libvirt XML to use disk image (%s) of type (%s)" % (new_diskimage, image_type))
        input_doc = lxml.etree.fromstring(libvirt_xml)
        disks = input_doc.xpath("/domain/devices/disk")
        if len(disks) != 1:
            self.log.warning("Oz given a libvirt domain with more than 1 disk; using the first one parsed")

        source = disks[0].xpath('source')
        if len(source) != 1:
            raise oz.OzException.OzException("invalid <disk> entry without a source")
        source[0].set('file', new_diskimage)

        driver = disks[0].xpath('driver')
        # at the time this function was added, all boot disk device stanzas
        # have a driver section - even raw images
        if len(driver) == 1:
            driver[0].set('type', image_type)
        else:
            raise oz.OzException.OzException("Found a disk with an unexpected number of driver sections")

        xml = lxml.etree.tostring(input_doc, pretty_print=True)
        self.log.debug("Generated XML:\n%s" % (xml))
        return xml

    def _wait_for_guest_boot(self, libvirt_dom):
        """
        Method to wait around for a guest to boot.  Orderly guests will boot
        up and announce their presence via a TCP message; if that happens within
        the timeout, this method returns the IP address of the guest.  If that
        doesn't happen an exception is raised.
        """
        self.log.info("Waiting for guest %s to boot" % (self.tdl.name))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.settimeout(1)
            sock.connect(('127.0.0.1', self.listen_port))

            addr = None
            count = 300
            data = ''
            while count > 0:
                do_sleep = True
                if count % 10 == 0:
                    self.log.debug("Waiting for guest %s to boot, %d/300" % (self.tdl.name, count))
                try:
                    # note that we have to build the data up here, since there
                    # is no guarantee that we will get the whole write in one go
                    data += sock.recv(100)
                except socket.timeout:
                    # the socket times out after 1 second.  We can just fall
                    # through to the below code because it is a noop, *except* that
                    # we don't want to sleep.  Set the flag
                    do_sleep = False

                # OK, we got data back from the socket.  Check to see if it is
                # is what we expect; essentially, some up-front garbage,
                # followed by a !<ip>,<uuid>!
                # Exclude ! from the wildcard to avoid errors when receiving two
                # announce messages in the same string
                match = re.search("!([^!]*?,[^!]*?)!$", data)
                if match is not None:
                    if len(match.groups()) != 1:
                        raise oz.OzException.OzException("Guest checked in with no data")
                    split = match.group(1).split(',')
                    if len(split) != 2:
                        raise oz.OzException.OzException("Guest checked in with bogus data")
                    addr = split[0]
                    uuidstr = split[1]
                    try:
                        # use socket.inet_aton() to validate the IP address
                        socket.inet_aton(addr)
                    except socket.error:
                        raise oz.OzException.OzException("Guest checked in with invalid IP address")

                    if uuidstr != str(self.uuid):
                        raise oz.OzException.OzException("Guest checked in with unknown UUID")
                    break

                # if the data we got didn't match, we need to continue waiting.
                # before going to sleep, make sure that the domain is still
                # around
                libvirt_dom.info()
                if do_sleep:
                    time.sleep(1)
                count -= 1
        finally:
            sock.close()

        if addr is None:
            raise oz.OzException.OzException("Timed out waiting for guest to boot")

        self.log.debug("IP address of guest is %s" % (addr))

        return addr

    def _output_icicle_xml(self, lines, description, extra=None):
        """
        Generate ICICLE XML based on the data supplied.  The parameter 'lines'
        is expected to be an list of strings, with one package per list item.
        The parameter 'description' is a description of the guest.  The
        parameter 'extra' is an optional one that describes any additional
        information the user wanted in the ICICLE output.
        """
        icicle = lxml.etree.Element("icicle")
        if description is not None:
            self.lxml_subelement(icicle, "description", description)
        packages = self.lxml_subelement(icicle, "packages")

        for index, line in enumerate(lines):
            if line == "":
                continue
            package = self.lxml_subelement(packages, "package", None,
                                           {'name':line})
            if extra is not None:
                self.lxml_subelement(package, "extra", extra[index])

        return lxml.etree.tostring(icicle, pretty_print=True)

    def _check_url(self, iso=True, url=True):
        """
        Method to check that a TDL URL meets the requirements for a particular
        operating system.
        """

        # this method is *slightly* odd in that it references ISOs from the
        # generic Guest class.  However, the installtype comes from the user
        # TDL, which means that they could have specified an ISO installtype for
        # a floppy guest (for instance).  Since we internally always set
        # iso=False for floppy guests, this will raise an appropriate error

        if iso and self.tdl.installtype == 'iso':
            url = self.tdl.iso
        elif url and self.tdl.installtype == 'url':
            url = self.tdl.url

            # when doing URL installs, we can't allow localhost URLs (the URL
            # will be embedded into the installer, so the install is guaranteed
            # to fail with localhost URLs).  Disallow them here
            if urlparse.urlparse(url)[1] in ["localhost", "127.0.0.1",
                                             "localhost.localdomain"]:
                raise oz.OzException.OzException("Can not use localhost for an URL based install")
        else:
            if iso and url:
                raise oz.OzException.OzException("%s installs must be done via url or iso" % (self.tdl.distro))
            elif iso:
                raise oz.OzException.OzException("%s installs must be done via iso" % (self.tdl.distro))
            elif url:
                raise oz.OzException.OzException("%s installs must be done via url" % (self.tdl.distro))
            else:
                raise oz.OzException.OzException("Unknown error occurred while determining install URL")

        return url

    def _generate_openssh_key(self, privname):
        """
        Method to generate an OpenSSH compatible public/private keypair.
        """
        self.log.info("Generating new openssh key")
        pubname = privname + ".pub"
        if os.access(privname, os.F_OK) and not os.access(pubname, os.F_OK):
            # hm, private key exists but not public?  We have to regenerate
            os.unlink(privname)

        if not os.access(privname, os.F_OK) and os.access(pubname, os.F_OK):
            # hm, public key exists but not private?  We have to regenerate
            os.unlink(pubname)

        # when we get here, either both the private and public key exist, or
        # neither exist.  If they don't exist, generate them
        if not os.access(privname, os.F_OK) and not os.access(pubname, os.F_OK):
            def _null_callback(p, n, out):
                """
                Method to silence the default M2Crypto.RSA.gen_key output.
                """
                pass

            pubname = privname + '.pub'

            key = M2Crypto.RSA.gen_key(2048, 65537, _null_callback)

            # this is the binary public key, in ssh "BN" (BigNumber) MPI format.
            # The ssh BN MPI format consists of 4 bytes that describe the length
            # of the following data, followed by the data itself in big-endian
            # format.  The start of the string is 0x0007, which represent the 7
            # bytes following that make up 'ssh-rsa'.  The key exponent and
            # modulus as fetched out of M2Crypto are already in MPI format, so
            # we can just use them as-is.  We then have to base64 encode the
            # result, add a little header information, and then we have a
            # full public key.
            pubkey = '\x00\x00\x00\x07' + 'ssh-rsa' + key.e + key.n

            username = os.getlogin()
            hostname = os.uname()[1]
            keystring = 'ssh-rsa %s %s@%s\n' % (base64.b64encode(pubkey),
                                                username, hostname)

            key.save_key(privname, cipher=None)
            os.chmod(privname, 0o600)
            with open(pubname, 'w') as f:
                f.write(keystring)
            os.chmod(pubname, 0o644)

class CDGuest(Guest):
    """
    Class for guest installation via ISO.
    """
    class _PrimaryVolumeDescriptor(object):
        """
        Class to hold information about a CD's Primary Volume Descriptor.
        """
        def __init__(self, version, sysid, volid, space_size, set_size, seqnum):
            self.version = version
            self.system_identifier = sysid
            self.volume_identifier = volid
            self.space_size = space_size
            self.set_size = set_size
            self.seqnum = seqnum

    def __init__(self, tdl, config, auto, output_disk, nicmodel, clockoffset,
                 mousetype, diskbus, iso_allowed, url_allowed, macaddress):
        Guest.__init__(self, tdl, config, auto, output_disk, nicmodel,
                       clockoffset, mousetype, diskbus, iso_allowed,
                       url_allowed, macaddress)

        self.orig_iso = os.path.join(self.data_dir, "isos",
                                     self.tdl.distro + self.tdl.update + self.tdl.arch + "-" + self.tdl.installtype + ".iso")
        self.modified_iso_cache = os.path.join(self.data_dir, "isos",
                                               self.tdl.distro + self.tdl.update + self.tdl.arch + "-" + self.tdl.installtype + "-oz.iso")
        self.output_iso = os.path.join(self.output_dir,
                                       self.tdl.name + "-" + self.tdl.installtype + "-oz.iso")
        self.iso_contents = os.path.join(self.data_dir, "isocontent",
                                         self.tdl.name + "-" + self.tdl.installtype)

        self.log.debug("Original ISO path: %s" % self.orig_iso)
        self.log.debug("Modified ISO cache: %s" % self.modified_iso_cache)
        self.log.debug("Output ISO path: %s" % self.output_iso)
        self.log.debug("ISO content path: %s" % self.iso_contents)

    def _get_original_iso(self, isourl, force_download):
        """
        Method to fetch the original ISO for an operating system.
        """
        self._get_original_media(isourl, self.orig_iso, force_download)

    def _copy_iso(self):
        """
        Method to copy the data out of an ISO onto the local filesystem.
        """
        self.log.info("Copying ISO contents for modification")
        try:
            shutil.rmtree(self.iso_contents)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
        os.makedirs(self.iso_contents)

        self.log.info("Setting up guestfs handle for %s" % (self.tdl.name))
        gfs = guestfs.GuestFS()
        self.log.debug("Adding ISO image %s" % (self.orig_iso))
        gfs.add_drive_opts(self.orig_iso, readonly=1, format='raw')
        self.log.debug("Launching guestfs")
        gfs.launch()
        try:
            self.log.debug("Mounting ISO")
            gfs.mount_options('ro', "/dev/sda", "/")

            self.log.debug("Checking if there is enough space on the filesystem")
            isostat = gfs.statvfs("/")
            outputstat = os.statvfs(self.iso_contents)
            if (outputstat.f_bsize*outputstat.f_bavail) < (isostat['blocks']*isostat['bsize']):
                raise oz.OzException.OzException("Not enough room on %s to extract install media" % (self.iso_contents))

            self.log.debug("Extracting ISO contents")
            current = os.getcwd()
            os.chdir(self.iso_contents)
            try:
                rd, wr = os.pipe()

                try:
                    # NOTE: it is very, very important that we use temporary
                    # files for collecting stdout and stderr here.  There is a
                    # nasty bug in python subprocess; if your process produces
                    # more than 64k of data on an fd that is using
                    # subprocess.PIPE, the whole thing will hang. To avoid
                    # this, we use temporary fds to capture the data
                    stdouttmp = tempfile.TemporaryFile()
                    stderrtmp = tempfile.TemporaryFile()

                    try:
                        tar = subprocess.Popen(["tar", "-x", "-v"], stdin=rd,
                                               stdout=stdouttmp,
                                               stderr=stderrtmp)
                        try:
                            gfs.tar_out("/", "/dev/fd/%d" % wr)
                        except:
                            # we need this here if gfs.tar_out throws an
                            # exception.  In that case, we need to manually
                            # kill off the tar process and re-raise the
                            # exception, otherwise we hang forever
                            tar.kill()
                            raise

                        # FIXME: we really should check tar.poll() here to get
                        # the return code, and print out stdout and stderr if
                        # we fail.  This will make debugging problems easier
                    finally:
                        stdouttmp.close()
                        stderrtmp.close()
                finally:
                    os.close(rd)
                    os.close(wr)

                # since we extracted from an ISO, there are no write bits
                # on any of the directories.  Fix that here
                for dirpath, dirnames, filenames in os.walk(self.iso_contents):
                    st = os.stat(dirpath)
                    os.chmod(dirpath, st.st_mode|stat.S_IWUSR)
                    for name in filenames:
                        fullpath = os.path.join(dirpath, name)
                        try:
                            # if there are broken symlinks in the ISO,
                            # then the below might fail.  This probably
                            # isn't fatal, so just allow it and go on
                            st = os.stat(fullpath)
                            os.chmod(fullpath, st.st_mode|stat.S_IWUSR)
                        except OSError as err:
                            if err.errno != errno.ENOENT:
                                raise
            finally:
                os.chdir(current)
        finally:
            gfs.sync()
            gfs.umount_all()
            gfs.kill_subprocess()

    def _get_primary_volume_descriptor(self, cdfd):
        """
        Method to extract the primary volume descriptor from a CD.
        """
        # check out the primary volume descriptor to make sure it is sane
        cdfd.seek(16*2048)
        fmt = "=B5sBB32s32sQLL32sHHHH"
        (desc_type, identifier, version, unused1, system_identifier, volume_identifier, unused2, space_size_le, space_size_be, unused3, set_size_le, set_size_be, seqnum_le, seqnum_be) = struct.unpack(fmt, cdfd.read(struct.calcsize(fmt)))

        if desc_type != 0x1:
            raise oz.OzException.OzException("Invalid primary volume descriptor")
        if identifier != "CD001":
            raise oz.OzException.OzException("invalid CD isoIdentification")
        if unused1 != 0x0:
            raise oz.OzException.OzException("data in unused field")
        if unused2 != 0x0:
            raise oz.OzException.OzException("data in 2nd unused field")

        return self._PrimaryVolumeDescriptor(version, system_identifier,
                                             volume_identifier, space_size_le,
                                             set_size_le, seqnum_le)

    def _geteltorito(self, cdfile, outfile):
        """
        Method to extract the El-Torito boot sector off of a CD and write it
        to a file.
        """
        if cdfile is None:
            raise oz.OzException.OzException("input iso is None")
        if outfile is None:
            raise oz.OzException.OzException("output file is None")

        cdfd = open(cdfile, "r")

        self._get_primary_volume_descriptor(cdfd)

        # the 17th sector contains the boot specification and the offset of the
        # boot sector
        cdfd.seek(17*2048)

        # NOTE: With "native" alignment (the default for struct), there is
        # some padding that happens that causes the unpacking to fail.
        # Instead we force "standard" alignment, which has no padding
        fmt = "=B5sB23s41sI"
        (boot, isoIdent, version, toritoSpec, unused, bootP) = struct.unpack(fmt,
                                                                             cdfd.read(struct.calcsize(fmt)))
        if boot != 0x0:
            raise oz.OzException.OzException("invalid CD boot sector")
        if isoIdent != "CD001":
            raise oz.OzException.OzException("invalid CD isoIdentification")
        if version != 0x1:
            raise oz.OzException.OzException("invalid CD version")
        if toritoSpec != "EL TORITO SPECIFICATION":
            raise oz.OzException.OzException("invalid CD torito specification")

        # OK, this looks like a bootable CD.  Seek to the boot sector, and
        # look for the header, 0x55, and 0xaa in the first 32 bytes
        cdfd.seek(bootP*2048)
        fmt = "=BBH24sHBB"
        bootdata = cdfd.read(struct.calcsize(fmt))
        (header, platform, unused, manu, unused2, five, aa) = struct.unpack(fmt,
                                                                            bootdata)
        if header != 0x1:
            raise oz.OzException.OzException("invalid CD boot sector header")
        if platform != 0x0 and platform != 0x1 and platform != 0x2:
            raise oz.OzException.OzException("invalid CD boot sector platform")
        if unused != 0x0:
            raise oz.OzException.OzException("invalid CD unused boot sector field")
        if five != 0x55 or aa != 0xaa:
            raise oz.OzException.OzException("invalid CD boot sector footer")

        def _checksum(data):
            """
            Method to compute the checksum on the ISO.  Note that this is *not*
            a 1's complement checksum; when an addition overflows, the carry
            bit is discarded, not added to the end.
            """
            s = 0
            for i in range(0, len(data), 2):
                w = ord(data[i]) + (ord(data[i+1]) << 8)
                s = (s + w) & 0xffff
            return s

        csum = _checksum(bootdata)
        if csum != 0:
            raise oz.OzException.OzException("invalid CD checksum: expected 0, saw %d" % (csum))

        # OK, everything so far has checked out.  Read the default/initial
        # boot entry
        cdfd.seek(bootP*2048+32)
        fmt = "=BBHBBHIB"
        (boot, media, loadsegment, systemtype, unused, scount, imgstart, unused2) = struct.unpack(fmt, cdfd.read(struct.calcsize(fmt)))

        if boot != 0x88:
            raise oz.OzException.OzException("invalid CD initial boot indicator")
        if unused != 0x0 or unused2 != 0x0:
            raise oz.OzException.OzException("invalid CD initial boot unused field")

        if media == 0 or media == 4:
            count = scount
        elif media == 1:
            # 1.2MB floppy in sectors
            count = 1200*1024/512
        elif media == 2:
            # 1.44MB floppy in sectors
            count = 1440*1024/512
        elif media == 3:
            # 2.88MB floppy in sectors
            count = 2880*1024/512
        else:
            raise oz.OzException.OzException("invalid CD media type")

        # finally, seek to "imgstart", and read "count" sectors, which
        # contains the boot image
        cdfd.seek(imgstart*2048)

        # The eltorito specification section 2.5 says:
        #
        # Sector Count. This is the number of virtual/emulated sectors the
        # system will store at Load Segment during the initial boot
        # procedure.
        #
        # and then Section 1.5 says:
        #
        # Virtual Disk - A series of sectors on the CD which INT 13 presents
        # to the system as a drive with 200 byte virtual sectors. There
        # are 4 virtual sectors found in each sector on a CD.
        #
        # (note that the bytes above are in hex).  So we read count*512
        eltoritodata = cdfd.read(count*512)
        cdfd.close()

        with open(outfile, "w") as f:
            f.write(eltoritodata)

    def _do_install(self, timeout=None, force=False, reboots=0,
                    kernelfname=None, ramdiskfname=None, cmdline=None,
                    extrainstalldevs=None):
        """
        Internal method to actually run the installation.
        """
        if not force and os.access(self.jeos_filename, os.F_OK):
            self.log.info("Found cached JEOS (%s), using it" % (self.jeos_filename))
            oz.ozutil.copyfile_sparse(self.jeos_filename, self.diskimage)
            return self._generate_xml("hd", None)

        self.log.info("Running install for %s" % (self.tdl.name))

        if timeout is None:
            timeout = 1200

        cddev = self._InstallDev("cdrom", self.output_iso, "hdc")
        if extrainstalldevs != None:
            extrainstalldevs.append(cddev)
            cddev = extrainstalldevs
        reboots_to_go = reboots
        while reboots_to_go >= 0:
            # if reboots_to_go is the same as reboots, it means that this is
            # the first time through and we should generate the "initial" xml
            if reboots_to_go == reboots:
                if kernelfname and os.access(kernelfname, os.F_OK) and ramdiskfname and os.access(ramdiskfname, os.F_OK) and cmdline:
                    xml = self._generate_xml(None, None, kernelfname,
                                             ramdiskfname, cmdline)
                else:
                    xml = self._generate_xml("cdrom", cddev)
            else:
                xml = self._generate_xml("hd", cddev)

            dom = self.libvirt_conn.createXML(xml, 0)
            self._wait_for_install_finish(dom, timeout)

            reboots_to_go -= 1

        if self.cache_jeos:
            self.log.info("Caching JEOS")
            oz.ozutil.mkdir_p(self.jeos_cache_dir)
            oz.ozutil.copyfile_sparse(self.diskimage, self.jeos_filename)

        return self._generate_xml("hd", None)

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        return self._do_install(timeout, force, 0)

    def _check_pvd(self):
        """
        Base method to check the Primary Volume Descriptor on the ISO.  In the
        common case, do nothing; subclasses that need to check the media will
        override this.
        """
        pass

    def _check_iso_tree(self, customize_or_icicle):
        """
        Base method to check the exploded ISO tree.  In the common case, do
        nothing; subclasses that need to check the tree will override this.
        """
        pass

    def _add_iso_extras(self):
        """
        Method to modify the ISO based on the directories specified in the TDL
        file. This modification is done before the final OS and is not
        expected to be override by subclasses
        """
        for isoextra in self.tdl.isoextras:
            targetabspath = os.path.join(self.iso_contents,
                                         isoextra.destination)
            oz.ozutil.mkdir_p(os.path.dirname(targetabspath))

            parsedurl = urlparse.urlparse(isoextra.source)
            if parsedurl.scheme == 'file':
                if isoextra.element_type == "file":
                    oz.ozutil.copyfile_sparse(parsedurl.path, targetabspath)
                else:
                    oz.ozutil.copytree_merge(parsedurl.path, targetabspath)
            elif parsedurl.scheme == "ftp":
                if isoextra.element_type == "file":
                    fd = os.open(targetabspath,
                                 os.O_CREAT|os.O_TRUNC|os.O_WRONLY)
                    try:
                        oz.ozutil.http_download_file(isoextra.source, fd, True,
                                                     self.log)
                    finally:
                        os.close(fd)
                else:
                    oz.ozutil.ftp_download_directory(parsedurl.hostname,
                                                     parsedurl.username,
                                                     parsedurl.password,
                                                     parsedurl.path,
                                                     targetabspath)
            elif parsedurl.scheme == "http":
                if isoextra.element_type == "directory":
                    raise oz.OzException.OzException("ISO extra directories cannot be fetched over HTTP")
                else:
                    fd = os.open(targetabspath,
                                 os.O_CREAT|os.O_TRUNC|os.O_WRONLY)
                    try:
                        oz.ozutil.http_download_file(isoextra.source, fd, True,
                                                     self.log)
                    finally:
                        os.close(fd)
            else:
                raise oz.OzException.OzException("The protocol '%s' is not supported for fetching remote files or directories" % parsedurl.scheme)

    def _modify_iso(self):
        """
        Base method to modify the ISO.  Subclasses are expected to override
        this.
        """
        raise oz.OzException.OzException("Internal error, subclass didn't override modify_iso")

    def _generate_new_iso(self):
        """
        Base method to generate the new ISO.  Subclasses are expected to
        override this.
        """
        raise oz.OzException.OzException("Internal error, subclass didn't override generate_new_iso")

    def _iso_generate_install_media(self, url, force_download,
                                    customize_or_icicle):
        """
        Method to generate the modified media necessary for unattended installs.
        """
        self.log.info("Generating install media")

        if not force_download:
            if os.access(self.jeos_filename, os.F_OK):
                # if we found a cached JEOS, we don't need to do anything here;
                # we'll copy the JEOS itself later on
                return
            elif os.access(self.modified_iso_cache, os.F_OK):
                self.log.info("Using cached modified media")
                shutil.copyfile(self.modified_iso_cache, self.output_iso)
                return

        self._get_original_iso(url, force_download)
        self._check_pvd()
        self._copy_iso()
        self._check_iso_tree(customize_or_icicle)
        try:
            self._add_iso_extras()
            self._modify_iso()
            self._generate_new_iso()
            if self.cache_modified_media:
                self.log.info("Caching modified media for future use")
                shutil.copyfile(self.output_iso, self.modified_iso_cache)
        finally:
            self._cleanup_iso()

    def generate_install_media(self, force_download=False,
                               customize_or_icicle=False):
        """
        Method to generate the install media for the operating
        system.  If force_download is False (the default), then the
        original media will only be fetched if it is not cached locally.  If
        force_download is True, then the original media will be downloaded
        regardless of whether it is cached locally.
        """
        return self._iso_generate_install_media(self.url, force_download,
                                                customize_or_icicle)

    def _cleanup_iso(self):
        """
        Method to cleanup the local ISO contents.
        """
        self.log.info("Cleaning up old ISO data")
        # if we are running as non-root, then there might be some files left
        # around that are not writable, which means that the rmtree below would
        # fail.  Recurse into the iso_contents tree, doing a chmod +w on
        # every file and directory to make sure the rmtree succeeds
        for dirpath, dirnames, filenames in os.walk(self.iso_contents):
            os.chmod(dirpath, stat.S_IWUSR|stat.S_IXUSR|stat.S_IRUSR)
            for name in filenames:
                try:
                    # if there are broken symlinks in the ISO,
                    # then the below might fail.  This probably
                    # isn't fatal, so just allow it and go on
                    os.chmod(os.path.join(dirpath, name), stat.S_IRUSR|stat.S_IWUSR)
                except OSError as err:
                    if err.errno != errno.ENOENT:
                        raise

        oz.ozutil.rmtree_and_sync(self.iso_contents)

    def cleanup_install(self):
        """
        Method to cleanup any transient install data.
        """
        self.log.info("Cleaning up after install")

        try:
            os.unlink(self.output_iso)
        except:
            pass

        if not self.cache_original_media:
            try:
                os.unlink(self.orig_iso)
            except:
                pass

class FDGuest(Guest):
    """
    Class for guest installation via floppy disk.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, clockoffset,
                 mousetype, diskbus, macaddress):
        Guest.__init__(self, tdl, config, auto, output_disk, nicmodel,
                       clockoffset, mousetype, diskbus, False, True, macaddress)
        self.orig_floppy = os.path.join(self.data_dir, "floppies",
                                        self.tdl.distro + self.tdl.update + self.tdl.arch + ".img")
        self.modified_floppy_cache = os.path.join(self.data_dir, "floppies",
                                                  self.tdl.distro + self.tdl.update + self.tdl.arch + "-oz.img")
        self.output_floppy = os.path.join(self.output_dir,
                                          self.tdl.name + "-oz.img")
        self.floppy_contents = os.path.join(self.data_dir, "floppycontent",
                                            self.tdl.name)

        self.log.debug("Original floppy path: %s" % self.orig_floppy)
        self.log.debug("Modified floppy cache: %s" % self.modified_floppy_cache)
        self.log.debug("Output floppy path: %s" % self.output_floppy)
        self.log.debug("Floppy content path: %s" % self.floppy_contents)

    def _get_original_floppy(self, floppyurl, force_download):
        """
        Method to download the original floppy if necessary.
        """
        self._get_original_media(floppyurl, self.orig_floppy, force_download)

    def _copy_floppy(self):
        """
        Method to copy the floppy contents for modification.
        """
        self.log.info("Copying floppy contents for modification")
        shutil.copyfile(self.orig_floppy, self.output_floppy)

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        if not force and os.access(self.jeos_filename, os.F_OK):
            self.log.info("Found cached JEOS, using it")
            oz.ozutil.copyfile_sparse(self.jeos_filename, self.diskimage)
            return self._generate_xml("hd", None)

        self.log.info("Running install for %s" % (self.tdl.name))

        fddev = self._InstallDev("floppy", self.output_floppy, "fda")

        if timeout is None:
            timeout = 1200

        dom = self.libvirt_conn.createXML(self._generate_xml("fd", fddev),
                                          0)
        self._wait_for_install_finish(dom, timeout)

        if self.cache_jeos:
            self.log.info("Caching JEOS")
            oz.ozutil.mkdir_p(self.jeos_cache_dir)
            oz.ozutil.copyfile_sparse(self.diskimage, self.jeos_filename)

        return self._generate_xml("hd", None)

    def _cleanup_floppy(self):
        """
        Method to cleanup the temporary floppy data.
        """
        self.log.info("Cleaning up floppy data")
        oz.ozutil.rmtree_and_sync(self.floppy_contents)

    def cleanup_install(self):
        """
        Method to cleanup the installation floppies.
        """
        self.log.info("Cleaning up after install")
        try:
            os.unlink(self.output_floppy)
        except:
            pass

        if not self.cache_original_media:
            try:
                os.unlink(self.orig_floppy)
            except:
                pass

########NEW FILE########
__FILENAME__ = GuestFactory
# Copyright (C) 2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Factory functions.
"""

import oz.OzException

os_dict = { 'Fedora': 'Fedora',
            'FedoraCore': 'FedoraCore',
            'FC': 'FedoraCore',
            'RedHatEnterpriseLinux-2.1': 'RHEL_2_1',
            'RHEL-2.1': 'RHEL_2_1',
            'RedHatEnterpriseLinux-3': 'RHEL_3',
            'RHEL-3': 'RHEL_3',
            'CentOS-3': 'RHEL_3',
            'RedHatEnterpriseLinux-4': 'RHEL_4',
            'RHEL-4': 'RHEL_4',
            'CentOS-4': 'RHEL_4',
            'ScientificLinux-4': 'RHEL_4',
            'SL-4': 'RHEL_4',
            'RedHatEnterpriseLinux-5': 'RHEL_5',
            'RHEL-5': 'RHEL_5',
            'CentOS-5': 'RHEL_5',
            'OL-5': 'RHEL_5',
            'ScientificLinux-5': 'RHEL_5',
            'SL-5': 'RHEL_5',
            'ScientificLinuxCern-5': 'RHEL_5',
            'SLC-5': 'RHEL_5',
            'RedHatEnterpriseLinux-6': 'RHEL_6',
            'RHEL-6': 'RHEL_6',
            'CentOS-6': 'RHEL_6',
            'ScientificLinux-6': 'RHEL_6',
            'SL-6': 'RHEL_6',
            'ScientificLinuxCern-6': 'RHEL_6',
            'SLC-6': 'RHEL_6',
            'OracleEnterpriseLinux-6': 'RHEL_6',
            'OEL-6': 'RHEL_6',
            'OL-6': 'RHEL_6',
            'RHEL-7': 'RHEL_7',
            'Ubuntu': 'Ubuntu',
            'Windows': 'Windows',
            'RedHatLinux': 'RHL',
            'RHL': 'RHL',
            'OpenSUSE': 'OpenSUSE',
            'Debian': 'Debian',
            'Mandrake': 'Mandrake',
            'Mandriva': 'Mandriva',
            'Mageia': 'Mageia',
            'FreeBSD': 'FreeBSD',
}

def guest_factory(tdl, config, auto, output_disk=None, netdev=None,
                  diskbus=None, macaddress=None):
    """
    Factory function return an appropriate Guest object based on the TDL.
    The arguments are:

    tdl    - The TDL object to be used.  The return object will be determined
             based on the distro and version from the TDL.
    config - A ConfigParser object that contains configuration.  If None is
             passed for the config, Oz defaults will be used.
    auto   - An unattended installation file to be used for the
             installation.  If None is passed for auto, then Oz will use
             a known-working unattended installation file.
    output_disk - An optional string argument specifying the path to the
                  disk to be written to.
    netdev - An optional string argument specifying the type of network device
             to be used during installation.  If specified, this will override
             the default that Oz uses.
    diskbus - An optional string argument specifying the type of disk device
              to be used during installation.  If specified, this will override
              the default that Oz uses.
    macaddress - An optional string argument specifying the MAC address to use
                 for the guest.
    """

    klass = None
    for name, importname in os_dict.items():
        if tdl.distro == name:
            # we found the matching module; import and call the get_class method
            module = __import__('oz.' + importname)
            klass = getattr(module, importname).get_class(tdl, config, auto,
                                                          output_disk, netdev,
                                                          diskbus, macaddress)
            break

    if klass is None:
        raise oz.OzException.OzException("Unsupported " + tdl.distro + " update " + tdl.update)

    return klass

def distrolist():
    """
    Function to print out a list of supported distributions.
    """
    strings = []
    for importname in os_dict.values():
        module = __import__('oz.' + importname)
        support = getattr(module, importname).get_supported_string()
        tmp = '   ' + support
        if not tmp in strings:
            strings.append(tmp)

    strings.sort()
    print('\n'.join(strings))

########NEW FILE########
__FILENAME__ = Linux
# Copyright (C) 2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Linux installation
"""

import re
import time
import libvirt
import os

import oz.Guest
import oz.OzException

class LinuxCDGuest(oz.Guest.CDGuest):
    """
    Class for Linux installation.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 iso_allowed, url_allowed, macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk,
                                  nicmodel, None, None, diskbus, iso_allowed,
                                  url_allowed, macaddress)

    def _test_ssh_connection(self, guestaddr):
        """
        Internal method to test out the ssh connection before we try to use it.
        Under systemd, the IP address of a guest can come up and reportip can
        run before the ssh key is generated and sshd starts up.  This check
        makes sure that we allow an additional 30 seconds (1 second per ssh
        attempt) for sshd to finish initializing.
        """
        count = 30
        success = False
        while count > 0:
            try:
                self.log.debug("Testing ssh connection, try %d" % (count))
                start = time.time()
                self.guest_execute_command(guestaddr, 'ls', timeout=1)
                self.log.debug("Succeeded")
                success = True
                break
            except oz.ozutil.SubprocessException:
                # ensure that we spent at least one second before trying again
                end = time.time()
                if (end - start) < 1:
                    time.sleep(1 - (end - start))
                count -= 1

        if not success:
            self.log.debug("Failed to connect to ssh on running guest")
            raise oz.OzException.OzException("Failed to connect to ssh on running guest")

    def get_default_runlevel(self, g_handle):
        """
        Function to determine the default runlevel based on the /etc/inittab.
        """
        runlevel = "3"
        if g_handle.exists('/etc/inittab'):
            lines = g_handle.cat('/etc/inittab').split("\n")
            for line in lines:
                if re.match('id:', line):
                    runlevel = line.split(':')[1]
                    break

        return runlevel

    def guest_execute_command(self, guestaddr, command, timeout=10):
        """
        Method to execute a command on the guest and return the output.
        """
        # ServerAliveInterval protects against NAT firewall timeouts
        # on long-running commands with no output
        #
        # PasswordAuthentication=no prevents us from falling back to
        # keyboard-interactive password prompting
        #
        # -F /dev/null makes sure that we don't use the global or per-user
        # configuration files

        return oz.ozutil.subprocess_check_output(["ssh", "-i", self.sshprivkey,
                                                  "-F", "/dev/null",
                                                  "-o", "ServerAliveInterval=30",
                                                  "-o", "StrictHostKeyChecking=no",
                                                  "-o", "ConnectTimeout=" + str(timeout),
                                                  "-o", "UserKnownHostsFile=/dev/null",
                                                  "-o", "PasswordAuthentication=no",
                                                  "root@" + guestaddr, command],
                                                 printfn=self.log.debug)

    def guest_live_upload(self, guestaddr, file_to_upload, destination,
                          timeout=10):
        """
        Method to copy a file to the live guest.
        """
        self.guest_execute_command(guestaddr,
                                   "mkdir -p " + os.path.dirname(destination),
                                   timeout)

        # ServerAliveInterval protects against NAT firewall timeouts
        # on long-running commands with no output
        #
        # PasswordAuthentication=no prevents us from falling back to
        # keyboard-interactive password prompting
        #
        # -F /dev/null makes sure that we don't use the global or per-user
        # configuration files
        return oz.ozutil.subprocess_check_output(["scp", "-i", self.sshprivkey,
                                                  "-F", "/dev/null",
                                                  "-o", "ServerAliveInterval=30",
                                                  "-o", "StrictHostKeyChecking=no",
                                                  "-o", "ConnectTimeout=" + str(timeout),
                                                  "-o", "UserKnownHostsFile=/dev/null",
                                                  "-o", "PasswordAuthentication=no",
                                                  file_to_upload,
                                                  "root@" + guestaddr + ":" + destination],
                                                 printfn=self.log.debug)

    def _customize_files(self, guestaddr):
        """
        Method to upload the custom files specified in the TDL to the guest.
        """
        self.log.info("Uploading custom files")
        for name, fp in list(self.tdl.files.items()):
            # all of the self.tdl.files are named temporary files; we just need
            # to fetch the name out and have scp upload it
            self.guest_live_upload(guestaddr, fp.name, name)

    def _shutdown_guest(self, guestaddr, libvirt_dom):
        """
        Method to shutdown the guest (gracefully at first, then with prejudice).
        """
        if guestaddr is not None:
            # sometimes the ssh process gets disconnected before it can return
            # cleanly (particularly when the guest is running systemd).  If that
            # happens, ssh returns 255, guest_execute_command throws an
            # exception, and the guest is forcibly destroyed.  While this
            # isn't the end of the world, it isn't desirable.  To avoid
            # this, we catch any exception thrown by ssh during the shutdown
            # command and throw them away.  In the (rare) worst case, the
            # shutdown will not have made it to the guest and we'll have to wait
            # 90 seconds for wait_for_guest_shutdown to timeout and forcibly
            # kill the guest.
            try:
                self.guest_execute_command(guestaddr, 'shutdown -h now')
            except:
                pass

            try:
                if not self._wait_for_guest_shutdown(libvirt_dom):
                    self.log.warn("Guest did not shutdown in time, going to kill")
                else:
                    libvirt_dom = None
            except:
                self.log.warn("Failed shutting down guest, forcibly killing")

        if libvirt_dom is not None:
            try:
                libvirt_dom.destroy()
            except libvirt.libvirtError:
                # the destroy failed for some reason.  This can happen if
                # _wait_for_guest_shutdown times out, but the domain shuts
                # down before we get to destroy.  Check to make sure that the
                # domain is gone from the list of running domains; if so, just
                # continue on; if not, re-raise the error.
                for domid in self.libvirt_conn.listDomainsID():
                    if domid == libvirt_dom.ID():
                        raise

    def _collect_setup(self, libvirt_xml):
        """
        Default method to set the guest up for remote access.
        """
        raise oz.OzException.OzException("ICICLE generation and customization is not implemented for guest %s" % (self.tdl.distro))

    def _collect_teardown(self, libvirt_xml):
        """
        Method to reverse the changes done in _collect_setup.
        """
        raise oz.OzException.OzException("ICICLE generation and customization is not implemented for guest %s" % (self.tdl.distro))

    def _install_packages(self, guestaddr, packstr):
        """
        Internal method to install packages; expected to be overriden by
        child classes.
        """
        raise oz.OzException.OzException("Customization is not implemented for guest %s" % (self.tdl.distro))

    def _customize_repos(self, guestaddr):
        """
        Internal method to customize repositories; expected to be overriden by
        child classes.
        """
        raise oz.OzException.OzException("Customization is not implemented for guest %s" % (self.tdl.distro))

    def _remove_repos(self, guestaddr):
        """
        Internal method to remove repositories; expected to be overriden by
        child classes.
        """
        raise oz.OzException.OzException("Repository removal not implemented for guest %s" % (self.tdl.distro))

    def do_customize(self, guestaddr):
        """
        Method to customize by installing additional packages and files.
        """
        if not self.tdl.packages and not self.tdl.files and not self.tdl.commands:
            # no work to do, just return
            return

        self._customize_repos(guestaddr)

        self.log.debug("Installing custom packages")
        packstr = ''
        for package in self.tdl.packages:
            packstr += '"' + package.name + '" '

        if packstr != '':
            self._install_packages(guestaddr, packstr)

        self._customize_files(guestaddr)

        self.log.debug("Running custom commands")
        for cmd in self.tdl.commands:
            self.guest_execute_command(guestaddr, cmd.read())

        self.log.debug("Removing non-persisted repos")
        self._remove_repos(guestaddr)

        self.log.debug("Syncing")
        self.guest_execute_command(guestaddr, 'sync')

    def do_icicle(self, guestaddr):
        """
        Default method to collect the package information and generate the
        ICICLE XML.
        """
        raise oz.OzException.OzException("ICICLE generation is not implemented for this guest type")

    def _internal_customize(self, libvirt_xml, action):
        """
        Internal method to customize and optionally generate an ICICLE for the
        operating system after initial installation.
        """
        # the "action" input is actually a tri-state:
        # action = "gen_and_mod" means to generate the icicle and to
        #          potentially make modifications
        # action = "gen_only" means to generate the icicle only, and not
        #          look at any modifications
        # action = "mod_only" means to not generate the icicle, but still
        #          potentially make modifications

        self.log.info("Customizing image")

        if not self.tdl.packages and not self.tdl.files and not self.tdl.commands:
            if action == "mod_only":
                self.log.info("No additional packages, files, or commands to install, and icicle generation not requested, skipping customization")
                return
            elif action == "gen_and_mod":
                # It is actually possible to get here with a "gen_and_mod"
                # action but a TDL that contains no real customizations.
                # In the "safe ICICLE" code below it is important to know
                # when we are truly in a "gen_only" state so we modify
                # the action here if we detect that ICICLE generation is the
                # only task to be done.
                self.log.debug("Asked to gen_and_mod but no mods are present - changing action to gen_only")
                action = "gen_only"

        # when doing an oz-install with -g, this isn't necessary as it will
        # just replace the port with the same port.  However, it is very
        # necessary when doing an oz-customize since the serial port might
        # not match what is specified in the libvirt XML
        modified_xml = self._modify_libvirt_xml_for_serial(libvirt_xml)

        if action == "gen_only" and self.safe_icicle_gen:
            # We are only generating ICICLE and the user has asked us to do
            # this without modifying the completed image by booting it.
            # Create a copy on write snapshot to use for ICICLE
            # generation - discard when finished
            cow_diskimage = self.diskimage + "-icicle-snap.qcow2"
            self._internal_generate_diskimage(force=True,
                                              backing_filename=self.diskimage,
                                              image_filename=cow_diskimage)
            modified_xml = self._modify_libvirt_xml_diskimage(modified_xml, cow_diskimage, 'qcow2')

        self._collect_setup(modified_xml)

        icicle = None
        try:
            libvirt_dom = self.libvirt_conn.createXML(modified_xml, 0)

            try:
                guestaddr = None
                guestaddr = self._wait_for_guest_boot(libvirt_dom)
                self._test_ssh_connection(guestaddr)

                if action == "gen_and_mod":
                    self.do_customize(guestaddr)
                    icicle = self.do_icicle(guestaddr)
                elif action == "gen_only":
                    icicle = self.do_icicle(guestaddr)
                elif action == "mod_only":
                    self.do_customize(guestaddr)
                else:
                    raise oz.OzException.OzException("Invalid customize action %s; this is a programming error" % (action))
            finally:
                if action == "gen_only" and self.safe_icicle_gen:
                    # if this is a gen_only and safe_icicle_gen, there is no
                    # reason to wait around for the guest to shutdown; we'll
                    # be removing the overlay file anyway.  Just destroy it
                    libvirt_dom.destroy()
                else:
                    self._shutdown_guest(guestaddr, libvirt_dom)
        finally:
            if action == "gen_only" and self.safe_icicle_gen:
                # no need to teardown because we simply discard the file
                # containing those changes
                os.unlink(cow_diskimage)
            else:
                self._collect_teardown(modified_xml)

        return icicle

    def customize(self, libvirt_xml):
        """
        Method to customize the operating system after installation.
        """
        return self._internal_customize(libvirt_xml, "mod_only")

    def customize_and_generate_icicle(self, libvirt_xml):
        """
        Method to customize and generate the ICICLE for an operating system
        after installation.  This is equivalent to calling customize() and
        generate_icicle() back-to-back, but is faster.
        """
        return self._internal_customize(libvirt_xml, "gen_and_mod")

    def generate_icicle(self, libvirt_xml):
        """
        Method to generate the ICICLE from an operating system after
        installation.  The ICICLE contains information about packages and
        other configuration on the diskimage.
        """
        return self._internal_customize(libvirt_xml, "gen_only")

########NEW FILE########
__FILENAME__ = Mageia
# Copyright (C) 2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Mageia installation
"""

import shutil
import os
import re

import oz.Guest
import oz.ozutil
import oz.OzException

class MageiaGuest(oz.Guest.CDGuest):
    """
    Class for Mageia 4 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk, netdev,
                                  None, None, diskbus, True, False, macaddress)

        self.mageia_arch = self.tdl.arch
        if self.mageia_arch == "i386":
            self.mageia_arch = "i586"
        self.output_floppy = os.path.join(self.output_dir,
                                          self.tdl.name + "-" + self.tdl.installtype + "-oz.img")


    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        self.log.debug("Copying cfg file to floppy image")

        outname = os.path.join(self.iso_contents, "auto_inst.cfg")

        if self.default_auto_file():

            def _cfg_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Mageia.
                """
                if re.search("'password' =>", line):
                    return "			'password' => '" + self.rootpw + "',\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _cfg_sub)
        else:
            shutil.copy(self.auto, outname)

        oz.ozutil.subprocess_check_output(["/sbin/mkfs.msdos", "-C",
                                           self.output_floppy, "1440"])
        oz.ozutil.subprocess_check_output(["mcopy", "-n", "-o", "-i",
                                           self.output_floppy, outname,
                                           "::AUTO_INST.CFG"])

        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(pathdir, "isolinux", "isolinux.cfg")
        with open(isolinuxcfg, 'w') as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  kernel alt0/vmlinuz
  append initrd=alt0/all.rdz ramdisk_size=128000 root=/dev/ram3 acpi=ht vga=788 automatic=method:cdrom kickstart=floppy
""")

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")

        isolinuxdir = ""
        if self.tdl.update in ["4"]:
            isolinuxdir = self.mageia_arch

        isolinuxbin = os.path.join(isolinuxdir, "isolinux/isolinux.bin")
        isolinuxboot = os.path.join(isolinuxdir, "isolinux/boot.cat")

        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-l", "-no-emul-boot",
                                           "-b", isolinuxbin,
                                           "-c", isolinuxboot,
                                           "-boot-load-size", "4",
                                           "-cache-inodes", "-boot-info-table",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)
    def _do_install(self, timeout=None, force=False, reboots=0,
                    kernelfname=None, ramdiskfname=None, cmdline=None):
        fddev = self._InstallDev("floppy", self.output_floppy, "fda")
        return oz.Guest.CDGuest._do_install(self, timeout, force, reboots,
                                            kernelfname, ramdiskfname, cmdline,
                                            [fddev])
    def cleanup_install(self):
        try:
            os.unlink(self.output_floppy)
        except:
            pass
        return oz.Guest.CDGuest.cleanup_install(self)

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Mageia installs.
    """
    if tdl.update in ["4"]:
        return MageiaGuest(tdl, config, auto, output_disk, netdev, diskbus,
                           macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Mageia: 4"

########NEW FILE########
__FILENAME__ = Mandrake
# Copyright (C) 2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Mandrake installation
"""

import shutil
import os
import re

import oz.Guest
import oz.ozutil
import oz.OzException

class MandrakeGuest(oz.Guest.CDGuest):
    """
    Class for Mandrake 9.1, 9.2, 10.0, and 10.1 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk, netdev,
                                  None, None, diskbus, True, False, macaddress)

        if self.tdl.arch != "i386":
            raise oz.OzException.OzException("Mandrake only supports i386 architecture")

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        self.log.debug("Copying cfg file")

        outname = os.path.join(self.iso_contents, "auto_inst.cfg")

        if self.default_auto_file():

            def _cfg_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Mandrake.
                """
                if re.search("'password' =>", line):
                    return "			'password' => '" + self.rootpw + "',\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _cfg_sub)
        else:
            shutil.copy(self.auto, outname)

        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(self.iso_contents, "isolinux",
                                   "isolinux.cfg")
        with open(isolinuxcfg, 'w') as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  kernel alt0/vmlinuz
  append initrd=alt0/all.rdz ramdisk_size=128000 root=/dev/ram3 acpi=ht vga=788 automatic=method:cdrom kickstart=auto_inst.cfg
""")

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-l", "-no-emul-boot",
                                           "-b", "isolinux/isolinux.bin",
                                           "-c", "isolinux/boot.cat",
                                           "-boot-load-size", "4",
                                           "-cache-inodes", "-boot-info-table",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

class Mandrake82Guest(oz.Guest.CDGuest):
    """
    Class for Mandrake 8.2 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk, netdev,
                                  None, None, diskbus, True, False, macaddress)

        if self.tdl.arch != "i386":
            raise oz.OzException.OzException("Mandrake only supports i386 architecture")

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        outname = os.path.join(self.iso_contents, "auto_inst.cfg")
        if self.default_auto_file():

            def _cfg_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Mandrake.
                """
                if re.search("'password' =>", line):
                    return "			'password' => '" + self.rootpw + "',\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _cfg_sub)
        else:
            shutil.copy(self.auto, outname)

        syslinux = os.path.join(self.icicle_tmp, 'syslinux.cfg')
        with open(syslinux, 'w') as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  kernel vmlinuz
  append initrd=cdrom.rdz ramdisk_size=32000 root=/dev/ram3 automatic=method:cdrom vga=788 auto_install=auto_inst.cfg
""")
        cdromimg = os.path.join(self.iso_contents, "Boot", "cdrom.img")
        oz.ozutil.subprocess_check_output(["mcopy", "-n", "-o", "-i",
                                           cdromimg, syslinux,
                                           "::SYSLINUX.CFG"],
                                          printfn=self.log.debug)

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-cache-inodes",
                                           "-b", "Boot/cdrom.img",
                                           "-c", "Boot/boot.cat",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def install(self, timeout=None, force=False):
        internal_timeout = timeout
        if internal_timeout is None:
            internal_timeout = 2500
        return self._do_install(internal_timeout, force, 0)

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Mandrake installs.
    """
    if tdl.update in ["8.2"]:
        return Mandrake82Guest(tdl, config, auto, output_disk, netdev, diskbus,
                               macaddress)
    if tdl.update in ["9.1", "9.2", "10.0", "10.1"]:
        return MandrakeGuest(tdl, config, auto, output_disk, netdev, diskbus,
                             macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Mandrake: 8.2, 9.1, 9.2, 10.0, 10.1"

########NEW FILE########
__FILENAME__ = Mandriva
# Copyright (C) 2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Mandriva installation
"""

import shutil
import os
import re

import oz.Guest
import oz.ozutil
import oz.OzException

class MandrivaGuest(oz.Guest.CDGuest):
    """
    Class for Mandriva 2005, 2006.0, 2007.0, and 2008.0 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk, netdev,
                                  None, None, diskbus, True, False, macaddress)

        self.mandriva_arch = self.tdl.arch
        if self.mandriva_arch == "i386":
            self.mandriva_arch = "i586"

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        self.log.debug("Copying cfg file")

        if self.tdl.update in ["2007.0", "2008.0"]:
            pathdir = os.path.join(self.iso_contents, self.mandriva_arch)
        else:
            pathdir = self.iso_contents

        outname = os.path.join(pathdir, "auto_inst.cfg")

        if self.default_auto_file():

            def _cfg_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Mandriva.
                """
                if re.search("'password' =>", line):
                    return "			'password' => '" + self.rootpw + "',\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _cfg_sub)
        else:
            shutil.copy(self.auto, outname)

        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(pathdir, "isolinux", "isolinux.cfg")
        with open(isolinuxcfg, 'w') as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  kernel alt0/vmlinuz
  append initrd=alt0/all.rdz ramdisk_size=128000 root=/dev/ram3 acpi=ht vga=788 automatic=method:cdrom kickstart=auto_inst.cfg
""")

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")

        isolinuxdir = ""
        if self.tdl.update in ["2007.0", "2008.0"]:
            isolinuxdir = self.mandriva_arch

        isolinuxbin = os.path.join(isolinuxdir, "isolinux/isolinux.bin")
        isolinuxboot = os.path.join(isolinuxdir, "isolinux/boot.cat")

        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-l", "-no-emul-boot",
                                           "-b", isolinuxbin,
                                           "-c", isolinuxboot,
                                           "-boot-load-size", "4",
                                           "-cache-inodes", "-boot-info-table",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Mandriva installs.
    """
    if tdl.update in ["2005", "2006.0", "2007.0", "2008.0"]:
        return MandrivaGuest(tdl, config, auto, output_disk, netdev, diskbus,
                             macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Mandriva: 2005, 2006.0, 2007.0, 2008.0"

########NEW FILE########
__FILENAME__ = OpenSUSE
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
OpenSUSE installation
"""

import re
import shutil
import os
import lxml.etree

import oz.Linux
import oz.ozutil
import oz.OzException

class OpenSUSEGuest(oz.Linux.LinuxCDGuest):
    """
    Class for OpenSUSE installation.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 macaddress):
        oz.Linux.LinuxCDGuest.__init__(self, tdl, config, auto, output_disk,
                                       nicmodel, diskbus, True, False,
                                       macaddress)

        self.crond_was_active = False
        self.sshd_was_active = False
        self.reboots = 1
        if self.tdl.update in ["10.3"]:
            # for 10.3 we don't have a 2-stage install process so don't reboot
            self.reboots = 0

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Putting the autoyast in place")

        outname = os.path.join(self.iso_contents, "autoinst.xml")

        if self.default_auto_file():
            doc = lxml.etree.parse(self.auto)

            pw = doc.xpath('/suse:profile/suse:users/suse:user/suse:user_password',
                           namespaces={'suse':'http://www.suse.com/1.0/yast2ns'})
            if len(pw) != 1:
                raise oz.OzException.OzException("Invalid SUSE autoyast file; expected single user_password, saw %d" % (len(pw)))
            pw[0].text = self.rootpw

            f = open(outname, 'w')
            f.write(lxml.etree.tostring(doc, pretty_print=True))
            f.close()
        else:
            shutil.copy(self.auto, outname)

        self.log.debug("Modifying the boot options")
        isolinux_cfg = os.path.join(self.iso_contents, "boot", self.tdl.arch,
                                    "loader", "isolinux.cfg")
        f = open(isolinux_cfg, "r")
        lines = f.readlines()
        f.close()
        for index, line in enumerate(lines):
            if re.match("timeout", line):
                lines[index] = "timeout 1\n"
            elif re.match("default", line):
                lines[index] = "default customiso\n"
        lines.append("label customiso\n")
        lines.append("  kernel linux\n")
        lines.append("  append initrd=initrd splash=silent instmode=cd autoyast=default")

        with open(isolinux_cfg, 'w') as f:
            f.writelines(lines)

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-no-emul-boot",
                                           "-b", "boot/" + self.tdl.arch + "/loader/isolinux.bin",
                                           "-c", "boot/" + self.tdl.arch + "/loader/boot.cat",
                                           "-boot-load-size", "4",
                                           "-boot-info-table", "-graft-points",
                                           "-iso-level", "4", "-pad",
                                           "-allow-leading-dots", "-l", "-v",
                                           "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        return self._do_install(timeout, force, self.reboots)

    def _image_ssh_teardown_step_1(self, g_handle):
        """
        First step to undo _image_ssh_setup (remove authorized keys).
        """
        self.log.debug("Teardown step 1")
        # reset the authorized keys
        self.log.debug("Resetting authorized_keys")
        self._guestfs_path_restore(g_handle, '/root/.ssh/authorized_keys')

    def _image_ssh_teardown_step_2(self, g_handle):
        """
        Second step to undo _image_ssh_setup (remove custom sshd_config).
        """
        self.log.debug("Teardown step 2")
        # remove custom sshd_config
        self.log.debug("Resetting sshd_config")
        self._guestfs_path_restore(g_handle, '/etc/ssh/sshd_config')

        # reset the service link
        self.log.debug("Resetting sshd service")
        if g_handle.exists('/usr/lib/systemd/system/sshd.service'):
            if not self.sshd_was_active:
                g_handle.rm('/etc/systemd/system/multi-user.target.wants/sshd.service')
        else:
            self._guestfs_path_restore(g_handle, '/etc/init.d/after.local')

    def _image_ssh_teardown_step_3(self, g_handle):
        """
        Third step to undo _image_ssh_setup (remove guest announcement).
        """
        self.log.debug("Teardown step 3")
        # remove announce cronjob
        self.log.debug("Resetting announcement to host")
        self._guestfs_remove_if_exists(g_handle,
                                       '/etc/NetworkManager/dispatcher.d/99-reportip')
        self._guestfs_remove_if_exists(g_handle, '/etc/cron.d/announce')

        # remove reportip
        self.log.debug("Removing reportip")
        self._guestfs_remove_if_exists(g_handle, '/root/reportip')

        # reset the service link
        self.log.debug("Resetting cron service")
        if g_handle.exists('/usr/lib/systemd/system/cron.service'):
            if not self.crond_was_active:
                g_handle.rm('/etc/systemd/system/multi-user.target.wants/cron.service')
        else:
            runlevel = self.get_default_runlevel(g_handle)
            startuplink = '/etc/rc.d/rc' + runlevel + ".d/S06cron"
            self._guestfs_path_restore(g_handle, startuplink)

    def _image_ssh_teardown_step_4(self, g_handle):
        """
        Fourth step to undo changes by the operating system.  For instance,
        during first boot openssh generates ssh host keys and stores them
        in /etc/ssh.  Since this image might be cached later on, this method
        removes those keys.
        """
        for f in ["/etc/ssh/ssh_host_dsa_key", "/etc/ssh/ssh_host_dsa_key.pub",
                  "/etc/ssh/ssh_host_rsa_key", "/etc/ssh/ssh_host_rsa_key.pub",
                  "/etc/ssh/ssh_host_ecdsa_key", "/etc/ssh/ssh_host_ecdsa_key.pub",
                  "/etc/ssh/ssh_host_key", "/etc/ssh/ssh_host_key.pub"]:
            self._guestfs_remove_if_exists(g_handle, f)

    def _collect_teardown(self, libvirt_xml):
        """
        Method to reverse the changes done in _collect_setup.
        """
        self.log.info("Collection Teardown")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        try:
            self._image_ssh_teardown_step_1(g_handle)

            self._image_ssh_teardown_step_2(g_handle)

            self._image_ssh_teardown_step_3(g_handle)

            self._image_ssh_teardown_step_4(g_handle)
        finally:
            self._guestfs_handle_cleanup(g_handle)
            shutil.rmtree(self.icicle_tmp)

    def do_icicle(self, guestaddr):
        """
        Method to collect the package information and generate the ICICLE
        XML.
        """
        self.log.debug("Generating ICICLE")
        stdout, stderr, retcode = self.guest_execute_command(guestaddr,
                                                             'rpm -qa',
                                                             timeout=30)

        return self._output_icicle_xml(stdout.split("\n"),
                                       self.tdl.description)

    def _image_ssh_setup_step_1(self, g_handle):
        """
        First step for allowing remote access (generate and upload ssh keys).
        """
        # part 1; upload the keys
        self.log.debug("Step 1: Uploading ssh keys")
        if not g_handle.exists('/root/.ssh'):
            g_handle.mkdir('/root/.ssh')

        self._guestfs_path_backup(g_handle, '/root/.ssh/authorized_keys')

        self._generate_openssh_key(self.sshprivkey)

        g_handle.upload(self.sshprivkey + ".pub", '/root/.ssh/authorized_keys')

    def _image_ssh_setup_step_2(self, g_handle):
        """
        Second step for allowing remote access (ensure sshd is running).
        """
        # part 2; check and setup sshd
        self.log.debug("Step 2: setup sshd")
        if not g_handle.exists('/etc/init.d/sshd') or not g_handle.exists('/usr/sbin/sshd'):
            raise oz.OzException.OzException("ssh not installed on the image, cannot continue")

        if g_handle.exists('/usr/lib/systemd/system/sshd.service'):
            if g_handle.exists('/etc/systemd/system/multi-user.target.wants/sshd.service'):
                self.sshd_was_active = True
            else:
                g_handle.ln_sf('/usr/lib/systemd/system/sshd.service',
                               '/etc/systemd/system/multi-user.target.wants/sshd.service')
        else:
            self._guestfs_path_backup(g_handle, "/etc/init.d/after.local")
            local = os.path.join(self.icicle_tmp, "after.local")
            with open(local, "w") as f:
                f.write("/sbin/service sshd start\n")
            try:
                g_handle.upload(local, "/etc/init.d/after.local")
            finally:
                os.unlink(local)

        sshd_config_file = self.icicle_tmp + "/sshd_config"
        with open(sshd_config_file, 'w') as f:
            f.write("""PasswordAuthentication no
UsePAM yes

X11Forwarding yes

Subsystem      sftp    /usr/lib64/ssh/sftp-server

AcceptEnv LANG LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES
AcceptEnv LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT
AcceptEnv LC_IDENTIFICATION LC_ALL
""")

        try:
            self._guestfs_path_backup(g_handle, "/etc/ssh/sshd_config")
            g_handle.upload(sshd_config_file, '/etc/ssh/sshd_config')
        finally:
            os.unlink(sshd_config_file)

    def _image_ssh_setup_step_3(self, g_handle):
        """
        Third step for allowing remote access (make the guest announce itself
        on bootup).
        """
        # part 3; make sure the guest announces itself
        self.log.debug("Step 3: Guest announcement")

        scriptfile = os.path.join(self.icicle_tmp, "script")

        if g_handle.exists("/etc/NetworkManager/dispatcher.d"):
            with open(scriptfile, 'w') as f:
                f.write("""\
#!/bin/bash

if [ "$1" = "eth0" -a "$2" = "up" ]; then
    echo -n "!$DHCP4_IP_ADDRESS,%s!" > /dev/ttyS1
fi
""" % (self.uuid))

            try:
                g_handle.upload(scriptfile,
                                '/etc/NetworkManager/dispatcher.d/99-reportip')
                g_handle.chmod(0755,
                               '/etc/NetworkManager/dispatcher.d/99-reportip')
            finally:
                os.unlink(scriptfile)

        if not g_handle.exists('/etc/init.d/cron') or not g_handle.exists('/usr/sbin/cron'):
            raise oz.OzException.OzException("cron not installed on the image, cannot continue")

        with open(scriptfile, 'w') as f:
            f.write("""\
#!/bin/bash
DEV=$(/bin/awk '{if ($2 == 0) print $1}' /proc/net/route) &&
[ -z "$DEV" ] && exit 0
ADDR=$(/sbin/ip -4 -o addr show dev $DEV | /bin/awk '{print $4}' | /usr/bin/cut -d/ -f1) &&
[ -z "$ADDR" ] && exit 0
echo -n "!$ADDR,%s!" > /dev/ttyS1
""" % (self.uuid))

        try:
            g_handle.upload(scriptfile, '/root/reportip')
            g_handle.chmod(0o755, '/root/reportip')
        finally:
            os.unlink(scriptfile)

        announcefile = os.path.join(self.icicle_tmp, "announce")
        with open(announcefile, 'w') as f:
            f.write('*/1 * * * * root /bin/bash -c "/root/reportip"\n')

        try:
            g_handle.upload(announcefile, '/etc/cron.d/announce')
        finally:
            os.unlink(announcefile)

        if g_handle.exists('/usr/lib/systemd/system/cron.service'):
            if g_handle.exists('/etc/systemd/system/multi-user.target.wants/cron.service'):
                self.crond_was_active = True
            else:
                g_handle.ln_sf('/lib/systemd/system/cron.service',
                               '/etc/systemd/system/multi-user.target.wants/cron.service')
        else:
            runlevel = self.get_default_runlevel(g_handle)
            startuplink = '/etc/rc.d/rc' + runlevel + ".d/S06cron"
            self._guestfs_path_backup(g_handle, startuplink)
            g_handle.ln_sf('/etc/init.d/cron', startuplink)

    def _collect_setup(self, libvirt_xml):
        """
        Setup the guest for remote access.
        """
        self.log.info("Collection Setup")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        # we have to do 3 things to make sure we can ssh into OpenSUSE:
        # 1)  Upload our ssh key
        # 2)  Make sure sshd is running on boot
        # 3)  Make the guest announce itself to the host

        try:
            try:
                self._image_ssh_setup_step_1(g_handle)

                try:
                    self._image_ssh_setup_step_2(g_handle)

                    try:
                        self._image_ssh_setup_step_3(g_handle)
                    except:
                        self._image_ssh_teardown_step_3(g_handle)
                        raise
                except:
                    self._image_ssh_teardown_step_2(g_handle)
                    raise
            except:
                self._image_ssh_teardown_step_1(g_handle)
                raise

        finally:
            self._guestfs_handle_cleanup(g_handle)

    def _customize_repos(self, guestaddr):
        """
        Method to add user-provided repositories to the guest.
        """
        self.log.debug("Installing additional repository files")
        for repo in list(self.tdl.repositories.values()):
            self.guest_execute_command(guestaddr,
                                       "zypper addrepo %s %s" % (repo.url,
                                                                 repo.name))

    def _install_packages(self, guestaddr, packstr):
        # due to a bug in OpenSUSE 11.1, we want to remove the default
        # CD repo first
        stdout, stderr, retcode = self.guest_execute_command(guestaddr,
                                                             'zypper repos -d')
        removerepos = []
        for line in stdout.split('\n'):
            if re.match("^[0-9]+", line):
                split = line.split('|')

                if re.match("^cd://", split[7].strip()):
                    removerepos.append(split[0].strip())
        for repo in removerepos:
            self.guest_execute_command(guestaddr,
                                       'zypper removerepo %s' % (repo))

        self.guest_execute_command(guestaddr,
                                   'zypper -n install %s' % (packstr))

    def _remove_repos(self, guestaddr):
        for repo in list(self.tdl.repositories.values()):
            if not repo.persisted:
                self.guest_execute_command(guestaddr,
                                           "zypper removerepo %s" % (repo.name))

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for OpenSUSE installs.
    """
    if tdl.update in ["10.3"]:
        return OpenSUSEGuest(tdl, config, auto, output_disk, netdev, diskbus,
                             macaddress)
    if tdl.update in ["11.0", "11.1", "11.2", "11.3", "11.4", "12.1", "12.2",
                      "12.3", "13.1"]:
        if diskbus is None:
            diskbus = 'virtio'
        if netdev is None:
            netdev = 'virtio'
        return OpenSUSEGuest(tdl, config, auto, output_disk, netdev, diskbus,
                             macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "OpenSUSE: 10.3, 11.0, 11.1, 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 13.1"

########NEW FILE########
__FILENAME__ = OzException
# Copyright (C) 2011  Chris Lalancette <clalance@redhat.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Exception class for Oz.
"""

class OzException(Exception):
    """
    Class for Oz Exceptions.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)

########NEW FILE########
__FILENAME__ = ozutil
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Miscellaneous utility functions.
"""

import os
import random
import subprocess
import tempfile
import errno
import stat
import shutil
import pycurl
import gzip
import time
import select
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import collections
import ftplib
import struct

def generate_full_auto_path(relative):
    """
    Function to find the absolute path to an unattended installation file.
    """
    # all of the automated installation paths are installed to $pkg_path/auto,
    # so we just need to find it and generate the right path here
    if relative is None:
        raise Exception("The relative path cannot be None")

    pkg_path = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(pkg_path, "auto", relative))

def executable_exists(program):
    """
    Function to find out whether an executable exists in the PATH
    of the user.  If so, the absolute path to the executable is returned.
    If not, an exception is raised.
    """
    def is_exe(fpath):
        """
        Helper method to check if a file exists and is executable
        """
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    if program is None:
        raise Exception("Invalid program name passed")

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    raise Exception("Could not find %s" % (program))

def write_bytes_to_fd(fd, buf):
    """
    Function to write all bytes in "buf" to "fd".  This handles both EINTR
    and short writes.
    """
    size = len(buf)
    offset = 0
    while size > 0:
        try:
            bytes_written = os.write(fd, buf[offset:])
            offset += bytes_written
            size -= bytes_written
        except OSError as err:
            # python's os.write() can raise an exception on EINTR, which
            # according to the man page can happen if a signal was
            # received before any data was written.  Therefore, we don't
            # need to update destlen or size, but just retry
            if err.errno == errno.EINTR:
                continue
            raise

    return offset

def read_bytes_from_fd(fd, num):
    """
    Function to read and return bytes from fd.  This handles the EINTR situation
    where no bytes were read before a signal happened.
    """
    read_done = False
    while not read_done:
        try:
            ret = os.read(fd, num)
            read_done = True
        except OSError as err:
            # python's os.read() can raise an exception on EINTR, which
            # according to the man page can happen if a signal was
            # received before any data was read.  In this case we need to retry
            if err.errno == errno.EINTR:
                continue
            raise

    return ret

def copyfile_sparse(src, dest):
    """
    Function to copy a file sparsely if possible.  The logic here is
    all taken from coreutils cp, specifically the 'sparse_copy' function.
    """
    if src is None:
        raise Exception("Source of copy cannot be None")
    if dest is None:
        raise Exception("Destination of copy cannot be None")

    if not os.path.exists(src):
        raise Exception("Source '%s' does not exist" % (src))

    if os.path.exists(dest) and os.path.samefile(src, dest):
        raise Exception("Source '%s' and dest '%s' are the same file" % (src, dest))

    base = os.path.dirname(dest)
    if not os.path.exists(base):
        mkdir_p(base)

    src_fd = os.open(src, os.O_RDONLY)

    try:
        dest_fd = os.open(dest, os.O_WRONLY|os.O_CREAT|os.O_TRUNC)

        try:
            sb = os.fstat(src_fd)

            # See io_blksize() in coreutils for an explanation of why 32*1024
            buf_size = max(32*1024, sb.st_blksize)

            size = sb.st_size
            destlen = 0
            while size != 0:
                buf = read_bytes_from_fd(src_fd, min(buf_size, size))
                if len(buf) == 0:
                    break

                buflen = len(buf)
                if buf == '\0'*buflen:
                    os.lseek(dest_fd, buflen, os.SEEK_CUR)
                else:
                    write_bytes_to_fd(dest_fd, buf)

                destlen += buflen
                size -= buflen

            os.ftruncate(dest_fd, destlen)

        finally:
            os.close(dest_fd)
    finally:
        os.close(src_fd)

def bsd_split(line, digest_type):
    """
    Function to split a BSD-style checksum line into a filename and
    checksum.
    """
    current = len(digest_type)

    if line[current] == ' ':
        current += 1

    if line[current] != '(':
        return None, None

    current += 1

    # find end of filename.  The BSD 'md5' and 'sha1' commands do not escape
    # filenames, so search backwards for the last ')'
    file_end = line.rfind(')')
    if file_end == -1:
        # could not find the ending ), fail
        return None, None

    filename = line[current:file_end]

    line = line[(file_end + 1):]
    line = line.lstrip()

    if line[0] != '=':
        return None, None

    line = line[1:]

    line = line.lstrip()
    if line[-1] == '\n':
        line = line[:-1]

    return line, filename

def sum_split(line, digest_bits):
    """
    Function to split a normal Linux checksum line into a filename and
    checksum.
    """
    digest_hex_bytes = digest_bits / 4
    min_digest_line_length = digest_hex_bytes + 2 + 1 # length of hex message digest + blank and binary indicator (2 bytes) + minimum file length (1 byte)

    min_length = min_digest_line_length
    if line[0] == '\\':
        min_length = min_length + 1
    if len(line) < min_length:
        # if the line is too short, skip it
        return None, None

    if line[0] == '\\':
        current = digest_hex_bytes + 1
        hex_digest = line[1:current]
        escaped_filename = True
    else:
        current = digest_hex_bytes
        hex_digest = line[0:current]
        escaped_filename = False

    # if the digest is not immediately followed by a white space, it is an
    # error
    if line[current] != ' ' and line[current] != '\t':
        return None, None

    current += 1
    # if the whitespace is not immediately followed by another space or a *,
    # it is an error
    if line[current] != ' ' and line[current] != '*':
        return None, None

    if line[current] == '*':
        binary = True

    current += 1

    if line[-1] == '\n':
        filename = line[current:-1]
    else:
        filename = line[current:]

    if escaped_filename:
        # FIXME: a \0 is not allowed in the sum file format, but
        # string_escape allows it.  We'd probably have to implement our
        # own codec to fix this
        filename = filename.decode('string_escape')

    return hex_digest, filename

def get_sum_from_file(sumfile, file_to_find, digest_bits, digest_type):
    """
    Function to get a checksum digest out of a checksum file given a
    filename.
    """
    retval = None

    f = open(sumfile, 'r')
    for line in f:
        binary = False

        # remove any leading whitespace
        line = line.lstrip()

        # ignore blank lines
        if len(line) == 0:
            continue

        # ignore comment lines
        if line[0] == '#':
            continue

        if line.startswith(digest_type):
            # OK, if it starts with a string of ["MD5", "SHA1", "SHA256"], then
            # this is a BSD-style sumfile
            hex_digest, filename = bsd_split(line, digest_type)
        else:
            # regular sumfile
            hex_digest, filename = sum_split(line, digest_bits)

        if hex_digest is None or filename is None:
            continue

        if filename == file_to_find:
            retval = hex_digest
            break

    f.close()

    return retval

def get_md5sum_from_file(sumfile, file_to_find):
    """
    Function to get an MD5 checksum out of a checksum file given a filename.
    """
    return get_sum_from_file(sumfile, file_to_find, 128, "MD5")

def get_sha1sum_from_file(sumfile, file_to_find):
    """
    Function to get a SHA1 checksum out of a checksum file given a filename.
    """
    return get_sum_from_file(sumfile, file_to_find, 160, "SHA1")

def get_sha256sum_from_file(sumfile, file_to_find):
    """
    Function to get a SHA256 checksum out of a checksum file given a
    filename.
    """
    return get_sum_from_file(sumfile, file_to_find, 256, "SHA256")

def string_to_bool(instr):
    """
    Function to take a string and determine whether it is True, Yes, False,
    or No.  It takes a single argument, which is the string to examine.

    Returns True if instr is "Yes" or "True", False if instr is "No"
    or "False", and None otherwise.
    """
    if instr is None:
        raise Exception("Input string was None!")
    lower = instr.lower()
    if lower == 'no' or lower == 'false':
        return False
    if lower == 'yes' or lower == 'true':
        return True
    return None

def generate_macaddress():
    """
    Function to generate a random MAC address.
    """
    mac = [0x52, 0x54, 0x00, random.randint(0x00, 0xff),
           random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
    return ':'.join(["%02x" % x for x in mac])

class SubprocessException(Exception):
    """
    Class for subprocess exceptions.  In addition to a error message, it
    also has a retcode member that has the returncode from the command.
    """
    def __init__(self, msg, retcode):
        Exception.__init__(self, msg)
        self.retcode = retcode

def subprocess_check_output(*popenargs, **kwargs):
    """
    Function to call a subprocess and gather the output.
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    if 'stderr' in kwargs:
        raise ValueError('stderr argument not allowed, it will be overridden.')

    printfn = None
    if kwargs.has_key('printfn'):
        printfn = kwargs['printfn']
        del kwargs['printfn']

    executable_exists(popenargs[0][0])

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               *popenargs, **kwargs)

    poller = select.poll()
    select_POLLIN_POLLPRI = select.POLLIN | select.POLLPRI
    poller.register(process.stdout.fileno(), select_POLLIN_POLLPRI)
    poller.register(process.stderr.fileno(), select_POLLIN_POLLPRI)

    stdout = ''
    stderr = ''
    retcode = process.poll()
    while retcode is None:
        start = time.time()
        try:
            ready = poller.poll(1000)
        except select.error, e:
            if e.args[0] == errno.EINTR:
                continue
            raise

        for fd, mode in ready:
            if mode & select_POLLIN_POLLPRI:
                data = os.read(fd, 4096)
                if not data:
                    poller.unregister(fd)
                else:
                    if printfn is not None:
                        printfn(data)
                    if fd == process.stdout.fileno():
                        stdout += data
                    else:
                        stderr += data
            else:
                # Ignore hang up or errors.
                poller.unregister(fd)

        end = time.time()
        if (end - start) < 1:
            time.sleep(1 - (end - start))
        retcode = process.poll()

    tmpout, tmperr = process.communicate()

    stdout += tmpout
    stderr += tmperr
    if printfn is not None:
        printfn(tmperr)
        printfn(tmpout)

    if retcode:
        cmd = ' '.join(*popenargs)
        raise SubprocessException("'%s' failed(%d): %s" % (cmd, retcode, stderr), retcode)

    return (stdout, stderr, retcode)

def mkdir_p(path):
    """
    Function to make a directory and all intermediate directories as
    necessary.  The functionality differs from os.makedirs slightly, in
    that this function does *not* raise an error if the directory already
    exists.
    """
    if path is None:
        raise Exception("Path cannot be None")

    if path == '':
        # this can happen if the user did something like call os.path.dirname()
        # on a file without directories.  Since os.makedirs throws an exception
        # in that case, check for it here and allow it.
        return

    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno != errno.EEXIST or not os.path.isdir(path):
            raise

def copytree_merge(src, dst, symlinks=False, ignore=None):
    """
    Function to copy an entire directory recursively. The functionality
    differs from shutil.copytree, in that this function does *not* raise
    an exception if the directory already exists.
    It is based on: http://docs.python.org/2.7/library/shutil.html#copytree-example
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    mkdir_p(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree_merge(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
            # FIXME: What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except shutil.WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)

def copy_modify_file(inname, outname, subfunc):
    """
    Function to copy a file from inname to outname, passing each line
    through subfunc first.  subfunc is expected to be a method that takes
    a single argument in (the next line), and returns a string to be
    written to the output file after modification (if any).
    """
    if inname is None:
        raise Exception("input filename is None")
    if outname is None:
        raise Exception("output filename is None")
    if subfunc is None:
        raise Exception("subfunction is None")
    if not isinstance(subfunc, collections.Callable):
        raise Exception("subfunction is not callable")

    infile = open(inname, 'r')
    outfile = open(outname, 'w')

    for line in infile:
        outfile.write(subfunc(line))

    infile.close()
    outfile.close()

def write_cpio(inputdict, outputfile):
    """
    Function to write a CPIO archive in the "New ASCII Format".  The
    inputlist is a dictionary of files to put in the archive, where the
    dictionary key is the path to the file on the local filesystem and the
    dictionary value is the location that the file should have in the cpio
    archive.  The outputfile is the location of the final cpio archive that
    will be written.
    """
    if inputdict is None:
        raise Exception("input dictionary was None")
    if outputfile is None:
        raise Exception("output file was None")

    outf = open(outputfile, "w")

    try:
        for inputfile, destfile in list(inputdict.items()):
            inf = open(inputfile, 'r')
            st = os.fstat(inf.fileno())

            # 070701 is the magic for new CPIO (newc in cpio parlance)
            outf.write("070701")
            # inode (really just needs to be unique)
            outf.write("%08x" % (st[stat.ST_INO]))
            # mode
            outf.write("%08x" % (st[stat.ST_MODE]))
            # uid is 0
            outf.write("00000000")
            # gid is 0
            outf.write("00000000")
            # nlink (always a single link for a single file)
            outf.write("00000001")
            # mtime
            outf.write("%08x" % (st[stat.ST_MTIME]))
            # filesize
            outf.write("%08x" % (st[stat.ST_SIZE]))
            # devmajor
            outf.write("%08x" % (os.major(st[stat.ST_DEV])))
            # dev minor
            outf.write("%08x" % (os.minor(st[stat.ST_DEV])))
            # rdevmajor (always 0)
            outf.write("00000000")
            # rdevminor (always 0)
            outf.write("00000000")
            # namesize (the length of the name plus 1 for the NUL padding)
            outf.write("%08x" % (len(destfile) + 1))
            # check (always 0)
            outf.write("00000000")
            # write the name of the inputfile minus the leading /
            stripped = destfile.lstrip('/')
            outf.write(stripped)

            # we now need to write sentinel NUL byte(s).  We need to make the
            # header (110 bytes) plus the filename, plus the sentinel a
            # multiple of 4 bytes.  Note that we always need at *least* one NUL,
            # so if it is exactly a multiple of 4 we need to write 4 NULs
            outf.write("\x00"*(4 - ((110+len(stripped)) % 4)))

            # now write the data from the input file
            outf.writelines(inf)
            inf.close()

            # we now need to write out NUL byte(s) to make it a multiple of 4.
            # note that unlike the name, we do *not* have to have any NUL bytes,
            # so if it is already aligned on 4 bytes do nothing
            remainder = st[stat.ST_SIZE] % 4
            if remainder != 0:
                outf.write("\x00"*(4 - remainder))

        # now that we have written all of the file entries, write the trailer
        outf.write("070701")
        # zero inode
        outf.write("00000000")
        # zero mode
        outf.write("00000000")
        # zero uid
        outf.write("00000000")
        # zero gid
        outf.write("00000000")
        # one nlink
        outf.write("00000001")
        # zero mtime
        outf.write("00000000")
        # zero filesize
        outf.write("00000000")
        # zero devmajor
        outf.write("00000000")
        # zero devminor
        outf.write("00000000")
        # zero rdevmajor
        outf.write("00000000")
        # zero rdevminor
        outf.write("00000000")
        # 0xB namesize
        outf.write("0000000B")
        # zero check
        outf.write("00000000")
        # trailer
        outf.write("TRAILER!!!")

        # finally, we need to pad to the closest 512 bytes
        outf.write("\x00"*(512 - (outf.tell() % 512)))
    except:
        os.unlink(outputfile)
        raise

    outf.close()

def config_get_key(config, section, key, default):
    """
    Function to retrieve config parameters out of the config file.
    """
    if config is not None and config.has_section(section) and config.has_option(section, key):
        return config.get(section, key)
    else:
        return default

def config_get_boolean_key(config, section, key, default):
    """
    Function to retrieve boolean config parameters out of the config file.
    """
    value = config_get_key(config, section, key, None)
    if value is None:
        return default

    retval = string_to_bool(value)
    if retval is None:
        raise Exception("Configuration parameter '%s' must be True, Yes, False, or No" % (key))

    return retval

def config_get_path(config, section, key, default):
    path = os.path.expanduser(config_get_key(config, section, key, default))
    if not os.path.isabs(path):
        raise Exception("Config key '%s' must have an absolute path" % (key))
    return path

def rmtree_and_sync(directory):
    """
    Function to remove a directory tree and do an fsync afterwards.  Because
    the removal of the directory tree can cause a lot of metadata updates, it
    can cause a lot of disk activity.  By doing the fsync, we ensure that any
    metadata updates caused by us will not cause subsequent steps to fail.  This
    cannot help if the system is otherwise very busy, but it does ensure that
    the problem is not self-inflicted.
    """
    shutil.rmtree(directory)
    fd = os.open(os.path.dirname(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def parse_config(config_file):
    """
    Function to parse the configuration file.  If the passed in config_file is
    None, then the default configuration file is used.
    """
    if config_file is None:
        if os.geteuid() == 0:
            config_file = "/etc/oz/oz.cfg"
        else:
            config_file = "~/.oz/oz.cfg"
    # if config_file was not None on input, then it was provided by the caller
    # and we use that instead

    config_file = os.path.expanduser(config_file)

    config = configparser.SafeConfigParser()
    if os.access(config_file, os.F_OK):
        config.read(config_file)

    return config

def default_output_dir():
    """
    Function to get the default path to the output directory.
    """
    if os.geteuid() == 0:
        return "/var/lib/libvirt/images"
    else:
        return "~/.oz/images"

def default_data_dir():
    """
    Function to get the default path to the data directory.
    """
    if os.geteuid() == 0:
        return "/var/lib/oz"
    else:
        return "~/.oz"

def default_sshprivkey():
    """
    Function to get the default path to the SSH private key.
    """
    if os.geteuid() == 0:
        return "/etc/oz/id_rsa-icicle-gen"
    else:
        return "~/.oz/id_rsa-icicle-gen"

def default_screenshot_dir():
    """
    Function to get the default path to the screenshot directory. The directory
    is generated relative to the default data directory.
    """
    return os.path.join(default_data_dir(), "screenshots")

def http_get_header(url, redirect=True):
    """
    Function to get the HTTP headers from a URL.  The available headers will be
    returned in a dictionary.  If redirect=True (the default), then this
    function will automatically follow http redirects through to the final
    destination, entirely transparently to the caller.  If redirect=False, then
    this function will follow http redirects through to the final destination,
    and also store that information in the 'Redirect-URL' key.  Note that
    'Redirect-URL' will always be None in the redirect=True case, and may be
    None in the redirect=True case if no redirects were required.
    """
    info = {}
    def _header(buf):
        """
        Internal function that is called back from pycurl perform() for
        header data.
        """
        buf = buf.strip()
        if len(buf) == 0:
            return

        split = buf.split(':')
        if len(split) < 2:
            # not a valid header; skip
            return
        key = split[0].strip()
        value = split[1].strip()
        info[key] = value

    def _data(buf):
        """
        Empty function that is called back from pycurl perform() for body data.
        """
        pass

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.NOBODY, True)
    c.setopt(c.HEADERFUNCTION, _header)
    c.setopt(c.HEADER, True)
    c.setopt(c.WRITEFUNCTION, _data)
    if redirect:
        c.setopt(c.FOLLOWLOCATION, True)
    c.perform()
    info['HTTP-Code'] = c.getinfo(c.HTTP_CODE)
    if info['HTTP-Code'] == 0:
        # if this was a file:/// URL, then the HTTP_CODE returned 0.
        # set it to 200 to be compatible with http
        info['HTTP-Code'] = 200
    if not redirect:
        info['Redirect-URL'] = c.getinfo(c.REDIRECT_URL)

    c.close()

    return info

def http_download_file(url, fd, show_progress, logger):
    """
    Function to download a file from url to file descriptor fd.
    """
    class Progress(object):
        """
        Internal class to represent progress on the connection.  This is only
        required so that we have somewhere to store the "last_mb" variable
        that is not global.
        """
        def __init__(self):
            self.last_mb = -1

        def progress(self, down_total, down_current, up_total, up_current):
            """
            Function that is called back from the pycurl perform() method to
            update the progress information.
            """
            if down_total == 0:
                return
            current_mb = int(down_current) / 10485760
            if current_mb > self.last_mb or down_current == down_total:
                self.last_mb = current_mb
                logger.debug("%dkB of %dkB" % (down_current/1024, down_total/1024))

    def _data(buf):
        """
        Function that is called back from the pycurl perform() method to
        actually write data to disk.
        """
        write_bytes_to_fd(fd, buf)

    progress = Progress()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.CONNECTTIMEOUT, 5)
    c.setopt(c.WRITEFUNCTION, _data)
    c.setopt(c.FOLLOWLOCATION, 1)
    if show_progress:
        c.setopt(c.NOPROGRESS, 0)
        c.setopt(c.PROGRESSFUNCTION, progress.progress)
    c.perform()
    c.close()

def ftp_download_directory(server, username, password, basepath, destination):
    """
    Function to recursively download an entire directory structure over FTP.
    """
    ftp = ftplib.FTP(server)
    ftp.login(username, password)

    def _recursive_ftp_download(sourcepath):
        """
        Function to iterate and download a remote ftp folder
        """
        original_dir = ftp.pwd()
        try:
            ftp.cwd(sourcepath)
        except ftplib.error_perm:
            relativesourcepath = os.path.relpath(sourcepath, basepath)
            destinationpath = os.path.join(destination, relativesourcepath)
            if not os.path.exists(os.path.dirname(destinationpath)):
                os.makedirs(os.path.dirname(destinationpath))
            ftp.retrbinary("RETR " + sourcepath, open(destinationpath, "wb").write)
            return

        names = ftp.nlst()
        for name in names:
            _recursive_ftp_download(os.path.join(sourcepath, name))

        ftp.cwd(original_dir)

    _recursive_ftp_download(basepath)
    ftp.close()

def _gzip_file(inputfile, outputfile, outputmode):
    """
    Internal function to gzip the input file and place it in the outputfile.
    If the outputmode is 'ab', then the input file will be appended to the
    output file, and if the outputmode is 'wb' then the input file will be
    written over the output file.
    """
    with open(inputfile, 'rb') as f:
        gzf = gzip.GzipFile(outputfile, mode=outputmode)
        gzf.writelines(f)
        gzf.close()

def gzip_append(inputfile, outputfile):
    """
    Function to gzip and append the data from inputfile onto output file.
    """
    _gzip_file(inputfile, outputfile, 'ab')

def gzip_create(inputfile, outputfile):
    """
    Function to gzip the data from inputfile and place it into outputfile,
    overwriting any existing data in outputfile.
    """
    try:
        _gzip_file(inputfile, outputfile, 'wb')
    except:
        # since we created the output file, we should clean it up
        if os.access(outputfile, os.F_OK):
            os.unlink(outputfile)
        raise

def check_qcow_size(filename):
    """
    Function to detect if an image is in qcow format.  If it is, return the size
    of the underlying disk image.  If it isn't, return None.
    """

    # For interested parties, this is the QCOW header struct in C
    # struct qcow_header {
    #    uint32_t magic;
    #    uint32_t version;
    #    uint64_t backing_file_offset;
    #    uint32_t backing_file_size;
    #    uint32_t cluster_bits;
    #    uint64_t size; /* in bytes */
    #    uint32_t crypt_method;
    #    uint32_t l1_size;
    #    uint64_t l1_table_offset;
    #    uint64_t refcount_table_offset;
    #    uint32_t refcount_table_clusters;
    #    uint32_t nb_snapshots;
    #    uint64_t snapshots_offset;
    # };

    # And in Python struct format string-ese
    qcow_struct = ">IIQIIQIIQQIIQ" # > means big-endian
    qcow_magic = 0x514649FB # 'Q' 'F' 'I' 0xFB

    f = open(filename,"r")
    pack = f.read(struct.calcsize(qcow_struct))
    f.close()

    unpack = struct.unpack(qcow_struct, pack)

    if unpack[0] == qcow_magic:
        return unpack[5]
    else:
        return None

########NEW FILE########
__FILENAME__ = RedHat
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Common methods for installing and configuring RedHat-based guests
"""

import re
import os
import shutil
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import gzip
import guestfs

import oz.Guest
import oz.Linux
import oz.ozutil
import oz.OzException

class RedHatLinuxCDGuest(oz.Linux.LinuxCDGuest):
    """
    Class for RedHat-based CD guests.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 iso_allowed, url_allowed, initrdtype, macaddress):
        oz.Linux.LinuxCDGuest.__init__(self, tdl, config, auto, output_disk,
                                       nicmodel, diskbus, iso_allowed,
                                       url_allowed, macaddress)
        self.crond_was_active = False
        self.sshd_was_active = False
        self.sshd_config = """\
SyslogFacility AUTHPRIV
PasswordAuthentication yes
ChallengeResponseAuthentication no
GSSAPIAuthentication yes
GSSAPICleanupCredentials yes
UsePAM yes
AcceptEnv LANG LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES
AcceptEnv LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT
AcceptEnv LC_IDENTIFICATION LC_ALL LANGUAGE
AcceptEnv XMODIFIERS
X11Forwarding yes
Subsystem	sftp	/usr/libexec/openssh/sftp-server
"""

        # initrdtype is actually a tri-state:
        # None - don't try to do direct kernel/initrd boot
        # "cpio" - Attempt to do direct kernel/initrd boot with a gzipped CPIO
        #        archive
        # "ext2" - Attempt to do direct kernel/initrd boot with a gzipped ext2
        #         filesystem
        self.initrdtype = initrdtype

        self.kernelfname = os.path.join(self.output_dir,
                                        self.tdl.name + "-kernel")
        self.initrdfname = os.path.join(self.output_dir,
                                        self.tdl.name + "-ramdisk")
        self.kernelcache = os.path.join(self.data_dir, "kernels",
                                        self.tdl.distro + self.tdl.update + self.tdl.arch + "-kernel")
        self.initrdcache = os.path.join(self.data_dir, "kernels",
                                        self.tdl.distro + self.tdl.update + self.tdl.arch + "-ramdisk")

        self.cmdline = "method=" + self.url + " ks=file:/ks.cfg"

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.debug("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-T", "-J",
                                           "-V", "Custom", "-no-emul-boot",
                                           "-b", "isolinux/isolinux.bin",
                                           "-c", "isolinux/boot.cat",
                                           "-boot-load-size", "4",
                                           "-boot-info-table", "-v",
                                           "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def _check_iso_tree(self, customize_or_icicle):
        kernel = os.path.join(self.iso_contents, "isolinux", "vmlinuz")
        if not os.path.exists(kernel):
            raise oz.OzException.OzException("Fedora/Red Hat installs can only be done using a boot.iso (netinst) or DVD image (LiveCDs are not supported)")

    def _modify_isolinux(self, initrdline):
        """
        Method to modify the isolinux.cfg file on a RedHat style CD.
        """
        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(self.iso_contents, "isolinux",
                                   "isolinux.cfg")

        with open(isolinuxcfg, "w") as f:
            f.write("""\
default customiso
timeout 1
prompt 0
label customiso
  kernel vmlinuz
%s
""" % (initrdline))

    def _copy_kickstart(self, outname):
        """
        Method to copy and modify a RedHat style kickstart file.
        """
        self.log.debug("Putting the kickstart in place")

        if self.default_auto_file():
            def _kssub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify kickstart files as appropriate.
                """
                if re.match("^rootpw", line):
                    return "rootpw " + self.rootpw + '\n'
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _kssub)
        else:
            shutil.copy(self.auto, outname)

    def _get_service_runlevel_link(self, g_handle, service):
        """
        Method to find the runlevel link(s) for a service based on the name
        and the (detected) default runlevel.
        """
        runlevel = self.get_default_runlevel(g_handle)

        lines = g_handle.cat('/etc/init.d/' + service).split("\n")
        startlevel = "99"
        for line in lines:
            if re.match('# chkconfig:', line):
                try:
                    startlevel = line.split(':')[1].split()[1]
                except:
                    pass
                break

        return "/etc/rc.d/rc" + runlevel + ".d/S" + startlevel + service

    def _image_ssh_teardown_step_1(self, g_handle):
        """
        First step to undo _image_ssh_setup (remove authorized keys).
        """
        self.log.debug("Teardown step 1")
        # reset the authorized keys
        self.log.debug("Resetting authorized_keys")
        self._guestfs_path_restore(g_handle, '/root/.ssh')

    def _image_ssh_teardown_step_2(self, g_handle):
        """
        Second step to undo _image_ssh_setup (reset sshd service).
        """
        self.log.debug("Teardown step 2")
        # remove custom sshd_config
        self.log.debug("Resetting sshd_config")
        self._guestfs_path_restore(g_handle, '/etc/ssh/sshd_config')

        # reset the service link
        self.log.debug("Resetting sshd service")
        if g_handle.exists('/lib/systemd/system/sshd.service'):
            if not self.sshd_was_active:
                g_handle.rm('/etc/systemd/system/multi-user.target.wants/sshd.service')
        else:
            startuplink = self._get_service_runlevel_link(g_handle, 'sshd')
            self._guestfs_path_restore(g_handle, startuplink)

    def _image_ssh_teardown_step_3(self, g_handle):
        """
        Third step to undo _image_ssh_setup (reset iptables).
        """
        self.log.debug("Teardown step 3")
        # reset iptables
        self.log.debug("Resetting iptables rules")
        self._guestfs_path_restore(g_handle, '/etc/sysconfig/iptables')

    def _image_ssh_teardown_step_4(self, g_handle):
        """
        Fourth step to undo _image_ssh_setup (remove guest announcement).
        """
        self.log.debug("Teardown step 4")
        self.log.debug("Removing announcement to host")
        self._guestfs_remove_if_exists(g_handle,
                                       '/etc/NetworkManager/dispatcher.d/99-reportip')

        # remove announce cronjob
        self.log.debug("Resetting announcement to host")
        self._guestfs_remove_if_exists(g_handle, '/etc/cron.d/announce')

        # remove reportip
        self.log.debug("Removing reportip")
        self._guestfs_remove_if_exists(g_handle, '/root/reportip')

        # reset the service link
        self.log.debug("Resetting crond service")
        if g_handle.exists('/lib/systemd/system/crond.service'):
            if not self.crond_was_active:
                g_handle.rm('/etc/systemd/system/multi-user.target.wants/crond.service')
        else:
            startuplink = self._get_service_runlevel_link(g_handle, 'crond')
            self._guestfs_path_restore(g_handle, startuplink)

    def _image_ssh_teardown_step_5(self, g_handle):
        """
        Fifth step to undo _image_ssh_setup (reset SELinux).
        """
        self.log.debug("Teardown step 5")
        self._guestfs_path_restore(g_handle, "/etc/selinux/config")

    def _image_ssh_teardown_step_6(self, g_handle):
        """
        Sixth step to undo changes by the operating system.  For instance,
        during first boot openssh generates ssh host keys and stores them
        in /etc/ssh.  Since this image might be cached later on, this method
        removes those keys.
        """
        for f in ["/etc/ssh/ssh_host_dsa_key", "/etc/ssh/ssh_host_dsa_key.pub",
                  "/etc/ssh/ssh_host_rsa_key", "/etc/ssh/ssh_host_rsa_key.pub",
                  "/etc/ssh/ssh_host_ecdsa_key", "/etc/ssh/ssh_host_ecdsa_key.pub",
                  "/etc/ssh/ssh_host_key", "/etc/ssh/ssh_host_key.pub"]:
            self._guestfs_remove_if_exists(g_handle, f)

    def _collect_teardown(self, libvirt_xml):
        """
        Method to reverse the changes done in _collect_setup.
        """
        self.log.info("Collection Teardown")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        try:
            self._image_ssh_teardown_step_1(g_handle)

            self._image_ssh_teardown_step_2(g_handle)

            self._image_ssh_teardown_step_3(g_handle)

            self._image_ssh_teardown_step_4(g_handle)

            self._image_ssh_teardown_step_5(g_handle)

            self._image_ssh_teardown_step_6(g_handle)
        finally:
            self._guestfs_handle_cleanup(g_handle)
            shutil.rmtree(self.icicle_tmp)

    def _image_ssh_setup_step_1(self, g_handle):
        """
        First step for allowing remote access (generate and upload ssh keys).
        """
        # part 1; upload the keys
        self.log.debug("Step 1: Uploading ssh keys")
        self._guestfs_path_backup(g_handle, '/root/.ssh')
        g_handle.mkdir('/root/.ssh')

        self._guestfs_path_backup(g_handle, '/root/.ssh/authorized_keys')

        self._generate_openssh_key(self.sshprivkey)

        g_handle.upload(self.sshprivkey + ".pub", '/root/.ssh/authorized_keys')

    def _image_ssh_setup_step_2(self, g_handle):
        """
        Second step for allowing remote access (configure sshd).
        """
        # part 2; check and setup sshd
        self.log.debug("Step 2: setup sshd")
        if not g_handle.exists('/usr/sbin/sshd'):
            raise oz.OzException.OzException("ssh not installed on the image, cannot continue")

        if g_handle.exists('/lib/systemd/system/sshd.service'):
            if g_handle.exists('/etc/systemd/system/multi-user.target.wants/sshd.service'):
                self.sshd_was_active = True
            else:
                g_handle.ln_sf('/lib/systemd/system/sshd.service',
                               '/etc/systemd/system/multi-user.target.wants/sshd.service')
        else:
            startuplink = self._get_service_runlevel_link(g_handle, 'sshd')
            self._guestfs_path_backup(g_handle, startuplink)
            g_handle.ln_sf('/etc/init.d/sshd', startuplink)

        sshd_config_file = os.path.join(self.icicle_tmp, "sshd_config")
        with open(sshd_config_file, 'w') as f:
            f.write(self.sshd_config)

        try:
            self._guestfs_path_backup(g_handle, '/etc/ssh/sshd_config')
            g_handle.upload(sshd_config_file, '/etc/ssh/sshd_config')
        finally:
            os.unlink(sshd_config_file)

    def _image_ssh_setup_step_3(self, g_handle):
        """
        Third step for allowing remote access (open up the firewall).
        """
        # part 3; open up iptables
        self.log.debug("Step 3: Open up the firewall")
        self._guestfs_path_backup(g_handle, '/etc/sysconfig/iptables')

    def _image_ssh_setup_step_4(self, g_handle):
        """
        Fourth step for allowing remote access (make the guest announce itself
        on bootup).
        """
        # part 4; make sure the guest announces itself
        self.log.debug("Step 4: Guest announcement")

        scriptfile = os.path.join(self.icicle_tmp, "script")

        if g_handle.exists("/etc/NetworkManager/dispatcher.d"):
            with open(scriptfile, 'w') as f:
                f.write("""\
#!/bin/bash

if [ "$1" = "eth0" -a "$2" = "up" ]; then
    echo -n "!$DHCP4_IP_ADDRESS,%s!" > /dev/ttyS1
fi
""" % (self.uuid))

            try:
                g_handle.upload(scriptfile,
                                '/etc/NetworkManager/dispatcher.d/99-reportip')
                g_handle.chmod(0755,
                               '/etc/NetworkManager/dispatcher.d/99-reportip')
            finally:
                os.unlink(scriptfile)

        if not g_handle.exists('/usr/sbin/crond'):
            raise oz.OzException.OzException("cron not installed on the image, cannot continue")

        with open(scriptfile, 'w') as f:
            f.write("""\
#!/bin/bash
DEV=$(/bin/awk '{if ($2 == 0) print $1}' /proc/net/route) &&
[ -z "$DEV" ] && exit 0
ADDR=$(/sbin/ip -4 -o addr show dev $DEV | /bin/awk '{print $4}' | /bin/cut -d/ -f1) &&
[ -z "$ADDR" ] && exit 0
echo -n "!$ADDR,%s!" > /dev/ttyS1
""" % (self.uuid))

        try:
            g_handle.upload(scriptfile, '/root/reportip')
            g_handle.chmod(0755, '/root/reportip')
        finally:
            os.unlink(scriptfile)

        announcefile = os.path.join(self.icicle_tmp, "announce")
        with open(announcefile, 'w') as f:
            f.write('*/1 * * * * root /bin/bash -c "/root/reportip"\n')

        try:
            g_handle.upload(announcefile, '/etc/cron.d/announce')
        finally:
            os.unlink(announcefile)

        if g_handle.exists('/lib/systemd/system/crond.service'):
            if g_handle.exists('/etc/systemd/system/multi-user.target.wants/crond.service'):
                self.crond_was_active = True
            else:
                g_handle.ln_sf('/lib/systemd/system/crond.service',
                               '/etc/systemd/system/multi-user.target.wants/crond.service')
        else:
            startuplink = self._get_service_runlevel_link(g_handle, 'crond')
            self._guestfs_path_backup(g_handle, startuplink)
            g_handle.ln_sf('/etc/init.d/crond', startuplink)

    def _image_ssh_setup_step_5(self, g_handle):
        """
        Fifth step for allowing remote access (set SELinux to permissive).
        """
        # part 5; set SELinux to permissive mode so we don't have to deal with
        # incorrect contexts
        self.log.debug("Step 5: Set SELinux to permissive mode")
        self._guestfs_path_backup(g_handle, '/etc/selinux/config')

        selinuxfile = self.icicle_tmp + "/selinux"
        with open(selinuxfile, 'w') as f:
            f.write("SELINUX=permissive\n")
            f.write("SELINUXTYPE=targeted\n")

        try:
            g_handle.upload(selinuxfile, "/etc/selinux/config")
        finally:
            os.unlink(selinuxfile)

    def _collect_setup(self, libvirt_xml):
        """
        Setup the guest for remote access.
        """
        self.log.info("Collection Setup")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        # we have to do 5 things to make sure we can ssh into RHEL/Fedora:
        # 1)  Upload our ssh key
        # 2)  Make sure sshd is running on boot
        # 3)  Make sure that port 22 is open in the firewall
        # 4)  Make the guest announce itself to the host
        # 5)  Set SELinux to permissive mode

        try:
            try:
                self._image_ssh_setup_step_1(g_handle)

                try:
                    self._image_ssh_setup_step_2(g_handle)

                    try:
                        self._image_ssh_setup_step_3(g_handle)

                        try:
                            self._image_ssh_setup_step_4(g_handle)

                            try:
                                self._image_ssh_setup_step_5(g_handle)
                            except:
                                self._image_ssh_teardown_step_5(g_handle)
                                raise
                        except:
                            self._image_ssh_teardown_step_4(g_handle)
                            raise
                    except:
                        self._image_ssh_teardown_step_3(g_handle)
                        raise
                except:
                    self._image_ssh_teardown_step_2(g_handle)
                    raise
            except:
                self._image_ssh_teardown_step_1(g_handle)
                raise

        finally:
            self._guestfs_handle_cleanup(g_handle)

    def do_icicle(self, guestaddr):
        """
        Method to collect the package information and generate the ICICLE
        XML.
        """
        self.log.debug("Generating ICICLE")
        stdout, stderr, retcode = self.guest_execute_command(guestaddr,
                                                             'rpm -qa',
                                                             timeout=30)

        package_split = stdout.split("\n")

        extrasplit = None
        if self.tdl.icicle_extra_cmd:
            extrastdout, stderr, retcode = self.guest_execute_command(guestaddr,
                                                                      self.tdl.icicle_extra_cmd,
                                                                      timeout=30)
            extrasplit = extrastdout.split("\n")

            if len(package_split) != len(extrasplit):
                raise oz.OzException.OzException("Invalid extra package command; it must return the same set of packages as 'rpm -qa'")

        return self._output_icicle_xml(package_split, self.tdl.description,
                                       extrasplit)

    def _get_kernel_from_treeinfo(self, fetchurl):
        """
        Internal method to download and parse the .treeinfo file from a URL.  If
        the .treeinfo file does not exist, or it does not have the keys that we
        expect, this method raises an error.
        """
        treeinfourl = fetchurl + "/.treeinfo"

        # first we check if the .treeinfo exists; this throws an exception if
        # it is missing
        info = oz.ozutil.http_get_header(treeinfourl)
        if info['HTTP-Code'] != 200:
            raise oz.OzException.OzException("Could not find %s" % (treeinfourl))

        treeinfo = os.path.join(self.icicle_tmp, "treeinfo")
        self.log.debug("Going to write treeinfo to %s" % (treeinfo))
        treeinfofd = os.open(treeinfo, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        fp = os.fdopen(treeinfofd)
        try:
            os.unlink(treeinfo)
            self.log.debug("Trying to get treeinfo from " + treeinfourl)
            oz.ozutil.http_download_file(treeinfourl, treeinfofd,
                                         False, self.log)

            # if we made it here, the .treeinfo existed.  Parse it and
            # find out the location of the vmlinuz and initrd
            self.log.debug("Got treeinfo, parsing")
            os.lseek(treeinfofd, 0, os.SEEK_SET)
            config = configparser.SafeConfigParser()
            config.readfp(fp)
            section = "images-%s" % (self.tdl.arch)
            kernel = oz.ozutil.config_get_key(config, section, "kernel", None)
            initrd = oz.ozutil.config_get_key(config, section, "initrd", None)
        finally:
            fp.close()

        if kernel is None or initrd is None:
            raise oz.OzException.OzException("Empty kernel or initrd")

        self.log.debug("Returning kernel %s and initrd %s" % (kernel, initrd))
        return (kernel, initrd)

    def _create_cpio_initrd(self, kspath):
        """
        Internal method to create a modified CPIO initrd
        """
        # if initrdtype is cpio, then we can just append a gzipped
        # archive onto the end of the initrd
        extrafname = os.path.join(self.icicle_tmp, "extra.cpio")
        self.log.debug("Writing cpio to %s" % (extrafname))
        cpiofiledict = {}
        cpiofiledict[kspath] = 'ks.cfg'
        oz.ozutil.write_cpio(cpiofiledict, extrafname)

        try:
            shutil.copyfile(self.initrdcache, self.initrdfname)
            oz.ozutil.gzip_append(extrafname, self.initrdfname)
        finally:
            os.unlink(extrafname)

    def _create_ext2_initrd(self, kspath):
        """
        Internal method to create a modified ext2 initrd
        """
        # in this case, the archive is not CPIO but is an ext2
        # filesystem.  use guestfs to mount it and add the kickstart
        self.log.debug("Creating temporary directory")
        tmpdir = os.path.join(self.icicle_tmp, "initrd")
        oz.ozutil.mkdir_p(tmpdir)

        ext2file = os.path.join(tmpdir, "initrd.ext2")
        self.log.debug("Uncompressing initrd %s to %s" % (self.initrdfname, ext2file))
        inf = gzip.open(self.initrdcache, 'rb')
        outf = open(ext2file, "w")
        try:
            outf.writelines(inf)
            inf.close()

            g = guestfs.GuestFS()
            g.add_drive_opts(ext2file, format='raw')
            self.log.debug("Launching guestfs")
            g.launch()

            g.mount_options('', g.list_devices()[0], "/")

            g.upload(kspath, "/ks.cfg")

            g.sync()
            g.umount_all()
            g.kill_subprocess()

            # kickstart is added, lets recompress it
            oz.ozutil.gzip_create(ext2file, self.initrdfname)
        finally:
            os.unlink(ext2file)

    def _initrd_inject_ks(self, fetchurl, force_download):
        """
        Internal method to download and inject a kickstart into an initrd.
        """
        # we first see if we can use direct kernel booting, as that is
        # faster than downloading the ISO
        kernel = None
        initrd = None
        try:
            (kernel, initrd) = self._get_kernel_from_treeinfo(fetchurl)
        except:
            pass

        if kernel is None:
            self.log.debug("Kernel was None, trying images/pxeboot/vmlinuz")
            # we couldn't find the kernel in the treeinfo, so try a
            # hard-coded path
            kernel = "images/pxeboot/vmlinuz"
        if initrd is None:
            self.log.debug("Initrd was None, trying images/pxeboot/initrd.img")
            # we couldn't find the initrd in the treeinfo, so try a
            # hard-coded path
            initrd = "images/pxeboot/initrd.img"

        self._get_original_media('/'.join([self.url.rstrip('/'),
                                           kernel.lstrip('/')]),
                                 self.kernelcache, force_download)

        try:
            self._get_original_media('/'.join([self.url.rstrip('/'),
                                               initrd.lstrip('/')]),
                                     self.initrdcache, force_download)
        except:
            os.unlink(self.kernelfname)
            raise

        # if we made it here, then we can copy the kernel into place
        shutil.copyfile(self.kernelcache, self.kernelfname)

        try:
            kspath = os.path.join(self.icicle_tmp, "ks.cfg")
            self._copy_kickstart(kspath)

            try:
                if self.initrdtype == "cpio":
                    self._create_cpio_initrd(kspath)
                elif self.initrdtype == "ext2":
                    self._create_ext2_initrd(kspath)
                else:
                    raise oz.OzException.OzException("Invalid initrdtype, this is a programming error")
            finally:
                os.unlink(kspath)
        except:
            os.unlink(self.kernelfname)
            raise

    def generate_install_media(self, force_download=False,
                               customize_or_icicle=False):
        """
        Method to generate the install media for RedHat based operating
        systems.  If force_download is False (the default), then the
        original media will only be fetched if it is not cached locally.  If
        force_download is True, then the original media will be downloaded
        regardless of whether it is cached locally.
        """
        fetchurl = self.url
        if self.tdl.installtype == 'url':
            # set the fetchurl up-front so that if the OS doesn't support
            # initrd injection, or the injection fails for some reason, we
            # fall back to the boot.iso
            fetchurl += "/images/boot.iso"

            if self.initrdtype is not None:
                self.log.debug("Installtype is URL, trying to do direct kernel boot")
                try:
                    return self._initrd_inject_ks(self.url, force_download)
                except Exception as err:
                    # if any of the above failed, we couldn't use the direct
                    # kernel/initrd build method.  Fall back to trying to fetch
                    # the boot.iso instead
                    self.log.debug("Could not do direct boot, fetching boot.iso instead (the following error message is useful for bug reports, but can be ignored)")
                    self.log.debug(err)

        return self._iso_generate_install_media(fetchurl, force_download,
                                                customize_or_icicle)

    def cleanup_install(self):
        """
        Method to cleanup any transient install data.
        """
        self.log.info("Cleaning up after install")

        for fname in [self.output_iso, self.initrdfname, self.kernelfname]:
            try:
                os.unlink(fname)
            except:
                pass

        if not self.cache_original_media:
            for fname in [self.orig_iso, self.kernelcache, self.initrdcache]:
                try:
                    os.unlink(fname)
                except:
                    pass

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        return self._do_install(timeout, force, 0, self.kernelfname,
                                self.initrdfname, self.cmdline)

class RedHatLinuxCDYumGuest(RedHatLinuxCDGuest):
    """
    Class for RedHat-based CD guests with yum support.
    """
    def _check_url(self, iso=True, url=True):
        """
        Method to check if a URL specified by the user is one that will work
        with anaconda.
        """
        url = RedHatLinuxCDGuest._check_url(self, iso, url)

        if self.tdl.installtype == 'url':
            # The HTTP/1.1 specification allows for servers that don't support
            # byte ranges; if the client requests it and the server doesn't
            # support it, it is supposed to return a header that looks like:
            #
            #   Accept-Ranges: none
            #
            # You can see this in action by editing httpd.conf:
            #
            #   ...
            #   LoadModule headers_module
            #   ...
            #   Header set Accept-Ranges "none"
            #
            # and then trying to fetch a file with wget:
            #
            #   wget --header="Range: bytes=5-10" http://path/to/my/file
            #
            # Unfortunately, anaconda does not honor this server header, and
            # blindly requests a byte range anyway.  When this happens, the
            # server throws a "403 Forbidden", and the URL install fails.
            #
            # There is the additional problem of mirror lists.  If we take
            # the original URL that was given to us, and it happens to be
            # a redirect, then what can happen is that each individual package
            # during the install can come from a different mirror (some of
            # which may not support the byte ranges).  To avoid both of these
            # problems, resolve the (possible) redirect to a real mirror, and
            # check if we hit a server that doesn't support ranges.  If we do
            # hit one of these, try up to 5 times to redirect to a different
            # mirror.  If after this we still cannot find a server that
            # supports byte ranges, fail.
            count = 5
            while count > 0:
                info = oz.ozutil.http_get_header(url, redirect=False)

                if 'Accept-Ranges' in info and info['Accept-Ranges'] == "none":
                    if url == info['Redirect-URL']:
                        # optimization; if the URL we resolved to is exactly
                        # the same as what we started with, this is *not*
                        # a redirect, and we should fail immediately
                        count = 0
                        break

                    count -= 1
                    continue

                if 'Redirect-URL' in info and info['Redirect-URL'] is not None:
                    url = info['Redirect-URL']
                break

            if count == 0:
                raise oz.OzException.OzException("%s URL installs cannot be done using servers that don't accept byte ranges.  Please try another mirror" % (self.tdl.distro))

        return url

    def _customize_repos(self, guestaddr):
        """
        Method to generate and upload custom repository files based on the TDL.
        """
        self.log.debug("Installing additional repository files")

        for repo in list(self.tdl.repositories.values()):
            filename = repo.name.replace(" ", "_") + ".repo"
            localname = os.path.join(self.icicle_tmp, filename)
            with open(localname, 'w') as f:
                f.write("[%s]\n" % repo.name.replace(" ", "_"))
                f.write("name=%s\n" % repo.name)
                f.write("baseurl=%s\n" % repo.url)
                f.write("skip_if_unavailable=1\n")
                f.write("enabled=1\n")

                if repo.sslverify:
                    f.write("sslverify=1\n")
                else:
                    f.write("sslverify=0\n")

                if repo.signed:
                    f.write("gpgcheck=1\n")
                else:
                    f.write("gpgcheck=0\n")

            try:
                remotename = os.path.join("/etc/yum.repos.d/", filename)
                self.guest_live_upload(guestaddr, localname, remotename)
            finally:
                os.unlink(localname)

    def _install_packages(self, guestaddr, packstr):
        self.guest_execute_command(guestaddr, 'yum -y install %s' % (packstr))

    def _remove_repos(self, guestaddr):
        for repo in list(self.tdl.repositories.values()):
            if not repo.persisted:
                filename = os.path.join("/etc/yum.repos.d",
                                        repo.name.replace(" ", "_") + ".repo")
                self.guest_execute_command(guestaddr, "rm -f " + filename,
                                           timeout=30)

class RedHatFDGuest(oz.Guest.FDGuest):
    """
    Class for RedHat-based floppy guests.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 macaddress):
        oz.Guest.FDGuest.__init__(self, tdl, config, auto, output_disk,
                                  nicmodel, None, None, diskbus, macaddress)

        if self.tdl.arch != "i386":
            raise oz.OzException.OzException("Invalid arch " + self.tdl.arch + "for " + self.tdl.distro + " guest")

    def _modify_floppy(self):
        """
        Method to make the floppy auto-boot with appropriate parameters.
        """
        oz.ozutil.mkdir_p(self.floppy_contents)

        self.log.debug("Putting the kickstart in place")

        output_ks = os.path.join(self.floppy_contents, "ks.cfg")

        if self.default_auto_file():
            def _kssub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify kickstart files as appropriate for RHL.
                """
                if re.match("^url", line):
                    return "url --url " + self.url + "\n"
                elif re.match("^rootpw", line):
                    return "rootpw " + self.rootpw + "\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, output_ks, _kssub)
        else:
            shutil.copy(self.auto, output_ks)

        oz.ozutil.subprocess_check_output(["mcopy", "-i", self.output_floppy,
                                           output_ks, "::KS.CFG"],
                                          printfn=self.log.debug)

        self.log.debug("Modifying the syslinux.cfg")

        syslinux = os.path.join(self.floppy_contents, "SYSLINUX.CFG")
        with open(syslinux, 'w') as outfile:
            outfile.write("""\
default customboot
prompt 1
timeout 1
label customboot
  kernel vmlinuz
  append initrd=initrd.img lang= devfs=nomount ramdisk_size=9126 ks=floppy method=%s
""" % (self.url))

        # sometimes, syslinux.cfg on the floppy gets marked read-only.  Avoid
        # problems with the subsequent mcopy by marking it read/write.
        oz.ozutil.subprocess_check_output(["mattrib", "-r", "-i",
                                           self.output_floppy,
                                           "::SYSLINUX.CFG"],
                                          printfn=self.log.debug)

        oz.ozutil.subprocess_check_output(["mcopy", "-n", "-o", "-i",
                                           self.output_floppy, syslinux,
                                           "::SYSLINUX.CFG"],
                                          printfn=self.log.debug)

    def generate_install_media(self, force_download=False,
                               customize_or_icicle=False):
        """
        Method to generate the install media for RedHat based operating
        systems that install from floppy.  If force_download is False (the
        default), then the original media will only be fetched if it is
        not cached locally.  If force_download is True, then the original
        media will be downloaded regardless of whether it is cached locally.
        """
        self.log.info("Generating install media")

        if not force_download:
            if os.access(self.jeos_filename, os.F_OK):
                # if we found a cached JEOS, we don't need to do anything here;
                # we'll copy the JEOS itself later on
                return
            elif os.access(self.modified_floppy_cache, os.F_OK):
                self.log.info("Using cached modified media")
                shutil.copyfile(self.modified_floppy_cache, self.output_floppy)
                return

        self._get_original_floppy(self.url + "/images/bootnet.img",
                                  force_download)
        self._copy_floppy()
        try:
            self._modify_floppy()
            if self.cache_modified_media:
                self.log.info("Caching modified media for future use")
                shutil.copyfile(self.output_floppy, self.modified_floppy_cache)
        finally:
            self._cleanup_floppy()

########NEW FILE########
__FILENAME__ = RHEL_2_1
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-2.1 installation
"""

import oz.RedHat
import oz.OzException

class RHEL21Guest(oz.RedHat.RedHatFDGuest):
    """
    Class for RHEL-2.1 GOLD, U2, U3, U4, U5, and U6 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.RedHat.RedHatFDGuest.__init__(self, tdl, config, auto, output_disk,
                                         netdev, diskbus, macaddress)

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 2.1 kickstart file.
        """
        return oz.ozutil.generate_full_auto_path("RHEL2.1.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-2.1 installs.
    """
    if tdl.update in ["GOLD", "U2", "U3", "U4", "U5", "U6"]:
        if netdev is None:
            netdev = 'pcnet'
        return RHEL21Guest(tdl, config, auto, output_disk, netdev, diskbus,
                           macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL 2.1: GOLD, U2, U3, U4, U5, U6"

########NEW FILE########
__FILENAME__ = RHEL_3
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-3 installation
"""

import re
import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHEL3Guest(oz.RedHat.RedHatLinuxCDGuest):
    """
    Class for RHEL-3 GOLD, U1, U2, U3, U4, U5, U6, U7, U8, and U9 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        iso_support = True
        if tdl.distro == "RHEL-3":
            iso_support = False

        # although we could use ext2 for the initrdtype here (and hence get
        # fast initial installs), it isn't super reliable on RHEL-3.  Just
        # disable it and fall back to the boot.iso method which is more reliable
        oz.RedHat.RedHatLinuxCDGuest.__init__(self, tdl, config, auto,
                                              output_disk, netdev, diskbus,
                                              iso_support, True, None,
                                              macaddress)

        # override the sshd_config value set in RedHatLinuxCDGuest.__init__
        self.sshd_config = """\
SyslogFacility AUTHPRIV
PasswordAuthentication yes
ChallengeResponseAuthentication no
X11Forwarding yes
Subsystem	sftp	/usr/libexec/openssh/sftp-server
"""

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method="
        if self.tdl.installtype == "url":
            initrdline += self.url + "\n"
        else:
            initrdline += "cdrom:/dev/cdrom\n"
        self._modify_isolinux(initrdline)

    def _check_pvd(self):
        """
        Method to ensure the the boot ISO for an ISO install is a DVD
        """
        cdfd = open(self.orig_iso, "r")
        pvd = self._get_primary_volume_descriptor(cdfd)
        cdfd.close()

        if pvd.system_identifier != "LINUX                           ":
            raise oz.OzException.OzException("Invalid system identifier on ISO for " + self.tdl.distro + " install")

        if self.tdl.distro == "RHEL-3":
            if self.tdl.installtype == "iso":
                raise oz.OzException.OzException("BUG: shouldn't be able to reach RHEL-3 with ISO checking")
            # The boot ISOs for RHEL-3 don't have a whole lot of identifying
            # information.  We just pass through here, doing nothing
        else:
            if self.tdl.installtype == "iso":
                if not re.match(r"CentOS-3(\.[0-9])? Disk 1", pvd.volume_identifier) and not re.match(r"CentOS-3(\.[0-9])? server", pvd.volume_identifier) and not re.match(r"CentOS-3(\.[0-9])? " + self.tdl.arch + " DVD", pvd.volume_identifier):
                    raise oz.OzException.OzException("Only DVDs are supported for CentOS-3 ISO installs")
            # The boot ISOs for CentOS-3 don't have a whole lot of identifying
            # information.  We just pass through here, doing nothing

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 3 kickstart files.
        """
        return oz.ozutil.generate_full_auto_path("RHEL3.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-3 installs.
    """
    if tdl.update in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9"]:
        return RHEL3Guest(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL/CentOS 3: GOLD, U1, U2, U3, U4, U5, U6, U7, U8, U9"

########NEW FILE########
__FILENAME__ = RHEL_4
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-4 installation
"""

import re
import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHEL4Guest(oz.RedHat.RedHatLinuxCDGuest):
    """
    Class for RHEL-4 GOLD, U1, U2, U3, U4, U5, U6, U7, U8, and U9 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 macaddress):
        # we set initrdtype to None because RHEL-4 spews errors using direct
        # kernel/initrd booting.  The odd part is that it actually works, but
        # it looks ugly so for now we will just always use the boot.iso method
        oz.RedHat.RedHatLinuxCDGuest.__init__(self, tdl, config, auto,
                                              output_disk, nicmodel, diskbus,
                                              True, True, None, macaddress)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method="
        if self.tdl.installtype == "url":
            initrdline += self.url + "\n"
        else:
            initrdline += "cdrom:/dev/cdrom\n"
        self._modify_isolinux(initrdline)

    def _check_pvd(self):
        """
        Method to ensure that boot ISO is a DVD (we cannot use boot CDs to
        install RHEL-4/CentOS-4 since it requires a switch during install,
        which we cannot detect).
        """
        with open(self.orig_iso, "r") as cdfd:
            pvd = self._get_primary_volume_descriptor(cdfd)

        # all of the below should have "LINUX" as their system_identifier,
        # so check it here
        if pvd.system_identifier != "LINUX                           ":
            raise oz.OzException.OzException("Invalid system identifier on ISO for " + self.tdl.distro + " install")

        if self.tdl.distro == "RHEL-4":
            if self.tdl.installtype == 'iso':
                # unfortunately RHEL-4 has the same volume identifier for both
                # DVDs and CDs.  To tell them apart, we assume that if the
                # size is smaller than 1GB, this is a CD
                if not re.match("RHEL/4(-U[0-9])?", pvd.volume_identifier) or (pvd.space_size * 2048) < 1 * 1024 * 1024 * 1024:
                    raise oz.OzException.OzException("Only DVDs are supported for RHEL-4 ISO installs")
            else:
                # url installs
                if not pvd.volume_identifier.startswith("Red Hat Enterprise Linux"):
                    raise oz.OzException.OzException("Invalid boot.iso for RHEL-4 URL install")
        elif self.tdl.distro == "CentOS-4":
            if self.tdl.installtype == 'iso':
                if not re.match(r"CentOS 4(\.[0-9])?.*DVD", pvd.volume_identifier):
                    raise oz.OzException.OzException("Only DVDs are supported for CentOS-4 ISO installs")
            else:
                # url installs
                if not re.match("CentOS *", pvd.volume_identifier):
                    raise oz.OzException.OzException("Invalid boot.iso for CentOS-4 URL install")

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 4 kickstart file.
        """
        return oz.ozutil.generate_full_auto_path("RHEL4.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-4 installs.
    """
    if tdl.update in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7"]:
        return RHEL4Guest(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)
    if tdl.update in ["U8", "U9"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return RHEL4Guest(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL/CentOS/Scientific Linux 4: GOLD, U1, U2, U3, U4, U5, U6, U7, U8, U9"

########NEW FILE########
__FILENAME__ = RHEL_5
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-5 installation
"""

import re
import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHEL5Guest(oz.RedHat.RedHatLinuxCDYumGuest):
    """
    Class for RHEL-5 GOLD, U1, U2, U3, U4, U5, U6, U7, U8, U9 and U10 installation.
    """
    def __init__(self, tdl, config, auto, nicmodel, diskbus, output_disk=None,
                 macaddress=None):
        oz.RedHat.RedHatLinuxCDYumGuest.__init__(self, tdl, config, auto,
                                                 output_disk, nicmodel, diskbus,
                                                 True, True, "cpio", macaddress)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method="
        if self.tdl.installtype == "url":
            initrdline += self.url + "\n"
        else:
            initrdline += "cdrom:/dev/cdrom\n"
        self._modify_isolinux(initrdline)

    def _check_pvd(self):
        """
        Method to ensure that boot ISO is a DVD (we cannot use boot CDs to
        install RHEL-5/CentOS-5 since it requires a switch during install,
        which we cannot detect).
        """
        with open(self.orig_iso, "r") as cdfd:
            pvd = self._get_primary_volume_descriptor(cdfd)

        # all of the below should have "LINUX" as their system_identifier,
        # so check it here
        if pvd.system_identifier != "LINUX                           ":
            raise oz.OzException.OzException("Invalid system identifier on ISO for " + self.tdl.distro + " install")

        if self.tdl.distro == "RHEL-5":
            if self.tdl.installtype == 'iso':
                if not re.match(r"RHEL/5(\.[0-9])? " + self.tdl.arch + " DVD",
                                pvd.volume_identifier):
                    raise oz.OzException.OzException("Only DVDs are supported for RHEL-5 ISO installs")
            else:
                # url installs
                if not pvd.volume_identifier.startswith("Red Hat Enterprise Linux"):
                    raise oz.OzException.OzException("Invalid boot.iso for RHEL-5 URL install")
        elif self.tdl.distro == "CentOS-5":
            # CentOS-5
            if self.tdl.installtype == 'iso':
                # unfortunately CentOS-5 has the same volume identifier for both
                # DVDs and CDs.  To tell them apart, we assume that if the
                # size is smaller than 1GB, this is a CD
                if not re.match(r"CentOS_5.[0-9]_Final", pvd.volume_identifier) or (pvd.space_size * 2048) < 1 * 1024 * 1024 * 1024:
                    raise oz.OzException.OzException("Only DVDs are supported for CentOS-5 ISO installs")
            else:
                # url installs
                if not re.match(r"CentOS *", pvd.volume_identifier):
                    raise oz.OzException.OzException("Invalid boot.iso for CentOS-5 URL install")
        elif self.tdl.distro == "SLC-5":
            # SLC-5
            if self.tdl.installtype == 'iso':
                if not re.match(r"Scientific Linux CERN 5.[0-9]", pvd.volume_identifier):
                    raise oz.OzException.OzException("Only DVDs are supported for SLC-5 ISO installs")
            else:
                # url installs
                if not re.match(r"CentOS *", pvd.volume_identifier):
                    raise oz.OzException.OzException("Invalid boot.iso for SLC-5 URL install")

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 5 kickstart file.
        """
        return oz.ozutil.generate_full_auto_path("RHEL5.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-5 installs.
    """
    if tdl.update in ["GOLD", "U1", "U2", "U3"]:
        return RHEL5Guest(tdl, config, auto, netdev, diskbus, output_disk,
                          macaddress)
    if tdl.update in ["U4", "U5", "U6", "U7", "U8", "U9", "U10"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return RHEL5Guest(tdl, config, auto, netdev, diskbus, output_disk,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL/OL/CentOS/Scientific Linux{,CERN} 5: GOLD, U1, U2, U3, U4, U5, U6, U7, U8, U9, U10"

########NEW FILE########
__FILENAME__ = RHEL_6
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-6 installation
"""

import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHEL6Guest(oz.RedHat.RedHatLinuxCDYumGuest):
    """
    Class for RHEL-6 installation
    """
    def __init__(self, tdl, config, auto, output_disk=None, netdev=None,
                 diskbus=None, macaddress=None):
        oz.RedHat.RedHatLinuxCDYumGuest.__init__(self, tdl, config, auto,
                                                 output_disk, netdev, diskbus,
                                                 True, True, "cpio", macaddress)

    def _modify_iso(self):
        """
        Method to modify the ISO for autoinstallation.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg"
        if self.tdl.installtype == "url":
            initrdline += " repo=" + self.url + "\n"
        else:
            initrdline += "\n"
        self._modify_isolinux(initrdline)

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 6 kickstart files.
        """
        return oz.ozutil.generate_full_auto_path("RHEL6.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-6 installs.
    """
    if tdl.update.isdigit():
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return RHEL6Guest(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL/OL/CentOS/Scientific Linux{,CERN} 6: 0, 1, 2, 3, 4, 5"

########NEW FILE########
__FILENAME__ = RHEL_7
# Copyright (C) 2013  Chris Lalancette <clalancette@gmail.com>
# Copyright (C) 2013  Ian McLeod <imcleod@redhat.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHEL-7 installation
"""

import os

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHEL7Guest(oz.RedHat.RedHatLinuxCDYumGuest):
    """
    Class for RHEL-7 installation
    """
    def __init__(self, tdl, config, auto, output_disk=None, netdev=None,
                 diskbus=None, macaddress=None):
        oz.RedHat.RedHatLinuxCDYumGuest.__init__(self, tdl, config, auto,
                                                 output_disk, netdev, diskbus,
                                                 True, True, "cpio", macaddress)

    def _modify_iso(self):
        """
        Method to modify the ISO for autoinstallation.
        """
        self._copy_kickstart(os.path.join(self.iso_contents, "ks.cfg"))

        initrdline = "  append initrd=initrd.img ks=cdrom:/dev/cdrom:/ks.cfg"
        if self.tdl.installtype == "url":
            initrdline += " repo=" + self.url + "\n"
        else:
            # RHEL6 dropped this command line directive due to an Anaconda bug
            # that has since been fixed.  Note that this used to be "method="
            # but that has been deprecated for some time.
            initrdline += " repo=cdrom:/dev/cdrom"
        self._modify_isolinux(initrdline)

    def get_auto_path(self):
        """
        Method to create the correct path to the RHEL 7 kickstart file.
        """
        return oz.ozutil.generate_full_auto_path("RHEL7.auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHEL-7 installs.
    """
    if tdl.update.isdigit() or tdl.update == "Beta":
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return RHEL7Guest(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHEL 7: Beta"

########NEW FILE########
__FILENAME__ = RHL
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
RHL installation
"""

import re
import os
import shutil

import oz.ozutil
import oz.RedHat
import oz.OzException

class RHL9Guest(oz.RedHat.RedHatLinuxCDGuest):
    """
    Class for RHL-9 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        # RHL-9 doesn't support direct kernel/initrd booting; it hangs right
        # after unpacking the initrd
        oz.RedHat.RedHatLinuxCDGuest.__init__(self, tdl, config, auto,
                                              output_disk, netdev, diskbus,
                                              False, True, None, macaddress)

        if self.tdl.arch != "i386":
            raise oz.OzException.OzException("Invalid arch " + self.tdl.arch + "for RHL guest")

    def _modify_iso(self):
        """
        Method to modify the ISO for autoinstallation.
        """
        self.log.debug("Putting the kickstart in place")

        outname = os.path.join(self.iso_contents, "ks.cfg")

        if self.default_auto_file():
            def _kssub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify kickstart files as appropriate for RHL-9.
                """
                # because we need to do this URL substitution here, we can't use
                # the generic "copy_kickstart()" method
                if re.match("^url", line):
                    return "url --url " + self.url + "\n"
                elif re.match("^rootpw", line):
                    return "rootpw " + self.rootpw + "\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _kssub)
        else:
            shutil.copy(self.auto, outname)

        initrdline = "  append initrd=initrd.img ks=cdrom:/ks.cfg method=" + self.url + "\n"
        self._modify_isolinux(initrdline)

    def get_auto_path(self):
        """
        Method to create the correct path to the RHL kickstart files.
        """
        return oz.ozutil.generate_full_auto_path("RedHatLinux" + self.tdl.update + ".auto")

class RHL7xand8Guest(oz.RedHat.RedHatFDGuest):
    """
    Class for RHL 7.0, 7.1, 7.2, and 8 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, nicmodel, diskbus,
                 macaddress):
        oz.RedHat.RedHatFDGuest.__init__(self, tdl, config, auto, output_disk,
                                         nicmodel, diskbus, macaddress)

    def get_auto_path(self):
        return oz.ozutil.generate_full_auto_path("RedHatLinux" + self.tdl.update + ".auto")

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for RHL installs.
    """
    if tdl.update in ["9"]:
        return RHL9Guest(tdl, config, auto, output_disk, netdev, diskbus,
                         macaddress)
    if tdl.update in ["7.2", "7.3", "8"]:
        return RHL7xand8Guest(tdl, config, auto, output_disk, netdev, diskbus,
                              macaddress)
    if tdl.update in ["7.0", "7.1"]:
        if netdev is None:
            netdev = "ne2k_pci"
        return RHL7xand8Guest(tdl, config, auto, output_disk, netdev, diskbus,
                              macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "RHL: 7.0, 7.1, 7.2, 7.3, 8, 9"

########NEW FILE########
__FILENAME__ = TDL
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Template Description Language (TDL)
"""

import lxml.etree
import base64
import re
import tempfile
import os
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse
try:
    import StringIO
except ImportError:
    from io import StringIO

import oz.ozutil
import oz.OzException

def _xml_get_value(doc, xmlstring, component, optional=False):
    """
    Function to get the contents from an XML node.  It takes 4 arguments:

    doc       - The lxml.etree document to get a value from.
    xmlstring - The XPath string to use.
    component - A string representing which TDL component is being
                looked for (used in error reporting).
    optional  - A boolean describing whether this XML node is allowed to be
                absent or not.  If optional is True and the node is absent,
                None is returned.  If optional is False and the node is
                absent, an exception is raised.  (default: False)

    Returns the content of the XML node if found, None if the node is not
    found and optional is True.
    """
    res = doc.xpath(xmlstring)
    if len(res) == 1:
        return res[0].text
    elif len(res) == 0:
        if optional:
            return None
        else:
            raise oz.OzException.OzException("Failed to find %s in TDL" % (component))
    else:
        raise oz.OzException.OzException("Expected 0 or 1 %s in TDL, saw %d" % (component, len(res)))

def data_from_type(name, contenttype, content):
    '''
    A function to get data out of some content, possibly decoding it depending
    on the content type.  This function understands three types of content:
    raw (where no decoding is necessary), base64 (where the data needs to be
    base64 decoded), and url (where the data needs to be downloaded).  Because
    the data might be large, all data is sent to file handle, which is returned
    from the function.
    '''

    out = tempfile.NamedTemporaryFile()
    if contenttype == 'raw':
        out.write(content)
    elif contenttype == 'base64':
        base64.decode(StringIO.StringIO(content), out)
    elif contenttype == 'url':
        url = urlparse.urlparse(content)
        if url.scheme == "file":
            with open(url.netloc + url.path) as f:
                out.write("".join(f.readlines()))
        else:
            oz.ozutil.http_download_file(content, out.fileno(), False, None)
    else:
        raise oz.OzException.OzException("Type for %s must be 'raw', 'url' or 'base64'" % (name))

    # make sure the data is flushed to disk for uses of the file through
    # the name
    out.flush()
    out.seek(0)

    return out

class Repository(object):
    """
    Class that represents a single repository to be used for installing
    packages.  Objects of this type contain 3 pieces of information:

    name       - The name of this repository.
    url        - The URL of this repository.
    signed     - Whether this repository is signed
    persisted  - Whether this repository should remain in the final image
    sslverify  - Whether SSL certificates should be verified
    """
    def __init__(self, name, url, signed, persisted, sslverify):
        self.name = name
        self.url = url
        self.signed = signed
        self.persisted = persisted
        self.sslverify = sslverify

class Package(object):
    """
    Class that represents a single package to be installed.
    Objects of this type contain 4 pieces of information:

    name     - The name of the package.
    repo     - The repository that this package comes from (optional).
    filename - The filename that contains this package (optional).
    args     - Arguments necessary to install this package (optional).
    """
    def __init__(self, name, repo, filename, args):
        self.name = name
        self.repo = repo
        self.filename = filename
        self.args = args

class ISOExtra(object):
    """
    Class that represents an extra element to add to an installation ISO.
    Objects of this type contain 3 pieces of information:

    element_type - "file" or "directory"
    source       - A source URL for the element.
    destination  - A relative destination for the element.
    """
    def __init__(self, element_type, source, destination):
        self.element_type = element_type
        self.source = source
        self.destination = destination

class TDL(object):
    """
    Class that represents a parsed piece of TDL XML.  Objects of this kind
    contain 10 pieces of information:

    name         - The name assigned to this TDL.
    distro       - The type of operating system this TDL represents.
    update       - The version of the operating system this TDL represents.
    arch         - The architecture of the operating system this TDL
                   represents. Currently this must be one of "i386" or
                   "x86_64".
    key          - The installation key necessary to install this operating
                   system (optional).
    description  - A free-form description of this TDL (optional).
    installtype  - The method to be used to install this operating system.
                   Currently this must be one of "url" or "iso".
    packages     - A list of Package objects describing the packages to be
                   installed on the operating system.  This list may be
                   empty.
    repositories - A dictionary of Repository objects describing the
                   repositories to be searched to find packages.  The
                   dictionary is indexed by repository name.  This
                   dictionary may be empty.
    files        - A dictionary of file contents to be added to the
                   operating system.  The dictionary is indexed by filename.
    commands     - A dictionary of commands to run inside the guest VM.  The
                   dictionary is indexed by commands.  This dictionary may
                   be empty.
    """
    def __init__(self, xmlstring, rootpw_required=False):
        # open the XML document
        self.doc = lxml.etree.fromstring(xmlstring)

        # then validate the schema
        relaxng = lxml.etree.RelaxNG(file=os.path.join(os.path.dirname(__file__),
                                                       'tdl.rng'))
        valid = relaxng.validate(self.doc)
        if not valid:
            errstr = "\nXML schema validation failed:\n"
            for error in relaxng.error_log:
                errstr += "\tline %s: %s\n" % (error.line, error.message)
            raise oz.OzException.OzException(errstr)

        template = self.doc.xpath('/template')
        if len(template) != 1:
            raise oz.OzException.OzException("Expected 1 template section in TDL, saw %d" % (len(template)))
        self.version = template[0].get('version')

        if self.version:
            self._validate_tdl_version()

        self.name = _xml_get_value(self.doc, '/template/name', 'template name')

        self.distro = _xml_get_value(self.doc, '/template/os/name', 'OS name')

        self.update = _xml_get_value(self.doc, '/template/os/version',
                                     'OS version')

        self.arch = _xml_get_value(self.doc, '/template/os/arch',
                                   'OS architecture')
        if self.arch != "i386" and self.arch != "x86_64":
            raise oz.OzException.OzException("Architecture must be one of 'i386' or 'x86_64'")

        self.key = _xml_get_value(self.doc, '/template/os/key', 'OS key',
                                  optional=True)
        # key is not required, so it is not fatal if it is None

        self.description = _xml_get_value(self.doc, '/template/description',
                                          'description', optional=True)
        # description is not required, so it is not fatal if it is None

        install = self.doc.xpath('/template/os/install')
        if len(install) != 1:
            raise oz.OzException.OzException("Expected 1 OS install section in TDL, saw %d" % (len(install)))
        self.installtype = install[0].get('type')
        if self.installtype is None:
            raise oz.OzException.OzException("Failed to find OS install type in TDL")

        # we only support md5/sha1/sha256 sums for ISO install types.  However,
        # we make sure the instance variables are set to None for both types
        # so code lower down in the stack doesn't have to care about the ISO
        # vs. URL install type distinction, and can just check whether or not
        # these URLs are None
        self.iso_md5_url = None
        self.iso_sha1_url = None
        self.iso_sha256_url = None

        if self.installtype == "url":
            self.url = _xml_get_value(self.doc, '/template/os/install/url',
                                      'OS install URL')
        elif self.installtype == "iso":
            self.iso = _xml_get_value(self.doc, '/template/os/install/iso',
                                      'OS install ISO')
            self.iso_md5_url = _xml_get_value(self.doc,
                                              '/template/os/install/md5sum',
                                              'OS install ISO MD5SUM',
                                              optional=True)
            self.iso_sha1_url = _xml_get_value(self.doc,
                                               '/template/os/install/sha1sum',
                                               'OS install ISO SHA1SUM',
                                               optional=True)
            self.iso_sha256_url = _xml_get_value(self.doc,
                                                 '/template/os/install/sha256sum',
                                                 'OS install ISO SHA256SUM',
                                                 optional=True)
            # only one of md5, sha1, or sha256 can be specified; raise an error
            # if multiple are
            if (self.iso_md5_url and self.iso_sha1_url) or (self.iso_md5_url and self.iso_sha256_url) or (self.iso_sha1_url and self.iso_sha256_url):
                raise oz.OzException.OzException("Only one of <md5sum>, <sha1sum>, and <sha256sum> can be specified")
        else:
            raise oz.OzException.OzException("Unknown install type " + self.installtype + " in TDL")

        self.rootpw = _xml_get_value(self.doc, '/template/os/rootpw',
                                     "root/Administrator password",
                                     optional=not rootpw_required)

        self.packages = []
        self._add_packages(self.doc.xpath('/template/packages/package'))

        self.files = {}
        for afile in self.doc.xpath('/template/files/file'):
            name = afile.get('name')
            if name is None:
                raise oz.OzException.OzException("File without a name was given")
            contenttype = afile.get('type')
            if contenttype is None:
                contenttype = 'raw'

            content = afile.text
            if content:
                content = content.strip()
            else:
                content = ''
            self.files[name] = data_from_type(name, contenttype, content)

        self.isoextras = self._add_isoextras('/template/os/install/extras/directory',
                                             'directory')
        self.isoextras += self._add_isoextras('/template/os/install/extras/file',
                                              'file')

        self.repositories = {}
        self._add_repositories(self.doc.xpath('/template/repositories/repository'))

        self.commands = self._parse_commands()

        self.disksize = self._parse_disksize()

        self.icicle_extra_cmd = _xml_get_value(self.doc,
                                               '/template/os/icicle/extra_command',
                                               "extra icicle command",
                                               optional=True)

    def _parse_disksize(self):
        """
        Internal method to parse the disk size out of the TDL.
        """
        size = _xml_get_value(self.doc, '/template/disk/size', 'disk size',
                              optional=True)
        if size is None:
            # if it wasn't specified, return None; the Guest object will assign
            # a sensible default
            return None

        match = re.match(r'([0-9]*) *([GT]?)$', size)
        if not match or len(match.groups()) != 2:
            raise oz.OzException.OzException("Invalid disk size; it must be specified as a size in gigabytes, optionally suffixed with 'G' or 'T'")

        number = match.group(1)
        suffix = match.group(2)

        if not suffix or suffix == 'G':
            # for backwards compatibility, we assume G when there is no suffix
            size = number
        elif suffix == 'T':
            size = str(int(number) * 1024)

        return size

    def _parse_commands(self):
        """
        Internal method to parse the commands XML and put it into order.  This
        order can either be via parse order (implicit) or by using the
        'position' attribute in the commands XML (explicit).  Note that the two
        cannot be mixed; if position is specified on one node, it must be
        specified on all of them.  Conversely, if position is *not* specified
        on one node, it must *not* be specified on any of them.  Also note that
        if explicit ordering is used, it must be strictly sequential, starting
        at 1, with no duplicate numbers.
        """
        tmp = []
        saw_position = False
        for command in self.doc.xpath('/template/commands/command'):
            name = command.get('name')
            if name is None:
                raise oz.OzException.OzException("Command without a name was given")
            contenttype = command.get('type')
            if contenttype is None:
                contenttype = 'raw'

            content = ""
            if command.text:
                content = command.text.strip()
            if len(content) == 0:
                raise oz.OzException.OzException("Empty commands are not allowed")

            # since XML doesn't *guarantee* an order, the correct way to
            # specify a particular order of commands is to use the "position"
            # attribute.  For backwards compatibility, if the order is not
            # specified, we just use the parse order.  That being said, we do
            # not allow a mix of position attributes and implicit order.  If
            # you use the position attribute on one command, you must use it
            # on all commands, and vice-versa.

            position = command.get('position')
            if position is not None:
                saw_position = True
                position = int(position)

            fp = data_from_type(name, contenttype, content)
            tmp.append((position, fp))

        commands = []
        if not saw_position:
            for pos, fp in tmp:
                commands.append(fp)
        else:
            tmp.sort(cmp=lambda x, y: cmp(x[0], y[0]))
            order = 1
            for pos, fp in tmp:
                if pos is None:
                    raise oz.OzException.OzException("All command elements must have a position (explicit order), or none of them may (implicit order)")
                elif pos != order:
                    # this handles both the case where there are duplicates and
                    # the case where there is a missing number
                    raise oz.OzException.OzException("Cannot have duplicate or sparse command position order!")
                order += 1
                commands.append(fp)

        return commands

    def merge_packages(self, packages):
        """
        Method to merge additional packages into an existing TDL.  The
        packages argument should be a properly structured <packages/> string
        as explained in the TDL documentation.  If a package with the same
        name is in the existing TDL and in packages, the value in packages
        overrides.
        """
        packsdoc = lxml.etree.fromstring(packages)
        packslist = packsdoc.xpath('/packages/package')
        self._add_packages(packslist, True)

    def _add_packages(self, packslist, remove_duplicates = False):
        """
        Internal method to add the list of lxml.etree nodes from packslist into
        the self.packages array.  If remove_duplicates is False (the default),
        then a package that is listed both in packslist and in the initial
        TDL is listed twice.  If it is set to True, then a package that is
        listed both in packslist and the initial TDL is listed only once,
        from the packslist.
        """
        for package in packslist:
            # package name
            name = package.get('name')

            if name is None:
                raise oz.OzException.OzException("Package without a name was given")

            # repository that the package lives in (optional)
            repo = _xml_get_value(package, 'repository',
                                  "package repository section", optional=True)

            # filename of the package (optional)
            filename = _xml_get_value(package, 'file', "package filename",
                                      optional=True)

            # arguments to install package (optional)
            args = _xml_get_value(package, 'arguments', "package arguments",
                                  optional=True)

            if remove_duplicates:
                # delete any existing packages with this name
                for package in [package for package in self.packages if package.name == name]:
                    self.packages.remove(package)

            # now add in our new package def
            self.packages.append(Package(name, repo, filename, args))

    def merge_repositories(self, repos):
        """
        Method to merge additional repositories into an existing TDL.  The
        repos argument should be a properly structured <repositories/>
        string as explained in the TDL documentation.  If a repository with
        the same name is in the existing TDL and in repos, the value in
        repos overrides.
        """
        reposdoc = lxml.etree.fromstring(repos)
        reposlist = reposdoc.xpath('/repositories/repository')
        self._add_repositories(reposlist)

    def _add_repositories(self, reposlist):
        """
        Internal method to add the list of lxml.etree nodes from reposlist into
        the self.repositories dictionary.
        """
        def _get_optional_repo_bool(repo, name, default):
            """
            Internal method to get an option boolean from a repo XML section.
            """
            xmlstr = _xml_get_value(repo, name, name, optional=True)
            if xmlstr is None:
                xmlstr = default

            val = oz.ozutil.string_to_bool(xmlstr)
            if val is None:
                raise oz.OzException.OzException("Repository %s property must be 'true', 'yes', 'false', or 'no'" % (name))
            return val

        for repo in reposlist:
            name = repo.get('name')
            if name is None:
                raise oz.OzException.OzException("Repository without a name was given")
            url = _xml_get_value(repo, 'url', 'repository url')

            if urlparse.urlparse(url)[1] in ["localhost", "127.0.0.1",
                                             "localhost.localdomain"]:
                raise oz.OzException.OzException("Repositories cannot be localhost, since they must be reachable from the guest operating system")

            signed = _get_optional_repo_bool(repo, 'signed', 'no')

            persist = _get_optional_repo_bool(repo, 'persisted', 'yes')

            sslverify = _get_optional_repo_bool(repo, 'sslverify', 'no')

            # no need to delete - if the name matches we just overwrite here
            self.repositories[name] = Repository(name, url, signed, persist,
                                                 sslverify)

    def _add_isoextras(self, extraspath, element_type):
        """
        Internal method to add the list of extra ISO elements from the specified
        XML path into the self.isoextras list.
        """
        isoextras = []
        extraslist = self.doc.xpath(extraspath)
        if self.installtype != 'iso' and extraslist:
            raise oz.OzException.OzException("Extra ISO data can only be used with iso install type")

        for extra in extraslist:
            source = extra.get('source')
            if source is None:
                raise oz.OzException.OzException("Extra ISO element without a source was given")
            destination = extra.get('destination')
            if destination is None:
                raise oz.OzException.OzException("Extra ISO element without a destination was given")

            isoextras.append(ISOExtra(element_type, source, destination))

        return isoextras

    # I declare we will use a 2 element version string with a dot
    # This allows simple comparison by conversion to float
    schema_version = "1.0"

    def _validate_tdl_version(self):
        """
        Internal method to validate that we support the TDL version.
        """
        if float(self.version) > float(self.schema_version):
            raise oz.OzException.OzException("TDL version (%s) is higher than our known version (%s)" % (self.version, self.schema_version))

########NEW FILE########
__FILENAME__ = Ubuntu
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013,2014  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Ubuntu installation
"""

import shutil
import re
import os
import gzip

import oz.Linux
import oz.ozutil
import oz.OzException

class UbuntuGuest(oz.Linux.LinuxCDGuest):
    """
    Class for Ubuntu 5.04, 5.10, 6.06, 6.10, 7.04, 7.10, 8.04, 8.10, 9.04, 9.10, 10.04, 10.10, 11.04, 11.10, 12.04, 12.10, 13.04, 13.10, and 14.04 installation.
    """
    def __init__(self, tdl, config, auto, output_disk, initrd, nicmodel,
                 diskbus, macaddress):
        oz.Linux.LinuxCDGuest.__init__(self, tdl, config, auto, output_disk,
                                       nicmodel, diskbus, True, True,
                                       macaddress)

        self.crond_was_active = False
        self.sshd_was_active = False
        self.sshd_config = """\
SyslogFacility AUTHPRIV
PasswordAuthentication yes
ChallengeResponseAuthentication no
GSSAPIAuthentication yes
GSSAPICleanupCredentials yes
UsePAM yes
AcceptEnv LANG LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES
AcceptEnv LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT
AcceptEnv LC_IDENTIFICATION LC_ALL LANGUAGE
AcceptEnv XMODIFIERS
X11Forwarding yes
Subsystem       sftp    /usr/libexec/openssh/sftp-server
"""

        self.casper_initrd = initrd

        self.ssh_startuplink = None
        self.cron_startuplink = None

        self.debarch = self.tdl.arch
        if self.debarch == "x86_64":
            self.debarch = "amd64"

        self.kernelfname = os.path.join(self.output_dir,
                                        self.tdl.name + "-kernel")
        self.initrdfname = os.path.join(self.output_dir,
                                        self.tdl.name + "-ramdisk")
        self.kernelcache = os.path.join(self.data_dir, "kernels",
                                        self.tdl.distro + self.tdl.update + self.tdl.arch + "-kernel")
        self.initrdcache = os.path.join(self.data_dir, "kernels",
                                        self.tdl.distro + self.tdl.update + self.tdl.arch + "-ramdisk")

        self.cmdline = "priority=critical locale=en_US"

        self.reboots = 0
        if self.tdl.update in ["5.04", "5.10"]:
            self.reboots = 1

    def _check_iso_tree(self, customize_or_icicle):
        # ISOs that contain casper are desktop install CDs
        if os.path.isdir(os.path.join(self.iso_contents, "casper")):
            if self.tdl.update in ["6.06", "6.10", "7.04"]:
                raise oz.OzException.OzException("Ubuntu %s installs can only be done using the alternate or server CDs" % (self.tdl.update))
            if customize_or_icicle:
                raise oz.OzException.OzException("Ubuntu customization or ICICLE generation can only be done using the alternate or server CDs")
            if self.tdl.update in ["13.10"]:
                raise oz.OzException.OzException("Ubuntu 13.10 installs can only be done with the server CD")

    def _copy_preseed(self, outname):
        """
        Method to copy and modify an Ubuntu style preseed file.
        """
        self.log.debug("Putting the preseed file in place")

        if self.default_auto_file():
            def _preseed_sub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify preseed files as appropriate for Ubuntu.
                """
                if re.match('d-i passwd/root-password password', line):
                    return 'd-i passwd/root-password password ' + self.rootpw + '\n'
                elif re.match('d-i passwd/root-password-again password', line):
                    return 'd-i passwd/root-password-again password ' + self.rootpw + '\n'
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _preseed_sub)
        else:
            shutil.copy(self.auto, outname)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        self.log.debug("Copying preseed file")
        outname = os.path.join(self.iso_contents, "preseed", "customiso.seed")
        outdir = os.path.dirname(outname)
        oz.ozutil.mkdir_p(outdir)

        self._copy_preseed(outname)

        self.log.debug("Modifying isolinux.cfg")
        isolinuxcfg = os.path.join(self.iso_contents, "isolinux",
                                   "isolinux.cfg")
        isolinuxdir = os.path.dirname(isolinuxcfg)
        if not os.path.isdir(isolinuxdir):
            oz.ozutil.mkdir_p(isolinuxdir)
            shutil.copyfile(os.path.join(self.iso_contents, "isolinux.bin"),
                            os.path.join(isolinuxdir, "isolinux.bin"))
            shutil.copyfile(os.path.join(self.iso_contents, "boot.cat"),
                            os.path.join(isolinuxdir, "boot.cat"))

        with open(isolinuxcfg, 'w') as f:

            if self.tdl.update in ["5.04", "5.10"]:
                f.write("""\
DEFAULT /install/vmlinuz
APPEND initrd=/install/initrd.gz ramdisk_size=16384 root=/dev/rd/0 rw preseed/file=/cdrom/preseed/customiso.seed debian-installer/locale=en_US kbd-chooser/method=us netcfg/choose_interface=auto keyboard-configuration/layoutcode=us debconf/priority=critical --
TIMEOUT 1
PROMPT 0
""")
            else:
                f.write("default customiso\n")
                f.write("timeout 1\n")
                f.write("prompt 0\n")
                f.write("label customiso\n")
                f.write("  menu label ^Customiso\n")
                f.write("  menu default\n")
                if os.path.isdir(os.path.join(self.iso_contents, "casper")):
                    kernelname = "/casper/vmlinuz"
                    if self.tdl.update in ["12.04.2", "13.04"] and self.tdl.arch == "x86_64":
                        kernelname += ".efi"
                    f.write("  kernel " + kernelname + "\n")
                    f.write("  append file=/cdrom/preseed/customiso.seed boot=casper automatic-ubiquity noprompt keyboard-configuration/layoutcode=us initrd=/casper/" + self.casper_initrd + "\n")
                else:
                    keyboard = "console-setup/layoutcode=us"
                    if self.tdl.update == "6.06":
                        keyboard = "kbd-chooser/method=us"
                    f.write("  kernel /install/vmlinuz\n")
                    f.write("  append preseed/file=/cdrom/preseed/customiso.seed debian-installer/locale=en_US " + keyboard + " netcfg/choose_interface=auto keyboard-configuration/layoutcode=us priority=critical initrd=/install/initrd.gz --\n")


    def get_auto_path(self):
        """
        Method to create the correct path to the Ubuntu preseed files.
        """
        autoname = self.tdl.distro + self.tdl.update + ".auto"
        sp = self.tdl.update.split('.')
        if len(sp) == 3:
            autoname = self.tdl.distro + sp[0] + "." + sp[1] + ".auto"
        return oz.ozutil.generate_full_auto_path(autoname)

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.info("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage", "-r", "-V", "Custom",
                                           "-J", "-l", "-no-emul-boot",
                                           "-b", "isolinux/isolinux.bin",
                                           "-c", "isolinux/boot.cat",
                                           "-boot-load-size", "4",
                                           "-cache-inodes", "-boot-info-table",
                                           "-v", "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        if self.tdl.update in ["5.04", "5.10", "6.06", "6.10", "7.04"]:
            if not timeout:
                timeout = 3000
        return self._do_install(timeout, force, self.reboots, self.kernelfname,
                                self.initrdfname, self.cmdline)

    def _get_service_runlevel_link(self, g_handle, service):
        """
        Method to find the runlevel link(s) for a service based on the name
        and the (detected) default runlevel.
        """
        runlevel = self.get_default_runlevel(g_handle)

        lines = g_handle.cat('/etc/init.d/' + service).split("\n")
        startlevel = "99"
        for line in lines:
            if re.match('# chkconfig:', line):
                try:
                    startlevel = line.split(':')[1].split()[1]
                except:
                    pass
                break

        return "/etc/rc" + runlevel + ".d/S" + startlevel + service

    def _image_ssh_teardown_step_1(self, g_handle):
        """
        First step to undo _image_ssh_setup (remove authorized keys).
        """
        self.log.debug("Teardown step 1")
        # reset the authorized keys
        self.log.debug("Resetting authorized_keys")
        self._guestfs_path_restore(g_handle, '/root/.ssh')

    def _image_ssh_teardown_step_2(self, g_handle):
        """
        Second step to undo _image_ssh_setup (reset sshd service).
        """
        self.log.debug("Teardown step 2")
        # remove custom sshd_config
        self.log.debug("Resetting sshd_config")
        self._guestfs_path_restore(g_handle, '/etc/ssh/sshd_config')

        # reset the service link
        self.log.debug("Resetting sshd service")
        if self.ssh_startuplink:
            self._guestfs_path_restore(g_handle, self.ssh_startuplink)

    def _image_ssh_teardown_step_3(self, g_handle):
        """
        Fourth step to undo _image_ssh_setup (remove guest announcement).
        """
        self.log.debug("Teardown step 3")
        # remove announce cronjob
        self.log.debug("Resetting announcement to host")
        self._guestfs_remove_if_exists(g_handle,
                                       '/etc/NetworkManager/dispatcher.d/99-reportip')

        self._guestfs_remove_if_exists(g_handle, '/etc/cron.d/announce')

        # remove reportip
        self.log.debug("Removing reportip")
        self._guestfs_remove_if_exists(g_handle, '/root/reportip')

        # reset the service link
        self.log.debug("Resetting cron service")
        if self.cron_startuplink:
            self._guestfs_path_restore(g_handle, self.cron_startuplink)

    def _image_ssh_teardown_step_4(self, g_handle):
        """
        Fourth step to undo changes by the operating system.  For instance,
        during first boot openssh generates ssh host keys and stores them
        in /etc/ssh.  Since this image might be cached later on, this method
        removes those keys.
        """
        for f in ["/etc/ssh/ssh_host_dsa_key", "/etc/ssh/ssh_host_dsa_key.pub",
                  "/etc/ssh/ssh_host_rsa_key", "/etc/ssh/ssh_host_rsa_key.pub",
                  "/etc/ssh/ssh_host_ecdsa_key", "/etc/ssh/ssh_host_ecdsa_key.pub",
                  "/etc/ssh/ssh_host_key", "/etc/ssh/ssh_host_key.pub"]:
            self._guestfs_remove_if_exists(g_handle, f)

    def _image_ssh_setup_step_1(self, g_handle):
        """
        First step for allowing remote access (generate and upload ssh keys).
        """
        # part 1; upload the keys
        self.log.debug("Step 1: Uploading ssh keys")
        self._guestfs_path_backup(g_handle, '/root/.ssh')
        g_handle.mkdir('/root/.ssh')

        self._guestfs_path_backup(g_handle, '/root/.ssh/authorized_keys')

        self._generate_openssh_key(self.sshprivkey)

        g_handle.upload(self.sshprivkey + ".pub", '/root/.ssh/authorized_keys')

    def _image_ssh_setup_step_2(self, g_handle):
        """
        Second step for allowing remote access (configure sshd).
        """
        # part 2; check and setup sshd
        self.log.debug("Step 2: setup sshd")
        if not g_handle.exists('/usr/sbin/sshd'):
            raise oz.OzException.OzException("ssh not installed on the image, cannot continue")

        self.ssh_startuplink = self._get_service_runlevel_link(g_handle, 'ssh')
        self._guestfs_path_backup(g_handle, self.ssh_startuplink)
        g_handle.ln_sf('/etc/init.d/ssh', self.ssh_startuplink)

        sshd_config_file = os.path.join(self.icicle_tmp, "sshd_config")
        with open(sshd_config_file, 'w') as f:
            f.write(self.sshd_config)

        try:
            self._guestfs_path_backup(g_handle, '/etc/ssh/sshd_config')
            g_handle.upload(sshd_config_file, '/etc/ssh/sshd_config')
        finally:
            os.unlink(sshd_config_file)

    def _image_ssh_setup_step_3(self, g_handle):
        """
        Fourth step for allowing remote access (make the guest announce itself
        on bootup).
        """
        # part 3; make sure the guest announces itself
        self.log.debug("Step 3: Guest announcement")

        scriptfile = os.path.join(self.icicle_tmp, "script")

        if g_handle.exists("/etc/NetworkManager/dispatcher.d"):
            with open(scriptfile, 'w') as f:
                f.write("""\
#!/bin/bash

if [ "$1" = "eth0" -a "$2" = "up" ]; then
    echo -n "!$DHCP4_IP_ADDRESS,%s!" > /dev/ttyS1
fi
""" % (self.uuid))

            try:
                g_handle.upload(scriptfile,
                                '/etc/NetworkManager/dispatcher.d/99-reportip')
                g_handle.chmod(0755,
                               '/etc/NetworkManager/dispatcher.d/99-reportip')
            finally:
                os.unlink(scriptfile)

        if not g_handle.exists('/usr/sbin/cron'):
            raise oz.OzException.OzException("cron not installed on the image, cannot continue")

        with open(scriptfile, 'w') as f:
            f.write("""\
#!/bin/bash
/bin/sleep 20
DEV=$(/usr/bin/awk '{if ($2 == 0) print $1}' /proc/net/route) &&
[ -z "$DEV" ] && exit 0
ADDR=$(/sbin/ip -4 -o addr show dev $DEV | /usr/bin/awk '{print $4}' | /usr/bin/cut -d/ -f1) &&
[ -z "$ADDR" ] && exit 0
echo -n "!$ADDR,%s!" > /dev/ttyS1
""" % (self.uuid))

        try:
            g_handle.upload(scriptfile, '/root/reportip')
            g_handle.chmod(0755, '/root/reportip')
        finally:
            os.unlink(scriptfile)

        announcefile = os.path.join(self.icicle_tmp, "announce")
        with open(announcefile, 'w') as f:
            f.write('*/1 * * * * root /bin/bash -c "/root/reportip"\n')

        try:
            g_handle.upload(announcefile, '/etc/cron.d/announce')
        finally:
            os.unlink(announcefile)

        self.cron_startuplink = self._get_service_runlevel_link(g_handle,
                                                                'cron')
        self._guestfs_path_backup(g_handle, self.cron_startuplink)
        g_handle.ln_sf('/etc/init.d/cron', self.cron_startuplink)

    def _collect_setup(self, libvirt_xml):
        """
        Setup the guest for remote access.
        """
        self.log.info("Collection Setup")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        # we have to do 3 things to make sure we can ssh into Ubuntu
        # 1)  Upload our ssh key
        # 2)  Make sure sshd is running on boot
        # 3)  Make the guest announce itself to the host

        try:
            try:
                self._image_ssh_setup_step_1(g_handle)

                try:
                    self._image_ssh_setup_step_2(g_handle)

                    try:
                        self._image_ssh_setup_step_3(g_handle)

                    except:
                        self._image_ssh_teardown_step_3(g_handle)
                        raise
                except:
                    self._image_ssh_teardown_step_2(g_handle)
                    raise
            except:
                self._image_ssh_teardown_step_1(g_handle)
                raise

        finally:
            self._guestfs_handle_cleanup(g_handle)

    def _collect_teardown(self, libvirt_xml):
        """
        Method to reverse the changes done in _collect_setup.
        """
        self.log.info("Collection Teardown")

        g_handle = self._guestfs_handle_setup(libvirt_xml)

        try:
            self._image_ssh_teardown_step_1(g_handle)

            self._image_ssh_teardown_step_2(g_handle)

            self._image_ssh_teardown_step_3(g_handle)

            self._image_ssh_teardown_step_4(g_handle)
        finally:
            self._guestfs_handle_cleanup(g_handle)
            shutil.rmtree(self.icicle_tmp)

    def _customize_repos(self, guestaddr):
        """
        Method to generate and upload custom repository files based on the TDL.
        """

        self.log.debug("Installing additional repository files")

        for repo in list(self.tdl.repositories.values()):
            self.guest_execute_command(guestaddr, "apt-add-repository --yes '%s'" % (repo.url.strip('\'"')))
            self.guest_execute_command(guestaddr, "apt-get update")

    def _install_packages(self, guestaddr, packstr):
        self.guest_execute_command(guestaddr,
                                   'apt-get install -y %s' % (packstr))

    def do_icicle(self, guestaddr):
        """
        Method to collect the package information and generate the ICICLE
        XML.
        """
        self.log.debug("Generating ICICLE")
        stdout, stderr, retcode = self.guest_execute_command(guestaddr,
                                                             'dpkg --get-selections',
                                                             timeout=30)

        # the data we get back from dpkg is in the form of:
        #
        # <package name>\t\t\tinstall
        #
        # so we have to strip out the tabs and the install before
        # passing it on to output_icicle_xml
        packages = []
        for line in stdout.split("\n"):
            packages.append(line.split("\t")[0])

        return self._output_icicle_xml(packages, self.tdl.description)

    def _get_kernel_from_txt_cfg(self, fetchurl):
        """
        Internal method to download and parse the txt.cfg file from a URL.  If
        the txt.cfg file does not exist, or it does not have the keys that we
        expect, this method raises an error.
        """
        txtcfgurl = fetchurl + "/ubuntu-installer/" + self.debarch + "/boot-screens/txt.cfg"

        # first we check if the txt.cfg exists; this throws an exception if
        # it is missing
        info = oz.ozutil.http_get_header(txtcfgurl)
        if info['HTTP-Code'] != 200:
            raise oz.OzException.OzException("Could not find %s" % (txtcfgurl))

        txtcfg = os.path.join(self.icicle_tmp, "txt.cfg")
        self.log.debug("Going to write txt.cfg to %s" % (txtcfg))
        txtcfgfd = os.open(txtcfg, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        os.unlink(txtcfg)
        fp = os.fdopen(txtcfgfd)
        try:
            self.log.debug("Trying to get txt.cfg from " + txtcfgurl)
            oz.ozutil.http_download_file(txtcfgurl, txtcfgfd, False, self.log)

            # if we made it here, the txt.cfg existed.  Parse it and
            # find out the location of the kernel and ramdisk
            self.log.debug("Got txt.cfg, parsing")
            os.lseek(txtcfgfd, 0, os.SEEK_SET)
            grub_pattern = re.compile(r"^default\s*(?P<default_entry>\w+)$.*"
                                      r"^label\s*(?P=default_entry)$.*"
                                      r"^\s*kernel\s*(?P<kernel>\S+)$.*"
                                      r"initrd=(?P<initrd>\S+).*"
                                      r"^label", re.DOTALL | re.MULTILINE)
            config_text = fp.read()
            match = re.search(grub_pattern, config_text)
            kernel = match.group('kernel')
            initrd = match.group('initrd')
        finally:
            fp.close()

        if kernel is None or initrd is None:
            raise oz.OzException.OzException("Empty kernel or initrd")

        self.log.debug("Returning kernel %s and initrd %s" % (kernel, initrd))
        return (kernel, initrd)

    def _gzip_file(self, inputfile, outputmode):
        """
        Internal method to gzip a file and write it to the initrd.
        """
        with open(inputfile, 'rb') as f:
            gzf = gzip.GzipFile(self.initrdfname, mode=outputmode)
            try:
                gzf.writelines(f)
                gzf.close()
            except:
                # there is a bit of asymmetry here in that OSs that support cpio
                # archives have the initial initrdfname copied in the higher level
                # function, but we delete it here.  OSs that don't support cpio,
                # though, get the initrd created right here.  C'est le vie
                os.unlink(self.initrdfname)
                raise

    def _create_cpio_initrd(self, preseedpath):
        """
        Internal method to create a modified CPIO initrd
        """
        extrafname = os.path.join(self.icicle_tmp, "extra.cpio")
        self.log.debug("Writing cpio to %s" % (extrafname))
        cpiofiledict = {}
        cpiofiledict[preseedpath] = 'preseed.cfg'
        oz.ozutil.write_cpio(cpiofiledict, extrafname)

        try:
            shutil.copyfile(self.initrdcache, self.initrdfname)
            self._gzip_file(extrafname, 'ab')
        finally:
            os.unlink(extrafname)

    def _initrd_inject_preseed(self, fetchurl, force_download):
        """
        Internal method to download and inject a preseed file into an initrd.
        """
        # we first see if we can use direct kernel booting, as that is
        # faster than downloading the ISO
        kernel = None
        initrd = None
        try:
            (kernel, initrd) = self._get_kernel_from_txt_cfg(fetchurl)
        except:
            pass

        if kernel is None:
            self.log.debug("Kernel was None, trying ubuntu-installer/%s/linux" % (self.debarch))
            # we couldn't find the kernel in the txt.cfg, so try a
            # hard-coded path
            kernel = "ubuntu-installer/%s/linux" % (self.debarch)
        if initrd is None:
            self.log.debug("Initrd was None, trying ubuntu-installer/%s/initrd.gz" % (self.debarch))
            # we couldn't find the initrd in the txt.cfg, so try a
            # hard-coded path
            initrd = "ubuntu-installer/%s/initrd.gz" % (self.debarch)

        self._get_original_media('/'.join([self.url.rstrip('/'),
                                           kernel.lstrip('/')]),
                                 self.kernelcache, force_download)

        try:
            self._get_original_media('/'.join([self.url.rstrip('/'),
                                               initrd.lstrip('/')]),
                                     self.initrdcache, force_download)
        except:
            os.unlink(self.kernelfname)
            raise

        # if we made it here, then we can copy the kernel into place
        shutil.copyfile(self.kernelcache, self.kernelfname)

        try:
            preseedpath = os.path.join(self.icicle_tmp, "preseed.cfg")
            self._copy_preseed(preseedpath)

            try:
                self._create_cpio_initrd(preseedpath)
            finally:
                os.unlink(preseedpath)
        except:
            os.unlink(self.kernelfname)
            raise

    def _remove_repos(self, guestaddr):
        # FIXME: until we switch over to doing repository add by hand (instead
        # of using add-apt-repository), we can't really reliably implement this
        pass

    def generate_install_media(self, force_download=False,
                               customize_or_icicle=False):
        """
        Method to generate the install media for Ubuntu based operating
        systems.  If force_download is False (the default), then the
        original media will only be fetched if it is not cached locally.  If
        force_download is True, then the original media will be downloaded
        regardless of whether it is cached locally.
        """
        fetchurl = self.url
        if self.tdl.installtype == 'url':
            # set the fetchurl up-front so that if the OS doesn't support
            # initrd injection, or the injection fails for some reason, we
            # fall back to the mini.iso
            fetchurl += "/mini.iso"

            self.log.debug("Installtype is URL, trying to do direct kernel boot")
            try:
                return self._initrd_inject_preseed(self.url, force_download)
            except Exception as err:
                # if any of the above failed, we couldn't use the direct
                # kernel/initrd build method.  Fall back to trying to fetch
                # the mini.iso instead
                self.log.debug("Could not do direct boot, fetching mini.iso instead (the following error message is useful for bug reports, but can be ignored)")
                self.log.debug(err)

        return self._iso_generate_install_media(fetchurl, force_download,
                                                customize_or_icicle)

    def cleanup_install(self):
        """
        Method to cleanup any transient install data.
        """
        self.log.info("Cleaning up after install")

        for fname in [self.output_iso, self.initrdfname, self.kernelfname]:
            try:
                os.unlink(fname)
            except:
                pass

        if not self.cache_original_media:
            for fname in [self.orig_iso, self.kernelcache, self.initrdcache]:
                try:
                    os.unlink(fname)
                except:
                    pass

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Ubuntu installs.
    """
    if tdl.update in ["5.04", "5.10", "6.06", "6.06.1", "6.06.2", "6.10",
                      "7.04", "7.10"]:
        return UbuntuGuest(tdl, config, auto, output_disk, "initrd.gz",
                           netdev, diskbus, macaddress)
    if tdl.update in ["8.04", "8.04.1", "8.04.2", "8.04.3", "8.04.4", "8.10",
                      "9.04"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return UbuntuGuest(tdl, config, auto, output_disk, "initrd.gz",
                           netdev, diskbus, macaddress)
    if tdl.update in ["9.10", "10.04", "10.04.1", "10.04.2", "10.04.3", "10.10",
                      "11.04", "11.10", "12.04", "12.04.1", "12.04.2",
                      "12.04.3", "12.10", "13.04", "13.10", "14.04"]:
        if netdev is None:
            netdev = 'virtio'
        if diskbus is None:
            diskbus = 'virtio'
        return UbuntuGuest(tdl, config, auto, output_disk, "initrd.lz",
                           netdev, diskbus, macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Ubuntu: 5.04, 5.10, 6.06[.1,.2], 6.10, 7.04, 7.10, 8.04[.1,.2,.3,.4], 8.10, 9.04, 9.10, 10.04[.1,.2,.3], 10.10, 11.04, 11.10, 12.04[.1,.2,.3], 12.10, 13.04, 13.10, 14.04"

########NEW FILE########
__FILENAME__ = Windows
# Copyright (C) 2010,2011  Chris Lalancette <clalance@redhat.com>
# Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Windows installation
"""

import random
import re
import os
import lxml.etree
import shutil

import oz.Guest
import oz.ozutil
import oz.OzException

class Windows(oz.Guest.CDGuest):
    """
    Shared Windows base class.
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        oz.Guest.CDGuest.__init__(self, tdl, config, auto, output_disk,
                                  netdev, "localtime", "usb", diskbus, True,
                                  False, macaddress)

        if self.tdl.key is None:
            raise oz.OzException.OzException("A key is required when installing Windows")

class Windows_v5(Windows):
    """
    Class for Windows versions based on kernel 5.x (2000, XP, and 2003).
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        Windows.__init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                         macaddress)

        if self.tdl.update == "2000" and self.tdl.arch != "i386":
            raise oz.OzException.OzException("Windows 2000 only supports i386 architecture")

        self.winarch = self.tdl.arch
        if self.winarch == "x86_64":
            self.winarch = "amd64"

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.debug("Generating new ISO")
        oz.ozutil.subprocess_check_output(["genisoimage",
                                           "-b", "cdboot/boot.bin",
                                           "-no-emul-boot", "-boot-load-seg",
                                           "1984", "-boot-load-size", "4",
                                           "-iso-level", "2", "-J", "-l", "-D",
                                           "-N", "-joliet-long",
                                           "-relaxed-filenames", "-v",
                                           "-V", "Custom",
                                           "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def generate_diskimage(self, size=10, force=False):
        """
        Method to generate a diskimage.  By default, a blank diskimage of
        10GB will be created; the caller can override this with the size
        parameter, specified in GB.  If force is False (the default), then
        a diskimage will not be created if a cached JEOS is found.  If
        force is True, a diskimage will be created regardless of whether a
        cached JEOS exists.  See the oz-install man page for more
        information about JEOS caching.
        """
        createpart = False
        if self.tdl.update == "2000":
            # If given a blank diskimage, windows 2000 stops very early in
            # install with a message:
            #
            #  Setup has determined that your computer's starupt hard disk is
            #  new or has been erased...
            #
            # To avoid that message, create a partition table that spans
            # the entire disk
            createpart = True
        return self._internal_generate_diskimage(size, force, createpart)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        os.mkdir(os.path.join(self.iso_contents, "cdboot"))
        self._geteltorito(self.orig_iso, os.path.join(self.iso_contents,
                                                      "cdboot", "boot.bin"))

        outname = os.path.join(self.iso_contents, self.winarch, "winnt.sif")

        if self.default_auto_file():
            # if this is the oz default siffile, we modify certain parameters
            # to make installation succeed
            computername = "OZ" + str(random.randrange(1, 900000))

            def _sifsub(line):
                """
                Method that is called back from oz.ozutil.copy_modify_file() to
                modify sif files as appropriate for Windows 2000/XP/2003.
                """
                if re.match(" *ProductKey", line):
                    return "    ProductKey=" + self.tdl.key + "\n"
                elif re.match(" *ProductID", line):
                    return "    ProductID=" + self.tdl.key + "\n"
                elif re.match(" *ComputerName", line):
                    return "    ComputerName=" + computername + "\n"
                elif re.match(" *AdminPassword", line):
                    return "    AdminPassword=" + self.rootpw + "\n"
                else:
                    return line

            oz.ozutil.copy_modify_file(self.auto, outname, _sifsub)
        else:
            # if the user provided their own siffile, do not override their
            # choices; the user gets to keep both pieces if something breaks
            shutil.copy(self.auto, outname)

    def install(self, timeout=None, force=False):
        """
        Method to run the operating system installation.
        """
        internal_timeout = timeout
        if internal_timeout is None:
            internal_timeout = 3600
        return self._do_install(internal_timeout, force, 1)

class Windows_v6(Windows):
    """
    Class for Windows versions based on kernel 6.x (2008, 7, 2012, and 8).
    """
    def __init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                 macaddress):
        Windows.__init__(self, tdl, config, auto, output_disk, netdev, diskbus,
                         macaddress)

        self.winarch = "x86"
        if self.tdl.arch == "x86_64":
            self.winarch = "amd64"

    def _generate_new_iso(self):
        """
        Method to create a new ISO based on the modified CD/DVD.
        """
        self.log.debug("Generating new ISO")
        # NOTE: Windows 2008 is very picky about which arguments to genisoimage
        # will generate a bootable CD, so modify these at your own risk
        oz.ozutil.subprocess_check_output(["genisoimage",
                                           "-b", "cdboot/boot.bin",
                                           "-no-emul-boot", "-c", "BOOT.CAT",
                                           "-iso-level", "2", "-J", "-l", "-D",
                                           "-N", "-joliet-long",
                                           "-relaxed-filenames", "-v",
                                           "-V", "Custom", "-udf",
                                           "-o", self.output_iso,
                                           self.iso_contents],
                                          printfn=self.log.debug)

    def _modify_iso(self):
        """
        Method to make the boot ISO auto-boot with appropriate parameters.
        """
        self.log.debug("Modifying ISO")

        os.mkdir(os.path.join(self.iso_contents, "cdboot"))
        self._geteltorito(self.orig_iso, os.path.join(self.iso_contents,
                                                      "cdboot", "boot.bin"))

        outname = os.path.join(self.iso_contents, "autounattend.xml")

        if self.default_auto_file():
            # if this is the oz default unattend file, we modify certain
            # parameters to make installation succeed
            doc = lxml.etree.parse(self.auto)

            for component in doc.xpath('/ms:unattend/ms:settings/ms:component',
                                       namespaces={'ms':'urn:schemas-microsoft-com:unattend'}):
                component.set('processorArchitecture', self.winarch)

            keys = doc.xpath('/ms:unattend/ms:settings/ms:component/ms:ProductKey',
                             namespaces={'ms':'urn:schemas-microsoft-com:unattend'})
            if len(keys) != 1:
                raise oz.OzException.OzException("Invalid autounattend file; expected 1 key, saw %d" % (len(keys)))
            keys[0].text = self.tdl.key

            adminpw = doc.xpath('/ms:unattend/ms:settings/ms:component/ms:UserAccounts/ms:AdministratorPassword/ms:Value',
                                namespaces={'ms':'urn:schemas-microsoft-com:unattend'})
            if len(adminpw) != 1:
                raise oz.OzException.OzException("Invalid autounattend file; expected 1 admin password, saw %d" % (len(adminpw)))
            adminpw[0].text = self.rootpw

            autologinpw = doc.xpath('/ms:unattend/ms:settings/ms:component/ms:AutoLogon/ms:Password/ms:Value',
                                    namespaces={'ms':'urn:schemas-microsoft-com:unattend'})
            if len(autologinpw) != 1:
                raise oz.OzException.OzException("Invalid autounattend file; expected 1 auto logon password, saw %d" % (len(autologinpw)))
            autologinpw[0].text = self.rootpw

            f = open(outname, 'w')
            f.write(lxml.etree.tostring(doc, pretty_print=True))
            f.close()
        else:
            # if the user provided their own unattend file, do not override
            # their choices; the user gets to keep both pieces if something
            # breaks
            shutil.copy(self.auto, outname)

    def install(self, timeout=None, force=False):
        internal_timeout = timeout
        if internal_timeout is None:
            internal_timeout = 8500
        return self._do_install(internal_timeout, force, 2)

def get_class(tdl, config, auto, output_disk=None, netdev=None, diskbus=None,
              macaddress=None):
    """
    Factory method for Windows installs.
    """
    if tdl.update in ["2000", "XP", "2003"]:
        return Windows_v5(tdl, config, auto, output_disk, netdev,
                          diskbus, macaddress)
    if tdl.update in ["2008", "7", "2012", "8"]:
        return Windows_v6(tdl, config, auto, output_disk, netdev, diskbus,
                          macaddress)

def get_supported_string():
    """
    Return supported versions as a string.
    """
    return "Windows: 2000, XP, 2003, 7, 2008, 2012, 8"

########NEW FILE########
__FILENAME__ = test_factory
#!/usr/bin/python

from __future__ import print_function
import sys
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
try:
    from io import StringIO, BytesIO
except:
    from StringIO import StringIO
    BytesIO = StringIO
import logging
import os

# Find oz library
prefix = '.'
for i in range(0,3):
    if os.path.isdir(os.path.join(prefix, 'oz')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

try:
    import oz.TDL
    import oz.GuestFactory
except ImportError as e:
    print(e)
    print('Unable to import oz.  Is oz installed or in your PYTHONPATH?')
    sys.exit(1)

try:
    import py.test
except ImportError:
    print('Unable to import py.test.  Is py.test installed?')
    sys.exit(1)

# Define a list to collect all tests
alltests = list()

# Define an object to record test results
class TestResult(object):
    def __init__(self, *args, **kwargs):
        if len(args) == 4:
            (self.distro, self.version, self.arch, self.installtype) = args
        for k,v in list(kwargs.items()):
            setattr(self, k, v)

    def __repr__(self):
        '''String representation of object'''
        return "test-{0}-{1}-{2}-{3}".format(*self.test_args())

    @property
    def name(self):
        '''Convenience property for test name'''
        return self.__repr__()

    def test_args(self):
        return (self.distro, self.version, self.arch, self.installtype)

    def execute(self):
        if self.expect_pass:
            return (self.name, runtest, self.test_args())
        else:
            return (self.name, handle_exception, self.test_args())

def default_route():
    route_file = "/proc/net/route"
    d = file(route_file)

    for line in d:
        info = line.split()
        if (len(info) != 11): # 11 = typical num of fields in the file
            logging.warn(_("Invalid line length while parsing %s.") %
                         (route_file))
            break
        try:
            route = int(info[1], 16)
            if route == 0:
                return info[0]
        except ValueError:
            continue
    raise Exception("Could not find default route")

# we find the default route for this machine.  Note that this very well
# may not be a bridge, but for the purposes of testing the factory, it
# doesn't really matter; it just has to have an IP address
route = default_route()

def runtest(args):
    global route

    (distro, version, arch, installtype) = args
    print("Testing %s-%s-%s-%s..." % (distro, version, arch, installtype), end=' ')

    tdlxml = """
<template>
  <name>tester</name>
  <os>
    <name>%s</name>
    <version>%s</version>
    <arch>%s</arch>
    <install type='%s'>
      <%s>http://example.org</%s>
    </install>
    <key>1234</key>
  </os>
</template>
""" % (distro, version, arch, installtype, installtype, installtype)

    tdl = oz.TDL.TDL(tdlxml)

    print(route)
    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    if os.getenv('DEBUG') != None:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    else:
        logging.basicConfig(level=logging.ERROR, format="%(message)s")

    oz.GuestFactory.guest_factory(tdl, config, None)

def expect_success(*args):
    '''Create a TestResult object using provided arguments.  Append result to
    global 'alltests' list.'''
    global alltests
    alltests.append(TestResult(*args, expect_pass=True))

def expect_fail(*args):
    '''Create a TestResult object using provided arguments.  Append result to
    global 'alltests' list.'''
    global alltests
    alltests.append(TestResult(*args, expect_pass=False))

def handle_exception(args):
    '''Helper method to capture OzException when executing 'runtest'.'''
    with py.test.raises(oz.OzException.OzException):
        runtest(args)

def test_all():

    # bad distro
    expect_fail("foo", "1", "i386", "url")
    # bad installtype
    expect_fail("Fedora", "14", "i386", "dong")
    # bad arch
    expect_fail("Fedora", "14", "ia64", "iso")

    # FedoraCore
    for version in ["1", "2", "3", "4", "5", "6"]:
        for arch in ["i386", "x86_64"]:
            for installtype in ["url", "iso"]:
                expect_success("FedoraCore", version, arch, installtype)
    # bad FedoraCore version
    expect_fail("FedoraCore", "24", "x86_64", "iso")

    # Fedora
    for version in ["7", "8", "9", "10", "11", "12", "13", "14", "15", "16",
                    "17", "18", "19"]:
        for arch in ["i386", "x86_64"]:
            for installtype in ["url", "iso"]:
                expect_success("Fedora", version, arch, installtype)
    # bad Fedora version
    expect_fail("Fedora", "24", "x86_64", "iso")

    # RHL
    for version in ["7.0", "7.1", "7.2", "7.3", "8", "9"]:
        expect_success("RHL", version, "i386", "url")
    # bad RHL version
    expect_fail("RHL", "10", "i386", "url")
    # bad RHL arch
    expect_fail("RHL", "9", "x86_64", "url")
    # bad RHL installtype
    expect_fail("RHL", "9", "x86_64", "iso")

    # RHEL-2.1
    for version in ["GOLD", "U2", "U3", "U4", "U5", "U6"]:
        expect_success("RHEL-2.1", version, "i386", "url")
    # bad RHEL-2.1 version
    expect_fail("RHEL-2.1", "U7", "i386", "url")
    # bad RHEL-2.1 arch
    expect_fail("RHEL-2.1", "U6", "x86_64", "url")
    # bad RHEL-2.1 installtype
    expect_fail("RHEL-2.1", "U6", "i386", "iso")

    # RHEL-3/CentOS-3
    for distro in ["RHEL-3", "CentOS-3"]:
        for version in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8",
                        "U9"]:
            for arch in ["i386", "x86_64"]:
                expect_success(distro, version, arch, "url")
    # bad RHEL-3 version
    expect_fail("RHEL-3", "U10", "x86_64", "url")
    # invalid RHEL-3 installtype
    expect_fail("RHEL-3", "U9", "x86_64", "iso")

    # RHEL-4/CentOS-4
    for distro in ["RHEL-4", "CentOS-4", "ScientificLinux-4"]:
        for version in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8",
                        "U9"]:
            for arch in ["i386", "x86_64"]:
                for installtype in ["url", "iso"]:
                    expect_success(distro, version, arch, installtype)
    # bad RHEL-4 version
    expect_fail("RHEL-4", "U10", "x86_64", "url")

    # RHEL-5/CentOS-5
    for distro in ["RHEL-5", "CentOS-5", "ScientificLinux-5"]:
        for version in ["GOLD", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8",
                        "U9", "U10"]:
            for arch in ["i386", "x86_64"]:
                for installtype in ["url", "iso"]:
                    expect_success(distro, version, arch, installtype)
    # bad RHEL-5 version
    expect_fail("RHEL-5", "U20", "x86_64", "url")

    # RHEL-6
    for distro in ["RHEL-6", "CentOS-6", "ScientificLinux-6", "OEL-6"]:
        for version in ["0", "1", "2", "3", "4"]:
            for arch in ["i386", "x86_64"]:
                for installtype in ["url", "iso"]:
                    expect_success(distro, version, arch, installtype)
    # bad RHEL-6 version
    expect_fail("RHEL-6", "U10", "x86_64", "url")

    # Debian
    for version in ["5", "6", "7"]:
        for arch in ["i386", "x86_64"]:
            expect_success("Debian", version, arch, "iso")
    # bad Debian version
    expect_fail("Debian", "12", "i386", "iso")
    # invalid Debian installtype
    expect_fail("Debian", "6", "x86_64", "url")

    # Windows
    expect_success("Windows", "2000", "i386", "iso")
    for version in ["XP", "2003", "2008", "7", "8", "2012"]:
        for arch in ["i386", "x86_64"]:
            expect_success("Windows", version, arch, "iso")
    # bad Windows 2000 arch
    expect_fail("Windows", "2000", "x86_64", "iso")
    # bad Windows version
    expect_fail("Windows", "1999", "x86_64", "iso")
    # invalid Windows installtype
    expect_fail("Windows", "2008", "x86_64", "url")

    # OpenSUSE
    for version in ["10.3", "11.0", "11.1", "11.2", "11.3", "11.4", "12.1",
                    "12.2", "12.3"]:
        for arch in ["i386", "x86_64"]:
            expect_success("OpenSUSE", version, arch, "iso")
    # bad OpenSUSE version
    expect_fail("OpenSUSE", "16", "x86_64", "iso")
    # invalid OpenSUSE installtype
    expect_fail("OpenSUSE", "11.4", "x86_64", "url")

    # Ubuntu
    for version in ["5.04", "5.10", "6.06", "6.06.1", "6.06.2", "6.10", "7.04",
                    "7.10", "8.04", "8.04.1", "8.04.2", "8.04.3", "8.04.4",
                    "8.10", "9.04", "9.10", "10.04", "10.04.1", "10.04.2",
                    "10.04.3", "10.10", "11.04", "11.10", "12.04", "12.04.1",
                    "12.04.2", "12.04.3", "12.10", "13.04", "13.10"]:
        for arch in ["i386", "x86_64"]:
            for installtype in ["iso", "url"]:
                expect_success("Ubuntu", version, arch, installtype)
    # bad Ubuntu version
    expect_fail("Ubuntu", "10.9", "i386", "iso")

    # Mandrake
    for version in ["8.2", "9.1", "9.2", "10.0", "10.1"]:
        expect_success("Mandrake", version, "i386", "iso")
    # bad Mandrake version
    expect_fail("Mandrake", "11", "i386", "iso")
    # bad Mandrake arch
    expect_fail("Mandrake", "8.2", "x86_64", "iso")
    # bad Mandrake installtype
    expect_fail("Mandrake", "8.2", "i386", "url")

    # Mandriva
    for version in ["2005", "2006.0", "2007.0", "2008.0"]:
        for arch in ["i386", "x86_64"]:
            expect_success("Mandriva", version, arch, "iso")
    # bad Mandriva version
    expect_fail("Mandriva", "80", "i386", "iso")
    # bad Mandriva installtype
    expect_fail("Mandriva", "2005", "i386", "url")

    # Now run all the tests
    for tst in alltests:
        yield tst.execute()

########NEW FILE########
__FILENAME__ = test_guest
#!/usr/bin/python

import sys
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
try:
    from io import StringIO, BytesIO
except:
    from StringIO import StringIO
    BytesIO = StringIO
import logging
import os

# Find oz library
prefix = '.'
for i in range(0,3):
    if os.path.isdir(os.path.join(prefix, 'oz')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

try:
    import oz.TDL
    import oz.GuestFactory
except ImportError as e:
    print(e)
    print('Unable to import oz.  Is oz installed or in your PYTHONPATH?')
    sys.exit(1)

try:
    import py.test
except ImportError:
    print('Unable to import py.test.  Is py.test installed?')
    sys.exit(1)

def default_route():
    route_file = "/proc/net/route"
    d = file(route_file)

    defn = 0
    for line in d:
        info = line.split()
        if (len(info) != 11): # 11 = typical num of fields in the file
            logging.warn(_("Invalid line length while parsing %s.") %
                         (route_file))
            break
        try:
            route = int(info[1], 16)
            if route == 0:
                return info[0]
        except ValueError:
            continue
    raise Exception("Could not find default route")

# we find the default route for this machine.  Note that this very well
# may not be a bridge, but for the purposes of testing the factory, it
# doesn't really matter; it just has to have an IP address
route = default_route()

tdlxml = """
<template>
  <name>tester</name>
  <os>
    <name>Fedora</name>
    <version>14</version>
    <arch>x86_64</arch>
    <install type='url'>
      <url>http://download.fedoraproject.org/pub/fedora/linux//releases/14/Fedora/x86_64/os/</url>
    </install>
  </os>
</template>
"""

def test_geteltorito_none_src():
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(None, None)

def test_geteltorito_none_dst(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('src')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, None)

def test_geteltorito_short_pvd(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('foo')

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(Exception):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_pvd_desc(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write('\0'*128)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_pvd_ident(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write('\0'*127)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_pvd_unused(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\0x1")
    fd.write('\0'*127)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_pvd_unused2(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x01")
    fd.write('\0'*127)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_short_boot_sector(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(Exception):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_boot_sector(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.seek(17*2048)
    fd.write("\x01")
    fd.write('\0'*75)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_boot_isoident(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.seek(17*2048)
    fd.write("\x00")
    fd.write("AAAAA")
    fd.write('\0'*75)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_boot_version(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.seek(17*2048)
    fd.write("\x00")
    fd.write("CD001")
    fd.write('\0'*75)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_boot_torito(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.seek(17*2048)
    fd.write("\x00")
    fd.write("CD001")
    fd.write("\x01")
    fd.write('\0'*75)
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(oz.OzException.OzException):
        guest._geteltorito(src, dst)

def test_geteltorito_bogus_bootp(tmpdir):
    tdl = oz.TDL.TDL(tdlxml)

    config = configparser.SafeConfigParser()
    config.readfp(BytesIO("[libvirt]\nuri=qemu:///session\nbridge_name=%s" % route))

    guest = oz.GuestFactory.guest_factory(tdl, config, None)

    src = os.path.join(str(tmpdir), 'src')
    fd = open(src, 'w')
    fd.seek(16*2048)
    fd.write("\x01")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("\x00")
    fd.write("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    fd.write("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
    fd.write("\x00")
    fd.write('\0'*127)
    fd.seek(17*2048)
    fd.write("\x00")
    fd.write("CD001")
    fd.write("\x01")
    fd.write("EL TORITO SPECIFICATION")
    fd.write('\0'*41)
    fd.write("\x20\x00\x00\x00")
    fd.close()

    dst = os.path.join(str(tmpdir), 'dst')

    with py.test.raises(Exception):
        guest._geteltorito(src, dst)

########NEW FILE########
__FILENAME__ = test_ozutil
#!/usr/bin/python

import sys
import os

try:
    import py.test
except ImportError:
    print('Unable to import py.test.  Is py.test installed?')
    sys.exit(1)

# Find oz
prefix = '.'
for i in range(0,3):
    if os.path.isdir(os.path.join(prefix, 'oz')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

try:
    import oz.ozutil
except ImportError:
    print('Unable to import oz.  Is oz installed?')
    sys.exit(1)

# test oz.ozutil.generate_full_auto_path
def test_auto():
    oz.ozutil.generate_full_auto_path('fedora-14-jeos.ks')

def test_auto_none():
    with py.test.raises(Exception):
        oz.ozutil.generate_full_auto_path(None)

# test oz.ozutil.executable_exists
def test_exe_exists_bin_ls():
    oz.ozutil.executable_exists('/bin/ls')

def test_exe_exists_foo():
    with py.test.raises(Exception):
        oz.ozutil.executable_exists('foo')

def test_exe_exists_full_foo():
    with py.test.raises(Exception):
        oz.ozutil.executable_exists('/bin/foo')

def test_exe_exists_not_x():
    with py.test.raises(Exception):
        oz.ozutil.executable_exists('/etc/hosts')

def test_exe_exists_relative_false():
    oz.ozutil.executable_exists('false')

def test_exe_exists_none():
    with py.test.raises(Exception):
        oz.ozutil.executable_exists(None)

# test oz.ozutil.copyfile_sparse
def test_copy_sparse_none_src():
    with py.test.raises(Exception):
        oz.ozutil.copyfile_sparse(None, None)

def test_copy_sparse_none_dst(tmpdir):
    fullname = os.path.join(str(tmpdir), 'src')
    open(fullname, 'w').write('src')
    with py.test.raises(Exception):
        oz.ozutil.copyfile_sparse(fullname, None)

def test_copy_sparse_bad_src_mode(tmpdir):
    if os.geteuid() == 0:
        # this test won't work as root, since root can copy any mode files
        return
    fullname = os.path.join(str(tmpdir), 'writeonly')
    open(fullname, 'w').write('writeonly')
    os.chmod(fullname, 0000)
    # because copyfile_sparse uses os.open() instead of open(), it throws an
    # OSError
    with py.test.raises(OSError):
        oz.ozutil.copyfile_sparse(fullname, 'output')

def test_copy_sparse_bad_dst_mode(tmpdir):
    if os.geteuid() == 0:
        # this test won't work as root, since root can copy any mode files
        return
    srcname = os.path.join(str(tmpdir), 'src')
    open(srcname, 'w').write('src')
    dstname = os.path.join(str(tmpdir), 'dst')
    open(dstname, 'w').write('dst')
    os.chmod(dstname, 0o444)
    with py.test.raises(OSError):
        oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_zero_size_src(tmpdir):
    srcname = os.path.join(str(tmpdir), 'src')
    fd = open(srcname, 'w')
    fd.close()
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_small_src(tmpdir):
    srcname = os.path.join(str(tmpdir), 'src')
    open(srcname, 'w').write('src')
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_one_block_src(tmpdir):
    infd = open('/dev/urandom', 'r')
    # we read 32*1024 to make sure we use one big buf_size block (see the
    # implementation of copyfile_sparse)
    data = infd.read(32*1024)
    infd.close

    srcname = os.path.join(str(tmpdir), 'src')
    outfd = open(srcname, 'w')
    outfd.write(data)
    outfd.close()
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_many_blocks_src(tmpdir):
    infd = open('/dev/urandom', 'r')
    # we read 32*1024 to make sure we use one big buf_size block (see the
    # implementation of copyfile_sparse)
    data = infd.read(32*1024*10)
    infd.close

    srcname = os.path.join(str(tmpdir), 'src')
    outfd = open(srcname, 'w')
    outfd.write(data)
    outfd.close()
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_zero_blocks(tmpdir):
    infd = open('/dev/urandom', 'r')
    # we read 32*1024 to make sure we use one big buf_size block (see the
    # implementation of copyfile_sparse)
    data1 = infd.read(32*1024)
    data2 = infd.read(32*1024)
    infd.close

    srcname = os.path.join(str(tmpdir), 'src')
    outfd = open(srcname, 'w')
    outfd.write(data1)
    outfd.write('\0'*32*1024)
    outfd.write(data2)
    outfd.close()
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_src_not_exists(tmpdir):
    srcname = os.path.join(str(tmpdir), 'src')
    dstname = os.path.join(str(tmpdir), 'dst')
    open(dstname, 'w').write('dst')
    with py.test.raises(Exception):
        oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_dest_not_exists(tmpdir):
    srcname = os.path.join(str(tmpdir), 'src')
    open(srcname, 'w').write('src')
    dstname = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copyfile_sparse(srcname, dstname)

def test_copy_sparse_src_is_dir(tmpdir):
    dstname = os.path.join(str(tmpdir), 'dst')
    open(dstname, 'w').write('dst')
    with py.test.raises(Exception):
        oz.ozutil.copyfile_sparse(tmpdir, dstname)

def test_copy_sparse_dst_is_dir(tmpdir):
    srcname = os.path.join(str(tmpdir), 'src')
    open(srcname, 'w').write('src')
    with py.test.raises(Exception):
        oz.ozutil.copyfile_sparse(srcname, tmpdir)

# test oz.ozutil.string_to_bool
def test_stb_no():
    for nletter in ['n', 'N']:
        for oletter in ['o', 'O']:
            curr = nletter+oletter
            yield ('bool-'+curr, oz.ozutil.string_to_bool, curr)

def test_stb_false():
    for fletter in ['f', 'F']:
        for aletter in ['a', 'A']:
            for lletter in ['l', 'L']:
                for sletter in ['s', 'S']:
                    for eletter in ['e', 'E']:
                        curr = fletter+aletter+lletter+sletter+eletter
                        yield ('bool-'+curr, oz.ozutil.string_to_bool, curr)

def test_stb_yes():
    for yletter in ['y', 'Y']:
        for eletter in ['e', 'E']:
            for sletter in ['s', 'S']:
                curr = yletter+eletter+sletter
                yield ('bool-'+curr, oz.ozutil.string_to_bool, curr)

def test_stb_true():
    for tletter in ['t', 'T']:
        for rletter in ['r', 'R']:
            for uletter in ['u', 'U']:
                for eletter in ['e', 'E']:
                    curr = tletter+rletter+uletter+eletter
                    yield ('bool-'+curr, oz.ozutil.string_to_bool, curr)

def test_stb_none():
    with py.test.raises(Exception):
        oz.ozutil.string_to_bool(None)


def test_stb_invalid():
    if oz.ozutil.string_to_bool('foobar') != None:
        raise Exception("Expected None return from string_to_bool")

# test oz.ozutil.generate_macaddress
def test_genmac():
    oz.ozutil.generate_macaddress()

# test oz.ozutil.mkdir_p
def test_mkdir_p(tmpdir):
    fullname = os.path.join(str(tmpdir), 'foo')
    oz.ozutil.mkdir_p(fullname)

def test_mkdir_p_twice(tmpdir):
    fullname = os.path.join(str(tmpdir), 'foo')
    oz.ozutil.mkdir_p(fullname)
    oz.ozutil.mkdir_p(fullname)

def test_mkdir_p_file_exists(tmpdir):
    fullname = os.path.join(str(tmpdir), 'file_exists')
    open(fullname, 'w').write('file_exists')
    with py.test.raises(OSError):
        oz.ozutil.mkdir_p(fullname)

def test_mkdir_p_none():
    with py.test.raises(Exception):
        oz.ozutil.mkdir_p(None)

def test_mkdir_p_empty_string():
    oz.ozutil.mkdir_p('')

# test oz.ozutil.copy_modify_file
def test_copy_modify_none_src():
    with py.test.raises(Exception):
        oz.ozutil.copy_modify_file(None, None, None)

def test_copy_modify_none_dst(tmpdir):
    fullname = os.path.join(str(tmpdir), 'src')
    open(fullname, 'w').write('src')
    with py.test.raises(Exception):
        oz.ozutil.copy_modify_file(fullname, None, None)

def test_copy_modify_none_subfunc(tmpdir):
    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('src')
    dst = os.path.join(str(tmpdir), 'dst')
    with py.test.raises(Exception):
        oz.ozutil.copy_modify_file(src, dst, None)

def test_copy_modify_bad_src_mode(tmpdir):
    if os.geteuid() == 0:
        # this test won't work as root, since root can copy any mode files
        return
    def sub(line):
        return line
    fullname = os.path.join(str(tmpdir), 'writeonly')
    open(fullname, 'w').write('writeonly')
    os.chmod(fullname, 0000)
    dst = os.path.join(str(tmpdir), 'dst')
    with py.test.raises(IOError):
        oz.ozutil.copy_modify_file(fullname, dst, sub)

def test_copy_modify_empty_file(tmpdir):
    def sub(line):
        return line
    src = os.path.join(str(tmpdir), 'src')
    f = open(src, 'w')
    f.close()
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copy_modify_file(src, dst, sub)

def test_copy_modify_file(tmpdir):
    def sub(line):
        return line
    src = os.path.join(str(tmpdir), 'src')
    f = open(src, 'w')
    f.write("this is a line in the file\n")
    f.write("this is another line in the file\n")
    f.close()
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.copy_modify_file(src, dst, sub)

# test oz.ozutil.write_cpio
def test_write_cpio_none_input():
    with py.test.raises(Exception):
        oz.ozutil.write_cpio(None, None)

def test_write_cpio_none_output():
    with py.test.raises(Exception):
        oz.ozutil.write_cpio({}, None)

def test_write_cpio_empty_dict(tmpdir):
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.write_cpio({}, dst)

def test_write_cpio_existing_file(tmpdir):
    if os.geteuid() == 0:
        # this test won't work as root, since root can copy any mode files
        return
    dst = os.path.join(str(tmpdir), 'dst')
    open(dst, 'w').write('hello')
    os.chmod(dst, 0000)
    with py.test.raises(IOError):
        oz.ozutil.write_cpio({}, dst)

def test_write_cpio_single_file(tmpdir):
    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('src')
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.write_cpio({src: 'src'}, dst)

def test_write_cpio_multiple_files(tmpdir):
    src1 = os.path.join(str(tmpdir), 'src1')
    open(src1, 'w').write('src1')
    src2 = os.path.join(str(tmpdir), 'src2')
    open(src2, 'w').write('src2')
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.write_cpio({src1: 'src1', src2: 'src2'}, dst)

def test_write_cpio_not_multiple_of_4(tmpdir):
    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('src')
    dst = os.path.join(str(tmpdir), 'dst')
    oz.ozutil.write_cpio({src: 'src'}, dst)

def test_write_cpio_exception(tmpdir):
    if os.geteuid() == 0:
        # this test won't work as root, since root can copy any mode files
        return
    src = os.path.join(str(tmpdir), 'src')
    open(src, 'w').write('src')
    os.chmod(src, 0000)
    dst = os.path.join(str(tmpdir), 'dst')
    with py.test.raises(IOError):
        oz.ozutil.write_cpio({src: 'src'}, dst)

def test_md5sum_regular(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('# this is a comment line, followed by a blank line\n\n6e812e782e52b536c0307bb26b3c244e *Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_sha1sum_regular(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e812e782e52b536c0307bb26b3c244e1c42b644 *Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_sha1sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_sha256sum_regular(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e812e782e52b536c0307bb26b3c244e1c42b644235f5a4b242786b1ef375358 *Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_sha256sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_bsd(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('MD5 (Fedora-11-i386-DVD.iso)=6e812e782e52b536c0307bb26b3c244e1c42b644235f5a4b242786b1ef375358\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_bsd_no_start_paren(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    # if BSD is missing a paren, we don't raise an exception, just ignore and
    # continue
    f.write('MD5 Fedora-11-i386-DVD.iso)=6e812e782e52b536c0307bb26b3c244e1c42b644235f5a4b242786b1ef375358\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_bsd_no_end_paren(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    # if BSD is missing a paren, we don't raise an exception, just ignore and
    # continue
    f.write('MD5 (Fedora-11-i386-DVD.iso=6e812e782e52b536c0307bb26b3c244e1c42b644235f5a4b242786b1ef375358\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_bsd_no_equal(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    # if BSD is missing a paren, we don't raise an exception, just ignore and
    # continue
    f.write('MD5 (Fedora-11-i386-DVD.iso) 6e812e782e52b536c0307bb26b3c244e1c42b644235f5a4b242786b1ef375358\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_regular_escaped(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('\\6e812e782e52b536c0307bb26b3c244e *Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_regular_too_short(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e *F\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_regular_no_star(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e812e782e52b536c0307bb26b3c244e Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_regular_no_newline(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e812e782e52b536c0307bb26b3c244e *Fedora-11-i386-DVD.iso')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

def test_md5sum_regular_no_space(tmpdir):
    src = os.path.join(str(tmpdir), 'md5sum')
    f = open(src, 'w')
    f.write('6e812e782e52b536c0307bb26b3c244e_*Fedora-11-i386-DVD.iso\n')
    f.close()

    oz.ozutil.get_md5sum_from_file(src, 'Fedora-11-i386-DVD.iso')

########NEW FILE########
__FILENAME__ = test_tdl
#!/usr/bin/python

import sys
import os

try:
    import lxml.etree
except ImportError:
    print('Unable to import lxml.  Is python-lxml installed?')
    sys.exit(1)

try:
    import py.test
except ImportError:
    print('Unable to import py.test.  Is py.test installed?')
    sys.exit(1)

# Find oz
prefix = '.'
for i in range(0,3):
    if os.path.isdir(os.path.join(prefix, 'oz')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

try:
    import oz
    import oz.TDL
except ImportError:
    print('Unable to import oz.  Is oz installed?')
    sys.exit(1)

# the tests dictionary lists all of the test we will run.  The key for the
# dictionary is the filename of the test, and the value is whether the test
# is expected to succeed (True) or not (False)
tests = {
    "test-01-simple-iso.tdl": True,
    "test-02-simple-url.tdl": True,
    "test-03-empty-template.tdl": False,
    "test-04-no-os.tdl": False,
    "test-05-no-name.tdl": False,
    "test-06-simple-iso-description.tdl": True,
    "test-07-packages-no-package.tdl": True,
    "test-08-repositories-no-repository.tdl": True,
    "test-09-os-invalid-arch.tdl": False,
    "test-10-os-invalid-install-type.tdl": False,
    "test-11-description-packages-repositories.tdl": True,
    "test-12-os-no-name.tdl": False,
    "test-13-os-no-version.tdl": False,
    "test-14-os-no-arch.tdl": False,
    "test-15-os-no-install.tdl": False,
    "test-16-signed-repository.tdl": True,
    "test-17-repo-invalid-signed.tdl": False,
    "test-18-rootpw.tdl": True,
    "test-19-key.tdl": True,
    "test-20-multiple-install.tdl": False,
    "test-21-missing-install-type.tdl": False,
    "test-22-md5sum.tdl": True,
    "test-23-sha1sum.tdl": True,
    "test-24-sha256sum.tdl": True,
    "test-25-md5sum-and-sha1sum.tdl": False,
    "test-26-md5sum-and-sha256sum.tdl": False,
    "test-27-sha1sum-and-sha256sum.tdl": False,
    "test-28-package-no-name.tdl": False,
    "test-29-files.tdl": True,
    "test-30-file-no-name.tdl": False,
    "test-31-file-raw-type.tdl": True,
    "test-32-file-base64-type.tdl": True,
    "test-33-file-invalid-type.tdl": False,
    "test-34-file-invalid-base64.tdl": False,
    "test-35-repository-no-name.tdl": False,
    "test-36-repository-no-url.tdl": False,
    "test-37-command.tdl": True,
    "test-38-command-no-name.tdl": False,
    "test-39-command-raw-type.tdl": True,
    "test-40-command-base64-type.tdl": True,
    "test-41-command-bogus-base64.tdl": False,
    "test-42-command-bogus-type.tdl": False,
    "test-43-persisted-repos.tdl": True,
    "test-44-version.tdl": True,
    "test-45-bogus-version.tdl": False,
    "test-46-duplicate-name.tdl": False,
    "test-47-invalid-template.tdl": False,
    "test-48-file-empty-base64.tdl": True,
    "test-49-file-empty-raw.tdl": True,
    "test-50-command-base64-empty.tdl": False,
    "test-51-disk-size.tdl": True,
    "test-52-command-file-url.tdl": True,
    "test-53-command-http-url.tdl": True,
    "test-54-files-file-url.tdl": True,
    "test-55-files-http-url.tdl": True,
}

# Validate oz handling of tdl file
def validate_ozlib(tdl_file):
    xmldata = open(tdl_file, 'r').read()
    return oz.TDL.TDL(xmldata)

# Validate schema
def validate_schema(tdl_file):

    # Locate relaxng schema
    rng_file = None
    for tryme in ['../../oz/tdl.rng',
                  '../oz/tdl.rng',
                  'oz/tdl.rng',
                  'tdl.rng',]:
        if os.path.isfile(tryme):
            rng_file = tryme
            break

    if rng_file is None:
        raise Exception('RelaxNG schema file not found: tdl.rng')

    relaxng = lxml.etree.RelaxNG(file=rng_file)
    xml = open(tdl_file, 'r')
    doc = lxml.etree.parse(xml)
    xml.close()

    valid = relaxng.validate(doc)
    if not valid:
        errstr = "\n%s XML schema validation failed:\n" % (tdl_file)
        for error in relaxng.error_log:
            errstr += "\tline %s: %s\n" % (error.line, error.message)
        raise Exception(errstr)

# Test generator that iterates over all .tdl files
def test():

    # Define a helper to expect an exception
    def handle_exception(func, *args):
        with py.test.raises(Exception):
            func(*args)

    # Sanity check to see if any tests are unaccounted for in the config file
    for (tdl, expected_pass) in list(tests.items()):

        # locate full path for tdl file
        tdl_prefix = ''
        for tdl_prefix in ['tests/tdl/', 'tdl/', '']:
            if os.path.isfile(tdl_prefix + tdl):
                break
        tdl_file = tdl_prefix + tdl
        test_name = os.path.splitext(tdl,)[0]

        # Generate a unique unittest test for each validate_* method
        for tst in (validate_ozlib, validate_schema, ):
            # We need a unique method name
            unique_name = test_name + tst.__name__

            # Are we expecting the test to fail?
            if expected_pass:
                yield '%s_%s' % (test_name, tst.__name__), tst, tdl_file
            else:
                yield '%s_%s' % (test_name, tst.__name__), handle_exception,\
                    tst, tdl_file

def test_persisted(tdl='test-43-persisted-repos.tdl'):
    # locate full path for tdl file
    tdl_prefix = ''
    for tdl_prefix in ['tests/tdl/', 'tdl/', '']:
        if os.path.isfile(tdl_prefix + tdl):
            break
    if not os.path.isfile(tdl_prefix + tdl):
        raise Exception('Unable to locate TDL: %s' % tdl)
    tdl_file = tdl_prefix + tdl
    test_name = os.path.splitext(tdl,)[0]

    # Grab TDL object
    tdl = validate_ozlib(tdl_file)

    def assert_persisted_value(persisted, value):
        assert persisted == value, \
            "expected %s, got %s" % (value, persisted)

    for repo in list(tdl.repositories.values()):
        if repo.name.endswith('true'):
            yield '%s_%s' % (test_name, repo.name), assert_persisted_value, repo.persisted, True
        else:
            yield '%s_%s' % (test_name, repo.name), assert_persisted_value, repo.persisted, False

########NEW FILE########
