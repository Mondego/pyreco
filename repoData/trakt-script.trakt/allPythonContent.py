__FILENAME__ = default
# -*- coding: utf-8 -*-
#

import xbmcaddon
import utilities
from service import traktService

__addon__ = xbmcaddon.Addon('script.trakt')
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__ = __addon__.getAddonInfo('id')

utilities.Debug("Loading '%s' version '%s'" % (__addonid__, __addonversion__))
traktService().run()
utilities.Debug("'%s' shutting down." % __addonid__)

########NEW FILE########
__FILENAME__ = globals
# -*- coding: utf-8 -*-
#

traktapi = None

########NEW FILE########
__FILENAME__ = queue
# -*- coding: utf-8 -*-

import os
import sqlite3
import utilities as utils

try:
	from simplejson import loads, dumps
except ImportError:
	from json import loads, dumps
from time import sleep

try:
	from thread import get_ident
except ImportError:
	from dummy_thread import get_ident

import xbmc
import xbmcvfs
import xbmcaddon

__addon__ = xbmcaddon.Addon('script.trakt')

# code from http://flask.pocoo.org/snippets/88/ with some modifications
class SqliteQueue(object):

	_create = (
				'CREATE TABLE IF NOT EXISTS queue ' 
				'('
				'  id INTEGER PRIMARY KEY AUTOINCREMENT,'
				'  item BLOB'
				')'
				)
	_count = 'SELECT COUNT(*) FROM queue'
	_iterate = 'SELECT id, item FROM queue'
	_append = 'INSERT INTO queue (item) VALUES (?)'
	_write_lock = 'BEGIN IMMEDIATE'
	_get = (
			'SELECT id, item FROM queue '
			'ORDER BY id LIMIT 1'
			)
	_del = 'DELETE FROM queue WHERE id = ?'
	_peek = (
			'SELECT item FROM queue '
			'ORDER BY id LIMIT 1'
			)
	_purge = 'DELETE FROM queue'

	def __init__(self):
		self.path = xbmc.translatePath(__addon__.getAddonInfo("profile")).decode("utf-8")
		if not xbmcvfs.exists(self.path):
			utils.Debug("Making path structure: " + repr(self.path))
			xbmcvfs.mkdir(self.path)
		self.path = os.path.join(self.path, 'queue.db')
		self._connection_cache = {}
		with self._get_conn() as conn:
			conn.execute(self._create)

	def __len__(self):
		with self._get_conn() as conn:
			l = conn.execute(self._count).next()[0]
		return l

	def __iter__(self):
		with self._get_conn() as conn:
			for id, obj_buffer in conn.execute(self._iterate):
				yield loads(str(obj_buffer))

	def _get_conn(self):
		id = get_ident()
		if id not in self._connection_cache:
			self._connection_cache[id] = sqlite3.Connection(self.path, timeout=60)
		return self._connection_cache[id]

	def purge(self):
		with self._get_conn() as conn:
			conn.execute(self._purge)

	def append(self, obj):
		obj_buffer = dumps(obj)
		with self._get_conn() as conn:
			conn.execute(self._append, (obj_buffer,)) 

	def get(self, sleep_wait=True):
		keep_pooling = True
		wait = 0.1
		max_wait = 2
		tries = 0
		with self._get_conn() as conn:
			id = None
			while keep_pooling:
				conn.execute(self._write_lock)
				cursor = conn.execute(self._get)
				try:
					id, obj_buffer = cursor.next()
					keep_pooling = False
				except StopIteration:
					conn.commit() # unlock the database
					if not sleep_wait:
						keep_pooling = False
						continue
					tries += 1
					sleep(wait)
					wait = min(max_wait, tries/10 + wait)
			if id:
				conn.execute(self._del, (id,))
				return loads(str(obj_buffer))
		return None

	def peek(self):
		with self._get_conn() as conn:
			cursor = conn.execute(self._peek)
			try:
				return loads(str(cursor.next()[0]))
			except StopIteration:
				return None

########NEW FILE########
__FILENAME__ = rating
# -*- coding: utf-8 -*-
"""Module used to launch rating dialogues and send ratings to trakt"""

import xbmc
import xbmcaddon
import xbmcgui
import utilities as utils
import tagging
import globals

__addon__ = xbmcaddon.Addon("script.trakt")

def ratingCheck(media_type, summary_info, watched_time, total_time, playlist_length):
	"""Check if a video should be rated and if so launches the rating dialog"""
	utils.Debug("[Rating] Rating Check called for '%s'" % media_type);
	if not utils.getSettingAsBool("rate_%s" % media_type):
		utils.Debug("[Rating] '%s' is configured to not be rated." % media_type)
		return
	if summary_info is None:
		utils.Debug("[Rating] Summary information is empty, aborting.")
		return
	watched = (watched_time / total_time) * 100
	if watched >= utils.getSettingAsFloat("rate_min_view_time"):
		if (playlist_length <= 1) or utils.getSettingAsBool("rate_each_playlist_item"):
			rateMedia(media_type, summary_info)
		else:
			utils.Debug("[Rating] Rate each playlist item is disabled.")
	else:
		utils.Debug("[Rating] '%s' does not meet minimum view time for rating (watched: %0.2f%%, minimum: %0.2f%%)" % (media_type, watched, utils.getSettingAsFloat("rate_min_view_time")))

def rateMedia(media_type, summary_info, unrate=False, rating=None):
	"""Launches the rating dialog"""
	if not utils.isValidMediaType(media_type):
		return
	
	if utils.isEpisode(media_type):
		if 'rating' in summary_info['episode']:
			summary_info['rating'] = summary_info['episode']['rating']
		if 'rating_advanced' in summary_info['episode']:
			summary_info['rating_advanced'] = summary_info['episode']['rating_advanced']

	s = utils.getFormattedItemName(media_type, summary_info)

	if not globals.traktapi.settings:
		globals.traktapi.getAccountSettings()
	rating_type = globals.traktapi.settings['viewing']['ratings']['mode']

	if unrate:
		rating = None

		if rating_type == "simple":
			if not summary_info['rating'] == "false":
				rating = "unrate"
		else:
			if summary_info['rating_advanced'] > 0:
				rating = 0

		if not rating is None:
			utils.Debug("[Rating] '%s' is being unrated." % s)
			rateOnTrakt(rating, media_type, summary_info, unrate=True)
		else:
			utils.Debug("[Rating] '%s' has not been rated, so not unrating." % s)

		return

	rerate = utils.getSettingAsBool('rate_rerate')
	if not rating is None:
		if summary_info['rating_advanced'] == 0:
			utils.Debug("[Rating] Rating for '%s' is being set to '%d' manually." % (s, rating))
			rateOnTrakt(rating, media_type, summary_info)
		else:
			if rerate:
				if not summary_info['rating_advanced'] == rating:
					utils.Debug("[Rating] Rating for '%s' is being set to '%d' manually." % (s, rating))
					rateOnTrakt(rating, media_type, summary_info)
				else:
					utils.notification(utils.getString(1353), s)
					utils.Debug("[Rating] '%s' already has a rating of '%d'." % (s, rating))
			else:
				utils.notification(utils.getString(1351), s)
				utils.Debug("[Rating] '%s' is already rated." % s)
		return

	if summary_info['rating'] or summary_info['rating_advanced']:
		if not rerate:
			utils.Debug("[Rating] '%s' has already been rated." % s)
			utils.notification(utils.getString(1351), s)
			return
		else:
			utils.Debug("[Rating] '%s' is being re-rated." % s)
	
	xbmc.executebuiltin('Dialog.Close(all, true)')

	gui = RatingDialog(
		"RatingDialog.xml",
		__addon__.getAddonInfo('path'),
		media_type=media_type,
		media=summary_info,
		rating_type=rating_type,
		rerate=rerate
	)

	gui.doModal()
	if gui.rating:
		rating = gui.rating
		if rerate:
			rating = gui.rating
			
			if rating_type == "simple":
				if not summary_info['rating'] == "false" and rating == summary_info['rating']:
					rating = "unrate"
			else:
				if summary_info['rating_advanced'] > 0 and rating == summary_info['rating_advanced']:
					rating = 0

		if rating == 0 or rating == "unrate":
			rateOnTrakt(rating, gui.media_type, gui.media, unrate=True)
		else:
			rateOnTrakt(rating, gui.media_type, gui.media)
	else:
		utils.Debug("[Rating] Rating dialog was closed with no rating.")

	del gui

def rateOnTrakt(rating, media_type, media, unrate=False):
	utils.Debug("[Rating] Sending rating (%s) to trakt.tv" % rating)

	params = {}
	params['rating'] = rating

	if utils.isMovie(media_type):
		params['title'] = media['title']
		params['year'] = media['year']
		params['tmdb_id'] = media['tmdb_id']
		params['imdb_id'] = media['imdb_id']

		data = globals.traktapi.rateMovie(params)

	elif utils.isShow(media_type):
		params['title'] = media['title']
		params['year'] = media['year']
		params['tvdb_id'] = media['tvdb_id']
		params['imdb_id'] = media['imdb_id']

		data = globals.traktapi.rateShow(params)
	
	elif utils.isEpisode(media_type):
		params['title'] = media['show']['title']
		params['year'] = media['show']['year']
		params['season'] = media['episode']['season']
		params['episode'] = media['episode']['number']
		params['tvdb_id'] = media['show']['tvdb_id']
		params['imdb_id'] = media['show']['imdb_id']

		data = globals.traktapi.rateEpisode(params)

	else:
		return

	if data:
		s = utils.getFormattedItemName(media_type, media)
		if 'status' in data and data['status'] == "success":

			if tagging.isTaggingEnabled() and tagging.isRatingsEnabled():
				if utils.isMovie(media_type) or utils.isShow(media_type):

					id = media['xbmc_id']
					f = utils.getMovieDetailsFromXbmc if utils.isMovie(media_type) else utils.getShowDetailsFromXBMC
					result = f(id, ['tag'])
					
					if result:
						tags = result['tag']

						new_rating = rating
						if new_rating == "love":
							new_rating = 10
						elif new_rating == "hate":
							new_rating = 1

						new_rating_tag = tagging.ratingToTag(new_rating)
						if unrate:
							new_rating_tag = ""

						update = False
						if tagging.hasTraktRatingTag(tags):
							old_rating_tag = tagging.getTraktRatingTag(tags)
							if not old_rating_tag == new_rating_tag:
								tags.remove(old_rating_tag)
								update = True

						if not unrate and new_rating >= tagging.getMinRating():
							tags.append(new_rating_tag)
							update = True

						if update:
							tagging.xbmcSetTags(id, media_type, s, tags)

					else:
						utils.Debug("No data was returned from XBMC, aborting tag udpate.")

			if not unrate:
				utils.notification(utils.getString(1350), s)
			else:
				utils.notification(utils.getString(1352), s)
		elif 'status' in data and data['status'] == "failure":
			utils.notification(utils.getString(1354), s)
		else:
			# status not in data, different problem, do nothing for now
			pass

class RatingDialog(xbmcgui.WindowXMLDialog):
	buttons = {
		10030:	'love',
		10031:	'hate',
		11030:	1,
		11031:	2,
		11032:	3,
		11033:	4,
		11034:	5,
		11035:	6,
		11036:	7,
		11037:	8,
		11038:	9,
		11039:	10
	}

	focus_labels = {
		10030: 1314,
		10031: 1315,
		11030: 1315,
		11031: 1316,
		11032: 1317,
		11033: 1318,
		11034: 1319,
		11035: 1320,
		11036: 1321,
		11037: 1322,
		11038: 1323,
		11039: 1314
	}

	def __init__(self, xmlFile, resourcePath, forceFallback=False, media_type=None, media=None, rating_type=None, rerate=False):
		self.media_type = media_type
		self.media = media
		self.rating_type = rating_type
		self.rating = None
		self.rerate = rerate
		self.default_simple = utils.getSettingAsInt('rating_default_simple')
		self.default_advanced = utils.getSettingAsInt('rating_default_advanced')

	def onInit(self):
		self.getControl(10014).setVisible(self.rating_type == 'simple')
		self.getControl(10015).setVisible(self.rating_type == 'advanced')

		s = utils.getFormattedItemName(self.media_type, self.media, short=True)
		self.getControl(10012).setLabel(s)

		rateID = None
		if self.rating_type == 'simple':
			rateID = 10030 + self.default_simple
			if self.rerate:
				if self.media['rating'] == "hate":
					rateID = 10031
		else:
			rateID = 11029 + self.default_advanced
			if self.rerate and int(self.media['rating_advanced']) > 0:
				rateID = 11029 + int(self.media['rating_advanced'])
		self.setFocus(self.getControl(rateID))

	def onClick(self, controlID):
		if controlID in self.buttons:
			self.rating = self.buttons[controlID]
			self.close()

	def onFocus(self, controlID):
		if controlID in self.focus_labels:
			s = utils.getString(self.focus_labels[controlID])
			if self.rerate:
				if self.media['rating'] == self.buttons[controlID] or self.media['rating_advanced'] == self.buttons[controlID]:
					if utils.isMovie(self.media_type):
						s = utils.getString(1325)
					elif utils.isShow(self.media_type):
						s = utils.getString(1326)
					elif utils.isEpisode(self.media_type):
						s = utils.getString(1327)
					else:
						pass
			
			self.getControl(10013).setLabel(s)
		else:
			self.getControl(10013).setLabel('')

########NEW FILE########
__FILENAME__ = script
# -*- coding: utf-8 -*-

import utilities as utils
import xbmc
import sys
import queue
import tagging
import time
from traktContextMenu import traktContextMenu

try:
	import simplejson as json
except ImportError:
	import json

def getMediaType():
	
	if xbmc.getCondVisibility('Container.Content(tvshows)'):
		return "show"
	elif xbmc.getCondVisibility('Container.Content(seasons)'):
		return "season"
	elif xbmc.getCondVisibility('Container.Content(episodes)'):
		return "episode"
	elif xbmc.getCondVisibility('Container.Content(movies)'):
		return "movie"
	else:
		return None

def getArguments():
	data = None
	default_actions = {0: "sync", 1: "managelists"}
	default = utils.getSettingAsInt('default_action')
	if len(sys.argv) == 1:
		data = {'action': default_actions[default]}
	else:
		data = {}
		for item in sys.argv:
			values = item.split("=")
			if len(values) == 2:
				data[values[0].lower()] = values[1]
		data['action'] = data['action'].lower()

	return data

def Main():

	args = getArguments()
	data = {}

	if args['action'] == 'contextmenu':
		buttons = []
		media_type = getMediaType()

		if utils.getSettingAsBool('tagging_enable'):
			if utils.isMovie(media_type):
				buttons.append("itemlists")
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
				result = utils.getMovieDetailsFromXbmc(dbid, ['tag'])
				if tagging.hasTraktWatchlistTag(result['tag']):
					buttons.append("removefromlist")
				else:
					buttons.append("addtolist")
			elif utils.isShow(media_type):
				buttons.append("itemlists")
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
				result = utils.getShowDetailsFromXBMC(dbid, ['tag'])
				if tagging.hasTraktWatchlistTag(result['tag']):
					buttons.append("removefromlist")
				else:
					buttons.append("addtolist")

		if media_type in ['movie', 'show', 'episode']:
			buttons.append("rate")

		if media_type in ['movie', 'show', 'season', 'episode']:
			buttons.append("togglewatched")

		if utils.getSettingAsBool('tagging_enable'):
			buttons.append("managelists")
			buttons.append("updatetags")
		buttons.append("sync")

		contextMenu = traktContextMenu(media_type=media_type, buttons=buttons)
		contextMenu.doModal()
		_action = contextMenu.action
		del contextMenu

		if _action is None:
			return

		utils.Debug("'%s' selected from trakt.tv action menu" % _action)
		args['action'] = _action
		if _action in ['addtolist', 'removefromlist']:
			args['list'] = "watchlist"

	if args['action'] == 'sync':
		data = {'action': 'manualSync'}
		data['silent'] = False
		if 'silent' in args:
			data['silent'] = (args['silent'].lower() == 'true')
		data['library'] = "all"
		if 'library' in args and args['library'] in ['episodes', 'movies']:
			data['library'] = args['library']

	elif args['action'] == 'loadsettings':
		data = {'action': 'loadsettings', 'force': True}
		utils.notification(utils.getString(1201), utils.getString(1111))

	elif args['action'] == 'settings':
		data = {'action': 'settings'}

	elif args['action'] in ['rate', 'unrate']:
		data = {}
		data['action'] = args['action']
		media_type = None
		if 'media_type' in args and 'dbid' in args:
			media_type = args['media_type']
			try:
				data['dbid'] = int(args['dbid'])
			except ValueError:
				utils.Debug("Manual %s triggered for library item, but DBID is invalid." % args['action'])
				return
		elif 'media_type' in args and 'remoteid' in args:
			media_type = args['media_type']
			data['remoteid'] = args['remoteid']
			if 'season' in args:
				if not 'episode' in args:
					utils.Debug("Manual %s triggered for non-library episode, but missing episode number." % args['action'])
					return
				try:
					data['season'] = int(args['season'])
					data['episode'] = int(args['episode'])
				except ValueError:
					utilities.Debug("Error parsing season or episode for manual %s" % args['action'])
					return
		else:
			media_type = getMediaType()
			if not utils.isValidMediaType(media_type):
				utils.Debug("Error, not in video library.")
				return
			data['dbid'] = int(xbmc.getInfoLabel('ListItem.DBID'))

		if media_type is None:
			utils.Debug("Manual %s triggered on an unsupported content container." % args['action'])
		elif utils.isValidMediaType(media_type):
			data['media_type'] = media_type
			if 'dbid' in data:
				utils.Debug("Manual %s of library '%s' with an ID of '%s'." % (args['action'], media_type, data['dbid']))
				if utils.isMovie(media_type):
					result = utils.getMovieDetailsFromXbmc(data['dbid'], ['imdbnumber', 'title', 'year'])
					if not result:
						utils.Debug("No data was returned from XBMC, aborting manual %s." % args['action'])
						return
					data['imdbnumber'] = result['imdbnumber']

				elif utils.isShow(media_type):
					result = utils.getShowDetailsFromXBMC(data['dbid'], ['imdbnumber', 'tag'])
					if not result:
						utils.Debug("No data was returned from XBMC, aborting manual %s." % args['action'])
						return
					data['imdbnumber'] = result['imdbnumber']
					data['tag'] = result['tag']

				elif utils.isEpisode(media_type):
					result = utils.getEpisodeDetailsFromXbmc(data['dbid'], ['showtitle', 'season', 'episode', 'tvshowid'])
					if not result:
						utils.Debug("No data was returned from XBMC, aborting manual %s." % args['action'])
						return
					data['tvdb_id'] = result['tvdb_id']
					data['season'] = result['season']
					data['episode'] = result['episode']

			else:
				if 'season' in data:
					utils.Debug("Manual %s of non-library '%s' S%02dE%02d, with an ID of '%s'." % (args['action'], media_type, data['season'], data['episode'], data['remoteid']))
					data['tvdb_id'] = data['remoteid']
				else:
					utils.Debug("Manual %s of non-library '%s' with an ID of '%s'." % (args['action'], media_type, data['remoteid']))
					data['imdbnumber'] = data['remoteid']

			if args['action'] == 'rate' and 'rating' in args:
				if args['rating'] in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
					data['rating'] = int(args['rating'])

			data = {'action': 'manualRating', 'ratingData': data}

		else:
			utils.Debug("Manual %s of '%s' is unsupported." % (args['action'], media_type))

	elif args['action'] == 'togglewatched':
		media_type = getMediaType()
		if media_type in ['movie', 'show', 'season', 'episode']:
			data = {}
			data['media_type'] = media_type
			if utils.isMovie(media_type):
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
				result = utils.getMovieDetailsFromXbmc(dbid, ['imdbnumber', 'title', 'year', 'playcount'])
				if result:
					if result['playcount'] == 0:
						data['id'] = result['imdbnumber']
					else:
						utils.Debug("Movie alread marked as watched in XBMC.")
				else:
					utils.Debug("Error getting movie details from XBMC.")
					return

			elif utils.isEpisode(media_type):
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
				result = utils.getEpisodeDetailsFromXbmc(dbid, ['showtitle', 'season', 'episode', 'tvshowid', 'playcount'])
				if result:
					if result['playcount'] == 0:
						data['id'] = result['tvdb_id']
						data['season'] = result['season']
						data['episode'] = result['episode']
					else:
						utils.Debug("Episode already marked as watched in XBMC.")
				else:
					utils.Debug("Error getting episode details from XBMC.")
					return

			elif utils.isSeason(media_type):
				showID = None
				showTitle = xbmc.getInfoLabel('ListItem.TVShowTitle')
				result = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'imdbnumber', 'year']}, 'id': 0})
				if result and 'tvshows' in result:
					for show in result['tvshows']:
						if show['title'] == showTitle:
							showID = show['tvshowid']
							data['id'] = show['imdbnumber']
							break
				else:
					utils.Debug("Error getting TV shows from XBMC.")
					return

				season = xbmc.getInfoLabel('ListItem.Season')
				if season == "":
					season = 0
				else:
					season = int(season)

				result = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': showID, 'season': season, 'properties': ['season', 'episode', 'playcount']}, 'id': 0})
				if result and 'episodes' in result:
					episodes = []
					for episode in result['episodes']:
						if episode['playcount'] == 0:
							episodes.append(episode['episode'])
					
					if len(episodes) == 0:
						utils.Debug("'%s - Season %d' is already marked as watched." % (showTitle, season))
						return

					data['season'] = season
					data['episodes'] = episodes
				else:
					utils.Debug("Error getting episodes from '%s' for Season %d" % (showTitle, season))
					return

			elif utils.isShow(media_type):
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
				result = utils.getShowDetailsFromXBMC(dbid, ['year', 'imdbnumber'])
				if not result:
					utils.Debug("Error getting show details from XBMC.")
					return
				showTitle = result['label']
				data['id'] = result['imdbnumber']
				result = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': dbid, 'properties': ['season', 'episode', 'playcount']}, 'id': 0})
				if result and 'episodes' in result:
					i = 0
					s = {}
					for e in result['episodes']:
						season = str(e['season'])
						if not season in s:
							s[season] = []
						if e['playcount'] == 0:
							s[season].append(e['episode'])
							i = i + 1

					if i == 0:
						utils.Debug("'%s' is already marked as watched." % showTitle)
						return

					data['seasons'] = dict((k, v) for k, v in s.iteritems() if v)
				else:
					utils.Debug("Error getting episode details for '%s' from XBMC." % showTitle)
					return

			if len(data) > 1:
				utils.Debug("Marking '%s' with the following data '%s' as watched on trakt.tv" % (media_type, str(data)))
				data['action'] = 'markWatched'

		# execute toggle watched action
		xbmc.executebuiltin("Action(ToggleWatched)")

	elif args['action'] == 'updatetags':
		data = {'action': 'updatetags'}

	elif args['action'] == 'managelists':
		data = {'action': 'managelists'}

	elif args['action'] == 'timertest':
		utils.Debug("Timing JSON requests.")
		import time
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params':{'tvshowid': 254, 'properties': ['tag']}, 'id': 1})
		#data = utils.getShowDetailsFromXBMC(254, ['tag', 'imdbnumber'])
		e = time.time() - t
		utils.Debug("VideoLibrary.GetTVShowDetails with tags: %0.3f seconds." % e)
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params':{'movieid': 634, 'properties': ['tag']}, 'id': 1})
		#data = utils.getMovieDetailsFromXbmc(634, ['tag', 'imdbnumber', 'title', 'year'])
		e = time.time() - t
		utils.Debug("VideoLibrary.GetMovieDetails with tags: %0.3f seconds." % e)

		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['tag', 'title', 'imdbnumber', 'year']}, 'id': 0})
		e = time.time() - t
		utils.Debug("VideoLibrary.GetTVShows with tags: %0.3f seconds, %d items at %0.5f seconds per item" % (e, len(data['tvshows']), e / len(data['tvshows'])))
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'id': 0, 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['tag', 'title', 'imdbnumber', 'year']}})
		e = time.time() - t
		utils.Debug("VideoLibrary.GetMovies with tags: %0.3f seconds, %d items at %0.5f seconds per item" % (e, len(data['movies']), e / len(data['movies'])))
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'imdbnumber', 'year']}, 'id': 0})
		e = time.time() - t
		utils.Debug("VideoLibrary.GetTVShows without tags: %0.3f seconds, %d items at %0.5f seconds per item" % (e, len(data['tvshows']), e / len(data['tvshows'])))
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'id': 0, 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['title', 'imdbnumber', 'year']}})
		e = time.time() - t
		utils.Debug("VideoLibrary.GetMovies without tags: %0.3f seconds, %d items at %0.5f seconds per item" % (e, len(data['movies']), e / len(data['movies'])))
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params':{'tvshowid': 254, 'properties': ['imdbnumber']}, 'id': 1})
		#data = utils.getShowDetailsFromXBMC(254, ['imdbnumber'])
		e = time.time() - t
		utils.Debug("VideoLibrary.GetTVShowDetails without tags: %0.3f seconds." % e)
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params':{'movieid': 634, 'properties': ['imdbnumber', 'title', 'year']}, 'id': 1})
		#data = utils.getMovieDetailsFromXbmc(634, ['imdbnumber', 'title', 'year'])
		e = time.time() - t
		utils.Debug("VideoLibrary.GetMovieDetails without tags: %0.3f seconds." % e)
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'imdbnumber', 'year']}, 'id': 0})
		data = data['tvshows']
		for item in data:
			item_data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params':{'tvshowid': item['tvshowid'], 'properties': ['tag']}, 'id': 1})
			item['tag'] = item_data['tvshowdetails']['tag']
		e = time.time() - t
		utils.Debug("VideoLibrary.GetTVShows with tags from loop: %0.3f seconds, %d items at %0.5f seconds per item" % (e, len(data), e / len(data)))
		
		t = time.time()
		data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['title', 'imdbnumber', 'year']}, 'id': 0})
		data = data['movies']
		for item in data:
			item_data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params':{'movieid': item['movieid'], 'properties': ['tag']}, 'id': 1})
			item['tag'] = item_data['moviedetails']['tag']
		e = time.time() - t
		utils.Debug("VideoLibrary.GetMovies with tags from: %0.3f seconds, %d items at %0.5f seconds per item." % (e, len(data), e / len(data)))

	elif args['action'] in ['itemlists', 'addtolist', 'removefromlist']:
		data = {}
		data['action'] = args['action']
		media_type = None
		dbid = None
		if 'media_type' in args and 'dbid' in args:
			media_type = args['media_type']
			try:
				dbid = int(args['dbid'])
			except ValueError:
				utils.Debug("'%s' triggered for library item, but DBID is invalid." % args['action'])
				return
		else:
			media_type = getMediaType()
			if not media_type in ['movie', 'show']:
				utils.Debug("Error, not in video library.")
				return
			try:
				dbid = int(xbmc.getInfoLabel('ListItem.DBID'))
			except ValueError:
				utils.Debug("'%s' triggered for library item, but there is a problem with ListItem.DBID." % args['action'])
				return
		
		if not media_type in ['movie', 'show']:
			utils.Debug("'%s' is not a valid media type for '%s'." % (media_type, args['action']))
			return

		if args['action'] in ['addtolist', 'removefromlist']:
			if 'list' in args:
				data['list'] = args['list']
			else:
				utils.Debug("'%s' requires a list parameter." % data['action'])

		data['type'] = media_type

		if utils.isMovie(media_type):
			result = utils.getMovieDetailsFromXbmc(dbid, ['imdbnumber', 'title', 'year', 'tag'])
			if not result:
				utils.Debug("Error getting movie details from XBMC.")
				return
			data['tag'] = result['tag']
			data['movieid'] = result['movieid']
			data['title'] = result['title']
			data['year'] = result['year']
			if result['imdbnumber'].startswith("tt"):
				data['imdb_id'] = result['imdbnumber']
			elif result['imdbnumber'].isdigit():
				data['tmdb_id'] = result['imdbnumber']
		
		elif utils.isShow(media_type):
			result = utils.getShowDetailsFromXBMC(dbid, ['imdbnumber', 'title', 'tag'])
			if not result:
				utils.Debug("Error getting show details from XBMC.")
				return
			data['tag'] = result['tag']
			data['tvshowid'] = result['tvshowid']
			data['title'] = result['title']
			if result['imdbnumber'].startswith("tt"):
				data['imdb_id'] = result['imdbnumber']
			elif result['imdbnumber'].isdigit():
				data['tvdb_id'] = result['imdbnumber']

	q = queue.SqliteQueue()
	if 'action' in data:
		utils.Debug("Queuing for dispatch: %s" % data)
		q.append(data)

