__FILENAME__ = context
#!/usr/bin/env python

from errno import ENOENT
from stat import S_IFDIR, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context


class Context(LoggingMixIn, Operations):
    'Example filesystem to demonstrate fuse_get_context()'

    def getattr(self, path, fh=None):
        uid, gid, pid = fuse_get_context()
        if path == '/':
            st = dict(st_mode=(S_IFDIR | 0755), st_nlink=2)
        elif path == '/uid':
            size = len('%s\n' % uid)
            st = dict(st_mode=(S_IFREG | 0444), st_size=size)
        elif path == '/gid':
            size = len('%s\n' % gid)
            st = dict(st_mode=(S_IFREG | 0444), st_size=size)
        elif path == '/pid':
            size = len('%s\n' % pid)
            st = dict(st_mode=(S_IFREG | 0444), st_size=size)
        else:
            raise FuseOSError(ENOENT)
        st['st_ctime'] = st['st_mtime'] = st['st_atime'] = time()
        return st

    def read(self, path, size, offset, fh):
        uid, gid, pid = fuse_get_context()
        encoded = lambda x: ('%s\n' % x).encode('utf-8')

        if path == '/uid':
            return encoded(uid)
        elif path == '/gid':
            return encoded(gid)
        elif path == '/pid':
            return encoded(pid)

        raise RuntimeError('unexpected path: %r' % path)

    def readdir(self, path, fh):
        return ['.', '..', 'uid', 'gid', 'pid']

    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    open = None
    opendir = None
    release = None
    releasedir = None
    statfs = None


if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    fuse = FUSE(Context(), argv[1], foreground=True, ro=True)

########NEW FILE########
__FILENAME__ = loopback
#!/usr/bin/env python

from __future__ import with_statement

from errno import EACCES
from os.path import realpath
from sys import argv, exit
from threading import Lock

import os

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class Loopback(LoggingMixIn, Operations):
    def __init__(self, root):
        self.root = realpath(root)
        self.rwlock = Lock()

    def __call__(self, op, path, *args):
        return super(Loopback, self).__call__(op, self.root + path, *args)

    def access(self, path, mode):
        if not os.access(path, mode):
            raise FuseOSError(EACCES)

    chmod = os.chmod
    chown = os.chown

    def create(self, path, mode):
        return os.open(path, os.O_WRONLY | os.O_CREAT, mode)

    def flush(self, path, fh):
        return os.fsync(fh)

    def fsync(self, path, datasync, fh):
        return os.fsync(fh)

    def getattr(self, path, fh=None):
        st = os.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
            'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    getxattr = None

    def link(self, target, source):
        return os.link(source, target)

    listxattr = None
    mkdir = os.mkdir
    mknod = os.mknod
    open = os.open

    def read(self, path, size, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.read(fh, size)

    def readdir(self, path, fh):
        return ['.', '..'] + os.listdir(path)

    readlink = os.readlink

    def release(self, path, fh):
        return os.close(fh)

    def rename(self, old, new):
        return os.rename(old, self.root + new)

    rmdir = os.rmdir

    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def symlink(self, target, source):
        return os.symlink(source, target)

    def truncate(self, path, length, fh=None):
        with open(path, 'r+') as f:
            f.truncate(length)

    unlink = os.unlink
    utimens = os.utime

    def write(self, path, data, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.write(fh, data)


if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: %s <root> <mountpoint>' % argv[0])
        exit(1)

    fuse = FUSE(Loopback(argv[1]), argv[2], foreground=True)

########NEW FILE########
__FILENAME__ = memory
#!/usr/bin/env python

import logging

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class Memory(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0755), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        if path not in self.files:
            raise FuseOSError(ENOENT)

        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        return ['.', '..'] + [x[1:] for x in self.files if x != '/']

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0777), st_nlink=1,
                                  st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)


if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.getLogger().setLevel(logging.DEBUG)
    fuse = FUSE(Memory(), argv[1], foreground=True)

########NEW FILE########
__FILENAME__ = memoryll
#!/usr/bin/env python

from collections import defaultdict
from errno import ENOENT, EROFS
from stat import S_IFMT, S_IMODE, S_IFDIR, S_IFREG
from sys import argv, exit
from time import time

from fusell import FUSELL


