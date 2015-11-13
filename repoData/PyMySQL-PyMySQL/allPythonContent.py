__FILENAME__ = example
#!/usr/bin/env python

from __future__ import print_function

import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='mysql')

cur = conn.cursor()

cur.execute("SELECT Host,User FROM user")

print(cur.description)

print()

for row in cur:
   print(row)

cur.close()
conn.close()

########NEW FILE########
__FILENAME__ = charset
MBLENGTH = {
        8:1,
        33:3,
        88:2,
        91:2
        }


class Charset(object):
    def __init__(self, id, name, collation, is_default):
        self.id, self.name, self.collation = id, name, collation
        self.is_default = is_default == 'Yes'

    @property
    def encoding(self):
        name = self.name
        if name == 'utf8mb4':
            return 'utf8'
        return name

    @property
    def is_binary(self):
        return self.id == 63


class Charsets:
    def __init__(self):
        self._by_id = {}

    def add(self, c):
        self._by_id[c.id] = c

    def by_id(self, id):
        return self._by_id[id]

    def by_name(self, name):
        name = name.lower()
        for c in self._by_id.values():
            if c.name == name and c.is_default:
                return c

_charsets = Charsets()
"""
Generated with:

mysql -N -s -e "select id, character_set_name, collation_name, is_default
from information_schema.collations order by id;" | python -c "import sys
for l in sys.stdin.readlines():
        id, name, collation, is_default  = l.split(chr(9))
        print '_charsets.add(Charset(%s, \'%s\', \'%s\', \'%s\'))' \
                % (id, name, collation, is_default.strip())
"

"""
_charsets.add(Charset(1, 'big5', 'big5_chinese_ci', 'Yes'))
_charsets.add(Charset(2, 'latin2', 'latin2_czech_cs', ''))
_charsets.add(Charset(3, 'dec8', 'dec8_swedish_ci', 'Yes'))
_charsets.add(Charset(4, 'cp850', 'cp850_general_ci', 'Yes'))
_charsets.add(Charset(5, 'latin1', 'latin1_german1_ci', ''))
_charsets.add(Charset(6, 'hp8', 'hp8_english_ci', 'Yes'))
_charsets.add(Charset(7, 'koi8r', 'koi8r_general_ci', 'Yes'))
_charsets.add(Charset(8, 'latin1', 'latin1_swedish_ci', 'Yes'))
_charsets.add(Charset(9, 'latin2', 'latin2_general_ci', 'Yes'))
_charsets.add(Charset(10, 'swe7', 'swe7_swedish_ci', 'Yes'))
_charsets.add(Charset(11, 'ascii', 'ascii_general_ci', 'Yes'))
_charsets.add(Charset(12, 'ujis', 'ujis_japanese_ci', 'Yes'))
_charsets.add(Charset(13, 'sjis', 'sjis_japanese_ci', 'Yes'))
_charsets.add(Charset(14, 'cp1251', 'cp1251_bulgarian_ci', ''))
_charsets.add(Charset(15, 'latin1', 'latin1_danish_ci', ''))
_charsets.add(Charset(16, 'hebrew', 'hebrew_general_ci', 'Yes'))
_charsets.add(Charset(18, 'tis620', 'tis620_thai_ci', 'Yes'))
_charsets.add(Charset(19, 'euckr', 'euckr_korean_ci', 'Yes'))
_charsets.add(Charset(20, 'latin7', 'latin7_estonian_cs', ''))
_charsets.add(Charset(21, 'latin2', 'latin2_hungarian_ci', ''))
_charsets.add(Charset(22, 'koi8u', 'koi8u_general_ci', 'Yes'))
_charsets.add(Charset(23, 'cp1251', 'cp1251_ukrainian_ci', ''))
_charsets.add(Charset(24, 'gb2312', 'gb2312_chinese_ci', 'Yes'))
_charsets.add(Charset(25, 'greek', 'greek_general_ci', 'Yes'))
_charsets.add(Charset(26, 'cp1250', 'cp1250_general_ci', 'Yes'))
_charsets.add(Charset(27, 'latin2', 'latin2_croatian_ci', ''))
_charsets.add(Charset(28, 'gbk', 'gbk_chinese_ci', 'Yes'))
_charsets.add(Charset(29, 'cp1257', 'cp1257_lithuanian_ci', ''))
_charsets.add(Charset(30, 'latin5', 'latin5_turkish_ci', 'Yes'))
_charsets.add(Charset(31, 'latin1', 'latin1_german2_ci', ''))
_charsets.add(Charset(32, 'armscii8', 'armscii8_general_ci', 'Yes'))
_charsets.add(Charset(33, 'utf8', 'utf8_general_ci', 'Yes'))
_charsets.add(Charset(34, 'cp1250', 'cp1250_czech_cs', ''))
_charsets.add(Charset(35, 'ucs2', 'ucs2_general_ci', 'Yes'))
_charsets.add(Charset(36, 'cp866', 'cp866_general_ci', 'Yes'))
_charsets.add(Charset(37, 'keybcs2', 'keybcs2_general_ci', 'Yes'))
_charsets.add(Charset(38, 'macce', 'macce_general_ci', 'Yes'))
_charsets.add(Charset(39, 'macroman', 'macroman_general_ci', 'Yes'))
_charsets.add(Charset(40, 'cp852', 'cp852_general_ci', 'Yes'))
_charsets.add(Charset(41, 'latin7', 'latin7_general_ci', 'Yes'))
_charsets.add(Charset(42, 'latin7', 'latin7_general_cs', ''))
_charsets.add(Charset(43, 'macce', 'macce_bin', ''))
_charsets.add(Charset(44, 'cp1250', 'cp1250_croatian_ci', ''))
_charsets.add(Charset(45, 'utf8mb4', 'utf8mb4_general_ci', 'Yes'))
_charsets.add(Charset(46, 'utf8mb4', 'utf8mb4_bin', ''))
_charsets.add(Charset(47, 'latin1', 'latin1_bin', ''))
_charsets.add(Charset(48, 'latin1', 'latin1_general_ci', ''))
_charsets.add(Charset(49, 'latin1', 'latin1_general_cs', ''))
_charsets.add(Charset(50, 'cp1251', 'cp1251_bin', ''))
_charsets.add(Charset(51, 'cp1251', 'cp1251_general_ci', 'Yes'))
_charsets.add(Charset(52, 'cp1251', 'cp1251_general_cs', ''))
_charsets.add(Charset(53, 'macroman', 'macroman_bin', ''))
_charsets.add(Charset(54, 'utf16', 'utf16_general_ci', 'Yes'))
_charsets.add(Charset(55, 'utf16', 'utf16_bin', ''))
_charsets.add(Charset(57, 'cp1256', 'cp1256_general_ci', 'Yes'))
_charsets.add(Charset(58, 'cp1257', 'cp1257_bin', ''))
_charsets.add(Charset(59, 'cp1257', 'cp1257_general_ci', 'Yes'))
_charsets.add(Charset(60, 'utf32', 'utf32_general_ci', 'Yes'))
_charsets.add(Charset(61, 'utf32', 'utf32_bin', ''))
_charsets.add(Charset(63, 'binary', 'binary', 'Yes'))
_charsets.add(Charset(64, 'armscii8', 'armscii8_bin', ''))
_charsets.add(Charset(65, 'ascii', 'ascii_bin', ''))
_charsets.add(Charset(66, 'cp1250', 'cp1250_bin', ''))
_charsets.add(Charset(67, 'cp1256', 'cp1256_bin', ''))
_charsets.add(Charset(68, 'cp866', 'cp866_bin', ''))
_charsets.add(Charset(69, 'dec8', 'dec8_bin', ''))
_charsets.add(Charset(70, 'greek', 'greek_bin', ''))
_charsets.add(Charset(71, 'hebrew', 'hebrew_bin', ''))
_charsets.add(Charset(72, 'hp8', 'hp8_bin', ''))
_charsets.add(Charset(73, 'keybcs2', 'keybcs2_bin', ''))
_charsets.add(Charset(74, 'koi8r', 'koi8r_bin', ''))
_charsets.add(Charset(75, 'koi8u', 'koi8u_bin', ''))
_charsets.add(Charset(77, 'latin2', 'latin2_bin', ''))
_charsets.add(Charset(78, 'latin5', 'latin5_bin', ''))
_charsets.add(Charset(79, 'latin7', 'latin7_bin', ''))
_charsets.add(Charset(80, 'cp850', 'cp850_bin', ''))
_charsets.add(Charset(81, 'cp852', 'cp852_bin', ''))
_charsets.add(Charset(82, 'swe7', 'swe7_bin', ''))
_charsets.add(Charset(83, 'utf8', 'utf8_bin', ''))
_charsets.add(Charset(84, 'big5', 'big5_bin', ''))
_charsets.add(Charset(85, 'euckr', 'euckr_bin', ''))
_charsets.add(Charset(86, 'gb2312', 'gb2312_bin', ''))
_charsets.add(Charset(87, 'gbk', 'gbk_bin', ''))
_charsets.add(Charset(88, 'sjis', 'sjis_bin', ''))
_charsets.add(Charset(89, 'tis620', 'tis620_bin', ''))
_charsets.add(Charset(90, 'ucs2', 'ucs2_bin', ''))
_charsets.add(Charset(91, 'ujis', 'ujis_bin', ''))
_charsets.add(Charset(92, 'geostd8', 'geostd8_general_ci', 'Yes'))
_charsets.add(Charset(93, 'geostd8', 'geostd8_bin', ''))
_charsets.add(Charset(94, 'latin1', 'latin1_spanish_ci', ''))
_charsets.add(Charset(95, 'cp932', 'cp932_japanese_ci', 'Yes'))
_charsets.add(Charset(96, 'cp932', 'cp932_bin', ''))
_charsets.add(Charset(97, 'eucjpms', 'eucjpms_japanese_ci', 'Yes'))
_charsets.add(Charset(98, 'eucjpms', 'eucjpms_bin', ''))
_charsets.add(Charset(99, 'cp1250', 'cp1250_polish_ci', ''))
_charsets.add(Charset(101, 'utf16', 'utf16_unicode_ci', ''))
_charsets.add(Charset(102, 'utf16', 'utf16_icelandic_ci', ''))
_charsets.add(Charset(103, 'utf16', 'utf16_latvian_ci', ''))
_charsets.add(Charset(104, 'utf16', 'utf16_romanian_ci', ''))
_charsets.add(Charset(105, 'utf16', 'utf16_slovenian_ci', ''))
_charsets.add(Charset(106, 'utf16', 'utf16_polish_ci', ''))
_charsets.add(Charset(107, 'utf16', 'utf16_estonian_ci', ''))
_charsets.add(Charset(108, 'utf16', 'utf16_spanish_ci', ''))
_charsets.add(Charset(109, 'utf16', 'utf16_swedish_ci', ''))
_charsets.add(Charset(110, 'utf16', 'utf16_turkish_ci', ''))
_charsets.add(Charset(111, 'utf16', 'utf16_czech_ci', ''))
_charsets.add(Charset(112, 'utf16', 'utf16_danish_ci', ''))
_charsets.add(Charset(113, 'utf16', 'utf16_lithuanian_ci', ''))
_charsets.add(Charset(114, 'utf16', 'utf16_slovak_ci', ''))
_charsets.add(Charset(115, 'utf16', 'utf16_spanish2_ci', ''))
_charsets.add(Charset(116, 'utf16', 'utf16_roman_ci', ''))
_charsets.add(Charset(117, 'utf16', 'utf16_persian_ci', ''))
_charsets.add(Charset(118, 'utf16', 'utf16_esperanto_ci', ''))
_charsets.add(Charset(119, 'utf16', 'utf16_hungarian_ci', ''))
_charsets.add(Charset(120, 'utf16', 'utf16_sinhala_ci', ''))
_charsets.add(Charset(128, 'ucs2', 'ucs2_unicode_ci', ''))
_charsets.add(Charset(129, 'ucs2', 'ucs2_icelandic_ci', ''))
_charsets.add(Charset(130, 'ucs2', 'ucs2_latvian_ci', ''))
_charsets.add(Charset(131, 'ucs2', 'ucs2_romanian_ci', ''))
_charsets.add(Charset(132, 'ucs2', 'ucs2_slovenian_ci', ''))
_charsets.add(Charset(133, 'ucs2', 'ucs2_polish_ci', ''))
_charsets.add(Charset(134, 'ucs2', 'ucs2_estonian_ci', ''))
_charsets.add(Charset(135, 'ucs2', 'ucs2_spanish_ci', ''))
_charsets.add(Charset(136, 'ucs2', 'ucs2_swedish_ci', ''))
_charsets.add(Charset(137, 'ucs2', 'ucs2_turkish_ci', ''))
_charsets.add(Charset(138, 'ucs2', 'ucs2_czech_ci', ''))
_charsets.add(Charset(139, 'ucs2', 'ucs2_danish_ci', ''))
_charsets.add(Charset(140, 'ucs2', 'ucs2_lithuanian_ci', ''))
_charsets.add(Charset(141, 'ucs2', 'ucs2_slovak_ci', ''))
_charsets.add(Charset(142, 'ucs2', 'ucs2_spanish2_ci', ''))
_charsets.add(Charset(143, 'ucs2', 'ucs2_roman_ci', ''))
_charsets.add(Charset(144, 'ucs2', 'ucs2_persian_ci', ''))
_charsets.add(Charset(145, 'ucs2', 'ucs2_esperanto_ci', ''))
_charsets.add(Charset(146, 'ucs2', 'ucs2_hungarian_ci', ''))
_charsets.add(Charset(147, 'ucs2', 'ucs2_sinhala_ci', ''))
_charsets.add(Charset(159, 'ucs2', 'ucs2_general_mysql500_ci', ''))
_charsets.add(Charset(160, 'utf32', 'utf32_unicode_ci', ''))
_charsets.add(Charset(161, 'utf32', 'utf32_icelandic_ci', ''))
_charsets.add(Charset(162, 'utf32', 'utf32_latvian_ci', ''))
_charsets.add(Charset(163, 'utf32', 'utf32_romanian_ci', ''))
_charsets.add(Charset(164, 'utf32', 'utf32_slovenian_ci', ''))
_charsets.add(Charset(165, 'utf32', 'utf32_polish_ci', ''))
_charsets.add(Charset(166, 'utf32', 'utf32_estonian_ci', ''))
_charsets.add(Charset(167, 'utf32', 'utf32_spanish_ci', ''))
_charsets.add(Charset(168, 'utf32', 'utf32_swedish_ci', ''))
_charsets.add(Charset(169, 'utf32', 'utf32_turkish_ci', ''))
_charsets.add(Charset(170, 'utf32', 'utf32_czech_ci', ''))
_charsets.add(Charset(171, 'utf32', 'utf32_danish_ci', ''))
_charsets.add(Charset(172, 'utf32', 'utf32_lithuanian_ci', ''))
_charsets.add(Charset(173, 'utf32', 'utf32_slovak_ci', ''))
_charsets.add(Charset(174, 'utf32', 'utf32_spanish2_ci', ''))
_charsets.add(Charset(175, 'utf32', 'utf32_roman_ci', ''))
_charsets.add(Charset(176, 'utf32', 'utf32_persian_ci', ''))
_charsets.add(Charset(177, 'utf32', 'utf32_esperanto_ci', ''))
_charsets.add(Charset(178, 'utf32', 'utf32_hungarian_ci', ''))
_charsets.add(Charset(179, 'utf32', 'utf32_sinhala_ci', ''))
_charsets.add(Charset(192, 'utf8', 'utf8_unicode_ci', ''))
_charsets.add(Charset(193, 'utf8', 'utf8_icelandic_ci', ''))
_charsets.add(Charset(194, 'utf8', 'utf8_latvian_ci', ''))
_charsets.add(Charset(195, 'utf8', 'utf8_romanian_ci', ''))
_charsets.add(Charset(196, 'utf8', 'utf8_slovenian_ci', ''))
_charsets.add(Charset(197, 'utf8', 'utf8_polish_ci', ''))
_charsets.add(Charset(198, 'utf8', 'utf8_estonian_ci', ''))
_charsets.add(Charset(199, 'utf8', 'utf8_spanish_ci', ''))
_charsets.add(Charset(200, 'utf8', 'utf8_swedish_ci', ''))
_charsets.add(Charset(201, 'utf8', 'utf8_turkish_ci', ''))
_charsets.add(Charset(202, 'utf8', 'utf8_czech_ci', ''))
_charsets.add(Charset(203, 'utf8', 'utf8_danish_ci', ''))
_charsets.add(Charset(204, 'utf8', 'utf8_lithuanian_ci', ''))
_charsets.add(Charset(205, 'utf8', 'utf8_slovak_ci', ''))
_charsets.add(Charset(206, 'utf8', 'utf8_spanish2_ci', ''))
_charsets.add(Charset(207, 'utf8', 'utf8_roman_ci', ''))
_charsets.add(Charset(208, 'utf8', 'utf8_persian_ci', ''))
_charsets.add(Charset(209, 'utf8', 'utf8_esperanto_ci', ''))
_charsets.add(Charset(210, 'utf8', 'utf8_hungarian_ci', ''))
_charsets.add(Charset(211, 'utf8', 'utf8_sinhala_ci', ''))
_charsets.add(Charset(223, 'utf8', 'utf8_general_mysql500_ci', ''))
_charsets.add(Charset(224, 'utf8mb4', 'utf8mb4_unicode_ci', ''))
_charsets.add(Charset(225, 'utf8mb4', 'utf8mb4_icelandic_ci', ''))
_charsets.add(Charset(226, 'utf8mb4', 'utf8mb4_latvian_ci', ''))
_charsets.add(Charset(227, 'utf8mb4', 'utf8mb4_romanian_ci', ''))
_charsets.add(Charset(228, 'utf8mb4', 'utf8mb4_slovenian_ci', ''))
_charsets.add(Charset(229, 'utf8mb4', 'utf8mb4_polish_ci', ''))
_charsets.add(Charset(230, 'utf8mb4', 'utf8mb4_estonian_ci', ''))
_charsets.add(Charset(231, 'utf8mb4', 'utf8mb4_spanish_ci', ''))
_charsets.add(Charset(232, 'utf8mb4', 'utf8mb4_swedish_ci', ''))
_charsets.add(Charset(233, 'utf8mb4', 'utf8mb4_turkish_ci', ''))
_charsets.add(Charset(234, 'utf8mb4', 'utf8mb4_czech_ci', ''))
_charsets.add(Charset(235, 'utf8mb4', 'utf8mb4_danish_ci', ''))
_charsets.add(Charset(236, 'utf8mb4', 'utf8mb4_lithuanian_ci', ''))
_charsets.add(Charset(237, 'utf8mb4', 'utf8mb4_slovak_ci', ''))
_charsets.add(Charset(238, 'utf8mb4', 'utf8mb4_spanish2_ci', ''))
_charsets.add(Charset(239, 'utf8mb4', 'utf8mb4_roman_ci', ''))
_charsets.add(Charset(240, 'utf8mb4', 'utf8mb4_persian_ci', ''))
_charsets.add(Charset(241, 'utf8mb4', 'utf8mb4_esperanto_ci', ''))
_charsets.add(Charset(242, 'utf8mb4', 'utf8mb4_hungarian_ci', ''))
_charsets.add(Charset(243, 'utf8mb4', 'utf8mb4_sinhala_ci', ''))


charset_by_name = _charsets.by_name
charset_by_id = _charsets.by_id


def charset_to_encoding(name):
    """Convert MySQL's charset name to Python's codec name"""
    if name == 'utf8mb4':
        return 'utf8'
    return name

########NEW FILE########
__FILENAME__ = connections
# Python implementation of the MySQL client-server protocol
# http://dev.mysql.com/doc/internals/en/client-server-protocol.html

from __future__ import print_function
from ._compat import PY2, range_type, text_type, str_type, JYTHON, IRONPYTHON

import errno
from functools import partial
import os
import hashlib
import socket

try:
    import ssl
    SSL_ENABLED = True
except ImportError:
    SSL_ENABLED = False

import struct
import sys
if PY2:
    import ConfigParser as configparser
else:
    import configparser

import io

try:
    import getpass
    DEFAULT_USER = getpass.getuser()
except ImportError:
    DEFAULT_USER = None


from .charset import MBLENGTH, charset_by_name, charset_by_id
from .cursors import Cursor
from .constants import FIELD_TYPE
from .constants import SERVER_STATUS
from .constants.CLIENT import *
from .constants.COMMAND import *
from .util import byte2int, int2byte
from .converters import escape_item, encoders, decoders, escape_string
from .err import (
    raise_mysql_exception, Warning, Error,
    InterfaceError, DataError, DatabaseError, OperationalError,
    IntegrityError, InternalError, NotSupportedError, ProgrammingError)

_py_version = sys.version_info[:2]


# socket.makefile() in Python 2 is not usable because very inefficient and
# bad behavior about timeout.
# XXX: ._socketio doesn't work under IronPython.
if _py_version == (2, 7) and not IRONPYTHON:
    # read method of file-like returned by sock.makefile() is very slow.
    # So we copy io-based one from Python 3.
    from ._socketio import SocketIO
    def _makefile(sock, mode):
        return io.BufferedReader(SocketIO(sock, mode))
