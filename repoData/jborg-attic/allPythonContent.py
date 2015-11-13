__FILENAME__ = archive
from datetime import datetime, timedelta, timezone
from getpass import getuser
from itertools import groupby
import errno
import shutil
import tempfile
from attic.key import key_factory
from attic.remote import cache_if_remote
import msgpack
import os
import socket
import stat
import sys
import time
from io import BytesIO
from attic import xattr
from attic.platform import acl_get, acl_set
from attic.chunker import chunkify
from attic.hashindex import ChunkIndex
from attic.helpers import Error, uid2user, user2uid, gid2group, group2gid, \
    Manifest, Statistics, decode_dict, st_mtime_ns, make_path_safe, StableDict, int_to_bigint, bigint_to_int

ITEMS_BUFFER = 1024 * 1024
CHUNK_MIN = 1024
WINDOW_SIZE = 0xfff
CHUNK_MASK = 0xffff

utime_supports_fd = os.utime in getattr(os, 'supports_fd', {})
has_mtime_ns = sys.version >= '3.3'
has_lchmod = hasattr(os, 'lchmod')
has_lchflags = hasattr(os, 'lchflags')


class DownloadPipeline:

    def __init__(self, repository, key):
        self.repository = repository
        self.key = key

    def unpack_many(self, ids, filter=None, preload=False):
        unpacker = msgpack.Unpacker(use_list=False)
        for data in self.fetch_many(ids):
            unpacker.feed(data)
            items = [decode_dict(item, (b'path', b'source', b'user', b'group')) for item in unpacker]
            if filter:
                items = [item for item in items if filter(item)]
            if preload:
                for item in items:
                    if b'chunks' in item:
                        self.repository.preload([c[0] for c in item[b'chunks']])
            for item in items:
                yield item

    def fetch_many(self, ids, is_preloaded=False):
        for id_, data in zip(ids, self.repository.get_many(ids, is_preloaded=is_preloaded)):
            yield self.key.decrypt(id_, data)


class ChunkBuffer:
    BUFFER_SIZE = 1 * 1024 * 1024

    def __init__(self, key):
        self.buffer = BytesIO()
        self.packer = msgpack.Packer(unicode_errors='surrogateescape')
        self.chunks = []
        self.key = key

    def add(self, item):
        self.buffer.write(self.packer.pack(StableDict(item)))
        if self.is_full():
            self.flush()

    def write_chunk(self, chunk):
        raise NotImplementedError

    def flush(self, flush=False):
        if self.buffer.tell() == 0:
            return
        self.buffer.seek(0)
        chunks = list(bytes(s) for s in chunkify(self.buffer, WINDOW_SIZE, CHUNK_MASK, CHUNK_MIN, self.key.chunk_seed))
        self.buffer.seek(0)
        self.buffer.truncate(0)
        # Leave the last parital chunk in the buffer unless flush is True
        end = None if flush or len(chunks) == 1 else -1
        for chunk in chunks[:end]:
            self.chunks.append(self.write_chunk(chunk))
        if end == -1:
            self.buffer.write(chunks[-1])

    def is_full(self):
        return self.buffer.tell() > self.BUFFER_SIZE


class CacheChunkBuffer(ChunkBuffer):

    def __init__(self, cache, key, stats):
        super(CacheChunkBuffer, self).__init__(key)
        self.cache = cache
        self.stats = stats

    def write_chunk(self, chunk):
        id_, _, _ = self.cache.add_chunk(self.key.id_hash(chunk), chunk, self.stats)
        return id_


class Archive:

    class DoesNotExist(Error):
        """Archive {} does not exist"""

    class AlreadyExists(Error):
        """Archive {} already exists"""

    def __init__(self, repository, key, manifest, name, cache=None, create=False,
                 checkpoint_interval=300, numeric_owner=False):
        self.cwd = os.getcwd()
        self.key = key
        self.repository = repository
        self.cache = cache
        self.manifest = manifest
        self.hard_links = {}
        self.stats = Statistics()
        self.name = name
        self.checkpoint_interval = checkpoint_interval
        self.numeric_owner = numeric_owner
        self.items_buffer = CacheChunkBuffer(self.cache, self.key, self.stats)
        self.pipeline = DownloadPipeline(self.repository, self.key)
        if create:
            if name in manifest.archives:
                raise self.AlreadyExists(name)
            self.last_checkpoint = time.time()
            i = 0
            while True:
                self.checkpoint_name = '%s.checkpoint%s' % (name, i and ('.%d' % i) or '')
                if not self.checkpoint_name in manifest.archives:
                    break
                i += 1
        else:
            if name not in self.manifest.archives:
                raise self.DoesNotExist(name)
            info = self.manifest.archives[name]
            self.load(info[b'id'])

    def load(self, id):
        self.id = id
        data = self.key.decrypt(self.id, self.repository.get(self.id))
        self.metadata = msgpack.unpackb(data)
        if self.metadata[b'version'] != 1:
            raise Exception('Unknown archive metadata version')
        decode_dict(self.metadata, (b'name', b'hostname', b'username', b'time'))
        self.metadata[b'cmdline'] = [arg.decode('utf-8', 'surrogateescape') for arg in self.metadata[b'cmdline']]
        self.name = self.metadata[b'name']

    @property
    def ts(self):
        """Timestamp of archive creation in UTC"""
        t, f = self.metadata[b'time'].split('.', 1)
        return datetime.strptime(t, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc) + timedelta(seconds=float('.' + f))

    def __repr__(self):
        return 'Archive(%r)' % self.name

    def iter_items(self, filter=None, preload=False):
        for item in self.pipeline.unpack_many(self.metadata[b'items'], filter=filter, preload=preload):
            yield item

    def add_item(self, item):
        self.items_buffer.add(item)
        if time.time() - self.last_checkpoint > self.checkpoint_interval:
            self.write_checkpoint()
            self.last_checkpoint = time.time()

    def write_checkpoint(self):
        self.save(self.checkpoint_name)
        del self.manifest.archives[self.checkpoint_name]
        self.cache.chunk_decref(self.id, self.stats)

    def save(self, name=None):
        name = name or self.name
        if name in self.manifest.archives:
            raise self.AlreadyExists(name)
        self.items_buffer.flush(flush=True)
        metadata = StableDict({
            'version': 1,
            'name': name,
            'items': self.items_buffer.chunks,
            'cmdline': sys.argv,
            'hostname': socket.gethostname(),
            'username': getuser(),
            'time': datetime.utcnow().isoformat(),
        })
        data = msgpack.packb(metadata, unicode_errors='surrogateescape')
        self.id = self.key.id_hash(data)
        self.cache.add_chunk(self.id, data, self.stats)
        self.manifest.archives[name] = {'id': self.id, 'time': metadata['time']}
        self.manifest.write()
        self.repository.commit()
        self.cache.commit()

    def calc_stats(self, cache):
        def add(id):
            count, size, csize = self.cache.chunks[id]
            stats.update(size, csize, count == 1)
            self.cache.chunks[id] = count - 1, size, csize
        def add_file_chunks(chunks):
            for id, _, _ in chunks:
                add(id)
        # This function is a bit evil since it abuses the cache to calculate
        # the stats. The cache transaction must be rolled back afterwards
        unpacker = msgpack.Unpacker(use_list=False)
        cache.begin_txn()
        stats = Statistics()
        add(self.id)
        for id, chunk in zip(self.metadata[b'items'], self.repository.get_many(self.metadata[b'items'])):
            add(id)
            unpacker.feed(self.key.decrypt(id, chunk))
            for item in unpacker:
                if b'chunks' in item:
                    stats.nfiles += 1
                    add_file_chunks(item[b'chunks'])
        cache.rollback()
        return stats

    def extract_item(self, item, restore_attrs=True, dry_run=False):
        if dry_run:
            if b'chunks' in item:
                for _ in self.pipeline.fetch_many([c[0] for c in item[b'chunks']], is_preloaded=True):
                    pass
            return

        dest = self.cwd
        if item[b'path'].startswith('/') or item[b'path'].startswith('..'):
            raise Exception('Path should be relative and local')
        path = os.path.join(dest, item[b'path'])
        # Attempt to remove existing files, ignore errors on failure
        try:
            st = os.lstat(path)
            if stat.S_ISDIR(st.st_mode):
                os.rmdir(path)
            else:
                os.unlink(path)
        except OSError:
            pass
        mode = item[b'mode']
        if stat.S_ISDIR(mode):
            if not os.path.exists(path):
                os.makedirs(path)
            if restore_attrs:
                self.restore_attrs(path, item)
        elif stat.S_ISREG(mode):
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            # Hard link?
            if b'source' in item:
                source = os.path.join(dest, item[b'source'])
                if os.path.exists(path):
                    os.unlink(path)
                os.link(source, path)
            else:
                with open(path, 'wb') as fd:
                    ids = [c[0] for c in item[b'chunks']]
                    for data in self.pipeline.fetch_many(ids, is_preloaded=True):
                        fd.write(data)
                    fd.flush()
                    self.restore_attrs(path, item, fd=fd.fileno())
        elif stat.S_ISFIFO(mode):
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            os.mkfifo(path)
            self.restore_attrs(path, item)
        elif stat.S_ISLNK(mode):
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            source = item[b'source']
            if os.path.exists(path):
                os.unlink(path)
            os.symlink(source, path)
            self.restore_attrs(path, item, symlink=True)
        elif stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
            os.mknod(path, item[b'mode'], item[b'rdev'])
            self.restore_attrs(path, item)
        else:
            raise Exception('Unknown archive item type %r' % item[b'mode'])

    def restore_attrs(self, path, item, symlink=False, fd=None):
        xattrs = item.get(b'xattrs')
        if xattrs:
                for k, v in xattrs.items():
                    try:
                        xattr.setxattr(fd or path, k, v, follow_symlinks=False)
                    except OSError as e:
                        if e.errno != errno.ENOTSUP:
                            raise
        uid = gid = None
        if not self.numeric_owner:
            uid = user2uid(item[b'user'])
            gid = group2gid(item[b'group'])
        uid = item[b'uid'] if uid is None else uid
        gid = item[b'gid'] if gid is None else gid
        # This code is a bit of a mess due to os specific differences
        try:
            if fd:
                os.fchown(fd, uid, gid)
            else:
                os.lchown(path, uid, gid)
        except OSError:
            pass
        if fd:
            os.fchmod(fd, item[b'mode'])
        elif not symlink:
            os.chmod(path, item[b'mode'])
        elif has_lchmod:  # Not available on Linux
            os.lchmod(path, item[b'mode'])
        mtime = bigint_to_int(item[b'mtime'])
        if fd and utime_supports_fd:  # Python >= 3.3
            os.utime(fd, None, ns=(mtime, mtime))
        elif utime_supports_fd:  # Python >= 3.3
            os.utime(path, None, ns=(mtime, mtime), follow_symlinks=False)
        elif not symlink:
            os.utime(path, (mtime / 1e9, mtime / 1e9))
        acl_set(path, item, self.numeric_owner)
        # Only available on OS X and FreeBSD
        if has_lchflags and b'bsdflags' in item:
            try:
                os.lchflags(path, item[b'bsdflags'])
            except OSError:
                pass

    def delete(self, stats):
        unpacker = msgpack.Unpacker(use_list=False)
        for items_id, data in zip(self.metadata[b'items'], self.repository.get_many(self.metadata[b'items'])):
            unpacker.feed(self.key.decrypt(items_id, data))
            self.cache.chunk_decref(items_id, stats)
            for item in unpacker:
                if b'chunks' in item:
                    for chunk_id, size, csize in item[b'chunks']:
                        self.cache.chunk_decref(chunk_id, stats)

        self.cache.chunk_decref(self.id, stats)
        del self.manifest.archives[self.name]

    def stat_attrs(self, st, path):
        item = {
            b'mode': st.st_mode,
            b'uid': st.st_uid, b'user': uid2user(st.st_uid),
            b'gid': st.st_gid, b'group': gid2group(st.st_gid),
            b'mtime': int_to_bigint(st_mtime_ns(st))
        }
        if self.numeric_owner:
            item[b'user'] = item[b'group'] = None
        xattrs = xattr.get_all(path, follow_symlinks=False)
        if xattrs:
            item[b'xattrs'] = StableDict(xattrs)
        if has_lchflags and st.st_flags:
            item[b'bsdflags'] = st.st_flags
        item[b'acl'] = acl_get(path, item, self.numeric_owner)
        return item

    def process_item(self, path, st):
        item = {b'path': make_path_safe(path)}
        item.update(self.stat_attrs(st, path))
        self.add_item(item)

    def process_dev(self, path, st):
        item = {b'path': make_path_safe(path), b'rdev': st.st_rdev}
        item.update(self.stat_attrs(st, path))
        self.add_item(item)

    def process_symlink(self, path, st):
        source = os.readlink(path)
        item = {b'path': make_path_safe(path), b'source': source}
        item.update(self.stat_attrs(st, path))
        self.add_item(item)

    def process_file(self, path, st, cache):
        safe_path = make_path_safe(path)
        # Is it a hard link?
        if st.st_nlink > 1:
            source = self.hard_links.get((st.st_ino, st.st_dev))
            if (st.st_ino, st.st_dev) in self.hard_links:
                item = self.stat_attrs(st, path)
                item.update({b'path': safe_path, b'source': source})
                self.add_item(item)
                return
            else:
                self.hard_links[st.st_ino, st.st_dev] = safe_path
        path_hash = self.key.id_hash(os.path.join(self.cwd, path).encode('utf-8', 'surrogateescape'))
        ids = cache.file_known_and_unchanged(path_hash, st)
        chunks = None
        if ids is not None:
            # Make sure all ids are available
            for id_ in ids:
                if not cache.seen_chunk(id_):
                    break
            else:
                chunks = [cache.chunk_incref(id_, self.stats) for id_ in ids]
        # Only chunkify the file if needed
        if chunks is None:
            with open(path, 'rb') as fd:
                chunks = []
                for chunk in chunkify(fd, WINDOW_SIZE, CHUNK_MASK, CHUNK_MIN, self.key.chunk_seed):
                    chunks.append(cache.add_chunk(self.key.id_hash(chunk), chunk, self.stats))
            cache.memorize_file(path_hash, st, [c[0] for c in chunks])
        item = {b'path': safe_path, b'chunks': chunks}
        item.update(self.stat_attrs(st, path))
        self.stats.nfiles += 1
        self.add_item(item)

    @staticmethod
    def list_archives(repository, key, manifest, cache=None):
        for name, info in manifest.archives.items():
            yield Archive(repository, key, manifest, name, cache=cache)


class RobustUnpacker():
    """A restartable/robust version of the streaming msgpack unpacker
    """
    item_keys = [msgpack.packb(name) for name in ('path', 'mode', 'source', 'chunks', 'rdev', 'xattrs', 'user', 'group', 'uid', 'gid', 'mtime')]

    def __init__(self, validator):
        super(RobustUnpacker, self).__init__()
        self.validator = validator
        self._buffered_data = []
        self._resync = False
        self._unpacker = msgpack.Unpacker(object_hook=StableDict)

    def resync(self):
        self._buffered_data = []
        self._resync = True

    def feed(self, data):
        if self._resync:
            self._buffered_data.append(data)
        else:
            self._unpacker.feed(data)

    def __iter__(self):
        return self

    def __next__(self):
        if self._resync:
            data = b''.join(self._buffered_data)
            while self._resync:
                if not data:
                    raise StopIteration
                # Abort early if the data does not look like a serialized dict
                if len(data) < 2 or ((data[0] & 0xf0) != 0x80) or ((data[1] & 0xe0) != 0xa0):
                    data = data[1:]
                    continue
                # Make sure it looks like an item dict
                for pattern in self.item_keys:
                    if data[1:].startswith(pattern):
                        break
                else:
                    data = data[1:]
                    continue

                self._unpacker = msgpack.Unpacker(object_hook=StableDict)
                self._unpacker.feed(data)
                try:
                    item = next(self._unpacker)
                    if self.validator(item):
                        self._resync = False
                        return item
                # Ignore exceptions that might be raised when feeding
                # msgpack with invalid data
                except (TypeError, ValueError, StopIteration):
                    pass
                data = data[1:]
        else:
            return next(self._unpacker)


class ArchiveChecker:

    def __init__(self):
        self.error_found = False
        self.possibly_superseded = set()
        self.tmpdir = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdir)

    def check(self, repository, repair=False):
        self.report_progress('Starting archive consistency check...')
        self.repair = repair
        self.repository = repository
        self.init_chunks()
        self.key = self.identify_key(repository)
        if not Manifest.MANIFEST_ID in self.chunks:
            self.manifest = self.rebuild_manifest()
        else:
            self.manifest, _ = Manifest.load(repository, key=self.key)
        self.rebuild_refcounts()
        self.verify_chunks()
        if not self.error_found:
            self.report_progress('Archive consistency check complete, no problems found.')
        return self.repair or not self.error_found

    def init_chunks(self):
        """Fetch a list of all object keys from repository
        """
        # Explicity set the initial hash table capacity to avoid performance issues
        # due to hash table "resonance"
        capacity = int(len(self.repository) * 1.2)
        self.chunks = ChunkIndex.create(os.path.join(self.tmpdir, 'chunks').encode('utf-8'), capacity=capacity)
        marker = None
        while True:
            result = self.repository.list(limit=10000, marker=marker)
            if not result:
                break
            marker = result[-1]
            for id_ in result:
                self.chunks[id_] = (0, 0, 0)

    def report_progress(self, msg, error=False):
        if error:
            self.error_found = True
        print(msg, file=sys.stderr if error else sys.stdout)

    def identify_key(self, repository):
        cdata = repository.get(next(self.chunks.iteritems())[0])
        return key_factory(repository, cdata)

    def rebuild_manifest(self):
        """Rebuild the manifest object if it is missing

        Iterates through all objects in the repository looking for archive metadata blocks.
        """
        self.report_progress('Rebuilding missing manifest, this might take some time...', error=True)
        manifest = Manifest(self.key, self.repository)
        for chunk_id, _ in self.chunks.iteritems():
            cdata = self.repository.get(chunk_id)
            data = self.key.decrypt(chunk_id, cdata)
            # Some basic sanity checks of the payload before feeding it into msgpack
            if len(data) < 2 or ((data[0] & 0xf0) != 0x80) or ((data[1] & 0xe0) != 0xa0):
                continue
            if not b'cmdline' in data or not b'\xa7version\x01' in data:
                continue
            try:
                archive = msgpack.unpackb(data)
            except:
                continue
            if isinstance(archive, dict) and b'items' in archive and b'cmdline' in archive:
                self.report_progress('Found archive ' + archive[b'name'].decode('utf-8'), error=True)
                manifest.archives[archive[b'name'].decode('utf-8')] = {b'id': chunk_id, b'time': archive[b'time']}
        self.report_progress('Manifest rebuild complete', error=True)
        return manifest

    def rebuild_refcounts(self):
        """Rebuild object reference counts by walking the metadata

        Missing and/or incorrect data is repaired when detected
        """
        # Exclude the manifest from chunks
        del self.chunks[Manifest.MANIFEST_ID]

        def mark_as_possibly_superseded(id_):
            if self.chunks.get(id_, (0,))[0] == 0:
                self.possibly_superseded.add(id_)

        def add_callback(chunk):
            id_ = self.key.id_hash(chunk)
            cdata = self.key.encrypt(chunk)
            add_reference(id_, len(chunk), len(cdata), cdata)
            return id_

        def add_reference(id_, size, csize, cdata=None):
            try:
                count, _, _ = self.chunks[id_]
                self.chunks[id_] = count + 1, size, csize
            except KeyError:
                assert cdata is not None
                self.chunks[id_] = 1, size, csize
                if self.repair:
                    self.repository.put(id_, cdata)

        def verify_file_chunks(item):
            """Verifies that all file chunks are present

            Missing file chunks will be replaced with new chunks of the same
            length containing all zeros.
            """
            offset = 0
            chunk_list = []
            for chunk_id, size, csize in item[b'chunks']:
                if not chunk_id in self.chunks:
                    # If a file chunk is missing, create an all empty replacement chunk
                    self.report_progress('{}: Missing file chunk detected (Byte {}-{})'.format(item[b'path'].decode('utf-8', 'surrogateescape'), offset, offset + size), error=True)
                    data = bytes(size)
                    chunk_id = self.key.id_hash(data)
                    cdata = self.key.encrypt(data)
                    csize = len(cdata)
                    add_reference(chunk_id, size, csize, cdata)
                else:
                    add_reference(chunk_id, size, csize)
                chunk_list.append((chunk_id, size, csize))
                offset += size
            item[b'chunks'] = chunk_list

        def robust_iterator(archive):
            """Iterates through all archive items

            Missing item chunks will be skipped and the msgpack stream will be restarted
            """
            unpacker = RobustUnpacker(lambda item: isinstance(item, dict) and b'path' in item)
            _state = 0
            def missing_chunk_detector(chunk_id):
                nonlocal _state
                if _state % 2 != int(not chunk_id in self.chunks):
                    _state += 1
                return _state
            for state, items in groupby(archive[b'items'], missing_chunk_detector):
                items = list(items)
                if state % 2:
                    self.report_progress('Archive metadata damage detected', error=True)
                    continue
                if state > 0:
                    unpacker.resync()
                for chunk_id, cdata in zip(items, repository.get_many(items)):
                    unpacker.feed(self.key.decrypt(chunk_id, cdata))
                    for item in unpacker:
                        yield item

        repository = cache_if_remote(self.repository)
        num_archives = len(self.manifest.archives)
        for i, (name, info) in enumerate(list(self.manifest.archives.items()), 1):
            self.report_progress('Analyzing archive {} ({}/{})'.format(name, i, num_archives))
            archive_id = info[b'id']
            if not archive_id in self.chunks:
                self.report_progress('Archive metadata block is missing', error=True)
                del self.manifest.archives[name]
                continue
            mark_as_possibly_superseded(archive_id)
            cdata = self.repository.get(archive_id)
            data = self.key.decrypt(archive_id, cdata)
            archive = StableDict(msgpack.unpackb(data))
            if archive[b'version'] != 1:
                raise Exception('Unknown archive metadata version')
            decode_dict(archive, (b'name', b'hostname', b'username', b'time'))  # fixme: argv
            items_buffer = ChunkBuffer(self.key)
            items_buffer.write_chunk = add_callback
            for item in robust_iterator(archive):
                if b'chunks' in item:
                    verify_file_chunks(item)
                items_buffer.add(item)
            items_buffer.flush(flush=True)
            for previous_item_id in archive[b'items']:
                mark_as_possibly_superseded(previous_item_id)
            archive[b'items'] = items_buffer.chunks
            data = msgpack.packb(archive, unicode_errors='surrogateescape')
            new_archive_id = self.key.id_hash(data)
            cdata = self.key.encrypt(data)
            add_reference(new_archive_id, len(data), len(cdata), cdata)
            info[b'id'] = new_archive_id

    def verify_chunks(self):
        unused = set()
        for id_, (count, size, csize) in self.chunks.iteritems():
            if count == 0:
                unused.add(id_)
        orphaned = unused - self.possibly_superseded
        if orphaned:
            self.report_progress('{} orphaned objects found'.format(len(orphaned)), error=True)
        if self.repair:
            for id_ in unused:
                self.repository.delete(id_)
            self.manifest.write()
            self.repository.commit()


########NEW FILE########
__FILENAME__ = archiver
import argparse
from binascii import hexlify
from datetime import datetime
from operator import attrgetter
import functools
import io
import os
import stat
import sys
import textwrap

from attic import __version__
from attic.archive import Archive, ArchiveChecker
from attic.repository import Repository
from attic.cache import Cache
from attic.key import key_creator
from attic.helpers import Error, location_validator, format_time, \
    format_file_mode, ExcludePattern, exclude_path, adjust_patterns, to_localtime, \
    get_cache_dir, get_keys_dir, format_timedelta, prune_within, prune_split, \
    Manifest, remove_surrogates, update_excludes, format_archive, check_extension_modules, Statistics, \
    is_cachedir, bigint_to_int
from attic.remote import RepositoryServer, RemoteRepository


