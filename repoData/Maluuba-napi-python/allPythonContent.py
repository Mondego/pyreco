__FILENAME__ = client
import datetime
import json
import logging

import requests

class NAPINormalizeType(object):
	"""
	The types of entities that the normalize endpoint can work with.
	"""
	Time, DateRange, TimeRange = ('time', 'daterange', 'timerange')

class NAPIClient(object):
	"""
	A connection to the Maluuba NAPI.
	"""
	BASE_URL = 'http://napi.maluuba.com'
	VERSION  = 'v0'

	class InterpretResponse(object):
		"""
		A wrapper object for responses from the /interpret endpoint.
		"""
		def __init__(self, action, category, entities={}):
			self.action = action
			self.category = category
			self.entities = entities
			if 'dateRange' in self.entities:
				self.entities['dateRange'] = map(NAPIClient._parse_dateRange, self.entities['dateRange'])
			if 'timeRange' in self.entities:
				self.entities['timeRange'] = map(NAPIClient._parse_timeRange, self.entities['timeRange'])

	class NormalizeResponse(object):
		"""
		A wrapper object for the responses from the /normalize endpoint.
		"""
		def __init__(self, entities={}, context={}):
			self.entities = entities
			self.context = context
			if 'dateRange' in self.entities:
				self.entities['dateRange'] = map(NAPIClient._parse_dateRange, self.entities['dateRange'])
			if 'timeRange' in self.entities:
				self.entities['timeRange'] = map(NAPIClient._parse_timeRange, self.entities['timeRange'])


	@staticmethod
	def _parse_dateRange(dateRange):
		return {x: datetime.datetime.strptime(dateRange[x], '%Y-%m-%d').date() for x in dateRange}

	@staticmethod
	def _parse_timeRange(timeRange):
		return {x: datetime.datetime.strptime(timeRange[x], '%I:%M:%S%p').time() for x in timeRange}

	def __init__(self, api_key):
		self.api_key = api_key

	def __query(self, endpoint, **kwargs):
		kwargs['apikey'] = self.api_key
		r = requests.get(self.__generate_url(endpoint), params=kwargs)
		logging.debug("Called %s" % r.url)
		if r.status_code == 200:
			try:
				return json.loads(r.content)
			except Exception as e:
				logging.warn("Failed to parse response: %s" % r.content)
				pass
		else:
			logging.warn("Failure: %s" % r.status_code)

	def __generate_url(self, endpoint):
		return '%s/%s/%s' % (NAPIClient.BASE_URL, NAPIClient.VERSION, endpoint)

	def interpret(self, phrase):
		"""
		The primary endpoint of the NAPI. Classifies the given phrase, and extracts
		entities.
		"""
		return NAPIClient.InterpretResponse(**(self.__query('interpret', phrase=phrase)))

	def normalize(self, phrase, _type, timezone=''):
		"""
		Normalizes a time, date, or range.
		"""
		return NAPIClient.NormalizeResponse(**(self.__query('normalize', phrase=phrase, type=_type, timezone=timezone)))
########NEW FILE########
__FILENAME__ = test_client
import datetime
import unittest

from maluuba_napi import client

class TestSetup(object):
	"""Maluuba NAPI test cases."""

	def setUp(self):
		pass

class TestBaseMixin(object):
	client = client.NAPIClient('ENTER YOUR API KEY HERE')

	def checkPhrase(self, phrase, category, action, **kwargs):
		r = self.client.interpret(phrase)
		self.assertEquals(category, r.category)
		self.assertEquals(action, r.action)
		for key, value in kwargs.iteritems():
			self.assertTrue(key in r.entities)
			self.assertEquals(r.entities[key] if isinstance(value, (list, tuple)) else r.entities[key][0], value)

