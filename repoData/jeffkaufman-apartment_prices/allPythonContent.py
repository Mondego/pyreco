__FILENAME__ = draw_heatmap
import Image
import sys
import math

# set boundaries in query_padmapper
from query_padmapper import MAX_LAT, MAX_LON, MIN_LAT, MIN_LON

# change these to change how detailed the generated image is
# (1000x1000 is good, but very slow)
MAX_X=100
MAX_Y=100

# at what distance should we stop making predictions?
IGNORE_DIST=0.01

# this is a good waty
MODE = "INVERTED_DISTANCE_WEIGHTED_AVERAGE"
#MODE = "K_NEAREST_NEIGHBORS"

# this only affects k_nearest mode
K=5

def pixel_to_ll(x,y):
    delta_lat = MAX_LAT-MIN_LAT
    delta_lon = MAX_LON-MIN_LON

    # x is lon, y is lat
    # 0,0 is MIN_LON, MAX_LAT

    x_frac = float(x)/MAX_X
    y_frac = float(y)/MAX_Y

    lon = MIN_LON + x_frac*delta_lon
    lat = MAX_LAT - y_frac*delta_lat


    calc_x, calc_y = ll_to_pixel(lat, lon)

    if abs(calc_x-x) > 1 or abs(calc_y-y) > 1:
        print "Mismatch: %s, %s => %s %s" % (
            x,y, calc_x, calc_y)

    return lat, lon

def ll_to_pixel(lat,lon):
    adj_lat = lat-MIN_LAT
    adj_lon = lon-MIN_LON

    delta_lat = MAX_LAT-MIN_LAT
    delta_lon = MAX_LON-MIN_LON

    # x is lon, y is lat
    # 0,0 is MIN_LON, MAX_LAT

    lon_frac = adj_lon/delta_lon
    lat_frac = adj_lat/delta_lat

    x = int(lon_frac*MAX_X)
    y = int((1-lat_frac)*MAX_Y)

    return x,y

def load_prices(fs, price_per_room=False):
    prices = []
    seen = set()
    for f in fs:
        with open(f) as inf:
            for line in inf:
                if not line[0].isdigit():
                    continue

                rent, bedrooms, apt_id, lon, lat = line.strip().split()

                if apt_id in seen:
                    continue
                else:
                    seen.add(apt_id)

                rent, bedrooms = int(rent), int(bedrooms)

                assert bedrooms >= 0
                rooms = bedrooms + 1

                if bedrooms < 1:
                    bedrooms = 1 # singles

                if price_per_room:
                    price = rent / rooms
                else:
                    price = rent / bedrooms

                if price < 150:
                    continue

                prices.append((price, float(lat), float(lon)))

    return prices

def distance(x1,y1,x2,y2):
    return math.sqrt((x1-x2)*(x1-x2) + (y1-y2)*(y1-y2))

def k_nearest(prices, lat, lon):
    distances = [(distance(lat,lon,plat,plon), price)
                 for (price, plat, plon) in prices]
    distances.sort()
    prices = [price for (dist, price) in distances[:K]
              if dist < IGNORE_DIST]
    if len(prices) != K:
        return None
    return prices

def greyscale(price):
    grey = int(256*float(price)/3000)
    return grey, grey, grey

def color(val, price_per_room=False):
    if val is None:
        return (255,255,255,0)

    if price_per_room:
        prices = [1600, 1500, 1400, 1300, 1200, 1100, 1000, 900,
                  800, 700, 600, 500, 400, 300, 250, 200]
    else:
        prices = [1800, 1700, 1600, 1500, 1400, 1300, 1200, 1100,
                  1000, 900, 800, 700, 600, 500, 400, 300]

    colors = [(255, 0, 0), # red
              (255, 43, 0), # redorange
              (255, 86, 0), # orangered
              (255, 127, 0), # orange
              (255, 171, 0), # orangeyellow
              (255, 213, 0), # yelloworange
              (255, 255, 0), # yellow
              (127, 255, 0), # lime green
              (0, 255, 0), # green
              (0, 255, 127), # teal
              (0, 255, 255), # light blue,
              (0, 213, 255), # medium light blue
              (0, 171, 255), # light medium blue
              (0, 127, 255), # medium blue
              (0, 86, 255), # medium dark blue
              (0, 43, 255), # dark medium blue
              (0, 0, 255), # dark blue
              ]

    assert len(prices) == len(colors) - 1

    for price, color in zip(prices, colors):
        if val > price:
            return color
    return colors[-1]

def inverted_distance_weighted_average(prices, lat, lon):
    num = 0
    dnm = 0
    c = 0

    for price, plat, plon in prices:
        dist = distance(lat,lon,plat,plon) + 0.0001

        if dist > IGNORE_DIST:
            continue

        inv_dist = 1/dist

        num += price * inv_dist
        dnm += inv_dist
        c += 1

    # don't display any averages that don't take into account at least five data points
    if c < 5:
        return None

    return num/dnm


