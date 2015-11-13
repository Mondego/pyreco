__FILENAME__ = constants
import oauth_secrets #NOTE this file is not included in the repository because it contains the OAuth consumer secrets
from os import environ
from gheatae import color_scheme
import logging

min_zoom = 3
max_zoom = 18 # note that these must also be in the static wdyg-private.js file

level_const = 140. #TODO fix this from being hard coded in models.py for UserInfo - I was getting a <type 'exceptions.AttributeError'>: 'module' object has no attribute 'level_const'

default_photo = 'static/foursquare_girl.png'
# def get_default_photo(gender='male'):
#   if gender is 'male':
#     return 'static/foursquare_boy.png'
#   else:
#     return 'static/foursquare_girl.png'   
default_color = color_scheme.color_schemes.keys()[0]
default_lat = 40.73607172122901 #NYC
default_lng = -73.96699905395508
default_zoom = 13
default_dimension = 640
google_maps_apikey = 'ABQIAAAAwA6oEsCLgzz6I150wm3ELBSujOi3smKLcjzph36ZE8UXngM_5BTs-xHblsuwK8V9g8bZ_PTfOWR1Fg'

def get_oauth_strings(force_primary_domain=False):
  if force_primary_domain: # I was getting SIGNATURE_INVALID oauth errors on many of my backend calls because 
                           # I was not using the same domain for the requests as I was when the users signed up
                           # Always forcing this will break support for other domains, but will fix some OAuth
                           # issues, so that's what I'm doing for now.
      domain = 'www.wheredoyougo.net'
  else:
      domain = environ['HTTP_HOST']
  logging.info('-------------------------------')
  logging.info(domain)
  if domain == 'www.wheredoyougo.net':
    consumer_key = 'KTNXGQJ4JXDZGAG35MGZ3WN0EQIO5XHNALYQZATHVEPDR3TI'
    callback_url = 'http://www.wheredoyougo.net/authenticated'
  elif domain == 'where-do-you-go-hrd.appspot.com':
    consumer_key = '1MVIIQ4S50Z0G3GRXYPG4PYFH44TYFAIZKG431CFLPQOVOND'
    callback_url = 'http://where-do-you-go-hrd.appspot.com/authenticated'
  else:
    consumer_key = ''
    callback_url = ''
    logging.error('No Foursquare OAuth consumer key found for domain ' + domain)
  return consumer_key, oauth_secrets.get_oauth_consumer_secret_for_domain(domain), callback_url

provider = None
########NEW FILE########
__FILENAME__ = foursquarev2
# -*- coding: utf-8 -*-
"""
A python wrapper for the foursquare APIv2

Author: Juan Odicio <juanodicio@gmail.com>

https://github.com/juanodicio/foursquare-apiv2-python

If you are looking for a complete foursquare-APIv2 reference, go to
http://developer.foursquare.com/docs/

"""

import urllib
import httplib2
import json
import logging

VERSION = '0.7'
VERSION_DATE = '20120609'


class FoursquareException(Exception):
    pass
    
class FoursquareRemoteException(FoursquareException):
    def __init__(self, method, code, msg):
        self.method = method
        self.code = code
        self.msg = msg

    def __str__(self):
        return 'Error signaled by remote method %s: %s (%s)' % (self.method, self.msg, self.code)

class FoursquareAuthHelper(object):
    _consumer_key = ''
    _consumer_secret = ''
    
    _access_token_url = 'https://foursquare.com/oauth2/access_token'
    _authentication_url = 'https://foursquare.com/oauth2/authenticate'
    _oauth_callback_uri = ''
    
    API_URL = 'https://api.foursquare.com/v2/'
    
    def __init__(self, key, secret, redirect_uri):
        self._consumer_key = key
        self._consumer_secret = secret
        self._oauth_callback_uri = redirect_uri
        
    def get_callback_uri(self):
        return self._oauth_callback_uri
    
    def get_authentication_url(self):
        query = {
            'v': VERSION_DATE,
            'client_id': self._consumer_key,
            'response_type': 'code',
            'redirect_uri': self._oauth_callback_uri
        }
        query_str = self.urlencode(query)
        return self._authentication_url + "?" + query_str

    def get_access_token_url(self, code):
        query = {
            'v': VERSION_DATE,
            'client_id': self._consumer_key,
            'client_secret': self._consumer_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self._oauth_callback_uri,
            'code': code
        }
        query_str = self.urlencode(query)
        return self._access_token_url + "?" + query_str
    
    def get_access_token(self, code):
        http = httplib2.Http()
        resp, content = http.request(self.get_access_token_url(code))
        j = json.loads(content)
        if 'access_token' in j:
            return j['access_token']
        else:
            return None
                
    def urlencode(self, query):
        return urllib.urlencode(query)
    
    
class FoursquareClient(object):
    
    API_URL = 'https://api.foursquare.com/v2'
    
    _access_token = ''
    
    def __init__(self, access_token):
        self._access_token = access_token
        
    def get_access_token(self):
        return self._access_token
        
    def _remove_empty_params(self, params):
        ret = {}
        for key in params:
            if not params[key] == None:
                ret[key] = params[key]
        return ret
                
    def make_api_call(self, url, method='GET', query={}, body={}, add_token=True):
        if add_token:
            query['oauth_token'] = self._access_token
            
        query = self._remove_empty_params(query)
        body = self._remove_empty_params(body)
        if 'v' not in query:
            query['v'] = VERSION_DATE
        query_str = urllib.urlencode(query)
        body_str = urllib.urlencode(body)
        
        if len(query) > 0:
            if url.find('?') == -1:
                url = url + '?' + query_str
            else:
                url = url + '&' + query_str
                    
        h = httplib2.Http()
        try:
          resp, content = h.request(url, method, body=body_str)
          raw_response = json.loads(content)
          if raw_response['meta']['code'] != 200:
            logging.error('ERROR: %s' % raw_response)
            raise FoursquareRemoteException(url, response.status, response_body)
          return raw_response['response']
        except Exception, err:
          logging.error(err)
          raise FoursquareException()
        
        
        
    # Not tested
    def users(self, user_id='self'):
        url = self.API_URL + '/users/%s' % user_id
        return self.make_api_call(url, method='GET')

    def users_search(self, phone=None, email=None, twitter=None
                     , twitter_source=None, fbid=None, name=None):
        url = self.API_URL + '/users/search'
        query = {
            'phone': phone,
            'email': email,
            'twitter': twitter,
            'twitterSource': twitter_source,
            'fbid': fbid,
            'name': name
        }
        return self.make_api_call(url, method='GET', query=query)
        
    def users_requests(self):
        url = self.API_URL + '/users/requests'
        return self.make_api_call(url, method='GET')

    def users_badges(self, user_id='self'):
        url = self.API_URL + '/users/%s/badges' % user_id
        return self.make_api_call(url, method='GET')
    
    def users_checkins(self, user_id='self', limit=250, after_timestamp=None, offset=0):
        url = self.API_URL + '/users/%s/checkins?offset=%s&limit=%s'%(user_id, offset, limit)
        if after_timestamp:
            url = url+'&afterTimestamp=%s'%(after_timestamp)
        return self.make_api_call(url, method='GET')
    
    def users_friends(self, user_id='self'):
        url = self.API_URL + '/users/%s/friends' % user_id
        return self.make_api_call(url, method='GET')
    
    def users_tips(self, user_id='self', sort='recent', ll=None):
        url = self.API_URL + '/users/%s/tips' % user_id
        query = {
            'sort': sort,
            'll': ll
        }
        return self.make_api_call(url, method='GET', query=query)
    
    def users_todos(self, user_id='self', sort='recent', ll=None):
        url = self.API_URL + '/users/%s/todos' % user_id
        query = {
            'sort': sort,
            'll': ll
        }
        return self.make_api_call(url, method='GET', query=query)
    
    def users_venuehistory(self, user_id='self'):
        url = self.API_URL + '/users/%s/venuehistory' % user_id
        return self.make_api_call(url, method='GET')
    
    def users_lists(self, user_id='self', ll='40.7,-74'):
        url = self.API_URL + '/users/%s/lists' % user_id
        query = {'ll': ll}
        return self.make_api_call(url, method='GET', query=query)
    #---------- POST -----------------------
    
    def users_request(self, user_id):
        url = self.API_URL + '/users/%s/request' % user_id
        return self.make_api_call(url, method='POST')
    
    def users_unfriend(self, user_id):
        url = self.API_URL + '/users/%s/unfriend' % user_id
        return self.make_api_call(url, method='POST')
    
    def users_approve(self, user_id):
        url = self.API_URL + '/users/%s/approve' % user_id
        return self.make_api_call(url, method='POST')
    
    def users_deny(self, user_id):
        url = self.API_URL + '/users/%s/deny' % user_id
        return self.make_api_call(url, method='POST')
    
    def users_setpings(self, user_id, value=False):
        """ NOTE: Documentation says that value parameter should be sent as
        POST var but it only works if you send it as query string
        """
        url = self.API_URL + '/users/%s/setpings' % user_id
        query = {
            'value': value
        }
        return self.make_api_call(url, method='POST', query=query)
    
    def venues(self, venue_id):
        url = self.API_URL + '/venues/%s' % venue_id
        return self.make_api_call(url, method='GET')
    # TODO: not tested
    def venues_add(self, name, address=None, cross_street=None, city=None
                   , state=None, zip=None, phone=None
                   , ll=None, primary_category_id=None):
        url = self.API_URL + '/venues/add'
        body = {
            'name': name,
            'address': address,
            'crossStreet': cross_street,
            'city': city,
            'state': state,
            'zip': zip,
            'phone': phone,
            'll': ll,
            'primaryCategoryId': primary_category_id
        }
        return self.make_api_call(url, method='POST', body=body)
    
    def venues_categories(self):
        url = self.API_URL + '/venues/categories'
        return self.make_api_call(url, method='GET')

    def venues_search(self, ll=None, ll_acc=None, alt=None, alt_acc=None
                      , query=None, limit=None, intent=None):
        url = self.API_URL + '/venues/search'
        query = {
            'll': ll,
            'llAcc': ll_acc,
            'alt': alt,
            'altAcc': alt_acc,
            'query': query,
            'limit': limit,
            'intent': intent
        }
        return self.make_api_call(url, method='GET', query=query)
    
    def venues_herenow(self, venue_id):
        url = self.API_URL + '/venues/%s/herenow' % venue_id
        return self.make_api_call(url, method='GET')
    
    def venues_tips(self, venue_id, sort='recent'):
        url = self.API_URL + '/venues/%s/tips' % venue_id
        return self.make_api_call(url, method='GET')

    def venues_marktodo(self, venue_id, text=''):
        url = self.API_URL + '/venues/%s/marktodo' % venue_id
        body = {
            'text': text
        }
        return self.make_api_call(url, method='POST', body=body)

    def venues_flag(self, venue_id, problem):
        problem_set = ['mislocated', 'closed', 'duplicated']
        url = self.API_URL + '/venues/%s/flag' % venue_id
        query = {
            'problem': problem
        }
        return self.make_api_call(url, method='POST', query=query)
    # TODO: not tested
    def venues_proposeedit(self, venue_id, name, address=None
                   , cross_street=None, city=None
                   , state=None, zip=None, phone=None
                   , ll=None, primary_category_id=None):
        url = self.API_URL + '/venues/%s/proposeedit' % venue_id
        body = {
            'name': name,
            'address': address,
            'crossStreet': cross_street,
            'city': city,
            'state': state,
            'zip': zip,
            'phone': phone,
            'll': ll,
            'primaryCategoryId': primary_category_id
        }
        return self.make_api_call(url, method='POST', body=body)
    
    def checkins(self, checkin_id):
        url = self.API_URL + '/checkins/%s' % checkin_id
        return self.make_api_call(url, method='GET')
    
    def checkins_add(self, venue_id=None, venue=None, shout=None
                     , broadcast='public', ll=None, ll_acc=None
                     , alt=None, alt_acc=None):
        url = self.API_URL + '/checkins/add'
        body = {
            'venueId': venue_id,
            'venue': venue,
            'shout': shout,
            'broadcast': broadcast,
            'll': ll,
            'llAcc': ll_acc,
            'alt': alt,
            'altAcc': alt_acc
        }
        return self.make_api_call(url, method='POST', query=body)
    
    def checkins_recent(self, ll=None, limit=None, offset=None
                        , after_timestamp=None):
        url = self.API_URL + '/checkins/recent'
        query = {
            'll': ll,
            'limit': limit,
            'offset': offset,
            'afterTimestamp': after_timestamp
        }
        return self.make_api_call(url, method='GET', query=query)
    
    def checkins_addcomment(self, checkin_id, text):
        url = self.API_URL + '/checkins/%s/addcomment' % checkin_id
        query = {
            'text': text
        }
        return self.make_api_call(url, method='POST', query=query)
    
    def checkins_deletecomment(self, checkin_id, comment_id):
        url = self.API_URL + '/checkins/%s/deletecomment' % checkin_id
        body = {
            'commentId': comment_id
        }
        return self.make_api_call(url, method='POST', query=body)
        
    
    def tips(self, tip_id):
        url = self.API_URL + '/tips/%s' % tip_id
        return self.make_api_call(url, method='GET')
    # TODO Not tested
    def tips_add(self, venue_id, text, url=None):
        url = self.API_URL + '/tips/add'
        query = {
            'venueId': venue_id,
            'text': text,
            'url': url
        }
        return self.make_api_call(url, method='POST', query=query)
    
    def tips_search(self, ll, limit=None, offset=None, filter=None, query=None):
        url = self.API_URL + '/tips/search'
        query = {
            'll': ll,
            'limit': limit,
            'offset': offset,
            'filter': filter,
            'query': query
        }
        return self.make_api_call(url, method='GET', query=query)

    def tips_marktodo(self, tip_id):
        url = self.API_URL + '/tips/%s/marktodo' % tip_id
        return self.make_api_call(url, method='POST')

    def tips_markdone(self, tip_id):
        url = self.API_URL + '/tips/%s/markdone' % tip_id
        return self.make_api_call(url, method='POST')

    def tips_unmark(self, tip_id):
        url = self.API_URL + '/tips/%s/unmark' % tip_id
        return self.make_api_call(url, method='POST')
    # TODO: Not tested
    def photos(self, photo_id):
        url = self.API_URL + '/photos/%s' % photo_id
        return self.make_api_call(url, method='GET')
    # TODO: Not implemented
    
    # LISTS
    def list_detail(self, list_id):
        url = self.API_URL + '/lists/%s' %list_id
        return self.make_api_call(url, method='GET')
    
    def list_add(self, name, description=None, collaborative=True, photo_id=None):
        url = self.API_URL + '/lists/add'
        query = {
            'name': name,
            'description': description,
            'collaborative': collaborative,
            'photoId': photo_id
        }
        return self.make_api_call(url, method='POST', query=query)

