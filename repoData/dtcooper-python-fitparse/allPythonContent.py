__FILENAME__ = activity
from fitparse.exceptions import FitParseError
from fitparse.base import FitFile


class Activity(FitFile):
    def parse(self, *args, **kwargs):
        return_value = super(Activity, self).parse(*args, **kwargs)
        if self.records[0].get_data('type') != 'activity':
            raise FitParseError("File parsed is not an activity file.")
        return return_value

########NEW FILE########
__FILENAME__ = base
import os
import struct

from fitparse.exceptions import FitParseError, FitParseComplete
from fitparse import records as r


class FitFile(object):
    FILE_HEADER_FMT = '2BHI4s'
    RECORD_HEADER_FMT = 'B'

    # First two bytes of a definition, to get endian_ness
    DEFINITION_PART1_FMT = '2B'
    # Second part, relies on endianness and tells us how large the rest is
    DEFINITION_PART2_FMT = 'HB'
    # Field definitions
    DEFINITION_PART3_FIELDDEF_FMT = '3B'

    CRC_TABLE = (
        0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
    )

    def __init__(self, f):
        '''
        Create a fit file. Argument f can be an open file-like object or a filename
        '''
        if isinstance(f, basestring):
            f = open(f, 'rb')

        # Private: call FitFile._read(), don't read from this. Important for CRC.
        self._file = f
        self._file_size = os.path.getsize(f.name)
        self._data_read = 0
        self._crc = 0

        self._last_timestamp = None
        self._global_messages = {}
        self.definitions = []
        self.records = []

    def get_records_by_type(self, t):
        # TODO: let t be a list/tuple of arbitary types (str, num, actual type)
        if isinstance(t, str):
            return (rec for rec in self.records if rec.type.name == t)
        elif isinstance(t, int):
            return (rec for rec in self.records if rec.type.num == t)
        elif isinstance(t, rec.MessageType):
            return (rec for rec in self.records if rec.type == t)
        else:
            return ()

    def get_records_as_dicts(self, t=None, with_ommited_fields=False):
        if t is None:
            records = self.records
        else:
            records = self.get_records_by_type(t)
        return (rec for rec in (rec.as_dict(with_ommited_fields) for rec in records) if rec)

    def parse(self, hook_func=None, hook_definitions=False):
        # TODO: Document hook function
        self._parse_file_header()

        try:
            while True:
                record = self._parse_record()
                if hook_func:
                    if hook_definitions or isinstance(record, r.DataRecord):
                        hook_func(record)
        except FitParseComplete:
            pass
        except Exception, e:
            self._file.close()
            raise FitParseError("Unexpected exception while parsing (%s: %s)" % (
                e.__class__.__name__, e,
            ))

        # Compare CRC (read last two bytes on _file without recalculating CRC)
        stored_crc, = struct.unpack('H', self._file.read(2))

        self._file.close()

        if stored_crc != self._crc:
            raise FitParseError("Invalid CRC")

    def _parse_record_header(self):
        header_data, = self._struct_read(FitFile.RECORD_HEADER_FMT)

        header_type = self._get_bit(header_data, 7)

        if header_type == r.RECORD_HEADER_NORMAL:
            message_type = self._get_bit(header_data, 6)
            local_message_type = header_data & 0b11111  # Bits 0-4
            # TODO: Should we set time_offset to 0?
            return r.RecordHeader(
                header_type, message_type, local_message_type, None,
            )
        else:
            # Compressed timestamp
            local_message_type = (header_data >> 5) & 0b11  # bits 5-6
            seconds_offset = header_data & 0b1111  # bits 0-3
            return r.RecordHeader(
                header_type, r.MESSAGE_DATA, local_message_type, seconds_offset)

    def _parse_definition_record(self, header):
        reserved, arch = self._struct_read(FitFile.DEFINITION_PART1_FMT)

        # We have the architecture now
        global_message_num, num_fields = self._struct_read(FitFile.DEFINITION_PART2_FMT, arch)

        # Fetch MessageType (unknown if it doesn't exist)
        message_type = r.MessageType(global_message_num)
        fields = []

        for field_num in range(num_fields):
            f_def_num, f_size, f_base_type_num = \
                               self._struct_read(FitFile.DEFINITION_PART3_FIELDDEF_FMT, arch)

            f_base_type_num = f_base_type_num & 0b11111  # bits 0-4

            try:
                field = message_type.fields[f_def_num]
            except (KeyError, TypeError):
                # unknown message has msg.fields as None = TypeError
                # if a known message doesn't define such a field = KeyError

                # Field type wasn't stored in message_type, fall back to a basic, unknown type
                field = r.Field(r.UNKNOWN_FIELD_NAME, r.FieldTypeBase(f_base_type_num), None, None, None)

            # XXX: -- very yucky!
            #  Convert extremely odd types where field size != type size to a byte
            #  field. They'll need to be handled customly. The FIT SDK has no examples
            #  of this but Cycling.fit on my Garmin Edge 500 does it, so I'll
            #  support it. This is probably the wrong way to do this, since it's
            #  not endian aware. Eventually, it should be a tuple/list of the type.
            #  Doing this will have to rethink the whole is_variable_size on FieldTypeBase
            calculated_f_size = struct.calcsize(
                self._get_endian_aware_struct(field.type.get_struct_fmt(f_size), arch)
            )
            if calculated_f_size != f_size:
                field = field._replace(type=r.FieldTypeBase(13))  # 13 = byte

            fields.append(r.AllocatedField(field, f_size))

        definition = r.DefinitionRecord(header, message_type, arch, fields)
        self._global_messages[header.local_message_type] = definition

        self.definitions.append(definition)

        return definition  # Do we need to return?

    def _parse_data_record(self, header):
        definition = self._global_messages[header.local_message_type]

        fields = []
        dynamic_fields = {}

        for i, (field, f_size) in enumerate(definition.fields):
            f_raw_data, = self._struct_read(field.type.get_struct_fmt(f_size), definition.arch)
            # BoundField handles data conversion (if necessary)
            bound_field = r.BoundField(f_raw_data, field)

            if field.name == r.COMPRESSED_TIMESTAMP_FIELD_NAME and \
               field.type.name == r.COMPRESSED_TIMESTAMP_TYPE_NAME:
                self._last_timestamp = f_raw_data

            fields.append(bound_field)

            if isinstance(field, r.DynamicField):
                dynamic_fields[i] = bound_field

        # XXX -- This could probably be refactored heavily. It's slow and a bit unclear.
        # Go through already bound fields that are dynamic fields
        if dynamic_fields:
            for dynamic_field_index, bound_field in dynamic_fields.iteritems():
                # Go by the reference field name and possible values
                for ref_field_name, possible_values in bound_field.field.possibilities.iteritems():
                    # Go through the definitions fields looking for the reference field
                    for field_index, (field, f_size) in enumerate(definition.fields):
                        # Did we find the refence field in the definition?
                        if field.name == ref_field_name:
                            # Get the reference field's value
                            ref_field_value = fields[field_index].data
                            # Is the reference field's value a value for a new dynamic field type?
                            new_field = possible_values.get(ref_field_value)
                            if new_field:
                                # Set it to the new type with old bound field's raw data
                                fields[dynamic_field_index] = r.BoundField(bound_field.raw_data, new_field)
                                break

        if header.type == r.RECORD_HEADER_COMPRESSED_TS:
            ts_field = definition.type.fields.get(r.TIMESTAMP_FIELD_DEF_NUM)
            if ts_field:
                timestamp = self._last_timestamp + header.seconds_offset
                fields.append(r.BoundField(timestamp, ts_field))
                self._last_timestamp = timestamp

        # XXX -- do compressed speed distance decoding here, similar to compressed ts
        # ie, inject the fields iff they're in definition.type.fields

        data = r.DataRecord(header, definition, fields)

        self.records.append(data)

        return data   # Do we need to return?

    def _parse_record(self):
        record_header = self._parse_record_header()

        if record_header.message_type == r.MESSAGE_DEFINITION:
            return self._parse_definition_record(record_header)
        else:
            return self._parse_data_record(record_header)

    @staticmethod
    def _get_bit(byte, bit_no):
        return (byte >> bit_no) & 1

    def _read(self, size):
        '''Call read from the file, otherwise the CRC won't match.'''

        if self._data_read >= self._file_size - 2:
            raise FitParseComplete

        data = self._file.read(size)
        self._data_read += size

        for byte in data:
            self._calc_crc(ord(byte))

        return data

    @staticmethod
    def _get_endian_aware_struct(fmt, endian):
        endian = '<' if endian == r.LITTLE_ENDIAN else '>'
        return '%s%s' % (endian, fmt)

    def _struct_read(self, fmt, endian=r.LITTLE_ENDIAN):
        fmt = self._get_endian_aware_struct(fmt, endian)
        data = self._read(struct.calcsize(fmt))
        return struct.unpack(fmt, data)

    def _calc_crc(self, char):
        # Taken almost verbatim from FITDTP section 3.3.2
        crc = self._crc
        tmp = FitFile.CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ FitFile.CRC_TABLE[char & 0xF]

        tmp = FitFile.CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        self._crc = crc ^ tmp ^ FitFile.CRC_TABLE[(char >> 4) & 0xF]

    def _parse_file_header(self):
        '''Parse a fit file's header. This needs to be the first operation
        performed when opening a file'''
        def throw_exception(error):
            raise FitParseError("Bad .FIT file header: %s" % error)

        if self._file_size < 12:
            throw_exception("Invalid file size")

        # Parse the FIT header
        header_size, self.protocol_version, self.profile_version, data_size, data_type = \
                   self._struct_read(FitFile.FILE_HEADER_FMT)
        num_extra_bytes = 0

        if header_size < 12:
            throw_exception("Invalid header size")
        elif header_size > 12:
            # Read and discard some extra bytes in the header
            # as per https://github.com/dtcooper/python-fitparse/issues/1
            num_extra_bytes = header_size - 12
            self._read(num_extra_bytes)

        if data_type != '.FIT':
            throw_exception('Data type not ".FIT"')

        # 12 byte header + 2 byte CRC = 14 bytes not included in that
        if self._file_size != 14 + data_size + num_extra_bytes:
            throw_exception("File size not set correctly in header.")

