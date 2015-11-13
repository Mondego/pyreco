__FILENAME__ = fuse
# Copyright (c) 2008 Giorgos Verigakis <verigak@gmail.com>
# 
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import division

from ctypes import *
from ctypes.util import find_library
from errno import *
from functools import partial
from os import strerror
from platform import machine, system
from stat import S_IFDIR
from traceback import print_exc


class c_timespec(Structure):
    _fields_ = [('tv_sec', c_long), ('tv_nsec', c_long)]

class c_utimbuf(Structure):
    _fields_ = [('actime', c_timespec), ('modtime', c_timespec)]

class c_stat(Structure):
    pass    # Platform dependent

_system = system()
if _system in ('Darwin', 'FreeBSD'):
    _libiconv = CDLL(find_library("iconv"), RTLD_GLOBAL)     # libfuse dependency
    ENOTSUP = 45
    c_dev_t = c_int32
    c_fsblkcnt_t = c_ulong
    c_fsfilcnt_t = c_ulong
    c_gid_t = c_uint32
    c_mode_t = c_uint16
    c_off_t = c_int64
    c_pid_t = c_int32
    c_uid_t = c_uint32
    setxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
        c_size_t, c_int, c_uint32)
    getxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
        c_size_t, c_uint32)
    c_stat._fields_ = [
        ('st_dev', c_dev_t),
        ('st_ino', c_uint32),
        ('st_mode', c_mode_t),
        ('st_nlink', c_uint16),
        ('st_uid', c_uid_t),
        ('st_gid', c_gid_t),
        ('st_rdev', c_dev_t),
        ('st_atimespec', c_timespec),
        ('st_mtimespec', c_timespec),
        ('st_ctimespec', c_timespec),
        ('st_size', c_off_t),
        ('st_blocks', c_int64),
        ('st_blksize', c_int32)]
elif _system == 'Linux':
    ENOTSUP = 95
    c_dev_t = c_ulonglong
    c_fsblkcnt_t = c_ulonglong
    c_fsfilcnt_t = c_ulonglong
    c_gid_t = c_uint
    c_mode_t = c_uint
    c_off_t = c_longlong
    c_pid_t = c_int
    c_uid_t = c_uint
    setxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte), c_size_t, c_int)
    getxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte), c_size_t)
    
    _machine = machine()
    if _machine == 'x86_64':
        c_stat._fields_ = [
            ('st_dev', c_dev_t),
            ('st_ino', c_ulong),
            ('st_nlink', c_ulong),
            ('st_mode', c_mode_t),
            ('st_uid', c_uid_t),
            ('st_gid', c_gid_t),
            ('__pad0', c_int),
            ('st_rdev', c_dev_t),
            ('st_size', c_off_t),
            ('st_blksize', c_long),
            ('st_blocks', c_long),
            ('st_atimespec', c_timespec),
            ('st_mtimespec', c_timespec),
            ('st_ctimespec', c_timespec)]
    elif _machine == 'ppc':
        c_stat._fields_ = [
            ('st_dev', c_dev_t),
            ('st_ino', c_ulonglong),
            ('st_mode', c_mode_t),
            ('st_nlink', c_uint),
            ('st_uid', c_uid_t),
            ('st_gid', c_gid_t),
            ('st_rdev', c_dev_t),
            ('__pad2', c_ushort),
            ('st_size', c_off_t),
            ('st_blksize', c_long),
            ('st_blocks', c_longlong),
            ('st_atimespec', c_timespec),
            ('st_mtimespec', c_timespec),
            ('st_ctimespec', c_timespec)]
    else:
        # i686, use as fallback for everything else
        c_stat._fields_ = [
            ('st_dev', c_dev_t),
            ('__pad1', c_ushort),
            ('__st_ino', c_ulong),
            ('st_mode', c_mode_t),
            ('st_nlink', c_uint),
            ('st_uid', c_uid_t),
            ('st_gid', c_gid_t),
            ('st_rdev', c_dev_t),
            ('__pad2', c_ushort),
            ('st_size', c_off_t),
            ('st_blksize', c_long),
            ('st_blocks', c_longlong),
            ('st_atimespec', c_timespec),
            ('st_mtimespec', c_timespec),
            ('st_ctimespec', c_timespec),
            ('st_ino', c_ulonglong)]
else:
    raise NotImplementedError('%s is not supported.' % _system)


class c_statvfs(Structure):
    _fields_ = [
        ('f_bsize', c_ulong),
        ('f_frsize', c_ulong),
        ('f_blocks', c_fsblkcnt_t),
        ('f_bfree', c_fsblkcnt_t),
        ('f_bavail', c_fsblkcnt_t),
        ('f_files', c_fsfilcnt_t),
        ('f_ffree', c_fsfilcnt_t),
        ('f_favail', c_fsfilcnt_t)]