class Memory(FUSELL):
    def create_ino(self):
        self.ino += 1
        return self.ino
    
    def init(self, userdata, conn):
        self.ino = 1
        self.attr = defaultdict(dict)
        self.data = defaultdict(str)
        self.parent = {}
        self.children = defaultdict(dict)
        
        self.attr[1] = {'st_ino': 1, 'st_mode': S_IFDIR | 0777, 'st_nlink': 2}
        self.parent[1] = 1
    
    forget = None
    
    def getattr(self, req, ino, fi):
        print 'getattr:', ino
        attr = self.attr[ino]
        if attr:
            self.reply_attr(req, attr, 1.0)
        else:
            self.reply_err(req, ENOENT)
    
    def lookup(self, req, parent, name):
        print 'lookup:', parent, name
        children = self.children[parent]
        ino = children.get(name, 0)
        attr = self.attr[ino]
        
        if attr:
            entry = {'ino': ino, 'attr': attr, 'atttr_timeout': 1.0, 'entry_timeout': 1.0}
            self.reply_entry(req, entry)
        else:
            self.reply_err(req, ENOENT)
    
    def mkdir(self, req, parent, name, mode):
        print 'mkdir:', parent, name
        ino = self.create_ino()
        ctx = self.req_ctx(req)
        now = time()
        attr = {
            'st_ino': ino,
            'st_mode': S_IFDIR | mode,
            'st_nlink': 2,
            'st_uid': ctx['uid'],
            'st_gid': ctx['gid'],
            'st_atime': now,
            'st_mtime': now,
            'st_ctime': now}
        
        self.attr[ino] = attr
        self.attr[parent]['st_nlink'] += 1
        self.parent[ino] = parent
        self.children[parent][name] = ino
        
        entry = {'ino': ino, 'attr': attr, 'atttr_timeout': 1.0, 'entry_timeout': 1.0}
        self.reply_entry(req, entry)
    
    def mknod(self, req, parent, name, mode, rdev):
        print 'mknod:', parent, name
        ino = self.create_ino()
        ctx = self.req_ctx(req)
        now = time()
        attr = {
            'st_ino': ino,
            'st_mode': mode,
            'st_nlink': 1,
            'st_uid': ctx['uid'],
            'st_gid': ctx['gid'],
            'st_rdev': rdev,
            'st_atime': now,
            'st_mtime': now,
            'st_ctime': now}
        
        self.attr[ino] = attr
        self.attr[parent]['st_nlink'] += 1
        self.children[parent][name] = ino
        
        entry = {'ino': ino, 'attr': attr, 'atttr_timeout': 1.0, 'entry_timeout': 1.0}
        self.reply_entry(req, entry)
    
    def open(self, req, ino, fi):
        print 'open:', ino
        self.reply_open(req, fi)

    def read(self, req, ino, size, off, fi):
        print 'read:', ino, size, off
        buf = self.data[ino][off:(off + size)]
        self.reply_buf(req, buf)
    
    def readdir(self, req, ino, size, off, fi):
        print 'readdir:', ino
        parent = self.parent[ino]
        entries = [('.', {'st_ino': ino, 'st_mode': S_IFDIR}),
            ('..', {'st_ino': parent, 'st_mode': S_IFDIR})]
        for name, child in self.children[ino].items():
            entries.append((name, self.attr[child]))
        self.reply_readdir(req, size, off, entries)        
    
    def rename(self, req, parent, name, newparent, newname):
        print 'rename:', parent, name, newparent, newname
        ino = self.children[parent].pop(name)
        self.children[newparent][newname] = ino
        self.parent[ino] = newparent
        self.reply_err(req, 0)
    
    def setattr(self, req, ino, attr, to_set, fi):
        print 'setattr:', ino, to_set
        a = self.attr[ino]
        for key in to_set:
            if key == 'st_mode':
                # Keep the old file type bit fields
                a['st_mode'] = S_IFMT(a['st_mode']) | S_IMODE(attr['st_mode'])
            else:
                a[key] = attr[key]
        self.attr[ino] = a
        self.reply_attr(req, a, 1.0)
    
    def write(self, req, ino, buf, off, fi):
        print 'write:', ino, off, len(buf)
        self.data[ino] = self.data[ino][:off] + buf
        self.attr[ino]['st_size'] = len(self.data[ino])
        self.reply_write(req, len(buf))

if __name__ == '__main__':
    if len(argv) != 2:
        print 'usage: %s <mountpoint>' % argv[0]
        exit(1)   
    fuse = Memory(argv[1])

########NEW FILE########
__FILENAME__ = sftp
#!/usr/bin/env python

from sys import argv, exit
from time import time

from paramiko import SSHClient

from fuse import FUSE, Operations, LoggingMixIn


class SFTP(LoggingMixIn, Operations):
    '''
    A simple SFTP filesystem. Requires paramiko: http://www.lag.net/paramiko/

    You need to be able to login to remote host without entering a password.
    '''

    def __init__(self, host, path='.'):
        self.client = SSHClient()
        self.client.load_system_host_keys()
        self.client.connect(host)
        self.sftp = self.client.open_sftp()
        self.root = path

    def chmod(self, path, mode):
        return self.sftp.chmod(path, mode)

    def chown(self, path, uid, gid):
        return self.sftp.chown(path, uid, gid)

    def create(self, path, mode):
        f = self.sftp.open(path, 'w')
        f.chmod(mode)
        f.close()
        return 0

    def destroy(self, path):
        self.sftp.close()
        self.client.close()

    def getattr(self, path, fh=None):
        st = self.sftp.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_gid',
            'st_mode', 'st_mtime', 'st_size', 'st_uid'))

    def mkdir(self, path, mode):
        return self.sftp.mkdir(path, mode)

    def read(self, path, size, offset, fh):
        f = self.sftp.open(path)
        f.seek(offset, 0)
        buf = f.read(size)
        f.close()
        return buf

    def readdir(self, path, fh):
        return ['.', '..'] + [name.encode('utf-8')
                              for name in self.sftp.listdir(path)]

    def readlink(self, path):
        return self.sftp.readlink(path)

    def rename(self, old, new):
        return self.sftp.rename(old, self.root + new)

    def rmdir(self, path):
        return self.sftp.rmdir(path)

    def symlink(self, target, source):
        return self.sftp.symlink(source, target)

    def truncate(self, path, length, fh=None):
        return self.sftp.truncate(path, length)

    def unlink(self, path):
        return self.sftp.unlink(path)

    def utimens(self, path, times=None):
        return self.sftp.utime(path, times)

    def write(self, path, data, offset, fh):
        f = self.sftp.open(path, 'r+')
        f.seek(offset, 0)
        f.write(data)
        f.close()
        return len(data)


if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: %s <host> <mountpoint>' % argv[0])
        exit(1)

    fuse = FUSE(SFTP(argv[1]), argv[2], foreground=True, nothreads=True)