elif _py_version == (2, 6):
    # Python 2.6 doesn't have fast io module.
    # So we make original one.
    class SockFile(object):
        def __init__(self, sock):
            self._sock = sock
        def read(self, n):
            read = self._sock.recv(n)
            if len(read) == n:
                return read
            while True:
                data = self._sock.recv(n-len(read))
                if not data:
                    return read
                read += data
                if len(read) == n:
                    return read

    def _makefile(sock, mode):
        assert mode == 'rb'
        return SockFile(sock)
else:
    # socket.makefile in Python 3 is nice.
    def _makefile(sock, mode):
        return sock.makefile(mode)


TEXT_TYPES = set([
    FIELD_TYPE.BIT,
    FIELD_TYPE.BLOB,
    FIELD_TYPE.LONG_BLOB,
    FIELD_TYPE.MEDIUM_BLOB,
    FIELD_TYPE.STRING,
    FIELD_TYPE.TINY_BLOB,
    FIELD_TYPE.VAR_STRING,
    FIELD_TYPE.VARCHAR])

sha_new = partial(hashlib.new, 'sha1')

DEBUG = False

NULL_COLUMN = 251
UNSIGNED_CHAR_COLUMN = 251
UNSIGNED_SHORT_COLUMN = 252
UNSIGNED_INT24_COLUMN = 253
UNSIGNED_INT64_COLUMN = 254
UNSIGNED_CHAR_LENGTH = 1
UNSIGNED_SHORT_LENGTH = 2
UNSIGNED_INT24_LENGTH = 3
UNSIGNED_INT64_LENGTH = 8

DEFAULT_CHARSET = 'latin1'

MAX_PACKET_LEN = 2**24-1


def dump_packet(data):

    def is_ascii(data):
        if 65 <= byte2int(data) <= 122:  #data.isalnum():
            if isinstance(data, int):
                return chr(data)
            return data
        return '.'

    try:
        print("packet length:", len(data))
        print("method call[1]:", sys._getframe(1).f_code.co_name)
        print("method call[2]:", sys._getframe(2).f_code.co_name)
        print("method call[3]:", sys._getframe(3).f_code.co_name)
        print("method call[4]:", sys._getframe(4).f_code.co_name)
        print("method call[5]:", sys._getframe(5).f_code.co_name)
        print("-" * 88)
    except ValueError:
        pass
    dump_data = [data[i:i+16] for i in range_type(0, min(len(data), 256), 16)]
    for d in dump_data:
        print(' '.join(map(lambda x:"{:02X}".format(byte2int(x)), d)) +
              '   ' * (16 - len(d)) + ' ' * 2 +
              ' '.join(map(lambda x:"{}".format(is_ascii(x)), d)))
    print("-" * 88)
    print()


def _scramble(password, message):
    if not password:
        return b'\0'
    if DEBUG: print('password=' + password)
    stage1 = sha_new(password).digest()
    stage2 = sha_new(stage1).digest()
    s = sha_new()
    s.update(message)
    s.update(stage2)
    result = s.digest()
    return _my_crypt(result, stage1)


def _my_crypt(message1, message2):
    length = len(message1)
    result = struct.pack('B', length)
    for i in range_type(length):
        x = (struct.unpack('B', message1[i:i+1])[0] ^
             struct.unpack('B', message2[i:i+1])[0])
        result += struct.pack('B', x)
    return result

# old_passwords support ported from libmysql/password.c
SCRAMBLE_LENGTH_323 = 8


class RandStruct_323(object):
    def __init__(self, seed1, seed2):
        self.max_value = 0x3FFFFFFF
        self.seed1 = seed1 % self.max_value
        self.seed2 = seed2 % self.max_value

    def my_rnd(self):
        self.seed1 = (self.seed1 * 3 + self.seed2) % self.max_value
        self.seed2 = (self.seed1 + self.seed2 + 33) % self.max_value
        return float(self.seed1) / float(self.max_value)


def _scramble_323(password, message):
    hash_pass = _hash_password_323(password)
    hash_message = _hash_password_323(message[:SCRAMBLE_LENGTH_323])
    hash_pass_n = struct.unpack(">LL", hash_pass)
    hash_message_n = struct.unpack(">LL", hash_message)

    rand_st = RandStruct_323(hash_pass_n[0] ^ hash_message_n[0],
                             hash_pass_n[1] ^ hash_message_n[1])
    outbuf = io.BytesIO()
    for _ in range_type(min(SCRAMBLE_LENGTH_323, len(message))):
        outbuf.write(int2byte(int(rand_st.my_rnd() * 31) + 64))
    extra = int2byte(int(rand_st.my_rnd() * 31))
    out = outbuf.getvalue()
    outbuf = io.BytesIO()
    for c in out:
        outbuf.write(int2byte(byte2int(c) ^ byte2int(extra)))
    return outbuf.getvalue()


def _hash_password_323(password):
    nr = 1345345333
    add = 7
    nr2 = 0x12345671

    for c in [byte2int(x) for x in password if x not in (' ', '\t')]:
        nr^= (((nr & 63)+add)*c)+ (nr << 8) & 0xFFFFFFFF
        nr2= (nr2 + ((nr2 << 8) ^ nr)) & 0xFFFFFFFF
        add= (add + c) & 0xFFFFFFFF

    r1 = nr & ((1 << 31) - 1) # kill sign bits
    r2 = nr2 & ((1 << 31) - 1)

    # pack
    return struct.pack(">LL", r1, r2)


def pack_int24(n):
    return struct.pack('<I', n)[:3]

def unpack_uint16(n):
    return struct.unpack('<H', n[0:2])[0]

def unpack_int24(n):
    return struct.unpack('<I', n + b'\0')[0]

def unpack_int32(n):
    return struct.unpack('<I', n)[0]

def unpack_int64(n):
    return struct.unpack('<Q', n)[0]


class MysqlPacket(object):
    """Representation of a MySQL response packet.  Reads in the packet
    from the network socket, removes packet header and provides an interface
    for reading/parsing the packet results."""
    __slots__ = ('_position', '_data', '_packet_number')

    def __init__(self, connection):
        self._position = 0
        self._recv_packet(connection)

    def _recv_packet(self, connection):
        """Parse the packet header and read entire packet payload into buffer."""
        buff = b''
        while True:
            packet_header = connection._read_bytes(4)
            if DEBUG: dump_packet(packet_header)
            packet_length_bin = packet_header[:3]

            #TODO: check sequence id
            self._packet_number = byte2int(packet_header[3])

            bin_length = packet_length_bin + b'\0'  # pad little-endian number
            bytes_to_read = struct.unpack('<I', bin_length)[0]
            recv_data = connection._read_bytes(bytes_to_read)
            if DEBUG: dump_packet(recv_data)
            buff += recv_data
            if bytes_to_read < MAX_PACKET_LEN:
                break
        self._data = buff

    def packet_number(self):
        return self._packet_number

    def get_all_data(self):
        return self._data

    def read(self, size):
        """Read the first 'size' bytes in packet and advance cursor past them."""
        result = self._data[self._position:(self._position+size)]
        if len(result) != size:
            error = ('Result length not requested length:\n'
                     'Expected=%s.  Actual=%s.  Position: %s.  Data Length: %s'
                     % (size, len(result), self._position, len(self._data)))
            if DEBUG:
                print(error)
                self.dump()
            raise AssertionError(error)
        self._position += size
        return result

    def read_all(self):
        """Read all remaining data in the packet.

        (Subsequent read() will return errors.)
        """
        result = self._data[self._position:]
        self._position = None  # ensure no subsequent read()
        return result

    def advance(self, length):
        """Advance the cursor in data buffer 'length' bytes."""
        new_position = self._position + length
        if new_position < 0 or new_position > len(self._data):
            raise Exception('Invalid advance amount (%s) for cursor.  '
                            'Position=%s' % (length, new_position))
        self._position = new_position

    def rewind(self, position=0):
        """Set the position of the data buffer cursor to 'position'."""
        if position < 0 or position > len(self._data):
            raise Exception("Invalid position to rewind cursor to: %s." % position)
        self._position = position

    def get_bytes(self, position, length=1):
        """Get 'length' bytes starting at 'position'.

        Position is start of payload (first four packet header bytes are not
        included) starting at index '0'.

        No error checking is done.  If requesting outside end of buffer
        an empty string (or string shorter than 'length') may be returned!
        """
        return self._data[position:(position+length)]

    def read_length_encoded_integer(self):
        """Read a 'Length Coded Binary' number from the data buffer.

        Length coded numbers can be anywhere from 1 to 9 bytes depending
        on the value of the first byte.
        """
        c = ord(self.read(1))
        if c == NULL_COLUMN:
            return None
        if c < UNSIGNED_CHAR_COLUMN:
            return c
        elif c == UNSIGNED_SHORT_COLUMN:
            return unpack_uint16(self.read(UNSIGNED_SHORT_LENGTH))
        elif c == UNSIGNED_INT24_COLUMN:
            return unpack_int24(self.read(UNSIGNED_INT24_LENGTH))
        elif c == UNSIGNED_INT64_COLUMN:
            return unpack_int64(self.read(UNSIGNED_INT64_LENGTH))

    def read_length_coded_string(self):
        """Read a 'Length Coded String' from the data buffer.

        A 'Length Coded String' consists first of a length coded
        (unsigned, positive) integer represented in 1-9 bytes followed by
        that many bytes of binary data.  (For example "cat" would be "3cat".)
        """
        length = self.read_length_encoded_integer()
        if length is None:
            return None
        return self.read(length)

    def is_ok_packet(self):
        return self._data[0:1] == b'\0'

    def is_eof_packet(self):
        # http://dev.mysql.com/doc/internals/en/generic-response-packets.html#packet-EOF_Packet
        # Caution: \xFE may be LengthEncodedInteger.
        # If \xFE is LengthEncodedInteger header, 8bytes followed.
        return len(self._data) < 9 and self._data[0:1] == b'\xfe'

    def is_resultset_packet(self):
        field_count = ord(self._data[0:1])
        return 1 <= field_count <= 250

    def is_error_packet(self):
        return self._data[0:1] == b'\xff'

    def check_error(self):
        if self.is_error_packet():
            self.rewind()
            self.advance(1)  # field_count == error (we already know that)
            errno = unpack_uint16(self.read(2))
            if DEBUG: print("errno =", errno)
            raise_mysql_exception(self._data)

    def dump(self):
        dump_packet(self._data)


class FieldDescriptorPacket(MysqlPacket):
    """A MysqlPacket that represents a specific column's metadata in the result.

    Parsing is automatically done and the results are exported via public
    attributes on the class such as: db, table_name, name, length, type_code.
    """

    def __init__(self, connection):
        MysqlPacket.__init__(self, connection)
        self.__parse_field_descriptor(connection.encoding)

    def __parse_field_descriptor(self, encoding):
        """Parse the 'Field Descriptor' (Metadata) packet.

        This is compatible with MySQL 4.1+ (not compatible with MySQL 4.0).
        """
        self.catalog = self.read_length_coded_string()
        self.db = self.read_length_coded_string()
        self.table_name = self.read_length_coded_string().decode(encoding)
        self.org_table = self.read_length_coded_string().decode(encoding)
        self.name = self.read_length_coded_string().decode(encoding)
        self.org_name = self.read_length_coded_string().decode(encoding)
        self.advance(1)  # non-null filler
        self.charsetnr = struct.unpack('<H', self.read(2))[0]
        self.length = struct.unpack('<I', self.read(4))[0]
        self.type_code = byte2int(self.read(1))
        self.flags = struct.unpack('<H', self.read(2))[0]
        self.scale = byte2int(self.read(1))  # "decimals"
        self.advance(2)  # filler (always 0x00)

        # 'default' is a length coded binary and is still in the buffer?
        # not used for normal result sets...

    def description(self):
        """Provides a 7-item tuple compatible with the Python PEP249 DB Spec."""
        desc = []
        desc.append(self.name)
        desc.append(self.type_code)
        desc.append(None) # TODO: display_length; should this be self.length?
        desc.append(self.get_column_length()) # 'internal_size'
        desc.append(self.get_column_length()) # 'precision'  # TODO: why!?!?
        desc.append(self.scale)

        # 'null_ok' -- can this be True/False rather than 1/0?
        #              if so just do:  desc.append(bool(self.flags % 2 == 0))
        if self.flags % 2 == 0:
            desc.append(1)
        else:
            desc.append(0)
        return tuple(desc)

    def get_column_length(self):
        if self.type_code == FIELD_TYPE.VAR_STRING:
            mblen = MBLENGTH.get(self.charsetnr, 1)
            return self.length // mblen
        return self.length

    def __str__(self):
        return ('%s %r.%r.%r, type=%s, flags=%x'
                % (self.__class__, self.db, self.table_name, self.name,
                   self.type_code, self.flags))


class OKPacketWrapper(object):
    """
    OK Packet Wrapper. It uses an existing packet object, and wraps
    around it, exposing useful variables while still providing access
    to the original packet objects variables and methods.
    """

    def __init__(self, from_packet):
        if not from_packet.is_ok_packet():
            raise ValueError('Cannot create ' + str(self.__class__.__name__) +
                             ' object from invalid packet type')

        self.packet = from_packet
        self.packet.advance(1)

        self.affected_rows = self.packet.read_length_encoded_integer()
        self.insert_id = self.packet.read_length_encoded_integer()
        self.server_status = struct.unpack('<H', self.packet.read(2))[0]
        self.warning_count = struct.unpack('<H', self.packet.read(2))[0]
        self.message = self.packet.read_all()
        self.has_next = self.server_status & SERVER_STATUS.SERVER_MORE_RESULTS_EXISTS

    def __getattr__(self, key):
        return getattr(self.packet, key)


class EOFPacketWrapper(object):
    """
    EOF Packet Wrapper. It uses an existing packet object, and wraps
    around it, exposing useful variables while still providing access
    to the original packet objects variables and methods.
    """

    def __init__(self, from_packet):
        if not from_packet.is_eof_packet():
            raise ValueError(
                "Cannot create '{0}' object from invalid packet type".format(
                    self.__class__))

        self.packet = from_packet
        from_packet.advance(1)
        self.warning_count = struct.unpack('<h', from_packet.read(2))[0]
        self.server_status = struct.unpack('<h', self.packet.read(2))[0]
        if DEBUG: print("server_status=", self.server_status)
        self.has_next = self.server_status & SERVER_STATUS.SERVER_MORE_RESULTS_EXISTS

    def __getattr__(self, key):
        return getattr(self.packet, key)


