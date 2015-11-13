__FILENAME__ = mongodb
#!/usr/bin/env python
# encoding: utf-8

from types import *
from time import *
from datetime import datetime
from pymongo import Connection as MongoConnection
from pymongo import database
from pymongo import collection as MongoCollection
from pymongo.cursor import Cursor

class MongoDB:
    
    def show_dbs(self, host, port):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            dbs = c.database_names()
        except Exception, err:
            return -1
        return dbs
    
    def show_collections(self, host, port, dbname):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            db = database.Database(c, dbname)
            collections = db.collection_names()
        except Exception, err:
            return -1
        return collections
    
    def drop_collection(self, host, port, dbname, collection_name):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            db = database.Database(c, dbname)
            db.drop_collection(collection_name)
        except Exception, err:
            return -1
        return db
    
    def drop_database(self, host, port, dbname):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            c.drop_database(dbname)
        except Exception, err:
            return -1
        return c
    
    def browse_collection(self, host, port, dbname, collection_name, page, step):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            db = database.Database(c, dbname)
            cl = MongoCollection.Collection(db, collection_name)
            res = cl.find(skip = (int(page) -1) * int(step), limit = int(step))
            entries = []
            for r in res:
                tmp = {}
                for k, v in r.items():
                    if isinstance(v, datetime):
                        tmp[k] = strftime('%Y-%m-%d %X', datetime.timetuple(v))
                    else:
                        tmp[k] = v
                entries.append(tmp)
            return {'count':cl.count(), 'entries': entries}
        except Exception, err:
            return -1
        return collections
    
    def query(self, host, port, dbname, query):
        try:
            c = MongoConnection(host=host, port=int(port), pool_size=1)
            db = database.Database(c, dbname)
            if not query.startswith('db.'):
                return -2
            res = eval(query)
            if isinstance(res, (GeneratorType, ListType, Cursor)):
                entries = []
                try:
                    for r in res:
                        tmp = {}
                        for k, v in r.items():
                            if isinstance(v, datetime):
                                tmp[k] = strftime('%Y-%m-%d %X', datetime.timetuple(v))
                            else:
                                tmp[k] = v
                        entries.append(tmp)
                    return {'count':len(entries), 'entries': entries}
                except:
                    return str(res)
            else:
                return str(res)
        except Exception, err:
            return -1
        return collections
########NEW FILE########
__FILENAME__ = binary
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for representing binary data to be stored in MongoDB.
"""

import types


class Binary(str):
    """Representation of binary data to be stored in or retrieved from MongoDB.

    This is necessary because we want to store Python strings as the BSON
    string type. We need to wrap binary data so we can tell the difference
    between what should be considered binary data and what should be considered
    a string when we encode to BSON.

    Raises TypeError if `data` is not an instance of str or `subtype` is
    not an instance of int. Raises ValueError if `subtype` is not in [0, 256).

    :Parameters:
      - `data`: the binary data to represent
      - `subtype` (optional): the `binary subtype
        <http://www.mongodb.org/display/DOCS/BSON#BSON-noteondatabinary>`_
        to use
    """

    def __new__(cls, data, subtype=2):
        if not isinstance(data, types.StringType):
            raise TypeError("data must be an instance of str")
        if not isinstance(subtype, types.IntType):
            raise TypeError("subtype must be an instance of int")
        if subtype >= 256 or subtype < 0:
            raise ValueError("subtype must be contained in [0, 256)")
        self = str.__new__(cls, data)
        self.__subtype = subtype
        return self

    def subtype(self):
        """Subtype of this binary data.
        """
        return self.__subtype
    subtype = property(subtype)

    def __eq__(self, other):
        if isinstance(other, Binary):
            return (self.__subtype, str(self)) == (other.__subtype, str(other))
        # We don't return NotImplemented here because if we did then
        # Binary("foo") == "foo" would return True, since Binary is a subclass
        # of str...
        return False

    def __repr__(self):
        return "Binary(%s, %s)" % (str.__repr__(self), self.__subtype)

########NEW FILE########
__FILENAME__ = bson
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for dealing with Mongo's BSON data representation.

Generally not needed to be used by application developers."""

import types
import struct
import re
import datetime
import calendar

from binary import Binary
from code import Code
from objectid import ObjectId
from dbref import DBRef
from son import SON
from errors import InvalidBSON, InvalidDocument
from errors import InvalidName, InvalidStringData

try:
    import _cbson
    _use_c = True
except ImportError:
    _use_c = False

try:
    import uuid
    _use_uuid = True
except ImportError:
    _use_uuid = False


def _get_int(data):
    try:
        value = struct.unpack("<i", data[:4])[0]
    except struct.error:
        raise InvalidBSON()

    return (value, data[4:])


def _get_c_string(data):
    try:
        end = data.index("\x00")
    except ValueError:
        raise InvalidBSON()

    return (unicode(data[:end], "utf-8"), data[end + 1:])


def _make_c_string(string):
    if "\x00" in string:
        raise InvalidStringData("BSON strings must not contain a NULL character")
    if isinstance(string, unicode):
        return string.encode("utf-8") + "\x00"
    else:
        try:
            string.decode("utf-8")
            return string + "\x00"
        except:
            raise InvalidStringData("strings in documents must be valid "
                                    "UTF-8: %r" % string)


def _validate_number(data):
    assert len(data) >= 8
    return data[8:]


def _validate_string(data):
    (length, data) = _get_int(data)
    assert len(data) >= length
    assert data[length - 1] == "\x00"
    return data[length:]


def _validate_object(data):
    return _validate_document(data, None)


_valid_array_name = re.compile("^\d+$")


def _validate_array(data):
    return _validate_document(data, _valid_array_name)


def _validate_binary(data):
    (length, data) = _get_int(data)
    # + 1 for the subtype byte
    assert len(data) >= length + 1
    return data[length + 1:]


def _validate_undefined(data):
    return data


_OID_SIZE = 12


def _validate_oid(data):
    assert len(data) >= _OID_SIZE
    return data[_OID_SIZE:]


def _validate_boolean(data):
    assert len(data) >= 1
    return data[1:]


_DATE_SIZE = 8


def _validate_date(data):
    assert len(data) >= _DATE_SIZE
    return data[_DATE_SIZE:]


_validate_null = _validate_undefined


def _validate_regex(data):
    (regex, data) = _get_c_string(data)
    (options, data) = _get_c_string(data)
    return data


def _validate_ref(data):
    data = _validate_string(data)
    return _validate_oid(data)


_validate_code = _validate_string


def _validate_code_w_scope(data):
    (length, data) = _get_int(data)
    assert len(data) >= length + 1
    return data[length + 1:]


_validate_symbol = _validate_string


def _validate_number_int(data):
    assert len(data) >= 4
    return data[4:]


def _validate_timestamp(data):
    assert len(data) >= 8
    return data[8:]

def _validate_number_long(data):
    assert len(data) >= 8
    return data[8:]


_element_validator = {
    "\x01": _validate_number,
    "\x02": _validate_string,
    "\x03": _validate_object,
    "\x04": _validate_array,
    "\x05": _validate_binary,
    "\x06": _validate_undefined,
    "\x07": _validate_oid,
    "\x08": _validate_boolean,
    "\x09": _validate_date,
    "\x0A": _validate_null,
    "\x0B": _validate_regex,
    "\x0C": _validate_ref,
    "\x0D": _validate_code,
    "\x0E": _validate_symbol,
    "\x0F": _validate_code_w_scope,
    "\x10": _validate_number_int,
    "\x11": _validate_timestamp,
    "\x12": _validate_number_long}


def _validate_element_data(type, data):
    try:
        return _element_validator[type](data)
    except KeyError:
        raise InvalidBSON("unrecognized type: %s" % type)


def _validate_element(data, valid_name):
    element_type = data[0]
    (element_name, data) = _get_c_string(data[1:])
    if valid_name:
        assert valid_name.match(element_name), "name is invalid"
    return _validate_element_data(element_type, data)


def _validate_elements(data, valid_name):
    while data:
        data = _validate_element(data, valid_name)


def _validate_document(data, valid_name=None):
    try:
        obj_size = struct.unpack("<i", data[:4])[0]
    except struct.error:
        raise InvalidBSON()

    assert obj_size <= len(data)
    obj = data[4:obj_size]
    assert len(obj)

    eoo = obj[-1]
    assert eoo == "\x00"

    elements = obj[:-1]
    _validate_elements(elements, valid_name)

    return data[obj_size:]


def _get_number(data):
    return (struct.unpack("<d", data[:8])[0], data[8:])


def _get_string(data):
    return _get_c_string(data[4:])


def _get_object(data):
    (object, data) = _bson_to_dict(data)
    if "$ref" in object:
        return (DBRef(object["$ref"], object["$id"], object.get("$db", None)), data)
    return (object, data)


def _get_array(data):
    (obj, data) = _get_object(data)
    result = []
    i = 0
    while True:
        try:
            result.append(obj[str(i)])
            i += 1
        except KeyError:
            break
    return (result, data)


def _get_binary(data):
    (length, data) = _get_int(data)
    subtype = ord(data[0])
    data = data[1:]
    if subtype == 2:
        (length2, data) = _get_int(data)
        if length2 != length - 4:
            raise InvalidBSON("invalid binary (st 2) - lengths don't match!")
        length = length2
    if subtype == 3 and _use_uuid:
        return (uuid.UUID(bytes=data[:length]), data[length:])
    return (Binary(data[:length], subtype), data[length:])


def _get_oid(data):
    return (ObjectId(data[:12]), data[12:])


def _get_boolean(data):
    return (data[0] == "\x01", data[1:])


def _get_date(data):
    seconds = float(struct.unpack("<q", data[:8])[0]) / 1000.0
    return (datetime.datetime.utcfromtimestamp(seconds), data[8:])


def _get_code_w_scope(data):
    (_, data) = _get_int(data)
    (code, data) = _get_string(data)
    (scope, data) = _get_object(data)
    return (Code(code, scope), data)


def _get_null(data):
    return (None, data)


def _get_regex(data):
    (pattern, data) = _get_c_string(data)
    (bson_flags, data) = _get_c_string(data)
    flags = 0
    if "i" in bson_flags:
        flags |= re.IGNORECASE
    if "l" in bson_flags:
        flags |= re.LOCALE
    if "m" in bson_flags:
        flags |= re.MULTILINE
    if "s" in bson_flags:
        flags |= re.DOTALL
    if "u" in bson_flags:
        flags |= re.UNICODE
    if "x" in bson_flags:
        flags |= re.VERBOSE
    return (re.compile(pattern, flags), data)


def _get_ref(data):
    (collection, data) = _get_c_string(data[4:])
    (oid, data) = _get_oid(data)
    return (DBRef(collection, oid), data)


def _get_timestamp(data):
    (timestamp, data) = _get_int(data)
    (inc, data) = _get_int(data)
    return ((timestamp, inc), data)

def _get_long(data):
    return (struct.unpack("<q", data[:8])[0], data[8:])

_element_getter = {
    "\x01": _get_number,
    "\x02": _get_string,
    "\x03": _get_object,
    "\x04": _get_array,
    "\x05": _get_binary,
    "\x06": _get_null, # undefined
    "\x07": _get_oid,
    "\x08": _get_boolean,
    "\x09": _get_date,
    "\x0A": _get_null,
    "\x0B": _get_regex,
    "\x0C": _get_ref,
    "\x0D": _get_string, # code
    "\x0E": _get_string, # symbol
    "\x0F": _get_code_w_scope,
    "\x10": _get_int, # number_int
    "\x11": _get_timestamp,
    "\x12": _get_long,
}


def _element_to_dict(data):
    element_type = data[0]
    (element_name, data) = _get_c_string(data[1:])
    (value, data) = _element_getter[element_type](data)
    return (element_name, value, data)


def _elements_to_dict(data):
    result = {}
    while data:
        (key, value, data) = _element_to_dict(data)
        result[key] = value
    return result


def _bson_to_dict(data):
    obj_size = struct.unpack("<i", data[:4])[0]
    elements = data[4:obj_size - 1]
    return (_elements_to_dict(elements), data[obj_size:])
if _use_c:
    _bson_to_dict = _cbson._bson_to_dict


_RE_TYPE = type(_valid_array_name)


def _element_to_bson(key, value, check_keys):
    if not isinstance(key, (str, unicode)):
        raise InvalidDocument("documents must have only string keys, key was %r" % key)

    if check_keys:
        if key.startswith("$"):
            raise InvalidName("key %r must not start with '$'" % key)
        if "." in key:
            raise InvalidName("key %r must not contain '.'" % key)

    name = _make_c_string(key)
    if isinstance(value, float):
        return "\x01" + name + struct.pack("<d", value)

    # Use Binary w/ subtype 3 for UUID instances
    try:
        import uuid

        if isinstance(value, uuid.UUID):
            value = Binary(value.bytes, subtype=3)
    except ImportError:
        pass

    if isinstance(value, Binary):
        subtype = value.subtype
        if subtype == 2:
            value = struct.pack("<i", len(value)) + value
        return "\x05%s%s%s%s" % (name, struct.pack("<i", len(value)),
                                 chr(subtype), value)
    if isinstance(value, Code):
        cstring = _make_c_string(value)
        scope = _dict_to_bson(value.scope, False)
        full_length = struct.pack("<i", 8 + len(cstring) + len(scope))
        length = struct.pack("<i", len(cstring))
        return "\x0F" + name + full_length + length + cstring + scope
    if isinstance(value, str):
        cstring = _make_c_string(value)
        length = struct.pack("<i", len(cstring))
        return "\x02" + name + length + cstring
    if isinstance(value, unicode):
        cstring = _make_c_string(value)
        length = struct.pack("<i", len(cstring))
        return "\x02" + name + length + cstring
    if isinstance(value, dict):
        return "\x03" + name + _dict_to_bson(value, check_keys)
    if isinstance(value, (list, tuple)):
        as_dict = SON(zip([str(i) for i in range(len(value))], value))
        return "\x04" + name + _dict_to_bson(as_dict, check_keys)
    if isinstance(value, ObjectId):
        return "\x07" + name + value.binary
    if value is True:
        return "\x08" + name + "\x01"
    if value is False:
        return "\x08" + name + "\x00"
    if isinstance(value, (int, long)):
        # TODO this is a really ugly way to check for this...
        if value > 2**64 / 2 - 1 or value < -2**64 / 2:
            raise OverflowError("MongoDB can only handle up to 8-byte ints")
        if value > 2**32 / 2 - 1 or value < -2**32 / 2:
            return "\x12" + name + struct.pack("<q", value)
        return "\x10" + name + struct.pack("<i", value)
    if isinstance(value, datetime.datetime):
        millis = int(calendar.timegm(value.timetuple()) * 1000 +
                     value.microsecond / 1000)
        return "\x09" + name + struct.pack("<q", millis)
    if value is None:
        return "\x0A" + name
    if isinstance(value, _RE_TYPE):
        pattern = value.pattern
        flags = ""
        if value.flags & re.IGNORECASE:
            flags += "i"
        if value.flags & re.LOCALE:
            flags += "l"
        if value.flags & re.MULTILINE:
            flags += "m"
        if value.flags & re.DOTALL:
            flags += "s"
        if value.flags & re.UNICODE:
            flags += "u"
        if value.flags & re.VERBOSE:
            flags += "x"
        return "\x0B" + name + _make_c_string(pattern) + _make_c_string(flags)
    if isinstance(value, DBRef):
        return _element_to_bson(key, value.as_doc(), False)

    raise InvalidDocument("cannot convert value of type %s to bson" %
                          type(value))


def _dict_to_bson(dict, check_keys):
    try:
        elements = ""
        if "_id" in dict:
            elements += _element_to_bson("_id", dict["_id"], False)
        for (key, value) in dict.iteritems():
            if key != "_id":
                elements += _element_to_bson(key, value, check_keys)
    except AttributeError:
        raise TypeError("encoder expected a mapping type but got: %r" % dict)

    length = len(elements) + 5
    if length > 4 * 1024 * 1024:
        raise InvalidDocument("document too large - BSON documents are limited "
                              "to 4 MB")
    return struct.pack("<i", length) + elements + "\x00"
if _use_c:
    _dict_to_bson = _cbson._dict_to_bson