#TODO: add the rest of the lists endpoints
    
    def photos_add(self, photo_path, checkin_id=None, tip_id=None
                   , venue_id=None, broadcast=None
                   , ll=None, ll_acc=None
                   , alt=None, alt_acc=None):
        url = self.API_URL + '/photos/add'
        body = {
            'checkinId': checkin_id,
            'tipId': tip_id,
            'venueId': venue_id,
            'broadcast': broadcast,
            'll': ll,
            'llAcc': ll_acc,
            'alt': alt,
            'alt_acc': alt_acc
        }
        return self.make_api_call(url, method='POST', query=body)
    
    def settings_all(self):
        url = self.API_URL + '/settings/all'
        return self.make_api_call(url, method='GET')
    
    def settings_set(self, setting_id, value):
        url = self.API_URL + '/settings/%s/set' % setting_id
        query = {
            'value': value
        }
        return self.make_api_call(url, method='POST', query=query)
########NEW FILE########
__FILENAME__ = geocell
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines the notion of 'geocells' and exposes methods to operate on them.

A geocell is a hexadecimal string that defines a two dimensional rectangular
region inside the [-90,90] x [-180,180] latitude/longitude space. A geocell's
'resolution' is its length. For most practical purposes, at high resolutions,
geocells can be treated as single points.