class ClientTestSuite(TestSetup, TestBaseMixin, unittest.TestCase):
	def test_business_search(self):
		self.checkPhrase('where can I buy a hammer', 'BUSINESS', 'BUSINESS_SEARCH', searchTerm='hammer')
		self.checkPhrase('i am hungry', 'BUSINESS', 'BUSINESS_SEARCH', searchTerm='hungry')
		self.checkPhrase('i want some pizza', 'BUSINESS', 'BUSINESS_SEARCH', searchTerm='pizza')

	def test_business_reservation(self):
		self.checkPhrase('book a table for 2 at an italian restaurant nearby', 'BUSINESS', 'BUSINESS_RESERVATION', numPeople='2', searchTerm='italian')
		self.checkPhrase('reserve a room at a hotel', 'BUSINESS', 'BUSINESS_RESERVATION', searchTerm='hotel')

	def test_call_dial(self):
		self.checkPhrase('call josh', 'CALL', 'CALL_DIAL', contacts=[{'name': 'josh'}, {'organization': 'josh'}])
		self.checkPhrase('dial pizza hut', 'CALL', 'CALL_DIAL', contacts=[{'name': 'pizza hut'}, {'organization': 'pizza hut'}])

	def test_call_check_missed(self):
		self.checkPhrase('did i miss any calls', 'CALL', 'CALL_CHECK_MISSED', )

	def test_call_respond_missed(self):
		self.checkPhrase('respond to that missed call', 'CALL', 'CALL_RESPOND_MISSED')

	def test_call_accept_incoming(self):
		self.checkPhrase('accept this call', 'CALL', 'CALL_ACCEPT_INCOMING')

	def test_contact_add(self):
		self.checkPhrase('add josh 5551234', 'CONTACT', 'CONTACT_ADD', contactFieldValue='5551234', contacts={'name': 'josh'})

	def test_contact_search(self):
		self.checkPhrase('what is josh\'s phone number', 'CONTACT', 'CONTACT_SEARCH', contactField='phone number', contacts={'name': 'josh'})
		self.checkPhrase('show me adrian\'s information', 'CONTACT', 'CONTACT_SEARCH', contacts={'name': 'adrian'})

	def test_contact_set_alias(self):
		self.checkPhrase('elizabeth is my mom', 'CONTACT', 'CONTACT_SET_ALIAS', contacts=[{'name': 'elizabeth'}, {'alias': 'MOTHER'}])

	def test_knowledge(self):
		self.checkPhrase('who is Barack Obama', 'KNOWLEDGE', 'KNOWLEDGE_SEARCH')
		self.checkPhrase('who is the president', 'KNOWLEDGE', 'KNOWLEDGE_SEARCH')
		self.checkPhrase('what is two plus two', 'KNOWLEDGE', 'KNOWLEDGE_SEARCH')
		self.checkPhrase('what is the tallest mountain', 'KNOWLEDGE', 'KNOWLEDGE_SEARCH')

	def test_entertainment_movie(self):
		self.checkPhrase('I want to see a funny movie', 'ENTERTAINMENT', 'ENTERTAINMENT_MOVIE', genre='comedy')
		self.checkPhrase('I want to see skyfall', 'ENTERTAINMENT', 'ENTERTAINMENT_MOVIE', title='skyfall')

	def test_entertainment_event(self):
		self.checkPhrase('when do the leafs play', 'ENTERTAINMENT', 'ENTERTAINMENT_EVENT', event='leafs')
		self.checkPhrase('I want to see justin bieber', 'ENTERTAINMENT', 'ENTERTAINMENT_EVENT', event='justin bieber')

	def test_entertainment_ambiguous(self):
		self.checkPhrase('what\'s fun to do on the weekend', 'ENTERTAINMENT', 'ENTERTAINMENT_AMBIGUOUS')

	def test_email_send(self):
		self.checkPhrase('email adrian about the api', 'EMAIL', 'EMAIL_SEND', subject='Api', contacts={'name': 'adrian'})

	def test_email_display(self):
		self.checkPhrase('show me emails from josh', 'EMAIL', 'EMAIL_DISPLAY', contacts={'name': 'josh'})

	def test_help_help(self):
		self.checkPhrase('help', 'HELP', 'HELP_HELP')
		self.checkPhrase('what can you do', 'HELP', 'HELP_HELP')

	def test_travel_flight(self):
		self.checkPhrase('i would like a first class ticket to new york leaving from toronto on the day before christmas returning a week after christmas', 'TRAVEL', 'TRAVEL_FLIGHT')

	def test_music_play(self):
		self.checkPhrase('play the song firework', 'MUSIC', 'MUSIC_PLAY', title='firework')

	def test_music_pause(self):
		self.checkPhrase('please pause the music', 'MUSIC', 'MUSIC_PAUSE')

	def test_calendar_create_event(self):
		self.checkPhrase('Set up a meeting from 8 to 10', 'CALENDAR', 'CALENDAR_CREATE_EVENT', title='meeting')

	def test_calendar_search(self):
		self.checkPhrase('what meetings do I have on Friday', 'CALENDAR', 'CALENDAR_SEARCH', title='meetings')

	def test_calendar_remove_event(self):
		self.checkPhrase('Cancel my next meeting', 'CALENDAR', 'CALENDAR_REMOVE_EVENT', title='meeting')

	def test_calendar_modify_event(self):
		self.checkPhrase('Move my 5 o\'clock to 7', 'CALENDAR', 'CALENDAR_MODIFY_EVENT')

	def test_calendar_availability(self):
		self.checkPhrase('When am I available', 'CALENDAR', 'CALENDAR_AVAILABILITY')

	def test_weather_status(self):
		self.checkPhrase('What is the weather outside?', 'WEATHER', 'WEATHER_STATUS')

	def test_weather_details(self):
		self.checkPhrase('What is the wind speed?', 'WEATHER', 'WEATHER_DETAILS')

	def test_weather_sunset(self):
		self.checkPhrase('When is the sunset?', 'WEATHER', 'WEATHER_SUNSET')

	def test_weather_sunrise(self):
		self.checkPhrase('When is sunrise for Friday?', 'WEATHER', 'WEATHER_SUNRISE')

	def test_reminder_set(self):
		self.checkPhrase('Remind me to put out the garbage tonight', 'REMINDER', 'REMINDER_SET', message='put out the garbage', time='06:00:00PM')

	def test_reminder_search(self):
		self.checkPhrase('Find me reminders for this week', 'REMINDER', 'REMINDER_SEARCH')

	def test_alarm_set(self):
		self.checkPhrase('set an alarm for five thirty', 'ALARM', 'ALARM_SET', )

	def test_alarm_set_recurring(self):
		self.checkPhrase('Set an alarm at five thirty every morning', 'ALARM', 'ALARM_SET_RECURRING')

	def test_alarm_modify(self):
		self.checkPhrase('Change my morning alarms from 5 to 7', 'ALARM', 'ALARM_MODIFY')

	def test_alarm_cancel(self):
		self.checkPhrase('Cancel my alarm at 6 tonight', 'ALARM', 'ALARM_CANCEL')

	def test_alarm_cancel_all_alarms(self):
		self.checkPhrase('Remove all my alarms', 'ALARM', 'ALARM_CANCEL_ALL_ALARMS')

	def test_alarm_search(self):
		self.checkPhrase('Find my alarms', 'ALARM', 'ALARM_SEARCH')

	def test_timer_start(self):
		self.checkPhrase('Set a 30 minute timer', 'TIMER', 'TIMER_START')

	def test_timer_display(self):
		self.checkPhrase('show my timer', 'TIMER', 'TIMER_DISPLAY')

	def test_timer_cancel(self):
		self.checkPhrase('cancel the timer', 'TIMER', 'TIMER_CANCEL')

	def test_timer_pause(self):
		self.checkPhrase('pause timer', 'TIMER', 'TIMER_PAUSE')

	def test_stopwatch_start(self):
		self.checkPhrase('start a stopwatch', 'STOPWATCH', 'STOPWATCH_START')

	def test_stopwatch_stop(self):
		self.checkPhrase('stop a stopwatch', 'STOPWATCH', 'STOPWATCH_STOP')

	def test_stopwatch_display(self):
		self.checkPhrase('display the stopwatch', 'STOPWATCH', 'STOPWATCH_DISPLAY')

	def test_navigation_directions(self):
		self.checkPhrase('How do I get to the mall from my house', 'NAVIGATION', 'NAVIGATION_DIRECTIONS', departing='house', destination='mall')
		self.checkPhrase('how do I get to san francisco', 'NAVIGATION', 'NAVIGATION_DIRECTIONS', destination='san francisco')

	def test_navigation_where_am_i(self):
		self.checkPhrase('Show my current location', 'NAVIGATION', 'NAVIGATION_WHERE_AM_I')

	def test_transit_next_bus(self):
		self.checkPhrase('When will the next bus come to the university', 'TRANSIT', 'TRANSIT_NEXT_BUS', departing='university', transitType='bus')

	def test_transit_nearby_stops(self):
		self.checkPhrase('bus stops near the mall', 'TRANSIT', 'TRANSIT_NEARBY_STOPS', departing='mall', transitType='bus', destination='mall')

	def test_transit_schedule(self):
		self.checkPhrase('What is the schedule for the green route tomorrow', 'TRANSIT', 'TRANSIT_SCHEDULE', route='green')

	def test_search_amazon(self):
		self.checkPhrase('i want to buy a book on amazon', 'SEARCH', 'SEARCH_AMAZON', searchTerm='book')
		self.checkPhrase('search amazon for electronics', 'SEARCH', 'SEARCH_AMAZON', searchTerm='electronics')

	def test_search_bing(self):
		self.checkPhrase('bing search ryan seacrest', 'SEARCH', 'SEARCH_BING', searchTerm='ryan seacrest')

	def test_search_ebay(self):
		self.checkPhrase('search ebay for socks', 'SEARCH', 'SEARCH_EBAY', searchTerm='socks')

	def test_search_default(self):
		self.checkPhrase('search the web for cheese', 'SEARCH', 'SEARCH_DEFAULT', searchTerm='cheese')

	def test_search_google(self):
		self.checkPhrase('google search androids', 'SEARCH', 'SEARCH_GOOGLE', searchTerm='androids')

	def test_search_recipes(self):
		self.checkPhrase('how do i make butter chicken', 'SEARCH', 'SEARCH_RECIPES', searchTerm='butter chicken')

	def test_search_wikipedia(self):
		self.checkPhrase('search wikipedia for the romans', 'SEARCH', 'SEARCH_WIKIPEDIA', searchTerm='romans')

	def test_text_display(self):
		self.checkPhrase('show unread texts', 'TEXT', 'TEXT_DISPLAY')

	def test_text_send(self):
		self.checkPhrase('send a text to rob how is the law stuff', 'TEXT', 'TEXT_SEND', contacts={'name': 'rob'}, message='how is the law stuff')

	def test_social_facebook_send_message(self):
		self.checkPhrase('send a facebook message to zhiyuan hey g', 'SOCIAL', 'SOCIAL_FACEBOOK_SEND_MESSAGE')

	def test_social_facebook_show_newsfeed(self):
		self.checkPhrase('show me my facebook newsfeed', 'SOCIAL', 'SOCIAL_FACEBOOK_SHOW_NEWSFEED')

	def test_social_facebook_show_photos(self):
		self.checkPhrase('show me pictures of irene', 'SOCIAL', 'SOCIAL_FACEBOOK_SHOW_PHOTOS', contacts={'name': 'irene'})

	def test_social_facebook_show_wall(self):
		self.checkPhrase('take me to cynthia\'s facebook wall', 'SOCIAL', 'SOCIAL_FACEBOOK_SHOW_WALL', contacts={'name': 'cynthia'})

	def test_social_facebook_write_on_wall(self):
		self.checkPhrase('write on sam\'s wall good luck in korea', 'SOCIAL', 'SOCIAL_FACEBOOK_WRITE_ON_WALL', contacts={'name': 'sam'}, message='good luck in korea')

	def test_social_foursquare_check_in(self):
		self.checkPhrase('check me in at communitech', 'SOCIAL', 'SOCIAL_FOURSQUARE_CHECK_IN')

	def test_social_foursquare_show_checkins(self):
		self.checkPhrase('where have i checked in', 'SOCIAL', 'SOCIAL_FOURSQUARE_SHOW_CHECKINS')

	def test_social_twitter_show_follower(self):
		self.checkPhrase('show my twitter timeline', 'SOCIAL', 'SOCIAL_TWITTER_SHOW_FOLLOWER')

	def test_social_twitter_show_trending(self):
		self.checkPhrase('what is trending on twitter', 'SOCIAL', 'SOCIAL_TWITTER_SHOW_TRENDING')

	def test_social_twitter_tweet(self):
		self.checkPhrase('tweet i want a burrito', 'SOCIAL', 'SOCIAL_TWITTER_TWEET', message='i want a burrito')

	def test_sports_misc(self):
		self.checkPhrase('what was the score of the game last night', 'SPORTS', 'SPORTS_MISC')

	def test_application_launch(self):
		self.checkPhrase('launch angry birds', 'APPLICATION', 'APPLICATION_LAUNCH', appName='angry birds')

########NEW FILE########