if _system == 'FreeBSD':
    c_fsblkcnt_t = c_uint64
    c_fsfilcnt_t = c_uint64
    setxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte), c_size_t, c_int)
    getxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte), c_size_t)
    class c_statvfs(Structure):
        _fields_ = [
            ('f_bavail', c_fsblkcnt_t),
            ('f_bfree', c_fsblkcnt_t),
            ('f_blocks', c_fsblkcnt_t),
            ('f_favail', c_fsfilcnt_t),
            ('f_ffree', c_fsfilcnt_t),
            ('f_files', c_fsfilcnt_t),
            ('f_bsize', c_ulong),
            ('f_flag', c_ulong),
            ('f_frsize', c_ulong)]

class fuse_file_info(Structure):
    _fields_ = [
        ('flags', c_int),
        ('fh_old', c_ulong),
        ('writepage', c_int),
        ('direct_io', c_uint, 1),
        ('keep_cache', c_uint, 1),
        ('flush', c_uint, 1),
        ('padding', c_uint, 29),
        ('fh', c_uint64),
        ('lock_owner', c_uint64)]

class fuse_context(Structure):
    _fields_ = [
        ('fuse', c_voidp),
        ('uid', c_uid_t),
        ('gid', c_gid_t),
        ('pid', c_pid_t),
        ('private_data', c_voidp)]

class fuse_operations(Structure):
    _fields_ = [
        ('getattr', CFUNCTYPE(c_int, c_char_p, POINTER(c_stat))),
        ('readlink', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t)),
        ('getdir', c_voidp),    # Deprecated, use readdir
        ('mknod', CFUNCTYPE(c_int, c_char_p, c_mode_t, c_dev_t)),
        ('mkdir', CFUNCTYPE(c_int, c_char_p, c_mode_t)),
        ('unlink', CFUNCTYPE(c_int, c_char_p)),
        ('rmdir', CFUNCTYPE(c_int, c_char_p)),
        ('symlink', CFUNCTYPE(c_int, c_char_p, c_char_p)),
        ('rename', CFUNCTYPE(c_int, c_char_p, c_char_p)),
        ('link', CFUNCTYPE(c_int, c_char_p, c_char_p)),
        ('chmod', CFUNCTYPE(c_int, c_char_p, c_mode_t)),
        ('chown', CFUNCTYPE(c_int, c_char_p, c_uid_t, c_gid_t)),
        ('truncate', CFUNCTYPE(c_int, c_char_p, c_off_t)),
        ('utime', c_voidp),     # Deprecated, use utimens
        ('open', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('read', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t, c_off_t,
            POINTER(fuse_file_info))),
        ('write', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t, c_off_t,
            POINTER(fuse_file_info))),
        ('statfs', CFUNCTYPE(c_int, c_char_p, POINTER(c_statvfs))),
        ('flush', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('release', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('fsync', CFUNCTYPE(c_int, c_char_p, c_int, POINTER(fuse_file_info))),
        ('setxattr', setxattr_t),
        ('getxattr', getxattr_t),
        ('listxattr', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t)),
        ('removexattr', CFUNCTYPE(c_int, c_char_p, c_char_p)),
        ('opendir', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('readdir', CFUNCTYPE(c_int, c_char_p, c_voidp, CFUNCTYPE(c_int, c_voidp,
            c_char_p, POINTER(c_stat), c_off_t), c_off_t, POINTER(fuse_file_info))),
        ('releasedir', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('fsyncdir', CFUNCTYPE(c_int, c_char_p, c_int, POINTER(fuse_file_info))),
        ('init', CFUNCTYPE(c_voidp, c_voidp)),
        ('destroy', CFUNCTYPE(c_voidp, c_voidp)),
        ('access', CFUNCTYPE(c_int, c_char_p, c_int)),
        ('create', CFUNCTYPE(c_int, c_char_p, c_mode_t, POINTER(fuse_file_info))),
        ('ftruncate', CFUNCTYPE(c_int, c_char_p, c_off_t, POINTER(fuse_file_info))),
        ('fgetattr', CFUNCTYPE(c_int, c_char_p, POINTER(c_stat),
            POINTER(fuse_file_info))),
        ('lock', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info), c_int, c_voidp)),
        ('utimens', CFUNCTYPE(c_int, c_char_p, POINTER(c_utimbuf))),
        ('bmap', CFUNCTYPE(c_int, c_char_p, c_size_t, POINTER(c_ulonglong)))]


def time_of_timespec(ts):
    return ts.tv_sec + ts.tv_nsec / 10 ** 9

def set_st_attrs(st, attrs):
    for key, val in attrs.items():
        if key in ('st_atime', 'st_mtime', 'st_ctime'):
            timespec = getattr(st, key + 'spec')
            timespec.tv_sec = int(val)
            timespec.tv_nsec = int((val - timespec.tv_sec) * 10 ** 9)
        elif hasattr(st, key):
            setattr(st, key, val)