Much like geohashes (see http://en.wikipedia.org/wiki/Geohash), geocells are
hierarchical, in that any prefix of a geocell is considered its ancestor, with
geocell[:-1] being geocell's immediate parent cell.

To calculate the rectangle of a given geocell string, first divide the
[-90,90] x [-180,180] latitude/longitude space evenly into a 4x4 grid like so:

             +---+---+---+---+ (90, 180)
             | a | b | e | f |
             +---+---+---+---+
             | 8 | 9 | c | d |
             +---+---+---+---+
             | 2 | 3 | 6 | 7 |
             +---+---+---+---+
             | 0 | 1 | 4 | 5 |
  (-90,-180) +---+---+---+---+

NOTE: The point (0, 0) is at the intersection of grid cells 3, 6, 9 and c. And,
      for example, cell 7 should be the sub-rectangle from
      (-45, 90) to (0, 180).

Calculate the sub-rectangle for the first character of the geocell string and
re-divide this sub-rectangle into another 4x4 grid. For example, if the geocell
string is '78a', we will re-divide the sub-rectangle like so:

               .                   .
               .                   .
           . . +----+----+----+----+ (0, 180)
               | 7a | 7b | 7e | 7f |
               +----+----+----+----+
               | 78 | 79 | 7c | 7d |
               +----+----+----+----+
               | 72 | 73 | 76 | 77 |
               +----+----+----+----+
               | 70 | 71 | 74 | 75 |
  . . (-45,90) +----+----+----+----+
               .                   .
               .                   .

Continue to re-divide into sub-rectangles and 4x4 grids until the entire
geocell string has been exhausted. The final sub-rectangle is the rectangular
region for the geocell.
"""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import os.path
import sys

import geomath
import geotypes

# Geocell algorithm constants.
_GEOCELL_GRID_SIZE = 4
_GEOCELL_ALPHABET = '0123456789abcdef'

# The maximum *practical* geocell resolution.
MAX_GEOCELL_RESOLUTION = 13

# The maximum number of geocells to consider for a bounding box search.
MAX_FEASIBLE_BBOX_SEARCH_CELLS = 300

# Direction enumerations.
NORTHWEST = (-1, 1)
NORTH = (0, 1)
NORTHEAST = (1, 1)
EAST = (1, 0)
SOUTHEAST = (1, -1)
SOUTH = (0, -1)
SOUTHWEST = (-1, -1)
WEST = (-1, 0)


def best_bbox_search_cells(bbox, cost_function):
  """Returns an efficient set of geocells to search in a bounding box query.

  This method is guaranteed to return a set of geocells having the same
  resolution.

  Args:
    bbox: A geotypes.Box indicating the bounding box being searched.
    cost_function: A function that accepts two arguments:
        * num_cells: the number of cells to search
        * resolution: the resolution of each cell to search
        and returns the 'cost' of querying against this number of cells
        at the given resolution.

  Returns:
    A list of geocell strings that contain the given box.
  """
  cell_ne = compute(bbox.north_east, resolution=MAX_GEOCELL_RESOLUTION)
  cell_sw = compute(bbox.south_west, resolution=MAX_GEOCELL_RESOLUTION)

  # The current lowest BBOX-search cost found; start with practical infinity.
  min_cost = 1e10000

  # The set of cells having the lowest calculated BBOX-search cost.
  min_cost_cell_set = None

  # First find the common prefix, if there is one.. this will be the base
  # resolution.. i.e. we don't have to look at any higher resolution cells.
  min_resolution = len(os.path.commonprefix([cell_sw, cell_ne]))

  # Iteravely calculate all possible sets of cells that wholely contain
  # the requested bounding box.
  for cur_resolution in range(min_resolution, MAX_GEOCELL_RESOLUTION + 1):
    cur_ne = cell_ne[:cur_resolution]
    cur_sw = cell_sw[:cur_resolution]

    num_cells = interpolation_count(cur_ne, cur_sw)
    if num_cells > MAX_FEASIBLE_BBOX_SEARCH_CELLS:
      continue

    cell_set = sorted(interpolate(cur_ne, cur_sw))
    simplified_cells = []

    cost = cost_function(num_cells=len(cell_set), resolution=cur_resolution)

    # TODO(romannurik): See if this resolution is even possible, as in the
    # future cells at certain resolutions may not be stored.
    if cost <= min_cost:
      min_cost = cost
      min_cost_cell_set = cell_set
    else:
      # Once the cost starts rising, we won't be able to do better, so abort.
      break

  return min_cost_cell_set


def collinear(cell1, cell2, column_test):
  """Determines whether the given cells are collinear along a dimension.

  Returns True if the given cells are in the same row (column_test=False)
  or in the same column (column_test=True).

  Args:
    cell1: The first geocell string.
    cell2: The second geocell string.
    column_test: A boolean, where False invokes a row collinearity test
        and 1 invokes a column collinearity test.

  Returns:
    A bool indicating whether or not the given cells are collinear in the given
    dimension.
  """
  for i in range(min(len(cell1), len(cell2))):
    x1, y1 = _subdiv_xy(cell1[i])
    x2, y2 = _subdiv_xy(cell2[i])

    # Check row collinearity (assure y's are always the same).
    if not column_test and y1 != y2:
      return False

    # Check column collinearity (assure x's are always the same).
    if column_test and x1 != x2:
      return False

  return True


def interpolate(cell_ne, cell_sw):
  """Calculates the grid of cells formed between the two given cells.

  Generates the set of cells in the grid created by interpolating from the
  given Northeast geocell to the given Southwest geocell.

  Assumes the Northeast geocell is actually Northeast of Southwest geocell.

  Arguments:
    cell_ne: The Northeast geocell string.
    cell_sw: The Southwest geocell string.

  Returns:
    A list of geocell strings in the interpolation.
  """
  # 2D array, will later be flattened.
  cell_set = [[cell_sw]]

  # First get adjacent geocells across until Southeast--collinearity with
  # Northeast in vertical direction (0) means we're at Southeast.
  while not collinear(cell_set[0][-1], cell_ne, True):
    cell_tmp = adjacent(cell_set[0][-1], (1, 0))
    if cell_tmp is None:
      break
    cell_set[0].append(cell_tmp)

  # Then get adjacent geocells upwards.
  while cell_set[-1][-1] != cell_ne:
    cell_tmp_row = [adjacent(g, (0, 1)) for g in cell_set[-1]]
    if cell_tmp_row[0] is None:
      break
    cell_set.append(cell_tmp_row)

  # Flatten cell_set, since it's currently a 2D array.
  return [g for inner in cell_set for g in inner]


def interpolation_count(cell_ne, cell_sw):
  """Computes the number of cells in the grid formed between two given cells.

  Computes the number of cells in the grid created by interpolating from the
  given Northeast geocell to the given Southwest geocell. Assumes the Northeast
  geocell is actually Northeast of Southwest geocell.

  Arguments:
    cell_ne: The Northeast geocell string.
    cell_sw: The Southwest geocell string.

  Returns:
    An int, indicating the number of geocells in the interpolation.
  """
  bbox_ne = compute_box(cell_ne)
  bbox_sw = compute_box(cell_sw)

  cell_lat_span = bbox_sw.north - bbox_sw.south
  cell_lon_span = bbox_sw.east - bbox_sw.west

  num_cols = int((bbox_ne.east - bbox_sw.west) / cell_lon_span)
  num_rows = int((bbox_ne.north - bbox_sw.south) / cell_lat_span)

  return num_cols * num_rows


def all_adjacents(cell):
  """Calculates all of the given geocell's adjacent geocells.

  Args:
    cell: The geocell string for which to calculate adjacent/neighboring cells.

  Returns:
    A list of 8 geocell strings and/or None values indicating adjacent cells.
  """
  return [adjacent(cell, d) for d in [NORTHWEST, NORTH, NORTHEAST, EAST,
                                      SOUTHEAST, SOUTH, SOUTHWEST, WEST]]


def adjacent(cell, dir):
  """Calculates the geocell adjacent to the given cell in the given direction.

  Args:
    cell: The geocell string whose neighbor is being calculated.
    dir: An (x, y) tuple indicating direction, where x and y can be -1, 0, or 1.
        -1 corresponds to West for x and South for y, and
         1 corresponds to East for x and North for y.
        Available helper constants are NORTH, EAST, SOUTH, WEST,
        NORTHEAST, NORTHWEST, SOUTHEAST, and SOUTHWEST.

  Returns:
    The geocell adjacent to the given cell in the given direction, or None if
    there is no such cell.
  """
  if cell is None:
    return None

  dx = dir[0]
  dy = dir[1]

  cell_adj_arr = list(cell)  # Split the geocell string characters into a list.
  i = len(cell_adj_arr) - 1

  while i >= 0 and (dx != 0 or dy != 0):
    x, y = _subdiv_xy(cell_adj_arr[i])

    # Horizontal adjacency.
    if dx == -1:  # Asking for left.
      if x == 0:  # At left of parent cell.
        x = _GEOCELL_GRID_SIZE - 1  # Becomes right edge of adjacent parent.
      else:
        x -= 1  # Adjacent, same parent.
        dx = 0  # Done with x.
    elif dx == 1:  # Asking for right.
      if x == _GEOCELL_GRID_SIZE - 1:  # At right of parent cell.
        x = 0  # Becomes left edge of adjacent parent.
      else:
        x += 1  # Adjacent, same parent.
        dx = 0  # Done with x.

    # Vertical adjacency.
    if dy == 1:  # Asking for above.
      if y == _GEOCELL_GRID_SIZE - 1:  # At top of parent cell.
        y = 0  # Becomes bottom edge of adjacent parent.
      else:
        y += 1  # Adjacent, same parent.
        dy = 0  # Done with y.
    elif dy == -1:  # Asking for below.
      if y == 0:  # At bottom of parent cell.
        y = _GEOCELL_GRID_SIZE - 1  # Becomes top edge of adjacent parent.
      else:
        y -= 1  # Adjacent, same parent.
        dy = 0  # Done with y.

    cell_adj_arr[i] = _subdiv_char((x,y))
    i -= 1

  # If we're not done with y then it's trying to wrap vertically,
  # which is a failure.
  if dy != 0:
    return None

  # At this point, horizontal wrapping is done inherently.
  return ''.join(cell_adj_arr)


def contains_point(cell, point):
  """Returns whether or not the given cell contains the given point."""
  return compute(point, len(cell)) == cell


def point_distance(cell, point):
  """Returns the shortest distance between a point and a geocell bounding box.

  If the point is inside the cell, the shortest distance is always to a 'edge'
  of the cell rectangle. If the point is outside the cell, the shortest distance
  will be to either a 'edge' or 'corner' of the cell rectangle.

  Returns:
    The shortest distance from the point to the geocell's rectangle, in meters.
  """
  bbox = compute_box(cell)

  between_w_e = bbox.west <= point.lon and point.lon <= bbox.east
  between_n_s = bbox.south <= point.lat and point.lat <= bbox.north

  if between_w_e:
    if between_n_s:
      # Inside the geocell.
      return min(geomath.distance(point, (bbox.south, point.lon)),
                 geomath.distance(point, (bbox.north, point.lon)),
                 geomath.distance(point, (point.lat, bbox.east)),
                 geomath.distance(point, (point.lat, bbox.west)))
    else:
      return min(geomath.distance(point, (bbox.south, point.lon)),
                 geomath.distance(point, (bbox.north, point.lon)))
  else:
    if between_n_s:
      return min(geomath.distance(point, (point.lat, bbox.east)),
                 geomath.distance(point, (point.lat, bbox.west)))
    else:
      # TODO(romannurik): optimize
      return min(geomath.distance(point, (bbox.south, bbox.east)),
                 geomath.distance(point, (bbox.north, bbox.east)),
                 geomath.distance(point, (bbox.south, bbox.west)),
                 geomath.distance(point, (bbox.north, bbox.west)))


def compute(point, resolution=MAX_GEOCELL_RESOLUTION):
  """Computes the geocell containing the given point to the given resolution.

  This is a simple 16-tree lookup to an arbitrary depth (resolution).

  Args:
    point: The geotypes.Point to compute the cell for.
    resolution: An int indicating the resolution of the cell to compute.

  Returns:
    The geocell string containing the given point, of length <resolution>.
  """
  north = 90.0
  south = -90.0
  east = 180.0
  west = -180.0

  cell = ''
  while len(cell) < resolution:
    subcell_lon_span = (east - west) / _GEOCELL_GRID_SIZE
    subcell_lat_span = (north - south) / _GEOCELL_GRID_SIZE

    x = min(int(_GEOCELL_GRID_SIZE * (point.lon - west) / (east - west)),
            _GEOCELL_GRID_SIZE - 1)
    y = min(int(_GEOCELL_GRID_SIZE * (point.lat - south) / (north - south)),
            _GEOCELL_GRID_SIZE - 1)

    cell += _subdiv_char((x,y))

    south += subcell_lat_span * y
    north = south + subcell_lat_span

    west += subcell_lon_span * x
    east = west + subcell_lon_span

  return cell


def compute_box(cell):
  """Computes the rectangular boundaries (bounding box) of the given geocell.

  Args:
    cell: The geocell string whose boundaries are to be computed.

  Returns:
    A geotypes.Box corresponding to the rectangular boundaries of the geocell.
  """
  if cell is None:
    return None

  bbox = geotypes.Box(90.0, 180.0, -90.0, -180.0)

  while len(cell) > 0:
    subcell_lon_span = (bbox.east - bbox.west) / _GEOCELL_GRID_SIZE
    subcell_lat_span = (bbox.north - bbox.south) / _GEOCELL_GRID_SIZE

    x, y = _subdiv_xy(cell[0])

    bbox = geotypes.Box(bbox.south + subcell_lat_span * (y + 1),
                        bbox.west  + subcell_lon_span * (x + 1),
                        bbox.south + subcell_lat_span * y,
                        bbox.west  + subcell_lon_span * x)

    cell = cell[1:]

  return bbox


def is_valid(cell):
  """Returns whether or not the given geocell string defines a valid geocell."""
  return bool(cell and reduce(lambda val, c: val and c in _GEOCELL_ALPHABET,
                              cell, True))


def children(cell):
  """Calculates the immediate children of the given geocell.

  For example, the immediate children of 'a' are 'a0', 'a1', ..., 'af'.
  """
  return [cell + chr for chr in _GEOCELL_ALPHABET]


def _subdiv_xy(char):
  """Returns the (x, y) of the geocell character in the 4x4 alphabet grid."""
  # NOTE: This only works for grid size 4.
  char = _GEOCELL_ALPHABET.index(char)
  return ((char & 4) >> 1 | (char & 1) >> 0,
          (char & 8) >> 2 | (char & 2) >> 1)


def _subdiv_char(pos):
  """Returns the geocell character in the 4x4 alphabet grid at pos. (x, y)."""
  # NOTE: This only works for grid size 4.
  return _GEOCELL_ALPHABET[
      (pos[1] & 2) << 2 |
      (pos[0] & 2) << 1 |
      (pos[1] & 1) << 1 |
      (pos[0] & 1) << 0]

########NEW FILE########
__FILENAME__ = geomath
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines common geo math functions used throughout the library."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import math

import geotypes

RADIUS = 6378135


def distance(p1, p2):
  """Calculates the great circle distance between two points (law of cosines).

  Args:
    p1: A geotypes.Point or db.GeoPt indicating the first point.
    p2: A geotypes.Point or db.GeoPt indicating the second point.

  Returns:
    The 2D great-circle distance between the two given points, in meters.
  """
  p1lat, p1lon = math.radians(p1.lat), math.radians(p1.lon)
  p2lat, p2lon = math.radians(p2.lat), math.radians(p2.lon)
  return RADIUS * math.acos(math.sin(p1lat) * math.sin(p2lat) +
      math.cos(p1lat) * math.cos(p2lat) * math.cos(p2lon - p1lon))

########NEW FILE########
__FILENAME__ = geomodel
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines the GeoModel class for running basic geospatial queries on
single-point geographic entities in Google App Engine.

TODO(romannurik): document how bounding box and proximity queries work.
"""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import copy
import logging
import math
import sys

from google.appengine.ext import db

import geocell
import geomath
import geotypes
import util

DEBUG = False


def default_cost_function(num_cells, resolution):
  """The default cost function, used if none is provided by the developer."""
  return 1e10000 if num_cells > pow(geocell._GEOCELL_GRID_SIZE, 2) else 0


class GeoModel(db.Model):
  """A base model class for single-point geographically located entities.

  Attributes:
    location: A db.GeoPt that defines the single geographic point
        associated with this entity.
  """
  location = db.GeoPtProperty(required=True)
  location_geocells = db.StringListProperty()

  def update_location(self):
    """Syncs underlying geocell properties with the entity's location.

    Updates the underlying geocell properties of the entity to match the
    entity's location property. A put() must occur after this call to save
    the changes to App Engine."""
    max_res_geocell = geocell.compute(self.location)
    self.location_geocells = [max_res_geocell[:res]
                              for res in
                              range(1, geocell.MAX_GEOCELL_RESOLUTION + 1)]

  @staticmethod
  def bounding_box_fetch(query, bbox, max_results=1000,
                         cost_function=None):
    """Performs a bounding box fetch on the given query.

    Fetches entities matching the given query with an additional filter
    matching only those entities that are inside of the given rectangular
    bounding box.

    Args:
      query: A db.Query on entities of this kind that should be additionally
          filtered by bounding box and subsequently fetched.
      bbox: A geotypes.Box indicating the bounding box to filter entities by.
      max_results: An optional int indicating the maximum number of desired
          results.
      cost_function: An optional function that accepts two arguments:
          * num_cells: the number of cells to search
          * resolution: the resolution of each cell to search
          and returns the 'cost' of querying against this number of cells
          at the given resolution.

    Returns:
      The fetched entities.

    Raises:
      Any exceptions that google.appengine.ext.db.Query.fetch() can raise.
    """
    # TODO(romannurik): Check for GqlQuery.
    results = []

    if cost_function is None:
      cost_function = default_cost_function
    query_geocells = geocell.best_bbox_search_cells(bbox, cost_function)

    if query_geocells:
      if query._Query__orderings:
        # NOTE(romannurik): since 'IN' queries seem boken in App Engine,
        # manually search each geocell and then merge results in-place
        cell_results = [copy.deepcopy(query)
            .filter('location_geocells =', search_cell)
            .fetch(max_results) for search_cell in query_geocells]

        # Manual in-memory sort on the query's defined ordering.
        query_orderings = query._Query__orderings or []
        def _ordering_fn(ent1, ent2):
          for prop, direction in query_orderings:
            prop_cmp = cmp(getattr(ent1, prop), getattr(ent2, prop))
            if prop_cmp != 0:
              return prop_cmp if direction == 1 else -prop_cmp

          return -1  # Default ent1 < ent2.

        # Duplicates aren't possible so don't provide a dup_fn.
        util.merge_in_place(cmp_fn=_ordering_fn, *cell_results)
        results = cell_results[0][:max_results]
      else:
        # NOTE: We can't pass in max_results because of non-uniformity of the
        # search.
        results = (query
            .filter('location_geocells IN', query_geocells)
            .fetch(1000))[:max_results]
    else:
      results = []

    if DEBUG:
      logging.info('bbox query looked in %d geocells' % len(query_geocells))

    # In-memory filter.
    return [entity for entity in results if
        entity.location.lat >= bbox.south and
        entity.location.lat <= bbox.north and
        entity.location.lon >= bbox.west and
        entity.location.lon <= bbox.east]

  @staticmethod
  def proximity_fetch(query, center, max_results=10, max_distance=0):
    """Performs a proximity/radius fetch on the given query.

    Fetches at most <max_results> entities matching the given query,
    ordered by ascending distance from the given center point, and optionally
    limited by the given maximum distance.

    This method uses a greedy algorithm that starts by searching high-resolution
    geocells near the center point and gradually looking in lower and lower
    resolution cells until max_results entities have been found matching the
    given query and no closer possible entities can be found.

    Args:
      query: A db.Query on entities of this kind.
      center: A geotypes.Point or db.GeoPt indicating the center point around
          which to search for matching entities.
      max_results: An int indicating the maximum number of desired results.
          The default is 10, and the larger this number, the longer the fetch
          will take.
      max_distance: An optional number indicating the maximum distance to
          search, in meters.

    Returns:
      The fetched entities, sorted in ascending order by distance to the search
      center.

    Raises:
      Any exceptions that google.appengine.ext.db.Query.fetch() can raise.
    """
    # TODO(romannurik): check for GqlQuery
    results = []

    searched_cells = set()

    # The current search geocell containing the lat,lon.
    cur_containing_geocell = geocell.compute(center)

    # The currently-being-searched geocells.
    # NOTES:
    #     * Start with max possible.
    #     * Must always be of the same resolution.
    #     * Must always form a rectangular region.
    #     * One of these must be equal to the cur_containing_geocell.
    cur_geocells = [cur_containing_geocell]

    closest_possible_next_result_dist = 0

    # Assumes both a and b are lists of (entity, dist) tuples, *sorted by dist*.
    # NOTE: This is an in-place merge, and there are guaranteed
    # no duplicates in the resulting list.
    def _merge_results_in_place(a, b):
      util.merge_in_place(a, b,
                        cmp_fn=lambda x, y: cmp(x[1], y[1]),
                        dup_fn=lambda x, y: x[0].key() == y[0].key())

    sorted_edges = [(0,0)]
    sorted_edge_distances = [0]

    while cur_geocells:
      closest_possible_next_result_dist = sorted_edge_distances[0]
      if max_distance and closest_possible_next_result_dist > max_distance:
        break

      cur_geocells_unique = list(set(cur_geocells).difference(searched_cells))

      # Run query on the next set of geocells.
      cur_resolution = len(cur_geocells[0])
      temp_query = copy.deepcopy(query)  # TODO(romannurik): is this safe?
      temp_query.filter('location_geocells IN', cur_geocells_unique)

      # Update results and sort.
      new_results = temp_query.fetch(1000)
      if DEBUG:
        logging.info('fetch complete for %s' % (','.join(cur_geocells_unique),))

      searched_cells.update(cur_geocells)

      # Begin storing distance from the search result entity to the
      # search center along with the search result itself, in a tuple.
      new_results = [(entity, geomath.distance(center, entity.location))
                     for entity in new_results]
      new_results = sorted(new_results, lambda dr1, dr2: cmp(dr1[1], dr2[1]))
      new_results = new_results[:max_results]

      # Merge new_results into results or the other way around, depending on
      # which is larger.
      if len(results) > len(new_results):
        _merge_results_in_place(results, new_results)
      else:
        _merge_results_in_place(new_results, results)
        results = new_results

      results = results[:max_results]

      sorted_edges, sorted_edge_distances = \
          util.distance_sorted_edges(cur_geocells, center)

      if len(results) == 0 or len(cur_geocells) == 4:
        # Either no results (in which case we optimize by not looking at
        # adjacents, go straight to the parent) or we've searched 4 adjacent
        # geocells, in which case we should now search the parents of those
        # geocells.
        cur_containing_geocell = cur_containing_geocell[:-1]
        cur_geocells = list(set([cell[:-1] for cell in cur_geocells]))
        if not cur_geocells or not cur_geocells[0]:
          break  # Done with search, we've searched everywhere.

      elif len(cur_geocells) == 1:
        # Get adjacent in one direction.
        # TODO(romannurik): Watch for +/- 90 degree latitude edge case geocells.
        nearest_edge = sorted_edges[0]
        cur_geocells.append(geocell.adjacent(cur_geocells[0], nearest_edge))

      elif len(cur_geocells) == 2:
        # Get adjacents in perpendicular direction.
        nearest_edge = util.distance_sorted_edges([cur_containing_geocell],
                                                   center)[0][0]
        if nearest_edge[0] == 0:
          # Was vertical, perpendicular is horizontal.
          perpendicular_nearest_edge = [x for x in sorted_edges if x[0] != 0][0]
        else:
          # Was horizontal, perpendicular is vertical.
          perpendicular_nearest_edge = [x for x in sorted_edges if x[0] == 0][0]

        cur_geocells.extend(
            [geocell.adjacent(cell, perpendicular_nearest_edge)
             for cell in cur_geocells])

      # We don't have enough items yet, keep searching.
      if len(results) < max_results:
        if DEBUG:
          logging.debug('have %d results but want %d results, '
                        'continuing search' % (len(results), max_results))
        continue

      if DEBUG:
        logging.debug('have %d results' % (len(results),))

      # If the currently max_results'th closest item is closer than any
      # of the next test geocells, we're done searching.
      current_farthest_returnable_result_dist = \
          geomath.distance(center, results[max_results - 1][0].location)
      if (closest_possible_next_result_dist >=
          current_farthest_returnable_result_dist):
        if DEBUG:
          logging.debug('DONE next result at least %f away, '
                        'current farthest is %f dist' %
                        (closest_possible_next_result_dist,
                         current_farthest_returnable_result_dist))
        break

      if DEBUG:
        logging.debug('next result at least %f away, '
                      'current farthest is %f dist' %
                      (closest_possible_next_result_dist,
                       current_farthest_returnable_result_dist))

    if DEBUG:
      logging.info('proximity query looked '
                   'in %d geocells' % len(searched_cells))

    return [entity for (entity, dist) in results[:max_results]
            if not max_distance or dist < max_distance]
########NEW FILE########
__FILENAME__ = geotypes
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines some useful geo types such as points and boxes."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'


class Point(object):
  """A two-dimensional point in the [-90,90] x [-180,180] lat/lon space.

  Attributes:
    lat: A float in the range [-90,90] indicating the point's latitude.
    lon: A float in the range [-180,180] indicating the point's longitude.
  """

  def __init__(self, lat, lon):
    """Initializes a point with the given latitude and longitude."""
    if -90 > lat or lat > 90:
      raise ValueError("Latitude must be in [-90, 90] but was %f" % lat)
    if -180 > lon or lon > 180:
      raise ValueError("Longitude must be in [-180, 180] but was %f" % lon)

    self.lat = lat
    self.lon = lon

  def __eq__(self, other):
    return self.lat == other.lat and self.lon == other.lon

  def __str__(self):
    return '(%f, %f)' % (self.lat, self.lon)


class Box(object):
  """A two-dimensional rectangular region defined by NE and SW points.

  Attributes:
    north_east: A read-only geotypes.Point indicating the box's Northeast
        coordinate.
    south_west: A read-only geotypes.Point indicating the box's Southwest
        coordinate.
    north: A float indicating the box's North latitude.
    east: A float indicating the box's East longitude.
    south: A float indicating the box's South latitude.
    west: A float indicating the box's West longitude.
  """

  def __init__(self, north, east, south, west):
    # TODO(romannurik): port geojs LatLonBox here
    if south > north:
      south, north = north, south

    # Don't swap east and west to allow disambiguation of
    # antimeridian crossing.

    self._ne = Point(north, east)
    self._sw = Point(south, west)

  north_east = property(lambda self: self._ne)
  south_west = property(lambda self: self._sw)

  def _set_north(self, val):
    if val < self._sw.lat:
      raise ValueError("Latitude must be north of box's south latitude")
    self._ne.lat = val
  north = property(lambda self: self._ne.lat, _set_north)

  def _set_east(self, val):
    self._ne.lat = val
  east  = property(lambda self: self._ne.lon, _set_east)

  def _set_south(self, val):
    if val > self._ne.lat:
      raise ValueError("Latitude must be south of box's north latitude")
    self._sw.lat = val
  south = property(lambda self: self._sw.lat, _set_south)

  def _set_west(self, val):
    self._sw.lon = val
  west  = property(lambda self: self._sw.lon, _set_west)

  def __eq__(self, other):
    return self._ne == other._ne and self._sw == other._sw

  def __str__(self):
    return '(N:%f, E:%f, S:%f, W:%f)' % (self.north, self.east,
                                         self.south, self.west)

########NEW FILE########
__FILENAME__ = geocell_test
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for geocell.py."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import unittest

from geo import geocell
from geo import geotypes


class GeocellTests(unittest.TestCase):
  def test_compute(self):
    # a valid geocell
    cell = geocell.compute(geotypes.Point(37, -122), 14)
    self.assertEqual(14, len(cell))
    self.assertTrue(geocell.is_valid(cell))
    self.assertTrue(geocell.contains_point(cell, geotypes.Point(37, -122)))

    # a lower resolution cell should be a prefix to a higher resolution
    # cell containing the same point
    lowres_cell = geocell.compute(geotypes.Point(37, -122), 8)
    self.assertTrue(cell.startswith(lowres_cell))
    self.assertTrue(geocell.contains_point(lowres_cell,
                                          geotypes.Point(37, -122)))

    # an invalid geocell
    cell = geocell.compute(geotypes.Point(0, 0), 0)
    self.assertEqual(0, len(cell))
    self.assertFalse(geocell.is_valid(cell))

  def test_compute_box(self):
    cell = geocell.compute(geotypes.Point(37, -122), 14)
    box = geocell.compute_box(cell)

    self.assertTrue(box.south <= 37 and 37 <= box.north and
                    box.west <= -122 and -122 <= box.east)

  def test_adjacent(self):
    cell = geocell.compute(geotypes.Point(37, -122), 14)
    box = geocell.compute_box(cell)

    # adjacency tests using bounding boxes
    self.assertEquals(box.north,
        geocell.compute_box(geocell.adjacent(cell, (0, 1))).south)
    self.assertEquals(box.south,
        geocell.compute_box(geocell.adjacent(cell, (0, -1))).north)
    self.assertEquals(box.east,
        geocell.compute_box(geocell.adjacent(cell, (1, 0))).west)
    self.assertEquals(box.west,
        geocell.compute_box(geocell.adjacent(cell, (-1, 0))).east)

    self.assertEquals(8, len(geocell.all_adjacents(cell)))

    # also test collinearity
    self.assertTrue(
        geocell.collinear(cell, geocell.adjacent(cell, (0, 1)), True))
    self.assertFalse(
        geocell.collinear(cell, geocell.adjacent(cell, (0, 1)), False))
    self.assertTrue(
        geocell.collinear(cell, geocell.adjacent(cell, (1, 0)), False))
    self.assertFalse(
        geocell.collinear(cell, geocell.adjacent(cell, (1, 0)), True))

  def test_interpolation(self):
    cell = geocell.compute(geotypes.Point(37, -122), 14)
    sw_adjacent = geocell.adjacent(cell, (-1, -1))
    sw_adjacent2 = geocell.adjacent(sw_adjacent, (-1, -1))

    # interpolate between a cell and south-west adjacent, should return
    # 4 total cells
    self.assertEquals(4, len(geocell.interpolate(cell, sw_adjacent)))
    self.assertEquals(4, geocell.interpolation_count(cell, sw_adjacent))

    # interpolate between a cell and the cell SW-adjacent twice over,
    # should return 9 total cells
    self.assertEquals(9, len(geocell.interpolate(cell, sw_adjacent2)))
    self.assertEquals(9, geocell.interpolation_count(cell, sw_adjacent2))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = geomath_test
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for geomath.py."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import unittest

from geo import geomath
from geo import geotypes


class GeomathTests(unittest.TestCase):
  def test_distance(self):
    # known distances using GLatLng from the Maps API
    calc_dist = geomath.distance(geotypes.Point(37, -122),
                                 geotypes.Point(42, -75))
    known_dist = 4024365

    # make sure the calculated distance is within +/- 1% of known distance
    self.assertTrue(abs((calc_dist - known_dist) / known_dist) <= 0.01)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = geotypes_test
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for geotypes.py."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import unittest

from geo import geotypes


class PointTests(unittest.TestCase):
  def test_Point(self):
    # an invalid point
    self.assertRaises(ValueError, geotypes.Point, 95, 0)
    self.assertRaises(ValueError, geotypes.Point, 0, 185)

    # a valid point
    point = geotypes.Point(37, -122)
    self.assertEquals(37, point.lat)
    self.assertEquals(-122, point.lon)

    self.assertTrue(isinstance(point.__str__(), str))

    self.assertEquals(geotypes.Point(37, -122), geotypes.Point(37, -122))
    self.assertNotEquals(geotypes.Point(37, -122), geotypes.Point(0, 0))

class BoxTests(unittest.TestCase):
  def test_Box(self):
    # an invalid box
    self.assertRaises(ValueError, geotypes.Box, 95, 0, 0, 0)

    # a valid box
    box = geotypes.Box(37, -122, 34, -125)
    self.assertEquals(37, box.north)
    self.assertEquals(34, box.south)
    self.assertEquals(-122, box.east)
    self.assertEquals(-125, box.west)

    # assert north can't be under south
    self.assertRaises(ValueError, box._set_north, 32)
    self.assertRaises(ValueError, box._set_south, 39)

    self.assertTrue(isinstance(box.__str__(), str))

    # valid boxes
    self.assertEquals(
        geotypes.Box(37, -122, 34, -125),
        geotypes.Box(34, -122, 37, -125))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = util_test
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for util.py."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import unittest

from geo import util


class MergeInPlaceTests(unittest.TestCase):
  def test_merge_in_place(self):
    self.assertEquals([], util.merge_in_place())

    # test massive list merge
    list1 = [0, 1, 5, 6, 8, 9, 15]
    list2 = [0, 2, 3, 5, 8, 10, 11, 17]
    list3 = [1, 4, 6, 8, 10, 15, 16]
    list4 = [-1, 19]
    list5 = [20]
    list6 = []

    util.merge_in_place(list1, list2, list3, list4, list5, list6,
        dup_fn=lambda x, y: x == y)

    self.assertEquals(
        [-1, 0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 15, 16, 17, 19, 20],
        list1)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines utility functions used throughout the geocell/GeoModel library."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import geocell
import geomath
import geotypes


def merge_in_place(*lists, **kwargs):
  """Merges an arbitrary number of pre-sorted lists in-place, into the first
  list, possibly pruning out duplicates. Source lists must not have
  duplicates.

  Args:
    list1: The first, sorted list into which the other lists should be merged.
    list2: A subsequent, sorted list to merge into the first.
    ...
    listn:  "   "
    cmp_fn: An optional binary comparison function that compares objects across
        lists and determines the merged list's sort order.
    dup_fn: An optional binary comparison function that should return True if
        the given objects are equivalent and one of them can be pruned from the
        resulting merged list.

  Returns:
    list1, in-placed merged wit the other lists, or an empty list if no lists
    were specified.
  """
  cmp_fn = kwargs.get('cmp_fn') or cmp
  dup_fn = kwargs.get('dup_fn') or None

  if not lists:
    return []

  reverse_indices = [len(arr) for arr in lists]
  aggregate_reverse_index = sum(reverse_indices)

  while aggregate_reverse_index > 0:
    pull_arr_index = None
    pull_val = None

    for i in range(len(lists)):
      if reverse_indices[i] == 0:
        # Reached the end of this list.
        pass
      elif (pull_arr_index is not None and
            dup_fn and dup_fn(lists[i][-reverse_indices[i]], pull_val)):
        # Found a duplicate, advance the index of the list in which the
        # duplicate was found.
        reverse_indices[i] -= 1
        aggregate_reverse_index -= 1
      elif (pull_arr_index is None or
            cmp_fn(lists[i][-reverse_indices[i]], pull_val) < 0):
        # Found a lower value.
        pull_arr_index = i
        pull_val = lists[i][-reverse_indices[i]]

    if pull_arr_index != 0:
      # Add the lowest found value in place into the first array.
      lists[0].insert(len(lists[0]) - reverse_indices[0], pull_val)

    aggregate_reverse_index -= 1
    reverse_indices[pull_arr_index] -= 1

  return lists[0]


def distance_sorted_edges(cells, point):
  """Returns the edges of the rectangular region containing all of the
  given geocells, sorted by distance from the given point, along with
  the actual distances from the point to these edges.

  Args:
    cells: The cells (should be adjacent) defining the rectangular region
        whose edge distances are requested.
    point: The point that should determine the edge sort order.

  Returns:
    A list of (direction, distance) tuples, where direction is the edge
    and distance is the distance from the point to that edge. A direction
    value of (0,-1), for example, corresponds to the South edge of the
    rectangular region containing all of the given geocells.
  """
  # TODO(romannurik): Assert that lat,lon are actually inside the geocell.
  boxes = [geocell.compute_box(cell) for cell in cells]

  max_box = geotypes.Box(max([box.north for box in boxes]),
                         max([box.east for box in boxes]),
                         min([box.south for box in boxes]),
                         min([box.west for box in boxes]))
  return zip(*sorted([
      ((0,-1), geomath.distance(geotypes.Point(max_box.south, point.lon),
                                point)),
      ((0,1),  geomath.distance(geotypes.Point(max_box.north, point.lon),
                                point)),
      ((-1,0), geomath.distance(geotypes.Point(point.lat, max_box.west),
                                point)),
      ((1,0),  geomath.distance(geotypes.Point(point.lat, max_box.east),
                                point))],
      lambda x, y: cmp(x[1], y[1])))

########NEW FILE########
__FILENAME__ = color_scheme
import pngcanvas
import os

TRANSPARENCY = 100

def createScheme(steps=255, r_start=255, g_start=255, b_start=255,
    r_step=-3.0, g_step=-1.0, b_step=-1.0):
  img = pngcanvas.PNGCanvas(30, steps)
  r_cur = r_start
  g_cur = g_start
  b_cur = b_start
  for y in range(0, steps):
    for x in range(0, 30):
      img.canvas[y][x] = [ r_cur, g_cur, b_cur, TRANSPARENCY]
    r_cur += r_step
    g_cur += g_step
    b_cur += b_step
    if r_cur > 255: r_step *= -1; r_cur = 255 + r_step;
    if r_cur < 0: r_step *= -1; r_cur = 0 + r_step;
    if g_cur > 255: g_step *= -1; g_cur = 255 + g_step;
    if g_cur < 0: g_step *= -1; g_cur = 0 + g_step;
    if b_cur > 255: b_step *= -1; b_cur = 255 + b_step;
    if b_cur < 0: b_step *= -1; b_cur = 0 + b_step;
  return img

def loadScheme(name, steps=255):
  ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
  file_loc = os.path.join(ROOT_DIR, 'color-schemes/' + name + '.png')
  f = open(file_loc, "rb")
  img = pngcanvas.PNGCanvas(24, steps, bgcolor=[0xff,0xff,0xff,TRANSPARENCY])
  img.load(f)
  f.close()
  return img

color_schemes = { 'fire': loadScheme("fire"),
                  'water': loadScheme("water"),
                  #'wp-barthelme': loadScheme("wp-barthelme"),
                  'cyan-red': createScheme(),
                  'classic': loadScheme("classic"),
                  'omg': loadScheme("omg"),
                  'pbj': loadScheme("pbj"),
                  'pgaitch': loadScheme("pgaitch"),
                  'classic-v2': loadScheme("classic2"),
                  'pgaitch-v2': loadScheme("pgaitch2")
                }
########NEW FILE########
__FILENAME__ = gmerc
"""This is a port of Google's GMercatorProjection.fromLatLngToPixel.

Doco on the original:

  http://code.google.com/apis/maps/documentation/reference.html#GMercatorProjection


Here's how I ported it:

  http://blag.whit537.org/2007/07/how-to-hack-on-google-maps.html


The goofy variable names below are an artifact of Google's javascript
obfuscation.

"""
import math


# Constants
# =========
# My knowledge of what these mean is undefined.

CBK = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912, 1073741824, 2147483648, 4294967296, 8589934592, 17179869184, 34359738368, 68719476736, 137438953472]
CEK = [0.7111111111111111, 1.4222222222222223, 2.8444444444444446, 5.688888888888889, 11.377777777777778, 22.755555555555556, 45.51111111111111, 91.02222222222223, 182.04444444444445, 364.0888888888889, 728.1777777777778, 1456.3555555555556, 2912.711111111111, 5825.422222222222, 11650.844444444445, 23301.68888888889, 46603.37777777778, 93206.75555555556, 186413.51111111112, 372827.02222222224, 745654.0444444445, 1491308.088888889, 2982616.177777778, 5965232.355555556, 11930464.711111112, 23860929.422222223, 47721858.844444446, 95443717.68888889, 190887435.37777779, 381774870.75555557, 763549741.5111111]
CFK = [40.74366543152521, 81.48733086305042, 162.97466172610083, 325.94932345220167, 651.8986469044033, 1303.7972938088067, 2607.5945876176133, 5215.189175235227, 10430.378350470453, 20860.756700940907, 41721.51340188181, 83443.02680376363, 166886.05360752725, 333772.1072150545, 667544.214430109, 1335088.428860218, 2670176.857720436, 5340353.715440872, 10680707.430881744, 21361414.86176349, 42722829.72352698, 85445659.44705395, 170891318.8941079, 341782637.7882158, 683565275.5764316, 1367130551.1528633, 2734261102.3057265, 5468522204.611453, 10937044409.222906, 21874088818.445812, 43748177636.891624]