########NEW FILE########
__FILENAME__ = exceptions
class FitError(Exception):
    pass


class FitParseError(FitError):
    pass


class FitParseComplete(Exception):
    pass

########NEW FILE########
__FILENAME__ = records
from collections import namedtuple
import datetime
import math
import os


RECORD_HEADER_NORMAL = 0
RECORD_HEADER_COMPRESSED_TS = 1

MESSAGE_DEFINITION = 1
MESSAGE_DATA = 0

LITTLE_ENDIAN = 0
BIG_ENDIAN = 1

TIMESTAMP_FIELD_DEF_NUM = 253
COMPRESSED_TIMESTAMP_FIELD_NAME = 'timestamp'
COMPRESSED_TIMESTAMP_TYPE_NAME = 'date_time'

UNKNOWN_FIELD_NAME = 'unknown'


class RecordHeader(namedtuple('RecordHeader',
    ('type', 'message_type', 'local_message_type', 'seconds_offset'))):
    # type -- one of RECORD_HEADER_NORMAL, RECORD_HEADER_COMPRESSED_TS
    # message_type -- one of MESSAGE_DEFINITION, MESSAGE_DATA
    # local_message_type -- a number
    #    * for a definition message, the key to store in FitFile().global_messages
    #    * for a data message, the key to look up the associated definition
    # seconds_offset -- for RECORD_HEADER_COMPRESSED_TS, offset in seconds
    # NOTE: Though named similarly, none of these map to the namedtuples below
    __slots__ = ()


