__FILENAME__ = echonest
import os
import simplejson
import urllib
import urllib2
import logging
from pyechonest import config, artist, song

logging.basicConfig(level=logging.DEBUG)
config.ECHO_NEST_API_KEY="OCQQQWJBKZXHKPXHZ"

def prompt():
    userinput = raw_input("Gimme an artist: ")
    if not userinput:
        exit()
    
    print dance_songs(get_artist_id(userinput))

def get_artist_id(artist_name):
    result = artist.search(name=artist_name)
    if not result:
        return False
    return result[0].id

def dance_songs(artist_id, dance=0.6, maxresults=10):
    results = song.search(artist_id=artist_id,
                          min_danceability=dance,
                          results=maxresults,
                          sort='danceability-desc',
                          buckets=['audio_summary'])
    return results



if __name__ == '__main__':
    prompt()
    
                                         

########NEW FILE########
__FILENAME__ = face_client
# -*- coding: utf-8 -*-
#
# Name: face.com Python API client library
# Description: face.com REST API Python client library.
#
# For more information about the API and the return values,
# visit the official documentation at http://developers.face.com/docs/api/.
#
# Author: Tomaž Muraus (http://www.tomaz-muraus.info)
# License: GPL (http://www.gnu.org/licenses/gpl.html)
# Version: 1.0

import urllib
import urllib2
import simplejson as json
import os.path

API_URL	= 'http://api.face.com'

class FaceClient(object):
	def __init__(self, api_key = None, api_secret = None):
		if not api_key or not api_secret:
			raise AttributeError('Missing api_key or api_secret argument')

		self.api_key 				= api_key
		self.api_secret 			= api_secret
		self.format 				= 'json'

		self.twitter_credentials	= None
		self.facebook_credentials 	= None

	def set_twitter_user_credentials(self, user = None, password = None):
		if not user or not password:
			raise AttributeError('Missing Twitter username or password')

		self.twitter_credentials = {'twitter_user': user,
									'twitter_password': password}

	def set_twitter_oauth_credentials(self, user = None, secret = None, token = None):
		if not user or not secret or not token:
			raise AttributeError('Missing one of the required arguments')

		self.twitter_credentials = {'twitter_oauth_user': user,
									'twitter_oauth_secret': secret,
									'twitter_oauth_token': token}

	def set_facebook_credentials(self, user = None, session = None):
		if not user or not session:
			raise AttributeError('Missing Facebook user or session argument')

		self.facebook_credentials = {'fb_user': user,
									'fb_session': session}

	### Recognition engine methods ###
	def faces_detect(self, urls = None, file = None, aggressive=False):
		"""
		Returns tags for detected faces in one or more photos, with geometric information
		of the tag, eyes, nose and mouth, as well as the gender, glasses, and smiling attributes.

		http://developers.face.com/docs/api/faces-detect/
		"""
		if not urls and not file:
			raise AttributeError('Missing URLs/filename argument')

		if file:
			# Check if the file exists
			if not os.path.exists(file):
				raise IOError('File %s does not exist' % (file))

			data = {'file': file}
		else:
			data = {'urls': urls}

		if aggressive:
			data['detector'] = 'Aggressive'

		response = self.send_request('faces/detect', data)
		return response

	def faces_status(self, uids = None, namespace = None):
		"""
		Reports training set status for the specified UIDs.

		http://developers.face.com/docs/api/faces-status/
		"""
		if not uids:
			raise AttributeError('Missing user IDs')

		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uids)

		data = {'uids': uids}
		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, namespace = namespace)

		response = self.send_request('faces/status', data)
		return response

	def faces_recognize(self, uids = None, urls = None, file = None, train = None, \
						namespace = None, aggressive = None):
		"""
		Attempts to detect and recognize one or more user IDs' faces, in one or more photos.
		For each detected face, the face.com engine will return the most likely user IDs,
		or empty result for unrecognized faces. In addition, each tag includes a threshold
		score - any score below this number is considered a low-probability hit.

		http://developers.face.com/docs/api/faces-recognize/
		"""
		if not uids or (not urls and not file):
			raise AttributeError('Missing required arguments')

		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uids)

		data = {'uids': uids}

		if file:
			# Check if the file exists
			if not os.path.exists(file):
				raise IOError('File %s does not exist' % (file))

			data.update({'file': file})
		else:
			data.update({'urls': urls})

		if aggressive:
			data['detector'] = 'Aggressive'

		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, train = train, namespace = namespace)

		response = self.send_request('faces/recognize', data)
		return response

	def faces_train(self, uids = None, namespace = None, callback = None):
		"""
		Calls the training procedure for the specified UIDs, and reports back changes.

		http://developers.face.com/docs/api/faces-train/
		"""
		if not uids:
			raise AttributeError('Missing user IDs')

		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uids)

		data = {'uids': uids}
		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, namespace = namespace, callback = callback)

		response = self.send_request('faces/train', data)
		return response

	### Methods for managing face tags ###
	def tags_get(self, uids = None, urls = None, pids = None, order = 'recent', \
				limit = 5, together = False, filter = None, namespace = None):
		"""
		Returns saved tags in one or more photos, or for the specified User ID(s).
		This method also accepts multiple filters for finding tags corresponding to
		a more specific criteria such as front-facing, recent, or where two or more
		users appear together in same photos.

		http://developers.face.com/docs/api/tags-get/
		"""
		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uids)

		data = {'uids': uids,
				'urls': urls,
				'together': together,
				'limit': limit}
		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, pids = pids, filter = filter, \
										namespace = namespace)

		response = self.send_request('tags/get', data)
		return response

	def tags_add(self, url = None, x = None, y = None, width = None, uid = None, \
				tagger_id = None, label = None, password = None):
		"""
		Add a (manual) face tag to a photo. Use this method to add face tags where
		those were not detected for completeness of your service.

		http://developers.face.com/docs/api/tags-add/
		"""
		if not url or not x or not y or not width or not uid or not tagger_id:
			raise AttributeError('Missing one of the required arguments')

		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uid)

		data = {'url': url,
				'x': x,
				'y': y,
				'width': width,
				'uid': uid,
				'tagger_id': tagger_id}
		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, label = label, password = password)

		response = self.send_request('tags/add', data)
		return response

	def tags_save(self, tids = None, uid = None, tagger_id = None, label = None, \
				password = None):
		"""
		Saves a face tag. Use this method to save tags for training the face.com
		index, or for future use of the faces.detect and tags.get methods.

		http://developers.face.com/docs/api/tags-save/
		"""
		if not tids or not uid:
			raise AttributeError('Missing required argument')

		(facebook_uids, twitter_uids) = self.__check_user_auth_credentials(uid)

		data = {'tids': tids,
				'uid': uid}
		self.__append_user_auth_data(data, facebook_uids, twitter_uids)
		self.__append_optional_arguments(data, tagger_id = tagger_id, label = label, \
										password = password)

		response = self.send_request('tags/save', data)
		return response

	def tags_remove(self, tids = None, password = None):
		"""
		Remove a previously saved face tag from a photo.

		http://developers.face.com/docs/api/tags-remove/
		"""
		if not tids:
			raise AttributeError('Missing tag IDs')

		data = {'tids': tids}

		response = self.send_request('tags/remove', data)
		return response

	### Account management methods ###
	def account_limits(self):
		"""
		Returns current rate limits for the account represented by the passed API key and Secret.

		http://developers.face.com/docs/api/account-limits/
		"""
		response = self.send_request('account/limits')
		return response['usage']

	def account_users(self, namespaces = None):
		"""
		Returns current rate limits for the account represented by the passed API key and Secret.

		http://developers.face.com/docs/api/account-limits/
		"""
		if not namespaces:
			raise AttributeError('Missing namespaces argument')

		response = self.send_request('account/users', {'namespaces': namespaces})

		return response

	def __check_user_auth_credentials(self, uids):
		# Check if needed credentials are provided
		facebook_uids = [uid for uid in uids.split(',') \
						if uid.find('@facebook.com') != -1]
		twitter_uids = [uid for uid in uids.split(',') \
						if uid.find('@twitter.com') != -1]

		if facebook_uids and not self.facebook_credentials:
			raise AttributeError('You need to set Facebook credentials to perform action on Facebook users')

		if twitter_uids and not self.twitter_credentials:
			raise AttributeError('You need to set Twitter credentials to perform action on Twitter users')

		return (facebook_uids, twitter_uids)

	def __append_user_auth_data(self, data, facebook_uids, twitter_uids):
		if facebook_uids:
			data.update({'user_auth': 'fb_user:%s,fb_oauth_token:%s' % (self.facebook_credentials['fb_user'],
						 self.facebook_credentials['fb_session'])})

		if twitter_uids:
			# If both user/password and OAuth credentials are provided, use
			# OAuth as default
			if self.twitter_credentials.get('twitter_oauth_user', None):
				data.update({'user_auth': 'twitter_oauth_user:%s,twitter_oauth_secret:%s,twitter_oauth_token:%s' %
							(self.twitter_credentials['twitter_oauth_user'], self.twitter_credentials['twitter_oauth_secret'], \
							self.twitter_credentials['twitter_oauth_token'])})
			else:
				data.update({'user_auth': 'twitter_user:%s,twitter_password:%s' % (self.twitter_credentials['twitter_user'],
							 self.twitter_credentials['twitter_password'])})

	def __append_optional_arguments(self, data, **kwargs):
		for key, value in kwargs.iteritems():
			if value:
				data.update({key: value})

	def send_request(self, method = None, parameters = None):
		url = '%s/%s' % (API_URL, method)

		data = {'api_key': self.api_key,
				'api_secret': self.api_secret,
				'format': self.format}

		if parameters:
			data.update(parameters)
		# raise Exception(url, data)
		# Local file is provided, use multi-part form
		if 'file' in parameters:
			from multipart import Multipart
			form = Multipart()

			for key, value in data.iteritems():

				if key == 'file':
					file = open(value, 'r')
					# with open(value, 'r') as file:
					form.file(os.path.basename(key), os.path.basename(key), file.read())
				else:
					form.field(key, value)

			(content_type, post_data) = form.get()
			headers = {'Content-Type': content_type}
		else:
			post_data = urllib.urlencode(data)
			headers = {}

		request = urllib2.Request(url, headers = headers, data = post_data)
		response = urllib2.urlopen(request)
		response = response.read()
		response_data = json.loads(response)

		if 'status' in response_data and \
			response_data['status'] == 'failure':
			raise FaceError(response_data['error_code'], response_data['error_message'])

		return response_data

class FaceError(Exception):
	def __init__(self, error_code, error_message):
		self.error_code = error_code
		self.error_message = error_message

	def __str__(self):
		return '%s (%d)' % (self.error_message, self.error_code)

########NEW FILE########
__FILENAME__ = multipart
'''
Classes for using multipart form data from Python, which does not (at the
time of writing) support this directly.
 
To use this, make an instance of Multipart and add parts to it via the factory
methods field and file.  When you are done, get the content via the get method.
 
@author: Stacy Prowell (http://stacyprowell.com)
'''
 
import mimetypes
 
class Part(object):
	'''
	Class holding a single part of the form.  You should never need to use
	this class directly; instead, use the factory methods in Multipart:
	field and file.
	'''
 
	# The boundary to use.  This is shamelessly taken from the standard.
	BOUNDARY = '----------AaB03x'
	CRLF = '\r\n'
	# Common headers.
	CONTENT_TYPE = 'Content-Type'
	CONTENT_DISPOSITION = 'Content-Disposition'
	# The default content type for parts.
	DEFAULT_CONTENT_TYPE = 'application/octet-stream'
 
	def __init__(self, name, filename, body, headers):
		'''
		Make a new part.  The part will have the given headers added initially.
 
		@param name: The part name.
		@type name: str
		@param filename: If this is a file, the name of the file.  Otherwise
						None.
		@type filename: str
		@param body: The body of the part.
		@type body: str
		@param headers: Additional headers, or overrides, for this part.
						You can override Content-Type here.
		@type headers: dict
		'''
		self._headers = headers.copy()
		self._name = name
		self._filename = filename
		self._body = body
		# We respect any content type passed in, but otherwise set it here.
		# We set the content disposition now, overwriting any prior value.
		if self._filename == None:
			self._headers[Part.CONTENT_DISPOSITION] = \
				('form-data; name="%s"' % self._name)
			self._headers.setdefault(Part.CONTENT_TYPE,
									 Part.DEFAULT_CONTENT_TYPE)
		else:
			self._headers[Part.CONTENT_DISPOSITION] = \
				('form-data; name="%s"; filename="%s"' %
				 (self._name, self._filename))
			self._headers.setdefault(Part.CONTENT_TYPE,
									 mimetypes.guess_type(filename)[0]
									 or Part.DEFAULT_CONTENT_TYPE)
		return
 
	def get(self):
		'''
		Convert the part into a list of lines for output.  This includes
		the boundary lines, part header lines, and the part itself.  A
		blank line is included between the header and the body.
 
		@return: Lines of this part.
		@rtype: list
		'''
		lines = []
		lines.append('--' + Part.BOUNDARY)
		for (key, val) in self._headers.items():
			lines.append('%s: %s' % (key, val))
		lines.append('')
		lines.append(self._body)
		return lines
 
class Multipart(object):
	'''
	Encapsulate multipart form data.  To use this, make an instance and then
	add parts to it via the two methods (field and file).  When done, you can
	get the result via the get method.
 
	See http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4.2 for
	details on multipart/form-data.
 
	Watch http://bugs.python.org/issue3244 to see if this is fixed in the
	Python libraries.
 
	@return: content type, body
	@rtype: tuple
	'''
 
	def __init__(self):
		self.parts = []
		return
 
	def field(self, name, value, headers={}):
		'''
		Create and append a field part.  This kind of part has a field name
		and value.
 
		@param name: The field name.
		@type name: str
		@param value: The field value.
		@type value: str
		@param headers: Headers to set in addition to disposition.
		@type headers: dict
		'''
		self.parts.append(Part(name, None, value, headers))
		return
 
	def file(self, name, filename, value, headers={}):
		'''
		Create and append a file part.  THis kind of part has a field name,
		a filename, and a value.
 
		@param name: The field name.
		@type name: str
		@param value: The field value.
		@type value: str
		@param headers: Headers to set in addition to disposition.
		@type headers: dict
		'''
		self.parts.append(Part(name, filename, value, headers))
		return
 
	def get(self):
		'''
		Get the multipart form data.  This returns the content type, which
		specifies the boundary marker, and also returns the body containing
		all parts and bondary markers.
 
		@return: content type, body
		@rtype: tuple
		'''
		all = []
		for part in self.parts:
			all += part.get()
		all.append('--' + Part.BOUNDARY + '--')
		all.append('')
		# We have to return the content type, since it specifies the boundary.
		content_type = 'multipart/form-data; boundary=%s' % Part.BOUNDARY
		return content_type, Part.CRLF.join(all)
########NEW FILE########
__FILENAME__ = artist
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.

