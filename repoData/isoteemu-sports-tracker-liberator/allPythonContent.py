__FILENAME__ = endomondo
# -*- coding: utf-8 -*-

from . import __version__, __title__
from .workout import sports, Workout, TrackPoint
from .utils import chunks, str_to_datetime, datetime_to_str, gzip_string
from .exceptions import *

import platform
import uuid, socket
import random
from datetime import datetime, timedelta

import requests
import zlib
import json

import logging

URL_AUTHENTICATE	= 'https://api.mobile.endomondo.com/mobile/auth'
URL_WORKOUTS		= 'https://api.mobile.endomondo.com/mobile/api/workouts'
URL_WORKOUT_GET 	= 'https://api.mobile.endomondo.com/mobile/api/workout/get'
URL_WORKOUT_POST	= 'https://api.mobile.endomondo.com/mobile/api/workout/post'
URL_TRACK			= 'https://api.mobile.endomondo.com/mobile/track'
URL_PLAYLIST		= 'https://api.mobile.endomondo.com/mobile/playlist'

URL_ACCOUNT_GET		= 'https://api.mobile.endomondo.com/mobile/api/profile/account/get'
URL_ACCOUNT_POST	= 'https://api.mobile.endomondo.com/mobile/api/profile/account/post'

UNITS_METRIC		= 'METRIC'
UNITS_IMPERIAL		= 'IMPERIAL'

GENDER_MALE			= 'MALE'
GENDER_FEMALE		= 'FEMALE'

'''
	Playlist items are sent one-by-one, using post and in format:
	>>> 1;I Will Survive;Gloria Gaynor;;;;2014-04-05 17:22:56 UTC;2014-04-05 17:23:26 UTC;;
	[...]
	>>> 6;Holding Out for a Hero;Bonnie Tyler;;;;2014-04-05 17:38:46 UTC;2014-04-05 17:44:47 UTC;<lat>;<lng>
'''

