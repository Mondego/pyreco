__FILENAME__ = snappy
#!/usr/bin/env python
#
# Copyright (c) 2011, Andres Moreira <andres@andresmoreira.com>
#               2011, Felipe Cruz <felipecruz@loogica.net>
#               2012, JT Olds <jt@spacemonkey.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the authors nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL ANDRES MOREIRA BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""python-snappy

Python library for the snappy compression library from Google.
Expected usage like:

    import snappy

    compressed = snappy.compress("some data")
    assert "some data" == snappy.uncompress(compressed)

"""

import sys
import struct

try:
    from _snappy import UncompressError, compress, decompress, \
                        isValidCompressed, uncompress, _crc32c
except ImportError:
    from snappy_cffi import UncompressError, compress, decompress, \
                            isValidCompressed, uncompress, _crc32c

_CHUNK_MAX = 65536
_STREAM_TO_STREAM_BLOCK_SIZE = _CHUNK_MAX
_STREAM_IDENTIFIER = b"sNaPpY"
_COMPRESSED_CHUNK = 0x00
_UNCOMPRESSED_CHUNK = 0x01
_IDENTIFIER_CHUNK = 0xff
_RESERVED_UNSKIPPABLE = (0x02, 0x80)  # chunk ranges are [inclusive, exclusive)
_RESERVED_SKIPPABLE = (0x80, 0xff)

# the minimum percent of bytes compression must save to be enabled in automatic
# mode
_COMPRESSION_THRESHOLD = .125

def _masked_crc32c(data):
    # see the framing format specification
    crc = _crc32c(data)
    return (((crc >> 15) | (crc << 17)) + 0xa282ead8) & 0xffffffff

_compress = compress
_uncompress = uncompress


py3k = False
if sys.hexversion > 0x03000000:
    unicode = str
    py3k = True

def compress(data, encoding='utf-8'):
    if isinstance(data, unicode):
        data = data.encode(encoding)

    return _compress(data)

def uncompress(data, decoding=None):
    if isinstance(data, unicode):
        raise UncompressError("It's only possible to uncompress bytes")
    if decoding:
        return _uncompress(data).decode(decoding)
    return _uncompress(data)

decompress = uncompress


class StreamCompressor(object):

    """This class implements the compressor-side of the proposed Snappy framing
    format, found at

        http://code.google.com/p/snappy/source/browse/trunk/framing_format.txt
            ?spec=svn68&r=71

    This class matches the interface found for the zlib module's compression
    objects (see zlib.compressobj), but also provides some additions, such as
    the snappy framing format's ability to intersperse uncompressed data.

    Keep in mind that this compressor object does no buffering for you to
    appropriately size chunks. Every call to StreamCompressor.compress results
    in a unique call to the underlying snappy compression method.
    """

    __slots__ = ["_header_chunk_written"]

    def __init__(self):
        self._header_chunk_written = False

    def add_chunk(self, data, compress=None):
        """Add a chunk containing 'data', returning a string that is framed and
        (optionally, default) compressed. This data should be concatenated to
        the tail end of an existing Snappy stream. In the absence of any
        internal buffering, no data is left in any internal buffers, and so
        unlike zlib.compress, this method returns everything.

        If compress is None, compression is determined automatically based on
        snappy's performance. If compress == True, compression always happens,
        and if compress == False, compression never happens.
        """
        if not self._header_chunk_written:
            self._header_chunk_written = True
            out = [struct.pack("<L", _IDENTIFIER_CHUNK +
                                      (len(_STREAM_IDENTIFIER) << 8)),
                   _STREAM_IDENTIFIER]
        else:
            out = []
        for i in range(0, len(data), _CHUNK_MAX):
            chunk = data[i:i + _CHUNK_MAX]
            crc = _masked_crc32c(chunk)
            if compress is None:
                compressed_chunk = _compress(chunk)
                if (len(compressed_chunk) <=
                        (1 - _COMPRESSION_THRESHOLD) * len(chunk)):
                    chunk = compressed_chunk
                    chunk_type = _COMPRESSED_CHUNK
                else:
                    chunk_type = _UNCOMPRESSED_CHUNK
                compressed_chunk = None
            elif compress:
                chunk = _compress(chunk)
                chunk_type = _COMPRESSED_CHUNK
            else:
                chunk_type = _UNCOMPRESSED_CHUNK
            out.append(struct.pack("<LL", chunk_type + ((len(chunk) + 4) << 8),
                                   crc))
            out.append(chunk)
        return b"".join(out)

    def compress(self, data):
        """This method is simply an alias for compatibility with zlib
        compressobj's compress method.
        """
        return self.add_chunk(data)

    def flush(self, mode=None):
        """This method does nothing and only exists for compatibility with
        the zlib compressobj
        """
        pass

    def copy(self):
        """This method exists for compatibility with the zlib compressobj.
        """
        copy = StreamCompressor()
        copy._header_chunk_written = self._header_chunk_written
        return copy


class StreamDecompressor(object):

    """This class implements the decompressor-side of the proposed Snappy
    framing format, found at

        http://code.google.com/p/snappy/source/browse/trunk/framing_format.txt
            ?spec=svn68&r=71

    This class matches a subset of the interface found for the zlib module's
    decompression objects (see zlib.decompressobj). Specifically, it currently
    implements the decompress method without the max_length option, the flush
    method without the length option, and the copy method.
    """

    __slots__ = ["_buf", "_header_found"]

    def __init__(self):
        self._buf = b""
        self._header_found = False

    def decompress(self, data):
        """Decompress 'data', returning a string containing the uncompressed
        data corresponding to at least part of the data in string. This data
        should be concatenated to the output produced by any preceding calls to
        the decompress() method. Some of the input data may be preserved in
        internal buffers for later processing.
        """
        self._buf += data
        uncompressed = []
        while True:
            if len(self._buf) < 4:
                return b"".join(uncompressed)
            chunk_type = struct.unpack("<L", self._buf[:4])[0]
            size = (chunk_type >> 8)
            chunk_type &= 0xff
            if not self._header_found:
                if (chunk_type != _IDENTIFIER_CHUNK or
                        size != len(_STREAM_IDENTIFIER)):
                    raise UncompressError("stream missing snappy identifier")
                self._header_found = True
            if (_RESERVED_UNSKIPPABLE[0] <= chunk_type and
                    chunk_type < _RESERVED_UNSKIPPABLE[1]):
                raise UncompressError(
                    "stream received unskippable but unknown chunk")
            if len(self._buf) < 4 + size:
                return b"".join(uncompressed)
            chunk, self._buf = self._buf[4:4 + size], self._buf[4 + size:]
            if chunk_type == _IDENTIFIER_CHUNK:
                if chunk != _STREAM_IDENTIFIER:
                    raise UncompressError(
                        "stream has invalid snappy identifier")
                continue
            if (_RESERVED_SKIPPABLE[0] <= chunk_type and
                    chunk_type < _RESERVED_SKIPPABLE[1]):
                continue
            assert chunk_type in (_COMPRESSED_CHUNK, _UNCOMPRESSED_CHUNK)
            crc, chunk = chunk[:4], chunk[4:]
            if chunk_type == _COMPRESSED_CHUNK:
                chunk = _uncompress(chunk)
            if struct.pack("<L", _masked_crc32c(chunk)) != crc:
                raise UncompressError("crc mismatch")
            uncompressed.append(chunk)

    def flush(self):
        """All pending input is processed, and a string containing the
        remaining uncompressed output is returned. After calling flush(), the
        decompress() method cannot be called again; the only realistic action
        is to delete the object.
        """
        if self._buf != b"":
            raise UncompressError("chunk truncated")
        return b""

    def copy(self):
        """Returns a copy of the decompression object. This can be used to save
        the state of the decompressor midway through the data stream in order
        to speed up random seeks into the stream at a future point.
        """
        copy = StreamDecompressor()
        copy._buf, copy._header_found = self._buf, self._header_found
        return copy


def stream_compress(src, dst, blocksize=_STREAM_TO_STREAM_BLOCK_SIZE):
    """Takes an incoming file-like object and an outgoing file-like object,
    reads data from src, compresses it, and writes it to dst. 'src' should
    support the read method, and 'dst' should support the write method.

    The default blocksize is good for almost every scenario.
    """
    compressor = StreamCompressor()
    while True:
        buf = src.read(blocksize)
        if not buf: break
        buf = compressor.add_chunk(buf)
        if buf: dst.write(buf)


def stream_decompress(src, dst, blocksize=_STREAM_TO_STREAM_BLOCK_SIZE):
    """Takes an incoming file-like object and an outgoing file-like object,
    reads data from src, decompresses it, and writes it to dst. 'src' should
    support the read method, and 'dst' should support the write method.

    The default blocksize is good for almost every scenario.
    """
    decompressor = StreamDecompressor()
    while True:
        buf = src.read(blocksize)
        if not buf: break
        buf = decompressor.decompress(buf)
        if buf: dst.write(buf)
    decompressor.flush()  # makes sure the stream ended well


def cmdline_main():
    """This method is what is run when invoking snappy via the commandline.
    Try python -m snappy --help
    """
    import sys
    if (len(sys.argv) < 2 or len(sys.argv) > 4 or "--help" in sys.argv or
            "-h" in sys.argv or sys.argv[1] not in ("-c", "-d")):
        print("Usage: python -m snappy <-c/-d> [src [dst]]")
        print("             -c      compress")
        print("             -d      decompress")
        print("output is stdout if dst is omitted or '-'")
        print("input is stdin if src and dst are omitted or src is '-'.")
        sys.exit(1)

    if len(sys.argv) >= 4 and sys.argv[3] != "-":
        dst = open(sys.argv[3], "wb")
    elif hasattr(sys.stdout, 'buffer'):
        dst = sys.stdout.buffer
    else:
        dst = sys.stdout

    if len(sys.argv) >= 3 and sys.argv[2] != "-":
        src = open(sys.argv[2], "rb")
    elif hasattr(sys.stdin, "buffer"):
        src = sys.stdin.buffer
    else:
        src = sys.stdin

    if sys.argv[1] == "-c":
        method = stream_compress
    else:
        method = stream_decompress

    method(src, dst)


if __name__ == "__main__":
    cmdline_main()

########NEW FILE########
__FILENAME__ = snappy_cffi
import sys

from cffi import FFI

if sys.hexversion > 0x03000000:
    unicode = str

ffi = FFI()

ffi.cdef('''
typedef enum {
  SNAPPY_OK = 0,
  SNAPPY_INVALID_INPUT = 1,
  SNAPPY_BUFFER_TOO_SMALL = 2
} snappy_status;

typedef uint32_t crc_t;

int snappy_compress(const char* input,
                    size_t input_length,
                    char* compressed,
                    size_t* compressed_length);

int snappy_uncompress(const char* compressed,
                      size_t compressed_length,
                      char* uncompressed,
                      size_t* uncompressed_length);

size_t snappy_max_compressed_length(size_t source_length);

int snappy_uncompressed_length(const char* compressed,
                               size_t compressed_length,
                               size_t* result);

int snappy_validate_compressed_buffer(const char* compressed,
                                      size_t compressed_length);

crc_t crc_init(void);

crc_t crc_finalize(crc_t crc);

crc_t crc_reflect(crc_t data, size_t data_len);

crc_t crc_update(crc_t crc, const unsigned char *data, size_t data_len);

crc_t _crc32c(const char *input, int input_size);

''')

C = ffi.verify('''
#include <stdint.h>
#include <stdlib.h>
#include "snappy-c.h"

/*
 * COPY of crc32c
 * This is allowed since all crc code is self contained
 */

typedef uint32_t crc_t;

uint32_t crc_table[256] = {
    0x00000000, 0xf26b8303, 0xe13b70f7, 0x1350f3f4,
    0xc79a971f, 0x35f1141c, 0x26a1e7e8, 0xd4ca64eb,
    0x8ad958cf, 0x78b2dbcc, 0x6be22838, 0x9989ab3b,
    0x4d43cfd0, 0xbf284cd3, 0xac78bf27, 0x5e133c24,
    0x105ec76f, 0xe235446c, 0xf165b798, 0x030e349b,
    0xd7c45070, 0x25afd373, 0x36ff2087, 0xc494a384,
    0x9a879fa0, 0x68ec1ca3, 0x7bbcef57, 0x89d76c54,
    0x5d1d08bf, 0xaf768bbc, 0xbc267848, 0x4e4dfb4b,
    0x20bd8ede, 0xd2d60ddd, 0xc186fe29, 0x33ed7d2a,
    0xe72719c1, 0x154c9ac2, 0x061c6936, 0xf477ea35,
    0xaa64d611, 0x580f5512, 0x4b5fa6e6, 0xb93425e5,
    0x6dfe410e, 0x9f95c20d, 0x8cc531f9, 0x7eaeb2fa,
    0x30e349b1, 0xc288cab2, 0xd1d83946, 0x23b3ba45,
    0xf779deae, 0x05125dad, 0x1642ae59, 0xe4292d5a,
    0xba3a117e, 0x4851927d, 0x5b016189, 0xa96ae28a,
    0x7da08661, 0x8fcb0562, 0x9c9bf696, 0x6ef07595,
    0x417b1dbc, 0xb3109ebf, 0xa0406d4b, 0x522bee48,
    0x86e18aa3, 0x748a09a0, 0x67dafa54, 0x95b17957,
    0xcba24573, 0x39c9c670, 0x2a993584, 0xd8f2b687,
    0x0c38d26c, 0xfe53516f, 0xed03a29b, 0x1f682198,
    0x5125dad3, 0xa34e59d0, 0xb01eaa24, 0x42752927,
    0x96bf4dcc, 0x64d4cecf, 0x77843d3b, 0x85efbe38,
    0xdbfc821c, 0x2997011f, 0x3ac7f2eb, 0xc8ac71e8,
    0x1c661503, 0xee0d9600, 0xfd5d65f4, 0x0f36e6f7,
    0x61c69362, 0x93ad1061, 0x80fde395, 0x72966096,
    0xa65c047d, 0x5437877e, 0x4767748a, 0xb50cf789,
    0xeb1fcbad, 0x197448ae, 0x0a24bb5a, 0xf84f3859,
    0x2c855cb2, 0xdeeedfb1, 0xcdbe2c45, 0x3fd5af46,
    0x7198540d, 0x83f3d70e, 0x90a324fa, 0x62c8a7f9,
    0xb602c312, 0x44694011, 0x5739b3e5, 0xa55230e6,
    0xfb410cc2, 0x092a8fc1, 0x1a7a7c35, 0xe811ff36,
    0x3cdb9bdd, 0xceb018de, 0xdde0eb2a, 0x2f8b6829,
    0x82f63b78, 0x709db87b, 0x63cd4b8f, 0x91a6c88c,
    0x456cac67, 0xb7072f64, 0xa457dc90, 0x563c5f93,
    0x082f63b7, 0xfa44e0b4, 0xe9141340, 0x1b7f9043,
    0xcfb5f4a8, 0x3dde77ab, 0x2e8e845f, 0xdce5075c,
    0x92a8fc17, 0x60c37f14, 0x73938ce0, 0x81f80fe3,
    0x55326b08, 0xa759e80b, 0xb4091bff, 0x466298fc,
    0x1871a4d8, 0xea1a27db, 0xf94ad42f, 0x0b21572c,
    0xdfeb33c7, 0x2d80b0c4, 0x3ed04330, 0xccbbc033,
    0xa24bb5a6, 0x502036a5, 0x4370c551, 0xb11b4652,
    0x65d122b9, 0x97baa1ba, 0x84ea524e, 0x7681d14d,
    0x2892ed69, 0xdaf96e6a, 0xc9a99d9e, 0x3bc21e9d,
    0xef087a76, 0x1d63f975, 0x0e330a81, 0xfc588982,
    0xb21572c9, 0x407ef1ca, 0x532e023e, 0xa145813d,
    0x758fe5d6, 0x87e466d5, 0x94b49521, 0x66df1622,
    0x38cc2a06, 0xcaa7a905, 0xd9f75af1, 0x2b9cd9f2,
    0xff56bd19, 0x0d3d3e1a, 0x1e6dcdee, 0xec064eed,
    0xc38d26c4, 0x31e6a5c7, 0x22b65633, 0xd0ddd530,
    0x0417b1db, 0xf67c32d8, 0xe52cc12c, 0x1747422f,
    0x49547e0b, 0xbb3ffd08, 0xa86f0efc, 0x5a048dff,
    0x8ecee914, 0x7ca56a17, 0x6ff599e3, 0x9d9e1ae0,
    0xd3d3e1ab, 0x21b862a8, 0x32e8915c, 0xc083125f,
    0x144976b4, 0xe622f5b7, 0xf5720643, 0x07198540,
    0x590ab964, 0xab613a67, 0xb831c993, 0x4a5a4a90,
    0x9e902e7b, 0x6cfbad78, 0x7fab5e8c, 0x8dc0dd8f,
    0xe330a81a, 0x115b2b19, 0x020bd8ed, 0xf0605bee,
    0x24aa3f05, 0xd6c1bc06, 0xc5914ff2, 0x37faccf1,
    0x69e9f0d5, 0x9b8273d6, 0x88d28022, 0x7ab90321,
    0xae7367ca, 0x5c18e4c9, 0x4f48173d, 0xbd23943e,
    0xf36e6f75, 0x0105ec76, 0x12551f82, 0xe03e9c81,
    0x34f4f86a, 0xc69f7b69, 0xd5cf889d, 0x27a40b9e,
    0x79b737ba, 0x8bdcb4b9, 0x988c474d, 0x6ae7c44e,
    0xbe2da0a5, 0x4c4623a6, 0x5f16d052, 0xad7d5351
};

crc_t crc_init(void)
{
    return 0xffffffff;
}

crc_t crc_finalize(crc_t crc)
{
    return crc ^ 0xffffffff;
}

crc_t crc_reflect(crc_t data, size_t data_len)
{
    unsigned int i;
    crc_t ret;

    ret = data & 0x01;
    for (i = 1; i < data_len; i++) {
        data >>= 1;
        ret = (ret << 1) | (data & 0x01);
    }
    return ret;
}

crc_t crc_update(crc_t crc, const unsigned char *data, size_t data_len)
{
    unsigned int tbl_idx;

    while (data_len--) {
        tbl_idx = (crc ^ *data) & 0xff;
        crc = (crc_table[tbl_idx] ^ (crc >> 8)) & 0xffffffff;

        data++;
    }
    return crc & 0xffffffff;
}

uint32_t _crc32c(const char *input, int input_size) {
    return crc_finalize(crc_update(crc_init(), input, input_size));
}

''', libraries=["snappy"])


class UncompressError(Exception):
    pass

class SnappyBufferSmallError(Exception):
    pass


def prepare(data):
    _out_data = None
    _out_size = None

    _out_data = ffi.new('char[]', data)
    _out_size = ffi.cast('size_t', len(data))

    return (_out_data, _out_size)


def compress(data):
    if isinstance(data, unicode):
        data = data.encode('utf-8')

    _input_data, _input_size = prepare(data)

    max_compressed = C.snappy_max_compressed_length(_input_size)

    _out_data = ffi.new('char[]', max_compressed)
    _out_size = ffi.new('size_t*', max_compressed)

    rc = C.snappy_compress(_input_data, _input_size, _out_data, _out_size)

    if rc != C.SNAPPY_OK:
        raise SnappyBufferSmallError()

    value = ffi.buffer(ffi.cast('char*', _out_data), _out_size[0])

    return value[:]


def uncompress(data):
    _out_data, _out_size = prepare(data)

    result = ffi.new('size_t*', 0)

    rc = C.snappy_validate_compressed_buffer(_out_data, _out_size)

    if not rc == C.SNAPPY_OK:
        raise UncompressError()

    rc = C.snappy_uncompressed_length(_out_data,
                                      _out_size,
                                      result)

    if not rc == C.SNAPPY_OK:
        raise UncompressError()

    _uncompressed_data = ffi.new('char[]', result[0])

    rc = C.snappy_uncompress(_out_data, _out_size, _uncompressed_data, result)

    if rc != C.SNAPPY_OK:
        raise UncompressError()

    buf =  ffi.buffer(ffi.cast('char*', _uncompressed_data), result[0])

    return buf[:]


def isValidCompressed(data):
    if isinstance(data, unicode):
        data = data.encode('utf-8')

    _out_data, _out_size= prepare(data)

    rc = C.snappy_validate_compressed_buffer(_out_data, _out_size)

    return rc == C.SNAPPY_OK

decompress = uncompress

def _crc32c(data):
    c_data = ffi.new('char[]', data)
    size = ffi.cast('int', len(data))
    return int(C._crc32c(c_data, size))


########NEW FILE########
__FILENAME__ = test_snappy
#!/usr/bin/env python
#
# Copyright (c) 2011, Andres Moreira <andres@andresmoreira.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the authors nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL ANDRES MOREIRA BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
import sys
import random
import snappy
import struct
from unittest import TestCase


class SnappyCompressionTest(TestCase):
    def test_simple_compress(self):
        text = "hello world!".encode('utf-8')
        compressed = snappy.compress(text)
        self.assertEqual(text, snappy.uncompress(compressed))

    def test_moredata_compress(self):
        text = "snappy +" * 1000 + " " + "by " * 1000 + " google"
        text = text.encode('utf-8')
        compressed = snappy.compress(text)
        self.assertEqual(text, snappy.uncompress(compressed))

    def test_randombytes_compress(self):
        _bytes = repr(os.urandom(1000)).encode('utf-8')
        compressed = snappy.compress(_bytes)
        self.assertEqual(_bytes, snappy.uncompress(compressed))

    def test_randombytes2_compress(self):
        _bytes = bytes(os.urandom(10000))
        compressed = snappy.compress(_bytes)
        self.assertEqual(_bytes, snappy.uncompress(compressed))

    def test_uncompress_error(self):
        self.assertRaises(snappy.UncompressError, snappy.uncompress,
                          "hoa".encode('utf-8'))

    if sys.version_info[0] == 2:
        def test_unicode_compress(self):
            text = "hello unicode world!".decode('utf-8')
            compressed = snappy.compress(text)
            self.assertEqual(text, snappy.uncompress(compressed))

    def test_decompress(self):
        # decompress == uncompress, just to support compatibility with zlib
        text = "hello world!".encode('utf-8')
        compressed = snappy.compress(text)
        self.assertEqual(text, snappy.decompress(compressed))

    def test_big_string(self):
        text = ('a'*10000000).encode('utf-8')
        compressed = snappy.compress(text)
        self.assertEqual(text, snappy.decompress(compressed))


class SnappyValidBufferTest(TestCase):

    def test_valid_compressed_buffer(self):
        text = "hello world!".encode('utf-8')
        compressed = snappy.compress(text)
        uncompressed = snappy.uncompress(compressed)
        self.assertEqual(text == uncompressed,
                         snappy.isValidCompressed(compressed))

    def test_invalid_compressed_buffer(self):
        self.assertFalse(snappy.isValidCompressed(
                "not compressed".encode('utf-8')))


class SnappyStreaming(TestCase):

    def test_random(self):
        for _ in range(100):
            compressor = snappy.StreamCompressor()
            decompressor = snappy.StreamDecompressor()
            data = b""
            compressed = b""
            for _ in range(random.randint(0, 3)):
                chunk = os.urandom(random.randint(0, snappy._CHUNK_MAX * 2))
                data += chunk
                compressed += compressor.add_chunk(
                        chunk, compress=random.choice([True, False, None]))

            upper_bound = random.choice([256, snappy._CHUNK_MAX * 2])
            while compressed:
                size = random.randint(0, upper_bound)
                chunk, compressed = compressed[:size], compressed[size:]
                chunk = decompressor.decompress(chunk)
                self.assertEqual(data[:len(chunk)], chunk)
                data = data[len(chunk):]

            decompressor.flush()
            self.assertEqual(len(data), 0)

    def test_compression(self):
        # test that we can add compressed chunks
        compressor = snappy.StreamCompressor()
        data = b"\0" * 50
        compressed_data = snappy.compress(data)
        crc = struct.pack("<L", snappy._masked_crc32c(data))
        self.assertEqual(crc, b"\x8f)H\xbd")
        self.assertEqual(len(compressed_data), 6)
        self.assertEqual(compressor.add_chunk(data, compress=True),
                         b"\xff\x06\x00\x00sNaPpY"
                         b"\x00\x0a\x00\x00" + crc + compressed_data)

        # test that we can add uncompressed chunks
        data = b"\x01" * 50
        crc = struct.pack("<L", snappy._masked_crc32c(data))
        self.assertEqual(crc, b"\xb2\x14)\x8a")
        self.assertEqual(compressor.add_chunk(data, compress=False),
                         b"\x01\x36\x00\x00" + crc + data)

        # test that we can add more data than will fit in one chunk
        data = b"\x01" * (snappy._CHUNK_MAX * 2 - 5)
        crc1 = struct.pack("<L",
                snappy._masked_crc32c(data[:snappy._CHUNK_MAX]))
        self.assertEqual(crc1, b"h#6\x8e")
        crc2 = struct.pack("<L",
                snappy._masked_crc32c(data[snappy._CHUNK_MAX:]))
        self.assertEqual(crc2, b"q\x8foE")
        self.assertEqual(compressor.add_chunk(data, compress=False),
                b"\x01\x04\x00\x01" + crc1 + data[:snappy._CHUNK_MAX] +
                b"\x01\xff\xff\x00" + crc2 + data[snappy._CHUNK_MAX:])

    def test_decompression(self):
        # test that we check for the initial stream identifier
        data = b"\x01" * 50
        self.assertRaises(snappy.UncompressError,
                snappy.StreamDecompressor().decompress,
                    b"\x01\x36\x00\00" +
                    struct.pack("<L", snappy._masked_crc32c(data)) + data)
        self.assertEqual(
                snappy.StreamDecompressor().decompress(
                    b"\xff\x06\x00\x00sNaPpY"
                    b"\x01\x36\x00\x00" +
                    struct.pack("<L", snappy._masked_crc32c(data)) + data),
                data)
        decompressor = snappy.StreamDecompressor()
        decompressor.decompress(b"\xff\x06\x00\x00sNaPpY")
        self.assertEqual(
                decompressor.copy().decompress(
                    b"\x01\x36\x00\x00" +
                    struct.pack("<L", snappy._masked_crc32c(data)) + data),
                data)

        # test that we throw errors for unknown unskippable chunks
        self.assertRaises(snappy.UncompressError,
                decompressor.copy().decompress, b"\x03\x01\x00\x00")

        # test that we skip unknown skippable chunks
        self.assertEqual(b"",
                         decompressor.copy().decompress(b"\xfe\x01\x00\x00"))

        # test that we check CRCs
        compressed_data = snappy.compress(data)
        real_crc = struct.pack("<L", snappy._masked_crc32c(data))
        fake_crc = os.urandom(4)
        self.assertRaises(snappy.UncompressError,
                decompressor.copy().decompress,
                    b"\x00\x0a\x00\x00" + fake_crc + compressed_data)
        self.assertEqual(
                decompressor.copy().decompress(
                    b"\x00\x0a\x00\x00" + real_crc + compressed_data),
                data)

        # test that we buffer when we don't have enough
        uncompressed_data = os.urandom(100)
        compressor = snappy.StreamCompressor()
        compressed_data = (compressor.compress(uncompressed_data[:50]) +
                           compressor.compress(uncompressed_data[50:]))
        for split1 in range(len(compressed_data) - 1):
            for split2 in range(split1, len(compressed_data)):
                decompressor = snappy.StreamDecompressor()
                self.assertEqual(
                    (decompressor.decompress(compressed_data[:split1]) +
                     decompressor.decompress(compressed_data[split1:split2]) +
                     decompressor.decompress(compressed_data[split2:])),
                    uncompressed_data)

    def test_concatenation(self):
        data1 = os.urandom(snappy._CHUNK_MAX * 2)
        data2 = os.urandom(4096)
        decompressor = snappy.StreamDecompressor()
        self.assertEqual(
                decompressor.decompress(
                    snappy.StreamCompressor().compress(data1) +
                    snappy.StreamCompressor().compress(data2)),
                data1 + data2)


if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_snappy_cffi
import sys

py3k = False
if sys.hexversion > 0x02070000:
    unicode = str
    py3k = True

def test_snappy_cffi_enum():
    from snappy_cffi import C

    assert 0 == C.SNAPPY_OK
    assert 1 == C.SNAPPY_INVALID_INPUT
    assert 2 == C.SNAPPY_BUFFER_TOO_SMALL

def test_snappy_all_cffi():
    from snappy_cffi import ffi, C

    import os
    data = 'string to be compressed'

    _input_data = ffi.new('char[]', data.encode('utf-8'))
    _input_size =  ffi.cast('size_t', len(_input_data))

    max_compressed = C.snappy_max_compressed_length(_input_size)

    _out_data = ffi.new('char[]', max_compressed)
    _out_size = ffi.new('size_t*', max_compressed)

    rc = C.snappy_compress(_input_data, _input_size, _out_data, _out_size)

    assert C.SNAPPY_OK == rc

    rc = C.snappy_validate_compressed_buffer(_out_data, _out_size[0])

    assert C.SNAPPY_OK == rc

    result = ffi.new('size_t*', 0)
    rc = C.snappy_uncompressed_length(_out_data,
                                      _out_size[0],
                                      result)

    assert C.SNAPPY_OK == rc

    _uncompressed_data = ffi.new('char[]', result[0])

    rc = C.snappy_uncompress(_out_data, _out_size[0], _uncompressed_data, result)

    assert C.SNAPPY_OK == rc

    result = ffi.string(_uncompressed_data, result[0])
    if py3k:
        result = result.decode('utf-8')

    assert data == result

########NEW FILE########
