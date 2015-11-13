__FILENAME__ = dedupfs
#!/usr/bin/python

# Documentation. {{{1

"""
This Python script implements a file system in user space using FUSE. It's
called DedupFS because the file system's primary feature is deduplication,
which enables it to store virtually unlimited copies of files because data
is only stored once.

In addition to deduplication the file system also supports transparent
compression using any of the compression methods lzo, zlib and bz2.

These two properties make the file system ideal for backups: I'm currently
storing 250 GB worth of backups using only 8 GB of disk space.

The latest version is available at http://peterodding.com/code/dedupfs/

DedupFS is licensed under the MIT license.
Copyright 2010 Peter Odding <peter@peterodding.com>.
"""

# Imports. {{{1

# Check the Python version, warn the user if untested.
import sys
if sys.version_info[:2] != (2, 6):
  msg = "Warning: DedupFS has only been tested on Python 2.6, while you're running Python %d.%d!\n"
  sys.stderr.write(msg % (sys.version_info[0], sys.version_info[1]))

# Try to load the required modules from Python's standard library.
try:
  import cStringIO
  import errno
  import hashlib
  import logging
  import math
  import os
  import sqlite3
  import stat
  import time
  import traceback
except ImportError, e:
  msg = "Error: Failed to load one of the required Python modules! (%s)\n"
  sys.stderr.write(msg % str(e))
  sys.exit(1)

# Try to load the Python FUSE binding.
try:
  import fuse
except ImportError:
  sys.stderr.write("Error: The Python FUSE binding isn't installed!\n" + \
      "If you're on Ubuntu try running `sudo apt-get install python-fuse'.\n")
  sys.exit(1)

# Local modules that are mostly useful for debugging.
from my_formats import format_size, format_timespan
from get_memory_usage import get_memory_usage

def main(): # {{{1
  """
  This function enables using dedupfs.py as a shell script that creates FUSE
  mount points. Execute "dedupfs -h" for a list of valid command line options.
  """

  dfs = DedupFS()

  # A short usage message with the command line options defined by dedupfs
  # itself (see the __init__() method of the DedupFS class) is automatically
  # printed by the following call when sys.argv contains -h or --help.
  fuse_opts = dfs.parse(['-o', 'use_ino,default_permissions,fsname=dedupfs'] + sys.argv[1:])

  dfs_opts = dfs.cmdline[0]
  if dfs_opts.print_stats:
    dfs.read_only = True
    dfs.fsinit(silent=True)
    dfs.report_disk_usage()
    dfs.fsdestroy(silent=True)

  # If the user didn't pass -h or --help and also didn't supply a mount point
  # as a positional argument, print the short usage message and exit (I don't
  # agree with the Python FUSE binding's default behavior, which is something
  # nonsensical like using the working directory as a mount point).
  elif dfs.fuse_args.mount_expected() and not fuse_opts.mountpoint:
    dfs.parse(['-h'])
  elif fuse_opts.mountpoint or not dfs.fuse_args.mount_expected():
    # Don't print all options unless the user passed -h or --help explicitly
    # because this listing includes the 20+ options defined by the Python FUSE
    # binding (which is kind of intimidating at first).
    dfs.main()