if __name__ == '__main__':
	Main()
########NEW FILE########
__FILENAME__ = scrobbler
# -*- coding: utf-8 -*-
#

import xbmc
import time

import utilities
import tagging
from utilities import Debug
from rating import ratingCheck

class Scrobbler():

	traktapi = None
	isPlaying = False
	isPaused = False
	isMultiPartEpisode = False
	lastMPCheck = 0
	curMPEpisode = 0
	videoDuration = 1
	watchedTime = 0
	pausedAt = 0
	curVideo = None
	curVideoInfo = None
	playlistLength = 1
	playlistIndex = 0
	markedAsWatched = []
	traktSummaryInfo = None

	def __init__(self, api):
		self.traktapi = api

	def _currentEpisode(self, watchedPercent, episodeCount):
		split = (100 / episodeCount)
		for i in range(episodeCount - 1, 0, -1):
			if watchedPercent >= (i * split):
				return i
		return 0

	def update(self, forceCheck = False):
		if not xbmc.Player().isPlayingVideo():
			return

		if self.isPlaying:
			t = xbmc.Player().getTime()
			l = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
			if self.playlistIndex == l:
				self.watchedTime = t
			else:
				Debug("[Scrobbler] Current playlist item changed! Not updating time! (%d -> %d)" % (self.playlistIndex, l))

			if 'id' in self.curVideo and self.isMultiPartEpisode:
				# do transition check every minute
				if (time.time() > (self.lastMPCheck + 60)) or forceCheck:
					self.lastMPCheck = time.time()
					watchedPercent = (self.watchedTime / self.videoDuration) * 100
					epIndex = self._currentEpisode(watchedPercent, self.curVideo['multi_episode_count'])
					if self.curMPEpisode != epIndex:
						# current episode in multi-part episode has changed
						Debug("[Scrobbler] Attempting to scrobble episode part %d of %d." % (self.curMPEpisode + 1, self.curVideo['multi_episode_count']))

						# recalculate watchedPercent and duration for multi-part, and scrobble
						adjustedDuration = int(self.videoDuration / self.curVideo['multi_episode_count'])
						duration = adjustedDuration / 60
						watchedPercent = ((self.watchedTime - (adjustedDuration * self.curMPEpisode)) / adjustedDuration) * 100
						response = self.traktapi.scrobbleEpisode(self.curVideoInfo, duration, watchedPercent)
						if response != None:
							Debug("[Scrobbler] Scrobble response: %s" % str(response))

						# update current information
						self.curMPEpisode = epIndex
						self.curVideoInfo = utilities.getEpisodeDetailsFromXbmc(self.curVideo['multi_episode_data'][self.curMPEpisode], ['showtitle', 'season', 'episode', 'tvshowid', 'uniqueid'])

						if not forceCheck:
							self.watching()

	def playbackStarted(self, data):
		Debug("[Scrobbler] playbackStarted(data: %s)" % data)
		if not data:
			return
		self.curVideo = data
		self.curVideoInfo = None
		# {"jsonrpc":"2.0","method":"Player.OnPlay","params":{"data":{"item":{"type":"movie"},"player":{"playerid":1,"speed":1},"title":"Shooter","year":2007},"sender":"xbmc"}}
		# {"jsonrpc":"2.0","method":"Player.OnPlay","params":{"data":{"episode":3,"item":{"type":"episode"},"player":{"playerid":1,"speed":1},"season":4,"showtitle":"24","title":"9:00 A.M. - 10:00 A.M."},"sender":"xbmc"}}
		if 'type' in self.curVideo:
			Debug("[Scrobbler] Watching: %s" % self.curVideo['type'])
			if not xbmc.Player().isPlayingVideo():
				Debug("[Scrobbler] Suddenly stopped watching item")
				return
			xbmc.sleep(1000) # Wait for possible silent seek (caused by resuming)
			try:
				self.watchedTime = xbmc.Player().getTime()
				self.videoDuration = xbmc.Player().getTotalTime()
			except Exception, e:
				Debug("[Scrobbler] Suddenly stopped watching item: %s" % e.message)
				self.curVideo = None
				return

			if self.videoDuration == 0:
				if utilities.isMovie(self.curVideo['type']):
					self.videoDuration = 90
				elif utilities.isEpisode(self.curVideo['type']):
					self.videoDuration = 30
				else:
					self.videoDuration = 1

			self.playlistLength = len(xbmc.PlayList(xbmc.PLAYLIST_VIDEO))
			self.playlistIndex = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
			if (self.playlistLength == 0):
				Debug("[Scrobbler] Warning: Cant find playlist length, assuming that this item is by itself")
				self.playlistLength = 1

			self.traktSummaryInfo = None
			self.isMultiPartEpisode = False
			if utilities.isMovie(self.curVideo['type']):
				if 'id' in self.curVideo:
					self.curVideoInfo = utilities.getMovieDetailsFromXbmc(self.curVideo['id'], ['imdbnumber', 'title', 'year'])
					if utilities.getSettingAsBool('rate_movie'):
						# pre-get sumamry information, for faster rating dialog.
						Debug("[Scrobbler] Movie rating is enabled, pre-fetching summary information.")
						imdb_id = self.curVideoInfo['imdbnumber']
						if imdb_id.startswith("tt") or imdb_id.isdigit():
							self.traktSummaryInfo = self.traktapi.getMovieSummary(self.curVideoInfo['imdbnumber'])
							self.traktSummaryInfo['xbmc_id'] = self.curVideo['id']
						else:
							self.curVideoInfo['imdbnumber'] = None
							Debug("[Scrobbler] Can not get summary information for '%s (%d)' as is has no valid id, will retry during a watching call." % (self.curVideoInfo['title'], self.curVideoInfo['year']))
				elif 'title' in self.curVideo and 'year' in self.curVideo:
					self.curVideoInfo = {}
					self.curVideoInfo['imdbnumber'] = None
					self.curVideoInfo['title'] = self.curVideo['title']
					self.curVideoInfo['year'] = self.curVideo['year']

			elif utilities.isEpisode(self.curVideo['type']):
				if 'id' in self.curVideo:
					self.curVideoInfo = utilities.getEpisodeDetailsFromXbmc(self.curVideo['id'], ['showtitle', 'season', 'episode', 'tvshowid', 'uniqueid'])
					if not self.curVideoInfo: # getEpisodeDetailsFromXbmc was empty
						Debug("[Scrobbler] Episode details from XBMC was empty, ID (%d) seems invalid, aborting further scrobbling of this episode." % self.curVideo['id'])
						self.curVideo = None
						self.isPlaying = False
						self.watchedTime = 0
						return
					if utilities.getSettingAsBool('rate_episode'):
						# pre-get sumamry information, for faster rating dialog.
						Debug("[Scrobbler] Episode rating is enabled, pre-fetching summary information.")
						tvdb_id = self.curVideoInfo['tvdb_id']
						if tvdb_id.isdigit() or tvdb_id.startswith("tt"):
							self.traktSummaryInfo = self.traktapi.getEpisodeSummary(tvdb_id, self.curVideoInfo['season'], self.curVideoInfo['episode'])
						else:
							self.curVideoInfo['tvdb_id'] = None
							Debug("[Scrobbler] Can not get summary information for '%s - S%02dE%02d' as it has no valid id, will retry during a watching call." % (self.curVideoInfo['showtitle'], self.curVideoInfo['season'], self.curVideoInfo['episode']))
				elif 'showtitle' in self.curVideo and 'season' in self.curVideo and 'episode' in self.curVideo:
					self.curVideoInfo = {}
					self.curVideoInfo['tvdb_id'] = None
					self.curVideoInfo['year'] = None
					if 'year' in self.curVideo:
						self.curVideoInfo['year'] = self.curVideo['year']
					self.curVideoInfo['showtitle'] = self.curVideo['showtitle']
					self.curVideoInfo['season'] = self.curVideo['season']
					self.curVideoInfo['episode'] = self.curVideo['episode']

				if 'multi_episode_count' in self.curVideo:
					self.isMultiPartEpisode = True
					self.markedAsWatched = []
					episode_count = self.curVideo['multi_episode_count']
					for i in range(episode_count):
						self.markedAsWatched.append(False)

			self.isPlaying = True
			self.isPaused = False
			self.watching()

	def playbackResumed(self):
		if not self.isPlaying:
			return

		Debug("[Scrobbler] playbackResumed()")
		if self.isPaused:
			p = time.time() - self.pausedAt
			Debug("[Scrobbler] Resumed after: %s" % str(p))
			self.pausedAt = 0
			self.isPaused = False
			self.update(True)
			if utilities.getSettingAsBool('watching_call_on_resume'):
				self.watching()

	def playbackPaused(self):
		if not self.isPlaying:
			return

		Debug("[Scrobbler] playbackPaused()")
		self.update(True)
		Debug("[Scrobbler] Paused after: %s" % str(self.watchedTime))
		self.isPaused = True
		self.pausedAt = time.time()

	def playbackSeek(self):
		if not self.isPlaying:
			return

		Debug("[Scrobbler] playbackSeek()")
		self.update(True)
		if utilities.getSettingAsBool('watching_call_on_seek'):
			self.watching()

	def playbackEnded(self):
		if not self.isPlaying:
			return

		Debug("[Scrobbler] playbackEnded()")
		if self.curVideo == None:
			Debug("[Scrobbler] Warning: Playback ended but video forgotten.")
			return
		self.isPlaying = False
		self.markedAsWatched = []
		if self.watchedTime != 0:
			if 'type' in self.curVideo:
				ratingCheck(self.curVideo['type'], self.traktSummaryInfo, self.watchedTime, self.videoDuration, self.playlistLength)
				self.check()
			self.watchedTime = 0
			self.isMultiPartEpisode = False
		self.traktSummaryInfo = None
		self.curVideo = None
		self.playlistLength = 0
		self.playlistIndex = 0

	def watching(self):
		if not self.isPlaying:
			return

		if not self.curVideoInfo:
			return

		Debug("[Scrobbler] watching()")
		scrobbleMovieOption = utilities.getSettingAsBool('scrobble_movie')
		scrobbleEpisodeOption = utilities.getSettingAsBool('scrobble_episode')

		self.update(True)

		duration = self.videoDuration / 60
		watchedPercent = (self.watchedTime / self.videoDuration) * 100

		if utilities.isMovie(self.curVideo['type']) and scrobbleMovieOption:
			response = self.traktapi.watchingMovie(self.curVideoInfo, duration, watchedPercent)
			if response != None:
				if self.curVideoInfo['imdbnumber'] is None:
					if 'status' in response and response['status'] == "success":
						if 'movie' in response and 'imdb_id' in response['movie']:
							self.curVideoInfo['imdbnumber'] = response['movie']['imdb_id']
							if 'id' in self.curVideo and utilities.getSettingAsBool('update_imdb_id'):
								req = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : self.curVideoInfo['movieid'], "imdbnumber": self.curVideoInfo['imdbnumber']}}
								utilities.xbmcJsonRequest(req)
							# get summary data now if we are rating this movie
							if utilities.getSettingAsBool('rate_movie') and self.traktSummaryInfo is None:
								Debug("[Scrobbler] Movie rating is enabled, pre-fetching summary information.")
								self.traktSummaryInfo = self.traktapi.getMovieSummary(self.curVideoInfo['imdbnumber'])

				Debug("[Scrobbler] Watch response: %s" % str(response))
				
		elif utilities.isEpisode(self.curVideo['type']) and scrobbleEpisodeOption:
			if self.isMultiPartEpisode:
				Debug("[Scrobbler] Multi-part episode, watching part %d of %d." % (self.curMPEpisode + 1, self.curVideo['multi_episode_count']))
				# recalculate watchedPercent and duration for multi-part
				adjustedDuration = int(self.videoDuration / self.curVideo['multi_episode_count'])
				duration = adjustedDuration / 60
				watchedPercent = ((self.watchedTime - (adjustedDuration * self.curMPEpisode)) / adjustedDuration) * 100
			
			response = self.traktapi.watchingEpisode(self.curVideoInfo, duration, watchedPercent)
			if response != None:
				if self.curVideoInfo['tvdb_id'] is None:
					if 'status' in response and response['status'] == "success":
						if 'show' in response and 'tvdb_id' in response['show']:
							self.curVideoInfo['tvdb_id'] = response['show']['tvdb_id']
							if 'id' in self.curVideo and utilities.getSettingAsBool('update_tvdb_id'):
								req = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetTVShowDetails", "params": {"tvshowid" : self.curVideoInfo['tvshowid'], "imdbnumber": self.curVideoInfo['tvdb_id']}}
								utilities.xbmcJsonRequest(req)
							# get summary data now if we are rating this episode
							if utilities.getSettingAsBool('rate_episode') and self.traktSummaryInfo is None:
								Debug("[Scrobbler] Episode rating is enabled, pre-fetching summary information.")
								self.traktSummaryInfo = self.traktapi.getEpisodeSummary(self.curVideoInfo['tvdb_id'], self.curVideoInfo['season'], self.curVideoInfo['episode'])

				Debug("[Scrobbler] Watch response: %s" % str(response))

	def stoppedWatching(self):
		Debug("[Scrobbler] stoppedWatching()")
		scrobbleMovieOption = utilities.getSettingAsBool("scrobble_movie")
		scrobbleEpisodeOption = utilities.getSettingAsBool("scrobble_episode")

		if utilities.isMovie(self.curVideo['type']) and scrobbleMovieOption:
			response = self.traktapi.cancelWatchingMovie()
			if response != None:
				Debug("[Scrobbler] Cancel watch response: %s" % str(response))
		elif utilities.isEpisode(self.curVideo['type']) and scrobbleEpisodeOption:
			response = self.traktapi.cancelWatchingEpisode()
			if response != None:
				Debug("[Scrobbler] Cancel watch response: %s" % str(response))

	def scrobble(self):
		if not self.curVideoInfo:
			return

		Debug("[Scrobbler] scrobble()")
		scrobbleMovieOption = utilities.getSettingAsBool('scrobble_movie')
		scrobbleEpisodeOption = utilities.getSettingAsBool('scrobble_episode')

		duration = self.videoDuration / 60
		watchedPercent = (self.watchedTime / self.videoDuration) * 100

		if utilities.isMovie(self.curVideo['type']) and scrobbleMovieOption:
			response = self.traktapi.scrobbleMovie(self.curVideoInfo, duration, watchedPercent)
			if not response is None and 'status' in response:
				if response['status'] == "success":
					self.watchlistTagCheck()
					response['title'] = response['movie']['title']
					response['year'] = response['movie']['year']
					self.scrobbleNotification(response)
					Debug("[Scrobbler] Scrobble response: %s" % str(response))
				elif response['status'] == "failure":
					if response['error'].startswith("scrobbled") and response['error'].endswith("already"):
						Debug("[Scrobbler] Movie was just recently scrobbled, attempting to cancel watching instead.")
						self.stoppedWatching()
					elif response['error'] == "movie not found":
						Debug("[Scrobbler] Movie '%s' was not found on trakt.tv, possible malformed XBMC metadata." % self.curVideoInfo['title'])

		elif utilities.isEpisode(self.curVideo['type']) and scrobbleEpisodeOption:
			if self.isMultiPartEpisode:
				Debug("[Scrobbler] Multi-part episode, scrobbling part %d of %d." % (self.curMPEpisode + 1, self.curVideo['multi_episode_count']))
				adjustedDuration = int(self.videoDuration / self.curVideo['multi_episode_count'])
				duration = adjustedDuration / 60
				watchedPercent = ((self.watchedTime - (adjustedDuration * self.curMPEpisode)) / adjustedDuration) * 100
			
			response = self.traktapi.scrobbleEpisode(self.curVideoInfo, duration, watchedPercent)
			if not response is None and 'status' in response:
				if response['status'] == "success":
					response['episode']['season'] = response['season']
					self.scrobbleNotification(response)
					Debug("[Scrobbler] Scrobble response: %s" % str(response))
				elif response['status'] == "failure":
					if response['error'].startswith("scrobbled") and response['error'].endswith("already"):
						Debug("[Scrobbler] Episode was just recently scrobbled, attempting to cancel watching instead.")
						self.stoppedWatching()
					elif response['error'] == "show not found":
						Debug("[Scrobbler] Show '%s' was not found on trakt.tv, possible malformed XBMC metadata." % self.curVideoInfo['showtitle'])

	def scrobbleNotification(self, info):
		if not self.curVideoInfo:
			return
		
		if utilities.getSettingAsBool("scrobble_notification"):
			s = utilities.getFormattedItemName(self.curVideo['type'], info)
			utilities.notification(utilities.getString(1049), s)

	def watchlistTagCheck(self):
		if not utilities.isMovie(self.curVideo['type']):
			return

		if not 'id' in self.curVideo:
			return

		if not (tagging.isTaggingEnabled() and tagging.isWatchlistsEnabled()):
			return

		id = self.curVideo['id']
		result = utilities.getMovieDetailsFromXbmc(id, ['tag'])
		
		if result:
			tags = result['tag']

			if tagging.hasTraktWatchlistTag(tags):
				tags.remove(tagging.listToTag("Watchlist"))
				s = utilities.getFormattedItemName(self.curVideo['type'], self.curVideoInfo)
				tagging.xbmcSetTags(id, self.curVideo['type'], s, tags)

		else:
			utilities.Debug("No data was returned from XBMC, aborting tag udpate.")

	def check(self):
		scrobbleMinViewTimeOption = utilities.getSettingAsFloat("scrobble_min_view_time")

		Debug("[Scrobbler] watched: %s / %s" % (str(self.watchedTime), str(self.videoDuration)))
		if ((self.watchedTime / self.videoDuration) * 100) >= scrobbleMinViewTimeOption:
			self.scrobble()
		else:
			self.stoppedWatching()

