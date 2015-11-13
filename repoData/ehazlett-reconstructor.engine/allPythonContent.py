__FILENAME__ = core
#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import os
import tempfile
import logging
import shutil
from subprocess import Popen, PIPE, STDOUT, call
import sys

class BaseDistro(object):
    """
    Core distro class

    """
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger('distro.base')
        self._name = kwargs.get('name', 'Reconstructor Live CD')
        self._arch = kwargs.get('arch', 'i386')
        self._codename = kwargs.get('codename')
        self._hostname = kwargs.get('hostname', 'live')
        self._live_user = kwargs.get('live_user', 'liveuser')
        self._url = kwargs.get('url', 'http://reconstructor.org')
        self._work_dir = kwargs.get('work_dir', tempfile.mkdtemp())
        self._chroot_dir = os.path.join(self._work_dir, 'chroot')
        self._iso_dir = os.path.join(self._work_dir, 'iso')
        self._skip_cleanup = kwargs.get('skip_cleanup', False)
        self._packages = kwargs.get('packages', '').split(',')
        self._output_file = kwargs.get('output_file')

    def _run_command(self, cmd):
        """
        Runs a command from the host machine

        :param cmd: Command to run

        """
        out = call(cmd, shell=True)
        return out

    def _run_chroot_command(self, cmd):
        """
        Runs a command inside the chroot environment

        :param cmd: Command to run

        """
        chroot_cmd = "chroot {0} /bin/bash -c \"{1}\"".format(
            self._chroot_dir, cmd)
        out = call(chroot_cmd, shell=True)
        return out

    def _init(self):
        if not os.path.exists(self._chroot_dir):
            os.makedirs(self._chroot_dir)
        if not os.path.exists(self._iso_dir):
            os.makedirs(self._iso_dir)

    def setup(self):
        """
        Override this for initial setup

        """
        raise NotImplementedError

    def build(self):
        """
        Override this for building the distribution

        """
        raise NotImplementedError

    def add_packages(self, packages=[]):
        """
        Override this for adding packages

        """
        raise NotImplementedError

    def run_chroot_script(self):
        """
        Override this for running scripts in the chroot environment

        """
        raise NotImplementedError

    def teardown(self):
        """
        Override this for environment teardown
        """
        pass

    def cleanup(self):
        """
        Override this for cleaning up

        """
        self.log.info('Cleaning up...')
        if os.path.exists(self._work_dir):
            self.log.debug('Removing work dir: {0}'.format(self._work_dir))
            shutil.rmtree(self._work_dir)

    def run(self):
        self._init()
        self.setup()
        self.teardown()
        self.build()
        if not self._skip_cleanup:
            self.cleanup()
        else:
            self.log.info('Skipping cleanup ; work directory is {0}'.format(
                self._work_dir))

########NEW FILE########
__FILENAME__ = ubuntu
#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import os
from base import BaseDistro
from subprocess import Popen, PIPE, STDOUT
import logging
import shutil