########NEW FILE########
__FILENAME__ = fuse
# Copyright (c) 2012 Terence Honles <terence@honles.com> (maintainer)
# Copyright (c) 2008 Giorgos Verigakis <verigak@gmail.com> (author)
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
from os import strerror
from platform import machine, system
from signal import signal, SIGINT, SIG_DFL
from stat import S_IFDIR
from traceback import print_exc

import logging

try:
    from functools import partial
except ImportError:
    # http://docs.python.org/library/functools.html#functools.partial
    def partial(func, *args, **keywords):
        def newfunc(*fargs, **fkeywords):
            newkeywords = keywords.copy()
            newkeywords.update(fkeywords)
            return func(*(args + fargs), **newkeywords)

        newfunc.func = func
        newfunc.args = args
        newfunc.keywords = keywords
        return newfunc

try:
    basestring
except NameError:
    basestring = str

class c_timespec(Structure):
    _fields_ = [('tv_sec', c_long), ('tv_nsec', c_long)]

class c_utimbuf(Structure):
    _fields_ = [('actime', c_timespec), ('modtime', c_timespec)]

class c_stat(Structure):
    pass    # Platform dependent

_system = system()
_machine = machine()

if _system == 'Darwin':
    _libiconv = CDLL(find_library('iconv'), RTLD_GLOBAL) # libfuse dependency
    _libfuse_path = (find_library('fuse4x') or find_library('osxfuse') or
                     find_library('fuse'))
else:
    _libfuse_path = find_library('fuse')

if not _libfuse_path:
    raise EnvironmentError('Unable to find libfuse')
else:
    _libfuse = CDLL(_libfuse_path)

if _system == 'Darwin' and hasattr(_libfuse, 'macfuse_version'):
    _system = 'Darwin-MacFuse'


if _system in ('Darwin', 'Darwin-MacFuse', 'FreeBSD'):
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
    if _system == 'Darwin':
        c_stat._fields_ = [
            ('st_dev', c_dev_t),
            ('st_mode', c_mode_t),
            ('st_nlink', c_uint16),
            ('st_ino', c_uint64),
            ('st_uid', c_uid_t),
            ('st_gid', c_gid_t),
            ('st_rdev', c_dev_t),
            ('st_atimespec', c_timespec),
            ('st_mtimespec', c_timespec),
            ('st_ctimespec', c_timespec),
            ('st_birthtimespec', c_timespec),
            ('st_size', c_off_t),
            ('st_blocks', c_int64),
            ('st_blksize', c_int32),
            ('st_flags', c_int32),
            ('st_gen', c_int32),
            ('st_lspare', c_int32),
            ('st_qspare', c_int64)]
    else:
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
    setxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
                           c_size_t, c_int)

    getxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
                           c_size_t)

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
    setxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
                           c_size_t, c_int)

    getxattr_t = CFUNCTYPE(c_int, c_char_p, c_char_p, POINTER(c_byte),
                           c_size_t)

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

_libfuse.fuse_get_context.restype = POINTER(fuse_context)


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

        ('read', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t,
                           c_off_t, POINTER(fuse_file_info))),

        ('write', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t,
                            c_off_t, POINTER(fuse_file_info))),

        ('statfs', CFUNCTYPE(c_int, c_char_p, POINTER(c_statvfs))),
        ('flush', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('release', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),
        ('fsync', CFUNCTYPE(c_int, c_char_p, c_int, POINTER(fuse_file_info))),
        ('setxattr', setxattr_t),
        ('getxattr', getxattr_t),
        ('listxattr', CFUNCTYPE(c_int, c_char_p, POINTER(c_byte), c_size_t)),
        ('removexattr', CFUNCTYPE(c_int, c_char_p, c_char_p)),
        ('opendir', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),

        ('readdir', CFUNCTYPE(c_int, c_char_p, c_voidp,
                              CFUNCTYPE(c_int, c_voidp, c_char_p,
                                        POINTER(c_stat), c_off_t),
                              c_off_t, POINTER(fuse_file_info))),

        ('releasedir', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info))),

        ('fsyncdir', CFUNCTYPE(c_int, c_char_p, c_int,
                               POINTER(fuse_file_info))),

        ('init', CFUNCTYPE(c_voidp, c_voidp)),
        ('destroy', CFUNCTYPE(c_voidp, c_voidp)),
        ('access', CFUNCTYPE(c_int, c_char_p, c_int)),

        ('create', CFUNCTYPE(c_int, c_char_p, c_mode_t,
                             POINTER(fuse_file_info))),

        ('ftruncate', CFUNCTYPE(c_int, c_char_p, c_off_t,
                                POINTER(fuse_file_info))),

        ('fgetattr', CFUNCTYPE(c_int, c_char_p, POINTER(c_stat),
                               POINTER(fuse_file_info))),

        ('lock', CFUNCTYPE(c_int, c_char_p, POINTER(fuse_file_info),
                           c_int, c_voidp)),

        ('utimens', CFUNCTYPE(c_int, c_char_p, POINTER(c_utimbuf))),
        ('bmap', CFUNCTYPE(c_int, c_char_p, c_size_t, POINTER(c_ulonglong))),
    ]


def time_of_timespec(ts):
    return ts.tv_sec + ts.tv_nsec / 10 ** 9

def set_st_attrs(st, attrs):
    for key, val in attrs.items():
        if key in ('st_atime', 'st_mtime', 'st_ctime', 'st_birthtime'):
            timespec = getattr(st, key + 'spec')
            timespec.tv_sec = int(val)
            timespec.tv_nsec = int((val - timespec.tv_sec) * 10 ** 9)
        elif hasattr(st, key):
            setattr(st, key, val)