class MobileApi(object):

	auth_token		= None
	secure_token	= None

	Requests		= requests.session()

	''' Details which Endomondo app sends back to home.
		If, for some reason, endomondo blocks this library, thease are likely what values they are using to validate against.
	'''
	device_info		= {
		'os':			platform.system(),
		'model':		platform.python_implementation(),
		'osVersion':	platform.release(),
		'vendor':		'github/isoteemu',
		'appVariant':	__title__,
		'country':		'GB',
		'v':			'2.4', # No idea, maybe api version?
		'appVersion':	__version__,
		'deviceId':		str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname())),
	}

	def __init__(self, **kwargs):
		'''
			:param auth_token: Optional Previous authentication token to use.
			:param email: Optional Authentication email.
			:param password: Optional Authentication password.
		'''
		email = kwargs.get('email')
		password = kwargs.get('password')

		if kwargs.get('auth_token'):
			self.set_auth_token(kwargs.get('auth_token'))
		elif email and password:
			self.set_auth_token(self.request_auth_token(email, password))

		if self.device_info['os'] in ['Linux']:
			self.device_info['vendor'] = platform.linux_distribution()[0]

		'''	User agent in endomondo app v. 10.1.1 is as:
			com.endomondo.android.pro/10.1.1 (Linux; U; Android {android_version}; {locality}; {build_model}; {phone_build_specific}) {resolution} {manufacturer} {model}
		'''
		self.Requests.headers['User-Agent'] = '{appVariant}/{appVersion} ({os}; {osVersion}; {model}) {vendor}'.format(**self.device_info)

	def get_auth_token(self):
		return self.auth_token

	def set_auth_token(self, auth_token):
		self.auth_token = auth_token

	def request_auth_token(self, email, password):
		''' Retrieve authentication token.
			:param email: Endomondo login email
			:param password: Endomondo login password

			At version 10.1.1, returned values are:
			action=PAIRED
			authToken=<authtoken>
			measure=METRIC
			displayName=<name>
			userId=<uid>
			facebookConnected=<true|false>
			secureToken=<securetoken>

			secureToken is quite new, and needed for personal data retrieval.
		'''

		params = self.device_info
		params.update({
			'action':	'pair',
			'email':	email,
			'password':	password
		})

		r = self.Requests.get(URL_AUTHENTICATE, params=params)

		lines = r.text.split("\n")
		if lines[0] != "OK":

			logging.warning("Logging failed into Endomondo, returned data was: %s" % r.text)
			raise AuthenticationError("Could not authenticate with Endomondo, Expected 'OK', got '%s'" % lines[0])

		lines.pop(0)
		for line in lines:
			key, value = line.split("=")
			if key == "authToken":
				return value

		return False

	def make_request(self, url, params={}, method='GET', data=None, **kwargs):
		''' Helper for generating requests - can't be used in athentication.

		:param url: base url for request.
		:param params: additional parameters to be passed in GET string.
		'''

		params.setdefault('authToken', self.auth_token)
		params.setdefault('language', 'en')

		# Flatten 'fields'
		if type(params.get('fields')) is list:
			params['fields'] = ','.join(params['fields'])

		if data and params.get('gzip') == 'true':
			data = gzip_string(data)
		elif data and params.get('deflate') == 'true':
			data = zlib.compress(data)

		r = self.Requests.request(method, url, data=data, params=params, **kwargs)

		if r.status_code != requests.codes.ok:
			logging.debug('Endomondo returned failed status code. Code: %s, message: %s' % (r.status_code, r.text))

		r.raise_for_status()

		'''
		# Endomondo has an odd way of randomly compressing things
		# TODO: Implement gzip
		if params.get('compression') == 'deflate':
			try:
				text = zlib.decompress(r.content)
				r._content = text
			except zlib.error as e:
				logging.warning('Could not decompress endomondo returned data, even thought deflate was requested. Error: %s' % e)
		'''
		try:
			data = r.json()
			if data.has_key('error'):
				logging.warning('Error loading data from Endomondo. Type: %s', data['error'].get('type'))

				err_type = data['error'].get('type')
				if err_type == 'AUTH_FAILED':
					raise AuthenticationError('Authentication token was not valid.')

		except:
			'''pass'''

		return r

	def get_account_info(self, **kwargs):
		''' Return data about current account.
			:param fields: Properties to retrieve. Default is `hr_zones`,`emails`.
			:return: Json object. Default fields:
			>>> {"data":{
			>>> 	"hr_zones":{"max":202,"z1":131,"z4":174,"z5":188,"z2":145,"z3":159,"rest":60},
			>>>		"weight_kg":int(),
			>>>		"phone":str("+3585551234"),
			>>>		"sex":str(<GENDER_MALE|GENDER_FEMALE>),
			>>>		"sync_time":datetime(),
			>>>		"date_of_birth":datetime(),
			>>>		"emails":[{"id":int(),"email":str('email@example.com'),"verified":bool(),"primary":bool()}],
			>>>		"lounge_member":bool(),
			>>>		"favorite_sport":int(),
			>>>		"units":str(<UNITS_METRIC|UNITS_IMPERIAL>,
			>>>		"country":str("CC"),
			>>>		"id":int(),
			>>>		"time_zone":str("+02:00"),
			>>>		"first_name":str("name"),
			>>>		"middle_name":str("middle"),
			>>>		"last_name":str("lastname"),
			>>>		"favorite_sport2":int(),
			>>>		"weight_time":datetime(),
			>>>		"created_time":datetime(),
			>>>		"height_cm":int()
			>>> }}
		'''

		kwargs.setdefault('fields', ['hr_zones','emails'])

		# App uses compressions for both ways, we don't handle that yet.
		#kwargs.setdefault('compression', 'deflate')
		kwargs.setdefault('deflate', 'true')

		r = self.make_request(URL_ACCOUNT_GET, params=kwargs)

		data = r.json()

		# Convert into datetime objects
		date_of_birth 	= data['data'].get('date_of_birth')
		sync_time		= data['data'].get('sync_time')
		weight_time		= data['data'].get('weight_time')

		if date_of_birth:
			data['data']['date_of_birth'] = str_to_datetime(date_of_birth)
		if sync_time:
			data['data']['sync_time'] = str_to_datetime(sync_time)
		if weight_time:
			data['data']['weight_time'] = str_to_datetime(weight_time)

		return data

	def post_account_info(self, account_info={}, **kwargs):
		''' Save user info.

			:param account_info: Dict of propeties to post. Known are:
			>>> {
			>>> 	"weight_kg":int(),
			>>> 	"first_name":str("name"),
			>>>		"sex":<GENDER_MALE|GENDER_FEMALE>,
			>>>		"middle_name":str("Middlename"),
			>>>		"last_name":str("Familyname"),
			>>>		"date_of_birth":datetime(),
			>>>		"height_cm":int(),
			>>>		"units":<UNITS_IMPERIAL|UNITS_METRIC>
			>>>	}
		'''

		# Endomondo App uses deflate, but at current time it's not implemented.
		#kwargs.setdefault('compression', 'deflate')
		kwargs.setdefault('deflate', 'true')


		if account_info.has_key('date_of_birth'):
			account_info['date_of_birth'] = datetime_to_str(account_info.get('date_of_birth'))

		data = json.dumps(account_info)

		r = self.make_request(URL_ACCOUNT_POST, params=kwargs, method='POST', data=data)
		return r.json()

	def get_workouts(self, before=None, **kwargs):
		''' Return list of workouts
			:param before: Optional datetime object or iso format date string (%Y-%m-%d %H:%M:%S UTC)
			:param maxResults: Optional Maximum number of workouts to be returned. Default is 20
			:param deflate: Optional true or false. Default is false, whereas endomondo app default is true. Untested.
			:param fields: Optional Comma separated list for endomondo properties to return. Default is: device,simple,basic,lcp_count
		'''

		kwargs.setdefault('maxResults', 20)
		# Default fields used by Endomondo 10.1 App
		kwargs.setdefault('fields', ['device', 'simple', 'basic', 'lcp_count'])

		# Flatten 'before'
		if before != None:
			if isinstance(before, datetime):
				kwargs['before'] = datetime_to_str(before)
			elif type(before) is str:
				kwargs['before'] = before
			else:
				raise ValueError("Param 'before' needs to be datetime object or iso formatted string.")

		if kwargs.get('deflate') == 'true':
			kwargs.setdefault('compression', 'deflate')

		r = self.make_request(URL_WORKOUTS, kwargs)

		workouts = []

		for entry in r.json().get('data', []):
			workout = self.build_workout(entry)
			workouts.append(workout)
			#print '[{id}] {start_time}: {name}'.format(entry)

		return workouts

	def get_workout(self, workout, **kwargs):
		''' Retrieve workout.
			:param workout: Workout ID, or ``Workout`` object to retrieve
			:param fields: Optional list of endomondo properties to request
		'''

		# Default fields used by Endomondo 10.1 App
		kwargs.setdefault('fields', [
			'device', 'simple','basic', 'motivation', 'interval',
			'hr_zones', 'weather', 'polyline_encoded_small', 'points',
			'lcp_count', 'tagged_users', 'pictures', 'feed'
		])

		if isinstance(workout, Workout):
			kwargs.setdefault('workoutId', workout.id)
		else:
			kwargs.setdefault('workoutId', int(workout))

		r = self.make_request(URL_WORKOUT_GET, kwargs)
		data = r.json()

		if data.has_key('error'):
			err_type = data['error'].get('type')
			if err_type == 'NOT_FOUND':
				raise NotFoundException('Item ``%s`` was not found in Endomondo.' % kwargs['workoutId'])
			else:
				raise EndomondoException('Error while loading data from Endomondo: %s' % err_type)

		workout = self.build_workout(data)
		return workout

	def build_workout(self, properties):
		''' Helper to build ``Workout`` model from request response.'''
		workout = Workout(properties)
		return workout

	def post_workout(self, workout, properties={}):
		''' Post workout in endomondo.

			At most basic, it should look like: 
            [workoutId] => -8848933288523797092
            [sport] => 46
            [duration] => 180
            [gzip] => true
            [audioMessage] => true
            [goalType] => BASIC
            [extendedResponse] => true
            [calories] => 18
            [hydration] => 0.012676

			:param workout: Workout object
			:param properties: Additional properties.
		'''

		properties.setdefault('audioMessage', 'true')
		properties.setdefault('goalType', 'BASIC')
		properties.setdefault('extendedResponse', 'true')

		# A "Bug" in endomondo infrastructure; If gzip is not defined, Endomondo
		# will complain about missing TrackPoints (not directly related to ``Workout.TrackPoint``)
		properties.setdefault('gzip', 'true')

		if not workout.device['workout_id']:
			workout.device['workout_id'] = random.randint(-9999999999999999999, 9999999999999999999)

		if workout.id:
			properties.setdefault('workoutId', workout.id)
		else:
			properties.setdefault('workoutId', workout.device['workout_id'])
		
		properties.setdefault('sport', workout.sport)
		properties.setdefault('calories', workout.calories)
		properties.setdefault('duration', workout.duration)
		properties.setdefault('hydration', workout.hydration)
		properties.setdefault('heartRateAvg', workout.heart_rate_avg)

		# Create pseudo point, if none exists
		if len(workout.points) == 0:
			point = TrackPoint({
				'time':	workout.start_time,
				'dist':	workout.distance,
				'inst': '3'
			})
			workout.addPoint(point)

		# App posts only 100 items, so multiple submissions might be needed.
		for chunk in chunks(workout.points,100):
			
			data = '\n'.join([self.flatten_trackpoint(i) for i in chunk])
			data = data+"\n"

			r = self.make_request(URL_TRACK, params=properties, method='POST', data=data)

			lines = r.text.split("\n")
			if lines[0] != 'OK':
				raise EndomondoException('Could not post track. Error ``%s``. Data may be partially uploaded' % lines[0])

			workout.id = int(lines[1].split('=')[1])

		logging.debug("Saved workout ID: %s" % workout.id)

		return workout

	def flatten_trackpoint(self, track_point):
		''' Convert ``TrackPoint`` into Endomondo textual presentation
			:param track_point: ``TrackPoint``.
		'''

		data = {
			'time':		datetime_to_str(track_point.time),
			'lng':		track_point.lng,
			'lat':		track_point.lat,
			'dist':		round(track_point.dist,2),
			'speed':	track_point.speed,
			'alt':		track_point.alt,
			'hr':		track_point.hr,
			'inst':		track_point.inst
		}

		text = u'{time};{inst};{lat};{lng};{dist};{speed};{alt};{hr};'.format(**data)
		return text

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
'''
Exceptions
'''