_libfuse_path = find_library('fuse')
if not _libfuse_path:
    raise EnvironmentError('Unable to find libfuse')
_libfuse = CDLL(_libfuse_path)
_libfuse.fuse_get_context.restype = POINTER(fuse_context)


def fuse_get_context():
    """Returns a (uid, gid, pid) tuple"""
    ctxp = _libfuse.fuse_get_context()
    ctx = ctxp.contents
    return ctx.uid, ctx.gid, ctx.pid


class FuseOSError(OSError):
    def __init__(self, errno):
        super(FuseOSError, self).__init__(errno, strerror(errno))


class FUSE(object):
    """This class is the lower level interface and should not be subclassed
       under normal use. Its methods are called by fuse.
       Assumes API version 2.6 or later."""
    
    def __init__(self, operations, mountpoint, raw_fi=False, **kwargs):
        """Setting raw_fi to True will cause FUSE to pass the fuse_file_info
           class as is to Operations, instead of just the fh field.
           This gives you access to direct_io, keep_cache, etc."""
        
        self.operations = operations
        self.raw_fi = raw_fi
        args = ['fuse']
        if kwargs.pop('foreground', False):
            args.append('-f')
        if kwargs.pop('debug', False):
            args.append('-d')
        if kwargs.pop('nothreads', False):
            args.append('-s')
        kwargs.setdefault('fsname', operations.__class__.__name__)
        args.append('-o')
        args.append(','.join(key if val == True else '%s=%s' % (key, val)
            for key, val in kwargs.items()))
        args.append(mountpoint)
        argv = (c_char_p * len(args))(*args)
        
        fuse_ops = fuse_operations()
        for name, prototype in fuse_operations._fields_:
            if prototype != c_voidp and getattr(operations, name, None):
                op = partial(self._wrapper_, getattr(self, name))
                setattr(fuse_ops, name, prototype(op))
        err = _libfuse.fuse_main_real(len(args), argv, pointer(fuse_ops),
            sizeof(fuse_ops), None)            
        del self.operations     # Invoke the destructor
        if err:
            raise RuntimeError(err)
    
    def _wrapper_(self, func, *args, **kwargs):
        """Decorator for the methods that follow"""
        try:
            return func(*args, **kwargs) or 0
        except OSError, e:
            return -(e.errno or EFAULT)
        except:
            print_exc()
            return -EFAULT
    
    def getattr(self, path, buf):
        return self.fgetattr(path, buf, None)
    
    def readlink(self, path, buf, bufsize):
        ret = self.operations('readlink', path)
        data = create_string_buffer(ret[:bufsize - 1])
        memmove(buf, data, len(data))
        return 0
    
    def mknod(self, path, mode, dev):
        return self.operations('mknod', path, mode, dev)
    
    def mkdir(self, path, mode):
        return self.operations('mkdir', path, mode)
    
    def unlink(self, path):
        return self.operations('unlink', path)
    
    def rmdir(self, path):
        return self.operations('rmdir', path)
    
    def symlink(self, source, target):
        return self.operations('symlink', target, source)
    
    def rename(self, old, new):
        return self.operations('rename', old, new)
    
    def link(self, source, target):
        return self.operations('link', target, source)
    
    def chmod(self, path, mode):
        return self.operations('chmod', path, mode)
    
    def chown(self, path, uid, gid):
        # Check if any of the arguments is a -1 that has overflowed
        if c_uid_t(uid + 1).value == 0:
            uid = -1
        if c_gid_t(gid + 1).value == 0:
            gid = -1
        return self.operations('chown', path, uid, gid)
    
    def truncate(self, path, length):
        return self.operations('truncate', path, length)
    
    def open(self, path, fip):
        fi = fip.contents
        if self.raw_fi:
            return self.operations('open', path, fi)
        else:
            fi.fh = self.operations('open', path, fi.flags)
            return 0
    
    def read(self, path, buf, size, offset, fip):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        ret = self.operations('read', path, size, offset, fh)
        if not ret:
            return 0
        data = create_string_buffer(ret[:size], size)
        memmove(buf, data, size)
        return size
    
    def write(self, path, buf, size, offset, fip):
        data = string_at(buf, size)
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('write', path, data, offset, fh)
    
    def statfs(self, path, buf):
        stv = buf.contents
        attrs = self.operations('statfs', path)
        for key, val in attrs.items():
            if hasattr(stv, key):
                setattr(stv, key, val)
        return 0
    
    def flush(self, path, fip):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('flush', path, fh)
    
    def release(self, path, fip):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('release', path, fh)
    
    def fsync(self, path, datasync, fip):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('fsync', path, datasync, fh)
    
    def setxattr(self, path, name, value, size, options, *args):
        data = string_at(value, size)
        return self.operations('setxattr', path, name, data, options, *args)
    
    def getxattr(self, path, name, value, size, *args):
        ret = self.operations('getxattr', path, name, *args)
        retsize = len(ret)
        buf = create_string_buffer(ret, retsize)    # Does not add trailing 0
        if bool(value):
            if retsize > size:
                return -ERANGE
            memmove(value, buf, retsize)
        return retsize
    
    def listxattr(self, path, namebuf, size):
        ret = self.operations('listxattr', path)
        buf = create_string_buffer('\x00'.join(ret)) if ret else ''
        bufsize = len(buf)
        if bool(namebuf):
            if bufsize > size:
                return -ERANGE
            memmove(namebuf, buf, bufsize)
        return bufsize
    
    def removexattr(self, path, name):
        return self.operations('removexattr', path, name)
    
    def opendir(self, path, fip):
        # Ignore raw_fi
        fip.contents.fh = self.operations('opendir', path)
        return 0
    
    def readdir(self, path, buf, filler, offset, fip):
        # Ignore raw_fi
        for item in self.operations('readdir', path, fip.contents.fh):
            if isinstance(item, str):
                name, st, offset = item, None, 0
            else:
                name, attrs, offset = item
                if attrs:
                    st = c_stat()
                    set_st_attrs(st, attrs)
                else:
                    st = None
            if filler(buf, name, st, offset) != 0:
                break
        return 0
    
    def releasedir(self, path, fip):
        # Ignore raw_fi
        return self.operations('releasedir', path, fip.contents.fh)
    
    def fsyncdir(self, path, datasync, fip):
        # Ignore raw_fi
        return self.operations('fsyncdir', path, datasync, fip.contents.fh)
    
    def init(self, conn):
        return self.operations('init', '/')
    
    def destroy(self, private_data):
        return self.operations('destroy', '/')
    
    def access(self, path, amode):
        return self.operations('access', path, amode)
    
    def create(self, path, mode, fip):
        fi = fip.contents
        if self.raw_fi:
            return self.operations('create', path, mode, fi)
        else:
            fi.fh = self.operations('create', path, mode)
            return 0
    
    def ftruncate(self, path, length, fip):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('truncate', path, length, fh)
    
    def fgetattr(self, path, buf, fip):
        memset(buf, 0, sizeof(c_stat))
        st = buf.contents
        fh = fip and (fip.contents if self.raw_fi else fip.contents.fh)
        attrs = self.operations('getattr', path, fh)
        set_st_attrs(st, attrs)
        return 0
    
    def lock(self, path, fip, cmd, lock):
        fh = fip.contents if self.raw_fi else fip.contents.fh
        return self.operations('lock', path, fh, cmd, lock)
    
    def utimens(self, path, buf):
        if buf:
            atime = time_of_timespec(buf.contents.actime)
            mtime = time_of_timespec(buf.contents.modtime)
            times = (atime, mtime)
        else:
            times = None
        return self.operations('utimens', path, times)
    
    def bmap(self, path, blocksize, idx):
        return self.operations('bmap', path, blocksize, idx)