class FieldTypeBase(namedtuple('FieldTypeBase', ('num', 'name', 'invalid', 'struct_fmt', 'is_variable_size'))):
    # Yields a singleton if called with just a num
    __slots__ = ()
    _instances = {}

    def __new__(cls, num, *args, **kwargs):
        instance = FieldTypeBase._instances.get(num)
        if instance:
            return instance

        instance = super(FieldTypeBase, cls).__new__(cls, num, *args, **kwargs)
        FieldTypeBase._instances[num] = instance
        return instance

    def get_struct_fmt(self, size):
        if self.is_variable_size:
            return self.struct_fmt % size
        else:
            return self.struct_fmt

    def convert(self, raw_data):
        if callable(self.invalid):
            if self.invalid(raw_data):
                return None
        else:
            if raw_data == self.invalid:
                return None

        if self.name == 'string':
            raw_data = raw_data.rstrip('\x00')

        return raw_data

    @property
    def base(self):
        return self


class FieldType(namedtuple('FieldType', ('name', 'base', 'converter'))):
    # Higher level fields as defined in Profile.xls
    #
    # converter is a dict or a func. If type is uint*z, then converter should
    # look through the value as a bit array and return all found values
    __slots__ = ()
    _instances = {}

    def __new__(cls, name, *args, **kwargs):
        instance = FieldType._instances.get(name)
        if instance:
            return instance

        instance = super(FieldType, cls).__new__(cls, name, *args, **kwargs)
        FieldType._instances[name] = instance
        return instance

    @property
    def get_struct_fmt(self):
        return self.base.get_struct_fmt

    def convert(self, raw_data):
        if self.base.convert(raw_data) is None:
            return None
        elif isinstance(self.converter, dict):
            #if self.base.name in ('uint8z', 'uint16z', 'uint32z'):
            #    XXX -- handle this condition, ie return a list of properties
            return self.converter.get(raw_data, raw_data)
        elif callable(self.converter):
            return self.converter(raw_data)
        else:
            return raw_data


