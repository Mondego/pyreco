__FILENAME__ = example
#!/usr/bin/env python26

"""Python HDFS use examples.

After reading this example you should have enough information to read and write
HDFS files from your programs.
"""

from hdfs.hfile import Hfile

hostname = 'hadoop.twitter.com'
port = 8020
hdfs_path = '/user/travis/example'
local_path = '/etc/motd'

# Let's open local and HDFS files.

hfile = Hfile(hostname, port, hdfs_path, mode='w')
fh = open(local_path)

# Now we'll write lines from a local file into the HDFS file.
for line in fh:
  hfile.write(line)

# And close them.
fh.close()
hfile.close()

# Let's read local_path into memory for comparison.
motd = open(local_path).read()

# Now let's read the data back
hfile = Hfile(hostname, port, hdfs_path)

# With an iterator
data_read_from_hdfs = ''
for line in hfile:
  data_read_from_hdfs += line
print motd == data_read_from_hdfs

# All at once
data_read_from_hdfs = hfile.read()
print motd == data_read_from_hdfs

hfile.close()

# Hopefully you have enough info to get started!

from hdfs.hfilesystem import Hfilesystem
hfs = Hfilesystem(hostname, port)
print hfs.getHosts(hdfs_path, 0, 1)


########NEW FILE########
__FILENAME__ = hfile
from hdfs._common import *

class Hfile(object):

  def __init__(self, hostname, port, filename, mode='r', buffer_size=0,
               replication=0, block_size=0):
    flags = None
    if mode == 'r':
      flags = os.O_RDONLY
    elif mode == 'w':
      flags = os.O_WRONLY
    else:
      raise HdfsError('Invalid open flags.')
    self.hostname = hostname
    self.port = port
    self.filename = filename
    self.fs = libhdfs.hdfsConnect(hostname, port)
    self.fh = libhdfs.hdfsOpenFile(self.fs, filename, flags, buffer_size,
                                   replication, block_size)
    self.readline_pos = 0

  def __iter__(self):
    return self

  def close(self):
    libhdfs.hdfsCloseFile(self.fs, self.fh)
    libhdfs.hdfsDisconnect(self.fs)

  def next(self):
    line = self.readline()
    if not line:
      raise StopIteration
    return line

  def open(self, filename, mode='r', buffer_size=0,
           replication=0, block_size=0):
    """Open a hdfs file in given mode.

    @param fs The configured filesystem handle.
    @param path The full path to the file.
    @param flags - an | of bits/fcntl.h file flags - supported flags are
    O_RDONLY, O_WRONLY (meaning create or overwrite i.e., implies
    O_TRUNCAT), O_WRONLY|O_APPEND. Other flags are generally ignored other
    than (O_RDWR || (O_EXCL & O_CREAT)) which return NULL and set errno
    equal ENOTSUP.
    @param bufferSize Size of buffer for read/write - pass 0 if you want
    to use the default configured values.
    @param replication Block replication - pass 0 if you want to use
    the default configured values.
    @param blocksize Size of block - pass 0 if you want to use the
    default configured values.
    @return Returns the handle to the open file or NULL on error.
    """
    flags = None
    if mode == 'r':
      flags = os.O_RDONLY
    elif mode == 'w':
      flags = os.O_WRONLY
    else:
      raise HdfsError('Invalid open flags.')

    self.fh = libhdfs.hdfsOpenFile(self.fs, filename, flags, buffer_size,
                                   replication, block_size)
    if not self.fh:
      raise HdfsError('Failed opening %s' % filename)

  def pread(self, position, length):
    """Positional read of data from an open file.

    @param position Position from which to read
    @param length The length of the buffer.
    @return Returns the number of bytes actually read, possibly less than
    than length; None on error.
    """
    st = self.stat()
    if position >= st.mSize:
      return None

    buf = create_string_buffer(length)
    buf_p = cast(buf, c_void_p)

    ret = libhdfs.hdfsPread(self.fs, self.fh, position, buf_p, length)
    if ret == -1:
      raise HdfsError('read failure')
    return buf.value

  def read(self):
    st = self.stat()

    buf = create_string_buffer(st.mSize)
    buf_p = cast(buf, c_void_p)

    ret = libhdfs.hdfsRead(self.fs, self.fh, buf_p, st.mSize)
    if ret == -1:
      raise HdfsError('read failure')
    return buf.value[0:ret]

  def readline(self, length=100):
    line = ''
    while True:
      data = self.pread(self.readline_pos, length)
      if data is None:
        return line
      newline_pos = data.find('\n')
      if newline_pos == -1:
        self.readline_pos += len(data)
        line += data
      else:
        self.readline_pos += newline_pos+1
        return line + data[0:newline_pos+1]

  def readlines(self):
    return [line for line in self]

  def seek(self, position):
    """Seek to given offset in file. This works only for
    files opened in read-only mode.

    Returns True if seek was successful, False on error.
    """
    if libhdfs.hdfsSeek(self.fs, self.fh, position) == 0:
      return True
    else:
      return False

  def stat(self):
    return libhdfs.hdfsGetPathInfo(self.fs, self.filename).contents

  def tell(self):
    """Returns current offset in bytes, None on error."""
    ret = libhdfs.hdfsTell(self.fs, self.fh)
    if ret != -1:
      return ret
    else:
      return None

  def write(self, buffer):
    sb = create_string_buffer(buffer)
    buffer_p = cast(sb, c_void_p)

    ret = libhdfs.hdfsWrite(self.fs, self.fh, buffer_p, len(buffer))

    if ret != -1:
      return True
    else:
      return False