########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

import xbmc
import threading
from time import time
import queue
import globals
import utilities
from traktapi import traktAPI
from rating import rateMedia, rateOnTrakt
from scrobbler import Scrobbler
from tagging import Tagger
from sync import Sync

try:
	import simplejson as json
except ImportError:
	import json

class traktService:

	scrobbler = None
	tagger = None
	updateTagsThread = None
	watcher = None
	syncThread = None
	dispatchQueue = queue.SqliteQueue()
	_interval = 10 * 60 # how often to send watching call
	
	def __init__(self):
		threading.Thread.name = 'trakt'

	def _dispatchQueue(self, data):
		utilities.Debug("Queuing for dispatch: %s" % data)
		self.dispatchQueue.append(data)
	
	def _dispatch(self, data):
		utilities.Debug("Dispatch: %s" % data)
		action = data['action']
		if action == 'started':
			del data['action']
			self.scrobbler.playbackStarted(data)
			self.watcher = threading.Timer(self._interval, self.doWatching)
			self.watcher.name = "trakt-watching"
			self.watcher.start()
		elif action == 'ended' or action == 'stopped':
			self.scrobbler.playbackEnded()
			if self.watcher:
				if self.watcher.isAlive():
					self.watcher.cancel()
					self.watcher = None
		elif action == 'paused':
			self.scrobbler.playbackPaused()
		elif action == 'resumed':
			self.scrobbler.playbackResumed()
		elif action == 'seek' or action == 'seekchapter':
			self.scrobbler.playbackSeek()
		elif action == 'databaseUpdated':
			if utilities.getSettingAsBool('sync_on_update'):
				utilities.Debug("Performing sync after library update.")
				self.doSync()
		elif action == 'scanStarted':
			pass
		elif action == 'settingsChanged':
			utilities.Debug("Settings changed, reloading.")
			globals.traktapi.updateSettings()
			self.tagger.updateSettings()
		elif action == 'markWatched':
			del data['action']
			self.doMarkWatched(data)
		elif action == 'manualRating':
			ratingData = data['ratingData']
			self.doManualRating(ratingData)
		elif action == 'manualSync':
			if not self.syncThread.isAlive():
				utilities.Debug("Performing a manual sync.")
				self.doSync(manual=True, silent=data['silent'], library=data['library'])
			else:
				utilities.Debug("There already is a sync in progress.")
		elif action == 'updatetags':
			if self.updateTagsThread and self.updateTagsThread.isAlive():
				utilities.Debug("Currently updating tags already.")
			else:
				self.updateTagsThread = threading.Thread(target=self.tagger.updateTagsFromTrakt, name="trakt-updatetags")
				self.updateTagsThread.start()
		elif action == 'managelists':
			self.tagger.manageLists()
		elif action == 'itemlists':
			del data['action']
			self.tagger.itemLists(data)
		elif action == 'addtolist':
			del data['action']
			list = data['list']
			del data['list']
			self.tagger.manualAddToList(list, data)
		elif action == 'removefromlist':
			del data['action']
			list = data['list']
			del data['list']
			self.tagger.manualRemoveFromList(list, data)
		elif action == 'loadsettings':
			force = False
			if 'force' in data:
				force = data['force']
			globals.traktapi.getAccountSettings(force)
		elif action == 'settings':
			utilisites.showSettings()
		else:
			utilities.Debug("Unknown dispatch action, '%s'." % action)

	def run(self):
		startup_delay = utilities.getSettingAsInt('startup_delay')
		if startup_delay:
			utilities.Debug("Delaying startup by %d seconds." % startup_delay)
			xbmc.sleep(startup_delay * 1000)

		utilities.Debug("Service thread starting.")

		# purge queue before doing anything
		self.dispatchQueue.purge()

		# queue a loadsettings action
		self.dispatchQueue.append({'action': 'loadsettings'})

		# setup event driven classes
		self.Player = traktPlayer(action = self._dispatchQueue)
		self.Monitor = traktMonitor(action = self._dispatchQueue)

		# init traktapi class
		globals.traktapi = traktAPI()

		# init sync thread
		self.syncThread = syncThread()

		# init scrobbler class
		self.scrobbler = Scrobbler(globals.traktapi)

		# init tagging class
		self.tagger = Tagger(globals.traktapi)
		
		# start loop for events
		while (not xbmc.abortRequested):
			while len(self.dispatchQueue) and (not xbmc.abortRequested):
				data = self.dispatchQueue.get()
				utilities.Debug("Queued dispatch: %s" % data)
				self._dispatch(data)

			if xbmc.Player().isPlayingVideo():
				self.scrobbler.update()

			xbmc.sleep(500)

		# we are shutting down
		utilities.Debug("Beginning shut down.")

		# check if watcher is set and active, if so, cancel it.
		if self.watcher:
			if self.watcher.isAlive():
				self.watcher.cancel()

		# delete player/monitor
		del self.Player
		del self.Monitor

		# check update tags thread.
		if self.updateTagsThread and self.updateTagsThread.isAlive():
			self.updateTagsThread.join()

		# check if sync thread is running, if so, join it.
		if self.syncThread.isAlive():
			self.syncThread.join()

	def doWatching(self):
		# check if we're still playing a video
		if not xbmc.Player().isPlayingVideo():
			self.watcher = None
			return

		# call watching method
		self.scrobbler.watching()

		# start a new timer thread
		self.watcher = threading.Timer(self._interval, self.doWatching)
		self.watcher.name = "trakt-watching"
		self.watcher.start()

	def doManualRating(self, data):

		action = data['action']
		media_type = data['media_type']
		summaryInfo = None

		if not utilities.isValidMediaType(media_type):
			utilities.Debug("doManualRating(): Invalid media type '%s' passed for manual %s." % (media_type, action))
			return

		if not data['action'] in ['rate', 'unrate']:
			utilities.Debug("doManualRating(): Unknown action passed.")
			return
			
		if 'dbid' in data:
			utilities.Debug("Getting data for manual %s of library '%s' with ID of '%s'" % (action, media_type, data['dbid']))
		elif 'remoteitd' in data:
			if 'season' in data:
				utilities.Debug("Getting data for manual %s of non-library '%s' S%02dE%02d, with ID of '%s'." % (action, media_type, data['season'], data['episode'], data['remoteid']))
			else:
				utilities.Debug("Getting data for manual %s of non-library '%s' with ID of '%s'" % (action, media_type, data['remoteid']))

		if utilities.isEpisode(media_type):
			summaryInfo = globals.traktapi.getEpisodeSummary(data['tvdb_id'], data['season'], data['episode'])
		elif utilities.isShow(media_type):
			summaryInfo = globals.traktapi.getShowSummary(data['imdbnumber'])
		elif utilities.isMovie(media_type):
			summaryInfo = globals.traktapi.getMovieSummary(data['imdbnumber'])
		
		if not summaryInfo is None:
			if utilities.isMovie(media_type) or utilities.isShow(media_type):
				summaryInfo['xbmc_id'] = data['dbid']

			if action == 'rate':
				if not 'rating' in data:
					rateMedia(media_type, summaryInfo)
				else:
					rateMedia(media_type, summaryInfo, rating=data['rating'])
			elif action == 'unrate':
				rateMedia(media_type, summaryInfo, unrate=True)
		else:
			utilities.Debug("doManualRating(): Summary info was empty, possible problem retrieving data from trakt.tv")

	def doMarkWatched(self, data):

		media_type = data['media_type']
		simulate = utilities.getSettingAsBool('simulate_sync')
		markedNotification = utilities.getSettingAsBool('show_marked_notification')
		
		if utilities.isMovie(media_type):
			summaryInfo = globals.traktapi.getMovieSummary(data['id'])
			if summaryInfo:
				if not summaryInfo['watched']:
					s = utilities.getFormattedItemName(media_type, summaryInfo)
					utilities.Debug("doMarkWatched(): '%s' is not watched on trakt, marking it as watched." % s)
					movie = {}
					movie['imdb_id'] = data['id']
					movie['title'] = summaryInfo['title']
					movie['year'] = summaryInfo['year']
					movie['plays'] = 1
					movie['last_played'] = int(time())
					params = {'movies': [movie]}
					utilities.Debug("doMarkWatched(): %s" % str(params))
					
					if not simulate:
						result = globals.traktapi.updateSeenMovie(params)
						if result:
							if markedNotification:
								utilities.notification(utilities.getString(1550), s)
						else:
							utilities.notification(utilities.getString(1551), s)
					else:
						if markedNotification:
							utilities.notification(utilities.getString(1550), s)
					
		elif utilities.isEpisode(media_type):
			summaryInfo = globals.traktapi.getEpisodeSummary(data['id'], data['season'], data['episode'])
			if summaryInfo:
				if not summaryInfo['episode']['watched']:
					s = utilities.getFormattedItemName(media_type, summaryInfo)
					utilities.Debug("doMarkWathced(): '%s' is not watched on trakt, marking it as watched." % s)
					params = {}
					params['imdb_id'] = summaryInfo['show']['imdb_id']
					params['tvdb_id'] = summaryInfo['show']['tvdb_id']
					params['title'] = summaryInfo['show']['title']
					params['year'] = summaryInfo['show']['year']
					params['episodes'] = [{'season': data['season'], 'episode': data['episode']}]
					utilities.Debug("doMarkWatched(): %s" % str(params))
					
					if not simulate:
						result = globals.traktapi.updateSeenEpisode(params)
						if result:
							if markedNotification:
								utilities.notification(utilities.getString(1550), s)
						else:
							utilities.notification(utilities.getString(1551), s)
					else:
						if markedNotification:
							utilities.notification(utilities.getString(1550), s)

		elif utilities.isSeason(media_type):
			showInfo = globals.traktapi.getShowSummary(data['id'])
			if not showInfo:
				return
			summaryInfo = globals.traktapi.getSeasonInfo(data['id'], data['season'])
			if summaryInfo:
				showInfo['season'] = data['season']
				s = utilities.getFormattedItemName(media_type, showInfo)
				params = {}
				params['imdb_id'] = showInfo['imdb_id']
				params['tvdb_id'] = showInfo['tvdb_id']
				params['title'] = showInfo['title']
				params['year'] = showInfo['year']
				params['episodes'] = []
				for ep in summaryInfo:
					if ep['episode'] in data['episodes']:
						if not ep['watched']:
							params['episodes'].append({'season': ep['season'], 'episode': ep['episode']})

				utilities.Debug("doMarkWatched(): '%s - Season %d' has %d episode(s) that are going to be marked as watched." % (showInfo['title'], data['season'], len(params['episodes'])))
				
				if len(params['episodes']) > 0:
					utilities.Debug("doMarkWatched(): %s" % str(params))
					if not simulate:
						result = globals.traktapi.updateSeenEpisode(params)
						if result:
							if markedNotification:
								utilities.notification(utilities.getString(1550), utilities.getString(1552) % (len(params['episodes']), s))
						else:
							utilities.notification(utilities.getString(1551), utilities.getString(1552) % (len(params['episodes']), s))
					else:
						if markedNotification:
							utilities.notification(utilities.getString(1550), utilities.getString(1552) % (len(params['episodes']), s))

		elif utilities.isShow(media_type):
			summaryInfo = globals.traktapi.getShowSummary(data['id'], extended=True)
			if summaryInfo:
				s = utilities.getFormattedItemName(media_type, summaryInfo)
				params = {}
				params['imdb_id'] = summaryInfo['imdb_id']
				params['tvdb_id'] = summaryInfo['tvdb_id']
				params['title'] = summaryInfo['title']
				params['year'] = summaryInfo['year']
				params['episodes'] = []
				for season in summaryInfo['seasons']:
					for ep in season['episodes']:
						if str(season['season']) in data['seasons']:
							if ep['episode'] in data['seasons'][str(season['season'])]:
								if not ep['watched']:
									params['episodes'].append({'season': ep['season'], 'episode': ep['episode']})
				utilities.Debug("doMarkWatched(): '%s' has %d episode(s) that are going to be marked as watched." % (summaryInfo['title'], len(params['episodes'])))

				if len(params['episodes']) > 0:
					utilities.Debug("doMarkWatched(): %s" % str(params))
					if not simulate:
						result = globals.traktapi.updateSeenEpisode(params)
						if result:
							if markedNotification:
								utilities.notification(utilities.getString(1550), utilities.getString(1552) % (len(params['episodes']), s))
						else:
							utilities.notification(utilities.getString(1551), utilities.getString(1552) % (len(params['episodes']), s))
					else:
						if markedNotification:
							utilities.notification(utilities.getString(1550), utilities.getString(1552) % (len(params['episodes']), s))

	def doSync(self, manual=False, silent=False, library="all"):
		self.syncThread = syncThread(manual, silent, library)
		self.syncThread.start()

class syncThread(threading.Thread):

	_isManual = False

	def __init__(self, isManual=False, runSilent=False, library="all"):
		threading.Thread.__init__(self)
		self.name = "trakt-sync"
		self._isManual = isManual
		self._runSilent = runSilent
		self._library = library

	def run(self):
		sync = Sync(show_progress=self._isManual, run_silent=self._runSilent, library=self._library, api=globals.traktapi)
		sync.sync()
		
		if utilities.getSettingAsBool('tagging_enable') and utilities.getSettingAsBool('tagging_tag_after_sync'):
			q = queue.SqliteQueue()
			q.append({'action': 'updatetags'})

class traktMonitor(xbmc.Monitor):

	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)
		self.action = kwargs['action']
		utilities.Debug("[traktMonitor] Initalized.")

	# called when database gets updated and return video or music to indicate which DB has been changed
	def onDatabaseUpdated(self, database):
		if database == 'video':
			utilities.Debug("[traktMonitor] onDatabaseUpdated(database: %s)" % database)
			data = {'action': 'databaseUpdated'}
			self.action(data)

	# called when database update starts and return video or music to indicate which DB is being updated
	def onDatabaseScanStarted(self, database):
		if database == "video":
			utilities.Debug("[traktMonitor] onDatabaseScanStarted(database: %s)" % database)
			data = {'action': 'scanStarted'}
			self.action(data)

	def onSettingsChanged(self):
		data = {'action': 'settingsChanged'}
		self.action(data)

class traktPlayer(xbmc.Player):

	_playing = False
	plIndex = None

	def __init__(self, *args, **kwargs):
		xbmc.Player.__init__(self)
		self.action = kwargs['action']
		utilities.Debug("[traktPlayer] Initalized.")

	# called when xbmc starts playing a file
	def onPlayBackStarted(self):
		xbmc.sleep(1000)
		self.type = None
		self.id = None

		# only do anything if we're playing a video
		if self.isPlayingVideo():
			# get item data from json rpc
			result = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'Player.GetItem', 'params': {'playerid': 1}, 'id': 1})
			utilities.Debug("[traktPlayer] onPlayBackStarted() - %s" % result)

			# check for exclusion
			_filename = None
			try:
				_filename = self.getPlayingFile()
			except:
				utilities.Debug("[traktPlayer] onPlayBackStarted() - Exception trying to get playing filename, player suddenly stopped.")
				return

			if utilities.checkScrobblingExclusion(_filename):
				utilities.Debug("[traktPlayer] onPlayBackStarted() - '%s' is in exclusion settings, ignoring." % _filename)
				return

			self.type = result['item']['type']

			data = {'action': 'started'}

			# check type of item
			if self.type == 'unknown':
				# do a deeper check to see if we have enough data to perform scrobbles
				utilities.Debug("[traktPlayer] onPlayBackStarted() - Started playing a non-library file, checking available data.")
				
				season = xbmc.getInfoLabel('VideoPlayer.Season')
				episode = xbmc.getInfoLabel('VideoPlayer.Episode')
				showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
				year = xbmc.getInfoLabel('VideoPlayer.Year')
				
				utilities.Debug("[traktPlayer] info - showtitle:"+ showtitle +", Year:"+ year +", Season:"+ season +", Episode:"+ episode)

				if season and episode and showtitle:
					# we have season, episode and show title, can scrobble this as an episode
					self.type = 'episode'
					data['type'] = 'episode'
					data['season'] = int(season)
					data['episode'] = int(episode)
					data['showtitle'] = showtitle
					data['title'] = xbmc.getInfoLabel('VideoPlayer.Title')
					if year.isdigit():
						data['year'] = year
					utilities.Debug("[traktPlayer] onPlayBackStarted() - Playing a non-library 'episode' - %s - S%02dE%02d - %s." % (data['showtitle'], data['season'], data['episode'], data['title']))
				elif year and not season and not showtitle:
					# we have a year and no season/showtitle info, enough for a movie
					self.type = 'movie'
					data['type'] = 'movie'
					data['year'] = int(year)
					data['title'] = xbmc.getInfoLabel('VideoPlayer.Title')
					utilities.Debug("[traktPlayer] onPlayBackStarted() - Playing a non-library 'movie' - %s (%d)." % (data['title'], data['year']))
				elif showtitle:
					title, season, episode = utilities.regex_tvshow(False, showtitle)
					data['type'] = 'episode'
					data['season'] = int(season)
					data['episode'] = int(episode)
					data['showtitle'] = title
					data['title'] = title
					utilities.Debug("[traktPlayer] onPlayBackStarted() - Title:"+title+", showtitle:"+showtitle+", season:"+season+", episode:"+episode)
				else:
					utilities.Debug("[traktPlayer] onPlayBackStarted() - Non-library file, not enough data for scrobbling, skipping.")
					return

			elif self.type == 'episode' or self.type == 'movie':
				# get library id
				self.id = result['item']['id']
				data['id'] = self.id
				data['type'] = self.type

				if self.type == 'episode':
					utilities.Debug("[traktPlayer] onPlayBackStarted() - Doing multi-part episode check.")
					result = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params': {'episodeid': self.id, 'properties': ['tvshowid', 'season', 'episode']}, 'id': 1})
					if result:
						utilities.Debug("[traktPlayer] onPlayBackStarted() - %s" % result)
						tvshowid = int(result['episodedetails']['tvshowid'])
						season = int(result['episodedetails']['season'])
						episode = int(result['episodedetails']['episode'])
						episode_index = episode - 1

						result = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': tvshowid, 'season': season, 'properties': ['episode', 'file'], 'sort': {'method': 'episode'}}, 'id': 1})
						if result:
							utilities.Debug("[traktPlayer] onPlayBackStarted() - %s" % result)
							# make sure episodes array exists in results
							if 'episodes' in result:
								multi = []
								for i in range(episode_index, result['limits']['total']):
									if result['episodes'][i]['file'] == result['episodes'][episode_index]['file']:
										multi.append(result['episodes'][i]['episodeid'])
									else:
										break
								if len(multi) > 1:
									data['multi_episode_data'] = multi
									data['multi_episode_count'] = len(multi)
									utilities.Debug("[traktPlayer] onPlayBackStarted() - This episode is part of a multi-part episode.")
								else:
									utilities.Debug("[traktPlayer] onPlayBackStarted() - This is a single episode.")

			else:
				utilities.Debug("[traktPlayer] onPlayBackStarted() - Video type '%s' unrecognized, skipping." % self.type)
				return

			pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
			plSize = len(pl)
			if plSize > 1:
				pos = pl.getposition()
				if not self.plIndex is None:
					utilities.Debug("[traktPlayer] onPlayBackStarted() - User manually skipped to next (or previous) video, forcing playback ended event.")
					self.onPlayBackEnded()
				self.plIndex = pos
				utilities.Debug("[traktPlayer] onPlayBackStarted() - Playlist contains %d item(s), and is currently on item %d" % (plSize, (pos + 1)))

			self._playing = True

			# send dispatch
			self.action(data)

	# called when xbmc stops playing a file
	def onPlayBackEnded(self):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackEnded() - %s" % self.isPlayingVideo())
			self._playing = False
			self.plIndex = None
			data = {'action': 'ended'}
			self.action(data)

	# called when user stops xbmc playing a file
	def onPlayBackStopped(self):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackStopped() - %s" % self.isPlayingVideo())
			self._playing = False
			self.plIndex = None
			data = {'action': 'stopped'}
			self.action(data)

	# called when user pauses a playing file
	def onPlayBackPaused(self):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackPaused() - %s" % self.isPlayingVideo())
			data = {'action': 'paused'}
			self.action(data)

	# called when user resumes a paused file
	def onPlayBackResumed(self):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackResumed() - %s" % self.isPlayingVideo())
			data = {'action': 'resumed'}
			self.action(data)

	# called when user queues the next item
	def onQueueNextItem(self):
		if self._playing:
			utilities.Debug("[traktPlayer] onQueueNextItem() - %s" % self.isPlayingVideo())

	# called when players speed changes. (eg. user FF/RW)
	def onPlayBackSpeedChanged(self, speed):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackSpeedChanged(speed: %s) - %s" % (str(speed), self.isPlayingVideo()))

	# called when user seeks to a time
	def onPlayBackSeek(self, time, offset):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackSeek(time: %s, offset: %s) - %s" % (str(time), str(offset), self.isPlayingVideo()))
			data = {'action': 'seek', 'time': time, 'offset': offset}
			self.action(data)

	# called when user performs a chapter seek
	def onPlayBackSeekChapter(self, chapter):
		if self._playing:
			utilities.Debug("[traktPlayer] onPlayBackSeekChapter(chapter: %s) - %s" % (str(chapter), self.isPlayingVideo()))
			data = {'action': 'seekchapter', 'chapter': chapter}
			self.action(data)

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import utilities
from utilities import Debug, notification
import copy

progress = xbmcgui.DialogProgress()

