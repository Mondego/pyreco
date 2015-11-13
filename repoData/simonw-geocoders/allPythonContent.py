__FILENAME__ = geonames
from utils import simplejson, geocoder_factory
import urllib

# http://www.geonames.org/export/geonames-search.html

def geocode(q):
    data = simplejson.load(urllib.urlopen(
        'http://ws.geonames.org/searchJSON?' + urllib.urlencode({
            'q': q,
            'maxRows': 1,
            'lang': 'en',
            'style': 'full'
        })
    ))
    if not data['geonames']:
        return None, (None, None)
    
    place = data['geonames'][0]
    name = place['name']
    if place['adminName1'] and place['name'] != place['adminName1']:
        name += ', ' + place['adminName1']
    return name, (place['lat'], place['lng'])

# No API key required, but let's fulfil the contract anyway
geocoder = geocoder_factory(geocode, takes_api_key = False)

########NEW FILE########
__FILENAME__ = google
import urllib
from utils import simplejson, geocoder_factory

# https://developers.google.com/maps/documentation/geocoding/


def geocode(q, api_key=None):
    json = simplejson.load(urllib.urlopen(
        'http://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode({
            'address': q,
            'sensor': 'false',
        })
    ))
    try:
        lon = json['results'][0]['geometry']['location']['lng']
        lat = json['results'][0]['geometry']['location']['lat']
    except (KeyError, IndexError):
        return None, (None, None)
    name = json['results'][0]['formatted_address']
    return name, (lat, lon)

geocoder = geocoder_factory(geocode)

########NEW FILE########
__FILENAME__ = multimap
import urllib
from utils import simplejson, geocoder_factory

# http://www.multimap.com/openapidocs/1.2/web_service/ws_geocoding.htm

def geocode(q, api_key):
    base_url = 'http://developer.multimap.com/API/geocode/1.2/%s' % urllib.quote(api_key)
    json = simplejson.load(urllib.urlopen(base_url + '?' + urllib.urlencode({
            'qs': q,
            'output': 'json'
        })
    ))
    try:
        lon = json['result_set'][0]['point']['lon']
        lat = json['result_set'][0]['point']['lat']
    except (KeyError, IndexError):
        return None, (None, None)
    name = json['result_set'][0]['address']['display_name']
    return name, (lat, lon)

geocoder = geocoder_factory(geocode)

########NEW FILE########
__FILENAME__ = nominatim
import urllib
from utils import simplejson, geocoder_factory

def geocode(q, email):
    """
    Geocode a location query using OpenStreetMap's Nominatim API.
    Pass an email address, as a courteous gesture, to allow the OSM
    admins to contact you if you are using too many resources.

    """

    json = simplejson.load(urllib.urlopen(
        'http://nominatim.openstreetmap.org/search?' + urllib.urlencode({
            'q': q,
            'format': 'json',
            'email': email
        })
    ))
    try:
        lon, lat = json[0]['lon'], json[0]['lat']
    except (KeyError, IndexError):
        return None, (None, None)
    name = json[0]['display_name']
    return name, (lat, lon)

geocoder = geocoder_factory(geocode)

########NEW FILE########
__FILENAME__ = placemaker
from utils import make_nsfind, ET, geocoder_factory
import urllib

# http://developer.yahoo.com/geo/placemaker/guide/api_docs.html

def geocode(q, api_key):
    find = make_nsfind({
        'ns': 'http://wherein.yahooapis.com/v1/schema'
    })
    args = {
        'documentContent': q,
        'documentType': 'text/plain',
        'appid': api_key,
    }
    et = ET.parse(urllib.urlopen(
        'http://wherein.yahooapis.com/v1/document', urllib.urlencode(args))
    )
    place = find(et, 'ns:document/ns:placeDetails/ns:place')
    if place is None:
        return None, (None, None)
    else:
        name = find(place, 'ns:name').text.decode('utf8')
        lat = float(find(place, 'ns:centroid/ns:latitude').text)
        lon = float(find(place, 'ns:centroid/ns:longitude').text)
        return name, (lat, lon)

geocoder = geocoder_factory(geocode)

########NEW FILE########
__FILENAME__ = utils
# Yuck! http://code.activestate.com/recipes/475126/
try:
    import xml.etree.ElementTree as ET # in python >=2.5
except ImportError:
    try:
        import cElementTree as ET # effbot's C module
    except ImportError:
        try:
            import elementtree.ElementTree as ET # effbot's pure Python module
        except ImportError:
            import lxml.etree as ET # ElementTree API using libxml2

try:
    import json as simplejson
except ImportError:
    import simplejson

# Methods for helping with namespace handling in ElementTree
def make_nsfind(nsdict=None):
    nsdict = nsdict or {}
    def find(et, xpath):
        xpath = fix_ns(xpath, nsdict)
        return et.find(xpath)
    return find

def make_nsfindall(nsdict=None):
    nsdict = nsdict or {}
    def find(et, xpath):
        return et.findall(fix_ns(xpath, nsdict))
    return find

def fix_ns(xpath, nsdict=None):
    nsdict = nsdict or {}
    for ns, url in nsdict.items():
        xpath = xpath.replace('%s:' % ns, '{%s}' % url)
    return xpath

def geocoder_factory(fn, takes_api_key=True):
    def make_geocoder(api_key = None, lonlat = False):
        def geocoder(q):
            args = [q]
            if takes_api_key:
                args.append(api_key)
            name, coords = fn(*args)
            if lonlat:
                return name, (coords[1], coords[0])
            else:
                return name, coords
        return geocoder
    return make_geocoder

########NEW FILE########
__FILENAME__ = yahoo
from utils import make_nsfind, ET, geocoder_factory
import urllib

# http://developer.yahoo.com/maps/rest/V1/geocode.html

def geocode(q, api_key):
    find = make_nsfind({'ns': 'urn:yahoo:maps'})
    args = {'location': q, 'appid': api_key}
    url = 'http://local.yahooapis.com/MapsService/V1/geocode?%s' % urllib.urlencode(args)
    et = ET.parse(urllib.urlopen(url))
    
    result = find(et, '//ns:Result')
    if not result:
        return (None, (None, None))
    else:
        namebits = {}
        for field in ('Address', 'City', 'State', 'Zip', 'Country'):
            bit = find(result, 'ns:%s' % field)
            if bit is not None and bit.text:
                namebits[field] = bit.text.decode('utf8')

        if 'Address' in namebits:
            name = '%(Address)s, %(City)s, %(State)s %(Zip)s, %(Country)s' % namebits
        elif 'Zip' in namebits:
            name = '%(City)s, %(State)s %(Zip)s, %(Country)s' % namebits
        elif 'City' in namebits:
            name = '%(City)s, %(State)s, %(Country)s' % namebits
        elif 'State' in namebits:
            name = '%(State)s, %(Country)s' % namebits
        elif 'Country' in namebits:
            name = namebits['Country']
        else:
            return (None, (None, None))

        lat = float(find(result, 'ns:Latitude').text)
        lon = float(find(result, 'ns:Longitude').text)
        
        return (name, (lat, lon))
    
geocoder = geocoder_factory(geocode)

########NEW FILE########
