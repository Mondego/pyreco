__FILENAME__ = bcycle
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import os
import sys
import time
import json
import argparse
import unidecode
from array import array
from urlparse import urlparse
from collections import namedtuple

import requests
from googlegeocoder import GoogleGeocoder
from slugify import slugify
from pyquery import PyQuery as pq
from pybikes import BCycleSystem, BCycleStation

MAIN = 'http://www.bcycle.com/'
SYS_SELECTOR = 'div.HomePage_TopMenuContent li.special ul li[class!=nav-vote] a'

geocoder = GoogleGeocoder()

CityRecord = namedtuple('CityRecord', 'city, country, lat, lng')

description = 'Extract BCycle instances from the main site'

parser = argparse.ArgumentParser(description = description)

parser.add_argument('-o', metavar = "file", dest = 'outfile', default = None, 
                    help="Save output to the specified file")
parser.add_argument('-g','--geocode', action="store_true",
                    help="Use Google GeoCoder for lat/lng and better names")

parser.add_argument('--proxy', metavar = "host:proxy", dest = 'proxy', 
                    default = None, help="Use host:port as a proxy for site calls")

parser.add_argument('-v', action="store_true", dest = 'verbose', 
                    default = False, help="Verbose output for debugging (no progress)")

args = parser.parse_args()

outfile = args.outfile

session = requests.session()

proxies = {}

if args.proxy is not None:
    proxies['http'] = args.proxy

"""
{
    "tag": "boulder",
    "system": "boulder",
    "meta": {
        "name": "Boulder B-Cycle",
        "city": "Boulder, CO",
        "country": "USA",
        "latitude": 40.0149856,
        "longitude": -105.2705455
    }
}
"""

sysdef = {
    "system": "bcycle",
    "class": "BCycleSystem",
    "instances": []
}

def extract_systems(site):
    sys_selector = 'div.HomePage_TopMenuContent li.special ul li[class!=nav-vote] a'
    fuzz_systems = pq(site)(SYS_SELECTOR)
    systems = []
    for system in fuzz_systems:
        name = pq(system).text()
        url = pq(system).attr('href')
        systems.append({'name': name,'url': url})
    return systems

def google_reverse_geocode(lat, lng):
    state_info = lambda lst: lst[len(lst) - 2].short_name
    country_info = lambda lst: lst[len(lst) - 1].short_name
    target = 'locality'

    if args.verbose:
        print "--- Javascript code for debugging output ---"
        print "    var geocoder = new google.maps.Geocoder()"
        print "    latlng = new google.maps.LatLng(%s,%s)" % (str(lat), str(lng))
        print "    geocoder.geocode({latLng:latlng}, function(res){console.log(res)})"

    info = geocoder.get((lat, lng),language = 'en')
    city_info = [i for i in info if target in i.types]
    if len(city_info) == 0:
        raise Exception
    else:
        city_info = city_info[0]

    city_name = city_info.address_components[0].long_name
    state = state_info(city_info.address_components)
    city = "%s, %s" % (city_name, state)

    country = country_info(city_info.address_components)
    latitude = city_info.geometry.location.lat
    longitude = city_info.geometry.location.lng

    return CityRecord(city, country, latitude, longitude)

def extract_system( data ):
    system = BCycleSystem(tag = 'foo', meta = {'name': data['name']},
                          feed_url = data['url'])
    try:
        system.update()
    except Exception:
        return None
    if len(system.stations) == 0:
        return None

    tag = urlparse(data['url']).netloc.split('.')[0]
    lat = system.stations[0].latitude
    lng = system.stations[0].longitude
    city = ''
    country = ''
    if args.geocode:
        if args.verbose:
            print "---> Geocoding %s" % data['name']
        try:
            city, country, lat, lng = google_reverse_geocode(lat, lng)
        except Exception:
            print "No geocoding results for %s" % data['name']
        time.sleep(1)

    instance = {
        'tag': tag,
        'feed_url': data['url'],
        'meta': {
            'name': data['name'],
            'city': city,
            'country': country,
            'latitude': lat,
            'longitude': lng
        }
    }

    return instance


def print_status(i, total, progress, status):
    status_pattern = "\r{i}/{total}: [{progress}] {status}"
    output = status_pattern.format(
        i = i+1, total = total, progress = progress.tostring(), status = status)
    sys.stdout.flush()
    sys.stdout.write("\r                                                              ")
    sys.stdout.flush()
    sys.stdout.write(unicode(output))
    sys.stdout.flush()


data = requests.get(MAIN, proxies = proxies)
systems = extract_systems(data.text)
print "Found %d systems!" % len(systems)
instances = []

progress = array('c','')
for p in range(len(systems)):
    progress.append(' ')

for i, system in enumerate(systems):
    progress[i] = '#'
    if not args.verbose:
        print_status(i, len(systems), progress, "%s" % system['name'])
    instance = extract_system(system)
    if instance is not None:
        instances.append(instance)
        if args.verbose:
            print instance

print "\n%d/%d systems are valid!" % (len(instances), len(systems))
sysdef['instances'] = sorted(instances, key = lambda inst: inst['tag'])

data = json.dumps(sysdef, sort_keys = False, indent = 4)

if outfile is not None:
    f = open(outfile, 'w')
    f.write(data)
    f.close()
    print "%s file written" % outfile
else:
    print "---- OUTPUT ----"
    print data

########NEW FILE########
__FILENAME__ = cyclocity
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import os
import sys
import time
import json
import argparse

from slugify import slugify
import pybikes

api_key = 'ace81338b73283277ddfe54c217ab965ac93cb50'

description = 'Extract cyclocity instances'

parser = argparse.ArgumentParser(description = description)

parser.add_argument('-o', metavar = "output", dest = "output", 
                    type = argparse.FileType('w'), default = sys.stdout, 
                    help="Output file")

parser.add_argument('-v', action="store_true", dest = 'verbose', 
                    default = False, help="Verbose output for debugging (no progress)")

parser.add_argument('--proxy', metavar = "host:proxy", dest = 'proxy', 
                    default = None, help="Use host:port as a proxy for site calls")

parser.add_argument('--httpsproxy', metavar = "host:proxy", dest = 'httpsproxy', 
                    default = None, help="Use host:port as an HTTPS proxy for site calls")

args = parser.parse_args()

scraper = pybikes.utils.PyBikesScraper()

proxies = {}

sysdef = {
    "system": "cyclocity",
    "class": "Cyclocity",
    "instances": []
}

def clearline(length):
    clearline = "\r" + "".join([" " for i in range(length)])
    sys.stderr.flush()
    sys.stderr.write(clearline)
    sys.stderr.flush()

def print_status(i, total, status):
    progress = "".join(["#" for step in range(i)]) + \
               "".join([" " for step in range(total-i)])
    status_pattern = "\r{0}/{1}: [{2}] {3}"
    output = status_pattern.format(i, total, progress, status)
    sys.stderr.flush()
    sys.stderr.write(unicode(output))
    sys.stderr.flush()
    if (i == total):
        sys.stderr.write('\n')
    return len(output)

def main():
    if args.proxy is not None:
        proxies['http'] = args.proxy
        scraper.enableProxy()

    if args.httpsproxy is not None:
        proxies['https'] = args.httpsproxy
        scraper.enableProxy()

    scraper.setProxies(proxies)

    services = pybikes.Cyclocity.get_contracts(api_key, scraper)
    lastlen = 0
    for i, service in enumerate(services):
        sysdef['instances'].append(
            {
                'tag': slugify(service['commercial_name']),
                'contract': service['name'],
                'meta': {
                    'name': service['commercial_name'],
                    'country': service['country_code']
                }
            }
        )
        clearline(lastlen)
        lastlen = print_status(i+1, len(services), \
                        "Testing %s" % repr(service['name']))

    output = json.dumps(sysdef, sort_keys = False, indent = 4)
    args.output.write(output)
    args.output.write('\n')
    args.output.close()

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = cyclocity_navigator
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import string

import requests

import sys

MAIN = 'https://gw.cyclocity.fr/3311a6cea2e49b10/'

ACTIONS = {
    'cities': 'contracts/full?token={token}',
    'token': 'token/key/b885ab926fdca7dbfbf717084fb36b5f',
    'availability': 'availability/{city}/stations/state/?token={token}',
    'availabitity_by_geo': 'availability/{city}/stations/proximity/{what}?lat={lat}&lng={lng}&maxRes=10000&min=1&token={token}'
}

TOKEN = None

def getUrl(action, **args):
    return '%s%s' % (MAIN, ACTIONS[action].format(**args))

def call(action, **args):
    if 'token' not in args and TOKEN is not None:
        args['token'] = TOKEN
    url = getUrl(action, **args)
    r = requests.get(url)
    return r.json()

def getToken():
    data = call('token')
    return data['token']

def listCities():
    cities = call('cities', token = TOKEN)
    print '--- %d Cities ---' % len(cities)
    for idx, city in enumerate(cities):
        print '[%d] %s - %s' % (idx, city['name'], city['code'])
    return cities

def listActions():
    print '--- Actions ---'
    res = []
    for idx, action in enumerate(MENU_ACTIONS):
        print '%d %s' % (idx, action)
        res.append(action)
    number = input('>> Select an action: ')
    action = res[number]
    return MENU_ACTIONS[action]

def getParams(action):
    iterparams = string.Formatter().parse(ACTIONS[action])
    params = [x[1] for x in iterparams if x[1] is not None and x[1] != 'token' and x[1] != 'city']
    user_input = {}
    for p in params:
        stuff = str(raw_input('>> %s: ' % p))
        user_input[p] = stuff
    return user_input

def quit(** args):
    sys.exit(0)