def start(fname, price_per_X):
    assert price_per_X in ["room", "bedroom"]
    price_per_room = price_per_X == "room"

    priced_points = load_prices([fname], price_per_room)

    I = Image.new('RGBA', (MAX_X, MAX_Y))
    IM = I.load()

    for x in range(MAX_X):
        for y in range(MAX_Y):
            lat, lon = pixel_to_ll(x,y)

            if MODE == "K_NEAREST_NEIGHBORS":
                nearest = k_nearest(priced_points, lat, lon)
                if not nearest:
                    price = None
                else:
                    price = float(sum(nearest))/K
            elif MODE == "INVERTED_DISTANCE_WEIGHTED_AVERAGE":
                price = inverted_distance_weighted_average(priced_points, lat, lon)
            else:
                assert False

            IM[x,y] = color(price, price_per_room)


        print "%s/%s" % (x, MAX_X)

    for _, lat, lon in priced_points:
        x, y = ll_to_pixel(lat, lon)
        if 0 <= x < MAX_X and 0 <= y < MAX_Y:
            IM[x,y] = (0,0,0)

    I.save(fname + "." + price_per_X + "." + str(MAX_X) + ".png", "PNG")

if __name__ == "__main__":
    if len(sys.argv) > 3 or len(sys.argv) < 2:
        print "usage: python draw_heatmap.py apts.txt [room|bedroom]"
        print "   room: price is $ per estimated rooms, which is bedrooms + 1"
        print "   bedroom: price is $ per bedroom, with singles counting as one bedroom"
        print " default is 'room' as this better reflects the underlying variable of"
        print " price per square foot"
    else:
        fname = sys.argv[1]
        if len(sys.argv) > 2:
            price_per_X = sys.argv[2]
        else:
            price_per_X = "room"
        start(fname, price_per_X)

########NEW FILE########
__FILENAME__ = query_padmapper
import time
import sys
import urllib
import json
import time

# boston
MIN_LAT=42.255594
MAX_LAT=42.4351936
MIN_LON=-71.1828231
MAX_LON=-70.975800

# baltimore
#MAX_LAT=39.388979
#MIN_LON=-76.752548
#MIN_LAT=39.208315
#MAX_LON=-76.464844

# atlanta
#MIN_LAT=33.453214
#MAX_LON=-84.017944
#MAX_LAT=33.934245
#MIN_LON=-84.508209

# bay area from google maps: ll=37.53151,-122.163849&spn=0.634907,1.0849
#MIN_LAT=37.23
#MAX_LON=-121.62
#MAX_LAT=37.83
#MIN_LON=-122.70

MAX_RENT=6050

DEFAULTS = {
    'cities': 'false',
    'showPOI': 'false',
    'limit': 2000,
    'minRent': 0,
    'maxRent': 6000,
    'searchTerms': '',
    'maxPricePerBedroom': 6000,
    'minBR': 0,
    'maxBR': 10,
    'minBA': 1,
    'maxAge': 7,
    'imagesOnly': 'false',
    'phoneReq': 'false',
    'cats': 'false',
    'dogs': 'false',
    'noFee': 'false',
    'showSubs': 'true',
    'showNonSubs': 'true',
    'showRooms': 'true',
    'userId': -1,
    'cl': 'true',
    'apts': 'true',
    'ood': 'true',
    'zoom': 15,
    'favsOnly': 'false',
    'onlyHQ': 'true',
    'showHidden': 'false',
    'workplaceLat': 0,
    'workplaceLong': 0,
    'maxTime': 0
    }

def query(kwargs):
    assert 'eastLong' in kwargs
    assert 'northLat' in kwargs
    assert 'westLong' in kwargs
    assert 'southLat' in kwargs

    url='https://www.padmapper.com/reloadMarkersJSON.php'

    full_url = '%s?%s' % (url, '&'.join('%s=%s' % (k,v) for (k,v) in kwargs.items()))

    apts = []

    txt = ""
    try:
        txt = urllib.urlopen(full_url).read()
        j = json.loads(txt)
    except Exception, e:
        print "ERROR", e
        print "ERROR", txt
        print "ERROR", full_url
        return []

    for apartment in j:
        apts.append(( apartment['id'], apartment['lng'], apartment['lat'] ))

    assert len(apts) < kwargs['limit']-1

    return apts

def start():
    kwargs = dict((k,v) for (k,v) in DEFAULTS.items())
    kwargs['southLat']=MIN_LAT
    kwargs['westLong']=MIN_LON
    kwargs['northLat']=MAX_LAT
    kwargs['eastLong']=MAX_LON

    seen_ids = set()

    epoch_timestamp = int(time.mktime(time.gmtime()))
    with open("apts-%s.txt" % epoch_timestamp, 'w') as outf:
        for rent in range(100,MAX_RENT,25):
            print "querying from $%s ..." % rent
            for bedrooms in range(10):
                kwargs['minRent'] = rent-25
                kwargs['maxRent'] = rent
                kwargs['minBR'] = bedrooms
                kwargs['maxBR'] = bedrooms

                for apt_id, lon, lat in query(kwargs):
                    if apt_id not in seen_ids:
                        outf.write("%s %s %s %s %s\n" % (
                                rent, bedrooms, apt_id, lon, lat))
                        sys.stdout.flush()
                        seen_ids.add(apt_id)

                time.sleep(2)


if __name__=="__main__":
    print """
The guy who wrote Padmapper says this tool puts a pretty heavy load on his server and he
would rather it was run no more than once a month.  If you're just looking for some
apartment data, I've put some in apts-2013-01-29, which is for Boston in January 2013.
"""
    # start(*sys.argv[1:])

    print """
Ones labeled $6000 in the output file are really $6000+.  You can fix them manually
by going to https://www.padmapper.com/show.php?type=0&id=[ID]&src=main for each one (the
id is the third output column) and looking at what it says there.

You probably also want to look over expensive '0 bedroom' apartments to check that none
are commercial listings.
"""

########NEW FILE########