The Artist module loosely covers http://developer.echonest.com/docs/v4/artist.html
Refer to the official api documentation if you are unsure about something.
"""
import util
from proxies import ArtistProxy, ResultList
from song import Song


class Artist(ArtistProxy):
    """
    An Artist object
    
    Attributes: 
        id (str): Echo Nest Artist ID
        
        name (str): Artist Name
        
        audio (list): Artist audio
        
        biographies (list): Artist biographies
        
        blogs (list): Artist blogs
        
        familiarity (float): Artist familiarity
        
        hotttnesss (float): Artist hotttnesss
        
        images (list): Artist images
        
        news (list): Artist news
        
        reviews (list): Artist reviews
        
        similar (list): Similar Artists
        
        songs (list): A list of song objects
        
        terms (list): Terms for an artist
        
        urls (list): Artist urls
        
        video (list): Artist video
        
    You create an artist object like this:
    
    >>> a = artist.Artist('ARH6W4X1187B99274F')
    >>> a = artist.Artist('the national')
    >>> a = artist.Artist('musicbrainz:artist:a74b1b7f-71a5-4011-9441-d0b5e4122711')
        
    """

    def __init__(self, id, **kwargs):
        """
        Artist class
        
        Args:
            id (str): an artistw ID 
            
        Returns:
            An artist object
            
        Example:
        
        >>> a = artist.Artist('ARH6W4X1187B99274F', buckets=['hotttnesss'])
        >>> a.hotttnesss
        0.80098515900997658
        >>>
        
        """
        super(Artist, self).__init__(id, **kwargs)    
    
    def __repr__(self):
        return "<%s - %s>" % (self._object_type.encode('utf-8'), self.name.encode('utf-8'))
    
    def __str__(self):
        return self.name.encode('utf-8')
    
    def __cmp__(self, other):
        return cmp(self.id, other.id)
    
    def get_audio(self, results=15, start=0, cache=True):
        """Get a list of audio documents found on the web related to an artist
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
        
        Returns:
            A list of audio document dicts; list contains additional attributes 'start' and 'total'
        
        Example:

        >>> a = artist.Artist('alphabeat')
        >>> a.get_audio()[0]
        {u'artist': u'Alphabeat',
         u'date': u'2010-04-28T01:40:45',
         u'id': u'70be4373fa57ac2eee8c7f30b0580899',
         u'length': 210.0,
         u'link': u'http://iamthecrime.com',
         u'release': u'The Beat Is...',
         u'title': u'DJ',
         u'url': u'http://iamthecrime.com/wp-content/uploads/2010/04/03_DJ_iatc.mp3'}
        >>> 
        """
        
        if cache and ('audio' in self.cache) and results==15 and start==0:
            return self.cache['audio']
        else:
            response = self.get_attribute('audio', results=results, start=start)
            if results==15 and start==0:
                self.cache['audio'] = ResultList(response['audio'], 0, response['total'])
            return ResultList(response['audio'], start, response['total'])
    
    audio = property(get_audio)
    
    def get_biographies(self, results=15, start=0, license='unknown', cache=True):
        """Get a list of artist biographies
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
            
            license (str): A string specifying the desired license type
        
        Returns:
            A list of biography document dicts; list contains additional attributes 'start' and 'total'
            
        Example:

        >>> a = artist.Artist('britney spears')
        >>> bio = a.get_biographies(results=1)[0]
        >>> bio['url']
        u'http://www.mtvmusic.com/spears_britney'
        >>> 
        """
        if cache and ('biographies' in self.cache) and results==15 and start==0 and license=='unknown':
            return self.cache['biographies']
        else:
            response = self.get_attribute('biographies', results=results, start=start, license=license)
            if results==15 and start==0 and license=='unknown':
                self.cache['biographies'] = ResultList(response['biographies'], 0, response['total'])
            return ResultList(response['biographies'], start, response['total'])
    
    biographies = property(get_biographies)    
    
    def get_blogs(self, results=15, start=0, cache=True, high_relevance=False):
        """Get a list of blog articles related to an artist
        
        Args:
            
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An ingteger starting value for the result set
        
        Returns:
            A list of blog document dicts; list contains additional attributes 'start' and 'total'
        
        Example:
        
        >>> a = artist.Artist('bob marley')
        >>> blogs = a.get_blogs(results=1,start=4)
        >>> blogs.total
        4068
        >>> blogs[0]['summary']
        But the Kenyans I know relate to music about the same way Americans do. They like their Congolese afropop, 
        and I've known some to be big fans of international acts like <span>Bob</span> <span>Marley</span> and Dolly Parton. 
        They rarely talk about music that's indigenous in the way a South African or Malian or Zimbabwean would, and it's 
        even rarer to actually hear such indigenous music. I do sometimes hear ceremonial chanting from the Maasai, but only 
        when they're dancing for tourists. If East Africa isn't the most musical part ... "
        >>> 
        """

        if cache and ('blogs' in self.cache) and results==15 and start==0 and not high_relevance:
            return self.cache['blogs']
        else:
            if high_relevance:
                high_relevance = 'true'
            else:
                high_relevance ='false'
            response = self.get_attribute('blogs', results=results, start=start, high_relevance=high_relevance)
            if results==15 and start==0:
                self.cache['blogs'] = ResultList(response['blogs'], 0, response['total'])
            return ResultList(response['blogs'], start, response['total'])
    
    blogs = property(get_blogs)
       
    def get_familiarity(self, cache=True):
        """Get our numerical estimation of how familiar an artist currently is to the world
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            A float representing familiarity.
        
        Example:

        >>> a = artist.Artist('frank sinatra')
        >>> a.get_familiarity()
        0.65142555825947457
        >>> a.familiarity
        0.65142555825947457
        >>>
        """
        if not (cache and ('familiarity' in self.cache)):
            response = self.get_attribute('familiarity')
            self.cache['familiarity'] = response['artist']['familiarity']
        return self.cache['familiarity']
    
    familiarity = property(get_familiarity)    

    def get_foreign_id(self, idspace='musicbrainz', cache=True):
        """Get the foreign id for this artist for a specific id space
        
        Args:
        
        Kwargs:
            idspace (str): A string indicating the idspace to fetch a foreign id for.
        
        Returns:
            A foreign ID string
        
        Example:
        
        >>> a = artist.Artist('fabulous')
        >>> a.get_foreign_id('7digital')
        u'7digital:artist:186042'
        >>> 
        """
        if not (cache and ('foreign_ids' in self.cache) and filter(lambda d: d.get('catalog') == idspace, self.cache['foreign_ids'])):
            response = self.get_attribute('profile', bucket=['id:'+idspace])
            foreign_ids = response['artist'].get("foreign_ids", [])
            self.cache['foreign_ids'] = self.cache.get('foreign_ids', []) + foreign_ids
        cval = filter(lambda d: d.get('catalog') == idspace, self.cache.get('foreign_ids'))
        if cval:
            return cval[0].get('foreign_id')
        else:
            return None
    
    def get_hotttnesss(self, cache=True):
        """Get our numerical description of how hottt an artist currently is
        
        Args:
            
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            float: the hotttnesss value
        
        Example:
        
        >>> a = artist.Artist('hannah montana')
        >>> a.get_hotttnesss()
        0.59906022155998995
        >>> a.hotttnesss
        0.59906022155998995
        >>>
        """
        if not (cache and ('hotttnesss' in self.cache)):
            response = self.get_attribute('hotttnesss')
            self.cache['hotttnesss'] = response['artist']['hotttnesss']
        return self.cache['hotttnesss']
    
    hotttnesss = property(get_hotttnesss)
    
    def get_images(self, results=15, start=0, license='unknown', cache=True):
        """Get a list of artist images
        
        Args:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
            
            license (str): A string specifying the desired license type
        
        Returns:
            A list of image document dicts; list contains additional attributes 'start' and 'total'
        
        Example:
        
        >>> a = artist.Artist('Captain Beefheart')
        >>> images = a.get_images(results=1)
        >>> images.total
        49
        >>> images[0]['url']
        u'http://c4.ac-images.myspacecdn.com/images01/5/l_e1a329cdfdb16a848288edc6d578730f.jpg'
        >>> 
        """
        
        if cache and ('images' in self.cache) and results==15 and start==0 and license=='unknown':
            return self.cache['images']
        else:
            response = self.get_attribute('images', results=results, start=start, license=license)
            if results==15 and start==0 and license=='unknown':
                self.cache['images'] = ResultList(response['images'], 0, response['total'])
            return ResultList(response['images'], start, response['total'])
    
    images = property(get_images)    
    
    def get_news(self, results=15, start=0, cache=True, high_relevance=False):
        """Get a list of news articles found on the web related to an artist
        
        Args:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
        
        Returns:
            A list of news document dicts; list contains additional attributes 'start' and 'total'
        
        Example:
        
        >>> a = artist.Artist('Henry Threadgill')
        >>> news = a.news
        >>> news.total
        41
        >>> news[0]['name']
        u'Jazz Journalists Association Announces 2010 Jazz Award Winners'
        >>> 
        """
        if cache and ('news' in self.cache) and results==15 and start==0 and not high_relevance:
            return self.cache['news']
        else:
            if high_relevance:
                high_relevance = 'true'
            else:
                high_relevance = 'false'                
            response = self.get_attribute('news', results=results, start=start, high_relevance=high_relevance)
            if results==15 and start==0:
                self.cache['news'] = ResultList(response['news'], 0, response['total'])
            return ResultList(response['news'], start, response['total'])
    
    news = property(get_news)
    
    def get_reviews(self, results=15, start=0, cache=True):
        """Get reviews related to an artist's work
        
        Args:
            
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
        
        Returns:
            A list of review document dicts; list contains additional attributes 'start' and 'total'
        
        Example:
        
        >>> a = artist.Artist('Ennio Morricone')
        >>> reviews = a.reviews
        >>> reviews.total
        17
        >>> reviews[0]['release']
        u'For A Few Dollars More'
        >>> 
        """
        if cache and ('reviews' in self.cache) and results==15 and start==0:
            return self.cache['reviews']
        else:
            response = self.get_attribute('reviews', results=results, start=start)
            if results==15 and start==0:
                self.cache['reviews'] = ResultList(response['reviews'], 0, response['total'])
            return ResultList(response['reviews'], start, response['total'])
    
    reviews = property(get_reviews)
    
    def get_similar(self, results=15, start=0, buckets=None, limit=False, cache=True, max_familiarity=None, min_familiarity=None, \
                    max_hotttnesss=None, min_hotttnesss=None, min_results=None, reverse=False):
        """Return similar artists to this one
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
            
            max_familiarity (float): A float specifying the max familiarity of artists to search for
            
            min_familiarity (float): A float specifying the min familiarity of artists to search for
            
            max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
            
            min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
            
            reverse (bool): A boolean indicating whether or not to return dissimilar artists (wrecommender). Defaults to False.
        
        Returns:
            A list of similar Artist objects
        
        Example:
        
        >>> a = artist.Artist('Sleater Kinney')
        >>> similars = a.similar[:5]
        >>> similars
        [<artist - Bikini Kill>, <artist - Pretty Girls Make Graves>, <artist - Huggy Bear>, <artist - Bratmobile>, <artist - Team Dresch>]
        >>> 
        """
        buckets = buckets or []
        kwargs = {}
        if max_familiarity:
            kwargs['max_familiarity'] = max_familiarity
        if min_familiarity:
            kwargs['min_familiarity'] = min_familiarity
        if max_hotttnesss:
            kwargs['max_hotttnesss'] = max_hotttnesss
        if min_hotttnesss:
            kwargs['min_hotttnesss'] = min_hotttnesss
        if min_results:
            kwargs['min_results'] = min_results
        if buckets:
            kwargs['bucket'] = buckets
        if limit:
            kwargs['limit'] = 'true'
        if reverse:
            kwargs['reverse'] = 'true'
        
        if cache and ('similar' in self.cache) and results==15 and start==0 and (not kwargs):
            return [Artist(**util.fix(a)) for a in self.cache['similar']]
        else:
            response = self.get_attribute('similar', results=results, start=start, **kwargs)
            if results==15 and start==0 and (not kwargs):
                self.cache['similar'] = response['artists']
            return [Artist(**util.fix(a)) for a in response['artists']]
    
    similar = property(get_similar)    
    
    def get_songs(self, cache=True, results=15, start=0):
        """Get the songs associated with an artist
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
            
        Results:
            A list of Song objects; list contains additional attributes 'start' and 'total'
        
        Example:

        >>> a = artist.Artist('Strokes')
        >>> a.get_songs(results=5)
        [<song - Fear Of Sleep>, <song - Red Light>, <song - Ize Of The World>, <song - Evening Sun>, <song - Juicebox>]
        >>> 
        """

        if cache and ('songs' in self.cache) and results==15 and start==0:
            return self.cache['songs']
        else:
            response = self.get_attribute('songs', results=results, start=start)
            for s in response['songs']:
                s.update({'artist_id':self.id, 'artist_name':self.name})
            songs = [Song(**util.fix(s)) for s in response['songs']]
            if results==15 and start==0:
                self.cache['songs'] = ResultList(songs, 0, response['total'])
            return ResultList(songs, start, response['total'])
    
    songs = property(get_songs)

    def get_terms(self, sort='weight', cache=True):
        """Get the terms associated with an artist
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            sort (str): A string specifying the desired sorting type (weight or frequency)
            
        Results:
            A list of term document dicts
            
        Example:

        >>> a = artist.Artist('tom petty')
        >>> a.terms
        [{u'frequency': 1.0, u'name': u'heartland rock', u'weight': 1.0},
         {u'frequency': 0.88569401860168606,
          u'name': u'jam band',
          u'weight': 0.9116501862732439},
         {u'frequency': 0.9656145118557401,
          u'name': u'pop rock',
          u'weight': 0.89777934440040685},
         {u'frequency': 0.8414744288140491,
          u'name': u'southern rock',
          u'weight': 0.8698567153186606},
         {u'frequency': 0.9656145118557401,
          u'name': u'hard rock',
          u'weight': 0.85738022655218893},
         {u'frequency': 0.88569401860168606,
          u'name': u'singer-songwriter',
          u'weight': 0.77427243392312772},
         {u'frequency': 0.88569401860168606,
          u'name': u'rock',
          u'weight': 0.71158718989399083},
         {u'frequency': 0.60874110500110956,
          u'name': u'album rock',
          u'weight': 0.69758668733499629},
         {u'frequency': 0.74350792060935744,
          u'name': u'psychedelic',
          u'weight': 0.68457367494207944},
         {u'frequency': 0.77213698386292873,
          u'name': u'pop',
          u'weight': 0.65039556639337293},
         {u'frequency': 0.41747136183050298,
          u'name': u'bar band',
          u'weight': 0.54974975024767025}]
        >>> 

        """
        if cache and ('terms' in self.cache) and sort=='weight':
            return self.cache['terms']
        else:
            response = self.get_attribute('terms', sort=sort)
            if sort=='weight':
                self.cache['terms'] = response['terms']
            return response['terms']
    
    terms = property(get_terms)
    
    def get_urls(self, cache=True):
        """Get the urls for an artist
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
        Results:
            A url document dict
            
        Example:

        >>> a = artist.Artist('the unicorns')
        >>> a.get_urls()
        {u'amazon_url': u'http://www.amazon.com/gp/search?ie=UTF8&keywords=The Unicorns&tag=httpechonecom-20&index=music',
         u'aolmusic_url': u'http://music.aol.com/artist/the-unicorns',
         u'itunes_url': u'http://itunes.com/TheUnicorns',
         u'lastfm_url': u'http://www.last.fm/music/The+Unicorns',
         u'mb_url': u'http://musicbrainz.org/artist/603c5f9f-492a-4f21-9d6f-1642a5dbea2d.html',
         u'myspace_url': u'http://www.myspace.com/iwasbornunicorn'}
        >>> 

        """
        if not (cache and ('urls' in self.cache)):
            response = self.get_attribute('urls')
            self.cache['urls'] = response['urls']
        return self.cache['urls']
    
    urls = property(get_urls)    
    
    def get_video(self, results=15, start=0, cache=True):
        """Get a list of video documents found on the web related to an artist
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
        
        Returns:
            A list of video document dicts; list contains additional attributes 'start' and 'total'
            
        Example:

        >>> a = artist.Artist('the vapors')
        >>> a.get_video(results=1, start=2)
        [{u'date_found': u'2009-12-28T08:27:48',
          u'id': u'd02f9e6dc7904f70402d4676516286b9',
          u'image_url': u'http://i1.ytimg.com/vi/p6c0wOFL3Us/default.jpg',
          u'site': u'youtube',
          u'title': u'The Vapors-Turning Japanese (rectangular white vinyl promo)',
          u'url': u'http://youtube.com/watch?v=p6c0wOFL3Us'}]
        >>> 

        """
        if cache and ('video' in self.cache) and results==15 and start==0:
            return self.cache['video']
        else:
            response = self.get_attribute('video', results=results, start=start)
            if results==15 and start==0:
                self.cache['video'] = ResultList(response['video'], 0, response['total'])
            return ResultList(response['video'], start, response['total'])
    
    video = property(get_video)

def search(name=None, description=None, results=15, buckets=None, limit=False, \
            fuzzy_match=False, sort=None, max_familiarity=None, min_familiarity=None, \
            max_hotttnesss=None, min_hotttnesss=None):
    """Search for artists by name, description, or constraint.
    
    Args:
    
    Kwargs:
        name (str): the name of an artist
        
        description (str): A string describing the artist
        
        results (int): An integer number of results to return
        
        buckets (list): A list of strings specifying which buckets to retrieve
        
        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets
        
        fuzzy_match (bool): A boolean indicating whether or not to search for similar sounding matches (only works with name)
        
        max_familiarity (float): A float specifying the max familiarity of artists to search for
        
        min_familiarity (float): A float specifying the min familiarity of artists to search for
        
        max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
        
        min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
    
    Returns:
        A list of Artist objects
    
    Example:
    
    >>> results = artist.search(name='t-pain')
    >>> results
    [<artist - T-Pain>, <artist - T-Pain & Lil Wayne>, <artist - T Pain & 2 Pistols>, <artist - Roscoe Dash & T-Pain>, <artist - Tony Moxberg & T-Pain>, <artist - Flo-Rida (feat. T-Pain)>, <artist - Shortyo/Too Short/T-Pain>]
    >>> 

    """
    buckets = buckets or []
    kwargs = {}
    if name:
        kwargs['name'] = name
    if description:
        kwargs['description'] = description
    if results:
        kwargs['results'] = results
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'
    if fuzzy_match:
        kwargs['fuzzy_match'] = 'true'
    if max_familiarity is not None:
        kwargs['max_familiarity'] = max_familiarity
    if min_familiarity is not None:
        kwargs['min_familiarity'] = min_familiarity
    if max_hotttnesss is not None:
        kwargs['max_hotttnesss'] = max_hotttnesss
    if min_hotttnesss is not None:
        kwargs['min_hotttnesss'] = min_hotttnesss
    if sort:
        kwargs['sort'] = sort
    
    """Search for artists"""
    result = util.callm("%s/%s" % ('artist', 'search'), kwargs)
    return [Artist(**util.fix(a_dict)) for a_dict in result['response']['artists']]

def top_hottt(start=0, results=15, buckets = None, limit=False):
    """Get the top hotttest artists, according to The Echo Nest
    
    Args:
    
    Kwargs:
        results (int): An integer number of results to return
        
        start (int): An integer starting value for the result set
        
        buckets (list): A list of strings specifying which buckets to retrieve
        
        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets
        
    Returns:
        A list of hottt Artist objects

    Example:

    >>> hot_stuff = artist.top_hottt()
    >>> hot_stuff
    [<artist - Deerhunter>, <artist - Sufjan Stevens>, <artist - Belle and Sebastian>, <artist - Glee Cast>, <artist - Linkin Park>, <artist - Neil Young>, <artist - Jimmy Eat World>, <artist - Kanye West>, <artist - Katy Perry>, <artist - Bruno Mars>, <artist - Lady Gaga>, <artist - Rihanna>, <artist - Lil Wayne>, <artist - Jason Mraz>, <artist - Green Day>]
    >>> 

    """
    buckets = buckets or []
    kwargs = {}
    if start:
        kwargs['start'] = start
    if results:
        kwargs['results'] = results
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'
    
    """Get top hottt artists"""
    result = util.callm("%s/%s" % ('artist', 'top_hottt'), kwargs)
    return [Artist(**util.fix(a_dict)) for a_dict in result['response']['artists']]    


def top_terms(results=15):
    """Get a list of the top overall terms
        
    Args:
    
    Kwargs:
        results (int): An integer number of results to return
        
    Returns:
        A list of term document dicts
    
    Example:
    
    >>> terms = artist.top_terms(results=5)
    >>> terms
    [{u'frequency': 1.0, u'name': u'rock'},
     {u'frequency': 0.99054710039307992, u'name': u'electronic'},
     {u'frequency': 0.96131624654034398, u'name': u'hip hop'},
     {u'frequency': 0.94358477322411127, u'name': u'jazz'},
     {u'frequency': 0.94023302416455468, u'name': u'pop rock'}]
    >>> 
    """
    
    kwargs = {}
    if results:
        kwargs['results'] = results
    
    """Get top terms"""
    result = util.callm("%s/%s" % ('artist', 'top_terms'), kwargs)
    return result['response']['terms']


def similar(names=None, ids=None, start=0, results=15, buckets=None, limit=False, max_familiarity=None, min_familiarity=None,
            max_hotttnesss=None, min_hotttnesss=None):
    """Return similar artists to this one
    
    Args:
    
    Kwargs:
        ids (str/list): An artist id or list of ids
        
        names (str/list): An artist name or list of names
        
        results (int): An integer number of results to return
        
        buckets (list): A list of strings specifying which buckets to retrieve
        
        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets
        
        start (int): An integer starting value for the result set
        
        max_familiarity (float): A float specifying the max familiarity of artists to search for
        
        min_familiarity (float): A float specifying the min familiarity of artists to search for
        
        max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
        
        min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
    
    Returns:
        A list of similar Artist objects
    
    Example:

    >>> some_dudes = [artist.Artist('weezer'), artist.Artist('radiohead')]
    >>> some_dudes
    [<artist - Weezer>, <artist - Radiohead>]
    >>> sims = artist.similar(ids=[art.id for art in some_dudes], results=5)
    >>> sims
    [<artist - The Smashing Pumpkins>, <artist - Biffy Clyro>, <artist - Death Cab for Cutie>, <artist - Jimmy Eat World>, <artist - Nerf Herder>]
    >>> 

    """
    
    buckets = buckets or []
    kwargs = {}

    if ids:
        if not isinstance(ids, list):
            ids = [ids]
        kwargs['id'] = ids
    if names:
        if not isinstance(names, list):
            names = [names]
        kwargs['name'] = names
    if max_familiarity is not None:
        kwargs['max_familiarity'] = max_familiarity
    if min_familiarity is not None:
        kwargs['min_familiarity'] = min_familiarity
    if max_hotttnesss is not None:
        kwargs['max_hotttnesss'] = max_hotttnesss
    if min_hotttnesss is not None:
        kwargs['min_hotttnesss'] = min_hotttnesss
    if start:
        kwargs['start'] = start
    if results:
        kwargs['results'] = results
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'

    result = util.callm("%s/%s" % ('artist', 'similar'), kwargs)
    return [Artist(**util.fix(a_dict)) for a_dict in result['response']['artists']]    


########NEW FILE########
__FILENAME__ = catalog
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Scotty Vercoe on 2010-08-25.

The Catalog module loosely covers http://developer.echonest.com/docs/v4/catalog.html
Refer to the official api documentation if you are unsure about something.
"""
try:
    import json