def get_everything(city):
    n_stations = count_stations(city)
    minLat = city['viewPort']['minLat']
    minLng = city['viewPort']['minLng']
    maxLat = city['viewPort']['maxLat']
    maxLng = city['viewPort']['maxLng']
    square = [0.001, 0.001]
    square[0] = float(raw_input('>> Select latitude box: '))
    square[1] = float(raw_input('>> Select longitude box: '))
    if (minLat > maxLat):
        square[0] = square[0] * -1
    if (minLng > maxLng):
        square[1] = square[1] * -1

    c_square_lat = minLat
    c_square_lng = minLng
    inRange = True
    geosquares = []
    all_stations = {}
    print 'From %s to %s' % ([minLat, minLng], [maxLat, maxLng])
    print 'Using %s' % square
    inc = 0
    print 'Recalculating splines...'
    while(inRange):
        geosquares.append([c_square_lat, c_square_lng])
        c_square_lng = c_square_lng + square[1]
        if (c_square_lng > maxLng + square[1]):
            c_square_lng = minLng
            c_square_lat = c_square_lat + square[0]
        inRange = c_square_lat < maxLat + square[0]
    print "%d Geo Squares calculated" % len(geosquares)
    nothing = raw_input('Is it ok?')
    if nothing == 'no':
        return
    for idx, gsquare in enumerate(geosquares):
        stations = call('availabitity_by_geo', city = city['code'], what = 'bike', lat = gsquare[0], lng = gsquare[1])
        added = 0
        for station in stations:
            if station['station']['nb'] not in all_stations:
                all_stations[station['station']['nb']] = station
                added = added + 1
        if (added > 0):
            sys.stdout.flush()
            sys.stdout.write('\r[%d%%] Got %d stations of %d' % (idx * 100 / len(geosquares), len(all_stations), n_stations))
        sys.stdout.write('.')

    print len(all_stations)

def count_stations(city):
    stations = call('availability', city = city['code'])
    print '%d stations in %s' % (len(stations['ststates']), city['name'])
    print stations
    return len(stations['ststates'])

MENU_ACTIONS = {
    'quit': quit,
    'get_everything': get_everything,
    'count_stations': count_stations,
}


if TOKEN is None:
    TOKEN = getToken()

cities = listCities()
number = input('>> Please, select your city: ')
city = cities[number]
print('%s selected' % city['name'])
while (True):
    action = listActions()
    action(city)



########NEW FILE########
__FILENAME__ = domoblue
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import os
import sys
import time
import json
import argparse
from collections import namedtuple
import re

from pyquery import PyQuery as pq

from googlegeocoder import GoogleGeocoder
from slugify import slugify
from pybikes.utils import PyBikesScraper
from pybikes import Domoblue

MAIN = 'http://clientes.domoblue.es/onroll/'
TOKEN_URL = 'generaMapa.php?cliente={service}&ancho=500&alto=700'
XML_URL = 'generaXml.php?token={token}&cliente={service}'
TOKEN_RE = 'generaXml\.php\?token\=(.*?)\&cliente'

geocoder = GoogleGeocoder()

CityRecord = namedtuple('CityRecord', 'city, country, lat, lng')

description = 'Extract DomoBlue instances from the main site'

parser = argparse.ArgumentParser(description = description)

parser.add_argument('-o', metavar = "file", dest = 'outfile', default = None, 
                    help="Save output to the specified file")
parser.add_argument('-g','--geocode', action="store_true",
                    help="Use Google GeoCoder for lat/lng and better names")

parser.add_argument('--proxy', metavar = "host:proxy", dest = 'proxy', 
                    default = None, help="Use host:port as a proxy for site calls")

parser.add_argument('-v', action="store_true", dest = 'verbose', 
                    default = False, help="Verbose output for debugging (no progress)")

args = parser.parse_args()

outfile = args.outfile

proxies = {}

user_agent = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.168 Safari/535.19'

scraper = PyBikesScraper()
scraper.setUserAgent(user_agent)

sysdef = {
    "system": "domoblue",
    "class": "Domoblue",
    "instances": []
}

if args.proxy is not None:
    proxies['http'] = args.proxy
    scraper.setProxies(proxies)
    scraper.enableProxy()


def get_token(client_id):
    if 'Referer' in scraper.headers:
        del(scraper.headers['Referer'])
    url = MAIN + TOKEN_URL.format(service = client_id)
    data = scraper.request(url)
    token = re.findall(TOKEN_RE, data)
    scraper.headers['Referer'] = url
    return token[0]

def get_xml(client_id):
    token = get_token(client_id)
    url = MAIN + XML_URL.format(token = token, service = client_id)
    return scraper.request(url).encode('raw_unicode_escape').decode('utf-8')

def test_system_health(domo_sys):
    online = False
    for s in domo_sys.stations:
        online = s.extra['status']['online']
        if online:
            break
    return online

def google_reverse_geocode(lat, lng):
    country_info = lambda lst: lst[len(lst) - 1].short_name
    target = 'locality'

    if args.verbose:
        print "--- Javascript code for debugging output ---"
        print "    var geocoder = new google.maps.Geocoder()"
        print "    latlng = new google.maps.LatLng(%s,%s)" % (str(lat), str(lng))
        print "    geocoder.geocode({latLng:latlng}, function(res){console.log(res)})"

    info = geocoder.get((lat, lng),language = 'es')
    city_info = [i for i in info if target in i.types]
    if len(city_info) == 0:
        target = 'political'
        city_info = [i for i in info if target in i.types]
        if len(city_info) == 0:
            raise Exception
    else:
        city_info = city_info[0]

    city = city_info.address_components[0].long_name

    country = country_info(city_info.address_components)
    latitude = city_info.geometry.location.lat
    longitude = city_info.geometry.location.lng

    return CityRecord(city, country, latitude, longitude)

def extract_systems():
    xml_data = get_xml('todos')
    xml_dom = pq(xml_data, parser = 'xml')
    systems = []
    for marker in xml_dom('marker'):
        if marker.get('tipo') == 'pendiente':
            continue
        sys = Domoblue('foo', {}, int(marker.get('codigoCliente')))
        sys.update()
        online = True #test_system_health(sys)
        if args.verbose:  
            print "--- %s --- " % repr(marker.get('nombre'))
            print " Total stations: %d" % len(sys.stations)
            print " Health: %s" % (lambda b: 'Online' if b else 'Offline')(online)
        if not online:
            if args.verbose:
                print " %s is Offline, ignoring!\n" % repr(marker.get('nombre'))
            continue

        name = 'Onroll %s' % marker.get('nombre')
        slug = slugify(name)
        city = marker.get('nombre')
        latitude = marker.get('lat')
        longitude = marker.get('lng')
        country = 'ES'

        if args.geocode:
            time.sleep(1)
            try:
                city, country, latitude, longitude = google_reverse_geocode(latitude, longitude)
                name = 'Onroll %s' % city
            except Exception:
                print " No geocoding results for %s!!" % repr(name)
        system = {
            'tag': slug,
            'system_id': int(marker.get('codigoCliente')),
            'meta': {
                'name': name,
                'latitude': latitude,
                'longitude': longitude,
                'city': city,
                'country': 'ES'
            }
        }
        systems.append(system)
        if args.verbose:
            print " Appended!\n"
    return systems

instances = extract_systems()
sysdef['instances'] = sorted(instances, key = lambda inst: inst['tag'])

data = json.dumps(sysdef, sort_keys = False, indent = 4)

if outfile is not None:
    f = open(outfile, 'w')
    f.write(data)
    f.close()
    print "%s file written" % outfile
else:
    print "---- OUTPUT ----"
    print data

########NEW FILE########
__FILENAME__ = filler
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import os
import sys, traceback
import time
import json
import argparse
from urlparse import urlparse
from collections import namedtuple
import traceback
from googlegeocoder import GoogleGeocoder
from slugify import slugify
import pybikes

geocoder = GoogleGeocoder()

CityRecord = namedtuple('CityRecord', 'city, country, lat, lng')

description = 'Given a PyBikes instance file, fills undeclared values'

parser = argparse.ArgumentParser(description = description)

parser.add_argument('input', metavar = "input", 
                    type = argparse.FileType('r'), default = sys.stdin,
                    help="Input file")

parser.add_argument('-o', metavar = "output", dest = "output", 
                    default = sys.stdout, 
                    help="Output file")

parser.add_argument('-v', action="store_true", dest = 'verbose', 
                    default = False, help="Verbose output for debugging (no progress)")

parser.add_argument('--proxy', metavar = "host:proxy", dest = 'proxy', 
                    default = None, help="Use host:port as a proxy for site calls")

parser.add_argument('--httpsproxy', metavar = "host:proxy", dest = 'httpsproxy', 
                    default = None, help="Use host:port as an HTTPS proxy for site calls")

parser.add_argument('--slugify', action="store_true", dest = 'slugify', 
                    default = False, help="Correct slugs, using the name as input")

parser.add_argument('--geocode', action="store_true", dest = 'geocode', 
                    default = False, help="Correct geodata using Google GeoCoder")

parser.add_argument('--correct_name', action="store_true", dest = "geoname",
                    default = False, help="Correct just the name using geodata")

parser.add_argument('-f', action="store_true", dest = 'overwrite', 
                    default = False, help="Overwrite already set variables")

parser.add_argument('-i', action="store_true", dest = 'interactive', 
                    default = False, help="Interactive prompt to select between results")

parser.add_argument('-c', action="store_true", dest = 'continuous', 
                    default = False, help="Continuous write output file")

parser.add_argument('-s', action="store_true", dest = 'skip', 
                    default = False, help="Skip complete instances")

args = parser.parse_args()

scraper = pybikes.utils.PyBikesScraper()

proxies = {}

prompts = {
    'slug': '\n--------------\n' + \
            '| Old: {old_tag}\n' + \
            '|---------------\n' + \
            '| New: {new_tag}\n' + \
            '----------------\n' + \
            'Overwrite? y/n/set: '
}

language = 'en'

metas = ['city', 'country']

data = {}

def clearline(length):
    clearline = "\r" + "".join([" " for i in range(length)])
    sys.stderr.flush()
    sys.stderr.write(clearline)
    sys.stderr.flush()

def print_status(i, total, status):
    progress = "".join(["#" for step in range(i)]) + \
               "".join([" " for step in range(total-i)])
    status_pattern = "\r{0}/{1}: [{2}] {3}"
    output = status_pattern.format(i, total, progress, status)
    sys.stderr.flush()
    sys.stderr.write(unicode(output))
    sys.stderr.flush()
    if (i == total):
        sys.stderr.write('\n')
    return len(output)