def fuse_get_context():
    'Returns a (uid, gid, pid) tuple'

    ctxp = _libfuse.fuse_get_context()
    ctx = ctxp.contents
    return ctx.uid, ctx.gid, ctx.pid


class FuseOSError(OSError):
    def __init__(self, errno):
        super(FuseOSError, self).__init__(errno, strerror(errno))


class FUSE(object):
    '''
    This class is the lower level interface and should not be subclassed under
    normal use. Its methods are called by fuse.

    Assumes API version 2.6 or later.
    '''

    OPTIONS = (
        ('foreground', '-f'),
        ('debug', '-d'),
        ('nothreads', '-s'),
    )

    def __init__(self, operations, mountpoint, raw_fi=False, encoding='utf-8',
                 **kwargs):

        '''
        Setting raw_fi to True will cause FUSE to pass the fuse_file_info
        class as is to Operations, instead of just the fh field.

        This gives you access to direct_io, keep_cache, etc.
        '''

        self.operations = operations
        self.raw_fi = raw_fi
        self.encoding = encoding

        args = ['fuse']

        args.extend(flag for arg, flag in self.OPTIONS
                    if kwargs.pop(arg, False))

        kwargs.setdefault('fsname', operations.__class__.__name__)
        args.append('-o')
        args.append(','.join(self._normalize_fuse_options(**kwargs)))
        args.append(mountpoint)

        args = [arg.encode(encoding) for arg in args]
        argv = (c_char_p * len(args))(*args)

        fuse_ops = fuse_operations()
        for name, prototype in fuse_operations._fields_:
            if prototype != c_voidp and getattr(operations, name, None):
                op = partial(self._wrapper, getattr(self, name))
                setattr(fuse_ops, name, prototype(op))

        try:
            old_handler = signal(SIGINT, SIG_DFL)
        except ValueError:
            old_handler = SIG_DFL

        err = _libfuse.fuse_main_real(len(args), argv, pointer(fuse_ops),
                                      sizeof(fuse_ops), None)

        try:
            signal(SIGINT, old_handler)
        except ValueError:
            pass

        del self.operations     # Invoke the destructor
        if err:
            raise RuntimeError(err)

    @staticmethod
    def _normalize_fuse_options(**kargs):
        for key, value in kargs.items():
            if isinstance(value, bool):
                if value is True: yield key
            else:
                yield '%s=%s' % (key, value)

    @staticmethod
    def _wrapper(func, *args, **kwargs):
        'Decorator for the methods that follow'

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
        ret = self.operations('readlink', path.decode(self.encoding)) \
                  .encode(self.encoding)

        # copies a string into the given buffer
        # (null terminated and truncated if necessary)
        data = create_string_buffer(ret[:bufsize - 1])
        memmove(buf, data, len(data))
        return 0

    def mknod(self, path, mode, dev):
        return self.operations('mknod', path.decode(self.encoding), mode, dev)

    def mkdir(self, path, mode):
        return self.operations('mkdir', path.decode(self.encoding), mode)

    def unlink(self, path):
        return self.operations('unlink', path.decode(self.encoding))

    def rmdir(self, path):
        return self.operations('rmdir', path.decode(self.encoding))

    def symlink(self, source, target):
        'creates a symlink `target -> source` (e.g. ln -s source target)'

        return self.operations('symlink', target.decode(self.encoding),
                                          source.decode(self.encoding))

    def rename(self, old, new):
        return self.operations('rename', old.decode(self.encoding),
                                         new.decode(self.encoding))

    def link(self, source, target):
        'creates a hard link `target -> source` (e.g. ln source target)'

        return self.operations('link', target.decode(self.encoding),
                                       source.decode(self.encoding))

    def chmod(self, path, mode):
        return self.operations('chmod', path.decode(self.encoding), mode)

    def chown(self, path, uid, gid):
        # Check if any of the arguments is a -1 that has overflowed
        if c_uid_t(uid + 1).value == 0:
            uid = -1
        if c_gid_t(gid + 1).value == 0:
            gid = -1

        return self.operations('chown', path.decode(self.encoding), uid, gid)

    def truncate(self, path, length):
        return self.operations('truncate', path.decode(self.encoding), length)

    def open(self, path, fip):
        fi = fip.contents
        if self.raw_fi:
            return self.operations('open', path.decode(self.encoding), fi)
        else:
            fi.fh = self.operations('open', path.decode(self.encoding),
                                            fi.flags)

            return 0

    def read(self, path, buf, size, offset, fip):
        if self.raw_fi:
          fh = fip.contents
        else:
          fh = fip.contents.fh

        ret = self.operations('read', path.decode(self.encoding), size,
                                      offset, fh)

        if not ret: return 0

        retsize = len(ret)
        assert retsize <= size, \
            'actual amount read %d greater than expected %d' % (retsize, size)

        data = create_string_buffer(ret, retsize)
        memmove(buf, ret, retsize)
        return retsize

    def write(self, path, buf, size, offset, fip):
        data = string_at(buf, size)

        if self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        return self.operations('write', path.decode(self.encoding), data,
                                        offset, fh)

    def statfs(self, path, buf):
        stv = buf.contents
        attrs = self.operations('statfs', path.decode(self.encoding))
        for key, val in attrs.items():
            if hasattr(stv, key):
                setattr(stv, key, val)

        return 0

    def flush(self, path, fip):
        if self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        return self.operations('flush', path.decode(self.encoding), fh)

    def release(self, path, fip):
        if self.raw_fi:
          fh = fip.contents
        else:
          fh = fip.contents.fh

        return self.operations('release', path.decode(self.encoding), fh)

    def fsync(self, path, datasync, fip):
        if self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        return self.operations('fsync', path.decode(self.encoding), datasync,
                                        fh)

    def setxattr(self, path, name, value, size, options, *args):
        return self.operations('setxattr', path.decode(self.encoding),
                               name.decode(self.encoding),
                               string_at(value, size), options, *args)

    def getxattr(self, path, name, value, size, *args):
        ret = self.operations('getxattr', path.decode(self.encoding),
                                          name.decode(self.encoding), *args)

        retsize = len(ret)
        # allow size queries
        if not value: return retsize

        # do not truncate
        if retsize > size: return -ERANGE

        buf = create_string_buffer(ret, retsize)    # Does not add trailing 0
        memmove(value, buf, retsize)

        return retsize

    def listxattr(self, path, namebuf, size):
        attrs = self.operations('listxattr', path.decode(self.encoding)) or ''
        ret = '\x00'.join(attrs).encode(self.encoding) + '\x00'

        retsize = len(ret)
        # allow size queries
        if not namebuf: return retsize

        # do not truncate
        if retsize > size: return -ERANGE

        buf = create_string_buffer(ret, retsize)
        memmove(namebuf, buf, retsize)

        return retsize

    def removexattr(self, path, name):
        return self.operations('removexattr', path.decode(self.encoding),
                                              name.decode(self.encoding))

    def opendir(self, path, fip):
        # Ignore raw_fi
        fip.contents.fh = self.operations('opendir',
                                          path.decode(self.encoding))

        return 0

    def readdir(self, path, buf, filler, offset, fip):
        # Ignore raw_fi
        for item in self.operations('readdir', path.decode(self.encoding),
                                               fip.contents.fh):

            if isinstance(item, basestring):
                name, st, offset = item, None, 0
            else:
                name, attrs, offset = item
                if attrs:
                    st = c_stat()
                    set_st_attrs(st, attrs)
                else:
                    st = None

            if filler(buf, name.encode(self.encoding), st, offset) != 0:
                break

        return 0

    def releasedir(self, path, fip):
        # Ignore raw_fi
        return self.operations('releasedir', path.decode(self.encoding),
                                             fip.contents.fh)

    def fsyncdir(self, path, datasync, fip):
        # Ignore raw_fi
        return self.operations('fsyncdir', path.decode(self.encoding),
                                           datasync, fip.contents.fh)

    def init(self, conn):
        return self.operations('init', '/')

    def destroy(self, private_data):
        return self.operations('destroy', '/')

    def access(self, path, amode):
        return self.operations('access', path.decode(self.encoding), amode)

    def create(self, path, mode, fip):
        fi = fip.contents
        path = path.decode(self.encoding)

        if self.raw_fi:
            return self.operations('create', path, mode, fi)
        else:
            fi.fh = self.operations('create', path, mode)
            return 0

    def ftruncate(self, path, length, fip):
        if self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        return self.operations('truncate', path.decode(self.encoding),
                                           length, fh)

    def fgetattr(self, path, buf, fip):
        memset(buf, 0, sizeof(c_stat))

        st = buf.contents
        if not fip:
            fh = fip
        elif self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        attrs = self.operations('getattr', path.decode(self.encoding), fh)
        set_st_attrs(st, attrs)
        return 0

    def lock(self, path, fip, cmd, lock):
        if self.raw_fi:
            fh = fip.contents
        else:
            fh = fip.contents.fh

        return self.operations('lock', path.decode(self.encoding), fh, cmd,
                                       lock)

    def utimens(self, path, buf):
        if buf:
            atime = time_of_timespec(buf.contents.actime)
            mtime = time_of_timespec(buf.contents.modtime)
            times = (atime, mtime)
        else:
            times = None

        return self.operations('utimens', path.decode(self.encoding), times)

    def bmap(self, path, blocksize, idx):
        return self.operations('bmap', path.decode(self.encoding), blocksize,
                                       idx)