class Connection(object):
    """
    Representation of a socket with a mysql server.

    The proper way to get an instance of this class is to call
    connect().

    """

    socket = None

    def __init__(self, host="localhost", user=None, passwd="",
                 database=None, port=3306, unix_socket=None,
                 charset='', sql_mode=None,
                 read_default_file=None, conv=decoders, use_unicode=None,
                 client_flag=0, cursorclass=Cursor, init_command=None,
                 connect_timeout=None, ssl=None, read_default_group=None,
                 compress=None, named_pipe=None, no_delay=False,
                 autocommit=False, db=None):
        """
        Establish a connection to the MySQL database. Accepts several
        arguments:

        host: Host where the database server is located
        user: Username to log in as
        passwd: Password to use.
        database: Database to use, None to not use a particular one.
        port: MySQL port to use, default is usually OK.
        unix_socket: Optionally, you can use a unix socket rather than TCP/IP.
        charset: Charset you want to use.
        sql_mode: Default SQL_MODE to use.
        read_default_file: Specifies  my.cnf file to read these parameters from under the [client] section.
        conv: Decoders dictionary to use instead of the default one. This is used to provide custom marshalling of types. See converters.
        use_unicode: Whether or not to default to unicode strings. This option defaults to true for Py3k.
        client_flag: Custom flags to send to MySQL. Find potential values in constants.CLIENT.
        cursorclass: Custom cursor class to use.
        init_command: Initial SQL statement to run when connection is established.
        connect_timeout: Timeout before throwing an exception when connecting.
        ssl: A dict of arguments similar to mysql_ssl_set()'s parameters. For now the capath and cipher arguments are not supported.
        read_default_group: Group to read from in the configuration file.
        compress; Not supported
        named_pipe: Not supported
        no_delay: Disable Nagle's algorithm on the socket
        autocommit: Autocommit mode. None means use server default. (default: False)
        db: Alias for database. (for compatibility to MySQLdb)
        """

        if use_unicode is None and sys.version_info[0] > 2:
            use_unicode = True

        if db is not None and database is None:
            database = db

        if compress or named_pipe:
            raise NotImplementedError("compress and named_pipe arguments are not supported")

        if ssl and ('capath' in ssl or 'cipher' in ssl):
            raise NotImplementedError('ssl options capath and cipher are not supported')

        self.ssl = False
        if ssl:
            if not SSL_ENABLED:
                raise NotImplementedError("ssl module not found")
            self.ssl = True
            client_flag |= SSL
            for k in ('key', 'cert', 'ca'):
                v = None
                if k in ssl:
                    v = ssl[k]
                setattr(self, k, v)

        if read_default_group and not read_default_file:
            if sys.platform.startswith("win"):
                read_default_file = "c:\\my.ini"
            else:
                read_default_file = "/etc/my.cnf"

        if read_default_file:
            if not read_default_group:
                read_default_group = "client"

            cfg = configparser.RawConfigParser()
            cfg.read(os.path.expanduser(read_default_file))

            def _config(key, default):
                try:
                    return cfg.get(read_default_group, key)
                except Exception:
                    return default

            user = _config("user", user)
            passwd = _config("password", passwd)
            host = _config("host", host)
            database = _config("database", database)
            unix_socket = _config("socket", unix_socket)
            port = int(_config("port", port))
            charset = _config("default-character-set", charset)

        self.host = host
        self.port = port
        self.user = user or DEFAULT_USER
        self.password = passwd or ""
        self.db = database
        self.no_delay = no_delay
        self.unix_socket = unix_socket
        if charset:
            self.charset = charset
            self.use_unicode = True
        else:
            self.charset = DEFAULT_CHARSET
            self.use_unicode = False

        if use_unicode is not None:
            self.use_unicode = use_unicode

        self.encoding = charset_by_name(self.charset).encoding

        client_flag |= CAPABILITIES
        client_flag |= MULTI_STATEMENTS
        if self.db:
            client_flag |= CONNECT_WITH_DB
        self.client_flag = client_flag

        self.cursorclass = cursorclass
        self.connect_timeout = connect_timeout

        self._result = None
        self._affected_rows = 0
        self.host_info = "Not connected"

        #: specified autocommit mode. None means use server default.
        self.autocommit_mode = autocommit

        self.encoders = encoders  # Need for MySQLdb compatibility.
        self.decoders = conv
        self.sql_mode = sql_mode
        self.init_command = init_command
        self._connect()

    def close(self):
        ''' Send the quit message and close the socket '''
        if self.socket is None:
            raise Error("Already closed")
        send_data = struct.pack('<i', 1) + int2byte(COM_QUIT)
        try:
            self._write_bytes(send_data)
        except Exception:
            pass
        finally:
            sock = self.socket
            self.socket = None
            self._rfile = None
            sock.close()

    def __del__(self):
        if self.socket:
            self.close()

    def autocommit(self, value):
        self.autocommit_mode = bool(value)
        current = self.get_autocommit()
        if value != current:
            self._send_autocommit_mode()

    def get_autocommit(self):
        return bool(self.server_status &
                    SERVER_STATUS.SERVER_STATUS_AUTOCOMMIT)

    def _read_ok_packet(self):
        pkt = self._read_packet()
        if not pkt.is_ok_packet():
            raise OperationalError(2014, "Command Out of Sync")
        ok = OKPacketWrapper(pkt)
        self.server_status = ok.server_status
        return True

    def _send_autocommit_mode(self):
        ''' Set whether or not to commit after every execute() '''
        self._execute_command(COM_QUERY, "SET AUTOCOMMIT = %s" %
                              self.escape(self.autocommit_mode))
        self._read_ok_packet()

    def commit(self):
        ''' Commit changes to stable storage '''
        self._execute_command(COM_QUERY, "COMMIT")
        self._read_ok_packet()

    def rollback(self):
        ''' Roll back the current transaction '''
        self._execute_command(COM_QUERY, "ROLLBACK")
        self._read_ok_packet()

    def select_db(self, db):
        '''Set current db'''
        self._execute_command(COM_INIT_DB, db)
        self._read_ok_packet()

    def escape(self, obj):
        ''' Escape whatever value you pass to it  '''
        if isinstance(obj, str_type):
            return "'" + self.escape_string(obj) + "'"
        return escape_item(obj, self.charset)

    def literal(self, obj):
        '''Alias for escape()'''
        return self.escape(obj)

    def escape_string(self, s):
        if (self.server_status &
                SERVER_STATUS.SERVER_STATUS_NO_BACKSLASH_ESCAPES):
            return s.replace("'", "''")
        return escape_string(s)

    def cursor(self, cursor=None):
        ''' Create a new cursor to execute queries with '''
        if cursor:
            return cursor(self)
        return self.cursorclass(self)

    def __enter__(self):
        ''' Context manager that returns a Cursor '''
        return self.cursor()

    def __exit__(self, exc, value, traceback):
        ''' On successful exit, commit. On exception, rollback. '''
        if exc:
            self.rollback()
        else:
            self.commit()

    # The following methods are INTERNAL USE ONLY (called from Cursor)
    def query(self, sql, unbuffered=False):
        #if DEBUG:
        #    print("DEBUG: sending query:", sql)
        if isinstance(sql, text_type) and not (JYTHON or IRONPYTHON):
            sql = sql.encode(self.encoding)
        self._execute_command(COM_QUERY, sql)
        self._affected_rows = self._read_query_result(unbuffered=unbuffered)
        return self._affected_rows

    def next_result(self):
        self._affected_rows = self._read_query_result()
        return self._affected_rows

    def affected_rows(self):
        return self._affected_rows

    def kill(self, thread_id):
        arg = struct.pack('<I', thread_id)
        self._execute_command(COM_PROCESS_KILL, arg)
        return self._read_ok_packet()

    def ping(self, reconnect=True):
        ''' Check if the server is alive '''
        if self.socket is None:
            if reconnect:
                self._connect()
                reconnect = False
            else:
                raise Error("Already closed")
        try:
            self._execute_command(COM_PING, "")
            return self._read_ok_packet()
        except Exception:
            if reconnect:
                self._connect()
                return self.ping(False)
            else:
                raise

    def set_charset(self, charset):
        # Make sure charset is supported.
        encoding = charset_by_name(charset).encoding

        self._execute_command(COM_QUERY, "SET NAMES %s" % self.escape(charset))
        self._read_packet()
        self.charset = charset
        self.encoding = encoding

    def _connect(self):
        sock = None
        try:
            if self.unix_socket and self.host in ('localhost', '127.0.0.1'):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                t = sock.gettimeout()
                sock.settimeout(self.connect_timeout)
                sock.connect(self.unix_socket)
                sock.settimeout(t)
                self.host_info = "Localhost via UNIX socket"
                if DEBUG: print('connected using unix_socket')
            else:
                while True:
                    try:
                        sock = socket.create_connection(
                                (self.host, self.port), self.connect_timeout)
                        break
                    except (OSError, IOError) as e:
                        if e.errno == errno.EINTR:
                            continue
                        raise
                self.host_info = "socket %s:%d" % (self.host, self.port)
                if DEBUG: print('connected using socket')
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if self.no_delay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket = sock
            self._rfile = _makefile(sock, 'rb')
            self._get_server_information()
            self._request_authentication()

            if self.sql_mode is not None:
                c = self.cursor()
                c.execute("SET sql_mode=%s", (self.sql_mode,))

            if self.init_command is not None:
                c = self.cursor()
                c.execute(self.init_command)
                self.commit()

            if self.autocommit_mode is not None:
                self.autocommit(self.autocommit_mode)
        except Exception as e:
            self._rfile = None
            if sock is not None:
                try:
                    sock.close()
                except socket.error:
                    pass
            raise OperationalError(
                2003, "Can't connect to MySQL server on %r (%s)" % (self.host, e))


    def _read_packet(self, packet_type=MysqlPacket):
        """Read an entire "mysql packet" in its entirety from the network
        and return a MysqlPacket type that represents the results.
        """
        packet = packet_type(self)
        packet.check_error()
        return packet

    def _read_bytes(self, num_bytes):
        while True:
            try:
                data = self._rfile.read(num_bytes)
                break
            except (IOError, OSError) as e:
                if e.errno == errno.EINTR:
                    continue
                raise OperationalError(
                        2013, "Lost connection to MySQL server during query (%r)" % (e,))
        if len(data) < num_bytes:
            raise OperationalError(2013,
                    "Lost connection to MySQL server during query")
        return data

    def _write_bytes(self, data):
        try:
            self.socket.sendall(data)
        except IOError as e:
            raise OperationalError(2006, "MySQL server has gone away (%r)" % (e,))

    def _read_query_result(self, unbuffered=False):
        if unbuffered:
            try:
                result = MySQLResult(self)
                result.init_unbuffered_query()
            except:
                result.unbuffered_active = False
                result.connection = None
                raise
        else:
            result = MySQLResult(self)
            result.read()
        self._result = result
        if result.server_status is not None:
            self.server_status = result.server_status
        return result.affected_rows

    def insert_id(self):
        if self._result:
            return self._result.insert_id
        else:
            return 0

    def _execute_command(self, command, sql):
        if not self.socket:
            raise InterfaceError("(0, '')")

        # If the last query was unbuffered, make sure it finishes before
        # sending new commands
        if self._result is not None and self._result.unbuffered_active:
            self._result._finish_unbuffered_query()

        if isinstance(sql, text_type):
            sql = sql.encode(self.encoding)

        chunk_size = min(MAX_PACKET_LEN, len(sql) + 1)  # +1 is for command

        prelude = struct.pack('<i', chunk_size) + int2byte(command)
        self._write_bytes(prelude + sql[:chunk_size-1])
        if DEBUG: dump_packet(prelude + sql)

        if chunk_size < MAX_PACKET_LEN:
            return

        seq_id = 1
        sql = sql[chunk_size-1:]
        while True:
            chunk_size = min(MAX_PACKET_LEN, len(sql))
            prelude = struct.pack('<i', chunk_size)[:3]
            data = prelude + int2byte(seq_id%256) + sql[:chunk_size]
            self._write_bytes(data)
            if DEBUG: dump_packet(data)
            sql = sql[chunk_size:]
            if not sql and chunk_size < MAX_PACKET_LEN:
                break
            seq_id += 1

    def _request_authentication(self):
        self.client_flag |= CAPABILITIES
        if self.server_version.startswith('5'):
            self.client_flag |= MULTI_RESULTS

        if self.user is None:
            raise ValueError("Did not specify a username")

        charset_id = charset_by_name(self.charset).id
        if isinstance(self.user, text_type):
            self.user = self.user.encode(self.encoding)

        data_init = struct.pack('<i', self.client_flag) + struct.pack("<I", 1) + \
                     int2byte(charset_id) + int2byte(0)*23

        next_packet = 1

        if self.ssl:
            data = pack_int24(len(data_init)) + int2byte(next_packet) + data_init
            next_packet += 1

            if DEBUG: dump_packet(data)

            self._write_bytes(data)
            self.socket = ssl.wrap_socket(self.socket, keyfile=self.key,
                                          certfile=self.cert,
                                          ssl_version=ssl.PROTOCOL_TLSv1,
                                          cert_reqs=ssl.CERT_REQUIRED,
                                          ca_certs=self.ca)
            self._rfile = _makefile(self.socket, 'rb')

        data = data_init + self.user + b'\0' + \
            _scramble(self.password.encode('latin1'), self.salt)

        if self.db:
            if isinstance(self.db, text_type):
                self.db = self.db.encode(self.encoding)
            data += self.db + int2byte(0)

        data = pack_int24(len(data)) + int2byte(next_packet) + data
        next_packet += 2

        if DEBUG: dump_packet(data)

        self._write_bytes(data)

        auth_packet = MysqlPacket(self)
        auth_packet.check_error()
        if DEBUG: auth_packet.dump()

        # if old_passwords is enabled the packet will be 1 byte long and
        # have the octet 254

        if auth_packet.is_eof_packet():
            # send legacy handshake
            data = _scramble_323(self.password.encode('latin1'), self.salt) + b'\0'
            data = pack_int24(len(data)) + int2byte(next_packet) + data

            self._write_bytes(data)
            auth_packet = MysqlPacket(self)
            auth_packet.check_error()
            if DEBUG: auth_packet.dump()

    # _mysql support
    def thread_id(self):
        return self.server_thread_id[0]

    def character_set_name(self):
        return self.charset

    def get_host_info(self):
        return self.host_info

    def get_proto_info(self):
        return self.protocol_version

    def _get_server_information(self):
        i = 0
        packet = MysqlPacket(self)
        packet.check_error()
        data = packet.get_all_data()

        if DEBUG: dump_packet(data)
        self.protocol_version = byte2int(data[i:i+1])
        i += 1

        server_end = data.find(int2byte(0), i)
        self.server_version = data[i:server_end].decode('latin1')
        i = server_end + 1

        self.server_thread_id = struct.unpack('<I', data[i:i+4])
        i += 4

        self.salt = data[i:i+8]
        i += 9  # 8 + 1(filler)

        self.server_capabilities = struct.unpack('<H', data[i:i+2])[0]
        i += 2

        if len(data) >= i + 6:
            lang, stat, cap_h, salt_len = struct.unpack('<BHHB', data[i:i+6])
            i += 6
            self.server_language = lang
            self.server_charset = charset_by_id(lang).name

            self.server_status = stat
            if DEBUG: print("server_status: %x" % stat)

            self.server_capabilities |= cap_h << 16
            if DEBUG: print("salt_len:", salt_len)
            salt_len = max(12, salt_len - 9)

        # reserved
        i += 10

        if len(data) >= i + salt_len:
            self.salt += data[i:i+salt_len] # salt_len includes auth_plugin_data_part_1 and filler
        #TODO: AUTH PLUGIN NAME may appeare here.

    def get_server_info(self):
        return self.server_version

    Warning = Warning
    Error = Error
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError


# TODO: move OK and EOF packet parsing/logic into a proper subclass
#       of MysqlPacket like has been done with FieldDescriptorPacket.
class MySQLResult(object):

    def __init__(self, connection):
        self.connection = connection
        self.affected_rows = None
        self.insert_id = None
        self.server_status = None
        self.warning_count = 0
        self.message = None
        self.field_count = 0
        self.description = None
        self.rows = None
        self.has_next = None
        self.unbuffered_active = False

    def __del__(self):
        if self.unbuffered_active:
            self._finish_unbuffered_query()

    def read(self):
        try:
            first_packet = self.connection._read_packet()

            # TODO: use classes for different packet types?
            if first_packet.is_ok_packet():
                self._read_ok_packet(first_packet)
            else:
                self._read_result_packet(first_packet)
        finally:
            self.connection = False

    def init_unbuffered_query(self):
        self.unbuffered_active = True
        first_packet = self.connection._read_packet()

        if first_packet.is_ok_packet():
            self._read_ok_packet(first_packet)
            self.unbuffered_active = False
            self.connection = None
        else:
            self.field_count = first_packet.read_length_encoded_integer()
            self._get_descriptions()

            # Apparently, MySQLdb picks this number because it's the maximum
            # value of a 64bit unsigned integer. Since we're emulating MySQLdb,
            # we set it to this instead of None, which would be preferred.
            self.affected_rows = 18446744073709551615

    def _read_ok_packet(self, first_packet):
        ok_packet = OKPacketWrapper(first_packet)
        self.affected_rows = ok_packet.affected_rows
        self.insert_id = ok_packet.insert_id
        self.server_status = ok_packet.server_status
        self.warning_count = ok_packet.warning_count
        self.message = ok_packet.message
        self.has_next = ok_packet.has_next

    def _check_packet_is_eof(self, packet):
        if packet.is_eof_packet():
            eof_packet = EOFPacketWrapper(packet)
            self.warning_count = eof_packet.warning_count
            self.has_next = eof_packet.has_next
            return True
        return False

    def _read_result_packet(self, first_packet):
        self.field_count = first_packet.read_length_encoded_integer()
        self._get_descriptions()
        self._read_rowdata_packet()

    def _read_rowdata_packet_unbuffered(self):
        # Check if in an active query
        if not self.unbuffered_active:
            return

        # EOF
        packet = self.connection._read_packet()
        if self._check_packet_is_eof(packet):
            self.unbuffered_active = False
            self.connection = None
            self.rows = None
            return

        row = self._read_row_from_packet(packet)
        self.affected_rows = 1
        self.rows = (row,)  # rows should tuple of row for MySQL-python compatibility.
        return row

    def _finish_unbuffered_query(self):
        # After much reading on the MySQL protocol, it appears that there is,
        # in fact, no way to stop MySQL from sending all the data after
        # executing a query, so we just spin, and wait for an EOF packet.
        while self.unbuffered_active:
            packet = self.connection._read_packet()
            if self._check_packet_is_eof(packet):
                self.unbuffered_active = False
                self.connection = None  # release reference to kill cyclic reference.

    def _read_rowdata_packet(self):
        """Read a rowdata packet for each data row in the result set."""
        rows = []
        while True:
            packet = self.connection._read_packet()
            if self._check_packet_is_eof(packet):
                self.connection = None  # release reference to kill cyclic reference.
                break
            rows.append(self._read_row_from_packet(packet))

        self.affected_rows = len(rows)
        self.rows = tuple(rows)

    def _read_row_from_packet(self, packet):
        use_unicode = self.connection.use_unicode
        row = []
        for field in self.fields:
            data = packet.read_length_coded_string()
            if data is not None:
                field_type = field.type_code
                if use_unicode:
                    if field_type in TEXT_TYPES:
                        charset = charset_by_id(field.charsetnr)
                        if use_unicode and not charset.is_binary:
                            # TEXTs with charset=binary means BINARY types.
                            data = data.decode(charset.encoding)
                    else:
                        data = data.decode()

                converter = self.connection.decoders.get(field_type)
                if DEBUG: print("DEBUG: field={}, converter={}".format(field, converter))
                if DEBUG: print("DEBUG: DATA = ", data)
                if converter is not None:
                    data = converter(data)
            row.append(data)
        return tuple(row)

    def _get_descriptions(self):
        """Read a column descriptor packet for each column in the result."""
        self.fields = []
        description = []
        for i in range_type(self.field_count):
            field = self.connection._read_packet(FieldDescriptorPacket)
            self.fields.append(field)
            description.append(field.description())

        eof_packet = self.connection._read_packet()
        assert eof_packet.is_eof_packet(), 'Protocol error, expecting EOF'
        self.description = tuple(description)

########NEW FILE########
__FILENAME__ = CLIENT

LONG_PASSWORD = 1
FOUND_ROWS = 1 << 1
LONG_FLAG = 1 << 2
CONNECT_WITH_DB = 1 << 3
NO_SCHEMA = 1 << 4
COMPRESS = 1 << 5
ODBC = 1 << 6
LOCAL_FILES = 1 << 7
IGNORE_SPACE = 1 << 8
PROTOCOL_41 = 1 << 9
INTERACTIVE = 1 << 10
SSL = 1 << 11
IGNORE_SIGPIPE = 1 << 12
TRANSACTIONS  = 1 << 13
SECURE_CONNECTION = 1 << 15
MULTI_STATEMENTS = 1 << 16
MULTI_RESULTS = 1 << 17
CAPABILITIES = LONG_PASSWORD|LONG_FLAG|TRANSACTIONS| \
    PROTOCOL_41|SECURE_CONNECTION

########NEW FILE########
__FILENAME__ = COMMAND

COM_SLEEP = 0x00
COM_QUIT = 0x01
COM_INIT_DB = 0x02
COM_QUERY = 0x03
COM_FIELD_LIST = 0x04
COM_CREATE_DB = 0x05
COM_DROP_DB = 0x06
COM_REFRESH = 0x07
COM_SHUTDOWN = 0x08
COM_STATISTICS = 0x09
COM_PROCESS_INFO = 0x0a
COM_CONNECT = 0x0b
COM_PROCESS_KILL = 0x0c
COM_DEBUG = 0x0d
COM_PING = 0x0e
COM_TIME = 0x0f
COM_DELAYED_INSERT = 0x10
COM_CHANGE_USER = 0x11
COM_BINLOG_DUMP = 0x12
COM_TABLE_DUMP = 0x13
COM_CONNECT_OUT = 0x14
COM_REGISTER_SLAVE = 0x15

########NEW FILE########
__FILENAME__ = ER

