__FILENAME__ = example
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

# the class name determines the plugin name
# if you want to override it simply provide a @classmethod name()
# that returns the name you want
class example(Plugin, RedHatPlugin):
    '''This is the description for the example plugin'''
    # Plugin developers want to override setup() from which they will call
    # add_copy_spec() to collect files and collectExtOutput() to collect programs
    # output.

    # Add your options here, indicate whether they are slow to run, and set
    # whether they are enabled by default
    # each option is a tuple of the following format:
    # (name, description, fast or slow, default value)
    # each option will be addressable like -k name=value
    option_list = [("init.d",  'Gathers the init.d directory', 'slow', 0),
                  ('follicles', 'Gathers information about each follicle on every toe', 'slow', 0),
                  ('color', 'Gathers toenail polish color', 'fast', 0)]

    def setup(self):
        ''' First phase - Collect all the information we need.
        Directories are copied recursively. arbitrary commands may be
        executed using the collectExtOutput() method. Information is
        automatically saved, and links are presented in the report to each
        file or directory which has been copied to the saved tree. Also, links
        are provided to the output from each command.
        '''
        # Here's how to copy files and directory trees
        self.add_copy_spec("/etc/hosts")

        with open("/proc/cpuinfo") as f:
            for line in f:
                if "vendor_id" in line:
                    self.add_alert("Vendor ID string is: %s <br>\n" % line)

        # Here's how to test your options and execute if enabled
        if self.option_enabled("init.d"):
            self.add_copy_spec("/etc/init.d") # copies a whole directory tree

        # Here's how to execute a command
        self.collectExtOutput("/bin/ps -ef")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = archive
## Copyright (C) 2012 Red Hat, Inc.,
##   Jesse Jaggars <jjaggars@redhat.com>
##   Bryn M. Reeves <bmr@redhat.com>
##
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
import os
import time
import tarfile
import zipfile
import shutil
import logging
import shlex
import re
import codecs
# required for compression callout (FIXME: move to policy?)
from subprocess import Popen, PIPE

try:
    import selinux
except ImportError:
    pass

# PYCOMPAT
import six
if six.PY3:
    long = int

class Archive(object):

    @classmethod
    def archive_type(class_):
        """Returns the archive class's name as a string.
        """
        return class_.__name__

    log = logging.getLogger("sos")

    _name = "unset"

    def _format_msg(self,msg):
        return "[archive:%s] %s" % (self.archive_type(), msg)

    def log_error(self, msg):
        self.log.error(self._format_msg(msg))

    def log_warn(self,msg):
        self.log.warning(self._format_msg(msg))

    def log_info(self, msg):
        self.log.info(self._format_msg(msg))

    def log_debug(self, msg):
        self.log.debug(self._format_msg(msg))

    # this is our contract to clients of the Archive class hierarchy.
    # All sub-classes need to implement these methods (or inherit concrete
    # implementations from a parent class.
    def add_file(self, src, dest=None):
        raise NotImplementedError

    def add_string(self, content, dest):
        raise NotImplementedError

    def add_link(self, source, link_name):
        raise NotImplementedError

    def add_dir(self, path):
        raise NotImplementedError

    def get_tmp_dir(self):
        """Return a temporary directory that clients of the archive may
        use to write content to. The content of the path is guaranteed
        to be included in the generated archive."""
        raise NotImplementedError

    def get_archive_path(self):
        """Return a string representing the path to the temporary
        archive. For archive classes that implement in-line handling
        this will be the archive file itself. Archives that use a
        directory based cache prior to packaging should return the
        path to the temporary directory where the report content is
        located"""
        pass

    def cleanup(self):
        """Clean up any temporary resources used by an Archive class."""
        pass

    def finalize(self, method):
        """Finalize an archive object via method. This may involve creating
        An archive that is subsequently compressed or simply closing an
        archive that supports in-line handling. If method is automatic then
        the following technologies are tried in order: xz, bz2 and gzip"""

        self.close()


class FileCacheArchive(Archive):

    _tmp_dir = ""
    _archive_root = ""
    _archive_name = ""

    def __init__(self, name, tmpdir):
        self._name = name
        self._tmp_dir = tmpdir
        self._archive_root = os.path.join(tmpdir, name)
        os.makedirs(self._archive_root, 0o700)
        self.log_info("initialised empty FileCacheArchive at '%s'" %
                       (self._archive_root,))

    def dest_path(self, name):
        if os.path.isabs(name):
            name = name.lstrip(os.sep)
        return (os.path.join(self._archive_root, name))

    def _check_path(self, dest):
        dest_dir = os.path.split(dest)[0]
        if not dest_dir:
            return
        if not os.path.isdir(dest_dir):
            self._makedirs(dest_dir)

    def add_file(self, src, dest=None):
        if not dest:
            dest = src
        dest = self.dest_path(dest)
        self._check_path(dest)
        try:
            shutil.copy(src, dest)
        except IOError as e:
            self.log_debug("caught '%s' copying '%s'" % (e, src))
        try:
            shutil.copystat(src, dest)
        except PermissionError:
            # SELinux xattrs in /proc and /sys throw this
            pass
        try:
            stat = os.stat(src)
            os.chown(dest, stat.st_uid, stat.st_gid)
        except Exception as e:
            self.log_debug("caught '%s' setting ownership of '%s'" % (e, dest))
        self.log_debug("added '%s' to FileCacheArchive '%s'" %
                       (src, self._archive_root))

    def add_string(self, content, dest):
        src = dest
        dest = self.dest_path(dest)
        self._check_path(dest)
        f = codecs.open(dest, 'w', encoding='utf-8')
        f.write(content)
        if os.path.exists(src):
            try:
                shutil.copystat(src, dest)
            except PermissionError:
                pass
        self.log_debug("added string at '%s' to FileCacheArchive '%s'"
                       % (src, self._archive_root))

    def add_link(self, source, link_name):
        dest = self.dest_path(link_name)
        self._check_path(dest)
        if not os.path.exists(dest):
            os.symlink(source, dest)
        self.log_debug("added symlink at '%s' to '%s' in FileCacheArchive '%s'"
                       % (dest, source, self._archive_root))

    def add_dir(self, path):
        self.makedirs(path)

    def _makedirs(self, path, mode=0o700):
        os.makedirs(path, mode)

    def get_tmp_dir(self):
        return self._archive_root

    def get_archive_path(self):
        return self._archive_root

    def makedirs(self, path, mode=0o700):
        self._makedirs(self.dest_path(path))
        self.log_debug("created directory at '%s' in FileCacheArchive '%s'"
                       % (path, self._archive_root))

    def open_file(self, path):
        path = self.dest_path(path)
        return codecs.open(path, "r", encoding='utf-8')

    def cleanup(self):
        shutil.rmtree(self._archive_root)

    def finalize(self, method):
        self.log_info("finalizing archive '%s'" % self._archive_root)
        self._build_archive()
        self.cleanup()
        self.log_info("built archive at '%s' (size=%d)" % (self._archive_name,
                       os.stat(self._archive_name).st_size))
        return self._compress()


class TarFileArchive(FileCacheArchive):

    method = None
    _with_selinux_context = False

    def __init__(self, name, tmpdir):
        super(TarFileArchive, self).__init__(name, tmpdir)
        self._suffix = "tar"
        self._archive_name = os.path.join(tmpdir, self.name())

    def set_tarinfo_from_stat(self, tar_info, fstat, mode=None):
        tar_info.mtime = fstat.st_mtime
        tar_info.pax_headers['atime'] = "%.9f" % fstat.st_atime
        tar_info.pax_headers['ctime'] = "%.9f" % fstat.st_ctime
        if mode:
            tar_info.mode = mode
        else:
            tar_info.mode = fstat.st_mode
        tar_info.uid = fstat.st_uid
        tar_info.gid = fstat.st_gid

    # this can be used to set permissions if using the
    # tarfile.add() interface to add directory trees.
    def copy_permissions_filter(self, tarinfo):
        orig_path = tarinfo.name[len(os.path.split(self._name)[-1]):]
        if not orig_path:
            orig_path = self._archive_root
        try:
            fstat = os.stat(orig_path)
        except OSError:
            return tarinfo
        if self._with_selinux_context:
            context = self.get_selinux_context(orig_path)
            if(context):
                tarinfo.pax_headers['RHT.security.selinux'] = context
        self.set_tarinfo_from_stat(tarinfo, fstat)
        return tarinfo

    def get_selinux_context(self, path):
        try:
            (rc, c) = selinux.getfilecon(path)
            return c
        except:
            return None

    def name(self):
        return "%s.%s" % (self._name, self._suffix)

    def _build_archive(self):
        tar = tarfile.open(self._archive_name, mode="w")
        # We need to pass the absolute path to the archive root but we
        # want the names used in the archive to be relative.
        tar.add(self._archive_root, arcname=os.path.split(self._name)[1],
                filter=self.copy_permissions_filter)
        tar.close()

    def _compress(self):
        methods = ['xz', 'bzip2', 'gzip']
        if self.method in methods:
            methods = [self.method]

        last_error = Exception("compression failed for an unknown reason")

        for cmd in methods:
            suffix = "." + cmd.replace('ip', '')
            # use fast compression if using xz or bz2
            if cmd != "gzip":
                cmd = "%s -1" % cmd
            try:
                command = shlex.split("%s %s" % (cmd, self.name()))
                p = Popen(command,
                          stdout=PIPE,
                          stderr=PIPE,
                          bufsize=-1,
                          close_fds=True)
                stdout, stderr = p.communicate()
                if stdout:
                    self.log_info(stdout.decode('utf-8'))
                if stderr:
                    self.log_error(stderr.decode('utf-8'))
                self._suffix += suffix
                return self.name()
            except Exception as e:
                last_error = e
        raise last_error


class ZipFileArchive(Archive):

    def __init__(self, name):
        self._name = name
        try:
            import zlib
            self.compression = zipfile.ZIP_DEFLATED
        except:
            self.compression = zipfile.ZIP_STORED

        self.zipfile = zipfile.ZipFile(self.name(), mode="w",
                                       compression=self.compression)

    def name(self):
        return "%s.zip" % self._name

    def finalize(self, method):
        super(ZipFileArchive, self).finalize(method)
        return self.name()

    def add_file(self, src, dest=None):
        src = str(src)
        if dest:
            dest = str(dest)

        if os.path.isdir(src):
            # We may not need, this, but if we do I only want to do it
            # one time
            regex = re.compile(r"^" + src)
            for path, dirnames, filenames in os.walk(src):
                for filename in filenames:
                    filename = "/".join((path, filename))
                    if dest:
                        self.zipfile.write(filename, re.sub(regex, dest,
                                                            filename))
                    else:
                        self.zipfile.write(filename)
        else:
            if dest:
                self.zipfile.write(src, dest)
            else:
                self.zipfile.write(src)

    def add_string(self, content, dest):
        info = zipfile.ZipInfo(dest,
                               date_time=time.localtime(time.time()))
        info.compress_type = self.compression
        info.external_attr = 0o400 << long(16)
        self.zipfile.writestr(info, content)

    def open_file(self, name):
        try:
            self.zipfile.close()
            self.zipfile = zipfile.ZipFile(self.name(), mode="r")
            file_obj = self.zipfile.open(name)
            return file_obj
        finally:
            self.zipfile.close()
            self.zipfile = zipfile.ZipFile(self.name(), mode="a")

    def close(self):
        self.zipfile.close()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = abrt
## Copyright (C) 2010 Red Hat, Inc., Tomas Smetana <tsmetana@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists

class Abrt(Plugin, RedHatPlugin):
    """ABRT log dump
    """

    plugin_name = "abrt"
    packages = ('abrt-cli',)
    files = ('/var/spool/abrt',)

    option_list = [("backtraces", 'collect backtraces for every report',
                                                            'slow', False)]

    def do_backtraces(self):
        ret, output, rtime = self.call_ext_prog('sqlite3 '
                    + '/var/spool/abrt/abrt-db \'select UUID from abrt_v4\'')
        try:
            for uuid in output.split():
                self.add_cmd_output("abrt-cli -ib %s" % uuid,
                    suggest_filename=("backtrace_%s" % uuid))
        except IndexError:
            pass

    def setup(self):
        self.add_cmd_output("abrt-cli -lf", suggest_filename="abrt-log")
        if self.get_option('backtraces'):
            self.do_backtraces()



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = acpid
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Acpid(Plugin):
    plugin_name = "acpid"

class RedHatAcpid(Acpid, RedHatPlugin):
    """acpid related information
    """
    def setup(self):
        self.add_copy_specs([
            "/var/log/acpid*",
            "/etc/acpi/events/power.conf"])