class Operations(object):
    '''
    This class should be subclassed and passed as an argument to FUSE on
    initialization. All operations should raise a FuseOSError exception on
    error.

    When in doubt of what an operation should do, check the FUSE header file
    or the corresponding system call man page.
    '''

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
        '''
        When raw_fi is False (default case), fi is None and create should
        return a numerical file handle.

        When raw_fi is True the file handle should be set directly by create
        and return 0.
        '''

        raise FuseOSError(EROFS)

    def destroy(self, path):
        'Called on filesystem destruction. Path is always /'

        pass

    def flush(self, path, fh):
        return 0

    def fsync(self, path, datasync, fh):
        return 0

    def fsyncdir(self, path, datasync, fh):
        return 0

    def getattr(self, path, fh=None):
        '''
        Returns a dictionary with keys identical to the stat C structure of
        stat(2).

        st_atime, st_mtime and st_ctime should be floats.

        NOTE: There is an incombatibility between Linux and Mac OS X
        concerning st_nlink of directories. Mac OS X counts all files inside
        the directory, while Linux counts only the subdirectories.
        '''

        if path != '/':
            raise FuseOSError(ENOENT)
        return dict(st_mode=(S_IFDIR | 0755), st_nlink=2)

    def getxattr(self, path, name, position=0):
        raise FuseOSError(ENOTSUP)

    def init(self, path):
        '''
        Called on filesystem initialization. (Path is always /)

        Use it instead of __init__ if you start threads on initialization.
        '''

        pass

    def link(self, target, source):
        'creates a hard link `target -> source` (e.g. ln source target)'

        raise FuseOSError(EROFS)

    def listxattr(self, path):
        return []

    lock = None

    def mkdir(self, path, mode):
        raise FuseOSError(EROFS)

    def mknod(self, path, mode, dev):
        raise FuseOSError(EROFS)

    def open(self, path, flags):
        '''
        When raw_fi is False (default case), open should return a numerical
        file handle.

        When raw_fi is True the signature of open becomes:
            open(self, path, fi)

        and the file handle should be set directly.
        '''

        return 0

    def opendir(self, path):
        'Returns a numerical file handle.'

        return 0

    def read(self, path, size, offset, fh):
        'Returns a string containing the data requested.'

        raise FuseOSError(EIO)

    def readdir(self, path, fh):
        '''
        Can return either a list of names, or a list of (name, attrs, offset)
        tuples. attrs is a dict as in getattr.
        '''

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
        '''
        Returns a dictionary with keys identical to the statvfs C structure of
        statvfs(3).

        On Mac OS X f_bsize and f_frsize must be a power of 2
        (minimum 512).
        '''

        return {}

    def symlink(self, target, source):
        'creates a symlink `target -> source` (e.g. ln -s source target)'

        raise FuseOSError(EROFS)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(EROFS)

    def unlink(self, path):
        raise FuseOSError(EROFS)

    def utimens(self, path, times=None):
        'Times is a (atime, mtime) tuple. If None use current time.'

        return 0

    def write(self, path, data, offset, fh):
        raise FuseOSError(EROFS)


