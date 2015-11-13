__FILENAME__ = pressfs
#!/usr/bin/env python

'''
pressfs - The WordPress filesystem
Joseph Scott
http://josephscott.org/

Copyright (c) 2011 Joseph Scott

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

import base64
import calendar
import ConfigParser
import errno
import fuse
import httplib2
import os
import re
import simplejson
import stat
import sys
import time
import urllib

fuse.fuse_python_api = ( 0, 2 )

class PressFS_Stat( fuse.Stat ) :
	def __init__( self ) :
		self.st_ino		= 0
		self.st_dev		= 0
		self.st_uid		= 0
		self.st_gid		= 0
		self.st_size	= 0
		self.st_atime	= 0
		self.st_mtime	= 0
		self.st_ctime	= 0

		# default to read only file
		self.st_mode = stat.S_IFREG | 0400
		self.st_nlink = 1

	def dir( self, mode = 0400 ) :
		self.st_mode = stat.S_IFDIR | mode
		self.st_nlink = 2

	def file_mode( self, mode = 0400 ) :
		self.st_mode = stat.S_IFREG | mode

	def size( self, size ) :
		self.st_size = size

	def time( self, when ) :
		self.st_atime = when
		self.st_mtime = when
		self.st_ctime = when

class PressFS( fuse.Fuse ) :
	def __init__( self, *args, **kw ) :
		fuse.Fuse.__init__( self, *args, **kw )

		self.version = '0.2.0'

		if ( os.path.isfile( 'config.ini' ) == False ) :
			print "You need setup config.ini first."
			sys.exit()

		self.config = ConfigParser.ConfigParser()
		self.config.read( 'config.ini' )

		self.wp_url = self.config.get( 'WordPress', 'url' ) + '?pressfs=1'
		self.wp_username = self.config.get( 'WordPress', 'username' )
		self.wp_password = self.config.get( 'WordPress', 'password' )
		self.req_expire = self.config.getint( 'Cache', 'req_expire' )

		self.writable_paths = {
			'post_content'		: '/(posts)/(\d+)-(.*?)/(content)',

			'user_url'			: '/(users)/(.*?)/(url)',
		}

		self.req_cache = { }
		self.open_files = { }
		self.write_files = { }

#	def __getattribute__( self, name ) :
#		print ">> __GET ATTR : ", name
#		try:
#			return object.__getattribute__(self, name)
#		except AttributeError:
#			return self._catch_call( name )

#	def _catch_call( self, name ) :
#		print ">> CATCH : " + name
###		return lambda: "catched: %s" % name

	def getattr( self, path ) :
		st = PressFS_Stat()

		if ( path == '/' ) :
			st.dir()
			return st

		for ( pattern ) in self.writable_paths :
			if ( re.match( self.writable_paths[pattern], path ) ) :
				st.file_mode( 0600 )
				break

		# MEDIA
		if ( path == '/media' ) :
			st.dir()
			return st

		match = re.match( '/media/(.*?)\.(.*)', path )
		if ( match ) :
			media = self.wp_request( 'get_media_list' )['media']
			for ( m ) in media :
				if ( media[m]['name'] == match.group( 1 ) ) :
					print ">> MEDIA : " + match.group( 1 )

					when = time.strptime(
						media[m]['date-gmt'],
						'%Y-%m-%d %H:%M:%S'
					)
					st.time( time.mktime( when ) )
					st.size( media[m]['size'] )

					return st

		# POSTS
		if ( path == '/posts' ) :
			st.dir()
			return st

		match = re.match( '/posts/(\d+)-(.*?)/(.*)', path )
		if ( match ) :
			post = self.wp_request( 'get_post_list' )['posts']
			post = post[ match.group( 1 ) ]

			if ( post['date-gmt'] != '0000-00-00 00:00:00' ) :
				when = time.strptime( post['date-gmt'], '%Y-%m-%d %H:%M:%S' )
				st.time( time.mktime( when ) )

			if ( post[ match.group( 3 ) ] ) :
				st.size( len( str( post[ match.group( 3 ) ] ) ) )

			return st

		match = re.match( '/posts/(\d+)-(.*)', path )
		if ( match ) :
			posts = self.wp_request( 'get_post_list' )['posts']
			post = posts[ match.group( 1 ) ]

			if ( post['date-gmt'] != '0000-00-00 00:00:00' ) :
				when = time.strptime( post['date-gmt'], '%Y-%m-%d %H:%M:%S' )
				st.time( time.mktime( when ) )

			st.dir()
			return st

		# TAGS
		if ( path == '/tags' ) :
			st.dir()
			return st

		match = re.match( '/tags/(.*?)/(.*)', path )
		if ( match ) :
			tags = self.wp_request( 'get_tag_list' )['tags']
			for ( tag_id ) in tags :
				if ( tags[tag_id]['slug'] == match.group( 1 ) ) :
					st.size( len( str( tags[tag_id][ match.group( 2 ) ] ) ) )
					return st

		match = re.match( '/tags/(.*)', path )
		if ( match ) :
			st.dir()
			return st

		# CATEGORIES
		if ( path == '/categories' ) :
			st.dir()
			return st
	
		match = re.match( '/categories/(.*?)/(.*)', path )
		if ( match ) :
			cats = self.wp_request( 'get_category_list' )['categories']
			for ( cat_id ) in cats :
				if ( cats[cat_id]['slug'] == match.group( 1 ) ) :
					st.size( len( str( cats[cat_id][ match.group( 2 ) ] ) ) )
					return st

		match = re.match( '/categories/(.*)', path )
		if ( match ) :
			st.dir()
			return st

		# USERS
		if ( path == '/users' ) :
			st.dir()
			return st

		match = re.match( '/users/(.*?)/(.*)', path )
		if ( match ) :
			users = self.wp_request( 'get_user_list' )['users']
			user = users[ match.group( 1 ) ]
			when = time.strptime( user['registered'], '%Y-%m-%d %H:%M:%S' )

			st.size( len( user[ match.group( 2 ) ] ) )
			st.time( time.mktime( when ) )
			return st

		match = re.match( '/users/(.*)', path )
		if ( match ) :
			users = self.wp_request( 'get_user_list' )['users']
			user = users[ match.group( 1 ) ]
			when = time.strptime( user['registered'], '%Y-%m-%d %H:%M:%S' )

			st.dir()
			st.time( time.mktime( when ) )
			return st

		return -errno.ENOENT

	def open( self, path, flags ) :
		print ">> OPEN : " + path
		print flags
		data = ''

		for ( pattern ) in self.writable_paths :
			write = re.match( self.writable_paths[pattern], path )
			if ( write ) :
				if ( write.group( 1 ) == 'posts' ) :
					post = self.wp_request( 'get_post_list' )['posts']
					post = post[ write.group( 2 ) ]
					data = post[ write.group( 4 ) ]
		
		self.open_files[path] = time.gmtime()

		# quick hack to check if the file was opened in read only mode
		if ( flags != 32768 ) :
			self.write_files[path] = {
				'size'	: len( data ),
				'data'	: data
			}

		return 0

	def read( self, path, size, offset ) :
		data = ''

		# MEDIA
		match = re.match( '/media/(.+)\.(\w+)', path )
		if ( match ) :
			data = self.wp_request(
				'get_media_file',
				{ 'name': match.group( 1 ) },
				{ },
				False
			)
			return self.read_data( str( data ), size, offset )

		# POSTS
		match = re.match( '/posts/(\d+)-(.*?)/(.*)', path )
		if ( match ) :
			post = self.wp_request( 'get_post_list' )['posts']
			post = post[ match.group( 1 ) ]

			data = post[ match.group( 3 ) ]
			return self.read_data( str( data ), size, offset )

		# TAGS
		match = re.match( '/tags/(.*?)/(.*)', path )
		if ( match ) :
			tags = self.wp_request( 'get_tag_list' )['tags']
			for ( tag_id ) in tags :
				if ( tags[tag_id]['slug'] == match.group( 1 ) ) :
					data = tags[tag_id][ match.group( 2 ) ]
					return self.read_data( str( data ), size, offset )

		# CATEGORIES
		match = re.match( '/categories/(.*?)/(.*)', path )
		if ( match ) :
			cats = self.wp_request( 'get_category_list' )['categories']
			for ( cat_id ) in cats :
				if ( cats[cat_id]['slug'] == match.group( 1 ) ) :
					data = cats[cat_id][ match.group( 2 ) ]
					return self.read_data( str( data ), size, offset )

		# USERS
		match = re.match( '/users/(.*?)/(.*)', path )
		if ( match ) :
			users = self.wp_request( 'get_user_list' )['users']
			user = users[ match.group( 1 ) ]
			data = user[ match.group( 2 ) ]
			return self.read_data( str( data ), size, offset )

	def read_data( self, data, size, offset ) :
		slen = len( data )
		if ( offset < slen ) :
			if ( ( offset + size ) > slen ) :
				size = slen - offset
			buf = data[ offset : offset + size ]
		else :
			buf = ''

		return buf

	def readdir( self, path, offset ) :
		yield fuse.Direntry( '.' )
		yield fuse.Direntry( '..' )

		if ( path == '/' ) :
			yield fuse.Direntry( 'categories' )
			yield fuse.Direntry( 'media' )
			yield fuse.Direntry( 'posts' )
			yield fuse.Direntry( 'tags' )
			yield fuse.Direntry( 'users' )
			return

		# MEDIA
		if ( path == '/media' ) :
			media = self.wp_request( 'get_media_list' )['media']
			for ( m ) in media.keys() :
				print ">> MEDIA ", media[m]
				media_name = media[m]['name'] + '.' + media[m]['extension']
				yield fuse.Direntry( media_name )

		# POSTS
		if ( path == '/posts' ) :
			posts = self.wp_request( 'get_post_list' )['posts']
			for ( p ) in posts.keys() :
				if ( posts[p]['name'] != '' ) :
					yield fuse.Direntry( p + '-' + posts[p]['name'] )
				else :
					yield fuse.Direntry( p + '-' + posts[p]['title'] )
			return

		match = re.match( '/posts/(\d+)-(.*)', path )
		if ( match ) :
			post = self.wp_request( 'get_post_list' )['posts']
			post = post[ match.group( 1 ) ]

			for ( attr ) in post :
				yield fuse.Direntry( attr )
			return

		# TAGS
		if ( path == '/tags' ) :
			tags = self.wp_request( 'get_tag_list' )['tags']
			for ( t ) in tags :
				yield fuse.Direntry( tags[t]['slug'] )
			return

		match = re.match( '/tags/(.*)', path )
		if ( match ) :
			tags = self.wp_request( 'get_tag_list' )['tags']
			for ( tag_id ) in tags :
				if ( tags[tag_id]['slug'] == match.group( 1 ) ) :
					for ( t ) in tags[tag_id] :
						yield fuse.Direntry( t )
					return

		# CATEGORIES
		if ( path == '/categories' ) :
			cats = self.wp_request( 'get_category_list' )['categories']
			for ( c ) in cats :
				yield fuse.Direntry( cats[c]['slug'] )
			return

		match = re.match( '/categories/(.*)', path )
		if ( match ) :
			cats = self.wp_request( 'get_category_list' )['categories']
			for ( cat_id ) in cats :
				if ( cats[cat_id]['slug'] == match.group( 1 ) ) :
					for ( c ) in cats[cat_id] :
						yield fuse.Direntry( c )
					return

		# USERS
		if ( path == '/users' ) :
			users = self.wp_request( 'get_user_list' )['users']
			for ( u ) in users :
				yield fuse.Direntry( u )
			return

		match = re.match( '/users/(.*)', path )
		if ( match ) :
			users = self.wp_request( 'get_user_list' )['users']
			user = users[ match.group(1) ]
			for ( attr ) in user :
				yield fuse.Direntry( attr )
			return

	def release( self, path, flags ) :
		print ">> RELEASE : " + path
		print flags
		if ( path ) in self.open_files :
			del self.open_files[path]

		if ( path ) not in self.write_files :
			return

		for ( pattern ) in self.writable_paths :
			write = re.match( self.writable_paths[pattern], path )
			if ( write ) :
				if ( write.group( 1 ) == 'posts' ) :
					post_id = write.group( 2 )
					post_field = write.group( 4 )

					self.wp_request(
						'update_post',
						post_vars = {
							'id'		: post_id,
							post_field	: self.write_files[path]['data']
						}
					)

				if ( write.group( 1 ) == 'users' ) :
					user_login = write.group( 2 )
					user_field = write.group( 3 )

					self.wp_request(
						'update_user',
						post_vars = {
							'login'		: user_login,
							user_field	: self.write_files[path]['data']
						}
					)

				# flush the request cache after each write completes
				self.req_cache = { }
				del self.write_files[path]

	def truncate( self, path, len ) :
		print ">> TRUNCATE : " + path
		print len

		if ( path ) in self.write_files :
			self.write_files[path]['data'] = ''
			self.write_files[path]['size'] = 0

	def wp_request( self, action, get_vars = {}, post_vars = {}, json_response = True ) :
		req_url = self.wp_url + '&call=' + action
		for ( g ) in get_vars :
			req_url += '&' + urllib.quote( g ) 
			req_url	+= '=' + urllib.quote( get_vars[g] )

		now = calendar.timegm( time.gmtime() )

		# check the cache first
		if ( req_url in self.req_cache ) :
			if ( self.req_cache[req_url]['expire'] > now ) :
				return self.req_cache[req_url]['data']
			else :
				del self.req_cache[req_url]

		# httplib2 won't send auth headers on the first request
		# so we force them in
		req_auth = base64.encodestring(
			self.wp_username + ':' + self.wp_password
		)

		req_headers = {
			'Authorization' : 'Basic ' + req_auth,
			'User-Agent' : 'PressFS/' + self.version,
			'Content-Type' : 'application/x-www-form-urlencoded'
		}

		print ">> WP REQUEST : " + req_url
		http = httplib2.Http()
		resp, content = http.request(
			req_url,
			'POST',
			urllib.urlencode( post_vars ),
			headers = req_headers
		)

		data = content
		if ( json_response ) :
			data = simplejson.loads( content )

		self.req_cache[req_url] = {
			'data'	: data,
			'expire': now + self.req_expire
		}

		return self.req_cache[req_url]['data']

	def write( self, path, buf, offset ) :
		self.write_files[path]['size'] += len( buf )

		new_data = self.write_files[path]['data'][:offset] + buf
		self.write_files[path]['data'] = new_data

		return len( buf )

if ( __name__ == '__main__' ) :
	fs = PressFS()
	fs.parse( errex = 1 )
	fs.main()

########NEW FILE########
