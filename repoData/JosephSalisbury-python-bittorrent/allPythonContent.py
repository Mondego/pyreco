__FILENAME__ = bencode
#	bencode.py -- deals with bencoding
#	Written by Joe Salisbury <salisbury.joseph@gmail.com>
#
#	You are free to use this code in anyway you see fit, on the basis
#	that if it is used, modified, or distributed, proper accreditation
#	of the original author remains.

""" This module deals with the encoding and decoding of bencoded data.
decode() and encode() are the major functions available, to decode
and encode data. """

# Note: Bencoding specification:
# http://www.bittorrent.org/beps/bep_0003.html

import types
from util import collapse

def stringlength(string, index = 0):
	""" Given a bencoded expression, starting with a string, returns
	the length of the string. """

	try:
		colon = string.find(":", index)	# Find the colon, ending the number.
	except ValueError:
		raise BencodeError("Decode", "Malformed expression", data)

	# Return a list of the number characters.
	num = [a for a in string[index:colon] if a.isdigit() ]
	n = int(collapse(num))	# Collapse them, and turn them into an int.

	# Return the length of the number, colon, and the string length.
	return len(num) + 1 + n

def walk(exp, index = 1):
	""" Given a compound bencoded expression, as a string, returns
	the index of the end of the first dict, or list.
	Start at an index of 1, to avoid the start of the actual list. """

	# The expression starts with an integer.
	if exp[index] == "i":
		# Find the end of the integer, then, keep walking.
		endchar = exp.find("e", index)
		return walk(exp, endchar + 1)

	# The expression starts with a string.
	elif exp[index].isdigit():
		# Skip to the end of the string, keep walking.
		strlength = stringlength(exp, index)
		return walk(exp, index + strlength)

	# The expression starts with a list or dict.
	elif exp[index] == "l" or exp[index] == "d":
		# Walk through to the end of the sub, then keep going.
		endsub = walk(exp[index:], 1)
		return walk(exp, index + endsub)

	# The expression is a lone 'e', so we're at the end of the list.
	elif exp[index] == "e":
		index += 1	# Jump one, to include it, then return the index.
		return index

def inflate(exp):
	""" Given a compound bencoded expression, as a string, returns the
	individual data types within the string as items in a list.
	Note, that lists and dicts will come out not inflated. """

	# Base case, for an empty expression.
	if exp == "":
		return []

	# The expression starts with an integer.
	if ben_type(exp) == int:
		# Take the integer, and inflate the rest.
		end = exp.find("e")	# The end of the integer.

		x = exp[:end + 1]
		xs = inflate(exp[end + 1:])

	# The expression starts with a string.
	elif ben_type(exp) == str:
		# Take the string, and inflate the rest.
		strlength = stringlength(exp)	# The end of the string.

		x = exp[:strlength]
		xs = inflate(exp[strlength:])

	# The expression starts with a dict, or a list.
	# We can treat both the same way.
	elif ben_type(exp) == list or ben_type(exp) == dict:
		# Take the sub type, and inflate the rest.
		end = walk(exp)	# Find the end of the data type

		x = exp[:end]
		xs = inflate(exp[end:])

	# Returns the first item, with the inflated rest of the list.
	return [x] + xs

def ben_type(exp):
	""" Given a bencoded expression, returns what type it is. """

	if exp[0] == "i":
		return int
	elif exp[0].isdigit():
		return str
	elif exp[0] == "l":
		return list
	elif exp[0] == "d":
		return dict

def check_type(exp, datatype):
	""" Given an expression, and a datatype, checks the two against
	each other. """

	try:
		assert type(exp) == datatype
	except AssertionError:
		raise BencodeError("Encode", "Malformed expression", exp)

def check_ben_type(exp, datatype):
	""" Given a bencoded expression, and a datatype, checks the two
	against each other. """

	try:
		assert ben_type(exp) == datatype
	except AssertionError:
		raise BencodeError("Decode", "Malformed expression", exp)

class BencodeError(Exception):
	""" Raised if an error occurs encoding or decoding. """

	def __init__(self, mode, value, data):
		""" Takes information of the error. """

		assert mode in ["Encode", "Decode"]

		self.mode = mode
		self.value = value
		self.data = data

	def __str__(self):
		""" Pretty-prints the information. """

		return repr(self.mode + ": " + self.value + " : " + str(self.data))

def encode_int(data):
	""" Given an integer, returns a bencoded string of that integer. """

	check_type(data, int)

	return "i" + str(data) + "e"

def decode_int(data):
	""" Given a bencoded string of a integer, returns the integer. """

	check_ben_type(data, int)

	# Find the end constant of the integer. It may not exist, which would lead
	# to an error being raised.
	try:
		end = data.index("e")
	except ValueError:
		raise BencodeError("Decode", "Cannot find end of integer expression", data)

	t = data[1:end]	# Remove the substring we want.

	# Check for leading zeros, which are not allowed.
	if len(t) > 1 and t[0] == "0":
		raise BencodeError("Decode", "Malformed expression, leading zeros", data)

	return int(t)	# Return an integer.

def encode_str(data):
	""" Given a string, returns a bencoded string of that string. """

	check_type(data, str)

	# Return the length of the string, the colon, and the string itself.
	return str(len(data)) + ":" + data

def decode_str(data):
	""" Given a bencoded string, returns the decoded string. """

	check_ben_type(data, str)

	# We want everything past the first colon.
	try:
		colon = data.find(":")
	except ValueError:
		raise BencodeError("Decode", "Badly formed expression", data)
	# Up to the end of the data.
	strlength = stringlength(data)

	# The subsection of the data we want.
	return data[colon + 1:strlength]

def encode_list(data):
	""" Given a list, returns a bencoded list. """

	check_type(data, list)

	# Special case of an empty list.
	if data == []:
		return "le"

	# Encode each item in the list.
	temp = [encode(item) for item in data]
	# Add list annotation, and collapse the list.
	return "l" + collapse(temp) + "e"

def decode_list(data):
	""" Given a bencoded list, return the unencoded list. """

	check_ben_type(data, list)

	# Special case of an empty list.
	if data == "le":
		return []

	# Remove list annotation, and inflate the l.
	temp = inflate(data[1:-1])
	# Decode each item in the list.
	return [decode(item) for item in temp]

def encode_dict(data):
	""" Given a dictionary, return the bencoded dictionary. """

	check_type(data, dict)

	# Special case of an empty dictionary.
	if data == {}:
		return "de"

	# Encode each key and value for each key in the dictionary.
	temp = [encode_str(key) + encode(data[key]) for key in sorted(data.keys())]
	# Add dict annotation, and collapse the dictionary.
	return "d" + collapse(temp) + "e"