class LoggingMixIn:
    log = logging.getLogger('fuse.log-mixin')

    def __call__(self, op, path, *args):
        self.log.debug('-> %s %s %s', op, path, repr(args))
        ret = '[Unhandled Exception]'
        try:
            ret = getattr(self, op)(path, *args)
            return ret
        except OSError, e:
            ret = str(e)
            raise
        finally:
            self.log.debug('<- %s %s', op, repr(ret))

########NEW FILE########
__FILENAME__ = fusell
# Copyright (c) 2010 Giorgos Verigakis <verigak@gmail.com>
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
from functools import partial, wraps
from inspect import getmembers, ismethod
from platform import machine, system
from stat import S_IFDIR, S_IFREG


_system = system()
_machine = machine()

class LibFUSE(CDLL):
    def __init__(self):
        if _system == 'Darwin':
            self.libiconv = CDLL(find_library('iconv'), RTLD_GLOBAL)
        super(LibFUSE, self).__init__(find_library('fuse'))
        
        self.fuse_mount.argtypes = (c_char_p, POINTER(fuse_args))
        self.fuse_mount.restype = c_void_p
        self.fuse_lowlevel_new.argtypes = (POINTER(fuse_args), POINTER(fuse_lowlevel_ops),
                                            c_size_t, c_void_p)
        self.fuse_lowlevel_new.restype = c_void_p
        self.fuse_set_signal_handlers.argtypes = (c_void_p,)
        self.fuse_session_add_chan.argtypes = (c_void_p, c_void_p)
        self.fuse_session_loop.argtypes = (c_void_p,)
        self.fuse_remove_signal_handlers.argtypes = (c_void_p,)
        self.fuse_session_remove_chan.argtypes = (c_void_p,)
        self.fuse_session_destroy.argtypes = (c_void_p,)
        self.fuse_unmount.argtypes = (c_char_p, c_void_p)
        
        self.fuse_req_ctx.restype = POINTER(fuse_ctx)
        self.fuse_req_ctx.argtypes = (fuse_req_t,)
        
        self.fuse_reply_err.argtypes = (fuse_req_t, c_int)
        self.fuse_reply_attr.argtypes = (fuse_req_t, c_void_p, c_double)
        self.fuse_reply_entry.argtypes = (fuse_req_t, c_void_p)
        self.fuse_reply_open.argtypes = (fuse_req_t, c_void_p)
        self.fuse_reply_buf.argtypes = (fuse_req_t, c_char_p, c_size_t)
        self.fuse_reply_write.argtypes = (fuse_req_t, c_size_t)
        
        self.fuse_add_direntry.argtypes = (c_void_p, c_char_p, c_size_t, c_char_p,
                                            c_stat_p, c_off_t)

class fuse_args(Structure):
    _fields_ = [('argc', c_int), ('argv', POINTER(c_char_p)), ('allocated', c_int)]

class c_timespec(Structure):
    _fields_ = [('tv_sec', c_long), ('tv_nsec', c_long)]

class c_stat(Structure):
    pass    # Platform dependent

if _system == 'Darwin':
    ENOTSUP = 45
    c_dev_t = c_int32
    c_fsblkcnt_t = c_ulong
    c_fsfilcnt_t = c_ulong
    c_gid_t = c_uint32
    c_mode_t = c_uint16
    c_off_t = c_int64
    c_pid_t = c_int32
    c_uid_t = c_uint32
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

class fuse_ctx(Structure):
    _fields_ = [('uid', c_uid_t), ('gid', c_gid_t), ('pid', c_pid_t)]

fuse_ino_t = c_ulong
fuse_req_t = c_void_p
c_stat_p = POINTER(c_stat)
fuse_file_info_p = POINTER(fuse_file_info)

FUSE_SET_ATTR = ('st_mode', 'st_uid', 'st_gid', 'st_size', 'st_atime', 'st_mtime')

class fuse_entry_param(Structure):
    _fields_ = [
        ('ino', fuse_ino_t),
        ('generation', c_ulong),
        ('attr', c_stat),
        ('attr_timeout', c_double),
        ('entry_timeout', c_double)]