class Sync():

	def __init__(self, show_progress=False, run_silent=False, library="all", api=None):
		self.traktapi = api
		self.show_progress = show_progress
		self.run_silent = run_silent
		self.library = library
		if self.show_progress and self.run_silent:
			Debug("[Sync] Sync is being run silently.")
		self.sync_on_update = utilities.getSettingAsBool('sync_on_update')
		self.notify = utilities.getSettingAsBool('show_sync_notifications')
		self.notify_during_playback = not (xbmc.Player().isPlayingVideo() and utilities.getSettingAsBool("hide_notifications_playback"))
		self.simulate = utilities.getSettingAsBool('simulate_sync')
		if self.simulate:
			Debug("[Sync] Sync is configured to be simulated.")

		_opts = ['ExcludePathOption', 'ExcludePathOption2', 'ExcludePathOption3']
		_vals = ['ExcludePath', 'ExcludePath2', 'ExcludePath3']
		self.exclusions = []
		for i in range(3):
			if utilities.getSettingAsBool(_opts[i]):
				_path = utilities.getSetting(_vals[i])
				if _path != "":
					self.exclusions.append(_path)

	def isCanceled(self):
		if self.show_progress and not self.run_silent and progress.iscanceled():
			Debug("[Sync] Sync was canceled by user.")
			return True
		elif xbmc.abortRequested:
			Debug('XBMC abort requested')
			return True
		else:
			return False

	def updateProgress(self, *args, **kwargs):
		if self.show_progress and not self.run_silent:
			kwargs['percent'] = args[0]
			progress.update(**kwargs)

	def checkExclusion(self, file):
		for _path in self.exclusions:
			if file.find(_path) > -1:
				return True
		return False

	''' begin code for episode sync '''
	def traktLoadShows(self):
		self.updateProgress(10, line1=utilities.getString(1485), line2=utilities.getString(1486))

		Debug('[Episodes Sync] Getting episode collection from trakt.tv')
		library_shows = self.traktapi.getShowLibrary()
		if not isinstance(library_shows, list):
			Debug("[Episodes Sync] Invalid trakt.tv show list, possible error getting data from trakt, aborting trakt.tv collection update.")
			return False

		self.updateProgress(12, line2=utilities.getString(1487))

		Debug('[Episodes Sync] Getting watched episodes from trakt.tv')
		watched_shows = self.traktapi.getWatchedEpisodeLibrary()
		if not isinstance(watched_shows, list):
			Debug("[Episodes Sync] Invalid trakt.tv watched show list, possible error getting data from trakt, aborting trakt.tv watched update.")
			return False

		shows = []
		i = 0
		x = float(len(library_shows))
		# reformat show array
		for show in library_shows:
			if show['title'] is None and show['imdb_id'] is None and show['tvdb_id'] is None:
				# has no identifing values, skip it
				continue

			y = {}
			w = {}
			for s in show['seasons']:
				y[s['season']] = s['episodes']
				w[s['season']] = []
			show['seasons'] = y
			show['watched'] = w
			show['in_collection'] = True
			if show['imdb_id'] is None:
				show['imdb_id'] = ""
			if show['tvdb_id'] is None:
				show['tvdb_id'] = ""

			shows.append(show)

			i = i + 1
			y = ((i / x) * 8) + 12
			self.updateProgress(int(y), line2=utilities.getString(1488))

		i = 0
		x = float(len(watched_shows))
		for watched_show in watched_shows:
			if watched_show['title'] is None and watched_show['imdb_id'] is None and watched_show['tvdb_id'] is None:
				# has no identifing values, skip it
				continue

			if watched_show['imdb_id'] is None:
				watched_show['imdb_id'] = ""
			if watched_show['tvdb_id'] is None:
				watched_show['tvdb_id'] = ""
			show = utilities.findShow(watched_show, shows)
			if show:
				for s in watched_show['seasons']:
					show['watched'][s['season']] = s['episodes']
			else:
				y = {}
				w = {}
				for s in watched_show['seasons']:
					w[s['season']] = s['episodes']
					y[s['season']] = []
				watched_show['seasons'] = y
				watched_show['watched'] = w
				watched_show['in_collection'] = False
				shows.append(watched_show)

			i = i + 1
			y = ((i / x) * 8) + 20
			self.updateProgress(int(y), line2=utilities.getString(1488))

		self.updateProgress(28, line2=utilities.getString(1489))

		return shows

	def xbmcLoadShowList(self):
		Debug("[Episodes Sync] Getting show data from XBMC")
		data = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': {'properties': ['title', 'imdbnumber', 'year']}, 'id': 0})
		if not data:
			Debug("[Episodes Sync] xbmc json request was empty.")
			return None
		
		if not 'tvshows' in data:
			Debug('[Episodes Sync] Key "tvshows" not found')
			return None

		shows = data['tvshows']
		Debug("[Episodes Sync] XBMC JSON Result: '%s'" % str(shows))

		# reformat show array
		for show in shows:
			show['in_collection'] = True
			show['tvdb_id'] = ""
			show['imdb_id'] = ""
			id = show['imdbnumber']
			if id.startswith("tt"):
				show['imdb_id'] = id
			if id.isdigit():
				show['tvdb_id'] = id
			del(show['imdbnumber'])
			del(show['label'])
		return shows

	def xbmcLoadShows(self):
		self.updateProgress(1, line1=utilities.getString(1480), line2=utilities.getString(1481))

		tvshows = self.xbmcLoadShowList()
		if tvshows is None:
			return None
			
		self.updateProgress(2, line2=utilities.getString(1482))

		i = 0
		x = float(len(tvshows))
		Debug("[Episodes Sync] Getting episode data from XBMC")
		for show in tvshows:
			show['seasons'] = {}
			show['watched'] = {}
			data = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': show['tvshowid'], 'properties': ['season', 'episode', 'playcount', 'uniqueid', 'file']}, 'id': 0})
			if not data:
				Debug("[Episodes Sync] There was a problem getting episode data for '%s', aborting sync." % show['title'])
				return None
			if not 'episodes' in data:
				Debug("[Episodes Sync] '%s' has no episodes in XBMC." % show['title'])
				continue
			episodes = data['episodes']
			for e in episodes:
				if self.checkExclusion(e['file']):
					continue
				_season = e['season']
				_episode = e['episode']
				if not _season in show['seasons']:
					show['seasons'][_season] = {}
					show['watched'][_season] = []
				if not _episode in show['seasons'][_season]:
					show['seasons'][_season][_episode] = {'id': e['episodeid'], 'episode_tvdb_id': e['uniqueid']['unknown']}
				if e['playcount'] > 0:
					if not _episode in show['watched'][_season]:
						show['watched'][_season].append(_episode)

			i = i + 1
			y = ((i / x) * 8) + 2
			self.updateProgress(int(y), line2=utilities.getString(1483))

		self.updateProgress(10, line2=utilities.getString(1484))

		return tvshows

	def countEpisodes(self, shows, watched=False, collection=True, all=False):
		count = 0
		p = 'watched' if watched else 'seasons'
		for show in shows:
			if all:
				for s in show[p]:
					count += len(show[p][s])
			else:
				if 'in_collection' in show and not show['in_collection'] == collection:
					continue
				for s in show[p]:
					count += len(show[p][s])
		return count
		
	def getShowAsString(self, show, short=False):
		p = []
		if 'seasons' in show:
			for season in show['seasons']:
				s = ""
				if short:
					s = ", ".join(["S%02dE%02d" % (season, i) for i in show['seasons'][season]])
				else:
					episodes = ", ".join([str(i) for i in show['seasons'][season]])
					s = "Season: %d, Episodes: %s" % (season, episodes)
				p.append(s)
		else:
			p = ["All"]
		return "%s [tvdb: %s] - %s" % (show['title'], show['tvdb_id'], ", ".join(p))

	def traktFormatShow(self, show):
		data = {'title': show['title'], 'tvdb_id': show['tvdb_id'], 'year': show['year'], 'episodes': []}
		if 'imdb_id' in show:
			data['imdb_id'] = show['imdb_id']
		for season in show['seasons']:
			for episode in show['seasons'][season]:
				data['episodes'].append({'season': season, 'episode': episode})
		return data

	def compareShows(self, shows_col1, shows_col2, watched=False, restrict=False):
		shows = []
		p = 'watched' if watched else 'seasons'
		for show_col1 in shows_col1:
			show_col2 = utilities.findShow(show_col1, shows_col2)
			if show_col2:
				season_diff = {}
				show_col2_seasons = show_col2[p]
				for season in show_col1[p]:
					a = show_col1[p][season]
					if season in show_col2_seasons:
						b = show_col2_seasons[season]
						diff = list(set(a).difference(set(b)))
						if len(diff) > 0:
							if restrict:
								t = list(set(show_col2['seasons'][season]).intersection(set(diff)))
								if len(t) > 0:
									eps = {}
									for ep in t:
										eps[ep] = show_col2['seasons'][season][ep]
									season_diff[season] = eps
							else:
								eps = {}
								for ep in diff:
									eps[ep] = ep
								season_diff[season] = eps
					else:
						if not restrict:
							if len(a) > 0:
								season_diff[season] = a
				if len(season_diff) > 0:
					show = {'title': show_col1['title'], 'tvdb_id': show_col1['tvdb_id'], 'year': show_col1['year'], 'seasons': season_diff}
					if 'imdb_id' in show_col1 and show_col1['imdb_id']:
						show['imdb_id'] = show_col1['imdb_id']
					if 'imdb_id' in show_col2 and show_col2['imdb_id']:
						show['imdb_id'] = show_col2['imdb_id']
					if 'tvshowid' in show_col1:
						show['tvshowid'] = show_col1['tvshowid']
					if 'tvshowid' in show_col2:
						show['tvshowid'] = show_col2['tvshowid']
					shows.append(show)
			else:
				if not restrict:
					if 'in_collection' in show_col1 and show_col1['in_collection']:
						if self.countEpisodes([show_col1], watched=watched) > 0:
							show = {'title': show_col1['title'], 'tvdb_id': show_col1['tvdb_id'], 'year': show_col1['year'], 'seasons': show_col1[p]}
							if 'tvshowid' in show_col1:
								show['tvshowid'] = show_col1['tvshowid']
							shows.append(show)
		return shows

	def traktAddEpisodes(self, shows):
		if len(shows) == 0:
			self.updateProgress(46, line1=utilities.getString(1435), line2=utilities.getString(1490))
			Debug("[Episodes Sync] trakt.tv episode collection is up to date.")
			return

		Debug("[Episodes Sync] %i show(s) have episodes (%d) to be added to your trakt.tv collection." % (len(shows), self.countEpisodes(shows)))
		for show in shows:
			Debug("[Episodes Sync] Episodes added: %s" % self.getShowAsString(show, short=True))
		
		self.updateProgress(28, line1=utilities.getString(1435), line2="%i %s" % (len(shows), utilities.getString(1436)), line3=" ")

		i = 0
		x = float(len(shows))
		for show in shows:
			if self.isCanceled():
				return

			epCount = self.countEpisodes([show])
			title = show['title'].encode('utf-8', 'ignore')

			i = i + 1
			y = ((i / x) * 18) + 28
			self.updateProgress(int(y), line1=utilities.getString(1435), line2=title, line3="%i %s" % (epCount, utilities.getString(1437)))

			s = self.traktFormatShow(show)
			if self.simulate:
				Debug("[Episodes Sync] %s" % str(s))
			else:
				self.traktapi.addEpisode(s)

		self.updateProgress(46, line1=utilities.getString(1435), line2=utilities.getString(1491) % self.countEpisodes(shows))

	def traktRemoveEpisodes(self, shows):
		if len(shows) == 0:
			self.updateProgress(98, line1=utilities.getString(1445), line2=utilities.getString(1496))
			Debug('[Episodes Sync] trakt.tv episode collection is clean')
			return

		Debug("[Episodes Sync] %i show(s) will have episodes removed from trakt.tv collection." % len(shows))
		for show in shows:
			Debug("[Episodes Sync] Episodes removed: %s" % self.getShowAsString(show, short=True))

		self.updateProgress(82, line1=utilities.getString(1445), line2=utilities.getString(1497) % self.countEpisodes(shows), line3=" ")

		i = 0
		x = float(len(shows))
		for show in shows:
			if self.isCanceled():
				return

			epCount = self.countEpisodes([show])
			title = show['title'].encode('utf-8', 'ignore')

			s = self.traktFormatShow(show)
			if self.simulate:
				Debug("[Episodes Sync] %s" % str(s))
			else:
				self.traktapi.removeEpisode(s)

			i = i + 1
			y = ((i / x) * 16) + 82
			self.updateProgress(int(y), line2=title, line3="%i %s" % (epCount, utilities.getString(1447)))

		self.updateProgress(98, line2=utilities.getString(1498) % self.countEpisodes(shows), line3=" ")

	def traktUpdateEpisodes(self, shows):
		if len(shows) == 0:
			self.updateProgress(64, line1=utilities.getString(1438), line2=utilities.getString(1492))
			Debug("[Episodes Sync] trakt.tv episode playcounts are up to date.")
			return

		Debug("[Episodes Sync] %i show(s) are missing playcounts on trakt.tv" % len(shows))
		for show in shows:
			Debug("[Episodes Sync] Episodes updated: %s" % self.getShowAsString(show, short=True))

		self.updateProgress(46, line1=utilities.getString(1438), line2="%i %s" % (len(shows), utilities.getString(1439)), line3=" ")

		i = 0
		x = float(len(shows))
		for show in shows:
			if self.isCanceled():
				return

			epCount = self.countEpisodes([show])
			title = show['title'].encode('utf-8', 'ignore')

			i = i + 1
			y = ((i / x) * 18) + 46
			self.updateProgress(70, line2=title, line3="%i %s" % (epCount, utilities.getString(1440)))

			s = self.traktFormatShow(show)
			if self.simulate:
				Debug("[Episodes Sync] %s" % str(s))
			else:
				self.traktapi.updateSeenEpisode(s)

		self.updateProgress(64, line2="%i %s" % (len(shows), utilities.getString(1439)))

	def xbmcUpdateEpisodes(self, shows):
		if len(shows) == 0:
			self.updateProgress(82, line1=utilities.getString(1441), line2=utilities.getString(1493))
			Debug("[Episodes Sync] XBMC episode playcounts are up to date.")
			return

		Debug("[Episodes Sync] %i show(s) shows are missing playcounts on XBMC" % len(shows))
		for s in ["%s" % self.getShowAsString(s, short=True) for s in shows]:
			Debug("[Episodes Sync] Episodes updated: %s" % s)

		self.updateProgress(64, line1=utilities.getString(1441), line2="%i %s" % (len(shows), utilities.getString(1439)), line3=" ")

		episodes = []
		for show in shows:
			for season in show['seasons']:
				for episode in show['seasons'][season]:
					episodes.append({'episodeid': show['seasons'][season][episode]['id'], 'playcount': 1})

		#split episode list into chunks of 50
		chunked_episodes = utilities.chunks([{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": episodes[i], "id": i} for i in range(len(episodes))], 50)
		i = 0
		x = float(len(chunked_episodes))
		for chunk in chunked_episodes:
			if self.isCanceled():
				return
			if self.simulate:
				Debug("[Episodes Sync] %s" % str(chunk))
			else:
				utilities.xbmcJsonRequest(chunk)

			i = i + 1
			y = ((i / x) * 18) + 64
			self.updateProgress(int(y), line2=utilities.getString(1494))

		self.updateProgress(82, line2=utilities.getString(1495) % len(episodes))

	def syncEpisodes(self):
		if not self.show_progress and self.sync_on_update and self.notify and self.notify_during_playback:
			notification('%s %s' % (utilities.getString(1400), utilities.getString(1406)), utilities.getString(1420)) #Sync started
		if self.show_progress and not self.run_silent:
			progress.create("%s %s" % (utilities.getString(1400), utilities.getString(1406)), line1=" ", line2=" ", line3=" ")

		xbmcShows = self.xbmcLoadShows()
		if not isinstance(xbmcShows, list) and not xbmcShows:
			Debug("[Episodes Sync] XBMC show list is empty, aborting tv show Sync.")
			if self.show_progress and not self.run_silent:
				progress.close()
			return

		traktShows = self.traktLoadShows()
		if not isinstance(traktShows, list):
			Debug("[Episodes Sync] Error getting trakt.tv show list, aborting tv show sync.")
			if self.show_progress and not self.run_silent:
				progress.close()
			return

		if utilities.getSettingAsBool('add_episodes_to_trakt') and not self.isCanceled():
			traktShowsAdd = self.compareShows(xbmcShows, traktShows)
			self.traktAddEpisodes(traktShowsAdd)
		
		if utilities.getSettingAsBool('trakt_episode_playcount') and not self.isCanceled():
			traktShowsUpdate = self.compareShows(xbmcShows, traktShows, watched=True)
			self.traktUpdateEpisodes(traktShowsUpdate)

		if utilities.getSettingAsBool('xbmc_episode_playcount') and not self.isCanceled():
			xbmcShowsUpadate = self.compareShows(traktShows, xbmcShows, watched=True, restrict=True)
			self.xbmcUpdateEpisodes(xbmcShowsUpadate)

		if utilities.getSettingAsBool('clean_trakt_episodes') and not self.isCanceled():
			traktShowsRemove = self.compareShows(traktShows, xbmcShows)
			self.traktRemoveEpisodes(traktShowsRemove)

		if not self.show_progress and self.sync_on_update and self.notify and self.notify_during_playback:
			notification('%s %s' % (utilities.getString(1400), utilities.getString(1406)), utilities.getString(1421)) #Sync complete

		if not self.isCanceled() and self.show_progress and not self.run_silent:
			self.updateProgress(100, line1=" ", line2=utilities.getString(1442), line3=" ")
			progress.close()

		Debug("[Episodes Sync] Shows on trakt.tv (%d), shows in XBMC (%d)." % (len(utilities.findAllInList(traktShows, 'in_collection', True)), len(xbmcShows)))
		Debug("[Episodes Sync] Episodes on trakt.tv (%d), episodes in XBMC (%d)." % (self.countEpisodes(traktShows), self.countEpisodes(xbmcShows)))
		Debug("[Episodes Sync] Complete.")

	''' begin code for movie sync '''
	def traktLoadMovies(self):
		self.updateProgress(5, line2=utilities.getString(1462))

		Debug("[Movies Sync] Getting movie collection from trakt.tv")
		movies = self.traktapi.getMovieLibrary()
		if not isinstance(movies, list):
			Debug("[Movies Sync] Invalid trakt.tv movie list, possible error getting data from trakt, aborting trakt.tv collection update.")
			return False

		self.updateProgress(6, line2=utilities.getString(1463))

		Debug("[Movies Sync] Getting seen movies from trakt.tv")
		watched_movies = self.traktapi.getWatchedMovieLibrary()
		if not isinstance(watched_movies, list):
			Debug("[Movies Sync] Invalid trakt.tv movie seen list, possible error getting data from trakt, aborting trakt.tv watched update.")
			return False

		self.updateProgress(8, line2=utilities.getString(1464))

		i = 0
		x = float(len(movies))
		# reformat movie arrays
		for movie in movies:
			movie['plays'] = 0
			movie['in_collection'] = True
			if movie['imdb_id'] is None:
				movie['imdb_id'] = ""
			if movie['tmdb_id'] is None:
				movie['tmdb_id'] = ""

			i = i + 1
			y = ((i / x) * 6) + 8
			self.updateProgress(int(y), line2=utilities.getString(1465))

		i = 0
		x = float(len(watched_movies))
		for movie in watched_movies:
			if movie['imdb_id'] is None:
				movie['imdb_id'] = ""
			if movie['tmdb_id'] is None:
				movie['tmdb_id'] = "" 
			else:
				movie['tmdb_id'] = unicode(movie['tmdb_id'])
			m = utilities.findMovie(movie, movies)
			if m:
				m['plays'] = movie['plays']
			else:
				movie['in_collection'] = False
				movies.append(movie)

			i = i + 1
			y = ((i / x) * 6) + 14
			self.updateProgress(int(y), line2=utilities.getString(1465))

		self.updateProgress(20, line2=utilities.getString(1466))

		return movies

	def xbmcLoadMovies(self):
		self.updateProgress(1, line2=utilities.getString(1460))

		Debug("[Movies Sync] Getting movie data from XBMC")
		data = utilities.xbmcJsonRequest({'jsonrpc': '2.0', 'id': 0, 'method': 'VideoLibrary.GetMovies', 'params': {'properties': ['title', 'imdbnumber', 'year', 'playcount', 'lastplayed', 'file']}})
		if not data:
			Debug("[Movies Sync] XBMC JSON request was empty.")
			return
		
		if not 'movies' in data:
			Debug('[Movies Sync] Key "movies" not found')
			return

		movies = data['movies']
		Debug("[Movies Sync] XBMC JSON Result: '%s'" % str(movies))

		i = 0
		x = float(len(movies))
		
		xbmc_movies = []

		# reformat movie array
		for movie in movies:
			if self.checkExclusion(movie['file']):
				continue
			if movie['lastplayed']:
				movie['last_played'] = utilities.sqlDateToUnixDate(movie['lastplayed'])
			movie['plays'] = movie.pop('playcount')
			movie['in_collection'] = True
			movie['imdb_id'] = ""
			movie['tmdb_id'] = ""
			id = movie['imdbnumber']
			if id.startswith("tt"):
				movie['imdb_id'] = id
			if id.isdigit():
				movie['tmdb_id'] = id
			del(movie['imdbnumber'])
			del(movie['lastplayed'])
			del(movie['label'])
			del(movie['file'])

			xbmc_movies.append(movie)

			i = i + 1
			y = ((i / x) * 4) + 1
			self.updateProgress(int(y))
			
		self.updateProgress(5, line2=utilities.getString(1461))

		return xbmc_movies

	def sanitizeMovieData(self, movie):
		data = copy.deepcopy(movie)
		if 'in_collection' in data:
			del(data['in_collection'])
		if 'movieid' in data:
			del(data['movieid'])
		if not data['tmdb_id']:
			del(data['tmdb_id'])
		return data

	def countMovies(self, movies, collection=True):
		if len(movies) > 0:
			if 'in_collection' in movies[0]:
				return len(utilities.findAllInList(movies, 'in_collection', collection))
			else:
				return len(movies)
		return 0

	def compareMovies(self, movies_col1, movies_col2, watched=False, restrict=False):
		movies = []
		for movie_col1 in movies_col1:
			movie_col2 = utilities.findMovie(movie_col1, movies_col2)
			if movie_col2:
				if watched:
					if (movie_col2['plays'] == 0) and (movie_col1['plays'] > movie_col2['plays']):
						if 'movieid' not in movie_col1:
							movie_col1['movieid'] = movie_col2['movieid']
						movies.append(movie_col1)
				else:
					if 'in_collection' in movie_col2 and not movie_col2['in_collection']:
						movies.append(movie_col1)
			else:
				if not restrict:
					if 'in_collection' in movie_col1 and movie_col1['in_collection']:
						if watched and (movie_col1['plays'] > 0):
							movies.append(movie_col1)
						elif not watched:
							movies.append(movie_col1)
		return movies

	def traktAddMovies(self, movies):
		if len(movies) == 0:
			self.updateProgress(40, line2=utilities.getString(1467))
			Debug("[Movies Sync] trakt.tv movie collection is up to date.")
			return
		
		titles = ", ".join(["%s (%s)" % (m['title'], m['imdb_id']) for m in movies])
		Debug("[Movies Sync] %i movie(s) will be added to trakt.tv collection." % len(movies))
		Debug("[Movies Sync] Movies added: %s" % titles)

		self.updateProgress(20, line2="%i %s" % (len(movies), utilities.getString(1426)))

		chunked_movies = utilities.chunks([self.sanitizeMovieData(movie) for movie in movies], 50)
		i = 0
		x = float(len(chunked_movies))
		for chunk in chunked_movies:
			if self.isCanceled():
				return
			params = {'movies': chunk}
			if self.simulate:
				Debug("[Movies Sync] %s" % str(params))
			else:
				self.traktapi.addMovie(params)

			i = i + 1
			y = ((i / x) * 20) + 20
			self.updateProgress(int(y), line2=utilities.getString(1477))

		self.updateProgress(40, line2=utilities.getString(1468) % len(movies))

	def traktRemoveMovies(self, movies):
		if len(movies) == 0:
			self.updateProgress(98, line2=utilities.getString(1474))
			Debug("[Movies Sync] trakt.tv movie collection is clean, no movies to remove.")
			return
		
		titles = ", ".join(["%s (%s)" % (m['title'], m['imdb_id']) for m in movies])
		Debug("[Movies Sync] %i movie(s) will be removed from trakt.tv collection." % len(movies))
		Debug("[Movies Sync] Movies removed: %s" % titles)

		self.updateProgress(80, line2="%i %s" % (len(movies), utilities.getString(1444)))
		
		chunked_movies = utilities.chunks([self.sanitizeMovieData(movie) for movie in movies], 50)
		i = 0
		x = float(len(chunked_movies))
		for chunk in chunked_movies:
			if self.isCanceled():
				return
			params = {'movies': chunk}
			if self.simulate:
				Debug("[Movies Sync] %s" % str(params))
			else:
				self.traktapi.removeMovie(params)

			i = i + 1
			y = ((i / x) * 20) + 80
			self.updateProgress(int(y), line2=utilities.getString(1476))

		self.updateProgress(98, line2=utilities.getString(1475) % len(movies))

	def traktUpdateMovies(self, movies):
		if len(movies) == 0:
			self.updateProgress(60, line2=utilities.getString(1469))
			Debug("[Movies Sync] trakt.tv movie playcount is up to date")
			return
		
		titles = ", ".join(["%s (%s)" % (m['title'], m['imdb_id']) for m in movies])
		Debug("[Movies Sync] %i movie(s) playcount will be updated on trakt.tv" % len(movies))
		Debug("[Movies Sync] Movies updated: %s" % titles)

		self.updateProgress(40, line2="%i %s" % (len(movies), utilities.getString(1428)))

		# Send request to update playcounts on trakt.tv
		chunked_movies = utilities.chunks([self.sanitizeMovieData(movie) for movie in movies], 50)
		i = 0
		x = float(len(chunked_movies))
		for chunk in chunked_movies:
			if self.isCanceled():
				return
			params = {'movies': chunk}
			if self.simulate:
				Debug("[Movies Sync] %s" % str(params))
			else:
				self.traktapi.updateSeenMovie(params)

			i = i + 1
			y = ((i / x) * 20) + 40
			self.updateProgress(int(y), line2=utilities.getString(1478))

		self.updateProgress(60, line2=utilities.getString(1470) % len(movies))

	def xbmcUpdateMovies(self, movies):
		if len(movies) == 0:
			self.updateProgress(80, line2=utilities.getString(1471))
			Debug("[Movies Sync] XBMC movie playcount is up to date.")
			return
		
		titles = ", ".join(["%s (%s)" % (m['title'], m['imdb_id']) for m in movies])
		Debug("[Movies Sync] %i movie(s) playcount will be updated in XBMC" % len(movies))
		Debug("[Movies Sync] Movies updated: %s" % titles)

		self.updateProgress(60, line2="%i %s" % (len(movies), utilities.getString(1430)))

		#split movie list into chunks of 50
		chunked_movies = utilities.chunks([{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": movies[i]['movieid'], "playcount": movies[i]['plays']}, "id": i} for i in range(len(movies))], 50)
		i = 0
		x = float(len(chunked_movies))
		for chunk in chunked_movies:
			if self.isCanceled():
				return
			if self.simulate:
				Debug("[Movies Sync] %s" % str(chunk))
			else:
				utilities.xbmcJsonRequest(chunk)

			i = i + 1
			y = ((i / x) * 20) + 60
			self.updateProgress(int(y), line2=utilities.getString(1472))

		self.updateProgress(80, line2=utilities.getString(1473) % len(movies))

	def syncMovies(self):
		if not self.show_progress and self.sync_on_update and self.notify and self.notify_during_playback:
			notification('%s %s' % (utilities.getString(1400), utilities.getString(1402)), utilities.getString(1420)) #Sync started
		if self.show_progress and not self.run_silent:
			progress.create("%s %s" % (utilities.getString(1400), utilities.getString(1402)), line1=" ", line2=" ", line3=" ")

		xbmcMovies = self.xbmcLoadMovies()
		if not isinstance(xbmcMovies, list) and not xbmcMovies:
			Debug("[Movies Sync] XBMC movie list is empty, aborting movie Sync.")
			if self.show_progress and not self.run_silent:
				progress.close()
			return

		traktMovies = self.traktLoadMovies()
		if not isinstance(traktMovies, list):
			Debug("[Movies Sync] Error getting trakt.tv movie list, aborting movie Sync.")
			if self.show_progress and not self.run_silent:
				progress.close()
			return

		if utilities.getSettingAsBool('add_movies_to_trakt') and not self.isCanceled():
			traktMoviesToAdd = self.compareMovies(xbmcMovies, traktMovies)
			self.traktAddMovies(traktMoviesToAdd)
		
		if utilities.getSettingAsBool('trakt_movie_playcount') and not self.isCanceled():
			traktMoviesToUpdate = self.compareMovies(xbmcMovies, traktMovies, watched=True)
			self.traktUpdateMovies(traktMoviesToUpdate)

		if utilities.getSettingAsBool('xbmc_movie_playcount') and not self.isCanceled():
			xbmcMoviesToUpdate = self.compareMovies(traktMovies, xbmcMovies, watched=True, restrict=True)
			self.xbmcUpdateMovies(xbmcMoviesToUpdate)

		if utilities.getSettingAsBool('clean_trakt_movies') and not self.isCanceled():
			traktMoviesToRemove = self.compareMovies(traktMovies, xbmcMovies)
			self.traktRemoveMovies(traktMoviesToRemove)

		if not self.isCanceled() and self.show_progress and not self.run_silent:
			self.updateProgress(100, line1=utilities.getString(1431), line2=" ", line3=" ")
			progress.close()

		if not self.show_progress and self.sync_on_update and self.notify and self.notify_during_playback:
			notification('%s %s' % (utilities.getString(1400), utilities.getString(1402)), utilities.getString(1421)) #Sync complete
		
		Debug("[Movies Sync] Movies on trakt.tv (%d), movies in XBMC (%d)." % (len(traktMovies), self.countMovies(xbmcMovies)))
		Debug("[Movies Sync] Complete.")

	def syncCheck(self, media_type):
		if media_type == 'movies':
			return utilities.getSettingAsBool('add_movies_to_trakt') or utilities.getSettingAsBool('trakt_movie_playcount') or utilities.getSettingAsBool('xbmc_movie_playcount') or utilities.getSettingAsBool('clean_trakt_movies')
		else:
			return utilities.getSettingAsBool('add_episodes_to_trakt') or utilities.getSettingAsBool('trakt_episode_playcount') or utilities.getSettingAsBool('xbmc_episode_playcount') or utilities.getSettingAsBool('clean_trakt_episodes')

		return False

	def sync(self):
		Debug("[Sync] Starting synchronization with trakt.tv")

		if self.syncCheck('movies'):
			if self.library in ["all", "movies"]:
				self.syncMovies()
			else:
				Debug("[Sync] Movie sync is being skipped for this manual sync.")
		else:
			Debug("[Sync] Movie sync is disabled, skipping.")

		if self.syncCheck('episodes'):
			if self.library in ["all", "episodes"]:
				self.syncEpisodes()
			else:
				Debug("[Sync] Episode sync is being skipped for this manual sync.")
		else:
			Debug("[Sync] Episode sync is disabled, skipping.")

		Debug("[Sync] Finished synchronization with trakt.tv")
	
########NEW FILE########
__FILENAME__ = tagging
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import utilities as utils
import copy
from time import time
from traktapi import traktAPI

__addon__ = xbmcaddon.Addon("script.trakt")

TAG_PREFIX = "trakt.tv - "
PRIVACY_LIST = ['public', 'friends', 'private']

def isTaggingEnabled():
	return utils.getSettingAsBool('tagging_enable')
def isWatchlistsEnabled():
	return utils.getSettingAsBool('tagging_watchlists')
def isRatingsEnabled():
	return utils.getSettingAsBool('tagging_ratings')
def getMinRating():
	return utils.getSettingAsInt('tagging_ratings_min')

def tagToList(tag):
	return tag.replace(TAG_PREFIX, "", 1)
def listToTag(list):
	return "%s%s" % (TAG_PREFIX, list)
def ratingToTag(rating):
	return "%sRating: %s" % (TAG_PREFIX, rating)
def isTraktList(tag):
	return True if tag.startswith(TAG_PREFIX) else False

def hasTraktWatchlistTag(tags):
	watchlist_tag = False
	for tag in tags:
		if isTraktList(tag):
			_tag = tagToList(tag)
			if _tag.lower() == "watchlist":
				watchlist_tag = True
				break
	return watchlist_tag
def getTraktRatingTag(tags):
	for tag in tags:
		if isTraktList(tag):
			_tag = tagToList(tag)
			if _tag.lower().startswith("rating:"):
				return tag
	return None
def hasTraktRatingTag(tags):
	return not getTraktRatingTag(tags) is None
def isTraktRatingTag(tag):
	if isTraktList(tag):
		_tag = tagToList(tag)
		return _tag.lower().startswith("rating:")
	return False

def xbmcSetTags(id, type, title, tags):
	if not (utils.isMovie(type) or utils.isShow(type)):
		return

	req = None
	if utils.isMovie(type):
		req = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : id, "tag": tags}}
	elif utils.isShow(type):
		req = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetTVShowDetails", "params": {"tvshowid" : id, "tag": tags}}

	if utils.getSettingAsBool('simulate_tagging'):
		utils.Debug("[Tagger] %s" % str(req))
		return True
	else:
		result = utils.xbmcJsonRequest(req)
		if result == "OK":
			utils.Debug("[Tagger] XBMC tags for '%s' were updated with '%s'." % (title, str(tags)))
			return True

	return False

class Tagger():

	traktLists = None
	traktListData = None
	traktListsLast = 0

	def __init__(self, api=None):
		if api is None:
			api = traktAPI(loadSettings=False)
		self.traktapi = api
		self.updateSettings()

	def updateSettings(self):
		self._enabled = utils.getSettingAsBool('tagging_enable')
		self._watchlists = utils.getSettingAsBool('tagging_watchlists')
		self._ratings = utils.getSettingAsBool('tagging_ratings')
		self._ratingMin = utils.getSettingAsInt('tagging_ratings_min')
		self.simulate = utils.getSettingAsBool('simulate_tagging')
		if self.simulate:
			utils.Debug("[Tagger] Tagging is configured to be simulated.")

	def xbmcLoadData(self, tags=False):
		data = {'movies': [], 'tvshows': []}

		props = ['title', 'imdbnumber', 'year']
		if tags:
			props.append('tag')
		m = {'method': 'VideoLibrary.GetMovies', 'props': props}
		s = {'method': 'VideoLibrary.GetTVShows', 'props': props}
		params = {'movies': m, 'tvshows': s}

		for type in params:
			utils.Debug("[Tagger] Getting '%s' from XBMC." % type)
			xbmc_data = utils.xbmcJsonRequest({'jsonrpc': '2.0', 'id': 0, 'method': params[type]['method'], 'params': {'properties': params[type]['props']}})
			if not xbmc_data:
				utils.Debug("[Tagger] XBMC JSON request was empty.")
				return False

			if not type in xbmc_data:
				utils.Debug("[Tagger] Key '%s' not found." % type)
				return False

			data[type] = xbmc_data[type]
			utils.Debug("[Tagger] XBMC JSON Result: '%s'" % str(data[type]))

			db_field = 'tmdb_id' if type == 'movies' else 'tvdb_id'

			for item in data[type]:
				item['type'] = 'movie' if type == 'movies' else 'show'
				id = item['imdbnumber']
				item['imdb_id'] = id if id.startswith("tt") else ""
				item[db_field] = unicode(id) if id.isdigit() else ""
				del(item['imdbnumber'])
				del(item['label'])

		data['shows'] = data.pop('tvshows')
		self.xbmcData = data
		return True

	def xbmcBuildTagList(self):
		data = {}

		for type in ['movies', 'shows']:
			for index in range(len(self.xbmcData[type])):
				item = self.xbmcData[type][index]
				for tag in item['tag']:
					if isTraktList(tag):
						listName = tagToList(tag)
						if not listName in data:
							data[listName] = {'movies': [], 'shows': []}
						data[listName][type].append(index)

		return data

	def getTraktLists(self, force=False):
		if force or self.traktListData is None or self.traktLists is None or (time() - self.traktListsLast) > (60 * 10):
			utils.Debug("[Tagger] Getting lists from trakt.tv")
			data = self.traktapi.getUserLists()

			if not isinstance(data, list):
				utils.Debug("[Tagger] Invalid trakt.tv lists, possible error getting data from trakt.")
				return False

			lists = {}
			list_data = {}
			hidden_lists = utils.getSettingAsList('tagging_hidden_lists')

			for item in data:
				lists[item['name']] = item['slug']
				del(item['url'])
				list_data[item['slug']] = copy.deepcopy(item)
				list_data[item['slug']]['hide'] = item['slug'] in hidden_lists

			self.traktLists = lists
			self.traktListData = list_data
			self.traktListsLast = time()
		else:
			utils.Debug("[Tagger] Using cached lists.")

		return self.traktLists

	def getTraktListData(self):
		data = {}

		utils.Debug("[Tagger] Getting list data from trakt.tv")
		lists = self.getTraktLists(force=True)
		if not lists:
			utils.Debug("[Tagger] No lists at trakt.tv, nothing to retrieve.")
			return {}

		for listName in lists:
			slug = lists[listName]
			data[listName] = {'movies': [], 'shows': []}

			utils.Debug("[Tagger] Getting list data for list slug '%s'." % slug)
			listdata = self.traktapi.getUserList(slug)

			if not isinstance(listdata, dict):
				utils.Debug("[Tagger] Invalid trakt.tv list data, possible error getting data from trakt.")
				return None

			for item in listdata['items']:
				type = 'movies' if item['type'] == 'movie' else 'shows'
				f = utils.findMovie if type == 'movies' else utils.findShow

				i = f(item[item['type']], self.xbmcData[type], returnIndex=True)
				if not i is None:
					data[listName][type].append(i)

		return data

	def getTraktWatchlistData(self):
		data = {}

		utils.Debug("[Tagger] Getting watchlist data from trakt.tv")
		w = {}
		w['movies']	= self.traktapi.getWatchlistMovies()
		w['shows'] = self.traktapi.getWatchlistShows()

		if isinstance(w['movies'], list) and isinstance(w['shows'], list):
			data['Watchlist'] = {'movies': [], 'shows': []}

			for type in w:
				f = utils.findMovie if type == 'movies' else utils.findShow
				for item in w[type]:
					i = f(item, self.xbmcData[type], returnIndex=True)
					if not i is None:
						data['Watchlist'][type].append(i)

		else:
			utils.Debug("[Tagger] There was a problem getting your watchlists.")
			return None

		return data

	def getTraktRatingData(self):
		data = {}

		utils.Debug("[Tagger] Getting rating data from trakt.tv")
		r = {}
		r['movies'] = self.traktapi.getRatedMovies()
		r['shows'] = self.traktapi.getRatedShows()

		if isinstance(r['movies'], list) and isinstance(r['shows'], list):

			for i in range(self._ratingMin, 11):
				listName = "Rating: %s" % i
				data[listName] = {'movies': [], 'shows': []}

			for type in r:
				f = utils.findMovie if type == 'movies' else utils.findShow
				for item in r[type]:
					if item['rating_advanced'] >= self._ratingMin:
						i = f(item, self.xbmcData[type], returnIndex=True)
						if not i is None:
							listName = "Rating: %s" % item['rating_advanced']
							data[listName][type].append(i)

		else:
			utils.Debug("[Tagger] There was a problem getting your rated movies or shows.")
			return None

		return data

	def sanitizeTraktParams(self, data):
		newData = copy.deepcopy(data)
		for item in newData:
			if 'imdb_id' in item and not item['imdb_id']:
				del(item['imdb_id'])
			if 'tmdb_id' in item and not item['tmdb_id']:
				del(item['tmdb_id'])
			if 'tvdb_id' in item and not item['tvdb_id']:
				del(item['tvdb_id'])
			if 'tvshowid' in item:
				del(item['tvshowid'])
			if 'movieid' in item:
				del(item['movieid'])
			if 'tag' in item:
				del(item['tag'])
		return newData

	def isListOnTrakt(self, list):
		lists = self.getTraktLists()
		return list in lists

	def getSlug(self, list):
		if self.isListOnTrakt(list):
			return self.getTraktLists[list]
		return None

	def xbmcUpdateTags(self, data):
		chunked = utils.chunks([{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : movie, "tag": data['movies'][movie]}} for movie in data['movies']], 50)
		chunked.extend(utils.chunks([{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetTVShowDetails", "params": {"tvshowid" : show, "tag": data['shows'][show]}} for show in data['shows']], 50))
		for chunk in chunked:
			if self.simulate:
				utils.Debug("[Tagger] %s" % str(chunk))
			else:
				utils.xbmcJsonRequest(chunk)

	def traktListAddItem(self, list, data):
		if not list:
			utils.Debug("[Tagger] No list provided.")
			return

		if not data:
			utils.Debug("[Tagger] Nothing to add to trakt lists")
			return

		params = {}
		params['items'] = self.sanitizeTraktParams(data)

		if self.simulate:
			utils.Debug("[Tagger] '%s' adding '%s'" % (list, str(params)))
		else:
			if self.isListOnTrakt(list):
				slug = self.traktLists[list]
				params['slug'] = slug
			else:
				list_privacy = utils.getSettingAsInt('tagging_list_privacy')
				allow_shouts = utils.getSettingAsBool('tagging_list_allowshouts')

				utils.Debug("[Tagger] Creating new list '%s'" % list)
				result = self.traktapi.userListAdd(list, PRIVACY_LIST[list_privacy], allow_shouts=allow_shouts)

				if result and 'status' in result and result['status'] == 'success':
					slug = result['slug']
					params['slug'] = slug
					self.traktLists[list] = slug
				else:
					utils.Debug("[Tagger] There was a problem create the list '%s' on trakt.tv" % list)
					return

			utils.Debug("[Tagger] Adding to list '%s', items '%s'" % (list, str(params['items'])))
			self.traktapi.userListItemAdd(params)

	def traktListRemoveItem(self, list, data):
		if not list:
			utils.Debug("[Tagger] No list provided.")
			return

		if not data:
			utils.Debug("[Tagger] Nothing to remove from trakt list.")
			return

		if not self.isListOnTrakt(list):
			utils.Debug("[Tagger] Trying to remove items from non-existant list '%s'." % list)

		slug = self.traktLists[list]
		params = {'slug': slug}
		params['items'] = self.sanitizeTraktParams(data)

		if self.simulate:
			utils.Debug("[Tagger] '%s' removing '%s'" % (list, str(params)))
		else:
			self.traktapi.userListItemDelete(params)

	def updateWatchlist(self, data, remove=False):
		movie_params = []
		show_params = []

		for item in data:
			if utils.isMovie(item['type']):
				movie = {}
				movie['title'] = item['title']
				if 'imdb_id' in item:
					movie['imdb_id'] = item['imdb_id']
				if 'tmdb_id' in data:
					movie['tmdb_id'] = item['tmdb_id']
				movie['year'] = item['year']
				movie_params.append(movie)

			elif utils.isShow(item['type']):
				show = {}
				show['title'] = item['title']
				if 'imdb_id' in item:
					show['imdb_id'] = item['imdb_id']
				if 'tvdb_id' in item:
					show['tvdb_id'] = item['tvdb_id']
				show_params.append(show)

		if movie_params:
			params = {'movies': movie_params}
			if self.simulate:
				utils.Debug("[Tagger] Movie watchlist %s '%s'." % ("remove" if remove else "add", str(params)))

			else:
				if not remove:
					self.traktapi.watchlistAddMovies(params)
				else:
					self.traktapi.watchlistRemoveMovies(params)

		if show_params:
			params = {'shows': show_params}
			if self.simulate:
				utils.Debug("[Tagger] Show watchlist %s '%s'." % ("remove" if remove else "add", str(params)))

			else:
				if not remove:
					self.traktapi.watchlistAddShows(params)
				else:
					self.traktapi.watchlistRemoveShows(params)

	def isAborted(self):
		if xbmc.abortRequested:
			utils.Debug("[Tagger] XBMC abort requested, stopping.")
			return true

	def updateTagsFromTrakt(self):
		if not self._enabled:
			utils.Debug("[Tagger] Tagging is not enabled, aborting.")
			return

		utils.Debug("[Tagger] Starting List/Tag synchronization.")
		if utils.getSettingAsBool('tagging_notifications'):
			utils.notification(utils.getString(1201), utils.getString(1658))

		tStart = time()
		if not self.xbmcLoadData(tags=True):
			utils.Debug("[Tagger] Problem loading XBMC data, aborting.")
			utils.notification(utils.getString(1201), utils.getString(1662))
			return
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to load data from XBMC: %0.3f seconds." % tTaken)

		tStart = time()
		xbmc_lists = self.xbmcBuildTagList()
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to load build list from XBMC data: %0.3f seconds." % tTaken)

		if self.isAborted():
			return

		trakt_lists = {}

		tStart = time()
		trakt_lists = self.getTraktListData()
		if trakt_lists is None:
			utils.Debug("[Tagger] Problem getting list data, aborting.")
			utils.notification(utils.getString(1201), utils.getString(1663))
			return

		if self.isAborted():
			return

		if self._watchlists:
			watchlist = self.getTraktWatchlistData()
			if watchlist is None:
				utils.Debug("[Tagger] Problem getting watchlist data, aborting.")
				utils.notification(utils.getString(1201), utils.getString(1664))
				return
			trakt_lists['Watchlist'] = watchlist['Watchlist']

		if self.isAborted():
			return

		if self._ratings:
			ratings = self.getTraktRatingData()
			if ratings is None:
				utils.Debug("[Tagger] Can not continue with managing lists, aborting.")
				utils.notification(utils.getString(1201), utils.getString(1665))
				return
			trakt_lists = dict(trakt_lists, **ratings)

		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to load data from trakt.tv: %0.3f seconds." % tTaken)

		if self.isAborted():
			return

		tStart = time()
		c = 0
		tags = {'movies': {}, 'shows': {}}
		for listName in trakt_lists:
			for type in ['movies', 'shows']:
				for index in trakt_lists[listName][type]:
					if not index in tags[type]:
						tags[type][index] = []
						c = c + 1
					tags[type][index].append(listToTag(listName))
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to build xbmc tag list for (%d) items: %0.3f seconds." % (c, tTaken))

		tStart = time()
		xbmc_update = {'movies': [], 'shows': []}
		for listName in trakt_lists:
			if listName in xbmc_lists:
				for type in ['movies', 'shows']:
					s1 = set(trakt_lists[listName][type])
					s2 = set(xbmc_lists[listName][type])
					if not s1 == s2:
						xbmc_update[type].extend(list(s1.difference(s2)))
						xbmc_update[type].extend(list(s2.difference(s1)))
			else:
				xbmc_update['movies'].extend(trakt_lists[listName]['movies'])
				xbmc_update['shows'].extend(trakt_lists[listName]['shows'])

		for list_name in xbmc_lists:
			if not list_name in trakt_lists:
				xbmc_update['movies'].extend(xbmc_lists[listName]['movies'])
				xbmc_update['shows'].extend(xbmc_lists[listName]['shows'])
				
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to compare data: %0.3f seconds." % tTaken)

		sStart = time()
		old_tags = {'movies': {}, 'shows': {}}
		c = 0
		for type in ['movies', 'shows']:
			for item in self.xbmcData[type]:
				t = []
				for old_tag in item['tag']:
					if not isTraktList(old_tag):
						t.append(old_tag)
				id_field = 'movieid' if type == 'movies' else 'tvshowid'
				id = item[id_field]
				if t:
					old_tags[type][id] = t
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to build list of old tags for (%d) items: %0.3f seconds." % (c, tTaken))
		
		sStart = time()
		xbmcTags = {'movies': {}, 'shows': {}}
		c = 0
		for type in xbmcTags:
			xbmc_update[type] = list(set(xbmc_update[type]))
			for index in xbmc_update[type]:
				t = []
				if index in tags[type]:
					t = tags[type][index]
				if index in old_tags[type]:
					t.extend(old_tags[type][index])
				id_field = 'movieid' if type == 'movies' else 'tvshowid'
				id = self.xbmcData[type][index][id_field]
				xbmcTags[type][id] = t
				c = c + 1

		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to build list of changes for (%d) items: %0.3f seconds." % (c, tTaken))

		# update xbmc tags from trakt lists
		utils.Debug("[Tagger] Updating XBMC tags from trakt.tv list(s).")
		tStart = time()
		self.xbmcUpdateTags(xbmcTags)
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to update changed xbmc tags: %0.3f seconds." % tTaken)

		if utils.getSettingAsBool('tagging_notifications'):
			utils.notification(utils.getString(1201), utils.getString(1659))
		utils.Debug("[Tagger] Tags have been updated.")

	def manageLists(self):
		utils.notification(utils.getString(1201), utils.getString(1661))
		utils.Debug("[Tagger] Starting to manage lists.")

		tStart = time()
		if not self.xbmcLoadData():
			utils.Debug("[Tagger] Problem loading XBMC data, aborting.")
			utils.notification(utils.getString(1201), utils.getString(1662))
			return
		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to load data from XBMC: %0.3f seconds." % tTaken)

		selected = {}

		tStart = time()
		selected = self.getTraktListData()

		if selected is None:
			utils.Debug("[Tagger] Problem getting list data, aborting.")
			utils.notification(utils.getString(1201), utils.getString(1663))
			return

		if self._watchlists:
			watchlist = self.getTraktWatchlistData()
			if watchlist is None:
				utils.Debug("[Tagger] Problem getting watchlist data, aborting.")
				utils.notification(utils.getString(1201), utils.getString(1664))
				return
			selected['Watchlist'] = watchlist['Watchlist']

		tTaken = time() - tStart
		utils.Debug("[Tagger] Time to load data from trakt.tv: %0.3f seconds." % tTaken)

		d = traktManageListsDialog(lists=self.traktListData, xbmc_data=self.xbmcData, selected=selected)
		d.doModal()
		_button = d.button
		_dirty = d.dirty
		_newSelected = d.selected
		_listData = d.listData
		del d

		if _button == BUTTON_OK:
			if _dirty:
				newSelected = _newSelected

				tags = {'movies': {}, 'shows': {}}
				ratingTags = {'movies': {}, 'shows': {}}
				tagUpdates = {'movies': [], 'shows': []}
				traktUpdates = {}

				# apply changes and create new lists first.
				tStart = time()
				_lists_changed = []
				_lists_added = []
				keys_ignore = ['hide', 'slug', 'url']
				for slug in _listData:
					if not slug in self.traktListData:
						_lists_added.append(slug)
						continue
					for key in _listData[slug]:
						if key in keys_ignore:
							continue
						if not _listData[slug][key] == self.traktListData[slug][key]:
							_lists_changed.append(slug)
							break

				_old_hidden = [slug for slug in self.traktListData if self.traktListData[slug]['hide']]
				_new_hidden = [slug for slug in _listData if _listData[slug]['hide']]
				if not set(_new_hidden) == set(_old_hidden):
					utils.Debug("[Tagger] Updating hidden lists to '%s'." % str(_new_hidden))
					utils.setSettingFromList('tagging_hidden_lists', _new_hidden)

				if _lists_changed:
					for slug in _lists_changed:
						params = {}
						params['slug'] = slug
						for key in _listData[slug]:
							if key in keys_ignore:
								continue
							params[key] = _listData[slug][key]

						if self.simulate:
							utils.Debug("[Tagger] Update list '%s' with params: %s" % (slug, str(params)))
						else:
							result = self.traktapi.userListUpdate(params)
							if result and 'status' in result and result['status'] == 'success':
								new_slug = result['slug']
								if not slug == new_slug:
									new_list_name = _listData[slug]['name']
									old_list_name = self.traktListData[slug]['name']
									self.traktLists[new_list_name] = new_slug
									del(self.traktLists[old_list_name])
									selected[new_list_name] = selected.pop(old_list_name)
									_listData[new_slug] = _listData.pop(slug)
									_listData[new_slug]['slug'] = new_slug

				if _lists_added:
					for list_name in _lists_added:
						list_data = _listData[list_name]
						result = self.traktapi.userListAdd(list_name, list_data['privacy'], list_data['description'], list_data['allow_shouts'], list_data['show_numbers'])

						if result and 'status' in result and result['status'] == 'success':
							slug = result['slug']
							self.traktLists[list_name] = slug
							_listData[slug] = _listData.pop(list_name)
						else:
							utils.Debug("[Tagger] There was a problem create the list '%s' on trakt.tv" % list)
					
				tTaken = time() - tStart
				utils.Debug("[Tagger] Time to update trakt.tv list settings: %0.3f seconds." % tTaken)

				# build all tags
				tStart = time()
				c = 0
				for listName in newSelected:
					for type in ['movies', 'shows']:
						for index in newSelected[listName][type]:
							if not index in tags[type]:
								tags[type][index] = []
							tags[type][index].append(listToTag(listName))
							c = c + 1
				tTaken = time() - tStart
				utils.Debug("[Tagger] Time to build xbmc tag list for (%d) items: %0.3f seconds." % (c, tTaken))

				# check if we rating tags are enabled
				c = 0
				if self._ratings:
					tStart = time()

					ratings = self.getTraktRatingData()
					if ratings is None:
						utils.Debug("[Tagger] Can not continue with managing lists, aborting.")
						utils.notification(utils.getString(1201), utils.getString(1665))
						return

					c = 0
					for listName in ratings:
						for type in ['movies', 'shows']:
							for index in ratings[listName][type]:
								if not index in ratingTags[type]:
									ratingTags[type][index] = []
								ratingTags[type][index].append(listToTag(listName))
								c = c + 1

					tTaken = time() - tStart
					utils.Debug("[Tagger] Time to get and build rating tag list for (%d) items: %0.3f seconds." % (c, tTaken))

				# build lists of changes
				tStart = time()
				for listName in newSelected:
					if listName in selected:
						for type in ['movies', 'shows']:
							s1 = set(newSelected[listName][type])
							s2 = set(selected[listName][type])
							if not s1 == s2:
								toAdd = list(s1.difference(s2))
								toRemove = list(s2.difference(s1))
								tagUpdates[type].extend(toAdd)
								tagUpdates[type].extend(toRemove)
								if not listName in traktUpdates:
									traktUpdates[listName] = {'movies': {'add': [], 'remove': []}, 'shows': {'add': [], 'remove': []}}
								traktUpdates[listName][type] = {'add': toAdd, 'remove': toRemove}
					else:
						tagUpdates['movies'].extend(newSelected[listName]['movies'])
						tagUpdates['shows'].extend(newSelected[listName]['shows'])
						traktUpdates[listName] = {}
						traktUpdates[listName]['movies'] = {'add': newSelected[listName]['movies'], 'remove': []}
						traktUpdates[listName]['shows'] = {'add': newSelected[listName]['shows'], 'remove': []}

				# build xmbc update list
				xbmcTags = {'movies': {}, 'shows': {}}
				c = 0
				for type in xbmcTags:
					tagUpdates[type] = list(set(tagUpdates[type]))
					f = utils.getMovieDetailsFromXbmc if type == 'movies' else utils.getShowDetailsFromXBMC
					for index in tagUpdates[type]:
						t = []
						if index in tags[type]:
							t = tags[type][index]
						if index in ratingTags[type]:
							t.extend(ratingTags[type][index])
						id_field = 'movieid' if type == 'movies' else 'tvshowid'
						id = self.xbmcData[type][index][id_field]

						result = f(id, ['tag'])
						for old_tag in result['tag']:
							if not isTraktList(old_tag):
								t.append(old_tag)

						xbmcTags[type][id] = t
						c = c + 1

				tTaken = time() - tStart
				utils.Debug("[Tagger] Time to build list of changes for (%d) items: %0.3f seconds." % (c, tTaken))

				# update tags in xbmc
				tStart = time()
				self.xbmcUpdateTags(xbmcTags)
				tTaken = time() - tStart
				utils.Debug("[Tagger] Time to update changed xbmc tags: %0.3f seconds." % tTaken)

				# update trakt.tv
				tStart = time()
				for listName in traktUpdates:
					data = {'add': [], 'remove': []}
					for type in ['movies', 'shows']:
						data['add'].extend([self.xbmcData[type][index] for index in traktUpdates[listName][type]['add']])
						data['remove'].extend([self.xbmcData[type][index] for index in traktUpdates[listName][type]['remove']])

					if data['add']:
						if listName.lower() == 'watchlist':
							self.updateWatchlist(data['add'])
						else:
							self.traktListAddItem(listName, data['add'])
					if data['remove']:
						if listName.lower() == 'watchlist':
							self.updateWatchlist(data['remove'], remove=True)
						else:
							self.traktListRemoveItem(listName, data['remove'])

				tTaken = time() - tStart
				utils.Debug("[Tagger] Time to update trakt.tv with changes: %0.3f seconds." % tTaken)

				utils.Debug("[Tagger] Finished managing lists.")
				utils.notification(utils.getString(1201), utils.getString(1666))

				self.traktLists = None
				self.traktListData = None

	def itemLists(self, data):

		lists = self.getTraktLists()

		if not isinstance(lists, dict):
			utils.Debug("[Tagger] Error getting lists from trakt.tv.")
			return

		d = traktItemListsDialog(list_data=self.traktListData, data=data)
		d.doModal()
		if not d.selectedLists is None:
			non_trakt_tags = [tag for tag in data['tag'] if not isTraktList(tag)]
			old_trakt_tags = [tagToList(tag) for tag in data['tag'] if isTraktList(tag)]
			new_trakt_tags = d.selectedLists

			if set(old_trakt_tags) == set(new_trakt_tags):
				utils.Debug("[Tagger] '%s' had no changes made to the lists it belongs to." % data['title'])

			else:
				s1 = set(old_trakt_tags)
				s2 = set(new_trakt_tags)

				_changes = {}
				_changes['add'] = list(s2.difference(s1))
				_changes['remove'] = list(s1.difference(s2))
				
				for _op in _changes:
					debug_str = "[Tagger] Adding '%s' to '%s'." if _op == 'add' else "[Tagger] Removing: '%s' from '%s'."
					f = self.traktListAddItem if _op == 'add' else self.traktListRemoveItem
					for _list in _changes[_op]:
						if _list.lower() == "watchlist":
							utils.Debug(debug_str % (data['title'], _list))
							remove = _op == 'remove'
							self.updateWatchlist([data], remove=remove)
						elif _list.lower().startswith("rating:"):
							pass
						else:
							utils.Debug(debug_str % (data['title'], _list))
							f(_list, [data])

				tags = non_trakt_tags
				tags.extend([listToTag(l) for l in new_trakt_tags])

				s = utils.getFormattedItemName(data['type'], data)
				id_field = "movieid" if data['type'] == 'movie' else "tvshowid"
				if xbmcSetTags(data[id_field], data['type'], s, tags):
					utils.notification(utils.getString(1201), utils.getString(1657) % s)

		else:
			utils.Debug("[Tagger] Dialog was cancelled.")

		del d

	def manualAddToList(self, list, data):
		if list.lower().startswith("rating:"):
			utils.Debug("[Tagger] '%s' is a reserved list name." % list)
			return

		tag = listToTag(list)
		if tag in data['tag']:
			utils.Debug("[Tagger] '%s' is already in the list '%s'." % (data['title'], list))
			return

		if list.lower() == "watchlist":
			utils.Debug("[Tagger] Adding '%s' to Watchlist." % data['title'])
			self.updateWatchlist([data])
		else:
			utils.Debug("[Tagger] Adding '%s' to '%s'." % (data['title'], list))
			self.traktListAddItem(list, [data])

		data['tag'].append(tag)

		s = utils.getFormattedItemName(data['type'], data)
		id_field = "movieid" if data['type'] == 'movie' else "tvshowid"
		if xbmcSetTags(data[id_field], data['type'], s, data['tag']):
			utils.notification(utils.getString(1201), utils.getString(1657) % s)

	def manualRemoveFromList(self, list, data):
		if list.lower().startswith("rating:"):
			utils.Debug("[Tagger] '%s' is a reserved list name." % list)
			return

		tag = listToTag(list)
		if not tag in data['tag']:
			utils.Debug("[Tagger] '%s' is not in the list '%s'." % (data['title'], list))
			return

		if list.lower() == "watchlist":
			utils.Debug("[Tagger] Removing: '%s' from Watchlist." % data['title'])
			self.updateWatchlist([data], remove=True)
		else:
			utils.Debug("[Tagger] Removing: '%s' from '%s'." % (data['title'], list))
			self.traktListRemoveItem(list, [data])

		data['tag'].remove(tag)

		s = utils.getFormattedItemName(data['type'], data)
		id_field = "movieid" if data['type'] == 'movie' else "tvshowid"
		if xbmcSetTags(data[id_field], data['type'], s, data['tag']):
			utils.notification(utils.getString(1201), utils.getString(1657) % s)

TRAKT_LISTS				= 4
GROUP_LIST_SETTINGS		= 100
LIST_PRIVACY_SETTING	= 111
LIST_OTHER_SETTINGS		= 141
BUTTON_EDIT_DESC		= 113
BUTTON_RENAME			= 114
BUTTON_ADD_LIST			= 15
BUTTON_OK				= 16
BUTTON_CANCEL			= 17
LABEL					= 25
ACTION_PREVIOUS_MENU2	= 92
ACTION_PARENT_DIR		= 9
ACTION_PREVIOUS_MENU	= 10 
ACTION_SELECT_ITEM		= 7
ACTION_MOUSE_LEFT_CLICK	= 100
ACTION_CLOSE_LIST		= [ACTION_PREVIOUS_MENU2, ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU]
ACTION_ITEM_SELECT		= [ACTION_SELECT_ITEM, ACTION_MOUSE_LEFT_CLICK]

class traktItemListsDialog(xbmcgui.WindowXMLDialog):

	selectedLists = None

	def __new__(cls, list_data, data):
		return super(traktItemListsDialog, cls).__new__(cls, "traktListDialog.xml", __addon__.getAddonInfo('path'), list_data=list_data, data=data) 

	def __init__(self, *args, **kwargs):
		data = kwargs['data']
		list_data = kwargs['list_data']
		self.data = data
		self.hasRating = False
		self.tags = {}
		for tag in data['tag']:
			if isTraktList(tag):
				t = tagToList(tag)
				if t.startswith("Rating:"):
					self.hasRating = True
					self.ratingTag = t
					continue
				self.tags[t] = True
		utils.Debug(str(list_data))
		for slug in list_data:
			list_name = list_data[slug]['name']
			hidden = list_data[slug]['hide']
			if not hidden and not list_name in self.tags:
				self.tags[list_name] = False

		if (not 'Watchlist' in self.tags) and utils.getSettingAsBool('tagging_watchlists'):
			self.tags['Watchlist'] = False

		super(traktItemListsDialog, self).__init__()

	def onInit(self):
		grp = self.getControl(GROUP_LIST_SETTINGS)
		grp.setEnabled(False)
		grp.setVisible(False)
		self.setInfoLabel(utils.getFormattedItemName(self.data['type'], self.data))
		self.list = self.getControl(TRAKT_LISTS)
		self.populateList()
		self.setFocus(self.list)

	def onAction(self, action):
		if not action.getId() in ACTION_ITEM_SELECT:
			if action in ACTION_CLOSE_LIST:
				self.close()
		if action in ACTION_ITEM_SELECT:
			cID = self.getFocusId() 
			if cID == TRAKT_LISTS:
				item = self.list.getSelectedItem()
				selected = not item.isSelected()
				item.select(selected)
				self.tags[item.getLabel()] = selected

	def onClick(self, control):
		if control == BUTTON_ADD_LIST:
			keyboard = xbmc.Keyboard("", utils.getString(1654))
			keyboard.doModal()
			if keyboard.isConfirmed() and keyboard.getText():
				new_list = keyboard.getText().strip()
				if new_list:
					if new_list.lower() == "watchlist" or new_list.lower().startswith("rating:"):
						utils.Debug("[Tagger] Dialog: Tried to add a reserved list name '%s'." % new_list)
						utils.notification(utils.getString(1650), utils.getString(1655) % new_list)
						return

					if new_list not in self.tags:
						utils.Debug("[Tagger] Dialog: Adding list '%s', and selecting it." % new_list)
					else:
						utils.Debug("[Tagger] Dialog: '%s' already in list, selecting it." % new_list)
						utils.notification(utils.getString(1650), utils.getString(1656) % new_list)

					self.tags[new_list] = True
					self.populateList()

		elif control == BUTTON_OK:
			data = []
			for i in range(0, self.list.size()):
				item = self.list.getListItem(i)
				if item.isSelected():
					data.append(item.getLabel())
			if self.hasRating:
				data.append(self.ratingTag)
			self.selectedLists = data
			self.close()

		elif control == BUTTON_CANCEL:
			self.close()

	def setInfoLabel(self, text):
		pl = self.getControl(LABEL)
		pl.setLabel(text)

	def populateList(self):
		self.list.reset()
		if 'Watchlist' in self.tags:
			item = xbmcgui.ListItem('Watchlist')
			item.select(self.tags['Watchlist'])
			self.list.addItem(item)

		for tag in sorted(self.tags.iterkeys()):
			if tag.lower() == "watchlist":
				continue
			item = xbmcgui.ListItem(tag)
			item.select(self.tags[tag])
			self.list.addItem(item)

class traktManageListsDialog(xbmcgui.WindowXMLDialog):

	dirty = False
	button = None
	selectedList = None

	def __new__(cls, lists, xbmc_data, selected):
		return super(traktManageListsDialog, cls).__new__(cls, "traktListDialog.xml", __addon__.getAddonInfo('path'), lists=lists, xbmc_data=xbmc_data, selected=selected)

	def __init__(self, *args, **kwargs):
		self.listData = copy.deepcopy(kwargs['lists'])
		self.lists = {}
		for l in self.listData:
			list_data = self.listData[l]
			self.lists[list_data['name']] = l
		self.xbmc_data = kwargs['xbmc_data']
		self.movies = self.xbmc_data['movies']
		self.movieList = {}
		for i in range(len(self.movies)):
			t = "%s (%d)" % (self.movies[i]['title'], self.movies[i]['year'])
			self.movieList[t] = i

		self.shows = self.xbmc_data['shows']
		self.showList = {}
		for i in range(len(self.shows)):
			self.showList[self.shows[i]['title']] = i

		self.selected = copy.deepcopy(kwargs['selected'])

		super(traktManageListsDialog, self).__init__()

	def onInit(self):
		l = self.getControl(LIST_PRIVACY_SETTING)
		lang = utils.getString
		privacy_settings = [lang(1671), lang(1672), lang(1673)]
		for i in range(len(privacy_settings)):
			l.addItem(self.newListItem(privacy_settings[i], id=PRIVACY_LIST[i]))

		l = self.getControl(LIST_OTHER_SETTINGS)
		other_settings = [lang(1674), lang(1675), lang(1676)]
		keys = ["allow_shouts", "show_numbers", "hide"]
		for i in range(len(other_settings)):
			l.addItem(self.newListItem(other_settings[i], id=keys[i]))

		self.list = self.getControl(TRAKT_LISTS)
		self.setInfoLabel(utils.getString(1660))
		self.level = 1
		self.populateLists()
		self.setFocus(self.list)

	def onAction(self, action):
		if not action.getId() in ACTION_ITEM_SELECT:
			if action in ACTION_CLOSE_LIST:
				if self.level > 1:
					self.goBackLevel()
					return
				else:
					self.close()

		if action in ACTION_ITEM_SELECT:
			cID = self.getFocusId() 
			if cID == TRAKT_LISTS:
				item = self.list.getSelectedItem()

				if item.getLabel() == "..":
					self.goBackLevel()
					return

				if self.level == 1:
					self.selectedList = item.getLabel()
					self.setInfoLabel(item.getLabel())
					self.setAddListEnabled(False)
					self.level = 2
					self.populateTypes()
					utils.Debug("[Tagger] Dialog: Selected '%s' moving to level 2." % self.selectedList)

				elif self.level == 2:
					self.mediaType = "movies" if item.getLabel() == "Movies" else "shows"
					self.setInfoLabel("%s - %s" % (self.selectedList, item.getLabel()))
					utils.Debug("[Tagger] Dialog: Selected '%s' moving to level 3." % item.getLabel())
					self.level = 3
					self.populateItems(self.mediaType)

				elif self.level == 3:
					selected = item.isSelected()
					id = int(item.getProperty('id'))
					if selected:
						self.selected[self.selectedList][self.mediaType].remove(id)
					else:
						self.selected[self.selectedList][self.mediaType].append(id)
					self.dirty = True
					item.select(not selected)
					s = "removing from" if selected else "adding to"
					utils.Debug("[Tagger] Dialog: Selected '%s' [%s] %s '%s'." % (item.getLabel(), item.getProperty('id'), s, self.selectedList))

			elif cID == LIST_PRIVACY_SETTING:
				self.dirty = True
				l = self.getControl(cID)
				for i in range(0, l.size()):
					item = l.getListItem(i)
					item.select(False)
				item = l.getSelectedItem()
				item.select(True)
				key = item.getProperty('id')
				list_slug = self.lists[self.selectedList]
				list_data = self.listData[list_slug]
				old_privacy = list_data['privacy']
				list_data['privacy'] = key
				utils.Debug("[Tagger] Dialog: Changing privacy from '%s' to '%s' for '%s'." % (old_privacy, key, self.selectedList))

			elif cID == LIST_OTHER_SETTINGS:
				self.dirty = True
				l = self.getControl(cID)
				item = l.getSelectedItem()
				selected = not item.isSelected()
				item.select(selected)
				key = item.getProperty('id')
				list_slug = self.lists[self.selectedList]
				list_data = self.listData[list_slug]
				list_data[key] = selected
				utils.Debug("[Tagger] Dialog: Changing %s for '%s' to '%s'" % (key, self.selectedList, str(selected)))

	def getKeyboardInput(self, title="", default=""):
		kbd = xbmc.Keyboard(default, title)
		kbd.doModal()
		if kbd.isConfirmed() and kbd.getText():
			return kbd.getText().strip()
		return None

	def goBackLevel(self):
		if self.level == 1:
			pass
		elif self.level == 2:
			self.setAddListEnabled(True)
			self.setInfoLabel(utils.getString(1660))
			self.level = 1
			self.populateLists()
			utils.Debug("[Tagger] Dialog: Going back a level, to level 1.")
		elif self.level == 3:
			self.setInfoLabel(self.selectedList)
			self.level = 2
			self.populateTypes()
			utils.Debug("[Tagger] Dialog: Going back a level, to level 2.")

	def onClick(self, control):
		self.button = control
		if control == BUTTON_ADD_LIST:
			list = self.getKeyboardInput(title=utils.getString(1654))
			if list:
				if list.lower() == "watchlist" or list.lower().startswith("rating:"):
					utils.Debug("[Tagger] Dialog: Tried to add a reserved list name '%s'." % list)
					utils.notification(utils.getString(1650), utils.getString(1655) % list)
					return
				if list not in self.lists:
					utils.Debug("[Tagger] Dialog: Adding list '%s'." % list)
					self.lists[list] = list
					self.selected[list] = {'movies': [], 'shows': []}
					data = {}
					data['name'] = list
					data['slug'] = list
					list_privacy = utils.getSettingAsInt('tagging_list_privacy')
					data['privacy'] = PRIVACY_LIST[list_privacy]
					data['allow_shouts'] = utils.getSettingAsBool('tagging_list_allowshouts')
					data['show_numbers'] = False
					data['hide'] = False
					data['description'] = ""
					self.listData[list] = data
					self.populateLists()
				else:
					utils.Debug("[Tagger] Dialog: '%s' already in list." % list)
					utils.notification(utils.getString(1650), utils.getString(1656) % list)

		elif control == BUTTON_EDIT_DESC:
			list_slug = self.lists[self.selectedList]
			list_data = self.listData[list_slug]
			new_description = self.getKeyboardInput(title=utils.getString(1669), default=list_data['description'])
			if new_description:
				utils.Debug("[Tagger] Dialog: Setting new description for list '%s', '%s'." % (self.selectedList, new_description))
				self.dirty = True
				list_data['description'] = new_description

		elif control == BUTTON_RENAME:
			list_slug = self.lists[self.selectedList]
			list_data = self.listData[list_slug]
			new_name = self.getKeyboardInput(title=utils.getString(1670), default=self.selectedList)
			if new_name:
				if new_name.lower() == "watchlist" or new_name.lower().startswith("rating:"):
					utils.Debug("[Tagger] Dialog: Tried to rename '%s' to a reserved list name '%s'." % (self.selectedList, new_name))
					utils.notification(utils.getString(1650), utils.getString(1655) % new_name)
					return
				
				if new_name in self.lists:
					utils.Debug("[Tagger] Dialog: Already contains '%s'." % new_name)
					utils.notification(utils.getString(1650), utils.getString(1677) % new_name)
					return
				
				old_name = self.selectedList
				self.selectedList = new_name
				list_data['name'] = new_name
				self.setInfoLabel(new_name)
				self.lists[new_name] = self.lists.pop(old_name)
				self.selected[new_name] = self.selected.pop(old_name)
				self.dirty = True
				utils.Debug("[Tagger] Dialog: Renamed '%s' to '%s'." % (old_name, new_name))

		elif control in [BUTTON_OK, BUTTON_CANCEL]:
			self.close()

	def setAddListEnabled(self, enabled):
		btn = self.getControl(BUTTON_ADD_LIST)
		btn.setEnabled(enabled)
	
	def setListEditGroupEnabled(self, enabled):
		new_height = 138 if enabled else 380
		self.list.setHeight(new_height)
		grp = self.getControl(GROUP_LIST_SETTINGS)
		grp.setEnabled(enabled)
		grp.setVisible(enabled)
		d = {'public': 0, 'friends': 1, 'private': 2}

		if enabled:
			list_slug = self.lists[self.selectedList]
			list_data = self.listData[list_slug]
			l = self.getControl(LIST_PRIVACY_SETTING)
			for i in range(0, l.size()):
				item = l.getListItem(i)
				item.select(True if d[list_data['privacy']] == i else False)

			l = self.getControl(LIST_OTHER_SETTINGS)
			item = l.getListItem(0)
			item.select(list_data['allow_shouts'])
			item = l.getListItem(1)
			item.select(list_data['show_numbers'])
			item = l.getListItem(2)
			item.select(list_data['hide'])
	
	def newListItem(self, label, selected=False, *args, **kwargs):
		item = xbmcgui.ListItem(label)
		item.select(selected)
		for key in kwargs:
			item.setProperty(key, str(kwargs[key]))
		return item
	
	def setInfoLabel(self, text):
		pl = self.getControl(LABEL)
		pl.setLabel(text)

	def populateLists(self):
		self.list.reset()
		self.setListEditGroupEnabled(False)
		if utils.getSettingAsBool('tagging_watchlists'):
			self.list.addItem(self.newListItem("Watchlist"))

		selected_item = 0
		sorted_lists = sorted(self.lists.iterkeys())
		if "Watchlist" in sorted_lists:
			sorted_lists.remove("Watchlist")
		for index in range(len(sorted_lists)):
			if sorted_lists[index] == self.selectedList:
				selected_item = index + 1
			self.list.addItem(self.newListItem(sorted_lists[index]))
		self.list.selectItem(selected_item)

		self.setFocus(self.list)

	def populateTypes(self):
		self.list.reset()
		if not self.selectedList.lower() == "watchlist":
			self.setListEditGroupEnabled(True)
		items = ["..", "Movies", "TV Shows"]
		for l in items:
			self.list.addItem(self.newListItem(l))

		self.setFocus(self.list)

	def populateItems(self, type):
		self.list.reset()
		self.setListEditGroupEnabled(False)
		self.list.addItem("..")

		items = None
		if type == "movies":
			items = self.movieList
		else:
			items = self.showList

		for title in sorted(items.iterkeys()):
			selected = True if items[title] in self.selected[self.selectedList][type] else False
			self.list.addItem(self.newListItem(title, selected=selected, id=str(items[title])))

		self.setFocus(self.list)
########NEW FILE########
__FILENAME__ = traktapi
# -*- coding: utf-8 -*-
#

import xbmc
import xbmcaddon
import xbmcgui
import time, socket
import math
import urllib2
import base64

from utilities import Debug, notification, getSetting, getSettingAsBool, getSettingAsInt, getString, setSetting
from urllib2 import Request, urlopen, HTTPError, URLError
from httplib import HTTPException, BadStatusLine

try:
	import simplejson as json
except ImportError:
	import json

try:
	from hashlib import sha1
except ImportError:
	from sha import new as sha1

# read settings
__addon__ = xbmcaddon.Addon('script.trakt')
__addonversion__ = __addon__.getAddonInfo('version')

class traktError(Exception):
	def __init__(self, value, code=None):
		self.value = value
		if code:
			self.code = code
	def __str__(self):
		return repr(self.value)

class traktAuthProblem(traktError): pass
class traktServerBusy(traktError): pass
class traktUnknownError(traktError): pass
class traktNotFoundError(traktError): pass
class traktNetworkError(traktError):
	def __init__(self, value, timeout):
		super(traktNetworkError, self).__init__(value)
		self.timeout = timeout

class traktAPI(object):

	__apikey = "b6135e0f7510a44021fac8c03c36c81a17be35d9"
	__baseURL = "https://api.trakt.tv"
	__username = ""
	__password = ""

	def __init__(self, loadSettings=False):
		Debug("[traktAPI] Initializing.")

		self.__username = getSetting('username')
		self.__password = sha1(getSetting('password')).hexdigest()

		self.settings = None
		if loadSettings and self.testAccount():
			self.getAccountSettings()

	def __getData(self, url, args, timeout=60):
		data = None
		try:
			Debug("[traktAPI] __getData(): urllib2.Request(%s)" % url)

			if args == None:
				req = Request(url)
			else:
				req = Request(url, args)

			Debug("[traktAPI] __getData(): urllib2.urlopen()")
			t1 = time.time()
			response = urlopen(req, timeout=timeout)
			t2 = time.time()

			Debug("[traktAPI] __getData(): response.read()")
			data = response.read()

			Debug("[traktAPI] __getData(): Response Code: %i" % response.getcode())
			Debug("[traktAPI] __getData(): Response Time: %0.2f ms" % ((t2 - t1) * 1000))
			Debug("[traktAPI] __getData(): Response Headers: %s" % str(response.info().dict))

		except BadStatusLine, e:
			raise traktUnknownError("BadStatusLine: '%s' from URL: '%s'" % (e.line, url)) 
		except IOError, e:
			if hasattr(e, 'code'): # error 401 or 503, possibly others
				# read the error document, strip newlines, this will make an html page 1 line
				error_data = e.read().replace("\n", "").replace("\r", "")

				if e.code == 401: # authentication problem
					raise traktAuthProblem(error_data)
				elif e.code == 503: # server busy problem
					raise traktServerBusy(error_data)
				else:
					try:
						_data = json.loads(error_data)
						if 'status' in _data:
							data = error_data
					except ValueError:
						raise traktUnknownError(error_data, e.code)

			elif hasattr(e, 'reason'): # usually a read timeout, or unable to reach host
				raise traktNetworkError(str(e.reason), isinstance(e.reason, socket.timeout))

			else:
				raise traktUnknownError(e.message)

		return data
	
	# make a JSON api request to trakt
	# method: http method (GET or POST)
	# req: REST request (ie '/user/library/movies/all.json/%%API_KEY%%/%%USERNAME%%')
	# args: arguments to be passed by POST JSON (only applicable to POST requests), default:{}
	# returnStatus: when unset or set to false the function returns None upon error and shows a notification,
	#	when set to true the function returns the status and errors in ['error'] as given to it and doesn't show the notification,
	#	use to customise error notifications
	# silent: default is True, when true it disable any error notifications (but not debug messages)
	# passVersions: default is False, when true it passes extra version information to trakt to help debug problems
	# hideResponse: used to not output the json response to the log
	def traktRequest(self, method, url, args=None, returnStatus=False, returnOnFailure=False, silent=True, passVersions=False, hideResponse=False):
		raw = None
		data = None
		jdata = {}
		retries = getSettingAsInt('retries')

		if args is None:
			args = {}

		if not (method == 'POST' or method == 'GET'):
			Debug("[traktAPI] traktRequest(): Unknown method '%s'." % method)
			return None
		
		if method == 'POST':
			# debug log before username and sha1hash are injected
			Debug("[traktAPI] traktRequest(): Request data: '%s'." % str(json.dumps(args)))
			
			# inject username/pass into json data
			args['username'] = self.__username
			args['password'] = self.__password
			
			# check if plugin version needs to be passed
			if passVersions:
				args['plugin_version'] = __addonversion__
				args['media_center_version'] = xbmc.getInfoLabel('system.buildversion')
				args['media_center_date'] = xbmc.getInfoLabel('system.builddate')
			
			# convert to json data
			jdata = json.dumps(args)

		Debug("[traktAPI] traktRequest(): Starting retry loop, maximum %i retries." % retries)
		
		# start retry loop
		for i in range(retries):	
			Debug("[traktAPI] traktRequest(): (%i) Request URL '%s'" % (i, url))

			# check if we are closing
			if xbmc.abortRequested:
				Debug("[traktAPI] traktRequest(): (%i) xbmc.abortRequested" % i)
				break

			try:
				# get data from trakt.tv
				raw = self.__getData(url, jdata)
			except traktError, e:
				if isinstance(e, traktServerBusy):
					Debug("[traktAPI] traktRequest(): (%i) Server Busy (%s)" % (i, e.value))
					xbmc.sleep(5000)
				elif isinstance(e, traktAuthProblem):
					Debug("[traktAPI] traktRequest(): (%i) Authentication Failure (%s)" % (i, e.value))
					setSetting('account_valid', False)
					notification('trakt', getString(1110))
					return
				elif isinstance(e, traktNetworkError):
					Debug("[traktAPI] traktRequest(): (%i) Network error: %s" % (i, e.value))
					if e.timeout:
						notification('trakt', getString(1108) + " (timeout)") # can't connect to trakt
					xbmc.sleep(5000)
				elif isinstance(e, traktUnknownError):
					Debug("[traktAPI] traktRequest(): (%i) Other problem (%s)" % (i, e.value))
				else:
					pass

				xbmc.sleep(1000)
				continue

			# check if we are closing
			if xbmc.abortRequested:
				Debug("[traktAPI] traktRequest(): (%i) xbmc.abortRequested" % i)
				break

			# check that returned data is not empty
			if not raw:
				Debug("[traktAPI] traktRequest(): (%i) JSON Response empty" % i)
				xbmc.sleep(1000)
				continue

			try:
				# get json formatted data	
				data = json.loads(raw)
				if hideResponse:
					Debug("[traktAPI] traktRequest(): (%i) JSON response recieved, response not logged" % i)
				else:
					Debug("[traktAPI] traktRequest(): (%i) JSON response: '%s'" % (i, str(data)))
			except ValueError:
				# malformed json response
				Debug("[traktAPI] traktRequest(): (%i) Bad JSON response: '%s'" % (i, raw))
				if not silent:
					notification('trakt', getString(1109) + ": Bad response from trakt") # Error
				
			# check for the status variable in JSON data
			if data and 'status' in data:
				if data['status'] == 'success':
					break
				elif returnOnFailure and data['status'] == 'failure':
					Debug("[traktAPI] traktRequest(): Return on error set, breaking retry.")
					break
				elif 'error' in data and data['status'] == 'failure':
					Debug("[traktAPI] traktRequest(): (%i) JSON Error '%s' -> '%s'" % (i, data['status'], data['error']))
					xbmc.sleep(1000)
					continue
				else:
					pass

			# check to see if we have data, an empty array is still valid data, so check for None only
			if not data is None:
				Debug("[traktAPI] traktRequest(): Have JSON data, breaking retry.")
				break

			xbmc.sleep(500)
		
		# handle scenario where all retries fail
		if data is None:
			Debug("[traktAPI] traktRequest(): JSON Request failed, data is still empty after retries.")
			return None
		
		if 'status' in data:
			if data['status'] == 'failure':
				Debug("[traktAPI] traktRequest(): Error: %s" % str(data['error']))
				if returnStatus or returnOnFailure:
					return data
				if not silent:
					notification('trakt', getString(1109) + ": " + str(data['error'])) # Error
				return None
			elif data['status'] == 'success':
				Debug("[traktAPI] traktRequest(): JSON request was successful.")

		return data

	# helper for onSettingsChanged
	def updateSettings(self):
	
		_username = getSetting('username')
		_password = sha1(getSetting('password')).hexdigest()
		
		if not ((self.__username == _username) and (self.__password == _password)):
			self.__username = _username
			self.__password = _password
			self.testAccount(force=True)

	# http://api.trakt.tv/account/test/<apikey>
	# returns: {"status": "success","message": "all good!"}
	def testAccount(self, force=False):
		
		if self.__username == "":
			notification('trakt', getString(1106)) # please enter your Username and Password in settings
			setSetting('account_valid', False)
			return False
		elif self.__password == "":
			notification("trakt", getString(1107)) # please enter your Password in settings
			setSetting('account_valid', False)
			return False

		if not getSettingAsBool('account_valid') or force:
			Debug("[traktAPI] Testing account '%s'." % self.__username)

			url = "%s/account/test/%s" % (self.__baseURL, self.__apikey)
			Debug("[traktAPI] testAccount(url: %s)" % url)
			
			args = json.dumps({'username': self.__username, 'password': self.__password})
			response = None
			
			try:
				# get data from trakt.tv
				response = self.__getData(url, args)
			except traktError, e:
				if isinstance(e, traktAuthProblem):
					Debug("[traktAPI] testAccount(): Account '%s' failed authentication. (%s)" % (self.__username, e.value))
				elif isinstance(e, traktServerBusy):
					Debug("[traktAPI] testAccount(): Server Busy (%s)" % e.value)
				elif isinstance(e, traktNetworkError):
					Debug("[traktAPI] testAccount(): Network error: %s" % e.value)
				elif isinstance(e, traktUnknownError):
					Debug("[traktAPI] testAccount(): Other problem (%s)" % e.value)
				else:
					pass
			
			if response:
				data = None
				try:
					data = json.loads(response)
				except ValueError:
					pass

				if 'status' in data:
					if data['status'] == 'success':
						setSetting('account_valid', True)
						Debug("[traktAPI] testAccount(): Account '%s' is valid." % self.__username)
						return True

		else:
			return True

		notification('trakt', getString(1110)) # please enter your Password in settings
		setSetting('account_valid', False)
		return False

	# url: http://api.trakt.tv/account/settings/<apikey>
	# returns: all settings for authenticated user
	def getAccountSettings(self, force=False):
		_interval = (60 * 60 * 24 * 7) - (60 * 60) # one week less one hour

		_next = getSettingAsInt('trakt_settings_last') + _interval
		stale = force

		if force:
			Debug("[traktAPI] Forcing a reload of settings from trakt.tv.")

		if not stale and time.time() >= _next:
			Debug("[traktAPI] trakt.tv account settings are stale, reloading.")
			stale = True

		if stale:
			if self.testAccount():
				Debug("[traktAPI] Getting account settings for '%s'." % self.__username)
				url = "%s/account/settings/%s" % (self.__baseURL, self.__apikey)
				Debug("[traktAPI] getAccountSettings(url: %s)" % url)
				response = self.traktRequest('POST', url, hideResponse=True)
				if response and 'status' in response:
					if response['status'] == 'success':
						del response['status']
						setSetting('trakt_settings', json.dumps(response))
						setSetting('trakt_settings_last', int(time.time()))
						self.settings = response

		else:
			Debug("[traktAPI] Loaded cached account settings for '%s'." % self.__username)
			s = getSetting('trakt_settings')
			self.settings = json.loads(s)

	# helper to get rating mode, returns the setting from trakt.tv, or 'advanced' if there were problems getting them
	def getRatingMode(self):
		if not self.settings:
			self.getAccountSettings()
		rating_mode = "advanced"
		if self.settings and 'viewing' in self.settings:
			rating_mode = self.settings['viewing']['ratings']['mode']
		return rating_mode

	# url: http://api.trakt.tv/<show|movie>/watching/<apikey>
	# returns: {"status":"success","message":"watching The Walking Dead 1x01","show":{"title":"The Walking Dead","year":"2010","imdb_id":"tt123456","tvdb_id":"153021","tvrage_id":"1234"},"season":"1","episode":{"number":"1","title":"Days Gone Bye"},"facebook":false,"twitter":false,"tumblr":false}
	def watching(self, type, data):
		if self.testAccount():
			url = "%s/%s/watching/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] watching(url: %s, data: %s)" % (url, str(data)))
			if getSettingAsBool('simulate_scrobbling'):
				Debug("[traktAPI] Simulating response.")
				return {'status': 'success'}
			else:
				return self.traktRequest('POST', url, data, passVersions=True)
	
	def watchingEpisode(self, info, duration, percent):
		data = {'tvdb_id': info['tvdb_id'], 'title': info['showtitle'], 'year': info['year'], 'season': info['season'], 'episode': info['episode'], 'duration': math.ceil(duration), 'progress': math.ceil(percent)}
		if 'uniqueid' in info:
			data['episode_tvdb_id'] = info['uniqueid']['unknown']
		return self.watching('show', data)
	def watchingMovie(self, info, duration, percent):
		data = {'imdb_id': info['imdbnumber'], 'title': info['title'], 'year': info['year'], 'duration': math.ceil(duration), 'progress': math.ceil(percent)}
		return self.watching('movie', data)

	# url: http://api.trakt.tv/<show|movie>/scrobble/<apikey>
	# returns: {"status": "success","message": "scrobbled The Walking Dead 1x01"}
	def scrobble(self, type, data):
		if self.testAccount():
			url = "%s/%s/scrobble/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] scrobble(url: %s, data: %s)" % (url, str(data)))
			if getSettingAsBool('simulate_scrobbling'):
				Debug("[traktAPI] Simulating response.")
				return {'status': 'success'}
			else:
				return self.traktRequest('POST', url, data, returnOnFailure=True, passVersions=True)

	def scrobbleEpisode(self, info, duration, percent):
		data = {'tvdb_id': info['tvdb_id'], 'title': info['showtitle'], 'year': info['year'], 'season': info['season'], 'episode': info['episode'], 'duration': math.ceil(duration), 'progress': math.ceil(percent)}
		if 'uniqueid' in info:
			data['episode_tvdb_id'] = info['uniqueid']['unknown']
		return self.scrobble('show', data)
	def scrobbleMovie(self, info, duration, percent):
		data = {'imdb_id': info['imdbnumber'], 'title': info['title'], 'year': info['year'], 'duration': math.ceil(duration), 'progress': math.ceil(percent)}
		return self.scrobble('movie', data)

	# url: http://api.trakt.tv/<show|movie>/cancelwatching/<apikey>
	# returns: {"status":"success","message":"cancelled watching"}
	def cancelWatching(self, type):
		if self.testAccount():
			url = "%s/%s/cancelwatching/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] cancelWatching(url: %s)" % url)
			if getSettingAsBool('simulate_scrobbling'):
				Debug("[traktAPI] Simulating response.")
				return {'status': 'success'}
			else:
				return self.traktRequest('POST', url)
		
	def cancelWatchingEpisode(self):
		return self.cancelWatching('show')
	def cancelWatchingMovie(self):
		return self.cancelWatching('movie')

	# url: http://api.trakt.tv/user/library/<shows|movies>/collection.json/<apikey>/<username>/min
	# response: [{"title":"Archer (2009)","year":2009,"imdb_id":"tt1486217","tvdb_id":110381,"seasons":[{"season":2,"episodes":[1,2,3,4,5]},{"season":1,"episodes":[1,2,3,4,5,6,7,8,9,10]}]}]
	# note: if user has nothing in collection, response is then []
	def getLibrary(self, type):
		if self.testAccount():
			url = "%s/user/library/%s/collection.json/%s/%s/min" % (self.__baseURL, type, self.__apikey, self.__username)
			Debug("[traktAPI] getLibrary(url: %s)" % url)
			return self.traktRequest('POST', url)

	def getShowLibrary(self):
		return self.getLibrary('shows')
	def getMovieLibrary(self):
		return self.getLibrary('movies')

	# url: http://api.trakt.tv/user/library/<shows|movies>/watched.json/<apikey>/<username>/min
	# returns: [{"title":"Archer (2009)","year":2009,"imdb_id":"tt1486217","tvdb_id":110381,"seasons":[{"season":2,"episodes":[1,2,3,4,5]},{"season":1,"episodes":[1,2,3,4,5,6,7,8,9,10]}]}]
	# note: if nothing watched in collection, returns []
	def getWatchedLibrary(self, type):
		if self.testAccount():
			url = "%s/user/library/%s/watched.json/%s/%s/min" % (self.__baseURL, type, self.__apikey, self.__username)
			Debug("[traktAPI] getWatchedLibrary(url: %s)" % url)
			return self.traktRequest('POST', url)

	def getWatchedEpisodeLibrary(self,):
		return self.getWatchedLibrary('shows')
	def getWatchedMovieLibrary(self):
		return self.getWatchedLibrary('movies')

	# url: http://api.trakt.tv/<show|show/episode|movie>/library/<apikey>
	# returns: {u'status': u'success', u'message': u'27 episodes added to your library'}
	def addToLibrary(self, type, data):
		if self.testAccount():
			url = "%s/%s/library/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] addToLibrary(url: %s, data: %s)" % (url, str(data)))
			return self.traktRequest('POST', url, data)

	def addEpisode(self, data):
		return self.addToLibrary('show/episode', data)
	def addShow(self, data):
		return self.addToLibrary('show', data)
	def addMovie(self, data):
		return self.addToLibrary('movie', data)

	# url: http://api.trakt.tv/<show|show/episode|movie>/unlibrary/<apikey>
	# returns:
	def removeFromLibrary(self, type, data):
		if self.testAccount():
			url = "%s/%s/unlibrary/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] removeFromLibrary(url: %s, data: %s)" % (url, str(data)))
			return self.traktRequest('POST', url, data)

	def removeEpisode(self, data):
		return self.removeFromLibrary('show/episode', data)
	def removeShow(self, data):
		return self.removeFromLibrary('show', data)
	def removeMovie(self, data):
		return self.removeFromLibrary('movie', data)

	# url: http://api.trakt.tv/<show|show/episode|movie>/seen/<apikey>
	# returns: {u'status': u'success', u'message': u'2 episodes marked as seen'}
	def updateSeenInLibrary(self, type, data):
		if self.testAccount():
			url = "%s/%s/seen/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] updateSeenInLibrary(url: %s, data: %s)" % (url, str(data)))
			return self.traktRequest('POST', url, data)

	def updateSeenEpisode(self, data):
		return self.updateSeenInLibrary('show/episode', data)
	def updateSeenShow(self, data):
		return self.updateSeenInLibrary('show', data)
	def updateSeenMovie(self, data):
		return self.updateSeenInLibrary('movie', data)

	# url: http://api.trakt.tv/<show|show/episode|movie>/summary.format/apikey/title[/season/episode]
	# returns: returns information for a movie, show or episode
	def getSummary(self, type, data):
		if self.testAccount():
			url = "%s/%s/summary.json/%s/%s" % (self.__baseURL, type, self.__apikey, data)
			Debug("[traktAPI] getSummary(url: %s)" % url)
			return self.traktRequest('POST', url)

	def getShowSummary(self, id, extended=False):
		data = str(id)
		if extended:
			data = "%s/extended" % data
		return self.getSummary('show', data)
	def getEpisodeSummary(self, id, season, episode):
		data = "%s/%s/%s" % (id, season, episode)
		return self.getSummary('show/episode', data)
	def getMovieSummary(self, id):
		data = str(id)
		return self.getSummary('movie', data)

	# url: http://api.trakt.tv/show/season.format/apikey/title/season
	# returns: returns detailed episode info for a specific season of a show.
	def getSeasonInfo(self, id, season):
		if self.testAccount():
			url = "%s/show/season.json/%s/%s/%d" % (self.__baseURL, self.__apikey, id, season)
			Debug("[traktAPI] getSeasonInfo(url: %s)" % url)
			return self.traktRequest('POST', url)
	
	# url: http://api.trakt.tv/rate/<show|episode|movie>/apikey
	# returns: {"status":"success","message":"rated Portlandia 1x01","type":"episode","rating":"love","ratings":{"percentage":100,"votes":2,"loved":2,"hated":0},"facebook":true,"twitter":true,"tumblr":false}
	def rate(self, type, data):
		if self.testAccount():
			url = "%s/rate/%s/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] rate(url: %s, data: %s)" % (url, str(data)))
			return self.traktRequest('POST', url, data, passVersions=True)

	def rateShow(self, data):
		return self.rate('show', data)
	def rateEpisode(self, data):
		return self.rate('episode', data)
	def rateMovie(self, data):
		return self.rate('movie', data)

	# url: http://api.trakt.tv/user/lists.json/apikey/<username>
	# returns: Returns all custom lists for a user.
	def getUserLists(self):
		if self.testAccount():
			url = "%s/user/lists.json/%s/%s" % (self.__baseURL, self.__apikey, self.__username)
			Debug("[traktAPI] getUserLists(url: %s)" % url)
			return self.traktRequest('POST', url)

	# url: http://api.trakt.tv/user/list.json/apikey/<username>/<slug>
	# returns: Returns list details and all items it contains.
	def getUserList(self, data):
		if self.testAccount():
			url = "%s/user/list.json/%s/%s/%s" % (self.__baseURL, self.__apikey, self.__username, data)
			Debug("[traktAPI] getUserList(url: %s)" % url)
			return self.traktRequest('POST', url, passVersions=True)

	# url: http://api.trakt.tv/lists/<add|delete|items/add|items/delete>/apikey
	# returns: {"status": "success","message": ... }
	# note: return data varies based on method, but all include status/message
	def userList(self, method, data):
		if self.testAccount():
			url = "%s/lists/%s/%s" % (self.__baseURL, method, self.__apikey)
			Debug("[traktAPI] userList(url: %s, data: %s)" % (url, str(data)))
			return self.traktRequest('POST', url, data, passVersions=True)
	
	def userListAdd(self, list_name, privacy, description=None, allow_shouts=False, show_numbers=False):
		data = {'name': list_name, 'show_numbers': show_numbers, 'allow_shouts': allow_shouts, 'privacy': privacy}
		if description:
			data['description'] = description
		return self.userList('add', data)
	def userListDelete(self, slug_name):
		data = {'slug': slug_name}
		return self.userList('delete', data)
	def userListItemAdd(self, data):
		return self.userList('items/add', data)
	def userListItemDelete(self, data):
		return self.userList('items/delete', data)
	def userListUpdate(self, data):
		return self.userList('update', data)

	# url: http://api.trakt.tv/user/watchlist/<movies|shows>.json/<apikey>/<username>
	# returns: [{"title":"GasLand","year":2010,"released":1264320000,"url":"http://trakt.tv/movie/gasland-2010","runtime":107,"tagline":"Can you light your water on fire? ","overview":"It is happening all across America-rural landowners wake up one day to find a lucrative offer from an energy company wanting to lease their property. Reason? The company hopes to tap into a reservoir dubbed the \"Saudi Arabia of natural gas.\" Halliburton developed a way to get the gas out of the ground-a hydraulic drilling process called \"fracking\"-and suddenly America finds itself on the precipice of becoming an energy superpower.","certification":"","imdb_id":"tt1558250","tmdb_id":"40663","inserted":1301130302,"images":{"poster":"http://trakt.us/images/posters_movies/1683.jpg","fanart":"http://trakt.us/images/fanart_movies/1683.jpg"},"genres":["Action","Comedy"]},{"title":"The King's Speech","year":2010,"released":1291968000,"url":"http://trakt.tv/movie/the-kings-speech-2010","runtime":118,"tagline":"God save the king.","overview":"Tells the story of the man who became King George VI, the father of Queen Elizabeth II. After his brother abdicates, George ('Bertie') reluctantly assumes the throne. Plagued by a dreaded stutter and considered unfit to be king, Bertie engages the help of an unorthodox speech therapist named Lionel Logue. Through a set of unexpected techniques, and as a result of an unlikely friendship, Bertie is able to find his voice and boldly lead the country into war.","certification":"R","imdb_id":"tt1504320","tmdb_id":"45269","inserted":1301130174,"images":{"poster":"http://trakt.us/images/posters_movies/8096.jpg","fanart":"http://trakt.us/images/fanart_movies/8096.jpg"},"genres":["Action","Comedy"]}]
	# note: if nothing in list, returns []
	def getWatchlist(self, type):
		if self.testAccount():
			url = "%s/user/watchlist/%s.json/%s/%s" % (self.__baseURL, type, self.__apikey, self.__username)
			Debug("[traktAPI] getWatchlist(url: %s)" % url)
			return self.traktRequest('POST', url)

	def getWatchlistShows(self):
		return self.getWatchlist('shows')
	def getWatchlistMovies(self):
		return self.getWatchlist('movies')

	# url: http://api.trakt.tv/<movie|show>/watchlist/<apikey>
	# returns: 
	def watchlistAddItems(self, type, data):
		if self.testAccount():
			url = "%s/%s/watchlist/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] watchlistAddItem(url: %s)" % url)
			return self.traktRequest('POST', url, data, passVersions=True)

	def watchlistAddShows(self, data):
		return self.watchlistAddItems('show', data)
	def watchlistAddMovies(self, data):
		return self.watchlistAddItems('movie', data)

	# url: http://api.trakt.tv/<movie|show>/unwatchlist/<apikey>
	# returns: 
	def watchlistRemoveItems(self, type, data):
		if self.testAccount():
			url = "%s/%s/unwatchlist/%s" % (self.__baseURL, type, self.__apikey)
			Debug("[traktAPI] watchlistRemoveItems(url: %s)" % url)
			return self.traktRequest('POST', url, data, passVersions=True)

	def watchlistRemoveShows(self, data):
		return self.watchlistRemoveItems('show', data)
	def watchlistRemoveMovies(self, data):
		return self.watchlistRemoveItems('movie', data)

	# url: http://api.trakt.tv/user/ratings/<movies|shows>.json/<apikey>/<username>/<rating>
	# returns:
	# note: if no items, returns []
	def getRatedItems(self, type):
		if self.testAccount():
			url = "%s/user/ratings/%s.json/%s/%s/all" % (self.__baseURL, type, self.__apikey, self.__username)
			Debug("[traktAPI] getRatedItems(url: %s)" % url)
			return self.traktRequest('POST', url)

	def getRatedMovies(self):
		return self.getRatedItems('movies')
	def getRatedShows(self):
		return self.getRatedItems('shows')