except ImportError:
    import simplejson as json
import datetime

import util
from proxies import CatalogProxy, ResultList
import artist, song

# deal with datetime in json
dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None

class Catalog(CatalogProxy):
    """
    A Catalog object
    
    Attributes:
        id (str): Catalog ID

        name (str): Catalog Name

    Create an catalog object like so:
    
    >>> c = catalog.Catalog('CAGPXKK12BB06F9DE9') # get existing catalog
    >>> c = catalog.Catalog('test_song_catalog', 'song') # get existing or create new catalog
    
    """
    def __init__(self, id, type=None, **kwargs):
        """
        Create a catalog object (get a catalog by ID or get or create one given by name and type)
        
        Args:
            id (str): A catalog id or name

        Kwargs:
            type (str): 'song' or 'artist', specifying the catalog type
            
        Returns:
            A catalog object
        
        Example:

        >>> c = catalog.Catalog('my_songs', type='song')
        >>> c.id
        u'CAVKUPC12BCA792120'
        >>> c.name
        u'my_songs'
        >>> 

        """
        super(Catalog, self).__init__(id, type, **kwargs)
    
    def __repr__(self):
        return "<%s - %s>" % (self._object_type.encode('utf-8'), self.name.encode('utf-8'))
    
    def __str__(self):
        return self.name.encode('utf-8')
    
    def update(self, items):
        """
        Update a catalog object
        
        Args:
            items (list): A list of dicts describing update data and action codes (see api docs)
        
        Kwargs:
            
        Returns:
            A ticket id
        
        Example:

        >>> c = catalog.Catalog('my_songs', type='song')
        >>> items 
        [{'action': 'update',
          'item': {'artist_name': 'dAn ThE aUtOmAtOr',
                   'disc_number': 1,
                   'genre': 'Instrumental',
                   'item_id': '38937DDF04BC7FC4',
                   'play_count': 5,
                   'release': 'Bombay the Hard Way: Guns, Cars & Sitars',
                   'song_name': 'Inspector Jay From Dehli',
                   'track_number': 9,
                   'url': 'file://localhost/Users/tylerw/Music/iTunes/iTunes%20Media/Music/Dan%20the%20Automator/Bombay%20the%20Hard%20Way_%20Guns,%20Cars%20&%20Sitars/09%20Inspector%20Jay%20From%20Dehli.m4a'}}]
        >>> ticket = c.update(items)
        >>> ticket
        u'7dcad583f2a38e6689d48a792b2e4c96'
        >>> c.status(ticket)
        {u'ticket_status': u'complete', u'update_info': []}
        >>> 
        
        """
        post_data = {}
        items_json = json.dumps(items, default=dthandler)
        post_data['data'] = items_json
        
        response = self.post_attribute("update", data=post_data)
        return response['ticket']
    
    def status(self, ticket):
        """
        Check the status of a catalog update
        
        Args:
            ticket (str): A string representing a ticket ID
            
        Kwargs:
            
        Returns:
            A dictionary representing ticket status
        
        Example:

        >>> ticket
        u'7dcad583f2a38e6689d48a792b2e4c96'
        >>> c.status(ticket)
        {u'ticket_status': u'complete', u'update_info': []}
        >>>
        
        """
        return self.get_attribute_simple("status", ticket=ticket)
    
    def get_profile(self):
        """
        Check the status of a catalog update
        
        Args:
            
        Kwargs:
            
        Returns:
            A dictionary representing ticket status
        
        Example:

        >>> c
        <catalog - test_song_catalog>
        >>> c.profile()
        {u'id': u'CAGPXKK12BB06F9DE9',
         u'name': u'test_song_catalog',
         u'pending_tickets': [],
         u'resolved': 2,
         u'total': 4,
         u'type': u'song'}
        >>> 
        
        """
        result = self.get_attribute("profile")
        return result['catalog']
    
    profile = property(get_profile)
    
    def read_items(self, buckets=None, results=15, start=0):
        """
        Returns data from the catalog; also expanded for the requested buckets
        
        Args:
            
        Kwargs:
            buckets (list): A list of strings specifying which buckets to retrieve
            
            results (int): An integer number of results to return
            
            start (int): An integer starting value for the result set
            
        Returns:
            A list of objects in the catalog; list contains additional attributes 'start' and 'total'
        
        Example:

        >>> c
        <catalog - my_songs>
        >>> c.read_items(results=1)
        [<song - Harmonice Mundi II>]
        >>>
        """
        kwargs = {}
        kwargs['bucket'] = buckets or []
        response = self.get_attribute("read", results=results, start=start, **kwargs)
        rval = ResultList([])
        rval.start = response['catalog']['start']
        rval.total = response['catalog']['total']
        for item in response['catalog']['items']:
            new_item = None
            # song item
            if 'song_id' in item:
                item['id'] = item.pop('song_id')
                item['title'] = item.pop('song_name')
                request = item['request']
                new_item = song.Song(**util.fix(item))
                new_item.request = request
            # artist item
            elif 'artist_id' in item:
                item['id'] = item.pop('artist_id')
                item['name'] = item.pop('artist_name')
                request = item['request']
                new_item = artist.Artist(**util.fix(item))
                new_item.request = request
            # unresolved item
            else:
                new_item = item
            rval.append(new_item)
        return rval
    
    read = property(read_items)

    def get_feed(self, buckets=None, since=None, results=15, start=0):
        """
        Returns feed (news, blogs, reviews, audio, video) for the catalog artists; response depends on requested buckets

        Args:

        Kwargs:
            buckets (list): A list of strings specifying which feed items to retrieve

            results (int): An integer number of results to return

            start (int): An integer starting value for the result set

        Returns:
            A list of news, blogs, reviews, audio or video document dicts; 

        Example:

        >>> c
        <catalog - my_artists>
        >>> c.get_feed(results=15)
	{u'date_found': u'2011-02-06T07:50:25',
	 u'date_posted': u'2011-02-06T07:50:23',
 	 u'id': u'caec686c0dff361e4c53dceb58fb9d2f',
 	 u'name': u'Linkin Park \u2013 \u201cWaiting For The End\u201d + \u201cWhen They Come For Me\u201d 2/5 SNL',
 	 u'references': [{u'artist_id': u'ARQUMH41187B9AF699',
        	          u'artist_name': u'Linkin Park'}],
	 u'summary': u'<span>Linkin</span> <span>Park</span> performed "Waiting For The End" and "When They Come For Me" on Saturday Night Live. Watch the videos below and pick up their album A Thousand Suns on iTunes, Amazon MP3, CD    Social Bookmarking ... ',
	 u'type': u'blogs',
	 u'url': u'http://theaudioperv.com/2011/02/06/linkin-park-waiting-for-the-end-when-they-come-for-me-25-snl/'}
        >>>
        """
        kwargs = {}
        kwargs['bucket'] = buckets or []
	if since:
		kwargs['since']=since  
        response = self.get_attribute("feed", results=results, start=start, **kwargs)
        rval = ResultList(response['feed'])
        return rval

    feed = property(get_feed)

    
    def delete(self):
        """
        Deletes the entire catalog
        
        Args:
            
        Kwargs:
            
        Returns:
            The deleted catalog's id.
        
        Example:

        >>> c
        <catalog - test_song_catalog>
        >>> c.delete()
        {u'id': u'CAXGUPY12BB087A21D'}
        >>>
        
        """
        return self.post_attribute("delete")
    

def list(results=30, start=0):
    """
    Returns list of all catalogs created on this API key
    
    Args:
        
    Kwargs:
        results (int): An integer number of results to return
        
        start (int): An integer starting value for the result set
        
    Returns:
        A list of catalog objects
    
    Example:

    >>> catalog.list()
    [<catalog - test_artist_catalog>, <catalog - test_song_catalog>, <catalog - my_songs>]
    >>> 

    
    """
    result = util.callm("%s/%s" % ('catalog', 'list'), {'results': results, 'start': start})
    return [Catalog(**util.fix(d)) for d in result['response']['catalogs']]
    

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.

Global configuration variables for accessing the Echo Nest web API.
"""

__version__ = "4.2.8"

import os

if('ECHO_NEST_API_KEY' in os.environ):
    ECHO_NEST_API_KEY = os.environ['ECHO_NEST_API_KEY']
else:
    ECHO_NEST_API_KEY = None


API_HOST = 'developer.echonest.com'

API_SELECTOR = 'api'
"Locations for the Analyze API calls."

API_VERSION = 'v4'
"Version of api to use... only 4 for now"

HTTP_USER_AGENT = 'PyEchonest'
"""
You may change this to be a user agent string of your
own choosing.
"""

MP3_BITRATE = 128
"""
Default bitrate for MP3 output. Conventionally an
integer divisible by 32kbits/sec.
"""

CACHE = True
"""
You may change this to False to prevent local caching
of API results.
"""

TRACE_API_CALLS = True
"""
If true, API calls will be traced to the console
"""

CALL_TIMEOUT = 10
"""
The API call timeout in seconds. 
"""

CODEGEN_BINARY_OVERRIDE = None
"""
Location of your codegen binary. If not given, we will guess codegen.platform-architecture on your system path, e.g. codegen.Darwin, codegen.Linux-i386
"""

########NEW FILE########
__FILENAME__ = playlist
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.

The Playlist module loosely covers http://developer.echonest.com/docs/v4/playlist.html
Refer to the official api documentation if you are unsure about something.
"""

import util
from proxies import PlaylistProxy
from song import Song
import catalog