def _to_dicts(data):
    """Convert binary data to sequence of SON objects.

    Data must be concatenated strings of valid BSON data.

    :Parameters:
      - `data`: bson data
    """
    dicts = []
    while len(data):
        (son, data) = _bson_to_dict(data)
        dicts.append(son)
    return dicts
if _use_c:
    _to_dicts = _cbson._to_dicts


def _to_dict(data):
    (son, _) = _bson_to_dict(data)
    return son


def is_valid(bson):
    """Validate that the given string represents valid BSON data.

    Raises TypeError if the data is not an instance of a subclass of str.
    Returns True if the data represents a valid BSON object, False otherwise.

    :Parameters:
      - `bson`: the data to be validated
    """
    if not isinstance(bson, types.StringType):
        raise TypeError("BSON data must be an instance of a subclass of str")

    # 4 MB limit
    if len(bson) > 4 * 1024 * 1024:
        raise InvalidBSON("BSON documents are limited to 4MB")

    try:
        remainder = _validate_document(bson)
        return remainder == ""
    except (AssertionError, InvalidBSON):
        return False


class BSON(str):
    """BSON data.

    Represents binary data storable in and retrievable from Mongo.
    """

    def __new__(cls, bson):
        """Initialize a new BSON object with some data.

        Raises TypeError if `bson` is not an instance of str.

        :Parameters:
          - `bson`: the initial data
        """
        return str.__new__(cls, bson)

    def from_dict(cls, dict, check_keys=False):
        """Create a new BSON object from a python mapping type (like dict).

        Raises TypeError if the argument is not a mapping type, or contains
        keys that are not instance of (str, unicode). Raises InvalidDocument
        if the dictionary cannot be converted to BSON.

        :Parameters:
          - `dict`: mapping type representing a Mongo document
          - `check_keys`: check if keys start with '$' or contain '.',
            raising `pymongo.errors.InvalidName` in either case
        """
        return cls(_dict_to_bson(dict, check_keys))
    from_dict = classmethod(from_dict)

    def to_dict(self):
        """Get the dictionary representation of this data."""
        (son, _) = _bson_to_dict(self)
        return son

########NEW FILE########
__FILENAME__ = code
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for representing JavaScript code to be evaluated by MongoDB.
"""

import types


class Code(str):
    """JavaScript code to be evaluated by MongoDB.

    Raises TypeError if `code` is not an instance of (str, unicode) or
    `scope` is not an instance of dict.

    :Parameters:
      - `code`: string containing JavaScript code to be evaluated
      - `scope` (optional): dictionary representing the scope in which
        `code` should be evaluated - a mapping from identifiers (as
        strings) to values
    """

    def __new__(cls, code, scope=None):
        if not isinstance(code, types.StringTypes):
            raise TypeError("code must be an instance of (str, unicode)")

        if scope is None:
            scope = {}
        if not isinstance(scope, types.DictType):
            raise TypeError("scope must be an instance of dict")

        self = str.__new__(cls, code)
        self.__scope = scope
        return self

    def scope(self):
        """Scope dictionary for this instance.
        """
        return self.__scope
    scope = property(scope)

    def __repr__(self):
        return "Code(%s, %r)" % (str.__repr__(self), self.__scope)

########NEW FILE########
__FILENAME__ = collection
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Collection level utilities for Mongo."""

import types
import warnings
import struct

import helpers
import message
from objectid import ObjectId
from cursor import Cursor
from son import SON
from errors import InvalidName, OperationFailure
from code import Code

_ZERO = "\x00\x00\x00\x00"


class Collection(object):
    """A Mongo collection.
    """

    def __init__(self, database, name, options=None):
        """Get / create a Mongo collection.

        Raises TypeError if name is not an instance of (str, unicode). Raises
        InvalidName if name is not a valid collection name. Raises TypeError if
        options is not an instance of dict. If options is non-empty a create
        command will be sent to the database. Otherwise the collection will be
        created implicitly on first use.

        :Parameters:
          - `database`: the database to get a collection from
          - `name`: the name of the collection to get
          - `options`: dictionary of collection options.
            see `pymongo.database.Database.create_collection` for details.
        """
        if not isinstance(name, types.StringTypes):
            raise TypeError("name must be an instance of (str, unicode)")

        if not isinstance(options, (types.DictType, types.NoneType)):
            raise TypeError("options must be an instance of dict")

        if not name or ".." in name:
            raise InvalidName("collection names cannot be empty")
        if "$" in name and not (name.startswith("oplog.$main") or
                                name.startswith("$cmd")):
            raise InvalidName("collection names must not "
                              "contain '$': %r" % name)
        if name[0] == "." or name[-1] == ".":
            raise InvalidName("collecion names must not start "
                              "or end with '.': %r" % name)

        self.__database = database
        self.__collection_name = unicode(name)
        if options is not None:
            self.__create(options)

    def __create(self, options):
        """Sends a create command with the given options.
        """

        # Send size as a float, not an int/long. BSON can only handle 32-bit
        # ints which conflicts w/ max collection size of 10000000000.
        if "size" in options:
            options["size"] = float(options["size"])

        command = SON({"create": self.__collection_name})
        command.update(options)

        self.__database._command(command)

    def __getattr__(self, name):
        """Get a sub-collection of this collection by name.

        Raises InvalidName if an invalid collection name is used.

        :Parameters:
          - `name`: the name of the collection to get
        """
        return Collection(self.__database, u"%s.%s" % (self.__collection_name,
                                                       name))

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __repr__(self):
        return "Collection(%r, %r)" % (self.__database, self.__collection_name)

    def __cmp__(self, other):
        if isinstance(other, Collection):
            return cmp((self.__database, self.__collection_name),
                       (other.__database, other.__collection_name))
        return NotImplemented

    def full_name(self):
        """Get the full name of this collection.

        The full name is of the form database_name.collection_name.
        """
        return u"%s.%s" % (self.__database.name(), self.__collection_name)

    def name(self):
        """Get the name of this collection.
        """
        return self.__collection_name

    def database(self):
        """Get the database that this collection is a part of.
        """
        return self.__database

    def save(self, to_save, manipulate=True, safe=False):
        """Save a document in this collection.

        If `to_save` already has an '_id' then an update (upsert) operation
        is performed and any existing document with that _id is overwritten.
        Otherwise an '_id' will be added to `to_save` and an insert operation
        is performed. Returns the _id of the saved document.

        Raises TypeError if to_save is not an instance of dict. If `safe`
        is True then the save will be checked for errors, raising
        OperationFailure if one occurred. Safe inserts wait for a
        response from the database, while normal inserts do not. Returns the
        _id of the saved document.

        :Parameters:
          - `to_save`: the SON object to be saved
          - `manipulate` (optional): manipulate the SON object before saving it
          - `safe` (optional): check that the save succeeded?
        """
        if not isinstance(to_save, types.DictType):
            raise TypeError("cannot save object of type %s" % type(to_save))

        if "_id" not in to_save:
            return self.insert(to_save, manipulate, safe)
        else:
            self.update({"_id": to_save["_id"]}, to_save, True,
                        manipulate, safe)
            return to_save.get("_id", None)

    def insert(self, doc_or_docs,
               manipulate=True, safe=False, check_keys=True):
        """Insert a document(s) into this collection.

        If manipulate is set the document(s) are manipulated using any
        SONManipulators that have been added to this database. Returns the _id
        of the inserted document or a list of _ids of the inserted documents.
        If the document(s) does not already contain an '_id' one will be added.
        If `safe` is True then the insert will be checked for errors, raising
        OperationFailure if one occurred. Safe inserts wait for a response from
        the database, while normal inserts do not.

        :Parameters:
          - `doc_or_docs`: a SON object or list of SON objects to be inserted
          - `manipulate` (optional): manipulate the documents before inserting?
          - `safe` (optional): check that the insert succeeded?
          - `check_keys` (optional): check if keys start with '$' or
            contain '.', raising `pymongo.errors.InvalidName` in either case
        """
        docs = doc_or_docs
        if isinstance(docs, types.DictType):
            docs = [docs]

        if manipulate:
            docs = [self.__database._fix_incoming(doc, self) for doc in docs]

        self.__database.connection()._send_message(
            message.insert(self.full_name(), docs, check_keys, safe), safe)

        ids = [doc.get("_id", None) for doc in docs]
        return len(ids) == 1 and ids[0] or ids

    def update(self, spec, document,
               upsert=False, manipulate=False, safe=False, multi=False):
        """Update a document(s) in this collection.

        Raises :class:`TypeError` if either `spec` or `document` is not an
        instance of ``dict`` or `upsert` is not an instance of ``bool``. If
        `safe` is ``True`` then the update will be checked for errors, raising
        :class:`~pymongo.errors.OperationFailure` if one occurred. Safe inserts
        wait for a response from the database, while normal inserts do not.

        There are many useful `update modifiers`_ which can be used when
        performing updates. For example, here we use the ``"$set"`` modifier to
        modify some fields in a matching document::

          >>> db.test.insert({"x": "y", "a": "b"})
          ObjectId('...')
          >>> list(db.test.find())
          [{u'a': u'b', u'x': u'y', u'_id': ObjectId('...')}]
          >>> db.test.update({"x": "y"}, {"$set": {"a": "c"}})
          >>> list(db.test.find())
          [{u'a': u'c', u'x': u'y', u'_id': ObjectId('...')}]

        :Parameters:
          - `spec`: a ``dict`` or :class:`~pymongo.son.SON` instance specifying
            elements which must be present for a document to be updated
          - `document`: a ``dict`` or :class:`~pymongo.son.SON` instance
            specifying the document to be used for the update or (in the case
            of an upsert) insert - see docs on MongoDB `update modifiers`_
          - `upsert` (optional): perform an upsert operation
          - `manipulate` (optional): manipulate the document before updating?
          - `safe` (optional): check that the update succeeded?
          - `multi` (optional): update all documents that match `spec`, rather
            than just the first matching document. The default value for
            `multi` is currently ``False``, but this might eventually change to
            ``True``. It is recommended that you specify this argument
            explicitly for all update operations in order to prepare your code
            for that change.

        .. versionadded:: 1.1.1
           The `multi` parameter.

        .. _update modifiers: http://www.mongodb.org/display/DOCS/Updating
        """
        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(document, types.DictType):
            raise TypeError("document must be an instance of dict")
        if not isinstance(upsert, types.BooleanType):
            raise TypeError("upsert must be an instance of bool")

        if upsert and manipulate:
            document = self.__database._fix_incoming(document, self)

        self.__database.connection()._send_message(
            message.update(self.full_name(), upsert, multi,
                           spec, document, safe), safe)

    def remove(self, spec_or_object_id=None, safe=False):
        """Remove a document(s) from this collection.

        .. warning:: Calls to :meth:`remove` should be performed with
           care, as removed data cannot be restored.

        Raises :class:`~pymongo.errors.TypeError` if
        `spec_or_object_id` is not an instance of (``dict``,
        :class:`~pymongo.objectid.ObjectId`). If `safe` is ``True``
        then the remove operation will be checked for errors, raising
        :class:`~pymongo.errors.OperationFailure` if one
        occurred. Safe removes wait for a response from the database,
        while normal removes do not.

        If no `spec_or_object_id` is given all documents in this
        collection will be removed. This is not equivalent to calling
        :meth:`~pymongo.database.Database.drop_collection`, however, as
        indexes will not be removed.

        :Parameters:
          - `spec_or_object_id` (optional): a ``dict`` or
            :class:`~pymongo.son.SON` instance specifying which documents
            should be removed; or an instance of
            :class:`~pymongo.objectid.ObjectId` specifying the value of the
            ``_id`` field for the document to be removed
          - `safe` (optional): check that the remove succeeded?

        .. versionchanged:: 1.1.2+
           The `spec_or_object_id` parameter is now optional. If it is
           not specified *all* documents in the collection will be
           removed.
        """
        spec = spec_or_object_id
        if spec is None:
            spec = {}
        if isinstance(spec, ObjectId):
            spec = {"_id": spec}

        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict, not %s" %
                            type(spec))

        self.__database.connection()._send_message(
            message.delete(self.full_name(), spec, safe), safe)

    def find_one(self, spec_or_object_id=None, fields=None, slave_okay=None,
                 _sock=None, _must_use_master=False):
        """Get a single object from the database.

        Raises TypeError if the argument is of an improper type. Returns a
        single SON object, or None if no result is found.

        :Parameters:
          - `spec_or_object_id` (optional): a SON object specifying elements
            which must be present for a document to be returned OR an instance
            of ObjectId to be used as the value for an _id query
          - `fields` (optional): a list of field names that should be included
            in the returned document ("_id" will always be included)
          - `slave_okay` (optional): DEPRECATED this option is deprecated and
            will be removed - see the slave_okay parameter to
            `pymongo.Connection.__init__`.
        """
        spec = spec_or_object_id
        if spec is None:
            spec = SON()
        if isinstance(spec, ObjectId):
            spec = SON({"_id": spec})

        for result in self.find(spec, limit=-1, fields=fields,
                                slave_okay=slave_okay, _sock=_sock,
                                _must_use_master=_must_use_master):
            return result
        return None

    def _fields_list_to_dict(self, fields):
        """Takes a list of field names and returns a matching dictionary.

        ["a", "b"] becomes {"a": 1, "b": 1}

        and

        ["a.b.c", "d", "a.c"] becomes {"a.b.c": 1, "d": 1, "a.c": 1}
        """
        as_dict = {}
        for field in fields:
            if not isinstance(field, types.StringTypes):
                raise TypeError("fields must be a list of key names as "
                                "(string, unicode)")
            as_dict[field] = 1
        return as_dict

    def find(self, spec=None, fields=None, skip=0, limit=0,
             slave_okay=None, timeout=True, snapshot=False, tailable=False,
             _sock=None, _must_use_master=False):
        """Query the database.

        The `spec` argument is a prototype document that all results must
        match. For example:

        >>> db.test.find({"hello": "world"})

        only matches documents that have a key "hello" with value "world".
        Matches can have other keys *in addition* to "hello". The `fields`
        argument is used to specify a subset of fields that should be included
        in the result documents. By limiting results to a certain subset of
        fields you can cut down on network traffic and decoding time.

        Raises TypeError if any of the arguments are of improper type. Returns
        an instance of Cursor corresponding to this query.

        :Parameters:
          - `spec` (optional): a SON object specifying elements which must be
            present for a document to be included in the result set
          - `fields` (optional): a list of field names that should be returned
            in the result set ("_id" will always be included)
          - `skip` (optional): the number of documents to omit (from the start
            of the result set) when returning the results
          - `limit` (optional): the maximum number of results to return
          - `slave_okay` (optional): DEPRECATED this option is deprecated and
            will be removed - see the slave_okay parameter to
            `pymongo.Connection.__init__`.
          - `timeout` (optional): if True, any returned cursor will be subject
            to the normal timeout behavior of the mongod process. Otherwise,
            the returned cursor will never timeout at the server. Care should
            be taken to ensure that cursors with timeout turned off are
            properly closed.
          - `snapshot` (optional): if True, snapshot mode will be used for this
            query. Snapshot mode assures no duplicates are returned, or objects
            missed, which were present at both the start and end of the query's
            execution. For details, see the `snapshot documentation
            <http://www.mongodb.org/display/DOCS/How+to+do+Snapshotting+in+the+Mongo+Database>`_.
          - `tailable` (optional): the result of this find call will be a
            tailable cursor - tailable cursors aren't closed when the last data
            is retrieved but are kept open and the cursors location marks the
            final document's position. if more data is received iteration of
            the cursor will continue from the last document received. For
            details, see the `tailable cursor documentation
            <http://www.mongodb.org/display/DOCS/Tailable+Cursors>`_.
        """
        if spec is None:
            spec = SON()
        if slave_okay is None:
            slave_okay = self.__database.connection().slave_okay
        else:
            warnings.warn("The slave_okay option to find and find_one is "
                          "deprecated. Please set slave_okay on the Connection "
                          "itself.",
                          DeprecationWarning)

        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(fields, (types.ListType, types.NoneType)):
            raise TypeError("fields must be an instance of list")
        if not isinstance(skip, types.IntType):
            raise TypeError("skip must be an instance of int")
        if not isinstance(limit, types.IntType):
            raise TypeError("limit must be an instance of int")
        if not isinstance(slave_okay, types.BooleanType):
            raise TypeError("slave_okay must be an instance of bool")
        if not isinstance(timeout, types.BooleanType):
            raise TypeError("timeout must be an instance of bool")
        if not isinstance(snapshot, types.BooleanType):
            raise TypeError("snapshot must be an instance of bool")
        if not isinstance(tailable, types.BooleanType):
            raise TypeError("tailable must be an instance of bool")

        if fields is not None:
            if not fields:
                fields = ["_id"]
            fields = self._fields_list_to_dict(fields)

        return Cursor(self, spec, fields, skip, limit, slave_okay, timeout,
                      tailable, snapshot, _sock=_sock,
                      _must_use_master=_must_use_master)

    def count(self):
        """Get the number of documents in this collection.

        To get the number of documents matching a specific query use
        :meth:`pymongo.cursor.Cursor.count`.
        """
        return self.find().count()

    def _gen_index_name(self, keys):
        """Generate an index name from the set of fields it is over.
        """
        return u"_".join([u"%s_%s" % item for item in keys])

    def create_index(self, key_or_list, direction=None, unique=False, ttl=300):
        """Creates an index on this collection.

        Takes either a single key or a list of (key, direction) pairs.
        The key(s) must be an instance of ``(str, unicode)``, and the
        directions must be one of (:data:`~pymongo.ASCENDING`,
        :data:`~pymongo.DESCENDING`). Returns the name of the created
        index.

        :Parameters:
          - `key_or_list`: a single key or a list of (key, direction) pairs
            specifying the index to create
          - `direction` (optional): DEPRECATED this option will be removed
          - `unique` (optional): should this index guarantee uniqueness?
          - `ttl` (optional): time window (in seconds) during which this index
            will be recognized by subsequent calls to :meth:`ensure_index` -
            see documentation for :meth:`ensure_index` for details
        """
        if not isinstance(key_or_list, (str, unicode, list)):
            raise TypeError("key_or_list must either be a single key or a list of (key, direction) pairs")

        if direction is not None:
            warnings.warn("specifying a direction for a single key index is "
                          "deprecated and will be removed. there is no need "
                          "for a direction on a single key index",
                          DeprecationWarning)

        to_save = SON()
        keys = helpers._index_list(key_or_list)
        name = self._gen_index_name(keys)
        to_save["name"] = name
        to_save["ns"] = self.full_name()
        to_save["key"] = helpers._index_document(keys)
        to_save["unique"] = unique

        self.database().connection()._cache_index(self.__database.name(),
                                                  self.name(),
                                                  name, ttl)

        self.database().system.indexes.insert(to_save, manipulate=False,
                                              check_keys=False)
        return to_save["name"]

    def ensure_index(self, key_or_list, direction=None, unique=False, ttl=300):
        """Ensures that an index exists on this collection.

        Takes either a single key or a list of (key, direction)
        pairs.  The key(s) must be an instance of ``(str, unicode)``,
        and the direction(s) must be one of
        (:data:`~pymongo.ASCENDING`, :data:`~pymongo.DESCENDING`).

        Unlike :meth:`create_index`, which attempts to create an index
        unconditionally, :meth:`ensure_index` takes advantage of some
        caching within the driver such that it only attempts to create
        indexes that might not already exist. When an index is created
        (or ensured) by PyMongo it is "remembered" for `ttl`
        seconds. Repeated calls to :meth:`ensure_index` within that
        time limit will be lightweight - they will not attempt to
        actually create the index.

        Care must be taken when the database is being accessed through
        multiple connections at once. If an index is created using
        PyMongo and then deleted using another connection any call to
        :meth:`ensure_index` within the cache window will fail to
        re-create the missing index.

        Returns the name of the created index if an index is actually
        created. Returns ``None`` if the index already exists.

        :Parameters:
          - `key_or_list`: a single key or a list of (key, direction) pairs
            specifying the index to ensure
          - `direction` (optional): DEPRECATED this option will be removed
          - `unique` (optional): should this index guarantee uniqueness?
          - `ttl` (optional): time window (in seconds) during which this index
            will be recognized by subsequent calls to :meth:`ensure_index`
        """
        if not isinstance(key_or_list, (str, unicode, list)):
            raise TypeError("key_or_list must either be a single key or a list of (key, direction) pairs")

        if direction is not None:
            warnings.warn("specifying a direction for a single key index is "
                          "deprecated and will be removed. there is no need "
                          "for a direction on a single key index",
                          DeprecationWarning)

        keys = helpers._index_list(key_or_list)
        name = self._gen_index_name(keys)
        if self.database().connection()._cache_index(self.__database.name(),
                                                     self.name(),
                                                     name, ttl):
            return self.create_index(key_or_list, unique=unique, ttl=ttl)
        return None

    def drop_indexes(self):
        """Drops all indexes on this collection.

        Can be used on non-existant collections or collections with no indexes.
        Raises OperationFailure on an error.
        """
        self.database().connection()._purge_index(self.database().name(),
                                                  self.name())
        self.drop_index(u"*")

    def drop_index(self, index_or_name):
        """Drops the specified index on this collection.

        Can be used on non-existant collections or collections with no indexes.
        Raises OperationFailure on an error. `index_or_name` can be either an
        index name (as returned by `create_index`), or an index specifier (as
        passed to `create_index`). An index specifier should be a list of (key,
        direction) pairs. Raises TypeError if index is not an instance of (str,
        unicode, list).

        :Parameters:
          - `index_or_name`: index (or name of index) to drop
        """
        name = index_or_name
        if isinstance(index_or_name, types.ListType):
            name = self._gen_index_name(index_or_name)

        if not isinstance(name, types.StringTypes):
            raise TypeError("index_or_name must be an index name or list")

        self.database().connection()._purge_index(self.database().name(),
                                                  self.name(), name)
        self.__database._command(SON([("deleteIndexes",
                                       self.__collection_name),
                                      ("index", name)]),
                                 ["ns not found"])

    def index_information(self):
        """Get information on this collection's indexes.

        Returns a dictionary where the keys are index names (as returned by
        create_index()) and the values are lists of (key, direction) pairs
        specifying the index (as passed to create_index()).
        """
        raw = self.__database.system.indexes.find({"ns": self.full_name()})
        info = {}
        for index in raw:
            info[index["name"]] = index["key"].items()
        return info

    def options(self):
        """Get the options set on this collection.

        Returns a dictionary of options and their values - see
        `pymongo.database.Database.create_collection` for more information on
        the options dictionary. Returns an empty dictionary if the collection
        has not been created yet.
        """
        result = self.__database.system.namespaces.find_one(
            {"name": self.full_name()})

        if not result:
            return {}

        options = result.get("options", {})
        if "create" in options:
            del options["create"]

        return options

    # TODO send all groups as commands once 1.2 is out
    #
    # Waiting on this because group command support for CodeWScope
    # wasn't added until 1.1
    def group(self, keys, condition, initial, reduce, finalize=None,
              command=False):
        """Perform a query similar to an SQL group by operation.

        Returns an array of grouped items.

        :Parameters:
          - `keys`: list of fields to group by
          - `condition`: specification of rows to be considered (as a `find`
            query specification)
          - `initial`: initial value of the aggregation counter object
          - `reduce`: aggregation function as a JavaScript string
          - `finalize`: function to be called on each object in output list.
          - `command` (optional): if True, run the group as a command instead
            of in an eval - it is likely that this option will eventually be
            deprecated and all groups will be run as commands. Please only use
            as a keyword argument, not as a positional argument.
        """

        #for now support people passing command in its old position
        if finalize in (True, False):
            command = finalize
            finalize = None
            warnings.warn("Please only pass 'command' as a keyword argument."
                         ,DeprecationWarning)

        if command:
            if not isinstance(reduce, Code):
                reduce = Code(reduce)
            group = {"ns": self.__collection_name,
                    "$reduce": reduce,
                    "key": self._fields_list_to_dict(keys),
                    "cond": condition,
                    "initial": initial}
            if finalize is not None:
                if not isinstance(finalize, Code):
                    finalize = Code(finalize)
                group["finalize"] = finalize
            return self.__database._command({"group":group})["retval"]

        scope = {}
        if isinstance(reduce, Code):
            scope = reduce.scope
        scope.update({"ns": self.__collection_name,
                      "keys": keys,
                      "condition": condition,
                      "initial": initial})

        group_function = """function () {
    var c = db[ns].find(condition);
    var map = new Map();
    var reduce_function = %s;
    var finalize_function = %s; //function or null
    while (c.hasNext()) {
        var obj = c.next();

        var key = {};
        for (var i = 0; i < keys.length; i++) {
            var k = keys[i];
            key[k] = obj[k];
        }

        var aggObj = map.get(key);
        if (aggObj == null) {
            var newObj = Object.extend({}, key);
            aggObj = Object.extend(newObj, initial);
            map.put(key, aggObj);
        }
        reduce_function(obj, aggObj);
    }

    out = map.values();
    if (finalize_function !== null){
        for (var i=0; i < out.length; i++){
            var ret = finalize_function(out[i]);
            if (ret !== undefined)
                out[i] = ret;
        }
    }

    return {"result": out};
}""" % (reduce, (finalize or 'null'));
        return self.__database.eval(Code(group_function, scope))["result"]

    def rename(self, new_name):
        """Rename this collection.

        If operating in auth mode, client must be authorized as an admin to
        perform this operation. Raises TypeError if new_name is not an instance
        of (str, unicode). Raises InvalidName if new_name is not a valid
        collection name.

        :Parameters:
          - `new_name`: new name for this collection
        """
        if not isinstance(new_name, types.StringTypes):
            raise TypeError("new_name must be an instance of (str, unicode)")

        if not new_name or ".." in new_name:
            raise InvalidName("collection names cannot be empty")
        if "$" in new_name:
            raise InvalidName("collection names must not contain '$'")
        if new_name[0] == "." or new_name[-1] == ".":
            raise InvalidName("collecion names must not start or end with '.'")

        rename_command = SON([("renameCollection", self.full_name()),
                              ("to", "%s.%s" % (self.__database.name(),
                                                new_name))])

        self.__database.connection().admin._command(rename_command)

    def distinct(self, key):
        """Get a list of distinct values for `key` among all documents in this
        collection.

        Raises :class:`TypeError` if `key` is not an instance of
        ``(str, unicode)``.

        To get the distinct values for a key in the result set of a query
        use :meth:`pymongo.cursor.Cursor.distinct`.

        :Parameters:
          - `key`: name of key for which we want to get the distinct values

        .. note:: Requires server version **>= 1.1.0**

        .. versionadded:: 1.1.1
        """
        return self.find().distinct(key)

    def map_reduce(self, map, reduce, full_response=False, **kwargs):
        """Perform a map/reduce operation on this collection.

        If `full_response` is ``False`` (default) returns a
        :class:`~pymongo.collection.Collection` instance containing
        the results of the operation. Otherwise, returns the full
        response from the server to the `map reduce command`_.

        :Parameters:
          - `map`: map function (as a JavaScript string)
          - `reduce`: reduce function (as a JavaScript string)
          - `full_response` (optional): if ``True``, return full response to
            this command - otherwise just return the result collection
          - `**kwargs` (optional): additional arguments to the
            `map reduce command`_ may be passed as keyword arguments to this
            helper method, e.g.::

            >>> db.test.map_reduce(map, reduce, limit=2)

        .. note:: Requires server version **>= 1.1.1**

        .. seealso:: :doc:`/examples/map_reduce`

        .. versionadded:: 1.1.2+

        .. _map reduce command: http://www.mongodb.org/display/DOCS/MapReduce
        """
        command = SON([("mapreduce", self.__collection_name),
                       ("map", map), ("reduce", reduce)])
        command.update(**kwargs)

        response = self.__database._command(command)
        if full_response:
            return response
        return self.__database[response["result"]]

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'Collection' object is not iterable")

    def __call__(self, *args, **kwargs):
        """This is only here so that some API misusages are easier to debug.
        """
        if "." not in self.__collection_name:
            raise TypeError("'Collection' object is not callable. If you "
                            "meant to call the '%s' method on a 'Database' "
                            "object it is failing because no such method "
                            "exists." %
                            self.__collection_name)
        raise TypeError("'Collection' object is not callable. If you meant to "
                        "call the '%s' method on a 'Collection' object it is "
                        "failing because no such method exists." %
                        self.__collection_name.split(".")[-1])