def _field_convert(self, raw_data):
    data = self.type.convert(raw_data)
    if isinstance(data, (int, float)):
        if self.scale:
            data = float(data) / self.scale
        if self.offset:
            data = data - self.offset
    return data


class Field(namedtuple('Field', ('name', 'type', 'units', 'scale', 'offset'))):
    # A name, type, units, scale, offset
    __slots__ = ()
    convert = _field_convert


class DynamicField(namedtuple('DynamicField', ('name', 'type', 'units', 'scale', 'offset', 'possibilities'))):
    # A name, type, units, scale, offset
    # TODO: Describe format of possiblities
    __slots__ = ()
    convert = _field_convert


class AllocatedField(namedtuple('AllocatedField', ('field', 'size'))):
    # A field along with its size
    __slots__ = ()

    @property
    def name(self):
        return self.field.name

    @property
    def type(self):
        return self.field.type


class BoundField(namedtuple('BoundField', ('data', 'raw_data', 'field'))):
    # Convert data
    __slots__ = ()

    def __new__(cls, raw_data, field):
        data = field.convert(raw_data)
        return super(BoundField, cls).__new__(cls, data, raw_data, field)

    @property
    def name(self):
        return self.field.name

    @property
    def type(self):
        return self.field.type

    @property
    def units(self):
        return self.field.units

    def items(self):
        return self.name, self.data


class MessageType(namedtuple('MessageType', ('num', 'name', 'fields'))):
    # TODO: Describe format of fields (dict)
    __slots__ = ()
    _instances = {}

    def __new__(cls, num, *args, **kwargs):
        instance = MessageType._instances.get(num)
        if instance:
            return instance

        try:
            instance = super(MessageType, cls).__new__(cls, num, *args, **kwargs)
        except TypeError:
            # Don't store unknown field types in _instances.
            # this would be a potential memory leak in a long-running parser
            return super(MessageType, cls).__new__(cls, num, 'unknown', None)

        MessageType._instances[num] = instance
        return instance

    @property
    def field_names(self):
        return [f.name for f in self.fields.values()]


class DefinitionRecord(namedtuple('DefinitionRecord', ('header', 'type', 'arch', 'fields'))):
    # arch -- Little endian or big endian
    # fields -- list of AllocatedFields
    # type -- MessageType
    __slots__ = ()

    @property
    def name(self):
        return self.type.name

    @property
    def num(self):
        return self.type.num


class DataRecord(namedtuple('DataRecord', ('header', 'definition', 'fields'))):
    # fields -- list of BoundFields
    __slots__ = ()

    @property
    def name(self):
        return self.definition.name

    @property
    def type(self):
        return self.definition.type

    @property
    def num(self):
        return self.definition.num

    def iteritems(self):
        return (f.items() for f in self.fields)

    def as_dict(self, with_ommited_fields=False):
        d = dict((k, v) for k, v in self.iteritems() if k != UNKNOWN_FIELD_NAME)
        if with_ommited_fields:
            for k in self.type.field_names:
                d.setdefault(k, None)
        return d

    def get_valid_field_names(self):
        return [f.name for f in self.fields if f.name != UNKNOWN_FIELD_NAME and f.data is not None]

    def get_data(self, field_name):
        for field in self.fields:
            if field.name == field_name:
                return field.data
        return None

    def get_units(self, field_name):
        for field in self.fields:
            if field.name == field_name:
                return field.units
        return None


# Definitions from FIT SDK 1.2