def decode_dict(data):
	""" Given a bencoded dictionary, return the dictionary. """

	check_ben_type(data, dict)

	# Special case of an empty dictionary.
	if data == "de":
		return {}

	# Remove dictionary annotation
	data = data[1:-1]

	temp = {}
	terms = inflate(data)

	# For every key value pair in the terms list, decode the key,
	# and add it to the dictionary, with its decoded value
	count = 0
	while count != len(terms):
		temp[decode_str(terms[count])] = decode(terms[count + 1])
		count += 2

	return temp

# Dictionaries of the data type, and the function to use
encode_functions = { int  : encode_int  ,
					 str  : encode_str  ,
					 list : encode_list ,
					 dict : encode_dict }

decode_functions = { int  : decode_int  ,
					 str  : decode_str  ,
					 list : decode_list ,
					 dict : decode_dict }

def encode(data):
	""" Dispatches data to appropriate encode function. """

	try:
		return encode_functions[type(data)](data)
	except KeyError:
		raise BencodeError("Encode", "Unknown data type", data)

def decode(data):
	""" Dispatches data to appropriate decode function. """

	try:
		return decode_functions[ben_type(data)](data)
	except KeyError:
		raise BencodeError("Decode", "Unknown data type", data)

########NEW FILE########
__FILENAME__ = bittorrent
#!/usr/bin/env python
# pytorrent.py

from torrent import *
from tracker import *
########NEW FILE########
__FILENAME__ = simpledb
#	simpledb.py -- a nice and simple database
#	Written by Joe Salisbury <salisbury.joseph@gmail.com>
#
#	You are free to use this code in anyway you see fit, on the basis
#	that if it is used, modified, or distributed, proper accreditation
#	of the original author remains.

""" A nice and simple database class. """

# In a nutshell, the Database class acts like a dictionary, and
# implements most of the built-in dictionaries functions. Except its
# persistent!
# As bsddb can only accept strings for keys and values, we need to
# pickle everything before we use it. Therefore, most of the functions
# dump the data, interface with the dict, then load the results.

from bsddb import hashopen
from pickle import dumps, loads

class Database():
	""" A wrapper around a bsddb database, acting as a dictionary.
	Can accept all Python datatypes as keys, and values. """

	def __init__(self, dbname, flag="c"):
		""" Read the database given by dbname. """

		self.data = hashopen(dbname, flag)

	def __contains__(self, key):
		""" Return true if the database contains the key. """

		key = dumps(key)
		boolean = self.data.has_key(key)	# Returns 1 or 0.
		return bool(boolean)

	def __getitem__(self, key):
		""" Return the value held by the key. """

		key = dumps(key)
		value = self.data[key]
		return loads(value)

	has_key = __contains__
	get 	= __getitem__

	def __setitem__(self, key, value):
		""" Set the value of key to the value given. """

		key = dumps(key)
		value = dumps(value)
		self.data[key] = value

	def __repr__(self):
		""" Represent the database. """

		keys = self.data.keys()
		items = [(loads(key), loads(self.data[key])) for key in keys]
		return str(dict(items))

	def clear(self):
		""" Remove all data in the database. """

		self.data.clear()

	def items(self):
		""" Return a list of tuples of the keys and values. """

		keys = self.data.keys()
		items = [(loads(key), loads(self.data[key])) for key in keys]
		return items

	def keys(self):
		""" Return a list of keys. """

		keys = [loads(key) for key in self.data.keys()]
		return keys

	def values(self):
		""" Return a list of values. """

		values = [loads(value) for value in self.data.values()]
		return values

	def pop(self, key):
		""" Return the value given by key, and remove it. """

		key = dumps(key)
		value = self.data[key]
		del self.data[key]
		return loads(value)

	def setdefault(self, key, default):
		""" Return the value held by key, or default if it isn't in
		the database. """

		key = dumps(key)
		try:
			value = self.data[key]
		except KeyError:
			return default
		return loads(value)

	def __del__(self):
		""" Sync the database. """

		self.data.sync()
########NEW FILE########
__FILENAME__ = bencode_tests
#!/usr/bin/env python
# bencode_tests.py -- testing the bencoding module

import unittest
import bencode

class Walk(unittest.TestCase):
	""" Check the function walk() works correctly. """

	def test_simple_list(self):
		""" Test that simple lists are correctly seperated. """

		self.exp = "li1eei1e"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "li1ee")

	def test_longer_list(self):
		""" Test that longer lists are correctly seperated. """

		self.exp = "li1ei2eei1e"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "li1ei2ee")

	def test_list_with_string(self):
		""" Test that simple list with a string is seperated. """

		self.exp = "l4:teste3:end"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "l4:teste")

	def test_list_with_long_string(self):
		""" Test a list with a long string is seperated correctly. """

		self.exp = "l10:eggsandhame3:end"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "l10:eggsandhame")

	def test_nested_list(self):
		""" Test a nested list is seperated correctly. """

		self.exp = "li1eli2eei3eeli1ee"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "li1eli2eei3ee")

	def test_simple_dict(self):
		""" Test that simple dict is correctly seperated. """

		self.exp = "d3:key5:valueei1e"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "d3:key5:valuee")

	def test_longer_dict(self):
		""" Test that a longer dict is correctly seperated. """

		self.exp = "d5:key_17:value_15:key_27:value_2ei1e"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "d5:key_17:value_15:key_27:value_2e")

	def test_nested_dict(self):
		""" Test that a nested dict is correctly seperated. """

		self.exp = "d3:subd3:key5:valueeei1e"
		self.n = bencode.walk(self.exp, 1)
		self.assertEqual(self.exp[:self.n], "d3:subd3:key5:valueee")

class Inflate(unittest.TestCase):
	""" Check the inflate() function works correctly. """

	def test_simple(self):
		""" Test that a simple expression is inflated correctly. """

		self.n = bencode.inflate("i1e")
		self.assertEqual(self.n, ["i1e"])

	def test_longer(self):
		""" Test that a longer expression is inflated correctly. """

		self.n = bencode.inflate("i1ei2ei3e")
		self.assertEqual(self.n, ["i1e", "i2e", "i3e"])

	def test_long_string(self):
		""" Test that an expression containing a long string is
		inflated correctly. """

		self.n = bencode.inflate("i1e15:averylongstringi2e")
		self.assertEqual(self.n, ["i1e", "15:averylongstring", "i2e"])

	def test_mixed_simple(self):
		""" Test that a mixed simple expression is inflated correctly. """

		self.n = bencode.inflate("3:onei1e3:twoi2e")
		self.assertEqual(self.n, ["3:one", "i1e", "3:two", "i2e"])

	def test_mixed_complex(self):
		""" Test that a mixed complex expression is inflated correctly. """

		self.n = bencode.inflate("li1ei2eed3:key5:valuee")
		self.assertEqual(self.n, ["li1ei2ee", "d3:key5:valuee"])