def geocode(instance, systemCls, language, address = None):
    if address is not None:
        query = address
    else:
        if args.verbose:
            sys.stderr.write("--- Geocoding %s ---- \n" % instance['tag'])
        bikesys = systemCls(** instance)

        latitude, longitude = [0.0, 0.0]
        if 'latitude' in instance['meta'] and 'longitude' in instance['meta']:
            latitude  = instance['meta']['latitude']
            longitude = instance['meta']['longitude']
        else:
            if args.verbose:
                sys.stderr.write("Updating system to get an initial lat/lng\n")
            bikesys.update(scraper)
            target = int(len(bikesys.stations) / 2)
            latitude  = bikesys.stations[target].latitude
            longitude = bikesys.stations[target].longitude
        if args.verbose:
            sys.stderr.write(" >>> %s, %s <<< \n" % (str(latitude), str(longitude)))
            sys.stderr.write("--- Javascript code for debugging output ---\n")
            sys.stderr.write("var geocoder = new google.maps.Geocoder()\n")
            sys.stderr.write("latlng = new google.maps.LatLng(%s,%s)\n" % (str(latitude), str(longitude)))
            sys.stderr.write("geocoder.geocode({latLng:latlng}, function(res){console.log(res)})\n")
        query = (latitude, longitude)
    try:        
        info = geocoder.get(query, language = language)
    except Exception as e:
        print e
        address = raw_input('Type an address: ')
        return geocode(instance, systemCls, language, address)
    if args.interactive:
        for index, address in enumerate(info):
            sys.stderr.write("%d: %s\n" % (index, address.formatted_address))
        sys.stderr.write("%d: Change language\n" % len(info))
        sys.stderr.write("%d: Manual address lookup\n" % int(len(info)+1))
        sys.stderr.write('\n')
        try:
            res = int(raw_input('Select option (number): '))
            if res == len(info):
                language = raw_input('New language? ')
                return geocode(instance, systemCls, language)
            elif res == len(info)+1:
                address = raw_input('Type an address: ')
                return geocode(instance, systemCls, language, address)
            elif res < len(info):
                address = info[res]
                metainfo = instance['meta']
                lat = address.geometry.location.lat
                lng = address.geometry.location.lng
                for index, el in enumerate(address.address_components):
                    sys.stderr.write("%d: %s\n" % (index, el.short_name))
                sys.stderr.write('Latitude: %s\n' % str(lat))
                sys.stderr.write('Longitude: %s\n' % str(lng))
                sys.stderr.write('\n')
                for meta in metas:
                    res = raw_input('Select the %s: ' % meta)
                    if ',' in res:
                        res = res.split(',')
                    else:
                        res = [res]
                    metainfo[meta] = ''
                    for i, r in enumerate(res):
                        r = int(r)
                        metainfo[meta] += address.address_components[r].short_name
                        if (i < len(res)-1):
                            metainfo[meta] += ', '
                if args.geoname:
                    lat = latitude
                    lng = longitude
                metainfo['latitude'] = lat
                metainfo['longitude'] = lng
                instance['meta'] = metainfo
                return True
        except Exception as e:
            print e
            return geocode(instance, systemCls, language)

    if args.verbose:
        sys.stderr.write("\n")

def is_complete(instance):
    fields = ['city','country','latitude','longitude','name']
    complete = True
    for field in fields:
        complete = field in instance['meta']
        if not complete:
            return False
    return complete

def write_output(data, way):
    way = open(way, 'w')
    corrected_data = json.dumps(data, sort_keys = False, indent = 4)
    way.write(corrected_data)
    way.write('\n')
    way.close()

def handle_System(cls, instances):
    systemCls = eval('pybikes.%s' % cls)
    lastlen = 0

    if args.interactive and args.geocode:
        language = raw_input('Desired geocoding language? ')

    for i, instance in enumerate(instances):
        if not args.verbose:
            clearline(lastlen)
            lastlen = print_status(i+1, len(instances), \
                        "Testing %s" % repr(instance['meta']['name']))
        if 'name' not in instance['meta'] or instance['meta']['name'] == "":
            raise Exception("name not set in instance %s" % str(instance))
        if args.skip and is_complete(instance):
            if args.verbose:
                sys.stderr.write("%s Looks complete, passing by\n" % 
                    repr(instance['meta']['name'])
                )
            continue
        if args.slugify:
            tag = slugify(instance['meta']['name'])
            r   = None
            if args.interactive:
                r = raw_input(prompts['slug'].format(old_tag = instance['tag'],
                                                     new_tag = tag))
                if r == 'set':
                    tag = raw_input("Set new tag: ")
                elif r == 'n':
                    continue
            if r != 'n' or args.overwrite or 'tag' not in instance or 'tag' == '':
                instance['tag'] = tag

        if args.geocode:
            geocode(instance, systemCls, language)
            time.sleep(1)


def main():
    global data
    if args.proxy is not None:
        proxies['http'] = args.proxy
        scraper.enableProxy()

    if args.httpsproxy is not None:
        proxies['https'] = args.httpsproxy
        scraper.enableProxy()

    scraper.setProxies(proxies)

    if not args.slugify and not args.geocode:
        sys.stderr.write("Nothing to do, stopping\n")
        exit(0)

    data = json.loads(args.input.read())
    args.input.close()
    if isinstance(data['class'], unicode):
        #UniSystem
        instances = data['instances']
        system = data['system']
        sys.stderr.write('Found %d instances for %s\n' % (len(instances), system))
        handle_System(data['class'], instances)
    elif isinstance(data['class'], dict):
        #MuliSystem
        for cls in data['class']:
            instances = data['class'][cls]['instances']
            system = data['system']
            sys.stderr.write('Found %d instances for %s\n' % (len(instances), system))
            handle_System(cls, instances)
    else:
        raise Exception('Malformed data file')


    write_output(data, args.output)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        if args.continuous:
            if args.verbose:
                sys.stderr.write("Writing file bc exception\n")
                traceback.print_exc(file=sys.stderr)
            write_output(data, args.output)
    except KeyboardInterrupt as e:
        print "KEYBOARD INTERRUPT"
        if args.continuous:
            if args.verbose:
                sys.stderr.write("Writing file bc exception\n")
            write_output(data, args.output)


########NEW FILE########
__FILENAME__ = keys.example
cyclocity = 'get your API key at http://developer.jcdecaux.com'

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

from datetime import datetime
import json
import hashlib

__author__ = "eskerda (eskerda@gmail.com)"
__version__ = "2.0"
__copyright__ = "Copyright (c) 2010-2012 eskerda"
__license__ = "AGPL"

__all__ = ['GeneralPurposeEncoder', 'BikeShareStation', 'BikeShareSystem' ]

class GeneralPurposeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

class BikeShareStation(object):
    """A base class to name a bike sharing Station. It can be:
        - Specific (cities):
            - BicingStation, VelibStation, ...
        - General (companies):
            - JCDecauxStation, ClearChannelStation
    """

    def __init__(self, id, timestamp = datetime.utcnow() ):

        self.id = id
        self.name = None
        self.latitude = None
        self.longitude = None
        self.bikes = None
        self.free = None
        self.timestamp = timestamp     # Store timestamp in UTC!
        self.extra = {}
    def __str__(self):
        return "--- {0} ---\n"\
               "bikes: {1}\n"\
               "free: {2}\n"\
               "latlng: {3},{4}\n"\
               "extra: {5}"\
               .format(repr(self.name), self.bikes, self.free, self.latitude, \
                       self.longitude,self.extra)

    def update(self, scraper = None):
        """ Base update method for BikeShareStation, any subclass can
            override this method, and should/could call it from inside
        """
        self.timestamp = datetime.utcnow()

    def to_json(self, **args):
        """ Dump a json string using the BikeShareStationEncoder with a
            set of default options
        """
        if 'cls' not in args:   # Set defaults here
            args['cls'] = GeneralPurposeEncoder

        return json.dumps(self, **args)
    
    def get_hash(self):
        """ Return a unique hash representing this station, usually with
            latitude and longitude, since it's the only globally ready and
            reliable information about an station that defines the 
            difference between one and another
        """
        str_rep = "%d,%d" % (int(self.latitude * 1E6), int(self.longitude * 1E6))
        h = hashlib.md5()
        h.update(str_rep.encode('utf-8'))
        return h.hexdigest()

class BikeShareSystem(object):
    """A base class to name a bike sharing System. It can be:
        - Specific (cities):
            - Bicing, Velib, ...
        - General (companies):
            - JCDecaux, ClearChannel
        At the same time, these classes can extend their base class,
        for example, Velib extends JCDecaux extends BikeShareSystem.

        This class might or not have METADATA assigned, usually intended
        for specific cases. This METADATA is dict / json formatted.
    """

    tag = None

    meta = {
        'name' : None,
        'city' : None,
        'country' : None,
        'latitude' : None,
        'longitude' : None,
        'company' : None
    }

    sync = True

    authed = False

    def __init__(self, tag, meta):
        self.stations = []
        self.tag = tag
        basemeta = dict(BikeShareSystem.meta, **self.meta)
        self.meta = dict(basemeta, **meta)

    def __str__(self):
        return "tag: %s\nmeta: %s" % (self.tag, str(self.meta))
        
    def to_json(self, **args):
        """ Dump a json string using the BikeShareSystemEncoder with a
            set of default options
        """
        if 'cls' not in args:   # Set defaults here
            args['cls'] = GeneralPurposeEncoder

        return json.dumps(self, **args)


########NEW FILE########
__FILENAME__ = bcycle
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import re

from pyquery import PyQuery as pq
from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['BCycleSystem', 'BCycleStation']

LAT_LNG_RGX = "var\ point\ =\ new\ google.maps.LatLng\(([+-]?\\d*\\.\\d+)(?![-+0-9\\.])\,\ ([+-]?\\d*\\.\\d+)(?![-+0-9\\.])\)"
DATA_RGX = "var\ marker\ =\ new\ createMarker\(point\,(.*?)\,\ icon\,\ back"
USERAGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/31.0.1650.63 Chrome/31.0.1650.63 Safari/537.36"