FieldTypeBase(0, 'enum', 0xFF, 'B', False)
FieldTypeBase(1, 'sint8', 0x7F, 'b', False)
FieldTypeBase(2, 'uint8', 0xFF, 'B', False)
FieldTypeBase(3, 'sint16', 0x7FFF, 'h', False)
FieldTypeBase(4, 'uint16', 0xFFFF, 'H', False)
FieldTypeBase(5, 'sint32', 0x7FFFFFFF, 'i', False)
FieldTypeBase(6, 'uint32', 0xFFFFFFFF, 'I', False)
FieldTypeBase(7, 'string', lambda x: all([ord(c) == '\x00' for c in x]), '%ds', True)
FieldTypeBase(8, 'float32', math.isnan, 'f', False)
FieldTypeBase(9, 'float64', math.isnan, 'd', False)
FieldTypeBase(10, 'uint8z', 0, 'B', False)
FieldTypeBase(11, 'uint16z', 0, 'H', False)
FieldTypeBase(12, 'uint32z', 0, 'I', False)
FieldTypeBase(13, 'byte', lambda x: all([ord(c) == '\xFF' for c in x]), '%ds', True)


# Custom conversion functions for FieldTypes (specific to FIT SDK 1.2)

# TODO:
#   "0x10000000: if date_time is < 0x10000000 then it is system time (seconds
#   from device power on)" -- not ofr local_date_time
_convert_date_time = lambda x: datetime.datetime.fromtimestamp(631065600 + x)

# TODO: Handle local tz conversion
_convert_local_date_time = lambda x: datetime.datetime.fromtimestamp(631065600 + x)

_convert_bool = lambda x: bool(x)


# XXX -- untested
# see FitSDK1_2.zip:c/examples/decode/decode.c lines 121-150 for an example
def _convert_record_compressed_speed_distance(raw_data):
    first, second, third = (ord(b) for b in raw_data)
    speed = first + (second & 0b1111)
    distance = (third << 4) + ((second & 0b11110000) >> 4)
    return speed / 100. / 1000. * 60. * 60., distance / 16.


class MessageIndexValue(int):
    __slots__ = ('selected',)


def _convert_message_index(raw_data):
    message_index = MessageIndexValue(raw_data & 0x0FFF)
    message_index.selected = bool(raw_data & 0x8000)
    return message_index


class ActivityClassValue(int):
    __slots__ = ('athlete',)


def _convert_activity_class(raw_data):
    activity_class = ActivityClassValue(raw_data & 0x7F)
    activity_class.athlete = bool(raw_data & 0x80)
    return activity_class


# Load in Profile

# XXX -- we do this so ipython doesn't throw an error on __file__.
try:
    execfile('profile.def')
except IOError:
    execfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profile.def'))

########NEW FILE########
__FILENAME__ = generate_profile
#!/usr/bin/env python

#
# Extremely crude script that I'm not at all proud of. Generate
# fitparse/profile.def from the Profile.xls definition file that comes with
# the FIT SDK. You shouldn't have to run this, since I've included an
# automatically generated profile.dif file.
#
# (NOTE: it'll probably break on any version of the FIT SDK that isn't 1.2)
#

# TODO: Units override code -- for at least,
#  * date_time -- it's "s" now, want None
#  * compressed_speed_distance -- it's "m/s,\nm", probably want None

from collections import namedtuple
import datetime
import os
import sys

import xlrd


def banner_str(s):
    return ("   %s   " % s).center(BANNER_PADDING, '#')


# TODO: Maybe make a copyright, or more info about this program/library?
BANNER_PADDING = 78
PROFILE_OUTPUT_FILE_HEADER_MAGIC = '%s\n%s\n%s' % (
    '#' * BANNER_PADDING,
    banner_str('AUTOMATICALLY GENERATED DEFINITION FILE'),
    '#' * BANNER_PADDING,
)

PROFILE_OUTPUT_FILE_HEADER_FMT = '''%s
#
# %%s -- Exported FIT SDK Profile Data
# Created on %%s by %%s from %%s
#
''' % PROFILE_OUTPUT_FILE_HEADER_MAGIC


# Using namedtuples for convience. These have absolutely nothing to do with the
# ones in found in fitparse.records, other than Field and DynamicField which
# are the similar to their counterparts in records.py by coincidence

Field = namedtuple('Field', ('name', 'type', 'scale', 'units', 'offset'))
DynamicField = namedtuple('DynamicField', ('name', 'type', 'scale', 'units', 'offset', 'possibilities'))
# Type.values can be a str, (ie, a lambda or the name of a function defined in records.py)
Type = namedtuple('Type', ('name', 'base_type', 'values'))
TypeValue = namedtuple('TypeValue', ('name', 'value'))
SpecialFunctionType = namedtuple('SpecialFunctionType', ('name', 'base_type', 'func_name'))