def ll2px(lat, lng, zoom):
    """Given two floats and an int, return a 2-tuple of ints.

    Note that the pixel coordinates are tied to the entire map, not to the map
    section currently in view.

    """
    assert isinstance(lat, (float, int, long)), \
        ValueError("lat must be a float")
    lat = float(lat)
    assert isinstance(lng, (float, int, long)), \
        ValueError("lng must be a float")
    lng = float(lng)
    assert isinstance(zoom, int), TypeError("zoom must be an int from 0 to 30")
    assert 0 <= zoom <= 30, ValueError("zoom must be an int from 0 to 30")

    cbk = CBK[zoom]

    x = int(round(cbk + (lng * CEK[zoom])))

    foo = math.sin(lat * math.pi / 180)
    if foo < -0.9999:
        foo = -0.9999
    elif foo > 0.9999:
        foo = 0.9999

    y = int(round(cbk + (0.5 * math.log((1+foo)/(1-foo)) * (-CFK[zoom]))))

    return (x, y)



def px2ll(x, y, zoom):
    """Given three ints, return a 2-tuple of floats.

    Note that the pixel coordinates are tied to the entire map, not to the map
    section currently in view.

    """
    assert isinstance(x, (int, long)), \
        ValueError("px must be a 2-tuple of ints")
    assert isinstance(y, (int, long)), \
        ValueError("px must be a 2-tuple of ints")
    assert isinstance(zoom, int), TypeError("zoom must be an int from 0 to 30")
    assert 0 <= zoom <= 30, ValueError("zoom must be an int from 0 to 30")

    foo = CBK[zoom]
    lng = (x - foo) / CEK[zoom]
    bar = (y - foo) / -CFK[zoom]
    blam = 2 * math.atan(math.exp(bar)) - math.pi / 2
    lat = blam / (math.pi / 180)

    return (lat, lng)