class DebianAcpid(Acpid, DebianPlugin, UbuntuPlugin):
    """acpid related information for Debian and Ubuntu
    """
    def setup(self):
        self.add_copy_specs([
            "/etc/acpi/events/powerbtn*"])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = anaconda
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class Anaconda(Plugin, RedHatPlugin):
    """Anaconda / Installation information
    """

    plugin_name = 'anaconda'

    files = ('/var/log/anaconda.log',
             '/var/log/anaconda')

    def setup(self):

        paths = [
            "/root/anaconda-ks.cfg"]

        if os.path.isdir('/var/log/anaconda'):
            # new anaconda
            paths.append('/var/log/anaconda')
        else:
            paths = paths + \
                [ "/var/log/anaconda.*"
                "/root/install.log",
                "/root/install.log.syslog"]

        self.add_copy_specs(paths)

    def postproc(self):
        self.do_file_sub("/root/anaconda-ks.cfg",
                        r"(\s*rootpw\s*).*",
                        r"\1******")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = anacron

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Anacron(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ capture scheduled jobs information """
    
    plugin_name = 'anacron'

    # anacron may be provided by anacron, cronie-anacron etc.
    # just look for the configuration file which is common
    files = ('/etc/anacrontab',)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = apache
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Apache(Plugin):
    """Apache related information
    """
    plugin_name = "apache"

    option_list = [("log", "gathers all apache logs", "slow", False)]

class RedHatApache(Apache, RedHatPlugin):
    """Apache related information for Red Hat distributions
    """
    files = ('/etc/httpd/conf/httpd.conf',)

    def setup(self):
        super(RedHatApache, self).setup()

        self.add_copy_specs([
            "/etc/httpd/conf/httpd.conf",
            "/etc/httpd/conf.d/*.conf"])

        self.add_forbidden_path("/etc/httpd/conf/password.conf")

        if self.get_option("log"):
            self.add_copy_spec("/var/log/httpd/*")

class DebianApache(Apache, DebianPlugin, UbuntuPlugin):
    """Apache related information for Debian distributions
    """
    files = ('/etc/apache2/apache2.conf',)

    def setup(self):
        super(DebianApache, self).setup()
        self.add_copy_specs([
            "/etc/apache2/*",
            "/etc/default/apache2"])
        if self.get_option("log"):
            self.add_copy_spec("/var/log/apache2/*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = apparmor
## Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin

class Apparmor(Plugin, UbuntuPlugin):
    """Apparmor related information
    """

    plugin_name = 'apparmor'

    def setup(self):
        self.add_copy_specs([
            "/etc/apparmor"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = apport
## Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin

class Apport(Plugin, DebianPlugin, UbuntuPlugin):
    """apport information
    """

    plugin_name = 'apport'

    def setup(self):
        self.add_copy_spec("/etc/apport/*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = apt
# Copyright (C) 2013 Louis Bouchard <louis.bouchard@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin, DebianPlugin

class Apt(Plugin, DebianPlugin, UbuntuPlugin):
    """ Apt Plugin
    """

    plugin_name = 'apt'

    def setup(self):
        self.add_copy_specs(["/etc/apt", "/var/log/apt"])

        self.add_cmd_outputs([
            "apt-get check",
            "apt-config dump",
            "apt-cache stats",
            "apt-cache policy"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ata
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import os

class Ata(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """ ATA and IDE related information (including PATA and SATA)
    """

    plugin_name = "ata"

    packages = ('hdparm', 'smartmontools')

    def setup(self):
        dev_path = '/dev'
        sys_block = '/sys/block'
        self.add_copy_spec('/proc/ide')
        if os.path.isdir(sys_block):
            for disk in os.listdir(sys_block):
                if disk.startswith("sd") or disk.startswith("hd"):
                    disk_path = os.path.join(dev_path, disk)
                    self.add_cmd_outputs([
                        "hdparm %s" % disk_path,
                        "smartctl -a %s" % disk_path
                    ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = auditd
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Auditd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Auditd related information
    """

    option_list = [("logsize", "maximum size (MiB) of logs to collect",
                    "", 15)]

    plugin_name = 'auditd'

    def setup(self):
        self.add_copy_specs(["/etc/audit/auditd.conf",
                            "/etc/audit/audit.rules"])
        self.add_copy_spec_limit("/var/log/audit*",
                sizelimit = self.get_option("logsize"))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = autofs
## Copyright (C) 2007 Red Hat, Inc., Adam Stokes <astokes@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin

class Autofs(Plugin):
    """autofs server-related information
    """

    plugin_name = "autofs"

    files = ('/etc/sysconfig/autofs', '/etc/default/autofs')
    packages = ('autofs',)

    def checkdebug(self):
        """ testing if autofs debug has been enabled anywhere
        """
        # Global debugging
        opt = self.file_grep(r"^(DEFAULT_LOGGING|DAEMONOPTIONS)=(.*)", *self.files)
        for opt1 in opt:
            for opt2 in opt1.split(" "):
                if opt2 in ("--debug", "debug"):
                    return True
        return False

    def getdaemondebug(self):
        """ capture daemon debug output
        """
        debugout = self.file_grep(r"^(daemon.*)\s+(\/var\/log\/.*)", *self.files)
        for i in debugout:
            return i[1]

    def setup(self):
        self.add_copy_spec("/etc/auto*")
        self.add_cmd_output("/etc/init.d/autofs status")
        if self.checkdebug():
            self.add_copy_spec(self.getdaemondebug())

class RedHatAutofs(Autofs, RedHatPlugin):
    """autofs server-related on RedHat based distributions"""

    def setup(self):
        super(RedHatAutofs, self).setup()
        self.add_cmd_output("rpm -qV autofs")

class DebianAutofs(Autofs, DebianPlugin, UbuntuPlugin):
    """autofs server-related on Debian based distributions"""

    def setup(self):
        super(DebianAutofs, self).setup()
        self.add_cmd_output("dpkg-query -s autofs")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = azure
# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin

class Azure(Plugin, UbuntuPlugin):
    """ Microsoft Azure Client Plugin
    """

    plugin_name = 'azure'
    packages = ('walinuxagent',)

    def setup(self):
        self.add_copy_specs(["/var/log/waagent*",
                           "/var/lib/cloud",
                           "/etc/default/kv-kvp-daemon-init",
                           "/sys/module/hv_netvsc/parameters/ring_size",
                           "/sys/module/hv_storvsc/parameters/storvsc_ringbuffer_size"])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = block
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Block(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Block device related information
    """

    plugin_name = 'block'

    def setup(self):
        self.add_copy_spec("/proc/partitions")
        
        self.add_cmd_outputs([
            "lsblk",
            "blkid -c /dev/null",
            "ls -lanR /dev",
            "ls -lanR /sys/block"
        ])

        # legacy location for non-/run distributions
        self.add_copy_specs([
            "/etc/blkid.tab",
            "/run/blkid/blkid.tab"
        ])

        if os.path.isdir("/sys/block"):
            for disk in os.listdir("/sys/block"):
                if disk in [ ".",  ".." ] or disk.startswith("ram"):
                    continue
                disk_path = os.path.join('/dev/', disk)
                self.add_cmd_outputs([
                    "udevadm info -ap /sys/block/%s" % (disk),
                    "parted -s %s print" % (disk_path),
                    "fdisk -l %s" % disk_path
                ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = boot
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from glob import glob

class Boot(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Bootloader information
    """

    plugin_name = 'boot'

    option_list = [("all-images",
                    "collect a file listing for all initramfs images", "slow",
                    False)]

    def setup(self):
        self.add_copy_specs([
            # legacy / special purpose bootloader configs
            "/etc/milo.conf",
            "/etc/silo.conf",
            "/boot/efi/efi/redhat/elilo.conf",
            "/etc/yaboot.conf",
            "/boot/yaboot.conf"
        ])
        self.add_cmd_outputs([
            "ls -lanR /boot",
            "lsinitrd"
        ])
        if self.get_option("all-images"):
            for image in glob('/boot/initr*.img'):
                if image[-9:] == "kdump.img":
                    continue
                self.add_cmd_output("lsinitrd %s" % image)


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ceph
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin

class Ceph(Plugin, RedHatPlugin, UbuntuPlugin):
    """information on CEPH
    """

    plugin_name = 'ceph'
    option_list = [("log", "gathers all ceph logs", "slow", False)]

    packages = ('ceph',
                'ceph-mds',
                'ceph-common',
                'libcephfs1',
                'ceph-fs-common')

    def setup(self):
        self.add_copy_specs([
            "/etc/ceph/",
            "/var/log/ceph/"
        ])

        self.add_cmd_outputs([
            "ceph status",
            "ceph health",
            "ceph osd tree",
            "ceph osd stat",
            "ceph osd dump",
            "ceph mon stat",
            "ceph mon dump"
        ])

        self.add_forbidden_path("/etc/ceph/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*/*keyring")
        self.add_forbidden_path("/var/lib/ceph/*keyring")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cgroups
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Cgroups(Plugin, DebianPlugin, UbuntuPlugin):
    """cgroup subsystem information
    """

    files = ('/proc/cgroups',)

    plugin_name = "cgroups"

    def setup(self):
        self.add_copy_specs([
            "/proc/cgroups",
            "/sys/fs/cgroup"
        ])
        return

class RedHatCgroups(Cgroups, RedHatPlugin):
    """Red Hat specific cgroup subsystem information
    """

    def setup(self):
        super(RedHatCgroups, self).setup()
        self.add_copy_specs([
            "/etc/sysconfig/cgconfig",
            "/etc/sysconfig/cgred",
            "/etc/cgsnapshot_blacklist.conf",
            "/etc/cgconfig.conf",
            "/etc/cgrules.conf"
        ])
        
# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cluster
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import re, os
from glob import glob
from datetime import datetime, timedelta

class Cluster(Plugin, RedHatPlugin):
    """cluster suite and GFS related information
    """

    plugin_name = 'cluster'
    option_list = [("gfslockdump", 'gather output of gfs lockdumps', 'slow', False),
                    ("crm_from", 'specify the --from parameter passed to crm_report', 'fast', False),
                    ('lockdump', 'gather dlm lockdumps', 'slow', False)]

    packages = [
        "ricci",
        "corosync",
        "openais",
        "cman",
        "clusterlib",
        "fence-agents",
        "pacemaker"
    ]

    files = [ "/etc/cluster/cluster.conf" ]

    def setup(self):

        self.add_copy_specs([
            "/etc/cluster.conf",
            "/etc/cluster.xml",
            "/etc/cluster",
            "/etc/sysconfig/cluster",
            "/etc/sysconfig/cman",
            "/etc/fence_virt.conf",
            "/var/lib/ricci",
            "/var/lib/luci/data/luci.db",
            "/var/lib/luci/etc",
            "/var/log/cluster",
            "/var/log/luci",
            "/etc/fence_virt.conf"
        ])

        if self.get_option('gfslockdump'):
            self.do_gfslockdump()

        if self.get_option('lockdump'):
            self.do_lockdump()

        self.add_cmd_outputs([
            "rg_test test /etc/cluster/cluster.conf",
            "fence_tool ls -n",
            "gfs_control ls -n",
            "dlm_tool log_plock",
            "clustat",
            "group_tool dump",
            "cman_tool services",
            "cman_tool nodes",
            "cman_tool status",
            "ccs_tool lsnode",
            "ipvsadm -L",
            "corosync-quorumtool -l",
            "corosync-quorumtool -s",
            "corosync-cpgtool",
            "corosync-objctl",
            "group_tool ls -g1",
            "gfs_control ls -n",
            "gfs_control dump",
            "fence_tool dump",
            "dlm_tool dump",
            "dlm_tool ls -n",
            "mkqdisk -L"
        ])

        # crm_report needs to be given a --from "YYYY-MM-DD HH:MM:SS" start
        # time in order to collect data.
        crm_from = (datetime.today()
                    - timedelta(hours=72)).strftime("%Y-%m-%d %H:%m:%S")
        if self.get_option('crm_from') != False:
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                        str(self.get_option('crm_from'))):
                crm_from = self.get_option('crm_from')
            else:
                self.log_error(
                    "crm_from parameter '%s' is not a valid date: using default"
                            % self.get_option('crm_from'))

        crm_dest = self.get_cmd_output_path(name='crm_report')
        self.add_cmd_output('crm_report -S -d --dest %s --from "%s"'
                    % (crm_dest, crm_from))

    def do_lockdump(self):
        dlm_tool = "dlm_tool ls"
        result = self.call_ext_prog(dlm_tool)
        if result['status'] != 0:
            return
        for lockspace in re.compile(r'^name\s+([^\s]+)$',
                re.MULTILINE).findall(result['output']):
            self.add_cmd_output("dlm_tool lockdebug -svw '%s'" % lockspace,
                        suggest_filename = "dlm_locks_%s" % lockspace)

    def do_gfslockdump(self):
        for mntpoint in self.do_regex_find_all(r'^\S+\s+([^\s]+)\s+gfs\s+.*$',
                    "/proc/mounts"):
            self.add_cmd_output("gfs_tool lockdump %s" % mntpoint,
                        suggest_filename = "gfs_lockdump_"
                        + self.mangle_command(mntpoint))

    def postproc(self):
        for cluster_conf in glob("/etc/cluster/cluster.conf*"):
            self.do_file_sub(cluster_conf,
                        r"(\s*\<fencedevice\s*.*\s*passwd\s*=\s*)\S+(\")",
                        r"\1%s" %('"***"'))
        for luci_cfg in glob("/var/lib/luci/etc/*.ini*"):
            self.do_file_sub(luci_cfg, r"(.*secret\s*=\s*)\S+", r"\1******")
        self.do_cmd_output_sub("corosync-objctl",
                        r"(.*fence.*\.passwd=)(.*)",
                        r"\1******")
        return

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cobbler
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Cobbler(Plugin):
    plugin_name = "cobbler"
    
class RedHatCobbler(Cobbler, RedHatPlugin):
    """cobbler related information
    """

    packages = ('cobbler',)

    def setup(self):
        self.add_copy_specs([
            "/etc/cobbler",
            "/var/log/cobbler",
            "/var/lib/rhn/kickstarts",
            "/var/lib/cobbler"
        ])

class DebianCobbler(Cobbler, DebianPlugin, UbuntuPlugin):
    """cobbler related information for Debian and Ubuntu
    """

    packages = ('cobbler',)

    def setup(self):
        self.add_copy_specs([
            "/etc/cobbler",
            "/var/log/cobbler",
            "/var/lib/cobbler"
        ])
        self.add_forbidden_path("/var/lib/cobbler/isos")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = corosync
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Corosync(Plugin):
    """ corosync information
    """

    plugin_name = "corosync"
    packages = ('corosync',)

    def setup(self):
        self.add_copy_specs([
            "/etc/corosync",
            "/var/lib/corosync/fdata",
            "/var/log/cluster/corosync.log"
        ])
        self.add_cmd_outputs([
            "corosync-quorumtool -l",
            "corosync-quorumtool -s",
            "corosync-cpgtool",
            "corosync-objctl -a",
            "corosync-fplay",
            "corosync-objctl -w runtime.blackbox.dump_state=$(date +\%s)",
            "corosync-objctl -w runtime.blackbox.dump_flight_data=$(date +\%s)"
        ])
        self.call_ext_prog("killall -USR2 corosync")

class RedHatCorosync(Corosync, RedHatPlugin):
    """ corosync information for RedHat based distribution
    """

    def setup(self):
        super(RedHatCorosync, self).setup()


class DebianCorosync(Corosync, DebianPlugin, UbuntuPlugin):
    """ corosync information for Debian and Ubuntu distributions
    """

    def setup(self):
        super(DebianCorosync, self).setup()

    files = ('/usr/sbin/corosync',)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cron
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Cron(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Crontab information
    """

    plugin_name = "cron"

    files = ('/etc/crontab')

    def setup(self):
        self.add_copy_specs([
                "/etc/cron*",
                "/var/log/cron*",
                "/var/spool/cron"
        ])
        self.add_cmd_output("crontab -l -u root",
                suggest_filename = "root_crontab")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cs
## Copyright (C) 2007-2010 Red Hat, Inc., Kent Lamb <klamb@redhat.com>
##                                        Marc Sauton <msauton@redhat.com>
##                                        Pierre Carrier <pcarrier@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists
from glob import glob

class CertificateSystem(Plugin, RedHatPlugin):
    """Red Hat Certificate System 7.1, 7.3, 8.0 and dogtag related information
    """

    plugin_name = 'certificatesystem'

    def checkversion(self):
        if self.is_installed("redhat-cs") or exists("/opt/redhat-cs"):
            return 71
        elif self.is_installed("rhpki-common") or len(glob("/var/lib/rhpki-*")):
            return 73
        # 8 should cover dogtag
        elif self.is_installed("pki-common") or exists("/usr/share/java/pki"):
            return 8
        return False

    def check_enabled(self):
        if self.is_installed("redhat-cs") or \
           self.is_installed("rhpki-common") or \
           self.is_installed("pki-common") or \
           exists("/opt/redhat-cs") or \
           exists("/usr/share/java/rhpki") or \
           exists("/usr/share/java/pki"):
            return True
        return False

    def setup(self):
        csversion = self.checkversion()
        if not csversion:
            self.add_alert("Red Hat Certificate System not found.")
            return
        if csversion == 71:
            self.add_copy_specs([
                "/opt/redhat-cs/slapd-*/logs/access",
                "/opt/redhat-cs/slapd-*/logs/errors",
                "/opt/redhat-cs/slapd-*/config/dse.ldif",
                "/opt/redhat-cs/cert-*/errors",
                "/opt/redhat-cs/cert-*/config/CS.cfg",
                "/opt/redhat-cs/cert-*/access",
                "/opt/redhat-cs/cert-*/errors",
                "/opt/redhat-cs/cert-*/system",
                "/opt/redhat-cs/cert-*/transactions",
                "/opt/redhat-cs/cert-*/debug",
                "/opt/redhat-cs/cert-*/tps-debug.log"])
        if csversion == 73:
            self.add_copy_specs([
                "/var/lib/rhpki-*/conf/*cfg*",
                "/var/lib/rhpki-*/conf/*.ldif",
                "/var/lib/rhpki-*/logs/debug",
                "/var/lib/rhpki-*/logs/catalina.*",
                "/var/lib/rhpki-*/logs/ra-debug.log",
                "/var/lib/rhpki-*/logs/transactions",
                "/var/lib/rhpki-*/logs/system"])
        if csversion in (73, 8):
            self.add_copy_specs([
                "/etc/dirsrv/slapd-*/dse.ldif",
                "/var/log/dirsrv/slapd-*/access",
                "/var/log/dirsrv/slapd-*/errors"])
        if csversion == 8:
            self.add_copy_specs([
                "/etc/pki-*/CS.cfg",
                "/var/lib/pki-*/conf/*cfg*",
                "/var/log/pki-*/debug",
                "/var/log/pki-*/catalina.*",
                "/var/log/pki-*/ra-debug.log",
                "/var/log/pki-*/transactions",
                "/var/log/pki-*/system"])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = cups
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Printing(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """printing related information (cups)
    """

    plugin_name = 'printing'

    packages = ('cups',)
    option_list = [("cups", "max size (MiB) to collect per cups log file",
                   "", 15)]

    def setup(self):
        self.add_copy_specs([
            "/etc/cups/*.conf",
            "/etc/cups/lpoptions",
            "/etc/cups/ppd/*.ppd"])
        self.add_cmd_outputs([
            "lpstat -t",
            "lpstat -s",
            "lpstat -d"
        ])
        self.add_copy_spec_limit("/var/log/cups",
            sizelimit=self.option_enabled("cupslogsize"))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = devicemapper
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class DeviceMapper(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """device-mapper related information
    """

    plugin_name = 'devicemapper'

    def setup(self):
        self.add_cmd_outputs([
            "dmsetup info -c",
            "dmsetup table",
            "dmsetup status",
            "dmsetup ls --tree"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = dhcp
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin

class Dhcp(Plugin):
    """DHCP related information
    """

    plugin_name = "dhcp"

class RedHatDhcp(Dhcp, RedHatPlugin):
    """DHCP related information for Red Hat based distributions"""

    files = ('/etc/rc.d/init.d/dhcpd',)
    packages = ('dhcp',)

    def setup(self):
        super(RedHatDhcp, self).setup()
        self.add_copy_specs([
            "/etc/dhcpd.conf",
            "/etc/dhcp"])

class UbuntuDhcp(Dhcp, UbuntuPlugin):
    """DHCP related information for Debian based distributions"""

    files = ('/etc/init.d/udhcpd',)
    packages = ('udhcpd',)

    def setup(self):
        super(DebianDhcp, self).setup()
        self.add_copy_specs([
            "/etc/default/udhcpd",
            "/etc/udhcpd.conf"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = distupgrade
## Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin

class DistUpgrade(Plugin):
    """ Distribution upgrade data """

    plugin_name = "distupgrade"

    files = None


class RedHatDistUpgrade(DistUpgrade, RedHatPlugin):

    files = (
        "/var/log/upgrade.log",
        "/var/log/redhat_update_tool.log",
        "/root/preupgrade/all-xccdf*",
        "/root/preupgrade/kickstart"
    )



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = dmraid
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Dmraid(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """dmraid related information
    """

    option_list = [(
        "metadata", "capture metadata from dmraid devices", "slow", False
    )]

    plugin_name = 'dmraid'
    # V - {-V/--version}
    # b - {-b|--block_devices}
    # r - {-r|--raid_devices}
    # s - {-s|--sets}
    # t - [-t|--test]
    # a - {-a|--activate} {y|n|yes|no}
    # D - [-D|--dump_metadata]
    dmraid_options = ['V','b','r','s','tay']

    def setup(self):
        for opt in self.dmraid_options:
            self.add_cmd_output("dmraid -%s" % (opt,))
        if self.get_option("metadata"):
            metadata_path = self.get_cmd_output_path("metadata")
            self.add_cmd_output("dmraid -rD", runat=metadata_path)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = dovecot
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Dovecot(Plugin):
    """dovecot server related information
    """

    plugin_name = "dovecot"

    def setup(self):
        self.add_copy_spec("/etc/dovecot*")
        self.add_cmd_output("dovecot -n")

class RedHatDovecot(Dovecot, RedHatPlugin):
    """dovecot server related information for RedHat based distribution
    """
    def setup(self):
        super(RedHatDovecot, self).setup()

    packages = ('dovecot', )
    files = ('/etc/dovecot.conf',)

class DebianDovecot(Dovecot, DebianPlugin, UbuntuPlugin):
    """dovecot server related information for Debian based distribution
    """
    def setup(self):
        super(DebianDovecot, self).setup()

    files = ('/etc/dovecot/README',)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = dpkg
## Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin

class Dpkg(Plugin, DebianPlugin, UbuntuPlugin):
    """dpkg information
    """

    plugin_name = 'dpkg'

    def setup(self):
        self.add_copy_spec("/var/log/dpkg.log")
        self.add_cmd_output("dpkg -l", root_symlink = "installed-debs")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ds
## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class DirectoryServer(Plugin, RedHatPlugin):
    """Directory Server information
    """

    plugin_name = 'directoryserver'

    files = ('/etc/dirsrv', '/opt/redhat-ds')
    packages = ('redhat-ds-base', 'redhat-ds-7')

    def check_version(self):
        if self.is_installed("redhat-ds-base") or \
        os.path.exists("/etc/dirsrv"):
            return "ds8"
        elif self.is_installed("redhat-ds-7") or \
        os.path.exists("/opt/redhat-ds"):
            return "ds7"
        return False

    def setup(self):
        if not self.check_version():
            self.add_alert("Directory Server not found.")
        elif "ds8" in self.check_version():
            self.add_copy_specs([
                "/etc/dirsrv/slapd*",
                "/var/log/dirsrv/*"])
        elif "ds7" in self.check_version():
            self.add_copy_specs([
                "/opt/redhat-ds/slapd-*/config",
                "/opt/redhat-ds/slapd-*/logs"])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = emc
## emc.py
## Captures EMC specific information during a sos run.

## Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, os

# Just for completeness sake.
from six.moves import input

class Emc(Plugin, RedHatPlugin):
    """EMC related information (PowerPath, Solutions Enabler CLI and Navisphere CLI)
    """

    plugin_name = 'emc'

    def about_emc(self):
        """ EMC Corporation specific information
        """
        self.add_custom_text('<center><h1><font size="+4"color="blue">EMC&sup2;</font><font size="-2" color="blue">&reg;</font>')
        self.add_custom_text('<br><font size="+1">where information lives</font><font size="-2">&reg;</font></h1>')
        self.add_custom_text("EMC Corporation is the world's leading developer and provider of information ")
        self.add_custom_text("infrastructure technology and solutions that enable organizations of all sizes to transform ")
        self.add_custom_text("the way they compete and create value from their information. &nbsp;")
        self.add_custom_text("Information about EMC's products and services can be found at ")
        self.add_custom_text('<a href="http://www.EMC.com/">www.EMC.com</a>.</center>')

    def get_pp_files(self):
        """ EMC PowerPath specific information - files
        """
        self.add_cmd_output("powermt version")
        self.add_copy_specs([
            "/etc/init.d/PowerPath",
            "/etc/powermt.custom",
            "/etc/emcp_registration",
            "/etc/emc/mpaa.excluded",
            "/etc/emc/mpaa.lams",
            "/etc/emcp_devicesDB.dat",
            "/etc/emcp_devicesDB.idx",
            "/etc/emc/powerkmd.custom",
            "/etc/modprobe.conf.pp"])

    def get_pp_config(self):
        """ EMC PowerPath specific information - commands
        """
        self.add_cmd_outputs([
            "powermt display",
            "powermt display dev=all",
            "powermt check_registration",
            "powermt display options",
            "powermt display ports",
            "powermt display paths",
            "powermt dump"
        ])

    def get_symcli_files(self):
        """ EMC Solutions Enabler SYMCLI specific information - files
        """
        self.add_copy_specs([
            "/var/symapi/db/symapi_db.bin",
            "/var/symapi/config/[a-z]*",
            "/var/symapi/log/[a-z]*"])

    def get_symcli_config(self):
        """ EMC Solutions Enabler SYMCLI specific information - Symmetrix/DMX - commands
        """
        self.add_cmd_outputs([
            "symclisymcli -def",
            "symclisymdg list",
            "symclisymdg -v list",
            "symclisymcg list",
            "symclisymcg -v list",
            "symclisymcfg list",
            "symclisymcfg -v list",
            "symclisymcfg -db",
            "symclisymcfg -semaphores list",
            "symclisymcfg -dir all -v list",
            "symclisymcfg -connections list",
            "symclisymcfg -app -v list",
            "symclisymcfg -fa all -port list",
            "symclisymcfg -ra all -port list",
            "symclisymcfg -sa all -port list",
            "symclisymcfg list -lock",
            "symclisymcfg list -lockn all",
            "symclisyminq",
            "symclisyminq -v",
            "symclisyminq -symmids",
            "symclisyminq hba -fibre",
            "symclisyminq hba -scsi",
            "symclisymhost show -config",
            "symclistordaemon list",
            "symclistordaemon -v list",
            "symclisympd list",
            "symclisympd list -vcm",
            "symclisymdev list",
            "symclisymdev -v list",
            "symclisymdev -rdfa list",
            "symclisymdev -rdfa -v list",
            "symclisymbcv list",
            "symclisymbcv -v list",
            "symclisymrdf list",
            "symclisymrdf -v list",
            "symclisymrdf -rdfa list",
            "symclisymrdf -rdfa -v list",
            "symclisymsnap list",
            "symclisymsnap list -savedevs",
            "symclisymclone list",
            "symclisymevent list",
            "symclisymmask list hba",
            "symclisymmask list logins",
            "symclisymmaskdb list database",
            "symclisymmaskdb -v list database"
        ])

    def get_navicli_config(self):
        """ EMC Navisphere Host Agent NAVICLI specific information - files
        """
        self.add_copy_specs([
            "/etc/Navisphere/agent.config",
            "/etc/Navisphere/Navimon.cfg",
            "/etc/Navisphere/Quietmode.cfg",
            "/etc/Navisphere/messages/[a-z]*",
            "/etc/Navisphere/log/[a-z]*"])

    def get_navicli_SP_info(self,SP_address):
        """ EMC Navisphere Host Agent NAVICLI specific information - CLARiiON - commands
        """
        self.add_cmd_outputs([
            "navicli -h %s getall" % SP_address,
            "navicli -h %s getsptime -spa" % SP_address,
            "navicli -h %s getsptime -spb" % SP_address,
            "navicli -h %s getlog" % SP_address,
            "navicli -h %s getdisk" % SP_address,
            "navicli -h %s getcache" % SP_address,
            "navicli -h %s getlun" % SP_address,
            "navicli -h %s getlun -rg -type -default -owner -crus -capacity" % SP_address,
            "navicli -h %s lunmapinfo" % SP_address,
            "navicli -h %s getcrus" % SP_address,
            "navicli -h %s port -list -all" % SP_address,
            "navicli -h %s storagegroup -list" % SP_address,
            "navicli -h %s spportspeed -get" % SP_address
        ])

    def check_enabled(self):
        self.packages = [ "EMCpower" ]
        self.files = [ "/opt/Navisphere/bin", "/proc/emcp" ]
        return Plugin.check_enabled(self)

    def setup(self):
        from subprocess import Popen, PIPE
        ## About EMC Corporation default no if no EMC products are installed
        add_about_emc="no"

        ## If PowerPath is installed collect PowerPath specific information
        if self.is_installed("EMCpower"):
            print("EMC PowerPath is installed.")
            print(" Gathering EMC PowerPath information...")
            self.add_custom_text("EMC PowerPath is installed.<br>")
            self.get_pp_files()
            add_about_emc = "yes"

        ## If PowerPath is running collect additional PowerPath specific information
        if os.path.isdir("/proc/emcp"):
            print("EMC PowerPath is running.")
            print(" Gathering additional EMC PowerPath information...")
            self.get_pp_config()

        ## If Solutions Enabler is installed collect Symmetrix/DMX specific information
        if len(self.policy().package_manager.all_pkgs_by_name_regex('[Ss][Yy][Mm][Cc][Ll][Ii]-[Ss][Yy][Mm][Cc][Ll][Ii]')) > 0:
            print("EMC Solutions Enabler SYMCLI is installed.")
            print(" Gathering EMC Solutions Enabler SYMCLI information...")
            self.add_custom_text("EMC Solutions Enabler is installed.<br>")
            self.get_symcli_files()
            self.get_symcli_config()
            add_about_emc = "yes"

        ## If Navisphere Host Agent is installed collect CLARiiON specific information
        if os.path.isdir("/opt/Navisphere/bin"):
            print("")
            print("The EMC CLARiiON Navisphere Host Agent is installed.")
            self.add_custom_text("EMC CLARiiON Navisphere Host Agent is installed.<br>")
            self.get_navicli_config()
            print(" Gathering Navisphere NAVICLI Host Agent information...")
            print(" Please enter a CLARiiON SP IP address.  In order to collect")
            print( " information for both SPA and SPB as well as multiple")
            print(" CLARiiON arrays (if desired) you will be prompted multiple times.")
            print(" To exit simply press [Enter]")
            print("")
            add_about_emc = "yes"
            CLARiiON_IP_address_list = []
            CLARiiON_IP_loop = "stay_in"
            while CLARiiON_IP_loop == "stay_in":
                ans = input("CLARiiON SP IP Address or [Enter] to exit: ")
                ## Check to make sure the CLARiiON SP IP address provided is valid
                p = Popen("navicli -h %s getsptime" % (ans,),
                            shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
                out, err = p.communicate()
                if p.returncode == 0:
                    CLARiiON_IP_address_list.append(ans)
                else:
                    if ans != "":
                        print("The IP address you entered, %s, is not to an active CLARiiON SP." % ans)
                    if ans == "":
                        CLARiiON_IP_loop = "get_out"
            ## Sort and dedup the list of CLARiiON IP Addresses
            CLARiiON_IP_address_list.sort()
            for SP_address in CLARiiON_IP_address_list:
                if CLARiiON_IP_address_list.count(SP_address) > 1:
                    CLARiiON_IP_address_list.remove(SP_address)
            for SP_address in CLARiiON_IP_address_list:
                if SP_address != "":
                    print(" Gathering NAVICLI information for %s..." % SP_address)
                    self.get_navicli_SP_info(SP_address)

        ## Only provide About EMC if EMC products are installed
        if add_about_emc != "no":
            self.about_emc()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = filesys
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re
from six.moves import zip

class Filesys(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """information on filesystems
    """

    plugin_name = 'filesys'

    option_list = [("lsof", 'gathers information on all open files', 'slow', False),
                   ("dumpe2fs", 'dump filesystem information', 'slow', False)]

    def setup(self):
        self.add_copy_specs([
            "/proc/filesystems",
            "/etc/fstab",
            "/proc/self/mounts",
            "/proc/self/mountinfo",
            "/proc/self/mountstats",
            "/proc/mounts"
        ])
        self.add_cmd_output("mount -l", root_symlink = "mount")
        self.add_cmd_output("df -al", root_symlink = "df")
        self.add_cmd_outputs([
            "df -ali",
            "findmnt"
        ])

        if self.get_option('lsof'):
            self.add_cmd_output("lsof -b +M -n -l -P", root_symlink = "lsof")

        if self.get_option('dumpe2fs'):
            mounts = '/proc/mounts'
            ext_fs_regex = r"^(/dev/.+).+ext[234]\s+"
            for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
                self.add_cmd_output("dumpe2fs -h %s" % (dev))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = foreman
## Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin

class Foreman(Plugin, RedHatPlugin):
    """Foreman project related information
    """

    plugin_name = 'foreman'
    packages = ('foreman')

    def setup(self):
        self.add_cmd_output("%s -q -a -d %s" % ("foreman-debug",
                           self.get_cmd_output_path(name="foreman-debug")))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = gdm
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Gdm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """gdm related information
    """

    plugin_name = 'gdm'

    def setup(self):
        self.add_copy_spec("/etc/gdm/*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = general
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin

class General(Plugin):
    """basic system information"""

    plugin_name = "general"

    def setup(self):
        self.add_copy_specs([
            "/etc/init",    # upstart
            "/etc/event.d", # "
            "/etc/inittab",
            "/etc/sos.conf",
            "/etc/sysconfig",
            "/proc/stat",
            "/var/log/pm/suspend.log",
            "/var/log/up2date",
            "/etc/hostid",
            "/var/lib/dbus/machine-id",
            "/etc/exports",
            "/etc/localtime"
        ])

        self.add_cmd_output("hostname", root_symlink="hostname")
        self.add_cmd_output("date", root_symlink="date")
        self.add_cmd_output("uptime", root_symlink="uptime")
        self.add_cmd_outputs([
            "tree /var/lib",
            "ls -lR /var/lib"
        ])


class RedHatGeneral(General, RedHatPlugin):
    """Basic system information for RedHat based distributions"""

    def setup(self):
        super(RedHatGeneral, self).setup()

        self.add_copy_specs([
            "/etc/redhat-release",
            "/etc/fedora-release"
        ])


    def postproc(self):
        self.do_file_sub("/etc/sysconfig/rhn/up2date",
                r"(\s*proxyPassword\s*=\s*)\S+", r"\1***")


class DebianGeneral(General, DebianPlugin):
    """Basic system information for Debian based distributions"""

    def setup(self):
        super(DebianGeneral, self).setup()
        self.add_copy_specs([
            "/etc/default",
            "/etc/lsb-release",
            "/etc/debian_version"
        ])


class UbuntuGeneral(DebianGeneral):
    """Basic system information for Ubuntu based distributions"""

    def setup(self):
        super(UbuntuGeneral, self).setup()
        self.add_copy_spec("/etc/os-release")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = gluster
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import time
import os.path
import os
import string
from sos.plugins import Plugin, RedHatPlugin

class Gluster(Plugin, RedHatPlugin):
    '''gluster related information'''

    plugin_name = 'gluster'

    statedump_dir = '/tmp/glusterfs-statedumps'
    packages = ["glusterfs", "glusterfs-core"]
    files = ["/etc/glusterd", "/var/lib/glusterd"]

    def default_enabled(self):
        return True

    def get_volume_names(self, volume_file):
        """Return a dictionary for which key are volume names according to the
        output of gluster volume info stored in volume_file.
        """
        out=[]
        fp = open(volume_file, 'r')
        for line in fp.readlines():
            if not line.startswith("Volume Name:"):
                continue
            volname = line[12:-1]
            out.append(volname)
        fp.close()
        return out

    def make_preparations(self, name_dir):
        try:
            os.mkdir(name_dir);
        except:
            pass
        fp = open ('/tmp/glusterdump.options', 'w');
        data = 'path=' + name_dir + '\n';
        fp.write(data);
        fp.write('all=yes');
        fp.close();

    def wait_for_statedump(self, name_dir):
        statedumps_present = 0;
        statedump_entries = os.listdir(name_dir);
        for statedump_file in statedump_entries:
            statedumps_present = statedumps_present+1;
            last_line = 'tmp';
            ret = -1;
            while  ret == -1:
                last_line = file(name_dir + '/' + statedump_file, "r").readlines()[-1];
                ret = string.count (last_line, 'DUMP_END_TIME');

    def postproc(self):
        if not os.path.exists(self.statedump_dir):
            return
        try:
            for dirs in os.listdir(self.statedump_dir):
                os.remove(os.path.join(self.statedump_dir,dirs));
            os.rmdir(self.statedump_dir);
            os.unlink('/tmp/glusterdump.options');
        except:
            pass

    def setup(self):
        self.add_cmd_output("gluster peer status")

        self.add_copy_spec("/var/lib/glusterd/")
        self.add_forbidden_path("/var/lib/glusterd/geo-replication/secret.pem")

        # collect unified file and object storage configuration
        self.add_copy_spec("/etc/swift/")

        # glusterfs-server rpm scripts stash this on migration to 3.3.x
        self.add_copy_spec("/etc/glusterd.rpmsave")

        # common to all versions
        self.add_copy_spec("/etc/glusterfs")

        self.make_preparations(self.statedump_dir)
        if self.check_ext_prog("killall -USR1 glusterfs glusterfsd"):
            # let all the processes catch the signal and create statedump file
            # entries.
            time.sleep(1)
            self.wait_for_statedump(self.statedump_dir)
            self.add_copy_spec('/tmp/glusterdump.options')
            self.add_copy_spec(self.statedump_dir)
        else:
            self.soslog.warning("could not send SIGUSR1 to glusterfs processes")

        volume_file = self.get_cmd_output_now("gluster volume info",
                        "gluster_volume_info")
        if volume_file:
            for volname in self.get_volume_names(volume_file):
                self.add_cmd_output("gluster volume geo-replication %s status"
                                    % volname)

        self.add_cmd_output("gluster volume status")
        # collect this last as some of the other actions create log entries
        self.add_copy_spec("/var/log/glusterfs")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = grub
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Grub(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Grub information
    """

    plugin_name = 'grub'
    packages = ('grub',)

    def setup(self):
        self.add_copy_specs([
            "/boot/efi/EFI/*/grub.conf",
            "/boot/grub/grub.conf",
            "/boot/grub/device.map",
            "/etc/grub.conf",
            "/etc/grub.d"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = grub2
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Grub2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Bootloader information
    """

    plugin_name = 'grub2'
    packages = ('grub2',)

    def setup(self):
        self.add_copy_specs([
            "/boot/efi/EFI/*/grub.cfg",
            "/boot/grub2/grub.cfg",
            "/boot/grub2/grubenv",
            "/boot/grub/grub.cfg",
            "/etc/default/grub",
            "/etc/grub2.cfg",
            "/etc/grub.d"
        ])
        self.add_cmd_outputs([
            "ls -lanR /boot",
            "grub2-mkconfig"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = hardware
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Hardware(Plugin):
    """hardware related information
    """

    plugin_name = "hardware"

    def setup(self):
        self.add_copy_specs([
            "/proc/interrupts",
            "/proc/irq",
            "/proc/dma",
            "/proc/devices",
            "/proc/rtc",
            "/var/log/mcelog"
        ])

        self.add_cmd_output("dmidecode", root_symlink = "dmidecode")
        

class RedHatHardware(Hardware, RedHatPlugin):
    """hardware related information for Red Hat distribution
    """

    def setup(self):
        super(RedHatHardware, self).setup()
        hwpaths = glob("/usr/share/rhn/up2date*client/hardware.py")
        if (len(hwpaths) == 0):
            return
        self.add_cmd_output("python " + hwpaths[0])


class DebianHardware(Hardware, DebianPlugin, UbuntuPlugin):
    """hardware related information for Debian distribution
    """

    def setup(self):
        super(DebianHardware, self).setup()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = hts
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class HardwareTestSuite(Plugin, RedHatPlugin):
    """Red Hat Hardware Test Suite related information
    """

    plugin_name = 'hardwaretestsuite'

    def setup(self):
        self.add_copy_specs([
            "/etc/httpd/conf.d/hts.conf",
            "/var/hts"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = i18n
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class I18n(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Internationalization related information
    """

    plugin_name = 'i18n'

    def setup(self):
        self.add_copy_specs(["/etc/X11/xinit/xinput.d/*", "/etc/locale.conf"])
        self.add_cmd_output("locale")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = infiniband
## Copyright (C) 2011, 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Infiniband(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Infiniband related information
    """

    plugin_name = 'infiniband'
    packages = ('libibverbs-utils',)

    def setup(self):
        self.add_copy_specs([
            "/etc/ofed/openib.conf",
            "/etc/ofed/opensm.conf"])

        self.add_cmd_outputs([
            "ibv_devices",
            "ibv_devinfo",
            "ibstat",
            "ibstatus",
            "ibhosts"
        ])

        return

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ipa
## Copyright (C) 2007 Red Hat, Inc., Kent Lamb <klamb@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Ipa(Plugin, RedHatPlugin):
    """IPA diagnostic information
    """

    plugin_name = 'ipa'

    ipa_server = False
    ipa_client = False

    files = ('/etc/ipa',)
    packages = ('ipa-server', 'ipa-client')

    def check_enabled(self):
        self.ipa_server = self.is_installed("ipa-server")
        self.ipa_client = self.is_installed("ipa-client")
        return Plugin.check_enabled(self)

    def setup(self):
        if self.ipa_server:
            self.add_copy_specs([
                "/var/log/ipaserver-install.log",
                "/var/log/ipareplica-install.log"
            ])
        if self.ipa_client:
            self.add_copy_spec("/var/log/ipaclient-install.log")

        self.add_copy_specs([
            "/var/log/ipaupgrade.log",
            "/var/log/krb5kdc.log",
            "/var/log/pki-ca/debug",
            "/var/log/pki-ca/catalina.out",
            "/var/log/pki-ca/system",
            "/var/log/pki-ca/transactions",
            "/var/log/dirsrv/slapd-*/logs/access",
            "/var/log/dirsrv/slapd-*/logs/errors",
            "/etc/dirsrv/slapd-*/dse.ldif",
            "/etc/dirsrv/slapd-*/schema/99user.ldif",
            "/etc/hosts",
            "/etc/named.*"
        ])

        self.add_forbidden_path("/etc/pki/nssdb/key*")
        self.add_forbidden_path("/etc/pki-ca/flatfile.txt")
        self.add_forbidden_path("/etc/pki-ca/password.conf")
        self.add_forbidden_path("/var/lib/pki-ca/alias/key*")

        self.add_forbidden_path("/etc/dirsrv/slapd-*/key*")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pin.txt")
        self.add_forbidden_path("/etc/dirsrv/slapd-*/pwdfile.txt")

        self.add_forbidden_path("/etc/named.keytab")

        self.add_cmd_outputs([
            "ls -la /etc/dirsrv/slapd-*/schema/",
            "ipa-getcert list",
            "certutil -L -d /etc/httpd/alias/",
            "certutil -L -d /etc/dirsrv/slapd-*/",
            "klist -ket /etc/dirsrv/ds.keytab",
            "klist -ket /etc/httpd/conf/ipa.keytab"
        ])

        return

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1********"
        self.do_file_sub("/etc/named.conf", match, subst)


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ipsec
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class IPSec(Plugin):
    """ipsec related information
    """

    plugin_name = "ipsec"
    packages = ('ipsec-tools',)

class RedHatIpsec(IPSec, RedHatPlugin):
    """ipsec related information for Red Hat distributions
    """

    files = ('/etc/racoon/racoon.conf',)

    def setup(self):
        self.add_copy_spec("/etc/racoon")

class DebianIPSec(IPSec, DebianPlugin, UbuntuPlugin):
    """ipsec related information for Debian distributions
    """

    files = ('/etc/ipsec-tools.conf',)

    def setup(self):
        self.add_copy_specs([
            "/etc/ipsec-tools.conf",
            "/etc/ipsec-tools.d",
            "/etc/default/setkey"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = iscsi
## Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Iscsi(Plugin):
    """iscsi-initiator related information
    """

    plugin_name = "iscsi"

class RedHatIscsi(Iscsi, RedHatPlugin):
    """iscsi-initiator related information Red Hat based distributions
    """

    packages = ('iscsi-initiator-utils',)

    def setup(self):
        super(RedHatIscsi, self).setup()
        self.add_copy_specs([
            "/etc/iscsi/iscsid.conf",
            "/etc/iscsi/initiatorname.iscsi",
            "/var/lib/iscsi"
        ])
        self.add_cmd_outputs([
            "iscsiadm -m session -P 3",
            "iscsiadm -m node -P 3",
            "iscsiadm -m iface -P 1",
            "iscsiadm -m node --op=show"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = iscsitarget
## Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
## Copyright (C) 2012 Adam Stokes <adam.stokes@canonical.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class IscsiTarget(Plugin):
    """iscsi-target related information
    """

    plugin_name = "iscsitarget"

class RedHatIscsiTarget(IscsiTarget, RedHatPlugin):
    """iscsi-target related information for Red Hat distributions
    """

    packages = ('scsi-target-utils',)

    def setup(self):
        super(RedHatIscsiTarget, self).setup()
        self.add_copy_spec("/etc/tgt/targets.conf")
        self.add_cmd_output("tgtadm --lld iscsi --op show --mode target")

class DebianIscsiTarget(IscsiTarget, DebianPlugin, UbuntuPlugin):
    """iscsi-target related information for Debian based distributions
    """

    packages = ('iscsitarget',)

    def setup(self):
        super(DebianIscsiTarget, self).setup()
        self.add_copy_specs([
            "/etc/iet",
            "/etc/sysctl.d/30-iscsitarget.conf",
            "/etc/default/iscsitarget"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = java
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin

class Java(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """basic java information"""

    plugin_name = "java"

    def setup(self):
        self.add_copy_spec("/etc/java")
        self.add_forbidden_path("/etc/java/security")
        self.add_cmd_output("alternatives --display java",
                                        root_symlink="java")
        self.add_cmd_output("readlink -f /usr/bin/java")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = juju
# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin

class Juju(Plugin, UbuntuPlugin):
    """ Juju Plugin
    """

    plugin_name = 'juju'

    def setup(self):
        self.add_copy_specs([
            "/var/log/juju",
            "/var/lib/juju"
        ])

        self.add_cmd_outputs([
            "juju -v status",
            "juju -v get-constraints"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = katello
## Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin

class Katello(Plugin, RedHatPlugin):
    """Katello project related information
    """

    plugin_name = 'katello'
    packages = ('katello', 'katello-common', 'katello-headpin')

    def setup(self):
        self.add_cmd_output("katello-debug --notar -d %s"
                            % self.get_cmd_output_path(name="katello-debug"))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = kdump
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class KDump(Plugin):
    """Kdump related information
    """

    plugin_name = "kdump"

    def setup(self):
        self.add_copy_specs([
            "/proc/cmdline"
        ])

class RedHatKDump(KDump, RedHatPlugin):
    """Kdump related information for Red Hat distributions
    """

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    def setup(self):
        self.add_copy_specs([
            "/etc/kdump.conf",
            "/etc/udev/rules.d/*kexec.rules",
            "/var/crash/*/vmcore-dmesg.txt"
        ])

class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):
    """Kdump related information for Debian distributions
    """

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        self.add_copy_specs([
            "/etc/default/kdump-tools"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = kernel
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Kernel(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """kernel related information
    """

    plugin_name = 'kernel'

    sys_module = '/sys/module'

    def setup(self):
        # compat
        self.add_cmd_output("uname -a", root_symlink = "uname")
        self.add_cmd_output("lsmod", root_symlink = "lsmod")

        try:
            modules = os.listdir(self.sys_module)
            self.add_cmd_output("modinfo " + " ".join(modules))
        except OSError:
            self.log_warn("could not list %s" % self.sys_module)

        self.add_cmd_outputs([
            "dmesg",
            "sysctl -a",
            "dkms status"
        ])

        self.add_copy_specs([
            "/proc/modules",
            "/proc/sys/kernel/random/boot_id",
            "/sys/module/*/parameters",
            "/sys/module/*/initstate",
            "/sys/module/*/refcnt",
            "/sys/module/*/taint",
            "/proc/kallsyms",
            "/proc/buddyinfo",
            "/proc/slabinfo",
            "/proc/zoneinfo",
            "/lib/modules/%s/modules.dep" % self.policy().kernel_version(),
            "/etc/conf.modules",
            "/etc/modules.conf",
            "/etc/modprobe.conf",
            "/etc/modprobe.d",
            "/etc/sysctl.conf",
            "/etc/sysctl.d",
            "/lib/sysctl.d",
            "/proc/cmdline",
            "/proc/driver",
            "/proc/sys/kernel/tainted",
            "/proc/softirqs",
            "/proc/timer*",
            "/proc/lock*",
            "/var/log/dmesg"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = kernelrt
# -*- python -*-
# -*- coding: utf-8 -*-

#
# Copyright 2012 Red Hat Inc.
# Guy Streeter <streeter@redhat.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; version 2.
#
#   This application is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.

from sos.plugins import Plugin, RedHatPlugin

class KernelRT(Plugin, RedHatPlugin):
    '''Information specific to the realtime kernel
    '''

    plugin_name = 'kernelrt'

    # this file exists only when the realtime kernel is booted
    # this plugin will not be called is this file does not exist
    files = ('/sys/kernel/realtime',)

    def setup(self):
        self.add_copy_specs([
            '/etc/rtgroups',
            '/proc/sys/kernel/sched_rt_period_us',
            '/proc/sys/kernel/sched_rt_runtime_us',
            '/sys/kernel/realtime',
            '/sys/devices/system/clocksource/clocksource0/available_clocksource',
            '/sys/devices/system/clocksource/clocksource0/current_clocksource'
        ])
        # note: rhbz#1059685 'tuna - NameError: global name 'cgroups' is not defined'
        # this command throws an exception on versions prior to 0.10.4-5.
        self.add_cmd_output('tuna -CP')

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = krb5
## Copyright (C) 2013 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Krb5(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Kerberos related information
    """
    packages = ('krb5-libs', 'krb5-user')
    plugin_name = 'krb5'

    def setup(self):
        self.add_copy_spec("/etc/krb5.conf")
        self.add_cmd_output("klist -ket /etc/krb5.keytab")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = kvm
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Kvm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """KVM related information
    """

    plugin_name = 'kvm'
    debugfs_path = "/sys/kernel/debug"

    _debugfs_cleanup = False

    def check_enabled(self):
        return os.access("/sys/module/kvm", os.R_OK)

    def setup(self):
        self.add_copy_specs([
            "/sys/module/kvm/srcversion",
            "/sys/module/kvm_intel/srcversion",
            "/sys/module/kvm_amd/srcversion",
            "/sys/module/ksm/srcversion"
        ])
        if not os.path.ismount(self.debugfs_path):
            self._debugfs_cleanup = True
            r = self.call_ext_prog("mount -t debugfs debugfs %s"
                                    % self.debugfs_path)
            if r['status'] != 0:
                self.log_error("debugfs not mounted and mount attempt failed")
                self._debugfs_cleanup = False
                return
        self.add_cmd_output("kvm_stat --once")

    def postproc(self):
        if self._debugfs_cleanup and os.path.ismount(self.debugfs_path):
            r = self.call_ext_prog("umount %s" % self.debugfs_path)
            self.log_error("could not unmount %s" % self.debugfs_path)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = landscape
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin

class Landscape(Plugin, UbuntuPlugin):
    """
    landscape client related information
    """

    plugin_name = 'landscape'

    files = (
        '/etc/landscape/client.conf',
        'broker.log',
        'broker.log.gz',
        'broker.log.1',
        'broker.log.1.gz',
        'broker.log.2',
        'broker.log.2.gz',
        'manager.log',
        'manager.log.gz',
        'manager.log.1',
        'manager.log.1.gz',
        'manager.log.2',
        'manager.log.2.gz',
        'monitor.log',
        'monitor.log.gz',
        'monitor.log.1',
        'monitor.log.1.gz',
        'monitor.log.2',
        'monitor.log.2.gz',
        'package-reporter.log',
        'package-reporter.log.gz',
        'package-reporter.log.1',
        'package-reporter.log.1.gz',
        'package-reporter.log.2',
        'package-reporter.log.2.gz',
        'sysinfo.log',
        'sysinfo.log.gz',
        'sysinfo.log.1',
        'sysinfo.log.1.gz',
        'sysinfo.log.2',
        'sysinfo.log.2.gz',
        'watchdog.log',
        'watchdog.log.gz',
        'watchdog.log.1',
        'watchdog.log.1.gz',
        'watchdog.log.2',
        'watchdog.log.2.gz'
    )
    packages = ('landscape-client',)

    def setup(self):
        self.add_copy_spec("/etc/landscape/client.conf")
        
    def postproc(self):
        self.do_file_sub("/etc/landscape/client.conf", 
        r"registration_password(.*)", 
        r"registration_password[***]"
        )
        
                                                    

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ldap
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Ldap(Plugin):
    """LDAP related information
    """

    plugin_name = "ldap"
    ldap_conf = "/etc/openldap/ldap.conf"

    def setup(self):
        super(Ldap, self).setup()
        self.add_copy_spec("/etc/ldap.conf")

    def postproc(self):
        self.do_file_sub("/etc/ldap.conf", r"(\s*bindpw\s*)\S+", r"\1******")

class RedHatLdap(Ldap, RedHatPlugin):
    """LDAP related information for RedHat based distribution
    """

    packages = ('openldap', 'nss-pam-ldapd')
    files = ('/etc/ldap.conf', '/etc/pam_ldap.conf')

    def setup(self):
        super(RedHatLdap, self).setup()
        self.add_copy_specs([
                "/etc/openldap",
                "/etc/nslcd.conf",
                "/etc/pam_ldap.conf"
        ])

    def postproc(self):
        super(RedHatLdap, self).postproc()
        self.do_file_sub("/etc/nslcd.conf",
                        r"(\s*bindpw\s*)\S+", r"\1********")
        self.do_file_sub("/etc/pam_ldap.conf",
                        r"(\s*bindpw\s*)\S+", r"\1********")

class DebianLdap(Ldap, DebianPlugin, UbuntuPlugin):
    """LDAP related information for Debian based distribution
    """

    ldap_conf = "/etc/ldap/ldap.conf"
    packages = ('slapd', 'ldap-utils')

    def setup(self):
        super(DebianLdap, self).setup()

        ldap_search = "ldapsearch -Q -LLL -Y EXTERNAL -H ldapi:/// "

        self.add_copy_specs([
            "/etc/ldap/ldap.conf",
            "/etc/slapd.conf",
            "/etc/ldap/slapd.d"
        ])

        self.add_cmd_output("ldapsearch -x -b '' -s base 'objectclass=*'")
        self.add_cmd_output(ldap_search + "-b cn=config '(!(objectClass=olcSchemaConfig))'",
            suggest_filename="configuration_minus_schemas")
        self.add_cmd_output(ldap_search + "-b cn=schema,cn=config dn",
            suggest_filename="loaded_schemas")
        self.add_cmd_output(ldap_search + "-b cn=config '(olcAccess=*)' olcAccess olcSuffix",
            suggest_filename="access_control_lists")

    def postproc(self):
        super(RedHatLdap, self).postproc()
        self.do_cmd_output_sub(
        "ldapsearch -Q -LLL -Y EXTERNAL -H ldapi:/// -b cn=config '(!(objectClass=olcSchemaConfig))'",
            r"(olcRootPW\: \s*)\S+", r"\1********")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = libraries
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin

class Libraries(Plugin, RedHatPlugin, UbuntuPlugin):
    """information on shared libraries
    """

    plugin_name = 'libraries'

    option_list = [('ldconfigv', 'the name of each directory as it is scanned, and any links that are created.',
                    "slow", False)]

    def setup(self):
        self.add_copy_specs(["/etc/ld.so.conf", "/etc/ld.so.conf.d"])
        if self.get_option("ldconfigv"):
            self.add_cmd_output("ldconfig -v -N -X")
        self.add_cmd_output("ldconfig -p -N -X")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = libvirt
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import glob

class Libvirt(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """libvirt-related information
    """

    plugin_name = 'libvirt'

    def setup(self):
        self.add_copy_specs([
            "/etc/libvirt/",
            "/var/log/libvirt*"
        ])

    def postproc(self):
       for xmlfile in glob.glob("/etc/libvirt/qemu/*.xml"):
            self.do_file_sub(xmlfile,
                    r"(\s*passwd=\s*')([^']*)('.*)",
                    r"\1******\3")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = lilo
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin

class Lilo(Plugin, RedHatPlugin, UbuntuPlugin):
    """Lilo information
    """

    plugin_name = 'lilo'
    packages = ('lilo',)

    def setup(self):
        self.add_copy_spec("/etc/lilo.conf")
        self.add_cmd_output("lilo -q")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = logrotate
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class LogRotate(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """logrotate configuration files and debug info
    """

    plugin_name = 'logrotate'

    def setup(self):
        self.add_cmd_output("logrotate --debug /etc/logrotate.conf",
                              suggest_filename = "logrotate_debug")
        self.add_copy_specs([
            "/etc/logrotate*",
            "/var/lib/logrotate.status"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = logs
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Logs(Plugin):
    """log data """

    plugin_name = "logs"

    option_list = [
        ("logsize",
            "max size (MiB) to collect per syslog file", "", 15),
        ("all_logs",
            "collect all log files defined in syslog.conf",
            "", False)
    ]

    def setup(self):
        self.add_copy_specs([
            "/etc/syslog.conf",
            "/etc/rsyslog.conf"
        ])

        self.limit = self.get_option("logsize")
        self.add_copy_spec_limit("/var/log/boot.log", sizelimit = self.limit)
        self.add_copy_spec_limit("/var/log/cloud-init*", sizelimit = self.limit)

        if self.get_option('all_logs'):
            logs = self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+",
                                "/etc/syslog.conf")
            if self.is_installed("rsyslog") \
              or os.path.exists("/etc/rsyslog.conf"):
                logs += self.do_regex_find_all("^\S+\s+(-?\/.*$)\s+", "/etc/rsyslog.conf")
            for i in logs:
                if i.startswith("-"):
                    i = i[1:]
                if os.path.isfile(i):
                    self.add_copy_spec_limit(i, sizelimit = self.limit)


class RedHatLogs(Logs, RedHatPlugin):
    """Basic system information for RedHat based distributions"""

    def setup(self):
        super(RedHatLogs, self).setup()
        self.add_copy_spec_limit("/var/log/secure*", sizelimit = self.limit)
        self.add_copy_spec_limit("/var/log/messages*", sizelimit = self.limit)


class DebianLogs(Logs, DebianPlugin, UbuntuPlugin):
    """Basic system information for Debian and Ubuntu based distributions"""

    def setup(self):
        super(DebianLogs, self).setup()
        self.add_copy_specs([
            "/var/log/syslog",
            "/var/log/udev",
            "/var/log/kern*",
            "/var/log/mail*",
            "/var/log/dist-upgrade",
            "/var/log/installer",
            "/var/log/unattended-upgrades",
            "/var/log/apport.log",
            "/var/log/landscape"
        ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = lsbrelease
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class LsbRelease(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Linux Standard Base information
    """

    plugin_name = 'lsbrelease'

    def setup(self):
        self.add_cmd_output("lsb_release -a")
        self.add_cmd_output("lsb_release -d", suggest_filename = "lsb_release", root_symlink = "lsb-release")
        self.add_copy_spec("/etc/lsb-release*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = lvm2
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Lvm2(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """lvm2 related information 
    """

    plugin_name = 'lvm2'

    option_list = [("lvmdump", 'collect an lvmdump tarball', 'fast', False),
                  ("lvmdump-am", 'attempt to collect an lvmdump with advanced ' \
                    + 'options and raw metadata collection', 'slow', False)]

    def do_lvmdump(self, metadata=False):
        """Collects an lvmdump in standard format with optional metadata
           archives for each physical volume present.
        """
        lvmdump_cmd = "lvmdump %s -d '%s'" 
        lvmdump_opts = ""
        if metadata:
            lvmdump_opts = "-a -m"
        cmd = lvmdump_cmd % (lvmdump_opts,
                             self.get_cmd_output_path(name="lvmdump"))
        self.add_cmd_output(cmd)

    def setup(self):
        # use locking_type 0 (no locks) when running LVM2 commands, from lvm.conf:
        # Turn locking off by setting to 0 (dangerous: risks metadata corruption
        # if LVM2 commands get run concurrently).
        # None of the commands issued by sos ever modify metadata and this avoids
        # the possibility of hanging lvm commands when another process or node
        # holds a conflicting lock.
        lvm_opts = '--config="global{locking_type=0}"'

        self.add_cmd_output(
            "vgdisplay -vv %s" % lvm_opts,
            root_symlink="vgdisplay"
        )
        self.add_cmd_outputs([
            "vgscan -vvv %s" % lvm_opts,
            "pvscan -v %s" % lvm_opts,
            "pvs -a -v %s" % lvm_opts,
            "vgs -v %s" % lvm_opts,
            "lvs -a -o +devices %s" % lvm_opts
        ])

        self.add_copy_spec("/etc/lvm")

        if self.get_option('lvmdump'):
            self.do_lvmdump()
        elif self.get_option('lvmdump-am'):
            self.do_lvmdump(metadata=True)



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = maas
# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin


class Maas(Plugin, UbuntuPlugin):
    """MAAS Plugin
    """

    plugin_name = 'maas'

    option_list = [
        ('profile-name',
         'The name with which you will later refer to this remote', '', False),
        ('url', 'The URL of the remote API', '', False),
        ('credentials',
         'The credentials, also known as the API key', '', False)
    ]

    def _has_login_options(self):
        return self.get_option("url") and self.get_option("credentials") \
            and self.get_option("profile-name")

    def _remote_api_login(self):
        ret = self.call_ext_prog("maas login %s %s %s" % (
            self.get_option("profile-name"),
            self.get_option("url"),
            self.get_option("credentials")))

        return ret['status'] == 0

    def setup(self):
        self.add_copy_specs([
            "/etc/squid-deb-proxy",
            "/etc/maas",
            "/var/lib/maas/dhcp*",
            "/var/log/apache2*",
            "/var/log/maas*",
            "/var/log/upstart/maas-*",
        ])
        self.add_cmd_outputs([
            "apt-cache policy maas-*",
            "apt-cache policy python-django-*",
            "maas dumpdata"
        ])

        if self._has_login_options():
            if self._remote_api_login():
                self.add_cmd_output("maas %s commissioning-results list" %
                                    self.get_option("profile-name"))
            else:
                self.log_error(
                    "Cannot login into Maas remote API with provided creds.")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = md
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Md(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """MD subsystem information
    """

    plugin_name = 'md'

    def setup(self):
        self.add_cmd_output("mdadm -D /dev/md*")
        self.add_copy_specs([
            "/proc/mdstat",
            "/etc/mdadm.conf",
            "/dev/md/md-device-map"
        ])
        

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = memory
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Memory(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """memory usage information
    """

    plugin_name = 'memory'

    def setup(self):
        self.add_copy_specs([
            "/proc/pci",
            "/proc/meminfo",
            "/proc/vmstat",
            "/proc/slabinfo",
            "/proc/pagetypeinfo"])
        self.add_cmd_output("free", root_symlink = "free")
        self.add_cmd_output("free -m")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = mrggrid
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class MrgGrid(Plugin, RedHatPlugin):
    """MRG GRID related information
    """

    plugin_name = 'mrggrid'

    def setup(self):
        self.add_copy_specs([
            "/etc/condor/condor_config",
            "condor_status"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = mrgmessg
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class MrgMessg(Plugin, RedHatPlugin):
    """MRG Messaging related information
    """

    plugin_name = 'mrgmessg'

    def setup(self):
        self.add_copy_specs([
            "/etc/qpidd.conf",
            "/etc/sasl2/qpidd.conf",
            "/var/rhm"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = multipath
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Multipath(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """device-mapper multipath information
    """

    plugin_name = 'multipath'

    def setup(self):
        self.add_copy_specs([
            "/etc/multipath/",
            "/etc/multipath.conf"
        ])
        self.add_cmd_output([
            "multipath -l",
            "multipath -v4 -ll"
        ])



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = mysql
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Mysql(Plugin):
    """MySQL related information
    """

    plugin_name = "mysql"
    mysql_cnf = "/etc/my.cnf"

    def setup(self):
        super(Mysql, self).setup()
        self.add_copy_specs([self.mysql_cnf,
                            "/var/log/mysql*"])


class RedHatMysql(Mysql, RedHatPlugin):
    """MySQL related information for RedHat based distributions
    """

    packages = ('mysql-server', 'mysql')

    def setup(self):
        self.mysql_cnf = "/etc/my.cnf"
        super(RedHatMysql, self).setup()
        self.add_copy_spec("/etc/ld.so.conf.d/mysql*")


class DebianMysql(Mysql, DebianPlugin, UbuntuPlugin):
    """MySQL related information for Debian based distributions
    """

    packages = ('mysql-server', 'mysql-common')

    def setup(self):
        self.mysql_cnf = "/etc/mysql/my.cnf"
        super(DebianMysql, self).setup()
        self.add_copy_spec("/etc/mysql/conf.d/mysql*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = named
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists, join, normpath
import pdb

class Named(Plugin):
    """named related information
    """

    plugin_name = "named"
    named_conf = "/etc/named.conf"
    config_files = named_conf

    def setup(self):
        for cfg in self.config_files:
            if exists(cfg):
                self.add_copy_specs([
                    cfg,
                    self.get_dns_dir(cfg)
                ])
                self.add_forbidden_path(join(self.get_dns_dir(cfg),
                                        "chroot/dev"))
                self.add_forbidden_path(join(self.get_dns_dir(cfg),
                                        "chroot/proc"))

    def get_dns_dir(self, config_file):
        """ grab directory path from named{conf,boot}
        """
        directory_list = self.do_regex_find_all("directory\s+\"(.*)\"", config_file)
        if directory_list:
            return normpath(directory_list[0])
        else:
            return ""

    def postproc(self):
        match = r"(\s*arg \"password )[^\"]*"
        subst = r"\1******"
        self.do_file_sub(self.named_conf, match, subst)


class RedHatNamed(Named, RedHatPlugin):
    """named related information for RedHat based distribution
    """

    named_conf = "/etc/named.conf"
    config_files = ("/etc/named.conf",
                    "/etc/named.boot")
    files = (named_conf, '/etc/sysconfig/named')
    packages = ('bind',)

    def setup(self):
        super(RedHatNamed, self).setup()
        self.add_copy_spec("/etc/named/")
        self.add_copy_spec("/etc/sysconfig/named")
        self.add_cmd_output("klist -ket /etc/named.keytab")
        self.add_forbidden_path("/etc/named.keytab")
        return


class DebianNamed(Named, DebianPlugin, UbuntuPlugin):
    """named related information for Debian based distribution
    """

    files = ('/etc/bind/named.conf')
    packages = ('bind9',)
    named_conf = "/etc/bind/named.conf"
    config_files = (named_conf,
                    "/etc/bind/named.conf.options",
                    "/etc/bind/named.conf.local")

    def setup(self):
        super(DebianNamed, self).setup()
        self.add_copy_spec("/etc/bind/")
        return


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = networking
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re

class Networking(Plugin):
    """network related information
    """
    plugin_name = "networking"
    trace_host = "www.example.com"
    option_list = [("traceroute", "collects a traceroute to %s" % trace_host,
                        "slow", False)]
    
    def setup(self):
        super(Networking, self).setup()

    def get_bridge_name(self,brctl_file):
        """Return a list for which items are bridge name according to the
        output of brctl show stored in brctl_file.
        """
        out=[]
        try:
            brctl_out = open(brctl_file).read()
        except:
            return out
        for line in brctl_out.splitlines():
            if line.startswith("bridge name") \
               or line.isspace() \
               or line[:1].isspace():
                continue
            br_name, br_rest = line.split(None, 1)
            out.append(br_name)
        return out

    def get_eth_interfaces(self,ip_link_out):
        """Return a dictionary for which keys are ethernet interface
        names taken from the output of "ip -o link".
        """
        out={}
        for line in ip_link_out.splitlines():
            match=re.match('.*link/ether', line)
            if match:
                iface=match.string.split(':')[1].lstrip()
                out[iface]=True
        return out

    def collect_iptable(self,tablename):
        """ When running the iptables command, it unfortunately auto-loads
        the modules before trying to get output.  Some people explicitly
        don't want this, so check if the modules are loaded before running
        the command.  If they aren't loaded, there can't possibly be any
        relevant rules in that table """


        if self.check_ext_prog("grep -q %s /proc/modules" % tablename):
            cmd = "iptables -t "+tablename+" -nvL"
            self.add_cmd_output(cmd)

    def setup(self):
        self.add_copy_specs([
            "/proc/net/",
            "/etc/nsswitch.conf",
            "/etc/yp.conf",
            "/etc/inetd.conf",
            "/etc/xinetd.conf",
            "/etc/xinetd.d",
            "/etc/host*",
            "/etc/resolv.conf",
            "/etc/network*",
            "/etc/NetworkManager/NetworkManager.conf",
            "/etc/NetworkManager/system-connections",
            "/etc/dnsmasq*",
            "/sys/class/net/*/flags"
        ])
        self.add_forbidden_path("/proc/net/rpc/use-gss-proxy")
        self.add_forbidden_path("/proc/net/rpc/*/channel")
        self.add_forbidden_path("/proc/net/rpc/*/flush")

        ip_addr_file=self.get_cmd_output_now("ip -o addr", root_symlink = "ip_addr")
        self.add_cmd_output("route -n", root_symlink = "route")
        self.collect_iptable("filter")
        self.collect_iptable("nat")
        self.collect_iptable("mangle")
        self.add_cmd_output("netstat -neopa", root_symlink = "netstat")
        self.add_cmd_outputs([
            "netstat -s",
            "netstat -agn",
            "ip route show table all",
            "ip -6 route show table all",
            "ip link",
            "ip address",
            "ifenslave -a",
            "ip mroute show",
            "ip maddr show",
            "ip neigh show"
        ])
        ip_link_result=self.call_ext_prog("ip -o link")
        if ip_link_result['status'] == 0:
            for eth in self.get_eth_interfaces(ip_link_result['output']):
                self.add_cmd_outputs([
                    "ethtool "+eth,
                    "ethtool -i "+eth,
                    "ethtool -k "+eth,
                    "ethtool -S "+eth,
                    "ethtool -a "+eth,
                    "ethtool -c "+eth,
                    "ethtool -g "+eth
                ])

        brctl_file=self.get_cmd_output_now("brctl show")
        if brctl_file:
            for br_name in self.get_bridge_name(brctl_file):
                self.add_cmd_output("brctl showstp "+br_name)

        if self.get_option("traceroute"):
            self.add_cmd_output("/bin/traceroute -n %s" % self.trace_host)

        return

    def postproc(self):
        for root, dirs, files in os.walk("/etc/NetworkManager/system-connections"):
            for net_conf in files:
                self.do_file_sub("/etc/NetworkManager/system-connections/"+net_conf, r"psk=(.*)",r"psk=***")

class RedHatNetworking(Networking, RedHatPlugin):
    """network related information for RedHat based distribution
    """
    trace_host = "rhn.redhat.com"
    def setup(self):
        super(RedHatNetworking, self).setup()

class UbuntuNetworking(Networking, UbuntuPlugin):
    """network related information for Ubuntu based distribution
    """
    trace_host = "archive.ubuntu.com"

    def setup(self):
        super(UbuntuNetworking, self).setup()

        self.add_copy_specs([
            "/etc/resolvconf",
            "/etc/network/interfaces",
            "/etc/network/interfaces.d",
            "/etc/ufw",
            "/var/log/ufw.Log",
            "/etc/resolv.conf"
        ])
        self.add_cmd_outputs([
            "/usr/sbin/ufw status",
            "/usr/sbin/ufw app list"
        ])
        if self.get_option("traceroute"):
            self.add_cmd_output("/usr/sbin/traceroute -n %s" % self.trace_host)


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = neutron
## Copyright (C) 2013 Red Hat, Inc., Brent Eagles <beagles@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import re

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

# The Networking plugin includes most of what is needed from a snapshot
# of the networking, so we only need to focus on the parts that are specific
# to OpenStack Networking. The Process plugin should capture the dnsmasq
# command line. The libvirt plugin grabs the instance's XML definition which
# has the interface names for an instance. So what remains is relevant database
# info...

class Neutron(Plugin):
    """OpenStack Networking (quantum/neutron) related information
    """
    plugin_name = "neutron"

    option_list = [("log", "Gathers all Neutron logs", "slow", False),
                   ("quantum", "Overrides checks for newer Neutron components",
                    "fast", False)]

    component_name = "neutron"

    def setup(self):
        if os.path.exists("/etc/neutron/") and self.get_option("quantum", False):
            self.component_name = self.plugin_name
        else:
            self.component_name = "quantum"

        self.add_copy_specs([
            "/etc/%s/" % self.component_name,
            "/var/log/%s/" % self.component_name
        ])

        self.netns_dumps()
        self.get_ovs_dumps()


    def get_ovs_dumps(self):
        # Check to see if we are using the Open vSwitch plugin. If not we 
        # should be able to skip the rest of the dump.
        ovs_conf_check = self.call_ext_prog('grep "^core_plugin.*openvswitch" ' +
            ("/etc/%s/*.conf" + self.component_name))
        if not (ovs_conf_check['status'] == 0):
            return
        if len(ovs_conf_check['output'].splitlines()) == 0:
            return

        # The '-s' option enables dumping of packet counters on the
        # ports.
        self.add_cmd_output("ovs-dpctl -s show")

        # The '-t 5' adds an upper bound on how long to wait to connect
        # to the Open vSwitch server, avoiding hangs when running sosreport.
        self.add_cmd_output("ovs-vsctl -t 5 show")

    def netns_dumps(self):
        # It would've been beautiful if we could get parts of the networking
        # plugin to run in different namespaces. There are a couple of options
        # in the short term: create a local instance and "borrow" some of the
        # functionality, or simply copy some of the functionality.
        prefixes = ["qdhcp", "qrouter"]
        ip_netns_result = self.call_ext_prog("ip netns")
        if not (ip_netns_result['status'] == 0):
            return
        nslist = ip_netns_result['output']
        lease_directories = []
        if nslist:
            for nsname in nslist.splitlines():
                prefix, netid = nsname.split('-', 1)
                if len(netid) > 0 and prefix in prefixes:
                    self.ns_gather_data(nsname)
                    lease_directories.append("/var/lib/%s/dhcp/%s/" %
                        (self.component_name, netid))
            self.add_copy_specs(lease_directories)

    # TODO: Refactor! Copied from Networking plugin.
    def get_interface_name(self,ip_addr_out):
        """Return a dictionary for which key are interface name according to the
        output of ifconifg-a stored in ifconfig_file.
        """
        out={}
        for line in ip_addr_out.splitlines():
            match=re.match('.*link/ether', line)
            if match:
                int=match.string.split(':')[1].lstrip()
                out[int]=True
        return out
        
    def ns_gather_data(self, nsname):
        cmd_prefix = "ip netns exec %s " % nsname
        self.add_cmd_outputs([
            cmd_prefix + "iptables-save",
            cmd_prefix + "ifconfig -a",
            cmd_prefix + "route -n"
        ])
        # borrowed from networking plugin
        ip_addr_result=self.call_ext_prog(cmd_prefix + "ip -o addr")
        if ip_addr_result['status'] == 0:
            for eth in self.get_interface_name(ip_addr_result['output']):
                # Most, if not all, IFs in the namespaces are going to be 
                # virtual. The '-a', '-c' and '-g' options are not likely to be
                # supported so these ops are not copied from the network
                # plugin.
                self.add_cmd_outputs([
                    cmd_prefix + "ethtool "+eth,
                    cmd_prefix + "ethtool -i "+eth,
                    cmd_prefix + "ethtool -k "+eth,
                    cmd_prefix + "ethtool -S "+eth
                ])

        # As all of the bridges are in the "global namespace", we do not need
        # to gather info on them.

    def gen_pkg_tuple(self, packages):
        names = []
        for p in packages:
            names.append(p % { "comp" : self.component_name })
        return tuple(names)

class DebianNeutron(Neutron, DebianPlugin, UbuntuPlugin):
    """OpenStack Neutron related information for Debian based distributions
    """
    package_list_template = [
        '%(comp)s-common',
        '%(comp)s-plugin-cisco',
        '%(comp)s-plugin-linuxbridge-agent',
        '%(comp)s-plugin-nicira',
        '%(comp)s-plugin-openvswitch',
        '%(comp)s-plugin-openvswitch-agent',
        '%(comp)s-plugin-ryu',
        '%(comp)s-plugin-ryu-agent',
        '%(comp)s-server',
        'python-%(comp)s',
        'python-%(comp)sclient'
    ]

    def check_enabled(self):
        return self.is_installed("%s-common" % self.component_name)

    def setup(self):
        super(DebianNeutron, self).setup()
        self.packages = self.gen_pkg_tuple(self.package_list_template)
        self.add_copy_spec("/etc/sudoers.d/%s_sudoers" % self.component_name)



class RedHatNeutron(Neutron, RedHatPlugin):
    """OpenStack Neutron related information for Red Hat distributions
    """

    package_list_template = [
        'openstack-%(comp)s', 
        'openstack-%(comp)s-linuxbridge'
        'openstack-%(comp)s-metaplugin',
        'openstack-%(comp)s-openvswitch',
        'openstack-%(comp)s-bigswitch',
        'openstack-%(comp)s-brocade',
        'openstack-%(comp)s-cisco',
        'openstack-%(comp)s-hyperv',
        'openstack-%(comp)s-midonet',
        'openstack-%(comp)s-nec'
        'openstack-%(comp)s-nicira',
        'openstack-%(comp)s-plumgrid',
        'openstack-%(comp)s-ryu',
        'python-%(comp)s',
        'python-%(comp)sclient'
    ]

    def check_enabled(self):
        return self.is_installed("openstack-%s" % self.component_name)

    def setup(self):
        super(RedHatNeutron, self).setup()
        self.packages = self.gen_pkg_tuple(self.package_list_template)
        self.add_copy_spec("/etc/sudoers.d/%s-rootwrap" % self.component_name)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = nfs
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Nfs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """NFS related information
    """
    plugin_name = 'nfs'
    packages = ['nfs-utils']

    def setup(self):
        self.add_copy_specs([
                "/etc/nfsmount.conf",
                "/etc/idmapd.conf",
                "/proc/fs/nfsfs/servers",
                "/proc/fs/nfsfs/volumes"
        ])
        return


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = nfsserver
## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os
from stat import ST_SIZE

class NfsServer(Plugin, RedHatPlugin):
    """NFS server-related information
    """

    plugin_name = 'nfsserver'

    def check_enabled(self):
        default_runlevel = self.policy().default_runlevel()
        nfs_runlevels = self.policy().runlevel_by_service("nfs")
        if default_runlevel in nfs_runlevels:
            return True

        try:
            exports = os.stat("/etc/exports")[ST_SIZE]
            xtab = os.stat("/var/lib/nfs/xtab")[ST_SIZE]
            if exports or xtab:
                return True
        except:
            pass

        return False

    def setup(self):
        self.add_copy_specs([
            "/etc/exports",
            "/var/lib/nfs/etab",
            "/var/lib/nfs/xtab",
            "/var/lib/nfs/rmtab"])
        self.add_cmd_outputs([
            "rpcinfo -p localhost",
            "nfsstat -o all"
        ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = nis
## nis.py
## A plugin to gather all the NIS information

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Nis(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """NIS related information
    """

    plugin_name = 'nis'

    files = ('/var/yp',)

    def setup(self):
        self.add_copy_specs([
            "/etc/yp*.conf",
            "/var/yp/*"
        ])
        self.add_cmd_output("domainname")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = nscd
## Copyright (C) 2007 Shijoe George <spanjikk@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Nscd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """NSCD related information
    """

    plugin_name = 'nscd'

    option_list = [("nscdlogsize", "max size (MiB) to collect per nscd log file",
                   "", 50)]

    files = ('/etc/nscd.conf',)
    packages = ('nscd',)

    def setup(self):
        self.add_copy_spec("/etc/nscd.conf")

        opt = self.file_grep(r"^\s*logfile", "/etc/nscd.conf")
        if (len(opt) > 0):
            for o in opt:
                f = o.split()
                self.add_copy_spec_limit(f[1],
                    sizelimit = self.option_enabled("nscdlogsize"))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ntp
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Ntp(Plugin):
    """NTP related information
    """

    plugin_name = "ntp"

    packages = ('ntp',)

    def setup(self):
        self.add_copy_specs([
            "/etc/ntp.conf",
            "/etc/ntp/step-tickers",
            "/etc/ntp/ntpservers"
        ])
        self.add_cmd_output("ntptime")


class RedHatNtp(Ntp, RedHatPlugin):
    """NTP related information for RedHat based distributions
    """

    def setup(self):
        super(RedHatNtp, self).setup()
        self.add_copy_spec("/etc/sysconfig/ntpd")
        self.add_cmd_output("ntpstat")


class DebianNtp(Ntp, DebianPlugin, UbuntuPlugin):
    """NTP related information for Debian based distributions
    """

    def setup(self):
        super(DebianNtp, self).setup()
        self.add_copy_spec('/etc/default/ntp')


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = oddjob
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Oddjob(Plugin, RedHatPlugin):
    """oddjob related information
    """

    plugin_name = 'oddjob'

    files = ('/etc/oddjobd.conf',)
    packages = ('oddjob',)

    def setup(self):
        self.add_copy_specs([
            "/etc/oddjobd.conf",
            "/etc/oddjobd.conf.d",
            "/etc/dbus-1/system.d/oddjob.conf"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openhpi
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class OpenHPI(Plugin, RedHatPlugin):
    """OpenHPI related information
    """

    plugin_name = 'openhpi'

    def setup(self):
        self.add_copy_specs([
            "/etc/openhpi/openhpi.conf",
            "/etc/openhpi/openhpiclient.conf"
        ])

    def postproc(self):
        self.do_file_sub("/etc/openhpi/openhpi.conf",
                        r'(\s*[Pp]ass.*\s*=\s*).*', r'\1********')


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openshift
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Openshift(Plugin, RedHatPlugin):
    '''Openshift related information'''

    plugin_name = "Openshift"

    option_list = [("broker", "Gathers broker specific files", "slow", False),
           ("node", "Gathers node specific files", "slow", False)]

    def setup(self):
        self.add_copy_specs([
            "/etc/openshift-enterprise-version",
            "/etc/openshift/",
            "/etc/dhcp/dhclient-*"
        ])

        if self.option_enabled("broker"):
            self.add_copy_specs([
                "/var/log/activemq",
                "/var/log/mongodb",
                "/var/log/openshift",
                "/var/www/openshift/broker/log",
                "/var/www/openshift/broker/httpd/logs/",
                "/var/www/openshift/console/log",
                "/var/www/openshift/console/httpd/logs",
                "/var/log/openshift/user_action.log"
            ])

            self.add_cmd_outputs([
                "oo-accpet-broker -v",
                "oo-admin-chk -v",
                "mco ping",
                "gem list --local"
            ])
            runat = '/var/www/openshift/broker/'
            self.add_cmd_output("bundle --local", runat)
                                        

        if self.option_enabled("node"):
            self.add_copy_specs([
                "/var/log/openshift/node",
                "/cgroup/all/openshift",
                "/var/log/mcollective.log",
                "/var/log/openshift-gears-async-start.log",
                "/var/log/httpd/error_log"
            ])

            self.add_cmd_outputs([
                "oo-accept-node -v",
                "oo-admin-ctl-gears list",
                "ls -l /var/lib/openshift"
            ])

    def postproc(self):
        self.do_file_sub('/etc/openshift/broker.conf',
                r"(MONGO_PASSWORD=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/broker.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/console.conf',
                r"(SESSION_SECRET=)(.*)",
                r"\1*******")

        self.do_file_sub('/etc/openshift/htpasswd',
                r"(.*:)(.*)",
                r"\1********")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openssl
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class OpenSSL(Plugin):
    """openssl related information
    """

    plugin_name = "openssl"
    packages = ('openssl',)

    def postproc(self):
        protect_keys = [
            "input_password",
            "output_password",
            "challengePassword"
        ]

        regexp = r"(?m)^(\s*#?\s*(%s).*=)(.*)" % "|".join(protect_keys)

        self.do_file_sub(
            '/etc/ssl/openssl.cnf',
            regexp,
            r"\1 ******"
        )

class RedHatOpenSSL(OpenSSL, RedHatPlugin):
    """openssl related information for Red Hat distributions
    """

    files = ('/etc/pki/tls/openssl.cnf',)

    def setup(self):
        super(RedHatOpenSSL, self).setup()
        self.add_copy_spec("/etc/pki/tls/openssl.cnf")

class DebianOpenSSL(OpenSSL, DebianPlugin, UbuntuPlugin):
    """openssl related information for Debian distributions
    """

    files = ('/etc/ssl/openssl.cnf',)

    def setup(self):
        super(DebianOpenSSL, self).setup()
        self.add_copy_spec("/etc/ssl/openssl.cnf")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_ceilometer
## Copyright (C) 2013 Red Hat, Inc., Eoghan Lynn <eglynn@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos import plugins


class OpenStackCeilometer(plugins.Plugin):
    """Openstack Ceilometer related information."""
    plugin_name = "openstack-ceilometer"

    option_list = [("log", "gathers openstack-ceilometer logs", "slow", False)]

    def setup(self):
        # Ceilometer
        self.add_copy_specs([
            "/etc/ceilometer/",
            "/var/log/ceilometer"
        ])

class DebianOpenStackCeilometer(OpenStackCeilometer, plugins.DebianPlugin, plugins.UbuntuPlugin):
    """OpenStackCeilometer related information for Debian based distributions."""

    packages = (
        'ceilometer-api',
        'ceilometer-agent-central',
        'ceilometer-agent-compute',
        'ceilometer-collector',
        'ceilometer-common',
        'python-ceilometer',
        'python-ceilometerclient'
    )


class RedHatOpenStackCeilometer(OpenStackCeilometer, plugins.RedHatPlugin):
    """OpenStackCeilometer related information for Red Hat distributions."""

    packages = (
        'openstack-ceilometer',
        'openstack-ceilometer-api',
        'openstack-ceilometer-central',
        'openstack-ceilometer-collector',
        'openstack-ceilometer-common',
        'openstack-ceilometer-compute',
        'python-ceilometerclient'
    )

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_cinder
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackCinder(Plugin):
    """openstack cinder related information
    """
    plugin_name = "openstack-cinder"

    option_list = [("log", "gathers openstack cinder logs", "slow", True),
                   ("db", "gathers openstack cinder db version", "slow", False)]

    def setup(self):
        if self.option_enabled("db"):
            self.add_cmd_output(
                "cinder-manage db version",
                suggest_filename="cinder_db_version")

        self.add_copy_specs(["/etc/cinder/"])

        if self.option_enabled("log"):
            self.add_copy_specs(["/var/log/cinder/"])


class DebianOpenStackCinder(OpenStackCinder, DebianPlugin, UbuntuPlugin):
    """OpenStack Cinder related information for Debian based distributions
    """

    cinder = False
    packages = (
        'cinder-api',
        'cinder-backup',
        'cinder-common',
        'cinder-scheduler',
        'cinder-volume',
        'python-cinder',
        'python-cinderclient'
    )

    def check_enabled(self):
        self.cinder = self.is_installed("cinder-common")
        return self.cinder

    def setup(self):
        super(DebianOpenStackCinder, self).setup()

class RedHatOpenStackCinder(OpenStackCinder, RedHatPlugin):
    """OpenStack related information for Red Hat distributions
    """

    cinder = False
    packages = ('openstack-cinder',
                'python-cinder',
                'python-cinderclient')

    def check_enabled(self):
        self.cinder = self.is_installed("openstack-cinder")
        return self.cinder

    def setup(self):
        super(RedHatOpenStackCinder, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/cinder"])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_glance
## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos import plugins


class OpenStackGlance(plugins.Plugin):
    """OpenstackGlance related information."""
    plugin_name = "openstack-glance"

    option_list = [("log", "gathers openstack-glance logs", "slow", False)]

    def setup(self):
        # Glance
        self.add_cmd_output(
            "glance-manage db_version",
            suggest_filename="glance_db_version"
        )
        self.add_copy_specs([
            "/etc/glance/",
            "/var/log/glance/"
        ])


class DebianOpenStackGlance(OpenStackGlance,
                            plugins.DebianPlugin,
                            plugins.UbuntuPlugin):
    """OpenStackGlance related information for Debian based distributions."""

    packages = (
        'glance',
        'glance-api',
        'glance-client',
        'glance-common',
        'glance-registry',
        'python-glance'
    )


class RedHatOpenStackGlance(OpenStackGlance, plugins.RedHatPlugin):
    """OpenStackGlance related information for Red Hat distributions."""

    packages = (
        'openstack-glance',
        'python-glanceclient'
    )

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_heat
## Copyright (C) 2013 Red Hat, Inc.

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos import plugins


class OpenStackHeat(plugins.Plugin):
    """openstack related information
    """
    plugin_name = "openstack-heat"

    option_list = [("log", "gathers openstack-heat logs", "slow", False)]

    def setup(self):
        # Heat
        self.add_cmd_output(
            "heat-manage db_version",
            suggest_filename="heat_db_version"
        )
        self.add_copy_specs([
            "/etc/heat/",
            "/var/log/heat/"
        ])


class DebianOpenStack(OpenStackHeat,
                      plugins.DebianPlugin,
                      plugins.UbuntuPlugin):
    """OpenStackHeat related information for Debian based distributions."""

    packages = (
        'heat-api',
        'heat-api-cfn',
        'heat-api-cloudwatch',
        'heat-common',
        'heat-engine',
        'python-heat',
        'python-heatclient'
    )


class RedHatOpenStack(OpenStackHeat, plugins.RedHatPlugin):
    """OpenStackHeat related information for Red Hat distributions."""

    packages = (
        'openstack-heat-api',
        'openstack-heat-api-cfn',
        'openstack-heat-api-cloudwatch',
        'openstack-heat-cli',
        'openstack-heat-common',
        'openstack-heat-engine',
        'python-heatclient'
    )

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_horizon
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackHorizon(Plugin):
    """openstack horizon related information
    """

    plugin_name = "openstack-horizon"
    option_list = [("log", "gathers openstack horizon logs", "slow", True)]

    def setup(self):
        self.add_copy_spec("/etc/openstack-dashboard/")
        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/horizon/")


class DebianOpenStackHorizon(OpenStackHorizon, DebianPlugin):
    """OpenStack Horizon related information for Debian based distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-apache'
    )

    def setup(self):
        super(DebianOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/sites-available/")


class UbuntuOpenStackHorizon(OpenStackHorizon, UbuntuPlugin):
    """OpenStack Horizon related information for Ubuntu based distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-ubuntu-theme'
    )

    def setup(self):
        super(UbuntuOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/conf.d/openstack-dashboard.conf")


class RedHatOpenStackHorizon(OpenStackHorizon, RedHatPlugin):
    """OpenStack Horizon related information for Red Hat distributions
    """

    packages = (
        'python-django-horizon',
        'openstack-dashboard'
    )

    def setup(self):
        super(RedHatOpenStackHorizon, self).setup()
        self.add_copy_spec("/etc/httpd/conf.d/openstack-dashboard.conf")
        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/httpd/")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_keystone
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackKeystone(Plugin):
    """openstack keystone related information
    """
    plugin_name = "openstack-keystone"

    option_list = [("log", "gathers openstack keystone logs", "slow", True),
                   ("nopw", "dont gathers keystone passwords", "slow", True)]

    def setup(self):
        self.add_copy_specs([
            "/etc/keystone/default_catalog.templates",
            "/etc/keystone/keystone.conf",
            "/etc/keystone/logging.conf",
            "/etc/keystone/policy.json"
        ])

        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/keystone/")

    def postproc(self):
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(?m)^(admin_password.*=)(.*)",
                    r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(?m)^(admin_token.*=)(.*)",
                    r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(?m)^(connection.*=.*mysql://)(.*)(:)(.*)(@)(.*)",
                    r"\1\2:******@\6")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(?m)^(password.*=)(.*)",
                    r"\1 ******")
        self.do_file_sub('/etc/keystone/keystone.conf',
                    r"(?m)^(ca_password.*=)(.*)",
                    r"\1 ******")


class DebianOpenStackKeystone(OpenStackKeystone, DebianPlugin, UbuntuPlugin):
    """OpenStack Keystone related information for Debian based distributions
    """

    packages = (
        'keystone',
        'python-keystone',
        'python-keystoneclient'
    )


class RedHatOpenStackKeystone(OpenStackKeystone, RedHatPlugin):
    """OpenStack Keystone related information for Red Hat distributions
    """

    packages = (
        'openstack-keystone',
        'python-keystone',
        'python-django-openstack-auth',
        'python-keystoneclient'
    )

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_neutron
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackNeutron(Plugin):
    """openstack neutron related information
    """
    plugin_name = "openstack-neutron"

    option_list = [("log", "gathers openstack neutron logs", "slow", True)]

    def setup(self):
        self.add_copy_spec("/etc/neutron/")

        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/neutron/")


class DebianOpenStackNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    """OpenStack Neutron related information for Debian based distributions
    """

    neutron = False
    packages = (
        'neutron-common',
        'neutron-plugin-cisco',
        'neutron-plugin-linuxbridge-agent',
        'neutron-plugin-nicira',
        'neutron-plugin-openvswitch',
        'neutron-plugin-openvswitch-agent',
        'neutron-plugin-ryu',
        'neutron-plugin-ryu-agent',
        'neutron-server',
        'python-neutron',
        'python-neutronclient'
    )

    def check_enabled(self):
        self.neutron = self.is_installed("neutron-common")
        return self.neutron

    def setup(self):
        super(DebianOpenStackNeutron, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/neutron_sudoers"])


class RedHatOpenStackNeutron(OpenStackNeutron, RedHatPlugin):
    """OpenStack Neutron related information for Red Hat distributions
    """

    neutron = False
    packages = (
        'openstack-neutron-bigswitch',
        'openstack-neutron-brocade',
        'openstack-neutron-cisco',
        'openstack-neutron-hyperv',
        'openstack-neutron-linuxbridge',
        'openstack-neutron-metaplugin',
        'openstack-neutron-midonet',
        'openstack-neutron-nec',
        'openstack-neutron-nicira',
        'openstack-neutron-openvswitch',
        'openstack-neutron-plumgrid',
        'openstack-neutron-ryu',
        'python-neutron',
        'python-neutronclient',
        'openstack-neutron'
    )

    def check_enabled(self):
        self.neutron = self.is_installed("openstack-neutron")
        return self.neutron

    def setup(self):
        super(RedHatOpenStackNeutron, self).setup()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_nova
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackNova(Plugin):
    """openstack nova related information
    """
    plugin_name = "openstack-nova"

    option_list = [("log", "gathers openstack nova logs", "slow", True),
                   ("cmds", "gathers openstack nova commands", "slow", False)]

    def setup(self):
        if self.option_enabled("cmds"):
            self.add_cmd_output(
                "nova-manage config list",
                suggest_filename="nova_config_list")
            self.add_cmd_output(
                "nova-manage service list",
                suggest_filename="nova_service_list")
            self.add_cmd_output(
                "nova-manage db version",
                suggest_filename="nova_db_version")
            self.add_cmd_output(
                "nova-manage fixed list",
                suggest_filename="nova_fixed_ip_list")
            self.add_cmd_output(
                "nova-manage floating list",
                suggest_filename="nova_floating_ip_list")
            self.add_cmd_output(
                "nova-manage flavor list",
                suggest_filename="nova_flavor_list")
            self.add_cmd_output(
                "nova-manage network list",
                suggest_filename="nova_network_list")
            self.add_cmd_output(
                "nova-manage vm list",
                suggest_filename="nova_vm_list")

        if self.option_enabled("log"):
            self.add_copy_spec("/var/log/nova/")

        self.add_copy_spec("/etc/nova/")

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "connection", "sql_connection", "admin_password"
        ]

        regexp = r"((?m)^\s*#*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        for conf_file in ["/etc/nova/nova.conf", "/etc/nova/api-paste.ini"]:
            self.do_file_sub(conf_file, regexp, r"\1*********")


class DebianOpenStackNova(OpenStackNova, DebianPlugin, UbuntuPlugin):
    """OpenStack nova related information for Debian based distributions
    """

    nova = False
    packages = (
        'nova-api-ec2',
        'nova-api-metadata',
        'nova-api-os-compute',
        'nova-api-os-volume',
        'nova-common',
        'nova-compute',
        'nova-compute-kvm',
        'nova-compute-lxc',
        'nova-compute-qemu',
        'nova-compute-uml',
        'nova-compute-xcp',
        'nova-compute-xen',
        'nova-xcp-plugins',
        'nova-consoleauth',
        'nova-network',
        'nova-scheduler',
        'nova-volume',
        'novnc',
        'python-nova',
        'python-novaclient',
        'python-novnc'
    )

    def check_enabled(self):
        self.nova = self.is_installed("nova-common")
        return self.nova

    def setup(self):
        super(DebianOpenStackNova, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/nova_sudoers"])


class RedHatOpenStackNova(OpenStackNova, RedHatPlugin):
    """OpenStack nova related information for Red Hat distributions
    """

    nova = False
    packages = (
        'openstack-nova-common',
        'openstack-nova-network',
        'openstack-nova-conductor',
        'openstack-nova-conductor',
        'openstack-nova-scheduler',
        'openstack-nova-console',
        'openstack-nova-novncproxy',
        'openstack-nova-compute',
        'openstack-nova-api',
        'openstack-nova-cert',
        'openstack-nova-cells',
        'openstack-nova-objectstore',
        'python-nova',
        'python-novaclient',
        'novnc'
    )

    def check_enabled(self):
        self.nova = self.is_installed("openstack-nova-common")
        return self.nova

    def setup(self):
        super(RedHatOpenStackNova, self).setup()
        self.add_copy_specs([
            "/etc/logrotate.d/openstack-nova",
            "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
            "/etc/sudoers.d/nova",
            "/etc/security/limits.d/91-nova.conf",
            "/etc/sysconfig/openstack-nova-novncproxy"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openstack_swift
## Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos import plugins


class OpenStackSwift(plugins.Plugin):
    """OpenstackSwift related information."""
    plugin_name = "openstack-swift"

    option_list = [("log", "gathers openstack-swift logs", "slow", False)]

    def setup(self):
        # Swift
        self.add_copy_spec("/etc/swift/")

class DebianOpenStackSwift(OpenStackSwift, plugins.DebianPlugin, plugins.UbuntuPlugin):
    """OpenStackSwift related information for Debian based distributions."""

    packages = (
        'swift',
        'swift-account',
        'swift-container',
        'swift-object',
        'swift-proxy',
        'swauth',
        'python-swift',
        'python-swauth'
    )


class RedHatOpenStackSwift(OpenStackSwift, plugins.RedHatPlugin):
    """OpenStackSwift related information for Red Hat distributions."""

    packages = (
        'openstack-swift',
        'openstack-swift-account',
        'openstack-swift-container',
        'openstack-swift-object',
        'openstack-swift-proxy',
        'swift',
        'python-swiftclient'
    )

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = openswan
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Openswan(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ipsec related information
    """

    plugin_name = 'openswan'
    option_list = [("ipsec-barf",
                   "collect the output of the ipsec barf command",
                   "slow", False)]

    files = ('/etc/ipsec.conf',)
    packages = ('openswan',)

    def setup(self):
        self.add_copy_specs([
            "/etc/ipsec.conf",
            "/etc/ipsec.d"
        ])
        self.add_cmd_output("ipsec verify")
        if self.get_option("ipsec-barf"):
            self.add_cmd_output("ipsec barf")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ovirt
## Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>
## Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
## Copyright (C) 2010 Red Hat, Inc.

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import re
import signal


from sos.plugins import Plugin, RedHatPlugin


# Class name must be the same as file name and method names must not change
class Ovirt(Plugin, RedHatPlugin):
    """oVirt Engine related information"""

    DB_PASS_FILES = re.compile(
        flags=re.VERBOSE,
        pattern=r"""
        ^
        /etc/
        (rhevm|ovirt-engine)/
        engine.conf
        (\.d/.+.conf)?
        $
        """
    )

    DEFAULT_SENSITIVE_KEYS = (
        'ENGINE_DB_PASSWORD:ENGINE_PKI_TRUST_STORE_PASSWORD:'
        'ENGINE_PKI_ENGINE_STORE_PASSWORD'
    )

    plugin_name = "ovirt"

    option_list = [
        ('jbosstrace', 'Enable oVirt Engine JBoss stack trace collection', '', True),
        ('sensitive_keys', 'Sensitive keys to be masked', '', DEFAULT_SENSITIVE_KEYS)
    ]

    def setup(self):
        if self.get_option('jbosstrace'):
            engine_pattern = "^ovirt-engine\ -server.*jboss-modules.jar"
            pgrep = "pgrep -f '%s'" % engine_pattern
            lines = self.call_ext_prog(pgrep)['output'].splitlines()
            engine_pids = [int(x) for x in lines]
            if not engine_pids:
                self.soslog.error('Unable to get ovirt-engine pid')
                self.add_alert('Unable to get ovirt-engine pid')
            for pid in engine_pids:
                try:
                    # backtrace written to '/var/log/ovirt-engine/console.log
                    os.kill(pid, signal.SIGQUIT)
                except OSError as e:
                    self.soslog.error('Unable to send signal to %d' % pid, e)

        self.add_forbidden_path('/etc/ovirt-engine/.pgpass')
        self.add_forbidden_path('/etc/rhevm/.pgpass')
        # Copy engine config files.
        self.add_copy_specs([
            "/etc/ovirt-engine",
            "/etc/rhevm",
            "/var/log/ovirt-engine",
            "/var/log/rhevm",
            "/etc/sysconfig/ovirt-engine",
            "/usr/share/ovirt-engine/conf",
            "/var/log/ovirt-guest-agent",
            "/var/lib/ovirt-engine/setup-history.txt",
            "/var/lib/ovirt-engine/setup/answers",
            "/var/lib/ovirt-engine/external_truststore",
            "/var/tmp/ovirt-engine/config"
        ])

    def postproc(self):
        """
        Obfuscate sensitive keys.
        """
        self.do_file_sub(
            "/etc/ovirt-engine/engine-config/engine-config.properties",
            r"Password.type=(.*)",
            r"Password.type=********"
        )
        self.do_file_sub(
            "/etc/rhevm/rhevm-config/rhevm-config.properties",
            r"Password.type=(.*)",
            r"Password.type=********"
        )

        engine_files = (
            'ovirt-engine.xml',
            'ovirt-engine_history/current/ovirt-engine.v1.xml',
            'ovirt-engine_history/ovirt-engine.boot.xml',
            'ovirt-engine_history/ovirt-engine.initial.xml',
            'ovirt-engine_history/ovirt-engine.last.xml',
        )
        for filename in engine_files:
            self.do_file_sub(
                "/var/tmp/ovirt-engine/config/%s" % filename,
                r"<password>(.*)</password>",
                r"<password>********</password>"
            )

        self.do_file_sub(
            "/etc/ovirt-engine/redhatsupportplugin.conf",
            r"proxyPassword=(.*)",
            r"proxyPassword=********"
        )

        sensitive_keys = self.DEFAULT_SENSITIVE_KEYS
        #Handle --alloptions case which set this to True.
        keys_opt = self.get_option('sensitive_keys')
        if keys_opt and keys_opt is not True:
            sensitive_keys = keys_opt
        key_list = [x for x in sensitive_keys.split(':') if x]
        for key in key_list:
                self.do_path_regex_sub(
                    self.DB_PASS_FILES,
                    r'{key}=(.*)'.format(key=key),
                    r'{key}=********'.format(key=key)
                )

# vim: expandtab tabstop=4 shiftwidth=4

########NEW FILE########
__FILENAME__ = pam
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Pam(Plugin):
    """PAM related information
    """

    plugin_name = "pam"
    security_libs = ""

    def setup(self):
        self.add_copy_specs([
            "/etc/pam.d",
            "/etc/security"
        ])
        self.add_cmd_output("ls -lanF %s" % self.security_libs)

class RedHatPam(Pam, RedHatPlugin):
    """PAM related information for RedHat based distribution
    """
    security_libs = "/lib*/security"

    def setup(self):
        super(RedHatPam, self).setup()


class DebianPam(Pam, DebianPlugin, UbuntuPlugin):
    """PAM related information for Debian based distribution
    """
    security_libs = "/lib/x86_64-linux-gnu/security"

    def setup(self):
        super(DebianPam, self).setup()


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = pci
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Pci(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """PCI device related information
    """

    plugin_name = "pci"

    def setup(self):
        self.add_copy_specs([
            "/proc/ioports",
            "/proc/iomem",
            "/proc/bus/pci"
        ])

        self.add_cmd_output("lspci", root_symlink = "lspci")
        self.add_cmd_outputs([
            "lspci -nvv",
            "lspci -tv"
        ])



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = postfix
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Postfix(Plugin):
    """mail server related information
    """
    plugin_name = "postfix"

    packages = ('postfix',)

    def setup(self):
        self.add_copy_specs([
            "/etc/postfix/main.cf",
            "/etc/postfix/master.cf"
        ])
        self.add_cmd_output("postconf")

class RedHatPostfix(Postfix, RedHatPlugin):
    """mail server related information for RedHat based distributions
    """

    files = ('/etc/rc.d/init.d/postfix',)
    packages = ('postfix',)

    def setup(self):
        super(RedHatPostfix, self).setup()
        self.add_copy_spec("/etc/mail")

class DebianPostfix(Postfix, DebianPlugin, UbuntuPlugin):
    """mail server related information for Debian based Distribution
    """

    packages = ('postfix',)

    def setup(self):
        super(DebianPostfix, self).setup()
        self.add_copy_spec("/etc/postfix/dynamicmaps.cf")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = postgresql
## Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>
## Copyright (C) 2013 Chris J Arges <chris.j.arges@canonical.com>
## Copyright (C) 2012-2013 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
## Copyright (C) 2011 Red Hat, Inc., Jesse Jaggars <jjaggars@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import tempfile

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from sos.utilities import find


class PostgreSQL(Plugin):
    """PostgreSQL related information"""

    plugin_name = "postgresql"

    packages = ('postgresql',)

    tmp_dir = None

    option_list = [
        ('pghome', 'PostgreSQL server home directory.', '', '/var/lib/pgsql'),
        ('username', 'username for pg_dump', '', 'postgres'),
        ('password', 'password for pg_dump', '', ''),
        ('dbname', 'database name to dump for pg_dump', '', ''),
        ('dbhost', 'database hostname/IP (do not use unix socket)', '', ''),
        ('dbport', 'database server port number', '', '5432')
    ]

    def pg_dump(self):
        dest_file = os.path.join(self.tmp_dir, "sos_pgdump.tar")
        old_env_pgpassword = os.environ.get("PGPASSWORD")
        os.environ["PGPASSWORD"] = self.get_option("password")
        if self.get_option("dbhost"):
            cmd = "pg_dump -U %s -h %s -p %s -w -f %s -F t %s" % (
                self.get_option("username"),
                self.get_option("dbhost"),
                self.get_option("dbport"),
                dest_file,
                self.get_option("dbname")
            )
        else:
            cmd = "pg_dump -C -U %s -w -f %s -F t %s " % (
                self.get_option("username"),
                dest_file,
                self.get_option("dbname")
            )
        result = self.call_ext_prog(cmd)
        if old_env_pgpassword is not None:
            os.environ["PGPASSWORD"] = str(old_env_pgpassword)
        if (result['status'] == 0):
            self.add_copy_spec(dest_file)
        else:
            self.log_error(
                "Unable to execute pg_dump. Error(%s)" % (result['output'])
            )
            self.add_alert(
                "ERROR: Unable to execute pg_dump. Error(%s)" % (result['output'])
            )

    def setup(self):
        if self.get_option("dbname"):
            if self.get_option("password"):
                self.tmp_dir = tempfile.mkdtemp()
                self.pg_dump()
            else:
                self.soslog.warning(
                    "password must be supplied to dump a database."
                )
                self.add_alert(
                    "WARN: password must be supplied to dump a database."
                )
        else:
            self.soslog.warning(
                "dbname must be supplied to dump a database."
            )
            self.add_alert(
                "WARN: dbname must be supplied to dump a database."
            )

    def postproc(self):
        import shutil
        if self.tmp_dir:
            try:
                shutil.rmtree(self.tmp_dir)
            except shutil.Error:
                self.soslog.exception(
                    "Unable to remove %s." % (self.tmp_dir)
                )
                self.add_alert("ERROR: Unable to remove %s." % (self.tmp_dir))


class RedHatPostgreSQL(PostgreSQL, RedHatPlugin):
    """PostgreSQL related information for Red Hat distributions"""

    def setup(self):
        super(RedHatPostgreSQL, self).setup()

        # Copy PostgreSQL log files.
        for filename in find("*.log", self.get_option("pghome")):
            self.add_copy_spec(filename)
        # Copy PostgreSQL config files.
        for filename in find("*.conf", self.get_option("pghome")):
            self.add_copy_spec(filename)

        self.add_copy_spec(
            os.path.join(
                self.get_option("pghome"),
                "data",
                "PG_VERSION"
            )
        )
        self.add_copy_spec(
            os.path.join(
                self.get_option("pghome"),
                "data",
                "postmaster.opts"
            )
        )


class DebianPostgreSQL(PostgreSQL, DebianPlugin, UbuntuPlugin):
    """PostgreSQL related information for Debian/Ubuntu distributions"""

    def setup(self):
        super(DebianPostgreSQL, self).setup()

        self.add_copy_specs([
            "/var/log/postgresql/*.log",
            "/etc/postgresql/*/main/*.conf",
            "/var/lib/postgresql/*/main/PG_VERSION",
            "/var/lib/postgresql/*/main/postmaster.opts"
        ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = powerpc
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

## This plugin enables collection of logs for Power systems and more
## specific logs for Pseries, PowerNV platforms.

import os
from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin

class PowerPC(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """IBM Power System related information
    """

    plugin_name = 'powerpc'

    def check_enabled(self):
        return (self.policy().get_arch() == "ppc64")

    def setup(self):
        try:
            with open('/proc/cpuinfo', 'r') as fp:
                contents = fp.read()
                ispSeries = "pSeries" in contents
                isPowerNV = "PowerNV" in contents
        except:
            ispSeries = False
            isPowerNV = False

        if ispSeries or isPowerNV:
            self.add_copy_specs([
                "/proc/device-tree/",
                "/proc/loadavg",
                "/proc/locks",
                "/proc/misc",
                "/proc/swaps",
                "/proc/version",
                "/dev/nvram",
                "/var/lib/lsvpd/"
            ])
            self.add_cmd_outputs([
                "ppc64_cpu --smt",
                "ppc64_cpu --cores-present",
                "ppc64_cpu --cores-on",
                "ppc64_cpu --run-mode",
                "ppc64_cpu --frequency",
                "ppc64_cpu --dscr",
                "lscfg -vp",
                "lsmcode -A",
                "lsvpd --debug"
            ])

        if ispSeries:
            self.add_copy_specs([
                "/proc/ppc64/lparcfg",
                "/proc/ppc64/eeh",
                "/proc/ppc64/systemcfg",
                "/var/log/platform"
            ])
            self.add_cmd_outputs([
                "lsvio -des",
                "servicelog --dump",
                "servicelog_notify --list",
                "usysattn",
                "usysident",
                "serv_config -l",
                "bootlist -m both -r",
                "lparstat -i"
            ])

        if isPowerNV:
            self.add_copy_specs([
                "/proc/ppc64/",
                "/sys/kernel/debug/powerpc/",
                "/sys/firmware/opal/msglog",
                "/var/log/opal-elog/"
            ])
            if os.path.isdir("/var/log/dump"):
                self.add_cmd_output("ls -l /var/log/dump")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ppp
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Ppp(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ppp, wvdial and rp-pppoe related information
    """

    plugin_name = 'ppp'

    packages = ('ppp',)

    def setup(self):
        self.add_copy_specs([
            "/etc/wvdial.conf",
            "/etc/ppp",
            "/var/log/ppp"
        ])
        self.add_cmd_output("adsl-status")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = procenv
## Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, DebianPlugin, UbuntuPlugin

class Procenv(Plugin, DebianPlugin, UbuntuPlugin):
    """Process environment.
    """

    plugin_name = 'procenv'

    def setup(self):
        self.add_cmd_output('procenv')

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = process
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Process(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """process information
    """

    plugin_name = 'process'

    def setup(self):
        self.add_cmd_output("ps auxwww", root_symlink = "ps")
        self.add_cmd_output("pstree", root_symlink = "pstree")
        self.add_cmd_output("lsof -b +M -n -l", root_symlink = "lsof")
        self.add_cmd_outputs([
            "ps auxwwwm",
            "ps alxwww"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = processor
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Processor(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """CPU information
    """

    plugin_name = 'processor'
    files = ('/proc/cpuinfo',)
    packages = ('cpufreq-utils')

    def setup(self):
        self.add_copy_specs([
            "/proc/cpuinfo",
            "/sys/class/cpuid",
            "/sys/devices/system/cpu"
        ])
        
        self.add_cmd_outputs([
            "lscpu",
            "cpupower info",
            "cpupower idle-info",
            "cpupower frequency-info"
        ])

        if '86' in self.policy().get_arch():
            self.add_cmd_output("x86info -a")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = psacct
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Psacct(Plugin):
    """Process accounting related information
    """

    option_list = [("all", "collect all process accounting files",
                        "slow", False)]

    packages = [ "psacct" ]


class RedHatPsacct(Psacct, RedHatPlugin):
    """Process accounting related information for RedHat based distributions
    """
    plugin_name = "psacct"

    packages = [ "psacct" ]

    def setup(self):
        super(RedHatPsacct, self).setup()
        self.add_copy_spec("/var/account/pacct")
        if self.get_option("all"):
            self.add_copy_spec("/var/account/pacct*.gz")

class DebianPsacct(Psacct, DebianPlugin, UbuntuPlugin):
    """Process accounting related information for Debian based distributions
    """

    plugin_name = "acct"
    packages = [ "acct" ]

    def setup(self):
        super(DebianPsacct, self).setup()
        self.add_copy_specs(["/var/log/account/pacct", "/etc/default/acct"])
        if self.get_option("all"):
            self.add_copy_spec("/var/log/account/pacct*.gz")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = pxe
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Pxe(Plugin):
    """PXE related information
    """

    option_list = [("tftpboot", 'gathers content from the tftpboot path',
                        'slow', False)]
    plugin_name = "pxe"


class RedHatPxe(Pxe, RedHatPlugin):
    """PXE related information for RedHat based distributions
    """

    files = ('/usr/sbin/pxeos',)
    packages = ('system-config-netboot-cmd',)

    def setup(self):
        super(RedHatPxe, self).setup()
        self.add_cmd_output("/usr/sbin/pxeos -l")
        self.add_copy_spec("/etc/dhcpd.conf")
        if self.get_option("tftpboot"):
            self.add_copy_spec("/tftpboot")


class DebianPxe(Pxe, DebianPlugin, UbuntuPlugin):
    """PXE related information for Ubuntu based distributions
    """

    packages = ('tftpd-hpa',)

    def setup(self):
        super(DebianPxe, self).setup()
        self.add_copy_specs([
            "/etc/dhcp/dhcpd.conf",
            "/etc/default/tftpd-hpa"
        ])
        if self.get_option("tftpboot"):
            self.add_copy_spec("/var/lib/tftpboot")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = qpid
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Qpid(Plugin, RedHatPlugin):
    """Messaging related information
    """

    plugin_name = 'qpid'

    packages = ('qpidd', 'qpid-cpp-server', 'qpid-tools')

    def setup(self):
        """ performs data collection for mrg """
        self.add_cmd_outputs([
            "qpid-stat -e",
            "qpid-stat -b",
            "qpid-config",
            "qpid-config -b exchanges",
            "qpid-config -b queues",
            "qpid-stat -c",
            "qpid-route link list",
            "qpid-route route list",
            "ls -lanR /var/lib/qpidd"
        ])

        self.add_copy_specs([
            "/etc/qpidd.conf",
            "/var/lib/qpid/syslog",
            "/etc/ais/openais.conf",
            "/var/log/cumin.log",
            "/var/log/mint.log",
            "/etc/sasl2/qpidd.conf",
            "/etc/qpid/qpidc.conf",
            "/etc/sesame/sesame.conf",
            "/etc/cumin/cumin.conf",
            "/etc/corosync/corosync.conf",
            "/var/lib/sesame",
            "/var/log/qpidd.log",
            "/var/log/sesame",
            "/var/log/cumin",
            "/var/log/cluster"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = quagga
## Copyright (C) 2007 Ranjith Rajaram <rrajaram@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Quagga(Plugin, RedHatPlugin):
    """quagga related information
    """

    plugin_name = 'quagga'

    files = ('/etc/quagga/zebra.conf',)
    packages = ('quagga',)

    def setup(self):
        self.add_copy_spec("/etc/quagga/")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = rabbitmq
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class RabbitMQ(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """rabbitmq related information
    """
    plugin_name = 'rabbitmq'
    files = ('/etc/rabbitmq/rabbitmq.conf',)
    packages = ('rabbitmq-server',)

    option_list = [("logsize", "maximum size (MiB) of logs to collect",
                    "", 15)]

    def setup(self):
        self.add_cmd_output("rabbitmqctl report")
        self.add_copy_spec("/etc/rabbitmq/*")
        self.add_copy_spec_limit("/var/log/rabbitmq/*",
                                 sizelimit=self.get_option('logsize'))
# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = radius
## Copyright (C) 2007 Navid Sheikhol-Eslami <navid@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Radius(Plugin):
    """radius related information
    """

    plugin_name = "radius"
    packages = ('freeradius',)

class RedHatRadius(Radius, RedHatPlugin):
    """radius related information on Red Hat distributions
    """

    files = ('/etc/raddb',)

    def setup(self):
        super(RedHatRadius, self).setup()
        self.add_copy_specs([
            "/etc/raddb",
            "/etc/pam.d/radiusd",
            "/var/log/radius"
        ])

    def postproc(self):
        self.do_file_sub("/etc/raddb/sql.conf", r"(\s*password\s*=\s*)\S+", r"\1***")

class DebianRadius(Radius, DebianPlugin, UbuntuPlugin):
    """radius related information on Debian distributions
    """

    files = ('/etc/freeradius',)

    def setup(self):
        super(DebianRadius, self).setup()
        self.add_copy_specs([
            "/etc/freeradius",
            "/etc/pam.d/radiusd",
            "/etc/default/freeradius",
            "/var/log/freeradius"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = rhui
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class Rhui(Plugin, RedHatPlugin):
    """Red Hat Update Infrastructure for Cloud Providers data
    """

    plugin_name = 'rhui'

    rhui_debug_path = "/usr/share/rh-rhua/rhui-debug.py"

    packages = [ "rh-rhui-tools" ]
    files = [ rhui_debug_path ]

    def setup(self):
        if self.is_installed("pulp-cds"):
            cds = "--cds"
        else:
            cds = ""

        rhui_debug_dst_path = self.get_cmd_output_path()
        self.add_cmd_output("python %s %s --dir %s"
                % (self.rhui_debug_path, cds, rhui_debug_dst_path),
                suggest_filename="rhui-debug")
        return

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = rpm
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Rpm(Plugin, RedHatPlugin):
    """RPM information
    """

    plugin_name = 'rpm'

    option_list = [("rpmq", "queries for package information via rpm -q", "fast", True),
                  ("rpmva", "runs a verify on all packages", "slow", False)]

    verify_list = [
        'kernel$', 'glibc', 'initscripts',
        'pam_.*',
        'java.*', 'perl.*',
        'rpm', 'yum',
        'spacewalk.*',
    ]

    def setup(self):
        self.add_copy_spec("/var/log/rpmpkgs")

        if self.get_option("rpmq"):
            query_fmt = '"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}'
            query_fmt = query_fmt + '~~%{INSTALLTIME:date}\t%{INSTALLTIME}\t%{VENDOR}\n"'
            rpmq_cmd = "rpm --nosignature --nodigest -qa --qf=%s" % query_fmt
            filter_cmd = 'awk -F "~~" "{printf \\"%-59s %s\\n\\",\$1,\$2}"|sort'
            shell_cmd = "sh -c '%s'" % (rpmq_cmd + "|" + filter_cmd)
            self.add_cmd_output(shell_cmd, root_symlink = "installed-rpms")

        if self.get_option("rpmva"):
            self.add_cmd_output("rpm -Va", root_symlink = "rpm-Va", timeout = 3600)
        else:
            pkgs_by_regex = self.policy().package_manager.all_pkgs_by_name_regex
            verify_list = map(pkgs_by_regex, self.verify_list)
            for pkg_list in verify_list:
                for pkg in pkg_list:
                    if 'debuginfo' in pkg \
                    or pkg.endswith('-debuginfo-common'):
                        continue
                    self.add_cmd_output("rpm -V %s" % pkg)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = s390
## Copyright (C) 2007 Red Hat, Inc., Justin Payne <jpayne@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class S390(Plugin, RedHatPlugin):
    """s390 related information
    """

    plugin_name = 's390'

    ### Check for s390 arch goes here

    def check_enabled(self):
        return (self.policy().get_arch() == "s390")

    ### Gather s390 specific information

    def setup(self):
        self.add_copy_specs([
            "/proc/cio_ignore",
            "/proc/crypto",
            "/proc/dasd/devices",
            "/proc/dasd/statistics",
            "/proc/misc",
            "/proc/qeth",
            "/proc/qeth_perf",
            "/proc/qeth_ipa_takeover",
            "/proc/sys/appldata/*",
            "/proc/sys/kernel/hz_timer",
            "/proc/sysinfo",
            "/sys/bus/ccwgroup/drivers/qeth/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/0x*/*",
            "/etc/zipl.conf",
            "/etc/zfcp.conf",
            "/etc/sysconfig/dumpconf",
            "/etc/src_vipa.conf",
            "/etc/ccwgroup.conf",
            "/etc/chandev.conf"])
        self.add_cmd_outputs([
            "lscss",
            "lsdasd",
            "lstape",
            "find /sys -type f",
            "find /proc/s390dbf -type f",
            "qethconf list_all",
            "lsqeth",
            "lszfcp"
        ])
        ret, dasd_dev, rtime = self.call_ext_prog("ls /dev/dasd?")
        for x in dasd_dev.split('\n'):
            self.add_cmd_outputs([
                "dasdview -x -i -j -l -f %s" % (x,),
                "fdasd -p %s" % (x,)
            ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = samba
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Samba(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Samba related information
    """
    packages = ('samba-common',)
    plugin_name = "samba"

    def setup(self):
        self.add_copy_specs([
            "/etc/samba",
            "/var/log/samba/*",])
        self.add_cmd_outputs([
            "wbinfo --domain='.' -g",
            "wbinfo --domain='.' -u",
            "testparm -s -v"
        ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sanlock
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class SANLock(Plugin):
    """sanlock-related information
    """
    plugin_name = "sanlock"
    packages = [ "sanlock" ]

    def setup(self):
        self.add_copy_spec("/var/log/sanlock.log*")
        self.add_cmd_outputs([
            "sanlock client status -D",
            "sanlock client host_status -D",
            "sanlock client log_dump"
        ])
        return

class RedHatSANLock(SANLock, RedHatPlugin):

    files = [ "/etc/sysconfig/sanlock" ]

    def setup(self):
        super(RedHatSANLock, self).setup()
        self.add_copy_spec("/etc/sysconfig/sanlock")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sar
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Sar(Plugin,):
    """ Collect system activity reporter data
    """

    plugin_name = 'sar'

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [("all_sar", "gather all system activity records", "", False)]

    # size-limit SAR data collected by default (MB)
    sa_size = 20

    def setup(self):
        if self.get_option("all_sar"):
            self.sa_size = 0

        # Copy all sa??, sar??, sa??.* and sar??.* files, which will net
        # compressed and uncompressed versions, typically.
        for suffix in ('', '.*'):
            self.add_copy_spec_limit(
                os.path.join(self.sa_path, "sa[0-3][0-9]" + suffix),
                sizelimit = self.sa_size, tailit=False)
            self.add_copy_spec_limit(
                os.path.join(self.sa_path, "sar[0-3][0-9]" + suffix),
                sizelimit = self.sa_size, tailit=False)
        try:
            dirList = os.listdir(self.sa_path)
        except:
            self.log_warn("sar: could not list %s" % self.sa_path)
            return
        # find all the sa files that don't have an existing sar file
        for fname in dirList:
            if fname.startswith('sar'):
                continue
            if not fname.startswith('sa'):
                continue
            if len(fname) != 4:
                # We either have an "sa" or "sa?" file, or more likely, a
                # compressed data file like, "sa??.xz".
                #
                # FIXME: We don't have a detector for the kind of compression
                # use for this file right now, so skip these kinds of files.
                continue
            sa_data_path = os.path.join(self.sa_path, fname)
            sar_filename = 'sar' + fname[2:]
            if sar_filename not in dirList:
                sar_cmd = 'sh -c "LANG=C sar -A -f %s"' % sa_data_path
                self.add_cmd_output(sar_cmd, sar_filename)
            sadf_cmd = "sadf -x %s" % sa_data_path
            self.add_cmd_output(sadf_cmd, "%s.xml" % fname)


class RedHatSar(Sar, RedHatPlugin):
    """ Collect system activity reporter data
    """

    sa_path = '/var/log/sa'


class DebianSar(Sar, DebianPlugin, UbuntuPlugin):
    """ Collect system activity reporter data
    """

    sa_path = '/var/log/sysstat'

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = satellite
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class Satellite(Plugin, RedHatPlugin):
    """RHN Satellite and Spacewalk related information
    """

    plugin_name = 'satellite'
    satellite = False
    proxy = False

    option_list = [("log", 'gathers all apache logs', 'slow', False)]

    def default_enabled(self):
        return False

    def rhn_package_check(self):
        self.satellite = self.is_installed("rhns-satellite-tools") \
                      or self.is_installed("spacewalk-java") \
                      or self.is_installed("rhn-base")
        self.proxy = self.is_installed("rhns-proxy-tools") \
                      or self.is_installed("spacewalk-proxy-management") \
                      or self.is_installed("rhn-proxy-management")
        return self.satellite or self.proxy

    def check_enabled(self):
        # enable if any related package is installed
        return self.rhn_package_check()

    def setup(self):
        self.rhn_package_check()
        self.add_copy_specs([
            "/etc/httpd/conf*",
            "/etc/rhn",
            "/var/log/rhn*"
        ])

        if self.get_option("log"):
            self.add_copy_spec("/var/log/httpd")

        # all these used to go in $DIR/mon-logs/
        self.add_copy_specs([
            "/opt/notification/var/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*"
        ])

        # monitoring scout logs
        self.add_copy_specs([
            "/home/nocpulse/var/*.log*",
            "/home/nocpulse/var/commands/*.log*",
            "/var/tmp/ack_handler.log*",
            "/var/tmp/enqueue.log*",
            "/var/log/nocpulse/*.log*",
            "/var/log/notification/*.log*",
            "/var/log/nocpulse/TSDBLocalQueue/TSDBLocalQueue.log"
        ])

        self.add_copy_spec("/root/ssl-build")
        self.add_cmd_output("rhn-schema-version",
                        root_symlink = "database-schema-version")
        self.add_cmd_output("rhn-charsets",
                        root_symlink = "database-character-sets")

        if self.satellite:
            self.add_copy_specs([
                "/etc/tnsnames.ora",
                "/etc/jabberd",
                "/etc/tomcat6/",
                "/var/log/tomcat6/"
            ])
            self.add_cmd_output("spacewalk-debug --dir %s"
                    % self.get_cmd_output_path(name="spacewalk-debug"))

        if self.proxy:
            self.add_copy_specs(["/etc/squid", "/var/log/squid"])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = scsi
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Scsi(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """hardware related information
    """

    plugin_name = 'scsi'

    def setup(self):
        self.add_copy_specs([
            "/proc/scsi",
            "/etc/stinit.def",
            "/sys/bus/scsi",
            "/sys/class/scsi_host",
            "/sys/class/scsi_disk",
            "/sys/class/scsi_device",
            "/sys/class/scsi_generic"
        ])
        
        self.add_cmd_outputs([
            "lsscsi",
            "sg_map"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = selinux
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
from os.path import join

class SELinux(Plugin, RedHatPlugin):
    """selinux related information
    """

    plugin_name = 'selinux'

    option_list = [("fixfiles", 'Print incorrect file context labels', 'slow', False),
                   ("list", 'List objects and their context', 'slow', False)]
    packages = ('libselinux',)

    def setup(self):
        # sestatus is always collected in check_enabled()
        self.add_copy_spec("/etc/selinux")
        self.add_cmd_outputs([
            "sestatus -b",
            "semodule -l",
            "selinuxdefcon root",
            "selinuxconlist root",
            "selinuxexeccon /bin/passwd",
            "ausearch -m avc,user_avc -ts today",
            "semanage -o -"
        ])
        if self.get_option('fixfiles'):
            self.add_cmd_output("fixfiles -v check")
        if self.get_option('list'):
            self.add_cmd_outputs([
                "semanage fcontext -l",
                "semanage user -l",
                "semanage login -l",
                "semanage port -l"
            ])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sendmail
## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Sendmail(Plugin):
    """sendmail information
    """

    plugin_name = "sendmail" 

    packages = ('sendmail',)


class RedHatSendmail(Sendmail, RedHatPlugin):
    """sendmail information for RedHat based distributions
    """

    files = ('/etc/rc.d/init.d/sendmail',)
    packages = ('sendmail',)

    def setup(self):
        super(RedHatSendmail, self).setup()
        self.add_copy_specs([
            "/etc/mail/*",
            "/var/log/maillog"
        ])

class DebianSendmail(Sendmail, DebianPlugin, UbuntuPlugin):
    """sendmail information for Debian based distributions
    """

    files = ('/etc/init.d/sendmail',)
    packages = ('sendmail',)

    def setup(self):
        super(DebianSendmail, self).setup()
        self.add_copy_specs([
            "/etc/mail/*",
            "/var/log/mail.*"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = smartcard
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Smartcard(Plugin, RedHatPlugin):
    """Smart Card related information
    """

    plugin_name = 'smartcard'

    files = ('/etc/pam_pkcs11/pam_pkcs11.conf',)
    packages = ('pam_pkcs11',)

    def setup(self):
        self.add_copy_specs([
            "/etc/reader.conf",
            "/etc/reader.conf.d/",
            "/etc/pam_pkcs11/"])
        self.add_cmd_outputs([
            "pkcs11_inspect debug",
            "pklogin_finder debug",
            "ls -nl /usr/lib*/pam_pkcs11/"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = snmp
## Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from os.path import exists

class Snmp(Plugin):
    """snmp related information
    """
    plugin_name = "snmp"

    files = ('/etc/snmp/snmpd.conf',)

    def setup(self):
        self.add_copy_spec("/etc/snmp")

class RedHatSnmp(Snmp, RedHatPlugin):
    """snmp related information for RedHat based distributions
    """

    packages = ('net-snmp',)

    def setup(self):
        super(RedHatSnmp, self).setup()

class DebianSnmp(Snmp, DebianPlugin, UbuntuPlugin):
    """snmp related information for Debian based distributions
    """

    packages = ('snmp',)

    def setup(self):
        super(DebianSnmp, self).setup()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = soundcard
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os

class Soundcard(Plugin):
    """ Sound card information
    """

    plugin_name = "soundcard"

    def default_enabled(self):
        return False

    def setup(self):
        self.add_copy_spec("/proc/asound/*")
        self.add_cmd_outputs([
            "aplay -l",
            "aplay -L",
            "amixer"
        ])

class RedHatSoundcard(Soundcard, RedHatPlugin):
    """ Sound card information for RedHat distros
    """

    def setup(self):
        super(RedHatSoundcard, self).setup()

        self.add_copy_specs([
            "/etc/alsa/*",
            "/etc/asound.*"
        ])

class DebianSoundcard(Soundcard, DebianPlugin, UbuntuPlugin):
    """ Sound card information for Debian/Ubuntu distros
    """

    def setup(self):
        super(DebianSoundcard, self).setup()

        self.add_copy_spec("/etc/pulse/*")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = squid
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Squid(Plugin):
    """squid related information
    """

    plugin_name = 'squid'

    option_list = [("logsize", "maximum size (MiB) of logs to collect",
                    "", 15)]


class RedHatSquid(Squid, RedHatPlugin):
    """squid Red Hat related information
    """

    files = ('/etc/squid/squid.conf',)
    packages = ('squid',)

    def setup(self):
        self.add_copy_spec_limit("/etc/squid/squid.conf",
                                 sizelimit=self.get_option('logsize'))


class DebianSquid(Squid, DebianPlugin, UbuntuPlugin):
    """squid related information for Debian and Ubuntu
    """

    plugin_name = 'squid'
    files = ('/etc/squid3/squid.conf',)
    packages = ('squid3',)

    def setup(self):
        self.add_copy_spec_limit("/etc/squid3/squid.conf",
                                 sizelimit=self.get_option('logsize'))
        self.add_copy_spec_limit("/var/log/squid3/*",
                                 sizelimit=self.get_option('logsize'))
        self.add_copy_specs(['/etc/squid-deb-proxy'])
        self.add_copy_spec_limit("/var/log/squid-deb-proxy/*",
                                 sizelimit=self.get_option('logsize'))
# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ssh
## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Ssh(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ssh-related information
    """

    plugin_name = 'ssh'

    def setup(self):
        self.add_copy_specs([
            "/etc/ssh/ssh_config",
            "/etc/ssh/sshd_config"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sssd
## Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Sssd(Plugin):
    """sssd-related Diagnostic Information
    """

    plugin_name = "sssd"
    packages = ('sssd',)

    def setup(self):
        self.add_copy_specs([
            "/etc/sssd/sssd.conf",
            "/var/log/sssd/*"
        ])

    def postproc(self):
        self.do_file_sub("/etc/sssd/sssd.conf",
                    r"(\s*ldap_default_authtok\s*=\s*)\S+",
                    r"\1********")

class RedHatSssd(Sssd, RedHatPlugin):
    """sssd-related Diagnostic Information on Red Hat based distributions
    """

    def setup(self):
        super(RedHatSssd, self).setup()

class DebianSssd(Sssd, DebianPlugin, UbuntuPlugin):
    """sssd-related Diagnostic Information on Debian based distributions
    """

    def setup(self):
        super(DebianSssd, self).setup()
        self.add_copy_spec("/etc/default/sssd")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = startup
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Startup(Plugin):
    """startup information
    """

    plugin_name = "startup"

    option_list = [("servicestatus", "get a status of all running services", "slow", False)]
    def setup(self):
        if self.get_option('servicestatus'):
            self.add_cmd_output("/sbin/service --status-all")
        self.add_cmd_output("/sbin/runlevel")

class RedHatStartup(Startup, RedHatPlugin):
    """startup information for RedHat based distributions
    """

    def setup(self):
        super(RedHatStartup, self).setup()
        self.add_copy_spec("/etc/rc.d")
        self.add_cmd_output("/sbin/chkconfig --list", root_symlink = "chkconfig")

class DebianStartup(Startup, DebianPlugin, UbuntuPlugin):
    """startup information
    """

    def setup(self):
        super(DebianStartup, self).setup()
        self.add_copy_spec("/etc/rc*.d")

        self.add_cmd_output("/sbin/initctl show-config", root_symlink = "initctl")
        if self.get_option('servicestatus'):
            self.add_cmd_output("/sbin/initctl list")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sunrpc
## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class SunRPC(Plugin):
    """Sun RPC related information
    """

    plugin_name = "sunrpc"
    service = None

    def check_enabled(self):
        if self.policy().default_runlevel() in \
          self.policy().runlevel_by_service(self.service):
            return True
        return False

    def setup(self):
        self.add_cmd_output("rpcinfo -p localhost")
        return

class RedHatSunRPC(SunRPC, RedHatPlugin):
    """Sun RPC related information for Red Hat systems
    """

    service = 'rpcbind'

# FIXME: depends on addition of runlevel_by_service (or similar)
# in Debian/Ubuntu policy classes
#class DebianSunRPC(SunRPC, DebianPlugin, UbuntuPlugin):
#    """Sun RPC related information for Red Hat systems
#    """
#
#    service = 'rpcbind-boot'
#
#    def setup(self):
#        self.add_cmd_output("rpcinfo -p localhost")
#        return



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = system
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class System(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """core system related information
    """

    plugin_name = "system"

    def setup(self):
        self.add_copy_spec("/proc/sys")
        self.add_forbidden_path(
                "/proc/sys/net/ipv6/neigh/*/retrans_time")
        self.add_forbidden_path(
                "/proc/sys/net/ipv6/neigh/*/base_reachable_time")


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = systemd
## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Systemd(Plugin, RedHatPlugin):
    """ Information on systemd and related subsystems
    """

    plugin_name = "systemd"

    packages = ('systemd',)
    files = ('/usr/lib/systemd/systemd',)

    def setup(self):
        self.add_cmd_outputs([
            "systemctl show --all",
            "systemctl list-units",
            "systemctl list-units --failed",
            "systemctl list-units --all",
            "systemctl list-unit-files",
            "systemctl show-environment",
            "systemd-delta",
            "journalctl --verify",
            "journalctl --all --this-boot --no-pager",
            "journalctl --all --this-boot --no-pager -o verbose",
            "ls -l /lib/systemd",
            "ls -l /lib/systemd/system-shutdown",
            "ls -l /lib/systemd/system-generators",
            "ls -l /lib/systemd/user-generators"
        ])

        self.add_copy_specs([
            "/etc/systemd",
            "/lib/systemd/system",
            "/lib/systemd/user",
            "/etc/vconsole.conf",
            "/etc/yum/protected.d/systemd.conf"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = systemtap
## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class SystemTap(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """SystemTap information
    """

    plugin_name = 'systemtap'

    files = ('stap',)
    packages = ('systemtap', 'systemtap-runtime')

    def setup(self):
        self.add_cmd_outputs([
            "stap -V 2",
            "uname -r"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sysvipc
## Copyright (C) 2007-2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class SysVIPC(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """SysV IPC related information
    """

    plugin_name = "sysvipc"

    def setup(self):
        self.add_copy_specs([
            "/proc/sysvipc/msg",
            "/proc/sysvipc/sem",
            "/proc/sysvipc/shm"
        ])
        self.add_cmd_output("ipcs")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = tftpserver
## Copyright (C) 2007 Shijoe George <spanjikk@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class TftpServer(Plugin, RedHatPlugin):
    """tftpserver related information
    """

    plugin_name = 'tftpserver'

    files = ('/etc/xinetd.d/tftp',)
    packages = ('tftp-server',)

    def setup(self):
        self.add_cmd_output("ls -lanR /tftpboot")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = tomcat
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Tomcat(Plugin, RedHatPlugin):
    """Tomcat related information
    """

    plugin_name = 'tomcat'

    packages = ('tomcat5',)

    def setup(self):
        self.add_copy_specs([
            "/etc/tomcat5",
            "/var/log/tomcat5"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = tuned
## Copyright (C) 2014 Red Hat, Inc., Peter Portante <peter.portante@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Tuned(Plugin, RedHatPlugin):
    """Tuned related information
    """
    packages = ('tuned',)
    plugin_name = 'tuned'

    def setup(self):
        self.add_cmd_outputs([
            "tuned-adm list",
            "tuned-adm active",
            "tuned-adm recommend"
        ])
        self.add_copy_specs([
            "/etc/tuned",
            "/usr/lib/tuned",
            "/var/log/tuned/tuned.log"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = udev
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Udev(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Udev related information
    """

    plugin_name = 'udev'

    def setup(self):
        self.add_copy_specs([
            "/etc/udev/udev.conf",
            "/lib/udev/rules.d",
            "/etc/udev/rules.d/*"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = upstart
## Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Upstart(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ Information on Upstart, the event-based init system.
    """

    plugin_name = 'upstart'
    packages = ('upstart',)

    option_list = [("logsize", "maximum size (MiB) of logs to collect",
                   "", 15)]

    def setup(self):
        self.add_cmd_outputs([
            'initctl --system list',
            'initctl --system version',
            'init --version',
            "ls -l /etc/init/"
        ])

        # Job Configuration Files
        self.add_copy_specs([
            '/etc/init.conf',
            '/etc/init/'
        ])

        # State file
        self.add_copy_spec('/var/log/upstart/upstart.state')

        # Log files
        self.add_copy_spec_limit('/var/log/upstart/*',
                                 sizelimit=self.get_option('logsize'))
        # Session Jobs (running Upstart as a Session Init)
        self.add_copy_spec('/usr/share/upstart/')


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = usb
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
from glob import glob
import os

class Usb(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """USB device related information
    """

    plugin_name = "usb"

    def setup(self):
        self.add_copy_spec("/sys/bus/usb")

        self.add_cmd_outputs([
            "lsusb",
            "lsusb -v",
            "lsusb -t"
        ])



# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = veritas
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os

class Veritas(Plugin, RedHatPlugin):
    """Veritas related information
    """

    plugin_name = 'veritas'

    # Information about VRTSexplorer obtained from
    # http://seer.entsupport.symantec.com/docs/243150.htm
    option_list = [("script", "Define VRTSexplorer script path", "", 
                                    "/opt/VRTSspt/VRTSexplorer")]

    def check_enabled(self):
        return os.path.isfile(self.get_option("script"))

    def setup(self):
        """ interface with vrtsexplorer to capture veritas related data """
        stat, out, runtime = self.call_ext_prog(self.get_option("script"))
        try:
            for line in out.readlines():
                line = line.strip()
                tarfile = self.do_regex_find_all(r"ftp (.*tar.gz)", line)
            if len(tarfile) == 1:
                self.add_copy_spec(tarfile[0])
        except AttributeError as e:
            self.add_alert(e)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = vmware
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class VMWare(Plugin, RedHatPlugin):
    """VMWare related information
    """

    plugin_name = 'vmware'

    files = ('vmware','/usr/init.d/vmware-tools')

    def setup(self):
        self.add_cmd_output("vmware -v")
        self.add_copy_specs([
            "/etc/vmware/locations",
            "/etc/vmware/config",
            "/proc/vmmemctl"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = vsftpd
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Vsftpd(Plugin, RedHatPlugin):
    """FTP server related information
    """

    plugin_name = 'vsftpd'

    files = ('/etc/vsftpd',)
    packages = ('vsftpd',)

    def setup(self):
        self.add_copy_specs([
            "/etc/ftp*",
            "/etc/vsftpd"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = x11
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class X11(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """X related information
    """

    plugin_name = 'x11'

    files = ('/etc/X11',)

    def setup(self):
        self.add_copy_specs([
            "/etc/X11",
            "/var/log/Xorg.*.log",
            "/var/log/XFree86.*.log",
        ])
        self.add_forbidden_path("/etc/X11/X")
        self.add_forbidden_path("/etc/X11/fontpath.d")

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = xen
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin
import os
import re
from stat import *

class Xen(Plugin, RedHatPlugin):
    """Xen related information
    """

    plugin_name = 'xen'

    def determine_xen_host(self):
        if os.access("/proc/acpi/dsdt", os.R_OK):
            (status, output, rtime) = self.call_ext_prog("grep -qi xen /proc/acpi/dsdt")
            if status == 0:
                return "hvm"

        if os.access("/proc/xen/capabilities", os.R_OK):
            (status, output, rtime) = self.call_ext_prog("grep -q control_d /proc/xen/capabilities")
            if status == 0:
                return "dom0"
            else:
                return "domU"
        return "baremetal"

    def check_enabled(self):
        return (self.determine_xen_host() == "baremetal")

    def is_running_xenstored(self):
        xs_pid = os.popen("pidof xenstored").read()
        xs_pidnum = re.split('\n$',xs_pid)[0]
        return xs_pidnum.isdigit()

    def dom_collect_proc(self):
        self.add_copy_specs([
            "/proc/xen/balloon",
            "/proc/xen/capabilities",
            "/proc/xen/xsd_kva",
            "/proc/xen/xsd_port"])
        # determine if CPU has PAE support
        self.add_cmd_output("grep pae /proc/cpuinfo")
        # determine if CPU has Intel-VT or AMD-V support
        self.add_cmd_output("egrep -e 'vmx|svm' /proc/cpuinfo")

    def setup(self):
        host_type = self.determine_xen_host()
        if host_type == "domU":
            # we should collect /proc/xen and /sys/hypervisor
            self.dom_collect_proc()
            # determine if hardware virtualization support is enabled
            # in BIOS: /sys/hypervisor/properties/capabilities
            self.add_copy_spec("/sys/hypervisor")
        elif host_type == "hvm":
            # what do we collect here???
            pass
        elif host_type == "dom0":
            # default of dom0, collect lots of system information
            self.add_copy_specs([
                "/var/log/xen",
                "/etc/xen",
                "/sys/hypervisor/version",
                "/sys/hypervisor/compilation",
                "/sys/hypervisor/properties",
                "/sys/hypervisor/type"])
            self.add_cmd_outputs([
                "xm dmesg",
                "xm info",
                "xm list",
                "xm list --long",
                "brctl show"
            ])
            self.dom_collect_proc()
            if self.is_running_xenstored():
                self.add_copy_spec("/sys/hypervisor/uuid")
                self.add_cmd_output("xenstore-ls")
            else:
                # we need tdb instead of xenstore-ls if cannot get it.
                self.add_copy_spec("/var/lib/xenstored/tdb")

            # FIXME: we *might* want to collect things in /sys/bus/xen*,
            # /sys/class/xen*, /sys/devices/xen*, /sys/modules/blk*,
            # /sys/modules/net*, but I've never heard of them actually being
            # useful, so I'll leave it out for now
        else:
            # for bare-metal, we don't have to do anything special
            return #USEFUL

        self.add_custom_text("Xen hostType: "+host_type)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = xfs
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re
from six.moves import zip

class Xfs(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """information on the XFS filesystem
    """

    plugin_name = 'xfs'

    option_list = [("logprint", 'gathers the log information', 'slow', False)]

    def setup(self):
        mounts = '/proc/mounts'
        ext_fs_regex = r"^(/dev/.+).+xfs\s+"
        for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
            for e in dev:
                parts = e.split(' ')
                self.add_cmd_output("xfs_info %s" % (parts[1]))

        if self.get_option('logprint'):
            for dev in zip(self.do_regex_find_all(ext_fs_regex, mounts)):
                for e in dev:
                    parts = e.split(' ')
                    self.add_cmd_output("xfs_logprint -c %s" % (parts[0]))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = xinetd
## Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class Xinetd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """xinetd information
    """

    plugin_name = 'xinetd'

    files = ('/etc/xinetd.conf',)
    packages = ('xinetd',)

    def setup(self):
        self.add_copy_specs([
            "/etc/xinetd.conf",
            "/etc/xinetd.d"
        ])

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = yum
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Yum(Plugin, RedHatPlugin):
    """yum information
    """

    plugin_name = 'yum'

    files = ('/etc/yum.conf',)
    packages = ('yum',)
    option_list = [("yumlist", "list repositories and packages", "slow", False),
                  ("yumdebug", "gather yum debugging data", "slow", False)]

    def setup(self):
        # Pull all yum related information
        self.add_copy_specs([
            "/etc/yum",
            "/etc/yum.repos.d",
            "/etc/yum.conf",
            "/var/log/yum.log"])

        # Get a list of channels the machine is subscribed to.
        self.add_cmd_output("yum -C repolist")

        # candlepin info
        self.add_forbidden_path("/etc/pki/entitlement/key.pem")
        self.add_forbidden_path("/etc/pki/entitlement/*-key.pem")
        self.add_copy_specs([
            "/etc/pki/product/*.pem",
            "/etc/pki/consumer/cert.pem",
            "/etc/pki/entitlement/*.pem",
            "/etc/rhsm/",
            "/var/log/rhsm/rhsm.log",
            "/var/log/rhsm/rhsmcertd.log"])
        self.add_cmd_outputs([
            "subscription-manager list --installed",
            "subscription-manager list --consumed"
        ])
        self.add_cmd_output("rhsm-debug system --sos --no-archive --destination %s"
                % self.get_cmd_output_path())

        if self.get_option("yumlist"):
            # List various information about available packages
            self.add_cmd_output("yum list")

        if self.get_option("yumdebug") and self.is_installed('yum-utils'):
            # RHEL6+ alternative for this whole function:
            # self.add_cmd_output("yum-debug-dump '%s'" % os.path.join(self.commons['dstroot'],"yum-debug-dump"))
            ret, output, rtime = self.call_ext_prog("yum-debug-dump")
            try:
                self.add_cmd_output("zcat %s" % (output.split()[-1],))
            except IndexError:
                pass

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = debian
from sos.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy

import os

class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_url = "http://www.debian.org/"
    report_name = ""
    ticket_number = ""
    package_manager = PackageManager("dpkg-query -W -f='${Package}|${Version}\\n' \*")
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
            + ":/usr/local/sbin:/usr/local/bin"

    def __init__(self):
        super(DebianPolicy, self).__init__()
        self.report_name = ""
        self.ticket_number = ""
        self.package_manager = PackageManager("dpkg-query -W -f='${Package}|${Version}\\n' \*")
        self.valid_subclasses = [DebianPlugin]

    @classmethod
    def check(self):
        """This method checks to see if we are running on Debian.
           It returns True or False."""
        return os.path.isfile('/etc/debian_version')

    def debianVersion(self):
        try:
            fp = open("/etc/debian_version").read()
            if "wheezy/sid" in fp:
                return 6
            fp.close()
        except:
            pass
        return False

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = osx
from sos.policies import PackageManager, Policy
from sos.utilities import shell_out

class OSXPolicy(Policy):

    distro = "Mac OS X"

    @classmethod
    def check(class_):
        try:
            return "Mac OS X" in shell_out("sw_vers")
        except Exception as e:
            return False

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = redhat
## Copyright (C) Steve Conklin <sconklin@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This enables the use of with syntax in python 2.5 (e.g. jython)
import os
import sys

from sos.plugins import RedHatPlugin
from sos.policies import LinuxPolicy, PackageManager
from sos import _sos as _

sys.path.insert(0, "/usr/share/rhn/")
try:
    from up2date_client import up2dateAuth
    from up2date_client import config
    from rhn import rpclib
except:
    # might fail if non-RHEL
    pass

class RedHatPolicy(LinuxPolicy):
    distro = "Red Hat"
    vendor = "Red Hat"
    vendor_url = "http://www.redhat.com/"
    _tmp_dir = "/var/tmp"

    def __init__(self):
        super(RedHatPolicy, self).__init__()
        self.report_name = ""
        self.ticket_number = ""
        self.package_manager = PackageManager(
                        'rpm -qa --queryformat "%{NAME}|%{VERSION}\\n"')
        self.valid_subclasses = [RedHatPlugin]

        # handle PATH for UsrMove
        if self.package_manager.all_pkgs()['filesystem']['version'][0] == '3':
            self.PATH = "/usr/sbin:/usr/bin:/root/bin"
        else:
            self.PATH = "/sbin:/bin:/usr/sbin:/usr/bin:/root/bin"
        self.PATH += os.pathsep + "/usr/local/bin"
        self.PATH += os.pathsep + "/usr/local/sbin"
        self.set_exec_path()

    @classmethod
    def check(self):
        """This method checks to see if we are running on Red Hat. It must be
        overriden by concrete subclasses to return True when running on a
        Fedora, RHEL or other Red Hat distribution or False otherwise."""
        return False

    def runlevel_by_service(self, name):
        from subprocess import Popen, PIPE
        ret = []
        p = Popen("LC_ALL=C /sbin/chkconfig --list %s" % name,
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  bufsize=-1,
                  close_fds=True)
        out, err = p.communicate()
        if err:
            return ret
        for tabs in out.split()[1:]:
            try:
                (runlevel, onoff) = tabs.split(":", 1)
            except:
                pass
            else:
                if onoff == "on":
                    ret.append(int(runlevel))
        return ret

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return self._tmp_dir
        return opt_tmp_dir

    def get_local_name(self):
        return self.host_name()

class RHELPolicy(RedHatPolicy):
    distro = "Red Hat Enterprise Linux"
    vendor = "Red Hat"
    vendor_url = "https://access.redhat.com/support/"
    msg = _("""\
This command will collect diagnostic and configuration \
information from this %(distro)s system and installed \
applications.

An archive containing the collected information will be \
generated in %(tmpdir)s and may be provided to a %(vendor)s \
support representative.

Any information provided to %(vendor)s will be treated in \
accordance with the published support policies at:\n
  %(vendor_url)s

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No changes will be made to system configuration.
%(vendor_text)s
""")

    def __init__(self):
        super(RHELPolicy, self).__init__()

    @classmethod
    def check(self):
        """This method checks to see if we are running on RHEL. It returns True
        or False."""
        return (os.path.isfile('/etc/redhat-release')
                and not os.path.isfile('/etc/fedora-release'))

    def rhel_version(self):
        try:
            pkg = self.pkg_by_name("redhat-release") or \
            self.all_pkgs_by_name_regex("redhat-release-.*")[-1]
            pkgname = pkg["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname[0] in [ "5Server", "5Client" ]:
                return 5
            elif pkgname[0] == "6":
                return 6
            elif pkgname[0] == "7":
                return 7
        except:
            pass
        return False

    def rhn_username(self):
        try:
            cfg = config.initUp2dateConfig()

            return rpclib.xmlrpclib.loads(up2dateAuth.getSystemId())[0][0]['username']
        except:
            # ignore any exception and return an empty username
            return ""

    def get_local_name(self):
        return self.rhn_username() or self.host_name()

class FedoraPolicy(RedHatPolicy):

    distro = "Fedora"
    vendor = "the Fedora Project"
    vendor_url = "https://fedoraproject.org/"

    def __init__(self):
        super(FedoraPolicy, self).__init__()

    @classmethod
    def check(self):
        """This method checks to see if we are running on Fedora. It returns True
        or False."""
        return os.path.isfile('/etc/fedora-release')

    def fedora_version(self):
        pkg = self.pkg_by_name("fedora-release") or \
        self.all_pkgs_by_name_regex("fedora-release-.*")[-1]
        return int(pkg["version"])


# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = ubuntu
from __future__ import with_statement

import os

from sos.plugins import UbuntuPlugin, DebianPlugin, IndependentPlugin
from sos.policies.debian import DebianPolicy

class UbuntuPolicy(DebianPolicy):
    distro = "Ubuntu"
    vendor = "Ubuntu"
    vendor_url = "http://www.ubuntu.com/"

    def __init__(self):
        super(UbuntuPolicy, self).__init__()
        self.valid_subclasses = [UbuntuPlugin, DebianPlugin]

    @classmethod
    def check(self):
        """This method checks to see if we are running on Ubuntu.
           It returns True or False."""
        try:
            with open('/etc/lsb-release', 'r') as fp:
                return "Ubuntu" in fp.read()
        except:
            return False

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = reporting
"""This provides a restricted tag language to define the sosreport index/report"""

try:
    import json
except ImportError:
    import simplejson as json

# PYCOMPAT
from six import iteritems

class Node(object):

    def __str__(self):
        return json.dumps(self.data)

    def can_add(self, node):
        return False

class Leaf(Node):
    """Marker class that can be added to a Section node"""
    pass


class Report(Node):
    """The root element of a report. This is a container for sections."""

    def __init__(self):
        self.data = {}

    def can_add(self, node):
        return isinstance(node, Section)

    def add(self, *nodes):
        for node in nodes:
            if self.can_add(node):
                self.data[node.name] = node.data


class Section(Node):
    """A section is a container for leaf elements. Sections may be nested
    inside of Report objects only."""

    def __init__(self, name):
        self.name = name
        self.data = {}

    def can_add(self, node):
        return isinstance(node, Leaf)

    def add(self, *nodes):
        for node in nodes:
            if self.can_add(node):
                self.data.setdefault(node.ADDS_TO, []).append(node.data)


class Command(Leaf):

    ADDS_TO = "commands"

    def __init__(self, name, return_code, href):
        self.data = {"name": name,
                     "return_code": return_code,
                     "href": href}


class CopiedFile(Leaf):

    ADDS_TO = "copied_files"

    def __init__(self, name, href):
        self.data = {"name": name,
                     "href": href}


class CreatedFile(Leaf):

    ADDS_TO = "created_files"

    def __init__(self, name):
        self.data = {"name": name}


class Alert(Leaf):

    ADDS_TO = "alerts"

    def __init__(self, content):
        self.data = content


class Note(Leaf):

    ADDS_TO = "notes"

    def __init__(self, content):
        self.data = content


class PlainTextReport(object):
    """Will generate a plain text report from a top_level Report object"""

    LEAF  = "  * %(name)s"
    ALERT = "  ! %s"
    NOTE  = "  * %s"
    DIVIDER = "=" * 72

    subsections = (
        (Command, LEAF,      "-  commands executed:"),
        (CopiedFile, LEAF,   "-  files copied:"),
        (CreatedFile, LEAF,  "-  files created:"),
        (Alert, ALERT,       "-  alerts:"),
        (Note, NOTE,         "-  notes:"),
    )

    buf = []

    def __init__(self, report_node):
        self.report_node = report_node

    def __str__(self):
        self.buf = buf = []
        for section_name, section_contents in sorted(iteritems(self.report_node.data)):
            buf.append(section_name + "\n" + self.DIVIDER)
            for type_, format_, header in self.subsections:
                self.process_subsection(section_contents, type_.ADDS_TO, header, format_)

        return "\n".join(buf)

    def process_subsection(self, section, key, header, format_):
        if key in section:
            self.buf.append(header)
            for item in section.get(key):
                self.buf.append(format_ % item)

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sosreport
"""
Gather information about a system and report it using plugins
supplied for application-specific information
"""
## sosreport.py
## gather information about a system and report it

## Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# pylint: disable-msg = W0611
# pylint: disable-msg = W0702
# pylint: disable-msg = R0912
# pylint: disable-msg = R0914
# pylint: disable-msg = R0915
# pylint: disable-msg = R0913
# pylint: disable-msg = E0611
# pylint: disable-msg = E1101
# pylint: disable-msg = R0904
# pylint: disable-msg = R0903

import sys
import traceback
import os
import errno
import logging
from optparse import OptionParser, Option
from sos.plugins import import_plugin
from sos.utilities import ImporterHelper
from stat import ST_UID, ST_GID, ST_MODE, ST_CTIME, ST_ATIME, ST_MTIME, S_IMODE
from time import strftime, localtime
from collections import deque
import textwrap
import tempfile

from sos import _sos as _
from sos import __version__
import sos.policies
from sos.archive import TarFileArchive, ZipFileArchive
from sos.reporting import Report, Section, Command, CopiedFile, CreatedFile, Alert, Note, PlainTextReport

# PYCOMPAT
import six
from six.moves import zip, input
if six.PY3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser
from six import print_


class TempFileUtil(object):

    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
        self.files = []

    def new(self):
       fd, fname = tempfile.mkstemp(dir=self.tmp_dir)
       fobj = open(fname, 'w')
       self.files.append((fname, fobj))
       return fobj

    def clean(self):
        for fname, f in self.files:
            try:
                f.flush()
                f.close()
            except Exception as e:
                pass
            try:
                os.unlink(fname)
            except Exception as e:
                pass
        self.files = []


class OptionParserExtended(OptionParser):
    """ Show examples """
    def print_help(self, out=sys.stdout):
        """ Prints help content including examples """
        OptionParser.print_help(self, out)
        print_()
        print_( "Some examples:")
        print_()
        print_( " enable cluster plugin only and collect dlm lockdumps:")
        print_( "   # sosreport -o cluster -k cluster.lockdump")
        print_()
        print_( " disable memory and samba plugins, turn off rpm -Va collection:")
        print_( "   # sosreport -n memory,samba -k rpm.rpmva=off")
        print_()

class SosOption(Option):
    """Allow to specify comma delimited list of plugins"""
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        """ Performs list extension on plugins """
        if action == "extend":
            try:
                lvalue = value.split(",")
            except:
                pass
            else:
                values.ensure_value(dest, deque()).extend(lvalue)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)



class XmlReport(object):
    """ Report build class """
    def __init__(self):
        try:
            import libxml2
        except ImportError:
            self.enabled = False
            return
        else:
            self.enabled = False
            return
        self.doc = libxml2.newDoc("1.0")
        self.root = self.doc.newChild(None, "sos", None)
        self.commands = self.root.newChild(None, "commands", None)
        self.files = self.root.newChild(None, "files", None)

    def add_command(self, cmdline, exitcode, stdout = None, stderr = None,
                    f_stdout=None, f_stderr=None, runtime=None):
        """ Appends command run into report """
        if not self.enabled:
            return

        cmd = self.commands.newChild(None, "cmd", None)

        cmd.setNsProp(None, "cmdline", cmdline)

        cmdchild = cmd.newChild(None, "exitcode", str(exitcode))

        if runtime:
            cmd.newChild(None, "runtime", str(runtime))

        if stdout or f_stdout:
            cmdchild = cmd.newChild(None, "stdout", stdout)
            if f_stdout:
                cmdchild.setNsProp(None, "file", f_stdout)

        if stderr or f_stderr:
            cmdchild = cmd.newChild(None, "stderr", stderr)
            if f_stderr:
                cmdchild.setNsProp(None, "file", f_stderr)

    def add_file(self, fname, stats):
        """ Appends file(s) added to report """
        if not self.enabled:
            return

        cfile = self.files.newChild(None, "file", None)

        cfile.setNsProp(None, "fname", fname)

        cchild = cfile.newChild(None, "uid", str(stats[ST_UID]))
        cchild = cfile.newChild(None, "gid", str(stats[ST_GID]))
        cfile.newChild(None, "mode", str(oct(S_IMODE(stats[ST_MODE]))))
        cchild = cfile.newChild(None, "ctime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_CTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_CTIME]))
        cchild = cfile.newChild(None, "atime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_ATIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_ATIME]))
        cchild = cfile.newChild(None, "mtime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_MTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_MTIME]))

    def serialize(self):
        """ Serializes xml """
        if not self.enabled:
            return

        self.ui_log.info(self.doc.serialize(None,  1))

    def serialize_to_file(self, fname):
        """ Serializes to file """
        if not self.enabled:
            return

        outf = tempfile.NamedTemporaryFile()
        outf.write(self.doc.serialize(None, 1))
        outf.flush()
        self.archive.add_file(outf.name, dest=fname)
        outf.close()

class SoSOptions(object):
    _list_plugins = False
    _noplugins = []
    _enableplugins = []
    _onlyplugins = []
    _plugopts = []
    _usealloptions = False
    _batch = False
    _build = False
    _verbosity = 0
    _quiet = False
    _debug = False
    _ticket_number = ""
    _customer_name = ""
    _config_file = ""
    _tmp_dir = ""
    _report = True
    _compression_type = 'auto'

    _options = None

    def __init__(self, args=None):
        if args:
            self._options = self._parse_args(args)
        else:
            self._options = None
        
    def _check_options_initialized(self):
        if self._options != None:
            raise ValueError("SoSOptions object already initialized "
                             + "from command line")
        
    @property
    def list_plugins(self):
        if self._options != None:
            return self._options.list_plugins
        return self._list_plugins

    @list_plugins.setter
    def list_plugins(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.list_plugins expects a boolean")
        self._list_plugins = value

    @property
    def noplugins(self):
        if self._options != None:
            return self._options.noplugins
        return self._noplugins

    @noplugins.setter
    def noplugins(self, value):
        self._check_options_initialized()
        self._noplugins = value

    @property
    def enableplugins(self):
        if self._options != None:
            return self._options.enableplugins
        return self._enableplugins

    @enableplugins.setter
    def enableplugins(self):
        self._check_options_initialized()
        self._enableplugins = value

    @property
    def onlyplugins(self):
        if self._options != None:
            return self._options.onlyplugins
        return self._onlyplugins

    @onlyplugins.setter
    def onlyplugins(self, value):
        self._check_options_initialized()
        self._onlyplugins = value

    @property
    def plugopts(self):
        if self._options != None:
            return self._options.plugopts
        return self._plugopts

    @plugopts.setter
    def plugopts(self, value):
        # If we check for anything it should be itterability.
        #if not isinstance(value, list):
        #    raise TypeError("SoSOptions.plugopts expects a list")
        self._plugopts = value

    @property
    def usealloptions(self):
        if self._options != None:
            return self._options.usealloptions
        return self._usealloptions

    @usealloptions.setter
    def usealloptions(self, value):
        self._check_options_initialized()
        if not isinsance(value, bool):
            raise TypeError("SoSOptions.usealloptions expects a boolean")
        self._usealloptions = value

    @property
    def batch(self):
        if self._options != None:
            return self._options.batch
        return self._batch

    @batch.setter
    def batch(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.batch expects a boolean")
        self._batch = value

    @property
    def build(self):
        if self._options != None:
            return self._options.build
        return self._build

    @build.setter
    def build(self):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.build expects a boolean")
        self._build = value

    @property
    def verbosity(self):
        if self._options != None:
            return self._options.verbosity
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        self._check_options_initialized()
        if value < 0 or value > 3:
            raise ValueError("SoSOptions.verbosity expects a value [0..3]")
        self._verbosity = value

    @property
    def quiet(self):
        if self._options != None:
            return self._options.quiet
        return self._quiet

    @quiet.setter
    def quiet(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.quiet expects a boolean")
        self._quiet = value
        
    @property
    def debug(self):
        if self._options != None:
            return self._options.debug
        return self._debug

    @debug.setter
    def debug(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.debug expects a boolean")
        self._debug = value

    @property
    def ticket_number(self):
        if self._options != None:
            return self._options.ticket_number
        return self._ticket_number

    @ticket_number.setter
    def ticket_number(self, value):
        self._check_options_initialized()
        self._ticket_number = value

    @property
    def customer_name(self):
        if self._options != None:
            return self._options.customer_name
        return self._customer_name

    @customer_name.setter
    def customer_name(self, value):
        self._check_options_initialized()
        self._customer_name = value

    @property
    def config_file(self):
        if self._options != None:
            return self._options.config_file
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        self._check_options_initialized()
        self._config_file = value

    @property
    def tmp_dir(self):
        if self._options != None:
            return self._options.tmp_dir
        return self._tmp_dir

    @tmp_dir.setter
    def tmp_dir(self, value):
        self._check_options_initialized()
        self._tmp_dir = value

    @property
    def report(self):
        if self._options != None:
            return self._options.report
        return self._report

    @report.setter
    def report(self, value):
        self._check_options_initialized()
        if not isinstance(value, bool):
            raise TypeError("SoSOptions.report expects a boolean")
        self._report = value

    @property
    def compression_type(self):
        if self._options != None:
            return self._options.compression_type
        return self._compression_type

    @compression_type.setter
    def compression_type(self, value):
        self._check_options_initialized()
        self._compression_type = value


    def _parse_args(self, args):
        """ Parse command line options and arguments"""

        self.parser = parser = OptionParserExtended(option_class=SosOption)
        parser.add_option("-l", "--list-plugins", action="store_true",
                             dest="list_plugins", default=False,
                             help="list plugins and available plugin options")
        parser.add_option("-n", "--skip-plugins", action="extend",
                             dest="noplugins", type="string",
                             help="disable these plugins", default = deque())
        parser.add_option("-e", "--enable-plugins", action="extend",
                             dest="enableplugins", type="string",
                             help="enable these plugins", default = deque())
        parser.add_option("-o", "--only-plugins", action="extend",
                             dest="onlyplugins", type="string",
                             help="enable these plugins only", default = deque())
        parser.add_option("-k", "--plugin-option", action="extend",
                             dest="plugopts", type="string",
                             help="plugin options in plugname.option=value format (see -l)",
                             default = deque())
        parser.add_option("-a", "--alloptions", action="store_true",
                             dest="usealloptions", default=False,
                             help="enable all options for loaded plugins")
        parser.add_option("--batch", action="store_true",
                             dest="batch", default=False,
                             help="batch mode - do not prompt interactively")
        parser.add_option("--build", action="store_true", \
                             dest="build", default=False, \
                             help="keep sos tree available and dont package results")
        parser.add_option("-v", "--verbose", action="count",
                             dest="verbosity",
                             help="increase verbosity")
        parser.add_option("", "--quiet", action="store_true",
                             dest="quiet", default=False,
                             help="only print fatal errors")
        parser.add_option("--debug", action="count",
                             dest="debug",
                             help="enable interactive debugging using the python debugger")
        parser.add_option("--ticket-number", action="store",
                             dest="ticket_number",
                             help="specify ticket number")
        parser.add_option("--name", action="store",
                             dest="customer_name",
                             help="specify report name")
        parser.add_option("--config-file", action="store",
                             dest="config_file",
                             help="specify alternate configuration file")
        parser.add_option("--tmp-dir", action="store",
                             dest="tmp_dir",
                             help="specify alternate temporary directory", default=None)
        parser.add_option("--no-report", action="store_true",
                             dest="report",
                             help="Disable HTML/XML reporting", default=False)
        parser.add_option("-z", "--compression-type", dest="compression_type",
                            help="compression technology to use [auto, zip, gzip, bzip2, xz] (default=auto)",
                            default="auto")

        return parser.parse_args(args)[0]

# file system errors that should terminate a run
fatal_fs_errors = (errno.ENOSPC, errno.EROFS)

class SoSReport(object):

    def __init__(self, args):
        self.loaded_plugins = deque()
        self.skipped_plugins = deque()
        self.all_options = deque()
        self.xml_report = XmlReport()
        self.global_plugin_options = {}
        self.archive = None
        self.tempfile_util = None

        try:
            import signal
            signal.signal(signal.SIGTERM, self.get_exit_handler())
        except Exception:
            pass # not available in java, but we don't care


        #self.opts = self.parse_options(args)[0]
        self.opts = SoSOptions(args)
        self._set_debug()
        self._read_config()
        try:
            self.policy = sos.policies.load()
        except KeyboardInterrupt:
           self._exit(0)
        self._is_root = self.policy.is_root()
        self.tmpdir = os.path.abspath(
            self.policy.get_tmp_dir(self.opts.tmp_dir))
        if not os.path.isdir(self.tmpdir) \
        or not os.access(self.tmpdir, os.W_OK):
            # write directly to stderr as logging is not initialised yet
            sys.stderr.write("temporary directory %s " % self.tmpdir \
                        + "does not exist or is not writable\n")
            self._exit(1)
        self.tempfile_util = TempFileUtil(self.tmpdir)
        self._set_directories()

    def print_header(self):
        self.ui_log.info("\n%s\n" % _("sosreport (version %s)" % (__version__,)))

    def get_commons(self):
        return {
                'cmddir': self.cmddir,
                'logdir': self.logdir,
                'rptdir': self.rptdir,
                'tmpdir': self.tmpdir,
                'soslog': self.soslog,
                'policy': self.policy,
                'verbosity': self.opts.verbosity,
                'xmlreport': self.xml_report,
                'cmdlineopts': self.opts,
                'config': self.config,
                'global_plugin_options': self.global_plugin_options,
                }

    def get_temp_file(self):
        return self.tempfile_util.new()

    def _set_archive(self):
        if self.opts.compression_type not in ('auto', 'zip', 'bzip2', 'gzip', 'xz'):
            raise Exception("Invalid compression type specified. Options are:" +
                            "auto, zip, bzip2, gzip and xz")
        archive_name = os.path.join(self.tmpdir,self.policy.get_archive_name())
        if self.opts.compression_type == 'auto':
            auto_archive = self.policy.preferred_archive_name()
            self.archive = auto_archive(archive_name, self.tmpdir)
        elif self.opts.compression_type == 'zip':
            self.archive = ZipFileArchive(archive_name, self.tmpdir)
        else:
            self.archive = TarFileArchive(archive_name, self.tmpdir)

    def _make_archive_paths(self):
        self.archive.makedirs(self.cmddir, 0o755)
        self.archive.makedirs(self.logdir, 0o755)
        self.archive.makedirs(self.rptdir, 0o755)

    def _set_directories(self):
        self.cmddir = 'sos_commands'
        self.logdir = 'sos_logs'
        self.rptdir = 'sos_reports'

    def _set_debug(self):
        if self.opts.debug:
            sys.excepthook = self._exception
            self.raise_plugins = True
        else:
            self.raise_plugins = False

    @staticmethod
    def _exception(etype, eval_, etrace):
        """ Wrap exception in debugger if not in tty """
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
            # we are in interactive mode or we don't have a tty-like
            # device, so we call the default hook
            sys.__excepthook__(etype, eval_, etrace)
        else:
            import traceback, pdb
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, eval_, etrace, limit=2, file=sys.stdout)
            print_()
            # ...then start the debugger in post-mortem mode.
            pdb.pm()

    def _exit(self, error=0):
        raise SystemExit()
#        sys.exit(error)

    def get_exit_handler(self):
        def exit_handler(signum, frame):
            self._exit()
        return exit_handler

    def _read_config(self):
        self.config = ConfigParser()
        if self.opts.config_file:
            config_file = self.opts.config_file
        else:
            config_file = '/etc/sos.conf'
        try:
            self.config.readfp(open(config_file))
        except IOError:
            pass

    def _setup_logging(self):
        # main soslog
        self.soslog = logging.getLogger('sos')
        self.soslog.setLevel(logging.DEBUG)
        self.sos_log_file = self.get_temp_file()
        self.sos_log_file.close()
        flog = logging.FileHandler(self.sos_log_file.name)
        flog.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        flog.setLevel(logging.INFO)
        self.soslog.addHandler(flog)

        if not self.opts.quiet:
            console = logging.StreamHandler(sys.stderr)
            console.setFormatter(logging.Formatter('%(message)s'))
            if self.opts.verbosity and self.opts.verbosity > 1:
                console.setLevel(logging.DEBUG)
                flog.setLevel(logging.DEBUG)
            elif self.opts.verbosity and self.opts.verbosity > 0:
                console.setLevel(logging.INFO)
                flog.setLevel(logging.DEBUG)
            else:
                console.setLevel(logging.WARNING)
            self.soslog.addHandler(console)

        # ui log
        self.ui_log = logging.getLogger('sos_ui')
        self.ui_log.setLevel(logging.INFO)
        self.sos_ui_log_file = self.get_temp_file()
        self.sos_ui_log_file.close()
        ui_fhandler = logging.FileHandler(self.sos_ui_log_file.name)
        ui_fhandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

        self.ui_log.addHandler(ui_fhandler)

        if not self.opts.quiet:
            ui_console = logging.StreamHandler(sys.stdout)
            ui_console.setFormatter(logging.Formatter('%(message)s'))
            ui_console.setLevel(logging.INFO)
            self.ui_log.addHandler(ui_console)

    def _finish_logging(self):
        logging.shutdown()

        # the logging module seems to persist in the jython/jboss/eap world
        # so the handlers need to be removed
        for logger in [logging.getLogger(x) for x in ('sos', 'sos_ui')]:
            for h in logger.handlers:
                logger.removeHandler(h)

        if getattr(self, "sos_log_file", None):
            self.archive.add_file(self.sos_log_file.name, dest=os.path.join('sos_logs', 'sos.log'))
        if getattr(self, "sos_ui_log_file", None):
            self.archive.add_file(self.sos_ui_log_file.name, dest=os.path.join('sos_logs', 'ui.log'))

    def _get_disabled_plugins(self):
        disabled = []
        if self.config.has_option("plugins", "disable"):
            disabled = [plugin.strip() for plugin in
                        self.config.get("plugins", "disable").split(',')]
        return disabled

    def _is_skipped(self, plugin_name):
        return (plugin_name in self.opts.noplugins or
                plugin_name in self._get_disabled_plugins())

    def _is_inactive(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).check_enabled() and
                not plugin_name in self.opts.enableplugins  and
                not plugin_name in self.opts.onlyplugins)

    def _is_not_default(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).default_enabled() and
                not plugin_name in self.opts.enableplugins and
                not plugin_name in self.opts.onlyplugins)

    def _is_not_specified(self, plugin_name):
        return (self.opts.onlyplugins and
                not plugin_name in self.opts.onlyplugins)

    def _skip(self, plugin_class, reason="unknown"):
        self.skipped_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons()),
            reason
        ))

    def _load(self, plugin_class):
        self.loaded_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons())
        ))


    def load_plugins(self):

        import sos.plugins
        helper = ImporterHelper(sos.plugins)
        plugins = helper.get_modules()
        self.plugin_names = deque()

        # validate and load plugins
        for plug in plugins:
            plugbase, ext = os.path.splitext(plug)
            try:
                plugin_classes = import_plugin(plugbase,
                        tuple(self.policy.valid_subclasses))
                if not len(plugin_classes):
                    # no valid plugin classes for this policy
                    continue

                plugin_class = self.policy.match_plugin(plugin_classes)
                if not self.policy.validate_plugin(plugin_class):
                    self.soslog.warning(_("plugin %s does not validate, skipping") % plug)
                    if self.opts.verbosity > 0:
                        self._skip(plugin_class, _("does not validate"))
                        continue

                if plugin_class.requires_root and not self._is_root:
                    self.soslog.info(_("plugin %s requires root permissions to execute, skipping") % plug)
                    self._skip(plugin_class, _("requires root"))
                    continue

                # plug-in is valid, let's decide whether run it or not
                self.plugin_names.append(plugbase)

                if  self._is_skipped(plugbase):
                    self._skip(plugin_class, _("skipped"))
                    continue

                if  self._is_inactive(plugbase, plugin_class):
                    self._skip(plugin_class, _("inactive"))
                    continue

                if  self._is_not_default(plugbase, plugin_class):
                    self._skip(plugin_class, _("not default"))
                    continue

                if  self._is_not_specified(plugbase):
                    self._skip(plugin_class, _("not specified"))
                    continue

                self._load(plugin_class)
            except Exception as e:
                self.soslog.warning(_("plugin %s does not install, skipping: %s") % (plug, e))
                if self.raise_plugins:
                    raise

    def _set_all_options(self):
        if self.opts.usealloptions:
            for plugname, plug in self.loaded_plugins:
                for name, parms in zip(plug.opt_names, plug.opt_parms):
                    if type(parms["enabled"])==bool:
                        parms["enabled"] = True

    def _set_tunables(self):
        if self.config.has_section("tunables"):
            if not self.opts.plugopts:
                self.opts.plugopts = deque()

            for opt, val in self.config.items("tunables"):
                if not opt.split('.')[0] in self._get_disabled_plugins():
                    self.opts.plugopts.append(opt + "=" + val)
        if self.opts.plugopts:
            opts = {}
            for opt in self.opts.plugopts:
                # split up "general.syslogsize=5"
                try:
                    opt, val = opt.split("=")
                except:
                    val = True
                else:
                    if val.lower() in ["off", "disable", "disabled", "false"]:
                        val = False
                    else:
                        # try to convert string "val" to int()
                        try:
                            val = int(val)
                        except:
                            pass

                # split up "general.syslogsize"
                try:
                    plug, opt = opt.split(".")
                except:
                    plug = opt
                    opt = True

                try:
                    opts[plug]
                except KeyError:
                    opts[plug] = deque()
                opts[plug].append( (opt, val) )

            for plugname, plug in self.loaded_plugins:
                if plugname in opts:
                    for opt, val in opts[plugname]:
                        if not plug.set_option(opt, val):
                            self.soslog.error('no such option "%s" for plugin '
                                         '(%s)' % (opt,plugname))
                            self._exit(1)
                    del opts[plugname]
            for plugname in opts.keys():
                self.soslog.error('unable to set option for disabled or non-existing '
                             'plugin (%s)' % (plugname))

    def _check_for_unknown_plugins(self):
        import itertools
        for plugin in itertools.chain(self.opts.onlyplugins,
                                      self.opts.noplugins,
                                      self.opts.enableplugins):
            plugin_name = plugin.split(".")[0]
            if not plugin_name in self.plugin_names:
                self.soslog.fatal('a non-existing plugin (%s) was specified in the '
                             'command line' % (plugin_name))
                self._exit(1)

    def _set_plugin_options(self):
        for plugin_name, plugin in self.loaded_plugins:
            names, parms = plugin.get_all_options()
            for optname, optparm in zip(names, parms):
                self.all_options.append((plugin, plugin_name, optname, optparm))

    def list_plugins(self):
        if not self.loaded_plugins and not self.skipped_plugins:
            self.soslog.fatal(_("no valid plugins found"))
            return

        if self.loaded_plugins:
            self.ui_log.info(_("The following plugins are currently enabled:"))
            self.ui_log.info("")
            for (plugname, plug) in self.loaded_plugins:
                self.ui_log.info(" %-20s %s" % (plugname, plug.get_description()))
        else:
            self.ui_log.info(_("No plugin enabled."))
        self.ui_log.info("")

        if self.skipped_plugins:
            self.ui_log.info(_("The following plugins are currently disabled:"))
            self.ui_log.info("")
            for (plugname, plugclass, reason) in self.skipped_plugins:
                self.ui_log.info(" %-20s %-14s %s" % (plugname,
                                     reason,
                                     plugclass.get_description()))
        self.ui_log.info("")

        if self.all_options:
            self.ui_log.info(_("The following plugin options are available:"))
            self.ui_log.info("")
            for (plug, plugname, optname, optparm)  in self.all_options:
                # format option value based on its type (int or bool)
                if type(optparm["enabled"]) == bool:
                    if optparm["enabled"] == True:
                        tmpopt = "on"
                    else:
                        tmpopt = "off"
                else:
                    tmpopt = optparm["enabled"]

                self.ui_log.info(" %-25s %-15s %s" % (
                    plugname + "." + optname, tmpopt, optparm["desc"]))
        else:
            self.ui_log.info(_("No plugin options available."))

        self.ui_log.info("")

    def batch(self):
        if self.opts.batch:
            self.ui_log.info(self.policy.get_msg())
        else:
            msg = self.policy.get_msg()
            msg += _("Press ENTER to continue, or CTRL-C to quit.\n")
            try:
                input(msg)
            except:
                self.ui_log.info("")
                self._exit()

    def _log_plugin_exception(self, plugin_name):
        self.soslog.error("%s\n%s" % (plugin_name, traceback.format_exc()))

    def prework(self):
        self.policy.pre_work()
        try:
            self.ui_log.info(_(" Setting up archive ..."))
            self._set_archive()
            self._make_archive_paths()
            return
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while setting up archive" % e.strerror)
                self.ui_log.error("")
            else:
                raise e
        except Exception as e:
            import traceback
            self.ui_log.error("")
            self.ui_log.error(" Unexpected exception setting up archive:")
            traceback.print_exc(e)
            self.ui_log.error(e)
        self._exit(1)

    def setup(self):
        self.ui_log.info(_(" Setting up plugins ..."))
        for plugname, plug in self.loaded_plugins:
            try:
                plug.archive = self.archive
                plug.setup()
            except KeyboardInterrupt:
                raise
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while setting up plugins"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception(plugname)

    def version(self):
        """Fetch version information from all plugins and store in the report
        version file"""

        versions = []
        versions.append("sosreport: %s" % __version__)
        for plugname, plug in self.loaded_plugins:
            versions.append("%s: %s" % (plugname, plug.version))
        self.archive.add_string(content="\n".join(versions), dest='version.txt')


    def collect(self):
        self.ui_log.info(_(" Running plugins. Please wait ..."))
        self.ui_log.info("")

        plugruncount = 0
        for i in zip(self.loaded_plugins):
            plugruncount += 1
            plugname, plug = i[0]
            status_line = ("  Running %d/%d: %s...        "
                           % (plugruncount, len(self.loaded_plugins), plugname))
            if self.opts.verbosity == 0:
                status_line = "\r%s" % status_line
            else:
                status_line = "%s\n" % status_line
            if not self.opts.quiet:
                sys.stdout.write(status_line)
                sys.stdout.flush()
            try:
                plug.collect()
            except KeyboardInterrupt:
                raise
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while collecting plugin data"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception(plugname)
        self.ui_log.info("")


    def report(self):
        for plugname, plug in self.loaded_plugins:
            for oneFile in plug.copied_files:
                try:
                    self.xml_report.add_file(oneFile["srcpath"], os.stat(oneFile["srcpath"]))
                except:
                    pass

        try:
            self.xml_report.serialize_to_file(os.path.join(self.rptdir, "sosreport.xml"))
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing report data"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)


    def plain_report(self):
        report = Report()

        for plugname, plug in self.loaded_plugins:
            section = Section(name=plugname)

            for alert in plug.alerts:
                section.add(Alert(alert))

            if plug.custom_text:
                section.add(Note(plug.custom_text))

            for f in plug.copied_files:
                section.add(CopiedFile(name=f['srcpath'],
                            href= ".." + f['dstpath']))

            for cmd in plug.executed_commands:
                section.add(Command(name=cmd['exe'], return_code=0,
                            href="../" + cmd['file']))

            for content, f in plug.copy_strings:
                section.add(CreatedFile(name=f))

            report.add(section)
        try:
            fd = self.get_temp_file()
            fd.write(str(PlainTextReport(report)))
            fd.flush()
            self.archive.add_file(fd.name, dest=os.path.join('sos_reports', 'sos.txt'))
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing text report"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)

    def html_report(self):
        try:
            self._html_report()
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error("")
                self.ui_log.error(" %s while writing HTML report"
                                  % e.strerror)
                self.ui_log.error("")
                self._exit(1)

    def _html_report(self):
        # Generate the header for the html output file
        rfd = self.get_temp_file()
        rfd.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
            <head>
        <link rel="stylesheet" type="text/css" media="screen" href="donot.css" />
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>Sos System Report</title>
            </head>

            <body>
        """)


        # Make a pass to gather Alerts and a list of module names
        allAlerts = deque()
        plugNames = deque()
        for plugname, plug in self.loaded_plugins:
            for alert in plug.alerts:
                allAlerts.append('<a href="#%s">%s</a>: %s' % (plugname, plugname,
                                                               alert))
            plugNames.append(plugname)

        # Create a table of links to the module info
        rfd.write("<hr/><h3>Loaded Plugins:</h3>")
        rfd.write("<table><tr>\n")
        rr = 0
        for i in range(len(plugNames)):
            rfd.write('<td><a href="#%s">%s</a></td>\n' % (plugNames[i],
                                                           plugNames[i]))
            rr = divmod(i, 4)[1]
            if (rr == 3):
                rfd.write('</tr>')
        if not (rr == 3):
            rfd.write('</tr>')
        rfd.write('</table>\n')

        rfd.write('<hr/><h3>Alerts:</h3>')
        rfd.write('<ul>')
        for alert in allAlerts:
            rfd.write('<li>%s</li>' % alert)
        rfd.write('</ul>')


        # Call the report method for each plugin
        for plugname, plug in self.loaded_plugins:
            try:
                html = plug.report()
            except:
                if self.raise_plugins:
                    raise
            else:
                rfd.write(html)

        rfd.write("</body></html>")

        rfd.flush()

        self.archive.add_file(rfd.name, dest=os.path.join('sos_reports', 'sos.html'))

    def postproc(self):
        for plugname, plug in self.loaded_plugins:
            try:
                plug.postproc()
            except (OSError, IOError) as e:
             if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(" %s while post-processing plugin data"
                                      % e.strerror)
                    self.ui_log.error("")
                    self._exit(1)
            except:
                if self.raise_plugins:
                    raise

    def final_work(self):
        # this must come before archive creation to ensure that log
        # files are closed and cleaned up at exit.
        self._finish_logging()
        # package up the results for the support organization
        if not self.opts.build:
            print (_("Creating compressed archive..."))
            # compression could fail for a number of reasons
            try:
                final_filename = self.archive.finalize(self.opts.compression_type)
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                   self.ui_log.error("")
                   self.ui_log.error(" %s while finalizing archive"
                                     % e.strerror)
                   self.ui_log.error("")
                   self._exit(1)
            except:
                if self.opts.debug:
                    raise
                else:
                    return False

        else:
            final_filename = self.archive.get_archive_path()

        self.policy.display_results(final_filename, build = self.opts.build)
        self.tempfile_util.clean()

        return True


    def verify_plugins(self):
        if not self.loaded_plugins:
            self.soslog.error(_("no valid plugins were enabled"))
            return False
        return True


    def set_global_plugin_option(self, key, value):
        self.global_plugin_options[key] = value;


    def execute(self):
        try:
            self._setup_logging()
            self.policy.set_commons(self.get_commons())
            self.print_header()
            self.load_plugins()
            self._set_all_options()
            self._set_tunables()
            self._check_for_unknown_plugins()
            self._set_plugin_options()

            if self.opts.list_plugins:
                self.list_plugins()
                return True

            # verify that at least one plug-in is enabled
            if not self.verify_plugins():
                return False

            self.batch()
            self.prework()
            self.setup()
            self.collect()
            if not self.opts.report:
                self.report()
                self.html_report()
                self.plain_report()
            self.postproc()
            self.version()

            return self.final_work()
        except (SystemExit, KeyboardInterrupt):
            if self.archive:
                self.archive.cleanup()
            if self.tempfile_util:
                self.tempfile_util.clean()
            return False

def main(args):
    """The main entry point"""
    sos = SoSReport(args)
    sos.execute()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = utilities
### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# pylint: disable-msg = R0902
# pylint: disable-msg = R0904
# pylint: disable-msg = W0702
# pylint: disable-msg = W0703
# pylint: disable-msg = R0201
# pylint: disable-msg = W0611
# pylint: disable-msg = W0613

from __future__ import with_statement

import os
import re
import inspect
from stat import *
#from itertools import *
from subprocess import Popen, PIPE, STDOUT
import zipfile
import tarfile
import hashlib
import logging
import fnmatch
import errno
import shlex

from contextlib import closing

# PYCOMPAT
import six
from six import StringIO

import time

def tail(filename, number_of_bytes):
    """Returns the last number_of_bytes of filename"""
    with open(filename, "rb") as f:
        if os.stat(filename).st_size > number_of_bytes:
            f.seek(-number_of_bytes, 2)
        return f.read()


def fileobj(path_or_file, mode='r'):
    """Returns a file-like object that can be used as a context manager"""
    if isinstance(path_or_file, six.string_types):
        try:
            return open(path_or_file, mode)
        except:
            log = logging.getLogger('sos')
            log.debug("fileobj: %s could not be opened" % path_or_file)
            return closing(StringIO())
    else:
        return closing(path_or_file)

def get_hash_name():
    """Returns the algorithm used when computing a hash"""
    import sos.policies
    policy = sos.policies.load()
    try:
        name = policy.get_preferred_hash_algorithm()
        hashlib.new(name)
        return name
    except:
        return 'sha256'

def convert_bytes(bytes_, K=1 << 10, M=1 << 20, G=1 << 30, T=1 << 40):
    """Converts a number of bytes to a shorter, more human friendly format"""
    fn = float(bytes_)
    if bytes_ >= T:
        return '%.1fT' % (fn / T)
    elif bytes_ >= G:
        return '%.1fG' % (fn / G)
    elif bytes_ >= M:
        return '%.1fM' % (fn / M)
    elif bytes_ >= K:
        return '%.1fK' % (fn / K)
    else:
        return '%d' % bytes_

def find(file_pattern, top_dir, max_depth=None, path_pattern=None):
    """generator function to find files recursively. Usage:

    for filename in find("*.properties", "/var/log/foobar"):
        print filename
    """
    if max_depth:
        base_depth = os.path.dirname(top_dir).count(os.path.sep)
        max_depth += base_depth

    for path, dirlist, filelist in os.walk(top_dir):
        if max_depth and path.count(os.path.sep) >= max_depth:
            del dirlist[:]

        if path_pattern and not fnmatch.fnmatch(path, path_pattern):
            continue

        for name in fnmatch.filter(filelist, file_pattern):
            yield os.path.join(path, name)


def grep(pattern, *files_or_paths):
    """Returns lines matched in fnames, where fnames can either be pathnames to files
    to grep through or open file objects to grep through line by line"""
    matches = []

    for fop in files_or_paths:
        with fileobj(fop) as fo:
            matches.extend((line for line in fo if re.match(pattern, line)))

    return matches

def is_executable(command):
    """Returns if a command matches an executable on the PATH"""

    paths = os.environ.get("PATH", "").split(os.path.pathsep)
    candidates = [command] + [os.path.join(p, command) for p in paths]
    return any(os.access(path, os.X_OK) for path in candidates)

def sos_get_command_output(command, timeout=300, runat=None):
    """Execute a command through the system shell. First checks to see if the
    requested command is executable. Returns (returncode, stdout, 0)"""
    def _child_chdir():
        if(runat):
            try:
                os.chdir(runat)
            except:
                self.log_error("failed to chdir to '%s'" % runat)
            
    cmd_env = os.environ
    # ensure consistent locale for collected command output
    cmd_env['LC_ALL'] = 'C'
    # use /usr/bin/timeout to implement a timeout
    if timeout and is_executable("timeout"):
        command = "timeout %ds %s" % (timeout, command)

    args = shlex.split(command)
    try:
        p = Popen(args, shell=False, stdout=PIPE, stderr=STDOUT,
              bufsize=-1, env = cmd_env, close_fds = True,
              preexec_fn=_child_chdir)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return {'status': 127, 'output': ""}
        else:
            raise e

    stdout, stderr = p.communicate()

    # Required hack while we still pass shell=True to Popen; a Popen
    # call with shell=False for a non-existant binary will raise OSError.
    if p.returncode == 127:
        stdout = six.binary_type(b"")
    
    return {'status': p.returncode, 'output': stdout.decode('utf-8')}

def import_module(module_fqname, superclasses=None):
    """Imports the module module_fqname and returns a list of defined classes
    from that module. If superclasses is defined then the classes returned will
    be subclasses of the specified superclass or superclasses. If superclasses
    is plural it must be a tuple of classes."""
    module_name = module_fqname.rpartition(".")[-1]
    module = __import__(module_fqname, globals(), locals(), [module_name])
    modules = [class_ for cname, class_ in
               inspect.getmembers(module, inspect.isclass)
               if class_.__module__ == module_fqname]
    if superclasses:
        modules = [m for m in modules if issubclass(m, superclasses)]

    return modules

def shell_out(cmd, runat=None):
    """Shell out to an external command and return the output or the empty
    string in case of error.
    """
    return sos_get_command_output(cmd, runat=runat)['output']

class ImporterHelper(object):
    """Provides a list of modules that can be imported in a package.
    Importable modules are located along the module __path__ list and modules
    are files that end in .py. This class will read from PKZip archives as well
    for listing out jar and egg contents."""

    def __init__(self, package):
        """package is a package module
        import my.package.module
        helper = ImporterHelper(my.package.module)"""
        self.package = package

    def _plugin_name(self, path):
        "Returns the plugin module name given the path"
        base = os.path.basename(path)
        name, ext = os.path.splitext(base)
        return name

    def _get_plugins_from_list(self, list_):
        plugins = [self._plugin_name(plugin)
                for plugin in list_
                if "__init__" not in plugin
                and plugin.endswith(".py")]
        plugins.sort()
        return plugins

    def _find_plugins_in_dir(self, path):
        if os.path.exists(path):
            py_files = list(find("*.py", path))
            pnames = self._get_plugins_from_list(py_files)
            if pnames:
                return pnames
            else:
                return []

    def _get_path_to_zip(self, path, tail_list=None):
        if not tail_list:
            tail_list = ['']

        if path.endswith(('.jar', '.zip', '.egg')):
            return path, os.path.join(*tail_list)

        head, tail = os.path.split(path)
        tail_list.insert(0, tail)

        if head == path:
            raise Exception("not a zip file")
        else:
            return self._get_path_to_zip(head, tail_list)


    def _find_plugins_in_zipfile(self, path):
        try:
            path_to_zip, tail = self._get_path_to_zip(path)
            zf = zipfile.ZipFile(path_to_zip)
            # the path will have os separators, but the zipfile will always have '/'
            tail = tail.replace(os.path.sep, "/")
            root_names = [name for name in zf.namelist() if tail in name]
            candidates = self._get_plugins_from_list(root_names)
            zf.close()
            if candidates:
                return candidates
            else:
                return []
        except (IOError, Exception):
            return []

    def get_modules(self):
        "Returns the list of importable modules in the configured python package."
        plugins = []
        for path in self.package.__path__:
            if os.path.isdir(path) or path == '':
                plugins.extend(self._find_plugins_in_dir(path))
            else:
                plugins.extend(self._find_plugins_in_zipfile(path))

        return plugins

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = archive_tests
#!/usr/bin/env python

import unittest
import os
import tarfile
import zipfile
import tempfile
import shutil

from sos.archive import TarFileArchive, ZipFileArchive

# PYCOMPAT
import six

class ZipFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.zf = ZipFileArchive('test')

    def tearDown(self):
        os.unlink('test.zip')

    def check_for_file(self, filename):
        zf = zipfile.ZipFile('test.zip', 'r')
        zf.getinfo(filename)
        zf.close()

    def test_create(self):
        self.zf.close()

    def test_add_file(self):
        self.zf.add_file('tests/ziptest')
        self.zf.close()

        self.check_for_file('tests/ziptest')

    def test_add_unicode_file(self):
        self.zf.add_file(six.u('tests/'))
        self.zf.close()

        self.check_for_file('tests/ziptest')

    def test_add_dir(self):
        self.zf.add_file('tests/')
        self.zf.close()

        self.check_for_file('tests/ziptest')

    def test_add_renamed(self):
        self.zf.add_file('tests/ziptest', dest='tests/ziptest_renamed')
        self.zf.close()

        self.check_for_file('tests/ziptest_renamed')

    def test_add_renamed_dir(self):
        self.zf.add_file('tests/', 'tests_renamed/')
        self.zf.close()

        self.check_for_file('tests_renamed/ziptest')

    def test_add_string(self):
        self.zf.add_string('this is content', 'tests/string_test.txt')
        self.zf.close()

        self.check_for_file('tests/string_test.txt')

    def test_get_file(self):
        self.zf.add_string('this is my content', 'tests/string_test.txt')

        afp = self.zf.open_file('tests/string_test.txt')
        self.assertEquals(six.b('this is my content'), afp.read())

    def test_overwrite_file(self):
        self.zf.add_string('this is my content', 'tests/string_test.txt')
        self.zf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.zf.open_file('tests/string_test.txt')
        self.assertEquals(six.b('this is my new content'), afp.read())

# Disabled as new api doesnt provide a add_link routine
#    def test_make_link(self):
#        self.zf.add_file('tests/ziptest')
#        self.zf.add_link('tests/ziptest', 'link_name')
#
#        self.zf.close()
#        try:
#            self.check_for_file('test/link_name')
#            self.fail("link should not exist")
#        except KeyError:
#            pass

# Disabled as new api doesnt provide a compress routine
#    def test_compress(self):
#        self.assertEquals(self.zf.compress("zip"), self.zf.name())


class TarFileArchiveTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tf = TarFileArchive('test', self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def check_for_file(self, filename):
        rtf = tarfile.open(os.path.join(self.tmpdir, 'test.tar'))
        rtf.getmember(filename)
        rtf.close()

    def test_create(self):
        self.tf.finalize('auto')
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir,
                                                    'test.tar')))

    def test_add_file(self):
        self.tf.add_file('tests/ziptest')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/ziptest')

# Since commit 179d9bb add_file does not support recursive directory
# addition. Disable this test for now.
#    def test_add_dir(self):
#        self.tf.add_file('tests/')
#        self.tf.close()
#
#        self.check_for_file('test/tests/ziptest')

    def test_add_renamed(self):
        self.tf.add_file('tests/ziptest', dest='tests/ziptest_renamed')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/ziptest_renamed')

# Since commit 179d9bb add_file does not support recursive directory
# addition. Disable this test for now.
#    def test_add_renamed_dir(self):
#        self.tf.add_file('tests/', 'tests_renamed/')
#        self.tf.close()
#
#        self.check_for_file('test/tests_renamed/ziptest')

    def test_add_string(self):
        self.tf.add_string('this is content', 'tests/string_test.txt')
        self.tf.finalize('auto')

        self.check_for_file('test/tests/string_test.txt')

    def test_get_file(self):
        self.tf.add_string('this is my content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my content', afp.read())

    def test_overwrite_file(self):
        self.tf.add_string('this is my content', 'tests/string_test.txt')
        self.tf.add_string('this is my new content', 'tests/string_test.txt')

        afp = self.tf.open_file('tests/string_test.txt')
        self.assertEquals('this is my new content', afp.read())

    def test_make_link(self):
        self.tf.add_file('tests/ziptest')
        self.tf.add_link('tests/ziptest', 'link_name')

        self.tf.finalize('auto')
        self.check_for_file('test/link_name')

    def test_compress(self):
        self.tf.finalize("auto")

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = importer_tests
import unittest

from sos.utilities import ImporterHelper

class ImporterHelperTests(unittest.TestCase):

    def test_runs(self):
        h = ImporterHelper(unittest)
        modules = h.get_modules()
        self.assertTrue('main' in modules)

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = option_tests
#!/usr/bin/env python

import unittest

from sos.plugins import Plugin

class GlobalOptionTest(unittest.TestCase):

    def setUp(self):
        self.commons = {
            'global_plugin_options': {
                'test_option': 'foobar',
                'baz': None,
                'empty_global': True,
            },
        }
        self.plugin = Plugin(self.commons)
        self.plugin.opt_names = ['baz', 'empty']
        self.plugin.opt_parms = [{'enabled': False}, {'enabled': None}]

    def test_simple_lookup(self):
        self.assertEquals(self.plugin.get_option('test_option'), 'foobar')

    def test_multi_lookup(self):
        self.assertEquals(self.plugin.get_option(('not_there', 'test_option')), 'foobar')

    def test_cascade(self):
        self.assertEquals(self.plugin.get_option(('baz')), False)

    def test_none_should_cascade(self):
        self.assertEquals(self.plugin.get_option(('empty', 'empty_global')), True)

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = plugin_tests
import unittest
import os
import tempfile

# PYCOMPAT
import six
try:
    from StringIO import StringIO
except:
    from io import StringIO

from sos.plugins import Plugin, regex_findall, mangle_command
from sos.archive import TarFileArchive, ZipFileArchive
import sos.policies

PATH = os.path.dirname(__file__)

def j(filename):
    return os.path.join(PATH, filename)

def create_file(size):
   f = tempfile.NamedTemporaryFile(delete=False)
   f.write(six.b("*" * size * 1024 * 1024))
   f.flush()
   f.close()
   return f.name

class MockArchive(TarFileArchive):

    def __init__(self):
        self.m = {}
        self.strings = {}

    def name(self):
        return "mock.archive"

    def add_file(self, src, dest=None):
        if not dest:
            dest = src
        self.m[src] = dest

    def add_string(self, content, dest):
        self.m[dest] = content

    def add_link(self, dest, link_name):
        pass

    def open_file(self, name):
        return open(self.m.get(name), 'r')

    def close(self):
        pass

    def compress(self, method):
        pass


class MockPlugin(Plugin):

    option_list = [("opt", 'an option', 'fast', None),
                  ("opt2", 'another option', 'fast', False)]

    def setup(self):
        pass


class NamedMockPlugin(Plugin):
    """This plugin has a description."""

    plugin_name = "testing"

    def setup(self):
        pass


class ForbiddenMockPlugin(Plugin):
    """This plugin has a description."""

    plugin_name = "forbidden"

    def setup(self):
        self.add_forbidden_path("tests")


class EnablerPlugin(Plugin):

    def is_installed(self, pkg):
        return self.is_installed


class MockOptions(object):
    pass


class PluginToolTests(unittest.TestCase):

    def test_regex_findall(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*lines$", test_fo)
        self.assertEquals(matches, ['there are only two lines'])

    def test_regex_findall_miss(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = regex_findall(r".*not_there$", test_fo)
        self.assertEquals(matches, [])

    def test_regex_findall_bad_input(self):
        matches = regex_findall(r".*", None)
        self.assertEquals(matches, [])
        matches = regex_findall(r".*", [])
        self.assertEquals(matches, [])
        matches = regex_findall(r".*", 1)
        self.assertEquals(matches, [])

    def test_mangle_command(self):
        self.assertEquals("foo", mangle_command("/usr/bin/foo"))
        self.assertEquals("foo_-x", mangle_command("/usr/bin/foo -x"))
        self.assertEquals("foo_--verbose", mangle_command("/usr/bin/foo --verbose"))
        self.assertEquals("foo_.path.to.stuff", mangle_command("/usr/bin/foo /path/to/stuff"))
        expected = "foo_.path.to.stuff.this.is.very.long.and.i.only.expect.part.of.it.maybe.this.is.enough.i.hope.so"[0:64]
        self.assertEquals(expected, mangle_command("/usr/bin/foo /path/to/stuff/this/is/very/long/and/i/only/expect/part/of/it/maybe/this/is/enough/i/hope/so"))


class PluginTests(unittest.TestCase):

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions()
        })
        self.mp.archive = MockArchive()

    def test_plugin_default_name(self):
        p = MockPlugin({})
        self.assertEquals(p.name(), "mockplugin")

    def test_plugin_set_name(self):
        p = NamedMockPlugin({})
        self.assertEquals(p.name(), "testing")

    def test_plugin_no_descrip(self):
        p = MockPlugin({})
        self.assertEquals(p.get_description(), "<no description available>")

    def test_plugin_no_descrip(self):
        p = NamedMockPlugin({})
        self.assertEquals(p.get_description(), "This plugin has a description.")

    def test_set_plugin_option(self):
        p = MockPlugin({})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option("opt"), "testing")

    def test_set_nonexistant_plugin_option(self):
        p = MockPlugin({})
        self.assertFalse(p.set_option("badopt", "testing"))

    def test_get_nonexistant_plugin_option(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option("badopt"), 0)

    def test_get_unset_plugin_option(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt"), 0)

    def test_get_unset_plugin_option_with_default(self):
        # this shows that even when we pass in a default to get,
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt", True), True)

    def test_get_unset_plugin_option_with_default_not_none(self):
        # this shows that even when we pass in a default to get,
        # if the plugin default is not None
        # we'll get the option's default as set in the plugin
        # this might not be what we really want
        p = MockPlugin({})
        self.assertEquals(p.get_option("opt2", True), False)

    def test_get_option_as_list_plugin_option(self):
        p = MockPlugin({})
        p.set_option("opt", "one,two,three")
        self.assertEquals(p.get_option_as_list("opt"), ['one', 'two', 'three'])

    def test_get_option_as_list_plugin_option_default(self):
        p = MockPlugin({})
        self.assertEquals(p.get_option_as_list("opt", default=[]), [])

    def test_get_option_as_list_plugin_option_not_list(self):
        p = MockPlugin({})
        p.set_option("opt", "testing")
        self.assertEquals(p.get_option_as_list("opt"), ['testing'])

    def test_copy_dir(self):
        self.mp.do_copy_path("tests")
        self.assertEquals(self.mp.archive.m["tests/plugin_tests.py"], 'tests/plugin_tests.py')

    def test_copy_dir_bad_path(self):
        self.mp.do_copy_path("not_here_tests")
        self.assertEquals(self.mp.archive.m, {})

    def test_copy_dir_forbidden_path(self):
        p = ForbiddenMockPlugin({
            'cmdlineopts': MockOptions()
        })
        p.archive = MockArchive()
        p.setup()
        p.do_copy_path("tests")
        self.assertEquals(p.archive.m, {})


class AddCopySpecTests(unittest.TestCase):

    expect_paths = set(['tests/tail_test.txt'])

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions()
        })
        self.mp.archive = MockArchive()

    def assert_expect_paths(self):
        self.assertEquals(self.mp.copy_paths, self.expect_paths)
        
    # add_copy_spec()

    def test_single_file(self):
        self.mp.add_copy_spec('tests/tail_test.txt')
        self.assert_expect_paths()
    def test_glob_file(self):
        self.mp.add_copy_spec('tests/tail_test.*')
        self.assert_expect_paths()

    def test_single_file_under_limit(self):
        self.mp.add_copy_spec_limit("tests/tail_test.txt", 1)
        self.assert_expect_paths()

    # add_copy_specs()

    def test_add_copy_specs(self):
        self.mp.add_copy_specs(["tests/tail_test.txt"])
        self.assert_expect_paths()

    def test_add_copy_spec_nostrings(self):
        self.assertRaises(TypeError, self.mp.add_copy_specs,"stringsarebadmkay?")

    # add_copy_spec_limit()

    def test_single_file_over_limit(self):
        fn = create_file(2) # create 2MB file, consider a context manager
        self.mp.add_copy_spec_limit(fn, 1)
        content, fname = self.mp.copy_strings[0]
        self.assertTrue("tailed" in fname)
        self.assertTrue("tmp" in fname)
        self.assertTrue("/" not in fname)
        self.assertEquals(1024 * 1024, len(content))
        os.unlink(fn)

    def test_bad_filename(self):
        self.assertFalse(self.mp.add_copy_spec_limit('', 1))
        self.assertFalse(self.mp.add_copy_spec_limit(None, 1))

    def test_glob_file_over_limit(self):
        # assume these are in /tmp
        fn = create_file(2)
        fn2 = create_file(2)
        self.mp.add_copy_spec_limit("/tmp/tmp*", 1)
        self.assertEquals(len(self.mp.copy_strings), 1)
        content, fname = self.mp.copy_strings[0]
        self.assertTrue("tailed" in fname)
        self.assertEquals(1024 * 1024, len(content))
        os.unlink(fn)
        os.unlink(fn2)


class CheckEnabledTests(unittest.TestCase):

    def setUp(self):
        self.mp = EnablerPlugin({'policy': sos.policies.load()})

    def test_checks_for_file(self):
        f = j("tail_test.txt")
        self.mp.files = (f,)
        self.assertTrue(self.mp.check_enabled())

    def test_checks_for_package(self):
        self.mp.packages = ('foo',)
        self.assertTrue(self.mp.check_enabled())

    def test_allows_bad_tuple(self):
        f = j("tail_test.txt")
        self.mp.files = (f)
        self.mp.packages = ('foo')
        self.assertTrue(self.mp.check_enabled())

    def test_enabled_by_default(self):
        self.assertTrue(self.mp.check_enabled())


class RegexSubTests(unittest.TestCase):

    def setUp(self):
        self.mp = MockPlugin({
            'cmdlineopts': MockOptions()
        })
        self.mp.archive = MockArchive()

    def test_file_never_copied(self):
        self.assertEquals(0, self.mp.do_file_sub("never_copied", r"^(.*)$", "foobar"))

    def test_no_replacements(self):
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect()
        replacements = self.mp.do_file_sub(j("tail_test.txt"), r"wont_match", "foobar")
        self.assertEquals(0, replacements)

    def test_replacements(self):
        self.mp.add_copy_spec(j("tail_test.txt"))
        self.mp.collect()
        replacements = self.mp.do_file_sub(j("tail_test.txt"), r"(tail)", "foobar")
        self.assertEquals(1, replacements)
        self.assertTrue("foobar" in self.mp.archive.m.get(j('tail_test.txt')))

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = policy_tests
import unittest

from sos.policies import Policy, PackageManager, import_policy
from sos.plugins import Plugin, IndependentPlugin, RedHatPlugin, DebianPlugin

class FauxPolicy(Policy):
    distro = "Faux"

class FauxPlugin(Plugin, IndependentPlugin):
    pass

class FauxRedHatPlugin(Plugin, RedHatPlugin):
    pass

class FauxDebianPlugin(Plugin, DebianPlugin):
    pass

class PolicyTests(unittest.TestCase):

    def test_independent_only(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertTrue(p.validate_plugin(FauxPlugin))

    def test_redhat(self):
        p = FauxPolicy()
        p.valid_subclasses = [RedHatPlugin]

        self.assertTrue(p.validate_plugin(FauxRedHatPlugin))

    def test_debian(self):
        p = FauxPolicy()
        p.valid_subclasses = [DebianPlugin]

        self.assertTrue(p.validate_plugin(FauxDebianPlugin))

    def test_fails(self):
        p = FauxPolicy()
        p.valid_subclasses = []

        self.assertFalse(p.validate_plugin(FauxDebianPlugin))

    def test_can_import(self):
        self.assertTrue(import_policy('redhat') is not None)

    def test_cant_import(self):
        self.assertTrue(import_policy('notreal') is None)


class PackageManagerTests(unittest.TestCase):

    def setUp(self):
        self.pm = PackageManager()

    def test_default_all_pkgs(self):
        self.assertEquals(self.pm.all_pkgs(), {})

    def test_default_all_pkgs_by_name(self):
        self.assertEquals(self.pm.all_pkgs_by_name('doesntmatter'), [])

    def test_default_all_pkgs_by_name_regex(self):
        self.assertEquals(self.pm.all_pkgs_by_name_regex('.*doesntmatter$'), [])

    def test_default_pkg_by_name(self):
        self.assertEquals(self.pm.pkg_by_name('foo'), None)

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = report_tests
#!/usr/bin/env python

import unittest
import os

try:
    import json
except ImportError:
    import simplejson as json

from sos.reporting import Report, Section, Command, CopiedFile, CreatedFile, Alert
from sos.reporting import PlainTextReport

class ReportTest(unittest.TestCase):

    def test_empty(self):
        report = Report()

        expected = json.dumps({})

        self.assertEquals(expected, str(report))

    def test_nested_section(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        expected = json.dumps({"section": {}})

        self.assertEquals(expected, str(report))

    def test_multiple_sections(self):
        report = Report()
        section = Section(name="section")
        report.add(section)

        section2 = Section(name="section2")
        report.add(section2)

        expected = json.dumps({"section": {},
                               "section2": {},})

        self.assertEquals(expected, str(report))


    def test_deeply_nested(self):
        report = Report()
        section = Section(name="section")
        command = Command(name="a command", return_code=0, href="does/not/matter")

        section.add(command)
        report.add(section)

        expected = json.dumps({"section": {"commands": [{"name": "a command",
                                                         "return_code": 0,
                                                         "href": "does/not/matter"}]}})

        self.assertEquals(expected, str(report))


class TestPlainReport(unittest.TestCase):

    def setUp(self):
        self.report = Report()
        self.section = Section(name="plugin")
        self.div = PlainTextReport.DIVIDER

    def test_basic(self):
        self.assertEquals("", str(PlainTextReport(self.report)))

    def test_one_section(self):
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div, str(PlainTextReport(self.report)))

    def test_two_sections(self):
        section1 = Section(name="first")
        section2 = Section(name="second")
        self.report.add(section1, section2)

        self.assertEquals("first\n" + self.div + "\nsecond\n" + self.div, str(PlainTextReport(self.report)))

    def test_command(self):
        cmd = Command(name="ls -al /foo/bar/baz",
                      return_code=0,
                      href="sos_commands/plugin/ls_-al_foo.bar.baz")
        self.section.add(cmd)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  commands executed:\n  * ls -al /foo/bar/baz",
                str(PlainTextReport(self.report)))

    def test_copied_file(self):
        cf = CopiedFile(name="/etc/hosts", href="etc/hosts")
        self.section.add(cf)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  files copied:\n  * /etc/hosts",
                str(PlainTextReport(self.report)))

    def test_created_file(self):
        crf = CreatedFile(name="sample.txt")
        self.section.add(crf)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  files created:\n  * sample.txt",
                str(PlainTextReport(self.report)))

    def test_alert(self):
        alrt = Alert("this is an alert")
        self.section.add(alrt)
        self.report.add(self.section)

        self.assertEquals("plugin\n" + self.div + "\n-  alerts:\n  ! this is an alert",
                str(PlainTextReport(self.report)))

if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = sosreport_pexpect
#!/usr/bin/env python

import unittest
import pexpect

from re import search, escape
from os import kill
from signal import SIGINT

class PexpectTest(unittest.TestCase):
    def test_plugins_install(self):
        sos = pexpect.spawn('/usr/sbin/sosreport -l')
        try:
            sos.expect('plugin.*does not install, skipping')
        except pexpect.EOF:
            pass
        else:
            self.fail("a plugin does not install or sosreport is too slow")
        kill(sos.pid, SIGINT)

    def test_batchmode_removes_questions(self):
        sos = pexpect.spawn('/usr/sbin/sosreport --batch')
        grp = sos.expect('send this file to your support representative.', 15)
        self.assertEquals(grp, 0)
        kill(sos.pid, SIGINT)

if __name__ == '__main__':
    unittest.main()

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = test_exe
#!/usr/bin/python
print "executed"

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = utilities_tests
import os.path
import unittest

# PYCOMPAT
import six
from six import StringIO

from sos.utilities import grep, get_hash_name, is_executable, sos_get_command_output, find, tail, shell_out
import sos

TEST_DIR = os.path.dirname(__file__)

class GrepTest(unittest.TestCase):

    def test_file_obj(self):
        test_s = "\n".join(['this is only a test', 'there are only two lines'])
        test_fo = StringIO(test_s)
        matches = grep(".*test$", test_fo)
        self.assertEquals(matches, ['this is only a test\n'])

    def test_real_file(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"))
        self.assertEquals(matches, ['import unittest\n'])

    def test_open_file(self):
        matches = grep(".*unittest$", open(__file__.replace(".pyc", ".py")))
        self.assertEquals(matches, ['import unittest\n'])

    def test_grep_multiple_files(self):
        matches = grep(".*unittest$", __file__.replace(".pyc", ".py"), "does_not_exist.txt")
        self.assertEquals(matches, ['import unittest\n'])


class TailTest(unittest.TestCase):

    def test_tail(self):
        t = tail("tests/tail_test.txt", 10)
        self.assertEquals(t, six.b("last line\n"))

    def test_tail_too_many(self):
        t = tail("tests/tail_test.txt", 200)
        expected = open("tests/tail_test.txt", "r").read()
        self.assertEquals(t, six.b(expected))


class ExecutableTest(unittest.TestCase):

    def test_nonexe_file(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        self.assertFalse(is_executable(path))

    def test_exe_file(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        self.assertTrue(is_executable(path))

    def test_exe_file_abs_path(self):
        self.assertTrue(is_executable("/usr/bin/timeout"))

    def test_output(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        result = sos_get_command_output(path)
        self.assertEquals(result['status'], 0)
        self.assertEquals(result['output'], "executed\n")

    def test_output_non_exe(self):
        path = os.path.join(TEST_DIR, 'utility_tests.py')
        result = sos_get_command_output(path)
        self.assertEquals(result['status'], 127)
        self.assertEquals(result['output'], "")

    def test_shell_out(self):
        path = os.path.join(TEST_DIR, 'test_exe.py')
        self.assertEquals("executed\n", shell_out(path))


class FindTest(unittest.TestCase):

    def test_find_leaf(self):
        leaves = find("leaf", TEST_DIR)
        self.assertTrue(any(name.endswith("leaf") for name in leaves))

    def test_too_shallow(self):
        leaves = find("leaf", TEST_DIR, max_depth=1)
        self.assertFalse(any(name.endswith("leaf") for name in leaves))

    def test_not_in_pattern(self):
        leaves = find("leaf", TEST_DIR, path_pattern="tests/path")
        self.assertFalse(any(name.endswith("leaf") for name in leaves))

# vim: et ts=4 sw=4

########NEW FILE########
__FILENAME__ = __run__
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
from sos.sosreport import main
import sys

main(sys.argv[1:])

# vim: et ts=4 sw=4

########NEW FILE########