class Operations(object):
    """This class should be subclassed and passed as an argument to FUSE on
       initialization. All operations should raise a FuseOSError exception
       on error.
       
       When in doubt of what an operation should do, check the FUSE header
       file or the corresponding system call man page."""
    
    def __call__(self, op, *args):
        if not hasattr(self, op):
            raise FuseOSError(EFAULT)
        return getattr(self, op)(*args)
        
    def access(self, path, amode):
        return 0
    
    bmap = None
    
    def chmod(self, path, mode):
        raise FuseOSError(EROFS)
    
    def chown(self, path, uid, gid):
        raise FuseOSError(EROFS)
    
    def create(self, path, mode, fi=None):
        """When raw_fi is False (default case), fi is None and create should
           return a numerical file handle.
           When raw_fi is True the file handle should be set directly by create
           and return 0."""
        raise FuseOSError(EROFS)
    
    def destroy(self, path):
        """Called on filesystem destruction. Path is always /"""
        pass
    
    def flush(self, path, fh):
        return 0
    
    def fsync(self, path, datasync, fh):
        return 0
    
    def fsyncdir(self, path, datasync, fh):
        return 0
    
    def getattr(self, path, fh=None):
        """Returns a dictionary with keys identical to the stat C structure
           of stat(2).
           st_atime, st_mtime and st_ctime should be floats.
           NOTE: There is an incombatibility between Linux and Mac OS X concerning
           st_nlink of directories. Mac OS X counts all files inside the directory,
           while Linux counts only the subdirectories."""
        
        if path != '/':
            raise FuseOSError(ENOENT)
        return dict(st_mode=(S_IFDIR | 0755), st_nlink=2)
    
    def getxattr(self, path, name, position=0):
        raise FuseOSError(ENOTSUP)
    
    def init(self, path):
        """Called on filesystem initialization. Path is always /
           Use it instead of __init__ if you start threads on initialization."""
        pass
    
    def link(self, target, source):
        raise FuseOSError(EROFS)
    
    def listxattr(self, path):
        return []
        
    lock = None
    
    def mkdir(self, path, mode):
        raise FuseOSError(EROFS)
    
    def mknod(self, path, mode, dev):
        raise FuseOSError(EROFS)
    
    def open(self, path, flags):
        """When raw_fi is False (default case), open should return a numerical
           file handle.
           When raw_fi is True the signature of open becomes:
               open(self, path, fi)
           and the file handle should be set directly."""
        return 0
    
    def opendir(self, path):
        """Returns a numerical file handle."""
        return 0
    
    def read(self, path, size, offset, fh):
        """Returns a string containing the data requested."""
        raise FuseOSError(EIO)
    
    def readdir(self, path, fh):
        """Can return either a list of names, or a list of (name, attrs, offset)
           tuples. attrs is a dict as in getattr."""
        return ['.', '..']
    
    def readlink(self, path):
        raise FuseOSError(ENOENT)
    
    def release(self, path, fh):
        return 0
    
    def releasedir(self, path, fh):
        return 0
    
    def removexattr(self, path, name):
        raise FuseOSError(ENOTSUP)
    
    def rename(self, old, new):
        raise FuseOSError(EROFS)
    
    def rmdir(self, path):
        raise FuseOSError(EROFS)
    
    def setxattr(self, path, name, value, options, position=0):
        raise FuseOSError(ENOTSUP)
    
    def statfs(self, path):
        """Returns a dictionary with keys identical to the statvfs C structure
           of statvfs(3).
           On Mac OS X f_bsize and f_frsize must be a power of 2 (minimum 512)."""
        return {}
    
    def symlink(self, target, source):
        raise FuseOSError(EROFS)
    
    def truncate(self, path, length, fh=None):
        raise FuseOSError(EROFS)
    
    def unlink(self, path):
        raise FuseOSError(EROFS)
    
    def utimens(self, path, times=None):
        """Times is a (atime, mtime) tuple. If None use current time."""
        return 0
    
    def write(self, path, data, offset, fh):
        raise FuseOSError(EROFS)


