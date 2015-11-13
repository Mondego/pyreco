__FILENAME__ = test_unirest
# -*- coding:utf-8 -*-

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import unirest

class UnirestTestCase(unittest.TestCase):
	def test_get(self):
		response = unirest.get('http://httpbin.org/get?name=Mark', params={"nick":"thefosk"})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 2)
		self.assertEqual(response.body['args']['name'], "Mark")
		self.assertEqual(response.body['args']['nick'], "thefosk")

	def test_get_unicode_param(self):
		response = unirest.get('http://httpbin.org/get?name=Shimada', params={"nick":u"しまりん"})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 2)
		self.assertEqual(response.body['args']['name'], "Shimada")
		self.assertEqual(response.body['args']['nick'], u"しまりん")

	def test_get_none_param(self):
		response = unirest.get('http://httpbin.org/get?name=Mark', params={"nick":"thefosk", "age": None, "third":""})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 3)
		self.assertEqual(response.body['args']['name'], "Mark")
		self.assertEqual(response.body['args']['nick'], "thefosk")
		self.assertEqual(response.body['args']['third'], "")

	def test_post(self):
		response = unirest.post('http://httpbin.org/post', params={"name":"Mark", "nick":"thefosk"})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 0)
		self.assertEqual(len(response.body['form']), 2)
		self.assertEqual(response.body['form']['name'], "Mark")
		self.assertEqual(response.body['form']['nick'], "thefosk")

	def test_post_none_param(self):
		response = unirest.post('http://httpbin.org/post', params={"name":"Mark", "nick":"thefosk", "age": None, "third":""})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 0)
		self.assertEqual(len(response.body['form']), 3)
		self.assertEqual(response.body['form']['name'], "Mark")
		self.assertEqual(response.body['form']['nick'], "thefosk")
		self.assertEqual(response.body['form']['third'], "")

	def test_delete(self):
		response = unirest.delete('http://httpbin.org/delete', params={"name":"Mark", "nick":"thefosk"})
		self.assertEqual(response.code, 200)
		self.assertEqual(response.body['data'], "nick=thefosk&name=Mark")

	def test_put(self):
		response = unirest.put('http://httpbin.org/put', params={"name":"Mark", "nick":"thefosk"})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 0)
		self.assertEqual(len(response.body['form']), 2)
		self.assertEqual(response.body['form']['name'], "Mark")
		self.assertEqual(response.body['form']['nick'], "thefosk")

	def test_patch(self):
		response = unirest.patch('http://httpbin.org/patch', params={"name":"Mark", "nick":"thefosk"})
		self.assertEqual(response.code, 200)
		self.assertEqual(len(response.body['args']), 0)
		self.assertEqual(len(response.body['form']), 2)
		self.assertEqual(response.body['form']['name'], "Mark")
		self.assertEqual(response.body['form']['nick'], "thefosk")

	def test_post_entity(self):
		response = unirest.post('http://httpbin.org/post', params="hello this is custom data")
		self.assertEqual(response.code, 200)
		self.assertEqual(response.body['data'], "hello this is custom data")

	def test_gzip(self):
		response = unirest.get('http://httpbin.org/gzip', params={"name":"Mark"})
		self.assertEqual(response.code, 200)
		self.assertTrue(response.body['gzipped'])

	def test_basicauth(self):
		response = unirest.get('http://httpbin.org/get', auth=('marco', 'password'))
		self.assertEqual(response.code, 200)
		self.assertEqual(response.body['headers']['Authorization'], "Basic bWFyY286cGFzc3dvcmQ=")

	def test_defaultheaders(self):
		unirest.default_header('custom','custom header')
		response = unirest.get('http://httpbin.org/get')
		self.assertEqual(response.code, 200)
		self.assertTrue('Custom' in response.body['headers']);
		self.assertEqual(response.body['headers']['Custom'], "custom header")

		# Make another request
		response = unirest.get('http://httpbin.org/get')
		self.assertEqual(response.code, 200)
		self.assertTrue('Custom' in response.body['headers']);
		self.assertTrue(response.body['headers']['Custom'], "custom header")

		# Clear the default headers
		unirest.clear_default_headers()
		response = unirest.get('http://httpbin.org/get')
		self.assertEqual(response.code, 200)
		self.assertFalse('Custom' in response.body['headers']);

	def test_timeout(self):
		unirest.timeout(3)
		response = unirest.get('http://httpbin.org/delay/1')
		self.assertEqual(response.code, 200)

		unirest.timeout(1)
		try:
			response = unirest.get('http://httpbin.org/delay/3')
			self.fail("The timeout didn't work")
		except:
								pass

if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = utils
from poster.encode import multipart_encode


def to_utf8(value):
    if isinstance(value, unicode):
        return value.encode('utf-8')
    return value


def _dictionary_encoder(key, dictionary):
    result = []
    for k, v in dictionary.iteritems():
        if type(v) is file:
            continue
        key = to_utf8(key)
        k = to_utf8(k)
        v = to_utf8(v)
        result.append('{}[{}]={}'.format(key, k, v))

    return result


def dict2query(dictionary):
    """
    We want post vars of form:
    {'foo': 'bar', 'nested': {'a': 'b', 'c': 'd'}}
    to become:
    foo=bar&nested[a]=b&nested[c]=d
    """
    query = []
    encoders = {dict: _dictionary_encoder}
    for k, v in dictionary.iteritems():
        if v.__class__ in encoders:
            nested_query = encoders[v.__class__](k, v)
            query += nested_query
        else:
            key = to_utf8(k)
            value = to_utf8(v)
            query.append('{}={}'.format(key, value))

    return '&'.join(query)


def urlencode(data):
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, file):
                return multipart_encode(data)
        return dict2query(data), None
    else:
        return data, None


if __name__ == '__main__':
    print '...'
    print dict2query({'foo': 'bar', 'nested': {'a': 'b', 'c': 'd'}})

########NEW FILE########