if __name__ == '__main__':

    # Tests
    # =====
    # The un-round numbers were gotten by calling Google's js function.

    data = [ (3, 39.81447, -98.565388, 463, 777)
           , (3, 40.609538, -80.224528, 568, 771)

           , (0, -90, 180, 256, 330)
           , (0, -90, -180, 0, 330)
           , (0, 90, 180, 256, -74)
           , (0, 90, -180, 0, -74)

           , (1, -90, 180, 512, 660)
           , (1, -90, -180, 0, 660)
           , (1, 90, 180, 512, -148)
           , (1, 90, -180, 0, -148)

           , (2, -90, 180, 1024, 1319)
           , (2, -90, -180, 0, 1319)
           , (2, 90, 180, 1024, -295)
           , (2, 90, -180, 0, -295)

            ]

    def close(floats, floats2):
        """Compare two sets of floats.
        """
        lat_actual = abs(floats[0] - floats2[0])
        lng_actual = abs(floats[1] - floats2[1])
        assert lat_actual < 1, (floats[0], floats2[0])
        assert lng_actual < 1, (floats[1], floats2[1])
        return True

    for zoom, lat, lng, x, y in data:
        assert ll2px(lat, lng, zoom) == (x, y), (lat, lng)
        assert close(px2ll(x, y, zoom), (lat, lng)), (x, y)

########NEW FILE########
__FILENAME__ = pngcanvas
#!/usr/bin/env python

"""Simple PNG Canvas for Python"""
__version__ = "0.8"
__author__ = "Rui Carmo (http://the.taoofmac.com)"
__copyright__ = "CC Attribution-NonCommercial-NoDerivs 2.0 Rui Carmo"
__contributors__ = ["http://collaboa.weed.rbse.com/repository/file/branches/pgsql/lib/spark_pr.rb"], ["Eli Bendersky"]

import zlib, struct

signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)

# alpha blends two colors, using the alpha given by c2
def blend(c1, c2):
  return [c1[i]*(0xFF-c2[3]) + c2[i]*c2[3] >> 8 for i in range(3)]

# calculate a new alpha given a 0-0xFF intensity
def intensity(c,i):
  return [c[0],c[1],c[2],(c[3]*i) >> 8]

# calculate perceptive grayscale value
def grayscale(c):
  return int(c[0]*0.3 + c[1]*0.59 + c[2]*0.11)

# calculate gradient colors
def gradientList(start,end,steps):
  delta = [end[i] - start[i] for i in range(4)]
  grad = []
  for i in range(steps+1):
    grad.append([start[j] + (delta[j]*i)/steps for j in range(4)])
  return grad

class PNGCanvas:
  def __init__(self, width, height,bgcolor=[0xff,0xff,0xff,0xff],color=[0,0,0,0xff]):
    self.canvas = []
    self.width = width
    self.height = height
    self.color = color #rgba
    bgcolor = bgcolor[0:4] # we don't need alpha for background
    for i in range(height):
      self.canvas.append([bgcolor] * width)

  def point(self,x,y,color=None):
    if x<0 or y<0 or x>self.width-1 or y>self.height-1: return
    if color == None: color = self.color
    self.canvas[y][x] = blend(self.canvas[y][x],color)

  def _rectHelper(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    return [x0,y0,x1,y1]

  def verticalGradient(self,x0,y0,x1,y1,start,end):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    grad = gradientList(start,end,y1-y0)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,grad[y-y0])

  def rectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    self.polyline([[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]])

  def filledRectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,self.color)

  def copyRect(self,x0,y0,x1,y1,dx,dy,destination):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        destination.canvas[dy+y-y0][dx+x-x0] = self.canvas[y][x]

  def blendRect(self,x0,y0,x1,y1,dx,dy,destination,alpha=0xff):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        rgba = self.canvas[y][x] + [alpha]
        destination.point(dx+x-x0,dy+y-y0,rgba)

  # draw a line using Xiaolin Wu's antialiasing technique
  def line(self,x0, y0, x1, y1):
    # clean params
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if y0>y1:
      y0, y1, x0, x1 = y1, y0, x1, x0
    dx = x1-x0
    if dx < 0:
      sx = -1
    else:
      sx = 1
    dx *= sx
    dy = y1-y0

    # 'easy' cases
    if dy == 0:
      for x in range(x0,x1,sx):
        self.point(x, y0)
      return
    if dx == 0:
      for y in range(y0,y1):
        self.point(x0, y)
      self.point(x1, y1)
      return
    if dx == dy:
      for x in range(x0,x1,sx):
        self.point(x, y0)
        y0 = y0 + 1
      return

    # main loop
    self.point(x0, y0)
    e_acc = 0
    if dy > dx: # vertical displacement
      e = (dx << 16) / dy
      for i in range(y0,y1-1):
        e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
        if (e_acc <= e_acc_temp):
          x0 = x0 + sx
        w = 0xFF-(e_acc >> 8)
        self.point(x0, y0, intensity(self.color,(w)))
        y0 = y0 + 1
        self.point(x0 + sx, y0, intensity(self.color,(0xFF-w)))
      self.point(x1, y1)
      return

    # horizontal displacement
    e = (dy << 16) / dx
    for i in range(x0,x1-sx,sx):
      e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
      if (e_acc <= e_acc_temp):
        y0 = y0 + 1
      w = 0xFF-(e_acc >> 8)
      self.point(x0, y0, intensity(self.color,(w)))
      x0 = x0 + sx
      self.point(x0, y0 + 1, intensity(self.color,(0xFF-w)))
    self.point(x1, y1)

  def polyline(self,arr):
    for i in range(0,len(arr)-1):
      self.line(arr[i][0],arr[i][1],arr[i+1][0], arr[i+1][1])

  def dump(self):
    raw_list = []
    for y in range(self.height):
      raw_list.append(chr(0)) # filter type 0 (None)
      for x in range(self.width):
        raw_list.append(struct.pack("!4B",*self.canvas[y][x]))
        #raw_list.append(struct.pack("!3B",*self.canvas[y][x]))
    raw_data = ''.join(raw_list)

    # 8-bit image represented as RGB tuples
    # simple transparency, alpha is pure white
    return signature + \
      self.pack_chunk('IHDR', struct.pack("!2I5B",self.width,self.height,8,6,0,0,0)) + \
      self.pack_chunk('tRNS', struct.pack("!6B",0xFF,0xFF,0xFF,0xFF,0xFF,0xFF)) + \
      self.pack_chunk('IDAT', zlib.compress(raw_data,9)) + \
      self.pack_chunk('IEND', '')
      #self.pack_chunk('IHDR', struct.pack("!2I5B",self.width,self.height,8,6,0,0,0)) + \

  def pack_chunk(self,tag,data):
    to_check = tag + data
    return struct.pack("!I",len(data)) + to_check + struct.pack("!I", zlib.crc32(to_check) & 0xFFFFFFFF)

  def load(self,f):
    assert f.read(8) == signature
    self.canvas=[]
    for tag, data in self.chunks(f):
      if tag == "IHDR":
        ( width,
          height,
          bitdepth,
          colortype,
          compression, filter, interlace ) = struct.unpack("!2I5B",data)
        self.width = width
        self.height = height
        if (bitdepth,colortype,compression, filter, interlace) != (8,2,0,0,0):
          raise TypeError('Unsupported PNG format')
      # we ignore tRNS because we use pure white as alpha anyway
      elif tag == 'IDAT':
        raw_data = zlib.decompress(data)
        rows = []
        i = 0
        for y in range(height):
          filtertype = ord(raw_data[i])
          i = i + 1
          cur = [ord(x) for x in raw_data[i:i+width*3]]
          if y == 0:
            rgb = self.defilter(cur,None,filtertype)
          else:
            rgb = self.defilter(cur,prev,filtertype)
          prev = cur
          i = i+width*3
          row = []
          j = 0
          for x in range(width):
            pixel = rgb[j:j+3]
            pixel.append(100)
            row.append(pixel)
            j = j + 3
          self.canvas.append(row)

  def defilter(self,cur,prev,filtertype,bpp=3):
    if filtertype == 0: # No filter
      return cur
    elif filtertype == 1: # Sub
      xp = 0
      for xc in range(bpp,len(cur)):
        cur[xc] = (cur[xc] + cur[xp]) % 256
        xp = xp + 1
    elif filtertype == 2: # Up
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + prev[xc]) % 256
    elif filtertype == 3: # Average
      xp = 0
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + (cur[xp] + prev[xc])/2) % 256
        xp = xp + 1
    elif filtertype == 4: # Paeth
      xp = 0
      for i in range(bpp):
        cur[i] = (cur[i] + prev[i]) % 256
      for xc in range(bpp,len(cur)):
        a = cur[xp]
        b = prev[xc]
        c = prev[xp]
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
          value = a
        elif pb <= pc:
          value = b
        else:
          value = c
        cur[xc] = (cur[xc] + value) % 256
        xp = xp + 1
    else:
      raise TypeError('Unrecognized scanline filter type')
    return cur

  def chunks(self,f):
    while 1:
      try:
        length = struct.unpack("!I",f.read(4))[0]
        tag = f.read(4)
        data = f.read(length)
        crc = struct.unpack("!i",f.read(4))[0]
      except:
        return
      #SJL http://conceptualadvantage.com/grow-your-concept/using-google-appengine-and-the-pure-python-pngcanvas/
      # if zlib.crc32(tag + data) != crc:
      #   raise IOError
      yield [tag,data]

if __name__ == '__main__':
  width = 128
  height = 64
  print "Creating Canvas..."
  c = PNGCanvas(width,height)
  c.color = [0xff,0,0,0xff]
  c.rectangle(0,0,width-1,height-1)
  print "Generating Gradient..."
  c.verticalGradient(1,1,width-2, height-2,[0xff,0,0,0xff],[0x20,0,0xff,0x80])
  print "Drawing Lines..."
  c.color = [0,0,0,0xff]
  c.line(0,0,width-1,height-1)
  c.line(0,0,width/2,height-1)
  c.line(0,0,width-1,height/2)
  # Copy Rect to Self
  print "Copy Rect"
  c.copyRect(1,1,width/2-1,height/2-1,0,height/2,c)
  # Blend Rect to Self
  print "Blend Rect"
  c.blendRect(1,1,width/2-1,height/2-1,width/2,0,c)
  # Write test
  print "Writing to file..."
  f = open("test.png", "wb")
  f.write(c.dump())
  f.close()
  # Read test
  print "Reading from file..."
  f = open("test.png", "rb")
  c.load(f)
  f.close()
  # Write back
  print "Writing to new file..."
  f = open("recycle.png","wb")
  f.write(c.dump())
  f.close()