########NEW FILE########
__FILENAME__ = hfilesystem
from hdfs._common import *

class Hfilesystem(object):

  def __init__(self, hostname='default', port=0):
    self.hostname = hostname
    self.port = port
    self.fs = libhdfs.hdfsConnect(hostname, port)

  def __del__(self):
    if self.fs:
      self.disconnect()

  def capacity(self):
    """Return the raw capacity of the filesystem.

    @param fs The configured filesystem handle.
    @return Returns the raw-capacity; None on error.
    """
    cap = libhdfs.hdfsGetCapacity(self.fs)
    if cap != -1:
      return cap
    else:
      return None

  def chmod(self, path, mode):
    """Change file mode.

    Permissions in HDFS are POSIX-like, with some important differences.

    For more information, please see:
    http://hadoop.apache.org/hdfs/docs/current/hdfs_permissions_guide.html

    @param path the path to the file or directory
    @param mode the bitmask to set it to
    @return True on success else False
    """
    if libhdfs.hdfsChmod(self.fs, path, mode) == 0:
      return True
    else:
      return False

  def chown(self, path, owner, group):
    """Change owner and group for a file.

    @param path the path to the file or directory
    @param owner this is a string in Hadoop land. Set to None if only setting group
    @param group  this is a string in Hadoop land. Set to None if only setting user
    @return Returns True on success, False on error.
    """
    if libhdfs.hdfsChown(self.fs, path, owner, group) == 0:
      return True
    else:
      return False

  def connect(self, hostname, port):
    """Connect to a hdfs file system.

    @param host A string containing either a host name, or an ip address
    of the namenode of a hdfs cluster. 'host' should be passed as NULL if
    you want to connect to local filesystem. 'host' should be passed as
    'default' (and port as 0) to used the 'configured' filesystem
    (core-site/core-default.xml).
    @param port The port on which the server is listening.
    @return Returns a handle to the filesystem or NULL on error.
    """
    self.fs = libhdfs.hdfsConnect(hostname, port)
    if not self.fs:
      raise HdfsError('Failed connecting to %s:%d' % (hostname, port))

  def copy(self, srcPath, dstPath):
    """Copy file from one filesystem to another.
    @param srcFS The handle to source filesystem.
    @param src The path of source file.
    @param dstFS The handle to destination filesystem.
    @param dst The path of destination file.
    @return Returns 0 on success, -1 on error.
    """
    raise NotImplementedError, "TODO(travis)"

  def delete(self, path):
    """
    @param fs The configured filesystem handle.
    @param path The path of the file.
    @return Returns 0 on success, -1 on error.
    """
    if libhdfs.hdfsDelete(self.fs, path) == 0:
      return True
    else:
      return False

  def disconnect(self):
    if libhdfs.hdfsDisconnect(self.fs) == -1:
      raise HdfsError('Failed disconnecting from %s:%d' % (self.hostname, self.port))

  def exists(self, path):
    """
    @param fs The configured filesystem handle.
    @param path The path to look for
    @return Returns True on success, False on error.
    """
    if libhdfs.hdfsExists(self.fs, path) == 0:
      return True
    else:
      return False

  def get_default_block_size(self):
    """Get the optimum blocksize.

    @param fs The configured filesystem handle.
    @return Returns the blocksize; -1 on error.
    """
    raise NotImplementedError, "TODO(travis)"

  def get_used(self):
    """Return the total raw size of all files in the filesystem.

    @param fs The configured filesystem handle.
    @return Returns the total-size; -1 on error.
    """
    raise NotImplementedError, "TODO(travis)"

  # TODO(travis): Decorate with @exists
  def listdir(self, path):
    """Get list of files/directories for a given directory-path.
    hdfsFreeFileInfo should be called to deallocate memory.

    @param path The path of the directory.
    @return Returns a dynamically-allocated array of hdfsFileInfo objects;
    NULL on error.
    """
    if not self.exists(path):
      return None

    path = c_char_p(path)
    num_entries = c_int()
    entries = []
    entries_p = libhdfs.hdfsListDirectory(self.fs, path, pointer(num_entries))
    [entries.append(entries_p[i].mName) for i in range(num_entries.value)]
    return sorted(entries)

  def mkdir(self, path):
    """Make the given file and all non-existent parents into directories.

    @param fs The configured filesystem handle.
    @param path The path of the directory.
    @return Returns True on success, False on error.
    """
    if libhdfs.hdfsCreateDirectory(self.fs, path) == 0:
      return True
    else:
      return False

  def move(self, srcFS, srcPath, dstFS, dstPath):
    """Move file from one filesystem to another.

    @param srcFS The handle to source filesystem.
    @param src The path of source file.
    @param dstFS The handle to destination filesystem.
    @param dst The path of destination file.
    @return Returns 0 on success, -1 on error.
    """
    raise NotImplementedError, "TODO(travis)"

  def rename(self, oldPath, newPath):
    """
    @param fs The configured filesystem handle.
    @param oldPath The path of the source file.
    @param newPath The path of the destination file.
    @return Returns 0 on success, -1 on error.
    """
    if libhdfs.hdfsRename(self.fs, oldPath, newPath) == 0:
      return True
    else:
      return False

  def set_replication(self, path, replication):
    """Set the replication of the specified file to the supplied value.

    @param fs The configured filesystem handle.
    @param path The path of the file.
    @return Returns 0 on success, -1 on error.
    """
    raise NotImplementedError, "TODO(travis)"

  def stat(self, path):
    """Get file status.

    @param path The path of the file.
    @return Returns a hdfsFileInfo structure.
    """
    return libhdfs.hdfsGetPathInfo(self.fs, path).contents

  def getHosts(self, path, begin, offset):
    '''Get host list.
    '''
    r= libhdfs.hdfsGetHosts(self.fs, path, begin, offset)
    i=0
    ret = []
    while r[0][i]:
       ret.append(r[0][i])
       i+=1
    if r:
      libhdfs.hdfsFreeHosts(r)
    return ret