class Playlist(PlaylistProxy):
    """
    A Dynamic Playlist object
    
    Attributes:
        session_id: Playlist Session ID
        song: The current song
    
    Example:
        >>> p = Playlist(type='artist-radio', artist=['ida maria', 'florence + the machine'])
        >>> p
        <Dynamic Playlist - 9c210205d4784144b4fa90770fa55d0b>
        >>> p.song
        <song - Later On>
        >>> p.get_next_song()
        <song - Overall>
        >>> 

    """
    
    def __init__(self, session_id=None, type='artist', artist_pick='song_hotttnesss-desc', variety=.5, artist_id=None, artist=None, \
                        song_id=None, description=None, max_tempo=None, min_tempo=None, max_duration=None, \
                        min_duration=None, max_loudness=None, min_loudness=None, max_danceability=None, min_danceability=None, \
                        max_energy=None, min_energy=None, artist_max_familiarity=None, artist_min_familiarity=None, \
                        artist_max_hotttnesss=None, artist_min_hotttnesss=None, song_max_hotttnesss=None, song_min_hotttnesss=None, \
                        min_longitude=None, max_longitude=None, min_latitude=None, max_latitude=None, \
                        mode=None, key=None, buckets=[], sort=None, limit=False, dmca=False, audio=False, chain_xspf=False, \
                        seed_catalog=None, steer=None, source_catalog=None, steer_description=None):
        """
        Args:

        Kwargs:
            type (str): a string representing the playlist type ('artist', 'artist-radio', ...)

            artist_pick (str): How songs should be chosen for each artist

            variety (float): A number between 0 and 1 specifying the variety of the playlist

            artist_id (str): the artist_id

            artist (str): the name of an artist

            song_id (str): the song_id

            description (str): A string describing the artist and song

            results (int): An integer number of results to return

            max_tempo (float): The max tempo of song results

            min_tempo (float): The min tempo of song results

            max_duration (float): The max duration of song results

            min_duration (float): The min duration of song results

            max_loudness (float): The max loudness of song results

            min_loudness (float): The min loudness of song results

            artist_max_familiarity (float): A float specifying the max familiarity of artists to search for

            artist_min_familiarity (float): A float specifying the min familiarity of artists to search for

            artist_max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for

            artist_min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for

            song_max_hotttnesss (float): A float specifying the max hotttnesss of songs to search for

            song_min_hotttnesss (float): A float specifying the max hotttnesss of songs to search for

            max_energy (float): The max energy of song results

            min_energy (float): The min energy of song results

            max_dancibility (float): The max dancibility of song results

            min_dancibility (float): The min dancibility of song results

            mode (int): 0 or 1 (minor or major)

            key (int): 0-11 (c, c-sharp, d, e-flat, e, f, f-sharp, g, a-flat, a, b-flat, b)

            max_latitude (float): A float specifying the max latitude of artists to search for

            min_latitude (float): A float specifying the min latitude of artists to search for

            max_longitude (float): A float specifying the max longitude of artists to search for

            min_longitude (float): A float specifying the min longitude of artists to search for                        

            sort (str): A string indicating an attribute and order for sorting the results

            buckets (list): A list of strings specifying which buckets to retrieve

            limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets

            seed_catalog (str or Catalog): A Catalog object or catalog id to use as a seed
            
            source_catalog (str or Catalog): A Catalog object or catalog id
            
            steer (str): A steering value to determine the target song attributes
            
            steer_description (str): A steering value to determine the target song description term attributes
            
        
        Returns:
            A dynamic playlist object
        
            
        """
        kwargs = {}
        if type:
            kwargs['type'] = type
        if artist_pick:
            kwargs['artist_pick'] = artist_pick
        if variety is not None:
            kwargs['variety'] = variety
        if artist:
            kwargs['artist'] = artist
        if artist_id:
            kwargs['artist_id'] = artist_id
        if song_id:
            kwargs['song_id'] = song_id
        if description:
            kwargs['description'] = description
        if max_tempo is not None:
            kwargs['max_tempo'] = max_tempo
        if min_tempo is not None:
            kwargs['min_tempo'] = min_tempo
        if max_duration is not None:
            kwargs['max_duration'] = max_duration
        if min_duration is not None:
            kwargs['min_duration'] = min_duration
        if max_loudness is not None:
            kwargs['max_loudness'] = max_loudness
        if min_loudness is not None:
            kwargs['min_loudness'] = min_loudness
        if max_danceability is not None:
            kwargs['max_danceability'] = max_danceability
        if min_danceability is not None:
            kwargs['min_danceability'] = min_danceability
        if max_energy is not None:
            kwargs['max_energy'] = max_energy
        if min_energy is not None:
            kwargs['min_energy'] = min_energy
        if artist_max_familiarity is not None:
            kwargs['artist_max_familiarity'] = artist_max_familiarity
        if artist_min_familiarity is not None:
            kwargs['artist_min_familiarity'] = artist_min_familiarity
        if artist_max_hotttnesss is not None:
            kwargs['artist_max_hotttnesss'] = artist_max_hotttnesss
        if artist_min_hotttnesss is not None:
            kwargs['artist_min_hotttnesss'] = artist_min_hotttnesss
        if song_max_hotttnesss is not None:
            kwargs['song_max_hotttnesss'] = song_max_hotttnesss
        if song_min_hotttnesss is not None:
            kwargs['song_min_hotttnesss'] = song_min_hotttnesss
        if mode is not None:
            kwargs['mode'] = mode
        if key is not None:
            kwargs['key'] = key
        if max_latitude is not None:
            kwargs['max_latitude'] = max_latitude
        if min_latitude is not None:
            kwargs['min_latitude'] = min_latitude
        if max_longitude is not None:
            kwargs['max_longitude'] = max_longitude
        if min_longitude is not None:
            kwargs['min_longitude'] = min_longitude
        if sort:
            kwargs['sort'] = sort
        if buckets:
            kwargs['bucket'] = buckets
        if limit:
            kwargs['limit'] = 'true'
        if dmca:
            kwargs['dmca'] = 'true'
        if chain_xspf:
            kwargs['chain_xspf'] = 'true'
        if audio:
            kwargs['audio'] = 'true'
        if steer:
            kwargs['steer'] = steer
        if steer_description:
            kwargs['steer_description'] = steer_description
        if seed_catalog:
            if isinstance(seed_catalog, catalog.Catalog):
                kwargs['seed_catalog'] = seed_catalog.id
            else:
                kwargs['seed_catalog'] = seed_catalog
        if source_catalog:
            if isinstance(source_catalog, catalog.Catalog):
                kwargs['source_catalog'] = source_catalog.id
            else:
                kwargs['source_catalog'] = source_catalog
                        
        super(Playlist, self).__init__(session_id, **kwargs)
    
    def __repr__(self):
        return "<Dynamic Playlist - %s>" % self.session_id.encode('utf-8')
    
    # def __str__(self):
    #     return self.name.encode('utf-8')
    
    def get_next_song(self, **kwargs):
        """Get the next song in the playlist
        
        Args:
        
        Kwargs:
        
        Returns:
            A song object
        
        Example:
        
        >>> p = playlist.Playlist(type='artist-radio', artist=['ida maria', 'florence + the machine'])
        >>> p.get_next_song()
        <song - She Said>
        >>> 


        """
        response = self.get_attribute('dynamic', session_id=self.session_id, **kwargs)
        self.cache['songs'] = response['songs']
        # we need this to fix up all the dict keys to be strings, not unicode objects
        fix = lambda x : dict((str(k), v) for (k,v) in x.iteritems())
        if len(self.cache['songs']):
            return Song(**fix(self.cache['songs'][0]))
        else:
            return None
    
    def get_current_song(self):
        """Get the current song in the playlist
        
        Args:
        
        Kwargs:
        
        Returns:
            A song object
        
        Example:
        
        >>> p = playlist.Playlist(type='artist-radio', artist=['ida maria', 'florence + the machine'])
        >>> p.song
        <song - Later On>
        >>> p.get_current_song()
        <song - Later On>
        >>> 

        """
        # we need this to fix up all the dict keys to be strings, not unicode objects
        if not 'songs' in self.cache:
            self.get_next_song()
        if len(self.cache['songs']):
            return Song(**util.fix(self.cache['songs'][0]))
        else:
            return None

    song = property(get_current_song)
    
    def session_info(self):
        """Get information about the playlist
        
        Args:
        
        Kwargs:
        
        Returns:
            A dict with diagnostic information about the currently running playlist
        
        Example:
        
        >>> p = playlist.Playlist(type='artist-radio', artist=['ida maria', 'florence + the machine'])
        >>> p.info
        
        {
            u 'terms': [{
                u 'frequency': 1.0,
                u 'name': u 'rock'
            },
            {
                u 'frequency': 0.99646542152360207,
                u 'name': u 'pop'
            },
            {
                u 'frequency': 0.90801905502131963,
                u 'name': u 'indie'
            },
            {
                u 'frequency': 0.90586455490260576,
                u 'name': u 'indie rock'
            },
            {
                u 'frequency': 0.8968907243373172,
                u 'name': u 'alternative'
            },
            [...]
            {
                u 'frequency': 0.052197425644931635,
                u 'name': u 'easy listening'
            }],
            u 'description': [],
            u 'seed_songs': [],
            u 'banned_artists': [],
            u 'rules': [{
                u 'rule': u "Don't put two copies of the same song in a playlist."
            },
            {
                u 'rule': u 'Give preference to artists that are not already in the playlist'
            }],
            u 'session_id': u '9c1893e6ace04c8f9ce745f38b35ff95',
            u 'seeds': [u 'ARI4XHX1187B9A1216', u 'ARNCHOP121318C56B8'],
            u 'skipped_songs': [],
            u 'banned_songs': [],
            u 'playlist_type': u 'artist-radio',
            u 'seed_catalogs': [],
            u 'rated_songs': [],
            u 'history': [{
                u 'artist_id': u 'ARN6QMG1187FB56C8D',
                u 'artist_name': u 'Laura Marling',
                u 'id': u 'SOMSHNP12AB018513F',
                u 'served_time': 1291412277.204201,
                u 'title': u 'Hope In The Air'
            }]
        }
        
        >>> p.session_info()
        (same result as above)
        >>> 

        """
        return self.get_attribute("session_info", session_id=self.session_id)
    
    info = property(session_info)


def static(type='artist', artist_pick='song_hotttnesss-desc', variety=.5, artist_id=None, artist=None, \
                    song_id=None, description=None, results=15, max_tempo=None, min_tempo=None, max_duration=None, \
                    min_duration=None, max_loudness=None, min_loudness=None, max_danceability=None, min_danceability=None, \
                    max_energy=None, min_energy=None, artist_max_familiarity=None, artist_min_familiarity=None, \
                    artist_max_hotttnesss=None, artist_min_hotttnesss=None, song_max_hotttnesss=None, song_min_hotttnesss=None, \
                    min_longitude=None, max_longitude=None, min_latitude=None, max_latitude=None, \
                    mode=None, key=None, buckets=[], sort=None, limit=False, seed_catalog=None, source_catalog=None):
    """Get a static playlist
    
    Args:
    
    Kwargs:
        type (str): a string representing the playlist type ('artist', 'artist-radio', ...)
        
        artist_pick (str): How songs should be chosen for each artist
        
        variety (float): A number between 0 and 1 specifying the variety of the playlist
        
        artist_id (str): the artist_id
        
        artist (str): the name of an artist
        
        song_id (str): the song_id
    
        description (str): A string describing the artist and song
    
        results (int): An integer number of results to return
    
        max_tempo (float): The max tempo of song results
    
        min_tempo (float): The min tempo of song results
    
        max_duration (float): The max duration of song results
    
        min_duration (float): The min duration of song results
    
        max_loudness (float): The max loudness of song results
    
        min_loudness (float): The min loudness of song results
    
        artist_max_familiarity (float): A float specifying the max familiarity of artists to search for
    
        artist_min_familiarity (float): A float specifying the min familiarity of artists to search for
    
        artist_max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
    
        artist_min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for
    
        song_max_hotttnesss (float): A float specifying the max hotttnesss of songs to search for
    
        song_min_hotttnesss (float): A float specifying the max hotttnesss of songs to search for
    
        max_energy (float): The max energy of song results
    
        min_energy (float): The min energy of song results
    
        max_dancibility (float): The max dancibility of song results
    
        min_dancibility (float): The min dancibility of song results
    
        mode (int): 0 or 1 (minor or major)
    
        key (int): 0-11 (c, c-sharp, d, e-flat, e, f, f-sharp, g, a-flat, a, b-flat, b)
    
        max_latitude (float): A float specifying the max latitude of artists to search for
    
        min_latitude (float): A float specifying the min latitude of artists to search for
    
        max_longitude (float): A float specifying the max longitude of artists to search for
    
        min_longitude (float): A float specifying the min longitude of artists to search for                        
    
        sort (str): A string indicating an attribute and order for sorting the results
    
        buckets (list): A list of strings specifying which buckets to retrieve
    
        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets
        
        seed_catalog (str or Catalog): An Artist Catalog object or Artist Catalog id to use as a seed
        
        source_catalog (str or Catalog): A Catalog object or catalog id
    
    Returns:
        A list of Song objects
    
    Example:
    
    >>> p = playlist.static(type='artist-radio', artist=['ida maria', 'florence + the machine'])
    >>> p
    [<song - Pickpocket>,
     <song - Self-Taught Learner>,
     <song - Maps>,
     <song - Window Blues>,
     <song - That's Not My Name>,
     <song - My Lover Will Go>,
     <song - Home Sweet Home>,
     <song - Stella & God>,
     <song - Don't You Want To Share The Guilt?>,
     <song - Forget About It>,
     <song - Dull Life>,
     <song - This Trumpet In My Head>,
     <song - Keep Your Head>,
     <song - One More Time>,
     <song - Knights in Mountain Fox Jackets>]
    >>> 

    """
    kwargs = {}
    if type:
        kwargs['type'] = type
    if artist_pick:
        kwargs['artist_pick'] = artist_pick
    if variety is not None:
        kwargs['variety'] = variety
    if artist:
        kwargs['artist'] = artist
    if artist_id:
        kwargs['artist_id'] = artist_id
    if song_id:
        kwargs['song_id'] = song_id
    if description:
        kwargs['description'] = description
    if results is not None:
        kwargs['results'] = results
    if max_tempo is not None:
        kwargs['max_tempo'] = max_tempo
    if min_tempo is not None:
        kwargs['min_tempo'] = min_tempo
    if max_duration is not None:
        kwargs['max_duration'] = max_duration
    if min_duration is not None:
        kwargs['min_duration'] = min_duration
    if max_loudness is not None:
        kwargs['max_loudness'] = max_loudness
    if min_loudness is not None:
        kwargs['min_loudness'] = min_loudness
    if max_danceability is not None:
        kwargs['max_danceability'] = max_danceability
    if min_danceability is not None:
        kwargs['min_danceability'] = min_danceability
    if max_energy is not None:
        kwargs['max_energy'] = max_energy
    if min_energy is not None:
        kwargs['min_energy'] = min_energy
    if artist_max_familiarity is not None:
        kwargs['artist_max_familiarity'] = artist_max_familiarity
    if artist_min_familiarity is not None:
        kwargs['artist_min_familiarity'] = artist_min_familiarity
    if artist_max_hotttnesss is not None:
        kwargs['artist_max_hotttnesss'] = artist_max_hotttnesss
    if artist_min_hotttnesss is not None:
        kwargs['artist_min_hotttnesss'] = artist_min_hotttnesss
    if song_max_hotttnesss is not None:
        kwargs['song_max_hotttnesss'] = song_max_hotttnesss
    if song_min_hotttnesss is not None:
        kwargs['song_min_hotttnesss'] = song_min_hotttnesss
    if mode is not None:
        kwargs['mode'] = mode
    if key is not None:
        kwargs['key'] = key
    if max_latitude is not None:
        kwargs['max_latitude'] = max_latitude
    if min_latitude is not None:
        kwargs['min_latitude'] = min_latitude
    if max_longitude is not None:
        kwargs['max_longitude'] = max_longitude
    if min_longitude is not None:
        kwargs['min_longitude'] = min_longitude
    if sort:
        kwargs['sort'] = sort
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'
    if seed_catalog:
        if isinstance(seed_catalog, catalog.Catalog):
            kwargs['seed_catalog'] = seed_catalog.id
        else:
            kwargs['seed_catalog'] = seed_catalog
    if source_catalog:
        if isinstance(source_catalog, catalog.Catalog):
            kwargs['source_catalog'] = source_catalog.id
        else:
            kwargs['source_catalog'] = source_catalog
            
    result = util.callm("%s/%s" % ('playlist', 'static'), kwargs)
    return [Song(**util.fix(s_dict)) for s_dict in result['response']['songs']]

########NEW FILE########
__FILENAME__ = proxies
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.
"""
import util

class ResultList(list):
    def __init__(self, li, start=0, total=0):
        self.extend(li)
        self.start = start
        if total == 0:
            total = len(li)
        self.total = total

class GenericProxy(object):
    def __init__(self):
        self.cache = {}
    
    def get_attribute(self, method_name, **kwargs):
        result = util.callm("%s/%s" % (self._object_type, method_name), kwargs)
        return result['response']
    
    def post_attribute(self, method_name, **kwargs):
        if 'data' in kwargs:
            data = kwargs.pop('data')
        else:
            data = {}
        result = util.callm("%s/%s" % (self._object_type, method_name), kwargs, POST=True, data=data)
        return result['response']
    

class ArtistProxy(GenericProxy):
    def __init__(self, identifier, buckets = None, **kwargs):
        super(ArtistProxy, self).__init__()
        buckets = buckets or []
        self.id = identifier
        self._object_type = 'artist'
        kwargs = dict((str(k), v) for (k,v) in kwargs.iteritems())
        # the following are integral to all artist objects... the rest is up to you!
        core_attrs = ['name']
        
        for ca in core_attrs:
            if not ca in kwargs:
                profile = self.get_attribute('profile', **{'bucket':buckets})
                kwargs.update(profile.get('artist'))
        
        #if not all(ca in kwargs for ca in core_attrs):
        #    profile = self.get_attribute('profile', **{'bucket':buckets})
        #    kwargs.update(profile.get('artist'))
        
        [self.__dict__.update({ca:kwargs.pop(ca)}) for ca in core_attrs+['id'] if ca in kwargs]        
        self.cache.update(kwargs)
    
    def get_attribute(self, *args, **kwargs):
        if util.short_regex.match(self.id) or util.long_regex.match(self.id) or util.foreign_regex.match(self.id):
            kwargs['id'] = self.id
        else:
            kwargs['name'] = self.id
        return super(ArtistProxy, self).get_attribute(*args, **kwargs)
    

class CatalogProxy(GenericProxy):
    def __init__(self, identifier, type, buckets = None, **kwargs):
        super(CatalogProxy, self).__init__()
        buckets = buckets or []
        self.id = identifier
        self._object_type = 'catalog'
        kwargs = dict((str(k), v) for (k,v) in kwargs.iteritems())
        # the following are integral to all catalog objects... the rest is up to you!
        core_attrs = ['name']
        if not all(ca in kwargs for ca in core_attrs):
            if util.short_regex.match(self.id) or util.long_regex.match(self.id) or util.foreign_regex.match(self.id):
                try:
                    profile = self.get_attribute('profile')
                    kwargs.update(profile['catalog'])
                except util.EchoNestAPIError:
                    raise Exception('Catalog %s does not exist' % (identifier))
            else:
                if not type:
                    raise Exception('You must specify a "type"!')
                try:
                    profile = self.get_attribute('profile')
                    existing_type = profile['catalog'].get('type', 'Unknown')
                    if type != existing_type:
                        raise Exception("Catalog type requested (%s) does not match existing catalog type (%s)" % (type, existing_type))
                    
                    kwargs.update(profile['catalog'])
                except util.EchoNestAPIError:
                    profile = self.post_attribute('create', type=type, **kwargs)
                    kwargs.update(profile)
        [self.__dict__.update({ca:kwargs.pop(ca)}) for ca in core_attrs+['id'] if ca in kwargs]
        self.cache.update(kwargs)
    
    def get_attribute_simple(self, *args, **kwargs):
        # omit name/id kwargs for this call
        return super(CatalogProxy, self).get_attribute(*args, **kwargs)
    
    def get_attribute(self, *args, **kwargs):
        if util.short_regex.match(self.id) or util.long_regex.match(self.id) or util.foreign_regex.match(self.id):
            kwargs['id'] = self.id
        else:
            kwargs['name'] = self.id
        return super(CatalogProxy, self).get_attribute(*args, **kwargs)
    
    def post_attribute(self, *args, **kwargs):
        if util.short_regex.match(self.id) or util.long_regex.match(self.id) or util.foreign_regex.match(self.id):
            kwargs['id'] = self.id
        else:
            kwargs['name'] = self.id
        return super(CatalogProxy, self).post_attribute(*args, **kwargs)
    

class PlaylistProxy(GenericProxy):
    def __init__(self, session_id, buckets = None, **kwargs):
        super(PlaylistProxy, self).__init__()
        buckets = buckets or []
        self._object_type = 'playlist'
        kwargs = dict((str(k), v) for (k,v) in kwargs.iteritems())
        if session_id:
            kwargs['session_id'] = session_id
        # the following are integral to all playlist objects... the rest is up to you!
        core_attrs = ['session_id']
        if not all(ca in kwargs for ca in core_attrs):
            profile = self.get_attribute('dynamic', **kwargs)
            kwargs.update(profile)
        [self.__dict__.update({ca:kwargs.pop(ca)}) for ca in core_attrs if ca in kwargs]        
        self.cache.update(kwargs)
    
    def get_attribute(self, *args, **kwargs):
        return super(PlaylistProxy, self).get_attribute(*args, **kwargs)
    

class SongProxy(GenericProxy):
    def __init__(self, identifier, buckets = None, **kwargs):
        super(SongProxy, self).__init__()
        buckets = buckets or []
        self.id = identifier
        self._object_type = 'song'
        kwargs = dict((str(k), v) for (k,v) in kwargs.iteritems())
        
        # BAW -- this is debug output from identify that returns a track_id. i am not sure where else to access this..
        if kwargs.has_key("track_id"):
            self.track_id = kwargs["track_id"]
        if kwargs.has_key("tag"):
            self.tag = kwargs["tag"]
        if kwargs.has_key("score"):
            self.score = kwargs["score"]
        if kwargs.has_key('audio'):
            self.audio = kwargs['audio']
        if kwargs.has_key('release_image'):
            self.release_image = kwargs['release_image']
        
        # the following are integral to all song objects... the rest is up to you!
        core_attrs = ['title', 'artist_name', 'artist_id']
        
        for ca in core_attrs:
            if not ca in kwargs:
                profile = self.get_attribute('profile', **{'id':self.id, 'bucket':buckets})
                kwargs.update(profile.get('songs')[0])
        
        #if not all(ca in kwargs for ca in core_attrs):
        #    profile = self.get_attribute('profile', **{'id':self.id, 'bucket':buckets})
        #    kwargs.update(profile.get('songs')[0])
        
        [self.__dict__.update({ca:kwargs.pop(ca)}) for ca in core_attrs]
        self.cache.update(kwargs)
    
    def get_attribute(self, *args, **kwargs):
        kwargs['id'] = self.id
        return super(SongProxy, self).get_attribute(*args, **kwargs)
    

class TrackProxy(GenericProxy):
    def __init__(self, identifier, md5, properties):
        """
        You should not call this constructor directly, rather use the convenience functions
        that are in track.py. For example, call track.track_from_filename
        Let's always get the bucket `audio_summary`
        """
        super(TrackProxy, self).__init__()
        self.id = identifier
        self.md5 = md5
        self._object_type = 'track'
        self.__dict__.update(properties)
    

########NEW FILE########
__FILENAME__ = results
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.
"""