FIELD_BASE_TYPES = {
    'enum': 0,
    'sint8': 1,
    'uint8': 2,
    'sint16': 3,
    'uint16': 4,
    'sint32': 5,
    'uint32': 6,
    'string': 7,
    'float32': 8,
    'float64': 9,
    'uint8z': 10,
    'uint16z': 11,
    'uint32z': 12,
    'byte': 13,
}

## Special fields in messages -- syntax "<message_name>-<field_name>"
SPECIAL_TYPES = {
    # '[<message_name>-]<field_name>': SpecialFunctionType('<base_type>', <function_str or None for default>),
    'bool': SpecialFunctionType('bool', 'enum', None),
    'record-compressed_speed_distance': SpecialFunctionType('record-compressed_speed_distance', 'byte', None),
}

# Same as SPECIAL_TYPES, but these will exist in the types dict after parse_fields()
SPECIAL_TYPES_IN_TYPES_SPREADSHEET = {
    'date_time': SpecialFunctionType('date_time', 'uint32', None),
    'local_date_time': SpecialFunctionType('local_date_time', 'uint32', None),
    'message_index': SpecialFunctionType('message_index', 'uint16', None),
    'activity_class': SpecialFunctionType('activity_class', 'enum', None),
}

SPECIAL_TYPES_ALL = dict(SPECIAL_TYPES.items() + SPECIAL_TYPES_IN_TYPES_SPREADSHEET.items())

if len(sys.argv) <= 1 or not os.path.exists(sys.argv[1]):
    print "Usage: %s <Profile.xls> [profile.def]" % os.path.basename(sys.argv[0])
    sys.exit(0)

profile_xls_filename = sys.argv[1]
workbook = xlrd.open_workbook(profile_xls_filename)

write_buffer = ""


def write(s):
    global write_buffer
    write_buffer += str(s)


def writeln(s=''):
    write(str(s) + "\n")


def parse_types():
    # Go through Types workbook

    types_sheet = workbook.sheet_by_name('Types')
    types = {}

    for row in range(1, types_sheet.nrows):
        row_values = [str(v).strip() if isinstance(v, (str, unicode)) else v \
                      for v in types_sheet.row_values(row, end_colx=4)]

        if not any(row_values):
            continue

        possible_type_name, possible_base_type, name, value = row_values

        if possible_type_name:
            type_name = possible_type_name
            base_type = possible_base_type

        if possible_type_name:
            # We define a type here
            types[type_name] = Type(type_name, base_type, {})

        elif name:
            if 'int' in base_type or base_type == 'enum':
                # Convert value to int if required
                if type(value) == float and value % 1 == 0.0:
                    value = int(value)

            types[type_name].values[value] = TypeValue(name, value)

    types.update(SPECIAL_TYPES)

    # Special considerations on types dict

    ## FOR NOW: skip mfg_range_min (0xFF00) and mfg_range_max (0xFFFE)
    for value in [v.value for v in types['mesg_num'].values.copy().itervalues()
                  if v.name in ('mfg_range_min', 'mfg_range_max')]:
        del types['mesg_num'].values[value]

    return types


### Go through Message workbook ###