class Archiver:

    def __init__(self):
        self.exit_code = 0

    def open_repository(self, location, create=False):
        if location.proto == 'ssh':
            repository = RemoteRepository(location, create=create)
        else:
            repository = Repository(location.path, create=create)
        repository._location = location
        return repository

    def print_error(self, msg, *args):
        msg = args and msg % args or msg
        self.exit_code = 1
        print('attic: ' + msg, file=sys.stderr)

    def print_verbose(self, msg, *args, **kw):
        if self.verbose:
            msg = args and msg % args or msg
            if kw.get('newline', True):
                print(msg)
            else:
                print(msg, end=' ')

    def do_serve(self, args):
        """Start Attic in server mode. This command is usually not used manually.
        """
        return RepositoryServer(restrict_to_paths=args.restrict_to_paths).serve()

    def do_init(self, args):
        """Initialize an empty repository"""
        print('Initializing repository at "%s"' % args.repository.orig)
        repository = self.open_repository(args.repository, create=True)
        key = key_creator(repository, args)
        manifest = Manifest(key, repository)
        manifest.key = key
        manifest.write()
        repository.commit()
        return self.exit_code

    def do_check(self, args):
        """Check repository consistency"""
        repository = self.open_repository(args.repository)
        if args.repair:
            while not os.environ.get('ATTIC_CHECK_I_KNOW_WHAT_I_AM_DOING'):
                self.print_error("""Warning: 'check --repair' is an experimental feature that might result
in data loss.

Type "Yes I am sure" if you understand this and want to continue.\n""")
                if input('Do you want to continue? ') == 'Yes I am sure':
                    break
        if not args.archives_only:
            print('Starting repository check...')
            if repository.check(repair=args.repair):
                print('Repository check complete, no problems found.')
            else:
                return 1
        if not args.repo_only and not ArchiveChecker().check(repository, repair=args.repair):
                return 1
        return 0

    def do_change_passphrase(self, args):
        """Change repository key file passphrase"""
        repository = self.open_repository(args.repository)
        manifest, key = Manifest.load(repository)
        key.change_passphrase()
        return 0

    def do_create(self, args):
        """Create new archive"""
        t0 = datetime.now()
        repository = self.open_repository(args.archive)
        manifest, key = Manifest.load(repository)
        cache = Cache(repository, key, manifest)
        archive = Archive(repository, key, manifest, args.archive.archive, cache=cache,
                          create=True, checkpoint_interval=args.checkpoint_interval,
                          numeric_owner=args.numeric_owner)
        # Add Attic cache dir to inode_skip list
        skip_inodes = set()
        try:
            st = os.stat(get_cache_dir())
            skip_inodes.add((st.st_ino, st.st_dev))
        except IOError:
            pass
        # Add local repository dir to inode_skip list
        if not args.archive.host:
            try:
                st = os.stat(args.archive.path)
                skip_inodes.add((st.st_ino, st.st_dev))
            except IOError:
                pass
        for path in args.paths:
            path = os.path.normpath(path)
            if args.dontcross:
                try:
                    restrict_dev = os.lstat(path).st_dev
                except OSError as e:
                    self.print_error('%s: %s', path, e)
                    continue
            else:
                restrict_dev = None
            self._process(archive, cache, args.excludes, args.exclude_caches, skip_inodes, path, restrict_dev)
        archive.save()
        if args.stats:
            t = datetime.now()
            diff = t - t0
            print('-' * 78)
            print('Archive name: %s' % args.archive.archive)
            print('Archive fingerprint: %s' % hexlify(archive.id).decode('ascii'))
            print('Start time: %s' % t0.strftime('%c'))
            print('End time: %s' % t.strftime('%c'))
            print('Duration: %s' % format_timedelta(diff))
            print('Number of files: %d' % archive.stats.nfiles)
            archive.stats.print_('This archive:', cache)
            print('-' * 78)
        return self.exit_code

    def _process(self, archive, cache, excludes, exclude_caches, skip_inodes, path, restrict_dev):
        if exclude_path(path, excludes):
            return
        try:
            st = os.lstat(path)
        except OSError as e:
            self.print_error('%s: %s', path, e)
            return
        if (st.st_ino, st.st_dev) in skip_inodes:
            return
        # Entering a new filesystem?
        if restrict_dev and st.st_dev != restrict_dev:
            return
        # Ignore unix sockets
        if stat.S_ISSOCK(st.st_mode):
            return
        self.print_verbose(remove_surrogates(path))
        if stat.S_ISREG(st.st_mode):
            try:
                archive.process_file(path, st, cache)
            except IOError as e:
                self.print_error('%s: %s', path, e)
        elif stat.S_ISDIR(st.st_mode):
            if exclude_caches and is_cachedir(path):
                return
            archive.process_item(path, st)
            try:
                entries = os.listdir(path)
            except OSError as e:
                self.print_error('%s: %s', path, e)
            else:
                for filename in sorted(entries):
                    self._process(archive, cache, excludes, exclude_caches, skip_inodes,
                                  os.path.join(path, filename), restrict_dev)
        elif stat.S_ISLNK(st.st_mode):
            archive.process_symlink(path, st)
        elif stat.S_ISFIFO(st.st_mode):
            archive.process_item(path, st)
        elif stat.S_ISCHR(st.st_mode) or stat.S_ISBLK(st.st_mode):
            archive.process_dev(path, st)
        else:
            self.print_error('Unknown file type: %s', path)

    def do_extract(self, args):
        """Extract archive contents"""
        repository = self.open_repository(args.archive)
        manifest, key = Manifest.load(repository)
        archive = Archive(repository, key, manifest, args.archive.archive,
                          numeric_owner=args.numeric_owner)
        patterns = adjust_patterns(args.paths, args.excludes)
        dirs = []
        for item in archive.iter_items(lambda item: not exclude_path(item[b'path'], patterns), preload=True):
            if not args.dry_run:
                while dirs and not item[b'path'].startswith(dirs[-1][b'path']):
                    archive.extract_item(dirs.pop(-1))
            self.print_verbose(remove_surrogates(item[b'path']))
            try:
                if args.dry_run:
                    archive.extract_item(item, dry_run=True)
                else:
                    if stat.S_ISDIR(item[b'mode']):
                        dirs.append(item)
                        archive.extract_item(item, restore_attrs=False)
                    else:
                        archive.extract_item(item)
            except IOError as e:
                self.print_error('%s: %s', remove_surrogates(item[b'path']), e)

        if not args.dry_run:
            while dirs:
                archive.extract_item(dirs.pop(-1))
        return self.exit_code

    def do_delete(self, args):
        """Delete an existing archive"""
        repository = self.open_repository(args.archive)
        manifest, key = Manifest.load(repository)
        cache = Cache(repository, key, manifest)
        archive = Archive(repository, key, manifest, args.archive.archive, cache=cache)
        stats = Statistics()
        archive.delete(stats)
        manifest.write()
        repository.commit()
        cache.commit()
        if args.stats:
            stats.print_('Deleted data:', cache)
        return self.exit_code

    def do_mount(self, args):
        """Mount archive or an entire repository as a FUSE fileystem"""
        try:
            from attic.fuse import AtticOperations
        except ImportError:
            self.print_error('the "llfuse" module is required to use this feature')
            return self.exit_code

        if not os.path.isdir(args.mountpoint) or not os.access(args.mountpoint, os.R_OK | os.W_OK | os.X_OK):
            self.print_error('%s: Mountpoint must be a writable directory' % args.mountpoint)
            return self.exit_code

        repository = self.open_repository(args.src)
        manifest, key = Manifest.load(repository)
        if args.src.archive:
            archive = Archive(repository, key, manifest, args.src.archive)
        else:
            archive = None
        operations = AtticOperations(key, repository, manifest, archive)
        self.print_verbose("Mounting filesystem")
        try:
            operations.mount(args.mountpoint, args.options, args.foreground)
        except RuntimeError:
            # Relevant error message already printed to stderr by fuse
            self.exit_code = 1
        return self.exit_code

    def do_list(self, args):
        """List archive or repository contents"""
        repository = self.open_repository(args.src)
        manifest, key = Manifest.load(repository)
        if args.src.archive:
            tmap = {1: 'p', 2: 'c', 4: 'd', 6: 'b', 0o10: '-', 0o12: 'l', 0o14: 's'}
            archive = Archive(repository, key, manifest, args.src.archive)
            for item in archive.iter_items():
                type = tmap.get(item[b'mode'] // 4096, '?')
                mode = format_file_mode(item[b'mode'])
                size = 0
                if type == '-':
                    try:
                        size = sum(size for _, size, _ in item[b'chunks'])
                    except KeyError:
                        pass
                mtime = format_time(datetime.fromtimestamp(bigint_to_int(item[b'mtime']) / 1e9))
                if b'source' in item:
                    if type == 'l':
                        extra = ' -> %s' % item[b'source']
                    else:
                        type = 'h'
                        extra = ' link to %s' % item[b'source']
                else:
                    extra = ''
                print('%s%s %-6s %-6s %8d %s %s%s' % (type, mode, item[b'user'] or item[b'uid'],
                                                  item[b'group'] or item[b'gid'], size, mtime,
                                                  remove_surrogates(item[b'path']), extra))
        else:
            for archive in sorted(Archive.list_archives(repository, key, manifest), key=attrgetter('ts')):
                print(format_archive(archive))
        return self.exit_code

    def do_info(self, args):
        """Show archive details such as disk space used"""
        repository = self.open_repository(args.archive)
        manifest, key = Manifest.load(repository)
        cache = Cache(repository, key, manifest)
        archive = Archive(repository, key, manifest, args.archive.archive, cache=cache)
        stats = archive.calc_stats(cache)
        print('Name:', archive.name)
        print('Fingerprint: %s' % hexlify(archive.id).decode('ascii'))
        print('Hostname:', archive.metadata[b'hostname'])
        print('Username:', archive.metadata[b'username'])
        print('Time: %s' % to_localtime(archive.ts).strftime('%c'))
        print('Command line:', remove_surrogates(' '.join(archive.metadata[b'cmdline'])))
        print('Number of files: %d' % archive.stats.nfiles)
        stats.print_('This archive:', cache)
        return self.exit_code

    def do_prune(self, args):
        """Prune repository archives according to specified rules"""
        repository = self.open_repository(args.repository)
        manifest, key = Manifest.load(repository)
        cache = Cache(repository, key, manifest)
        archives = list(sorted(Archive.list_archives(repository, key, manifest, cache),
                               key=attrgetter('ts'), reverse=True))
        if args.hourly + args.daily + args.weekly + args.monthly + args.yearly == 0 and args.within is None:
            self.print_error('At least one of the "within", "hourly", "daily", "weekly", "monthly" or "yearly" '
                             'settings must be specified')
            return 1
        if args.prefix:
            archives = [archive for archive in archives if archive.name.startswith(args.prefix)]
        keep = []
        if args.within:
            keep += prune_within(archives, args.within)
        if args.hourly:
            keep += prune_split(archives, '%Y-%m-%d %H', args.hourly, keep)
        if args.daily:
            keep += prune_split(archives, '%Y-%m-%d', args.daily, keep)
        if args.weekly:
            keep += prune_split(archives, '%G-%V', args.weekly, keep)
        if args.monthly:
            keep += prune_split(archives, '%Y-%m', args.monthly, keep)
        if args.yearly:
            keep += prune_split(archives, '%Y', args.yearly, keep)

        keep.sort(key=attrgetter('ts'), reverse=True)
        to_delete = [a for a in archives if a not in keep]
        stats = Statistics()
        for archive in keep:
            self.print_verbose('Keeping archive: %s' % format_archive(archive))
        for archive in to_delete:
            if args.dry_run:
                self.print_verbose('Would prune:     %s' % format_archive(archive))
            else:
                self.print_verbose('Pruning archive: %s' % format_archive(archive))
                archive.delete(stats)
        if to_delete and not args.dry_run:
            manifest.write()
            repository.commit()
            cache.commit()
        if args.stats:
            stats.print_('Deleted data:', cache)
        return self.exit_code

    helptext = {}
    helptext['patterns'] = '''
        Exclude patterns use a variant of shell pattern syntax, with '*' matching any
        number of characters, '?' matching any single character, '[...]' matching any
        single character specified, including ranges, and '[!...]' matching any
        character not specified.  For the purpose of these patterns, the path
        separator ('\\' for Windows and '/' on other systems) is not treated
        specially.  For a path to match a pattern, it must completely match from
        start to end, or must match from the start to just before a path separator.
        Except for the root path, paths will never end in the path separator when
        matching is attempted.  Thus, if a given pattern ends in a path separator, a
        '*' is appended before matching is attempted.  Patterns with wildcards should
        be quoted to protect them from shell expansion.

        Examples:

        # Exclude '/home/user/file.o' but not '/home/user/file.odt':
        $ attic create -e '*.o' repo.attic /

        # Exclude '/home/user/junk' and '/home/user/subdir/junk' but
        # not '/home/user/importantjunk' or '/etc/junk':
        $ attic create -e '/home/*/junk' repo.attic /

        # Exclude the contents of '/home/user/cache' but not the directory itself:
        $ attic create -e /home/user/cache/ repo.attic /

        # The file '/home/user/cache/important' is *not* backed up:
        $ attic create -e /home/user/cache/ repo.attic / /home/user/cache/important
        '''

    def do_help(self, parser, commands, args):
        if not args.topic:
            parser.print_help()
        elif args.topic in self.helptext:
            print(self.helptext[args.topic])
        elif args.topic in commands:
            if args.epilog_only:
                print(commands[args.topic].epilog)
            elif args.usage_only:
                commands[args.topic].epilog = None
                commands[args.topic].print_help()
            else:
                commands[args.topic].print_help()
        else:
            parser.error('No help available on %s' % (args.topic,))
        return self.exit_code

    def preprocess_args(self, args):
        deprecations = [
            ('--hourly', '--keep-hourly', 'Warning: "--hourly" has been deprecated. Use "--keep-hourly" instead.'),
            ('--daily', '--keep-daily', 'Warning: "--daily" has been deprecated. Use "--keep-daily" instead.'),
            ('--weekly', '--keep-weekly', 'Warning: "--weekly" has been deprecated. Use "--keep-weekly" instead.'),
            ('--monthly', '--keep-monthly', 'Warning: "--monthly" has been deprecated. Use "--keep-monthly" instead.'),
            ('--yearly', '--keep-yearly', 'Warning: "--yearly" has been deprecated. Use "--keep-yearly" instead.')
        ]
        if args and args[0] == 'verify':
            print('Warning: "attic verify" has been deprecated. Use "attic extract --dry-run" instead.')
            args = ['extract', '--dry-run'] + args[1:]
        for i, arg in enumerate(args[:]):
            for old_name, new_name, warning in deprecations:
                if arg.startswith(old_name):
                    args[i] = arg.replace(old_name, new_name)
                    print(warning)
        return args

    def run(self, args=None):
        check_extension_modules()
        keys_dir = get_keys_dir()
        if not os.path.exists(keys_dir):
            os.makedirs(keys_dir)
            os.chmod(keys_dir, stat.S_IRWXU)
        cache_dir = get_cache_dir()
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            os.chmod(cache_dir, stat.S_IRWXU)
            with open(os.path.join(cache_dir, 'CACHEDIR.TAG'), 'w') as fd:
                fd.write(textwrap.dedent("""
                    Signature: 8a477f597d28d172789f06886806bc55
                    # This file is a cache directory tag created by Attic.
                    # For information about cache directory tags, see:
                    #       http://www.brynosaurus.com/cachedir/
                    """).lstrip())
        common_parser = argparse.ArgumentParser(add_help=False)
        common_parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                            default=False,
                            help='verbose output')

        # We can't use argparse for "serve" since we don't want it to show up in "Available commands"
        if args:
            args = self.preprocess_args(args)

        parser = argparse.ArgumentParser(description='Attic %s - Deduplicated Backups' % __version__)
        subparsers = parser.add_subparsers(title='Available commands')

        subparser = subparsers.add_parser('serve', parents=[common_parser],
                                          description=self.do_serve.__doc__)
        subparser.set_defaults(func=self.do_serve)
        subparser.add_argument('--restrict-to-path', dest='restrict_to_paths', action='append',
                               metavar='PATH', help='restrict repository access to PATH')
        init_epilog = textwrap.dedent("""
        This command initializes an empty repository. A repository is a filesystem
        directory containing the deduplicated data from zero or more archives.
        Encryption can be enabled at repository init time.
        """)
        subparser = subparsers.add_parser('init', parents=[common_parser],
                                          description=self.do_init.__doc__, epilog=init_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_init)
        subparser.add_argument('repository', metavar='REPOSITORY',
                               type=location_validator(archive=False),
                               help='repository to create')
        subparser.add_argument('-e', '--encryption', dest='encryption',
                               choices=('none', 'passphrase', 'keyfile'), default='none',
                               help='select encryption method')

        check_epilog = textwrap.dedent("""
        The check command verifies the consistency of a repository and the corresponding
        archives. The underlying repository data files are first checked to detect bit rot
        and other types of damage. After that the consistency and correctness of the archive
        metadata is verified.

        The archive metadata checks can be time consuming and requires access to the key
        file and/or passphrase if encryption is enabled. These checks can be skipped using
        the --repository-only option.
        """)
        subparser = subparsers.add_parser('check', parents=[common_parser],
                                          description=self.do_check.__doc__,
                                          epilog=check_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_check)
        subparser.add_argument('repository', metavar='REPOSITORY',
                               type=location_validator(archive=False),
                               help='repository to check consistency of')
        subparser.add_argument('--repository-only', dest='repo_only', action='store_true',
                               default=False,
                               help='only perform repository checks')
        subparser.add_argument('--archives-only', dest='archives_only', action='store_true',
                               default=False,
                               help='only perform archives checks')
        subparser.add_argument('--repair', dest='repair', action='store_true',
                               default=False,
                               help='attempt to repair any inconsistencies found')

        change_passphrase_epilog = textwrap.dedent("""
        The key files used for repository encryption are optionally passphrase
        protected. This command can be used to change this passphrase.
        """)
        subparser = subparsers.add_parser('change-passphrase', parents=[common_parser],
                                          description=self.do_change_passphrase.__doc__,
                                          epilog=change_passphrase_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_change_passphrase)
        subparser.add_argument('repository', metavar='REPOSITORY',
                               type=location_validator(archive=False))

        create_epilog = textwrap.dedent("""
        This command creates a backup archive containing all files found while recursively
        traversing all paths specified. The archive will consume almost no disk space for
        files or parts of files that have already been stored in other archives.

        See "attic help patterns" for more help on exclude patterns.
        """)

        subparser = subparsers.add_parser('create', parents=[common_parser],
                                          description=self.do_create.__doc__,
                                          epilog=create_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_create)
        subparser.add_argument('-s', '--stats', dest='stats',
                               action='store_true', default=False,
                               help='print statistics for the created archive')
        subparser.add_argument('-e', '--exclude', dest='excludes',
                               type=ExcludePattern, action='append',
                               metavar="PATTERN", help='exclude paths matching PATTERN')
        subparser.add_argument('--exclude-from', dest='exclude_files',
                               type=argparse.FileType('r'), action='append',
                               metavar='EXCLUDEFILE', help='read exclude patterns from EXCLUDEFILE, one per line')
        subparser.add_argument('--exclude-caches', dest='exclude_caches',
                               action='store_true', default=False,
                               help='exclude directories that contain a CACHEDIR.TAG file (http://www.brynosaurus.com/cachedir/spec.html)')
        subparser.add_argument('-c', '--checkpoint-interval', dest='checkpoint_interval',
                               type=int, default=300, metavar='SECONDS',
                               help='write checkpoint every SECONDS seconds (Default: 300)')
        subparser.add_argument('--do-not-cross-mountpoints', dest='dontcross',
                               action='store_true', default=False,
                               help='do not cross mount points')
        subparser.add_argument('--numeric-owner', dest='numeric_owner',
                               action='store_true', default=False,
                               help='only store numeric user and group identifiers')
        subparser.add_argument('archive', metavar='ARCHIVE',
                               type=location_validator(archive=True),
                               help='archive to create')
        subparser.add_argument('paths', metavar='PATH', nargs='+', type=str,
                               help='paths to archive')

        extract_epilog = textwrap.dedent("""
        This command extracts the contents of an archive. By default the entire
        archive is extracted but a subset of files and directories can be selected
        by passing a list of ``PATHs`` as arguments. The file selection can further
        be restricted by using the ``--exclude`` option.

        See "attic help patterns" for more help on exclude patterns.
        """)
        subparser = subparsers.add_parser('extract', parents=[common_parser],
                                          description=self.do_extract.__doc__,
                                          epilog=extract_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_extract)
        subparser.add_argument('-n', '--dry-run', dest='dry_run',
                               default=False, action='store_true',
                               help='do not actually change any files')
        subparser.add_argument('-e', '--exclude', dest='excludes',
                               type=ExcludePattern, action='append',
                               metavar="PATTERN", help='exclude paths matching PATTERN')
        subparser.add_argument('--exclude-from', dest='exclude_files',
                               type=argparse.FileType('r'), action='append',
                               metavar='EXCLUDEFILE', help='read exclude patterns from EXCLUDEFILE, one per line')
        subparser.add_argument('--numeric-owner', dest='numeric_owner',
                               action='store_true', default=False,
                               help='only obey numeric user and group identifiers')
        subparser.add_argument('archive', metavar='ARCHIVE',
                               type=location_validator(archive=True),
                               help='archive to extract')
        subparser.add_argument('paths', metavar='PATH', nargs='*', type=str,
                               help='paths to extract')

        delete_epilog = textwrap.dedent("""
        This command deletes an archive from the repository. Any disk space not
        shared with any other existing archive is also reclaimed.
        """)
        subparser = subparsers.add_parser('delete', parents=[common_parser],
                                          description=self.do_delete.__doc__,
                                          epilog=delete_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_delete)
        subparser.add_argument('-s', '--stats', dest='stats',
                               action='store_true', default=False,
                               help='print statistics for the deleted archive')
        subparser.add_argument('archive', metavar='ARCHIVE',
                               type=location_validator(archive=True),
                               help='archive to delete')

        list_epilog = textwrap.dedent("""
        This command lists the contents of a repository or an archive.
        """)
        subparser = subparsers.add_parser('list', parents=[common_parser],
                                          description=self.do_list.__doc__,
                                          epilog=list_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_list)
        subparser.add_argument('src', metavar='REPOSITORY_OR_ARCHIVE', type=location_validator(),
                               help='repository/archive to list contents of')
        mount_epilog = textwrap.dedent("""
        This command mounts an archive as a FUSE filesystem. This can be useful for
        browsing an archive or restoring individual files. Unless the ``--foreground``
        option is given the command will run in the background until the filesystem
        is ``umounted``.
        """)
        subparser = subparsers.add_parser('mount', parents=[common_parser],
                                          description=self.do_mount.__doc__,
                                          epilog=mount_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_mount)
        subparser.add_argument('src', metavar='REPOSITORY_OR_ARCHIVE', type=location_validator(),
                               help='repository/archive to mount')
        subparser.add_argument('mountpoint', metavar='MOUNTPOINT', type=str,
                               help='where to mount filesystem')
        subparser.add_argument('-f', '--foreground', dest='foreground',
                               action='store_true', default=False,
                               help='stay in foreground, do not daemonize')
        subparser.add_argument('-o', dest='options', type=str,
                               help='Extra mount options')

        info_epilog = textwrap.dedent("""
        This command displays some detailed information about the specified archive.
        """)
        subparser = subparsers.add_parser('info', parents=[common_parser],
                                          description=self.do_info.__doc__,
                                          epilog=info_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_info)
        subparser.add_argument('archive', metavar='ARCHIVE',
                               type=location_validator(archive=True),
                               help='archive to display information about')

        prune_epilog = textwrap.dedent("""
        The prune command prunes a repository by deleting archives not matching
        any of the specified retention options. This command is normally used by
        automated backup scripts wanting to keep a certain number of historic backups.

        As an example, "-d 7" means to keep the latest backup on each day for 7 days.
        Days without backups do not count towards the total.
        The rules are applied from hourly to yearly, and backups selected by previous
        rules do not count towards those of later rules. The time that each backup
        completes is used for pruning purposes. Dates and times are interpreted in
        the local timezone, and weeks go from Monday to Sunday. Specifying a
        negative number of archives to keep means that there is no limit.

        The "--keep-within" option takes an argument of the form "<int><char>",
        where char is "H", "d", "w", "m", "y". For example, "--keep-within 2d" means
        to keep all archives that were created within the past 48 hours.
        "1m" is taken to mean "31d". The archives kept with this option do not
        count towards the totals specified by any other options.

        If a prefix is set with -p, then only archives that start with the prefix are
        considered for deletion and only those archives count towards the totals
        specified by the rules.
        """)
        subparser = subparsers.add_parser('prune', parents=[common_parser],
                                          description=self.do_prune.__doc__,
                                          epilog=prune_epilog,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(func=self.do_prune)
        subparser.add_argument('-n', '--dry-run', dest='dry_run',
                               default=False, action='store_true',
                               help='do not change repository')
        subparser.add_argument('-s', '--stats', dest='stats',
                               action='store_true', default=False,
                               help='print statistics for the deleted archive')
        subparser.add_argument('--keep-within', dest='within', type=str, metavar='WITHIN',
                               help='keep all archives within this time interval')
        subparser.add_argument('-H', '--keep-hourly', dest='hourly', type=int, default=0,
                               help='number of hourly archives to keep')
        subparser.add_argument('-d', '--keep-daily', dest='daily', type=int, default=0,
                               help='number of daily archives to keep')
        subparser.add_argument('-w', '--keep-weekly', dest='weekly', type=int, default=0,
                               help='number of weekly archives to keep')
        subparser.add_argument('-m', '--keep-monthly', dest='monthly', type=int, default=0,
                               help='number of monthly archives to keep')
        subparser.add_argument('-y', '--keep-yearly', dest='yearly', type=int, default=0,
                               help='number of yearly archives to keep')
        subparser.add_argument('-p', '--prefix', dest='prefix', type=str,
                               help='only consider archive names starting with this prefix')
        subparser.add_argument('repository', metavar='REPOSITORY',
                               type=location_validator(archive=False),
                               help='repository to prune')

        subparser = subparsers.add_parser('help', parents=[common_parser],
                                          description='Extra help')
        subparser.add_argument('--epilog-only', dest='epilog_only',
                               action='store_true', default=False)
        subparser.add_argument('--usage-only', dest='usage_only',
                               action='store_true', default=False)
        subparser.set_defaults(func=functools.partial(self.do_help, parser, subparsers.choices))
        subparser.add_argument('topic', metavar='TOPIC', type=str, nargs='?',
                               help='additional help on TOPIC')

        args = parser.parse_args(args or ['-h'])
        self.verbose = args.verbose
        update_excludes(args)
        return args.func(args)


def main():
    # Make sure stdout and stderr have errors='replace') to avoid unicode
    # issues when print()-ing unicode file names
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, sys.stdout.encoding, 'replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, sys.stderr.encoding, 'replace', line_buffering=True)
    archiver = Archiver()
    try:
        exit_code = archiver.run(sys.argv[1:])
    except Error as e:
        archiver.print_error(e.get_message())
        exit_code = e.exit_code
    except KeyboardInterrupt:
        archiver.print_error('Error: Keyboard interrupt')
        exit_code = 1
    else:
        if exit_code:
            archiver.print_error('Exiting with failure status due to previous errors')
    sys.exit(exit_code)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cache
from configparser import RawConfigParser
from attic.remote import cache_if_remote
import msgpack
import os
from binascii import hexlify
import shutil

from .helpers import Error, get_cache_dir, decode_dict, st_mtime_ns, unhexlify, UpgradableLock
from .hashindex import ChunkIndex


class Cache(object):
    """Client Side cache
    """
    # Do not cache file metadata for files smaller than this
    FILE_MIN_SIZE = 4096

    class RepositoryReplay(Error):
        """Cache is newer than repository, refusing to continue"""

    def __init__(self, repository, key, manifest, path=None, sync=True):
        self.timestamp = None
        self.txn_active = False
        self.repository = repository
        self.key = key
        self.manifest = manifest
        self.path = path or os.path.join(get_cache_dir(), hexlify(repository.id).decode('ascii'))
        if not os.path.exists(self.path):
            self.create()
        self.open()
        if sync and self.manifest.id != self.manifest_id:
            # If repository is older than the cache something fishy is going on
            if self.timestamp and self.timestamp > manifest.timestamp:
                raise self.RepositoryReplay()
            self.sync()
            self.commit()

    def __del__(self):
        self.close()

    def create(self):
        """Create a new empty cache at `path`
        """
        os.makedirs(self.path)
        with open(os.path.join(self.path, 'README'), 'w') as fd:
            fd.write('This is an Attic cache')
        config = RawConfigParser()
        config.add_section('cache')
        config.set('cache', 'version', '1')
        config.set('cache', 'repository', hexlify(self.repository.id).decode('ascii'))
        config.set('cache', 'manifest', '')
        with open(os.path.join(self.path, 'config'), 'w') as fd:
            config.write(fd)
        ChunkIndex.create(os.path.join(self.path, 'chunks').encode('utf-8'))
        with open(os.path.join(self.path, 'files'), 'w') as fd:
            pass  # empty file

    def open(self):
        if not os.path.isdir(self.path):
            raise Exception('%s Does not look like an Attic cache' % self.path)
        self.lock = UpgradableLock(os.path.join(self.path, 'config'), exclusive=True)
        self.rollback()
        self.config = RawConfigParser()
        self.config.read(os.path.join(self.path, 'config'))
        if self.config.getint('cache', 'version') != 1:
            raise Exception('%s Does not look like an Attic cache')
        self.id = self.config.get('cache', 'repository')
        self.manifest_id = unhexlify(self.config.get('cache', 'manifest'))
        self.timestamp = self.config.get('cache', 'timestamp', fallback=None)
        self.chunks = ChunkIndex(os.path.join(self.path, 'chunks').encode('utf-8'))
        self.files = None

    def close(self):
        self.lock.release()

    def _read_files(self):
        self.files = {}
        self._newest_mtime = 0
        with open(os.path.join(self.path, 'files'), 'rb') as fd:
            u = msgpack.Unpacker(use_list=True)
            while True:
                data = fd.read(64 * 1024)
                if not data:
                    break
                u.feed(data)
                for path_hash, item in u:
                    if item[2] > self.FILE_MIN_SIZE:
                        item[0] += 1
                        self.files[path_hash] = item

    def begin_txn(self):
        # Initialize transaction snapshot
        txn_dir = os.path.join(self.path, 'txn.tmp')
        os.mkdir(txn_dir)
        shutil.copy(os.path.join(self.path, 'config'), txn_dir)
        shutil.copy(os.path.join(self.path, 'chunks'), txn_dir)
        shutil.copy(os.path.join(self.path, 'files'), txn_dir)
        os.rename(os.path.join(self.path, 'txn.tmp'),
                  os.path.join(self.path, 'txn.active'))
        self.txn_active = True

    def commit(self):
        """Commit transaction
        """
        if not self.txn_active:
            return
        if self.files is not None:
            with open(os.path.join(self.path, 'files'), 'wb') as fd:
                for item in self.files.items():
                    # Discard cached files with the newest mtime to avoid
                    # issues with filesystem snapshots and mtime precision
                    if item[1][0] < 10 and item[1][3] < self._newest_mtime:
                        msgpack.pack(item, fd)
        self.config.set('cache', 'manifest', hexlify(self.manifest.id).decode('ascii'))
        self.config.set('cache', 'timestamp', self.manifest.timestamp)
        with open(os.path.join(self.path, 'config'), 'w') as fd:
            self.config.write(fd)
        self.chunks.flush()
        os.rename(os.path.join(self.path, 'txn.active'),
                  os.path.join(self.path, 'txn.tmp'))
        shutil.rmtree(os.path.join(self.path, 'txn.tmp'))
        self.txn_active = False

    def rollback(self):
        """Roll back partial and aborted transactions
        """
        # Remove partial transaction
        if os.path.exists(os.path.join(self.path, 'txn.tmp')):
            shutil.rmtree(os.path.join(self.path, 'txn.tmp'))
        # Roll back active transaction
        txn_dir = os.path.join(self.path, 'txn.active')
        if os.path.exists(txn_dir):
            shutil.copy(os.path.join(txn_dir, 'config'), self.path)
            shutil.copy(os.path.join(txn_dir, 'chunks'), self.path)
            shutil.copy(os.path.join(txn_dir, 'files'), self.path)
            os.rename(txn_dir, os.path.join(self.path, 'txn.tmp'))
            if os.path.exists(os.path.join(self.path, 'txn.tmp')):
                shutil.rmtree(os.path.join(self.path, 'txn.tmp'))
        self.txn_active = False

    def sync(self):
        """Initializes cache by fetching and reading all archive indicies
        """
        def add(id, size, csize):
            try:
                count, size, csize = self.chunks[id]
                self.chunks[id] = count + 1, size, csize
            except KeyError:
                self.chunks[id] = 1, size, csize
        self.begin_txn()
        print('Initializing cache...')
        self.chunks.clear()
        unpacker = msgpack.Unpacker()
        repository = cache_if_remote(self.repository)
        for name, info in self.manifest.archives.items():
            archive_id = info[b'id']
            cdata = repository.get(archive_id)
            data = self.key.decrypt(archive_id, cdata)
            add(archive_id, len(data), len(cdata))
            archive = msgpack.unpackb(data)
            if archive[b'version'] != 1:
                raise Exception('Unknown archive metadata version')
            decode_dict(archive, (b'name',))
            print('Analyzing archive:', archive[b'name'])
            for key, chunk in zip(archive[b'items'], repository.get_many(archive[b'items'])):
                data = self.key.decrypt(key, chunk)
                add(key, len(data), len(chunk))
                unpacker.feed(data)
                for item in unpacker:
                    if b'chunks' in item:
                        for chunk_id, size, csize in item[b'chunks']:
                            add(chunk_id, size, csize)

    def add_chunk(self, id, data, stats):
        if not self.txn_active:
            self.begin_txn()
        if self.seen_chunk(id):
            return self.chunk_incref(id, stats)
        size = len(data)
        data = self.key.encrypt(data)
        csize = len(data)
        self.repository.put(id, data, wait=False)
        self.chunks[id] = (1, size, csize)
        stats.update(size, csize, True)
        return id, size, csize

    def seen_chunk(self, id):
        return self.chunks.get(id, (0, 0, 0))[0]

    def chunk_incref(self, id, stats):
        if not self.txn_active:
            self.begin_txn()
        count, size, csize = self.chunks[id]
        self.chunks[id] = (count + 1, size, csize)
        stats.update(size, csize, False)
        return id, size, csize

    def chunk_decref(self, id, stats):
        if not self.txn_active:
            self.begin_txn()
        count, size, csize = self.chunks[id]
        if count == 1:
            del self.chunks[id]
            self.repository.delete(id, wait=False)
            stats.update(-size, -csize, True)
        else:
            self.chunks[id] = (count - 1, size, csize)
            stats.update(-size, -csize, False)

    def file_known_and_unchanged(self, path_hash, st):
        if self.files is None:
            self._read_files()
        entry = self.files.get(path_hash)
        if (entry and entry[3] == st_mtime_ns(st)
            and entry[2] == st.st_size and entry[1] == st.st_ino):
            # reset entry age
            if entry[0] != 0:
                self.files[path_hash][0] = 0
            return entry[4]
        else:
            return None

    def memorize_file(self, path_hash, st, ids):
        if st.st_size > self.FILE_MIN_SIZE:
            # Entry: Age, inode, size, mtime, chunk ids
            mtime_ns = st_mtime_ns(st)
            self.files[path_hash] = 0, st.st_ino, st.st_size, mtime_ns, ids
            self._newest_mtime = max(self._newest_mtime, mtime_ns)

########NEW FILE########
__FILENAME__ = fuse
from collections import defaultdict
import errno
import io
import llfuse
import msgpack
import os
import stat
import tempfile
import time
from attic.archive import Archive
from attic.helpers import daemonize
from attic.remote import cache_if_remote

# Does this version of llfuse support ns precision?
have_fuse_mtime_ns = hasattr(llfuse.EntryAttributes, 'st_mtime_ns')


class ItemCache:
    def __init__(self):
        self.fd = tempfile.TemporaryFile()
        self.offset = 1000000

    def add(self, item):
        pos = self.fd.seek(0, io.SEEK_END)
        self.fd.write(msgpack.packb(item))
        return pos + self.offset

    def get(self, inode):
        self.fd.seek(inode - self.offset, io.SEEK_SET)
        return next(msgpack.Unpacker(self.fd))


class AtticOperations(llfuse.Operations):
    """Export Attic archive as a fuse filesystem
    """
    def __init__(self, key, repository, manifest, archive):
        super(AtticOperations, self).__init__()
        self._inode_count = 0
        self.key = key
        self.repository = cache_if_remote(repository)
        self.items = {}
        self.parent = {}
        self.contents = defaultdict(dict)
        self.default_dir = {b'mode': 0o40755, b'mtime': int(time.time() * 1e9), b'uid': os.getuid(), b'gid': os.getgid()}
        self.pending_archives = {}
        self.cache = ItemCache()
        if archive:
            self.process_archive(archive)
        else:
            # Create root inode
            self.parent[1] = self.allocate_inode()
            self.items[1] = self.default_dir
            for archive_name in manifest.archives:
                # Create archive placeholder inode
                archive_inode = self.allocate_inode()
                self.items[archive_inode] = self.default_dir
                self.parent[archive_inode] = 1
                self.contents[1][os.fsencode(archive_name)] = archive_inode
                self.pending_archives[archive_inode] = Archive(repository, key, manifest, archive_name)

    def process_archive(self, archive, prefix=[]):
        """Build fuse inode hierarcy from archive metadata
        """
        unpacker = msgpack.Unpacker()
        for key, chunk in zip(archive.metadata[b'items'], self.repository.get_many(archive.metadata[b'items'])):
            data = self.key.decrypt(key, chunk)
            unpacker.feed(data)
            for item in unpacker:
                segments = prefix + os.fsencode(os.path.normpath(item[b'path'])).split(b'/')
                del item[b'path']
                num_segments = len(segments)
                parent = 1
                for i, segment in enumerate(segments, 1):
                    # Insert a default root inode if needed
                    if self._inode_count == 0 and segment:
                        archive_inode = self.allocate_inode()
                        self.items[archive_inode] = self.default_dir
                        self.parent[archive_inode] = parent
                    # Leaf segment?
                    if i == num_segments:
                        if b'source' in item and stat.S_ISREG(item[b'mode']):
                            inode = self._find_inode(item[b'source'], prefix)
                            item = self.cache.get(inode)
                            item[b'nlink'] = item.get(b'nlink', 1) + 1
                            self.items[inode] = item
                        else:
                            inode = self.cache.add(item)
                        self.parent[inode] = parent
                        if segment:
                            self.contents[parent][segment] = inode
                    elif segment in self.contents[parent]:
                        parent = self.contents[parent][segment]
                    else:
                        inode = self.allocate_inode()
                        self.items[inode] = self.default_dir
                        self.parent[inode] = parent
                        if segment:
                            self.contents[parent][segment] = inode
                        parent = inode

    def allocate_inode(self):
        self._inode_count += 1
        return self._inode_count

    def statfs(self):
        stat_ = llfuse.StatvfsData()
        stat_.f_bsize = 512
        stat_.f_frsize = 512
        stat_.f_blocks = 0
        stat_.f_bfree = 0
        stat_.f_bavail = 0
        stat_.f_files = 0
        stat_.f_ffree = 0
        stat_.f_favail = 0
        return stat_

    def get_item(self, inode):
        try:
            return self.items[inode]
        except KeyError:
            return self.cache.get(inode)

    def _find_inode(self, path, prefix=[]):
        segments = prefix + os.fsencode(os.path.normpath(path)).split(b'/')
        inode = 1
        for segment in segments:
            inode = self.contents[inode][segment]
        return inode

    def getattr(self, inode):
        item = self.get_item(inode)
        size = 0
        try:
            size = sum(size for _, size, _ in item[b'chunks'])
        except KeyError:
            pass
        entry = llfuse.EntryAttributes()
        entry.st_ino = inode
        entry.generation = 0
        entry.entry_timeout = 300
        entry.attr_timeout = 300
        entry.st_mode = item[b'mode']
        entry.st_nlink = item.get(b'nlink', 1)
        entry.st_uid = item[b'uid']
        entry.st_gid = item[b'gid']
        entry.st_rdev = item.get(b'rdev', 0)
        entry.st_size = size
        entry.st_blksize = 512
        entry.st_blocks = 1
        if have_fuse_mtime_ns:
            entry.st_atime_ns = item[b'mtime']
            entry.st_mtime_ns = item[b'mtime']
            entry.st_ctime_ns = item[b'mtime']
        else:
            entry.st_atime = item[b'mtime'] / 1e9
            entry.st_mtime = item[b'mtime'] / 1e9
            entry.st_ctime = item[b'mtime'] / 1e9
        return entry

    def listxattr(self, inode):
        item = self.get_item(inode)
        return item.get(b'xattrs', {}).keys()

    def getxattr(self, inode, name):
        item = self.get_item(inode)
        try:
            return item.get(b'xattrs', {})[name]
        except KeyError:
            raise llfuse.FUSEError(errno.ENODATA)

    def _load_pending_archive(self, inode):
        # Check if this is an archive we need to load
        archive = self.pending_archives.pop(inode, None)
        if archive:
            self.process_archive(archive, [os.fsencode(archive.name)])

    def lookup(self, parent_inode, name):
        self._load_pending_archive(parent_inode)
        if name == b'.':
            inode = parent_inode
        elif name == b'..':
            inode = self.parent[parent_inode]
        else:
            inode = self.contents[parent_inode].get(name)
            if not inode:
                raise llfuse.FUSEError(errno.ENOENT)
        return self.getattr(inode)

    def open(self, inode, flags):
        return inode

    def opendir(self, inode):
        self._load_pending_archive(inode)
        return inode

    def read(self, fh, offset, size):
        parts = []
        item = self.get_item(fh)
        for id, s, csize in item[b'chunks']:
            if s < offset:
                offset -= s
                continue
            n = min(size, s - offset)
            chunk = self.key.decrypt(id, self.repository.get(id))
            parts.append(chunk[offset:offset+n])
            offset = 0
            size -= n
            if not size:
                break
        return b''.join(parts)

    def readdir(self, fh, off):
        entries = [(b'.', fh), (b'..', self.parent[fh])]
        entries.extend(self.contents[fh].items())
        for i, (name, inode) in enumerate(entries[off:], off):
            yield name, self.getattr(inode), i + 1

    def readlink(self, inode):
        item = self.get_item(inode)
        return os.fsencode(item[b'source'])

    def mount(self, mountpoint, extra_options, foreground=False):
        options = ['fsname=atticfs', 'ro']
        if extra_options:
            options.extend(extra_options.split(','))
        llfuse.init(self, mountpoint, options)
        if not foreground:
            daemonize()
        try:
            llfuse.main(single=True)
        except:
            llfuse.close()
            raise
        llfuse.close()

########NEW FILE########
__FILENAME__ = helpers
import argparse
import binascii
import grp
import msgpack
import os
import pwd
import re
import stat
import sys
import time
from datetime import datetime, timezone, timedelta
from fnmatch import translate
from operator import attrgetter
import fcntl

import attic.hashindex
import attic.chunker
import attic.crypto


class Error(Exception):
    """Error base class"""

    exit_code = 1

    def get_message(self):
        return 'Error: ' + type(self).__doc__.format(*self.args)


class ExtensionModuleError(Error):
    """The Attic binary extension modules does not seem to be properly installed"""


class UpgradableLock:

    class LockUpgradeFailed(Error):
        """Failed to acquire write lock on {}"""

    def __init__(self, path, exclusive=False):
        self.path = path
        try:
            self.fd = open(path, 'r+')
        except IOError:
            self.fd = open(path, 'r')
        if exclusive:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)
        else:
            fcntl.lockf(self.fd, fcntl.LOCK_SH)
        self.is_exclusive = exclusive

    def upgrade(self):
        try:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)
        except OSError as e:
            raise self.LockUpgradeFailed(self.path)
        self.is_exclusive = True

    def release(self):
        fcntl.lockf(self.fd, fcntl.LOCK_UN)
        self.fd.close()


