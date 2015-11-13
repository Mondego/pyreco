__FILENAME__ = Docker
#!/usr/bin/python
#
#   Copyright 2014 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import libxml2
import json
import os
import struct
import subprocess
from xml.etree.ElementTree import fromstring
from imgfac.Template import Template
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.BuildDispatcher import BuildDispatcher
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.CloudDelegate import CloudDelegate
from imgfac.FactoryUtils import launch_inspect_and_mount, shutdown_and_close, remove_net_persist, create_cloud_info

class Docker(object):
    zope.interface.implements(CloudDelegate)

    compress_commands = { "xz":    "xz -T 0 --stdout %s > %s",
                          "gzip":  "gzip -c %s > %s",
                          "bzip2": "bzip2 -c %s > %s" }

    def __init__(self):
        super(Docker, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        raise ImageFactoryException("Pushing not currently supported for Docker image builds")

    def snapshot_image_on_provider(self, builder, provider, credentials, template, parameters):
        # TODO: Implement snapshot builds
        raise ImageFactoryException("Snapshot builds not currently supported for Docker")

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.debug("builder_should_create_target_image called for Docker plugin - doing all our work here then stopping the process")
        # At this point our input base_image is available as builder.base_image.data
        # We simply mount it up in libguestfs and tar out the results as builder.target_image.data
        compress_type = parameters.get('compress', None)
        if compress_type:
            if compress_type in self.compress_commands.keys():
                compress_command = self.compress_commands[compress_type]
            else:
                raise Exception("Passed unknown compression type (%s) for Docker plugin" % (compress_type))
        else:
            compress_command = None
        guestfs_handle = launch_inspect_and_mount(builder.base_image.data, readonly = True)
        self.log.debug("Creating tar of root directory of input image %s saving as output image %s" % 
                       (builder.base_image.data, builder.target_image.data) )
        guestfs_handle.tar_out_opts("/", builder.target_image.data)
        if compress_command:
            self.log.debug("Compressing tar file using %s" % (compress_type))
            rawimage =  builder.target_image.data
            compimage =  builder.target_image.data + ".tmp.%s" % (compress_type)
            result = subprocess.call(compress_command % ( rawimage, compimage), shell = True)
            if result:
                raise Exception("Compression of image failed")
            self.log.debug("Compression complete, replacing original")
            os.unlink(rawimage)
            os.rename(compimage, rawimage)
            self.log.debug("Done")
        return False

    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        raise ImageFactoryException("builder_will_create_target_image called in Docker plugin - this should never happen")


    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        raise ImageFactoryException("builder_did_create_target_image called in Docker plugin - this should never happen") 

########NEW FILE########
__FILENAME__ = EC2
#
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import oz.Fedora
import oz.TDL
import subprocess
import os
import re
import guestfs
import string
import libxml2
import traceback
import ConfigParser
import boto.ec2
import sys
import json
from time import *
from tempfile import *
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.ReservationManager import ReservationManager
from boto.s3.connection import S3Connection
from boto.s3.connection import Location
from boto.exception import *
from boto.ec2.blockdevicemapping import EBSBlockDeviceType, BlockDeviceMapping
from imgfac.CloudDelegate import CloudDelegate
from imgfac.FactoryUtils import *
from xml.etree import ElementTree

# Boto is very verbose - shut it up
logging.getLogger('boto').setLevel(logging.INFO)


class EC2(object):
    zope.interface.implements(CloudDelegate)

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def __init__(self):
        # Note that we are now missing ( template, target, config_block = None):
        super(EC2, self).__init__()
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        config_obj = ApplicationConfiguration()
        self.app_config = config_obj.configuration
        self.oz_config = ConfigParser.SafeConfigParser()
        self.oz_config.read("/etc/oz/oz.cfg")
        self.oz_config.set('paths', 'output_dir', self.app_config["imgdir"])
        self.guest = None

        if "ec2" in config_obj.jeos_images:
            self.ec2_jeos_amis = config_obj.jeos_images['ec2']
        else:
            self.log.warning("No JEOS amis defined for ec2.  Snapshot builds will not be possible.")
            self.ec2_jeos_amis = {}


    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_should_create_target_image() called on EC2 plugin - returning True')
        return True


    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        # Nothing really to do here
        pass


    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_did_create_target_image() called in EC2 plugin')
        # The bulk of what is done here is EC2 specific
        # There are OS conditionals thrown in at the moment
        # For now we are putting everything into the EC2 Cloud plugin
        # TODO: Revisit this, and the plugin interface, to see if there are ways to
        #       make the separation cleaner

        # This lets our logging helper know what image is being operated on
        self.builder = builder
        self.active_image = self.builder.target_image

        try:
            # TODO: More convenience vars - revisit
            self.template = template
            self.target = target
            self.tdlobj = oz.TDL.TDL(xmlstring=self.template.xml, rootpw_required=self.app_config["tdl_require_root_pw"])
            self._get_os_helper()
            # Add in target specific content
            self.add_target_content()

            # TODO: This is a convenience variable for refactoring - rename
            self.new_image_id = builder.target_image.identifier

            # This lets our logging helper know what image is being operated on
                    
            self.activity("Initializing Oz environment")
            # Create a name combining the TDL name and the UUID for use when tagging EC2 AMIs
            self.longname = self.tdlobj.name + "-" + self.new_image_id

            # Oz assumes unique names - TDL built for multiple backends guarantees they are not unique
            # We don't really care about the name so just force uniqueness
            self.tdlobj.name = "factory-build-" + self.new_image_id

            # populate a config object to pass to OZ; this allows us to specify our
            # own output dir but inherit other Oz behavior
            self.oz_config = ConfigParser.SafeConfigParser()
            self.oz_config.read("/etc/oz/oz.cfg")
            self.oz_config.set('paths', 'output_dir', self.app_config["imgdir"])

            # make this a property to enable quick cleanup on abort
            self.instance = None

            # OK great, we now have a customized KVM image
            # Now we do some target specific transformation
            # None of these things actually require anything other than the TDL object
            # and the original disk image
            
            # At this point our builder has a target_image and a base_image
            # OS plugin has already provided the initial file for us to work with
            # which we can currently assume is a raw KVM compatible image
            self.image = builder.target_image.data

            self.modify_oz_filesystem()

            self.ec2_copy_filesystem()
            self.ec2_modify_filesystem()

        except:
            self.log_exc()
            self.status="FAILED"
            raise

        self.percent_complete=100
        self.status="COMPLETED"

    def _get_os_helper(self):
        # For now we are adopting a 'mini-plugin' approach to OS specific code within the EC2 plugin
        # In theory, this could live in the OS plugin - however, the code in question is very tightly
        # related to the EC2 plugin, so it probably should stay here
        try:
            # Change RHEL-6 to RHEL6, etc.
            os_name = self.tdlobj.distro.translate(None, '-')
            class_name = "%s_ec2_Helper" % (os_name)
            module_name = "imagefactory_plugins.EC2.EC2CloudOSHelpers"
            __import__(module_name)
            os_helper_class = getattr(sys.modules[module_name], class_name)
            self.os_helper = os_helper_class(self)
        except:
            self.log_exc()
            raise ImageFactoryException("Unable to create EC2 OS helper object for distro (%s) in TDL" % (self.tdlobj.distro) )

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        self.log.info('push_image_to_provider() called in EC2')

        self.builder = builder
        self.active_image = self.builder.provider_image

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.provider_image.identifier

        self.tdlobj = oz.TDL.TDL(xmlstring=builder.target_image.template, rootpw_required=self.app_config["tdl_require_root_pw"])
        self._get_os_helper()
        self.push_image_upload(target_image, provider, credentials)


    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        self.builder = builder
        self.active_image = self.builder.provider_image
        self.log.debug("Deleting AMI (%s)" % (self.active_image.identifier_on_provider))
        self.activity("Preparing EC2 region details")
        region=provider
        region_conf=self._decode_region_details(region)
        boto_loc = region_conf['boto_loc']
        if(boto_loc == ''):
            boto_loc = 'us-east-1'
        if region_conf['host'] != "us-east-1":
            s3_host = 's3-%s.amazonaws.com' % region_conf['host']
        else:
            # Note to Amazon - would it be that hard to have s3-us-east-1.amazonaws.com?
            s3_host = "s3.amazonaws.com"

        self.ec2_decode_credentials(credentials)
        
        ec2region = boto.ec2.get_region(boto_loc, aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)
        conn = ec2region.connect(aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)

        amis = conn.get_all_images([ self.builder.provider_image.identifier_on_provider ])
        if len(amis) == 0:
            raise ImageFactoryException("Unable to find AMI (%s) - cannot delete it" % (self.builder.provider_image.identifier_on_provider))
        if len(amis) > 1:
            raise ImageFactoryException("AMI lookup during delete returned more than one result - this should never happen - aborting")

        ami = amis[0]

        if ami.root_device_type == "ebs":
            self.log.debug("This is an EBS AMI")
            # Disect the block device mapping to identify the snapshots
            bd_map = ami.block_device_mapping
            self.log.debug("De-registering AMI")
            ami.deregister()
            self.log.debug("Deleting EBS snapshots associated with AMI")
            for bd in bd_map:
                self.log.debug("Deleting bd snapshot (%s) for bd (%s)" % (bd_map[bd].snapshot_id, bd))
                conn.delete_snapshot(bd_map[bd].snapshot_id)
        else:
            self.log.debug("This is an S3 AMI")
            s3_conn = boto.s3.connection.S3Connection(aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key, host=s3_host)
            # Disect the location to get the bucket and key for the manifest
            (bucket, key) = string.split(ami.location, '/', 1)
            self.log.debug("Retrieving S3 AMI manifest from bucket (%s) at key (%s)" % (bucket, key))
            bucket = s3_conn.get_bucket(bucket)
            key_obj = bucket.get_key(key)
            manifest = key_obj.get_contents_as_string()
            # It is possible that the key has a path-like structure"
            # The XML contains only filenames - not path components
            # so extract any "directory" type stuff here
            keyprefix = ""
            keysplit = string.rsplit(key, "/", 1)
            if len(keysplit) == 2:
                keyprefix="%s/" % (keysplit[0])

            self.log.debug("Deleting S3 image disk chunks")
            man_etree = ElementTree.fromstring(manifest)
            for part in man_etree.find("image").find("parts").findall("part"):
                filename = part.find("filename").text
                fullname = "%s%s" % (keyprefix, filename)
                part_key_obj = bucket.get_key(fullname)
                self.log.debug("Deleting %s" % (fullname))
                part_key_obj.delete()
            self.log.debug("Deleting manifest object %s" % (key))
            key_obj.delete()
            
            self.log.debug("de-registering the AMI itself")
            ami.deregister()

    def log_exc(self):
        self.log.debug("Exception caught in ImageFactory")
        self.log.debug(traceback.format_exc())
        self.active_image.status_detail['error'] = traceback.format_exc()

    def modify_oz_filesystem(self):
        self.activity("Removing unique identifiers from image - Adding cloud information")
        guestfs_handle = launch_inspect_and_mount(self.builder.target_image.data)
        remove_net_persist(guestfs_handle)
        create_cloud_info(guestfs_handle, self.target)
        shutdown_and_close(guestfs_handle)

    def ec2_copy_filesystem(self):

        self.activity("Copying image contents to single flat partition for EC2")
        target_image=self.image + ".tmp"

        self.log.debug("init guestfs")
        g = guestfs.GuestFS ()

        self.log.debug("add input image")
        # /dev/sda
        g.add_drive (self.image)

        self.log.debug("create target image")
        # /dev/sdb
        f = open (target_image, "w")
        # TODO: Can this be larger, smaller - should it be?
        f.truncate (10000 * 1024 * 1024)
        f.close ()
        g.add_drive(target_image)

        g.launch()

        g.mkmountpoint("/in")
        g.mkmountpoint("/out")
        g.mkmountpoint("/out/in")

        # Input image ends up mounted at /in
        inspect_and_mount(g, relative_mount="/in")

        # Blank target image ends up mounted at /out/in
        # Yes, this looks odd but it is the easiest way to use cp_a from guestfs
        # cp_a is needed because we cannot use wildcards directly with guestfs
        # TODO: Inherit the FS type from the source image instead of ext3 hardcode
        g.mkfs ("ext3", "/dev/sdb")
        g.set_e2label ("/dev/sdb", "/")
        g.mount_options ("", "/dev/sdb", "/out/in")

        # See how nice this is
        self.log.info("Copying image contents to EC2 flat filesystem")
        g.cp_a("/in/", "/out")

        self.log.debug("Shutting down and closing libguestfs")
        shutdown_and_close(g)

        self.log.debug("Copy complete - removing old image and replacing with new flat filesystem image")
        os.unlink(self.image)
        os.rename(target_image, self.image)


    def ec2_modify_filesystem(self):
        # Modifications
        # Many of these are more or less directly ported from BoxGrinder
        # Boxgrinder is written and maintained by Marek Goldmann and can be found at:
        # http://boxgrinder.org/

        # TODO: This would be safer and more robust if done within the running modified
        # guest - in this would require tighter Oz integration

        self.activity("Modifying flat filesystem with EC2 specific changes")
        g = guestfs.GuestFS ()

        g.add_drive(self.image)
        g.launch ()

        # Do inspection here, as libguestfs prefers we do it before mounting anything
        # This should always be /dev/vda or /dev/sda but we do it anyway to be safe
        osroot = g.inspect_os()[0]

        # eg "fedora"
        distro = g.inspect_get_distro(osroot)
        arch = g.inspect_get_arch(osroot)
        major_version = g.inspect_get_major_version(osroot)
        minor_version = g.inspect_get_minor_version(osroot)

        self.log.debug("distro: %s - arch: %s - major: %s - minor %s" % (distro, arch, major_version, minor_version))

        g.mount_options ("", osroot, "/")

        self.log.info("Modifying flat FS contents to be EC2 compatible")

        self.log.info("Disabling SELINUX")
        tmpl = '# Factory Disabled SELINUX - sorry\nSELINUX=permissive\nSELINUXTYPE=targeted\n'
        g.write("/etc/sysconfig/selinux", tmpl)

        # Make a /data directory for 64 bit hosts
        # Ephemeral devs come pre-formatted from AWS - weird
        if arch == "x86_64":
            self.log.info("Making data directory")
            g.mkdir("/data")

        # BG - Upload one of two templated fstabs
        # Input - root device name
        # TODO: Match OS default behavior and/or what is found in the existing image

        self.log.info("Modifying and uploading fstab")
        # Make arch conditional
        if arch == "x86_64":
            tmpl=self.fstab_64bit
        else:
            tmpl=self.fstab_32bit

        g.write("/etc/fstab", tmpl)

        # BG - Enable networking
        # Upload a known good ifcfg-eth0 and then chkconfig on networking
        self.log.info("Enabling networking and uploading ifcfg-eth0")
        g.sh("/sbin/chkconfig network on")
        g.write("/etc/sysconfig/network-scripts/ifcfg-eth0", self.ifcfg_eth0)

        # Disable first boot - this slows things down otherwise
        if g.is_file("/etc/init.d/firstboot"):
            g.sh("/sbin/chkconfig firstboot off")

        # Ensure a sensible runlevel on systemd systems (>=F15)
        # Oz/Anaconda hand us a graphical runlevel
        if g.is_symlink("/etc/systemd/system/default.target"):
            g.rm("/etc/systemd/system/default.target")
            g.ln_s("/lib/systemd/system/multi-user.target","/etc/systemd/system/default.target")

        # BG - Upload rc.local extra content
        # Again, this uses a static copy - this bit is where the ssh key is downloaded
        # TODO: Is this where we inject puppet?
        # TODO - Possibly modify the key injection from rc_local to be only non-root
        #  and add a special user to sudoers - this is what BG has evolved to do
        self.log.info("Updating rc.local for key injection")
        g.write("/tmp/rc.local", self.rc_local)
        # Starting with F16, rc.local doesn't exist by default
        if not g.exists("/etc/rc.d/rc.local"):
            g.sh("echo \#\!/bin/bash > /etc/rc.d/rc.local")
            g.sh("chmod a+x /etc/rc.d/rc.local")
        g.sh("cat /tmp/rc.local >> /etc/rc.d/rc.local")
        g.rm("/tmp/rc.local")

        # Don't ever allow password logins to EC2 sshd
        g.aug_init("/", 0)
        g.aug_set("/files/etc/ssh/sshd_config/PermitRootLogin", "without-password")
        g.aug_save()
        g.aug_close()
        self.log.debug("Disabled root loging with password in /etc/ssh/sshd_config")

        # Install menu list
        # Derive the kernel version from the last element of ls /lib/modules and some
        # other magic - look at linux_helper for details

        # Look at /lib/modules and assume that the last kernel listed is the version we use
        self.log.info("Modifying and updating menu.lst")
        kernel_versions = g.ls("/lib/modules")
        kernel_version = None
        if (distro == "rhel") and (major_version == 5):
            xenre = re.compile("xen$")
            for kern in kernel_versions:
                if xenre.search(kern):
                    kernel_version = kern
        elif (len(kernel_versions) > 1) and (arch == "i386") and (distro == "fedora") and (int(major_version) <=13):
            paere = re.compile("PAE$")
            for kern in kernel_versions:
                if paere.search(kern):
                    kernel_version = kern
        else:
            kernel_version = kernel_versions[len(kernel_versions)-1]
        if not kernel_version:
            self.log.debug("Unable to extract correct kernel version from: %s" % (str(kernel_versions)))
            raise ImageFactoryException("Unable to extract kernel version")

        self.log.debug("Using kernel version: %s" % (kernel_version))


        # We could deduce this from version but it's easy to inspect
        bootramfs = int(g.sh("ls -1 /boot | grep initramfs | wc -l"))
        ramfs_prefix = "initramfs" if bootramfs > 0 else "initrd"

        name="Image Factory EC2 boot - kernel: " + kernel_version

        if (distro == "rhel") and (major_version == 5):
            g.sh("/sbin/mkinitrd -f -v --preload xenblk --preload xennet /boot/initrd-%s.img %s" % (kernel_version))

        kernel_options = ""
        if (distro == "fedora") and (str(major_version) == "16"):
            self.log.debug("Adding idle=halt option for Fedora 16 on EC2")
            kernel_options += "idle=halt " 

        tmpl = self.menu_lst
        tmpl = string.replace(tmpl, "#KERNEL_OPTIONS#", kernel_options)
        tmpl = string.replace(tmpl, "#KERNEL_VERSION#", kernel_version)
        tmpl = string.replace(tmpl, "#KERNEL_IMAGE_NAME#", ramfs_prefix)
        tmpl = string.replace(tmpl, "#TITLE#", name)

        if not g.is_dir("/boot/grub"):
            try:
                g.mkdir_p("/boot/grub")
            except RuntimeError:
                raise ImageFactoryException("Unable to create /boot/grub directory - aborting")

        g.write("/boot/grub/menu.lst", tmpl)

        # EC2 Xen nosegneg bug
        # This fixes issues with Fedora >=14 on EC2: https://bugzilla.redhat.com/show_bug.cgi?id=651861#c39
        if (arch == "i386") and (distro == "fedora") and (int(major_version) >= 14):
            self.log.info("Fixing Xen EC2 bug")
            g.sh("echo \"hwcap 1 nosegneg\" > /etc/ld.so.conf.d/libc6-xen.conf")
            g.sh("/sbin/ldconfig")

        self.log.info("Done with EC2 filesystem modifications")

        g.sync ()
        g.umount_all ()

        # TODO: Based on architecture associate one of two XML blocks that contain the correct
        # regional AKIs for pvgrub

    def wait_for_ec2_ssh_access(self, guestaddr, sshprivkey, user='root'):
        self.activity("Waiting for SSH access to EC2 instance (User: %s)" % user)
        for i in range(300):
            if i % 10 == 0:
                self.log.debug("Waiting for EC2 ssh access: %d/300" % (i))

            try:
                ssh_execute_command(guestaddr, sshprivkey, "/bin/true", user=user)
                break
            except:
                pass

            sleep(1)

        if i == 299:
            raise ImageFactoryException("Unable to gain ssh access after 300 seconds - aborting")

    def wait_for_ec2_instance_start(self, instance):
        self.activity("Waiting for EC2 instance to become active")
        for i in range(300):
            if i % 10 == 0:
                self.log.debug("Waiting for EC2 instance to start: %d/300" % (i))
            try:
                instance.update()
            except EC2ResponseError, e:
                # We occasionally get errors when querying an instance that has just started - ignore them and hope for the best
                self.log.warning("EC2ResponseError encountered when querying EC2 instance (%s) - trying to continue" % (instance.id), exc_info = True)
            except:
                self.log.error("Exception encountered when updating status of instance (%s)" % (instance.id), exc_info = True)
                self.status="FAILED"
                try:
                    self.terminate_instance(instance)
                except:
                    self.log.warning("WARNING: Instance (%s) failed to start and will not terminate - it may still be running" % (instance.id), exc_info = True)
                    raise ImageFactoryException("Instance (%s) failed to fully start or terminate - it may still be running" % (instance.id))
                raise ImageFactoryException("Exception encountered when waiting for instance (%s) to start" % (instance.id))
            if instance.state == u'running':
                break
            sleep(1)

        if instance.state != u'running':
            self.status="FAILED"
            try:
                self.terminate_instance(instance)
            except:
                self.log.warning("WARNING: Instance (%s) failed to start and will not terminate - it may still be running" % (instance.id), exc_info = True)
                raise ImageFactoryException("Instance (%s) failed to fully start or terminate - it may still be running" % (instance.id))
            raise ImageFactoryException("Instance failed to start after 300 seconds - stopping")

    def terminate_instance(self, instance):
        # boto 1.9 claims a terminate() method but does not implement it
        # boto 2.0 throws an exception if you attempt to stop() an S3 backed instance
        # introspect here and do the best we can
        if "terminate" in dir(instance):
            instance.terminate()
        else:
            instance.stop()

    def snapshot_image_on_provider(self, builder, provider, credentials, target, template, parameters):
        self.log.info('snapshot_image_on_provider() called in EC2')

        self.builder = builder
        self.active_image = self.builder.provider_image

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.provider_image.identifier
        # TODO: so is this
        self.target = target


        # Template must be defined for snapshots
        self.tdlobj = oz.TDL.TDL(xmlstring=str(template), rootpw_required=self.app_config["tdl_require_root_pw"])
        self._get_os_helper()
        self.os_helper.init_guest()

        # Create a name combining the TDL name and the UUID for use when tagging EC2 AMIs
        self.longname = self.tdlobj.name + "-" + self.new_image_id

        def replace(item):
            if item in [self.ec2_access_key, self.ec2_secret_key]:
                return "REDACTED"
            return item

        self.log.debug("Being asked to push for provider %s" % (provider))
        self.log.debug("distro: %s - update: %s - arch: %s" % (self.tdlobj.distro, self.tdlobj.update, self.tdlobj.arch))
        self.ec2_decode_credentials(credentials)
        self.log.debug("acting as EC2 user: %s" % (str(self.ec2_user_id)))

        self.status="PUSHING"
        self.percent_complete=0

        self.activity("Preparing EC2 region details")
        region=provider
        # These are the region details for the TARGET region for our new AMI
        region_conf=self._decode_region_details(region)
        aki = region_conf[self.tdlobj.arch]
        boto_loc = region_conf['boto_loc']
        if region_conf['host'] != "us-east-1":
            upload_url = "http://s3-%s.amazonaws.com/" % (region_conf['host'])
        else:
            # Note to Amazon - would it be that hard to have s3-us-east-1.amazonaws.com?
            upload_url = "http://s3.amazonaws.com/"

        register_url = "http://ec2.%s.amazonaws.com/" % (region_conf['host'])

        build_region = provider

        try:
            ami_id = self.ec2_jeos_amis[provider][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['img_id']
            user = self.ec2_jeos_amis[provider][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['user']
            cmd_prefix = self.ec2_jeos_amis[provider][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['cmd_prefix']
        except KeyError:
            try:
                # Fallback to modification on us-east and upload cross-region
                ami_id = self.ec2_jeos_amis['ec2-us-east-1'][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['img_id']
                build_region = 'ec2-us-east-1'
                self.log.info("WARNING: Building in ec2-us-east-1 for upload to %s" % (provider))
                self.log.info(" This may be a bit slow - ask the Factory team to create a region-local JEOS")
            except KeyError:
                self.status="FAILED"
                raise ImageFactoryException("No available JEOS for %s %s %s in %s" % (self.tdlobj.distro, self.tdlobj.update, self.tdlobj.arch, region_conf['host']))

            try:
                user = self.ec2_jeos_amis['ec2-us-east-1'][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['user']
                cmd_prefix = self.ec2_jeos_amis['ec2-us-east-1'][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['cmd_prefix']
            except:
                user = 'root'
                cmd_prefix = None

        self.log.debug("Snapshotting %s (%s %s %s) on %s" % (ami_id, self.tdlobj.distro, self.tdlobj.update, self.tdlobj.arch, build_region))

        # These are the region details for the region we are building in (which may be different from the target)
        build_region_conf = self._decode_region_details(build_region)

        # Note that this connection may be to a region other than the target
        self.activity("Preparing EC2 JEOS AMI details")
        ec2region = boto.ec2.get_region(build_region_conf['host'], aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)
        conn = ec2region.connect(aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)

        # Verify that AMI actually exists - err out if not
        # Extract AMI type - "ebs" or "instance-store" (S3)
        # If build_region != provider (meaning we are not building in our target region)
        #  if type == ebs throw an error - EBS builds must be in the target region/provider
        amis = conn.get_all_images([ ami_id ])
        ami = amis[0]
        if (build_region_conf['host'] != region_conf['host']) and (ami.root_device_type == "ebs"):
            self.log.error("EBS JEOS image exists in us-east-1 but not in target region (%s)" % (provider))
            raise ImageFactoryException("No EBS JEOS image for region (%s) - aborting" % (provider))

        instance_type=self.app_config.get('ec2-64bit-util','m1.large')
        if self.tdlobj.arch == "i386":
            instance_type=self.app_config.get('ec2-32bit-util','m1.small')

        # Create a use-once SSH-able security group
        self.activity("Creating EC2 security group for SSH access to utility image")
        factory_security_group_name = "imagefactory-%s" % (self.new_image_id, )
        factory_security_group_desc = "Temporary ImageFactory generated security group with SSH access"
        self.log.debug("Creating temporary security group (%s)" % (factory_security_group_name))
        factory_security_group = conn.create_security_group(factory_security_group_name, factory_security_group_desc)
        factory_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')

        # Create a use-once SSH key
        self.activity("Creating EC2 SSH key pair")
        key_name = "fac-tmp-key-%s" % (self.new_image_id)
        key = conn.create_key_pair(key_name)
        # Shove into a named temp file
        key_file_object = NamedTemporaryFile()
        key_file_object.write(key.material)
        key_file_object.flush()
        key_file=key_file_object.name

        # Now launch it
        self.activity("Launching EC2 JEOS image")
        self.log.debug("Starting ami %s with instance_type %s" % (ami_id, instance_type))
        reservation = conn.run_instances(ami_id, instance_type=instance_type, key_name=key_name, security_groups = [ factory_security_group_name ])

        if len(reservation.instances) != 1:
            self.status="FAILED"
            raise ImageFactoryException("run_instances did not result in the expected single instance - stopping")

        self.instance = reservation.instances[0]

        self.wait_for_ec2_instance_start(self.instance)

        # From this point on we must be sure to terminate the instance when we are done
        # so wrap in a try/finally
        # Accidentally running a 64 bit instance doing nothing costs 56 USD week
        try:
            guestaddr = self.instance.public_dns_name

            self.guest.sshprivkey = key_file

            # Ugly ATM because failed access always triggers an exception
            self.wait_for_ec2_ssh_access(guestaddr, key_file, user=user)

            # There are a handful of additional boot tasks after SSH starts running
            # Give them an additional 20 seconds for good measure
            self.log.debug("Waiting 20 seconds for remaining boot tasks")
            sleep(20)

            if (user != 'root'):
                self.log.debug("Temporarily enabling root user for customization steps...")
                enable_root(guestaddr, key_file, user, cmd_prefix)

            self.activity("Customizing running EC2 JEOS instance")
            self.log.debug("Stopping cron and killing any updatedb process that may be running")
            # updatedb interacts poorly with the bundle step - make sure it isn't running
            self.guest.guest_execute_command(guestaddr, "/sbin/service crond stop")
            self.guest.guest_execute_command(guestaddr, "killall -9 updatedb || /bin/true")
            self.log.debug("Done")

            if ami.root_device_type == "instance-store":
                # Different OSes need different steps here
                # Only needed for S3 images
                self.os_helper.install_euca_tools(guestaddr)

            # Not all JEOS images contain this - redoing it if already present is harmless
            self.log.info("Creating cloud-info file indicating target (%s)" % (self.target))
            self.guest.guest_execute_command(guestaddr, 'echo CLOUD_TYPE=\\\"%s\\\" > /etc/sysconfig/cloud-info' % (self.target))

            self.log.debug("Customizing guest: %s" % (guestaddr))
            self.guest.mkdir_p(self.guest.icicle_tmp)
            self.guest.do_customize(guestaddr)
            self.log.debug("Customization step complete")

            self.log.debug("Generating ICICLE from customized guest")
            self.output_descriptor = self.guest.do_icicle(guestaddr)
            self.log.debug("ICICLE generation complete")

            self.log.debug("Re-de-activate firstboot just in case it has been revived during customize")
            self.guest.guest_execute_command(guestaddr, "[ -f /etc/init.d/firstboot ] && /sbin/chkconfig firstboot off || /bin/true")
            self.log.debug("De-activation complete")

            new_ami_id = None
            image_name = str(self.longname)
            image_desc = "%s - %s" % (asctime(localtime()), self.tdlobj.description)

            if ami.root_device_type == "instance-store":
                # This is an S3 image so we snapshot to another S3 image using euca-bundle-vol and
                # associated tools
                ec2cert =  "/etc/pki/imagefactory/cert-ec2.pem"

                # This is needed for uploading and registration
                # Note that it is excluded from the final image
                self.activity("Uploading certificate material for bundling of instance")
                self.guest.guest_live_upload(guestaddr, self.ec2_cert_file, "/tmp")
                self.guest.guest_live_upload(guestaddr, self.ec2_key_file, "/tmp")
                self.guest.guest_live_upload(guestaddr, ec2cert, "/tmp")
                self.log.debug("Cert upload complete")

                # Some local variables to make the calls below look a little cleaner
                ec2_uid = self.ec2_user_id
                arch = self.tdlobj.arch
                # AKI is set above
                uuid = self.new_image_id

                # We exclude /mnt /tmp and /root/.ssh to avoid embedding our utility key into the image
                command = "euca-bundle-vol -c /tmp/%s -k /tmp/%s -u %s -e /mnt,/tmp,/root/.ssh --arch %s -d /mnt/bundles --kernel %s -p %s -s 10240 --ec2cert /tmp/cert-ec2.pem --fstab /etc/fstab -v /" % (os.path.basename(self.ec2_cert_file), os.path.basename(self.ec2_key_file), ec2_uid, arch, aki, uuid)
                self.activity("Bundling remote instance in-place")
                self.log.debug("Executing bundle vol command: %s" % (command))
                stdout, stderr, retcode = self.guest.guest_execute_command(guestaddr, command)
                self.log.debug("Bundle output: %s" % (stdout))

                # Now, ensure we have an appropriate bucket to receive this image
                # TODO: This is another copy - make it a function soon please
                bucket= "imagefactory-" + region + "-" + self.ec2_user_id

                self.activity("Preparing S3 destination for image bundle")
                sconn = S3Connection(self.ec2_access_key, self.ec2_secret_key)
                try:
                    sconn.create_bucket(bucket, location=boto_loc)
                except S3CreateError as buckerr:
                    if buckerr.error_code == "BucketAlreadyOwnedByYou":
                        # Expected behavior after first push - not an error
                        pass
                    else:
                        raise
                # TODO: End of copy

                # TODO: We cannot timeout on any of the three commands below - can we fix that?
                manifest = "/mnt/bundles/%s.manifest.xml" % (uuid)

                # Unfortunately, for some OS versions we need to correct the manifest
                self.os_helper.correct_remote_manifest(guestaddr, manifest)

                command = ['euca-upload-bundle', '-b', bucket, '-m', manifest,
                           '--ec2cert', '/tmp/cert-ec2.pem',
                           '-a', self.ec2_access_key, '-s', self.ec2_secret_key,
                           '-U', upload_url]
                command_log = map(replace, command)
                self.activity("Uploading bundle to S3")
                self.log.debug("Executing upload bundle command: %s" % (command_log))
                stdout, stderr, retcode = self.guest.guest_execute_command(guestaddr, ' '.join(command))
                self.log.debug("Upload output: %s" % (stdout))

                manifest_s3_loc = "%s/%s.manifest.xml" % (bucket, uuid)

                command = ['euca-register', '-U', register_url,
                           '-A', self.ec2_access_key, '-S', self.ec2_secret_key, '-a', self.tdlobj.arch,
                           #'-n', image_name, '-d', image_desc,
                           manifest_s3_loc]
                command_log = map(replace, command)
                self.activity("Registering bundle as a new AMI")
                self.log.debug("Executing register command: %s" % (command_log))
                stdout, stderr, retcode = self.guest.guest_execute_command(guestaddr,
                                                                           ' '.join(command))
                self.log.debug("Register output: %s" % (stdout))

                m = re.match(".*(ami-[a-fA-F0-9]+)", stdout)
                new_ami_id = m.group(1)
                self.log.debug("Extracted AMI ID: %s " % (new_ami_id))
                ### End S3 snapshot code
            else:
                self.activity("Preparing image for an EBS snapshot")
                self.log.debug("Performing image prep tasks for EBS backed images")
                self.os_helper.ebs_pre_snapshot_tasks(guestaddr)
                self.activity("Requesting EBS snapshot creation by EC2")
                self.log.debug("Creating a new EBS backed image from our running EBS instance")
                new_ami_id = conn.create_image(self.instance.id, image_name, image_desc)
                self.log.debug("EUCA creat_image call returned AMI ID: %s" % (new_ami_id))
                self.activity("Waiting for newly generated AMI to become available")
                # As with launching an instance we have seen occasional issues when trying to query this AMI right
                # away - give it a moment to settle
                sleep(10)
                new_amis = conn.get_all_images([ new_ami_id ])
                new_ami = new_amis[0]
                timeout = 120
                interval = 10
                for i in range(timeout):
                    new_ami.update()
                    if new_ami.state == "available":
                        break
                    elif new_ami.state == "failed":
                        raise ImageFactoryException("Amazon reports EBS image creation failed")
                    self.log.debug("AMI status (%s) - waiting for 'available' - [%d of %d seconds elapsed]" % (new_ami.state, i * interval, timeout * interval))
                    sleep(interval)

            if not new_ami_id:
                raise ImageFactoryException("Failed to produce an AMI ID")

            self.builder.provider_image.icicle = self.output_descriptor
            self.builder.provider_image.identifier_on_provider = new_ami_id
            self.builder.provider_account_identifier = self.ec2_access_key
        finally:
            self.activity("Terminating EC2 instance and deleting security group and SSH key")
            self.terminate_instance(self.instance)
            key_file_object.close()
            conn.delete_key_pair(key_name)
            try:
                timeout = 60
                interval = 5
                for i in range(timeout):
                    self.instance.update()
                    if(self.instance.state == "terminated"):
                        factory_security_group.delete()
                        self.log.debug("Removed temporary security group (%s)" % (factory_security_group_name))
                        break
                    elif(i < timeout):
                        self.log.debug("Instance status (%s) - waiting for 'terminated'. [%d of %d seconds elapsed]" % (self.instance.state, i * interval, timeout * interval))
                        sleep(interval)
                    else:
                        raise Exception("Timeout waiting for instance to terminate.")
            except Exception, e:
                self.log.debug("Unable to delete temporary security group (%s) due to exception: %s" % (factory_security_group_name, e))

        self.log.debug("Fedora_ec2_Builder successfully pushed image with uuid %s as %s" % (self.new_image_id, new_ami_id))

    def push_image_upload(self, target_image_id, provider, credentials):
        self.status="PUSHING"
        self.percent_complete=0
        try:
            if self.app_config["ec2_ami_type"] == "s3":
                self.ec2_push_image_upload(target_image_id, provider,
                                           credentials)
            elif self.app_config["ec2_ami_type"] == "ebs":
                self.ec2_push_image_upload_ebs(target_image_id, provider,
                                               credentials)
            else:
                raise ImageFactoryException("Invalid or unspecified EC2 AMI type in config file")
        except:
            self.log_exc()
            self.status="FAILED"
            raise
        self.status="COMPLETED"

    def _ec2_get_xml_node(self, doc, credtype):
        nodes = doc.xpathEval("//provider_credentials/ec2_credentials/%s" % (credtype))
        if len(nodes) < 1:
            raise ImageFactoryException("No EC2 %s available" % (credtype))

        return nodes[0].content

    def ec2_decode_credentials(self, credentials):
        self.activity("Preparing EC2 credentials")
        doc = libxml2.parseDoc(credentials.strip())

        self.ec2_user_id = self._ec2_get_xml_node(doc, "account_number")
        self.ec2_access_key = self._ec2_get_xml_node(doc, "access_key")
        self.provider_account_identifier = self.ec2_access_key
        self.ec2_secret_key = self._ec2_get_xml_node(doc, "secret_access_key")

        # Support both "key" and "x509_private" as element names
        ec2_key_node = doc.xpathEval("//provider_credentials/ec2_credentials/key")
        if not ec2_key_node:
            ec2_key_node = doc.xpathEval("//provider_credentials/ec2_credentials/x509_private")
        if not ec2_key_node:
            raise ImageFactoryException("No x509 private key found in ec2 credentials")
        ec2_key = ec2_key_node[0].content.strip()

        # Support both "certificate" and "x509_public" as element names
        ec2_cert_node = doc.xpathEval("//provider_credentials/ec2_credentials/certificate")
        if not ec2_cert_node:
            ec2_cert_node = doc.xpathEval("//provider_credentials/ec2_credentials/x509_public")
        if not ec2_cert_node:
            raise ImageFactoryException("No x509 public certificate found in ec2 credentials")
        ec2_cert = ec2_cert_node[0].content.strip()

        doc.freeDoc()

        # Shove certs into  named temporary files
        self.ec2_cert_file_object = NamedTemporaryFile()
        self.ec2_cert_file_object.write(ec2_cert)
        self.ec2_cert_file_object.flush()
        self.ec2_cert_file=self.ec2_cert_file_object.name

        self.ec2_key_file_object = NamedTemporaryFile()
        self.ec2_key_file_object.write(ec2_key)
        self.ec2_key_file_object.flush()
        self.ec2_key_file=self.ec2_key_file_object.name

    def ec2_push_image_upload_ebs(self, target_image_id, provider, credentials):
        # TODO: Merge with ec2_push_image_upload and/or factor out duplication
        # In this case we actually do need an Oz object to manipulate a remote guest
        self.os_helper.init_guest()

        self.ec2_decode_credentials(credentials)
        # We don't need the x509 material here so close the temp files right away
        # TODO: Mod the decode to selectively create the files in the first place
        #   This is silly and messy
        self.ec2_cert_file_object.close()
        self.ec2_key_file_object.close()

        # Image is always here and it is the target_image datafile
        input_image = self.builder.target_image.data

        input_image_compressed = input_image + ".gz"
        input_image_compressed_name = os.path.basename(input_image_compressed)
        compress_complete_marker = input_image_compressed + "-factory-compressed"

        # We are guaranteed to hit this from multiple builders looking at the same image
        # Grab a named lock based on the file name
        # If the file is not present this guarantees that only one thread will compress
        # NOTE: It is important to grab the lock before we even look for the file
        # TODO: Switched this to use shell callouts because of a 64 bit bug - fix that
        res_mgr = ReservationManager()
        res_mgr.get_named_lock(input_image_compressed)
        try:
            if not os.path.isfile(input_image_compressed) or not os.path.isfile(compress_complete_marker):
                self.activity("Compressing image file for upload to EC2")
                self.log.debug("No compressed version of image file found - compressing now")
                compress_command = 'gzip -c %s > %s' % (input_image, input_image_compressed)
                self.log.debug("Compressing image file with external gzip cmd: %s" % (compress_command))
                result = subprocess.call(compress_command, shell = True)
                if result:
                    raise ImageFactoryException("Compression of image failed")
                self.log.debug("Compression complete")
                # Mark completion with an empty file
                # Without this we might use a partially compressed file that resulted from a crash or termination
                subprocess.call("touch %s" % (compress_complete_marker), shell = True)
        finally:
            res_mgr.release_named_lock(input_image_compressed)

        self.activity("Preparing EC2 region details")
        region=provider
        region_conf=self._decode_region_details(region)
        aki = region_conf[self.tdlobj.arch]

        # Use our F16 - 32 bit JEOS image as the utility image for uploading to the EBS volume
        try:
            ami_id = self.ec2_jeos_amis['ec2-' + region_conf['host']]['Fedora']['16']['i386']
        except KeyError:
            raise ImageFactoryException("No Fedora 16 i386 JEOS/utility image in region (%s) - aborting" % (provider))

        # i386
        instance_type=self.app_config.get('ec2-32bit-util','m1.small')

        self.activity("Initializing connection to ec2 region (%s)" % region_conf['host'])
        ec2region = boto.ec2.get_region(region_conf['host'], aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)
        conn = ec2region.connect(aws_access_key_id=self.ec2_access_key, aws_secret_access_key=self.ec2_secret_key)

        # Create security group
        self.activity("Creating EC2 security group for SSH access to utility image")
        factory_security_group_name = "imagefactory-%s" % (str(self.new_image_id))
        factory_security_group_desc = "Temporary ImageFactory generated security group with SSH access"
        self.log.debug("Creating temporary security group (%s)" % (factory_security_group_name))
        factory_security_group = conn.create_security_group(factory_security_group_name, factory_security_group_desc)
        factory_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')

        # Create a use-once SSH key
        self.activity("Creating SSH key pair for image upload")
        key_name = "fac-tmp-key-%s" % (self.new_image_id)
        key = conn.create_key_pair(key_name)
        # Shove into a named temp file
        key_file_object = NamedTemporaryFile()
        key_file_object.write(key.material)
        key_file_object.flush()
        key_file=key_file_object.name

        # Now launch it
        self.activity("Launching EC2 utility image")
        reservation = conn.run_instances(ami_id, instance_type=instance_type, key_name=key_name, security_groups = [ factory_security_group_name ])

        if len(reservation.instances) != 1:
            self.status="FAILED"
            raise ImageFactoryException("run_instances did not result in the expected single instance - stopping")

        self.instance = reservation.instances[0]

        self.wait_for_ec2_instance_start(self.instance)

        # From this point on we must be sure to terminate the instance when we are done
        # so wrap in a try/finally
        # Accidentally running a 64 bit instance doing nothing costs 56 USD week
        volume = None
        try:
            guestaddr = self.instance.public_dns_name

            self.guest.sshprivkey = key_file

            # Ugly ATM because failed access always triggers an exception
            self.wait_for_ec2_ssh_access(guestaddr)

            # There are a handful of additional boot tasks after SSH starts running
            # Give them an additional 20 seconds for good measure
            self.log.debug("Waiting 20 seconds for remaining boot tasks")
            sleep(20)

            self.activity("Creating 10 GiB volume in (%s) to hold new image" % (self.instance.placement))
            volume = conn.create_volume(10, self.instance.placement)

            # Do the upload before testing to see if the volume has completed
            # to get a bit of parallel work
            self.activity("Uploading compressed image file")
            self.guest.guest_live_upload(guestaddr, input_image_compressed, "/mnt")

            # Don't burden API users with the step-by-step details here
            self.activity("Preparing EC2 volume to receive new image")

            # Volumes can sometimes take a very long time to create
            # Wait up to 10 minutes for now (plus the time taken for the upload above)
            self.log.debug("Waiting up to 600 seconds for volume (%s) to become available" % (volume.id))
            retcode = 1
            for i in range(60):
                volume.update()
                if volume.status == "available":
                    retcode = 0
                    break
                self.log.debug("Volume status (%s) - waiting for 'available': %d/600" % (volume.status, i*10))
                sleep(10)

            if retcode:
                raise ImageFactoryException("Unable to create target volume for EBS AMI - aborting")

            # Volume is now available
            # Attach it
            conn.attach_volume(volume.id, self.instance.id, "/dev/sdh")

            self.log.debug("Waiting up to 120 seconds for volume (%s) to become in-use" % (volume.id))
            retcode = 1
            for i in range(12):
                volume.update()
                vs = volume.attachment_state()
                if vs == "attached":
                    retcode = 0
                    break
                self.log.debug("Volume status (%s) - waiting for 'attached': %d/120" % (vs, i*10))
                sleep(10)

            if retcode:
                raise ImageFactoryException("Unable to attach volume (%s) to instance (%s) aborting" % (volume.id, self.instance.id))

            # TODO: This may not be necessary but it helped with some funnies observed during testing
            #         At some point run a bunch of builds without the delay to see if it breaks anything
            self.log.debug("Waiting 20 seconds for EBS attachment to stabilize")
            sleep(20)

            # Decompress image into new EBS volume
            self.activity("Decompressing image into new volume")
            command = "gzip -dc /mnt/%s | dd of=/dev/xvdh bs=4k\n" % (input_image_compressed_name)
            self.log.debug("Decompressing image file into EBS device via command: %s" % (command))
            self.guest.guest_execute_command(guestaddr, command)

            # Sync before snapshot
            self.guest.guest_execute_command(guestaddr, "sync")

            # Snapshot EBS volume
            self.activity("Taking EC2 snapshot of new volume")
            self.log.debug("Taking snapshot of volume (%s)" % (volume.id))
            snapshot = conn.create_snapshot(volume.id, 'Image Factory Snapshot for provider image %s' % self.new_image_id)

            # This can take a _long_ time - wait up to 20 minutes
            self.log.debug("Waiting up to 1200 seconds for snapshot (%s) to become completed" % (snapshot.id))
            retcode = 1
            for i in range(120):
                snapshot.update()
                if snapshot.status == "completed":
                    retcode = 0
                    break
                self.log.debug("Snapshot progress(%s) -  status (%s) - waiting for 'completed': %d/1200" % (str(snapshot.progress), snapshot.status, i*10))
                sleep(10)

            if retcode:
                raise ImageFactoryException("Unable to snapshot volume (%s) - aborting" % (volume.id))

            # register against snapshot
            self.activity("Registering snapshot as a new AMI")
            self.log.debug("Registering snapshot (%s) as new EBS AMI" % (snapshot.id))
            ebs = EBSBlockDeviceType()
            ebs.snapshot_id = snapshot.id
            ebs.delete_on_termination = True
            block_map = BlockDeviceMapping()
            block_map['/dev/sda1'] = ebs
            # The ephemeral mappings are automatic with S3 images
            # For EBS images we need to make them explicit
            # These settings are required to make the same fstab work on both S3 and EBS images
            e0 = EBSBlockDeviceType()
            e0.ephemeral_name = 'ephemeral0'
            e1 = EBSBlockDeviceType()
            e1.ephemeral_name = 'ephemeral1'
            if self.tdlobj.arch == "i386":
                block_map['/dev/sda2'] = e0
                block_map['/dev/sda3'] = e1
            else:
                block_map['/dev/sdb'] = e0
                block_map['/dev/sdc'] = e1
            result = conn.register_image(name='ImageFactory created AMI - %s' % (self.new_image_id),
                            description='ImageFactory created AMI - %s' % (self.new_image_id),
                            architecture=self.tdlobj.arch,  kernel_id=aki,
                            root_device_name='/dev/sda1', block_device_map=block_map)

            ami_id = str(result)
            self.log.debug("Extracted AMI ID: %s " % (ami_id))
        except:
            self.log.debug("EBS image upload failed on exception")
            #DANGER!!! Uncomment at your own risk!
            #This is for deep debugging of the EBS utility instance - don't forget to shut it down manually
            #self.log.debug("EBS image upload failed on exception", exc_info = True)
            #self.log.debug("Waiting more or less forever to allow inspection of the instance")
            #self.log.debug("run this: ssh -i %s root@%s" % (key_file, self.instance.public_dns_name))
            #sleep(999999)
            raise
        finally:
            self.activity("Terminating EC2 instance and deleting temp security group and volume")
            self.terminate_instance(self.instance)
            key_file_object.close()
            conn.delete_key_pair(key_name)

            self.log.debug("Waiting up to 240 seconds for instance (%s) to shut down" % (self.instance.id))
            retcode = 1
            for i in range(24):
                self.instance.update()
                if self.instance.state == "terminated":
                    retcode = 0
                    break
                self.log.debug("Instance status (%s) - waiting for 'terminated': %d/240" % (self.instance.state, i*10))
                sleep(10)
            if retcode:
                self.log.warning("Instance (%s) failed to terminate - Unable to delete volume (%s) or delete factory temp security group" % (self.instance.id, volume.id))
            else:
                self.log.debug("Deleting temporary security group")
                factory_security_group.delete()
                if volume:
                    self.log.debug("Deleting EBS volume (%s)" % (volume.id))
                    volume.delete()

        # TODO: Add back-reference to ICICLE from base image object
        # This replaces our warehouse calls
        self.builder.provider_image.identifier_on_provider=ami_id
        self.builder.provider_image.provider_account_identifier=self.ec2_access_key
        self.percent_complete=100

    def ec2_push_image_upload(self, target_image_id, provider, credentials):
        def replace(item):
            if item in [self.ec2_access_key, self.ec2_secret_key]:
                return "REDACTED"
            return item

        # Image is always here and it is the target_image datafile
        input_image = self.builder.target_image.data
        input_image_name = os.path.basename(input_image)

        self.ec2_decode_credentials(credentials)

        bundle_destination=self.app_config['imgdir']


        self.activity("Preparing EC2 region details and connection")
        region=provider
        region_conf = self._decode_region_details(region)
        aki = region_conf[self.tdlobj.arch]
        boto_loc = region_conf['boto_loc']
        if region_conf['host'] != "us-east-1":
            upload_url = "http://s3-%s.amazonaws.com/" % (region_conf['host'])
        else:
            # Note to Amazon - would it be that hard to have s3-us-east-1.amazonaws.com?
            upload_url = "http://s3.amazonaws.com/"

        register_url = "http://ec2.%s.amazonaws.com/" % (region_conf['host'])

        bucket= "imagefactory-" + region + "-" + self.ec2_user_id

        # Euca does not support specifying region for bucket
        # (Region URL is not sufficient)
        # See: https://bugs.launchpad.net/euca2ools/+bug/704658
        # What we end up having to do is manually create a bucket in the right region
        # then explicitly point to that region URL when doing the image upload
        # We CANNOT let euca create the bucket when uploading or it will end up in us-east-1

        conn = S3Connection(self.ec2_access_key, self.ec2_secret_key)
        try:
            conn.create_bucket(bucket, location=boto_loc)
        except S3CreateError as buckerr:
            # if the bucket already exists, it is not an error
            if buckerr.error_code != "BucketAlreadyOwnedByYou":
                raise

        # TODO: Make configurable?
        ec2_service_cert = "/etc/pki/imagefactory/cert-ec2.pem"

        bundle_command = [ "euca-bundle-image", "-i", input_image,
                           "--kernel", aki, "-d", bundle_destination,
                           "-a", self.ec2_access_key, "-s", self.ec2_secret_key,
                           "-c", self.ec2_cert_file, "-k", self.ec2_key_file,
                           "-u", self.ec2_user_id, "-r", self.tdlobj.arch,
                           "--ec2cert", ec2_service_cert ]

        bundle_command_log = map(replace, bundle_command)

        self.activity("Bundling image locally")
        self.log.debug("Executing bundle command: %s " % (bundle_command_log))

        bundle_output = subprocess_check_output(bundle_command)

        self.log.debug("Bundle command complete")
        self.log.debug("Bundle command output: %s " % (str(bundle_output)))
        self.percent_complete=40

        manifest = bundle_destination + "/" + input_image_name + ".manifest.xml"

        upload_command = [ "euca-upload-bundle", "-b", bucket, "-m", manifest,
                           "--ec2cert", ec2_service_cert,
                           "-a", self.ec2_access_key, "-s", self.ec2_secret_key,
                           "-U" , upload_url ]

        upload_command_log = map(replace, upload_command)

        self.activity("Uploading image to EC2")
        self.log.debug("Executing upload command: %s " % (upload_command_log))
        upload_output = subprocess_check_output(upload_command)
        self.log.debug("Upload command output: %s " % (str(upload_output)))
        self.percent_complete=90

        s3_path = bucket + "/" + input_image_name + ".manifest.xml"

        register_env = { 'EC2_URL':register_url }
        register_command = [ "euca-register" , "-A", self.ec2_access_key,
                             "-S", self.ec2_secret_key, "-a", self.tdlobj.arch, s3_path ]
        register_command_log = map(replace, register_command)
        self.activity("Registering image")
        self.log.debug("Executing register command: %s with environment %s " % (register_command_log, repr(register_env)))
        register_output = subprocess_check_output(register_command, env=register_env)
        self.log.debug("Register command output: %s " % (str(register_output)))
        m = re.match(".*(ami-[a-fA-F0-9]+)", register_output[0])
        ami_id = m.group(1)
        self.log.debug("Extracted AMI ID: %s " % (ami_id))

        # TODO: This should be in a finally statement that rethrows exceptions
        self.ec2_cert_file_object.close()
        self.ec2_key_file_object.close()

        self.status = "PUSHING"

        # TODO: Generate and store ICICLE
        # This replaces our warehouse calls
        self.builder.provider_image.identifier_on_provider = ami_id
        self.builder.provider_image.provider_account_identifier = self.ec2_access_key

        self.log.debug("Fedora_ec2_Builder instance %s pushed image with uuid %s to provider_image UUID (%s)" % (id(self), target_image_id, self.new_image_id))
        self.percent_complete=100

    def abort(self):
        # TODO: Make this progressively more robust

        # In the near term, the most important thing we can do is terminate any EC2 instance we may be using
        if self.instance:
            instance_id = self.instance.id
            try:
                self.terminate_instance(self.instance)
            except Exception, e:
                self.log.warning("Warning, encountered - Instance %s may not be terminated ******** " % (instance_id))
                self.log.exception(e)

    # This file content is tightly bound up with our mod code above
    # I've inserted it as class variables for convenience
    rc_local="""# We have seen timing issues with curl commands - try several times
for t in 1 2 3 4 5 6 7 8 9 10; do
  echo "Try number $t" >> /tmp/ec2-keypull.stderr
  curl -o /tmp/my-key http://169.254.169.254/2009-04-04/meta-data/public-keys/0/openssh-key 2>> /tmp/ec2-keypull.stderr
  [ -f /tmp/my-key ] && break
  sleep 10
done

if ! [ -f /tmp/my-key ]; then
  echo "Failed to retrieve SSH key after 10 tries and 100 seconds" > /dev/hvc0
  exit 1
fi

dd if=/dev/urandom count=50 2>/dev/null|md5sum|awk '{ print $1 }'|passwd --stdin root >/dev/null

if [ ! -d /root/.ssh ] ; then
mkdir /root/.ssh
chmod 700 /root/.ssh
fi

cat /tmp/my-key >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

for home in `find /home/* -maxdepth 0 -type d 2>/dev/null | tr '\\n' ' '`; do
user=`echo $home | awk -F '/' '{ print $3 }'`

if [ ! -d $home/.ssh ] ; then
mkdir -p $home/.ssh
chmod 700 $home/.ssh
chown $user $home/.ssh
fi

cat /tmp/my-key >> $home/.ssh/authorized_keys
chmod 600 $home/.ssh/authorized_keys
chown $user $home/.ssh/authorized_keys

done
rm /tmp/my-key
"""

    ifcfg_eth0="""DEVICE=eth0
BOOTPROTO=dhcp
ONBOOT=yes
TYPE=Ethernet
USERCTL=yes
PEERDNS=yes
IPV6INIT=no
"""

    menu_lst="""default=0
timeout=0
title #TITLE#
    root (hd0)
    kernel /boot/vmlinuz-#KERNEL_VERSION# ro root=LABEL=/ rd_NO_PLYMOUTH #KERNEL_OPTIONS#
    initrd /boot/#KERNEL_IMAGE_NAME#-#KERNEL_VERSION#.img
"""

    fstab_32bit="""LABEL=/    /         ext3    defaults         1 1
/dev/xvda2  /mnt      ext3    defaults,nofail         1 2
/dev/xvda3  swap      swap    defaults,nofail         0 0
none       /dev/pts  devpts  gid=5,mode=620   0 0
none       /dev/shm  tmpfs   defaults         0 0
none       /proc     proc    defaults         0 0
none       /sys      sysfs   defaults         0 0
"""

    fstab_64bit="""LABEL=/    /         ext3    defaults         1 1
/dev/xvdb   /mnt      ext3    defaults,nofail         0 0
/dev/xvdc   /data     ext3    defaults,nofail         0 0
none       /dev/pts  devpts  gid=5,mode=620   0 0
none       /dev/shm  tmpfs   defaults         0 0
none       /proc     proc    defaults         0 0
none       /sys      sysfs   defaults         0 0
"""

    ############ BEGIN CONFIG-LIKE class variables ###########################
    ##########################################################################
    # Perhaps there is a better way to do this but this works for now

    # TODO: Ideally we should use boto "Location" references when possible - 1.9 contains only DEFAULT and EU
    #       The rest are hard coded strings for now.

    def _decode_region_details(self, region):
        """Accept as input either the original ec2-* strings or a JSON string containing the same
        details.
        If the JSON contains a 'name' field attempt to match it to known details.  Allow any other
        fields in the JSON to override. """

        # This whole thing is a bit of a mess but it preserves backwards compat but also allows for
        # ad-hoc addition of new regions without code changes
        # TODO: Move EC2 builtin details to a config file
        region_details = None

        # If it is JSON, decode it
        try:
            region_details = json.loads(region)
        except:
            pass

        # If decoded JSON has a name field, use it for the follow on lookups
        if region_details and 'name' in region_details:
            region = region_details['name']

        if region in self.ec2_region_details:
            bi_region_details = self.ec2_region_details[region]
        elif ("ec2-" + region) in self.ec2_region_details:
            bi_region_details = self.ec2_region_details["ec2-" + region]
        else:
            bi_region_details = None

        if (not region_details) and (not bi_region_details):
            # We couldn't decode any json and the string we were passed is not a builtin region - give up
            raise ImageFactoryException("Passed unknown EC2 region (%s)" % region)

        if not region_details:
            region_details = { }

        # Allow the builtin details to fill in anything that is missing
        if bi_region_details:
            for bi_key in bi_region_details:
                if not (bi_key in region_details):
                    region_details[bi_key] = bi_region_details[bi_key]

        return region_details


    ec2_region_details={
         'ec2-us-east-1':      { 'boto_loc': Location.DEFAULT,     'host':'us-east-1',      'i386': 'aki-805ea7e9', 'x86_64': 'aki-825ea7eb' },
         'ec2-us-west-1':      { 'boto_loc': 'us-west-1',          'host':'us-west-1',      'i386': 'aki-83396bc6', 'x86_64': 'aki-8d396bc8' },
         'ec2-us-west-2':      { 'boto_loc': 'us-west-2',          'host':'us-west-2',      'i386': 'aki-c2e26ff2', 'x86_64': 'aki-98e26fa8' },
         'ec2-ap-southeast-1': { 'boto_loc': 'ap-southeast-1',     'host':'ap-southeast-1', 'i386': 'aki-a4225af6', 'x86_64': 'aki-aa225af8' },
         'ec2-ap-northeast-1': { 'boto_loc': 'ap-northeast-1',     'host':'ap-northeast-1', 'i386': 'aki-ec5df7ed', 'x86_64': 'aki-ee5df7ef' },
         'ec2-sa-east-1':      { 'boto_loc': 'sa-east-1',          'host':'sa-east-1',      'i386': 'aki-bc3ce3a1', 'x86_64': 'aki-cc3ce3d1' },
         'ec2-eu-west-1':      { 'boto_loc': Location.EU,          'host':'eu-west-1',      'i386': 'aki-64695810', 'x86_64': 'aki-62695816' } }

        # July 13 - new approach - generic JEOS AMIs for Fedora - no userdata and no euca-tools
        #           ad-hoc ssh keys replace userdata - runtime install of euca tools for bundling
        # v0.6 of F14 and F15 - dropped F13 for now - also include official public RHEL hourly AMIs for RHEL6
        # Sept 1 - 2011 - updated us-west Fedora JEOSes to 0.6
        # Sept 30 - 2011 - Moved out of here entirely to ApplicationConfiguration
        # ec2_jeos_amis = <not here anymore>

    def add_target_content(self):
        """Merge in target specific package and repo content.
        TDL object must already exist as self.tdlobj"""
        doc = None
# TODONOW: Fix
#        if self.config_block:
        import os.path
        if None:
            doc = libxml2.parseDoc(self.config_block)
        elif os.path.isfile("/etc/imagefactory/target_content.xml"):
            doc = libxml2.parseFile("/etc/imagefactory/target_content.xml")
        else:
            self.log.debug("Found neither a call-time config nor a config file - doing nothing")
            return

        # Purely to make the xpath statements below a tiny bit shorter
        target = self.target
        os=self.tdlobj.distro
        version=self.tdlobj.update
        arch=self.tdlobj.arch

        # We go from most to least specific in this order:
        #   arch -> version -> os-> target
        # Note that at the moment we even allow an include statment that covers absolutely everything.
        # That is, one that doesn't even specify a target - this is to support a very simple call-time syntax
        include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and @version='%s' and @arch='%s']" %
                                (target, os, version, arch))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and @version='%s' and not(@arch)]" %
                                    (target, os, version))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and not(@version) and not(@arch)]" %
                                        (target, os))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and not(@os) and not(@version) and not(@arch)]" %
                                            (target))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[not(@target) and not(@os) and not(@version) and not(@arch)]")
        if len(include) == 0:
            self.log.debug("cannot find a config section that matches our build details - doing nothing")
            return

        # OK - We have at least one config block that matches our build - take the first one, merge it and be done
        # TODO: Merge all of them?  Err out if there is more than one?  Warn?
        include = include[0]

        packages = include.xpathEval("packages")
        if len(packages) > 0:
            self.tdlobj.merge_packages(str(packages[0]))

        repositories = include.xpathEval("repositories")
        if len(repositories) > 0:
            self.tdlobj.merge_repositories(str(repositories[0]))


########NEW FILE########
__FILENAME__ = EC2CloudOSHelpers
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
from imgfac.ImageFactoryException import ImageFactoryException
import oz.RHEL_5
import oz.RHEL_6
import oz.Fedora


class Base_ec2_Helper(object):

    def __init__(self, plugin):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.plugin = plugin
        self.guest = None

    def init_guest(self):
        raise ImageFactoryException("init_guest() not implemented in this helper")

    def ebs_pre_snapshot_tasks(self, guestaddr):
        if(self.guest):
            self.log.debug("Removing /root/.ssh/authorized_keys file...")
            self.guest.guest_execute_command(guestaddr, "[ -f /root/.ssh/authorized_keys ] && rm -f /root/.ssh/authorized_keys")

    def correct_remote_manifest(self, guestaddr, manifest):
        pass

    def install_euca_tools(self, guestaddr):
        pass

    def _init_guest_common(self):
        self.guest.diskimage = self.plugin.app_config["imgdir"] + "/base-image-" + self.plugin.new_image_id + ".dsk"
        # Oz assumes unique names - TDL built for multiple backends guarantees they are not unique
        # We don't really care about the name so just force uniqueness
        self.guest.name = self.guest.name + "-" + self.plugin.new_image_id
        # Allow both us and the plugin to reference self.guest
        self.plugin.guest = self.guest



class RHEL5_ec2_Helper(Base_ec2_Helper):

    class RHEL5RemoteGuest(oz.RHEL_5.RHEL5Guest):
        def __init__(self, tdl, config, auto):
            # The debug output in the Guest parent class needs this property to exist
            self.host_bridge_ip = "0.0.0.0"
            # Add virtio as dummy arguments below - doesn't actually matter what we put
            oz.RHEL_5.RHEL5Guest.__init__(self, tdl, config, auto, "virtio",
                                          "virtio")

        def connect_to_libvirt(self):
            pass

        def guest_execute_command(self, guestaddr, command, timeout=30,
                                  tunnels=None):
            return super(RHEL5_ec2_Helper.RHEL5RemoteGuest, self).guest_execute_command(guestaddr, command, timeout, tunnels)

        def guest_live_upload(self, guestaddr, file_to_upload, destination,
                              timeout=30):
            return super(RHEL5_ec2_Helper.RHEL5RemoteGuest, self).guest_live_upload(guestaddr, file_to_upload, destination, timeout)

    def init_guest(self):
        self.guest = self.RHEL5RemoteGuest(self.plugin.tdlobj, self.plugin.oz_config, None)
        self._init_guest_common()

    def correct_remote_manifest(self, guestaddr, manifest):
        # We end up with a bogus block device mapping due to our EBS to S3 switch
        # cannot get euca-bundle-vol in RHEL5 EPEL to correct this so fix it manually - sigh
        # Remove entirely - we end up with the default root map to sda1 which is acceptable
        # TODO: Switch to a euca version that can produce sensible maps
        self.log.debug("Removing bogus block device mapping from remote manifest")
        self.guest.guest_execute_command(guestaddr, 'perl -p -i -e "s/<block_device_mapping\>.*<\/block_device_mapping>//" %s' % (manifest))

    def install_euca_tools(self, guestaddr):
        # For RHEL5 S3 snapshots we need to enable EPEL, install, then disable EPEL
        # TODO: This depends on external infra which is bad, and trusts external SW, which may be bad
        # For now we also mount up /mnt
        self.guest.guest_execute_command(guestaddr, "mount /dev/sdf /mnt")
        self.guest.guest_execute_command(guestaddr, "rpm -ivh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm")
        self.guest.guest_execute_command(guestaddr, "yum -y install euca2ools")
        self.guest.guest_execute_command(guestaddr, "rpm -e epel-release")



class RHEL6_ec2_Helper(Base_ec2_Helper):

    class RHEL6RemoteGuest(oz.RHEL_6.RHEL6Guest):
        def __init__(self, tdl, config, auto):
            # The debug output in the Guest parent class needs this property to exist
            self.host_bridge_ip = "0.0.0.0"
            oz.RHEL_6.RHEL6Guest.__init__(self, tdl, config, auto)

        def connect_to_libvirt(self):
            pass

        def guest_execute_command(self, guestaddr, command, timeout=30,
                                  tunnels=None):
            return super(RHEL6_ec2_Helper.RHEL6RemoteGuest, self).guest_execute_command(guestaddr, command, timeout, tunnels)

        def guest_live_upload(self, guestaddr, file_to_upload, destination,
                              timeout=30):
            return super(RHEL6_ec2_Helper.RHEL6RemoteGuest, self).guest_live_upload(guestaddr, file_to_upload, destination, timeout)

    def init_guest(self):
        self.guest = self.RHEL6RemoteGuest(self.plugin.tdlobj, self.plugin.oz_config, None)
        self._init_guest_common()

    def install_euca_tools(self, guestaddr):
        # For RHEL6 we need to enable EPEL, install, then disable EPEL
        # TODO: This depends on external infra which is bad, and trusts external SW, which may be bad
        # For now we also mount up /mnt
        self.guest.guest_execute_command(guestaddr, "mount /dev/xvdj /mnt")
        self.guest.guest_execute_command(guestaddr, "rpm -ivh http://download.fedora.redhat.com/pub/epel/6/i386/epel-release-6-5.noarch.rpm")
        self.guest.guest_execute_command(guestaddr, "yum -y install euca2ools")
        self.guest.guest_execute_command(guestaddr, "rpm -e epel-release")



class Fedora_ec2_Helper(Base_ec2_Helper):

    class FedoraRemoteGuest(oz.Fedora.FedoraGuest):
        def __init__(self, tdl, config, auto, nicmodel, haverepo, diskbus,
                     brokenisomethod):
            # The debug output in the Guest parent class needs this property to exist
            self.host_bridge_ip = "0.0.0.0"
            oz.Fedora.FedoraGuest.__init__(self, tdl, config, auto, nicmodel, haverepo, diskbus,
                     brokenisomethod)

        def connect_to_libvirt(self):
            pass

        def guest_execute_command(self, guestaddr, command, timeout=30,
                                  tunnels=None):
            return super(Fedora_ec2_Helper.FedoraRemoteGuest, self).guest_execute_command(guestaddr, command, timeout, tunnels)

        def guest_live_upload(self, guestaddr, file_to_upload, destination,
                              timeout=30):
            return super(Fedora_ec2_Helper.FedoraRemoteGuest, self).guest_live_upload(guestaddr, file_to_upload, destination, timeout)

    def init_guest(self):
        self.guest = self.FedoraRemoteGuest(self.plugin.tdlobj, self.plugin.oz_config, None,
                                           "virtio", True, "virtio", True)
        self._init_guest_common()

    def install_euca_tools(self, guestaddr):
        # For F13-F15 we now have a working euca2ools in the default repos
        self.guest.guest_execute_command(guestaddr, "yum -y install euca2ools")

########NEW FILE########
__FILENAME__ = make_parameters
#!/usr/bin/python
# This just wraps the kickstart file provided on the command line into JSON
# that can be passed to the factory via REST or the command line
# This is important since ks files typically have characters that may need
# to be escaped - even newlines need this

import sys
import json

kickstart = open(sys.argv[1]).read()

parameters =  { "install_script": kickstart, "generate_icicle": False }

print json.dumps(parameters)

########NEW FILE########
__FILENAME__ = make_target_parameters
#!/usr/bin/python

import sys
import json


utility_tdl = open(sys.argv[1]).read()
utility_image = sys.argv[2]

parameters =  { "utility_image": utility_image, "utility_customizations": utility_tdl }

print json.dumps(parameters)

########NEW FILE########
__FILENAME__ = IndirectionCloud
#!/usr/bin/python
#
#   Copyright 2012 Red Hat, Inc.
#   Portions Copyright (C) 2012,2013  Chris Lalancette <clalancette@gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import oz.TDL
import oz.GuestFactory
import oz.ozutil
import guestfs
# TODO: We've had to migrate to lxml here because of Oz changes
#       see if we can't move the libvirt stuff as well
# For now we import both
import libxml2
import lxml
import ConfigParser
import tempfile
import base64
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.CloudDelegate import CloudDelegate
from imgfac.PersistentImageManager import PersistentImageManager
from imgfac.ReservationManager import ReservationManager

# This makes extensive use of parameters with some sensible defaults
# Try to keep an accurate list up here

# Parameter     -  Default - 
# Description

# utility_image - <base_image_id>
# Description: UUID of the image that will be launched to do the modification of the 
#              the base_image referenced in this target_image build.  Note that the 
#              utility image should itself be a base image and can, if constructed properly,
#              be the same as the base image that is being modified.  The plugin makes a copy
#              of the utility image before launching it, which allows safe modification during 
#              the target_image creation process.


# input_image_file - /input_image.raw (but only if input_image_device is not specified)
# Description: The name of the file on the working space disk where the base_image is presented

# input_image_device - None
# Description: The name of the device where the base_image is presented to the utility VM.
#              (e.g. vdc)

# NOTE: You can specify one or the other of these options but not both.  If neither are specified
#       you will end up with the default value for input_image_file.

# utility_cpus - None
# Description: Number of CPUs in the utility VM - this can also be set in the global Oz config
#              The lmc Live CD creation process benefits greatly from extra CPUs during the squashfs
#              creation step.  The performance improvement is almost perfectly O(n) w.r.t CPU.

# utility_customizations - None
# Description: A partial TDL document to drive the actions of the utility VM - only repos, packages,
#              files and commands will be used - all other content is ignored

# results_location - /results/images/boot.iso

# Description: Location inside of the working space image from which to extract the results.

# Borrowed from Oz by Chris Lalancette
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


class IndirectionCloud(object):
    zope.interface.implements(CloudDelegate)

    def __init__(self):
        super(IndirectionCloud, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.pim = PersistentImageManager.default_manager()
        self.res_mgr = ReservationManager()

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        # This plugin wants to be the only thing operating on the input image
        # We do all our work here and then return False which stops any additional activity

        # User may specify a utility image - if they do not we assume we can use the input image
        utility_image_id = parameters.get('utility_image', image_id)

        # The utility image is what we actually re-animate with Oz
        # We borrow these variable names from code that is very similar to the Oz/TinMan OS plugin
        self.active_image = self.pim.image_with_id(utility_image_id)
        if not self.active_image:
            raise Exception("Could not find utility image with ID (%s)" % (utility_image_id) )
        self.tdlobj = oz.TDL.TDL(xmlstring=self.active_image.template)

        # Later on, we will either copy in the base_image content as a file, or expose it as a device
        # to the utility VM.  We cannot do both.  Detect invalid input here before doing any long running
        # work
        input_image_device = parameters.get('input_image_device', None)
        input_image_file = parameters.get('input_image_filename', None)

        if input_image_device and input_image_file:
            raise Exception("You can specify either an input_image_device or an input_image_file but not both")

        if (not input_image_device) and (not input_image_file):
            input_image_file="/input_image.raw"


        # We remove any packages, commands and files from the original TDL - these have already been
        # installed/executed.  We leave the repos in place, as it is possible that commands executed
        # later may depend on them
        self.tdlobj.packages = [ ]
        self.tdlobj.commands = { }
        self.tdlobj.files = { } 

        # This creates a new Oz object - replaces the auto-generated disk file location with
        # the copy of the utility image made above, and prepares an initial libvirt_xml string
        self._init_oz()
        utility_image_tmp = self.app_config['imgdir'] + "/tmp-utility-image-" + str(builder.target_image.identifier)
        self.guest.diskimage = utility_image_tmp
        if 'utility_cpus' in parameters:
            self.guest.install_cpus = int(parameters['utility_cpus'])

        libvirt_xml = self.guest._generate_xml("hd", None)
        libvirt_doc = libxml2.parseDoc(libvirt_xml)

        # Now we create a second disk image as working/scratch space
        # Hardcode at 30G
        # TODO: Make configurable
        # Make it, format it, copy in the base_image 
        working_space_image = self.app_config['imgdir'] + "/working-space-image-" + str(builder.target_image.identifier)
        self.create_ext2_image(working_space_image)

        # Modify the libvirt_xml used with Oz to contain a reference to a second "working space" disk image
        working_space_device = parameters.get('working_space_device', 'vdb')
        self.add_disk(libvirt_doc, working_space_image, working_space_device)

        self.log.debug("Updated domain XML with working space image:\n%s" % (libvirt_xml))

        # We expect to find a partial TDL document in this parameter - this is what drives the
        # tasks performed by the utility image
        if 'utility_customizations' in parameters:
            self.oz_refresh_customizations(parameters['utility_customizations'])
        else:
            self.log.info('No additional repos, packages, files or commands specified for utility tasks')

        # Make a copy of the utlity image - this will be modified and then discarded
        self.log.debug("Creating temporary working copy of utlity image (%s) as (%s)" % (self.active_image.data, utility_image_tmp))
        oz.ozutil.copyfile_sparse(self.active_image.data, utility_image_tmp)

        if input_image_file: 
            # Here we finally involve the actual Base Image content - it is made available for the utlity image to modify
            self.copy_content_to_image(builder.base_image.data, working_space_image, input_image_file)
        else:
            # Note that we know that one or the other of these are set because of code earlier
            self.add_disk(libvirt_doc, builder.base_image.data, input_image_device)

        # Run all commands, repo injection, etc specified
        try:
            self.log.debug("Launching utility image and running any customizations specified")
            libvirt_xml = libvirt_doc.serialize(None, 1)
            self.guest.customize(libvirt_xml)
            self.log.debug("Utility image tasks complete")
        finally:
            self.log.debug("Cleaning up install artifacts")
            self.guest.cleanup_install()

        # After shutdown, extract the results
        results_location = parameters.get('results_location', "/results/images/boot.iso")
        self.copy_content_from_image(results_location, working_space_image, builder.target_image.data)

        # TODO: Remove working_space image and utility_image_tmp
        return False


    def add_disk(self, libvirt_doc, disk_image_file, device_name):
	devices = libvirt_doc.xpathEval("/domain/devices")[0]
	new_dev = devices.newChild(None, "disk", None)
	new_dev.setProp("type", "file")
	new_dev.setProp("device", "disk")
	source = new_dev.newChild(None, "source", None)
	source.setProp("file", disk_image_file)
	target = new_dev.newChild(None, "target", None)
	target.setProp("dev", device_name)
	target.setProp("bus", self.guest.disk_bus)


    def oz_refresh_customizations(self, partial_tdl):
        # This takes our already created and well formed TDL object with already blank customizations
        # and attempts to add in any additional customizations found in partial_tdl
        # partial_tdl need not contain the <os>, <name> or <description> sections
        # if it does they will be ignored
        # TODO: Submit an Oz patch to make this shorter or a utility function within the TDL class

        doc = lxml.etree.fromstring(partial_tdl)
        self.tdlobj.doc = doc 

        packageslist = doc.xpath('/template/packages/package')
        self.tdlobj._add_packages(packageslist)

        for afile in doc.xpath('/template/files/file'):
            name = afile.get('name')
            if name is None:
                raise Exception("File without a name was given")
            contenttype = afile.get('type')
            if contenttype is None:
                contenttype = 'raw'

            content = afile.text
            if content:
                content = content.strip()
            else:
                content = ''
            self.tdlobj.files[name] = data_from_type(name, contenttype, content)

        repositorieslist = doc.xpath('/template/repositories/repository')
        self.tdlobj._add_repositories(repositorieslist)

        self.tdlobj.commands = self.tdlobj._parse_commands()


    def _init_oz(self):
        # populate a config object to pass to OZ; this allows us to specify our
        # own output dir but inherit other Oz behavior
        self.oz_config = ConfigParser.SafeConfigParser()
        if self.oz_config.read("/etc/oz/oz.cfg") != []:
            self.oz_config.set('paths', 'output_dir', self.app_config["imgdir"])
            if "oz_data_dir" in self.app_config:
                self.oz_config.set('paths', 'data_dir', self.app_config["oz_data_dir"])
            if "oz_screenshot_dir" in self.app_config:
                self.oz_config.set('paths', 'screenshot_dir', self.app_config["oz_screenshot_dir"])
        else:
            raise ImageFactoryException("No Oz config file found. Can't continue.")

        # Use the factory function from Oz directly
        try:
            # Force uniqueness by overriding the name in the TDL
            self.tdlobj.name = "factory-build-" + self.active_image.identifier
            self.guest = oz.GuestFactory.guest_factory(self.tdlobj, self.oz_config, None)
            # Oz just selects a random port here - This could potentially collide if we are unlucky
            self.guest.listen_port = self.res_mgr.get_next_listen_port()
        except libvirtError, e:
            raise ImageFactoryException("Cannot connect to libvirt.  Make sure libvirt is running. [Original message: %s]" %  e.message)
        except OzException, e:
            if "Unsupported" in e.message:
                raise ImageFactoryException("TinMan plugin does not support distro (%s) update (%s) in TDL" % (self.tdlobj.distro, self.tdlobj.update) )
            else:
                raise e


    def create_ext2_image(self, image_file, image_size=(1024*1024*1024*30)):
        # Why ext2?  Why not?  There's no need for the overhead of journaling.  This disk will be mounted once and thrown away.
        self.log.debug("Creating disk image of size (%d) in file (%s) with single partition containint ext2 filesystem" % (image_size, image_file))
        raw_fs_image=open(image_file,"w")
        raw_fs_image.truncate(image_size)
        raw_fs_image.close()
        g = guestfs.GuestFS()
        g.add_drive(image_file)
        g.launch()
        g.part_disk("/dev/sda","msdos")
        g.part_set_mbr_id("/dev/sda",1,0x83)
        g.mkfs("ext2", "/dev/sda1")
        g.sync()

    def copy_content_to_image(self, filename, target_image, target_filename):
        self.log.debug("Copying file (%s) into disk image (%s)" % (filename, target_image))
        g = guestfs.GuestFS()
        g.add_drive(target_image)
        g.launch()
        g.mount_options ("", "/dev/sda1", "/")
        g.upload(filename, target_filename)
        g.sync()

    def copy_content_from_image(self, filename, target_image, destination_file):
        self.log.debug("Copying file (%s) out of disk image (%s) into (%s)" % (filename, target_image, destination_file))
        g = guestfs.GuestFS()
        g.add_drive(target_image)
        g.launch()
        g.mount_options ("", "/dev/sda1", "/")
        g.download(filename,destination_file)
        g.sync()


########NEW FILE########
__FILENAME__ = MockCloud
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import uuid
import zope
import inspect
from imgfac.CloudDelegate import CloudDelegate

class MockCloud(object):
    zope.interface.implements(CloudDelegate)


    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))
        builder.provider_image.identifier_on_provider = str(uuid.uuid4())
        builder.provider_image.provider_account_identifier = 'mock_user'

    def snapshot_image_on_provider(self, builder, provider, credentials, target, template, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))
        builder.provider_image.identifier_on_provider = str(uuid.uuid4())
        builder.provider_image.provider_account_identifier = 'mock_user'

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))
        return True

    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))

    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))

    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        self.log.info('%s called in MockCloud plugin' % (inspect.stack()[1][3]))

########NEW FILE########
__FILENAME__ = MockOS
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
from imgfac.OSDelegate import OSDelegate
from imgfac.BaseImage import BaseImage
from imgfac.TargetImage import TargetImage

class MockOS(object):
    zope.interface.implements(OSDelegate)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def create_base_image(self, builder, template, parameters):
        self.log.info('create_base_image() called in MockOS')
        mock_image_file = open(builder.base_image.data, "w")
        mock_image_file.write("MockOS base_image file for id (%s)" % builder.base_image.identifier)
        mock_image_file.close()
        #return BaseImage(template)

    def create_target_image(self, builder, target, base_image, parameters):
        self.log.info('create_target_image() called in MockOS')
        mock_image_file = open(builder.target_image.data, "w")
        mock_image_file.write("MockOS target_image file for id (%s)" % builder.target_image.identifier)
        mock_image_file.close()
        #return TargetImage(base_image, target, parameters)

########NEW FILE########
__FILENAME__ = Nova
# encoding: utf-8
#
#   Copyright 2014 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import os.path
import shutil
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.OSDelegate import OSDelegate
from imgfac.ImageFactoryException import ImageFactoryException
from novaimagebuilder.Builder import Builder as NIB
from novaimagebuilder.StackEnvironment import StackEnvironment

PROPERTY_NAME_GLANCE_ID = 'x-image-properties-glance_id'


class Nova(object):
    """
    Nova implements the ImageFactory OSDelegate interface for the Nova plugin.
    """
    zope.interface.implements(OSDelegate)

    def __init__(self):
        super(Nova, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.nib = None
        self._cloud_plugin_content = []

    def abort(self):
        """
        Abort the current operation.
        """
        if self.nib and isinstance(self.nib, NIB):
            status = self.nib.abort()
            self.log.debug('aborting... status: %s' % status)
        else:
            self.log.debug('No active Nova Image Builder instance found, nothing to abort.')

    def create_base_image(self, builder, template, parameters):
        """
        Create a JEOS image and install any packages specified in the template.

        @param builder The Builder object coordinating image creation.
        @param template A Template object.
        @param parameters Dictionary of target specific parameters.

        @return A BaseImage object.
        """
        self.log.info('create_base_image() called for Nova plugin - creating a BaseImage')

        self.log.debug('Nova.create_base_image() called by builder (%s)' % builder)
        if not parameters:
            parameters = {}
        self.log.debug('parameters set to %s' % parameters)

        builder.base_image.update(5, 'PENDING', 'Collecting build arguments to pass to Nova Image Builder...')
        # Derive the OSInfo OS short_id from the os_name and os_version in template
        if template.os_version:
            if template.os_name[-1].isdigit():
                install_os = '%s.%s' % (template.os_name, template.os_version)
            else:
                install_os = '%s%s' % (template.os_name, template.os_version)
        else:
            install_os = template.os_name

        install_os = install_os.lower()

        install_location = template.install_location
        # TDL uses 'url' but Nova Image Builder uses 'tree'
        install_type = 'tree' if template.install_type == 'url' else template.install_type
        install_script = parameters.get('install_script')
        install_config = {'admin_password': parameters.get('admin_password'),
                          'license_key': parameters.get('license_key'),
                          'arch': template.os_arch,
                          'disk_size': parameters.get('disk_size'),
                          'flavor': parameters.get('flavor'),
                          'storage': parameters.get('storage'),
                          'name': template.name,
                          'direct_boot': False}

        builder.base_image.update(10, 'BUILDING', 'Created Nova Image Builder instance...')
        self.nib = NIB(install_os, install_location, install_type, install_script, install_config)
        self.nib.run()

        builder.base_image.update(10, 'BUILDING', 'Waiting for Nova Image Builder to complete...')
        os_image_id = self.nib.wait_for_completion(180)
        if os_image_id:
            builder.base_image.properties[PROPERTY_NAME_GLANCE_ID] = os_image_id
            builder.base_image.update(100, 'COMPLETE', 'Image stored in glance with id (%s)' % os_image_id)
        else:
            exc_msg = 'Nova Image Builder failed to return a Glance ID, failing...'
            builder.base_image.update(status='FAILED', error=exc_msg)
            self.log.exception(exc_msg)
            raise ImageFactoryException(exc_msg)

    def create_target_image(self, builder, target, base_image, parameters):
        """
        *** NOT YET IMPLEMENTED ***
        Performs cloud specific customization on the base image.

        @param builder The builder object.
        @param base_image The BaseImage to customize.
        @param target The cloud type to customize for.
        @param parameters Dictionary of target specific parameters.

        @return A TargetImage object.
        """
        self.log.info('create_target_image() currently unsupported for Nova plugin')

        ### TODO: Snapshot the image in glance, launch in nova, and ssh in to customize.
        # The following is incomplete and not correct as it assumes local manipulation of the image
        # self.log.info('create_target_image() called for Nova plugin - creating TargetImage')
        # base_img_path = base_image.data
        # target_img_path = builder.target_image.data
        #
        # builder.target_image.update(status='PENDING', detail='Copying base image...')
        # if os.path.exists(base_img_path) and os.path.getsize(base_img_path):
        #     try:
        #         shutil.copyfile(base_img_path, target_img_path)
        #     except IOError as e:
        #         builder.target_image.update(status='FAILED', error='Error copying base image: %s' % e)
        #         self.log.exception(e)
        #         raise e
        # else:
        #     glance_id = base_image.properties[PROPERTY_NAME_GLANCE_ID]
        #     base_img_file = StackEnvironment().download_image_from_glance(glance_id)
        #     with open(builder.target_image.data, 'wb') as target_img_file:
        #         shutil.copyfileobj(base_img_file, target_img_file)
        #     base_img_file.close()

    def add_cloud_plugin_content(self, content):
        """
        This is a method that cloud plugins can call to deposit content/commands to
        be run during the OS-specific first stage of the Target Image creation.

        There is no support for repos at the moment as these introduce external
        dependencies that we may not be able to resolve.

        @param content dict containing commands and file.
        """
        self._cloud_plugin_content.append(content)
########NEW FILE########
__FILENAME__ = glance_upload
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from glance import client as glance_client
from pprint import pprint

def glance_upload(image_filename, creds = {'auth_url': None, 'password': None, 'strategy': 'noauth', 'tenant': None, 'username': None},
                  host = "0.0.0.0", port = "9292", token = None):

    image_meta = {'container_format': 'bare',
     'disk_format': 'qcow2',
     'is_public': True,
     'min_disk': 0,
     'min_ram': 0,
     'name': 'Factory Test Image',
     'properties': {'distro': 'rhel'}}


    c = glance_client.Client(host=host, port=port,
                             auth_tok=token, creds=creds)

    image_data = open(image_filename, "r")

    image_meta = c.add_image(image_meta, image_data)

    image_data.close()

    return image_meta['id']


image_id = glance_upload("/root/base-image-f19e3f9b-5905-4b66-acb2-2e25395fdff7.qcow2")

print image_id


########NEW FILE########
__FILENAME__ = OpenStack
#!/usr/bin/python
#
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import libxml2
import json
import os
import struct
from xml.etree.ElementTree import fromstring
from imgfac.Template import Template
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.BuildDispatcher import BuildDispatcher
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.CloudDelegate import CloudDelegate
from imgfac.FactoryUtils import launch_inspect_and_mount, shutdown_and_close, remove_net_persist, create_cloud_info
from glance import client as glance_client

def glance_upload(image_filename, creds = {'auth_url': None, 'password': None, 'strategy': 'noauth', 'tenant': None, 'username': None},
                  host = "0.0.0.0", port = "9292", token = None, name = 'Factory Test Image', disk_format = 'raw'):

    image_meta = {'container_format': 'bare',
     'disk_format': disk_format,
     'is_public': True,
     'min_disk': 0,
     'min_ram': 0,
     'name': name,
     'properties': {'distro': 'rhel'}}


    c = glance_client.Client(host=host, port=port,
                             auth_tok=token, creds=creds)
    image_data = open(image_filename, "r")
    image_meta = c.add_image(image_meta, image_data)
    image_data.close()
    return image_meta['id']

class OpenStack(object):
    zope.interface.implements(CloudDelegate)

    def __init__(self):
        # Note that we are now missing ( template, target, config_block = None):
        super(OpenStack, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        # Our target_image is already a raw KVM image.  All we need to do is upload to glance
        self.builder = builder
        self.active_image = self.builder.provider_image
        self.openstack_decode_credentials(credentials)

        provider_data = self.get_dynamic_provider_data(provider)
        if provider_data is None:
            raise ImageFactoryException("OpenStack KVM instance not found in XML or JSON provided")

        # Image is always here and it is the target_image datafile
        input_image = self.builder.target_image.data

        # If the template species a name, use that, otherwise create a name
        # using provider_image.identifier.
        template = Template(self.builder.provider_image.template)
        if template.name:
            image_name = template.name
        else:
            image_name = 'ImageFactory created image - %s' % (self.builder.provider_image.identifier)

        if self.check_qcow_size(input_image):
            self.log.debug("Uploading image to glance, detected qcow format")
            disk_format='qcow2'
        else:
            self.log.debug("Uploading image to glance, assuming raw format")
            disk_format='raw'
        image_id = glance_upload(input_image, creds = self.credentials_dict, token = self.credentials_token,
                                 host=provider_data['glance-host'], port=provider_data['glance-port'],
                                 name=image_name, disk_format=disk_format)

        self.builder.provider_image.identifier_on_provider = image_id
        if 'username' in self.credentials_dict:
            self.builder.provider_image.provider_account_identifier = self.credentials_dict['username']
        self.percent_complete=100

    def openstack_decode_credentials(self, credentials):
        self.activity("Preparing OpenStack credentials")
        # TODO: Validate these - in particular, ensure that if some nodes are missing at least
        #       a minimal acceptable set of auth is present
        doc = libxml2.parseDoc(credentials)

        self.credentials_dict = { }
        for authprop in [ 'auth_url', 'password', 'strategy', 'tenant', 'username']:
            self.credentials_dict[authprop] = self._get_xml_node(doc, authprop)
        self.credentials_token = self._get_xml_node(doc, 'token')

    def _get_xml_node(self, doc, credtype):
        nodes = doc.xpathEval("//provider_credentials/openstack_credentials/%s" % (credtype))
        # OpenStack supports multiple auth schemes so not all nodes are required
        if len(nodes) < 1:
            return None

        return nodes[0].content

    def snapshot_image_on_provider(self, builder, provider, credentials, template, parameters):
        # TODO: Implement snapshot builds
        raise ImageFactoryException("Snapshot builds not currently supported on OpenStack KVM")

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        return True

    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        pass

    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.target=target
        self.builder=builder 
        self.modify_oz_filesystem()

        # OS plugin has already provided the initial file for us to work with
        # which we can currently assume is a raw image
        input_image = builder.target_image.data

        # Support conversion to alternate preferred image format
        # Currently only handle qcow2, but the size reduction of
        # using this avoids the performance penalty of uploading
        # (and launching) raw disk images on slow storage
        if self.app_config.get('openstack_image_format', 'raw') == 'qcow2':
            self.log.debug("Converting RAW image to compressed qcow2 format")
            rc = os.system("qemu-img convert -c -O qcow2 %s %s" %
                            (input_image, input_image + ".tmp.qcow2"))
            if rc == 0:
                os.unlink(input_image)
                os.rename(input_image + ".tmp.qcow2", input_image)
            else:
                raise ImageFactoryException("qemu-img convert failed!")

    def modify_oz_filesystem(self):
        self.log.debug("Doing further Factory specific modification of Oz image")
        guestfs_handle = launch_inspect_and_mount(self.builder.target_image.data)
        remove_net_persist(guestfs_handle)
        create_cloud_info(guestfs_handle, self.target)
        shutdown_and_close(guestfs_handle)

    def get_dynamic_provider_data(self, provider):
        try:
            xml_et = fromstring(provider)
            return xml_et.attrib
        except Exception as e:
            self.log.debug('Testing provider for XML: %s' % e)
            pass

        try:
            jload = json.loads(provider)
            return jload
        except ValueError as e:
            self.log.debug('Testing provider for JSON: %s' % e)
            pass

        return None

    # FIXME : cut/paste from RHEVMHelper.py, should refactor into a common utility class
    def check_qcow_size(self, filename):
        # Detect if an image is in qcow format
        # If it is, return the size of the underlying disk image
        # If it isn't, return None

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
        qcow_struct=">IIQIIQIIQQIIQ" # > means big-endian
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
__FILENAME__ = OVA
# encoding: utf-8

#   Copyright 2013 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import uuid
import zope
import inspect
from imgfac.CloudDelegate import CloudDelegate
from imgfac.PersistentImageManager import PersistentImageManager
from imgfac.TargetImage import TargetImage
from imagefactory_plugins.ovfcommon.ovfcommon import RHEVOVFPackage, VsphereOVFPackage
from imgfac.ImageFactoryException import ImageFactoryException
from oz.ozutil import copyfile_sparse

class OVA(object):
    zope.interface.implements(CloudDelegate)

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        retval = False

        if isinstance(builder.base_image, TargetImage):
            if builder.base_image.target in ('vsphere', 'rhevm'):
                retval = True

        self.log.info('builder_should_create_target_image() called on OVA plugin - returning %s' % retval)

        return retval

    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_did_create_target_image() called in OVA plugin')
        self.status="BUILDING"

        self.target_image = builder.base_image
        self.base_image = PersistentImageManager.default_manager().image_with_id(self.target_image.base_image_id)
        self.image = builder.target_image
        self.parameters = parameters

        # This lets our logging helper know what image is being operated on
        self.active_image = self.image

        self.generate_ova()

        self.percent_complete=100
        self.status="COMPLETED"

    def generate_ova(self):
        if self.target_image.target == 'rhevm':
            klass = RHEVOVFPackage
        elif self.target_image.target == 'vsphere':
            klass = VsphereOVFPackage
        else:
            raise ImageFactoryException("OVA plugin only support rhevm and vsphere images")

        klass_parameters = dict()

        if self.parameters:
            params = ['ovf_cpu_count','ovf_memory_mb',
                      'rhevm_default_display_type','rhevm_description','rhevm_os_descriptor',
                      'vsphere_product_name','vsphere_product_vendor_name','vsphere_product_version']

            for param in params:
                if (self.parameters.get(param) and 
                    klass.__init__.func_code.co_varnames.__contains__(param)):
                    klass_parameters[param] = self.parameters.get(param)

        pkg = klass(disk=self.image.data, base_image=self.base_image.data,
                    **klass_parameters)
        ova = pkg.make_ova_package()
        copyfile_sparse(ova, self.image.data)
        pkg.delete()

########NEW FILE########
__FILENAME__ = ovfcommon
# encoding: utf-8

#   Copyright 2013 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from xml.etree import ElementTree
from oz.ozutil import copyfile_sparse
import os
import tarfile
from shutil import rmtree
import uuid
import struct
import time
import glob
import tempfile
from stat import *
from imgfac.PersistentImageManager import PersistentImageManager

class RHEVOVFDescriptor(object):
    def __init__(self, img_uuid, vol_uuid, tpl_uuid, disk,
                 ovf_name,
                 ovf_cpu_count,
                 ovf_memory_mb,
                 rhevm_description,
                 rhevm_default_display_type,
                 rhevm_os_descriptor,
                 pool_id="00000000-0000-0000-0000-000000000000"):
        self.img_uuid = img_uuid
        self.vol_uuid = vol_uuid
        self.tpl_uuid = tpl_uuid
        self.disk = disk

        if ovf_name is None:
            self.ovf_name = str(self.tpl_uuid)
        else:
            self.ovf_name = ovf_name

        self.ovf_cpu_count = ovf_cpu_count
        self.ovf_memory_mb = ovf_memory_mb
        self.rhevm_description = rhevm_description
        self.rhevm_default_display_type = rhevm_default_display_type
        self.rhevm_os_descriptor = rhevm_os_descriptor
        self.pool_id = pool_id

    def generate_ovf_xml(self):
        etroot = ElementTree.Element('ovf:Envelope')
        etroot.set('xmlns:ovf', "http://schemas.dmtf.org/ovf/envelope/1/")
        etroot.set('xmlns:rasd', "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData")
        etroot.set('xmlns:vssd', "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData")
        etroot.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
        etroot.set('ovf:version', "0.9")

        etref = ElementTree.Element('References')

        etfile = ElementTree.Element('File')
        etfile.set('ovf:href', str(self.img_uuid)+'/'+str(self.vol_uuid))
        etfile.set('ovf:id', str(self.vol_uuid))
        etfile.set('ovf:size', str(self.disk.vol_size))
        # TODO: Bulk this up a bit
        etfile.set('ovf:description', self.ovf_name)
        etref.append(etfile)

        etroot.append(etref)

        etsec = ElementTree.Element('Section')
        etsec.set('xsi:type', "ovf:NetworkSection_Type")
        ete = ElementTree.Element('Info')
        ete.text = "List of Networks"
        etsec.append(ete)
        # dummy section, even though we have Ethernet defined below
        etroot.append(etsec)

        etsec = ElementTree.Element('Section')
        etsec.set('xsi:type', "ovf:DiskSection_Type")

        etdisk = ElementTree.Element('Disk')
        etdisk.set('ovf:diskId', str(self.vol_uuid))
        vol_size_str = str((self.disk.vol_size + (1024*1024*1024) - 1) / (1024*1024*1024))
        etdisk.set('ovf:size', vol_size_str)
        etdisk.set('ovf:vm_snapshot_id', str(uuid.uuid4()))
        etdisk.set('ovf:actual_size', vol_size_str)
        etdisk.set('ovf:format', 'http://www.vmware.com/specifications/vmdk.html#sparse')
        etdisk.set('ovf:parentRef', '')
        # XXX ovf:vm_snapshot_id
        etdisk.set('ovf:fileRef', str(self.img_uuid)+'/'+str(self.vol_uuid))
        # XXX ovf:format ("usually url to the specification")
        if self.disk.qcow_size:
            etdisk.set('ovf:volume-type', "Sparse")
            etdisk.set('ovf:volume-format', "COW")
        else:
            etdisk.set('ovf:volume-type', "Preallocated")
            etdisk.set('ovf:volume-format', "RAW")
        etdisk.set('ovf:disk-interface', "VirtIO")
        etdisk.set('ovf:disk-type', "System")
        etdisk.set('ovf:boot', "true")
        etdisk.set('ovf:wipe-after-delete', "false")
        etsec.append(etdisk)

        etroot.append(etsec)

        etcon = ElementTree.Element('Content')
        etcon.set('xsi:type', "ovf:VirtualSystem_Type")
        etcon.set('ovf:id', "out")

        ete = ElementTree.Element('Name')
        ete.text = self.ovf_name
        etcon.append(ete)

        ete = ElementTree.Element('TemplateId')
        ete.text = str(self.tpl_uuid)
        etcon.append(ete)

        # spec also has 'TemplateName'

        ete = ElementTree.Element('Description')
        ete.text = self.rhevm_description
        etcon.append(ete)

        ete = ElementTree.Element('Domain')
        # AD domain, not in use right now
        # ete.text =
        etcon.append(ete)

        ete = ElementTree.Element('CreationDate')
        ete.text = time.strftime("%Y/%m/%d %H:%M:%S", self.disk.create_time)
        etcon.append(ete)

        ete = ElementTree.Element('TimeZone')
        # ete.text =
        etcon.append(ete)

        ete = ElementTree.Element('IsAutoSuspend')
        ete.text = "false"
        etcon.append(ete)

        ete = ElementTree.Element('VmType')
        ete.text = "1"
        etcon.append(ete)

        ete = ElementTree.Element('default_display_type')
        # vnc = 0, gxl = 1
        ete.text = self.rhevm_default_display_type
        etcon.append(ete)

        ete = ElementTree.Element('default_boot_sequence')
        # C=0,   DC=1,  N=2, CDN=3, CND=4, DCN=5, DNC=6, NCD=7,
        # NDC=8, CD=9, D=10, CN=11, DN=12, NC=13, ND=14
        # (C - HardDisk, D - CDROM, N - Network)
        ete.text = "1"
        etcon.append(ete)

        etsec = ElementTree.Element('Section')
        etsec.set('xsi:type', "ovf:OperatingSystemSection_Type")
        etsec.set('ovf:id', str(self.tpl_uuid))
        etsec.set('ovf:required', "false")

        ete = ElementTree.Element('Info')
        ete.text = "Guest OS"
        etsec.append(ete)

        ete = ElementTree.Element('Description')
        # This is rigid, must be "Other", "OtherLinux", "RHEL6", or such
        ete.text = self.rhevm_os_descriptor
        etsec.append(ete)

        etcon.append(etsec)

        etsec = ElementTree.Element('Section')
        etsec.set('xsi:type', "ovf:VirtualHardwareSection_Type")

        ete = ElementTree.Element('Info')
        ete.text = "%s CPU, %s Memory" % (self.ovf_cpu_count, self.ovf_memory_mb)
        etsec.append(ete)

        etsys = ElementTree.Element('System')
        # This is probably wrong, needs actual type.
        ete = ElementTree.Element('vssd:VirtualSystemType')
        ete.text = "RHEVM 4.6.0.163"
        etsys.append(ete)
        etsec.append(etsys)

        etitem = ElementTree.Element('Item')

        ete = ElementTree.Element('rasd:Caption')
        ete.text = "%s virtual CPU" % self.ovf_cpu_count
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Description')
        ete.text = "Number of virtual CPU"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:InstanceId')
        ete.text = "1"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceType')
        ete.text = "3"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:num_of_sockets')
        ete.text = "1"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:cpu_per_socket')
        ete.text = self.ovf_cpu_count
        etitem.append(ete)

        etsec.append(etitem)

        etitem = ElementTree.Element('Item')

        ete = ElementTree.Element('rasd:Caption')
        ete.text = "%s MB of memory" % self.ovf_memory_mb
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Description')
        ete.text = "Memory Size"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:InstanceId')
        ete.text = "2"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceType')
        ete.text = "4"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:AllocationUnits')
        ete.text = "MegaBytes"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:VirtualQuantity')
        ete.text = self.ovf_memory_mb
        etitem.append(ete)

        etsec.append(etitem)

        etitem = ElementTree.Element('Item')

        ete = ElementTree.Element('rasd:Caption')
        ete.text = "Drive 1"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:InstanceId')
        ete.text = str(self.vol_uuid)
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceType')
        ete.text = "17"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:HostResource')
        ete.text = str(self.img_uuid)+'/'+str(self.vol_uuid)
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Parent')
        ete.text = "00000000-0000-0000-0000-000000000000"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Template')
        ete.text = "00000000-0000-0000-0000-000000000000"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ApplicationList')
        # List of installed applications, separated by comma
        etitem.append(ete)

        # This corresponds to ID of volgroup in host where snapshot was taken.
        # Obviously we have nothing like it.
        ete = ElementTree.Element('rasd:StorageId')
        # "Storage Domain Id"
        ete.text = "00000000-0000-0000-0000-000000000000"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:StoragePoolId')
        ete.text = self.pool_id
        etitem.append(ete)

        ete = ElementTree.Element('rasd:CreationDate')
        ete.text = time.strftime("%Y/%m/%d %H:%M:%S", self.disk.create_time)
        etitem.append(ete)

        ete = ElementTree.Element('rasd:LastModified')
        ete.text = time.strftime("%Y/%m/%d %H:%M:%S", self.disk.create_time)
        etitem.append(ete)

        etsec.append(etitem)

        etitem = ElementTree.Element('Item')

        ete = ElementTree.Element('rasd:Caption')
        ete.text = "Ethernet 0 rhevm"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:InstanceId')
        ete.text = "3"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceType')
        ete.text = "10"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceSubType')
        # e1000 = 2, pv = 3
        ete.text = "3"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Connection')
        ete.text = "rhevm"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:Name')
        ete.text = "eth0"
        etitem.append(ete)

        # also allowed is "MACAddress"

        ete = ElementTree.Element('rasd:speed')
        ete.text = "1000"
        etitem.append(ete)

        etsec.append(etitem)

        etitem = ElementTree.Element('Item')

        ete = ElementTree.Element('rasd:Caption')
        ete.text = "Graphics"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:InstanceId')
        # doc says "6", reality is "5"
        ete.text = "5"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:ResourceType')
        ete.text = "20"
        etitem.append(ete)

        ete = ElementTree.Element('rasd:VirtualQuantity')
        ete.text = "1"
        etitem.append(ete)

        etsec.append(etitem)

        etcon.append(etsec)

        etroot.append(etcon)

        et = ElementTree.ElementTree(etroot)
        return et


class VsphereOVFDescriptor(object):
    def __init__(self, disk,
                 ovf_cpu_count,
                 ovf_memory_mb,
                 vsphere_product_name,
                 vsphere_product_vendor_name,
                 vsphere_product_version):
        self.disk = disk
        self.ovf_cpu_count = ovf_cpu_count
        self.ovf_memory_mb = ovf_memory_mb
        self.vsphere_product_name = vsphere_product_name
        self.vsphere_product_vendor_name = vsphere_product_vendor_name
        self.vsphere_product_version = vsphere_product_version

    def generate_ovf_xml(self):
        etroot = ElementTree.Element('Envelope')
        etroot.set("vmw:buildId", "build-880146")
        etroot.set("xmlns", "http://schemas.dmtf.org/ovf/envelope/1")
        etroot.set("xmlns:cim", "http://schemas.dmtf.org/wbem/wscim/1/common")
        etroot.set("xmlns:ovf", "http://schemas.dmtf.org/ovf/envelope/1")
        etroot.set("xmlns:rasd", "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData")
        etroot.set("xmlns:vmw", "http://www.vmware.com/schema/ovf")
        etroot.set("xmlns:vssd", "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData")
        etroot.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        etref = ElementTree.Element('References')

        etfile = ElementTree.Element('File')
        etfile.set('ovf:href', 'disk.img')
        etfile.set('ovf:id', 'file1')
        etfile.set('ovf:size', str(self.disk.vol_size))

        etref.append(etfile)

        etroot.append(etref)

        etdisksec = ElementTree.Element('DiskSection')

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'Virtual disk information'
        etdisksec.append(etinfo)

        etdisk = ElementTree.Element('Disk')
        etdisk.set("ovf:capacity", str(self.disk.vol_size))
        etdisk.set("ovf:capacityAllocationUnits", "byte")
        etdisk.set("ovf:diskId", "vmdisk1")
        etdisk.set("ovf:fileRef", "file1")
        etdisk.set("ovf:format", "http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized")
        etdisk.set("ovf:populatedSize", str(self.disk.sparse_size))
        etdisksec.append(etdisk)
        etroot.append(etdisksec)

        etnetsec = ElementTree.Element('NetworkSection')

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'The list of logical networks'
        etnetsec.append(etinfo)

        etnet = ElementTree.Element('Network')
        etnet.set('ovf:name', 'VM Network')
        etdesc = ElementTree.Element('Description')
        etdesc.text = 'The VM Network network'
        etnet.append(etdesc)
        etnetsec.append(etnet)

        etroot.append(etnetsec)

        etvirtsys = ElementTree.Element('VirtualSystem')
        etvirtsys.set('ovf:id', self.disk.id)

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'A virtual machine'
        etvirtsys.append(etinfo)

        etname = ElementTree.Element('Name')
        etname.text = self.disk.id
        etvirtsys.append(etname)

        # TODO this should be dynamic
        etossec = ElementTree.Element('OperatingSystemSection')
        etossec.set('ovf:id', '80')
        etossec.set('ovf:version', '6')
        etossec.set('vmw:osType', 'rhel6_64Guest')

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'The kind of installed guest operating system'
        etossec.append(etinfo)

        etvirtsys.append(etossec)

        etvirthwsec = ElementTree.Element('VirtualHardwareSection')

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'Virtual hardware requirements'
        etvirthwsec.append(etinfo)

        etsystem = ElementTree.Element('System')

        etelemname = ElementTree.Element('vssd:ElementName')
        etelemname.text = 'Virtual Hardware Family'
        etsystem.append(etelemname)

        etinstid = ElementTree.Element('vssd:InstanceID')
        etinstid.text = '0'
        etsystem.append(etinstid)

        etvirtsysid = ElementTree.Element('vssd:VirtualSystemIdentifier')
        etvirtsysid.text = self.disk.id
        etsystem.append(etvirtsysid)

        etvirtsystype = ElementTree.Element('vssd:VirtualSystemType')
        etvirtsystype.text = 'vmx-07 vmx-08' #maybe not hardcode this?
        etsystem.append(etvirtsystype)

        etvirthwsec.append(etsystem)

        etitem = ElementTree.Element('Item')
        etalloc = ElementTree.Element('rasd:AllocationUnits')
        etalloc.text = 'hertz * 10^6'
        etitem.append(etalloc)
        etdesc = ElementTree.Element('rasd:Description')
        etdesc.text = 'Number of Virtual CPUs'
        etitem.append(etdesc)
        etelemname = ElementTree.Element('rasd:ElementName')
        etelemname.text = "%s virtual CPU(s)" % self.ovf_cpu_count
        etitem.append(etelemname)
        etinstid = ElementTree.Element('rasd:InstanceID')
        etinstid.text = '1'
        etitem.append(etinstid)
        etrestype = ElementTree.Element('rasd:ResourceType')
        etrestype.text = '3'
        etitem.append(etrestype)
        etvirtqty = ElementTree.Element('rasd:VirtualQuantity')
        etvirtqty.text = self.ovf_cpu_count
        etitem.append(etvirtqty)
        etvirthwsec.append(etitem)

        etitem = ElementTree.Element('Item')
        etalloc = ElementTree.Element('rasd:AllocationUnits')
        etalloc.text = 'byte * 2^20'
        etitem.append(etalloc)
        etdesc = ElementTree.Element('rasd:Description')
        etdesc.text = 'Memory Size'
        etitem.append(etdesc)
        etelemname = ElementTree.Element('rasd:ElementName')
        etelemname.text = "%s MB of memory" % self.ovf_memory_mb
        etitem.append(etelemname)
        etinstid = ElementTree.Element('rasd:InstanceID')
        etinstid.text = '2'
        etitem.append(etinstid)
        etrestype = ElementTree.Element('rasd:ResourceType')
        etrestype.text = '4'
        etitem.append(etrestype)
        etvirtqty = ElementTree.Element('rasd:VirtualQuantity')
        etvirtqty.text = self.ovf_memory_mb
        etitem.append(etvirtqty)
        etvirthwsec.append(etitem)

        etitem = ElementTree.Element('Item')
        etaddr = ElementTree.Element('rasd:Address')
        etaddr.text = '0'
        etitem.append(etaddr)
        etdesc = ElementTree.Element('rasd:Description')
        etdesc.text = 'SCSI Controller'
        etitem.append(etdesc)
        etelemname = ElementTree.Element('rasd:ElementName')
        etelemname.text = 'SCSI Controller 0'
        etitem.append(etelemname)
        etinstid = ElementTree.Element('rasd:InstanceID')
        etinstid.text = '3'
        etitem.append(etinstid)
        etressubtype = ElementTree.Element('rasd:ResourceSubType')
        etressubtype.text = 'lsilogic'
        etitem.append(etressubtype)
        etrestype = ElementTree.Element('rasd:ResourceType')
        etrestype.text = '6'
        etitem.append(etrestype)
        etvirthwsec.append(etitem)

        etitem = ElementTree.Element('Item')
        etaddronparent = ElementTree.Element('rasd:AddressOnParent')
        etaddronparent.text = '0'
        etitem.append(etaddronparent)
        etelemname = ElementTree.Element('rasd:ElementName')
        etelemname.text = 'Hard disk 0'
        etitem.append(etelemname)
        ethostres = ElementTree.Element('rasd:HostResource')
        ethostres.text = 'ovf:/disk/vmdisk1'
        etitem.append(ethostres)
        etinstid = ElementTree.Element('rasd:InstanceID')
        etinstid.text = '4'
        etitem.append(etinstid)
        etparent = ElementTree.Element('rasd:Parent')
        etparent.text = '3'
        etitem.append(etparent)
        etrestype = ElementTree.Element('rasd:ResourceType')
        etrestype.text = '17'
        etitem.append(etrestype)
        etconfig = ElementTree.Element('vmw:Config')
        etconfig.set('ovf:required', 'false')
        etconfig.set('vmw:key', 'backing.writeThrough')
        etconfig.set('vmw:value', 'false')
        etitem.append(etconfig)
        etvirthwsec.append(etitem)

        etitem = ElementTree.Element('Item')
        etaddronparent = ElementTree.Element('rasd:AddressOnParent')
        etaddronparent.text = '7'
        etitem.append(etaddronparent)
        etautoalloc = ElementTree.Element('rasd:AutomaticAllocation')
        etautoalloc.text = 'true'
        etitem.append(etautoalloc)
        etconn = ElementTree.Element('rasd:Connection')
        etconn.text = 'VM Network'
        etitem.append(etconn)
        etdesc = ElementTree.Element('rasd:Description')
        etdesc.text = 'E1000 ethernet adapter on "VM Network"'
        etitem.append(etdesc)
        etelemname = ElementTree.Element('rasd:ElementName')
        etelemname.text = 'Network adapter 1'
        etitem.append(etelemname)
        etinstid = ElementTree.Element('rasd:InstanceID')
        etinstid.text = '5'
        etitem.append(etinstid)
        etressubtype = ElementTree.Element('rasd:ResourceSubType')
        etressubtype.text = 'E1000'
        etitem.append(etressubtype)
        etrestype = ElementTree.Element('rasd:ResourceType')
        etrestype.text = '10'
        etitem.append(etrestype)
        etconfig = ElementTree.Element('vmw:Config')
        etconfig.set('ovf:required', 'false')
        etconfig.set('vmw:key', 'connectable.allowGuestControl')
        etconfig.set('vmw:value', 'true')
        etitem.append(etconfig)
        etconfig = ElementTree.Element('vmw:Config')
        etconfig.set('ovf:required', 'false')
        etconfig.set('vmw:key', 'wakeOnLanEnabled')
        etconfig.set('vmw:value', 'false')
        etitem.append(etconfig)
        etvirthwsec.append(etitem)


        etvirtsys.append(etvirthwsec)

        etprodsec = ElementTree.Element('ProductSection')

        etinfo = ElementTree.Element('Info')
        etinfo.text = 'Information about the installed software'
        etprodsec.append(etinfo)

        etprod = ElementTree.Element('Product')
        etprod.text = self.vsphere_product_name
        etprodsec.append(etprod)

        etvendor = ElementTree.Element('Vendor')
        etvendor.text = self.vsphere_product_vendor_name
        etprodsec.append(etvendor)

        etversion = ElementTree.Element('Version')
        etversion.text = self.vsphere_product_version
        etprodsec.append(etversion)

        etvirtsys.append(etprodsec)

        etroot.append(etvirtsys)

        et = ElementTree.ElementTree(etroot)
        return et

class OVFPackage(object):
    '''A directory containing an OVF descriptor and related files such as disk images'''
    def __init__(self, disk, path=None):
        if path:
            self.path = path
        else:
            storage_path = PersistentImageManager.default_manager().storage_path
            self.path = tempfile.mkdtemp(dir=storage_path)
            # this needs to be readable by others, e.g. the nfs user
            # when used in the RHEVHelper
            os.chmod(self.path, S_IRUSR|S_IWUSR|S_IXUSR|S_IRGRP|S_IXGRP|S_IROTH|S_IXOTH)

        self.disk = disk

    def delete(self):
        rmtree(self.path, ignore_errors=True)

    def sync(self):
        '''Copy disk image to path, regenerate OVF descriptor'''
        self.copy_disk()
        self.ovf_descriptor = self.new_ovf_descriptor()

        ovf_xml = self.ovf_descriptor.generate_ovf_xml()

        try:
            os.makedirs(os.path.dirname(self.ovf_path))
        except OSError, e:
            if "File exists" not in e:
                raise

        ovf_xml.write(self.ovf_path)

    def make_ova_package(self, gzip=False):
        self.sync()

        mode = 'w' if not gzip else 'w|gz'
        ovapath = os.path.join(self.path, "ova")
        tar = tarfile.open(ovapath, mode)
        cwd = os.getcwd()
        os.chdir(self.path)
        files = glob.glob('*')
        files.remove(os.path.basename(ovapath))

        # per specification, the OVF descriptor must be first in
        # the archive, and the manifest if present must be second
        # in the archive
        for f in files:
            if f.endswith(".ovf"):
                tar.add(f)
                files.remove(f)
                break
        for f in files:
            if f.endswith(".MF"):
                tar.add(f)
                files.remove(f)
                break

        # everything else last
        for f in files:
            tar.add(f)

        os.chdir(cwd)
        tar.close()

        return ovapath


class RHEVOVFPackage(OVFPackage):
    def __init__(self, disk, path=None, base_image=None,
                 ovf_name=None,
                 ovf_cpu_count="1",
                 ovf_memory_mb="512",
                 rhevm_description="Created by Image Factory",
                 rhevm_default_display_type="0",
                 rhevm_os_descriptor="OtherLinux"):

        disk = RHEVDisk(disk)
        super(RHEVOVFPackage, self).__init__(disk, path)
        # We need these three unique identifiers when generating XML and the meta file
        self.img_uuid = str(uuid.uuid4())
        self.vol_uuid = str(uuid.uuid4())
        self.tpl_uuid = str(uuid.uuid4())
        self.image_dir = os.path.join(self.path, "images",
                                      self.img_uuid)
        self.disk_path = os.path.join(self.image_dir,
                                      self.vol_uuid)
        self.meta_path = self.disk_path + ".meta"
        self.ovf_dir  = os.path.join(self.path, "master", "vms",
                                     self.tpl_uuid)
        self.ovf_path = os.path.join(self.ovf_dir,
                                     self.tpl_uuid + '.ovf')

        self.ovf_name = ovf_name
        self.ovf_cpu_count = ovf_cpu_count
        self.ovf_memory_mb = ovf_memory_mb
        self.rhevm_description = rhevm_description
        self.rhevm_default_display_type = rhevm_default_display_type
        self.rhevm_os_descriptor = rhevm_os_descriptor

    def new_ovf_descriptor(self):
        return RHEVOVFDescriptor(self.img_uuid,
                                 self.vol_uuid,
                                 self.tpl_uuid,
                                 self.disk,
                                 self.ovf_name,
                                 self.ovf_cpu_count,
                                 self.ovf_memory_mb,
                                 self.rhevm_description,
                                 self.rhevm_default_display_type,
                                 self.rhevm_os_descriptor)

    def copy_disk(self):
        os.makedirs(os.path.dirname(self.disk_path))
        copyfile_sparse(self.disk.path, self.disk_path)

    def sync(self):
        super(RHEVOVFPackage, self).sync()
        self.meta_file = RHEVMetaFile(self.img_uuid, self.disk)
        meta = open(self.meta_path, 'w')
        meta.write(self.meta_file.generate_meta_file())
        meta.close()

    def make_ova_package(self):
        return super(RHEVOVFPackage, self).make_ova_package(gzip=True)


class VsphereOVFPackage(OVFPackage):
    def __init__(self, disk, base_image, path=None,
                 ovf_cpu_count="2",
                 ovf_memory_mb="4096",
                 vsphere_product_name="Product Name",
                 vsphere_product_vendor_name="Vendor Name",
                 vsphere_product_version="1.0"):
        disk = VsphereDisk(disk, base_image)
        super(VsphereOVFPackage, self).__init__(disk, path)
        self.disk_path = os.path.join(self.path, "disk.img")
        self.ovf_path  = os.path.join(self.path, "desc.ovf")

        self.ovf_cpu_count = ovf_cpu_count
        self.ovf_memory_mb = ovf_memory_mb
        self.vsphere_product_name = vsphere_product_name
        self.vsphere_product_vendor_name = vsphere_product_vendor_name
        self.vsphere_product_version = vsphere_product_version

    def new_ovf_descriptor(self):
        return VsphereOVFDescriptor(self.disk,
                                    self.ovf_cpu_count,
                                    self.ovf_memory_mb,
                                    self.vsphere_product_name,
                                    self.vsphere_product_vendor_name,
                                    self.vsphere_product_version)

    def copy_disk(self):
        copyfile_sparse(self.disk.path, self.disk_path)


class RHEVMetaFile(object):
    def __init__(self,
                 img_uuid,
                 disk,
                 storage_domain="00000000-0000-0000-0000-000000000000",
                 pool_id="00000000-0000-0000-0000-000000000000"):
        self.img_uuid = img_uuid
        self.disk = disk
        self.storage_domain = storage_domain
        self.pool_id = pool_id

    def generate_meta_file(self):
        metafile=""

        metafile += "DOMAIN=" + self.storage_domain + "\n"
        # saved template has VOLTYPE=SHARED
        metafile += "VOLTYPE=LEAF\n"
        metafile += "CTIME=" + str(int(self.disk.raw_create_time)) + "\n"
        # saved template has FORMAT=COW
        if self.disk.qcow_size:
            metafile += "FORMAT=COW\n"
        else:
            metafile += "FORMAT=RAW\n"
        metafile += "IMAGE=" + str(self.img_uuid) + "\n"
        metafile += "DISKTYPE=1\n"
        metafile += "PUUID=00000000-0000-0000-0000-000000000000\n"
        metafile += "LEGALITY=LEGAL\n"
        metafile += "MTIME=" + str(int(self.disk.raw_create_time)) + "\n"
        metafile += "POOL_UUID=" + self.pool_id + "\n"
        # assuming 1KB alignment
        metafile += "SIZE=" + str(self.disk.vol_size/512) + "\n"
        metafile += "TYPE=SPARSE\n"
        metafile += "DESCRIPTION=Uploaded by Image Factory\n"
        metafile += "EOF\n"

        return metafile

class RHEVDisk(object):
    def __init__(self, path):
        self.path = path
        self.qcow_size = self.check_qcow_size()
        if self.qcow_size:
            self.vol_size=self.qcow_size
        else:
            self.vol_size = os.stat(self.path).st_size

        self.raw_create_time = os.path.getctime(self.path)
        self.create_time = time.gmtime(self.raw_create_time)

    def check_qcow_size(self):
        # Detect if an image is in qcow format
        # If it is, return the size of the underlying disk image
        # If it isn't, return none

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
        qcow_struct=">IIQIIQIIQQIIQ" # > means big-endian
        qcow_magic = 0x514649FB # 'Q' 'F' 'I' 0xFB

        f = open(self.path,"r")
        pack = f.read(struct.calcsize(qcow_struct))
        f.close()

        unpack = struct.unpack(qcow_struct, pack)

        if unpack[0] == qcow_magic:
            return unpack[5]
        else:
            return None

class VsphereDisk(object):
    def __init__(self, path, base_image):
        self.path = path
        self.base_image = base_image
        self.id = os.path.basename(self.path).split('.')[0]

        self.vol_size = os.stat(self.base_image).st_size
        self.sparse_size = os.stat(self.path).st_blocks*512

        # self.raw_create_time = os.path.getctime(self.path)
        # self.create_time = time.gmtime(self.raw_create_time)

########NEW FILE########
__FILENAME__ = Rackspace
#
#   Copyright 2013 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import oz.Fedora
import oz.TDL
import subprocess
import libxml2
import traceback
import ConfigParser
from time import *
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.CloudDelegate import CloudDelegate
from novaclient.v1_1 import client
from novaclient.exceptions import NotFound
import oz.Fedora


def subprocess_check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)
    stdout, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = ' '.join(*popenargs)
        raise ImageFactoryException("'%s' failed(%d): %s" % (cmd, retcode, stderr))
    return stdout, stderr, retcode


class Rackspace(object):
    zope.interface.implements(CloudDelegate)

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def __init__(self):
        # Note that we are now missing ( template, target, config_block = None):
        super(Rackspace, self).__init__()
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        config_obj = ApplicationConfiguration()
        self.app_config = config_obj.configuration
        self.oz_config = ConfigParser.SafeConfigParser()
        self.oz_config.read("/etc/oz/oz.cfg")
        self.oz_config.set('paths', 'output_dir', self.app_config["imgdir"])

        if "rackspace" in config_obj.jeos_images:
            self.rackspace_jeos_amis = config_obj.jeos_images['rackspace']
        else:
            self.log.warning("No JEOS images defined for Rackspace.  Snapshot builds will not be possible.")
            self.rackspace_jeos_amis = {}

    def log_exc(self):
        self.log.debug("Exception caught in ImageFactory")
        self.log.debug(traceback.format_exc())
        self.active_image.status_detail['error'] = traceback.format_exc()

    def wait_for_rackspace_ssh_access(self, guestaddr):
        self.activity("Waiting for SSH access to Rackspace instance")
        for index in range(300):
            if index % 10 == 0:
                self.log.debug("Waiting for Rackspace ssh access: %d/300" % index)

            try:
                self.guest.guest_execute_command(guestaddr, "/bin/true", timeout=10)
                break
            except Exception, e:
                self.log.exception('Caught exception waiting for ssh access: %s' % e)
                #import pdb
                #pdb.set_trace()
                #pass

            sleep(1)

            if index == 299:
                raise ImageFactoryException("Unable to gain ssh access after 300 seconds - aborting")

    def wait_for_rackspace_instance_start(self, instance):
        self.activity("Waiting for Rackspace instance to become active")
        for i in range(600):
            if i % 10 == 0:
                try:
                    instance.get()
                    self.log.debug("Waiting %d more seconds for Rackspace instance to start, %d%% complete..." %
                                   ((600-i), instance.progress))
                except NotFound:
                    # We occasionally get errors when querying an instance that has just started.
                    # Ignore & hope for the best
                    self.log.warning(
                        "NotFound exception encountered when querying Rackspace instance (%s) - trying to continue" % (
                            instance.id), exc_info=True)
                except:
                    self.log.error("Exception encountered when updating status of instance (%s)" % instance.id,
                                   exc_info=True)
                    self.status = "FAILED"
                    try:
                        self.terminate_instance(instance)
                    except:
                        self.log.warning(
                            "WARNING: Instance (%s) failed to start and will not terminate - it may still be running" % (
                                instance.id), exc_info=True)
                        raise ImageFactoryException(
                            "Instance (%s) failed to fully start or terminate - it may still be running" % instance.id)
                    raise ImageFactoryException(
                        "Exception encountered when waiting for instance (%s) to start" % instance.id)
                if instance.status == u'ACTIVE':
                    break
            sleep(1)
        if instance.status != u'ACTIVE':
            self.status = "FAILED"
            try:
                self.terminate_instance(instance)
            except:
                self.log.warning(
                    "WARNING: Instance (%s) failed to start and will not terminate - it may still be running" % (
                        instance.id), exc_info=True)
                raise ImageFactoryException(
                    "Instance (%s) failed to fully start or terminate - it may still be running" % instance.id)
            raise ImageFactoryException("Instance failed to start after 300 seconds - stopping")

    def terminate_instance(self, instance):
        self.activity("Deleting Rackspace instance.")
        try:
            instance.delete()
        except Exception, e:
            self.log.info("Failed to delete Rackspace instance. %s" % e)

    def snapshot_image_on_provider(self, builder, provider, credentials, target, template, parameters):
        self.log.info('snapshot_image_on_provider() called in Rackspace')

        self.builder = builder
        self.active_image = self.builder.provider_image

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.provider_image.identifier
        # TODO: so is this
        self.target = target

        # Template must be defined for snapshots
        self.tdlobj = oz.TDL.TDL(xmlstring=str(template), rootpw_required=True)

        # Create a name combining the TDL name and the UUID for use when tagging Rackspace Images
        self.longname = self.tdlobj.name + "-" + self.new_image_id

        self.log.debug("Being asked to push for provider %s" % provider)
        self.log.debug(
            "distro: %s - update: %s - arch: %s" % (self.tdlobj.distro, self.tdlobj.update, self.tdlobj.arch))
        self.rackspace_decode_credentials(credentials)
        self.log.debug("acting as Rackspace user: %s" % (str(self.rackspace_username)))

        self.status = "PUSHING"
        self.percent_complete = 0

        region = provider

        auth_url = 'https://identity.api.rackspacecloud.com/v2.0/'

        rackspace_client = client.Client(self.rackspace_username, self.rackspace_password,
                                         self.rackspace_account_number, auth_url, service_type="compute",
                                         region_name=region)
        rackspace_client.authenticate()

        mypub = open("/etc/oz/id_rsa-icicle-gen.pub")
        server_files = {"/root/.ssh/authorized_keys": mypub}

        # Now launch it
        self.activity("Launching Rackspace JEOS image")
        rackspace_image_id = self.rackspace_jeos_amis[region][self.tdlobj.distro][self.tdlobj.update][self.tdlobj.arch]['img_id']
        instance_type = '512MB Standard Instance'
        image = rackspace_client.images.find(id=rackspace_image_id)
        small = rackspace_client.flavors.find(name=instance_type)
        self.log.debug("Starting build server %s with instance_type %s" % (rackspace_image_id, instance_type))
        reservation_name = 'imagefactory-snapshot-%s' % self.active_image.identifier
        reservation = rackspace_client.servers.create(reservation_name, image, small, files=server_files)

        if not reservation:
            self.status = "FAILED"
            raise ImageFactoryException("run_instances did not result in the expected single instance - stopping")

        self.instance = reservation

        self.wait_for_rackspace_instance_start(self.instance)

        # From this point on we must be sure to terminate the instance when we are done
        # so wrap in a try/finally
        # Accidentally running a 64 bit instance doing nothing costs 56 USD week
        try:
            while self.instance.accessIPv4 == '':
                self.log.debug("Waiting to get public IP address")
            sleep(1)
            self.instance.get()
            guestaddr = self.instance.accessIPv4
            self.guest = oz.Fedora.FedoraGuest(self.tdlobj, self.oz_config, None, "virtio", True, "virtio", True)

            # Ugly ATM because failed access always triggers an exception
            self.wait_for_rackspace_ssh_access(guestaddr)

            # There are a handful of additional boot tasks after SSH starts running
            # Give them an additional 20 seconds for good measure
            self.log.debug("Waiting 60 seconds for remaining boot tasks")
            sleep(60)

            self.activity("Customizing running Rackspace JEOS instance")
            self.log.debug("Stopping cron and killing any updatedb process that may be running")
            # updatedb interacts poorly with the bundle step - make sure it isn't running
            self.guest.guest_execute_command(guestaddr, "/sbin/service crond stop")
            self.guest.guest_execute_command(guestaddr, "killall -9 updatedb || /bin/true")
            self.log.debug("Done")

            # Not all JEOS images contain this - redoing it if already present is harmless
            self.log.info("Creating cloud-info file indicating target (%s)" % self.target)
            self.guest.guest_execute_command(guestaddr,
                                             'echo CLOUD_TYPE=\\\"%s\\\" > /etc/sysconfig/cloud-info' % self.target)

            self.log.debug("Customizing guest: %s" % guestaddr)
            self.guest.mkdir_p(self.guest.icicle_tmp)
            self.guest.do_customize(guestaddr)
            self.log.debug("Customization step complete")

            self.log.debug("Generating ICICLE from customized guest")
            self.output_descriptor = self.guest.do_icicle(guestaddr)
            self.log.debug("ICICLE generation complete")

            self.log.debug("Re-de-activate firstboot just in case it has been revived during customize")
            self.guest.guest_execute_command(guestaddr,
                                             "[ -f /etc/init.d/firstboot ] && /sbin/chkconfig firstboot off || /bin/true")
            self.log.debug("De-activation complete")

            image_name = str(self.longname)
            #image_desc = "%s - %s" % (asctime(localtime()), self.tdlobj.description)

            self.log.debug("Creating a snapshot of our running Rackspace instance")
            #TODO: give proper name??
            new_image_id = self.instance.create_image(image_name)
            new_image = rackspace_client.images.find(id=new_image_id)
            while True:
                new_image.get()
                self.log.info("Saving image: %d percent complete" % new_image.progress)
                if new_image.progress == 100:
                    break
                else:
                    sleep(20)

            self.builder.provider_image.icicle = self.output_descriptor
            self.builder.provider_image.identifier_on_provider = new_image_id
            self.builder.provider_image.provider_account_identifier = self.rackspace_account_number
        except Exception, e:
            self.log.warning("Exception while executing commands on guest: %s" % e)
        finally:
            self.terminate_instance(self.instance)

    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        self.builder = builder
        self.active_image = self.builder.provider_image
        rackspace_image_id = self.active_image.identifier_on_provider
        try:
            self.log.debug("Deleting Rackspace image (%s)" % self.active_image.identifier_on_provider)
            self.rackspace_decode_credentials(credentials)
            self.log.debug("acting as Rackspace user: %s" % (str(self.rackspace_username)))

            auth_url = 'https://identity.api.rackspacecloud.com/v2.0/'
            rackspace_client = client.Client(self.rackspace_username, self.rackspace_password,
                                             self.rackspace_account_number, auth_url, service_type="compute",
                                             region_name=provider)
            rackspace_client.authenticate()
            image = rackspace_client.images.find(id=rackspace_image_id)
            if image:
                rackspace_client.images.delete(rackspace_image_id)
                self.log.debug('Successfully deleted Rackspace image (%s)' % rackspace_image_id)
        except Exception, e:
            raise ImageFactoryException('Failed to delete Rackspace image (%s) with error (%s)' % (rackspace_image_id,
                                                                                                   str(e)))

    def abort(self):
        # TODO: Make this progressively more robust
        # In the near term, the most important thing we can do is terminate any Rackspace instance we may be using
        if self.instance:
            try:
                self.log.debug('Attempting to abort instance: %s' % self.instance)
                self.terminate_instance(self.instance)
            except Exception, e:
                self.log.exception(e)
                self.log.warning("** WARNING ** Instance MAY NOT be terminated ******** ")

    def _rackspace_get_xml_node(self, doc, credtype):
        nodes = doc.xpathEval("//provider_credentials/rackspace_credentials/%s" % credtype)
        if len(nodes) < 1:
            raise ImageFactoryException("No Rackspace %s available" % credtype)

        return nodes[0].content

    def rackspace_decode_credentials(self, credentials):
        self.activity("Preparing Rackspace credentials")
        doc = libxml2.parseDoc(credentials.strip())

        self.rackspace_account_number = self._rackspace_get_xml_node(doc, "account_number")
        self.rackspace_username = self._rackspace_get_xml_node(doc, "username")
        self.rackspace_password = self._rackspace_get_xml_node(doc, "password")

        doc.freeDoc()

########NEW FILE########
__FILENAME__ = RHEVM
#
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import zope
import oz.GuestFactory
import oz.TDL
import guestfs
import libxml2
import traceback
import json
import ConfigParser
import subprocess
import logging
from time import *
from tempfile import *
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.CloudDelegate import CloudDelegate
from imgfac.FactoryUtils import launch_inspect_and_mount, shutdown_and_close, remove_net_persist, create_cloud_info
from xml.etree.ElementTree import fromstring
from RHEVMHelper import RHEVMHelper


def subprocess_check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)
    stdout, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = ' '.join(*popenargs)
        raise ImageFactoryException("'%s' failed(%d): %s\nstdout: %s" % (cmd, retcode, stderr, stdout))
    return (stdout, stderr, retcode)


class RHEVM(object):
    zope.interface.implements(CloudDelegate)

    def __init__(self):
        super(RHEVM, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_should_create_target_image() called on RHEVM plugin - returning True')
        return True


    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        # Nothing really to do here
        pass

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def log_exc(self):
        self.log.debug("Exception caught in ImageFactory")
        self.log.debug(traceback.format_exc())

    def build_image(self, build_id=None):
        try:
            self.build_upload(build_id)
        except:
            self.log_exc()
            self.status="FAILED"
            raise

    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_did_create_target_image() called in RHEVM plugin')
        self.status="BUILDING"

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.target_image.identifier

        # TODO: More convenience vars - revisit
        self.template = template
        self.target = target
        self.builder = builder

        # This lets our logging helper know what image is being operated on
        self.active_image = self.builder.target_image

        self.tdlobj = oz.TDL.TDL(xmlstring=self.template.xml, rootpw_required=self.app_config["tdl_require_root_pw"])

        # Add in target specific content
        #TODO-URGENT: Work out how to do this in the new framework
        #self.add_target_content()

        # Oz assumes unique names - TDL built for multiple backends guarantees
        # they are not unique.  We don't really care about the name so just
        # force uniqueness
        #  Oz now uses the tdlobject name property directly in several places
        # so we must change it
        self.tdlobj.name = "factory-build-" + self.new_image_id

        # In contrast to our original builders, we enter the cloud plugins with a KVM file already
        # created as the base_image.  As a result, all the Oz building steps are gone (and can be found
        # in the OS plugin(s)

        # OS plugin has already provided the initial file for us to work with
        # which we can currently assume is a raw KVM compatible image
        self.image = builder.target_image.data

        # Add the cloud-info file
        self.modify_oz_filesystem()

        # Finally, if our format is qcow2, do the transformation here
        if ("rhevm_image_format" in self.app_config) and  (self.app_config["rhevm_image_format"] == "qcow2"):
            self.log.debug("Converting RAW image to compressed qcow2 format")
            # TODO: When RHEV adds support, use the -c option to compress these images to save space
            qemu_img_cmd = [ "qemu-img", "convert", "-O", "qcow2", self.image, self.image + ".tmp.qcow2" ]
            (stdout, stderr, retcode) = subprocess_check_output(qemu_img_cmd)
            os.unlink(self.image)
            os.rename(self.image + ".tmp.qcow2", self.image)

        self.percent_complete=100
        self.status="COMPLETED"

    def modify_oz_filesystem(self):
        self.log.debug("Doing further Factory specific modification of Oz image")
        guestfs_handle = launch_inspect_and_mount(self.builder.target_image.data)
        remove_net_persist(guestfs_handle)
        create_cloud_info(guestfs_handle, self.target)
        shutdown_and_close(guestfs_handle)

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        self.log.info('push_image_to_provider() called in RHEVM')

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.provider_image.identifier

        self.tdlobj = oz.TDL.TDL(xmlstring=builder.target_image.template, rootpw_required=self.app_config["tdl_require_root_pw"])
        self.builder = builder
        self.active_image = self.builder.provider_image
        self.push_image(target_image, provider, credentials)

    def push_image(self, target_image_id, provider, credentials):
        try:
            self.status = "PUSHING"
            self.percent_complete = 0
            self.rhevm_push_image_upload(target_image_id, provider, credentials)
        except:
            self.log_exc()
            self.status="FAILED"
            raise
        self.status = "COMPLETED"

    def rhevm_push_image_upload(self, target_image_id, provider, credentials):
        provider_data = self.get_dynamic_provider_data(provider)
        if provider_data is None:
            raise ImageFactoryException("RHEV-M instance not found in XML or JSON provided")

        self.generic_decode_credentials(credentials, provider_data, "rhevm")

        self.log.debug("Username: %s" % (self.username))

        helper = RHEVMHelper(url=provider_data['api-url'], username=self.username, password=self.password)
        # Image is always here and it is the target_image datafile
        input_image = self.builder.target_image.data
        rhevm_uuid = helper.import_template(input_image, provider_data['nfs-host'], provider_data['nfs-path'], 
                                            provider_data['nfs-dir'], provider_data['cluster'], ovf_name=str(self.new_image_id), 
                                            ovf_desc = "Template name (%s) from base image (%s)" % (self.tdlobj.name, str(self.builder.base_image.identifier)) )

        if rhevm_uuid is None:
            raise ImageFactoryException("Failed to obtain RHEV-M UUID from helper")

        self.log.debug("New RHEVM Template UUID: %s " % (rhevm_uuid))

        self.builder.provider_image.identifier_on_provider = rhevm_uuid
        self.builder.provider_image.provider_account_identifier = self.username
        self.percent_complete = 100

    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        self.log.debug("Deleting RHEVM template (%s)" % (self.builder.provider_image.identifier_on_provider))
        provider_data = self.get_dynamic_provider_data(provider)
        if provider_data is None:
            raise ImageFactoryException("RHEV-M instance not found in XML or JSON provided")

        self.generic_decode_credentials(credentials, provider_data, "rhevm")

        self.log.debug("Username: %s" % (self.username))

        helper = RHEVMHelper(url=provider_data['api-url'], username=self.username, password=self.password)
        if not helper.delete_template(self.builder.provider_image.identifier_on_provider):
            raise ImageFactoryException("Delete of template failed")


    def generic_decode_credentials(self, credentials, provider_data, target):
        # convenience function for simple creds (rhev-m and vmware currently)
        doc = libxml2.parseDoc(credentials)

        self.username = None
        _usernodes = doc.xpathEval("//provider_credentials/%s_credentials/username" % (target))
        if len(_usernodes) > 0:
            self.username = _usernodes[0].content
        else:
            try:
                self.username = provider_data['username']
            except KeyError:
                raise ImageFactoryException("No username specified in config file or in push call")
        self.provider_account_identifier = self.username

        _passnodes = doc.xpathEval("//provider_credentials/%s_credentials/password" % (target))
        if len(_passnodes) > 0:
            self.password = _passnodes[0].content
        else:
            try:
                self.password = provider_data['password']
            except KeyError:
                raise ImageFactoryException("No password specified in config file or in push call")

        doc.freeDoc()

    def get_dynamic_provider_data(self, provider):
        # Get provider details for RHEV-M or VSphere
        # First try to interpret this as an ad-hoc/dynamic provider def
        # If this fails, try to find it in one or the other of the config files
        # If this all fails return None
        # We use this in the builders as well so I have made it "public"

        try:
            xml_et = fromstring(provider)
            return xml_et.attrib
        except Exception as e:
            self.log.debug('Testing provider for XML: %s' % e)
            pass

        try:
            jload = json.loads(provider)
            return jload
        except ValueError as e:
            self.log.debug('Testing provider for JSON: %s' % e)
            pass

        return None

    def abort(self):
        pass

########NEW FILE########
__FILENAME__ = RHEVMHelper
#!/usr/bin/python
import pdb
import logging
import stat
import os
import sys
import struct
import time
import uuid
import subprocess
from tempfile import NamedTemporaryFile, TemporaryFile
from ovirtsdk.api import API
from ovirtsdk.xml import params
from xml.etree import ElementTree
from time import sleep
from threading import BoundedSemaphore
from imagefactory_plugins.ovfcommon.ovfcommon import RHEVOVFPackage

# Large portions derived from dc-rhev-img from iwhd written by
# Pete Zaitcev <zaitcev@redhat.com>

NFSUID = 36
NFSGID = 36

# Borrowed from Oz by Chris Lalancette 
def subprocess_check_output(*popenargs, **kwargs):
    """
Function to call a subprocess and gather the output.
"""
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    if 'stderr' in kwargs:
        raise ValueError('stderr argument not allowed, it will be overridden.')

    #executable_exists(popenargs[0][0])

    # NOTE: it is very, very important that we use temporary files for
    # collecting stdout and stderr here. There is a nasty bug in python
    # subprocess; if your process produces more than 64k of data on an fd that
    # is using subprocess.PIPE, the whole thing will hang. To avoid this, we
    # use temporary fds to capture the data
    stdouttmp = TemporaryFile()
    stderrtmp = TemporaryFile()

    process = subprocess.Popen(stdout=stdouttmp, stderr=stderrtmp, *popenargs,
                               **kwargs)
    process.communicate()
    retcode = process.poll()

    stdouttmp.seek(0, 0)
    stdout = stdouttmp.read()
    stdouttmp.close()

    stderrtmp.seek(0, 0)
    stderr = stderrtmp.read()
    stderrtmp.close()

    if retcode:
        cmd = ' '.join(*popenargs)
        raise Exception("'%s' failed(%d): %s" % (cmd, retcode, stderr), retcode)
    return (stdout, stderr, retcode)


class RHEVMHelper(object):

    api_connections_lock = BoundedSemaphore()

    def __init__(self, url, username, password):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        # The SDK allows only a single active connection object to be created, regardless of whether 
        # or not multiple RHEVM servers are being accessed.  For now we need to have a global lock,
        # create a connection object before each batch of API interactions and then disconnect it.
        self.api_details = { 'url':url, 'username':username, 'password':password }

    # TODO: When this limitation in the ovirt SDK is removed, get rid of these
    def _init_api(self):
        self.log.debug("Doing blocking acquire() on global RHEVM API connection lock")
        self.api_connections_lock.acquire()
        self.log.debug("Got global RHEVM API connection lock")
        url = self.api_details['url']
        username = self.api_details['username']
        password = self.api_details['password']
        self.api = API(url=url, username=username, password=password, insecure=True)

    def _disconnect_api(self):
        try:
            self.log.debug("Attempting API disconnect")
            if hasattr(self, 'api') and self.api is not None:
                self.api.disconnect()
            else:
                self.log.debug("API connection was not initialized.  Will not attempt to disconnect.")
        finally:
            # Must always do this
            self.log.debug("Releasing global RHEVM API connection lock")
            self.api_connections_lock.release()

    # These are the only two genuinley public methods
    # What we create is a VM template

    def import_template(self, image_filename, nfs_host, nfs_path, nfs_dir, cluster,
                        ovf_name = None, ovf_desc = None):
        if not ovf_desc:
            self.ovf_desc = "Imported by Image Factory"
        else:
            self.ovf_desc = ovf_desc
        self.log.debug("Preparing for RHEVM template import of image file (%s)" % (image_filename))

        # API lock protected action
        try: 
            self._init_api()
            self.init_vm_import(image_filename, nfs_host, nfs_path, nfs_dir, cluster)
        finally:
            self._disconnect_api()

        self.ovf_name = ovf_name
        self.log.debug("Staging files")
        self.stage_files()
        self.log.debug("Moving files to final export domain location")
        self.move_files()
        self.ovf_pkg.delete()
        self.log.debug("Executing import")

        # API lock protected action
        try:
            self._init_api()
            self.execute_import()
        finally:
            self._disconnect_api()

        return str(self.ovf_pkg.tpl_uuid)

    def delete_template(self, template_uuid):
        template = self.api.templates.get(id=template_uuid)
        if template:
            template.delete()
            return True
        else:
            return False

    # Begin Nuts and Bolts

    # We don't want to run seteuid() in our main process as it will globally change the UID/GID for everything
    # OTOH, we need to be root to access our image files and temp files
    # We use stdin and Popen's preexec_fn via the helper functions below to deal with this
    def become_nfs_user(self):
        os.setegid(NFSGID)
        os.seteuid(NFSUID)

    def copy_as_nfs_user(self, sourcefile, destfile):
        self.log.debug("Copying (%s) to (%s) as nfsuser" % (sourcefile, destfile))
        f = open(sourcefile,"r")
        (stdout, stderr, retcode) = subprocess_check_output([ 'dd', 'of=%s' % (destfile), 'bs=4k' ], stdin=f, preexec_fn=self.become_nfs_user)
        f.close()

    def copy_dir_as_nfs_user(self, sourcefile, destfile):
        self.log.debug("Copying directory (%s) to (%s) as nfsuser" % (sourcefile, destfile))
        (stdout, stderr, retcode) = subprocess_check_output([ 'cp', '-r', '%s' % (sourcefile), '%s' % (destfile)], preexec_fn=self.become_nfs_user)

    def move_as_nfs_user(self, sourcefile, destfile):
        self.log.debug("Moving (%s) to (%s) as nfsuser" % (sourcefile, destfile))
        (stdout, stderr, retcode) = subprocess_check_output([ 'mv', '%s' % (sourcefile), '%s' % (destfile)], preexec_fn=self.become_nfs_user)

    def mkdir_as_nfs_user(self, directory):
        self.log.debug("Making directory (%s) as nfsuser" % (directory))
        (stdout, stderr, retcode) = subprocess_check_output([ 'mkdir', '%s' % (directory)], preexec_fn=self.become_nfs_user)

    def rm_rf_as_nfs_user(self, directory):
        self.log.debug("Recursive remove of dir (%s) as nfsuser" % (directory))
        (stdout, stderr, retcode) = subprocess_check_output([ 'rm', '-rf', '%s' % (directory)], preexec_fn=self.become_nfs_user)

    def get_storage_domain(self, nfs_host, nfs_path):
        # Find the storage domain that matches the nfs details given
        sds = self.api.storagedomains.list()
        for sd in sds:
            if sd.get_type() == "export":
                self.log.debug("Export domain: (%s)" % (sd.get_name()))
                stor = sd.get_storage()
                if (stor.get_address() == nfs_host) and (stor.get_path() == nfs_path):
                    self.log.debug("This is the right domain (%s)" % (sd.get_id()))
                    return sd
        return None

    def get_pool_id(self, sd_uuid):
        # Get datacenter for a given storage domain UUID
        # This is the UUID that becomes the "StoragePoolID" in our OVF XML
        # TODO: The storagedomain object has a get_data_center() method that doesn't seem to work
        #       Find out why
        dcs =  self.api.datacenters.list()
        for dc in dcs:
            self.log.debug("Looking for our storage domain (%s) in data center (%s)" % (sd_uuid, dc.get_id()))
            sd = dc.storagedomains.get(id=sd_uuid)
            if sd: 
                self.log.debug("This is the right datacenter (%s)" % (dc.get_id()))
                return dc
        return None

    def get_cluster_by_dc(self, poolid):
        # If we have been passed "_any_" as the cluster name, we pick the first cluster that
        # matches our datacenter/pool ID
        clusters = self.api.clusters.list()

        for cluster in clusters:
            dc_id = None
            if cluster.get_data_center():
                dc_id = cluster.get_data_center().get_id()
            self.log.debug("Checking cluster (%s) with name (%s) with data center (%s)" % (cluster.get_id(), cluster.get_name(), dc_id))
            if dc_id == poolid:
                return cluster
        self.log.debug("Cannot find cluster for dc (%s)" % (poolid))
        return None

    def get_cluster_by_name(self, name):
        # If we have been passed a specific cluster name, we need to find that specific cluster
        clusters = self.api.clusters.list()
        for cluster in clusters:
            self.log.debug("Checking cluster (%s) with name (%s)" % (cluster.get_id(), cluster.get_name()))
            if cluster.get_name() == name:
                return cluster
        self.log.debug("Cannot find cluster named (%s)" % (name))
        return None


    def init_vm_import(self, image_filename, nfs_host, nfs_path, nfs_dir, cluster):
        # Prepare for the import of a VM
        self.image_filename = image_filename
        self.nfs_host = nfs_host
        self.nfs_path = nfs_path
        self.nfs_dir = nfs_dir

        # Sets some values used when creating XML and meta files
        self.storage_domain_object = self.get_storage_domain(nfs_host, nfs_path)
        if self.storage_domain_object:
            self.storage_domain = self.storage_domain_object.get_id()
        else:
            raise Exception("Cannot find storage domain matching NFS details given")

        self.dc_object = self.get_pool_id(self.storage_domain)
        if self.dc_object:
            # Our StoragePoolID is the UUID of the DC containing our storage domain
            self.pool_id=self.dc_object.get_id()
        else:
            raise Exception("Cannot find datacenter for our storage domain")

        if cluster == '_any_':
            self.cluster_object = self.get_cluster_by_dc(self.pool_id)
        else:
            self.cluster_object = self.get_cluster_by_name(cluster)
        if self.cluster_object:
            self.cluster = self.cluster_object.get_id()
        else:
            raise Exception("Cannot find cluster (%s)" % (cluster))

    def stage_files(self):
        # Called after init to copy files to staging location

        # This is the base dir of the export domain
        self.export_domain_dir = self.nfs_dir + "/" + self.storage_domain
        if not os.path.isdir(self.export_domain_dir):
            raise Exception("Cannot find expected export domain directory (%s) at local mount point (%s)" % (self.nfs_dir, self.storage_domain))

        self.ovf_pkg = RHEVOVFPackage(disk=self.image_filename,
                                      ovf_name=self.ovf_name,
                                      ovf_desc=self.ovf_desc)
        self.ovf_pkg.sync()

    def move_files(self):
        self.final_image_dir = "%s/images/%s" % (self.export_domain_dir, str(self.ovf_pkg.img_uuid))
        self.final_ovf_dir = "%s/master/vms/%s" % (self.export_domain_dir, str(self.ovf_pkg.tpl_uuid))

        self.copy_dir_as_nfs_user(self.ovf_pkg.image_dir, self.final_image_dir)
        self.copy_dir_as_nfs_user(self.ovf_pkg.ovf_dir, self.final_ovf_dir)

    def remove_export_template(self):
        self.rm_rf_as_nfs_user(self.final_image_dir)
        self.rm_rf_as_nfs_user(self.final_ovf_dir)       

    def execute_import(self):
        # We import to the master storage domain of the datacenter of which our export domain is a member
        # Got it?
        action = params.Action()
        sds = self.dc_object.storagedomains.list()
        for sd in sds:
            if sd.get_master():
                action.storage_domain=sd
        if not action.storage_domain:
            raise Exception("Could not find master storage domain for datacenter ID (%s)" % (self.dc_object.get_id()))
        action.cluster = self.cluster_object

        # At this point our freshly copied in files are discoverable via the tpl_uuid in our export domain
        template = self.storage_domain_object.templates.get(id=str(self.ovf_pkg.tpl_uuid))
        if template:
            template.import_template(action=action)
            real_template = self.api.templates.get(id=str(self.ovf_pkg.tpl_uuid))
            # Wait 5 minutes for an import to finish
            self.log.debug("Waiting for template import to complete")
            for i in range(30):
                self.log.debug("Waited %d - state (%s)" % (i*10, real_template.get_status().get_state()))
                if real_template.get_status().get_state() != 'locked':
                    break
                real_template = real_template.update()
                sleep(10)
            self.log.debug("Deleting export domain files")
            self.remove_export_template() 
            final_state = real_template.get_status().get_state()
            if final_state == 'ok':
                self.log.debug("Template import completed successfully")
                return
            elif final_state == 'locked':
                raise Exception("Timed out waiting for template import to finish")
            else:
                raise Exception("Template import ended in unknown state (%s)" % (final_state))

########NEW FILE########
__FILENAME__ = TinMan
#
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import zope
import oz.GuestFactory
import oz.TDL
import oz.ozutil
import subprocess
import libxml2
import traceback
import ConfigParser
from os.path import isfile
from time import *
from tempfile import NamedTemporaryFile
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.ReservationManager import ReservationManager
from imgfac.FactoryUtils import launch_inspect_and_mount, shutdown_and_close, remove_net_persist
from imgfac.OSDelegate import OSDelegate
from imgfac.FactoryUtils import parameter_cast_to_bool
from libvirt import libvirtError
from oz.OzException import OzException


def subprocess_check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)
    stdout, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = ' '.join(*popenargs)
        raise ImageFactoryException("'%s' failed(%d): %s" % (cmd, retcode, stderr))
    return (stdout, stderr, retcode)



class TinMan(object):
    zope.interface.implements(OSDelegate)

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    ## INTERFACE METHOD
    def create_target_image(self, builder, target, base_image, parameters):
        self.log.info('create_target_image() called for TinMan plugin - creating a TargetImage')
        self.active_image = builder.target_image
        self.target = target
        self.base_image = builder.base_image

        # populate our target_image bodyfile with the original base image
        # which we do not want to modify in place
        self.activity("Copying BaseImage to modifiable TargetImage")
        self.log.debug("Copying base_image file (%s) to new target_image file (%s)" % (builder.base_image.data, builder.target_image.data))
        oz.ozutil.copyfile_sparse(builder.base_image.data, builder.target_image.data)
        self.image = builder.target_image.data

        # Merge together any TDL-style customizations requested via our plugin-to-plugin interface
        # with any target specific packages, repos and commands and then run a second Oz customization
        # step.
        self.tdlobj = oz.TDL.TDL(xmlstring=builder.base_image.template, rootpw_required=self.app_config["tdl_require_root_pw"])
        
        # We remove any packages, commands and files from the original TDL - these have already been
        # installed/executed.  We leave the repos in place, as it is possible that the target
        # specific packages or commands may require them.
        self.tdlobj.packages = [ ]
        self.tdlobj.commands = { }
        self.tdlobj.files = { } 
        # This is user-defined target-specific packages and repos in a local config file
        self.add_target_content()
        # This is content deposited by cloud plugins - typically commands to run to prep the image further
        self.merge_cloud_plugin_content()

        # If there are no new commands, packages or files, we can stop here - there is no need to run Oz again
        if (len(self.tdlobj.packages) + len(self.tdlobj.commands) + len(self.tdlobj.files)) == 0:
            self.log.debug("No further modification of the TargetImage to perform in the OS Plugin - returning")
            return 

        # We have some additional work to do - create a new Oz guest object that we can use to run the guest
        # customization a second time
        self._init_oz()

        self.guest.diskimage = builder.target_image.data

        libvirt_xml = self.guest._generate_xml("hd", None)

        # One last step is required here - The persistent net rules in some Fedora and RHEL versions
        # Will cause our new incarnation of the image to fail to get network - fix that here
        # We unfortunately end up having to duplicate this a second time in the cloud plugins
        # when we are done with our second  stage customizations
        # TODO: Consider moving all of that back here

        guestfs_handle = launch_inspect_and_mount(builder.target_image.data)
        remove_net_persist(guestfs_handle)
        shutdown_and_close(guestfs_handle)

        try:
            self.log.debug("Doing second-stage target_image customization and ICICLE generation")
            #self.percent_complete = 30
            builder.target_image.icicle = self.guest.customize_and_generate_icicle(libvirt_xml)
            self.log.debug("Customization and ICICLE generation complete")
            #self.percent_complete = 50
        finally:
            self.activity("Cleaning up install artifacts")
            self.guest.cleanup_install()

    def add_cloud_plugin_content(self, content):
        # This is a method that cloud plugins can call to deposit content/commands to be run
        # during the OS-specific first stage of the Target Image creation.
        # The expected input is a dict containing commands and files
        # No support for repos at the moment as these introduce external deps that we may not be able to count on
        # Add this to an array which will later be merged into the TDL object used to drive Oz
        self.cloud_plugin_content.append(content)

    def merge_cloud_plugin_content(self):
        for content in self.cloud_plugin_content:
            if 'files' in content:
                for fileentry in content['files']:
                    if not 'name' in fileentry:
                        raise ImageFactoryException("File given without a name")
                    if not 'type' in fileentry:
                        raise ImageFactoryException("File given without a type")
                    if not 'file' in fileentry:
                        raise ImageFactoryException("File given without any content")
                    if fileentry['type'] == 'raw':
                        self.tdlobj.files[fileentry['name']] = fileentry['file']
                    elif fileentry['type'] == 'base64':
                        if len(fileentry['file']) == 0:
                            self.tdlobj.files[fileentry['name']] = ""
                        else:
                            self.tdlobj.files[fileentry['name']] = base64.b64decode(fileentry['file'])
                    else:
                        raise ImageFactoryException("File given with invalid type (%s)" % (file['type']))

            if 'commands' in content:
                for command in content['commands']:
                    if not 'name' in command:
                        raise ImageFactoryException("Command given without a name")
                    if not 'type' in command:
                        raise ImageFactoryException("Command given without a type")
                    if not 'command' in command:
                        raise ImageFactoryException("Command given without any content")
                    if command['type'] == 'raw':
                        self.tdlobj.commands[command['name']] = command['command']
                    elif command['type'] == 'base64':
                        if len(command['command']) == 0:
                            self.log.warning("Command with zero length given")
                            self.tdlobj.commands[command['name']] = ""
                        else:
                            self.tdlobj.commandss[command['name']] = base64.b64decode(command['command'])
                    else:
                        raise ImageFactoryException("Command given with invalid type (%s)" % (command['type']))


    def add_target_content(self):
        """Merge in target specific package and repo content.
        TDL object must already exist as self.tdlobj"""
        doc = None
        if isfile("/etc/imagefactory/target_content.xml"):
            doc = libxml2.parseFile("/etc/imagefactory/target_content.xml")
        else:
            self.log.debug("Found neither a call-time config nor a config file - doing nothing")
            return

        # Purely to make the xpath statements below a tiny bit shorter
        target = self.target
        os=self.tdlobj.distro
        version=self.tdlobj.update
        arch=self.tdlobj.arch

        # We go from most to least specific in this order:
        #   arch -> version -> os-> target
        # Note that at the moment we even allow an include statment that covers absolutely everything.
        # That is, one that doesn't even specify a target - this is to support a very simple call-time syntax
        include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and @version='%s' and @arch='%s']" %
                  (target, os, version, arch))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and @version='%s' and not(@arch)]" %
                      (target, os, version))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and @os='%s' and not(@version) and not(@arch)]" %
                      (target, os))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[@target='%s' and not(@os) and not(@version) and not(@arch)]" %
                      (target))
        if len(include) == 0:
            include = doc.xpathEval("/template_includes/include[not(@target) and not(@os) and not(@version) and not(@arch)]")
        if len(include) == 0:
            self.log.debug("cannot find a config section that matches our build details - doing nothing")
            return

        # OK - We have at least one config block that matches our build - take the first one, merge it and be done
        # TODO: Merge all of them?  Err out if there is more than one?  Warn?
        include = include[0]

        packages = include.xpathEval("packages")
        if len(packages) > 0:
            self.tdlobj.merge_packages(str(packages[0]))

        repositories = include.xpathEval("repositories")
        if len(repositories) > 0:
            self.tdlobj.merge_repositories(str(repositories[0]))


    def __init__(self):
        super(TinMan, self).__init__()
        self.cloud_plugin_content = [ ]
        config_obj = ApplicationConfiguration()
        self.app_config = config_obj.configuration
        self.res_mgr = ReservationManager()
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.parameters = None
        self.install_script_object = None
        self.guest = None

    def abort(self):
        self.log.debug("ABORT called in TinMan plugin")
        # If we have an active Oz VM destroy it - if not do nothing but log why we did nothing
        if not self.guest:
            self.log.debug("No Oz guest object present - nothing to do")
            return

        try:
            # Oz doesn't keep the active domain object as an instance variable so we have to look it up
            guest_dom = self.guest.libvirt_conn.lookupByName(self.tdlobj.name)
        except Exception, e:
            self.log.exception(e)
            self.log.debug("No Oz VM found with name (%s) - nothing to do" % (self.tdlobj.name))
            self.log.debug("This likely means the local VM has already been destroyed or never started")
            return

        try:
            self.log.debug("Attempting to destroy local guest/domain (%s)" % (self.tdlobj.name))
            guest_dom.destroy()
        except Exception, e:
            self.log.exception(e)
            self.log.warning("Exception encountered while destroying domain - it may still exist")


    def _init_oz(self):
        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = self.active_image.identifier

        # Create a name combining the TDL name and the UUID for use when tagging EC2 AMIs
        self.longname = self.tdlobj.name + "-" + self.new_image_id
        # Oz assumes unique names - TDL built for multiple backends guarantees they are not unique
        # We don't really care about the name so just force uniqueness
        # 18-Jul-2011 - Moved to constructor and modified to change TDL object name itself
        #   Oz now uses the tdlobject name property directly in several places so we must change it
        self.tdlobj.name = "factory-build-" + self.new_image_id

        # populate a config object to pass to OZ; this allows us to specify our
        # own output dir but inherit other Oz behavior
        self.oz_config = ConfigParser.SafeConfigParser()
        if self.oz_config.read("/etc/oz/oz.cfg") != []:
            self.oz_config.set('paths', 'output_dir', self.app_config["imgdir"])
            if "oz_data_dir" in self.app_config:
                self.oz_config.set('paths', 'data_dir', self.app_config["oz_data_dir"])
            if "oz_screenshot_dir" in self.app_config:
                self.oz_config.set('paths', 'screenshot_dir', self.app_config["oz_screenshot_dir"])
        else:
            raise ImageFactoryException("No Oz config file found. Can't continue.")

        # make this a property to enable quick cleanup on abort
        self.instance = None

        # Here we are always dealing with a local install
        self.init_guest()


    ## INTERFACE METHOD
    def create_base_image(self, builder, template, parameters):
        self.log.info('create_base_image() called for TinMan plugin - creating a BaseImage')

        self.tdlobj = oz.TDL.TDL(xmlstring=template.xml, rootpw_required=self.app_config["tdl_require_root_pw"])
        if parameters:
            self.parameters = parameters
        else:
            self.parameters = { }

        # TODO: Standardize reference scheme for the persistent image objects in our builder
        #   Having local short-name copies like this may well be a good idea though they
        #   obscure the fact that these objects are in a container "upstream" of our plugin object
        self.base_image = builder.base_image

        # Set to the image object that is actively being created or modified
        # Used in the logging helper function above
        self.active_image = self.base_image

        try:
            self._init_oz()
            self.guest.diskimage = self.base_image.data
            self.activity("Cleaning up any old Oz guest")
            self.guest.cleanup_old_guest()
            self.activity("Generating JEOS install media")
            self.threadsafe_generate_install_media(self.guest)
            self.percent_complete=10

            # We want to save this later for use by RHEV-M and Condor clouds
            libvirt_xml=""
            gfs = None

            try:
                self.activity("Generating JEOS disk image")
                # Newer Oz versions introduce a configurable disk size in TDL
                # We must still detect that it is present and pass it in this call
                try:
                    disksize=getattr(self.guest, "disksize")
                except AttributeError:
                    disksize = 10
                self.guest.generate_diskimage(size = disksize)
                # TODO: If we already have a base install reuse it
                #  subject to some rules about updates to underlying repo
                self.activity("Execute JEOS install")
                libvirt_xml = self.guest.install(self.app_config["timeout"])
                self.base_image.parameters['libvirt_xml'] = libvirt_xml
                self.image = self.guest.diskimage
                self.log.debug("Base install complete - Doing customization and ICICLE generation")
                self.percent_complete = 30
                # Power users may wish to avoid ever booting the guest after the installer is finished
                # They can do so by passing in a { "generate_icicle": False } KV pair in the parameters dict
                if parameter_cast_to_bool(self.parameters.get("generate_icicle", True)):
                    if parameter_cast_to_bool(self.parameters.get("offline_icicle", False)):
                        self.guest.customize(libvirt_xml)
                        gfs = launch_inspect_and_mount(self.image, readonly=True)
                        # Monkey-patching is bad
                        # TODO: Work with Chris to incorporate a more elegant version of this into Oz itself
                        def libguestfs_execute_command(gfs, cmd, timeout):
                            stdout = gfs.sh(cmd)
                            return (stdout, None, 0)
                        self.guest.guest_execute_command = libguestfs_execute_command
                        builder.base_image.icicle = self.guest.do_icicle(gfs)                            
                    else:
                        builder.base_image.icicle = self.guest.customize_and_generate_icicle(libvirt_xml)
                else:
                    self.guest.customize(libvirt_xml)
                self.log.debug("Customization and ICICLE generation complete")
                self.percent_complete = 50
            finally:
                self.activity("Cleaning up install artifacts")
                if self.guest:
                    self.guest.cleanup_install()
                if self.install_script_object:
                    # NamedTemporaryFile - removed on close
                    self.install_script_object.close()    
                if gfs:
                    shutdown_and_close(gfs)

            self.log.debug("Generated disk image (%s)" % (self.guest.diskimage))
            # OK great, we now have a customized KVM image

        finally:
            pass
            # TODO: Create the base_image object representing this
            # TODO: Create the base_image object at the beginning and then set the diskimage accordingly

    def init_guest(self):
        # Use the factory function from Oz directly
        # This raises an exception if the TDL contains an unsupported distro or version
        # Cloud plugins that use KVM directly, such as RHEV-M and openstack-kvm can accept
        # any arbitrary guest that Oz is capable of producing

        install_script_name = None
        install_script = self.parameters.get("install_script", None)
        if install_script:
            self.install_script_object = NamedTemporaryFile()
            self.install_script_object.write(install_script)
            self.install_script_object.flush()
            install_script_name = self.install_script_object.name

        try:
            self.guest = oz.GuestFactory.guest_factory(self.tdlobj, self.oz_config, install_script_name)
            # Oz just selects a random port here - This could potentially collide if we are unlucky
            self.guest.listen_port = self.res_mgr.get_next_listen_port()
        except libvirtError, e:
            raise ImageFactoryException("Cannot connect to libvirt.  Make sure libvirt is running. [Original message: %s]" %  e.message)
        except OzException, e:
            if "Unsupported" in e.message:
                raise ImageFactoryException("TinMan plugin does not support distro (%s) update (%s) in TDL" % (self.tdlobj.distro, self.tdlobj.update) )
            else:
                raise e

    def log_exc(self):
        self.log.debug("Exception caught in ImageFactory")
        self.log.debug(traceback.format_exc())
        self.active_image.status_detal['error'] = traceback.format_exc()

    def threadsafe_generate_install_media(self, guest):
        # Oz caching of install media and modified install media is not thread safe
        # Make it safe here using some locks
        # We can only have one active generate_install_media() call for each unique tuple:
        #  (OS, update, architecture, installtype)

        tdl = guest.tdl
        queue_name = "%s-%s-%s-%s" % (tdl.distro, tdl.update, tdl.arch, tdl.installtype)
        self.res_mgr.get_named_lock(queue_name)
        try:
            guest.generate_install_media(force_download=False)
        finally:
            self.res_mgr.release_named_lock(queue_name)



########NEW FILE########
__FILENAME__ = vSphere
#
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import zope
import oz.GuestFactory
import oz.TDL
import os
import guestfs
import libxml2
import traceback
import json
import ConfigParser
import logging
from xml.etree.ElementTree import fromstring
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.ImageFactoryException import ImageFactoryException
from imgfac.FactoryUtils import launch_inspect_and_mount, shutdown_and_close, remove_net_persist, create_cloud_info
from VSphereHelper import VSphereHelper
from VMDKstream import convert_to_stream
from imgfac.CloudDelegate import CloudDelegate

rhel5_module_script='''echo "alias scsi_hostadapter2 mptbase" >> /etc/modprobe.conf
echo "alias scsi_hostadapter3 mptspi" >> /etc/modprobe.conf
KERNEL=`grubby --default-kernel`
KERNELVERSION=`grubby --default-kernel | cut -f 2- -d "-"`
NEWINITRD="`grubby --info=$KERNEL | grep initrd | cut -f 2 -d "="`-vsphere"
mkinitrd $NEWINITRD $KERNELVERSION
grubby --add-kernel=$KERNEL --copy-default --make-default --initrd=$NEWINITRD --title="Red Hat Enterprise Linux Server ($KERNELVERSION) Image Factory vSphere module update"
rm /root/vsphere-module.sh'''

class vSphere(object):
    """docstring for Fedora_vsphere_Builder"""
    zope.interface.implements(CloudDelegate)

    def __init__(self):
        super(vSphere, self).__init__()
        self.app_config = ApplicationConfiguration().configuration
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def activity(self, activity):
        # Simple helper function
        # Activity should be a one line human-readable string indicating the task in progress
        # We log it at DEBUG and also set it as the status_detail on our active image
        self.log.debug(activity)
        self.active_image.status_detail['activity'] = activity

    def log_exc(self):
        self.log.debug("Exception caught in ImageFactory")
        self.log.debug(traceback.format_exc())

    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        self.log.debug("Deleting vSphere image (%s)" % (self.builder.provider_image.identifier_on_provider))

        provider_data = self.get_dynamic_provider_data(provider)
        if provider_data is None:
            raise ImageFactoryException("VMWare instance not found in XML or JSON provided")
        self.generic_decode_credentials(credentials, provider_data, "vsphere")
        helper = VSphereHelper(provider_data['api-url'], self.username, self.password)
        # This call raises an exception on error
        helper.delete_vm(self.builder.provider_image.identifier_on_provider)

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_should_create_target_image() called on vSphere plugin - returning True')
        return True

    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        tdlobj = oz.TDL.TDL(xmlstring=template.xml, rootpw_required=self.app_config["tdl_require_root_pw"])
        if tdlobj.distro == "RHEL-5":
            merge_content = { "commands": [ { "name": "execute-module-script", "type": "raw" , "command": "/bin/sh /root/vsphere-module.sh" } ],
                              "files" : [ { "name": "/root/vsphere-module.sh", "type": "raw", "file": rhel5_module_script } ] }
            try:
                builder.os_plugin.add_cloud_plugin_content(merge_content)
            except:
                self.log.error("Failed to add RHEL-5 specific vSphere customization to cloud plugin tasks")
                raise

    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        self.log.info('builder_did_create_target_image() called in vSphere plugin')
        self.status="BUILDING"

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.target_image.identifier

        # TODO: More convenience vars - revisit
        self.template = template
        self.target = target
        self.builder = builder
        self.image = builder.target_image.data

        # This lets our logging helper know what image is being operated on
        self.active_image = self.builder.target_image

        self.tdlobj = oz.TDL.TDL(xmlstring=self.template.xml, rootpw_required=self.app_config["tdl_require_root_pw"])
        # Add in target specific content
        #TODO - URGENT - make this work again
        #self.add_target_content()
        # Oz assumes unique names - TDL built for multiple backends guarantees
        # they are not unique.  We don't really care about the name so just
        # force uniqueness
        #  Oz now uses the tdlobject name property directly in several places
        # so we must change it
        self.tdlobj.name = "factory-build-" + self.new_image_id

        # In contrast to our original builders, we enter the cloud plugins with a KVM file already
        # created as the base_image.  As a result, all the Oz building steps are gone (and can be found
        # in the OS plugin(s)

        # OS plugin has already provided the initial file for us to work with
        # which we can currently assume is a raw KVM compatible image

        # Add the cloud-info file
        self.modify_oz_filesystem()

        self.log.info("Transforming image for use on VMWare")
        self.vmware_transform_image()

        self.percent_complete=100
        self.status="COMPLETED"

    def vmware_transform_image(self):
        # On entry the image points to our generic KVM raw image
        # Convert to stream-optimized VMDK and then update the image property
        target_image = self.image + ".tmp.vmdk"
        self.log.debug("Converting raw kvm image (%s) to vmware stream-optimized image (%s)" % (self.image, target_image))
        convert_to_stream(self.image, target_image)
        self.log.debug("VMWare stream conversion complete")
        os.unlink(self.image)
        os.rename(self.image + ".tmp.vmdk", self.image)

    def modify_oz_filesystem(self):
        self.log.debug("Doing further Factory specific modification of Oz image")
        guestfs_handle = launch_inspect_and_mount(self.builder.target_image.data)
        remove_net_persist(guestfs_handle)
        create_cloud_info(guestfs_handle, self.target)
        shutdown_and_close(guestfs_handle)

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        self.log.info('push_image_to_provider() called in vSphere')

        # TODO: This is a convenience variable for refactoring - rename
        self.new_image_id = builder.provider_image.identifier

        self.tdlobj = oz.TDL.TDL(xmlstring=builder.target_image.template, rootpw_required=self.app_config["tdl_require_root_pw"])
        self.builder = builder
        self.active_image = self.builder.provider_image
        self.vmware_push_image_upload(target_image, provider, credentials)

    def vmware_push_image_upload(self, target_image_id, provider, credentials):
        # BuildDispatcher is now the only location for the logic to map a provider to its data and target
        provider_data = self.get_dynamic_provider_data(provider)
        if provider_data is None:
            raise ImageFactoryException("VMWare instance not found in XML or JSON provided")

        self.generic_decode_credentials(credentials, provider_data, "vsphere")

        # Image is always here and it is the target_image datafile
        input_image = self.builder.target_image.data

        # Example of some JSON for westford_esx
        # {"westford_esx": {"api-url": "https://vsphere.virt.bos.redhat.com/sdk", "username": "Administrator", "password": "changeme",
        #       "datastore": "datastore1", "network_name": "VM Network" } }

        vm_name = "factory-image-" + self.new_image_id
        helper = VSphereHelper(provider_data['api-url'], self.username, self.password)

        # Newer Oz versions introduce a configurable disk size in TDL
        # We must still detect that it is present and pass it in this call
        try:
            disksize=getattr(self.tdlobj, "disksize")
        except AttributeError:
            disksize = 10
        disksize_str = str(int(disksize)*1024*1024 + 2) + "KB"

        helper.create_vm(input_image, vm_name, provider_data['compute_resource'], provider_data['datastore'], 
                         disksize_str, [ { "network_name": provider_data['network_name'], "type": "VirtualE1000"} ], 
                         "512MB", 1, 'otherLinux64Guest')
        self.builder.provider_image.identifier_on_provider = vm_name
        self.builder.provider_account_identifier = self.username
        self.percent_complete = 100

    def generic_decode_credentials(self, credentials, provider_data, target):
        # convenience function for simple creds (rhev-m and vmware currently)
        doc = libxml2.parseDoc(credentials)

        self.username = None
        _usernodes = doc.xpathEval("//provider_credentials/%s_credentials/username" % (target))
        if len(_usernodes) > 0:
            self.username = _usernodes[0].content
        else:
            try:
                self.username = provider_data['username']
            except KeyError:
                raise ImageFactoryException("No username specified in config file or in push call")
        self.provider_account_identifier = self.username

        _passnodes = doc.xpathEval("//provider_credentials/%s_credentials/password" % (target))
        if len(_passnodes) > 0:
            self.password = _passnodes[0].content
        else:
            try:
                self.password = provider_data['password']
            except KeyError:
                raise ImageFactoryException("No password specified in config file or in push call")

        doc.freeDoc()

    def get_dynamic_provider_data(self, provider):
        # Get provider details for RHEV-M or VSphere
        # First try to interpret this as an ad-hoc/dynamic provider def
        # If this fails, try to find it in one or the other of the config files
        # If this all fails return None
        # We use this in the builders as well so I have made it "public"

        try:
            xml_et = fromstring(provider)
            return xml_et.attrib
        except Exception as e:
            self.log.debug('Testing provider for XML: %s' % e)
            pass

        try:
            jload = json.loads(provider)
            return jload
        except ValueError as e:
            self.log.debug('Testing provider for JSON: %s' % e)
            pass

        return None

    def abort(self):
        pass

########NEW FILE########
__FILENAME__ = VSphereHelper
#!/usr/bin/env python
# Copyright 2011 Jonathan Kinred
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at:
# 
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re
import sys
import time
import os
import pycurl
import logging
import urllib2
from psphere.client import Client
from psphere.errors import TemplateNotFoundError
from psphere.soap import VimFault
from time import sleep, time

logging.getLogger('suds').setLevel(logging.INFO)

class VSphereHelper:
    def __init__(self, url, username, password):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        if(url.startswith('http://') or url.startswith('https://')):
            server = urllib2.Request(url).get_host()
        else:
            server = url
        self.client = Client(server=server, username=username, password=password)

    def curl_progress(self, download_t, download_d, upload_t, upload_d):
        curtime=time()
        # TODO: Make poke frequency variable
        # 5 seconds isn't too much and it makes the status bar in the vSphere GUI look nice :-)
        if  (curtime - self.time_at_last_poke) >= 5:
            self.lease.HttpNfcLeaseProgress(percent = int(upload_d*100/upload_t))
            self.time_at_last_poke = time()

    def create_vm(self, imagefilename, name, compute_resource, datastore, disksize, nics,
                  memory, num_cpus, guest_id, host=None):
        """Create a virtual machine using the specified values.

        :param name: The name of the VM to create.
        :type name: str
        :param compute_resource: The name of a ComputeResource in which to \
                create the VM.
        :type compute_resource: str
        :param datastore: The name of the datastore on which to create the VM.
        :type datastore: str
        :param disksize: The size of the disk, specified in KB, MB or GB. e.g. \
                20971520KB, 20480MB, 20GB.
        :type disksize: str
        :param nics: The NICs to create, specified in a list of dict's which \
                contain a "network_name" and "type" key. e.g. \
                {"network_name": "VM Network", "type": "VirtualE1000"}
        :type nics: list of dict's
        :param memory: The amount of memory for the VM. Specified in KB, MB or \
                GB. e.g. 2097152KB, 2048MB, 2GB.
        :type memory: str
        :param num_cpus: The number of CPUs the VM will have.
        :type num_cpus: int
        :param guest_id: The vSphere string of the VM guest you are creating. \
                The list of VMs can be found at \
            http://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/index.html
        :type guest_id: str
        :param host: The name of the host (default: None), if you want to \
                provision the VM on a \ specific host.
        :type host: str

        """
        # Convenience variable
        client = self.client

        self.log.debug("Creating VM %s" % name)
        # If the host is not set, use the ComputeResource as the target
        if host is None:
            target = client.find_entity_view("ComputeResource",
                                          filter={"name": compute_resource})
            resource_pool = target.resourcePool
        else:
            target = client.find_entity_view("HostSystem", filter={"name": host})
            resource_pool = target.parent.resourcePool

        disksize_pattern = re.compile("^\d+[KMG]B")
        if disksize_pattern.match(disksize) is None:
            raise Exception("Disk size %s is invalid. Try \"12G\" or similar" % disksize)

        if disksize.endswith("GB"):
            disksize_kb = int(disksize[:-2]) * 1024 * 1024
        elif disksize.endswith("MB"):
            disksize_kb = int(disksize[:-2]) * 1024
        elif disksize.endswith("KB"):
            disksize_kb = int(disksize[:-2])
        else:
            raise Exception("Disk size %s is invalid. Try \"12G\" or similar" % disksize)

        memory_pattern = re.compile("^\d+[KMG]B")
        if memory_pattern.match(memory) is None:
            raise Exception("Memory size %s is invalid. Try \"12G\" or similar" % memory)

        if memory.endswith("GB"):
            memory_mb = int(memory[:-2]) * 1024
        elif memory.endswith("MB"):
            memory_mb = int(memory[:-2])
        elif memory.endswith("KB"):
            memory_mb = int(memory[:-2]) / 1024
        else:
            raise Exception("Memory size %s is invalid. Try \"12G\" or similar" % memory)

        # A list of devices to be assigned to the VM
        vm_devices = []

        # Create a disk controller
        controller = self.create_controller("VirtualLsiLogicController")
        vm_devices.append(controller)

        ds_to_use = None
        for ds in target.datastore:
            if ds.name == datastore:
                ds_to_use = ds
                break

        if ds_to_use is None:
            raise Exception("Could not find datastore on %s with name %s" %
                  (target.name, datastore))

        # Ensure the datastore is accessible and has enough space
        if ds_to_use.summary.accessible is not True:
            raise Exception("Datastore (%s) exists, but is not accessible" %
                  ds_to_use.summary.name)
        if ds_to_use.summary.freeSpace < disksize_kb * 1024:
            raise Exception("Datastore (%s) exists, but does not have sufficient"
                  " free space." % ds_to_use.summary.name)

        disk = self.create_disk(datastore=ds_to_use, disksize_kb=disksize_kb)
        vm_devices.append(disk)

        cdrom = self.create_cdrom(datastore=ds_to_use)
        vm_devices.append(cdrom)
        
        for nic in nics:
            nic_spec = self.create_nic(target, nic)
            if nic_spec is None:
                raise Exception("Could not create spec for NIC")

            # Append the nic spec to the vm_devices list
            vm_devices.append(nic_spec)

        vmfi = client.create("VirtualMachineFileInfo")
        vmfi.vmPathName = "[%s]" % ds_to_use.summary.name
        vm_config_spec = client.create("VirtualMachineConfigSpec")
        vm_config_spec.name = name
        vm_config_spec.memoryMB = memory_mb
        vm_config_spec.files = vmfi
        vm_config_spec.annotation = "Auto-provisioned by psphere"
        vm_config_spec.numCPUs = num_cpus
        vm_config_spec.guestId = guest_id
        vm_config_spec.deviceChange = vm_devices

        # Find the datacenter of the target
        if target.__class__.__name__ == "HostSystem":
            datacenter = target.parent.parent.parent
        else:
            datacenter = target.parent.parent

        importspec = client.create('VirtualMachineImportSpec')

        importspec.configSpec = vm_config_spec
        importspec.resPoolEntity = None

        lease = resource_pool.ImportVApp(spec = importspec, folder = datacenter.vmFolder)
        self.lease = lease

        # Lease takes a bit of time to initialize
        for i in range(1000):
            #print lease.error
            if lease.state == "ready":
                break
            if lease.state == "error":
                raise Exception("Our HttpNFCLease failed to initialize")
            sleep(5)
            lease.update_view_data(properties=["state"])

        #print "For debug and general info, here is the lease info"
        #pprint(lease.info)

        upload_url = None
        for url_candidate in lease.info.deviceUrl:
            if url_candidate['disk']:
                upload_url = str(url_candidate['url'])

        if not upload_url:
            raise Exception("Unable to extract disk upload URL from HttpNfcLease")

        self.log.debug("Extracted image upload URL (%s) from lease" % (upload_url))

        lease_timeout = lease.info.leaseTimeout
        self.time_at_last_poke = time()

        image_file = open(imagefilename)

        # Upload the image itself
        image_size = os.path.getsize(imagefilename)
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, upload_url)
        curl.setopt(pycurl.SSL_VERIFYPEER, 0)
        curl.setopt(pycurl.POST, 1)
        curl.setopt(pycurl.POSTFIELDSIZE, image_size)
        curl.setopt(pycurl.READFUNCTION, image_file.read)
        curl.setopt(pycurl.HTTPHEADER, ["User-Agent: Load Tool (PyCURL Load Tool)", "Content-Type: application/octet-stream"])
        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, self.curl_progress)
        curl.perform()
        curl.close()

        image_file.close()

        lease.HttpNfcLeaseComplete()

        vm = lease.info.entity

        vm.MarkAsTemplate()

    def create_nic(self, target, nic):
        # Convenience variable
        client = self.client
        """Return a NIC spec"""
        # Iterate through the networks and look for one matching
        # the requested name
        for network in target.network:
            if network.name == nic["network_name"]:
                net = network
                break
        else:
            return None

        # Success! Create a nic attached to this network
        backing = client.create("VirtualEthernetCardNetworkBackingInfo")
        backing.deviceName = nic["network_name"]
        backing.network = net

        connect_info = client.create("VirtualDeviceConnectInfo")
        connect_info.allowGuestControl = True
        connect_info.connected = False
        connect_info.startConnected = True

        new_nic = client.create(nic["type"]) 
        new_nic.backing = backing
        new_nic.key = 2
        # TODO: Work out a way to automatically increment this
        new_nic.unitNumber = 1
        new_nic.addressType = "generated"
        new_nic.connectable = connect_info

        nic_spec = client.create("VirtualDeviceConfigSpec")
        nic_spec.device = new_nic
        nic_spec.fileOperation = None
        operation = client.create("VirtualDeviceConfigSpecOperation")
        nic_spec.operation = (operation.add)

        return nic_spec

    def create_controller(self, controller_type):
        # Convenience variable
        client = self.client
        controller = client.create(controller_type)
        controller.key = 0
        controller.device = [0]
        controller.busNumber = 0,
        controller.sharedBus = client.create("VirtualSCSISharing").noSharing
        spec = client.create("VirtualDeviceConfigSpec")
        spec.device = controller
        spec.fileOperation = None
        spec.operation = client.create("VirtualDeviceConfigSpecOperation").add
        return spec

    def create_disk(self, datastore, disksize_kb):
        # Convenience variable
        client = self.client
        backing = client.create("VirtualDiskFlatVer2BackingInfo")
        backing.datastore = None
        backing.diskMode = "persistent"
        backing.fileName = "[%s]" % datastore.summary.name
        backing.thinProvisioned = True

        disk = client.create("VirtualDisk")
        disk.backing = backing
        disk.controllerKey = 0
        disk.key = 0
        disk.unitNumber = 0
        disk.capacityInKB = disksize_kb

        disk_spec = client.create("VirtualDeviceConfigSpec")
        disk_spec.device = disk
        file_op = client.create("VirtualDeviceConfigSpecFileOperation")
        disk_spec.fileOperation = file_op.create
        operation = client.create("VirtualDeviceConfigSpecOperation")
        disk_spec.operation = operation.add

        return disk_spec

    def create_cdrom(self, datastore):
        # Convenience variable
        client = self.client
        # This creates what is essentially a virtual CDROM drive with no disk in it
        # Adding this greatly simplifies the process of adding a custom ISO via deltacloud
        connectable = client.create('VirtualDeviceConnectInfo')
        connectable.allowGuestControl = True
        connectable.connected = True
        connectable.startConnected = True
        #connectable.status = None

        backing = client.create('VirtualCdromIsoBackingInfo')
        backing.datastore = None
        backing.fileName = '[%s]' % datastore.summary.name

        cdrom = client.create('VirtualCdrom')
        cdrom.connectable = connectable
        cdrom.backing = backing
        # 201 is the second built in IDE controller
        cdrom.controllerKey = 201
        cdrom.key = 10
        cdrom.unitNumber = 0

        cdrom_spec = client.create('VirtualDeviceConfigSpec')
        cdrom_spec.fileOperation = None
        cdrom_spec.device = cdrom
        operation = client.create('VirtualDeviceConfigSpecOperation')
        cdrom_spec.operation = operation.add

        return cdrom_spec

    def delete_vm(self, name):
        vm = self.client.find_entity_view("VirtualMachine", filter={"name":name})
        if not vm:
            raise Exception("Cannot find VM with name (%s)" % (name))

        vmdestroy = vm.Destroy_Task()
        for i in range(300):
            if not (vmdestroy.info.state in ["queued", "running"]):
                break
            sleep(1)
            vmdestroy.update_view_data(properties=["info"])

        if vmdestroy.info.state != "success":
            # TODO: Return the reason - this is part of the rather complex Task object
            raise Exception("Failed to delete VM (%s) in timeout period" % (name))

########NEW FILE########
__FILENAME__ = ApplicationConfiguration
# encoding: utf-8

#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import sys
import os
import os.path
import argparse
import json
import logging
import props
from Singleton import Singleton
from imgfac.Version import VERSION as VERSION
from urlgrabber import urlopen


class ApplicationConfiguration(Singleton):
    configuration = props.prop("_configuration", "The configuration property.")

    def _singleton_init(self, configuration = None):
        super(ApplicationConfiguration, self)._singleton_init()
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.jeos_images = { }

        if configuration:
            if not isinstance(configuration, dict):
                raise Exception("ApplicationConfiguration configuration argument must be a dict")
            self.log.debug("ApplicationConfiguration passed a dictionary - ignoring any local config files including JEOS configs")
            self.configuration = configuration
        else:
            self.configuration = self.__parse_arguments()
            self.__parse_jeos_images()

        if not 'debug' in self.configuration:
            # This most likely means we are being used as a module/library and are not running CLI or daemon
            self.configuration['debug'] = False

        if not 'secondary' in self.configuration:
            # We use this in the non-daemon context so it needs to be set
            # TODO: Something cleaner?
            self.configuration['secondary'] = False

    def __init__(self, configuration = None):
        pass

    def __new_argument_parser(self, appname):
        main_description = """Image Factory is an application for creating system images for use on public and private clouds."""

        argparser = argparse.ArgumentParser(description=main_description, prog=appname)
        argparser.add_argument('--version', action='version', default=argparse.SUPPRESS, version=VERSION, help='Show the version number and exit')
        argparser.add_argument('--verbose', action='store_true', default=False, help='Set verbose logging.')
        argparser.add_argument('--config', default='/etc/imagefactory/imagefactory.conf', help='Configuration file to use. (default: %(default)s)')
        argparser.add_argument('--imgdir', default='/tmp', help='Build image files in location specified. (default: %(default)s)')
        argparser.add_argument('--timeout', type=int, default=3600, help='Set the timeout period for image building in seconds. (default: %(default)s)')
        argparser.add_argument('--tmpdir', default='/tmp', help='Use the specified location for temporary files.  (default: %(default)s)')
        argparser.add_argument('--plugins', default='/etc/imagefactory/plugins.d', help='Plugin directory. (default: %(default)s)')

        group_ec2 = argparser.add_argument_group(title='EC2 settings')
        group_ec2.add_argument('--ec2-32bit-util', default = 'm1.small', help='Instance type to use when launching a 32 bit utility instance')
        group_ec2.add_argument('--ec2-64bit-util', default = 'm1.large', help='Instance type to use when launching a 64 bit utility instance')

        if(appname == 'imagefactoryd'):
            debug_group = argparser.add_mutually_exclusive_group()
            debug_group.add_argument('--debug', action='store_true', default=False, help='Set really verbose logging for debugging.')
            debug_group.add_argument('--nodebug', dest='debug', action='store_false', help='Turn off the default verbose CLI logging')
            argparser.add_argument('--foreground', action='store_true', default=False, help='Stay in the foreground and avoid launching a daemon. (default: %(default)s)')
            group_rest = argparser.add_argument_group(title='REST service options')
            group_rest.add_argument('--port', type=int, default=8075, help='Port to attach the RESTful http interface to. (default: %(default)s)')
            group_rest.add_argument('--address', default='0.0.0.0', help='Interface address to listen to. (default: %(default)s)')
            group_rest.add_argument('--no_ssl', action='store_true', default=False, help='Turn off SSL. (default: %(default)s)')
            group_rest.add_argument('--ssl_pem', default='*', help='PEM certificate file to use for HTTPS access to the REST interface. (default: A transient certificate is generated at runtime.)')
            group_rest.add_argument('--no_oauth', action='store_true', default=False, help='Use 2 legged OAuth to protect the REST interface. (default: %(default)s)')
            group_rest.add_argument('--secondary', action='store_true', default=False, help='Operate as a secondary/helper factory. (default: %(default)s)')
        elif(appname == 'imagefactory'):
            debug_group = argparser.add_mutually_exclusive_group()
            debug_group.add_argument('--debug', action='store_true', default=True, help='Set really verbose logging for debugging.')
            debug_group.add_argument('--nodebug', dest='debug', action='store_false', help='Turn off the default verbose CLI logging')
            argparser.add_argument('--output', choices=('log', 'json'), default='log', help='Choose between log or json output. (default: %(default)s)')
            argparser.add_argument('--raw', action='store_true', default=False, help='Turn off pretty printing.')
            subparsers = argparser.add_subparsers(title='commands', dest='command')
            template_help = 'A file containing the image template or component outline, compatible with the TDL schema (http://imgfac.org/documentation/tdl).'

            cmd_base = subparsers.add_parser('base_image', help='Build a generic image.')
            cmd_base.add_argument('template', type=argparse.FileType(), help=template_help)
            self.__add_param_arguments(cmd_base)

            cmd_target = subparsers.add_parser('target_image', help='Customize an image for a given cloud.')
            cmd_target.add_argument('target', help='The name of the target cloud for which to customize the image.')
            target_group = cmd_target.add_mutually_exclusive_group(required=True)
            target_group.add_argument('--id', help='The uuid of the BaseImage to customize.')
            target_group.add_argument('--template', type=argparse.FileType(), help=template_help)
            self.__add_param_arguments(cmd_target)

            cmd_provider = subparsers.add_parser('provider_image', help='Push an image to a cloud provider.')
            cmd_provider.add_argument('target', help='The target type of the given cloud provider')
            cmd_provider.add_argument('provider', help="A file containing the cloud provider description or a string literal starting with '@' such as '@ec2-us-east-1'.")
            cmd_provider.add_argument('credentials', type=argparse.FileType(), help='A file containing the cloud provider credentials')
            provider_group = cmd_provider.add_mutually_exclusive_group(required=True)
            provider_group.add_argument('--id', help='The uuid of the TargetImage to push.')
            provider_group.add_argument('--template', type=argparse.FileType(), help=template_help)
            self.__add_param_arguments(cmd_provider)
            cmd_provider.add_argument('--snapshot', action='store_true', default=False, help='Use snapshot style building. (default: %(default)s)')

            cmd_list = subparsers.add_parser('images', help='List images of a given type or get details of an image.')
            cmd_list.add_argument('fetch_spec', help='JSON formatted string of key/value pairs')

            cmd_delete = subparsers.add_parser('delete', help='Delete an image.')
            cmd_delete.add_argument('id', help='UUID of the image to delete')
            cmd_delete.add_argument('--provider', help="A file containing the cloud provider description or a string literal starting with '@' such as '@ec2-us-east-1'.")
            cmd_delete.add_argument('--credentials', type=argparse.FileType(), help='A file containing the cloud provider credentials')
            cmd_delete.add_argument('--target', help='The name of the target cloud for which to customize the image.')
            self.__add_param_arguments(cmd_delete)

            cmd_plugins = subparsers.add_parser('plugins', help='List active plugins or get details of a specific plugin.')
            cmd_plugins.add_argument('--id')
        return argparser

    def __add_param_arguments(self, parser):
        # We do this for all three image types so lets make it a util function
        parameters_help = 'An optional JSON file containing additional parameters to pass to the builders.'
        parser.add_argument('--parameters', type=argparse.FileType(), help=parameters_help)
        parser.add_argument('--parameter', nargs=2, action='append', help='A parameter name and the literal value to assign it.  Can be used more than once.')
        parser.add_argument('--file-parameter', nargs=2, action='append', help='A parameter name and a file to insert into it.  Can be used more than once.')

    def __parse_arguments(self):
        appname = sys.argv[0].rpartition('/')[2]
        argparser = self.__new_argument_parser(appname)
        if((appname == 'imagefactory') and (len(sys.argv) == 1)):
            argparser.print_help()
            sys.exit()
        configuration = argparser.parse_args()
        if (os.path.isfile(configuration.config)):
            try:
                def dencode(a_dict, encoding='ascii'):
                    new_dict = {}
                    for k,v in a_dict.items():
                        ek = k.encode(encoding)
                        if(isinstance(v, unicode)):
                            new_dict[ek] = v.encode(encoding)
                        elif(isinstance(v, dict)):
                            new_dict[ek] = dencode(v)
                        else:
                            new_dict[ek] = v
                    return new_dict

                config_file = open(configuration.config)
                uconfig = json.load(config_file)
                config_file.close()
                defaults = dencode(uconfig)
                argparser.set_defaults(**defaults)
                configuration = argparser.parse_args()
            except Exception, e:
                self.log.exception(e)
        return configuration.__dict__

    def __add_jeos_image(self, image_detail):
        log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        # our multi-dimensional-dict has the following keys
        # target - provider - os - version - arch - provider_image_id - user - cmd_prefix
        for i in range(8):
            try:
                image_detail[i] = image_detail[i].strip()
            except IndexError:
                image_detail.append(None)

        (target, provider, os, version, arch, provider_image_id, user, cmd_prefix) = image_detail
        if not (target in self.jeos_images):
            self.jeos_images[target] = {}
        if not (provider in self.jeos_images[target]):
            self.jeos_images[target][provider] = {}
        if not (os in self.jeos_images[target][provider]):
            self.jeos_images[target][provider][os] = {}
        if not (version in self.jeos_images[target][provider][os]):
            self.jeos_images[target][provider][os][version] = {}
        if arch in self.jeos_images[target][provider][os][version]:
            log.warning("JEOS image defined more than once for %s - %s - %s - %s - %s" % (target, provider, os, version, arch))
            log.warning("Replacing (%s) with (%s)" % (self.jeos_images[target][provider][os][version][arch], provider_image_id))

        self.jeos_images[target][provider][os][version][arch] = {'img_id':provider_image_id,
                                                                 'user':user,
                                                                 'cmd_prefix':cmd_prefix}

    def __parse_jeos_images(self):
        log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        config_urls = self.configuration['jeos_config']
        # Expand directories from the config and url-ify files
        # Read inlist - replace directories with their contents
        nextlist = []
        for path in config_urls:
            if os.path.isdir(path):
                for filename in os.listdir(path):
                    fullname = os.path.join(path, filename)
                    if os.path.isfile(fullname):
                        nextlist.append(fullname)
            else:
                nextlist.append(path)

        # Read nextlist - replace files with file:// URLs
        finalist = []
        for path in nextlist:
            if os.path.isfile(path):
                finalist.append("file://" + path)
            else:
                finalist.append(path)

        for url in finalist:
            try:
                filehandle = urlopen(str(url))
                line = filehandle.readline().strip()
            except:
                log.warning("Failed to open JEOS URL (%s)" % url)
                continue
            line_number = 1

            while line:
                # Lines that start with '#' are a comment
                if line[0] == "#":
                    pass
                # Lines that are zero length are whitespace
                elif len(line.split()) == 0:
                    pass
                else:
                    image_detail = line.split(":")
                    if len(image_detail) >= 6:
                        self.__add_jeos_image(image_detail)
                    else:
                        log.warning("Failed to parse line %d in JEOS config (%s):\n%s" % (line_number, url, line))

                line = filehandle.readline()
                line_number += 1

            filehandle.close()

########NEW FILE########
__FILENAME__ = BaseImage
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from PersistentImage import PersistentImage
#from props import prop


METADATA = ( )

class BaseImage(PersistentImage):
    """ TODO: Docstring for BaseImage  """

    def __init__(self, image_id=None):
        """ TODO: Fill me in
        
        @param template TODO
        """
        super(BaseImage, self).__init__(image_id)
        self.template = None

    def metadata(self):
        self.log.debug("Getting metadata in class (%s) my metadata is (%s)" % (self.__class__, METADATA))
        return frozenset(METADATA + super(self.__class__, self).metadata())

########NEW FILE########
__FILENAME__ = BuildDispatcher
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
from imgfac.Singleton import Singleton
from Builder import Builder
from imgfac.NotificationCenter import NotificationCenter
from threading import BoundedSemaphore

class BuildDispatcher(Singleton):

    def _singleton_init(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.builders = dict()
        self.builders_lock = BoundedSemaphore()
        NotificationCenter().add_observer(self, 'handle_state_change', 'image.status')

    def handle_state_change(self, notification):
        status = notification.user_info['new_status']
        if(status in ('COMPLETED', 'FAILED', 'DELETED', 'DELETEFAILED')):
            self.builders_lock.acquire()
            image_id = notification.sender.identifier
            if(image_id in self.builders):
                del self.builders[image_id]
                self.log.debug('Removed builder from BuildDispatcher on notification from image %s: %s' % (image_id, status))
            self.builders_lock.release()

    def builder_for_base_image(self, template, parameters=None):
        builder = Builder()
        builder.build_image_from_template(template, parameters=parameters)
        self.builders_lock.acquire()
        try:
            self.builders[builder.base_image.identifier] = builder
        finally:
            self.builders_lock.release()
        return builder

    def builder_for_target_image(self, target, image_id=None, template=None, parameters=None):
        builder = Builder()
        builder.customize_image_for_target(target, image_id, template, parameters)
        self.builders_lock.acquire()
        try:
            self.builders[builder.target_image.identifier] = builder
        finally:
            self.builders_lock.release()
        return builder

    def builder_for_provider_image(self, provider, credentials, target, image_id=None, template=None, parameters=None, my_image_id=None):
        builder = Builder()
        builder.create_image_on_provider(provider, credentials, target, image_id, template, parameters, my_image_id)
        self.builders_lock.acquire()
        try:
            self.builders[builder.provider_image.identifier] = builder
        finally:
            self.builders_lock.release()
        return builder

########NEW FILE########
__FILENAME__ = Builder
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import uuid
import logging
from threading import Thread
from props import prop
from NotificationCenter import NotificationCenter
from Template import Template
from PluginManager import PluginManager
from ApplicationConfiguration import ApplicationConfiguration
from PersistentImageManager import PersistentImageManager
from BaseImage import BaseImage
from TargetImage import TargetImage
from ProviderImage import ProviderImage
from ImageFactoryException import ImageFactoryException
from CallbackWorker import CallbackWorker
from time import sleep

class Builder(object):
    """ TODO: Docstring for Builder  """

##### PROPERTIES
    os_plugin = prop("_os_plugin")
    cloud_plugin = prop("_cloud_plugin")
    base_image = prop("_base_image")
    target_image = prop("_target_image")
    provider_image = prop("_provider_image")
    image_metadata = prop("_image_metadata")

##### INITIALIZER
    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.app_config = ApplicationConfiguration().configuration
        self.notification_center = NotificationCenter()
        self.pim = PersistentImageManager.default_manager()
        self._os_plugin = None
        self._cloud_plugin = None
        self._base_image = None
        self._base_image_cbws = [ ]
        self._target_image = None
        self._target_image_cbws = [ ]
        self._provider_image = None
        self._provider_image_cbws = [ ]
        self._deletion_cbws = []
        self.base_thread = None
        self.target_thread = None
        self.push_thread = None
        self.snapshot_thread = None
        try:
            from imgfac.secondary.SecondaryDispatcher import SecondaryDispatcher
            from imgfac.secondary.SecondaryPlugin import SecondaryPlugin
            self.secondary_dispatcher = SecondaryDispatcher()
        except:
            self.log.debug("No SecondaryDispatcher present - Use of secondary factories is not enabled")
            self.secondary_dispatcher = None
    

#####  SETUP CALLBACKS
    def _init_callback_workers(self, image, callbacks, callbackworkers):
        for callback_url in callbacks:
            self.log.debug("Seeting up callback worker for (%s)" % (callback_url))
            worker = CallbackWorker(callback_url)
            worker.start()
            callbackworkers.append(worker)
            self.notification_center.add_observer(worker, 'status_notifier', 'image.status', sender = image)

    def _shutdown_callback_workers(self, image, callbackworkers):
        for worker in callbackworkers:
            self.notification_center.remove_observer(worker, 'status_notifier', 'image.status', sender = image)
            worker.shut_down()

#####  PENDING BUILD HELPERS
    def _wait_for_final_status(self, image):
        image_id = image.identifier
        self.log.debug("Waiting for image of type (%s) and id (%s) to enter a final status" % (str(type(image)), image_id ) )
        # Wait forever - Short of a factory crash, we have timeouts elsewhere that should ensure
        #                that the pending images eventually hit success or failure
        while(True):
            # Our local image object isn't necessarily the one that is being actively updated
            # In fact, we know it isn't.  It has been created out of a PIM retrieval.
            # To update its metadata, we just re-fetch it.
            image = self.pim.image_with_id(image_id)
            if image.status not in [ 'NEW','PENDING' ]:
                self.log.debug("Image of type (%s) entered final status of (%s)" % (str(type(image)), image.status) )
                return image
            sleep(5)

#####  BUILD IMAGE
    def build_image_from_template(self, template, parameters=None):
        """
        TODO: Docstring for build_image_from_template

        @param template TODO 

        @return TODO
        """
        # Create what is essentially an empty BaseImage here
        self.base_image = BaseImage()
        self.base_image.template = template
        if parameters:
            self.base_image.parameters = parameters
        self.pim.add_image(self.base_image)
        if parameters and ('callbacks' in parameters):
            # This ensures we have workers in place before any potential state changes
            self._init_callback_workers(self.base_image, parameters['callbacks'], self._base_image_cbws)

        thread_name = str(uuid.uuid4())[0:8]
        thread_kwargs = {'template':template, 'parameters':parameters}
        self.base_thread = Thread(target=self._build_image_from_template, name=thread_name, args=(), kwargs=thread_kwargs)
        self.base_thread.start()

    def _build_image_from_template(self, template, parameters=None):
        try:
            template = template if(isinstance(template, Template)) else Template(template)
            plugin_mgr = PluginManager(self.app_config['plugins'])
            self.os_plugin = plugin_mgr.plugin_for_target((template.os_name, template.os_version, template.os_arch))
            self.base_image.status="BUILDING"
            self.os_plugin.create_base_image(self, template, parameters)
            # This implies a convention where the plugin can never dictate completion and must indicate failure
            # via an exception
            self.base_image.status_detail = { 'activity': 'Base Image build complete', 'error':None }
            self.base_image.status="COMPLETE"
            self.pim.save_image(self.base_image)
        except Exception, e:
            self.base_image.status_detail = {'activity': 'Base Image build failed with exception.', 'error': str(e)}
            self.base_image.status="FAILED"
            self.pim.save_image(self.base_image)
            self.log.error("Exception encountered in _build_image_from_template thread")
            self.log.exception(e)
        finally:
            # We only shut the workers down after a known-final state change
            self._shutdown_callback_workers(self.base_image, self._base_image_cbws)

##### CUSTOMIZE IMAGE FOR TARGET
    def customize_image_for_target(self, target, image_id=None, template=None, parameters=None):
        """
        TODO: Docstring for customize_image_for_target

        @param factory_image TODO
        @param target TODO 
        @param target_params TODO

        @return TODO
        """

        self.target_image = TargetImage()
        self.target_image.target = target
        self.target_image.base_image_id = image_id
        self.target_image.template = template
        if parameters:
            self.target_image.parameters = parameters
        self.pim.add_image(self.target_image)        
        if parameters and ('callbacks' in parameters):
            # This ensures we have workers in place before any potential state changes
            self._init_callback_workers(self.target_image, parameters['callbacks'], self._target_image_cbws)

        if(image_id and (not template)):
            self.base_image = self.pim.image_with_id(image_id)
            template = self.base_image.template
            self.target_image.template = template
        elif template:
            self.build_image_from_template(template, parameters)
            # Populate the base_image property of our target image correctly
            # (The ID value is always available immediately after the call above)
            image_id = self.base_image.identifier
            self.target_image.base_image_id = self.base_image.identifier
        elif template and image_id:
            raise ImageFactoryException("Must specify either a template or a BaseImage ID, not both")
        else:
            raise ImageFactoryException("Asked to create a TargetImage without a BaseImage or a template")

        # Both base_image and target_image exist at this point and have IDs and status
        # We can now launch our thread and return to the caller
        
        thread_name = str(uuid.uuid4())[0:8]
        thread_kwargs = {'target':target, 'image_id':image_id, 'template':template, 'parameters':parameters}
        self.target_thread = Thread(target=self._customize_image_for_target, name=thread_name, args=(), kwargs=thread_kwargs)
        self.target_thread.start()

    def _customize_image_for_target(self, target, image_id=None, template=None, parameters=None):
        try:
            # If there is an ongoing base image build that we started, wait for it to finish
            if self.base_thread:
                self.target_image.status="PENDING"
                threadname=self.base_thread.getName()
                self.log.debug("Waiting for our BaseImage builder thread (%s) to finish" % (threadname))
                self.base_thread.join()
                self.log.debug("BaseImage builder thread (%s) finished - continuing with TargetImage tasks" % (threadname))

            # If we were called against an ongoing base_image build, wait for a terminal status on it
            if self.base_image.status in [ "NEW", "PENDING" ]:
                self.target_image.status="PENDING"
                self.base_image = self._wait_for_final_status(self.base_image)

            if self.base_image.status == "FAILED":
                raise ImageFactoryException("The BaseImage (%s) for our TargetImage has failed its build.  Cannot continue." % (self.base_image.identifier))

            if self.base_image.status != "COMPLETE":
                raise ImageFactoryException("Got to TargetImage build step with a BaseImage status of (%s).  This should never happen.  Aborting." % (self.base_image.status))

            # Only at this point can we be sure that our base_image has icicle associated with it
            self.target_image.icicle = self.base_image.icicle

            template = template if(isinstance(template, Template)) else Template(template)

            plugin_mgr = PluginManager(self.app_config['plugins'])

            # It's possible this has already been set by the base_image creation above
            if not self.os_plugin:
                self.os_plugin = plugin_mgr.plugin_for_target((template.os_name, template.os_version, template.os_arch))

            self.cloud_plugin = plugin_mgr.plugin_for_target(target)
            if not self.cloud_plugin:
                self.log.warn("Unable to find cloud plugin for target (%s)" % (target))

            self.target_image.status = "BUILDING"
            if(hasattr(self.cloud_plugin, 'builder_should_create_target_image')):
                _should_create = self.cloud_plugin.builder_should_create_target_image(self, target, image_id, template, parameters)
            else:
                _should_create = True
            if(_should_create and hasattr(self.cloud_plugin, 'builder_will_create_target_image')):
                self.cloud_plugin.builder_will_create_target_image(self, target, image_id, template, parameters)
            if(_should_create):
                if(hasattr(self.os_plugin, 'create_target_image')):
                    self.os_plugin.create_target_image(self, target, image_id, parameters)
                if(hasattr(self.cloud_plugin, 'builder_did_create_target_image')):
                    self.cloud_plugin.builder_did_create_target_image(self, target, image_id, template, parameters)
            self.target_image.status_detail = { 'activity': 'Target Image build complete', 'error':None }
            self.target_image.status = "COMPLETE"
            self.pim.save_image(self.target_image)
        except Exception, e:
            self.target_image.status_detail={'activity': 'Target Image build failed with exception', 'error': str(e)}
            self.target_image.status = "FAILED"
            self.pim.save_image(self.target_image)
            self.log.error("Exception encountered in _customize_image_for_target thread")
            self.log.exception(e)
        finally:
            # We only shut the workers down after a known-final state change
            self._shutdown_callback_workers(self.target_image, self._target_image_cbws)

##### CREATE PROVIDER IMAGE
    def create_image_on_provider(self, provider, credentials, target, image_id=None, template=None, parameters=None, my_image_id = None):
        if(parameters and parameters.get('snapshot', False)):
            self.snapshot_image(provider, credentials, target, image_id, template, parameters, my_image_id)
        else:
            self.push_image_to_provider(provider, credentials, target, image_id, template, parameters, my_image_id)

##### PUSH IMAGE TO PROVIDER
    def push_image_to_provider(self, provider, credentials, target, image_id, template, parameters, my_image_id):
        """
        TODO: Docstring for push_image_to_provider

        @param image TODO
        @param provider TODO
        @param credentials TODO
        @param provider_params TODO 

        @return TODO
        """

        # If operating as a secondary we will have the provider_image ID dictated to us - otherwise it is None and it is created
        self.provider_image = ProviderImage(image_id = my_image_id) 
        self.provider_image.provider = provider
        self.provider_image.credentials = credentials
        self.provider_image.target_image_id = image_id
        self.provider_image.template = template
        self.pim.add_image(self.provider_image)
        if parameters and ('callbacks' in parameters):
            # This ensures we have workers in place before any potential state changes
            self._init_callback_workers(self.provider_image, parameters['callbacks'], self._provider_image_cbws)

        if(image_id and (not template)):
            self.target_image = self.pim.image_with_id(image_id)
            if not self.target_image:
                raise ImageFactoryException("Unable to retrieve target image with id (%s) from storage" % (image_id))
            # If we are being called as a secondary do not try to look up the base image
            if not my_image_id:
                self.base_image = self.pim.image_with_id(self.target_image.base_image_id)
                if not self.base_image:
                    raise ImageFactoryException("Unable to retrieve base image with id (%s) from storage" % (image_id))
            template = self.target_image.template
            self.provider_image.template = template
        elif template and image_id:
            raise ImageFactoryException("Must specify either a template or a TargetImage ID, not both")
        elif template:
            self.customize_image_for_target(target=target , image_id=None, template=template, parameters=parameters)
            # Populate the target_image value of our provider image properly
            # (The ID value is always available immediately after the call above)
            # self.base_image is created in cascading fashion from the above call
            image_id = self.target_image.identifier
            self.provider_image.target_image_id = self.target_image.identifier
        else:
            raise ImageFactoryException("Asked to create a ProviderImage without a TargetImage or a template")

        thread_name = str(uuid.uuid4())[0:8]
        thread_kwargs = {'provider':provider, 'credentials':credentials, 'target':target, 'image_id':image_id, 'template':template, 'parameters':parameters}
        self.push_thread = Thread(target=self._push_image_to_provider, name=thread_name, args=(), kwargs=thread_kwargs)
        self.push_thread.start()

    def _push_image_to_provider(self, provider, credentials, target, image_id, template, parameters):
        try:
            # If there is an ongoing target_image build that we started, wait for it to finish
            if self.target_thread:
                self.provider_image.status = "PENDING"
                threadname=self.target_thread.getName()
                self.log.debug("Waiting for our TargetImage builder thread (%s) to finish" % (threadname))
                self.target_thread.join()
                self.log.debug("TargetImage builder thread (%s) finished - continuing with ProviderImage tasks" % (threadname))

            # If we were called against an ongoing target_image build, wait for a terminal status on it
            if self.target_image.status in [ "NEW", "PENDING" ]:
                self.provider_image.status = "PENDING"
                self.target_image = self._wait_for_final_status(self.target_image) 

            if self.target_image.status == "FAILED":
                raise ImageFactoryException("The TargetImage (%s) for our ProviderImage has failed its build.  Cannot continue." % (self.target_image.identifier))

            if self.target_image.status != "COMPLETE":
                raise ImageFactoryException("Got to ProviderImage build step with a TargetImage status of (%s).  This should never happen.  Aborting." % (self.target_image.status))

            # Only at this point can we be sure that our target_image has icicle associated with it
            self.provider_image.icicle = self.target_image.icicle

            template = template if(isinstance(template, Template)) else Template(template)

            if not self.app_config['secondary'] and self.secondary_dispatcher:
                secondary = self.secondary_dispatcher.get_secondary(target, provider)
            else:
                # Do not allow nesting of secondaries and do not try to use the dispatcher if it is not present
                secondary = None

            if secondary:
                # NOTE: This may overwrite the cloud_plugin that was used to create the target_image
                #       This is expected and is correct
                self.cloud_plugin = SecondaryPlugin(SecondaryDispatcher().get_helper(secondary))
            else:
                plugin_mgr = PluginManager(self.app_config['plugins'])
                if not self.cloud_plugin:
                    self.cloud_plugin = plugin_mgr.plugin_for_target(target)
            self.provider_image.status="BUILDING"
            self.cloud_plugin.push_image_to_provider(self, provider, credentials, target, image_id, parameters)
            self.provider_image.status_detail = { 'activity': 'Provider Image build complete', 'error':None }
            self.provider_image.status="COMPLETE"
            self.pim.save_image(self.provider_image)
        except Exception, e:
            self.provider_image.status_detail={'activity': 'Provider Image build failed with exception', 'error': str(e)}
            self.provider_image.status="FAILED"
            self.pim.save_image(self.provider_image)
            self.log.error("Exception encountered in _push_image_to_provider thread")
            self.log.exception(e)
        finally:
            # We only shut the workers down after a known-final state change
            self._shutdown_callback_workers(self.provider_image, self._provider_image_cbws)

##### SNAPSHOT IMAGE
    def snapshot_image(self, provider, credentials, target, image_id, template, parameters, my_image_id):
        """
        TODO: Docstring for snapshot_image
        
        @param template TODO
        @param target TODO
        @param provider TODO
        @param credentials TODO
        @param snapshot_params TODO

        @return TODO
        """

        # If operating as a secondary we will have the provider_image ID dictated to us - otherwise it is None and it is created
        self.provider_image = ProviderImage(image_id = my_image_id)
        self.provider_image.provider = provider
        self.provider_image.credentials = credentials
        self.provider_image.target_image_id = image_id
        self.provider_image.template = template
        self.pim.add_image(self.provider_image)
        if parameters and ('callbacks' in parameters):
            # This ensures we have workers in place before any potential state changes
            self._init_callback_workers(self.provider_image, parameters['callbacks'], self._provider_image_cbws)

        if not template:
            raise ImageFactoryException("Must specify a template when requesting a snapshot-style build")

        thread_name = str(uuid.uuid4())[0:8]
        thread_kwargs = {'provider':provider, 'credentials':credentials, 'target':target, 'image_id':image_id, 'template':template, 'parameters':parameters}
        self.snapshot_thread = Thread(target=self._snapshot_image, name=thread_name, args=(), kwargs=thread_kwargs)
        self.snapshot_thread.start()

    def _snapshot_image(self, provider, credentials, target, image_id, template, parameters):
        try:
            if not self.app_config['secondary'] and self.secondary_dispatcher:
                secondary = self.secondary_dispatcher.get_secondary(target, provider)
            else:
                # Do not allow nesting of secondaries and do not try to use the dispatcher if it is not present
                secondary = None

            if secondary:
                self.cloud_plugin = SecondaryPlugin(SecondaryDispatcher().get_helper(secondary))
            else:    
                plugin_mgr = PluginManager(self.app_config['plugins'])
                self.cloud_plugin = plugin_mgr.plugin_for_target(target)
            self.provider_image.status="BUILDING"
            self.cloud_plugin.snapshot_image_on_provider(self, provider, credentials, target, template, parameters)
            self.provider_image.status_detail = { 'activity': 'Provider Image build complete', 'error':None }
            self.provider_image.status="COMPLETE"
            self.pim.save_image(self.provider_image)
        except Exception, e:
            self.provider_image.status_detail = {'activity': 'Provider Image build failed with exception',
                                                 'error': str(e)}
            self.provider_image.status="FAILED"
            self.pim.save_image(self.provider_image)
            self.log.error("Exception encountered in _snapshot_image thread")
            self.log.exception(e)
        finally:
            # We only shut the workers down after a known-final state change
            self._shutdown_callback_workers(self.provider_image, self._provider_image_cbws)

##### DELETE IMAGE
    def delete_image(self, provider, credentials, target, image_object, parameters):
        """
        Delete an image of any type - We only need plugin-specific methods to delete ProviderImages
        Both TargetImages and BaseImages can be deleted directly at the PersistentImageManager layer only.
        
        @param provider - XML or JSON provider definition - None if not a ProviderImage
        @param credentials - Credentials for the given provider - None if not a ProviderImage
        @param target - Target type if applicable - None if not
        @param image_object - Already-retrieved and populated PersistentImage object
        @param parameters TODO

        @return TODO
        """
        if parameters and ('callbacks' in parameters):
            # This ensures we have workers in place before any potential state changes
            self._init_callback_workers(image_object, parameters['callbacks'], self._deletion_cbws)

        thread_name = str(uuid.uuid4())[0:8]
        thread_kwargs = {'provider':provider, 'credentials':credentials, 'target':target, 'image_object':image_object, 'parameters':parameters}
        self.delete_thread = Thread(target=self._delete_image, name=thread_name, args=(), kwargs=thread_kwargs)
        self.delete_thread.start()


    def _delete_image(self, provider, credentials, target, image_object, parameters):
        try:
            image_object.status = "DELETING"
            if type(image_object).__name__ == "ProviderImage":
                self.provider_image = image_object
                plugin_mgr = PluginManager(self.app_config['plugins'])
                self.cloud_plugin = plugin_mgr.plugin_for_target(target)
                self.cloud_plugin.delete_from_provider(self, provider, credentials, target, parameters)
            self.pim.delete_image_with_id(image_object.identifier)
            image_object.status_detail = {'activity': 'Image deleted.', 'error': None}
            image_object.status = "DELETED"
        except Exception, e:
            image_object.status_detail = {'activity': 'Failed to delete image.', 'error': str(e)}
            image_object.status="DELETEFAILED"
            self.pim.save_image(image_object)
            self.log.error("Exception encountered in _delete_image_on_provider thread")
            self.log.exception(e)
        finally:
            # We only shut the workers down after a known-final state change
            self._shutdown_callback_workers(image_object, self._deletion_cbws)

########NEW FILE########
__FILENAME__ = CallbackWorker

# Callable class that is used to launch a thread
import threading
import time
import logging
import httplib2
import json
import re
import base64

class CallbackWorker():

    def __init__(self, callback_url):
        # callback_url - the URL to which we will send the full object JSON for each STATUS update
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))        
        self.callback_queue = [ ]
        self.queue_lock = threading.BoundedSemaphore()
        self.queue_not_empty = threading.Event()
        self.httplib = httplib2.Http()
        # TODO: A more flexible approach than simply supporting basic auth embedded in the URL
        url_regex = r"^(\w*://)([^:/]+)(:)([^:/]+)(@)(.*)$"
        sr = re.search(url_regex, callback_url)
        if sr:
            self.callback_url = sr.group(1) + sr.group(6)
            auth = base64.encodestring( sr.group(2) + ':' + sr.group(4) )
            self.headers = {'content-type':'application/json', 'Authorization' : 'Basic ' + auth}
        else:
            self.callback_url = callback_url
            self.headers = {'content-type':'application/json'}
        self.shutdown = False

    def start(self):
        self.thread = threading.Thread(target=self)
        self.thread.start()
        return self.thread

    def shut_down(self, blocking=False):
        # At this point the caller has promised us that they will not enqueue anything else
        self.shutdown = True
        self.queue_lock.acquire()
        ### QUEUE LOCK ###
        # The queue cannot grow at this point
        # The worker thread at this point can be:
        # 1) Sleeping due to empty 
        # 2) Woken up but not yet acquired lock in _get_next_callback()
        # 3) Woken up and past QUEUE LOCK in _get_next_callback() (including remainder of main loop)
        #
        # We wish to avoid a situation where the worker thread lingers forever because it is sleeping
        # on an empty queue
        # In case 2 the queue may end up empty but that will be caught in the main loop
        # In case 3 the queue may already be empty but this _should_ always be caught by the main loop
        # Case 1 is only possible if the queue is already empty (I think)
        # So, here we check if the queue is empty and, if it is, we inaccurately set queue_not_empty
        # to wake up the worker thread.  _get_next_thing will detect this and fall through to the 
        # bottom of the main loop which will, in turn, break out and exit
        if len(self.callback_queue) == 0:
            self.queue_not_empty.set()
        self.queue_lock.release()
        if blocking:
            self.thread.join()

    def status_notifier(self, notification):
        image = notification.sender
        _type = type(image).__name__
        typemap = {"TargetImage": "target_image", "ProviderImage": "provider_image", "BaseImage": "base_image" }
        if not _type in typemap:
            raise Exception("Unmappable object type: %s" % _type)
        callback_body = { typemap[_type]: {'_type':_type,
                         'id':image.identifier} }
#                         'href':request.url}
        for key in image.metadata():
            if key not in ('identifier', 'data', 'base_image_id', 'target_image_id'):
                callback_body[typemap[_type]][key] = getattr(image, key, None)
        self._enqueue(callback_body)

    def _enqueue(self, status_update):
        # This is, in short, a request to enqueue a task
        if self.shutdown:
            raise Exception("Attempt made to add work to a terminating worker thread")
        self.queue_lock.acquire()
        ### QUEUE LOCK ###
        self.callback_queue.append(status_update)
        self.queue_not_empty.set()
        ### END QUEUE LOCK ###
        self.queue_lock.release()

    def _wait_for_callback(self):
        # Called at the start of the main loop if the queue is empty
        # self.queue_not_empty is set anytime an item is added to the queue
        # or if the shutdown method is called on an empty queue (which prevents us
        # waiting here forever)
        self.log.debug("Entering blocking non-empty queue call")
        self.queue_not_empty.wait()
        self.log.debug("Leaving blocking non-empty queue call")

    def _get_next_callback(self):
        self.queue_lock.acquire()
        ### QUEUE LOCK ###
        if len(self.callback_queue) == 0:
            # Can potentially happen if worker is shutdown without doing anything
            self.queue_lock.release()
            return None
        next_callback = self.callback_queue.pop(0)
        if len(self.callback_queue) == 0:
            self.queue_not_empty.clear()
        ### END QUEUE LOCK ###
        self.queue_lock.release()
        return next_callback

    def _do_next_callback(self):
        self._wait_for_callback()
        next_callback = self._get_next_callback()
        if next_callback:
            self.log.debug("Updated image is: (%s)" % (str(next_callback)))
            if self.callback_url == "debug":
                self.log.debug("Executing a debug callback - sleeping 5 seconds - no actual PUT sent")
                time.sleep(5)
            else:
                self.log.debug("PUTing update to URL (%s)" % (self.callback_url))
                try:
                    resp, content = self.httplib.request(self.callback_url, 
                                                         "PUT", body=json.dumps(next_callback), 
                                                         headers=self.headers )
                except Exception, e:
                    # We treat essentially every potential error here as non-fatal and simply move on to the next update
                    # TODO: Configurable retries?
                    self.log.debug("Caught exception (%s) when attempting to PUT callback - Ignoring" % (str(e)))

    def __call__(self):
        while True:
            self._do_next_callback()
            if self.shutdown and len(self.callback_queue) == 0:
                break
    
    


########NEW FILE########
__FILENAME__ = CloudDelegate
#
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from zope.interface import Interface

class CloudDelegate(Interface):
    """ Delegate interface for OS installation and customization. OS plugins
    use provide the builder with a delegate. Not all methods defined in this
    interface need to be implemented by the delegate, just the ones that
    the plugin cares about. Delegation provides a way for the plugin to
    customize the behavior of the builder. """

    def push_image_to_provider(self, builder, provider, credentials, target, target_image, parameters):
        """
        Prepare the image for use on and upload to a specified provider.

        @param builder The Builder object coordinating image creation.
        @param image The TargetImage to be pushed.
        @param target The cloud target to which the provider belongs.
        @param provider The cloud provider to which the image will be pushed.
        @param parameters The cloud provider specific parameters for pushing.

        @return A ProviderImage object.
        """

    def snapshot_image_on_provider(self, builder, provider, credentials, target, template, parameters):
        """
        Create a ProviderImage by taking a snapshot of an existing image on the provider.

        @param builder The Builder object coordinating image creation.
        @param image_id The provider identifier of the image to snapshot.
        @param target The cloud target to which the provider belongs.
        @param provider The cloud provider to which the image will be pushed.
        @param parameters The cloud provider specific parameters for pushing.

        @return A ProviderImage object.
        """

    def delete_from_provider(self, builder, provider, credentials, target, parameters):
        """
        Delete the image from the provider.

        @param builder The Builder object with the provider image to delete.
        @param target The cloud target to which the provider belongs.
        @param provider The cloud provider from which the image will be deleted.
        @param parameters The cloud provider specific parameters for deletion.
        """

    def builder_should_create_target_image(self, builder, target, image_id, template, parameters):
        """
        Allows the delegate to decide if a TargetImage should be created.

        @param builder The Builder object coordinating image creation.

        @return bool
        """

    def builder_will_create_target_image(self, builder, target, image_id, template, parameters):
        """
        Called just before a TargetImage is created.

        @param builder The Builder object coordinating image creation.
        """
    
    def builder_did_create_target_image(self, builder, target, image_id, template, parameters):
        """
        Called just after a TargetImage has been created.

        @param builder The Builder object coordinating image creation.
        """


########NEW FILE########
__FILENAME__ = FactoryUtils
#!/usr/bin/python

# A set of helpful utility functions
# Avoid imports that are too specific to a given cloud or OS
# We want to allow people to import all of these
# Add logging option

import guestfs
import os
import re
from imgfac.ImageFactoryException import ImageFactoryException
import subprocess


def launch_inspect_and_mount(diskfile, readonly=False):
    g = guestfs.GuestFS()
    # Added to allow plugins that wish to inspect base images without modifying them
    # (once FINISHED images should never be changed)
    if readonly:
        g.add_drive_ro(diskfile)
    else:
        g.add_drive(diskfile)
    g.launch()
    return inspect_and_mount(g, diskfile=diskfile)

def inspect_and_mount(guestfs_handle, relative_mount="", diskfile='*unspecified*'):
    g = guestfs_handle
    # Breaking this out allows the EC2 cloud plugin to avoid duplicating this
    inspection = g.inspect_os()
    if len(inspection) == 0:
        raise Exception("Unable to find an OS on disk image (%s)" % (diskfile))
    if len(inspection) > 1:
        raise Exception("Found multiple OSes on disk image (%s)" % (diskfile))
    filesystems = g.inspect_get_mountpoints(inspection[0])
    fshash = { }
    for filesystem in filesystems:
        fshash[filesystem[0]] = filesystem[1]
 
    mountpoints = fshash.keys()
    # per suggestion in libguestfs doc - sort the mount points on length
    # simple way to ensure that mount points are present before a mount is attempted
    mountpoints.sort(key=len)
    for mountpoint in mountpoints:
        g.mount_options("", fshash[mountpoint], relative_mount + mountpoint)

    return g

def shutdown_and_close(guestfs_handle):
    shutdown_result = guestfs_handle.shutdown()
    guestfs_handle.close()
    if shutdown_result:
        raise Exception("Error encountered during guestfs shutdown - data may not have been written out")

def remove_net_persist(guestfs_handle):
    # In the cloud context we currently never need or want persistent net device names
    # This is known to break networking in RHEL/VMWare and could potentially do so elsewhere
    # Just delete the file to be safe
    g = guestfs_handle
    if g.is_file("/etc/udev/rules.d/70-persistent-net.rules"):
        g.rm("/etc/udev/rules.d/70-persistent-net.rules")

    # Also clear out the MAC address this image was bound to.
    g.aug_init("/", 0)
    # This silently fails, without an exception, if the HWADDR is already gone
    g.aug_rm("/files/etc/sysconfig/network-scripts/ifcfg-eth0/HWADDR")
    g.aug_save()
    g.aug_close()

def create_cloud_info(guestfs_handle, target):
    tmpl = 'CLOUD_TYPE="%s"\n' % (target)
    guestfs_handle.write("/etc/sysconfig/cloud-info", tmpl)

def subprocess_check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)

    stdout, stderr = process.communicate()
    retcode = process.poll()

    if retcode:
        cmd = ' '.join(*popenargs)
        raise ImageFactoryException("'%s' failed(%d): %s" % (cmd, retcode, stderr))
    return (stdout, stderr, retcode)

def subprocess_check_output_pty(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    (master, slave) = os.openpty()
    process = subprocess.Popen(stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)

    stdout, stderr = process.communicate()
    retcode = process.poll()

    os.close(slave)
    os.close(master)

    if retcode:
        cmd = ' '.join(*popenargs)
        raise ImageFactoryException("'%s' failed(%d): %s" % (cmd, retcode, stderr))
    return (stdout, stderr, retcode)

def ssh_execute_command(guestaddr, sshprivkey, command, timeout=10, user='root', prefix=None):
    """
    Function to execute a command on the guest using SSH and return the output.
    Modified version of function from ozutil to allow us to deal with non-root
    authorized users on ec2
    """
    # ServerAliveInterval protects against NAT firewall timeouts
    # on long-running commands with no output
    #
    # PasswordAuthentication=no prevents us from falling back to
    # keyboard-interactive password prompting
    #
    # -F /dev/null makes sure that we don't use the global or per-user
    # configuration files
    #
    # -t -t ensures we have a pseudo tty for sudo

    cmd = ["ssh", "-i", sshprivkey,
            "-F", "/dev/null",
            "-o", "ServerAliveInterval=30",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=" + str(timeout),
            "-o", "UserKnownHostsFile=/dev/null",
            "-t", "-t",
            "-o", "PasswordAuthentication=no"]

    if prefix:
        command = prefix + " " + command

    cmd.extend(["%s@%s" % (user, guestaddr), command])

    if(prefix == 'sudo'):
        return subprocess_check_output_pty(cmd)
    else:
        return subprocess_check_output(cmd)

def enable_root(guestaddr, sshprivkey, user, prefix):
    for cmd in ('mkdir /root/.ssh',
                'chmod 600 /root/.ssh',
                'cp /home/%s/.ssh/authorized_keys /root/.ssh' % user,
                'chmod 600 /root/.ssh/authorized_keys'):
        try:
            ssh_execute_command(guestaddr, sshprivkey, cmd, user=user, prefix=prefix)
        except Exception as e:
            pass

    try:
        stdout, stderr, retcode = ssh_execute_command(guestaddr, sshprivkey, '/bin/id')
        if not re.search('uid=0', stdout):
            raise Exception('Running /bin/id on %s as root: %s' % (guestaddr, stdout))
    except Exception as e:
        raise ImageFactoryException('Transfer of authorized_keys to root from %s must have failed - Aborting - %s' % (user, e))

# Our generic "parameters" dict passed to the plugins may be derived from either
# real JSON or from individual parameters passed on the command line.  In the case
# of command line parameters, all dict values are strings.  Plugins that want to
# accept non-string parameters should be prepared to do a string conversion.

def parameter_cast_to_bool(ival):
    """
    Function to take an input that may be a string, an int or a bool
    If input is a string it is made lowecase
    Returns True if ival is boolean True, a non-zero integer, "Yes",
    "True" or "1"
    Returns False in ival is boolean False, zero, "No", "False" or "0"
    In all other cases, returns None
    """
    if type(ival) is bool:
        return ival
    if type(ival) is int:
        return bool(ival)
    if type(ival) is str:
        lower = ival.lower()
        if lower == 'no' or lower == 'false' or lower == '0':
            return False
        if lower == 'yes' or lower == 'true' or lower == '1':
            return True
    return None

########NEW FILE########
__FILENAME__ = FilePersistentImageManager
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import re
import os
import os.path
import stat
import json
from props import prop
from ImageFactoryException import ImageFactoryException
from PersistentImageManager import PersistentImageManager
from threading import BoundedSemaphore

STORAGE_PATH = '/var/lib/imagefactory/storage'
METADATA_EXT = '.meta'
BODY_EXT = '.body'

class FilePersistentImageManager(PersistentImageManager):
    """ TODO: Docstring for PersistentImageManager  """

    storage_path = prop("_storage_path")

    def __init__(self, storage_path=STORAGE_PATH):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        if not os.path.exists(storage_path):
            self.log.debug("Creating directory (%s) for persistent storage" % (storage_path))
            os.makedirs(storage_path)
            os.chmod(storage_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        elif not os.path.isdir(storage_path):
            raise ImageFactoryException("Storage location (%s) already exists and is not a directory - cannot init persistence" % (storage_path))
        else:
            # TODO: verify that we can write to this location
            pass
        self.storage_path = storage_path
        self.metadata_lock = BoundedSemaphore()


    def _image_from_metadata(self, metadata):
        # Given the retrieved metadata from mongo, return a PersistentImage type object
        # with us as the persistent_manager.

        image_module = __import__(metadata['type'], globals(), locals(), [metadata['type']], -1)
        image_class = getattr(image_module, metadata['type'])
        image = image_class(metadata['identifier'])

        # We don't actually want a 'type' property in the resulting PersistentImage object
        del metadata['type']

        for key in image.metadata().union(metadata.keys()):
            setattr(image, key, metadata.get(key))

        #set ourselves as the manager
        image.persistent_manager = self

        return image


    def _metadata_from_file(self, metadatafile):
        self.metadata_lock.acquire()
        try:
            mdf = open(metadatafile, 'r')
            metadata = json.load(mdf)
            mdf.close()
        finally:
            self.metadata_lock.release()
        return metadata


    def image_with_id(self, image_id):
        """
        TODO: Docstring for image_with_id

        @param image_id TODO 

        @return TODO
        """
        metadatafile = self.storage_path + '/' + image_id + METADATA_EXT
        try:
            metadata = self._metadata_from_file(metadatafile)
        except Exception as e:
            self.log.debug('Exception caught: %s' % e)
            return None

        return self._image_from_metadata(metadata)


    def images_from_query(self, query):
        images = [ ]
        for storefileshortname in os.listdir(self.storage_path):
            storefilename = self.storage_path + '/' + storefileshortname
            if re.search(METADATA_EXT, storefilename):
                try:
                    metadata = self._metadata_from_file(storefilename)
                    match = True
                    for querykey in query:
                        if metadata[querykey] != query[querykey]:
                            match = False
                            break
                    if match:
                        images.append(self._image_from_metadata(metadata))
                except:
                    self.log.warn("Could not extract image metadata from file (%s)" % (storefilename))

        return images              


    def add_image(self, image):
        """
        TODO: Docstring for add_image

        @param image TODO 

        @return TODO
        """
        image.persistent_manager = self
        basename = self.storage_path + '/' + str(image.identifier)
        metadata_path = basename + METADATA_EXT
        body_path = basename + BODY_EXT
        image.data = body_path
        try:
            if not os.path.isfile(metadata_path):
                open(metadata_path, 'w').close()
                self.log.debug('Created file %s' % metadata_path)
            if not os.path.isfile(body_path):
                open(body_path, 'w').close()
                self.log.debug('Created file %s' % body_path)
        except IOError as e:
            self.log.debug('Exception caught: %s' % e)

        self.save_image(image)

    def save_image(self, image):
        """
        TODO: Docstring for save_image

        @param image TODO

        @return TODO
        """
        image_id = str(image.identifier)
        metadata_path = self.storage_path + '/' + image_id + METADATA_EXT
        if not os.path.isfile(metadata_path):
            raise ImageFactoryException('Image %s not managed, use "add_image()" first.' % image_id)
        try:
            meta = {'type': type(image).__name__}
            for mdprop in image.metadata():
                meta[mdprop] = getattr(image, mdprop, None)
 
            self.metadata_lock.acquire()
            try:
                mdf = open(metadata_path, 'w')
                json.dump(meta, mdf)
                mdf.close()
            finally:
                self.metadata_lock.release()

            self.log.debug("Saved metadata for image (%s): %s" % (image_id, meta))
        except Exception as e:
            self.log.debug('Exception caught: %s' % e)
            raise ImageFactoryException('Unable to save image metadata: %s' % e)

    def delete_image_with_id(self, image_id):
        """
        TODO: Docstring for delete_image_with_id

        @param image_id TODO 

        @return TODO
        """
        basename = self.storage_path + '/' + image_id
        metadata_path = basename + METADATA_EXT
        body_path = basename + BODY_EXT
        try:
            os.remove(metadata_path)
            os.remove(body_path)
        except Exception as e:
            self.log.warn('Unable to delete file: %s' % e)

########NEW FILE########
__FILENAME__ = ImageFactoryException
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

class ImageFactoryException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

########NEW FILE########
__FILENAME__ = MongoPersistentImageManager
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import os
import os.path
import json
import pymongo
from copy import copy
from props import prop
from ImageFactoryException import ImageFactoryException
from PersistentImageManager import PersistentImageManager

STORAGE_PATH = '/var/lib/imagefactory/storage'
METADATA_EXT = '.meta'
BODY_EXT = '.body'
DB_NAME = "factory_db"
COLLECTION_NAME = "factory_collection"


class MongoPersistentImageManager(PersistentImageManager):
    """ TODO: Docstring for PersistentImageManager  """

    storage_path = prop("_storage_path")

    def __init__(self, storage_path=STORAGE_PATH):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        if not os.path.exists(storage_path):
            self.log.debug("Creating directory (%s) for persistent storage" % (storage_path))
            os.makedirs(storage_path)
        elif not os.path.isdir(storage_path):
            raise ImageFactoryException("Storage location (%s) already exists and is not a directory - cannot init persistence" % (storage_path))
        else:
            # TODO: verify that we can write to this location
            pass
        self.storage_path = storage_path
        self.con = pymongo.Connection()
        self.db = self.con[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]

    def _to_mongo_meta(self, meta):
        # Take our view of the metadata and make the mongo view
        # Use our "identifier" as the mongo "_id"
        # Explicitly recommended here: http://www.mongodb.org/display/DOCS/Object+IDs
        # TODO: Pack UUID into BSON representation
        mongometa = copy(meta)
        mongometa['_id'] = meta['identifier']
        return mongometa

    def _from_mongo_meta(self, mongometa):
        # Take mongo metadata and return the internal view
        meta = copy(mongometa)
        # This is just a duplicate
        del meta['_id']
        return meta

    def _image_from_metadata(self, metadata):
        # Given the retrieved metadata from mongo, return a PersistentImage type object
        # with us as the persistent_manager.

        image_module = __import__(metadata['type'], globals(), locals(), [metadata['type']], -1)
        image_class = getattr(image_module, metadata['type'])
        image = image_class(metadata['identifier'])

        # We don't actually want a 'type' property in the resulting PersistentImage object
        del metadata['type']

        for key in image.metadata().union(metadata.keys()):
            setattr(image, key, metadata.get(key))

        #I don't think we want this as it will overwrite the "data" element
        #read from the store.
        #self.add_image(image)

        #just set ourselves as the manager
        image.persistent_manager = self

        return image


    def image_with_id(self, image_id):
        """
        TODO: Docstring for image_with_id

        @param image_id TODO 

        @return TODO
        """
        try:
            metadata = self._from_mongo_meta(self.collection.find_one( { "_id": image_id } ))
        except Exception as e:
            self.log.debug('Exception caught: %s' % e)
            return None

        if not metadata:
            raise ImageFactoryException("Unable to retrieve object metadata in Mongo for ID (%s)" % (image_id))

        return self._image_from_metadata(metadata)


    def images_from_query(self, query):
        images = [ ]
        for image_meta in self.collection.find(query):
            if "type" in image_meta:
                images.append(self._image_from_metadata(image_meta))
            else:
                self.log.warn("Found mongo record with no 'type' key - id (%s)" % (image_meta['_id']))
        return images 

    def add_image(self, image):
        """
        Add a PersistentImage-type object to this PersistenImageManager
        This should only be called with an image that has not yet been added to the store.
        To retrieve a previously persisted image use image_with_id() or image_query()

        @param image TODO 

        @return TODO
        """
        metadata = self.collection.find_one( { "_id": image.identifier } )
        if metadata:
            raise ImageFactoryException("Image %s already managed, use image_with_id() and save_image()" % (image.identifier))

        image.persistent_manager = self
        basename = self.storage_path + '/' + str(image.identifier)
        body_path = basename + BODY_EXT
        image.data = body_path
        try:
            if not os.path.isfile(body_path):
                open(body_path, 'w').close()
                self.log.debug('Created file %s' % body_path)
        except IOError as e:
            self.log.debug('Exception caught: %s' % e)

        self._save_image(image)

    def save_image(self, image):
        """
        TODO: Docstring for save_image

        @param image TODO

        @return TODO
        """
        image_id = str(image.identifier)
        metadata = self._from_mongo_meta(self.collection.find_one( { "_id": image_id } ))
        if not metadata:
            raise ImageFactoryException('Image %s not managed, use "add_image()" first.' % image_id)
        self._save_image(image)

    def _save_image(self, image):
        try:
            meta = {'type': type(image).__name__}
            for mdprop in image.metadata():
                meta[mdprop] = getattr(image, mdprop, None)
            # Set upsert to true - allows this function to do the initial insert for add_image
            # We check existence for save_image() already
            self.collection.update( { '_id': image.identifier}, self._to_mongo_meta(meta), upsert=True )
            self.log.debug("Saved metadata for image (%s): %s" % (image.identifier, meta))
        except Exception as e:
            self.log.debug('Exception caught: %s' % e)
            raise ImageFactoryException('Unable to save image metadata: %s' % e)

    def delete_image_with_id(self, image_id):
        """
        TODO: Docstring for delete_image_with_id

        @param image_id TODO 

        @return TODO
        """
        basename = self.storage_path + '/' + image_id
        body_path = basename + BODY_EXT
        try:
            os.remove(body_path)
        except Exception as e:
            self.log.warn('Unable to delete file: %s' % e)

        try:
            self.collection.remove(image_id)
        except Exception as e:
            self.log.warn('Unable to remove mongo record: %s' % e)

########NEW FILE########
__FILENAME__ = Notification
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from props import prop

class Notification(object):
    """ TODO: Docstring for Notification  """

    message = prop("_message")
    sender = prop("_sender")
    user_info = prop("_user_info")

    def __init__(self, message, sender, user_info=None):
        """ TODO: Fill me in
        
        @param message TODO
        @param sender TODO
        @param user_info TODO
        """
        self._message = message
        self._sender = sender
        self._user_info = user_info

########NEW FILE########
__FILENAME__ = NotificationCenter
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
from Singleton import Singleton
from props import prop
from collections import defaultdict
from threading import RLock
from Notification import Notification

class NotificationCenter(Singleton):
    """ TODO: Docstring for NotificationCenter  """

    observers = prop("_observers")

    def _singleton_init(self, *args, **kwargs):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.observers = defaultdict(set)
        self.lock = RLock()

    def add_observer(self, observer, method, message='all', sender=None):
        """
        TODO: Docstring for add_observer
        
        @param observer TODO
        @param method TODO
        @param message TODO
        @param sender TODO
        """
        self.lock.acquire()
        self.observers[message].add((observer, method, sender))
        self.lock.release()

    def remove_observer(self, observer, method, message='all', sender=None):
        """
        TODO: Docstring for remove_observer
        
        @param observer TODO
        @param message TODO
        @param sender TODO
        """
        self.lock.acquire()
        _observer = (observer, method, sender)
        self.observers[message].discard(_observer)
        if (len(self.observers[message]) == 0):
            del self.observers[message]
        self.lock.release()

    def post_notification(self, notification):
        """
        TODO: Docstring for post_notification
        
        @param notification TODO
        """
        self.lock.acquire()
        _observers = self.observers['all'].union(self.observers[notification.message])
        for _observer in _observers:
            _sender = _observer[2]
            if ((not _sender) or (_sender == notification.sender)):
                try:
                    getattr(_observer[0], _observer[1])(notification)
                except AttributeError as e:
                    self.log.exception('Caught exception: posting notification to object (%s) with method (%s)' % (_observer[0], _observer[1]))
        self.lock.release()

    def post_notification_with_info(self, message, sender, user_info=None):
        """
        TODO: Docstring for post_notification_with_info
        
        @param message TODO
        @param sender TODO
        @param user_info TODO
        """
        self.post_notification(Notification(message, sender, user_info))

########NEW FILE########
__FILENAME__ = OSDelegate
#
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from zope.interface import Interface

class OSDelegate(Interface):
    """ Delegate interface for OS installation and customization. OS plugins
    use provide the builder with a delegate. Not all methods defined in this
    interface need to be implemented by the delegate, just the ones that
    the plugin cares about. Delegation provides a way for the plugin to
    customize the behavior of the builder. """

    def create_base_image(self, builder, template, parameters):
        """
        Create a JEOS image and install any packages specified in the template.

        @param builder The Builder object coordinating image creation.
        @param template A Template object.
        @param parameters Dictionary of target specific parameters.

        @return A BaseImage object.
        """

    def create_target_image(self, builder, target, base_image, parameters):
        """
        Performs cloud specific customization on the base image.

        @param builder The builder object.
        @param base_image The BaseImage to customize.
        @param target The cloud type to customize for.
        @param parameters Dictionary of target specific parameters.

        @return A TargetImage object.
        """

    def add_cloud_plugin_content(self, content):
        """
        This is a method that cloud plugins can call to deposit content/commands to
        be run during the OS-specific first stage of the Target Image creation.

        There is no support for repos at the moment as these introduce external
        dependencies that we may not be able to resolve.

        @param content dict containing commands and file.
        """

########NEW FILE########
__FILENAME__ = PersistentImage
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from props import prop
import uuid
import logging
from Notification import Notification
from NotificationCenter import NotificationCenter


METADATA = ('identifier', 'data', 'template', 'icicle', 'status_detail', 'status', 'percent_complete', 'parameters',
            'properties')
STATUS_STRINGS = ('NEW', 'PENDING', 'BUILDING', 'COMPLETE', 'FAILED', 'DELETING', 'DELETED', 'DELETEFAILED')
NOTIFICATIONS = ('image.status', 'image.percentage')


class PersistentImage(object):
    """ TODO: Docstring for PersistentImage  """

##### PROPERTIES
    persistence_manager = prop("_persistence_manager")
    identifier = prop("_identifier")
    data = prop("_data")
    template = prop("_template")
    icicle = prop("_icicle")
    status_detail = prop("_status_detail")
    parameters = prop("_parameters")
    properties = prop("_properties")

    def status():
        doc = "A string value."

        def fget(self):
            return self._status

        def fset(self, value):
            value = value.upper()
            if value == self._status:
                # Do not update or send a notification if nothing has changed
                return
            if value in STATUS_STRINGS:
                old_value = self._status
                self._status = value
                notification = Notification(message=NOTIFICATIONS[0],
                                            sender=self,
                                            user_info=dict(old_status=old_value, new_status=value))
                self.notification_center.post_notification(notification)
            else:
                raise KeyError('Status (%s) unknown. Use one of %s.' % (value, STATUS_STRINGS))

        return locals()
    status = property(**status())

    def percent_complete():
        doc = "The percentage through an operation."

        def fget(self):
            return self._percent_complete

        def fset(self, value):
            old_value = self._percent_complete
            if value == old_value:
                # Do not update or send a notification if nothing has changed
                return
            self._percent_complete = value
            notification = Notification(message=NOTIFICATIONS[1],
                                        sender=self,
                                        user_info=dict(old_percentage=old_value, new_percentage=value))
            self.notification_center.post_notification(notification)

        return locals()
    percent_complete = property(**percent_complete())
##### End PROPERTIES

    def __init__(self, image_id=None):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.notification_center = NotificationCenter()
        # We have never had use for the UUID object itself - make this a string
        # TODO: Root out all places where were str() convert this elsewhere
        self.identifier = image_id if image_id else str(uuid.uuid4())
        self.persistence_manager = None
        self.data = None
        # 'activity' should be set to a single line indicating, in as much detail as reasonably possible,
        #   what it is that the plugin operating on this image is doing at any given time.
        # 'error' should remain None unless an exception or other fatal error has occurred.  Error may
        #   be a multi-line string
        self.status_detail = {'activity': 'Initializing image prior to Cloud/OS customization', 'error': None}
        # Setting these to None or setting initial value via the properties breaks the prop code above
        self._status = "NEW"
        self._percent_complete = 0
        self.icicle = None
        self.parameters = {}
        self.properties = {}

    def update(self, percentage=None, status=None, detail=None, error=None):
        if percentage:
            self.percent_complete = percentage
        if status:
            self.status = status
        if detail:
            self.status_detail['activity'] = detail
        self.status_detail['error'] = error

    def metadata(self):
        self.log.debug("Executing metadata in class (%s) my metadata is (%s)" % (self.__class__, METADATA))
        return METADATA
########NEW FILE########
__FILENAME__ = PersistentImageManager
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from ApplicationConfiguration import ApplicationConfiguration


class PersistentImageManager(object):
    """ Abstract base class for the Persistence managers  """


    _default_manager = None

    @classmethod
    def default_manager(cls):
        if not cls._default_manager:
            appconfig = ApplicationConfiguration().configuration
            class_name = appconfig['image_manager'].capitalize() + "PersistentImageManager"
            kwargs = appconfig['image_manager_args'] 
            # The current defaults are 'file' for class name and 
            # { "storage_location": "/var/lib/imagefactory/storage" } for the args
            pim_module = __import__(class_name, globals(), locals(), [ class_name ], -1)
            pim_class = getattr(pim_module, class_name)
            cls._default_manager = pim_class(**kwargs)
        return cls._default_manager

    def __init__(self, storage_path = None):
        raise NotImplementedError("PersistentImageManager is an abstract class.  You must instantiate a real manager.")

    def image_with_id(self, image_id):
        """
        TODO: Docstring for image_with_id

        @param image_id TODO 

        @return TODO
        """
        raise NotImplementedError("image_with_id() not implemented - cannot continue")

    def images_from_query(self, query):
        """
        TODO: Docstring for images_from_query

        @param image_id TODO 

        @return TODO
        """
        raise NotImplementedError("images_from_query() not implemented - cannot continue")


    def add_image(self, image):
        """
        TODO: Docstring for add_image

        @param image TODO 

        @return TODO
        """
        raise NotImplementedError("add_image() not implemented - cannot continue")

    def save_image(self, image):
        """
        TODO: Docstring for save_image

        @param image TODO

        @return TODO
        """
        raise NotImplementedError("save_image() not implemented - cannot continue")

    def delete_image_with_id(self, image_id):
        """
        TODO: Docstring for delete_image_with_id

        @param image_id TODO 

        @return TODO
        """
        raise NotImplementedError("delete_image_with_id() not implemented - cannot continue")

########NEW FILE########
__FILENAME__ = arraydisposition
#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
////////////////////////////////// ArrayDisposition_e ////////////////
// Different kinds of POD (Plain Old Data: int_1, int_2, real_4, etc.) arrays: 
// there are essentially 4 different types of POD arrays that might be moving 
// around: 
//
// (1) a = [1,2,3]  
//     Python styles lists (which are inefficient for storing 
//     homogeneous data)
//
// (2) import array; a = array.array('i',[1,2,3])
//     the arrays from the Python module array 
//     Unfortunately, they pickle different from 2.6 to 2.7, so we
//     prefer not to use these.
//   
// (3) import Numeric: a = Numeric.array([1,2,3], 'i')
//     the Numeric arrays which are built in to XMPY,
//     but most standard Pythons do not have it installed.
//
// (4) import numpy; a = numpy.array([1,2,3], dtype=numpy.int32)
//     numpy is an external package, but a reasonably de-facto
//     standard (replacing Numeric)
//
// In C++, POD arrays are handled as Array<T>, thus (2) & (3) & (4)
// are handled with the same:  (1) is handled as the C++ Arr.  
// These distinctions are more important if you are in Python, or talking 
// to a Python system, as you have to specify how a C++ Array
// converts to a Python POD array.
//
// These 4 distinctions are made because Python doesn't deal
// well with POD (plain old data) arrays well:  This option allows
// you to choose what you want when dealing with POD when you
// convert between systems.  Consider:
// (1) Python style lists work, but are horribly inefficient for
//     large arrays of just plain numbers, both from a storage
//     perspective or accessing.  Also, you "lose" the fact 
//     that this is true POD array if you go back to C++.
// (2) Numeric is old, but handles all the different types well,
//     including complex (although Numeric doesn't deal with int_8s!).
//     It is also NOT a default-installed package: you may have to find
//     the proper RPM for this to work.
// (3) Python array from the array module are default but have issues:
//     (a) can't do complex data 
//     (b) may or may not support int_8
//     (c) pickling changes at 2.3.4 and 2.6, so if you are
//        3 pickling with protocol 2, you may have issues.
// (4) NumPy arrays are well-supported and pretty much the de-facto
//     standard.  Their only real drawback is that they are not
//     necessarily installed by default, but most likely they are
//
// NUMERIC_WRAPPER is for the XML classes, but unsupported elsewhere.
//
// None of these solutions is perfect, but going to NumPy will
// probably fix most of these issues in the future.
/////////////////////////////////////////////////////////////////////
"""

# Different kinds of Arrays: there are essentially 3 different types
# of arrays that might be moving arround: Python styles lists (which
# are inefficient for storing homogeneous data), the arrays from the
# Python module array (which doesn't work well with Pickling until
# sometime after 2.3.4), and the Numeric arrays which is built in to
# XMPY, but most standard Pythons do not have it installed.
ARRAYDISPOSITION_AS_NUMERIC = 0
ARRAYDISPOSITION_AS_LIST = 1
ARRAYDISPOSITION_AS_PYTHON_ARRAY = 2   # New feature
ARRAYDISPOSITION_AS_NUMERIC_WRAPPER = 3   
ARRAYDISPOSITION_AS_NUMPY = 4   # New feature



########NEW FILE########
__FILENAME__ = circularbuffer
#!/usr/bin/env python

"""A CircularBuffer used to hold elements by value: the end the front
can inserted/deleted in constant time: it can request infinite
Circular buffer (meaning that puts will never over-write read
data)."""

class CircularBuffer(object) :

    def __init__ (self, initial_length=4, infinite=False) :
        """Construct a circular buffer (with buffer length)"""
        # Array<T> buff_;
        # int nextPut_;          // Points where next put will occur
        # int nextGet_;          // Points to where next get will occur
        # bool empty_;           // nextPut_==nextGet is either empty or full
        # bool infinite_;        // Puts into empty cause a doubling
  
        self.buff_ = [None for x in xrange(initial_length)]
        self.nextPut_ = 0
        self.nextGet_ = 0
        self.empty_   = True
        self.infinite_ = infinite


    def empty (self): return self.empty_
    def full (self): return not self.empty_ and self.nextGet_==self.nextPut_
    def infinite (self): return self.infinite_
    def capacity (self): return len(self.buff_)
    def __len__ (self) : 
        if (self.empty()) :
            return 0
        elif (self.full()):
            return self.capacity()
        elif (self.nextGet_>self.nextPut_) :
            return self.capacity()-(self.nextGet_-self.nextPut_)
        else :
            return self.nextPut_-self.nextGet_

    def put (self, c) :
        """Put a single element into the buffer.  If in infinite mode, a put
        into a "full" buffer will cause it to re-expand and double the
        size.  If in finite mode, it will throw a runtime_error."""
        self._checkFullness()
        # Space available, just plop it in
        retval = self.buff_[self.nextPut_] = c
        self.nextPut_ = (self.nextPut_+1) % self.capacity()
        self.empty_ = False
        return retval
    
    def get (self) :
        """Get a single element out of the circular buffer.  If the buffer
        is empty, throw a runtime_error"""
        if (self.empty()) :  # Empty, can't get anything
            raise Exception("Circular Buffer Empty")
        else :       # nextGet always tells us where we are
            c = self.buff_[self.nextGet_];
            self.nextGet_ = (self.nextGet_+1) % self.capacity()
            self.empty_ = (self.nextGet_ == self.nextPut_)
        return c

    def peek (self, where=0) :
        """Peek at the nth element (element 0 would be the first thing "get"
        would return, element 1 would be the next).  Throws the
        runtime_error exception if try to peek beyond what the buffer
        has.  This does NOT advance the circular buffer: it only looks
        inside."""
        if (where<0 or where>=len(self)) :
            m = "Trying to peek beyond the end of the Circ. Buff"
            raise Exception(m)
        index = (self.nextGet_+where) % self.capacity()
        return self.buff_[index]
    


    def consume (self, n) :
        """This implements performing "n" gets, but in O(1) time.  If asked
        to consume more elements that the CircularBuffer contains, a
        runtime_error will be thrown."""
        if (n<0 or n>len(self)) :
            m = "Trying to consume more data than in Circ. Buff"
            raise Exception(m)
    
        self.empty_ = (n==len(self))
        self.nextGet_ = (self.nextGet_+n) % self.capacity()
  

    def pushback (self, pushback_val) :
        """The "get()" always pulls from one side of the circular buffer:
        Sometimes, you want to be able to pushback some entry
        you just got as if it were never "get()" ed.   This is
        very similar to "put", but it is simply doing it on the other
        side of the circular buffer.  The pushback can fail if the
        queue is full (not infinite mode) with a runtime_error.
        If it is an infiite queue, it will simply re-expand."""

        self._checkFullness()
        # Space available, just plop it in
        self.nextGet_ = (self.nextGet_+self.capacity()-1) % self.capacity()
        retval = self.buff_[self.nextGet_] = pushback_val
        self.empty_ = False
        return retval


    def drop (self) :
        """ Drop the last "put()" as if it never went in: this can throw
        an exception if the buffer is empty."""
        if (self.empty()) : # Empty, can't get anything
            raise Exception("Circular Buffer Empty")
        else :      # nextPut always tells us where we are
            self.nextPut_ = (self.nextPut_+self.capacity()-1) % self.capacity()
            c = self.buff_[self.nextPut_]
            self.empty_ = (self.nextGet_ == self.nextPut_)
        return c
    
    def __str__ (self) :
        """Stringize from front to back"""
        a = []
        next_get = self.nextGet_
        buffer   = self.buff_
        length   = self.capacity()
        for x in xrange(len(self)) :
            a.append(str(buffer[next_get]))
            a.append(" ")
            next_get = (next_get+1) % length
    
        return "".join(a)


    def _checkFullness (self) :
        # Centralize fullness check and re-expansion code
        if (self.full()) : # Circ Buffer Full, expand and remake
            if (not self.infinite()) : 
                raise Exception("Circular Buffer full")
            else :
                # Create a new Circ. Buffer of twice the size
                length = self.buff_.capacity()
                temp = [None for x in xrange(length*2)]

                buffer = self.buffer_
                next_get = self.nextGet_
                for x in xrange(length) :
                    
                    temp[x] =  buffer[next_get]
                    next_get = (next_get+1) % length

                # Install new buffer
                self.buff_    = temp
                self.nextPut_ = length
                self.nextGet_ = 0
                
        # Assertion: new buffer that is no longer full (has space to grow)
        return

    

if __name__ == "__main__" :
    # testing harness
    CB = CircularBuffer
    
    import sys
    if len(sys.argv)>1 :
        temp = sys.stdout
    else :
        import StringIO
        temp = StringIO.StringIO()
    
    def CBstat(c, temp) :
        print >> temp, "empty:", c.empty(), " full:", c.full(), " len(c):", len(c), " capacity:", c.capacity()
        print >> temp, c

    # Below is the output as you'd cut and patse it: for difflib purposes,
    # we want this to be a list of things
    expected_output_as_cut_and_paste = """\
empty: True  full: False  len(c): 0  capacity: 3

empty: False  full: False  len(c): 1  capacity: 3
100 
100
empty: True  full: False  len(c): 0  capacity: 3

empty: False  full: True  len(c): 3  capacity: 3
1 2 3 
Circular Buffer full
empty: False  full: True  len(c): 3  capacity: 3
1 2 3 
empty: False  full: False  len(c): 2  capacity: 3
2 3 
empty: True  full: False  len(c): 0  capacity: 1

empty: False  full: True  len(c): 1  capacity: 1
4 
Circular Buffer full
empty: False  full: True  len(c): 1  capacity: 1
4 
4
empty: True  full: False  len(c): 0  capacity: 1

empty: True  full: False  len(c): 0  capacity: 2

empty: False  full: False  len(c): 1  capacity: 2
8 
empty: False  full: True  len(c): 2  capacity: 2
8 9 
Circular Buffer full
empty: False  full: True  len(c): 2  capacity: 2
8 9 
8
empty: False  full: False  len(c): 1  capacity: 2
9 
9
empty: True  full: False  len(c): 0  capacity: 2

"""
    expected_output = expected_output_as_cut_and_paste.split('\n')

    a = CB(3)
    CBstat(a, temp)
    a.put(100)
    CBstat(a,temp)
    print >> temp, a.get()
    CBstat(a,temp)

    a.put(1)
    a.put(2)
    a.put(3)
    CBstat(a,temp)

    try :
        a.put(666)
    except Exception, e :
        print >> temp, e
    CBstat(a,temp)

    a.get()
    CBstat(a,temp)


    b = CB(1)
    CBstat(b, temp)
    b.put(4)
    CBstat(b, temp)
    try :
        b.put(666)
    except Exception, e :
        print >> temp, e
    CBstat(b, temp)
    print >> temp, b.get()
    CBstat(b, temp)

    
    b = CB(2)
    CBstat(b, temp)
    b.put(8)
    CBstat(b, temp)
    b.put(9)
    CBstat(b, temp)
    try :
        b.put(666)
    except Exception, e :
        print >> temp, e
    CBstat(b, temp)
    print >> temp, b.get()
    CBstat(b, temp)
    print >> temp, b.get()
    CBstat(b, temp)


    # Finish up early if we just want the output: if we
    # have any argument
    if temp == sys.stdout :
        sys.exit(0)

    # Otherwise, show the diff
    actual_output = temp.getvalue().split('\n')
    temp.close()
    if (expected_output == actual_output) :
        print 'All tests PASSED'
        sys.exit(0) # good!
    else :
        import difflib 
        for line in difflib.context_diff(expected_output, actual_output, fromfile="expected_output", tofile="actual_output", lineterm="") :
            # sys.stdout.write(line)
            print line
        sys.exit(1)  # bad
        

########NEW FILE########
__FILENAME__ = parsereader
#!/bin/env python

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from circularbuffer import * # used for context

class Context_(object) :
    """
     A helper class that keeps track of where we are within the parsing:
     allows us to return better error messages from parsing the tabs.
     """

    def __init__(self, keep_last_n_lines=5) :
        """Create a Parsing Context and remember the last n lines for when
        error messages happen"""
        self.contextLines_ = keep_last_n_lines
        self.data_ = CircularBuffer(1024)
        self.lineNumber_ = 1
        self.charNumber_ = 0

    # // When holding the data, we make the "keeping context" operations
    # // cheap, but when we need to actually supply the information, it's
    # // a little more expensive, as we have to look for line breaks, etc.
    #
    # int contextLines_;  // how lines of context to hold (i.e., how much do we
    #                     // buffer)
    # CircularBuffer<char> data_;  
    #                     // The current "context", i.e., that last few lines 
    # int lineNumber_;    // Current line number we are on
    # int charNumber_;   // current character within that line

  
    def addChar (self, c) :
        """ Add a character to the context """
        #  Notice the \n so we can notice when new lines begin
        if (c=='\n') :
            self.lineNumber_ += 1
            self.charNumber_  = 0
            
        # Keep the last 1024 or so characters
        if (self.data_.full()) :
            self.data_.get()
        self.data_.put(c)
        self.charNumber_ += 1
        

    def deleteLastChar (self) :
        """Delete a character from the context"""
        c = self.data_.drop();
        # Notice the \n so we can notice when new lines begin
        if (c=='\n') :
            self.lineNumber_ -= 1
            # Find last \n ... if we can
            index_of_last_newline = -1
            for ii in xrange(0, len(self.data_)) :
                if (self.data_.peek(len(self.data_)-ii-1)=='\n') :
                    index_of_last_newline = ii
                    break   
      
            self.charNumber_ = index_of_last_newline
            if (index_of_last_newline==-1) : self.charNumber = 80
        else :
            self.charNumber_-=1;


    # Add from this buffer, the amount of data
    def addData (self, buffer, len) :
        for ii in xrange(0,len) :
            self.addChar(buffer[ii])
            

    # Generate a string which has the full context (the last n lines)
    def generateReport (self) :
      
        report = ""

        # Post processing: Create an array of the lines of input.  The
        # last line probably won't end with an newline because the error
        # probably happened in the middle of the line.
        lines = []
        current_line = ""
        for ii in xrange(0, len(self.data_)) :
            c = self.data_.peek(ii)
            current_line = current_line + c
            if (c=='\n') :
                lines.append(current_line)
                current_line = ""
                
        if (current_line != "") :
            current_line = current_line + '\n'
            lines.append(current_line)


        # Only take the last few lines for error reporting
        context_lines = self.contextLines_
        if (len(lines) < self.contextLines_) : context_lines = len(lines)

        if (context_lines) :
            start_line = len(lines)-context_lines

            report = "****Syntax Error on line:"+str(self.lineNumber_)+\
                     " Last "+str(context_lines)+ " line"
            if (context_lines!=1) :
                report = report + "s"
            report = report + " of input (lines "+ \
                     str(start_line+1)+"-"+str(start_line+context_lines)+") "\
                     "shown below****\n"

            for ii in xrange(0, context_lines) :
                report = report + "  " + lines[start_line+ii]
      
            # Show, on last line, where!
            cursor = "-"*(self.charNumber_+1) + "^\n"
            report = report + cursor

        # All done
        return report
  

    def syntaxError (self, s) :
        """Have everything do a syntax error the same way"""
        report = self.generateReport() + s
        raise Exception, report

# A meta-object that is not a string so we can compare against it
EOF = "" # None 
        
class ReaderA(object) :
    """Interface for all Readers parsing ASCII streams.  They all have a
    context for holding the current line numbers for error reporting
    purposes."""

    def __init__ (self) :
        self.context_ = Context_()
        
    def syntaxError (self, s) : self.context_.syntaxError(s)
    def EOFComing (self) :      return self._peekNWSChar()==EOF
    
    def _getNWSChar (self)  : pass
    def _peekNWSChar (self) : pass
    def _getChar (self)     : pass
    def _peekChar (self)    : pass
    def _consumeWS (self)   : pass
    def _pushback (self, pushback_char) : pass

    
class StringReader (ReaderA) :
    """A class to read directly from strings (or any class that supports
    [] and len)"""

    def __init__ (self, input) :
        """Allows to read and parse around anything that can be indexed"""
        ReaderA.__init__(self) # call parent
        # print '************************* input = ', input, type(input)
        self.buffer_ = input   # this is any thing that can be indexed
        self.current_ = 0
    
    # Return the index of the next Non-White Space character.  This is
    # where comments are handled: comments are counted as white space.
    # The default implementation treats # and \n as comments
    def _indexOfNextNWSChar (self) :
        length=len(self.buffer_)
        cur = self.current_
        if (cur==length) : return cur
        # Look for WS or comments that start with #
        comment_mode = False
        while cur<len :
            if (comment_mode) :
                if (self.buffer_[cur]=='\n') : comment_mode = False
                continue
            else :
                if (self.buffer_[cur].isspace()) : continue
                elif (self.buffer_[cur]=='#') :
                    comment_mode = True
                    continue
                else :
                    break
        # All done
        return cur

  
    # Get a the next non-white character from input
    def _getNWSChar(self) :
        index = self._indexOfNextNWSChar()

        # Save all chars read into 
        old_current = self.current_
        self.current_ = index
        self.context_.addData(self.buffer_[old_current:],
                              self.current_-old_current)

        return self._getChar()
  
    # Peek at the next non-white character
    def _peekNWSChar(self) :
        index = self._indexOfNextNWSChar()
        if (index>=len(self.buffer_)) : return EOF
        c = self.buffer_[index]
        return c

    # get the next character
    def _getChar(self) :
        length=len(self.buffer_)
        if (self.current_==length) : return EOF
        
        c = self.buffer_[self.current_] # avoid EOF/int-1 weirdness
        self.current_ += 1
        self.context_.addChar(c)

        # Next char
        return c
  
    # look at the next char without getting it
    def _peekChar(self) : 
        length=len(self.buffer_)
        if (self.current_==length) : return EOF
        c = self.buffer_[self.current_] # avoid EOF/int-1 weirdness
        return c

    # Consume the next bit of whitespace
    def _consumeWS(self) :
        index = self._indexOfNextNWSChar()
        
        old_current = self.current_
        self.current_ = index
        self.context_.addData(self.buffer_[old_current:],
                              self.current_-old_current)
        
        if (index==len(self.buffer_)): return EOF
        c = self.buffer_[index]  # avoid EOF/int-1 weirdness
        return c


    # The pushback allows just a little extra flexibility in parsing:
    # Note that we can only pushback chracters that were already there!
    def _pushback(self, pushback_char) :
        # EOF pushback
        if (pushback_char==EOF) :
            if (self.current_!=len(self.buffer_)) :
                self.syntaxError("Internal Error: Attempt to pushback EOF when not at end")
            else :
                return

        if (self.current_<=0) :
            print "*********************current is", self.current_, self.buffer_
            self.syntaxError("Internal Error: Attempted to pushback beginning of file")
        # Normal char pushback
        else :
            self.current_ -= 1
            if (self.buffer_[self.current_]!=pushback_char) :
                # print "** pushback_char", pushback_char, " buffer", buffer_[current_]
                self.syntaxError("Internal Error: Attempt to pushback diff char")

        self.context_.deleteLastChar()





class StreamReader (ReaderA) :
    """A StreamReader exists to read in data from an input stream  """

    def __init__ (self, istream) :
        """ Open the given file, and attempt to read Vals out of it"""
        ReaderA.__init__(self) # call parent
        self.is_ = istream
        self.cached_ = CircularBuffer(132, True) 


    # istream& is_;
    # CircularBuffer<int> cached_;

    # This routines buffers data up until the next Non-White space
    # character, ands returns what the next ws char is _WITHOUT
    # GETTING IT_.  It returns (c, "peek_ahead") where peek_ahead to
    # indicate how many characters into the stream you need to be to
    # get it.

    # This is the default implementation that treats # and \n as comments
    def _peekIntoNextNWSChar (self) :
        peek_ahead = 0  # This marks how many characters into the stream we need to consume
        start_comment = False
        while (1) :
            # Peek at a character either from the cache, or grab a new char
            # of the stream and cache it "peeking" at it.
            c = ''
            if (peek_ahead >= len(self.cached_)) :
                c = self.is_.read(1)
                self.cached_.put(c);
            else :
                c = self.cached_.peek(peek_ahead)

            # Look at each character individually
            if (c==EOF) :  # EOF
                # We never consume the EOF once we've seen it
                return (c, peek_ahead)
            elif (start_comment) : 
                peek_ahead+=1
                start_comment = (c!='\n')
                continue
            elif (c=='#') : 
                peek_ahead+=1
                start_comment = True
                continue
            elif (c.isspace()) : # white and comments
                peek_ahead+=1
                continue
            else :
                return (c, peek_ahead)


    # Get the next Non White Space character
    def _getNWSChar (self) :
        (_, peek_ahead) = self._peekIntoNextNWSChar()
      
        for ii in xrange(0, peek_ahead) :
            cc_ii = self.cached_.peek(ii);
            if (cc_ii != EOF) :  # Strange EOF char NOT in context!
                self.context_.addChar(cc_ii)
      
        self.cached_.consume(peek_ahead)
  
        return self._getChar() # This will handle syntax error message buffer for char
  

    # Look at but do not consume the next NWS Char
    def _peekNWSChar (self) : 
        (c, _) = self._peekIntoNextNWSChar()
        return c

    # get a char
    def _getChar (self) : 
        if (self.cached_.empty()) :
            cc = self.is_.read(1)
        else :
            cc = self.cached_.get()
    
        if (cc!=EOF) :
            self.context_.addChar(cc)
        return cc
  
  
    def _peekChar (self) :
        if (self.cached_.empty()) :
            c = self.is_.read(1)
            self.cached_.put(c)
        return self.cached_.peek()


    def _consumeWS (self) :
        (c,peek_ahead) = self._peekIntoNextNWSChar()
        for ii in xrange(0,peek_ahead) :
            cc_ii = self.cached_.peek(ii)
            if (cc_ii != EOF) :  # Strange EOF char NOT in context!
                self.context_.addChar(cc_ii)
        self.cached_.consume(peek_ahead)
        return c

    def _pushback (self, pushback_char) :
        if (pushback_char != EOF) : self.context_.deleteLastChar()
        self.cached_.pushback(pushback_char)



########NEW FILE########
__FILENAME__ = pretty
#!/usr/bin/env python

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Similar to to pprint from the pprint module, but tends to expose
nested tables and lists much better for a human-readable format. For
example:

 >>> from pretty import pretty
 >>> a = {'a':1, 'b':[1,2], 'c':{'nest':None} }
 >>> print a
 {'a': 1, 'c': {'nest': None}, 'b': [1, 2]}
 >>> pretty(a)
{
    'a':1,
    'b':[
        1,
        2
    ],
    'c':{
        'nest':None
    }
}

Note that pretty always sorts the keys.  This is essentially how prettyPrint
works in OpenContainers and prettyPrint works in Midas 2k OpalTables.
NOTE!  This was recently updated to remove the excess spaces:  the
prettyPrint in Python and C++ should print exactly the same (i.e.,
you can use diff with them)
"""

# Make it so we can print out nan and inf and eval them too!
# IMPORTANT!  You need these in your environment before you eval
# any tables so that you can get eval to work.  For example:
# >>> a = float('inf')
# >>> print a
# inf
# >>> x = { 'i' : a }
# >>> print x
# {'i': inf}
# >>> eval(repr(x))
# Traceback (most recent call last):
#   File "<stdin>", line 1, in ?
#   File "<string>", line 0, in ?
# NameError: name 'inf' is not defined
# >>>
# >>> from pretty import *          # grabs inf and nan
# >>>
# >>> eval(repr(x))                 # Now it works!!
# {'i': inf}
inf = float('inf')
nan = float('nan')

from pprint import pprint

supports_numeric = False
try :
    import Numeric
    supports_numeric = True
except :
    pass

# Not until 2.7, keep as plain dict then
try :
    from collections import OrderedDict
except :
    OrderedDict = dict


def indentOut_ (stream, indent) :
    """Indent the given number of spaces"""
    if indent == 0 :
        return
    else :
        stream.write(" "*indent)

    
def prettyPrintDictHelper_ (d, stream, indent, pretty_print=True, indent_additive=4) :
    """Helper routine to print nested dicts and arrays with more structure"""
    
    # Base case, empty table
    entries = len(d)
    if entries==0 :
        stream.write("{ }")
        return

    # Recursive case
    stream.write("{")
    if pretty_print: stream.write('\n')

    # Iterate through, printing each element
    ii=0
    keys = d.keys()
    keys.sort()
    for key in keys :  # Sorted order on keys
        if pretty_print : indentOut_(stream, indent+indent_additive)
        stream.write(repr(key)+":")
        value = d[key]
        specialStream_(value, stream, indent, pretty_print, indent_additive)
        if entries>1 and ii!=entries-1 :
            stream.write(",")
        if pretty_print: stream.write('\n')
        ii += 1
        
    if pretty_print : indentOut_(stream, indent)        
    stream.write("}")



# TODO: What should the default of OTab pretty print be?
# o{ 'a': 1, 'b':1 } 
# ['a':1, 'b':2]
# OrderedDict([('a',1), ('b':2)])
# Easiest right now is o{ }, but will revisit
# I also like odict() instead of dict.
OTabEmpty=[ "OrderedDict([])", "o{ }","OrderedDict([])" ]
OTabLeft =[ "OrderedDict([", "o{", "[" ]
OTabRight=[ "])", "}", "]" ]
# OC_DEFAULT_OTAB_REPR = 1
if not "OC_DEFAULT_OTAB_REPR" in dir() :
   OC_DEFAULT_OTAB_REPR  = 1
OTabRepr = OC_DEFAULT_OTAB_REPR;

# To change the printing of OrderedDict
# import pretty
# pretty.OTabRepr = 0

def prettyPrintODictHelper_ (d, stream, indent, pretty_print=True, indent_additive=4) :
    """Helper routine to print nested dicts and arrays with more structure"""
    global OTabRepr
    # Base case, empty table
    entries = len(d)
    if entries==0 :
        stream.write(OTabEmpty[OTabRepr]) # "o{ }"
        return

    # Recursive case
    stream.write(OTabLeft[OTabRepr]) # "o{"
    if pretty_print: stream.write('\n')

    # Iterate through, printing each element
    ii=0
    keys = d.keys()
    for key in keys :  # Insertion order on keys
        if pretty_print : indentOut_(stream, indent+indent_additive)
        if OTabRepr == 0 :
            stream.write("("+repr(key)+", ")
        else :
            stream.write(repr(key)+":")
        value = d[key]
        specialStream_(value, stream, indent, pretty_print, indent_additive)
        if OTabRepr == 0 :
            stream.write(")")
            
        if entries>1 and ii!=entries-1 :
            stream.write(",")
        if pretty_print: stream.write('\n')
        ii += 1
        
    if pretty_print : indentOut_(stream, indent)        
    stream.write(OTabRight[OTabRepr])  # "}"


def prettyPrintListHelper_ (l, stream, indent, pretty_print=True, indent_additive=4) :
    """Helper routine to print nested lists and arrays with more structure"""
    
    # Base case, empty table
    entries = len(l)
    if entries==0 :
        stream.write("[ ]")
        return
    
    # Recursive case
    stream.write("[")
    if pretty_print: stream.write('\n')

    # Iterate through, printing each element
    for ii in xrange(0,entries) :
        if pretty_print : indentOut_(stream, indent+indent_additive)
        specialStream_(l[ii], stream, indent, pretty_print, indent_additive)
        if entries>1 and ii!=entries-1 :
            stream.write(",")
        if pretty_print: stream.write('\n')

    if pretty_print : indentOut_(stream, indent); 
    stream.write("]")



def prettyPrintStringHelper_ (s, stream, indent, pretty_print=True, indent_additive=4):
    """Helper routine to print strings"""
    stream.write(repr(s))

# List of special pretty Print methods
OutputMethod = { str           :prettyPrintStringHelper_,
                 OrderedDict   :prettyPrintODictHelper_,
                 dict          :prettyPrintDictHelper_,
                 list          :prettyPrintListHelper_
               }

def formatHelp_ (format_str, value, strip_all_zeros=False) :
    s = format_str % value
    # All this crap: for complex numbers 500.0+0.0j should be 500+0
    # (notice it strips all zeros for complexes) 
    if strip_all_zeros :
        where_decimal_starts = s.find('.')
        if where_decimal_starts == -1 :
            return s   # all done, no 0s to strip after .
        where_e_starts = s.find('E')
        if where_e_starts == -1 :  # no e
            where_e_starts = len(s)
        dot_to_e = s[where_decimal_starts:where_e_starts].rstrip('0')
        if len(dot_to_e)==1 : # just a .
            dot_to_e = ""
        return s[:where_decimal_starts]+dot_to_e+s[where_e_starts:]
    else :
        if not ('E' in s) and s.endswith('0') and '.' in s:
            s = s.rstrip('0')
            if s[-1]=='.' : s+='0'
    return s

def NumericString_ (typecode, value) :
    """ floats need to print 7 digits of precision, doubles 16"""
    if typecode == 'f'   :
        return formatHelp_("%#.7G", value)
    
    elif typecode == 'd' :
        return formatHelp_("%#.16G", value)
    
    elif typecode == 'F' :
        front = '('+formatHelp_("%#.7G", value.real, strip_all_zeros=True)
        if value.imag==0 :
            front += "+0j)"
        else :
            front += formatHelp_("%+#.7G", value.imag, strip_all_zeros=True)+"j)"
        return front
        
    elif typecode == 'D' :
        front = '('+formatHelp_("%#.16G", value.real, strip_all_zeros=True)
        if value.imag==0 :
            front += "+0j)"
        else :
            front += formatHelp_("%+#.16G", value.imag, strip_all_zeros=True)+"j)"
        return front
    
    else :
        return str(value)
    
def specialStream_ (value, stream, indent, pretty_print, indent_additive) :
    """Choose the proper pretty printer based on type"""
    global OutputMethod
    type_value = type(value)
    if type_value in OutputMethod:  # Special, indent
        output_method = OutputMethod[type_value]
        indent_plus = 0;
        if pretty_print:indent_plus = indent+indent_additive
        output_method(value, stream, indent_plus, pretty_print, indent_additive)
    elif supports_numeric and type_value == type(Numeric.array([])) :
        stream.write('array([')
        l = value.tolist()
        typecode = value.typecode()
        for x in xrange(0,len(l)) :
            r = NumericString_(typecode, l[x])
            stream.write(r)
            if x<len(l)-1 : stream.write(",")
        stream.write('], '+repr(value.typecode())+")")
    elif type_value in [float, complex] : 
        typecode = { float: 'd', complex: 'D' }
        stream.write(NumericString_(typecode[type_value], value))
    else :
        stream.write(repr(value))

import sys

def pretty (value, stream=sys.stdout, starting_indent=0, indent_additive=4) :
    """Output the given items in such a way as to highlight
    nested structures of Python dictionaries or Lists.  By default,
    it prints to sys.stdout, but can easily be redirected to any file:
    >>> f = file('goo.txt', 'w')
    >>> pretty({'a':1}, f)
    >>> f.close()
    """
    indentOut_(stream, starting_indent)
    pretty_print = 1
    specialStream_(value, stream, starting_indent-indent_additive, pretty_print, indent_additive)
    if type(value) in [list, dict, OrderedDict] :
        stream.write('\n')


if __name__=="__main__":
    # Test it
    import sys
    a = [1, 'two', 3.1]
    pretty(a)
    pretty(a,sys.stdout,2)
    pretty(a,sys.stdout,2,2)

    pretty(a)
    pretty(a,sys.stdout,1)
    pretty(a,sys.stdout,1,1)

    t = {'a':1, 'b':2}
    pretty(t)
    pretty(t,sys.stdout,2)
    pretty(t,sys.stdout,2,2)

    pretty(t)
    pretty(t,sys.stdout,1)
    pretty(t,sys.stdout,1,1)


########NEW FILE########
__FILENAME__ = simplearray
#! /bin/env

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Simple array wrapper: Looks like the Numeric array (with same constructors
   and the like), but implemented as a Python array"""

import array
import pretty
import struct

# Array is very pickly about what fits inside, so we have to
# manually stomp the ranges
TypeRanges = {
  'b': (1, [-128,127,0xff,'b','B',int]),
  'B': (1, [0,255,0xff,'b','B',int]),
  'h': (2, [-32768,32767,0xffff,'h','H',int]),
  'H': (2, [0,65535,0xffff, 'h','H',int]),
  'i': (4, [-2147483648,2147483647, 0xffffffff, 'i', 'I', int]),
  'I': (4, [0, 4294967295, 0xffffffff, 'i', 'I', int]),
  'l': (8, [-9223372036854775808,9223372036854775807, 0xffffffffffffffff, 'l', 'L', int]),
  'L': (8, [0, 18446744073709551615, 0xffffffffffffffff, 'l', 'L', int]),
  'f': (4, [float('-inf'), float("inf"), 0, 'f', 'f', float]),
  'd': (4, [float('-inf'), float("inf"), 0, 'd', 'd', float]),                 
}

# Allow us to convert between Numeric typecodes and "array" typecodes
NumericToArray = {
    '1': ('b',1), 'b':('B',1),
    's': ('h',1), 'w':('H',1),
    'i': ('i',1), 'u':('I',1),
    'l': ('l',1), # 'l':('L',1),
    'f': ('f',1), 'd':('d',1),
    'F': ('f',2), 'D':('d',2), # complex supported but at TWICE the size
}
class SimpleArray(object) :
    """Simple array wrapper that looks like a simple Numeric array,
    but uses Python array underneath.  Not a full implementation, but
    handles complex numbers (unlike array) and also clips overflowing
    values (array likes to throw exceptions if the values are out of range)"""

    def __init__(self, initializing_list, typecode) :
        """Create an Numeric-like array object, using Numeric typecodes"""
        global TypeRanges, NumericToArray
        array_typecode = NumericToArray[typecode][0]
        self.numeric_typecode = typecode
        self.impl = array.array(array_typecode)
        self.complex = (typecode=='F' or typecode=='D')
        for x in initializing_list :
            self.append(x)
            
    def append(self, value) :
        """Append the appropriate item into the list"""
        global TypeRanges, NumericToArray
        a = self.impl
        if self.complex : # complex, append twice!
            if type(value) == complex :
                a.append(value.real)
                a.append(value.imag)
            else :
                a.append(float(value))
                a.append(0.0)
            
        else :
            a.append(self._crop(value))

    def _crop(self, value) :
        # Convert integer values out of range into proper range
        a = [left, right, mask, signed_code, unsigned_code, converter] = TypeRanges[self.impl.typecode][1]
        if value < left or value > right:
            value = value & mask
            if left < 0 :  # Handle signed as C would
                b = struct.pack(unsigned_code, value)
                value = struct.unpack(signed_code, b)[0]
        return converter(value)
        
    def __getitem__(self,ii) :
        a = self.impl
        if self.complex :
            return complex(a[ii*2], a[ii*2+1])
        else :
            return a[ii]

    def __setitem__(self, ii, value) :
        a = self.impl
        if self.complex :
            if type(value)==complex :
                a[ii*2] = value.real
                a[ii*2+1] = value.imag
            else :
                a[ii*2] = float(value)
                a[ii*2+1] = 0.0
        else :
            a[ii] = self._crop(value)

    def __len__ (self) :
        a = self.impl
        if self.complex : return len(a)/2
        return len(a)

    def __str__(self) :
        a = self.impl
        length = len(self)
        out = "array(["
        for ii in xrange(0, length) :
            out += str(self[ii])
            if ii!=length-1 : out += ","
        out += "], "+repr(self.numeric_typecode)+")"
        return out

    def __repr__(self) :
        a = self.impl
        length = len(self)
        numeric_typecode = self.numeric_typecode
        out = "array(["
        for ii in xrange(0, length) :
            out += pretty.NumericString_(numeric_typecode, self[ii]) 
            if ii!=length-1 : out += ","
        out += "], "+repr(numeric_typecode)+")"
        return out

    def __eq__ (self, rhs) :
        if type(rhs) != type(self) : return False
        if len(self)==len(rhs) and self.numeric_typecode==rhs.numeric_typecode :
            for x in xrange(0,len(self)) :
                if self[x] != rhs[x] :
                    return False
            return True
        return False
    
    def toarray (self) :
        """Return the underlying Python array: Note that complex data are
        stored as real, imag pairs in a float array."""
        return self.impl
    def tolist (self) :
        """Convert the array to a Python list"""
        if self.complex :
            result = []
            for x in xrange(0,len(self)) :
                result.append(self[x])
            return result
        else :
            return self.impl.tolist()

    def typecode (self) :
        """Return the typecode as Numeric would"""
        return self.numeric_typecode

if __name__ == "__main__" :
    a = SimpleArray([1,2,3], 'i')
    print a[0]
    print len(a)
    a.append(4)
    print a[3]
    print a
    print repr(a)
    b = SimpleArray([1+2j,3+4j], 'D')
    print b[0]
    print len(b)
    b.append(1)
    b.append(6+7j)
    print b[2]
    print b[3]
    print b
    print repr(b)

########NEW FILE########
__FILENAME__ = xmldumper
#!/bin/env python

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
   This class convert dictionaries to XML.  This is usually
   an easy mapping, because key-value mappings go easily to XML
   (the other way is more problematic).  A potential issue
   usually is how to handle attributes.... See the options below!

   Examples:
  
    { 'book' = {
          'chapter' = [ 'text chap 1', 'text chap 2']
          '__attrs__' = { 'attr1':"1", 'attr2':"2" }
    }
    --------dumps as --------------
    <book attr1="1" attr2="2">
       <chapter>text chap 1</chapter>
        <chapter>text chap 2</chapter>
    </book>
   

   With UNFOLDING on  (attributes are marked with _)
  
    { 'book' = {
          'chapter' = [ 'text chap 1', 'text chap 2']
          '_attr1':"1", 
          '_attr2':"2" 
       }
    }
    ---------dumps as --------------
    <book attr1="1" attr2="2">
        <chapter date="1999">text chap 1</chapter>
        <chapter data="2000">text chap 2</chapter>
    </book>
"""

import sys
import pretty
from curses.ascii import isprint

# Not until 2.7, keep as plain dict then
try :
    from collections import OrderedDict
except :
    OrderedDict = dict

# All the arrays we may get when iterating through: if someone gives
# us the data structure (Numeric array or Python array), we still try
# to dump it.
from arraydisposition import *
array_types = []
try :
    import Numeric
    array_types.append(type(Numeric.array([]))) # Tag doesn't effect type
except :
    pass
try :
    import array
    array_types.append(array.array)
except :
    pass
import simplearray
array_types.append(simplearray.SimpleArray)

import pretty

# Options for dictionaries -> XML
#  If XML attributes are being folded up, then you may
#  want to prepend a special character to distinguish attributes
#  from nested tags: an underscore is the usual default.  If
#  you don't want a prepend char, use XML_DUMP_NO_PREPEND option
XML_PREPEND_CHAR = '_'


# When dumping, by DEFAULT the keys that start with _ become
# attributes (this is called "unfolding").  You may want to keep
# those keys as tags.  Consider:
#
#   { 'top': { '_a':'1', '_b': 2 }} 
# 
# DEFAULT behavior, this becomes:
#   <top a="1" b="2"></top>       This moves the _names to attributes
#  
# But, you may want all _ keys to stay as tags: that's the purpose of this opt
#   <top> <_a>1</_a> <_b>2</b> </top>
XML_DUMP_PREPEND_KEYS_AS_TAGS = 0x100

# Any value that is simple (i.e., contains no nested
# content) will be placed in the attributes bin:
#  For examples:
#    { 'top': { 'x':'1', 'y': 2 }} ->  <top x="1" y="2"></top>
XML_DUMP_SIMPLE_TAGS_AS_ATTRIBUTES = 0x200

# By default, everything dumps as strings (without quotes), but those things
# that are strings lose their "stringedness", which means
# they can't be "evaled" on the way back in.  This option makes 
# Vals that are strings dump with quotes.
XML_DUMP_STRINGS_AS_STRINGS = 0x400

# Like XML_DUMP_STRINGS_AS_STRINGS, but this one ONLY
# dumps strings with quotes if it thinks Eval will return
# something else.  For example in { 's': '123' } : '123' is 
# a STRING, not a number.  When evalled with an XMLLoader
# with XML_LOAD_EVAL_CONTENT flag, that will become a number.
XML_DUMP_STRINGS_BEST_GUESS = 0x800

# Show nesting when you dump: like "prettyPrint": basically, it shows
# nesting
XML_DUMP_PRETTY = 0x1000

# Arrays of POD (plain old data: ints, real, complex, etc) can
# dump as huge lists:  By default they just dump with one tag
# and then a list of numbers.  If you set this option, they dump
# as a true XML list (<data>1.0/<data><data>2.0</data> ...)
# which is very expensive, but is easier to use with other
# tools (spreadsheets that support lists, etc.).
XML_DUMP_POD_LIST_AS_XML_LIST = 0x2000


# When dumping an empty tag, what do you want it to be?
# I.e., what is <empty></empty>  
# Normally (DEFAULT) this is an empty dictionary 'empty': {}
# If you want that to be empty content, as in an empty string,
# set this option: 'empty': ""
# NOTE: You don't need this option if you are using
# XML_DUMP_STRINGS_AS_STRINGS or XML_DUMP_STRINGS_BEST_GUESS
XML_DUMP_PREFER_EMPTY_STRINGS = 0x4000

# When dumping dictionaries in order, a dict BY DEFAULT prints
# out the keys in sorted/alphabetic order and BY DEFAULT an OrderedDict
# prints out in the OrderedDict order.  The "unnatural" order
# for a dict is to print out in "random" order (but probably slightly
# faster).  The "unnatural" order for an OrderedDict is sorted
# (because normally we use an OrderedDict because we WANTS its
# notion of order)
XML_DUMP_UNNATURAL_ORDER = 0x8000

# Even though illegal XML, allow element names starting with Digits:
# when it does see a starting digit, it turns it into an _digit
# so that it is still legal XML
XML_TAGS_ACCEPTS_DIGITS  = 0x80

# When dumping XML, the default is to NOT have the XML header 
# <?xml version="1.0">:  Specifying this option will always make that
# the header always precedes all content
XML_STRICT_HDR = 0x10000


class XMLDumper(object) :
  """An instance of this will help dump a Python object (made up of lists,
     dictionaries, Numeric data and all primitive types as XML"""

  # On error, do you want to throw exception, silently continue or warn
  # on stderr?  Usually errors happens when there are multiple attributes
  # that conflict.
  SILENT_ON_ERROR = 1
  CERR_ON_ERROR   = 2
  THROW_ON_ERROR  = 3 

  def __init__ (self, os, options=0,
                array_disposition=ARRAYDISPOSITION_AS_LIST,
                indent_increment=4,
                prepend_char=XML_PREPEND_CHAR, 
                mode = 2) : # XMLDumper.CERR_ON_ERROR
      """Create am XML dumper.  Note that options are | together:
      XMLDumper xd(cout, XML_DUMP_PRETTY | XML_STRICT_HDR)
      """
      # Handle 
      if array_disposition == ARRAYDISPOSITION_AS_NUMERIC :
          import Numeric # let this throw the exception
      if array_disposition == ARRAYDISPOSITION_AS_NUMERIC_WRAPPER :
          import simplearray # let this throw the exception
      if array_disposition == ARRAYDISPOSITION_AS_PYTHON_ARRAY :
          import array   # let this throw the exception
      
      self.os_ = os
      self.options_ = options
      self.arrDisp_ = array_disposition
      self.indentIncrement_ = indent_increment
      self.prependChar_ = prepend_char
      self.mode_ = mode
      self.specialCharToEscapeSeq_ = { }
      self.NULLKey_ = None  # Has to be non-string meta-value so "is" test won't fail with ""
      self.EMPTYAttrs_ = { }
      self.LISTAttrs_ = { }
      self.DICTTag_ = "dict__"
  
      self.specialCharToEscapeSeq_['&'] = "&amp;"
      self.specialCharToEscapeSeq_['<'] = "&lt;"
      self.specialCharToEscapeSeq_['>'] = "&gt;"
      self.specialCharToEscapeSeq_['\"'] = "&quot;"
      self.specialCharToEscapeSeq_['\''] = "&apos;"
      self.LISTAttrs_["type__"] = "list"

      # ostream& os_;             // Stream outputting to
      # int options_;             // OR ed options
      # ArrayDisposition_e arrDisp_; // How to handle POD data
      # int indentIncrement_; // How much to up the indent at each nesting level
      # char prependChar_;        // '\0' means NO prepend char
      # XMLDumpErrorMode_e mode_; // How to handle errors: silent, cerr,or throw
      # HashTableT<char, string, 8> 
      # specialCharToEscapeSeq_;  // Handle XML escape sequences
      # string NULLKey_;          // Empty key
      # Tab    EMPTYAttrs_;       // Empty Attrs when dumping a primitive
      # Tab    LISTAttrs_;        // { "type__" = 'list' } 
      # string DICTTag_;          // "dict__"

      
  def XMLDumpValue (self, value, indent=0) :
      "Dump without a top-level container (i.e., no containing top-level tag)"
      self.XMLDumpKeyValue(self.NULLKey_, value, indent) # handles header too

  def XMLDumpKeyValue (self, key, value, indent=0) :
      "Dump with the given top-level key as the top-level tag."
      self._XMLHeader()

      # Top level lists suck: you can't "really" have a
      # list at the top level of an XML document, only
      # a table that contains a list!
      if type(value)==list :
          a = value
          p = a        # DO NOT adopt, just sharing reference
          top = { }
          top["list__"] = p
          self._XMLDumpKeyValue(key, top, indent)
      else :
          self._XMLDumpKeyValue(key, value, indent)
          
  
  def dump (self, key, value, indent=0) :
      """Dump *WITHOUT REGARD* to top-level container and/or XML header:
      this allows you to compose XML streams if you need to: it just
      dumps XML into the stream."""
      self._XMLDumpKeyValue(key, value, indent)
      
  def dumpValue (self, value, indent=0) :
      """Dump *WITHOUT REGARD* to top-level container and/or XML header:
      this allows you to compose XML streams if you need to: it just
      dumps XML (value only) into the stream."""
      self._XMLDumpKeyValue(self.NULLKey_, value, indent)

  def mode (self, mode) :
      """If the table is malformed (usually attributes conflicting), throw
      a runtime error if strict.  By default, outputs to cerr"""
      self.mode_ = mode 


  # Handle the XML Header, if we want to dump it
  def _XMLHeader (self) :
      if self.options_ & XML_STRICT_HDR :
          self.os_.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")

  # Dump, but allow passage of attributes
  def _XMLDumpKeyValue (self, key, value, indent=0, attrs_ptr=None,
                        was_array_typecode=None):
      t = type(value)
      if t==dict :
          
          if self.options_ & XML_DUMP_UNNATURAL_ORDER : # may want speed
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=False)
          else : # Natural order (for predictability) 
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=True)
              
      elif t==OrderedDict :
          
          if self.options_ & XML_DUMP_UNNATURAL_ORDER : # may still want sorted
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=True)
          else : # Natural order of an odict is the order of the odict
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=False)
              
      elif t==list or t==tuple :
          self._XMLDumpList(key, value, indent, was_array_typecode)
      elif t in array_types :
          self._XMLDumpPODList(key, value, indent, -1, False)
      else :
          self._XMLDumpPrimitive(key, value, indent, attrs_ptr, was_array_typecode)

  # Dump just the name and make sure it's well-formed tag name
  # (or attribute name): TODO: This may be too restrictive
  def _XMLDumpName (self, tag) :
      if len(tag)==0 :
          self._handleProblem("tag cannot be empty (0 length)")
    
      t = tag
      if t[0].isdigit() :
          if self.options_ & XML_TAGS_ACCEPTS_DIGITS :
              self.os_.write('_')
          else :
              self._handleProblem("tag must start with alphabetic or _, not "+t[0])
      elif not(t[0].isalpha() or t[0]=='_') :
          self._handleProblem("tag must start with alphabetic or _, not "+t[0])
    
      for ii in xrange(1, len(tag)) :
          if not (t[ii].isalnum() or t[ii]=='_' or t[ii]==':') :
              self._handleProblem("tag must contain alphanumeric or _, not "+t[ii])
      
      self.os_.write(tag) # All good
  

  # Dump content: this means handling escape characters
  def _XMLContentFilter (self, content, was_array_typecode=None) :
      result = "" # RVO
      typecode = { float:'d', complex:'D' }
      type_content = type(content)
      if was_array_typecode != None :
          t = pretty.NumericString_(was_array_typecode, content)
      elif type_content in [float, complex] :
          t = pretty.NumericString_(typecode[type_content], content)
      elif type_content == long :
          t = repr(content)
      else : 
          t = str(content)
      for ii in xrange(0,len(t)) :
          c = t[ii]
          if not isprint(c) :
              result += "&#"+hex(ord(c))[1:]+";"
          else :
              if c in self.specialCharToEscapeSeq_ :
                  esc_seq = self.specialCharToEscapeSeq_[t[ii]]
                  result = result + esc_seq
              else :
                  result = result + t[ii]
      return result


  # Dump the start tag, with attention to formatting and options
  def _XMLDumpStartTag (self, tag, attrs, indent,
                        primitive_dump=False, none_dump=False,
                        was_array_typecode=None) :
      if tag is self.NULLKey_ : return

      if self.options_ & XML_DUMP_PRETTY :
          self.os_.write( ' '*indent )
      self.os_.write('<')
      self._XMLDumpName(tag)
      
      # Attributes  key1="something" key2="somethingelse"
      len_attrs = len(attrs)
      if len_attrs >= 1 : self.os_.write(" ")
      where = 0
      for key, val in sorted(attrs.iteritems()) :
          # String as is
          attr_name = str(key)
          if (len(attr_name)>0 and attr_name[0]==self.prependChar_ and
              ((self.options_ & XML_DUMP_PREPEND_KEYS_AS_TAGS)==0) ) :
              attr_name = attr_name[1:] # strip _
          
          attr_val = str(val)
      
          #os_ << attr_name << "=" << attr_val;
          self._XMLDumpName(attr_name)
          self.os_.write("=\"" + self._XMLContentFilter(attr_val, was_array_typecode) + "\"") # TODO: handle '

          where += 1
          if (where!=len_attrs) : # last one, no extra space
              self.os_.write(" ") 
      
      if none_dump: self.os_.write("/")
      self.os_.write(">")
      if ((self.options_ & XML_DUMP_PRETTY)!=0) and (not primitive_dump or none_dump) :
          self.os_.write("\n")



  # Dump the end tag, with attention to output options and formatting
  def _XMLDumpEndTag (self, tag, indent, primitive_dump=False) :
    if tag is self.NULLKey_ :
        return
    if ((self.options_ & XML_DUMP_PRETTY) and not primitive_dump) :
        self.os_.write(' '*indent)
    self.os_.write("</"+tag+">") # Note: Already checked that tag is okay! 
    if (self.options_ & XML_DUMP_PRETTY) :
        self.os_.write("\n")


  # Does the tag represent a composite object: any container is
  # a composite: Tab, Arr, Tup, OTab 
  # primitive data: string, complex, int, float, etc.
  def _IsComposite (self, v) :
      t = type(v)
      return t in [tuple, dict, list, OrderedDict] or t in array_types


  # Find all key-values that could be XML attributes 
  def _FindAttributes (self, t) :
      # Collect all things that could be attributes
      attrs = { }   # RVO
      if "__attrs__" in t :  # We want to discover automatically:
          # Attributes all in special key '__attrs__'
          attrs = t["__attrs__"]
          
      # Attributes may also have to be found
      sorted_keys = sorted(t.keys())
      for key in sorted_keys :
          value = t[key]
      ##for key, value in sorted(t.iteritems()) :
          if key=="__attrs__": continue  # already processed
          if key=="__content__": continue # special

          # Special character says they *MAY* become attributes
          if (len(key)> 0 and key[0] == self.prependChar_) :
              if key in attrs :
                  self._handleProblem(key+string(" already in ")+str(t))
	
              key_without_underscore = key[1:]
              if (self.options_ & XML_DUMP_PREPEND_KEYS_AS_TAGS)==0 :
                  attrs[key_without_underscore] = value
                  continue
	
          # Do All simple values become attributes?
          if (self.options_ & XML_DUMP_SIMPLE_TAGS_AS_ATTRIBUTES) :
              simple = not self._IsComposite(value)
              if key in attrs :
                  self._handleProblem(key+string(" already in ")+str(t))
	
              if simple :
                  attrs[key] = value
              continue
      # All done
      return attrs

  
  def _XMLDumpList (self, list_name, l, indent, was_array_typecode=None) :
    # This strange business is to handle lists with no names:
    # either nested within other lists or at the top-level so it will
    # still form well-formed XML: this is pretty rare, but we should
    # still do something useful.
    if list_name is self.NULLKey_ :
        tag = "list__"
    else :
        tag = list_name

    # Empty list
    if len(l)==0 :   # Force list type__ so will unXMLize as an Arr()
        self._XMLDumpPrimitive(tag, None, indent, self.LISTAttrs_)
        return

    # Non-empty list
    for ii in xrange(0, len(l)) :
        key_to_use = self.NULLKey_   # normally NULL RARELY: empty list
        value_ptr = l[ii]
      
        # This strange bit is because a table is directly inside a 
        # list, which means there IS no tag, which normally would be
        # an extra indent with an empty name: this is specifically because
        # of the dict within a list.  A table inside can also mean
        # the __contents__
        table_inside_value = type(value_ptr)==dict or type(value_ptr)==OrderedDict
        indent_inc = self.indentIncrement_
        attrs = { }
        if (table_inside_value) :
            indent_inc = 0
            attrs = self._FindAttributes(value_ptr)
            # Special rare case: contents in special key
            if ("__content__" in value_ptr) :
                value_ptr = value_ptr["__content__"]

            if (type(value_ptr)==dict or type(value_ptr)==OrderedDict) and len(value_ptr)==0 and len(l)==1 :
                # This RARE situation:  
                # { 'top': [ {} ] } -> <top type__="list"> <dict__/> </top>
                # Empty table inside a list: Ugh: hard to express in XML
                # without a new tag ... it's basically an anonymous table:
                # Normally, it's easy to detect a table, but an empty
                # dict inside a list is a special case
                indent_inc = self.indentIncrement_
                key_to_use = self.DICTTag_
	
	
        elif type(value_ptr) in array_types and \
             self.arrDisp_ != ARRAYDISPOSITION_AS_LIST :
	    #### Array data, well has peculilarities: let it handle it
            self._XMLDumpPODList(tag, value_ptr, indent, ii, 
                                 (ii==0 and len(l)==1))
            continue
      
        # If list of 1, preserve listness by adding type field
        if (ii==0 and len(l)==1) :
            attrs["type__"]="list"
      
        primitive_type = not self._IsComposite(value_ptr)
        self._XMLDumpStartTag(tag, attrs, indent, primitive_type, False,
                              was_array_typecode)
        self._XMLDumpKeyValue(key_to_use, value_ptr, indent+indent_inc, None, 
                              was_array_typecode)
        self._XMLDumpEndTag(tag, indent, primitive_type)
    
        
  # Dump a list of binary data as a tag with one special key:
  # arraytype__ = "<typetag>" which is some typetag (silxfdSILXFD)
  # or, every individual element as a "type__" = <typetag>"
  def _XMLDumpPODList (self, list_name, l, 
                       indent, inside_list_number, add_type):
      # tag = str(list_name)
      tag = list_name

      # Check to see if we want to dump this as a LIST or plain POD array
      if self.arrDisp_ == ARRAYDISPOSITION_AS_LIST :
          # This works works with array.array and Numeric.array because
          # the floating point typecodes are essentially the same,
          # and both support typecode and tolist
          was_array_typecode = l.typecode
          if callable(l.typecode) : was_array_typecode = l.typecode()
          # float types
          if not was_array_typecode in ['f','F','d','D'] : 
              was_array_typecode = None
          l = l.tolist()
          # Integer types
          if was_array_typecode == None :  
              l = [int(x) for x in l]
              
          self._XMLDumpList(list_name, l, indent, was_array_typecode)
          return

      # The attributes for an Array of POD will the Numeric type tag
      attrs = { }
      lookup_table = {'1':'s','b':'S', 's':'i','w':'I', 'i':'l','u':'L', 'l':'x', 'f':'f', 'd':'d', 'F':'F', 'D':'D' }
      bytetag = lookup_table[l.typecode()]
      if (self.options_ & XML_DUMP_POD_LIST_AS_XML_LIST) :
          attrs["type__"] = bytetag
      else :
          attrs["arraytype__"] = bytetag

      # There are two ways to dump Array data: either as one tag
      # with a list of numbers, or a tag for for every number.
      # Dumping array data with a tag for every number works better with 
      # other tools (spreasheet etc.), but if you annotate EVERY ELEMENT 
      # of a long list, the XML becomes much bigger and slow.

      # Dump array with a tag for EVERY element
      primitive_type = True
      temp = None
      inner_tag = tag
      if (self.options_ & XML_DUMP_POD_LIST_AS_XML_LIST) :
          # Rare case when POD array inside list
          if (inside_list_number!=-1) :
              inner_attrs = { }
              if inside_list_number==0 and add_type :
                  inner_attrs["type__"]="list"
              self._XMLDumpStartTag(tag, inner_attrs, indent, False)
              inner_tag = "list"+str(inside_list_number)+"__"
              indent += self.indentIncrement_
              
          if len(l)==0 :
              # Empty list
              self._XMLDumpStartTag(inner_tag, attrs, indent, primitive_type)
              self._XMLDumpEndTag(inner_tag, indent, primitive_type)
          else :
              # Non-empty list
              for ii in xrange(0, len(l)) :
                  self._XMLDumpStartTag(inner_tag, attrs, indent, primitive_type)
                  temp = pretty.NumericString_(bytetag, l[ii])       #repr(l[ii])  # so prints with full precision of Val for reals, etc.
                  self.os_.write(temp)
                  self._XMLDumpEndTag(inner_tag, indent, primitive_type)
                  
          # Rare case when POD array inside list
          if (inside_list_number!=-1) :
              indent -= self.indentIncrement_
              self._XMLDumpEndTag(tag, indent, False)
    
      # Dump as a list of numbers with just one tag: the tag, the list of data, 
      # then the end tag      
      else :
          if (inside_list_number==0 and add_type) : attrs["type__"]="list"
          self._XMLDumpStartTag(tag, attrs, indent, primitive_type)
          for ii in xrange(0, len(l)) :
              temp = pretty.NumericString_(bytetag, l[ii])       #repr(l[ii])  # so prints with full precision of Val for reals, etc. 
              self.os_.write(temp)
              if (ii<len(l)-1) : self.os_.write(",")
          # End
          self._XMLDumpEndTag(tag, indent, primitive_type)


  # Dump a table t
  def _XMLDumpTable (self, dict_name, t, indent, attrs_ptr, sortkeys):
      # Rare case: when __content__ there
      if "__content__" in t :
          attrs = self._FindAttributes(t)
          self._XMLDumpKeyValue(dict_name, t["__content__"], indent, attrs)
          return
      
      # Get attributes, Always dump start tag
      if attrs_ptr == None :
          attrs = self._FindAttributes(t)
      else :
          attrs = attrs_ptr
      self._XMLDumpStartTag(dict_name, attrs, indent)
    
      # Normally, just iterate over all keys for nested content
      keys = t.keys()
      if sortkeys : keys.sort()
      for key in keys :
          value = t[key]

          # Skip over keys that have already been put in attributes
          k = str(key)
          if key in attrs or k=="__attrs__" or (len(k)>0 and k[0]==self.prependChar_ and k[1:] in attrs) :
              continue # Skip in attrs

          self._XMLDumpKeyValue(key, value, indent+self.indentIncrement_)

      # Always dump end tag
      self._XMLDumpEndTag(dict_name, indent)

  
  # Dump a primitive type (string, number, real, complex, etc.)
  def _XMLDumpPrimitive (self, key, value, indent, attrs_ptr, was_array_typecode=None) :
      if attrs_ptr is None :
          attrs = self.EMPTYAttrs_
      else :
          attrs = attrs_ptr

      if (self._IsComposite(value)) :
          raise Exception("Trying to dump a composite type as a primitive")
  
      if value is None :
          self._XMLDumpStartTag(key, attrs, indent, True, True)
          return

      self._XMLDumpStartTag(key, attrs, indent, True)

      # Force all strings into quotes, messy but will always work
      # with XML_LOAD_EVAL_CONTENT on the way back if you have to convert
      if (self.options_ & XML_DUMP_STRINGS_AS_STRINGS) :
          if (type(value) == str) : # make sure pick up quotes 
              self.os_.write(self._XMLContentFilter(repr(value), was_array_typecode))
          else :
              self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # Let str pick 

      # Most of the time, we can keep all strings as-is (and avoid
      # those nasty '&apos;' quotes in XML around them): those
      # strings that will become something "real values" when Evalled 
      # need to have quotes so they will come back as strings
      # when using XML_LOAD_EVAL_CONTENT.  For example: '123' is a string
      # but when evaled, will become a number;  We dump this as 
      # "&apos;123&apos;" to preserve the numberness.
      elif (self.options_ & XML_DUMP_STRINGS_BEST_GUESS) :
          if (type(value)==str) :
              s = str(value)    # no quotes on string
              if (len(s)==0 or # always dump empty strings with &apos!
                  ((len(s)>0) and 
                   (s[0].isdigit() or s[0]=='(' or s[0]=='-' or s[0]=='+'))) :
                  # If it starts with a number or a sign or '(' (for (1+2j), 
                  # probably a number and we WANT to stringize
                  self.os_.write(self._XMLContentFilter(repr(value), was_array_typecode)) # puts quotes on str
              else :
                  self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # no quotes!
          else :
              self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # Let str pick 
  

      # Default, just plop content: still be careful of <empty></empty>:
      # Should that be a {}, None, [], or ""?  With this option, makes it
      # empty string (you don't need this option if you are using
      # XML_DUMP_STRINGS_BEST_GUESS or XML_DUMP_STRINGS_AS_STRINGS
      else :
          if (self.options_ & XML_DUMP_PREFER_EMPTY_STRINGS) :
              if type(value)==str and len(value)==0 :
                  value =  "''"  # Makes <empty></empty> into empty string

          self.os_.write(self._XMLContentFilter(value, was_array_typecode))
  
      self._XMLDumpEndTag(key, indent, True)


  # Centralize error handling
  def _handleProblem (self, text):
      if (self.mode_==XMLDumper.SILENT_ON_ERROR) : return
      if (self.mode_==XMLDumper.THROW_ON_ERROR) :
          raise Exception, text
      sys.stderr.write(text+"\n")




# ############################# Global Functions

def WriteToXMLStream (v, ofs, top_level_key = None,
                      options = XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS, # best options for invertible transforms
                      arr_disp = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                      prepend_char=XML_PREPEND_CHAR) :
    """Write a Python object (usually a dict or list)  as XML to a stream:
    throw a runtime-error if anything bad goes down.
    These default options:
    options=XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS 
    are the best options for invertible transforms.
    Array disposition: AS_LIST (0) might be better for dealing with Python,
    but you are much less  likely to lose information by using the default
    AS_NUMERIC_WRAPPER"""
    indent = 2
    xd = XMLDumper(ofs, options, arr_disp, indent, prepend_char,
                   XMLDumper.THROW_ON_ERROR)
    if top_level_key==None:
        xd.XMLDumpValue(v)
    else :
        xd.XMLDumpKeyValue(top_level_key, v)


def WriteToXMLFile (v, filename, top_level_key = None,
                    options = XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS, # best options for invertible transforms
                    arr_disp = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                    prepend_char=XML_PREPEND_CHAR) :
    """Write a Python object (usually a dict or list)  as XML to a file:
    throw a runtime-error if anything bad goes down.
    These default options:
    options=XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS 
    are the best options for invertible transforms.
    Array disposition: AS_LIST (0) might be better for dealing with Python,
    but you are much less  likely to lose information by using the default
    AS_NUMERIC_WRAPPER"""

    try :
        ofs = open(filename, 'w')
        WriteToXMLStream(v, ofs, top_level_key, options, arr_disp, prepend_char)
    except Exception, e :
        raise Exception, e

import cStringIO
def ConvertToXML (given_dict) :
    """Convert the given Python dictionary to XML and return the XML
    (a text string).  This uses the most common options that tend to
    make the conversions fully invertible."""
    stream_thing = cStringIO.StringIO()
    WriteToXMLStream(given_dict, stream_thing, 'top')
    return stream_thing.getvalue()



########NEW FILE########
__FILENAME__ = xmlloader
#!/bin/env python

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
   The reader will take and translate the XML into appropriate
   Val data structures.  This is appropriate for Key-Value documents,
   where the tags and attributes translate readily to key-value pairs
   of dictionaries.

   Examples:

     <book attr1="1" attr2="2">
        <chapter>text chap 1</chapter>
        <chapter>text chap 2</chapter>
     </book>
   
   becomes
    { 'book' : {
          '__attrs__' : { 'attr1':"1", 'attr2':"2" },
          'chapter' : [ 'text chap 1', 'text chap 2']
    }
"""

import sys
# Not until 2.7, keep as plain dict then
try :
    from collections import OrderedDict
except :
    OrderedDict = dict

# We want to use literal_eval, but it may not be available
try :
    from ast import literal_eval  # Safe: just can handle standard literals
    def safe_eval (s) :
        """This does an safe eval(i.e., ast.literal_eval): but literal_eval
        doesn't like whitespace,so this strips the whitespace before"""
        a = s.strip()
        return literal_eval(a)
    some_eval = safe_eval
except :
    # Set XML_NO_WARN in your global to avoid this warning
    # XML_NO_WARN = 1
    # import xmlloader
    if not ("XML_NO_WARN" in globals()) :
        print "*Warning: This version of Python doesn't support ast.literal_eval, so XML_LOAD_EVAL_CONTENT can be an unsafe option in malicious input/XML"
    some_eval = eval   # Warning: May be unsafe if malicious user code

# Parser of single characters
from parsereader import *

# The way to handle POD data
from arraydisposition import *


###################### OPTIONS for XML -> dictionaries

#  ATTRS (attributes on XML nodes) by default becomes
#  separate dictionaries in the table with a 
#  "__attrs__" key.  If you choose to unfold, the attributes
#  become keys at the same level, with an underscore.
#  (thus "unfolding" the attributes to an outer level).
#  
#  For example:
#    <book attr1="1" attr2="2>contents</book>
#  WITHOUT unfolding  (This is the DEFAULT)
#    { 'book' : "contents",
#      '__attrs__' : {'attr1'="1", "attr2"="2"}
#    }
#  WITH unfolding:  (Turning XML_LOAD_UNFOLD_ATTRS on)
#    { 'book' : "contents",
#      '_attr1':"1", 
#      '_attr2':"2", 
#    }
XML_LOAD_UNFOLD_ATTRS = 0x01


#  When unfolding, choose to either use the XML_PREPEND character '_'
#  or no prepend at all.  This only applies if XML_LOAD_UNFOLD_ATTRS is on.
#    <book attr1="1" attr2="2>contents</book>
#  becomes 
#   { 'book': "content", 
#     'attr1':'1',
#     'attr2':'2'
#   }
#  Of course, the problem is you can't differentiate TAGS and ATTRIBUTES 
#  with this option 
XML_LOAD_NO_PREPEND_CHAR = 0x02

#  If XML attributes are being folded up, then you may
#  want to prepend a special character to distinguish attributes
#  from nested tags: an underscore is the usual default.  If
#  you don't want a prepend char, use XML_LOAD_NO_PREPEND_CHAR option
XML_PREPEND_CHAR = '_'


#  Or, you may choose to simply drop all attributes:
#  <book a="1">text<book>
#    becomes
#  { 'book':'1' } #  Drop ALL attributes
XML_LOAD_DROP_ALL_ATTRS = 0x04

#  By default, we use Dictionaries (as we trying to model
#  key-value dictionaries).  Can also use ordered dictionaries
#  if you really truly care about the order of the keys from 
#  the XML
XML_LOAD_USE_OTABS = 0x08

#  Sometimes, for key-value translation, somethings don't make sense.
#  Normally:
#    <top a="1" b="2">content</top>
#  .. this will issue a warning that attributes a and b will be dropped
#  becuase this doesn't translate "well" into a key-value substructure.
#    { 'top':'content' }
# 
#  If you really want the attributes, you can try to keep the content by setting
#  the value below (and this will supress the warning)
#  
#   { 'top': { '__attrs__':{'a':1, 'b':2}, '__content__':'content' } }
#  
#  It's probably better to rethink your key-value structure, but this
#  will allow you to move forward and not lose the attributes
XML_LOAD_TRY_TO_KEEP_ATTRIBUTES_WHEN_NOT_TABLES = 0x10

#  Drop the top-level key: the XML spec requires a "containing"
#  top-level key.  For example: <top><l>1</l><l>2</l></top>
#  becomes { 'top':[1,2] }  (and you need the top-level key to get a 
#  list) when all you really want is the list:  [1,2].  This simply
#  drops the "envelope" that contains the real data.
XML_LOAD_DROP_TOP_LEVEL = 0x20

#  Converting from XML to Tables results in almost everything 
#  being strings:  this option allows us to "try" to guess
#  what the real type is by doing an Eval on each member:
#  Consider: <top> <a>1</a> <b>1.1</b> <c>'string' </top>
#  WITHOUT this option (the default) -> {'top': { 'a':'1','b':'1.1','c':'str'}}
#  WITH this option                  -> {'top': { 'a':1, 'b':1.1, 'c':'str' } }
#  If the content cannot be evaluated, then content simply says 'as-is'.
#  Consider combining this with the XML_DUMP_STRINGS_BEST_GUESS
#  if you go back and forth between Tables and XML a lot.
#  NOTE:  If you are using Python 2.6 and higher, this uses ast.literal_eval,
#         which is much SAFER than eval.  Pre-2.6 has no choice but to use
#         eval.
XML_LOAD_EVAL_CONTENT = 0x40

# Even though illegal XML, allow element names starting with Digits:
# when it does see a starting digit, it turns it into an _digit
# so that it is still legal XML
XML_TAGS_ACCEPTS_DIGITS = 0x80


#  When loading XML, do we require the strict XML header?
#  I.e., <?xml version="1.0"?>
#  By default, we do not.  If we set this option, we get an error
#  thrown if we see XML without a header
XML_STRICT_HDR = 0x10000




class XMLLoaderA(object) :
  """Abstract base class: All the code for parsing the letters one by
     one is here.  The code for actually getting the letters (from a
     string, stream, etc.) defers and uses the same framework as the
     OCValReader and the OpalReader (so that we can handle
     context for syntax errors)."""


  def __init__ (self, reader, options,
                array_disposition=ARRAYDISPOSITION_AS_LIST,
                prepend_char=XML_PREPEND_CHAR,
                suppress_warnings_when_not_key_value_xml=False) : # XMLDumper.CERR_ON_ERROR construct
      # // ///// Data Members
      # ReaderA* reader_;                 // Defer I/O so better syntax errors
      # int options_;                     // | ed options
      # HashTable<char> escapeSeqToSpecialChar_; // XML escape sequences
      # string prependChar_;              // When unfolding, prepend char
      # bool suppressWarning_;            // The warnings can be obnoxious
      
      """*The ReaderA* handles IO (from file, stream or string).
      *The options are or'ed in:  XML_LOAD_CONTENT | XML_STRICT_HDR: 
       see all the options above (this controls most XML loading features).  
      *The array_disposition tells what to do with Numeric arrays: AS_LIST
       turns them into lists, whereas both AS_NUMERIC and AS_PYTHON_ARRAY
       turn them into true POD arrays (there's no difference in this
       context: it makes more sense in Python when there are multiple POD
       array choices).
      *The prepend_char is what to look for if folding attributes (see above).
      *When problems loading, do we output an error to cerr or not."""
      self.reader_ = reader
      self.options_= options
      self.arrayDisp_ = array_disposition
      self.escapeSeqToSpecialChar_ = { }
      self.prependChar_ = prepend_char
      self.suppressWarning_ = suppress_warnings_when_not_key_value_xml

      if array_disposition==ARRAYDISPOSITION_AS_NUMERIC :
          # If we support Numeric, immediately construct and use those
          import Numeric
          self.array_type = type(Numeric.array([],'i'))
          self.array = Numeric.array
      else :
          # Otherwise, use the wrapper which looks like Numeric
          from simplearray import SimpleArray as array
          self.array_type = array
          self.array = array
                    
      # Low over constructor
      self.escapeSeqToSpecialChar_ = { 
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&apos;": "\'",
        "&quot;": "\"", 
      }

  def EOFComing () :
      "Look for EOF"
      return self.reader_.EOFComing()
  

  def expectXML (self) :
      """ Reads some XML and fills in result appropriately.  TODO: Still need
      to handle namespaces."""
      # Initial parsing into simpler IM 
      self._handleXMLDeclaration()
      name_attrs_content = [] 
      self._expectElement(name_attrs_content, False)
      # return name_attrs_content
    
      # Turn name_attrs_content into more "familiar' dicts
      result = self._tableType()
      self._fillInOutput(name_attrs_content, result) # fill in result
      post_result = self._postProcessListsOflist(result)
      final_result = self._dropTop(post_result)
      return final_result
  
  # ###### Helper methods

    # Choose whether we use OTabs or Tabs for dictionaries
  def _tableType (self, attrsp=None) :
      if self.options_ & XML_LOAD_USE_OTABS :
          return OrderedDict()
      else :
          return dict()

  # May or may not have an XML declaration: 
  #  <?xml version="1.0" encoding="UTF-8"?> or
  # <?xml version="1.0"?>
  # Really, all we support is version 1.0 and UTF-8.  And we don't
  # have to have the header.
  def _handleXMLDeclaration (self) :
      cc = self._peekNWSChar()
      if cc!='<':
          self._syntaxError("No top level for XML? Content without tags")
          
      self._getNWSChar()
      cc = self._peekChar()
      if cc==EOF :
          self._syntaxError("Premature EOF")

      # Look for XML Declaration
      if cc=='?' :
          self._expectString("Error during XML declaration", "?xml")
          xml_decl_attrs = { }
          self._getAttributeTable(xml_decl_attrs)
          if "version" in xml_decl_attrs and xml_decl_attrs["version"]!="1.0" :
              self._syntaxError("Can't handle any XML other than version 1.0")
      
          if ("encoding" in xml_decl_attrs and
              xml_decl_attrs["encoding"]!="UTF-8") :
              self._syntaxError("Can't handle any XML encodings other than UTF-8")
      
          self._expectString("Error during XML declaration", "?>")
          self._consumeWS()
    
      # Nope, just saw a < which starts some tag
      else :
          if (self.options_ & XML_STRICT_HDR) :
              self._syntaxError("No XML header (i.e., <?xml ... ?> on XML")
      
          self._pushback('<')

      # handle comments just after
      #while self._peekStream("<!--") :
      #    self._consumeComment()
      #    self._consumeWS()
      while 1 :
          if self._peekStream("<!") :
              if self._peekStream("<!--") :
                  self._consumeComment()
                  self._consumeWS()
              else :
                  self._consumeDTD()
                  self._consumeWS()
          else :
              break

  def _syntaxError (self, s) :
      # centralized syntax error handling
      self.reader_.syntaxError(s)
    
  def _XMLNotKeyValueWarning (self, name, output):
      if self.suppressWarning_ : 
         return
  
      mesg = "Warning: the given input XML has content interspersed\n" \
      "with keys and values:  the last content (and nesting will override\n"\
      "content) seen will become the value, but this kind of XML is not good\n"\
      "for just key-value pairs. Some info may be lost."
      sys.stderr.write(mesg + "\n")
      sys.stderr.write("name:"+name+'\n')
      sys.stderr.write("output:"+repr(output)+'\n')
      sys.stderr.write("... Continuing with best effort ...\n")

  def _XMLAttributesWithPrimitiveContentWarning (self, tag, value, output) :
      if self.suppressWarning_ :
         return
    
      mesg = "Warning: the given input XML has attributes interspersed with\n"\
      "primitive content:  To preserve the primitivenes of the data,\n"\
      "the attributes will been dropped from the data. Please revisit\n"\
      "your data format to avoid this situation so the data is more\n"\
      "key-value centric."
      sys.stderr.write(mesg+'\n')
      sys.stderr.write(" tag:"+tag+'\n')
      sys.stderr.write(" value:"+repr(value)+'\n') 
      sys.stderr.write(" output:"+repr(output)+'\n')
      sys.stderr.write(" ... Continuing with best effort ...\n")

  def _arrayPODWarning (self): 
      if self.suppressWarning_ :
          return  
      mesg = ""\
      "Trying to build an ArrayPOD list, but mismatched type__ attributes:\n" \
      "(or other attributes?) continuing with first definition";
      sys.stderr.write(mesg+'\n') 
      sys.stderr.write(" ... Continuing with best effort ...\n")
      
  # Drop the top level key, if it makes sense
  def _dropTop (self, result) :
      # Drop the top
      if (self.options_ & XML_LOAD_DROP_TOP_LEVEL):
           if ((type(result)==OrderedDict or type(result)==dict) and len(result)==1) :
               # We RETURN the dropped top
               for key,value in result.iteritems() :
                   return value
           else :
               if self.suppressWarning_ : 
                   return result
               mesg = ""\
               "Trying to drop the top-level key, but there is no single-top " \
               "level key that makes sense to drop, so not doing it"
               sys.stderr.write(mesg+"\n")
               sys.stderr.write(" ... Continuing with best effort ...\n")
      
      return result  # No change
    
  ######################################################################
  ## take the IM form and turn it into the final results
    
  # Post-processing: if the table has one entry labelled "listx__",
  # then this was a special way for XML->dict() to occur:
  # Basically:
  # { 'top:' [0,1,2] },
  #   becomes
  # <top>
  #  <list__>0</list__>
  #  <list__>1</list__>
  #  <list__>2</list__>
  # </top>
  #  We see this is as:
  #  { 'top': { 'list__': [0,1,2] } }
  #  .... We want to convert this BACK the right way, so we have to 
  #  find all <listx__ keys> and post-process.
  def _postProcessListsOflist (self, child) :
      # Base case
      if type(child)==self.array_type :
          if self.arrayDisp_ == ARRAYDISPOSITION_AS_LIST :
              return child.tolist()
          elif self.arrayDisp_ == ARRAYDISPOSITION_AS_NUMERIC :
              return child   # Could only do this if we supported Numeric
                             # in constructor
          elif self.arrayDisp_ == ARRAYDISPOSITION_AS_PYTHON_ARRAY :
              return child.asarray()
          elif self.arrayDisp_ == ARRAYDISPOSITION_AS_NUMERIC_WRAPPER :
              return child

          
      if type(child)!=OrderedDict and type(child)!=dict and type(child)!=list : 
          # Eval content instead of just strings
          if (self.options_ & XML_LOAD_EVAL_CONTENT) :
              try :
                  temp = some_eval(child)  # May be eval or ast.literal_eval
                  # Only eval "reversible" operations
                  if type(temp)==str :
                      # Then this was a string: the only
                      # way to get here is to have "" match (some whitespace
                      # at end:  "'123'" and "'123' " is legal
                      return temp

                  else :
                      stringized_temp = repr(temp)
                      
                  if (stringized_temp==child.strip()) : 
                      return temp
                  # So, wasn't reversible:  something prevents from being completely
                  # invertible. For many real-valued entries, this is simply
                  # a precision (one too many or too few digits) or a format
                  # thing (1e6 vs. 100000.0).  The ValReader can handle this
                  # by JUST expecting a real or complex, and we can check if there
                  # is "more stuff" on input after a full complex or real evaluation
                  t = type(temp)
                  if t in [float, long, complex] :
                      # temp is a real-valued datapoint: real values are
                      # problematic because of precision issues.
                      splits = child.split()
                      if len(splits)!=1: 
                          # Extra characters, so really not reversible
                          pass
                      else :
                          # So, got all characters as part, so, really just a precision
                          # issue, let's keep reals
                          if (stringized_temp == repr(t(splits[0]))) :
                              return temp
              
              except :
                  # Just ignore, and leave original as is
                  pass
          return child
    
      # Recursive: table
      elif (type(child)==dict or type(child)==OrderedDict) :
          # Recursively descend
          new_child = child.__class__()   # create new prototype with same type
          for key, value in child.iteritems() :
              new_value = self._postProcessListsOflist(value)
              new_child[key] = new_value
      

          # However, A lone list__ in a table is the target audience
          #  or      A lone dict__ in a table is the target audience
          if (len(new_child)==1) :
              found_lone_container = False
              
              for key, value in new_child.iteritems() : # get one and only item
                  if (key[-1]=='_' and key[-2]=='_') :
                      if (key.find("list")==0 and type(value) in [list, self.array_type] ) :
                          found_lone_container = True
	  
                      if (key.find("dict")==0 and type(value) in [dict, OrderedDict]) :
                          found_lone_container = True

                  # Make sure calls to child are cleaned up
                  if found_lone_container :
                      # child.swap(*vp) leaks because contains
                      new_child = value
                    
          # Processed entire dict, returning new_child
          return new_child

      # Recursive: list
      else : # child.tag=='n' subtype='Z'
          new_child = []
          for entry in child :
              new_entry = self._postProcessListsOflist(entry)
              new_child.append(new_entry)
          return new_child



  # Specialization for Val code ... slightly more efficient
  def _addValToList (self, content, output) :
    # TODO: this is probably tail-recursive, should iterate
    
    # Assertion: Have a list now
    # output is a list
    
    # Recursively fills in: by default it creates Tabs, so we need
    # to fix up into list.  TODO: Warn about non-empty attributes for lists
    temp=self._tableType()
    self._fillInOutput(content, temp);
    v = temp[content[0]]
    output.append(v)

    # All done
    return output


  # helper for fillingNestedList: After we know output is a 
  # list, we fill it in correctly.  This is really only called 
  # when we are doing the long form of Array<POD> types:
  # <l type__='f'>1</l><l type__='f'>/l>
  def _addToList (self, content, output) :
    # TODO: this is probably tail-recursive, should iterate
        
    # Assertion: Have a Numeric array now
    # Array<T>& l = output;   
    
    # Recursively fills in: by default it creates Tabs, so we need
    # to fix up into list.  TODO: Warn about non-empty attributes for lists
    temp=self._tableType()
    self._fillInOutput(content, temp)
    nested = temp[content[0]]
    t = nested  # will be filled in as some number
    if (type(nested) in [list, self.array_type]) :
      if (output.typecode() != nested.typecode()) :
	self._arrayPODWarning()
      t = nested[0]  # Had type__ tag too
    else :
      t = nested     # forgot type tag, but okay, still can process

    if self.arrayDisp_ != ARRAYDISPOSITION_AS_NUMERIC :
        output.append(t) ### NO APPEND on Numeric Arrays??????
    else :
        import Numeric
        # We have to friggin' do concatenate (Ugh, so O(n^2):  TODO: Fix!
    ##print >> sys.stderr, "************* t is ", t, ' nested is ', nested, '   output is', output
        output = Numeric.concatenate((output, Numeric.array([t], output.typecode()))) # YES, has to be a TUPLE as input to concatenate! SUCK!
    return output
   

  
  # The nested_name is already in the dictionary of output: by XML
  # rules, this needs to become a list.  Then either 
  # is already a list or we need to turn it into one
  def _fillingNestedList (self, content, output) :
  
    # Standard case: Not a list: either content or a dictionary: 
    # needs to be listized! (because we have repeated keys!).
    if ( (not (type(output) in [list, self.array_type])) or
         ((type(output)==self.array_type and (not ("type__" in content[1]))))) : # special:  the longer array pod sequence .. don't convert!

      # Assertion: "output" is either content or dictionary
      output = [output]
  
    # Assertion: "output" is a list ... either POD or Arr:
    # Add in the content
    if type(output)==list :
      return self._addValToList(content, output)
    else :
      return self._addToList(content, output)


  
  # Add in the given key-value pair to the output table.  Because the
  # output may not be a table, we handle this consistently by converting
  # (if the user chooses) that to a table.
  def _addAttrs (self, tag, value, output) :

      # Drop all attributes
      if (self.options_ & XML_LOAD_DROP_ALL_ATTRS) :
          return output

      # More complex: if there is some "non-insertable" content,
      # we either (a) ignore the attrs or (b) turn the content
      # into a table and THEN insert it
      new_output = output
      if (not (type(output)==OrderedDict or type(output)==dict)) :
          if (self.options_ & XML_LOAD_TRY_TO_KEEP_ATTRIBUTES_WHEN_NOT_TABLES) :
              # Otherwise, we have to turn content into a table
              # that contains the content
              new_output = self._tableType()
              new_output["__content__"] = output
          else :
              self._XMLAttributesWithPrimitiveContentWarning(tag,value,output)
              return new_output

      # Assertion: Standard table already there in output, 
      # so easy to just plop this in
      new_output[tag] = value
      return new_output

  
  # Taking the options as presented, figure out how to deal with the
  # attributes.  Do they go in as __attrs__?  Each tag as _ members?
  # Dropped entirely?
  def _addInAttrs (self, attrs, output) :
  
    if (len(attrs)==0) : return output
    if ("type__" in attrs) :
        if (len(attrs)!=1) :
            self._arrayPODWarning_() # TODO: Better warning?
        return output

    # Unfold attributes into table
    if (self.options_ & XML_LOAD_UNFOLD_ATTRS) : 
        # Iterate through all attributes, and add each one to the table
        for orig_key, value in attrs.iteritems() :
	
            # Choose what prepend char is
            key = str(orig_key);
            if (not(self.options_ & XML_LOAD_NO_PREPEND_CHAR)) :
                key = self.prependChar_ + key
	
            output = self._addAttrs(key, value, output)
      
     
    # The DEFAULT is as __attrs__: only do this if we haven't
    # set the unfold
    else :
        output = self._addAttrs("__attrs__", attrs, output)
    
    # All done
    return output


  # ... helper function for when processing arraytype__ 
  def _handlePODArraysHelper (self, output, name_attrs_content, typecode) :
    # print >> sys.stderr, '@@@@@@@@@@@@@@@ typecode is', typecode, '  @@@@ output is', output
    # Set the output, and check a few things
    output = self.array([], typecode) # Array<T>();
    if (len(name_attrs_content)<=2) : return output # No content
    content = name_attrs_content[2]
    string_content = ""
    if (type(content) == str) :
      string_content = str(content)
    elif (type(content)==list and len(content)>0 and type(content[0])==str) :
      string_content = str(content[0])
    elif (type(content)==list and len(content)==0) :
      string_content = ""
    else :
      print >> sys.stderr, content 
      raise Exception("Expecting solely string content for array of POD");
      
    # Assertion: We have a string of stuff, hopefully , separated numbers
    list_of_strings = string_content.split(',')
    if list_of_strings[0] == "" :
        intermediate_list = []
    else :
        intermediate_list = map(eval, list_of_strings)
    output = self.array(intermediate_list, typecode)
    return output


  # TOP-LEVEL: Map to map Val typecodes to Numeric typecodes
  typecodes_map = { 's':'1',
                    'S':'b',
                    'i':'s',
                    'I':'w',
                    'l':'i',
                    'L':'u',
                    'x':'l',
                    'X':'l',
                    'f':'f',
                    'd':'d',
                    'F':'F',
                    'D':'D'
                    }

  # If the attsr contain arraytype__, then the content is a POD
  # array:  Turn this into the proper type!
  def _handlePODArrays (self, name_attrs_content, output) :
    attrs = name_attrs_content[1]
    val_tag = attrs["arraytype__"]
    if val_tag in XMLLoader.typecodes_map :
      return self._handlePODArraysHelper(output, name_attrs_content,
                                         XMLLoader.typecodes_map[val_tag])
    else :
      raise Exception("arraytype__ attribute is not recognized")

  
  # Used when we first see an attribute <type__>
  def _createPODArray (self, value, tag, appending) :
    if tag in XMLLoader.typecodes_map :
      typecode = XMLLoader.typecodes_map[tag]
      if appending :
          a = self.array([eval(value)], typecode)
      else :
          a = self.array([], typecode)
      return a
    else :
      raise Exception("Don't support lists of anything but POD")
    
      
  # We have seen attrs("type__") == "list", so we have to be careful
  # parsing this thing
  def _handleAttributeTypeOfList (self, look) :
  
      # Returned with something that SHOULD be a list: most of the
      # time this means turning the nested thing into a list
      #//cout << "Got type list ... here's what I got:" << look << endl;
      if (type(look)==list) :
          # already a list, don't have to do anything
          pass
      elif ((type(look)==dict or type(look)==OrderedDict) and len(look)==0) :
          look = []
      else :
          look = [ look ]
    
      return look

  # helper; check to see if a "type__" tag is a legal one
  def _type__fillIn_ (self, type_tag, content, appending) :
      # Tag so we will create a  BRAND NEW minted Array POD!
      tag = None
      stag = str(type_tag)
      if len(stag)>0 : tag = stag[0]

      if stag=="list" :
          result = []
          if appending :
              result.append(content)
      elif len(stag)!=1 or not (stag[0] in "silxfdSILXFDb") :
          print sys.stderr, "Unknown tag '"+stag+"' .. ignoring "
          result = content
      else :
          result = self._createPODArray(content, tag, appending)
      return result


  # MAIN ENTRY:
  # Centralize all the output options for the given XML here.
  # Once we have parsed all the nessary parsed XML, we want to turn
  # it into a much simpler key-value thingee.  Output is assumed to
  # be the "dictionary" to fill in: it shoudl be set to an empty dict
  # by the caller, and it will be filled in by name_attrs_content
  def _fillInOutput (self, name_attrs_content, output) :
  
      # Parsed work here: need to turn into better vals
      name  = str(name_attrs_content[0])
      attrs = name_attrs_content[1]  # should be a table
      # print "name:", name, " attrs:", attrs 

      # Default of no content
      output[name] = self._tableType()
      look = output[name]

      # Arrays of POD content have some special keys to distinguish them:
      # array_type as an attribute
      if ("arraytype__" in attrs) :
          output[name] = self._handlePODArrays(name_attrs_content, look)
          look = output[name]
          if ("type__" in attrs and attrs["type__"]=="list") :
              output[name] = self._handleAttributeTypeOfList(look)
              look = output[name]
          return # TODO: revisit?  To handle listn__ ?
      
      # Special case: type__ tag, empty content
      if ("type__" in attrs) and \
         (len(name_attrs_content)==2 or \
          len(name_attrs_content)==3 and len(name_attrs_content[2])==0) :
          # <tag type__="something"></tag> or
          # <tag type__="something"/> 
          # NOTE: This needs to become a PODArray of empty
          dud = 666
          output[name] = self._type__fillIn_(attrs["type__"], dud, False)
          look = output[name]


      # Figure out which things will be lists, which will be attrs,
      # which will be nested tags.  
      if (len(name_attrs_content)>2) : # Content may be empty because of />
          contents   = name_attrs_content[2]
          # print >> sys.stderr, '****************CONTENTS', contents
          for content in contents :
	
              # Nested content: either needs to become a list or a dict
              if (type(content) == list) : 
                  nested_name = str(content[0])
	  
                  # If name is already there: then this is from an XML list with
                  # repeated entries, so the entry becomes a list
                  if (type(look)!=type("") and nested_name in look) :
                      look[nested_name] = self._fillingNestedList(content, look[nested_name])
	  
	  
                  # Name not there, so we need to insert a new table
                  else :
                      # Already filled in for something: careful, because
                      # we may have content littering the key-value portions
                      if (type(look) == type("")) : # May destroy content  
                          self._XMLNotKeyValueWarning(nested_name, look) 
	    
                      # Force name to be a table ... may destroy content
                      if (type(look)!=OrderedDict and type(look)!=dict) :
                          output[name] = self._tableType()
                          look = output[name]
                          
                      self._fillInOutput(content, output[name])
	  
  
              # Plain primitive content
              elif (type(content) == type("")) :
                  # print >> sys.stderr,  '****************** primitive content', content
                  if ("type__" in attrs) : # special key means Array<POD>, List
                      output[name] = \
                          self._type__fillIn_(attrs["type__"], content, True)
                      look = output[name]
                      
                  else :
                      # print >> sys.stderr, '**************primitive type: look is ', look, type(look)
                      t_look = type(look)
                      if ((t_look in [list,self.array_type] and len(look)==0) or
                          ((t_look==OrderedDict or t_look==dict) and len(look)>0)) :
                          self._XMLNotKeyValueWarning(name, content)
	    
	              output[name] = content  # TODO: Swap?
	              look = output[name]

              else :
                  self._syntaxError("Internal Error?  Malformed XML");
	

      # print >> sys.stderr,  '************ look is', look, ' ** output[name] is', output[name]
      # print >> sys.stderr,  '       ....  output is', output

      # POST_PROCESSING
      
      # Adding a tag of "type__"="list" means we want to make sure
      # some single element lists are tagged as lists, not tables
      if ("type__" in attrs and attrs["type__"]=="list") :
          output[name] = self._handleAttributeTypeOfList(look)
          look = output[name]

      # We want to do it AFTER we have processed all tags, as we want to
      # always *PREFER* tags so that if there might be an unfold of attributes,
      # we don't step on a real tag.
      output[name] = self._addInAttrs(attrs, look)
      look = output[name]

      # print >> sys.stderr,  '************ look is', look, ' ** output[name] is', output[name]
      # print >> sys.stderr,  '       ....  output is', output
      # done


  ##############################################################
  # Most of the routines from here PARSE the XML into a simpler
  # IM form which we then operate on and turn into more familiar
  # dicts

  # Expect a string of particular chars
  def _expectString (self, error_message_prefix, string_to_expect) :
      # 
      for some_char in string_to_expect :
          xc = self._getChar()
          char_found = xc
          char_look  = some_char
          if (xc==EOF) : 
            self._syntaxError(str(error_message_prefix)+ \
                           ":Premature EOF while looking for '"+char_look+"'")
      
          elif (char_look != char_found) :
            self._syntaxError(str(error_message_prefix)+ \
                              ":Was looking for '"+ \
                              char_look+"' but found '"+char_found+"'")
  

  # Expect some characters in a set: if not, throw error with message
  def _expect (self, message, one_of_set) :      
      # Single character token
      get      = self._getNWSChar()
      expected = -1
      for one in one_of_set :
          if (get==one) : 
              expected = one

      if (get!=expected) :
          get_string = ""
          if (get==EOF) :
              get_string="EOF"
          else :
              get_string=get
          self._syntaxError("Expected one of:'"+one_of_set+ \
                            "', but saw '"+get_string+"' " \
                            "on input during "+message)
      return get


  # Look for the ending character, grabbing everything
  # in between.  Really, these are for XML escapes
  def _expectUntil (self, end_char) :
      ret = []
      while (1) :
          ii = self._getChar()
          if (ii==EOF) :
              cc = end_char
              self._syntaxError("Unexpected EOF before "+str(cc)+" encountered")

          c = ii
          ret.append(c)

          if (c==end_char) :
              name = "".join(ret) # make string from all elements
              if (len(name)>1 and name[1] == '#') : # Numeric char. references
                  if (len(name)>2 and (str.lower(name[2])=='x')) : # hex number
                      if len(name)<=4 : # Not really legal ... &#x;
                          self._syntaxError("Expected some digits for hex escape sequence")
                      if len(name)>19 :
                          self._syntaxError("Too many digits in hex escape sequence")
                      # Every digit must be hex digit
                      hexdigits = "0123456789abcdef"
                      hexme = 0
                      for ii in xrange(3, len(name)-1) :
                          dig = str.lower(name[ii])
                          if not(dig in hexdigits) :
                              self._syntaxError("Expected hex digits only in escape sequence")
                          value = str.find(hexdigits, dig)
                          hexme = hexme* 16 + value
                      # if hexme==0 : syntaxError("Can't have \x0 on input") # ridiculous
                      # all done accumulating hex digits
                      # Since only do UTF-8 for now, truncate
                      return chr(hexme)
                  else : # decimal number
                      #decimal_number = int(name[2:])
                      #unicode = decimal_number
                      #return str(unicode)
                      self._syntaxError("Missing x for escape sequence")
	  
              special_char = '*' # just something to shut up compiler
              if name in self.escapeSeqToSpecialChar_ :
                  return self.escapeSeqToSpecialChar_[name] 
              else :
                  self._syntaxError("Unknown XML escape sequence:"+name)


      
  # Simply get the name, everything up to whitespace
  def _getElementName (self) :
      name = [] # Array appends better than string
    
      # Makes sure starts with 'a..ZA..Z_/'
      ii = self._getChar()
      if (ii==EOF) : self._syntaxError("Unexpected EOF inside element name")
      c = ii
      if (c.isdigit()) :
          if self.options_ & XML_TAGS_ACCEPTS_DIGITS == 0:
              self._syntaxError("element names can't start with '"+str(cc)+"'")
          else :
              name.append('_')
      elif (not(c.isalpha() or ii=='_' or ii=='/')) :
          cc = str(c)
          self._syntaxError("element names can't start with '"+str(cc)+"'")
    
      name.append(c)

      # .. now, make sure rest of name contains _, A..Za..Z, numbers
      while (1) :
          ii = self._peekChar()
          if (ii==EOF) : break
          c = ii
          if (c.isalnum() or c=='_') :
              self._getChar()
              name.append(c)
          else :
              break
      
      return "".join(name) # flatten [] to string


  # Get the attribute="value" names.  Expect "value" to be surrounded
  # by either " or ' quotes.
  def _getKeyValuePair (self) :
      
      # Simple name
      key = self._getElementName()
      self._consumeWS()
      #char the_equals  = 
      self._expect("looking at key:"+key, "=")
      self._consumeWS()
      which_quote = self._expect("looking at key:"+key, "\"'");

      # Follow quotes until see new one.  TODO:  look for escapes?
      value = None
      value_a = []
      while (1) :
          ii = self._getChar()
          if (ii==EOF) : 
              self._syntaxError("Unexpected EOF parsing key:"+key)
          elif (ii==which_quote) :
              value = "".join(value_a)
              break
          elif (ii=='&') : # start XML escape sequence 
              esc = self._expectUntil(';')
              for s in esc: # Most likely single char
                  value_a.append(s)
          else :
              value_a.append(ii)

      return (key, value)



  #  Assumption: We are just after the ELEMENT_NAME in "<ELEMENT_NAME
  #  att1=1, ... >" and we are looking to build a table of attributes.
  #  TODO: Should this be a list?
  def _getAttributeTable (self, attribute_table) :
      
      # The attribute list may be empty
      ii = self._peekNWSChar()
      c = ii
      if ('>'==c or '/'==c or '?'==c or EOF==ii) : return

      # Expecting something there
      while (1) :
          self._consumeWS()
          (key, value) = self._getKeyValuePair()
          attribute_table[key] = value

          self._consumeWS()
          ii = self._peekChar()
          c = ii;
          if ('>'==c or '/'==c or '?'==c or EOF==ii) : return
  

  def _isXMLSpecial (self, c) :
      return c=='<'


  # Expect a tag: starts with a < ends with a >.  If there is an
  # attribute list, will be the second element.  
  def _expectTag (self, a) :
      is_empty_tag = False

      # Expecting '<' to start
      self._expect("looking for start of tag", "<")
    
      # Assumption: Saw and got opening '<'.  Get the name
      element_name = self._getElementName()
      a.append(element_name)
    
      # Assumption: Got the < and NAME.  Now, Get the list of attributes
      # before the end of the '>'
      a.append({})  # attribute table ALWAYS a tab
      attribute_table = a[-1]
      self._getAttributeTable(attribute_table)
    
      # Assumption: End of list, consume the ">" or "/>"
      ii = self._peekNWSChar()
      if (EOF==ii) :
          self._syntaxError("Unexpected EOF inside tag '"+element_name+"'")
    
      if (ii=='/') :
          self._expect("empty content tag", "/")
          is_empty_tag = True
    
      self._expect("looking for end of tag"+element_name, ">")

      # End of list, make sure its well formed
      if (is_empty_tag and len(element_name)>0 and element_name[0]=='/') :
          self._syntaxError(
              "Can't have a tag start with </ and end with"
              "/> for element:"+element_name)

      return is_empty_tag


  # Expect a string of base content.  Collect it until you reach a
  # special character which ends the content ('<' for example).
  def _expectBaseContent (self, content) :
      ret = []
      while (1) :
          c = self._peekChar()
          if (c==EOF) : 
              return
          elif ('&'==c) :
              entity = self._expectUntil(';'); # Handles escapes for us
              for character in entity :
                  ret.append(character)
               
          elif (not self._isXMLSpecial(c)) :
              c = self._getChar()
              ret.append(c)
          else :
              # We have a '<':  is it a comment or start of a tag?
              if self._peekStream("<!--") :
                  self._consumeComment()
                  continue
	
              return_content = content + "".join(ret)
              return return_content


  #  [ 'book',                         // name 
  #    {'attr1': "1", 'attr2'="2"},    // table of attributes
  #    ["content"]                     // actual content
  #  ]                  
  #  
  #  If content is nested:
  #  <book attr1="1" attr2="2">
  #      <chapter>text chap 1</chapter>
  #      <chapter>text chap 2</chapter>
  #  </book>
  # 
  #  becomes
  # 
  #  [ 'book',  
  #    {'attr1'="1" 'attr2'="2"},
  #    [ ... ]
  #  ] 
  #  where [ ... ] is 
  #  [ ['chapter', {}, ["text chap 1"]], ['chapter', {}, ["text chap 2"]] ]
  # 
  #  We are starting with a beginning <tag> and we will return the table
  #  up to the end </tag>.  In other words, the next character we expect
  #  to see is a '<'.  This return the tag for the element, and fills
  #  in the element with some composite container (based on the options).
  def _expectElement (self, element, already_consumed_begin_tag=False) :
      
      # Get '<' NAME optional_attribute_list '>', put NAME, attr_list in
      if (not already_consumed_begin_tag) :
          tag_and_attrs = []
          is_empty_tag = self._expectTag(element)
          if (is_empty_tag): return
          
      tag_name = element[0] # Name always at front element

      # Assumption, consumed < NAME atr_list '>' of ELEMENT.
      # Everything that follow is content until we hit the </theendtag>
    
      # The content is a list of possibly nested ELEMENTs
      element.append([]) 
      content = element[-1]

      while (1) :
      
          whitespace = self._consumeWSWithReturn()  # always a string

          # We immediately see a <, is nested tag or end tag?
          ci = self._peekChar()
          if (ci == EOF) : self._syntaxError("Premature EOF?")
          c = ci
          if ('<' == c) : # Immediately saw <

              # May be comment!
              if (self._peekStream("<!--")) :
                  self._consumeComment()
                  continue
      
              
              # Get next tag 
              new_tag = []
              is_empty_tag = self._expectTag(new_tag)
              new_tag_name = new_tag[0]  # name always at front of list
	
              # Check for / to see if end tag
              if (len(new_tag_name)>0 and new_tag_name[0]=='/') :
                  if (new_tag_name[1:]==tag_name) : # saw end tag
                      return  # all good!
                  else :
                      self._syntaxError(
                          "Was looking for an end tag of '"+tag_name+
                          "' and saw an end tag of '"+new_tag_name+"'")
	  
	

              # This is a nested XML start tag
              else : 
                  content.append(new_tag)
                  nested_element = content[-1]
                  if (not is_empty_tag) : 
                      self._expectElement(nested_element, True) # already consumed tag!
      
          # No <, so it must be some content which we collect
          else :
              base_content = whitespace
              return_content = self._expectBaseContent(base_content)
              content.append(return_content)

  

  # If we see the given string as the next characters on the
  # input, return true.  Otherwise, false.  Note, we leave the
  # stream exactly as it is either way.
  def _peekStream (self, given) :
      # Holding area for stream as we peek it
      hold = [0 for x in xrange(len(given))]

      # Continue peeking and holding each char you see
      peeked_stream_ok = True
      length = len(given)
      ii = 0
      while ii<length :
          ci = self._getChar()
          hold[ii] = ci;
          if ci==EOF or ci!=given[ii] :
              peeked_stream_ok = False
              break
          ii += 1
      
      if peeked_stream_ok: ii-=1 # All the way through .. okay!

      # Restore the stream to its former glory
      jj = ii
      while jj>=0 :
          self._pushback(hold[jj]);
          jj -= 1
  
      return peeked_stream_ok
  


  # Assumes next four characters are <!--: a comment is coming.  
  # When done, stream reads immediately after comment ending -->
  def _consumeComment (self) :
      self._expectString("Expecting <!-- to start comment?", "<!--")
      while 1 :
          ci = self._getChar()
          if ci==EOF: self._syntaxError("Found EOF inside of comment")
          if ci!='-': continue
      
          # Saw a - ... looking for ->
          ci = self._getChar()
          if ci==EOF : self._syntaxError("Found EOF inside of comment")
          if ci!='-' : continue

          # Saw second - ... looking for >
          while 1 :
              ci = self._getChar()
              if ci==EOF : self._syntaxError("Found EOF inside of comment")
              if ci=='-' : continue  # Saw enough --, keep going
              if ci=='>' : return       # All done! Consumed a comment
              break  # Ah, no - or >, start all over looking for comment
          

  # Currently don't handle DTDs; just throw them away
  def _consumeDTD (self) :
      
      self._expectString("Expecting <! to start a DTD", "<!")
      while (1) :
          # You can have comments and NESTED DTDs in these things, ugh
          if (self._peekStream("<!")) :
              if (self._peekStream("<!--")) :
                  self._consumeComment()
              else :
                  self._consumeDTD()
                  
          # End of is just >
          ci = self._getChar()
          if (ci==EOF) : self._syntaxError("Found EOF inside of <!")
          if (ci=='>') : return


  # Plain whitespace, no comments
  def _consumeWSWithReturn (self) :
      retval = ""
      while (1) :
          cc = self._peekChar()
          if (cc==EOF) : break
          if (cc.isspace()) :
              retval = retval + cc
              self._getChar()
              continue
          else :
              break
      
      return retval





  # A derived class implements these methods to read characters from
  # some input source.
  def _getNWSChar(self)    : return self.reader_._getNWSChar() 
  def _peekNWSChar(self)   : return self.reader_._peekNWSChar()
  def _getChar(self)       : return self.reader_._getChar() 
  def _peekChar(self)      : return self.reader_._peekChar() 
  def _consumeWS(self)     : return self.reader_._consumeWS()
  def _pushback(self, pushback_ch) : return self.reader_._pushback(pushback_ch)

# XMLLoaderA



# Helper class to handle reading strings from an XML string
class XMLStringReader_ (StringReader) :

      def __init__(self, seq) :
          StringReader.__init__(self, seq) 

      # Return the index of the next Non-White Space character.
      # The default string reader handles # comments, which is NOT
      # what we want.  In fact, comments in XML are really only in
      # one syntactic place, so actually expect them explicitly when
      # reading them, otherwise, we don't expect them at all.
      # Return the index of the next Non-White Space character.
      def _indexOfNextNWSChar (self) : 
          length = len(self.buffer_)
          cur = self.current_
          if (cur==len) : return cur;
          while (cur<len and self.buffer_[cur].isspace()) :
              cur +=1 
          return cur


class XMLLoader (XMLLoaderA) :
      """ The XMLLoader reads XML from strings """

      def __init__(self, seq, options,
                   array_disposition=ARRAYDISPOSITION_AS_LIST, 
                   prepend_char=XML_PREPEND_CHAR,
                   suppress_warnings_when_not_key_value_xml=False) :
        """Create an XML loader from the given sequence"""
        XMLLoaderA.__init__(self, XMLStringReader_(seq), options,
                            array_disposition,
                            prepend_char, 
                            suppress_warnings_when_not_key_value_xml)



# Helper class for reading XML ASCII streams
class XMLStreamReader_(StreamReader) :
  
  def __init__(self, istream) :
    StreamReader.__init__(self, istream) 
    
  # This routines buffers data up until the next Non-White space
  # character, ands returns what the next ws char is _WITHOUT
  # GETTING IT_.  It returns (c, peek_ahead) where peek_ahead is
  # used to indicate how many characters into the stream you need
  # to be to get it (and c is the char)
  def _peekIntoNextNWSChar (self) :
    peek_ahead = 0   # This marks how many characters into the stream we need to consume
    while (1) :
      # Peek at a character either from the cache, or grab a new char
      # of the stream and cache it "peeking" at it.
      c = '*'
      if (peek_ahead >= len(self.cached_)) :
        c = self.is_.read(1)
        self.cached_.put(c)
      else :
        c = self.cached_.peek(peek_ahead)

      # Look at each character individually
      if (c==EOF) :
        # We never consume the EOF once we've seen it
        return (c, peek_ahead)
      elif (c.isspace()) : # whitespace but NOT comments!
        peek_ahead += 1;
        continue
      else :
        return (c, peek_ahead)
      
class StreamXMLLoader(XMLLoaderA) :
  """ Read an XML table from a stream """

  def __init__(self, istream, options,
               array_disposition = ARRAYDISPOSITION_AS_LIST,
               prepend_char=XML_PREPEND_CHAR,
	       suppress_warnings_when_not_key_value_xml=False) :
    """Open the given stream, and attempt to read Vals out of it"""
    XMLLoaderA.__init__(self, XMLStreamReader_(istream), options,
                        array_disposition,
                        prepend_char, suppress_warnings_when_not_key_value_xml)



def ReadFromXMLStream (istream,
                       options = XML_STRICT_HDR | XML_LOAD_DROP_TOP_LEVEL | XML_LOAD_EVAL_CONTENT, # best option for invertibility 
                       array_disposition = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                       prepend_char=XML_PREPEND_CHAR) :
    """Read XML from a stream and turn it into a dictionary.
    The options below represent the 'best choice' for invertibility:
     options=XML_STRICT_HDR | XML_LOAD_DROP_TOP_LEVEL | XML_LOAD_EVAL_CONTENT
    Although AS_NUMERIC_WRAPPER is less compatible, you are not going to lose
    any information."""
    sv = StreamXMLLoader(istream, options, array_disposition,prepend_char,False)
    return sv.expectXML()


def ReadFromXMLFile (filename,
                     options = XML_STRICT_HDR | XML_LOAD_DROP_TOP_LEVEL | XML_LOAD_EVAL_CONTENT, # best options for invertibility 
                     array_disposition = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                     prepend_char=XML_PREPEND_CHAR) :
    """ Read XML from a file and return it as a dictionary (as approp.)
    The options below represent the 'best choice' for invertibility:
     options=XML_STRICT_HDR | XML_LOAD_DROP_TOP_LEVEL | XML_LOAD_EVAL_CONTENT
    Although AS_NUMERIC_WRAPPER is less compatible, you are not going to lose
    any information."""
    ifstream = file(filename, 'r')
    return ReadFromXMLStream(ifstream, options, array_disposition, prepend_char)

import cStringIO
def ConvertFromXML (given_xml_string) :
    """Convert the given XML string (a text string) to a Python dictionary
    and return that.  This uses the most common options that tend to
    make the conversions fully invertible."""
    stream_thing = cStringIO.StringIO(given_xml_string)
    return ReadFromXMLStream(stream_thing)



if __name__ == "__main__" :  # from UNIX shell
  x = XMLLoader("<top>1</top>", XML_LOAD_DROP_TOP_LEVEL)  
  print x.expectXML()
  #xx = { 'top' : { 'lots':1, 'o':2 } }
  #print xx
  #print x._dropTop(xx)
  #xx = { 'top' : [1,2,3] }
  #print xx
  #print x._dropTop(xx)
  #xx = { 'top' : [1,2,3], 'other':1 }
  #print xx
  #print x._dropTop(xx)
  #xx = { 'top': { 'list0__': Numeric.array([0,1,2],'i') } }
  #yy = x._postProcessListsOflist(xx) 
  #print yy

  

########NEW FILE########
__FILENAME__ = xmltools
#!/bin/env python

#  Copyright (c) 2001-2009 Rincon Research Corporation, Richard T. Saunders
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. The name of the author may not be used to endorse or promote products
#     derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
#  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
#  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
  The tools here allow us to 
  (1) translate from XML to Val/Tar/Arr using xmlreader.h
  (2) translate from Val/Tab/Arr to XML using xmldumper.h
 
  The basic premise of these tools is that you are using
  XML as key-value pairs, and thus translating between
  dictionaries and XML is straight-forward.  In the
  following example, there is an obvious mapping between 
  dictionaries and XML:
 
    <book attr1="1" attr2="2">
       <chapter>text chap 1</chapter>
       <chapter>text chap 2</chapter>
    </book>
  
  ----------------------------------
  
   { 'book' = {
         '__attrs__' = { 'attr1':"1", 'attr2':"2" }
         'chapter' = [ 'text chap1', 'text chap2']
   }
 
  Adding attributes complicates the issues: many of the options
  below help control how the attributes in XML gets translated.
  The examples below showing UNFOLDING (or not) of attributes
  
  <html>
    <book attr1="1" attr2="2">
      <chapter> chapter 1 </chapter>
      <chapter> chapter 2 </chapter>
    </book>
  </html>
  ----------------------------------------
  { 'html': {           
       'book': {
          '_attr1':"1",     <!--- Attributes UNFOLDED -->
          '_attr2':"2",
          'chapter': [ 'chapter1', 'chapter2' ]
       }
  }
   or
  { 'html' : {
       'book': {
          '__attrs__': { 'attr1'="1", 'attr2'="2" },  <!-- DEFAULT way -->
          'chapter' : [ 'chapter1', 'chapter2' ]
       }
    }
  }


  ** Example where XML really is better:
  ** This is more of a "document", where HTML is better (text and
  key-values are interspersed)
  <html>
    <book attr1="1" attr2="2">
      This is the intro
      <chapter> chapter 1 </chapter>
      This is the extro
    </book>
  </html>
  
  {
    'book': { 
       'chapter': { ???
       }
    }
  }
  
  ???? ['book'] -> "This is the intro" or "This is the outro?"
  NEITHER.  It gets dumped, as book is a dictionary.
  This is an example where converting from XML to Dictionaries
  may be a bad idea and just may not be a good correspondance.


  Options are formed by 'or'ing together. 
"""

from xmlloader import *
from xmldumper import *

########NEW FILE########
__FILENAME__ = PluginManager
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import sys
import os
import json
from Singleton import Singleton
from ImageFactoryException import ImageFactoryException

PLUGIN_TYPES = ('OS', 'CLOUD')
INFO_FILE_EXTENSION = '.info'
PKG_STR = 'imagefactory_plugins'


class PluginManager(Singleton):
    """ Registers and manages ImageFactory plugins. """

    @property
    def plugins(self):
        """
        The property plugins
        """
        return self._plugins

    def _singleton_init(self, plugin_path):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        sys.path.append(plugin_path)

        if os.path.exists(plugin_path):
            self.path = plugin_path
        else:
            msg = 'Plugin path (%s) does not exist! No plugins loaded.' % plugin_path
            self.log.exception(msg)
            raise Exception(msg)

        self._plugins = dict()
        self._targets = dict()
        self._types = dict().fromkeys(PLUGIN_TYPES, list())

    def load(self):
        """
        Enumerates through installed plugins and registers each according to
        the features provided. Only one plugin may be registered per feature.
        When more than one plugin is found, the first will be registered and
        all others listed as inactive.
        """
        info_files = list()
        directory_listing = os.listdir(self.path)
        for _file in directory_listing:
            if _file.endswith(INFO_FILE_EXTENSION):
                info_files.append(_file)

        for filename in info_files:
            plugin_name = filename[:-len(INFO_FILE_EXTENSION)]
            md = self.metadata_for_plugin(plugin_name)
            try:
                if md['type'].upper() in PLUGIN_TYPES:
                    for target in md['targets']:
                        target = target if isinstance(target, str) else tuple(target)
                        if not target in self._targets:
                            self._targets[target] = plugin_name
                        else:
                            msg = 'Did not register %s for %s. Plugin %s already registered.' % (plugin_name,
                                                                                                 target,
                                                                                                 self._targets[target])
                            self._register_plugin_with_error(plugin_name, msg)
                            self.log.warn(msg)
                    self._plugins[plugin_name] = md
                    self._types[md['type'].upper()].append(plugin_name)
                    self.log.info('Plugin (%s) loaded...' % plugin_name)
            except KeyError as e:
                msg = 'Invalid metadata for plugin (%s). Missing entry for %s.' % (plugin_name, e)
                self._register_plugin_with_error(plugin_name, msg)
                self.log.exception(msg)
            except Exception as e:
                msg = 'Loading plugin (%s) failed with exception: %s' % (plugin_name, e)
                self._register_plugin_with_error(plugin_name, msg)
                self.log.exception(msg)

    def _register_plugin_with_error(self, plugin_name, error_msg):
        self._plugins[plugin_name] = dict(ERROR=error_msg)

    def metadata_for_plugin(self, plugin):
        """
        Returns the metadata dictionary for the plugin.

        @param plugin name of the plugin or the plugin's info file

        @return dictionary containing the plugin's metadata
        """
        if plugin in self._plugins:
            return self._plugins[plugin]
        else:
            fp = None
            metadata = None
            info_file = plugin + INFO_FILE_EXTENSION
            try:
                fp = open(os.path.join(self.path, info_file), 'r')
                metadata = json.load(fp)
            except Exception as e:
                self.log.exception('Exception caught while loading plugin metadata: %s' % e)
                raise e
            finally:
                if fp:
                    fp.close()
                return metadata

    def plugin_for_target(self, target):
        """
        Looks up the plugin for a given target and returns an instance of the 
        delegate class or None if no plugin is registered for the given target.
        Matches are done from left to right, ie. ('Fedora', '16', 'x86_64') will
        match a plugin with a target of ('Fedora', None, None) but not
        ('Fedora', None, 'x86_64')
        
        @param target A list or string matching the target field of the
        plugin's .info file.
    
        @return An instance of the delegate class of the plugin or None.
        """
        try:
            if isinstance(target, str):
                self.log.debug("Attempting to match string target (%s)" % target)
                plugin_name = self._targets.get(tuple([target]))
                if not plugin_name:
                    raise ImageFactoryException("No plugin .info file loaded for target: %s" % (target))
                plugin = __import__('%s.%s' % (PKG_STR, plugin_name), fromlist=['delegate_class'])
                return plugin.delegate_class()
            elif isinstance(target, tuple):
                _target = list(target)
                self.log.debug("Attempting to match list target (%s)" % (str(_target)))
                for index in range(1, len(target) + 1):
                    plugin_name = self._targets.get(tuple(_target))
                    if not plugin_name:
                        _target[-index] = None
                    else:
                        plugin = __import__('%s.%s' % (PKG_STR, plugin_name), fromlist=['delegate_class'])
                        return plugin.delegate_class()
        except ImportError as e:
            self.log.exception(e)
            raise ImageFactoryException("Unable to import plugin for target: %s" % str(target))


########NEW FILE########
__FILENAME__ = props
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#
# Return a property backed by the given attribute
#
def prop(attr, doc = None, ro = None):
    def fget(self):
        return getattr(self, attr)
    def fset(self, value):
        setattr(self, attr, value)
    def fdel(self):
        delattr(self, attr)
    return property(fget, fset if not ro else None, fdel if not ro else None, doc)

def ro_prop(attr, doc = None):
    return prop(attr, doc, True)

#
# A variant of the above where the property is backed by an
# attribute of an attribute
#
def subprop(attr, subattr, doc = None, ro = False):
    def fget(self):
        return getattr(getattr(self, attr), subattr)
    def fset(self, value):
        setattr(getattr(self, attr), subattr, value)
    def fdel(self):
        delattr(getattr(self, attr), subattr)
    return property(fget, fset if not ro else None, fdel if not ro else None, doc)

def ro_subprop(attr, subattr, doc = None):
    return subprop(attr, subattr, doc, True)

########NEW FILE########
__FILENAME__ = Provider
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import logging
import os.path
from xml.etree.ElementTree import fromstring


########## THIS IS TEMPORARY 
# These functions were moved from being methods on BuildDispatcher
# to avoid a circular import in Builder.py. There may be a better
# place for these, but I could see us having Target and Provider
# clases in thhe future, so I created this module as a placeholder.
#
# TODO This is *UGLY* and should get cleaned up.
###################################################################


# FIXME: this is a hack; conductor is the only one who really
#        knows this mapping, so perhaps it should provide it?
#        e.g. pass a provider => target dict into push_image
#        rather than just a list of providers. Perhaps just use
#        this heuristic for the command line?
#
# provider semantics, per target:
#  - ec2: region, one of ec2-us-east-1, ec2-us-west-1, ec2-ap-southeast-1, ec2-ap-northeast-1, ec2-eu-west-1
#  - condorcloud: ignored
#  - mock: any provider with 'mock' prefix
#  - rackspace: provider is rackspace
# UPDATE - Sept 13, 2011 for dynamic providers
#  - vpshere: encoded in provider string or a key in /etc/vmware.json
#  - rhevm: encoded in provider string or a key in /etc/rhevm.json
#
def map_provider_to_target(provider):
    # TODO: Add to the cloud plugin delegate interface a method to allow the plugin to "claim"
    #       a provider name.  Loop through the clouds, find ones that claim it.  Warn if more
    #       than one.  Error if none.  Success if only one.
    log = logging.getLogger(__name__)
    # Check for dynamic providers first
    provider_data = get_dynamic_provider_data(provider)
    if provider_data:
        try:
            return provider_data['target']
        except KeyError as e:
            log.debug('Provider data does not specify target!\n%s' % provider_data)
            log.exception(e)
            raise Exception('Provider data does not specify target!\n%s' % provider_data)
    elif provider.startswith('ec2-'):
        return 'ec2'
    elif provider == 'rackspace':
        return 'rackspace'
    elif provider.startswith('mock'):
        return 'mock'
    elif provider.startswith('MockCloud'):
        return 'MockCloud'
    else:
        log.warn('No matching provider found for %s, using "condorcloud" by default.' % (provider))
        return 'condorcloud' # condorcloud ignores provider

def get_dynamic_provider_data(provider):
    log = logging.getLogger(__name__)
    # Get provider details for RHEV-M or VSphere
    # First try to interpret this as an ad-hoc/dynamic provider def
    # If this fails, try to find it in one or the other of the config files
    # If this all fails return None
    # We use this in the builders as well so I have made it "public"

    try:
        xml_et = fromstring(provider)
        return xml_et.attrib
    except Exception as e:
        log.debug('Testing provider for XML: %s' % e)
        pass

    try:
        jload = json.loads(provider)
        return jload
    except ValueError as e:
        log.debug('Testing provider for JSON: %s' % e)
        pass

    rhevm_data = _return_dynamic_provider_data(provider, "rhevm")
    if rhevm_data:
        rhevm_data['target'] = "rhevm"
        rhevm_data['name'] = provider
        return rhevm_data

    vsphere_data = _return_dynamic_provider_data(provider, "vsphere")
    if vsphere_data:
        vsphere_data['target'] = "vsphere"
        vsphere_data['name'] = provider
        return vsphere_data

    # It is not there
    return None

def _return_dynamic_provider_data(provider, filebase):
    provider_json = '/etc/imagefactory/%s.json' % (filebase)
    if not os.path.exists(provider_json):
        return False

    provider_sites = {}
    f = open(provider_json, 'r')
    try:
        provider_sites = json.loads(f.read())
    finally:
        f.close()

    if provider in provider_sites:
        return provider_sites[provider]
    else:
        return None

########NEW FILE########
__FILENAME__ = ProviderImage
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from PersistentImage import PersistentImage
from props import prop


METADATA = ('target_image_id', 'provider', 'identifier_on_provider', 'provider_account_identifier', 'parameters')

class ProviderImage(PersistentImage):
    """ TODO: Docstring for ProviderImage  """

    target_image_id = prop("_target_image_id")
    provider = prop("_provider")
    identifier_on_provider = prop("_identifier_on_provider")
    provider_account_identifier = prop("_provider_account_identifier")
    credentials = prop("_credentials")
    parameters = prop("_parameters")

    def __init__(self, image_id=None):
        """ TODO: Fill me in
        
        @param template TODO
        @param target_img_id TODO
        """
        super(ProviderImage, self).__init__(image_id)
        self.target_image_id = None
        self.provider = None
        self.identifier_on_provider = None
        self.provider_account_identifier = None
        self.credentials = None
        self.parameters = None

    def metadata(self):
        self.log.debug("Executing metadata in class (%s) my metadata is (%s)" % (self.__class__, METADATA))
        return frozenset(METADATA + super(self.__class__, self).metadata())

########NEW FILE########
__FILENAME__ = ReservationManager
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import os
import os.path
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from threading import BoundedSemaphore

class ReservationManager(object):
    """ TODO: Docstring for ReservationManager """
    instance = None

    DEFAULT_MINIMUM = 21474836480

    MIN_PORT = 1025
    MAX_PORT = 65535

    ### Properties
    def default_minimum():
        """The property default_minimum"""
        def fget(self):
            return self._default_minimum
        def fset(self, value):
            self._default_minimum = value
        return locals()
    default_minimum = property(**default_minimum())

    @property
    def available_space(self):
        """Dictionary of mount points and bytes available."""
        space = dict()
        for path in self._mounts.keys():
            space.update({path:self.available_space_for_path(path)})
        return space

    @property
    def reservations(self):
        """Dictionary of filepaths and number of bytes reserved for each."""
        reservations = dict()
        for key in self._mounts.keys():
            reservations.update(self._mounts[key]['reservations'])
        return reservations

    @property
    def queues(self):
        """The property queues"""
        return self._queues.keys()
    ### END Properties

    def __new__(cls, *p, **k):
        if cls.instance is None:
            i = super(ReservationManager, cls).__new__(cls, *p, **k)
            # initialize here, not in __init__()
            i.log = logging.getLogger('%s.%s' % (__name__, i.__class__.__name__))
            i.default_minimum = cls.DEFAULT_MINIMUM
            i._mounts = dict()
            i.appconfig = ApplicationConfiguration().configuration
            i._queues = dict(local=BoundedSemaphore(i.appconfig.get('max_concurrent_local_sessions', 1)),
                             ec2=BoundedSemaphore(i.appconfig.get('max_concurrent_ec2_sessions', 1)))
            i._named_locks = { } 
            i._named_locks_lock = BoundedSemaphore()
            # Initialize based on PID to prevent conflicts from multiple CLI runs on the same machine
            # TODO: This is TinMan/Oz specific - move it to the plugin
            i._listen_port = cls.MIN_PORT + (os.getpid() % (cls.MAX_PORT - cls.MIN_PORT))
            i._listen_port_lock = BoundedSemaphore()
            cls.instance = i
        return cls.instance

    def __init__(self):
        """
        @param default_minimum Default for the minimum amount needed for a path.
        """
        pass

    def get_next_listen_port(self):
        self._listen_port_lock.acquire()
        try:
            self._listen_port += 1
            if self._listen_port > self.MAX_PORT:
                self._listen_port = self.MIN_PORT
            return self._listen_port
        finally:
            self._listen_port_lock.release()

    def reserve_space_for_file(self, size, filepath):
        """
        TODO: Docstring for reserve_space_for_file

        @param size TODO
        @param filepath TODO
        """
        mount_path = self._mount_for_path(filepath)
        mount = self._mounts.setdefault(mount_path,
                {'min_free': self.default_minimum, 'reservations': dict()})
        available = self.available_space_for_path(mount_path) - mount['min_free']
        if(size < available):
            mount['reservations'].update({filepath:size})
            return True
        else:
            return False

    def cancel_reservation_for_file(self, filepath, quiet=True):
        """
        TODO: Docstring for cancel_reservation_for_file

        @param filepath TODO
        """
        mount_path = self._mount_for_path(filepath)

        try:
            mount = self._mounts.get(mount_path)
            try:
                del mount['reservations'][filepath]
            except (TypeError, KeyError), e:
                if(quiet):
                    self.log.warn('No reservation for %s to cancel!' % filepath)
                else:
                    raise e
        except KeyError, e:
            if(quiet):
                self.log.warn('No reservations exist on %s!' % mount_path)
            else:
                raise e

    def _mount_for_path(self, path):
        path = os.path.abspath(path)
        while path != os.path.sep:
            if os.path.ismount(path):
                return path
            path = os.path.abspath(os.path.join(path, os.pardir))
        return path

    def add_path(self, path, min_free=None):
        """
        TODO: Docstring for add_path

        @param path TODO
        @param min_free TODO
        """
        if(isinstance(path, str)):
            mount_path = self._mount_for_path(path)
            mount = self._mounts.setdefault(mount_path,
                    {'min_free':min_free, 'reservations': dict()})
            if(not mount):
                raise RuntimeError("Unable to add path (%s)." % path)
        else:
            raise TypeError("Argument 'path' must be string.")

    def remove_path(self, path, quiet=True):
        """
        Removes a path from the list of watched paths.

        @param path Filesystem path string to remove.
        """
        mount_path = self._mount_for_path(path)
        try:
            del self._mounts[mount_path]
        except KeyError, e:
            if(quiet):
                self.log.warn('%s not in reservation list.' % mount_path)
            else:
                raise e

    def available_space_for_path(self, path):
        """
        TODO: Docstring for available_space_for_path

        @param path TODO

        @return TODO
        """
        mount_path = self._mount_for_path(path)
        if(mount_path in self._mounts):
            reservations = self._mounts[mount_path]['reservations'].values()
            reservation_total = sum(reservations)
            consumed_total = 0
            for filepath in self._mounts[mount_path]['reservations'].keys():
                try:
                    consumed_total += os.path.getsize(filepath)
                except os.error:
                    self.log.warn('%s does not exist.' % filepath)
            remaining = reservation_total - consumed_total
            stat = os.statvfs(path)
            available = stat.f_bavail * stat.f_frsize
            return available - (remaining if remaining > 0 else 0)
        else:
            return None

    def enter_queue(self, name=None):
        """
        Tries to acquire a semaphore for the named queue. Blocks until a slot opens up.
        If no name is given or a queue for the given name is not found, the default 'local' 
        queue will be used.

        @param name - The name of the queue to enter. See the queues property of ReservationManager.
        """
        if(name):
            self.log.debug("ENTERING queue: (%s)" % (name))
            self._queues[name].acquire()
            self.log.debug("SUCCESS ENTERING queue: (%s)" % (name))

    def exit_queue(self, name=None):
        """
        Releases semaphore for the named queue. This opens up a slot for waiting members of the queue.
        If no name is given or a queue for the given name is not found, the default 'local' 
        queue will be used.

        @param name - The name of the queue to enter. See the queues property of ReservationManager.
        """
        if(name):
            self.log.debug("EXITING queue: (%s)" % (name))
            self._queues[name].release()
            self.log.debug("SUCCESS EXITING queue: (%s)" % (name))

    def get_named_lock(self, name):
        """
        Get the named lock.
        If the semaphore representing the lock does not exit, create it in a thread safe way.
        Note that this is always a blocking call that will wait until the lock is available.

        @param name - The name of the lock
        """
        # Global critical section
        self._named_locks_lock.acquire()
        if not name in self._named_locks:
            self._named_locks[name] = BoundedSemaphore()
        self._named_locks_lock.release()
        # End global critical section

        self.log.debug("Grabbing named lock (%s)" % name)
        self._named_locks[name].acquire()
        self.log.debug("Got named lock (%s)" % name)

    def release_named_lock(self, name):
        """
        Release a named lock acquired with get_named_lock()

        @param name - The name of the lock
        """
        self.log.debug("Releasing named lock (%s)" % name)
        self._named_locks[name].release()

########NEW FILE########
__FILENAME__ = bottle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bottle is a fast and simple micro-framework for small web applications. It
offers request dispatching (Routes) with url parameter support, templates,
a built-in HTTP Server and adapters for many third party WSGI/HTTP-server and
template engines - all in a single file and with no dependencies other than the
Python Standard Library.

Homepage and documentation: http://bottlepy.org/

Copyright (c) 2011, Marcel Hellkamp.
License: MIT (see LICENSE.txt for details)
"""

from __future__ import with_statement

__author__ = 'Marcel Hellkamp'
__version__ = '0.10.9'
__license__ = 'MIT'

# The gevent server adapter needs to patch some modules before they are imported
# This is why we parse the commandline parameters here but handle them later
if __name__ == '__main__':
    from optparse import OptionParser
    _cmd_parser = OptionParser(usage="usage: %prog [options] package.module:app")
    _opt = _cmd_parser.add_option
    _opt("--version", action="store_true", help="show version number.")
    _opt("-b", "--bind", metavar="ADDRESS", help="bind socket to ADDRESS.")
    _opt("-s", "--server", default='wsgiref', help="use SERVER as backend.")
    _opt("-p", "--plugin", action="append", help="install additional plugin/s.")
    _opt("--debug", action="store_true", help="start server in debug mode.")
    _opt("--reload", action="store_true", help="auto-reload on file changes.")
    _cmd_options, _cmd_args = _cmd_parser.parse_args()
    if _cmd_options.server and _cmd_options.server.startswith('gevent'):
        import gevent.monkey; gevent.monkey.patch_all()

import sys
import base64
import cgi
import email.utils
import functools
import hmac
import httplib
import imp
import itertools
import mimetypes
import os
import re
import subprocess
import tempfile
import thread
import threading
import time
import warnings

from Cookie import SimpleCookie
from datetime import date as datedate, datetime, timedelta
from tempfile import TemporaryFile
from traceback import format_exc, print_exc
from urlparse import urljoin, SplitResult as UrlSplitResult

# Workaround for a bug in some versions of lib2to3 (fixed on CPython 2.7 and 3.2)
import urllib
urlencode = urllib.urlencode
urlquote = urllib.quote
urlunquote = urllib.unquote

try: from collections import MutableMapping as DictMixin
except ImportError: # pragma: no cover
    from UserDict import DictMixin

try: from urlparse import parse_qsl
except ImportError: # pragma: no cover
    from cgi import parse_qsl

try: import cPickle as pickle
except ImportError: # pragma: no cover
    import pickle

try: from json import dumps as json_dumps, loads as json_lds
except ImportError: # pragma: no cover
    try: from simplejson import dumps as json_dumps, loads as json_lds
    except ImportError: # pragma: no cover
        try: from django.utils.simplejson import dumps as json_dumps, loads as json_lds
        except ImportError: # pragma: no cover
            def json_dumps(data):
                raise ImportError("JSON support requires Python 2.6 or simplejson.")
            json_lds = json_dumps

py3k = sys.version_info >= (3,0,0)
NCTextIOWrapper = None

if sys.version_info < (2,6,0):
    msg = "Python 2.5 support may be dropped in future versions of Bottle."
    warnings.warn(msg, DeprecationWarning)

if py3k: # pragma: no cover
    json_loads = lambda s: json_lds(touni(s))
    # See Request.POST
    from io import BytesIO
    def touni(x, enc='utf8', err='strict'):
        """ Convert anything to unicode """
        return str(x, enc, err) if isinstance(x, bytes) else str(x)
    if sys.version_info < (3,2,0):
        from io import TextIOWrapper
        class NCTextIOWrapper(TextIOWrapper):
            ''' Garbage collecting an io.TextIOWrapper(buffer) instance closes
                the wrapped buffer. This subclass keeps it open. '''
            def close(self): pass
else:
    json_loads = json_lds
    from StringIO import StringIO as BytesIO
    bytes = str
    def touni(x, enc='utf8', err='strict'):
        """ Convert anything to unicode """
        return x if isinstance(x, unicode) else unicode(str(x), enc, err)

def tob(data, enc='utf8'):
    """ Convert anything to bytes """
    return data.encode(enc) if isinstance(data, unicode) else bytes(data)

tonat = touni if py3k else tob
tonat.__doc__ = """ Convert anything to native strings """

def try_update_wrapper(wrapper, wrapped, *a, **ka):
    try: # Bug: functools breaks if wrapper is an instane method
        functools.update_wrapper(wrapper, wrapped, *a, **ka)
    except AttributeError: pass

# Backward compatibility
def depr(message):
    warnings.warn(message, DeprecationWarning, stacklevel=3)


# Small helpers
def makelist(data):
    if isinstance(data, (tuple, list, set, dict)): return list(data)
    elif data: return [data]
    else: return []


class DictProperty(object):
    ''' Property that maps to a key in a local dict-like attribute. '''
    def __init__(self, attr, key=None, read_only=False):
        self.attr, self.key, self.read_only = attr, key, read_only

    def __call__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter, self.key = func, self.key or func.__name__
        return self

    def __get__(self, obj, cls):
        if obj is None: return self
        key, storage = self.key, getattr(obj, self.attr)
        if key not in storage: storage[key] = self.getter(obj)
        return storage[key]

    def __set__(self, obj, value):
        if self.read_only: raise AttributeError("Read-Only property.")
        getattr(obj, self.attr)[self.key] = value

    def __delete__(self, obj):
        if self.read_only: raise AttributeError("Read-Only property.")
        del getattr(obj, self.attr)[self.key]


class CachedProperty(object):
    ''' A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. '''

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value

cached_property = CachedProperty


class lazy_attribute(object): # Does not need configuration -> lower-case name
    ''' A property that caches itself to the class object. '''
    def __init__(self, func):
        functools.update_wrapper(self, func, updated=[])
        self.getter = func

    def __get__(self, obj, cls):
        value = self.getter(cls)
        setattr(cls, self.__name__, value)
        return value






###############################################################################
# Exceptions and Events ########################################################
###############################################################################


class BottleException(Exception):
    """ A base class for exceptions used by bottle. """
    pass


#TODO: These should subclass BaseRequest

class HTTPResponse(BottleException):
    """ Used to break execution and immediately finish the response """
    def __init__(self, output='', status=200, header=None):
        super(BottleException, self).__init__("HTTP Response %d" % status)
        self.status = int(status)
        self.output = output
        self.headers = HeaderDict(header) if header else None

    def apply(self, response):
        if self.headers:
            for key, value in self.headers.iterallitems():
                response.headers[key] = value
        response.status = self.status


class HTTPError(HTTPResponse):
    """ Used to generate an error page """
    def __init__(self, code=500, output='Unknown Error', exception=None,
                 traceback=None, header=None):
        super(HTTPError, self).__init__(output, code, header)
        self.exception = exception
        self.traceback = traceback

    def __repr__(self):
        return tonat(template(ERROR_PAGE_TEMPLATE, e=self))






###############################################################################
# Routing ######################################################################
###############################################################################


class RouteError(BottleException):
    """ This is a base class for all routing related exceptions """


class RouteReset(BottleException):
    """ If raised by a plugin or request handler, the route is reset and all
        plugins are re-applied. """

class RouterUnknownModeError(RouteError): pass

class RouteSyntaxError(RouteError):
    """ The route parser found something not supported by this router """

class RouteBuildError(RouteError):
    """ The route could not been built """

class Router(object):
    ''' A Router is an ordered collection of route->target pairs. It is used to
        efficiently match WSGI requests against a number of routes and return
        the first target that satisfies the request. The target may be anything,
        usually a string, ID or callable object. A route consists of a path-rule
        and a HTTP method.

        The path-rule is either a static path (e.g. `/contact`) or a dynamic
        path that contains wildcards (e.g. `/wiki/<page>`). The wildcard syntax
        and details on the matching order are described in docs:`routing`.
    '''

    default_pattern = '[^/]+'
    default_filter   = 're'
    #: Sorry for the mess. It works. Trust me.
    rule_syntax = re.compile('(\\\\*)'\
        '(?:(?::([a-zA-Z_][a-zA-Z_0-9]*)?()(?:#(.*?)#)?)'\
          '|(?:<([a-zA-Z_][a-zA-Z_0-9]*)?(?::([a-zA-Z_]*)'\
            '(?::((?:\\\\.|[^\\\\>]+)+)?)?)?>))')

    def __init__(self, strict=False):
        self.rules    = {} # A {rule: Rule} mapping
        self.builder  = {} # A rule/name->build_info mapping
        self.static   = {} # Cache for static routes: {path: {method: target}}
        self.dynamic  = [] # Cache for dynamic routes. See _compile()
        #: If true, static routes are no longer checked first.
        self.strict_order = strict
        self.filters = {'re': self.re_filter, 'int': self.int_filter,
                        'float': self.float_filter, 'path': self.path_filter}

    def re_filter(self, conf):
        return conf or self.default_pattern, None, None

    def int_filter(self, conf):
        return r'-?\d+', int, lambda x: str(int(x))

    def float_filter(self, conf):
        return r'-?[\d.]+', float, lambda x: str(float(x))

    def path_filter(self, conf):
        return r'.*?', None, None
    
    def add_filter(self, name, func):
        ''' Add a filter. The provided function is called with the configuration
        string as parameter and must return a (regexp, to_python, to_url) tuple.
        The first element is a string, the last two are callables or None. '''
        self.filters[name] = func
    
    def parse_rule(self, rule):
        ''' Parses a rule into a (name, filter, conf) token stream. If mode is
            None, name contains a static rule part. '''
        offset, prefix = 0, ''
        for match in self.rule_syntax.finditer(rule):
            prefix += rule[offset:match.start()]
            g = match.groups()
            if len(g[0])%2: # Escaped wildcard
                prefix += match.group(0)[len(g[0]):]
                offset = match.end()
                continue
            if prefix: yield prefix, None, None
            name, filtr, conf = g[1:4] if not g[2] is None else g[4:7]
            if not filtr: filtr = self.default_filter
            yield name, filtr, conf or None
            offset, prefix = match.end(), ''
        if offset <= len(rule) or prefix:
            yield prefix+rule[offset:], None, None

    def add(self, rule, method, target, name=None):
        ''' Add a new route or replace the target for an existing route. '''
        if rule in self.rules:
            self.rules[rule][method] = target
            if name: self.builder[name] = self.builder[rule]
            return

        target = self.rules[rule] = {method: target}

        # Build pattern and other structures for dynamic routes
        anons = 0      # Number of anonymous wildcards
        pattern = ''   # Regular expression  pattern
        filters = []   # Lists of wildcard input filters
        builder = []   # Data structure for the URL builder
        is_static = True
        for key, mode, conf in self.parse_rule(rule):
            if mode:
                is_static = False
                mask, in_filter, out_filter = self.filters[mode](conf)
                if key:
                    pattern += '(?P<%s>%s)' % (key, mask)
                else:
                    pattern += '(?:%s)' % mask
                    key = 'anon%d' % anons; anons += 1
                if in_filter: filters.append((key, in_filter))
                builder.append((key, out_filter or str))
            elif key:
                pattern += re.escape(key)
                builder.append((None, key))
        self.builder[rule] = builder
        if name: self.builder[name] = builder

        if is_static and not self.strict_order:
            self.static[self.build(rule)] = target
            return

        def fpat_sub(m):
            return m.group(0) if len(m.group(1)) % 2 else m.group(1) + '(?:'
        flat_pattern = re.sub(r'(\\*)(\(\?P<[^>]*>|\((?!\?))', fpat_sub, pattern)

        try:
            re_match = re.compile('^(%s)$' % pattern).match
        except re.error, e:
            raise RouteSyntaxError("Could not add Route: %s (%s)" % (rule, e))

        def match(path):
            """ Return an url-argument dictionary. """
            url_args = re_match(path).groupdict()
            for name, wildcard_filter in filters:
                try:
                    url_args[name] = wildcard_filter(url_args[name])
                except ValueError:
                    raise HTTPError(400, 'Path has wrong format.')
            return url_args

        try:
            combined = '%s|(^%s$)' % (self.dynamic[-1][0].pattern, flat_pattern)
            self.dynamic[-1] = (re.compile(combined), self.dynamic[-1][1])
            self.dynamic[-1][1].append((match, target))
        except (AssertionError, IndexError), e: # AssertionError: Too many groups
            self.dynamic.append((re.compile('(^%s$)' % flat_pattern),
                                [(match, target)]))
        return match

    def build(self, _name, *anons, **query):
        ''' Build an URL by filling the wildcards in a rule. '''
        builder = self.builder.get(_name)
        if not builder: raise RouteBuildError("No route with that name.", _name)
        try:
            for i, value in enumerate(anons): query['anon%d'%i] = value
            url = ''.join([f(query.pop(n)) if n else f for (n,f) in builder])
            return url if not query else url+'?'+urlencode(query)
        except KeyError, e:
            raise RouteBuildError('Missing URL argument: %r' % e.args[0])

    def match(self, environ):
        ''' Return a (target, url_agrs) tuple or raise HTTPError(400/404/405). '''
        path, targets, urlargs = environ['PATH_INFO'] or '/', None, {}
        if path in self.static:
            targets = self.static[path]
        else:
            for combined, rules in self.dynamic:
                match = combined.match(path)
                if not match: continue
                getargs, targets = rules[match.lastindex - 1]
                urlargs = getargs(path) if getargs else {}
                break

        if not targets:
            raise HTTPError(404, "Not found: " + repr(environ['PATH_INFO']))
        method = environ['REQUEST_METHOD'].upper()
        if method in targets:
            return targets[method], urlargs
        if method == 'HEAD' and 'GET' in targets:
            return targets['GET'], urlargs
        if 'ANY' in targets:
            return targets['ANY'], urlargs
        allowed = [verb for verb in targets if verb != 'ANY']
        if 'GET' in allowed and 'HEAD' not in allowed:
            allowed.append('HEAD')
        raise HTTPError(405, "Method not allowed.",
                        header=[('Allow',",".join(allowed))])



class Route(object):
    ''' This class wraps a route callback along with route specific metadata and
        configuration and applies Plugins on demand. It is also responsible for
        turing an URL path rule into a regular expression usable by the Router.
    '''


    def __init__(self, app, rule, method, callback, name=None,
                 plugins=None, skiplist=None, **config):
        #: The application this route is installed to.
        self.app = app
        #: The path-rule string (e.g. ``/wiki/:page``).
        self.rule = rule
        #: The HTTP method as a string (e.g. ``GET``).
        self.method = method
        #: The original callback with no plugins applied. Useful for introspection.
        self.callback = callback
        #: The name of the route (if specified) or ``None``.
        self.name = name or None
        #: A list of route-specific plugins (see :meth:`Bottle.route`).
        self.plugins = plugins or []
        #: A list of plugins to not apply to this route (see :meth:`Bottle.route`).
        self.skiplist = skiplist or []
        #: Additional keyword arguments passed to the :meth:`Bottle.route`
        #: decorator are stored in this dictionary. Used for route-specific
        #: plugin configuration and meta-data.
        self.config = ConfigDict(config)

    def __call__(self, *a, **ka):
        depr("Some APIs changed to return Route() instances instead of"\
             " callables. Make sure to use the Route.call method and not to"\
             " call Route instances directly.")
        return self.call(*a, **ka)

    @cached_property
    def call(self):
        ''' The route callback with all plugins applied. This property is
            created on demand and then cached to speed up subsequent requests.'''
        return self._make_callback()

    def reset(self):
        ''' Forget any cached values. The next time :attr:`call` is accessed,
            all plugins are re-applied. '''
        self.__dict__.pop('call', None)

    def prepare(self):
        ''' Do all on-demand work immediately (useful for debugging).'''
        self.call

    @property
    def _context(self):
        depr('Switch to Plugin API v2 and access the Route object directly.')
        return dict(rule=self.rule, method=self.method, callback=self.callback,
                    name=self.name, app=self.app, config=self.config,
                    apply=self.plugins, skip=self.skiplist)

    def all_plugins(self):
        ''' Yield all Plugins affecting this route. '''
        unique = set()
        for p in reversed(self.app.plugins + self.plugins):
            if True in self.skiplist: break
            name = getattr(p, 'name', False)
            if name and (name in self.skiplist or name in unique): continue
            if p in self.skiplist or type(p) in self.skiplist: continue
            if name: unique.add(name)
            yield p

    def _make_callback(self):
        callback = self.callback
        for plugin in self.all_plugins():
            try:
                if hasattr(plugin, 'apply'):
                    api = getattr(plugin, 'api', 1)
                    context = self if api > 1 else self._context
                    callback = plugin.apply(callback, context)
                else:
                    callback = plugin(callback)
            except RouteReset: # Try again with changed configuration.
                return self._make_callback()
            if not callback is self.callback:
                try_update_wrapper(callback, self.callback)
        return callback






###############################################################################
# Application Object ###########################################################
###############################################################################


class Bottle(object):
    """ WSGI application """

    def __init__(self, catchall=True, autojson=True, config=None):
        """ Create a new bottle instance.
            You usually don't do that. Use `bottle.app.push()` instead.
        """
        self.routes = [] # List of installed :class:`Route` instances.
        self.router = Router() # Maps requests to :class:`Route` instances.
        self.plugins = [] # List of installed plugins.

        self.error_handler = {}
        #: If true, most exceptions are catched and returned as :exc:`HTTPError`
        self.config = ConfigDict(config or {})
        self.catchall = catchall
        #: An instance of :class:`HooksPlugin`. Empty by default.
        self.hooks = HooksPlugin()
        self.install(self.hooks)
        if autojson:
            self.install(JSONPlugin())
        self.install(TemplatePlugin())

    def mount(self, prefix, app, **options):
        ''' Mount an application (:class:`Bottle` or plain WSGI) to a specific
            URL prefix. Example::

                root_app.mount('/admin/', admin_app)

            :param prefix: path prefix or `mount-point`. If it ends in a slash,
                that slash is mandatory.
            :param app: an instance of :class:`Bottle` or a WSGI application.

            All other parameters are passed to the underlying :meth:`route` call.
        '''
        if isinstance(app, basestring):
            prefix, app = app, prefix
            depr('Parameter order of Bottle.mount() changed.') # 0.10

        parts = filter(None, prefix.split('/'))
        if not parts: raise ValueError('Empty path prefix.')
        path_depth = len(parts)
        options.setdefault('skip', True)
        options.setdefault('method', 'ANY')

        @self.route('/%s/:#.*#' % '/'.join(parts), **options)
        def mountpoint():
            try:
                request.path_shift(path_depth)
                rs = BaseResponse([], 200)
                def start_response(status, header):
                    rs.status = status
                    for name, value in header: rs.add_header(name, value)
                    return rs.body.append
                rs.body = itertools.chain(rs.body, app(request.environ, start_response))
                return HTTPResponse(rs.body, rs.status_code, rs.headers)
            finally:
                request.path_shift(-path_depth)

        if not prefix.endswith('/'):
            self.route('/' + '/'.join(parts), callback=mountpoint, **options)

    def install(self, plugin):
        ''' Add a plugin to the list of plugins and prepare it for being
            applied to all routes of this application. A plugin may be a simple
            decorator or an object that implements the :class:`Plugin` API.
        '''
        if hasattr(plugin, 'setup'): plugin.setup(self)
        if not callable(plugin) and not hasattr(plugin, 'apply'):
            raise TypeError("Plugins must be callable or implement .apply()")
        self.plugins.append(plugin)
        self.reset()
        return plugin

    def uninstall(self, plugin):
        ''' Uninstall plugins. Pass an instance to remove a specific plugin, a type
            object to remove all plugins that match that type, a string to remove
            all plugins with a matching ``name`` attribute or ``True`` to remove all
            plugins. Return the list of removed plugins. '''
        removed, remove = [], plugin
        for i, plugin in list(enumerate(self.plugins))[::-1]:
            if remove is True or remove is plugin or remove is type(plugin) \
            or getattr(plugin, 'name', True) == remove:
                removed.append(plugin)
                del self.plugins[i]
                if hasattr(plugin, 'close'): plugin.close()
        if removed: self.reset()
        return removed

    def reset(self, route=None):
        ''' Reset all routes (force plugins to be re-applied) and clear all
            caches. If an ID or route object is given, only that specific route
            is affected. '''
        if route is None: routes = self.routes
        elif isinstance(route, Route): routes = [route]
        else: routes = [self.routes[route]]
        for route in routes: route.reset()
        if DEBUG:
            for route in routes: route.prepare()
        self.hooks.trigger('app_reset')

    def close(self):
        ''' Close the application and all installed plugins. '''
        for plugin in self.plugins:
            if hasattr(plugin, 'close'): plugin.close()
        self.stopped = True

    def match(self, environ):
        """ Search for a matching route and return a (:class:`Route` , urlargs)
            tuple. The second value is a dictionary with parameters extracted
            from the URL. Raise :exc:`HTTPError` (404/405) on a non-match."""
        return self.router.match(environ)

    def get_url(self, routename, **kargs):
        """ Return a string that matches a named route """
        scriptname = request.environ.get('SCRIPT_NAME', '').strip('/') + '/'
        location = self.router.build(routename, **kargs).lstrip('/')
        return urljoin(urljoin('/', scriptname), location)

    def route(self, path=None, method='GET', callback=None, name=None,
              apply=None, skip=None, **config):
        """ A decorator to bind a function to a request URL. Example::

                @app.route('/hello/:name')
                def hello(name):
                    return 'Hello %s' % name

            The ``:name`` part is a wildcard. See :class:`Router` for syntax
            details.

            :param path: Request path or a list of paths to listen to. If no
              path is specified, it is automatically generated from the
              signature of the function.
            :param method: HTTP method (`GET`, `POST`, `PUT`, ...) or a list of
              methods to listen to. (default: `GET`)
            :param callback: An optional shortcut to avoid the decorator
              syntax. ``route(..., callback=func)`` equals ``route(...)(func)``
            :param name: The name for this route. (default: None)
            :param apply: A decorator or plugin or a list of plugins. These are
              applied to the route callback in addition to installed plugins.
            :param skip: A list of plugins, plugin classes or names. Matching
              plugins are not installed to this route. ``True`` skips all.

            Any additional keyword arguments are stored as route-specific
            configuration and passed to plugins (see :meth:`Plugin.apply`).
        """
        if callable(path): path, callback = None, path
        plugins = makelist(apply)
        skiplist = makelist(skip)
        def decorator(callback):
            # TODO: Documentation and tests
            if isinstance(callback, basestring): callback = load(callback)
            for rule in makelist(path) or yieldroutes(callback):
                for verb in makelist(method):
                    verb = verb.upper()
                    route = Route(self, rule, verb, callback, name=name,
                                  plugins=plugins, skiplist=skiplist, **config)
                    self.routes.append(route)
                    self.router.add(rule, verb, route, name=name)
                    if DEBUG: route.prepare()
            return callback
        return decorator(callback) if callback else decorator

    def get(self, path=None, method='GET', **options):
        """ Equals :meth:`route`. """
        return self.route(path, method, **options)

    def post(self, path=None, method='POST', **options):
        """ Equals :meth:`route` with a ``POST`` method parameter. """
        return self.route(path, method, **options)

    def put(self, path=None, method='PUT', **options):
        """ Equals :meth:`route` with a ``PUT`` method parameter. """
        return self.route(path, method, **options)

    def delete(self, path=None, method='DELETE', **options):
        """ Equals :meth:`route` with a ``DELETE`` method parameter. """
        return self.route(path, method, **options)

    def error(self, code=500):
        """ Decorator: Register an output handler for a HTTP error code"""
        def wrapper(handler):
            self.error_handler[int(code)] = handler
            return handler
        return wrapper

    def hook(self, name):
        """ Return a decorator that attaches a callback to a hook. """
        def wrapper(func):
            self.hooks.add(name, func)
            return func
        return wrapper

    def handle(self, path, method='GET'):
        """ (deprecated) Execute the first matching route callback and return
            the result. :exc:`HTTPResponse` exceptions are catched and returned.
            If :attr:`Bottle.catchall` is true, other exceptions are catched as
            well and returned as :exc:`HTTPError` instances (500).
        """
        depr("This method will change semantics in 0.10. Try to avoid it.")
        if isinstance(path, dict):
            return self._handle(path)
        return self._handle({'PATH_INFO': path, 'REQUEST_METHOD': method.upper()})

    def _handle(self, environ):
        try:
            route, args = self.router.match(environ)
            environ['route.handle'] = environ['bottle.route'] = route
            environ['route.url_args'] = args
            return route.call(**args)
        except HTTPResponse, r:
            return r
        except RouteReset:
            route.reset()
            return self._handle(environ)
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception, e:
            if not self.catchall: raise
            stacktrace = format_exc(10)
            environ['wsgi.errors'].write(stacktrace)
            return HTTPError(500, "Internal Server Error", e, stacktrace)

    def _cast(self, out, request, response, peek=None):
        """ Try to convert the parameter into something WSGI compatible and set
        correct HTTP headers when possible.
        Support: False, str, unicode, dict, HTTPResponse, HTTPError, file-like,
        iterable of strings and iterable of unicodes
        """

        # Empty output is done here
        if not out:
            response['Content-Length'] = 0
            return []
        # Join lists of byte or unicode strings. Mixed lists are NOT supported
        if isinstance(out, (tuple, list))\
        and isinstance(out[0], (bytes, unicode)):
            out = out[0][0:0].join(out) # b'abc'[0:0] -> b''
        # Encode unicode strings
        if isinstance(out, unicode):
            out = out.encode(response.charset)
        # Byte Strings are just returned
        if isinstance(out, bytes):
            response['Content-Length'] = len(out)
            return [out]
        # HTTPError or HTTPException (recursive, because they may wrap anything)
        # TODO: Handle these explicitly in handle() or make them iterable.
        if isinstance(out, HTTPError):
            out.apply(response)
            out = self.error_handler.get(out.status, repr)(out)
            if isinstance(out, HTTPResponse):
                depr('Error handlers must not return :exc:`HTTPResponse`.') #0.9
            return self._cast(out, request, response)
        if isinstance(out, HTTPResponse):
            out.apply(response)
            return self._cast(out.output, request, response)

        # File-like objects.
        if hasattr(out, 'read'):
            if 'wsgi.file_wrapper' in request.environ:
                return request.environ['wsgi.file_wrapper'](out)
            elif hasattr(out, 'close') or not hasattr(out, '__iter__'):
                return WSGIFileWrapper(out)

        # Handle Iterables. We peek into them to detect their inner type.
        try:
            out = iter(out)
            first = out.next()
            while not first:
                first = out.next()
        except StopIteration:
            return self._cast('', request, response)
        except HTTPResponse, e:
            first = e
        except Exception, e:
            first = HTTPError(500, 'Unhandled exception', e, format_exc(10))
            if isinstance(e, (KeyboardInterrupt, SystemExit, MemoryError))\
            or not self.catchall:
                raise
        # These are the inner types allowed in iterator or generator objects.
        if isinstance(first, HTTPResponse):
            return self._cast(first, request, response)
        if isinstance(first, bytes):
            return itertools.chain([first], out)
        if isinstance(first, unicode):
            return itertools.imap(lambda x: x.encode(response.charset),
                                  itertools.chain([first], out))
        return self._cast(HTTPError(500, 'Unsupported response type: %s'\
                                         % type(first)), request, response)

    def wsgi(self, environ, start_response):
        """ The bottle WSGI-interface. """
        try:
            environ['bottle.app'] = self
            request.bind(environ)
            response.bind()
            out = self._cast(self._handle(environ), request, response)
            # rfc2616 section 4.3
            if response._status_code in (100, 101, 204, 304)\
            or request.method == 'HEAD':
                if hasattr(out, 'close'): out.close()
                out = []
            start_response(response._status_line, list(response.iter_headers()))
            return out
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception, e:
            if not self.catchall: raise
            err = '<h1>Critical error while processing request: %s</h1>' \
                  % html_escape(environ.get('PATH_INFO', '/'))
            if DEBUG:
                err += '<h2>Error:</h2>\n<pre>\n%s\n</pre>\n' \
                       '<h2>Traceback:</h2>\n<pre>\n%s\n</pre>\n' \
                       % (html_escape(repr(e)), html_escape(format_exc(10)))
            environ['wsgi.errors'].write(err)
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            start_response('500 INTERNAL SERVER ERROR', headers)
            return [tob(err)]

    def __call__(self, environ, start_response):
        ''' Each instance of :class:'Bottle' is a WSGI application. '''
        return self.wsgi(environ, start_response)






###############################################################################
# HTTP and WSGI Tools ##########################################################
###############################################################################


class BaseRequest(DictMixin):
    """ A wrapper for WSGI environment dictionaries that adds a lot of
        convenient access methods and properties. Most of them are read-only."""

    #: Maximum size of memory buffer for :attr:`body` in bytes.
    MEMFILE_MAX = 102400
    #: Maximum number pr GET or POST parameters per request
    MAX_PARAMS  = 100

    def __init__(self, environ):
        """ Wrap a WSGI environ dictionary. """
        #: The wrapped WSGI environ dictionary. This is the only real attribute.
        #: All other attributes actually are read-only properties.
        self.environ = environ
        environ['bottle.request'] = self

    @property
    def path(self):
        ''' The value of ``PATH_INFO`` with exactly one prefixed slash (to fix
            broken clients and avoid the "empty path" edge case). '''
        return '/' + self.environ.get('PATH_INFO','').lstrip('/')

    @property
    def method(self):
        ''' The ``REQUEST_METHOD`` value as an uppercase string. '''
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    @DictProperty('environ', 'bottle.request.headers', read_only=True)
    def headers(self):
        ''' A :class:`WSGIHeaderDict` that provides case-insensitive access to
            HTTP request headers. '''
        return WSGIHeaderDict(self.environ)

    def get_header(self, name, default=None):
        ''' Return the value of a request header, or a given default value. '''
        return self.headers.get(name, default)

    @DictProperty('environ', 'bottle.request.cookies', read_only=True)
    def cookies(self):
        """ Cookies parsed into a :class:`FormsDict`. Signed cookies are NOT
            decoded. Use :meth:`get_cookie` if you expect signed cookies. """
        cookies = SimpleCookie(self.environ.get('HTTP_COOKIE',''))
        cookies = list(cookies.values())[:self.MAX_PARAMS]
        return FormsDict((c.key, c.value) for c in cookies)

    def get_cookie(self, key, default=None, secret=None):
        """ Return the content of a cookie. To read a `Signed Cookie`, the
            `secret` must match the one used to create the cookie (see
            :meth:`BaseResponse.set_cookie`). If anything goes wrong (missing
            cookie or wrong signature), return a default value. """
        value = self.cookies.get(key)
        if secret and value:
            dec = cookie_decode(value, secret) # (key, value) tuple or None
            return dec[1] if dec and dec[0] == key else default
        return value or default

    @DictProperty('environ', 'bottle.request.query', read_only=True)
    def query(self):
        ''' The :attr:`query_string` parsed into a :class:`FormsDict`. These
            values are sometimes called "URL arguments" or "GET parameters", but
            not to be confused with "URL wildcards" as they are provided by the
            :class:`Router`. '''
        pairs = parse_qsl(self.query_string, keep_blank_values=True)
        get = self.environ['bottle.get'] = FormsDict()
        for key, value in pairs[:self.MAX_PARAMS]:
            get[key] = value
        return get

    @DictProperty('environ', 'bottle.request.forms', read_only=True)
    def forms(self):
        """ Form values parsed from an `url-encoded` or `multipart/form-data`
            encoded POST or PUT request body. The result is retuned as a
            :class:`FormsDict`. All keys and values are strings. File uploads
            are stored separately in :attr:`files`. """
        forms = FormsDict()
        for name, item in self.POST.iterallitems():
            if not hasattr(item, 'filename'):
                forms[name] = item
        return forms

    @DictProperty('environ', 'bottle.request.params', read_only=True)
    def params(self):
        """ A :class:`FormsDict` with the combined values of :attr:`query` and
            :attr:`forms`. File uploads are stored in :attr:`files`. """
        params = FormsDict()
        for key, value in self.query.iterallitems():
            params[key] = value
        for key, value in self.forms.iterallitems():
            params[key] = value
        return params

    @DictProperty('environ', 'bottle.request.files', read_only=True)
    def files(self):
        """ File uploads parsed from an `url-encoded` or `multipart/form-data`
            encoded POST or PUT request body. The values are instances of
            :class:`cgi.FieldStorage`. The most important attributes are:

            filename
                The filename, if specified; otherwise None; this is the client
                side filename, *not* the file name on which it is stored (that's
                a temporary file you don't deal with)
            file
                The file(-like) object from which you can read the data.
            value
                The value as a *string*; for file uploads, this transparently
                reads the file every time you request the value. Do not do this
                on big files.
        """
        files = FormsDict()
        for name, item in self.POST.iterallitems():
            if hasattr(item, 'filename'):
                files[name] = item
        return files

    @DictProperty('environ', 'bottle.request.json', read_only=True)
    def json(self):
        ''' If the ``Content-Type`` header is ``application/json``, this
            property holds the parsed content of the request body. Only requests
            smaller than :attr:`MEMFILE_MAX` are processed to avoid memory
            exhaustion. '''
        if 'application/json' in self.environ.get('CONTENT_TYPE', '') \
        and 0 < self.content_length < self.MEMFILE_MAX:
            return json_loads(self.body.read(self.MEMFILE_MAX))
        return None

    @DictProperty('environ', 'bottle.request.body', read_only=True)
    def _body(self):
        maxread = max(0, self.content_length)
        stream = self.environ['wsgi.input']
        body = BytesIO() if maxread < self.MEMFILE_MAX else TemporaryFile(mode='w+b')
        while maxread > 0:
            part = stream.read(min(maxread, self.MEMFILE_MAX))
            if not part: break
            body.write(part)
            maxread -= len(part)
        self.environ['wsgi.input'] = body
        body.seek(0)
        return body

    @property
    def body(self):
        """ The HTTP request body as a seek-able file-like object. Depending on
            :attr:`MEMFILE_MAX`, this is either a temporary file or a
            :class:`io.BytesIO` instance. Accessing this property for the first
            time reads and replaces the ``wsgi.input`` environ variable.
            Subsequent accesses just do a `seek(0)` on the file object. """
        self._body.seek(0)
        return self._body

    #: An alias for :attr:`query`.
    GET = query

    @DictProperty('environ', 'bottle.request.post', read_only=True)
    def POST(self):
        """ The values of :attr:`forms` and :attr:`files` combined into a single
            :class:`FormsDict`. Values are either strings (form values) or
            instances of :class:`cgi.FieldStorage` (file uploads).
        """
        post = FormsDict()
        safe_env = {'QUERY_STRING':''} # Build a safe environment for cgi
        for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
            if key in self.environ: safe_env[key] = self.environ[key]
        if NCTextIOWrapper:
            fb = NCTextIOWrapper(self.body, encoding='ISO-8859-1', newline='\n')
        else:
            fb = self.body
        data = cgi.FieldStorage(fp=fb, environ=safe_env, keep_blank_values=True)
        for item in (data.list or [])[:self.MAX_PARAMS]:
            post[item.name] = item if item.filename else item.value
        return post

    @property
    def COOKIES(self):
        ''' Alias for :attr:`cookies` (deprecated). '''
        depr('BaseRequest.COOKIES was renamed to BaseRequest.cookies (lowercase).')
        return self.cookies

    @property
    def url(self):
        """ The full request URI including hostname and scheme. If your app
            lives behind a reverse proxy or load balancer and you get confusing
            results, make sure that the ``X-Forwarded-Host`` header is set
            correctly. """
        return self.urlparts.geturl()

    @DictProperty('environ', 'bottle.request.urlparts', read_only=True)
    def urlparts(self):
        ''' The :attr:`url` string as an :class:`urlparse.SplitResult` tuple.
            The tuple contains (scheme, host, path, query_string and fragment),
            but the fragment is always empty because it is not visible to the
            server. '''
        env = self.environ
        http = env.get('wsgi.url_scheme', 'http')
        host = env.get('HTTP_X_FORWARDED_HOST') or env.get('HTTP_HOST')
        if not host:
            # HTTP 1.1 requires a Host-header. This is for HTTP/1.0 clients.
            host = env.get('SERVER_NAME', '127.0.0.1')
            port = env.get('SERVER_PORT')
            if port and port != ('80' if http == 'http' else '443'):
                host += ':' + port
        path = urlquote(self.fullpath)
        return UrlSplitResult(http, host, path, env.get('QUERY_STRING'), '')

    @property
    def fullpath(self):
        """ Request path including :attr:`script_name` (if present). """
        return urljoin(self.script_name, self.path.lstrip('/'))

    @property
    def query_string(self):
        """ The raw :attr:`query` part of the URL (everything in between ``?``
            and ``#``) as a string. """
        return self.environ.get('QUERY_STRING', '')

    @property
    def script_name(self):
        ''' The initial portion of the URL's `path` that was removed by a higher
            level (server or routing middleware) before the application was
            called. This script path is returned with leading and tailing
            slashes. '''
        script_name = self.environ.get('SCRIPT_NAME', '').strip('/')
        return '/' + script_name + '/' if script_name else '/'

    def path_shift(self, shift=1):
        ''' Shift path segments from :attr:`path` to :attr:`script_name` and
            vice versa.

           :param shift: The number of path segments to shift. May be negative
                         to change the shift direction. (default: 1)
        '''
        script = self.environ.get('SCRIPT_NAME','/')
        self['SCRIPT_NAME'], self['PATH_INFO'] = path_shift(script, self.path, shift)

    @property
    def content_length(self):
        ''' The request body length as an integer. The client is responsible to
            set this header. Otherwise, the real length of the body is unknown
            and -1 is returned. In this case, :attr:`body` will be empty. '''
        return int(self.environ.get('CONTENT_LENGTH') or -1)

    @property
    def is_xhr(self):
        ''' True if the request was triggered by a XMLHttpRequest. This only
            works with JavaScript libraries that support the `X-Requested-With`
            header (most of the popular libraries do). '''
        requested_with = self.environ.get('HTTP_X_REQUESTED_WITH','')
        return requested_with.lower() == 'xmlhttprequest'

    @property
    def is_ajax(self):
        ''' Alias for :attr:`is_xhr`. "Ajax" is not the right term. '''
        return self.is_xhr

    @property
    def auth(self):
        """ HTTP authentication data as a (user, password) tuple. This
            implementation currently supports basic (not digest) authentication
            only. If the authentication happened at a higher level (e.g. in the
            front web-server or a middleware), the password field is None, but
            the user field is looked up from the ``REMOTE_USER`` environ
            variable. On any errors, None is returned. """
        basic = parse_auth(self.environ.get('HTTP_AUTHORIZATION',''))
        if basic: return basic
        ruser = self.environ.get('REMOTE_USER')
        if ruser: return (ruser, None)
        return None

    @property
    def remote_route(self):
        """ A list of all IPs that were involved in this request, starting with
            the client IP and followed by zero or more proxies. This does only
            work if all proxies support the ```X-Forwarded-For`` header. Note
            that this information can be forged by malicious clients. """
        proxy = self.environ.get('HTTP_X_FORWARDED_FOR')
        if proxy: return [ip.strip() for ip in proxy.split(',')]
        remote = self.environ.get('REMOTE_ADDR')
        return [remote] if remote else []

    @property
    def remote_addr(self):
        """ The client IP as a string. Note that this information can be forged
            by malicious clients. """
        route = self.remote_route
        return route[0] if route else None

    def copy(self):
        """ Return a new :class:`Request` with a shallow :attr:`environ` copy. """
        return BaseRequest(self.environ.copy())

    def __getitem__(self, key): return self.environ[key]
    def __delitem__(self, key): self[key] = ""; del(self.environ[key])
    def __iter__(self): return iter(self.environ)
    def __len__(self): return len(self.environ)
    def keys(self): return self.environ.keys()
    def __setitem__(self, key, value):
        """ Change an environ value and clear all caches that depend on it. """

        if self.environ.get('bottle.request.readonly'):
            raise KeyError('The environ dictionary is read-only.')

        self.environ[key] = value
        todelete = ()

        if key == 'wsgi.input':
            todelete = ('body', 'forms', 'files', 'params', 'post', 'json')
        elif key == 'QUERY_STRING':
            todelete = ('query', 'params')
        elif key.startswith('HTTP_'):
            todelete = ('headers', 'cookies')

        for key in todelete:
            self.environ.pop('bottle.request.'+key, None)

    def __repr__(self):
        return '<%s: %s %s>' % (self.__class__.__name__, self.method, self.url)

def _hkey(s):
    return s.title().replace('_','-')


class HeaderProperty(object):
    def __init__(self, name, reader=None, writer=str, default=''):
        self.name, self.reader, self.writer, self.default = name, reader, writer, default
        self.__doc__ = 'Current value of the %r header.' % name.title()

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.headers.get(self.name)
        return self.reader(value) if (value and self.reader) else (value or self.default)

    def __set__(self, obj, value):
        if self.writer: value = self.writer(value)
        obj.headers[self.name] = value

    def __delete__(self, obj):
        if self.name in obj.headers:
            del obj.headers[self.name]


class BaseResponse(object):
    """ Storage class for a response body as well as headers and cookies.

        This class does support dict-like case-insensitive item-access to
        headers, but is NOT a dict. Most notably, iterating over a response
        yields parts of the body and not the headers.
    """

    default_status = 200
    default_content_type = 'text/html; charset=UTF-8'

    # Header blacklist for specific response codes
    # (rfc2616 section 10.2.3 and 10.3.5)
    bad_headers = {
        204: set(('Content-Type',)),
        304: set(('Allow', 'Content-Encoding', 'Content-Language',
                  'Content-Length', 'Content-Range', 'Content-Type',
                  'Content-Md5', 'Last-Modified'))}

    def __init__(self, body='', status=None, **headers):
        self._status_line = None
        self._status_code = None
        self.body = body
        self._cookies = None
        self._headers = {'Content-Type': [self.default_content_type]}
        self.status = status or self.default_status
        if headers:
            for name, value in headers.items():
                self[name] = value

    def copy(self):
        ''' Returns a copy of self. '''
        copy = Response()
        copy.status = self.status
        copy._headers = dict((k, v[:]) for (k, v) in self._headers.items())
        return copy

    def __iter__(self):
        return iter(self.body)

    def close(self):
        if hasattr(self.body, 'close'):
            self.body.close()

    @property
    def status_line(self):
        ''' The HTTP status line as a string (e.g. ``404 Not Found``).'''
        return self._status_line

    @property
    def status_code(self):
        ''' The HTTP status code as an integer (e.g. 404).'''
        return self._status_code

    def _set_status(self, status):
        if isinstance(status, int):
            code, status = status, _HTTP_STATUS_LINES.get(status)
        elif ' ' in status:
            status = status.strip()
            code   = int(status.split()[0])
        else:
            raise ValueError('String status line without a reason phrase.')
        if not 100 <= code <= 999: raise ValueError('Status code out of range.')
        self._status_code = code
        self._status_line = status or ('%d Unknown' % code)

    def _get_status(self):
        depr('BaseRequest.status will change to return a string in 0.11. Use'\
             ' status_line and status_code to make sure.') #0.10
        return self._status_code

    status = property(_get_status, _set_status, None,
        ''' A writeable property to change the HTTP response status. It accepts
            either a numeric code (100-999) or a string with a custom reason
            phrase (e.g. "404 Brain not found"). Both :data:`status_line` and
            :data:`status_code` are updates accordingly. The return value is
            always a numeric code. ''')
    del _get_status, _set_status

    @property
    def headers(self):
        ''' An instance of :class:`HeaderDict`, a case-insensitive dict-like
            view on the response headers. '''
        self.__dict__['headers'] = hdict = HeaderDict()
        hdict.dict = self._headers
        return hdict

    def __contains__(self, name): return _hkey(name) in self._headers
    def __delitem__(self, name):  del self._headers[_hkey(name)]
    def __getitem__(self, name):  return self._headers[_hkey(name)][-1]
    def __setitem__(self, name, value): self._headers[_hkey(name)] = [str(value)]

    def get_header(self, name, default=None):
        ''' Return the value of a previously defined header. If there is no
            header with that name, return a default value. '''
        return self._headers.get(_hkey(name), [default])[-1]

    def set_header(self, name, value, append=False):
        ''' Create a new response header, replacing any previously defined
            headers with the same name. '''
        if append:
            self.add_header(name, value)
        else:
            self._headers[_hkey(name)] = [str(value)]

    def add_header(self, name, value):
        ''' Add an additional response header, not removing duplicates. '''
        self._headers.setdefault(_hkey(name), []).append(str(value))

    def iter_headers(self):
        ''' Yield (header, value) tuples, skipping headers that are not
            allowed with the current response status code. '''
        headers = self._headers.iteritems()
        bad_headers = self.bad_headers.get(self.status_code)
        if bad_headers:
            headers = [h for h in headers if h[0] not in bad_headers]
        for name, values in headers:
            for value in values:
                yield name, value
        if self._cookies:
            for c in self._cookies.values():
                yield 'Set-Cookie', c.OutputString()

    def wsgiheader(self):
        depr('The wsgiheader method is deprecated. See headerlist.') #0.10
        return self.headerlist

    @property
    def headerlist(self):
        ''' WSGI conform list of (header, value) tuples. '''
        return list(self.iter_headers())

    content_type = HeaderProperty('Content-Type')
    content_length = HeaderProperty('Content-Length', reader=int)

    @property
    def charset(self):
        """ Return the charset specified in the content-type header (default: utf8). """
        if 'charset=' in self.content_type:
            return self.content_type.split('charset=')[-1].split(';')[0].strip()
        return 'UTF-8'

    @property
    def COOKIES(self):
        """ A dict-like SimpleCookie instance. This should not be used directly.
            See :meth:`set_cookie`. """
        depr('The COOKIES dict is deprecated. Use `set_cookie()` instead.') # 0.10
        if not self._cookies:
            self._cookies = SimpleCookie()
        return self._cookies

    def set_cookie(self, name, value, secret=None, **options):
        ''' Create a new cookie or replace an old one. If the `secret` parameter is
            set, create a `Signed Cookie` (described below).

            :param name: the name of the cookie.
            :param value: the value of the cookie.
            :param secret: a signature key required for signed cookies.

            Additionally, this method accepts all RFC 2109 attributes that are
            supported by :class:`cookie.Morsel`, including:

            :param max_age: maximum age in seconds. (default: None)
            :param expires: a datetime object or UNIX timestamp. (default: None)
            :param domain: the domain that is allowed to read the cookie.
              (default: current domain)
            :param path: limits the cookie to a given path (default: current path)
            :param secure: limit the cookie to HTTPS connections (default: off).
            :param httponly: prevents client-side javascript to read this cookie
              (default: off, requires Python 2.6 or newer).

            If neither `expires` nor `max_age` is set (default), the cookie will
            expire at the end of the browser session (as soon as the browser
            window is closed).

            Signed cookies may store any pickle-able object and are
            cryptographically signed to prevent manipulation. Keep in mind that
            cookies are limited to 4kb in most browsers.

            Warning: Signed cookies are not encrypted (the client can still see
            the content) and not copy-protected (the client can restore an old
            cookie). The main intention is to make pickling and unpickling
            save, not to store secret information at client side.
        '''
        if not self._cookies:
            self._cookies = SimpleCookie()

        if secret:
            value = touni(cookie_encode((name, value), secret))
        elif not isinstance(value, basestring):
            raise TypeError('Secret key missing for non-string Cookie.')

        if len(value) > 4096: raise ValueError('Cookie value to long.')
        self._cookies[name] = value

        for key, value in options.iteritems():
            if key == 'max_age':
                if isinstance(value, timedelta):
                    value = value.seconds + value.days * 24 * 3600
            if key == 'expires':
                if isinstance(value, (datedate, datetime)):
                    value = value.timetuple()
                elif isinstance(value, (int, float)):
                    value = time.gmtime(value)
                value = time.strftime("%a, %d %b %Y %H:%M:%S GMT", value)
            self._cookies[name][key.replace('_', '-')] = value

    def delete_cookie(self, key, **kwargs):
        ''' Delete a cookie. Be sure to use the same `domain` and `path`
            settings as used to create the cookie. '''
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def __repr__(self):
        out = ''
        for name, value in self.headerlist:
            out += '%s: %s\n' % (name.title(), value.strip())
        return out


class LocalRequest(BaseRequest, threading.local):
    ''' A thread-local subclass of :class:`BaseRequest`. '''
    def __init__(self): pass
    bind = BaseRequest.__init__


class LocalResponse(BaseResponse, threading.local):
    ''' A thread-local subclass of :class:`BaseResponse`. '''
    bind = BaseResponse.__init__

Response = LocalResponse # BC 0.9
Request  = LocalRequest  # BC 0.9






###############################################################################
# Plugins ######################################################################
###############################################################################

class PluginError(BottleException): pass

class JSONPlugin(object):
    name = 'json'
    api  = 2

    def __init__(self, json_dumps=json_dumps):
        self.json_dumps = json_dumps

    def apply(self, callback, context):
        dumps = self.json_dumps
        if not dumps: return callback
        def wrapper(*a, **ka):
            rv = callback(*a, **ka)
            if isinstance(rv, dict):
                #Attempt to serialize, raises exception on failure
                json_response = dumps(rv)
                #Set content type only if serialization succesful
                response.content_type = 'application/json'
                return json_response
            return rv
        return wrapper


class HooksPlugin(object):
    name = 'hooks'
    api  = 2

    _names = 'before_request', 'after_request', 'app_reset'

    def __init__(self):
        self.hooks = dict((name, []) for name in self._names)
        self.app = None

    def _empty(self):
        return not (self.hooks['before_request'] or self.hooks['after_request'])

    def setup(self, app):
        self.app = app

    def add(self, name, func):
        ''' Attach a callback to a hook. '''
        was_empty = self._empty()
        self.hooks.setdefault(name, []).append(func)
        if self.app and was_empty and not self._empty(): self.app.reset()

    def remove(self, name, func):
        ''' Remove a callback from a hook. '''
        was_empty = self._empty()
        if name in self.hooks and func in self.hooks[name]:
            self.hooks[name].remove(func)
        if self.app and not was_empty and self._empty(): self.app.reset()

    def trigger(self, name, *a, **ka):
        ''' Trigger a hook and return a list of results. '''
        hooks = self.hooks[name]
        if ka.pop('reversed', False): hooks = hooks[::-1]
        return [hook(*a, **ka) for hook in hooks]

    def apply(self, callback, context):
        if self._empty(): return callback
        def wrapper(*a, **ka):
            self.trigger('before_request')
            rv = callback(*a, **ka)
            self.trigger('after_request', reversed=True)
            return rv
        return wrapper


class TemplatePlugin(object):
    ''' This plugin applies the :func:`view` decorator to all routes with a
        `template` config parameter. If the parameter is a tuple, the second
        element must be a dict with additional options (e.g. `template_engine`)
        or default variables for the template. '''
    name = 'template'
    api  = 2

    def apply(self, callback, route):
        conf = route.config.get('template')
        if isinstance(conf, (tuple, list)) and len(conf) == 2:
            return view(conf[0], **conf[1])(callback)
        elif isinstance(conf, str) and 'template_opts' in route.config:
            depr('The `template_opts` parameter is deprecated.') #0.9
            return view(conf, **route.config['template_opts'])(callback)
        elif isinstance(conf, str):
            return view(conf)(callback)
        else:
            return callback


#: Not a plugin, but part of the plugin API. TODO: Find a better place.
class _ImportRedirect(object):
    def __init__(self, name, impmask):
        ''' Create a virtual package that redirects imports (see PEP 302). '''
        self.name = name
        self.impmask = impmask
        self.module = sys.modules.setdefault(name, imp.new_module(name))
        self.module.__dict__.update({'__file__': __file__, '__path__': [],
                                    '__all__': [], '__loader__': self})
        sys.meta_path.append(self)

    def find_module(self, fullname, path=None):
        if '.' not in fullname: return
        packname, modname = fullname.rsplit('.', 1)
        if packname != self.name: return
        return self

    def load_module(self, fullname):
        if fullname in sys.modules: return sys.modules[fullname]
        packname, modname = fullname.rsplit('.', 1)
        realname = self.impmask % modname
        __import__(realname)
        module = sys.modules[fullname] = sys.modules[realname]
        setattr(self.module, modname, module)
        module.__loader__ = self
        return module






###############################################################################
# Common Utilities #############################################################
###############################################################################


class MultiDict(DictMixin):
    """ This dict stores multiple values per key, but behaves exactly like a
        normal dict in that it returns only the newest value for any given key.
        There are special methods available to access the full list of values.
    """

    def __init__(self, *a, **k):
        self.dict = dict((k, [v]) for k, v in dict(*a, **k).iteritems())
    def __len__(self): return len(self.dict)
    def __iter__(self): return iter(self.dict)
    def __contains__(self, key): return key in self.dict
    def __delitem__(self, key): del self.dict[key]
    def __getitem__(self, key): return self.dict[key][-1]
    def __setitem__(self, key, value): self.append(key, value)
    def iterkeys(self): return self.dict.iterkeys()
    def itervalues(self): return (v[-1] for v in self.dict.itervalues())
    def iteritems(self): return ((k, v[-1]) for (k, v) in self.dict.iteritems())
    def iterallitems(self):
        for key, values in self.dict.iteritems():
            for value in values:
                yield key, value

    # 2to3 is not able to fix these automatically.
    keys     = iterkeys     if py3k else lambda self: list(self.iterkeys())
    values   = itervalues   if py3k else lambda self: list(self.itervalues())
    items    = iteritems    if py3k else lambda self: list(self.iteritems())
    allitems = iterallitems if py3k else lambda self: list(self.iterallitems())

    def get(self, key, default=None, index=-1, type=None):
        ''' Return the most recent value for a key.

            :param default: The default value to be returned if the key is not
                   present or the type conversion fails.
            :param index: An index for the list of available values.
            :param type: If defined, this callable is used to cast the value
                    into a specific type. Exception are suppressed and result in
                    the default value to be returned.
        '''
        try:
            val = self.dict[key][index]
            return type(val) if type else val
        except Exception, e:
            pass
        return default

    def append(self, key, value):
        ''' Add a new value to the list of values for this key. '''
        self.dict.setdefault(key, []).append(value)

    def replace(self, key, value):
        ''' Replace the list of values with a single value. '''
        self.dict[key] = [value]

    def getall(self, key):
        ''' Return a (possibly empty) list of values for a key. '''
        return self.dict.get(key) or []

    #: Aliases for WTForms to mimic other multi-dict APIs (Django)
    getone = get
    getlist = getall



class FormsDict(MultiDict):
    ''' This :class:`MultiDict` subclass is used to store request form data.
        Additionally to the normal dict-like item access methods (which return
        unmodified data as native strings), this container also supports
        attribute-like access to its values. Attribues are automatiically de- or
        recoded to match :attr:`input_encoding` (default: 'utf8'). Missing
        attributes default to an empty string. '''

    #: Encoding used for attribute values.
    input_encoding = 'utf8'

    def getunicode(self, name, default=None, encoding=None):
        value, enc = self.get(name, default), encoding or self.input_encoding
        try:
            if isinstance(value, bytes): # Python 2 WSGI
                return value.decode(enc)
            elif isinstance(value, unicode): # Python 3 WSGI
                return value.encode('latin1').decode(enc)
            return value
        except UnicodeError, e:
            return default

    def __getattr__(self, name): return self.getunicode(name, default=u'')


class HeaderDict(MultiDict):
    """ A case-insensitive version of :class:`MultiDict` that defaults to
        replace the old value instead of appending it. """

    def __init__(self, *a, **ka):
        self.dict = {}
        if a or ka: self.update(*a, **ka)

    def __contains__(self, key): return _hkey(key) in self.dict
    def __delitem__(self, key): del self.dict[_hkey(key)]
    def __getitem__(self, key): return self.dict[_hkey(key)][-1]
    def __setitem__(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def append(self, key, value):
        self.dict.setdefault(_hkey(key), []).append(str(value))
    def replace(self, key, value): self.dict[_hkey(key)] = [str(value)]
    def getall(self, key): return self.dict.get(_hkey(key)) or []
    def get(self, key, default=None, index=-1):
        return MultiDict.get(self, _hkey(key), default, index)
    def filter(self, names):
        for name in map(_hkey, names):
            if name in self.dict:
                del self.dict[name]


class WSGIHeaderDict(DictMixin):
    ''' This dict-like class wraps a WSGI environ dict and provides convenient
        access to HTTP_* fields. Keys and values are native strings
        (2.x bytes or 3.x unicode) and keys are case-insensitive. If the WSGI
        environment contains non-native string values, these are de- or encoded
        using a lossless 'latin1' character set.

        The API will remain stable even on changes to the relevant PEPs.
        Currently PEP 333, 444 and 3333 are supported. (PEP 444 is the only one
        that uses non-native strings.)
    '''
    #: List of keys that do not have a 'HTTP_' prefix.
    cgikeys = ('CONTENT_TYPE', 'CONTENT_LENGTH')

    def __init__(self, environ):
        self.environ = environ

    def _ekey(self, key):
        ''' Translate header field name to CGI/WSGI environ key. '''
        key = key.replace('-','_').upper()
        if key in self.cgikeys:
            return key
        return 'HTTP_' + key

    def raw(self, key, default=None):
        ''' Return the header value as is (may be bytes or unicode). '''
        return self.environ.get(self._ekey(key), default)

    def __getitem__(self, key):
        return tonat(self.environ[self._ekey(key)], 'latin1')

    def __setitem__(self, key, value):
        raise TypeError("%s is read-only." % self.__class__)

    def __delitem__(self, key):
        raise TypeError("%s is read-only." % self.__class__)

    def __iter__(self):
        for key in self.environ:
            if key[:5] == 'HTTP_':
                yield key[5:].replace('_', '-').title()
            elif key in self.cgikeys:
                yield key.replace('_', '-').title()

    def keys(self): return [x for x in self]
    def __len__(self): return len(self.keys())
    def __contains__(self, key): return self._ekey(key) in self.environ


class ConfigDict(dict):
    ''' A dict-subclass with some extras: You can access keys like attributes.
        Uppercase attributes create new ConfigDicts and act as name-spaces.
        Other missing attributes return None. Calling a ConfigDict updates its
        values and returns itself.

        >>> cfg = ConfigDict()
        >>> cfg.Namespace.value = 5
        >>> cfg.OtherNamespace(a=1, b=2)
        >>> cfg
        {'Namespace': {'value': 5}, 'OtherNamespace': {'a': 1, 'b': 2}}
    '''

    def __getattr__(self, key):
        if key not in self and key[0].isupper():
            self[key] = ConfigDict()
        return self.get(key)

    def __setattr__(self, key, value):
        if hasattr(dict, key):
            raise AttributeError('Read-only attribute.')
        if key in self and self[key] and isinstance(self[key], ConfigDict):
            raise AttributeError('Non-empty namespace attribute.')
        self[key] = value

    def __delattr__(self, key):
        if key in self: del self[key]

    def __call__(self, *a, **ka):
        for key, value in dict(*a, **ka).iteritems(): setattr(self, key, value)
        return self


class AppStack(list):
    """ A stack-like list. Calling it returns the head of the stack. """

    def __call__(self):
        """ Return the current default application. """
        return self[-1]

    def push(self, value=None):
        """ Add a new :class:`Bottle` instance to the stack """
        if not isinstance(value, Bottle):
            value = Bottle()
        self.append(value)
        return value


class WSGIFileWrapper(object):

   def __init__(self, fp, buffer_size=1024*64):
       self.fp, self.buffer_size = fp, buffer_size
       for attr in ('fileno', 'close', 'read', 'readlines'):
           if hasattr(fp, attr): setattr(self, attr, getattr(fp, attr))

   def __iter__(self):
       read, buff = self.fp.read, self.buffer_size
       while True:
           part = read(buff)
           if not part: break
           yield part






###############################################################################
# Application Helper ###########################################################
###############################################################################


def abort(code=500, text='Unknown Error: Application stopped.'):
    """ Aborts execution and causes a HTTP error. """
    raise HTTPError(code, text)


def redirect(url, code=None):
    """ Aborts execution and causes a 303 or 302 redirect, depending on
        the HTTP protocol version. """
    if code is None:
        code = 303 if request.get('SERVER_PROTOCOL') == "HTTP/1.1" else 302
    location = urljoin(request.url, url)
    raise HTTPResponse("", status=code, header=dict(Location=location))


def static_file(filename, root, mimetype='auto', download=False):
    """ Open a file in a safe way and return :exc:`HTTPResponse` with status
        code 200, 305, 401 or 404. Set Content-Type, Content-Encoding,
        Content-Length and Last-Modified header. Obey If-Modified-Since header
        and HEAD requests.
    """
    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip('/\\')))
    header = dict()

    if not filename.startswith(root):
        return HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        return HTTPError(403, "You do not have permission to access this file.")

    if mimetype == 'auto':
        mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype: header['Content-Type'] = mimetype
        if encoding: header['Content-Encoding'] = encoding
    elif mimetype:
        header['Content-Type'] = mimetype

    if download:
        download = os.path.basename(filename if download == True else download)
        header['Content-Disposition'] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    header['Content-Length'] = stats.st_size
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    header['Last-Modified'] = lm

    ims = request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        header['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return HTTPResponse(status=304, header=header)

    body = '' if request.method == 'HEAD' else open(filename, 'rb')
    return HTTPResponse(body, header=header)






###############################################################################
# HTTP Utilities and MISC (TODO) ###############################################
###############################################################################


def debug(mode=True):
    """ Change the debug level.
    There is only one debug level supported at the moment."""
    global DEBUG
    DEBUG = bool(mode)


def parse_date(ims):
    """ Parse rfc1123, rfc850 and asctime timestamps and return UTC epoch. """
    try:
        ts = email.utils.parsedate_tz(ims)
        return time.mktime(ts[:8] + (0,)) - (ts[9] or 0) - time.timezone
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def parse_auth(header):
    """ Parse rfc2617 HTTP authentication header string (basic) and return (user,pass) tuple or None"""
    try:
        method, data = header.split(None, 1)
        if method.lower() == 'basic':
            #TODO: Add 2to3 save base64[encode/decode] functions.
            user, pwd = touni(base64.b64decode(tob(data))).split(':',1)
            return user, pwd
    except (KeyError, ValueError):
        return None


def _lscmp(a, b):
    ''' Compares two strings in a cryptographically save way:
        Runtime is not affected by length of common prefix. '''
    return not sum(0 if x==y else 1 for x, y in zip(a, b)) and len(a) == len(b)


def cookie_encode(data, key):
    ''' Encode and sign a pickle-able object. Return a (byte) string '''
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(tob(key), msg).digest())
    return tob('!') + sig + tob('?') + msg


def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = tob(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(tob('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(tob(key), msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(tob('!')) and tob('?') in data)


def html_escape(string):
    ''' Escape HTML special characters ``&<>`` and quotes ``'"``. '''
    return string.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')\
                 .replace('"','&quot;').replace("'",'&#039;')


def html_quote(string):
    ''' Escape and quote a string to be used as an HTTP attribute.'''
    return '"%s"' % html_escape(string).replace('\n','%#10;')\
                    .replace('\r','&#13;').replace('\t','&#9;')


def yieldroutes(func):
    """ Return a generator for routes that match the signature (name, args)
    of the func parameter. This may yield more than one route if the function
    takes optional keyword arguments. The output is best described by example::

        a()         -> '/a'
        b(x, y)     -> '/b/:x/:y'
        c(x, y=5)   -> '/c/:x' and '/c/:x/:y'
        d(x=5, y=6) -> '/d' and '/d/:x' and '/d/:x/:y'
    """
    import inspect # Expensive module. Only import if necessary.
    path = '/' + func.__name__.replace('__','/').lstrip('/')
    spec = inspect.getargspec(func)
    argc = len(spec[0]) - len(spec[3] or [])
    path += ('/:%s' * argc) % tuple(spec[0][:argc])
    yield path
    for arg in spec[0][argc:]:
        path += '/:%s' % arg
        yield path


def path_shift(script_name, path_info, shift=1):
    ''' Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

        :return: The modified paths.
        :param script_name: The SCRIPT_NAME path.
        :param script_name: The PATH_INFO path.
        :param shift: The number of path fragments to shift. May be negative to
          change the shift direction. (default: 1)
    '''
    if shift == 0: return script_name, path_info
    pathlist = path_info.strip('/').split('/')
    scriptlist = script_name.strip('/').split('/')
    if pathlist and pathlist[0] == '': pathlist = []
    if scriptlist and scriptlist[0] == '': scriptlist = []
    if shift > 0 and shift <= len(pathlist):
        moved = pathlist[:shift]
        scriptlist = scriptlist + moved
        pathlist = pathlist[shift:]
    elif shift < 0 and shift >= -len(scriptlist):
        moved = scriptlist[shift:]
        pathlist = moved + pathlist
        scriptlist = scriptlist[:shift]
    else:
        empty = 'SCRIPT_NAME' if shift < 0 else 'PATH_INFO'
        raise AssertionError("Cannot shift. Nothing left from %s" % empty)
    new_script_name = '/' + '/'.join(scriptlist)
    new_path_info = '/' + '/'.join(pathlist)
    if path_info.endswith('/') and pathlist: new_path_info += '/'
    return new_script_name, new_path_info


def validate(**vkargs):
    """
    Validates and manipulates keyword arguments by user defined callables.
    Handles ValueError and missing arguments by raising HTTPError(403).
    """
    depr('Use route wildcard filters instead.')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kargs):
            for key, value in vkargs.iteritems():
                if key not in kargs:
                    abort(403, 'Missing parameter: %s' % key)
                try:
                    kargs[key] = value(kargs[key])
                except ValueError:
                    abort(403, 'Wrong parameter format for: %s' % key)
            return func(*args, **kargs)
        return wrapper
    return decorator


def auth_basic(check, realm="private", text="Access denied"):
    ''' Callback decorator to require HTTP auth (basic).
        TODO: Add route(check_auth=...) parameter. '''
    def decorator(func):
      def wrapper(*a, **ka):
        user, password = request.auth or (None, None)
        if user is None or not check(user, password):
          response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % realm
          return HTTPError(401, text)
        return func(*a, **ka)
      return wrapper
    return decorator


def make_default_app_wrapper(name):
    ''' Return a callable that relays calls to the current default app. '''
    @functools.wraps(getattr(Bottle, name))
    def wrapper(*a, **ka):
        return getattr(app(), name)(*a, **ka)
    return wrapper


for name in '''route get post put delete error mount
               hook install uninstall'''.split():
    globals()[name] = make_default_app_wrapper(name)
url = make_default_app_wrapper('get_url')
del name






###############################################################################
# Server Adapter ###############################################################
###############################################################################


class ServerAdapter(object):
    quiet = False
    def __init__(self, host='127.0.0.1', port=8080, **config):
        self.options = config
        self.host = host
        self.port = int(port)

    def run(self, handler): # pragma: no cover
        pass

    def __repr__(self):
        args = ', '.join(['%s=%s'%(k,repr(v)) for k, v in self.options.items()])
        return "%s(%s)" % (self.__class__.__name__, args)


class CGIServer(ServerAdapter):
    quiet = True
    def run(self, handler): # pragma: no cover
        from wsgiref.handlers import CGIHandler
        def fixed_environ(environ, start_response):
            environ.setdefault('PATH_INFO', '')
            return handler(environ, start_response)
        CGIHandler().run(fixed_environ)


class FlupFCGIServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        import flup.server.fcgi
        self.options.setdefault('bindAddress', (self.host, self.port))
        flup.server.fcgi.WSGIServer(handler, **self.options).run()


class WSGIRefServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.serve_forever()


class CherryPyServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cherrypy import wsgiserver
        server = wsgiserver.CherryPyWSGIServer((self.host, self.port), handler)
        try:
            server.start()
        finally:
            server.stop()


class PasteServer(ServerAdapter):
    def run(self, handler): # pragma: no cover
        from paste import httpserver
        if not self.quiet:
            from paste.translogger import TransLogger
            handler = TransLogger(handler)
        httpserver.serve(handler, host=self.host, port=str(self.port),
                         **self.options)


class MeinheldServer(ServerAdapter):
    def run(self, handler):
        from meinheld import server
        server.listen((self.host, self.port))
        server.run(handler)


class FapwsServer(ServerAdapter):
    """ Extremely fast webserver using libev. See http://www.fapws.org/ """
    def run(self, handler): # pragma: no cover
        import fapws._evwsgi as evwsgi
        from fapws import base, config
        port = self.port
        if float(config.SERVER_IDENT[-2:]) > 0.4:
            # fapws3 silently changed its API in 0.5
            port = str(port)
        evwsgi.start(self.host, port)
        # fapws3 never releases the GIL. Complain upstream. I tried. No luck.
        if 'BOTTLE_CHILD' in os.environ and not self.quiet:
            print "WARNING: Auto-reloading does not work with Fapws3."
            print "         (Fapws3 breaks python thread support)"
        evwsgi.set_base_module(base)
        def app(environ, start_response):
            environ['wsgi.multiprocess'] = False
            return handler(environ, start_response)
        evwsgi.wsgi_cb(('', app))
        evwsgi.run()


class TornadoServer(ServerAdapter):
    """ The super hyped asynchronous server by facebook. Untested. """
    def run(self, handler): # pragma: no cover
        import tornado.wsgi, tornado.httpserver, tornado.ioloop
        container = tornado.wsgi.WSGIContainer(handler)
        server = tornado.httpserver.HTTPServer(container)
        server.listen(port=self.port)
        tornado.ioloop.IOLoop.instance().start()


class AppEngineServer(ServerAdapter):
    """ Adapter for Google App Engine. """
    quiet = True
    def run(self, handler):
        from google.appengine.ext.webapp import util
        # A main() function in the handler script enables 'App Caching'.
        # Lets makes sure it is there. This _really_ improves performance.
        module = sys.modules.get('__main__')
        if module and not hasattr(module, 'main'):
            module.main = lambda: util.run_wsgi_app(handler)
        util.run_wsgi_app(handler)


class TwistedServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from twisted.web import server, wsgi
        from twisted.python.threadpool import ThreadPool
        from twisted.internet import reactor
        thread_pool = ThreadPool()
        thread_pool.start()
        reactor.addSystemEventTrigger('after', 'shutdown', thread_pool.stop)
        factory = server.Site(wsgi.WSGIResource(reactor, thread_pool, handler))
        reactor.listenTCP(self.port, factory, interface=self.host)
        reactor.run()


class DieselServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from diesel.protocols.wsgi import WSGIApplication
        app = WSGIApplication(handler, port=self.port)
        app.run()


class GeventServer(ServerAdapter):
    """ Untested. Options:

        * `monkey` (default: True) fixes the stdlib to use greenthreads.
        * `fast` (default: False) uses libevent's http server, but has some
          issues: No streaming, no pipelining, no SSL.
    """
    def run(self, handler):
        from gevent import wsgi as wsgi_fast, pywsgi, monkey, local
        if self.options.get('monkey', True):
            if not threading.local is local.local: monkey.patch_all()
        wsgi = wsgi_fast if self.options.get('fast') else pywsgi
        wsgi.WSGIServer((self.host, self.port), handler).serve_forever()


class GunicornServer(ServerAdapter):
    """ Untested. See http://gunicorn.org/configure.html for options. """
    def run(self, handler):
        from gunicorn.app.base import Application

        config = {'bind': "%s:%d" % (self.host, int(self.port))}
        config.update(self.options)

        class GunicornApplication(Application):
            def init(self, parser, opts, args):
                return config

            def load(self):
                return handler

        GunicornApplication().run()


class EventletServer(ServerAdapter):
    """ Untested """
    def run(self, handler):
        from eventlet import wsgi, listen
        wsgi.server(listen((self.host, self.port)), handler)


class RocketServer(ServerAdapter):
    """ Untested. """
    def run(self, handler):
        from rocket import Rocket
        server = Rocket((self.host, self.port), 'wsgi', { 'wsgi_app' : handler })
        server.start()


class BjoernServer(ServerAdapter):
    """ Fast server written in C: https://github.com/jonashaag/bjoern """
    def run(self, handler):
        from bjoern import run
        run(handler, self.host, self.port)


class AutoServer(ServerAdapter):
    """ Untested. """
    adapters = [PasteServer, CherryPyServer, TwistedServer, WSGIRefServer]
    def run(self, handler):
        for sa in self.adapters:
            try:
                return sa(self.host, self.port, **self.options).run(handler)
            except ImportError:
                pass

server_names = {
    'cgi': CGIServer,
    'flup': FlupFCGIServer,
    'wsgiref': WSGIRefServer,
    'cherrypy': CherryPyServer,
    'paste': PasteServer,
    'fapws3': FapwsServer,
    'tornado': TornadoServer,
    'gae': AppEngineServer,
    'twisted': TwistedServer,
    'diesel': DieselServer,
    'meinheld': MeinheldServer,
    'gunicorn': GunicornServer,
    'eventlet': EventletServer,
    'gevent': GeventServer,
    'rocket': RocketServer,
    'bjoern' : BjoernServer,
    'auto': AutoServer,
}






###############################################################################
# Application Control ##########################################################
###############################################################################


def load(target, **namespace):
    """ Import a module or fetch an object from a module.

        * ``package.module`` returns `module` as a module object.
        * ``pack.mod:name`` returns the module variable `name` from `pack.mod`.
        * ``pack.mod:func()`` calls `pack.mod.func()` and returns the result.

        The last form accepts not only function calls, but any type of
        expression. Keyword arguments passed to this function are available as
        local variables. Example: ``import_string('re:compile(x)', x='[a-z]')``
    """
    module, target = target.split(":", 1) if ':' in target else (target, None)
    if module not in sys.modules: __import__(module)
    if not target: return sys.modules[module]
    if target.isalnum(): return getattr(sys.modules[module], target)
    package_name = module.split('.')[0]
    namespace[package_name] = sys.modules[package_name]
    return eval('%s.%s' % (module, target), namespace)


def load_app(target):
    """ Load a bottle application from a module and make sure that the import
        does not affect the current default application, but returns a separate
        application object. See :func:`load` for the target parameter. """
    global NORUN; NORUN, nr_old = True, NORUN
    try:
        tmp = default_app.push() # Create a new "default application"
        rv = load(target) # Import the target module
        return rv if callable(rv) else tmp
    finally:
        default_app.remove(tmp) # Remove the temporary added default application
        NORUN = nr_old

def run(app=None, server='wsgiref', host='127.0.0.1', port=8080,
        interval=1, reloader=False, quiet=False, plugins=None, **kargs):
    """ Start a server instance. This method blocks until the server terminates.

        :param app: WSGI application or target string supported by
               :func:`load_app`. (default: :func:`default_app`)
        :param server: Server adapter to use. See :data:`server_names` keys
               for valid names or pass a :class:`ServerAdapter` subclass.
               (default: `wsgiref`)
        :param host: Server address to bind to. Pass ``0.0.0.0`` to listens on
               all interfaces including the external one. (default: 127.0.0.1)
        :param port: Server port to bind to. Values below 1024 require root
               privileges. (default: 8080)
        :param reloader: Start auto-reloading server? (default: False)
        :param interval: Auto-reloader interval in seconds (default: 1)
        :param quiet: Suppress output to stdout and stderr? (default: False)
        :param options: Options passed to the server adapter.
     """
    if NORUN: return
    if reloader and not os.environ.get('BOTTLE_CHILD'):
        try:
            fd, lockfile = tempfile.mkstemp(prefix='bottle.', suffix='.lock')
            os.close(fd) # We only need this file to exist. We never write to it
            while os.path.exists(lockfile):
                args = [sys.executable] + sys.argv
                environ = os.environ.copy()
                environ['BOTTLE_CHILD'] = 'true'
                environ['BOTTLE_LOCKFILE'] = lockfile
                p = subprocess.Popen(args, env=environ)
                while p.poll() is None: # Busy wait...
                    os.utime(lockfile, None) # I am alive!
                    time.sleep(interval)
                if p.poll() != 3:
                    if os.path.exists(lockfile): os.unlink(lockfile)
                    sys.exit(p.poll())
        except KeyboardInterrupt:
            pass
        finally:
            if os.path.exists(lockfile):
                os.unlink(lockfile)
        return

    stderr = sys.stderr.write

    try:
        app = app or default_app()
        if isinstance(app, basestring):
            app = load_app(app)
        if not callable(app):
            raise ValueError("Application is not callable: %r" % app)

        for plugin in plugins or []:
            app.install(plugin)

        if server in server_names:
            server = server_names.get(server)
        if isinstance(server, basestring):
            server = load(server)
        if isinstance(server, type):
            server = server(host=host, port=port, **kargs)
        if not isinstance(server, ServerAdapter):
            raise ValueError("Unknown or unsupported server: %r" % server)

        server.quiet = server.quiet or quiet
        if not server.quiet:
            stderr("Bottle server starting up (using %s)...\n" % repr(server))
            stderr("Listening on http://%s:%d/\n" % (server.host, server.port))
            stderr("Hit Ctrl-C to quit.\n\n")

        if reloader:
            lockfile = os.environ.get('BOTTLE_LOCKFILE')
            bgcheck = FileCheckerThread(lockfile, interval)
            with bgcheck:
                server.run(app)
            if bgcheck.status == 'reload':
                sys.exit(3)
        else:
            server.run(app)
    except KeyboardInterrupt:
        pass
    except (SyntaxError, ImportError):
        if not reloader: raise
        if not getattr(server, 'quiet', False): print_exc()
        sys.exit(3)
    finally:
        if not getattr(server, 'quiet', False): stderr('Shutdown...\n')


class FileCheckerThread(threading.Thread):
    ''' Interrupt main-thread as soon as a changed module file is detected,
        the lockfile gets deleted or gets to old. '''

    def __init__(self, lockfile, interval):
        threading.Thread.__init__(self)
        self.lockfile, self.interval = lockfile, interval
        #: Is one of 'reload', 'error' or 'exit'
        self.status = None

    def run(self):
        exists = os.path.exists
        mtime = lambda path: os.stat(path).st_mtime
        files = dict()

        for module in sys.modules.values():
            path = getattr(module, '__file__', '')
            if path[-4:] in ('.pyo', '.pyc'): path = path[:-1]
            if path and exists(path): files[path] = mtime(path)

        while not self.status:
            if not exists(self.lockfile)\
            or mtime(self.lockfile) < time.time() - self.interval - 5:
                self.status = 'error'
                thread.interrupt_main()
            for path, lmtime in files.iteritems():
                if not exists(path) or mtime(path) > lmtime:
                    self.status = 'reload'
                    thread.interrupt_main()
                    break
            time.sleep(self.interval)
    
    def __enter__(self):
        self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.status: self.status = 'exit' # silent exit
        self.join()
        return issubclass(exc_type, KeyboardInterrupt)





###############################################################################
# Template Adapters ############################################################
###############################################################################


class TemplateError(HTTPError):
    def __init__(self, message):
        HTTPError.__init__(self, 500, message)


class BaseTemplate(object):
    """ Base class and minimal API for template adapters """
    extensions = ['tpl','html','thtml','stpl']
    settings = {} #used in prepare()
    defaults = {} #used in render()

    def __init__(self, source=None, name=None, lookup=[], encoding='utf8', **settings):
        """ Create a new template.
        If the source parameter (str or buffer) is missing, the name argument
        is used to guess a template filename. Subclasses can assume that
        self.source and/or self.filename are set. Both are strings.
        The lookup, encoding and settings parameters are stored as instance
        variables.
        The lookup parameter stores a list containing directory paths.
        The encoding parameter should be used to decode byte strings or files.
        The settings parameter contains a dict for engine-specific settings.
        """
        self.name = name
        self.source = source.read() if hasattr(source, 'read') else source
        self.filename = source.filename if hasattr(source, 'filename') else None
        self.lookup = map(os.path.abspath, lookup)
        self.encoding = encoding
        self.settings = self.settings.copy() # Copy from class variable
        self.settings.update(settings) # Apply
        if not self.source and self.name:
            self.filename = self.search(self.name, self.lookup)
            if not self.filename:
                raise TemplateError('Template %s not found.' % repr(name))
        if not self.source and not self.filename:
            raise TemplateError('No template specified.')
        self.prepare(**self.settings)

    @classmethod
    def search(cls, name, lookup=[]):
        """ Search name in all directories specified in lookup.
        First without, then with common extensions. Return first hit. """
        if os.path.isfile(name): return name
        for spath in lookup:
            fname = os.path.join(spath, name)
            if os.path.isfile(fname):
                return fname
            for ext in cls.extensions:
                if os.path.isfile('%s.%s' % (fname, ext)):
                    return '%s.%s' % (fname, ext)

    @classmethod
    def global_config(cls, key, *args):
        ''' This reads or sets the global settings stored in class.settings. '''
        if args:
            cls.settings = cls.settings.copy() # Make settings local to class
            cls.settings[key] = args[0]
        else:
            return cls.settings[key]

    def prepare(self, **options):
        """ Run preparations (parsing, caching, ...).
        It should be possible to call this again to refresh a template or to
        update settings.
        """
        raise NotImplementedError

    def render(self, *args, **kwargs):
        """ Render the template with the specified local variables and return
        a single byte or unicode string. If it is a byte string, the encoding
        must match self.encoding. This method must be thread-safe!
        Local variables may be provided in dictionaries (*args)
        or directly, as keywords (**kwargs).
        """
        raise NotImplementedError


class MakoTemplate(BaseTemplate):
    def prepare(self, **options):
        from mako.template import Template
        from mako.lookup import TemplateLookup
        options.update({'input_encoding':self.encoding})
        options.setdefault('format_exceptions', bool(DEBUG))
        lookup = TemplateLookup(directories=self.lookup, **options)
        if self.source:
            self.tpl = Template(self.source, lookup=lookup, **options)
        else:
            self.tpl = Template(uri=self.name, filename=self.filename, lookup=lookup, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)


class CheetahTemplate(BaseTemplate):
    def prepare(self, **options):
        from Cheetah.Template import Template
        self.context = threading.local()
        self.context.vars = {}
        options['searchList'] = [self.context.vars]
        if self.source:
            self.tpl = Template(source=self.source, **options)
        else:
            self.tpl = Template(file=self.filename, **options)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        self.context.vars.update(self.defaults)
        self.context.vars.update(kwargs)
        out = str(self.tpl)
        self.context.vars.clear()
        return out


class Jinja2Template(BaseTemplate):
    def prepare(self, filters=None, tests=None, **kwargs):
        from jinja2 import Environment, FunctionLoader
        if 'prefix' in kwargs: # TODO: to be removed after a while
            raise RuntimeError('The keyword argument `prefix` has been removed. '
                'Use the full jinja2 environment name line_statement_prefix instead.')
        self.env = Environment(loader=FunctionLoader(self.loader), **kwargs)
        if filters: self.env.filters.update(filters)
        if tests: self.env.tests.update(tests)
        if self.source:
            self.tpl = self.env.from_string(self.source)
        else:
            self.tpl = self.env.get_template(self.filename)

    def render(self, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        _defaults = self.defaults.copy()
        _defaults.update(kwargs)
        return self.tpl.render(**_defaults)

    def loader(self, name):
        fname = self.search(name, self.lookup)
        if fname:
            with open(fname, "rb") as f:
                return f.read().decode(self.encoding)


class SimpleTALTemplate(BaseTemplate):
    ''' Untested! '''
    def prepare(self, **options):
        from simpletal import simpleTAL
        # TODO: add option to load METAL files during render
        if self.source:
            self.tpl = simpleTAL.compileHTMLTemplate(self.source)
        else:
            with open(self.filename, 'rb') as fp:
                self.tpl = simpleTAL.compileHTMLTemplate(tonat(fp.read()))

    def render(self, *args, **kwargs):
        from simpletal import simpleTALES
        for dictarg in args: kwargs.update(dictarg)
        # TODO: maybe reuse a context instead of always creating one
        context = simpleTALES.Context()
        for k,v in self.defaults.items():
            context.addGlobal(k, v)
        for k,v in kwargs.items():
            context.addGlobal(k, v)
        output = StringIO()
        self.tpl.expand(context, output)
        return output.getvalue()


class SimpleTemplate(BaseTemplate):
    blocks = ('if', 'elif', 'else', 'try', 'except', 'finally', 'for', 'while',
              'with', 'def', 'class')
    dedent_blocks = ('elif', 'else', 'except', 'finally')

    @lazy_attribute
    def re_pytokens(cls):
        ''' This matches comments and all kinds of quoted strings but does
            NOT match comments (#...) within quoted strings. (trust me) '''
        return re.compile(r'''
            (''(?!')|""(?!")|'{6}|"{6}    # Empty strings (all 4 types)
             |'(?:[^\\']|\\.)+?'          # Single quotes (')
             |"(?:[^\\"]|\\.)+?"          # Double quotes (")
             |'{3}(?:[^\\]|\\.|\n)+?'{3}  # Triple-quoted strings (')
             |"{3}(?:[^\\]|\\.|\n)+?"{3}  # Triple-quoted strings (")
             |\#.*                        # Comments
            )''', re.VERBOSE)

    def prepare(self, escape_func=html_escape, noescape=False, **kwargs):
        self.cache = {}
        enc = self.encoding
        self._str = lambda x: touni(x, enc)
        self._escape = lambda x: escape_func(touni(x, enc))
        if noescape:
            self._str, self._escape = self._escape, self._str

    @classmethod
    def split_comment(cls, code):
        """ Removes comments (#...) from python code. """
        if '#' not in code: return code
        #: Remove comments only (leave quoted strings as they are)
        subf = lambda m: '' if m.group(0)[0]=='#' else m.group(0)
        return re.sub(cls.re_pytokens, subf, code)

    @cached_property
    def co(self):
        return compile(self.code, self.filename or '<string>', 'exec')

    @cached_property
    def code(self):
        stack = [] # Current Code indentation
        lineno = 0 # Current line of code
        ptrbuffer = [] # Buffer for printable strings and token tuple instances
        codebuffer = [] # Buffer for generated python code
        multiline = dedent = oneline = False
        template = self.source or open(self.filename, 'rb').read()

        def yield_tokens(line):
            for i, part in enumerate(re.split(r'\{\{(.*?)\}\}', line)):
                if i % 2:
                    if part.startswith('!'): yield 'RAW', part[1:]
                    else: yield 'CMD', part
                else: yield 'TXT', part

        def flush(): # Flush the ptrbuffer
            if not ptrbuffer: return
            cline = ''
            for line in ptrbuffer:
                for token, value in line:
                    if token == 'TXT': cline += repr(value)
                    elif token == 'RAW': cline += '_str(%s)' % value
                    elif token == 'CMD': cline += '_escape(%s)' % value
                    cline +=  ', '
                cline = cline[:-2] + '\\\n'
            cline = cline[:-2]
            if cline[:-1].endswith('\\\\\\\\\\n'):
                cline = cline[:-7] + cline[-1] # 'nobr\\\\\n' --> 'nobr'
            cline = '_printlist([' + cline + '])'
            del ptrbuffer[:] # Do this before calling code() again
            code(cline)

        def code(stmt):
            for line in stmt.splitlines():
                codebuffer.append('  ' * len(stack) + line.strip())

        for line in template.splitlines(True):
            lineno += 1
            line = line if isinstance(line, unicode)\
                        else unicode(line, encoding=self.encoding)
            sline = line.lstrip()
            if lineno <= 2:
                m = re.search(r"%.*coding[:=]\s*([-\w\.]+)", line)
                if m: self.encoding = m.group(1)
                if m: line = line.replace('coding','coding (removed)')
            if sline and sline[0] == '%' and sline[:2] != '%%':
                line = line.split('%',1)[1].lstrip() # Full line following the %
                cline = self.split_comment(line).strip()
                cmd = re.split(r'[^a-zA-Z0-9_]', cline)[0]
                flush() # You are actually reading this? Good luck, it's a mess :)
                if cmd in self.blocks or multiline:
                    cmd = multiline or cmd
                    dedent = cmd in self.dedent_blocks # "else:"
                    if dedent and not oneline and not multiline:
                        cmd = stack.pop()
                    code(line)
                    oneline = not cline.endswith(':') # "if 1: pass"
                    multiline = cmd if cline.endswith('\\') else False
                    if not oneline and not multiline:
                        stack.append(cmd)
                elif cmd == 'end' and stack:
                    code('#end(%s) %s' % (stack.pop(), line.strip()[3:]))
                elif cmd == 'include':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("_=_include(%s, _stdout, %s)" % (repr(p[0]), p[1]))
                    elif p:
                        code("_=_include(%s, _stdout)" % repr(p[0]))
                    else: # Empty %include -> reverse of %rebase
                        code("_printlist(_base)")
                elif cmd == 'rebase':
                    p = cline.split(None, 2)[1:]
                    if len(p) == 2:
                        code("globals()['_rebase']=(%s, dict(%s))" % (repr(p[0]), p[1]))
                    elif p:
                        code("globals()['_rebase']=(%s, {})" % repr(p[0]))
                else:
                    code(line)
            else: # Line starting with text (not '%') or '%%' (escaped)
                if line.strip().startswith('%%'):
                    line = line.replace('%%', '%', 1)
                ptrbuffer.append(yield_tokens(line))
        flush()
        return '\n'.join(codebuffer) + '\n'

    def subtemplate(self, _name, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        if _name not in self.cache:
            self.cache[_name] = self.__class__(name=_name, lookup=self.lookup)
        return self.cache[_name].execute(_stdout, kwargs)

    def execute(self, _stdout, *args, **kwargs):
        for dictarg in args: kwargs.update(dictarg)
        env = self.defaults.copy()
        env.update({'_stdout': _stdout, '_printlist': _stdout.extend,
               '_include': self.subtemplate, '_str': self._str,
               '_escape': self._escape, 'get': env.get,
               'setdefault': env.setdefault, 'defined': env.__contains__})
        env.update(kwargs)
        eval(self.co, env)
        if '_rebase' in env:
            subtpl, rargs = env['_rebase']
            rargs['_base'] = _stdout[:] #copy stdout
            del _stdout[:] # clear stdout
            return self.subtemplate(subtpl,_stdout,rargs)
        return env

    def render(self, *args, **kwargs):
        """ Render the template using keyword arguments as local variables. """
        for dictarg in args: kwargs.update(dictarg)
        stdout = []
        self.execute(stdout, kwargs)
        return ''.join(stdout)


def template(*args, **kwargs):
    '''
    Get a rendered template as a string iterator.
    You can use a name, a filename or a template string as first parameter.
    Template rendering arguments can be passed as dictionaries
    or directly (as keyword arguments).
    '''
    tpl = args[0] if args else None
    template_adapter = kwargs.pop('template_adapter', SimpleTemplate)
    if tpl not in TEMPLATES or DEBUG:
        settings = kwargs.pop('template_settings', {})
        lookup = kwargs.pop('template_lookup', TEMPLATE_PATH)
        if isinstance(tpl, template_adapter):
            TEMPLATES[tpl] = tpl
            if settings: TEMPLATES[tpl].prepare(**settings)
        elif "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
            TEMPLATES[tpl] = template_adapter(source=tpl, lookup=lookup, **settings)
        else:
            TEMPLATES[tpl] = template_adapter(name=tpl, lookup=lookup, **settings)
    if not TEMPLATES[tpl]:
        abort(500, 'Template (%s) not found' % tpl)
    for dictarg in args[1:]: kwargs.update(dictarg)
    return TEMPLATES[tpl].render(kwargs)

mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)
simpletal_template = functools.partial(template, template_adapter=SimpleTALTemplate)


def view(tpl_name, **defaults):
    ''' Decorator: renders a template for a handler.
        The handler can control its behavior like that:

          - return a dict of template vars to fill out the template
          - return something other than a dict and the view decorator will not
            process the template, but return the handler result as is.
            This includes returning a HTTPResponse(dict) to get,
            for instance, JSON with autojson or other castfilters.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (dict, DictMixin)):
                tplvars = defaults.copy()
                tplvars.update(result)
                return template(tpl_name, **tplvars)
            return result
        return wrapper
    return decorator

mako_view = functools.partial(view, template_adapter=MakoTemplate)
cheetah_view = functools.partial(view, template_adapter=CheetahTemplate)
jinja2_view = functools.partial(view, template_adapter=Jinja2Template)
simpletal_view = functools.partial(view, template_adapter=SimpleTALTemplate)






###############################################################################
# Constants and Globals ########################################################
###############################################################################


TEMPLATE_PATH = ['./', './views/']
TEMPLATES = {}
DEBUG = False
NORUN = False # If set, run() does nothing. Used by load_app()

#: A dict to map HTTP status codes (e.g. 404) to phrases (e.g. 'Not Found')
HTTP_CODES = httplib.responses
HTTP_CODES[418] = "I'm a teapot" # RFC 2324
HTTP_CODES[428] = "Precondition Required"
HTTP_CODES[429] = "Too Many Requests"
HTTP_CODES[431] = "Request Header Fields Too Large"
HTTP_CODES[511] = "Network Authentication Required"
_HTTP_STATUS_LINES = dict((k, '%d %s'%(k,v)) for (k,v) in HTTP_CODES.iteritems())

#: The default template used for error pages. Override with @error()
ERROR_PAGE_TEMPLATE = """
%try:
    %from imgfac.rest.bottle import DEBUG, HTTP_CODES, request, touni
    %status_name = HTTP_CODES.get(e.status, 'Unknown').title()
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <html>
        <head>
            <title>Error {{e.status}}: {{status_name}}</title>
            <style type="text/css">
              html {background-color: #eee; font-family: sans;}
              body {background-color: #fff; border: 1px solid #ddd;
                    padding: 15px; margin: 15px;}
              pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}
            </style>
        </head>
        <body>
            <h1>Error {{e.status}}: {{status_name}}</h1>
            <p>Sorry, the requested URL <tt>{{repr(request.url)}}</tt>
               caused an error:</p>
            <pre>{{e.output}}</pre>
            %if DEBUG and e.exception:
              <h2>Exception:</h2>
              <pre>{{repr(e.exception)}}</pre>
            %end
            %if DEBUG and e.traceback:
              <h2>Traceback:</h2>
              <pre>{{e.traceback}}</pre>
            %end
        </body>
    </html>
%except ImportError:
    <b>ImportError:</b> Could not generate the error page. Please add bottle to
    the import path.
%end
"""

#: A thread-safe instance of :class:`Request` representing the `current` request.
request = Request()

#: A thread-safe instance of :class:`Response` used to build the HTTP response.
response = Response()

#: A thread-safe namespace. Not used by Bottle.
local = threading.local()

# Initialize app stack (create first empty Bottle app)
# BC: 0.6.4 and needed for run()
app = default_app = AppStack()
app.push()

#: A virtual package that redirects import statements.
#: Example: ``import bottle.ext.sqlite`` actually imports `bottle_sqlite`.
ext = _ImportRedirect(__name__+'.ext', 'bottle_%s').module

if __name__ == '__main__':
    opt, args, parser = _cmd_options, _cmd_args, _cmd_parser
    if opt.version:
        print 'Bottle', __version__; sys.exit(0)
    if not args:
        parser.print_help()
        print '\nError: No application specified.\n'
        sys.exit(1)

    try:
        sys.path.insert(0, '.')
        sys.modules.setdefault('bottle', sys.modules['__main__'])
    except (AttributeError, ImportError), e:
        parser.error(e.args[0])

    if opt.bind and ':' in opt.bind:
        host, port = opt.bind.rsplit(':', 1)
    else:
        host, port = (opt.bind or 'localhost'), 8080

    debug(opt.debug)
    run(args[0], host=host, port=port, server=opt.server, reloader=opt.reload, plugins=opt.plugin)

# THE END

########NEW FILE########
__FILENAME__ = OAuthTools
#
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http:/www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import oauth2 as oauth
from imgfac.rest.bottle import * 
from imgfac.ApplicationConfiguration import ApplicationConfiguration

log = logging.getLogger(__name__)

oauth_server = oauth.Server(signature_methods={'HMAC-SHA1':oauth.SignatureMethod_HMAC_SHA1()})

class Consumer(object):
    def __init__(self, key):
        consumers = ApplicationConfiguration().configuration['clients']
        self.key = key
        self.secret = consumers.get(key) if consumers else None

def validate_two_leg_oauth():
    try:
        auth_header_key = 'Authorization'
        auth_header = {}
        if auth_header_key in request.headers:
            auth_header.update({auth_header_key:request.headers[auth_header_key]})
        else:
            response.set_header('WWW-Authenticate', 'OAuth')
            raise HTTPResponse(status=401, output='Unauthorized: missing authorization')
        req = oauth.Request.from_request(request.method,
                                         request.url,
                                         headers=auth_header,
                                         parameters=request.params)
        oauth_consumer = Consumer(request.params['oauth_consumer_key'])
        oauth_server.verify_request(req, oauth_consumer, None)
        return True
    except AttributeError as e:
        log.debug('Returning HTTP 401 (Unauthorized: authorization failed) on exception: %s' % e)
        response.set_header('WWW-Authenticate', 'OAuth')
        raise HTTPResponse(status=401, output='Unauthorized: authorization failed')
    except Exception as e:
        log.exception('Returning HTTP 500 (OAuth validation failed) on exception: %s' % e)
        raise HTTPResponse(status=500, output='OAuth validation failed: %s' % e)

def oauth_protect(f):
    def decorated_function(*args, **kwargs):
        if(not ApplicationConfiguration().configuration['no_oauth']):
            validate_two_leg_oauth()
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


########NEW FILE########
__FILENAME__ = RESTtools
#
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http:/www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.rest.bottle import *
from imgfac.picklingtools.xmlloader import *

log = logging.getLogger(__name__)

def form_data_for_content_type(content_type):
    def dencode(a_dict, encoding='ascii'):
        new_dict = {}
        for k,v in a_dict.items():
            ek = k.encode(encoding)
            if(isinstance(v, unicode)):
                new_dict[ek] = v.encode(encoding)
            elif(isinstance(v, dict)):
                new_dict[ek] = dencode(v)
            else:
                new_dict[ek] = v
        return new_dict

    try:
        if(content_type.startswith('application/json')):
            return dencode(request.json)
        elif(content_type.startswith('application/xml') or content_type.startswith('text/xml')):
            xml_options = XML_LOAD_UNFOLD_ATTRS | XML_LOAD_NO_PREPEND_CHAR | XML_LOAD_EVAL_CONTENT
            return dencode(ReadFromXMLStream(request.body, xml_options))
        else:
            return dencode(request.forms)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

def log_request(f):
    def decorated_function(*args, **kwargs):
        if(ApplicationConfiguration().configuration['debug']):
            request_body = request.body.read()
            if('credentials' in request_body):
                marker = 'provider_credentials'
                starting_index = request_body.find(marker)
                ending_index = request_body.rfind(marker) + len(marker)
                sensitive = request_body[starting_index:ending_index]
                request_body = request_body.replace(sensitive, 'REDACTED')
            log.debug('Handling %s HTTP %s REQUEST for resource at %s: %s' % (request.headers.get('Content-Type'),
                                                                              request.method,
                                                                              request.path,
                                                                              request_body))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def check_accept_header(f):
    def decorated_function(*args, **kwargs):
        accept_header = request.get_header('Accept', None)
        if(accept_header and (('*/*' not in accept_header) and ('application/json' not in accept_header) and ('xml' not in accept_header))):
            log.debug('Returning HTTP 406, unsupported response type: %s' % accept_header)
            raise HTTPResponse(status=406, output='Responses in %s are currently unsupported.' % accept_header)
        else:
            return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

########NEW FILE########
__FILENAME__ = RESTv2
#
#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http:/www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import sys
import traceback

sys.path.insert(1, '%s/imgfac/rest' % sys.path[0])

import logging
import os.path
from bottle import *
from imgfac.rest.RESTtools import *
from imgfac.rest.OAuthTools import oauth_protect
from imgfac.BuildDispatcher import BuildDispatcher
from imgfac.PluginManager import PluginManager
from imgfac.PersistentImageManager import PersistentImageManager
from imgfac.Version import VERSION as VERSION
from imgfac.picklingtools.xmldumper import *
from imgfac.Builder import Builder

log = logging.getLogger(__name__)

rest_api = Bottle(catchall=True)

IMAGE_TYPES = {'BaseImage': 'base_image', 'TargetImage': 'target_image', 'ProviderImage': 'provider_image',
               'base_images': 'BaseImage', 'target_images': 'TargetImage', 'provider_images': 'ProviderImage'}

def converted_response(resp_dict):
    if('xml' in request.get_header('Accept', '')):
        response.set_header('Content-Type', request.get_header('Accept', None))
        xml_options = XML_DUMP_STRINGS_AS_STRINGS | XML_DUMP_PRETTY | XML_DUMP_POD_LIST_AS_XML_LIST
        string_stream = cStringIO.StringIO()
        WriteToXMLStream(resp_dict, string_stream, options=xml_options)
        converted_response = string_stream.getvalue()
        return converted_response
    else:
        return resp_dict

@rest_api.get('/imagefactory')
@log_request
@check_accept_header
def api_info():
    return converted_response({'name':'imagefactory', 'version':VERSION, 'api_version':'2.0'})

@rest_api.get('/imagefactory/<image_collection>')
@rest_api.get('/imagefactory/base_images/<base_image_id>/<image_collection>')
@rest_api.get('/imagefactory/target_images/<target_image_id>/<image_collection>')
@log_request
@oauth_protect
@check_accept_header
def list_images(image_collection, base_image_id=None, target_image_id=None, list_url=None):
    try:
        _type = IMAGE_TYPES[image_collection]
        if _type:
            fetch_spec = {'type': _type}
            if base_image_id:
                fetch_spec['base_image_id'] = base_image_id
            if target_image_id:
                fetch_spec['target_image_id'] = target_image_id
        else:
            raise HTTPResponse(status=404, output='%s not found' % image_collection)

        fetched_images = PersistentImageManager.default_manager().images_from_query(fetch_spec)
        images = list()
        _url = list_url if list_url else request.url
        for image in fetched_images:
            resp_item = {image_collection[0:-1]:
                            {'_type':type(image).__name__,
                            'id':image.identifier,
                            'href':'%s/%s' % (_url, image.identifier)}
                        }
            images.append(resp_item)

        return converted_response({image_collection:images})
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

@rest_api.post('/imagefactory/<image_collection>')
@rest_api.post('/imagefactory/base_images/<base_image_id>/<image_collection>')
@rest_api.post('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>/<image_collection>')
@rest_api.post('/imagefactory/target_images/<target_image_id>/<image_collection>')
@log_request
@oauth_protect
@check_accept_header
def create_image(image_collection, base_image_id=None, target_image_id=None):
    try:
        image_type = image_collection[0:-1]
        content_type = request.headers.get('Content-Type')
        form_data = form_data_for_content_type(content_type)
        if(('application/x-www-form-urlencoded' in content_type) or ('multipart/form-data' in content_type)):
            request_data = form_data
        else:
            request_data = form_data.get(image_type)
        if(not request_data):
            raise HTTPResponse(status=400, output='%s not found in request.' % image_type)

        req_base_img_id = request_data.get('base_image_id')
        req_target_img_id = request_data.get('target_image_id')
        base_img_id = req_base_img_id if req_base_img_id else base_image_id
        target_img_id = req_target_img_id if req_target_img_id else target_image_id

        if(image_collection == 'base_images'):
            builder = BuildDispatcher().builder_for_base_image(template=request_data.get('template'),
                                                               parameters=request_data.get('parameters'))
            image = builder.base_image
        elif(image_collection == 'target_images'):
            builder = BuildDispatcher().builder_for_target_image(target=request_data.get('target'),
                                                                 image_id=base_img_id,
                                                                 template=request_data.get('template'),
                                                                 parameters=request_data.get('parameters'))
            image = builder.target_image
        elif(image_collection == 'provider_images'):
            _provider = request_data.get('provider')
            _credentials = request_data.get('credentials')
            _target = request_data.get('target')
            if(_provider and _credentials and _target):
                builder = BuildDispatcher().builder_for_provider_image(provider=_provider,
                                                                   credentials=_credentials,
                                                                   target=_target,
                                                                   image_id=target_img_id,
                                                                   template=request_data.get('template'),
                                                                   parameters=request_data.get('parameters'))
                image = builder.provider_image
            else:
                _credentials = 'REDACTED' if _credentials else None
                raise HTTPResponse(status=400, output="Missing key/value pair: provider(%s), credentials(%s), target(%s)" % (_provider, _credentials, _target))
        else:
            raise HTTPResponse(status=404, output="%s not found" % image_collection)

        _response = {'_type':type(image).__name__,
                     'id':image.identifier,
                     'href':'%s/%s' % (request.url, image.identifier)}
        for key in image.metadata():
            if key not in ('identifier', 'data'):
                _response[key] = getattr(image, key, None)

        response.status = 202
        return converted_response({image_collection[0:-1]:_response})
    except KeyError as e:
        log.exception(e)
        raise HTTPResponse(status=400, output='Missing value for key: %s' % e)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

@rest_api.get('/imagefactory/<collection_type>/<image_id>')
@rest_api.get('/imagefactory/base_images/<base_image_id>/<collection_type>/<image_id>')
@rest_api.get('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>/<collection_type>/<image_id>')
@rest_api.get('/imagefactory/target_images/<target_image_id>/<collection_type>/<image_id>')
@log_request
@oauth_protect
@check_accept_header
def image_with_id(collection_type, image_id, base_image_id=None, target_image_id=None, provider_image_id=None):
    try:
        img_class = IMAGE_TYPES[collection_type]
        if img_class:
            fetch_spec = {'type': img_class, 'identifier': image_id}
            try:
                image = PersistentImageManager.default_manager().images_from_query(fetch_spec)[0]
                _type = type(image).__name__
                _response = {'_type': _type,
                             'id': image.identifier,
                             'href': request.url}
                for key in image.metadata():
                    if key not in ('identifier', 'data', 'base_image_id', 'target_image_id'):
                        _response[key] = getattr(image, key, None)

                api_url = '%s://%s/imagefactory' % (request.urlparts[0], request.urlparts[1])

                if (_type == "BaseImage"):
                    _objtype = 'base_image'
                    _response['target_images'] = list_images('target_images',
                                                             base_image_id=image.identifier,
                                                             list_url='%s/target_images' % api_url)
                elif (_type == "TargetImage"):
                    _objtype = 'target_image'
                    base_image_id = image.base_image_id
                    if (base_image_id):
                        base_image_href = '%s/base_images/%s' % (api_url, base_image_id)
                        base_image_dict = {'_type': 'BaseImage', 'id': base_image_id, 'href': base_image_href}
                        _response['base_image'] = base_image_dict
                    else:
                        _response['base_image'] = None
                    _response['provider_images'] = list_images('provider_images',
                                                               target_image_id=image.identifier,
                                                               list_url='%s/provider_images' % api_url)
                elif (_type == "ProviderImage"):
                    _objtype = 'provider_image'
                    target_image_id = image.target_image_id
                    if (target_image_id):
                        target_image_href = '%s/target_images/%s' % (api_url, target_image_id)
                        target_image_dict = {'_type': 'TargetImage', 'id': target_image_id, 'href': target_image_href}
                        _response['target_image'] = target_image_dict
                    else:
                        _response['target_image'] = None
                else:
                    log.error("Returning HTTP status 500 due to unknown image type: %s" % _type)
                    raise HTTPResponse(status=500, output='Bad type for found object: %s' % _type)

                response.status = 200
                return converted_response({_objtype: _response})

            except IndexError as e:
                log.warning(e)
                raise HTTPResponse(status=404, output='No %s found with id: %s' % (img_class, image_id))
        else:
            raise HTTPResponse(status=404, output='Unknown resource type: %s' % collection_type)
    except KeyError as e:
        if collection_type == 'plugins':
            return get_plugins(plugin_id=image_id)
        else:
            log.exception(e)
            raise HTTPResponse(status=500, output=e)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

@rest_api.get('/imagefactory/base_images/<image_id>/raw_image')
@rest_api.get('/imagefactory/target_images/<image_id>/raw_image')
@rest_api.get('/imagefactory/provider_images/<image_id>/raw_image')
@rest_api.get('/imagefactory/base_images/<base_image_id>/target_images/<image_id>/raw_image')
@rest_api.get('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>/provider_images/<image_id>/raw_image')
@rest_api.get('/imagefactory/target_images/<target_image_id>/provider_images/<image_id>/raw_image')
@log_request
@oauth_protect
@check_accept_header
def get_image_file(image_id, base_image_id=None, target_image_id=None, provider_image_id=None):
    try:
        image = PersistentImageManager.default_manager().image_with_id(image_id)
        if(not image):
            raise HTTPResponse(status=404, output='No image found with id: %s' % image_id)
        path, filename = os.path.split(image.data)
        return static_file(filename, path, download=True)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

@rest_api.delete('/imagefactory/<collection_type>/<image_id>')
@rest_api.delete('/imagefactory/base_images/<base_image_id>/<collection_type>/<image_id>')
@rest_api.delete('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>/<collection_type>/<image_id>')
@rest_api.delete('/imagefactory/target_images/<target_image_id>/<collection_type>/<image_id>')
@log_request
@oauth_protect
@check_accept_header
def delete_image_with_id(image_id, collection_type=None, base_image_id=None, target_image_id=None, provider_image_id=None):
    try:
        response.status = 204
        image = PersistentImageManager.default_manager().image_with_id(image_id)
        if(not image):
            raise HTTPResponse(status=404, output='No image found with id: %s' % image_id)
        image_class = type(image).__name__
        builder = Builder()
        content_type = request.headers.get('Content-Type')
        form_data = form_data_for_content_type(content_type)
        required_values = set(['provider', 'credentials', 'target'])

        if form_data:
            root_object = form_data.get(IMAGE_TYPES.get(image_class))
            if root_object and (type(root_object) is dict):
                request_data = root_object
            else:
                request_data = form_data

            if image_class == 'ProviderImage':
                missing_values = required_values.difference(request_data)
                if len(missing_values) > 0:
                    raise HTTPResponse(status=400, output='Missing required values: %s' % missing_values)

            builder.delete_image(provider=request_data.get('provider'),
                                 credentials=request_data.get('credentials'),
                                 target=request_data.get('target'),
                                 image_object=image,
                                 parameters=request_data.get('parameters'))
        else:
            if image_class == 'ProviderImage':
                raise HTTPResponse(status=400, output='Missing required values:%s' % required_values)
            else:
                builder.delete_image(provider=None, credentials=None, target=None, image_object=image, parameters=None)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output=e)

@rest_api.get('/imagefactory/plugins')
@rest_api.get('/imagefactory/plugins/')
@rest_api.get('/imagefactory/plugins/<plugin_id>')
@log_request
@oauth_protect
@check_accept_header
def get_plugins(plugin_id=None):
    try:
        response.status = 200
        plugin_mgr = PluginManager()
        if(plugin_id):
            plugin = plugin_mgr.plugins[plugin_id].copy()
            plugin.update({'_type':'plugin',
                           'id':plugin_id,
                           'href':'%s/%s' % (request.url, plugin_id)})
            return converted_response(plugin)
        else:
            plugins = plugin_mgr.plugins.copy()
            for plugin in plugins:
                plugins[plugin].update({'_type':'plugin',
                                        'id':plugin,
                                        'href':'%s/%s' % (request.url, plugin)})
        return converted_response({'plugins':plugins.values()})
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output='%s %s' % (e, traceback.format_exc()))

@rest_api.get('/imagefactory/jeos')
@log_request
@check_accept_header
def get_jeos_config():
    try:
        jeos_confs = dict()
        jeos_conf_list = ApplicationConfiguration().configuration['jeos_config']
        for item in jeos_conf_list:
            jeos_confs[jeos_conf_list.index(item)] = item
        return converted_response(jeos_confs)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output='%s %s' % (e, traceback.format_exc()))

@rest_api.get('/imagefactory/jeos/images')
@rest_api.get('/imagefactory/jeos/images/<jeos_id>')
@log_request
@check_accept_header
def get_jeos_info(jeos_id=None):
    try:
        if jeos_id:
            return HTTPResponse(status=501)

        response.status = 200
        return converted_response(ApplicationConfiguration().jeos_images)
    except Exception as e:
        log.exception(e)
        raise HTTPResponse(status=500, output='%s %s' % (e, traceback.format_exc()))

# Things we have not yet implemented
@rest_api.get('/imagefactory/targets')
@rest_api.get('/imagefactory/targets/<target_id>')
@rest_api.get('/imagefactory/targets/<target_id>/providers')
@rest_api.get('/imagefactory/targets/<target_id>/providers/<provider_id>')
@log_request
@check_accept_header
def method_not_implemented(**kw):
    """
    @return 501 Not Implemented
    """
    raise HTTPResponse(status=501)

# Things we don't plan to implement
#@rest_api.route('/imagefactory', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/base_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/base_images/<base_image_id>', method=('PUT','POST'))
#@rest_api.route('/imagefactory/target_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/target_images/<target_image_id>', method=('PUT','POST'))
#@rest_api.route('/imagefactory/target_images/<target_image_id>/provider_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/provider_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/provider_images/<provider_image_id>', method=('PUT','POST'))
#@rest_api.route('/imagefactory/base_images/<base_image_id>/target_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>', method=('PUT','POST'))
#@rest_api.route('/imagefactory/base_images/<base_image_id>/target_images/<target_image_id>/provider_images', method=('PUT','DELETE'))
#@rest_api.route('/imagefactory/targets', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/targets/<target_id>', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/targets/<target_id>/providers', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/targets/<target_id>/providers/<provider_id>', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/jeos', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/jeos/<jeos_id>', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/plugins', method=('PUT','POST','DELETE'))
#@rest_api.route('/imagefactory/plugins/<plugin_id>', method=('PUT','POST','DELETE'))
#def method_not_allowed(**kw):
#    """
#    @return 405 Method Not Allowed
#    """
#    raise HTTPResponse(status=405)

########NEW FILE########
__FILENAME__ = Singleton
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            instance = super(Singleton, cls).__new__(cls)
            instance._singleton_init(*args, **kwargs)
            cls._instance = instance
        return cls._instance

    def __init__(self, *args, **kwargs):
        pass

    def _singleton_init(self, *args, **kwargs):
        """Initialize a singleton instance before it is registered."""
        pass

########NEW FILE########
__FILENAME__ = TargetImage
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from PersistentImage import PersistentImage
from props import prop


METADATA = ('base_image_id', 'target')

class TargetImage(PersistentImage):
    """ TODO: Docstring for TargetImage  """

    base_image_id = prop("_base_image_id")
    target = prop("_target")
    parameters = prop("_parameters")

    def __init__(self, image_id=None):
        super(TargetImage, self).__init__(image_id)
        self.base_image_id = None
        self.target = None

    def metadata(self):
        self.log.debug("Executing metadata in class (%s) my metadata is (%s)" % (self.__class__, METADATA))
        return frozenset(METADATA + super(self.__class__, self).metadata())

########NEW FILE########
__FILENAME__ = Template
# encoding: utf-8

#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import httplib2
import re
import os.path
import props
import libxml2
from imgfac.ApplicationConfiguration import ApplicationConfiguration

class Template(object):
    uuid_pattern = '([0-9a-f]{8})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{12})'

    identifier = props.prop("_identifier", "The identifier property.")
    url = props.prop("_url", "The url property.")
    xml = props.prop("_xml", "The xml property.")
    @property
    def name(self):
        """The property name"""
        return self._content_at_path('/template/name')
    @property
    def os_name(self):
        """The property os_name"""
        return self._content_at_path('/template/os/name')
    @property
    def os_version(self):
        """The property os_version"""
        return self._content_at_path('/template/os/version')
    @property
    def os_arch(self):
        """The property os_arch"""
        return self._content_at_path('/template/os/arch')
    @property
    def install_type(self):
        """The type of install ('url' or 'iso')"""
        result = libxml2.parseDoc(self.xml).xpathEval('/template/os/install')[0]
        if result:
            return result.prop('type')
        else:
            return None
    @property
    def install_url(self):
        """OS install URL"""
        return self._content_at_path('/template/os/install/url')
    @property
    def install_iso(self):
        """OS install ISO"""
        return self._content_at_path('/template/os/install/iso')
    @property
    def install_location(self):
        """Either OS install URL or ISO"""
        return self._content_at_path('/template/os/install/%s' % self.install_type)

    def __repr__(self):
        if(self.xml):
            return self.xml
        else:
            return super(Template, self).__repr__

    def _content_at_path(self, path):
        try:
            return libxml2.parseDoc(self.xml).xpathEval(path)[0].content
        except Exception as e:
            self.log.exception('Could not parse document for path (%s):\n%s' % (path, e))
            return None

    def __init__(self, template=None, uuid=None, url=None, xml=None):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

        self.identifier = None
        self.url = None
        self.xml = None

        path = None
        if(template):
            template_string = str(template)
            template_string_type = self.__template_string_type(template_string)
            if(template_string_type == "UUID"):
                uuid = template_string
            elif(template_string_type == "URL"):
                url = template_string
            elif(template_string_type == "XML"):
                xml = template_string
            elif(template_string_type == "PATH"):
                path = template_string

        if(uuid):
            uuid_string = uuid
            self.identifier, self.xml = self.__fetch_template_for_uuid(uuid_string)
            if((not self.identifier) and (not self.xml)):
                raise RuntimeError("Could not create a template with the uuid %s" % (uuid, ))
        elif(url):
            self.url = url
            self.identifier, self.xml = self.__fetch_template_with_url(url)
        elif(xml):
            self.xml = xml
        elif(path):
            template_file = open(path, "r")
            file_content = template_file.read()
            template_file.close()
            if(self.__string_is_xml_template(file_content)):
                self.xml = file_content
            else:
                raise ValueError("File %s does not contain properly formatted template xml:\n%s" % (path, self.__abbreviated_template(file_content)))
        else:
            raise ValueError("'template' must be a UUID, URL, XML string or XML document path...")

    def __template_string_type(self, template_string):
        regex = re.compile(Template.uuid_pattern)
        match = regex.search(template_string)

        if(template_string.lower().startswith("http")):
            return "URL"
        elif(("<template" in template_string.lower()) and ("</template>" in template_string.lower())):
            return "XML"
        elif(match):
            return "UUID"
        elif(os.path.exists(template_string)):
            return "PATH"
        else:
            raise ValueError("'template_string' must be a UUID, URL, or XML document...\n--- TEMPLATE STRING ---\n%s\n-----------------" % (template_string, ))

    def __string_is_xml_template(self, text):
        return (("<template" in text.lower()) and ("</template>" in text.lower()))

    def __abbreviated_template(self, template_string):
        lines = template_string.splitlines(True)
        if(len(lines) > 20):
            return "%s\n...\n...\n...\n%s" % ("".join(lines[0:10]), "".join(lines[-10:len(lines)]))
        else:
            return template_string

########NEW FILE########
__FILENAME__ = e2eTest
#!/usr/bin/env python

import argparse
import tempfile
import subprocess
import json
from time import sleep
import threading
import os
import sys
from tempfile import NamedTemporaryFile
import requests
from requests_oauthlib import OAuth1

client_key = 'mock-key'
client_secret = 'mock-secret'

oauth = OAuth1(client_key, client_secret=client_secret)


description = 'Attempts an end to end test of the imagefactory command line interface\
        by creating base images, building a target image from each of the successfully\
        built base images, pushing the target images to each of the providers defined\
        for a target, and finally deleting the provider images. What is done at each\
        step is controlled by the datafile you supply this script. The e2eTest-ExampleData.json\
        file can be found in the scripts/tests/ directory of the imagefactory source\
        tree for you to customize to your own testing.\
        To execute the test via REST api (the default) you need to disable ssl and oauth\
        launching the daemon with --no_ssl and --no_oauth.'
argparser = argparse.ArgumentParser()
argparser.add_argument('datafile', type=argparse.FileType('r'))
argparser.add_argument('--cmd', default='/usr/bin/imagefactory', help='Path to the imagefactory command. (default: %(default)s)')
argparser.add_argument('--url', default='https://localhost:8075/imagefactory', help='URL of the imagefactory instance to test. (default: %(default)s)')
argparser.add_argument('-L', help='uses the local CLI to run the tests instead of the REST api interface. (default: %(default)s)', action='store_false', dest='remote')

args = argparser.parse_args()
test_data = json.load(args.datafile)
args.datafile.close()
builds = test_data['jeos']
targets = test_data['targets']
providers = test_data['providers']
requests_headers = {'accept': 'application/json', 'content-type': 'application/json'}

base_images = []
b_lock = threading.Lock()
target_images = []
t_lock = threading.Lock()
provider_images = []
p_lock = threading.Lock()
failures = []
f_lock = threading.Lock()
build_queue = threading.BoundedSemaphore(len(builds))
test_count = len(builds) * len(targets)
test_index = 0
proc_chk_interval = 10
# Required for Python 2.6 backwards compat
def subprocess_check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, *popenargs, **kwargs)
    stdout, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = ' '.join(*popenargs)
        raise Exception("'%s' failed(%d): %s" % (cmd, retcode, stdout))
    return (stdout, stderr, retcode)
###

def create_base_image(template_args):
    print "Building base image"
    build_queue.acquire()
    try:
        TDL = "<template><name>buildbase_image</name><os><name>%s</name><version>%s\
</version><arch>%s</arch><install type='url'><url>%s</url></install><rootpw>password</rootpw></os>\
<description>Tests building a base_image</description></template>" % (template_args['os'],
                                                                     template_args['version'],
                                                                     template_args['arch'],
                                                                     template_args['url'])

        template = tempfile.NamedTemporaryFile(mode='w', delete=False)
        template.write(TDL)
        template.close()

        if args.remote:
            payload = {'base_image': {'template': TDL}}
            r = requests.post(args.url+'/base_images', data=json.dumps(payload), headers=requests_headers, auth=oauth, verify=False)
            base_image_output_str = r.text
        else:
            (base_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw base_image %s' % (args.cmd, template.name), shell=True)
        base_image_output_dict = json.loads(base_image_output_str)['base_image']
        base_image_id = base_image_output_dict['id']
        while(base_image_output_dict['status'] not in ('COMPLETE', 'COMPLETED', 'FAILED')):
            sleep(proc_chk_interval)
            if args.remote:
                r = requests.get(args.url+'/base_images/'+base_image_id, auth=oauth, verify=False)
                base_image_output_str = r.text
                print "Checking status of %s" % (base_image_id,)
            else:
                (base_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw images \'{"identifier":"%s"}\'' % (args.cmd, base_image_id), shell=True)
            base_image_output_dict = json.loads(base_image_output_str)['base_image']

        if(base_image_output_dict['status'] == 'FAILED'):
            with f_lock:
                failures.append(base_image_output_dict)
        else:
            with b_lock:
                base_images.append(base_image_output_dict)
    finally:
        build_queue.release()

def build_push_delete(target, index):
    global test_index
    build_queue.acquire()
    try:
        if(index < len(base_images)):
            base_image = base_images[index]
            if args.remote:
                payload = {'target_image': {'target': target}}
                print "Creating a target image"
                r = requests.post(args.url+'/base_images/'+base_image['id']+'/target_images', data=json.dumps(payload), headers=requests_headers, auth=oauth, verify=False)
                target_image_output_str = r.text
            else:
                (target_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw target_image --id %s %s' % (args.cmd, base_image['id'], target), shell=True)
            target_image_output_dict = json.loads(target_image_output_str)['target_image']
            target_image_id = target_image_output_dict['id']
            while(target_image_output_dict['status'] not in ('COMPLETE', 'COMPLETED', 'FAILED')):
                sleep(proc_chk_interval)
                if args.remote:
                    r = requests.get(args.url+'/target_images/'+target_image_id, auth=oauth, verify=False)
                    target_image_output_str = r.text
                else:
                    (target_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw images \'{"identifier":"%s"}\'' % (args.cmd, target_image_id), shell=True)
                target_image_output_dict = json.loads(target_image_output_str)['target_image']

            if(target_image_output_dict['status'] == 'FAILED'):
                with f_lock:
                    failures.append(target_image_output_dict)
            else:
                with t_lock:
                    target_images.append(target_image_output_dict)
                for provider in providers:
                    if((not provider['name'].startswith('example')) and (provider['target'] == target)):
                        try:
                            if 'ec2' in provider['target']:
                                f = open(provider['credentials'], 'r')
                                provider['credentials'] = f.read()
                                f.close()
                            credentials_file = NamedTemporaryFile()
                            credentials_file.write(provider['credentials'])
                            provider_file = NamedTemporaryFile()
                            provider_file.write(str(provider['definition']))
                            if args.remote:
                                payload = {'provider_image': {'target': target, 'provider': provider['name'], 'credentials': provider['credentials']}}
                                r = requests.post(args.url+'/target_images/'+target_image_id+'/provider_images', data=json.dumps(payload), headers=requests_headers, auth=oauth, verify=False)
                                provider_image_output_str = r.text
                            else:
                                (provider_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw provider_image --id %s %s %s %s' % (args.cmd, target_image_id, provider['target'], provider_file.name, credentials_file.name), shell=True)
                            provider_image_output_dict = json.loads(provider_image_output_str)['provider_image']
                            provider_image_id = provider_image_output_dict['id']
                            while(provider_image_output_dict['status'] not in ('COMPLETE', 'COMPLETED', 'FAILED')):
                                sleep(proc_chk_interval)
                                if args.remote:
                                    r = requests.get(args.url+'/provider_images/'+provider_image_id, auth=oauth, verify=False)
                                    provider_image_output_str = r.text
                                else:
                                    (provider_image_output_str, ignore, ignore) = subprocess_check_output('%s --output json --raw images \'{"identifier":"%s"}\'' % (args.cmd, provider_image_id), shell=True)
                                provider_image_output_dict = json.loads(provider_image_output_str)['provider_image']

                            if(provider_image_output_dict['status'] == 'FAILED'):
                                with f_lock:
                                    failures.append(provider_image_output_dict)
                            else:
                                with p_lock:
                                    provider_images.append(provider_image_output_dict)
                                if args.remote:
                                    
                                    print "Checking status of %s" % (base_image_id,)
                                    r = requests.delete(args.url+'/provider_images/'+provider_image_id, auth=oauth, verify=False)
                                else:
                                    subprocess_check_output('%s --output json --raw delete %s --target %s --provider %s --credentials %s' % (args.cmd, provider_image_id, provider['target'], provider_file.name, credentials_file.name), shell=True)
                        finally:
                            credentials_file.close()
                            provider_file.close()

    finally:
        build_queue.release()
        test_index += 1

for build in builds:
    thread_name = "%s-%s-%s.%s" % (build['os'], build['version'], build['arch'], os.getpid())
    build_thread = threading.Thread(target=create_base_image, name = thread_name, args=(build,))
    build_thread.start()
for target in targets:
    for index in range(len(builds)):
        thread_name = "%s-%s.%s" % (target, index, os.getpid())
        customize_thread = threading.Thread(target=build_push_delete, name=thread_name, args=(target, index))
        customize_thread.start()

while(test_index < test_count):
    sleep(proc_chk_interval)
for target_image in target_images:
    if args.remote:
        r = requests.delete(args.url+'/target_images/'+target_image['id'], auth=oauth, verify=False)
    else:
        subprocess_check_output('%s --output json --raw delete %s' % (args.cmd, target_image['id']), shell=True)

for base_image in base_images:
    if args.remote:
        print "About to delete base image: %s" % (base_image['id'],)
        r = requests.delete(args.url+'/base_images/'+base_image['id'], auth=oauth, verify=False)
    else:
        subprocess_check_output('%s --output json --raw delete %s' % (args.cmd, base_image['id']), shell=True)

print json.dumps({"failures":failures, "base_images":base_images, "target_images":target_images}, indent=2)
sys.exit(0)

########NEW FILE########
__FILENAME__ = test_build
# loads tests config and utilities
import utils

# actual tests code
import os
import Queue
import threading

base_built = {}
base_lock = threading.RLock()

target_built = {}
target_lock = threading.RLock()

provider_built = {}
provider_lock = threading.RLock()

def _assert_base_complete(tdlfile):
  imageid, imagestatus = base_built.get(tdlfile)
  assert imagestatus == 'COMPLETE'

def _build_base_from_queue(queue):
  global base_built
  while True:
    tdlfile = queue.get()
    template = open(tdlfile, 'r').read()
    imagejson = utils.build_base(template)
    imageid = imagejson['id']
    imagestatus = utils.wait_until_base_completes(imageid)
    with base_lock:
      base_built[tdlfile] = (imageid, imagestatus)
    queue.task_done()

def test_base_build():
  queue = Queue.Queue()
  for tdlfile in utils.TEMPLATE_FILES:
    queue.put(tdlfile)
  for i in range(utils.MAX_THREADS):
    t = threading.Thread(target=_build_base_from_queue, args=(queue,))
    t.daemon = True
    t.start()
  queue.join()
  for tdlfile in utils.TEMPLATE_FILES:
    yield _assert_base_complete, tdlfile

def _assert_target_complete(tdlfile, target_provider):
  imageid, imagestatus = target_built.get((tdlfile, target_provider))
  assert imagestatus == 'COMPLETE'

def _build_target_from_queue(queue):
  global target_built
  while True:
    tdlfile, target_provider = queue.get()
    template = open(tdlfile, 'r').read()
    imagejson = utils.build_target(template, target_provider)
    imageid = imagejson['id']
    imagestatus = utils.wait_until_target_completes(imageid)
    with target_lock:
      target_built[(tdlfile, target_provider)] = (imageid, imagestatus)
    queue.task_done()

def test_target_build():
  queue = Queue.Queue()
  for tdlfile in utils.TEMPLATE_FILES:
    for target_provider in utils.TARGETS:
      queue.put((tdlfile, target_provider))
  for i in range(utils.MAX_THREADS):
    t = threading.Thread(target=_build_target_from_queue, args=(queue,))
    t.daemon = True
    t.start()
  queue.join()
  for tdlfile in utils.TEMPLATE_FILES:
    for target_provider in utils.TARGETS:
      yield _assert_target_complete, tdlfile, target_provider

def _assert_provider_complete(tdlfile, target_provider):
  imageid, imagestatus = provider_built.get((tdlfile, target_provider))
  assert imagestatus == 'COMPLETE'

def _build_provider_from_queue(queue):
  global provider_built
  while True:
    tdlfile, provider = queue.get()
    template = open(tdlfile, 'r').read()
    provider_definition = open(utils.PROVIDERS_FILE_PATH+provider+'.json', 'r').read()
    provider_credentials = open(utils.PROVIDERS_FILE_PATH+provider+'_credentials.xml', 'r').read()
    imagejson = utils.build_provider(template, provider, provider_definition.strip(), provider_credentials)
    imageid = imagejson['id']
    imagestatus = utils.wait_until_provider_completes(imageid)
    with provider_lock:
      provider_built[(tdlfile, provider)] = (imageid, imagestatus)
    queue.task_done()

def test_provider_build():
  queue = Queue.Queue()
  for tdlfile in utils.TEMPLATE_FILES:
    for provider in utils.PROVIDERS:
      queue.put((tdlfile, provider))
  for i in range(utils.MAX_THREADS):
    t = threading.Thread(target=_build_provider_from_queue, args=(queue,))
    t.daemon = True
    t.start()
  queue.join()
  for tdlfile in utils.TEMPLATE_FILES:
    for provider in utils.PROVIDERS:
      yield _assert_provider_complete, tdlfile, provider

def _assert_target_content_installed(target_provider, imageid):
  expectedpkgs = utils.list_expected_packages(target_provider)
  imagepkgs = utils.list_installed_packages(imageid)
  for pkg in expectedpkgs:
    assert pkg in imagepkgs

def test_target_content():
  if utils.IMGFAC_URL.find("localhost") >= 0 and os.path.isfile(utils.IMGFAC_TCXML) and os.path.isfile(utils.IMGFAC_CONF):
    for target_imageid, target_imagestatus in target_built.itervalues():
      if target_imagestatus == 'COMPLETE':
        imagejson = utils.get_target(target_imageid)
        yield _assert_target_content_installed, imagejson['target'], target_imageid
  else:
    print "Skipping target images inspection: imgfac is not running locally? target_content.xml missing? imagefactory.conf misplaced?"

########NEW FILE########
__FILENAME__ = test_validation
# loads tests config and utilities
import utils

# actual tests code
import re
import random
import xml.etree.ElementTree as ET


def test_tdl_structure_validation():
  template = open(random.choice(utils.TEMPLATE_FILES), 'r').read()
  template = re.sub('<install', '<intall', template)
  imagejson = utils.build_base(template)
  imageid = imagejson['id']
  assert utils.wait_until_base_completes(imageid) == 'FAILED'

def test_tdl_content_validation():
  tree = ET.parse(random.choice(utils.TEMPLATE_FILES))
  roottag = tree.getroot()
  ostag = roottag.find('./os')
  rootpwtag = ostag.find('./rootpw')
  ostag.remove(rootpwtag)
  imagejson = utils.build_base(ET.tostring(roottag))
  imageid = imagejson['id']
  assert utils.wait_until_base_completes(imageid) == 'FAILED'

########NEW FILE########
__FILENAME__ = test_version
# loads tests config and utilities
import utils

# actual tests code
#import


def test_api_version():
  rootobject = utils.get_root()
  assert rootobject['api_version'] >= 2

########NEW FILE########
__FILENAME__ = utils
# configuration management
import os
execfile(os.path.join(os.path.dirname(__file__),'config')) 

if 'IMGFAC_URL' in os.environ.keys():
  IMGFAC_URL = os.environ['IMGFAC_URL']

# actual utils code
import json
import time
import requests


def build_base(template):
  payload = {'base_image': {'template': template}}
  r = requests.post(IMGFAC_URL+BASE_IMAGE_ENDPOINT, data=json.dumps(payload), headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['base_image']

def get_base(imageid):
  r = requests.get(IMGFAC_URL+BASE_IMAGE_ENDPOINT+'/'+imageid, headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['base_image']

def wait_until_base_completes(imageid):
  currently = 'UNKNOWN'
  while currently not in ['COMPLETE', 'FAILED']:
    time.sleep(POLLING_INTERVAL)
    try:
      imagejson = get_base(imageid)
      currently = imagejson['status']
    except:
      currently = "FAILED"
  return currently

def build_target(template, target_provider):
  payload = {'target_image': {'target': target_provider, 'template': template}}
  r = requests.post(IMGFAC_URL+TARGET_IMAGE_ENDPOINT, data=json.dumps(payload), headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['target_image']

def get_target(imageid):
  r = requests.get(IMGFAC_URL+TARGET_IMAGE_ENDPOINT+'/'+imageid, headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['target_image']

def wait_until_target_completes(imageid):
  currently = 'UNKNOWN'
  while currently not in ['COMPLETE', 'FAILED']:
    time.sleep(POLLING_INTERVAL)
    try:
      imagejson = get_target(imageid)
      currently = imagejson['status']
    except:
      currently = "FAILED"
  return currently

def build_provider(template, provider, provider_definition, provider_credentials):
  payload = {'provider_image': {'target': provider, 'template': template, 'provider': provider_definition, 'credentials': provider_credentials}}
  if provider.lower() == 'ec2':
    payload = {'provider_image': {'target': provider, 'template': template, 'provider': provider_definition, 'credentials': provider_credentials, 'parameters': {'snapshot': True}}}
  r = requests.post(IMGFAC_URL+PROVIDER_IMAGE_ENDPOINT, data=json.dumps(payload), headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['provider_image']

def get_provider(imageid):
  r = requests.get(IMGFAC_URL+PROVIDER_IMAGE_ENDPOINT+'/'+imageid, headers=REQUEST_HEADERS)
  imagejson = json.loads(r.text)
  return imagejson['provider_image']

def wait_until_provider_completes(imageid):
  currently = 'UNKNOWN'
  while currently not in ['COMPLETE', 'FAILED']:
    time.sleep(POLLING_INTERVAL)
    try:
      imagejson = get_provider(imageid)
      currently = imagejson['status']
    except:
      currently = "FAILED"
  return currently

def get_root():
  r = requests.get(IMGFAC_URL, headers=REQUEST_HEADERS)
  return json.loads(r.text)

# code added for target_content.xml testing
import guestfs
import xml.etree.ElementTree as ET


def _compare_mps(a, b):
  if len(a[0]) > len(b[0]):
    return 1
  elif len(a[0]) == len(b[0]):
    return 0
  else:
    return -1

def list_installed_packages(imageid):
  # Gets the imageid imagefile location
  imgfac_config_file = open(IMGFAC_CONF).read()
  imgfac_conf = json.loads(imgfac_config_file)
  storage_path = imgfac_conf['image_manager_args']['storage_path']
  imgfile = imageid + ".body"
  imgfile_path = storage_path + "/" + imgfile
  # Create the guestfs object, attach the disk image and launch the back-end
  g = guestfs.GuestFS()
  g.add_drive(imgfile_path)
  g.launch()
  # Gets the operating systems root
  roots = g.inspect_os()
  # Assumes the first is the one we want to inspect
  root = roots[0]
  # Mount up the disks, like guestfish -i
  # Sort keys by length, shortest first, so that we end up
  # mounting the filesystems in the correct order
  mps = g.inspect_get_mountpoints(root)
  mps.sort(_compare_mps)
  for mp_dev in mps:
    g.mount_ro (mp_dev[1], mp_dev[0])
  apps = g.inspect_list_applications(root)
  # apps is a list of dicts, we extract app_name of every item
  pkgs = [d["app_name"] for d in apps]
  # Unmount everything
  g.umount_all()
  return pkgs

def list_expected_packages(target_provider):
  tree = ET.parse(IMGFAC_TCXML)
  rootel = tree.getroot()
  pkgsel = rootel.findall("./include[@target='" + target_provider + "']/packages/package")
  pkgs = []
  for pkg in pkgsel:
    pkgs.append(pkg.get("name"))
  return pkgs

########NEW FILE########
__FILENAME__ = testApplicationConfiguration
#!/usr/bin/env python
# encoding: utf-8

#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
import logging
import os
import json
from imgfac.ApplicationConfiguration import ApplicationConfiguration


class TestApplicationConfiguration(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.NOTSET, format='%(asctime)s %(levelname)s %(name)s pid(%(process)d) Message: %(message)s', filename='/tmp/imagefactory-unittests.log')

        self.defaults = dict(verbose=False, debug=False, foreground=False, config="/etc/imagefactory/imagefactory.conf", imgdir="/tmp", qmf=False, warehouse=None, template=None)

        config_file_path = self.defaults["config"]
        if (os.path.isfile(config_file_path)):
            try:
                config_file = open(config_file_path)
                self.defaults.update(json.load(config_file))
                config_file.close()
            except IOError, e:
                pass


    def tearDown(self):
        del self.defaults

    def testSingleton(self):
        self.assertTrue(id(ApplicationConfiguration()) == id(ApplicationConfiguration()))

    # def testConfigurationDictionaryDefaults(self):
    #     self.assertIsNotNone(ApplicationConfiguration().configuration)
    #     self.assertDictContainsSubset(self.defaults, ApplicationConfiguration().configuration)
    #

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testNotificationCenter
#!/usr/bin/env python
# encoding: utf-8

#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
from imgfac.NotificationCenter import NotificationCenter

class testNotificationCenter(unittest.TestCase):
    def setUp(self):
        self.notification_center = NotificationCenter()

    def tearDown(self):
        del self.notification_center

    def testAddRemoveObservers(self):
        o1 = MockObserver()
        o2 = MockObserver()
        nc = self.notification_center
        self.assertEqual(len(nc.observers), 0)
        nc.add_observer(o1, 'receive')
        self.assertEqual(len(nc.observers), 1)
        nc.add_observer(o1, 'receive', 'test')
        self.assertEqual(len(nc.observers), 2)
        nc.add_observer(o2, 'receive', 'test2', self)
        self.assertEqual(len(nc.observers), 3)
        nc.remove_observer(o1, 'receive')
        self.assertEqual(len(nc.observers), 2)
        nc.remove_observer(o1, 'receive', 'test')
        self.assertEqual(len(nc.observers), 1)
        nc.remove_observer(o2, 'receive', 'test2', self)
        self.assertEqual(len(nc.observers), 0)

    def testPostNotification(self):
        o1 = MockObserver()
        o2 = MockObserver()
        o3 = MockObserver()
        mock_sender = object()
        mock_usr_info = dict(test_key='test_value')
        self.assertIsNone(o1.notification)
        nc = self.notification_center
        nc.add_observer(o1, 'receive')
        nc.add_observer(o2, 'receive', 'test')
        nc.add_observer(o3, 'receive', sender=mock_sender)

        nc.post_notification_with_info('any_message', self)
        self.assertEqual(o1.notification.message, 'any_message')
        self.assertIsNone(o2.notification)
        self.assertIsNone(o3.notification)

        nc.post_notification_with_info('test', self)
        self.assertEqual(o1.notification.message, 'test')
        self.assertEqual(o2.notification.message, 'test')
        self.assertIsNone(o3.notification)

        nc.post_notification_with_info('test2', mock_sender)
        self.assertEqual(o1.notification.message, 'test2')
        self.assertNotEqual(o2.notification.message, 'test2')
        self.assertEqual(o3.notification.message, 'test2')

        self.assertIsNone(o1.notification.user_info)
        nc.post_notification_with_info('test3', self, mock_usr_info)
        self.assertDictEqual(o1.notification.user_info, mock_usr_info)
        self.assertEqual(o1.notification.message, 'test3')
        self.assertNotEqual(o2.notification.message, 'test3')
        self.assertNotEqual(o3.notification.message, 'test3')

class MockObserver(object):
    def __init__(self):
        self.notification = None

    def receive(self, notification):
        self.notification = notification

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testPluginManager
# encoding: utf-8

#   Copyright 2012 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
import logging
from imgfac.PluginManager import PluginManager
import tempfile
import json
import os.path
import os
import shutil
import sys

INFO1 = {
            "type":"os",
            "targets":[["osfoo", "osbar", "osbaz"]],
            "description":"blah",
            "maintainer": {
                "name":"foo1",
                "email":"bar1",
                "url":"baz1"
            },
            "version":"1.0",
            "license":"NA"
        }
INFO2 = {
            "type":"cloud",
            "targets":[["cloudfoo", "cloudbar", "cloudbaz"]],
            "description":"whatever",
            "maintainer": {
                "name":"foo2",
                "email":"bar2",
                "url":"baz2"
            },
            "version":"1.0",
            "license":"NA"
        }


class testPluginManager(unittest.TestCase):
    """ TODO: Docstring for testPluginManager  """

    def __init__(self, methodName='runTest'):
        super(testPluginManager, self).__init__(methodName)
        logging.basicConfig(level=logging.NOTSET,
                            format='%(asctime)s \
                                    %(levelname)s \
                                    %(name)s \
                                    pid(%(process)d) \
                                    Message: %(message)s', 
                            filename='/tmp/testPluginManager.log')

    def setUp(self):
        # create the info file for an OS plugin
        self.os_info_file = tempfile.NamedTemporaryFile(mode='w', suffix='.info', prefix='ifut-')
        json.dump(INFO1, self.os_info_file)
        self.os_info_file.flush()
        os.fsync(self.os_info_file)
        self.os_plugin_name = os.path.basename(self.os_info_file.name).partition('.')[0]
        # create a module for this plugin
        os.mkdir(os.path.join(tempfile.gettempdir(), self.os_plugin_name), 0744)
        osclass = open(os.path.join(tempfile.gettempdir(), self.os_plugin_name, self.os_plugin_name + '.py'), 'w')
        osclass.write('class %s(object):\n    pass' % self.os_plugin_name)
        osclass.close()
        osinit = open(os.path.join(tempfile.gettempdir(), self.os_plugin_name, '__init__.py'), 'w')
        osinit.write('from %s import %s as delegate_class' % (self.os_plugin_name, self.os_plugin_name))
        osinit.close()
        # create the info file for a CLOUD plugin
        self.cloud_info_file = tempfile.NamedTemporaryFile(mode='w', suffix='.info', prefix='ifut-')
        json.dump(INFO2, self.cloud_info_file)
        self.cloud_info_file.flush()
        os.fsync(self.cloud_info_file)
        self.cloud_plugin_name = os.path.basename(self.cloud_info_file.name).partition('.')[0]
        # create a module for this plugin
        os.mkdir(os.path.join(tempfile.gettempdir(), self.cloud_plugin_name), 0744)
        cloudclass = open(os.path.join(tempfile.gettempdir(), self.cloud_plugin_name, self.cloud_plugin_name + '.py'), 'w')
        cloudclass.write('class %s(object):\n    pass' % self.cloud_plugin_name)
        cloudclass.close()
        cloudinit = open(os.path.join(tempfile.gettempdir(), self.cloud_plugin_name, '__init__.py'), 'w')
        cloudinit.write('from %s import %s as delegate_class' % (self.cloud_plugin_name, self.cloud_plugin_name))
        cloudinit.close()
        # get a PluginManager instance and load plugin .info files
        self.plugin_mgr = PluginManager(plugin_path=tempfile.gettempdir())
        self.plugin_mgr.load()

    def tearDown(self):
        self.plugin_mgr = None
        shutil.rmtree(path=os.path.join(tempfile.gettempdir(), self.os_plugin_name), ignore_errors=True)
        shutil.rmtree(path=os.path.join(tempfile.gettempdir(), self.cloud_plugin_name), ignore_errors=True)
        self.os_info_file.close()
        self.cloud_info_file.close()

    def testMetadataForPlugin(self):
        os_metadata = self.plugin_mgr.metadata_for_plugin(self.os_plugin_name)
        self.assertDictEqual(os_metadata, INFO1)
        cloud_metadata = self.plugin_mgr.metadata_for_plugin(self.cloud_plugin_name)
        self.assertDictEqual(cloud_metadata, INFO2)

    @unittest.skip('See comments in code.')
    def testPluginForTarget(self):
        # This code is flawed...
        os_plugin = self.plugin_mgr.plugin_for_target(('osfoo', 'osbar', 'osbaz'))
        self.assertEqual(os_plugin.__class__.__name__, self.os_plugin_name)
        cloud_plugin = self.plugin_mgr.plugin_for_target(('cloudfoo', 'cloudbar', 'cloudbaz'))
        self.assertEqual(cloud_plugin.__class__.__name__, self.cloud_plugin_name)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testReservationManager
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
import logging
import os
import time
from imgfac.ReservationManager import ReservationManager
from threading import Thread, Semaphore


class testReservationManager(unittest.TestCase):
    """ TODO: Docstring for testReservationManager  """

    def __init__(self, methodName='runTest'):
        super(testReservationManager, self).__init__(methodName)
        logging.basicConfig(level=logging.NOTSET,
                            format='%(asctime)s \
                                    %(levelname)s \
                                    %(name)s \
                                    pid(%(process)d) \
                                    Message: %(message)s',
                            filename='/tmp/imagefactory-unittests.log')

    def setUp(self):
        self.test_path = '/tmp/imagefactory.unittest.ReservationManager'
        self.test_file = '%s/reservation.test' % self.test_path
        os.mkdir(self.test_path)
        fstat = os.statvfs(self.test_path)
        self.max_free = fstat.f_bavail * fstat.f_frsize
        self.min_free = self.max_free / 2
        self.res_mgr = ReservationManager()

    def tearDown(self):
        self.res_mgr.remove_path(self.test_path)
        os.rmdir(self.test_path)
        del self.res_mgr

    def testSingleton(self):
        """
        Prove this class produces a singelton object.
        """
        self.assertEqual(id(self.res_mgr), id(ReservationManager()))

    def testDefaultMinimumProperty(self):
        """
        TODO: Docstring for testDefaultMinimumProperty
        """
        self.res_mgr.default_minimum = self.min_free
        self.assertEqual(self.min_free, self.res_mgr.default_minimum)

    def testAddRemovePath(self):
        """
        TODO: Docstring for testRemovePath
        """
        path = '/'
        # start off with nothing tracked
        self.assertFalse(path in self.res_mgr.available_space)
        # add / and check that it's listed in the dictionary returned by
        # available_space
        self.res_mgr.add_path('/')
        self.assertTrue(path in self.res_mgr.available_space)
        # remove / and check that it's no longer listed in the dictionary
        # returned by available_space
        self.res_mgr.remove_path('/')
        self.assertFalse(path in self.res_mgr.available_space)

    def testReserveSpaceForFile(self):
        """
        TODO: Docstring for testReserveSpaceForFile
        """
        self.res_mgr.default_minimum = self.min_free
        size = self.min_free / 10
        result = self.res_mgr.reserve_space_for_file(size, self.test_file)
        self.assertTrue(result)
        self.assertTrue(self.test_file in self.res_mgr.reservations)

    def testReserveSpaceForFileThatIsTooBig(self):
        """
        TODO: Docstring for testReserveSpaceForFile
        """
        size = self.max_free * 10
        result = self.res_mgr.reserve_space_for_file(size, self.test_file)
        self.assertFalse(result)
        self.assertFalse(self.test_file in self.res_mgr.reservations)

    def testCancelReservationForFile(self):
        """
        TODO: Docstring for testCancelReservationForFile
        """
        size = self.min_free / 10
        self.res_mgr.default_minimum = self.min_free
        if(self.res_mgr.reserve_space_for_file(size, self.test_file)):
            self.assertTrue(self.test_file in self.res_mgr.reservations)
            self.res_mgr.cancel_reservation_for_file(self.test_file)
            self.assertFalse(self.test_file in self.res_mgr.reservations)
        else:
            self.fail('Failed to reserve space...')

    def testCancelNonExistentReservation(self):
        """
        TODO: Docstring for testCancelNonExistentReservation
        """
        self.assertRaises((TypeError, KeyError), self.res_mgr.cancel_reservation_for_file, *('/tmp/not.there', False))

    def testAvailableSpaceForPath(self):
        """
        TODO: Docstring for testAvailableSpace
        """
        size = self.min_free / 10
        self.res_mgr.add_path(self.test_path, self.min_free)
        available = self.res_mgr.available_space_for_path(self.test_path)
        if(self.res_mgr.reserve_space_for_file(size, self.test_file)):
            now_available = self.res_mgr.available_space_for_path(self.test_path)
            self.assertEqual(now_available, (available - size))
        else:
            self.fail('Failed to reserve space...')

    def testJobQueue(self):
        """
        TODO: Docstring for testJobQueue
        """
        job_number = 3
        job_threads = []
        job_output = []
        for i in range(job_number):
            for name in ReservationManager().queues:
                job_threads.append(MockJob(kwargs=dict(qname=name, position=i, output=job_output)))
        for job in job_threads:
            job.start()
        for job in job_threads:
            if job.isAlive():
                job.join()
        #self.log.info(job_output)
        self.assertEqual((3 * job_number * len(ReservationManager().queues)), len(job_output))


class MockJob(Thread):
    """ TODO: Docstring for MockJob  """

    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super(MockJob, self).__init__(group=None, target=None, name=None, args=(), kwargs={})
        self.qname = kwargs['qname']
        self.position = kwargs['position']
        self.output = kwargs['output']

    def run(self):
        resmgr = ReservationManager()
        str_args = (self.qname, self.position)
        self.output.append('enter-%s-%d' % str_args)
        resmgr.enter_queue(self.qname)
        self.output.append('start-%s-%d' % str_args)
        if(self.qname == 'local'):
            time.sleep(4)
        else:
            time.sleep(1)
        self.output.append('exit-%s-%d' % str_args)
        resmgr.exit_queue(self.qname)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testTemplate
#!/usr/bin/env python
# encoding: utf-8

#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import unittest
import logging
import tempfile
from imgfac.Template import Template
from imgfac.ImageWarehouse import ImageWarehouse
from imgfac.ApplicationConfiguration import ApplicationConfiguration
from imgfac.builders.Mock_Builder import Mock_Builder


class testTemplate(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.NOTSET, format='%(asctime)s %(levelname)s %(name)s pid(%(process)d) Message: %(message)s', filename='/tmp/imagefactory-unittests.log')
        self.warehouse = ImageWarehouse(ApplicationConfiguration().configuration["warehouse"])
        self.template_xml = "<template>This is a test template.  There is not much to it.</template>"

    def tearDown(self):
        del self.warehouse
        del self.template_xml

    def testTemplateFromUUID(self):
        template_id = self.warehouse.store_template(self.template_xml)
        template = Template(template_id)
        self.assertEqual(template_id, template.identifier)
        self.assertEqual(self.template_xml, template.xml)
        self.assertFalse(template.url)

    def testTemplateFromImageID(self):
        template_id = self.warehouse.store_template(self.template_xml)
        template = Template(template_id)
        target = "mock"
        builder = Mock_Builder(self.template_xml, target)
        builder.build_image()
        metadata = dict(template=template_id, target=target, icicle="None", target_parameters="None")
        self.warehouse.store_target_image(builder.new_image_id, builder.image, metadata=metadata)
        image_template = Template(builder.new_image_id)
        self.assertEqual(template_id, image_template.identifier)
        self.assertEqual(self.template_xml, image_template.xml)
        self.assertFalse(template.url)

    def testTemplateFromXML(self):
        template = Template(self.template_xml)
        self.assertEqual(self.template_xml, template.xml)
        self.assertFalse(template.identifier)
        self.assertFalse(template.url)

    def testTemplateFromURL(self):
        template_id = self.warehouse.store_template(self.template_xml)
        template_url = "%s/%s/%s" % (self.warehouse.url, self.warehouse.template_bucket, template_id)
        template = Template(template_url)
        self.assertEqual(template_url, template.url)
        self.assertEqual(template_id, template.identifier)
        self.assertEqual(self.template_xml, template.xml)

    def testTemplateFromPath(self):
        (fd, template_path) = tempfile.mkstemp(prefix = "test_image_factory-")
        os.write(fd, self.template_xml)
        os.close(fd)

        template = Template(template_path)
        self.assertFalse(template.url)
        self.assertFalse(template.identifier)
        self.assertEqual(self.template_xml, template.xml)

        os.remove(template_path)

    def testTemplateStringRepresentation(self):
        template = Template(self.template_xml)
        self.assertEqual(self.template_xml, repr(template))
        self.assertEqual(self.template_xml, str(template))
        self.assertEqual(self.template_xml, "%r" % (template, ))
        self.assertEqual(self.template_xml, "%s" % (template, ))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = consumer-service
#   Copyright 2011 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import win32serviceutil
import win32service
import win32event
import win32api
import win32security
import win32con
import win32process
import win32pipe
import win32file
import win32net
import win32netcon
import msvcrt
import os
import threading
import servicemanager
import socket
import platform
from qpid.messaging import *
from qpid.util import URL
import base64
import random
import string

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "StartConsumer"
    _svc_display_name_ = "Consumer Service"
    _svc_description_ = "Consumer service to process Qpid commands"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None,0,0,None)
        socket.setdefaulttimeout(60)


    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))

        
        # Create an Administrator account to be impersonated and used for the process
        def create_user():
            params={}
            params['name']= 'RHAdmin'
            digits = "".join( [random.choice(string.digits) for i in range(10)] )
            chars_lower = ''.join( [random.choice(string.ascii_lowercase) for i in range(10)] )
            chars_upper = ''.join( [random.choice(string.ascii_uppercase) for i in range(10)] ) 
            params['password']= digits+chars_lower+chars_upper
            params['password'] = ''.join([str(w) for w in random.sample(params['password'], len(params['password']))])
            params['flags']= win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UF_SCRIPT
            params['priv'] = win32netcon.USER_PRIV_USER

            user = win32net.NetUserAdd(None, 1, params)
            domain = socket.gethostname()
            data = [ {'domainandname' : domain+'\\RHAdmin'} ]
            win32net.NetLocalGroupAddMembers(None, 'Administrators', 3, data)
            return params['password']
        
        try:
            win32net.NetUserDel(None, 'RHAdmin')
            Password = create_user()
        except:
            Password = create_user()
        

        token = win32security.LogonUser('RHAdmin', None, Password, \
        	       win32con.LOGON32_LOGON_INTERACTIVE,
                    win32con.LOGON32_PROVIDER_DEFAULT)
        win32security.ImpersonateLoggedOnUser(token)
        self.main(token)

    def main(self, token):

        connection = Connection('localhost', port=5672)
        connection.open()
        session = connection.session(str(uuid4()))

        receiver = session.receiver('amq.topic')
        local_ip = socket.gethostbyname(socket.gethostname())
        localhost_name = platform.uname()[1]



        def make_inheritable(token):
            """Return a duplicate of handle, which is inheritable"""
            return win32api.DuplicateHandle(win32api.GetCurrentProcess(), token,
                                   win32api.GetCurrentProcess(), 0, 1,
                                   win32con.DUPLICATE_SAME_ACCESS)

        while True:
            message = receiver.fetch()
            session.acknowledge()
            sender = session.sender(message.reply_to)
            command = base64.b64decode(message.content)
            if command.startswith('winrs' or 'winrm') != True or command.find('-r:') == -1 or command.find('localhost') != -1 or command.find(localhost_name) != -1 or command.find(local_ip) != -1:
                sender.send(Message(base64.b64encode('Commands against the proxy are not accepted')))
            else:
                #Start the process:

                # First let's create the communication pipes used by the process
                # we need to have the pipes inherit the rights from token
                stdin_read, stdin_write = win32pipe.CreatePipe(None, 0)
                stdin_read = make_inheritable(stdin_read)

                stdout_read, stdout_write = win32pipe.CreatePipe(None, 0)
                stdout_write = make_inheritable(stdout_write)

                stderr_read, stderr_write = win32pipe.CreatePipe(None, 0)
                stderr_write = make_inheritable(stderr_write)

                # Set start-up parameters the process will use.
                #Here we specify the pipes for input, output and error.
                si = win32process.STARTUPINFO()
                si.dwFlags = win32con.STARTF_USESTDHANDLES
                si.hStdInput = stdin_read
                si.hStdOutput = stdout_write
                si.hStdError = stderr_write


                procArgs = (None,  # appName
                    command,  # commandLine
                    None,  # processAttributes
                    None,  # threadAttributes
                    1,  # bInheritHandles
                    0,  # dwCreationFlags
                    None,  # newEnvironment
                    None,  # currentDirectory
                    si)  # startupinfo

                # CreateProcessAsUser takes the first parameter the token,
                # this way the process will impersonate a user
                try:
                    hProcess, hThread, PId, TId =  win32process.CreateProcessAsUser(token, *procArgs)

                    hThread.Close()

                    if stdin_read is not None:
                        stdin_read.Close()
                    if stdout_write is not None:
                        stdout_write.Close()
                    if stderr_write is not None:
                        stderr_write.Close()

                    stdin_write = msvcrt.open_osfhandle(stdin_write.Detach(), 0)
                    stdout_read = msvcrt.open_osfhandle(stdout_read.Detach(), 0)
                    stderr_read = msvcrt.open_osfhandle(stderr_read.Detach(), 0)


                    stdin_file = os.fdopen(stdin_write, 'wb', 0)
                    stdout_file = os.fdopen(stdout_read, 'rU', 0)
                    stderr_file = os.fdopen(stderr_read, 'rU', 0)

                    def readerthread(fh, buffer):
                        buffer.append(fh.read())

                    def translate_newlines(data):
                        data = data.replace("\r\n", "\n")
                        data = data.replace("\r", "\n")
                        return data

                    def wait():
                        """Wait for child process to terminate.  Returns returncode
                        attribute."""
                        win32event.WaitForSingleObject(hProcess,
                                                        win32event.INFINITE)
                        returncode = win32process.GetExitCodeProcess(hProcess)
                        return returncode


                    def communicate():

                        if stdout_file:
                            stdout = []
                            stdout_thread = threading.Thread(target=readerthread,
                                                             args=(stdout_file, stdout))
                            stdout_thread.setDaemon(True)
                            stdout_thread.start()
                        if stderr_file:
                            stderr = []
                            stderr_thread = threading.Thread(target=readerthread,
                                                             args=(stderr_file, stderr))
                            stderr_thread.setDaemon(True)
                            stderr_thread.start()

                        stdin_file.close()

                        if stdout_file:
                            stdout_thread.join()
                        if stderr_file:
                            stderr_thread.join()

                        if stdout is not None:
                            stdout = stdout[0]
                        if stderr is not None:
                            stderr = stderr[0]

                        if stdout:
                            stdout = translate_newlines(stdout)
                        if stderr:
                            stderr = translate_newlines(stderr)

                        return_code = wait()
                        return (stdout, stderr, return_code)

                    ret_stdout, ret_stderr, retcode =  communicate()


                    result = Message(base64.b64encode(str(ret_stdout)))
                    result.properties["retcode"] = base64.b64encode(str(retcode))
                    if ret_stderr:
                        result.properties["stderr"] = base64.b64encode(str(ret_stderr))
                    else:
                        result.properties["stderr"] = base64.b64encode('')

                    sender.send(result)

                except Exception as exception_message:
                    result = Message(base64.b64encode(''))
                    result.properties["retcode"] = base64.b64encode(str(exception_message[0]))
                    result.properties["stderr"] = base64.b64encode(str(exception_message[2]))

                    sender.send(result)


########NEW FILE########