class Ben_Type(unittest.TestCase):
	""" Check the function ben_type() works correctly. """

	def test_integers(self):
		""" Test that integers are correctly identified. """

		self.n = bencode.ben_type("i1e")
		self.assertEqual(self.n, int)

	def test_string(self):
		""" Test that strings are correctly identified. """

		self.n = bencode.ben_type("4:test")
		self.assertEqual(self.n, str)

	def test_list(self):
		""" Test that lists are correctly identified. """

		self.n = bencode.ben_type("l4:teste")
		self.assertEqual(self.n, list)

	def test_dict(self):
		""" Test that dictionaries are correctly identified. """

		self.n = bencode.ben_type("d3:key5:valuee")
		self.assertEqual(self.n, dict)

class Encode_Int(unittest.TestCase):
	"""  Check the function encode_int() works correctly. """

	def test_simple_integers(self):
		""" Test that simple integers are encoded correctly. """

		self.n = bencode.encode_int(1)
		self.assertEqual(self.n, "i1e")

	def test_zero(self):
		""" Test that zero is encoded correctly. """

		self.n = bencode.encode_int(0)
		self.assertEqual(self.n, "i0e")

	def test_longer_integers(self):
		""" Test that longer numbers are correctly encoded. """

		self.n = bencode.encode_int(12345)
		self.assertEqual(self.n, "i12345e")

	def test_minus_integers(self):
		""" Test that minus numbers are correctly encoded. """

		self.n = bencode.encode_int(-1)
		self.assertEqual(self.n, "i-1e")

	def test_leading_zeros(self):
		""" Test that leading zeros are correctly removed. """

		self.n = bencode.encode_int(01)
		self.assertEqual(self.n, "i1e")

	def test_exception_on_string(self):
		""" Test an exception is raised when encoding a string. """

		self.assertRaises(bencode.BencodeError, bencode.encode_int, "test")

class Decode_Int(unittest.TestCase):
	""" Check the function decode_int() works correctly. """

	def test_simple_integers(self):
		""" Test that simple integers are decoded correctly. """

		self.n = bencode.decode_int("i1e")
		self.assertEqual(self.n, 1)

	def test_zero(self):
		""" Test that zero is decoded correctly. """

		self.n = bencode.decode_int("i0e")
		self.assertEqual(self.n, 0)

	def test_longer_integers(self):
		""" Test that longer numbers are correctly decoded. """

		self.n = bencode.decode_int("i12345e")
		self.assertEqual(self.n, 12345)

	def test_minus_integers(self):
		""" Test that minus numbers are correctly decoded. """

		self.n = bencode.decode_int("i-1e")
		self.assertEqual(self.n, -1)

	def test_exception_on_leading_zeros(self):
		""" Test that an exception is raised when decoding an expression which
			has leading zeros. """

		self.assertRaises(bencode.BencodeError, bencode.decode_int, "i01e")

	def test_exception_on_missing_start_constant(self):
		""" Test that an exception is raised when trying to decode an expression
			which is missing the start constant. """

		self.assertRaises(bencode.BencodeError, bencode.decode_int, "1e")

	def test_exception_on_missing_end_constant(self):
		""" Test that an exception is raised when trying to decode an expression
			which is missing the end constant. """

		self.assertRaises(bencode.BencodeError, bencode.decode_int, "i1")

class Encode_Str(unittest.TestCase):
	""" Check the function encode_str() works correctly. """

	def test_character(self):
		""" Test that a single character is encoded correctly. """

		self.n = bencode.encode_str("a")
		self.assertEqual(self.n, "1:a")

	def test_string(self):
		""" Test that a string is encoded correctly. """

		self.n = bencode.encode_str("test")
		self.assertEqual(self.n, "4:test")

	def test_long_string(self):
		""" Test that a long string is encoded correctly. """

		self.n = bencode.encode_str("averylongstring")
		self.assertEqual(self.n, "15:averylongstring")

	def test_exception_on_int(self):
		""" Test that an exception is raised when trying to encode an integer. """

		self.assertRaises(bencode.BencodeError, bencode.encode_str, 1)

class Decode_Str(unittest.TestCase):
	""" Check the function decode_str() works correctly. """

	def test_character(self):
		""" Test that a single character is decoded correctly """

		self.n = bencode.decode_str("1:a")
		self.assertEqual(self.n, "a")

	def test_string(self):
		""" Test that a string is decoded correctly. """

		self.n = bencode.decode_str("4:test")
		self.assertEqual(self.n, "test")

	def test_long_string(self):
		""" Test that a long string is decoded correctly. """

		self.n = bencode.decode_str("15:averylongstring")
		self.assertEqual(self.n, "averylongstring")

	def test_string_length(self):
		""" Test that string length is respected. """

		self.n = bencode.decode_str("1:abc")
		self.assertEqual(self.n, "a")

	def test_exception_on_no_number(self):
		""" Test that an exception is raised when no number is prefixed. """

		self.assertRaises(bencode.BencodeError, bencode.decode_str, "abc")

class Encode_List(unittest.TestCase):
	""" Check the function encode_list() works correctly. """

	def test_simple_list(self):
		""" Test that a one item list is encoded correctly. """

		self.n = bencode.encode_list([1])
		self.assertEquals(self.n, "li1ee")

	def test_longer_list(self):
		""" Test that a longer list is encoded correctly. """

		self.n = bencode.encode_list([1, 2, 3])
		self.assertEquals(self.n, "li1ei2ei3ee")

	def test_mixed_list(self):
		""" Test that a mixed list is encoded correctly. """

		self.n = bencode.encode_list([1, "one"])
		self.assertEquals(self.n, "li1e3:onee")

	def test_nested_list(self):
		""" Test that a nested list is encoded correctly. """

		self.n = bencode.encode_list([[1, 2], [3, 4]])
		self.assertEquals(self.n, "lli1ei2eeli3ei4eee")

	def test_empty_list(self):
		""" Test that an empty list is encoded correctly. """

		self.n = bencode.encode_list([])
		self.assertEquals(self.n, "le")

	def test_exception_on_string(self):
		""" Test that an exception is raised when given a string. """

		self.assertRaises(bencode.BencodeError, bencode.encode_list, "test")