class LoggingMixIn:
    def __call__(self, op, path, *args):
        print '->', op, path, repr(args)
        ret = '[Unhandled Exception]'
        try:
            ret = getattr(self, op)(path, *args)
            return ret
        except OSError, e:
            ret = str(e)
            raise
        finally:
            print '<-', op, repr(ret)

########NEW FILE########
__FILENAME__ = sharebox
#!/usr/bin/env python
"""
Distributed mirroring filesystem based on git-annex.

Usage:

sharebox <mountpoint> [-o <option>]
sharebox -c [command] <mountpoint>

Options:
    -o gitdir=<path>            mandatory: path to the git directory to
                                actually store the files in.
    -o numversions=<number>     number of different versions of the same
                                file to keep. Any number <=0 means "keep
                                everything" (default 0).
    -o getall                   when there are modifications on a remote,
                                download the content of files.
    -o notifycmd                How the filesystem should notify you about
                                problems: string containing "%s" between
                                quotes (default:
                                'notify-send "sharebox" "%s"').
    -o foreground               debug mode.

Commands:
    sync                        queries all the remotes for changes and
                                merges if possible.
    merge                       the same except if there are conflicts,
                                a merge interface is spawned to help you
                                choose which files you want to keep
"""
from __future__ import with_statement

from errno import EACCES
import threading

import os
import os.path

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

import shlex
import subprocess
import time
import sys
import getopt
import time

foreground = False

def ignored(path):
    """
    Returns true if we should ignore this file, false otherwise. This
    should respect the different ways for git to ignore a file.
    """
    path_ = path[2:]
    # Exception: files that are versionned by git but that we want to
    # ignore, and special sharebox directory.
    if (path_ == '.git-attributes' or
            path_.startswith('.git/') or
            path_.startswith('.git-annex/') or
            path_ == '.command'):
        return True
    else:
        ls_options = "-c -o -d -m --full-name --exclude-standard"
        considered = subprocess.Popen(
                shlex.split('git ls-files %s -- "%s"' % (ls_options, path_)),
                stdout=subprocess.PIPE).communicate()[0].strip().split('\n')
        return path_ not in considered

def annexed(path):
    """
    returns True if the file is annexed, false otherwise
    """
    return (os.path.islink(path) and
            os.readlink(path).count('.git/annex/objects'))

def shell_do(cmd):
    """
    calls the given shell command
    """
    if foreground:
        print cmd
    p = None
    stdin = None
    for i in cmd.split('|'):
        p = subprocess.Popen(shlex.split(i), stdin=stdin, stdout=subprocess.PIPE)
        stdin = p.stdout
    p.wait()
    return not p.returncode # will return True if everything ok