class BCycleError(Exception):
    def __init__(self, msg):
            self.msg = msg

    def __repr__(self):
            return self.msg
    __str__ = __repr__


class BCycleSystem(BikeShareSystem):

    feed_url = "http://{system}.bcycle.com"
    sync = True

    meta = {
        'system': 'B-cycle',
        'company': [ 'Trek Bicycle Corporation'
                     ,'Humana'
                     ,'Crispin Porter + Bogusky' ]
    }

    def __init__(self, tag, meta, system = None, feed_url = None):
        super( BCycleSystem, self).__init__(tag, meta)
        if feed_url is not None:
            self.feed_url = feed_url
        else:
            self.feed_url = BCycleSystem.feed_url.format(system =  system)

    def update(self, scraper = None):

        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.setUserAgent(USERAGENT)

        html_data = scraper.request(self.feed_url)

        geopoints = re.findall(LAT_LNG_RGX, html_data)
        puzzle = re.findall(DATA_RGX, html_data)
        stations = []

        for index, fuzzle in enumerate(puzzle):

            station = BCycleStation(index)
            station.latitude = float(geopoints[index][0])
            station.longitude = float(geopoints[index][1])
            station.from_html(fuzzle)

            stations.append(station)

        self.stations = stations


class BCycleStation(BikeShareStation):

    def from_html(self, fuzzle):
        """ Take a good look at this fuzzle:
            var point = new google.maps.LatLng(41.86727, -87.61527);
            var marker = new createMarker(
                point,                       .--- Fuzzle
                "<div class='location'>      '
                    <strong>Museum Campus</strong><br />
                    1200 S Lakeshore Drive<br />
                    Chicago, IL 60605
                </div>
                <div class='avail'>
                    Bikes available: <strong>0</strong><br />
                    Docks available: <strong>21</strong>
                </div>
                <br/>
                ", icon, back);
            Now, do something about it
        """

        d = pq(fuzzle)('div')
        location = d.find('.location').html().split('<br/>')
        availability = d.find('.avail strong')

        self.name = pq(location[0]).html()
        self.bikes = int(availability.eq(0).text())
        self.free = int(availability.eq(1).text())

        self.extra = {
            'address' : '{0} - {1}'.format(location[1], location[2])
        }
        return self


########NEW FILE########
__FILENAME__ = bicicard
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the LGPL license, see LICENSE.txt
"""bicicard.py

The Bicicard system (Spain, ITCL), only provides information on the status
of the stations, but not their position (which is provided in a pdf / jpg map,
go figure). The only way to get a consistent feed for that is providing the
location of the stations on a different feed (for instance, a KML feed), and
then map these to the shitty-table-status-page, as in:

    - Map: http://goo.gl/maps/C2xLB (community provided map)
    - KML: http://goo.gl/xGScNY (same map, output as kml)
    - Status: http://www.bicileon.com/estado/EstadoActual.asp

The mapping is done on the description field (on the KML), and the name will
be used as the valid and definitive name. So, for instance:
KML
    Name: Foo's bar awesomest place (fancy name)
    Description: Foo Bar baz
    Coordinates: 1.2, 3.4, 0.0

Status:
    <table> {...}
        <td class="titulo">Fo Bar baz - EN LINIA</td> ◁───────────┬ :)
        {...}                                                     │
        <td width="100" class="lat2" nowrap>{...}</td>            │
        <td width="100" class="lat2" nowrap>ESTADO - (2/10)</td> ◁┘
        <td width="65" align="center" class="ico" nowrap bgcolor="#F0F0F0">
            <img src="no.jpg">
        </td>
        <td width="65" align="center" class="ico" nowrap bgcolor="#E7FE68">
            <img src="si.jpg">
        </td>
        <td width="65" align="center" class="ico" nowrap bgcolor="#F0F0F0">
            <img src="no.jpg">
        </td>
        {...}
        <td width="65" align="center" class="ico" nowrap bgcolor="#E7FE68">
            <img src="si.jpg">
        </td>
    </table>

    This station would have 1 free bike and 9 parking slots (10 total), and
    distributed as P B P P P P P P P B.

    The stations are either EN LÍNEA (online) or FUERA DE LÍNEA (offline)

    Now, we can either count the "si" and "no" imgs, or just get the info
    from the "lat2" td. The first is funnier (in the eye-spoon horror way) and
    the latter makes, I guess, more sense.

We are not going to manually map the stations of all the sharing networks that
use this system, but if the community does it, that's ok (assumedly, this
information one day will be public / maybe we can ask them to make a dump).
"""

import re

from lxml import etree
from lxml import html

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['Bicicard']

_kml_ns = {
    'kml': 'http://earth.google.com/kml/2.2'
}

_xpath_q = "//td[@class='titulo']/text()[contains(.,'%s')]/ancestor::table[1]"\
           "//td[@class='lat2']/text()[contains(.,'ESTADO')]"

_re_bikes_slots = ".*\((?P<bikes>\d+)\/(?P<slots>\d+)\)" #  ESTADO - (1/10)
                                                         #            ↑  ↑
class Bicicard(BikeShareSystem):
    sync = True
    meta = {
        'system': 'Bicicard',
        'company': 'ITCL'
    }

    def __init__(self, tag, location_url, status_url, meta):
        super(Bicicard, self).__init__(tag, meta)
        self.location_url = location_url
        self.status_url   = status_url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        location_kml  = scraper.request(self.location_url).encode('utf-8')
        status_fuzzle = scraper.request(self.status_url)

        location_dom  = etree.fromstring(location_kml)
        status_dom    = html.fromstring(status_fuzzle)

        placemarks = location_dom.xpath("//kml:Placemark",
                                        namespaces = _kml_ns)
        index = 0
        stations = []
        for placemark in placemarks:
            name = placemark.findtext('kml:name', namespaces = _kml_ns)
            name_id = placemark.findtext('kml:description',
                                      namespaces = _kml_ns)
            coor = map(
                float, placemark.findtext('.//kml:coordinates',
                                          namespaces = _kml_ns).
                       split(',')[0:2]
            )

            # Find a status table with the name_id of this station, XPath
            # performance on this query is not really costly so far.
            try:
                (status,) = status_dom.xpath(_xpath_q % name_id)
            except ValueError:
                # Not found.. move along?
                continue

            m = re.search(_re_bikes_slots, status)
            bikes = int(m.group('bikes'))
            slots = int(m.group('slots'))

            station = BikeShareStation(index)
            station.name       = name
            station.latitude   = coor[1]
            station.longitude  = coor[0]
            station.bikes      = bikes
            station.free       = slots - bikes
            station.extra      = { 'slots': slots }

            stations.append(station)
            index = index + 1

        self.stations = stations


########NEW FILE########
__FILENAME__ = bicincitta
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the LGPL license, see LICENSE.txt

import re

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['BicincittaOld', 'Bicincitta','BicincittaStation']

class BaseSystem(BikeShareSystem):
    meta = {
        'system': 'Bicincittà',
        'company': 'Comunicare S.r.l.'
    }

class BicincittaOld(BaseSystem):
    sync = True
    _useragent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:14.0) '\
                 'Gecko/20100101 Firefox/14.0.1'
    _RE_INFO_LAT_CORD = "var sita_x =(.*?);"
    _RE_INFO_LNG_CORD = "var sita_y =(.*?);"
    _RE_INFO_NAME     = "var sita_n =(.*?);"
    _RE_INFO_AVAIL    = "var sita_b =(.*?);"
    _endpoint         = "http://www.bicincitta.com/citta_v3.asp?id={id}&pag=2"

    def __init__(self, tag, meta, system_id):
        super(BicincittaOld, self).__init__(tag, meta)
        self.system_id = system_id
        self.url = BicincittaOld._endpoint.format(id = system_id)

    @staticmethod
    def _clean_raw(raw_string):
        raw_string = raw_string.strip()
        raw_string = raw_string.replace("+","")
        raw_string = raw_string.replace("\"","")
        return raw_string.split("_")

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.setUserAgent(BicincittaOld._useragent)

        data = scraper.request(self.url)

        raw_lat   = re.findall(BicincittaOld._RE_INFO_LAT_CORD,data);
        raw_lng   = re.findall(BicincittaOld._RE_INFO_LNG_CORD,data);
        raw_name  = re.findall(BicincittaOld._RE_INFO_NAME,data);
        raw_avail = re.findall(BicincittaOld._RE_INFO_AVAIL,data);

        vec_lat   = BicincittaOld._clean_raw(raw_lat[0]);
        vec_lng   = BicincittaOld._clean_raw(raw_lng[0]);
        vec_name  = BicincittaOld._clean_raw(raw_name[0]);
        vec_avail = BicincittaOld._clean_raw(raw_avail[0]);
        
        stations = []

        for index, name in enumerate(vec_name):
            latitude    = float(vec_lat[index])
            longitude   = float(vec_lng[index])
            description = None
            bikes       = int(vec_avail[index].count('4'))
            free        = int(vec_avail[index].count('0'))
            station     = BicincittaStation(index, name, description, \
                            latitude, longitude, bikes, free)
            stations.append(station)
        self.stations = stations

class Bicincitta(BaseSystem):
    sync = True
    _RE_INFO="RefreshMap\((.*?)\)\;"
    _endpoint = "http://bicincitta.tobike.it/frmLeStazioni.aspx?ID={id}"

    def __init__(self, tag, meta, ** instance):
        super(Bicincitta, self).__init__(tag, meta)

        if 'endpoint' in instance:
            endpoint = instance['endpoint']
        else:
            endpoint = Bicincitta._endpoint

        if 'system_id' in instance:
            self.system_id = system_id
            self.url = [endpoint.format(id = system_id)]
        elif 'comunes' in instance:
            self.url = map(
                lambda comune: endpoint.format(id = comune['id']),
                instance['comunes']
            )
        else:
            self.url = [endpoint]


    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        self.stations = []
        for url in self.url:
            self.stations += Bicincitta._getStations(url, scraper)

    @staticmethod
    def _getStations(url, scraper):
        data = scraper.request(url)
        raw  = re.findall(Bicincitta._RE_INFO, data)
        info = raw[0].split('\',\'')
        info = map(lambda chunk: chunk.split('|'), info)
        stations = []

        for index in range(len(info[0])):
            name        = info[5][index]
            description = info[7][index]
            latitude    = float(info[3][index])
            longitude   = float(info[4][index])
            bikes       = int(info[6][index].count('4'))
            free        = int(info[6][index].count('0'))
            station     = BicincittaStation(index, name, description, \
                            latitude, longitude, bikes, free)
            stations.append(station)
        return stations

