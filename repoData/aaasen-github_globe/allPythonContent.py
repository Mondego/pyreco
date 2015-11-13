__FILENAME__ = fetch_error

class FetchError(Exception):
    def __init__(self, resp):
        self.resp = resp

    def __str__(self):
        return '%s returned invalid status code %s' % (self.resp.url, self.resp.status_code)

########NEW FILE########
__FILENAME__ = geocode

"""A wrapper for the Google Geocoding API

Notes on usage limits:
    The API's courtesy limit is 2,500 requests/day.
    Be nice; it's free.

"""

import requests
import requests_cache
import json
import fetch_error

requests_cache.install_cache('cache/coords_cache')
maps_api_endpoint = 'http://maps.googleapis.com/maps/api/geocode/json?address=%s&sensor=%s'

"""A generic query method for the Google Geocoding API"""
def _query(address, sensor=False):
    resp = requests.get(maps_api_endpoint % (address, 'true' if sensor else 'false'))

    if resp.status_code == requests.codes.ok:
        return resp.json()
    else:
        raise FetchError(resp)

"""Returns approximate geo coordinates for a given address"""
def address_to_coords(address, sensor=False):
    results = _query(address, sensor)['results']

    if len(results) > 0:
        return results[0]['geometry']['location']

    return None

########NEW FILE########
__FILENAME__ = geo_coord

"""A container for geographic coordinates (latitude and longitude)"""

class GeoCoord:
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng

    def __eq__(self, other):
        return self.lat == other.lat and self.lng == other.lng

    def __hash__(self):
        return hash((self.lat, self.lng))

    def round(self, ndigits=0):
        return GeoCoord(round(self.lat, ndigits), round(self.lng, ndigits))

########NEW FILE########
__FILENAME__ = github_globe

import requests
import requests_cache
import json

import fetch_error
import geocode
from geo_coord import GeoCoord

requests_cache.install_cache('cache/loc_cache')

LOC_DATA_URL = 'http://commondatastorage.googleapis.com/github_globe/location_frequencies'
MAX_VALUES = 1000

def _extract_json(text, max_values=None, delimiter='\n'):
    data = text.split('}%s{' % delimiter)[:max_values]
    data = map(lambda x: '{%s}' % x, data)

    data[0] = data[0].replace('{{', '{')
    data[-1] = data[-1].replace('}}', '}')

    return map(lambda x: json.loads(x), data)

"""Fetches raw data from LOC_DATA_URL

Returns a string of newline-delimited json elements that looks something like this:

{"actor_attributes_location":"Seattle, WA", "num_users":"1024"}
{"actor_attributes_location":"San Francisco", "num_users":"2048"}

"""
def fetch_data(url=LOC_DATA_URL):
    resp = requests.get(url)

    if resp.status_code == requests.codes.ok:
        return resp.text
    else:
        raise FetchError(resp)

"""Extracts json elements from raw response string

return format example:

[{u'num_users': u'22582', u'actor_attributes_location': u'San Francisco, CA'},
{u'num_users': u'16838', u'actor_attributes_location': u'Germany'}]

"""
def format_data(raw):
    locs = _extract_json(raw, max_values=MAX_VALUES)
    return filter(lambda x: x is not None, locs)

"""Adds geographic coordinates with Google's geocoding API

return format example:

[{u'num_users': u'22582', 'coords': <geo_coord.GeoCoord instance>},
{u'num_users': u'16838', 'coords': <geo_coord.GeoCoord instance>}]

"""
def add_coords(data):
    data = filter(lambda x: type(x) is dict, data)
    new = []

    for x in xrange(len(data)):
        print('processing %s out of %s' % (x, len(data)))
        coords = geocode.address_to_coords(data[x]['actor_attributes_location'])

        if coords is not None:
            coords = GeoCoord(coords['lat'], coords['lng'])
            data[x]['coords'] = coords
            del data[x]['actor_attributes_location']
            new.append(data[x])

    return new

"""Combines duplicate locations and reformats data

Github users often user permutations of a location's name.
For example, 'San Francisco' and 'San Fran' and 'San Francisco, CA'
are all the same location and should be combined.

Data is also translated into a new, friendlier format.

return format example:

{
    <geo_coord.GeoCoord instance> : 25582,
    <geo_coord.GeoCoord instance> : 16838
}

"""
def combine_duplicates(data):
    new = {}

    for el in data:
        el['coords'] = el['coords'].round(2)
        if el['coords'] in new:
            new[el['coords']] += int(el['num_users'])
        else:
            new[el['coords']] = int(el['num_users'])

    return new

"""Translates populations onto the range 0-1

return format example:

{
    <geo_coord.GeoCoord instance> : 1.0,
    <geo_coord.GeoCoord instance> : 0.712334545
}

"""
def normalize_populations(data):
    max_pop = max(data.values())
    
    for x in data.keys():
        data[x] = float(data[x]) / max_pop

    return data

"""Translates data to the WebGL format

return format:

[[label, [latitude, longitude, magnitude, latitude, longitude, magnitude]]]

"""
def to_webgl_globe_format(data, label='data'):
    data = map(lambda x: [x.lat, x.lng, data[x]], data.keys())
    data = [item for sublist in data for item in sublist]
    data = map(lambda x: float(x), data)
    return [[label, data]]

data = normalize_populations(
    combine_duplicates(
    add_coords(
    format_data(
    fetch_data()))))

data_globe_format = to_webgl_globe_format(data) 

with open('../visualize/globe/user_locations.json', 'w') as f:
    f.write(json.dumps(data_globe_format))

########NEW FILE########