########NEW FILE########
__FILENAME__ = traktContextMenu
# -*- coding: utf-8 -*-
#

import xbmc
import xbmcaddon
import xbmcgui
import utilities as utils

__addon__ = xbmcaddon.Addon("script.trakt")

ACTION_LIST = 111
DIALOG_IMAGE = 2
ACTION_PREVIOUS_MENU2	= 92
ACTION_PARENT_DIR		= 9
ACTION_PREVIOUS_MENU	= 10 
ACTION_SELECT_ITEM		= 7
ACTION_MOUSE_LEFT_CLICK	= 100
ACTION_CLOSE_LIST		= [ACTION_PREVIOUS_MENU2, ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU]
ACTION_ITEM_SELECT		= [ACTION_SELECT_ITEM, ACTION_MOUSE_LEFT_CLICK]

class traktContextMenu(xbmcgui.WindowXMLDialog):

	action = None

	def __new__(cls, media_type=None, buttons=None):
		return super(traktContextMenu, cls).__new__(cls, "traktContextMenu.xml", __addon__.getAddonInfo('path'), media_type=media_type, buttons=None) 

	def __init__(self, *args, **kwargs):
		self.buttons = kwargs['buttons']
		self.media_type = kwargs['media_type']
		super(traktContextMenu, self).__init__()

	def onInit(self):
		lang = utils.getString
		mange_string = lang(2000) if utils.isMovie(self.media_type) else lang(2001)
		rate_string = lang(2030)
		if utils.isShow(self.media_type):
			rate_string = lang(2031)
		elif utils.isEpisode(self.media_type):
			rate_string = lang(2032)

		actions = [mange_string, lang(2010), lang(2020), rate_string, lang(2040), lang(2050), lang(2060), lang(2070)]
		keys = ["itemlists", "removefromlist", "addtolist", "rate", "togglewatched", "managelists", "updatetags", "sync"]

		l = self.getControl(ACTION_LIST)
		for i in range(len(actions)):
			if keys[i] in self.buttons:
				l.addItem(self.newListItem(actions[i], id=keys[i]))

		h = ((len(self.buttons)) * 46) - 6
		l.setHeight(h)

		d = self.getControl(DIALOG_IMAGE)
		d.setHeight(h + 40)

		offset = (316 - h) / 2

		d.setPosition(0, offset - 20)
		l.setPosition(20, offset)

		self.setFocus(l)

	def newListItem(self, label, selected=False, *args, **kwargs):
		item = xbmcgui.ListItem(label)
		item.select(selected)
		for key in kwargs:
			item.setProperty(key, str(kwargs[key]))
		return item

	def onAction(self, action):
		if not action.getId() in ACTION_ITEM_SELECT:
			if action in ACTION_CLOSE_LIST:
				self.close()

		if action in ACTION_ITEM_SELECT:
			cID = self.getFocusId() 
			if cID == ACTION_LIST:
				l = self.getControl(cID)
				item = l.getSelectedItem()
				selected = not item.isSelected()
				self.action = item.getProperty('id')
				self.close()