########NEW FILE########
__FILENAME__ = connection
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for connecting to MongoDB.

To connect to a single instance of MongoDB use :class:`Connection`. To connect
to a replica pair use :meth:`~Connection.paired`.

.. seealso:: Module :mod:`~pymongo.master_slave_connection` for connecting to
   master-slave clusters.

To get a :class:`~pymongo.database.Database` instance from a
:class:`Connection` use either dictionary-style or attribute-style access::

  >>> from pymongo import Connection
  >>> c = Connection()
  >>> c.test_database
  Database(Connection('localhost', 27017), u'test_database')
  >>> c['test-database']
  Database(Connection('localhost', 27017), u'test-database')
"""

import sys
import socket
import struct
import types
import logging
import threading
import random
import errno
import datetime

from errors import ConnectionFailure, ConfigurationError, AutoReconnect
from errors import OperationFailure
from database import Database
from cursor_manager import CursorManager
from thread_util import TimeoutableLock
import bson
import message
import helpers

_logger = logging.getLogger("pymongo.connection")
_logger.addHandler(logging.StreamHandler())
_logger.setLevel(logging.INFO)

_CONNECT_TIMEOUT = 20.0


class Connection(object): # TODO support auth for pooling
    """Connection to MongoDB.
    """

    HOST = "localhost"
    PORT = 27017
    POOL_SIZE = 1
    AUTO_START_REQUEST = True
    TIMEOUT = 1.0

    def __init__(self, host=None, port=None, pool_size=None,
                 auto_start_request=None, timeout=None, slave_okay=False,
                 network_timeout=None, _connect=True):
        """Create a new connection to a single MongoDB instance at *host:port*.

        The resultant connection object has connection-pooling built in. It
        also performs auto-reconnection when necessary. If an operation fails
        because of a connection error,
        :class:`~pymongo.errors.ConnectionFailure` is raised. If
        auto-reconnection will be performed,
        :class:`~pymongo.errors.AutoReconnect` will be raised. Application code
        should handle this exception (recognizing that the operation failed)
        and then continue to execute.

        Raises :class:`TypeError` if host is not an instance of string or port
        is not an instance of ``int``. Raises
        :class:`~pymongo.errors.ConnectionFailure` if the connection cannot be
        made. Raises :class:`TypeError` if `pool_size` is not an instance of
        ``int``. Raises :class:`ValueError` if `pool_size` is not greater than
        or equal to one.

        .. warning:: Connection pooling is not compatible with auth (yet).
           Please do not set the `pool_size` parameter to anything other than 1
           if auth is in use.

        :Parameters:
          - `host` (optional): hostname or IPv4 address of the instance to
            connect to
          - `port` (optional): port number on which to connect
          - `pool_size` (optional): maximum size of the built in
            connection-pool
          - `auto_start_request` (optional): automatically start a request
            on every operation - see :meth:`start_request`
          - `slave_okay` (optional): is it okay to connect directly to and
            perform queries on a slave instance
          - `timeout` (optional): max time to wait when attempting to acquire a
            connection from the connection pool before raising an exception -
            can be set to -1 to wait indefinitely
          - `network_timeout` (optional): timeout (in seconds) to use for socket
            operations - default is no timeout
        """
        if host is None:
            host = self.HOST
        if port is None:
            port = self.PORT
        if pool_size is None:
            pool_size = self.POOL_SIZE
        if auto_start_request is None:
            auto_start_request = self.AUTO_START_REQUEST
        if timeout is None:
            timeout = self.TIMEOUT
        if timeout == -1:
            timeout = None

        if not isinstance(host, types.StringTypes):
            raise TypeError("host must be an instance of (str, unicode)")
        if not isinstance(port, types.IntType):
            raise TypeError("port must be an instance of int")
        if not isinstance(pool_size, types.IntType):
            raise TypeError("pool_size must be an instance of int")
        if pool_size <= 0:
            raise ValueError("pool_size must be positive")

        self.__host = None
        self.__port = None

        self.__nodes = [(host, port)]
        self.__slave_okay = slave_okay

        self.__cursor_manager = CursorManager(self)

        self.__pool_size = pool_size
        self.__auto_start_request = auto_start_request
        # map from threads to sockets
        self.__thread_map = {}
        # count of how many threads are mapped to each socket
        self.__thread_count = [0 for _ in range(self.__pool_size)]
        self.__acquire_timeout = timeout
        self.__locks = [TimeoutableLock() for _ in range(self.__pool_size)]
        self.__sockets = [None for _ in range(self.__pool_size)]
        self.__currently_resetting = False

        self.__network_timeout = network_timeout

        # cache of existing indexes used by ensure_index ops
        self.__index_cache = {}

        if _connect:
            self.__find_master()

    def __pair_with(self, host, port):
        """Pair this connection with a Mongo instance running on host:port.

        Raises TypeError if host is not an instance of string or port is not an
        instance of int. Raises ConnectionFailure if the connection cannot be
        made.

        :Parameters:
          - `host`: the hostname or IPv4 address of the instance to
            pair with
          - `port`: the port number on which to connect
        """
        if not isinstance(host, types.StringType):
            raise TypeError("host must be an instance of str")
        if not isinstance(port, types.IntType):
            raise TypeError("port must be an instance of int")
        self.__nodes.append((host, port))

        self.__find_master()

    def paired(cls, left, right=None,
               pool_size=None, auto_start_request=None):
        """Open a new paired connection to Mongo.

        Raises :class:`TypeError` if either `left` or `right` is not a tuple of
        the form ``(host, port)``. Raises :class:`~pymongo.ConnectionFailure`
        if the connection cannot be made.

        :Parameters:
          - `left`: ``(host, port)`` pair for the left MongoDB instance
          - `right` (optional): ``(host, port)`` pair for the right MongoDB
            instance
          - `pool_size` (optional): same as argument to :class:`Connection`
          - `auto_start_request` (optional): same as argument to
            :class:`Connection`
        """
        if right is None:
            right = (cls.HOST, cls.PORT)
        if pool_size is None:
            pool_size = cls.POOL_SIZE
        if auto_start_request is None:
            auto_start_request = cls.AUTO_START_REQUEST

        connection = cls(left[0], left[1], pool_size, auto_start_request,
                         _connect=False)
        connection.__pair_with(*right)
        return connection
    paired = classmethod(paired)

    def __master(self, sock):
        """Get the hostname and port of the master Mongo instance.

        Return a tuple (host, port).
        """
        result = self["admin"]._command({"ismaster": 1}, sock=sock)

        if result["ismaster"] == 1:
            return True
        else:
            if "remote" not in result:
                return False

            strings = result["remote"].split(":", 1)
            if len(strings) == 1:
                port = self.PORT
            else:
                port = int(strings[1])
            return (strings[0], port)

    def _cache_index(self, database, collection, index, ttl):
        """Add an index to the index cache for ensure_index operations.

        Return ``True`` if the index has been newly cached or if the index had
        expired and is being re-cached.

        Return ``False`` if the index exists and is valid.
        """
        now = datetime.datetime.utcnow()
        expire = datetime.timedelta(seconds=ttl) + now

        if database not in self.__index_cache:
            self.__index_cache[database] = {}
            self.__index_cache[database][collection] = {}
            self.__index_cache[database][collection][index] = expire
            return True

        if collection not in self.__index_cache[database]:
            self.__index_cache[database][collection] = {}
            self.__index_cache[database][collection][index] = expire
            return True

        if index in self.__index_cache[database][collection]:
            if now < self.__index_cache[database][collection][index]:
                return False

        self.__index_cache[database][collection][index] = expire
        return True

    def _purge_index(self, database_name,
                     collection_name=None, index_name=None):
        """Purge an index from the index cache.

        If `index_name` is None purge an entire collection.

        If `collection_name` is None purge an entire database.
        """
        if not database_name in self.__index_cache:
            return

        if collection_name is None:
            del self.__index_cache[database_name]
            return

        if not collection_name in self.__index_cache[database_name]:
            return

        if index_name is None:
            del self.__index_cache[database_name][collection_name]
            return

        if index_name in self.__index_cache[database_name][collection_name]:
            del self.__index_cache[database_name][collection_name][index_name]

    # TODO these really should be properties... Could be ugly to make that
    # backwards compatible though...
    def host(self):
        """Get the connection's current host.
        """
        return self.__host

    def port(self):
        """Get the connection's current port.
        """
        return self.__port

    def slave_okay(self):
        """Is it okay for this connection to connect directly to a slave?
        """
        return self.__slave_okay
    slave_okay = property(slave_okay)

    def __find_master(self):
        """Create a new socket and use it to figure out who the master is.

        Sets __host and __port so that `host()` and `port()` will return the
        address of the master.
        """
        _logger.debug("finding master")
        self.__host = None
        self.__port = None
        sock = None
        for (host, port) in self.__nodes:
            _logger.debug("trying %r:%r" % (host, port))
            try:
                try:
                    sock = socket.socket()
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.settimeout(_CONNECT_TIMEOUT)
                    sock.connect((host, port))
                    sock.settimeout(self.__network_timeout)
                    try:
                        master = self.__master(sock)
                    except ConnectionFailure, e:
                        raise AutoReconnect(str(e))
                    if master is True:
                        self.__host = host
                        self.__port = port
                        _logger.debug("found master")
                        return
                    if not master:
                        if self.__slave_okay:
                            self.__host = host
                            self.__port = port
                            _logger.debug("connecting to slave (slave_okay mode)")
                            return

                        raise ConfigurationError("trying to connect directly to"
                                                 " slave %s:%r - must specify "
                                                 "slave_okay to connect to "
                                                 "slaves" % (host, port))
                    if master not in self.__nodes:
                        raise ConfigurationError(
                            "%r claims master is %r, "
                            "but that's not configured" %
                            ((host, port), master))
                    _logger.debug("not master, master is (%r, %r)" % master)
                except socket.error, e:
                    exctype, value = sys.exc_info()[:2]
                    _logger.debug("could not connect, got: %s %s" %
                                  (exctype, value))
                    if len(self.__nodes) == 1:
                        raise ConnectionFailure(e)
                    continue
            finally:
                if sock is not None:
                    sock.close()
        raise AutoReconnect("could not find master")

    def __connect(self, socket_number):
        """(Re-)connect to Mongo.

        Connect to the master if this is a paired connection.
        """
        if self.host() is None or self.port() is None:
            self.__find_master()
        _logger.debug("connecting socket %s..." % socket_number)

        assert self.__sockets[socket_number] is None

        try:
            self.__sockets[socket_number] = socket.socket()
            self.__sockets[socket_number].setsockopt(socket.IPPROTO_TCP,
                                                     socket.TCP_NODELAY, 1)
            sock = self.__sockets[socket_number]
            sock.settimeout(_CONNECT_TIMEOUT)
            sock.connect((self.host(), self.port()))
            sock.settimeout(self.__network_timeout)
            _logger.debug("connected")
            return
        except socket.error:
            raise ConnectionFailure("could not connect to %r" % self.__nodes)

    def _reset(self):
        """Reset everything and start connecting again.

        Closes all open sockets and resets them to None. Re-finds the master.

        This should be done in case of a connection failure or a "not master"
        error.
        """
        if self.__currently_resetting:
            return
        self.__currently_resetting = True

        for i in range(self.__pool_size):
            # prevent all operations during the reset
            if not self.__locks[i].acquire(timeout=self.__acquire_timeout):
                raise ConnectionFailure("timed out before acquiring "
                                        "a connection from the pool")
            if self.__sockets[i] is not None:
                self.__sockets[i].close()
                self.__sockets[i] = None

        try:
            self.__find_master()
        finally:
            self.__currently_resetting = False
            for i in range(self.__pool_size):
                self.__locks[i].release()

    def set_cursor_manager(self, manager_class):
        """Set this connection's cursor manager.

        Raises :class:`TypeError` if `manager_class` is not a subclass of
        :class:`~pymongo.cursor_manager.CursorManager`. A cursor manager handles
        closing cursors. Different managers can implement different policies in
        terms of when to actually kill a cursor that has been closed.

        :Parameters:
          - `manager_class`: cursor manager to use
        """
        manager = manager_class(self)
        if not isinstance(manager, CursorManager):
            raise TypeError("manager_class must be a subclass of "
                            "CursorManager")

        self.__cursor_manager = manager

    def __pick_and_acquire_socket(self):
        """Acquire a socket to use for synchronous send and receive operations.
        """
        choices = range(self.__pool_size)
        random.shuffle(choices)
        choices.sort(lambda x, y: cmp(self.__thread_count[x],
                                      self.__thread_count[y]))

        for choice in choices:
            if self.__locks[choice].acquire(False):
                return choice

        if not self.__locks[choices[0]].acquire(timeout=
                                                self.__acquire_timeout):
            raise ConnectionFailure("timed out before acquiring "
                                    "a connection from the pool")
        return choices[0]

    def __get_socket(self):
        thread = threading.currentThread()
        if self.__thread_map.get(thread, -1) >= 0:
            sock = self.__thread_map[thread]
            if not self.__locks[sock].acquire(timeout=self.__acquire_timeout):
                raise ConnectionFailure("timed out before acquiring "
                                        "a connection from the pool")
        else:
            sock = self.__pick_and_acquire_socket()
            if self.__auto_start_request or thread in self.__thread_map:
                self.__thread_map[thread] = sock
                self.__thread_count[sock] += 1

        try:
            if not self.__sockets[sock]:
                self.__connect(sock)
        except ConnectionFailure, e:
            self.__sockets[sock].close()
            self.__sockets[sock] = None
            raise AutoReconnect(str(e))
        return sock

    # TODO use static methods for a bunch of these
    def __send_data_on_socket(self, data, sock):
        """Lowest level send operation.

        Takes data to send as a byte string and a socket instance and
        sends all of the data, raising ConnectionFailure on error.
        """
        total_sent = 0
        while total_sent < len(data):
            try:
                sent = sock.send(data[total_sent:])
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    continue
                raise ConnectionFailure("connection closed, resetting")
            if sent == 0:
                raise ConnectionFailure("connection closed, resetting")
            total_sent += sent

    def __check_response_to_last_error(self, response):
        """Check a response to a lastError message for errors.

        `response` is a byte string representing a response to the message.
        If it represents an error response we raise OperationFailure.
        """
        response = helpers._unpack_response(response)

        assert response["number_returned"] == 1
        error = response["data"][0]

        # TODO unify logic with database.error method
        if error.get("err", 0) is None:
            return
        if error["err"] == "not master":
            self._reset()
        raise OperationFailure(error["err"])

    def _send_message(self, message, with_last_error=False):
        """Say something to Mongo.

        Raises ConnectionFailure if the message cannot be sent. Raises
        OperationFailure if `with_last_error` is ``True`` and the response to
        the getLastError call returns an error.

        :Parameters:
          - `message`: message to send
          - `with_last_error`: check getLastError status after sending the
            message
        """
        sock_number = self.__get_socket()
        sock = self.__sockets[sock_number]
        try:
            try:
                (request_id, data) = message
                self.__send_data_on_socket(data, sock)
                # Safe mode. We pack the message together with a lastError
                # message and send both. We then get the response (to the
                # lastError) and raise OperationFailure if it is an error
                # response.
                if with_last_error:
                    response = self.__receive_message_on_socket(1, request_id, sock)
                    self.__check_response_to_last_error(response)
            except ConnectionFailure, e:
                self.__sockets[sock_number].close()
                self.__sockets[sock_number] = None
                raise AutoReconnect(str(e))
        finally:
            self.__locks[sock_number].release()

    def __receive_data_on_socket(self, length, sock):
        """Lowest level receive operation.

        Takes length to receive and repeatedly calls recv until able to
        return a buffer of that length, raising ConnectionFailure on error.
        """
        message = ""
        while len(message) < length:
            try:
                chunk = sock.recv(length - len(message))
            except socket.error, e:
                raise ConnectionFailure(e)
            if chunk == "":
                raise ConnectionFailure("connection closed")
            message += chunk
        return message

    def __receive_message_on_socket(self, operation, request_id, sock):
        """Receive a message in response to `request_id` on `sock`.

        Returns the response data with the header removed.
        """
        header = self.__receive_data_on_socket(16, sock)
        length = struct.unpack("<i", header[:4])[0]
        assert request_id == struct.unpack("<i", header[8:12])[0], \
            "ids don't match %r %r" % (request_id,
                                       struct.unpack("<i", header[8:12])[0])
        assert operation == struct.unpack("<i", header[12:])[0]

        return self.__receive_data_on_socket(length - 16, sock)

    def __send_and_receive(self, message, sock):
        """Send a message on the given socket and return the response data.
        """
        (request_id, data) = message
        self.__send_data_on_socket(data, sock)
        return self.__receive_message_on_socket(1, request_id, sock)

    __hack_socket_lock = threading.Lock()
    # we just ignore _must_use_master here: it's only relavant for
    # MasterSlaveConnection instances.
    def _send_message_with_response(self, message,
                                    _sock=None, _must_use_master=False):
        """Send a message to Mongo and return the response.

        Sends the given message and returns the response.

        :Parameters:
          - `message`: (request_id, data) pair making up the message to send
        """
        # hack so we can do find_master on a specific socket...
        if _sock:
            self.__hack_socket_lock.acquire()
            try:
                return self.__send_and_receive(message, _sock)
            finally:
                self.__hack_socket_lock.release()

        sock_number = self.__get_socket()
        sock = self.__sockets[sock_number]
        try:
            try:
                return self.__send_and_receive(message, sock)
            except ConnectionFailure, e:
                self.__sockets[sock_number].close()
                self.__sockets[sock_number] = None
                raise AutoReconnect(str(e))
        finally:
            self.__locks[sock_number].release()

    def start_request(self):
        """Start a "request".

        A "request" is a group of operations in which order matters. Examples
        include inserting a document and then performing a query which expects
        that document to have been inserted, or performing an operation and
        then using :meth:`database.Database.error()` to perform error-checking
        on that operation. When a thread performs operations in a "request", the
        connection will perform all operations on the same socket, so Mongo
        will order them correctly.

        This method is only relevant when the current :class:`Connection` has a
        ``pool_size`` greater than one. Otherwise only a single socket will be
        used for *all* operations, so there is no need to group operations into
        requests.

        This method only needs to be used if the ``auto_start_request`` option
        is set to ``False``. If ``auto_start_request`` is ``True``, a request
        will be started (if necessary) on every operation.
        """
        if not self.__auto_start_request:
            self.end_request()
            self.__thread_map[threading.currentThread()] = -1

    def end_request(self):
        """End the current "request", if this thread is in one.

        Judicious use of this method can lead to performance gains when
        connection-pooling is being used. By ending a request when it is safe
        to do so the connection is allowed to pick a new socket from the pool
        for that thread on the next operation. This could prevent an imbalance
        of threads trying to connect on the same socket. Care should be taken,
        however, to make sure that :meth:`end_request` isn't called in the
        middle of a sequence of operations in which ordering is important. This
        could lead to unexpected results.

        :meth:`end_request` is useful even (especially) if
        ``auto_start_request`` is ``True``.

        .. seealso:: :meth:`start_request` for more information on what
           a "request" is and when one should be used.
        """
        thread = threading.currentThread()
        if self.__thread_map.get(thread, -1) >= 0:
            sock_number = self.__thread_map.pop(thread)
            self.__thread_count[sock_number] -= 1

    def __cmp__(self, other):
        if isinstance(other, Connection):
            return cmp((self.__host, self.__port),
                       (other.__host, other.__port))
        return NotImplemented

    def __repr__(self):
        if len(self.__nodes) == 1:
            return "Connection(%r, %r)" % (self.__host, self.__port)
        elif len(self.__nodes) == 2:
            return ("Connection.paired((%r, %r), (%r, %r))" %
                    (self.__nodes[0][0],
                     self.__nodes[0][1],
                     self.__nodes[1][0],
                     self.__nodes[1][1]))

    def __getattr__(self, name):
        """Get a database by name.

        Raises InvalidName if an invalid database name is used.

        :Parameters:
          - `name`: the name of the database to get
        """
        return Database(self, name)

    def __getitem__(self, name):
        """Get a database by name.

        Raises InvalidName if an invalid database name is used.

        :Parameters:
          - `name`: the name of the database to get
        """
        return self.__getattr__(name)

    def close_cursor(self, cursor_id):
        """Close a single database cursor.

        Raises :class:`TypeError` if `cursor_id` is not an instance of ``(int, long)``. What closing the cursor actually means depends on this connection's cursor manager.

        :Parameters:
          - `cursor_id`: id of cursor to close

        .. seealso:: :meth:`set_cursor_manager` and
           the :mod:`~pymongo.cursor_manager` module
        """
        if not isinstance(cursor_id, (types.IntType, types.LongType)):
            raise TypeError("cursor_id must be an instance of (int, long)")

        self.__cursor_manager.close(cursor_id)

    def kill_cursors(self, cursor_ids):
        """Send a kill cursors message with the given ids.

        Raises :class:`TypeError` if `cursor_ids` is not an instance of
        ``list``.

        :Parameters:
          - `cursor_ids`: list of cursor ids to kill
        """
        if not isinstance(cursor_ids, types.ListType):
            raise TypeError("cursor_ids must be a list")
        return self._send_message(message.kill_cursors(cursor_ids))

    def __database_info(self):
        """Get a dictionary of (database_name: size_on_disk).
        """
        result = self["admin"]._command({"listDatabases": 1})
        info = result["databases"]
        return dict([(db["name"], db["sizeOnDisk"]) for db in info])

    def server_info(self):
        """Get information about the MongoDB server we're connected to.
        """
        return self["admin"]._command({"buildinfo": 1})

    def database_names(self):
        """Get a list of the names of all databases on the connected server.
        """
        return self.__database_info().keys()

    def drop_database(self, name_or_database):
        """Drop a database.

        Raises :class:`TypeError` if `name_or_database` is not an instance of
        ``(str, unicode, Database)``

        :Parameters:
          - `name_or_database`: the name of a database to drop, or a
            :class:`~pymongo.database.Database` instance representing the
            database to drop
        """
        name = name_or_database
        if isinstance(name, Database):
            name = name.name()

        if not isinstance(name, types.StringTypes):
            raise TypeError("name_or_database must be an instance of "
                            "(Database, str, unicode)")

        self._purge_index(name)
        self[name]._command({"dropDatabase": 1})

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'Connection' object is not iterable")

########NEW FILE########
__FILENAME__ = cursor
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cursor class to iterate over Mongo query results."""

