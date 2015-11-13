__FILENAME__ = decoders
# Copyright (c) 2013 Blizzard Entertainment
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

import struct


class TruncatedError(Exception):
    pass


class CorruptedError(Exception):
    pass


class BitPackedBuffer:
    def __init__(self, contents, endian='big'):
        self._data = contents or []
        self._used = 0
        self._next = None
        self._nextbits = 0
        self._bigendian = (endian == 'big')

    def __str__(self):
        return 'buffer(%02x/%d,[%d]=%s)' % (
            self._nextbits and self._next or 0, self._nextbits,
            self._used, '%02x' % (ord(self._data[self._used]),) if (self._used < len(self._data)) else '--')

    def done(self):
        return self._nextbits == 0 and self._used >= len(self._data)

    def used_bits(self):
        return self._used * 8 - self._nextbits

    def byte_align(self):
        self._nextbits = 0

    def read_aligned_bytes(self, bytes):
        self.byte_align()
        data = self._data[self._used:self._used + bytes]
        self._used += bytes
        if len(data) != bytes:
            raise TruncatedError(self)
        return data

    def read_bits(self, bits):
        result = 0
        resultbits = 0
        while resultbits != bits:
            if self._nextbits == 0:
                if self.done():
                    raise TruncatedError(self)
                self._next = ord(self._data[self._used])
                self._used += 1
                self._nextbits = 8
            copybits = min(bits - resultbits, self._nextbits)
            copy = (self._next & ((1 << copybits) - 1))
            if self._bigendian:
                result |= copy << (bits - resultbits - copybits)
            else:
                result |= copy << resultbits
            self._next >>= copybits
            self._nextbits -= copybits
            resultbits += copybits
        return result

    def read_unaligned_bytes(self, bytes):
        return ''.join([chr(self.read_bits(8)) for i in xrange(bytes)])


class BitPackedDecoder:
    def __init__(self, contents, typeinfos):
        self._buffer = BitPackedBuffer(contents)
        self._typeinfos = typeinfos

    def __str__(self):
        return self._buffer.__str__()

    def instance(self, typeid):
        if typeid >= len(self._typeinfos):
            raise CorruptedError(self)
        typeinfo = self._typeinfos[typeid]
        return getattr(self, typeinfo[0])(*typeinfo[1])

    def byte_align(self):
        self._buffer.byte_align()

    def done(self):
        return self._buffer.done()

    def used_bits(self):
        return self._buffer.used_bits()

    def _array(self, bounds, typeid):
        length = self._int(bounds)
        return [self.instance(typeid) for i in xrange(length)]

    def _bitarray(self, bounds):
        length = self._int(bounds)
        return (length, self._buffer.read_bits(length))

    def _blob(self, bounds):
        length = self._int(bounds)
        result = self._buffer.read_aligned_bytes(length)
        return result

    def _bool(self):
        return self._int((0, 1)) != 0

    def _choice(self, bounds, fields):
        tag = self._int(bounds)
        if tag not in fields:
            raise CorruptedError(self)
        field = fields[tag]
        return {field[0]: self.instance(field[1])}

    def _fourcc(self):
        return self._buffer.read_unaligned_bytes(4)

    def _int(self, bounds):
        return bounds[0] + self._buffer.read_bits(bounds[1])

    def _null(self):
        return None

    def _optional(self, typeid):
        exists = self._bool()
        return self.instance(typeid) if exists else None

    def _real32(self):
        return struct.unpack('>f', self._buffer.read_unaligned_bytes(4))

    def _real64(self):
        return struct.unpack('>d', self._buffer.read_unaligned_bytes(8))

    def _struct(self, fields):
        result = {}
        for field in fields:
            if field[0] == '__parent':
                parent = self.instance(field[1])
                if isinstance(parent, dict):
                    result.update(parent)
                elif len(fields) == 1:
                    result = parent
                else:
                    result[field[0]] = parent
            else:
                result[field[0]] = self.instance(field[1])
        return result


class VersionedDecoder:
    def __init__(self, contents, typeinfos):
        self._buffer = BitPackedBuffer(contents)
        self._typeinfos = typeinfos

    def __str__(self):
        return self._buffer.__str__()

    def instance(self, typeid):
        if typeid >= len(self._typeinfos):
            raise CorruptedError(self)
        typeinfo = self._typeinfos[typeid]
        return getattr(self, typeinfo[0])(*typeinfo[1])

    def byte_align(self):
        self._buffer.byte_align()

    def done(self):
        return self._buffer.done()

    def used_bits(self):
        return self._buffer.used_bits()

    def _expect_skip(self, expected):
        if self._buffer.read_bits(8) != expected:
            raise CorruptedError(self)

    def _vint(self):
        b = self._buffer.read_bits(8)
        negative = b & 1
        result = (b >> 1) & 0x3f
        bits = 6
        while (b & 0x80) != 0:
            b = self._buffer.read_bits(8)
            result |= (b & 0x7f) << bits
            bits += 7
        return -result if negative else result

    def _array(self, bounds, typeid):
        self._expect_skip(0)
        length = self._vint()
        return [self.instance(typeid) for i in xrange(length)]

    def _bitarray(self, bounds):
        self._expect_skip(1)
        length = self._vint()
        return (length, self._buffer.read_aligned_bytes((length + 7) / 8))

    def _blob(self, bounds):
        self._expect_skip(2)
        length = self._vint()
        return self._buffer.read_aligned_bytes(length)

    def _bool(self):
        self._expect_skip(6)
        return self._buffer.read_bits(8) != 0

    def _choice(self, bounds, fields):
        self._expect_skip(3)
        tag = self._vint()
        if tag not in fields:
            self._skip_instance()
            return {}
        field = fields[tag]
        return {field[0]: self.instance(field[1])}

    def _fourcc(self):
        self._expect_skip(7)
        return self._buffer.read_aligned_bytes(4)

    def _int(self, bounds):
        self._expect_skip(9)
        return self._vint()

    def _null(self):
        return None

    def _optional(self, typeid):
        self._expect_skip(4)
        exists = self._buffer.read_bits(8) != 0
        return self.instance(typeid) if exists else None

    def _real32(self):
        self._expect_skip(7)
        return struct.unpack('>f', self._buffer.read_aligned_bytes(4))

    def _real64(self):
        self._expect_skip(8)
        return struct.unpack('>d', self._buffer.read_aligned_bytes(8))

    def _struct(self, fields):
        self._expect_skip(5)
        result = {}
        length = self._vint()
        for i in xrange(length):
            tag = self._vint()
            field = next((f for f in fields if f[2] == tag), None)
            if field:
                if field[0] == '__parent':
                    parent = self.instance(field[1])
                    if isinstance(parent, dict):
                        result.update(parent)
                    elif len(fields) == 1:
                        result = parent
                    else:
                        result[field[0]] = parent
                else:
                    result[field[0]] = self.instance(field[1])
            else:
                self._skip_instance()
        return result

    def _skip_instance(self):
        skip = self._buffer.read_bits(8)
        if skip == 0:  # array
            length = self._vint()
            for i in xrange(length):
                self._skip_instance()
        elif skip == 1:  # bitblob
            length = self._vint()
            self._buffer.read_aligned_bytes((length + 7) / 8)
        elif skip == 2:  # blob
            length = self._vint()
            self._buffer.read_aligned_bytes(length)
        elif skip == 3:  # choice
            tag = self._vint()
            self._skip_instance()
        elif skip == 4:  # optional
            exists = self._buffer.read_bits(8) != 0
            if exists:
                self._skip_instance()
        elif skip == 5:  # struct
            length = self._vint()
            for i in xrange(length):
                tag = self._vint()
                self._skip_instance()
        elif skip == 6:  # u8
            self._buffer.read_aligned_bytes(1)
        elif skip == 7:  # u32
            self._buffer.read_aligned_bytes(4)
        elif skip == 8:  # u64
            self._buffer.read_aligned_bytes(8)
        elif skip == 9:  # vint
            self._vint()

########NEW FILE########
__FILENAME__ = mpyq
#!/usr/bin/env python
# coding: utf-8

"""
mpyq is a Python library for reading MPQ (MoPaQ) archives.
"""

import bz2
import cStringIO
import os
import struct
import zlib
from collections import namedtuple


__author__ = "Aku Kotkavuo"
__version__ = "0.2.0"


MPQ_FILE_IMPLODE        = 0x00000100
MPQ_FILE_COMPRESS       = 0x00000200
MPQ_FILE_ENCRYPTED      = 0x00010000
MPQ_FILE_FIX_KEY        = 0x00020000
MPQ_FILE_SINGLE_UNIT    = 0x01000000
MPQ_FILE_DELETE_MARKER  = 0x02000000
MPQ_FILE_SECTOR_CRC     = 0x04000000
MPQ_FILE_EXISTS         = 0x80000000

MPQFileHeader = namedtuple('MPQFileHeader',
    '''
    magic
    header_size
    archive_size
    format_version
    sector_size_shift
    hash_table_offset
    block_table_offset
    hash_table_entries
    block_table_entries
    '''
)
MPQFileHeader.struct_format = '<4s2I2H4I'

MPQFileHeaderExt = namedtuple('MPQFileHeaderExt',
    '''
    extended_block_table_offset
    hash_table_offset_high
    block_table_offset_high
    '''
)
MPQFileHeaderExt.struct_format = 'q2h'

MPQUserDataHeader = namedtuple('MPQUserDataHeader',
    '''
    magic
    user_data_size
    mpq_header_offset
    user_data_header_size
    '''
)
MPQUserDataHeader.struct_format = '<4s3I'

MPQHashTableEntry = namedtuple('MPQHashTableEntry',
    '''
    hash_a
    hash_b
    locale
    platform
    block_table_index
    '''
)
MPQHashTableEntry.struct_format = '2I2HI'

MPQBlockTableEntry = namedtuple('MPQBlockTableEntry',
    '''
    offset
    archived_size
    size
    flags
    '''
)
MPQBlockTableEntry.struct_format = '4I'


class MPQArchive(object):

    def __init__(self, filename, listfile=True):
        """Create a MPQArchive object.

        You can skip reading the listfile if you pass listfile=False
        to the constructor. The 'files' attribute will be unavailable
        if you do this.
        """
        if hasattr(filename, 'read'):
            self.file = filename
        else:
            self.file = open(filename, 'rb')
        self.header = self.read_header()
        self.hash_table = self.read_table('hash')
        self.block_table = self.read_table('block')
        if listfile:
            self.files = self.read_file('(listfile)').splitlines()
        else:
            self.files = None

    def read_header(self):
        """Read the header of a MPQ archive."""

        def read_mpq_header(offset=None):
            if offset:
                self.file.seek(offset)
            data = self.file.read(32)
            header = MPQFileHeader._make(
                struct.unpack(MPQFileHeader.struct_format, data))
            header = header._asdict()
            if header['format_version'] == 1:
                data = self.file.read(12)
                extended_header = MPQFileHeaderExt._make(
                    struct.unpack(MPQFileHeaderExt.struct_format, data))
                header.update(extended_header._asdict())
            return header

        def read_mpq_user_data_header():
            data = self.file.read(16)
            header = MPQUserDataHeader._make(
                struct.unpack(MPQUserDataHeader.struct_format, data))
            header = header._asdict()
            header['content'] = self.file.read(header['user_data_header_size'])
            return header

        magic = self.file.read(4)
        self.file.seek(0)

        if magic == 'MPQ\x1a':
            header = read_mpq_header()
            header['offset'] = 0
        elif magic == 'MPQ\x1b':
            user_data_header = read_mpq_user_data_header()
            header = read_mpq_header(user_data_header['mpq_header_offset'])
            header['offset'] = user_data_header['mpq_header_offset']
            header['user_data_header'] = user_data_header

        return header

    def read_table(self, table_type):
        """Read either the hash or block table of a MPQ archive."""

        if table_type == 'hash':
            entry_class = MPQHashTableEntry
        elif table_type == 'block':
            entry_class = MPQBlockTableEntry
        else:
            raise ValueError("Invalid table type.")

        table_offset = self.header['%s_table_offset' % table_type]
        table_entries = self.header['%s_table_entries' % table_type]
        key = self._hash('(%s table)' % table_type, 'TABLE')

        self.file.seek(table_offset + self.header['offset'])
        data = self.file.read(table_entries * 16)
        data = self._decrypt(data, key)

        def unpack_entry(position):
            entry_data = data[position*16:position*16+16]
            return entry_class._make(
                struct.unpack(entry_class.struct_format, entry_data))

        return [unpack_entry(i) for i in range(table_entries)]

    def get_hash_table_entry(self, filename):
        """Get the hash table entry corresponding to a given filename."""
        hash_a = self._hash(filename, 'HASH_A')
        hash_b = self._hash(filename, 'HASH_B')
        for entry in self.hash_table:
            if (entry.hash_a == hash_a and entry.hash_b == hash_b):
                return entry

    def read_file(self, filename, force_decompress=False):
        """Read a file from the MPQ archive."""

        def decompress(data):
            """Read the compression type and decompress file data."""
            compression_type = ord(data[0])
            if compression_type == 0:
                return data
            elif compression_type == 2:
                return zlib.decompress(data[1:], 15)
            elif compression_type == 16:
                return bz2.decompress(data[1:])
            else:
                raise RuntimeError("Unsupported compression type.")

        hash_entry = self.get_hash_table_entry(filename)
        if hash_entry is None:
            return None
        block_entry = self.block_table[hash_entry.block_table_index]

        # Read the block.
        if block_entry.flags & MPQ_FILE_EXISTS:
            if block_entry.archived_size == 0:
                return None

            offset = block_entry.offset + self.header['offset']
            self.file.seek(offset)
            file_data = self.file.read(block_entry.archived_size)

            if block_entry.flags & MPQ_FILE_ENCRYPTED:
                raise NotImplementedError("Encryption is not supported yet.")

            if not block_entry.flags & MPQ_FILE_SINGLE_UNIT:
                # File consist of many sectors. They all need to be
                # decompressed separately and united.
                sector_size = 512 << self.header['sector_size_shift']
                sectors = block_entry.size / sector_size + 1
                if block_entry.flags & MPQ_FILE_SECTOR_CRC:
                    crc = True
                    sectors += 1
                else:
                    crc = False
                positions = struct.unpack('<%dI' % (sectors + 1),
                                          file_data[:4*(sectors+1)])
                result = cStringIO.StringIO()
                for i in range(len(positions) - (2 if crc else 1)):
                    sector = file_data[positions[i]:positions[i+1]]
                    if (block_entry.flags & MPQ_FILE_COMPRESS and
                        (force_decompress or block_entry.size > block_entry.archived_size)):
                        sector = decompress(sector)
                    result.write(sector)
                file_data = result.getvalue()
            else:
                # Single unit files only need to be decompressed, but
                # compression only happens when at least one byte is gained.
                if (block_entry.flags & MPQ_FILE_COMPRESS and
                    (force_decompress or block_entry.size > block_entry.archived_size)):
                    file_data = decompress(file_data)

            return file_data

    def extract(self):
        """Extract all the files inside the MPQ archive in memory."""
        if self.files:
            return dict((f, self.read_file(f)) for f in self.files)
        else:
            raise RuntimeError("Can't extract whole archive without listfile.")

    def extract_to_disk(self):
        """Extract all files and write them to disk."""
        archive_name, extension = os.path.splitext(os.path.basename(self.file.name))
        if not os.path.isdir(os.path.join(os.getcwd(), archive_name)):
            os.mkdir(archive_name)
        os.chdir(archive_name)
        for filename, data in self.extract().items():
            f = open(filename, 'wb')
            f.write(data)
            f.close()

    def extract_files(self, *filenames):
        """Extract given files from the archive to disk."""
        for filename in filenames:
            data = self.read_file(filename)
            f = open(filename, 'wb')
            f.write(data)
            f.close()

    def print_headers(self):
        print "MPQ archive header"
        print "------------------"
        for key, value in self.header.iteritems():
            if key == "user_data_header":
                continue
            print "{0:30} {1!r}".format(key, value)
        if self.header.get('user_data_header'):
            print
            print "MPQ user data header"
            print "--------------------"
            for key, value in self.header['user_data_header'].iteritems():
                print "{0:30} {1!r}".format(key, value)
        print

    def print_hash_table(self):
        print "MPQ archive hash table"
        print "----------------------"
        print " Hash A   Hash B  Locl Plat BlockIdx"
        for entry in self.hash_table:
            print '%08X %08X %04X %04X %08X' % entry
        print

    def print_block_table(self):
        print "MPQ archive block table"
        print "-----------------------"
        print " Offset  ArchSize RealSize  Flags"
        for entry in self.block_table:
            print '%08X %8d %8d %8X' % entry
        print

    def print_files(self):
        if self.files:
            print "Files"
            print "-----"
            width = max(len(name) for name in self.files) + 2
            for filename in self.files:
                hash_entry = self.get_hash_table_entry(filename)
                block_entry = self.block_table[hash_entry.block_table_index]
                print "{0:{width}} {1:>8} bytes".format(filename,
                                                        block_entry.size,
                                                        width=width)

    def _hash(self, string, hash_type):
        """Hash a string using MPQ's hash function."""
        hash_types = {
            'TABLE_OFFSET': 0,
            'HASH_A': 1,
            'HASH_B': 2,
            'TABLE': 3
        }
        seed1 = 0x7FED7FED
        seed2 = 0xEEEEEEEE

        for ch in string:
            ch = ord(ch.upper())
            value = self.encryption_table[(hash_types[hash_type] << 8) + ch]
            seed1 = (value ^ (seed1 + seed2)) & 0xFFFFFFFF
            seed2 = ch + seed1 + seed2 + (seed2 << 5) + 3 & 0xFFFFFFFF

        return seed1

    def _decrypt(self, data, key):
        """Decrypt hash or block table or a sector."""
        seed1 = key
        seed2 = 0xEEEEEEEE
        result = cStringIO.StringIO()

        for i in range(len(data) // 4):
            seed2 += self.encryption_table[0x400 + (seed1 & 0xFF)]
            seed2 &= 0xFFFFFFFF
            value = struct.unpack("<I", data[i*4:i*4+4])[0]
            value = (value ^ (seed1 + seed2)) & 0xFFFFFFFF

            seed1 = ((~seed1 << 0x15) + 0x11111111) | (seed1 >> 0x0B)
            seed1 &= 0xFFFFFFFF
            seed2 = value + seed2 + (seed2 << 5) + 3 & 0xFFFFFFFF

            result.write(struct.pack("<I", value))

        return result.getvalue()

    def _prepare_encryption_table():
        """Prepare encryption table for MPQ hash function."""
        seed = 0x00100001
        crypt_table = {}

        for i in range(256):
            index = i
            for j in range(5):
                seed = (seed * 125 + 3) % 0x2AAAAB
                temp1 = (seed & 0xFFFF) << 0x10

                seed = (seed * 125 + 3) % 0x2AAAAB
                temp2 = (seed & 0xFFFF)

                crypt_table[index] = (temp1 | temp2)

                index += 0x100

        return crypt_table

    encryption_table = _prepare_encryption_table()


def main():
    import argparse
    description = "mpyq reads and extracts MPQ archives."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("file", action="store", help="path to the archive")
    parser.add_argument("-I", "--headers", action="store_true", dest="headers",
                        help="print header information from the archive")
    parser.add_argument("-H", "--hash-table", action="store_true",
                        dest="hash_table", help="print hash table"),
    parser.add_argument("-b", "--block-table", action="store_true",
                        dest="block_table", help="print block table"),
    parser.add_argument("-s", "--skip-listfile", action="store_true",
                        dest="skip_listfile", help="skip reading (listfile)"),
    parser.add_argument("-t", "--list-files", action="store_true", dest="list",
                        help="list files inside the archive")
    parser.add_argument("-x", "--extract", action="store_true", dest="extract",
                        help="extract files from the archive")
    args = parser.parse_args()
    if args.file:
        if not args.skip_listfile:
            archive = MPQArchive(args.file)
        else:
            archive = MPQArchive(args.file, listfile=False)
        if args.headers:
            archive.print_headers()
        if args.hash_table:
            archive.print_hash_table()
        if args.block_table:
            archive.print_block_table()
        if args.list:
            archive.print_files()
        if args.extract:
            archive.extract_to_disk()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = protocol15405
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_name',9,-6),('m_randomSeed',5,-5),('m_racePreference',34,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #35
    ('_array',[(0,5),35]),  #36
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #37
    ('_int',[(1,4)]),  #38
    ('_int',[(1,5)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',37,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',38,-15),('m_maxColors',39,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-9),('m_userId',47,-8),('m_teamId',1,-7),('m_colorPref',49,-6),('m_racePref',34,-5),('m_difficulty',2,-4),('m_handicap',0,-3),('m_observe',19,-2),('m_rewards',50,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',36,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #61
    ('_struct',[[]]),  #62
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #63
    ('_int',[(-2147483648,32)]),  #64
    ('_struct',[[('x',64,-2),('y',64,-1)]]),  #65
    ('_struct',[[('m_point',65,-4),('m_time',64,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #66
    ('_struct',[[('m_data',66,-1)]]),  #67
    ('_int',[(0,16)]),  #68
    ('_struct',[[('x',64,-3),('y',64,-2),('z',64,-1)]]),  #69
    ('_struct',[[('m_cmdFlags',5,-11),('m_abilLink',68,-10),('m_abilCmdIndex',10,-9),('m_abilCmdData',10,-8),('m_targetUnitFlags',10,-7),('m_targetUnitTimer',10,-6),('m_otherUnit',5,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',68,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',69,-1)]]),  #70
    ('_struct',[[('__parent',42,-1)]]),  #71
    ('_struct',[[('m_unitLink',68,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #72
    ('_array',[(0,8),72]),  #73
    ('_array',[(0,8),5]),  #74
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',71,-3),('m_addSubgroups',73,-2),('m_addUnitTags',74,-1)]]),  #75
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',75,-1)]]),  #76
    ('_optional',[71]),  #77
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',77,-1)]]),  #78
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #79
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',79,-1)]]),  #80
    ('_array',[(0,3),64]),  #81
    ('_struct',[[('m_recipientId',1,-2),('m_resources',81,-1)]]),  #82
    ('_struct',[[('m_chatMessage',23,-1)]]),  #83
    ('_int',[(-128,8)]),  #84
    ('_struct',[[('m_beacon',84,-7),('m_ally',84,-6),('m_autocast',84,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',68,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',69,-1)]]),  #85
    ('_struct',[[('m_speed',12,-1)]]),  #86
    ('_struct',[[('m_delta',84,-1)]]),  #87
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #88
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #89
    ('_struct',[[('m_unitTag',5,-1)]]),  #90
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #91
    ('_struct',[[('m_conversationId',64,-2),('m_replyId',64,-1)]]),  #92
    ('_struct',[[('m_purchaseItemId',64,-1)]]),  #93
    ('_struct',[[('m_difficultyLevel',64,-1)]]),  #94
    ('_null',[]),  #95
    ('_choice',[(0,3),{0:('None',95),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',64),4:('TextChanged',24)}]),  #96
    ('_struct',[[('m_controlId',64,-3),('m_eventType',64,-2),('m_eventData',96,-1)]]),  #97
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #98
    ('_struct',[[('m_soundHash',74,-2),('m_length',74,-1)]]),  #99
    ('_struct',[[('m_syncInfo',99,-1)]]),  #100
    ('_struct',[[('m_sound',5,-1)]]),  #101
    ('_struct',[[('m_transmissionId',64,-1)]]),  #102
    ('_struct',[[('x',68,-2),('y',68,-1)]]),  #103
    ('_optional',[68]),  #104
    ('_struct',[[('m_target',103,-4),('m_distance',104,-3),('m_pitch',104,-2),('m_yaw',104,-1)]]),  #105
    ('_int',[(0,1)]),  #106
    ('_struct',[[('m_skipType',106,-1)]]),  #107
    ('_struct',[[('m_button',5,-7),('m_down',26,-6),('m_posXUI',5,-5),('m_posYUI',5,-4),('m_posXWorld',64,-3),('m_posYWorld',64,-2),('m_posZWorld',64,-1)]]),  #108
    ('_struct',[[('m_soundtrack',5,-1)]]),  #109
    ('_struct',[[('m_planetId',64,-1)]]),  #110
    ('_struct',[[('m_key',84,-2),('m_flags',84,-1)]]),  #111
    ('_struct',[[('m_resources',81,-1)]]),  #112
    ('_struct',[[('m_fulfillRequestId',64,-1)]]),  #113
    ('_struct',[[('m_cancelRequestId',64,-1)]]),  #114
    ('_struct',[[('m_researchItemId',64,-1)]]),  #115
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #116
    ('_struct',[[('m_mercenaryId',64,-1)]]),  #117
    ('_struct',[[('m_battleReportId',64,-2),('m_difficultyLevel',64,-1)]]),  #118
    ('_struct',[[('m_battleReportId',64,-1)]]),  #119
    ('_struct',[[('m_decrementMs',5,-1)]]),  #120
    ('_struct',[[('m_portraitId',64,-1)]]),  #121
    ('_struct',[[('m_functionName',15,-1)]]),  #122
    ('_struct',[[('m_result',64,-1)]]),  #123
    ('_struct',[[('m_gameMenuItemIndex',64,-1)]]),  #124
    ('_struct',[[('m_reason',84,-1)]]),  #125
    ('_struct',[[('m_purchaseCategoryId',64,-1)]]),  #126
    ('_struct',[[('m_button',68,-1)]]),  #127
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #128
    ('_struct',[[('m_recipient',19,-2),('m_point',65,-1)]]),  #129
    ('_struct',[[('m_progress',64,-1)]]),  #130
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (62, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (61, 'NNet.Game.SUserOptionsEvent'),
    22: (63, 'NNet.Game.SSaveGameEvent'),
    23: (62, 'NNet.Game.SSaveGameDoneEvent'),
    25: (62, 'NNet.Game.SPlayerLeaveEvent'),
    26: (67, 'NNet.Game.SGameCheatEvent'),
    27: (70, 'NNet.Game.SCmdEvent'),
    28: (76, 'NNet.Game.SSelectionDeltaEvent'),
    29: (78, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (80, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (82, 'NNet.Game.SResourceTradeEvent'),
    32: (83, 'NNet.Game.STriggerChatMessageEvent'),
    33: (85, 'NNet.Game.SAICommunicateEvent'),
    34: (86, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (87, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (88, 'NNet.Game.SBroadcastCheatEvent'),
    38: (89, 'NNet.Game.SAllianceEvent'),
    39: (90, 'NNet.Game.SUnitClickEvent'),
    40: (91, 'NNet.Game.SUnitHighlightEvent'),
    41: (92, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (62, 'NNet.Game.STriggerSkippedEvent'),
    45: (98, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (101, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (102, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (102, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (105, 'NNet.Game.SCameraUpdateEvent'),
    50: (62, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (93, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (62, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (94, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (62, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (97, 'NNet.Game.STriggerDialogControlEvent'),
    56: (100, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (107, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (108, 'NNet.Game.STriggerMouseClickedEvent'),
    63: (62, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (109, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (110, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (111, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (122, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (62, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (62, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (112, 'NNet.Game.SResourceRequestEvent'),
    71: (113, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (114, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (62, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (62, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (115, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (116, 'NNet.Game.SLagMessageEvent'),
    77: (62, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (62, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (117, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (62, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (62, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (118, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (119, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (119, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (94, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (62, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (62, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (120, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (121, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (123, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (124, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (125, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (93, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (126, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (127, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (62, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (128, 'NNet.Game.SChatMessage'),
    1: (129, 'NNet.Game.SPingMessage'),
    2: (130, 'NNet.Game.SLoadingProgressMessage'),
    3: (62, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol16561
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,5)]),  #40
    ('_int',[(1,8)]),  #41
    ('_bitarray',[(0,6)]),  #42
    ('_bitarray',[(0,8)]),  #43
    ('_bitarray',[(0,2)]),  #44
    ('_struct',[[('m_allowedColors',42,-5),('m_allowedRaces',43,-4),('m_allowedDifficulty',42,-3),('m_allowedControls',43,-2),('m_allowedObserveTypes',44,-1)]]),  #45
    ('_array',[(0,5),45]),  #46
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',40,-14),('m_maxRaces',41,-13),('m_maxControls',41,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',46,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #47
    ('_optional',[1]),  #48
    ('_optional',[7]),  #49
    ('_struct',[[('m_color',49,-1)]]),  #50
    ('_array',[(0,5),5]),  #51
    ('_struct',[[('m_control',10,-9),('m_userId',48,-8),('m_teamId',1,-7),('m_colorPref',50,-6),('m_racePref',34,-5),('m_difficulty',2,-4),('m_handicap',0,-3),('m_observe',19,-2),('m_rewards',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',48,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',47,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #62
    ('_struct',[[]]),  #63
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #64
    ('_int',[(-2147483648,32)]),  #65
    ('_struct',[[('x',65,-2),('y',65,-1)]]),  #66
    ('_struct',[[('m_point',66,-4),('m_time',65,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #67
    ('_struct',[[('m_data',67,-1)]]),  #68
    ('_int',[(0,17)]),  #69
    ('_int',[(0,16)]),  #70
    ('_struct',[[('m_abilLink',70,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #71
    ('_optional',[71]),  #72
    ('_null',[]),  #73
    ('_int',[(0,20)]),  #74
    ('_struct',[[('x',74,-3),('y',74,-2),('z',65,-1)]]),  #75
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',70,-3),('m_snapshotPlayerId',48,-2),('m_snapshotPoint',75,-1)]]),  #76
    ('_choice',[(0,2),{0:('None',73),1:('TargetPoint',75),2:('TargetUnit',76),3:('Data',5)}]),  #77
    ('_optional',[5]),  #78
    ('_struct',[[('m_cmdFlags',69,-4),('m_abil',72,-3),('m_data',77,-2),('m_otherUnit',78,-1)]]),  #79
    ('_array',[(0,8),10]),  #80
    ('_choice',[(0,2),{0:('None',73),1:('Mask',43),2:('OneIndices',80),3:('ZeroIndices',80)}]),  #81
    ('_struct',[[('m_unitLink',70,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #82
    ('_array',[(0,8),82]),  #83
    ('_array',[(0,8),5]),  #84
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',81,-3),('m_addSubgroups',83,-2),('m_addUnitTags',84,-1)]]),  #85
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',81,-1)]]),  #87
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #88
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',88,-1)]]),  #89
    ('_array',[(0,3),65]),  #90
    ('_struct',[[('m_recipientId',1,-2),('m_resources',90,-1)]]),  #91
    ('_struct',[[('m_chatMessage',23,-1)]]),  #92
    ('_int',[(-128,8)]),  #93
    ('_struct',[[('x',65,-3),('y',65,-2),('z',65,-1)]]),  #94
    ('_struct',[[('m_beacon',93,-7),('m_ally',93,-6),('m_autocast',93,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',70,-3),('m_targetUnitSnapshotPlayerId',48,-2),('m_targetPoint',94,-1)]]),  #95
    ('_struct',[[('m_speed',12,-1)]]),  #96
    ('_struct',[[('m_delta',93,-1)]]),  #97
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #98
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #99
    ('_struct',[[('m_unitTag',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #101
    ('_struct',[[('m_conversationId',65,-2),('m_replyId',65,-1)]]),  #102
    ('_struct',[[('m_purchaseItemId',65,-1)]]),  #103
    ('_struct',[[('m_difficultyLevel',65,-1)]]),  #104
    ('_choice',[(0,3),{0:('None',73),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',65),4:('TextChanged',24)}]),  #105
    ('_struct',[[('m_controlId',65,-3),('m_eventType',65,-2),('m_eventData',105,-1)]]),  #106
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #107
    ('_struct',[[('m_soundHash',84,-2),('m_length',84,-1)]]),  #108
    ('_struct',[[('m_syncInfo',108,-1)]]),  #109
    ('_struct',[[('m_sound',5,-1)]]),  #110
    ('_struct',[[('m_transmissionId',65,-1)]]),  #111
    ('_struct',[[('x',70,-2),('y',70,-1)]]),  #112
    ('_optional',[70]),  #113
    ('_struct',[[('m_target',112,-4),('m_distance',113,-3),('m_pitch',113,-2),('m_yaw',113,-1)]]),  #114
    ('_int',[(0,1)]),  #115
    ('_struct',[[('m_skipType',115,-1)]]),  #116
    ('_struct',[[('m_button',5,-7),('m_down',26,-6),('m_posXUI',5,-5),('m_posYUI',5,-4),('m_posXWorld',65,-3),('m_posYWorld',65,-2),('m_posZWorld',65,-1)]]),  #117
    ('_struct',[[('m_soundtrack',5,-1)]]),  #118
    ('_struct',[[('m_planetId',65,-1)]]),  #119
    ('_struct',[[('m_key',93,-2),('m_flags',93,-1)]]),  #120
    ('_struct',[[('m_resources',90,-1)]]),  #121
    ('_struct',[[('m_fulfillRequestId',65,-1)]]),  #122
    ('_struct',[[('m_cancelRequestId',65,-1)]]),  #123
    ('_struct',[[('m_researchItemId',65,-1)]]),  #124
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #125
    ('_struct',[[('m_mercenaryId',65,-1)]]),  #126
    ('_struct',[[('m_battleReportId',65,-2),('m_difficultyLevel',65,-1)]]),  #127
    ('_struct',[[('m_battleReportId',65,-1)]]),  #128
    ('_int',[(0,19)]),  #129
    ('_struct',[[('m_decrementMs',129,-1)]]),  #130
    ('_struct',[[('m_portraitId',65,-1)]]),  #131
    ('_struct',[[('m_functionName',15,-1)]]),  #132
    ('_struct',[[('m_result',65,-1)]]),  #133
    ('_struct',[[('m_gameMenuItemIndex',65,-1)]]),  #134
    ('_struct',[[('m_reason',93,-1)]]),  #135
    ('_struct',[[('m_purchaseCategoryId',65,-1)]]),  #136
    ('_struct',[[('m_button',70,-1)]]),  #137
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #138
    ('_struct',[[('m_recipient',19,-2),('m_point',66,-1)]]),  #139
    ('_struct',[[('m_progress',65,-1)]]),  #140
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (63, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SUserOptionsEvent'),
    22: (64, 'NNet.Game.SSaveGameEvent'),
    23: (63, 'NNet.Game.SSaveGameDoneEvent'),
    25: (63, 'NNet.Game.SPlayerLeaveEvent'),
    26: (68, 'NNet.Game.SGameCheatEvent'),
    27: (79, 'NNet.Game.SCmdEvent'),
    28: (86, 'NNet.Game.SSelectionDeltaEvent'),
    29: (87, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (89, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (91, 'NNet.Game.SResourceTradeEvent'),
    32: (92, 'NNet.Game.STriggerChatMessageEvent'),
    33: (95, 'NNet.Game.SAICommunicateEvent'),
    34: (96, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (97, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (98, 'NNet.Game.SBroadcastCheatEvent'),
    38: (99, 'NNet.Game.SAllianceEvent'),
    39: (100, 'NNet.Game.SUnitClickEvent'),
    40: (101, 'NNet.Game.SUnitHighlightEvent'),
    41: (102, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (63, 'NNet.Game.STriggerSkippedEvent'),
    45: (107, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (110, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (111, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (111, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (114, 'NNet.Game.SCameraUpdateEvent'),
    50: (63, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (103, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (63, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (104, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (63, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (106, 'NNet.Game.STriggerDialogControlEvent'),
    56: (109, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (116, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (117, 'NNet.Game.STriggerMouseClickedEvent'),
    63: (63, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (118, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (119, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (120, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (132, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (63, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (63, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (121, 'NNet.Game.SResourceRequestEvent'),
    71: (122, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (123, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (63, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (63, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (124, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (125, 'NNet.Game.SLagMessageEvent'),
    77: (63, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (63, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (126, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (63, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (63, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (127, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (128, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (128, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (104, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (63, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (63, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (130, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (131, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (133, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (134, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (135, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (103, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (136, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (137, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (63, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (138, 'NNet.Game.SChatMessage'),
    1: (139, 'NNet.Game.SPingMessage'),
    2: (140, 'NNet.Game.SLoadingProgressMessage'),
    3: (63, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol16605
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,5)]),  #40
    ('_int',[(1,8)]),  #41
    ('_bitarray',[(0,6)]),  #42
    ('_bitarray',[(0,8)]),  #43
    ('_bitarray',[(0,2)]),  #44
    ('_struct',[[('m_allowedColors',42,-5),('m_allowedRaces',43,-4),('m_allowedDifficulty',42,-3),('m_allowedControls',43,-2),('m_allowedObserveTypes',44,-1)]]),  #45
    ('_array',[(0,5),45]),  #46
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',40,-14),('m_maxRaces',41,-13),('m_maxControls',41,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',46,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #47
    ('_optional',[1]),  #48
    ('_optional',[7]),  #49
    ('_struct',[[('m_color',49,-1)]]),  #50
    ('_array',[(0,5),5]),  #51
    ('_struct',[[('m_control',10,-9),('m_userId',48,-8),('m_teamId',1,-7),('m_colorPref',50,-6),('m_racePref',34,-5),('m_difficulty',2,-4),('m_handicap',0,-3),('m_observe',19,-2),('m_rewards',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',48,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',47,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #62
    ('_struct',[[]]),  #63
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #64
    ('_int',[(-2147483648,32)]),  #65
    ('_struct',[[('x',65,-2),('y',65,-1)]]),  #66
    ('_struct',[[('m_point',66,-4),('m_time',65,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #67
    ('_struct',[[('m_data',67,-1)]]),  #68
    ('_int',[(0,17)]),  #69
    ('_int',[(0,16)]),  #70
    ('_struct',[[('m_abilLink',70,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #71
    ('_optional',[71]),  #72
    ('_null',[]),  #73
    ('_int',[(0,20)]),  #74
    ('_struct',[[('x',74,-3),('y',74,-2),('z',65,-1)]]),  #75
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',70,-3),('m_snapshotPlayerId',48,-2),('m_snapshotPoint',75,-1)]]),  #76
    ('_choice',[(0,2),{0:('None',73),1:('TargetPoint',75),2:('TargetUnit',76),3:('Data',5)}]),  #77
    ('_optional',[5]),  #78
    ('_struct',[[('m_cmdFlags',69,-4),('m_abil',72,-3),('m_data',77,-2),('m_otherUnit',78,-1)]]),  #79
    ('_array',[(0,8),10]),  #80
    ('_choice',[(0,2),{0:('None',73),1:('Mask',43),2:('OneIndices',80),3:('ZeroIndices',80)}]),  #81
    ('_struct',[[('m_unitLink',70,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #82
    ('_array',[(0,8),82]),  #83
    ('_array',[(0,8),5]),  #84
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',81,-3),('m_addSubgroups',83,-2),('m_addUnitTags',84,-1)]]),  #85
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',81,-1)]]),  #87
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #88
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',88,-1)]]),  #89
    ('_array',[(0,3),65]),  #90
    ('_struct',[[('m_recipientId',1,-2),('m_resources',90,-1)]]),  #91
    ('_struct',[[('m_chatMessage',23,-1)]]),  #92
    ('_int',[(-128,8)]),  #93
    ('_struct',[[('x',65,-3),('y',65,-2),('z',65,-1)]]),  #94
    ('_struct',[[('m_beacon',93,-7),('m_ally',93,-6),('m_autocast',93,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',70,-3),('m_targetUnitSnapshotPlayerId',48,-2),('m_targetPoint',94,-1)]]),  #95
    ('_struct',[[('m_speed',12,-1)]]),  #96
    ('_struct',[[('m_delta',93,-1)]]),  #97
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #98
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #99
    ('_struct',[[('m_unitTag',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #101
    ('_struct',[[('m_conversationId',65,-2),('m_replyId',65,-1)]]),  #102
    ('_struct',[[('m_purchaseItemId',65,-1)]]),  #103
    ('_struct',[[('m_difficultyLevel',65,-1)]]),  #104
    ('_choice',[(0,3),{0:('None',73),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',65),4:('TextChanged',24)}]),  #105
    ('_struct',[[('m_controlId',65,-3),('m_eventType',65,-2),('m_eventData',105,-1)]]),  #106
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #107
    ('_struct',[[('m_soundHash',84,-2),('m_length',84,-1)]]),  #108
    ('_struct',[[('m_syncInfo',108,-1)]]),  #109
    ('_struct',[[('m_sound',5,-1)]]),  #110
    ('_struct',[[('m_transmissionId',65,-1)]]),  #111
    ('_struct',[[('x',70,-2),('y',70,-1)]]),  #112
    ('_optional',[70]),  #113
    ('_struct',[[('m_target',112,-4),('m_distance',113,-3),('m_pitch',113,-2),('m_yaw',113,-1)]]),  #114
    ('_int',[(0,1)]),  #115
    ('_struct',[[('m_skipType',115,-1)]]),  #116
    ('_struct',[[('m_button',5,-7),('m_down',26,-6),('m_posXUI',5,-5),('m_posYUI',5,-4),('m_posXWorld',65,-3),('m_posYWorld',65,-2),('m_posZWorld',65,-1)]]),  #117
    ('_struct',[[('m_soundtrack',5,-1)]]),  #118
    ('_struct',[[('m_planetId',65,-1)]]),  #119
    ('_struct',[[('m_key',93,-2),('m_flags',93,-1)]]),  #120
    ('_struct',[[('m_resources',90,-1)]]),  #121
    ('_struct',[[('m_fulfillRequestId',65,-1)]]),  #122
    ('_struct',[[('m_cancelRequestId',65,-1)]]),  #123
    ('_struct',[[('m_researchItemId',65,-1)]]),  #124
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #125
    ('_struct',[[('m_mercenaryId',65,-1)]]),  #126
    ('_struct',[[('m_battleReportId',65,-2),('m_difficultyLevel',65,-1)]]),  #127
    ('_struct',[[('m_battleReportId',65,-1)]]),  #128
    ('_int',[(0,19)]),  #129
    ('_struct',[[('m_decrementMs',129,-1)]]),  #130
    ('_struct',[[('m_portraitId',65,-1)]]),  #131
    ('_struct',[[('m_functionName',15,-1)]]),  #132
    ('_struct',[[('m_result',65,-1)]]),  #133
    ('_struct',[[('m_gameMenuItemIndex',65,-1)]]),  #134
    ('_struct',[[('m_reason',93,-1)]]),  #135
    ('_struct',[[('m_purchaseCategoryId',65,-1)]]),  #136
    ('_struct',[[('m_button',70,-1)]]),  #137
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #138
    ('_struct',[[('m_recipient',19,-2),('m_point',66,-1)]]),  #139
    ('_struct',[[('m_progress',65,-1)]]),  #140
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (63, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SUserOptionsEvent'),
    22: (64, 'NNet.Game.SSaveGameEvent'),
    23: (63, 'NNet.Game.SSaveGameDoneEvent'),
    25: (63, 'NNet.Game.SPlayerLeaveEvent'),
    26: (68, 'NNet.Game.SGameCheatEvent'),
    27: (79, 'NNet.Game.SCmdEvent'),
    28: (86, 'NNet.Game.SSelectionDeltaEvent'),
    29: (87, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (89, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (91, 'NNet.Game.SResourceTradeEvent'),
    32: (92, 'NNet.Game.STriggerChatMessageEvent'),
    33: (95, 'NNet.Game.SAICommunicateEvent'),
    34: (96, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (97, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (98, 'NNet.Game.SBroadcastCheatEvent'),
    38: (99, 'NNet.Game.SAllianceEvent'),
    39: (100, 'NNet.Game.SUnitClickEvent'),
    40: (101, 'NNet.Game.SUnitHighlightEvent'),
    41: (102, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (63, 'NNet.Game.STriggerSkippedEvent'),
    45: (107, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (110, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (111, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (111, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (114, 'NNet.Game.SCameraUpdateEvent'),
    50: (63, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (103, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (63, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (104, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (63, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (106, 'NNet.Game.STriggerDialogControlEvent'),
    56: (109, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (116, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (117, 'NNet.Game.STriggerMouseClickedEvent'),
    63: (63, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (118, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (119, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (120, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (132, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (63, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (63, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (121, 'NNet.Game.SResourceRequestEvent'),
    71: (122, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (123, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (63, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (63, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (124, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (125, 'NNet.Game.SLagMessageEvent'),
    77: (63, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (63, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (126, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (63, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (63, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (127, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (128, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (128, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (104, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (63, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (63, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (130, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (131, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (133, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (134, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (135, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (103, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (136, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (137, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (63, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (138, 'NNet.Game.SChatMessage'),
    1: (139, 'NNet.Game.SPingMessage'),
    2: (140, 'NNet.Game.SLoadingProgressMessage'),
    3: (63, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol16755
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,5)]),  #40
    ('_int',[(1,8)]),  #41
    ('_bitarray',[(0,6)]),  #42
    ('_bitarray',[(0,8)]),  #43
    ('_bitarray',[(0,2)]),  #44
    ('_struct',[[('m_allowedColors',42,-5),('m_allowedRaces',43,-4),('m_allowedDifficulty',42,-3),('m_allowedControls',43,-2),('m_allowedObserveTypes',44,-1)]]),  #45
    ('_array',[(0,5),45]),  #46
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',40,-14),('m_maxRaces',41,-13),('m_maxControls',41,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',46,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #47
    ('_optional',[1]),  #48
    ('_optional',[7]),  #49
    ('_struct',[[('m_color',49,-1)]]),  #50
    ('_array',[(0,5),5]),  #51
    ('_struct',[[('m_control',10,-9),('m_userId',48,-8),('m_teamId',1,-7),('m_colorPref',50,-6),('m_racePref',34,-5),('m_difficulty',2,-4),('m_handicap',0,-3),('m_observe',19,-2),('m_rewards',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',48,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',47,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #62
    ('_struct',[[]]),  #63
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #64
    ('_int',[(-2147483648,32)]),  #65
    ('_struct',[[('x',65,-2),('y',65,-1)]]),  #66
    ('_struct',[[('m_point',66,-4),('m_time',65,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #67
    ('_struct',[[('m_data',67,-1)]]),  #68
    ('_int',[(0,17)]),  #69
    ('_int',[(0,16)]),  #70
    ('_struct',[[('m_abilLink',70,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #71
    ('_optional',[71]),  #72
    ('_null',[]),  #73
    ('_int',[(0,20)]),  #74
    ('_struct',[[('x',74,-3),('y',74,-2),('z',65,-1)]]),  #75
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',70,-3),('m_snapshotPlayerId',48,-2),('m_snapshotPoint',75,-1)]]),  #76
    ('_choice',[(0,2),{0:('None',73),1:('TargetPoint',75),2:('TargetUnit',76),3:('Data',5)}]),  #77
    ('_optional',[5]),  #78
    ('_struct',[[('m_cmdFlags',69,-4),('m_abil',72,-3),('m_data',77,-2),('m_otherUnit',78,-1)]]),  #79
    ('_array',[(0,8),10]),  #80
    ('_choice',[(0,2),{0:('None',73),1:('Mask',43),2:('OneIndices',80),3:('ZeroIndices',80)}]),  #81
    ('_struct',[[('m_unitLink',70,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #82
    ('_array',[(0,8),82]),  #83
    ('_array',[(0,8),5]),  #84
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',81,-3),('m_addSubgroups',83,-2),('m_addUnitTags',84,-1)]]),  #85
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',81,-1)]]),  #87
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #88
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',88,-1)]]),  #89
    ('_array',[(0,3),65]),  #90
    ('_struct',[[('m_recipientId',1,-2),('m_resources',90,-1)]]),  #91
    ('_struct',[[('m_chatMessage',23,-1)]]),  #92
    ('_int',[(-128,8)]),  #93
    ('_struct',[[('x',65,-3),('y',65,-2),('z',65,-1)]]),  #94
    ('_struct',[[('m_beacon',93,-7),('m_ally',93,-6),('m_autocast',93,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',70,-3),('m_targetUnitSnapshotPlayerId',48,-2),('m_targetPoint',94,-1)]]),  #95
    ('_struct',[[('m_speed',12,-1)]]),  #96
    ('_struct',[[('m_delta',93,-1)]]),  #97
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #98
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #99
    ('_struct',[[('m_unitTag',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #101
    ('_struct',[[('m_conversationId',65,-2),('m_replyId',65,-1)]]),  #102
    ('_struct',[[('m_purchaseItemId',65,-1)]]),  #103
    ('_struct',[[('m_difficultyLevel',65,-1)]]),  #104
    ('_choice',[(0,3),{0:('None',73),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',65),4:('TextChanged',24)}]),  #105
    ('_struct',[[('m_controlId',65,-3),('m_eventType',65,-2),('m_eventData',105,-1)]]),  #106
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #107
    ('_struct',[[('m_soundHash',84,-2),('m_length',84,-1)]]),  #108
    ('_struct',[[('m_syncInfo',108,-1)]]),  #109
    ('_struct',[[('m_sound',5,-1)]]),  #110
    ('_struct',[[('m_transmissionId',65,-1)]]),  #111
    ('_struct',[[('x',70,-2),('y',70,-1)]]),  #112
    ('_optional',[70]),  #113
    ('_struct',[[('m_target',112,-4),('m_distance',113,-3),('m_pitch',113,-2),('m_yaw',113,-1)]]),  #114
    ('_int',[(0,1)]),  #115
    ('_struct',[[('m_skipType',115,-1)]]),  #116
    ('_struct',[[('m_button',5,-7),('m_down',26,-6),('m_posXUI',5,-5),('m_posYUI',5,-4),('m_posXWorld',65,-3),('m_posYWorld',65,-2),('m_posZWorld',65,-1)]]),  #117
    ('_struct',[[('m_soundtrack',5,-1)]]),  #118
    ('_struct',[[('m_planetId',65,-1)]]),  #119
    ('_struct',[[('m_key',93,-2),('m_flags',93,-1)]]),  #120
    ('_struct',[[('m_resources',90,-1)]]),  #121
    ('_struct',[[('m_fulfillRequestId',65,-1)]]),  #122
    ('_struct',[[('m_cancelRequestId',65,-1)]]),  #123
    ('_struct',[[('m_researchItemId',65,-1)]]),  #124
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #125
    ('_struct',[[('m_mercenaryId',65,-1)]]),  #126
    ('_struct',[[('m_battleReportId',65,-2),('m_difficultyLevel',65,-1)]]),  #127
    ('_struct',[[('m_battleReportId',65,-1)]]),  #128
    ('_int',[(0,19)]),  #129
    ('_struct',[[('m_decrementMs',129,-1)]]),  #130
    ('_struct',[[('m_portraitId',65,-1)]]),  #131
    ('_struct',[[('m_functionName',15,-1)]]),  #132
    ('_struct',[[('m_result',65,-1)]]),  #133
    ('_struct',[[('m_gameMenuItemIndex',65,-1)]]),  #134
    ('_struct',[[('m_reason',93,-1)]]),  #135
    ('_struct',[[('m_purchaseCategoryId',65,-1)]]),  #136
    ('_struct',[[('m_button',70,-1)]]),  #137
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #138
    ('_struct',[[('m_recipient',19,-2),('m_point',66,-1)]]),  #139
    ('_struct',[[('m_progress',65,-1)]]),  #140
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (63, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SUserOptionsEvent'),
    22: (64, 'NNet.Game.SSaveGameEvent'),
    23: (63, 'NNet.Game.SSaveGameDoneEvent'),
    25: (63, 'NNet.Game.SPlayerLeaveEvent'),
    26: (68, 'NNet.Game.SGameCheatEvent'),
    27: (79, 'NNet.Game.SCmdEvent'),
    28: (86, 'NNet.Game.SSelectionDeltaEvent'),
    29: (87, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (89, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (91, 'NNet.Game.SResourceTradeEvent'),
    32: (92, 'NNet.Game.STriggerChatMessageEvent'),
    33: (95, 'NNet.Game.SAICommunicateEvent'),
    34: (96, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (97, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (98, 'NNet.Game.SBroadcastCheatEvent'),
    38: (99, 'NNet.Game.SAllianceEvent'),
    39: (100, 'NNet.Game.SUnitClickEvent'),
    40: (101, 'NNet.Game.SUnitHighlightEvent'),
    41: (102, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (63, 'NNet.Game.STriggerSkippedEvent'),
    45: (107, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (110, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (111, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (111, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (114, 'NNet.Game.SCameraUpdateEvent'),
    50: (63, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (103, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (63, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (104, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (63, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (106, 'NNet.Game.STriggerDialogControlEvent'),
    56: (109, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (116, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (117, 'NNet.Game.STriggerMouseClickedEvent'),
    63: (63, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (118, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (119, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (120, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (132, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (63, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (63, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (121, 'NNet.Game.SResourceRequestEvent'),
    71: (122, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (123, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (63, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (63, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (124, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (125, 'NNet.Game.SLagMessageEvent'),
    77: (63, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (63, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (126, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (63, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (63, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (127, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (128, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (128, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (104, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (63, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (63, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (130, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (131, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (133, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (134, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (135, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (103, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (136, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (137, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (63, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (138, 'NNet.Game.SChatMessage'),
    1: (139, 'NNet.Game.SPingMessage'),
    2: (140, 'NNet.Game.SLoadingProgressMessage'),
    3: (63, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol16939
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,5)]),  #40
    ('_int',[(1,8)]),  #41
    ('_bitarray',[(0,6)]),  #42
    ('_bitarray',[(0,8)]),  #43
    ('_bitarray',[(0,2)]),  #44
    ('_struct',[[('m_allowedColors',42,-5),('m_allowedRaces',43,-4),('m_allowedDifficulty',42,-3),('m_allowedControls',43,-2),('m_allowedObserveTypes',44,-1)]]),  #45
    ('_array',[(0,5),45]),  #46
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',40,-14),('m_maxRaces',41,-13),('m_maxControls',41,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',46,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #47
    ('_optional',[1]),  #48
    ('_optional',[7]),  #49
    ('_struct',[[('m_color',49,-1)]]),  #50
    ('_array',[(0,5),5]),  #51
    ('_struct',[[('m_control',10,-9),('m_userId',48,-8),('m_teamId',1,-7),('m_colorPref',50,-6),('m_racePref',34,-5),('m_difficulty',2,-4),('m_handicap',0,-3),('m_observe',19,-2),('m_rewards',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',48,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',47,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #62
    ('_struct',[[]]),  #63
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #64
    ('_int',[(-2147483648,32)]),  #65
    ('_struct',[[('x',65,-2),('y',65,-1)]]),  #66
    ('_struct',[[('m_point',66,-4),('m_time',65,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #67
    ('_struct',[[('m_data',67,-1)]]),  #68
    ('_int',[(0,17)]),  #69
    ('_int',[(0,16)]),  #70
    ('_struct',[[('m_abilLink',70,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #71
    ('_optional',[71]),  #72
    ('_null',[]),  #73
    ('_int',[(0,20)]),  #74
    ('_struct',[[('x',74,-3),('y',74,-2),('z',65,-1)]]),  #75
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',70,-3),('m_snapshotPlayerId',48,-2),('m_snapshotPoint',75,-1)]]),  #76
    ('_choice',[(0,2),{0:('None',73),1:('TargetPoint',75),2:('TargetUnit',76),3:('Data',5)}]),  #77
    ('_optional',[5]),  #78
    ('_struct',[[('m_cmdFlags',69,-4),('m_abil',72,-3),('m_data',77,-2),('m_otherUnit',78,-1)]]),  #79
    ('_array',[(0,8),10]),  #80
    ('_choice',[(0,2),{0:('None',73),1:('Mask',43),2:('OneIndices',80),3:('ZeroIndices',80)}]),  #81
    ('_struct',[[('m_unitLink',70,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #82
    ('_array',[(0,8),82]),  #83
    ('_array',[(0,8),5]),  #84
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',81,-3),('m_addSubgroups',83,-2),('m_addUnitTags',84,-1)]]),  #85
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',81,-1)]]),  #87
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #88
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',88,-1)]]),  #89
    ('_array',[(0,3),65]),  #90
    ('_struct',[[('m_recipientId',1,-2),('m_resources',90,-1)]]),  #91
    ('_struct',[[('m_chatMessage',23,-1)]]),  #92
    ('_int',[(-128,8)]),  #93
    ('_struct',[[('x',65,-3),('y',65,-2),('z',65,-1)]]),  #94
    ('_struct',[[('m_beacon',93,-7),('m_ally',93,-6),('m_autocast',93,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',70,-3),('m_targetUnitSnapshotPlayerId',48,-2),('m_targetPoint',94,-1)]]),  #95
    ('_struct',[[('m_speed',12,-1)]]),  #96
    ('_struct',[[('m_delta',93,-1)]]),  #97
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #98
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #99
    ('_struct',[[('m_unitTag',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #101
    ('_struct',[[('m_conversationId',65,-2),('m_replyId',65,-1)]]),  #102
    ('_struct',[[('m_purchaseItemId',65,-1)]]),  #103
    ('_struct',[[('m_difficultyLevel',65,-1)]]),  #104
    ('_choice',[(0,3),{0:('None',73),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',65),4:('TextChanged',24)}]),  #105
    ('_struct',[[('m_controlId',65,-3),('m_eventType',65,-2),('m_eventData',105,-1)]]),  #106
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #107
    ('_struct',[[('m_soundHash',84,-2),('m_length',84,-1)]]),  #108
    ('_struct',[[('m_syncInfo',108,-1)]]),  #109
    ('_struct',[[('m_sound',5,-1)]]),  #110
    ('_struct',[[('m_transmissionId',65,-1)]]),  #111
    ('_struct',[[('x',70,-2),('y',70,-1)]]),  #112
    ('_optional',[70]),  #113
    ('_struct',[[('m_target',112,-4),('m_distance',113,-3),('m_pitch',113,-2),('m_yaw',113,-1)]]),  #114
    ('_int',[(0,1)]),  #115
    ('_struct',[[('m_skipType',115,-1)]]),  #116
    ('_struct',[[('m_button',5,-7),('m_down',26,-6),('m_posXUI',5,-5),('m_posYUI',5,-4),('m_posXWorld',65,-3),('m_posYWorld',65,-2),('m_posZWorld',65,-1)]]),  #117
    ('_struct',[[('m_soundtrack',5,-1)]]),  #118
    ('_struct',[[('m_planetId',65,-1)]]),  #119
    ('_struct',[[('m_key',93,-2),('m_flags',93,-1)]]),  #120
    ('_struct',[[('m_resources',90,-1)]]),  #121
    ('_struct',[[('m_fulfillRequestId',65,-1)]]),  #122
    ('_struct',[[('m_cancelRequestId',65,-1)]]),  #123
    ('_struct',[[('m_researchItemId',65,-1)]]),  #124
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #125
    ('_struct',[[('m_mercenaryId',65,-1)]]),  #126
    ('_struct',[[('m_battleReportId',65,-2),('m_difficultyLevel',65,-1)]]),  #127
    ('_struct',[[('m_battleReportId',65,-1)]]),  #128
    ('_int',[(0,19)]),  #129
    ('_struct',[[('m_decrementMs',129,-1)]]),  #130
    ('_struct',[[('m_portraitId',65,-1)]]),  #131
    ('_struct',[[('m_functionName',15,-1)]]),  #132
    ('_struct',[[('m_result',65,-1)]]),  #133
    ('_struct',[[('m_gameMenuItemIndex',65,-1)]]),  #134
    ('_struct',[[('m_reason',93,-1)]]),  #135
    ('_struct',[[('m_purchaseCategoryId',65,-1)]]),  #136
    ('_struct',[[('m_button',70,-1)]]),  #137
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #138
    ('_struct',[[('m_recipient',19,-2),('m_point',66,-1)]]),  #139
    ('_struct',[[('m_progress',65,-1)]]),  #140
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (63, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SUserOptionsEvent'),
    22: (64, 'NNet.Game.SSaveGameEvent'),
    23: (63, 'NNet.Game.SSaveGameDoneEvent'),
    25: (63, 'NNet.Game.SPlayerLeaveEvent'),
    26: (68, 'NNet.Game.SGameCheatEvent'),
    27: (79, 'NNet.Game.SCmdEvent'),
    28: (86, 'NNet.Game.SSelectionDeltaEvent'),
    29: (87, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (89, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (91, 'NNet.Game.SResourceTradeEvent'),
    32: (92, 'NNet.Game.STriggerChatMessageEvent'),
    33: (95, 'NNet.Game.SAICommunicateEvent'),
    34: (96, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (97, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (98, 'NNet.Game.SBroadcastCheatEvent'),
    38: (99, 'NNet.Game.SAllianceEvent'),
    39: (100, 'NNet.Game.SUnitClickEvent'),
    40: (101, 'NNet.Game.SUnitHighlightEvent'),
    41: (102, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (63, 'NNet.Game.STriggerSkippedEvent'),
    45: (107, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (110, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (111, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (111, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (114, 'NNet.Game.SCameraUpdateEvent'),
    50: (63, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (103, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (63, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (104, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (63, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (106, 'NNet.Game.STriggerDialogControlEvent'),
    56: (109, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (116, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (117, 'NNet.Game.STriggerMouseClickedEvent'),
    63: (63, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (118, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (119, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (120, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (132, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (63, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (63, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (121, 'NNet.Game.SResourceRequestEvent'),
    71: (122, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (123, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (63, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (63, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (124, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (125, 'NNet.Game.SLagMessageEvent'),
    77: (63, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (63, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (126, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (63, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (63, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (127, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (128, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (128, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (104, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (63, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (63, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (130, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (131, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (133, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (134, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (135, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (103, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (136, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (137, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (63, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (138, 'NNet.Game.SChatMessage'),
    1: (139, 'NNet.Game.SPingMessage'),
    2: (140, 'NNet.Game.SLoadingProgressMessage'),
    3: (63, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol17266
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-10),('m_userId',47,-9),('m_teamId',1,-8),('m_colorPref',49,-7),('m_racePref',34,-6),('m_difficulty',2,-5),('m_handicap',0,-4),('m_observe',19,-3),('m_rewards',50,-2),('m_toonHandle',15,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_array',[(0,5),10]),  #61
    ('_struct',[[('m_signature',61,-1)]]),  #62
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #63
    ('_struct',[[]]),  #64
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #65
    ('_int',[(-2147483648,32)]),  #66
    ('_struct',[[('x',66,-2),('y',66,-1)]]),  #67
    ('_struct',[[('m_point',67,-4),('m_time',66,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #68
    ('_struct',[[('m_data',68,-1)]]),  #69
    ('_int',[(0,17)]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #72
    ('_optional',[72]),  #73
    ('_null',[]),  #74
    ('_int',[(0,20)]),  #75
    ('_struct',[[('x',75,-3),('y',75,-2),('z',66,-1)]]),  #76
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',71,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',76,-1)]]),  #77
    ('_choice',[(0,2),{0:('None',74),1:('TargetPoint',76),2:('TargetUnit',77),3:('Data',5)}]),  #78
    ('_optional',[5]),  #79
    ('_struct',[[('m_cmdFlags',70,-4),('m_abil',73,-3),('m_data',78,-2),('m_otherUnit',79,-1)]]),  #80
    ('_array',[(0,8),10]),  #81
    ('_choice',[(0,2),{0:('None',74),1:('Mask',42),2:('OneIndices',81),3:('ZeroIndices',81)}]),  #82
    ('_struct',[[('m_unitLink',71,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #83
    ('_array',[(0,8),83]),  #84
    ('_array',[(0,8),5]),  #85
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',82,-3),('m_addSubgroups',84,-2),('m_addUnitTags',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',82,-1)]]),  #88
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',89,-1)]]),  #90
    ('_array',[(0,3),66]),  #91
    ('_struct',[[('m_recipientId',1,-2),('m_resources',91,-1)]]),  #92
    ('_struct',[[('m_chatMessage',23,-1)]]),  #93
    ('_int',[(-128,8)]),  #94
    ('_struct',[[('x',66,-3),('y',66,-2),('z',66,-1)]]),  #95
    ('_struct',[[('m_beacon',94,-7),('m_ally',94,-6),('m_autocast',94,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',71,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',95,-1)]]),  #96
    ('_struct',[[('m_speed',12,-1)]]),  #97
    ('_struct',[[('m_delta',94,-1)]]),  #98
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #99
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #102
    ('_struct',[[('m_conversationId',66,-2),('m_replyId',66,-1)]]),  #103
    ('_struct',[[('m_purchaseItemId',66,-1)]]),  #104
    ('_struct',[[('m_difficultyLevel',66,-1)]]),  #105
    ('_choice',[(0,3),{0:('None',74),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',66),4:('TextChanged',24)}]),  #106
    ('_struct',[[('m_controlId',66,-3),('m_eventType',66,-2),('m_eventData',106,-1)]]),  #107
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #108
    ('_struct',[[('m_soundHash',85,-2),('m_length',85,-1)]]),  #109
    ('_struct',[[('m_syncInfo',109,-1)]]),  #110
    ('_struct',[[('m_sound',5,-1)]]),  #111
    ('_struct',[[('m_transmissionId',66,-1)]]),  #112
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #113
    ('_optional',[71]),  #114
    ('_struct',[[('m_target',113,-4),('m_distance',114,-3),('m_pitch',114,-2),('m_yaw',114,-1)]]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_skipType',116,-1)]]),  #117
    ('_int',[(0,11)]),  #118
    ('_struct',[[('x',118,-2),('y',118,-1)]]),  #119
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #120
    ('_struct',[[('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #121
    ('_struct',[[('m_soundtrack',5,-1)]]),  #122
    ('_struct',[[('m_planetId',66,-1)]]),  #123
    ('_struct',[[('m_key',94,-2),('m_flags',94,-1)]]),  #124
    ('_struct',[[('m_resources',91,-1)]]),  #125
    ('_struct',[[('m_fulfillRequestId',66,-1)]]),  #126
    ('_struct',[[('m_cancelRequestId',66,-1)]]),  #127
    ('_struct',[[('m_researchItemId',66,-1)]]),  #128
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #129
    ('_struct',[[('m_mercenaryId',66,-1)]]),  #130
    ('_struct',[[('m_battleReportId',66,-2),('m_difficultyLevel',66,-1)]]),  #131
    ('_struct',[[('m_battleReportId',66,-1)]]),  #132
    ('_int',[(0,19)]),  #133
    ('_struct',[[('m_decrementMs',133,-1)]]),  #134
    ('_struct',[[('m_portraitId',66,-1)]]),  #135
    ('_struct',[[('m_functionName',15,-1)]]),  #136
    ('_struct',[[('m_result',66,-1)]]),  #137
    ('_struct',[[('m_gameMenuItemIndex',66,-1)]]),  #138
    ('_struct',[[('m_reason',94,-1)]]),  #139
    ('_struct',[[('m_purchaseCategoryId',66,-1)]]),  #140
    ('_struct',[[('m_button',71,-1)]]),  #141
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_point',67,-1)]]),  #143
    ('_struct',[[('m_progress',66,-1)]]),  #144
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (64, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SBankSignatureEvent'),
    12: (63, 'NNet.Game.SUserOptionsEvent'),
    22: (65, 'NNet.Game.SSaveGameEvent'),
    23: (64, 'NNet.Game.SSaveGameDoneEvent'),
    25: (64, 'NNet.Game.SPlayerLeaveEvent'),
    26: (69, 'NNet.Game.SGameCheatEvent'),
    27: (80, 'NNet.Game.SCmdEvent'),
    28: (87, 'NNet.Game.SSelectionDeltaEvent'),
    29: (88, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (90, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (92, 'NNet.Game.SResourceTradeEvent'),
    32: (93, 'NNet.Game.STriggerChatMessageEvent'),
    33: (96, 'NNet.Game.SAICommunicateEvent'),
    34: (97, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (98, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (99, 'NNet.Game.SBroadcastCheatEvent'),
    38: (100, 'NNet.Game.SAllianceEvent'),
    39: (101, 'NNet.Game.SUnitClickEvent'),
    40: (102, 'NNet.Game.SUnitHighlightEvent'),
    41: (103, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (64, 'NNet.Game.STriggerSkippedEvent'),
    45: (108, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (111, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (112, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (112, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (115, 'NNet.Game.SCameraUpdateEvent'),
    50: (64, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (104, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (64, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (105, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (64, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (107, 'NNet.Game.STriggerDialogControlEvent'),
    56: (110, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (117, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (120, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (121, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (64, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (122, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (123, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (124, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (136, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (64, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (64, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (125, 'NNet.Game.SResourceRequestEvent'),
    71: (126, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (127, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (64, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (64, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (128, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (129, 'NNet.Game.SLagMessageEvent'),
    77: (64, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (64, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (130, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (64, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (64, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (131, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (132, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (132, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (105, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (64, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (64, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (134, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (135, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (137, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (138, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (139, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (104, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (140, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (141, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (64, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (142, 'NNet.Game.SChatMessage'),
    1: (143, 'NNet.Game.SPingMessage'),
    2: (144, 'NNet.Game.SLoadingProgressMessage'),
    3: (64, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = None
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol17326
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-10),('m_userId',47,-9),('m_teamId',1,-8),('m_colorPref',49,-7),('m_racePref',34,-6),('m_difficulty',2,-5),('m_handicap',0,-4),('m_observe',19,-3),('m_rewards',50,-2),('m_toonHandle',15,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_array',[(0,5),10]),  #61
    ('_struct',[[('m_signature',61,-1)]]),  #62
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #63
    ('_struct',[[]]),  #64
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #65
    ('_int',[(-2147483648,32)]),  #66
    ('_struct',[[('x',66,-2),('y',66,-1)]]),  #67
    ('_struct',[[('m_point',67,-4),('m_time',66,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #68
    ('_struct',[[('m_data',68,-1)]]),  #69
    ('_int',[(0,17)]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #72
    ('_optional',[72]),  #73
    ('_null',[]),  #74
    ('_int',[(0,20)]),  #75
    ('_struct',[[('x',75,-3),('y',75,-2),('z',66,-1)]]),  #76
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',71,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',76,-1)]]),  #77
    ('_choice',[(0,2),{0:('None',74),1:('TargetPoint',76),2:('TargetUnit',77),3:('Data',5)}]),  #78
    ('_optional',[5]),  #79
    ('_struct',[[('m_cmdFlags',70,-4),('m_abil',73,-3),('m_data',78,-2),('m_otherUnit',79,-1)]]),  #80
    ('_array',[(0,8),10]),  #81
    ('_choice',[(0,2),{0:('None',74),1:('Mask',42),2:('OneIndices',81),3:('ZeroIndices',81)}]),  #82
    ('_struct',[[('m_unitLink',71,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #83
    ('_array',[(0,8),83]),  #84
    ('_array',[(0,8),5]),  #85
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',82,-3),('m_addSubgroups',84,-2),('m_addUnitTags',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',82,-1)]]),  #88
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',89,-1)]]),  #90
    ('_array',[(0,3),66]),  #91
    ('_struct',[[('m_recipientId',1,-2),('m_resources',91,-1)]]),  #92
    ('_struct',[[('m_chatMessage',23,-1)]]),  #93
    ('_int',[(-128,8)]),  #94
    ('_struct',[[('x',66,-3),('y',66,-2),('z',66,-1)]]),  #95
    ('_struct',[[('m_beacon',94,-7),('m_ally',94,-6),('m_autocast',94,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',71,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',95,-1)]]),  #96
    ('_struct',[[('m_speed',12,-1)]]),  #97
    ('_struct',[[('m_delta',94,-1)]]),  #98
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #99
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #102
    ('_struct',[[('m_conversationId',66,-2),('m_replyId',66,-1)]]),  #103
    ('_struct',[[('m_purchaseItemId',66,-1)]]),  #104
    ('_struct',[[('m_difficultyLevel',66,-1)]]),  #105
    ('_choice',[(0,3),{0:('None',74),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',66),4:('TextChanged',24)}]),  #106
    ('_struct',[[('m_controlId',66,-3),('m_eventType',66,-2),('m_eventData',106,-1)]]),  #107
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #108
    ('_struct',[[('m_soundHash',85,-2),('m_length',85,-1)]]),  #109
    ('_struct',[[('m_syncInfo',109,-1)]]),  #110
    ('_struct',[[('m_sound',5,-1)]]),  #111
    ('_struct',[[('m_transmissionId',66,-1)]]),  #112
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #113
    ('_optional',[71]),  #114
    ('_struct',[[('m_target',113,-4),('m_distance',114,-3),('m_pitch',114,-2),('m_yaw',114,-1)]]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_skipType',116,-1)]]),  #117
    ('_int',[(0,11)]),  #118
    ('_struct',[[('x',118,-2),('y',118,-1)]]),  #119
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #120
    ('_struct',[[('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #121
    ('_struct',[[('m_soundtrack',5,-1)]]),  #122
    ('_struct',[[('m_planetId',66,-1)]]),  #123
    ('_struct',[[('m_key',94,-2),('m_flags',94,-1)]]),  #124
    ('_struct',[[('m_resources',91,-1)]]),  #125
    ('_struct',[[('m_fulfillRequestId',66,-1)]]),  #126
    ('_struct',[[('m_cancelRequestId',66,-1)]]),  #127
    ('_struct',[[('m_researchItemId',66,-1)]]),  #128
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #129
    ('_struct',[[('m_mercenaryId',66,-1)]]),  #130
    ('_struct',[[('m_battleReportId',66,-2),('m_difficultyLevel',66,-1)]]),  #131
    ('_struct',[[('m_battleReportId',66,-1)]]),  #132
    ('_int',[(0,19)]),  #133
    ('_struct',[[('m_decrementMs',133,-1)]]),  #134
    ('_struct',[[('m_portraitId',66,-1)]]),  #135
    ('_struct',[[('m_functionName',15,-1)]]),  #136
    ('_struct',[[('m_result',66,-1)]]),  #137
    ('_struct',[[('m_gameMenuItemIndex',66,-1)]]),  #138
    ('_struct',[[('m_reason',94,-1)]]),  #139
    ('_struct',[[('m_purchaseCategoryId',66,-1)]]),  #140
    ('_struct',[[('m_button',71,-1)]]),  #141
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_point',67,-1)]]),  #143
    ('_struct',[[('m_progress',66,-1)]]),  #144
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (64, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SBankSignatureEvent'),
    12: (63, 'NNet.Game.SUserOptionsEvent'),
    22: (65, 'NNet.Game.SSaveGameEvent'),
    23: (64, 'NNet.Game.SSaveGameDoneEvent'),
    25: (64, 'NNet.Game.SPlayerLeaveEvent'),
    26: (69, 'NNet.Game.SGameCheatEvent'),
    27: (80, 'NNet.Game.SCmdEvent'),
    28: (87, 'NNet.Game.SSelectionDeltaEvent'),
    29: (88, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (90, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (92, 'NNet.Game.SResourceTradeEvent'),
    32: (93, 'NNet.Game.STriggerChatMessageEvent'),
    33: (96, 'NNet.Game.SAICommunicateEvent'),
    34: (97, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (98, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (99, 'NNet.Game.SBroadcastCheatEvent'),
    38: (100, 'NNet.Game.SAllianceEvent'),
    39: (101, 'NNet.Game.SUnitClickEvent'),
    40: (102, 'NNet.Game.SUnitHighlightEvent'),
    41: (103, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (64, 'NNet.Game.STriggerSkippedEvent'),
    45: (108, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (111, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (112, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (112, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (115, 'NNet.Game.SCameraUpdateEvent'),
    50: (64, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (104, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (64, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (105, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (64, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (107, 'NNet.Game.STriggerDialogControlEvent'),
    56: (110, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (117, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (120, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (121, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (64, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (122, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (123, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (124, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (136, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (64, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (64, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (125, 'NNet.Game.SResourceRequestEvent'),
    71: (126, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (127, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (64, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (64, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (128, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (129, 'NNet.Game.SLagMessageEvent'),
    77: (64, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (64, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (130, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (64, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (64, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (131, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (132, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (132, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (105, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (64, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (64, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (134, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (135, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (137, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (138, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (139, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (104, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (140, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (141, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (64, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (142, 'NNet.Game.SChatMessage'),
    1: (143, 'NNet.Game.SPingMessage'),
    2: (144, 'NNet.Game.SLoadingProgressMessage'),
    3: (64, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol18092
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-10),('m_userId',47,-9),('m_teamId',1,-8),('m_colorPref',49,-7),('m_racePref',34,-6),('m_difficulty',2,-5),('m_handicap',0,-4),('m_observe',19,-3),('m_rewards',50,-2),('m_toonHandle',15,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_array',[(0,5),10]),  #61
    ('_struct',[[('m_signature',61,-1)]]),  #62
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #63
    ('_struct',[[]]),  #64
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #65
    ('_int',[(-2147483648,32)]),  #66
    ('_struct',[[('x',66,-2),('y',66,-1)]]),  #67
    ('_struct',[[('m_point',67,-4),('m_time',66,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #68
    ('_struct',[[('m_data',68,-1)]]),  #69
    ('_int',[(0,17)]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #72
    ('_optional',[72]),  #73
    ('_null',[]),  #74
    ('_int',[(0,20)]),  #75
    ('_struct',[[('x',75,-3),('y',75,-2),('z',66,-1)]]),  #76
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',71,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',76,-1)]]),  #77
    ('_choice',[(0,2),{0:('None',74),1:('TargetPoint',76),2:('TargetUnit',77),3:('Data',5)}]),  #78
    ('_optional',[5]),  #79
    ('_struct',[[('m_cmdFlags',70,-4),('m_abil',73,-3),('m_data',78,-2),('m_otherUnit',79,-1)]]),  #80
    ('_array',[(0,8),10]),  #81
    ('_choice',[(0,2),{0:('None',74),1:('Mask',42),2:('OneIndices',81),3:('ZeroIndices',81)}]),  #82
    ('_struct',[[('m_unitLink',71,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #83
    ('_array',[(0,8),83]),  #84
    ('_array',[(0,8),5]),  #85
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',82,-3),('m_addSubgroups',84,-2),('m_addUnitTags',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',82,-1)]]),  #88
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',89,-1)]]),  #90
    ('_array',[(0,3),66]),  #91
    ('_struct',[[('m_recipientId',1,-2),('m_resources',91,-1)]]),  #92
    ('_struct',[[('m_chatMessage',23,-1)]]),  #93
    ('_int',[(-128,8)]),  #94
    ('_struct',[[('x',66,-3),('y',66,-2),('z',66,-1)]]),  #95
    ('_struct',[[('m_beacon',94,-7),('m_ally',94,-6),('m_autocast',94,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',71,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',95,-1)]]),  #96
    ('_struct',[[('m_speed',12,-1)]]),  #97
    ('_struct',[[('m_delta',94,-1)]]),  #98
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #99
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #102
    ('_struct',[[('m_conversationId',66,-2),('m_replyId',66,-1)]]),  #103
    ('_struct',[[('m_purchaseItemId',66,-1)]]),  #104
    ('_struct',[[('m_difficultyLevel',66,-1)]]),  #105
    ('_choice',[(0,3),{0:('None',74),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',66),4:('TextChanged',24)}]),  #106
    ('_struct',[[('m_controlId',66,-3),('m_eventType',66,-2),('m_eventData',106,-1)]]),  #107
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #108
    ('_struct',[[('m_soundHash',85,-2),('m_length',85,-1)]]),  #109
    ('_struct',[[('m_syncInfo',109,-1)]]),  #110
    ('_struct',[[('m_sound',5,-1)]]),  #111
    ('_struct',[[('m_transmissionId',66,-1)]]),  #112
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #113
    ('_optional',[71]),  #114
    ('_struct',[[('m_target',113,-4),('m_distance',114,-3),('m_pitch',114,-2),('m_yaw',114,-1)]]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_skipType',116,-1)]]),  #117
    ('_int',[(0,11)]),  #118
    ('_struct',[[('x',118,-2),('y',118,-1)]]),  #119
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #120
    ('_struct',[[('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #121
    ('_struct',[[('m_soundtrack',5,-1)]]),  #122
    ('_struct',[[('m_planetId',66,-1)]]),  #123
    ('_struct',[[('m_key',94,-2),('m_flags',94,-1)]]),  #124
    ('_struct',[[('m_resources',91,-1)]]),  #125
    ('_struct',[[('m_fulfillRequestId',66,-1)]]),  #126
    ('_struct',[[('m_cancelRequestId',66,-1)]]),  #127
    ('_struct',[[('m_researchItemId',66,-1)]]),  #128
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #129
    ('_struct',[[('m_mercenaryId',66,-1)]]),  #130
    ('_struct',[[('m_battleReportId',66,-2),('m_difficultyLevel',66,-1)]]),  #131
    ('_struct',[[('m_battleReportId',66,-1)]]),  #132
    ('_int',[(0,19)]),  #133
    ('_struct',[[('m_decrementMs',133,-1)]]),  #134
    ('_struct',[[('m_portraitId',66,-1)]]),  #135
    ('_struct',[[('m_functionName',15,-1)]]),  #136
    ('_struct',[[('m_result',66,-1)]]),  #137
    ('_struct',[[('m_gameMenuItemIndex',66,-1)]]),  #138
    ('_struct',[[('m_reason',94,-1)]]),  #139
    ('_struct',[[('m_purchaseCategoryId',66,-1)]]),  #140
    ('_struct',[[('m_button',71,-1)]]),  #141
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_point',67,-1)]]),  #143
    ('_struct',[[('m_progress',66,-1)]]),  #144
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (64, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SBankSignatureEvent'),
    12: (63, 'NNet.Game.SUserOptionsEvent'),
    22: (65, 'NNet.Game.SSaveGameEvent'),
    23: (64, 'NNet.Game.SSaveGameDoneEvent'),
    25: (64, 'NNet.Game.SPlayerLeaveEvent'),
    26: (69, 'NNet.Game.SGameCheatEvent'),
    27: (80, 'NNet.Game.SCmdEvent'),
    28: (87, 'NNet.Game.SSelectionDeltaEvent'),
    29: (88, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (90, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (92, 'NNet.Game.SResourceTradeEvent'),
    32: (93, 'NNet.Game.STriggerChatMessageEvent'),
    33: (96, 'NNet.Game.SAICommunicateEvent'),
    34: (97, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (98, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (99, 'NNet.Game.SBroadcastCheatEvent'),
    38: (100, 'NNet.Game.SAllianceEvent'),
    39: (101, 'NNet.Game.SUnitClickEvent'),
    40: (102, 'NNet.Game.SUnitHighlightEvent'),
    41: (103, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (64, 'NNet.Game.STriggerSkippedEvent'),
    45: (108, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (111, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (112, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (112, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (115, 'NNet.Game.SCameraUpdateEvent'),
    50: (64, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (104, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (64, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (105, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (64, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (107, 'NNet.Game.STriggerDialogControlEvent'),
    56: (110, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (117, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (120, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (121, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (64, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (122, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (123, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (124, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (136, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (64, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (64, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (125, 'NNet.Game.SResourceRequestEvent'),
    71: (126, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (127, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (64, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (64, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (128, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (129, 'NNet.Game.SLagMessageEvent'),
    77: (64, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (64, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (130, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (64, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (64, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (131, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (132, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (132, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (105, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (64, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (64, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (134, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (135, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (137, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (138, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (139, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (104, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (140, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (141, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (64, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (142, 'NNet.Game.SChatMessage'),
    1: (143, 'NNet.Game.SPingMessage'),
    2: (144, 'NNet.Game.SLoadingProgressMessage'),
    3: (64, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol18468
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-10),('m_userId',47,-9),('m_teamId',1,-8),('m_colorPref',49,-7),('m_racePref',34,-6),('m_difficulty',2,-5),('m_handicap',0,-4),('m_observe',19,-3),('m_rewards',50,-2),('m_toonHandle',15,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_array',[(0,5),10]),  #61
    ('_struct',[[('m_signature',61,-1)]]),  #62
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #63
    ('_struct',[[]]),  #64
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #65
    ('_int',[(-2147483648,32)]),  #66
    ('_struct',[[('x',66,-2),('y',66,-1)]]),  #67
    ('_struct',[[('m_point',67,-4),('m_time',66,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #68
    ('_struct',[[('m_data',68,-1)]]),  #69
    ('_int',[(0,18)]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #72
    ('_optional',[72]),  #73
    ('_null',[]),  #74
    ('_int',[(0,20)]),  #75
    ('_struct',[[('x',75,-3),('y',75,-2),('z',66,-1)]]),  #76
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',71,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',76,-1)]]),  #77
    ('_choice',[(0,2),{0:('None',74),1:('TargetPoint',76),2:('TargetUnit',77),3:('Data',5)}]),  #78
    ('_optional',[5]),  #79
    ('_struct',[[('m_cmdFlags',70,-4),('m_abil',73,-3),('m_data',78,-2),('m_otherUnit',79,-1)]]),  #80
    ('_array',[(0,8),10]),  #81
    ('_choice',[(0,2),{0:('None',74),1:('Mask',42),2:('OneIndices',81),3:('ZeroIndices',81)}]),  #82
    ('_struct',[[('m_unitLink',71,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #83
    ('_array',[(0,8),83]),  #84
    ('_array',[(0,8),5]),  #85
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',82,-3),('m_addSubgroups',84,-2),('m_addUnitTags',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',82,-1)]]),  #88
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',89,-1)]]),  #90
    ('_array',[(0,3),66]),  #91
    ('_struct',[[('m_recipientId',1,-2),('m_resources',91,-1)]]),  #92
    ('_struct',[[('m_chatMessage',23,-1)]]),  #93
    ('_int',[(-128,8)]),  #94
    ('_struct',[[('x',66,-3),('y',66,-2),('z',66,-1)]]),  #95
    ('_struct',[[('m_beacon',94,-7),('m_ally',94,-6),('m_autocast',94,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',71,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',95,-1)]]),  #96
    ('_struct',[[('m_speed',12,-1)]]),  #97
    ('_struct',[[('m_delta',94,-1)]]),  #98
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #99
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #102
    ('_struct',[[('m_conversationId',66,-2),('m_replyId',66,-1)]]),  #103
    ('_struct',[[('m_purchaseItemId',66,-1)]]),  #104
    ('_struct',[[('m_difficultyLevel',66,-1)]]),  #105
    ('_choice',[(0,3),{0:('None',74),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',66),4:('TextChanged',24)}]),  #106
    ('_struct',[[('m_controlId',66,-3),('m_eventType',66,-2),('m_eventData',106,-1)]]),  #107
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #108
    ('_struct',[[('m_soundHash',85,-2),('m_length',85,-1)]]),  #109
    ('_struct',[[('m_syncInfo',109,-1)]]),  #110
    ('_struct',[[('m_sound',5,-1)]]),  #111
    ('_struct',[[('m_transmissionId',66,-1)]]),  #112
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #113
    ('_optional',[71]),  #114
    ('_struct',[[('m_target',113,-4),('m_distance',114,-3),('m_pitch',114,-2),('m_yaw',114,-1)]]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_skipType',116,-1)]]),  #117
    ('_int',[(0,11)]),  #118
    ('_struct',[[('x',118,-2),('y',118,-1)]]),  #119
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #120
    ('_struct',[[('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #121
    ('_struct',[[('m_soundtrack',5,-1)]]),  #122
    ('_struct',[[('m_planetId',66,-1)]]),  #123
    ('_struct',[[('m_key',94,-2),('m_flags',94,-1)]]),  #124
    ('_struct',[[('m_resources',91,-1)]]),  #125
    ('_struct',[[('m_fulfillRequestId',66,-1)]]),  #126
    ('_struct',[[('m_cancelRequestId',66,-1)]]),  #127
    ('_struct',[[('m_researchItemId',66,-1)]]),  #128
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #129
    ('_struct',[[('m_mercenaryId',66,-1)]]),  #130
    ('_struct',[[('m_battleReportId',66,-2),('m_difficultyLevel',66,-1)]]),  #131
    ('_struct',[[('m_battleReportId',66,-1)]]),  #132
    ('_int',[(0,19)]),  #133
    ('_struct',[[('m_decrementMs',133,-1)]]),  #134
    ('_struct',[[('m_portraitId',66,-1)]]),  #135
    ('_struct',[[('m_functionName',15,-1)]]),  #136
    ('_struct',[[('m_result',66,-1)]]),  #137
    ('_struct',[[('m_gameMenuItemIndex',66,-1)]]),  #138
    ('_struct',[[('m_reason',94,-1)]]),  #139
    ('_struct',[[('m_purchaseCategoryId',66,-1)]]),  #140
    ('_struct',[[('m_button',71,-1)]]),  #141
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_point',67,-1)]]),  #143
    ('_struct',[[('m_progress',66,-1)]]),  #144
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (64, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SBankSignatureEvent'),
    12: (63, 'NNet.Game.SUserOptionsEvent'),
    22: (65, 'NNet.Game.SSaveGameEvent'),
    23: (64, 'NNet.Game.SSaveGameDoneEvent'),
    25: (64, 'NNet.Game.SPlayerLeaveEvent'),
    26: (69, 'NNet.Game.SGameCheatEvent'),
    27: (80, 'NNet.Game.SCmdEvent'),
    28: (87, 'NNet.Game.SSelectionDeltaEvent'),
    29: (88, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (90, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (92, 'NNet.Game.SResourceTradeEvent'),
    32: (93, 'NNet.Game.STriggerChatMessageEvent'),
    33: (96, 'NNet.Game.SAICommunicateEvent'),
    34: (97, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (98, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (99, 'NNet.Game.SBroadcastCheatEvent'),
    38: (100, 'NNet.Game.SAllianceEvent'),
    39: (101, 'NNet.Game.SUnitClickEvent'),
    40: (102, 'NNet.Game.SUnitHighlightEvent'),
    41: (103, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (64, 'NNet.Game.STriggerSkippedEvent'),
    45: (108, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (111, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (112, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (112, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (115, 'NNet.Game.SCameraUpdateEvent'),
    50: (64, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (104, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (64, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (105, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (64, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (107, 'NNet.Game.STriggerDialogControlEvent'),
    56: (110, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (117, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (120, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (121, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (64, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (122, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (123, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (124, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (136, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (64, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (64, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (125, 'NNet.Game.SResourceRequestEvent'),
    71: (126, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (127, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (64, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (64, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (128, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (129, 'NNet.Game.SLagMessageEvent'),
    77: (64, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (64, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (130, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (64, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (64, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (131, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (132, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (132, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (105, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (64, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (64, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (134, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (135, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (137, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (138, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (139, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (104, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (140, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (141, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (64, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (142, 'NNet.Game.SChatMessage'),
    1: (143, 'NNet.Game.SPingMessage'),
    2: (144, 'NNet.Game.SLoadingProgressMessage'),
    3: (64, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol18574
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_struct',[[('m_control',10,-10),('m_userId',47,-9),('m_teamId',1,-8),('m_colorPref',49,-7),('m_racePref',34,-6),('m_difficulty',2,-5),('m_handicap',0,-4),('m_observe',19,-3),('m_rewards',50,-2),('m_toonHandle',15,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',52,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #53
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',53,-1)]]),  #54
    ('_struct',[[('m_syncLobbyState',54,-1)]]),  #55
    ('_struct',[[('m_name',15,-1)]]),  #56
    ('_blob',[(0,6)]),  #57
    ('_struct',[[('m_name',57,-1)]]),  #58
    ('_struct',[[('m_name',57,-3),('m_type',5,-2),('m_data',15,-1)]]),  #59
    ('_struct',[[('m_type',5,-3),('m_name',57,-2),('m_data',28,-1)]]),  #60
    ('_array',[(0,5),10]),  #61
    ('_struct',[[('m_signature',61,-1)]]),  #62
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #63
    ('_struct',[[]]),  #64
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #65
    ('_int',[(-2147483648,32)]),  #66
    ('_struct',[[('x',66,-2),('y',66,-1)]]),  #67
    ('_struct',[[('m_point',67,-4),('m_time',66,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #68
    ('_struct',[[('m_data',68,-1)]]),  #69
    ('_int',[(0,18)]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #72
    ('_optional',[72]),  #73
    ('_null',[]),  #74
    ('_int',[(0,20)]),  #75
    ('_struct',[[('x',75,-3),('y',75,-2),('z',66,-1)]]),  #76
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',71,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',76,-1)]]),  #77
    ('_choice',[(0,2),{0:('None',74),1:('TargetPoint',76),2:('TargetUnit',77),3:('Data',5)}]),  #78
    ('_optional',[5]),  #79
    ('_struct',[[('m_cmdFlags',70,-4),('m_abil',73,-3),('m_data',78,-2),('m_otherUnit',79,-1)]]),  #80
    ('_array',[(0,8),10]),  #81
    ('_choice',[(0,2),{0:('None',74),1:('Mask',42),2:('OneIndices',81),3:('ZeroIndices',81)}]),  #82
    ('_struct',[[('m_unitLink',71,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #83
    ('_array',[(0,8),83]),  #84
    ('_array',[(0,8),5]),  #85
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',82,-3),('m_addSubgroups',84,-2),('m_addUnitTags',85,-1)]]),  #86
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',82,-1)]]),  #88
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',89,-1)]]),  #90
    ('_array',[(0,3),66]),  #91
    ('_struct',[[('m_recipientId',1,-2),('m_resources',91,-1)]]),  #92
    ('_struct',[[('m_chatMessage',23,-1)]]),  #93
    ('_int',[(-128,8)]),  #94
    ('_struct',[[('x',66,-3),('y',66,-2),('z',66,-1)]]),  #95
    ('_struct',[[('m_beacon',94,-7),('m_ally',94,-6),('m_autocast',94,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',71,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',95,-1)]]),  #96
    ('_struct',[[('m_speed',12,-1)]]),  #97
    ('_struct',[[('m_delta',94,-1)]]),  #98
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #99
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #100
    ('_struct',[[('m_unitTag',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #102
    ('_struct',[[('m_conversationId',66,-2),('m_replyId',66,-1)]]),  #103
    ('_struct',[[('m_purchaseItemId',66,-1)]]),  #104
    ('_struct',[[('m_difficultyLevel',66,-1)]]),  #105
    ('_choice',[(0,3),{0:('None',74),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',66),4:('TextChanged',24)}]),  #106
    ('_struct',[[('m_controlId',66,-3),('m_eventType',66,-2),('m_eventData',106,-1)]]),  #107
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #108
    ('_struct',[[('m_soundHash',85,-2),('m_length',85,-1)]]),  #109
    ('_struct',[[('m_syncInfo',109,-1)]]),  #110
    ('_struct',[[('m_sound',5,-1)]]),  #111
    ('_struct',[[('m_transmissionId',66,-1)]]),  #112
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #113
    ('_optional',[71]),  #114
    ('_struct',[[('m_target',113,-4),('m_distance',114,-3),('m_pitch',114,-2),('m_yaw',114,-1)]]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_skipType',116,-1)]]),  #117
    ('_int',[(0,11)]),  #118
    ('_struct',[[('x',118,-2),('y',118,-1)]]),  #119
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #120
    ('_struct',[[('m_posUI',119,-2),('m_posWorld',76,-1)]]),  #121
    ('_struct',[[('m_soundtrack',5,-1)]]),  #122
    ('_struct',[[('m_planetId',66,-1)]]),  #123
    ('_struct',[[('m_key',94,-2),('m_flags',94,-1)]]),  #124
    ('_struct',[[('m_resources',91,-1)]]),  #125
    ('_struct',[[('m_fulfillRequestId',66,-1)]]),  #126
    ('_struct',[[('m_cancelRequestId',66,-1)]]),  #127
    ('_struct',[[('m_researchItemId',66,-1)]]),  #128
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #129
    ('_struct',[[('m_mercenaryId',66,-1)]]),  #130
    ('_struct',[[('m_battleReportId',66,-2),('m_difficultyLevel',66,-1)]]),  #131
    ('_struct',[[('m_battleReportId',66,-1)]]),  #132
    ('_int',[(0,19)]),  #133
    ('_struct',[[('m_decrementMs',133,-1)]]),  #134
    ('_struct',[[('m_portraitId',66,-1)]]),  #135
    ('_struct',[[('m_functionName',15,-1)]]),  #136
    ('_struct',[[('m_result',66,-1)]]),  #137
    ('_struct',[[('m_gameMenuItemIndex',66,-1)]]),  #138
    ('_struct',[[('m_reason',94,-1)]]),  #139
    ('_struct',[[('m_purchaseCategoryId',66,-1)]]),  #140
    ('_struct',[[('m_button',71,-1)]]),  #141
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_point',67,-1)]]),  #143
    ('_struct',[[('m_progress',66,-1)]]),  #144
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (64, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (56, 'NNet.Game.SBankFileEvent'),
    8: (58, 'NNet.Game.SBankSectionEvent'),
    9: (59, 'NNet.Game.SBankKeyEvent'),
    10: (60, 'NNet.Game.SBankValueEvent'),
    11: (62, 'NNet.Game.SBankSignatureEvent'),
    12: (63, 'NNet.Game.SUserOptionsEvent'),
    22: (65, 'NNet.Game.SSaveGameEvent'),
    23: (64, 'NNet.Game.SSaveGameDoneEvent'),
    25: (64, 'NNet.Game.SPlayerLeaveEvent'),
    26: (69, 'NNet.Game.SGameCheatEvent'),
    27: (80, 'NNet.Game.SCmdEvent'),
    28: (87, 'NNet.Game.SSelectionDeltaEvent'),
    29: (88, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (90, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (92, 'NNet.Game.SResourceTradeEvent'),
    32: (93, 'NNet.Game.STriggerChatMessageEvent'),
    33: (96, 'NNet.Game.SAICommunicateEvent'),
    34: (97, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (98, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (99, 'NNet.Game.SBroadcastCheatEvent'),
    38: (100, 'NNet.Game.SAllianceEvent'),
    39: (101, 'NNet.Game.SUnitClickEvent'),
    40: (102, 'NNet.Game.SUnitHighlightEvent'),
    41: (103, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (64, 'NNet.Game.STriggerSkippedEvent'),
    45: (108, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (111, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (112, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (112, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (115, 'NNet.Game.SCameraUpdateEvent'),
    50: (64, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (104, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (64, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (105, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (64, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (107, 'NNet.Game.STriggerDialogControlEvent'),
    56: (110, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (117, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (120, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (121, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (64, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (122, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (123, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (124, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (136, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (64, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (64, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (125, 'NNet.Game.SResourceRequestEvent'),
    71: (126, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (127, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (64, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (64, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (128, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (129, 'NNet.Game.SLagMessageEvent'),
    77: (64, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (64, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (130, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (64, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (64, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (131, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (132, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (132, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (105, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (64, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (64, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (134, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (135, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (137, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (138, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (139, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (104, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (140, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (141, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (64, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (142, 'NNet.Game.SChatMessage'),
    1: (143, 'NNet.Game.SPingMessage'),
    2: (144, 'NNet.Game.SLoadingProgressMessage'),
    3: (64, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 55


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol19132
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_array',[(0,9),5]),  #51
    ('_struct',[[('m_control',10,-11),('m_userId',47,-10),('m_teamId',1,-9),('m_colorPref',49,-8),('m_racePref',34,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',50,-3),('m_toonHandle',15,-2),('m_licenses',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_array',[(0,5),10]),  #62
    ('_struct',[[('m_signature',62,-1)]]),  #63
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #64
    ('_struct',[[]]),  #65
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #66
    ('_int',[(-2147483648,32)]),  #67
    ('_struct',[[('x',67,-2),('y',67,-1)]]),  #68
    ('_struct',[[('m_point',68,-4),('m_time',67,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #69
    ('_struct',[[('m_data',69,-1)]]),  #70
    ('_int',[(0,18)]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #73
    ('_optional',[73]),  #74
    ('_null',[]),  #75
    ('_int',[(0,20)]),  #76
    ('_struct',[[('x',76,-3),('y',76,-2),('z',67,-1)]]),  #77
    ('_struct',[[('m_targetUnitFlags',10,-6),('m_timer',10,-5),('m_tag',5,-4),('m_snapshotUnitLink',72,-3),('m_snapshotPlayerId',47,-2),('m_snapshotPoint',77,-1)]]),  #78
    ('_choice',[(0,2),{0:('None',75),1:('TargetPoint',77),2:('TargetUnit',78),3:('Data',5)}]),  #79
    ('_optional',[5]),  #80
    ('_struct',[[('m_cmdFlags',71,-4),('m_abil',74,-3),('m_data',79,-2),('m_otherUnit',80,-1)]]),  #81
    ('_array',[(0,8),10]),  #82
    ('_choice',[(0,2),{0:('None',75),1:('Mask',42),2:('OneIndices',82),3:('ZeroIndices',82)}]),  #83
    ('_struct',[[('m_unitLink',72,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #84
    ('_array',[(0,8),84]),  #85
    ('_array',[(0,8),5]),  #86
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',83,-3),('m_addSubgroups',85,-2),('m_addUnitTags',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',87,-1)]]),  #88
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',83,-1)]]),  #89
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #90
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',90,-1)]]),  #91
    ('_array',[(0,3),67]),  #92
    ('_struct',[[('m_recipientId',1,-2),('m_resources',92,-1)]]),  #93
    ('_struct',[[('m_chatMessage',23,-1)]]),  #94
    ('_int',[(-128,8)]),  #95
    ('_struct',[[('x',67,-3),('y',67,-2),('z',67,-1)]]),  #96
    ('_struct',[[('m_beacon',95,-7),('m_ally',95,-6),('m_autocast',95,-5),('m_targetUnitTag',5,-4),('m_targetUnitSnapshotUnitLink',72,-3),('m_targetUnitSnapshotPlayerId',47,-2),('m_targetPoint',96,-1)]]),  #97
    ('_struct',[[('m_speed',12,-1)]]),  #98
    ('_struct',[[('m_delta',95,-1)]]),  #99
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #100
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-1)]]),  #102
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #103
    ('_struct',[[('m_conversationId',67,-2),('m_replyId',67,-1)]]),  #104
    ('_struct',[[('m_purchaseItemId',67,-1)]]),  #105
    ('_struct',[[('m_difficultyLevel',67,-1)]]),  #106
    ('_choice',[(0,3),{0:('None',75),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',67),4:('TextChanged',24)}]),  #107
    ('_struct',[[('m_controlId',67,-3),('m_eventType',67,-2),('m_eventData',107,-1)]]),  #108
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #109
    ('_struct',[[('m_soundHash',86,-2),('m_length',86,-1)]]),  #110
    ('_struct',[[('m_syncInfo',110,-1)]]),  #111
    ('_struct',[[('m_sound',5,-1)]]),  #112
    ('_struct',[[('m_transmissionId',67,-1)]]),  #113
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #114
    ('_optional',[72]),  #115
    ('_struct',[[('m_target',114,-4),('m_distance',115,-3),('m_pitch',115,-2),('m_yaw',115,-1)]]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_skipType',117,-1)]]),  #118
    ('_int',[(0,11)]),  #119
    ('_struct',[[('x',119,-2),('y',119,-1)]]),  #120
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #121
    ('_struct',[[('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #122
    ('_struct',[[('m_soundtrack',5,-1)]]),  #123
    ('_struct',[[('m_planetId',67,-1)]]),  #124
    ('_struct',[[('m_key',95,-2),('m_flags',95,-1)]]),  #125
    ('_struct',[[('m_resources',92,-1)]]),  #126
    ('_struct',[[('m_fulfillRequestId',67,-1)]]),  #127
    ('_struct',[[('m_cancelRequestId',67,-1)]]),  #128
    ('_struct',[[('m_researchItemId',67,-1)]]),  #129
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #130
    ('_struct',[[('m_mercenaryId',67,-1)]]),  #131
    ('_struct',[[('m_battleReportId',67,-2),('m_difficultyLevel',67,-1)]]),  #132
    ('_struct',[[('m_battleReportId',67,-1)]]),  #133
    ('_int',[(0,19)]),  #134
    ('_struct',[[('m_decrementMs',134,-1)]]),  #135
    ('_struct',[[('m_portraitId',67,-1)]]),  #136
    ('_struct',[[('m_functionName',15,-1)]]),  #137
    ('_struct',[[('m_result',67,-1)]]),  #138
    ('_struct',[[('m_gameMenuItemIndex',67,-1)]]),  #139
    ('_struct',[[('m_reason',95,-1)]]),  #140
    ('_struct',[[('m_purchaseCategoryId',67,-1)]]),  #141
    ('_struct',[[('m_button',72,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #143
    ('_struct',[[('m_recipient',19,-2),('m_point',68,-1)]]),  #144
    ('_struct',[[('m_progress',67,-1)]]),  #145
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (65, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (63, 'NNet.Game.SBankSignatureEvent'),
    12: (64, 'NNet.Game.SUserOptionsEvent'),
    22: (66, 'NNet.Game.SSaveGameEvent'),
    23: (65, 'NNet.Game.SSaveGameDoneEvent'),
    25: (65, 'NNet.Game.SPlayerLeaveEvent'),
    26: (70, 'NNet.Game.SGameCheatEvent'),
    27: (81, 'NNet.Game.SCmdEvent'),
    28: (88, 'NNet.Game.SSelectionDeltaEvent'),
    29: (89, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (91, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (93, 'NNet.Game.SResourceTradeEvent'),
    32: (94, 'NNet.Game.STriggerChatMessageEvent'),
    33: (97, 'NNet.Game.SAICommunicateEvent'),
    34: (98, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (99, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (100, 'NNet.Game.SBroadcastCheatEvent'),
    38: (101, 'NNet.Game.SAllianceEvent'),
    39: (102, 'NNet.Game.SUnitClickEvent'),
    40: (103, 'NNet.Game.SUnitHighlightEvent'),
    41: (104, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (65, 'NNet.Game.STriggerSkippedEvent'),
    45: (109, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (112, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (113, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (113, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (116, 'NNet.Game.SCameraUpdateEvent'),
    50: (65, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (105, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (65, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (106, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (65, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (108, 'NNet.Game.STriggerDialogControlEvent'),
    56: (111, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (118, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (121, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (122, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (65, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (123, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (124, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (125, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (137, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (65, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (65, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (126, 'NNet.Game.SResourceRequestEvent'),
    71: (127, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (128, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (65, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (65, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (129, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (130, 'NNet.Game.SLagMessageEvent'),
    77: (65, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (65, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (131, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (65, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (65, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (132, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (133, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (133, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (106, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (65, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (65, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (135, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (136, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (138, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (139, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (140, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (105, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (141, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (142, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (65, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (143, 'NNet.Game.SChatMessage'),
    1: (144, 'NNet.Game.SPingMessage'),
    2: (145, 'NNet.Game.SLoadingProgressMessage'),
    3: (65, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol19458
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_array',[(0,9),5]),  #51
    ('_struct',[[('m_control',10,-11),('m_userId',47,-10),('m_teamId',1,-9),('m_colorPref',49,-8),('m_racePref',34,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',50,-3),('m_toonHandle',15,-2),('m_licenses',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_array',[(0,5),10]),  #62
    ('_struct',[[('m_signature',62,-1)]]),  #63
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #64
    ('_struct',[[]]),  #65
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #66
    ('_int',[(-2147483648,32)]),  #67
    ('_struct',[[('x',67,-2),('y',67,-1)]]),  #68
    ('_struct',[[('m_point',68,-4),('m_time',67,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #69
    ('_struct',[[('m_data',69,-1)]]),  #70
    ('_int',[(0,18)]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #73
    ('_optional',[73]),  #74
    ('_null',[]),  #75
    ('_int',[(0,20)]),  #76
    ('_struct',[[('x',76,-3),('y',76,-2),('z',67,-1)]]),  #77
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',72,-4),('m_snapshotControlPlayerId',47,-3),('m_snapshotUpkeepPlayerId',47,-2),('m_snapshotPoint',77,-1)]]),  #78
    ('_choice',[(0,2),{0:('None',75),1:('TargetPoint',77),2:('TargetUnit',78),3:('Data',5)}]),  #79
    ('_optional',[5]),  #80
    ('_struct',[[('m_cmdFlags',71,-4),('m_abil',74,-3),('m_data',79,-2),('m_otherUnit',80,-1)]]),  #81
    ('_array',[(0,8),10]),  #82
    ('_choice',[(0,2),{0:('None',75),1:('Mask',42),2:('OneIndices',82),3:('ZeroIndices',82)}]),  #83
    ('_struct',[[('m_unitLink',72,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #84
    ('_array',[(0,8),84]),  #85
    ('_array',[(0,8),5]),  #86
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',83,-3),('m_addSubgroups',85,-2),('m_addUnitTags',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',87,-1)]]),  #88
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',83,-1)]]),  #89
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #90
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',90,-1)]]),  #91
    ('_array',[(0,3),67]),  #92
    ('_struct',[[('m_recipientId',1,-2),('m_resources',92,-1)]]),  #93
    ('_struct',[[('m_chatMessage',23,-1)]]),  #94
    ('_int',[(-128,8)]),  #95
    ('_struct',[[('x',67,-3),('y',67,-2),('z',67,-1)]]),  #96
    ('_struct',[[('m_beacon',95,-8),('m_ally',95,-7),('m_autocast',95,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',72,-4),('m_targetUnitSnapshotUpkeepPlayerId',47,-3),('m_targetUnitSnapshotControlPlayerId',47,-2),('m_targetPoint',96,-1)]]),  #97
    ('_struct',[[('m_speed',12,-1)]]),  #98
    ('_struct',[[('m_delta',95,-1)]]),  #99
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #100
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-1)]]),  #102
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #103
    ('_struct',[[('m_conversationId',67,-2),('m_replyId',67,-1)]]),  #104
    ('_struct',[[('m_purchaseItemId',67,-1)]]),  #105
    ('_struct',[[('m_difficultyLevel',67,-1)]]),  #106
    ('_choice',[(0,3),{0:('None',75),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',67),4:('TextChanged',24)}]),  #107
    ('_struct',[[('m_controlId',67,-3),('m_eventType',67,-2),('m_eventData',107,-1)]]),  #108
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #109
    ('_struct',[[('m_soundHash',86,-2),('m_length',86,-1)]]),  #110
    ('_struct',[[('m_syncInfo',110,-1)]]),  #111
    ('_struct',[[('m_sound',5,-1)]]),  #112
    ('_struct',[[('m_transmissionId',67,-1)]]),  #113
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #114
    ('_optional',[72]),  #115
    ('_struct',[[('m_target',114,-4),('m_distance',115,-3),('m_pitch',115,-2),('m_yaw',115,-1)]]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_skipType',117,-1)]]),  #118
    ('_int',[(0,11)]),  #119
    ('_struct',[[('x',119,-2),('y',119,-1)]]),  #120
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #121
    ('_struct',[[('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #122
    ('_struct',[[('m_soundtrack',5,-1)]]),  #123
    ('_struct',[[('m_planetId',67,-1)]]),  #124
    ('_struct',[[('m_key',95,-2),('m_flags',95,-1)]]),  #125
    ('_struct',[[('m_resources',92,-1)]]),  #126
    ('_struct',[[('m_fulfillRequestId',67,-1)]]),  #127
    ('_struct',[[('m_cancelRequestId',67,-1)]]),  #128
    ('_struct',[[('m_researchItemId',67,-1)]]),  #129
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #130
    ('_struct',[[('m_mercenaryId',67,-1)]]),  #131
    ('_struct',[[('m_battleReportId',67,-2),('m_difficultyLevel',67,-1)]]),  #132
    ('_struct',[[('m_battleReportId',67,-1)]]),  #133
    ('_int',[(0,19)]),  #134
    ('_struct',[[('m_decrementMs',134,-1)]]),  #135
    ('_struct',[[('m_portraitId',67,-1)]]),  #136
    ('_struct',[[('m_functionName',15,-1)]]),  #137
    ('_struct',[[('m_result',67,-1)]]),  #138
    ('_struct',[[('m_gameMenuItemIndex',67,-1)]]),  #139
    ('_struct',[[('m_reason',95,-1)]]),  #140
    ('_struct',[[('m_purchaseCategoryId',67,-1)]]),  #141
    ('_struct',[[('m_button',72,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #143
    ('_struct',[[('m_recipient',19,-2),('m_point',68,-1)]]),  #144
    ('_struct',[[('m_progress',67,-1)]]),  #145
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (65, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (63, 'NNet.Game.SBankSignatureEvent'),
    12: (64, 'NNet.Game.SUserOptionsEvent'),
    22: (66, 'NNet.Game.SSaveGameEvent'),
    23: (65, 'NNet.Game.SSaveGameDoneEvent'),
    25: (65, 'NNet.Game.SPlayerLeaveEvent'),
    26: (70, 'NNet.Game.SGameCheatEvent'),
    27: (81, 'NNet.Game.SCmdEvent'),
    28: (88, 'NNet.Game.SSelectionDeltaEvent'),
    29: (89, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (91, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (93, 'NNet.Game.SResourceTradeEvent'),
    32: (94, 'NNet.Game.STriggerChatMessageEvent'),
    33: (97, 'NNet.Game.SAICommunicateEvent'),
    34: (98, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (99, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (100, 'NNet.Game.SBroadcastCheatEvent'),
    38: (101, 'NNet.Game.SAllianceEvent'),
    39: (102, 'NNet.Game.SUnitClickEvent'),
    40: (103, 'NNet.Game.SUnitHighlightEvent'),
    41: (104, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (65, 'NNet.Game.STriggerSkippedEvent'),
    45: (109, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (112, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (113, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (113, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (116, 'NNet.Game.SCameraUpdateEvent'),
    50: (65, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (105, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (65, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (106, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (65, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (108, 'NNet.Game.STriggerDialogControlEvent'),
    56: (111, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (118, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (121, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (122, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (65, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (123, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (124, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (125, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (137, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (65, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (65, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (126, 'NNet.Game.SResourceRequestEvent'),
    71: (127, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (128, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (65, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (65, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (129, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (130, 'NNet.Game.SLagMessageEvent'),
    77: (65, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (65, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (131, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (65, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (65, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (132, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (133, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (133, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (106, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (65, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (65, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (135, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (136, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (138, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (139, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (140, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (105, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (141, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (142, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (65, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (143, 'NNet.Game.SChatMessage'),
    1: (144, 'NNet.Game.SPingMessage'),
    2: (145, 'NNet.Game.SLoadingProgressMessage'),
    3: (65, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol19595
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_array',[(0,9),5]),  #51
    ('_struct',[[('m_control',10,-11),('m_userId',47,-10),('m_teamId',1,-9),('m_colorPref',49,-8),('m_racePref',34,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',50,-3),('m_toonHandle',15,-2),('m_licenses',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_array',[(0,5),10]),  #62
    ('_struct',[[('m_signature',62,-1)]]),  #63
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #64
    ('_struct',[[]]),  #65
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #66
    ('_int',[(-2147483648,32)]),  #67
    ('_struct',[[('x',67,-2),('y',67,-1)]]),  #68
    ('_struct',[[('m_point',68,-4),('m_time',67,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #69
    ('_struct',[[('m_data',69,-1)]]),  #70
    ('_int',[(0,18)]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #73
    ('_optional',[73]),  #74
    ('_null',[]),  #75
    ('_int',[(0,20)]),  #76
    ('_struct',[[('x',76,-3),('y',76,-2),('z',67,-1)]]),  #77
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',72,-4),('m_snapshotControlPlayerId',47,-3),('m_snapshotUpkeepPlayerId',47,-2),('m_snapshotPoint',77,-1)]]),  #78
    ('_choice',[(0,2),{0:('None',75),1:('TargetPoint',77),2:('TargetUnit',78),3:('Data',5)}]),  #79
    ('_optional',[5]),  #80
    ('_struct',[[('m_cmdFlags',71,-4),('m_abil',74,-3),('m_data',79,-2),('m_otherUnit',80,-1)]]),  #81
    ('_array',[(0,8),10]),  #82
    ('_choice',[(0,2),{0:('None',75),1:('Mask',42),2:('OneIndices',82),3:('ZeroIndices',82)}]),  #83
    ('_struct',[[('m_unitLink',72,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #84
    ('_array',[(0,8),84]),  #85
    ('_array',[(0,8),5]),  #86
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',83,-3),('m_addSubgroups',85,-2),('m_addUnitTags',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',87,-1)]]),  #88
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',83,-1)]]),  #89
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #90
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',90,-1)]]),  #91
    ('_array',[(0,3),67]),  #92
    ('_struct',[[('m_recipientId',1,-2),('m_resources',92,-1)]]),  #93
    ('_struct',[[('m_chatMessage',23,-1)]]),  #94
    ('_int',[(-128,8)]),  #95
    ('_struct',[[('x',67,-3),('y',67,-2),('z',67,-1)]]),  #96
    ('_struct',[[('m_beacon',95,-8),('m_ally',95,-7),('m_autocast',95,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',72,-4),('m_targetUnitSnapshotUpkeepPlayerId',47,-3),('m_targetUnitSnapshotControlPlayerId',47,-2),('m_targetPoint',96,-1)]]),  #97
    ('_struct',[[('m_speed',12,-1)]]),  #98
    ('_struct',[[('m_delta',95,-1)]]),  #99
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #100
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-1)]]),  #102
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #103
    ('_struct',[[('m_conversationId',67,-2),('m_replyId',67,-1)]]),  #104
    ('_struct',[[('m_purchaseItemId',67,-1)]]),  #105
    ('_struct',[[('m_difficultyLevel',67,-1)]]),  #106
    ('_choice',[(0,3),{0:('None',75),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',67),4:('TextChanged',24)}]),  #107
    ('_struct',[[('m_controlId',67,-3),('m_eventType',67,-2),('m_eventData',107,-1)]]),  #108
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #109
    ('_struct',[[('m_soundHash',86,-2),('m_length',86,-1)]]),  #110
    ('_struct',[[('m_syncInfo',110,-1)]]),  #111
    ('_struct',[[('m_sound',5,-1)]]),  #112
    ('_struct',[[('m_transmissionId',67,-1)]]),  #113
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #114
    ('_optional',[72]),  #115
    ('_struct',[[('m_target',114,-4),('m_distance',115,-3),('m_pitch',115,-2),('m_yaw',115,-1)]]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_skipType',117,-1)]]),  #118
    ('_int',[(0,11)]),  #119
    ('_struct',[[('x',119,-2),('y',119,-1)]]),  #120
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #121
    ('_struct',[[('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #122
    ('_struct',[[('m_soundtrack',5,-1)]]),  #123
    ('_struct',[[('m_planetId',67,-1)]]),  #124
    ('_struct',[[('m_key',95,-2),('m_flags',95,-1)]]),  #125
    ('_struct',[[('m_resources',92,-1)]]),  #126
    ('_struct',[[('m_fulfillRequestId',67,-1)]]),  #127
    ('_struct',[[('m_cancelRequestId',67,-1)]]),  #128
    ('_struct',[[('m_researchItemId',67,-1)]]),  #129
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #130
    ('_struct',[[('m_mercenaryId',67,-1)]]),  #131
    ('_struct',[[('m_battleReportId',67,-2),('m_difficultyLevel',67,-1)]]),  #132
    ('_struct',[[('m_battleReportId',67,-1)]]),  #133
    ('_int',[(0,19)]),  #134
    ('_struct',[[('m_decrementMs',134,-1)]]),  #135
    ('_struct',[[('m_portraitId',67,-1)]]),  #136
    ('_struct',[[('m_functionName',15,-1)]]),  #137
    ('_struct',[[('m_result',67,-1)]]),  #138
    ('_struct',[[('m_gameMenuItemIndex',67,-1)]]),  #139
    ('_struct',[[('m_reason',95,-1)]]),  #140
    ('_struct',[[('m_purchaseCategoryId',67,-1)]]),  #141
    ('_struct',[[('m_button',72,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #143
    ('_struct',[[('m_recipient',19,-2),('m_point',68,-1)]]),  #144
    ('_struct',[[('m_progress',67,-1)]]),  #145
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (65, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (63, 'NNet.Game.SBankSignatureEvent'),
    12: (64, 'NNet.Game.SUserOptionsEvent'),
    22: (66, 'NNet.Game.SSaveGameEvent'),
    23: (65, 'NNet.Game.SSaveGameDoneEvent'),
    25: (65, 'NNet.Game.SPlayerLeaveEvent'),
    26: (70, 'NNet.Game.SGameCheatEvent'),
    27: (81, 'NNet.Game.SCmdEvent'),
    28: (88, 'NNet.Game.SSelectionDeltaEvent'),
    29: (89, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (91, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (93, 'NNet.Game.SResourceTradeEvent'),
    32: (94, 'NNet.Game.STriggerChatMessageEvent'),
    33: (97, 'NNet.Game.SAICommunicateEvent'),
    34: (98, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (99, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (100, 'NNet.Game.SBroadcastCheatEvent'),
    38: (101, 'NNet.Game.SAllianceEvent'),
    39: (102, 'NNet.Game.SUnitClickEvent'),
    40: (103, 'NNet.Game.SUnitHighlightEvent'),
    41: (104, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (65, 'NNet.Game.STriggerSkippedEvent'),
    45: (109, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (112, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (113, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (113, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (116, 'NNet.Game.SCameraUpdateEvent'),
    50: (65, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (105, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (65, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (106, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (65, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (108, 'NNet.Game.STriggerDialogControlEvent'),
    56: (111, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (118, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (121, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (122, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (65, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (123, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (124, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (125, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (137, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (65, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (65, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (126, 'NNet.Game.SResourceRequestEvent'),
    71: (127, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (128, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (65, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (65, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (129, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (130, 'NNet.Game.SLagMessageEvent'),
    77: (65, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (65, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (131, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (65, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (65, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (132, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (133, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (133, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (106, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (65, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (65, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (135, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (136, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (138, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (139, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (140, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (105, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (141, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (142, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (65, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (143, 'NNet.Game.SChatMessage'),
    1: (144, 'NNet.Game.SPingMessage'),
    2: (145, 'NNet.Game.SLoadingProgressMessage'),
    3: (65, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol19679
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_array',[(0,9),5]),  #51
    ('_struct',[[('m_control',10,-11),('m_userId',47,-10),('m_teamId',1,-9),('m_colorPref',49,-8),('m_racePref',34,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',50,-3),('m_toonHandle',15,-2),('m_licenses',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_array',[(0,5),10]),  #62
    ('_struct',[[('m_signature',62,-1)]]),  #63
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #64
    ('_struct',[[]]),  #65
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #66
    ('_int',[(-2147483648,32)]),  #67
    ('_struct',[[('x',67,-2),('y',67,-1)]]),  #68
    ('_struct',[[('m_point',68,-4),('m_time',67,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #69
    ('_struct',[[('m_data',69,-1)]]),  #70
    ('_int',[(0,18)]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #73
    ('_optional',[73]),  #74
    ('_null',[]),  #75
    ('_int',[(0,20)]),  #76
    ('_struct',[[('x',76,-3),('y',76,-2),('z',67,-1)]]),  #77
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',72,-4),('m_snapshotControlPlayerId',47,-3),('m_snapshotUpkeepPlayerId',47,-2),('m_snapshotPoint',77,-1)]]),  #78
    ('_choice',[(0,2),{0:('None',75),1:('TargetPoint',77),2:('TargetUnit',78),3:('Data',5)}]),  #79
    ('_optional',[5]),  #80
    ('_struct',[[('m_cmdFlags',71,-4),('m_abil',74,-3),('m_data',79,-2),('m_otherUnit',80,-1)]]),  #81
    ('_array',[(0,8),10]),  #82
    ('_choice',[(0,2),{0:('None',75),1:('Mask',42),2:('OneIndices',82),3:('ZeroIndices',82)}]),  #83
    ('_struct',[[('m_unitLink',72,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #84
    ('_array',[(0,8),84]),  #85
    ('_array',[(0,8),5]),  #86
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',83,-3),('m_addSubgroups',85,-2),('m_addUnitTags',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',87,-1)]]),  #88
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',83,-1)]]),  #89
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #90
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',90,-1)]]),  #91
    ('_array',[(0,3),67]),  #92
    ('_struct',[[('m_recipientId',1,-2),('m_resources',92,-1)]]),  #93
    ('_struct',[[('m_chatMessage',23,-1)]]),  #94
    ('_int',[(-128,8)]),  #95
    ('_struct',[[('x',67,-3),('y',67,-2),('z',67,-1)]]),  #96
    ('_struct',[[('m_beacon',95,-8),('m_ally',95,-7),('m_autocast',95,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',72,-4),('m_targetUnitSnapshotUpkeepPlayerId',47,-3),('m_targetUnitSnapshotControlPlayerId',47,-2),('m_targetPoint',96,-1)]]),  #97
    ('_struct',[[('m_speed',12,-1)]]),  #98
    ('_struct',[[('m_delta',95,-1)]]),  #99
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #100
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-1)]]),  #102
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #103
    ('_struct',[[('m_conversationId',67,-2),('m_replyId',67,-1)]]),  #104
    ('_struct',[[('m_purchaseItemId',67,-1)]]),  #105
    ('_struct',[[('m_difficultyLevel',67,-1)]]),  #106
    ('_choice',[(0,3),{0:('None',75),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',67),4:('TextChanged',24)}]),  #107
    ('_struct',[[('m_controlId',67,-3),('m_eventType',67,-2),('m_eventData',107,-1)]]),  #108
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #109
    ('_struct',[[('m_soundHash',86,-2),('m_length',86,-1)]]),  #110
    ('_struct',[[('m_syncInfo',110,-1)]]),  #111
    ('_struct',[[('m_sound',5,-1)]]),  #112
    ('_struct',[[('m_transmissionId',67,-1)]]),  #113
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #114
    ('_optional',[72]),  #115
    ('_struct',[[('m_target',114,-4),('m_distance',115,-3),('m_pitch',115,-2),('m_yaw',115,-1)]]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_skipType',117,-1)]]),  #118
    ('_int',[(0,11)]),  #119
    ('_struct',[[('x',119,-2),('y',119,-1)]]),  #120
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #121
    ('_struct',[[('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #122
    ('_struct',[[('m_soundtrack',5,-1)]]),  #123
    ('_struct',[[('m_planetId',67,-1)]]),  #124
    ('_struct',[[('m_key',95,-2),('m_flags',95,-1)]]),  #125
    ('_struct',[[('m_resources',92,-1)]]),  #126
    ('_struct',[[('m_fulfillRequestId',67,-1)]]),  #127
    ('_struct',[[('m_cancelRequestId',67,-1)]]),  #128
    ('_struct',[[('m_researchItemId',67,-1)]]),  #129
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #130
    ('_struct',[[('m_mercenaryId',67,-1)]]),  #131
    ('_struct',[[('m_battleReportId',67,-2),('m_difficultyLevel',67,-1)]]),  #132
    ('_struct',[[('m_battleReportId',67,-1)]]),  #133
    ('_int',[(0,19)]),  #134
    ('_struct',[[('m_decrementMs',134,-1)]]),  #135
    ('_struct',[[('m_portraitId',67,-1)]]),  #136
    ('_struct',[[('m_functionName',15,-1)]]),  #137
    ('_struct',[[('m_result',67,-1)]]),  #138
    ('_struct',[[('m_gameMenuItemIndex',67,-1)]]),  #139
    ('_struct',[[('m_reason',95,-1)]]),  #140
    ('_struct',[[('m_purchaseCategoryId',67,-1)]]),  #141
    ('_struct',[[('m_button',72,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #143
    ('_struct',[[('m_recipient',19,-2),('m_point',68,-1)]]),  #144
    ('_struct',[[('m_progress',67,-1)]]),  #145
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (65, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (63, 'NNet.Game.SBankSignatureEvent'),
    12: (64, 'NNet.Game.SUserOptionsEvent'),
    22: (66, 'NNet.Game.SSaveGameEvent'),
    23: (65, 'NNet.Game.SSaveGameDoneEvent'),
    25: (65, 'NNet.Game.SPlayerLeaveEvent'),
    26: (70, 'NNet.Game.SGameCheatEvent'),
    27: (81, 'NNet.Game.SCmdEvent'),
    28: (88, 'NNet.Game.SSelectionDeltaEvent'),
    29: (89, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (91, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (93, 'NNet.Game.SResourceTradeEvent'),
    32: (94, 'NNet.Game.STriggerChatMessageEvent'),
    33: (97, 'NNet.Game.SAICommunicateEvent'),
    34: (98, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (99, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (100, 'NNet.Game.SBroadcastCheatEvent'),
    38: (101, 'NNet.Game.SAllianceEvent'),
    39: (102, 'NNet.Game.SUnitClickEvent'),
    40: (103, 'NNet.Game.SUnitHighlightEvent'),
    41: (104, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (65, 'NNet.Game.STriggerSkippedEvent'),
    45: (109, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (112, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (113, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (113, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (116, 'NNet.Game.SCameraUpdateEvent'),
    50: (65, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (105, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (65, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (106, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (65, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (108, 'NNet.Game.STriggerDialogControlEvent'),
    56: (111, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (118, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (121, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (122, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (65, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (123, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (124, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (125, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (137, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (65, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (65, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (126, 'NNet.Game.SResourceRequestEvent'),
    71: (127, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (128, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (65, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (65, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (129, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (130, 'NNet.Game.SLagMessageEvent'),
    77: (65, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (65, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (131, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (65, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (65, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (132, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (133, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (133, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (106, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (65, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (65, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (135, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (136, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (138, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (139, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (140, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (105, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (141, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (142, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (65, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (143, 'NNet.Game.SChatMessage'),
    1: (144, 'NNet.Game.SPingMessage'),
    2: (145, 'NNet.Game.SLoadingProgressMessage'),
    3: (65, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol21029
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,4),29]),  #30
    ('_optional',[30]),  #31
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13)]]),  #32
    ('_optional',[10]),  #33
    ('_struct',[[('m_race',33,-1)]]),  #34
    ('_struct',[[('m_team',33,-1)]]),  #35
    ('_struct',[[('m_name',9,-7),('m_randomSeed',5,-6),('m_racePreference',34,-5),('m_teamPreference',35,-4),('m_testMap',26,-3),('m_testAuto',26,-2),('m_observe',19,-1)]]),  #36
    ('_array',[(0,5),36]),  #37
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #38
    ('_int',[(1,4)]),  #39
    ('_int',[(1,8)]),  #40
    ('_bitarray',[(0,6)]),  #41
    ('_bitarray',[(0,8)]),  #42
    ('_bitarray',[(0,2)]),  #43
    ('_struct',[[('m_allowedColors',41,-5),('m_allowedRaces',42,-4),('m_allowedDifficulty',41,-3),('m_allowedControls',42,-2),('m_allowedObserveTypes',43,-1)]]),  #44
    ('_array',[(0,5),44]),  #45
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',38,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',39,-15),('m_maxColors',2,-14),('m_maxRaces',40,-13),('m_maxControls',40,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',45,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #46
    ('_optional',[1]),  #47
    ('_optional',[7]),  #48
    ('_struct',[[('m_color',48,-1)]]),  #49
    ('_array',[(0,5),5]),  #50
    ('_array',[(0,9),5]),  #51
    ('_struct',[[('m_control',10,-11),('m_userId',47,-10),('m_teamId',1,-9),('m_colorPref',49,-8),('m_racePref',34,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',50,-3),('m_toonHandle',15,-2),('m_licenses',51,-1)]]),  #52
    ('_array',[(0,5),52]),  #53
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',53,-6),('m_randomSeed',5,-5),('m_hostUserId',47,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #54
    ('_struct',[[('m_userInitialData',37,-3),('m_gameDescription',46,-2),('m_lobbyState',54,-1)]]),  #55
    ('_struct',[[('m_syncLobbyState',55,-1)]]),  #56
    ('_struct',[[('m_name',15,-1)]]),  #57
    ('_blob',[(0,6)]),  #58
    ('_struct',[[('m_name',58,-1)]]),  #59
    ('_struct',[[('m_name',58,-3),('m_type',5,-2),('m_data',15,-1)]]),  #60
    ('_struct',[[('m_type',5,-3),('m_name',58,-2),('m_data',28,-1)]]),  #61
    ('_array',[(0,5),10]),  #62
    ('_struct',[[('m_signature',62,-1)]]),  #63
    ('_struct',[[('m_developmentCheatsEnabled',26,-4),('m_multiplayerCheatsEnabled',26,-3),('m_syncChecksummingEnabled',26,-2),('m_isMapToMapTransition',26,-1)]]),  #64
    ('_struct',[[]]),  #65
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #66
    ('_int',[(-2147483648,32)]),  #67
    ('_struct',[[('x',67,-2),('y',67,-1)]]),  #68
    ('_struct',[[('m_point',68,-4),('m_time',67,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #69
    ('_struct',[[('m_data',69,-1)]]),  #70
    ('_int',[(0,18)]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',33,-1)]]),  #73
    ('_optional',[73]),  #74
    ('_null',[]),  #75
    ('_int',[(0,20)]),  #76
    ('_struct',[[('x',76,-3),('y',76,-2),('z',67,-1)]]),  #77
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',72,-4),('m_snapshotControlPlayerId',47,-3),('m_snapshotUpkeepPlayerId',47,-2),('m_snapshotPoint',77,-1)]]),  #78
    ('_choice',[(0,2),{0:('None',75),1:('TargetPoint',77),2:('TargetUnit',78),3:('Data',5)}]),  #79
    ('_optional',[5]),  #80
    ('_struct',[[('m_cmdFlags',71,-4),('m_abil',74,-3),('m_data',79,-2),('m_otherUnit',80,-1)]]),  #81
    ('_array',[(0,8),10]),  #82
    ('_choice',[(0,2),{0:('None',75),1:('Mask',42),2:('OneIndices',82),3:('ZeroIndices',82)}]),  #83
    ('_struct',[[('m_unitLink',72,-3),('m_intraSubgroupPriority',10,-2),('m_count',10,-1)]]),  #84
    ('_array',[(0,8),84]),  #85
    ('_array',[(0,8),5]),  #86
    ('_struct',[[('m_subgroupIndex',10,-4),('m_removeMask',83,-3),('m_addSubgroups',85,-2),('m_addUnitTags',86,-1)]]),  #87
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',87,-1)]]),  #88
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',83,-1)]]),  #89
    ('_struct',[[('m_count',10,-6),('m_subgroupCount',10,-5),('m_activeSubgroupIndex',10,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #90
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',90,-1)]]),  #91
    ('_array',[(0,3),67]),  #92
    ('_struct',[[('m_recipientId',1,-2),('m_resources',92,-1)]]),  #93
    ('_struct',[[('m_chatMessage',23,-1)]]),  #94
    ('_int',[(-128,8)]),  #95
    ('_struct',[[('x',67,-3),('y',67,-2),('z',67,-1)]]),  #96
    ('_struct',[[('m_beacon',95,-8),('m_ally',95,-7),('m_autocast',95,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',72,-4),('m_targetUnitSnapshotUpkeepPlayerId',47,-3),('m_targetUnitSnapshotControlPlayerId',47,-2),('m_targetPoint',96,-1)]]),  #97
    ('_struct',[[('m_speed',12,-1)]]),  #98
    ('_struct',[[('m_delta',95,-1)]]),  #99
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #100
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #101
    ('_struct',[[('m_unitTag',5,-1)]]),  #102
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #103
    ('_struct',[[('m_conversationId',67,-2),('m_replyId',67,-1)]]),  #104
    ('_struct',[[('m_purchaseItemId',67,-1)]]),  #105
    ('_struct',[[('m_difficultyLevel',67,-1)]]),  #106
    ('_choice',[(0,3),{0:('None',75),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',67),4:('TextChanged',24)}]),  #107
    ('_struct',[[('m_controlId',67,-3),('m_eventType',67,-2),('m_eventData',107,-1)]]),  #108
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #109
    ('_struct',[[('m_soundHash',86,-2),('m_length',86,-1)]]),  #110
    ('_struct',[[('m_syncInfo',110,-1)]]),  #111
    ('_struct',[[('m_sound',5,-1)]]),  #112
    ('_struct',[[('m_transmissionId',67,-1)]]),  #113
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #114
    ('_optional',[72]),  #115
    ('_struct',[[('m_target',114,-4),('m_distance',115,-3),('m_pitch',115,-2),('m_yaw',115,-1)]]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_skipType',117,-1)]]),  #118
    ('_int',[(0,11)]),  #119
    ('_struct',[[('x',119,-2),('y',119,-1)]]),  #120
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #121
    ('_struct',[[('m_posUI',120,-2),('m_posWorld',77,-1)]]),  #122
    ('_struct',[[('m_soundtrack',5,-1)]]),  #123
    ('_struct',[[('m_planetId',67,-1)]]),  #124
    ('_struct',[[('m_key',95,-2),('m_flags',95,-1)]]),  #125
    ('_struct',[[('m_resources',92,-1)]]),  #126
    ('_struct',[[('m_fulfillRequestId',67,-1)]]),  #127
    ('_struct',[[('m_cancelRequestId',67,-1)]]),  #128
    ('_struct',[[('m_researchItemId',67,-1)]]),  #129
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #130
    ('_struct',[[('m_mercenaryId',67,-1)]]),  #131
    ('_struct',[[('m_battleReportId',67,-2),('m_difficultyLevel',67,-1)]]),  #132
    ('_struct',[[('m_battleReportId',67,-1)]]),  #133
    ('_int',[(0,19)]),  #134
    ('_struct',[[('m_decrementMs',134,-1)]]),  #135
    ('_struct',[[('m_portraitId',67,-1)]]),  #136
    ('_struct',[[('m_functionName',15,-1)]]),  #137
    ('_struct',[[('m_result',67,-1)]]),  #138
    ('_struct',[[('m_gameMenuItemIndex',67,-1)]]),  #139
    ('_struct',[[('m_reason',95,-1)]]),  #140
    ('_struct',[[('m_purchaseCategoryId',67,-1)]]),  #141
    ('_struct',[[('m_button',72,-1)]]),  #142
    ('_struct',[[('m_recipient',19,-2),('m_string',24,-1)]]),  #143
    ('_struct',[[('m_recipient',19,-2),('m_point',68,-1)]]),  #144
    ('_struct',[[('m_progress',67,-1)]]),  #145
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (65, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (57, 'NNet.Game.SBankFileEvent'),
    8: (59, 'NNet.Game.SBankSectionEvent'),
    9: (60, 'NNet.Game.SBankKeyEvent'),
    10: (61, 'NNet.Game.SBankValueEvent'),
    11: (63, 'NNet.Game.SBankSignatureEvent'),
    12: (64, 'NNet.Game.SUserOptionsEvent'),
    22: (66, 'NNet.Game.SSaveGameEvent'),
    23: (65, 'NNet.Game.SSaveGameDoneEvent'),
    25: (65, 'NNet.Game.SPlayerLeaveEvent'),
    26: (70, 'NNet.Game.SGameCheatEvent'),
    27: (81, 'NNet.Game.SCmdEvent'),
    28: (88, 'NNet.Game.SSelectionDeltaEvent'),
    29: (89, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (91, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (93, 'NNet.Game.SResourceTradeEvent'),
    32: (94, 'NNet.Game.STriggerChatMessageEvent'),
    33: (97, 'NNet.Game.SAICommunicateEvent'),
    34: (98, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (99, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    37: (100, 'NNet.Game.SBroadcastCheatEvent'),
    38: (101, 'NNet.Game.SAllianceEvent'),
    39: (102, 'NNet.Game.SUnitClickEvent'),
    40: (103, 'NNet.Game.SUnitHighlightEvent'),
    41: (104, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (65, 'NNet.Game.STriggerSkippedEvent'),
    45: (109, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (112, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (113, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (113, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (116, 'NNet.Game.SCameraUpdateEvent'),
    50: (65, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (105, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (65, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (106, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (65, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (108, 'NNet.Game.STriggerDialogControlEvent'),
    56: (111, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (118, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (121, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (122, 'NNet.Game.STriggerMouseMovedEvent'),
    63: (65, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (123, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (124, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (125, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (137, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (65, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (65, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (126, 'NNet.Game.SResourceRequestEvent'),
    71: (127, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (128, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (65, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (65, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (129, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (130, 'NNet.Game.SLagMessageEvent'),
    77: (65, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (65, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (131, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (65, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (65, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (132, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (133, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (133, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (106, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (65, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (65, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (135, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (136, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (138, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (139, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (140, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (105, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (141, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (142, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (65, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (143, 'NNet.Game.SChatMessage'),
    1: (144, 'NNet.Game.SPingMessage'),
    2: (145, 'NNet.Game.SLoadingProgressMessage'),
    3: (65, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 32

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 56


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol21995
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,6),29]),  #30
    ('_optional',[30]),  #31
    ('_array',[(0,6),24]),  #32
    ('_optional',[32]),  #33
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13),('m_modPaths',33,14)]]),  #34
    ('_optional',[10]),  #35
    ('_struct',[[('m_race',35,-1)]]),  #36
    ('_struct',[[('m_team',35,-1)]]),  #37
    ('_struct',[[('m_name',9,-8),('m_randomSeed',5,-7),('m_racePreference',36,-6),('m_teamPreference',37,-5),('m_testMap',26,-4),('m_testAuto',26,-3),('m_examine',26,-2),('m_observe',19,-1)]]),  #38
    ('_array',[(0,5),38]),  #39
    ('_struct',[[('m_lockTeams',26,-11),('m_teamsTogether',26,-10),('m_advancedSharedControl',26,-9),('m_randomRaces',26,-8),('m_battleNet',26,-7),('m_amm',26,-6),('m_ranked',26,-5),('m_noVictoryOrDefeat',26,-4),('m_fog',19,-3),('m_observers',19,-2),('m_userDifficulty',19,-1)]]),  #40
    ('_int',[(1,4)]),  #41
    ('_int',[(1,8)]),  #42
    ('_bitarray',[(0,6)]),  #43
    ('_bitarray',[(0,8)]),  #44
    ('_bitarray',[(0,2)]),  #45
    ('_struct',[[('m_allowedColors',43,-5),('m_allowedRaces',44,-4),('m_allowedDifficulty',43,-3),('m_allowedControls',44,-2),('m_allowedObserveTypes',45,-1)]]),  #46
    ('_array',[(0,5),46]),  #47
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',40,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',41,-15),('m_maxColors',2,-14),('m_maxRaces',42,-13),('m_maxControls',42,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',47,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #48
    ('_optional',[1]),  #49
    ('_optional',[7]),  #50
    ('_struct',[[('m_color',50,-1)]]),  #51
    ('_array',[(0,5),5]),  #52
    ('_array',[(0,9),5]),  #53
    ('_struct',[[('m_control',10,-11),('m_userId',49,-10),('m_teamId',1,-9),('m_colorPref',51,-8),('m_racePref',36,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',52,-3),('m_toonHandle',15,-2),('m_licenses',53,-1)]]),  #54
    ('_array',[(0,5),54]),  #55
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',55,-6),('m_randomSeed',5,-5),('m_hostUserId',49,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #56
    ('_struct',[[('m_userInitialData',39,-3),('m_gameDescription',48,-2),('m_lobbyState',56,-1)]]),  #57
    ('_struct',[[('m_syncLobbyState',57,-1)]]),  #58
    ('_struct',[[('m_name',15,-1)]]),  #59
    ('_blob',[(0,6)]),  #60
    ('_struct',[[('m_name',60,-1)]]),  #61
    ('_struct',[[('m_name',60,-3),('m_type',5,-2),('m_data',15,-1)]]),  #62
    ('_struct',[[('m_type',5,-3),('m_name',60,-2),('m_data',28,-1)]]),  #63
    ('_array',[(0,5),10]),  #64
    ('_struct',[[('m_signature',64,-1)]]),  #65
    ('_struct',[[('m_gameFullyDownloaded',26,-6),('m_developmentCheatsEnabled',26,-5),('m_multiplayerCheatsEnabled',26,-4),('m_syncChecksummingEnabled',26,-3),('m_isMapToMapTransition',26,-2),('m_useAIBeacons',26,-1)]]),  #66
    ('_struct',[[]]),  #67
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #68
    ('_int',[(-2147483648,32)]),  #69
    ('_struct',[[('x',69,-2),('y',69,-1)]]),  #70
    ('_struct',[[('m_point',70,-4),('m_time',69,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #71
    ('_struct',[[('m_data',71,-1)]]),  #72
    ('_int',[(0,20)]),  #73
    ('_int',[(0,16)]),  #74
    ('_struct',[[('m_abilLink',74,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',35,-1)]]),  #75
    ('_optional',[75]),  #76
    ('_null',[]),  #77
    ('_struct',[[('x',73,-3),('y',73,-2),('z',69,-1)]]),  #78
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',74,-4),('m_snapshotControlPlayerId',49,-3),('m_snapshotUpkeepPlayerId',49,-2),('m_snapshotPoint',78,-1)]]),  #79
    ('_choice',[(0,2),{0:('None',77),1:('TargetPoint',78),2:('TargetUnit',79),3:('Data',5)}]),  #80
    ('_optional',[5]),  #81
    ('_struct',[[('m_cmdFlags',73,-4),('m_abil',76,-3),('m_data',80,-2),('m_otherUnit',81,-1)]]),  #82
    ('_int',[(0,9)]),  #83
    ('_bitarray',[(0,9)]),  #84
    ('_array',[(0,9),83]),  #85
    ('_choice',[(0,2),{0:('None',77),1:('Mask',84),2:('OneIndices',85),3:('ZeroIndices',85)}]),  #86
    ('_struct',[[('m_unitLink',74,-3),('m_intraSubgroupPriority',10,-2),('m_count',83,-1)]]),  #87
    ('_array',[(0,9),87]),  #88
    ('_struct',[[('m_subgroupIndex',83,-4),('m_removeMask',86,-3),('m_addSubgroups',88,-2),('m_addUnitTags',53,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',89,-1)]]),  #90
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',86,-1)]]),  #91
    ('_struct',[[('m_count',83,-6),('m_subgroupCount',83,-5),('m_activeSubgroupIndex',83,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #92
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',92,-1)]]),  #93
    ('_array',[(0,3),69]),  #94
    ('_struct',[[('m_recipientId',1,-2),('m_resources',94,-1)]]),  #95
    ('_struct',[[('m_chatMessage',23,-1)]]),  #96
    ('_int',[(-128,8)]),  #97
    ('_struct',[[('x',69,-3),('y',69,-2),('z',69,-1)]]),  #98
    ('_struct',[[('m_beacon',97,-9),('m_ally',97,-8),('m_flags',97,-7),('m_build',97,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',74,-4),('m_targetUnitSnapshotUpkeepPlayerId',97,-3),('m_targetUnitSnapshotControlPlayerId',97,-2),('m_targetPoint',98,-1)]]),  #99
    ('_struct',[[('m_speed',12,-1)]]),  #100
    ('_struct',[[('m_delta',97,-1)]]),  #101
    ('_struct',[[('m_point',70,-3),('m_unit',5,-2),('m_pingedMinimap',26,-1)]]),  #102
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #103
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #104
    ('_struct',[[('m_unitTag',5,-1)]]),  #105
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #106
    ('_struct',[[('m_conversationId',69,-2),('m_replyId',69,-1)]]),  #107
    ('_struct',[[('m_purchaseItemId',69,-1)]]),  #108
    ('_struct',[[('m_difficultyLevel',69,-1)]]),  #109
    ('_choice',[(0,3),{0:('None',77),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',69),4:('TextChanged',24)}]),  #110
    ('_struct',[[('m_controlId',69,-3),('m_eventType',69,-2),('m_eventData',110,-1)]]),  #111
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #112
    ('_array',[(0,8),5]),  #113
    ('_struct',[[('m_soundHash',113,-2),('m_length',113,-1)]]),  #114
    ('_struct',[[('m_syncInfo',114,-1)]]),  #115
    ('_struct',[[('m_sound',5,-1)]]),  #116
    ('_struct',[[('m_transmissionId',69,-2),('m_thread',5,-1)]]),  #117
    ('_struct',[[('m_transmissionId',69,-1)]]),  #118
    ('_struct',[[('x',74,-2),('y',74,-1)]]),  #119
    ('_optional',[74]),  #120
    ('_struct',[[('m_target',119,-4),('m_distance',120,-3),('m_pitch',120,-2),('m_yaw',120,-1)]]),  #121
    ('_int',[(0,1)]),  #122
    ('_struct',[[('m_skipType',122,-1)]]),  #123
    ('_int',[(0,11)]),  #124
    ('_struct',[[('x',124,-2),('y',124,-1)]]),  #125
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #126
    ('_struct',[[('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #127
    ('_struct',[[('m_achievementLink',74,-1)]]),  #128
    ('_struct',[[('m_soundtrack',5,-1)]]),  #129
    ('_struct',[[('m_planetId',69,-1)]]),  #130
    ('_struct',[[('m_key',97,-2),('m_flags',97,-1)]]),  #131
    ('_struct',[[('m_resources',94,-1)]]),  #132
    ('_struct',[[('m_fulfillRequestId',69,-1)]]),  #133
    ('_struct',[[('m_cancelRequestId',69,-1)]]),  #134
    ('_struct',[[('m_researchItemId',69,-1)]]),  #135
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #136
    ('_struct',[[('m_mercenaryId',69,-1)]]),  #137
    ('_struct',[[('m_battleReportId',69,-2),('m_difficultyLevel',69,-1)]]),  #138
    ('_struct',[[('m_battleReportId',69,-1)]]),  #139
    ('_int',[(0,19)]),  #140
    ('_struct',[[('m_decrementMs',140,-1)]]),  #141
    ('_struct',[[('m_portraitId',69,-1)]]),  #142
    ('_struct',[[('m_functionName',15,-1)]]),  #143
    ('_struct',[[('m_result',69,-1)]]),  #144
    ('_struct',[[('m_gameMenuItemIndex',69,-1)]]),  #145
    ('_struct',[[('m_reason',97,-1)]]),  #146
    ('_struct',[[('m_purchaseCategoryId',69,-1)]]),  #147
    ('_struct',[[('m_button',74,-1)]]),  #148
    ('_struct',[[('m_cutsceneId',69,-2),('m_bookmarkName',15,-1)]]),  #149
    ('_struct',[[('m_cutsceneId',69,-1)]]),  #150
    ('_struct',[[('m_cutsceneId',69,-3),('m_conversationLine',15,-2),('m_altConversationLine',15,-1)]]),  #151
    ('_struct',[[('m_cutsceneId',69,-2),('m_conversationLine',15,-1)]]),  #152
    ('_struct',[[('m_recipient',12,-2),('m_string',24,-1)]]),  #153
    ('_struct',[[('m_recipient',12,-2),('m_point',70,-1)]]),  #154
    ('_struct',[[('m_progress',69,-1)]]),  #155
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (67, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (59, 'NNet.Game.SBankFileEvent'),
    8: (61, 'NNet.Game.SBankSectionEvent'),
    9: (62, 'NNet.Game.SBankKeyEvent'),
    10: (63, 'NNet.Game.SBankValueEvent'),
    11: (65, 'NNet.Game.SBankSignatureEvent'),
    12: (66, 'NNet.Game.SUserOptionsEvent'),
    22: (68, 'NNet.Game.SSaveGameEvent'),
    23: (67, 'NNet.Game.SSaveGameDoneEvent'),
    25: (67, 'NNet.Game.SPlayerLeaveEvent'),
    26: (72, 'NNet.Game.SGameCheatEvent'),
    27: (82, 'NNet.Game.SCmdEvent'),
    28: (90, 'NNet.Game.SSelectionDeltaEvent'),
    29: (91, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (93, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (95, 'NNet.Game.SResourceTradeEvent'),
    32: (96, 'NNet.Game.STriggerChatMessageEvent'),
    33: (99, 'NNet.Game.SAICommunicateEvent'),
    34: (100, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (101, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (102, 'NNet.Game.STriggerPingEvent'),
    37: (103, 'NNet.Game.SBroadcastCheatEvent'),
    38: (104, 'NNet.Game.SAllianceEvent'),
    39: (105, 'NNet.Game.SUnitClickEvent'),
    40: (106, 'NNet.Game.SUnitHighlightEvent'),
    41: (107, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (67, 'NNet.Game.STriggerSkippedEvent'),
    45: (112, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (116, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (117, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (118, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (121, 'NNet.Game.SCameraUpdateEvent'),
    50: (67, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (108, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (67, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (109, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (67, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (111, 'NNet.Game.STriggerDialogControlEvent'),
    56: (115, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (123, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (126, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (127, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (128, 'NNet.Game.SAchievementAwardedEvent'),
    63: (67, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (129, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (130, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (131, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (143, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (67, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (67, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (132, 'NNet.Game.SResourceRequestEvent'),
    71: (133, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (134, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (67, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (67, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (135, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (136, 'NNet.Game.SLagMessageEvent'),
    77: (67, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (67, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (137, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (67, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (67, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (138, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (139, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (139, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (109, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (67, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (67, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (141, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (142, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (144, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (145, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (146, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (108, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (147, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (148, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (67, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (149, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (150, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (151, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (152, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (153, 'NNet.Game.SChatMessage'),
    1: (154, 'NNet.Game.SPingMessage'),
    2: (155, 'NNet.Game.SLoadingProgressMessage'),
    3: (67, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 34

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 58


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol22612
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,6),29]),  #30
    ('_optional',[30]),  #31
    ('_array',[(0,6),24]),  #32
    ('_optional',[32]),  #33
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13),('m_modPaths',33,14)]]),  #34
    ('_optional',[10]),  #35
    ('_struct',[[('m_race',35,-1)]]),  #36
    ('_struct',[[('m_team',35,-1)]]),  #37
    ('_struct',[[('m_name',9,-8),('m_randomSeed',5,-7),('m_racePreference',36,-6),('m_teamPreference',37,-5),('m_testMap',26,-4),('m_testAuto',26,-3),('m_examine',26,-2),('m_observe',19,-1)]]),  #38
    ('_array',[(0,5),38]),  #39
    ('_struct',[[('m_lockTeams',26,-12),('m_teamsTogether',26,-11),('m_advancedSharedControl',26,-10),('m_randomRaces',26,-9),('m_battleNet',26,-8),('m_amm',26,-7),('m_ranked',26,-6),('m_noVictoryOrDefeat',26,-5),('m_fog',19,-4),('m_observers',19,-3),('m_userDifficulty',19,-2),('m_clientDebugFlags',16,-1)]]),  #40
    ('_int',[(1,4)]),  #41
    ('_int',[(1,8)]),  #42
    ('_bitarray',[(0,6)]),  #43
    ('_bitarray',[(0,8)]),  #44
    ('_bitarray',[(0,2)]),  #45
    ('_struct',[[('m_allowedColors',43,-5),('m_allowedRaces',44,-4),('m_allowedDifficulty',43,-3),('m_allowedControls',44,-2),('m_allowedObserveTypes',45,-1)]]),  #46
    ('_array',[(0,5),46]),  #47
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',40,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',41,-15),('m_maxColors',2,-14),('m_maxRaces',42,-13),('m_maxControls',42,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',47,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #48
    ('_optional',[1]),  #49
    ('_optional',[7]),  #50
    ('_struct',[[('m_color',50,-1)]]),  #51
    ('_array',[(0,5),5]),  #52
    ('_array',[(0,9),5]),  #53
    ('_struct',[[('m_control',10,-11),('m_userId',49,-10),('m_teamId',1,-9),('m_colorPref',51,-8),('m_racePref',36,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',52,-3),('m_toonHandle',15,-2),('m_licenses',53,-1)]]),  #54
    ('_array',[(0,5),54]),  #55
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',55,-6),('m_randomSeed',5,-5),('m_hostUserId',49,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #56
    ('_struct',[[('m_userInitialData',39,-3),('m_gameDescription',48,-2),('m_lobbyState',56,-1)]]),  #57
    ('_struct',[[('m_syncLobbyState',57,-1)]]),  #58
    ('_struct',[[('m_name',15,-1)]]),  #59
    ('_blob',[(0,6)]),  #60
    ('_struct',[[('m_name',60,-1)]]),  #61
    ('_struct',[[('m_name',60,-3),('m_type',5,-2),('m_data',15,-1)]]),  #62
    ('_struct',[[('m_type',5,-3),('m_name',60,-2),('m_data',28,-1)]]),  #63
    ('_array',[(0,5),10]),  #64
    ('_struct',[[('m_signature',64,-1)]]),  #65
    ('_struct',[[('m_gameFullyDownloaded',26,-6),('m_developmentCheatsEnabled',26,-5),('m_multiplayerCheatsEnabled',26,-4),('m_syncChecksummingEnabled',26,-3),('m_isMapToMapTransition',26,-2),('m_useAIBeacons',26,-1)]]),  #66
    ('_struct',[[]]),  #67
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #68
    ('_int',[(-2147483648,32)]),  #69
    ('_struct',[[('x',69,-2),('y',69,-1)]]),  #70
    ('_struct',[[('m_point',70,-4),('m_time',69,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #71
    ('_struct',[[('m_data',71,-1)]]),  #72
    ('_int',[(0,20)]),  #73
    ('_int',[(0,16)]),  #74
    ('_struct',[[('m_abilLink',74,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',35,-1)]]),  #75
    ('_optional',[75]),  #76
    ('_null',[]),  #77
    ('_struct',[[('x',73,-3),('y',73,-2),('z',69,-1)]]),  #78
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',74,-4),('m_snapshotControlPlayerId',49,-3),('m_snapshotUpkeepPlayerId',49,-2),('m_snapshotPoint',78,-1)]]),  #79
    ('_choice',[(0,2),{0:('None',77),1:('TargetPoint',78),2:('TargetUnit',79),3:('Data',5)}]),  #80
    ('_optional',[5]),  #81
    ('_struct',[[('m_cmdFlags',73,-4),('m_abil',76,-3),('m_data',80,-2),('m_otherUnit',81,-1)]]),  #82
    ('_int',[(0,9)]),  #83
    ('_bitarray',[(0,9)]),  #84
    ('_array',[(0,9),83]),  #85
    ('_choice',[(0,2),{0:('None',77),1:('Mask',84),2:('OneIndices',85),3:('ZeroIndices',85)}]),  #86
    ('_struct',[[('m_unitLink',74,-3),('m_intraSubgroupPriority',10,-2),('m_count',83,-1)]]),  #87
    ('_array',[(0,9),87]),  #88
    ('_struct',[[('m_subgroupIndex',83,-4),('m_removeMask',86,-3),('m_addSubgroups',88,-2),('m_addUnitTags',53,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',89,-1)]]),  #90
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',86,-1)]]),  #91
    ('_struct',[[('m_count',83,-6),('m_subgroupCount',83,-5),('m_activeSubgroupIndex',83,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #92
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',92,-1)]]),  #93
    ('_array',[(0,3),69]),  #94
    ('_struct',[[('m_recipientId',1,-2),('m_resources',94,-1)]]),  #95
    ('_struct',[[('m_chatMessage',23,-1)]]),  #96
    ('_int',[(-128,8)]),  #97
    ('_struct',[[('x',69,-3),('y',69,-2),('z',69,-1)]]),  #98
    ('_struct',[[('m_beacon',97,-9),('m_ally',97,-8),('m_flags',97,-7),('m_build',97,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',74,-4),('m_targetUnitSnapshotUpkeepPlayerId',97,-3),('m_targetUnitSnapshotControlPlayerId',97,-2),('m_targetPoint',98,-1)]]),  #99
    ('_struct',[[('m_speed',12,-1)]]),  #100
    ('_struct',[[('m_delta',97,-1)]]),  #101
    ('_struct',[[('m_point',70,-3),('m_unit',5,-2),('m_pingedMinimap',26,-1)]]),  #102
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #103
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #104
    ('_struct',[[('m_unitTag',5,-1)]]),  #105
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #106
    ('_struct',[[('m_conversationId',69,-2),('m_replyId',69,-1)]]),  #107
    ('_struct',[[('m_purchaseItemId',69,-1)]]),  #108
    ('_struct',[[('m_difficultyLevel',69,-1)]]),  #109
    ('_choice',[(0,3),{0:('None',77),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',69),4:('TextChanged',24)}]),  #110
    ('_struct',[[('m_controlId',69,-3),('m_eventType',69,-2),('m_eventData',110,-1)]]),  #111
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #112
    ('_array',[(0,8),5]),  #113
    ('_struct',[[('m_soundHash',113,-2),('m_length',113,-1)]]),  #114
    ('_struct',[[('m_syncInfo',114,-1)]]),  #115
    ('_struct',[[('m_sound',5,-1)]]),  #116
    ('_struct',[[('m_transmissionId',69,-2),('m_thread',5,-1)]]),  #117
    ('_struct',[[('m_transmissionId',69,-1)]]),  #118
    ('_struct',[[('x',74,-2),('y',74,-1)]]),  #119
    ('_optional',[74]),  #120
    ('_struct',[[('m_target',119,-4),('m_distance',120,-3),('m_pitch',120,-2),('m_yaw',120,-1)]]),  #121
    ('_int',[(0,1)]),  #122
    ('_struct',[[('m_skipType',122,-1)]]),  #123
    ('_int',[(0,11)]),  #124
    ('_struct',[[('x',124,-2),('y',124,-1)]]),  #125
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #126
    ('_struct',[[('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #127
    ('_struct',[[('m_achievementLink',74,-1)]]),  #128
    ('_struct',[[('m_soundtrack',5,-1)]]),  #129
    ('_struct',[[('m_planetId',69,-1)]]),  #130
    ('_struct',[[('m_key',97,-2),('m_flags',97,-1)]]),  #131
    ('_struct',[[('m_resources',94,-1)]]),  #132
    ('_struct',[[('m_fulfillRequestId',69,-1)]]),  #133
    ('_struct',[[('m_cancelRequestId',69,-1)]]),  #134
    ('_struct',[[('m_researchItemId',69,-1)]]),  #135
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #136
    ('_struct',[[('m_mercenaryId',69,-1)]]),  #137
    ('_struct',[[('m_battleReportId',69,-2),('m_difficultyLevel',69,-1)]]),  #138
    ('_struct',[[('m_battleReportId',69,-1)]]),  #139
    ('_int',[(0,19)]),  #140
    ('_struct',[[('m_decrementMs',140,-1)]]),  #141
    ('_struct',[[('m_portraitId',69,-1)]]),  #142
    ('_struct',[[('m_functionName',15,-1)]]),  #143
    ('_struct',[[('m_result',69,-1)]]),  #144
    ('_struct',[[('m_gameMenuItemIndex',69,-1)]]),  #145
    ('_struct',[[('m_reason',97,-1)]]),  #146
    ('_struct',[[('m_purchaseCategoryId',69,-1)]]),  #147
    ('_struct',[[('m_button',74,-1)]]),  #148
    ('_struct',[[('m_cutsceneId',69,-2),('m_bookmarkName',15,-1)]]),  #149
    ('_struct',[[('m_cutsceneId',69,-1)]]),  #150
    ('_struct',[[('m_cutsceneId',69,-3),('m_conversationLine',15,-2),('m_altConversationLine',15,-1)]]),  #151
    ('_struct',[[('m_cutsceneId',69,-2),('m_conversationLine',15,-1)]]),  #152
    ('_struct',[[('m_recipient',12,-2),('m_string',24,-1)]]),  #153
    ('_struct',[[('m_recipient',12,-2),('m_point',70,-1)]]),  #154
    ('_struct',[[('m_progress',69,-1)]]),  #155
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (67, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (59, 'NNet.Game.SBankFileEvent'),
    8: (61, 'NNet.Game.SBankSectionEvent'),
    9: (62, 'NNet.Game.SBankKeyEvent'),
    10: (63, 'NNet.Game.SBankValueEvent'),
    11: (65, 'NNet.Game.SBankSignatureEvent'),
    12: (66, 'NNet.Game.SUserOptionsEvent'),
    22: (68, 'NNet.Game.SSaveGameEvent'),
    23: (67, 'NNet.Game.SSaveGameDoneEvent'),
    25: (67, 'NNet.Game.SPlayerLeaveEvent'),
    26: (72, 'NNet.Game.SGameCheatEvent'),
    27: (82, 'NNet.Game.SCmdEvent'),
    28: (90, 'NNet.Game.SSelectionDeltaEvent'),
    29: (91, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (93, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (95, 'NNet.Game.SResourceTradeEvent'),
    32: (96, 'NNet.Game.STriggerChatMessageEvent'),
    33: (99, 'NNet.Game.SAICommunicateEvent'),
    34: (100, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (101, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (102, 'NNet.Game.STriggerPingEvent'),
    37: (103, 'NNet.Game.SBroadcastCheatEvent'),
    38: (104, 'NNet.Game.SAllianceEvent'),
    39: (105, 'NNet.Game.SUnitClickEvent'),
    40: (106, 'NNet.Game.SUnitHighlightEvent'),
    41: (107, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (67, 'NNet.Game.STriggerSkippedEvent'),
    45: (112, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (116, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (117, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (118, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (121, 'NNet.Game.SCameraUpdateEvent'),
    50: (67, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (108, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (67, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (109, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (67, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (111, 'NNet.Game.STriggerDialogControlEvent'),
    56: (115, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (123, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (126, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (127, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (128, 'NNet.Game.SAchievementAwardedEvent'),
    63: (67, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (129, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (130, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (131, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (143, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (67, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (67, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (132, 'NNet.Game.SResourceRequestEvent'),
    71: (133, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (134, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (67, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (67, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (135, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (136, 'NNet.Game.SLagMessageEvent'),
    77: (67, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (67, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (137, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (67, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (67, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (138, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (139, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (139, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (109, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (67, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (67, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (141, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (142, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (144, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (145, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (146, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (108, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (147, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (148, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (67, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (149, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (150, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (151, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (152, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (153, 'NNet.Game.SChatMessage'),
    1: (154, 'NNet.Game.SPingMessage'),
    2: (155, 'NNet.Game.SLoadingProgressMessage'),
    3: (67, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 34

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 58


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol23260
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_playerId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8)]]),  #20
    ('_array',[(0,5),20]),  #21
    ('_optional',[21]),  #22
    ('_blob',[(0,10)]),  #23
    ('_blob',[(0,11)]),  #24
    ('_struct',[[('m_file',24,0)]]),  #25
    ('_bool',[]),  #26
    ('_int',[(-9223372036854775808,64)]),  #27
    ('_blob',[(0,12)]),  #28
    ('_blob',[(40,0)]),  #29
    ('_array',[(0,6),29]),  #30
    ('_optional',[30]),  #31
    ('_array',[(0,6),24]),  #32
    ('_optional',[32]),  #33
    ('_struct',[[('m_playerList',22,0),('m_title',23,1),('m_difficulty',9,2),('m_thumbnail',25,3),('m_isBlizzardMap',26,4),('m_timeUTC',27,5),('m_timeLocalOffset',27,6),('m_description',28,7),('m_imageFilePath',24,8),('m_mapFileName',24,9),('m_cacheHandles',31,10),('m_miniSave',26,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13),('m_modPaths',33,14)]]),  #34
    ('_optional',[10]),  #35
    ('_struct',[[('m_race',35,-1)]]),  #36
    ('_struct',[[('m_team',35,-1)]]),  #37
    ('_struct',[[('m_name',9,-8),('m_randomSeed',5,-7),('m_racePreference',36,-6),('m_teamPreference',37,-5),('m_testMap',26,-4),('m_testAuto',26,-3),('m_examine',26,-2),('m_observe',19,-1)]]),  #38
    ('_array',[(0,5),38]),  #39
    ('_struct',[[('m_lockTeams',26,-12),('m_teamsTogether',26,-11),('m_advancedSharedControl',26,-10),('m_randomRaces',26,-9),('m_battleNet',26,-8),('m_amm',26,-7),('m_ranked',26,-6),('m_noVictoryOrDefeat',26,-5),('m_fog',19,-4),('m_observers',19,-3),('m_userDifficulty',19,-2),('m_clientDebugFlags',16,-1)]]),  #40
    ('_int',[(1,4)]),  #41
    ('_int',[(1,8)]),  #42
    ('_bitarray',[(0,6)]),  #43
    ('_bitarray',[(0,8)]),  #44
    ('_bitarray',[(0,2)]),  #45
    ('_struct',[[('m_allowedColors',43,-5),('m_allowedRaces',44,-4),('m_allowedDifficulty',43,-3),('m_allowedControls',44,-2),('m_allowedObserveTypes',45,-1)]]),  #46
    ('_array',[(0,5),46]),  #47
    ('_struct',[[('m_randomValue',5,-23),('m_gameCacheName',23,-22),('m_gameOptions',40,-21),('m_gameSpeed',12,-20),('m_gameType',12,-19),('m_maxUsers',7,-18),('m_maxObservers',7,-17),('m_maxPlayers',7,-16),('m_maxTeams',41,-15),('m_maxColors',2,-14),('m_maxRaces',42,-13),('m_maxControls',42,-12),('m_mapSizeX',10,-11),('m_mapSizeY',10,-10),('m_mapFileSyncChecksum',5,-9),('m_mapFileName',24,-8),('m_mapAuthorName',9,-7),('m_modFileSyncChecksum',5,-6),('m_slotDescriptions',47,-5),('m_defaultDifficulty',2,-4),('m_cacheHandles',30,-3),('m_isBlizzardMap',26,-2),('m_isPremadeFFA',26,-1)]]),  #48
    ('_optional',[1]),  #49
    ('_optional',[7]),  #50
    ('_struct',[[('m_color',50,-1)]]),  #51
    ('_array',[(0,5),5]),  #52
    ('_array',[(0,9),5]),  #53
    ('_struct',[[('m_control',10,-11),('m_userId',49,-10),('m_teamId',1,-9),('m_colorPref',51,-8),('m_racePref',36,-7),('m_difficulty',2,-6),('m_handicap',0,-5),('m_observe',19,-4),('m_rewards',52,-3),('m_toonHandle',15,-2),('m_licenses',53,-1)]]),  #54
    ('_array',[(0,5),54]),  #55
    ('_struct',[[('m_phase',12,-9),('m_maxUsers',7,-8),('m_maxObservers',7,-7),('m_slots',55,-6),('m_randomSeed',5,-5),('m_hostUserId',49,-4),('m_isSinglePlayer',26,-3),('m_gameDuration',5,-2),('m_defaultDifficulty',2,-1)]]),  #56
    ('_struct',[[('m_userInitialData',39,-3),('m_gameDescription',48,-2),('m_lobbyState',56,-1)]]),  #57
    ('_struct',[[('m_syncLobbyState',57,-1)]]),  #58
    ('_struct',[[('m_name',15,-1)]]),  #59
    ('_blob',[(0,6)]),  #60
    ('_struct',[[('m_name',60,-1)]]),  #61
    ('_struct',[[('m_name',60,-3),('m_type',5,-2),('m_data',15,-1)]]),  #62
    ('_struct',[[('m_type',5,-3),('m_name',60,-2),('m_data',28,-1)]]),  #63
    ('_array',[(0,5),10]),  #64
    ('_struct',[[('m_signature',64,-1)]]),  #65
    ('_struct',[[('m_gameFullyDownloaded',26,-6),('m_developmentCheatsEnabled',26,-5),('m_multiplayerCheatsEnabled',26,-4),('m_syncChecksummingEnabled',26,-3),('m_isMapToMapTransition',26,-2),('m_useAIBeacons',26,-1)]]),  #66
    ('_struct',[[]]),  #67
    ('_struct',[[('m_fileName',24,-5),('m_automatic',26,-4),('m_overwrite',26,-3),('m_name',9,-2),('m_description',23,-1)]]),  #68
    ('_int',[(-2147483648,32)]),  #69
    ('_struct',[[('x',69,-2),('y',69,-1)]]),  #70
    ('_struct',[[('m_point',70,-4),('m_time',69,-3),('m_verb',23,-2),('m_arguments',23,-1)]]),  #71
    ('_struct',[[('m_data',71,-1)]]),  #72
    ('_int',[(0,20)]),  #73
    ('_int',[(0,16)]),  #74
    ('_struct',[[('m_abilLink',74,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',35,-1)]]),  #75
    ('_optional',[75]),  #76
    ('_null',[]),  #77
    ('_struct',[[('x',73,-3),('y',73,-2),('z',69,-1)]]),  #78
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',74,-4),('m_snapshotControlPlayerId',49,-3),('m_snapshotUpkeepPlayerId',49,-2),('m_snapshotPoint',78,-1)]]),  #79
    ('_choice',[(0,2),{0:('None',77),1:('TargetPoint',78),2:('TargetUnit',79),3:('Data',5)}]),  #80
    ('_optional',[5]),  #81
    ('_struct',[[('m_cmdFlags',73,-4),('m_abil',76,-3),('m_data',80,-2),('m_otherUnit',81,-1)]]),  #82
    ('_int',[(0,9)]),  #83
    ('_bitarray',[(0,9)]),  #84
    ('_array',[(0,9),83]),  #85
    ('_choice',[(0,2),{0:('None',77),1:('Mask',84),2:('OneIndices',85),3:('ZeroIndices',85)}]),  #86
    ('_struct',[[('m_unitLink',74,-3),('m_intraSubgroupPriority',10,-2),('m_count',83,-1)]]),  #87
    ('_array',[(0,9),87]),  #88
    ('_struct',[[('m_subgroupIndex',83,-4),('m_removeMask',86,-3),('m_addSubgroups',88,-2),('m_addUnitTags',53,-1)]]),  #89
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',89,-1)]]),  #90
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',86,-1)]]),  #91
    ('_struct',[[('m_count',83,-6),('m_subgroupCount',83,-5),('m_activeSubgroupIndex',83,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #92
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',92,-1)]]),  #93
    ('_array',[(0,3),69]),  #94
    ('_struct',[[('m_recipientId',1,-2),('m_resources',94,-1)]]),  #95
    ('_struct',[[('m_chatMessage',23,-1)]]),  #96
    ('_int',[(-128,8)]),  #97
    ('_struct',[[('x',69,-3),('y',69,-2),('z',69,-1)]]),  #98
    ('_struct',[[('m_beacon',97,-9),('m_ally',97,-8),('m_flags',97,-7),('m_build',97,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',74,-4),('m_targetUnitSnapshotUpkeepPlayerId',97,-3),('m_targetUnitSnapshotControlPlayerId',97,-2),('m_targetPoint',98,-1)]]),  #99
    ('_struct',[[('m_speed',12,-1)]]),  #100
    ('_struct',[[('m_delta',97,-1)]]),  #101
    ('_struct',[[('m_point',70,-3),('m_unit',5,-2),('m_pingedMinimap',26,-1)]]),  #102
    ('_struct',[[('m_verb',23,-2),('m_arguments',23,-1)]]),  #103
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #104
    ('_struct',[[('m_unitTag',5,-1)]]),  #105
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #106
    ('_struct',[[('m_conversationId',69,-2),('m_replyId',69,-1)]]),  #107
    ('_struct',[[('m_purchaseItemId',69,-1)]]),  #108
    ('_struct',[[('m_difficultyLevel',69,-1)]]),  #109
    ('_choice',[(0,3),{0:('None',77),1:('Checked',26),2:('ValueChanged',5),3:('SelectionChanged',69),4:('TextChanged',24)}]),  #110
    ('_struct',[[('m_controlId',69,-3),('m_eventType',69,-2),('m_eventData',110,-1)]]),  #111
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #112
    ('_array',[(0,7),5]),  #113
    ('_struct',[[('m_soundHash',113,-2),('m_length',113,-1)]]),  #114
    ('_struct',[[('m_syncInfo',114,-1)]]),  #115
    ('_struct',[[('m_sound',5,-1)]]),  #116
    ('_struct',[[('m_transmissionId',69,-2),('m_thread',5,-1)]]),  #117
    ('_struct',[[('m_transmissionId',69,-1)]]),  #118
    ('_struct',[[('x',74,-2),('y',74,-1)]]),  #119
    ('_optional',[74]),  #120
    ('_struct',[[('m_target',119,-4),('m_distance',120,-3),('m_pitch',120,-2),('m_yaw',120,-1)]]),  #121
    ('_int',[(0,1)]),  #122
    ('_struct',[[('m_skipType',122,-1)]]),  #123
    ('_int',[(0,11)]),  #124
    ('_struct',[[('x',124,-2),('y',124,-1)]]),  #125
    ('_struct',[[('m_button',5,-4),('m_down',26,-3),('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #126
    ('_struct',[[('m_posUI',125,-2),('m_posWorld',78,-1)]]),  #127
    ('_struct',[[('m_achievementLink',74,-1)]]),  #128
    ('_struct',[[('m_soundtrack',5,-1)]]),  #129
    ('_struct',[[('m_planetId',69,-1)]]),  #130
    ('_struct',[[('m_key',97,-2),('m_flags',97,-1)]]),  #131
    ('_struct',[[('m_resources',94,-1)]]),  #132
    ('_struct',[[('m_fulfillRequestId',69,-1)]]),  #133
    ('_struct',[[('m_cancelRequestId',69,-1)]]),  #134
    ('_struct',[[('m_researchItemId',69,-1)]]),  #135
    ('_struct',[[('m_laggingPlayerId',1,-1)]]),  #136
    ('_struct',[[('m_mercenaryId',69,-1)]]),  #137
    ('_struct',[[('m_battleReportId',69,-2),('m_difficultyLevel',69,-1)]]),  #138
    ('_struct',[[('m_battleReportId',69,-1)]]),  #139
    ('_int',[(0,19)]),  #140
    ('_struct',[[('m_decrementMs',140,-1)]]),  #141
    ('_struct',[[('m_portraitId',69,-1)]]),  #142
    ('_struct',[[('m_functionName',15,-1)]]),  #143
    ('_struct',[[('m_result',69,-1)]]),  #144
    ('_struct',[[('m_gameMenuItemIndex',69,-1)]]),  #145
    ('_struct',[[('m_reason',97,-1)]]),  #146
    ('_struct',[[('m_purchaseCategoryId',69,-1)]]),  #147
    ('_struct',[[('m_button',74,-1)]]),  #148
    ('_struct',[[('m_cutsceneId',69,-2),('m_bookmarkName',15,-1)]]),  #149
    ('_struct',[[('m_cutsceneId',69,-1)]]),  #150
    ('_struct',[[('m_cutsceneId',69,-3),('m_conversationLine',15,-2),('m_altConversationLine',15,-1)]]),  #151
    ('_struct',[[('m_cutsceneId',69,-2),('m_conversationLine',15,-1)]]),  #152
    ('_struct',[[('m_recipient',12,-2),('m_string',24,-1)]]),  #153
    ('_struct',[[('m_recipient',12,-2),('m_point',70,-1)]]),  #154
    ('_struct',[[('m_progress',69,-1)]]),  #155
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (67, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (59, 'NNet.Game.SBankFileEvent'),
    8: (61, 'NNet.Game.SBankSectionEvent'),
    9: (62, 'NNet.Game.SBankKeyEvent'),
    10: (63, 'NNet.Game.SBankValueEvent'),
    11: (65, 'NNet.Game.SBankSignatureEvent'),
    12: (66, 'NNet.Game.SUserOptionsEvent'),
    22: (68, 'NNet.Game.SSaveGameEvent'),
    23: (67, 'NNet.Game.SSaveGameDoneEvent'),
    25: (67, 'NNet.Game.SPlayerLeaveEvent'),
    26: (72, 'NNet.Game.SGameCheatEvent'),
    27: (82, 'NNet.Game.SCmdEvent'),
    28: (90, 'NNet.Game.SSelectionDeltaEvent'),
    29: (91, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (93, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (95, 'NNet.Game.SResourceTradeEvent'),
    32: (96, 'NNet.Game.STriggerChatMessageEvent'),
    33: (99, 'NNet.Game.SAICommunicateEvent'),
    34: (100, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (101, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (102, 'NNet.Game.STriggerPingEvent'),
    37: (103, 'NNet.Game.SBroadcastCheatEvent'),
    38: (104, 'NNet.Game.SAllianceEvent'),
    39: (105, 'NNet.Game.SUnitClickEvent'),
    40: (106, 'NNet.Game.SUnitHighlightEvent'),
    41: (107, 'NNet.Game.STriggerReplySelectedEvent'),
    44: (67, 'NNet.Game.STriggerSkippedEvent'),
    45: (112, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (116, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (117, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (118, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (121, 'NNet.Game.SCameraUpdateEvent'),
    50: (67, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (108, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (67, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (109, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (67, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (111, 'NNet.Game.STriggerDialogControlEvent'),
    56: (115, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (123, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (126, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (127, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (128, 'NNet.Game.SAchievementAwardedEvent'),
    63: (67, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (129, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (130, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (131, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (143, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (67, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (67, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (132, 'NNet.Game.SResourceRequestEvent'),
    71: (133, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (134, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (67, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (67, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (135, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    76: (136, 'NNet.Game.SLagMessageEvent'),
    77: (67, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (67, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (137, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (67, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (67, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (138, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (139, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (139, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (109, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (67, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (67, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (141, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (142, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (144, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (145, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (146, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (108, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (147, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (148, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (67, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (149, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (150, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (151, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (152, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (153, 'NNet.Game.SChatMessage'),
    1: (154, 'NNet.Game.SPingMessage'),
    2: (155, 'NNet.Game.SLoadingProgressMessage'),
    3: (67, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SPlayerId (the type used to encode player ids).
replay_playerid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 34

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 58


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_player_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_player_id:
            playerid = decoder.instance(replay_playerid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_player_id:
            event['_playerid'] = playerid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_player_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol24764
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,6)]),  #2
    ('_int',[(0,14)]),  #3
    ('_int',[(0,22)]),  #4
    ('_int',[(0,32)]),  #5
    ('_choice',[(0,2),{0:('m_uint6',2),1:('m_uint14',3),2:('m_uint22',4),3:('m_uint32',5)}]),  #6
    ('_int',[(0,5)]),  #7
    ('_struct',[[('m_userId',7,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',5,4),('m_baseBuild',5,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',5,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',5,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_optional',[10]),  #20
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8),('m_workingSetSlotId',20,9)]]),  #21
    ('_array',[(0,5),21]),  #22
    ('_optional',[22]),  #23
    ('_blob',[(0,10)]),  #24
    ('_blob',[(0,11)]),  #25
    ('_struct',[[('m_file',25,0)]]),  #26
    ('_bool',[]),  #27
    ('_int',[(-9223372036854775808,64)]),  #28
    ('_blob',[(0,12)]),  #29
    ('_blob',[(40,0)]),  #30
    ('_array',[(0,6),30]),  #31
    ('_optional',[31]),  #32
    ('_array',[(0,6),25]),  #33
    ('_optional',[33]),  #34
    ('_struct',[[('m_playerList',23,0),('m_title',24,1),('m_difficulty',9,2),('m_thumbnail',26,3),('m_isBlizzardMap',27,4),('m_timeUTC',28,5),('m_timeLocalOffset',28,6),('m_description',29,7),('m_imageFilePath',25,8),('m_campaignIndex',10,15),('m_mapFileName',25,9),('m_cacheHandles',32,10),('m_miniSave',27,11),('m_gameSpeed',12,12),('m_defaultDifficulty',2,13),('m_modPaths',34,14)]]),  #35
    ('_optional',[9]),  #36
    ('_optional',[5]),  #37
    ('_struct',[[('m_race',20,-1)]]),  #38
    ('_struct',[[('m_team',20,-1)]]),  #39
    ('_struct',[[('m_name',9,-12),('m_clanTag',36,-11),('m_highestLeague',20,-10),('m_combinedRaceLevels',37,-9),('m_randomSeed',5,-8),('m_racePreference',38,-7),('m_teamPreference',39,-6),('m_testMap',27,-5),('m_testAuto',27,-4),('m_examine',27,-3),('m_customInterface',27,-2),('m_observe',19,-1)]]),  #40
    ('_array',[(0,5),40]),  #41
    ('_struct',[[('m_lockTeams',27,-12),('m_teamsTogether',27,-11),('m_advancedSharedControl',27,-10),('m_randomRaces',27,-9),('m_battleNet',27,-8),('m_amm',27,-7),('m_competitive',27,-6),('m_noVictoryOrDefeat',27,-5),('m_fog',19,-4),('m_observers',19,-3),('m_userDifficulty',19,-2),('m_clientDebugFlags',16,-1)]]),  #42
    ('_int',[(1,4)]),  #43
    ('_int',[(1,8)]),  #44
    ('_bitarray',[(0,6)]),  #45
    ('_bitarray',[(0,8)]),  #46
    ('_bitarray',[(0,2)]),  #47
    ('_bitarray',[(0,7)]),  #48
    ('_struct',[[('m_allowedColors',45,-6),('m_allowedRaces',46,-5),('m_allowedDifficulty',45,-4),('m_allowedControls',46,-3),('m_allowedObserveTypes',47,-2),('m_allowedAIBuilds',48,-1)]]),  #49
    ('_array',[(0,5),49]),  #50
    ('_struct',[[('m_randomValue',5,-25),('m_gameCacheName',24,-24),('m_gameOptions',42,-23),('m_gameSpeed',12,-22),('m_gameType',12,-21),('m_maxUsers',7,-20),('m_maxObservers',7,-19),('m_maxPlayers',7,-18),('m_maxTeams',43,-17),('m_maxColors',2,-16),('m_maxRaces',44,-15),('m_maxControls',44,-14),('m_mapSizeX',10,-13),('m_mapSizeY',10,-12),('m_mapFileSyncChecksum',5,-11),('m_mapFileName',25,-10),('m_mapAuthorName',9,-9),('m_modFileSyncChecksum',5,-8),('m_slotDescriptions',50,-7),('m_defaultDifficulty',2,-6),('m_defaultAIBuild',0,-5),('m_cacheHandles',31,-4),('m_isBlizzardMap',27,-3),('m_isPremadeFFA',27,-2),('m_isCoopMode',27,-1)]]),  #51
    ('_optional',[1]),  #52
    ('_optional',[7]),  #53
    ('_struct',[[('m_color',53,-1)]]),  #54
    ('_array',[(0,6),5]),  #55
    ('_array',[(0,9),5]),  #56
    ('_struct',[[('m_control',10,-13),('m_userId',52,-12),('m_teamId',1,-11),('m_colorPref',54,-10),('m_racePref',38,-9),('m_difficulty',2,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',19,-5),('m_workingSetSlotId',20,-4),('m_rewards',55,-3),('m_toonHandle',15,-2),('m_licenses',56,-1)]]),  #57
    ('_array',[(0,5),57]),  #58
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',7,-9),('m_maxObservers',7,-8),('m_slots',58,-7),('m_randomSeed',5,-6),('m_hostUserId',52,-5),('m_isSinglePlayer',27,-4),('m_gameDuration',5,-3),('m_defaultDifficulty',2,-2),('m_defaultAIBuild',0,-1)]]),  #59
    ('_struct',[[('m_userInitialData',41,-3),('m_gameDescription',51,-2),('m_lobbyState',59,-1)]]),  #60
    ('_struct',[[('m_syncLobbyState',60,-1)]]),  #61
    ('_struct',[[('m_name',15,-1)]]),  #62
    ('_blob',[(0,6)]),  #63
    ('_struct',[[('m_name',63,-1)]]),  #64
    ('_struct',[[('m_name',63,-3),('m_type',5,-2),('m_data',15,-1)]]),  #65
    ('_struct',[[('m_type',5,-3),('m_name',63,-2),('m_data',29,-1)]]),  #66
    ('_array',[(0,5),10]),  #67
    ('_struct',[[('m_signature',67,-2),('m_toonHandle',15,-1)]]),  #68
    ('_struct',[[('m_gameFullyDownloaded',27,-7),('m_developmentCheatsEnabled',27,-6),('m_multiplayerCheatsEnabled',27,-5),('m_syncChecksummingEnabled',27,-4),('m_isMapToMapTransition',27,-3),('m_startingRally',27,-2),('m_baseBuildNum',5,-1)]]),  #69
    ('_struct',[[]]),  #70
    ('_struct',[[('m_fileName',25,-5),('m_automatic',27,-4),('m_overwrite',27,-3),('m_name',9,-2),('m_description',24,-1)]]),  #71
    ('_int',[(-2147483648,32)]),  #72
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #73
    ('_struct',[[('m_point',73,-4),('m_time',72,-3),('m_verb',24,-2),('m_arguments',24,-1)]]),  #74
    ('_struct',[[('m_data',74,-1)]]),  #75
    ('_int',[(0,20)]),  #76
    ('_int',[(0,16)]),  #77
    ('_struct',[[('m_abilLink',77,-3),('m_abilCmdIndex',7,-2),('m_abilCmdData',20,-1)]]),  #78
    ('_optional',[78]),  #79
    ('_null',[]),  #80
    ('_struct',[[('x',76,-3),('y',76,-2),('z',72,-1)]]),  #81
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',5,-5),('m_snapshotUnitLink',77,-4),('m_snapshotControlPlayerId',52,-3),('m_snapshotUpkeepPlayerId',52,-2),('m_snapshotPoint',81,-1)]]),  #82
    ('_choice',[(0,2),{0:('None',80),1:('TargetPoint',81),2:('TargetUnit',82),3:('Data',5)}]),  #83
    ('_struct',[[('m_cmdFlags',76,-4),('m_abil',79,-3),('m_data',83,-2),('m_otherUnit',37,-1)]]),  #84
    ('_int',[(0,9)]),  #85
    ('_bitarray',[(0,9)]),  #86
    ('_array',[(0,9),85]),  #87
    ('_choice',[(0,2),{0:('None',80),1:('Mask',86),2:('OneIndices',87),3:('ZeroIndices',87)}]),  #88
    ('_struct',[[('m_unitLink',77,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',85,-1)]]),  #89
    ('_array',[(0,9),89]),  #90
    ('_struct',[[('m_subgroupIndex',85,-4),('m_removeMask',88,-3),('m_addSubgroups',90,-2),('m_addUnitTags',56,-1)]]),  #91
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',91,-1)]]),  #92
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',88,-1)]]),  #93
    ('_struct',[[('m_count',85,-6),('m_subgroupCount',85,-5),('m_activeSubgroupIndex',85,-4),('m_unitTagsChecksum',5,-3),('m_subgroupIndicesChecksum',5,-2),('m_subgroupsChecksum',5,-1)]]),  #94
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',94,-1)]]),  #95
    ('_array',[(0,3),72]),  #96
    ('_struct',[[('m_recipientId',1,-2),('m_resources',96,-1)]]),  #97
    ('_struct',[[('m_chatMessage',24,-1)]]),  #98
    ('_int',[(-128,8)]),  #99
    ('_struct',[[('x',72,-3),('y',72,-2),('z',72,-1)]]),  #100
    ('_struct',[[('m_beacon',99,-9),('m_ally',99,-8),('m_flags',99,-7),('m_build',99,-6),('m_targetUnitTag',5,-5),('m_targetUnitSnapshotUnitLink',77,-4),('m_targetUnitSnapshotUpkeepPlayerId',99,-3),('m_targetUnitSnapshotControlPlayerId',99,-2),('m_targetPoint',100,-1)]]),  #101
    ('_struct',[[('m_speed',12,-1)]]),  #102
    ('_struct',[[('m_delta',99,-1)]]),  #103
    ('_struct',[[('m_point',73,-3),('m_unit',5,-2),('m_pingedMinimap',27,-1)]]),  #104
    ('_struct',[[('m_verb',24,-2),('m_arguments',24,-1)]]),  #105
    ('_struct',[[('m_alliance',5,-2),('m_control',5,-1)]]),  #106
    ('_struct',[[('m_unitTag',5,-1)]]),  #107
    ('_struct',[[('m_unitTag',5,-2),('m_flags',10,-1)]]),  #108
    ('_struct',[[('m_conversationId',72,-2),('m_replyId',72,-1)]]),  #109
    ('_optional',[15]),  #110
    ('_struct',[[('m_gameUserId',1,-4),('m_name',9,-3),('m_toonHandle',110,-2),('m_clanTag',36,-1)]]),  #111
    ('_array',[(0,5),111]),  #112
    ('_struct',[[('m_userInfos',112,-1)]]),  #113
    ('_struct',[[('m_purchaseItemId',72,-1)]]),  #114
    ('_struct',[[('m_difficultyLevel',72,-1)]]),  #115
    ('_choice',[(0,3),{0:('None',80),1:('Checked',27),2:('ValueChanged',5),3:('SelectionChanged',72),4:('TextChanged',25),5:('MouseButton',5)}]),  #116
    ('_struct',[[('m_controlId',72,-3),('m_eventType',72,-2),('m_eventData',116,-1)]]),  #117
    ('_struct',[[('m_soundHash',5,-2),('m_length',5,-1)]]),  #118
    ('_array',[(0,7),5]),  #119
    ('_struct',[[('m_soundHash',119,-2),('m_length',119,-1)]]),  #120
    ('_struct',[[('m_syncInfo',120,-1)]]),  #121
    ('_struct',[[('m_sound',5,-1)]]),  #122
    ('_struct',[[('m_transmissionId',72,-2),('m_thread',5,-1)]]),  #123
    ('_struct',[[('m_transmissionId',72,-1)]]),  #124
    ('_struct',[[('x',77,-2),('y',77,-1)]]),  #125
    ('_optional',[125]),  #126
    ('_optional',[77]),  #127
    ('_struct',[[('m_target',126,-4),('m_distance',127,-3),('m_pitch',127,-2),('m_yaw',127,-1)]]),  #128
    ('_int',[(0,1)]),  #129
    ('_struct',[[('m_skipType',129,-1)]]),  #130
    ('_int',[(0,11)]),  #131
    ('_struct',[[('x',131,-2),('y',131,-1)]]),  #132
    ('_struct',[[('m_button',5,-4),('m_down',27,-3),('m_posUI',132,-2),('m_posWorld',81,-1)]]),  #133
    ('_struct',[[('m_posUI',132,-2),('m_posWorld',81,-1)]]),  #134
    ('_struct',[[('m_achievementLink',77,-1)]]),  #135
    ('_struct',[[('m_abilLink',77,-3),('m_abilCmdIndex',7,-2),('m_state',99,-1)]]),  #136
    ('_struct',[[('m_soundtrack',5,-1)]]),  #137
    ('_struct',[[('m_planetId',72,-1)]]),  #138
    ('_struct',[[('m_key',99,-2),('m_flags',99,-1)]]),  #139
    ('_struct',[[('m_resources',96,-1)]]),  #140
    ('_struct',[[('m_fulfillRequestId',72,-1)]]),  #141
    ('_struct',[[('m_cancelRequestId',72,-1)]]),  #142
    ('_struct',[[('m_researchItemId',72,-1)]]),  #143
    ('_struct',[[('m_mercenaryId',72,-1)]]),  #144
    ('_struct',[[('m_battleReportId',72,-2),('m_difficultyLevel',72,-1)]]),  #145
    ('_struct',[[('m_battleReportId',72,-1)]]),  #146
    ('_int',[(0,19)]),  #147
    ('_struct',[[('m_decrementMs',147,-1)]]),  #148
    ('_struct',[[('m_portraitId',72,-1)]]),  #149
    ('_struct',[[('m_functionName',15,-1)]]),  #150
    ('_struct',[[('m_result',72,-1)]]),  #151
    ('_struct',[[('m_gameMenuItemIndex',72,-1)]]),  #152
    ('_struct',[[('m_reason',99,-1)]]),  #153
    ('_struct',[[('m_purchaseCategoryId',72,-1)]]),  #154
    ('_struct',[[('m_button',77,-1)]]),  #155
    ('_struct',[[('m_cutsceneId',72,-2),('m_bookmarkName',15,-1)]]),  #156
    ('_struct',[[('m_cutsceneId',72,-1)]]),  #157
    ('_struct',[[('m_cutsceneId',72,-3),('m_conversationLine',15,-2),('m_altConversationLine',15,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',72,-2),('m_conversationLine',15,-1)]]),  #159
    ('_struct',[[('m_observe',19,-3),('m_name',9,-2),('m_toonHandle',110,-1)]]),  #160
    ('_struct',[[('m_recipient',12,-2),('m_string',25,-1)]]),  #161
    ('_struct',[[('m_recipient',12,-2),('m_point',73,-1)]]),  #162
    ('_struct',[[('m_progress',72,-1)]]),  #163
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (70, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (69, 'NNet.Game.SUserOptionsEvent'),
    9: (62, 'NNet.Game.SBankFileEvent'),
    10: (64, 'NNet.Game.SBankSectionEvent'),
    11: (65, 'NNet.Game.SBankKeyEvent'),
    12: (66, 'NNet.Game.SBankValueEvent'),
    13: (68, 'NNet.Game.SBankSignatureEvent'),
    21: (71, 'NNet.Game.SSaveGameEvent'),
    22: (70, 'NNet.Game.SSaveGameDoneEvent'),
    23: (70, 'NNet.Game.SLoadGameDoneEvent'),
    26: (75, 'NNet.Game.SGameCheatEvent'),
    27: (84, 'NNet.Game.SCmdEvent'),
    28: (92, 'NNet.Game.SSelectionDeltaEvent'),
    29: (93, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (95, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (97, 'NNet.Game.SResourceTradeEvent'),
    32: (98, 'NNet.Game.STriggerChatMessageEvent'),
    33: (101, 'NNet.Game.SAICommunicateEvent'),
    34: (102, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (103, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (104, 'NNet.Game.STriggerPingEvent'),
    37: (105, 'NNet.Game.SBroadcastCheatEvent'),
    38: (106, 'NNet.Game.SAllianceEvent'),
    39: (107, 'NNet.Game.SUnitClickEvent'),
    40: (108, 'NNet.Game.SUnitHighlightEvent'),
    41: (109, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (113, 'NNet.Game.SHijackReplayGameEvent'),
    44: (70, 'NNet.Game.STriggerSkippedEvent'),
    45: (118, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (122, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (123, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (124, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (128, 'NNet.Game.SCameraUpdateEvent'),
    50: (70, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (114, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (70, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (115, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (70, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (117, 'NNet.Game.STriggerDialogControlEvent'),
    56: (121, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (130, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (133, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (134, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (135, 'NNet.Game.SAchievementAwardedEvent'),
    62: (136, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (70, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (137, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (138, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (139, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (150, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (70, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (70, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (140, 'NNet.Game.SResourceRequestEvent'),
    71: (141, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (142, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (70, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (70, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (143, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (70, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (70, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (144, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (70, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (70, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (145, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (146, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (146, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (115, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (70, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (70, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (148, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (149, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (151, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (152, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (153, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (114, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (154, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (155, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (70, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (156, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (157, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (158, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (159, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (70, 'NNet.Game.SGameUserLeaveEvent'),
    102: (160, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (161, 'NNet.Game.SChatMessage'),
    1: (162, 'NNet.Game.SPingMessage'),
    2: (163, 'NNet.Game.SLoadingProgressMessage'),
    3: (70, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 6

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 35

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 61


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol24944
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,5)]),  #2
    ('_int',[(0,6)]),  #3
    ('_int',[(0,14)]),  #4
    ('_int',[(0,22)]),  #5
    ('_int',[(0,32)]),  #6
    ('_choice',[(0,2),{0:('m_uint6',3),1:('m_uint14',4),2:('m_uint22',5),3:('m_uint32',6)}]),  #7
    ('_struct',[[('m_userId',2,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',6,4),('m_baseBuild',6,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',6,3)]]),  #13
    ('_fourcc',[]),  #14
    ('_blob',[(0,7)]),  #15
    ('_int',[(0,64)]),  #16
    ('_struct',[[('m_region',10,0),('m_programId',14,1),('m_realm',6,2),('m_name',15,3),('m_id',16,4)]]),  #17
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #18
    ('_int',[(0,2)]),  #19
    ('_optional',[10]),  #20
    ('_struct',[[('m_name',9,0),('m_toon',17,1),('m_race',9,2),('m_color',18,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',19,7),('m_result',19,8),('m_workingSetSlotId',20,9)]]),  #21
    ('_array',[(0,5),21]),  #22
    ('_optional',[22]),  #23
    ('_blob',[(0,10)]),  #24
    ('_blob',[(0,11)]),  #25
    ('_struct',[[('m_file',25,0)]]),  #26
    ('_bool',[]),  #27
    ('_int',[(-9223372036854775808,64)]),  #28
    ('_blob',[(0,12)]),  #29
    ('_blob',[(40,0)]),  #30
    ('_array',[(0,6),30]),  #31
    ('_optional',[31]),  #32
    ('_array',[(0,6),25]),  #33
    ('_optional',[33]),  #34
    ('_struct',[[('m_playerList',23,0),('m_title',24,1),('m_difficulty',9,2),('m_thumbnail',26,3),('m_isBlizzardMap',27,4),('m_timeUTC',28,5),('m_timeLocalOffset',28,6),('m_description',29,7),('m_imageFilePath',25,8),('m_campaignIndex',10,15),('m_mapFileName',25,9),('m_cacheHandles',32,10),('m_miniSave',27,11),('m_gameSpeed',12,12),('m_defaultDifficulty',3,13),('m_modPaths',34,14)]]),  #35
    ('_optional',[9]),  #36
    ('_optional',[6]),  #37
    ('_struct',[[('m_race',20,-1)]]),  #38
    ('_struct',[[('m_team',20,-1)]]),  #39
    ('_struct',[[('m_name',9,-12),('m_clanTag',36,-11),('m_highestLeague',20,-10),('m_combinedRaceLevels',37,-9),('m_randomSeed',6,-8),('m_racePreference',38,-7),('m_teamPreference',39,-6),('m_testMap',27,-5),('m_testAuto',27,-4),('m_examine',27,-3),('m_customInterface',27,-2),('m_observe',19,-1)]]),  #40
    ('_array',[(0,5),40]),  #41
    ('_struct',[[('m_lockTeams',27,-12),('m_teamsTogether',27,-11),('m_advancedSharedControl',27,-10),('m_randomRaces',27,-9),('m_battleNet',27,-8),('m_amm',27,-7),('m_competitive',27,-6),('m_noVictoryOrDefeat',27,-5),('m_fog',19,-4),('m_observers',19,-3),('m_userDifficulty',19,-2),('m_clientDebugFlags',16,-1)]]),  #42
    ('_int',[(1,4)]),  #43
    ('_int',[(1,8)]),  #44
    ('_bitarray',[(0,6)]),  #45
    ('_bitarray',[(0,8)]),  #46
    ('_bitarray',[(0,2)]),  #47
    ('_bitarray',[(0,7)]),  #48
    ('_struct',[[('m_allowedColors',45,-6),('m_allowedRaces',46,-5),('m_allowedDifficulty',45,-4),('m_allowedControls',46,-3),('m_allowedObserveTypes',47,-2),('m_allowedAIBuilds',48,-1)]]),  #49
    ('_array',[(0,5),49]),  #50
    ('_struct',[[('m_randomValue',6,-25),('m_gameCacheName',24,-24),('m_gameOptions',42,-23),('m_gameSpeed',12,-22),('m_gameType',12,-21),('m_maxUsers',2,-20),('m_maxObservers',2,-19),('m_maxPlayers',2,-18),('m_maxTeams',43,-17),('m_maxColors',3,-16),('m_maxRaces',44,-15),('m_maxControls',44,-14),('m_mapSizeX',10,-13),('m_mapSizeY',10,-12),('m_mapFileSyncChecksum',6,-11),('m_mapFileName',25,-10),('m_mapAuthorName',9,-9),('m_modFileSyncChecksum',6,-8),('m_slotDescriptions',50,-7),('m_defaultDifficulty',3,-6),('m_defaultAIBuild',0,-5),('m_cacheHandles',31,-4),('m_isBlizzardMap',27,-3),('m_isPremadeFFA',27,-2),('m_isCoopMode',27,-1)]]),  #51
    ('_optional',[1]),  #52
    ('_optional',[2]),  #53
    ('_struct',[[('m_color',53,-1)]]),  #54
    ('_array',[(0,6),6]),  #55
    ('_array',[(0,9),6]),  #56
    ('_struct',[[('m_control',10,-13),('m_userId',52,-12),('m_teamId',1,-11),('m_colorPref',54,-10),('m_racePref',38,-9),('m_difficulty',3,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',19,-5),('m_workingSetSlotId',20,-4),('m_rewards',55,-3),('m_toonHandle',15,-2),('m_licenses',56,-1)]]),  #57
    ('_array',[(0,5),57]),  #58
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',2,-9),('m_maxObservers',2,-8),('m_slots',58,-7),('m_randomSeed',6,-6),('m_hostUserId',52,-5),('m_isSinglePlayer',27,-4),('m_gameDuration',6,-3),('m_defaultDifficulty',3,-2),('m_defaultAIBuild',0,-1)]]),  #59
    ('_struct',[[('m_userInitialData',41,-3),('m_gameDescription',51,-2),('m_lobbyState',59,-1)]]),  #60
    ('_struct',[[('m_syncLobbyState',60,-1)]]),  #61
    ('_struct',[[('m_name',15,-1)]]),  #62
    ('_blob',[(0,6)]),  #63
    ('_struct',[[('m_name',63,-1)]]),  #64
    ('_struct',[[('m_name',63,-3),('m_type',6,-2),('m_data',15,-1)]]),  #65
    ('_struct',[[('m_type',6,-3),('m_name',63,-2),('m_data',29,-1)]]),  #66
    ('_array',[(0,5),10]),  #67
    ('_struct',[[('m_signature',67,-2),('m_toonHandle',15,-1)]]),  #68
    ('_struct',[[('m_gameFullyDownloaded',27,-7),('m_developmentCheatsEnabled',27,-6),('m_multiplayerCheatsEnabled',27,-5),('m_syncChecksummingEnabled',27,-4),('m_isMapToMapTransition',27,-3),('m_startingRally',27,-2),('m_baseBuildNum',6,-1)]]),  #69
    ('_struct',[[]]),  #70
    ('_int',[(0,16)]),  #71
    ('_struct',[[('x',71,-2),('y',71,-1)]]),  #72
    ('_struct',[[('m_which',12,-2),('m_target',72,-1)]]),  #73
    ('_struct',[[('m_fileName',25,-5),('m_automatic',27,-4),('m_overwrite',27,-3),('m_name',9,-2),('m_description',24,-1)]]),  #74
    ('_int',[(-2147483648,32)]),  #75
    ('_struct',[[('x',75,-2),('y',75,-1)]]),  #76
    ('_struct',[[('m_point',76,-4),('m_time',75,-3),('m_verb',24,-2),('m_arguments',24,-1)]]),  #77
    ('_struct',[[('m_data',77,-1)]]),  #78
    ('_int',[(0,20)]),  #79
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',2,-2),('m_abilCmdData',20,-1)]]),  #80
    ('_optional',[80]),  #81
    ('_null',[]),  #82
    ('_struct',[[('x',79,-3),('y',79,-2),('z',75,-1)]]),  #83
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',6,-5),('m_snapshotUnitLink',71,-4),('m_snapshotControlPlayerId',52,-3),('m_snapshotUpkeepPlayerId',52,-2),('m_snapshotPoint',83,-1)]]),  #84
    ('_choice',[(0,2),{0:('None',82),1:('TargetPoint',83),2:('TargetUnit',84),3:('Data',6)}]),  #85
    ('_struct',[[('m_cmdFlags',79,-4),('m_abil',81,-3),('m_data',85,-2),('m_otherUnit',37,-1)]]),  #86
    ('_int',[(0,9)]),  #87
    ('_bitarray',[(0,9)]),  #88
    ('_array',[(0,9),87]),  #89
    ('_choice',[(0,2),{0:('None',82),1:('Mask',88),2:('OneIndices',89),3:('ZeroIndices',89)}]),  #90
    ('_struct',[[('m_unitLink',71,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',87,-1)]]),  #91
    ('_array',[(0,9),91]),  #92
    ('_struct',[[('m_subgroupIndex',87,-4),('m_removeMask',90,-3),('m_addSubgroups',92,-2),('m_addUnitTags',56,-1)]]),  #93
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',93,-1)]]),  #94
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',19,-2),('m_mask',90,-1)]]),  #95
    ('_struct',[[('m_count',87,-6),('m_subgroupCount',87,-5),('m_activeSubgroupIndex',87,-4),('m_unitTagsChecksum',6,-3),('m_subgroupIndicesChecksum',6,-2),('m_subgroupsChecksum',6,-1)]]),  #96
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',96,-1)]]),  #97
    ('_array',[(0,3),75]),  #98
    ('_struct',[[('m_recipientId',1,-2),('m_resources',98,-1)]]),  #99
    ('_struct',[[('m_chatMessage',24,-1)]]),  #100
    ('_int',[(-128,8)]),  #101
    ('_struct',[[('x',75,-3),('y',75,-2),('z',75,-1)]]),  #102
    ('_struct',[[('m_beacon',101,-9),('m_ally',101,-8),('m_flags',101,-7),('m_build',101,-6),('m_targetUnitTag',6,-5),('m_targetUnitSnapshotUnitLink',71,-4),('m_targetUnitSnapshotUpkeepPlayerId',101,-3),('m_targetUnitSnapshotControlPlayerId',101,-2),('m_targetPoint',102,-1)]]),  #103
    ('_struct',[[('m_speed',12,-1)]]),  #104
    ('_struct',[[('m_delta',101,-1)]]),  #105
    ('_struct',[[('m_point',76,-3),('m_unit',6,-2),('m_pingedMinimap',27,-1)]]),  #106
    ('_struct',[[('m_verb',24,-2),('m_arguments',24,-1)]]),  #107
    ('_struct',[[('m_alliance',6,-2),('m_control',6,-1)]]),  #108
    ('_struct',[[('m_unitTag',6,-1)]]),  #109
    ('_struct',[[('m_unitTag',6,-2),('m_flags',10,-1)]]),  #110
    ('_struct',[[('m_conversationId',75,-2),('m_replyId',75,-1)]]),  #111
    ('_optional',[15]),  #112
    ('_struct',[[('m_gameUserId',1,-5),('m_observe',19,-4),('m_name',9,-3),('m_toonHandle',112,-2),('m_clanTag',36,-1)]]),  #113
    ('_array',[(0,5),113]),  #114
    ('_int',[(0,1)]),  #115
    ('_struct',[[('m_userInfos',114,-2),('m_method',115,-1)]]),  #116
    ('_struct',[[('m_purchaseItemId',75,-1)]]),  #117
    ('_struct',[[('m_difficultyLevel',75,-1)]]),  #118
    ('_choice',[(0,3),{0:('None',82),1:('Checked',27),2:('ValueChanged',6),3:('SelectionChanged',75),4:('TextChanged',25),5:('MouseButton',6)}]),  #119
    ('_struct',[[('m_controlId',75,-3),('m_eventType',75,-2),('m_eventData',119,-1)]]),  #120
    ('_struct',[[('m_soundHash',6,-2),('m_length',6,-1)]]),  #121
    ('_array',[(0,7),6]),  #122
    ('_struct',[[('m_soundHash',122,-2),('m_length',122,-1)]]),  #123
    ('_struct',[[('m_syncInfo',123,-1)]]),  #124
    ('_struct',[[('m_sound',6,-1)]]),  #125
    ('_struct',[[('m_transmissionId',75,-2),('m_thread',6,-1)]]),  #126
    ('_struct',[[('m_transmissionId',75,-1)]]),  #127
    ('_optional',[72]),  #128
    ('_optional',[71]),  #129
    ('_struct',[[('m_target',128,-4),('m_distance',129,-3),('m_pitch',129,-2),('m_yaw',129,-1)]]),  #130
    ('_struct',[[('m_skipType',115,-1)]]),  #131
    ('_int',[(0,11)]),  #132
    ('_struct',[[('x',132,-2),('y',132,-1)]]),  #133
    ('_struct',[[('m_button',6,-4),('m_down',27,-3),('m_posUI',133,-2),('m_posWorld',83,-1)]]),  #134
    ('_struct',[[('m_posUI',133,-2),('m_posWorld',83,-1)]]),  #135
    ('_struct',[[('m_achievementLink',71,-1)]]),  #136
    ('_struct',[[('m_abilLink',71,-3),('m_abilCmdIndex',2,-2),('m_state',101,-1)]]),  #137
    ('_struct',[[('m_soundtrack',6,-1)]]),  #138
    ('_struct',[[('m_planetId',75,-1)]]),  #139
    ('_struct',[[('m_key',101,-2),('m_flags',101,-1)]]),  #140
    ('_struct',[[('m_resources',98,-1)]]),  #141
    ('_struct',[[('m_fulfillRequestId',75,-1)]]),  #142
    ('_struct',[[('m_cancelRequestId',75,-1)]]),  #143
    ('_struct',[[('m_researchItemId',75,-1)]]),  #144
    ('_struct',[[('m_mercenaryId',75,-1)]]),  #145
    ('_struct',[[('m_battleReportId',75,-2),('m_difficultyLevel',75,-1)]]),  #146
    ('_struct',[[('m_battleReportId',75,-1)]]),  #147
    ('_int',[(0,19)]),  #148
    ('_struct',[[('m_decrementMs',148,-1)]]),  #149
    ('_struct',[[('m_portraitId',75,-1)]]),  #150
    ('_struct',[[('m_functionName',15,-1)]]),  #151
    ('_struct',[[('m_result',75,-1)]]),  #152
    ('_struct',[[('m_gameMenuItemIndex',75,-1)]]),  #153
    ('_struct',[[('m_reason',101,-1)]]),  #154
    ('_struct',[[('m_purchaseCategoryId',75,-1)]]),  #155
    ('_struct',[[('m_button',71,-1)]]),  #156
    ('_struct',[[('m_cutsceneId',75,-2),('m_bookmarkName',15,-1)]]),  #157
    ('_struct',[[('m_cutsceneId',75,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',75,-3),('m_conversationLine',15,-2),('m_altConversationLine',15,-1)]]),  #159
    ('_struct',[[('m_cutsceneId',75,-2),('m_conversationLine',15,-1)]]),  #160
    ('_struct',[[('m_observe',19,-4),('m_name',9,-3),('m_toonHandle',112,-2),('m_clanTag',36,-1)]]),  #161
    ('_struct',[[('m_recipient',12,-2),('m_string',25,-1)]]),  #162
    ('_struct',[[('m_recipient',12,-2),('m_point',76,-1)]]),  #163
    ('_struct',[[('m_progress',75,-1)]]),  #164
    ('_struct',[[('m_scoreValueMineralsCurrent',75,0),('m_scoreValueVespeneCurrent',75,1),('m_scoreValueMineralsCollectionRate',75,2),('m_scoreValueVespeneCollectionRate',75,3),('m_scoreValueWorkersActiveCount',75,4),('m_scoreValueMineralsUsedInProgressArmy',75,5),('m_scoreValueMineralsUsedInProgressEconomy',75,6),('m_scoreValueMineralsUsedInProgressTechnology',75,7),('m_scoreValueVespeneUsedInProgressArmy',75,8),('m_scoreValueVespeneUsedInProgressEconomy',75,9),('m_scoreValueVespeneUsedInProgressTechnology',75,10),('m_scoreValueMineralsUsedCurrentArmy',75,11),('m_scoreValueMineralsUsedCurrentEconomy',75,12),('m_scoreValueMineralsUsedCurrentTechnology',75,13),('m_scoreValueVespeneUsedCurrentArmy',75,14),('m_scoreValueVespeneUsedCurrentEconomy',75,15),('m_scoreValueVespeneUsedCurrentTechnology',75,16),('m_scoreValueMineralsLostArmy',75,17),('m_scoreValueMineralsLostEconomy',75,18),('m_scoreValueMineralsLostTechnology',75,19),('m_scoreValueVespeneLostArmy',75,20),('m_scoreValueVespeneLostEconomy',75,21),('m_scoreValueVespeneLostTechnology',75,22),('m_scoreValueMineralsKilledArmy',75,23),('m_scoreValueMineralsKilledEconomy',75,24),('m_scoreValueMineralsKilledTechnology',75,25),('m_scoreValueVespeneKilledArmy',75,26),('m_scoreValueVespeneKilledEconomy',75,27),('m_scoreValueVespeneKilledTechnology',75,28),('m_scoreValueFoodUsed',75,29),('m_scoreValueFoodMade',75,30),('m_scoreValueMineralsUsedActiveForces',75,31),('m_scoreValueVespeneUsedActiveForces',75,32)]]),  #165
    ('_struct',[[('m_playerId',1,0),('m_stats',165,1)]]),  #166
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',24,2),('m_controlPlayerId',1,3),('m_upkeepPlayerId',1,4),('m_x',10,5),('m_y',10,6)]]),  #167
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_killerPlayerId',52,2),('m_x',10,3),('m_y',10,4)]]),  #168
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_controlPlayerId',1,2),('m_upkeepPlayerId',1,3)]]),  #169
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',24,2)]]),  #170
    ('_struct',[[('m_playerId',1,0),('m_upgradeTypeName',24,1),('m_count',75,2)]]),  #171
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1)]]),  #172
    ('_array',[(0,10),75]),  #173
    ('_struct',[[('m_firstUnitIndex',6,0),('m_items',173,1)]]),  #174
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (70, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (69, 'NNet.Game.SUserOptionsEvent'),
    9: (62, 'NNet.Game.SBankFileEvent'),
    10: (64, 'NNet.Game.SBankSectionEvent'),
    11: (65, 'NNet.Game.SBankKeyEvent'),
    12: (66, 'NNet.Game.SBankValueEvent'),
    13: (68, 'NNet.Game.SBankSignatureEvent'),
    14: (73, 'NNet.Game.SCameraSaveEvent'),
    21: (74, 'NNet.Game.SSaveGameEvent'),
    22: (70, 'NNet.Game.SSaveGameDoneEvent'),
    23: (70, 'NNet.Game.SLoadGameDoneEvent'),
    26: (78, 'NNet.Game.SGameCheatEvent'),
    27: (86, 'NNet.Game.SCmdEvent'),
    28: (94, 'NNet.Game.SSelectionDeltaEvent'),
    29: (95, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (97, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (99, 'NNet.Game.SResourceTradeEvent'),
    32: (100, 'NNet.Game.STriggerChatMessageEvent'),
    33: (103, 'NNet.Game.SAICommunicateEvent'),
    34: (104, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (105, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (106, 'NNet.Game.STriggerPingEvent'),
    37: (107, 'NNet.Game.SBroadcastCheatEvent'),
    38: (108, 'NNet.Game.SAllianceEvent'),
    39: (109, 'NNet.Game.SUnitClickEvent'),
    40: (110, 'NNet.Game.SUnitHighlightEvent'),
    41: (111, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (116, 'NNet.Game.SHijackReplayGameEvent'),
    44: (70, 'NNet.Game.STriggerSkippedEvent'),
    45: (121, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (125, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (126, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (127, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (130, 'NNet.Game.SCameraUpdateEvent'),
    50: (70, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (117, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (70, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (118, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (70, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (120, 'NNet.Game.STriggerDialogControlEvent'),
    56: (124, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (131, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (134, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (135, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (136, 'NNet.Game.SAchievementAwardedEvent'),
    62: (137, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (70, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (138, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (139, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (140, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (151, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (70, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (70, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (141, 'NNet.Game.SResourceRequestEvent'),
    71: (142, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (143, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (70, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (70, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (144, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (70, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (70, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (145, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (70, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (70, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (146, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (147, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (147, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (118, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (70, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (70, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (149, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (150, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (152, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (153, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (154, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (117, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (155, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (156, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (70, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (157, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (158, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (159, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (160, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (70, 'NNet.Game.SGameUserLeaveEvent'),
    102: (161, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (162, 'NNet.Game.SChatMessage'),
    1: (163, 'NNet.Game.SPingMessage'),
    2: (164, 'NNet.Game.SLoadingProgressMessage'),
    3: (70, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# Map from protocol NNet.Replay.Tracker.*Event eventid to (typeid, name)
tracker_event_types = {
    0: (166, 'NNet.Replay.Tracker.SPlayerStatsEvent'),
    1: (167, 'NNet.Replay.Tracker.SUnitBornEvent'),
    2: (168, 'NNet.Replay.Tracker.SUnitDiedEvent'),
    3: (169, 'NNet.Replay.Tracker.SUnitOwnerChangeEvent'),
    4: (170, 'NNet.Replay.Tracker.SUnitTypeChangeEvent'),
    5: (171, 'NNet.Replay.Tracker.SUpgradeEvent'),
    6: (167, 'NNet.Replay.Tracker.SUnitInitEvent'),
    7: (172, 'NNet.Replay.Tracker.SUnitDoneEvent'),
    8: (174, 'NNet.Replay.Tracker.SUnitPositionsEvent'),
}

# The typeid of the NNet.Replay.Tracker.EEventId enum.
tracker_eventid_typeid = 2

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 7

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 13

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 35

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 61


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_tracker_events(contents):
    """Decodes and yields each tracker event from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      tracker_eventid_typeid,
                                      tracker_event_types,
                                      decode_user_id=False):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol26490
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,5)]),  #2
    ('_int',[(0,6)]),  #3
    ('_int',[(0,14)]),  #4
    ('_int',[(0,22)]),  #5
    ('_int',[(0,32)]),  #6
    ('_choice',[(0,2),{0:('m_uint6',3),1:('m_uint14',4),2:('m_uint22',5),3:('m_uint32',6)}]),  #7
    ('_struct',[[('m_userId',2,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',6,4),('m_baseBuild',6,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_bool',[]),  #13
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',6,3),('m_useScaledTime',13,4)]]),  #14
    ('_fourcc',[]),  #15
    ('_blob',[(0,7)]),  #16
    ('_int',[(0,64)]),  #17
    ('_struct',[[('m_region',10,0),('m_programId',15,1),('m_realm',6,2),('m_name',16,3),('m_id',17,4)]]),  #18
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #19
    ('_int',[(0,2)]),  #20
    ('_optional',[10]),  #21
    ('_struct',[[('m_name',9,0),('m_toon',18,1),('m_race',9,2),('m_color',19,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',20,7),('m_result',20,8),('m_workingSetSlotId',21,9)]]),  #22
    ('_array',[(0,5),22]),  #23
    ('_optional',[23]),  #24
    ('_blob',[(0,10)]),  #25
    ('_blob',[(0,11)]),  #26
    ('_struct',[[('m_file',26,0)]]),  #27
    ('_optional',[13]),  #28
    ('_int',[(-9223372036854775808,64)]),  #29
    ('_blob',[(0,12)]),  #30
    ('_blob',[(40,0)]),  #31
    ('_array',[(0,6),31]),  #32
    ('_optional',[32]),  #33
    ('_array',[(0,6),26]),  #34
    ('_optional',[34]),  #35
    ('_struct',[[('m_playerList',24,0),('m_title',25,1),('m_difficulty',9,2),('m_thumbnail',27,3),('m_isBlizzardMap',13,4),('m_restartAsTransitionMap',28,16),('m_timeUTC',29,5),('m_timeLocalOffset',29,6),('m_description',30,7),('m_imageFilePath',26,8),('m_campaignIndex',10,15),('m_mapFileName',26,9),('m_cacheHandles',33,10),('m_miniSave',13,11),('m_gameSpeed',12,12),('m_defaultDifficulty',3,13),('m_modPaths',35,14)]]),  #36
    ('_optional',[9]),  #37
    ('_optional',[6]),  #38
    ('_struct',[[('m_race',21,-1)]]),  #39
    ('_struct',[[('m_team',21,-1)]]),  #40
    ('_struct',[[('m_name',9,-12),('m_clanTag',37,-11),('m_highestLeague',21,-10),('m_combinedRaceLevels',38,-9),('m_randomSeed',6,-8),('m_racePreference',39,-7),('m_teamPreference',40,-6),('m_testMap',13,-5),('m_testAuto',13,-4),('m_examine',13,-3),('m_customInterface',13,-2),('m_observe',20,-1)]]),  #41
    ('_array',[(0,5),41]),  #42
    ('_struct',[[('m_lockTeams',13,-12),('m_teamsTogether',13,-11),('m_advancedSharedControl',13,-10),('m_randomRaces',13,-9),('m_battleNet',13,-8),('m_amm',13,-7),('m_competitive',13,-6),('m_noVictoryOrDefeat',13,-5),('m_fog',20,-4),('m_observers',20,-3),('m_userDifficulty',20,-2),('m_clientDebugFlags',17,-1)]]),  #43
    ('_int',[(1,4)]),  #44
    ('_int',[(1,8)]),  #45
    ('_bitarray',[(0,6)]),  #46
    ('_bitarray',[(0,8)]),  #47
    ('_bitarray',[(0,2)]),  #48
    ('_bitarray',[(0,7)]),  #49
    ('_struct',[[('m_allowedColors',46,-6),('m_allowedRaces',47,-5),('m_allowedDifficulty',46,-4),('m_allowedControls',47,-3),('m_allowedObserveTypes',48,-2),('m_allowedAIBuilds',49,-1)]]),  #50
    ('_array',[(0,5),50]),  #51
    ('_struct',[[('m_randomValue',6,-25),('m_gameCacheName',25,-24),('m_gameOptions',43,-23),('m_gameSpeed',12,-22),('m_gameType',12,-21),('m_maxUsers',2,-20),('m_maxObservers',2,-19),('m_maxPlayers',2,-18),('m_maxTeams',44,-17),('m_maxColors',3,-16),('m_maxRaces',45,-15),('m_maxControls',10,-14),('m_mapSizeX',10,-13),('m_mapSizeY',10,-12),('m_mapFileSyncChecksum',6,-11),('m_mapFileName',26,-10),('m_mapAuthorName',9,-9),('m_modFileSyncChecksum',6,-8),('m_slotDescriptions',51,-7),('m_defaultDifficulty',3,-6),('m_defaultAIBuild',0,-5),('m_cacheHandles',32,-4),('m_isBlizzardMap',13,-3),('m_isPremadeFFA',13,-2),('m_isCoopMode',13,-1)]]),  #52
    ('_optional',[1]),  #53
    ('_optional',[2]),  #54
    ('_struct',[[('m_color',54,-1)]]),  #55
    ('_array',[(0,6),6]),  #56
    ('_array',[(0,9),6]),  #57
    ('_struct',[[('m_control',10,-13),('m_userId',53,-12),('m_teamId',1,-11),('m_colorPref',55,-10),('m_racePref',39,-9),('m_difficulty',3,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',20,-5),('m_workingSetSlotId',21,-4),('m_rewards',56,-3),('m_toonHandle',16,-2),('m_licenses',57,-1)]]),  #58
    ('_array',[(0,5),58]),  #59
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',2,-9),('m_maxObservers',2,-8),('m_slots',59,-7),('m_randomSeed',6,-6),('m_hostUserId',53,-5),('m_isSinglePlayer',13,-4),('m_gameDuration',6,-3),('m_defaultDifficulty',3,-2),('m_defaultAIBuild',0,-1)]]),  #60
    ('_struct',[[('m_userInitialData',42,-3),('m_gameDescription',52,-2),('m_lobbyState',60,-1)]]),  #61
    ('_struct',[[('m_syncLobbyState',61,-1)]]),  #62
    ('_struct',[[('m_name',16,-1)]]),  #63
    ('_blob',[(0,6)]),  #64
    ('_struct',[[('m_name',64,-1)]]),  #65
    ('_struct',[[('m_name',64,-3),('m_type',6,-2),('m_data',16,-1)]]),  #66
    ('_struct',[[('m_type',6,-3),('m_name',64,-2),('m_data',30,-1)]]),  #67
    ('_array',[(0,5),10]),  #68
    ('_struct',[[('m_signature',68,-2),('m_toonHandle',16,-1)]]),  #69
    ('_struct',[[('m_gameFullyDownloaded',13,-8),('m_developmentCheatsEnabled',13,-7),('m_multiplayerCheatsEnabled',13,-6),('m_syncChecksummingEnabled',13,-5),('m_isMapToMapTransition',13,-4),('m_startingRally',13,-3),('m_debugPauseEnabled',13,-2),('m_baseBuildNum',6,-1)]]),  #70
    ('_struct',[[]]),  #71
    ('_int',[(0,16)]),  #72
    ('_struct',[[('x',72,-2),('y',72,-1)]]),  #73
    ('_struct',[[('m_which',12,-2),('m_target',73,-1)]]),  #74
    ('_struct',[[('m_fileName',26,-5),('m_automatic',13,-4),('m_overwrite',13,-3),('m_name',9,-2),('m_description',25,-1)]]),  #75
    ('_int',[(-2147483648,32)]),  #76
    ('_struct',[[('x',76,-2),('y',76,-1)]]),  #77
    ('_struct',[[('m_point',77,-4),('m_time',76,-3),('m_verb',25,-2),('m_arguments',25,-1)]]),  #78
    ('_struct',[[('m_data',78,-1)]]),  #79
    ('_int',[(0,20)]),  #80
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',2,-2),('m_abilCmdData',21,-1)]]),  #81
    ('_optional',[81]),  #82
    ('_null',[]),  #83
    ('_struct',[[('x',80,-3),('y',80,-2),('z',76,-1)]]),  #84
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',6,-5),('m_snapshotUnitLink',72,-4),('m_snapshotControlPlayerId',53,-3),('m_snapshotUpkeepPlayerId',53,-2),('m_snapshotPoint',84,-1)]]),  #85
    ('_choice',[(0,2),{0:('None',83),1:('TargetPoint',84),2:('TargetUnit',85),3:('Data',6)}]),  #86
    ('_struct',[[('m_cmdFlags',80,-4),('m_abil',82,-3),('m_data',86,-2),('m_otherUnit',38,-1)]]),  #87
    ('_int',[(0,9)]),  #88
    ('_bitarray',[(0,9)]),  #89
    ('_array',[(0,9),88]),  #90
    ('_choice',[(0,2),{0:('None',83),1:('Mask',89),2:('OneIndices',90),3:('ZeroIndices',90)}]),  #91
    ('_struct',[[('m_unitLink',72,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',88,-1)]]),  #92
    ('_array',[(0,9),92]),  #93
    ('_struct',[[('m_subgroupIndex',88,-4),('m_removeMask',91,-3),('m_addSubgroups',93,-2),('m_addUnitTags',57,-1)]]),  #94
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',94,-1)]]),  #95
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',20,-2),('m_mask',91,-1)]]),  #96
    ('_struct',[[('m_count',88,-6),('m_subgroupCount',88,-5),('m_activeSubgroupIndex',88,-4),('m_unitTagsChecksum',6,-3),('m_subgroupIndicesChecksum',6,-2),('m_subgroupsChecksum',6,-1)]]),  #97
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',97,-1)]]),  #98
    ('_array',[(0,3),76]),  #99
    ('_struct',[[('m_recipientId',1,-2),('m_resources',99,-1)]]),  #100
    ('_struct',[[('m_chatMessage',25,-1)]]),  #101
    ('_int',[(-128,8)]),  #102
    ('_struct',[[('x',76,-3),('y',76,-2),('z',76,-1)]]),  #103
    ('_struct',[[('m_beacon',102,-9),('m_ally',102,-8),('m_flags',102,-7),('m_build',102,-6),('m_targetUnitTag',6,-5),('m_targetUnitSnapshotUnitLink',72,-4),('m_targetUnitSnapshotUpkeepPlayerId',102,-3),('m_targetUnitSnapshotControlPlayerId',102,-2),('m_targetPoint',103,-1)]]),  #104
    ('_struct',[[('m_speed',12,-1)]]),  #105
    ('_struct',[[('m_delta',102,-1)]]),  #106
    ('_struct',[[('m_point',77,-3),('m_unit',6,-2),('m_pingedMinimap',13,-1)]]),  #107
    ('_struct',[[('m_verb',25,-2),('m_arguments',25,-1)]]),  #108
    ('_struct',[[('m_alliance',6,-2),('m_control',6,-1)]]),  #109
    ('_struct',[[('m_unitTag',6,-1)]]),  #110
    ('_struct',[[('m_unitTag',6,-2),('m_flags',10,-1)]]),  #111
    ('_struct',[[('m_conversationId',76,-2),('m_replyId',76,-1)]]),  #112
    ('_optional',[16]),  #113
    ('_struct',[[('m_gameUserId',1,-5),('m_observe',20,-4),('m_name',9,-3),('m_toonHandle',113,-2),('m_clanTag',37,-1)]]),  #114
    ('_array',[(0,5),114]),  #115
    ('_int',[(0,1)]),  #116
    ('_struct',[[('m_userInfos',115,-2),('m_method',116,-1)]]),  #117
    ('_struct',[[('m_purchaseItemId',76,-1)]]),  #118
    ('_struct',[[('m_difficultyLevel',76,-1)]]),  #119
    ('_choice',[(0,3),{0:('None',83),1:('Checked',13),2:('ValueChanged',6),3:('SelectionChanged',76),4:('TextChanged',26),5:('MouseButton',6)}]),  #120
    ('_struct',[[('m_controlId',76,-3),('m_eventType',76,-2),('m_eventData',120,-1)]]),  #121
    ('_struct',[[('m_soundHash',6,-2),('m_length',6,-1)]]),  #122
    ('_array',[(0,7),6]),  #123
    ('_struct',[[('m_soundHash',123,-2),('m_length',123,-1)]]),  #124
    ('_struct',[[('m_syncInfo',124,-1)]]),  #125
    ('_struct',[[('m_sound',6,-1)]]),  #126
    ('_struct',[[('m_transmissionId',76,-2),('m_thread',6,-1)]]),  #127
    ('_struct',[[('m_transmissionId',76,-1)]]),  #128
    ('_optional',[73]),  #129
    ('_optional',[72]),  #130
    ('_struct',[[('m_target',129,-4),('m_distance',130,-3),('m_pitch',130,-2),('m_yaw',130,-1)]]),  #131
    ('_struct',[[('m_skipType',116,-1)]]),  #132
    ('_int',[(0,11)]),  #133
    ('_struct',[[('x',133,-2),('y',133,-1)]]),  #134
    ('_struct',[[('m_button',6,-5),('m_down',13,-4),('m_posUI',134,-3),('m_posWorld',84,-2),('m_flags',102,-1)]]),  #135
    ('_struct',[[('m_posUI',134,-3),('m_posWorld',84,-2),('m_flags',102,-1)]]),  #136
    ('_struct',[[('m_achievementLink',72,-1)]]),  #137
    ('_struct',[[('m_abilLink',72,-3),('m_abilCmdIndex',2,-2),('m_state',102,-1)]]),  #138
    ('_struct',[[('m_soundtrack',6,-1)]]),  #139
    ('_struct',[[('m_planetId',76,-1)]]),  #140
    ('_struct',[[('m_key',102,-2),('m_flags',102,-1)]]),  #141
    ('_struct',[[('m_resources',99,-1)]]),  #142
    ('_struct',[[('m_fulfillRequestId',76,-1)]]),  #143
    ('_struct',[[('m_cancelRequestId',76,-1)]]),  #144
    ('_struct',[[('m_researchItemId',76,-1)]]),  #145
    ('_struct',[[('m_mercenaryId',76,-1)]]),  #146
    ('_struct',[[('m_battleReportId',76,-2),('m_difficultyLevel',76,-1)]]),  #147
    ('_struct',[[('m_battleReportId',76,-1)]]),  #148
    ('_int',[(0,19)]),  #149
    ('_struct',[[('m_decrementMs',149,-1)]]),  #150
    ('_struct',[[('m_portraitId',76,-1)]]),  #151
    ('_struct',[[('m_functionName',16,-1)]]),  #152
    ('_struct',[[('m_result',76,-1)]]),  #153
    ('_struct',[[('m_gameMenuItemIndex',76,-1)]]),  #154
    ('_struct',[[('m_reason',102,-1)]]),  #155
    ('_struct',[[('m_purchaseCategoryId',76,-1)]]),  #156
    ('_struct',[[('m_button',72,-1)]]),  #157
    ('_struct',[[('m_cutsceneId',76,-2),('m_bookmarkName',16,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',76,-1)]]),  #159
    ('_struct',[[('m_cutsceneId',76,-3),('m_conversationLine',16,-2),('m_altConversationLine',16,-1)]]),  #160
    ('_struct',[[('m_cutsceneId',76,-2),('m_conversationLine',16,-1)]]),  #161
    ('_struct',[[('m_observe',20,-4),('m_name',9,-3),('m_toonHandle',113,-2),('m_clanTag',37,-1)]]),  #162
    ('_struct',[[('m_recipient',12,-2),('m_string',26,-1)]]),  #163
    ('_struct',[[('m_recipient',12,-2),('m_point',77,-1)]]),  #164
    ('_struct',[[('m_progress',76,-1)]]),  #165
    ('_struct',[[('m_scoreValueMineralsCurrent',76,0),('m_scoreValueVespeneCurrent',76,1),('m_scoreValueMineralsCollectionRate',76,2),('m_scoreValueVespeneCollectionRate',76,3),('m_scoreValueWorkersActiveCount',76,4),('m_scoreValueMineralsUsedInProgressArmy',76,5),('m_scoreValueMineralsUsedInProgressEconomy',76,6),('m_scoreValueMineralsUsedInProgressTechnology',76,7),('m_scoreValueVespeneUsedInProgressArmy',76,8),('m_scoreValueVespeneUsedInProgressEconomy',76,9),('m_scoreValueVespeneUsedInProgressTechnology',76,10),('m_scoreValueMineralsUsedCurrentArmy',76,11),('m_scoreValueMineralsUsedCurrentEconomy',76,12),('m_scoreValueMineralsUsedCurrentTechnology',76,13),('m_scoreValueVespeneUsedCurrentArmy',76,14),('m_scoreValueVespeneUsedCurrentEconomy',76,15),('m_scoreValueVespeneUsedCurrentTechnology',76,16),('m_scoreValueMineralsLostArmy',76,17),('m_scoreValueMineralsLostEconomy',76,18),('m_scoreValueMineralsLostTechnology',76,19),('m_scoreValueVespeneLostArmy',76,20),('m_scoreValueVespeneLostEconomy',76,21),('m_scoreValueVespeneLostTechnology',76,22),('m_scoreValueMineralsKilledArmy',76,23),('m_scoreValueMineralsKilledEconomy',76,24),('m_scoreValueMineralsKilledTechnology',76,25),('m_scoreValueVespeneKilledArmy',76,26),('m_scoreValueVespeneKilledEconomy',76,27),('m_scoreValueVespeneKilledTechnology',76,28),('m_scoreValueFoodUsed',76,29),('m_scoreValueFoodMade',76,30),('m_scoreValueMineralsUsedActiveForces',76,31),('m_scoreValueVespeneUsedActiveForces',76,32),('m_scoreValueMineralsFriendlyFireArmy',76,33),('m_scoreValueMineralsFriendlyFireEconomy',76,34),('m_scoreValueMineralsFriendlyFireTechnology',76,35),('m_scoreValueVespeneFriendlyFireArmy',76,36),('m_scoreValueVespeneFriendlyFireEconomy',76,37),('m_scoreValueVespeneFriendlyFireTechnology',76,38)]]),  #166
    ('_struct',[[('m_playerId',1,0),('m_stats',166,1)]]),  #167
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2),('m_controlPlayerId',1,3),('m_upkeepPlayerId',1,4),('m_x',10,5),('m_y',10,6)]]),  #168
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_killerPlayerId',53,2),('m_x',10,3),('m_y',10,4)]]),  #169
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_controlPlayerId',1,2),('m_upkeepPlayerId',1,3)]]),  #170
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2)]]),  #171
    ('_struct',[[('m_playerId',1,0),('m_upgradeTypeName',25,1),('m_count',76,2)]]),  #172
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1)]]),  #173
    ('_array',[(0,10),76]),  #174
    ('_struct',[[('m_firstUnitIndex',6,0),('m_items',174,1)]]),  #175
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (71, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (70, 'NNet.Game.SUserOptionsEvent'),
    9: (63, 'NNet.Game.SBankFileEvent'),
    10: (65, 'NNet.Game.SBankSectionEvent'),
    11: (66, 'NNet.Game.SBankKeyEvent'),
    12: (67, 'NNet.Game.SBankValueEvent'),
    13: (69, 'NNet.Game.SBankSignatureEvent'),
    14: (74, 'NNet.Game.SCameraSaveEvent'),
    21: (75, 'NNet.Game.SSaveGameEvent'),
    22: (71, 'NNet.Game.SSaveGameDoneEvent'),
    23: (71, 'NNet.Game.SLoadGameDoneEvent'),
    26: (79, 'NNet.Game.SGameCheatEvent'),
    27: (87, 'NNet.Game.SCmdEvent'),
    28: (95, 'NNet.Game.SSelectionDeltaEvent'),
    29: (96, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (98, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (100, 'NNet.Game.SResourceTradeEvent'),
    32: (101, 'NNet.Game.STriggerChatMessageEvent'),
    33: (104, 'NNet.Game.SAICommunicateEvent'),
    34: (105, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (106, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (107, 'NNet.Game.STriggerPingEvent'),
    37: (108, 'NNet.Game.SBroadcastCheatEvent'),
    38: (109, 'NNet.Game.SAllianceEvent'),
    39: (110, 'NNet.Game.SUnitClickEvent'),
    40: (111, 'NNet.Game.SUnitHighlightEvent'),
    41: (112, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (117, 'NNet.Game.SHijackReplayGameEvent'),
    44: (71, 'NNet.Game.STriggerSkippedEvent'),
    45: (122, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (126, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (127, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (128, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (131, 'NNet.Game.SCameraUpdateEvent'),
    50: (71, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (118, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (71, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (119, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (71, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (121, 'NNet.Game.STriggerDialogControlEvent'),
    56: (125, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (132, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (135, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (136, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (137, 'NNet.Game.SAchievementAwardedEvent'),
    62: (138, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (71, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (139, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (140, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (141, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (152, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (71, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (71, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (142, 'NNet.Game.SResourceRequestEvent'),
    71: (143, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (144, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (71, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (71, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (145, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (71, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (71, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (146, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (71, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (71, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (147, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (148, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (148, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (119, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (71, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (71, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (150, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (151, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (153, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (154, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    92: (155, 'NNet.Game.STriggerCameraMoveEvent'),
    93: (118, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (156, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (157, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (71, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (158, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (159, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (160, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (161, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (71, 'NNet.Game.SGameUserLeaveEvent'),
    102: (162, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (163, 'NNet.Game.SChatMessage'),
    1: (164, 'NNet.Game.SPingMessage'),
    2: (165, 'NNet.Game.SLoadingProgressMessage'),
    3: (71, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# Map from protocol NNet.Replay.Tracker.*Event eventid to (typeid, name)
tracker_event_types = {
    0: (167, 'NNet.Replay.Tracker.SPlayerStatsEvent'),
    1: (168, 'NNet.Replay.Tracker.SUnitBornEvent'),
    2: (169, 'NNet.Replay.Tracker.SUnitDiedEvent'),
    3: (170, 'NNet.Replay.Tracker.SUnitOwnerChangeEvent'),
    4: (171, 'NNet.Replay.Tracker.SUnitTypeChangeEvent'),
    5: (172, 'NNet.Replay.Tracker.SUpgradeEvent'),
    6: (168, 'NNet.Replay.Tracker.SUnitInitEvent'),
    7: (173, 'NNet.Replay.Tracker.SUnitDoneEvent'),
    8: (175, 'NNet.Replay.Tracker.SUnitPositionsEvent'),
}

# The typeid of the NNet.Replay.Tracker.EEventId enum.
tracker_eventid_typeid = 2

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 7

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 14

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 36

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 62


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_tracker_events(contents):
    """Decodes and yields each tracker event from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      tracker_eventid_typeid,
                                      tracker_event_types,
                                      decode_user_id=False):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol27950
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,5)]),  #2
    ('_int',[(0,6)]),  #3
    ('_int',[(0,14)]),  #4
    ('_int',[(0,22)]),  #5
    ('_int',[(0,32)]),  #6
    ('_choice',[(0,2),{0:('m_uint6',3),1:('m_uint14',4),2:('m_uint22',5),3:('m_uint32',6)}]),  #7
    ('_struct',[[('m_userId',2,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',6,4),('m_baseBuild',6,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_bool',[]),  #13
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',6,3),('m_useScaledTime',13,4)]]),  #14
    ('_fourcc',[]),  #15
    ('_blob',[(0,7)]),  #16
    ('_int',[(0,64)]),  #17
    ('_struct',[[('m_region',10,0),('m_programId',15,1),('m_realm',6,2),('m_name',16,3),('m_id',17,4)]]),  #18
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #19
    ('_int',[(0,2)]),  #20
    ('_optional',[10]),  #21
    ('_struct',[[('m_name',9,0),('m_toon',18,1),('m_race',9,2),('m_color',19,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',20,7),('m_result',20,8),('m_workingSetSlotId',21,9)]]),  #22
    ('_array',[(0,5),22]),  #23
    ('_optional',[23]),  #24
    ('_blob',[(0,10)]),  #25
    ('_blob',[(0,11)]),  #26
    ('_struct',[[('m_file',26,0)]]),  #27
    ('_optional',[13]),  #28
    ('_int',[(-9223372036854775808,64)]),  #29
    ('_blob',[(0,12)]),  #30
    ('_blob',[(40,0)]),  #31
    ('_array',[(0,6),31]),  #32
    ('_optional',[32]),  #33
    ('_array',[(0,6),26]),  #34
    ('_optional',[34]),  #35
    ('_struct',[[('m_playerList',24,0),('m_title',25,1),('m_difficulty',9,2),('m_thumbnail',27,3),('m_isBlizzardMap',13,4),('m_restartAsTransitionMap',28,16),('m_timeUTC',29,5),('m_timeLocalOffset',29,6),('m_description',30,7),('m_imageFilePath',26,8),('m_campaignIndex',10,15),('m_mapFileName',26,9),('m_cacheHandles',33,10),('m_miniSave',13,11),('m_gameSpeed',12,12),('m_defaultDifficulty',3,13),('m_modPaths',35,14)]]),  #36
    ('_optional',[9]),  #37
    ('_optional',[31]),  #38
    ('_optional',[6]),  #39
    ('_struct',[[('m_race',21,-1)]]),  #40
    ('_struct',[[('m_team',21,-1)]]),  #41
    ('_struct',[[('m_name',9,-13),('m_clanTag',37,-12),('m_clanLogo',38,-11),('m_highestLeague',21,-10),('m_combinedRaceLevels',39,-9),('m_randomSeed',6,-8),('m_racePreference',40,-7),('m_teamPreference',41,-6),('m_testMap',13,-5),('m_testAuto',13,-4),('m_examine',13,-3),('m_customInterface',13,-2),('m_observe',20,-1)]]),  #42
    ('_array',[(0,5),42]),  #43
    ('_struct',[[('m_lockTeams',13,-12),('m_teamsTogether',13,-11),('m_advancedSharedControl',13,-10),('m_randomRaces',13,-9),('m_battleNet',13,-8),('m_amm',13,-7),('m_competitive',13,-6),('m_noVictoryOrDefeat',13,-5),('m_fog',20,-4),('m_observers',20,-3),('m_userDifficulty',20,-2),('m_clientDebugFlags',17,-1)]]),  #44
    ('_int',[(1,4)]),  #45
    ('_int',[(1,8)]),  #46
    ('_bitarray',[(0,6)]),  #47
    ('_bitarray',[(0,8)]),  #48
    ('_bitarray',[(0,2)]),  #49
    ('_bitarray',[(0,7)]),  #50
    ('_struct',[[('m_allowedColors',47,-6),('m_allowedRaces',48,-5),('m_allowedDifficulty',47,-4),('m_allowedControls',48,-3),('m_allowedObserveTypes',49,-2),('m_allowedAIBuilds',50,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_randomValue',6,-26),('m_gameCacheName',25,-25),('m_gameOptions',44,-24),('m_gameSpeed',12,-23),('m_gameType',12,-22),('m_maxUsers',2,-21),('m_maxObservers',2,-20),('m_maxPlayers',2,-19),('m_maxTeams',45,-18),('m_maxColors',3,-17),('m_maxRaces',46,-16),('m_maxControls',10,-15),('m_mapSizeX',10,-14),('m_mapSizeY',10,-13),('m_mapFileSyncChecksum',6,-12),('m_mapFileName',26,-11),('m_mapAuthorName',9,-10),('m_modFileSyncChecksum',6,-9),('m_slotDescriptions',52,-8),('m_defaultDifficulty',3,-7),('m_defaultAIBuild',0,-6),('m_cacheHandles',32,-5),('m_hasExtensionMod',13,-4),('m_isBlizzardMap',13,-3),('m_isPremadeFFA',13,-2),('m_isCoopMode',13,-1)]]),  #53
    ('_optional',[1]),  #54
    ('_optional',[2]),  #55
    ('_struct',[[('m_color',55,-1)]]),  #56
    ('_array',[(0,6),6]),  #57
    ('_array',[(0,9),6]),  #58
    ('_struct',[[('m_control',10,-13),('m_userId',54,-12),('m_teamId',1,-11),('m_colorPref',56,-10),('m_racePref',40,-9),('m_difficulty',3,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',20,-5),('m_workingSetSlotId',21,-4),('m_rewards',57,-3),('m_toonHandle',16,-2),('m_licenses',58,-1)]]),  #59
    ('_array',[(0,5),59]),  #60
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',2,-9),('m_maxObservers',2,-8),('m_slots',60,-7),('m_randomSeed',6,-6),('m_hostUserId',54,-5),('m_isSinglePlayer',13,-4),('m_gameDuration',6,-3),('m_defaultDifficulty',3,-2),('m_defaultAIBuild',0,-1)]]),  #61
    ('_struct',[[('m_userInitialData',43,-3),('m_gameDescription',53,-2),('m_lobbyState',61,-1)]]),  #62
    ('_struct',[[('m_syncLobbyState',62,-1)]]),  #63
    ('_struct',[[('m_name',16,-1)]]),  #64
    ('_blob',[(0,6)]),  #65
    ('_struct',[[('m_name',65,-1)]]),  #66
    ('_struct',[[('m_name',65,-3),('m_type',6,-2),('m_data',16,-1)]]),  #67
    ('_struct',[[('m_type',6,-3),('m_name',65,-2),('m_data',30,-1)]]),  #68
    ('_array',[(0,5),10]),  #69
    ('_struct',[[('m_signature',69,-2),('m_toonHandle',16,-1)]]),  #70
    ('_struct',[[('m_gameFullyDownloaded',13,-8),('m_developmentCheatsEnabled',13,-7),('m_multiplayerCheatsEnabled',13,-6),('m_syncChecksummingEnabled',13,-5),('m_isMapToMapTransition',13,-4),('m_startingRally',13,-3),('m_debugPauseEnabled',13,-2),('m_baseBuildNum',6,-1)]]),  #71
    ('_struct',[[]]),  #72
    ('_int',[(0,16)]),  #73
    ('_struct',[[('x',73,-2),('y',73,-1)]]),  #74
    ('_struct',[[('m_which',12,-2),('m_target',74,-1)]]),  #75
    ('_struct',[[('m_fileName',26,-5),('m_automatic',13,-4),('m_overwrite',13,-3),('m_name',9,-2),('m_description',25,-1)]]),  #76
    ('_int',[(-2147483648,32)]),  #77
    ('_struct',[[('x',77,-2),('y',77,-1)]]),  #78
    ('_struct',[[('m_point',78,-4),('m_time',77,-3),('m_verb',25,-2),('m_arguments',25,-1)]]),  #79
    ('_struct',[[('m_data',79,-1)]]),  #80
    ('_int',[(0,20)]),  #81
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_abilCmdData',21,-1)]]),  #82
    ('_optional',[82]),  #83
    ('_null',[]),  #84
    ('_struct',[[('x',81,-3),('y',81,-2),('z',77,-1)]]),  #85
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',6,-5),('m_snapshotUnitLink',73,-4),('m_snapshotControlPlayerId',54,-3),('m_snapshotUpkeepPlayerId',54,-2),('m_snapshotPoint',85,-1)]]),  #86
    ('_choice',[(0,2),{0:('None',84),1:('TargetPoint',85),2:('TargetUnit',86),3:('Data',6)}]),  #87
    ('_struct',[[('m_cmdFlags',81,-4),('m_abil',83,-3),('m_data',87,-2),('m_otherUnit',39,-1)]]),  #88
    ('_int',[(0,9)]),  #89
    ('_bitarray',[(0,9)]),  #90
    ('_array',[(0,9),89]),  #91
    ('_choice',[(0,2),{0:('None',84),1:('Mask',90),2:('OneIndices',91),3:('ZeroIndices',91)}]),  #92
    ('_struct',[[('m_unitLink',73,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',89,-1)]]),  #93
    ('_array',[(0,9),93]),  #94
    ('_struct',[[('m_subgroupIndex',89,-4),('m_removeMask',92,-3),('m_addSubgroups',94,-2),('m_addUnitTags',58,-1)]]),  #95
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',95,-1)]]),  #96
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',20,-2),('m_mask',92,-1)]]),  #97
    ('_struct',[[('m_count',89,-6),('m_subgroupCount',89,-5),('m_activeSubgroupIndex',89,-4),('m_unitTagsChecksum',6,-3),('m_subgroupIndicesChecksum',6,-2),('m_subgroupsChecksum',6,-1)]]),  #98
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',98,-1)]]),  #99
    ('_array',[(0,3),77]),  #100
    ('_struct',[[('m_recipientId',1,-2),('m_resources',100,-1)]]),  #101
    ('_struct',[[('m_chatMessage',25,-1)]]),  #102
    ('_int',[(-128,8)]),  #103
    ('_struct',[[('x',77,-3),('y',77,-2),('z',77,-1)]]),  #104
    ('_struct',[[('m_beacon',103,-9),('m_ally',103,-8),('m_flags',103,-7),('m_build',103,-6),('m_targetUnitTag',6,-5),('m_targetUnitSnapshotUnitLink',73,-4),('m_targetUnitSnapshotUpkeepPlayerId',103,-3),('m_targetUnitSnapshotControlPlayerId',103,-2),('m_targetPoint',104,-1)]]),  #105
    ('_struct',[[('m_speed',12,-1)]]),  #106
    ('_struct',[[('m_delta',103,-1)]]),  #107
    ('_struct',[[('m_point',78,-3),('m_unit',6,-2),('m_pingedMinimap',13,-1)]]),  #108
    ('_struct',[[('m_verb',25,-2),('m_arguments',25,-1)]]),  #109
    ('_struct',[[('m_alliance',6,-2),('m_control',6,-1)]]),  #110
    ('_struct',[[('m_unitTag',6,-1)]]),  #111
    ('_struct',[[('m_unitTag',6,-2),('m_flags',10,-1)]]),  #112
    ('_struct',[[('m_conversationId',77,-2),('m_replyId',77,-1)]]),  #113
    ('_optional',[16]),  #114
    ('_struct',[[('m_gameUserId',1,-6),('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #115
    ('_array',[(0,5),115]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_userInfos',116,-2),('m_method',117,-1)]]),  #118
    ('_struct',[[('m_purchaseItemId',77,-1)]]),  #119
    ('_struct',[[('m_difficultyLevel',77,-1)]]),  #120
    ('_choice',[(0,3),{0:('None',84),1:('Checked',13),2:('ValueChanged',6),3:('SelectionChanged',77),4:('TextChanged',26),5:('MouseButton',6)}]),  #121
    ('_struct',[[('m_controlId',77,-3),('m_eventType',77,-2),('m_eventData',121,-1)]]),  #122
    ('_struct',[[('m_soundHash',6,-2),('m_length',6,-1)]]),  #123
    ('_array',[(0,7),6]),  #124
    ('_struct',[[('m_soundHash',124,-2),('m_length',124,-1)]]),  #125
    ('_struct',[[('m_syncInfo',125,-1)]]),  #126
    ('_struct',[[('m_sound',6,-1)]]),  #127
    ('_struct',[[('m_transmissionId',77,-2),('m_thread',6,-1)]]),  #128
    ('_struct',[[('m_transmissionId',77,-1)]]),  #129
    ('_optional',[74]),  #130
    ('_optional',[73]),  #131
    ('_optional',[103]),  #132
    ('_struct',[[('m_target',130,-5),('m_distance',131,-4),('m_pitch',131,-3),('m_yaw',131,-2),('m_reason',132,-1)]]),  #133
    ('_struct',[[('m_skipType',117,-1)]]),  #134
    ('_int',[(0,11)]),  #135
    ('_struct',[[('x',135,-2),('y',135,-1)]]),  #136
    ('_struct',[[('m_button',6,-5),('m_down',13,-4),('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #137
    ('_struct',[[('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #138
    ('_struct',[[('m_achievementLink',73,-1)]]),  #139
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_state',103,-1)]]),  #140
    ('_struct',[[('m_soundtrack',6,-1)]]),  #141
    ('_struct',[[('m_planetId',77,-1)]]),  #142
    ('_struct',[[('m_key',103,-2),('m_flags',103,-1)]]),  #143
    ('_struct',[[('m_resources',100,-1)]]),  #144
    ('_struct',[[('m_fulfillRequestId',77,-1)]]),  #145
    ('_struct',[[('m_cancelRequestId',77,-1)]]),  #146
    ('_struct',[[('m_researchItemId',77,-1)]]),  #147
    ('_struct',[[('m_mercenaryId',77,-1)]]),  #148
    ('_struct',[[('m_battleReportId',77,-2),('m_difficultyLevel',77,-1)]]),  #149
    ('_struct',[[('m_battleReportId',77,-1)]]),  #150
    ('_int',[(0,19)]),  #151
    ('_struct',[[('m_decrementMs',151,-1)]]),  #152
    ('_struct',[[('m_portraitId',77,-1)]]),  #153
    ('_struct',[[('m_functionName',16,-1)]]),  #154
    ('_struct',[[('m_result',77,-1)]]),  #155
    ('_struct',[[('m_gameMenuItemIndex',77,-1)]]),  #156
    ('_struct',[[('m_purchaseCategoryId',77,-1)]]),  #157
    ('_struct',[[('m_button',73,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',77,-2),('m_bookmarkName',16,-1)]]),  #159
    ('_struct',[[('m_cutsceneId',77,-1)]]),  #160
    ('_struct',[[('m_cutsceneId',77,-3),('m_conversationLine',16,-2),('m_altConversationLine',16,-1)]]),  #161
    ('_struct',[[('m_cutsceneId',77,-2),('m_conversationLine',16,-1)]]),  #162
    ('_struct',[[('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #163
    ('_struct',[[('m_recipient',12,-2),('m_string',26,-1)]]),  #164
    ('_struct',[[('m_recipient',12,-2),('m_point',78,-1)]]),  #165
    ('_struct',[[('m_progress',77,-1)]]),  #166
    ('_struct',[[('m_scoreValueMineralsCurrent',77,0),('m_scoreValueVespeneCurrent',77,1),('m_scoreValueMineralsCollectionRate',77,2),('m_scoreValueVespeneCollectionRate',77,3),('m_scoreValueWorkersActiveCount',77,4),('m_scoreValueMineralsUsedInProgressArmy',77,5),('m_scoreValueMineralsUsedInProgressEconomy',77,6),('m_scoreValueMineralsUsedInProgressTechnology',77,7),('m_scoreValueVespeneUsedInProgressArmy',77,8),('m_scoreValueVespeneUsedInProgressEconomy',77,9),('m_scoreValueVespeneUsedInProgressTechnology',77,10),('m_scoreValueMineralsUsedCurrentArmy',77,11),('m_scoreValueMineralsUsedCurrentEconomy',77,12),('m_scoreValueMineralsUsedCurrentTechnology',77,13),('m_scoreValueVespeneUsedCurrentArmy',77,14),('m_scoreValueVespeneUsedCurrentEconomy',77,15),('m_scoreValueVespeneUsedCurrentTechnology',77,16),('m_scoreValueMineralsLostArmy',77,17),('m_scoreValueMineralsLostEconomy',77,18),('m_scoreValueMineralsLostTechnology',77,19),('m_scoreValueVespeneLostArmy',77,20),('m_scoreValueVespeneLostEconomy',77,21),('m_scoreValueVespeneLostTechnology',77,22),('m_scoreValueMineralsKilledArmy',77,23),('m_scoreValueMineralsKilledEconomy',77,24),('m_scoreValueMineralsKilledTechnology',77,25),('m_scoreValueVespeneKilledArmy',77,26),('m_scoreValueVespeneKilledEconomy',77,27),('m_scoreValueVespeneKilledTechnology',77,28),('m_scoreValueFoodUsed',77,29),('m_scoreValueFoodMade',77,30),('m_scoreValueMineralsUsedActiveForces',77,31),('m_scoreValueVespeneUsedActiveForces',77,32),('m_scoreValueMineralsFriendlyFireArmy',77,33),('m_scoreValueMineralsFriendlyFireEconomy',77,34),('m_scoreValueMineralsFriendlyFireTechnology',77,35),('m_scoreValueVespeneFriendlyFireArmy',77,36),('m_scoreValueVespeneFriendlyFireEconomy',77,37),('m_scoreValueVespeneFriendlyFireTechnology',77,38)]]),  #167
    ('_struct',[[('m_playerId',1,0),('m_stats',167,1)]]),  #168
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2),('m_controlPlayerId',1,3),('m_upkeepPlayerId',1,4),('m_x',10,5),('m_y',10,6)]]),  #169
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_killerPlayerId',54,2),('m_x',10,3),('m_y',10,4),('m_killerUnitTagIndex',39,5),('m_killerUnitTagRecycle',39,6)]]),  #170
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_controlPlayerId',1,2),('m_upkeepPlayerId',1,3)]]),  #171
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2)]]),  #172
    ('_struct',[[('m_playerId',1,0),('m_upgradeTypeName',25,1),('m_count',77,2)]]),  #173
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1)]]),  #174
    ('_array',[(0,10),77]),  #175
    ('_struct',[[('m_firstUnitIndex',6,0),('m_items',175,1)]]),  #176
    ('_struct',[[('m_playerId',1,0),('m_type',6,1),('m_userId',39,2),('m_slotId',39,3)]]),  #177
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (72, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (71, 'NNet.Game.SUserOptionsEvent'),
    9: (64, 'NNet.Game.SBankFileEvent'),
    10: (66, 'NNet.Game.SBankSectionEvent'),
    11: (67, 'NNet.Game.SBankKeyEvent'),
    12: (68, 'NNet.Game.SBankValueEvent'),
    13: (70, 'NNet.Game.SBankSignatureEvent'),
    14: (75, 'NNet.Game.SCameraSaveEvent'),
    21: (76, 'NNet.Game.SSaveGameEvent'),
    22: (72, 'NNet.Game.SSaveGameDoneEvent'),
    23: (72, 'NNet.Game.SLoadGameDoneEvent'),
    26: (80, 'NNet.Game.SGameCheatEvent'),
    27: (88, 'NNet.Game.SCmdEvent'),
    28: (96, 'NNet.Game.SSelectionDeltaEvent'),
    29: (97, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (99, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (101, 'NNet.Game.SResourceTradeEvent'),
    32: (102, 'NNet.Game.STriggerChatMessageEvent'),
    33: (105, 'NNet.Game.SAICommunicateEvent'),
    34: (106, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (107, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (108, 'NNet.Game.STriggerPingEvent'),
    37: (109, 'NNet.Game.SBroadcastCheatEvent'),
    38: (110, 'NNet.Game.SAllianceEvent'),
    39: (111, 'NNet.Game.SUnitClickEvent'),
    40: (112, 'NNet.Game.SUnitHighlightEvent'),
    41: (113, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (118, 'NNet.Game.SHijackReplayGameEvent'),
    44: (72, 'NNet.Game.STriggerSkippedEvent'),
    45: (123, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (127, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (128, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (129, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (133, 'NNet.Game.SCameraUpdateEvent'),
    50: (72, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (119, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (72, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (120, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (72, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (122, 'NNet.Game.STriggerDialogControlEvent'),
    56: (126, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (134, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (137, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (138, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (139, 'NNet.Game.SAchievementAwardedEvent'),
    62: (140, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (72, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (141, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (142, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (143, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (154, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (72, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (72, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (144, 'NNet.Game.SResourceRequestEvent'),
    71: (145, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (146, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (72, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (72, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (147, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (72, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (72, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (148, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (72, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (72, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (149, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (150, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (150, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (120, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (72, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (72, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (152, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (153, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (155, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (156, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    93: (119, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (157, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (158, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (72, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (159, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (160, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (161, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (162, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (72, 'NNet.Game.SGameUserLeaveEvent'),
    102: (163, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (164, 'NNet.Game.SChatMessage'),
    1: (165, 'NNet.Game.SPingMessage'),
    2: (166, 'NNet.Game.SLoadingProgressMessage'),
    3: (72, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# Map from protocol NNet.Replay.Tracker.*Event eventid to (typeid, name)
tracker_event_types = {
    0: (168, 'NNet.Replay.Tracker.SPlayerStatsEvent'),
    1: (169, 'NNet.Replay.Tracker.SUnitBornEvent'),
    2: (170, 'NNet.Replay.Tracker.SUnitDiedEvent'),
    3: (171, 'NNet.Replay.Tracker.SUnitOwnerChangeEvent'),
    4: (172, 'NNet.Replay.Tracker.SUnitTypeChangeEvent'),
    5: (173, 'NNet.Replay.Tracker.SUpgradeEvent'),
    6: (169, 'NNet.Replay.Tracker.SUnitInitEvent'),
    7: (174, 'NNet.Replay.Tracker.SUnitDoneEvent'),
    8: (176, 'NNet.Replay.Tracker.SUnitPositionsEvent'),
    9: (177, 'NNet.Replay.Tracker.SPlayerSetupEvent'),
}

# The typeid of the NNet.Replay.Tracker.EEventId enum.
tracker_eventid_typeid = 2

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 7

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 14

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 36

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 63


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_tracker_events(contents):
    """Decodes and yields each tracker event from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      tracker_eventid_typeid,
                                      tracker_event_types,
                                      decode_user_id=False):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol28272
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,5)]),  #2
    ('_int',[(0,6)]),  #3
    ('_int',[(0,14)]),  #4
    ('_int',[(0,22)]),  #5
    ('_int',[(0,32)]),  #6
    ('_choice',[(0,2),{0:('m_uint6',3),1:('m_uint14',4),2:('m_uint22',5),3:('m_uint32',6)}]),  #7
    ('_struct',[[('m_userId',2,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',6,4),('m_baseBuild',6,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_bool',[]),  #13
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',6,3),('m_useScaledTime',13,4)]]),  #14
    ('_fourcc',[]),  #15
    ('_blob',[(0,7)]),  #16
    ('_int',[(0,64)]),  #17
    ('_struct',[[('m_region',10,0),('m_programId',15,1),('m_realm',6,2),('m_name',16,3),('m_id',17,4)]]),  #18
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #19
    ('_int',[(0,2)]),  #20
    ('_optional',[10]),  #21
    ('_struct',[[('m_name',9,0),('m_toon',18,1),('m_race',9,2),('m_color',19,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',20,7),('m_result',20,8),('m_workingSetSlotId',21,9)]]),  #22
    ('_array',[(0,5),22]),  #23
    ('_optional',[23]),  #24
    ('_blob',[(0,10)]),  #25
    ('_blob',[(0,11)]),  #26
    ('_struct',[[('m_file',26,0)]]),  #27
    ('_optional',[13]),  #28
    ('_int',[(-9223372036854775808,64)]),  #29
    ('_blob',[(0,12)]),  #30
    ('_blob',[(40,0)]),  #31
    ('_array',[(0,6),31]),  #32
    ('_optional',[32]),  #33
    ('_array',[(0,6),26]),  #34
    ('_optional',[34]),  #35
    ('_struct',[[('m_playerList',24,0),('m_title',25,1),('m_difficulty',9,2),('m_thumbnail',27,3),('m_isBlizzardMap',13,4),('m_restartAsTransitionMap',28,16),('m_timeUTC',29,5),('m_timeLocalOffset',29,6),('m_description',30,7),('m_imageFilePath',26,8),('m_campaignIndex',10,15),('m_mapFileName',26,9),('m_cacheHandles',33,10),('m_miniSave',13,11),('m_gameSpeed',12,12),('m_defaultDifficulty',3,13),('m_modPaths',35,14)]]),  #36
    ('_optional',[9]),  #37
    ('_optional',[31]),  #38
    ('_optional',[6]),  #39
    ('_struct',[[('m_race',21,-1)]]),  #40
    ('_struct',[[('m_team',21,-1)]]),  #41
    ('_struct',[[('m_name',9,-13),('m_clanTag',37,-12),('m_clanLogo',38,-11),('m_highestLeague',21,-10),('m_combinedRaceLevels',39,-9),('m_randomSeed',6,-8),('m_racePreference',40,-7),('m_teamPreference',41,-6),('m_testMap',13,-5),('m_testAuto',13,-4),('m_examine',13,-3),('m_customInterface',13,-2),('m_observe',20,-1)]]),  #42
    ('_array',[(0,5),42]),  #43
    ('_struct',[[('m_lockTeams',13,-12),('m_teamsTogether',13,-11),('m_advancedSharedControl',13,-10),('m_randomRaces',13,-9),('m_battleNet',13,-8),('m_amm',13,-7),('m_competitive',13,-6),('m_noVictoryOrDefeat',13,-5),('m_fog',20,-4),('m_observers',20,-3),('m_userDifficulty',20,-2),('m_clientDebugFlags',17,-1)]]),  #44
    ('_int',[(1,4)]),  #45
    ('_int',[(1,8)]),  #46
    ('_bitarray',[(0,6)]),  #47
    ('_bitarray',[(0,8)]),  #48
    ('_bitarray',[(0,2)]),  #49
    ('_bitarray',[(0,7)]),  #50
    ('_struct',[[('m_allowedColors',47,-6),('m_allowedRaces',48,-5),('m_allowedDifficulty',47,-4),('m_allowedControls',48,-3),('m_allowedObserveTypes',49,-2),('m_allowedAIBuilds',50,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_randomValue',6,-26),('m_gameCacheName',25,-25),('m_gameOptions',44,-24),('m_gameSpeed',12,-23),('m_gameType',12,-22),('m_maxUsers',2,-21),('m_maxObservers',2,-20),('m_maxPlayers',2,-19),('m_maxTeams',45,-18),('m_maxColors',3,-17),('m_maxRaces',46,-16),('m_maxControls',10,-15),('m_mapSizeX',10,-14),('m_mapSizeY',10,-13),('m_mapFileSyncChecksum',6,-12),('m_mapFileName',26,-11),('m_mapAuthorName',9,-10),('m_modFileSyncChecksum',6,-9),('m_slotDescriptions',52,-8),('m_defaultDifficulty',3,-7),('m_defaultAIBuild',0,-6),('m_cacheHandles',32,-5),('m_hasExtensionMod',13,-4),('m_isBlizzardMap',13,-3),('m_isPremadeFFA',13,-2),('m_isCoopMode',13,-1)]]),  #53
    ('_optional',[1]),  #54
    ('_optional',[2]),  #55
    ('_struct',[[('m_color',55,-1)]]),  #56
    ('_array',[(0,6),6]),  #57
    ('_array',[(0,9),6]),  #58
    ('_struct',[[('m_control',10,-13),('m_userId',54,-12),('m_teamId',1,-11),('m_colorPref',56,-10),('m_racePref',40,-9),('m_difficulty',3,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',20,-5),('m_workingSetSlotId',21,-4),('m_rewards',57,-3),('m_toonHandle',16,-2),('m_licenses',58,-1)]]),  #59
    ('_array',[(0,5),59]),  #60
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',2,-9),('m_maxObservers',2,-8),('m_slots',60,-7),('m_randomSeed',6,-6),('m_hostUserId',54,-5),('m_isSinglePlayer',13,-4),('m_gameDuration',6,-3),('m_defaultDifficulty',3,-2),('m_defaultAIBuild',0,-1)]]),  #61
    ('_struct',[[('m_userInitialData',43,-3),('m_gameDescription',53,-2),('m_lobbyState',61,-1)]]),  #62
    ('_struct',[[('m_syncLobbyState',62,-1)]]),  #63
    ('_struct',[[('m_name',16,-1)]]),  #64
    ('_blob',[(0,6)]),  #65
    ('_struct',[[('m_name',65,-1)]]),  #66
    ('_struct',[[('m_name',65,-3),('m_type',6,-2),('m_data',16,-1)]]),  #67
    ('_struct',[[('m_type',6,-3),('m_name',65,-2),('m_data',30,-1)]]),  #68
    ('_array',[(0,5),10]),  #69
    ('_struct',[[('m_signature',69,-2),('m_toonHandle',16,-1)]]),  #70
    ('_struct',[[('m_gameFullyDownloaded',13,-8),('m_developmentCheatsEnabled',13,-7),('m_multiplayerCheatsEnabled',13,-6),('m_syncChecksummingEnabled',13,-5),('m_isMapToMapTransition',13,-4),('m_startingRally',13,-3),('m_debugPauseEnabled',13,-2),('m_baseBuildNum',6,-1)]]),  #71
    ('_struct',[[]]),  #72
    ('_int',[(0,16)]),  #73
    ('_struct',[[('x',73,-2),('y',73,-1)]]),  #74
    ('_struct',[[('m_which',12,-2),('m_target',74,-1)]]),  #75
    ('_struct',[[('m_fileName',26,-5),('m_automatic',13,-4),('m_overwrite',13,-3),('m_name',9,-2),('m_description',25,-1)]]),  #76
    ('_int',[(-2147483648,32)]),  #77
    ('_struct',[[('x',77,-2),('y',77,-1)]]),  #78
    ('_struct',[[('m_point',78,-4),('m_time',77,-3),('m_verb',25,-2),('m_arguments',25,-1)]]),  #79
    ('_struct',[[('m_data',79,-1)]]),  #80
    ('_int',[(0,20)]),  #81
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_abilCmdData',21,-1)]]),  #82
    ('_optional',[82]),  #83
    ('_null',[]),  #84
    ('_struct',[[('x',81,-3),('y',81,-2),('z',77,-1)]]),  #85
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',6,-5),('m_snapshotUnitLink',73,-4),('m_snapshotControlPlayerId',54,-3),('m_snapshotUpkeepPlayerId',54,-2),('m_snapshotPoint',85,-1)]]),  #86
    ('_choice',[(0,2),{0:('None',84),1:('TargetPoint',85),2:('TargetUnit',86),3:('Data',6)}]),  #87
    ('_struct',[[('m_cmdFlags',81,-4),('m_abil',83,-3),('m_data',87,-2),('m_otherUnit',39,-1)]]),  #88
    ('_int',[(0,9)]),  #89
    ('_bitarray',[(0,9)]),  #90
    ('_array',[(0,9),89]),  #91
    ('_choice',[(0,2),{0:('None',84),1:('Mask',90),2:('OneIndices',91),3:('ZeroIndices',91)}]),  #92
    ('_struct',[[('m_unitLink',73,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',89,-1)]]),  #93
    ('_array',[(0,9),93]),  #94
    ('_struct',[[('m_subgroupIndex',89,-4),('m_removeMask',92,-3),('m_addSubgroups',94,-2),('m_addUnitTags',58,-1)]]),  #95
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',95,-1)]]),  #96
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',20,-2),('m_mask',92,-1)]]),  #97
    ('_struct',[[('m_count',89,-6),('m_subgroupCount',89,-5),('m_activeSubgroupIndex',89,-4),('m_unitTagsChecksum',6,-3),('m_subgroupIndicesChecksum',6,-2),('m_subgroupsChecksum',6,-1)]]),  #98
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',98,-1)]]),  #99
    ('_array',[(0,3),77]),  #100
    ('_struct',[[('m_recipientId',1,-2),('m_resources',100,-1)]]),  #101
    ('_struct',[[('m_chatMessage',25,-1)]]),  #102
    ('_int',[(-128,8)]),  #103
    ('_struct',[[('x',77,-3),('y',77,-2),('z',77,-1)]]),  #104
    ('_struct',[[('m_beacon',103,-9),('m_ally',103,-8),('m_flags',103,-7),('m_build',103,-6),('m_targetUnitTag',6,-5),('m_targetUnitSnapshotUnitLink',73,-4),('m_targetUnitSnapshotUpkeepPlayerId',103,-3),('m_targetUnitSnapshotControlPlayerId',103,-2),('m_targetPoint',104,-1)]]),  #105
    ('_struct',[[('m_speed',12,-1)]]),  #106
    ('_struct',[[('m_delta',103,-1)]]),  #107
    ('_struct',[[('m_point',78,-3),('m_unit',6,-2),('m_pingedMinimap',13,-1)]]),  #108
    ('_struct',[[('m_verb',25,-2),('m_arguments',25,-1)]]),  #109
    ('_struct',[[('m_alliance',6,-2),('m_control',6,-1)]]),  #110
    ('_struct',[[('m_unitTag',6,-1)]]),  #111
    ('_struct',[[('m_unitTag',6,-2),('m_flags',10,-1)]]),  #112
    ('_struct',[[('m_conversationId',77,-2),('m_replyId',77,-1)]]),  #113
    ('_optional',[16]),  #114
    ('_struct',[[('m_gameUserId',1,-6),('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #115
    ('_array',[(0,5),115]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_userInfos',116,-2),('m_method',117,-1)]]),  #118
    ('_struct',[[('m_purchaseItemId',77,-1)]]),  #119
    ('_struct',[[('m_difficultyLevel',77,-1)]]),  #120
    ('_choice',[(0,3),{0:('None',84),1:('Checked',13),2:('ValueChanged',6),3:('SelectionChanged',77),4:('TextChanged',26),5:('MouseButton',6)}]),  #121
    ('_struct',[[('m_controlId',77,-3),('m_eventType',77,-2),('m_eventData',121,-1)]]),  #122
    ('_struct',[[('m_soundHash',6,-2),('m_length',6,-1)]]),  #123
    ('_array',[(0,7),6]),  #124
    ('_struct',[[('m_soundHash',124,-2),('m_length',124,-1)]]),  #125
    ('_struct',[[('m_syncInfo',125,-1)]]),  #126
    ('_struct',[[('m_sound',6,-1)]]),  #127
    ('_struct',[[('m_transmissionId',77,-2),('m_thread',6,-1)]]),  #128
    ('_struct',[[('m_transmissionId',77,-1)]]),  #129
    ('_optional',[74]),  #130
    ('_optional',[73]),  #131
    ('_optional',[103]),  #132
    ('_struct',[[('m_target',130,-5),('m_distance',131,-4),('m_pitch',131,-3),('m_yaw',131,-2),('m_reason',132,-1)]]),  #133
    ('_struct',[[('m_skipType',117,-1)]]),  #134
    ('_int',[(0,11)]),  #135
    ('_struct',[[('x',135,-2),('y',135,-1)]]),  #136
    ('_struct',[[('m_button',6,-5),('m_down',13,-4),('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #137
    ('_struct',[[('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #138
    ('_struct',[[('m_achievementLink',73,-1)]]),  #139
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_state',103,-1)]]),  #140
    ('_struct',[[('m_soundtrack',6,-1)]]),  #141
    ('_struct',[[('m_planetId',77,-1)]]),  #142
    ('_struct',[[('m_key',103,-2),('m_flags',103,-1)]]),  #143
    ('_struct',[[('m_resources',100,-1)]]),  #144
    ('_struct',[[('m_fulfillRequestId',77,-1)]]),  #145
    ('_struct',[[('m_cancelRequestId',77,-1)]]),  #146
    ('_struct',[[('m_researchItemId',77,-1)]]),  #147
    ('_struct',[[('m_mercenaryId',77,-1)]]),  #148
    ('_struct',[[('m_battleReportId',77,-2),('m_difficultyLevel',77,-1)]]),  #149
    ('_struct',[[('m_battleReportId',77,-1)]]),  #150
    ('_int',[(0,19)]),  #151
    ('_struct',[[('m_decrementMs',151,-1)]]),  #152
    ('_struct',[[('m_portraitId',77,-1)]]),  #153
    ('_struct',[[('m_functionName',16,-1)]]),  #154
    ('_struct',[[('m_result',77,-1)]]),  #155
    ('_struct',[[('m_gameMenuItemIndex',77,-1)]]),  #156
    ('_struct',[[('m_purchaseCategoryId',77,-1)]]),  #157
    ('_struct',[[('m_button',73,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',77,-2),('m_bookmarkName',16,-1)]]),  #159
    ('_struct',[[('m_cutsceneId',77,-1)]]),  #160
    ('_struct',[[('m_cutsceneId',77,-3),('m_conversationLine',16,-2),('m_altConversationLine',16,-1)]]),  #161
    ('_struct',[[('m_cutsceneId',77,-2),('m_conversationLine',16,-1)]]),  #162
    ('_struct',[[('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #163
    ('_struct',[[('m_recipient',12,-2),('m_string',26,-1)]]),  #164
    ('_struct',[[('m_recipient',12,-2),('m_point',78,-1)]]),  #165
    ('_struct',[[('m_progress',77,-1)]]),  #166
    ('_struct',[[('m_scoreValueMineralsCurrent',77,0),('m_scoreValueVespeneCurrent',77,1),('m_scoreValueMineralsCollectionRate',77,2),('m_scoreValueVespeneCollectionRate',77,3),('m_scoreValueWorkersActiveCount',77,4),('m_scoreValueMineralsUsedInProgressArmy',77,5),('m_scoreValueMineralsUsedInProgressEconomy',77,6),('m_scoreValueMineralsUsedInProgressTechnology',77,7),('m_scoreValueVespeneUsedInProgressArmy',77,8),('m_scoreValueVespeneUsedInProgressEconomy',77,9),('m_scoreValueVespeneUsedInProgressTechnology',77,10),('m_scoreValueMineralsUsedCurrentArmy',77,11),('m_scoreValueMineralsUsedCurrentEconomy',77,12),('m_scoreValueMineralsUsedCurrentTechnology',77,13),('m_scoreValueVespeneUsedCurrentArmy',77,14),('m_scoreValueVespeneUsedCurrentEconomy',77,15),('m_scoreValueVespeneUsedCurrentTechnology',77,16),('m_scoreValueMineralsLostArmy',77,17),('m_scoreValueMineralsLostEconomy',77,18),('m_scoreValueMineralsLostTechnology',77,19),('m_scoreValueVespeneLostArmy',77,20),('m_scoreValueVespeneLostEconomy',77,21),('m_scoreValueVespeneLostTechnology',77,22),('m_scoreValueMineralsKilledArmy',77,23),('m_scoreValueMineralsKilledEconomy',77,24),('m_scoreValueMineralsKilledTechnology',77,25),('m_scoreValueVespeneKilledArmy',77,26),('m_scoreValueVespeneKilledEconomy',77,27),('m_scoreValueVespeneKilledTechnology',77,28),('m_scoreValueFoodUsed',77,29),('m_scoreValueFoodMade',77,30),('m_scoreValueMineralsUsedActiveForces',77,31),('m_scoreValueVespeneUsedActiveForces',77,32),('m_scoreValueMineralsFriendlyFireArmy',77,33),('m_scoreValueMineralsFriendlyFireEconomy',77,34),('m_scoreValueMineralsFriendlyFireTechnology',77,35),('m_scoreValueVespeneFriendlyFireArmy',77,36),('m_scoreValueVespeneFriendlyFireEconomy',77,37),('m_scoreValueVespeneFriendlyFireTechnology',77,38)]]),  #167
    ('_struct',[[('m_playerId',1,0),('m_stats',167,1)]]),  #168
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2),('m_controlPlayerId',1,3),('m_upkeepPlayerId',1,4),('m_x',10,5),('m_y',10,6)]]),  #169
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_killerPlayerId',54,2),('m_x',10,3),('m_y',10,4),('m_killerUnitTagIndex',39,5),('m_killerUnitTagRecycle',39,6)]]),  #170
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_controlPlayerId',1,2),('m_upkeepPlayerId',1,3)]]),  #171
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2)]]),  #172
    ('_struct',[[('m_playerId',1,0),('m_upgradeTypeName',25,1),('m_count',77,2)]]),  #173
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1)]]),  #174
    ('_array',[(0,10),77]),  #175
    ('_struct',[[('m_firstUnitIndex',6,0),('m_items',175,1)]]),  #176
    ('_struct',[[('m_playerId',1,0),('m_type',6,1),('m_userId',39,2),('m_slotId',39,3)]]),  #177
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (72, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (71, 'NNet.Game.SUserOptionsEvent'),
    9: (64, 'NNet.Game.SBankFileEvent'),
    10: (66, 'NNet.Game.SBankSectionEvent'),
    11: (67, 'NNet.Game.SBankKeyEvent'),
    12: (68, 'NNet.Game.SBankValueEvent'),
    13: (70, 'NNet.Game.SBankSignatureEvent'),
    14: (75, 'NNet.Game.SCameraSaveEvent'),
    21: (76, 'NNet.Game.SSaveGameEvent'),
    22: (72, 'NNet.Game.SSaveGameDoneEvent'),
    23: (72, 'NNet.Game.SLoadGameDoneEvent'),
    26: (80, 'NNet.Game.SGameCheatEvent'),
    27: (88, 'NNet.Game.SCmdEvent'),
    28: (96, 'NNet.Game.SSelectionDeltaEvent'),
    29: (97, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (99, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (101, 'NNet.Game.SResourceTradeEvent'),
    32: (102, 'NNet.Game.STriggerChatMessageEvent'),
    33: (105, 'NNet.Game.SAICommunicateEvent'),
    34: (106, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (107, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (108, 'NNet.Game.STriggerPingEvent'),
    37: (109, 'NNet.Game.SBroadcastCheatEvent'),
    38: (110, 'NNet.Game.SAllianceEvent'),
    39: (111, 'NNet.Game.SUnitClickEvent'),
    40: (112, 'NNet.Game.SUnitHighlightEvent'),
    41: (113, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (118, 'NNet.Game.SHijackReplayGameEvent'),
    44: (72, 'NNet.Game.STriggerSkippedEvent'),
    45: (123, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (127, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (128, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (129, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (133, 'NNet.Game.SCameraUpdateEvent'),
    50: (72, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (119, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (72, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (120, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (72, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (122, 'NNet.Game.STriggerDialogControlEvent'),
    56: (126, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (134, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (137, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (138, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (139, 'NNet.Game.SAchievementAwardedEvent'),
    62: (140, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (72, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (141, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (142, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (143, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (154, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (72, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (72, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (144, 'NNet.Game.SResourceRequestEvent'),
    71: (145, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (146, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (72, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (72, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (147, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (72, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (72, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (148, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (72, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (72, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (149, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (150, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (150, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (120, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (72, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (72, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (152, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (153, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (155, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (156, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    93: (119, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (157, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (158, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (72, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (159, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (160, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (161, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (162, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (72, 'NNet.Game.SGameUserLeaveEvent'),
    102: (163, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (164, 'NNet.Game.SChatMessage'),
    1: (165, 'NNet.Game.SPingMessage'),
    2: (166, 'NNet.Game.SLoadingProgressMessage'),
    3: (72, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# Map from protocol NNet.Replay.Tracker.*Event eventid to (typeid, name)
tracker_event_types = {
    0: (168, 'NNet.Replay.Tracker.SPlayerStatsEvent'),
    1: (169, 'NNet.Replay.Tracker.SUnitBornEvent'),
    2: (170, 'NNet.Replay.Tracker.SUnitDiedEvent'),
    3: (171, 'NNet.Replay.Tracker.SUnitOwnerChangeEvent'),
    4: (172, 'NNet.Replay.Tracker.SUnitTypeChangeEvent'),
    5: (173, 'NNet.Replay.Tracker.SUpgradeEvent'),
    6: (169, 'NNet.Replay.Tracker.SUnitInitEvent'),
    7: (174, 'NNet.Replay.Tracker.SUnitDoneEvent'),
    8: (176, 'NNet.Replay.Tracker.SUnitPositionsEvent'),
    9: (177, 'NNet.Replay.Tracker.SPlayerSetupEvent'),
}

# The typeid of the NNet.Replay.Tracker.EEventId enum.
tracker_eventid_typeid = 2

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 7

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 14

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 36

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 63


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_tracker_events(contents):
    """Decodes and yields each tracker event from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      tracker_eventid_typeid,
                                      tracker_event_types,
                                      decode_user_id=False):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = protocol28667
# Copyright (c) 2013 Blizzard Entertainment
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

from decoders import *


# Decoding instructions for each protocol type.
typeinfos = [
    ('_int',[(0,7)]),  #0
    ('_int',[(0,4)]),  #1
    ('_int',[(0,5)]),  #2
    ('_int',[(0,6)]),  #3
    ('_int',[(0,14)]),  #4
    ('_int',[(0,22)]),  #5
    ('_int',[(0,32)]),  #6
    ('_choice',[(0,2),{0:('m_uint6',3),1:('m_uint14',4),2:('m_uint22',5),3:('m_uint32',6)}]),  #7
    ('_struct',[[('m_userId',2,-1)]]),  #8
    ('_blob',[(0,8)]),  #9
    ('_int',[(0,8)]),  #10
    ('_struct',[[('m_flags',10,0),('m_major',10,1),('m_minor',10,2),('m_revision',10,3),('m_build',6,4),('m_baseBuild',6,5)]]),  #11
    ('_int',[(0,3)]),  #12
    ('_bool',[]),  #13
    ('_struct',[[('m_signature',9,0),('m_version',11,1),('m_type',12,2),('m_elapsedGameLoops',6,3),('m_useScaledTime',13,4)]]),  #14
    ('_fourcc',[]),  #15
    ('_blob',[(0,7)]),  #16
    ('_int',[(0,64)]),  #17
    ('_struct',[[('m_region',10,0),('m_programId',15,1),('m_realm',6,2),('m_name',16,3),('m_id',17,4)]]),  #18
    ('_struct',[[('m_a',10,0),('m_r',10,1),('m_g',10,2),('m_b',10,3)]]),  #19
    ('_int',[(0,2)]),  #20
    ('_optional',[10]),  #21
    ('_struct',[[('m_name',9,0),('m_toon',18,1),('m_race',9,2),('m_color',19,3),('m_control',10,4),('m_teamId',1,5),('m_handicap',0,6),('m_observe',20,7),('m_result',20,8),('m_workingSetSlotId',21,9)]]),  #22
    ('_array',[(0,5),22]),  #23
    ('_optional',[23]),  #24
    ('_blob',[(0,10)]),  #25
    ('_blob',[(0,11)]),  #26
    ('_struct',[[('m_file',26,0)]]),  #27
    ('_optional',[13]),  #28
    ('_int',[(-9223372036854775808,64)]),  #29
    ('_blob',[(0,12)]),  #30
    ('_blob',[(40,0)]),  #31
    ('_array',[(0,6),31]),  #32
    ('_optional',[32]),  #33
    ('_array',[(0,6),26]),  #34
    ('_optional',[34]),  #35
    ('_struct',[[('m_playerList',24,0),('m_title',25,1),('m_difficulty',9,2),('m_thumbnail',27,3),('m_isBlizzardMap',13,4),('m_restartAsTransitionMap',28,16),('m_timeUTC',29,5),('m_timeLocalOffset',29,6),('m_description',30,7),('m_imageFilePath',26,8),('m_campaignIndex',10,15),('m_mapFileName',26,9),('m_cacheHandles',33,10),('m_miniSave',13,11),('m_gameSpeed',12,12),('m_defaultDifficulty',3,13),('m_modPaths',35,14)]]),  #36
    ('_optional',[9]),  #37
    ('_optional',[31]),  #38
    ('_optional',[6]),  #39
    ('_struct',[[('m_race',21,-1)]]),  #40
    ('_struct',[[('m_team',21,-1)]]),  #41
    ('_struct',[[('m_name',9,-13),('m_clanTag',37,-12),('m_clanLogo',38,-11),('m_highestLeague',21,-10),('m_combinedRaceLevels',39,-9),('m_randomSeed',6,-8),('m_racePreference',40,-7),('m_teamPreference',41,-6),('m_testMap',13,-5),('m_testAuto',13,-4),('m_examine',13,-3),('m_customInterface',13,-2),('m_observe',20,-1)]]),  #42
    ('_array',[(0,5),42]),  #43
    ('_struct',[[('m_lockTeams',13,-12),('m_teamsTogether',13,-11),('m_advancedSharedControl',13,-10),('m_randomRaces',13,-9),('m_battleNet',13,-8),('m_amm',13,-7),('m_competitive',13,-6),('m_noVictoryOrDefeat',13,-5),('m_fog',20,-4),('m_observers',20,-3),('m_userDifficulty',20,-2),('m_clientDebugFlags',17,-1)]]),  #44
    ('_int',[(1,4)]),  #45
    ('_int',[(1,8)]),  #46
    ('_bitarray',[(0,6)]),  #47
    ('_bitarray',[(0,8)]),  #48
    ('_bitarray',[(0,2)]),  #49
    ('_bitarray',[(0,7)]),  #50
    ('_struct',[[('m_allowedColors',47,-6),('m_allowedRaces',48,-5),('m_allowedDifficulty',47,-4),('m_allowedControls',48,-3),('m_allowedObserveTypes',49,-2),('m_allowedAIBuilds',50,-1)]]),  #51
    ('_array',[(0,5),51]),  #52
    ('_struct',[[('m_randomValue',6,-26),('m_gameCacheName',25,-25),('m_gameOptions',44,-24),('m_gameSpeed',12,-23),('m_gameType',12,-22),('m_maxUsers',2,-21),('m_maxObservers',2,-20),('m_maxPlayers',2,-19),('m_maxTeams',45,-18),('m_maxColors',3,-17),('m_maxRaces',46,-16),('m_maxControls',10,-15),('m_mapSizeX',10,-14),('m_mapSizeY',10,-13),('m_mapFileSyncChecksum',6,-12),('m_mapFileName',26,-11),('m_mapAuthorName',9,-10),('m_modFileSyncChecksum',6,-9),('m_slotDescriptions',52,-8),('m_defaultDifficulty',3,-7),('m_defaultAIBuild',0,-6),('m_cacheHandles',32,-5),('m_hasExtensionMod',13,-4),('m_isBlizzardMap',13,-3),('m_isPremadeFFA',13,-2),('m_isCoopMode',13,-1)]]),  #53
    ('_optional',[1]),  #54
    ('_optional',[2]),  #55
    ('_struct',[[('m_color',55,-1)]]),  #56
    ('_array',[(0,6),6]),  #57
    ('_array',[(0,9),6]),  #58
    ('_struct',[[('m_control',10,-13),('m_userId',54,-12),('m_teamId',1,-11),('m_colorPref',56,-10),('m_racePref',40,-9),('m_difficulty',3,-8),('m_aiBuild',0,-7),('m_handicap',0,-6),('m_observe',20,-5),('m_workingSetSlotId',21,-4),('m_rewards',57,-3),('m_toonHandle',16,-2),('m_licenses',58,-1)]]),  #59
    ('_array',[(0,5),59]),  #60
    ('_struct',[[('m_phase',12,-10),('m_maxUsers',2,-9),('m_maxObservers',2,-8),('m_slots',60,-7),('m_randomSeed',6,-6),('m_hostUserId',54,-5),('m_isSinglePlayer',13,-4),('m_gameDuration',6,-3),('m_defaultDifficulty',3,-2),('m_defaultAIBuild',0,-1)]]),  #61
    ('_struct',[[('m_userInitialData',43,-3),('m_gameDescription',53,-2),('m_lobbyState',61,-1)]]),  #62
    ('_struct',[[('m_syncLobbyState',62,-1)]]),  #63
    ('_struct',[[('m_name',16,-1)]]),  #64
    ('_blob',[(0,6)]),  #65
    ('_struct',[[('m_name',65,-1)]]),  #66
    ('_struct',[[('m_name',65,-3),('m_type',6,-2),('m_data',16,-1)]]),  #67
    ('_struct',[[('m_type',6,-3),('m_name',65,-2),('m_data',30,-1)]]),  #68
    ('_array',[(0,5),10]),  #69
    ('_struct',[[('m_signature',69,-2),('m_toonHandle',16,-1)]]),  #70
    ('_struct',[[('m_gameFullyDownloaded',13,-8),('m_developmentCheatsEnabled',13,-7),('m_multiplayerCheatsEnabled',13,-6),('m_syncChecksummingEnabled',13,-5),('m_isMapToMapTransition',13,-4),('m_startingRally',13,-3),('m_debugPauseEnabled',13,-2),('m_baseBuildNum',6,-1)]]),  #71
    ('_struct',[[]]),  #72
    ('_int',[(0,16)]),  #73
    ('_struct',[[('x',73,-2),('y',73,-1)]]),  #74
    ('_struct',[[('m_which',12,-2),('m_target',74,-1)]]),  #75
    ('_struct',[[('m_fileName',26,-5),('m_automatic',13,-4),('m_overwrite',13,-3),('m_name',9,-2),('m_description',25,-1)]]),  #76
    ('_int',[(-2147483648,32)]),  #77
    ('_struct',[[('x',77,-2),('y',77,-1)]]),  #78
    ('_struct',[[('m_point',78,-4),('m_time',77,-3),('m_verb',25,-2),('m_arguments',25,-1)]]),  #79
    ('_struct',[[('m_data',79,-1)]]),  #80
    ('_int',[(0,20)]),  #81
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_abilCmdData',21,-1)]]),  #82
    ('_optional',[82]),  #83
    ('_null',[]),  #84
    ('_struct',[[('x',81,-3),('y',81,-2),('z',77,-1)]]),  #85
    ('_struct',[[('m_targetUnitFlags',10,-7),('m_timer',10,-6),('m_tag',6,-5),('m_snapshotUnitLink',73,-4),('m_snapshotControlPlayerId',54,-3),('m_snapshotUpkeepPlayerId',54,-2),('m_snapshotPoint',85,-1)]]),  #86
    ('_choice',[(0,2),{0:('None',84),1:('TargetPoint',85),2:('TargetUnit',86),3:('Data',6)}]),  #87
    ('_struct',[[('m_cmdFlags',81,-4),('m_abil',83,-3),('m_data',87,-2),('m_otherUnit',39,-1)]]),  #88
    ('_int',[(0,9)]),  #89
    ('_bitarray',[(0,9)]),  #90
    ('_array',[(0,9),89]),  #91
    ('_choice',[(0,2),{0:('None',84),1:('Mask',90),2:('OneIndices',91),3:('ZeroIndices',91)}]),  #92
    ('_struct',[[('m_unitLink',73,-4),('m_subgroupPriority',10,-3),('m_intraSubgroupPriority',10,-2),('m_count',89,-1)]]),  #93
    ('_array',[(0,9),93]),  #94
    ('_struct',[[('m_subgroupIndex',89,-4),('m_removeMask',92,-3),('m_addSubgroups',94,-2),('m_addUnitTags',58,-1)]]),  #95
    ('_struct',[[('m_controlGroupId',1,-2),('m_delta',95,-1)]]),  #96
    ('_struct',[[('m_controlGroupIndex',1,-3),('m_controlGroupUpdate',20,-2),('m_mask',92,-1)]]),  #97
    ('_struct',[[('m_count',89,-6),('m_subgroupCount',89,-5),('m_activeSubgroupIndex',89,-4),('m_unitTagsChecksum',6,-3),('m_subgroupIndicesChecksum',6,-2),('m_subgroupsChecksum',6,-1)]]),  #98
    ('_struct',[[('m_controlGroupId',1,-2),('m_selectionSyncData',98,-1)]]),  #99
    ('_array',[(0,3),77]),  #100
    ('_struct',[[('m_recipientId',1,-2),('m_resources',100,-1)]]),  #101
    ('_struct',[[('m_chatMessage',25,-1)]]),  #102
    ('_int',[(-128,8)]),  #103
    ('_struct',[[('x',77,-3),('y',77,-2),('z',77,-1)]]),  #104
    ('_struct',[[('m_beacon',103,-9),('m_ally',103,-8),('m_flags',103,-7),('m_build',103,-6),('m_targetUnitTag',6,-5),('m_targetUnitSnapshotUnitLink',73,-4),('m_targetUnitSnapshotUpkeepPlayerId',103,-3),('m_targetUnitSnapshotControlPlayerId',103,-2),('m_targetPoint',104,-1)]]),  #105
    ('_struct',[[('m_speed',12,-1)]]),  #106
    ('_struct',[[('m_delta',103,-1)]]),  #107
    ('_struct',[[('m_point',78,-3),('m_unit',6,-2),('m_pingedMinimap',13,-1)]]),  #108
    ('_struct',[[('m_verb',25,-2),('m_arguments',25,-1)]]),  #109
    ('_struct',[[('m_alliance',6,-2),('m_control',6,-1)]]),  #110
    ('_struct',[[('m_unitTag',6,-1)]]),  #111
    ('_struct',[[('m_unitTag',6,-2),('m_flags',10,-1)]]),  #112
    ('_struct',[[('m_conversationId',77,-2),('m_replyId',77,-1)]]),  #113
    ('_optional',[16]),  #114
    ('_struct',[[('m_gameUserId',1,-6),('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #115
    ('_array',[(0,5),115]),  #116
    ('_int',[(0,1)]),  #117
    ('_struct',[[('m_userInfos',116,-2),('m_method',117,-1)]]),  #118
    ('_struct',[[('m_purchaseItemId',77,-1)]]),  #119
    ('_struct',[[('m_difficultyLevel',77,-1)]]),  #120
    ('_choice',[(0,3),{0:('None',84),1:('Checked',13),2:('ValueChanged',6),3:('SelectionChanged',77),4:('TextChanged',26),5:('MouseButton',6)}]),  #121
    ('_struct',[[('m_controlId',77,-3),('m_eventType',77,-2),('m_eventData',121,-1)]]),  #122
    ('_struct',[[('m_soundHash',6,-2),('m_length',6,-1)]]),  #123
    ('_array',[(0,7),6]),  #124
    ('_struct',[[('m_soundHash',124,-2),('m_length',124,-1)]]),  #125
    ('_struct',[[('m_syncInfo',125,-1)]]),  #126
    ('_struct',[[('m_sound',6,-1)]]),  #127
    ('_struct',[[('m_transmissionId',77,-2),('m_thread',6,-1)]]),  #128
    ('_struct',[[('m_transmissionId',77,-1)]]),  #129
    ('_optional',[74]),  #130
    ('_optional',[73]),  #131
    ('_optional',[103]),  #132
    ('_struct',[[('m_target',130,-5),('m_distance',131,-4),('m_pitch',131,-3),('m_yaw',131,-2),('m_reason',132,-1)]]),  #133
    ('_struct',[[('m_skipType',117,-1)]]),  #134
    ('_int',[(0,11)]),  #135
    ('_struct',[[('x',135,-2),('y',135,-1)]]),  #136
    ('_struct',[[('m_button',6,-5),('m_down',13,-4),('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #137
    ('_struct',[[('m_posUI',136,-3),('m_posWorld',85,-2),('m_flags',103,-1)]]),  #138
    ('_struct',[[('m_achievementLink',73,-1)]]),  #139
    ('_struct',[[('m_abilLink',73,-3),('m_abilCmdIndex',2,-2),('m_state',103,-1)]]),  #140
    ('_struct',[[('m_soundtrack',6,-1)]]),  #141
    ('_struct',[[('m_planetId',77,-1)]]),  #142
    ('_struct',[[('m_key',103,-2),('m_flags',103,-1)]]),  #143
    ('_struct',[[('m_resources',100,-1)]]),  #144
    ('_struct',[[('m_fulfillRequestId',77,-1)]]),  #145
    ('_struct',[[('m_cancelRequestId',77,-1)]]),  #146
    ('_struct',[[('m_researchItemId',77,-1)]]),  #147
    ('_struct',[[('m_mercenaryId',77,-1)]]),  #148
    ('_struct',[[('m_battleReportId',77,-2),('m_difficultyLevel',77,-1)]]),  #149
    ('_struct',[[('m_battleReportId',77,-1)]]),  #150
    ('_int',[(0,19)]),  #151
    ('_struct',[[('m_decrementMs',151,-1)]]),  #152
    ('_struct',[[('m_portraitId',77,-1)]]),  #153
    ('_struct',[[('m_functionName',16,-1)]]),  #154
    ('_struct',[[('m_result',77,-1)]]),  #155
    ('_struct',[[('m_gameMenuItemIndex',77,-1)]]),  #156
    ('_struct',[[('m_purchaseCategoryId',77,-1)]]),  #157
    ('_struct',[[('m_button',73,-1)]]),  #158
    ('_struct',[[('m_cutsceneId',77,-2),('m_bookmarkName',16,-1)]]),  #159
    ('_struct',[[('m_cutsceneId',77,-1)]]),  #160
    ('_struct',[[('m_cutsceneId',77,-3),('m_conversationLine',16,-2),('m_altConversationLine',16,-1)]]),  #161
    ('_struct',[[('m_cutsceneId',77,-2),('m_conversationLine',16,-1)]]),  #162
    ('_struct',[[('m_observe',20,-5),('m_name',9,-4),('m_toonHandle',114,-3),('m_clanTag',37,-2),('m_clanLogo',38,-1)]]),  #163
    ('_struct',[[('m_recipient',12,-2),('m_string',26,-1)]]),  #164
    ('_struct',[[('m_recipient',12,-2),('m_point',78,-1)]]),  #165
    ('_struct',[[('m_progress',77,-1)]]),  #166
    ('_struct',[[('m_scoreValueMineralsCurrent',77,0),('m_scoreValueVespeneCurrent',77,1),('m_scoreValueMineralsCollectionRate',77,2),('m_scoreValueVespeneCollectionRate',77,3),('m_scoreValueWorkersActiveCount',77,4),('m_scoreValueMineralsUsedInProgressArmy',77,5),('m_scoreValueMineralsUsedInProgressEconomy',77,6),('m_scoreValueMineralsUsedInProgressTechnology',77,7),('m_scoreValueVespeneUsedInProgressArmy',77,8),('m_scoreValueVespeneUsedInProgressEconomy',77,9),('m_scoreValueVespeneUsedInProgressTechnology',77,10),('m_scoreValueMineralsUsedCurrentArmy',77,11),('m_scoreValueMineralsUsedCurrentEconomy',77,12),('m_scoreValueMineralsUsedCurrentTechnology',77,13),('m_scoreValueVespeneUsedCurrentArmy',77,14),('m_scoreValueVespeneUsedCurrentEconomy',77,15),('m_scoreValueVespeneUsedCurrentTechnology',77,16),('m_scoreValueMineralsLostArmy',77,17),('m_scoreValueMineralsLostEconomy',77,18),('m_scoreValueMineralsLostTechnology',77,19),('m_scoreValueVespeneLostArmy',77,20),('m_scoreValueVespeneLostEconomy',77,21),('m_scoreValueVespeneLostTechnology',77,22),('m_scoreValueMineralsKilledArmy',77,23),('m_scoreValueMineralsKilledEconomy',77,24),('m_scoreValueMineralsKilledTechnology',77,25),('m_scoreValueVespeneKilledArmy',77,26),('m_scoreValueVespeneKilledEconomy',77,27),('m_scoreValueVespeneKilledTechnology',77,28),('m_scoreValueFoodUsed',77,29),('m_scoreValueFoodMade',77,30),('m_scoreValueMineralsUsedActiveForces',77,31),('m_scoreValueVespeneUsedActiveForces',77,32),('m_scoreValueMineralsFriendlyFireArmy',77,33),('m_scoreValueMineralsFriendlyFireEconomy',77,34),('m_scoreValueMineralsFriendlyFireTechnology',77,35),('m_scoreValueVespeneFriendlyFireArmy',77,36),('m_scoreValueVespeneFriendlyFireEconomy',77,37),('m_scoreValueVespeneFriendlyFireTechnology',77,38)]]),  #167
    ('_struct',[[('m_playerId',1,0),('m_stats',167,1)]]),  #168
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2),('m_controlPlayerId',1,3),('m_upkeepPlayerId',1,4),('m_x',10,5),('m_y',10,6)]]),  #169
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_killerPlayerId',54,2),('m_x',10,3),('m_y',10,4),('m_killerUnitTagIndex',39,5),('m_killerUnitTagRecycle',39,6)]]),  #170
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_controlPlayerId',1,2),('m_upkeepPlayerId',1,3)]]),  #171
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1),('m_unitTypeName',25,2)]]),  #172
    ('_struct',[[('m_playerId',1,0),('m_upgradeTypeName',25,1),('m_count',77,2)]]),  #173
    ('_struct',[[('m_unitTagIndex',6,0),('m_unitTagRecycle',6,1)]]),  #174
    ('_array',[(0,10),77]),  #175
    ('_struct',[[('m_firstUnitIndex',6,0),('m_items',175,1)]]),  #176
    ('_struct',[[('m_playerId',1,0),('m_type',6,1),('m_userId',39,2),('m_slotId',39,3)]]),  #177
]

# Map from protocol NNet.Game.*Event eventid to (typeid, name)
game_event_types = {
    5: (72, 'NNet.Game.SUserFinishedLoadingSyncEvent'),
    7: (71, 'NNet.Game.SUserOptionsEvent'),
    9: (64, 'NNet.Game.SBankFileEvent'),
    10: (66, 'NNet.Game.SBankSectionEvent'),
    11: (67, 'NNet.Game.SBankKeyEvent'),
    12: (68, 'NNet.Game.SBankValueEvent'),
    13: (70, 'NNet.Game.SBankSignatureEvent'),
    14: (75, 'NNet.Game.SCameraSaveEvent'),
    21: (76, 'NNet.Game.SSaveGameEvent'),
    22: (72, 'NNet.Game.SSaveGameDoneEvent'),
    23: (72, 'NNet.Game.SLoadGameDoneEvent'),
    26: (80, 'NNet.Game.SGameCheatEvent'),
    27: (88, 'NNet.Game.SCmdEvent'),
    28: (96, 'NNet.Game.SSelectionDeltaEvent'),
    29: (97, 'NNet.Game.SControlGroupUpdateEvent'),
    30: (99, 'NNet.Game.SSelectionSyncCheckEvent'),
    31: (101, 'NNet.Game.SResourceTradeEvent'),
    32: (102, 'NNet.Game.STriggerChatMessageEvent'),
    33: (105, 'NNet.Game.SAICommunicateEvent'),
    34: (106, 'NNet.Game.SSetAbsoluteGameSpeedEvent'),
    35: (107, 'NNet.Game.SAddAbsoluteGameSpeedEvent'),
    36: (108, 'NNet.Game.STriggerPingEvent'),
    37: (109, 'NNet.Game.SBroadcastCheatEvent'),
    38: (110, 'NNet.Game.SAllianceEvent'),
    39: (111, 'NNet.Game.SUnitClickEvent'),
    40: (112, 'NNet.Game.SUnitHighlightEvent'),
    41: (113, 'NNet.Game.STriggerReplySelectedEvent'),
    43: (118, 'NNet.Game.SHijackReplayGameEvent'),
    44: (72, 'NNet.Game.STriggerSkippedEvent'),
    45: (123, 'NNet.Game.STriggerSoundLengthQueryEvent'),
    46: (127, 'NNet.Game.STriggerSoundOffsetEvent'),
    47: (128, 'NNet.Game.STriggerTransmissionOffsetEvent'),
    48: (129, 'NNet.Game.STriggerTransmissionCompleteEvent'),
    49: (133, 'NNet.Game.SCameraUpdateEvent'),
    50: (72, 'NNet.Game.STriggerAbortMissionEvent'),
    51: (119, 'NNet.Game.STriggerPurchaseMadeEvent'),
    52: (72, 'NNet.Game.STriggerPurchaseExitEvent'),
    53: (120, 'NNet.Game.STriggerPlanetMissionLaunchedEvent'),
    54: (72, 'NNet.Game.STriggerPlanetPanelCanceledEvent'),
    55: (122, 'NNet.Game.STriggerDialogControlEvent'),
    56: (126, 'NNet.Game.STriggerSoundLengthSyncEvent'),
    57: (134, 'NNet.Game.STriggerConversationSkippedEvent'),
    58: (137, 'NNet.Game.STriggerMouseClickedEvent'),
    59: (138, 'NNet.Game.STriggerMouseMovedEvent'),
    60: (139, 'NNet.Game.SAchievementAwardedEvent'),
    62: (140, 'NNet.Game.STriggerTargetModeUpdateEvent'),
    63: (72, 'NNet.Game.STriggerPlanetPanelReplayEvent'),
    64: (141, 'NNet.Game.STriggerSoundtrackDoneEvent'),
    65: (142, 'NNet.Game.STriggerPlanetMissionSelectedEvent'),
    66: (143, 'NNet.Game.STriggerKeyPressedEvent'),
    67: (154, 'NNet.Game.STriggerMovieFunctionEvent'),
    68: (72, 'NNet.Game.STriggerPlanetPanelBirthCompleteEvent'),
    69: (72, 'NNet.Game.STriggerPlanetPanelDeathCompleteEvent'),
    70: (144, 'NNet.Game.SResourceRequestEvent'),
    71: (145, 'NNet.Game.SResourceRequestFulfillEvent'),
    72: (146, 'NNet.Game.SResourceRequestCancelEvent'),
    73: (72, 'NNet.Game.STriggerResearchPanelExitEvent'),
    74: (72, 'NNet.Game.STriggerResearchPanelPurchaseEvent'),
    75: (147, 'NNet.Game.STriggerResearchPanelSelectionChangedEvent'),
    77: (72, 'NNet.Game.STriggerMercenaryPanelExitEvent'),
    78: (72, 'NNet.Game.STriggerMercenaryPanelPurchaseEvent'),
    79: (148, 'NNet.Game.STriggerMercenaryPanelSelectionChangedEvent'),
    80: (72, 'NNet.Game.STriggerVictoryPanelExitEvent'),
    81: (72, 'NNet.Game.STriggerBattleReportPanelExitEvent'),
    82: (149, 'NNet.Game.STriggerBattleReportPanelPlayMissionEvent'),
    83: (150, 'NNet.Game.STriggerBattleReportPanelPlaySceneEvent'),
    84: (150, 'NNet.Game.STriggerBattleReportPanelSelectionChangedEvent'),
    85: (120, 'NNet.Game.STriggerVictoryPanelPlayMissionAgainEvent'),
    86: (72, 'NNet.Game.STriggerMovieStartedEvent'),
    87: (72, 'NNet.Game.STriggerMovieFinishedEvent'),
    88: (152, 'NNet.Game.SDecrementGameTimeRemainingEvent'),
    89: (153, 'NNet.Game.STriggerPortraitLoadedEvent'),
    90: (155, 'NNet.Game.STriggerCustomDialogDismissedEvent'),
    91: (156, 'NNet.Game.STriggerGameMenuItemSelectedEvent'),
    93: (119, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseItemChangedEvent'),
    94: (157, 'NNet.Game.STriggerPurchasePanelSelectedPurchaseCategoryChangedEvent'),
    95: (158, 'NNet.Game.STriggerButtonPressedEvent'),
    96: (72, 'NNet.Game.STriggerGameCreditsFinishedEvent'),
    97: (159, 'NNet.Game.STriggerCutsceneBookmarkFiredEvent'),
    98: (160, 'NNet.Game.STriggerCutsceneEndSceneFiredEvent'),
    99: (161, 'NNet.Game.STriggerCutsceneConversationLineEvent'),
    100: (162, 'NNet.Game.STriggerCutsceneConversationLineMissingEvent'),
    101: (72, 'NNet.Game.SGameUserLeaveEvent'),
    102: (163, 'NNet.Game.SGameUserJoinEvent'),
}

# The typeid of the NNet.Game.EEventId enum.
game_eventid_typeid = 0

# Map from protocol NNet.Game.*Message eventid to (typeid, name)
message_event_types = {
    0: (164, 'NNet.Game.SChatMessage'),
    1: (165, 'NNet.Game.SPingMessage'),
    2: (166, 'NNet.Game.SLoadingProgressMessage'),
    3: (72, 'NNet.Game.SServerPingMessage'),
}

# The typeid of the NNet.Game.EMessageId enum.
message_eventid_typeid = 1

# Map from protocol NNet.Replay.Tracker.*Event eventid to (typeid, name)
tracker_event_types = {
    0: (168, 'NNet.Replay.Tracker.SPlayerStatsEvent'),
    1: (169, 'NNet.Replay.Tracker.SUnitBornEvent'),
    2: (170, 'NNet.Replay.Tracker.SUnitDiedEvent'),
    3: (171, 'NNet.Replay.Tracker.SUnitOwnerChangeEvent'),
    4: (172, 'NNet.Replay.Tracker.SUnitTypeChangeEvent'),
    5: (173, 'NNet.Replay.Tracker.SUpgradeEvent'),
    6: (169, 'NNet.Replay.Tracker.SUnitInitEvent'),
    7: (174, 'NNet.Replay.Tracker.SUnitDoneEvent'),
    8: (176, 'NNet.Replay.Tracker.SUnitPositionsEvent'),
    9: (177, 'NNet.Replay.Tracker.SPlayerSetupEvent'),
}

# The typeid of the NNet.Replay.Tracker.EEventId enum.
tracker_eventid_typeid = 2

# The typeid of NNet.SVarUint32 (the type used to encode gameloop deltas).
svaruint32_typeid = 7

# The typeid of NNet.Replay.SGameUserId (the type used to encode player ids).
replay_userid_typeid = 8

# The typeid of NNet.Replay.SHeader (the type used to store replay game version and length).
replay_header_typeid = 14

# The typeid of NNet.Game.SDetails (the type used to store overall replay details).
game_details_typeid = 36

# The typeid of NNet.Replay.SInitData (the type used to store the inital lobby).
replay_initdata_typeid = 63


def _varuint32_value(value):
    # Returns the numeric value from a SVarUint32 instance.
    for k,v in value.iteritems():
        return v
    return 0


def _decode_event_stream(decoder, eventid_typeid, event_types, decode_user_id):
    # Decodes events prefixed with a gameloop and possibly userid
    gameloop = 0
    while not decoder.done():
        start_bits = decoder.used_bits()

        # decode the gameloop delta before each event
        delta = _varuint32_value(decoder.instance(svaruint32_typeid))
        gameloop += delta

        # decode the userid before each event
        if decode_user_id:
            userid = decoder.instance(replay_userid_typeid)

        # decode the event id
        eventid = decoder.instance(eventid_typeid)
        typeid, typename = event_types.get(eventid, (None, None))
        if typeid is None:
            raise CorruptedError('eventid(%d) at %s' % (eventid, decoder))

        # decode the event struct instance
        event = decoder.instance(typeid)
        event['_event'] = typename
        event['_eventid'] = eventid

        #  insert gameloop and userid
        event['_gameloop'] = gameloop
        if decode_user_id:
            event['_userid'] = userid

        # the next event is byte aligned
        decoder.byte_align()

        # insert bits used in stream
        event['_bits'] = decoder.used_bits() - start_bits

        yield event


def decode_replay_game_events(contents):
    """Decodes and yields each game event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      game_eventid_typeid,
                                      game_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_message_events(contents):
    """Decodes and yields each message event from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      message_eventid_typeid,
                                      message_event_types,
                                      decode_user_id=True):
        yield event


def decode_replay_tracker_events(contents):
    """Decodes and yields each tracker event from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    for event in _decode_event_stream(decoder,
                                      tracker_eventid_typeid,
                                      tracker_event_types,
                                      decode_user_id=False):
        yield event


def decode_replay_header(contents):
    """Decodes and return the replay header from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(replay_header_typeid)


def decode_replay_details(contents):
    """Decodes and returns the game details from the contents byte string."""
    decoder = VersionedDecoder(contents, typeinfos)
    return decoder.instance(game_details_typeid)


def decode_replay_initdata(contents):
    """Decodes and return the replay init data from the contents byte string."""
    decoder = BitPackedDecoder(contents, typeinfos)
    return decoder.instance(replay_initdata_typeid)


def decode_replay_attributes_events(contents):
    """Decodes and yields each attribute from the contents byte string."""
    buffer = BitPackedBuffer(contents, 'little')
    attributes = {}
    if not buffer.done():
        attributes['source'] = buffer.read_bits(8)
        attributes['mapNamespace'] = buffer.read_bits(32)
        count = buffer.read_bits(32)
        attributes['scopes'] = {}
        while not buffer.done():
            value = {}
            value['namespace'] = buffer.read_bits(32)
            value['attrid'] = attrid = buffer.read_bits(32)
            scope = buffer.read_bits(8)
            value['value'] = buffer.read_aligned_bytes(4)[::-1].strip('\x00')
            if not scope in attributes['scopes']:
                attributes['scopes'][scope] = {}
            if not attrid in attributes['scopes'][scope]:
                attributes['scopes'][scope][attrid] = []
            attributes['scopes'][scope][attrid].append(value)
    return attributes


def unit_tag(unitTagIndex, unitTagRecycle):
    return (unitTagIndex << 18) + unitTagRecycle


def unit_tag_index(unitTag):
    return (unitTag >> 18) & 0x00003fff


def unit_tag_recycle(unitTag):
    return (unitTag) & 0x0003ffff

########NEW FILE########
__FILENAME__ = s2protocol
#!/usr/bin/env python
#
# Copyright (c) 2013 Blizzard Entertainment
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

import sys
import argparse
import pprint

from mpyq import mpyq
import protocol15405


class EventLogger:
    def __init__(self):
        self._event_stats = {}
        
    def log(self, output, event):
        # update stats
        if '_event' in event and '_bits' in event:
            stat = self._event_stats.get(event['_event'], [0, 0])
            stat[0] += 1  # count of events
            stat[1] += event['_bits']  # count of bits
            self._event_stats[event['_event']] = stat
        # write structure
        pprint.pprint(event, stream=output)
        
    def log_stats(self, output):
        for name, stat in sorted(self._event_stats.iteritems(), key=lambda x: x[1][1]):
            print >> output, '"%s", %d, %d,' % (name, stat[0], stat[1] / 8)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('replay_file', help='.SC2Replay file to load')
    parser.add_argument("--gameevents", help="print game events",
                        action="store_true")
    parser.add_argument("--messageevents", help="print message events",
                        action="store_true")
    parser.add_argument("--trackerevents", help="print tracker events",
                        action="store_true")
    parser.add_argument("--attributeevents", help="print attributes events",
                        action="store_true")
    parser.add_argument("--header", help="print protocol header",
                        action="store_true")
    parser.add_argument("--details", help="print protocol details",
                        action="store_true")
    parser.add_argument("--initdata", help="print protocol initdata",
                        action="store_true")
    parser.add_argument("--stats", help="print stats",
                        action="store_true")
    args = parser.parse_args()

    archive = mpyq.MPQArchive(args.replay_file)
    
    logger = EventLogger()

    # Read the protocol header, this can be read with any protocol
    contents = archive.header['user_data_header']['content']
    header = protocol15405.decode_replay_header(contents)
    if args.header:
        logger.log(sys.stdout, header)

    # The header's baseBuild determines which protocol to use
    baseBuild = header['m_version']['m_baseBuild']
    try:
        protocol = __import__('protocol%s' % (baseBuild,))
    except:
        print >> sys.stderr, 'Unsupported base build: %d' % baseBuild
        sys.exit(1)
        
    # Print protocol details
    if args.details:
        contents = archive.read_file('replay.details')
        details = protocol.decode_replay_details(contents)
        logger.log(sys.stdout, details)

    # Print protocol init data
    if args.initdata:
        contents = archive.read_file('replay.initData')
        initdata = protocol.decode_replay_initdata(contents)
        logger.log(sys.stdout, initdata['m_syncLobbyState']['m_gameDescription']['m_cacheHandles'])
        logger.log(sys.stdout, initdata)

    # Print game events and/or game events stats
    if args.gameevents:
        contents = archive.read_file('replay.game.events')
        for event in protocol.decode_replay_game_events(contents):
            logger.log(sys.stdout, event)

    # Print message events
    if args.messageevents:
        contents = archive.read_file('replay.message.events')
        for event in protocol.decode_replay_message_events(contents):
            logger.log(sys.stdout, event)

    # Print tracker events
    if args.trackerevents:
        if hasattr(protocol, 'decode_replay_tracker_events'):
            contents = archive.read_file('replay.tracker.events')
            for event in protocol.decode_replay_tracker_events(contents):
                logger.log(sys.stdout, event)

    # Print attributes events
    if args.attributeevents:
        contents = archive.read_file('replay.attributes.events')
        attributes = protocol.decode_replay_attributes_events(contents)
        logger.log(sys.stdout, attributes)
        
    # Print stats
    if args.stats:
        logger.log_stats(sys.stderr)


########NEW FILE########