########NEW FILE########
__FILENAME__ = utilities
# -*- coding: utf-8 -*-
#

import xbmc
import xbmcaddon
import xbmcgui
import math
import time
import copy
import re

try:
	import simplejson as json
except ImportError:
	import json

# read settings
__addon__ = xbmcaddon.Addon('script.trakt')

# make strptime call prior to doing anything, to try and prevent threading errors
time.strptime("1970-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")

REGEX_EXPRESSIONS = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09
                      '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                      '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                      '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                      'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',              # Season 01 - Episode 02
                      'Season ([0-9]+) Episode ([0-9]+)[^\\/]*',                # Season 01 Episode 02
                      '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                      '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                #foo_[s01]_[e01]
                      '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',       #foo, s01e01, foo.s01.e01, foo.s01-e01
                      's([0-9]+)ep([0-9]+)[^\\/]*',                             #foo - s01ep03, foo - s1ep03
                      '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
                     ]

def Debug(msg, force = False):
	if(getSettingAsBool('debug') or force):
		try:
			print "[trakt] " + msg
		except UnicodeEncodeError:
			print "[trakt] " + msg.encode('utf-8', 'ignore')

def notification(header, message, time=5000, icon=__addon__.getAddonInfo('icon')):
	xbmc.executebuiltin("XBMC.Notification(%s,%s,%i,%s)" % (header, message, time, icon))