########NEW FILE########
__FILENAME__ = provider
from geo import geotypes
from google.appengine.api.datastore_types import GeoPt
from models import UserVenue
import logging

log = logging.getLogger('tile')

class Provider(object):
  def __init__(self):
    pass

  def get_data(self, layer, x, y):
    pass

class DBProvider(Provider):
  def get_user_data(self, user=None, lat_north=90, lng_west=-180, range_lat=-180, range_lng=360, max_results=2000):
    # log.info("GeoRange: (%6.4f, %6.4f) ZoomStep: (%6.4f, %6.4f)" % (lat_north, lng_west, range_lat, range_lng))
    # log.info("Range: (%6.4f - %6.4f), (%6.4f - %6.4f)" % (min(90, max(-90, lat_north + range_lat)), lat_north, min(180, max(-180, lng_west + range_lng)), lng_west))
    if user:
      # not sure why Google was giving latitudes outside of the allowable range near the International Date Line at zoom level 3,
      # but cap it to the max anyway here. this might result in incorrectly drawn tiles near there, but oh well.
      if lng_west < -180:
        lng_west = -180
      return UserVenue.bounding_box_fetch(UserVenue.all().filter('user =', user).order('-last_checkin_at'), #TODO find a way to specify this elsewhere!!
        geotypes.Box(min(90, max(-90, lat_north + range_lat)),
            min(180, max(-180, lng_west + range_lng)),
            lat_north,
            lng_west),
        max_results, )
    else:
      return []

  def get_all_data(self, user=None, lat_north=90, lng_west=-180, range_lat=-180, range_lng=360, max_results=2000):
    if user:
      self.get_user_data(user, lat_north, lng_west, range_lat, range_lng, max_results)
    else:
      return UserVenue.bounding_box_fetch(UserVenue.all().order('-last_checkin_at'),
        geotypes.Box(min(90, max(-90, lat_north + range_lat)),
            min(180, max(-180, lng_west + range_lng)),
            lat_north,
            lng_west),
        max_results, )

########NEW FILE########
__FILENAME__ = tile
import constants
from gheatae import color_scheme, provider
from pngcanvas import PNGCanvas
from random import random, Random
import logging
import gmerc
import math
from models import UserInfo
from datetime import datetime

from google.appengine.api import users
log = logging.getLogger('space_level')

rdm = Random()

DOT_MULT = 3
SIZE = 256
MAX_ALPHA = 100

class BasicTile(object):
  def __init__(self, user, lat_north, lng_west, range_lat, range_lng):
    userinfo = UserInfo.all().filter('user =', user).get()
    if userinfo:
      self.level_max = userinfo.level_max
      self.color_scheme = color_scheme.color_schemes[userinfo.color_scheme]
    else:
      self.level_max = int(constants.level_const)
      self.color_scheme = color_scheme.color_schemes[constants.default_color]
    if not constants.provider:
      constants.provider = provider.DBProvider()
    uservenues = constants.provider.get_user_data(user, lat_north, lng_west, range_lat, range_lng)
    if uservenues and len(uservenues):
      if len(uservenues) > 1000:
        logging.warning("%d uservenues found for this tile - maybe too many?" % len(uservenues))
      self.cache_levels = []
      for i in range(self.level_max - 1, -1, -1):
        self.cache_levels.append(int(((-(pow(float(i) - self.level_max, 2))/self.level_max) + self.level_max) / self.level_max * 255))
      self.tile_img = self.plot_image(uservenues)
    else: # don't do any more math if we don't have any venues
      cur_canvas = self.color_scheme.canvas
      self.tile_img = PNGCanvas(SIZE, SIZE, bgcolor=cur_canvas[len(cur_canvas) - 1][0]) #NOTE the last index should be safe here, but for users with negative level_max's, self.cache_levels was an empty list and thus this was erroring

  def plot_image(self, points):
    space_level = self.__create_empty_space()
    rad = int(self.zoom * DOT_MULT)
    start = datetime.now()
    for i, point in enumerate(points):
      self.__merge_point_in_space(space_level, point, rad)
      # logging.debug('   point %d of %d, start at %s, done at %s' % (i, len(points), start, datetime.now()))
    return self.convert_image(space_level)

  def __merge_point_in_space(self, space_level, point, rad):
    weight = len(point.checkin_guid_list)
    rad_exp = math.pow(weight, 0.25)
    alpha_weight = MAX_ALPHA * weight
    twice_rad = rad * 2
    y_off = int(math.ceil((-1 * self.northwest_ll[0] + point.location.lat) / self.latlng_diff[0] * 256. - rad))
    x_off = int(math.ceil((-1 * self.northwest_ll[1] + point.location.lon) / self.latlng_diff[1] * 256. - rad))
    for y in range(y_off, y_off + twice_rad):
      if y < 0 or y >= SIZE:
        continue
      y_adj = math.pow((y - rad - y_off), 2)
      for x in range(x_off, x_off + twice_rad):
        if x < 0 or x >= SIZE:
          continue
        x_adj = math.pow((x - rad - x_off), 2)
        pt_rad = math.sqrt(y_adj + x_adj)
        if pt_rad > rad:
          continue
        space_level[y][x] += (math.pow((rad - pt_rad) / rad, rad_exp) * alpha_weight)
        
  def scale_value(self, value):
    #ret_float = math.log(max((value + 50) / 50, 1), 1.01) + 30
    #ret_float = math.log(max((value + 30) / 40, 1), 1.01) + 30
    #ret_float = math.log(max((value + 40) / 20, 1), 1.01)
    ret_float = math.log(max(value, 1), 1.1) * 4
    return int(ret_float)

  def convert_image(self, space_level):
    tile = PNGCanvas(SIZE, SIZE, bgcolor=[0xff,0xff,0xff,0])
    temp_color_scheme = []
    for i in range(self.level_max):
      temp_color_scheme.append(self.color_scheme.canvas[self.cache_levels[i]][0])
    for y in xrange(SIZE):
      for x in xrange(SIZE):
        if len(temp_color_scheme) > 0:
          tile.canvas[y][x] = [int(e) for e in temp_color_scheme[max(0, min(len(temp_color_scheme) - 1, self.scale_value(space_level[y][x])))]]
        else:
          tile.canvas[y][x] = [0,0,0,0]
    return tile

  def __create_empty_space(self):
    space = []
    for i in range(SIZE):
      space.append( [0.] * SIZE )
    return space

  def image_out(self):
    if self.tile_img:
      self.tile_dump = self.tile_img.dump()

    if self.tile_dump:
      return self.tile_dump
    else:
      raise Exception("Failure in generation of image.")

class CustomTile(BasicTile):
  def __init__(self, user, zoom, lat_north, lng_west, offset_x_px, offset_y_px):
    self.zoom = zoom
    self.decay = 0.5
    #dot_radius = int(math.ceil(len(dot[self.zoom]) / 2))
    dot_radius = int(math.ceil((self.zoom + 1) * DOT_MULT)) #TODO double check that this is + 1 - because range started from 1 in old dot array?!

    # convert to pixel first so we can factor in the dot radius and get the tile bounds
    northwest_px = gmerc.ll2px(lat_north, lng_west, zoom)

    self.northwest_ll_buffered = gmerc.px2ll(northwest_px[0] + offset_x_px       - dot_radius, northwest_px[1] + offset_y_px       - dot_radius, zoom)
    self.northwest_ll          = gmerc.px2ll(northwest_px[0] + offset_x_px                   , northwest_px[1] + offset_y_px                   , zoom)

    self.southeast_ll_buffered = gmerc.px2ll(northwest_px[0] + offset_x_px + 256 + dot_radius, northwest_px[1] + offset_y_px + 256 + dot_radius, zoom)
    self.southeast_ll          = gmerc.px2ll(northwest_px[0] + offset_x_px + 256             , northwest_px[1] + offset_y_px + 256             , zoom) # THIS IS IMPORTANT TO PROPERLY CALC latlng_diff

    self.latlng_diff_buffered = [ self.southeast_ll_buffered[0] - self.northwest_ll_buffered[0], self.southeast_ll_buffered[1] - self.northwest_ll_buffered[1]]
    self.latlng_diff          = [ self.southeast_ll[0]          - self.northwest_ll[0]         , self.southeast_ll[1]          - self.northwest_ll[1]]

    BasicTile.__init__(self, user, self.northwest_ll_buffered[0], self.northwest_ll_buffered[1], self.latlng_diff_buffered[0], self.latlng_diff_buffered[1])


class GoogleTile(BasicTile):
  def __init__(self, user, zoom, x_tile, y_tile):
    self.zoom = zoom
    self.decay = 0.5
    #dot_radius = int(math.ceil(len(dot[self.zoom]) / 2))
    dot_radius = int(math.ceil((self.zoom + 1) * DOT_MULT))

    self.northwest_ll_buffered = gmerc.px2ll((x_tile    ) * 256 - dot_radius, (y_tile    ) * 256 - dot_radius, zoom)
    self.northwest_ll          = gmerc.px2ll((x_tile    ) * 256             , (y_tile    ) * 256             , zoom)

    self.southeast_ll_buffered = gmerc.px2ll((x_tile + 1) * 256 + dot_radius, (y_tile + 1) * 256 + dot_radius, zoom) #TODO fix this in case we're at the edge of the map!
    self.southeast_ll          = gmerc.px2ll((x_tile + 1) * 256             , (y_tile + 1) * 256             , zoom)

    # calculate the real values for these without the offsets, otherwise it messes up the __merge_point_in_space calculations
    self.latlng_diff_buffered = [ self.southeast_ll_buffered[0] - self.northwest_ll_buffered[0], self.southeast_ll_buffered[1] - self.northwest_ll_buffered[1]]
    self.latlng_diff          = [ self.southeast_ll[0]          - self.northwest_ll[0]         , self.southeast_ll[1]          - self.northwest_ll[1]]

    BasicTile.__init__(self, user, self.northwest_ll_buffered[0], self.northwest_ll_buffered[1], self.latlng_diff_buffered[0], self.latlng_diff_buffered[1])
########NEW FILE########
__FILENAME__ = handlers
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api.labs import taskqueue
from google.appengine.api.urlfetch import DownloadError
from google.appengine.api.datastore_errors import BadRequestError
from google.appengine.runtime import DeadlineExceededError
from os import environ
import json
import urllib
import logging
import time
import foursquarev2 as foursquare
import constants
import time
from datetime import datetime
from scripts import manage_foursquare_data
from gheatae import color_scheme, tile, provider
from models import UserInfo, UserVenue, MapImage

class IndexHandler(webapp.RequestHandler):
  def get(self):
    welcome_data = {
      'user': '',
      'userinfo': '',
      'url': users.create_login_url(self.request.uri),
      'real_name': '',
      'photo_url': constants.default_photo,
      'is_ready': False
    }
    sidebar_data = {
      'color_scheme_dict': color_scheme.color_schemes,
      'color_scheme': constants.default_color,
    }
    map_data = {
      'citylat': constants.default_lat,
      'citylng': constants.default_lng,
      'zoom': constants.default_zoom,
      'width': constants.default_dimension,
      'height': constants.default_dimension,
      'domain': environ['HTTP_HOST'],
      'static_url': 'http://maps.google.com/maps/api/staticmap?center=40.738152838822934%2C-73.9822769165039&format=png&zoom=13&key=ABQIAAAAwA6oEsCLgzz6I150wm3ELBSujOi3smKLcjzph36ZE8UXngM_5BTs-xHblsuwK8V9g8bZ_PTfOWR1Fg&sensor=false&size=640x640',
      'mapimage_url': 'map/%s.png' % 'ag93aGVyZS1kby15b3UtZ29yEQsSCE1hcEltYWdlGNL0_wIM',
    }
    user = users.get_current_user()
    if user:
      welcome_data['user'] = user
      welcome_data['url'] = users.create_logout_url(self.request.uri)
      userinfo = UserInfo.all().filter('user =', user).get()
      if userinfo:
        welcome_data['userinfo'] = userinfo
        welcome_data['real_name'] = userinfo.real_name
        welcome_data['photo_url'] = userinfo.photo_url
        welcome_data['is_ready'] = userinfo.is_ready
        sidebar_data['color_scheme'] = userinfo.color_scheme
        map_data['citylat'] = userinfo.citylat
        map_data['citylng'] = userinfo.citylng
    os_path = os.path.dirname(__file__)
    self.response.out.write(template.render(os.path.join(os_path, 'templates/all_header.html'), {'key': constants.google_maps_apikey}))
    self.response.out.write(template.render(os.path.join(os_path, 'templates/private_welcome.html'), welcome_data))
    if user and userinfo:
      if userinfo.has_been_cleared:
        self.response.out.write(template.render(os.path.join(os_path, 'templates/information.html'), {'user': user, 'has_been_cleared': userinfo.has_been_cleared}))
      elif userinfo.is_authorized:
        self.response.out.write(template.render(os.path.join(os_path, 'templates/private_sidebar.html'), sidebar_data))
      else:
        self.response.out.write(template.render(os.path.join(os_path, 'templates/private_unauthorized.html'), None))
    else:
      self.response.out.write(template.render(os.path.join(os_path, 'templates/information.html'), {'user': user, 'has_been_cleared': False}))
    self.response.out.write(template.render(os.path.join(os_path, 'templates/private_map.html'), map_data))
    self.response.out.write(template.render(os.path.join(os_path, 'templates/all_footer.html'), None))