class Decode_List(unittest.TestCase):
	""" Check the function decode_list() works correctly. """

	def test_simple_list(self):
		""" Test that a one item list is decoded correctly. """

		self.n = bencode.decode_list("li1ee")
		self.assertEquals(self.n, [1])

	def test_longer_list(self):
		""" Test that a longer list is decoded correctly. """

		self.n = bencode.decode_list("li1ei2ei3ee")
		self.assertEquals(self.n, [1, 2, 3])

	def test_mixed_list(self):
		""" Test that a mixed list is decoded correctly. """

		self.n = bencode.decode_list("li1e3:onee")
		self.assertEquals(self.n, [1, "one"])

	def test_nested_list(self):
		""" Test that a nested list is decoded correctly. """

		self.n = bencode.decode_list("lli1ei2eeli3ei4eee")
		self.assertEquals(self.n, [[1, 2], [3, 4]])

	def test_empty_list(self):
		""" Test that an empty list is decoded correctly. """

		self.n = bencode.decode_list("le")
		self.assertEquals(self.n, [])

	def test_exception_on_string(self):
		""" Test that an exception is raised when given a string. """

		self.assertRaises(bencode.BencodeError, bencode.decode_list, "test")

class Encode_Dict(unittest.TestCase):
	""" Check the function encode_dict() works correctly. """

	def test_simple_dict(self):
		""" Test that a one key dict is encoded correctly. """

		self.n = bencode.encode_dict({"key":"value"})
		self.assertEquals(self.n, "d3:key5:valuee")

	def test_longer_dict(self):
		""" Test that a longer dict is encoded correctly. """

		self.n = bencode.encode_dict({"key_1":"value_1", "key_2":"value_2"})
		self.assertEquals(self.n, "d5:key_17:value_15:key_27:value_2e")

	def test_mixed_dict(self):
		""" Test that a dict with a list value is encoded correctly. """

		self.n = bencode.encode_dict({'key': ['a', 'b']})
		self.assertEquals(self.n, "d3:keyl1:a1:bee")

	def test_nested_dict(self):
		""" Test that a nested dict is encoded correctly. """

		self.n = bencode.encode_dict({"key":{"key":"value"}})
		self.assertEquals(self.n, "d3:keyd3:key5:valueee")

	def test_exception_on_string(self):
		""" Test that an exception is raised when given a string. """

		self.assertRaises(bencode.BencodeError, bencode.encode_dict, "test")

class Decode_Dict(unittest.TestCase):
	""" Check the function decode_dict() works correctly. """

	def test_simple_dict(self):
		""" Test that a one key dict is decoded correctly. """

		self.n = bencode.decode_dict("d3:key5:valuee")
		self.assertEquals(self.n, {"key":"value"})

	def test_longer_dict(self):
		""" Test that a longer dict is decoded correctly. """

		self.n = bencode.decode_dict("d5:key_17:value_15:key_27:value_2e")
		self.assertEquals(self.n, {"key_1":"value_1", "key_2":"value_2"})

	def test_mixed_dict(self):
		""" Test that a dict with a list value is decoded correctly. """

		self.n = bencode.decode_dict("d3:keyl1:a1:bee")
		self.assertEquals(self.n, {'key': ['a', 'b']})

	def test_nested_dict(self):
		""" Test that a nested dict is decoded correctly. """

		self.n = bencode.decode_dict("d3:keyd3:key5:valueee")
		self.assertEquals(self.n, {"key":{"key":"value"}})

	def test_exception_on_string(self):
		""" Test that an exception is raised when given a string. """

		self.assertRaises(bencode.BencodeError, bencode.decode_dict, "test")

class Encode(unittest.TestCase):
	""" Check the encode() function works. As this dispatches to the other
		encode functions, we only have to check the dispatching, not the other
		functions, as we have already checked those. """

	def test_integers(self):
		""" Test integers are encoded correctly. """

		self.n = bencode.encode(123)
		self.assertEqual(self.n, "i123e")

	def test_strings(self):
		""" Test strings are encoded correctly. """

		self.n = bencode.encode("test")
		self.assertEqual(self.n, "4:test")

	def test_lists(self):
		""" Test lists are encoded correctly. """

		self.n = bencode.encode([1, 2, 3])
		self.assertEquals(self.n, "li1ei2ei3ee")

	def test_dicts(self):
		""" Test dicts are encoded correctly. """

		self.n = bencode.encode({"key":"value"})
		self.assertEquals(self.n, "d3:key5:valuee")

class Decode(unittest.TestCase):
	""" Check the decode() function works. As this dispatches to the other
		decode functions, we only have to check the dispatching, not the other
		functions, as we have already checked those. """

	def test_integers(self):
		""" Test integers are decoded correctly. """

		self.n = bencode.decode("i123e")
		self.assertEqual(self.n, 123)

	def test_strings(self):
		""" Test strings are decoded correctly. """

		self.n = bencode.decode("4:test")
		self.assertEqual(self.n, "test")

	def test_lists(self):
		""" Test lists are decoded correctly. """

		self.n = bencode.decode("li1ee")
		self.assertEqual(self.n, [1])

	def test_dicts(self):
		""" Test dictionaries are decoded correctly. """

		self.n = bencode.decode("d3:key5:valuee")
		self.assertEqual(self.n, {"key":"value"})

########NEW FILE########
__FILENAME__ = simpledb_tests
#!/usr/bin/env python
# simpledb_tests.py -- tests for simpledb.py

import unittest
import simpledb

class Database_Tests(unittest.TestCase):
	""" Test that the Database() class works correctly. """

	def setUp(self):
		self.db = simpledb.Database(None)
		self.db["key"] = "value"	# Test key, value pair

	def test_contains(self):
		self.assertTrue(self.db.__contains__("key"))

	def test_getitem(self):
		self.assertEqual(self.db.__getitem__("key"), "value")

	def test_setitem(self):
		self.db.__setitem__("test_key", "test_value")
		self.assertEqual(self.db["test_key"], "test_value")

	def test_clear(self):
		self.db.clear()
		self.assertEqual(self.db.data, {})

	def test_has_key(self):
		self.assertTrue(self.db.has_key("key"))

	def test_get(self):
		self.assertEqual(self.db.get("key"), "value")

	def test_items(self):
		self.assertEqual(self.db.items(), [("key", "value")])

	def test_keys(self):
		self.assertEqual(self.db.keys(), ["key"])

	def test_values(self):
		self.assertEqual(self.db.values(), ["value"])

	def test_pop_return(self):
		self.assertEqual(self.db.pop("key"), "value")

	def test_pop_delete(self):
		self.db.pop("key")
		self.assertEqual(self.db.data, {})

	def test_setdefault_get(self):
		self.assertEqual(self.db.setdefault("key", "def"), "value")

	def test_setdefault_default(self):
		self.assertEqual(self.db.setdefault("no_key", "def"), "def")

	def tearDown(self):
		self.db = None