class fuse_lowlevel_ops(Structure):
    _fields_ = [
        ('init', CFUNCTYPE(None, c_void_p, c_void_p)),
        ('destroy', CFUNCTYPE(None, c_void_p)),
        ('lookup', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p)),
        ('forget', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_ulong)),
        ('getattr', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('setattr', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_stat_p, c_int, fuse_file_info_p)),
        ('readlink', CFUNCTYPE(None, fuse_req_t, fuse_ino_t)),
        ('mknod', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p, c_mode_t, c_dev_t)),
        ('mkdir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p, c_mode_t)),
        ('unlink', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p)),
        ('rmdir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p)),
        ('symlink', CFUNCTYPE(None, fuse_req_t, c_char_p, fuse_ino_t, c_char_p)),
        ('rename', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p, fuse_ino_t, c_char_p)),
        ('link', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_ino_t, c_char_p)),
        ('open', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('read', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_size_t, c_off_t, fuse_file_info_p)),
        ('write', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_char_p, c_size_t, c_off_t,
                                fuse_file_info_p)),
        ('flush', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('release', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('fsync', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_int, fuse_file_info_p)),
        ('opendir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('readdir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_size_t, c_off_t, fuse_file_info_p)),
        ('releasedir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, fuse_file_info_p)),
        ('fsyncdir', CFUNCTYPE(None, fuse_req_t, fuse_ino_t, c_int, fuse_file_info_p))]


def struct_to_dict(p):
    try:
        x = p.contents
        return dict((key, getattr(x, key)) for key, type in x._fields_)
    except ValueError:
        return {}

def stat_to_dict(p):
    try:
        d = {}
        x = p.contents
        for key, type in x._fields_:
            if key in ('st_atimespec', 'st_mtimespec', 'st_ctimespec'):
                ts = getattr(x, key)
                key = key[:-4]      # Lose the "spec"
                d[key] = ts.tv_sec + ts.tv_nsec / 10 ** 9
            else:
                d[key] = getattr(x, key)
        return d
    except ValueError:
        return {}

def dict_to_stat(d):
    for key in ('st_atime', 'st_mtime', 'st_ctime'):
        if key in d:
            val = d[key]
            sec = int(val)
            nsec = int((val - sec) * 10 ** 9)
            d[key + 'spec'] = c_timespec(sec, nsec)
    return c_stat(**d)

def setattr_mask_to_list(mask):
    return [FUSE_SET_ATTR[i] for i in range(len(FUSE_SET_ATTR)) if mask & (1 << i)]