class EndomondoException(RuntimeError):
	''' Base class for Endomondo API related errors '''

class NotFoundException(EndomondoException):
	''' Requested item was not found in Endomondo database '''

class AuthenticationError(ValueError):
	''' Could not authenticate into Endomondo '''

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from datetime import datetime, tzinfo
import gzip, StringIO

def str_to_datetime(date):
	''' Convert string presentation into datetime object.
	'''
	return datetime.strptime(date, "%Y-%m-%d %H:%M:%S %Z")

def datetime_to_str(date):
	''' Convert datetime object into string presentation
		TODO: Convert local timezone to UTC.
	'''
	if type(date) == str:
		return date

	if date.tzinfo != None:
		date = date.astimezone(tzinfo('UTC'))
	text = date.strftime('%Y-%m-%d %H:%M:%S UTC')
	return text

def chunks(l, n):
	""" Yield successive n-sized chunks from l.
		From https://stackoverflow.com/a/312464
	"""
	for i in xrange(0, len(l), n):
		yield l[i:i+n]

def gzip_string(data):
	''' Android/Java compatible gziping.
		Sucks ass - pythons zlib that is. In PHP one can do same by gzdeflate()
	'''

	stringio = StringIO.StringIO()
	gfp = gzip.GzipFile(fileobj=stringio, mode='w')
	gfp.write(data)
	gfp.close()

	return stringio.getvalue()