class InformationWriter(webapp.RequestHandler): #NOTE this defaults to the has_been_cleared case for now, since that's the only one that's used
  def get(self):
    user = users.get_current_user()
    os_path = os.path.dirname(__file__)
    self.response.out.write(template.render(os.path.join(os_path, 'templates/information.html'), {'user': user, 'has_been_cleared': True}))

class AuthHandler(webapp.RequestHandler):
  def _get_new_fs_and_credentials(self):
    consumer_key, oauth_secret, url = constants.get_oauth_strings()
    fs = foursquare.FoursquareAuthHelper(key=consumer_key, secret=oauth_secret, redirect_uri=url)
    return fs, None
    
  def get(self):
    user = users.get_current_user()
    if user:
      code = self.request.get("code")
      if code:
        old_userinfos = UserInfo.all().filter('user =', user).fetch(500)
        db.delete(old_userinfos)
        fs, credentials = self._get_new_fs_and_credentials()
        try:
          user_token = fs.get_access_token(code)
          userinfo = UserInfo(user = user, token = user_token, secret = None, is_ready=False, is_authorized=True, level_max=int(3 * constants.level_const))
        except DownloadError, err:
          if str(err).find('ApplicationError: 5') >= 0:
            pass # if something bad happens on OAuth, then it currently just redirects to the signup page
                 #TODO find a better way to handle this case, but it's not clear there is a simple way to do it without messing up a bunch of code
          else:
            raise err
        try:
          manage_foursquare_data.update_user_info(userinfo)
          manage_foursquare_data.fetch_and_store_checkins_next(userinfo, limit=50)
        except foursquare.FoursquareRemoteException, err:
          if str(err).find('403 Forbidden') >= 0:
            pass # if a user tries to sign up while my app is blocked, then it currently just redirects to the signup page
                 #TODO find a better way to handle this case, but it's not clear there is a simple way to do it without messing up a bunch of code
          else:
            raise err
        except DownloadError:
          pass #TODO make this better, but I'd rather throw the user back to the main page to try again than show the user an error.
        self.redirect("/")
      else:
        fs, credentials = self._get_new_fs_and_credentials()
        self.redirect(fs.get_authentication_url())
    else:
      self.redirect(users.create_login_url(self.request.uri))

class StaticMapHandler(webapp.RequestHandler):
  def get(self):
    path = environ['PATH_INFO']
    if path.endswith('.png'):
      raw = path[:-4] # strip extension
      try:
        assert raw.count('/') == 2, "%d /'s" % raw.count('/')
        foo, bar, map_key = raw.split('/')
      except AssertionError, err:
        logging.error(err.args[0])
        return
    else:
      logging.error("Invalid path: " + path)
      return
    mapimage = convert_map_key(map_key)
    if mapimage:
      self.response.headers['Content-Type'] = 'image/png'
      self.response.out.write(mapimage.img)
    else:
      self.redirect("/")