import types
import struct
import warnings

import helpers
import message
from son import SON
from code import Code
from errors import InvalidOperation, OperationFailure, AutoReconnect

_QUERY_OPTIONS = {
    "tailable_cursor": 2,
    "slave_okay": 4,
    "oplog_replay": 8,
    "no_timeout": 16
}


class Cursor(object):
    """A cursor / iterator over Mongo query results.
    """

    def __init__(self, collection, spec, fields, skip, limit, slave_okay,
                 timeout, tailable, snapshot=False,
                 _sock=None, _must_use_master=False):
        """Create a new cursor.

        Should not be called directly by application developers.
        """
        self.__collection = collection
        self.__spec = spec
        self.__fields = fields
        self.__skip = skip
        self.__limit = limit
        self.__slave_okay = slave_okay
        self.__timeout = timeout
        self.__tailable = tailable
        self.__snapshot = snapshot
        self.__ordering = None
        self.__explain = False
        self.__hint = None
        self.__socket = _sock
        self.__must_use_master = _must_use_master

        self.__data = []
        self.__id = None
        self.__connection_id = None
        self.__retrieved = 0
        self.__killed = False

    def collection(self):
        """Get the collection for this cursor.
        """
        return self.__collection
    collection = property(collection)

    def __del__(self):
        if self.__id and not self.__killed:
            self.__die()

    def rewind(self):
        """Rewind this cursor to it's unevaluated state.

        Reset this cursor if it has been partially or completely evaluated.
        Any options that are present on the cursor will remain in effect.
        Future iterating performed on this cursor will cause new queries to
        be sent to the server, even if the resultant data has already been
        retrieved by this cursor.
        """
        self.__data = []
        self.__id = None
        self.__connection_id = None
        self.__retrieved = 0
        self.__killed = False

        return self

    def clone(self):
        """Get a clone of this cursor.

        Returns a new Cursor instance with options matching those that have
        been set on the current instance. The clone will be completely
        unevaluated, even if the current instance has been partially or
        completely evaluated.
        """
        copy = Cursor(self.__collection, self.__spec, self.__fields,
                      self.__skip, self.__limit, self.__slave_okay,
                      self.__timeout, self.__tailable, self.__snapshot)
        copy.__ordering = self.__ordering
        copy.__explain = self.__explain
        copy.__hint = self.__hint
        copy.__socket = self.__socket
        return copy

    def __die(self):
        """Closes this cursor.
        """
        if self.__id and not self.__killed:
            connection = self.__collection.database().connection()
            if self.__connection_id is not None:
                connection.close_cursor(self.__id, self.__connection_id)
            else:
                connection.close_cursor(self.__id)
        self.__killed = True

    def __query_spec(self):
        """Get the spec to use for a query.
        """
        spec = SON({"query": self.__spec})
        if self.__ordering:
            spec["orderby"] = self.__ordering
        if self.__explain:
            spec["$explain"] = True
        if self.__hint:
            spec["$hint"] = self.__hint
        if self.__snapshot:
            spec["$snapshot"] = True
        return spec

    def __query_options(self):
        """Get the query options string to use for this query.
        """
        options = 0
        if self.__tailable:
            options |= _QUERY_OPTIONS["tailable_cursor"]
        if self.__slave_okay:
            options |= _QUERY_OPTIONS["slave_okay"]
        if not self.__timeout:
            options |= _QUERY_OPTIONS["no_timeout"]
        return options

    def __check_okay_to_chain(self):
        """Check if it is okay to chain more options onto this cursor.
        """
        if self.__retrieved or self.__id is not None:
            raise InvalidOperation("cannot set options after executing query")

    def limit(self, limit):
        """Limits the number of results to be returned by this cursor.

        Raises TypeError if limit is not an instance of int. Raises
        InvalidOperation if this cursor has already been used. The last `limit`
        applied to this cursor takes precedence.

        :Parameters:
          - `limit`: the number of results to return
        """
        if not isinstance(limit, types.IntType):
            raise TypeError("limit must be an int")
        self.__check_okay_to_chain()

        self.__limit = limit
        return self

    def skip(self, skip):
        """Skips the first `skip` results of this cursor.

        Raises TypeError if skip is not an instance of int. Raises
        InvalidOperation if this cursor has already been used. The last `skip`
        applied to this cursor takes precedence.

        :Parameters:
          - `skip`: the number of results to skip
        """
        if not isinstance(skip, (types.IntType, types.LongType)):
            raise TypeError("skip must be an int")
        self.__check_okay_to_chain()

        self.__skip = skip
        return self

    def __getitem__(self, index):
        """Get a single document or a slice of documents from this cursor.

        Raises :class:`~pymongo.errors.InvalidOperation` if this
        cursor has already been used.

        To get a single document use an integral index, e.g.::

          >>> db.test.find()[50]

        An :class:`IndexError` will be raised if the index is negative
        or greater than the amount of documents in this cursor. Any
        limit applied to this cursor will be ignored.

        To get a slice of documents use a slice index, e.g.::

          >>> db.test.find()[20:25]

        This will return this cursor with a limit of ``5`` and skip of
        ``20`` applied.  Using a slice index will override any prior
        limits or skips applied to this cursor (including those
        applied through previous calls to this method). Raises
        :class:`IndexError` when the slice has a step, a negative
        start value, or a stop value less than or equal to the start
        value.

        :Parameters:
          - `index`: An integer or slice index to be applied to this cursor
        """
        self.__check_okay_to_chain()
        if isinstance(index, types.SliceType):
            if index.step is not None:
                raise IndexError("Cursor instances do not support slice steps")

            skip = 0
            if index.start is not None:
                if index.start < 0:
                    raise IndexError("Cursor instances do not support negative indices")
                skip = index.start

            if index.stop is not None:
                limit = index.stop - skip
                if limit <= 0:
                    raise IndexError("stop index must be greater than start index for slice %r" % index)
            else:
                limit = 0

            self.__skip = skip
            self.__limit = limit
            return self

        if isinstance(index, (types.IntType, types.LongType)):
            if index < 0:
                raise IndexError("Cursor instances do not support negative indices")
            clone = self.clone()
            clone.skip(index + self.__skip)
            clone.limit(-1) # use a hard limit
            for doc in clone:
                return doc
            raise IndexError("no such item for Cursor instance")
        raise TypeError("index %r cannot be applied to Cursor instances" % index)

    def sort(self, key_or_list, direction=None):
        """Sorts this cursor's results.

        Takes either a single key and a direction, or a list of (key,
        direction) pairs. The key(s) must be an instance of ``(str,
        unicode)``, and the direction(s) must be one of
        (:data:`~pymongo.ASCENDING`,
        :data:`~pymongo.DESCENDING`). Raises
        :class:`~pymongo.errors.InvalidOperation` if this cursor has
        already been used. Only the last :meth:`sort` applied to this
        cursor has any effect.

        :Parameters:
          - `key_or_list`: a single key or a list of (key, direction)
            pairs specifying the keys to sort on
          - `direction` (optional): only used if `key_or_list` is a single
            key, if not given :data:`~pymongo.ASCENDING` is assumed
        """
        self.__check_okay_to_chain()
        keys = helpers._index_list(key_or_list, direction)
        self.__ordering = helpers._index_document(keys)
        return self

    def count(self, with_limit_and_skip=False):
        """Get the size of the results set for this query.

        Returns the number of documents in the results set for this query. Does
        not take :meth:`limit` and :meth:`skip` into account by default - set
        `with_limit_and_skip` to ``True`` if that is the desired behavior.
        Raises :class:`~pymongo.errors.OperationFailure` on a database error.

        :Parameters:
          - `with_limit_and_skip` (optional): take any :meth:`limit` or
            :meth:`skip` that has been applied to this cursor into account when
            getting the count

        .. note:: The `with_limit_and_skip` parameter requires server
           version **>= 1.1.4-**

        .. versionadded:: 1.1.1
           The `with_limit_and_skip` parameter.
           :meth:`~pymongo.cursor.Cursor.__len__` was deprecated in favor of
           calling :meth:`count` with `with_limit_and_skip` set to ``True``.
        """
        command = SON([("count", self.__collection.name()),
                       ("query", self.__spec),
                       ("fields", self.__fields)])

        if with_limit_and_skip:
            if self.__limit:
                command["limit"] = self.__limit
            if self.__skip:
                command["skip"] = self.__skip

        response = self.__collection.database()._command(command,
                                                         ["ns missing"])
        if response.get("errmsg", "") == "ns missing":
            return 0
        return int(response["n"])

    def distinct(self, key):
        """Get a list of distinct values for `key` among all documents in the
        result set of this query.

        Raises :class:`TypeError` if `key` is not an instance of
        ``(str, unicode)``.

        :Parameters:
          - `key`: name of key for which we want to get the distinct values

        .. note:: Requires server version **>= 1.1.3+**

        .. seealso:: :meth:`pymongo.collection.Collection.distinct`

        .. versionadded:: 1.1.2+
        """
        if not isinstance(key, types.StringTypes):
            raise TypeError("key must be an instance of (str, unicode)")

        command = SON([("distinct", self.__collection.name()), ("key", key)])

        if self.__spec:
            command["query"] = self.__spec

        return self.__collection.database()._command(command)["values"]

    # __len__ is deprecated (replaced with count(True)) and will be removed.
    #
    # The reason for this deprecation is a bit complex:
    # list(...) calls _PyObject_LengthHint to guess how much space will be
    # required for the returned list. That method in turn calls __len__.
    # Therefore, calling list(...) on a Cursor instance would require at least
    # two round trips to the database if we keep __len__ - this makes it about
    # twice as slow as [x for x in Cursor], which isn't obvious to users.
    # Not defining __len__ here makes performance more consistent
    def __len__(self):
        """DEPRECATED use :meth:`count` instead.
        """
        raise TypeError("Cursor.__len__ is deprecated, please use "
                        "Cursor.count(with_limit_and_skip=True) instead")

    def explain(self):
        """Returns an explain plan record for this cursor.
        """
        c = self.clone()
        c.__explain = True

        # always use a hard limit for explains
        if c.__limit:
            c.__limit = -abs(c.__limit)
        return c.next()

    def hint(self, index):
        """Adds a 'hint', telling Mongo the proper index to use for the query.

        Judicious use of hints can greatly improve query
        performance. When doing a query on multiple fields (at least
        one of which is indexed) pass the indexed field as a hint to
        the query. Hinting will not do anything if the corresponding
        index does not exist. Raises
        :class:`~pymongo.errors.InvalidOperation` if this cursor has
        already been used.

        `index` should be an index as passed to
        :meth:`~pymongo.collection.Collection.create_index`
        (e.g. ``[('field', ASCENDING)]``). If `index`
        is ``None`` any existing hints for this query are cleared. The
        last hint applied to this cursor takes precedence over all
        others.

        :Parameters:
          - `index`: index to hint on (as an index specifier)
        """
        self.__check_okay_to_chain()
        if index is None:
            self.__hint = None
            return self

        if not isinstance(index, (types.ListType)):
            raise TypeError("hint takes a list specifying an index")
        self.__hint = helpers._index_document(index)
        return self

    def where(self, code):
        """Adds a $where clause to this query.

        The `code` argument must be an instance of (str, unicode, Code)
        containing a JavaScript expression. This expression will be evaluated
        for each object scanned. Only those objects for which the expression
        evaluates to *true* will be returned as results. The keyword *this*
        refers to the object currently being scanned.

        Raises TypeError if `code` is not an instance of (str, unicode). Raises
        InvalidOperation if this cursor has already been used. Only the last
        where clause applied to a cursor has any effect.

        :Parameters:
          - `code`: JavaScript expression to use as a filter
        """
        self.__check_okay_to_chain()
        if not isinstance(code, Code):
            code = Code(code)

        self.__spec["$where"] = code
        return self

    def __send_message(self, message):
        """Send a query or getmore message and handles the response.
        """
        db = self.__collection.database()
        kwargs = {"_sock": self.__socket,
                  "_must_use_master": self.__must_use_master}
        if self.__connection_id is not None:
            kwargs["_connection_to_use"] = self.__connection_id

        response = db.connection()._send_message_with_response(message,
                                                               **kwargs)

        if isinstance(response, types.TupleType):
            (connection_id, response) = response
        else:
            connection_id = None

        self.__connection_id = connection_id

        try:
            response = helpers._unpack_response(response, self.__id)
        except AutoReconnect:
            db.connection()._reset()
            raise
        self.__id = response["cursor_id"]

        # starting from doesn't get set on getmore's for tailable cursors
        if not self.__tailable:
            assert response["starting_from"] == self.__retrieved

        self.__retrieved += response["number_returned"]
        self.__data = response["data"]

        if self.__limit and self.__id and self.__limit <= self.__retrieved:
            self.__die()

    def _refresh(self):
        """Refreshes the cursor with more data from Mongo.

        Returns the length of self.__data after refresh. Will exit early if
        self.__data is already non-empty. Raises OperationFailure when the
        cursor cannot be refreshed due to an error on the query.
        """
        if len(self.__data) or self.__killed:
            return len(self.__data)

        if self.__id is None:
            # Query
            self.__send_message(
                message.query(self.__query_options(),
                              self.__collection.full_name(),
                              self.__skip, self.__limit,
                              self.__query_spec(), self.__fields))
            if not self.__id:
                self.__killed = True
        elif self.__id:
            # Get More
            limit = 0
            if self.__limit:
                if self.__limit > self.__retrieved:
                    limit = self.__limit - self.__retrieved
                else:
                    self.__killed = True
                    return 0

            self.__send_message(
                message.get_more(self.__collection.full_name(),
                                 limit, self.__id))

        return len(self.__data)

    def __iter__(self):
        return self

    def next(self):
        db = self.__collection.database()
        if len(self.__data) or self._refresh():
            next = db._fix_outgoing(self.__data.pop(0), self.__collection)
        else:
            raise StopIteration
        return next