class BicincittaStation(BikeShareStation):
    def __init__(self, id, name, description, lat, lng, bikes, free):
        super(BicincittaStation, self).__init__(id)

        if name[-1] == ":":
            name = name[:-1]

        self.name        = utils.clean_string(name)
        self.latitude    = lat
        self.longitude   = lng
        self.bikes       = bikes
        self.free        = free
        self.extra       = { }

        if description is not None and description != u'':
            self.extra['description'] = utils.clean_string(description)


########NEW FILE########
__FILENAME__ = bicipalma
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import json
import re

from lxml import html
from lxml import etree

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['BiciPalma']

COOKIE_URL = "http://83.36.51.60:8080/eTraffic3/Control?act=mp"
DATA_URL = "http://83.36.51.60:8080/eTraffic3/DataServer?ele=equ&type=401&li=2.6288892088318&ld=2.6721907911682&ln=39.58800054245&ls=39.55559945755&zoom=15&adm=N&mapId=1&lang=es"
NAME_UID_RE = "\[(\d+)\] (.*)"

headers = {
'User-Agent':'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.106 Safari/535.2',
'Referer':'http://83.36.51.60:8080/eTraffic3/Control?act=mp'
}

class BiciPalma(BikeShareSystem):
    meta = {}

    def __init__(self, tag, meta):
        super(BiciPalma, self).__init__(tag, meta)

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.headers.update(headers)

        # First visit the cookie setter
        scraper.request(COOKIE_URL)
        # We should have now a nice cookie in our header

        # Wow many fuzzle, so ugly
        fuzzle = scraper.request(DATA_URL)
        markers = json.loads(fuzzle)

        stations = []
        for index, marker in enumerate(markers):
            # id = marker['id']
            # Seems that this id is just incremental, and not related to the
            # system at all.. discrating until further notiche?

            # [uid] name as [77] THIS IS HORRID SHIT
            uid, name = re.findall(NAME_UID_RE, marker['title'])[0]

            stat_fuzzle = html.fromstring(marker['paramsHtml'])
            stats = stat_fuzzle.cssselect('div#popParam')
            ints = []
            for i in range(1,6):
                ints.append(int([a for a in stats[i].itertext()][1].strip()))

            station = BikeShareStation(index)
            station.latitude = float(marker['realLat'])
            station.longitude = float(marker['realLon'])
            station.name = utils.sp_capwords(re.sub('\ *-\ *',' - ',name).title())
            station.bikes = ints[1]
            station.free = ints[4]
            station.extra = {
                'uid': uid,
                'enabled': marker['enabled'],
                'used_slots': ints[2],
                'faulty_slots': ints[3]
            }
            stations.append(station)

        self.stations = stations


########NEW FILE########
__FILENAME__ = bixi
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import json
import codecs

from pyquery import PyQuery as pq

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['BixiSystem', 'BixiStation']

parse_methods = {
    'xml': 'get_xml_stations',
    'json': 'get_json_stations',
    'json_from_xml': 'get_json_xml_stations'
}

class BixiSystem(BikeShareSystem):

    sync = True

    meta = { 
        'system': 'Bixi',
        'company': 'PBSC' 
    }

    def __init__(self, tag, feed_url, meta, format):
        super( BixiSystem, self).__init__(tag, meta)
        self.feed_url = feed_url
        self.method = format

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        if self.method not in parse_methods:
            raise Exception('Extractor for method %s is not implemented' % self.method )

        self.stations = eval(parse_methods[self.method])(self, scraper)

def get_xml_stations(self, scraper):
    xml_data = scraper.request(self.feed_url)
    dom = pq(xml_data.encode('utf-8'), parser = 'xml')
    markers = dom('station')
    stations = []
    
    for index, marker in enumerate(markers):
        station = BixiStation(index)
        station.from_xml(marker)
        stations.append(station)
    return stations

def get_json_stations(self, scraper):
    data = json.loads(scraper.request(self.feed_url))
    stations = []
    index = 0
    for marker in data['stationBeanList']:
        try:
          station = BixiStation(index)
          station.from_json(marker)
          index = index + 1
          stations.append(station)
        except Exception as e:
          print e
    return stations

def get_json_xml_stations(self, scraper):
    raw = scraper.request(self.feed_url).decode('unicode-escape')
    data = json.loads(raw)
    stations = []
    for index, marker in enumerate(data):
        station = BixiStation(index)
        station.from_json_xml(marker)
        stations.append(station)
    return stations

class BixiStation(BikeShareStation):

    def from_xml(self, xml_data):
        """ xml marker object as in
        <station>
            <id>1</id>
            <name>Notre Dame / Place Jacques Cartier</name>
            <terminalName>6001</terminalName>
            <lat>45.508183</lat>
            <long>-73.554094</long>
            <installed>true</installed>
            <locked>false</locked>
            <installDate>1276012920000</installDate>
            <removalDate />
            <temporary>false</temporary>
            <nbBikes>14</nbBikes>
            <nbEmptyDocks>17</nbEmptyDocks>
        </station>
        """
        xml_data = pq(xml_data, parser='xml')
        
        terminalName = xml_data('terminalName').text()
        name = xml_data('name').text()
        self.name = "%s - %s" % (terminalName, name)
        self.latitude = float(xml_data('lat').text())
        self.longitude = float(xml_data('long').text())
        self.bikes = int(xml_data('nbBikes').text())
        self.free = int(xml_data('nbEmptyDocks').text())

        self.extra = {
            'uid': int(xml_data('id').text()),
            'name': name,
            'terminalName' : terminalName,
            'locked': utils.str2bool(xml_data('locked').text()),
            'installed': utils.str2bool(xml_data('installed').text()),
            'temporary': utils.str2bool(xml_data('temporary').text()),
            'installDate': xml_data('installDate').text(),
            'removalDate': xml_data('removalDate').text(),
            'latestUpdateTime': xml_data('latestUpdateTime').text()
        }
        return self

    def from_json(self, data):
        '''
          {
            "id":2026,
            "stationName":"Broadway & W 60 Street",
            "availableDocks":0,
            "totalDocks":0,
            "latitude":40.76915505,
            "longitude":-73.98191841,
            "statusValue":"Planned",
            "statusKey":2,
            "availableBikes":0,
            "stAddress1":"Broadway & W 60 Street",
            "stAddress2":"",
            "city":"",
            "postalCode":"",
            "location":"",
            "altitude":"",
            "testStation":false,
            "lastCommunicationTime":null,
            "landMark":""
          }
        '''

        if data['statusValue'] == 'Planned' or data['testStation']:
            raise Exception('Station is only Planned or is a Test one')

        self.name      = "%s - %s" % (data['id'], data['stationName'])
        self.longitude = float(data['longitude'])
        self.latitude  = float(data['latitude'])
        self.bikes     = int(data['availableBikes'])
        self.free      = int(data['availableDocks'])

        self.extra = {
            'uid': int(data['id']),
            'statusValue': data['statusValue'],
            'statusKey': data['statusKey'],
            'stAddress1': data['stAddress1'],
            'stAddress2': data['stAddress2'],
            'city': data['city'],
            'postalCode': data['postalCode'],
            'location': data['location'],
            'altitude': data['altitude'],
            'testStation': data['testStation'],
            'lastCommunicationTime': data['lastCommunicationTime'],
            'landMark': data['landMark'],
            'totalDocks': data['totalDocks']
        }

        return self
    def from_json_xml(self, data):
        """ json marker object translated from xml
        { 
            "id": "2", 
            "name": "Docklands Drive - Docklands", 
            "terminalName": "60000", 
            "lastCommWithServer": "1375644471147", 
            "lat": "-37.814022", 
            "long": "144.939521", 
            "installed": "true", 
            "locked": "false", 
            "installDate": "1313724600000", 
            "removalDate": {  }, 
            "temporary": "false", 
            "public": "true", 
            "nbBikes": "15", 
            "nbEmptyDocks": "8", 
            "latestUpdateTime": "1375592453128" 
        }
        """
        
        self.name = "%s - %s" % (data['terminalName'], data['name'])
        self.latitude = float(data['lat'])
        self.longitude = float(data['long'])
        self.bikes = int(data['nbBikes'])
        self.free = int(data['nbEmptyDocks'])

        self.extra = {
            'uid': int(data['id']),
            'name': data['name'],
            'terminalName': data['terminalName'],
            'lastCommWithServer': data['lastCommWithServer'],
            'installed': utils.str2bool(data['installed']),
            'locked': utils.str2bool(data['locked']),
            'installDate': data['installDate'],
            'removalDate': data['removalDate'],
            'temporary': utils.str2bool(data['temporary']),
            'public': utils.str2bool(data['public']),
            'latestUpdateTime': data['latestUpdateTime']
        }
        return self
########NEW FILE########
__FILENAME__ = cyclocity
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import re
import json
import HTMLParser

from pyquery import PyQuery as pq
from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['Cyclocity','CyclocityStation','CyclocityWeb','CyclocityWebStation']

api_root = "https://api.jcdecaux.com/vls/v1/"

endpoints = {
    'contracts': 'contracts?apiKey={api_key}',
    'stations' : 'stations?apiKey={api_key}&contract={contract}',
    'station'  : 'stations/{station_id}?contract={contract}&apiKey={api_key}'
}

html_parser = HTMLParser.HTMLParser()