import logging
from util import attrdict

# I want a:
#   generic object that takes a dict and turns it into an object
#   should take on the name of a key in the dict
#   should handle lists
class Result(attrdict):
    def __init__(self, result_type, result_dict):
        self._object_type = result_type
        assert(isinstance(result_dict,dict))
        self.__dict__.update(result_dict)
    
    def __repr__(self):
        return "<Result - %s>" % (self._object_type)
    
    def __str__(self):
        return "<Result - %s>" % (self._object_type)

def make_results(result_type, response, accessor_function):
    try:
        data = accessor_function(response)
        if isinstance(data, list):
            return [Result(result_type, item) for item in data]
        elif isinstance(data, dict):
            return Result(result_type, data)
        else:
             return data
    except IndexError:
        logging.info("No songs found")


########NEW FILE########
__FILENAME__ = song
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.

The Song module loosely covers http://developer.echonest.com/docs/v4/song.html
Refer to the official api documentation if you are unsure about something.
"""
import os
import util
from proxies import SongProxy

try:
    import json
except ImportError:
    import simplejson as json
    
class Song(SongProxy):
    """
    A Song object
    
    Attributes: 
        id (str): Echo Nest Song ID
        
        title (str): Song Title
        
        artist_name (str): Artist Name
        
        artist_id (str): Artist ID
        
        audio_summary (dict): An Audio Summary dict
        
        song_hotttnesss (float): A float representing a song's hotttnesss
        
        artist_hotttnesss (float): A float representing a song's parent artist's hotttnesss
        
        artist_familiarity (float): A float representing a song's parent artist's familiarity
        
        artist_location (str): A string specifying a song's parent artist's location
        
        tracks (list): A list of track objects
        
    Create a song object like so:

    >>> s = song.Song('SOPEXHZ12873FD2AC7')
    
    """
    def __init__(self, id, buckets=None, **kwargs):
        """
        Song class
        
        Args:
            id (str): a song ID 

        Kwargs:
            buckets (list): A list of strings specifying which buckets to retrieve

        Returns:
            A Song object

        Example:

        >>> s = song.Song('SOPEXHZ12873FD2AC7', buckets=['song_hotttnesss', 'artist_hotttnesss'])
        >>> s.song_hotttnesss
        0.58602500000000002
        >>> s.artist_hotttnesss
        0.80329715999999995
        >>> 

        """
        buckets = buckets or []
        super(Song, self).__init__(id, buckets, **kwargs)
    
    def __repr__(self):
        return "<%s - %s>" % (self._object_type.encode('utf-8'), self.title.encode('utf-8'))
    
    def __str__(self):
        return self.title.encode('utf-8')
    
        
    def get_audio_summary(self, cache=True):
        """Get an audio summary of a song containing mode, tempo, key, duration, time signature, loudness, danceability, energy, and analysis_url.
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            A dictionary containing mode, tempo, key, duration, time signature, loudness, danceability, energy and analysis_url keys.
            
        Example:
            >>> s = song.Song('SOGNMKX12B0B806320')
            >>> s.audio_summary
            {u'analysis_url': u'https://echonest-analysis.s3.amazonaws.com:443/TR/TRCPUOG123E85891F2/3/full.json?Signature=wcML1ZKsl%2F2FU4k68euHJcF7Jbc%3D&Expires=1287518562&AWSAccessKeyId=AKIAIAFEHLM3KJ2XMHRA',
             u'danceability': 0.20964757782725996,
             u'duration': 472.63301999999999,
             u'energy': 0.64265230549809549,
             u'key': 0,
             u'loudness': -9.6820000000000004,
             u'mode': 1,
             u'tempo': 126.99299999999999,
             u'time_signature': 4}
            >>> 
            
        """
        if not (cache and ('audio_summary' in self.cache)):
            response = self.get_attribute('profile', bucket='audio_summary')
            self.cache['audio_summary'] = response['songs'][0]['audio_summary']
        return self.cache['audio_summary']
    
    audio_summary = property(get_audio_summary)
    
    def get_song_hotttnesss(self, cache=True):
        """Get our numerical description of how hottt a song currently is
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            A float representing hotttnesss.
        
        Example:
            >>> s = song.Song('SOLUHKP129F0698D49')
            >>> s.get_song_hotttnesss()
            0.57344379999999995
            >>> s.song_hotttnesss
            0.57344379999999995
            >>> 

        """
        if not (cache and ('song_hotttnesss' in self.cache)):
            response = self.get_attribute('profile', bucket='song_hotttnesss')
            self.cache['song_hotttnesss'] = response['songs'][0]['song_hotttnesss']
        return self.cache['song_hotttnesss']
    
    song_hotttnesss = property(get_song_hotttnesss)
    
    def get_artist_hotttnesss(self, cache=True):
        """Get our numerical description of how hottt a song's artist currently is
        
        Args:
        
        Kwargs:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            A float representing hotttnesss.
        
        Example:
            >>> s = song.Song('SOOLGAZ127F3E1B87C')
            >>> s.artist_hotttnesss
            0.45645633000000002
            >>> s.get_artist_hotttnesss()
            0.45645633000000002
            >>> 
        
        """
        if not (cache and ('artist_hotttnesss' in self.cache)):
            response = self.get_attribute('profile', bucket='artist_hotttnesss')
            self.cache['artist_hotttnesss'] = response['songs'][0]['artist_hotttnesss']
        return self.cache['artist_hotttnesss']
    
    artist_hotttnesss = property(get_artist_hotttnesss)
    
    def get_artist_familiarity(self, cache=True):
        """Get our numerical estimation of how familiar a song's artist currently is to the world
        
        Args:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            A float representing familiarity.
        
        Example:
            >>> s = song.Song('SOQKVPH12A58A7AF4D')
            >>> s.get_artist_familiarity()
            0.639626025843539
            >>> s.artist_familiarity
            0.639626025843539
            >>> 
        """
        if not (cache and ('artist_familiarity' in self.cache)):
            response = self.get_attribute('profile', bucket='artist_familiarity')
            self.cache['artist_familiarity'] = response['songs'][0]['artist_familiarity']
        return self.cache['artist_familiarity']
    
    artist_familiarity = property(get_artist_familiarity)
    
    def get_artist_location(self, cache=True):
        """Get the location of a song's artist.
        
        Args:
            cache (bool): A boolean indicating whether or not the cached value should be used (if available). Defaults to True.
        
        Returns:
            An artist location object.
        
        Example:
            >>> s = song.Song('SOQKVPH12A58A7AF4D')
            >>> s.artist_location
            {u'latitude': 34.053489999999996, u'location': u'Los Angeles, CA', u'longitude': -118.24532000000001}
            >>> 

        """
        if not (cache and ('artist_location' in self.cache)):
            response = self.get_attribute('profile', bucket='artist_location')
            self.cache['artist_location'] = response['songs'][0]['artist_location']
        return self.cache['artist_location']
    
    artist_location = property(get_artist_location)
    
    def get_tracks(self, catalog, cache=True):
        """Get the tracks for a song given a catalog.
        
        Args:
            catalog (str): a string representing the catalog whose track you want to retrieve.
        
        Returns:
            A list of Track dicts.
        
        Example:
            >>> s = song.Song('SOWDASQ12A6310F24F')
            >>> s.get_tracks('7digital')[0]
            {u'catalog': u'7digital',
             u'foreign_id': u'7digital:track:8445818',
             u'id': u'TRJGNNY12903CC625C',
             u'preview_url': u'http://previews.7digital.com/clips/34/8445818.clip.mp3',
             u'release_image': u'http://cdn.7static.com/static/img/sleeveart/00/007/628/0000762838_200.jpg'}
            >>> 

        """
        if not (cache and ('tracks' in self.cache) and (catalog in [td['catalog'] for td in self.cache['tracks']])):
            kwargs = {
                'bucket':['tracks', 'id:%s' % catalog],
            }
                        
            response = self.get_attribute('profile', **kwargs)
            if not 'tracks' in self.cache:
                self.cache['tracks'] = []
            # don't blow away the cache for other catalogs
            potential_tracks = response['songs'][0].get('tracks', [])
            existing_track_ids = [tr['foreign_id'] for tr in self.cache['tracks']]
            new_tds = filter(lambda tr: tr['foreign_id'] not in existing_track_ids, potential_tracks)
            self.cache['tracks'].extend(new_tds)
        return filter(lambda tr: tr['catalog']==catalog, self.cache['tracks'])

def identify(filename=None, query_obj=None, code=None, artist=None, title=None, release=None, duration=None, genre=None, buckets=None, codegen_start=0, codegen_duration=30):
    """Identify a song.
    
    Args:
        
    Kwargs:
        filename (str): The path of the file you want to analyze (requires codegen binary!)
        
        query_obj (dict or list): A dict or list of dicts containing a 'code' element with an fp code
        
        code (str): A fingerprinter code
        
        artist (str): An artist name
        
        title (str): A song title
        
        release (str): A release name
        
        duration (int): A song duration
        
        genre (str): A string representing the genre
        
        buckets (list): A list of strings specifying which buckets to retrieve
        
        codegen_start (int): The point (in seconds) where the codegen should start
        
        codegen_duration (int): The duration (in seconds) the codegen should analyze
        
    Example:
        >>> qo
        {'code': 'eJxlldehHSEMRFsChAjlAIL-S_CZvfaXXxAglEaBTen300Qu__lAyoJYhVQdXTvXrmvXdTsKZOqoU1q63QNydBGfOd1cGX3scpb1jEiWRLaPcJureC6RVkXE69jL8pGHjpP48pLI1m7r9oiEyBXvoVv45Q-5IhylYLkIRxGO4rp18ZpEOmpFPopwfJjL0u3WceO3HB1DIvJRnkQeO1PCLIsIjBWEzYaShq4pV9Z0KzDiQ8SbSNuSyBZPOOxIJKR7dauEmXwotxDCqllEAVZlrX6F8Y-IJ0e169i_HQaqslaVtTq1W-1vKeupImzrxWWVI5cPlw-XDxckN-3kyeXDm3jKmqv6PtB1gfH1Eey5qu8qvAuMC4zLfPv1l3aqviylJhytFhF0mzqs6aYpYU04mlqgKWtNjppwNKWubR2FowlHUws0gWmPi668dSHq6rOuPuhqgRcVKKM8s-fZS937nBe23iz3Uctx9607z-kLph1i8YZ8f_TfzLXseBh7nXy9nn1YBAg4Nwjp4AzTL23M_U3Rh0-sdDFtyspNOb1bYeZZqz2Y6TaHmXeuNmfFdTueLuvdsbOU9luvtIkl4vI5F_92PVprM1-sdJ_o9_Guc0b_WimpD_Rt1DFg0sY3wyw08e6jlqhjH3o76naYvzWqhX9rOv15Y7Ww_MIF8dXzw30s_uHO5PPDfUonnzq_NJ8J93mngAkIz5jA29SqxGwwvxQsih-sozX0zVk__RFaf_qyG9hb8dktZZXd4a8-1ljB-c5bllXOe1HqHplzeiN4E7q9ZRdmJuI73gBEJ_HcAxUm74PAVDNL47D6OAfzTHI0mHpXAmY60QNmlqjDfIPzwUDYhVnoXqtvZGrBdMi3ClQUQ8D8rX_1JE_In94CBXER4lrrw0H867ei8x-OVz8c-Osh5plzTOySpKIROmFkbn5xVuK784vTyPpS3OlcSjHpL16saZnm4Bk66hte9sd80Dcj02f7xDVrExjk32cssKXjmflU_SxXmn4Y9Ttued10YM552h5Wtt_WeVR4U6LPWfbIdW31J4JOXnpn4qhH7yE_pdBH9E_sMwbNFr0z0IW5NA8aOZhLmOh3zSVNRZwxiZc5pb8fikGzIf-ampJnCSb3r-ZPfjPuvLm7CY_Vfa_k7SCzdwHNg5mICTSHDxyBWmaOSyLQpPmCSXyF-eL7MHo7zNd668JMb_N-AJJRuMwrX0jNx7a8-Rj5oN6nyWoL-jRv4pu7Ue821TzU3MhvpD9Fo-XI',
         'code_count': 151,
         'low_rank': 0,
         'metadata': {'artist': 'Harmonic 313',
                      'bitrate': 198,
                      'codegen_time': 0.57198400000000005,
                      'decode_time': 0.37954599999999999,
                      'duration': 226,
                      'filename': 'koln.mp3',
                      'genre': 'Electronic',
                      'given_duration': 30,
                      'release': 'When Machines Exceed Human Intelligence',
                      'sample_rate': 44100,
                      'samples_decoded': 661816,
                      'start_offset': 0,
                      'title': 'kln',
                      'version': 3.1499999999999999},
         'tag': 0}
        >>> song.identify(query_obj=qo)
        [<song - Köln>]
        >>> 


    """
    post, has_data, data = False, False, False
    
    if filename:
        if os.path.exists(filename):
            query_obj = util.codegen(filename, start=codegen_start, duration=codegen_duration)
            if query_obj is None:
                raise Exception("The filename specified: %s could not be decoded." % filename)
        else:
            raise Exception("The filename specified: %s does not exist." % filename)
    if query_obj and not isinstance(query_obj, list):
        query_obj = [query_obj]
        
    if filename:
        # check codegen results from file in case we had a bad result
        for q in query_obj:
            if 'error' in q:
                raise Exception(q['error'] + ": " + q.get('metadata', {}).get('filename', ''))
    
    if not (filename or query_obj or code):
        raise Exception("Not enough information to identify song.")
    
    kwargs = {}
    if code:
        has_data = True
        kwargs['code'] = code
    if title:
        kwargs['title'] = title
    if release:
        kwargs['release'] = release
    if duration:
        kwargs['duration'] = duration
    if genre:
        kwargs['genre'] = genre
    if buckets:
        kwargs['bucket'] = buckets
    
    if query_obj and any(query_obj):
        has_data = True
        data = {'query':json.dumps(query_obj)}
        post = True
    
    if has_data:
        result = util.callm("%s/%s" % ('song', 'identify'), kwargs, POST=post, data=data)
        return [Song(**util.fix(s_dict)) for s_dict in result['response'].get('songs',[])]


def search(title=None, artist=None, artist_id=None, combined=None, description=None, results=None, start=None, max_tempo=None, \
                min_tempo=None, max_duration=None, min_duration=None, max_loudness=None, min_loudness=None, \
                artist_max_familiarity=None, artist_min_familiarity=None, artist_max_hotttnesss=None, \
                artist_min_hotttnesss=None, song_max_hotttnesss=None, song_min_hotttnesss=None, mode=None, \
                min_energy=None, max_energy=None, min_danceability=None, max_danceability=None, \
                key=None, max_latitude=None, min_latitude=None, max_longitude=None, min_longitude=None, \
                sort=None, buckets = None, limit=False):
    """Search for songs by name, description, or constraint.

    Args:

    Kwargs:
        title (str): the name of a song
        
        artist (str): the name of an artist

        artist_id (str): the artist_id
        
        combined (str): the artist name and song title
        
        description (str): A string describing the artist and song

        results (int): An integer number of results to return
        
        max_tempo (float): The max tempo of song results
        
        min_tempo (float): The min tempo of song results
        
        max_duration (float): The max duration of song results
        
        min_duration (float): The min duration of song results

        max_loudness (float): The max loudness of song results
        
        min_loudness (float): The min loudness of song results
        
        artist_max_familiarity (float): A float specifying the max familiarity of artists to search for

        artist_min_familiarity (float): A float specifying the min familiarity of artists to search for

        artist_max_hotttnesss (float): A float specifying the max hotttnesss of artists to search for

        artist_min_hotttnesss (float): A float specifying the max hotttnesss of artists to search for

        song_max_hotttnesss (float): A float specifying the max hotttnesss of songs to search for

        song_min_hotttnesss (float): A float specifying the max hotttnesss of songs to search for
        
        max_energy (float): The max energy of song results

        min_energy (float): The min energy of song results

        max_dancibility (float): The max dancibility of song results

        min_dancibility (float): The min dancibility of song results
        
        mode (int): 0 or 1 (minor or major)
        
        key (int): 0-11 (c, c-sharp, d, e-flat, e, f, f-sharp, g, a-flat, a, b-flat, b)
        
        max_latitude (float): A float specifying the max latitude of artists to search for
        
        min_latitude (float): A float specifying the min latitude of artists to search for
        
        max_longitude (float): A float specifying the max longitude of artists to search for

        min_longitude (float): A float specifying the min longitude of artists to search for                        

        sort (str): A string indicating an attribute and order for sorting the results
        
        buckets (list): A list of strings specifying which buckets to retrieve

        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets

    Returns:
        A list of Song objects

    Example:

    >>> results = song.search(artist='shakira', title='she wolf', buckets=['id:7digital', 'tracks'], limit=True, results=1)
    >>> results
    [<song - She Wolf>]
    >>> results[0].get_tracks('7digital')[0]
    {u'catalog': u'7digital',
     u'foreign_id': u'7digital:track:7854109',
     u'id': u'TRTOBSE12903CACEC4',
     u'preview_url': u'http://previews.7digital.com/clips/34/7854109.clip.mp3',
     u'release_image': u'http://cdn.7static.com/static/img/sleeveart/00/007/081/0000708184_200.jpg'}
    >>> 
    """
    
    kwargs = {}
    if title:
        kwargs['title'] = title
    if artist:
        kwargs['artist'] = artist
    if artist_id:
        kwargs['artist_id'] = artist_id
    if combined:
        kwargs['combined'] = combined
    if description:
        kwargs['description'] = description
    if results is not None:
        kwargs['results'] = results
    if start is not None:
        kwargs['start'] = start
    if max_tempo is not None:
        kwargs['max_tempo'] = max_tempo
    if min_tempo is not None:
        kwargs['min_tempo'] = min_tempo
    if max_duration is not None:
        kwargs['max_duration'] = max_duration
    if min_duration is not None:
        kwargs['min_duration'] = min_duration
    if max_loudness is not None:
        kwargs['max_loudness'] = max_loudness
    if min_loudness is not None:
        kwargs['min_loudness'] = min_loudness
    if artist_max_familiarity is not None:
        kwargs['artist_max_familiarity'] = artist_max_familiarity
    if artist_min_familiarity is not None:
        kwargs['artist_min_familiarity'] = artist_min_familiarity
    if artist_max_hotttnesss is not None:
        kwargs['artist_max_hotttnesss'] = artist_max_hotttnesss
    if artist_min_hotttnesss is not None:
        kwargs['artist_min_hotttnesss'] = artist_min_hotttnesss
    if song_max_hotttnesss is not None:
        kwargs['song_max_hotttnesss'] = song_max_hotttnesss
    if song_min_hotttnesss is not None:
        kwargs['song_min_hotttnesss'] = song_min_hotttnesss
    if min_danceability is not None:
        kwargs['min_danceability'] = min_danceability
    if max_danceability is not None:
        kwargs['max_danceability'] = max_danceability
    if max_energy is not None:
        kwargs['max_energy'] = max_energy
    if max_energy is not None:
        kwargs['max_energy'] = max_energy
    if mode is not None:
        kwargs['mode'] = mode
    if key is not None:
        kwargs['key'] = key
    if max_latitude is not None:
        kwargs['max_latitude'] = max_latitude
    if min_latitude is not None:
        kwargs['min_latitude'] = min_latitude
    if max_longitude is not None:
        kwargs['max_longitude'] = max_longitude
    if min_longitude is not None:
        kwargs['min_longitude'] = min_longitude
    if sort:
        kwargs['sort'] = sort
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'
    
    result = util.callm("%s/%s" % ('song', 'search'), kwargs)
    return [Song(**util.fix(s_dict)) for s_dict in result['response']['songs']]

def profile(ids, buckets=None, limit=False):
    """get the profiles for multiple songs at once
        
    Args:
        ids (str or list): a song ID or list of song IDs
    
    Kwargs:
        buckets (list): A list of strings specifying which buckets to retrieve

        limit (bool): A boolean indicating whether or not to limit the results to one of the id spaces specified in buckets
    
    Returns:
        A list of term document dicts
    
    Example:

    >>> song_ids = [u'SOGNMKX12B0B806320', u'SOLUHKP129F0698D49', u'SOOLGAZ127F3E1B87C', u'SOQKVPH12A58A7AF4D', u'SOHKEEM1288D3ED9F5']
    >>> songs = song.profile(song_ids, buckets=['audio_summary'])
    [<song - chickfactor>,
     <song - One Step Closer>,
     <song - And I Am Telling You I'm Not Going (Glee Cast Version)>,
     <song - In This Temple As In The Hearts Of Man For Whom He Saved The Earth>,
     <song - Octet>]
    >>> songs[0].audio_summary
    {u'analysis_url': u'https://echonest-analysis.s3.amazonaws.com:443/TR/TRKHTDL123E858AC4B/3/full.json?Signature=sE6OwAzg6UvrtiX6nJJW1t7E6YI%3D&Expires=1287585351&AWSAccessKeyId=AKIAIAFEHLM3KJ2XMHRA',
     u'danceability': None,
     u'duration': 211.90485000000001,
     u'energy': None,
     u'key': 7,
     u'loudness': -16.736999999999998,
     u'mode': 1,
     u'tempo': 94.957999999999998,
     u'time_signature': 4}
    >>> 
    
    """
    buckets = buckets or []
    if not isinstance(ids, list):
        ids = [ids]
    kwargs = {}
    kwargs['id'] = ids
    if buckets:
        kwargs['bucket'] = buckets
    if limit:
        kwargs['limit'] = 'true'
    
    result = util.callm("%s/%s" % ('song', 'profile'), kwargs)
    return [Song(**util.fix(s_dict)) for s_dict in result['response']['songs']]


########NEW FILE########
__FILENAME__ = track
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

import hashlib
from proxies import TrackProxy
import util

class Track(TrackProxy):
    """
    Represents an audio analysis from The Echo Nest.

    All methods in this module return Track objects.

    Attributes:

        analysis_channels       int: the number of audio channels used during analysis
    
        analysis_sample_rate    float: the sample rate used during analysis
    
        analyzer_version        str: e.g. '3.01a'
    
        artist                  str or None: artist name
    
        bars                    list of dicts: timing of each measure
    
        beats                   list of dicts: timing of each beat
    
        bitrate                 int: the bitrate of the input mp3 (or other file)
        
        danceability            float: relative danceability (0 to 1)
    
        duration                float: length of track in seconds
        
        energy                  float: relative energy (0 to 1)
    
        end_of_fade_in          float: time in seconds track where fade-in ends
    
        id                      str: Echo Nest Track ID, e.g. 'TRTOBXJ1296BCDA33B'
    
        key                     int: between 0 (key of C) and 11 (key of B flat) inclusive
    
        key_confidence          float: confidence that key detection was accurate
    
        loudness                float: overall loudness in decibels (dB)
    
        md5                     str: 32-character checksum of the input mp3
    
        meta                    dict: other track metainfo
    
        mode                    int: 0 (major) or 1 (minor)
    
        mode_confidence         float: confidence that mode detection was accurate
    
        num_samples             int: total samples in the decoded track
    
        release                 str or None: the album name
    
        sample_md5              str: 32-character checksum of the decoded audio file
    
        samplerate              int: sample rate of input mp3
    
        sections                list of dicts: larger sections of song (chorus, bridge, solo, etc.)
    
        segments                list of dicts: timing, pitch, loudness and timbre for each segment
    
        start_of_fade_out       float: time in seconds where fade out begins
    
        status                  str: analysis status, e.g. 'complete', 'pending', 'error'
    
        tatums                  list of dicts: the smallest metrical unit (subdivision of a beat)
    
        tempo                   float: overall BPM (beats per minute)
    
        tempo_confidence        float: confidence that tempo detection was accurate
    
        title                   str or None: song title

    Each bar, beat, section, segment and tatum has a start time, a duration, and a confidence,
    in addition to whatever other data is given.
    
    Examples:
    
    >>> t = track.track_from_id('TRXXHTJ1294CD8F3B3')
    >>> t
    <track - Neverwas Restored (from Neverwas Soundtrack)>
    >>> t = track.track_from_md5('b8abf85746ab3416adabca63141d8c2d')
    >>> t
    <track - Neverwas Restored (from Neverwas Soundtrack)>
    >>> 
    """

    def __repr__(self):
        try:
            return "<%s - %s>" % (self._object_type.encode('utf-8'), self.title.encode('utf-8'))
        except AttributeError:
            # the title is None
            return "< Track >"
    
    def __str__(self):
        return self.title.encode('utf-8')

def _track_from_response(response):
    """
    This is the function that actually creates the track object
    """
    result = response['response']
    status = result['track']['status'].lower()
    if not status == 'complete':
        """
        pyechonest only supports wait = true for now, so this should not be pending
        """
        if status == 'error':
            raise Exception('there was an error analyzing the track')
        if status == 'pending':
            raise Exception('the track is still being analyzed')
        if status == 'forbidden':
            raise Exception('analysis of this track is forbidden')
        if status == 'unavailable':
            return track_from_reanalyzing_id(result['track']['id'])
    else:
        track = result['track']
        identifier      = track.pop('id') 
        md5             = track.pop('md5', None) # tracks from song api calls will not have an md5
        audio_summary   = track.pop('audio_summary')
        energy          = audio_summary.get('energy', 0)
        danceability    = audio_summary.get('danceability', 0)
        json_url        = audio_summary['analysis_url']
        json_string     = urllib2.urlopen(json_url).read()
        analysis        = json.loads(json_string)
        nested_track    = analysis.pop('track')
        track.update(analysis)
        track.update(nested_track)
        track.update({'analysis_url': json_url, 'energy': energy, 'danceability': danceability})
        return Track(identifier, md5, track)

def _upload(param_dict, data = None):
    """
    Calls upload either with a local audio file,
    or a url. Returns a track object.
    """
    param_dict['format'] = 'json'
    param_dict['wait'] = 'true'
    param_dict['bucket'] = 'audio_summary'
    result = util.callm('track/upload', param_dict, POST = True, socket_timeout = 300,  data = data) 
    return _track_from_response(result)

def _profile(param_dict):
    param_dict['format'] = 'json'
    param_dict['bucket'] = 'audio_summary'
    result = util.callm('track/profile', param_dict)
    return _track_from_response(result)

def _analyze(param_dict):
    param_dict['format'] = 'json'
    param_dict['bucket'] = 'audio_summary'
    param_dict['wait'] = 'true'
    result = util.callm('track/analyze', param_dict, POST = True, socket_timeout = 300)
    return _track_from_response(result)
    

""" Below are convenience functions for creating Track objects, you should use them """

def _track_from_string(audio_data, filetype):
    param_dict = {}
    param_dict['filetype'] = filetype 
    return _upload(param_dict, data = audio_data)

def track_from_file(file_object, filetype):
    """
    Create a track object from a file-like object.

    Args:
        file_object: a file-like Python object
        filetype: the file type (ex. mp3, ogg, wav)
    """
    try:
        hash = hashlib.md5(file_object.read()).hexdigest()
        return track_from_md5(hash)
    except util.EchoNestAPIError:
        file_object.seek(0)
        return _track_from_string(file_object.read(), filetype)

def track_from_filename(filename, filetype = None):
    """
    Create a track object from a filename.

    Args:
        filename: A string containing the path to the input file.
        filetype: A string indicating the filetype; Defaults to None (type determined by file extension).
    """
    filetype = filetype or filename.split('.')[-1]
    try:
        hash = hashlib.md5(open(filename, 'rb').read()).hexdigest()
        return track_from_md5(hash)
    except util.EchoNestAPIError:
        return track_from_file(open(filename, 'rb'), filetype)

def track_from_url(url):
    """
    Create a track object from a public http URL.

    Args:
        url: A string giving the URL to read from. This must be on a public machine accessible by HTTP.
    """
    param_dict = dict(url = url)
    return _upload(param_dict) 
     
def track_from_id(identifier):
    """
    Create a track object from an Echo Nest track ID.

    Args:
        identifier: A string containing the ID of a track already analyzed (looks like "TRLMNOP12345678901").
    """
    param_dict = dict(id = identifier)
    return _profile(param_dict)

def track_from_md5(md5):
    """
    Create a track object from an md5 hash.

    Args:
        md5: A string 32 characters long giving the md5 checksum of a track already analyzed.
    """
    param_dict = dict(md5 = md5)
    return _profile(param_dict)

def track_from_reanalyzing_id(identifier):
    """
    Create a track object from an Echo Nest track ID, reanalyzing the track first.

    Args:
        identifier: A string containing the ID of a track already analyzed (looks like "TRLMNOP12345678901").
    """
    param_dict = dict(id = identifier)
    return _analyze(param_dict)

def track_from_reanalyzing_md5(md5):
    """
    Create a track object from an md5 hash, reanalyzing the track first.

    Args:
        md5: A string containing the md5 of a track already analyzed (looks like "TRLMNOP12345678901").
    """
    param_dict = dict(md5 = md5)
    return _analyze(param_dict)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# encoding: utf-8

"""
Copyright (c) 2010 The Echo Nest. All rights reserved.
Created by Tyler Williams on 2010-04-25.

