__FILENAME__ = acfun
#!/usr/bin/env python

__all__ = ['acfun_download']

import re
from common import *
#from iask import iask_download_by_id
from youku import youku_download_by_id
from tudou import tudou_download_by_iid
from qq import qq_download_by_id
import json

def get_srt_json(id):
	url = 'http://comment.acfun.tv/%s.json' % id
	return get_html(url)

def acfun_download_by_id(id, title, merge=True):
	info = json.loads(get_html('http://www.acfun.tv/api/getVideoByID.aspx?vid=' + id))
	t = info['vtype']
	vid = info['vid']
	if t == 'sina':
		iask_download_by_id(vid, title, merge=merge)
	elif t == 'youku':
		youku_download_by_id(vid, title, merge=merge)
	elif t == 'tudou':
		tudou_download_by_iid(vid, title, merge=merge)
	elif t == 'qq':
		qq_download_by_id(vid, title, merge=merge)
	else:
		raise NotImplementedError(t)

	srt = get_srt_json(vid)
	with open(title + '.json', 'w') as x:
		x.write(srt)

def acfun_download(url, merge=True):
	assert re.match(r'http://www.acfun.tv/v/ac(\d+)', url)
	html = get_html(url).decode('utf-8')

	title = r1(r'<h1 id="title-article" class="title"[^<>]*>([^<>]+)</h1>', html)
	assert title
	title = unescape_html(title)
	title = escape_file_path(title)
	title = title.replace(' - AcFun.tv', '')

	id = r1(r"\[[Vv]ideo\](\d+)\[/[Vv]ideo\]", html)
	if id:
		return acfun_download_by_id(id, title, merge=merge)
	id = r1(r'<embed [^<>]* (?:src|flashvars)="[^"]+id=(\d+)[^"]+"', html)
	assert id
	iask_download_by_id(id, title, merge=merge)

def video_info(id):
	url = 'http://platform.sina.com.cn/playurl/t_play?app_key=1917945218&vid=%s' % id
	xml = get_decoded_html(url)
	urls = re.findall(r'<url>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</url>', xml)
	name = r1(r'<vname>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vname>', xml)
	vstr = r1(r'<vstr>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vstr>', xml)
	return urls, name, vstr

def iask_download_by_id(id, title=None, merge=True):
	urls, name, vstr = video_info(id)
	title = title or name
	assert title
	download_urls(urls, title, 'flv', total_size=None, merge=merge)



download = acfun_download
download_playlist = playlist_not_supported('acfun')

