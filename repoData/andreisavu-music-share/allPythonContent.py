__FILENAME__ = db

import web, settings

#
# Master read/write database
#
master = web.database(dbn = settings.DB_MASTER_TYPE,
	host = settings.DB_MASTER_HOST,
	db = settings.DB_MASTER_NAME,
	user = settings.DB_MASTER_USER,
	pw = settings.DB_MASTER_PASSW)

#
# Slave databases - multiple servers behind HA proxy
#
slave = web.database(dbn = settings.DB_SLAVE_TYPE,
	host = settings.DB_SLAVE_HOST,
	db = settings.DB_SLAVE_NAME,
	user = settings.DB_SLAVE_USER,
	pw = settings.DB_SLAVE_PASSW)


########NEW FILE########
__FILENAME__ = index

import web, cgi, settings
import storage, search, db
import simplejson
from lib import is_mp3, get_mp3_info

urls = (
    '^/$', 'do_index',						
	'^/about[/]?$', 'do_about',			
	'^/search[/]?$', 'do_search',			
	'^/upload[/]?$', 'do_upload',
	'^/upload/error[/]?$', 'do_upload_error',		
	'^/api/about[/]?$', 'do_api_about',	
	'^/api/search(.*)$', 'do_api_search',
	'^/api/upload(.*)$', 'do_api_upload',	
	'^/media/(\d+)$', 'do_media',
	'^/view/(\d+)$', 'do_view'
)

app = web.application(urls, globals())

render = web.template.render(settings.TEMPLATE_FOLDER, base='base')

class do_index:        
    def GET(self):
		files = db.slave.select('ms_files', order='date desc', limit=5)
		return render.index(files)

class do_about:
	def GET(self):
		return render.about(title='About')

class do_search:
	def GET(self):
		input = web.input(q='')
		files = search.get(input.q, db.slave)
		return render.search(files, query=input.q, title='Search')

class do_upload_error:
	def GET(self):
		return render.upload_error(title='Upload error')

class do_upload:
	def GET(self):
		return render.upload(title='Upload')

	def POST(self):
		cgi.maxlen = settings.MAX_UP_FILE_SIZE

		input = web.input(file={})
		if input.file.file:
			if not is_mp3(input.file.file):
				raise web.seeother('/upload/error')
			try:
				info = get_mp3_info(input.file.file)
				info['FILENAME'] = input.file.filename
			except:
				raise web.seeother('/upload/error')
			id = storage.save(info, input.file.file, db.master)
			search.update(id, info)
		raise web.seeother('/')

class do_media:
	def GET(self, id):	
		path = "/%s" % storage.get_path(int(id))
		raise web.seeother(path)

class do_view:
	def GET(self, id):
		f = search.get_by_id(id, db.slave)
		if f.title and f.artist:
			title = "%s : %s" % (f.artist, f.title)
			related = search.get(f.artist, db.slave)
		else:
			title = f.filename
			import re
			q = re.sub('[^a-zA-Z ]+', ' ', f.filename[:-4])
			q = [t[:5] for t in q.split(' ') if t.strip()]
			if len(q) > 2:
				q = "%s %s" % (q[0], q[1])
			else:
				q = ' '.join(q)
			related = search.get(q, db.slave)
		related = [x for x in related if x.id != int(id)]

		url = "%s://%s" % (web.ctx['protocol'], web.ctx['host'])
		embedded = """<object type="application/x-shockwave-flash" data="%s/static/player_mp3.swf" width="200" height="20"><param name="movie" value="%s/static/player_mp3.swf" /><param name="FlashVars" value="mp3=%s/media/%d&amp;showstop=1" /></object>""" % (url, url, url, int(id))
		return render.view(f, related, embedded, title)

class do_api_about:
	def GET(self):
		return render.api.about(title='Api Documentation')