########NEW FILE########
__FILENAME__ = hfilesystem_test
#!/usr/bin/env python26

import unittest
from datetime import datetime
from hdfs.hfilesystem import Hfilesystem
from hdfs.hfile import Hfile

hostname = 'hadoop.twitter.com'
port = 8020
path = '/user/travis/test_%s' % datetime.now().strftime('%Y%m%dT%H%M%SZ')
data = 'read write test'


class HfilesystemTestCase(unittest.TestCase):

  def test_filesystem(self):
    hfile = Hfile(hostname, port, path, mode='w')
    hfile.close()

    fs = Hfilesystem(hostname, port)

    self.assertTrue(fs.exists(path))
    self.assertFalse(fs.exists(path + 'doesnotexist'))

    self.assertTrue(fs.rename(path, path + 'renamed'))

    self.assertTrue(fs.delete(path + 'renamed'))
    self.assertFalse(fs.delete(path))

  def test_mkdir(self):
    fs = Hfilesystem(hostname, port)
    self.assertTrue(fs.mkdir(path))
    self.assertTrue(fs.delete(path))


if __name__ == '__main__':
  test_cases = [HfilesystemTestCase,
               ]
  for test_case in test_cases:
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = hfile_test
#!/usr/bin/env python26

import unittest
from datetime import datetime
from hdfs.hfile import Hfile

hostname = 'hadoop.twitter.com'
port = 8020
path = '/user/travis/test_%s' % datetime.now().strftime('%Y%m%dT%H%M%SZ')
data = 'read write test'


class FileTestCase(unittest.TestCase):

  def test_file(self):
    hfile = Hfile(hostname, port, path, mode='w')
    self.assertTrue(hfile.write(data))
    hfile.close()

    hfile = Hfile(hostname, port, path)

    self.assertTrue(hfile.seek(10))
    self.assertEqual(hfile.tell(), 10)
    hfile.seek(0)

    read_data = hfile.read()
    self.assertEqual(read_data, data)

    hfile.close()

  def test_iter_with_trailing_newline(self):
    write_data = 'a\nb\nc\n'
    hfile = Hfile(hostname, port, path, mode='w')
    self.assertTrue(hfile.write(write_data))
    hfile.close()

    hfile = Hfile(hostname, port, path)
    read_data = ''
    for line in hfile:
      read_data += line

    self.assertEqual(write_data, read_data)

  def test_iter_without_trailing_newline(self):
    write_data = 'a\nb\nc'
    hfile = Hfile(hostname, port, path, mode='w')
    self.assertTrue(hfile.write(write_data))
    hfile.close()

    hfile = Hfile(hostname, port, path)
    read_data = ''
    for line in hfile:
      read_data += line

    self.assertEqual(write_data, read_data)