class Cyclocity(BikeShareSystem):

    sync = True

    authed = True

    meta = {
        'system': 'Cyclocity',
        'company': 'JCDecaux',
        'license': {
            'name': 'Open Licence',
            'url': 'https://developer.jcdecaux.com/#/opendata/licence'
        },
        'source': 'https://developer.jcdecaux.com'
    }

    def __init__(self, tag, meta, contract, key):
        super( Cyclocity, self).__init__(tag, meta)
        self.contract = contract
        self.api_key = key
        self.stations_url = api_root + endpoints['stations'].format(
            api_key  = self.api_key,
            contract = contract
        )

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        data = json.loads(scraper.request(self.stations_url))
        stations = []
        for index, info in enumerate(data):
            station_url = api_root + endpoints['station'].format(
                api_key    = self.api_key,
                contract   = self.contract,
                station_id = "{station_id}"
            )
            try:
                station = CyclocityStation(index, info, station_url)
                stations.append(station)
            except Exception:
                continue
        self.stations = stations

    @staticmethod
    def get_contracts(api_key, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        url = api_root + endpoints['contracts'].format(
            api_key = api_key
        )
        return json.loads(scraper.request(url))


class CyclocityStation(BikeShareStation):

    def __init__(self, id, jcd_data, station_url):
        super(CyclocityStation, self).__init__(id)

        self.name      = jcd_data['name']
        self.latitude  = jcd_data['position']['lat']
        self.longitude = jcd_data['position']['lng']
        self.bikes     = jcd_data['available_bikes']
        self.free      = jcd_data['available_bike_stands']

        self.extra = {
            'uid': jcd_data['number'],
            'address': jcd_data['address'],
            'status': jcd_data['status'],
            'banking': jcd_data['banking'],
            'bonus': jcd_data['bonus'],
            'last_update': jcd_data['last_update'],
            'slots': jcd_data['bike_stands']
        }

        self.url = station_url.format(station_id = jcd_data['number'])

        if self.latitude is None or self.longitude is None:
            raise Exception('An station needs a lat/lng to be defined!')

    def update(self, scraper = None, net_update = False):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        super(CyclocityStation, self).update()
        if net_update:
            status = json.loads(scraper.request(self.url))
            self.__init__(self.id, status, self.url)
        return self

class CyclocityWeb(BikeShareSystem):
    sync = False

    meta = {
        'system': 'Cyclocity',
        'company': 'JCDecaux'
    }

    _list_url = '/service/carto'
    _station_url = '/service/stationdetails/{city}/{id}'

    def __init__(self, tag, meta, endpoint, city):
        super(CyclocityWeb, self).__init__(tag, meta)
        self.endpoint    = endpoint
        self.city        = city
        self.list_url    = endpoint + CyclocityWeb._list_url
        self.station_url = endpoint + CyclocityWeb._station_url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        xml_markers = scraper.request(self.list_url)
        dom = pq(xml_markers.encode('utf-8'), parser = 'xml')
        markers = dom('marker')
        stations = []
        for index, marker in enumerate(markers):
            station = CyclocityWebStation(index)
            station.from_xml(marker)
            station.url = self.station_url.format(
                city = self.city, id = station.extra['uid']
            )
            stations.append(station)
        self.stations = stations

class CyclocityWebStation(BikeShareStation):
    def from_xml(self, marker):
        self.name = marker.get('name').title()
        self.latitude  = float(marker.get('lat'))
        self.longitude = float(marker.get('lng'))

        self.extra = {
            'uid': int(marker.get('number')),
            'address': html_parser.unescape(
                marker.get('fullAddress').rstrip()
            ),
            'open': int(marker.get('open')) == 1,
            'bonus': int(marker.get('bonus')) == 1
        }

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        super(CyclocityWebStation, self).update()

        status_xml = scraper.request(self.url)
        status = pq(status_xml.encode('utf-8'), parser = 'xml')

        self.bikes = int(status('available').text())
        self.free  = int(status('free').text())
        self.extra['open'] = int(status('open').text()) == 1
        self.extra['last_update'] = status('updated').text()
        self.extra['connected'] = status('connected').text()
        self.extra['slots'] = int(status('total').text())
        self.extra['ticket'] = int(status('ticket').text()) == 1


########NEW FILE########
__FILENAME__ = decobike
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import json
import codecs

from pyquery import PyQuery as pq

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['DecoBike']

FEED = "{endpoint}/playmoves.xml"

class DecoBike(BikeShareSystem):
    sync = True

    meta = {
        'system': 'DecoBike',
        'company': 'DecoBike LLC'
    }

    def __init__(self, tag, meta, endpoint):
        super(DecoBike, self).__init__(tag, meta)
        self.feed_url = FEED.format(endpoint = endpoint)

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        raw = scraper.request(self.feed_url)
        dom = pq(raw, parser = 'xml')
        stations = []
        for location in dom('location'):
            station = BikeShareStation(0)
            uid     = location.find('Id').text
            address = location.find('Address').text

            station.name      = "%s - %s" % (uid, address)
            station.latitude  = float(location.find('Latitude').text)
            station.longitude = float(location.find('Longitude').text)
            station.bikes     = int(location.find('Bikes').text)
            station.free      = int(location.find('Dockings').text)

            station.extra = {
                'uid': uid,
                'address': address
            }

            stations.append(station)

        self.stations = stations


########NEW FILE########
__FILENAME__ = domoblue
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the LGPL license, see LICENSE.txt

import re
import string

from pyquery import PyQuery as pq

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['Domoblue']

MAIN = 'http://clientes.domoblue.es/onroll/'
TOKEN_URL = 'generaMapa.php?cliente={service}&ancho=500&alto=700'
XML_URL = 'generaXml.php?token={token}&cliente={service}'
TOKEN_RE = 'generaXml\.php\?token\=(.*?)\&cliente'
USER_AGENT = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, '\
             'like Gecko) Chrome/18.0.1025.168 Safari/535.19'
STATUS_CODES = {
    14: 'Online',
    16: 'No Power',
    17: 'No Service'
}

def get_token(client_id, scraper):
    if 'Referer' in scraper.headers:
        del(scraper.headers['Referer'])
    url = MAIN + TOKEN_URL.format(service = client_id)
    data = scraper.request(url)
    token = re.findall(TOKEN_RE, data)
    scraper.headers['Referer'] = url
    return token[0]

def get_xml(client_id, scraper):
    token = get_token(client_id, scraper)
    url = MAIN + XML_URL.format(token = token, service = client_id)
    return scraper.request(url)

class Domoblue(BikeShareSystem):
    sync = True
    meta = {
        'system': 'Onroll',
        'company': 'Domoblue'
    }

    def __init__(self, tag, meta, system_id):
        super(Domoblue, self).__init__(tag, meta)
        self.system_id = system_id


    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.setUserAgent(USER_AGENT)

        xml_data = get_xml(self.system_id, scraper)
        xml_data = xml_data.encode('raw_unicode_escape').decode('utf-8')
        xml_dom = pq(xml_data, parser = 'xml')
        stations = []
        for index, marker in enumerate(xml_dom('marker')):
            station = BikeShareStation(index)
            station.name        = marker.get('nombre')
            station.bikes       = int(marker.get('bicicletas'))
            station.free        = int(marker.get('candadosLibres'))
            station.latitude    = float(marker.get('lat'))
            station.longitude   = float(marker.get('lng'))
            status_code         = int(marker.get('estado'))
            station.extra = {
                'status': {
                    'code':    status_code,
                    'online':  (lambda c: c == 14)(status_code),
                    'message': (lambda c: \
                                    STATUS_CODES[c] if c in STATUS_CODES \
                                                    else 'Planned'\
                               )(status_code)
                }
            }
            # Uppercase is UGLY, do not shout at me domoblue!
            station.name = utils.sp_capwords(station.name)

            stations.append(station)
        self.stations = stations

########NEW FILE########
__FILENAME__ = emovity
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the LGPL license, see LICENSE.txt

import re

from lxml import html

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['Emovity']

RE_INFO = "var html\d+ =\'(.*)\'"
RE_LATLNG = 'var pBikes\d+= new GLatLng\((.*)\,(.*)\)'

class Emovity(BikeShareSystem):
    sync = True
    meta = {
        'system': 'Emovity',
        'company': 'ICNITA S.L.'
    }

    def __init__(self, tag, feed_url, meta):
        super(Emovity, self).__init__(tag, meta)
        self.feed_url = feed_url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        fuzzle = scraper.request(self.feed_url)
        latlngs = re.findall(RE_LATLNG, fuzzle)
        infos = re.findall(RE_INFO, fuzzle)
        stations = []

        for i in range(0, len(latlngs)):
            tree = html.fromstring(infos[i])

            station = BikeShareStation(i)
            station.latitude = float(latlngs[i][0])
            station.longitude = float(latlngs[i][1])
            station.name = tree[1].text
            station.bikes = int(re.findall(".*: (\d+)", tree[2].text)[0])
            station.free  = int(re.findall(".*: (\d+)", tree[3].text)[0])
            station.extra = {
                'uid': re.findall("(\d+)\-.*", tree[0].text)[0]
            }
            stations.append(station)
        self.stations = stations

########NEW FILE########
__FILENAME__ = gewista_citybike
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

from pyquery import PyQuery as pq

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = ['GewistaCityBike']

class GewistaCityBike(BikeShareSystem):

    sync = True

    meta = {
        'system': 'CityBike',
        'company': 'Gewista Werbegesellschaft m.b.H'
    }

    def __init__(self, tag, endpoint, meta):
        super(GewistaCityBike, self).__init__(tag, meta)
        self.endpoint = endpoint

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        data = scraper.request(self.endpoint)
        dom  = pq(data.encode('utf-8'), parser = 'xml')
        markers = dom('station')
        stations = []
        for index, marker in enumerate(markers):
            station = GewistaStation(index)
            station.from_xml(marker)
            stations.append(station)
        self.stations = stations

class GewistaStation(BikeShareStation):
    def from_xml(self, xml_data):
        """
        <station>
            <id>2001</id>
            <internal_id>1046</internal_id>
            <name>Wallensteinplatz</name>
            <boxes>27</boxes>
            <free_boxes>19</free_boxes>
            <free_bikes>8</free_bikes>
            <status>aktiv</status>
            <description/>
            <latitude>48.229912</latitude>
            <longitude>16.371582</longitude>
        </station>
        """
        xml_data = pq(xml_data, parser='xml')

        self.name      = xml_data('name').text()
        self.latitude  = float(xml_data('latitude').text())
        self.longitude = float(xml_data('longitude').text())
        self.bikes     = int(xml_data('free_bikes').text())
        self.free      = int(xml_data('free_boxes').text())

        self.extra = {
            'uid': int(xml_data('id').text()),
            'internal_id': int(xml_data('internal_id').text()),
            'status': xml_data('status').text(),
            'description': xml_data('description').text(),
            'slots': int(xml_data('boxes').text())
        }