class Ubuntu(BaseDistro):
    """
    Core distro class

    """
    def __init__(self, *args, **kwargs):
        super(Ubuntu, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('distro.ubuntu')

    def setup(self):
        self.log.debug('Name: {0}'.format(self._name))
        self.log.debug('Codename: {0}'.format(self._codename))
        self.log.debug('Architecture: {0}'.format(self._arch))
        self.log.debug('Working directory: {0}'.format(self._work_dir))
        self.log.info('Setting up base distro environment')
        cmd = "debootstrap --arch={0} --exclude=atd {1} {2}".format(self._arch,
            self._codename, self._chroot_dir)
        self._run_command(cmd)
        self._mount_dev()
        self._setup_network()
        self._setup_apt()
        self._setup_machine()
        self._install_extra_packages()
        self._setup_iso_dir()

    def _mount_dev(self):
        self.log.debug('Mounting filesystems')
        cmd = "mount --bind /dev {0}/dev".format(self._chroot_dir)
        self._run_command(cmd)
        cmd = "mkdir -p /proc ; mount none -t proc /proc"
        self._run_chroot_command(cmd)
        cmd = "mount none -t sysfs /sys"
        self._run_chroot_command(cmd)
        cmd = "mount none -t devpts /dev/pts"
        self._run_chroot_command(cmd)

    def _setup_network(self):
        self.log.debug('Setting up hosts and DNS resolving')
        cmd = "cp /etc/hosts {0}/etc/".format(
            self._chroot_dir)
        self._run_command(cmd)
        cmd = "cp /etc/resolv.conf {0}/etc/".format(
            self._chroot_dir)
        self._run_command(cmd)

    def _setup_apt(self):
        self.log.debug('Setting up APT')
        tmpl = """deb http://us.archive.ubuntu.com/ubuntu/ {0} main
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} main
deb http://us.archive.ubuntu.com/ubuntu/ {0} universe
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} universe
deb http://us.archive.ubuntu.com/ubuntu/ {0} multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} multiverse
deb http://us.archive.ubuntu.com/ubuntu/ {0} restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ {0} restricted
""".format(self._codename)
        cmd = 'echo "{0}" > {1}/etc/apt/sources.list'.format(tmpl,
            self._chroot_dir)
        self._run_command(cmd)
        self._run_chroot_command('apt-get update')

    def _setup_machine(self):
        self.log.debug('Configuring machine id')
        # setup machine id
        cmd = "dbus-uuidgen > /var/lib/dbus/machine-id"
        self._run_chroot_command(cmd)
        cmd = "mv /sbin/initctl /sbin/initctl.bkup"
        self._run_chroot_command(cmd)
        cmd = "ln -sf /bin/true /sbin/initctl"
        self._run_chroot_command(cmd)
        open('{0}/etc/hostname'.format(self._chroot_dir), 'w').write(
            self._hostname)
        # policy file to prevent daemons from starting
        policy_file = '{0}/usr/sbin/policy-rc.d'.format(self._chroot_dir)
        with open(policy_file, 'w') as f:
            f.write('#!/bin/sh\nexit 101\n')
        os.chmod(policy_file, 0755)
        # install dbus
        self.add_packages(['dbus'])
        # install packages for live env
        self.add_packages(['ubuntu-minimal', 'casper', 'psmisc'])
        self.add_packages(['discover', 'laptop-detect', 'os-prober'])
        # set grub-pc selections for automated
        grub_pc_selections = """grub-pc grub-pc/kopt_extracted  boolean false
grub-pc grub2/kfreebsd_cmdline  string
grub-pc grub2/device_map_regenerated    note
grub-pc grub-pc/install_devices	multiselect /dev/sda
grub-pc grub-pc/postrm_purge_boot_grub  boolean false
grub-pc grub-pc/install_devices_failed_upgrade  boolean true
grub-pc grub2/linux_cmdline string
grub-pc grub-pc/install_devices_empty   boolean false
grub-pc grub2/kfreebsd_cmdline_default  string  quiet
grub-pc grub-pc/install_devices_failed  boolean false
grub-pc grub-pc/install_devices_disks_changed   multiselect
grub-pc grub2/linux_cmdline_default string  quiet
grub-pc grub-pc/chainload_from_menu.lst boolean true
grub-pc grub-pc/hidden_timeout  boolean true
grub-pc grub-pc/mixed_legacy_and_grub2  boolean true
grub-pc grub-pc/timeout string  10"""
        tmpfile_name = '/tmp/grub_pc.debconf'
        tmpfile = '{0}{1}'.format(self._chroot_dir, tmpfile_name)
        with open(tmpfile, 'w') as f:
            f.write(grub_pc_selections)
        cmd = "cat {0} | debconf-set-selections".format(tmpfile_name)
        self._run_chroot_command(cmd)
        self.add_packages(['grub2', 'grub-pc'])
        self.add_packages(['linux-image-generic'])
        cmd = "DEBCONF_FRONTEND=noninteractive apt-get install -y " \
            "--no-install-recommends network-manager"
        self._run_chroot_command(cmd)

    def _setup_iso_dir(self):
        dirs = ['casper', 'isolinux', 'install', '.disk']
        for d in dirs:
            fdir = os.path.join(self._iso_dir, d)
            if not os.path.exists(fdir):
                os.makedirs(fdir)
        # copy kernel and initrd
        cmd = "cp {0}/boot/vmlinuz-*.*.*-**-generic {1}/casper/vmlinuz".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp {0}/boot/initrd.img-*.*.*-**-generic {1}/casper/initrd.img".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp /usr/lib/syslinux/isolinux.bin {1}/isolinux/".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "echo \"***** {0} *****\" > {1}/isolinux/isolinux.txt".format(
            self._name, self._iso_dir)
        self._run_command(cmd)
        boot_tmpl = """DEFAULT live
LABEL live
  menu label ^Start or install Ubuntu Remix
  kernel /casper/vmlinuz
  append  file=/cdrom/preseed/ubuntu.seed boot=casper initrd=/casper/initrd.img quiet splash --
LABEL check
  menu label ^Check CD for defects
  kernel /casper/vmlinuz
  append  boot=casper integrity-check initrd=/casper/initrd.img quiet splash --
LABEL hd
  menu label ^Boot from first hard disk
  localboot 0x80
  append -
DISPLAY isolinux.txt
TIMEOUT 300
PROMPT 1
"""
        tmpfile = '{0}/isolinux/isolinux.cfg'.format(self._iso_dir)
        with open(tmpfile, 'w') as f:
            f.write(boot_tmpl)
        cmd = "chroot {0} dpkg-query -W --showformat='${{Package}} ${{Version}}\n' | sudo tee {1}/casper/filesystem.manifest".format(self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "cp -v {0}/casper/filesystem.manifest {0}/casper/filesystem.manifest-desktop".format(
            self._iso_dir)
        self._run_command(cmd)

    def _install_extra_packages(self):
        if self._packages:
            self.log.info('Installing extra packages')
            self.log.debug('Packages: {0}'.format(','.join(self._packages)))
            self.add_packages(self._packages)

    def _teardown_machine(self):
        self.log.debug('Removing machine id')
        cmd = "rm -f /var/lib/dbus/machine-id"
        self._run_chroot_command(cmd)
        self.log.debug('Removing initctl diversion')
        cmd = "rm /sbin/initctl"
        self._run_chroot_command(cmd)
        cmd = "mv /sbin/initctl.bkup /sbin/initctl"
        self._run_chroot_command(cmd)
        policy_file = '{0}/usr/sbin/policy-rc.d'.format(self._chroot_dir)
        os.remove(policy_file)

    def _teardown_network(self):
        self.log.debug('Removing network config')
        cmd = "rm -rf {0}/etc/hosts".format(
            self._chroot_dir)
        self._run_chroot_command(cmd)
        cmd = "rm -rf {0}/etc/resolv.conf".format(
            self._chroot_dir)
        self._run_chroot_command(cmd)

    def _unmount_dev(self):
        self.log.debug('Stopping processes in chroot')
        cmd = "fuser -k {0}/".format(self._chroot_dir)
        self._run_command(cmd)
        self.log.debug('Unmounting filesystems')
        cmd = "umount -lf /proc"
        self._run_chroot_command(cmd)
        cmd = "umount -lf /sys"
        self._run_chroot_command(cmd)
        cmd = "umount -lf /dev/pts"
        self._run_command(cmd)
        cmd = "umount -lf {0}/dev".format(self._chroot_dir)
        self._run_command(cmd)

    def add_packages(self, packages=[]):
        pkg_list = ' '.join(packages)
        cmd = "LC_ALL=C DEBIAN_PRIORITY=critical DEBCONF_FRONTEND=noninteractive apt-get install -y --force-yes {0}".format(
            pkg_list)
        self._run_chroot_command(cmd)

    def build(self):
        self.log.info('Building Live Filesystem ; this will take a while')
        squashfs_file = os.path.join(self._iso_dir, 'casper/filesystem.squashfs')
        if os.path.exists(squashfs_file):
            os.remove(squashfs_file)
        cmd = "mksquashfs {0} {1}/casper/filesystem.squashfs".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        cmd = "printf $(sudo du -sx --block-size=1 {0} | cut -f1) > {1}/casper/filesystem.size".format(
            self._chroot_dir, self._iso_dir)
        self._run_command(cmd)
        defines_tmpl = """#define DISKNAME  {0}
#define TYPE  binary
#define TYPEbinary  1
#define ARCH  {1}
#define ARCH{1}  1
#define DISKNUM  1
#define DISKNUM1  1
#define TOTALNUM  0
#define TOTALNUM0  1
""".format(self._name, self._arch)
        defines_file = os.path.join(self._iso_dir, 'README.diskdefines')
        with open(defines_file, 'w') as f:
            f.write(defines_tmpl)
        # disk info
        open(os.path.join(self._iso_dir, '.disk/base_installable'), 'w').write('')
        open(os.path.join(self._iso_dir, '.disk/cd_type'), 'w').write(
            'full_cd/single')
        open(os.path.join(self._iso_dir, '.disk/info'), 'w').write(
            self._name)
        open(os.path.join(self._iso_dir, '.disk/release_notes_url'), 'w').write(
            self._url)
        open(os.path.join(self._iso_dir, '.disk/reconstructor'), 'w').write(
            'Built by Reconstructor')
        # generate md5s
        cmd = "(cd {0} ; find . -type f -print0 | xargs -0 md5sum | grep -v \"\./md5sum.txt\" > md5sum.txt)".format(self._iso_dir)
        self._run_command(cmd)
        cmd = "cd {0} ; mkisofs -r -V \"{1}\" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o \"{2}\" .".format(
            self._iso_dir, self._name, self._output_file)
        self._run_command(cmd)
        cmd = "md5sum {0}".format(self._output_file)
        self._run_command(cmd)

    def run_chroot_script(self):
        raise NotImplementedError
    
    def teardown(self):
        self._teardown_network()
        self._teardown_machine()
        self._unmount_dev()

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from optparse import OptionParser
import logging
import os
import sys
import tempfile
from distro import Ubuntu

LOG_FILE='reconstructor.log'
LOG_CONFIG=logging.basicConfig(level=logging.DEBUG, # always log debug to file
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d-%Y %H:%M:%S',
                    filename=LOG_FILE,
                    filemode='w')

logging.config=LOG_CONFIG
console = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)-5s %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def main():
    log = logging.getLogger('reconstructor.cli')

    parser = OptionParser()
    parser.add_option('--name', dest='name', default='Reconstructor Live CD',
        help='Distribution Name')
    parser.add_option('--hostname', dest='hostname', default='live',
        help='Distribution Hostname')
    parser.add_option('--arch', dest='arch', default='i386',
        help='Distribution Architecture (i.e. i386, amd64)')
    parser.add_option('--codename', dest='codename', default=None,
        help='Distribution Codename (i.e. precise)')
    parser.add_option('--output-file', dest='output_file', default=None,
        help='Output file')
    parser.add_option('--url', dest='url', default='http://reconstructor.org',
        help='Distribution URL')
    parser.add_option('--debug', dest='debug', action='store_true',
        default=False, help='Show debug')
    parser.add_option('--packages', dest='packages',
        default='',
        help='Comma separated list of additional packages to install')
    parser.add_option('--work-dir', dest='work_dir',
        default=tempfile.mkdtemp())
    parser.add_option('--skip-cleanup', dest='skip_cleanup', action='store_true',
        default=False, help='Skip removing work directory')
    # parse
    opts, args = parser.parse_args()
    # set log level
    level = logging.INFO
    if opts.debug:
        level = logging.DEBUG
    log.setLevel(level)
    console.setLevel(level)
    # check args
    if not opts.codename:
        log.error('You must specify a codename')
        sys.exit(1)
    if not opts.output_file:
        log.error('You must specify an output file')
        sys.exit(1)
    # select distro
    distros = {
        'precise': Ubuntu(**vars(opts)),
    }
    # run
    distros[opts.codename].run()
if __name__=='__main__':
    main()


########NEW FILE########