class DedupFS(fuse.Fuse): # {{{1

  def __init__(self, *args, **kw):  # {{{2

    try:

      # Set the Python FUSE API version.
      fuse.fuse_python_api = (0, 2)

      # Initialize the FUSE binding's internal state.
      fuse.Fuse.__init__(self, *args, **kw)

      # Set some options required by the Python FUSE binding.
      self.flags = 0
      self.multithreaded = 0

      # Initialize instance attributes.
      self.block_size = 1024 * 128
      self.buffers = {}
      self.bytes_read = 0
      self.bytes_written = 0
      self.cache_gc_last_run = time.time()
      self.cache_requests = 0
      self.cache_timeout = 60 # TODO Make this a command line option!
      self.cached_nodes = {}
      self.calls_log_filter = []
      self.datastore_file = '~/.dedupfs-datastore.db'
      self.fs_mounted_at = time.time()
      self.gc_enabled = True
      self.gc_hook_last_run = time.time()
      self.gc_interval = 60
      self.link_mode = stat.S_IFLNK | 0777
      self.memory_usage = 0
      self.metastore_file = '~/.dedupfs-metastore.sqlite3'
      self.opcount = 0
      self.read_only = False
      self.root_mode = stat.S_IFDIR | 0755
      self.time_spent_caching_nodes = 0
      self.time_spent_hashing = 0
      self.time_spent_interning = 0
      self.time_spent_querying_tree = 0
      self.time_spent_reading = 0
      self.time_spent_traversing_tree = 0
      self.time_spent_writing = 0
      self.time_spent_writing_blocks = 0
      self.__NODE_KEY_VALUE = 0
      self.__NODE_KEY_LAST_USED = 1

      # Initialize a Logger() object to handle logging.
      self.logger = logging.getLogger('dedupfs')
      self.logger.setLevel(logging.INFO)
      self.logger.addHandler(logging.StreamHandler(sys.stderr))

      # Register some custom command line options with the option parser.
      option_stored_in_db = " (this option is only useful when creating a new database, because your choice is stored in the database and can't be changed after that)"
      self.parser.set_conflict_handler('resolve') # enable overriding the --help message.
      self.parser.add_option('-h', '--help', action='help', help="show this help message followed by the command line options defined by the Python FUSE binding and exit")
      self.parser.add_option('-v', '--verbose', action='count', dest='verbosity', default=0, help="increase verbosity")
      self.parser.add_option('--print-stats', dest='print_stats', action='store_true', default=False, help="print the total apparent size and the actual disk usage of the file system and exit")
      self.parser.add_option('--log-file', dest='log_file', help="specify log file location")
      self.parser.add_option('--metastore', dest='metastore', metavar='FILE', default=self.metastore_file, help="specify the location of the file in which metadata is stored")
      self.parser.add_option('--datastore', dest='datastore', metavar='FILE', default=self.datastore_file, help="specify the location of the file in which data blocks are stored")
      self.parser.add_option('--block-size', dest='block_size', metavar='BYTES', default=self.block_size, type='int', help="specify the maximum block size in bytes" + option_stored_in_db)
      self.parser.add_option('--no-transactions', dest='use_transactions', action='store_false', default=True, help="don't use transactions when making multiple related changes, this might make the file system faster or slower (?)")
      self.parser.add_option('--nosync', dest='synchronous', action='store_false', default=True, help="disable SQLite's normal synchronous behavior which guarantees that data is written to disk immediately, because it slows down the file system too much (this means you might lose data when the mount point isn't cleanly unmounted)")
      self.parser.add_option('--nogc', dest='gc_enabled', action='store_false', default=True, help="disable the periodic garbage collection because it degrades performance (only do this when you've got disk space to waste or you know that nothing will be be deleted from the file system, which means little to no garbage will be produced)")
      self.parser.add_option('--verify-writes', dest='verify_writes', action='store_true', default=False, help="after writing a new data block to the database, check that the block was written correctly by reading it back again and checking for differences")

      # Dynamically check for supported hashing algorithms.
      msg = "specify the hashing algorithm that will be used to recognize duplicate data blocks: one of %s" + option_stored_in_db
      hash_functions = filter(lambda m: m[0] != '_' and m != 'new', dir(hashlib))
      msg %= ', '.join('%r' % fun for fun in hash_functions)
      self.parser.add_option('--hash', dest='hash_function', metavar='FUNCTION', type='choice', choices=hash_functions, default='sha1', help=msg)

      # Dynamically check for supported compression methods.
      def noop(s): return s
      self.compressors = { 'none': (noop, noop) }
      compression_methods = ['none']
      for modname in 'lzo', 'zlib', 'bz2':
        try:
          module = __import__(modname)
          if hasattr(module, 'compress') and hasattr(module, 'decompress'):
            self.compressors[modname] = (module.compress, module.decompress)
            compression_methods.append(modname)
        except ImportError:
          pass
      msg = "enable compression of data blocks using one of the supported compression methods: one of %s" + option_stored_in_db
      msg %= ', '.join('%r' % mth for mth in compression_methods[1:])
      self.parser.add_option('--compress', dest='compression_method', metavar='METHOD', type='choice', choices=compression_methods, default='none', help=msg)

      # Dynamically check for profiling support.
      try:
        # Using __import__() here because of pyflakes.
        for p in 'cProfile', 'pstats': __import__(p)
        self.parser.add_option('--profile', action='store_true', default=False, help="use the Python modules cProfile and pstats to create a profile of time spent in various function calls and print out a table of the slowest functions at exit (of course this slows everything down but it can nevertheless give a good indication of the hot spots)")
      except ImportError:
        self.logger.warning("No profiling support available, --profile option disabled.")
        self.logger.warning("If you're on Ubuntu try `sudo apt-get install python-profiler'.")

    except Exception, e:
      self.__except_to_status('__init__', e)
      sys.exit(1)

  # FUSE API implementation: {{{2

  def access(self, path, flags): # {{{3
    try:
      self.__log_call('access', 'access(%r, %o)', path, flags)
      inode = self.__path2keys(path)[1]
      if flags != os.F_OK and not self.__access(inode, flags):
        return -errno.EACCES
      return 0
    except Exception, e:
      return self.__except_to_status('access', e, errno.ENOENT)

  def chmod(self, path, mode): # {{{3
    try:
      self.__log_call('chmod', 'chmod(%r, %o)', path, mode)
      if self.read_only: return -errno.EROFS
      inode = self.__path2keys(path)[1]
      self.conn.execute('UPDATE inodes SET mode = ? WHERE inode = ?', (mode, inode))
      self.__gc_hook()
      return 0
    except Exception, e:
      return self.__except_to_status('chmod', e, errno.EIO)

  def chown(self, path, uid, gid): # {{{3
    try:
      self.__log_call('chown', 'chown(%r, %i, %i)', path, uid, gid)
      if self.read_only: return -errno.EROFS
      inode = self.__path2keys(path)[1]
      self.conn.execute('UPDATE inodes SET uid = ?, gid = ? WHERE inode = ?', (uid, gid, inode))
      self.__gc_hook()
      return 0
    except Exception, e:
      return self.__except_to_status('chown', e, errno.EIO)

  def create(self, path, flags, mode): # {{{3
    try:
      self.__log_call('create', 'create(%r, %o, %o)', path, flags, mode)
      if self.read_only: return -errno.EROFS
      try:
        # If the file already exists, just open it.
        status = self.open(path, flags, nested=True)
      except OSError, e:
        if e.errno != errno.ENOENT: raise
        # Otherwise create a new file and open that.
        inode, parent_ino = self.__insert(path, mode, 0)
        status = self.open(path, flags, nested=True, inode=inode)
      self.__commit_changes()
      self.__gc_hook()
      return status
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('create', e, errno.EIO)

  def fsdestroy(self, silent=False): # {{{3
    try:
      self.__log_call('fsdestroy', 'fsdestroy()')
      self.__collect_garbage()
      if not silent:
        self.__print_stats()
      if not self.read_only:
        self.logger.info("Committing outstanding changes to `%s'.", self.metastore_file)
        self.__dbmcall('sync')
        self.conn.commit()
      self.conn.close()
      self.__dbmcall('close')
      return 0
    except Exception, e:
      return self.__except_to_status('fsdestroy', e, errno.EIO)

  def fsinit(self, silent=False): # {{{3
    try:
      # Process the custom command line options defined in __init__().
      options = self.cmdline[0]
      self.block_size = options.block_size
      self.compression_method = options.compression_method
      self.datastore_file = self.__check_data_file(options.datastore, silent)
      self.gc_enabled = options.gc_enabled
      self.hash_function = options.hash_function
      self.metastore_file = self.__check_data_file(options.metastore, silent)
      self.synchronous = options.synchronous
      self.use_transactions = options.use_transactions
      self.verify_writes = options.verify_writes
      # Initialize the logging and database subsystems.
      self.__init_logging(options)
      self.__log_call('fsinit', 'fsinit()')
      self.__setup_database_connections(silent)
      if not self.read_only:
        self.__init_metastore()
      self.__get_opts_from_db(options)
      # Make sure the hash function is (still) valid (since the database was created).
      if not hasattr(hashlib, self.hash_function):
        self.logger.critical("Error: The selected hash function %r doesn't exist!", self.hash_function)
        sys.exit(1)
      # Get a reference to the hash function.
      self.hash_function_impl = getattr(hashlib, self.hash_function)
      # Disable synchronous operation. This is supposed to make SQLite perform
      # MUCH better but it has to be enabled wit --nosync because you might
      # lose data when the file system isn't cleanly unmounted...
      if not self.synchronous and not self.read_only:
        self.logger.warning("Warning: Disabling synchronous operation, you might lose data..")
        self.conn.execute('PRAGMA synchronous = OFF')
      # Select the compression method (if any) after potentially reading the
      # configured block size that was used to create the database (see the
      # set_block_size() call).
      self.__select_compress_method(options, silent)
      return 0
    except Exception, e:
      self.__except_to_status('fsinit', e, errno.EIO)
      # Bug fix: Break the mount point when initialization failed with an
      # exception, because self.conn might not be valid, which results in
      # an internal error message for every FUSE API call...
      os._exit(1)

  def getattr(self, path): # {{{3
    try:
      self.__log_call('getattr', 'getattr(%r)', path)
      inode = self.__path2keys(path)[1]
      query = 'SELECT inode, nlinks, mode, uid, gid, rdev, size, atime, mtime, ctime FROM inodes WHERE inode = ?'
      attrs = self.conn.execute(query, (inode,)).fetchone()
      result = Stat(st_ino     = attrs[0],
                    st_nlink   = attrs[1],
                    st_mode    = attrs[2],
                    st_uid     = attrs[3],
                    st_gid     = attrs[4],
                    st_rdev    = attrs[5],
                    st_size    = attrs[6],
                    st_atime   = attrs[7],
                    st_mtime   = attrs[8],
                    st_ctime   = attrs[9],
                    st_blksize = self.block_size,
                    st_blocks  = attrs[6] / 512,
                    st_dev     = 0)
      self.logger.debug("getattr(%r) returning %s", path, result)
      return result
    except Exception, e:
      self.logger.debug("getattr(%r) returning ENOENT", path)
      return self.__except_to_status('getattr', e, errno.ENOENT)

  def link(self, target_path, link_path, nested=False): # {{{3
    # From the link(2) manual page: "If link_path names a directory, link()
    # shall fail unless the process has appropriate privileges and the
    # implementation supports using link() on directories." ... :-)
    # However I've read that FUSE doesn't like multiple directory pathnames
    # with the same inode number (maybe because of internal caching based on
    # inode numbers?).
    try:
      self.__log_call('link', '%slink(%r -> %r)', nested and ' ' or '', target_path, link_path)
      if self.read_only: return -errno.EROFS
      target_ino = self.__path2keys(target_path)[1]
      link_parent, link_name = os.path.split(link_path)
      link_parent_id, link_parent_ino = self.__path2keys(link_parent)
      string_id = self.__intern(link_name)
      self.conn.execute('INSERT INTO tree (parent_id, name, inode) VALUES (?, ?, ?)', (link_parent_id, string_id, target_ino))
      node_id = self.__fetchval('SELECT last_insert_rowid()')
      self.conn.execute('UPDATE inodes SET nlinks = nlinks + 1 WHERE inode = ?', (target_ino,))
      if self.__fetchval('SELECT mode FROM inodes WHERE inode = ?', target_ino) & stat.S_IFDIR:
        self.conn.execute('UPDATE inodes SET nlinks = nlinks + 1 WHERE inode = ?', (link_parent_ino,))
      self.__cache_set(link_path, (node_id, target_ino))
      self.__commit_changes(nested)
      self.__gc_hook(nested)
      return 0
    except Exception, e:
      self.__rollback_changes(nested)
      if nested: raise
      return self.__except_to_status('link', e, errno.EIO)

  def mkdir(self, path, mode): # {{{3
    try:
      self.__log_call('mkdir', 'mkdir(%r, %o)', path, mode)
      if self.read_only: return -errno.EROFS
      inode, parent_ino = self.__insert(path, mode | stat.S_IFDIR, 1024 * 4)
      self.conn.execute('UPDATE inodes SET nlinks = nlinks + 1 WHERE inode = ?', (parent_ino,))
      self.__commit_changes()
      self.__gc_hook()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('mkdir', e, errno.EIO)

  def mknod(self, path, mode, rdev): # {{{3
    try:
      self.__log_call('mknod', 'mknod(%r, %o)', path, mode)
      if self.read_only: return -errno.EROFS
      self.__insert(path, mode, 0, rdev)
      self.__commit_changes()
      self.__gc_hook()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('mknod', e, errno.EIO)

  def open(self, path, flags, nested=None, inode=None): # {{{3
    try:
      self.__log_call('open', 'open(%r, %o)', path, flags)
      # Make sure the file exists?
      inode = inode or self.__path2keys(path)[1]
      # Make sure the file is readable and/or writable.
      access_flags = 0
      if flags & (os.O_RDONLY | os.O_RDWR): access_flags |= os.R_OK
      if flags & (os.O_WRONLY | os.O_RDWR): access_flags |= os.W_OK
      if not self.__access(inode, access_flags):
        return -errno.EACCES
      return 0
    except Exception, e:
      if nested: raise
      return self.__except_to_status('open', e, errno.ENOENT)

  def read(self, path, length, offset): # {{{3
    try:
      self.__log_call('read', 'read(%r, %i, %i)', path, length, offset)
      start_time = time.time()
      buf = self.__get_file_buffer(path)
      buf.seek(offset)
      data = buf.read(length)
      self.time_spent_reading += time.time() - start_time
      self.bytes_read += len(data)
      return data
    except Exception, e:
      return self.__except_to_status('read', e, code=errno.EIO)

  def readdir(self, path, offset): # {{{3
    # Bug fix: When you use the -o use_ino option, directory entries must have
    # an "ino" field, otherwise not a single directory entry will be listed!
    try:
      self.__log_call('readdir', 'readdir(%r, %i)', path, offset)
      node_id, inode = self.__path2keys(path)
      yield fuse.Direntry('.', ino=inode)
      yield fuse.Direntry('..')
      query = "SELECT t.inode, s.value FROM tree t, strings s WHERE t.parent_id = ? AND t.name = s.id"
      for inode, name in self.conn.execute(query, (node_id,)).fetchall():
        yield fuse.Direntry(str(name), ino=inode)
    except Exception, e:
      self.__except_to_status('readdir', e)

  def readlink(self, path): # {{{3
    try:
      self.__log_call('readlink', 'readlink(%r)', path)
      inode = self.__path2keys(path)[1]
      query = 'SELECT target FROM links WHERE inode = ?'
      return str(self.__fetchval(query, inode))
    except Exception, e:
      return self.__except_to_status('readlink', e, errno.ENOENT)

  def release(self, path, flags): # {{{3
    try:
      self.__log_call('release', 'release(%r, %o)', path, flags)
      # Flush the write buffer?!
      if path in self.buffers:
        buf = self.buffers[path]
        # Flush the write buffer?
        if buf.dirty:
          # Record start time so we can calculate average write speed.
          start_time = time.time()
          # Make sure the file exists and get its inode number.
          inode = self.__path2keys(path)[1]
          # Save apparent file size before possibly compressing data.
          apparent_size = len(buf)
          # Split up that string in the configured block size, hash the
          # resulting blocks and store any new blocks.
          try:
            self.__write_blocks(inode, buf, apparent_size)
            self.__commit_changes()
          except Exception, e:
            self.__rollback_changes()
            raise
          # Record the number of bytes written and the elapsed time.
          self.bytes_written += apparent_size
          self.time_spent_writing += time.time() - start_time
          self.__gc_hook()
        # Delete the buffer.
        buf.close()
        del self.buffers[path]
      return 0
    except Exception, e:
      return self.__except_to_status('release', e, errno.EIO)

  def rename(self, old_path, new_path): # {{{3
    try:
      self.__log_call('rename', 'rename(%r -> %r)', old_path, new_path)
      if self.read_only: return -errno.EROFS
      # Try to remove the existing target path (if if exists).
      # NB: This also makes sure target directories are empty.
      try:
        self.__remove(new_path, check_empty=True)
      except OSError, e:
        # Ignore errno.ENOENT, re raise other exceptions.
        if e.errno != errno.ENOENT: raise
      # Link the new path to the same inode as the old path.
      self.link(old_path, new_path, nested=True)
      # Finally unlink the old path.
      self.unlink(old_path, nested=True)
      self.__commit_changes()
      self.__gc_hook()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('rename', e, errno.ENOENT)

  def rmdir(self, path): # {{{3
    try:
      self.__log_call('rmdir', 'rmdir(%r)', path)
      if self.read_only: return -errno.EROFS
      self.__remove(path, check_empty=True)
      self.__commit_changes()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('rmdir', e, errno.ENOENT)

  def statfs(self): # {{{3
    try:
      self.__log_call('statfs', 'statfs()')
      # Use os.statvfs() to report the host file system's storage capacity.
      host_fs = os.statvfs(self.metastore_file)
      return StatVFS(f_bavail  = (host_fs.f_bsize * host_fs.f_bavail) / self.block_size, # The total number of free blocks available to a non privileged process.
                     f_bfree   = (host_fs.f_frsize * host_fs.f_bfree) / self.block_size, # The total number of free blocks in the file system.
                     f_blocks  = (host_fs.f_frsize * host_fs.f_blocks) / self.block_size, # The total number of blocks in the file system in terms of f_frsize.
                     f_bsize   = self.block_size, # The file system block size in bytes.
                     f_favail  = 0, # The number of free file serial numbers available to a non privileged process.
                     f_ffree   = 0, # The total number of free file serial numbers.
                     f_files   = 0, # The total number of file serial numbers.
                     f_flag    = 0, # File system flags. Symbols are defined in the <sys/statvfs.h> header file to refer to bits in this field (see The f_flags field).
                     f_frsize  = self.block_size, # The fundamental file system block size in bytes.
                     f_namemax = 4294967295) # The maximum file name length in the file system. Some file systems may return the maximum value that can be stored in an unsigned long to indicate the file system has no maximum file name length. The maximum value that can be stored in an unsigned long is defined in <limits.h> as ULONG_MAX.
    except Exception, e:
      return self.__except_to_status('statfs', e, errno.EIO)


  def symlink(self, target_path, link_path): # {{{3
    try:
      self.__log_call('symlink', 'symlink(%r -> %r)', link_path, target_path)
      if self.read_only: return -errno.EROFS
      # Create an inode to hold the symbolic link.
      inode, parent_ino = self.__insert(link_path, self.link_mode, len(target_path))
      # Save the symbolic link's target.
      self.conn.execute('INSERT INTO links (inode, target) VALUES (?, ?)', (inode, sqlite3.Binary(target_path)))
      self.__commit_changes()
      self.__gc_hook()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('symlink', e, errno.EIO)

  def truncate(self, path, size): # {{{3
    try:
      self.__log_call('truncate', 'truncate(%r, %i)', path, size)
      if self.read_only: return -errno.EROFS
      inode = self.__path2keys(path)[1]
      last_block = size / self.block_size
      self.conn.execute('DELETE FROM "index" WHERE inode = ? AND block_nr > ?', (inode, last_block))
      self.conn.execute('UPDATE inodes SET size = ? WHERE inode = ?', (size, inode))
      self.__gc_hook()
      self.__commit_changes()
      return 0
    except Exception, e:
      self.__rollback_changes()
      return self.__except_to_status('truncate', e, errno.ENOENT)

  def unlink(self, path, nested=False): # {{{3
    try:
      self.__log_call('unlink', '%sunlink(%r)', nested and ' ' or '', path)
      if self.read_only: return -errno.EROFS
      self.__remove(path)
      self.__commit_changes(nested)
    except Exception, e:
      self.__rollback_changes(nested)
      if nested: raise
      return self.__except_to_status('unlink', e, errno.ENOENT)

  def utime(self, path, times): # {{{3
    try:
      self.__log_call('utime', 'utime(%r, %i, %i)', path, *times)
      if self.read_only: return -errno.EROFS
      inode = self.__path2keys(path)[1]
      atime, mtime = times
      self.conn.execute('UPDATE inodes SET atime = ?, mtime = ? WHERE inode = ?', (atime, mtime, inode))
      self.__gc_hook()
      return 0
    except Exception, e:
      return self.__except_to_status('utime', e, errno.ENOENT)

  def utimens(self, path, ts_acc, ts_mod): # {{{3
    try:
      self.__log_call('utimens', 'utimens(%r, %i.%i, %i.%i)', path, ts_acc.tv_sec, ts_acc.tv_nsec, ts_mod.tv_sec, ts_mod.tv_nsec)
      if self.read_only: return -errno.EROFS
      inode = self.__path2keys(path)[1]
      atime = ts_acc.tv_sec + (ts_acc.tv_nsec / 1000000.0)
      mtime = ts_mod.tv_sec + (ts_mod.tv_nsec / 1000000.0)
      self.conn.execute('UPDATE inodes SET atime = ?, mtime = ? WHERE inode = ?', (atime, mtime, inode))
      self.__gc_hook()
      return 0
    except Exception, e:
      return self.__except_to_status('utimens', e, errno.ENOENT)

  def write(self, path, data, offset): # {{{3
    try:
      length = len(data)
      self.__log_call('write', 'write(%r, %i, %i)', path, offset, length)
      start_time = time.time()
      buf = self.__get_file_buffer(path)
      buf.seek(offset)
      buf.write(data)
      self.time_spent_writing += time.time() - start_time
      # self.bytes_written is incremented from release().
      return length
    except Exception, e:
      return self.__except_to_status('write', e, errno.EIO)

  # Miscellaneous methods: {{{2

  def __init_logging(self, options): # {{{3
    # Configure logging of messages to a file.
    if options.log_file:
      handler = logging.StreamHandler(open(options.log_file, 'w'))
      self.logger.addHandler(handler)
    # Convert verbosity argument to logging level?
    if options.verbosity > 0:
      if options.verbosity <= 1:
        self.logger.setLevel(logging.INFO)
      elif options.verbosity <= 2:
        self.logger.setLevel(logging.DEBUG)
      else:
        self.logger.setLevel(logging.NOTSET)

  def __init_metastore(self): # {{{3
    # Bug fix: At this point fuse.FuseGetContext() returns uid = 0 and gid = 0
    # which differs from the info returned in later calls. The simple fix is to
    # use Python's os.getuid() and os.getgid() library functions instead of
    # fuse.FuseGetContext().
    uid, gid = os.getuid(), os.getgid()
    t = self.__newctime()
    self.conn.executescript("""

      -- Create the required tables?
      CREATE TABLE IF NOT EXISTS tree (id INTEGER PRIMARY KEY, parent_id INTEGER, name INTEGER NOT NULL, inode INTEGER NOT NULL, UNIQUE (parent_id, name));
      CREATE TABLE IF NOT EXISTS strings (id INTEGER PRIMARY KEY, value BLOB NOT NULL UNIQUE);
      CREATE TABLE IF NOT EXISTS inodes (inode INTEGER PRIMARY KEY, nlinks INTEGER NOT NULL, mode INTEGER NOT NULL, uid INTEGER, gid INTEGER, rdev INTEGER, size INTEGER, atime INTEGER, mtime INTEGER, ctime INTEGER);
      CREATE TABLE IF NOT EXISTS links (inode INTEGER UNIQUE, target BLOB NOT NULL);
      CREATE TABLE IF NOT EXISTS hashes (id INTEGER PRIMARY KEY, hash BLOB NOT NULL UNIQUE);
      CREATE TABLE IF NOT EXISTS "index" (inode INTEGER, hash_id INTEGER, block_nr INTEGER, PRIMARY KEY (inode, hash_id, block_nr));
      CREATE TABLE IF NOT EXISTS options (name TEXT PRIMARY KEY, value TEXT NOT NULL);

      -- Create the root node of the file system?
      INSERT OR IGNORE INTO strings (id, value) VALUES (1, '');
      INSERT OR IGNORE INTO tree (id, parent_id, name, inode) VALUES (1, NULL, 1, 1);
      INSERT OR IGNORE INTO inodes (nlinks, mode, uid, gid, rdev, size, atime, mtime, ctime) VALUES (2, %i, %i, %i, 0, 1024*4, %f, %f, %f);

      -- Save the command line options used to initialize the database?
      INSERT OR IGNORE INTO options (name, value) VALUES ('synchronous', %i);
      INSERT OR IGNORE INTO options (name, value) VALUES ('block_size', %i);
      INSERT OR IGNORE INTO options (name, value) VALUES ('compression_method', %r);
      INSERT OR IGNORE INTO options (name, value) VALUES ('hash_function', %r);

    """ % (self.root_mode, uid, gid, t, t, t, self.synchronous and 1 or 0,
           self.block_size, self.compression_method, self.hash_function))

  def __setup_database_connections(self, silent): # {{{3
    if not silent:
      self.logger.info("Using data files %r and %r.", self.metastore_file, self.datastore_file)
    # Open the key/value store containing the data blocks.
    if not os.path.exists(self.metastore_file):
      self.blocks = self.__open_datastore(True)
    else:
      from whichdb import whichdb
      created_by_gdbm = whichdb(self.metastore_file) == 'gdbm'
      self.blocks = self.__open_datastore(created_by_gdbm)
    # Open an SQLite database connection with manual transaction management.
    self.conn = sqlite3.connect(self.metastore_file, isolation_level=None)
    # Use the built in row factory to enable named attributes.
    self.conn.row_factory = sqlite3.Row
    # Return regular strings instead of Unicode objects.
    self.conn.text_factory = str
    # Don't bother releasing any locks since there's currently no point in
    # having concurrent reading/writing of the file system database.
    self.conn.execute('PRAGMA locking_mode = EXCLUSIVE')

  def __open_datastore(self, use_gdbm):
    # gdbm is preferred over other dbm implementations because it supports fast
    # vs. synchronous modes, however any other dedicated key/value store should
    # work just fine (albeit not as fast). Note though that existing key/value
    # stores are always accessed through the library that created them.
    mode = self.read_only and 'r' or 'c'
    if use_gdbm:
      try:
        import gdbm
        mode += self.synchronous and 's' or 'f'
        return gdbm.open(self.datastore_file, mode)
      except ImportError:
        pass
    import anydbm
    return anydbm.open(self.datastore_file, mode)

  def __dbmcall(self, fun): # {{{3
    # I simply cannot find any freakin' documentation on the type of objects
    # returned by anydbm and gdbm, so cannot verify that any single method will
    # always be there, although most seem to...
    if hasattr(self.blocks, fun):
      getattr(self.blocks, fun)()

  def __check_data_file(self, pathname, silent): # {{{3
    pathname = os.path.expanduser(pathname)
    if os.access(pathname, os.F_OK):
      # If the datafile already exists make sure it's readable,
      # otherwise the file system would be completely unusable.
      if not os.access(pathname, os.R_OK):
        self.logger.critical("Error: Datafile %r exists but isn't readable!", pathname)
        os._exit(1)
      # Check and respect whether the datafile is writable (e.g. when it was
      # created by root but is currently being accessed by another user).
      if not os.access(pathname, os.W_OK):
        if not silent:
          self.logger.warning("File %r exists but isn't writable! Switching to read only mode.", pathname)
        self.read_only = True
    return pathname

  def __log_call(self, fun, msg, *args): # {{{3
    # To disable all __log_call() invocations:
    #  :%s/^\(\s\+\)\(self\.__log_call\)/\1#\2
    # To re enable them:
    #  :%s/^\(\s\+\)#\(self\.__log_call\)/\1\2
    if self.calls_log_filter == [] or fun in self.calls_log_filter:
      self.logger.debug(msg, *args)

  def __get_opts_from_db(self, options): # {{{3
    for name, value in self.conn.execute('SELECT name, value FROM options'):
      if name == 'synchronous':
        self.synchronous = int(value) != 0
        # If the user passed --nosync, override the value stored in the database.
        if not options.synchronous:
          self.synchronous = False
      elif name == 'block_size' and int(value) != self.block_size:
        self.logger.warning("Ignoring --block-size=%i argument, using previously chosen block size %i instead", self.block_size, int(value))
        self.block_size = int(value)
      elif name == 'compression_method' and value != self.compression_method:
        if self.compression_method != 'none':
          self.logger.warning("Ignoring --compress=%s argument, using previously chosen compression method %r instead", self.compression_method, value)
        self.compression_method = value
      elif name == 'hash_function' and value != self.hash_function:
        self.logger.warning("Ignoring --hash=%s argument, using previously chosen hash function %r instead", self.hash_function, value)
        self.hash_function = value

  def __select_compress_method(self, options, silent): # {{{3
    valid_formats = self.compressors.keys()
    selected_format = self.compression_method.lower()
    if selected_format not in valid_formats:
      self.logger.warning("Invalid compression format `%s' selected!", selected_format)
      selected_format = 'none'
    if selected_format != 'none':
      if not silent:
        self.logger.debug("Using the %s compression method.", selected_format)
      # My custom LZO binding defines set_block_size() which enables
      # optimizations like preallocating a buffer that can be reused for
      # every call to compress() and decompress().
      if selected_format == 'lzo':
        module = __import__('lzo')
        if hasattr(module, 'set_block_size'):
          module.set_block_size(self.block_size)
    self.compress, self.decompress = self.compressors[selected_format]

  def __write_blocks(self, inode, buf, apparent_size): # {{{3
    start_time = time.time()
    # Delete existing index entries for file.
    self.conn.execute('DELETE FROM "index" WHERE inode = ?', (inode,))
    # Store any changed blocks and rebuild the file index.
    storage_size = len(buf)
    for block_nr in xrange(int(math.ceil(storage_size / float(self.block_size)))):
      buf.seek(self.block_size * block_nr, os.SEEK_SET)
      new_block = buf.read(self.block_size)
      digest = self.__hash(new_block)
      encoded_digest = sqlite3.Binary(digest)
      row = self.conn.execute('SELECT id FROM hashes WHERE hash = ?', (encoded_digest,)).fetchone()
      if row:
        hash_id = row[0]
        existing_block = self.decompress(self.blocks[digest])
        # Check for hash collisions.
        if new_block != existing_block:
          # Found a hash collision: dump debugging info and exit.
          dumpfile_collision = '/tmp/dedupfs-collision-%i' % time.time()
          handle = open(dumpfile_collision, 'w')
          handle.write('Content of existing block is %r.\n' % existing_block)
          handle.write('Content of new block is %r.\n' % new_block)
          handle.close()
          self.logger.critical(
              "Found a hash collision on block number %i of inode %i!\n" + \
              "The existing block is %i bytes and hashes to %s.\n"   + \
              "The new block is %i bytes and hashes to %s.\n"        + \
              "Saved existing and conflicting data blocks to %r.",
              block_nr, inode, len(existing_block), digest,
              len(new_block), digest, dumpfile_collision)
          os._exit(1)
        self.conn.execute('INSERT INTO "index" (inode, hash_id, block_nr) VALUES (?, ?, ?)', (inode, hash_id, block_nr))
      else:
        self.blocks[digest] = self.compress(new_block)
        self.conn.execute('INSERT INTO hashes (id, hash) VALUES (NULL, ?)', (encoded_digest,))
        self.conn.execute('INSERT INTO "index" (inode, hash_id, block_nr) VALUES (?, last_insert_rowid(), ?)', (inode, block_nr))
        # Check that the data was properly stored in the database?
        self.__verify_write(new_block, digest, block_nr, inode)
      block_nr += 1
    # Update file size and last modified time.
    self.conn.execute('UPDATE inodes SET size = ?, mtime = ? WHERE inode = ?', (apparent_size, self.__newctime(), inode))
    self.time_spent_writing_blocks += time.time() - start_time

  def __insert(self, path, mode, size, rdev=0): # {{{3
    parent, name = os.path.split(path)
    parent_id, parent_ino = self.__path2keys(parent)
    nlinks = mode & stat.S_IFDIR and 2 or 1
    t = self.__newctime()
    uid, gid = self.__getctx()
    self.conn.execute('INSERT INTO inodes (nlinks, mode, uid, gid, rdev, size, atime, mtime, ctime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (nlinks, mode, uid, gid, rdev, size, t, t, t))
    inode = self.__fetchval('SELECT last_insert_rowid()')
    string_id = self.__intern(name)
    self.conn.execute('INSERT INTO tree (parent_id, name, inode) VALUES (?, ?, ?)', (parent_id, string_id, inode))
    node_id = self.__fetchval('SELECT last_insert_rowid()')
    self.__cache_set(path, (node_id, inode))
    return inode, parent_ino

  def __intern(self, string): # {{{3
    start_time = time.time()
    args = (sqlite3.Binary(string),)
    result = self.conn.execute('SELECT id FROM strings WHERE value = ?', args).fetchone()
    if not result:
      self.conn.execute('INSERT INTO strings (id, value) VALUES (NULL, ?)', args)
      result = self.conn.execute('SELECT last_insert_rowid()').fetchone()
    self.time_spent_interning += time.time() - start_time
    return int(result[0])

  def __remove(self, path, check_empty=False): # {{{3
    node_id, inode = self.__path2keys(path)
    # Make sure directories are empty before deleting them to avoid orphaned inodes.
    query = """ SELECT COUNT(t.id) FROM tree t, inodes i WHERE
                t.parent_id = ? AND i.inode = t.inode AND i.nlinks > 0 """
    if check_empty and self.__fetchval(query, node_id) > 0:
      raise OSError, (errno.ENOTEMPTY, os.strerror(errno.ENOTEMPTY), path)
    self.__cache_set(path, None)
    self.conn.execute('DELETE FROM tree WHERE id = ?', (node_id,))
    self.conn.execute('UPDATE inodes SET nlinks = nlinks - 1 WHERE inode = ?', (inode,))
    # Inodes with nlinks = 0 are purged periodically from __collect_garbage() so
    # we don't have to do that here.
    if self.__fetchval('SELECT mode FROM inodes where inode = ?', inode) & stat.S_IFDIR:
      parent_id, parent_ino = self.__path2keys(os.path.split(path)[0])
      self.conn.execute('UPDATE inodes SET nlinks = nlinks - 1 WHERE inode = ?', (parent_ino,))

  def __verify_write(self, block, digest, block_nr, inode): # {{{3
    if self.verify_writes:
      saved_value = self.decompress(self.blocks[digest])
      if saved_value != block:
        # The data block was corrupted when it was written or read.
        dumpfile_corruption = '/tmp/dedupfs-corruption-%i' % time.time()
        handle = open(dumpfile_corruption, 'w')
        handle.write('The content that should have been stored is %r.\n' % block)
        handle.write('The content that was retrieved from the database is %r.\n' % saved_value)
        handle.close()
        self.logger.critical(
            "Failed to verify data with block number %i of inode %i!\n" + \
            "Saved original and corrupted data blocks to %i.",
            block_nr, inode, dumpfile_corruption)
        os._exit(1)

  def __access(self, inode, flags): # {{{3
    # Check if the flags include writing while the database is read only.
    if self.read_only and flags & os.W_OK:
      return False
    # Get the path's mode, owner and group through the inode.
    query = 'SELECT mode, uid, gid FROM inodes WHERE inode = ?'
    attrs = self.conn.execute(query, (inode,)).fetchone()
    # Determine by whom the request is being made.
    uid, gid = self.__getctx()
    o = uid == attrs['uid'] # access by same user id?
    g = gid == attrs['gid'] and not o # access by same group id?
    # Note: "and not o" added after experimenting with EXT4.
    w = not (o or g) # anything else
    m = attrs['mode']
    # The essence of UNIX file permissions. Did I miss anything?! (Probably...)
    return (not (flags & os.R_OK) or ((o and (m & 0400)) or (g and (m & 0040)) or (w and (m & 0004)))) \
       and (not (flags & os.W_OK) or ((o and (m & 0200)) or (g and (m & 0020)) or (w and (m & 0002)))) \
       and (not (flags & os.X_OK) or ((o and (m & 0100)) or (g and (m & 0010)) or (w and (m & 0001))))

  def __path2keys(self, path): # {{{3
    node_id, inode = 1, 1
    if path == '/':
      return node_id, inode
    start_time = time.time()
    node = self.cached_nodes
    parent_id = node_id
    for segment in self.__split_segments(path):
      if segment in node:
        node = node[segment]
        node[self.__NODE_KEY_LAST_USED] = start_time
        node_id, inode = node[self.__NODE_KEY_VALUE]
      else:
        query_start_time = time.time()
        query = 'SELECT t.id, t.inode FROM tree t, strings s WHERE t.parent_id = ? AND t.name = s.id AND s.value = ? LIMIT 1'
        result = self.conn.execute(query, (parent_id, sqlite3.Binary(segment))).fetchone()
        self.time_spent_querying_tree += time.time() - query_start_time
        if result == None:
          self.__cache_check_gc()
          self.time_spent_traversing_tree += time.time() - start_time
          raise OSError, (errno.ENOENT, os.strerror(errno.ENOENT), path)
        node_id, inode = result
        new_node = { self.__NODE_KEY_VALUE: (node_id, inode), self.__NODE_KEY_LAST_USED: start_time }
        node[segment] = new_node
        node = new_node
      parent_id = node_id
    self.__cache_check_gc()
    self.time_spent_traversing_tree += time.time() - start_time
    return node_id, inode

  def __cache_set(self, key, value): # {{{3
    segments = self.__split_segments(key)
    last_segment = segments.pop(-1)
    node = self.cached_nodes
    time_now = time.time()
    for segment in segments:
      # Check that the keys of the sub path have been cached.
      if segment not in node:
        self.time_spent_caching_nodes += time.time() - time_now
        return False
      # Resolve the next path segment.
      node = node[segment]
      # Update the last used time of the sub path.
      node[self.__NODE_KEY_LAST_USED] = time_now
    if not value:
      # Delete the path's keys.
      if last_segment in node:
        del node[last_segment]
    elif last_segment not in node:
      # Create the path's keys.
      node[last_segment] = { self.__NODE_KEY_VALUE: value, self.__NODE_KEY_LAST_USED: time_now }
    else:
      # Update the path's keys.
      node = node[last_segment]
      node[self.__NODE_KEY_VALUE] = value
      node[self.__NODE_KEY_LAST_USED] = time_now
    self.__cache_check_gc()
    self.time_spent_caching_nodes += time.time() - time_now
    return True

  def __cache_check_gc(self): # {{{3
    self.cache_requests += 1
    if self.cache_requests >= 2500:
      time_now = time.time()
      if time_now - self.cache_gc_last_run >= self.cache_timeout:
        self.__cache_do_gc(self.cached_nodes, time_now)
        self.cache_gc_last_run = time_now
      self.cache_requests = 0

  def __cache_do_gc(self, node, time_now): # {{{3
    for key in node.keys():
      child = node[key]
      if isinstance(child, dict):
        last_used = time_now - child[self.__NODE_KEY_LAST_USED]
        if last_used > self.cache_timeout:
          del node[key]
        else:
          self.__cache_do_gc(child, time_now)

  def __split_segments(self, key): # {{{3
    return filter(None, key.split('/'))

  def __newctime(self): # {{{3
    return time.time()

  def __getctx(self): # {{{3
    c = fuse.FuseGetContext()
    return (c['uid'], c['gid'])

  def __hash(self, data): # {{{3
    start_time = time.time()
    context = self.hash_function_impl()
    context.update(data)
    digest = context.digest()
    self.time_spent_hashing += time.time() - start_time
    return digest

  def __print_stats(self): # {{{3
    self.logger.info('-' * 79)
    self.__report_memory_usage()
    self.__report_throughput()
    self.__report_timings()

  def __report_timings(self): # {{{3
    if self.logger.isEnabledFor(logging.DEBUG):
      timings = [(self.time_spent_traversing_tree, 'Traversing the tree'),
                 (self.time_spent_caching_nodes, 'Caching tree nodes'),
                 (self.time_spent_interning, 'Interning path components'),
                 (self.time_spent_writing_blocks, 'Writing data blocks'),
                 (self.time_spent_hashing, 'Hashing data blocks'),
                 (self.time_spent_querying_tree, 'Querying the tree')]
      maxdescwidth = max([len(l) for t, l in timings]) + 3
      timings.sort(reverse=True)
      uptime = time.time() - self.fs_mounted_at
      printed_heading = False
      for timespan, description in timings:
        percentage = timespan / (uptime / 100)
        if percentage >= 1:
          if not printed_heading:
            self.logger.debug("Cumulative timings of slowest operations:")
            printed_heading = True
          self.logger.debug(" - %-*s%s (%i%%)" % (maxdescwidth, description + ':', format_timespan(timespan), percentage))

  def report_disk_usage(self): # {{{3
    disk_usage = self.__fetchval('PRAGMA page_size') * self.__fetchval('PRAGMA page_count')
    disk_usage += os.stat(self.datastore_file).st_size
    apparent_size = self.__fetchval('SELECT SUM(inodes.size) FROM tree, inodes WHERE tree.inode = inodes.inode')
    self.logger.info("The total apparent size is %s while the databases take up %s (that's %.2f%%).",
        format_size(apparent_size), format_size(disk_usage), float(disk_usage) / (apparent_size / 100))

  def __report_memory_usage(self): # {{{3
    memory_usage = get_memory_usage()
    msg = "Current memory usage is " + format_size(memory_usage)
    difference = abs(memory_usage - self.memory_usage)
    if self.memory_usage != 0 and difference:
      direction = self.memory_usage < memory_usage and 'up' or 'down'
      msg += " (%s by %s)" % (direction, format_size(difference))
    self.logger.info(msg + '.')
    self.memory_usage = memory_usage

  def __report_throughput(self, nbytes=None, nseconds=None, label=None): # {{{3
    if nbytes == None:
      self.bytes_read, self.time_spent_reading = \
          self.__report_throughput(self.bytes_read, self.time_spent_reading, "read")
      self.bytes_written, self.time_spent_writing = \
          self.__report_throughput(self.bytes_written, self.time_spent_writing, "write")
    else:
      if nbytes > 0:
        average = format_size(nbytes / max(1, nseconds))
        self.logger.info("Average %s speed is %s/s.", label, average)
        # Decrease the influence of previous measurements over time?
        if nseconds > 60 and nbytes > 1024**2:
          return nbytes / 2, nseconds / 2
      return nbytes, nseconds

  def __report_top_blocks(self): # {{{3
    query = """
      SELECT * FROM (
        SELECT *, COUNT(*) AS "count" FROM "index"
        GROUP BY hash_id ORDER BY "count" DESC
      ), hashes WHERE
        "count" > 1 AND
        hash_id = hashes.id
        LIMIT 10 """
    if self.logger.isEnabledFor(logging.DEBUG):
      printed_header = False
      for row in self.conn.execute(query):
        if not printed_header:
          self.logger.debug("A listing of the most used blocks follows:")
          printed_header = True
        msg = "Block #%s of %s has been used %i times: %r"
        preview = row['value']
        max_length = 60
        if len(preview) < max_length:
          preview = str(preview)
        else:
          preview = preview[0 : max_length] + '...'
        nbytes = format_size(len(row['value']))
        self.logger.debug(msg, row['hash_id'], nbytes, row['count'], preview)

  def __gc_hook(self, nested=False): # {{{3
    # Don't collect any garbage for nested calls.
    if not nested:
      # Don't call time.time() more than once every 500th FUSE call.
      self.opcount += 1
      if self.opcount % 500 == 0:
        # Every minute the other statistics are reported and garbage
        # collection is performed when it isn't disabled.
        if time.time() - self.gc_hook_last_run >= self.gc_interval:
          self.__collect_garbage()
          self.__print_stats()
          self.gc_hook_last_run = time.time()

  def __collect_garbage(self): # {{{3
    if self.gc_enabled and not self.read_only:
      start_time = time.time()
      self.logger.info("Performing garbage collection (this might take a while) ..")
      self.should_vacuum = False
      for method in self.__collect_strings, self.__collect_inodes, \
          self.__collect_indices, self.__collect_blocks, self.__vacuum_metastore:
        sub_start_time = time.time()
        msg = method()
        if msg:
          elapsed_time = time.time() - sub_start_time
          self.logger.info(msg, format_timespan(elapsed_time))
      elapsed_time = time.time() - start_time
      self.logger.info("Finished garbage collection in %s.", format_timespan(elapsed_time))

  def __collect_strings(self): # {{{4
    count = self.conn.execute('DELETE FROM strings WHERE id NOT IN (SELECT name FROM tree)').rowcount
    if count > 0:
      self.should_vacuum = True
      return "Cleaned up %i unused path segment%s in %%s." % (count, count != 1 and 's' or '')

  def __collect_inodes(self): # {{{4
    count = self.conn.execute('DELETE FROM inodes WHERE nlinks = 0').rowcount
    if count > 0:
      self.should_vacuum = True
      return "Cleaned up %i unused inode%s in %%s." % (count, count != 1 and 's' or '')

  def __collect_indices(self): # {{{4
    count = self.conn.execute('DELETE FROM "index" WHERE inode NOT IN (SELECT inode FROM inodes)').rowcount
    if count > 0:
      self.should_vacuum = True
      return "Cleaned up %i unused index entr%s in %%s." % (count, count != 1 and 'ies' or 'y')

  def __collect_blocks(self): # {{{4
    should_reorganize = False
    for row in self.conn.execute('SELECT hash FROM hashes WHERE id NOT IN (SELECT hash_id FROM "index")'):
      del self.blocks[str(row[0])]
      should_reorganize = True
    if should_reorganize:
      self.__dbmcall('reorganize')
    count = self.conn.execute('DELETE FROM hashes WHERE id NOT IN (SELECT hash_id FROM "index")').rowcount
    if count > 0:
      self.should_vacuum = True
      return "Cleaned up %i unused data block%s in %%s." % (count, count != 1 and 's' or '')

  def __vacuum_metastore(self): # {{{4
    if self.should_vacuum:
      self.conn.execute('VACUUM')
      return "Vacuumed SQLite metadata store in %s."

  def __commit_changes(self, nested=False): # {{{3
    if self.use_transactions and not nested:
      self.conn.commit()

  def __rollback_changes(self, nested=False): # {{{3
    if self.use_transactions and not nested:
      self.logger.info('Rolling back changes')
      self.conn.rollback()

  def __get_file_buffer(self, path): # {{{3
    if path in self.buffers:
      return self.buffers[path]
    else:
      buf = Buffer()
      inode = self.__path2keys(path)[1]
      query = """ SELECT h.hash FROM hashes h, "index" i
                  WHERE i.inode = ? AND h.id = i.hash_id
                  ORDER BY i.block_nr ASC """
      for row in self.conn.execute(query, (inode,)).fetchall():
        # TODO Make the file system more robust against failure by doing
        # something sensible when self.blocks.has_key(digest) is false.
        buf.write(self.decompress(self.blocks[str(row[0])]))
      self.buffers[path] = buf
      return buf

  def __fetchval(self, query, *values): # {{{3
    return self.conn.execute(query, values).fetchone()[0]

  def __except_to_status(self, method, exception, code=errno.ENOENT): # {{{3
    # Don't report ENOENT raised from getattr().
    if method != 'getattr' or code != errno.ENOENT:
      sys.stderr.write('%s\n' % ('-' * 50))
      sys.stderr.write("Caught exception in %s(): %s\n" % (method, exception))
      traceback.print_exc(file=sys.stderr)
      sys.stderr.write('%s\n' % ('-' * 50))
      sys.stderr.write("Returning %i\n" % -code)
      sys.stderr.flush()
    # Convert the exception to a FUSE error code.
    if isinstance(exception, OSError):
      return -exception.errno
    else:
      return -code

class Buffer: # {{{1

  """
  This class wraps cStringIO.StringIO with two additions: The __len__
  method and a dirty flag to determine whether a buffer has changed.
  """

  def __init__(self):
    self.buf = cStringIO.StringIO()
    self.dirty = False

  def __getattr__(self, attr, default=None):
    """ Delegate to the StringIO object. """
    return getattr(self.buf, attr, default)

  def __len__(self):
    """ Get the total size of the buffer in bytes. """
    position = self.buf.tell()
    self.buf.seek(0, os.SEEK_END)
    length = self.buf.tell()
    self.buf.seek(position, os.SEEK_SET)
    return length

  def truncate(self, *args):
    """ Truncate the file at the current position and set the dirty flag. """
    if len(self) > self.buf.tell():
      self.dirty = True
    return self.buf.truncate(*args)

  def write(self, *args):
    """ Write a string to the file and set the dirty flag. """
    self.dirty = True
    return self.buf.write(*args)

# Named tuples used to return complex objects to FUSE. {{{1

try:
  import collections
  Stat = collections.namedtuple('Stat', 'st_atime st_blksize st_blocks \
      st_ctime st_dev st_gid st_ino st_mode st_mtime st_nlink st_rdev \
      st_size st_uid')
  StatVFS = collections.namedtuple('StatVFS', 'f_bavail f_bfree f_blocks \
      f_bsize f_favail f_ffree f_files f_flag f_frsize f_namemax')
except ImportError:
  # Fall back to regular Python classes instead of named tuples.
  class __Struct:
    def __init__(self, **kw):
      for k, v in kw.iteritems():
        setattr(self, k, v)
  class Stat(__Struct): pass
  class StatVFS(__Struct): pass

# }}}1

if __name__ == '__main__':

  if '--profile' in sys.argv:
    sys.stderr.write("Enabling profiling..\n")
    import cProfile, pstats
    profile = '.dedupfs.cprofile-%i' % time.time()
    cProfile.run('main()', profile)
    sys.stderr.write("\n Profiling statistics:\n\n")
    s = pstats.Stats(profile)
    s.sort_stats('time')
    s.print_stats(0.1)
    os.unlink(profile)
  else:
    main()

# vim: ts=2 sw=2 et

########NEW FILE########
__FILENAME__ = fuse
#
#    Copyright (C) 2001  Jeff Epler  <jepler@unpythonic.dhs.org>
#    Copyright (C) 2006  Csaba Henk  <csaba.henk@creo.hu>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#


# suppress version mismatch warnings
try:
    import warnings
    warnings.filterwarnings('ignore',
                            'Python C API version mismatch',
                            RuntimeWarning,
                            )
except:
    pass

from string import join
import sys
from errno import *
from os import environ
import re
from fuseparts import __version__
from fuseparts._fuse import main, FuseGetContext, FuseInvalidate
from fuseparts._fuse import FuseError, FuseAPIVersion
from fuseparts.subbedopts import SubOptsHive, SubbedOptFormatter
from fuseparts.subbedopts import SubbedOptIndentedFormatter, SubbedOptParse
from fuseparts.subbedopts import SUPPRESS_HELP, OptParseError
from fuseparts.setcompatwrap import set


##########
###
###  API specification API.
###
##########

# The actual API version of this module
FUSE_PYTHON_API_VERSION = (0, 2)

def __getenv__(var, pattern = '.', trans = lambda x: x):
    """
    Fetch enviroment variable and optionally transform it. Return `None` if
    variable is unset. Bail out if value of variable doesn't match (optional)
    regex pattern.
    """

    if var not in environ:
        return None
    val = environ[var]
    rpat = pattern
    if not isinstance(rpat, type(re.compile(''))):
        rpat = re.compile(rpat)
    if not rpat.search(val):
        raise RuntimeError("env var %s doesn't match required pattern %s" % \
                           (var, `pattern`))
    return trans(val)

def get_fuse_python_api():
    if fuse_python_api:
        return fuse_python_api
    elif compat_0_1:
        # deprecated way of API specification
        return (0,1)

def get_compat_0_1():
    return get_fuse_python_api() == (0, 1)

# API version to be used
fuse_python_api = __getenv__('FUSE_PYTHON_API', '^[\d.]+$',
                              lambda x: tuple([int(i) for i in x.split('.')]))

# deprecated way of API specification
compat_0_1 = __getenv__('FUSE_PYTHON_COMPAT', '^(0.1|ALL)$', lambda x: True)

fuse_python_api = get_fuse_python_api()

##########
###
###  Parsing for FUSE.
###
##########



class FuseArgs(SubOptsHive):
    """
    Class representing a FUSE command line.
    """

    fuse_modifiers = {'showhelp': '-ho',
                      'showversion': '-V',
                      'foreground': '-f'}

    def __init__(self):

        SubOptsHive.__init__(self)

        self.modifiers = {}
        self.mountpoint = None

        for m in self.fuse_modifiers:
            self.modifiers[m] = False

    def __str__(self):
        return '\n'.join(['< on ' + str(self.mountpoint) + ':',
                          '  ' + str(self.modifiers), '  -o ']) + \
               ',\n     '.join(self._str_core()) + \
               ' >'

    def getmod(self, mod):
        return self.modifiers[mod]

    def setmod(self, mod):
        self.modifiers[mod] = True

    def unsetmod(self, mod):
        self.modifiers[mod] = False

    def mount_expected(self):
        if self.getmod('showhelp'):
            return False
        if self.getmod('showversion'):
            return False
        return True

    def assemble(self):
        """Mangle self into an argument array"""

        self.canonify()
        args = [sys.argv and sys.argv[0] or "python"]
        if self.mountpoint:
            args.append(self.mountpoint)
        for m, v in self.modifiers.iteritems():
            if v:
                args.append(self.fuse_modifiers[m])

        opta = []
        for o, v in self.optdict.iteritems():
                opta.append(o + '=' + v)
        opta.extend(self.optlist)

        if opta:
            args.append("-o" + ",".join(opta))

        return args

    def filter(self, other=None):
        """
        Same as for SubOptsHive, with the following difference:
        if other is not specified, `Fuse.fuseoptref()` is run and its result
        will be used.
        """

        if not other:
            other = Fuse.fuseoptref()

        return SubOptsHive.filter(self, other)



class FuseFormatter(SubbedOptIndentedFormatter):

    def __init__(self, **kw):
        if not 'indent_increment' in kw:
            kw['indent_increment'] = 4
        SubbedOptIndentedFormatter.__init__(self, **kw)

    def store_option_strings(self, parser):
        SubbedOptIndentedFormatter.store_option_strings(self, parser)
        # 27 is how the lib stock help appears
        self.help_position = max(self.help_position, 27)
        self.help_width = self.width - self.help_position


class FuseOptParse(SubbedOptParse):
    """
    This class alters / enhances `SubbedOptParse` so that it's
    suitable for usage with FUSE.

    - When adding options, you can use the `mountopt` pseudo-attribute which
      is equivalent with adding a subopt for option ``-o``
      (it doesn't require an option argument).

    - FUSE compatible help and version printing.

    - Error and exit callbacks are relaxed. In case of FUSE, the command
      line is to be treated as a DSL [#]_. You don't wanna this module to
      force an exit on you just because you hit a DSL syntax error.

    - Built-in support for conventional FUSE options (``-d``, ``-f`, ``-s``).
      The way of this can be tuned by keyword arguments, see below.

    .. [#] http://en.wikipedia.org/wiki/Domain-specific_programming_language

    Keyword arguments for initialization
    ------------------------------------

    standard_mods
      Boolean [default is `True`].
      Enables support for the usual interpretation of the ``-d``, ``-f``
      options.

    fetch_mp
      Boolean [default is `True`].
      If it's True, then the last (non-option) argument
      (if there is such a thing) will be used as the FUSE mountpoint.

    dash_s_do
      String: ``whine``, ``undef``, or ``setsingle`` [default is ``whine``].
      The ``-s`` option -- traditionally for asking for single-threadedness --
      is an oddball: single/multi threadedness of a fuse-py fs doesn't depend
      on the FUSE command line, we have direct control over it.

      Therefore we have two conflicting principles:

      - *Orthogonality*: option parsing shouldn't affect the backing `Fuse`
        instance directly, only via its `fuse_args` attribute.

      - *POLS*: behave like other FUSE based fs-es do. The stock FUSE help
        makes mention of ``-s`` as a single-threadedness setter.

      So, if we follow POLS and implement a conventional ``-s`` option, then
      we have to go beyond the `fuse_args` attribute and set the respective
      Fuse attribute directly, hence violating orthogonality.

      We let the fs authors make their choice: ``dash_s_do=undef`` leaves this
      option unhandled, and the fs author can add a handler as she desires.
      ``dash_s_do=setsingle`` enables the traditional behaviour.

      Using ``dash_s_do=setsingle`` is not problematic at all, but we want fs
      authors be aware of the particularity of ``-s``, therefore the default is
      the ``dash_s_do=whine`` setting which raises an exception for ``-s`` and
      suggests the user to read this documentation.

    dash_o_handler
      Argument should be a SubbedOpt instance (created with
      ``action="store_hive"`` if you want it to be useful).
      This lets you customize the handler of the ``-o`` option. For example,
      you can alter or suppress the generic ``-o`` entry in help output.
    """

    def __init__(self, *args, **kw):

        self.mountopts = []

        self.fuse_args = \
            'fuse_args' in kw and kw.pop('fuse_args') or FuseArgs()
        dsd = 'dash_s_do' in kw and kw.pop('dash_s_do') or 'whine'
        if 'fetch_mp' in kw:
            self.fetch_mp = bool(kw.pop('fetch_mp'))
        else:
            self.fetch_mp = True
        if 'standard_mods' in kw:
            smods = bool(kw.pop('standard_mods'))
        else:
            smods = True
        if 'fuse' in kw:
            self.fuse = kw.pop('fuse')
        if not 'formatter' in kw:
            kw['formatter'] = FuseFormatter()
        doh = 'dash_o_handler' in kw and kw.pop('dash_o_handler')

        SubbedOptParse.__init__(self, *args, **kw)

        if doh:
            self.add_option(doh)
        else:
            self.add_option('-o', action='store_hive',
                            subopts_hive=self.fuse_args, help="mount options",
                            metavar="opt,[opt...]")

        if smods:
            self.add_option('-f', action='callback',
                            callback=lambda *a: self.fuse_args.setmod('foreground'),
                            help=SUPPRESS_HELP)
            self.add_option('-d', action='callback',
                            callback=lambda *a: self.fuse_args.add('debug'),
                            help=SUPPRESS_HELP)

        if dsd == 'whine':
            def dsdcb(option, opt_str, value, parser):
                raise RuntimeError, """

! If you want the "-s" option to work, pass
!
!   dash_s_do='setsingle'
!
! to the Fuse constructor. See docstring of the FuseOptParse class for an
! explanation why is it not set by default.
"""

        elif dsd == 'setsingle':
            def dsdcb(option, opt_str, value, parser):
                self.fuse.multithreaded = False

        elif dsd == 'undef':
            dsdcb = None
        else:
            raise ArgumentError, "key `dash_s_do': uninterpreted value " + str(dsd)

        if dsdcb:
            self.add_option('-s', action='callback', callback=dsdcb,
                            help=SUPPRESS_HELP)


    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)

    def error(self, msg):
        SubbedOptParse.error(self, msg)
        raise OptParseError, msg

    def print_help(self, file=sys.stderr):
        SubbedOptParse.print_help(self, file)
        print >> file
        self.fuse_args.setmod('showhelp')

    def print_version(self, file=sys.stderr):
        SubbedOptParse.print_version(self, file)
        self.fuse_args.setmod('showversion')

    def parse_args(self, args=None, values=None):
        o, a = SubbedOptParse.parse_args(self, args, values)
        if a and self.fetch_mp:
            self.fuse_args.mountpoint = a.pop()
        return o, a

    def add_option(self, *opts, **attrs):
        if 'mountopt' in attrs:
            if opts or 'subopt' in attrs:
                raise OptParseError(
                  "having options or specifying the `subopt' attribute conflicts with `mountopt' attribute")
            opts = ('-o',)
            attrs['subopt'] = attrs.pop('mountopt')
            if not 'dest' in attrs:
                attrs['dest'] = attrs['subopt']

        SubbedOptParse.add_option(self, *opts, **attrs)