ERROR_FIRST = 1000
HASHCHK = 1000
NISAMCHK = 1001
NO = 1002
YES = 1003
CANT_CREATE_FILE = 1004
CANT_CREATE_TABLE = 1005
CANT_CREATE_DB = 1006
DB_CREATE_EXISTS = 1007
DB_DROP_EXISTS = 1008
DB_DROP_DELETE = 1009
DB_DROP_RMDIR = 1010
CANT_DELETE_FILE = 1011
CANT_FIND_SYSTEM_REC = 1012
CANT_GET_STAT = 1013
CANT_GET_WD = 1014
CANT_LOCK = 1015
CANT_OPEN_FILE = 1016
FILE_NOT_FOUND = 1017
CANT_READ_DIR = 1018
CANT_SET_WD = 1019
CHECKREAD = 1020
DISK_FULL = 1021
DUP_KEY = 1022
ERROR_ON_CLOSE = 1023
ERROR_ON_READ = 1024
ERROR_ON_RENAME = 1025
ERROR_ON_WRITE = 1026
FILE_USED = 1027
FILSORT_ABORT = 1028
FORM_NOT_FOUND = 1029
GET_ERRNO = 1030
ILLEGAL_HA = 1031
KEY_NOT_FOUND = 1032
NOT_FORM_FILE = 1033
NOT_KEYFILE = 1034
OLD_KEYFILE = 1035
OPEN_AS_READONLY = 1036
OUTOFMEMORY = 1037
OUT_OF_SORTMEMORY = 1038
UNEXPECTED_EOF = 1039
CON_COUNT_ERROR = 1040
OUT_OF_RESOURCES = 1041
BAD_HOST_ERROR = 1042
HANDSHAKE_ERROR = 1043
DBACCESS_DENIED_ERROR = 1044
ACCESS_DENIED_ERROR = 1045
NO_DB_ERROR = 1046
UNKNOWN_COM_ERROR = 1047
BAD_NULL_ERROR = 1048
BAD_DB_ERROR = 1049
TABLE_EXISTS_ERROR = 1050
BAD_TABLE_ERROR = 1051
NON_UNIQ_ERROR = 1052
SERVER_SHUTDOWN = 1053
BAD_FIELD_ERROR = 1054
WRONG_FIELD_WITH_GROUP = 1055
WRONG_GROUP_FIELD = 1056
WRONG_SUM_SELECT = 1057
WRONG_VALUE_COUNT = 1058
TOO_LONG_IDENT = 1059
DUP_FIELDNAME = 1060
DUP_KEYNAME = 1061
DUP_ENTRY = 1062
WRONG_FIELD_SPEC = 1063
PARSE_ERROR = 1064
EMPTY_QUERY = 1065
NONUNIQ_TABLE = 1066
INVALID_DEFAULT = 1067
MULTIPLE_PRI_KEY = 1068
TOO_MANY_KEYS = 1069
TOO_MANY_KEY_PARTS = 1070
TOO_LONG_KEY = 1071
KEY_COLUMN_DOES_NOT_EXITS = 1072
BLOB_USED_AS_KEY = 1073
TOO_BIG_FIELDLENGTH = 1074
WRONG_AUTO_KEY = 1075
READY = 1076
NORMAL_SHUTDOWN = 1077
GOT_SIGNAL = 1078
SHUTDOWN_COMPLETE = 1079
FORCING_CLOSE = 1080
IPSOCK_ERROR = 1081
NO_SUCH_INDEX = 1082
WRONG_FIELD_TERMINATORS = 1083
BLOBS_AND_NO_TERMINATED = 1084
TEXTFILE_NOT_READABLE = 1085
FILE_EXISTS_ERROR = 1086
LOAD_INFO = 1087
ALTER_INFO = 1088
WRONG_SUB_KEY = 1089
CANT_REMOVE_ALL_FIELDS = 1090
CANT_DROP_FIELD_OR_KEY = 1091
INSERT_INFO = 1092
UPDATE_TABLE_USED = 1093
NO_SUCH_THREAD = 1094
KILL_DENIED_ERROR = 1095
NO_TABLES_USED = 1096
TOO_BIG_SET = 1097
NO_UNIQUE_LOGFILE = 1098
TABLE_NOT_LOCKED_FOR_WRITE = 1099
TABLE_NOT_LOCKED = 1100
BLOB_CANT_HAVE_DEFAULT = 1101
WRONG_DB_NAME = 1102
WRONG_TABLE_NAME = 1103
TOO_BIG_SELECT = 1104
UNKNOWN_ERROR = 1105
UNKNOWN_PROCEDURE = 1106
WRONG_PARAMCOUNT_TO_PROCEDURE = 1107
WRONG_PARAMETERS_TO_PROCEDURE = 1108
UNKNOWN_TABLE = 1109
FIELD_SPECIFIED_TWICE = 1110
INVALID_GROUP_FUNC_USE = 1111
UNSUPPORTED_EXTENSION = 1112
TABLE_MUST_HAVE_COLUMNS = 1113
RECORD_FILE_FULL = 1114
UNKNOWN_CHARACTER_SET = 1115
TOO_MANY_TABLES = 1116
TOO_MANY_FIELDS = 1117
TOO_BIG_ROWSIZE = 1118
STACK_OVERRUN = 1119
WRONG_OUTER_JOIN = 1120
NULL_COLUMN_IN_INDEX = 1121
CANT_FIND_UDF = 1122
CANT_INITIALIZE_UDF = 1123
UDF_NO_PATHS = 1124
UDF_EXISTS = 1125
CANT_OPEN_LIBRARY = 1126
CANT_FIND_DL_ENTRY = 1127
FUNCTION_NOT_DEFINED = 1128
HOST_IS_BLOCKED = 1129
HOST_NOT_PRIVILEGED = 1130
PASSWORD_ANONYMOUS_USER = 1131
PASSWORD_NOT_ALLOWED = 1132
PASSWORD_NO_MATCH = 1133
UPDATE_INFO = 1134
CANT_CREATE_THREAD = 1135
WRONG_VALUE_COUNT_ON_ROW = 1136
CANT_REOPEN_TABLE = 1137
INVALID_USE_OF_NULL = 1138
REGEXP_ERROR = 1139
MIX_OF_GROUP_FUNC_AND_FIELDS = 1140
NONEXISTING_GRANT = 1141
TABLEACCESS_DENIED_ERROR = 1142
COLUMNACCESS_DENIED_ERROR = 1143
ILLEGAL_GRANT_FOR_TABLE = 1144
GRANT_WRONG_HOST_OR_USER = 1145
NO_SUCH_TABLE = 1146
NONEXISTING_TABLE_GRANT = 1147
NOT_ALLOWED_COMMAND = 1148
SYNTAX_ERROR = 1149
DELAYED_CANT_CHANGE_LOCK = 1150
TOO_MANY_DELAYED_THREADS = 1151
ABORTING_CONNECTION = 1152
NET_PACKET_TOO_LARGE = 1153
NET_READ_ERROR_FROM_PIPE = 1154
NET_FCNTL_ERROR = 1155
NET_PACKETS_OUT_OF_ORDER = 1156
NET_UNCOMPRESS_ERROR = 1157
NET_READ_ERROR = 1158
NET_READ_INTERRUPTED = 1159
NET_ERROR_ON_WRITE = 1160
NET_WRITE_INTERRUPTED = 1161
TOO_LONG_STRING = 1162
TABLE_CANT_HANDLE_BLOB = 1163
TABLE_CANT_HANDLE_AUTO_INCREMENT = 1164
DELAYED_INSERT_TABLE_LOCKED = 1165
WRONG_COLUMN_NAME = 1166
WRONG_KEY_COLUMN = 1167
WRONG_MRG_TABLE = 1168
DUP_UNIQUE = 1169
BLOB_KEY_WITHOUT_LENGTH = 1170
PRIMARY_CANT_HAVE_NULL = 1171
TOO_MANY_ROWS = 1172
REQUIRES_PRIMARY_KEY = 1173
NO_RAID_COMPILED = 1174
UPDATE_WITHOUT_KEY_IN_SAFE_MODE = 1175
KEY_DOES_NOT_EXITS = 1176
CHECK_NO_SUCH_TABLE = 1177
CHECK_NOT_IMPLEMENTED = 1178
CANT_DO_THIS_DURING_AN_TRANSACTION = 1179
ERROR_DURING_COMMIT = 1180
ERROR_DURING_ROLLBACK = 1181
ERROR_DURING_FLUSH_LOGS = 1182
ERROR_DURING_CHECKPOINT = 1183
NEW_ABORTING_CONNECTION = 1184
DUMP_NOT_IMPLEMENTED = 1185
FLUSH_MASTER_BINLOG_CLOSED = 1186
INDEX_REBUILD = 1187
MASTER = 1188
MASTER_NET_READ = 1189
MASTER_NET_WRITE = 1190
FT_MATCHING_KEY_NOT_FOUND = 1191
LOCK_OR_ACTIVE_TRANSACTION = 1192
UNKNOWN_SYSTEM_VARIABLE = 1193
CRASHED_ON_USAGE = 1194
CRASHED_ON_REPAIR = 1195
WARNING_NOT_COMPLETE_ROLLBACK = 1196
TRANS_CACHE_FULL = 1197
SLAVE_MUST_STOP = 1198
SLAVE_NOT_RUNNING = 1199
BAD_SLAVE = 1200
MASTER_INFO = 1201
SLAVE_THREAD = 1202
TOO_MANY_USER_CONNECTIONS = 1203
SET_CONSTANTS_ONLY = 1204
LOCK_WAIT_TIMEOUT = 1205
LOCK_TABLE_FULL = 1206
READ_ONLY_TRANSACTION = 1207
DROP_DB_WITH_READ_LOCK = 1208
CREATE_DB_WITH_READ_LOCK = 1209
WRONG_ARGUMENTS = 1210
NO_PERMISSION_TO_CREATE_USER = 1211
UNION_TABLES_IN_DIFFERENT_DIR = 1212
LOCK_DEADLOCK = 1213
TABLE_CANT_HANDLE_FT = 1214
CANNOT_ADD_FOREIGN = 1215
NO_REFERENCED_ROW = 1216
ROW_IS_REFERENCED = 1217
CONNECT_TO_MASTER = 1218
QUERY_ON_MASTER = 1219
ERROR_WHEN_EXECUTING_COMMAND = 1220
WRONG_USAGE = 1221
WRONG_NUMBER_OF_COLUMNS_IN_SELECT = 1222
CANT_UPDATE_WITH_READLOCK = 1223
MIXING_NOT_ALLOWED = 1224
DUP_ARGUMENT = 1225
USER_LIMIT_REACHED = 1226
SPECIFIC_ACCESS_DENIED_ERROR = 1227
LOCAL_VARIABLE = 1228
GLOBAL_VARIABLE = 1229
NO_DEFAULT = 1230
WRONG_VALUE_FOR_VAR = 1231
WRONG_TYPE_FOR_VAR = 1232
VAR_CANT_BE_READ = 1233
CANT_USE_OPTION_HERE = 1234
NOT_SUPPORTED_YET = 1235
MASTER_FATAL_ERROR_READING_BINLOG = 1236
SLAVE_IGNORED_TABLE = 1237
INCORRECT_GLOBAL_LOCAL_VAR = 1238
WRONG_FK_DEF = 1239
KEY_REF_DO_NOT_MATCH_TABLE_REF = 1240
OPERAND_COLUMNS = 1241
SUBQUERY_NO_1_ROW = 1242
UNKNOWN_STMT_HANDLER = 1243
CORRUPT_HELP_DB = 1244
CYCLIC_REFERENCE = 1245
AUTO_CONVERT = 1246
ILLEGAL_REFERENCE = 1247
DERIVED_MUST_HAVE_ALIAS = 1248
SELECT_REDUCED = 1249
TABLENAME_NOT_ALLOWED_HERE = 1250
NOT_SUPPORTED_AUTH_MODE = 1251
SPATIAL_CANT_HAVE_NULL = 1252
COLLATION_CHARSET_MISMATCH = 1253
SLAVE_WAS_RUNNING = 1254
SLAVE_WAS_NOT_RUNNING = 1255
TOO_BIG_FOR_UNCOMPRESS = 1256
ZLIB_Z_MEM_ERROR = 1257
ZLIB_Z_BUF_ERROR = 1258
ZLIB_Z_DATA_ERROR = 1259
CUT_VALUE_GROUP_CONCAT = 1260
WARN_TOO_FEW_RECORDS = 1261
WARN_TOO_MANY_RECORDS = 1262
WARN_NULL_TO_NOTNULL = 1263
WARN_DATA_OUT_OF_RANGE = 1264
WARN_DATA_TRUNCATED = 1265
WARN_USING_OTHER_HANDLER = 1266
CANT_AGGREGATE_2COLLATIONS = 1267
DROP_USER = 1268
REVOKE_GRANTS = 1269
CANT_AGGREGATE_3COLLATIONS = 1270
CANT_AGGREGATE_NCOLLATIONS = 1271
VARIABLE_IS_NOT_STRUCT = 1272
UNKNOWN_COLLATION = 1273
SLAVE_IGNORED_SSL_PARAMS = 1274
SERVER_IS_IN_SECURE_AUTH_MODE = 1275
WARN_FIELD_RESOLVED = 1276
BAD_SLAVE_UNTIL_COND = 1277
MISSING_SKIP_SLAVE = 1278
UNTIL_COND_IGNORED = 1279
WRONG_NAME_FOR_INDEX = 1280
WRONG_NAME_FOR_CATALOG = 1281
WARN_QC_RESIZE = 1282
BAD_FT_COLUMN = 1283
UNKNOWN_KEY_CACHE = 1284
WARN_HOSTNAME_WONT_WORK = 1285
UNKNOWN_STORAGE_ENGINE = 1286
WARN_DEPRECATED_SYNTAX = 1287
NON_UPDATABLE_TABLE = 1288
FEATURE_DISABLED = 1289
OPTION_PREVENTS_STATEMENT = 1290
DUPLICATED_VALUE_IN_TYPE = 1291
TRUNCATED_WRONG_VALUE = 1292
TOO_MUCH_AUTO_TIMESTAMP_COLS = 1293
INVALID_ON_UPDATE = 1294
UNSUPPORTED_PS = 1295
GET_ERRMSG = 1296
GET_TEMPORARY_ERRMSG = 1297
UNKNOWN_TIME_ZONE = 1298
WARN_INVALID_TIMESTAMP = 1299
INVALID_CHARACTER_STRING = 1300
WARN_ALLOWED_PACKET_OVERFLOWED = 1301
CONFLICTING_DECLARATIONS = 1302
SP_NO_RECURSIVE_CREATE = 1303
SP_ALREADY_EXISTS = 1304
SP_DOES_NOT_EXIST = 1305
SP_DROP_FAILED = 1306
SP_STORE_FAILED = 1307
SP_LILABEL_MISMATCH = 1308
SP_LABEL_REDEFINE = 1309
SP_LABEL_MISMATCH = 1310
SP_UNINIT_VAR = 1311
SP_BADSELECT = 1312
SP_BADRETURN = 1313
SP_BADSTATEMENT = 1314
UPDATE_LOG_DEPRECATED_IGNORED = 1315
UPDATE_LOG_DEPRECATED_TRANSLATED = 1316
QUERY_INTERRUPTED = 1317
SP_WRONG_NO_OF_ARGS = 1318
SP_COND_MISMATCH = 1319
SP_NORETURN = 1320
SP_NORETURNEND = 1321
SP_BAD_CURSOR_QUERY = 1322
SP_BAD_CURSOR_SELECT = 1323
SP_CURSOR_MISMATCH = 1324
SP_CURSOR_ALREADY_OPEN = 1325
SP_CURSOR_NOT_OPEN = 1326
SP_UNDECLARED_VAR = 1327
SP_WRONG_NO_OF_FETCH_ARGS = 1328
SP_FETCH_NO_DATA = 1329
SP_DUP_PARAM = 1330
SP_DUP_VAR = 1331
SP_DUP_COND = 1332
SP_DUP_CURS = 1333
SP_CANT_ALTER = 1334
SP_SUBSELECT_NYI = 1335
STMT_NOT_ALLOWED_IN_SF_OR_TRG = 1336
SP_VARCOND_AFTER_CURSHNDLR = 1337
SP_CURSOR_AFTER_HANDLER = 1338
SP_CASE_NOT_FOUND = 1339
FPARSER_TOO_BIG_FILE = 1340
FPARSER_BAD_HEADER = 1341
FPARSER_EOF_IN_COMMENT = 1342
FPARSER_ERROR_IN_PARAMETER = 1343
FPARSER_EOF_IN_UNKNOWN_PARAMETER = 1344
VIEW_NO_EXPLAIN = 1345
FRM_UNKNOWN_TYPE = 1346
WRONG_OBJECT = 1347
NONUPDATEABLE_COLUMN = 1348
VIEW_SELECT_DERIVED = 1349
VIEW_SELECT_CLAUSE = 1350
VIEW_SELECT_VARIABLE = 1351
VIEW_SELECT_TMPTABLE = 1352
VIEW_WRONG_LIST = 1353
WARN_VIEW_MERGE = 1354
WARN_VIEW_WITHOUT_KEY = 1355
VIEW_INVALID = 1356
SP_NO_DROP_SP = 1357
SP_GOTO_IN_HNDLR = 1358
TRG_ALREADY_EXISTS = 1359
TRG_DOES_NOT_EXIST = 1360
TRG_ON_VIEW_OR_TEMP_TABLE = 1361
TRG_CANT_CHANGE_ROW = 1362
TRG_NO_SUCH_ROW_IN_TRG = 1363
NO_DEFAULT_FOR_FIELD = 1364
DIVISION_BY_ZERO = 1365
TRUNCATED_WRONG_VALUE_FOR_FIELD = 1366
ILLEGAL_VALUE_FOR_TYPE = 1367
VIEW_NONUPD_CHECK = 1368
VIEW_CHECK_FAILED = 1369
PROCACCESS_DENIED_ERROR = 1370
RELAY_LOG_FAIL = 1371
PASSWD_LENGTH = 1372
UNKNOWN_TARGET_BINLOG = 1373
IO_ERR_LOG_INDEX_READ = 1374
BINLOG_PURGE_PROHIBITED = 1375
FSEEK_FAIL = 1376
BINLOG_PURGE_FATAL_ERR = 1377
LOG_IN_USE = 1378
LOG_PURGE_UNKNOWN_ERR = 1379
RELAY_LOG_INIT = 1380
NO_BINARY_LOGGING = 1381
RESERVED_SYNTAX = 1382
WSAS_FAILED = 1383
DIFF_GROUPS_PROC = 1384
NO_GROUP_FOR_PROC = 1385
ORDER_WITH_PROC = 1386
LOGGING_PROHIBIT_CHANGING_OF = 1387
NO_FILE_MAPPING = 1388
WRONG_MAGIC = 1389
PS_MANY_PARAM = 1390
KEY_PART_0 = 1391
VIEW_CHECKSUM = 1392
VIEW_MULTIUPDATE = 1393
VIEW_NO_INSERT_FIELD_LIST = 1394
VIEW_DELETE_MERGE_VIEW = 1395
CANNOT_USER = 1396
XAER_NOTA = 1397
XAER_INVAL = 1398
XAER_RMFAIL = 1399
XAER_OUTSIDE = 1400
XAER_RMERR = 1401
XA_RBROLLBACK = 1402
NONEXISTING_PROC_GRANT = 1403
PROC_AUTO_GRANT_FAIL = 1404
PROC_AUTO_REVOKE_FAIL = 1405
DATA_TOO_LONG = 1406
SP_BAD_SQLSTATE = 1407
STARTUP = 1408
LOAD_FROM_FIXED_SIZE_ROWS_TO_VAR = 1409
CANT_CREATE_USER_WITH_GRANT = 1410
WRONG_VALUE_FOR_TYPE = 1411
TABLE_DEF_CHANGED = 1412
SP_DUP_HANDLER = 1413
SP_NOT_VAR_ARG = 1414
SP_NO_RETSET = 1415
CANT_CREATE_GEOMETRY_OBJECT = 1416
FAILED_ROUTINE_BREAK_BINLOG = 1417
BINLOG_UNSAFE_ROUTINE = 1418
BINLOG_CREATE_ROUTINE_NEED_SUPER = 1419
EXEC_STMT_WITH_OPEN_CURSOR = 1420
STMT_HAS_NO_OPEN_CURSOR = 1421
COMMIT_NOT_ALLOWED_IN_SF_OR_TRG = 1422
NO_DEFAULT_FOR_VIEW_FIELD = 1423
SP_NO_RECURSION = 1424
TOO_BIG_SCALE = 1425
TOO_BIG_PRECISION = 1426
M_BIGGER_THAN_D = 1427
WRONG_LOCK_OF_SYSTEM_TABLE = 1428
CONNECT_TO_FOREIGN_DATA_SOURCE = 1429
QUERY_ON_FOREIGN_DATA_SOURCE = 1430
FOREIGN_DATA_SOURCE_DOESNT_EXIST = 1431
FOREIGN_DATA_STRING_INVALID_CANT_CREATE = 1432
FOREIGN_DATA_STRING_INVALID = 1433
CANT_CREATE_FEDERATED_TABLE = 1434
TRG_IN_WRONG_SCHEMA = 1435
STACK_OVERRUN_NEED_MORE = 1436
TOO_LONG_BODY = 1437
WARN_CANT_DROP_DEFAULT_KEYCACHE = 1438
TOO_BIG_DISPLAYWIDTH = 1439
XAER_DUPID = 1440
DATETIME_FUNCTION_OVERFLOW = 1441
CANT_UPDATE_USED_TABLE_IN_SF_OR_TRG = 1442
VIEW_PREVENT_UPDATE = 1443
PS_NO_RECURSION = 1444
SP_CANT_SET_AUTOCOMMIT = 1445
MALFORMED_DEFINER = 1446
VIEW_FRM_NO_USER = 1447
VIEW_OTHER_USER = 1448
NO_SUCH_USER = 1449
FORBID_SCHEMA_CHANGE = 1450
ROW_IS_REFERENCED_2 = 1451
NO_REFERENCED_ROW_2 = 1452
SP_BAD_VAR_SHADOW = 1453
TRG_NO_DEFINER = 1454
OLD_FILE_FORMAT = 1455
SP_RECURSION_LIMIT = 1456
SP_PROC_TABLE_CORRUPT = 1457
SP_WRONG_NAME = 1458
TABLE_NEEDS_UPGRADE = 1459
SP_NO_AGGREGATE = 1460
MAX_PREPARED_STMT_COUNT_REACHED = 1461
VIEW_RECURSIVE = 1462
NON_GROUPING_FIELD_USED = 1463
TABLE_CANT_HANDLE_SPKEYS = 1464
NO_TRIGGERS_ON_SYSTEM_SCHEMA = 1465
USERNAME = 1466
HOSTNAME = 1467
WRONG_STRING_LENGTH = 1468
ERROR_LAST = 1468

########NEW FILE########
__FILENAME__ = FIELD_TYPE


DECIMAL = 0
TINY = 1
SHORT = 2
LONG = 3
FLOAT = 4
DOUBLE = 5
NULL = 6
TIMESTAMP = 7
LONGLONG = 8
INT24 = 9
DATE = 10
TIME = 11
DATETIME = 12
YEAR = 13
NEWDATE = 14
VARCHAR = 15
BIT = 16
NEWDECIMAL = 246
ENUM = 247
SET = 248
TINY_BLOB = 249
MEDIUM_BLOB = 250
LONG_BLOB = 251
BLOB = 252
VAR_STRING = 253
STRING = 254
GEOMETRY = 255

CHAR = TINY
INTERVAL = ENUM

########NEW FILE########
__FILENAME__ = FLAG
NOT_NULL = 1
PRI_KEY = 2
UNIQUE_KEY = 4
MULTIPLE_KEY = 8
BLOB = 16
UNSIGNED = 32
ZEROFILL = 64
BINARY = 128
ENUM = 256
AUTO_INCREMENT = 512
TIMESTAMP = 1024
SET = 2048
PART_KEY = 16384
GROUP = 32767
UNIQUE = 65536

########NEW FILE########
__FILENAME__ = SERVER_STATUS

SERVER_STATUS_IN_TRANS = 1
SERVER_STATUS_AUTOCOMMIT = 2
SERVER_MORE_RESULTS_EXISTS = 8
SERVER_QUERY_NO_GOOD_INDEX_USED = 16
SERVER_QUERY_NO_INDEX_USED = 32
SERVER_STATUS_CURSOR_EXISTS = 64
SERVER_STATUS_LAST_ROW_SENT = 128
SERVER_STATUS_DB_DROPPED = 256
SERVER_STATUS_NO_BACKSLASH_ESCAPES = 512
SERVER_STATUS_METADATA_CHANGED = 1024

########NEW FILE########
__FILENAME__ = converters
from ._compat import PY2, text_type, long_type, JYTHON, IRONPYTHON

import sys
import binascii
import datetime
from decimal import Decimal
import re
import time

from .constants import FIELD_TYPE, FLAG
from .charset import charset_by_id, charset_to_encoding


ESCAPE_REGEX = re.compile(r"[\0\n\r\032\'\"\\]")
ESCAPE_MAP = {'\0': '\\0', '\n': '\\n', '\r': '\\r', '\032': '\\Z',
              '\'': '\\\'', '"': '\\"', '\\': '\\\\'}


def escape_item(val, charset):
    if type(val) in [tuple, list, set]:
        return escape_sequence(val, charset)
    if type(val) is dict:
        return escape_dict(val, charset)
    encoder = encoders[type(val)]
    val = encoder(val)
    if type(val) in [str, int, text_type]:
        return val
    return val

def escape_dict(val, charset):
    n = {}
    for k, v in val.items():
        quoted = escape_item(v, charset)
        n[k] = quoted
    return n

def escape_sequence(val, charset):
    n = []
    for item in val:
        quoted = escape_item(item, charset)
        n.append(quoted)
    return "(" + ",".join(n) + ")"

def escape_set(val, charset):
    val = map(lambda x: escape_item(x, charset), val)
    return ','.join(val)

def escape_bool(value):
    return str(int(value))

def escape_object(value):
    return str(value)

def escape_int(value):
    return str(value)


def escape_float(value):
    return ('%.15g' % value)

def escape_string(value):
    return ("%s" % (ESCAPE_REGEX.sub(
            lambda match: ESCAPE_MAP.get(match.group(0)), value),))

def escape_str(value):
    return "'%s'" % escape_string(value)

def escape_unicode(value):
    return escape_str(value)

def escape_bytes(value):
    return "x'%s'" % binascii.hexlify(value).decode(sys.getdefaultencoding())