def parse_fields():
    messages_sheet = workbook.sheet_by_name('Messages')

    fields = {}
    last_field = None
    last_f_def_num = None

    for row in range(1, messages_sheet.nrows):
        row_values = [str(v).strip() if isinstance(v, (str, unicode)) else v \
                      for v in messages_sheet.row_values(row, end_colx=4)]

        # Skip blank rows
        if not any(row_values):
            continue

        # Check if it's a seperator row, ie only third column
        if not any(row_values[:3]) and row_values[3]:
            # TODO: here row_values[3] describes what file type these messages belong to
            continue

        possible_message_name, f_def_num, f_name, f_type = row_values

        if possible_message_name:
            # Define a message here
            message_name = possible_message_name
            fields[message_name] = {}
        else:
            # Sip for now unless all rows are here
            if not (message_name and f_name and f_type):
                pass
            else:

                is_dynamic_field = False

                try:
                    f_def_num = int(f_def_num)
                except ValueError:
                    # f_def_num not defined, we have a dynamic field on last_field
                    is_dynamic_field = True

                    if not isinstance(last_field, DynamicField):
                        last_field = DynamicField(*(tuple(last_field) + ({},)))
                        fields[message_name][last_f_def_num] = last_field

                    ref_field_names = [str(n).strip() for n in messages_sheet.row_values(row)[11].split(',')]
                    ref_field_values = [str(n).strip() for n in messages_sheet.row_values(row)[12].split(',')]

                    if len(ref_field_names) != len(ref_field_values):
                        raise Exception("Number of ref fields != number of ref values for %s" % f_name)

                try:
                    f_scale = int(messages_sheet.row_values(row)[6])
                    if f_scale == 1:
                        raise ValueError
                except ValueError:
                    f_scale = None

                try:
                    f_offset = int(messages_sheet.row_values(row)[7])
                except ValueError:
                    f_offset = None

                f_units = str(messages_sheet.row_values(row)[8]).strip()
                if not f_units:
                    f_units = None

                field = Field(f_name, f_type, f_scale, f_units, f_offset)

                if is_dynamic_field:
                    for i in range(len(ref_field_names)):
                        last_field.possibilities.setdefault(ref_field_names[i], {})[ref_field_values[i]] = field

                else:
                    fields[message_name][f_def_num] = field
                    last_field = field
                    last_f_def_num = f_def_num

    # Special considerations on fields dict

    # Copy possiblities for event.data into event.data16
    event = fields['event']
    for k, v in event.iteritems():
        if v.name == 'data':
            data_num = k
        elif v.name == 'data16':
            data16_num = k
    try:
        event[data16_num] = DynamicField(*tuple(event[data16_num] + (event[data_num].possibilities.copy(),)))
    except NameError:
        raise Exception("Couldn't find fields data/data16 in message type event")

    return fields


def autogen_python(types, fields):
    global write_buffer

    functions = {}

    writeln("\n%s\n" % banner_str('BEGIN FIELD TYPES'))

    for _, type in sorted(types.iteritems()):

        write("FieldType(%s, FieldTypeBase(%s), " % (repr(type.name), FIELD_BASE_TYPES[type.base_type]))

        if type.name in SPECIAL_TYPES_ALL:
            special_type = SPECIAL_TYPES_ALL[type.name]
            if type.base_type != special_type.base_type:
                raise Exception("Type misatch on '%s'" % type.name)

            func_name = special_type.func_name
            if not special_type.func_name:
                func_name = '_convert_%s' % type.name.replace('-', '_')
            functions.setdefault(func_name, []).append(type.name)

            writeln("%s)  # base type: %s\n" % (func_name, type.base_type))

        else:
            writeln("{  # base type: %s" % type.base_type)
            for _, value in sorted(type.values.iteritems()):
                writeln("    %s: %s," % (value.value, repr(value.name)))
            writeln("})\n")

    writeln("\n%s\n" % banner_str('BEGIN MESSAGE TYPES'))

    for msg_num, message in sorted(types['mesg_num'].values.iteritems()):
        msg_name = message.name

        writeln("MessageType(%s, %s, {" % (msg_num, repr(msg_name)))

        msg_fields = fields[msg_name]
        for f_num, field in sorted(msg_fields.iteritems()):
            write("    %s: " % f_num)

            def field_gen(field):
                is_base_type = False
                is_special_function_type = False
                write("%s(%s, " % (field.__class__.__name__, repr(field.name)))

                special_type_name = "%s-%s" % (msg_name, field.name)
                # Predefined type
                if field.type in types or special_type_name in types:
                    type_name = field.type
                    special_type = SPECIAL_TYPES_ALL.get(special_type_name)
                    if special_type:
                        type_name = special_type_name
                        is_special_function_type = True
                        if special_type.base_type != field.type:
                            raise Exception("Type misatch on '%s'" % field.name)

                    write("FieldType(%s)," % repr(type_name))

                # Base type
                elif field.type in FIELD_BASE_TYPES:
                    write("FieldTypeBase(%s)," % FIELD_BASE_TYPES[field.type])
                    is_base_type = True
                else:
                    raise Exception("Unknown field type: %s" % field.type)

                write(" %s, %s, %s" % (
                    repr(field.units), repr(field.scale), repr(field.offset)))

                if isinstance(field, DynamicField):
                    write(", {")
                else:
                    write('),')

                write("  # base type: ")
                if is_base_type or is_special_function_type:
                    writeln(field.type)
                else:
                    writeln(types[field.type].base_type)

            field_gen(field)

            if isinstance(field, DynamicField):
                for ref_name, dynamic_fields in field.possibilities.iteritems():
                    writeln('        %s: {' % repr(ref_name))
                    for ref_value, dynamic_field in dynamic_fields.iteritems():
                        write('            %s: ' % repr(ref_value))
                        field_gen(dynamic_field)
                    writeln('        },')
                writeln('    }),')
        writeln("})\n")

    writeln("\n%s\n" % banner_str('DELETE CONVERSION FUNCTIONS'))

    for func in sorted(set(functions.iterkeys())):
        writeln("del %s" % func)

    writeln("\n\n%s" % banner_str('AUTOGENERATION COMPLETE'))

    # Prepend a required functions header to write_buffer
    req_func_out = '#' * BANNER_PADDING + "\n#\n"
    req_func_out += "# Please define the following functions (types that use them are listed):\n#\n"
    for func_name, type_names in sorted(functions.iteritems()):
        req_func_out += "#  %s\n" % func_name
        req_func_out += "#    * Used by types:\n"
        for type_name in type_names:
            req_func_out += "#       - %s\n" % type_name
        req_func_out += '#\n'
    req_func_out += ('#' * BANNER_PADDING) + "\n\n"

    write_buffer = req_func_out + write_buffer