########NEW FILE########
__FILENAME__ = torrent_tests
#!/usr/bin/env python
# torrent_tests.py -- testing the torrent module

import unittest
import torrent
import bencode
import hashlib
import os
import util

class Make_Info_Dict(unittest.TestCase):
	""" Test that the make_info_dict function works correctly. """

	def setUp(self):
		""" Write a little file, and turn it into an info dict. """

		self.filename = "test.txt"
		with open(self.filename, "w") as self.file:
			self.file.write("Test file.")
		self.d = torrent.make_info_dict(self.filename)

	def test_length(self):
		""" Test that the length of file is correct. """

		with open(self.filename) as self.file:
			self.length = len(self.file.read())
		self.assertEqual(self.length, self.d["length"])

	def test_name(self):
		""" Test that the name of the file is correct. """

		self.assertEqual(self.filename, self.d["name"])

	def test_md5(self):
		""" Test that the md5 hash of the file is correct. """

		with open(self.filename) as self.file:
			self.md5 = hashlib.md5(self.file.read()).hexdigest()
		self.assertEqual(self.md5, self.d["md5sum"])

	def tearDown(self):
		""" Remove the file. """

		os.remove(self.filename)
		self.d = None

class Make_Torrent_File(unittest.TestCase):
	""" Test that make_torrent_file() works correctly. """

	def setUp(self):
		""" Write a little torrent file. """

		self.filename = "test.txt"
		self.tracker = "http://tracker.com"
		self.comment = "test"
		with open(self.filename, "w") as self.file:
			self.file.write("Test file.")
		self.t = bencode.decode(torrent.make_torrent_file \
			(file = self.filename, \
			tracker = self.tracker, \
			comment = self.comment))

	def test_announce(self):
		""" Test that the announce url is correct. """

		self.assertEqual(self.tracker, self.t["announce"])

	def test_announce_with_multiple_trackers(self):
		""" Test that announce is correct with multiple tracker. """

		self.t = bencode.decode(torrent.make_torrent_file \
			(file = self.filename, \
			tracker = [self.tracker, "http://tracker2.com"], \
			comment = self.comment))
		self.assertEqual(self.tracker, self.t["announce"])

	def test_announce_list(self):
		""" Test that the announce list is correct. """

		self.t = bencode.decode(torrent.make_torrent_file \
			(file = self.filename, \
			tracker = [self.tracker, "http://tracker2.com"], \
			comment = self.comment))
		self.assertEqual([[self.tracker], ["http://tracker2.com"]], \
			self.t["announce-list"])

	def test_created_by(self):
		""" Test that the created by field is correct. """

		self.assertEqual(torrent.CLIENT_NAME, self.t["created by"])

	def test_comment(self):
		""" Test that the comment is correct. """

		self.assertEqual(self.comment, self.t["comment"])

	def test_info_dict(self):
		""" Test that the info dict is correct. """

		self.info = torrent.make_info_dict(self.filename)
		self.assertEqual(self.info, self.t["info"])

	def test_error_on_no_file(self):
		""" Test that an error is raised when no file is given. """

		self.assertRaises(TypeError, torrent.make_torrent_file, \
			tracker = self.tracker)

	def test_error_on_no_tracker(self):
		""" Test that an error is raised when no tracker is given. """

		self.assertRaises(TypeError, torrent.make_torrent_file, \
			file = self.filename)

	def tearDown(self):
		""" Remove the torrent, and the file. """

		os.remove(self.filename)
		self.t = None

class Write_Torrent_File(unittest.TestCase):
	""" Test that write_torrent_file() works. As this dispatches to
	make_torrent_file, we only really need to test for errors, and that
	the actual file exists. """

	def setUp(self):
		""" Write a little torrent file. """

		self.torrent = "testing.torrent"
		self.filename = "test.txt"
		self.tracker = "http://tracker.com"
		self.comment = "test"
		with open(self.filename, "w") as self.file:
			self.file.write("Test file.")
		torrent.write_torrent_file(torrent = self.torrent,  \
			file = self.filename, tracker = self.tracker, \
				comment = self.comment)

	def test_torrent_file(self):
		""" Test that the torrent file has been written to. """

		self.assertTrue(os.path.isfile(self.torrent))

	def test_error_on_no_torrent(self):
		""" Test that an error occurs when no torrent is given. """

		self.assertRaises(TypeError, torrent.write_torrent_file, \
			file = self.filename)

	def tearDown(self):
		""" Remove the file. """

		self.t = None
		os.remove("testing.torrent")

class Read_Torrent_File(unittest.TestCase):
	""" Test that read_torrent_file() works. """

	def setUp(self):
		""" Write a little bencoded data to a file. """

		self.filename = "test.txt"
		self.data = bencode.encode([1, 2, 3])
		with open(self.filename, "w") as self.file:
			self.file.write(self.data)

	def test_read(self):
		""" Test that reading works correctly. """

		self.data = torrent.read_torrent_file(self.filename)
		self.assertEqual(self.data, [1, 2, 3])

	def tearDown(self):
		""" Delete the file. """

		self.data = None
		os.remove(self.filename)

class Generate_Peer_ID(unittest.TestCase):
	""" Test that generate_peer_id() works correctly. """

	def setUp(self):
		""" Generate a peerid. """

		self.peer_id = torrent.generate_peer_id()

	def test_first_dash(self):
		""" Test that the first character is a dash. """

		self.assertEqual("-", self.peer_id[0])

	def test_client_id(self):
		""" Test that the client id is correct. """

		self.assertEqual(torrent.CLIENT_ID, self.peer_id[1:3])

	def test_client_version(self):
		""" Test that the client version is correct. """

		self.assertEqual(torrent.CLIENT_VERSION, self.peer_id[3:7])

	def test_second_dash(self):
		""" Test that the second dash is present. """

		self.assertEqual("-", self.peer_id[7])

	def test_length(self):
		""" Test that the length of the id is correct. """

		self.assertTrue(len(self.peer_id) == 20)

	def tearDown(self):
		""" Remove the peerid. """

		self.peer_id = None

class Decode_Expanded_Peers(unittest.TestCase):
	""" Test that decode_expanded_peers() works. """

	def test_zero_peer(self):
		""" Test that a zero peer list is decoded correctly. """

		self.p = torrent.decode_expanded_peers([])
		self.assertEqual(self.p, [])

	def test_single_peer(self):
		""" Test that a one peer list is decoded. """

		self.p = torrent.decode_expanded_peers( \
			[{'ip': '100.100.100.100', 'peer id': 'test1', \
				'port': 1000}])
		self.assertEqual(self.p, [("100.100.100.100", 1000)])

	def test_multiple_peers(self):
		""" Test that a two peer list is decoded correctly. """

		self.p = torrent.decode_expanded_peers( \
			[{'ip': '100.100.100.100', \
			'peer id': 'test1', 'port': 1000}, \
				{'ip': '100.100.100.100', \
					'peer id': 'test2', 'port': 1000}])
		self.assertEqual(self.p, [('100.100.100.100', 1000), \
			('100.100.100.100', 1000)])