if __name__ == '__main__':
  test_cases = [FileTestCase,
               ]
  for test_case in test_cases:
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = _common
import os
from ctypes import *

tSize = c_int32
tTime = c_long
tOffset = c_int64
tPort = c_uint16
hdfsFS = c_void_p
hdfsFile = c_void_p

class HdfsError(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

if not os.getenv("CLASSPATH"):
  raise HdfsError('Failed loading libhdfs.so because CLASSPATH environment variable is not set.')

class tObjectKind(Structure):
  _fields_ = [('kObjectKindFile', c_char),
              ('kObjectKindDirectory', c_char)]

class hdfsFileInfo(Structure):
  _fields_ = [('mKind', tObjectKind),      # file or directory
              ('mName', c_char_p),         # the name of the file
              ('mLastMod', tTime),         # the last modification time for the file in seconds
              ('mSize', c_longlong),       # the size of the file in bytes
              ('mReplication', c_short),   # the count of replicas
              ('mBlockSize', c_longlong),  # the block size for the file
              ('mOwner', c_char_p),        # the owner of the file
              ('mGroup', c_char_p),        # the group associated with the file
              ('mPermissions', c_short),   # the permissions associated with the file
              ('mLastAccess', tTime)]      # the last access time for the file in seconds

libhdfs = cdll.LoadLibrary('libhdfs.so')
libhdfs.hdfsAvailable.argtypes = [hdfsFS, hdfsFile]
libhdfs.hdfsChmod.argtypes = [hdfsFS, c_char_p, c_short]
libhdfs.hdfsChown.argtypes = [hdfsFS, c_char_p, c_char_p, c_char_p]
libhdfs.hdfsCloseFile.argtypes = [hdfsFS, hdfsFile]
libhdfs.hdfsConnect.argtypes = [c_char_p, tPort]
libhdfs.hdfsConnect.restype = hdfsFS
libhdfs.hdfsCopy.argtypes = [hdfsFS, c_char_p, hdfsFS, c_char_p]
libhdfs.hdfsCreateDirectory.argtypes = [hdfsFS, c_char_p]
libhdfs.hdfsDelete.argtypes = [hdfsFS, c_char_p]
libhdfs.hdfsDisconnect.argtypes = [hdfsFS]
libhdfs.hdfsExists.argtypes = [hdfsFS, c_char_p]
libhdfs.hdfsFlush.argtypes = [hdfsFS, hdfsFile]
libhdfs.hdfsGetCapacity.argtypes = [hdfsFS]
libhdfs.hdfsGetCapacity.restype = tOffset
libhdfs.hdfsGetDefaultBlockSize.argtypes = [hdfsFS]
libhdfs.hdfsGetDefaultBlockSize.restype = tOffset
libhdfs.hdfsGetPathInfo.argtypes = [hdfsFS, c_char_p]
libhdfs.hdfsGetPathInfo.restype = POINTER(hdfsFileInfo)
libhdfs.hdfsGetUsed.argtypes = [hdfsFS]
libhdfs.hdfsGetUsed.restype = tOffset
libhdfs.hdfsListDirectory.argtypes = [hdfsFS, c_char_p, POINTER(c_int)]
libhdfs.hdfsListDirectory.restype = POINTER(hdfsFileInfo)
libhdfs.hdfsMove.argtypes = [hdfsFS, c_char_p, hdfsFS, c_char_p]
libhdfs.hdfsOpenFile.argtypes = [hdfsFS, c_char_p, c_int, c_int, c_short, tSize]
libhdfs.hdfsOpenFile.restype = hdfsFile
libhdfs.hdfsPread.argtypes = [hdfsFS, hdfsFile, tOffset, c_void_p, tSize]
libhdfs.hdfsPread.restype = tSize
libhdfs.hdfsRead.argtypes = [hdfsFS, hdfsFile, c_void_p, tSize]
libhdfs.hdfsRead.restype = tSize
libhdfs.hdfsRename.argtypes = [hdfsFS, c_char_p, c_char_p]
libhdfs.hdfsSeek.argtypes = [hdfsFS, hdfsFile, tOffset]
libhdfs.hdfsSetReplication.argtypes = [hdfsFS, c_char_p, c_int16]
libhdfs.hdfsTell.argtypes = [hdfsFS, hdfsFile]
libhdfs.hdfsTell.restype = tOffset
libhdfs.hdfsUtime.argtypes = [hdfsFS, c_char_p, tTime, tTime]
libhdfs.hdfsWrite.argtypes = [hdfsFS, hdfsFile, c_void_p, tSize]
libhdfs.hdfsWrite.restype = tSize
libhdfs.hdfsGetHosts.restype = POINTER(POINTER(c_char_p))
libhdfs.hdfsGetHosts.argtypes = [hdfsFS, c_char_p, tOffset, tOffset]

########NEW FILE########