def escape_None(value):
    return 'NULL'

def escape_timedelta(obj):
    seconds = int(obj.seconds) % 60
    minutes = int(obj.seconds // 60) % 60
    hours = int(obj.seconds // 3600) % 24 + int(obj.days) * 24
    return escape_str('%02d:%02d:%02d' % (hours, minutes, seconds))

def escape_time(obj):
    s = "%02d:%02d:%02d" % (int(obj.hour), int(obj.minute),
                            int(obj.second))
    if obj.microsecond:
        s += ".{0:06}".format(obj.microsecond)

    return escape_str(s)

def escape_datetime(obj):
    return escape_str(obj.isoformat(' '))

def escape_date(obj):
    return escape_str(obj.isoformat())

def escape_struct_time(obj):
    return escape_datetime(datetime.datetime(*obj[:6]))

def convert_datetime(obj):
    """Returns a DATETIME or TIMESTAMP column value as a datetime object:

      >>> datetime_or_None('2007-02-25 23:06:20')
      datetime.datetime(2007, 2, 25, 23, 6, 20)
      >>> datetime_or_None('2007-02-25T23:06:20')
      datetime.datetime(2007, 2, 25, 23, 6, 20)

    Illegal values are returned as None:

      >>> datetime_or_None('2007-02-31T23:06:20') is None
      True
      >>> datetime_or_None('0000-00-00 00:00:00') is None
      True

    """
    if ' ' in obj:
        sep = ' '
    elif 'T' in obj:
        sep = 'T'
    else:
        return convert_date(obj)

    try:
        ymd, hms = obj.split(sep, 1)
        usecs = '0'
        if '.' in hms:
            hms, usecs = hms.split('.')
        usecs = float('0.' + usecs) * 1e6
        return datetime.datetime(*[ int(x) for x in ymd.split('-')+hms.split(':')+[usecs] ])
    except ValueError:
        return convert_date(obj)


def convert_timedelta(obj):
    """Returns a TIME column as a timedelta object:

      >>> timedelta_or_None('25:06:17')
      datetime.timedelta(1, 3977)
      >>> timedelta_or_None('-25:06:17')
      datetime.timedelta(-2, 83177)

    Illegal values are returned as None:

      >>> timedelta_or_None('random crap') is None
      True

    Note that MySQL always returns TIME columns as (+|-)HH:MM:SS, but
    can accept values as (+|-)DD HH:MM:SS. The latter format will not
    be parsed correctly by this function.
    """
    try:
        microseconds = 0
        if "." in obj:
            (obj, tail) = obj.split('.')
            microseconds = float('0.' + tail) * 1e6
        hours, minutes, seconds = obj.split(':')
        tdelta = datetime.timedelta(
            hours = int(hours),
            minutes = int(minutes),
            seconds = int(seconds),
            microseconds = int(microseconds)
            )
        return tdelta
    except ValueError:
        return None

def convert_time(obj):
    """Returns a TIME column as a time object:

      >>> time_or_None('15:06:17')
      datetime.time(15, 6, 17)

    Illegal values are returned as None:

      >>> time_or_None('-25:06:17') is None
      True
      >>> time_or_None('random crap') is None
      True

    Note that MySQL always returns TIME columns as (+|-)HH:MM:SS, but
    can accept values as (+|-)DD HH:MM:SS. The latter format will not
    be parsed correctly by this function.

    Also note that MySQL's TIME column corresponds more closely to
    Python's timedelta and not time. However if you want TIME columns
    to be treated as time-of-day and not a time offset, then you can
    use set this function as the converter for FIELD_TYPE.TIME.
    """
    try:
        microseconds = 0
        if "." in obj:
            (obj, tail) = obj.split('.')
            microseconds = float('0.' + tail) * 1e6
        hours, minutes, seconds = obj.split(':')
        return datetime.time(hour=int(hours), minute=int(minutes),
                             second=int(seconds), microsecond=int(microseconds))
    except ValueError:
        return None

def convert_date(obj):
    """Returns a DATE column as a date object:

      >>> date_or_None('2007-02-26')
      datetime.date(2007, 2, 26)

    Illegal values are returned as None:

      >>> date_or_None('2007-02-31') is None
      True
      >>> date_or_None('0000-00-00') is None
      True

    """
    try:
        return datetime.date(*[ int(x) for x in obj.split('-', 2) ])
    except ValueError:
        return None


def convert_mysql_timestamp(timestamp):
    """Convert a MySQL TIMESTAMP to a Timestamp object.

    MySQL >= 4.1 returns TIMESTAMP in the same format as DATETIME:

      >>> mysql_timestamp_converter('2007-02-25 22:32:17')
      datetime.datetime(2007, 2, 25, 22, 32, 17)

    MySQL < 4.1 uses a big string of numbers:

      >>> mysql_timestamp_converter('20070225223217')
      datetime.datetime(2007, 2, 25, 22, 32, 17)

    Illegal values are returned as None:

      >>> mysql_timestamp_converter('2007-02-31 22:32:17') is None
      True
      >>> mysql_timestamp_converter('00000000000000') is None
      True

    """
    if timestamp[4] == '-':
        return convert_datetime(timestamp)
    timestamp += "0"*(14-len(timestamp)) # padding
    year, month, day, hour, minute, second = \
        int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]), \
        int(timestamp[8:10]), int(timestamp[10:12]), int(timestamp[12:14])
    try:
        return datetime.datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None

def convert_set(s):
    return set(s.split(","))

def convert_bit(b):
    #b = "\x00" * (8 - len(b)) + b # pad w/ zeroes
    #return struct.unpack(">Q", b)[0]
    #
    # the snippet above is right, but MySQLdb doesn't process bits,
    # so we shouldn't either
    return b

def convert_characters(connection, field, data):
    field_charset = charset_by_id(field.charsetnr).name
    encoding = charset_to_encoding(field_charset)
    if field.flags & FLAG.SET:
        return convert_set(data.decode(encoding))
    if field.flags & FLAG.BINARY:
        return data

    if connection.use_unicode:
        data = data.decode(encoding)
    elif connection.charset != field_charset:
        data = data.decode(encoding)
        data = data.encode(connection.encoding)
    return data

encoders = {
        bool: escape_bool,
        int: escape_int,
        long_type: escape_int,
        float: escape_float,
        str: escape_str,
        text_type: escape_unicode,
        tuple: escape_sequence,
        list: escape_sequence,
        set: escape_sequence,
        dict: escape_dict,
        type(None): escape_None,
        datetime.date: escape_date,
        datetime.datetime: escape_datetime,
        datetime.timedelta: escape_timedelta,
        datetime.time: escape_time,
        time.struct_time: escape_struct_time,
        Decimal: str,
        }


def through(x):
    return x

if not PY2 or JYTHON or IRONPYTHON:
    encoders[bytes] = escape_bytes

decoders = {
        FIELD_TYPE.BIT: convert_bit,
        FIELD_TYPE.TINY: int,
        FIELD_TYPE.SHORT: int,
        FIELD_TYPE.LONG: int,
        FIELD_TYPE.FLOAT: float,
        FIELD_TYPE.DOUBLE: float,
        FIELD_TYPE.DECIMAL: float,
        FIELD_TYPE.NEWDECIMAL: float,
        FIELD_TYPE.LONGLONG: int,
        FIELD_TYPE.INT24: int,
        FIELD_TYPE.YEAR: int,
        FIELD_TYPE.TIMESTAMP: convert_mysql_timestamp,
        FIELD_TYPE.DATETIME: convert_datetime,
        FIELD_TYPE.TIME: convert_timedelta,
        FIELD_TYPE.DATE: convert_date,
        FIELD_TYPE.SET: convert_set,
        FIELD_TYPE.BLOB: through,
        FIELD_TYPE.TINY_BLOB: through,
        FIELD_TYPE.MEDIUM_BLOB: through,
        FIELD_TYPE.LONG_BLOB: through,
        FIELD_TYPE.STRING: through,
        FIELD_TYPE.VAR_STRING: through,
        FIELD_TYPE.VARCHAR: through,
        FIELD_TYPE.DECIMAL: Decimal,
        FIELD_TYPE.NEWDECIMAL: Decimal,
        }


# for MySQLdb compatibility
conversions = decoders

def Thing2Literal(obj):
    return escape_str(str(obj))

########NEW FILE########
__FILENAME__ = cursors
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import
import re

from ._compat import range_type, text_type, PY2

from .err import (
    Warning, Error, InterfaceError, DataError,
    DatabaseError, OperationalError, IntegrityError, InternalError,
    NotSupportedError, ProgrammingError)


#: Regular expression for :meth:`Cursor.executemany`.
#: executemany only suports simple bulk insert.
#: You can use it to load large dataset.
RE_INSERT_VALUES = re.compile(r"""INSERT\s.+\sVALUES\s+(\(\s*%s\s*(,\s*%s\s*)*\))\s*\Z""",
                              re.IGNORECASE | re.DOTALL)


class Cursor(object):
    '''
    This is the object you use to interact with the database.
    '''

    #: Max stetement size which :meth:`executemany` generates.
    #:
    #: Max size of allowed statement is max_allowed_packet - packet_header_size.
    #: Default value of max_allowed_packet is 1048576.
    max_stmt_length = 1024000

    def __init__(self, connection):
        '''
        Do not create an instance of a Cursor yourself. Call
        connections.Connection.cursor().
        '''
        self.connection = connection
        self.description = None
        self.rownumber = 0
        self.rowcount = -1
        self.arraysize = 1
        self._executed = None
        self._result = None
        self._rows = None

    def __del__(self):
        '''
        When this gets GC'd close it.
        '''
        self.close()

    def close(self):
        '''
        Closing a cursor just exhausts all remaining data.
        '''
        conn = self.connection
        if conn is None:
            return
        try:
            while self.nextset():
                pass
        finally:
            self.connection = None

    def _get_db(self):
        if not self.connection:
            raise ProgrammingError("Cursor closed")
        return self.connection

    def _check_executed(self):
        if not self._executed:
            raise ProgrammingError("execute() first")

    def _conv_row(self, row):
        return row

    def setinputsizes(self, *args):
        """Does nothing, required by DB API."""

    def setoutputsizes(self, *args):
        """Does nothing, required by DB API."""

    def nextset(self):
        """Get the next query set"""
        conn = self._get_db()
        current_result = self._result
        if current_result is None or current_result is not conn._result:
            return None
        if not current_result.has_next:
            return None
        conn.next_result()
        self._do_get_result()
        return True

    def _escape_args(self, args, conn):
        if isinstance(args, (tuple, list)):
            return tuple(conn.escape(arg) for arg in args)
        elif isinstance(args, dict):
            return dict((key, conn.escape(val)) for (key, val) in args.items())
        else:
            #If it's not a dictionary let's try escaping it anyways.
            #Worst case it will throw a Value error
            return conn.escape(args)

    def execute(self, query, args=None):
        '''Execute a query'''
        conn = self._get_db()

        while self.nextset():
            pass

        if PY2:  # Use bytes on Python 2 always
            encoding = conn.encoding

            def ensure_bytes(x):
                if isinstance(x, unicode):
                    x = x.encode(encoding)
                return x

            query = ensure_bytes(query)

            if args is not None:
                if isinstance(args, (tuple, list)):
                    args = tuple(map(ensure_bytes, args))
                elif isinstance(args, dict):
                    args = dict((ensure_bytes(key), ensure_bytes(val)) for (key, val) in args.items())
                else:
                    args = ensure_bytes(args)

        if args is not None:
            query = query % self._escape_args(args, conn)

        result = self._query(query)
        self._executed = query
        return result

    def executemany(self, query, args):
        """Run several data against one query

        PyMySQL can execute bulkinsert for query like 'INSERT ... VALUES (%s)'.
        In other form of queries, just run :meth:`execute` many times.
        """
        if not args:
            return

        m = RE_INSERT_VALUES.match(query)
        if m:
            q_values = m.group(1).rstrip()
            assert q_values[0] == '(' and q_values[-1] == ')'
            q_prefix = query[:m.start(1)]
            return self._do_execute_many(q_prefix, q_values, args,
                                         self.max_stmt_length,
                                         self._get_db().encoding)

        self.rowcount = sum(self.execute(query, arg) for arg in args)
        return self.rowcount

    def _do_execute_many(self, prefix, values, args, max_stmt_length, encoding):
        conn = self._get_db()
        escape = self._escape_args
        if isinstance(prefix, text_type):
            prefix = prefix.encode(encoding)
        sql = bytearray(prefix)
        args = iter(args)
        v = values % escape(next(args), conn)
        if isinstance(v, text_type):
            v = v.encode(encoding)
        sql += v
        rows = 0
        for arg in args:
            v = values % escape(arg, conn)
            if isinstance(v, text_type):
                v = v.encode(encoding)
            if len(sql) + len(v) + 1 > max_stmt_length:
                rows += self.execute(sql)
                sql = bytearray(prefix)
            else:
                sql += b','
            sql += v
        rows += self.execute(sql)
        self.rowcount = rows
        return rows

    def callproc(self, procname, args=()):
        """Execute stored procedure procname with args

        procname -- string, name of procedure to execute on server

        args -- Sequence of parameters to use with procedure

        Returns the original args.

        Compatibility warning: PEP-249 specifies that any modified
        parameters must be returned. This is currently impossible
        as they are only available by storing them in a server
        variable and then retrieved by a query. Since stored
        procedures return zero or more result sets, there is no
        reliable way to get at OUT or INOUT parameters via callproc.
        The server variables are named @_procname_n, where procname
        is the parameter above and n is the position of the parameter
        (from zero). Once all result sets generated by the procedure
        have been fetched, you can issue a SELECT @_procname_0, ...
        query using .execute() to get any OUT or INOUT values.

        Compatibility warning: The act of calling a stored procedure
        itself creates an empty result set. This appears after any
        result sets generated by the procedure. This is non-standard
        behavior with respect to the DB-API. Be sure to use nextset()
        to advance through all result sets; otherwise you may get
        disconnected.
        """
        conn = self._get_db()
        for index, arg in enumerate(args):
            q = "SET @_%s_%d=%s" % (procname, index, conn.escape(arg))
            self._query(q)
            self.nextset()

        q = "CALL %s(%s)" % (procname,
                             ','.join(['@_%s_%d' % (procname, i)
                                       for i in range_type(len(args))]))
        self._query(q)
        self._executed = q
        return args

    def fetchone(self):
        ''' Fetch the next row '''
        self._check_executed()
        if self._rows is None or self.rownumber >= len(self._rows):
            return None
        result = self._rows[self.rownumber]
        self.rownumber += 1
        return result

    def fetchmany(self, size=None):
        ''' Fetch several rows '''
        self._check_executed()
        if self._rows is None:
            return None
        end = self.rownumber + (size or self.arraysize)
        result = self._rows[self.rownumber:end]
        self.rownumber = min(end, len(self._rows))
        return result

    def fetchall(self):
        ''' Fetch all the rows '''
        self._check_executed()
        if self._rows is None:
            return None
        if self.rownumber:
            result = self._rows[self.rownumber:]
        else:
            result = self._rows
        self.rownumber = len(self._rows)
        return result

    def scroll(self, value, mode='relative'):
        self._check_executed()
        if mode == 'relative':
            r = self.rownumber + value
        elif mode == 'absolute':
            r = value
        else:
            raise ProgrammingError("unknown scroll mode %s" % mode)

        if not (0 <= r < len(self._rows)):
            raise IndexError("out of range")
        self.rownumber = r

    def _query(self, q):
        conn = self._get_db()
        self._last_executed = q
        conn.query(q)
        self._do_get_result()
        return self.rowcount

    def _do_get_result(self):
        conn = self._get_db()

        self.rownumber = 0
        self._result = result = conn._result

        self.rowcount = result.affected_rows
        self.description = result.description
        self.lastrowid = result.insert_id
        self._rows = result.rows

    def __iter__(self):
        return iter(self.fetchone, None)

    Warning = Warning
    Error = Error
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError


class DictCursorMixin(object):
    # You can override this to use OrderedDict or other dict-like types.
    dict_type = dict

    def _do_get_result(self):
        super(DictCursorMixin, self)._do_get_result()
        fields = []
        if self.description:
            for f in self._result.fields:
                name = f.name
                if name in fields:
                    name = f.table_name + '.' + name
                fields.append(name)
            self._fields = fields

        if fields and self._rows:
            self._rows = [self._conv_row(r) for r in self._rows]

    def _conv_row(self, row):
        if row is None:
            return None
        return self.dict_type(zip(self._fields, row))


class DictCursor(DictCursorMixin, Cursor):
    """A cursor which returns results as a dictionary"""


class SSCursor(Cursor):
    """
    Unbuffered Cursor, mainly useful for queries that return a lot of data,
    or for connections to remote servers over a slow network.

    Instead of copying every row of data into a buffer, this will fetch
    rows as needed. The upside of this, is the client uses much less memory,
    and rows are returned much faster when traveling over a slow network,
    or if the result set is very big.

    There are limitations, though. The MySQL protocol doesn't support
    returning the total number of rows, so the only way to tell how many rows
    there are is to iterate over every row returned. Also, it currently isn't
    possible to scroll backwards, as only the current row is held in memory.
    """

    def _conv_row(self, row):
        return row

    def close(self):
        conn = self.connection
        if conn is None:
            return

        if self._result is not None and self._result is conn._result:
            self._result._finish_unbuffered_query()

        try:
            while self.nextset():
                pass
        finally:
            self.connection = None

    def _query(self, q):
        conn = self._get_db()
        self._last_executed = q
        conn.query(q, unbuffered=True)
        self._do_get_result()
        return self.rowcount

    def read_next(self):
        """ Read next row """
        return self._conv_row(self._result._read_rowdata_packet_unbuffered())

    def fetchone(self):
        """ Fetch next row """
        self._check_executed()
        row = self.read_next()
        if row is None:
            return None
        self.rownumber += 1
        return row

    def fetchall(self):
        """
        Fetch all, as per MySQLdb. Pretty useless for large queries, as
        it is buffered. See fetchall_unbuffered(), if you want an unbuffered
        generator version of this method.

        """
        return list(self.fetchall_unbuffered())

    def fetchall_unbuffered(self):
        """
        Fetch all, implemented as a generator, which isn't to standard,
        however, it doesn't make sense to return everything in a list, as that
        would use ridiculous memory for large result sets.
        """
        return iter(self.fetchone, None)

    def __iter__(self):
        return self.fetchall_unbuffered()

    def fetchmany(self, size=None):
        """ Fetch many """

        self._check_executed()
        if size is None:
            size = self.arraysize

        rows = []
        for i in range_type(size):
            row = self.read_next()
            if row is None:
                break
            rows.append(row)
            self.rownumber += 1
        return rows

    def scroll(self, value, mode='relative'):
        self._check_executed()

        if mode == 'relative':
            if value < 0:
                raise NotSupportedError(
                        "Backwards scrolling not supported by this cursor")

            for _ in range_type(value):
                self.read_next()
            self.rownumber += value
        elif mode == 'absolute':
            if value < self.rownumber:
                raise NotSupportedError(
                    "Backwards scrolling not supported by this cursor")

            end = value - self.rownumber
            for _ in range_type(end):
                self.read_next()
            self.rownumber = value
        else:
            raise ProgrammingError("unknown scroll mode %s" % mode)


class SSDictCursor(DictCursorMixin, SSCursor):
    """ An unbuffered cursor, which returns results as a dictionary """

########NEW FILE########
__FILENAME__ = err
import struct

from .constants import ER

class MySQLError(Exception):
    """Exception related to operation with MySQL."""


class Warning(Warning, MySQLError):
    """Exception raised for important warnings like data truncations
    while inserting, etc."""

class Error(MySQLError):
    """Exception that is the base class of all other error exceptions
    (not Warning)."""


class InterfaceError(Error):
    """Exception raised for errors that are related to the database
    interface rather than the database itself."""


class DatabaseError(Error):
    """Exception raised for errors that are related to the
    database."""


class DataError(DatabaseError):
    """Exception raised for errors that are due to problems with the
    processed data like division by zero, numeric value out of range,
    etc."""


class OperationalError(DatabaseError):
    """Exception raised for errors that are related to the database's
    operation and not necessarily under the control of the programmer,
    e.g. an unexpected disconnect occurs, the data source name is not
    found, a transaction could not be processed, a memory allocation
    error occurred during processing, etc."""


class IntegrityError(DatabaseError):
    """Exception raised when the relational integrity of the database
    is affected, e.g. a foreign key check fails, duplicate key,
    etc."""


class InternalError(DatabaseError):
    """Exception raised when the database encounters an internal
    error, e.g. the cursor is not valid anymore, the transaction is
    out of sync, etc."""


class ProgrammingError(DatabaseError):
    """Exception raised for programming errors, e.g. table not found
    or already exists, syntax error in the SQL statement, wrong number
    of parameters specified, etc."""


class NotSupportedError(DatabaseError):
    """Exception raised in case a method or database API was used
    which is not supported by the database, e.g. requesting a
    .rollback() on a connection that does not support transaction or
    has transactions turned off."""


error_map = {}

def _map_error(exc, *errors):
    for error in errors:
        error_map[error] = exc