def check_extension_modules():
    import attic.platform
    if (attic.hashindex.API_VERSION != 1 or
        attic.chunker.API_VERSION != 1 or
        attic.crypto.API_VERSION != 2 or
        attic.platform.API_VERSION != 1):
        raise ExtensionModuleError


class Manifest:

    MANIFEST_ID = b'\0' * 32

    def __init__(self, key, repository):
        self.archives = {}
        self.config = {}
        self.key = key
        self.repository = repository

    @classmethod
    def load(cls, repository, key=None):
        from .key import key_factory
        cdata = repository.get(cls.MANIFEST_ID)
        if not key:
            key = key_factory(repository, cdata)
        manifest = cls(key, repository)
        data = key.decrypt(None, cdata)
        manifest.id = key.id_hash(data)
        m = msgpack.unpackb(data)
        if not m.get(b'version') == 1:
            raise ValueError('Invalid manifest version')
        manifest.archives = dict((k.decode('utf-8'), v) for k,v in m[b'archives'].items())
        manifest.timestamp = m.get(b'timestamp')
        if manifest.timestamp:
            manifest.timestamp = manifest.timestamp.decode('ascii')
        manifest.config = m[b'config']
        return manifest, key

    def write(self):
        self.timestamp = datetime.utcnow().isoformat()
        data = msgpack.packb(StableDict({
            'version': 1,
            'archives': self.archives,
            'timestamp': self.timestamp,
            'config': self.config,
        }))
        self.id = self.key.id_hash(data)
        self.repository.put(self.MANIFEST_ID, self.key.encrypt(data))


def prune_within(archives, within):
    multiplier = {'H': 1, 'd': 24, 'w': 24*7, 'm': 24*31, 'y': 24*365}
    try:
        hours = int(within[:-1]) * multiplier[within[-1]]
    except (KeyError, ValueError):
        # I don't like how this displays the original exception too:
        raise argparse.ArgumentTypeError('Unable to parse --within option: "%s"' % within)
    if hours <= 0:
        raise argparse.ArgumentTypeError('Number specified using --within option must be positive')
    target = datetime.now(timezone.utc) - timedelta(seconds=hours*60*60)
    return [a for a in archives if a.ts > target]


def prune_split(archives, pattern, n, skip=[]):
    last = None
    keep = []
    if n == 0:
        return keep
    for a in sorted(archives, key=attrgetter('ts'), reverse=True):
        period = to_localtime(a.ts).strftime(pattern)
        if period != last:
            last = period
            if a not in skip:
                keep.append(a)
                if len(keep) == n: break
    return keep


class Statistics:

    def __init__(self):
        self.osize = self.csize = self.usize = self.nfiles = 0

    def update(self, size, csize, unique):
        self.osize += size
        self.csize += csize
        if unique:
            self.usize += csize

    def print_(self, label, cache):
        total_size, total_csize, unique_size, unique_csize = cache.chunks.summarize()
        print()
        print('                       Original size      Compressed size    Deduplicated size')
        print('%-15s %20s %20s %20s' % (label, format_file_size(self.osize), format_file_size(self.csize), format_file_size(self.usize)))
        print('All archives:   %20s %20s %20s' % (format_file_size(total_size), format_file_size(total_csize), format_file_size(unique_csize)))


def get_keys_dir():
    """Determine where to repository keys and cache"""
    return os.environ.get('ATTIC_KEYS_DIR',
                          os.path.join(os.path.expanduser('~'), '.attic', 'keys'))


def get_cache_dir():
    """Determine where to repository keys and cache"""
    return os.environ.get('ATTIC_CACHE_DIR',
                          os.path.join(os.path.expanduser('~'), '.cache', 'attic'))


def to_localtime(ts):
    """Convert datetime object from UTC to local time zone"""
    return datetime(*time.localtime((ts - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds())[:6])


def update_excludes(args):
    """Merge exclude patterns from files with those on command line.
    Empty lines and lines starting with '#' are ignored, but whitespace
    is not stripped."""
    if hasattr(args, 'exclude_files') and args.exclude_files:
        if not hasattr(args, 'excludes') or args.excludes is None:
            args.excludes = []
        for file in args.exclude_files:
            patterns = [line.rstrip('\r\n') for line in file if not line.startswith('#')]
            args.excludes += [ExcludePattern(pattern) for pattern in patterns if pattern]
            file.close()


def adjust_patterns(paths, excludes):
    if paths:
        return (excludes or []) + [IncludePattern(path) for path in paths] + [ExcludePattern('*')]
    else:
        return excludes


def exclude_path(path, patterns):
    """Used by create and extract sub-commands to determine
    whether or not an item should be processed.
    """
    for pattern in (patterns or []):
        if pattern.match(path):
            return isinstance(pattern, ExcludePattern)
    return False


# For both IncludePattern and ExcludePattern, we require that
# the pattern either match the whole path or an initial segment
# of the path up to but not including a path separator.  To
# unify the two cases, we add a path separator to the end of
# the path before matching.

class IncludePattern:
    """Literal files or directories listed on the command line
    for some operations (e.g. extract, but not create).
    If a directory is specified, all paths that start with that
    path match as well.  A trailing slash makes no difference.
    """
    def __init__(self, pattern):
        self.pattern = pattern.rstrip(os.path.sep)+os.path.sep

    def match(self, path):
        return (path+os.path.sep).startswith(self.pattern)

    def __repr__(self):
        return '%s(%s)' % (type(self), self.pattern)


class ExcludePattern(IncludePattern):
    """Shell glob patterns to exclude.  A trailing slash means to
    exclude the contents of a directory, but not the directory itself.
    """
    def __init__(self, pattern):
        if pattern.endswith(os.path.sep):
            self.pattern = pattern+'*'+os.path.sep
        else:
            self.pattern = pattern+os.path.sep+'*'
        # fnmatch and re.match both cache compiled regular expressions.
        # Nevertheless, this is about 10 times faster.
        self.regex = re.compile(translate(self.pattern))

    def match(self, path):
        return self.regex.match(path+os.path.sep) is not None

    def __repr__(self):
        return '%s(%s)' % (type(self), self.pattern)


def is_cachedir(path):
    """Determines whether the specified path is a cache directory (and
    therefore should potentially be excluded from the backup) according to
    the CACHEDIR.TAG protocol
    (http://www.brynosaurus.com/cachedir/spec.html).
    """

    tag_contents = b'Signature: 8a477f597d28d172789f06886806bc55'
    tag_path = os.path.join(path, 'CACHEDIR.TAG')
    try:
        if os.path.exists(tag_path):
            with open(tag_path, 'rb') as tag_file:
                tag_data = tag_file.read(len(tag_contents))
                if tag_data == tag_contents:
                    return True
    except OSError:
        pass
    return False


def walk_path(path, skip_inodes=None):
    st = os.lstat(path)
    if skip_inodes and (st.st_ino, st.st_dev) in skip_inodes:
        return
    yield path, st
    if stat.S_ISDIR(st.st_mode):
        for f in os.listdir(path):
            for x in walk_path(os.path.join(path, f), skip_inodes):
                yield x


def format_time(t):
    """Format datetime suitable for fixed length list output
    """
    if abs((datetime.now() - t).days) < 365:
        return t.strftime('%b %d %H:%M')
    else:
        return t.strftime('%b %d  %Y')


def format_timedelta(td):
    """Format timedelta in a human friendly format
    """
    # Since td.total_seconds() requires python 2.7
    ts = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)
    s = ts % 60
    m = int(ts / 60) % 60
    h = int(ts / 3600) % 24
    txt = '%.2f seconds' % s
    if m:
        txt = '%d minutes %s' % (m, txt)
    if h:
        txt = '%d hours %s' % (h, txt)
    if td.days:
        txt = '%d days %s' % (td.days, txt)
    return txt