class Decode_Binary_Peers(unittest.TestCase):
	""" Test that decode_binary_peers() works. """

	def test_zero_peer(self):
		""" Test that a zero peer list is decoded correctly. """

		self.p = torrent.decode_binary_peers([])
		self.assertEqual(self.p, [])

	def test_single_peer(self):
		""" Test that a one peer list is decoded. """

		self.p = torrent.decode_binary_peers("dddd\x03\xe8")
		self.assertEqual(self.p, [("100.100.100.100", 1000)])

	def test_multiple_peers(self):
		""" Test that a two peer list is decoded correctly. """

		self.p = torrent.decode_binary_peers("dddd\x03\xe8dddd\x03\xe8")
		self.assertEqual(self.p, [('100.100.100.100', 1000), \
			('100.100.100.100', 1000)])

class Get_Peers(unittest.TestCase):
	""" Test that get_peers() dispatches correctly. """

	def test_binary_list(self):
		""" Test that a binary list is dispatched correctly. """

		self.p = torrent.get_peers("dddd\x03\xe8")
		self.assertEqual(self.p, [("100.100.100.100", 1000)])

	def test_expanded_list(self):
		""" Test that an expanded list is dispatched correctly. """

		self.p = torrent.get_peers( \
			[{'ip': '100.100.100.100', 'peer id': 'test1', \
				'port': 1000}])
		self.assertEqual(self.p, [("100.100.100.100", 1000)])

class Decode_Port(unittest.TestCase):
	""" Test that decode_port() works correctly. """

	def test_port(self):
		""" Test that the port 6881 is decoded correctly. """

		self.p = torrent.decode_port("\x1a\xe1")
		self.assertEqual(self.p, 6881)

class Generate_Handshake(unittest.TestCase):
	""" Test that generate_handshake() works. """

	def setUp(self):
		""" Generate a handshake. """

		self.info_hash = "test_info_hash"
		self.peer_id = "test_peer_id"
		self.h = torrent.generate_handshake(self.info_hash, \
			self.peer_id)

	def test_length_protocol(self):
		""" Test that the length of the protocol is correct. """

		self.assertEqual("19", self.h[0:2])

	def test_protocol_id(self):
		""" Test the protocol id is correct. """

		self.assertEqual("BitTorrent protocol", self.h[2:21])

	def test_reserved(self):
		""" Test that the reserved bytes are correct. """

		self.assertEqual("00000000", self.h[21:29])

	def test_info_hash(self):
		""" Test that the info hash is correct. """

		self.assertEqual(self.info_hash, \
			self.h[29:29+len(self.info_hash)])

	def test_peer_id(self):
		""" Test that the peer id is correct. """

		self.assertEqual(self.peer_id, self.h[29+len(self.info_hash): \
			29+len(self.info_hash)+len(self.peer_id)])

	def tearDown(self):
		""" Remove the handshake. """

		self.h = None
########NEW FILE########
__FILENAME__ = tracker_tests
#!/usr/bin/env python
# tracker_tests.py -- tests for the bittorrent tracker

import unittest
import tracker
import os
import pickle

class Decode_Request(unittest.TestCase):
	""" Test that we can decode GET requests correctly. """

	def test_simple_request(self):
		""" Test that a simple request is decoded correctly. """

		self.n = tracker.decode_request("?key=value")
		self.assertEqual(self.n, {"key":["value"]})

	def test_slash_at_start(self):
		""" Test that if the request has a slash to start, that it is
		removed as well. """

		self.n = tracker.decode_request("/?key=value")
		self.assertEqual(self.n, {"key":["value"]})

class Add_Peer(unittest.TestCase):
	""" Test that peers are correctly added to the tracker database. """

	def test_unique_peer(self):
		""" Test that a unique peer is added correctly. """

		self.db = {}
		tracker.add_peer(self.db, \
			"test_hash", "test", "100.100.100.100", 1000)
		self.assertEqual(self.db, \
			{'test_hash': [('test', '100.100.100.100', 1000)]})

	def test_duplicate_peer(self):
		""" Test that a duplicated peer is not added. """

		self.db = {'test_hash': [('test', '100.100.100.100', 1000)]}
		tracker.add_peer(self.db, \
			"test_hash", "test", "100.100.100.100", 1000)
		self.assertEqual(self.db, \
			{'test_hash': [('test', '100.100.100.100', 1000)]})

class Make_Compact_Peer_List(unittest.TestCase):
	""" Test that a compact peer list is correctly made. """

	def test_empty_peer(self):
		""" Test that an empty peer list works. """

		self.n = tracker.make_compact_peer_list([])
		self.assertEqual(self.n, "")

	def test_one_peer(self):
		""" Test that one peer works correctly. """

		self.n = tracker.make_compact_peer_list \
			([("test1", "100.100.100.100", "1000")])
		self.assertEqual(self.n, "dddd\x03\xe8")

	def test_multiple_peers(self):
		""" Test that multiple peers works correctly. """

		self.n = tracker.make_compact_peer_list \
			([("test1", "100.100.100.100", "1000"), \
				("test2", "100.100.100.100", "1000")])
		self.assertEqual(self.n, "dddd\x03\xe8dddd\x03\xe8")

class Make_Expanded_Peer_List(unittest.TestCase):
	""" Test that an expanded peer list is correctly made. """

	def test_empty_peer(self):
		""" Test that an empty peer list works correctly. """

		self.n = tracker.make_peer_list([])
		self.assertEqual(self.n, [])

	def test_one_peer(self):
		""" Test that one peer works correctly. """

		self.n = tracker.make_peer_list \
			([("test1", "100.100.100.100", "1000")])
		self.assertEqual(self.n, [{'ip': '100.100.100.100', \
			'peer id': 'test1', 'port': 1000}])

	def test_multiple_peers(self):
		""" Test that multiple peers works correctly. """

		self.n = tracker.make_peer_list \
			([("test1", "100.100.100.100", "1000"), \
				("test2", "100.100.100.100", "1000")])
		self.assertEqual(self.n, [{'ip': '100.100.100.100', \
			'peer id': 'test1', 'port': 1000}, \
				{'ip': '100.100.100.100', \
					'peer id': 'test2', 'port': 1000}])

