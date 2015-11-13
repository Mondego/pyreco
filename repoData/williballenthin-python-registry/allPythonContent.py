__FILENAME__ = changelog
#!/usr/bin/env python

from Registry import _version_
from datetime import datetime

with open("debian/changelog", "w") as fd:
    fd.write("""python-registry (%s) unstable; urgency=low

  * Upstream release

-- Willi Ballenthin <willi.ballenthin@gmail.com>  %s
""" % (_version_, datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')))


########NEW FILE########
__FILENAME__ = Registry
#!/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011, 2012 Willi Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from __future__ import print_function

import sys
import ntpath
from enum import Enum

from . import RegistryParse

RegSZ = 0x0001
RegExpandSZ = 0x0002
RegBin = 0x0003
RegDWord = 0x0004
RegMultiSZ = 0x0007
RegQWord = 0x000B
RegNone = 0x0000
RegBigEndian = 0x0005
RegLink = 0x0006
RegResourceList = 0x0008
RegFullResourceDescriptor = 0x0009
RegResourceRequirementsList = 0x000A

class HiveType(Enum):
    UNKNOWN = ""
    NTUSER = "ntuser.dat"
    SAM = "sam"
    SECURITY = "security"
    SOFTWARE = "software"
    SYSTEM = "system"
    USRCLASS = "usrclass.dat"


class RegistryKeyHasNoParentException(RegistryParse.RegistryStructureDoesNotExist):
    """
    """
    def __init__(self, value):
        """
        Constructor.
        Arguments:
        - `value`: A string description.
        """
        super(RegistryKeyHasNoParentException, self).__init__(value)

    def __str__(self):
        return "Registry key has no parent key: %s" % (self._value)


class RegistryKeyNotFoundException(RegistryParse.RegistryStructureDoesNotExist):
    """
    """
    def __init__(self, value):
        """

        Arguments:
        - `value`:
        """
        super(RegistryKeyNotFoundException, self).__init__(value)

    def __str__(self):
        return "Registry key not found: %s" % (self._value)

class RegistryValueNotFoundException(RegistryParse.RegistryStructureDoesNotExist):
    """
    """
    def __init__(self, value):
        """

        Arguments:
        - `value`:
        """
        super(RegistryValueNotFoundException, self).__init__(value)

    def __str__(self):
        return "Registry value not found: %s" % (self._value)

class RegistryValue(object):
    """
    This is a high level structure for working with the Windows Registry.
    It represents the 3-tuple of (name, type, value) associated with 
      a registry value.
    """
    def __init__(self, vkrecord):
        self._vkrecord = vkrecord

    def name(self):
        """
        Get the name of the value as a string.
        The name of the default value is returned as "(default)".
        """
        if self._vkrecord.has_name():
            return self._vkrecord.name()
        else:
            return  "(default)"

    def value_type(self):
        """
        Get the type of the value as an integer constant.

        One of:
         - RegSZ = 0x0001
         - RegExpandSZ = 0x0002
         - RegBin = 0x0003
         - RegDWord = 0x0004
         - RegMultiSZ = 0x0007
         - RegQWord = 0x000B
         - RegNone = 0x0000
         - RegBigEndian = 0x0005
         - RegLink = 0x0006
         - RegResourceList = 0x0008
         - RegFullResourceDescriptor = 0x0009
         - RegResourceRequirementsList = 0x000A
        """
        return self._vkrecord.data_type()

    def value_type_str(self):
        """
        Get the type of the value as a string.

        One of:
         - RegSZ
         - RegExpandSZ
         - RegBin
         - RegDWord
         - RegMultiSZ
         - RegQWord
         - RegNone
         - RegBigEndian
         - RegLink
         - RegResourceList
         - RegFullResourceDescriptor
         - RegResourceRequirementsList
        """
        return self._vkrecord.data_type_str()

    def value(self):
        return self._vkrecord.data()


class RegistryKey(object):
    """
    A high level structure for use in traversing the Windows Registry.
    A RegistryKey is a node in a tree-like structure.
    A RegistryKey may have a set of values associated with it,
      as well as a last modified timestamp.
    """
    def __init__(self, nkrecord):
        """

        Arguments:
        - `NKRecord`:
        """
        self._nkrecord = nkrecord

    def __str__(self):
        return "Registry Key %s with %d values and %d subkeys" % \
            (self.path(), len(self.values()), len(self.subkeys()))

    def __getitem__(self, key):
        return self.value(key)

    def timestamp(self):
        """
        Get the last modified timestamp as a Python datetime.
        """
        return self._nkrecord.timestamp()

    def name(self):
        """
        Get the name of the key as a string.

        For example, "Windows" if the key path were
        /{hive name}/SOFTWARE/Microsoft/Windows
        See RegistryKey.path() to get the complete key name.
        """
        return self._nkrecord.name()

    def path(self):
        """
        Get the full path of the RegistryKey as a string.
        For example, "/{hive name}/SOFTWARE/Microsoft/Windows"
        """
        return self._nkrecord.path()

    def parent(self):
        """
        Get the parent RegistryKey of this key, or raise
        RegistryKeyHasNoParentException if it does not exist (for example,
        the root key has no parent).
        """
        # there may be a memory inefficiency here, since we create
        # a new RegistryKey from the NKRecord parent key, rather
        # than using the parent of this instance, if it exists.
        try:
            return RegistryKey(self._nkrecord.parent_key())
        except RegistryParse.ParseException:
            raise RegistryKeyHasNoParentException(self.name())

    def subkeys(self):
        """
        Return a list of all subkeys.
        Each element in the list is a RegistryKey.
        If the key has no subkeys, the empty list is returned.
        """
        if self._nkrecord.subkey_number() == 0:
            return []

        l = self._nkrecord.subkey_list()
        return [RegistryKey(k) for k in l.keys()]

    def subkey(self, name):
        """
        Return the subkey with a given name as a RegistryKey.
        Raises RegistryKeyNotFoundException if the subkey with 
          the given name does not exist.
        """
        if self._nkrecord.subkey_number() == 0:
            raise RegistryKeyNotFoundException(self.path() + "\\" + name)

        for k in self._nkrecord.subkey_list().keys():
            if k.name().lower() == name.lower():
                return RegistryKey(k)
        raise RegistryKeyNotFoundException(self.path() + "\\" + name)

    def values(self):
        """
        Return a list containing the values associated with this RegistryKey.
        Each element of the list will be a RegistryValue.
        If there are no values associated with this RegistryKey, then the
        empty list is returned.
        """
        try:
            return [RegistryValue(v) for v in self._nkrecord.values_list().values()]
        except RegistryParse.RegistryStructureDoesNotExist:
            return []

    def value(self, name):
        """
        Return the value with the given name as a RegistryValue.
        Raises RegistryValueNotFoundExceptiono if the value with
          the given name does not exist.
        """
        if name == "(default)":
            name = ""
        for v in self._nkrecord.values_list().values():
            if v.name().lower() == name.lower():
                return RegistryValue(v)
        raise RegistryValueNotFoundException(self.path() + " : " + name)

    def find_key(self, path):
        """
        Perform a search for a RegistryKey with a specific path.
        """
        if len(path) == 0:
            return self

        (immediate, _, future) = path.partition("\\")
        return self.subkey(immediate).find_key(future)
        
    def values_number(self):
    	"""
    	Return the number of values associated with this key
    	"""
    	return self._nkrecord.values_number()
    	
    def subkeys_number(self):
    	"""
    	Return the number of subkeys associated with this key
    	"""
    	return self._nkrecord.subkey_number()


class Registry(object):
    """
    A class for parsing and reading from a Windows Registry file.
    """
    def __init__(self, filelikeobject):
        """
        Constructor.
        Arguments:
        - `filelikeobject`: A file-like object with a .read() method.
              If a Python string is passed, it is interpreted as a filename,
              and the corresponding file is opened.
        """
        try:
            self._buf = filelikeobject.read()
        except AttributeError:
            with open(filelikeobject, "rb") as f:
                self._buf = f.read()
        self._regf = RegistryParse.REGFBlock(self._buf, 0, False)

    def hive_name(self):
        """Returns the internal file name"""
        return self._regf.hive_name()

    def hive_type(self):
        """Returns the hive type"""
        temp = self.hive_name()
        temp = temp.replace('\\??\\', '')
        temp = ntpath.basename(temp)

        if temp.lower() == HiveType.NTUSER.value:
            return HiveType.NTUSER
        elif temp.lower() == HiveType.SAM.value:
            return HiveType.SAM
        elif temp.lower() == HiveType.SECURITY.value:
            return HiveType.SECURITY
        elif temp.lower() == HiveType.SOFTWARE.value:
            return HiveType.SOFTWARE
        elif temp.lower() == HiveType.SYSTEM.value:
            return HiveType.SYSTEM
        elif temp.lower() == HiveType.USRCLASS.value:
            return HiveType.USRCLASS
        else:
            return HiveType.UNKNOWN

    def root(self):
        """
        Return the first RegistryKey in the hive.
        """
        return RegistryKey(self._regf.first_key())

    def open(self, path):
        """
        Return a RegistryKey by full path.
        Subkeys are separated by the backslash character ('\').
        A trailing backslash may or may not be present.
        The hive name should not be included.
        """
        # is the first registry key always the root?
        # are there any other keys at this
        # level? is this the name of the hive?
        return RegistryKey(self._regf.first_key()).find_key(path)

def print_all(key):
    if len(key.subkeys()) == 0:
        print(key.path())
    else:
        for k in key.subkeys():
            print_all(k)

if __name__ == '__main__':
    r = Registry(sys.argv[1])
    print_all(r.root())

########NEW FILE########
__FILENAME__ = RegistryParse
#!/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# Added for python2-3 compatibility
from __future__ import print_function
from __future__ import unicode_literals

import struct
from datetime import datetime

# Constants
RegSZ = 0x0001
RegExpandSZ = 0x0002
RegBin = 0x0003
RegDWord = 0x0004
RegMultiSZ = 0x0007
RegQWord = 0x000B
RegNone = 0x0000
RegBigEndian = 0x0005
RegLink = 0x0006
RegResourceList = 0x0008
RegFullResourceDescriptor = 0x0009
RegResourceRequirementsList = 0x000A

_global_warning_messages = []
def warn(msg):
    if msg not in _global_warning_messages:
        _global_warning_messages.append(msg)
        print("Warning: %s" % (msg))


def parse_windows_timestamp(qword):
    # see http://integriography.wordpress.com/2010/01/16/using-phython-to-parse-and-present-windows-64-bit-timestamps/
    return datetime.utcfromtimestamp(float(qword) * 1e-7 - 11644473600 )


class RegistryException(Exception):
    """
    Base Exception class for Windows Registry access.
    """

    def __init__(self, value):
        """
        Constructor.
        Arguments:
        - `value`: A string description.
        """
        super(RegistryException, self).__init__()
        self._value = value

    def __str__(self):
        return "Registry Exception: %s" % (self._value)


class RegistryStructureDoesNotExist(RegistryException):
    """
    Exception to be raised when a structure or block is requested which does not exist.
    For example, asking for the ValuesList structure of an NKRecord that has no values
    (and therefore no ValuesList) should result in this exception.
    """
    def __init__(self, value):
        """
        Constructor.
        Arguments:
        - `value`: A string description.
        """
        super(RegistryStructureDoesNotExist, self).__init__(value)

    def __str__(self):
        return "Registry Structure Does Not Exist Exception: %s" % (self._value)


class ParseException(RegistryException):
    """
    An exception to be thrown during Windows Registry parsing, such as
    when an invalid header is encountered.
    """
    def __init__(self, value):
        """
        Constructor.
        Arguments:
        - `value`: A string description.
        """
        super(ParseException, self).__init__(value)

    def __str__(self):
        return "Registry Parse Exception(%s)" % (self._value)


class UnknownTypeException(RegistryException):
    """
    An exception to be raised when an unknown data type is encountered.
    Supported data types current consist of
     - RegSZ
     - RegExpandSZ
     - RegBin
     - RegDWord
     - RegMultiSZ
     - RegQWord
     - RegNone
     - RegBigEndian
     - RegLink
     - RegResourceList
     - RegFullResourceDescriptor
     - RegResourceRequirementsList
    """
    def __init__(self, value):
        """
        Constructor.
        Arguments:
        - `value`: A string description.
        """
        super(UnknownTypeException, self).__init__(value)

    def __str__(self):
        return "Unknown Type Exception(%s)" % (self._value)


class RegistryBlock(object):
    """
    Base class for structure blocks in the Windows Registry.
    A block is associated with a offset into a byte-string.

    All blocks (besides the root) also have a parent member, which refers to
    a RegistryBlock that contains a reference to this block, an is found at a
    hierarchically superior rank. Note, by following the parent links upwards,
    the root block should be accessible (aka. there should not be any loops)
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        self._buf = buf
        self._offset = offset
        self._parent = parent

    def unpack_word(self, offset):
        """
        Returns a little-endian WORD (2 bytes) from the relative offset.
        Arguments:
        - `offset`: The relative offset from the start of the block.
        """
        return struct.unpack_from(str("<H"), self._buf, self._offset + offset)[0]

    def unpack_dword(self, offset):
        """
        Returns a little-endian DWORD (4 bytes) from the relative offset.
        Arguments:
        - `offset`: The relative offset from the start of the block.
        """
        return struct.unpack_from(str("<I"), self._buf, self._offset + offset)[0]

    def unpack_int(self, offset):
        """
        Returns a little-endian signed integer (4 bytes) from the relative offset.
        Arguments:
        - `offset`: The relative offset from the start of the block.
        """
        return struct.unpack_from(str("<i"), self._buf, self._offset + offset)[0]

    def unpack_qword(self, offset):
        """
        Returns a little-endian QWORD (8 bytes) from the relative offset.
        Arguments:
        - `offset`: The relative offset from the start of the block.
        """
        return struct.unpack_from(str("<Q"), self._buf, self._offset + offset)[0]

    def unpack_string(self, offset, length):
        """
        Returns a byte string from the relative offset with the given length.
        Arguments:
        - `offset`: The relative offset from the start of the block.
        - `length`: The length of the string.
        """
        return struct.unpack_from(str("<%ds") % (length), self._buf, self._offset + offset)[0]

    def absolute_offset(self, offset):
        """
        Get the absolute offset from an offset relative to this block
        Arguments:
        - `offset`: The relative offset into this block.
        """
        return self._offset + offset

    def parent(self):
        """
        Get the parent block. See the class documentation for what the parent link is.
        """
        return self._parent

    def offset(self):
        """
        Equivalent to self.absolute_offset(0x0), which is the starting offset of this block.
        """
        return self._offset


class REGFBlock(RegistryBlock):
    """
    The Windows Registry file header. This block has a length of 4k, although
    only the first 0x200 bytes are generally used.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(REGFBlock, self).__init__(buf, offset, parent)

        _id = self.unpack_dword(0)
        if _id != 0x66676572:
            raise ParseException("Invalid REGF ID")

        _seq1 = self.unpack_dword(0x4)
        _seq2 = self.unpack_dword(0x8)

        if _seq1 != _seq2:
            # the registry was not synchronized
            pass

        # TODO: compute checksum and check

    def major_version(self):
        """
        Get the major version of the Windows Registry file format
        in use as an unsigned integer.
        """
        return self.unpack_dword(0x14)

    def minor_version(self):
        """
        Get the minor version of the Windows Registry file format
        in use as an unsigned integer.
        """
        return self.unpack_dword(0x18)

    def hive_name(self):
        """
        Get the hive name of the open Windows Registry file as a string.
        """
        return self.unpack_string(0x30, 64).decode("utf-16le").rstrip("\x00")

    def last_hbin_offset(self):
        """
        Get the buffer offset of the last HBINBlock as an unsigned integer.
        """
        return self.unpack_dword(0x28)

    def first_key(self):
        first_hbin = next(self.hbins())

        key_offset = first_hbin.absolute_offset(self.unpack_dword(0x24))

        d = HBINCell(self._buf, key_offset, first_hbin)
        return NKRecord(self._buf, d.data_offset(), first_hbin)

    def hbins(self):
        """
        A generator that enumerates all HBIN (HBINBlock) structures in this Windows Registry.
        """
        h = HBINBlock(self._buf, 0x1000, self) # sorry, but 0x1000 is a magic number
        yield h

        while h.has_next():
            h = h.next()
            yield h


class HBINCell(RegistryBlock):
    """
    HBIN data cell. An HBINBlock is continuously filled with HBINCell structures.
    The general structure is the length of the block, followed by a blob of data.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(HBINCell, self).__init__(buf, offset, parent)
        self._size = self.unpack_int(0x0)

    def __str__(self):
        if self.is_free():
            return "HBIN Cell (free) at 0x%x" % (self._offset)
        else:
            return "HBIN Cell at 0x%x" % (self._offset)

    def is_free(self):
        """
        Is the cell free?
        """
        return self._size > 0

    def size(self):
        """
        Size of this cell, as an unsigned integer.
        """
        if self.is_free():
            return self._size
        else:
            return self._size * -1

    def next(self):
        """
        Returns the next HBINCell, which is located immediately after this.
        Note: This will always return an HBINCell starting at the next location
        whether or not the buffer is large enough. The calling function should
        check the offset of the next HBINCell to ensure it does not overrun the
        HBIN buffer.
        """
        try:
            return HBINCell(self._buf, self._offset + self.size(), self.parent())
        except:
            raise RegistryStructureDoesNotExist("HBINCell does not exist at 0x%x" % (self._offset + self.size()))

    def offset(self):
        """
        Accessor for absolute offset of this HBINCell.
        """
        return self._offset

    def data_offset(self):
        """
        Get the absolute offset of the data block of this HBINCell.
        """
        return self._offset + 0x4

    def raw_data(self):
        """
        Get the raw data from the buffer contained by this HBINCell.
        """
        return self._buf[self.data_offset():self.data_offset() + self.size()]

    def data_id(self):
        """
        Get the ID string of the data block of this HBINCell.
        """
        return self.unpack_string(0x4, 2)

    def abs_offset_from_hbin_offset(self, offset):
        """
        Offsets contained in HBIN cells are relative to the beginning of the first HBIN.
        This converts the relative offset into an absolute offset.
        """
        h = self.parent()
        while h.__class__.__name__ != "HBINBlock":
            h = h.parent()

        return h.first_hbin().offset() + offset

    def child(self):
        """
        Make a _guess_ as to the contents of this structure and
        return an instance of that class, or just a DataRecord
        otherwise.
        """
        if self.is_free():
            raise RegistryStructureDoesNotExist("HBINCell is free at 0x%x" % (self.offset()))

        id_ = self.data_id()
        
        if id_ == b"vk":
            return VKRecord(self._buf, self.data_offset(), self)
        elif id_ == b"nk":
            return NKRecord(self._buf, self.data_offset(), self)
        elif id_ == b"lf":
            return LFRecord(self._buf, self.data_offset(), self)
        elif id_ == b"lh":
            return LHRecord(self._buf, self.data_offset(), self)
        elif id_ == b"li":
            return LIRecord(self._buf, self.data_offset(), self)
        elif id_ == b"ri":
            return RIRecord(self._buf, self.data_offset(), self)
        elif id_ == b"sk":
            return SKRecord(self._buf, self.data_offset(), self)
        elif id_ == b"db":
            return DBRecord(self._buf, self.data_offset(), self)
        else:
            return DataRecord(self._buf, self.data_offset(), self)


class Record(RegistryBlock):
    """
    Abstract class for Records contained by cells in HBINs
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This SHOULD be an HBINCell.
        """
        super(Record, self).__init__(buf, offset, parent)

    def abs_offset_from_hbin_offset(self, offset):
        # TODO This violates DRY as this is a redefinition, see HBINCell.abs_offset_from_hbin_offset()
        """
        Offsets contained in HBIN cells are relative to the beginning of the first HBIN.
        This converts the relative offset into an absolute offset.
        """
        h = self.parent()
        while h.__class__.__name__ != "HBINBlock":
            h = h.parent()

        return h.first_hbin().offset() + offset


class DataRecord(Record):
    """
    A DataRecord is a HBINCell that does not contain any further structural data, but
    may contain, for example, the values pointed to by a VKRecord.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.

        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This should be an HBINCell.
        """
        super(DataRecord, self).__init__(buf, offset, parent)

    def __str__(self):
        return "Data Record at 0x%x" % (self.offset())


class DBIndirectBlock(Record):
    """
    The DBIndirect block is a list of offsets to DataRecords with data
    size up to 0x3fd8.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This should be an HBINCell.
        """
        super(DBIndirectBlock, self).__init__(buf, offset, parent)

    def __str__(self):
        return "Large Data Block at 0x%x" % (self.offset())

    def large_data(self, length):
        """
        Get the data pointed to by the indirect block. It may be large.
        Return a byte string.
        """
        b = bytearray()
        count = 0
        while length > 0:
            off = self.abs_offset_from_hbin_offset(self.unpack_dword(4 * count))
            size = min(0x3fd8, length)
            b += HBINCell(self._buf, off, self).raw_data()[0:size]

            count += 1
            length -= size
        return str(b)


class DBRecord(Record):
    """
    A DBRecord is a large data block, which is not thoroughly documented.
    Its similar to an inode in the Ext file systems.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This should be an HBINCell.
        """
        super(DBRecord, self).__init__(buf, offset, parent)

        _id = self.unpack_string(0x0, 2)
        if _id != b"db":
            raise ParseException("Invalid DB Record ID")

    def __str__(self):
        return "Large Data Block at 0x%x" % (self.offset())

    def large_data(self, length):
        """
        Get the data described by the DBRecord. It may be large.
        Return a byte array.
        """
        off = self.abs_offset_from_hbin_offset(self.unpack_dword(0x4))
        cell = HBINCell(self._buf, off, self)
        dbi = DBIndirectBlock(self._buf, cell.data_offset(), cell)
        return dbi.large_data(length)


def decode_utf16le(s):
    """
    decode_utf16le attempts to decode a bytestring as UTF-16LE.
      If the string has an odd length, or some unexpected feature,
      this function does its best to handle the data. It does not
      catch any Unicode-related exceptions, such as UnicodeDecodeError,
      so these should be handled by the caller.

    @type s: str
    @param s: a bytestring to pase
    @rtype: unicode
    @return: the unicode string decoded from `s`
    @raises: this function does not attempt to catch any Unicode-related exception, so the caller should handle these.
    """
    if b"\x00\x00" in s:
        index = s.index(b"\x00\x00")
        if index > 2:
            if s[index - 2] != b"\x00"[0]: #py2+3 
                #  61 00 62 00 63 64 00 00
                #                    ^  ^-- end of string
                #                    +-- index
                s = s[:index + 2]
            else:
                #  61 00 62 00 63 00 00 00
                #                 ^     ^-- end of string
                #                 +-- index
                s = s[:index + 3]
    if (len(s) % 2) != 0:
        s = s + b"\x00"
    s = s.decode("utf16")
    s = s.partition('\x00')[0]
    return s


class VKRecord(Record):
    """
    The VKRecord holds one name-value pair.  The data may be one many types,
    including strings, integers, and binary data.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
              This should be an HBINCell.
        """
        super(VKRecord, self).__init__(buf, offset, parent)

        _id = self.unpack_string(0x0, 2)
        if _id != b"vk":
            raise ParseException("Invalid VK Record ID")

    def data_type_str(self):
        """
        Get the value data's type as a string
        """
        data_type = self.data_type()
        if data_type == RegSZ:
            return "RegSZ"
        elif data_type == RegExpandSZ:
            return "RegExpandSZ"
        elif data_type == RegBin:
            return "RegBin"
        elif data_type == RegDWord:
            return "RegDWord"
        elif data_type == RegMultiSZ:
            return "RegMultiSZ"
        elif data_type == RegQWord:
            return "RegQWord"
        elif data_type == RegNone:
            return "RegNone"
        elif data_type == RegBigEndian:
            return "RegBigEndian"
        elif data_type == RegLink:
            return "RegLink"
        elif data_type == RegResourceList:
            return "RegResourceList"
        elif data_type == RegFullResourceDescriptor:
            return "RegFullResourceDescriptor"
        elif data_type == RegResourceRequirementsList:
            return "RegResourceRequirementsList"
        else:
            return "Unknown type: %s" % (hex(data_type))

    def __str__(self):
        if self.has_name():
            name = self.name()
        else:
            name = "(default)"

        data = ""
        data_type = self.data_type()
        if data_type == RegSZ or data_type == RegExpandSZ:
            data = self.data()[0:16] + "..."
        elif data_type == RegMultiSZ:
            data = str(len(self.data())) + " strings"
        elif data_type == RegDWord or data_type == RegQWord:
            data = str(hex(self.data()))
        elif data_type == RegNone:
            data = "(none)"
        elif data_type == RegBin:
            data = "(binary)"
        else:
            data = "(unsupported)"

        return "VKRecord(Name: %s, Type: %s, Data: %s) at 0x%x" % (name,
                                                         self.data_type_str(),
                                                         data,
                                                         self.offset())

    def has_name(self):
        """
        Has a name? or perhaps we should use '(default)'
        """
        return self.unpack_word(0x2) != 0

    def has_ascii_name(self):
        """
        Is the name of this value in the ASCII charset?
        Note, this doesnt work, yet... TODO
        """
        return self.unpack_word(0x10) & 1 == 1

    def name(self):
        """
        Get the name, if it exists. If not, the empty string is returned.
        @return: ascii string containing the name
        """
        if not self.has_name():
            return ""
        else:
            name_length = self.unpack_word(0x2)
            return self.unpack_string(0x14, name_length).decode("windows-1252")

    def data_type(self):
        """
        Get the data type of this value data as an unsigned integer.
        """
        return self.unpack_dword(0xC)

    def data_length(self):
        """
        Get the length of this value data. This is the actual length of the data that should be parsed for the value.
        """
        size = self.unpack_dword(0x4)
        if size > 0x80000000:
            size -= 0x80000000
        return size

    def raw_data_length(self):
        """
        Get the literal length of this value data. Some interpretation may be required to make sense of the value.
        """
        return self.unpack_dword(0x4)

    def data_offset(self):
        """
        Get the offset to the raw data associated with this value.
        """
        if self.raw_data_length() < 5 or self.raw_data_length() >= 0x80000000:
            return self.absolute_offset(0x8)
        else:
            return self.abs_offset_from_hbin_offset(self.unpack_dword(0x8))

    def data(self):
        """
        Get the data.  This method will return various types based on the data type.

        RegSZ:
          Return a string containing the data, doing the best we can to convert it
          to ASCII or UNICODE.
        RegExpandSZ:
          Return a string containing the data, doing the best we can to convert it
          to ASCII or UNICODE. The special variables are not expanded.
        RegMultiSZ:
          Return a list of strings.
        RegNone:
          See RegBin
        RegDword:
          Return an unsigned integer containing the data.
        RegQword:
          Return an unsigned integer containing the data.
        RegBin:
          Return a sequence of bytes containing the binary data.
        RegBigEndian:
          Not currently supported. TODO.
        RegLink:
          Not currently supported. TODO.
        RegResourceList:
          Not currently supported. TODO.
        RegFullResourceDescriptor:
          Not currently supported. TODO.
        RegResourceRequirementsList:
          Not currently supported. TODO.
        """
        data_type = self.data_type()
        data_length = self.raw_data_length()
        data_offset = self.data_offset()

        if data_type == RegSZ or data_type == RegExpandSZ:
            if data_length >= 0x80000000:
                # data is contained in the data_offset field
                s = struct.unpack_from(str("<%ds") % (4), self._buf, data_offset)[0]
            elif 0x3fd8 < data_length < 0x80000000:
                d = HBINCell(self._buf, data_offset, self)
                if d.data_id() == b"db":
                    # this should always be the case
                    # but empirical testing does not confirm this
                    s = d.child().large_data(data_length)
                else:
                    s = d.raw_data()[:data_length]
            else:
                d = HBINCell(self._buf, data_offset, self)
                s = struct.unpack_from(str("<%ds") % (data_length), self._buf, d.data_offset())[0]
            s = decode_utf16le(s)
            return s
        elif data_type == RegBin or data_type == RegNone:
            if data_length >= 0x80000000:
                data_length -= 0x80000000
                return self._buf[data_offset:data_offset + data_length]
            elif 0x3fd8 < data_length < 0x80000000:
                d = HBINCell(self._buf, data_offset, self)
                if d.data_id() == b"db":
                    # this should always be the case
                    # but empirical testing does not confirm this
                    return d.child().large_data(data_length)
                else:
                    return d.raw_data()[:data_length]
            return self._buf[data_offset + 4:data_offset + 4 + data_length]
        elif data_type == RegDWord:
            return self.unpack_dword(0x8)
        elif data_type == RegMultiSZ:
            if data_length >= 0x80000000:
                # this means data_length < 5, so it must be 4, and
                # be composed of completely \x00, so the strings are empty
                return []
            elif 0x3fd8 < data_length < 0x80000000:
                d = HBINCell(self._buf, data_offset, self)
                if d.data_id() == b"db":
                    s = d.child().large_data(data_length)
                else:
                    s = d.raw_data()[:data_length]
            else:
                s = self._buf[data_offset + 4:data_offset + 4 + data_length]
            s = s.decode("utf16")
            return s.split("\x00")
        elif data_type == RegQWord:
            d = HBINCell(self._buf, data_offset, self)
            return struct.unpack_from(str("<Q"), self._buf, d.data_offset())[0]
        elif data_type == RegBigEndian:
            d = HBINCell(self._buf, data_offset, self)
            return struct.unpack_from(str(">I"), self._buf, d.data_offset())[0]
        elif data_type == RegLink or \
                        data_type == RegResourceList or \
                        data_type == RegFullResourceDescriptor or \
                        data_type == RegResourceRequirementsList:
            # we don't really support these types, but can at least
            #  return raw binary for someone else to work with.
            if data_length >= 0x80000000:
                data_length -= 0x80000000
                return self._buf[data_offset:data_offset + data_length]
            elif 0x3fd8 < data_length < 0x80000000:
                d = HBINCell(self._buf, data_offset, self)
                if d.data_id() == b"db":
                    # this should always be the case
                    # but empirical testing does not confirm this
                    return d.child().large_data(data_length)
                else:
                    return d.raw_data()[:data_length]
            return self._buf[data_offset + 4:data_offset + 4 + data_length]
        elif data_length < 5 or data_length >= 0x80000000:
            return self.unpack_dword(0x8)
        else:
            raise UnknownTypeException("Unknown VK Record type 0x%x at 0x%x" % (data_type, self.offset()))


class SKRecord(Record):
    """
    Security Record. Contains Windows security descriptor,
    Which defines ownership and permissions for local values
    and subkeys.

    May be referenced by multiple NK records.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This should be an HBINCell.
        """
        super(SKRecord, self).__init__(buf, offset, parent)

        _id = self.unpack_string(0x0, 2)
        if _id != b"sk":
            raise ParseException("Invalid SK Record ID")

        self._offset_prev_sk = self.unpack_dword(0x4)
        self._offset_next_sk = self.unpack_dword(0x8)

    def __str__(self):
        return "SK Record at 0x%x" % (self.offset())


class ValuesList(HBINCell):
    """
    A ValuesList is a simple structure of fixed length pointers/offsets to VKRecords.
    """
    def __init__(self, buf, offset, parent, number):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. The parent of a ValuesList SHOULD be a NKRecord.
        """
        super(ValuesList, self).__init__(buf, offset, parent)
        self._number = number

    def __str__(self):
        return "ValueList(Length: %d) at 0x%x" % (self.parent().values_number(), self.offset())

    def values(self):
        """
        A generator that yields the VKRecords referenced by this list.
        """
        value_item = 0x0

        for _ in range(0, self._number):
            value_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(value_item))

            d = HBINCell(self._buf, value_offset, self)
            v = VKRecord(self._buf, d.data_offset(), self)
            value_item += 4
            yield v


class SubkeyList(Record):
    """
    A base class for use by structures recording the subkeys of Registry key.
    The required overload is self.keys(), which is a generator for all the subkeys (NKRecords).
    The SubkeyList is not meant to be used directly.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. The parent of a SubkeyList SHOULD be a NKRecord.
        """
        super(SubkeyList, self).__init__(buf, offset, parent)

    def __str__(self):
        return "SubkeyList(Length: %d) at 0x%x" % (0, self.offset())

    def _keys_len(self):
        return self.unpack_word(0x2)

    def keys(self):
        """
        A generator that yields the NKRecords referenced by this list.
        The base SubkeyList class returns no NKRecords, since it should not be used directly.
        """
        return


class RIRecord(SubkeyList):
    """
    The RIRecord is a structure linking to structures containing
    a lists of offsets/pointers to subkey NKRecords. It is like a double (or more)
    indirect block.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(RIRecord, self).__init__(buf, offset, parent)

    def __str__(self):
        return "RIRecord(Length: %d) at 0x%x" % (len(self.keys()), self.offset())

    def keys(self):
        """
        A generator that yields the NKRecords referenced by this list.
        ri style entry size.
        """
        key_index = 0x4

        for _ in range(0, self._keys_len()):
            key_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(key_index))
            d = HBINCell(self._buf, key_offset, self)

            try:
                for k in d.child().keys():
                    yield k
            except RegistryStructureDoesNotExist:
                raise ParseException("Unsupported subkey list encountered.")

            key_index += 4


class DirectSubkeyList(SubkeyList):
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(DirectSubkeyList, self).__init__(buf, offset, parent)

    def __str__(self):
        return "DirectSubkeyList(Length: %d) at 0x%x" % (self._keys_len(), self.offset())

    def keys(self):
        """
        A generator that yields the NKRecords referenced by this list.
        Assumes each entry is 0x8 bytes long (lf / lh style).
        """
        key_index = 0x4

        for _ in range(0, self._keys_len()):
            key_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(key_index))

            d = HBINCell(self._buf, key_offset, self)
            yield NKRecord(self._buf, d.data_offset(), self)
            key_index += 8


class LIRecord(DirectSubkeyList):
    """
    The LIRecord is a simple structure containing a list of offsets/pointers
    to subkey NKRecords. It is a single indirect block.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(LIRecord, self).__init__(buf, offset, parent)

    def __str__(self):
        return "LIRecord(Length: %d) at 0x%x" % (self._keys_len(), self.offset())

    def keys(self):
        """
        A generator that yields the NKRecords referenced by this list.
        li style entry size.
        """
        key_index = 0x4

        for _ in range(0, self._keys_len()):
            key_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(key_index))

            d = HBINCell(self._buf, key_offset, self)
            yield NKRecord(self._buf, d.data_offset(), self)
            key_index += 4