def main():
	script_main('acfun', acfun_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = bilibili
#!/usr/bin/env python

__all__ = ['bilibili_download']

import re
from common import *
from iask import iask_download_by_id
from youku import youku_download_by_id
from tudou import tudou_download_by_id

def get_srt_xml(id):
	url = 'http://comment.bilibili.tv/%s.xml' % id
	return get_html(url).decode('utf-8')

def parse_srt_p(p):
	fields = p.split(',')
	assert len(fields) == 8, fields
	time, mode, font_size, font_color, pub_time, pool, user_id, history = fields
	time = float(time)

	mode = int(mode)
	assert 1 <= mode <= 8
	# mode 1~3: scrolling
	# mode 4: bottom
	# mode 5: top
	# mode 6: reverse?
	# mode 7: position
	# mode 8: advanced

	pool = int(pool)
	assert 0 <= pool <= 2
	# pool 0: normal
	# pool 1: srt
	# pool 2: special?
	
	font_size = int(font_size)

	font_color = '#%06x' % int(font_color)

	return pool, mode, font_size, font_color

def parse_srt_xml(xml):
	d = re.findall(r'<d p="([^"]+)">(.*)</d>', xml)
	for x, y in d:
		p = parse_srt_p(x)
	raise NotImplementedError()

def parse_cid_playurl(xml):
	from xml.dom.minidom import parseString
	doc = parseString(xml.encode('utf-8'))
	urls = [durl.getElementsByTagName('url')[0].firstChild.nodeValue for durl in doc.getElementsByTagName('durl')]
	return urls

def bilibili_download_by_cid(id, title, merge=True):
	url = 'http://interface.bilibili.tv/playurl?cid=' + id
	urls = parse_cid_playurl(get_html(url, 'utf-8'))
	if re.search(r'\.(flv|hlv)\b', urls[0]):
		download_urls(urls, title, 'flv', total_size=None, merge=merge)
	elif re.search(r'/mp4/', urls[0]):
		download_urls(urls, title, 'mp4', total_size=None, merge=merge)
	else:
		raise NotImplementedError(urls[0])

def bilibili_download(url, merge=True):
	assert re.match(r'http://(www.bilibili.tv|bilibili.kankanews.com|bilibili.smgbb.cn)/video/av(\d+)', url)
	html = get_html(url)

	title = r1(r'<h2>([^<>]+)</h2>', html).decode('utf-8')
	title = unescape_html(title)
	title = escape_file_path(title)

	flashvars = r1_of([r'flashvars="([^"]+)"', r'"https://secure.bilibili.tv/secure,(cid=\d+)(?:&aid=\d+)?"'], html)
	assert flashvars
	t, id = flashvars.split('=', 1)
	id = id.split('&')[0]
	if t == 'cid':
		bilibili_download_by_cid(id, title, merge=merge)
	elif t == 'vid':
		iask_download_by_id(id, title, merge=merge)
	elif t == 'ykid':
		youku_download_by_id(id, title, merge=merge)
	elif t == 'uid':
		tudou_download_by_id(id, title, merge=merge)
	else:
		raise NotImplementedError(flashvars)

	xml = get_srt_xml(id)
	with open(title + '.xml', 'w') as x:
		x.write(xml.encode('utf-8'))

download = bilibili_download
download_playlist = playlist_not_supported('bilibili')

def main():
	script_main('bilibili', bilibili_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = cntv
#!/usr/bin/env python

__all__ = ['cntv_download', 'cntv_download_by_id']

from common import *
import json
import re

def cntv_download_by_id(id, title=None, output_dir='.', merge=True):
	assert id
	info = json.loads(get_html('http://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid='+id).decode('utf-8'))
	title = title or info['title']
	video = info['video']
	alternatives = [x for x in video.keys() if x.startswith('chapters')]
	assert alternatives in (['chapters'], ['chapters', 'chapters2']), alternatives
	chapters = video['chapters2'] if 'chapters2' in video else video['chapters']
	urls = [x['url'] for x in chapters]
	ext = r1(r'\.([^.]+)$', urls[0])
	assert ext in ('flv', 'mp4')
	download_urls(urls, title, str(ext), total_size=None, merge=merge)

def cntv_download(url, merge=True):
	if re.match(r'http://\w+\.cntv\.cn/(\w+/\w+/(classpage/video/)?)?\d+/\d+\.shtml', url):
		id = r1(r'<!--repaste.video.code.begin-->(\w+)<!--repaste.video.code.end-->', get_html(url))
	elif re.match(r'http://xiyou.cntv.cn/v-[\w-]+\.html', url):
		id = r1(r'http://xiyou.cntv.cn/v-([\w-]+)\.html', url)
	else:
		raise NotImplementedError(url)
	cntv_download_by_id(id, merge=merge)

download = cntv_download
download_playlist = playlist_not_supported('cntv')

def main():
	script_main('cntv', cntv_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = common

import urllib2
import os.path
import sys
import re

default_encoding = sys.getfilesystemencoding()
if default_encoding.lower() == 'ascii':
	default_encoding = 'utf-8'

def to_native_string(s):
	if type(s) == unicode:
		return s.encode(default_encoding)
	else:
		return s

def r1(pattern, text):
	m = re.search(pattern, text)
	if m:
		return m.group(1)

def r1_of(patterns, text):
	for p in patterns:
		x = r1(p, text)
		if x:
			return x

def unescape_html(html):
	import xml.sax.saxutils
	html = xml.sax.saxutils.unescape(html)
	html = re.sub(r'&#(\d+);', lambda x: unichr(int(x.group(1))), html)
	return html

def ungzip(s):
	from StringIO import StringIO
	import gzip
	buffer = StringIO(s)
	f = gzip.GzipFile(fileobj=buffer)
	return f.read()

def undeflate(s):
	import zlib
	return zlib.decompress(s, -zlib.MAX_WBITS)

def get_response(url):
	response = urllib2.urlopen(url)
	data = response.read()
	if response.info().get('Content-Encoding') == 'gzip':
		data = ungzip(data)
	elif response.info().get('Content-Encoding') == 'deflate':
		data = undeflate(data)
	response.data = data
	return response

def get_html(url, encoding=None):
	content = get_response(url).data
	if encoding:
		content = content.decode(encoding)
	return content

def get_decoded_html(url):
	response = get_response(url)
	data = response.data
	charset = r1(r'charset=([\w-]+)', response.headers['content-type'])
	if charset:
		return data.decode(charset)
	else:
		return data

def url_save(url, filepath, bar, refer=None):
	headers = {}
	if refer:
		headers['Referer'] = refer
	request = urllib2.Request(url, headers=headers)
	response = urllib2.urlopen(request)
	file_size = int(response.headers['content-length'])
	assert file_size
	if os.path.exists(filepath):
		if file_size == os.path.getsize(filepath):
			if bar:
				bar.done()
			print 'Skip %s: file already exists' % os.path.basename(filepath)
			return
		else:
			if bar:
				bar.done()
			print 'Overwriting', os.path.basename(filepath), '...'
	with open(filepath, 'wb') as output:
		received = 0
		while True:
			buffer = response.read(1024*256)
			if not buffer:
				break
			received += len(buffer)
			output.write(buffer)
			if bar:
				bar.update_received(len(buffer))
	assert received == file_size == os.path.getsize(filepath), '%s == %s == %s' % (received, file_size, os.path.getsize(filepath))

def url_size(url):
	request = urllib2.Request(url)
	request.get_method = lambda: 'HEAD'
	response = urllib2.urlopen(request)
	size = int(response.headers['content-length'])
	return size

def url_size(url):
	size = int(urllib2.urlopen(url).headers['content-length'])
	return size

def urls_size(urls):
	return sum(map(url_size, urls))

class SimpleProgressBar:
	def __init__(self, total_size, total_pieces=1):
		self.displayed = False
		self.total_size = total_size
		self.total_pieces = total_pieces
		self.current_piece = 1
		self.received = 0
	def update(self):
		self.displayed = True
		bar_size = 40
		percent = self.received*100.0/self.total_size
		if percent > 100:
			percent = 100.0
		bar_rate = 100.0 / bar_size
		dots = percent / bar_rate
		dots = int(dots)
		plus = percent / bar_rate - dots
		if plus > 0.8:
			plus = '='
		elif plus > 0.4:
			plus = '-'
		else:
			plus = ''
		bar = '=' * dots + plus
		bar = '{0:>3.0f}% [{1:<40}] {2}/{3}'.format(percent, bar, self.current_piece, self.total_pieces)
		sys.stdout.write('\r'+bar)
		sys.stdout.flush()
	def update_received(self, n):
		self.received += n
		self.update()
	def update_piece(self, n):
		self.current_piece = n
	def done(self):
		if self.displayed:
			print
			self.displayed = False

class PiecesProgressBar:
	def __init__(self, total_size, total_pieces=1):
		self.displayed = False
		self.total_size = total_size
		self.total_pieces = total_pieces
		self.current_piece = 1
		self.received = 0
	def update(self):
		self.displayed = True
		bar = '{0:>3}%[{1:<40}] {2}/{3}'.format('?', '?'*40, self.current_piece, self.total_pieces)
		sys.stdout.write('\r'+bar)
		sys.stdout.flush()
	def update_received(self, n):
		self.received += n
		self.update()
	def update_piece(self, n):
		self.current_piece = n
	def done(self):
		if self.displayed:
			print
			self.displayed = False

class DummyProgressBar:
	def __init__(self, *args):
		pass
	def update_received(self, n):
		pass
	def update_piece(self, n):
		pass
	def done(self):
		pass

def escape_file_path(path):
	path = path.replace('/', '-')
	path = path.replace('\\', '-')
	path = path.replace('*', '-')
	path = path.replace('?', '-')
	return path

def download_urls(urls, title, ext, total_size, output_dir='.', refer=None, merge=True):
	assert urls
	assert ext in ('flv', 'mp4')
	if not total_size:
		try:
			total_size = urls_size(urls)
		except:
			import traceback
			import sys
			traceback.print_exc(file=sys.stdout)
			pass
	title = to_native_string(title)
	title = escape_file_path(title)
	filename = '%s.%s' % (title, ext)
	filepath = os.path.join(output_dir, filename)
	if total_size:
		if os.path.exists(filepath) and os.path.getsize(filepath) >= total_size * 0.9:
			print 'Skip %s: file already exists' % filepath
			return
		bar = SimpleProgressBar(total_size, len(urls))
	else:
		bar = PiecesProgressBar(total_size, len(urls))
	if len(urls) == 1:
		url = urls[0]
		print 'Downloading %s ...' % filename
		url_save(url, filepath, bar, refer=refer)
		bar.done()
	else:
		flvs = []
		print 'Downloading %s.%s ...' % (title, ext)
		for i, url in enumerate(urls):
			filename = '%s[%02d].%s' % (title, i, ext)
			filepath = os.path.join(output_dir, filename)
			flvs.append(filepath)
			#print 'Downloading %s [%s/%s]...' % (filename, i+1, len(urls))
			bar.update_piece(i+1)
			url_save(url, filepath, bar, refer=refer)
		bar.done()
		if not merge:
			return
		if ext == 'flv':
			from flv_join import concat_flvs
			concat_flvs(flvs, os.path.join(output_dir, title+'.flv'))
			for flv in flvs:
				os.remove(flv)
		elif ext == 'mp4':
			from mp4_join import concat_mp4s
			concat_mp4s(flvs, os.path.join(output_dir, title+'.mp4'))
			for flv in flvs:
				os.remove(flv)
		else:
			print "Can't join %s files" % ext

def playlist_not_supported(name):
	def f(*args, **kwargs):
		raise NotImplementedError('Play list is not supported for '+name)
	return f

def script_main(script_name, download, download_playlist=None):
	if download_playlist:
		help = 'python %s.py [--playlist] [-c|--create-dir] [--no-merge] url ...' % script_name
		short_opts = 'hc'
		opts = ['help', 'playlist', 'create-dir', 'no-merge']
	else:
		help = 'python [--no-merge] %s.py url ...' % script_name
		short_opts = 'h'
		opts = ['help', 'no-merge']
	import sys, getopt
	try:
		opts, args = getopt.getopt(sys.argv[1:], short_opts, opts)
	except getopt.GetoptError, err:
		print help
		sys.exit(1)
	playlist = False
	create_dir = False
	merge = True
	for o, a in opts:
		if o in ('-h', '--help'):
			print help
			sys.exit()
		elif o in ('--playlist',):
			playlist = True
		elif o in ('-c', '--create-dir'):
			create_dir = True
		elif o in ('--no-merge'):
			merge = False
		else:
			print help
			sys.exit(1)
	if not args:
		print help
		sys.exit(1)

	for url in args:
		if playlist:
			download_playlist(url, create_dir=create_dir, merge=merge)
		else:
			download(url, merge=merge)


########NEW FILE########
__FILENAME__ = flv_join
#!/usr/bin/env python

import struct
from cStringIO import StringIO

TAG_TYPE_METADATA = 18

##################################################
# AMF0
##################################################

AMF_TYPE_NUMBER = 0x00
AMF_TYPE_BOOLEAN = 0x01
AMF_TYPE_STRING = 0x02
AMF_TYPE_OBJECT = 0x03
AMF_TYPE_MOVIECLIP = 0x04
AMF_TYPE_NULL = 0x05
AMF_TYPE_UNDEFINED = 0x06
AMF_TYPE_REFERENCE = 0x07
AMF_TYPE_MIXED_ARRAY = 0x08
AMF_TYPE_END_OF_OBJECT = 0x09
AMF_TYPE_ARRAY = 0x0A
AMF_TYPE_DATE = 0x0B
AMF_TYPE_LONG_STRING = 0x0C
AMF_TYPE_UNSUPPORTED = 0x0D
AMF_TYPE_RECORDSET = 0x0E
AMF_TYPE_XML = 0x0F
AMF_TYPE_CLASS_OBJECT = 0x10
AMF_TYPE_AMF3_OBJECT = 0x11

class ECMAObject:
	def __init__(self, max_number):
		self.max_number = max_number
		self.data = []
		self.map = {}
	def put(self, k, v):
		self.data.append((k, v))
		self.map[k] = v
	def get(self, k):
		return self.map[k]
	def set(self, k, v):
		for i in range(len(self.data)):
			if self.data[i][0] == k:
				self.data[i] = (k, v)
				break
		else:
			raise KeyError(k)
		self.map[k] = v
	def keys(self):
		return self.map.keys()
	def __str__(self):
		return 'ECMAObject<'+repr(self.map)+'>'
	def __eq__(self, other):
		return self.max_number == other.max_number and self.data == other.data

def read_amf_number(stream):
	return struct.unpack('>d', stream.read(8))[0]

def read_amf_boolean(stream):
	b = read_byte(stream)
	assert b in (0, 1)
	return bool(b)

def read_amf_string(stream):
	xx = stream.read(2)
	if xx == '':
		# dirty fix for the invalid Qiyi flv
		return None
	n = struct.unpack('>H', xx)[0]
	s = stream.read(n)
	assert len(s) == n
	return s.decode('utf-8')

def read_amf_object(stream):
	obj = {}
	while True:
		k = read_amf_string(stream)
		if not k:
			assert read_byte(stream) == AMF_TYPE_END_OF_OBJECT
			break
		v = read_amf(stream)
		obj[k] = v
	return obj

def read_amf_mixed_array(stream):
	max_number = read_uint(stream)
	mixed_results = ECMAObject(max_number)
	while True:
		k = read_amf_string(stream)
		if k is None:
			# dirty fix for the invalid Qiyi flv
			break
		if not k:
			assert read_byte(stream) == AMF_TYPE_END_OF_OBJECT
			break
		v = read_amf(stream)
		mixed_results.put(k, v)
	assert len(mixed_results.data) == max_number
	return mixed_results

def read_amf_array(stream):
	n = read_uint(stream)
	v = []
	for i in range(n):
		v.append(read_amf(stream))
	return v

amf_readers = {
		AMF_TYPE_NUMBER: read_amf_number,
		AMF_TYPE_BOOLEAN: read_amf_boolean,
		AMF_TYPE_STRING: read_amf_string,
		AMF_TYPE_OBJECT: read_amf_object,
		AMF_TYPE_MIXED_ARRAY: read_amf_mixed_array,
		AMF_TYPE_ARRAY: read_amf_array,
}

def read_amf(stream):
	return amf_readers[read_byte(stream)](stream)

def write_amf_number(stream, v):
	stream.write(struct.pack('>d', v))

def write_amf_boolean(stream, v):
	if v:
		stream.write('\x01')
	else:
		stream.write('\x00')

def write_amf_string(stream, s):
	s = s.encode('utf-8')
	stream.write(struct.pack('>H', len(s)))
	stream.write(s)

def write_amf_object(stream, o):
	for k in o:
		write_amf_string(stream, k)
		write_amf(stream, o[k])
	write_amf_string(stream, '')
	write_byte(stream, AMF_TYPE_END_OF_OBJECT)

def write_amf_mixed_array(stream, o):
	write_uint(stream, o.max_number)
	for k, v in o.data:
		write_amf_string(stream, k)
		write_amf(stream, v)
	write_amf_string(stream, '')
	write_byte(stream, AMF_TYPE_END_OF_OBJECT)

def write_amf_array(stream, o):
	write_uint(stream, len(o))
	for v in o:
		write_amf(stream, v)

amf_writers_tags = {
		float: AMF_TYPE_NUMBER,
		bool: AMF_TYPE_BOOLEAN,
		unicode: AMF_TYPE_STRING,
		dict: AMF_TYPE_OBJECT,
		ECMAObject: AMF_TYPE_MIXED_ARRAY,
		list: AMF_TYPE_ARRAY,
}

amf_writers = {
		AMF_TYPE_NUMBER: write_amf_number,
		AMF_TYPE_BOOLEAN: write_amf_boolean,
		AMF_TYPE_STRING: write_amf_string,
		AMF_TYPE_OBJECT: write_amf_object,
		AMF_TYPE_MIXED_ARRAY: write_amf_mixed_array,
		AMF_TYPE_ARRAY: write_amf_array,
}

def write_amf(stream, v):
	if isinstance(v, ECMAObject):
		tag = amf_writers_tags[ECMAObject]
	else:
		tag = amf_writers_tags[type(v)]
	write_byte(stream, tag)
	amf_writers[tag](stream, v)

##################################################
# FLV
##################################################

def read_int(stream):
	return struct.unpack('>i', stream.read(4))[0]

def read_uint(stream):
	return struct.unpack('>I', stream.read(4))[0]

def write_uint(stream, n):
	stream.write(struct.pack('>I', n))

def read_byte(stream):
	return ord(stream.read(1))

def write_byte(stream, b):
	stream.write(chr(b))

def read_unsigned_medium_int(stream):
	x1, x2, x3 = struct.unpack('BBB', stream.read(3))
	return (x1 << 16) | (x2 << 8) | x3

def read_tag(stream):
	# header size: 15 bytes
	header = stream.read(15)
	if len(header) == 4:
		return
	x = struct.unpack('>IBBBBBBBBBBB', header)
	previous_tag_size = x[0]
	data_type = x[1]
	body_size = (x[2] << 16) | (x[3] << 8) | x[4]
	assert body_size < 1024*1024*128, 'tag body size too big (> 128MB)'
	timestamp = (x[5] << 16) | (x[6] << 8) | x[7]
	timestamp += x[8] << 24
	assert x[9:] == (0, 0, 0)
	body = stream.read(body_size)
	return (data_type, timestamp, body_size, body, previous_tag_size)
	#previous_tag_size = read_uint(stream)
	#data_type = read_byte(stream)
	#body_size = read_unsigned_medium_int(stream)
	#assert body_size < 1024*1024*128, 'tag body size too big (> 128MB)'
	#timestamp = read_unsigned_medium_int(stream)
	#timestamp += read_byte(stream) << 24
	#assert read_unsigned_medium_int(stream) == 0
	#body = stream.read(body_size)
	#return (data_type, timestamp, body_size, body, previous_tag_size)

def write_tag(stream, tag):
	data_type, timestamp, body_size, body, previous_tag_size = tag
	write_uint(stream, previous_tag_size)
	write_byte(stream, data_type)
	write_byte(stream, body_size>>16 & 0xff)
	write_byte(stream, body_size>>8  & 0xff)
	write_byte(stream, body_size     & 0xff)
	write_byte(stream, timestamp>>16 & 0xff)
	write_byte(stream, timestamp>>8  & 0xff)
	write_byte(stream, timestamp     & 0xff)
	write_byte(stream, timestamp>>24 & 0xff)
	stream.write('\0\0\0')
	stream.write(body)

def read_flv_header(stream):
	assert stream.read(3) == 'FLV'
	header_version = read_byte(stream)
	assert header_version == 1
	type_flags = read_byte(stream)
	assert type_flags == 5
	data_offset = read_uint(stream)
	assert data_offset == 9

def write_flv_header(stream):
	stream.write('FLV')
	write_byte(stream, 1)
	write_byte(stream, 5)
	write_uint(stream, 9)

def read_meta_data(stream):
	meta_type = read_amf(stream)
	meta = read_amf(stream)
	return meta_type, meta

def read_meta_tag(tag):
	data_type, timestamp, body_size, body, previous_tag_size = tag
	assert data_type == TAG_TYPE_METADATA
	assert timestamp == 0
	assert previous_tag_size == 0
	return read_meta_data(StringIO(body))

def write_meta_data(stream, meta_type, meta_data):
	assert isinstance(meta_type, basesting)
	write_amf(meta_type)
	write_amf(meta_data)

def write_meta_tag(stream, meta_type, meta_data):
	buffer = StringIO()
	write_amf(buffer, meta_type)
	write_amf(buffer, meta_data)
	body = buffer.getvalue()
	write_tag(stream, (TAG_TYPE_METADATA, 0, len(body), body, 0))


##################################################
# main
##################################################

def guess_output(inputs):
	import os.path
	inputs = map(os.path.basename, inputs)
	n = min(map(len, inputs))
	for i in reversed(range(1, n)):
		if len(set(s[:i] for s in inputs)) == 1:
			return inputs[0][:i] + '.flv'
	return 'output.flv'

def concat_flvs(flvs, output=None):
	assert flvs, 'no flv file found'
	import os.path
	if not output:
		output = guess_output(flvs)
	elif os.path.isdir(output):
		output = os.path.join(output, guess_output(flvs))

	print 'Joining %s into %s' % (', '.join(flvs), output)
	ins = [open(flv, 'rb') for flv in flvs]
	for stream in ins:
		read_flv_header(stream)
	meta_tags = map(read_tag, ins)
	metas = map(read_meta_tag, meta_tags)
	meta_types, metas = zip(*metas)
	assert len(set(meta_types)) == 1
	meta_type = meta_types[0]

	# must merge fields: duration
	# TODO: check other meta info, update other meta info
	total_duration = sum(meta.get('duration') for meta in metas)
	meta_data = metas[0]
	meta_data.set('duration', total_duration)

	out = open(output, 'wb')
	write_flv_header(out)
	write_meta_tag(out, meta_type, meta_data)
	timestamp_start = 0
	for stream in ins:
		while True:
			tag = read_tag(stream)
			if tag:
				data_type, timestamp, body_size, body, previous_tag_size = tag
				timestamp += timestamp_start
				tag = data_type, timestamp, body_size, body, previous_tag_size
				write_tag(out, tag)
			else:
				break
		timestamp_start = timestamp
	write_uint(out, previous_tag_size)

	return output

def usage():
	print 'python flv_join.py --output target.flv flv...'

def main():
	import sys, getopt
	try:
		opts, args = getopt.getopt(sys.argv[1:], "ho:", ["help", "output="])
	except getopt.GetoptError, err:
		usage()
		sys.exit(1)
	output = None
	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit()
		elif o in ("-o", "--output"):
			output = a
		else:
			usage()
			sys.exit(1)
	if not args:
		usage()
		sys.exit(1)

	concat_flvs(args, output)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = iask
#!/usr/bin/env python

__all__ = ['iask_download', 'iask_download_by_id']

import re
from common import *

def video_info(id):
	xml = get_decoded_html('http://v.iask.com/v_play.php?vid=%s' % id)
	urls = re.findall(r'<url>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</url>', xml)
	name = r1(r'<vname>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vname>', xml)
	vstr = r1(r'<vstr>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</vstr>', xml)
	return urls, name, vstr

def iask_download_by_id(id, title=None, merge=True):
	urls, name, vstr = video_info(id)
	title = title or name
	assert title
	download_urls(urls, title, 'flv', total_size=None, merge=merge)

def iask_download(url, merge=True):
	id = r1(r'vid:(\d+),', get_html(url))
	iask_download_by_id(id, merge=merge)

download = iask_download
download_playlist = playlist_not_supported('iask')

def main():
	script_main('iask', iask_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = ifeng
#!/usr/bin/env python

__all__ = ['ifeng_download', 'ifeng_download_by_id']

from common import *

def ifeng_download_by_id(id, title=None, merge=True):
	assert r1(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', id), id
	url = 'http://v.ifeng.com/video_info_new/%s/%s/%s.xml' % (id[-2], id[-2:], id)
	xml = get_html(url, 'utf-8')
	title = r1(r'Name="([^"]+)"', xml)
	title = unescape_html(title)
	url = r1(r'VideoPlayUrl="([^"]+)"', xml)
	from random import randint
	r = randint(10, 19)
	url = url.replace('http://video.ifeng.com/', 'http://video%s.ifeng.com/' % r)
	assert url.endswith('.mp4')
	download_urls([url], title, 'mp4', total_size=None, merge=merge)

def ifeng_download(url, merge=True):
	id = r1(r'/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.shtml$', url)
	if id:
		return ifeng_download_by_id(id)
	html = get_html(url)
	id = r1(r'var vid="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', html)
	assert id, "can't find video info"
	return ifeng_download_by_id(id)

download = ifeng_download
download_playlist = playlist_not_supported('ifeng')

def main():
	script_main('ifeng', ifeng_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = iqiyi
#!/usr/bin/env python

__all__ = ['iqiyi_download']

import re
from common import *

def real_url(url):
	import time
	import json
	return json.loads(get_html(url[:-3]+'hml?v='+str(int(time.time()) + 1921658928)))['l'] # XXX: what is 1921658928?

def iqiyi_download(url, merge=True):
	html = get_html(url)
	#title = r1(r'title\s*:\s*"([^"]+)"', html)
	#title = unescape_html(title).decode('utf-8')
	#videoId = r1(r'videoId\s*:\s*"([^"]+)"', html)
	#pid = r1(r'pid\s*:\s*"([^"]+)"', html)
	#ptype = r1(r'ptype\s*:\s*"([^"]+)"', html)
	#info_url = 'http://cache.video.qiyi.com/v/%s/%s/%s/' % (videoId, pid, ptype)
	videoId = r1(r'''videoId\s*[:=]\s*["']([^"']+)["']''', html)
	assert videoId
	info_url = 'http://cache.video.qiyi.com/v/%s' % videoId
	info_xml = get_html(info_url)

	from xml.dom.minidom import parseString
	doc = parseString(info_xml)
	title = doc.getElementsByTagName('title')[0].firstChild.nodeValue
	size = int(doc.getElementsByTagName('totalBytes')[0].firstChild.nodeValue)
	urls = [n.firstChild.nodeValue for n in doc.getElementsByTagName('file')]
	assert urls[0].endswith('.f4v'), urls[0]
	urls = map(real_url, urls)
	download_urls(urls, title, 'flv', total_size=size, merge=merge)

download = iqiyi_download
download_playlist = playlist_not_supported('iqiyi')

def main():
	script_main('iqiyi', iqiyi_download)

if __name__ == '__main__':
	main()




########NEW FILE########
__FILENAME__ = ku6
#!/usr/bin/env python

__all__ = ['ku6_download', 'ku6_download_by_id']

import json
import re
from common import *

def ku6_download_by_id(id, title=None, output_dir='.', merge=True):
	data = json.loads(get_html('http://v.ku6.com/fetchVideo4Player/%s...html'%id))['data']
	t = data['t']
	f = data['f']
	size = int(data['videosize'])
	title = title or t
	assert title
	urls = f.split(',')
	ext = re.sub(r'.*\.', '', urls[0])
	assert ext in ('flv', 'mp4', 'f4v'), ext
	ext = {'f4v':'flv'}.get(ext, ext)
	download_urls(urls, title, ext, total_size=size, merge=merge)

def ku6_download(url, merge=True):
	id = r1(r'http://v.ku6.com/special/show_\d+/(.*)\.\.\.html', url)
	ku6_download_by_id(id, merge=merge)

download = ku6_download
download_playlist = playlist_not_supported('ku6')

def main():
	script_main('ku6', ku6_download)

if __name__ == '__main__':
	main()



########NEW FILE########
__FILENAME__ = mp4_join
#!/usr/bin/env python

# reference: c041828_ISO_IEC_14496-12_2005(E).pdf

##################################################
# reader and writer
##################################################

import struct
from cStringIO import StringIO

def skip(stream, n):
	stream.seek(stream.tell() + n)

def skip_zeros(stream, n):
	assert stream.read(n) == '\x00' * n

def read_int(stream):
	return struct.unpack('>i', stream.read(4))[0]

def read_uint(stream):
	return struct.unpack('>I', stream.read(4))[0]

def write_uint(stream, n):
	stream.write(struct.pack('>I', n))

def read_ushort(stream):
	return struct.unpack('>H', stream.read(2))[0]

def read_ulong(stream):
	return struct.unpack('>Q', stream.read(8))[0]

def read_byte(stream):
	return ord(stream.read(1))

def copy_stream(source, target, n):
	buffer_size = 1024*1024
	while n > 0:
		to_read = min(buffer_size, n)
		s = source.read(to_read)
		assert len(s) == to_read, 'no enough data'
		target.write(s)
		n -= to_read

class Atom:
	def __init__(self, type, size, body):
		assert len(type) == 4
		self.type = type
		self.size = size
		self.body = body
	def __str__(self):
		#return '<Atom(%s):%s>' % (self.type, repr(self.body))
		return '<Atom(%s):%s>' % (self.type, '')
	def __repr__(self):
		return str(self)
	def write1(self, stream):
		write_uint(stream, self.size)
		stream.write(self.type)
	def write(self, stream):
		assert type(self.body) == str, '%s: %s' % (self.type, type(self.body))
		assert self.size == 8 + len(self.body)
		self.write1(stream)
		stream.write(self.body)
	def calsize(self):
		return self.size

class CompositeAtom(Atom):
	def __init__(self, type, size, body):
		assert isinstance(body, list)
		Atom.__init__(self, type, size, body)
	def write(self, stream):
		assert type(self.body) == list
		self.write1(stream)
		for atom in self.body:
			atom.write(stream)
	def calsize(self):
		self.size = 8 + sum([atom.calsize() for atom in self.body])
		return self.size
	def get1(self, k):
		for a in self.body:
			if a.type == k:
				return a
		else:
			raise Exception('atom not found: '+k)
	def get(self, *keys):
		atom = self
		for k in keys:
			atom = atom.get1(k)
		return atom
	def get_all(self, k):
		return filter(lambda x: x.type == k, self.body)

class VariableAtom(Atom):
	def __init__(self, type, size, body, variables):
		assert isinstance(body, str)
		Atom.__init__(self, type, size, body)
		self.variables = variables
	def write(self, stream):
		self.write1(stream)
		i = 0
		n = 0
		for name, offset, value in self.variables:
			stream.write(self.body[i:offset])
			write_uint(stream, value)
			n += offset - i + 4
			i = offset + 4
		stream.write(self.body[i:])
		n += len(self.body) - i
		assert n == len(self.body)
	def get(self, k):
		for v in self.variables:
			if v[0] == k:
				return v[2]
		else:
			raise Exception('field not found: '+k)
	def set(self, k, v):
		for i in range(len(self.variables)):
			variable = self.variables[i]
			if variable[0] == k:
				self.variables[i] = (k, variable[1], v)
				break
		else:
			raise Exception('field not found: '+k)

def read_raw(stream, size, left, type):
	assert size == left + 8
	body = stream.read(left)
	return Atom(type, size, body)

def read_body_stream(stream, left):
	body = stream.read(left)
	assert len(body) == left
	return body, StringIO(body)

def read_full_atom(stream):
	value = read_uint(stream)
	version = value >> 24
	flags = value & 0xffffff
	assert version == 0
	return value

def read_mvhd(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	# new Date(movieTime * 1000 - 2082850791998L); 
	creation_time = read_uint(stream)
	modification_time = read_uint(stream)
	time_scale = read_uint(stream)
	duration = read_uint(stream)
	left -= 16

	qt_preferred_fate = read_uint(stream)
	qt_preferred_volume = read_ushort(stream)
	assert stream.read(10) == '\x00' * 10
	qt_matrixA = read_uint(stream)
	qt_matrixB = read_uint(stream)
	qt_matrixU = read_uint(stream)
	qt_matrixC = read_uint(stream)
	qt_matrixD = read_uint(stream)
	qt_matrixV = read_uint(stream)
	qt_matrixX = read_uint(stream)
	qt_matrixY = read_uint(stream)
	qt_matrixW = read_uint(stream)
	qt_previewTime = read_uint(stream)
	qt_previewDuration = read_uint(stream)
	qt_posterTime = read_uint(stream)
	qt_selectionTime = read_uint(stream)
	qt_selectionDuration = read_uint(stream)
	qt_currentTime = read_uint(stream)
	nextTrackID = read_uint(stream)
	left -= 80
	assert left == 0
	return VariableAtom('mvhd', size, body, [('duration', 16, duration)])

def read_tkhd(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	# new Date(movieTime * 1000 - 2082850791998L); 
	creation_time = read_uint(stream)
	modification_time = read_uint(stream)
	track_id = read_uint(stream)
	assert stream.read(4) == '\x00' * 4
	duration = read_uint(stream)
	left -= 20

	assert stream.read(8) == '\x00' * 8
	qt_layer = read_ushort(stream)
	qt_alternate_group = read_ushort(stream)
	qt_volume = read_ushort(stream)
	assert stream.read(2) == '\x00\x00'
	qt_matrixA = read_uint(stream)
	qt_matrixB = read_uint(stream)
	qt_matrixU = read_uint(stream)
	qt_matrixC = read_uint(stream)
	qt_matrixD = read_uint(stream)
	qt_matrixV = read_uint(stream)
	qt_matrixX = read_uint(stream)
	qt_matrixY = read_uint(stream)
	qt_matrixW = read_uint(stream)
	qt_track_width = read_uint(stream)
	width = qt_track_width >> 16
	qt_track_height = read_uint(stream)
	height = qt_track_height >> 16
	left -= 60
	assert left == 0
	return VariableAtom('tkhd', size, body, [('duration', 20, duration)])

def read_mdhd(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	# new Date(movieTime * 1000 - 2082850791998L); 
	creation_time = read_uint(stream)
	modification_time = read_uint(stream)
	time_scale = read_uint(stream)
	duration = read_uint(stream)
	left -= 16

	packed_language = read_ushort(stream)
	qt_quality = read_ushort(stream)
	left -= 4

	assert left == 0
	return VariableAtom('mdhd', size, body, [('duration', 16, duration)])

def read_hdlr(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	qt_component_type = read_uint(stream)
	handler_type = read_uint(stream)
	qt_component_manufacturer = read_uint(stream)
	qt_component_flags = read_uint(stream)
	qt_component_flags_mask = read_uint(stream)
	left -= 20

	track_name = stream.read(left - 1)
	assert stream.read(1) == '\x00'

	return Atom('hdlr', size, body)

def read_vmhd(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	assert left == 8
	graphic_mode = read_ushort(stream)
	op_color_read = read_ushort(stream)
	op_color_green = read_ushort(stream)
	op_color_blue = read_ushort(stream)

	return Atom('vmhd', size, body)

def read_stsd(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	left -= 4

	children = []
	for i in range(entry_count):
		atom = read_atom(stream)
		children.append(atom)
		left -= atom.size

	assert left == 0
	#return Atom('stsd', size, children)
	class stsd_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for atom in self.body[1]:
				atom.write(stream)
		def calsize(self):
			oldsize = self.size # TODO: remove
			self.size = 8 + 4 + 4 + sum([atom.calsize() for atom in self.body[1]])
			assert oldsize == self.size, '%s: %d, %d' % (self.type, oldsize, self.size) # TODO: remove
			return self.size
	return stsd_atom('stsd', size, (value, children))

def read_avc1(stream, size, left, type):
	body, stream = read_body_stream(stream, left)

	skip_zeros(stream, 6)
	data_reference_index = read_ushort(stream)
	skip_zeros(stream, 2)
	skip_zeros(stream, 2)
	skip_zeros(stream, 12)
	width = read_ushort(stream)
	height = read_ushort(stream)
	horizontal_rez = read_uint(stream) >> 16
	vertical_rez = read_uint(stream) >> 16
	assert stream.read(4) == '\x00' * 4
	frame_count = read_ushort(stream)
	string_len = read_byte(stream)
	compressor_name = stream.read(31)
	depth = read_ushort(stream)
	assert stream.read(2) == '\xff\xff'
	left -= 78

	child = read_atom(stream)
	assert child.type in ('avcC', 'pasp'), 'if the sub atom is not avcC or pasp (actual %s), you should not cache raw body' % child.type
	left -= child.size
	stream.read(left) # XXX
	return Atom('avc1', size, body)

def read_avcC(stream, size, left, type):
	stream.read(left)
	return Atom('avcC', size, None)

def read_stts(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	assert entry_count == 1
	left -= 4

	samples = []
	for i in range(entry_count):
		sample_count = read_uint(stream)
		sample_duration = read_uint(stream)
		samples.append((sample_count, sample_duration))
		left -= 8
	
	assert left == 0
	#return Atom('stts', size, None)
	class stts_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for sample_count, sample_duration in self.body[1]:
				write_uint(stream, sample_count)
				write_uint(stream, sample_duration)
		def calsize(self):
			oldsize = self.size # TODO: remove
			self.size = 8 + 4 + 4 + len(self.body[1]) * 8
			assert oldsize == self.size, '%s: %d, %d' % (self.type, oldsize, self.size) # TODO: remove
			return self.size
	return stts_atom('stts', size, (value, samples))

def read_stss(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	left -= 4

	samples = []
	for i in range(entry_count):
		sample = read_uint(stream)
		samples.append(sample)
		left -= 4
	
	assert left == 0
	#return Atom('stss', size, None)
	class stss_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for sample in self.body[1]:
				write_uint(stream, sample)
		def calsize(self):
			self.size = 8 + 4 + 4 + len(self.body[1]) * 4
			return self.size
	return stss_atom('stss', size, (value, samples))

def read_stsc(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	left -= 4

	chunks = []
	for i in range(entry_count):
		first_chunk = read_uint(stream)
		samples_per_chunk = read_uint(stream)
		sample_description_index = read_uint(stream)
		assert sample_description_index == 1 # what is it?
		chunks.append((first_chunk, samples_per_chunk, sample_description_index))
		left -= 12
	#chunks, samples = zip(*chunks)
	#total = 0
	#for c, s in zip(chunks[1:], samples):
	#	total += c*s
	#print 'total', total
	
	assert left == 0
	#return Atom('stsc', size, None)
	class stsc_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for first_chunk, samples_per_chunk, sample_description_index in self.body[1]:
				write_uint(stream, first_chunk)
				write_uint(stream, samples_per_chunk)
				write_uint(stream, sample_description_index)
		def calsize(self):
			self.size = 8 + 4 + 4 + len(self.body[1]) * 12
			return self.size
	return stsc_atom('stsc', size, (value, chunks))

def read_stsz(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	sample_size = read_uint(stream)
	sample_count = read_uint(stream)
	left -= 8

	assert sample_size == 0
	total = 0
	sizes = []
	if sample_size == 0:
		for i in range(sample_count):
			entry_size = read_uint(stream)
			sizes.append(entry_size)
			total += entry_size
			left -= 4

	assert left == 0
	#return Atom('stsz', size, None)
	class stsz_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, self.body[1])
			write_uint(stream, self.body[2])
			for entry_size in self.body[3]:
				write_uint(stream, entry_size)
		def calsize(self):
			self.size = 8 + 4 + 8 + len(self.body[3]) * 4
			return self.size
	return stsz_atom('stsz', size, (value, sample_size, sample_count, sizes))

def read_stco(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	left -= 4

	offsets = []
	for i in range(entry_count):
		chunk_offset = read_uint(stream)
		offsets.append(chunk_offset)
		left -= 4
	
	assert left == 0
	#return Atom('stco', size, None)
	class stco_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for chunk_offset in self.body[1]:
				write_uint(stream, chunk_offset)
		def calsize(self):
			self.size = 8 + 4 + 4 + len(self.body[1]) * 4
			return self.size
	return stco_atom('stco', size, (value, offsets))

def read_ctts(stream, size, left, type):
	value = read_full_atom(stream)
	left -= 4

	entry_count = read_uint(stream)
	left -= 4

	samples = []
	for i in range(entry_count):
		sample_count = read_uint(stream)
		sample_offset = read_uint(stream)
		samples.append((sample_count, sample_offset))
		left -= 8
	
	assert left == 0
	class ctts_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			write_uint(stream, self.body[0])
			write_uint(stream, len(self.body[1]))
			for sample_count, sample_offset in self.body[1]:
				write_uint(stream, sample_count)
				write_uint(stream, sample_offset)
		def calsize(self):
			self.size = 8 + 4 + 4 + len(self.body[1]) * 8
			return self.size
	return ctts_atom('ctts', size, (value, samples))

def read_smhd(stream, size, left, type):
	body, stream = read_body_stream(stream, left)
	value = read_full_atom(stream)
	left -= 4

	balance = read_ushort(stream)
	assert stream.read(2) == '\x00\x00'
	left -= 4

	assert left == 0
	return Atom('smhd', size, body)

def read_mp4a(stream, size, left, type):
	body, stream = read_body_stream(stream, left)

	assert stream.read(6) == '\x00' * 6
	data_reference_index = read_ushort(stream)
	assert stream.read(8) == '\x00' * 8
	channel_count = read_ushort(stream)
	sample_size = read_ushort(stream)
	assert stream.read(4) == '\x00' * 4
	time_scale = read_ushort(stream)
	assert stream.read(2) == '\x00' * 2
	left -= 28

	atom = read_atom(stream)
	assert atom.type == 'esds'
	left -= atom.size

	assert left == 0
	return Atom('mp4a', size, body)

def read_descriptor(stream):
	tag = read_byte(stream)
	raise NotImplementedError()

def read_esds(stream, size, left, type):
	value = read_uint(stream)
	version = value >> 24
	assert version == 0
	flags = value & 0xffffff
	left -= 4

	body = stream.read(left)
	return Atom('esds', size, None)

def read_composite_atom(stream, size, left, type):
	children = []
	while left > 0:
		atom = read_atom(stream)
		children.append(atom)
		left -= atom.size
	assert left == 0, left
	return CompositeAtom(type, size, children)

def read_mdat(stream, size, left, type):
	source_start = stream.tell()
	source_size = left
	skip(stream, left)
	#return Atom(type, size, None)
	#raise NotImplementedError()
	class mdat_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			self.write2(stream)
		def write2(self, stream):
			source, source_start, source_size = self.body
			original = source.tell()
			source.seek(source_start)
			copy_stream(source, stream, source_size)
		def calsize(self):
			return self.size
	return mdat_atom('mdat', size, (stream, source_start, source_size))

atom_readers = {
	'mvhd': read_mvhd, # merge duration
	'tkhd': read_tkhd, # merge duration
	'mdhd': read_mdhd, # merge duration
	'hdlr': read_hdlr, # nothing
	'vmhd': read_vmhd, # nothing
	'stsd': read_stsd, # nothing
	'avc1': read_avc1, # nothing
	'avcC': read_avcC, # nothing
	'stts': read_stts, # sample_count, sample_duration
	'stss': read_stss, # join indexes
	'stsc': read_stsc, # merge # sample numbers
	'stsz': read_stsz, # merge # samples
	'stco': read_stco, # merge # chunk offsets
	'ctts': read_ctts, # merge
	'smhd': read_smhd, # nothing
	'mp4a': read_mp4a, # nothing
	'esds': read_esds, # noting

	'ftyp': read_raw,
	'yqoo': read_raw,
	'moov': read_composite_atom,
	'trak': read_composite_atom,
	'mdia': read_composite_atom,
	'minf': read_composite_atom,
	'dinf': read_composite_atom,
	'stbl': read_composite_atom,
	'iods': read_raw,
	'dref': read_raw,
	'free': read_raw,
	'edts': read_raw,
	'pasp': read_raw,

	'mdat': read_mdat,
}
#stsd sample descriptions (codec types, initialization etc.) 
#stts (decoding) time-to-sample  
#ctts (composition) time to sample 
#stsc sample-to-chunk, partial data-offset information 
#stsz sample sizes (framing) 
#stz2 compact sample sizes (framing) 
#stco chunk offset, partial data-offset information 
#co64 64-bit chunk offset 
#stss sync sample table (random access points) 
#stsh shadow sync sample table 
#padb sample padding bits 
#stdp sample degradation priority 
#sdtp independent and disposable samples 
#sbgp sample-to-group 
#sgpd sample group description 
#subs sub-sample information


def read_atom(stream):
	header = stream.read(8)
	if not header:
		return
	assert len(header) == 8
	n = 0
	size = struct.unpack('>I', header[:4])[0]
	assert size > 0
	n += 4
	type = header[4:8]
	n += 4
	assert type != 'uuid'
	if size == 1:
		size = read_ulong(stream)
		n += 8

	left = size - n
	if type in atom_readers:
		return atom_readers[type](stream, size, left, type)
	raise NotImplementedError('%s: %d' % (type, left))

def write_atom(stream, atom):
	atom.write(stream)

def parse_atoms(stream):
	atoms = []
	while True:
		atom = read_atom(stream)
		if atom:
			atoms.append(atom)
		else:
			break
	return atoms

def read_mp4(stream):
	atoms = parse_atoms(stream)
	moov = filter(lambda x: x.type == 'moov', atoms)
	mdat = filter(lambda x: x.type == 'mdat', atoms)
	assert len(moov) == 1
	assert len(mdat) == 1
	moov = moov[0]
	mdat = mdat[0]
	return atoms, moov, mdat

##################################################
# merge
##################################################

def merge_stts(samples_list):
	sample_list = []
	for samples in samples_list:
		assert len(samples) == 1
		sample_list.append(samples[0])
	counts, durations = zip(*sample_list)
	assert len(set(durations)) == 1, 'not all durations equal'
	return [(sum(counts), durations[0])]

def merge_stss(samples, sample_number_list):
	results = []
	start = 0
	for samples, sample_number_list in zip(samples, sample_number_list):
		results.extend(map(lambda x: start + x, samples))
		start += sample_number_list
	return results

def merge_stsc(chunks_list, total_chunk_number_list):
	results = []
	chunk_index = 1
	for chunks, total in zip(chunks_list, total_chunk_number_list):
		for i in range(len(chunks)):
			if i < len(chunks) - 1:
				chunk_number = chunks[i+1][0] - chunks[i][0]
			else:
				chunk_number = total + 1 - chunks[i][0]
			sample_number = chunks[i][1]
			description = chunks[i][2]
			results.append((chunk_index, sample_number, description))
			chunk_index += chunk_number
	return results

def merge_stco(offsets_list, mdats):
	offset = 0
	results = []
	for offsets, mdat in zip(offsets_list, mdats):
		results.extend(offset + x - mdat.body[1] for x in offsets)
		offset += mdat.size - 8
	return results

def merge_stsz(sizes_list):
	return sum(sizes_list, [])

def merge_mdats(mdats):
	total_size = sum(x.size - 8 for x in mdats) + 8
	class multi_mdat_atom(Atom):
		def __init__(self, type, size, body):
			Atom.__init__(self, type, size, body)
		def write(self, stream):
			self.write1(stream)
			self.write2(stream)
		def write2(self, stream):
			for mdat in self.body:
				mdat.write2(stream)
		def calsize(self):
			return self.size
	return multi_mdat_atom('mdat', total_size, mdats)

def merge_moov(moovs, mdats):
	mvhd_duration = 0
	for x in moovs:
		mvhd_duration += x.get('mvhd').get('duration')
	tkhd_durations = [0, 0]
	mdhd_durations = [0, 0]
	for x in moovs:
		traks = x.get_all('trak')
		assert len(traks) == 2
		tkhd_durations[0] += traks[0].get('tkhd').get('duration')
		tkhd_durations[1] += traks[1].get('tkhd').get('duration')
		mdhd_durations[0] += traks[0].get('mdia', 'mdhd').get('duration')
		mdhd_durations[1] += traks[1].get('mdia', 'mdhd').get('duration')
	#mvhd_duration = min(mvhd_duration, tkhd_durations)

	trak0s = [x.get_all('trak')[0] for x in moovs]
	trak1s = [x.get_all('trak')[1] for x in moovs]

	stts0 = merge_stts(x.get('mdia', 'minf', 'stbl', 'stts').body[1] for x in trak0s)
	stts1 = merge_stts(x.get('mdia', 'minf', 'stbl', 'stts').body[1] for x in trak1s)

	stss = merge_stss((x.get('mdia', 'minf', 'stbl', 'stss').body[1] for x in trak0s), (len(x.get('mdia', 'minf', 'stbl', 'stsz').body[3]) for x in trak0s))

	stsc0 = merge_stsc((x.get('mdia', 'minf', 'stbl', 'stsc').body[1] for x in trak0s), (len(x.get('mdia', 'minf', 'stbl', 'stco').body[1]) for x in trak0s))
	stsc1 = merge_stsc((x.get('mdia', 'minf', 'stbl', 'stsc').body[1] for x in trak1s), (len(x.get('mdia', 'minf', 'stbl', 'stco').body[1]) for x in trak1s))

	stco0 = merge_stco((x.get('mdia', 'minf', 'stbl', 'stco').body[1] for x in trak0s), mdats)
	stco1 = merge_stco((x.get('mdia', 'minf', 'stbl', 'stco').body[1] for x in trak1s), mdats)

	stsz0 = merge_stsz((x.get('mdia', 'minf', 'stbl', 'stsz').body[3] for x in trak0s))
	stsz1 = merge_stsz((x.get('mdia', 'minf', 'stbl', 'stsz').body[3] for x in trak1s))

	ctts = sum((x.get('mdia', 'minf', 'stbl', 'ctts').body[1] for x in trak0s), [])

	moov = moovs[0]

	moov.get('mvhd').set('duration', mvhd_duration)
	trak0 = moov.get_all('trak')[0]
	trak1 = moov.get_all('trak')[1]
	trak0.get('tkhd').set('duration', tkhd_durations[0])
	trak1.get('tkhd').set('duration', tkhd_durations[1])
	trak0.get('mdia', 'mdhd').set('duration', mdhd_durations[0])
	trak1.get('mdia', 'mdhd').set('duration', mdhd_durations[1])

	stts_atom = trak0.get('mdia', 'minf', 'stbl', 'stts')
	stts_atom.body = stts_atom.body[0], stts0
	stts_atom = trak1.get('mdia', 'minf', 'stbl', 'stts')
	stts_atom.body = stts_atom.body[0], stts1

	stss_atom = trak0.get('mdia', 'minf', 'stbl', 'stss')
	stss_atom.body = stss_atom.body[0], stss

	stsc_atom = trak0.get('mdia', 'minf', 'stbl', 'stsc')
	stsc_atom.body = stsc_atom.body[0], stsc0
	stsc_atom = trak1.get('mdia', 'minf', 'stbl', 'stsc')
	stsc_atom.body = stsc_atom.body[0], stsc1

	stco_atom = trak0.get('mdia', 'minf', 'stbl', 'stco')
	stco_atom.body = stss_atom.body[0], stco0
	stco_atom = trak1.get('mdia', 'minf', 'stbl', 'stco')
	stco_atom.body = stss_atom.body[0], stco1

	stsz_atom = trak0.get('mdia', 'minf', 'stbl', 'stsz')
	stsz_atom.body = stsz_atom.body[0], stsz_atom.body[1], len(stsz0), stsz0
	stsz_atom = trak1.get('mdia', 'minf', 'stbl', 'stsz')
	stsz_atom.body = stsz_atom.body[0], stsz_atom.body[1], len(stsz1), stsz1

	ctts_atom = trak0.get('mdia', 'minf', 'stbl', 'ctts')
	ctts_atom.body = ctts_atom.body[0], ctts

	old_moov_size = moov.size
	new_moov_size = moov.calsize()
	new_mdat_start = mdats[0].body[1] + new_moov_size - old_moov_size
	stco0 = map(lambda x: x + new_mdat_start, stco0)
	stco1 = map(lambda x: x + new_mdat_start, stco1)
	stco_atom = trak0.get('mdia', 'minf', 'stbl', 'stco')
	stco_atom.body = stss_atom.body[0], stco0
	stco_atom = trak1.get('mdia', 'minf', 'stbl', 'stco')
	stco_atom.body = stss_atom.body[0], stco1

	return moov

def merge_mp4s(files, output):
	assert files
	ins = [open(mp4, 'rb') for mp4 in files]
	mp4s = map(read_mp4, ins)
	moovs = map(lambda x: x[1], mp4s)
	mdats = map(lambda x: x[2], mp4s)
	moov = merge_moov(moovs, mdats)
	mdat = merge_mdats(mdats)
	with open(output, 'wb') as output:
		for x in mp4s[0][0]:
			if x.type == 'moov':
				moov.write(output)
			elif x.type == 'mdat':
				mdat.write(output)
			else:
				x.write(output)

##################################################
# main
##################################################

# TODO: FIXME: duplicate of flv_join

def guess_output(inputs):
	import os.path
	inputs = map(os.path.basename, inputs)
	n = min(map(len, inputs))
	for i in reversed(range(1, n)):
		if len(set(s[:i] for s in inputs)) == 1:
			return inputs[0][:i] + '.mp4'
	return 'output.mp4'

def concat_mp4s(mp4s, output=None):
	assert mp4s, 'no mp4 file found'
	import os.path
	if not output:
		output = guess_output(mp4s)
	elif os.path.isdir(output):
		output = os.path.join(output, guess_output(mp4s))

	print 'Joining %s into %s' % (', '.join(mp4s), output)
	merge_mp4s(mp4s, output)

	return output

def usage():
	print 'python mp4_join.py --output target.mp4 mp4...'

def main():
	import sys, getopt
	try:
		opts, args = getopt.getopt(sys.argv[1:], "ho:", ["help", "output="])
	except getopt.GetoptError, err:
		usage()
		sys.exit(1)
	output = None
	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit()
		elif o in ("-o", "--output"):
			output = a
		else:
			usage()
			sys.exit(1)
	if not args:
		usage()
		sys.exit(1)

	concat_mp4s(args, output)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = pptv
#!/usr/bin/env python

__all__ = ['pptv_download', 'pptv_download_by_id']

import re
import urllib
from common import *
import hashlib

def pptv_download_by_id(id, merge=True):
	xml = get_html('http://web-play.pptv.com/webplay3-151-%s.xml' % id)
	xml = xml.decode('utf-8')
	host = r1(r'<sh>([^<>]+)</sh>', xml)
	port = 8080
	st = r1(r'<st>([^<>]+)</st>', xml)
	key = hashlib.md5(st).hexdigest() # FIXME: incorrect key
	rids = re.findall(r'rid="([^"]+)"', xml)
	rid = r1(r'rid="([^"]+)"', xml)
	title = r1(r'nm="([^"]+)"', xml)
	pieces = re.findall('<sgm no="(\d+)".*fs="(\d+)"', xml)
	numbers, fs = zip(*pieces)
	urls = ['http://%s:%s/%s/%s?key=%s' % (host, port, i, rid, key) for i in numbers]
	urls = ['http://pptv.vod.lxdns.com/%s/%s?key=%s' % (i, rid, key) for i in numbers]
	total_size = sum(map(int, fs))
	assert rid.endswith('.mp4')
	download_urls(urls, title, 'mp4', total_size=total_size, merge=merge)

def pptv_download(url, merge=True):
	assert re.match(r'http://v.pptv.com/show/(\w+)\.html$', url)
	html = get_html(url)
	id = r1(r'webcfg\s*=\s*{"id":\s*(\d+)', html)
	assert id
	pptv_download_by_id(id, merge=merge)

download = pptv_download
download_playlist = playlist_not_supported('pptv')

def main():
	script_main('pptv', pptv_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = qq
#!/usr/bin/env python

__all__ = ['qq_download_by_id']

import re
from common import *

def qq_download_by_id(id, title, merge=True):
	url = 'http://vsrc.store.qq.com/%s.flv' % id
	assert title
	download_urls([url], title, 'flv', total_size=None, merge=merge)


########NEW FILE########
__FILENAME__ = sohu
#!/usr/bin/env python

__all__ = ['sohu_download']

from common import *

def real_url(host, prot, file, new):
	url = 'http://%s/?prot=%s&file=%s&new=%s' % (host, prot, file, new)
	start, _, host, key, _, _ = get_html(url).split('|')
	return '%s%s?key=%s' % (start[:-1], new, key)

def sohu_download(url, merge=True):
	vid = r1('vid="(\d+)"', get_html(url))
	assert vid
	import json
	data = json.loads(get_decoded_html('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % vid))
	host = data['allot']
	prot = data['prot']
	urls = []
	data = data['data']
	title = data['tvName']
	size = sum(data['clipsBytes'])
	assert len(data['clipsURL']) == len(data['clipsBytes']) == len(data['su'])
	for file, new in zip(data['clipsURL'], data['su']):
		urls.append(real_url(host, prot, file, new))
	assert data['clipsURL'][0].endswith('.mp4')
	download_urls(urls, title, 'mp4', total_size=size, refer=url, merge=merge)

download = sohu_download
download_playlist = playlist_not_supported('sohu')

def main():
	script_main('sohu', sohu_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = tudou
#!/usr/bin/env python

__all__ = ['tudou_download', 'tudou_download_playlist', 'tudou_download_by_id', 'tudou_download_by_iid']

from common import *

def tudou_download_by_iid(iid, title, merge=True):
	xml = get_html('http://v2.tudou.com/v?it=' + iid + '&st=1,2,3,4,99')

	from xml.dom.minidom import parseString
	doc = parseString(xml)
	title = title or doc.firstChild.getAttribute('tt') or doc.firstChild.getAttribute('title')
	urls = [(int(n.getAttribute('brt')), n.firstChild.nodeValue.strip()) for n in doc.getElementsByTagName('f')]

	url = max(urls, key=lambda x:x[0])[1]
	assert 'f4v' in url

	#url_save(url, filepath, bar):
	download_urls([url], title, 'flv', total_size=None, merge=merge)

def tudou_download_by_id(id, title, merge=True):
	html = get_html('http://www.tudou.com/programs/view/%s/' % id)
	iid = r1(r'iid\s*=\s*(\S+)', html)
	tudou_download_by_iid(iid, title, merge=merge)

def tudou_download(url, merge=True):
	html = get_decoded_html(url)
	iid = r1(r'iid\s*[:=]\s*(\d+)', html)
	assert iid
	title = r1(r"kw\s*[:=]\s*'([^']+)'", html)
	assert title
	title = unescape_html(title)
	tudou_download_by_iid(iid, title, merge=merge)

def parse_playlist(url):
	#if r1('http://www.tudou.com/playlist/p/a(\d+)\.html', url):
	#	html = get_html(url)
	#	print re.search(r'<script>var.*?</script>', html, flags=re.S).group()
	#else:
	#	raise NotImplementedError(url)
	raise NotImplementedError()

def parse_playlist(url):
	aid = r1('http://www.tudou.com/playlist/p/a(\d+)(?:i\d+)?\.html', url)
	html = get_decoded_html(url)
	if not aid:
		aid = r1(r"aid\s*[:=]\s*'(\d+)'", html)
	if re.match(r'http://www.tudou.com/albumcover/', url):
		atitle = r1(r"title\s*:\s*'([^']+)'", html)
	elif re.match(r'http://www.tudou.com/playlist/p/', url):
		atitle = r1(r'atitle\s*=\s*"([^"]+)"', html)
	else:
		raise NotImplementedError(url)
	assert aid
	assert atitle
	import json
	#url = 'http://www.tudou.com/playlist/service/getZyAlbumItems.html?aid='+aid
	url = 'http://www.tudou.com/playlist/service/getAlbumItems.html?aid='+aid
	return [(atitle + '-' + x['title'], str(x['itemId'])) for x in json.loads(get_html(url))['message']]

def tudou_download_playlist(url, create_dir=False, merge=True):
	if create_dir:
		raise NotImplementedError('please report a bug so I can implement this')
	videos = parse_playlist(url)
	for i, (title, id) in enumerate(videos):
		print 'Downloading %s of %s videos...' % (i + 1, len(videos))
		tudou_download_by_iid(id, title, merge=merge)

download = tudou_download
download_playlist = tudou_download_playlist

def main():
	script_main('tudou', tudou_download, tudou_download_playlist)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = video_lixian
#!/usr/bin/env python

import youku
import bilibili
import acfun
import iask
import ku6
import pptv
import iqiyi
import tudou
import sohu
import w56
import cntv
import yinyuetai
import ifeng

from common import *
import re

def url_to_module(url):
	site = r1(r'http://([^/]+)/', url)
	assert site, 'invalid url: ' + url
	if site.endswith('.com.cn'):
		site = site[:-3]
	domain = r1(r'(\.[^.]+\.[^.]+)$', site)
	assert domain, 'not supported url: ' + url
	k = r1(r'([^.]+)', domain)
	downloads = {
			'youku':youku,
			'bilibili':bilibili,
			'kankanews':bilibili,
			'smgbb':bilibili,
			'acfun':acfun,
			'iask':iask,
			'sina':iask,
			'ku6':ku6,
			'pptv':pptv,
			'iqiyi':iqiyi,
			'tudou':tudou,
			'sohu':sohu,
			'56':w56,
			'cntv':cntv,
			'yinyuetai':yinyuetai,
			'ifeng':ifeng,
	}
	if k in downloads:
		return downloads[k]
	else:
		raise NotImplementedError(url)

def any_download(url, merge=True):
	m = url_to_module(url)
	m.download(url, merge=merge)

def any_download_playlist(url, create_dir=False, merge=True):
	m = url_to_module(url)
	m.download_playlist(url, create_dir=create_dir, merge=merge)

def main():
	script_main('video_lixian', any_download, any_download_playlist)

if __name__ == '__main__':
	main()



########NEW FILE########
__FILENAME__ = w56
#!/usr/bin/env python

__all__ = ['w56_download', 'w56_download_by_id']

from common import *
import json

def w56_download_by_id(id, title=None, output_dir='.', merge=True):
	info = json.loads(get_html('http://vxml.56.com/json/%s/?src=site'%id))['info']
	title = title or info['Subject']
	assert title
	hd = info['hd']
	assert hd in (0, 1, 2)
	type = ['normal', 'clear', 'super'][hd]
	files = [x for x in info['rfiles'] if x['type'] == type]
	assert len(files) == 1
	size = int(files[0]['filesize'])
	url = files[0]['url']
	ext = r1(r'\.([^.]+)$', url)
	assert ext in ('flv', 'mp4')
	download_urls([url], title, str(ext), total_size=size, merge=merge)

def w56_download(url, merge=True):
	id = r1(r'http://www.56.com/u\d+/v_(\w+).html', url)
	w56_download_by_id(id, merge=merge)

download = w56_download
download_playlist = playlist_not_supported('56')

def main():
	script_main('w56', w56_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = yinyuetai
#!/usr/bin/env python

__all__ = ['yinyuetai_download', 'yinyuetai_download_by_id']

from common import *

def url_info(url):
	request = urllib2.Request(url)
	response = urllib2.urlopen(request)
	headers = response.headers

	type = headers['content-type']
	mapping = {'video/mp4': 'mp4'}
	assert type in mapping, type
	type = mapping[type]

	size = int(headers['content-length'])

	return type, size

def yinyuetai_download_by_id(id, title=None, merge=True):
	assert title
	# XXX: what's the format? it looks not amf
	amf = get_html('http://www.yinyuetai.com/insite/get-video-info?flex=true&videoId=' + id)
	# TODO: run a fully parse instead of text search
	#url = r1(r'(http://flv.yinyuetai.com/uploads/videos/common/\w+\.flv\?t=[a-f0-9]{16})', amf)
	#url = r1(r'http://hc.yinyuetai.com/uploads/videos/common/[A-F0-9]{32}\.mp4\?v=\d{12}', amf)
	url = r1(r'(http://\w+\.yinyuetai\.com/uploads/videos/common/\w+\.(?:flv|mp4)\?(?:sc=[a-f0-9]{16}|v=\d{12}))', amf)
	assert url
	ext, size = url_info(url)
	download_urls([url], title, ext, total_size=size, merge=merge)

def yinyuetai_download(url, merge=True):
	id = r1(r'http://www.yinyuetai.com/video/(\d+)$', url)
	assert id
	html = get_html(url, 'utf-8')
	import urllib
	title = r1(r'<meta property="og:title" content="([^"]+)"/>', html)
	assert title
	title = urllib.unquote(title)
	title = escape_file_path(title)
	yinyuetai_download_by_id(id, title, merge=merge)

download = yinyuetai_download
download_playlist = playlist_not_supported('yinyuetai')

def main():
	script_main('yinyuetai', yinyuetai_download)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = youku
#!/usr/bin/env python
# encoding: utf-8

__all__ = ['youku_download', 'youku_download_playlist', 'youku_download_by_id']

import urllib2
import json
from random import randint
from time import time
import re
import sys
from common import *

def find_video_id_from_url(url):
	patterns = [r'^http://v.youku.com/v_show/id_([\w=]+).html',
	            r'^http://player.youku.com/player.php/sid/([\w=]+)/v.swf',
	            r'^loader\.swf\?VideoIDS=([\w=]+)',
				r'^([\w=]+)$']
	return r1_of(patterns, url)

def find_video_id_from_show_page(url):
	return re.search(r'<div class="btnplay">.*href="([^"]+)"', get_html(url)).group(1)

def youku_url(url):
	id = find_video_id_from_url(url)
	if id:
		return 'http://v.youku.com/v_show/id_%s.html' % id
	if re.match(r'http://www.youku.com/show_page/id_\w+.html', url):
		return find_video_id_from_show_page(url)
	if re.match(r'http://v.youku.com/v_playlist/\w+.html', url):
		return url
	raise Exception('Invalid youku URL: '+url)

def trim_title(title):
	title = title.replace(u' - 视频 - 优酷视频 - 在线观看', '')
	title = title.replace(u' - 专辑 - 优酷视频', '')
	title = re.sub(ur'—([^—]+)—优酷网，视频高清在线观看', '', title)
	return title

def parse_video_title(url, page):
	if re.search(r'v_playlist', url):
		# if we are playing a viedo from play list, the meta title might be incorrect
		title = r1_of([r'<div class="show_title" title="([^"]+)">[^<]', r'<title>([^<>]*)</title>'], page).decode('utf-8')
	else:
		title = r1_of([r'<div class="show_title" title="([^"]+)">[^<]', r'<meta name="title" content="([^"]*)"'], page).decode('utf-8')
	assert title
	title = trim_title(title)
	if re.search(r'v_playlist', url) and re.search(r'-.*\S+', title):
		title = re.sub(r'^[^-]+-\s*', '', title) # remove the special name from title for playlist video
	title = re.sub(ur'—专辑：.*', u'', title) # remove the special name from title for playlist video
	title = unescape_html(title)

	subtitle = re.search(r'<span class="subtitle" id="subtitle">([^<>]*)</span>', page)
	if subtitle:
		subtitle = subtitle.group(1).decode('utf-8').strip()
	if subtitle == title:
		subtitle = None
	if subtitle:
		title += '-' + subtitle
	return title

def parse_playlist_title(url, page):
	if re.search(r'v_playlist', url):
		# if we are playing a viedo from play list, the meta title might be incorrect
		title = re.search(r'<title>([^<>]*)</title>', page).group(1).decode('utf-8')
	else:
		title = re.search(r'<meta name="title" content="([^"]*)"', page).group(1).decode('utf-8')
	title = trim_title(title)
	if re.search(r'v_playlist', url) and re.search(r'-.*\S+', title):
		title = re.sub(ur'^[^-]+-\s*', u'', title)
	title = re.sub(ur'^.*—专辑：《(.+)》', ur'\1', title)
	title = unescape_html(title)
	return title

def parse_page(url):
	url = youku_url(url)
	page = get_html(url)
	id2 = re.search(r"var\s+videoId2\s*=\s*'(\S+)'", page).group(1)
	title = parse_video_title(url, page)
	return id2, title

def get_info(videoId2):
	return json.loads(get_html('http://v.youku.com/player/getPlayList/VideoIDS/'+videoId2))

def find_video(info, stream_type=None):
	#key = '%s%x' % (info['data'][0]['key2'], int(info['data'][0]['key1'], 16) ^ 0xA55AA5A5)
	segs = info['data'][0]['segs']
	types = segs.keys()
	if not stream_type:
		for x in ['hd3', 'hd2', 'mp4', 'flv']:
			if x in types:
				stream_type = x
				break
		else:
			raise NotImplementedError()
	assert stream_type in ('hd3', 'hd2', 'mp4', 'flv')
	file_type = {'hd3':'flv', 'hd2':'flv', 'mp4':'mp4', 'flv':'flv'}[stream_type]

	seed = info['data'][0]['seed']
	source = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/\\:._-1234567890")
	mixed = ''
	while source:
		seed = (seed * 211 + 30031) & 0xFFFF
		index = seed * len(source) >> 16
		c = source.pop(index)
		mixed += c

	ids = info['data'][0]['streamfileids'][stream_type].split('*')[:-1]
	vid = ''.join(mixed[int(i)] for i in ids)

	sid = '%s%s%s' % (int(time()*1000), randint(1000, 1999), randint(1000, 9999))

	urls = []
	for s in segs[stream_type]:
		no = '%02x' % int(s['no'])
		url = 'http://f.youku.com/player/getFlvPath/sid/%s_%s/st/%s/fileid/%s%s%s?K=%s&ts=%s' % (sid, no, file_type, vid[:8], no.upper(), vid[10:], s['k'], s['seconds'])
		urls.append((url, int(s['size'])))
	return urls


def file_type_of_url(url):
	return str(re.search(r'/st/([^/]+)/', url).group(1))

def youku_download_by_id(id2, title, output_dir='.', stream_type=None, merge=True):
	info = get_info(id2)
	urls, sizes = zip(*find_video(info, stream_type))
	total_size = sum(sizes)
	download_urls(urls, title, file_type_of_url(urls[0]), total_size, output_dir, merge=merge)

def youku_download(url, output_dir='', stream_type=None, merge=True):
	id2, title = parse_page(url)
	if type(title) == unicode:
		title = title.encode(default_encoding)
		title = title.replace('?', '-')
	youku_download_by_id(id2, title, output_dir, merge=merge)

def parse_playlist_videos(html):
	return re.findall(r'id="A_(\w+)"', html)

def parse_playlist_pages(html):
	m = re.search(r'<ul class="pages">.*?</ul>', html, flags=re.S)
	if m:
		urls = re.findall(r'href="([^"]+)"', m.group())
		x1, x2, x3 = re.match(r'^(.*page_)(\d+)(_.*)$', urls[-1]).groups()
		return ['http://v.youku.com%s%s%s?__rt=1&__ro=listShow' % (x1, i, x3) for i in range(2, int(x2)+1)]
	else:
		return []

def parse_playlist(url):
	html = get_html(url)
	video_id = re.search(r"var\s+videoId\s*=\s*'(\d+)'", html).group(1)
	show_id = re.search(r'var\s+showid\s*=\s*"(\d+)"', html).group(1)
	list_url = 'http://v.youku.com/v_vpofficiallist/page_1_showid_%s_id_%s.html?__rt=1&__ro=listShow' % (show_id, video_id)
	html = get_html(list_url)
	ids = parse_playlist_videos(html)
	for url in parse_playlist_pages(html):
		ids.extend(parse_playlist_videos(get_html(url)))
	return ids

def parse_vplaylist(url):
	id = r1_of([r'^http://www.youku.com/playlist_show/id_(\d+)(?:_ascending_\d_mode_pic(?:_page_\d+)?)?.html',
	            r'^http://v.youku.com/v_playlist/f(\d+)o[01]p\d+.html',
				r'^http://u.youku.com/user_playlist/pid_(\d+)_id_[\w=]+(?:_page_\d+)?.html'],
	           url)
	assert id, 'not valid vplaylist url: '+url
	url = 'http://www.youku.com/playlist_show/id_%s.html' % id
	n = int(re.search(r'<span class="num">(\d+)</span>', get_html(url)).group(1))
	return ['http://v.youku.com/v_playlist/f%so0p%s.html' % (id, i) for i in range(n)]

def youku_download_playlist(url, create_dir=False, merge=True):
	if re.match(r'http://www.youku.com/show_page/id_\w+.html', url):
		url = find_video_id_from_show_page(url)
	if re.match(r'http://www.youku.com/playlist_show/id_\d+(?:_ascending_\d_mode_pic(?:_page_\d+)?)?.html', url):
		ids = parse_vplaylist(url)
	elif re.match(r'http://v.youku.com/v_playlist/f\d+o[01]p\d+.html', url):
		ids = parse_vplaylist(url)
	elif re.match(r'http://u.youku.com/user_playlist/pid_(\d+)_id_[\w=]+(?:_page_\d+)?.html', url):
		ids = parse_vplaylist(url)
	else:
		assert re.match(r'http://v.youku.com/v_show/id_([\w=]+).html', url), 'URL not supported as playlist'
		ids = parse_playlist(url)
	output_dir = '.'
	if create_dir:
		title = parse_playlist_title(url, get_html(url))
		title = title.encode(default_encoding)
		title = title.replace('?', '-')
		import os
		if not os.path.exists(title):
			os.makedirs(title)
		output_dir = title
	for i, id in enumerate(ids):
		print 'Downloading %s of %s videos...' % (i + 1, len(ids))
		youku_download(id, output_dir=output_dir, merge=merge)

download = youku_download
download_playlist = youku_download_playlist

def main():
	script_main('youku', youku_download, youku_download_playlist)

if __name__ == '__main__':
	main()


########NEW FILE########