Utility functions to support the Echo Nest web API interface.
"""
import urllib
import urllib2
import httplib
import config
import logging
import socket
import re
import time
import os
import subprocess
import traceback
from types import StringType, UnicodeType

try:
    import json
except ImportError:
    import simplejson as json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TYPENAMES = (
    ('AR', 'artist'),
    ('SO', 'song'),
    ('RE', 'release'),
    ('TR', 'track'),
    ('PE', 'person'),
    ('DE', 'device'),
    ('LI', 'listener'),
    ('ED', 'editor'),
    ('TW', 'tweditor'),
    ('CA', 'catalog'),
)
foreign_regex = re.compile(r'^.+?:(%s):([^^]+)\^?([0-9\.]+)?' % r'|'.join(n[1] for n in TYPENAMES))
short_regex = re.compile(r'^((%s)[0-9A-Z]{16})\^?([0-9\.]+)?' % r'|'.join(n[0] for n in TYPENAMES))
long_regex = re.compile(r'music://id.echonest.com/.+?/(%s)/(%s)[0-9A-Z]{16}\^?([0-9\.]+)?' % (r'|'.join(n[0] for n in TYPENAMES), r'|'.join(n[0] for n in TYPENAMES)))
headers = [('User-Agent', 'Pyechonest %s' % (config.__version__,))]

class MyBaseHandler(urllib2.BaseHandler):
    def default_open(self, request):
        if config.TRACE_API_CALLS:
            logger.info("%s" % (request.get_full_url(),))
        request.start_time = time.time()
        return None
        
class MyErrorProcessor(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        code = response.code
        if config.TRACE_API_CALLS:
            logger.info("took %2.2fs: (%i)" % (time.time()-request.start_time,code))
        if code in [200, 400, 403, 500]:
            return response
        else:
            urllib2.HTTPErrorProcessor.http_response(self, request, response)

opener = urllib2.build_opener(MyBaseHandler(), MyErrorProcessor())
opener.addheaders = headers

class EchoNestAPIError(Exception):
    """
    Generic API errors. 
    """
    def __init__(self, code, message):
        self.args = ('Echo Nest API Error %d: %s' % (code, message),)

def get_successful_response(raw_json):
    try:
        response_dict = json.loads(raw_json)
        status_dict = response_dict['response']['status']
        code = int(status_dict['code'])
        message = status_dict['message']
        if (code != 0):
            # do some cute exception handling
            raise EchoNestAPIError(code, message)
        del response_dict['response']['status']
        return response_dict
    except ValueError:
        logger.debug(traceback.format_exc())
        raise EchoNestAPIError(-1, "Unknown error.")


# These two functions are to deal with the unknown encoded output of codegen (varies by platform and ID3 tag)
def reallyunicode(s, encoding="utf-8"):
    if type(s) is StringType:
        for args in ((encoding,), ('utf-8',), ('latin-1',), ('ascii', 'replace')):
            try:
                s = s.decode(*args)
                break
            except UnicodeDecodeError:
                continue
    if type(s) is not UnicodeType:
        raise ValueError, "%s is not a string at all." % s
    return s

def reallyUTF8(s):
    return reallyunicode(s).encode("utf-8")

def codegen(filename, start=0, duration=30):
    # Run codegen on the file and return the json. If start or duration is -1 ignore them.
    cmd = config.CODEGEN_BINARY_OVERRIDE
    if not cmd:
        # Is this is posix platform, or is it windows?
        if hasattr(os, 'uname'):
            if(os.uname()[0] == "Darwin"):
                cmd = "codegen.Darwin"
            else:
                cmd = 'codegen.'+os.uname()[0]+'-'+os.uname()[4]
        else:
            cmd = "codegen.windows.exe"

    if not os.path.exists(cmd):
        raise Exception("Codegen binary not found.")

    command = cmd + " \"" + filename + "\" " 
    if start >= 0:
        command = command + str(start) + " "
    if duration >= 0:
        command = command + str(duration)
        
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (json_block, errs) = p.communicate()
    json_block = reallyUTF8(json_block)

    try:
        return json.loads(json_block)
    except ValueError:
        logger.debug("No JSON object came out of codegen: error was %s" % (errs))
        return None


def callm(method, param_dict, POST=False, socket_timeout=None, data=None):
    """
    Call the api! 
    Param_dict is a *regular* *python* *dictionary* so if you want to have multi-valued params
    put them in a list.
    
    ** note, if we require 2.6, we can get rid of this timeout munging.
    """
    param_dict['api_key'] = config.ECHO_NEST_API_KEY
    param_list = []
    if not socket_timeout:
        socket_timeout = config.CALL_TIMEOUT
    
    for key,val in param_dict.iteritems():
        if isinstance(val, list):
            param_list.extend( [(key,subval) for subval in val] )
        else:
            if isinstance(val, unicode):
                val = val.encode('utf-8')
            param_list.append( (key,val) )

    params = urllib.urlencode(param_list)
        
    socket.setdefaulttimeout(socket_timeout)

    if(POST):
        if (not method == 'track/upload') or ((method == 'track/upload') and 'url' in param_dict):
            """
            this is a normal POST call
            """
            url = 'http://%s/%s/%s/%s' % (config.API_HOST, config.API_SELECTOR, 
                                        config.API_VERSION, method)
            
            if data is None:
                data = ''
            
            data = urllib.urlencode(data)
            data = "&".join([data, params])

            f = opener.open(url, data=data)
        else:
            """
            upload with a local file is special, as the body of the request is the content of the file,
            and the other parameters stay on the URL
            """
            url = '/%s/%s/%s?%s' % (config.API_SELECTOR, config.API_VERSION, 
                                        method, params)

            if ':' in config.API_HOST:
                host, port = config.API_HOST.split(':')
            else:
                host = config.API_HOST
                port = 80
                
            if config.TRACE_API_CALLS:
                logger.info("%s/%s" % (host+':'+str(port), url,))
            conn = httplib.HTTPConnection(host, port = port)
            conn.request('POST', url, body = data, headers = dict([('Content-Type', 'application/octet-stream')]+headers))
            f = conn.getresponse()

    else:
        """
        just a normal GET call
        """
        url = 'http://%s/%s/%s/%s?%s' % (config.API_HOST, config.API_SELECTOR, config.API_VERSION, 
                                        method, params)

        f = opener.open(url)
            
    socket.setdefaulttimeout(None)
    
    # try/except
    response_dict = get_successful_response(f.read())
    return response_dict


def postChunked(host, selector, fields, files):
    """
    Attempt to replace postMultipart() with nearly-identical interface.
    (The files tuple no longer requires the filename, and we only return
    the response body.) 
    Uses the urllib2_file.py originally from 
    http://fabien.seisen.org which was also drawn heavily from 
    http://code.activestate.com/recipes/146306/ .
    
    This urllib2_file.py is more desirable because of the chunked 
    uploading from a file pointer (no need to read entire file into 
    memory) and the ability to work from behind a proxy (due to its 
    basis on urllib2).
    """
    params = urllib.urlencode(fields)
    url = 'http://%s%s?%s' % (host, selector, params)
    u = urllib2.urlopen(url, files)
    result = u.read()
    [fp.close() for (key, fp) in files]
    return result


def fix(x):
    # we need this to fix up all the dict keys to be strings, not unicode objects
    assert(isinstance(x,dict))
    return dict((str(k), v) for (k,v) in x.iteritems())


########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
import re
import sys
import struct

from simplejson.scanner import make_scanner
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.
    
    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at" % (terminator,)
                raise ValueError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            # Unicode escape sequence
            esc = s[end + 1:end + 5]
            next_end = end + 5
            if len(esc) != 4:
                msg = "Invalid \\uXXXX escape"
                raise ValueError(errmsg(msg, s, end))
            uni = int(esc, 16)
            # Check for surrogate pair on UCS-4 systems
            if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                if not s[end + 5:end + 7] == '\\u':
                    raise ValueError(errmsg(msg, s, end))
                esc2 = s[end + 7:end + 11]
                if len(esc2) != 4:
                    raise ValueError(errmsg(msg, s, end))
                uni2 = int(esc2, 16)
                uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                next_end += 6
            char = unichr(uni)
            end = next_end
        # Append the unescaped character
        _append(char)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject((s, end), encoding, strict, scan_once, object_hook, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    pairs = {}
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            return pairs, end + 1
        elif nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise ValueError(errmsg("Expecting : delimiter", s, end))

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))

    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray((s, end), scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.

        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        try:
            obj, end = self.scan_once(s, idx)
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
import re

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None
try:
    from simplejson._speedups import make_encoder as c_make_encoder
except ImportError:
    c_make_encoder = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def encode_basestring(s):
    """Return a JSON representation of a Python string

    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    """Return an ASCII-only JSON representation of a Python string

    """
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = c_encode_basestring_ascii or py_encode_basestring_ascii

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, str):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan, _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor- and/or
            # platform-specific, so do tests which don't depend on the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError("Out of range float values are not JSON compliant: %r"
                    % (o,))

            return text


        if _one_shot and c_make_encoder is not None and not self.indent and not self.sort_keys:
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)
        return _iterencode(o, 0)