def main():
    global write_buffer

    profile_output_filename = None

    if len(sys.argv) >= 3:
        profile_output_filename = sys.argv[2]

        if os.path.exists(profile_output_filename):
            old_profile = open(profile_output_filename, 'r').read()
            if PROFILE_OUTPUT_FILE_HEADER_MAGIC not in old_profile:
                print "Couldn't find header in %s. Exiting." % profile_output_filename
                sys.exit(1)
            del old_profile

        # Generate header
        profile_header = PROFILE_OUTPUT_FILE_HEADER_FMT % (
            os.path.basename(profile_output_filename),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            os.path.basename(__file__),
            os.path.basename(profile_xls_filename),
        )

    if profile_output_filename:
        print "Generating profile from %s" % profile_xls_filename

    types = parse_types()
    fields = parse_fields()

    autogen_python(types, fields)

    if profile_output_filename:
        print "Writing to %s" % profile_output_filename
        profile_output_file = open(profile_output_filename, 'w')
        copyright_header = open(os.path.abspath(__file__)).readlines()
        copyright_header = (''.join(copyright_header[1:copyright_header.index('\n')])).strip()
        profile_output_file.write(copyright_header + "\n\n\n")
        profile_output_file.write(profile_header)
        profile_output_file.write(write_buffer)
        profile_output_file.close()
    else:
        print write_buffer


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sample_program
#!/usr/bin/env python

import os
import sys

# Add folder to search path

PROJECT_PATH = os.path.realpath(os.path.join(sys.path[0], '..'))
sys.path.append(PROJECT_PATH)

from fitparse import Activity

quiet = 'quiet' in sys.argv or '-q' in sys.argv
filenames = None

if len(sys.argv) >= 2:
    filenames = [f for f in sys.argv[1:] if os.path.exists(f)]

if not filenames:
    filenames = [os.path.join(PROJECT_PATH, 'tests', 'data', 'sample-activity.fit')]


def print_record(rec, ):
    global record_number
    record_number += 1
    print ("-- %d. #%d: %s (%d entries) " % (record_number, rec.num, rec.type.name, len(rec.fields))).ljust(60, '-')
    for field in rec.fields:
        to_print = "%s [%s]: %s" % (field.name, field.type.name, field.data)
        if field.data is not None and field.units:
            to_print += " [%s]" % field.units
        print to_print
    print

for f in filenames:
    if quiet:
        print f
    else:
        print ('##### %s ' % f).ljust(60, '#')

    print_hook_func = None
    if not quiet:
        print_hook_func = print_record

    record_number = 0
    a = Activity(f)
    a.parse(hook_func=print_hook_func)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import os
import sys
import unittest

PROJECT_PATH = os.path.realpath(os.path.join(sys.path[0], '..'))
sys.path.append(PROJECT_PATH)

from fitparse.base import FitFile


def testfile(*filename):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'data',
        os.path.join(*filename),
    )


class FitFileTestCase(unittest.TestCase):
    def test_fitfile_parses_with_correct_number_of_recs_defs_and_file_size_and_CRC(self):
        fit = FitFile(testfile('sample-activity.fit'))
        fit.parse()

        self.assertEquals(len(fit.records), 3228)
        self.assertEquals(len(fit.definitions), 9)
        self.assertEquals(fit._file_size, 104761)
        self.assertEquals(fit._crc, 0x75C5)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