##########
###
###  The FUSE interface.
###
##########



class ErrnoWrapper(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kw):
        try:
            return apply(self.func, args, kw)
        except (IOError, OSError), detail:
            # Sometimes this is an int, sometimes an instance...
            if hasattr(detail, "errno"): detail = detail.errno
            return -detail


########### Custom objects for transmitting system structures to FUSE

class FuseStruct(object):

    def __init__(self, **kw):
        for k in kw:
             setattr(self, k, kw[k])


class Stat(FuseStruct):
    """
    Auxiliary class which can be filled up stat attributes.
    The attributes are undefined by default.
    """

    def __init__(self, **kw):
        self.st_mode  = None
        self.st_ino   = 0
        self.st_dev   = 0
        self.st_nlink = None
        self.st_uid   = 0
        self.st_gid   = 0
        self.st_size  = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

        FuseStruct.__init__(self, **kw)


class StatVfs(FuseStruct):
    """
    Auxiliary class which can be filled up statvfs attributes.
    The attributes are 0 by default.
    """

    def __init__(self, **kw):

        self.f_bsize   = 0
        self.f_frsize  = 0
        self.f_blocks  = 0
        self.f_bfree   = 0
        self.f_bavail  = 0
        self.f_files   = 0
        self.f_ffree   = 0
        self.f_favail  = 0
        self.f_flag    = 0
        self.f_namemax = 0

        FuseStruct.__init__(self, **kw)