def _make_iterencode(markers, _default, _encoder, _indent, _floatstr, _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        ## HACK: hand-optimized bytecode; turn globals into locals
        False=False,
        True=True,
        ValueError=ValueError,
        basestring=basestring,
        dict=dict,
        float=float,
        id=id,
        int=int,
        isinstance=isinstance,
        list=list,
        long=long,
        str=str,
        tuple=tuple,
    ):

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, basestring):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, (int, long)):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = dct.items()
            items.sort(key=lambda kv: kv[0])
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif _skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, basestring):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, (int, long)):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, basestring):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
try:
    from simplejson._speedups import make_scanner as c_make_scanner
except ImportError:
    c_make_scanner = None

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict, _scan_once, object_hook)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    return _scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = test_check_circular
from unittest import TestCase
import simplejson as json

def default_iterable(obj):
    return list(obj)

class TestCheckCircular(TestCase):
    def test_circular_dict(self):
        dct = {}
        dct['a'] = dct
        self.assertRaises(ValueError, json.dumps, dct)

    def test_circular_list(self):
        lst = []
        lst.append(lst)
        self.assertRaises(ValueError, json.dumps, lst)

    def test_circular_composite(self):
        dct2 = {}
        dct2['a'] = []
        dct2['a'].append(dct2)
        self.assertRaises(ValueError, json.dumps, dct2)

    def test_circular_default(self):
        json.dumps([set()], default=default_iterable)
        self.assertRaises(TypeError, json.dumps, [set()])

    def test_circular_off_default(self):
        json.dumps([set()], default=default_iterable, check_circular=False)
        self.assertRaises(TypeError, json.dumps, [set()], check_circular=False)

########NEW FILE########
__FILENAME__ = test_decode
import decimal
from unittest import TestCase

import simplejson as S

class TestDecode(TestCase):
    def test_decimal(self):
        rval = S.loads('1.1', parse_float=decimal.Decimal)
        self.assert_(isinstance(rval, decimal.Decimal))
        self.assertEquals(rval, decimal.Decimal('1.1'))

    def test_float(self):
        rval = S.loads('1', parse_int=float)
        self.assert_(isinstance(rval, float))
        self.assertEquals(rval, 1.0)

    def test_decoder_optimizations(self):
        # Several optimizations were made that skip over calls to
        # the whitespace regex, so this test is designed to try and
        # exercise the uncommon cases. The array cases are already covered.
        rval = S.loads('{   "key"    :    "value"    ,  "k":"v"    }')
        self.assertEquals(rval, {"key":"value", "k":"v"})

########NEW FILE########
__FILENAME__ = test_default
from unittest import TestCase

import simplejson as S

class TestDefault(TestCase):
    def test_default(self):
        self.assertEquals(
            S.dumps(type, default=repr),
            S.dumps(repr(type)))

########NEW FILE########
__FILENAME__ = test_dump
from unittest import TestCase
from cStringIO import StringIO

import simplejson as S

class TestDump(TestCase):
    def test_dump(self):
        sio = StringIO()
        S.dump({}, sio)
        self.assertEquals(sio.getvalue(), '{}')

    def test_dumps(self):
        self.assertEquals(S.dumps({}), '{}')

########NEW FILE########
__FILENAME__ = test_encode_basestring_ascii
from unittest import TestCase

import simplejson.encoder