########NEW FILE########
__FILENAME__ = hacks
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt


hack_table = {
    'cristolib': ['cristolib'],
    'le-velo': ['levelo']
}

class cristolib(object):
    def markers(self, markers):
        return [marker for marker in markers if int(marker.attrib['number']) < 30]

class levelo(object):
    def markers(self, markers):
        return [marker for marker in markers if int(marker.attrib['number']) != 602]

########NEW FILE########
__FILENAME__ = keolis
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

from .base import BikeShareSystem, BikeShareStation
from . import utils

from lxml import etree

__all__ = ['Keolis_v2', 'KeolisStation_v2']

xml_parser = etree.XMLParser(recover = True)

class Keolis_v2(BikeShareSystem):

    sync = False

    meta = {
        'system': 'Keolis',
        'company': 'Keolis'
    }

    _list_url = '/stations/xml-stations.aspx'
    _station_url = '/stations/xml-station.aspx?borne={id}'

    def __init__(self, tag, feed_url, meta):
        super(Keolis_v2, self).__init__(tag, meta)
        self.feed_url = feed_url + self._list_url
        self.station_url = feed_url + self._station_url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        raw_list = scraper.request(self.feed_url).encode('utf-16')
        xml_list = etree.fromstring(raw_list, xml_parser)

        stations = []
        for index, marker in enumerate(xml_list.iter('marker')):
            station = KeolisStation_v2(index, marker, self.station_url)
            stations.append(station)
        self.stations = stations

class KeolisStation_v2(BikeShareStation):
    def __init__(self, index, marker, station_url):
        super(KeolisStation_v2, self).__init__(index)

        self.name      = marker.get('name')
        self.latitude  = float(marker.get('lat'))
        self.longitude = float(marker.get('lng'))
        self.extra     = {
            'uid': int(marker.get('id'))
        }

        self._station_url = station_url.format(id = self.extra['uid'])

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        raw_status = scraper.request(self._station_url).encode('utf-16')
        xml_status = etree.fromstring(raw_status, xml_parser)
        self.bikes = int(xml_status.find('bikes').text)
        self.free  = int(xml_status.find('attachs').text)

        self.extra['address'] = xml_status.find('adress').text.title()

        # TODO: Try to standarize these fields
        # 0 means online, 1 means temporarily unavailable
        # are there more status?
        self.extra['status'] = xml_status.find('status').text

        # payment: AVEC_TPE | SANS_TPE
        # as in, accepts bank cards or not
        self.extra['payment'] = xml_status.find('paiement').text

        # Update time as in 47 seconds ago: '47 secondes'
        self.extra['lastupd'] = xml_status.find('lastupd').text


########NEW FILE########
__FILENAME__ = smartbike
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import re
import json
from pyquery import PyQuery as pq
from lxml import html

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = [ 'SmartBike', 'SmartBikeStation',
            'SmartClunky', 'SmartClunkyStation',
            'SmartShitty', 'SmartShittyStation' ]

LAT_LNG_RGX = 'point \= new GLatLng\((.*?)\,(.*?)\)'
ID_ADD_RGX = 'idStation\=(.*)\&addressnew\=(.*)\&s\_id\_idioma'
ID_ADD_RGX_V = 'idStation\=\"\+(.*)\+\"\&addressnew\=(.*)\+\"\&s\_id\_idioma'

parse_methods = {
    'xml': 'get_xml_stations',
    'json': 'get_json_stations',
    'json_v2': 'get_json_v2_stations'
}

class BaseSystem(BikeShareSystem):
    meta = {
        'system': 'SmartBike',
        'company': 'ClearChannel'
    }

class SmartBike(BaseSystem):
    sync = True

    def __init__(self, tag, meta, feed_url, format = "json"):
        super(SmartBike, self).__init__(tag, meta)
        self.feed_url = feed_url
        if format not in parse_methods:
            raise Exception('Unsupported method %s' % format)
        self.method = parse_methods[format]

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        raw_req = scraper.request(self.feed_url)
        self.stations = eval(self.method)(self, raw_req)

def get_xml_stations(self, raw):
    raise Exception("Not implemented")

def get_json_stations(self, raw):
    # Double encoded json FTWTF..
    data = json.loads(json.loads(raw)[1]['data'])
    stations = map(SmartBikeStation, data)
    return stations

def get_json_v2_stations(self, raw):
    data = json.loads(raw)
    stations = map(SmartBikeStation, data)
    return stations

class SmartBikeStation(BikeShareStation):
    def __init__(self, info):
        super(SmartBikeStation, self).__init__(0)
        try:
            self.name      = info['StationName']
            self.bikes     = int(info['StationAvailableBikes'])
            self.free      = int(info['StationFreeSlot'])
            self.latitude  = float(info['AddressGmapsLatitude'])
            self.longitude = float(info['AddressGmapsLongitude'])
            self.extra = {
                'uid': info['StationID'],
                'status': info['StationStatusCode'],
                'districtCode': info['DisctrictCode'],
                'NearbyStationList': map(
                    int, info['NearbyStationList'].split(',')
                )
            }
        except KeyError:
            # Either something has changed, or it's the other type of feed
            # Same data, different keys.
            self.name = info['name']
            self.bikes = int(info['bikes'])
            self.free = int(info['slots'])
            self.latitude = float(info['lat'])
            self.longitude = float(info['lon'])
            self.extra = {
                'uid': info['id'],
                'status': info['status'],
                'districtCode': info['district'],
                'address': info['address']
            }
            if info['nearbyStations'] is not None:
                self.extra['NearbyStationList'] = map(
                    int, info['nearbyStations'].split(',')
                )
            if info['zip'] is not None:
                self.extra['zip'] = info['zip']


class SmartClunky(BaseSystem):
    sync = False
    list_url = "/localizaciones/localizaciones.php"
    station_url = "/CallWebService/StationBussinesStatus.php"

    def __init__(self, tag, meta, root_url, ** extra):
        super(SmartClunky, self).__init__(tag, meta)
        self.root_url = root_url
        if 'list_url' in extra:
            self.list_url = extra['list_url']

        if 'station_url' in extra:
            self.station_url = extra['station_url']

    def update(self, scraper = None):

        if scraper is None:
            scraper = utils.PyBikesScraper()

        raw = scraper.request(
            "{0}{1}".format(self.root_url, self.list_url)
        )
        geopoints = re.findall(LAT_LNG_RGX, raw)
        ids_addrs = re.findall(ID_ADD_RGX_V, raw)
        stations = []

        for index, geopoint in enumerate(geopoints):
            station = SmartClunkyStation(index)
            station.latitude = float(geopoint[0])
            station.longitude = float(geopoint[1])
            uid = int(ids_addrs[index][0])
            station.extra = {
                'uid': uid,
                'token': ids_addrs[index][1]
            }
            station.parent = self
            stations.append(station)

        self.stations = stations

class SmartClunkyStation(BikeShareStation):
    def update(self, scraper = None):

        if scraper is None:
            scraper = utils.PyBikesScraper()


        super(SmartClunkyStation, self).update()
        raw = scraper.request( method="POST",
                url = "{0}{1}".format(
                    self.parent.root_url,
                    self.parent.station_url
                ),
                data = {
                    'idStation': self.extra['uid'],
                    'addressnew': self.extra['token']
                }
        )
        dom = pq(raw)
        availability = dom('div').eq(2).text().split(':')
        name = dom('div').eq(1).text().replace('<br>','').strip()
        self.name = name.encode('utf-8')
        self.bikes = int(availability[1].lstrip())
        self.free = int(availability[2].lstrip())

        return True

class SmartShitty(BaseSystem):
    """
    BikeMI decided to implement yet another way of displaying the map...
    So, I guess what we will do here is using a regular expression to get the
    info inside the $create function, and then load that as a JSON. Who the
    fuck pay this guys money, seriously?

    <script type="text/javascript">
    //<![CDATA[
    Sys.Application.add_init(function() {
        $create(Artem.Google.MarkersBehavior, {
            "markerOptions":[
                {
                    "clickable":true,
                    "icon":{
                        ...
                    },
                    "optimized":true,
                    "position":{
                        "lat":45.464683238625966,
                        "lng":9.18879747390747
                    },
                    "raiseOnDrag":true,
                    "title":"01 - Duomo",    _____ Thank you...
                    "visible":true,         /
                    "info":"<div style=\"width: 240px; height: 100px;\">
                                <span style=\"font-weight: bold;\">
                                    01 - Duomo
                                </span>
                                <br/>
                                <ul>
                                    <li>Available bicycles: 17</li>
                                    <li>Available slots: 7</li>
                                </ul>
                            </div>
                }, ...
            ],
            "name": "fuckeduplongstring"
        }, null, null, $get("station-map"));
    })
    """
    sync = True

    _RE_MARKERS = 'Google\.MarkersBehavior\,\ (?P<data>.*?)\,\ null'

    def __init__(self, tag, meta, feed_url):
        super(SmartShitty, self).__init__(tag, meta)
        self.feed_url = feed_url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        page = scraper.request(self.feed_url)
        markers = json.loads(
            re.search(SmartShitty._RE_MARKERS, page).group('data')
        )['markerOptions']
        self.stations = map(SmartShittyStation, markers)

class SmartShittyStation(BikeShareStation):
    def __init__(self, marker):
        super(SmartShittyStation, self).__init__(0) #TODO: remove idx in base

        avail_soup   = html.fromstring(marker['info'])
        availability = map(
            lambda x: int(x.split(':')[1]),
            avail_soup.xpath("//div/ul/li/text()")
        )

        self.name      = marker['title']
        self.latitude  = marker['position']['lat']
        self.longitude = marker['position']['lng']
        self.bikes     = availability[0]
        self.free      = availability[1]


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import re
import requests
import urllib, urllib2
from urlparse import urlparse