class Direntry(FuseStruct):
    """
    Auxiliary class for carrying directory entry data.
    Initialized with `name`. Further attributes (each
    set to 0 as default):

    offset
        An integer (or long) parameter, used as a bookmark
        during directory traversal.
        This needs to be set it you want stateful directory
        reading.

    type
       Directory entry type, should be one of the stat type
       specifiers (stat.S_IFLNK, stat.S_IFBLK, stat.S_IFDIR,
       stat.S_IFCHR, stat.S_IFREG, stat.S_IFIFO, stat.S_IFSOCK).

    ino
       Directory entry inode number.

    Note that Python's standard directory reading interface is
    stateless and provides only names, so the above optional
    attributes doesn't make sense in that context.
    """

    def __init__(self, name, **kw):

        self.name   = name
        self.offset = 0
        self.type   = 0
        self.ino    = 0

        FuseStruct.__init__(self, **kw)


class Flock(FuseStruct):
    """
    Class for representing flock structures (cf. fcntl(3)).
    
    It makes sense to give values to the `l_type`, `l_start`,
    `l_len`, `l_pid` attributes (`l_whence` is not used by
    FUSE, see ``fuse.h``).
    """

    def __init__(self, name, **kw):
    
        self.l_type  = None
        self.l_start = None
        self.l_len   = None
        self.l_pid   = None
 
        FuseStruct.__init__(self, **kw)

 