class AnnexUnlock:
    """
    Annex unlock operation

    Unlocks the given path before an operation and commits the result
    after.

    usage:
    >>>  with AnnexUnlock(path):
    >>>    dosomething()
    """
    def __init__(self, path):
        self.path = path
        self.annexed = annexed(path)

    def __enter__(self):
        if self.annexed:
            shell_do('git annex unlock "%s"' % self.path)

    def __exit__(self, type, value, traceback):
        if self.annexed:
            shell_do('git annex add "%s"' % self.path)
            shell_do('git commit -m "changed %s"' % self.path)

class CopyOnWrite:
    """
    Copy on Write operation

    Returns a suited file descriptor to use as a replacement for the one
    you provide. Can clean and commit when your operation is over.

    usage:

    >>>  with CopyOnWrite(path, fh, opened_copies, unlock=False,
    >>>         commit=False):
    >>>    dosomething()

    if opened_copies already contains a file descriptor opened for write
    to use as a replacement for fh, return it

    >>>  with CopyOnWrite(path, fh, opened_copies, unlock=True,
    >>>         commit=False):
    >>>    dosomething()

    same as above, except it will unlock a copy and create the file
    descriptor if it was not found in opened_copies

    >>>  with CopyOnWrite(path, fh, opened_copies, unlock=True,
    >>>         commit=True):
    >>>    dosomething()

    same as above, except after the operation the file descriptor in
    opened_copies will be closed and deleted, and the copy will be
    commited.
    """
    def __init__(self, path, fh, opened_copies, unlock, commit):
        self.path = path
        self.fh = fh
        self.opened_copies = opened_copies
        self.unlock = unlock
        self.commit = commit

    def __enter__(self):
        if self.unlock:
            if self.opened_copies.get(self.fh, None) == None:
                if annexed(self.path):
                    shell_do('git annex unlock "%s"' % self.path)
                    self.opened_copies[self.fh] = os.open(self.path,
                            os.O_WRONLY | os.O_CREAT)
        return self.opened_copies.get(self.fh, self.fh)

    def __exit__(self, type, value, traceback):
        if self.commit:
            if self.opened_copies.get(self.fh, None) != None:
                try:
                    os.close(self.opened_copies[self.fh])
                    del self.opened_copies[self.fh]
                except KeyError:
                    pass
            if not ignored(self.path):
                shell_do('git annex add "%s"' % self.path)
                shell_do('git commit -m "changed %s"' % self.path)