########NEW FILE########
__FILENAME__ = workout
# -*- coding: utf-8 -*-

from .utils import str_to_datetime

from datetime import datetime
import logging

PRIVACY_PUBLIC	= 0
PRIVACY_FRIENDS	= 1
PRIVACY_PRIVATE	= 2

sports = {
	0:	'Running',
	1:	'Cycling, transport',
	2:	'Cycling, sport',
	3:	'Mountain biking',
	4:	'Skating',
	5:	'Roller skiing',
	6:	'Skiing, cross country',
	7:	'Skiing, downhill',
	8:	'Snowboarding',
	9:	'Kayaking',
	10:	'Kite surfing',
	11:	'Rowing',
	12:	'Sailing',
	13:	'Windsurfing',
	14:	'Fitness walking',
	15:	'Golfing',
	16:	'Hiking',
	17:	'Orienteering',
	18:	'Walking',
	19:	'Riding',
	20:	'Swimming',
	21:	'Indoor cycling',
	22:	'Other',
	23:	'Aerobics',
	24:	'Badminton',
	25:	'Baseball',
	26:	'Basketball',
	27:	'Boxing',
	28:	'Climbing stairs',
	29:	'Cricket',
	30:	'Elliptical training',
	31:	'Dancing',
	32:	'Fencing',
	33:	'Football, American',
	34:	'Football, rugby',
	35:	'Football, soccer',
	36:	'Handball',
	37:	'Hockey',
	38:	'Pilates',
	39:	'Polo',
	40:	'Scuba diving',
	41:	'Squash',
	42:	'Table tennis',
	43:	'Tennis',
	44:	'Volleyball, beach',
	45:	'Volleyball, indoor',
	46:	'Weight training',
	47:	'Yoga',
	48:	'Martial arts',
	49:	'Gymnastics',
	50:	'Step counter',
	87:	'Circuit Training',
	88:	'Treadmill running',
	89:	'Skateboarding',
	90:	'Surfing',
	91:	'Snowshoeing',
	92:	'Wheelchair',
	93:	'Climbing',
	94:	'Treadmill walking'
}