_map_error(ProgrammingError, ER.DB_CREATE_EXISTS, ER.SYNTAX_ERROR,
           ER.PARSE_ERROR, ER.NO_SUCH_TABLE, ER.WRONG_DB_NAME,
           ER.WRONG_TABLE_NAME, ER.FIELD_SPECIFIED_TWICE,
           ER.INVALID_GROUP_FUNC_USE, ER.UNSUPPORTED_EXTENSION,
           ER.TABLE_MUST_HAVE_COLUMNS, ER.CANT_DO_THIS_DURING_AN_TRANSACTION)
_map_error(DataError, ER.WARN_DATA_TRUNCATED, ER.WARN_NULL_TO_NOTNULL,
           ER.WARN_DATA_OUT_OF_RANGE, ER.NO_DEFAULT, ER.PRIMARY_CANT_HAVE_NULL,
           ER.DATA_TOO_LONG, ER.DATETIME_FUNCTION_OVERFLOW)
_map_error(IntegrityError, ER.DUP_ENTRY, ER.NO_REFERENCED_ROW,
           ER.NO_REFERENCED_ROW_2, ER.ROW_IS_REFERENCED, ER.ROW_IS_REFERENCED_2,
           ER.CANNOT_ADD_FOREIGN, ER.BAD_NULL_ERROR)
_map_error(NotSupportedError, ER.WARNING_NOT_COMPLETE_ROLLBACK,
           ER.NOT_SUPPORTED_YET, ER.FEATURE_DISABLED, ER.UNKNOWN_STORAGE_ENGINE)
_map_error(OperationalError, ER.DBACCESS_DENIED_ERROR, ER.ACCESS_DENIED_ERROR,
           ER.CON_COUNT_ERROR, ER.TABLEACCESS_DENIED_ERROR,
           ER.COLUMNACCESS_DENIED_ERROR)

del _map_error, ER


def _get_error_info(data):
    errno = struct.unpack('<h', data[1:3])[0]
    is_41 = data[3:4] == b"#"
    if is_41:
        # version 4.1
        sqlstate = data[4:9].decode("utf8", 'replace')
        errorvalue = data[9:].decode("utf8", 'replace')
        return (errno, sqlstate, errorvalue)
    else:
        # version 4.0
        return (errno, None, data[3:].decode("utf8", 'replace'))

def _check_mysql_exception(errinfo):
    errno, sqlstate, errorvalue = errinfo
    errorclass = error_map.get(errno, None)
    if errorclass:
        raise errorclass(errno,errorvalue)

    # couldn't find the right error number
    raise InternalError(errno, errorvalue)

def raise_mysql_exception(data):
    errinfo = _get_error_info(data)
    _check_mysql_exception(errinfo)

########NEW FILE########
__FILENAME__ = base
import os
import json
import pymysql
try:
    import unittest2 as unittest
except ImportError:
    import unittest

class PyMySQLTestCase(unittest.TestCase):
    # You can specify your test environment creating a file named
    #  "databases.json" or editing the `databases` variable below.
    fname = os.path.join(os.path.dirname(__file__), "databases.json")
    if os.path.exists(fname):
        with open(fname) as f:
            databases = json.load(f)
    else:
        databases = [
            {"host":"localhost","user":"root",
             "passwd":"","db":"test_pymysql", "use_unicode": True},
            {"host":"localhost","user":"root","passwd":"","db":"test_pymysql2"}]

    def setUp(self):
        self.connections = []
        for params in self.databases:
            self.connections.append(pymysql.connect(**params))

    def tearDown(self):
        for connection in self.connections:
            connection.close()

########NEW FILE########
__FILENAME__ = test_basic
import pymysql.cursors

from pymysql.tests import base
from pymysql import util
from pymysql.err import ProgrammingError

import time
import datetime

__all__ = ["TestConversion", "TestCursor", "TestBulkInserts"]


class TestConversion(base.PyMySQLTestCase):
    def test_datatypes(self):
        """ test every data type """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_datatypes (b bit, i int, l bigint, f real, s varchar(32), u varchar(32), bb blob, d date, dt datetime, ts timestamp, td time, t time, st datetime)")
        try:
            # insert values
            v = (True, -3, 123456789012, 5.7, "hello'\" world", u"Espa\xc3\xb1ol", "binary\x00data".encode(conn.charset), datetime.date(1988,2,2), datetime.datetime.now(), datetime.timedelta(5,6), datetime.time(16,32), time.localtime())
            c.execute("insert into test_datatypes (b,i,l,f,s,u,bb,d,dt,td,t,st) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", v)
            c.execute("select b,i,l,f,s,u,bb,d,dt,td,t,st from test_datatypes")
            r = c.fetchone()
            self.assertEqual(util.int2byte(1), r[0])
            self.assertEqual(v[1:8], r[1:8])
            # mysql throws away microseconds so we need to check datetimes
            # specially. additionally times are turned into timedeltas.
            self.assertEqual(datetime.datetime(*v[8].timetuple()[:6]), r[8])
            self.assertEqual(v[9], r[9]) # just timedeltas
            self.assertEqual(datetime.timedelta(0, 60 * (v[10].hour * 60 + v[10].minute)), r[10])
            self.assertEqual(datetime.datetime(*v[-1][:6]), r[-1])

            c.execute("delete from test_datatypes")

            # check nulls
            c.execute("insert into test_datatypes (b,i,l,f,s,u,bb,d,dt,td,t,st) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", [None] * 12)
            c.execute("select b,i,l,f,s,u,bb,d,dt,td,t,st from test_datatypes")
            r = c.fetchone()
            self.assertEqual(tuple([None] * 12), r)

            c.execute("delete from test_datatypes")

            # check sequence type
            c.execute("insert into test_datatypes (i, l) values (2,4), (6,8), (10,12)")
            c.execute("select l from test_datatypes where i in %s order by i", ((2,6),))
            r = c.fetchall()
            self.assertEqual(((4,),(8,)), r)
        finally:
            c.execute("drop table test_datatypes")

    def test_dict(self):
        """ test dict escaping """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a integer, b integer, c integer)")
        try:
            c.execute("insert into test_dict (a,b,c) values (%(a)s, %(b)s, %(c)s)", {"a":1,"b":2,"c":3})
            c.execute("select a,b,c from test_dict")
            self.assertEqual((1,2,3), c.fetchone())
        finally:
            c.execute("drop table test_dict")

    def test_string(self):
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a text)")
        test_value = "I am a test string"
        try:
            c.execute("insert into test_dict (a) values (%s)", test_value)
            c.execute("select a from test_dict")
            self.assertEqual((test_value,), c.fetchone())
        finally:
            c.execute("drop table test_dict")

    def test_integer(self):
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a integer)")
        test_value = 12345
        try:
            c.execute("insert into test_dict (a) values (%s)", test_value)
            c.execute("select a from test_dict")
            self.assertEqual((test_value,), c.fetchone())
        finally:
            c.execute("drop table test_dict")


    def test_big_blob(self):
        """ test tons of data """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_big_blob (b blob)")
        try:
            data = "pymysql" * 1024
            c.execute("insert into test_big_blob (b) values (%s)", (data,))
            c.execute("select b from test_big_blob")
            self.assertEqual(data.encode(conn.charset), c.fetchone()[0])
        finally:
            c.execute("drop table test_big_blob")

    def test_untyped(self):
        """ test conversion of null, empty string """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("select null,''")
        self.assertEqual((None,u''), c.fetchone())
        c.execute("select '',null")
        self.assertEqual((u'',None), c.fetchone())

    def test_timedelta(self):
        """ test timedelta conversion """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("select time('12:30'), time('23:12:59'), time('23:12:59.05100')")
        self.assertEqual((datetime.timedelta(0, 45000),
                          datetime.timedelta(0, 83579),
                          datetime.timedelta(0, 83579, 51000)),
                         c.fetchone())

    def test_datetime(self):
        """ test datetime conversion """
        conn = self.connections[0]
        c = conn.cursor()
        dt = datetime.datetime(2013,11,12,9,9,9,123450)
        try:
            c.execute("create table test_datetime (id int, ts datetime(6))")
            c.execute("insert into test_datetime values (1,'2013-11-12 09:09:09.12345')")
            c.execute("select ts from test_datetime")
            self.assertEqual((dt,),c.fetchone())
        except ProgrammingError:
            # User is running a version of MySQL that doesn't support msecs within datetime
            pass
        finally:
            c.execute("drop table if exists test_datetime")


class TestCursor(base.PyMySQLTestCase):
    # this test case does not work quite right yet, however,
    # we substitute in None for the erroneous field which is
    # compatible with the DB-API 2.0 spec and has not broken
    # any unit tests for anything we've tried.

    #def test_description(self):
    #    """ test description attribute """
    #    # result is from MySQLdb module
    #    r = (('Host', 254, 11, 60, 60, 0, 0),
    #         ('User', 254, 16, 16, 16, 0, 0),
    #         ('Password', 254, 41, 41, 41, 0, 0),
    #         ('Select_priv', 254, 1, 1, 1, 0, 0),
    #         ('Insert_priv', 254, 1, 1, 1, 0, 0),
    #         ('Update_priv', 254, 1, 1, 1, 0, 0),
    #         ('Delete_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_priv', 254, 1, 1, 1, 0, 0),
    #         ('Drop_priv', 254, 1, 1, 1, 0, 0),
    #         ('Reload_priv', 254, 1, 1, 1, 0, 0),
    #         ('Shutdown_priv', 254, 1, 1, 1, 0, 0),
    #         ('Process_priv', 254, 1, 1, 1, 0, 0),
    #         ('File_priv', 254, 1, 1, 1, 0, 0),
    #         ('Grant_priv', 254, 1, 1, 1, 0, 0),
    #         ('References_priv', 254, 1, 1, 1, 0, 0),
    #         ('Index_priv', 254, 1, 1, 1, 0, 0),
    #         ('Alter_priv', 254, 1, 1, 1, 0, 0),
    #         ('Show_db_priv', 254, 1, 1, 1, 0, 0),
    #         ('Super_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_tmp_table_priv', 254, 1, 1, 1, 0, 0),
    #         ('Lock_tables_priv', 254, 1, 1, 1, 0, 0),
    #         ('Execute_priv', 254, 1, 1, 1, 0, 0),
    #         ('Repl_slave_priv', 254, 1, 1, 1, 0, 0),
    #         ('Repl_client_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_view_priv', 254, 1, 1, 1, 0, 0),
    #         ('Show_view_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_routine_priv', 254, 1, 1, 1, 0, 0),
    #         ('Alter_routine_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_user_priv', 254, 1, 1, 1, 0, 0),
    #         ('Event_priv', 254, 1, 1, 1, 0, 0),
    #         ('Trigger_priv', 254, 1, 1, 1, 0, 0),
    #         ('ssl_type', 254, 0, 9, 9, 0, 0),
    #         ('ssl_cipher', 252, 0, 65535, 65535, 0, 0),
    #         ('x509_issuer', 252, 0, 65535, 65535, 0, 0),
    #         ('x509_subject', 252, 0, 65535, 65535, 0, 0),
    #         ('max_questions', 3, 1, 11, 11, 0, 0),
    #         ('max_updates', 3, 1, 11, 11, 0, 0),
    #         ('max_connections', 3, 1, 11, 11, 0, 0),
    #         ('max_user_connections', 3, 1, 11, 11, 0, 0))
    #    conn = self.connections[0]
    #    c = conn.cursor()
    #    c.execute("select * from mysql.user")
    #
    #    self.assertEqual(r, c.description)

    def test_fetch_no_result(self):
        """ test a fetchone() with no rows """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_nr (b varchar(32))")
        try:
            data = "pymysql"
            c.execute("insert into test_nr (b) values (%s)", (data,))
            self.assertEqual(None, c.fetchone())
        finally:
            c.execute("drop table test_nr")

    def test_aggregates(self):
        """ test aggregate functions """
        conn = self.connections[0]
        c = conn.cursor()
        try:
            c.execute('create table test_aggregates (i integer)')
            for i in range(0, 10):
                c.execute('insert into test_aggregates (i) values (%s)', (i,))
            c.execute('select sum(i) from test_aggregates')
            r, = c.fetchone()
            self.assertEqual(sum(range(0,10)), r)
        finally:
            c.execute('drop table test_aggregates')

    def test_single_tuple(self):
        """ test a single tuple """
        conn = self.connections[0]
        c = conn.cursor()
        try:
            c.execute("create table mystuff (id integer primary key)")
            c.execute("insert into mystuff (id) values (1)")
            c.execute("insert into mystuff (id) values (2)")
            c.execute("select id from mystuff where id in %s", ((1,),))
            self.assertEqual([(1,)], list(c.fetchall()))
        finally:
            c.execute("drop table mystuff")


class TestBulkInserts(base.PyMySQLTestCase):

    cursor_type = pymysql.cursors.DictCursor

    def setUp(self):
        super(TestBulkInserts, self).setUp()
        self.conn = conn = self.connections[0]
        c = conn.cursor(self.cursor_type)

        # create a table ane some data to query
        c.execute("drop table if exists bulkinsert")
        c.execute(
"""CREATE TABLE bulkinsert
(
id int(11),
name char(20),
age int,
height int,
PRIMARY KEY (id)
)
""")

    def _verify_records(self, data):
        conn = self.connections[0]
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, age, height from bulkinsert")
        result = cursor.fetchall()
        self.assertEqual(sorted(data), sorted(result))

    def test_bulk_insert(self):
        conn = self.connections[0]
        cursor = conn.cursor()

        data = [(0, "bob", 21, 123), (1, "jim", 56, 45), (2, "fred", 100, 180)]
        cursor.executemany("insert into bulkinsert (id, name, age, height) "
                           "values (%s,%s,%s,%s)", data)
        self.assertEqual(
            cursor._last_executed, bytearray(
            b"insert into bulkinsert (id, name, age, height) values "
            b"(0,'bob',21,123),(1,'jim',56,45),(2,'fred',100,180)"))
        cursor.execute('commit')
        self._verify_records(data)

    def test_bulk_insert_multiline_statement(self):
        conn = self.connections[0]
        cursor = conn.cursor()
        data = [(0, "bob", 21, 123), (1, "jim", 56, 45), (2, "fred", 100, 180)]
        cursor.executemany("""insert
into bulkinsert (id, name,
age, height)
values (%s,
%s , %s,
%s )
 """, data)
        self.assertEqual(cursor._last_executed, bytearray(b"""insert
into bulkinsert (id, name,
age, height)
values (0,
'bob' , 21,
123 ),(1,
'jim' , 56,
45 ),(2,
'fred' , 100,
180 )"""))
        cursor.execute('commit')
        self._verify_records(data)

    def test_bulk_insert_single_record(self):
        conn = self.connections[0]
        cursor = conn.cursor()
        data = [(0, "bob", 21, 123)]
        cursor.executemany("insert into bulkinsert (id, name, age, height) "
                           "values (%s,%s,%s,%s)", data)
        cursor.execute('commit')
        self._verify_records(data)


if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
import pymysql
import time
from pymysql.tests import base


class TestConnection(base.PyMySQLTestCase):
    def test_utf8mb4(self):
        """This test requires MySQL >= 5.5"""
        arg = self.databases[0].copy()
        arg['charset'] = 'utf8mb4'
        conn = pymysql.connect(**arg)

    def test_largedata(self):
        """Large query and response (>=16MB)"""
        cur = self.connections[0].cursor()
        cur.execute("SELECT @@max_allowed_packet")
        if cur.fetchone()[0] < 16*1024*1024 + 10:
            print("Set max_allowed_packet to bigger than 17MB")
            return
        t = 'a' * (16*1024*1024)
        cur.execute("SELECT '" + t + "'")
        assert cur.fetchone()[0] == t

    def test_escape_string(self):
        con = self.connections[0]
        cur = con.cursor()

        self.assertEqual(con.escape("foo'bar"), "'foo\\'bar'")
        cur.execute("SET sql_mode='NO_BACKSLASH_ESCAPES'")
        self.assertEqual(con.escape("foo'bar"), "'foo''bar'")

    def test_autocommit(self):
        con = self.connections[0]
        self.assertFalse(con.get_autocommit())

        cur = con.cursor()
        cur.execute("SET AUTOCOMMIT=1")
        self.assertTrue(con.get_autocommit())

        con.autocommit(False)
        self.assertFalse(con.get_autocommit())
        cur.execute("SELECT @@AUTOCOMMIT")
        self.assertEqual(cur.fetchone()[0], 0)

    def test_select_db(self):
        con = self.connections[0]
        current_db = self.databases[0]['db']
        other_db = self.databases[1]['db']

        cur = con.cursor()
        cur.execute('SELECT database()')
        self.assertEqual(cur.fetchone()[0], current_db)

        con.select_db(other_db)
        cur.execute('SELECT database()')
        self.assertEqual(cur.fetchone()[0], other_db)

    def test_connection_gone_away(self):
        """
        http://dev.mysql.com/doc/refman/5.0/en/gone-away.html
        http://dev.mysql.com/doc/refman/5.0/en/error-messages-client.html#error_cr_server_gone_error
        """
        con = self.connections[0]
        cur = con.cursor()
        cur.execute("SET wait_timeout=1")
        time.sleep(2)
        with self.assertRaises(pymysql.OperationalError) as cm:
            cur.execute("SELECT 1+1")
        # error occures while reading, not writing because of socket buffer.
        #self.assertEquals(cm.exception.args[0], 2006)
        self.assertIn(cm.exception.args[0], (2006, 2013))


if __name__ == "__main__":
    try:
        import unittest2 as unittest
    except ImportError:
        import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_DictCursor
from pymysql.tests import base
import pymysql.cursors

import datetime


class TestDictCursor(base.PyMySQLTestCase):
    bob = {'name': 'bob', 'age': 21, 'DOB': datetime.datetime(1990, 2, 6, 23, 4, 56)}
    jim = {'name': 'jim', 'age': 56, 'DOB': datetime.datetime(1955, 5, 9, 13, 12, 45)}
    fred = {'name': 'fred', 'age': 100, 'DOB': datetime.datetime(1911, 9, 12, 1, 1, 1)}

    cursor_type = pymysql.cursors.DictCursor

    def setUp(self):
        super(TestDictCursor, self).setUp()
        self.conn = conn = self.connections[0]
        c = conn.cursor(self.cursor_type)

        # create a table ane some data to query
        c.execute("drop table if exists dictcursor")
        c.execute("""CREATE TABLE dictcursor (name char(20), age int , DOB datetime)""")
        data = [("bob", 21, "1990-02-06 23:04:56"),
                ("jim", 56, "1955-05-09 13:12:45"),
                ("fred", 100, "1911-09-12 01:01:01")]
        c.executemany("insert into dictcursor values (%s,%s,%s)", data)

    def tearDown(self):
        c = self.conn.cursor()
        c.execute("drop table dictcursor")
        super(TestDictCursor, self).tearDown()

    def test_DictCursor(self):
        bob, jim, fred = self.bob.copy(), self.jim.copy(), self.fred.copy()
        #all assert test compare to the structure as would come out from MySQLdb
        conn = self.conn
        c = conn.cursor(self.cursor_type)

        # try an update which should return no rows
        c.execute("update dictcursor set age=20 where name='bob'")
        bob['age'] = 20
        # pull back the single row dict for bob and check
        c.execute("SELECT * from dictcursor where name='bob'")
        r = c.fetchone()
        self.assertEqual(bob, r, "fetchone via DictCursor failed")
        # same again, but via fetchall => tuple)
        c.execute("SELECT * from dictcursor where name='bob'")
        r = c.fetchall()
        self.assertEqual([bob], r, "fetch a 1 row result via fetchall failed via DictCursor")
        # same test again but iterate over the
        c.execute("SELECT * from dictcursor where name='bob'")
        for r in c:
            self.assertEqual(bob, r, "fetch a 1 row result via iteration failed via DictCursor")
        # get all 3 row via fetchall
        c.execute("SELECT * from dictcursor")
        r = c.fetchall()
        self.assertEqual([bob,jim,fred], r, "fetchall failed via DictCursor")
        #same test again but do a list comprehension
        c.execute("SELECT * from dictcursor")
        r = list(c)
        self.assertEqual([bob,jim,fred], r, "DictCursor should be iterable")
        # get all 2 row via fetchmany
        c.execute("SELECT * from dictcursor")
        r = c.fetchmany(2)
        self.assertEqual([bob, jim], r, "fetchmany failed via DictCursor")

    def test_custom_dict(self):
        class MyDict(dict): pass

        class MyDictCursor(self.cursor_type):
            dict_type = MyDict

        keys = ['name', 'age', 'DOB']
        bob = MyDict([(k, self.bob[k]) for k in keys])
        jim = MyDict([(k, self.jim[k]) for k in keys])
        fred = MyDict([(k, self.fred[k]) for k in keys])

        cur = self.conn.cursor(MyDictCursor)
        cur.execute("SELECT * FROM dictcursor WHERE name='bob'")
        r = cur.fetchone()
        self.assertEqual(bob, r, "fetchone() returns MyDictCursor")

        cur.execute("SELECT * FROM dictcursor")
        r = cur.fetchall()
        self.assertEqual([bob, jim, fred], r,
                         "fetchall failed via MyDictCursor")

        cur.execute("SELECT * FROM dictcursor")
        r = list(cur)
        self.assertEqual([bob, jim, fred], r,
                         "list failed via MyDictCursor")

        cur.execute("SELECT * FROM dictcursor")
        r = cur.fetchmany(2)
        self.assertEqual([bob, jim], r,
                         "list failed via MyDictCursor")