class FUSELL(object):
    def __init__(self, mountpoint):
        self.libfuse = LibFUSE()       
        
        fuse_ops = fuse_lowlevel_ops()
        
        for name, prototype in fuse_lowlevel_ops._fields_:
            method = getattr(self, 'fuse_' + name, None) or getattr(self, name, None)
            if method:
                setattr(fuse_ops, name, prototype(method))
        
        args = ['fuse']
        argv = fuse_args(len(args), (c_char_p * len(args))(*args), 0)
        
        # TODO: handle initialization errors
        
        chan = self.libfuse.fuse_mount(mountpoint, argv)
        assert chan
        
        session = self.libfuse.fuse_lowlevel_new(argv, byref(fuse_ops), sizeof(fuse_ops), None)
        assert session
        
        err = self.libfuse.fuse_set_signal_handlers(session)
        assert err == 0
        
        self.libfuse.fuse_session_add_chan(session, chan)
        
        err = self.libfuse.fuse_session_loop(session)
        assert err == 0
        
        err = self.libfuse.fuse_remove_signal_handlers(session)
        assert err == 0
        
        self.libfuse.fuse_session_remove_chan(chan)
        self.libfuse.fuse_session_destroy(session)
        self.libfuse.fuse_unmount(mountpoint, chan)
    
    def reply_err(self, req, err):
        return self.libfuse.fuse_reply_err(req, err)
    
    def reply_none(self, req):
        self.libfuse.fuse_reply_none(req)
    
    def reply_entry(self, req, entry):
        entry['attr'] = c_stat(**entry['attr'])
        e = fuse_entry_param(**entry)
        self.libfuse.fuse_reply_entry(req, byref(e))
    
    def reply_create(self, req, *args):
        pass    # XXX
    
    def reply_attr(self, req, attr, attr_timeout):
        st = dict_to_stat(attr)
        return self.libfuse.fuse_reply_attr(req, byref(st), c_double(attr_timeout))
    
    def reply_readlink(self, req, *args):
        pass    # XXX
    
    def reply_open(self, req, d):
        fi = fuse_file_info(**d)
        return self.libfuse.fuse_reply_open(req, byref(fi))
    
    def reply_write(self, req, count):
        return self.libfuse.fuse_reply_write(req, count)
    
    def reply_buf(self, req, buf):
        return self.libfuse.fuse_reply_buf(req, buf, len(buf))
    
    def reply_readdir(self, req, size, off, entries):
        bufsize = 0
        sized_entries = []
        for name, attr in entries:
            entsize = self.libfuse.fuse_add_direntry(req, None, 0, name, None, 0)
            sized_entries.append((name, attr, entsize))
            bufsize += entsize

        next = 0
        buf = create_string_buffer(bufsize)
        for name, attr, entsize in sized_entries:
            entbuf = cast(addressof(buf) + next, c_char_p)
            st = c_stat(**attr)
            next += entsize
            self.libfuse.fuse_add_direntry(req, entbuf, entsize, name, byref(st), next)

        if off < bufsize:
            buf = cast(addressof(buf) + off, c_char_p) if off else buf
            return self.libfuse.fuse_reply_buf(req, buf, min(bufsize - off, size))
        else:
            return self.libfuse.fuse_reply_buf(req, None, 0)
    
    
    # If you override the following methods you should reply directly
    # with the self.libfuse.fuse_reply_* methods.
    
    def fuse_getattr(self, req, ino, fi):
        self.getattr(req, ino, struct_to_dict(fi))
    
    def fuse_setattr(self, req, ino, attr, to_set, fi):
        attr_dict = stat_to_dict(attr)
        to_set_list = setattr_mask_to_list(to_set)
        fi_dict = struct_to_dict(fi)
        self.setattr(req, ino, attr_dict, to_set_list, fi_dict)
        
    def fuse_open(self, req, ino, fi):
        self.open(req, ino, struct_to_dict(fi))
    
    def fuse_read(self, req, ino, size, off, fi):
        self.read(req, ino, size, off, fi)
    
    def fuse_write(self, req, ino, buf, size, off, fi):
        buf_str = string_at(buf, size)
        fi_dict = struct_to_dict(fi)
        self.write(req, ino, buf_str, off, fi_dict)

    def fuse_flush(self, req, ino, fi):
        self.flush(req, ino, struct_to_dict(fi))
    
    def fuse_release(self, req, ino, fi):
        self.release(req, ino, struct_to_dict(fi))
    
    def fuse_fsync(self, req, ino, datasync, fi):
        self.fsyncdir(req, ino, datasync, struct_to_dict(fi))
    
    def fuse_opendir(self, req, ino, fi):
        self.opendir(req, ino, struct_to_dict(fi))
    
    def fuse_readdir(self, req, ino, size, off, fi):
        self.readdir(req, ino, size, off, struct_to_dict(fi))
    
    def fuse_releasedir(self, req, ino, fi):
        self.releasedir(req, ino, struct_to_dict(fi))
    
    def fuse_fsyncdir(self, req, ino, datasync, fi):
        self.fsyncdir(req, ino, datasync, struct_to_dict(fi))
    
    
    # Utility methods
    
    def req_ctx(self, req):
        ctx = self.libfuse.fuse_req_ctx(req)
        return struct_to_dict(ctx)
    
    
    # Methods to be overridden in subclasses.
    # Reply with the self.reply_* methods.
    
    def init(self, userdata, conn):
        """Initialize filesystem
        
        There's no reply to this method
        """
        pass

    def destroy(self, userdata):
        """Clean up filesystem
        
        There's no reply to this method
        """
        pass

    def lookup(self, req, parent, name):
        """Look up a directory entry by name and get its attributes.
        
        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, ENOENT)
    
    def forget(self, req, ino, nlookup):
        """Forget about an inode
        
        Valid replies:
            reply_none
        """
        self.reply_none(req)

    def getattr(self, req, ino, fi):
        """Get file attributes
        
        Valid replies:
            reply_attr
            reply_err
        """
        if ino == 1:
            attr = {'st_ino': 1, 'st_mode': S_IFDIR | 0755, 'st_nlink': 2}
            self.reply_attr(req, attr, 1.0)
        else:
            self.reply_err(req, ENOENT)        
    
    def setattr(self, req, ino, attr, to_set, fi):
        """Set file attributes
        
        Valid replies:
            reply_attr
            reply_err
        """
        self.reply_err(req, EROFS)
        
    def readlink(self, req, ino):
        """Read symbolic link
        
        Valid replies:
            reply_readlink
            reply_err
        """
        self.reply_err(req, ENOENT)
    
    def mknod(self, req, parent, name, mode, rdev):
        """Create file node
        
        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def mkdir(self, req, parent, name, mode):
        """Create a directory
        
        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, EROFS)

    def unlink(self, req, parent, name):
        """Remove a file
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def rmdir(self, req, parent, name):
        """Remove a directory
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def symlink(self, req, link, parent, name):
        """Create a symbolic link
        
        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def rename(self, req, parent, name, newparent, newname):
        """Rename a file
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def link(self, req, ino, newparent, newname):
        """Create a hard link
        
        Valid replies:
            reply_entry
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def open(self, req, ino, fi):
        """Open a file
        
        Valid replies:
            reply_open
            reply_err
        """
        self.reply_open(req, fi)
    
    def read(self, req, ino, size, off, fi):
        """Read data
        
        Valid replies:
            reply_buf
            reply_err
        """
        self.reply_err(req, EIO)
        
    def write(self, req, ino, buf, off, fi):
        """Write data
        
        Valid replies:
            reply_write
            reply_err
        """
        self.reply_err(req, EROFS)
    
    def flush(self, req, ino, fi):
        """Flush method
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)
    
    def release(self, req, ino, fi):
        """Release an open file
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)
    
    def fsync(self, req, ino, datasync, fi):
        """Synchronize file contents
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)

    def opendir(self, req, ino, fi):
        """Open a directory
        
        Valid replies:
            reply_open
            reply_err
        """
        self.reply_open(req, fi)
    
    def readdir(self, req, ino, size, off, fi):
        """Read directory
        
        Valid replies:
            reply_readdir
            reply_err
        """
        if ino == 1:
            attr = {'st_ino': 1, 'st_mode': S_IFDIR}
            entries = [('.', attr), ('..', attr)]
            self.reply_readdir(req, size, off, entries)
        else:
            self.reply_err(req, ENOENT)
    
    def releasedir(self, req, ino, fi):
        """Release an open directory
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)

    def fsyncdir(self, req, ino, datasync, fi):
        """Synchronize directory contents
        
        Valid replies:
            reply_err
        """
        self.reply_err(req, 0)
########NEW FILE########