class do_api_search:
	def GET(self, format):
		if not format:
			format = '.json'
		input = web.input(q='')
		res = search.get(input.q, db.slave)
		files = []
		for f in res:
			del(f['date'])
			files.append(f)
		return simplejson.dumps(files)

class do_api_upload:
	def POST(self, format):
		cgi.maxlen = settings.MAX_UP_FILE_SIZE
		if not format:
			format = '.json'

		input = web.input(file={})
		if input.file.file:
			if not is_mp3(input.file.file):
				return simplejson.dumps({'code':1, 'error':'Check file format and try again'})
			try:
				info = get_mp3_info(input.file.file)
				info['FILENAME'] = input.file.filename
			except:
				return simplejson.dumps({'code':2, 'error':'Error getting file information'})
			id = storage.save(info, input.file.file, db.master)
			search.update(id, info)
		return simplejson.dumps({'code':0})

def notfound():
	return web.notfound(render.notfound(render))
app.notfound = notfound


def internalerror():
	return web.internalerror(render.internalerror(render))
app.internalerror = internalerror
	
if __name__ == "__main__":
    app.run()


########NEW FILE########
__FILENAME__ = mp3
#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
 
   --cat [files]  -- categorize a bunch of files

      mp3info(filename)
        - reads the mp3 header and returns a dictionary containing
          these fields:

          VERSION
          MM - number of minutes
          SS - number of seconds
          STEREO - 0-mono, 1-stereo
          LAYER - MPEG layer 2 or 3
          MODE 
          COPYRIGHT
          BITRATE 
          FREQUENCY

      get_mp3tag(filename)
        - finds the id3 tag of the mp3 and returns a dictionary
          containing these fields: TITLE, ARTIST, ALBUM, YEAR, COMMENT

      get_xing_header(filename)
        - returns the XING header (flags, frames, bytes) of the mp3 or
          None.

      Categorize(fn)
        - creates a directory called 'cats' with three subdirectories
          'GENRE_ARTIST', 'GENRE', and 'ARTIST'.  It reads the ID3 tag
          off of the mp3 and creates a three symlinks in this
          directory structure.  All files without ID3 tags will have a
          genre and artist of 'Unknown'.