class TestSSDictCursor(TestDictCursor):
    cursor_type = pymysql.cursors.SSDictCursor


if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_example
import pymysql
from pymysql.tests import base

class TestExample(base.PyMySQLTestCase):
    def test_example(self):
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='mysql')


        cur = conn.cursor()

        cur.execute("SELECT Host,User FROM user")

        # print cur.description

        # r = cur.fetchall()
        # print r
        # ...or...
        u = False

        for r in cur.fetchall():
            u = u or conn.user in r

        self.assertTrue(u)

        cur.close()
        conn.close()

__all__ = ["TestExample"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_issues
import pymysql
from pymysql.tests import base
try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import imp
    reload = imp.reload
except AttributeError:
    pass

import datetime


class TestOldIssues(base.PyMySQLTestCase):
    def test_issue_3(self):
        """ undefined methods datetime_or_None, date_or_None """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists issue3")
        c.execute("create table issue3 (d date, t time, dt datetime, ts timestamp)")
        try:
            c.execute("insert into issue3 (d, t, dt, ts) values (%s,%s,%s,%s)", (None, None, None, None))
            c.execute("select d from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select t from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select dt from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select ts from issue3")
            self.assertTrue(isinstance(c.fetchone()[0], datetime.datetime))
        finally:
            c.execute("drop table issue3")

    def test_issue_4(self):
        """ can't retrieve TIMESTAMP fields """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists issue4")
        c.execute("create table issue4 (ts timestamp)")
        try:
            c.execute("insert into issue4 (ts) values (now())")
            c.execute("select ts from issue4")
            self.assertTrue(isinstance(c.fetchone()[0], datetime.datetime))
        finally:
            c.execute("drop table issue4")

    def test_issue_5(self):
        """ query on information_schema.tables fails """
        con = self.connections[0]
        cur = con.cursor()
        cur.execute("select * from information_schema.tables")

    def test_issue_6(self):
        """ exception: TypeError: ord() expected a character, but string of length 0 found """
        # ToDo: this test requires access to db 'mysql'.
        kwargs = self.databases[0].copy()
        kwargs['db'] = "mysql"
        conn = pymysql.connect(**kwargs)
        c = conn.cursor()
        c.execute("select * from user")
        conn.close()

    def test_issue_8(self):
        """ Primary Key and Index error when selecting data """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists test")
        c.execute("""CREATE TABLE `test` (`station` int(10) NOT NULL DEFAULT '0', `dh`
datetime NOT NULL DEFAULT '0000-00-00 00:00:00', `echeance` int(1) NOT NULL
DEFAULT '0', `me` double DEFAULT NULL, `mo` double DEFAULT NULL, PRIMARY
KEY (`station`,`dh`,`echeance`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;""")
        try:
            self.assertEqual(0, c.execute("SELECT * FROM test"))
            c.execute("ALTER TABLE `test` ADD INDEX `idx_station` (`station`)")
            self.assertEqual(0, c.execute("SELECT * FROM test"))
        finally:
            c.execute("drop table test")

    def test_issue_9(self):
        """ sets DeprecationWarning in Python 2.6 """
        try:
            reload(pymysql)
        except DeprecationWarning:
            self.fail()

    def test_issue_13(self):
        """ can't handle large result fields """
        conn = self.connections[0]
        cur = conn.cursor()
        cur.execute("drop table if exists issue13")
        try:
            cur.execute("create table issue13 (t text)")
            # ticket says 18k
            size = 18*1024
            cur.execute("insert into issue13 (t) values (%s)", ("x" * size,))
            cur.execute("select t from issue13")
            # use assertTrue so that obscenely huge error messages don't print
            r = cur.fetchone()[0]
            self.assertTrue("x" * size == r)
        finally:
            cur.execute("drop table issue13")

    def test_issue_15(self):
        """ query should be expanded before perform character encoding """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists issue15")
        c.execute("create table issue15 (t varchar(32))")
        try:
            c.execute("insert into issue15 (t) values (%s)", (u'\xe4\xf6\xfc',))
            c.execute("select t from issue15")
            self.assertEqual(u'\xe4\xf6\xfc', c.fetchone()[0])
        finally:
            c.execute("drop table issue15")

    def test_issue_16(self):
        """ Patch for string and tuple escaping """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists issue16")
        c.execute("create table issue16 (name varchar(32) primary key, email varchar(32))")
        try:
            c.execute("insert into issue16 (name, email) values ('pete', 'floydophone')")
            c.execute("select email from issue16 where name=%s", ("pete",))
            self.assertEqual("floydophone", c.fetchone()[0])
        finally:
            c.execute("drop table issue16")

    @unittest.skip("test_issue_17() requires a custom, legacy MySQL configuration and will not be run.")
    def test_issue_17(self):
        """ could not connect mysql use passwod """
        conn = self.connections[0]
        host = self.databases[0]["host"]
        db = self.databases[0]["db"]
        c = conn.cursor()
        # grant access to a table to a user with a password
        try:
            c.execute("drop table if exists issue17")
            c.execute("create table issue17 (x varchar(32) primary key)")
            c.execute("insert into issue17 (x) values ('hello, world!')")
            c.execute("grant all privileges on %s.issue17 to 'issue17user'@'%%' identified by '1234'" % db)
            conn.commit()

            conn2 = pymysql.connect(host=host, user="issue17user", passwd="1234", db=db)
            c2 = conn2.cursor()
            c2.execute("select x from issue17")
            self.assertEqual("hello, world!", c2.fetchone()[0])
        finally:
            c.execute("drop table issue17")

class TestNewIssues(base.PyMySQLTestCase):
    def test_issue_34(self):
        try:
            pymysql.connect(host="localhost", port=1237, user="root")
            self.fail()
        except pymysql.OperationalError as e:
            self.assertEqual(2003, e.args[0])
        except Exception:
            self.fail()

    def test_issue_33(self):
        conn = pymysql.connect(charset="utf8", **self.databases[0])
        c = conn.cursor()
        try:
            c.execute(b"drop table if exists hei\xc3\x9fe".decode("utf8"))
            c.execute(b"create table hei\xc3\x9fe (name varchar(32))".decode("utf8"))
            c.execute(b"insert into hei\xc3\x9fe (name) values ('Pi\xc3\xb1ata')".decode("utf8"))
            c.execute(b"select name from hei\xc3\x9fe".decode("utf8"))
            self.assertEqual(b"Pi\xc3\xb1ata".decode("utf8"), c.fetchone()[0])
        finally:
            c.execute(b"drop table hei\xc3\x9fe".decode("utf8"))

    @unittest.skip("This test requires manual intervention")
    def test_issue_35(self):
        conn = self.connections[0]
        c = conn.cursor()
        print("sudo killall -9 mysqld within the next 10 seconds")
        try:
            c.execute("select sleep(10)")
            self.fail()
        except pymysql.OperationalError as e:
            self.assertEqual(2013, e.args[0])

    def test_issue_36(self):
        conn = self.connections[0]
        c = conn.cursor()
        # kill connections[0]
        c.execute("show processlist")
        kill_id = None
        for row in c.fetchall():
            id = row[0]
            info = row[7]
            if info == "show processlist":
                kill_id = id
                break
        # now nuke the connection
        conn.kill(kill_id)
        # make sure this connection has broken
        try:
            c.execute("show tables")
            self.fail()
        except Exception:
            pass
        # check the process list from the other connection
        try:
            c = self.connections[1].cursor()
            c.execute("show processlist")
            ids = [row[0] for row in c.fetchall()]
            self.assertFalse(kill_id in ids)
        finally:
            del self.connections[0]

    def test_issue_37(self):
        conn = self.connections[0]
        c = conn.cursor()
        self.assertEqual(1, c.execute("SELECT @foo"))
        self.assertEqual((None,), c.fetchone())
        self.assertEqual(0, c.execute("SET @foo = 'bar'"))
        c.execute("set @foo = 'bar'")

    def test_issue_38(self):
        conn = self.connections[0]
        c = conn.cursor()
        datum = "a" * 1024 * 1023 # reduced size for most default mysql installs

        try:
            c.execute("drop table if exists issue38")
            c.execute("create table issue38 (id integer, data mediumblob)")
            c.execute("insert into issue38 values (1, %s)", (datum,))
        finally:
            c.execute("drop table issue38")

    def disabled_test_issue_54(self):
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("drop table if exists issue54")
        big_sql = "select * from issue54 where "
        big_sql += " and ".join("%d=%d" % (i,i) for i in range(0, 100000))

        try:
            c.execute("create table issue54 (id integer primary key)")
            c.execute("insert into issue54 (id) values (7)")
            c.execute(big_sql)
            self.assertEqual(7, c.fetchone()[0])
        finally:
            c.execute("drop table issue54")

class TestGitHubIssues(base.PyMySQLTestCase):
    def test_issue_66(self):
        """ 'Connection' object has no attribute 'insert_id' """
        conn = self.connections[0]
        c = conn.cursor()
        self.assertEqual(0, conn.insert_id())
        try:
            c.execute("drop table if exists issue66")
            c.execute("create table issue66 (id integer primary key auto_increment, x integer)")
            c.execute("insert into issue66 (x) values (1)")
            c.execute("insert into issue66 (x) values (1)")
            self.assertEqual(2, conn.insert_id())
        finally:
            c.execute("drop table issue66")

    def test_issue_79(self):
        """ Duplicate field overwrites the previous one in the result of DictCursor """
        conn = self.connections[0]
        c = conn.cursor(pymysql.cursors.DictCursor)

        c.execute("drop table if exists a")
        c.execute("drop table if exists b")
        c.execute("""CREATE TABLE a (id int, value int)""")
        c.execute("""CREATE TABLE b (id int, value int)""")

        a=(1,11)
        b=(1,22)
        try:
            c.execute("insert into a values (%s, %s)", a)
            c.execute("insert into b values (%s, %s)", b)

            c.execute("SELECT * FROM a inner join b on a.id = b.id")
            r = c.fetchall()[0]
            self.assertEqual(r['id'], 1)
            self.assertEqual(r['value'], 11)
            self.assertEqual(r['b.value'], 22)
        finally:
            c.execute("drop table a")
            c.execute("drop table b")

    def test_issue_95(self):
        """ Leftover trailing OK packet for "CALL my_sp" queries """
        conn = self.connections[0]
        cur = conn.cursor()
        cur.execute("DROP PROCEDURE IF EXISTS `foo`")
        cur.execute("""CREATE PROCEDURE `foo` ()
        BEGIN
            SELECT 1;
        END""")
        try:
            cur.execute("""CALL foo()""")
            cur.execute("""SELECT 1""")
            self.assertEqual(cur.fetchone()[0], 1)
        finally:
            cur.execute("DROP PROCEDURE IF EXISTS `foo`")

    def test_issue_114(self):
        """ autocommit is not set after reconnecting with ping() """
        conn = pymysql.connect(charset="utf8", **self.databases[0])
        conn.autocommit(False)
        c = conn.cursor()
        c.execute("""select @@autocommit;""")
        self.assertFalse(c.fetchone()[0])
        conn.close()
        conn.ping()
        c.execute("""select @@autocommit;""")
        self.assertFalse(c.fetchone()[0])
        conn.close()

        # Ensure autocommit() is still working
        conn = pymysql.connect(charset="utf8", **self.databases[0])
        c = conn.cursor()
        c.execute("""select @@autocommit;""")
        self.assertFalse(c.fetchone()[0])
        conn.close()
        conn.ping()
        conn.autocommit(True)
        c.execute("""select @@autocommit;""")
        self.assertTrue(c.fetchone()[0])
        conn.close()

    def test_issue_175(self):
        """ The number of fields returned by server is read in wrong way """
        conn = self.connections[0]
        cur = conn.cursor()
        for length in (200, 300):
            columns = ', '.join('c{0} integer'.format(i) for i in range(length))
            sql = 'create table test_field_count ({0})'.format(columns)
            try:
                cur.execute(sql)
                cur.execute('select * from test_field_count')
                assert len(cur.description) == length
            finally:
                cur.execute('drop table if exists test_field_count')


__all__ = ["TestOldIssues", "TestNewIssues", "TestGitHubIssues"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_nextset
from pymysql.tests import base
from pymysql import util

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestNextset(base.PyMySQLTestCase):

    def setUp(self):
        super(TestNextset, self).setUp()
        self.con = self.connections[0]

    def test_nextset(self):
        cur = self.con.cursor()
        cur.execute("SELECT 1; SELECT 2;")
        self.assertEqual([(1,)], list(cur))

        r = cur.nextset()
        self.assertTrue(r)

        self.assertEqual([(2,)], list(cur))
        self.assertIsNone(cur.nextset())

    def test_skip_nextset(self):
        cur = self.con.cursor()
        cur.execute("SELECT 1; SELECT 2;")
        self.assertEqual([(1,)], list(cur))

        cur.execute("SELECT 42")
        self.assertEqual([(42,)], list(cur))

    def test_ok_and_next(self):
        cur = self.con.cursor()
        cur.execute("SELECT 1; commit; SELECT 2;")
        self.assertEqual([(1,)], list(cur))
        self.assertTrue(cur.nextset())
        self.assertTrue(cur.nextset())
        self.assertEqual([(2,)], list(cur))
        self.assertFalse(bool(cur.nextset()))

    @unittest.expectedFailure
    def test_multi_cursor(self):
        cur1 = self.con.cursor()
        cur2 = self.con.cursor()

        cur1.execute("SELECT 1; SELECT 2;")
        cur2.execute("SELECT 42")

        self.assertEqual([(1,)], list(cur1))
        self.assertEqual([(42,)], list(cur2))

        r = cur1.nextset()
        self.assertTrue(r)

        self.assertEqual([(2,)], list(cur1))
        self.assertIsNone(cur1.nextset())

    #TODO: How about SSCursor and nextset?
    # It's very hard to implement correctly...

########NEW FILE########
__FILENAME__ = test_SSCursor
import sys

try:
    from pymysql.tests import base
    import pymysql.cursors
except Exception:
    # For local testing from top-level directory, without installing
    sys.path.append('../pymysql')
    from pymysql.tests import base
    import pymysql.cursors

class TestSSCursor(base.PyMySQLTestCase):
    def test_SSCursor(self):
        affected_rows = 18446744073709551615

        conn = self.connections[0]
        data = [
            ('America', '', 'America/Jamaica'),
            ('America', '', 'America/Los_Angeles'),
            ('America', '', 'America/Lima'),
            ('America', '', 'America/New_York'),
            ('America', '', 'America/Menominee'),
            ('America', '', 'America/Havana'),
            ('America', '', 'America/El_Salvador'),
            ('America', '', 'America/Costa_Rica'),
            ('America', '', 'America/Denver'),
            ('America', '', 'America/Detroit'),]

        try:
            cursor = conn.cursor(pymysql.cursors.SSCursor)

            # Create table
            cursor.execute(('CREATE TABLE tz_data ('
                'region VARCHAR(64),'
                'zone VARCHAR(64),'
                'name VARCHAR(64))'))

            # Test INSERT
            for i in data:
                cursor.execute('INSERT INTO tz_data VALUES (%s, %s, %s)', i)
                self.assertEqual(conn.affected_rows(), 1, 'affected_rows does not match')
            conn.commit()

            # Test fetchone()
            iter = 0
            cursor.execute('SELECT * FROM tz_data')
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                iter += 1

                # Test cursor.rowcount
                self.assertEqual(cursor.rowcount, affected_rows,
                    'cursor.rowcount != %s' % (str(affected_rows)))

                # Test cursor.rownumber
                self.assertEqual(cursor.rownumber, iter,
                    'cursor.rowcount != %s' % (str(iter)))

                # Test row came out the same as it went in
                self.assertEqual((row in data), True,
                    'Row not found in source data')

            # Test fetchall
            cursor.execute('SELECT * FROM tz_data')
            self.assertEqual(len(cursor.fetchall()), len(data),
                'fetchall failed. Number of rows does not match')

            # Test fetchmany
            cursor.execute('SELECT * FROM tz_data')
            self.assertEqual(len(cursor.fetchmany(2)), 2,
                'fetchmany failed. Number of rows does not match')

            # So MySQLdb won't throw "Commands out of sync"
            while True:
                res = cursor.fetchone()
                if res is None:
                    break

            # Test update, affected_rows()
            cursor.execute('UPDATE tz_data SET zone = %s', ['Foo'])
            conn.commit()
            self.assertEqual(cursor.rowcount, len(data),
                'Update failed. affected_rows != %s' % (str(len(data))))

            # Test executemany
            cursor.executemany('INSERT INTO tz_data VALUES (%s, %s, %s)', data)
            self.assertEqual(cursor.rowcount, len(data),
                'executemany failed. cursor.rowcount != %s' % (str(len(data))))

        finally:
            cursor.execute('DROP TABLE tz_data')
            cursor.close()

__all__ = ["TestSSCursor"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = capabilities
#!/usr/bin/env python -O
""" Script to test database capabilities and the DB-API interface
    for functionality and memory leaks.

    Adapted from a script by M-A Lemburg.

"""
import sys
from time import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

PY2 = sys.version_info[0] == 2

class DatabaseTest(unittest.TestCase):

    db_module = None
    connect_args = ()
    connect_kwargs = dict(use_unicode=True, charset="utf8")
    create_table_extra = "ENGINE=INNODB CHARACTER SET UTF8"
    rows = 10
    debug = False

    def setUp(self):
        db = self.db_module.connect(*self.connect_args, **self.connect_kwargs)
        self.connection = db
        self.cursor = db.cursor()
        self.BLOBText = ''.join([chr(i) for i in range(256)] * 100);
        if PY2:
            self.BLOBUText = unicode().join(unichr(i) for i in range(16834))
        else:
            self.BLOBUText = "".join(chr(i) for i in range(16834))
        self.BLOBBinary = self.db_module.Binary(''.join([chr(i) for i in range(256)] * 16))

    leak_test = True

    def tearDown(self):
        if self.leak_test:
            import gc
            del self.cursor
            orphans = gc.collect()
            self.assertFalse(orphans, "%d orphaned objects found after deleting cursor" % orphans)

            del self.connection
            orphans = gc.collect()
            self.assertFalse(orphans, "%d orphaned objects found after deleting connection" % orphans)

    def table_exists(self, name):
        try:
            self.cursor.execute('select * from %s where 1=0' % name)
        except Exception:
            return False
        else:
            return True

    def quote_identifier(self, ident):
        return '"%s"' % ident

    def new_table_name(self):
        i = id(self.cursor)
        while True:
            name = self.quote_identifier('tb%08x' % i)
            if not self.table_exists(name):
                return name
            i = i + 1

    def create_table(self, columndefs):

        """ Create a table using a list of column definitions given in
            columndefs.

            generator must be a function taking arguments (row_number,
            col_number) returning a suitable data object for insertion
            into the table.

        """
        self.table = self.new_table_name()
        self.cursor.execute('CREATE TABLE %s (%s) %s' %
                            (self.table,
                             ',\n'.join(columndefs),
                             self.create_table_extra))

    def check_data_integrity(self, columndefs, generator):
        # insert
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' %
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        if self.debug:
            print(data)
        self.cursor.executemany(insert_statement, data)
        self.connection.commit()
        # verify
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        if self.debug:
            print(l)
        self.assertEqual(len(l), self.rows)
        try:
            for i in range(self.rows):
                for j in range(len(columndefs)):
                    self.assertEqual(l[i][j], generator(i,j))
        finally:
            if not self.debug:
                self.cursor.execute('drop table %s' % (self.table))

    def test_transactions(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*255
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' %
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        self.cursor.executemany(insert_statement, data)
        # verify
        self.connection.commit()
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        self.assertEqual(len(l), self.rows)
        for i in range(self.rows):
            for j in range(len(columndefs)):
                self.assertEqual(l[i][j], generator(i,j))
        delete_statement = 'delete from %s where col1=%%s' % self.table
        self.cursor.execute(delete_statement, (0,))
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.assertFalse(l, "DELETE didn't work")
        self.connection.rollback()
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.assertTrue(len(l) == 1, "ROLLBACK didn't work")
        self.cursor.execute('drop table %s' % (self.table))

    def test_truncation(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*((255-self.rows//2)+row)
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' %
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))

        try:
            self.cursor.execute(insert_statement, (0, '0'*256))
        except Warning:
            if self.debug: print(self.cursor.messages)
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long column did not generate warnings/exception with single insert")

        self.connection.rollback()

        try:
            for i in range(self.rows):
                data = []
                for j in range(len(columndefs)):
                    data.append(generator(i,j))
                self.cursor.execute(insert_statement,tuple(data))
        except Warning:
            if self.debug: print(self.cursor.messages)
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with execute()")

        self.connection.rollback()

        try:
            data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                     for i in range(self.rows) ]
            self.cursor.executemany(insert_statement, data)
        except Warning:
            if self.debug: print(self.cursor.messages)
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with executemany()")

        self.connection.rollback()
        self.cursor.execute('drop table %s' % (self.table))

    def test_CHAR(self):
        # Character data
        def generator(row,col):
            return ('%i' % ((row+col) % 10)) * 255
        self.check_data_integrity(
            ('col1 char(255)','col2 char(255)'),
            generator)

    def test_INT(self):
        # Number data
        def generator(row,col):
            return row*row
        self.check_data_integrity(
            ('col1 INT',),
            generator)

    def test_DECIMAL(self):
        # DECIMAL
        def generator(row,col):
            from decimal import Decimal
            return Decimal("%d.%02d" % (row, col))
        self.check_data_integrity(
            ('col1 DECIMAL(5,2)',),
            generator)

    def test_DATE(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.DateFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATE',),
                 generator)

    def test_TIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimeFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_DATETIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATETIME',),
                 generator)

    def test_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_fractional_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313+row*0.7*col/3.0)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_LONG(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBUText # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col1 INT', 'col2 LONG'),
                 generator)

    def test_TEXT(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBUText[:5192] # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col1 INT', 'col2 TEXT'),
                 generator)

    def test_LONG_BYTE(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 LONG BYTE'),
                 generator)

    def test_BLOB(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 BLOB'),
                 generator)

########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite.

    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__  = '$Id$'
__version__ = '$Revision$'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import time

# $Log$
# Revision 1.1.2.1  2006/02/25 03:44:32  adustman
# Generic DB-API unit test module
#
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#

class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this
        test case to ensure compiliance with the DB-API. It is
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20
        class mytest(dbapi20.DatabaseAPI20Test):
           [...]

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = () # List of arguments to pass to connect
    connect_kw_args = {} # Keyword arguments for connect
    table_prefix = 'dbapi20test_' # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    lowerfunc = 'lower' # Name of stored procedure to convert string->lowercase

    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self,cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self,cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required cleanup
            if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for ddl in (self.xddl1,self.xddl2):
                try:
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error:
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args,**self.connect_kw_args
                )
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel,'2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.assertTrue(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.assertTrue(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.assertTrue(issubclass(self.driver.Warning,Exception))
        self.assertTrue(issubclass(self.driver.Error,Exception))
        self.assertTrue(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.NotSupportedError,self.driver.Error)
            )

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.assertTrue(con.Warning is drv.Warning)
        self.assertTrue(con.Error is drv.Error)
        self.assertTrue(con.InterfaceError is drv.InterfaceError)
        self.assertTrue(con.DatabaseError is drv.DatabaseError)
        self.assertTrue(con.OperationalError is drv.OperationalError)
        self.assertTrue(con.IntegrityError is drv.IntegrityError)
        self.assertTrue(con.InternalError is drv.InternalError)
        self.assertTrue(con.ProgrammingError is drv.ProgrammingError)
        self.assertTrue(con.NotSupportedError is drv.NotSupportedError)


    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con,'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass

    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze),1)
            self.assertEqual(len(booze[0]),1)
            self.assertEqual(booze[0][0],'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.description,None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)'
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(len(cur.description),1,
                'cursor.description describes too many columns'
                )
            self.assertEqual(len(cur.description[0]),7,
                'cursor.description[x] tuples must have 7 elements'
                )
            self.assertEqual(cur.description[0][0].lower(),'name',
                'cursor.description[x][0] must return column name'
                )
            self.assertEqual(cur.description[0][1],self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                    % cur.description[0][1]
                )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(cur.description,None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)'
                )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements'
                )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertTrue(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertTrue(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements'
                )
        finally:
            con.close()

    lower_func = 'lower'
    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur,'callproc'):
                r = cur.callproc(self.lower_func,('FOO',))
                self.assertEqual(len(r),1)
                self.assertEqual(r[0],'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r),1,'callproc produced no result set')
                self.assertEqual(len(r[0]),1,
                    'callproc produced invalid result set'
                    )
                self.assertEqual(r[0][0],'foo',
                    'callproc produced invalid results'
                    )
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error,self.executeDDL1,cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error,con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error,con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self,cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix
            ))
        self.assertTrue(cur.rowcount in (-1,1))

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        else:
            self.fail('Invalid paramstyle')
        self.assertTrue(cur.rowcount in (-1,1))

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res),2,'cursor.fetchall returned too few rows')
        beers = [res[0][0],res[1][0]]
        beers.sort()
        self.assertEqual(beers[0],"Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )
        self.assertEqual(beers[1],"Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [ ("Cooper's",) , ("Boag's",) ]
            margs = [ {'beer': "Cooper's"}, {'beer': "Boag's"} ]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix
                        ),
                    margs
                    )
            else:
                self.fail('Unknown paramstyle')
            self.assertTrue(cur.rowcount in (-1,2),
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(len(res),2,
                'cursor.fetchall retrieved incorrect number of rows'
                )
            beers = [res[0][0],res[1][0]]
            beers.sort()
            self.assertEqual(beers[0],"Boag's",'incorrect data retrieved')
            self.assertEqual(beers[1],"Cooper's",'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.assertTrue(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if no more rows available'
                )
            self.assertTrue(cur.rowcount in (-1,1))
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix,s)
                for s in self.samples
            ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            #issuing a query
            self.assertRaises(self.driver.Error,cur.fetchmany,4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(len(r),1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.'
                )
            cur.arraysize=10
            r = cur.fetchmany(3) # Should get 3 rows
            self.assertEqual(len(r),3,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should get 2 more
            self.assertEqual(len(r),2,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should be an empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted'
            )
            self.assertTrue(cur.rowcount in (-1,6))

            # Same as above, using cursor.arraysize
            cur.arraysize=4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany() # Should get 4 rows
            self.assertEqual(len(r),4,
                'cursor.arraysize not being honoured by fetchmany'
                )
            r = cur.fetchmany() # Should get 2 more
            self.assertEqual(len(r),2)
            r = cur.fetchmany() # Should be an empty sequence
            self.assertEqual(len(r),0)
            self.assertTrue(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.assertTrue(cur.rowcount in (-1,6))
            self.assertEqual(len(rows),6)
            self.assertEqual(len(rows),6)
            rows = [r[0] for r in rows]
            rows.sort()

            # Make sure we get the right data back out
            for i in range(0,6):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany'
                    )

            rows = cur.fetchmany() # Should return an empty list
            self.assertEqual(len(rows),0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched'
                )
            self.assertTrue(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.assertTrue(cur.rowcount in (-1,0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )

        finally:
            con.close()

    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1  = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4  = cur.fetchone()
            rows56 = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,6))
            self.assertEqual(len(rows23),2,
                'fetchmany returned incorrect number of rows'
                )
            self.assertEqual(len(rows56),2,
                'fetchall returned incorrect number of rows'
                )

            rows = [rows1[0]]
            rows.extend([rows23[0][0],rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0],rows56[1][0]])
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved or inserted'
                    )
        finally:
            con.close()

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the
            number of rows in booze then "name from booze"
        '''
        raise NotImplementedError('Helper not implemented')
        #sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        #"""
        #cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError('Helper not implemented')
        #cur.execute("drop procedure deleteme")

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    def test_nextset(self):
        raise NotImplementedError('Drivers need to override this test')

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.assertTrue(hasattr(cur,'arraysize'),
                'cursor.arraysize must be defined'
                )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes( (25,) )
            self._paraminsert(cur) # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000,0)
            self._paraminsert(cur) # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError('Driver need to override this test')

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute('insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r),1)
            self.assertEqual(len(r[0]),1)
            self.assertEqual(r[0][0],None,'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002,12,25)
        d2 = self.driver.DateFromTicks(time.mktime((2002,12,25,0,0,0,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13,45,30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001,1,1,13,45,30,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002,12,25,13,45,30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002,12,25,13,45,30,0,0,0))
            )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary('Something')
        b = self.driver.Binary('')

    def test_STRING(self):
        self.assertTrue(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.assertTrue(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.assertTrue(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.assertTrue(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.assertTrue(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )

########NEW FILE########
__FILENAME__ = test_MySQLdb_capabilities
#!/usr/bin/env python
from . import capabilities
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import pymysql
from pymysql.tests import base
import warnings

warnings.filterwarnings('error')

class test_MySQLdb(capabilities.DatabaseTest):

    db_module = pymysql
    connect_args = ()
    connect_kwargs = base.PyMySQLTestCase.databases[0].copy()
    connect_kwargs.update(dict(read_default_file='~/.my.cnf',
                          use_unicode=True,
                          charset='utf8', sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL"))

    create_table_extra = "ENGINE=INNODB CHARACTER SET UTF8"
    leak_test = False

    def quote_identifier(self, ident):
        return "`%s`" % ident

    def test_TIME(self):
        from datetime import timedelta
        def generator(row,col):
            return timedelta(0, row*8000)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_TINYINT(self):
        # Number data
        def generator(row,col):
            v = (row*row) % 256
            if v > 127:
                v = v-256
            return v
        self.check_data_integrity(
            ('col1 TINYINT',),
            generator)

    def test_stored_procedures(self):
        db = self.connection
        c = self.cursor
        try:
            self.create_table(('pos INT', 'tree CHAR(20)'))
            c.executemany("INSERT INTO %s (pos,tree) VALUES (%%s,%%s)" % self.table,
                          list(enumerate('ash birch cedar larch pine'.split())))
            db.commit()

            c.execute("""
            CREATE PROCEDURE test_sp(IN t VARCHAR(255))
            BEGIN
                SELECT pos FROM %s WHERE tree = t;
            END
            """ % self.table)
            db.commit()

            c.callproc('test_sp', ('larch',))
            rows = c.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], 3)
            c.nextset()
        finally:
            c.execute("DROP PROCEDURE IF EXISTS test_sp")
            c.execute('drop table %s' % (self.table))

    def test_small_CHAR(self):
        # Character data
        def generator(row,col):
            i = ((row+1)*(col+1)+62)%256
            if i == 62: return ''
            if i == 63: return None
            return chr(i)
        self.check_data_integrity(
            ('col1 char(1)','col2 char(1)'),
            generator)

    def test_bug_2671682(self):
        from pymysql.constants import ER
        try:
            self.cursor.execute("describe some_non_existent_table");
        except self.connection.ProgrammingError as msg:
            self.assertEqual(msg.args[0], ER.NO_SUCH_TABLE)

    def test_ping(self):
        self.connection.ping()

    def test_literal_int(self):
        self.assertTrue("2" == self.connection.literal(2))

    def test_literal_float(self):
        self.assertTrue("3.1415" == self.connection.literal(3.1415))

    def test_literal_string(self):
        self.assertTrue("'foo'" == self.connection.literal("foo"))


if __name__ == '__main__':
    if test_MySQLdb.leak_test:
        import gc
        gc.enable()
        gc.set_debug(gc.DEBUG_LEAK)
    unittest.main()

########NEW FILE########
__FILENAME__ = test_MySQLdb_dbapi20
#!/usr/bin/env python
from . import dbapi20
import pymysql
from pymysql.tests import base

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class test_MySQLdb(dbapi20.DatabaseAPI20Test):
    driver = pymysql
    connect_args = ()
    connect_kw_args = base.PyMySQLTestCase.databases[0].copy()
    connect_kw_args.update(dict(read_default_file='~/.my.cnf',
                                charset='utf8',
                                sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL"))

    def test_setoutputsize(self): pass
    def test_setoutputsize_basic(self): pass
    def test_nextset(self): pass

    """The tests on fetchone and fetchall and rowcount bogusly
    test for an exception if the statement cannot return a
    result set. MySQL always returns a result set; it's just that
    some things return empty result sets."""

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
##             self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )

        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.assertTrue(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
##             self.assertEqual(cur.fetchone(),None,
##                 'cursor.fetchone should return None if no more rows available'
##                 )
            self.assertTrue(cur.rowcount in (-1,1))
        finally:
            con.close()

    # Same complaint as for fetchall and fetchone
    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount should be -1 after executing no-result '
##                 'statements'
##                 )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.assertTrue(cur.rowcount in (-1,1),
##                 'cursor.rowcount should == number or rows inserted, or '
##                 'set to -1 after executing an insert statement'
##                 )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertTrue(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount not being reset to -1 after executing '
##                 'no-result statements'
##                 )
        finally:
            con.close()

    def test_callproc(self):
        pass # performed in test_MySQL_capabilities

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the
            number of rows in booze then "name from booze"
        '''
        sql="""
           create procedure deleteme()
           begin
               select count(*) from %(tp)sbooze;
               select name from %(tp)sbooze;
           end
        """ % dict(tp=self.table_prefix)
        cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        cur.execute("drop procedure deleteme")

    @unittest.expectedFailure
    def test_nextset(self):
        from warnings import warn
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                if s:
                    empty = cur.fetchall()
                    self.assertEqual(len(empty), 0,
                                      "non-empty result set after other result sets")
                    #warn("Incompatibility: MySQL returns an empty result set for the CALL itself",
                    #     Warning)
                #assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_MySQLdb_nonstandard