########NEW FILE########
__FILENAME__ = cursor_manager
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Different managers to handle when cursors are killed after they are closed.

New cursor managers should be defined as subclasses of CursorManager and can be
installed on a connection by calling
`pymongo.connection.Connection.set_cursor_manager`."""

import types


class CursorManager(object):
    """The default cursor manager.

    This manager will kill cursors one at a time as they are closed.
    """

    def __init__(self, connection):
        """Instantiate the manager.

        :Parameters:
          - `connection`: a Mongo Connection
        """
        self.__connection = connection

    def close(self, cursor_id):
        """Close a cursor by killing it immediately.

        Raises TypeError if cursor_id is not an instance of (int, long).

        :Parameters:
          - `cursor_id`: cursor id to close
        """
        if not isinstance(cursor_id, (types.IntType, types.LongType)):
            raise TypeError("cursor_id must be an instance of (int, long)")

        self.__connection.kill_cursors([cursor_id])


class BatchCursorManager(CursorManager):
    """A cursor manager that kills cursors in batches.
    """

    def __init__(self, connection):
        """Instantiate the manager.

        :Parameters:
          - `connection`: a Mongo Connection
        """
        self.__dying_cursors = []
        self.__max_dying_cursors = 20
        self.__connection = connection

        CursorManager.__init__(self, connection)

    def __del__(self):
        """Cleanup - be sure to kill any outstanding cursors.
        """
        self.__connection.kill_cursors(self.__dying_cursors)

    def close(self, cursor_id):
        """Close a cursor by killing it in a batch.

        Raises TypeError if cursor_id is not an instance of (int, long).

        :Parameters:
          - `cursor_id`: cursor id to close
        """
        if not isinstance(cursor_id, (types.IntType, types.LongType)):
            raise TypeError("cursor_id must be an instance of (int, long)")

        self.__dying_cursors.append(cursor_id)

        if len(self.__dying_cursors) > self.__max_dying_cursors:
            self.__connection.kill_cursors(self.__dying_cursors)
            self.__dying_cursors = []

########NEW FILE########
__FILENAME__ = database
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Database level operations."""

