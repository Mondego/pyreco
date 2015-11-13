__FILENAME__ = codec
#!/usr/bin/python -OOOO
# vim: set fileencoding=utf8 shiftwidth=4 tabstop=4 textwidth=80 foldmethod=marker :
# Copyright (c) 2010, Kou Man Tong. All rights reserved.
# For licensing, see LICENSE file included in the package.
"""
Base codec functions for bson.
"""
import struct
import cStringIO
import calendar, pytz
from datetime import datetime
import warnings
from abc import ABCMeta, abstractmethod

# {{{ Error Classes
class MissingClassDefinition(ValueError):
	def __init__(self, class_name):
		super(MissingClassDefinition, self).__init__(
		"No class definition for class %s" % (class_name,))
# }}}
# {{{ Warning Classes
class MissingTimezoneWarning(RuntimeWarning):
	def __init__(self, *args):
		args = list(args)
		if len(args) < 1:
			args.append("Input datetime object has no tzinfo, assuming UTC.")
		super(MissingTimezoneWarning, self).__init__(*args)
# }}}
# {{{ Traversal Step
class TraversalStep(object):
	def __init__(self, parent, key):
		self.parent = parent
		self.key = key
# }}}
# {{{ Custom Object Codec

class BSONCoding(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def bson_encode(self):
		pass

	@abstractmethod
	def bson_init(self, raw_values):
		pass

classes = {}

def import_class(cls):
	if not issubclass(cls, BSONCoding):
		return

	global classes
	classes[cls.__name__] = cls

def import_classes(*args):
	for cls in args:
		import_class(cls)

def import_classes_from_modules(*args):
	for module in args:
		for item in module.__dict__:
			if hasattr(item, "__new__") and hasattr(item, "__name__"):
				import_class(item)

def encode_object(obj, traversal_stack, generator_func):
	values = obj.bson_encode()
	class_name = obj.__class__.__name__
	values["$$__CLASS_NAME__$$"] = class_name
	return encode_document(values, traversal_stack, obj, generator_func)

def encode_object_element(name, value, traversal_stack, generator_func):
	return "\x03" + encode_cstring(name) + \
			encode_object(value, traversal_stack,
					generator_func = generator_func)

class _EmptyClass(object):
	pass

def decode_object(raw_values):
	global classes
	class_name = raw_values["$$__CLASS_NAME__$$"]
	cls = None
	try:
		cls = classes[class_name]
	except KeyError, e:
		raise MissingClassDefinition(class_name)

	retval = _EmptyClass()
	retval.__class__ = cls
	alt_retval = retval.bson_init(raw_values)
	return alt_retval or retval

# }}}
# {{{ Codec Logic
def encode_string(value):
	value = value.encode("utf8")
	length = len(value)
	return struct.pack("<i%dsb" % (length,), length + 1, value, 0)

def decode_string(data, base):
	length = struct.unpack("<i", data[base:base + 4])[0]
	value = data[base + 4: base + 4 + length - 1]
	value = value.decode("utf8")
	return (base + 4 + length, value)

def encode_cstring(value):
	if isinstance(value, unicode):
		value = value.encode("utf8")
	return value + "\x00"

def decode_cstring(data, base):
	length = 0
	max_length = len(data) - base
	while length < max_length:
		character = data[base + length]
		length += 1
		if character == "\x00":
			break
	return (base + length, data[base:base + length - 1].decode("utf8"))

def encode_binary(value):
	length = len(value)
	return struct.pack("<ib", length, 0) + value

def decode_binary(data, base):
	length, binary_type = struct.unpack("<ib", data[base:base + 5])
	return (base + 5 + length, data[base + 5:base + 5 + length])

def encode_double(value):
	return struct.pack("<d", value)

def decode_double(data, base):
	return (base + 8, struct.unpack("<d", data[base: base + 8])[0])


ELEMENT_TYPES = {
		0x01 : "double",
		0x02 : "string",
		0x03 : "document",
		0x04 : "array",
		0x05 : "binary",
		0x08 : "boolean",
        0x09 : "UTCdatetime",
		0x0A : "none",
		0x10 : "int32",
		0x12 : "int64"
	}

def encode_double_element(name, value):
	return "\x01" + encode_cstring(name) + encode_double(value)

def decode_double_element(data, base):
	base, name = decode_cstring(data, base + 1)
	base, value = decode_double(data, base)
	return (base, name, value)

def encode_string_element(name, value):
	return "\x02" + encode_cstring(name) + encode_string(value)

def decode_string_element(data, base):
	base, name = decode_cstring(data, base + 1)
	base, value = decode_string(data, base)
	return (base, name, value)

def encode_value(name, value, buf, traversal_stack, generator_func):
	if isinstance(value, BSONCoding):
		buf.write(encode_object_element(name, value, traversal_stack,
			generator_func))
	elif isinstance(value, float):
		buf.write(encode_double_element(name, value))
	elif isinstance(value, unicode):
		buf.write(encode_string_element(name, value))
	elif isinstance(value, dict):
		buf.write(encode_document_element(name, value,
			traversal_stack, generator_func))
	elif isinstance(value, list) or isinstance(value, tuple):
		buf.write(encode_array_element(name, value,
			traversal_stack, generator_func))
	elif isinstance(value, str):
		buf.write(encode_binary_element(name, value))
	elif isinstance(value, bool):
		buf.write(encode_boolean_element(name, value))
	elif isinstance(value, datetime):
		buf.write(encode_UTCdatetime_element(name, value))
	elif value is None:
		buf.write(encode_none_element(name, value))
	elif isinstance(value, int):
		if value < -0x80000000 or value > 0x7fffffff:
			buf.write(encode_int64_element(name, value))
		else:
			buf.write(encode_int32_element(name, value))
	elif isinstance(value, long):
		buf.write(encode_int64_element(name, value))

def encode_document(obj, traversal_stack,
		traversal_parent = None,
		generator_func = None):
	buf = cStringIO.StringIO()
	key_iter = obj.iterkeys()
	if generator_func is not None:
		key_iter = generator_func(obj, traversal_stack)
	for name in key_iter:
		value = obj[name]
		traversal_stack.append(TraversalStep(traversal_parent or obj, name))
		encode_value(name, value, buf, traversal_stack, generator_func)
		traversal_stack.pop()
	e_list = buf.getvalue()
	e_list_length = len(e_list)
	return struct.pack("<i%dsb" % (e_list_length,), e_list_length + 4 + 1,
			e_list, 0)

def encode_array(array, traversal_stack,
		traversal_parent = None,
		generator_func = None):
	buf = cStringIO.StringIO()
	for i in xrange(0, len(array)):
		value = array[i]
		traversal_stack.append(TraversalStep(traversal_parent or array, i))
		encode_value(unicode(i), value, buf, traversal_stack, generator_func)
		traversal_stack.pop()
	e_list = buf.getvalue()
	e_list_length = len(e_list)
	return struct.pack("<i%dsb" % (e_list_length,), e_list_length + 4 + 1,
			e_list, 0)

def decode_element(data, base):
	element_type = struct.unpack("<b", data[base:base + 1])[0]
	element_description = ELEMENT_TYPES[element_type]
	decode_func = globals()["decode_" + element_description + "_element"]
	return decode_func(data, base)

def decode_document(data, base):
	length = struct.unpack("<i", data[base:base + 4])[0]
	end_point = base + length
	base += 4
	retval = {}
	while base < end_point - 1:
		base, name, value = decode_element(data, base)
		retval[name] = value
	if "$$__CLASS_NAME__$$" in retval:
		retval = decode_object(retval)
	return (end_point, retval)

def encode_document_element(name, value, traversal_stack, generator_func):
	return "\x03" + encode_cstring(name) + \
			encode_document(value, traversal_stack,
					generator_func = generator_func)

def decode_document_element(data, base):
	base, name = decode_cstring(data, base + 1)
	base, value = decode_document(data, base)
	return (base, name, value)

def encode_array_element(name, value, traversal_stack, generator_func):
	return "\x04" + encode_cstring(name) + \
			encode_array(value, traversal_stack, generator_func = generator_func)

def decode_array_element(data, base):
	base, name = decode_cstring(data, base + 1)
	base, value = decode_document(data, base)
	retval = []
	try:
		i = 0
		while True:
			retval.append(value[unicode(i)])
			i += 1
	except KeyError:
		pass
	return (base, name, retval)

def encode_binary_element(name, value):
	return "\x05" + encode_cstring(name) + encode_binary(value)

def decode_binary_element(data, base):
	base, name = decode_cstring(data, base + 1)
	base, value = decode_binary(data, base)
	return (base, name, value)

def encode_boolean_element(name, value):
	return "\x08" + encode_cstring(name) + struct.pack("<b", value)

def decode_boolean_element(data, base):
	base, name = decode_cstring(data, base + 1)
	value = not not struct.unpack("<b", data[base:base + 1])[0]
	return (base + 1, name, value)

def encode_UTCdatetime_element(name, value):
	if value.tzinfo is None:
		warnings.warn(MissingTimezoneWarning(), None, 4)
	value = int(round(calendar.timegm(value.utctimetuple()) * 1000 +
		(value.microsecond / 1000.0)))
	return "\x09" + encode_cstring(name) + struct.pack("<q", value)

def decode_UTCdatetime_element(data, base):
	base, name = decode_cstring(data, base + 1)
	value = datetime.fromtimestamp(struct.unpack("<q",
		data[base:base + 8])[0] / 1000.0, pytz.utc)
	return (base + 8, name, value)

def encode_none_element(name, value):
	return "\x0a" + encode_cstring(name)

def decode_none_element(data, base):
	base, name = decode_cstring(data, base + 1)
	return (base, name, None)

def encode_int32_element(name, value):
	return "\x10" + encode_cstring(name) + struct.pack("<i", value)

def decode_int32_element(data, base):
	base, name = decode_cstring(data, base + 1)
	value = struct.unpack("<i", data[base:base + 4])[0]
	return (base + 4, name, value)

def encode_int64_element(name, value):
	return "\x12" + encode_cstring(name) + struct.pack("<q", value)

def decode_int64_element(data, base):
	base, name = decode_cstring(data, base + 1)
	value = struct.unpack("<q", data[base:base + 8])[0]
	return (base + 8, name, value)
# }}}

########NEW FILE########
__FILENAME__ = network
#!/usr/bin/env python

import socket
try:
	from cStringIO import StringIO
except ImportError, e:
	from StringIO import StringIO
from struct import unpack
from __init__ import dumps, loads

def _bintoint(data):
	return unpack("<i", data)[0]

def _sendobj(self, obj):
	"""
	Atomically send a BSON message.
	"""
	data = dumps(obj)
	self.sendall(data)

def _recvobj(self):
	"""
	Atomic read of a BSON message.

	This function either returns a dict, None, or raises a socket error.

	If the return value is None, it means the socket is closed by the other side.
	"""
	sock_buf = self.recvbytes(4)
	if sock_buf is None:
		return None

	message_length = _bintoint(sock_buf.getvalue())
	sock_buf = self.recvbytes(message_length - 4, sock_buf)
	if sock_buf is None:
		return None

	retval = loads(sock_buf.getvalue())
	return retval


def _recvbytes(self, bytes_needed, sock_buf = None):
	"""
	Atomic read of bytes_needed bytes.

	This function either returns exactly the nmber of bytes requested in a
	StringIO buffer, None, or raises a socket error.

	If the return value is None, it means the socket is closed by the other side.
	"""
	if sock_buf is None:
		sock_buf = StringIO()
	bytes_count = 0
	while bytes_count < bytes_needed:
		chunk = self.recv(min(bytes_needed - bytes_count, 32768))
		part_count = len(chunk)

		if part_count < 1:
			return None

		bytes_count += part_count
		sock_buf.write(chunk)
	
	return sock_buf

########NEW FILE########
__FILENAME__ = test_array
#!/usr/bin/env python

from bson import dumps, loads
from unittest import TestCase

class TestArray(TestCase):
	def setUp(self):
		lyrics = u"""Viva La Vida lyrics

		I used to rule the world
		Seas would rise when I gave the word
		Now in the morning I sleep alone
		Sweep the streets I used to own

		I used to roll the dice
		Feel the fear in my enemy's eyes
		Listen as the crowd would sing
		"Now the old king is dead! Long live the king!"

		One minute I held the key
		Next the walls were closed on me
		And I discovered that my castles stand
		Upon pillars of salt and pillars of sand

		I hear Jerusalem bells a ringing
		Roman Cavalry choirs are singing
		Be my mirror, my sword and shield
		My missionaries in a foreign field

		For some reason I can't explain
		Once you go there was never
		Never an honest word
		And that was when I ruled the world

		It was the wicked and wild wind
		Blew down the doors to let me in
		Shattered windows and the sound of drums
		People couldn't believe what I'd become

		Revolutionaries wait
		For my head on a silver plate
		Just a puppet on a lonely string
		Oh who would ever want to be king?

		I hear Jerusalem bells a ringing
		Roman Cavalry choirs are singing
		Be my mirror, my sword and shield
		My missionaries in a foreign field

		For some reason I can't explain
		I know Saint Peter won't call my name
		Never an honest word
		But that was when I ruled the world

		I hear Jerusalem bells a ringing
		Roman Cavalry choirs are singing
		Be my mirror, my sword and shield
		My missionaries in a foreign field

		For some reason I can't explain
		I know Saint Peter won't call my name
		Never an honest word
		But that was when I ruled the world""".split(u"\n")
		self.doc = {u"lyrics" : lyrics}

	def test_long_array(self):
		serialized = dumps(self.doc)
		doc2 = loads(serialized)
		self.assertEquals(self.doc, doc2)

	def test_encoded_order(self):
		serialized = dumps(self.doc)
		self.assertEquals(repr(serialized), r"""'\xe2\x07\x00\x00\x04lyrics\x00\xd5\x07\x00\x00\x020\x00\x14\x00\x00\x00Viva La Vida lyrics\x00\x021\x00\x01\x00\x00\x00\x00\x022\x00\x1b\x00\x00\x00\t\tI used to rule the world\x00\x023\x00\'\x00\x00\x00\t\tSeas would rise when I gave the word\x00\x024\x00#\x00\x00\x00\t\tNow in the morning I sleep alone\x00\x025\x00"\x00\x00\x00\t\tSweep the streets I used to own\x00\x026\x00\x01\x00\x00\x00\x00\x027\x00\x1a\x00\x00\x00\t\tI used to roll the dice\x00\x028\x00#\x00\x00\x00\t\tFeel the fear in my enemy\'s eyes\x00\x029\x00!\x00\x00\x00\t\tListen as the crowd would sing\x00\x0210\x002\x00\x00\x00\t\t"Now the old king is dead! Long live the king!"\x00\x0211\x00\x01\x00\x00\x00\x00\x0212\x00\x1c\x00\x00\x00\t\tOne minute I held the key\x00\x0213\x00#\x00\x00\x00\t\tNext the walls were closed on me\x00\x0214\x00)\x00\x00\x00\t\tAnd I discovered that my castles stand\x00\x0215\x00+\x00\x00\x00\t\tUpon pillars of salt and pillars of sand\x00\x0216\x00\x01\x00\x00\x00\x00\x0217\x00#\x00\x00\x00\t\tI hear Jerusalem bells a ringing\x00\x0218\x00#\x00\x00\x00\t\tRoman Cavalry choirs are singing\x00\x0219\x00$\x00\x00\x00\t\tBe my mirror, my sword and shield\x00\x0220\x00%\x00\x00\x00\t\tMy missionaries in a foreign field\x00\x0221\x00\x01\x00\x00\x00\x00\x0222\x00"\x00\x00\x00\t\tFor some reason I can\'t explain\x00\x0223\x00\x1e\x00\x00\x00\t\tOnce you go there was never\x00\x0224\x00\x17\x00\x00\x00\t\tNever an honest word\x00\x0225\x00&\x00\x00\x00\t\tAnd that was when I ruled the world\x00\x0226\x00\x01\x00\x00\x00\x00\x0227\x00"\x00\x00\x00\t\tIt was the wicked and wild wind\x00\x0228\x00#\x00\x00\x00\t\tBlew down the doors to let me in\x00\x0229\x00+\x00\x00\x00\t\tShattered windows and the sound of drums\x00\x0230\x00*\x00\x00\x00\t\tPeople couldn\'t believe what I\'d become\x00\x0231\x00\x01\x00\x00\x00\x00\x0232\x00\x17\x00\x00\x00\t\tRevolutionaries wait\x00\x0233\x00 \x00\x00\x00\t\tFor my head on a silver plate\x00\x0234\x00#\x00\x00\x00\t\tJust a puppet on a lonely string\x00\x0235\x00%\x00\x00\x00\t\tOh who would ever want to be king?\x00\x0236\x00\x01\x00\x00\x00\x00\x0237\x00#\x00\x00\x00\t\tI hear Jerusalem bells a ringing\x00\x0238\x00#\x00\x00\x00\t\tRoman Cavalry choirs are singing\x00\x0239\x00$\x00\x00\x00\t\tBe my mirror, my sword and shield\x00\x0240\x00%\x00\x00\x00\t\tMy missionaries in a foreign field\x00\x0241\x00\x01\x00\x00\x00\x00\x0242\x00"\x00\x00\x00\t\tFor some reason I can\'t explain\x00\x0243\x00(\x00\x00\x00\t\tI know Saint Peter won\'t call my name\x00\x0244\x00\x17\x00\x00\x00\t\tNever an honest word\x00\x0245\x00&\x00\x00\x00\t\tBut that was when I ruled the world\x00\x0246\x00\x01\x00\x00\x00\x00\x0247\x00#\x00\x00\x00\t\tI hear Jerusalem bells a ringing\x00\x0248\x00#\x00\x00\x00\t\tRoman Cavalry choirs are singing\x00\x0249\x00$\x00\x00\x00\t\tBe my mirror, my sword and shield\x00\x0250\x00%\x00\x00\x00\t\tMy missionaries in a foreign field\x00\x0251\x00\x01\x00\x00\x00\x00\x0252\x00"\x00\x00\x00\t\tFor some reason I can\'t explain\x00\x0253\x00(\x00\x00\x00\t\tI know Saint Peter won\'t call my name\x00\x0254\x00\x17\x00\x00\x00\t\tNever an honest word\x00\x0255\x00&\x00\x00\x00\t\tBut that was when I ruled the world\x00\x00\x00'""")

########NEW FILE########
__FILENAME__ = test_datetime
#!/usr/bin/env python

from bson import dumps, loads
from unittest import TestCase
import pytz
from datetime import datetime

class TestDateTime(TestCase):
	def test_datetime(self):
		now = datetime.now(pytz.utc)
		obj = {"now" : now}
		serialized = dumps(obj)
		obj2 = loads(serialized)

		td = obj2["now"] - now
		seconds_delta = (td.microseconds + (td.seconds + td.days * 24 * 3600) *
				1e6) / 1e6
		self.assertTrue(abs(seconds_delta) < 0.001)

########NEW FILE########
__FILENAME__ = test_object
#!/usr/bin/env python

from bson import BSONCoding, dumps, loads, import_class
from unittest import TestCase

class TestData(BSONCoding):
	def __init__(self, *args):
		self.args = list(args)
		self.nested = None

	def bson_encode(self):
		return {"args" : self.args, "nested" : self.nested}

	def bson_init(self, raw_values):
		self.args = raw_values["args"]
		self.nested = raw_values["nested"]

	def __eq__(self, other):
		if not isinstance(other, TestData):
			return NotImplemented
		if self.args != other.args:
			return False
		if self.nested != other.nested:
			return False
		return True

	def __ne__(self, other):
		return not self.__eq__(other)

class TestObjectCoding(TestCase):
	def test_codec(self):
		import_class(TestData)
		data = TestData(u"Lorem ipsum dolor sit amet",
				"consectetur adipisicing elit",
				42)

		data2 = TestData(u"She's got both hands in her pockets",
				"and she won't look at you won't look at you eh",
				66,
				23.54,
				None,
				True,
				False,
				u"Alejandro")
		data2.nested = data

		serialized = dumps(data2)
		data3 = loads(serialized)
		self.assertTrue(data2 == data3)

########NEW FILE########
__FILENAME__ = test_random_tree
from bson import dumps, loads
from random import randint
from unittest import TestCase
import os

def populate(parent, howmany, max_children):
	to_add = howmany
	if howmany > max_children:
		children = randint(2, max_children)
		distribution = []
		for i in xrange(0, children - 1):
			distribution.append(int(howmany / children))
		distribution.append(howmany - sum(distribution, 0))
		for i in xrange(0, children):
			steal_target = randint(0, children - 1)
			while steal_target == i:
				steal_target = randint(0, children -1)
			steal_count = randint(-1 * distribution[i],
					distribution[steal_target]) / 2
			distribution[i] += steal_count
			distribution[steal_target] -= steal_count
		
		for i in xrange(0, children):
			make_dict = randint(0, 1)
			baby = None
			if make_dict:
				baby = {}
			else:
				baby = []
			populate(baby, distribution[i], max_children)
			if isinstance(parent, dict):
				parent[os.urandom(8).encode("hex")] = baby
			else:
				parent.append(baby)
	else:
		populate_with_leaves(parent, howmany)

def populate_with_leaves(parent, howmany):
	for i in xrange(0, howmany):
		leaf = os.urandom(4).encode("hex")
		make_unicode = randint(0, 1)
		if make_unicode:
			leaf = unicode(leaf)
		if isinstance(parent, dict):
			parent[os.urandom(4).encode("hex")] = leaf
		else:
			parent.append(leaf)

class TestRandomTree(TestCase):
	def test_random_tree(self):
		for i in xrange(0, 16):
			p = {}
			populate(p, 256, 4)
			sp = dumps(p)
			p2 = loads(sp)
			self.assertEquals(p, p2)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# vim: set fileencoding=utf8 shiftwidth=4 tabstop=4 textwidth=80 foldmethod=marker :
# Copyright (c) 2011, Kou Man Tong. All rights reserved.
# For licensing, see LICENSE file included in the package.

import bson.tests

if __name__ == "__main__":
	bson.tests.main()

########NEW FILE########