import sys
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import pymysql
_mysql = pymysql
from pymysql.constants import FIELD_TYPE
from pymysql.tests import base
from pymysql._compat import PY2, long_type

if not PY2:
    basestring = str


class TestDBAPISet(unittest.TestCase):
    def test_set_equality(self):
        self.assertTrue(pymysql.STRING == pymysql.STRING)

    def test_set_inequality(self):
        self.assertTrue(pymysql.STRING != pymysql.NUMBER)

    def test_set_equality_membership(self):
        self.assertTrue(FIELD_TYPE.VAR_STRING == pymysql.STRING)

    def test_set_inequality_membership(self):
        self.assertTrue(FIELD_TYPE.DATE != pymysql.STRING)


class CoreModule(unittest.TestCase):
    """Core _mysql module features."""

    def test_NULL(self):
        """Should have a NULL constant."""
        self.assertEqual(_mysql.NULL, 'NULL')

    def test_version(self):
        """Version information sanity."""
        self.assertTrue(isinstance(_mysql.__version__, basestring))

        self.assertTrue(isinstance(_mysql.version_info, tuple))
        self.assertEqual(len(_mysql.version_info), 5)

    def test_client_info(self):
        self.assertTrue(isinstance(_mysql.get_client_info(), basestring))

    def test_thread_safe(self):
        self.assertTrue(isinstance(_mysql.thread_safe(), int))


class CoreAPI(unittest.TestCase):
    """Test _mysql interaction internals."""

    def setUp(self):
        kwargs = base.PyMySQLTestCase.databases[0].copy()
        kwargs["read_default_file"] = "~/.my.cnf"
        self.conn = _mysql.connect(**kwargs)

    def tearDown(self):
        self.conn.close()

    def test_thread_id(self):
        tid = self.conn.thread_id()
        self.assertTrue(isinstance(tid, (int, long_type)),
                        "thread_id didn't return an integral value.")

        self.assertRaises(TypeError, self.conn.thread_id, ('evil',),
                          "thread_id shouldn't accept arguments.")

    def test_affected_rows(self):
        self.assertEqual(self.conn.affected_rows(), 0,
                          "Should return 0 before we do anything.")


    #def test_debug(self):
        ## FIXME Only actually tests if you lack SUPER
        #self.assertRaises(pymysql.OperationalError,
                          #self.conn.dump_debug_info)

    def test_charset_name(self):
        self.assertTrue(isinstance(self.conn.character_set_name(), basestring),
                        "Should return a string.")

    def test_host_info(self):
        assert isinstance(self.conn.get_host_info(), basestring), "should return a string"

    def test_proto_info(self):
        self.assertTrue(isinstance(self.conn.get_proto_info(), int),
                        "Should return an int.")

    def test_server_info(self):
        if sys.version_info[0] == 2:
            self.assertTrue(isinstance(self.conn.get_server_info(), basestring),
                            "Should return an str.")
        else:
            self.assertTrue(isinstance(self.conn.get_server_info(), basestring),
                            "Should return an str.")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = times
from time import localtime
from datetime import date, datetime, time, timedelta

Date = date
Time = time
TimeDelta = timedelta
Timestamp = datetime

def DateFromTicks(ticks):
    return date(*localtime(ticks)[:3])

def TimeFromTicks(ticks):
    return time(*localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    return datetime(*localtime(ticks)[:6])

########NEW FILE########
__FILENAME__ = util
import struct

def byte2int(b):
    if isinstance(b, int):
        return b
    else:
        return struct.unpack("!B", b)[0]

def int2byte(i):
    return struct.pack("!B", i)

def join_bytes(bs):
    if len(bs) == 0:
        return ""
    else:
        rv = bs[0]
        for b in bs[1:]:
            rv += b
        return rv

########NEW FILE########
__FILENAME__ = _compat
import sys

PY2 = sys.version_info[0] == 2
PYPY = hasattr(sys, 'pypy_translation_info')
JYTHON = sys.platform.startswith('java')
IRONPYTHON = sys.platform == 'cli'

if PY2:
    range_type = xrange
    text_type = unicode
    long_type = long
    str_type = basestring
else:
    range_type = range
    text_type = str
    long_type = int
    str_type = str

########NEW FILE########
__FILENAME__ = _socketio
"""
SocketIO imported from socket module in Python 3.

Copyright (c) 2001-2013 Python Software Foundation; All Rights Reserved.
"""

from socket import *
import io
import errno

__all__ = ['SocketIO']

EINTR = errno.EINTR
_blocking_errnos = { errno.EAGAIN, errno.EWOULDBLOCK }

class SocketIO(io.RawIOBase):

    """Raw I/O implementation for stream sockets.

    This class supports the makefile() method on sockets.  It provides
    the raw I/O interface on top of a socket object.
    """

    # One might wonder why not let FileIO do the job instead.  There are two
    # main reasons why FileIO is not adapted:
    # - it wouldn't work under Windows (where you can't used read() and
    #   write() on a socket handle)
    # - it wouldn't work with socket timeouts (FileIO would ignore the
    #   timeout and consider the socket non-blocking)

    # XXX More docs

    def __init__(self, sock, mode):
        if mode not in ("r", "w", "rw", "rb", "wb", "rwb"):
            raise ValueError("invalid mode: %r" % mode)
        io.RawIOBase.__init__(self)
        self._sock = sock
        if "b" not in mode:
            mode += "b"
        self._mode = mode
        self._reading = "r" in mode
        self._writing = "w" in mode
        self._timeout_occurred = False

    def readinto(self, b):
        """Read up to len(b) bytes into the writable buffer *b* and return
        the number of bytes read.  If the socket is non-blocking and no bytes
        are available, None is returned.

        If *b* is non-empty, a 0 return value indicates that the connection
        was shutdown at the other end.
        """
        self._checkClosed()
        self._checkReadable()
        if self._timeout_occurred:
            raise IOError("cannot read from timed out object")
        while True:
            try:
                return self._sock.recv_into(b)
            except timeout:
                self._timeout_occurred = True
                raise
            except error as e:
                n = e.args[0]
                if n == EINTR:
                    continue
                if n in _blocking_errnos:
                    return None
                raise

    def write(self, b):
        """Write the given bytes or bytearray object *b* to the socket
        and return the number of bytes written.  This can be less than
        len(b) if not all data could be written.  If the socket is
        non-blocking and no bytes could be written None is returned.
        """
        self._checkClosed()
        self._checkWritable()
        try:
            return self._sock.send(b)
        except error as e:
            # XXX what about EINTR?
            if e.args[0] in _blocking_errnos:
                return None
            raise

    def readable(self):
        """True if the SocketIO is open for reading.
        """
        if self.closed:
            raise ValueError("I/O operation on closed socket.")
        return self._reading

    def writable(self):
        """True if the SocketIO is open for writing.
        """
        if self.closed:
            raise ValueError("I/O operation on closed socket.")
        return self._writing

    def seekable(self):
        """True if the SocketIO is open for seeking.
        """
        if self.closed:
            raise ValueError("I/O operation on closed socket.")
        return super().seekable()

    def fileno(self):
        """Return the file descriptor of the underlying socket.
        """
        self._checkClosed()
        return self._sock.fileno()

    @property
    def name(self):
        if not self.closed:
            return self.fileno()
        else:
            return -1

    @property
    def mode(self):
        return self._mode

    def close(self):
        """Close the SocketIO object.  This doesn't close the underlying
        socket, except if all references to it have disappeared.
        """
        if self.closed:
            return
        io.RawIOBase.close(self)
        self._sock._decref_socketios()
        self._sock = None


########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pymysql._compat import PYPY, JYTHON, IRONPYTHON

if not (PYPY or JYTHON or IRONPYTHON):
    import atexit
    import gc
    gc.set_debug(gc.DEBUG_UNCOLLECTABLE)

    @atexit.register
    def report_uncollectable():
        if not gc.garbage:
            print("No garbages!")
            return
        print('uncollectable objects')
        for obj in gc.garbage:
            print(obj)
            if hasattr(obj, '__dict__'):
                print(obj.__dict__)
            for ref in gc.get_referrers(obj):
                print("referrer:", ref)
            print('---')

import pymysql.tests
unittest.main(pymysql.tests)

########NEW FILE########
