__FILENAME__ = compat
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
# Copyright (C) 2011 Victor Stinner
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import codecs
import os
import subprocess
import sys


PY3 = sys.version_info[0] >= 3
FSENC = sys.getfilesystemencoding()


# CFFI 0.4 reimplements Python 2 buffers on Python 3
if PY3 and False:
    def buffer_to_bytes(buf):
        return buf.tobytes()
else:
    def buffer_to_bytes(buf):
        return buf[:]


if PY3:
    _unichr = chr
else:
    _unichr = unichr


try:
    codecs.lookup_error('surrogateescape')
except LookupError:
    def my_se(exc):
        """
        Pure Python implementation of PEP 383: the "surrogateescape" error
        handler of Python 3.1.

        https://bitbucket.org/haypo/misc/src/tip/python/surrogateescape.py
        """
        if isinstance(exc, UnicodeDecodeError):
            decoded = []
            for ch in exc.object[exc.start:exc.end]:
                if PY3:
                    code = ch
                else:
                    code = ord(ch)
                if 0x80 <= code <= 0xFF:
                    decoded.append(_unichr(0xDC00 + code))
                elif code <= 0x7F:
                    decoded.append(_unichr(code))
                else:
                    print("RAISE!")
                    raise exc
            decoded = str().join(decoded)
            return (decoded, exc.end)
        else:
            print(exc.args)
            ch = exc.object[exc.start:exc.end]
            code = ord(ch)
            if not 0xDC80 <= code <= 0xDCFF:
                print("RAISE!")
                raise exc
            print(exc.start)
            byte = _unichr(code - 0xDC00)
            print(repr(byte))
            return (byte, exc.end)

    codecs.register_error('surrogateescape', my_se)


if PY3:
    from os import fsdecode
else:
    def fsdecode(filename):
        assert isinstance(filename, str)
        return filename.decode(FSENC, 'surrogateescape')


if not hasattr(os, 'O_CLOEXEC'):
    # Monkey-patching.
    os.O_CLOEXEC = 524288