def str2bool(v):
  return v.lower() in ["yes", "true", "t", "1"]

def url_scheme(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme

def sp_capwords(word):
    blacklist = [
        u'el', u'la', u'los', u'las', \
        u'un', u'una', u'unos', u'unas', \
        u'lo', u'al', u'del', \
        u'a', u'ante', u'bajo', u'cabe', u'con', u'contra', u'de', u'desde', \
        u'en', u'entre', u'hacia', u'hasta', u'mediante', u'para', u'por', \
        u'según', u'sin' \
        # Catala | Valencia | Mallorqui
        u'ses', u'sa', u'ses'
    ]
    word = word.lower()
    cap_lambda = lambda (index, w): \
                    w.capitalize() if index == 0 or w not in blacklist \
                                   else w
    return " ".join(map(cap_lambda, enumerate(word.split())))

def clean_string(dirty):
    # Way generic strip_tags. This is unsafe in some cases, but gets the job
    # done for most inputs
    dirty = re.sub(r'<[^>]*?>', '', dirty)
    # Decode any escaped sequences
    dirty = dirty.encode('utf-8').decode('unicode_escape')
    return dirty

class PyBikesScraper(object):
    
    headers = {
        'User-Agent': 'PyBikes'
    }

    proxies = {}

    proxy_enabled = False

    last_request = None

    def __init__(self):

        self.session = requests.session()


    def setUserAgent(self, user_agent):

        self.headers['User-Agent'] = user_agent

    def request(self, url, method = 'GET', params = None, data = None):

        if self.proxy_enabled and url_scheme(url) == 'https':
            proxy = urllib2.ProxyHandler(self.proxies)
            opener = urllib2.build_opener(proxy)
            response = opener.open(url)
            data = response.read()
            if "charset" in response.headers['content-type']:
                encoding = response.headers['content-type'].split('charset=')[-1]
                data = unicode(data, encoding)
            self.last_request = response
            return data

        response = self.session.request(
            method = method,
            url = url,
            params = params,
            data = data,
            proxies = self.getProxies(),
            headers = self.headers,
            verify = False
        )
        if 'set-cookie' in response.headers:
            self.headers['Cookie'] = response.headers['set-cookie']
            
        self.last_request = response
        return response.text

    def clearCookie(self):
        
        if 'Cookie' in self.headers:
            del self.headers['Cookie']

    def setProxies(self, proxies ):
        self.proxies = proxies

    def getProxies(self):
        if self.proxy_enabled:
            return self.proxies
        else:
            return {}

    def enableProxy(self):
        self.proxy_enabled = True

    def disableProxy(self):
        self.proxy_enabled = False

########NEW FILE########
__FILENAME__ = unittest_pybikes
# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import unittest
from pkg_resources import resource_string
import json

import sys

import pybikes
from pybikes import *
from pybikes import utils
import test_keys

class TestSystems(unittest.TestCase):

    def test_bixi(self):
        self._test_systems('bixi')

    def test_bcycle(self):
        self._test_systems('bcycle')

    def test_cyclocity(self):
        self._test_systems('cyclocity')

    def test_gewista(self):
        self._test_systems('gewista')

    def test_smartbike(self):
        self._test_systems('smartbike')

    def test_decobike(self):
        self._test_systems('decobike')

    def test_keolis(self):
        self._test_systems('keolis')

    def test_domoblue(self):
        self._test_systems('domoblue')

    def test_emovity(self):
        self._test_systems('emovity')

    def test_bicipalma(self):
        self._test_systems('bicipalma')

    def test_bicincitta(self):
        self._test_systems('bicincitta')

    def test_bicincittaold(self):
        self._test_systems('bicincittaold')

    def test_bicicard(self):
        self._test_systems('bicicard')

    def _test_systems(self, system):
        data = pybikes.getDataFile(system)
        if isinstance(data['class'], unicode):
            sys_class = eval(data['class'])
            if sys_class.authed:
                key = eval('test_keys.%s' % system)
            else:
                key = None
            for instance in data['instances']:
                self._test_system(system, instance['tag'], key)
        elif isinstance(data['class'], dict):
            for cls in data['class']:
                sys_class = eval(cls)
                if sys_class.authed:
                    key = eval('test_keys.%s' % system)
                else:
                    key = None
                for instance in data['class'][cls]['instances']:
                    self._test_system(system, instance['tag'], key)
        else:
            raise Exception('Malformed data file')

    def _test_system(self, system, tag, key = None):
        """ Tests okayness of a system:
            - Test if system can be updated
            - Tests okayness of 5 stations on the system
        """
        p_sys = pybikes.getBikeShareSystem(system, tag, key)
        self._test_update(p_sys)
        station_string = ""
        if len(p_sys.stations) < 5:
            t_range = len(p_sys.stations)
        else:
            t_range = 5
        for i in range(t_range):
            station_string += unichr(ord(u'▚') + i)
            sys.stdout.flush()
            sys.stdout.write('\r[%s] testing %d' % (station_string, i+1))
            sys.stdout.flush()
            self._test_station_ok(p_sys, p_sys.stations[i])
        sys.stdout.flush()
        sys.stdout.write('\r↑ stations look ok ↑                          \n\n')
        sys.stdout.flush()

    def _test_station_ok(self, instance, station):
        """ Tests okayness of a station:
            - coming from an async system
                - Station can be updated
            - Station has its base parameters
        """
        if not instance.sync:
            station.update()
            self._test_allows_parameter(station)
        else:
            self._test_dumb_allows_parameter(station)

        self.assertIsNotNone(station.bikes)
        self.assertIsNotNone(station.free)
        self.assertIsNotNone(station.latitude)
        self.assertIsNotNone(station.longitude)
        self.assertIsNotNone(station.name)

    def _test_update(self, instance):
        """ Tests if this system can be updated
            we assume that having more than 0 stations
            means being updateable. Also, test if its update function
            allows a PyBikesScraper parameter
        """
        instance.update()
        print "%s has %d stations" % (
            instance.meta['name'], len(instance.stations)
        )
        self.assertTrue(len(instance.stations)>0)
        self._test_allows_parameter(instance)

    def _test_allows_parameter(self, instance):
        """ Tests if this instance, be it a system or a station, allows a
            PyBikesScraper parameter for its update method
        """
        scraper = utils.PyBikesScraper()
        instance.update(scraper)
        self.assertIsNotNone(scraper.last_request)

    def _test_dumb_allows_parameter(self, instance):
        """ Dumber version of the allows parameter test, in this case, we
            just want to check that calling a synchronous system station
            update with an scraper does not fail (more clearly, that the
            parameter is defined in the base class, hence we can always
            pass the scraper by)
        """
        raised = False
        try:
            scraper = utils.PyBikesScraper()
            instance.update(scraper)
        except Exception:
            raised = True
        self.assertFalse(raised, 'Base class does not allow an scraper parameter')


class TestBikeShareStationInstance(unittest.TestCase):

    def setUp(self):
        self.battery = []

        stationFoo = BikeShareStation(0)
        stationFoo.name = 'foo'
        stationFoo.latitude = 40.0149856
        stationFoo.longitude = -105.2705455
        stationFoo.bikes = 10
        stationFoo.free = 20
        stationFoo.extra = {
            'foo': 'fuzz'
        }

        stationBar = BikeShareStation(1)
        stationBar.name = 'foo'
        stationBar.latitude = 19.4326077
        stationBar.longitude = -99.13320799999997
        stationBar.bikes = 10
        stationBar.free = 20
        stationBar.extra = {
            'bar': 'baz'
        }

        self.battery.append({
            'instance': stationFoo,
            'hash': 'e1aea428a04db6a77c4a1a091edcfcb6'
        })
        self.battery.append({
            'instance': stationBar,
            'hash': '065d7bb95e6c9079190334ee0d320c72'
        })
    def testHash(self):
        for unit in self.battery:
            self.assertEqual(
                unit['instance'].get_hash(),
                unit['hash']
            )

class TestBikeShareSystemInstance(unittest.TestCase):
    
    def setUp(self):

        metaFoo = {
            'name' : 'Foo',
            'uname' : 'foo',
            'city' : 'Fooland',
            'country' : 'FooEmpire',
            'latitude' : 10.12312,
            'longitude' : 1.12312,
            'company' : 'FooCompany'
        }

        metaBar = {
            'name' : 'Bar',
            'uname' : 'bar',
            'city' : 'Barland',
            'population' : 100000
        }

        class FooSystem(BikeShareSystem):
            pass

        class BarSystem(BikeShareSystem):
            # Tests inheritance in meta-data:
            # - System has own meta-data
            # - Instance has also, meta-data
            # -> Hence, the result should have:
            #     1) Mandatory metadata of BikeShareSystem
            #     2) Base metadata of the system (BarSystem)
            #     3) Metadata passed on instantiation (metaBar)
            meta = {
                'company' : 'BarCompany'
            }

        self.battery = []
        self.battery.append({
                        'tag': 'foo',
                        'meta': metaFoo,
                        'instance': FooSystem('foo', metaFoo)
                    })
        self.battery.append({
                        'tag': 'bar',
                        'meta': dict(metaBar,**BarSystem.meta),
                        'instance': BarSystem('bar',metaBar)
                    })

    def test_instantiation(self):
        # make sure instantiation parameters are correctly stored

        for unit in self.battery:
            
            self.assertEqual(unit.get('tag'), unit.get('instance').tag)

            # Check that all metainfo set on instantiation
            # appears on the instance
            for meta in unit.get('meta'):
                self.assertIn(meta,unit.get('instance').meta)
                self.assertEqual(
                        unit.get('meta').get(meta), 
                        unit.get('instance').meta.get(meta)
                    )

            # Check that all metainfo not set on instantiation
            # appears on the instance as None
            for meta in BikeShareSystem.meta:
                if meta not in unit.get('meta'):
                    self.assertIn(meta, unit.get('instance').meta)
                    self.assertEqual(
                        None, 
                        unit.get('instance').meta.get(meta)
                    )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