import types
try:
    import hashlib
    _md5func = hashlib.md5
except: # for Python < 2.5
    import md5
    _md5func = md5.new

from son import SON
from dbref import DBRef
from son_manipulator import ObjectIdInjector, ObjectIdShuffler
from collection import Collection
from errors import InvalidName, CollectionInvalid, OperationFailure
from code import Code
import helpers


class Database(object):
    """A Mongo database.
    """

    def __init__(self, connection, name):
        """Get a database by connection and name.

        Raises TypeError if name is not an instance of (str, unicode). Raises
        InvalidName if name is not a valid database name.

        :Parameters:
          - `connection`: a connection to Mongo
          - `name`: database name
        """
        if not isinstance(name, types.StringTypes):
            raise TypeError("name must be an instance of (str, unicode)")

        self.__check_name(name)

        self.__name = unicode(name)
        self.__connection = connection
        self.__incoming_manipulators = []
        self.__incoming_copying_manipulators = []
        self.__outgoing_manipulators = []
        self.__outgoing_copying_manipulators = []
        self.add_son_manipulator(ObjectIdInjector())

    def __check_name(self, name):
        for invalid_char in [" ", ".", "$", "/", "\\"]:
            if invalid_char in name:
                raise InvalidName("database names cannot contain the "
                                  "character %r" % invalid_char)
        if not name:
            raise InvalidName("database name cannot be the empty string")

    def add_son_manipulator(self, manipulator):
        """Add a new son manipulator to this database.

        Newly added manipulators will be applied before existing ones.

        :Parameters:
          - `manipulator`: the manipulator to add
        """
        def method_overwritten(instance, method):
            return getattr(instance, method) != getattr(super(instance.__class__, instance), method)


        if manipulator.will_copy():
            if method_overwritten(manipulator, "transform_incoming"):
                self.__incoming_copying_manipulators.insert(0, manipulator)
            if method_overwritten(manipulator, "transform_outgoing"):
                self.__outgoing_copying_manipulators.insert(0, manipulator)
        else:
            if method_overwritten(manipulator, "transform_incoming"):
                self.__incoming_manipulators.insert(0, manipulator)
            if method_overwritten(manipulator, "transform_outgoing"):
                self.__outgoing_manipulators.insert(0, manipulator)

    def connection(self):
        """Get the database connection.
        """
        return self.__connection

    def name(self):
        """Get the database name.
        """
        return self.__name

    def __cmp__(self, other):
        if isinstance(other, Database):
            return cmp((self.__connection, self.__name),
                       (other.__connection, other.__name))
        return NotImplemented

    def __repr__(self):
        return "Database(%r, %r)" % (self.__connection, self.__name)

    def __getattr__(self, name):
        """Get a collection of this database by name.

        Raises InvalidName if an invalid collection name is used.

        :Parameters:
          - `name`: the name of the collection to get
        """
        return Collection(self, name)

    def __getitem__(self, name):
        """Get a collection of this database by name.

        Raises InvalidName if an invalid collection name is used.

        :Parameters:
          - `name`: the name of the collection to get
        """
        return self.__getattr__(name)

    def create_collection(self, name, options={}):
        """Create a new collection in this database.

        Normally collection creation is automatic. This method should only if
        you want to specify options on creation. CollectionInvalid is raised
        if the collection already exists.

        Options should be a dictionary, with any of the following options:

          - "size": desired initial size for the collection (in bytes). must be
            less than or equal to 10000000000. For capped collections this size
            is the max size of the collection.
          - "capped": if True, this is a capped collection
          - "max": maximum number of objects if capped (optional)

        :Parameters:
          - `name`: the name of the collection to create
          - `options` (optional): options to use on the new collection
        """
        if name in self.collection_names():
            raise CollectionInvalid("collection %s already exists" % name)

        return Collection(self, name, options)

    def _fix_incoming(self, son, collection):
        """Apply manipulators to an incoming SON object before it gets stored.

        :Parameters:
          - `son`: the son object going into the database
          - `collection`: the collection the son object is being saved in
        """
        for manipulator in self.__incoming_manipulators:
            son = manipulator.transform_incoming(son, collection)
        for manipulator in self.__incoming_copying_manipulators:
            son = manipulator.transform_incoming(son, collection)
        return son

    def _fix_outgoing(self, son, collection):
        """Apply manipulators to a SON object as it comes out of the database.

        :Parameters:
          - `son`: the son object coming out of the database
          - `collection`: the collection the son object was saved in
        """
        for manipulator in helpers._reversed(self.__outgoing_manipulators):
            son = manipulator.transform_outgoing(son, collection)
        for manipulator in helpers._reversed(self.__outgoing_copying_manipulators):
            son = manipulator.transform_outgoing(son, collection)
        return son

    def _command(self, command, allowable_errors=[], check=True, sock=None):
        """Issue a DB command.
        """
        result = self["$cmd"].find_one(command, _sock=sock,
                                       _must_use_master=True)

        if check and result["ok"] != 1:
            if result["errmsg"] in allowable_errors:
                return result
            raise OperationFailure("command %r failed: %s" %
                                   (command, result["errmsg"]))
        return result

    def collection_names(self):
        """Get a list of all the collection names in this database.
        """
        results = self["system.namespaces"].find(_must_use_master=True)
        names = [r["name"] for r in results]
        names = [n[len(self.__name) + 1:] for n in names
                 if n.startswith(self.__name + ".")]
        names = [n for n in names if "$" not in n]
        return names

    def drop_collection(self, name_or_collection):
        """Drop a collection.

        :Parameters:
          - `name_or_collection`: the name of a collection to drop or the
            collection object itself
        """
        name = name_or_collection
        if isinstance(name, Collection):
            name = name.name()

        if not isinstance(name, types.StringTypes):
            raise TypeError("name_or_collection must be an instance of "
                            "(Collection, str, unicode)")

        self.connection()._purge_index(self.name(), name)

        if name not in self.collection_names():
            return

        self._command({"drop": unicode(name)})

    def validate_collection(self, name_or_collection):
        """Validate a collection.

        Returns a string of validation info. Raises CollectionInvalid if
        validation fails.
        """
        name = name_or_collection
        if isinstance(name, Collection):
            name = name.name()

        if not isinstance(name, types.StringTypes):
            raise TypeError("name_or_collection must be an instance of "
                            "(Collection, str, unicode)")

        result = self._command({"validate": unicode(name)})

        info = result["result"]
        if info.find("exception") != -1 or info.find("corrupt") != -1:
            raise CollectionInvalid("%s invalid: %s" % (name, info))
        return info

    def profiling_level(self):
        """Get the database's current profiling level.

        Returns one of (:data:`~pymongo.OFF`,
        :data:`~pymongo.SLOW_ONLY`, :data:`~pymongo.ALL`).
        """
        result = self._command({"profile": -1})

        assert result["was"] >= 0 and result["was"] <= 2
        return result["was"]

    def set_profiling_level(self, level):
        """Set the database's profiling level.

        Raises :class:`ValueError` if level is not one of
        (:data:`~pymongo.OFF`, :data:`~pymongo.SLOW_ONLY`,
        :data:`~pymongo.ALL`).

        :Parameters:
          - `level`: the profiling level to use
        """
        if not isinstance(level, types.IntType) or level < 0 or level > 2:
            raise ValueError("level must be one of (OFF, SLOW_ONLY, ALL)")

        self._command({"profile": level})

    def profiling_info(self):
        """Returns a list containing current profiling information.
        """
        return list(self["system.profile"].find())

    def error(self):
        """Get a database error if one occured on the last operation.

        Return None if the last operation was error-free. Otherwise return the
        error that occurred.
        """
        error = self._command({"getlasterror": 1})
        if error.get("err", 0) is None:
            return None
        if error["err"] == "not master":
            self.__connection._reset()
        return error

    def last_status(self):
        """Get status information from the last operation.

        Returns a SON object with status information.
        """
        return self._command({"getlasterror": 1})

    def previous_error(self):
        """Get the most recent error to have occurred on this database.

        Only returns errors that have occurred since the last call to
        `Database.reset_error_history`. Returns None if no such errors have
        occurred.
        """
        error = self._command({"getpreverror": 1})
        if error.get("err", 0) is None:
            return None
        return error

    def reset_error_history(self):
        """Reset the error history of this database.

        Calls to `Database.previous_error` will only return errors that have
        occurred since the most recent call to this method.
        """
        self._command({"reseterror": 1})

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'Database' object is not iterable")

    def _password_digest(self, username, password):
        """Get a password digest to use for authentication.
        """
        if not isinstance(password, types.StringTypes):
            raise TypeError("password must be an instance of (str, unicode)")
        if not isinstance(username, types.StringTypes):
            raise TypeError("username must be an instance of (str, unicode)")

        md5hash = _md5func()
        md5hash.update(username + ":mongo:" + password)
        return unicode(md5hash.hexdigest())

    def authenticate(self, name, password):
        """Authenticate to use this database.

        Once authenticated, the user has full read and write access to this
        database. Raises TypeError if either name or password is not an
        instance of (str, unicode). Authentication lasts for the life of the
        database connection, or until `Database.logout` is called.

        The "admin" database is special. Authenticating on "admin" gives access
        to *all* databases. Effectively, "admin" access means root access to
        the database.

        :Parameters:
          - `name`: the name of the user to authenticate
          - `password`: the password of the user to authenticate
        """
        if not isinstance(name, types.StringTypes):
            raise TypeError("name must be an instance of (str, unicode)")
        if not isinstance(password, types.StringTypes):
            raise TypeError("password must be an instance of (str, unicode)")

        result = self._command({"getnonce": 1})
        nonce = result["nonce"]
        digest = self._password_digest(name, password)
        md5hash = _md5func()
        md5hash.update("%s%s%s" % (nonce, unicode(name), digest))
        key = unicode(md5hash.hexdigest())
        try:
            result = self._command(SON([("authenticate", 1),
                                        ("user", unicode(name)),
                                        ("nonce", nonce),
                                        ("key", key)]))
            return True
        except OperationFailure:
            return False

    def logout(self):
        """Deauthorize use of this database for this connection.

        Note that other databases may still be authorized.
        """
        self._command({"logout": 1})

    def dereference(self, dbref):
        """Dereference a DBRef, getting the SON object it points to.

        Raises TypeError if `dbref` is not an instance of DBRef. Returns a SON
        object or None if the reference does not point to a valid object. Raises
        ValueError if `dbref` has a database specified that is different from
        the current database.

        :Parameters:
          - `dbref`: the reference
        """
        if not isinstance(dbref, DBRef):
            raise TypeError("cannot dereference a %s" % type(dbref))
        if dbref.database is not None and dbref.database != self.__name:
            raise ValueError("trying to dereference a DBRef that points to "
                             "another database (%r not %r)" % (dbref.database,
                                                               self.__name))
        return self[dbref.collection].find_one({"_id": dbref.id})

    def eval(self, code, *args):
        """Evaluate a JavaScript expression on the Mongo server.

        Useful if you need to touch a lot of data lightly; in such a scenario
        the network transfer of the data could be a bottleneck. The `code`
        argument must be a JavaScript function. Additional positional
        arguments will be passed to that function when it is run on the
        server.

        Raises TypeError if `code` is not an instance of (str, unicode,
        `Code`). Raises OperationFailure if the eval fails. Returns the result
        of the evaluation.

        :Parameters:
          - `code`: string representation of JavaScript code to be evaluated
          - `args` (optional): additional positional arguments are passed to
            the `code` being evaluated
        """
        if not isinstance(code, Code):
            code = Code(code)

        command = SON([("$eval", code), ("args", list(args))])
        result = self._command(command)
        return result.get("retval", None)

    def __call__(self, *args, **kwargs):
        """This is only here so that some API misusages are easier to debug.
        """
        raise TypeError("'Database' object is not callable. If you meant to "
                        "call the '%s' method on a 'Collection' object it is "
                        "failing because no such method exists." % self.__name)

########NEW FILE########
__FILENAME__ = dbref
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for manipulating DBRefs (references to MongoDB documents)."""

import types

from son import SON


class DBRef(object):
    """A reference to a document stored in a Mongo database.
    """

    def __init__(self, collection, id, database=None):
        """Initialize a new DBRef.

        Raises TypeError if collection or database is not an instance of
        (str, unicode). `database` is optional and allows references to
        documents to work across databases.

        :Parameters:
          - `collection`: name of the collection the document is stored in
          - `id`: the value of the document's _id field
          - `database` (optional): name of the database to reference
        """
        if not isinstance(collection, types.StringTypes):
            raise TypeError("collection must be an instance of (str, unicode)")
        if not isinstance(database, (types.StringTypes, types.NoneType)):
            raise TypeError("database must be an instance of (str, unicode)")

        self.__collection = collection
        self.__id = id
        self.__database = database

    def collection(self):
        """Get the name of this DBRef's collection as unicode.
        """
        return self.__collection
    collection = property(collection)

    def id(self):
        """Get this DBRef's _id.
        """
        return self.__id
    id = property(id)

    def database(self):
        """Get the name of this DBRef's database.

        Returns None if this DBRef doesn't specify a database.
        """
        return self.__database
    database = property(database)

    def as_doc(self):
        """Get the SON document representation of this DBRef.

        Generally not needed by application developers
        """
        doc = SON([("$ref", self.collection),
                         ("$id", self.id)])
        if self.database is not None:
            doc["$db"] = self.database
        return doc

    def __repr__(self):
        if self.database is None:
            return "DBRef(%r, %r)" % (self.collection, self.id)
        return "DBRef(%r, %r, %r)" % (self.collection, self.id, self.database)

    def __cmp__(self, other):
        if isinstance(other, DBRef):
            return cmp([self.__database, self.__collection, self.__id],
                       [other.__database, other.__collection, other.__id])
        return NotImplemented

    def __hash__(self):
        return hash((self.__collection, self.__id, self.__database))

########NEW FILE########
__FILENAME__ = errors
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Exceptions raised by the Mongo driver."""


class ConnectionFailure(IOError):
    """Raised when a connection to the database cannot be made or is lost.
    """


class AutoReconnect(ConnectionFailure):
    """Raised when a connection to the database is lost and an attempt to
    auto-reconnect will be made.

    In order to auto-reconnect you must handle this exception, recognizing that
    the operation which caused it has not necessarily succeeded. Future
    operations will attempt to open a new connection to the database (and
    will continue to raise this exception until the first successful
    connection is made).
    """