class Peer_List(unittest.TestCase):
	""" Test that peer_list() dispatcher works correctly. """

	def test_compact_list(self):
		""" Test that a compact peer list dispatches. """

		self.n = tracker.peer_list([("test1", "100.100.100.100", \
			"1000")], True)
		self.assertEqual(self.n, "dddd\x03\xe8")

	def test_expanded_list(self):
		""" Test that an expanded list dispatches. """

		self.n = tracker.peer_list([("test1", "100.100.100.100", \
			"1000")], False)
		self.assertEqual(self.n, [{'ip': '100.100.100.100', \
			'peer id': 'test1', 'port': 1000}])

class Tracker_Test(unittest.TestCase):
	""" Test that the Tracker() class works correctly. """

	def setUp(self):
		""" Start the tracker. """

		self.port = 8888
		self.inmemory = True
		self.interval =10

		self.tracker = tracker.Tracker(port = self.port, \
			inmemory = self.inmemory, \
			interval = self.interval)

	def test_port(self):
		""" Test that the port is correct. """

		self.assertEqual(self.port, self.tracker.port)

	def test_inmemory(self):
		""" Test that inmemory is correct. """

		self.assertEqual(self.inmemory, self.tracker.inmemory)

	def test_interval(self):
		""" Test that the interval is correct. """

		self.assertEqual(self.interval, self.tracker.server_class.interval)

	def tearDown(self):
		""" Stop the tracker. """

		self.tracker = None

########NEW FILE########
__FILENAME__ = util_tests
#!/usr/bin/env python
# util_tests.py -- testing the util module

import unittest
import util

class Collapse(unittest.TestCase):
	""" Check the function collapse() works correctly. """

	def test_concatenation(self):
		""" Test that characters are correctly concatenated. """

		self.n = util.collapse(["t", "e", "s", "t"])
		self.assertEqual(self.n, "test")

	def test_exception_raised(self):
		""" Test a TypeError is raised when concating different types. """

		self.assertRaises(TypeError, util.collapse, [1, "a", True])

class Slice(unittest.TestCase):
	""" Check the function slice() works correctly. """

	def test_simple(self):
		""" Test that a small string slices correctly. """

		self.n = util.slice("abc", 1)
		self.assertEqual(self.n, ["a", "b", "c"])

	def test_longer(self):
		""" Test that a larger string slice works correctly. """

		self.n = util.slice("abcdef", 2)
		self.assertEqual(self.n, ["ab", "cd", "ef"])

	def test_too_long(self):
		""" Test that a string too long works fine. """

		self.n = util.slice("abcd", 6)
		self.assertEqual(self.n, ["abcd"])
########NEW FILE########
__FILENAME__ = torrent
# torrent.py
# Torrent file related utilities

from hashlib import md5, sha1
from random import choice
import socket
from struct import pack, unpack
from threading import Thread
from time import sleep, time
import types
from urllib import urlencode, urlopen
from util import collapse, slice

from bencode import decode, encode

CLIENT_NAME = "pytorrent"
CLIENT_ID = "PY"
CLIENT_VERSION = "0001"

def make_info_dict(file):
	""" Returns the info dictionary for a torrent file. """

	with open(file) as f:
		contents = f.read()

	piece_length = 524288	# TODO: This should change dependent on file size

	info = {}

	info["piece length"] = piece_length
	info["length"] = len(contents)
	info["name"] = file
	info["md5sum"] = md5(contents).hexdigest()

	# Generate the pieces
	pieces = slice(contents, piece_length)
	pieces = [ sha1(p).digest() for p in pieces ]
	info["pieces"] = collapse(pieces)

	return info

def make_torrent_file(file = None, tracker = None, comment = None):
	""" Returns the bencoded contents of a torrent file. """

	if not file:
		raise TypeError("make_torrent_file requires at least one file, non given.")
	if not tracker:
		raise TypeError("make_torrent_file requires at least one tracker, non given.")

	torrent = {}

	# We only have one tracker, so that's the announce
	if type(tracker) != list:
		torrent["announce"] = tracker
	# Multiple trackers, first is announce, and all go in announce-list
	elif type(tracker) == list:
		torrent["announce"] = tracker[0]
		# And for some reason, each needs its own list
		torrent["announce-list"] = [[t] for t in tracker]

	torrent["creation date"] = int(time())
	torrent["created by"] = CLIENT_NAME
	if comment:
		torrent["comment"] = comment

	torrent["info"] = make_info_dict(file)

	return encode(torrent)

def write_torrent_file(torrent = None, file = None, tracker = None, \
	comment = None):
	""" Largely the same as make_torrent_file(), except write the file
	to the file named in torrent. """

	if not torrent:
		raise TypeError("write_torrent_file() requires a torrent filename to write to.")

	data = make_torrent_file(file = file, tracker = tracker, \
		comment = comment)
	with open(torrent, "w") as torrent_file:
		torrent_file.write(data)

def read_torrent_file(torrent_file):
	""" Given a .torrent file, returns its decoded contents. """

	with open(torrent_file) as file:
		return decode(file.read())

def generate_peer_id():
	""" Returns a 20-byte peer id. """

	# As Azureus style seems most popular, we'll be using that.
	# Generate a 12 character long string of random numbers.
	random_string = ""
	while len(random_string) != 12:
		random_string = random_string + choice("1234567890")

	return "-" + CLIENT_ID + CLIENT_VERSION + "-" + random_string

def make_tracker_request(info, peer_id, tracker_url):
	""" Given a torrent info, and tracker_url, returns the tracker
	response. """

	# Generate a tracker GET request.
	payload = {"info_hash" : info,
			"peer_id" : peer_id,
			"port" : 6881,
			"uploaded" : 0,
			"downloaded" : 0,
			"left" : 1000,
			"compact" : 1}
	payload = urlencode(payload)

	# Send the request
	response = urlopen(tracker_url + "?" + payload).read()

	return decode(response)

def decode_expanded_peers(peers):
	""" Return a list of IPs and ports, given an expanded list of peers,
	from a tracker response. """

	return [(p["ip"], p["port"]) for p in peers]

def decode_binary_peers(peers):
	""" Return a list of IPs and ports, given a binary list of peers,
	from a tracker response. """

	peers = slice(peers, 6)	# Cut the response at the end of every peer
	return [(socket.inet_ntoa(p[:4]), decode_port(p[4:])) for p in peers]

def get_peers(peers):
	""" Dispatches peer list to decode binary or expanded peer list. """

	if type(peers) == str:
		return decode_binary_peers(peers)
	elif type(peers) == list:
		return decode_expanded_peers(peers)