def showSettings():
	__addon__.openSettings()

def getSetting(setting):
    return __addon__.getSetting(setting).strip()

def getSettingAsBool(setting):
        return getSetting(setting).lower() == "true"

def getSettingAsFloat(setting):
    try:
        return float(getSetting(setting))
    except ValueError:
        return 0

def getSettingAsInt(setting):
    try:
        return int(getSettingAsFloat(setting))
    except ValueError:		
        return 0

def getSettingAsList(setting):
	data = getSetting(setting)
	try:
		return json.loads(data)
	except ValueError:
		return []

def setSetting(setting, value):
	__addon__.setSetting(setting, str(value))

def setSettingFromList(setting, value):
	if value is None:
		value = []
	data = json.dumps(value)
	setSetting(setting, data)

def getString(string_id):
    return __addon__.getLocalizedString(string_id).encode('utf-8', 'ignore')

def getProperty(property):
	return xbmcgui.Window(10000).getProperty(property)

def getPropertyAsBool(property):
	return getProperty(property) == "True"
	
def setProperty(property, value):
	xbmcgui.Window(10000).setProperty(property, value)

def clearProperty(property):
	xbmcgui.Window(10000).clearProperty(property)

def isMovie(type):
	return type == 'movie'

def isEpisode(type):
	return type == 'episode'