"""

import os, sys, string, time, getopt

mp3_genres = ['Blues',  'Classic Rock',  'Country',  'Dance',  
	      'Disco',  'Funk',  'Grunge',  'Hip-Hop',  'Jazz',  
	      'Metal',  'New Age',  'Oldies',  'Other',  'Pop',  
	      'R&B',  'Rap',  'Reggae',  'Rock',  'Techno',  
	      'Industrial',  'Alternative',  'Ska',  'Death Metal',  
	      'Pranks',  'Soundtrack',  'Euro-Techno',  'Ambient',  
	      'Trip-Hop',  'Vocal',  'Jazz+Funk',  'Fusion',  'Trance',  
	      'Classical',  'Instrumental',  'Acid',  'House',  'Game',  
	      'Sound Clip',  'Gospel',  'Noise',  'AlternRock',  'Bass',  
	      'Soul',  'Punk',  'Space',  'Meditative',  
	      'Instrumental Pop',  'Instrumental Rock',  'Ethnic',  
	      'Gothic',  'Darkwave',  'Techno-Industrial',  'Electronic',  
	      'Pop-Folk',  'Eurodance',  'Dream',  'Southern Rock',  
	      'Comedy',  'Cult',  'Gangsta',  'Top 40',  'Christian Rap',  
	      'Pop/Funk',  'Jungle',  'Native American',  'Cabaret',  
	      'New Wave',  'Psychadelic',  'Rave',  'Showtunes',  
	      'Trailer',  'Lo-Fi',  'Tribal',  'Acid Punk',  
	      'Acid Jazz',  'Polka',  'Retro',  'Musical',  
	      'Rock & Roll',  'Hard Rock',  ]

winamp_genres = mp3_genres + \
		['Folk','Folk-Rock','National Folk','Swing','Fast Fusion','Bebob','Latin',
		'Revival','Celtic','Bluegrass','Avantgarde','Gothic Rock','Progressive Rock',
		'Psychedelic Rock','Symphonic Rock','Slow Rock','Big Band','Chorus',
		 'Easy Listening','Acoustic','Humour','Speech','Chanson','Opera',
		 'Chamber Music','Sonata','Symphony','Booty Bass','Primus','Porn Groove',
		 'Satire','Slow Jam','Club','Tango','Samba','Folklore','Ballad',
		 'Power Ballad','Rhythmic Soul','Freestyle','Duet','Punk Rock','Drum Solo',
		 'Acapella','Euro-House','Dance Hall']


t_bitrate = [
  [
    [0,32,48,56,64,80,96,112,128,144,160,176,192,224,256],
    [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160],
    [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160]
    ],
  [
    [0,32,64,96,128,160,192,224,256,288,320,352,384,416,448],
    [0,32,48,56,64,80,96,112,128,160,192,224,256,320,384],
    [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320]
    ]
  ]
        
t_sampling_freq = [
  [22050, 24000, 16000],
  [44100, 48000, 32000]
  ]

frequency_tbl = {0:22050,1:24000,2:16000,3:44100,4:48000,5:32000,6:64000}


def getword(fp, off):
  fp.seek(off, 0)
  word = fp.read(4)
  return word

def get_l4 (s):
    return reduce (lambda a,b: ((a<<8) + b), map (long, map (ord, s)))

def get_xing_header (f):
    where = f.tell()
    try:
        f.seek(0)
        b = f.read(8192)
        i = string.find (b, 'Xing')
        if i > 0:
            # 32-bit fields; "Xing", flags, frames, bytes, 100 toc
            i = i + 4
            flags	= get_l4 (b[i:i+4]); i = i + 4
            frames	= get_l4 (b[i:i+4]); i = i + 4
            bytes	= get_l4 (b[i:i+4]); i = i + 4
            return flags, frames, bytes
        else:
            return None
    finally:
        f.seek (where)

MPG_MD_STEREO           = 0
MPG_MD_JOINT_STEREO     = 1
MPG_MD_DUAL_CHANNEL     = 2
MPG_MD_MONO             = 3

def get_newhead (word):
  word = get_l4 (word)
  if (word & (1<<20)):
    if (word & (1<<19)):
      lsf = 0
    else:
      lsf = 1
    mpeg25 = 0
  else:
    lsf = 1
    mpeg25 = 1
  lay = 4 - ((word>>17)&3)
  if mpeg25:
    sampling_frequency = 6 + ((word>>10) & 3)
  else:
    sampling_frequency = ((word>>10)&3) + (lsf * 3)
  error_protection 	= ((word>>16)&1) ^ 1
  bitrate_index 	= (word>>12) & 0xf
  padding 		= ((word >> 9) & 0x1)
  extension 		= ((word >> 8) & 0x1)
  mode	 		= ((word >> 6) & 0x3)
  mode_ext 		= ((word >> 4) & 0x3)
  copyright 		= ((word >> 3) & 0x1)
  original 		= ((word >> 2) & 0x1)
  emphasis 		= word & 0x3

  if mode == MPG_MD_MONO:
    stereo = 1
  else:
    stereo = 2


  return locals()
  import pprint
  pprint.pprint (locals())
  
def get_head(word):
  if len(word) != 4:
    return {}
  l = ord(word[0])<<24|ord(word[1])<<16|ord(word[2])<<8|ord(word[3])

  id = (l>>19) & 1
  layer = (l>>17) & 3
  protection_bit = (l>>16) & 1
  bitrate_index = (l>>12) & 15
  sampling_freq = (l>>10) & 3
  padding_bit = (l>>9) & 1
  private_bit = (l>>8) & 1
  mode = (l>>6) & 3
  mode_extension = (l>>4) & 3
  copyright = (l>>3) & 1
  original = (l>>2) & 1
  emphasis = (l>>0) & 1
  version_index = (l>>19) & 3
  bytes = l

##   for k,v in vars().items():
##     print k,v

  try:
    bitrate = t_bitrate[id][3-layer][bitrate_index]
  except IndexError:
    bitrate = 0

  try:
    fs = t_sampling_freq[id][sampling_freq]
  except IndexError:
    fs = 0

  return vars()

def is_mp3(h):
  #if h['bytes'] == -1: return 0
  if not (h['bitrate_index'] == 0 or \
	  h['version_index'] == 1 or \
	  ((h['bytes'] & 0xFFE00000) != 0xFFE00000) or \
	  (not h['fs']) or \
	  (not h['bitrate'])):
    return 1
  return 0

def get_v2head(fp):
  fp.seek(0,0)
  word = fp.read(3)
  if word != "ID3": return 0

  bytes = fp.read(2)
  major_version = ord(bytes[0])
  minor_version = ord(bytes[1])

  version = "ID3v2.%d.%d" % (major_version, minor_version)
  bytes = fp.read(1)
  unsync = (ord(bytes)>>7) & 1
  ext_header = (ord(bytes)>>6) & 1
  experimental = (ord(bytes)>>5) & 1

  bytes = fp.read(4)
  tagsize = 0

  for i in range(4):
    tagsize = tagsize + ord(bytes[3-i])*128*i

  if ext_header:
    ext_header_size = ext_header_size + 10
    bytes = fp.read(4)

  return vars()

def mp3info(fn=None, fp=None):
  if not fn and not fp:
    return {}
  off = 0
  eof = 0
  h = 0
  i = 0
  tot = 4096

  if fn and os.stat(fn)[6] == 0:
    return {}

  if not fp:
  	fp = open(fn)
  word = getword(fp, off)

  if off==0:
    id3v2 = get_v2head(fp)
    if id3v2:
      off = off + id3v2['tagsize']
      tot = tot + off
      word = getword(fp, off)

  nh = get_newhead (word)

  vbr = 0
  xh = get_xing_header (fp)
  if xh:
    flags, xing_frames, xing_bytes = xh
    if (flags & 0x08):
        vbr = 1

    try:
      if vbr:
        tpf = float([0,384,1152,1152][int(nh['lay'])])
        tpf = tpf / ([44100, 48000, 32000, 22050, 24000, 16000, 11025, 12000, 8000][int(nh['sampling_frequency'])] << nh['lsf'])
    except IndexError,e:
		return {}    
  while 1:
    h = get_head(word)
    if not h: break
    off=off+1
    word = getword(fp, off)
    if off>tot: 
      return {}
    if is_mp3(h): break


  fp.seek(0, 2)
  eof = fp.tell()

  try:
    fp.seek(-128, 2)
  except IOError, reason:
    return {}
  

  if h['id']:
    h['mean_frame_size'] = (144000. * h['bitrate']) / h['fs']
  else:
    h['mean_frame_size'] = (72000. * h['bitrate']) / h['fs']

  h['layer'] = h['mode']
  h['freq_idx'] = 3*h['id'] + h['sampling_freq']

  h['length'] = ((1.0*eof-off) / h['mean_frame_size']) * ((115200./2)*(1.+h['id']))/(1.0*h['fs'])
  h['secs'] = int(h['length'] / 100);
  

  i = {}
  i['VERSION'] = h['id']
  i['MM'] = int(h['secs']/60)
  i['SS'] = h['secs']%60
  i['STEREO'] = not(h['mode'] == 3)
  if h['layer'] >= 0:
    if h['layer'] == 3:
      i['LAYER'] = 2
    else:
      i['LAYER'] = 3
  else:
    i['LAYER'] = ''
  i['MODE'] = h['mode']
  i['COPYRIGHT'] = h['copyright']
  if h['bitrate'] >=0:
    i['BITRATE'] = h['bitrate']
  else:
    i['BITRATE'] = ''
  if h['freq_idx'] >= 0:
    i['FREQUENCY'] = frequency_tbl[h['freq_idx']]
  else:
    i['FREQUENCY'] = ''

  return i
			    
def get_mp3tag(fn=None, fp=None):
  if not fn and not fp:
    return {}
  if fn and os.stat(fn)[6] == 0:
    return {}

  try:
    if not fp:
      fp = open(fn)
  except IOError, reason:
    return {}

  try:
    fp.seek(-128, 2)
  except IOError, reason:
    return {}

  line = None
  while 1:
    l = fp.readline()
    if not l: break
    line = l

  id = {}
  if line[:3] == 'TAG':
    v1 = 1
    i = 0; j = i + 3
    #id['d1'] = string.strip(line[i:j])
    i = j; j = i + 30
    id['TITLE'] = string.strip(line[i:j])
    i = j; j = i + 30
    id['ARTIST'] = string.strip(line[i:j])
    i = j; j = i + 30
    id['ALBUM'] = string.strip(line[i:j])
    i = j; j = i + 4
    id['YEAR'] = string.strip(line[i:j])
    i = j; j = i + 28
    id['COMMENT'] = string.strip(line[i:j])

    genre = ord(line[-1])
    try:
      id['GENRE'] = winamp_genres[ord(line[-1])]
    except IndexError:
      id['GENRE'] = "Unknown"


  return id

def Categorize(fn):
  i1 = mp3info(fn)
  i2 = get_mp3tag(fn)

  path1 = "cats/GENRE_ARIST/%s/%s" % (i2.get('GENRE', "Unknown"), i2.get('ARTIST', "Unknown"))
  path2 = "cats/GENRE/%s" % (i2.get('GENRE', "Unknown"), )
  path3 = "cats/ARIST/%s" % (i2.get('ARTIST', "Unknown"), )

  path1 = string.replace(path1, "\0", "_")
  path1 = string.replace(path1, " ", "_")
  path2 = string.replace(path2, "\0", "_")
  path2 = string.replace(path2, " ", "_")
  path3 = string.replace(path3, "\0", "_")
  path3 = string.replace(path3, " ", "_")

  if not os.path.isdir(path1):
    os.makedirs(path1)
  if not os.path.isdir(path2):
    os.makedirs(path2)
  if not os.path.isdir(path3):
    os.makedirs(path3)
  base, ffn = os.path.split(fn)

  try: os.symlink(fn, os.path.join(path1, ffn))
  except:  pass
  try: os.symlink(fn, os.path.join(path2, ffn))
  except:  pass
  try: os.symlink(fn, os.path.join(path3, ffn))
  except:  pass

def usage(progname):
  print __doc__ % vars()

def main(argv, stdout, environ):
  progname = argv[0]
  list, args = getopt.getopt(argv[1:], "", ["help", "cat"])

  if len(args) == 0:
    usage(progname)
    return
  for (field, val) in list:
    if field == "--help":
      usage(progname)
      return
    elif field == "--cat":
      for fn in args:
	Categorize(fn)
      return

  for fn in args:
    print fn
    i1 = mp3info(fn)
    for k,v in i1.items():
      print k,v

    i2 = get_mp3tag(fn)
    for k,v in i2.items():
      print k,v
    print


if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)

########NEW FILE########
__FILENAME__ = search

import web

def update(id, info):
	pass

def get_by_id(id, db):
	file = db.query('select * from ms_files where id=$id', vars={'id':id})
	return file[0]

def get_related(id, db):
	return []

def get(q, db):
	if not q:
		return []
	pq = [t.strip() for t in q.split(' ') if len(t.strip())!=0]
	pq = '%' + '%'.join(pq) + '%'
	files = db.query('select * from ms_files where filename like $q', vars={'q':pq})
	return files


########NEW FILE########
__FILENAME__ = settings

TEMPLATE_FOLDER = 'templates/'
MAX_UP_FILE_SIZE = 10 * 1024 * 1024 # 10 MB

DB_MASTER_TYPE = 'mysql'
DB_MASTER_HOST = 'localhost'
DB_MASTER_NAME = 'music'
DB_MASTER_USER = 'root'
DB_MASTER_PASSW = ''

DB_SLAVE_TYPE = 'mysql'
DB_SLAVE_HOST = 'localhost'
DB_SLAVE_NAME = 'music'
DB_SLAVE_USER = 'root'
DB_SLAVE_PASSW = ''


########NEW FILE########
__FILENAME__ = storage

import web, re, os

def db_save(info, db):
	""" Save data in database """
	return db.insert('ms_files', filename=info['FILENAME'], 
		album=info['ALBUM'], artist=info['ARTIST'], 
		title=info['TITLE'], year=info['YEAR'])

def clean(v):
	""" Remove any not visible chars """
	return re.sub('[^\w.\'" ]+', '', v)

def add_missing_fields(info):
	""" Add to the info structure the missing fields """
	if not 'ALBUM' in info:
		info['ALBUM'] = ''
	if not 'ARTIST' in info:
		info['ARTIST'] = ''
	if not 'TITLE' in info:
		info['TITLE'] = ''
	if not 'YEAR' in info:
		info['YEAR'] = 0

	info['ALBUM'] = clean(info['ALBUM'])
	info['ARTIST'] = clean(info['ARTIST'])
	info['TITLE'] = clean(info['TITLE'])

	return info

def save_file(id, fp):
	folder = get_folder(id)
	if not os.path.exists(folder):
		os.makedirs(folder)

	dest = "%s/%d.mp3" % (folder, id)
	f = open(dest, 'w')
	fp.seek(0)
	f.write(fp.read())
	f.close()

def get_folder(id):
	return "static/upload/%d/%d" % ((id / 10) % 10, id % 10)

def get_path(id):
	return "%s/%d.mp3" % (get_folder(id), id)

def save(info, fp, db):
	""" Save track info in database """
	info = add_missing_fields(info)
	id = db_save(info, db)
	save_file(id, fp)
	return id


########NEW FILE########
__FILENAME__ = uploader
#! /usr/bin/python

# http://fabien.seisen.org/python/urllib2_multipart.html

__author__ = 'Savu Andrei <contact@andreisavu.ro>'

import os, sys
import urllib2_file
import urllib2
import simplejson
import socket

def parse_cli_params():
	if len(sys.argv) != 3:
		print 'Usage: ./uploader.py <api_endpoint> <folder_or_file>'
		sys.exit(0)
	# api_endpoint should be a valid url
	if not os.path.exists(sys.argv[2]):
		print 'File or dir not found.'
		sys.exit(2)
	return sys.argv[1], sys.argv[2]

def do_file_upload(url, file):
	data = { 'file': open(file) }
	try:
		r = simplejson.loads(urllib2.urlopen(url, data).read())
		return r
	except socket.error, e:
		return {'code': 1}

def folder_scanner(folder):
    if folder[0] == '.':
        folder = os.path.join( os.getcwd(), folder[2:] )
    for f in os.listdir(folder):
        if f[0] == '.':
            continue
        f = os.path.join(folder, f)
        if os.path.isdir(f):
            for x in folder_scanner(f):
                yield x
        if os.path.isfile(f):
            yield f

def check_result(r, f):
	if r['code'] != 0:
		print 'Error:', f
	else:
		print 'Ok:', f

def is_mp3(f):
	if f[-3:] == 'mp3':
		return True
	return False

def handle_file(f):
	if is_mp3(f):
		r = do_file_upload(url, f)
		check_result(r,f)
	else:
		print 'Ignore:', f

if __name__ == '__main__':
	url, src = parse_cli_params()
	if os.path.isfile(src):
		handle_file(src)
	else:
		for f in folder_scanner(src):
			handle_file(f)

########NEW FILE########
__FILENAME__ = urllib2_file
#!/usr/bin/env python
####
# Version: 0.2.0
#  - UTF-8 filenames are now allowed (Eli Golovinsky)<br/>
#  - File object is no more mandatory, Object only needs to have seek() read() attributes (Eli Golovinsky)<br/>
#
# Version: 0.1.0
#  - upload is now done with chunks (Adam Ambrose)
#
# Version: older
# THANKS TO:
# bug fix: kosh @T aesaeion.com
# HTTPS support : Ryan Grow <ryangrow @T yahoo.com>

# Copyright (C) 2004,2005,2006 Fabien SEISEN
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
# you can contact me at: <fabien@seisen.org>
# http://fabien.seisen.org/python/
#
# Also modified by Adam Ambrose (aambrose @T pacbell.net) to write data in
# chunks (hardcoded to CHUNK_SIZE for now), so the entire contents of the file
# don't need to be kept in memory.
#
"""
enable to upload files using multipart/form-data