class TileHandler(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      path = environ['PATH_INFO']
      if path.endswith('.png'):
        raw = path[:-4] # strip extension
        try:
          assert raw.count('/') == 4, "%d /'s" % raw.count('/')
          foo, bar, layer, zoom, yx = raw.split('/') #tile is ignored, is just here to prevent caching
          assert yx.count(',') == 1, "%d /'s" % yx.count(',')
          y, x = yx.split(',')
          assert zoom.isdigit() and x.isdigit() and y.isdigit(), "not digits"
          zoom = int(zoom)
          x = int(x)
          y = int(y)
          assert constants.min_zoom <= zoom <= constants.max_zoom, "bad zoom: %d" % zoom
        except AssertionError, err:
          logging.error(err.args[0])
          self.respondError(err)
          return
      else:
        self.respondError("Invalid path")
        return
      start = datetime.now()
      try:
        new_tile = tile.GoogleTile(user, zoom, x, y)
        img_data = new_tile.image_out()
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(img_data)
      except DeadlineExceededError, err:
        logging.warning('%s error - started at %s, failed at %s' % (str(err), start, datetime.now()))
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write('')

class PublicPageHandler(webapp.RequestHandler):
  def get(self):
    path = environ['PATH_INFO']
    if path.endswith('.html'):
      raw = path[:-5] # strip extension
      try:
        assert raw.count('/') == 2, "%d /'s" % raw.count('/')
        foo, bar, map_key = raw.split('/')
      except AssertionError, err:
        logging.error(err.args[0])
        return
    else:
      logging.error("Invalid path: " + path)
      return
    mapimage = convert_map_key(map_key)
    if mapimage:
      welcome_data = {
        'real_name': '',
        'photo_url': constants.default_photo,
      }
      sidebar_data = {
        'domain': environ['HTTP_HOST'],
        'public_url': 'public/%s.html' % mapimage.key(),
      }
      map_data = {
        'domain': environ['HTTP_HOST'],
        'static_url': mapimage.static_url,
        'mapimage_url': 'map/%s.png' % mapimage.key(),
      }
      userinfo = UserInfo.all().filter('user =', mapimage.user).get()
      if userinfo:
        welcome_data['real_name'] = userinfo.real_name
        welcome_data['photo_url'] = userinfo.photo_url
        #welcome_data['checkin_count'] = userinfo.checkin_count
      os_path = os.path.dirname(__file__)
      self.response.out.write(template.render(os.path.join(os_path, 'templates/all_header.html'), None))
      self.response.out.write(template.render(os.path.join(os_path, 'templates/public_welcome.html'), welcome_data))
      self.response.out.write(template.render(os.path.join(os_path, 'templates/public_sidebar.html'), sidebar_data))
      self.response.out.write(template.render(os.path.join(os_path, 'templates/public_map.html'), map_data))
      self.response.out.write(template.render(os.path.join(os_path, 'templates/all_footer.html'), None))
    else:
      self.redirect("/")

class StaticMapHtmlWriter(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      mapimage = MapImage.all().filter('user =', user).get()
      if mapimage:
        template_data = {
          'domain': environ['HTTP_HOST'],
          'static_url': mapimage.static_url,
          'mapimage_url': 'map/%s.png' % mapimage.key(),
          'public_url': 'public/%s.html' % mapimage.key(),
          'timestamp': str(time.time())
        }
        os_path = os.path.dirname(__file__)
        self.response.out.write(template.render(os.path.join(os_path, 'templates/static_map.html'), template_data))
      else:
        self.response.out.write("")

class UserReadyEndpoint(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      userinfo = UserInfo.all().filter('user =', user).get()
      if userinfo:
        self.response.out.write(str(userinfo.has_been_cleared) + ',' + str(userinfo.is_ready) + ',' + str(userinfo.checkin_count))
        return
    self.response.out.write('error')

class MapDoneEndpoint(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      mapimage = MapImage.all().filter('user =', user).get()
      if mapimage:
        self.response.out.write(str(mapimage.tiles_remaining == 0))
        return
    self.response.out.write('error')

def convert_map_key(map_key):
  try:
    return db.get(map_key)
  except BadRequestError, err:
    if err.message == 'app s~where-do-you-go-hrd cannot access app where-do-you-go\'s data':
      old_key = db.Key(map_key)
      new_key = db.Key.from_path(old_key.kind(), old_key.id())
      return db.get(new_key)
    else:
      raise BadRequestError, err

def main():
  application = webapp.WSGIApplication([('/', IndexHandler),
                                        ('/go_to_foursquare', AuthHandler),
                                        ('/authenticated', AuthHandler),
                                        ('/tile/.*', TileHandler),
                                        ('/map/.*', StaticMapHandler),
                                        ('/public/.*', PublicPageHandler),
                                        ('/information', InformationWriter),
                                        ('/static_map_html', StaticMapHtmlWriter),
                                        ('/user_is_ready/.*', UserReadyEndpoint),
                                        ('/map_is_done/', MapDoneEndpoint)],
                                      debug=True)
  constants.provider = provider.DBProvider()
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db
from geo.geomodel import GeoModel
import constants
from datetime import datetime

class UserInfo(db.Model):  
  user = db.UserProperty()
  created = db.DateTimeProperty(auto_now_add=True) # unused to save index space, but keep anyway
  last_updated = db.DateTimeProperty(auto_now_add=True)
  is_ready = db.BooleanProperty() # if this has a default value of Fale, setting it seems to sometimes not work...
  has_been_cleared = db.BooleanProperty(default=False)
  color_scheme = db.StringProperty(default='fire')
  level_max = db.IntegerProperty(default=int(140.)) #TODO see note in constants.py, was =int(constants.level_const))
  checkin_count = db.IntegerProperty(default=0)
  venue_count = db.IntegerProperty(default=0)
  gender = db.StringProperty()
  photo_url = db.StringProperty()
  real_name = db.StringProperty()
  citylat = db.FloatProperty() # no longer really cities! just where the user was scene at the time of signup
  citylng = db.FloatProperty()
  is_authorized = db.BooleanProperty(default=False)
  token = db.StringProperty()
  secret = db.StringProperty()

  def __str__(self):
    return 'UserInfo:  | user =' + str(self.user) + ' | key =' + str(self.key()) + ' | is_ready =' + str(self.is_ready) + ' | color_scheme = ' + str(self.color_scheme) + ' | level_max =' + str(self.level_max) + ' | checkin_count =' + str(self.checkin_count) + ' | venue_count =' + str(self.venue_count) + ' | photo_url =' + str(self.photo_url) + ' | real_name =' + str(self.real_name) + ' | citylat =' + str(self.citylat) + ' | citylng =' + str(self.citylng) + ' | created =' + str(self.created)

class UserVenue(GeoModel):
  user = db.UserProperty()
  last_checkin_at = db.DateTimeProperty()
  checkin_guid_list = db.ListProperty(str, default=[])
  venue_guid = db.StringProperty()
  
class MapImage(db.Model):
  last_updated = db.DateTimeProperty(auto_now_add=True)
  user = db.UserProperty()
  tiles_remaining = db.IntegerProperty(default=0)
  centerlat = db.FloatProperty()
  centerlng = db.FloatProperty()
  northlat = db.FloatProperty()
  westlng = db.FloatProperty()
  zoom = db.IntegerProperty()
  width = db.IntegerProperty()
  height = db.IntegerProperty()
  img = db.BlobProperty()
  static_url = db.StringProperty()
  update_count = db.IntegerProperty(default=0)


########NEW FILE########
__FILENAME__ = oauth_secrets_template
import logging

# this function allows you to simultaneously run the application on multiple domains
# (such as the default application-name.appspot.com domain as well as your own www.somedomain.com)

def get_oauth_consumer_secret_for_domain(domain):
  if domain == 'FIRST DOMAIN':
    return 'CORRESPONDING CONSUMER SECRET'
  elif domain == 'SECOND DOMAIN':
    return 'CORRESPONDING CONSUMER SECRET'
  else:
    logging.error('No Foursquare OAuth consumer secret found for domain ' + domain)
    return ''
########NEW FILE########
__FILENAME__ = delete_data
import os
from os import environ
import constants
from google.appengine.ext import db
from google.appengine.api import users
from models import UserInfo, UserVenue, MapImage
from gheatae import provider

if __name__ == '__main__':
  raw = environ['PATH_INFO']
  assert raw.count('/') == 2, "%d /'s" % raw.count('/')
  foo, bar, rest, = raw.split('/')

  if not constants.provider:
    constants.provider = provider.DBProvider()

  # if rest == 'all': # This is dangerous, so I'm commenting it out :)
  #   while(MapImage.all().count() > 0):
  #     mapimages = MapImage.all().fetch(500)
  #     db.delete(mapimages)
  #   while(UserVenue.all().count() > 0):
  #     uservenues = UserVenue.all().fetch(500)
  #     db.delete(uservenues)
  #   while(AuthToken.all().count() > 0):
  #     authtokens = AuthToken.all().fetch(500)
  #     db.delete(authtokens)
  #   while(UserInfo.all().count() > 0):
  #     userinfos = UserInfo.all().fetch(500)
  #     db.delete(userinfos)

  elif rest == 'user':
    user = users.get_current_user()
    if user:
      while(MapImage.all().filter('user =', user).count() > 0):
        mapimages = MapImage.all().filter('user =', user).fetch(500)
        db.delete(mapimages)
      while(UserVenue.all().filter('user = ', user).count() > 0):
        uservenues = UserVenue.all().filter('user = ', user).fetch(500)
        db.delete(uservenues)
      while(UserInfo.all().filter('user =', user).count() > 0):
        userinfos = UserInfo.all().filter('user =', user).fetch(500)
        db.delete(userinfos)

  elif rest == 'mapimage':
    user = users.get_current_user()
    if user:
      while(MapImage.all().filter('user =', user).count() > 0):
        mapimages = MapImage.all().filter('user =', user).fetch(500)
        db.delete(mapimages)

########NEW FILE########
__FILENAME__ = manage_foursquare_data
from os import environ
import constants
import foursquarev2
import logging
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.api.urlfetch import DownloadError
from google.appengine.api.datastore_errors import BadRequestError
from google.appengine.runtime import DeadlineExceededError
from datetime import datetime, timedelta
from time import mktime
from models import UserInfo, UserVenue

def get_new_fs_for_userinfo(userinfo):
  return foursquarev2.FoursquareClient(userinfo.token)

def fetch_and_store_checkins(userinfo, limit):
  num_added = 0
  userinfo.is_authorized = True
  logging.info('in fetch_and_store_checkins for user %s' % userinfo.user)
  try:
    fs = get_new_fs_for_userinfo(userinfo)
    total_count = int(fs.users()['user']['checkins']['count'])
    logging.info('total checkin count for user %s: %d' % (userinfo.user, total_count))
    if userinfo.checkin_count >= total_count:
      return 0, 0
    to_skip = total_count - limit
    if to_skip >= userinfo.checkin_count:
      to_skip -= userinfo.checkin_count
    else:
      to_skip = 0
      limit = total_count - userinfo.checkin_count
    history = fs.users_checkins(limit=limit, offset=to_skip)
    logging.info('number skipped for user %s: %d' % (userinfo.user, to_skip))
  except foursquarev2.FoursquareException, err:  
    if str(err).find('SIGNATURE_INVALID') >= 0 or str(err).find('TOKEN_EXPIRED') >= 0:
      userinfo.is_authorized = False
      logging.warning("User %s is no longer authorized with err: %s" % (userinfo.user, err))
      userinfo.put()
    else:
      logging.warning("History not fetched for %s with %s" % (userinfo.user, err))
    return 0, 0
  except DownloadError, err:
    logging.warning("History not fetched for %s with %s" % (userinfo.user, err))
    return 0, 0
  try:
    if not 'checkins' in history:
      logging.error("no value for 'checkins' in history: " + str(history))
      userinfo.put()
      return -1, 0
    elif history['checkins']['items'] == None:
      userinfo.put()
      return 0, 0
    history['checkins']['items'].reverse()
    logging.debug('will process %d items' % (len(history['checkins']['items'])))
    for checkin in history['checkins']['items']:
      if 'venue' in checkin:
        j_venue = checkin['venue']
        if 'id' in j_venue:
          uservenue = UserVenue.all().filter('user = ', userinfo.user).filter('venue_guid = ', str(j_venue['id'])).get()
          if not uservenue and 'location' in j_venue and 'lat' in j_venue['location'] and 'lng' in j_venue['location']:
            userinfo.venue_count = userinfo.venue_count + 1
            uservenue = UserVenue(parent=userinfo, location = db.GeoPt(j_venue['location']['lat'], j_venue['location']['lng']))
            uservenue.venue_guid = str(j_venue['id'])
            uservenue.update_location()
            uservenue.user = userinfo.user
            uservenue.checkin_guid_list = []
          if uservenue: # if there's no uservenue by this point, then the venue was missing a location
            uservenue.checkin_guid_list.append(str(checkin['id']))
            userinfo.checkin_count += 1
            def put_updated_uservenue_and_userinfo(uservenue_param, userinfo_param, num_added):
              uservenue_param.put()
              userinfo_param.put()
              return num_added + 1
            try:
              num_added = db.run_in_transaction(put_updated_uservenue_and_userinfo, uservenue, userinfo, num_added)
            except BadRequestError, err:
              logging.warning("Database transaction error due to entity restrictions: %s" % err)
          else:
            logging.error("Venue missing location with JSON: %s" % str(j_venue))
  except KeyError:
    logging.error("There was a KeyError when processing the response: " + str(history))
    raise
  return num_added, int(history['checkins']['count'])	

def fetch_and_store_checkins_next(userinfo, limit=100):
  num_added, num_received = fetch_and_store_checkins(userinfo, limit)
  logging.info("num_added = %d, num_received = %d" % (num_added, num_received))
  if num_added == 0:
    def put_ready_userinfo(userinfo_param):
      userinfo_param.is_ready = True
      userinfo_param.put()
    db.run_in_transaction(put_ready_userinfo, userinfo)
  else:
    taskqueue.add(queue_name='checkins', url='/manage_foursquare_data/next_for_user/%s' % userinfo.key())

def update_user_info(userinfo):
  fs = get_new_fs_for_userinfo(userinfo)
  try:
    user_data = fs.users()
  except foursquarev2.FoursquareException, err:
    if str(err).find('{"unauthorized":"TOKEN_EXPIRED"}') >= 0 or str(err).find('OAuth token invalid or revoked') >= 0:
      userinfo.is_authorized = False
      userinfo.put()
      logging.warning("User %s has unauthorized with %s" % (userinfo.user, err))
      return
    else:
      raise err
  except DownloadError:    
    logging.warning("DownloadError for user %s, retrying once" % userinfo.user)
    try:
      user_data = fs.users()
    except DownloadError, err:
      logging.warning("DownloadError for user %s on first retry, returning" % userinfo.user)
      raise err
      #TODO handle this case better, it's currently a bit of a hack to just get it to return to signin page
  if 'user' in user_data:
    userinfo.real_name = user_data['user']['firstName']
    if 'gender' in user_data['user']:
      userinfo.gender = user_data['user']['gender']
    if 'photo' in user_data['user'] and not user_data['user']['photo'] == '' :
      userinfo.photo_url = user_data['user']['photo']['prefix'] + '100x100' + user_data['user']['photo']['suffix']
    elif 'gender' in user_data['user'] and user_data['user']['gender'] is 'male':
      userinfo.photo_url = 'static/blank_boy.png'
    elif 'gender' in user_data['user'] and user_data['user']['gender'] is 'female':
      userinfo.photo_url = 'static/blank_girl.png'
    else:
      userinfo.photo_url = constants.default_photo
    if 'checkin' in user_data['user'] and 'venue' in user_data['user']['checkin'] and 'geolat' in user_data['user']['checkin']['venue'] and 'geolong' in user_data['user']['checkin']['venue']:
      userinfo.citylat = user_data['user']['checkin']['venue']['geolat']
      userinfo.citylng = user_data['user']['checkin']['venue']['geolong']
    else:
      userinfo.citylat = constants.default_lat
      userinfo.citylng = constants.default_lng
    userinfo.put()
  else:
    logging.error('no "user" key in json: %s' % user_data)

def clear_old_uservenues():
  num_cleared = 0
  cutoff = datetime.now() - timedelta(days=7)   
  userinfos = UserInfo.all().filter('has_been_cleared = ', False).filter('last_updated <', cutoff).fetch(200)
  try:
    for userinfo in userinfos:
      while True:
        uservenues = UserVenue.all(keys_only=True).filter('user =', userinfo.user).fetch(1000)
        if not uservenues: break
        db.delete(uservenues)
        num_cleared = num_cleared + len(uservenues)
      userinfo.has_been_cleared = True
      userinfo.checkin_count = 0
      userinfo.venue_count = 0
      userinfo.last_updated = datetime.now()
      userinfo.put()
    logging.info("finished after deleting at least %d UserVenues for %d UserInfos" % (num_cleared, len(userinfos)))
  except DeadlineExceededError:
    logging.info("exceeded deadline after deleting at least %d UserVenues for %d UserInfos" % (num_cleared, len(userinfos)))
    
if __name__ == '__main__':
  raw = environ['PATH_INFO']
  assert raw.count('/') == 2 or raw.count('/') == 3, "%d /'s" % raw.count('/')

  if raw.count('/') == 2:
    foo, bar, rest, = raw.split('/')
  elif raw.count('/') == 3:
    foo, bar, rest, userinfo_key = raw.split('/')

  if rest == 'clear_old_uservenues':
    clear_old_uservenues()
  elif rest == 'all_for_user':
    user = users.get_current_user()
    if user:
      userinfo = UserInfo.all().filter('user =', user).get()
      if userinfo:
        fetch_and_store_checkins_next(userinfo)
      else:
        logging.warning('No userinfo found for re-fetching user %s' % user)      
    else:
      logging.warning('No user found for re-fetch')
  elif rest == 'next_for_user':
    userinfo = db.get(userinfo_key)
    if userinfo:
      fetch_and_store_checkins_next(userinfo)
    else:
      logging.warning('No userinfo found for key %s' % userinfo_key)
########NEW FILE########
__FILENAME__ = update_user_color
from google.appengine.api import users
from os import environ
from models import UserInfo

user = users.get_current_user()
if user:
  path = environ['PATH_INFO']
  try:
    assert path.count('/') == 2, "%d /'s" % path.count('/')
    foo, bar, color_scheme = path.split('/')
    userinfo = UserInfo.all().filter('user =', user).get()
    userinfo.color_scheme = color_scheme
    userinfo.put()
  except AssertionError, err:
    logging.error(err.args[0])
    self.respondError(err)

########NEW FILE########
__FILENAME__ = update_user_level
from google.appengine.api import users
from gheatae import provider
from os import environ
from models import UserInfo
import constants
import logging

user = users.get_current_user()
if user:
  path = environ['PATH_INFO']
  try:
    assert path.count('/') == 4, "%d /'s" % path.count('/')
    foo, bar, level_offset_str, northwest, southeast = path.split('/')
    level_offset = int(level_offset_str)
    assert northwest.count(',') == 1, "%d ,'s" % northwest.count(',')
    northlat, westlng = northwest.split(',')
    assert southeast.count(',') == 1, "%d ,'s" % southeast.count(',')
    southlat, eastlng = southeast.split(',')

    if not constants.provider:
      constants.provider = provider.DBProvider()
    visible_uservenues = constants.provider.get_user_data(user, float(northlat), float(westlng), float(southlat) - float(northlat), float(eastlng) - float(westlng))

    visible_checkin_count = 0
    for uservenue in visible_uservenues:
      visible_checkin_count += len(uservenue.checkin_guid_list)

    userinfo = UserInfo.all().filter('user =', user).get()
    level_offset = level_offset * 15
    userinfo.level_max = int(float(visible_checkin_count) / float(max(len(visible_uservenues), 1)) * max(constants.level_const + level_offset, 1))
    userinfo.put()
    
  except AssertionError, err:
    logging.error(err.args[0])

########NEW FILE########
__FILENAME__ = update_user_maps
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError
from google.appengine.runtime.apiproxy_errors import CancelledError
import os
from os import environ
import urllib
import constants
import logging
from datetime import datetime
from gheatae import tile
from models import MapImage, UserInfo

def draw_static_tile(user, mapimage_key, zoom, northlat, westlng, offset_x_px, offset_y_px):
  new_tile = tile.CustomTile(user, zoom, northlat, westlng, offset_x_px, offset_y_px) # do the hard work of drawing the tiles in parallel
  def compose_and_save(key, tile, x, y): # but this has to be done in a transaction - otherwise the different threads will overwrite each other's progress on the shared mapimage
    mapimage = db.get(key)
    input_tuples = [(tile.image_out(), x, y, 1.0, images.TOP_LEFT)]
    if mapimage.img:
      input_tuples.append((mapimage.img, 0, 0, 1.0, images.TOP_LEFT))
    img = images.composite(inputs=input_tuples, width=mapimage.width, height=mapimage.height, color=0, output_encoding=images.PNG) # redraw main image every time to show progress
    mapimage.img = db.Blob(img)
    mapimage.tiles_remaining -= 1
    mapimage.last_updated = datetime.now()
    mapimage.put()
  db.run_in_transaction_custom_retries(10, compose_and_save, mapimage_key, new_tile, offset_x_px, offset_y_px)

def generate_static_map(user, widthxheight, zoom, centerpoint, northwest):
  try:
    assert widthxheight.count('x') == 1, "%d x's" % centerpoint.count('x')
    width, height = widthxheight.split('x')
    width, height = int(width), int(height)
    assert zoom.isdigit(), "not digits"
    zoom = int(zoom)
    assert centerpoint.count(',') == 1, "%d ,'s" % centerpoint.count(',')
    centerlat, centerlng = centerpoint.split(',')
    centerlat, centerlng = float(centerlat), float(centerlng)
    assert northwest.count(',') == 1, "%d ,'s" % northwest.count(',')
    northlat, westlng = northwest.split(',')
    northlat, westlng = float(northlat), float(westlng)
  except AssertionError, err:
    logging.error(err.args[0])
    return
  try:
    google_data = {
      'key': constants.google_maps_apikey,
      'zoom': zoom,
      'center': centerpoint,
      'size': widthxheight,
      'sensor':'false',
      'format':'png',
    }
    mapimage = MapImage.all().filter('user =', user).get()
    if not mapimage:
      mapimage              = MapImage()
      mapimage.user         = user
    def reset_map_image(mapimage_param, centerlat_param, centerlng_param, northlat_param, westlng_param, zoom_param, height_param, width_param, google_data_param):
      mapimage_param.tiles_remaining = len(range(0, width_param, 256)) * len(range(0, height_param, 256))
      mapimage_param.centerlat  = centerlat_param
      mapimage_param.centerlng  = centerlng_param
      mapimage_param.northlat   = northlat_param
      mapimage_param.westlng    = westlng_param
      mapimage_param.zoom       = zoom_param
      mapimage_param.height     = height_param
      mapimage_param.width      = width_param
      mapimage_param.static_url = "http://maps.google.com/maps/api/staticmap?" + urllib.urlencode(google_data_param)
      mapimage_param.img = None
      mapimage_param.put()
    db.run_in_transaction(reset_map_image, mapimage, centerlat, centerlng, northlat, westlng, zoom, height, width, google_data)
    for offset_x_px in range(0, width, 256):
      for offset_y_px in range(0, height, 256):
        taskqueue.add(queue_name='tiles', url='/draw_static_tile/%s/%d/%f/%f/%d/%d' % (mapimage.key(), zoom, northlat, westlng, offset_x_px, offset_y_px))
  except DeadlineExceededError, err:    
    logging.error("Ran out of time before creating a map! %s" % err)

if __name__ == '__main__':
  fragments = environ['PATH_INFO'].split('/')
  fragments.pop(0)
  func = fragments.pop(0)
  user = users.get_current_user()
  try:
    if user and func == 'generate_static_map':
      assert len(fragments) == 4, "fragments should have 4 elements %s" % str(fragments)
      widthxheight, zoom, centerpoint, northwest = fragments
      generate_static_map(user, widthxheight, zoom, centerpoint, northwest)
    elif func == 'draw_static_tile':
      mapimage_key = fragments.pop(0)
      mapimage = db.get(mapimage_key)
      if mapimage:
        assert len(fragments) == 5, "fragments should have 5 elements %s" % str(fragments)
        zoom, northlat, westlng, offset_x_px, offset_y_px = fragments
        draw_static_tile(mapimage.user, mapimage_key, int(zoom), float(northlat), float(westlng), int(offset_x_px), int(offset_y_px))
      else: 
        logging.warning('No mapimage found for key %s' % mapimage_key)
  except AssertionError, err:
    logging.error(err.args[0])

########NEW FILE########