class Timespec(FuseStruct):
    """
    Cf. struct timespec in time.h:
    http://www.opengroup.org/onlinepubs/009695399/basedefs/time.h.html
    """

    def __init__(self, **kw):
    
        self.tv_sec  = None
        self.tv_nsec = None
 
        FuseStruct.__init__(self, **kw)


class FuseFileInfo(FuseStruct):

    def __init__(self, **kw):

        self.keep      = False
        self.direct_io = False

        FuseStruct.__init__(self, **kw)



########## Interface for requiring certain features from your underlying FUSE library.

def feature_needs(*feas):
    """
    Get info about the FUSE API version needed for the support of some features.

    This function takes a variable number of feature patterns.

    A feature pattern is either:

    -  an integer (directly referring to a FUSE API version number)
    -  a built-in feature specifier string (meaning defined by dictionary)
    -  a string of the form ``has_foo``, where ``foo`` is a filesystem method
       (refers to the API version where the method has been introduced)
    -  a list/tuple of other feature patterns (matches each of its members)
    -  a regexp (meant to be matched against the builtins plus ``has_foo``
       patterns; can also be given by a string of the from "re:*")
    -  a negated regexp (can be given by a string of the form "!re:*")

    If called with no arguments, then the list of builtins is returned, mapped
    to their meaning.

    Otherwise the function returns the smallest FUSE API version number which
    has all the matching features.

    Builtin specifiers worth to explicit mention:
    - ``stateful_files``: you want to use custom filehandles (eg. a file class).
    - ``*``: you want all features.
    - while ``has_foo`` makes sense for all filesystem method ``foo``, some
      of these can be found among the builtins, too (the ones which can be
      handled by the general rule).

    specifiers like ``has_foo`` refer to requirement that the library knows of
      the fs method ``foo``.
    """

    fmap = {'stateful_files': 22,
            'stateful_dirs':  23,
            'stateful_io':    ('stateful_files', 'stateful_dirs'),
            'stateful_files_keep_cache': 23,
            'stateful_files_direct_io': 23,
            'keep_cache':     ('stateful_files_keep_cache',),
            'direct_io':      ('stateful_files_direct_io',),
            'has_opendir':    ('stateful_dirs',),
            'has_releasedir': ('stateful_dirs',),
            'has_fsyncdir':   ('stateful_dirs',),
            'has_create':     25,
            'has_access':     25,
            'has_fgetattr':   25,
            'has_ftruncate':  25,
            'has_fsinit':     ('has_init'),
            'has_fsdestroy':  ('has_destroy'),
            'has_lock':       26,
            'has_utimens':    26,
            'has_bmap':       26,
            'has_init':       23,
            'has_destroy':    23,
            '*':              '!re:^\*$'}

    if not feas:
        return fmap

    def resolve(args, maxva):

        for fp in args:
            if isinstance(fp, int):
                maxva[0] = max(maxva[0], fp)
                continue
            if isinstance(fp, list) or isinstance(fp, tuple):
                for f in fp:
                    yield f
                continue
            ma = isinstance(fp, str) and re.compile("(!\s*|)re:(.*)").match(fp)
            if isinstance(fp, type(re.compile(''))) or ma:
                neg = False
                if ma:
                    mag = ma.groups()
                    fp = re.compile(mag[1])
                    neg = bool(mag[0])
                for f in fmap.keys() + [ 'has_' + a for a in Fuse._attrs ]:
                    if neg != bool(re.search(fp, f)):
                        yield f
                continue
            ma = re.compile("has_(.*)").match(fp)
            if ma and ma.groups()[0] in Fuse._attrs and not fp in fmap:
                yield 21
                continue
            yield fmap[fp]

    maxva = [0]
    while feas:
        feas = set(resolve(feas, maxva))

    return maxva[0]