class ConfigurationError(Exception):
    """Raised when something is incorrectly configured.
    """


class OperationFailure(Exception):
    """Raised when a database operation fails.
    """


class InvalidOperation(Exception):
    """Raised when a client attempts to perform an invalid operation.
    """


class CollectionInvalid(Exception):
    """Raised when collection validation fails.
    """


class InvalidName(ValueError):
    """Raised when an invalid name is used.
    """


class InvalidBSON(ValueError):
    """Raised when trying to create a BSON object from invalid data.
    """

class InvalidStringData(ValueError):
    """Raised when trying to encode a string containing non-UTF8 data.
    """


class InvalidDocument(ValueError):
    """Raised when trying to create a BSON object from an invalid document.
    """


class UnsupportedTag(ValueError):
    """Raised when trying to parse an unsupported tag in an XML document.
    """


class InvalidId(ValueError):
    """Raised when trying to create an ObjectId from invalid data.
    """

########NEW FILE########
__FILENAME__ = helpers
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Little bits and pieces used by the driver that don't really fit elsewhere."""

import sys
import struct

from son import SON
from errors import OperationFailure, AutoReconnect
import bson
import pymongo

def _index_list(key_or_list, direction=None):
    """Helper to generate a list of (key, direction) pairs.

    Takes such a list, or a single key, or a single key and direction.
    """
    if direction is not None:
        return [(key_or_list, direction)]
    else:
        if isinstance(key_or_list, (str, unicode)):
            return [(key_or_list, pymongo.ASCENDING)]
        return key_or_list


def _index_document(index_list):
    """Helper to generate an index specifying document.

    Takes a list of (key, direction) pairs.
    """
    if not isinstance(index_list, list):
        raise TypeError("if no direction is specified, key_or_list must be an "
                        "instance of list")
    if not len(index_list):
        raise ValueError("key_or_list must not be the empty list")

    index = SON()
    for (key, value) in index_list:
        if not isinstance(key, (str, unicode)):
            raise TypeError("first item in each key pair must be a string")
        if not isinstance(value, int):
            raise TypeError("second item in each key pair must be ASCENDING or "
                            "DESCENDING")
        index[key] = value
    return index

def _reversed(l):
    """A version of the `reversed()` built-in for Python 2.3.
    """
    i = len(l)
    while i > 0:
        i -= 1
        yield l[i]
if sys.version_info[:3] >= (2, 4, 0):
    _reversed = reversed

def _unpack_response(response, cursor_id=None):
    """Unpack a response from the database.

    Check the response for errors and unpack, returning a dictionary
    containing the response data.

    :Parameters:
      - `response`: byte string as returned from the database
      - `cursor_id` (optional): cursor_id we sent to get this response -
        used for raising an informative exception when we get cursor id not
        valid at server response
    """
    response_flag = struct.unpack("<i", response[:4])[0]
    if response_flag == 1:
        # Shouldn't get this response if we aren't doing a getMore
        assert cursor_id is not None

        raise OperationFailure("cursor id '%s' not valid at server" %
                               cursor_id)
    elif response_flag == 2:
        error_object = bson.BSON(response[20:]).to_dict()
        if error_object["$err"] == "not master":
            raise AutoReconnect("master has changed")
        raise OperationFailure("database error: %s" %
                               error_object["$err"])
    else:
        assert response_flag == 0

    result = {}
    result["cursor_id"] = struct.unpack("<q", response[4:12])[0]
    result["starting_from"] = struct.unpack("<i", response[12:16])[0]
    result["number_returned"] = struct.unpack("<i", response[16:20])[0]
    result["data"] = bson._to_dicts(response[20:])
    assert len(result["data"]) == result["number_returned"]
    return result

########NEW FILE########
__FILENAME__ = json_util
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for using Python's :mod:`json` module with MongoDB documents.

This module provides two methods: `object_hook` and `default`. These names are
pretty terrible, but match the names used in Python's `json library
<http://docs.python.org/library/json.html>`_. They allow for specialized
encoding and decoding of MongoDB documents into `Mongo Extended JSON
<http://www.mongodb.org/display/DOCS/Mongo+Extended+JSON>`_'s *Strict* mode.
This lets you encode / decode MongoDB documents to JSON even when they use
special PyMongo types.

Example usage (serialization)::

>>> json.dumps(..., default=json_util.default)

Example usage (deserialization)::

>>> json.loads(..., object_hook=json_util.object_hook)

Currently this only handles special encoding and decoding for ObjectId and
DBRef instancs.
"""

from objectid import ObjectId
from dbref import DBRef

# TODO support other types, like Binary, Code, datetime & regex
# Binary and Code are tricky because they subclass str so json thinks it can
# handle them. Not sure what the proper way to get around this is...

def object_hook(dct):
    if "$oid" in dct:
        return ObjectId(str(dct["$oid"]))
    if "$ref" in dct:
        return DBRef(dct["$ref"], dct["$id"], dct.get("$db", None))
    return dct

def default(obj):
    if isinstance(obj, ObjectId):
        return {"$oid": str(obj)}
    if isinstance(obj, DBRef):
        return obj.as_doc()
    raise TypeError("%r is not JSON serializable" % obj)

########NEW FILE########
__FILENAME__ = master_slave_connection
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Master-Slave connection to Mongo.

Performs all writes to Master instance and distributes reads among all
instances."""

import types
import random

from database import Database
from connection import Connection


class MasterSlaveConnection(object):
    """A master-slave connection to Mongo.
    """

    def __init__(self, master, slaves=[]):
        """Create a new Master-Slave connection.

        The resultant connection should be interacted with using the same
        mechanisms as a regular `Connection`. The `Connection` instances used
        to create this `MasterSlaveConnection` can themselves make use of
        connection pooling, etc. 'Connection' instances used as slaves should
        be created with the slave_okay option set to True.

        If connection pooling is being used the connections should be created
        with "auto_start_request" mode set to False. All request functionality
        that is needed should be initiated by calling `start_request` on the
        `MasterSlaveConnection` instance.

        Raises TypeError if `master` is not an instance of `Connection` or
        slaves is not a list of at least one `Connection` instances.

        :Parameters:
          - `master`: `Connection` instance for the writable Master
          - `slaves` (optional): list of `Connection` instances for the
            read-only slaves
        """
        if not isinstance(master, Connection):
            raise TypeError("master must be a Connection instance")
        if not isinstance(slaves, types.ListType) or len(slaves) == 0:
            raise TypeError("slaves must be a list of length >= 1")

        for slave in slaves:
            if not isinstance(slave, Connection):
                raise TypeError("slave %r is not an instance of Connection" %
                                slave)

        self.__in_request = False
        self.__master = master
        self.__slaves = slaves

    def master(self):
        return self.__master
    master = property(master)

    def slaves(self):
        return self.__slaves
    slaves = property(slaves)

    def slave_okay(self):
        """Is it okay for this connection to connect directly to a slave?

        This is always True for MasterSlaveConnection instances.
        """
        return True
    slave_okay = property(slave_okay)

    def set_cursor_manager(self, manager_class):
        """Set the cursor manager for this connection.

        Helper to set cursor manager for each individual `Connection` instance
        that make up this `MasterSlaveConnection`.
        """
        self.__master.set_cursor_manager(manager_class)
        for slave in self.__slaves:
            slave.set_cursor_manager(manager_class)

    # _connection_to_use is a hack that we need to include to make sure
    # that killcursor operations can be sent to the same instance on which
    # the cursor actually resides...
    def _send_message(self, operation, data, safe=False, _connection_to_use=None):
        """Say something to Mongo.

        Sends a message on the Master connection. This is used for inserts,
        updates, and deletes.

        Raises ConnectionFailure if the message cannot be sent. Returns the
        request id of the sent message.

        :Parameters:
          - `operation`: opcode of the message
          - `data`: data to send
          - `safe`: perform a getLastError after sending the message
        """
        if _connection_to_use is None or _connection_to_use == -1:
            return self.__master._send_message(operation, data, safe)
        return self.__slaves[_connection_to_use]._send_message(operation, data, safe)

    # _connection_to_use is a hack that we need to include to make sure
    # that getmore operations can be sent to the same instance on which
    # the cursor actually resides...
    def _send_message_with_response(self, operation, data,
                                    _sock=None, _connection_to_use=None,
                                    _must_use_master=False):
        """Receive a message from Mongo.

        Sends the given message and returns a (connection_id, response) pair.

        :Parameters:
          - `operation`: opcode of the message to send
          - `data`: data to send
        """
        if _connection_to_use is not None:
            if _connection_to_use == -1:
                return (-1, self.__master._send_message_with_response(operation,
                                                                      data,
                                                                      _sock))
            else:
                return (_connection_to_use,
                        self.__slaves[_connection_to_use]
                        ._send_message_with_response(operation, data, _sock))

        # for now just load-balance randomly among slaves only...
        connection_id = random.randrange(0, len(self.__slaves))

        # _must_use_master is set for commands, which must be sent to the
        # master instance. any queries in a request must be sent to the
        # master since that is where writes go.
        if _must_use_master or self.__in_request or connection_id == -1:
            return (-1, self.__master._send_message_with_response(operation,
                                                                  data, _sock))

        return (connection_id,
                self.__slaves[connection_id]._send_message_with_response(operation,
                                                                         data,
                                                                         _sock))

    def start_request(self):
        """Start a "request".

        See documentation for `Connection.start_request`. Note that all
        operations performed within a request will be sent using the Master
        connection.
        """
        self.__in_request = True
        self.__master.start_request()

    def end_request(self):
        """End the current "request".

        See documentation for `Connection.end_request`.
        """
        self.__in_request = False
        self.__master.end_request()

    def __cmp__(self, other):
        if isinstance(other, MasterSlaveConnection):
            return cmp((self.__master, self.__slaves),
                       (other.__master, other.__slaves))
        return NotImplemented

    def __repr__(self):
        return "MasterSlaveConnection(%r, %r)" % (self.__master, self.__slaves)

    def __getattr__(self, name):
        """Get a database by name.

        Raises InvalidName if an invalid database name is used.

        :Parameters:
          - `name`: the name of the database to get
        """
        return Database(self, name)

    def __getitem__(self, name):
        """Get a database by name.

        Raises InvalidName if an invalid database name is used.

        :Parameters:
          - `name`: the name of the database to get
        """
        return self.__getattr__(name)

    def close_cursor(self, cursor_id, connection_id):
        """Close a single database cursor.

        Raises TypeError if cursor_id is not an instance of (int, long). What
        closing the cursor actually means depends on this connection's cursor
        manager.

        :Parameters:
          - `cursor_id`: cursor id to close
          - `connection_id`: id of the `Connection` instance where the cursor
            was opened
        """
        if connection_id == -1:
            return self.__master.close_cursor(cursor_id)
        return self.__slaves[connection_id].close_cursor(cursor_id)

    def database_names(self):
        """Get a list of all database names.
        """
        return self.__master.database_names()

    def drop_database(self, name_or_database):
        """Drop a database.

        :Parameters:
          - `name_or_database`: the name of a database to drop or the object
            itself
        """
        return self.__master.drop_database(name_or_database)

    def __iter__(self):
        return self

    def next(self):
        raise TypeError("'MasterSlaveConnection' object is not iterable")

    def _cache_index(self, database_name, collection_name, index_name, ttl):
        return self.__master._cache_index(database_name, collection_name,
                                          index_name, ttl)

    def _purge_index(self, database_name,
                     collection_name=None, index_name=None):
        return self.__master._purge_index(database_name,
                                          collection_name,
                                          index_name)

########NEW FILE########
__FILENAME__ = message
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for creating `messages
<http://www.mongodb.org/display/DOCS/Mongo+Wire+Protocol>`_ to be sent to
MongoDB.

.. note:: This module is for internal use and is generally not needed by
   application developers.

.. versionadded:: 1.1.2
"""

import threading
import struct
import random
import sys

import bson

try:
    import _cbson
    _use_c = True
except ImportError:
    _use_c = False


__ZERO = "\x00\x00\x00\x00"


def __last_error():
    """Data to send to do a lastError.
    """
    return query(0, "admin.$cmd", 0, -1, {"getlasterror": 1})


def __pack_message(operation, data):
    """Takes message data and adds a message header based on the operation.

    Returns the resultant message string.
    """
    request_id = random.randint(-2**31 - 1, 2**31)
    message = struct.pack("<i", 16 + len(data))
    message += struct.pack("<i", request_id)
    message += __ZERO # responseTo
    message += struct.pack("<i", operation)
    return (request_id, message + data)


def insert(collection_name, docs, check_keys, safe):
    """Get an **insert** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += "".join([bson.BSON.from_dict(doc, check_keys) for doc in docs])
    if safe:
        (_, insert_message) = __pack_message(2002, data)
        (request_id, error_message) = __last_error()
        return (request_id, insert_message + error_message)
    else:
        return __pack_message(2002, data)
if _use_c:
    insert = _cbson._insert_message


def update(collection_name, upsert, multi, spec, doc, safe):
    """Get an **update** message.
    """
    options = 0
    if upsert:
        options += 1
    if multi:
        options += 2

    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", options)
    data += bson.BSON.from_dict(spec)
    data += bson.BSON.from_dict(doc)
    if safe:
        (_, update_message) = __pack_message(2001, data)
        (request_id, error_message) = __last_error()
        return (request_id, update_message + error_message)
    else:
        return __pack_message(2001, data)


def query(options, collection_name,
          num_to_skip, num_to_return, query, field_selector=None):
    """Get a **query** message.
    """
    data = struct.pack("<I", options)
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_skip)
    data += struct.pack("<i", num_to_return)
    data += bson.BSON.from_dict(query)
    if field_selector is not None:
        data += bson.BSON.from_dict(field_selector)
    return __pack_message(2004, data)


def get_more(collection_name, num_to_return, cursor_id):
    """Get a **getMore** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_return)
    data += struct.pack("<q", cursor_id)
    return __pack_message(2005, data)


def delete(collection_name, spec, safe):
    """Get a **delete** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += __ZERO
    data += bson.BSON.from_dict(spec)
    if safe:
        (_, remove_message) = __pack_message(2006, data)
        (request_id, error_message) = __last_error()
        return (request_id, remove_message + error_message)
    else:
        return __pack_message(2006, data)


def kill_cursors(cursor_ids):
    """Get a **killCursors** message.
    """
    data = __ZERO
    data += struct.pack("<i", len(cursor_ids))
    for cursor_id in cursor_ids:
        data += struct.pack("<q", cursor_id)
    return __pack_message(2007, data)