class Workout(object):

	''' Workout object.
		:param id: Workout key.
		:param name: Optional User provided name.
		:param heart_rate_avg: Average heart rate.
		:param heart_rate_max: Maximum heart rate.
		:param owner_id: Workout creator ID.
		:param privacy_workout: Workout privacy. See: ``PRIVACY_PUBLIC``, ``PRIVACY_FRIENDS``, and ``PRIVACY_PRIVATE``
		:param privacy_map: Workout track privacy. See: ``PRIVACY_PUBLIC``, ``PRIVACY_FRIENDS``, and ``PRIVACY_PRIVATE``
		:param distance: Traveled distance.
		:param lcp_count: Social media count crap.
		:param calories: Estimate of burned calories.
		:param weather: Weather types follow accuweather types.
		:param feed: Endomondos' own social media crap.
		:param speed_avg: Average speed.
		:param speed_max: Maximum achieved speed.
		:param sport: Sport type. See: ``sports``
		:param device: Devide understanding of workout. When new workout is created, app creates own ID for it for what it then tries to request
	'''

	id 				= None

	name			= ''

	heart_rate_avg	= None
	heart_rate_max	= None

	owner_id		= 0

	privacy_workout	= PRIVACY_PRIVATE
	privacy_map		= PRIVACY_PRIVATE

	distance 		= 0.0
	calories		= None

	message			= ''
	lcp_count		= {
		'peptalks':	0,
		'likes':	0,
		'comments':	0
	}

	weather			= {
		'weather_type': 0
	}

	feed			= {
		'story': ''
	}

	speed_avg		= 0.0
	speed_max		= 0

	sport			= 0

	descent			= 0.0
	ascent			= 0.0
	altitude_min	= 0.0
	altitude_max	= 0.0

	hydration		= None
	burgers_burned	= 0

	steps			= 0
	cadence_max		= 0

	device			= {
		'workout_id':	0
	}

	_points = []

	_start_time		= None
	_duration		= None

	_live			= False
	''' Stuff not implemented
	polyline_encoded_small = ""
	'''

	def __init__(self, properties={}):

		#super(Workout, self).__init__()

		properties.setdefault('start_time', datetime.utcnow())

		if properties.has_key('sport'):
			properties.setdefault('name', sports.get(properties['sport']))

		for key in properties:
			#if key != "points":
			logging.debug("setting property: %s = %s" % (key,properties[key]))
			setattr(self, key, properties[key])

	def addPoint(self, point):
		self._points.append(point)

	@property
	def duration(self):
		''' Return excercise duration. Calculate from points, if missing.
		'''
		if self._duration:
			return self._duration

		self._duration = 0

		youngest = None

		for point in self.points:
			if youngest:
				youngest = max(point.time, youngest)
			else:
				youngest = point.time

		start_time = self.start_time
		if youngest and start_time < youngest:
			time_diff = youngest - start_time
			self.duration = time_diff.total_seconds()

		return self._duration

	@duration.setter
	def duration(self, value):
		self._duration = int(value)

	@property
	def start_time(self):
		if not self._start_time:
			oldest = datetime.utcnow()
			for point in self.points:
				oldest = min(point.time, oldest)
			self.start_time = oldest

		return self._start_time

	@start_time.setter
	def start_time(self, value):
		if isinstance(value, datetime):
			self._start_time = value
		else:
			self._start_time = str_to_datetime(value)

		return self._start_time

	@property
	def points(self):
		return self._points

	@points.setter
	def points(self, points):
		for point in points:
			self.addPoint(TrackPoint(point))

	@property
	def live(self):
		return self._live

	@live.setter
	def live(self, value):
		self._live = bool(value)
		return self._live
	