def APIVersion():
    """Get the API version of your underlying FUSE lib"""

    return FuseAPIVersion()


def feature_assert(*feas):
    """
    Takes some feature patterns (like in `feature_needs`).
    Raises a fuse.FuseError if your underlying FUSE lib fails
    to have some of the matching features.

    (Note: use a ``has_foo`` type feature assertion only if lib support
    for method ``foo`` is *necessary* for your fs. Don't use this assertion
    just because your fs implements ``foo``. The usefulness of ``has_foo``
    is limited by the fact that we can't guarantee that your FUSE kernel
    module also supports ``foo``.)
    """

    fav = APIVersion()

    for fea in feas:
        fn = feature_needs(fea)
        if fav < fn:
            raise FuseError(
              "FUSE API version %d is required for feature `%s' but only %d is available" % \
              (fn, str(fea), fav))


############# Subclass this.

class Fuse(object):
    """
    Python interface to FUSE.

    Basic usage:

    - instantiate

    - add options to `parser` attribute (an instance of `FuseOptParse`)

    - call `parse`

    - call `main`
    """

    _attrs = ['getattr', 'readlink', 'readdir', 'mknod', 'mkdir',
              'unlink', 'rmdir', 'symlink', 'rename', 'link', 'chmod',
              'chown', 'truncate', 'utime', 'open', 'read', 'write', 'release',
              'statfs', 'fsync', 'create', 'opendir', 'releasedir', 'fsyncdir',
              'flush', 'fgetattr', 'ftruncate', 'getxattr', 'listxattr',
              'setxattr', 'removexattr', 'access', 'lock', 'utimens', 'bmap',
              'fsinit', 'fsdestroy']

    fusage = "%prog [mountpoint] [options]"

    def __init__(self, *args, **kw):
        """
        Not much happens here apart from initializing the `parser` attribute.
        Arguments are forwarded to the constructor of the parser class almost
        unchanged.

        The parser class is `FuseOptParse` unless you specify one using the
        ``parser_class`` keyword. (See `FuseOptParse` documentation for
        available options.)
        """

        if not fuse_python_api:
            raise RuntimeError, __name__ + """.fuse_python_api not defined.

! Please define """ + __name__ + """.fuse_python_api internally (eg.
! 
! (1)  """ + __name__ + """.fuse_python_api = """ + `FUSE_PYTHON_API_VERSION` + """
! 
! ) or in the enviroment (eg. 
! 
! (2)  FUSE_PYTHON_API=0.1
! 
! ).
!
! If you are actually developing a filesystem, probably (1) is the way to go.
! If you are using a filesystem written before 2007 Q2, probably (2) is what
! you want."
"""

        def malformed():
            raise RuntimeError, \
                  "malformatted fuse_python_api value " + `fuse_python_api`
        if not isinstance(fuse_python_api, tuple):
            malformed()
        for i in fuse_python_api:
            if not isinstance(i, int) or i < 0:
                malformed() 

        if fuse_python_api > FUSE_PYTHON_API_VERSION:
            raise RuntimeError, """
! You require FUSE-Python API version """ + `fuse_python_api` + """.
! However, the latest available is """ + `FUSE_PYTHON_API_VERSION` + """.
"""

        self.fuse_args = \
            'fuse_args' in kw and kw.pop('fuse_args') or FuseArgs()

        if get_compat_0_1():
            return self.__init_0_1__(*args, **kw)

        self.multithreaded = True

        if not 'usage' in kw:
            kw['usage'] = self.fusage
        if not 'fuse_args' in kw:
            kw['fuse_args'] = self.fuse_args
        kw['fuse'] = self
        parserclass = \
          'parser_class' in kw and kw.pop('parser_class') or FuseOptParse

        self.parser = parserclass(*args, **kw)
        self.methproxy = self.Methproxy()

    def parse(self, *args, **kw):
        """Parse command line, fill `fuse_args` attribute."""

        ev = 'errex' in kw and kw.pop('errex')
        if ev and not isinstance(ev, int):
            raise TypeError, "error exit value should be an integer"

        try:
            self.cmdline = self.parser.parse_args(*args, **kw)
        except OptParseError:
          if ev:
              sys.exit(ev)
          raise

        return self.fuse_args

    def main(self, args=None):
        """Enter filesystem service loop."""

        if get_compat_0_1():
            args = self.main_0_1_preamble()

        d = {'multithreaded': self.multithreaded and 1 or 0}
        d['fuse_args'] = args or self.fuse_args.assemble()

        for t in 'file_class', 'dir_class':
            if hasattr(self, t):
                getattr(self.methproxy, 'set_' + t)(getattr(self,t))

        for a in self._attrs:
            b = a
            if get_compat_0_1() and a in self.compatmap:
                b = self.compatmap[a]
            if hasattr(self, b):
                c = ''
                if get_compat_0_1() and hasattr(self, a + '_compat_0_1'):
                    c = '_compat_0_1'
                d[a] = ErrnoWrapper(self.lowwrap(a + c))

        try:
            main(**d)
        except FuseError:
            if args or self.fuse_args.mount_expected():
                raise

    def lowwrap(self, fname):
        """
        Wraps the fname method when the C code expects a different kind of
        callback than we have in the fusepy API. (The wrapper is usually for
        performing some checks or transfromations which could be done in C but
        is simpler if done in Python.)

        Currently `open` and `create` are wrapped: a boolean flag is added
        which indicates if the result is to be kept during the opened file's
        lifetime or can be thrown away. Namely, it's considered disposable
        if it's an instance of FuseFileInfo.
        """
        fun = getattr(self, fname)

        if fname in ('open', 'create'):
            def wrap(*a, **kw):
                res = fun(*a, **kw)
                if not res or type(res) == type(0):
                    return res
                else:
                    return (res, type(res) != FuseFileInfo)
        elif fname == 'utimens':
            def wrap(path, acc_sec, acc_nsec, mod_sec, mod_nsec):
                ts_acc = Timespec(tv_sec = acc_sec, tv_nsec = acc_nsec)
                ts_mod = Timespec(tv_sec = mod_sec, tv_nsec = mod_nsec)
                return fun(path, ts_acc, ts_mod)
        else:
            wrap = fun

        return wrap

    def GetContext(self):
        return FuseGetContext(self)

    def Invalidate(self, path):
        return FuseInvalidate(self, path)

    def fuseoptref(cls):
        """
        Find out which options are recognized by the library.
        Result is a `FuseArgs` instance with the list of supported
        options, suitable for passing on to the `filter` method of
        another `FuseArgs` instance.
        """

        import os, re

        pr, pw = os.pipe()
        pid = os.fork()
        if pid == 0:
             os.dup2(pw, 2)
             os.close(pr)

             fh = cls()
             fh.fuse_args = FuseArgs()
             fh.fuse_args.setmod('showhelp')
             fh.main()
             sys.exit()

        os.close(pw)

        fa = FuseArgs()
        ore = re.compile("-o\s+([\w\[\]]+(?:=\w+)?)")
        fpr = os.fdopen(pr)
        for l in fpr:
             m = ore.search(l)
             if m:
                 o = m.groups()[0]
                 oa = [o]
                 # try to catch two-in-one options (like "[no]foo")
                 opa = o.split("[")
                 if len(opa) == 2:
                    o1, ox = opa
                    oxpa = ox.split("]")
                    if len(oxpa) == 2:
                       oo, o2 = oxpa
                       oa = [o1 + o2, o1 + oo + o2]
                 for o in oa:
                     fa.add(o)

        fpr.close()
        return fa

    fuseoptref = classmethod(fuseoptref)


    class Methproxy(object):

        def __init__(self):

            class mpx(object):
               def __init__(self, name):
                   self.name = name
               def __call__(self, *a, **kw):
                   return getattr(a[-1], self.name)(*(a[1:-1]), **kw)

            self.proxyclass = mpx
            self.mdic = {}
            self.file_class = None
            self.dir_class = None

        def __call__(self, meth):
            return meth in self.mdic and self.mdic[meth] or None

        def _add_class_type(cls, type, inits, proxied):

            def setter(self, xcls):

                setattr(self, type + '_class', xcls)

                for m in inits:
                    self.mdic[m] = xcls

                for m in proxied:
                    if hasattr(xcls, m):
                        self.mdic[m] = self.proxyclass(m)

            setattr(cls, 'set_' + type + '_class', setter)

        _add_class_type = classmethod(_add_class_type)

    Methproxy._add_class_type('file', ('open', 'create'),
                              ('read', 'write', 'fsync', 'release', 'flush',
                               'fgetattr', 'ftruncate', 'lock'))
    Methproxy._add_class_type('dir', ('opendir',),
                              ('readdir', 'fsyncdir', 'releasedir'))


    def __getattr__(self, meth):

        m = self.methproxy(meth)
        if m:
            return m

        raise AttributeError, "Fuse instance has no attribute '%s'" % meth