idea from:
upload files in python:
 http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306

timeoutsocket.py: overriding Python socket API:
 http://www.timo-tasi.org/python/timeoutsocket.py
 http://mail.python.org/pipermail/python-announce-list/2001-December/001095.html

import urllib2_files
import urllib2
u = urllib2.urlopen('http://site.com/path' [, data])

data can be a mapping object or a sequence of two-elements tuples
(like in original urllib2.urlopen())
varname still need to be a string and
value can be string of a file object
eg:
  ((varname, value),
   (varname2, value),
  )
  or
  { name:  value,
    name2: value2
  }

"""

import os
import socket
import sys
import stat
import mimetypes
import mimetools
import httplib
import urllib
import urllib2

CHUNK_SIZE = 65536

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

# if sock is None, juste return the estimate size
def send_data(v_vars, v_files, boundary, sock=None):
	l = 0
	for (k, v) in v_vars:
		buffer=''
		buffer += '--%s\r\n' % boundary
		buffer += 'Content-Disposition: form-data; name="%s"\r\n' % k
		buffer += '\r\n'
		buffer += v + '\r\n'
		if sock:
			sock.send(buffer)
		l += len(buffer)
	for (k, v) in v_files:
		fd = v
		file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
		name = fd.name.split('/')[-1]
		if isinstance(name, unicode):
			name = name.encode('UTF-8')
		buffer=''
		buffer += '--%s\r\n' % boundary
		buffer += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' \
				  % (k, name)
		buffer += 'Content-Type: %s\r\n' % get_content_type(name)
		buffer += 'Content-Length: %s\r\n' % file_size
		buffer += '\r\n'

		l += len(buffer)
		if sock:
			sock.send(buffer)
			if hasattr(fd, 'seek'):
				fd.seek(0)
 			while True:
				chunk = fd.read(CHUNK_SIZE)
				if not chunk: break
				sock.send(chunk)

		l += file_size
	buffer='\r\n'
	buffer += '--%s--\r\n' % boundary
	buffer += '\r\n'
	if sock:
		sock.send(buffer)
	l += len(buffer)
	return l

# mainly a copy of HTTPHandler from urllib2
class newHTTPHandler(urllib2.BaseHandler):
	def http_open(self, req):
		return self.do_open(httplib.HTTP, req)

	def do_open(self, http_class, req):
		data = req.get_data()
		v_files=[]
		v_vars=[]
		# mapping object (dict)
		if req.has_data() and type(data) != str:
			if hasattr(data, 'items'):
				data = data.items()
			else:
				try:
					if len(data) and not isinstance(data[0], tuple):
						raise TypeError
				except TypeError:
					ty, va, tb = sys.exc_info()
					raise TypeError, "not a valid non-string sequence or mapping object", tb
				
			for (k, v) in data:
				if hasattr(v, 'read'):
					v_files.append((k, v))
				else:
					v_vars.append( (k, v) )
		# no file ? convert to string
		if len(v_vars) > 0 and len(v_files) == 0:
			data = urllib.urlencode(v_vars)
			v_files=[]
			v_vars=[]
		host = req.get_host()
		if not host:
			raise urllib2.URLError('no host given')

		h = http_class(host) # will parse host:port
		if req.has_data():
			h.putrequest('POST', req.get_selector())
			if not 'Content-type' in req.headers:
				if len(v_files) > 0:
					boundary = mimetools.choose_boundary()
					l = send_data(v_vars, v_files, boundary)
					h.putheader('Content-Type',
								'multipart/form-data; boundary=%s' % boundary)
					h.putheader('Content-length', str(l))
				else:
					h.putheader('Content-type',
								'application/x-www-form-urlencoded')
					if not 'Content-length' in req.headers:
						h.putheader('Content-length', '%d' % len(data))
		else:
	   		h.putrequest('GET', req.get_selector())

		scheme, sel = urllib.splittype(req.get_selector())
		sel_host, sel_path = urllib.splithost(sel)
		h.putheader('Host', sel_host or host)
		for name, value in self.parent.addheaders:
			name = name.capitalize()
			if name not in req.headers:
				h.putheader(name, value)
		for k, v in req.headers.items():
			h.putheader(k, v)
		# httplib will attempt to connect() here.  be prepared
		# to convert a socket error to a URLError.
		try:
			h.endheaders()
		except socket.error, err:
			raise urllib2.URLError(err)

		if req.has_data():
			if len(v_files) >0:
				l = send_data(v_vars, v_files, boundary, h)
			elif len(v_vars) > 0:
				# if data is passed as dict ...
				data = urllib.urlencode(v_vars)
				h.send(data)
			else:
				# "normal" urllib2.urlopen()
				h.send(data)

	   	code, msg, hdrs = h.getreply()
		fp = h.getfile()
		if code == 200:
			resp = urllib.addinfourl(fp, hdrs, req.get_full_url())
			resp.code = code
			resp.msg = msg
			return resp
		else:
			return self.parent.error('http', req, fp, code, msg, hdrs)

urllib2._old_HTTPHandler = urllib2.HTTPHandler
urllib2.HTTPHandler = newHTTPHandler

class newHTTPSHandler(newHTTPHandler):
	def https_open(self, req):
		return self.do_open(httplib.HTTPS, req)
	
urllib2.HTTPSHandler = newHTTPSHandler

if __name__ == '__main__':
	import getopt
	import urllib2
	import urllib2_file
	import string
	import sys

	def usage(progname):
		print """
SYNTAX: %s -u url -f file [-v]
""" % progname
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hvu:f:')
	except getopt.GetoptError, errmsg:
		print "ERROR:", errmsg
		sys.exit(1)

	v_url = ''
	v_verbose = 0
	v_file = ''

	for name, value in opts:
		if name in ('-h',):
			usage(sys.argv[0])
			sys.exit(0)
		elif name in ('-v',):
			v_verbose += 1
		elif name in ('-u',):
			v_url = value
		elif name in ('-f',):
			v_file = value
		else:
			print "invalid argument:", name
			sys.exit(2)

	error = 0
	if v_url == '':
		print "need -u"
		error += 1
	if v_file == '':
		print "need -f"
		error += 1

	if error > 0:
		sys.exit(3)
		
	fd = open(v_file, 'r')
	data = {
		'filename' : fd,
		}
	# u = urllib2.urlopen(v_url, data)
	req = urllib2.Request(v_url, data, {})
	try:
		u = urllib2.urlopen(req)
	except urllib2.HTTPError, errobj:
		print "HTTPError:", errobj.code
		
	else:
		buf = u.read()
		print "OK"

########NEW FILE########