def decode_port(port):
	""" Given a big-endian encoded port, returns the numerical port. """

	return unpack(">H", port)[0]

def generate_handshake(info_hash, peer_id):
	""" Returns a handshake. """

	protocol_id = "BitTorrent protocol"
	len_id = str(len(protocol_id))
	reserved = "00000000"

	return len_id + protocol_id + reserved + info_hash + peer_id

def send_recv_handshake(handshake, host, port):
	""" Sends a handshake, returns the data we get back. """

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((host, port))
	s.send(handshake)

	data = s.recv(len(handshake))
	s.close()

	return data

class Torrent():
	def __init__(self, torrent_file):
		self.running = False

		self.data = read_torrent_file(torrent_file)

		self.info_hash = sha1(encode(self.data["info"])).digest()
		self.peer_id = generate_peer_id()
		self.handshake = generate_handshake(self.info_hash, self.peer_id)

	def perform_tracker_request(self, url, info_hash, peer_id):
		""" Make a tracker request to url, every interval seconds, using
		the info_hash and peer_id, and decode the peers on a good response. """

		while self.running:
			self.tracker_response = make_tracker_request(info_hash, peer_id, url)

			if "failure reason" not in self.tracker_response:
				self.peers = get_peers(self.tracker_response["peers"])
			sleep(self.tracker_response["interval"])

	def run(self):
		""" Start the torrent running. """

		if not self.running:
			self.running = True

			self.tracker_loop = Thread(target = self.perform_tracker_request, \
				args = (self.data["announce"], self.info_hash, self.peer_id))
			self.tracker_loop.start()

	def stop(self):
		""" Stop the torrent from running. """

		if self.running:
			self.running = False

			self.tracker_loop.join()


########NEW FILE########
__FILENAME__ = tracker
# pytorrent-tracker.py
# A bittorrent tracker

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from logging import basicConfig, info, INFO
from pickle import dump, load
from socket import inet_aton
from struct import pack
from urllib import urlopen
from urlparse import parse_qs

from bencode import encode
from simpledb import Database

def decode_request(path):
	""" Return the decoded request string. """

	# Strip off the start characters
	if path[:1] == "?":
		path = path[1:]
	elif path[:2] == "/?":
		path = path[2:]

	return parse_qs(path)

def add_peer(torrents, info_hash, peer_id, ip, port):
	""" Add the peer to the torrent database. """

	# If we've heard of this, just add the peer
	if info_hash in torrents:
		# Only add the peer if they're not already in the database
		if (peer_id, ip, port) not in torrents[info_hash]:
			torrents[info_hash].append((peer_id, ip, port))
	# Otherwise, add the info_hash and the peer
	else:
		torrents[info_hash] = [(peer_id, ip, port)]

def make_compact_peer_list(peer_list):
	""" Return a compact peer string, given a list of peer details. """

	peer_string = ""
	for peer in peer_list:
		ip = inet_aton(peer[1])
		port = pack(">H", int(peer[2]))

		peer_string += (ip + port)

	return peer_string

def make_peer_list(peer_list):
	""" Return an expanded peer list suitable for the client, given
	the peer list. """

	peers = []
	for peer in peer_list:
		p = {}
		p["peer id"] = peer[0]
		p["ip"] = peer[1]
		p["port"] = int(peer[2])

		peers.append(p)

	return peers

def peer_list(peer_list, compact):
	""" Depending on compact, dispatches to compact or expanded peer
	list functions. """

	if compact:
		return make_compact_peer_list(peer_list)
	else:
		return make_peer_list(peer_list)

class RequestHandler(BaseHTTPRequestHandler):
	def do_GET(s):
		""" Take a request, do some some database work, return a peer
		list response. """

		# Decode the request
		package = decode_request(s.path)

		if not package:
			s.send_error(403)
			return

		# Get the necessary info out of the request
		info_hash = package["info_hash"][0]
		compact = bool(package["compact"][0])
		ip = s.client_address[0]
		port = package["port"][0]
		peer_id = package["peer_id"][0]

		add_peer(s.server.torrents, info_hash, peer_id, ip, port)

		# Generate a response
		response = {}
		response["interval"] = s.server.interval
		response["complete"] = 0
		response["incomplete"] = 0
		response["peers"] = peer_list( \
		s.server.torrents[info_hash], compact)

		# Send off the response
		s.send_response(200)
		s.end_headers()
		s.wfile.write(encode(response))

		# Log the request, and what we send back
		info("PACKAGE: %s", package)
		info("RESPONSE: %s", response)

	def log_message(self, format, *args):
		""" Just supress logging. """

		return

class Tracker():
	def __init__(self, host = "", port = 9010, interval = 5, \
		torrent_db = "tracker.db", log = "tracker.log", \
		inmemory = True):
		""" Read in the initial values, load the database. """

		self.host = host
		self.port = port

		self.inmemory = inmemory

		self.server_class = HTTPServer
		self.httpd = self.server_class((self.host, self.port), \
			RequestHandler)

		self.running = False	# We're not running to begin with

		self.server_class.interval = interval

		# Set logging info
		basicConfig(filename = log, level = INFO)

		# If not in memory, give the database a file, otherwise it
		# will stay in memory
		if not self.inmemory:
			self.server_class.torrents = Database(torrent_db)
		else:
			self.server_class.torrents = Database(None)

	def runner(self):
		""" Keep handling requests, until told to stop. """

		while self.running:
			self.httpd.handle_request()

	def run(self):
		""" Start the runner, in a seperate thread. """

		if not self.running:
			self.running = True

			self.thread = Thread(target = self.runner)
			self.thread.start()

	def send_dummy_request(self):
		""" Send a dummy request to the server. """

		# To finish off httpd.handle_request()
		address = "http://127.0.0.1:" + str(self.port)
		urlopen(address)

	def stop(self):
		""" Stop the thread, and join to it. """

		if self.running:
			self.running = False

			self.send_dummy_request()
			self.thread.join()

	def __del__(self):
		""" Stop the tracker thread, write the database. """

		self.stop()
		self.httpd.server_close()
########NEW FILE########
__FILENAME__ = util
# util.py
# A small collection of useful functions

def collapse(data):
	""" Given an homogenous list, returns the items of that list
	concatenated together. """

	return reduce(lambda x, y: x + y, data)

def slice(string, n):
	""" Given a string and a number n, cuts the string up, returns a
	list of strings, all size n. """

	temp = []
	i = n
	while i <= len(string):
		temp.append(string[(i-n):i])
		i += n

	try:	# Add on any stragglers
		if string[(i-n)] != "":
			temp.append(string[(i-n):])
	except IndexError:
		pass

	return temp
########NEW FILE########