def format_file_mode(mod):
    """Format file mode bits for list output
    """
    def x(v):
        return ''.join(v & m and s or '-'
                       for m, s in ((4, 'r'), (2, 'w'), (1, 'x')))
    return '%s%s%s' % (x(mod // 64), x(mod // 8), x(mod))


def format_file_size(v):
    """Format file size into a human friendly format
    """
    if abs(v) > 10**12:
        return '%.2f TB' % (v / 10**12)
    elif abs(v) > 10**9:
        return '%.2f GB' % (v / 10**9)
    elif abs(v) > 10**6:
        return '%.2f MB' % (v / 10**6)
    elif abs(v) > 10**3:
        return '%.2f kB' % (v / 10**3)
    else:
        return '%d B' % v


def format_archive(archive):
    return '%-36s %s' % (archive.name, to_localtime(archive.ts).strftime('%c'))


class IntegrityError(Error):
    """Data integrity error"""


def memoize(function):
    cache = {}

    def decorated_function(*args):
        try:
            return cache[args]
        except KeyError:
            val = function(*args)
            cache[args] = val
            return val
    return decorated_function


@memoize
def uid2user(uid, default=None):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return default


@memoize
def user2uid(user, default=None):
    try:
        return user and pwd.getpwnam(user).pw_uid
    except KeyError:
        return default


@memoize
def gid2group(gid, default=None):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return default


@memoize
def group2gid(group, default=None):
    try:
        return group and grp.getgrnam(group).gr_gid
    except KeyError:
        return default


def posix_acl_use_stored_uid_gid(acl):
    """Replace the user/group field with the stored uid/gid
    """
    entries = []
    for entry in acl.decode('ascii').split('\n'):
        if entry:
            fields = entry.split(':')
            if len(fields) == 4:
                entries.append(':'.join([fields[0], fields[3], fields[2]]))
            else:
                entries.append(entry)
    return ('\n'.join(entries)).encode('ascii')


class Location:
    """Object representing a repository / archive location
    """
    proto = user = host = port = path = archive = None
    ssh_re = re.compile(r'(?P<proto>ssh)://(?:(?P<user>[^@]+)@)?'
                        r'(?P<host>[^:/#]+)(?::(?P<port>\d+))?'
                        r'(?P<path>[^:]+)(?:::(?P<archive>.+))?')
    file_re = re.compile(r'(?P<proto>file)://'
                         r'(?P<path>[^:]+)(?:::(?P<archive>.+))?')
    scp_re = re.compile(r'((?:(?P<user>[^@]+)@)?(?P<host>[^:/]+):)?'
                        r'(?P<path>[^:]+)(?:::(?P<archive>.+))?')

    def __init__(self, text):
        self.orig = text
        if not self.parse(text):
            raise ValueError

    def parse(self, text):
        m = self.ssh_re.match(text)
        if m:
            self.proto = m.group('proto')
            self.user = m.group('user')
            self.host = m.group('host')
            self.port = m.group('port') and int(m.group('port')) or None
            self.path = m.group('path')
            self.archive = m.group('archive')
            return True
        m = self.file_re.match(text)
        if m:
            self.proto = m.group('proto')
            self.path = m.group('path')
            self.archive = m.group('archive')
            return True
        m = self.scp_re.match(text)
        if m:
            self.user = m.group('user')
            self.host = m.group('host')
            self.path = m.group('path')
            self.archive = m.group('archive')
            self.proto = self.host and 'ssh' or 'file'
            return True
        return False

    def __str__(self):
        items = []
        items.append('proto=%r' % self.proto)
        items.append('user=%r' % self.user)
        items.append('host=%r' % self.host)
        items.append('port=%r' % self.port)
        items.append('path=%r' % self.path)
        items.append('archive=%r' % self.archive)
        return ', '.join(items)

    def to_key_filename(self):
        name = re.sub('[^\w]', '_', self.path).strip('_')
        if self.proto != 'file':
            name = self.host + '__' + name
        return os.path.join(get_keys_dir(), name)

    def __repr__(self):
        return "Location(%s)" % self


def location_validator(archive=None):
    def validator(text):
        try:
            loc = Location(text)
        except ValueError:
            raise argparse.ArgumentTypeError('Invalid location format: "%s"' % text)
        if archive is True and not loc.archive:
            raise argparse.ArgumentTypeError('"%s": No archive specified' % text)
        elif archive is False and loc.archive:
            raise argparse.ArgumentTypeError('"%s" No archive can be specified' % text)
        return loc
    return validator


def read_msgpack(filename):
    with open(filename, 'rb') as fd:
        return msgpack.unpack(fd)


def write_msgpack(filename, d):
    with open(filename + '.tmp', 'wb') as fd:
        msgpack.pack(d, fd)
        fd.flush()
        os.fsync(fd)
    os.rename(filename + '.tmp', filename)


def decode_dict(d, keys, encoding='utf-8', errors='surrogateescape'):
    for key in keys:
        if isinstance(d.get(key), bytes):
            d[key] = d[key].decode(encoding, errors)
    return d


def remove_surrogates(s, errors='replace'):
    """Replace surrogates generated by fsdecode with '?'
    """
    return s.encode('utf-8', errors).decode('utf-8')


_safe_re = re.compile('^((..)?/+)+')


def make_path_safe(path):
    """Make path safe by making it relative and local
    """
    return _safe_re.sub('', path) or '.'


def daemonize():
    """Detach process from controlling terminal and run in background
    """
    pid = os.fork()
    if pid:
        os._exit(0)
    os.setsid()
    pid = os.fork()
    if pid:
        os._exit(0)
    os.chdir('/')
    os.close(0)
    os.close(1)
    os.close(2)
    fd = os.open('/dev/null', os.O_RDWR)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)


class StableDict(dict):
    """A dict subclass with stable items() ordering"""
    def items(self):
        return sorted(super(StableDict, self).items())


if sys.version < '3.3':
    # st_mtime_ns attribute only available in 3.3+
    def st_mtime_ns(st):
        return int(st.st_mtime * 1e9)

    # unhexlify in < 3.3 incorrectly only accepts bytes input
    def unhexlify(data):
        if isinstance(data, str):
            data = data.encode('ascii')
        return binascii.unhexlify(data)
else:
    def st_mtime_ns(st):
        return st.st_mtime_ns

    unhexlify = binascii.unhexlify


def bigint_to_int(mtime):
    """Convert bytearray to int
    """
    if isinstance(mtime, bytes):
        return int.from_bytes(mtime, 'little', signed=True)
    return mtime


def int_to_bigint(value):
    """Convert integers larger than 64 bits to bytearray

    Smaller integers are left alone
    """
    if value.bit_length() > 63:
        return value.to_bytes((value.bit_length() + 9) // 8, 'little', signed=True)
    return value

########NEW FILE########
__FILENAME__ = key
from binascii import hexlify, a2b_base64, b2a_base64
from getpass import getpass
import os
import msgpack
import textwrap
import hmac
from hashlib import sha256
import zlib

from attic.crypto import pbkdf2_sha256, get_random_bytes, AES, bytes_to_long, long_to_bytes, bytes_to_int, num_aes_blocks
from attic.helpers import IntegrityError, get_keys_dir

PREFIX = b'\0' * 8


class HMAC(hmac.HMAC):
    """Workaround a bug in Python < 3.4 Where HMAC does not accept memoryviews
    """
    def update(self, msg):
        self.inner.update(msg)


def key_creator(repository, args):
    if args.encryption == 'keyfile':
        return KeyfileKey.create(repository, args)
    elif args.encryption == 'passphrase':
        return PassphraseKey.create(repository, args)
    else:
        return PlaintextKey.create(repository, args)


def key_factory(repository, manifest_data):
    if manifest_data[0] == KeyfileKey.TYPE:
        return KeyfileKey.detect(repository, manifest_data)
    elif manifest_data[0] == PassphraseKey.TYPE:
        return PassphraseKey.detect(repository, manifest_data)
    elif manifest_data[0] == PlaintextKey.TYPE:
        return PlaintextKey.detect(repository, manifest_data)
    else:
        raise Exception('Unkown Key type %d' % ord(manifest_data[0]))


class KeyBase(object):

    def __init__(self):
        self.TYPE_STR = bytes([self.TYPE])

    def id_hash(self, data):
        """Return HMAC hash using the "id" HMAC key
        """

    def encrypt(self, data):
        pass

    def decrypt(self, id, data):
        pass


class PlaintextKey(KeyBase):
    TYPE = 0x02

    chunk_seed = 0

    @classmethod
    def create(cls, repository, args):
        print('Encryption NOT enabled.\nUse the "--encryption=passphrase|keyfile" to enable encryption.')
        return cls()

    @classmethod
    def detect(cls, repository, manifest_data):
        return cls()

    def id_hash(self, data):
        return sha256(data).digest()

    def encrypt(self, data):
        return b''.join([self.TYPE_STR, zlib.compress(data)])

    def decrypt(self, id, data):
        if data[0] != self.TYPE:
            raise IntegrityError('Invalid encryption envelope')
        data = zlib.decompress(memoryview(data)[1:])
        if id and sha256(data).digest() != id:
            raise IntegrityError('Chunk id verification failed')
        return data


class AESKeyBase(KeyBase):
    """Common base class shared by KeyfileKey and PassphraseKey

    Chunks are encrypted using 256bit AES in Counter Mode (CTR)

    Payload layout: TYPE(1) + HMAC(32) + NONCE(8) + CIPHERTEXT

    To reduce payload size only 8 bytes of the 16 bytes nonce is saved
    in the payload, the first 8 bytes are always zeros. This does not
    affect security but limits the maximum repository capacity to
    only 295 exabytes!
    """

    PAYLOAD_OVERHEAD = 1 + 32 + 8  # TYPE + HMAC + NONCE

    def id_hash(self, data):
        """Return HMAC hash using the "id" HMAC key
        """
        return HMAC(self.id_key, data, sha256).digest()

    def encrypt(self, data):
        data = zlib.compress(data)
        self.enc_cipher.reset()
        data = b''.join((self.enc_cipher.iv[8:], self.enc_cipher.encrypt(data)))
        hmac = HMAC(self.enc_hmac_key, data, sha256).digest()
        return b''.join((self.TYPE_STR, hmac, data))

    def decrypt(self, id, data):
        if data[0] != self.TYPE:
            raise IntegrityError('Invalid encryption envelope')
        hmac = memoryview(data)[1:33]
        if memoryview(HMAC(self.enc_hmac_key, memoryview(data)[33:], sha256).digest()) != hmac:
            raise IntegrityError('Encryption envelope checksum mismatch')
        self.dec_cipher.reset(iv=PREFIX + data[33:41])
        data = zlib.decompress(self.dec_cipher.decrypt(data[41:]))  # should use memoryview
        if id and HMAC(self.id_key, data, sha256).digest() != id:
            raise IntegrityError('Chunk id verification failed')
        return data

    def extract_nonce(self, payload):
        if payload[0] != self.TYPE:
            raise IntegrityError('Invalid encryption envelope')
        nonce = bytes_to_long(payload[33:41])
        return nonce

    def init_from_random_data(self, data):
        self.enc_key = data[0:32]
        self.enc_hmac_key = data[32:64]
        self.id_key = data[64:96]
        self.chunk_seed = bytes_to_int(data[96:100])
        # Convert to signed int32
        if self.chunk_seed & 0x80000000:
            self.chunk_seed = self.chunk_seed - 0xffffffff - 1

    def init_ciphers(self, enc_iv=b''):
        self.enc_cipher = AES(self.enc_key, enc_iv)
        self.dec_cipher = AES(self.enc_key)


class PassphraseKey(AESKeyBase):
    TYPE = 0x01
    iterations = 100000

    @classmethod
    def create(cls, repository, args):
        key = cls()
        passphrase = os.environ.get('ATTIC_PASSPHRASE')
        if passphrase is not None:
            passphrase2 = passphrase
        else:
            passphrase, passphrase2 = 1, 2
        while passphrase != passphrase2:
            passphrase = getpass('Enter passphrase: ')
            if not passphrase:
                print('Passphrase must not be blank')
                continue
            passphrase2 = getpass('Enter same passphrase again: ')
            if passphrase != passphrase2:
                print('Passphrases do not match')
        key.init(repository, passphrase)
        if passphrase:
            print('Remember your passphrase. Your data will be inaccessible without it.')
        return key

    @classmethod
    def detect(cls, repository, manifest_data):
        prompt = 'Enter passphrase for %s: ' % repository._location.orig
        key = cls()
        passphrase = os.environ.get('ATTIC_PASSPHRASE')
        if passphrase is None:
            passphrase = getpass(prompt)
        while True:
            key.init(repository, passphrase)
            try:
                key.decrypt(None, manifest_data)
                num_blocks = num_aes_blocks(len(manifest_data) - 41)
                key.init_ciphers(PREFIX + long_to_bytes(key.extract_nonce(manifest_data) + num_blocks))
                return key
            except IntegrityError:
                passphrase = getpass(prompt)

    def init(self, repository, passphrase):
        self.init_from_random_data(pbkdf2_sha256(passphrase.encode('utf-8'), repository.id, self.iterations, 100))
        self.init_ciphers()


class KeyfileKey(AESKeyBase):
    FILE_ID = 'ATTIC KEY'
    TYPE = 0x00

    @classmethod
    def detect(cls, repository, manifest_data):
        key = cls()
        path = cls.find_key_file(repository)
        prompt = 'Enter passphrase for key file %s: ' % path
        passphrase = os.environ.get('ATTIC_PASSPHRASE', '')
        while not key.load(path, passphrase):
            passphrase = getpass(prompt)
        num_blocks = num_aes_blocks(len(manifest_data) - 41)
        key.init_ciphers(PREFIX + long_to_bytes(key.extract_nonce(manifest_data) + num_blocks))
        return key

    @classmethod
    def find_key_file(cls, repository):
        id = hexlify(repository.id).decode('ascii')
        keys_dir = get_keys_dir()
        for name in os.listdir(keys_dir):
            filename = os.path.join(keys_dir, name)
            with open(filename, 'r') as fd:
                line = fd.readline().strip()
                if line and line.startswith(cls.FILE_ID) and line[10:] == id:
                    return filename
        raise Exception('Key file for repository with ID %s not found' % id)

    def load(self, filename, passphrase):
        with open(filename, 'r') as fd:
            cdata = a2b_base64(''.join(fd.readlines()[1:]).encode('ascii'))  # .encode needed for Python 3.[0-2]
        data = self.decrypt_key_file(cdata, passphrase)
        if data:
            key = msgpack.unpackb(data)
            if key[b'version'] != 1:
                raise IntegrityError('Invalid key file header')
            self.repository_id = key[b'repository_id']
            self.enc_key = key[b'enc_key']
            self.enc_hmac_key = key[b'enc_hmac_key']
            self.id_key = key[b'id_key']
            self.chunk_seed = key[b'chunk_seed']
            self.path = filename
            return True

    def decrypt_key_file(self, data, passphrase):
        d = msgpack.unpackb(data)
        assert d[b'version'] == 1
        assert d[b'algorithm'] == b'sha256'
        key = pbkdf2_sha256(passphrase.encode('utf-8'), d[b'salt'], d[b'iterations'], 32)
        data = AES(key).decrypt(d[b'data'])
        if HMAC(key, data, sha256).digest() != d[b'hash']:
            return None
        return data

    def encrypt_key_file(self, data, passphrase):
        salt = get_random_bytes(32)
        iterations = 100000
        key = pbkdf2_sha256(passphrase.encode('utf-8'), salt, iterations, 32)
        hash = HMAC(key, data, sha256).digest()
        cdata = AES(key).encrypt(data)
        d = {
            'version': 1,
            'salt': salt,
            'iterations': iterations,
            'algorithm': 'sha256',
            'hash': hash,
            'data': cdata,
        }
        return msgpack.packb(d)

    def save(self, path, passphrase):
        key = {
            'version': 1,
            'repository_id': self.repository_id,
            'enc_key': self.enc_key,
            'enc_hmac_key': self.enc_hmac_key,
            'id_key': self.id_key,
            'chunk_seed': self.chunk_seed,
        }
        data = self.encrypt_key_file(msgpack.packb(key), passphrase)
        with open(path, 'w') as fd:
            fd.write('%s %s\n' % (self.FILE_ID, hexlify(self.repository_id).decode('ascii')))
            fd.write('\n'.join(textwrap.wrap(b2a_base64(data).decode('ascii'))))
            fd.write('\n')
        self.path = path

    def change_passphrase(self):
        passphrase, passphrase2 = 1, 2
        while passphrase != passphrase2:
            passphrase = getpass('New passphrase: ')
            passphrase2 = getpass('Enter same passphrase again: ')
            if passphrase != passphrase2:
                print('Passphrases do not match')
        self.save(self.path, passphrase)
        print('Key file "%s" updated' % self.path)

    @classmethod
    def create(cls, repository, args):
        filename = args.repository.to_key_filename()
        path = filename
        i = 1
        while os.path.exists(path):
            i += 1
            path = filename + '.%d' % i
        passphrase = os.environ.get('ATTIC_PASSPHRASE')
        if passphrase is not None:
            passphrase2 = passphrase
        else:
            passphrase, passphrase2 = 1, 2
        while passphrase != passphrase2:
            passphrase = getpass('Enter passphrase (empty for no passphrase):')
            passphrase2 = getpass('Enter same passphrase again: ')
            if passphrase != passphrase2:
                print('Passphrases do not match')
        key = cls()
        key.repository_id = repository.id
        key.init_from_random_data(get_random_bytes(100))
        key.init_ciphers()
        key.save(path, passphrase)
        print('Key file "%s" created.' % key.path)
        print('Keep this file safe. Your data will be inaccessible without it.')
        return key

########NEW FILE########
__FILENAME__ = lrucache
class LRUCache(dict):

    def __init__(self, capacity):
        super(LRUCache, self).__init__()
        self._lru = []
        self._capacity = capacity

    def __setitem__(self, key, value):
        try:
            self._lru.remove(key)
        except ValueError:
            pass
        self._lru.append(key)
        while len(self._lru) > self._capacity:
            del self[self._lru[0]]
        return super(LRUCache, self).__setitem__(key, value)

    def __getitem__(self, key):
        try:
            self._lru.remove(key)
            self._lru.append(key)
        except ValueError:
            pass
        return super(LRUCache, self).__getitem__(key)

    def __delitem__(self, key):
        try:
            self._lru.remove(key)
        except ValueError:
            pass
        return super(LRUCache, self).__delitem__(key)

    def pop(self, key, default=None):
        try:
            self._lru.remove(key)
        except ValueError:
            pass
        return super(LRUCache, self).pop(key, default)

    def _not_implemented(self, *args, **kw):
        raise NotImplementedError
    popitem = setdefault = update = _not_implemented

########NEW FILE########
__FILENAME__ = platform
import os

platform = os.uname()[0]

if platform == 'Linux':
    from attic.platform_linux import acl_get, acl_set, API_VERSION
elif platform == 'FreeBSD':
    from attic.platform_freebsd import acl_get, acl_set, API_VERSION
elif platform == 'Darwin':
    from attic.platform_darwin import acl_get, acl_set, API_VERSION
else:
    API_VERSION = 1

    def acl_get(path, item, numeric_owner=False):
        pass
    def acl_set(path, item, numeric_owner=False):
        pass

########NEW FILE########
__FILENAME__ = remote
import fcntl
import msgpack
import os
import select
import shutil
from subprocess import Popen, PIPE
import sys
import tempfile

from .hashindex import NSIndex
from .helpers import Error, IntegrityError
from .repository import Repository

BUFSIZE = 10 * 1024 * 1024


class ConnectionClosed(Error):
    """Connection closed by remote host"""


class PathNotAllowed(Error):
    """Repository path not allowed"""


class RepositoryServer(object):

    def __init__(self, restrict_to_paths):
        self.repository = None
        self.restrict_to_paths = restrict_to_paths

    def serve(self):
        # Make stdin non-blocking
        fl = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)
        # Make stdout blocking
        fl = fcntl.fcntl(sys.stdout.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(sys.stdout.fileno(), fcntl.F_SETFL, fl & ~os.O_NONBLOCK)
        unpacker = msgpack.Unpacker(use_list=False)
        while True:
            r, w, es = select.select([sys.stdin], [], [], 10)
            if r:
                data = os.read(sys.stdin.fileno(), BUFSIZE)
                if not data:
                    return
                unpacker.feed(data)
                for type, msgid, method, args in unpacker:
                    method = method.decode('ascii')
                    try:
                        try:
                            f = getattr(self, method)
                        except AttributeError:
                            f = getattr(self.repository, method)
                        res = f(*args)
                    except Exception as e:
                        sys.stdout.buffer.write(msgpack.packb((1, msgid, e.__class__.__name__, e.args)))
                    else:
                        sys.stdout.buffer.write(msgpack.packb((1, msgid, None, res)))
                    sys.stdout.flush()
            if es:
                return

    def negotiate(self, versions):
        return 1

    def open(self, path, create=False):
        path = os.fsdecode(path)
        if path.startswith('/~'):
            path = path[1:]
        path = os.path.realpath(os.path.expanduser(path))
        if self.restrict_to_paths:
            for restrict_to_path in self.restrict_to_paths:
                if path.startswith(os.path.realpath(restrict_to_path)):
                    break
            else:
                raise PathNotAllowed(path)
        self.repository = Repository(path, create)
        return self.repository.id


class RemoteRepository(object):
    extra_test_args = []

    class RPCError(Exception):

        def __init__(self, name):
            self.name = name

    def __init__(self, location, create=False):
        self.location = location
        self.preload_ids = []
        self.msgid = 0
        self.to_send = b''
        self.cache = {}
        self.ignore_responses = set()
        self.responses = {}
        self.unpacker = msgpack.Unpacker(use_list=False)
        self.p = None
        if location.host == '__testsuite__':
            args = [sys.executable, '-m', 'attic.archiver', 'serve'] + self.extra_test_args
        else:
            args = ['ssh']
            if location.port:
                args += ['-p', str(location.port)]
            if location.user:
                args.append('%s@%s' % (location.user, location.host))
            else:
                args.append('%s' % location.host)
            args += ['attic', 'serve']
        self.p = Popen(args, bufsize=0, stdin=PIPE, stdout=PIPE)
        self.stdin_fd = self.p.stdin.fileno()
        self.stdout_fd = self.p.stdout.fileno()
        fcntl.fcntl(self.stdin_fd, fcntl.F_SETFL, fcntl.fcntl(self.stdin_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(self.stdout_fd, fcntl.F_SETFL, fcntl.fcntl(self.stdout_fd, fcntl.F_GETFL) | os.O_NONBLOCK)
        self.r_fds = [self.stdout_fd]
        self.x_fds = [self.stdin_fd, self.stdout_fd]

        version = self.call('negotiate', 1)
        if version != 1:
            raise Exception('Server insisted on using unsupported protocol version %d' % version)
        self.id = self.call('open', location.path, create)

    def __del__(self):
        self.close()

    def call(self, cmd, *args, **kw):
        for resp in self.call_many(cmd, [args], **kw):
            return resp

    def call_many(self, cmd, calls, wait=True, is_preloaded=False):
        if not calls:
            return
        def fetch_from_cache(args):
            msgid = self.cache[args].pop(0)
            if not self.cache[args]:
                del self.cache[args]
            return msgid

        calls = list(calls)
        waiting_for = []
        w_fds = [self.stdin_fd]
        while wait or calls:
            while waiting_for:
                try:
                    error, res = self.responses.pop(waiting_for[0])
                    waiting_for.pop(0)
                    if error:
                        if error == b'DoesNotExist':
                            raise Repository.DoesNotExist(self.location.orig)
                        elif error == b'AlreadyExists':
                            raise Repository.AlreadyExists(self.location.orig)
                        elif error == b'CheckNeeded':
                            raise Repository.CheckNeeded(self.location.orig)
                        elif error == b'IntegrityError':
                            raise IntegrityError(res)
                        elif error == b'PathNotAllowed':
                            raise PathNotAllowed(*res)
                        raise self.RPCError(error)
                    else:
                        yield res
                        if not waiting_for and not calls:
                            return
                except KeyError:
                    break
            r, w, x = select.select(self.r_fds, w_fds, self.x_fds, 1)
            if x:
                raise Exception('FD exception occured')
            if r:
                data = os.read(self.stdout_fd, BUFSIZE)
                if not data:
                    raise ConnectionClosed()
                self.unpacker.feed(data)
                for type, msgid, error, res in self.unpacker:
                    if msgid in self.ignore_responses:
                        self.ignore_responses.remove(msgid)
                    else:
                        self.responses[msgid] = error, res
            if w:
                while not self.to_send and (calls or self.preload_ids) and len(waiting_for) < 100:
                    if calls:
                        if is_preloaded:
                            if calls[0] in self.cache:
                                waiting_for.append(fetch_from_cache(calls.pop(0)))
                        else:
                            args = calls.pop(0)
                            if cmd == 'get' and args in self.cache:
                                waiting_for.append(fetch_from_cache(args))
                            else:
                                self.msgid += 1
                                waiting_for.append(self.msgid)
                                self.to_send = msgpack.packb((1, self.msgid, cmd, args))
                    if not self.to_send and self.preload_ids:
                        args = (self.preload_ids.pop(0),)
                        self.msgid += 1
                        self.cache.setdefault(args, []).append(self.msgid)
                        self.to_send = msgpack.packb((1, self.msgid, cmd, args))

                if self.to_send:
                    self.to_send = self.to_send[os.write(self.stdin_fd, self.to_send):]
                if not self.to_send and not (calls or self.preload_ids):
                    w_fds = []
        self.ignore_responses |= set(waiting_for)

    def check(self, repair=False):
        return self.call('check', repair)

    def commit(self, *args):
        return self.call('commit')

    def rollback(self, *args):
        return self.call('rollback')

    def __len__(self):
        return self.call('__len__')

    def list(self, limit=None, marker=None):
        return self.call('list', limit, marker)

    def get(self, id_):
        for resp in self.get_many([id_]):
            return resp

    def get_many(self, ids, is_preloaded=False):
        for resp in self.call_many('get', [(id_,) for id_ in ids], is_preloaded=is_preloaded):
            yield resp

    def put(self, id_, data, wait=True):
        return self.call('put', id_, data, wait=wait)

    def delete(self, id_, wait=True):
        return self.call('delete', id_, wait=wait)

    def close(self):
        if self.p:
            self.p.stdin.close()
            self.p.stdout.close()
            self.p.wait()
            self.p = None

    def preload(self, ids):
        self.preload_ids += ids


class RepositoryCache:
    """A caching Repository wrapper

    Caches Repository GET operations using a temporary file
    """
    def __init__(self, repository):
        self.tmppath = None
        self.index = None
        self.data_fd = None
        self.repository = repository
        self.entries = {}
        self.initialize()

    def __del__(self):
        self.cleanup()

    def initialize(self):
        self.tmppath = tempfile.mkdtemp()
        self.index = NSIndex.create(os.path.join(self.tmppath, 'index'))
        self.data_fd = open(os.path.join(self.tmppath, 'data'), 'a+b')

    def cleanup(self):
        del self.index
        if self.data_fd:
            self.data_fd.close()
        if self.tmppath:
            shutil.rmtree(self.tmppath)

    def load_object(self, offset, size):
        self.data_fd.seek(offset)
        data = self.data_fd.read(size)
        assert len(data) == size
        return data

    def store_object(self, key, data):
        self.data_fd.seek(0, os.SEEK_END)
        self.data_fd.write(data)
        offset = self.data_fd.tell()
        self.index[key] = offset - len(data), len(data)

    def get(self, key):
        return next(self.get_many([key]))

    def get_many(self, keys):
        unknown_keys = [key for key in keys if not key in self.index]
        repository_iterator = zip(unknown_keys, self.repository.get_many(unknown_keys))
        for key in keys:
            try:
                yield self.load_object(*self.index[key])
            except KeyError:
                for key_, data in repository_iterator:
                    if key_ == key:
                        self.store_object(key, data)
                        yield data
                        break
        # Consume any pending requests
        for _ in repository_iterator:
            pass


def cache_if_remote(repository):
    if isinstance(repository, RemoteRepository):
        return RepositoryCache(repository)
    return repository
########NEW FILE########
__FILENAME__ = repository
from configparser import RawConfigParser
from binascii import hexlify
from itertools import islice
import errno
import os
import shutil
import struct
import sys
from zlib import crc32

from .hashindex import NSIndex
from .helpers import Error, IntegrityError, read_msgpack, write_msgpack, unhexlify, UpgradableLock
from .lrucache import LRUCache

MAX_OBJECT_SIZE = 20 * 1024 * 1024
MAGIC = b'ATTICSEG'
TAG_PUT = 0
TAG_DELETE = 1
TAG_COMMIT = 2


class Repository(object):
    """Filesystem based transactional key value store

    On disk layout:
    dir/README
    dir/config
    dir/data/<X / SEGMENTS_PER_DIR>/<X>
    dir/index.X
    dir/hints.X
    """
    DEFAULT_MAX_SEGMENT_SIZE = 5 * 1024 * 1024
    DEFAULT_SEGMENTS_PER_DIR = 10000

    class DoesNotExist(Error):
        """Repository {} does not exist"""

    class AlreadyExists(Error):
        """Repository {} already exists"""

    class InvalidRepository(Error):
        """{} is not a valid repository"""

    class CheckNeeded(Error):
        '''Inconsistency detected. Please run "attic check {}"'''

    def __init__(self, path, create=False):
        self.path = path
        self.io = None
        self.lock = None
        self.index = None
        self._active_txn = False
        if create:
            self.create(path)
        self.open(path)

    def __del__(self):
        self.close()

    def create(self, path):
        """Create a new empty repository at `path`
        """
        if os.path.exists(path) and (not os.path.isdir(path) or os.listdir(path)):
            raise self.AlreadyExists(path)
        if not os.path.exists(path):
            os.mkdir(path)
        with open(os.path.join(path, 'README'), 'w') as fd:
            fd.write('This is an Attic repository\n')
        os.mkdir(os.path.join(path, 'data'))
        config = RawConfigParser()
        config.add_section('repository')
        config.set('repository', 'version', '1')
        config.set('repository', 'segments_per_dir', self.DEFAULT_SEGMENTS_PER_DIR)
        config.set('repository', 'max_segment_size', self.DEFAULT_MAX_SEGMENT_SIZE)
        config.set('repository', 'id', hexlify(os.urandom(32)).decode('ascii'))
        with open(os.path.join(path, 'config'), 'w') as fd:
            config.write(fd)

    def get_index_transaction_id(self):
        indicies = sorted((int(name[6:]) for name in os.listdir(self.path) if name.startswith('index.') and name[6:].isdigit()))
        if indicies:
            return indicies[-1]
        else:
            return None

    def get_transaction_id(self):
        index_transaction_id = self.get_index_transaction_id()
        segments_transaction_id = self.io.get_segments_transaction_id()
        if index_transaction_id is not None and segments_transaction_id is None:
            raise self.CheckNeeded(self.path)
        # Attempt to automatically rebuild index if we crashed between commit
        # tag write and index save
        if index_transaction_id != segments_transaction_id:
            if index_transaction_id is not None and index_transaction_id > segments_transaction_id:
                replay_from = None
            else:
                replay_from = index_transaction_id
            self.replay_segments(replay_from, segments_transaction_id)
        return self.get_index_transaction_id()

    def open(self, path):
        self.path = path
        if not os.path.isdir(path):
            raise self.DoesNotExist(path)
        self.config = RawConfigParser()
        self.config.read(os.path.join(self.path, 'config'))
        if not 'repository' in self.config.sections() or self.config.getint('repository', 'version') != 1:
            raise self.InvalidRepository(path)
        self.lock = UpgradableLock(os.path.join(path, 'config'))
        self.max_segment_size = self.config.getint('repository', 'max_segment_size')
        self.segments_per_dir = self.config.getint('repository', 'segments_per_dir')
        self.id = unhexlify(self.config.get('repository', 'id').strip())
        self.io = LoggedIO(self.path, self.max_segment_size, self.segments_per_dir)

    def close(self):
        if self.lock:
            if self.io:
                self.io.close()
            self.io = None
            self.lock.release()
            self.lock = None

    def commit(self):
        """Commit transaction
        """
        self.io.write_commit()
        self.compact_segments()
        self.write_index()
        self.rollback()

    def get_read_only_index(self, transaction_id):
        if transaction_id is None:
            return {}
        return NSIndex((os.path.join(self.path, 'index.%d') % transaction_id).encode('utf-8'), readonly=True)

    def get_index(self, transaction_id, do_cleanup=True):
        self._active_txn = True
        self.lock.upgrade()
        if transaction_id is None:
            self.index = NSIndex.create(os.path.join(self.path, 'index.tmp').encode('utf-8'))
            self.segments = {}
            self.compact = set()
        else:
            if do_cleanup:
                self.io.cleanup(transaction_id)
            shutil.copy(os.path.join(self.path, 'index.%d' % transaction_id),
                        os.path.join(self.path, 'index.tmp'))
            self.index = NSIndex(os.path.join(self.path, 'index.tmp').encode('utf-8'))
            hints = read_msgpack(os.path.join(self.path, 'hints.%d' % transaction_id))
            if hints[b'version'] != 1:
                raise ValueError('Unknown hints file version: %d' % hints['version'])
            self.segments = hints[b'segments']
            self.compact = set(hints[b'compact'])

    def write_index(self):
        hints = {b'version': 1,
                 b'segments': self.segments,
                 b'compact': list(self.compact)}
        transaction_id = self.io.get_segments_transaction_id()
        write_msgpack(os.path.join(self.path, 'hints.%d' % transaction_id), hints)
        self.index.flush()
        os.rename(os.path.join(self.path, 'index.tmp'),
                  os.path.join(self.path, 'index.%d' % transaction_id))
        # Remove old indices
        current = '.%d' % transaction_id
        for name in os.listdir(self.path):
            if not name.startswith('index.') and not name.startswith('hints.'):
                continue
            if name.endswith(current):
                continue
            os.unlink(os.path.join(self.path, name))
        self.index = None

    def compact_segments(self):
        """Compact sparse segments by copying data into new segments
        """
        if not self.compact:
            return
        index_transaction_id = self.get_index_transaction_id()
        segments = self.segments
        for segment in sorted(self.compact):
            if self.io.segment_exists(segment):
                for tag, key, offset, data in self.io.iter_objects(segment, include_data=True):
                    if tag == TAG_PUT and self.index.get(key, (-1, -1)) == (segment, offset):
                        new_segment, offset = self.io.write_put(key, data)
                        self.index[key] = new_segment, offset
                        segments.setdefault(new_segment, 0)
                        segments[new_segment] += 1
                        segments[segment] -= 1
                    elif tag == TAG_DELETE:
                        if index_transaction_id is None or segment > index_transaction_id:
                            self.io.write_delete(key)
                assert segments[segment] == 0

        self.io.write_commit()
        for segment in sorted(self.compact):
            assert self.segments.pop(segment) == 0
            self.io.delete_segment(segment)
        self.compact = set()

    def replay_segments(self, index_transaction_id, segments_transaction_id):
        self.get_index(index_transaction_id, do_cleanup=False)
        for segment, filename in self.io.segment_iterator():
            if index_transaction_id is not None and segment <= index_transaction_id:
                continue
            if segment > segments_transaction_id:
                break
            self.segments[segment] = 0
            for tag, key, offset in self.io.iter_objects(segment):
                if tag == TAG_PUT:
                    try:
                        s, _ = self.index[key]
                        self.compact.add(s)
                        self.segments[s] -= 1
                    except KeyError:
                        pass
                    self.index[key] = segment, offset
                    self.segments[segment] += 1
                elif tag == TAG_DELETE:
                    try:
                        s, _ = self.index.pop(key)
                        self.segments[s] -= 1
                        self.compact.add(s)
                    except KeyError:
                        pass
                    self.compact.add(segment)
                elif tag == TAG_COMMIT:
                    continue
                else:
                    raise self.CheckNeeded(self.path)
            if self.segments[segment] == 0:
                self.compact.add(segment)
        self.write_index()
        self.rollback()

    def check(self, repair=False):
        """Check repository consistency

        This method verifies all segment checksums and makes sure
        the index is consistent with the data stored in the segments.
        """
        error_found = False
        def report_error(msg):
            nonlocal error_found
            error_found = True
            print(msg, file=sys.stderr)

        assert not self._active_txn
        try:
            transaction_id = self.get_transaction_id()
            current_index = self.get_read_only_index(transaction_id)
        except Exception:
            transaction_id = self.io.get_segments_transaction_id()
            current_index = None
        if transaction_id is None:
            transaction_id = self.get_index_transaction_id()
        if transaction_id is None:
            transaction_id = self.io.get_latest_segment()
        if repair:
            self.io.cleanup(transaction_id)
        segments_transaction_id = self.io.get_segments_transaction_id()
        self.get_index(None)
        for segment, filename in self.io.segment_iterator():
            if segment > transaction_id:
                continue
            try:
                objects = list(self.io.iter_objects(segment))
            except (IntegrityError, struct.error):
                report_error('Error reading segment {}'.format(segment))
                objects = []
                if repair:
                    self.io.recover_segment(segment, filename)
                    objects = list(self.io.iter_objects(segment))
            self.segments[segment] = 0
            for tag, key, offset in objects:
                if tag == TAG_PUT:
                    try:
                        s, _ = self.index[key]
                        self.compact.add(s)
                        self.segments[s] -= 1
                    except KeyError:
                        pass
                    self.index[key] = segment, offset
                    self.segments[segment] += 1
                elif tag == TAG_DELETE:
                    try:
                        s, _ = self.index.pop(key)
                        self.segments[s] -= 1
                        self.compact.add(s)
                    except KeyError:
                        pass
                    self.compact.add(segment)
                elif tag == TAG_COMMIT:
                    continue
                else:
                    report_error('Unexpected tag {} in segment {}'.format(tag, segment))
        # We might need to add a commit tag if no committed segment is found
        if repair and segments_transaction_id is None:
            report_error('Adding commit tag to segment {}'.format(transaction_id))
            self.io.segment = transaction_id + 1
            self.io.write_commit()
            self.io.close_segment()
        if current_index and not repair:
            if len(current_index) != len(self.index):
                report_error('Index object count mismatch. {} != {}'.format(len(current_index), len(self.index)))
            elif current_index:
                for key, value in self.index.iteritems():
                    if current_index.get(key, (-1, -1)) != value:
                        report_error('Index mismatch for key {}. {} != {}'.format(key, value, current_index.get(key, (-1, -1))))
        if repair:
            self.compact_segments()
            self.write_index()
        else:
            os.unlink(os.path.join(self.path, 'index.tmp'))
        self.rollback()
        return not error_found or repair

    def rollback(self):
        """
        """
        self.index = None
        self._active_txn = False

    def __len__(self):
        if not self.index:
            self.index = self.get_read_only_index(self.get_transaction_id())
        return len(self.index)

    def list(self, limit=None, marker=None):
        if not self.index:
            self.index = self.get_read_only_index(self.get_transaction_id())
        return [id_ for id_, _ in islice(self.index.iteritems(marker=marker), limit)]

    def get(self, id_):
        if not self.index:
            self.index = self.get_read_only_index(self.get_transaction_id())
        try:
            segment, offset = self.index[id_]
            return self.io.read(segment, offset, id_)
        except KeyError:
            raise self.DoesNotExist(self.path)

    def get_many(self, ids, is_preloaded=False):
        for id_ in ids:
            yield self.get(id_)

    def put(self, id, data, wait=True):
        if not self._active_txn:
            self.get_index(self.get_transaction_id())
        try:
            segment, _ = self.index[id]
            self.segments[segment] -= 1
            self.compact.add(segment)
            segment = self.io.write_delete(id)
            self.segments.setdefault(segment, 0)
            self.compact.add(segment)
        except KeyError:
            pass
        segment, offset = self.io.write_put(id, data)
        self.segments.setdefault(segment, 0)
        self.segments[segment] += 1
        self.index[id] = segment, offset

    def delete(self, id, wait=True):
        if not self._active_txn:
            self.get_index(self.get_transaction_id())
        try:
            segment, offset = self.index.pop(id)
        except KeyError:
            raise self.DoesNotExist(self.path)
        self.segments[segment] -= 1
        self.compact.add(segment)
        segment = self.io.write_delete(id)
        self.compact.add(segment)
        self.segments.setdefault(segment, 0)

    def preload(self, ids):
        """Preload objects (only applies to remote repositories
        """


class LoggedIO(object):

    header_fmt = struct.Struct('<IIB')
    assert header_fmt.size == 9
    put_header_fmt = struct.Struct('<IIB32s')
    assert put_header_fmt.size == 41
    header_no_crc_fmt = struct.Struct('<IB')
    assert header_no_crc_fmt.size == 5
    crc_fmt = struct.Struct('<I')
    assert crc_fmt.size == 4

    _commit = header_no_crc_fmt.pack(9, TAG_COMMIT)
    COMMIT = crc_fmt.pack(crc32(_commit)) + _commit

    def __init__(self, path, limit, segments_per_dir, capacity=90):
        self.path = path
        self.fds = LRUCache(capacity)
        self.segment = 0
        self.limit = limit
        self.segments_per_dir = segments_per_dir
        self.offset = 0
        self._write_fd = None

    def close(self):
        for segment in list(self.fds.keys()):
            self.fds.pop(segment).close()
        self.close_segment()
        self.fds = None  # Just to make sure we're disabled

    def segment_iterator(self, reverse=False):
        for dirpath, dirs, filenames in os.walk(os.path.join(self.path, 'data')):
            dirs.sort(key=int, reverse=reverse)
            filenames = sorted((filename for filename in filenames if filename.isdigit()), key=int, reverse=reverse)
            for filename in filenames:
                yield int(filename), os.path.join(dirpath, filename)


    def get_latest_segment(self):
        for segment, filename in self.segment_iterator(reverse=True):
            return segment
        return None

    def get_segments_transaction_id(self):
        """Verify that the transaction id is consistent with the index transaction id
        """
        for segment, filename in self.segment_iterator(reverse=True):
            if self.is_committed_segment(filename):
                return segment
        return None

    def cleanup(self, transaction_id):
        """Delete segment files left by aborted transactions
        """
        self.segment = transaction_id + 1
        for segment, filename in self.segment_iterator(reverse=True):
            if segment > transaction_id:
                os.unlink(filename)
            else:
                break

    def is_committed_segment(self, filename):
        """Check if segment ends with a COMMIT_TAG tag
        """
        with open(filename, 'rb') as fd:
            try:
                fd.seek(-self.header_fmt.size, os.SEEK_END)
            except Exception as e:
                # return False if segment file is empty or too small
                if e.errno == errno.EINVAL:
                    return False
                raise e
            return fd.read(self.header_fmt.size) == self.COMMIT

    def segment_filename(self, segment):
        return os.path.join(self.path, 'data', str(segment // self.segments_per_dir), str(segment))

    def get_write_fd(self, no_new=False):
        if not no_new and self.offset and self.offset > self.limit:
            self.close_segment()
        if not self._write_fd:
            if self.segment % self.segments_per_dir == 0:
                dirname = os.path.join(self.path, 'data', str(self.segment // self.segments_per_dir))
                if not os.path.exists(dirname):
                    os.mkdir(dirname)
            self._write_fd = open(self.segment_filename(self.segment), 'ab')
            self._write_fd.write(MAGIC)
            self.offset = 8
        return self._write_fd

    def get_fd(self, segment):
        try:
            return self.fds[segment]
        except KeyError:
            fd = open(self.segment_filename(segment), 'rb')
            self.fds[segment] = fd
            return fd

    def delete_segment(self, segment):
        try:
            os.unlink(self.segment_filename(segment))
        except OSError:
            pass

    def segment_exists(self, segment):
        return os.path.exists(self.segment_filename(segment))

    def iter_objects(self, segment, include_data=False):
        fd = self.get_fd(segment)
        fd.seek(0)
        if fd.read(8) != MAGIC:
            raise IntegrityError('Invalid segment header')
        offset = 8
        header = fd.read(self.header_fmt.size)
        while header:
            crc, size, tag = self.header_fmt.unpack(header)
            if size > MAX_OBJECT_SIZE:
                raise IntegrityError('Invalid segment object size')
            rest = fd.read(size - self.header_fmt.size)
            if crc32(rest, crc32(memoryview(header)[4:])) & 0xffffffff != crc:
                raise IntegrityError('Segment checksum mismatch')
            if tag not in (TAG_PUT, TAG_DELETE, TAG_COMMIT):
                raise IntegrityError('Invalid segment entry header')
            key = None
            if tag in (TAG_PUT, TAG_DELETE):
                key = rest[:32]
            if include_data:
                yield tag, key, offset, rest[32:]
            else:
                yield tag, key, offset
            offset += size
            header = fd.read(self.header_fmt.size)

    def recover_segment(self, segment, filename):
        self.fds.pop(segment).close()
        # FIXME: save a copy of the original file
        with open(filename, 'rb') as fd:
            data = memoryview(fd.read())
        os.rename(filename, filename + '.beforerecover')
        print('attempting to recover ' + filename, file=sys.stderr)
        with open(filename, 'wb') as fd:
            fd.write(MAGIC)
            while len(data) >= self.header_fmt.size:
                crc, size, tag = self.header_fmt.unpack(data[:self.header_fmt.size])
                if size < self.header_fmt.size or size > len(data):
                    data = data[1:]
                    continue
                if crc32(data[4:size]) & 0xffffffff != crc:
                    data = data[1:]
                    continue
                fd.write(data[:size])
                data = data[size:]

    def read(self, segment, offset, id):
        if segment == self.segment and self._write_fd:
            self._write_fd.flush()
        fd = self.get_fd(segment)
        fd.seek(offset)
        header = fd.read(self.put_header_fmt.size)
        crc, size, tag, key = self.put_header_fmt.unpack(header)
        if size > MAX_OBJECT_SIZE:
            raise IntegrityError('Invalid segment object size')
        data = fd.read(size - self.put_header_fmt.size)
        if crc32(data, crc32(memoryview(header)[4:])) & 0xffffffff != crc:
            raise IntegrityError('Segment checksum mismatch')
        if tag != TAG_PUT or id != key:
            raise IntegrityError('Invalid segment entry header')
        return data

    def write_put(self, id, data):
        size = len(data) + self.put_header_fmt.size
        fd = self.get_write_fd()
        offset = self.offset
        header = self.header_no_crc_fmt.pack(size, TAG_PUT)
        crc = self.crc_fmt.pack(crc32(data, crc32(id, crc32(header))) & 0xffffffff)
        fd.write(b''.join((crc, header, id, data)))
        self.offset += size
        return self.segment, offset

    def write_delete(self, id):
        fd = self.get_write_fd()
        header = self.header_no_crc_fmt.pack(self.put_header_fmt.size, TAG_DELETE)
        crc = self.crc_fmt.pack(crc32(id, crc32(header)) & 0xffffffff)
        fd.write(b''.join((crc, header, id)))
        self.offset += self.put_header_fmt.size
        return self.segment

    def write_commit(self):
        fd = self.get_write_fd(no_new=True)
        header = self.header_no_crc_fmt.pack(self.header_fmt.size, TAG_COMMIT)
        crc = self.crc_fmt.pack(crc32(header) & 0xffffffff)
        fd.write(b''.join((crc, header)))
        self.close_segment()

    def close_segment(self):
        if self._write_fd:
            self.segment += 1
            self.offset = 0
            os.fsync(self._write_fd)
            self._write_fd.close()
            self._write_fd = None

########NEW FILE########
__FILENAME__ = archive
import msgpack
from attic.testsuite import AtticTestCase
from attic.archive import CacheChunkBuffer, RobustUnpacker
from attic.key import PlaintextKey


class MockCache:

    def __init__(self):
        self.objects = {}

    def add_chunk(self, id, data, stats=None):
        self.objects[id] = data
        return id, len(data), len(data)


class ChunkBufferTestCase(AtticTestCase):

    def test(self):
        data = [{b'foo': 1}, {b'bar': 2}]
        cache = MockCache()
        key = PlaintextKey()
        chunks = CacheChunkBuffer(cache, key, None)
        for d in data:
            chunks.add(d)
            chunks.flush()
        chunks.flush(flush=True)
        self.assert_equal(len(chunks.chunks), 2)
        unpacker = msgpack.Unpacker()
        for id in chunks.chunks:
            unpacker.feed(cache.objects[id])
        self.assert_equal(data, list(unpacker))


class RobustUnpackerTestCase(AtticTestCase):

    def make_chunks(self, items):
        return b''.join(msgpack.packb({'path': item}) for item in items)

    def _validator(self, value):
        return isinstance(value, dict) and value.get(b'path') in (b'foo', b'bar', b'boo', b'baz')

    def process(self, input):
        unpacker = RobustUnpacker(validator=self._validator)
        result = []
        for should_sync, chunks in input:
            if should_sync:
                unpacker.resync()
            for data in chunks:
                unpacker.feed(data)
                for item in unpacker:
                    result.append(item)
        return result

    def test_extra_garbage_no_sync(self):
        chunks = [(False, [self.make_chunks([b'foo', b'bar'])]),
                  (False, [b'garbage'] + [self.make_chunks([b'boo', b'baz'])])]
        result = self.process(chunks)
        self.assert_equal(result, [
            {b'path': b'foo'}, {b'path': b'bar'},
            103, 97, 114, 98, 97, 103, 101,
            {b'path': b'boo'},
            {b'path': b'baz'}])

    def split(self, left, length):
        parts = []
        while left:
            parts.append(left[:length])
            left = left[length:]
        return parts

    def test_correct_stream(self):
        chunks = self.split(self.make_chunks([b'foo', b'bar', b'boo', b'baz']), 2)
        input = [(False, chunks)]
        result = self.process(input)
        self.assert_equal(result, [{b'path': b'foo'}, {b'path': b'bar'}, {b'path': b'boo'}, {b'path': b'baz'}])

    def test_missing_chunk(self):
        chunks = self.split(self.make_chunks([b'foo', b'bar', b'boo', b'baz']), 4)
        input = [(False, chunks[:3]), (True, chunks[4:])]
        result = self.process(input)
        self.assert_equal(result, [{b'path': b'foo'}, {b'path': b'boo'}, {b'path': b'baz'}])

    def test_corrupt_chunk(self):
        chunks = self.split(self.make_chunks([b'foo', b'bar', b'boo', b'baz']), 4)
        input = [(False, chunks[:3]), (True, [b'gar', b'bage'] + chunks[3:])]
        result = self.process(input)
        self.assert_equal(result, [{b'path': b'foo'}, {b'path': b'boo'}, {b'path': b'baz'}])

########NEW FILE########
__FILENAME__ = archiver
import os
from io import StringIO
import stat
import subprocess
import sys
import shutil
import tempfile
import time
import unittest
from hashlib import sha256
from attic import xattr
from attic.archive import Archive, ChunkBuffer
from attic.archiver import Archiver
from attic.crypto import bytes_to_long, num_aes_blocks
from attic.helpers import Manifest
from attic.remote import RemoteRepository, PathNotAllowed
from attic.repository import Repository
from attic.testsuite import AtticTestCase
from attic.testsuite.mock import patch

try:
    import llfuse
    has_llfuse = True
except ImportError:
    has_llfuse = False

has_lchflags = hasattr(os, 'lchflags')

src_dir = os.path.join(os.getcwd(), os.path.dirname(__file__), '..')


class changedir:
    def __init__(self, dir):
        self.dir = dir

    def __enter__(self):
        self.old = os.getcwd()
        os.chdir(self.dir)

    def __exit__(self, *args, **kw):
        os.chdir(self.old)


class ArchiverTestCaseBase(AtticTestCase):

    prefix = ''

    def setUp(self):
        os.environ['ATTIC_CHECK_I_KNOW_WHAT_I_AM_DOING'] = '1'
        self.archiver = Archiver()
        self.tmpdir = tempfile.mkdtemp()
        self.repository_path = os.path.join(self.tmpdir, 'repository')
        self.repository_location = self.prefix + self.repository_path
        self.input_path = os.path.join(self.tmpdir, 'input')
        self.output_path = os.path.join(self.tmpdir, 'output')
        self.keys_path = os.path.join(self.tmpdir, 'keys')
        self.cache_path = os.path.join(self.tmpdir, 'cache')
        self.exclude_file_path = os.path.join(self.tmpdir, 'excludes')
        os.environ['ATTIC_KEYS_DIR'] = self.keys_path
        os.environ['ATTIC_CACHE_DIR'] = self.cache_path
        os.mkdir(self.input_path)
        os.mkdir(self.output_path)
        os.mkdir(self.keys_path)
        os.mkdir(self.cache_path)
        with open(self.exclude_file_path, 'wb') as fd:
            fd.write(b'input/file2\n# A commment line, then a blank line\n\n')
        self._old_wd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self._old_wd)

    def attic(self, *args, **kw):
        exit_code = kw.get('exit_code', 0)
        fork = kw.get('fork', False)
        if fork:
            try:
                output = subprocess.check_output((sys.executable, '-m', 'attic.archiver') + args)
                ret = 0
            except subprocess.CalledProcessError as e:
                output = e.output
                ret = e.returncode
            output = os.fsdecode(output)
            if ret != exit_code:
                print(output)
            self.assert_equal(exit_code, ret)
            return output
        args = list(args)
        stdout, stderr = sys.stdout, sys.stderr
        try:
            output = StringIO()
            sys.stdout = sys.stderr = output
            ret = self.archiver.run(args)
            sys.stdout, sys.stderr = stdout, stderr
            if ret != exit_code:
                print(output.getvalue())
            self.assert_equal(exit_code, ret)
            return output.getvalue()
        finally:
            sys.stdout, sys.stderr = stdout, stderr

    def create_src_archive(self, name):
        self.attic('create', self.repository_location + '::' + name, src_dir)


class ArchiverTestCase(ArchiverTestCaseBase):

    def create_regular_file(self, name, size=0, contents=None):
        filename = os.path.join(self.input_path, name)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(filename, 'wb') as fd:
            if contents is None:
                contents = b'X' * size
            fd.write(contents)

    def create_test_files(self):
        """Create a minimal test case including all supported file types
        """
        # File
        self.create_regular_file('empty', size=0)
        # 2600-01-01 > 2**64 ns
        os.utime('input/empty', (19880895600, 19880895600))
        self.create_regular_file('file1', size=1024 * 80)
        self.create_regular_file('flagfile', size=1024)
        # Directory
        self.create_regular_file('dir2/file2', size=1024 * 80)
        # File owner
        os.chown('input/file1', 100, 200)
        # File mode
        os.chmod('input/file1', 0o7755)
        os.chmod('input/dir2', 0o555)
        # Block device
        os.mknod('input/bdev', 0o600 | stat.S_IFBLK,  os.makedev(10, 20))
        # Char device
        os.mknod('input/cdev', 0o600 | stat.S_IFCHR,  os.makedev(30, 40))
        # Hard link
        os.link(os.path.join(self.input_path, 'file1'),
                os.path.join(self.input_path, 'hardlink'))
        # Symlink
        os.symlink('somewhere', os.path.join(self.input_path, 'link1'))
        if xattr.is_enabled():
            xattr.setxattr(os.path.join(self.input_path, 'file1'), 'user.foo', b'bar')
            xattr.setxattr(os.path.join(self.input_path, 'link1'), 'user.foo_symlink', b'bar_symlink', follow_symlinks=False)
        # FIFO node
        os.mkfifo(os.path.join(self.input_path, 'fifo1'))
        if has_lchflags:
            os.lchflags(os.path.join(self.input_path, 'flagfile'), stat.UF_NODUMP)

    def test_basic_functionality(self):
        self.create_test_files()
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test', 'input')
        self.attic('create', self.repository_location + '::test.2', 'input')
        with changedir('output'):
            self.attic('extract', self.repository_location + '::test')
        self.assert_equal(len(self.attic('list', self.repository_location).splitlines()), 2)
        self.assert_equal(len(self.attic('list', self.repository_location + '::test').splitlines()), 11)
        self.assert_dirs_equal('input', 'output/input')
        info_output = self.attic('info', self.repository_location + '::test')
        shutil.rmtree(self.cache_path)
        info_output2 = self.attic('info', self.repository_location + '::test')
        # info_output2 starts with some "initializing cache" text but should
        # end the same way as info_output
        assert info_output2.endswith(info_output)

    def test_extract_include_exclude(self):
        self.attic('init', self.repository_location)
        self.create_regular_file('file1', size=1024 * 80)
        self.create_regular_file('file2', size=1024 * 80)
        self.create_regular_file('file3', size=1024 * 80)
        self.create_regular_file('file4', size=1024 * 80)
        self.attic('create', '--exclude=input/file4', self.repository_location + '::test', 'input')
        with changedir('output'):
            self.attic('extract', self.repository_location + '::test', 'input/file1', )
        self.assert_equal(sorted(os.listdir('output/input')), ['file1'])
        with changedir('output'):
            self.attic('extract', '--exclude=input/file2', self.repository_location + '::test')
        self.assert_equal(sorted(os.listdir('output/input')), ['file1', 'file3'])
        with changedir('output'):
            self.attic('extract', '--exclude-from=' + self.exclude_file_path, self.repository_location + '::test')
        self.assert_equal(sorted(os.listdir('output/input')), ['file1', 'file3'])

    def test_exclude_caches(self):
        self.attic('init', self.repository_location)
        self.create_regular_file('file1', size=1024 * 80)
        self.create_regular_file('cache1/CACHEDIR.TAG', contents = b'Signature: 8a477f597d28d172789f06886806bc55 extra stuff')
        self.create_regular_file('cache2/CACHEDIR.TAG', contents = b'invalid signature')
        self.attic('create', '--exclude-caches', self.repository_location + '::test', 'input')
        with changedir('output'):
            self.attic('extract', self.repository_location + '::test')
        self.assert_equal(sorted(os.listdir('output/input')), ['cache2', 'file1'])
        self.assert_equal(sorted(os.listdir('output/input/cache2')), ['CACHEDIR.TAG'])

    def test_path_normalization(self):
        self.attic('init', self.repository_location)
        self.create_regular_file('dir1/dir2/file', size=1024 * 80)
        with changedir('input/dir1/dir2'):
            self.attic('create', self.repository_location + '::test', '../../../input/dir1/../dir1/dir2/..')
        output = self.attic('list', self.repository_location + '::test')
        self.assert_not_in('..', output)
        self.assert_in(' input/dir1/dir2/file', output)

    def test_repeated_files(self):
        self.create_regular_file('file1', size=1024 * 80)
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test', 'input', 'input')

    def test_overwrite(self):
        self.create_regular_file('file1', size=1024 * 80)
        self.create_regular_file('dir2/file2', size=1024 * 80)
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test', 'input')
        # Overwriting regular files and directories should be supported
        os.mkdir('output/input')
        os.mkdir('output/input/file1')
        os.mkdir('output/input/dir2')
        with changedir('output'):
            self.attic('extract', self.repository_location + '::test')
        self.assert_dirs_equal('input', 'output/input')
        # But non-empty dirs should fail
        os.unlink('output/input/file1')
        os.mkdir('output/input/file1')
        os.mkdir('output/input/file1/dir')
        with changedir('output'):
            self.attic('extract', self.repository_location + '::test', exit_code=1)

    def test_delete(self):
        self.create_regular_file('file1', size=1024 * 80)
        self.create_regular_file('dir2/file2', size=1024 * 80)
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test', 'input')
        self.attic('create', self.repository_location + '::test.2', 'input')
        self.attic('extract', '--dry-run', self.repository_location + '::test')
        self.attic('extract', '--dry-run', self.repository_location + '::test.2')
        self.attic('delete', self.repository_location + '::test')
        self.attic('extract', '--dry-run', self.repository_location + '::test.2')
        self.attic('delete', self.repository_location + '::test.2')
        # Make sure all data except the manifest has been deleted
        repository = Repository(self.repository_path)
        self.assert_equal(len(repository), 1)

    def test_corrupted_repository(self):
        self.attic('init', self.repository_location)
        self.create_src_archive('test')
        self.attic('extract', '--dry-run', self.repository_location + '::test')
        self.attic('check', self.repository_location)
        name = sorted(os.listdir(os.path.join(self.tmpdir, 'repository', 'data', '0')), reverse=True)[0]
        fd = open(os.path.join(self.tmpdir, 'repository', 'data', '0', name), 'r+')
        fd.seek(100)
        fd.write('XXXX')
        fd.close()
        self.attic('check', self.repository_location, exit_code=1)

    def test_readonly_repository(self):
        self.attic('init', self.repository_location)
        self.create_src_archive('test')
        os.system('chmod -R ugo-w ' + self.repository_path)
        try:
            self.attic('extract', '--dry-run', self.repository_location + '::test')
        finally:
            # Restore permissions so shutil.rmtree is able to delete it
            os.system('chmod -R u+w ' + self.repository_path)

    def test_cmdline_compatibility(self):
        self.create_regular_file('file1', size=1024 * 80)
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test', 'input')
        output = self.attic('verify', '-v', self.repository_location + '::test')
        self.assert_in('"attic verify" has been deprecated', output)
        output = self.attic('prune', self.repository_location, '--hourly=1')
        self.assert_in('"--hourly" has been deprecated. Use "--keep-hourly" instead', output)

    def test_prune_repository(self):
        self.attic('init', self.repository_location)
        self.attic('create', self.repository_location + '::test1', src_dir)
        self.attic('create', self.repository_location + '::test2', src_dir)
        output = self.attic('prune', '-v', '--dry-run', self.repository_location, '--keep-daily=2')
        self.assert_in('Keeping archive: test2', output)
        self.assert_in('Would prune:     test1', output)
        output = self.attic('list', self.repository_location)
        self.assert_in('test1', output)
        self.assert_in('test2', output)
        self.attic('prune', self.repository_location, '--keep-daily=2')
        output = self.attic('list', self.repository_location)
        self.assert_not_in('test1', output)
        self.assert_in('test2', output)

    def test_usage(self):
        self.assert_raises(SystemExit, lambda: self.attic())
        self.assert_raises(SystemExit, lambda: self.attic('-h'))

    @unittest.skipUnless(has_llfuse, 'llfuse not installed')
    def test_fuse_mount_repository(self):
        mountpoint = os.path.join(self.tmpdir, 'mountpoint')
        os.mkdir(mountpoint)
        self.attic('init', self.repository_location)
        self.create_test_files()
        self.attic('create', self.repository_location + '::archive', 'input')
        self.attic('create', self.repository_location + '::archive2', 'input')
        try:
            self.attic('mount', self.repository_location, mountpoint, fork=True)
            self.wait_for_mount(mountpoint)
            self.assert_dirs_equal(self.input_path, os.path.join(mountpoint, 'archive', 'input'))
            self.assert_dirs_equal(self.input_path, os.path.join(mountpoint, 'archive2', 'input'))
        finally:
            if sys.platform.startswith('linux'):
                os.system('fusermount -u ' + mountpoint)
            else:
                os.system('umount ' + mountpoint)
            os.rmdir(mountpoint)
            # Give the daemon some time to exit
            time.sleep(.2)

    @unittest.skipUnless(has_llfuse, 'llfuse not installed')
    def test_fuse_mount_archive(self):
        mountpoint = os.path.join(self.tmpdir, 'mountpoint')
        os.mkdir(mountpoint)
        self.attic('init', self.repository_location)
        self.create_test_files()
        self.attic('create', self.repository_location + '::archive', 'input')
        try:
            self.attic('mount', self.repository_location + '::archive', mountpoint, fork=True)
            self.wait_for_mount(mountpoint)
            self.assert_dirs_equal(self.input_path, os.path.join(mountpoint, 'input'))
        finally:
            if sys.platform.startswith('linux'):
                os.system('fusermount -u ' + mountpoint)
            else:
                os.system('umount ' + mountpoint)
            os.rmdir(mountpoint)
            # Give the daemon some time to exit
            time.sleep(.2)

    def verify_aes_counter_uniqueness(self, method):
        seen = set()  # Chunks already seen
        used = set()  # counter values already used

        def verify_uniqueness():
            repository = Repository(self.repository_path)
            for key, _ in repository.get_read_only_index(repository.get_transaction_id()).iteritems():
                data = repository.get(key)
                hash = sha256(data).digest()
                if not hash in seen:
                    seen.add(hash)
                    num_blocks = num_aes_blocks(len(data) - 41)
                    nonce = bytes_to_long(data[33:41])
                    for counter in range(nonce, nonce + num_blocks):
                        self.assert_not_in(counter, used)
                        used.add(counter)

        self.create_test_files()
        os.environ['ATTIC_PASSPHRASE'] = 'passphrase'
        self.attic('init', '--encryption=' + method, self.repository_location)
        verify_uniqueness()
        self.attic('create', self.repository_location + '::test', 'input')
        verify_uniqueness()
        self.attic('create', self.repository_location + '::test.2', 'input')
        verify_uniqueness()
        self.attic('delete', self.repository_location + '::test.2')
        verify_uniqueness()
        self.assert_equal(used, set(range(len(used))))

    def test_aes_counter_uniqueness_keyfile(self):
        self.verify_aes_counter_uniqueness('keyfile')

    def test_aes_counter_uniqueness_passphrase(self):
        self.verify_aes_counter_uniqueness('passphrase')


class ArchiverCheckTestCase(ArchiverTestCaseBase):

    def setUp(self):
        super(ArchiverCheckTestCase, self).setUp()
        with patch.object(ChunkBuffer, 'BUFFER_SIZE', 10):
            self.attic('init', self.repository_location)
            self.create_src_archive('archive1')
            self.create_src_archive('archive2')

    def open_archive(self, name):
        repository = Repository(self.repository_path)
        manifest, key = Manifest.load(repository)
        archive = Archive(repository, key, manifest, name)
        return archive, repository

    def test_check_usage(self):
        output = self.attic('check', self.repository_location, exit_code=0)
        self.assert_in('Starting repository check', output)
        self.assert_in('Starting archive consistency check', output)
        output = self.attic('check', '--repository-only', self.repository_location, exit_code=0)
        self.assert_in('Starting repository check', output)
        self.assert_not_in('Starting archive consistency check', output)
        output = self.attic('check', '--archives-only', self.repository_location, exit_code=0)
        self.assert_not_in('Starting repository check', output)
        self.assert_in('Starting archive consistency check', output)

    def test_missing_file_chunk(self):
        archive, repository = self.open_archive('archive1')
        for item in archive.iter_items():
            if item[b'path'].endswith('testsuite/archiver.py'):
                repository.delete(item[b'chunks'][-1][0])
                break
        repository.commit()
        self.attic('check', self.repository_location, exit_code=1)
        self.attic('check', '--repair', self.repository_location, exit_code=0)
        self.attic('check', self.repository_location, exit_code=0)

    def test_missing_archive_item_chunk(self):
        archive, repository = self.open_archive('archive1')
        repository.delete(archive.metadata[b'items'][-5])
        repository.commit()
        self.attic('check', self.repository_location, exit_code=1)
        self.attic('check', '--repair', self.repository_location, exit_code=0)
        self.attic('check', self.repository_location, exit_code=0)

    def test_missing_archive_metadata(self):
        archive, repository = self.open_archive('archive1')
        repository.delete(archive.id)
        repository.commit()
        self.attic('check', self.repository_location, exit_code=1)
        self.attic('check', '--repair', self.repository_location, exit_code=0)
        self.attic('check', self.repository_location, exit_code=0)

    def test_missing_manifest(self):
        archive, repository = self.open_archive('archive1')
        repository.delete(Manifest.MANIFEST_ID)
        repository.commit()
        self.attic('check', self.repository_location, exit_code=1)
        output = self.attic('check', '--repair', self.repository_location, exit_code=0)
        self.assert_in('archive1', output)
        self.assert_in('archive2', output)
        self.attic('check', self.repository_location, exit_code=0)

    def test_extra_chunks(self):
        self.attic('check', self.repository_location, exit_code=0)
        repository = Repository(self.repository_location)
        repository.put(b'01234567890123456789012345678901', b'xxxx')
        repository.commit()
        repository.close()
        self.attic('check', self.repository_location, exit_code=1)
        self.attic('check', self.repository_location, exit_code=1)
        self.attic('check', '--repair', self.repository_location, exit_code=0)
        self.attic('check', self.repository_location, exit_code=0)
        self.attic('extract', '--dry-run', self.repository_location + '::archive1', exit_code=0)


class RemoteArchiverTestCase(ArchiverTestCase):
    prefix = '__testsuite__:'

    def test_remote_repo_restrict_to_path(self):
        self.attic('init', self.repository_location)
        path_prefix = os.path.dirname(self.repository_path)
        with patch.object(RemoteRepository, 'extra_test_args', ['--restrict-to-path', '/foo']):
            self.assert_raises(PathNotAllowed, lambda: self.attic('init', self.repository_location + '_1'))
        with patch.object(RemoteRepository, 'extra_test_args', ['--restrict-to-path', path_prefix]):
            self.attic('init', self.repository_location + '_2')
        with patch.object(RemoteRepository, 'extra_test_args', ['--restrict-to-path', '/foo', '--restrict-to-path', path_prefix]):
            self.attic('init', self.repository_location + '_3')

########NEW FILE########
__FILENAME__ = chunker
from attic.chunker import chunkify, buzhash, buzhash_update
from attic.testsuite import AtticTestCase
from io import BytesIO


class ChunkerTestCase(AtticTestCase):

    def test_chunkify(self):
        data = b'0' * 1024 * 1024 * 15 + b'Y'
        parts = [bytes(c) for c in chunkify(BytesIO(data), 2, 0x3, 2, 0)]
        self.assert_equal(len(parts), 2)
        self.assert_equal(b''.join(parts), data)
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b''), 2, 0x3, 2, 0)], [])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 2, 0x3, 2, 0)], [b'fooba', b'rboobaz', b'fooba', b'rboobaz', b'fooba', b'rboobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 2, 0x3, 2, 1)], [b'fo', b'obarb', b'oob', b'azf', b'oobarb', b'oob', b'azf', b'oobarb', b'oobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 2, 0x3, 2, 2)], [b'foob', b'ar', b'boobazfoob', b'ar', b'boobazfoob', b'ar', b'boobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 3, 0)], [b'foobarboobaz' * 3])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 3, 1)], [b'foobar', b'boo', b'bazfo', b'obar', b'boo', b'bazfo', b'obar', b'boobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 3, 2)], [b'foo', b'barboobaz', b'foo', b'barboobaz', b'foo', b'barboobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 4, 0)], [b'foobarboobaz' * 3])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 4, 1)], [b'foobar', b'boobazfo', b'obar', b'boobazfo', b'obar', b'boobaz'])
        self.assert_equal([bytes(c) for c in chunkify(BytesIO(b'foobarboobaz' * 3), 3, 0x3, 4, 2)], [b'foob', b'arboobaz', b'foob', b'arboobaz', b'foob', b'arboobaz'])

    def test_buzhash(self):
        self.assert_equal(buzhash(b'abcdefghijklmnop', 0), 3795437769)
        self.assert_equal(buzhash(b'abcdefghijklmnop', 1), 3795400502)
        self.assert_equal(buzhash(b'abcdefghijklmnop', 1), buzhash_update(buzhash(b'Xabcdefghijklmno', 1), ord('X'), ord('p'), 16, 1))

########NEW FILE########
__FILENAME__ = crypto
from binascii import hexlify
from attic.testsuite import AtticTestCase
from attic.crypto import AES, bytes_to_long, bytes_to_int, long_to_bytes, pbkdf2_sha256, get_random_bytes


class CryptoTestCase(AtticTestCase):

    def test_bytes_to_int(self):
        self.assert_equal(bytes_to_int(b'\0\0\0\1'), 1)

    def test_bytes_to_long(self):
        self.assert_equal(bytes_to_long(b'\0\0\0\0\0\0\0\1'), 1)
        self.assert_equal(long_to_bytes(1), b'\0\0\0\0\0\0\0\1')

    def test_pbkdf2_sha256(self):
        self.assert_equal(hexlify(pbkdf2_sha256(b'password', b'salt', 1, 32)),
                         b'120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b')
        self.assert_equal(hexlify(pbkdf2_sha256(b'password', b'salt', 2, 32)),
                         b'ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43')
        self.assert_equal(hexlify(pbkdf2_sha256(b'password', b'salt', 4096, 32)),
                         b'c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a')

    def test_get_random_bytes(self):
        bytes = get_random_bytes(10)
        bytes2 = get_random_bytes(10)
        self.assert_equal(len(bytes), 10)
        self.assert_equal(len(bytes2), 10)
        self.assert_not_equal(bytes, bytes2)

    def test_aes(self):
        key = b'X' * 32
        data = b'foo' * 10
        aes = AES(key)
        self.assert_equal(bytes_to_long(aes.iv, 8), 0)
        cdata = aes.encrypt(data)
        self.assert_equal(hexlify(cdata), b'c6efb702de12498f34a2c2bbc8149e759996d08bf6dc5c610aefc0c3a466')
        self.assert_equal(bytes_to_long(aes.iv, 8), 2)
        self.assert_not_equal(data, aes.decrypt(cdata))
        aes.reset(iv=b'\0' * 16)
        self.assert_equal(data, aes.decrypt(cdata))

########NEW FILE########
__FILENAME__ = hashindex
import hashlib
import os
import tempfile
from attic.hashindex import NSIndex, ChunkIndex
from attic.testsuite import AtticTestCase


class HashIndexTestCase(AtticTestCase):

    def _generic_test(self, cls, make_value, sha):
        idx_name = tempfile.NamedTemporaryFile()
        idx = cls.create(idx_name.name)
        self.assert_equal(len(idx), 0)
        # Test set
        for x in range(100):
            idx[bytes('%-32d' % x, 'ascii')] = make_value(x)
        self.assert_equal(len(idx), 100)
        for x in range(100):
            self.assert_equal(idx[bytes('%-32d' % x, 'ascii')], make_value(x))
        # Test update
        for x in range(100):
            idx[bytes('%-32d' % x, 'ascii')] = make_value(x * 2)
        self.assert_equal(len(idx), 100)
        for x in range(100):
            self.assert_equal(idx[bytes('%-32d' % x, 'ascii')], make_value(x * 2))
        # Test delete
        for x in range(50):
            del idx[bytes('%-32d' % x, 'ascii')]
        self.assert_equal(len(idx), 50)
        del idx
        # Verify file contents
        with open(idx_name.name, 'rb') as fd:
            self.assert_equal(hashlib.sha256(fd.read()).hexdigest(), sha)
        # Make sure we can open the file
        idx = cls(idx_name.name)
        self.assert_equal(len(idx), 50)
        for x in range(50, 100):
            self.assert_equal(idx[bytes('%-32d' % x, 'ascii')], make_value(x * 2))
        idx.clear()
        self.assert_equal(len(idx), 0)
        del idx
        self.assert_equal(len(cls(idx_name.name)), 0)

    def test_nsindex(self):
        self._generic_test(NSIndex, lambda x: (x, x), '369a18ae6a52524eb2884a3c0fdc2824947edd017a2688c5d4d7b3510c245ab9')

    def test_chunkindex(self):
        self._generic_test(ChunkIndex, lambda x: (x, x, x), 'ed22e8a883400453c0ee79a06c54df72c994a54eeefdc6c0989efdc5ee6d07b7')

    def test_resize(self):
        n = 2000  # Must be >= MIN_BUCKETS
        idx_name = tempfile.NamedTemporaryFile()
        idx = NSIndex.create(idx_name.name)
        initial_size = os.path.getsize(idx_name.name)
        self.assert_equal(len(idx), 0)
        for x in range(n):
            idx[bytes('%-32d' % x, 'ascii')] = x, x
        idx.flush()
        self.assert_true(initial_size < os.path.getsize(idx_name.name))
        for x in range(n):
            del idx[bytes('%-32d' % x, 'ascii')]
        self.assert_equal(len(idx), 0)
        idx.flush()
        self.assert_equal(initial_size, os.path.getsize(idx_name.name))

    def test_read_only(self):
        """Make sure read_only indices work even they contain a lot of tombstones
        """
        idx_name = tempfile.NamedTemporaryFile()
        idx = NSIndex.create(idx_name.name)
        for x in range(100):
            idx[bytes('%-0.32d' % x, 'ascii')] = x, x
        for x in range(99):
            del idx[bytes('%-0.32d' % x, 'ascii')]
        idx.flush()
        idx2 = NSIndex(idx_name.name, readonly=True)
        self.assert_equal(idx2[bytes('%-0.32d' % 99, 'ascii')], (99, 99))

    def test_iteritems(self):
        idx_name = tempfile.NamedTemporaryFile()
        idx = NSIndex.create(idx_name.name)
        for x in range(100):
            idx[bytes('%-0.32d' % x, 'ascii')] = x, x
        all = list(idx.iteritems())
        self.assert_equal(len(all), 100)
        second_half = list(idx.iteritems(marker=all[49][0]))
        self.assert_equal(len(second_half), 50)
        self.assert_equal(second_half, all[50:])

########NEW FILE########
__FILENAME__ = helpers
import hashlib
from time import mktime, strptime
from datetime import datetime, timezone, timedelta
import os
import tempfile
import unittest
from attic.helpers import adjust_patterns, exclude_path, Location, format_timedelta, IncludePattern, ExcludePattern, make_path_safe, UpgradableLock, prune_within, prune_split, to_localtime, \
    StableDict, int_to_bigint, bigint_to_int
from attic.testsuite import AtticTestCase
import msgpack


class BigIntTestCase(AtticTestCase):

    def test_bigint(self):
        self.assert_equal(int_to_bigint(0), 0)
        self.assert_equal(int_to_bigint(2**63-1), 2**63-1)
        self.assert_equal(int_to_bigint(-2**63+1), -2**63+1)
        self.assert_equal(int_to_bigint(2**63), b'\x00\x00\x00\x00\x00\x00\x00\x80\x00')
        self.assert_equal(int_to_bigint(-2**63), b'\x00\x00\x00\x00\x00\x00\x00\x80\xff')
        self.assert_equal(bigint_to_int(int_to_bigint(-2**70)), -2**70)
        self.assert_equal(bigint_to_int(int_to_bigint(2**70)), 2**70)


class LocationTestCase(AtticTestCase):

    def test(self):
        self.assert_equal(
            repr(Location('ssh://user@host:1234/some/path::archive')),
            "Location(proto='ssh', user='user', host='host', port=1234, path='/some/path', archive='archive')"
        )
        self.assert_equal(
            repr(Location('file:///some/path::archive')),
            "Location(proto='file', user=None, host=None, port=None, path='/some/path', archive='archive')"
        )
        self.assert_equal(
            repr(Location('user@host:/some/path::archive')),
            "Location(proto='ssh', user='user', host='host', port=None, path='/some/path', archive='archive')"
        )
        self.assert_equal(
            repr(Location('mybackup.attic::archive')),
            "Location(proto='file', user=None, host=None, port=None, path='mybackup.attic', archive='archive')"
        )
        self.assert_equal(
            repr(Location('/some/absolute/path::archive')),
            "Location(proto='file', user=None, host=None, port=None, path='/some/absolute/path', archive='archive')"
        )
        self.assert_equal(
            repr(Location('some/relative/path::archive')),
            "Location(proto='file', user=None, host=None, port=None, path='some/relative/path', archive='archive')"
        )


class FormatTimedeltaTestCase(AtticTestCase):

    def test(self):
        t0 = datetime(2001, 1, 1, 10, 20, 3, 0)
        t1 = datetime(2001, 1, 1, 12, 20, 4, 100000)
        self.assert_equal(
            format_timedelta(t1 - t0),
            '2 hours 1.10 seconds'
        )


class PatternTestCase(AtticTestCase):

    files = [
        '/etc/passwd', '/etc/hosts', '/home',
        '/home/user/.profile', '/home/user/.bashrc',
        '/home/user2/.profile', '/home/user2/public_html/index.html',
        '/var/log/messages', '/var/log/dmesg',
    ]

    def evaluate(self, paths, excludes):
        patterns = adjust_patterns(paths, [ExcludePattern(p) for p in excludes])
        return [path for path in self.files if not exclude_path(path, patterns)]

    def test(self):
        self.assert_equal(self.evaluate(['/'], []), self.files)
        self.assert_equal(self.evaluate([], []), self.files)
        self.assert_equal(self.evaluate(['/'], ['/h']), self.files)
        self.assert_equal(self.evaluate(['/'], ['/home']),
                          ['/etc/passwd', '/etc/hosts', '/var/log/messages', '/var/log/dmesg'])
        self.assert_equal(self.evaluate(['/'], ['/home/']),
                          ['/etc/passwd', '/etc/hosts', '/home', '/var/log/messages', '/var/log/dmesg'])
        self.assert_equal(self.evaluate(['/home/u'], []), [])
        self.assert_equal(self.evaluate(['/', '/home', '/etc/hosts'], ['/']), [])
        self.assert_equal(self.evaluate(['/home/'], ['/home/user2']), 
                          ['/home', '/home/user/.profile', '/home/user/.bashrc'])
        self.assert_equal(self.evaluate(['/'], ['*.profile', '/var/log']),
                          ['/etc/passwd', '/etc/hosts', '/home', '/home/user/.bashrc', '/home/user2/public_html/index.html'])
        self.assert_equal(self.evaluate(['/'], ['/home/*/public_html', '*.profile', '*/log/*']),
                          ['/etc/passwd', '/etc/hosts', '/home', '/home/user/.bashrc'])
        self.assert_equal(self.evaluate(['/etc/', '/var'], ['dmesg']),
                          ['/etc/passwd', '/etc/hosts', '/var/log/messages', '/var/log/dmesg'])


class MakePathSafeTestCase(AtticTestCase):

    def test(self):
        self.assert_equal(make_path_safe('/foo/bar'), 'foo/bar')
        self.assert_equal(make_path_safe('/foo/bar'), 'foo/bar')
        self.assert_equal(make_path_safe('../foo/bar'), 'foo/bar')
        self.assert_equal(make_path_safe('../../foo/bar'), 'foo/bar')
        self.assert_equal(make_path_safe('/'), '.')
        self.assert_equal(make_path_safe('/'), '.')


class UpgradableLockTestCase(AtticTestCase):

    def test(self):
        file = tempfile.NamedTemporaryFile()
        lock = UpgradableLock(file.name)
        lock.upgrade()
        lock.upgrade()
        lock.release()

    @unittest.skipIf(os.getuid() == 0, 'Root can always open files for writing')
    def test_read_only_lock_file(self):
        file = tempfile.NamedTemporaryFile()
        os.chmod(file.name, 0o444)
        lock = UpgradableLock(file.name)
        self.assert_raises(UpgradableLock.LockUpgradeFailed, lock.upgrade)
        lock.release()


class MockArchive(object):

    def __init__(self, ts):
        self.ts = ts

    def __repr__(self):
        return repr(self.ts)


class PruneSplitTestCase(AtticTestCase):

    def test(self):

        def local_to_UTC(month, day):
            'Convert noon on the month and day in 2013 to UTC.'
            seconds = mktime(strptime('2013-%02d-%02d 12:00' % (month, day), '%Y-%m-%d %H:%M'))
            return datetime.fromtimestamp(seconds, tz=timezone.utc)

        def subset(lst, indices):
            return {lst[i] for i in indices}

        def dotest(test_archives, n, skip, indices):
            for ta in test_archives, reversed(test_archives):
                self.assert_equal(set(prune_split(ta, '%Y-%m', n, skip)),
                                  subset(test_archives, indices))
            
        test_pairs = [(1,1), (2,1), (2,28), (3,1), (3,2), (3,31), (5,1)]
        test_dates = [local_to_UTC(month, day) for month, day in test_pairs]
        test_archives = [MockArchive(date) for date in test_dates]

        dotest(test_archives, 3, [], [6, 5, 2])
        dotest(test_archives, -1, [], [6, 5, 2, 0])
        dotest(test_archives, 3, [test_archives[6]], [5, 2, 0])
        dotest(test_archives, 3, [test_archives[5]], [6, 2, 0])
        dotest(test_archives, 3, [test_archives[4]], [6, 5, 2])
        dotest(test_archives, 0, [], [])


class PruneWithinTestCase(AtticTestCase):

    def test(self):

        def subset(lst, indices):
            return {lst[i] for i in indices}

        def dotest(test_archives, within, indices):
            for ta in test_archives, reversed(test_archives):
                self.assert_equal(set(prune_within(ta, within)),
                                  subset(test_archives, indices))
            
        # 1 minute, 1.5 hours, 2.5 hours, 3.5 hours, 25 hours, 49 hours
        test_offsets = [60, 90*60, 150*60, 210*60, 25*60*60, 49*60*60]
        now = datetime.now(timezone.utc)
        test_dates = [now - timedelta(seconds=s) for s in test_offsets]
        test_archives = [MockArchive(date) for date in test_dates]

        dotest(test_archives, '1H',  [0])
        dotest(test_archives, '2H',  [0, 1])
        dotest(test_archives, '3H',  [0, 1, 2])
        dotest(test_archives, '24H', [0, 1, 2, 3])
        dotest(test_archives, '26H', [0, 1, 2, 3, 4])
        dotest(test_archives, '2d',  [0, 1, 2, 3, 4])
        dotest(test_archives, '50H', [0, 1, 2, 3, 4, 5])
        dotest(test_archives, '3d',  [0, 1, 2, 3, 4, 5])
        dotest(test_archives, '1w',  [0, 1, 2, 3, 4, 5])
        dotest(test_archives, '1m',  [0, 1, 2, 3, 4, 5])
        dotest(test_archives, '1y',  [0, 1, 2, 3, 4, 5])


class StableDictTestCase(AtticTestCase):

    def test(self):
        d = StableDict(foo=1, bar=2, boo=3, baz=4)
        self.assert_equal(list(d.items()), [('bar', 2), ('baz', 4), ('boo', 3), ('foo', 1)])
        self.assert_equal(hashlib.md5(msgpack.packb(d)).hexdigest(), 'fc78df42cd60691b3ac3dd2a2b39903f')

########NEW FILE########
__FILENAME__ = key
import os
import re
import shutil
import tempfile
from binascii import hexlify
from attic.crypto import bytes_to_long, num_aes_blocks
from attic.testsuite import AtticTestCase
from attic.key import PlaintextKey, PassphraseKey, KeyfileKey
from attic.helpers import Location, unhexlify


class KeyTestCase(AtticTestCase):

    class MockArgs(object):
        repository = Location(tempfile.mkstemp()[1])

    keyfile2_key_file = """
        ATTIC KEY 0000000000000000000000000000000000000000000000000000000000000000
        hqppdGVyYXRpb25zzgABhqCkaGFzaNoAIMyonNI+7Cjv0qHi0AOBM6bLGxACJhfgzVD2oq
        bIS9SFqWFsZ29yaXRobaZzaGEyNTakc2FsdNoAINNK5qqJc1JWSUjACwFEWGTdM7Nd0a5l
        1uBGPEb+9XM9p3ZlcnNpb24BpGRhdGHaANAYDT5yfPpU099oBJwMomsxouKyx/OG4QIXK2
        hQCG2L2L/9PUu4WIuKvGrsXoP7syemujNfcZws5jLp2UPva4PkQhQsrF1RYDEMLh2eF9Ol
        rwtkThq1tnh7KjWMG9Ijt7/aoQtq0zDYP/xaFF8XXSJxiyP5zjH5+spB6RL0oQHvbsliSh
        /cXJq7jrqmrJ1phd6dg4SHAM/i+hubadZoS6m25OQzYAW09wZD/phG8OVa698Z5ed3HTaT
        SmrtgJL3EoOKgUI9d6BLE4dJdBqntifo""".strip()

    keyfile2_cdata = unhexlify(re.sub('\W', '', """
        0055f161493fcfc16276e8c31493c4641e1eb19a79d0326fad0291e5a9c98e5933
        00000000000003e8d21eaf9b86c297a8cd56432e1915bb
        """))
    keyfile2_id = unhexlify('c3fbf14bc001ebcc3cd86e696c13482ed071740927cd7cbe1b01b4bfcee49314')

    def setUp(self):
        self.tmppath = tempfile.mkdtemp()
        os.environ['ATTIC_KEYS_DIR'] = self.tmppath

    def tearDown(self):
        shutil.rmtree(self.tmppath)

    class MockRepository(object):
        class _Location(object):
            orig = '/some/place'

        _location = _Location()
        id = bytes(32)

    def test_plaintext(self):
        key = PlaintextKey.create(None, None)
        data = b'foo'
        self.assert_equal(hexlify(key.id_hash(data)), b'2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae')
        self.assert_equal(data, key.decrypt(key.id_hash(data), key.encrypt(data)))

    def test_keyfile(self):
        os.environ['ATTIC_PASSPHRASE'] = 'test'
        key = KeyfileKey.create(self.MockRepository(), self.MockArgs())
        self.assert_equal(bytes_to_long(key.enc_cipher.iv, 8), 0)
        manifest = key.encrypt(b'XXX')
        self.assert_equal(key.extract_nonce(manifest), 0)
        manifest2 = key.encrypt(b'XXX')
        self.assert_not_equal(manifest, manifest2)
        self.assert_equal(key.decrypt(None, manifest), key.decrypt(None, manifest2))
        self.assert_equal(key.extract_nonce(manifest2), 1)
        iv = key.extract_nonce(manifest)
        key2 = KeyfileKey.detect(self.MockRepository(), manifest)
        self.assert_equal(bytes_to_long(key2.enc_cipher.iv, 8), iv + num_aes_blocks(len(manifest) - KeyfileKey.PAYLOAD_OVERHEAD))
        # Key data sanity check
        self.assert_equal(len(set([key2.id_key, key2.enc_key, key2.enc_hmac_key])), 3)
        self.assert_equal(key2.chunk_seed == 0, False)
        data = b'foo'
        self.assert_equal(data, key2.decrypt(key.id_hash(data), key.encrypt(data)))

    def test_keyfile2(self):
        with open(os.path.join(os.environ['ATTIC_KEYS_DIR'], 'keyfile'), 'w') as fd:
            fd.write(self.keyfile2_key_file)
        os.environ['ATTIC_PASSPHRASE'] = 'passphrase'
        key = KeyfileKey.detect(self.MockRepository(), self.keyfile2_cdata)
        self.assert_equal(key.decrypt(self.keyfile2_id, self.keyfile2_cdata), b'payload')

    def test_passphrase(self):
        os.environ['ATTIC_PASSPHRASE'] = 'test'
        key = PassphraseKey.create(self.MockRepository(), None)
        self.assert_equal(bytes_to_long(key.enc_cipher.iv, 8), 0)
        self.assert_equal(hexlify(key.id_key), b'793b0717f9d8fb01c751a487e9b827897ceea62409870600013fbc6b4d8d7ca6')
        self.assert_equal(hexlify(key.enc_hmac_key), b'b885a05d329a086627412a6142aaeb9f6c54ab7950f996dd65587251f6bc0901')
        self.assert_equal(hexlify(key.enc_key), b'2ff3654c6daf7381dbbe718d2b20b4f1ea1e34caa6cc65f6bb3ac376b93fed2a')
        self.assert_equal(key.chunk_seed, -775740477)
        manifest = key.encrypt(b'XXX')
        self.assert_equal(key.extract_nonce(manifest), 0)
        manifest2 = key.encrypt(b'XXX')
        self.assert_not_equal(manifest, manifest2)
        self.assert_equal(key.decrypt(None, manifest), key.decrypt(None, manifest2))
        self.assert_equal(key.extract_nonce(manifest2), 1)
        iv = key.extract_nonce(manifest)
        key2 = PassphraseKey.detect(self.MockRepository(), manifest)
        self.assert_equal(bytes_to_long(key2.enc_cipher.iv, 8), iv + num_aes_blocks(len(manifest) - PassphraseKey.PAYLOAD_OVERHEAD))
        self.assert_equal(key.id_key, key2.id_key)
        self.assert_equal(key.enc_hmac_key, key2.enc_hmac_key)
        self.assert_equal(key.enc_key, key2.enc_key)
        self.assert_equal(key.chunk_seed, key2.chunk_seed)
        data = b'foo'
        self.assert_equal(hexlify(key.id_hash(data)), b'818217cf07d37efad3860766dcdf1d21e401650fed2d76ed1d797d3aae925990')
        self.assert_equal(data, key2.decrypt(key2.id_hash(data), key.encrypt(data)))

########NEW FILE########
__FILENAME__ = lrucache
from attic.lrucache import LRUCache
from attic.testsuite import AtticTestCase


class LRUCacheTestCase(AtticTestCase):

    def test(self):
        c = LRUCache(2)
        self.assert_equal(len(c), 0)
        for i, x in enumerate('abc'):
            c[x] = i
        self.assert_equal(len(c), 2)
        self.assert_equal(set(c), set(['b', 'c']))
        self.assert_equal(set(c.items()), set([('b', 1), ('c', 2)]))
        self.assert_equal(False, 'a' in c)
        self.assert_equal(True, 'b' in c)
        self.assert_raises(KeyError, lambda: c['a'])
        self.assert_equal(c['b'], 1)
        self.assert_equal(c['c'], 2)
        c['d'] = 3
        self.assert_equal(len(c), 2)
        self.assert_equal(c['c'], 2)
        self.assert_equal(c['d'], 3)
        c['c'] = 22
        c['e'] = 4
        self.assert_equal(len(c), 2)
        self.assert_raises(KeyError, lambda: c['d'])
        self.assert_equal(c['c'], 22)
        self.assert_equal(c['e'], 4)
        del c['c']
        self.assert_equal(len(c), 1)
        self.assert_raises(KeyError, lambda: c['c'])
        self.assert_equal(c['e'], 4)

    def test_pop(self):
        c = LRUCache(2)
        c[1] = 1
        c[2] = 2
        c.pop(1)
        c[3] = 3

########NEW FILE########
__FILENAME__ = mock
try:
    # Only available in python 3.3+
    from unittest.mock import *
except ImportError:
    from mock import *

########NEW FILE########
__FILENAME__ = platform
import os
import shutil
import sys
import tempfile
import unittest
from attic.platform import acl_get, acl_set
from attic.testsuite import AtticTestCase


ACCESS_ACL = """
user::rw-
user:root:rw-:0
user:9999:r--:9999
group::r--
group:root:r--:0
group:9999:r--:9999
mask::rw-
other::r--
""".strip().encode('ascii')

DEFAULT_ACL = """
user::rw-
user:root:r--:0
user:8888:r--:8888
group::r--
group:root:r--:0
group:8888:r--:8888
mask::rw-
other::r--
""".strip().encode('ascii')


def fakeroot_detected():
    return 'FAKEROOTKEY' in os.environ


@unittest.skipUnless(sys.platform.startswith('linux'), 'linux only test')
@unittest.skipIf(fakeroot_detected(), 'not compatible with fakeroot')
class PlatformLinuxTestCase(AtticTestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def get_acl(self, path, numeric_owner=False):
        item = {}
        acl_get(path, item, numeric_owner=numeric_owner)
        return item

    def set_acl(self, path, access=None, default=None, numeric_owner=False):
        item = {b'acl_access': access, b'acl_default': default}
        acl_set(path, item, numeric_owner=numeric_owner)

    def test_access_acl(self):
        file = tempfile.NamedTemporaryFile()
        self.assert_equal(self.get_acl(file.name), {})
        self.set_acl(file.name, access=b'user::rw-\ngroup::r--\nmask::rw-\nother::---\nuser:root:rw-:9999\ngroup:root:rw-:9999\n', numeric_owner=False)
        self.assert_in(b'user:root:rw-:0', self.get_acl(file.name)[b'acl_access'])
        self.assert_in(b'group:root:rw-:0', self.get_acl(file.name)[b'acl_access'])
        self.assert_in(b'user:0:rw-:0', self.get_acl(file.name, numeric_owner=True)[b'acl_access'])
        file2 = tempfile.NamedTemporaryFile()
        self.set_acl(file2.name, access=b'user::rw-\ngroup::r--\nmask::rw-\nother::---\nuser:root:rw-:9999\ngroup:root:rw-:9999\n', numeric_owner=True)
        self.assert_in(b'user:9999:rw-:9999', self.get_acl(file2.name)[b'acl_access'])
        self.assert_in(b'group:9999:rw-:9999', self.get_acl(file2.name)[b'acl_access'])

    def test_default_acl(self):
        self.assert_equal(self.get_acl(self.tmpdir), {})
        self.set_acl(self.tmpdir, access=ACCESS_ACL, default=DEFAULT_ACL)
        self.assert_equal(self.get_acl(self.tmpdir)[b'acl_access'], ACCESS_ACL)
        self.assert_equal(self.get_acl(self.tmpdir)[b'acl_default'], DEFAULT_ACL)


@unittest.skipUnless(sys.platform.startswith('darwin'), 'OS X only test')
@unittest.skipIf(fakeroot_detected(), 'not compatible with fakeroot')
class PlatformDarwinTestCase(AtticTestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def get_acl(self, path, numeric_owner=False):
        item = {}
        acl_get(path, item, numeric_owner=numeric_owner)
        return item

    def set_acl(self, path, acl, numeric_owner=False):
        item = {b'acl_extended': acl}
        acl_set(path, item, numeric_owner=numeric_owner)

    def test_access_acl(self):
        file = tempfile.NamedTemporaryFile()
        file2 = tempfile.NamedTemporaryFile()
        self.assert_equal(self.get_acl(file.name), {})
        self.set_acl(file.name, b'!#acl 1\ngroup:ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000:staff:0:allow:read\nuser:FFFFEEEE-DDDD-CCCC-BBBB-AAAA00000000:root:0:allow:read\n', numeric_owner=False)
        self.assert_in(b'group:ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000014:staff:20:allow:read', self.get_acl(file.name)[b'acl_extended'])
        self.assert_in(b'user:FFFFEEEE-DDDD-CCCC-BBBB-AAAA00000000:root:0:allow:read', self.get_acl(file.name)[b'acl_extended'])
        self.set_acl(file2.name, b'!#acl 1\ngroup:ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000:staff:0:allow:read\nuser:FFFFEEEE-DDDD-CCCC-BBBB-AAAA00000000:root:0:allow:read\n', numeric_owner=True)
        self.assert_in(b'group:ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000:wheel:0:allow:read', self.get_acl(file2.name)[b'acl_extended'])
        self.assert_in(b'group:ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000::0:allow:read', self.get_acl(file2.name, numeric_owner=True)[b'acl_extended'])


########NEW FILE########
__FILENAME__ = repository
import os
import shutil
import tempfile
from attic.testsuite.mock import patch
from attic.hashindex import NSIndex
from attic.helpers import Location, IntegrityError, UpgradableLock
from attic.remote import RemoteRepository
from attic.repository import Repository
from attic.testsuite import AtticTestCase


class RepositoryTestCaseBase(AtticTestCase):

    def open(self, create=False):
        return Repository(os.path.join(self.tmppath, 'repository'), create=create)

    def setUp(self):
        self.tmppath = tempfile.mkdtemp()
        self.repository = self.open(create=True)

    def tearDown(self):
        self.repository.close()
        shutil.rmtree(self.tmppath)

    def reopen(self):
        if self.repository:
            self.repository.close()
        self.repository = self.open()


class RepositoryTestCase(RepositoryTestCaseBase):

    def test1(self):
        for x in range(100):
            self.repository.put(('%-32d' % x).encode('ascii'), b'SOMEDATA')
        key50 = ('%-32d' % 50).encode('ascii')
        self.assert_equal(self.repository.get(key50), b'SOMEDATA')
        self.repository.delete(key50)
        self.assert_raises(Repository.DoesNotExist, lambda: self.repository.get(key50))
        self.repository.commit()
        self.repository.close()
        repository2 = self.open()
        self.assert_raises(Repository.DoesNotExist, lambda: repository2.get(key50))
        for x in range(100):
            if x == 50:
                continue
            self.assert_equal(repository2.get(('%-32d' % x).encode('ascii')), b'SOMEDATA')
        repository2.close()

    def test2(self):
        """Test multiple sequential transactions
        """
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.repository.put(b'00000000000000000000000000000001', b'foo')
        self.repository.commit()
        self.repository.delete(b'00000000000000000000000000000000')
        self.repository.put(b'00000000000000000000000000000001', b'bar')
        self.repository.commit()
        self.assert_equal(self.repository.get(b'00000000000000000000000000000001'), b'bar')

    def test_consistency(self):
        """Test cache consistency
        """
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo')
        self.repository.put(b'00000000000000000000000000000000', b'foo2')
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo2')
        self.repository.put(b'00000000000000000000000000000000', b'bar')
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'bar')
        self.repository.delete(b'00000000000000000000000000000000')
        self.assert_raises(Repository.DoesNotExist, lambda: self.repository.get(b'00000000000000000000000000000000'))

    def test_consistency2(self):
        """Test cache consistency2
        """
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo')
        self.repository.commit()
        self.repository.put(b'00000000000000000000000000000000', b'foo2')
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo2')
        self.repository.rollback()
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo')

    def test_overwrite_in_same_transaction(self):
        """Test cache consistency2
        """
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.repository.put(b'00000000000000000000000000000000', b'foo2')
        self.repository.commit()
        self.assert_equal(self.repository.get(b'00000000000000000000000000000000'), b'foo2')

    def test_single_kind_transactions(self):
        # put
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.repository.commit()
        self.repository.close()
        # replace
        self.repository = self.open()
        self.repository.put(b'00000000000000000000000000000000', b'bar')
        self.repository.commit()
        self.repository.close()
        # delete
        self.repository = self.open()
        self.repository.delete(b'00000000000000000000000000000000')
        self.repository.commit()

    def test_list(self):
        for x in range(100):
            self.repository.put(('%-32d' % x).encode('ascii'), b'SOMEDATA')
        all = self.repository.list()
        self.assert_equal(len(all), 100)
        first_half = self.repository.list(limit=50)
        self.assert_equal(len(first_half), 50)
        self.assert_equal(first_half, all[:50])
        second_half = self.repository.list(marker=first_half[-1])
        self.assert_equal(len(second_half), 50)
        self.assert_equal(second_half, all[50:])
        self.assert_equal(len(self.repository.list(limit=50)), 50)


class RepositoryCommitTestCase(RepositoryTestCaseBase):

    def add_keys(self):
        self.repository.put(b'00000000000000000000000000000000', b'foo')
        self.repository.put(b'00000000000000000000000000000001', b'bar')
        self.repository.put(b'00000000000000000000000000000003', b'bar')
        self.repository.commit()
        self.repository.put(b'00000000000000000000000000000001', b'bar2')
        self.repository.put(b'00000000000000000000000000000002', b'boo')
        self.repository.delete(b'00000000000000000000000000000003')

    def test_replay_of_missing_index(self):
        self.add_keys()
        for name in os.listdir(self.repository.path):
            if name.startswith('index.'):
                os.unlink(os.path.join(self.repository.path, name))
        self.reopen()
        self.assert_equal(len(self.repository), 3)
        self.assert_equal(self.repository.check(), True)

    def test_crash_before_compact_segments(self):
        self.add_keys()
        self.repository.compact_segments = None
        try:
            self.repository.commit()
        except TypeError:
            pass
        self.reopen()
        self.assert_equal(len(self.repository), 3)
        self.assert_equal(self.repository.check(), True)

    def test_replay_of_readonly_repository(self):
        self.add_keys()
        for name in os.listdir(self.repository.path):
            if name.startswith('index.'):
                os.unlink(os.path.join(self.repository.path, name))
        with patch.object(UpgradableLock, 'upgrade', side_effect=UpgradableLock.LockUpgradeFailed) as upgrade:
            self.reopen()
            self.assert_raises(UpgradableLock.LockUpgradeFailed, lambda: len(self.repository))
            upgrade.assert_called_once()


    def test_crash_before_write_index(self):
        self.add_keys()
        self.repository.write_index = None
        try:
            self.repository.commit()
        except TypeError:
            pass
        self.reopen()
        self.assert_equal(len(self.repository), 3)
        self.assert_equal(self.repository.check(), True)

    def test_crash_before_deleting_compacted_segments(self):
        self.add_keys()
        self.repository.io.delete_segment = None
        try:
            self.repository.commit()
        except TypeError:
            pass
        self.reopen()
        self.assert_equal(len(self.repository), 3)
        self.assert_equal(self.repository.check(), True)
        self.assert_equal(len(self.repository), 3)


class RepositoryCheckTestCase(RepositoryTestCaseBase):

    def list_indices(self):
        return [name for name in os.listdir(os.path.join(self.tmppath, 'repository')) if name.startswith('index.')]

    def check(self, repair=False, status=True):
        self.assert_equal(self.repository.check(repair=repair), status)
        # Make sure no tmp files are left behind
        self.assert_equal([name for name in os.listdir(os.path.join(self.tmppath, 'repository')) if 'tmp' in name], [], 'Found tmp files')

    def get_objects(self, *ids):
        for id_ in ids:
            self.repository.get(('%032d' % id_).encode('ascii'))

    def add_objects(self, segments):
        for ids in segments:
            for id_ in ids:
                self.repository.put(('%032d' % id_).encode('ascii'), b'data')
            self.repository.commit()

    def get_head(self):
        return sorted(int(n) for n in os.listdir(os.path.join(self.tmppath, 'repository', 'data', '0')) if n.isdigit())[-1]

    def open_index(self):
        return NSIndex(os.path.join(self.tmppath, 'repository', 'index.{}'.format(self.get_head())))

    def corrupt_object(self, id_):
        idx = self.open_index()
        segment, offset = idx[('%032d' % id_).encode('ascii')]
        with open(os.path.join(self.tmppath, 'repository', 'data', '0', str(segment)), 'r+b') as fd:
            fd.seek(offset)
            fd.write(b'BOOM')

    def delete_segment(self, segment):
        os.unlink(os.path.join(self.tmppath, 'repository', 'data', '0', str(segment)))

    def delete_index(self):
        os.unlink(os.path.join(self.tmppath, 'repository', 'index.{}'.format(self.get_head())))

    def rename_index(self, new_name):
        os.rename(os.path.join(self.tmppath, 'repository', 'index.{}'.format(self.get_head())),
                  os.path.join(self.tmppath, 'repository', new_name))

    def list_objects(self):
        return set(int(key) for key in self.repository.list())

    def test_repair_corrupted_segment(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        self.assert_equal(set([1, 2, 3, 4, 5, 6]), self.list_objects())
        self.check(status=True)
        self.corrupt_object(5)
        self.assert_raises(IntegrityError, lambda: self.get_objects(5))
        self.repository.rollback()
        # Make sure a regular check does not repair anything
        self.check(status=False)
        self.check(status=False)
        # Make sure a repair actually repairs the repo
        self.check(repair=True, status=True)
        self.get_objects(4)
        self.check(status=True)
        self.assert_equal(set([1, 2, 3, 4, 6]), self.list_objects())

    def test_repair_missing_segment(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        self.assert_equal(set([1, 2, 3, 4, 5, 6]), self.list_objects())
        self.check(status=True)
        self.delete_segment(1)
        self.repository.rollback()
        self.check(repair=True, status=True)
        self.assert_equal(set([1, 2, 3]), self.list_objects())

    def test_repair_missing_commit_segment(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        self.delete_segment(1)
        self.assert_raises(Repository.DoesNotExist, lambda: self.get_objects(4))
        self.assert_equal(set([1, 2, 3]), self.list_objects())

    def test_repair_corrupted_commit_segment(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        with open(os.path.join(self.tmppath, 'repository', 'data', '0', '1'), 'r+b') as fd:
            fd.seek(-1, os.SEEK_END)
            fd.write(b'X')
        self.assert_raises(Repository.DoesNotExist, lambda: self.get_objects(4))
        self.check(status=True)
        self.get_objects(3)
        self.assert_equal(set([1, 2, 3]), self.list_objects())

    def test_repair_no_commits(self):
        self.add_objects([[1, 2, 3]])
        with open(os.path.join(self.tmppath, 'repository', 'data', '0', '0'), 'r+b') as fd:
            fd.seek(-1, os.SEEK_END)
            fd.write(b'X')
        self.assert_raises(Repository.CheckNeeded, lambda: self.get_objects(4))
        self.check(status=False)
        self.check(status=False)
        self.assert_equal(self.list_indices(), ['index.0'])
        self.check(repair=True, status=True)
        self.assert_equal(self.list_indices(), ['index.1'])
        self.check(status=True)
        self.get_objects(3)
        self.assert_equal(set([1, 2, 3]), self.list_objects())

    def test_repair_missing_index(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        self.delete_index()
        self.check(status=True)
        self.get_objects(4)
        self.assert_equal(set([1, 2, 3, 4, 5, 6]), self.list_objects())

    def test_repair_index_too_new(self):
        self.add_objects([[1, 2, 3], [4, 5, 6]])
        self.assert_equal(self.list_indices(), ['index.1'])
        self.rename_index('index.100')
        self.check(status=True)
        self.assert_equal(self.list_indices(), ['index.1'])
        self.get_objects(4)
        self.assert_equal(set([1, 2, 3, 4, 5, 6]), self.list_objects())

    def test_crash_before_compact(self):
        self.repository.put(bytes(32), b'data')
        self.repository.put(bytes(32), b'data2')
        # Simulate a crash before compact
        with patch.object(Repository, 'compact_segments') as compact:
            self.repository.commit()
            compact.assert_called_once()
        self.reopen()
        self.check(repair=True)
        self.assert_equal(self.repository.get(bytes(32)), b'data2')


class RemoteRepositoryTestCase(RepositoryTestCase):

    def open(self, create=False):
        return RemoteRepository(Location('__testsuite__:' + os.path.join(self.tmppath, 'repository')), create=create)


class RemoteRepositoryCheckTestCase(RepositoryCheckTestCase):

    def open(self, create=False):
        return RemoteRepository(Location('__testsuite__:' + os.path.join(self.tmppath, 'repository')), create=create)

########NEW FILE########
__FILENAME__ = run
import unittest
from attic.testsuite import TestLoader


def main():
    unittest.main(testLoader=TestLoader(), defaultTest='')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = xattr
import os
import tempfile
import unittest
from attic.testsuite import AtticTestCase
from attic.xattr import is_enabled, getxattr, setxattr, listxattr

@unittest.skipUnless(is_enabled(), 'xattr not enabled on filesystem')
class XattrTestCase(AtticTestCase):

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile()
        self.symlink = os.path.join(os.path.dirname(self.tmpfile.name), 'symlink')
        os.symlink(self.tmpfile.name, self.symlink)

    def tearDown(self):
        os.unlink(self.symlink)

    def test(self):
        self.assert_equal(listxattr(self.tmpfile.name), [])
        self.assert_equal(listxattr(self.tmpfile.fileno()), [])
        self.assert_equal(listxattr(self.symlink), [])
        setxattr(self.tmpfile.name, 'user.foo', b'bar')
        setxattr(self.tmpfile.fileno(), 'user.bar', b'foo')
        self.assert_equal(set(listxattr(self.tmpfile.name)), set(['user.foo', 'user.bar']))
        self.assert_equal(set(listxattr(self.tmpfile.fileno())), set(['user.foo', 'user.bar']))
        self.assert_equal(set(listxattr(self.symlink)), set(['user.foo', 'user.bar']))
        self.assert_equal(listxattr(self.symlink, follow_symlinks=False), [])
        self.assert_equal(getxattr(self.tmpfile.name, 'user.foo'), b'bar')
        self.assert_equal(getxattr(self.tmpfile.fileno(), 'user.foo'), b'bar')
        self.assert_equal(getxattr(self.symlink, 'user.foo'), b'bar')

########NEW FILE########
__FILENAME__ = xattr
"""A basic extended attributes (xattr) implementation for Linux and MacOS X
"""
import errno
import os
import sys
import tempfile
from ctypes import CDLL, create_string_buffer, c_ssize_t, c_size_t, c_char_p, c_int, c_uint32, get_errno
from ctypes.util import find_library


def is_enabled():
    """Determine if xattr is enabled on the filesystem
    """
    with tempfile.NamedTemporaryFile() as fd:
        try:
            setxattr(fd.fileno(), 'user.name', b'value')
        except OSError:
            return False
        return getxattr(fd.fileno(), 'user.name') == b'value'


def get_all(path, follow_symlinks=True):
    try:
        return dict((name, getxattr(path, name, follow_symlinks=follow_symlinks))
                    for name in listxattr(path, follow_symlinks=follow_symlinks))
    except OSError as e:
        if e.errno in (errno.ENOTSUP, errno.EPERM):
            return {}


libc = CDLL(find_library('c'), use_errno=True)


def _check(rv, path=None):
    if rv < 0:
        raise OSError(get_errno(), path)
    return rv

if sys.platform.startswith('linux'):
    libc.llistxattr.argtypes = (c_char_p, c_char_p, c_size_t)
    libc.llistxattr.restype = c_ssize_t
    libc.flistxattr.argtypes = (c_int, c_char_p, c_size_t)
    libc.flistxattr.restype = c_ssize_t
    libc.lsetxattr.argtypes = (c_char_p, c_char_p, c_char_p, c_size_t, c_int)
    libc.lsetxattr.restype = c_int
    libc.fsetxattr.argtypes = (c_int, c_char_p, c_char_p, c_size_t, c_int)
    libc.fsetxattr.restype = c_int
    libc.lgetxattr.argtypes = (c_char_p, c_char_p, c_char_p, c_size_t)
    libc.lgetxattr.restype = c_ssize_t
    libc.fgetxattr.argtypes = (c_int, c_char_p, c_char_p, c_size_t)
    libc.fgetxattr.restype = c_ssize_t

    def listxattr(path, *, follow_symlinks=True):
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.flistxattr
        elif follow_symlinks:
            func = libc.listxattr
        else:
            func = libc.llistxattr
        n = _check(func(path, None, 0), path)
        if n == 0:
            return []
        namebuf = create_string_buffer(n)
        n2 = _check(func(path, namebuf, n), path)
        if n2 != n:
            raise Exception('listxattr failed')
        return [os.fsdecode(name) for name in namebuf.raw.split(b'\0')[:-1] if not name.startswith(b'system.posix_acl_')]

    def getxattr(path, name, *, follow_symlinks=True):
        name = os.fsencode(name)
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.fgetxattr
        elif follow_symlinks:
            func = libc.getxattr
        else:
            func = libc.lgetxattr
        n = _check(func(path, name, None, 0))
        if n == 0:
            return
        valuebuf = create_string_buffer(n)
        n2 = _check(func(path, name, valuebuf, n), path)
        if n2 != n:
            raise Exception('getxattr failed')
        return valuebuf.raw

    def setxattr(path, name, value, *, follow_symlinks=True):
        name = os.fsencode(name)
        value = os.fsencode(value)
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.fsetxattr
        elif follow_symlinks:
            func = libc.setxattr
        else:
            func = libc.lsetxattr
        _check(func(path, name, value, len(value), 0), path)

elif sys.platform == 'darwin':
    libc.listxattr.argtypes = (c_char_p, c_char_p, c_size_t, c_int)
    libc.listxattr.restype = c_ssize_t
    libc.flistxattr.argtypes = (c_int, c_char_p, c_size_t)
    libc.flistxattr.restype = c_ssize_t
    libc.setxattr.argtypes = (c_char_p, c_char_p, c_char_p, c_size_t, c_uint32, c_int)
    libc.setxattr.restype = c_int
    libc.fsetxattr.argtypes = (c_int, c_char_p, c_char_p, c_size_t, c_uint32, c_int)
    libc.fsetxattr.restype = c_int
    libc.getxattr.argtypes = (c_char_p, c_char_p, c_char_p, c_size_t, c_uint32, c_int)
    libc.getxattr.restype = c_ssize_t
    libc.fgetxattr.argtypes = (c_int, c_char_p, c_char_p, c_size_t, c_uint32, c_int)
    libc.fgetxattr.restype = c_ssize_t

    XATTR_NOFOLLOW = 0x0001

    def listxattr(path, *, follow_symlinks=True):
        func = libc.listxattr
        flags = 0
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.flistxattr
        elif not follow_symlinks:
            flags = XATTR_NOFOLLOW
        n = _check(func(path, None, 0, flags), path)
        if n == 0:
            return []
        namebuf = create_string_buffer(n)
        n2 = _check(func(path, namebuf, n, flags), path)
        if n2 != n:
            raise Exception('listxattr failed')
        return [os.fsdecode(name) for name in namebuf.raw.split(b'\0')[:-1]]

    def getxattr(path, name, *, follow_symlinks=True):
        name = os.fsencode(name)
        func = libc.getxattr
        flags = 0
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.fgetxattr
        elif not follow_symlinks:
            flags = XATTR_NOFOLLOW
        n = _check(func(path, name, None, 0, 0, flags))
        if n == 0:
            return
        valuebuf = create_string_buffer(n)
        n2 = _check(func(path, name, valuebuf, n, 0, flags), path)
        if n2 != n:
            raise Exception('getxattr failed')
        return valuebuf.raw

    def setxattr(path, name, value, *, follow_symlinks=True):
        name = os.fsencode(name)
        value = os.fsencode(value)
        func = libc.setxattr
        flags = 0
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.fsetxattr
        elif not follow_symlinks:
            flags = XATTR_NOFOLLOW
        _check(func(path, name, value, len(value), 0, flags), path)

elif sys.platform.startswith('freebsd'):
    EXTATTR_NAMESPACE_USER = 0x0001
    libc.extattr_list_fd.argtypes = (c_int, c_int, c_char_p, c_size_t)
    libc.extattr_list_fd.restype = c_ssize_t
    libc.extattr_list_link.argtypes = (c_char_p, c_int, c_char_p, c_size_t)
    libc.extattr_list_link.restype = c_ssize_t
    libc.extattr_list_file.argtypes = (c_char_p, c_int, c_char_p, c_size_t)
    libc.extattr_list_file.restype = c_ssize_t
    libc.extattr_get_fd.argtypes = (c_int, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_get_fd.restype = c_ssize_t
    libc.extattr_get_link.argtypes = (c_char_p, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_get_link.restype = c_ssize_t
    libc.extattr_get_file.argtypes = (c_char_p, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_get_file.restype = c_ssize_t
    libc.extattr_set_fd.argtypes = (c_int, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_set_fd.restype = c_int
    libc.extattr_set_link.argtypes = (c_char_p, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_set_link.restype = c_int
    libc.extattr_set_file.argtypes = (c_char_p, c_int, c_char_p, c_char_p, c_size_t)
    libc.extattr_set_file.restype = c_int

    def listxattr(path, *, follow_symlinks=True):
        ns = EXTATTR_NAMESPACE_USER
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.extattr_list_fd
        elif follow_symlinks:
            func = libc.extattr_list_file
        else:
            func = libc.extattr_list_link
        n = _check(func(path, ns, None, 0), path)
        if n == 0:
            return []
        namebuf = create_string_buffer(n)
        n2 = _check(func(path, ns, namebuf, n), path)
        if n2 != n:
            raise Exception('listxattr failed')
        names = []
        mv = memoryview(namebuf.raw)
        while mv:
            length = mv[0]
            # Python < 3.3 returns bytes instead of int
            if isinstance(length, bytes):
                length = ord(length)
            names.append(os.fsdecode(bytes(mv[1:1+length])))
            mv = mv[1+length:]
        return names

    def getxattr(path, name, *, follow_symlinks=True):
        name = os.fsencode(name)
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.extattr_get_fd
        elif follow_symlinks:
            func = libc.extattr_get_file
        else:
            func = libc.extattr_get_link
        n = _check(func(path, EXTATTR_NAMESPACE_USER, name, None, 0))
        if n == 0:
            return
        valuebuf = create_string_buffer(n)
        n2 = _check(func(path, EXTATTR_NAMESPACE_USER, name, valuebuf, n), path)
        if n2 != n:
            raise Exception('getxattr failed')
        return valuebuf.raw

    def setxattr(path, name, value, *, follow_symlinks=True):
        name = os.fsencode(name)
        value = os.fsencode(value)
        if isinstance(path, str):
            path = os.fsencode(path)
        if isinstance(path, int):
            func = libc.extattr_set_fd
        elif follow_symlinks:
            func = libc.extattr_set_file
        else:
            func = libc.extattr_set_link
        _check(func(path, EXTATTR_NAMESPACE_USER, name, value, len(value)), path)

else:
    raise Exception('Unsupported platform: %s' % sys.platform)

########NEW FILE########
__FILENAME__ = _version

IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.cmd"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "Attic-"
versionfile_source = "attic/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Attic documentation build configuration file, created by
# sphinx-quickstart on Sat Sep 10 18:18:25 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, attic

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Attic - Deduplicating Archiver'
copyright = '2010-2014, Jonas Borgström'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = attic.__version__.split('-')[0]
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'attic'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index': ['sidebarlogo.html', 'sidebarusefullinks.html', 'searchbox.html'],
    '**': ['sidebarlogo.html', 'localtoc.html', 'relations.html', 'sidebarusefullinks.html', 'searchbox.html']
}
# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'atticdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Attic.tex', 'Attic Documentation',
   'Jonas Borgström', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
#man_pages = [
#    ('man', 'attic', 'Attic',
#     ['Jonas Borgström'], 1)
#]

########NEW FILE########
__FILENAME__ = versioneer
"""versioneer.py

(like a rocketeer, but for versions)

* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Version: 0.7+

This file helps distutils-based projects manage their version number by just
creating version-control tags.

For developers who work from a VCS-generated tree (e.g. 'git clone' etc),
each 'setup.py version', 'setup.py build', 'setup.py sdist' will compute a
version number by asking your version-control tool about the current
checkout. The version number will be written into a generated _version.py
file of your choosing, where it can be included by your __init__.py

For users who work from a VCS-generated tarball (e.g. 'git archive'), it will
compute a version number by looking at the name of the directory created when
te tarball is unpacked. This conventionally includes both the name of the
project and a version number.

For users who work from a tarball built by 'setup.py sdist', it will get a
version number from a previously-generated _version.py file.

As a result, loading code directly from the source tree will not result in a
real version. If you want real versions from VCS trees (where you frequently
update from the upstream repository, or do new development), you will need to
do a 'setup.py version' after each update, and load code from the build/
directory.

You need to provide this code with a few configuration values:

 versionfile_source:
    A project-relative pathname into which the generated version strings
    should be written. This is usually a _version.py next to your project's
    main __init__.py file. If your project uses src/myproject/__init__.py,
    this should be 'src/myproject/_version.py'. This file should be checked
    in to your VCS as usual: the copy created below by 'setup.py
    update_files' will include code that parses expanded VCS keywords in
    generated tarballs. The 'build' and 'sdist' commands will replace it with
    a copy that has just the calculated version string.

 versionfile_build:
    Like versionfile_source, but relative to the build directory instead of
    the source directory. These will differ when your setup.py uses
    'package_dir='. If you have package_dir={'myproject': 'src/myproject'},
    then you will probably have versionfile_build='myproject/_version.py' and
    versionfile_source='src/myproject/_version.py'.

 tag_prefix: a string, like 'PROJECTNAME-', which appears at the start of all
             VCS tags. If your tags look like 'myproject-1.2.0', then you
             should use tag_prefix='myproject-'. If you use unprefixed tags
             like '1.2.0', this should be an empty string.

 parentdir_prefix: a string, frequently the same as tag_prefix, which
                   appears at the start of all unpacked tarball filenames. If
                   your tarball unpacks into 'myproject-1.2.0', this should
                   be 'myproject-'.

To use it:

 1: include this file in the top level of your project
 2: make the following changes to the top of your setup.py:
     import versioneer
     versioneer.versionfile_source = 'src/myproject/_version.py'
     versioneer.versionfile_build = 'myproject/_version.py'
     versioneer.tag_prefix = '' # tags are like 1.2.0
     versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'
 3: add the following arguments to the setup() call in your setup.py:
     version=versioneer.get_version(),
     cmdclass=versioneer.get_cmdclass(),
 4: run 'setup.py update_files', which will create _version.py, and will
    append the following to your __init__.py:
     from _version import __version__
 5: modify your MANIFEST.in to include versioneer.py
 6: add both versioneer.py and the generated _version.py to your VCS
"""

import os, sys, re
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"
IN_LONG_VERSION_PY = False


LONG_VERSION_PY = '''
IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %%s" %% args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%%s', no digits" %% ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %%d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %%s" %% ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.cmd"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver

'''


import subprocess
import sys

def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        for line in open(versionfile_source,"r").readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    for ref in list(refs):
        if not re.search(r'\d', ref):
            if verbose:
                print("discarding '%s', no digits" % ref)
            refs.discard(ref)
            # Assume all version tags have a digit. git's %d expansion
            # behaves like git log --decorate=short and strips out the
            # refs/heads/ and refs/tags/ prefixes that would let us
            # distinguish between branches and tags. By ignoring refnames
            # without digits, we filter out many common branch names like
            # "release" and "stabilization", as well as "HEAD" and "master".
    if verbose:
        print("remaining refs: %s" % ",".join(sorted(refs)))
    for ref in sorted(refs):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {} # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(here)
    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.cmd"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source, verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {} # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

import sys

def do_vcs_install(versionfile_source, ipy):
    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.cmd"
    run_command([GIT, "add", "versioneer.py"])
    run_command([GIT, "add", versionfile_source])
    run_command([GIT, "add", ipy])
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass    
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        run_command([GIT, "add", ".gitattributes"])
    

SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.7+) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))


def get_best_versions(versionfile, tag_prefix, parentdir_prefix,
                      default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    #
    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_source)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile, ver))
        return ver

    ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, versionfile_source, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_versions(default=DEFAULT, verbose=False):
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    return get_best_versions(versionfile_source, tag_prefix, parentdir_prefix,
                             default=default, verbose=verbose)
def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run2(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "modify __init__.py and create _version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)
        do_vcs_install(versionfile_source, ipy)

def get_cmdclass():
    return {'version': cmd_version,
            'update_files': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }

########NEW FILE########