CASES = [
    (u'/\\"\ucafe\ubabe\uab98\ufcde\ubcda\uef4a\x08\x0c\n\r\t`1~!@#$%^&*()_+-=[]{}|;:\',./<>?', '"/\\\\\\"\\ucafe\\ubabe\\uab98\\ufcde\\ubcda\\uef4a\\b\\f\\n\\r\\t`1~!@#$%^&*()_+-=[]{}|;:\',./<>?"'),
    (u'\u0123\u4567\u89ab\ucdef\uabcd\uef4a', '"\\u0123\\u4567\\u89ab\\ucdef\\uabcd\\uef4a"'),
    (u'controls', '"controls"'),
    (u'\x08\x0c\n\r\t', '"\\b\\f\\n\\r\\t"'),
    (u'{"object with 1 member":["array with 1 element"]}', '"{\\"object with 1 member\\":[\\"array with 1 element\\"]}"'),
    (u' s p a c e d ', '" s p a c e d "'),
    (u'\U0001d120', '"\\ud834\\udd20"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    ('\xce\xb1\xce\xa9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    ('\xce\xb1\xce\xa9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    (u"`1~!@#$%^&*()_+-={':[,]}|;.</>?", '"`1~!@#$%^&*()_+-={\':[,]}|;.</>?"'),
    (u'\x08\x0c\n\r\t', '"\\b\\f\\n\\r\\t"'),
    (u'\u0123\u4567\u89ab\ucdef\uabcd\uef4a', '"\\u0123\\u4567\\u89ab\\ucdef\\uabcd\\uef4a"'),
]

class TestEncodeBaseStringAscii(TestCase):
    def test_py_encode_basestring_ascii(self):
        self._test_encode_basestring_ascii(simplejson.encoder.py_encode_basestring_ascii)

    def test_c_encode_basestring_ascii(self):
        if not simplejson.encoder.c_encode_basestring_ascii:
            return
        self._test_encode_basestring_ascii(simplejson.encoder.c_encode_basestring_ascii)

    def _test_encode_basestring_ascii(self, encode_basestring_ascii):
        fname = encode_basestring_ascii.__name__
        for input_string, expect in CASES:
            result = encode_basestring_ascii(input_string)
            self.assertEquals(result, expect,
                '%r != %r for %s(%r)' % (result, expect, fname, input_string))

########NEW FILE########
__FILENAME__ = test_fail
from unittest import TestCase

import simplejson as S

# Fri Dec 30 18:57:26 2005
JSONDOCS = [
    # http://json.org/JSON_checker/test/fail1.json
    '"A JSON payload should be an object or array, not a string."',
    # http://json.org/JSON_checker/test/fail2.json
    '["Unclosed array"',
    # http://json.org/JSON_checker/test/fail3.json
    '{unquoted_key: "keys must be quoted}',
    # http://json.org/JSON_checker/test/fail4.json
    '["extra comma",]',
    # http://json.org/JSON_checker/test/fail5.json
    '["double extra comma",,]',
    # http://json.org/JSON_checker/test/fail6.json
    '[   , "<-- missing value"]',
    # http://json.org/JSON_checker/test/fail7.json
    '["Comma after the close"],',
    # http://json.org/JSON_checker/test/fail8.json
    '["Extra close"]]',
    # http://json.org/JSON_checker/test/fail9.json
    '{"Extra comma": true,}',
    # http://json.org/JSON_checker/test/fail10.json
    '{"Extra value after close": true} "misplaced quoted value"',
    # http://json.org/JSON_checker/test/fail11.json
    '{"Illegal expression": 1 + 2}',
    # http://json.org/JSON_checker/test/fail12.json
    '{"Illegal invocation": alert()}',
    # http://json.org/JSON_checker/test/fail13.json
    '{"Numbers cannot have leading zeroes": 013}',
    # http://json.org/JSON_checker/test/fail14.json
    '{"Numbers cannot be hex": 0x14}',
    # http://json.org/JSON_checker/test/fail15.json
    '["Illegal backslash escape: \\x15"]',
    # http://json.org/JSON_checker/test/fail16.json
    '["Illegal backslash escape: \\\'"]',
    # http://json.org/JSON_checker/test/fail17.json
    '["Illegal backslash escape: \\017"]',
    # http://json.org/JSON_checker/test/fail18.json
    '[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]',
    # http://json.org/JSON_checker/test/fail19.json
    '{"Missing colon" null}',
    # http://json.org/JSON_checker/test/fail20.json
    '{"Double colon":: null}',
    # http://json.org/JSON_checker/test/fail21.json
    '{"Comma instead of colon", null}',
    # http://json.org/JSON_checker/test/fail22.json
    '["Colon instead of comma": false]',
    # http://json.org/JSON_checker/test/fail23.json
    '["Bad value", truth]',
    # http://json.org/JSON_checker/test/fail24.json
    "['single quote']",
    # http://code.google.com/p/simplejson/issues/detail?id=3
    u'["A\u001FZ control characters in string"]',
]

SKIPS = {
    1: "why not have a string payload?",
    18: "spec doesn't specify any nesting limitations",
}

class TestFail(TestCase):
    def test_failures(self):
        for idx, doc in enumerate(JSONDOCS):
            idx = idx + 1
            if idx in SKIPS:
                S.loads(doc)
                continue
            try:
                S.loads(doc)
            except ValueError:
                pass
            else:
                self.fail("Expected failure for fail%d.json: %r" % (idx, doc))

########NEW FILE########
__FILENAME__ = test_float
import math
from unittest import TestCase

import simplejson as S

class TestFloat(TestCase):
    def test_floats(self):
        for num in [1617161771.7650001, math.pi, math.pi**100, math.pi**-100, 3.1]:
            self.assertEquals(float(S.dumps(num)), num)
            self.assertEquals(S.loads(S.dumps(num)), num)

    def test_ints(self):
        for num in [1, 1L, 1<<32, 1<<64]:
            self.assertEquals(S.dumps(num), str(num))
            self.assertEquals(int(S.dumps(num)), num)

########NEW FILE########
__FILENAME__ = test_indent
from unittest import TestCase

import simplejson as S
import textwrap

class TestIndent(TestCase):
    def test_indent(self):
        h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
             {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

        expect = textwrap.dedent("""\
        [
          [
            "blorpie"
          ],
          [
            "whoops"
          ],
          [],
          "d-shtaeou",
          "d-nthiouh",
          "i-vhbjkhnth",
          {
            "nifty": 87
          },
          {
            "field": "yes",
            "morefield": false
          }
        ]""")


        d1 = S.dumps(h)
        d2 = S.dumps(h, indent=2, sort_keys=True, separators=(',', ': '))

        h1 = S.loads(d1)
        h2 = S.loads(d2)

        self.assertEquals(h1, h)
        self.assertEquals(h2, h)
        self.assertEquals(d2, expect)

########NEW FILE########
__FILENAME__ = test_pass1
from unittest import TestCase

import simplejson as S

# from http://json.org/JSON_checker/test/pass1.json
JSON = r'''
[
    "JSON Test Pattern pass1",
    {"object with 1 member":["array with 1 element"]},
    {},
    [],
    -42,
    true,
    false,
    null,
    {
        "integer": 1234567890,
        "real": -9876.543210,
        "e": 0.123456789e-12,
        "E": 1.234567890E+34,
        "":  23456789012E666,
        "zero": 0,
        "one": 1,
        "space": " ",
        "quote": "\"",
        "backslash": "\\",
        "controls": "\b\f\n\r\t",
        "slash": "/ & \/",
        "alpha": "abcdefghijklmnopqrstuvwyz",
        "ALPHA": "ABCDEFGHIJKLMNOPQRSTUVWYZ",
        "digit": "0123456789",
        "special": "`1~!@#$%^&*()_+-={':[,]}|;.</>?",
        "hex": "\u0123\u4567\u89AB\uCDEF\uabcd\uef4A",
        "true": true,
        "false": false,
        "null": null,
        "array":[  ],
        "object":{  },
        "address": "50 St. James Street",
        "url": "http://www.JSON.org/",
        "comment": "// /* <!-- --",
        "# -- --> */": " ",
        " s p a c e d " :[1,2 , 3

,

4 , 5        ,          6           ,7        ],
        "compact": [1,2,3,4,5,6,7],
        "jsontext": "{\"object with 1 member\":[\"array with 1 element\"]}",
        "quotes": "&#34; \u0022 %22 0x22 034 &#x22;",
        "\/\\\"\uCAFE\uBABE\uAB98\uFCDE\ubcda\uef4A\b\f\n\r\t`1~!@#$%^&*()_+-=[]{}|;:',./<>?"
: "A key can be any string"
    },
    0.5 ,98.6
,
99.44
,

1066


,"rosebud"]
'''

class TestPass1(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))
        try:
            S.dumps(res, allow_nan=False)
        except ValueError:
            pass
        else:
            self.fail("23456789012E666 should be out of range")

########NEW FILE########
__FILENAME__ = test_pass2
from unittest import TestCase
import simplejson as S

# from http://json.org/JSON_checker/test/pass2.json
JSON = r'''
[[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]
'''

class TestPass2(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))

########NEW FILE########
__FILENAME__ = test_pass3
from unittest import TestCase

import simplejson as S

# from http://json.org/JSON_checker/test/pass3.json
JSON = r'''
{
    "JSON Test Pattern pass3": {
        "The outermost value": "must be an object or array.",
        "In this test": "It is an object."
    }
}
'''

class TestPass3(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))

########NEW FILE########
__FILENAME__ = test_recursion
from unittest import TestCase

import simplejson as S

class JSONTestObject:
    pass

class RecursiveJSONEncoder(S.JSONEncoder):
    recurse = False
    def default(self, o):
        if o is JSONTestObject:
            if self.recurse:
                return [JSONTestObject]
            else:
                return 'JSONTestObject'
        return S.JSONEncoder.default(o)

class TestRecursion(TestCase):
    def test_listrecursion(self):
        x = []
        x.append(x)
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on list recursion")
        x = []
        y = [x]
        x.append(y)
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on alternating list recursion")
        y = []
        x = [y, y]
        # ensure that the marker is cleared
        S.dumps(x)

    def test_dictrecursion(self):
        x = {}
        x["test"] = x
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on dict recursion")
        x = {}
        y = {"a": x, "b": x}
        # ensure that the marker is cleared
        S.dumps(x)

    def test_defaultrecursion(self):
        enc = RecursiveJSONEncoder()
        self.assertEquals(enc.encode(JSONTestObject), '"JSONTestObject"')
        enc.recurse = True
        try:
            enc.encode(JSONTestObject)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on default recursion")

########NEW FILE########
__FILENAME__ = test_scanstring
import sys
import decimal
from unittest import TestCase

import simplejson.decoder

class TestScanString(TestCase):
    def test_py_scanstring(self):
        self._test_scanstring(simplejson.decoder.py_scanstring)

    def test_c_scanstring(self):
        if not simplejson.decoder.c_scanstring:
            return
        self._test_scanstring(simplejson.decoder.c_scanstring)

    def _test_scanstring(self, scanstring):
        self.assertEquals(
            scanstring('"z\\ud834\\udd20x"', 1, None, True),
            (u'z\U0001d120x', 16))

        if sys.maxunicode == 65535:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 6))
        else:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 5))

        self.assertEquals(
            scanstring('"\\u007b"', 1, None, True),
            (u'{', 8))

        self.assertEquals(
            scanstring('"A JSON payload should be an object or array, not a string."', 1, None, True),
            (u'A JSON payload should be an object or array, not a string.', 60))

        self.assertEquals(
            scanstring('["Unclosed array"', 2, None, True),
            (u'Unclosed array', 17))

        self.assertEquals(
            scanstring('["extra comma",]', 2, None, True),
            (u'extra comma', 14))

        self.assertEquals(
            scanstring('["double extra comma",,]', 2, None, True),
            (u'double extra comma', 21))

        self.assertEquals(
            scanstring('["Comma after the close"],', 2, None, True),
            (u'Comma after the close', 24))

        self.assertEquals(
            scanstring('["Extra close"]]', 2, None, True),
            (u'Extra close', 14))

        self.assertEquals(
            scanstring('{"Extra comma": true,}', 2, None, True),
            (u'Extra comma', 14))

        self.assertEquals(
            scanstring('{"Extra value after close": true} "misplaced quoted value"', 2, None, True),
            (u'Extra value after close', 26))

        self.assertEquals(
            scanstring('{"Illegal expression": 1 + 2}', 2, None, True),
            (u'Illegal expression', 21))

        self.assertEquals(
            scanstring('{"Illegal invocation": alert()}', 2, None, True),
            (u'Illegal invocation', 21))

        self.assertEquals(
            scanstring('{"Numbers cannot have leading zeroes": 013}', 2, None, True),
            (u'Numbers cannot have leading zeroes', 37))

        self.assertEquals(
            scanstring('{"Numbers cannot be hex": 0x14}', 2, None, True),
            (u'Numbers cannot be hex', 24))

        self.assertEquals(
            scanstring('[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]', 21, None, True),
            (u'Too deep', 30))

        self.assertEquals(
            scanstring('{"Missing colon" null}', 2, None, True),
            (u'Missing colon', 16))

        self.assertEquals(
            scanstring('{"Double colon":: null}', 2, None, True),
            (u'Double colon', 15))

        self.assertEquals(
            scanstring('{"Comma instead of colon", null}', 2, None, True),
            (u'Comma instead of colon', 25))

        self.assertEquals(
            scanstring('["Colon instead of comma": false]', 2, None, True),
            (u'Colon instead of comma', 25))

        self.assertEquals(
            scanstring('["Bad value", truth]', 2, None, True),
            (u'Bad value', 12))

########NEW FILE########
__FILENAME__ = test_separators
import textwrap
from unittest import TestCase

import simplejson as S


class TestSeparators(TestCase):
    def test_separators(self):
        h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
             {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

        expect = textwrap.dedent("""\
        [
          [
            "blorpie"
          ] ,
          [
            "whoops"
          ] ,
          [] ,
          "d-shtaeou" ,
          "d-nthiouh" ,
          "i-vhbjkhnth" ,
          {
            "nifty" : 87
          } ,
          {
            "field" : "yes" ,
            "morefield" : false
          }
        ]""")


        d1 = S.dumps(h)
        d2 = S.dumps(h, indent=2, sort_keys=True, separators=(' ,', ' : '))

        h1 = S.loads(d1)
        h2 = S.loads(d2)

        self.assertEquals(h1, h)
        self.assertEquals(h2, h)
        self.assertEquals(d2, expect)

########NEW FILE########
__FILENAME__ = test_unicode
from unittest import TestCase

import simplejson as S

class TestUnicode(TestCase):
    def test_encoding1(self):
        encoder = S.JSONEncoder(encoding='utf-8')
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = encoder.encode(u)
        js = encoder.encode(s)
        self.assertEquals(ju, js)

    def test_encoding2(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = S.dumps(u, encoding='utf-8')
        js = S.dumps(s, encoding='utf-8')
        self.assertEquals(ju, js)

    def test_encoding3(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps(u)
        self.assertEquals(j, '"\\u03b1\\u03a9"')

    def test_encoding4(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps([u])
        self.assertEquals(j, '["\\u03b1\\u03a9"]')

    def test_encoding5(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps(u, ensure_ascii=False)
        self.assertEquals(j, u'"%s"' % (u,))

    def test_encoding6(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps([u], ensure_ascii=False)
        self.assertEquals(j, u'["%s"]' % (u,))

    def test_big_unicode_encode(self):
        u = u'\U0001d120'
        self.assertEquals(S.dumps(u), '"\\ud834\\udd20"')
        self.assertEquals(S.dumps(u, ensure_ascii=False), u'"\U0001d120"')

    def test_big_unicode_decode(self):
        u = u'z\U0001d120x'
        self.assertEquals(S.loads('"' + u + '"'), u)
        self.assertEquals(S.loads('"z\\ud834\\udd20x"'), u)

    def test_unicode_decode(self):
        for i in range(0, 0xd7ff):
            u = unichr(i)
            json = '"\\u%04x"' % (i,)
            self.assertEquals(S.loads(json), u)

    def test_default_encoding(self):
        self.assertEquals(S.loads(u'{"a": "\xe9"}'.encode('utf-8')),
            {'a': u'\xe9'})

    def test_unicode_preservation(self):
        self.assertEquals(type(S.loads(u'""')), unicode)
        self.assertEquals(type(S.loads(u'"a"')), unicode)
        self.assertEquals(type(S.loads(u'["a"]')[0]), unicode)
########NEW FILE########
__FILENAME__ = tool
r"""Using simplejson from the shell to validate and
pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson.tool
    Expecting property name: line 1 column 2 (char 2)
"""
import simplejson

def main():
    import sys
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit("%s [infile [outfile]]" % (sys.argv[0],))
    try:
        obj = simplejson.load(infile)
    except ValueError, e:
        raise SystemExit(e)
    simplejson.dump(obj, outfile, sort_keys=True, indent=4)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = visage
import hmac
import os
import random
import simplejson
import sys
import urllib
import urllib2
import traceback
from face_client import face_client
from pyechonest import config, artist, song

SPOTIFY_BASE_URL = 'http://ws.spotify.com/search/1/%s.json?q=%s'

# edit me!
FACE_API_KEY = ''
FACE_API_SECRET = ''
FB_SESSION_KEY = ''
FB_USER = ''
ISIGHTCAPTURE_PATH = '/usr/local/bin/isightcapture'
HUNCH_AUTH_TOKEN = ''

# for grooveshark
GROOVESHARK_SESSION_ID = ''
GROOVESHARK_API_KEY = ''
GROOVESHARK_SECRET = ''
GROOVESHARK_BASE_URL = 'http://api.grooveshark.com/ws/2.1/'
config.ECHO_NEST_API_KEY= ''

SPOTIFY_SCRIPT_SONG = """osascript<<END
on spotify_exec(command)
	if command is "mute" then set menu_item to 10
	if command is "unmute" then set menu_item to 9
	tell application "Spotify" to activate
	tell application "System Events"
		tell process "Spotify"
			repeat 10 times
				click menu item menu_item of menu 1 of menu bar item 6 of menu bar 1
			end repeat
		end tell
	end tell
end spotify_exec

spotify_exec("mute")
open location "%s"
say "%s is in the house!"

tell application "Spotify" to activate
tell application "System Events"
	tell process "Spotify"
		my spotify_exec("unmute")
                -- tell application "System Events" to set visible of process "Spotify" to false
	end tell
end tell
"""

SPOTIFY_SCRIPT = """osascript<<END
on spotify_exec(command)
	if command is "mute" then set menu_item to 10
	if command is "unmute" then set menu_item to 9
	tell application "Spotify" to activate
	tell application "System Events"
		tell process "Spotify"
			repeat 10 times
				click menu item menu_item of menu 1 of menu bar item 6 of menu bar 1
			end repeat
		end tell
	end tell
end spotify_exec

spotify_exec("mute")
open location "%s"
say "%s is in the house!"

tell application "Spotify" to activate
tell application "System Events"
	tell process "Spotify"
		keystroke "l" using {command down}
		repeat 3 times
			keystroke tab
		end repeat
		repeat %d times
			key code {125}
		end repeat
		keystroke return
		my spotify_exec("unmute")
                -- tell application "System Events" to set visible of process "Spotify" to false
	end tell
end tell
"""

def recognize(live=True, path='/tmp/pic.jpg'):
    client = face_client.FaceClient(FACE_API_KEY, FACE_API_SECRET)
    client.set_facebook_credentials(session=FB_SESSION_KEY, user=FB_USER)
    if live:
        os.system('%s %s' % (ISIGHTCAPTURE_PATH, path))
    result = client.faces_recognize(file=path, uids='friends@facebook.com', aggressive=True)
    if not result:
        return 'Could not recognize face'
    try:
        print [uid for uid in result['photos'][0]['tags'][0]['uids'][:5]]
        uid = result['photos'][0]['tags'][0]['uids'][0]['uid']
    except:
        return result

    uid = uid.replace('@facebook.com', '')
    fb_result = fetch_url('http://graph.facebook.com/' + uid)
    if not fb_result:
        return 'Could not contact facebook'
    fb_result = simplejson.loads(fb_result)
    print '\n\n\nHello, %s\n\n\n' % (fb_result['name'])
    return {'uid': uid, 'name': fb_result['name']}

def train(url):
    print 'training...'
    client = face_client.FaceClient(FACE_API_KEY, FACE_API_SECRET)
    client.set_facebook_credentials(session=FB_SESSION_KEY, user=FB_USER)
    if 'profile.php' in url:
        id = url[url.find('id=') + 3:]
        result = client.faces_train(uids='%s@facebook.com' % (id))
        return result
    url = url.replace('www.facebook.com', 'graph.facebook.com')
    result = fetch_url(url)
    if not result:
        return 'Could not train'
    id = simplejson.loads(result).get('id')
    result = client.faces_train(uids='%s@facebook.com' % (id))
    return result

def debug_print(string):
    print '!'*80
    print string
    print '!'*80


def musicify(live=True, uid=None):
    result = {}
    name = ''
    if not uid:
        result = recognize(live=live)
        uid = result.get('uid')
        name = result.get('name')
        if not uid or type(uid) == dict:
            return 'Sorry, could not recognize face'

    fb_id = 'fb_' + uid

    # recs = get_recs('hn_t32564', fb_id)
    if not uid == '5552189986':
        recs = get_recs('list_musician', fb_id)
    else:
        recs = {'recommendations':[{'name':'Loscil'},{'name':'School of Seven Bells'},{'name':'Gold Panda'},{'name':'Solvent'},{'name':'Tycho'},{'name':'Lusine'}]}
    worked = False
    song_name = ''
    artist = ''
    while not worked:
        try:
            artist = random.choice(recs.get('recommendations')).get('name')
            debug_print(artist)
            # Uncomment to use the Echonest API
            # artist_id = echonest_artist_id(artist)
            # debug_print(artist_id)
            # songs = echonest_dance_songs(artist_id)
            if False:
                success = False
                num_tries = 0
                while not success and num_tries < 9:
                    song_choice = random.choice(songs)
                    song_name = song_choice.title
                    song = ' '.join([artist, song_name])
                    try:
                        spotify_queue_type('track', song, name=name)
                        success = True
                    except:
                        num_tries += 1
                        continue

            else:
                spotify_queue_type('artist', artist, name=name)

            worked = True
        except Exception, e:
            traceback.print_exc(file=sys.stdout)
            pass

    result['artist'] = artist
    result['title'] = song_name
    return result


def get_recs(topic_id, user_id):
    url = 'http://api.hunch.com/api/v1/get-recommendations/?topic_ids=%s&limit=10&group_user_ids=%s&minimal=1&popularity=0&auth_token=%s' % (topic_id, user_id, HUNCH_AUTH_TOKEN)
    return simplejson.loads(fetch_url(url))

def spotify_queue(href, name=''):
    os.system(SPOTIFY_SCRIPT % (href, name or 'Automatic DJ', random.randint(0,10)))

def spotify_queue_song(href, name=''):
    debug_print(href)
    debug_print("song!!!!")
    os.system(SPOTIFY_SCRIPT_SONG % (href, name or 'Automatic DJ'))

def spotify_queue_type(music_type, query, name=''):
    url = SPOTIFY_BASE_URL % (music_type, urllib.quote(query))
    result = fetch_url(url)
    if not result:
        return False
    result = simplejson.loads(result)
    href = result.get(music_type + 's')[0].get('href')
    spotify_queue(href, name)

def spotify_queue_album(query, name=''):
    url = SPOTIFY_BASE_URL % ('album', urllib.quote(query))
    result = fetch_url(url)
    if not result:
        return False
    result = simplejson.loads(result)
    href = result.get('albums')[0].get('artists')[0].get('href')
    spotify_queue(href, name)

def spotify_queue_artist(query, name=''):
    url = SPOTIFY_BASE_URL % ('artist', urllib.quote(query))
    result = fetch_url(url)
    if not result:
        return False
    result = simplejson.loads(result)
    href = result.get('albums')[0].get('artists')[0].get('href')
    spotify_queue(href, name)

def spotify_prompt():
    artist = raw_input('What artist would you like to hear today? ')
    spotify_queue_type('artist', artist)

def echonest_artist_id(artist_name):
    result = artist.search(name=artist_name)
    if not result:
        return False
    return result[0].id

def echonest_dance_songs(artist_id, dance=0.6, maxresults=10):
    return song.search(artist_id=artist_id,
                       min_danceability=dance,
                       results=maxresults,
                       sort='danceability-desc',
                       buckets=['audio_summary'])

def fetch_url(url, values=None):
    user_agent = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_8; en-US) AppleWebKit/534.13 (KHTML, like Gecko) Chrome/9.0.597.94 Safari/534.13'
    headers = {'User-Agent': user_agent}
    if values:
        data = urllib.urlencode(values).replace('%5B', '[').replace('%5D', ']')
    else:
        data = ''
    print url

    req = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    return the_page

def gs_sign_request(method, dict_object):
    test = ''
    code = hmac.new(GROOVESHARK_SECRET)
    code.update(method)
    test += method
    # encoded_args = sorted([(k.encode('utf-8') if type(k) in [str,unicode] else str(k), v.encode('utf-8') if type(v) in [str,unicode] else (flatten_dict(v) if type(v) in [dict] else str(v))) for k, v in dict_object.items()])
    encoded_args = []
    for key, value in encoded_args:
        code.update(key)
        code.update(value)
        test += key
        test += value
    print "!"*80
    print test
    print "!"*80
    return code.hexdigest()

def flatten_dict(dict_object):
    string = ''
    for k, v in dict_object.items():
        string += k.encode('utf-8') + v.encode('utf-8')
    return string

def gs_call_method(method, dict_object, format='json'):
    dict_object['sessionID'] = GROOVESHARK_SESSION_ID
    data = {}
    data.update(dict_object)
    data['method'] = method
    data['sig'] = gs_sign_request(method, dict_object)
    data['format'] = format
    data['wsKey'] = GROOVESHARK_API_KEY
    return data

def gs_country():
    return {'country[ID]': '223',
            'country[CC1]': '0',
            'country[CC3]': '0',
            'country[CC2]': '0',
            'country[CC4]': '1073741824',
            'country[IPR]': '3949'}

def gs_get_song():
    songid = 145992
    method = 'getSubscriberStreamKey'

    params = {}
    params['songID'] = songid
    params['lowBitrate'] = 0
    params = gs_call_method(method, params)

    sigparams = {"country": "ID223CC10CC20CC30CC41073741824IPR3949",
                 "songID": songid,
                 "lowBitrate": '0',
                 "sessionID": GROOVESHARK_SESSION_ID}

    print params
    params['sig'] = gs_sign_request(method, sigparams)

    querystring = urllib.urlencode(params) + '&country[ID]=223&country[CC1]=0&country[CC2]=0&country[CC3]=0&country[CC4]=1073741824&country[IPR]=3949'
    url = GROOVESHARK_BASE_URL + '?' + querystring

    print url
    res = fetch_url(url)

    print res


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'recognize':
        recognize()
    else:
        os.system('clear')
        spotify_prompt()

########NEW FILE########