class TrackPoint(object):

	''' Track measurement point.
		:param hr:	Heart rate.
		:param time: Measurement time
		:param speed: Current speed
		:param alt: Altitude
		:param lng: Longitude
		:param lat: Latitude
		:param dist: Distance from start
		:param inst: Don't know.
	'''

	hr		= ''
	_time	= ''
	speed	= ''
	alt		= ''
	lng		= ''
	lat		= ''
	dist	= ''
	inst	= ''

	def __init__(self, properties):
		properties.setdefault('time', datetime.utcnow())
		for key in properties:
			setattr(self, key, properties[key])

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, value):
		if isinstance(value, datetime):
			self._time = value
		else:
			self._time = str_to_datetime(value)

		return self._time



########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Commandline example for using Endomondo api
'''

import keyring

import sys
import getopt
import getpass

from datetime import datetime, timedelta

from endomondo import MobileApi, Workout, sports

from pprint import pprint

import logging, sys

if __name__ == '__main__':

	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

	try:
		opts, args = getopt.getopt(sys.argv[1:], '', ['email=', 'pw='])
	except getopt.error, msg:
		print 'python %s --email=[email] --pw=[password]' % sys.argv[0]
		sys.exit(2)

	email = ''
	pw = ''

	auth_token = ''

	endomondoapi = MobileApi()

	for option, arg in opts:
		if option == '--email':
			email = arg
		elif option == '--pw':
			pw = arg

	while not email:
		email = raw_input('Please enter your endomondo email: ')

	auth_token = None
	if not pw:
		auth_token = keyring.get_password("endomondo", email)

	pprint(endomondoapi.device_info)

	while not auth_token:
		while not pw:
			print "No authentication token, using password authentication."
			pw = getpass.getpass()
			if not pw:
				print "Password can't be empty"

		try:
			auth_token = endomondoapi.request_auth_token(email=email, password=pw)
		except:
			pass

		if not auth_token:
			print "Did not receive valid authentication token."
			pw = ''
		else:
			keyring.set_password("endomondo", email, auth_token)

	endomondoapi.set_auth_token(auth_token)

	##
	## * Retrieve user profile info
	##
	user_data = endomondoapi.get_account_info()['data']
	print "Hello {first_name} {last_name}".format(**user_data)

	##
	## * Retrieve last workouts.
	##
	print "Your last 5 workouts:"
	for workout in endomondoapi.get_workouts( maxResults=5 ):
		print "[%s] %s at %s" % (workout.id, workout.name, workout.start_time)

	##
	## * Create new workout.
	##

	workout = Workout()

	workout_type = False
	while workout_type == False:
		# Ask for a workout type
		workout_type = raw_input('Workout type (p to print) [0]:')
		if workout_type == '':
			workout_type = '0'

		if workout_type == 'p':	
			for i in sports:
				print "%s:\t%s" % (i, sports[i])
			workout_type = False
		elif not workout_type.isdigit() or not sports.has_key(int(workout_type)):
			print "Key not found"
			workout_type = False
		else:
			workout.sport = int(workout_type)


	workout.name = raw_input('Workout name [%s]: ' % sports[workout.sport])
	while not workout.duration:
		duration = raw_input('Workout duration in seconds [300]: ')
		if duration is '':
			print "Using 5 minutes as duration"
			duration = 300
	
		elif not duration.isdigit():
			print "Please insert digit for duration"
			continue
	
		workout.duration = int(duration)
		workout.start_time = datetime.utcnow() - timedelta(seconds=workout.duration)

		workout.distance = workout.duration*0.0027777778
		# Calories is calculated on server side too.
		#workout.calories = int(workout.duration*0.26666667)

	#workout = endomondoapi.get_workout(w_id)


########NEW FILE########