##########
###
###  Compat stuff.
###
##########



    def __init_0_1__(self, *args, **kw):

        self.flags = 0
        multithreaded = 0

        # default attributes
        if args == ():
            # there is a self.optlist.append() later on, make sure it won't
            # bomb out.
            self.optlist = []
        else:
            self.optlist = args
        self.optdict = kw

        if len(self.optlist) == 1:
            self.mountpoint = self.optlist[0]
        else:
            self.mountpoint = None

        # grab command-line arguments, if any.
        # Those will override whatever parameters
        # were passed to __init__ directly.
        argv = sys.argv
        argc = len(argv)
        if argc > 1:
            # we've been given the mountpoint
            self.mountpoint = argv[1]
        if argc > 2:
            # we've received mount args
            optstr = argv[2]
            opts = optstr.split(",")
            for o in opts:
                try:
                    k, v = o.split("=", 1)
                    self.optdict[k] = v
                except:
                    self.optlist.append(o)


    def main_0_1_preamble(self):

        cfargs = FuseArgs()

        cfargs.mountpoint = self.mountpoint

        if hasattr(self, 'debug'):
            cfargs.add('debug')

        if hasattr(self, 'allow_other'):
            cfargs.add('allow_other')

        if hasattr(self, 'kernel_cache'):
            cfargs.add('kernel_cache')

        return cfargs.assemble()


    def getattr_compat_0_1(self, *a):
        from os import stat_result

        return stat_result(self.getattr(*a))


    def statfs_compat_0_1(self, *a):

        oout = self.statfs(*a)
        lo = len(oout)

        svf = StatVfs()
        svf.f_bsize   = oout[0]                   # 0
        svf.f_frsize  = oout[lo >= 8 and 7 or 0]  # 1
        svf.f_blocks  = oout[1]                   # 2
        svf.f_bfree   = oout[2]                   # 3
        svf.f_bavail  = oout[3]                   # 4
        svf.f_files   = oout[4]                   # 5
        svf.f_ffree   = oout[5]                   # 6
        svf.f_favail  = lo >= 9 and oout[8] or 0  # 7
        svf.f_flag    = lo >= 10 and oout[9] or 0 # 8
        svf.f_namemax = oout[6]                   # 9

        return svf


    def readdir_compat_0_1(self, path, offset, *fh):

        for name, type in self.getdir(path):
            de = Direntry(name)
            de.type = type

            yield de


    compatmap = {'readdir': 'getdir'}