class ShareBox(LoggingMixIn, Operations):
    """
    Assumes operating from the root of the managed git directory

    git-annex allows to version only links to files and to keep their
    content out of git. Once a file is added to git annex, it is replaced
    by a symbolic link to the content of the file. The content of the file
    is made read-only by git-annex so that we don't modify it by mistake.

    What does this file system:
    - It automatically adds new files to git-annex.
    - It resolves git-annex symlinks so that we see them as regular
      writable files.
    - If the content of a file is not present on the file system, it is
      requested on the fly from one of the replicated copies.
    - When you access a file, it does copy on write: if you don't modify
      it, you read the git-annex copy. However, if you change it, the copy
      is unlocked on the fly and commited to git-annex when closed.
      Depending on the mount option, the previous copy can be kept in
      git-annex.
    - It pulls at regular intervals the other replicated copies and
      launches a merge program if there are conflicts.
    """
    def __init__(self, gitdir, mountpoint, numversions,
            getall, notifycmd):
        """
        Calls 'git init' and 'git annex init' on the storage directory if
        necessary.
        """
        self.gitdir = gitdir
        self.mountpoint = mountpoint
        self.numversions = numversions
        self.getall = getall
        self.notifycmd = notifycmd
        self.rwlock = threading.Lock()
        self.opened_copies = {}
        with self.rwlock:
            if os.path.realpath(os.curdir) != self.gitdir:
                os.chdir(self.gitdir)
            if not os.path.exists('.git'):
                shell_do('git init')
            if not os.path.exists('.git-annex'):
                import socket
                shell_do('git annex init "%s"' % socket.gethostname())


    def __call__(self, op, path, *args):
        """
        redirects self.op('/foo', ...) to self.op('./foo', ...)
        """
        os.chdir(self.gitdir)   # when foreground is not set, the working
                                # directory changes unexplainably
        return super(ShareBox, self).__call__(op, "." + path, *args)

    getxattr = None
    listxattr = None
    link = None                 # No hardlinks
    mknod = None                # No devices
    mkdir = os.mkdir
    readlink = os.readlink
    rmdir = os.rmdir

    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail',
            'f_bfree', 'f_blocks', 'f_bsize', 'f_favail', 'f_ffree',
            'f_files', 'f_flag', 'f_frsize', 'f_namemax'))

    def create(self, path, mode):
        return os.open(path, os.O_WRONLY | os.O_CREAT, mode)

    def utimens(self, path, times):
        if path == './.command':
            raise FuseOSError(EACCES)
        else:
            os.utime(path, times)

    def readdir(self, path, fh):
        """
        We have special files in the root to communicate with sharebox.
        """
        if path == './':
            return ['.', '..', '.command'] + os.listdir(path)
        else:
            return ['.', '..'] + os.listdir(path)

    def access(self, path, mode):
        """
        Annexed files can be accessed any mode as long are they are
        present.
        """
        if path == './.command':
            if mode & os.R_OK:
                raise FuseOSError(EACCES)
        else:
            if annexed(path):
                if not os.path.exists(path):
                    raise FuseOSError(EACCES)
            else:
                if not os.access(path, mode):
                    raise FuseOSError(EACCES)

    def open(self, path, flags):
        """
        When an annexed file is requested, if it is not present on the
        system we first try to get it. If it fails, we refuse the access.
        Since we do copy on write, we do not need to try to open in write
        mode annexed files.
        """
        if path == './.command':
            return os.open('/dev/null', flags)
        else:
            res = None
            if annexed(path):
                if not os.path.exists(path):
                    shell_do('git annex get "%s"' % path)
                if not os.path.exists(path):
                    raise FuseOSError(EACCES)
                res = os.open(path, os.R_OK) # magic to open read only
            else:
                res = os.open(path, flags)
            return res

    def getattr(self, path, fh=None):
        """
        When an annexed file is requested, we fake some of its attributes,
        making it look like a conventional file (of size 0 if if is not
        present on the system).

        FIXME: this method has too much black magic. We should find a way
        to show annexed files as regular and writable by altering the
        st_mode, not by replacing it.

        The file ./.command is a special file for communicating with the
        filesystem, we fake its attributes.
        """
        if path == './.command':
            # regular file, write-only, all the time attributes are 'now'
            return {'st_ctime': time.time(), 'st_mtime': time.time(),
                    'st_nlink': 1, 'st_mode': 32896, 'st_size': 0,
                    'st_gid': 1000, 'st_uid': 1000, 'st_atime':
                    time.time()}
        else:
            path_ = path
            faked_attr = {}
            if annexed(path):
                faked_attr ['st_mode'] = 33188 # we fake a 644 regular file
                if os.path.exists(path):
                    base = os.path.dirname(path_)
                    path_ = os.path.join(base, os.readlink(path))
                else:
                    faked_attr ['st_size'] = 0
            st = os.lstat(path_)
            res = dict((key, getattr(st, key)) for key in ('st_atime',
                'st_ctime', 'st_gid', 'st_mode', 'st_mtime',
                'st_nlink', 'st_size', 'st_uid'))
            for attr, value in faked_attr.items():
                res [attr] = value
            return res

    def chmod(self, path, mode):
        if path == './.command':
            raise FuseOSError(EACCES)
        else:
            with self.rwlock:
                with AnnexUnlock(path):
                    os.chmod(path, mode)

    def chown(self, path, user, group):
        if path == './.command':
            raise FuseOSError(EACCES)
        else:
            with self.rwlock:
                with AnnexUnlock(path):
                    os.chown(path, user, group)

    def truncate(self, path, length, fh=None):
        if path == './.command':
            return
        else:
            with self.rwlock:
                with AnnexUnlock(path):
                    with open(path, 'r+') as f:
                        f.truncate(length)

    def flush(self, path, fh):
        if path == './.command':
            return
        else:
            with self.rwlock:
                with CopyOnWrite(path, fh, self.opened_copies,
                        unlock=False, commit=False) as fh_:
                    os.fsync(fh_)

    def fsync(self, path, datasync, fh):
        if path == './.command':
            return
        else:
            with self.rwlock:
                with CopyOnWrite(path, fh, self.opened_copies,
                        unlock=False, commit=False) as fh_:
                    os.fsync(fh_)

    def read(self, path, size, offset, fh):
        if path == './.command':
            return
        else:
            with self.rwlock:
                with CopyOnWrite(path, fh, self.opened_copies,
                        unlock=False, commit=False) as fh_:
                    os.lseek(fh_, offset, 0)
                    return os.read(fh_, size)

    def write(self, path, data, offset, fh):
        if path == './.command':
            self.dotcommand(data)
            return len(data)
        else:
            with self.rwlock:
                with CopyOnWrite(path, fh, self.opened_copies,
                        unlock=True, commit=False) as fh_:
                    os.lseek(fh_, offset, 0)
                    return os.write(fh_, data)

    def release(self, path, fh):
        """
        Closed files are commited and removed from the open fd list
        """
        with self.rwlock:
            with CopyOnWrite(path, fh, self.opened_copies,
                    unlock=False, commit=True):
                os.close(fh)

    def rename(self, old, new):
        if old == './.command' or new == '/.command':
            raise FuseOSError(EACCES)
        else:
            with self.rwlock:
                # Make sure to lock the file (and to annex it if it was not)
                if not ignored(old):
                    shell_do('git annex add "%s"' % old)
                os.rename(old, '.' + new)
                if ignored(old) or ignored('.' + new):
                    if not ignored(old):
                        shell_do('git rm "%s"' % old)
                        shell_do('git commit -m "moved %s to ignored file"' % old)
                    if not ignored('.' + new):
                        shell_do('git annex add ".%s"' % new)
                        shell_do('git commit -m "moved an ignored file to .%s"' % new)
                else:
                    shell_do('git mv "%s" ".%s"' % (old, new))
                    shell_do('git commit -m "moved %s to .%s"' % (old, new))


    def symlink(self, target, source):
        if target == './.command':
            raise FuseOSError(EACCES)
        else:
            with self.rwlock:
                os.symlink(source, target)
                if not ignored(target):
                    shell_do('git annex add "%s"' % target)
                    shell_do('git commit -m "created symlink %s -> %s"' %(target,
                        source) )

    def unlink(self, path):
        if path == './.command':
            raise FuseOSError(EACCES)
        else:
            with self.rwlock:
                os.unlink(path)
                if not ignored(path):
                    shell_do('git rm "%s"' % path)
                    shell_do('git commit -m "removed %s"' % path)

    def dotcommand(self, text):
        for command in text.strip().split('\n'):
            if command == 'sync':
                self.sync()
            if command == 'merge':
                self.sync(True)
            if command.startswith('get '):
                shell_do('git annex ' + command)

    def sync(self, manual_merge=False):
        with sharebox.rwlock:
            shell_do('git fetch --all')
            repos = subprocess.Popen(
                    shlex.split('git remote show'),
                    stdout=subprocess.PIPE).communicate()[0].strip().split('\n')
            for remote in repos:
                if remote:
                    if not shell_do('git merge %s/master' % remote):
                        if manual_merge:
                            shell_do(self.notifycmd %
                                    "Manual merge invoked, but not implemented.")
                            shell_do('git reset --hard')
                            shell_do('git clean -f')
                        else:
                            shell_do('git reset --hard')
                            shell_do('git clean -f')
                            shell_do(self.notifycmd %
                                    "Manual merge is required. Run: \nsharebox --merge "+
                                    self.mountpoint)
                    else:
                        if self.getall:
                            shell_do('git annex get .')
                        shell_do('git commit -m "merged with %s"' % remote)