########NEW FILE########
__FILENAME__ = objectid
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for working with MongoDB `ObjectIds
<http://www.mongodb.org/display/DOCS/Object+IDs>`_.
"""

import warnings
import datetime
import threading
import types
import time
import socket
import os
import struct
try:
    import hashlib
    _md5func = hashlib.md5
except: # for Python < 2.5
    import md5
    _md5func = md5.new

from errors import InvalidId


def _machine_bytes():
    """Get the machine portion of an ObjectId.
    """
    machine_hash = _md5func()
    machine_hash.update(socket.gethostname())
    return machine_hash.digest()[0:3]


class ObjectId(object):
    """A Mongo ObjectId.
    """

    _inc = 0
    _inc_lock = threading.Lock()

    _machine_bytes = _machine_bytes()

    def __init__(self, oid=None):
        """Initialize a new ObjectId_.

        If `oid` is ``None``, create a new (unique)
        ObjectId_. If `oid` is an instance of (``string``,
        :class:`ObjectId`) validate it and use that.  Otherwise, a
        :class:`TypeError` is raised. If `oid` is invalid,
        :class:`~pymongo.errors.InvalidId` is raised.

        :Parameters:
          - `oid` (optional): a valid ObjectId_ (12 byte binary or 24 character
            hex string)

        .. _ObjectId: http://www.mongodb.org/display/DOCS/Object+IDs
        """
        if oid is None:
            self.__generate()
        else:
            self.__validate(oid)

    def __generate(self):
        """Generate a new value for this ObjectId.
        """
        oid = ""

        # 4 bytes current time
        oid += struct.pack(">i", int(time.time()))

        # 3 bytes machine
        oid += ObjectId._machine_bytes

        # 2 bytes pid
        oid += struct.pack(">H", os.getpid() % 0xFFFF)

        # 3 bytes inc
        ObjectId._inc_lock.acquire()
        oid += struct.pack(">i", ObjectId._inc)[1:4]
        ObjectId._inc = (ObjectId._inc + 1) % 0xFFFFFF
        ObjectId._inc_lock.release()

        self.__id = oid

    def __validate(self, oid):
        """Validate and use the given id for this ObjectId.

        Raises TypeError if id is not an instance of (str, ObjectId) and
        InvalidId if it is not a valid ObjectId.

        :Parameters:
          - `oid`: a valid ObjectId
        """
        if isinstance(oid, ObjectId):
            self.__id = oid.__id
        elif isinstance(oid, types.StringType):
            if len(oid) == 12:
                self.__id = oid
            elif len(oid) == 24:
                self.__id = oid.decode("hex")
            else:
                raise InvalidId("%s is not a valid ObjectId" % oid)
        else:
            raise TypeError("id must be an instance of (str, ObjectId), "
                            "not %s" % type(oid))

    # DEPRECATED - use str(oid) instead, which returns a hex encoded string
    def url_encode(self):
        warnings.warn("oid.url_encode is deprecated and will be removed. "
                      "Please use str(oid) instead.", DeprecationWarning)
        return self.__id.encode("hex")

    # DEPRECATED - use ObjectId(encoded_oid) instead,
    # which takes a hex encoded string
    def url_decode(cls, encoded_oid):
        warnings.warn("ObjectId.url_decode is deprecated and will be removed. "
                      "Please use ObjectId(...) instead.", DeprecationWarning)
        return cls(encoded_oid.decode("hex"))
    url_decode = classmethod(url_decode)

    def binary(self):
        """12-byte binary representation of this ObjectId.
        """
        return self.__id
    binary = property(binary)

    def generation_time(self):
        """A :class:`datetime.datetime` instance representing the time of
        generation for this :class:`ObjectId`.

        The :class:`datetime.datetime` is always naive and represents the
        generation time in UTC. It is precise to the second.

        .. versionadded:: 1.1.2+
        """
        t = struct.unpack(">i", self.__id[0:4])[0]
        return datetime.datetime.utcfromtimestamp(t)
    generation_time = property(generation_time)

    def __str__(self):
        return self.__id.encode("hex")

    def __repr__(self):
        return "ObjectId('%s')" % self.__id.encode("hex")

    def __cmp__(self, other):
        if isinstance(other, ObjectId):
            return cmp(self.__id, other.__id)
        return NotImplemented

    def __hash__(self):
        return hash(self.__id)



########NEW FILE########
__FILENAME__ = son
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for creating and manipulating SON, the Serialized Ocument Notation.

Regular dictionaries can be used instead of SON objects, but not when the order
of keys is important. A SON object can be used just like a normal Python
dictionary."""

import datetime
import re
import binascii
import base64
import types


class SON(dict):
    """SON data.

    A subclass of dict that maintains ordering of keys and provides a few extra
    niceties for dealing with SON. SON objects can be saved and retrieved from
    Mongo.

    The mapping from Python types to Mongo types is as follows:

    ===================================  =============  ===================
    Python Type                          Mongo Type     Supported Direction
    ===================================  =============  ===================
    None                                 null           both
    bool                                 boolean        both
    int                                  number (int)   both
    float                                number (real)  both
    string                               string         py -> mongo
    unicode                              string         both
    list                                 array          both
    dict / `SON`                         object         both
    datetime.datetime [#dt]_ [#dt2]_     date           both
    compiled re                          regex          both
    `pymongo.binary.Binary`              binary         both
    `pymongo.objectid.ObjectId`          oid            both
    `pymongo.dbref.DBRef`                dbref          both
    None                                 undefined      mongo -> py
    unicode                              code           mongo -> py
    `pymongo.code.Code`                  code           py -> mongo
    unicode                              symbol         mongo -> py
    ===================================  =============  ===================

    Note that to save binary data it must be wrapped as an instance of
    `pymongo.binary.Binary`. Otherwise it will be saved as a Mongo string and
    retrieved as unicode.

    .. [#dt] datetime.datetime instances will be rounded to the nearest
       millisecond when saved
    .. [#dt2] all datetime.datetime instances are treated as *naive*. clients
       should always use UTC.
    """

    def __init__(self, data=None, **kwargs):
        self.__keys = []
        dict.__init__(self)
        self.update(data)
        self.update(kwargs)

    def __repr__(self):
        result = []
        for key in self.__keys:
            result.append("(%r, %r)" % (key, self[key]))
        return "SON([%s])" % ", ".join(result)

    def __setitem__(self, key, value):
        if key not in self:
            self.__keys.append(key)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.__keys.remove(key)
        dict.__delitem__(self, key)

    def keys(self):
        return list(self.__keys)

    def copy(self):
        other = SON()
        other.update(self)
        return other

    # TODO this is all from UserDict.DictMixin. it could probably be made more
    # efficient.
    # second level definitions support higher levels
    def __iter__(self):
        for k in self.keys():
            yield k

    def has_key(self, key):
        return key in self.keys()

    def __contains__(self, key):
        return key in self.keys()

    # third level takes advantage of second level definitions
    def iteritems(self):
        for k in self:
            yield (k, self[k])

    def iterkeys(self):
        return self.__iter__()

    # fourth level uses definitions from lower levels
    def itervalues(self):
        for _, v in self.iteritems():
            yield v

    def values(self):
        return [v for _, v in self.iteritems()]

    def items(self):
        return list(self.iteritems())

    def clear(self):
        for key in self.keys():
            del self[key]

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got "\
                                + repr(1 + len(args)))
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            raise
        del self[key]
        return value

    def popitem(self):
        try:
            k, v = self.iteritems().next()
        except StopIteration:
            raise KeyError('container is empty')
        del self[k]
        return (k, v)

    def update(self, other=None, **kwargs):
        # Make progressively weaker assumptions about "other"
        if other is None:
            pass
        elif hasattr(other, 'iteritems'):  # iteritems saves memory and lookups
            for k, v in other.iteritems():
                self[k] = v
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self[k] = other[k]
        else:
            for k, v in other:
                self[k] = v
        if kwargs:
            self.update(kwargs)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __cmp__(self, other):
        if isinstance(other, SON):
            return cmp((dict(self.iteritems()), self.keys()),
                       (dict(other.iteritems()), other.keys()))
        return cmp(dict(self.iteritems()), other)

    def __len__(self):
        return len(self.keys())

    # Thanks to Jeff Jenkins for the idea and original implementation
    def to_dict(self):
        """Convert a SON document to a normal Python dictionary instance.

        This is trickier than just *dict(...)* because it needs to be
        recursive.
        """

        def transform_value(value):
            if isinstance(value, types.ListType):
                return [transform_value(v) for v in value]
            if isinstance(value, SON):
                value = dict(value)
            if isinstance(value, types.DictType):
                for k, v in value.iteritems():
                    value[k] = transform_value(v)
            return value

        return transform_value(dict(self))

    def from_xml(cls, xml):
        """Create an instance of SON from an xml document.

        This is really only used for testing, and is probably unnecessary.
        """
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            import elementtree.ElementTree as ET

        from code import Code
        from binary import Binary
        from objectid import ObjectId
        from dbref import DBRef
        from errors import UnsupportedTag

        def pad(list, index):
            while index >= len(list):
                list.append(None)

        def make_array(array):
            doc = make_doc(array)
            array = []
            for (key, value) in doc.items():
                index = int(key)
                pad(array, index)
                array[index] = value
            return array

        def make_string(string):
            return string.text is not None and unicode(string.text) or u""

        def make_code(code):
            return code.text is not None and Code(code.text) or Code("")

        def make_binary(binary):
            if binary.text is not None:
                return Binary(base64.decodestring(binary.text))
            return Binary("")

        def make_boolean(bool):
            return bool.text == "true"

        def make_date(date):
            return datetime.datetime.utcfromtimestamp(float(date.text) /
                                                      1000.0)

        def make_ref(dbref):
            return DBRef(make_elem(dbref[0]), make_elem(dbref[1]))

        def make_oid(oid):
            return ObjectId(binascii.unhexlify(oid.text))

        def make_int(data):
            return int(data.text)

        def make_null(null):
            return None

        def make_number(number):
            return float(number.text)

        def make_regex(regex):
            return re.compile(make_elem(regex[0]), make_elem(regex[1]))

        def make_options(data):
            options = 0
            if not data.text:
                return options
            if "i" in data.text:
                options |= re.IGNORECASE
            if "l" in data.text:
                options |= re.LOCALE
            if "m" in data.text:
                options |= re.MULTILINE
            if "s" in data.text:
                options |= re.DOTALL
            if "u" in data.text:
                options |= re.UNICODE
            if "x" in data.text:
                options |= re.VERBOSE
            return options

        def make_elem(elem):
            try:
                return {"array": make_array,
                        "doc": make_doc,
                        "string": make_string,
                        "binary": make_binary,
                        "boolean": make_boolean,
                        "code": make_code,
                        "date": make_date,
                        "ref": make_ref,
                        "ns": make_string,
                        "oid": make_oid,
                        "int": make_int,
                        "null": make_null,
                        "number": make_number,
                        "pattern": make_string,
                        "options": make_options,
                        }[elem.tag](elem)
            except KeyError:
                raise UnsupportedTag("cannot parse tag: %s" % elem.tag)

        def make_doc(doc):
            son = SON()
            for elem in doc:
                son[elem.attrib["name"]] = make_elem(elem)
            return son

        tree = ET.XML(xml)
        doc = tree[1]

        return make_doc(doc)
    from_xml = classmethod(from_xml)

########NEW FILE########
__FILENAME__ = son_manipulator
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Manipulators that can edit SON objects as they enter and exit a database.

New manipulators should be defined as subclasses of SONManipulator and can be
installed on a database by calling
`pymongo.database.Database.add_son_manipulator`."""

import types

from objectid import ObjectId
from dbref import DBRef
from son import SON


class SONManipulator(object):
    """A base son manipulator.

    This manipulator just saves and restores objects without changing them.
    """

    def will_copy(self):
        """Will this SON manipulator make a copy of the incoming document?

        Derived classes that do need to make a copy should override this
        method, returning True instead of False. All non-copying manipulators
        will be applied first (so that the user's document will be updated
        appropriately), followed by copying manipulators.
        """
        return False

    def transform_incoming(self, son, collection):
        """Manipulate an incoming SON object.

        :Parameters:
          - `son`: the SON object to be inserted into the database
          - `collection`: the collection the object is being inserted into
        """
        if self.will_copy():
            return SON(son)
        return son

    def transform_outgoing(self, son, collection):
        """Manipulate an outgoing SON object.

        :Parameters:
          - `son`: the SON object being retrieved from the database
          - `collection`: the collection this object was stored in
        """
        if self.will_copy():
            return SON(son)
        return son


class ObjectIdInjector(SONManipulator):
    """A son manipulator that adds the _id field if it is missing.
    """

    def transform_incoming(self, son, collection):
        """Add an _id field if it is missing.
        """
        if not "_id" in son:
            son["_id"] = ObjectId()
        return son


# This is now handled during BSON encoding (for performance reasons),
# but I'm keeping this here as a reference for those implementing new
# SONManipulators.
class ObjectIdShuffler(SONManipulator):
    """A son manipulator that moves _id to the first position.
    """

    def will_copy(self):
        """We need to copy to be sure that we are dealing with SON, not a dict.
        """
        return True

    def transform_incoming(self, son, collection):
        """Move _id to the front if it's there.
        """
        if not "_id" in son:
            return son
        transformed = SON({"_id": son["_id"]})
        transformed.update(son)
        return transformed


class NamespaceInjector(SONManipulator):
    """A son manipulator that adds the _ns field.
    """

    def transform_incoming(self, son, collection):
        """Add the _ns field to the incoming object
        """
        son["_ns"] = collection.name()
        return son


class AutoReference(SONManipulator):
    """Transparently reference and de-reference already saved embedded objects.

    This manipulator should probably only be used when the NamespaceInjector is
    also being used, otherwise it doesn't make too much sense - documents can
    only be auto-referenced if they have an *_ns* field.

    NOTE: this will behave poorly if you have a circular reference.

    TODO: this only works for documents that are in the same database. To fix
    this we'll need to add a DatabaseInjector that adds *_db* and then make
    use of the optional *database* support for DBRefs.
    """

    def __init__(self, db):
        self.__database = db

    def will_copy(self):
        """We need to copy so the user's document doesn't get transformed refs.
        """
        return True

    def transform_incoming(self, son, collection):
        """Replace embedded documents with DBRefs.
        """

        def transform_value(value):
            if isinstance(value, types.DictType):
                if "_id" in value and "_ns" in value:
                    return DBRef(value["_ns"], transform_value(value["_id"]))
                else:
                    return transform_dict(SON(value))
            elif isinstance(value, types.ListType):
                return [transform_value(v) for v in value]
            return value

        def transform_dict(object):
            for (key, value) in object.items():
                object[key] = transform_value(value)
            return object

        return transform_dict(SON(son))

    def transform_outgoing(self, son, collection):
        """Replace DBRefs with embedded documents.
        """

        def transform_value(value):
            if isinstance(value, DBRef):
                return self.__database.dereference(value)
            elif isinstance(value, types.ListType):
                return [transform_value(v) for v in value]
            elif isinstance(value, types.DictType):
                return transform_dict(SON(value))
            return value

        def transform_dict(object):
            for (key, value) in object.items():
                object[key] = transform_value(value)
            return object

        return transform_dict(SON(son))

# TODO make a generic translator for custom types. Take encode, decode,
# should_encode and should_decode functions and just encode and decode where
# necessary. See examples/custom_type.py for where this would be useful.
# Alternatively it could take a should_encode, to_binary, from_binary and
# binary subtype.

########NEW FILE########
__FILENAME__ = thread_util
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Some utilities for dealing with threading."""

import threading
import time


class TimeoutableLock(object):
    """Lock implementation that allows blocking acquires to timeout.
    """

    def __init__(self):
        self.__unlocked = threading.Event()
        self.__unlocked.set()
        self.__lock = threading.Lock()

    def acquire(self, blocking=True, timeout=None):
        """Acquire the lock, blocking or non-blocking.

        When invoked without arguments, block until the lock is unlocked, then
        set it to locked, and return True.

        When invoked with the `blocking` argument set to True, do the same
        thing as when called without arguments, and return True.

        When invoked with the `blocking` argument set to False, do not block.
        If a call without an argument would block, return False immediately;
        otherwise do the same thing as when called without arguments, and
        return True.

        If `blocking` is True and `timeout` is not None then `timeout`
        specifies a timeout in seconds. If the lock cannot be acquired within
        the time limit return False. If `blocking` is False then `timeout` is
        ignored.

        :Parameters:
          - `blocking` (optional): perform a blocking acquire
          - `timeout` (optional): add a time limit to a blocking acquire
        """
        did_acquire = False

        self.__lock.acquire()

        if self.__unlocked.isSet():
            self.__unlocked.clear()
            did_acquire = True
        elif blocking:
            if timeout is not None:
                start_blocking = time.time()
            while True:
                self.__lock.release()

                if timeout is not None:
                    self.__unlocked.wait(start_blocking + timeout - \
                                             time.time())
                else:
                    self.__unlocked.wait()

                self.__lock.acquire()

                if self.__unlocked.isSet():
                    self.__unlocked.clear()
                    did_acquire = True
                    break
                elif timeout is not None and \
                        time.time() > start_blocking + timeout:
                    break

        self.__lock.release()
        return did_acquire

    def release(self):
        """Release the lock.

        When the lock is locked, reset it to unlocked and return. If any other
        threads are blocked waiting for the lock to become unlocked, allow
        exactly one of them to proceed.

        Do not call this method when the lock is unlocked - a RuntimeError will
        be raised.

        There is no return value.
        """
        self.__lock.acquire()
        if self.__unlocked.isSet():
            self.__lock.release()
            raise RuntimeError("trying to release an unlocked TimeoutableLock")

        self.__unlocked.set()
        self.__lock.release()

########NEW FILE########