def isShow(type):
	return type == 'show'

def isSeason(type):
	return type == 'season'

def isValidMediaType(type):
	return type in ['movie', 'show', 'episode']

def xbmcJsonRequest(params):
	data = json.dumps(params)
	request = xbmc.executeJSONRPC(data)
	response = None
	try:
		response = json.loads(request)
	except UnicodeDecodeError:
		response = json.loads(request.decode('utf-8', 'ignore'))

	try:
		if 'result' in response:
			return response['result']
		return None
	except KeyError:
		Debug("[%s] %s" % (params['method'], response['error']['message']), True)
		return None

def sqlDateToUnixDate(date):
	if not date:
		return 0
	t = time.strptime(date, "%Y-%m-%d %H:%M:%S")
	try:
		utime = int(time.mktime(t))
	except OverflowError:
		utime = None
	return utime

def chunks(l, n):
	return [l[i:i+n] for i in range(0, len(l), n)]

# check exclusion settings for filename passed as argument
def checkScrobblingExclusion(fullpath):

	if not fullpath:
		return True
	
	Debug("checkScrobblingExclusion(): Checking exclusion settings for '%s'." % fullpath)
	
	if (fullpath.find("pvr://") > -1) and getSettingAsBool('ExcludeLiveTV'):
		Debug("checkScrobblingExclusion(): Video is playing via Live TV, which is currently set as excluded location.")
		return True
				
	if (fullpath.find("http://") > -1) and getSettingAsBool('ExcludeHTTP'):
		Debug("checkScrobblingExclusion(): Video is playing via HTTP source, which is currently set as excluded location.")
		return True
		
	ExcludePath = getSetting('ExcludePath')
	if ExcludePath != "" and getSettingAsBool('ExcludePathOption'):
		if (fullpath.find(ExcludePath) > -1):
			Debug("checkScrobblingExclusion(): Video is playing from location, which is currently set as excluded path 1.")
			return True

	ExcludePath2 = getSetting('ExcludePath2')
	if ExcludePath2 != "" and getSettingAsBool('ExcludePathOption2'):
		if (fullpath.find(ExcludePath2) > -1):
			Debug("checkScrobblingExclusion(): Video is playing from location, which is currently set as excluded path 2.")
			return True

	ExcludePath3 = getSetting('ExcludePath3')
	if ExcludePath3 != "" and getSettingAsBool('ExcludePathOption3'):
		if (fullpath.find(ExcludePath3) > -1):
			Debug("checkScrobblingExclusion(): Video is playing from location, which is currently set as excluded path 3.")
			return True
	
	return False

def getFormattedItemName(type, info, short=False):
	s = None
	if isShow(type):
		s = info['title']
	elif isEpisode(type):
		if short:
			s = "S%02dE%02d - %s" % (info['episode']['season'], info['episode']['number'], info['episode']['title'])
		else:
			s = "%s - S%02dE%02d - %s" % (info['show']['title'], info['episode']['season'], info['episode']['number'], info['episode']['title'])
	elif isSeason(type):
		if info['season'] > 0:
			s = "%s - Season %d" % (info['title'], info['season'])
		else:
			s = "%s - Specials" % info['title']
	elif isMovie(type):
		s = "%s (%s)" % (info['title'], info['year'])
	return s.encode('utf-8', 'ignore')

def getShowDetailsFromXBMC(showID, fields):
	result = xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShowDetails', 'params':{'tvshowid': showID, 'properties': fields}, 'id': 1})
	Debug("getShowDetailsFromXBMC(): %s" % str(result))

	if not result:
		Debug("getEpisodeDetailsFromXbmc(): Result from XBMC was empty.")
		return None

	try:
		return result['tvshowdetails']
	except KeyError:
		Debug("getShowDetailsFromXBMC(): KeyError: result['tvshowdetails']")
		return None

# get a single episode from xbmc given the id
def getEpisodeDetailsFromXbmc(libraryId, fields):
	result = xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params':{'episodeid': libraryId, 'properties': fields}, 'id': 1})
	Debug("getEpisodeDetailsFromXbmc(): %s" % str(result))

	if not result:
		Debug("getEpisodeDetailsFromXbmc(): Result from XBMC was empty.")
		return None

	show_data = getShowDetailsFromXBMC(result['episodedetails']['tvshowid'], ['year', 'imdbnumber'])
	
	if not show_data:
		Debug("getEpisodeDetailsFromXbmc(): Result from getShowDetailsFromXBMC() was empty.")
		return None
		
	result['episodedetails']['tvdb_id'] = show_data['imdbnumber']
	result['episodedetails']['year'] = show_data['year']
	
	try:
		return result['episodedetails']
	except KeyError:
		Debug("getEpisodeDetailsFromXbmc(): KeyError: result['episodedetails']")
		return None

# get a single movie from xbmc given the id
def getMovieDetailsFromXbmc(libraryId, fields):
	result = xbmcJsonRequest({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovieDetails', 'params':{'movieid': libraryId, 'properties': fields}, 'id': 1})
	Debug("getMovieDetailsFromXbmc(): %s" % str(result))

	if not result:
		Debug("getMovieDetailsFromXbmc(): Result from XBMC was empty.")
		return None

	try:
		return result['moviedetails']
	except KeyError:
		Debug("getMovieDetailsFromXbmc(): KeyError: result['moviedetails']")
		return None

def findInList(list, returnIndex=False, returnCopy=False, case_sensitive=True, *args, **kwargs):
	for index in range(len(list)):
		item = list[index]
		i = 0
		for key in kwargs:
			if not key in item:
				continue
			if not case_sensitive and isinstance(item[key], basestring):
				if item[key].lower() == kwargs[key].lower():
					i = i + 1
			else:
				if item[key] == kwargs[key]:
					i = i + 1
		if i == len(kwargs):
			if returnIndex:
				return index
			else:
				if returnCopy:
					return copy.deepcopy(list[index])
				else:
					return list[index]
	return None

def findAllInList(list, key, value):
	return [item for item in list if item[key] == value]

def findMovie(movie, movies, returnIndex=False):
	result = None
	if 'imdb_id' in movie and unicode(movie['imdb_id']).startswith("tt"):
		result = findInList(movies, returnIndex=returnIndex, imdb_id=movie['imdb_id'])
	if result is None and 'tmdb_id' in movie and unicode(movie['tmdb_id']).isdigit():
		result = findInList(movies, returnIndex=returnIndex, tmdb_id=unicode(movie['tmdb_id']))
	if result is None and movie['title'] and movie['year'] > 0:
		result = findInList(movies, returnIndex=returnIndex, title=movie['title'], year=movie['year'])
	return result

def findShow(show, shows, returnIndex=False):
	result = None
	if 'tvdb_id' in show and unicode(show['tvdb_id']).isdigit():
		result = findInList(shows, returnIndex=returnIndex, tvdb_id=unicode(show['tvdb_id']))
	if result is None and 'imdb_id' in show and unicode(show['imdb_id']).startswith("tt"):
		result = findInList(shows, returnIndex=returnIndex, imdb_id=show['imdb_id'])
	if result is None and show['title'] and 'year' in show and show['year'] > 0:
		result = findInList(shows, returnIndex=returnIndex, title=show['title'], year=show['year'])
	return result

def regex_tvshow(compare, file, sub = ""):
	sub_info = ""
	tvshow = 0

  	for regex in REGEX_EXPRESSIONS:
  		response_file = re.findall(regex, file)
  		if len(response_file) > 0 :
  			Debug("regex_tvshow(): Regex File Se: %s, Ep: %s," % (str(response_file[0][0]),str(response_file[0][1]),) )
  			tvshow = 1
  			if not compare :
  				title = re.split(regex, file)[0]
  				for char in ['[', ']', '_', '(', ')','.','-']:
  					title = title.replace(char, ' ')
  				if title.endswith(" "): title = title[:-1]
  				return title,response_file[0][0], response_file[0][1]
  			else:
  				break

  	if (tvshow == 1):
  		for regex in regex_expressions:
  			response_sub = re.findall(regex, sub)
  			if len(response_sub) > 0 :
  				try :
  					sub_info = "Regex Subtitle Ep: %s," % (str(response_sub[0][1]),)
  					if (int(response_sub[0][1]) == int(response_file[0][1])):
  						return True
  				except: pass
  		return False
  	if compare :
  		return True
  	else:
  		return "","",""
########NEW FILE########