########NEW FILE########
__FILENAME__ = get_memory_usage
#!/usr/bin/python

"""
The function in this Python module determines the current memory usage of the
current process by reading the VmSize value from /proc/$pid/status. It's based
on the following entry in the Python cookbook:
http://code.activestate.com/recipes/286222/
"""

import os

_units = { 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3 }
_handle = _handle = open('/proc/%d/status' % os.getpid())

def get_memory_usage():
  global _proc_status, _units, _handle
  try:
    for line in _handle:
      if line.startswith('VmSize:'):
        label, count, unit = line.split()
        return int(count) * _units[unit.upper()]
  except:
    return 0
  finally:
    _handle.seek(0)

if __name__ == '__main__':
  from my_formats import format_size
  megabyte = 1024**2
  counter = megabyte
  limit = megabyte * 50
  memory = []
  old_memory_usage = get_memory_usage()
  assert old_memory_usage > 0
  while counter < limit:
    memory.append('a' * counter)
    msg = "I've just allocated %s and get_memory_usage() returns %s (%s more, deviation is %s)"
    new_memory_usage = get_memory_usage()
    difference = new_memory_usage - old_memory_usage
    deviation = max(difference, counter) - min(difference, counter)
    assert deviation < 1024*100
    print msg % (format_size(counter), format_size(new_memory_usage), format_size(difference), format_size(deviation))
    old_memory_usage = new_memory_usage
    counter += megabyte
  print "Stopped allocating new strings at %s" % format_size(limit)

# vim: ts=2 sw=2 et

########NEW FILE########
__FILENAME__ = my_formats
from math import floor

def format_timespan(seconds): # {{{1
  """
  Format a timespan in seconds as a human-readable string.
  """
  result = []
  units = [('day', 60 * 60 * 24), ('hour', 60 * 60), ('minute', 60), ('second', 1)]
  for name, size in units:
    if seconds >= size:
      count = seconds / size
      seconds %= size
      result.append('%i %s%s' % (count, name, floor(count) != 1 and 's' or ''))
  if result == []:
    return 'less than a second'
  if len(result) == 1:
    return result[0]
  else:
    return ', '.join(result[:-1]) + ' and ' + result[-1]

def format_size(nbytes):
  """
  Format a byte count as a human-readable file size.
  """
  return nbytes < 1024 and '%i bytes' % nbytes \
      or nbytes < (1024 ** 2) and __round(nbytes, 1024, 'KB') \
      or nbytes < (1024 ** 3) and __round(nbytes, 1024 ** 2, 'MB') \
      or nbytes < (1024 ** 4) and __round(nbytes, 1024 ** 3, 'GB') \
      or __round(nbytes, 1024 ** 4, 'TB')

def __round(nbytes, divisor, suffix):
  nbytes = float(nbytes) / divisor
  if floor(nbytes) == nbytes:
    return str(int(nbytes)) + ' ' + suffix
  else:
    return '%.2f %s' % (nbytes, suffix)

# vim: sw=2 sw=2 et

########NEW FILE########