class LFRecord(DirectSubkeyList):
    """
    The LFRecord is a simple structure containing a list of offsets/pointers
    to subkey NKRecords.
    The LFRecord also contains a hash for the name of the subkey pointed to
    by the offset, which enables more efficient seaching of the Registry tree.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(LFRecord, self).__init__(buf, offset, parent)
        _id = self.unpack_string(0x0, 2)
        if _id != b"lf":
            raise ParseException("Invalid LF Record ID")

    def __str__(self):
        return "LFRecord(Length: %d) at 0x%x" % (self._keys_len(), self.offset())


class LHRecord(DirectSubkeyList):
    """
    The LHRecord is a simple structure containing a list of offsets/pointers
    to subkey NKRecords.
    The LHRecord also contains a hash for the name of the subkey pointed to
    by the offset, which enables more efficient seaching of the Registry tree.
    The LHRecord is analogous to the LFRecord, but it uses a different hashing function.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block.
        """
        super(LHRecord, self).__init__(buf, offset, parent)
        _id = self.unpack_string(0x0, 2)
        if _id != b"lh":
            raise ParseException("Invalid LH Record ID")

    def __str__(self):
        return "LHRecord(Length: %d) at 0x%x" % (self._keys_len(), self.offset())


class NKRecord(Record):
    """
    The NKRecord defines the tree-like structure of the Windows Registry.
    It contains pointers/offsets to the ValueList (values associated with the given record),
    and to subkeys.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. This should be a HBINCell.
        """
        super(NKRecord, self).__init__(buf, offset, parent)
        _id = self.unpack_string(0x0, 2)
        if _id != b"nk":
            raise ParseException("Invalid NK Record ID")

    def __str__(self):
        classname = self.classname()
        if not self.has_classname():
            classname = "(none)"

        if self.is_root():
            return "Root NKRecord(Class: %s, Name: %s) at 0x%x" % (classname,
                                                                   self.name(),
                                                                   self.offset())
        else:
            return "NKRecord(Class: %s, Name: %s) at 0x%x" % (classname,
                                                              self.name(),
                                                              self.offset())

    def has_classname(self):
        """
        Does this have a classname?
        """
        return self.unpack_dword(0x30) != 0xFFFFFFFF

    def classname(self):
        """
        If this has a classname, get it as a string. Otherwise, return the empty string.
        @return: unicode string containg the class name
        """
        if not self.has_classname():
            return ""

        classname_offset = self.unpack_dword(0x30)
        classname_length = self.unpack_word(0x4A)

        offset = self.abs_offset_from_hbin_offset(classname_offset)
        d = HBINCell(self._buf, offset, self)
        return struct.unpack_from(str("<%ds") % (classname_length), self._buf, d.data_offset())[0].decode("utf-16le").rstrip("\x00")

    def timestamp(self):
        """
        Get the modified timestamp as a Python datetime.
        """
        return parse_windows_timestamp(self.unpack_qword(0x4))

    def name(self):
        """
        Return the registry key name as a string.
        @return: ascii string containing the name
        """
        name_length = self.unpack_word(0x48)
        return self.unpack_string(0x4C, name_length).decode("windows-1252")

    def path(self):
        """
        Return the full path of the registry key as a unicode string
        @return: unicode string containing the path
        """
        name = ""
        p = self

        name = "\\" + name
        name = p.name()
        while p.has_parent_key():
            p = p.parent_key()
            name = p.name() + "\\" + name
        return name

    def is_root(self):
        """
        Is this a root key?
        """
        return self.unpack_word(0x2) == 0x2C

    def has_parent_key(self):
        """
        Is there a parent key? There should always be a parent key, unless
        this is a root key (see self.is_root())
        """
        if self.is_root():
            return False
        try:
            self.parent_key()
            return True
        except ParseException:
            return False

    def parent_key(self):
        """
        Get the parent_key, which will be an NKRecord.
        """
        offset = self.abs_offset_from_hbin_offset(self.unpack_dword(0x10))

        # TODO be careful here in setting the parent of the HBINCell
        d = HBINCell(self._buf, offset, self.parent())
        return NKRecord(self._buf, d.data_offset(), self.parent())

    def sk_record(self):
        """
        Get the security descriptor associated with this NKRecord as an SKRecord.
        """
        offset = self.abs_offset_from_hbin_offset(self.unpack_dword(0x2C))

        d = HBINCell(self._buf, offset, self)
        return SKRecord(self._buf, d.data_offset(), d)

    def values_number(self):
        """
        Get the number of values associated with this NKRecord/Key.
        """
        num = self.unpack_dword(0x24)
        if num == 0xFFFFFFFF:
            return 0
        return num

    def values_list(self):
        """
        Get the values as a ValuesList.
        Raises RegistryStructureDoesNotExist if this NKRecord has no values.
        """
        if self.values_number() == 0:
            raise RegistryStructureDoesNotExist("NK Record has no associated values.")

        values_list_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(0x28))

        d = HBINCell(self._buf, values_list_offset, self)
        return ValuesList(self._buf, d.data_offset(), self, self.values_number())

    def subkey_number(self):
        """
        Get the number of subkeys of this key.
        """
        number = self.unpack_dword(0x14)
        if number == 0xFFFFFFFF:
            return 0
        return number

    def subkey_list(self):
        """
        Get the subkeys of this key as a descendant of SubkeyList.
        Raises RegistryStructureDoesNotExists if this NKRecord does not have any subkeys.
        See NKRecord.subkey_number() to check for the existance of subkeys.
        """
        if self.subkey_number() == 0:
            raise RegistryStructureDoesNotExist("NKRecord has no subkey list at 0x%x" % (self.offset()))

        subkey_list_offset = self.abs_offset_from_hbin_offset(self.unpack_dword(0x1C))

        d = HBINCell(self._buf, subkey_list_offset, self)
        id_ = d.data_id()

        if id_ == b"lf":
            l = LFRecord(self._buf, d.data_offset(), self)
        elif id_ == b"lh":
            l = LHRecord(self._buf, d.data_offset(), self)
        elif id_ == b"ri":
            l = RIRecord(self._buf, d.data_offset(), self)
        elif id_ == b"li":
            l = LIRecord(self._buf, d.data_offset(), self)
        else:
            raise ParseException("Subkey list with type %s encountered, but not yet supported." % (id_))

        return l


class HBINBlock(RegistryBlock):
    """
    An HBINBlock is the basic allocation block of the Windows Registry.
    It has a length of 0x1000.
    """
    def __init__(self, buf, offset, parent):
        """
        Constructor.
        Arguments:
        - `buf`: Byte string containing Windows Registry file.
        - `offset`: The offset into the buffer at which the block starts.
        - `parent`: The parent block, which links to this block. The parent of the first HBINBlock
        should be the REGFBlock, and the parents of other HBINBlocks should be the preceeding
        HBINBlocks.
        """
        super(HBINBlock, self).__init__(buf, offset, parent)

        _id = self.unpack_dword(0)
        if _id != 0x6E696268:
            raise ParseException("Invalid HBIN ID")

        self._reloffset_next_hbin = self.unpack_dword(0x8)
        self._offset_next_hbin = self._reloffset_next_hbin + self._offset

    def __str__(self):
        return "HBIN at 0x%x" % (self._offset)

    def first_hbin(self):
        """
        Get the first HBINBlock.
        """
        reloffset_from_first_hbin = self.unpack_dword(0x4)
        return HBINBlock(self._buf, (self.offset() - reloffset_from_first_hbin), self.parent())

    def has_next(self):
        """
        Does another HBINBlock exist after this one?
        """
        regf = self.first_hbin().parent()
        if regf.last_hbin_offset() == self.offset():
            return False

        try:
            HBINBlock(self._buf, self._offset_next_hbin, self.parent())
            return True
        except (ParseException, struct.error):
            return False

    def next(self):
        """
        Get the next HBIN after this one.
        Note: This will blindly attempts to create it regardless of if it exists.
        """
        return HBINBlock(self._buf, self._offset_next_hbin, self.parent())

    def cells(self):
        """
        Get a generator that yields each HBINCell contained in this HBIN.
        """
        c = HBINCell(self._buf, self._offset + 0x20, self)

        while c.offset() < self._offset_next_hbin:
            yield c
            c = c.next()

    def records(self):
        """
        A generator that yields each HBINCell contained in this HBIN.
        These are not necessarily in use, or linked to, from the root key.
        """
        c = HBINCell(self._buf, self._offset + 0x20, self)

        while c.offset() < self._offset_next_hbin:
            yield c
            try:
                c = c.next()
            except RegistryStructureDoesNotExist:
                break

########NEW FILE########
__FILENAME__ = findkey
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#   Find all Registry paths, value names, and values that
#   contain the given string.
#
#   python findkey.py <registry file> <needle>
#

from __future__ import print_function
from __future__ import unicode_literals

import sys

import argparse
from Registry import Registry


def main():
    parser = argparse.ArgumentParser(
        description="Search for a string in a Windows Registry hive")
    parser.add_argument("registry_hive", type=str,
                        help="Path to the Windows Registry hive to process")
    parser.add_argument("query", type=str,
                        help="Query for which to search")
    parser.add_argument("-i", action="store_true", dest="case_insensitive",
                        help="Query for which to search")
    args = parser.parse_args()

    paths = []
    value_names = []
    values = []


    def rec(key, depth, needle):
        for value in key.values():
            if (args.case_insensitive and needle in value.name().lower()) or needle in value.name():
                value_names.append((key.path(), value.name()))
                sys.stdout.write("n")
                sys.stdout.flush()
            try:
                if (args.case_insensitive and needle in str(value.value()).lower()) or needle in str(value.value()):
                    values.append((key.path(), value.name()))
                    sys.stdout.write("v")
                    sys.stdout.flush()
            except UnicodeEncodeError:
                pass

        for subkey in key.subkeys():
            if needle in subkey.name():
                paths.append(subkey.path())
                sys.stdout.write("p")
                sys.stdout.flush()
            rec(subkey, depth + 1, needle)

    reg = Registry.Registry(args.registry_hive)
    needle = args.query
    if args.case_insensitive:
        needle = needle.lower()

    rec(reg.root(), 0, needle)
    print("")

    print("[Paths]")
    for path in paths:
        print("  - %s" % (path))
    if len(paths) == 0:
        print("  (none)")
    print("")

    print("[Value Names]")
    for pair in value_names:
        print("  - %s : %s" % (pair[0], pair[1]))
    if len(value_names) == 0:
        print("  (none)")
    print("")

    print("[Values]")
    for pair in values:
        print("  - %s : %s" % (pair[0], pair[1]))
    if len(values) == 0:
        print("  (none)")
    print("")


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = forensicating
#!/usr/bin/env python

# created by Glenn P. Edwards Jr.
#   http://hiddenillusion.blogspot.com
#       @hiddenillusion
# Version 0.1
# Date: 07-23-2013
# (while at FireEye)

from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
import time
try:
    from Registry import Registry
except ImportError:
    print("[!] Python-Registry not found")

"""
Some repetitively used functions
"""

def control_set_check(sys_reg): 
    """
    Determine which Control Set the system was using
    """
    registry = Registry.Registry(sys_reg)
    key = registry.open("Select")    
    for v in key.values():
        if v.name() == "Current":
            return v.value()             

def arch_check(sys_reg):
    """
    Architecture Check
    """    
    registry = Registry.Registry(sys_reg)
    key = registry.open("ControlSet00%s\\Control\\Session Manager\\Environment" % control_set_check(sys_reg)) 
    for v in key.values():
        if v.name() == "PROCESSOR_ARCHITECTURE":
            return v.value()                

def windir_check(sys_reg):
    """
    Locate the Windows directory
    """
    registry = Registry.Registry(sys_reg)    
    key = registry.open("ControlSet00%s\\Control\\Session Manager\\Environment" % control_set_check(sys_reg))    
    for v in key.values():
        if v.name() == "windir":
            return v.value()                

def os_check(soft_reg):
    """
    Determine the Operating System
    """
    registry = Registry.Registry(soft_reg)
    key = registry.open("Microsoft\\Windows NT\\CurrentVersion")
    for v in key.values():
        if v.name() == "ProductName":
            return v.value()                

def users_sids(soft_reg):
    '''
    Return a list of subkeys containing the users SIDs
    '''
    sid_list = []
    registry = Registry.Registry(soft_reg)
    key = registry.open("Microsoft\\Windows NT\\CurrentVersion\\ProfileList")
    for v in key.subkeys():
        sid_list.append(v.name())

    return sid_list

def sid_to_user(sid_list, soft_reg):
    '''
    Return a list which maps SIDs to usernames
    '''
    # Grab the users profiles path based on the above SIDs
    mapping_list = []
    registry = Registry.Registry(soft_reg)
    for sid in sid_list:
        k = registry.open("Microsoft\\Windows NT\\CurrentVersion\\ProfileList\\%s" % sid)
        for v in k.values():
            if v.name() == "ProfileImagePath":
                mapping_list.append("{0:20} : {1}".format(v.value().rpartition('\\')[2],sid))

    return mapping_list
    
def users_paths(soft_reg, sid_list):
    '''
    Return a list of the profile paths for users on the system
    '''
    # Grab the users profiles path based on their SIDs
    users_paths_list = []
    registry = Registry.Registry(soft_reg)
    for sid in sid_list:
        k = registry.open("Microsoft\\Windows NT\\CurrentVersion\\ProfileList\\%s" % sid) 
        for v in k.values():
            if v.name() == "ProfileImagePath":
                users_paths_list.append(v.value())

    return users_paths_list   


def user_reg_locs(user_path_locs):
    """
    Returns the full path to each users NTUSER.DAT hive
    """
    user_ntuser_list = []
    for p in user_path_locs:
        if re.match('.*(Users|Documents and Settings).*', p):
            user_reg = os.path.join(p, "NTUSER.DAT")
            user_ntuser_list.append(user_reg)

    return user_ntuser_list

"""
Leverage the above functions and do something cool with them
"""
def env_settings(sys_reg):
    """
    Environment Settings
    """
    results = []
    sys_architecture = []
    registry = Registry.Registry(sys_reg)    
    print(("=" * 51) + "\n[+] Environment Settings\n" + ("=" * 51))
    key = registry.open("ControlSet00%s\\Control\\Session Manager\\Environment" % control_set_check(sys_reg))    
    for v in key.values():
        if v.name() == "PROCESSOR_ARCHITECTURE":
            sys_architecture = v.value()
            results.append("[-] Architecture.....: " + str(v.value()))            
        if v.name() == "NUMBER_OF_PROCESSORS":
            results.append("[-] Processors.......: " + str(v.value()))
        if v.name() == "TEMP":
            results.append("[-] Temp path........: " + str(v.value()))
        if v.name() == "TMP":
            results.append("[-] Tmp path.........: " + str(v.value()))                                                                             
    for line in results:
        print(line)

def tz_settings(sys_reg):
    """
    Time Zone Settings
    """
    results = []
    current_control_set = "ControlSet00%s" % control_set_check(sys_reg)
    k = "%s\\Control\\TimeZoneInformation" % current_control_set
    registry = Registry.Registry(sys_reg)
    key = registry.open(k)
    results.append(("=" * 51) + "\nTime Zone Settings\n" + ("=" * 51))    
    print("[-] Checking %s based on 'Select' settings" % current_control_set)
    results.append("[+] %s" % k)
    results.append("---------------------------------------")
    for v in key.values():
        if v.name() == "ActiveTimeBias":
            results.append("[-] ActiveTimeBias: %s" % v.value())
        if v.name() == "Bias":
            results.append("[-] Bias...: %s" % v.value())
        if v.name() == "TimeZoneKeyName":
            results.append("[-] Time Zone Name...: %s" % str(v.value()))

    return results

def os_settings(sys_reg, soft_reg):
    """
    Installed Operating System information
    """
    results = []
    registry = Registry.Registry(soft_reg)
    os_dict = {}
    key = registry.open("Microsoft\\Windows NT\\CurrentVersion")             
    for v in key.values():
        if v.name() == "ProductName":
            os_dict['ProductName'] = v.value()          
        if v.name() == "ProductId":
            os_dict['ProductId'] = v.value()              
        if v.name() == "CSDVersion":
            os_dict['CSDVersion'] = v.value()
        if v.name() == "PathName":
            os_dict['PathName'] = v.value()  
        if v.name() == "InstallDate":
            os_dict['InstallDate'] = time.strftime('%a %b %d %H:%M:%S %Y (UTC)', time.gmtime(v.value()))
        if v.name() == "RegisteredOrganization":
            os_dict['RegisteredOrganization'] = v.value()   
        if v.name() == "RegisteredOwner":
            os_dict['RegisteredOwner'] = v.value()          
                          
    print(("=" * 51) + "\n[+] Operating System Information\n" + ("=" * 51))
    print("[-] Product Name.....: %s" % os_dict['ProductName'])
    print("[-] Product ID.......: %s" % os_dict['ProductId'])
    print("[-] CSDVersion.......: %s" % os_dict['CSDVersion'])
    print("[-] Path Name........: %s" % os_dict['PathName']    )
    print("[-] Install Date.....: %s" % os_dict['InstallDate']       )
    print("[-] Registered Org...: %s" % os_dict['RegisteredOrganization'])
    print("[-] Registered Owner : %s" % os_dict['RegisteredOwner'])

def network_settings(sys_reg, soft_reg):
    """
    Network Settings
    """
    nic_names = []
    results_dict = {}
    nic_list = []
    nics_dict = {}
    int_list = []
    registry = Registry.Registry(soft_reg)
    key = registry.open("Microsoft\\Windows NT\\CurrentVersion\\NetworkCards")
    print(("=" * 51) + "\n[+] Network Adapters\n" + ("=" * 51))

    # Populate the subkeys containing the NICs information
    for v in key.subkeys():
        nic_list.append(v.name())
  
    for nic in nic_list:
        k = registry.open("Microsoft\\Windows NT\\CurrentVersion\\NetworkCards\\%s" % nic)
        for v in k.values():
            if v.name() == "Description":
                desc = v.value()
                nic_names.append(desc)
            if v.name() == "ServiceName":
                guid = v.value()
        nics_dict['Description'] = desc
        nics_dict['ServiceName'] = guid

    reg = Registry.Registry(sys_reg)
    key2 = reg.open("ControlSet00%s\\services\\Tcpip\\Parameters\\Interfaces" % control_set_check(sys_reg))
    # Populate the subkeys containing the interfaces GUIDs
    for v in key2.subkeys():
        int_list.append(v.name())

    def guid_to_name(g):
        for k,v in nics_dict.items():
            '''
            k = ServiceName, Description
            v = GUID, Adapter name
            '''
            if v == g:
                return nics_dict['Description']

    # Grab the NICs info based on the above list
    for i in int_list:
        print("[-] Interface........: %s" % guid_to_name(i))
        print("[-] GUID.............: %s" % i)
        key3 = reg.open("ControlSet00%s\\services\\Tcpip\\Parameters\\Interfaces\\%s" % (control_set_check(sys_reg), i))  
        for v in key3.values():
            if v.name() == "Domain":
                results_dict['Domain'] = v.value()
            if v.name() == "IPAddress":
                # Sometimes the IP would end up in a list here so just doing a little check
                ip = v.value()
                results_dict['IPAddress'] = ip[0]                   
            if v.name() == "DhcpIPAddress":
                results_dict['DhcpIPAddress'] = v.value()                    
            if v.name() == "DhcpServer":
                results_dict['DhcpServer'] = v.value()                    
            if v.name() == "DhcpSubnetMask":
                results_dict['DhcpSubnetMask'] = v.value()      
   
        # Just to avoid key errors and continue to do becuase not all will have these fields 
        if not 'Domain' in results_dict: 
            results_dict['Domain'] = "N/A"
        if not 'IPAddress' in results_dict: 
            results_dict['IPAddress'] = "N/A"
        if not 'DhcpIPAddress' in results_dict: 
            results_dict['DhcpIPAddress'] = "N/A"                
        if not 'DhcpServer' in results_dict: 
            results_dict['DhcpServer'] = "N/A"        
        if not 'DhcpSubnetMask' in results_dict: 
            results_dict['DhcpSubnetMask'] = "N/A"        

        print("[-] Domain...........: %s" % results_dict['Domain'])
        print("[-] IP Address.......: %s" % results_dict['IPAddress'])
        print("[-] DHCP IP..........: %s" % results_dict['DhcpIPAddress'])
        print("[-] DHCP Server......: %s" % results_dict['DhcpServer'])
        print("[-] DHCP Subnet......: %s" % results_dict['DhcpSubnetMask'])
        print("\n"                                      )

def users_info(soft_reg):
    """
    Populating all of the user accounts
    ref: http://support.microsoft.com/kb/154599
    """     
    results = []
    results_dict = {}
    registry = Registry.Registry(soft_reg)
   
    results.append("{0:20} : {1}".format("Username", "SID"))
    results.append("---------------------------------------")    

    for l in sid_to_user(users_sids(soft_reg), soft_reg):
        results.append(l)
                            
    print(("=" * 51) + "\n[+] User Accounts\n" + ("=" * 51))
    for line in results:
        print(line)


if __name__ == "__main__":
    """
    Print out all of the information
    """            
    import sys
    sys_reg = sys.argv[1]
    soft_reg = sys.argv[2]
    print("[+] SYSTEM hive:   %s" % sys_reg)
    print("[+] SOFTWARE hive: %s" % soft_reg)
    print("[+] The system's Control Set is :",control_set_check(sys_reg))
    print("[+] The system's Architecture is:",arch_check(sys_reg))
    tz_settings(sys_reg)
    env_settings(sys_reg)
    os_settings(sys_reg, soft_reg)
    network_settings(sys_reg, soft_reg)
    users_info(soft_reg)
    user_reg_locs(users_paths(soft_reg, users_sids(soft_reg)))

########NEW FILE########
__FILENAME__ = list_services
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from __future__ import print_function
from __future__ import unicode_literals

import sys
from Registry import Registry


def usage():
    return "  USAGE:\n\t%s <Windows Registry file> <Registry key path>" % sys.argv[0]


def main():
    if len(sys.argv) != 2:
        print(usage())
        sys.exit(-1)

    registry = Registry.Registry(sys.argv[1])
    select = registry.open("Select")
    current = select.value("Current").value()
    services = registry.open("ControlSet00%d\\Services" % (current))
    for service in services.subkeys():
        try:
            display_name = service.value("DisplayName").value()
        except:
            display_name = "???"

        try:
            description = service.value("Description").value()
        except:
            description = "???"

        try:
            image_path = service.value("ImagePath").value()
        except:
            image_path = "???"

        try:
            dll = service.subkey("Parameters").value("ServiceDll").value()
        except:
            dll = "???"
        print('%s, %s, "%s", "%s", "%s"' % (service.name(), display_name, image_path, dll, description))


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = printall
from __future__ import print_function
from __future__ import unicode_literals

import sys
from Registry import *

def rec(key, depth=0):
    print("\t" * depth + key.path())
    for subkey in key.subkeys():
        rec(subkey, depth + 1)

reg = Registry.Registry(sys.argv[1])
rec(reg.root())


########NEW FILE########
__FILENAME__ = regfetch
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from __future__ import print_function
from __future__ import unicode_literals

import sys
from Registry import Registry

def usage():
    return "  USAGE:\n\t%s <Windows Registry file> <Registry key path> [<Registry Value>]" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) != 4 and len(sys.argv) != 3:
        print(usage())
        sys.exit(-1)

    registry = Registry.Registry(sys.argv[1])

    try:
        if sys.argv[2].startswith(registry.root().name()):
            key = registry.open(sys.argv[2].partition("\\")[2])
        else:
            key = registry.open(sys.argv[2])
    except Registry.RegistryKeyNotFoundException:
        print("Specified key not found")
        sys.exit(-1) 

    if len(sys.argv) == 4:
        if sys.argv[3] == "default":
            sys.argv[3] = "(default)"

        value = key.value(sys.argv[3])
        sys.stdout.write(str(value.value()))
    if len(sys.argv) == 3:
        print("Subkeys")
        for subkey in key.subkeys():
            print("  - {}".format(subkey.name()))

        print("Values")
        for value in key.values():
            print("  - {}".format(value.name()))


########NEW FILE########
__FILENAME__ = regview
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import wx
from Registry import Registry

ID_FILE_OPEN = wx.NewId()
ID_FILE_SESSION_SAVE = wx.NewId()
ID_FILE_SESSION_OPEN = wx.NewId()
ID_TAB_CLOSE = wx.NewId()
ID_FILE_EXIT = wx.NewId()
ID_HELP_ABOUT = wx.NewId()


def nop(*args, **kwargs):
    pass


def basename(path):
    if "/" in path:
        path = path.split("/")[-1]
    if "\\" in path:
        path = path.split("\\")[-1]
    return path


def _expand_into(dest, src):
    vbox = wx.BoxSizer(wx.VERTICAL)
    vbox.Add(src, 1, wx.EXPAND | wx.ALL)
    dest.SetSizer(vbox)


def _format_hex(data):
    """
    see http://code.activestate.com/recipes/142812/
    """
    byte_format = {}
    for c in xrange(256):
        if c > 126:
            byte_format[c] = '.'
        elif len(repr(chr(c))) == 3 and chr(c):
            byte_format[c] = chr(c)
        else:
            byte_format[c] = '.'

    def format_bytes(s):
        return "".join([byte_format[ord(c)] for c in s])

    def dump(src, length=16):
        N = 0
        result = ''
        while src:
            s, src = src[:length], src[length:]
            hexa = ' '.join(["%02X" % ord(x) for x in s])
            s = format_bytes(s)
            result += "%04X   %-*s   %s\n" % (N, length * 3, hexa, s)
            N += length
        return result
    return dump(data)


class DataPanel(wx.Panel):
    """
    Displays the contents of a Registry value.
    Shows a text string where appropriate, or a hex dump.
    """
    def __init__(self, *args, **kwargs):
        super(DataPanel, self).__init__(*args, **kwargs)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

    def display_value(self, value):
        self._sizer.Clear()
        data_type = value.value_type()

        if data_type == Registry.RegSZ or \
                data_type == Registry.RegExpandSZ or \
                data_type == Registry.RegDWord or \
                data_type == Registry.RegQWord:
            view = wx.TextCtrl(self, style=wx.TE_MULTILINE)
            view.SetValue(unicode(value.value()))

        elif data_type == Registry.RegMultiSZ:
            view = wx.ListCtrl(self, style=wx.LC_LIST)
            for string in value.value():
                view.InsertStringItem(view.GetItemCount(), string)

        elif data_type == Registry.RegBin or \
                data_type == Registry.RegNone:
            view = wx.TextCtrl(self, style=wx.TE_MULTILINE)
            font = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False, u'Courier')
            view.SetFont(font)
            view.SetValue(_format_hex(value.value()))

        else:
            view = wx.TextCtrl(self, style=wx.TE_MULTILINE)
            view.SetValue(unicode(value.value()))

        self._sizer.Add(view, 1, wx.EXPAND)
        self._sizer.Layout()

    def clear_value(self):
        self._sizer.Clear()
        self._sizer.Add(wx.Panel(self, -1), 1, wx.EXPAND)
        self._sizer.Layout()


class ValuesListCtrl(wx.ListCtrl):
    """
    Shows a list of values associated with a Registry key.
    """
    def __init__(self, *args, **kwargs):
        super(ValuesListCtrl, self).__init__(*args, **kwargs)
        self.InsertColumn(0, "Value name")
        self.InsertColumn(1, "Value type")
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(0, 300)
        self.values = {}

    def clear_values(self):
        self.DeleteAllItems()
        self.values = {}

    def add_value(self, value):
        n = self.GetItemCount()
        self.InsertStringItem(n, value.name())
        self.SetStringItem(n, 1, value.value_type_str())
        self.values[value.name()] = value

    def get_value(self, valuename):
        return self.values[valuename]


class RegistryTreeCtrl(wx.TreeCtrl):
    """
    Treeview control that displays the Registry key structure.
    """
    def __init__(self, *args, **kwargs):
        super(RegistryTreeCtrl, self).__init__(*args, **kwargs)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandKey)

    def add_registry(self, registry):
        """
        Add the registry to the control as the (a?) root element.
        """
        root_key = registry.root()
        root_item = self.AddRoot(root_key.name())
        self.SetPyData(root_item, {"key": root_key,
                                   "has_expanded": False})

        if len(root_key.subkeys()) > 0:
            self.SetItemHasChildren(root_item)

    def delete_registry(self):
        """
        Removes all elements from the control.
        """
        self.DeleteAllItems()

    def select_path(self, path):
        """
        Take a Registry key path separated by back slashes and select
        that key. The path should not contain the root key name.
        If the key is not found, the most specific ancestor key is selected.
        """
        parts = path.split("\\")
        node = self.GetRootItem()

        for part in parts:
            self._extend(node)
            (node, cookie) = self.GetFirstChild(node)

            cont = True
            while node and cont:
                key = self.GetPyData(node)["key"]
                if key.name() == part:
                    self.SelectItem(node)
                    cont = False
                else:
                    node = self.GetNextSibling(node)

    def _extend(self, item):
        """
        Lazily parse and add children items to the tree.
        """
        if self.GetPyData(item)["has_expanded"]:
            return

        key = self.GetPyData(item)["key"]

        for subkey in key.subkeys():
            subkey_item = self.AppendItem(item, subkey.name())
            self.SetPyData(subkey_item, {"key": subkey,
                                         "has_expanded": False})

            if len(subkey.subkeys()) > 0:
                self.SetItemHasChildren(subkey_item)

        self.GetPyData(item)["has_expanded"] = True

    def OnExpandKey(self, event):
        item = event.GetItem()
        if not item.IsOk():
            item = self.GetSelection()

        if not self.GetPyData(item)["has_expanded"]:
            self._extend(item)


class RegistryFileView(wx.Panel):
    """
    A three-paned display of the RegistryTreeCtrl, ValueListCtrl, and DataPanel.
    """
    def __init__(self, parent, registry, filename):
        super(RegistryFileView, self).__init__(parent, -1, size=(800, 600))
        self._filename = filename

        vsplitter = wx.SplitterWindow(self, -1)
        panel_left = wx.Panel(vsplitter, -1)
        self._tree = RegistryTreeCtrl(panel_left, -1)
        _expand_into(panel_left, self._tree)

        hsplitter = wx.SplitterWindow(vsplitter, -1)
        panel_top = wx.Panel(hsplitter, -1)
        panel_bottom = wx.Panel(hsplitter, -1)

        self._value_list_view = ValuesListCtrl(panel_top, -1, style=wx.LC_REPORT)
        self._data_view = DataPanel(panel_bottom, -1)

        _expand_into(panel_top,    self._value_list_view)
        _expand_into(panel_bottom, self._data_view)

        hsplitter.SplitHorizontally(panel_top, panel_bottom)
        vsplitter.SplitVertically(panel_left, hsplitter)

        # give enough space in the data display for the hex output
        vsplitter.SetSashPosition(325, True)
        _expand_into(self, vsplitter)
        self.Centre()

        self._value_list_view.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnValueSelected)
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnKeySelected)

        self._tree.add_registry(registry)

    def OnKeySelected(self, event):
        item = event.GetItem()
        if not item.IsOk():
            item = self._tree.GetSelection()

        key = self._tree.GetPyData(item)["key"]

        parent = self.GetParent()
        while parent:
            try:
                parent.SetStatusText(key.path())
            except AttributeError:
                pass
            parent = parent.GetParent()

        self._data_view.clear_value()
        self._value_list_view.clear_values()
        for value in key.values():
            self._value_list_view.add_value(value)

    def OnValueSelected(self, event):
        item = event.GetItem()

        value = self._value_list_view.get_value(item.GetText())
        self._data_view.display_value(value)

    def filename(self):
        """
        Return the filename of the current Registry file as a string.
        """
        return self._filename

    def selected_path(self):
        """
        Return the Registry key path of the currently selected item.
        """
        item = self._tree.GetSelection()
        if item:
            return self._tree.GetPyData(item)["key"].path()
        return False

    def select_path(self, path):
        """
        Select a Registry key path specified as a string in the relevant panes.
        """
        self._tree.select_path(path)


class RegistryFileViewer(wx.Frame):
    """
    The main RegView GUI application.
    """
    def __init__(self, parent, files):
        super(RegistryFileViewer, self).__init__(parent, -1, "Registry File Viewer", size=(800, 600))
        self.CreateStatusBar()

        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        _open = file_menu.Append(ID_FILE_OPEN, '&Open File')
        self.Bind(wx.EVT_MENU, self.menu_file_open, _open)
        file_menu.AppendSeparator()
        _session_save = file_menu.Append(ID_FILE_SESSION_SAVE, '&Save Session')
        self.Bind(wx.EVT_MENU, self.menu_file_session_save, _session_save)
        _session_open = file_menu.Append(ID_FILE_SESSION_OPEN, '&Open Session')
        self.Bind(wx.EVT_MENU, self.menu_file_session_open, _session_open)
        file_menu.AppendSeparator()
        _exit = file_menu.Append(ID_FILE_EXIT, 'E&xit Program')
        self.Bind(wx.EVT_MENU, self.menu_file_exit, _exit)
        menu_bar.Append(file_menu, "&File")

        tab_menu = wx.Menu()
        _close = tab_menu.Append(ID_TAB_CLOSE, '&Close')
        self.Bind(wx.EVT_MENU, self.menu_tab_close, _close)
        menu_bar.Append(tab_menu, "&Tab")

        help_menu = wx.Menu()
        _about = help_menu.Append(ID_HELP_ABOUT, '&About')
        self.Bind(wx.EVT_MENU, self.menu_help_about, _about)
        menu_bar.Append(help_menu, "&Help")
        self.SetMenuBar(menu_bar)

        p = wx.Panel(self)
        self._nb = wx.Notebook(p)

        for filename in files:
            self._open_registry_file(filename)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._nb, 1, wx.EXPAND)
        p.SetSizer(sizer)
        self.Layout()

    def _open_registry_file(self, filename):
        """
        Open a Registry file by filename into a new tab and return the window.
        """
        with open(filename, "rb") as f:
            registry = Registry.Registry(f)
            view = RegistryFileView(self._nb, registry=registry, filename=filename)
            self._nb.AddPage(view, basename(filename))
            return view
        # TODO handle error

    def menu_file_open(self, evt):
        dialog = wx.FileDialog(None, "Choose Registry File", "", "", "*", wx.OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            return
        filename = os.path.join(dialog.GetDirectory(), dialog.GetFilename())
        self._open_registry_file(filename)

    def menu_file_exit(self, evt):
        sys.exit(0)

    def menu_file_session_open(self, evt):
        self._nb.DeleteAllPages()

        dialog = wx.FileDialog(None, "Open Session File", "", "", "*", wx.OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            return
        filename = os.path.join(dialog.GetDirectory(), dialog.GetFilename())
        with open(filename, "rb") as f:
            t = f.read()

            lines = t.split("\n")

            if len(lines) % 2 != 1:  # there is a trailing newline
                self.SetStatusText("Malformed session file!")
                return

            while len(lines) > 1:
                filename = lines.pop(0)
                path = lines.pop(0)

                view = self._open_registry_file(filename)
                view.select_path(path.partition("\\")[2])

            self.SetStatusText("Opened session")

    def menu_file_session_save(self, evt):
        dialog = wx.FileDialog(None, "Save Session File", "", "", "*", wx.SAVE)
        if dialog.ShowModal() != wx.ID_OK:
            return
        filename = os.path.join(dialog.GetDirectory(), dialog.GetFilename())
        with open(filename, "wb") as f:
            for i in range(0, self._nb.GetPageCount()):
                page = self._nb.GetPage(i)
                f.write(page.filename() + "\n")

                path = page.selected_path()
                if path:
                    f.write(path)
                f.write("\n")
            self.SetStatusText("Saved session")
        # TODO handle error

    def menu_tab_close(self, evt):
        self._nb.RemovePage(self._nb.GetSelection())

    def menu_help_about(self, evt):
        wx.MessageBox("regview.py, a part of `python-registry`\n\nhttp://www.williballenthin.com/registry/", "info")


if __name__ == '__main__':
    app = wx.App(False)

    filenames = []
    filenames = sys.argv[1:]

    frame = RegistryFileViewer(None, filenames)
    frame.Show()
    app.MainLoop()

########NEW FILE########
__FILENAME__ = shelltypes
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function
from __future__ import unicode_literals

import re, sys, datetime, time
from Registry import Registry

def get_shellbags(registry):
    shellbags = []
    # TODO try both Shell and ShellNoRoam
    try:
        # Windows XP NTUSER.DAT location
        windows = registry.open("Software\\Microsoft\\Windows\\ShellNoRoam")
    except Registry.RegistryKeyNotFoundException:
        try:
            # Windows 7 UsrClass.dat location
            windows = registry.open("Local Settings\\Software\\Microsoft\\Windows\\Shell")
        except Registry.RegistryKeyNotFoundException:
            print("Unable to find shellbag key.")
            sys.exit(-1)
    bagmru = windows.subkey("BagMRU")

    def shellbag_rec(key, bag_prefix):
        for value in key.values():
            if not re.match("\d+", value.name()):
                continue
            mru_type = ord(value.value()[2:3])
            print("%s %s" % (hex(mru_type), bag_prefix + "\\" + value.name()))

            shellbag_rec(key.subkey(value.name()), bag_prefix + "\\" + value.name())

    shellbag_rec(bagmru, "")

def usage():
    return "  USAGE:\n\t%s <Windows Registry file>" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(usage())
        sys.exit(-1)

    get_shellbags(Registry.Registry(sys.argv[1]))

########NEW FILE########
__FILENAME__ = timeline
#!/usr/bin/python

from __future__ import print_function
from __future__ import unicode_literals

import os
import calendar

import argparse
from Registry import Registry


def guess_hive_name(path):
    for i in range(len(path)):
        rpath = path[-(i + 1):].lower()
        for guess in ["ntuser", "software", "system",
                      "userdiff", "sam", "default"]:
            if guess in rpath:
                return guess.upper()


def main():
    parser = argparse.ArgumentParser(
        description="Timeline Windows Registry key timestamps")
    parser.add_argument("--bodyfile", action="store_true",
                        help="Output in the Bodyfile 3 format")
    parser.add_argument("registry_hives", type=str, nargs="+",
                        help="Path to the Windows Registry hive to process")
    args = parser.parse_args()

    def rec(key, visitor):
        try:
            visitor(key.timestamp(), key.path())
        except ValueError:
            pass
        for subkey in key.subkeys():
            rec(subkey, visitor)

    for filename in args.registry_hives:
        basename = os.path.basename(filename)
        reg = Registry.Registry(filename)

        if args.bodyfile:
            def visitor(timestamp, path):
                try:
                    print("0|[Registry %s] %s|0|0|0|0|0|%s|0|0|0" % \
                      (basename, path, int(calendar.timegm(timestamp.timetuple()))))
                except UnicodeDecodeError:
                    pass

            rec(reg.root(), visitor)
        else:
            items = []
            rec(reg.root(), lambda a, b: items.append((a, b)))
            for i in sorted(items, key=lambda x: x[0]):
                print("%s\t[Registry %s]%s" % (i[0], basename, i[1]))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = issue22
#!/usr/bin/python
from Registry import Registry


def main():
    import sys
    hive = sys.argv[1]

    import hashlib
    m = hashlib.md5()
    with open(hive, 'rb') as f:
        m.update(f.read())
    if m.hexdigest() != "26cb15876ceb4fd64476223c2bf1c8e3":
        print "Please use the SYSTEM hive with MD5 26cb15876ceb4fd64476223c2bf1c8e3"
        sys.exit(-1)

    r = Registry.Registry(hive)
    k = r.open("ControlSet001\\Control\\TimeZoneInformation")
    v = k.value("TimeZoneKeyName")
    if v.value() == "Pacific Standard Time":
        print "Passed."
    else:
        print "Failed."
        print "Expected: Pacific Standard Time"
        print "Got: %s (length: %d)" % (v.value(), len(v.value()))
    sys.exit(0)


if __name__ == "__main__":
    main()




########NEW FILE########
__FILENAME__ = issue26
#!/usr/bin/python
# -*- coding: utf-8 -*-
from Registry.RegistryParse import decode_utf16le


# here are the test cases written out with their explanations:
#
# 61 00                 --> 61             --> "a"
# 61 62                 --> 61 62          --> "扡"
# 61 62 00 00           --> 61 62          --> "扡"
# 61 00 61 00 00 00     --> 61 00 61 00    --> "aa"
# 61 00 61 62 00 00     --> 61 00 61 62    --> "a扡"
# 61 00 61 00 00        --> 61 00 61 00    --> "aa"
# 61 00 61 62 00        --> 61 00 61 62    --> "a扡"


def main(args):
    assert(decode_utf16le("\x61\x00") == u"a")
    assert(decode_utf16le("\x61\x62") == u"扡")
    assert(decode_utf16le("\x61\x62\x00\x00") == u"扡")
    assert(decode_utf16le("\x61\x00\x61\x00\x00\x00") == u"aa")
    assert(decode_utf16le("\x61\x00\x61\x62\x00\x00") == u"a扡")
    assert(decode_utf16le("\x61\x00\x61\x00\x00") == u"aa")
    assert(decode_utf16le("\x61\x00\x61\x62\x00") == u"a扡")
    print "Pass"

if __name__ == "__main__":
    import sys
    main(sys.argv)


########NEW FILE########
__FILENAME__ = RegTester
#!/usr/bin/python

#    This file is part of python-registry.
#
#   Copyright 2011 Will Ballenthin <william.ballenthin@mandiant.com>
#                    while at Mandiant <http://www.mandiant.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function
from __future__ import unicode_literals

import sys, struct
import registry

class Value(object):
    def __init__(self, name, data_type, data):
        self.name = name
        self.data_type = data_type
        self.data = data

class Key(object):
    def __init__(self, name):
        self.name = name
        self.values = []

def parse(f):
    t = f.read()
    h = t.partition("\n")[0]
    if "\xff\xfe\x57\x00\x69\x00" in h: # Windows Registry Editor 5.00
        raise "THIS ISNT SUPPORTED YET"
        try:
            t = t.decode("utf16")
            print("Decoded input file with UTF16 decoder")
        except:
            raise
    elif "REGEDIT4" in h: # Regedit
        t = t.decode("iso-8859-1", "replace")
        print("Decoded input file with ASCII decoder")
    else:
        print("Unable to parse header")
        sys.exit(-1)

    lines = t.split("\n")

    current_key = False
    current_value  = False
    keys = []

    print("Found " + str(len(lines)) + " lines")

    line_count = 0
    for line in [l.rstrip('\r') for l in lines[1:]]:
        line_count += 1

        if len(line.lstrip(" ")) < 2:
            if current_value:
                current_key.values.append(current_value)
                current_value = False
            keys.append(current_key)
            current_key = False
            continue

        if current_key:
            if current_value:
                real_data = line.lstrip(" ")
                real_data = real_data.replace("\\", "")

                for c in real_data.split(","):
                    try:
                        current_value.data += chr(int(c, 16))
                    except ValueError:
                        continue

            else:
                (name, _, data) = line.partition("=")

                # strip exactly one " mark from either side of the name
                if name[0] == '"':
                    name = name[1:]
                if name[-1] == '"':
                    name = name[:-1]

                if name == "@":
                    name = "(default)"

                if ":" in data and data[0] != '"':
                    real_data = data.partition(":")[2].rstrip("\\") # strip off trailing \ if it exists
                    try:
                        if real_data[-1] == '\\':
                            real_data = real_data[:-2]
                    except IndexError:
                        real_data = ""
                    data_type = data.partition(":")[0]
                else:
                    real_data = data
                    data_value = data.rstrip("\r\n") # strip off one " from both sides

                    if data_value[0] == '"':
                        data_value = data_value[1:]
                    if data_value[-1] == '"':
                        data_value = data_value[:-1]

                    data_value = data_value.replace('\\"', '"')
                    data_value = data_value.replace('\\\\', '\\')

                    data_type = "string"

                if "word" in data_type:
                    data_value = int(real_data, 16)

                if "hex" in data_type:
                    data_value = ""
                    for c in real_data.split(","):
                        try:
                            data_value += chr(int(c, 16))
                        except ValueError:
                            continue

                print_value = data_value
                if "word" in data_type:
                    print_value = str(print_value)
                elif "hex" in data_type:
                    print_value = print_value.decode("ascii", "replace") + ""

                v = Value(name, data_type, data_value)
                
                if  data[-1] == "\\":
                    current_value = v
                else:
                    current_key.values.append(v)
        else:
            name = line.lstrip("[").partition("]")[0]
            current_key = Key(name)

    return keys

def key_long_str(key):
    """
    Prints a long listing of a Registry Key
    """
    ret = ""
    ret += str(key) + "\n"
    
    for s in key.subkeys():
        ret += "\tsubkey: %s\n" % (s.name())

    for v in key.values():
        ret += "\tvalue: %s\n" % (v.name())

    return ret

def usage():
    return "  USAGE:\n\t%s  <.reg file>  <Registry Hive file>" % (sys.argv[0])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(usage())
        sys.exit(-1)

    f = open(sys.argv[1])
    keys = parse(f)
    print("Parsed .reg file")

    r = registry.Registry(sys.argv[2])
    print("Parsed Registry file")

    not_found_keys = 0
    incorrect_data = 0
    not_found_values = 0

    for k in [k for k in keys if k]:
        try:
            rk = r.open(k.name.partition("\\")[2])
            for v in k.values:
                if v.name == ".Default":
                    v.name = ""
                try:
                    rv = rk.value(v.name)

                    if rv.value_type() == registry.RegSZ or \
                            rv.value_type() == registry.ExpandSZ:
                        rvv = rv.value().decode("utf8")

                        try:
                            if rvv[-1] == '\x00':
                                rvv = rvv[:-1]
                            if rvv[-1] == '\x00':
                                rvv = rvv[:-1]
                        except IndexError:
                            pass

                        vv = unicode(v.data).partition('\x00')[0]
                        
                        if not rvv == vv:
                            print("DATA VALUE INCORRECT: " + k.name + ":" + v.name)
                            print("                      " + rk.path() + ":" + rv.name())
                            print(key_long_str(rk))

                            print("|%s|" % (rvv))
                            print(rvv.__class__.__name__)
                            print(len(rvv))
                            print(list(rvv))

                            print("|%s|" % (vv))
                            print(vv.__class__.__name__)
                            print(len(vv))
                            print(list(vv))

                            incorrect_data += 1

                    elif rv.value_type() == registry.RegMultiSZ:
                        # this is very ugly. im not sure it tests consistently
                        # should be fixed/made clean, but atm I am confused
                        # about how unicode is being converted, and when
                        vv = filter(lambda x: len(x) > 0, unicode(v.data).split('\x00'))
                        try:
                            rvv = map(lambda x: x.decode("utf8"), rv.value())
                        except:
                            print(rk.path())
                            print(rv.name())
                            print(rv.value())
                            raise

                        for vvv in vv:
                            if vvv not in rvv:
                                print("REGMULTISZ DATA VALUE MISSING: " + vvv)
                                print(rk.path())
                                print(rv.name())
                                print(rv.value())

                                print(list(v.data))
                                print(vv)
                                print(rvv)

                                incorrect_data += 1

                    elif rv.value_type() == registry.RegDWord:
                        vv = v.data
                            
                        rvv = rv.value()
                        if not rvv == vv:
                            print("DWORD INCORRECT: " + str(vv) + " != " + str(rvv))
                            print(list(vv))
                            print(rk.path())
                            print(rv.name())
                            print(rv.value())

                            incorrect_data += 1

                    elif rv.value_type() == registry.RegQWord:
                        vv = struct.unpack("<Q", v.data)[0]
                        rvv = rv.value()
                        if not rvv == vv:
                            print("QWORD INCORRECT: " + str(vv) + " != " + str(rvv))
                            print(rk.path())
                            print(rv.name())
                            print(rv.value())

                            incorrect_data += 1

                    elif rv.value_type() == registry.RegBin or \
                         rv.value_type() == registry.RegNone:
                        vv = v.data
                        rvv = rv.value()
                        if not rvv == vv:
                            print("BIN INCORRECT")
                            print(rk.path())
                            print(rv.name())

                            incorrect_data += 1

                except registry.RegistryValueNotFoundException:
                    print("VALUE NOT FOUND: " + k.name + ":" +  v.name)
                    not_found_values += 1

        except registry.RegistryKeyNotFoundException:
            print("KEY NOT FOUND: " + k.name)
            not_found_keys += 1

    if not_found_keys > 0:
        print("Unable to find %d keys" % (not_found_keys))
    else:
        print("Found all keys")

    if not_found_values > 0:
        print("Unable to find %d values" % (not_found_values))
    else:
        print("Found all values")

    if incorrect_data > 0:
        print("%d incorrect data values" % (incorrect_data))
    else:
        print("All supported data values correct")



########NEW FILE########