def send_sharebox_command(command, mountpoint):
    """
    send a command to the sharebox file system mounted on the mountpoint:
    write the command to the .command file on the root
    """
    if not shell_do('grep %s /etc/mtab' % mountpoint):
        print 'Mountpoint %s was not found in /etc/mtab' % mountpoint
        return 1
    else:
        valid_commands = ["merge", "get", "sync"]
        if not command.split()[0] in valid_commands:
            print '%s : unrecognized command' % command
            return 1
        else:
            with open(os.path.join(mountpoint, ".command"), 'w') as f:
                f.write(command)

if __name__ == "__main__":
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "ho:c:", ["help",
            "command="])
    except getopt.GetoptError, err:
        print str(err)
        print __doc__
        sys.exit(1)

    command = None
    gitdir = None
    getall = False
    numversions = 0
    notifycmd = 'notify-send "sharebox" "%s"'

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        if opt in ("-c", "--command"):
            command = arg
        if opt == "-o":
            if '=' in arg:
                option = arg.split('=')[0]
                value = arg.replace( option + '=', '', 1)
                if option == 'gitdir':
                    gitdir = value
                elif option == 'numversions':
                    numversions = int(value)
                elif option == 'notifycmd':
                    notifycmd = value
                else:
                    print("unrecognized option: %s" % option)
                    sys.exit(1)
            else:
                if arg == 'foreground':
                    foreground=True
                elif arg == 'getall':
                    getall=True
                else:
                    print("unrecognized option: %s" % arg)
                    sys.exit(1)

    mountpoint = "".join(args)
    if mountpoint == "":
        print 'invalid mountpoint'
        sys.exit(1)
    mountpoint = os.path.realpath(mountpoint)

    if command:
        retcode = send_sharebox_command(command, mountpoint)
        sys.exit(retcode)
    else:
        if not gitdir:
            print "Can't mount, missing the gitdir option."
            print __doc__
            sys.exit(1)
        gitdir = os.path.realpath(gitdir)

        sharebox = ShareBox(gitdir, mountpoint, numversions, getall,
                notifycmd)
        fuse = FUSE(sharebox, mountpoint, foreground=foreground)

########NEW FILE########