if not hasattr(subprocess, 'check_output'):
    # Monkey-patching. That way lies madness.

    def _check_output(*popenargs, **kwargs):
        """Run command with arguments and return its output as a byte string"""

        process = subprocess.Popen(
            stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            error = subprocess.CalledProcessError(retcode, cmd)
            error.output = output
            raise error
        return output
    subprocess.check_output = _check_output


########NEW FILE########
__FILENAME__ = datetime
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
import datetime

ZERO = datetime.timedelta(0)


class Utc(datetime.tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return ZERO

UTC = Utc()


def system_now():
    # datetime.utcnow is broken
    return datetime.datetime.now(tz=UTC)


########NEW FILE########
__FILENAME__ = dedup
# vim: set fileencoding=utf-8 sw=4 ts=4 et :

# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import collections
import errno
import glob
import os
import re
import stat

from .platform.btrfs import clone_data, defragment as btrfs_defragment
from .platform.chattr import editflags, FS_IMMUTABLE_FL
from .platform.futimens import fstat_ns, futimens


BUFSIZE = 8192


class FilesDifferError(ValueError):
    pass


class FilesInUseError(RuntimeError):
    def describe(self, ofile):
        for (fi, users) in self.args[1].iteritems():
            ofile.write('File %s is in use\n' % fi)
            for use_info in users:
                ofile.write('  used as %r\n' % (use_info,))


ProcUseInfo = collections.namedtuple(
    'ProcUseInfo', 'proc_path is_readable is_writable')


def proc_use_info(proc_path):
    try:
        mode = os.lstat(proc_path).st_mode
    except OSError as e:
        if e.errno == errno.ENOENT:
            return
        raise
    else:
        return ProcUseInfo(
            proc_path=proc_path,
            is_readable=bool(mode & stat.S_IRUSR),
            is_writable=bool(mode & stat.S_IWUSR))


def cmp_fds(fd1, fd2):
    # Python 3 can take closefd=False instead of a duplicated fd.
    fi1 = os.fdopen(os.dup(fd1), 'rb')
    fi2 = os.fdopen(os.dup(fd2), 'rb')
    return cmp_files(fi1, fi2)


def cmp_files(fi1, fi2):
    fi1.seek(0)
    fi2.seek(0)
    while True:
        b1 = fi1.read(BUFSIZE)
        b2 = fi2.read(BUFSIZE)
        if b1 != b2:
            return False
        if not b1:
            return True


def dedup_same(source, dests, defragment=False):
    if defragment:
        source_fd = os.open(source, os.O_RDWR)
    else:
        source_fd = os.open(source, os.O_RDONLY)
    dest_fds = [os.open(dname, os.O_RDWR) for dname in dests]
    fds = [source_fd] + dest_fds
    fd_names = dict(zip(fds, [source] + dests))

    with ImmutableFDs(fds) as immutability:
        if immutability.fds_in_write_use:
            raise FilesInUseError(
                'Some of the files to deduplicate '
                'are open for writing elsewhere',
                dict(
                    (fd_names[fd], tuple(immutability.write_use_info(fd)))
                    for fd in immutability.fds_in_write_use))

        if defragment:
            btrfs_defragment(source_fd)
        for fd in dest_fds:
            if not cmp_fds(source_fd, fd):
                raise FilesDifferError(fd_names[source_fd], fd_names[fd])
            clone_data(dest=fd, src=source_fd, check_first=not defragment)


PROC_PATH_RE = re.compile(r'^/proc/(\d+)/fd/(\d+)$')


def find_inodes_in_write_use(fds):
    for (fd, use_info) in find_inodes_in_use(fds):
        if use_info.is_writable:
            yield (fd, use_info)


def find_inodes_in_use(fds):
    """
    Find which of these inodes are in use, and give their open modes.

    Does not count the passed fds as an use of the inode they point to,
    but if the current process has the same inodes open with different
    file descriptors these will be listed.

    Looks at /proc/*/fd and /proc/*/map_files (Linux 3.3).
    Conceivably there are other uses we're missing, to be foolproof
    will require support in btrfs itself; a share-same-range ioctl
    would work well.
    """

    self_pid = os.getpid()
    id_fd_assoc = collections.defaultdict(list)

    for fd in fds:
        st = os.fstat(fd)
        id_fd_assoc[(st.st_dev, st.st_ino)].append(fd)

    def st_id_candidates(it):
        # map proc paths to stat identifiers (devno and ino)
        for proc_path in it:
            try:
                st = os.stat(proc_path)
            except OSError as e:
                # glob opens directories during matching,
                # and other processes might close their fds in the meantime.
                # This isn't a problem for the immutable-locked use case.
                if e.errno == errno.ENOENT:
                    continue
                raise

            st_id = (st.st_dev, st.st_ino)
            if st_id not in id_fd_assoc:
                continue

            yield proc_path, st_id

    for proc_path, st_id in st_id_candidates(glob.glob('/proc/[1-9]*/fd/*')):
        other_pid, other_fd = map(
            int, PROC_PATH_RE.match(proc_path).groups())
        original_fds = id_fd_assoc[st_id]
        if other_pid == self_pid:
            if other_fd in original_fds:
                continue

        use_info = proc_use_info(proc_path)
        if not use_info:
            continue

        for fd in original_fds:
            yield (fd, use_info)

    # Requires Linux 3.3
    for proc_path, st_id in st_id_candidates(
        glob.glob('/proc/[1-9]*/map_files/*')
    ):
        use_info = proc_use_info(proc_path)
        if not use_info:
            continue

        original_fds = id_fd_assoc[st_id]
        for fd in original_fds:
            yield (fd, use_info)


RestoreInfo = collections.namedtuple(
    'RestoreInfo', ('fd', 'immutable', 'atime', 'mtime'))


class ImmutableFDs(object):
    """A context manager to mark a set of fds immutable.

    Actually works at the inode level, fds are just to make sure
    inodes can be referenced unambiguously.

    This also restores atime and mtime when leaving.
    """

    # Alternatives: mandatory locking.
    # Needs -o remount,mand + a metadata update + the same scan
    # for outstanding fds (although the race window is smaller).
    # The only real advantage is portability to more filesystems.
    # Since mandatory locking is a mount option, chances are
    # it is scoped to a mount namespace, which would complicate
    # attempts to enforce it with a remount.

    def __init__(self, fds):
        self.__fds = fds
        self.__revert_list = []
        self.__in_use = None
        self.__writable_fds = None

    def __enter__(self):
        for fd in self.__fds:
            # Prevents anyone from creating write-mode file descriptors,
            # but the ones that already exist remain valid.
            was_immutable = editflags(fd, add_flags=FS_IMMUTABLE_FL)
            # editflags doesn't change atime or mtime;
            # measure after locking then.
            atime, mtime = fstat_ns(fd)
            self.__revert_list.append(
                RestoreInfo(fd, was_immutable, atime, mtime))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for (fd, immutable, atime, mtime) in reversed(self.__revert_list):
            if not immutable:
                editflags(fd, remove_flags=FS_IMMUTABLE_FL)
            # XXX Someone might modify the file between editflags
            # and futimens; oh well.
            # Needs kernel changes either way, either a dedup ioctl
            # or mandatory locking that doesn't touch file metadata.
            futimens(fd, (atime, mtime))

    def __require_use_info(self):
        # We only track write use, other uses can appear after the /proc scan
        if self.__in_use is None:
            self.__in_use = collections.defaultdict(list)
            for (fd, use_info) in find_inodes_in_write_use(self.__fds):
                self.__in_use[fd].append(use_info)
            self.__writable_fds = frozenset(self.__in_use.keys())

    def write_use_info(self, fd):
        self.__require_use_info()
        # A quick check to prevent unnecessary list instanciation
        if fd in self.__in_use:
            return tuple(self.__in_use[fd])
        else:
            return tuple()

    @property
    def fds_in_write_use(self):
        self.__require_use_info()
        return self.__writable_fds


########NEW FILE########
__FILENAME__ = filesystem
# vim: set fileencoding=utf-8 sw=4 ts=4 et :
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import errno
import os
import re
import subprocess
import sys
import tempfile

from collections import namedtuple, defaultdict, OrderedDict, Counter
from uuid import UUID

from sqlalchemy.util import memoized_property
from sqlalchemy.orm.exc import NoResultFound

from .compat import fsdecode
from .platform.btrfs import (
    get_fsid, get_root_id, lookup_ino_path_one,
    read_root_tree, BTRFS_FIRST_FREE_OBJECTID)
from .platform.openat import openat
from .platform.unshare import unshare, CLONE_NEWNS

from .model import (
    BtrfsFilesystem, Volume, get_or_create, VolumePathHistory)


# 32MiB, initial scan takes about 12', might gain 15837689948,
# sqlite takes 256k
DEFAULT_SIZE_CUTOFF = 32 * 1024 ** 2
# about 12' again, might gain 25807974687
DEFAULT_SIZE_CUTOFF = 16 * 1024 ** 2
# 13'40" (36' with a backup job running in parallel), might gain 26929240347,
# sqlite takes 758k
DEFAULT_SIZE_CUTOFF = 8 * 1024 ** 2


DeviceInfo = namedtuple('DeviceInfo', 'label devices')
MountInfo = namedtuple('MountInfo', 'internal_path mpoint readonly private')

# A description, which may or may not be a path in the global filesystem
VolDesc = namedtuple('VolDesc', 'description is_fs_path')


class NotMounted(RuntimeError):
    pass


class NotPlugged(RuntimeError):
    pass


class BadDevice(RuntimeError):
    pass


class NotAVolume(RuntimeError):
    # Not a BtrFS volume
    # For example: not btrfs, or normal directory within a btrfs fs
    pass


def path_isprefix(prefix, path):
    # prefix and path must be absolute and normalised,
    # including symlink resolution.
    return prefix == '/' or path == prefix or path.startswith(prefix + '/')


class BtrfsFilesystem2(object):
    """Augments the db-persisted BtrfsFilesystem with some live metadata.
    """

    def __init__(self, whole_fs, impl, uuid):
        self._whole_fs = whole_fs
        self._impl = impl
        self._uuid = uuid
        self._root_info = None
        self._mpoints = None
        self._best_desc = {}
        self._priv_mpoint = None

        self._minfos = None

        try:
            # XXX Not in the db schema yet
            self._impl.label = self.label
        except NotPlugged:
            # XXX No point creating a live object in this case
            pass

    @property
    def impl(self):
        return self._impl

    @property
    def uuid(self):
        return self._uuid

    def iter_open_vols(self):
        for vol in self._whole_fs.iter_open_vols():
            if vol._fs == self:
                yield vol

    def clean_up_mpoints(self):
        if self._priv_mpoint is None:
            return
        for vol in self.iter_open_vols():
            if vol._fd is not None:
                vol.close()
        subprocess.check_call('umount -n -- '.split() + [self._priv_mpoint])
        os.rmdir(self._priv_mpoint)
        self._priv_mpoint = None

    def __str__(self):
        return self.desc

    @memoized_property
    def desc(self):
        try:
            if self.label and self._whole_fs._label_occurs[self.label] == 1:
                return '<%s>' % self.label
        except NotPlugged:
            # XXX Keep the label in the db?
            pass
        return '{%s}' % self.uuid

    def best_desc(self, root_id):
        if root_id not in self._best_desc:
            intpath = fsdecode(self.root_info[root_id].path)
            candidate_mis = [
                mi for mi in self.minfos
                if not mi.private and path_isprefix(mi.internal_path, intpath)]
            if candidate_mis:
                mi = max(
                    candidate_mis, key=lambda mi: len(mi.internal_path))
                base = mi.mpoint
                intbase = mi.internal_path
                is_fs_path = True
            else:
                base = self.desc
                intbase = '/'
                is_fs_path = False
            self._best_desc[root_id] = VolDesc(
                os.path.normpath(
                    os.path.join(base, os.path.relpath(intpath, intbase))),
                is_fs_path)
        return self._best_desc[root_id]

    def ensure_private_mpoint(self):
        # Create a private mountpoint with:
        # noatime,noexec,nodev
        # subvol=/
        if self._priv_mpoint is not None:
            return

        self.require_plugged()
        self._whole_fs.ensure_unshared()
        pm = tempfile.mkdtemp(suffix='.privmnt')
        subprocess.check_call(
            'mount -t btrfs -o subvol=/,noatime,noexec,nodev -nU'.split()
            + [str(self.uuid), pm])
        self._priv_mpoint = pm
        self.add_minfo(MountInfo(
            internal_path='/', mpoint=pm, readonly=False, private=True))

    def load_vol_by_root_id(self, root_id):
        self.ensure_private_mpoint()
        ri = self.root_info[root_id]
        return self._whole_fs._get_vol_by_path(
            self._priv_mpoint + ri.path, desc=None)

    @memoized_property
    def root_info(self):
        if not self.minfos:
            raise NotMounted
        fd = os.open(self.minfos[0].mpoint, os.O_DIRECTORY)
        try:
            return read_root_tree(fd)
        finally:
            os.close(fd)

    @memoized_property
    def device_info(self):
        try:
            return self._whole_fs.device_info[self.uuid]
        except KeyError:
            raise NotPlugged(self)

    def require_plugged(self):
        if self.uuid not in self._whole_fs.device_info:
            raise NotPlugged(self)

    @memoized_property
    def label(self):
        return self.device_info.label

    @property
    def minfos(self):
        # Not memoised, some may be added later
        if self._minfos is None:
            mps = []
            try:
                for dev in self.device_info.devices:
                    dev_canonical = os.path.realpath(dev)
                    if dev_canonical in self._whole_fs.mpoints_by_dev:
                        mps.extend(self._whole_fs.mpoints_by_dev[dev_canonical])
            except NotPlugged:
                pass
            self._minfos = mps
        return tuple(self._minfos)

    def add_minfo(self, mi):
        if mi not in self.minfos:
            self._minfos.append(mi)

    def _iter_subvols(self, start_root_ids):
        child_id_map = defaultdict(list)

        for root_id, ri in self.root_info.iteritems():
            if ri.parent_root_id is not None:
                child_id_map[ri.parent_root_id].append(root_id)

        def _iter_children(root_id, top_level):
            yield (root_id, self.root_info[root_id], top_level)
            for child_id in child_id_map[root_id]:
                for item in _iter_children(child_id, False):
                    yield item

        for root_id in start_root_ids:
            for item in _iter_children(root_id, True):
                yield item

    def _load_visible_vols(self, start_paths, nest_desc):
        # Use dicts, there may be repetitions under multiple mountpoints
        loaded = OrderedDict()

        start_vols = OrderedDict(
            (vol.root_id, vol)
            for vol in (
                self._whole_fs._get_vol_by_path(start_fspath, desc=None)
                for start_fspath in start_paths))

        for (root_id, ri, top_level) in self._iter_subvols(start_vols):
            if top_level:
                start_vol = start_vols[root_id]
                if start_vol not in loaded:
                    loaded[start_vol] = True
                start_desc = start_vol.desc
                start_intpath = ri.path
                start_fd = start_vol.fd
                # relpath is more predictable with absolute paths;
                # otherwise it relies on getcwd (via abspath)
                assert os.path.isabs(start_intpath)
            else:
                relpath = os.path.relpath(ri.path, start_intpath)
                if nest_desc:
                    desc = VolDesc(
                        os.path.join(start_desc.description, relpath),
                        start_desc.is_fs_path)
                else:
                    desc = None
                vol = self._whole_fs._get_vol_by_relpath(
                    start_fd, relpath, desc=desc)
                if vol not in loaded:
                    loaded[vol] = True
        return loaded.keys(), start_vols.values()


def impl_property(name):
    def getter(inst):
        return getattr(inst._impl, name)

    def setter(inst, val):
        setattr(inst._impl, name, val)

    return property(getter, setter)


class Volume2(object):
    def __init__(self, whole_fs, fs, impl, desc, fd):
        self._whole_fs = whole_fs
        self._fs = fs
        self._impl = impl
        self._desc = desc
        self._fd = fd

        self.st_dev = os.fstat(self._fd).st_dev

        self._impl.live = self

    last_tracked_generation = impl_property('last_tracked_generation')
    last_tracked_size_cutoff = impl_property('last_tracked_size_cutoff')
    size_cutoff = impl_property('size_cutoff')

    def __str__(self):
        return self.desc.description

    @property
    def impl(self):
        return self._impl

    @property
    def root_info(self):
        return self._fs.root_info[self._impl.root_id]

    @property
    def root_id(self):
        return self._impl.root_id

    @property
    def desc(self):
        return self._desc

    @property
    def fd(self):
        return self._fd

    @property
    def fs(self):
        return self._fs

    @classmethod
    def vol_id_of_fd(cls, fd):
        try:
            return get_fsid(fd), get_root_id(fd)
        except IOError as err:
            if err.errno == errno.ENOTTY:
                raise NotAVolume(fd)
            raise

    def close(self):
        os.close(self._fd)
        self._fd = None

    def lookup_one_path(self, inode):
        return lookup_ino_path_one(self.fd, inode.ino)

    def describe_path(self, relpath):
        return os.path.join(self.desc.description, relpath)


class WholeFS(object):
    """A singleton representing the local filesystem"""

    def __init__(self, sess, size_cutoff=None):
        # Public functions that rely on sess:
        # get_fs, iter_fs, load_all_writable_vols, load_vols,
        # Requiring root:
        # load_all_writable_vols, load_vols.
        self.sess = sess
        self._unshared = False
        self._size_cutoff = size_cutoff
        self._fs_map = {}
        # keyed on fs_uuid, vol.root_id
        self._vol_map = {}
        self._label_occurs = None

    def get_fs_existing(self, uuid):
        assert isinstance(uuid, UUID)
        if uuid not in self._fs_map:
            try:
                db_fs = self.sess.query(
                    BtrfsFilesystem).filter_by(uuid=str(uuid)).one()
            except NoResultFound:
                raise KeyError(uuid)
            fs = BtrfsFilesystem2(self, db_fs, uuid)
            self._fs_map[uuid] = fs
        return self._fs_map[uuid]

    def get_fs(self, uuid):
        assert isinstance(uuid, UUID)
        if uuid not in self._fs_map:
            if uuid in self.device_info:
                db_fs, fs_created = get_or_create(
                    self.sess, BtrfsFilesystem, uuid=str(uuid))
            else:
                # Don't create a db object without a live fs backing it
                try:
                    db_fs = self.sess.query(
                        BtrfsFilesystem).filter_by(uuid=str(uuid)).one()
                except NoResultFound:
                    raise NotPlugged(uuid)
            fs = BtrfsFilesystem2(self, db_fs, uuid)
            self._fs_map[uuid] = fs
        return self._fs_map[uuid]

    def iter_fs(self):
        seen_fs_ids = []
        for (uuid, di) in self.device_info.iteritems():
            fs = self.get_fs(uuid)
            seen_fs_ids.append(fs._impl.id)
            yield fs, di

        extra_fs_query = self.sess.query(BtrfsFilesystem.uuid)
        if seen_fs_ids:
            # Conditional because we get a performance SAWarning otherwise
            extra_fs_query = extra_fs_query.filter(
                ~ BtrfsFilesystem.id.in_(seen_fs_ids))
        for uuid, in extra_fs_query:
            yield self.get_fs(UUID(hex=uuid)), None

    def iter_open_vols(self):
        return self._vol_map.itervalues()

    def _get_vol_by_path(self, volpath, desc):
        volpath = os.path.normpath(volpath)
        fd = os.open(volpath, os.O_DIRECTORY)
        return self._get_vol(fd, desc)

    def _get_vol_by_relpath(self, base_fd, relpath, desc):
        fd = openat(base_fd, relpath, os.O_DIRECTORY)
        return self._get_vol(fd, desc)

    def _get_vol(self, fd, desc):
        if not is_subvolume(fd):
            raise NotAVolume(fd, desc)
        vol_id = Volume2.vol_id_of_fd(fd)

        # If a volume was given multiple times on the command line,
        # keep the first name and fd for it.
        if vol_id in self._vol_map:
            os.close(fd)
            return self._vol_map[vol_id]

        fs_uuid, root_id = vol_id

        fs = self.get_fs(uuid=fs_uuid)
        db_vol, db_vol_created = get_or_create(
            self.sess, Volume, fs=fs._impl, root_id=root_id)

        if self._size_cutoff is not None:
            db_vol.size_cutoff = self._size_cutoff
        elif db_vol_created:
            db_vol.size_cutoff = DEFAULT_SIZE_CUTOFF

        if desc is None:
            desc = fs.best_desc(root_id)

        vol = Volume2(self, fs=fs, impl=db_vol, desc=desc, fd=fd)

        if desc.is_fs_path:
            path_history, ph_created = get_or_create(
                self.sess, VolumePathHistory,
                vol=db_vol, path=desc.description)

        self._vol_map[vol_id] = vol
        return vol

    @memoized_property
    def mpoints_by_dev(self):
        assert not self._unshared
        mbd = defaultdict(list)
        with open('/proc/self/mountinfo') as mounts:
            for line in mounts:
                items = line.split()
                idx = items.index('-')
                fs_type = items[idx + 1]
                opts1 = items[5].split(',')
                opts2 = items[idx + 3].split(',')
                readonly = 'ro' in opts1 + opts2
                if fs_type != 'btrfs':
                    continue
                intpath = items[3]
                mpoint = items[4]
                dev = os.path.realpath(items[idx + 2])
                mbd[dev].append(MountInfo(intpath, mpoint, readonly, False))
        return dict(mbd)

    @memoized_property
    def device_info(self):
        di = {}
        lbls = Counter()
        cmd = 'blkid -s LABEL -s UUID -t TYPE=btrfs'.split()
        subp = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        for line in subp.stdout:
            dev, label, uuid = BLKID_RE.match(line).groups()
            uuid = UUID(hex=uuid.decode('ascii'))
            dev = fsdecode(dev)
            if label is not None:
                try:
                    label = label.decode('ascii')
                except UnicodeDecodeError:
                    # Don't try to guess.
                    pass
            if uuid in di:
                # btrfs raid
                assert di[uuid].label == label
                di[uuid].devices.append(dev)
            else:
                lbls[label] += 1
                di[uuid] = DeviceInfo(label, [dev])
        rc = subp.wait()
        # 2 means there is no btrfs filesystem
        if rc not in (0, 2):
            raise subprocess.CalledProcessError(rc, cmd)
        self._label_occurs = dict(lbls)
        return di

    def ensure_unshared(self):
        if not self._unshared:
            # Make sure we read mountpoints before creating ours,
            # so that ours won't appear on the list.
            self.mpoints_by_dev
            unshare(CLONE_NEWNS)
            self._unshared = True

    def clean_up_mpoints(self):
        if not self._unshared:
            return
        for fs, di in self.iter_fs():
            fs.clean_up_mpoints()

    def close(self):
        # For context managers
        self.clean_up_mpoints()

    def load_vols_for_device(self, devpath, tt):
        for uuid, di in self.device_info.iteritems():
            if any(os.path.samefile(dp, devpath) for dp in di.devices):
                fs = self.get_fs(uuid)
                return self.load_vols_for_fs(fs, tt)
        raise BadDevice('No Btrfs filesystem detected by blkid', devpath)

    def load_vols_for_fs(self, fs, tt):
        # Check that the filesystem is plugged
        fs.device_info

        loaded = []
        fs.ensure_private_mpoint()
        lo, sta = fs._load_visible_vols([fs._priv_mpoint], nest_desc=False)
        assert self._vol_map
        frozen_skipped = 0
        for vol in lo:
            if vol.root_info.is_frozen:
                vol.close()
                frozen_skipped += 1
            else:
                loaded.append(vol)
        if frozen_skipped:
            tt.notify(
                'Skipped %d frozen volumes in filesystem %s' % (
                    frozen_skipped, fs))
        return loaded

    def load_all_writable_vols(self, tt):
        # All non-frozen volumes that are on a
        # filesystem that has a non-ro mountpoint.
        loaded = []
        for (uuid, di) in self.device_info.iteritems():
            fs = self.get_fs(uuid)
            try:
                fs.root_info
            except NotMounted:
                tt.notify('Skipping filesystem %s, not mounted' % fs)
                continue
            if all(mi.readonly for mi in fs.minfos):
                tt.notify('Skipping filesystem %s, not mounted rw' % fs)
                continue
            loaded.extend(self.load_vols_for_fs(fs, tt))
        return loaded

    def load_vols(self, volpaths, tt, recurse):
        # The volume at volpath, plus all its visible non-frozen descendants
        # XXX Some of these may fail if other filesystems
        # are mounted on top of them.
        loaded = OrderedDict()
        for volpath in volpaths:
            vol = self._get_vol_by_path(volpath, desc=VolDesc(volpath, True))
            if recurse:
                if vol.root_info.path != b'/':
                    tt.notify(
                        '%s isn\'t the root volume, '
                        'use the filesystem uuid for maximum efficiency.' % vol)
                lo, sta = vol._fs._load_visible_vols([volpath], nest_desc=True)
                skipped = 0
                for vol in lo:
                    if vol in loaded:
                        continue
                    if vol.root_info.is_frozen and vol not in sta:
                        vol.close()
                        skipped += 1
                    else:
                        loaded[vol] = True
                if skipped:
                    tt.notify(
                        'Skipped %d frozen volumes in filesystem %s' % (
                            skipped, vol.fs))
            else:
                if vol not in loaded:
                    loaded[vol] = True
        return loaded.keys()


BLKID_RE = re.compile(
    br'^(?P<dev>/dev/.*):'
    br'(?:\s+LABEL="(?P<label>[^"]*)"|\s+UUID="(?P<uuid>[^"]*)")+\s*$')


def is_subvolume(btrfs_mountpoint_fd):
    st = os.fstat(btrfs_mountpoint_fd)
    return st.st_ino == BTRFS_FIRST_FREE_OBJECTID


def show_fs(fs, print_indented, show_deleted):
    vols_by_id = dict((db_vol.root_id, db_vol) for db_vol in fs._impl.volumes)
    root_ids = set(vols_by_id.keys())
    has_ri = False
    deleted_skipped = 0

    try:
        root_ids.update(fs.root_info.keys())
    except IOError as err:
        if err.errno != errno.EPERM:
            raise
    except NotMounted:
        pass
    else:
        has_ri = True

    for root_id in sorted(root_ids):
        flags = ''
        if has_ri:
            if root_id not in fs.root_info:
                if not show_deleted:
                    deleted_skipped += 1
                    continue
                # The filesystem is available (we could scan the root tree),
                # so the volume must have been destroyed.
                flags = ' (deleted)'
            elif fs.root_info[root_id].is_frozen:
                flags = ' (frozen)'

        print_indented('Volume %d%s' % (root_id, flags), 0)
        try:
            vol = vols_by_id[root_id]
        except KeyError:
            # We'll only use vol in the 'else' no-exception branch
            pass
        else:
            if vol.inode_count:
                print_indented(
                    'As of generation %d, '
                    'tracking %d inodes of size at least %d'
                    % (vol.last_tracked_generation, vol.inode_count,
                       vol.size_cutoff), 1)

        if has_ri and root_id in fs.root_info:
            ri = fs.root_info[root_id]
            desc = fs.best_desc(root_id)
            if desc.is_fs_path:
                print_indented('Accessible at %s' % desc.description, 1)
            else:
                print_indented('Internal path %s' % ri.path, 1)
        else:
            # We can use vol, since keys come from one or the other
            print_indented(
                'Last seen at %s' % vol.last_known_mountpoint, 1)

    if deleted_skipped:
        print_indented('Skipped %d deleted volumes' % deleted_skipped, 0)


def show_vols(whole_fs, fsuuid_or_device, show_deleted):
    initial_indent = indent = '  '
    uuid_filter = device_filter = None
    found = True

    if fsuuid_or_device is not None:
        found = False
        if fsuuid_or_device[0] == '/':
            device_filter = fsuuid_or_device
            # TODO: use stat, if it's a dir,
            # call show_vol extracted from show_fs
        else:
            uuid_filter = UUID(hex=fsuuid_or_device)

    def print_indented(line, depth):
        sys.stdout.write(initial_indent + depth * indent + line + '\n')

    # Without root, we are mostly limited to what's stored in the db.
    # Can't link volume ids to mountpoints, can't list subvolumes.
    # There's just blkid sharing blkid.tab, and the kernel with mountinfo.
    # Print a warning?
    for (fs, di) in whole_fs.iter_fs():
        if uuid_filter:
            if fs.uuid == uuid_filter:
                found = True
            else:
                continue
        if di is not None:
            if device_filter:
                if device_filter in di.devices:
                    found = True
                else:
                    continue
            sys.stdout.write('Label: %s UUID: %s\n' % (di.label, fs.uuid))
            for dev in di.devices:
                print_indented('Device: %s' % (dev, ), 0)
            show_fs(fs, print_indented, show_deleted)
        elif device_filter is None:
            sys.stdout.write(
                'UUID: %s\n  <no device available>\n' % (fs.uuid,))
            show_fs(fs, print_indented, show_deleted)

    if not found:
        sys.stderr.write(
            'Filesystem at %s was not found\n' % fsuuid_or_device)
    whole_fs.sess.commit()


########NEW FILE########
__FILENAME__ = hashing
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from zlib import adler32

from .platform.fiemap import fiemap


def mini_hash_from_file(inode, rfile):
    # A very cheap, very partial hash for quick disambiguation
    # Won't help with things like zeroed or sparse files.
    # The mini_hash for those is 0x10000001
    rfile.seek(int(inode.size * .3))
    # bitops to make unsigned, for better readability
    return adler32(rfile.read(4096)) & 0xffffffff


def fiemap_hash_from_file(rfile):
    extents = tuple(fiemap(rfile.fileno()))
    return hash(extents)


########NEW FILE########
__FILENAME__ = main
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

# This file is a workaround for Python2.6
# Also has workarounds for -mtrace

import sys
try:
    # For -mtrace
    sys.path.remove('bedup')
except ValueError:
    pass

# -mtrace can't use relative imports either
from bedup.__main__ import script_main

if __name__ == '__main__':
    script_main()


########NEW FILE########
__FILENAME__ = migrations
# vim: set fileencoding=utf-8 sw=4 ts=4 et :

# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import MetaData

from .model import META


REV = 1


def upgrade_with_range(context, from_rev, to_rev):
    assert from_rev == to_rev
    op = Operations(context)
    #from IPython import embed; embed()


def upgrade_schema(engine):
    context = MigrationContext.configure(engine.connect())
    current_rev = context.get_current_revision()

    if current_rev is None:
        inspected_meta = MetaData()
        inspected_meta.reflect(bind=engine)
        if 'Inode' in inspected_meta.tables:
            inspected_rev = 1
            upgrade_with_range(context, inspected_rev, REV)
        else:
            META.create_all(engine)
    else:
        current_rev = int(current_rev)
        upgrade_with_range(context, current_rev, REV)
    context._update_current_rev(current_rev, REV)


########NEW FILE########
__FILENAME__ = model
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy.orm import relationship, column_property, backref as backref_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import select, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import (
    Boolean, Integer, Text, DateTime, TypeDecorator)
from sqlalchemy.schema import (
    Column, ForeignKey, UniqueConstraint, CheckConstraint)

from .datetime import UTC
from .hashing import mini_hash_from_file, fiemap_hash_from_file


def parent_entity(cattr):
    # This got renamed in 0.8, leaving no easy way to handle both versions.
    try:
        return cattr.parent
    except AttributeError:
        return cattr.parententity


def FK(cattr, primary_key=False, backref=None, nullable=False, cascade=False):
    # cascade=False will select the sqla default (save-update, merge)
    col, = cattr.property.columns
    if backref is None:
        assert cascade is False
    else:
        backref = backref_(backref, cascade=cascade)

    return (
        Column(
            col.type, ForeignKey(col),
            primary_key=primary_key,
            nullable=nullable),
        relationship(
            parent_entity(cattr), backref=backref))


class UTCDateTime(TypeDecorator):
    impl = DateTime

    def process_bind_param(self, value, engine):
        return value.astimezone(UTC)

    def process_result_value(self, value, engine):
        return value.replace(tzinfo=UTC)


# XXX I actually need create_or_update here
def get_or_create(sess, model, **kwargs):
    try:
        return sess.query(model).filter_by(**kwargs).one(), False
    except NoResultFound:
        instance = model(**kwargs)
        # XXX Some of the relationship attributes remain unset at this point
        sess.add(instance)
        return instance, True


class SuperBase(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__
Base = declarative_base(cls=SuperBase)


class BtrfsFilesystem(Base):
    id = Column(Integer, primary_key=True)
    uuid = Column(
        Text, CheckConstraint("uuid != ''"),
        unique=True, index=True, nullable=False)
    __tablename__ = 'Filesystem'
    __table_args__ = (
        dict(
            sqlite_autoincrement=True))


class Volume(Base):
    # SmallInteger might be preferrable here,
    # but would require reimplementing an autoincrement
    # sequence outside of sqlite
    id = Column(Integer, primary_key=True)
    fs_id, fs = FK(BtrfsFilesystem.id, backref='volumes')
    __table_args__ = (
        UniqueConstraint(
            'fs_id', 'root_id'),
        dict(
            sqlite_autoincrement=True))
    root_id = Column(Integer, nullable=False)
    last_tracked_generation = Column(Integer, nullable=False, default=0)
    last_tracked_size_cutoff = Column(Integer, nullable=True)
    size_cutoff = Column(Integer, nullable=False)


class VolumePathHistory(Base):
    id = Column(Integer, primary_key=True)
    vol_id, vol = FK(
        Volume.id, backref='path_history', cascade='all, delete-orphan')
    # Paths in the / filesystem.
    # For paths relative to the root volume, see read_root_tree
    path = Column(Text, index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'vol_id', 'path'),
        dict(
            sqlite_autoincrement=True))


Volume.last_known_mountpoint = column_property(
    select([VolumePathHistory.path])
        .where(
            VolumePathHistory.vol_id == Volume.id)
        .order_by(-VolumePathHistory.id)
        .label('last_known_mountpoint'),
    deferred=True)


class InodeProps(object):
    @declared_attr
    def fs_id(cls):
        return column_property(
            select([Volume.fs_id]).where(
                Volume.id == cls.vol_id).label('fs_id'), deferred=True)

    def mini_hash_from_file(self, rfile):
        self.mini_hash = mini_hash_from_file(self, rfile)

    def fiemap_hash_from_file(self, rfile):
        self.fiemap_hash = fiemap_hash_from_file(rfile)


class Inode(Base, InodeProps):
    vol_id, vol = FK(
        Volume.id, primary_key=True, backref='inodes',
        cascade='all, delete-orphan')
    # inode number
    ino = Column(Integer, primary_key=True)
    # We learn the size at the same time as the inode number,
    # and it's the first criterion we'll use, so not nullable
    size = Column(Integer, index=True, nullable=False)
    mini_hash = Column(Integer, index=True, nullable=True)
    # A digest of that file's FIEMAP extent info.
    fiemap_hash = Column(Integer, index=True, nullable=True)

    # has_updates gets set whenever this inode
    # appears in the volume scan, and reset whenever we do
    # a dedup pass.
    has_updates = Column(Boolean, index=True, nullable=False)

    def __repr__(self):
        return 'Inode(ino=%d, volume=%d)' % (self.ino, self.vol_id)


Volume.inode_count = column_property(
    select([func.count(Inode.ino)])
        .where(Inode.vol_id == Volume.id)
        .label('inode_count'),
    deferred=True)


# The logging classes don't have anything in common (no FKs)
# with the tracking classes. For example, inode numbers may
# be reused, and inodes can be removed from tracking in these
# cases. That would cause dangling references or delete cascades.
# We do allow FKs to volumes; those aren't meant to be removed.
class DedupEvent(Base):
    id = Column(Integer, primary_key=True)
    fs_id, fs = FK(
        BtrfsFilesystem.id,
        backref='dedup_events', cascade='all, delete-orphan')

    item_size = Column(Integer, index=True, nullable=False)
    created = Column(UTCDateTime, index=True, nullable=False)

    @hybrid_property
    def estimated_space_gain(self):
        return self.item_size * (self.inode_count - 1)

    __table_args__ = (
        dict(
            sqlite_autoincrement=True))


class DedupEventInode(Base):
    id = Column(Integer, primary_key=True)
    event_id, event = FK(
        DedupEvent.id, backref='inodes', cascade='all, delete-orphan')
    ino = Column(Integer, index=True, nullable=False)
    vol_id, vol = FK(
        Volume.id, backref='dedup_event_inodes', cascade='all, delete-orphan')

    __table_args__ = (
        dict(
            sqlite_autoincrement=True))

DedupEvent.inode_count = column_property(
    select([func.count(DedupEventInode.id)])
    .where(DedupEventInode.event_id == DedupEvent.id)
    .label('inode_count'))


META = Base.metadata


########NEW FILE########
__FILENAME__ = btrfs
# vim: set fileencoding=utf-8 sw=4 ts=4 et :

# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import cffi
import posixpath
import uuid
import sys

from ..compat import buffer_to_bytes, fsdecode
from .fiemap import same_extents
from . import cffi_support

from collections import namedtuple


ffi = cffi.FFI()

ffi.cdef("""
/* ioctl.h */

#define BTRFS_IOC_TREE_SEARCH ...
#define BTRFS_IOC_INO_PATHS ...
#define BTRFS_IOC_INO_LOOKUP ...
#define BTRFS_IOC_FS_INFO ...
#define BTRFS_IOC_CLONE ...
#define BTRFS_IOC_DEFRAG ...
#define BTRFS_IOC_SUBVOL_GETFLAGS ...
#define BTRFS_IOC_SUBVOL_SETFLAGS ...

#define BTRFS_FSID_SIZE ...
#define BTRFS_UUID_SIZE ...

struct btrfs_ioctl_search_key {
    /* The search root
    /* tree_id = 0 will use the subvolume from the ioctl fd */
    uint64_t tree_id;

    /* keys returned will be >= min and <= max */
    uint64_t min_objectid;
    uint64_t max_objectid;

    /* keys returned will be >= min and <= max */
    uint64_t min_offset;
    uint64_t max_offset;

    /* max and min transids to search for */
    uint64_t min_transid;
    uint64_t max_transid;

    /* keys returned will be >= min and <= max */
    uint32_t min_type;
    uint32_t max_type;

    /*
     * how many items did userland ask for, and how many are we
     * returning
     */
    uint32_t nr_items;

    ...;
};

struct btrfs_ioctl_search_header {
    uint64_t transid;
    uint64_t objectid;
    uint64_t offset;
    uint32_t type;
    uint32_t len;
};

struct btrfs_ioctl_search_args {
    /* search parameters and state */
    struct btrfs_ioctl_search_key key;
    /* found items */
    char buf[];
};

struct btrfs_data_container {
    uint32_t    bytes_left; /* out -- bytes not needed to deliver output */
    uint32_t    bytes_missing;  /* out -- additional bytes needed for result */
    uint32_t    elem_cnt;   /* out */
    uint32_t    elem_missed;    /* out */
    uint64_t    val[0];     /* out */
};

struct btrfs_ioctl_ino_path_args {
    uint64_t                inum;       /* in */
    uint64_t                size;       /* in */
    /* struct btrfs_data_container  *fspath;       out */
    uint64_t                fspath;     /* out */
    ...; // reserved/padding
};

struct btrfs_ioctl_fs_info_args {
    uint64_t max_id;                /* max device id; out */
    uint64_t num_devices;           /* out */
    uint8_t fsid[16];      /* BTRFS_FSID_SIZE == 16; out */
    ...; // reserved/padding
};

struct btrfs_ioctl_ino_lookup_args {
    uint64_t treeid;
    uint64_t objectid;

    // pads to 4k; don't use this ioctl for path lookup, it's kind of broken.
    // re-enabled, the alternative is buggy atm
    //char name[BTRFS_INO_LOOKUP_PATH_MAX];
    char name[4080];
    //...;
};


/* ctree.h */

#define BTRFS_EXTENT_DATA_KEY ...
#define BTRFS_INODE_REF_KEY ...
#define BTRFS_INODE_ITEM_KEY ...
#define BTRFS_DIR_ITEM_KEY ...
#define BTRFS_DIR_INDEX_KEY ...
#define BTRFS_ROOT_ITEM_KEY ...
#define BTRFS_ROOT_BACKREF_KEY ...

#define BTRFS_FIRST_FREE_OBJECTID ...
#define BTRFS_ROOT_TREE_OBJECTID ...
#define BTRFS_FS_TREE_OBJECTID ...

// A root_item flag
// Not to be confused with a similar ioctl flag with a different value
// XXX The kernel uses cpu_to_le64 to check this flag
#define BTRFS_ROOT_SUBVOL_RDONLY ...


struct btrfs_file_extent_item {
    /*
     * transaction id that created this extent
     */
    uint64_t generation;
    /*
     * max number of bytes to hold this extent in ram
     * when we split a compressed extent we can't know how big
     * each of the resulting pieces will be.  So, this is
     * an upper limit on the size of the extent in ram instead of
     * an exact limit.
     */
    uint64_t ram_bytes;

    /*
     * 32 bits for the various ways we might encode the data,
     * including compression and encryption.  If any of these
     * are set to something a given disk format doesn't understand
     * it is treated like an incompat flag for reading and writing,
     * but not for stat.
     */
    uint8_t compression;
    uint8_t encryption;
    uint16_t other_encoding; /* spare for later use */

    /* are we inline data or a real extent? */
    uint8_t type;

    /*
     * disk space consumed by the extent, checksum blocks are included
     * in these numbers
     */
    uint64_t disk_bytenr;
    uint64_t disk_num_bytes;
    /*
     * the logical offset in file blocks (no csums)
     * this extent record is for.  This allows a file extent to point
     * into the middle of an existing extent on disk, sharing it
     * between two snapshots (useful if some bytes in the middle of the
     * extent have changed
     */
    uint64_t offset;
    /*
     * the logical number of file blocks (no csums included)
     */
    uint64_t num_bytes;
    ...;
};

struct btrfs_timespec {
    uint64_t sec;
    uint32_t nsec;
    ...;
};

struct btrfs_inode_item {
    /* nfs style generation number */
    uint64_t generation;
    /* transid that last touched this inode */
    uint64_t transid;
    uint64_t size;
    uint64_t nbytes;
    uint64_t block_group;
    uint32_t nlink;
    uint32_t uid;
    uint32_t gid;
    uint32_t mode;
    uint64_t rdev;
    uint64_t flags;

    /* modification sequence number for NFS */
    uint64_t sequence;

    struct btrfs_timespec atime;
    struct btrfs_timespec ctime;
    struct btrfs_timespec mtime;
    struct btrfs_timespec otime;
    ...; // reserved/padding
};

struct btrfs_root_item {
// XXX CFFI and endianness: ???
    struct btrfs_inode_item inode;
    uint64_t generation;
    uint64_t root_dirid;
    uint64_t bytenr;
    uint64_t byte_limit;
    uint64_t bytes_used;
    uint64_t last_snapshot;
    uint64_t flags;
    uint32_t refs;
    struct btrfs_disk_key drop_progress;
    uint8_t drop_level;
    uint8_t level;

    /*
     * The following fields appear after subvol_uuids+subvol_times
     * were introduced.
     */

    /*
     * This generation number is used to test if the new fields are valid
     * and up to date while reading the root item. Everytime the root item
     * is written out, the "generation" field is copied into this field. If
     * anyone ever mounted the fs with an older kernel, we will have
     * mismatching generation values here and thus must invalidate the
     * new fields. See btrfs_update_root and btrfs_find_last_root for
     * details.
     * the offset of generation_v2 is also used as the start for the memset
     * when invalidating the fields.
     */
    uint64_t generation_v2;
    //uint8_t uuid[BTRFS_UUID_SIZE]; // BTRFS_UUID_SIZE == 16
    //uint8_t parent_uuid[BTRFS_UUID_SIZE];
    //uint8_t received_uuid[BTRFS_UUID_SIZE];
    uint64_t ctransid; /* updated when an inode changes */
    uint64_t otransid; /* trans when created */
    uint64_t stransid; /* trans when sent. non-zero for received subvol */
    uint64_t rtransid; /* trans when received. non-zero for received subvol */
    struct btrfs_timespec ctime;
    struct btrfs_timespec otime;
    struct btrfs_timespec stime;
    struct btrfs_timespec rtime;
    ...; // reserved and packing
};


struct btrfs_inode_ref {
    uint64_t index;
    uint16_t name_len;
    /* name goes here */
    ...;
};

/*
 * this is used for both forward and backward root refs
 */
struct btrfs_root_ref {
    uint64_t dirid;
    uint64_t sequence;
    uint16_t name_len;
    /* name goes here */
    ...;
};

struct btrfs_disk_key {
    uint64_t objectid;
    uint8_t type;
    uint64_t offset;
    ...;
};

struct btrfs_dir_item {
    struct btrfs_disk_key location;
    uint64_t transid;
    uint16_t data_len;
    uint16_t name_len;
    uint8_t type;
    ...;
};

uint64_t btrfs_stack_file_extent_generation(struct btrfs_file_extent_item *s);
uint64_t btrfs_stack_inode_generation(struct btrfs_inode_item *s);
uint64_t btrfs_stack_inode_size(struct btrfs_inode_item *s);
uint32_t btrfs_stack_inode_mode(struct btrfs_inode_item *s);
uint64_t btrfs_stack_inode_ref_name_len(struct btrfs_inode_ref *s);
uint16_t btrfs_stack_root_ref_name_len(struct btrfs_root_ref *s);
uint64_t btrfs_stack_root_ref_dirid(struct btrfs_root_ref *s);
uint16_t btrfs_stack_dir_name_len(struct btrfs_dir_item *s);
uint64_t btrfs_root_generation(struct btrfs_root_item *s);
""")


# Also accessible as ffi.verifier.load_library()
lib = cffi_support.verify(ffi, '''
    #include <btrfs/ioctl.h>
    #include <btrfs/ctree.h>
    ''',
    include_dirs=[cffi_support.BTRFS_INCLUDE_DIR])


BTRFS_FIRST_FREE_OBJECTID = lib.BTRFS_FIRST_FREE_OBJECTID

u64_max = ffi.cast('uint64_t', -1)

RootInfo = namedtuple('RootInfo', 'path parent_root_id is_frozen')


def name_of_inode_ref(ref):
    namelen = lib.btrfs_stack_inode_ref_name_len(ref)
    return ffi.string(ffi.cast('char*', ref + 1), namelen)


def name_of_root_ref(ref):
    namelen = lib.btrfs_stack_root_ref_name_len(ref)
    return ffi.string(ffi.cast('char*', ref + 1), namelen)


def name_of_dir_item(item):
    namelen = lib.btrfs_stack_dir_name_len(item)
    return ffi.string(ffi.cast('char*', item + 1), namelen)


def ioctl_pybug(fd, ioc, arg=0):
    # Private import
    import fcntl

    if isinstance(arg, int):
        return fcntl.ioctl(fd, ioc, arg)

    # Check for http://bugs.python.org/issue1520818
    # Also known as http://bugs.python.org/issue9758
    # Fixed in 2.7.1, 3.1.3, and 3.2, not backported to 2.6
    # which is now in maintenance mode.
    if len(arg) == 1024:
        raise ValueError(arg)

    return fcntl.ioctl(fd, ioc, arg, True)


def lookup_ino_paths(volume_fd, ino, alloc_extra=0):  # pragma: no cover
    raise OSError('kernel bugs')

    # This ioctl requires root
    args = ffi.new('struct btrfs_ioctl_ino_path_args*')

    assert alloc_extra >= 0
    # XXX We're getting some funky overflows here
    # inode-resolve -v 541144
    # NB: as of 3.6.1 the kernel will allow at most 4096 bytes here,
    # from the min_t in fs/btrfs/ioctl.c
    alloc_size = 4096 + alloc_extra

    # keep a reference around; args.fspath isn't a reference after the cast
    fspath = ffi.new('char[]', alloc_size)

    args.fspath = ffi.cast('uint64_t', fspath)
    args.size = alloc_size
    args.inum = ino

    ioctl_pybug(volume_fd, lib.BTRFS_IOC_INO_PATHS, ffi.buffer(args))
    data_container = ffi.cast('struct btrfs_data_container *', fspath)
    if not (data_container.bytes_missing == data_container.elem_missed == 0):
        print(
            'Problem inode %d %d %d' % (
                ino, data_container.bytes_missing, data_container.elem_missed),
            file=sys.stderr)
        # just say no
        raise IOError('Problem on inode %d' % ino)

        if alloc_extra:
            # We already added a lot of padding, don't get caught in a loop.
            raise IOError('Problem on inode %d' % ino)
        else:
            # The +1024 is some extra padding so we don't have to realloc twice
            # if someone is creating hardlinks while we run.
            # The + 8 * is a workaround for the kernel being a little off
            # in its pointer logic.
            # Want: yield from
            for el in lookup_ino_paths(
                volume_fd, ino,
                data_container.bytes_missing + 1024
                + 8 * data_container.elem_missed):
                yield el
            return

    base = ffi.cast('char*', data_container.val)
    offsets = ffi.cast('uint64_t*', data_container.val)

    for i_path in xrange(data_container.elem_cnt):
        ptr = base + offsets[i_path]
        path = ffi.string(ptr)
        yield path


def get_fsid(fd):
    if False:  # pragma: nocover
        args = ffi.new('struct btrfs_ioctl_fs_info_args *')
        args_buf = ffi.buffer(args)
    else:
        # Work around http://bugs.python.org/issue1520818
        # by making sure the buffer size isn't 1024
        args_cbuf = ffi.new(
            'char[]',
            max(ffi.sizeof('struct btrfs_ioctl_fs_info_args'), 1025))
        args_buf = ffi.buffer(args_cbuf)
        args = ffi.cast('struct btrfs_ioctl_fs_info_args *', args_cbuf)
    before = tuple(args.fsid)
    ioctl_pybug(fd, lib.BTRFS_IOC_FS_INFO, args_buf)
    after = tuple(args.fsid)
    # Check for http://bugs.python.org/issue1520818
    assert after != before, (before, after)
    return uuid.UUID(bytes=buffer_to_bytes(ffi.buffer(args.fsid)))


def get_root_id(fd):
    args = ffi.new('struct btrfs_ioctl_ino_lookup_args *')
    # the inode of the root directory
    args.objectid = lib.BTRFS_FIRST_FREE_OBJECTID
    ioctl_pybug(fd, lib.BTRFS_IOC_INO_LOOKUP, ffi.buffer(args))
    return args.treeid


def lookup_ino_path_one(volume_fd, ino, tree_id=0):
    # tree_id == 0 means the subvolume in volume_fd
    # Sort of sucks (only gets one backref),
    # but that's sufficient for now; the other option
    # has kernel bugs we can't work around.
    args = ffi.new('struct btrfs_ioctl_ino_lookup_args *')
    args.objectid = ino
    args.treeid = tree_id
    ioctl_pybug(volume_fd, lib.BTRFS_IOC_INO_LOOKUP, ffi.buffer(args))
    rv = ffi.string(args.name)
    # For some reason the kernel puts a final /
    if tree_id == 0:
        assert rv[-1:] == b'/', repr(rv)
        return rv[:-1]
    else:
        return rv


def read_root_tree(volume_fd):
    args = ffi.new('struct btrfs_ioctl_search_args *')
    args_buffer = ffi.buffer(args)
    sk = args.key

    sk.tree_id = lib.BTRFS_ROOT_TREE_OBJECTID  # the tree of roots
    sk.max_objectid = u64_max
    sk.min_type = lib.BTRFS_ROOT_ITEM_KEY
    sk.max_type = lib.BTRFS_ROOT_BACKREF_KEY
    sk.max_offset = u64_max
    sk.max_transid = u64_max

    root_info = {}
    ri_rel = {}

    while True:
        sk.nr_items = 4096

        ioctl_pybug(
            volume_fd, lib.BTRFS_IOC_TREE_SEARCH, args_buffer)
        if sk.nr_items == 0:
            break

        offset = 0
        for item_id in xrange(sk.nr_items):
            sh = ffi.cast(
                'struct btrfs_ioctl_search_header *', args.buf + offset)
            offset += ffi.sizeof('struct btrfs_ioctl_search_header') + sh.len
            if sh.type == lib.BTRFS_ROOT_ITEM_KEY:
                item = ffi.cast('struct btrfs_root_item *', sh + 1)
                is_frozen = bool(item.flags & lib.BTRFS_ROOT_SUBVOL_RDONLY)
                item_root_id = sh.objectid
                if sh.objectid == lib.BTRFS_FS_TREE_OBJECTID:
                    root_info[sh.objectid] = RootInfo(b'/', None, is_frozen)
            elif sh.type == lib.BTRFS_ROOT_BACKREF_KEY:
                ref = ffi.cast('struct btrfs_root_ref *', sh + 1)
                assert sh.objectid != lib.BTRFS_FS_TREE_OBJECTID
                dir_id = lib.btrfs_stack_root_ref_dirid(ref)
                root_id = sh.objectid
                name = name_of_root_ref(ref)
                # We can use item and is_frozen
                # from the previous loop iteration
                assert root_id == item_root_id
                parent_root_id = sh.offset  # completely obvious, no?
                # The path from the parent root to the parent directory
                reldirpath = lookup_ino_path_one(
                    volume_fd, dir_id, tree_id=parent_root_id)
                assert parent_root_id
                if parent_root_id in root_info:
                    root_info[root_id] = RootInfo(
                        posixpath.join(
                            root_info[parent_root_id].path, reldirpath, name),
                    parent_root_id,
                    is_frozen)
                else:
                    ri_rel[root_id] = RootInfo(
                        posixpath.join(reldirpath, name),
                        parent_root_id,
                        is_frozen)
            # There's also a uuid we could catch on a sufficiently recent
            # BTRFS_ROOT_ITEM_KEY (v3.6). Since the fs is live careful
            # invalidation (in case it was mounted by an older kernel)
            # shouldn't be necessary.

        sk.min_objectid = sh.objectid
        sk.min_type = max(lib.BTRFS_ROOT_ITEM_KEY, sh.type)
        sk.min_offset = sh.offset + 1

    # Deal with parent_root_id > root_id,
    # happens after moving subvolumes.
    while ri_rel:
        for (root_id, ri) in ri_rel.items():
            if ri.parent_root_id not in root_info:
                continue
            parent_path = root_info[ri.parent_root_id].path
            root_info[root_id] = ri._replace(
                path=posixpath.join(parent_path, ri.path))
            del ri_rel[root_id]
    return root_info


def get_root_generation(volume_fd):
    # Adapted from find_root_gen in btrfs-list.c
    # XXX I'm iffy about the search, we may not be using the most
    # recent snapshot, don't want to pick up a newer generation from
    # a different snapshot.
    treeid = get_root_id(volume_fd)
    max_found = 0

    args = ffi.new('struct btrfs_ioctl_search_args *')
    args_buffer = ffi.buffer(args)
    sk = args.key

    sk.tree_id = lib.BTRFS_ROOT_TREE_OBJECTID  # the tree of roots
    sk.min_objectid = sk.max_objectid = treeid
    sk.min_type = sk.max_type = lib.BTRFS_ROOT_ITEM_KEY
    sk.max_offset = u64_max
    sk.max_transid = u64_max

    while True:
        sk.nr_items = 4096

        ioctl_pybug(
            volume_fd, lib.BTRFS_IOC_TREE_SEARCH, args_buffer)
        if sk.nr_items == 0:
            break

        offset = 0
        for item_id in xrange(sk.nr_items):
            sh = ffi.cast(
                'struct btrfs_ioctl_search_header *', args.buf + offset)
            offset += ffi.sizeof('struct btrfs_ioctl_search_header') + sh.len
            assert sh.objectid == treeid
            assert sh.type == lib.BTRFS_ROOT_ITEM_KEY
            item = ffi.cast(
                'struct btrfs_root_item *', sh + 1)
            max_found = max(max_found, lib.btrfs_root_generation(item))

        sk.min_offset = sh.offset + 1

    assert max_found > 0
    return max_found


# clone_data and defragment also have _RANGE variants
def clone_data(dest, src, check_first):
    if check_first and same_extents(dest, src):
        return False
    ioctl_pybug(dest, lib.BTRFS_IOC_CLONE, src)
    return True


def defragment(fd):
    # XXX Can remove compression as a side-effect
    # Also, can unshare extents.
    ioctl_pybug(fd, lib.BTRFS_IOC_DEFRAG)


def find_new(volume_fd, min_generation, results_file, terse, sep):
    args = ffi.new('struct btrfs_ioctl_search_args *')
    args_buffer = ffi.buffer(args)
    sk = args.key

    # Not a valid objectid that I know.
    # But find-new uses that and it seems to work.
    sk.tree_id = 0

    sk.min_transid = min_generation

    sk.max_objectid = u64_max
    sk.max_offset = u64_max
    sk.max_transid = u64_max
    sk.max_type = lib.BTRFS_EXTENT_DATA_KEY

    while True:
        sk.nr_items = 4096

        # May raise EPERM
        ioctl_pybug(
            volume_fd, lib.BTRFS_IOC_TREE_SEARCH, args_buffer)

        if sk.nr_items == 0:
            break

        offset = 0
        for item_id in xrange(sk.nr_items):
            sh = ffi.cast(
                'struct btrfs_ioctl_search_header *', args.buf + offset)
            offset += ffi.sizeof('struct btrfs_ioctl_search_header') + sh.len

            # XXX The classic btrfs find-new looks only at extents,
            # and doesn't find empty files or directories.
            # Need to look at other types.
            if sh.type == lib.BTRFS_EXTENT_DATA_KEY:
                item = ffi.cast(
                    'struct btrfs_file_extent_item *', sh + 1)
                found_gen = lib.btrfs_stack_file_extent_generation(
                    item)
                if terse:
                    name = lookup_ino_path_one(volume_fd, sh.objectid)
                    results_file.write(name + sep)
                else:
                    results_file.write(
                        'item type %d ino %d len %d gen0 %d gen1 %s%s' % (
                            sh.type, sh.objectid, sh.len, sh.transid,
                            found_gen, sep))
                if found_gen < min_generation:
                    continue
            elif sh.type == lib.BTRFS_INODE_ITEM_KEY:
                item = ffi.cast(
                    'struct btrfs_inode_item *', sh + 1)
                found_gen = lib.btrfs_stack_inode_generation(item)
                if terse:
                    # XXX sh.objectid must be wrong
                    continue
                    name = lookup_ino_path_one(volume_fd, sh.objectid)
                    results_file.write(name + sep)
                else:
                    results_file.write(
                        'item type %d ino %d len %d gen0 %d gen1 %d%s' % (
                            sh.type, sh.objectid, sh.len, sh.transid,
                            found_gen, sep))
                if found_gen < min_generation:
                    continue
            elif sh.type == lib.BTRFS_INODE_REF_KEY:
                ref = ffi.cast(
                    'struct btrfs_inode_ref *', sh + 1)
                name = name_of_inode_ref(ref)
                if terse:
                    # XXX short name
                    continue
                    results_file.write(name + sep)
                else:
                    results_file.write(
                        'item type %d ino %d len %d gen0 %d name %s%s' % (
                            sh.type, sh.objectid, sh.len, sh.transid,
                            fsdecode(name), sep))
            elif (sh.type == lib.BTRFS_DIR_ITEM_KEY
                  or sh.type == lib.BTRFS_DIR_INDEX_KEY):
                item = ffi.cast(
                    'struct btrfs_dir_item *', sh + 1)
                name = name_of_dir_item(item)
                if terse:
                    # XXX short name
                    continue
                    results_file.write(name + sep)
                else:
                    results_file.write(
                        'item type %d dir ino %d len %d'
                        ' gen0 %d gen1 %d type1 %d name %s%s' % (
                            sh.type, sh.objectid, sh.len,
                            sh.transid, item.transid, item.type, fsdecode(name), sep))
            else:
                if not terse:
                    results_file.write(
                        'item type %d oid %d len %d gen0 %d%s' % (
                            sh.type, sh.objectid, sh.len, sh.transid, sep))
        sk.min_objectid = sh.objectid
        sk.min_type = sh.type
        sk.min_offset = sh.offset

        # CFFI 0.3 raises an OverflowError if necessary, no need to assert
        #assert sk.min_offset < u64_max
        # If the OverflowError actually happens in practice,
        # we'll need to increase min_type resetting min_objectid to zero,
        # then increase min_objectid resetting min_type and min_offset to zero.
        # See
        # https://btrfs.wiki.kernel.org/index.php/Btrfs_design#Btree_Data_structures
        # and btrfs_key for the btree iteration order.
        sk.min_offset += 1


########NEW FILE########
__FILENAME__ = cffi_support
# vim: set fileencoding=utf-8 sw=4 ts=4 et :

# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import hashlib

from os import getcwd  # XXX


# This will be switched to True by a build_py preprocessor in setup.py
CFFI_INSTALLED_MODE = False
# Will be hardcoded in by a preprocessor so that CFFI module hashes don't
# change after installation
BTRFS_INCLUDE_DIR = getcwd()


def verify(ffi, source, **kwargs):
    assert 'ext_package' not in kwargs
    assert 'modulename' not in kwargs
    kwargs['ext_package'] = 'bedup.platform'

    # modulename can't prevent a rebuild atm,
    # and is also hard to make work with build_ext (build_ext looks
    # at the unprocessed module). Skip it for now.
    if CFFI_INSTALLED_MODE and False:
        # We still need a hash so that the modules have distinct names
        srchash = hashlib.sha1(source).hexdigest()
        kwargs['modulename'] = 'pyext_' + srchash
    return ffi.verify(source, **kwargs)


def get_mods():
    from . import (
        btrfs, chattr, fiemap, futimens, ioprio, openat, syncfs, time, unshare)

    return (
        btrfs, chattr, fiemap, futimens, ioprio, openat, syncfs, time, unshare)


def get_ext_modules():
    return [mod.ffi.verifier.get_extension() for mod in get_mods()]


########NEW FILE########
__FILENAME__ = chattr
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import fcntl

from . import cffi_support


__all__ = (
    'getflags',
    'editflags',
    'FS_IMMUTABLE_FL',
)

ffi = FFI()
ffi.cdef('''
#define FS_IOC_GETFLAGS ...
#define FS_IOC_SETFLAGS ...

#define	FS_SECRM_FL ... /* Secure deletion */
#define	FS_UNRM_FL ... /* Undelete */
#define	FS_COMPR_FL ... /* Compress file */
#define FS_SYNC_FL ... /* Synchronous updates */
#define FS_IMMUTABLE_FL ... /* Immutable file */
#define FS_APPEND_FL ... /* writes to file may only append */
#define FS_NODUMP_FL ... /* do not dump file */
#define FS_NOATIME_FL ... /* do not update atime */
/* Reserved for compression usage... */
#define FS_DIRTY_FL ...
#define FS_COMPRBLK_FL ... /* One or more compressed clusters */
#define FS_NOCOMP_FL ... /* Don't compress */
#define FS_ECOMPR_FL ... /* Compression error */
/* End compression flags --- maybe not all used */
#define FS_BTREE_FL ... /* btree format dir */
#define FS_INDEX_FL ... /* hash-indexed directory */
#define FS_IMAGIC_FL ... /* AFS directory */
#define FS_JOURNAL_DATA_FL ... /* Reserved for ext3 */
#define FS_NOTAIL_FL ... /* file tail should not be merged */
#define FS_DIRSYNC_FL ... /* dirsync behaviour (directories only) */
#define FS_TOPDIR_FL ... /* Top of directory hierarchies*/
#define FS_EXTENT_FL ... /* Extents */
#define FS_DIRECTIO_FL ... /* Use direct i/o */
#define FS_NOCOW_FL ... /* Do not cow file */
#define FS_RESERVED_FL ... /* reserved for ext2 lib */

#define FS_FL_USER_VISIBLE ... /* User visible flags */
#define FS_FL_USER_MODIFIABLE ... /* User modifiable flags */
''')

# apt:linux-libc-dev
lib = cffi_support.verify(ffi, '''
    #include <linux/fs.h>
    ''')

FS_IMMUTABLE_FL = lib.FS_IMMUTABLE_FL


def getflags(fd):
    """
    Gets per-file filesystem flags.
    """

    flags_ptr = ffi.new('uint64_t*')
    flags_buf = ffi.buffer(flags_ptr)
    fcntl.ioctl(fd, lib.FS_IOC_GETFLAGS, flags_buf)
    return flags_ptr[0]


def editflags(fd, add_flags=0, remove_flags=0):
    """
    Sets and unsets per-file filesystem flags.
    """

    if add_flags & remove_flags != 0:
        raise ValueError(
            'Added and removed flags shouldn\'t overlap',
            add_flags, remove_flags)

    # The ext2progs code uses int or unsigned long,
    # the kernel uses an implicit int,
    # let's be explicit here.
    flags_ptr = ffi.new('uint64_t*')
    flags_buf = ffi.buffer(flags_ptr)
    fcntl.ioctl(fd, lib.FS_IOC_GETFLAGS, flags_buf)
    prev_flags = flags_ptr[0]
    flags_ptr[0] |= add_flags
    # Python represents negative numbers with an infinite number of
    # ones in bitops, so this will work correctly.
    flags_ptr[0] &= ~remove_flags
    fcntl.ioctl(fd, lib.FS_IOC_SETFLAGS, flags_buf)
    return prev_flags & (add_flags | remove_flags)


########NEW FILE########
__FILENAME__ = fiemap
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
from collections import namedtuple
import fcntl

from . import cffi_support


ffi = FFI()
ffi.cdef('''
#define FS_IOC_FIEMAP ...

struct fiemap_extent {
    uint64_t fe_logical;  /* logical offset in bytes for the start of
                           * the extent from the beginning of the file */
    uint64_t fe_physical; /* physical offset in bytes for the start
                           * of the extent from the beginning of the disk */
    uint64_t fe_length;   /* length in bytes for this extent */
    uint32_t fe_flags;    /* FIEMAP_EXTENT_* flags for this extent */
    ...;
};

struct fiemap {
    uint64_t fm_start;  /* logical offset (inclusive) at
                         * which to start mapping (in) */
    uint64_t fm_length; /* logical length of mapping which
                         * userspace wants (in) */
    uint32_t fm_flags;          /* FIEMAP_FLAG_* flags for request (in/out) */
    uint32_t fm_mapped_extents; /* number of extents that were mapped (out) */
    uint32_t fm_extent_count;   /* size of fm_extents array (in) */
    struct fiemap_extent fm_extents[0]; /* array of mapped extents (out) */
    ...;
};

#define FIEMAP_MAX_OFFSET ...

#define FIEMAP_FLAG_SYNC                ... /* sync file data before map */
#define FIEMAP_FLAG_XATTR               ... /* map extended attribute tree */
#define FIEMAP_FLAGS_COMPAT             ...

#define FIEMAP_EXTENT_LAST              ... /* Last extent in file. */
#define FIEMAP_EXTENT_UNKNOWN           ... /* Data location unknown. */
#define FIEMAP_EXTENT_DELALLOC          ... /* Location still pending.
                                             * Sets EXTENT_UNKNOWN. */
#define FIEMAP_EXTENT_ENCODED           ... /* Data can not be read
                                             * while fs is unmounted */
#define FIEMAP_EXTENT_DATA_ENCRYPTED    ... /* Data is encrypted by fs.
                                             * Sets EXTENT_NO_BYPASS. */
#define FIEMAP_EXTENT_NOT_ALIGNED       ... /* Extent offsets may not be
                                             * block aligned. */
#define FIEMAP_EXTENT_DATA_INLINE       ... /* Data mixed with metadata.
                                             * Sets EXTENT_NOT_ALIGNED.*/
#define FIEMAP_EXTENT_DATA_TAIL         ... /* Multiple files in block.
                                             * Sets EXTENT_NOT_ALIGNED.*/
#define FIEMAP_EXTENT_UNWRITTEN         ... /* Space allocated, but
                                             * no data (i.e. zero). */
#define FIEMAP_EXTENT_MERGED            ... /* File does not natively
                                             * support extents. Result
                                             * merged for efficiency. */
// Linux 2.6.33
#define FIEMAP_EXTENT_SHARED            ... /* Space shared with other
                                             * files. */

''')

lib = cffi_support.verify(ffi, '''
#include <inttypes.h>
#include <linux/fs.h>
#include <linux/fiemap.h>
''')


FiemapExtent = namedtuple('FiemapExtent', 'logical physical length flags')


def fiemap(fd):
    """
    Gets a map of file extents.
    """

    count = 72
    fiemap_cbuf = ffi.new(
        'char[]',
        ffi.sizeof('struct fiemap')
        + count * ffi.sizeof('struct fiemap_extent'))
    fiemap_pybuf = ffi.buffer(fiemap_cbuf)
    fiemap_ptr = ffi.cast('struct fiemap*', fiemap_cbuf)
    assert ffi.sizeof(fiemap_cbuf) <= 4096

    while True:
        fiemap_ptr.fm_length = lib.FIEMAP_MAX_OFFSET
        fiemap_ptr.fm_extent_count = count
        fcntl.ioctl(fd, lib.FS_IOC_FIEMAP, fiemap_pybuf)
        if fiemap_ptr.fm_mapped_extents == 0:
            break
        for i in xrange(fiemap_ptr.fm_mapped_extents):
            extent = fiemap_ptr.fm_extents[i]
            yield FiemapExtent(
                extent.fe_logical, extent.fe_physical,
                extent.fe_length, extent.fe_flags)
        fiemap_ptr.fm_start = extent.fe_logical + extent.fe_length


def same_extents(fd1, fd2):
    return tuple(fiemap(fd1)) == tuple(fiemap(fd2))


########NEW FILE########
__FILENAME__ = futimens
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import os
import weakref

from . import cffi_support


# XXX All this would work effortlessly in Python 3.3:
# st_atime_ns, and os.utime(ns=())


ffi = FFI()
ffi.cdef('''
struct timespec {
    // time_t is long
    long tv_sec;  // seconds
    long tv_nsec; // nanoseconds
};

struct stat {
    struct timespec st_atim;
    struct timespec st_mtim;
    ...;
};

int fstat(int fd, struct stat *buf);

int futimens(int fd, const struct timespec times[2]);
''')
lib = cffi_support.verify(ffi, '''
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
''')


_stat_ownership = weakref.WeakKeyDictionary()


def fstat_ns(fd):
    stat = ffi.new('struct stat *')
    if lib.fstat(fd, stat) != 0:
        raise IOError(ffi.errno, os.strerror(ffi.errno), fd)
    # The nested structs seem to be recreated at every member access.
    atime, mtime = stat.st_atim, stat.st_mtim
    assert 0 <= atime.tv_nsec < 1e9
    assert 0 <= mtime.tv_nsec < 1e9
    _stat_ownership[atime] = _stat_ownership[mtime] = stat
    return atime, mtime


def futimens(fd, ns):
    """
    set inode atime and mtime

    ns is (atime, mtime), a pair of struct timespec
    with nanosecond resolution.
    """

    # ctime can't easily be reset
    # also, we have no way to do mandatory locking without
    # changing the ctime.
    times = ffi.new('struct timespec[2]')
    atime, mtime = ns
    assert 0 <= atime.tv_nsec < 1e9
    assert 0 <= mtime.tv_nsec < 1e9
    times[0] = atime
    times[1] = mtime
    if lib.futimens(fd, times) != 0:
        raise IOError(
            ffi.errno, os.strerror(ffi.errno),
            (fd, atime.tv_sec, atime.tv_nsec, mtime.tv_sec, mtime.tv_nsec))


########NEW FILE########
__FILENAME__ = ioprio
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import os

from . import cffi_support


# Or we could just use psutil (though it's not PyPy compatible)


ffi = FFI()
ffi.cdef('''
#define IOPRIO_WHO_PROCESS ...
#define IOPRIO_WHO_PGRP ...
#define IOPRIO_WHO_USER ...

#define IOPRIO_CLASS_NONE ...
#define IOPRIO_CLASS_RT ...
#define IOPRIO_CLASS_BE ...
#define IOPRIO_CLASS_IDLE ...

int ioprio_get(int which, int who);
int ioprio_set(int which, int who, int ioprio);
int IOPRIO_PRIO_VALUE(int class, int data);
int IOPRIO_PRIO_CLASS(int mask);
int IOPRIO_PRIO_DATA(int mask);
''')

# Parts nabbed from schedutils/ionice.c
# include/linux/ioprio.h has the macro half
lib = cffi_support.verify(ffi, '''
#include <unistd.h>
#include <sys/syscall.h>

#define IOPRIO_CLASS_SHIFT      (13)
#define IOPRIO_PRIO_VALUE(class, data) (((class) << IOPRIO_CLASS_SHIFT) | data)
#define IOPRIO_PRIO_MASK        ((1UL << IOPRIO_CLASS_SHIFT) - 1)
#define IOPRIO_PRIO_CLASS(mask) ((mask) >> IOPRIO_CLASS_SHIFT)
#define IOPRIO_PRIO_DATA(mask)  ((mask) & IOPRIO_PRIO_MASK)
#define IOPRIO_PRIO_VALUE(class, data) (((class) << IOPRIO_CLASS_SHIFT) | data)

enum {
    IOPRIO_CLASS_NONE,
    IOPRIO_CLASS_RT,
    IOPRIO_CLASS_BE,
    IOPRIO_CLASS_IDLE,
};

enum {
    IOPRIO_WHO_PROCESS = 1,
    IOPRIO_WHO_PGRP,
    IOPRIO_WHO_USER,
};

static inline int ioprio_set(int which, int who, int ioprio) {
    return syscall(SYS_ioprio_set, which, who, ioprio);
}

static inline int ioprio_get(int which, int who) {
    return syscall(SYS_ioprio_get, which, who);
}
''')


def set_idle_priority(pid=None):
    """
    Puts a process in the idle io priority class.

    If pid is omitted, applies to the current process.
    """

    if pid is None:
        pid = os.getpid()
    lib.ioprio_set(
        lib.IOPRIO_WHO_PROCESS, pid,
        lib.IOPRIO_PRIO_VALUE(lib.IOPRIO_CLASS_IDLE, 0))


########NEW FILE########
__FILENAME__ = openat
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import os

from . import cffi_support


ffi = FFI()
ffi.cdef('''
    int openat(int dirfd, const char *pathname, int flags);
''')
lib = cffi_support.verify(ffi, '''
#include <fcntl.h>
''')


def openat(base_fd, path, flags):
    fd = lib.openat(base_fd, path, flags)
    if fd < 0:
        # There's a little bit of magic here:
        # IOError.errno is only set if there are exactly two or three
        # arguments.
        raise IOError(ffi.errno, os.strerror(ffi.errno), (base_fd, path))
    return fd


def fopenat(base_fd, path):
    """
    Does openat read-only, then does fdopen to get a file object
    """

    return os.fdopen(openat(base_fd, path, os.O_RDONLY), 'rb')


def fopenat_rw(base_fd, path):
    """
    Does openat read-write, then does fdopen to get a file object
    """

    return os.fdopen(openat(base_fd, path, os.O_RDWR), 'rb+')


########NEW FILE########
__FILENAME__ = syncfs
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import os

from . import cffi_support


ffi = FFI()
ffi.cdef('''
int syncfs(int fd);
''')
lib = cffi_support.verify(ffi, '''
#include <unistd.h>
#include <sys/syscall.h>

// (re)define for compatibility with glibc < 2.14
int syncfs(int fd) {
    return syscall(__NR_syncfs, fd);
}
''',
    extra_compile_args=['-D_GNU_SOURCE'])


def syncfs(fd):
    if lib.syncfs(fd) != 0:
        raise IOError(ffi.errno, os.strerror(ffi.errno), fd)


########NEW FILE########
__FILENAME__ = time
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ('monotonic_time', )

from cffi import FFI

from . import cffi_support


ffi = FFI()
ffi.cdef('''
#define CLOCK_MONOTONIC ...

// From /usr/include/bits:
// time_t is long, clockid_t is int

struct timespec {
    long     tv_sec;        /* seconds */
    long     tv_nsec;       /* nanoseconds */
};

int clock_gettime(int clk_id, struct timespec *tp);
''')

lib = cffi_support.verify(ffi, '''
#include <time.h>''',
    libraries=['rt'])


def monotonic_time():
    tp = ffi.new('struct timespec *')
    if lib.clock_gettime(lib.CLOCK_MONOTONIC, tp) != 0:
        assert False, ffi.errno
    return tp.tv_sec + 1e-9 * tp.tv_nsec


########NEW FILE########
__FILENAME__ = unshare
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from cffi import FFI
import os


from . import cffi_support


ffi = FFI()
ffi.cdef('''
// New mount namespace
#define CLONE_NEWNS ...

int unshare(int flags);
''')
lib = cffi_support.verify(ffi, '''
#include <sched.h>
''',
    extra_compile_args=['-D_GNU_SOURCE'])

CLONE_NEWNS = lib.CLONE_NEWNS


def unshare(flags):
    if lib.unshare(flags) != 0:
        raise IOError(ffi.errno, os.strerror(ffi.errno), flags)


########NEW FILE########
__FILENAME__ = termupdates
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import collections
import string
import sys

from .platform.time import monotonic_time

_formatter = string.Formatter()

# Yay VT100
LINE_START = '\r'
CLEAR_END_OF_LINE = '\x1b[K'
CLEAR_LINE = LINE_START + CLEAR_END_OF_LINE
# XXX nowrap doesn't work well in screen (over gnome-term, libvte)
# with some non-ascii characters that are twice as wide in a monospace font.
# All tested terms (urxvt, aterm, xterm, xfce4-terminal, gnome-terminal)
# work fine without screen, for either value of VTE_CJK_WIDTH.
# See: CJK double-width/bi-width
TTY_NOWRAP = '\x1b[?7l'
TTY_DOWRAP = '\x1b[?7h'
HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'


def format_duration(seconds):
    sec_format = '%05.2f'
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        sec_format = '%04.1f'
    hours, minutes = divmod(minutes, 60)
    if hours:
        sec_format = '%02d'
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    greatest_unit = (
        not weeks, not days, not hours, not minutes, not seconds, False
    ).index(False)
    rv = ''
    if weeks:
        rv += '%dW' % weeks
    if days:
        rv += '%dD' % days
    if rv:
        rv += ' '
    if greatest_unit <= 2:
        rv += '%02d:' % hours
    if greatest_unit <= 3:
        rv += '%02d:' % minutes
    rv += sec_format % seconds
    return rv


class TermTemplate(object):
    def __init__(self):
        self._template = None
        self._kws = {}
        self._kws_counter = collections.defaultdict(int)
        self._kws_totals = {}
        self._stream = sys.stdout
        self._isatty = self._stream.isatty()
        # knowing this is stdout:
        self._newline_needs_flush = not self._isatty
        self._wraps = True

    def update(self, **kwargs):
        self._kws.update(kwargs)
        for key in kwargs:
            self._kws_counter[key] += 1
        self._render(with_newline=False)

    def set_total(self, **kwargs):
        self._kws_totals.update(kwargs)
        self._render(with_newline=False)

    def format(self, template):
        if self._template is not None:
            self._render(with_newline=True)
        else:
            self._initial_time = monotonic_time()
        self._kws.clear()
        self._kws_counter.clear()
        self._kws_totals.clear()
        if template is None:
            self._template = None
        else:
            self._template = tuple(_formatter.parse(template))
            self._time = monotonic_time()
            self._render(with_newline=False)

    def _write_tty(self, data):
        if self._isatty:
            self._stream.write(data)

    def _nowrap(self):
        # Don't forget to flush
        if self._wraps:
            self._write_tty(TTY_NOWRAP)
            self._wraps = False

    def _dowrap(self):
        # Don't forget to flush
        if not self._wraps:
            self._write_tty(TTY_DOWRAP)
            self._wraps = True

    def _render(self, with_newline, flush_anyway=False):
        if (self._template is not None) and (self._isatty or with_newline):
            self._nowrap()
            self._write_tty(CLEAR_LINE)
            for (
                literal_text, field_name, format_spec, conversion
            ) in self._template:
                self._stream.write(literal_text)
                if field_name:
                    if format_spec == '':
                        if field_name in ('elapsed', 'elapsed_total'):
                            format_spec = 'time'

                    if format_spec == '':
                        self._stream.write(str(self._kws.get(field_name, '')))
                    elif format_spec == 'total':
                        if field_name in self._kws_totals:
                            self._stream.write(
                                '%d' % self._kws_totals[field_name])
                        else:
                            self._stream.write('??')
                    elif format_spec == 'time':
                        if field_name == 'elapsed':
                            duration = monotonic_time() - self._time
                        elif field_name == 'elapsed_total':
                            duration = monotonic_time() - self._initial_time
                        else:
                            assert False, field_name
                        self._stream.write(format_duration(duration))
                    elif format_spec == 'truncate-left':
                        # XXX NotImplemented
                        self._stream.write(self._kws.get(field_name, ''))
                    elif format_spec == 'size':
                        # XXX stub
                        self._stream.write(
                            '%d' % (self._kws.get(field_name, 0)))
                    elif format_spec == 'counter':
                        self._stream.write(
                            '%d' % self._kws_counter[field_name])
                    else:
                        assert False, format_spec
            # Just in case we get an inopportune SIGKILL, reset this
            # immediately (before the render flush) so we don't have to
            # rely on finish: clauses or context managers.
            self._dowrap()
            if with_newline:
                self._stream.write('\n')
                if self._newline_needs_flush:
                    self._stream.flush()
            else:
                self._stream.flush()
        elif flush_anyway:
            self._stream.flush()

    def notify(self, message):
        self._write_tty(CLEAR_LINE)
        self._dowrap()
        self._stream.write(message + '\n')
        self._render(
            with_newline=False, flush_anyway=self._newline_needs_flush)

    def close(self):
        # Called close so it can be used with contextlib.closing
        self._render(with_newline=True)
        self._dowrap()
        self._stream.flush()
        self._stream = None


########NEW FILE########
__FILENAME__ = test_bedup

import contextlib
import fcntl
import multiprocessing
import os
import shutil
import subprocess
import tempfile


from .platform.syncfs import syncfs
from .platform.btrfs import lookup_ino_paths, BTRFS_FIRST_FREE_OBJECTID

from .__main__ import main
from . import compat  # monkey-patch check_output and O_CLOEXEC

# Placate pyflakes
tdir = db = fs = fsimage = fsimage2 = sampledata1 = sampledata2 = vol_fd = None


def mk_sample_data(fn):
    subprocess.check_call(
        'dd bs=4096 count=2048 if=/dev/urandom'.split() + ['of=' + fn])
    return fn


def setup_module():
    global tdir, db, fs, fsimage, fsimage2, sampledata1, sampledata2, vol_fd
    tdir = tempfile.mkdtemp(prefix='dedup-tests-')
    db = tdir + '/db.sqlite'
    fsimage = tdir + '/fsimage.btrfs'
    fsimage2 = tdir + '/fsimage-nolabel.btrfs'
    sampledata1 = mk_sample_data(tdir + '/s1.sample')
    sampledata2 = mk_sample_data(tdir + '/s2.sample')
    fs = tdir + '/fs'
    os.mkdir(fs)

    # The older mkfs.btrfs on travis somehow needs 256M;
    # sparse file, costs nothing
    subprocess.check_call('truncate -s256M --'.split() + [fsimage])
    subprocess.check_call('truncate -s256M --'.split() + [fsimage2])
    # mkfs.btrfs is buggy under libefence
    env2 = dict(os.environ)
    if 'LD_PRELOAD' in env2 and 'libefence.so' in env2['LD_PRELOAD']:
        del env2['LD_PRELOAD']
    subprocess.check_call(
        'mkfs.btrfs -LBedupTest --'.split() + [fsimage], env=env2)
    subprocess.check_call(
        'mkfs.btrfs --'.split() + [fsimage2], env=env2)
    subprocess.check_call(
        'mount -t btrfs -o loop,compress-force=lzo --'.split() + [fsimage, fs])
    shutil.copy(sampledata1, os.path.join(fs, 'one.sample'))
    shutil.copy(sampledata1, os.path.join(fs, 'two.sample'))
    shutil.copy(sampledata2, os.path.join(fs, 'three.sample'))
    shutil.copy(sampledata2, os.path.join(fs, 'four.sample'))
    vol_fd = os.open(fs, os.O_DIRECTORY)
    syncfs(vol_fd)


def subp_main(conn, argv):
    try:
        rv = main(argv)
    except Exception as exn:
        conn.send(exn)
        raise
    except:
        conn.send('I don\'t even')
        raise
    else:
        conn.send(rv)


def boxed_call(argv, expected_rv=None):
    # We need multiprocessing rather than fork(), because the
    # former has hooks for nose-cov, pytest-cov & friends.
    # Also fork + sys.exit breaks pytest, os._exit was required.
    # Also also, multiprocessing won't let us use sys.exit either
    # (it captures the exception and changes the exit status).
    # We have to use IPC instead.
    parent_conn, child_conn = multiprocessing.Pipe()
    argv = list(argv)
    if argv[0] not in 'dedup-files find-new'.split():
        argv[1:1] = ['--db-path', db]
    argv[0:0] = ['__main__']
    proc = multiprocessing.Process(target=subp_main, args=(child_conn, argv))
    proc.start()
    rv = parent_conn.recv()
    proc.join()
    if isinstance(rv, Exception):
        raise rv
    assert rv == expected_rv


def stat(fname):
    # stat without args would include ctime, use a custom format
    return subprocess.check_output(
        ['stat', '--printf=atime %x\nmtime %y\n', '--', fname])


@contextlib.contextmanager
def open_cloexec(fname, rw=False):
    if rw:
        fd = os.open(fname, os.O_CLOEXEC | os.O_RDWR)
    else:
        fd = os.open(fname, os.O_CLOEXEC | os.O_RDONLY)
    yield
    os.close(fd)


def test_functional():
    boxed_call('scan --'.split() + [fs])
    with open_cloexec(fs + '/one.sample') as busy1:
        with open_cloexec(fs + '/three.sample') as busy2:
            boxed_call('dedup --'.split() + [fs])
    boxed_call('reset --'.split() + [fs])
    boxed_call('scan --size-cutoff=65536 --'.split() + [fs, fs])
    boxed_call('dedup --'.split() + [fs])
    boxed_call(
        'dedup-files --defrag --'.split() +
        [fs + '/one.sample', fs + '/two.sample'])
    stat0 = stat(fs + '/one.sample')
    shutil.copy(sampledata1, os.path.join(fs, 'two.sample'))
    with open_cloexec(fs + '/one.sample', rw=True):
        with open_cloexec(fs + '/two.sample', rw=True):
            boxed_call(
                'dedup-files --defrag --'.split() +
                    [fs + '/one.sample', fs + '/two.sample'],
                expected_rv=1)
    boxed_call(
        'dedup-files --defrag --'.split() +
            [fs + '/one.sample', fs + '/two.sample'])
    stat1 = stat(fs + '/one.sample')
    # Check that atime and mtime are restored
    assert stat0 == stat1
    boxed_call('find-new --'.split() + [fs])
    boxed_call('show'.split())


def teardown_module():
    if vol_fd is not None:
        os.close(vol_fd)
    try:
        subprocess.check_call('umount --'.split() + [fs])
    except subprocess.CalledProcessError:
        # Apparently we kept the vol fd around
        # Not necessarily a bad thing, because keeping references
        # to closed file descriptors is much worse.
        # Will need a test harness that lets us split processes,
        # and still tracks code coverage in the slave.
        subprocess.check_call('lsof -n'.split() + [fs])
        raise
    finally:
        shutil.rmtree(tdir)


########NEW FILE########
__FILENAME__ = tracking
# vim: set fileencoding=utf-8 sw=4 ts=4 et :
# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import errno
import fcntl
import gc
import hashlib
import os
import resource
import stat
import sys
import threading

from collections import defaultdict, namedtuple
from contextlib import closing, contextmanager
from contextlib2 import ExitStack
from itertools import groupby
from sqlalchemy.sql import and_, select, func, literal_column
from uuid import UUID

from .compat import fsdecode
from .platform.btrfs import (
    get_root_generation, clone_data, defragment as btrfs_defragment)
from .platform.openat import fopenat, fopenat_rw

from .datetime import system_now
from .dedup import ImmutableFDs, cmp_files
from .filesystem import NotPlugged
from .hashing import mini_hash_from_file, fiemap_hash_from_file
from .model import (
    Inode, get_or_create, DedupEvent, DedupEventInode)


BUFSIZE = 8192

WINDOW_SIZE = 200


def reset_vol(sess, vol):
    # Forgets Inodes, not logging. Make that configurable?
    sess.query(Inode).filter_by(vol=vol.impl).delete()
    vol.last_tracked_generation = 0
    sess.commit()


def fake_updates(sess, max_events):
    faked = 0
    for de in sess.query(DedupEvent).limit(max_events):
        ino_count = 0
        for dei in de.inodes:
            inode = sess.query(Inode).filter_by(
                ino=dei.ino, vol=dei.vol).scalar()
            if not inode:
                continue
            inode.has_updates = True
            ino_count += 1
        if ino_count > 1:
            faked += 1
    sess.commit()
    return faked


def inodes_by_size(sess, size):
    # orm grouping is too complicated, just sort
    return sess.query(Inode).filter_by(size=size).order_by(
        Inode.fs_id, Inode.vol_id)


def annotated_inodes_by_size(whole_fs, size):
    sess = whole_fs.sess
    fs_uuid = None
    vol_id = None

    for inode in inodes_by_size(sess, size):
        if inode.vol_id != vol_id:
            if vol_id is not None and vol is not None:
                vol.close()
            if inode.vol.fs.uuid != fs_uuid:
                if fs_uuid is not None:
                    #fs.close()  # XXX implement
                    fs.clean_up_mpoints()
                fs_uuid = inode.vol.fs.uuid
                fs = whole_fs.get_fs(UUID(hex=fs_uuid))
            vol_id = inode.vol_id
            # XXX Make the mountpoint read-only
            try:
                vol = fs.load_vol_by_root_id(inode.vol.root_id)
            except NotPlugged:
                vol = None
                continue
            except KeyError:
                vol = None
                continue
        if vol is None:
            continue
        try:
            rp = vol.lookup_one_path(inode)
        except IOError as err:
            if err.errno != errno.ENOENT:
                raise
            sess.delete(inode)
            continue
        yield vol, rp, inode


def track_updated_files(sess, vol, tt):
    from .platform.btrfs import ffi, u64_max

    top_generation = get_root_generation(vol.fd)
    if (vol.last_tracked_size_cutoff is not None
        and vol.last_tracked_size_cutoff <= vol.size_cutoff):
        min_generation = vol.last_tracked_generation + 1
    else:
        min_generation = 0
    if min_generation > top_generation:
        tt.notify(
            'Not scanning %s, generation is still %d'
            % (vol, top_generation))
        sess.commit()
        return
    tt.notify(
        'Scanning volume %s generations from %d to %d, with size cutoff %d'
        % (vol, min_generation, top_generation, vol.size_cutoff))
    tt.format(
        '{elapsed} Scanned {scanned} retained {retained:counter}')
    scanned = 0

    args = ffi.new('struct btrfs_ioctl_search_args *')
    args_buffer = ffi.buffer(args)
    sk = args.key
    lib = ffi.verifier.load_library()

    # Not a valid objectid that I know.
    # But find-new uses that and it seems to work.
    sk.tree_id = 0

    # Because we don't have min_objectid = max_objectid,
    # a min_type filter would be ineffective.
    # min_ criteria are modified by the kernel during tree traversal;
    # they are used as an iterator on tuple order,
    # not an intersection of min ranges.
    sk.min_transid = min_generation

    sk.max_objectid = u64_max
    sk.max_offset = u64_max
    sk.max_transid = u64_max
    sk.max_type = lib.BTRFS_INODE_ITEM_KEY

    while True:
        sk.nr_items = 4096

        try:
            fcntl.ioctl(
                vol.fd, lib.BTRFS_IOC_TREE_SEARCH, args_buffer)
        except IOError:
            raise

        if sk.nr_items == 0:
            break

        offset = 0
        for item_id in xrange(sk.nr_items):
            sh = ffi.cast(
                'struct btrfs_ioctl_search_header *', args.buf + offset)
            offset += ffi.sizeof('struct btrfs_ioctl_search_header') + sh.len

            # We can't prevent the search from grabbing irrelevant types
            if sh.type == lib.BTRFS_INODE_ITEM_KEY:
                item = ffi.cast(
                    'struct btrfs_inode_item *', sh + 1)
                inode_gen = lib.btrfs_stack_inode_generation(item)
                size = lib.btrfs_stack_inode_size(item)
                mode = lib.btrfs_stack_inode_mode(item)
                if size < vol.size_cutoff:
                    continue
                # XXX Should I use inner or outer gen in these checks?
                # Inner gen seems to miss updates (due to delalloc?),
                # whereas outer gen has too many spurious updates.
                if (vol.last_tracked_size_cutoff
                    and size >= vol.last_tracked_size_cutoff):
                    if inode_gen <= vol.last_tracked_generation:
                        continue
                else:
                    if inode_gen < min_generation:
                        continue
                if not stat.S_ISREG(mode):
                    continue
                ino = sh.objectid
                inode, inode_created = get_or_create(
                    sess, Inode, vol=vol.impl, ino=ino)
                inode.size = size
                inode.has_updates = True
                tt.update(retained=True)
        scanned += sk.nr_items
        tt.update(scanned=scanned)

        sk.min_objectid = sh.objectid
        sk.min_type = sh.type
        sk.min_offset = sh.offset

        sk.min_offset += 1
    tt.format(None)
    vol.last_tracked_generation = top_generation
    vol.last_tracked_size_cutoff = vol.size_cutoff
    sess.commit()


class Checkpointer(threading.Thread):
    def __init__(self, bind):
        super(Checkpointer, self).__init__(name='checkpointer')
        self.bind = bind
        self.evt = threading.Event()
        self.done = False

    def run(self):
        self.conn = self.bind.connect()
        while True:
            self.evt.wait()
            self.conn.execute('PRAGMA wal_checkpoint;')
            self.evt.clear()
            if self.done:
                return

    def please_checkpoint(self):
        self.evt.set()
        if not self.is_alive():
            self.start()

    def close(self):
        if not self.is_alive():
            return
        self.done = True
        self.evt.set()
        self.join()


Commonality1 = namedtuple('Commonality1', 'size inode_count inodes')


class WindowedQuery(object):
    def __init__(
        self, sess, unfiltered, filt_crit, tt, window_size=WINDOW_SIZE
    ):
        self.sess = sess
        self.unfiltered = unfiltered
        self.filt_crit = filt_crit
        self.tt = tt
        self.window_size = window_size

        self.skipped = []

        # select-only, can't be used for updates
        self.filtered_s = filtered = select(
            unfiltered.c
        ).where(
            filt_crit
        ).alias('filtered')

        self.selectable = select([
            filtered.c.size,
            func.count().label('inode_count'),
            func.max(filtered.c.has_updates).label('has_updates')]
        ).group_by(
            filtered.c.size,
        ).having(and_(
            literal_column('inode_count') > 1,
            literal_column('has_updates') > 0,
        ))

        # This is higher than selectable.first().size, in order to also clear
        # updates without commonality.
        self.upper_bound = self.sess.query(
            self.unfiltered.c.size).order_by(
                -self.unfiltered.c.size).limit(1).scalar()
        if self.upper_bound is None:
            self.upper_bound = -1

    def __len__(self):
        return self.sess.execute(self.selectable.count()).scalar()

    def __iter__(self):
        # XXX The PRAGMAs below only work with a SingletonThreadPool.
        # Otherwise they'd have to be re-enabled every time the session
        # calls self.bind.connect().
        # Clearing updates and logging dedup events can cause frequent
        # commits, we don't mind losing them in a crash (no need for
        # durability). SQLite is in WAL mode, so this pragma should disable
        # most commit-time fsync calls without compromising consistency.
        self.sess.execute('PRAGMA synchronous=NORMAL;')
        # Checkpointing is now in the checkpointer thread.
        self.sess.execute('PRAGMA wal_autocheckpoint=0;')
        # just to check commit speed
        #sess.commit()

        checkpointer = Checkpointer(self.sess.bind)
        checkpointer.daemon = True

        # [window_start, window_end] is inclusive at both ends
        selectable = self.selectable.order_by(-self.filtered_s.c.size)

        # This is higher than selectable.first().size, in order to also clear
        # updates without commonality.
        window_start = self.upper_bound

        while True:
            window_select = selectable.where(
                self.filtered_s.c.size <= window_start
            ).limit(self.window_size).alias('s1')
            li = self.sess.execute(window_select).fetchall()
            if not li:
                self.clear_updates(window_start, 0)
                break
            window_start = li[0].size
            window_end = li[-1].size
            # If we wanted to be subtle we'd use limits here as well
            inodes = self.sess.query(Inode).select_entity_from(
                self.filtered_s).join(
                window_select, window_select.c.size == Inode.size
            ).order_by(-Inode.size, Inode.ino)
            inodes_by_size = groupby(inodes, lambda inode: inode.size)
            for size, inodes in inodes_by_size:
                inodes = list(inodes)
                yield Commonality1(size, len(inodes), inodes)
            self.clear_updates(window_start, window_end)
            checkpointer.please_checkpoint()
            window_start = window_end - 1

        self.tt.format('{elapsed} Committing tracking state')
        checkpointer.close()
        # Restore fsync so that the final commit (in dedup_tracked)
        # will be durable.
        self.sess.execute('PRAGMA synchronous=FULL;')

    def clear_updates(self, window_start, window_end):
        # Can't call update directly on FilteredInode because it is aliased.
        # Can't use a <= b <= c in one term with SQLa.
        self.sess.execute(
            self.unfiltered.update().where(and_(
                self.filt_crit,
                window_start >= self.unfiltered.c.size,
                self.unfiltered.c.size >= window_end,
            )).values(
                has_updates=False))

        for inode in self.skipped:
            inode.has_updates = True
        self.sess.commit()
        # clear the list
        self.skipped[:] = []

    def clear_all_updates(self):
        return self.clear_updates(self.upper_bound, 0)


def hardcode_params_unsafe(query):
    # Only tested with ints on sqlite
    # Used to work around the sqlite parameter limit
    q2 = query.compile()
    q2.visit_bindparam = q2.render_literal_bindparam
    return q2.process(query)


def dedup_tracked(sess, volset, tt, defrag):
    fs = volset[0].fs
    vol_ids = [vol.impl.id for vol in volset]
    assert all(vol.fs == fs for vol in volset)

    # 3 for stdio, 3 for sqlite (wal mode), 1 that somehow doesn't
    # get closed, 1 per volume.
    ofile_reserved = 7 + len(volset)

    inode = Inode.__table__
    inode_filt = inode.c.vol_id.in_(vol_ids)
    if len(volset) > 490:
        # SQLite 3 has a hardcoded limit on query parameters
        inode_filt = hardcode_params_unsafe(inode_filt)
    query = WindowedQuery(sess, inode, inode_filt, tt)
    le = len(query)
    ds = DedupSession(sess, tt, defrag, fs, query, ofile_reserved)

    if le:
        # Hopefully close any files we left around
        gc.collect()

        tt.format(
            '{elapsed} Size group {comm1:counter}/{comm1:total} ({size:size}) '
            'sampled {mhash:counter} hashed {fhash:counter} '
            'freed {space_gain:size}')
        tt.set_total(comm1=le)
        for comm1 in query:
            dedup_tracked1(ds, comm1)
        tt.format(None)
    else:
        query.clear_all_updates()
    sess.commit()
    tt.format(None)



class DedupSession(object):
    space_gain = 0

    def __init__(self, sess, tt, defrag, fs, query, ofile_reserved):
        self.sess = sess
        self.tt = tt
        self.defrag = defrag
        self.fs = fs
        self.query = query
        self.ofile_reserved = ofile_reserved
        self.ofile_soft, self.ofile_hard = resource.getrlimit(
            resource.RLIMIT_OFILE)

    def skip(self, inode):
        self.query.skipped.append(inode)

    @contextmanager
    def open_by_inode(self, inode):
        try:
            pathb = inode.vol.live.lookup_one_path(inode)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            # Delete stale inodes;
            # some do survive because the number is reused.
            self.sess.delete(inode)
            yield None
            return

        try:
            rfile = fopenat(inode.vol.live.fd, pathb)
        except IOError as e:
            if e.errno not in (errno.ENOENT, errno.EISDIR):
                raise
            # Don't delete an inode if it was moved by a racing process;
            # mark it for the next run.
            self.skip(inode)
            yield None
            return

        try:
            yield rfile
        finally:
            rfile.close()


def dedup_tracked1(ds, comm1):
    size = comm1.size
    ds.tt.update(comm1=comm1, size=size)
    by_mh = defaultdict(list)
    for inode in comm1.inodes:
        # XXX Need to cope with deleted inodes.
        # We cannot find them in the search-new pass, not without doing
        # some tracking of directory modifications to poke updated
        # directories to find removed elements.

        # rehash everytime for now
        # I don't know enough about how inode transaction numbers are
        # updated (as opposed to extent updates) to be able to actually
        # cache the result
        with ds.open_by_inode(inode) as rfile:
            if rfile is None:
                continue
            by_mh[mini_hash_from_file(inode, rfile)].append(inode)
            ds.tt.update(mhash=None)

    for inodes in by_mh.itervalues():
        inode_count = len(inodes)
        if inode_count < 2:
            continue
        fies = set()
        for inode in inodes:
            with ds.open_by_inode(inode) as rfile:
                if rfile is None:
                    continue
                fies.add(fiemap_hash_from_file(rfile))

        if len(fies) < 2:
            continue

        files = []
        fds = []
        # For description only
        fd_names = {}
        fd_inodes = {}
        by_hash = defaultdict(list)

        # XXX I have no justification for doubling inode_count
        ofile_req = 2 * inode_count + ds.ofile_reserved
        if ofile_req > ds.ofile_soft:
            if ofile_req <= ds.ofile_hard:
                resource.setrlimit(
                    resource.RLIMIT_OFILE, (ofile_req, ds.ofile_hard))
                ds.ofile_soft = ofile_req
            else:
                ds.tt.notify(
                    'Too many duplicates (%d at size %d), '
                    'would bring us over the open files limit (%d, %d).'
                    % (inode_count, size, ds.ofile_soft, ds.ofile_hard))
                for inode in inodes:
                    if inode.has_updates:
                        ds.skip(inode)
                continue

        for inode in inodes:
            # Open everything rw, we can't pick one for the source side
            # yet because the crypto hash might eliminate it.
            # We may also want to defragment the source.
            try:
                pathb = inode.vol.live.lookup_one_path(inode)
                path = fsdecode(pathb)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    ds.sess.delete(inode)
                    continue
                raise
            try:
                afile = fopenat_rw(inode.vol.live.fd, pathb)
            except IOError as e:
                if e.errno == errno.ETXTBSY:
                    # The file contains the image of a running process,
                    # we can't open it in write mode.
                    ds.tt.notify('File %r is busy, skipping' % path)
                elif e.errno == errno.EACCES:
                    # Could be SELinux or immutability
                    ds.tt.notify('Access denied on %r, skipping' % path)
                elif e.errno == errno.ENOENT:
                    # The file was moved or unlinked by a racing process
                    ds.tt.notify('File %r may have moved, skipping' % path)
                else:
                    raise
                ds.skip(inode)
                continue

            # It's not completely guaranteed we have the right inode,
            # there may still be race conditions at this point.
            # Gets re-checked below (tell and fstat).
            fd = afile.fileno()
            fd_inodes[fd] = inode
            fd_names[fd] = path
            files.append(afile)
            fds.append(fd)

        with ExitStack() as stack:
            for afile in files:
                stack.enter_context(closing(afile))
            # Enter this context last
            immutability = stack.enter_context(ImmutableFDs(fds))

            # With a false positive, some kind of cmp pass that compares
            # all files at once might be more efficient that hashing.
            for afile in files:
                fd = afile.fileno()
                inode = fd_inodes[fd]
                if fd in immutability.fds_in_write_use:
                    ds.tt.notify('File %r is in use, skipping' % fd_names[fd])
                    ds.skip(inode)
                    continue
                hasher = hashlib.sha1()
                for buf in iter(lambda: afile.read(BUFSIZE), b''):
                    hasher.update(buf)

                # Gets rid of a race condition
                st = os.fstat(fd)
                if st.st_ino != inode.ino:
                    ds.skip(inode)
                    continue
                if st.st_dev != inode.vol.live.st_dev:
                    ds.skip(inode)
                    continue

                size1 = afile.tell()
                if size1 != size:
                    if size1 < inode.vol.size_cutoff:
                        # if we didn't delete this inode, it would cause
                        # spurious comm groups in all future invocations.
                        ds.sess.delete(inode)
                    else:
                        ds.skip(inode)
                    continue

                by_hash[hasher.digest()].append(afile)
                ds.tt.update(fhash=None)

            for fileset in by_hash.itervalues():
                dedup_fileset(ds, fileset, fd_names, fd_inodes, size)


def dedup_fileset(ds, fileset, fd_names, fd_inodes, size):
    if len(fileset) < 2:
        return
    sfile = fileset[0]
    sfd = sfile.fileno()
    sdesc = fd_inodes[sfd].vol.live.describe_path(fd_names[sfd])
    if ds.defrag:
        btrfs_defragment(sfd)
    dfiles = fileset[1:]
    dfiles_successful = []
    for dfile in dfiles:
        dfd = dfile.fileno()
        ddesc = fd_inodes[dfd].vol.live.describe_path(
            fd_names[dfd])
        if not cmp_files(sfile, dfile):
            # Probably a bug since we just used a crypto hash
            ds.tt.notify('Files differ: %r %r' % (sdesc, ddesc))
            assert False, (sdesc, ddesc)
            return
        if clone_data(dest=dfd, src=sfd, check_first=True):
            ds.tt.notify(
                'Deduplicated:\n- %r\n- %r' % (sdesc, ddesc))
            dfiles_successful.append(dfile)
            ds.space_gain += size
            ds.tt.update(space_gain=ds.space_gain)
        elif False:
            # Often happens when there are multiple files with
            # the same extents, plus one with the same size and
            # mini-hash but a difference elsewhere.
            # We hash the same extents multiple times, but
            # I assume the data is shared in the vfs cache.
            ds.tt.notify(
                'Did not deduplicate (same extents): %r %r' % (
                    sdesc, ddesc))
    if dfiles_successful:
        evt = DedupEvent(
            fs=ds.fs.impl, item_size=size, created=system_now())
        ds.sess.add(evt)
        for afile in [sfile] + dfiles_successful:
            inode = fd_inodes[afile.fileno()]
            evti = DedupEventInode(
                event=evt, ino=inode.ino, vol=inode.vol)
            ds.sess.add(evti)
        ds.sess.commit()


########NEW FILE########
__FILENAME__ = __main__
# vim: set fileencoding=utf-8 sw=4 ts=4 et :

# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import argparse
import errno
import os
import sqlalchemy
import sys
import warnings
import xdg.BaseDirectory  # pyxdg, apt:python-xdg

from collections import defaultdict, OrderedDict
from contextlib import closing
from contextlib2 import ExitStack
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
from uuid import UUID

from .platform.btrfs import find_new, get_root_generation
from .platform.ioprio import set_idle_priority
from .platform.syncfs import syncfs

from .dedup import dedup_same, FilesInUseError
from .filesystem import show_vols, WholeFS, NotAVolume
from .migrations import upgrade_schema
from .termupdates import TermTemplate
from .tracking import (
    track_updated_files, dedup_tracked, reset_vol, fake_updates,
    annotated_inodes_by_size)


APP_NAME = 'bedup'


def cmd_dedup_files(args):
    try:
        return dedup_same(args.source, args.dests, args.defrag)
    except FilesInUseError as exn:
        exn.describe(sys.stderr)
        return 1


def cmd_find_new(args):
    volume_fd = os.open(args.volume, os.O_DIRECTORY)
    if args.zero_terminated:
        sep = '\0'
    else:
        sep = '\n'
    find_new(volume_fd, args.generation, sys.stdout, terse=args.terse, sep=sep)


def cmd_show_vols(args):
    sess = get_session(args)
    whole_fs = WholeFS(sess)
    show_vols(whole_fs, args.fsuuid_or_device, args.show_deleted)


def sql_setup(dbapi_con, con_record):
    cur = dbapi_con.cursor()
    # Uncripple the SQL implementation
    cur.execute('PRAGMA foreign_keys = ON')
    cur.execute('PRAGMA foreign_keys')
    val = cur.fetchone()
    assert val == (1,), val

    # So that writers do not block readers
    # https://www.sqlite.org/wal.html
    cur.execute('PRAGMA journal_mode = WAL')
    cur.execute('PRAGMA journal_mode')
    val = cur.fetchone()
    # SQLite 3.7 is required
    assert val == ('wal',), val


def get_session(args):
    if args.db_path is None:
        data_dir = xdg.BaseDirectory.save_data_path(APP_NAME)
        args.db_path = os.path.join(data_dir, 'db.sqlite')
    url = sqlalchemy.engine.url.URL('sqlite', database=args.db_path)
    engine = sqlalchemy.engine.create_engine(
        url, echo=args.verbose_sql, poolclass=SingletonThreadPool)
    sqlalchemy.event.listen(engine, 'connect', sql_setup)
    upgrade_schema(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    return sess


def vol_cmd(args):
    if args.command == 'dedup-vol':
        sys.stderr.write(
            "The dedup-vol command is deprecated, please use dedup.\n")
        args.command = 'dedup'
        args.defrag = False
    elif args.command == 'reset' and not args.filter:
        sys.stderr.write("You need to list volumes explicitly.\n")
        return 1

    with ExitStack() as stack:
        tt = stack.enter_context(closing(TermTemplate()))
        # Adds about 1s to cold startup
        sess = get_session(args)
        whole_fs = WholeFS(sess, size_cutoff=args.size_cutoff)
        stack.enter_context(closing(whole_fs))

        if not args.filter:
            vols = whole_fs.load_all_writable_vols(tt)
        else:
            vols = OrderedDict()
            for filt in args.filter:
                if filt.startswith('vol:/'):
                    volpath = filt[4:]
                    try:
                        filt_vols = whole_fs.load_vols(
                            [volpath], tt, recurse=False)
                    except NotAVolume:
                        sys.stderr.write(
                            'Path doesn\'t point to a btrfs volume: %r\n'
                            % (volpath,))
                        return 1
                elif filt.startswith('/'):
                    if os.path.realpath(filt).startswith('/dev/'):
                        filt_vols = whole_fs.load_vols_for_device(filt, tt)
                    else:
                        volpath = filt
                        try:
                            filt_vols = whole_fs.load_vols(
                                [volpath], tt, recurse=True)
                        except NotAVolume:
                            sys.stderr.write(
                                'Path doesn\'t point to a btrfs volume: %r\n'
                                % (volpath,))
                            return 1
                else:
                    try:
                        uuid = UUID(hex=filt)
                    except ValueError:
                        sys.stderr.write(
                            'Filter format not recognised: %r\n' % filt)
                        return 1
                    filt_vols = whole_fs.load_vols_for_fs(
                        whole_fs.get_fs(uuid), tt)
                for vol in filt_vols:
                    vols[vol] = True

        # XXX should group by mountpoint instead.
        # Only a problem when called with volume names instead of an fs filter.
        vols_by_fs = defaultdict(list)

        if args.command == 'reset':
            for vol in vols:
                if user_confirmation(
                    'Reset tracking status of {}?'.format(vol), False
                ):
                    reset_vol(sess, vol)
                    print('Reset of {} done'.format(vol))

        if args.command in ('scan', 'dedup'):
            set_idle_priority()
            for vol in vols:
                if args.flush:
                    tt.format('{elapsed} Flushing %s' % (vol,))
                    syncfs(vol.fd)
                    tt.format(None)
                track_updated_files(sess, vol, tt)
                vols_by_fs[vol.fs].append(vol)

        if args.command == 'dedup':
            if args.groupby == 'vol':
                for vol in vols:
                    tt.notify('Deduplicating volume %s' % vol)
                    dedup_tracked(sess, [vol], tt, defrag=args.defrag)
            elif args.groupby == 'mpoint':
                for fs, volset in vols_by_fs.iteritems():
                    tt.notify('Deduplicating filesystem %s' % fs)
                    dedup_tracked(sess, volset, tt, defrag=args.defrag)
            else:
                assert False, args.groupby

        # For safety only.
        # The methods we call from the tracking module are expected to commit.
        sess.commit()


def cmd_generation(args):
    volume_fd = os.open(args.volume, os.O_DIRECTORY)
    if args.flush:
        syncfs(volume_fd)
    generation = get_root_generation(volume_fd)
    print('%d' % generation)


def user_confirmation(message, default):
    # default='n' would be an easy mistake to make
    assert default is bool(default)

    yes_values = 'y yes'.split()
    no_values = 'n no'.split()
    if default:
        choices = 'Y/n'
        yes_values.append('')
    else:
        choices = 'y/N'
        no_values.append('')

    while True:
        try:
            choice = raw_input("%s (%s) " % (message, choices)).lower().strip()
        except EOFError:
            # non-interactive
            choice = ''
        if choice in yes_values:
            return True
        elif choice in no_values:
            return False


def cmd_forget_fs(args):
    sess = get_session(args)
    whole_fs = WholeFS(sess)
    filesystems = [
        whole_fs.get_fs_existing(UUID(hex=uuid)) for uuid in args.uuid]
    for fs in filesystems:
        if not user_confirmation('Wipe all data about fs %s?' % fs, False):
            continue
        for vol in fs._impl.volumes:
            # A lot of things will cascade
            sess.delete(vol)
        sess.delete(fs._impl)
        sess.commit()
        print('Wiped all data about %s' % fs)


def cmd_size_lookup(args):
    sess = get_session(args)
    whole_fs = WholeFS(sess)
    if args.zero_terminated:
        end ='\0'
    else:
        end = '\n'
    for vol, rp, inode in annotated_inodes_by_size(whole_fs, args.size):
        print(vol.describe_path(rp), end=end)

    # We've deleted some stale inodes
    sess.commit()


def cmd_shell(args):
    sess = get_session(args)
    whole_fs = WholeFS(sess)
    from . import model
    try:
        from IPython import embed
    except ImportError:
        sys.stderr.write(
            'Please install bedup[interactive] for this feature\n')
        return 1
    with warnings.catch_warnings():
        warnings.simplefilter('default')
        warnings.filterwarnings('ignore', module='IPython')
        embed()


def cmd_fake_updates(args):
    sess = get_session(args)
    faked = fake_updates(sess, args.max_events)
    sess.commit()
    print('Faked about %d commonality clusters' % faked)


def sql_flags(parser):
    parser.add_argument(
        '--db-path', dest='db_path',
        help='Override the location of the sqlite database')
    parser.add_argument(
        '--verbose-sql', action='store_true', dest='verbose_sql',
        help='Print SQL statements being executed')


def vol_flags(parser):
    parser.add_argument(
        'filter', nargs='*',
        help='List filesystem uuids, devices, or volume mountpoints to '
        'select which volumes are included. '
        'Prefix a volume mountpoint with vol: if you do not want '
        'subvolumes to be included.')
    sql_flags(parser)
    parser.add_argument(
        '--size-cutoff', type=int, dest='size_cutoff',
        help='Change the minimum size (in bytes) of tracked files '
        'for the listed volumes. '
        'Lowering the cutoff will trigger a partial rescan of older files.')
    parser.add_argument(
        '--no-crossvol', action='store_const',
        const='vol', default='mpoint', dest='groupby',
        help='This option disables cross-volume deduplication. '
        'This may be useful with pre-3.6 kernels.')


def scan_flags(parser):
    vol_flags(parser)
    parser.add_argument(
        '--flush', action='store_true', dest='flush',
        help='Flush outstanding data using syncfs before scanning volumes')


def is_in_path(cmd):
    # See shutil.which in Python 3.3
    return any(
        os.path.exists(el + '/' + cmd) for el in os.environ['PATH'].split(':'))


def main(argv):
    progname = 'bedup' if is_in_path('bedup') else 'python -m bedup'
    parser = argparse.ArgumentParser(prog=progname)
    parser.add_argument(
        '--debug', action='store_true', help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest='command', metavar='command')

    sp_scan_vol = commands.add_parser(
        'scan', help='Scan', description="""
Scans volumes to keep track of potentially duplicated files.""")
    sp_scan_vol.set_defaults(action=vol_cmd)
    scan_flags(sp_scan_vol)

    # In Python 3.2+ we can add aliases here.
    # Hidden aliases doesn't seem supported though.
    sp_dedup_vol = commands.add_parser(
        'dedup', help='Scan and deduplicate', description="""
Runs scan, then deduplicates identical files.""")
    sp_dedup_vol.set_defaults(action=vol_cmd)
    scan_flags(sp_dedup_vol)
    sp_dedup_vol.add_argument(
        '--defrag', action='store_true',
        help='Defragment files that are going to be deduplicated')

    # An alias so as not to break btrfs-time-machine.
    # help='' is unset, which should make it (mostly) invisible.
    sp_dedup_vol_compat = commands.add_parser(
        'dedup-vol', description="""
A deprecated alias for the 'dedup' command.""")
    sp_dedup_vol_compat.set_defaults(action=vol_cmd)
    scan_flags(sp_dedup_vol_compat)

    sp_reset_vol = commands.add_parser(
        'reset', help='Reset tracking metadata', description="""
Reset tracking data for the listed volumes. Mostly useful for testing.""")
    sp_reset_vol.set_defaults(action=vol_cmd)
    vol_flags(sp_reset_vol)

    sp_show_vols = commands.add_parser(
        'show', help='Show metadata overview', description="""
Shows filesystems and volumes with their tracking status.""")
    sp_show_vols.set_defaults(action=cmd_show_vols)
    sp_show_vols.add_argument('fsuuid_or_device', nargs='?')
    sp_show_vols.add_argument(
        '--show-deleted', dest='show_deleted', action='store_true',
        help='Show volumes that have been deleted')
    sql_flags(sp_show_vols)

    sp_find_new = commands.add_parser(
        'find-new', help='List changed files', description="""
lists changes to volume since generation

This is a reimplementation of btrfs find-new,
modified to include directories as well.""")
    sp_find_new.set_defaults(action=cmd_find_new)
    sp_find_new.add_argument(
        '-0|--zero-terminated', dest='zero_terminated', action='store_true',
        help='Use a NUL character as the line separator')
    sp_find_new.add_argument(
        '--terse', dest='terse', action='store_true', help='Print names only')
    sp_find_new.add_argument('volume', help='Volume to search')
    sp_find_new.add_argument(
        'generation', type=int, nargs='?', default=0,
        help='Only show items modified at generation or a newer transaction')

    sp_forget_fs = commands.add_parser(
        'forget-fs', help='Wipe all metadata', description="""
Wipe all metadata for the listed filesystems.
Useful if the filesystems don't exist anymore.""")
    sp_forget_fs.set_defaults(action=cmd_forget_fs)
    sp_forget_fs.add_argument('uuid', nargs='+', help='Btrfs filesystem uuids')
    sql_flags(sp_forget_fs)

    sp_dedup_files = commands.add_parser(
        'dedup-files', help='Deduplicate listed', description="""
Freezes listed files, checks them for being identical,
and projects the extents of the first file onto the other files.

The effects are visible with filefrag -v (apt:e2fsprogs),
which displays the extent map of files.
        """.strip())
    sp_dedup_files.set_defaults(action=cmd_dedup_files)
    sp_dedup_files.add_argument('source', metavar='SRC', help='Source file')
    sp_dedup_files.add_argument(
        'dests', metavar='DEST', nargs='+', help='Dest files')
    # Don't forget to also set new options in the dedup-vol test in vol_cmd
    sp_dedup_files.add_argument(
        '--defrag', action='store_true',
        help='Defragment the source file first')

    sp_generation = commands.add_parser(
        'generation', help='Display volume generation', description="""
Display the btrfs generation of VOLUME.""")
    sp_generation.set_defaults(action=cmd_generation)
    sp_generation.add_argument('volume', help='Btrfs volume')
    sp_generation.add_argument(
        '--flush', action='store_true', dest='flush',
        help='Flush outstanding data using syncfs before lookup')

    sp_size_lookup = commands.add_parser(
        'size-lookup', help='Look up inodes by size', description="""
List tracked inodes with a given size.""")
    sp_size_lookup.set_defaults(action=cmd_size_lookup)
    sp_size_lookup.add_argument('size', type=int)
    sp_size_lookup.add_argument(
        '-0|--zero-terminated', dest='zero_terminated', action='store_true',
        help='Use a NUL character as the line separator')
    sql_flags(sp_size_lookup)

    sp_shell = commands.add_parser(
        'shell', description="""
Run an interactive shell (useful for prototyping).""")
    sp_shell.set_defaults(action=cmd_shell)
    sql_flags(sp_shell)

    sp_fake_updates = commands.add_parser(
        'fake-updates', description="""
Fake inode updates from the latest dedup events (useful for benchmarking).""")
    sp_fake_updates.set_defaults(action=cmd_fake_updates)
    sp_fake_updates.add_argument('max_events', type=int)
    sql_flags(sp_fake_updates)

    # Give help when no subcommand is given
    if not argv[1:]:
        parser.print_help()
        return

    args = parser.parse_args(argv[1:])

    if args.debug:
        try:
            from ipdb import launch_ipdb_on_exception
        except ImportError:
            sys.stderr.write(
                'Please install bedup[interactive] for this feature\n')
            return 1
        with launch_ipdb_on_exception():
            # Handle all warnings as errors.
            # Overrides the default filter that ignores deprecations
            # and prints the rest.
            warnings.simplefilter('error')
            return args.action(args)
    else:
        try:
            return args.action(args)
        except IOError as err:
            if err.errno == errno.EPERM:
                sys.stderr.write(
                    "You need to run this command as root.\n")
                return 1
            raise


def script_main():
    # site.py takes about 1s before main gets called
    sys.exit(main(sys.argv))


if __name__ == '__main__':
    script_main()


########NEW FILE########
