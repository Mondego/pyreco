__FILENAME__ = decorators
from django.http import HttpResponse

import json

class ApiHandler(object):
    """When passed lists or dicts, it will return them in various serialized
    forms. Defaults to JSON, can also do JSONP."""

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        request = args[0]
        format = request.GET.get('format')

        response = self.func(*args, **kwargs)
        if format == 'jsonp':
            data = json.dumps(response)
            callback = request.GET.get('callback')

            if callback:
                data = "%s(%s)" % (callback, data)
                mime_type = 'application/javascript'
        else:
            mime_type = 'application/json'
            data = json.dumps(response)

        return HttpResponse(data, content_type=mime_type)

########NEW FILE########
__FILENAME__ = geojson
from django.core.management.base import BaseCommand
from open311dashboard.dashboard.models import Geography, Request, Street

from django.db import connection
import json

# TODO: ABSTRACT THIS!
class Command(BaseCommand):
    help = """

    Grab relevant GeoJSON files to store and interact with the maps layer. We
    do not do this dynamically because the map layers are generated once a week
    and the JSON overlay should not interfere

    """

    def handle(self, *args, **options):
        geojson = {"type": "FeatureCollection",
                "features":[]
                }
        # Select JSON

        cursor = connection.cursor()
        cursor.execute("""
SELECT a.* FROM(
SELECT
	ST_AsGeoJSON(ST_Transform(ST_SetSRID(dashboard_street.line,900913),4326)),
	extract(epoch from avg(dashboard_request.updated_datetime - dashboard_request.requested_datetime)) as average,
	percent_rank() OVER (order by extract(epoch from avg(dashboard_request.updated_datetime - dashboard_request.requested_datetime))) as rank
FROM dashboard_street
LEFT OUTER JOIN
	dashboard_request ON (dashboard_street.id = dashboard_request.street_id)
WHERE
	dashboard_request.status='Closed' AND
	dashboard_request.updated_datetime > dashboard_request.requested_datetime AND
	requested_datetime > '2010-12-31' AND
	dashboard_request.service_code = '024'
GROUP BY dashboard_street.line
) AS a WHERE a.rank > .8
            """)
        rows = cursor.fetchall()

        for row in rows:
            geojson['features'].append({"type": "Feature",
                "geometry": json.loads(row[0]),
                "properties": {
                    "percentile": "%s" % row[2]
                    }})
        f = open('dashboard/static/sidewalk_cleaning.json', 'w')
        f.write(json.dumps(geojson))
        f.close()

        geojson['features'] = []

        cursor.execute("""
SELECT a.* FROM(
SELECT
	ST_AsGeoJSON(ST_Transform(ST_SetSRID(dashboard_street.line,900913),4326)),
	extract(epoch from avg(dashboard_request.updated_datetime - dashboard_request.requested_datetime)) as average,
	percent_rank() OVER (order by extract(epoch from avg(dashboard_request.updated_datetime - dashboard_request.requested_datetime))) as rank,
    dashboard_street.id
FROM dashboard_street
LEFT OUTER JOIN
	dashboard_request ON (dashboard_street.id = dashboard_request.street_id)
WHERE
	dashboard_request.status='Closed' AND
	dashboard_request.updated_datetime > dashboard_request.requested_datetime AND
	requested_datetime > '2010-12-31' AND
	dashboard_request.service_code = '049'
GROUP BY dashboard_street.line, dashboard_street.id
) AS a WHERE a.rank > .8
            """)
        rows = cursor.fetchall()
        for row in rows:
            geojson['features'].append({"type": "Feature",
                "geometry": json.loads(row[0]),
                "properties": {
                    "percentile": "%s" % row[2],
                    "id": "%s" % row[3]
                    }})
        f = open('dashboard/static/graffiti.json', 'w')
        f.write(json.dumps(geojson))
        f.close()


        g = Geography.objects.all().transform()
        geojson['features'] = []

        for shape in g:
            geojson['features'].append({"type": "Feature",
                "geometry": json.loads(shape.geo.simplify(.0003,
                    preserve_topology=True).json),
                "properties": {
                    "neighborhood": shape.name,
                    "id": shape.id
                    }})

        h = open('dashboard/static/neighborhoods.json', 'w')
        h.write(json.dumps(geojson))
        h.close()

########NEW FILE########
__FILENAME__ = import
from osgeo import ogr
from django.contrib.gis.utils import LayerMapping

from dashboard.models import Street

ogr.UseExceptions()
shapefile = ''

source = ogr.Open(shapefile, 1)

city_id_def = ogr.FieldDefn('CITY_ID', ogr.OFTInteger)
layer = source.GetLayer()
layer.CreateField(city_id_def)

for feature in layer:
    feature.SetField('CITY_ID', 1)
    layer.SetFeature(feature)
    print "%s : %s" % (feature.GetField('STREETN_GC'), feature.GetField('CITY_ID'))


mapping = {'line': 'LINESTRING',
        'street_name': 'STREETN_GC',
        'left_low_address': 'LF_FADD',
        'left_high_address': 'LF_TOADD',
        'right_low_address': 'RT_FADD',
        'right_high_address': 'RT_TOADD',
        'city': {'id': 'CITY_ID'}}

lm = LayerMapping(Street, shapefile, mapping)
lm.save(verbose=True)

########NEW FILE########
__FILENAME__ = update_db
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from open311dashboard.dashboard.models import City, Request
from dateutil import parser

from optparse import make_option
import urllib2
import urllib
import datetime as dt
import xml.dom.minidom as dom

ONE_DAY = dt.timedelta(days=1)

def get_time_range(on_day=None):
    if on_day is None:
        on_day = dt.datetime.utcnow() - ONE_DAY

    # End at the begining of on_day; start at the beginning of the previous
    # day.
    end = on_day.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - ONE_DAY

    return (start, end)

def parse_date(date_string):
    new_date = parser.parse(date_string)
    return new_date.strftime("%Y-%m-%d %I:%M")

def validate_dt_value(datetime):
    """
    Verify that the given datetime will not cause problems for the Open311 API.
    For the San Francisco Open311 API, start and end dates are ISO8601 strings,
    but they are expected to be a specific subset.
    """
    if datetime.microsecond != 0:
        raise ValueError('Microseconds on datetime must be 0: %s' % datetime)

    if datetime.tzinfo is not None:
        raise ValueError('Tzinfo on datetime must be None: %s' % datetime)

def get_requests_from_SF(start,end,page,city):
    """
    Retrieve the requests from the San Francisco 311 API within the time range
    specified by the dates start and end.

    Returns a stream containing the content from the API call.
    """

    validate_dt_value(start)
    validate_dt_value(end)

    #url = r'https://open311.sfgov.org/dev/Open311/v2/requests.xml' #dev
    url = city.url
    query_data = {
        'start_date' : start.isoformat() + 'Z',
        'end_date' : end.isoformat() + 'Z',
        'jurisdiction_id' : city.jurisdiction_id,
    }

    if page > 0:
        query_data['page'] = page

    query_str = urllib.urlencode(query_data)
    print url + '?' + query_str

    requests_stream = urllib2.urlopen(url + '?' + query_str)
    return requests_stream

def parse_requests_doc(stream):
    """
    Converts the given file-like object, which presumably contains a service
    requests document, into a list of request dictionaries.
    """

    import xml.dom

    xml_string = stream.read()

    columns = [] #holding columns for a day's worth of incident data
    values = [] #holding values for a day's worth of incident data

    try:
        requests_root = dom.parseString(xml_string).documentElement
    except ExpatError:
        print(xml_string)
        raise

    if len(requests_root.childNodes) < 1:
        return False

    for request_node in requests_root.childNodes:
        indiv_columns_list = []
        indiv_values_list = []

        if request_node.nodeType != xml.dom.Node.ELEMENT_NODE:
            continue

        if request_node.tagName != 'request':
            raise Exception('Unexpected node: %s' % requests_root.toprettyxml())

        for request_attr in request_node.childNodes:
            if request_attr.childNodes:
                if request_attr.tagName.find('datetime') > -1:
                    request_attr.childNodes[0].data = parse_date(request_attr.childNodes[0].data)

                if request_attr.tagName in Request._meta.get_all_field_names():
                    indiv_columns_list.append(request_attr.tagName)
                    indiv_values_list.append(request_attr.childNodes[0].data)

        columns.append(indiv_columns_list)
        values.append(indiv_values_list)
    return (columns,values)

def insert_data(requests, city):
    '''
    Takes the requests tuple, turns it into a dictionary, and saves it to the
    Requests model in django.
    '''

    columns,values = requests

    for i in range(len(values)):

        # Put the key-value pairs into a dictionary and then an arguments list.
        request_dict = dict(zip(columns[i], values[i]))

        # Check if the record already exists.
        try:
            exists = Request.objects.get(service_request_id = request_dict['service_request_id'],
                                        service_code = request_dict['service_code'])
            request_dict['id'] = exists.id
        except:
            pass

        r = Request(**request_dict)

        # Hardcoded for now.
        r.city_id = city.id

        try:
            r.save()
            print "Successfully saved %s" % r.service_request_id
        except ValidationError, e:
            raise CommandError('Request "%s" does not validate correctly\n %s' %
                    (r.service_request_id, e))

def process_requests(start, end, page, city):
    requests_stream = get_requests_from_SF(start, end, page, city)
    requests = parse_requests_doc(requests_stream)

    if requests != False:
        insert_data(requests, city)

        if page != 0:
            page = page+1
            process_requests(start, end, page, city)
    return requests

def handle_open_requests(city):
    url = city.url
    open_requests = Request.objects.all().filter(status__iexact="open")
    length = len(open_requests)
    print "Checking %d tickets for changed status" % length

    for index in xrange(0, length, 10):
        data = []
        for i in xrange(0, 10):
            data.append(open_requests[index + i].service_request_id)

        query_data = {
                'jurisdiction_id': city.jurisdiction_id,
                'service_request_id': ','.join(data)
                }

        query_str = urllib.urlencode(query_data)
        print url + '?' + query_str

        requests_stream = urllib2.urlopen(url + '?' + query_str)
        try:
            print "Parsing open docs"
            requests = parse_requests_doc(requests_stream)
            print "Saving..."
            insert_data(requests)
        except:
            print "Could not process updates."

# At runtime...
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--checkopen', dest='open',
                default=False, help="Boolean to check open tickets"),
            make_option('--default', dest='default',
                default=True, help="Boolean to execute default functionality"),
            )

    help = """Update and seed the database from data retrieved from the API.
    Makes calls one day at a time"""

    def handle(self, *args, **options):
        cities = City.objects.all()

        for city in cities:
            if options['default'] is True:
                if len(args) >= 1:
                    start, end = get_time_range(dt.datetime.strptime(args[0], '%Y-%m-%d'))
                else:
                    start, end = get_time_range()

                if len(args) >= 2:
                    num_days = int(args[1])
                    print(args[1])
                else:
                    num_days = 1

                if city.paginated:
                    page = 1
                else:
                    page = False

                for _ in xrange(num_days):
                    requests = process_requests(start, end, page, city)

                    start -= ONE_DAY
                    end -= ONE_DAY

                    print start

            if options['open'] is True:
                handle_open_requests()



########NEW FILE########
__FILENAME__ = utilities
import datetime as dt
from dateutil import parser

ONE_DAY = dt.timedelta(days=1)

def get_time_range(on_day=None):
    """
    Calculate a return a tuple of datetimes that are exactly 24
    hours apart, from midnight on the day passed in to the 
    midnight prior. If the passed in value is None, then use
    datetime.utcnow() by default.
    """

    # ensure that on_day is defaulted to the previous day
    if on_day is None:
        on_day = dt.datetime.utcnow() - ONE_DAY

    # End at the begining of on_day; start at the beginning of the previous
    # day relative to on_day.
    end = on_day.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - ONE_DAY

    # return tuple of start and end
    return (start, end)

def transform_date(date_string):
    """ 
    All Open311 date/time fields must be formatted in a common 
    subset of ISO 8601 as per the w3 note. Timezone information 
    (either Z meaning UTC, or an HH:MM offset from UTC) must be included.
    This method parses the Open311 date and transforms it into a simpler
    format and returns a string formatted as YYYY-MM-DD HH:MM.
    """

    new_date = parser.parse(date_string)
    return new_date.strftime("%Y-%m-%d %I:%M")


# TODO:
# Why is this test done every time? Why can't it be a unit test?
# If microsends are non-zero and tzinfo is not None the first time 
# then why would it ever change?
# The comments indicate that this is for the SF Open 311 API, is this
# really SF specific or should it be done for every endpoint
def validate_dt_value(datetime):
    """
    Verify that the given datetime will not cause problems for the Open311 API.
    For the San Francisco Open311 API, start and end dates are ISO8601 strings,
    but they are expected to be a specific subset.
    """

    if datetime.microsecond != 0:
        raise ValueError('Microseconds on datetime must be 0: %s' % datetime)

    if datetime.tzinfo is not None:
        raise ValueError('Tzinfo on datetime must be None: %s' % datetime)



########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance as D
from open311dashboard.settings import ENABLE_GEO

class Request(models.Model):
    """

    The actual meat-n-potatoes of the 311 dashboard, all the data.
    Implementations are different so most of these fields are optional.

    Optional: PostGIS component set in settings.py

    """
    service_request_id = models.CharField(max_length=200)
    status = models.CharField(max_length=10)
    status_notes = models.TextField(blank=True, null=True)
    service_name = models.CharField(max_length=100)
    service_code = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    agency_responsible = models.CharField(max_length=255, blank=True, null=True)
    service_notice = models.CharField(max_length=255, blank=True, null=True)
    requested_datetime = models.DateTimeField()
    updated_datetime = models.DateTimeField(null=True, blank=True)
    expected_datetime = models.DateTimeField(null=True, blank=True)
    address = models.CharField(max_length=255)
    address_id = models.IntegerField(blank=True, null=True)
    zipcode = models.IntegerField(blank=True, null=True)
    lat = models.FloatField()
    long = models.FloatField()
    media_url = models.URLField(blank=True, null=True)

    city = models.ForeignKey('City')

    def get_service_name(self):
      return self.service_name.replace('_', ' ')


    # Super top secret geographic data.
    if ENABLE_GEO is True:
        geo_point = models.PointField(srid=900913, null=True)
        street = models.ForeignKey('Street', null=True)
        objects = models.GeoManager()

        def save(self):
            if (float(self.long) != 0.0 and float(self.lat) != 0.0):
                # Save the geo_point.
                point = Point(float(self.long), float(self.lat), srid=4326)
                point.transform(900913)

                self.geo_point = point

                # Lookup the nearest street
                street = Street.objects.filter(line__dwithin=(point, D(m=100))) \
                        .distance(point).order_by('distance')[:1]

                if len(street) > 0:
                    self.street = street[0]

            super(Request, self).save()

# class Service(models.Model):
    """

    In a perfect world, this would be related to each Request but separate
    implementations are, again, different.

    """
    # service_code = models.CharField(max_length=100)
    # metadata = models.CharField(max_length=100)
    # type = models.CharField(max_length=50)
    # keywords = models.TextField(blank=True, null=True)
    # group = models.CharField(max_length=100)
    # service_name = models.CharField(max_length=100)
    # description = models.TextField()

    # city = models.ForeignKey('City')
    # street = models.ForeignKey('Street')

class City(models.Model):
    """

    Give an ID to each city so everything can relate.

    """
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=50)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255)
    jurisdiction_id = models.CharField(max_length=100)
    paginated = models.BooleanField()

    def natural_key(self):
        return self.name

if ENABLE_GEO is True:
    class Geography(models.Model):
        """

        You can import any geographical shapes you want here and associate them
        with a city.

        """
        name = models.CharField(max_length=25)
        geo = models.MultiPolygonField(srid=900913)

        city = models.ForeignKey('City')
        #geo_type = models.ForeignKey('GeographyType')

        objects = models.GeoManager()

        def __unicode__(self):
            return self.name

        def get_absolute_url(self):
            return "/neighborhood/%i/" %  self.id

    # class GeographyType(models.Model):
        """

        Ex: Neighborhood, Congressional Districts...

        """
        # name = models.CharField(max_length=25)

        # Thank @ravoreyer for recommending this.
        # city = models.ForeignKey('City')

    class Street(models.Model):
        """

        Street centerline data.

        """
        street_name = models.CharField(max_length=100)
        line = models.LineStringField(srid=900913)
        city = models.ForeignKey("City")

        left_low_address = models.IntegerField(default=0)
        left_high_address = models.IntegerField(default=0)
        right_low_address = models.IntegerField(default=0)
        right_high_address = models.IntegerField(default=0)

        objects = models.GeoManager()

        def __unicode__(self):
            return self.street_name

        def natural_key(self):
            return self.street_name

        def get_absolute_url(self):
            return "/street/%i/" % self.id

########NEW FILE########
__FILENAME__ = bounding_box
def create_bounding_box(points):
  #initialize
  lon_init = points[0]['lon']
  lat_init = points[0]['lat']
  
  minLon = lon_init
  maxLon = lon_init
  minLat = lat_init
  maxLat = lat_init
  
  for i in xrange(1,len(points)):
    if minLon > points[i]['lon']:
      minLon = points[i]['lon']
    if maxLon < points[i]['lon']:
      maxLon = points[i]['lon']
    if minLat > points[i]['lat']:
      minLat = points[i]['lat']
    if maxLat < points[i]['lat']:
      maxLat = points[i]['lat']
  
  bounding_box = [{'lat':minLat,'lon':minLon},{'lat':maxLat,'lon':maxLon}]
  print bounding_box
  return bounding_box

if __name__ == 'main':
  #Create array of test points
  points = [{'lat': 37.77017,'lon':-122.41996},{'lat': 37.77559,'lon':-122.41516},{'lat':37.77858,'lon':-122.42614}]
  create_bounding_box(points)
########NEW FILE########
__FILENAME__ = calculate_centroid
from sys import argv
import urllib
import json as simplejson
#2-D approximation
def compute_area_of_polygon(polygon_points):
  area = 0
  num_of_vertices = len(polygon_points)
  j = num_of_vertices - 1
  
  for i in xrange(num_of_vertices):
    point1 = polygon_points[i]
    point2 = polygon_points[j]
        
    area = area + point1[0]*point2[1]
    area = area - point1[1]*point2[0]
    
    j = i
  
  area = .5 * area
  
  return area

def compute_centroid(polygon_points):
  num_of_vertices = len(polygon_points)
  j = num_of_vertices - 1
  x = 0
  y = 0
  
  for i in xrange(num_of_vertices):
    point1 = polygon_points[i]
    point2 = polygon_points[j]

    diff = point1[0]*point2[1] - point2[0]*point1[1]
    
    x = x + diff * (point1[0]+point2[0])
    y = y + diff * (point1[1]+point2[1])
    
    j = i
    
  factor = 6 * compute_area_of_polygon(polygon_points)
  
  centroid = [x/factor,y/factor]

  print 'The centroid of the polygon is', centroid

  return centroid

if __name__ == '__main__':
  script,input_file = argv
  
  geojson_url = input_file
  geojson = simplejson.load(urllib.urlopen(geojson_url))
  
  for i in xrange(len(geojson['features'])):
    print i
    if len(geojson['features'][i]['geometry']['coordinates'][0]) > 1:
      polygon_points = geojson['features'][i]['geometry']['coordinates'][0]
    else:
      polygon_points = geojson['features'][i]['geometry']['coordinates'][0][0]

    compute_centroid(polygon_points)
  
  


########NEW FILE########
__FILENAME__ = extract_and_upload
import os
import sqlite3

import boto
import sys
from boto.s3.key import Key

#Use this if you want to use the create_bucket method
#from boto import s3

def percent_cb(complete, total):
  sys.stdout.write('.')
  sys.stdout.flush()

def extract_tiles():
  """
  Shoutout to @rosskarchner: https://gist.github.com/837851
  Extracting images out of mbtiles. Creating folders and filenames.
  Works with mbtiles exported out of TileMill 0.4.2.
  """

  #Connect to the database
  connection = sqlite3.connect('census_blocks.mbtiles')
  
  #Get everything out of the flat file
  pieces = connection.execute('select * from tiles').fetchall()
  
  for piece in pieces:
    #the image is a png
    zoom_level, row, column, image = piece
    
    try: 
      os.makedirs('%s/%s/' % (zoom_level,row))
    except:
      pass
    tile = open('%s/%s/%s.png' % (zoom_level, row, column), 'wb')
    tile.write(image)
    tile.close()
  
  if to_upload:
    upload_to_s3()

def upload_to_s3():
  """
  Assists you in uploading a set of directories/files to S3. Assumes that your S3 bucket
  has already been created. Use the boto's create_bucket method if you don't have an existing bucket.
  """
  AWS_ACCESS_KEY_ID = 'Your AWS Access Key ID'
  AWS_SECRET_ACCESS_KEY = 'Your AWS Secret Access Key'
  
  #This is for making an extremely unique bucket name.
  #bucket_name = AWS_ACCESS_KEY_ID.lower() + 'Your desired bucket name'
  
  bucket_name = 'Your existing bucket name'
  
  #We connect!
  conn = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)
  
  #Use this if you want to create a bucket
  #bucket = conn.create_bucket(bucket_name,location=s3.connection.Location.DEFAULT)
  
  #Connect to our existing bucket
  bucket = conn.get_bucket(bucket_name)
  
  #the base directory
  directory = 'base-directory'
  
  k = Key(bucket)
  
  for root, dirs, files in os.walk(directory):
    for f in files:
      print 'Uploading %s/%s to Amazon bucket %s' % (root, f, bucket_name)
      
      file_name = root + '/' + f
      
      k.key = file_name
      k.set_contents_from_filename(file_name,cb=percent_cb,num_cb=10)

if __name__ == '__main__':
  """
    Pass is in Boolean variable on the command line to specify whether you want to upload your tiles to Amazon S3.
    to_upload is a Boolean variable.
  """
  script,to_upload = argv
  extract_tiles()
  

########NEW FILE########
__FILENAME__ = extract_tiles
import os
import sqlite3

mbtiles_filename = 'filename.mbtiles'

def extract_tiles():
  """
  Shoutout to @rosskarchner: https://gist.github.com/837851
  Extracting images out of mbtiles. Creating folders and filenames.
  Works with mbtiles exported out of TileMill v0.4.2.
  """

  #Connect to the database
  connection = sqlite3.connect(mbtiles_filename)
  
  #Get everything out of the flat file
  pieces = connection.execute('select * from tiles').fetchall()
  
  for piece in pieces:
    #the image is a png
    zoom_level, row, column, image = piece
    
    try: 
      os.makedirs('%s/%s/' % (zoom_level,row))
    except:
      pass
    tile = open('%s/%s/%s.png' % (zoom_level, row, column), 'wb')
    tile.write(image)
    tile.close()

extract_tiles()
  
  

########NEW FILE########
__FILENAME__ = heatmap_blocks
import urllib
import json as simplejson
import math
import pprint

service_requests_url = 'input/service_requests.json'
blocks_url = 'input/sf_blocks.json'

#def compute_rect_bounds():

def inside_rect_bounds(polygon_bounds,request_location):
  
  #initialize
  lon_init = polygon_bounds[0][0][0]
  lat_init = polygon_bounds[0][0][1]
  
  minLon = lon_init
  maxLon = lon_init
  minLat = lat_init
  maxLat = lat_init
  
  request_lat = request_location[0]
  request_lon = request_location[1]
  
  for i in xrange(1,len(polygon_bounds[0])):
    if minLon > polygon_bounds[0][i][0]:
      minLon = polygon_bounds[0][i][0]
    if maxLon < polygon_bounds[0][i][0]:
      maxLon = polygon_bounds[0][i][0]
    if minLat > polygon_bounds[0][i][1]:
      minLat = polygon_bounds[0][i][1]
    if maxLat < polygon_bounds[0][i][1]:
      maxLat = polygon_bounds[0][i][1]
  
  #rect_bounds = [minLon,maxLon,minLat,maxLat]
  if request_lat >= minLat and request_lat <= maxLat and request_lon >= minLon and request_lon <= maxLon:
    return True
  else:
    return False

def inside_polygon(polygon_bounds,request_location):
  #polygon_bounds is an array
  #request_location is an array, lat/long
  request_lat = request_location[0]
  request_lon = request_location[1]
  
  vertices_count = len(polygon_bounds[0])
  inside = False
  #i = 0
  j = vertices_count - 1
  
  if inside_rect_bounds(polygon_bounds,request_location) == False:
    return False
  else:
    for i in xrange(vertices_count):
      vertexA = polygon_bounds[0][i]
      vertexB = polygon_bounds[0][j]
      
      if (vertexA[0] < request_lon and vertexB[0] >= request_lon) or (vertexB[0] < request_lon and vertexA[0] >= request_lon):
        if vertexA[1] + (((request_lon - vertexA[0]) / (vertexB[0] - vertexA[0])) * (vertexB[1] - vertexA[1])) < request_lat:
          inside = not inside
      j = i
    return inside

#load in data
service_requests = simplejson.load(urllib.urlopen(service_requests_url))
blocks = simplejson.load(urllib.urlopen(blocks_url))

#block_totals = [] #maps to 7386 blocks
block_totals = [0]*len(blocks["features"])

for i in xrange(len(service_requests["rows"])):
  print i
  request_lat = service_requests["rows"][i]["value"]["lat"]
  request_lon = service_requests["rows"][i]["value"]["long"]
  request_location = [float(request_lat),float(request_lon)]
  
  #print request_location
  
  if math.fabs(request_location[0]) != 0 or math.fabs(request_location[1]) != 0:
    for j in xrange(len(blocks["features"])):
      polygon_bounds = blocks["features"][j]["geometry"]["coordinates"]
      
      if inside_polygon(polygon_bounds,request_location) == True:
        block_totals[j] = block_totals[j] + 1
      else:
        continue
  #print block_totals

print 'block_totals: ', block_totals

for i in xrange(len(block_totals)):
  blocks["features"][i]["properties"]["count"] = block_totals[i]
  
f = open('output/block_with_counts.json','w')
simplejson.dump(blocks,f)
f.close()
########NEW FILE########
__FILENAME__ = heatmap_blocks_amazon
#works!
import urllib
import json as simplejson
import math
import pprint
import psycopg2 as pg

service_requests_url = 'input/service_requests.json'
blocks_url = 'input/sf_blocks.json'

def connect_with_amazon(**kwargs):
  conn = pg.connect(**kwargs)
  cursor = conn.cursor()
  cursor.execute("""select lat, long from dashboard_request where lat > 0 and
                    requested_datetime > '12-31-2010'""")

  return cursor.fetchall() #returns a list
#def compute_rect_bounds():

def inside_rect_bounds(polygon_bounds,request_location):
  
  #initialize
  lon_init = polygon_bounds[0][0][0]
  lat_init = polygon_bounds[0][0][1]
  
  minLon = lon_init
  maxLon = lon_init
  minLat = lat_init
  maxLat = lat_init
  
  request_lat = request_location[0]
  request_lon = request_location[1]
  
  for i in xrange(1,len(polygon_bounds[0])):
    if minLon > polygon_bounds[0][i][0]:
      minLon = polygon_bounds[0][i][0]
    if maxLon < polygon_bounds[0][i][0]:
      maxLon = polygon_bounds[0][i][0]
    if minLat > polygon_bounds[0][i][1]:
      minLat = polygon_bounds[0][i][1]
    if maxLat < polygon_bounds[0][i][1]:
      maxLat = polygon_bounds[0][i][1]
  
  #rect_bounds = [minLon,maxLon,minLat,maxLat]
  if request_lat >= minLat and request_lat <= maxLat and request_lon >= minLon and request_lon <= maxLon:
    return True
  else:
    return False

def inside_polygon(polygon_bounds,request_location):
  #polygon_bounds is an array
  #request_location is an array, lat/long
  request_lat = request_location[0]
  request_lon = request_location[1]
  
  vertices_count = len(polygon_bounds[0])
  inside = False
  #i = 0
  j = vertices_count - 1
  
  if inside_rect_bounds(polygon_bounds,request_location) == False:
    return False
  else:
    for i in xrange(vertices_count):
      vertexA = polygon_bounds[0][i]
      vertexB = polygon_bounds[0][j]
      
      if (vertexA[0] < request_lon and vertexB[0] >= request_lon) or (vertexB[0] < request_lon and vertexA[0] >= request_lon):
        if vertexA[1] + (((request_lon - vertexA[0]) / (vertexB[0] - vertexA[0])) * (vertexB[1] - vertexA[1])) < request_lat:
          inside = not inside
      j = i
    return inside

#load in data
#service_requests = simplejson.load(urllib.urlopen(service_requests_url))
service_requests = connect_with_amazon(host='', database='', user='',password='')
print service_requests[0][0]

blocks = simplejson.load(urllib.urlopen(blocks_url))

#block_totals = [] #maps to 7386 blocks
block_totals = [0]*len(blocks["features"])

for i in xrange(len(service_requests)):
  print i
  request_lat = service_requests[i][0]
  print request_lat
  request_lon = service_requests[i][1]
  request_location = [float(request_lat),float(request_lon)]
  
  #print request_location
  
  if math.fabs(request_location[0]) != 0 or math.fabs(request_location[1]) != 0:
    for j in xrange(len(blocks["features"])):
      polygon_bounds = blocks["features"][j]["geometry"]["coordinates"]
      
      if inside_polygon(polygon_bounds,request_location) == True:
        block_totals[j] = block_totals[j] + 1
      else:
        continue
  #print block_totals

print 'block_totals: ', block_totals

for i in xrange(len(block_totals)):
  blocks["features"][i]["properties"]["count"] = block_totals[i]
  
f = open('output/block_with_counts_pg.json','w')
simplejson.dump(blocks,f)
f.close()

########NEW FILE########
__FILENAME__ = nearest_street
#!/usr/bin/python

import urllib
import json as simplejson
import pprint
import math

service_requests_url = 'input/service_requests.json'
centerlines_url = 'input/centerlines.json'

def lat_long_to_x_y(lat,lng):
    """Returns an array, a lng/lat pair that has been converted to x and y"""
    pair = []
    sinLat = math.sin((lat*math.pi)/180.0)

    x = ((lng+180.0)/360.0)
    y = (.5 - math.log((1.0 + sinLat)/(1.0 - sinLat)) / (4.0*math.pi))

    pair.append(x)
    pair.append(y)

    return pair

"""
Duplicating function: to be fixed later
"""
def lat_long_to_x_y_list(lng_lat):
    pair = []
    sinLat = math.sin((lng_lat[1]*math.pi)/180.0)

    x = ((lng_lat[0]+180.0)/360.0)
    y = (.5 - math.log((1.0 + sinLat)/(1.0 - sinLat)) / (4.0*math.pi))

    pair.append(x)
    pair.append(y)
    #print(lng_lat[1], lng_lat[0]);
    return pair

def dot_product(v1,v2):
    """
    Take the dot product of two vectors; v1 and v2 are arrays.
    """
    return v1[0] * v2[0] + v1[1] * v2[1]

"""
Optimizations
TODO: Coarse Grid
Precompute everything for a given segment, save time by computing information about a segment once, instead of everytime you use a segment
Can take out square roots
"""
def compute_distance(incident_x_y, segment_start, segment_end):
    deltaX_btwn_endpoints = segment_end[0] - segment_start[0]
    deltaY_btwn_endpoints = segment_end[1] - segment_start[1]

    segment_deltas = [deltaX_btwn_endpoints,deltaY_btwn_endpoints]

    deltaX_btwn_incident_and_segment_start = incident_x_y[0] - segment_start[0]
    deltaY_btwn_incident_and_segment_start = incident_x_y[1] - segment_start[1]

    incident_start_deltas = [deltaX_btwn_incident_and_segment_start, deltaY_btwn_incident_and_segment_start]

    """
    t is a parameter of the line segment. We compute the value of t, where the incident point orthogonally projects to the extended line segment.
    If t is less than 0, it projects before the startpoint. If t is greater than 1, it projects after the endpoint. Otherwise, it projects interior to
    the line segment.
    """
    t = dot_product(segment_deltas,incident_start_deltas)

    if t <= 0:
        #startpoint is closest to incident point
        return math.sqrt(dot_product(incident_start_deltas, incident_start_deltas))
        #return dot_product(incident_start_deltas, incident_start_deltas)

    squared_length_of_segment_deltas = dot_product(segment_deltas,segment_deltas)

    if t >= squared_length_of_segment_deltas:
        #endpoint is closest to incident point

        """
        compute incident_end_deltas
        """
        deltaX_btwn_incident_and_segment_end = incident_x_y[0] - segment_end[0]
        deltaY_btwn_incident_and_segment_end = incident_x_y[1] - segment_end[1]

        incident_end_deltas = [deltaX_btwn_incident_and_segment_end,deltaY_btwn_incident_and_segment_end]

        return math.sqrt(dot_product(incident_end_deltas,incident_end_deltas))
        #return dot_product(incident_end_deltas,incident_end_deltas)
    """
    closest point is interior to segment
    """
    interior_closest = dot_product(incident_start_deltas,incident_start_deltas) - ((t*t)/squared_length_of_segment_deltas)
    if interior_closest < 0:
        return 0
    else:
        return math.sqrt(interior_closest)
    #return dot_product(incident_start_deltas,incident_start_deltas) - ((t*t)/squared_length_of_segment_deltas)
    
    
def process_data():
    service_requests = simplejson.load(urllib.urlopen(service_requests_url))
    centerlines = simplejson.load(urllib.urlopen(centerlines_url))
    #print(len(centerlines["features"]))

    service_requests_x_y = []
    month_list = []
    request_list = []

    for i in range(len(service_requests["rows"])):
        lat = float(service_requests["rows"][i]["value"]["lat"])
        lng = float(service_requests["rows"][i]["value"]["long"])

        if lat != 0.0 and lng != 0.0:
            service_requests_x_y.append(lat_long_to_x_y(lat,lng))

    line_segments = []

    for i in range(len(centerlines["features"])):
        sub_segments = centerlines["features"][i]["geometry"]["coordinates"]
        line_segments.append(sub_segments)
    
    line_segments_x_y = []
    for i in range(len(line_segments)):
        line_segments_x_y.append(map(lat_long_to_x_y_list, line_segments[i]))

    street_index = 0
    response_time_average = [0] * len(line_segments_x_y)
    response_time_sum = [0] * len(line_segments_x_y)
    street_count = [0] * len(line_segments_x_y)

    for i in range(len(service_requests_x_y)-41000):
        print i
        distance = 200;
        for j in range(len(line_segments_x_y)):
            for k in range(len(line_segments_x_y[j])-1):
                computed_distance = compute_distance(service_requests_x_y[i],line_segments_x_y[j][k],line_segments_x_y[j][k+1])
                if (distance > computed_distance):
                    distance = computed_distance
                    street_index = j


        #requests_by_street[street_index].append(request_list[i])
        
        street_count[street_index] = street_count[street_index] + 1
    print street_count
    max_count_list = []
    
    maximum = 0

    individual_counts = []
    
    maximum = max(street_count)
    normalized_street_scores = map(lambda x: 100*math.log((1024/maximum)*x,2) if x > 0 else x,street_count)
    #sub_centerlines = {"type": "FeatureCollection","features":[]}
    for i in range(len(centerlines["features"])):
        centerlines["features"][i]["properties"]["score"] = street_count[i] #either or
        #centerlines["features"][i]["properties"]["score"] = normalized_street_scores[i]

    #print "sub_centerlines length: ",len(sub_centerlines["features"])
        

    #f = open('output/scored_centerlines_sub_final.json','w')
    #simplejson.dump(sub_centerlines,f)
    #f.close()
    f2 = open('output/scored_centerlines_final.json','w')
    simplejson.dump(centerlines,f2)
    f2.close()
process_data()
########NEW FILE########
__FILENAME__ = upload_to_s3
#Authors: Michael Lawrence Evans + Joanne Cheng
import os
import sys
import boto
from boto.s3.key import Key

#Use this if you want to use the create_bucket method
#from boto import s3

def percent_cb(complete, total):
  """Command line updates."""
  sys.stdout.write('.')
  sys.stdout.flush()

def upload_to_s3():
  AWS_ACCESS_KEY_ID = 'Your AWS Access Key ID'
  AWS_SECRET_ACCESS_KEY = 'Your AWS Secret Access Key'
  
  #This is for making an extremely unique bucket name.
  #bucket_name = AWS_ACCESS_KEY_ID.lower() + 'Your desired bucket name'
  
  bucket_name = 'Your existing bucket name'
  
  #We connect!
  conn = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)
  
  #Use this if you want to create a bucket
  #bucket = conn.create_bucket(bucket_name,location=s3.connection.Location.DEFAULT)
  
  #Connect to our existing bucket
  bucket = conn.get_bucket(bucket_name)
  
  #the base directory
  directory = 'base-directory'
  
  k = Key(bucket)
  
  for root, dirs, files in os.walk(directory):
    for f in files:
      print 'Uploading %s/%s to Amazon bucket %s' % (root, f, bucket_name) #debugging
      
      file_name = root + '/' + f
      
      k.key = file_name
      k.set_contents_from_filename(file_name,cb=percent_cb,num_cb=10)

upload_to_s3()
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

import json
import random

class IndexTest(TestCase):
    """Test the index view and related json"""
    fixtures = ['test.json']

    def test_success(self):
        """Test that the index works"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_template(self):
        """Test that the correct templates are being rendered"""
        response = self.client.get("/")
        self.assertTemplateUsed(response, 'index.html')
        self.assertTemplateUsed(response, 'base/main.html')

    def test_api_success(self):
        """Test the JSON API"""
        rand = random.randint(1,5)
        response = self.client.get("/api/home/%s.json" % rand)

        self.assertEqual(response.status_code, 200)

    def test_api_valid(self):
        """Test that the JSON is valid"""
        rand = random.randint(1,5)
        response = self.client.get("/api/home/%s.json" % rand)
        data = json.loads(response.content)

        self.assertIsInstance(data, dict)

class NeighborhoodTest(TestCase):
    """Test the neighborhood views"""
    fixtures = ['test.json']

    def test_success_list(self):
        """Check to make sure the neighborhood list is working"""
        response = self.client.get("/neighborhood/")
        self.assertEqual(response.status_code, 200)

    def test_success_detail(self):
        """Check to make sure neighborhood detail is working"""
        rand = random.randint(1, 5)
        response = self.client.get("/neighborhood/%s/" % rand)

        self.assertEqual(response.status_code, 200)

    def test_success_api(self):
        """Check to make sure the API works"""
        rand = random.randint(1, 5)
        response = self.client.get("/neighborhood/%s.json" % rand)
        self.assertEqual(response.status_code, 200)

    def test_template_list(self):
        """Check the template that is rendered for the neighborhood list."""
        response = self.client.get("/neighborhood/")
        self.assertTemplateUsed(response, "neighborhood_list.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_template_detail(self):
        """Check the template that is rendered for the neighborhood detail."""
        rand = random.randint(1, 5)
        response = self.client.get("/neighborhood/%s/" % rand)

        self.assertTemplateUsed(response, "geo_detail.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_redirect_list(self):
        """Check the neighborhood list redirect"""
        response = self.client.get("/neighborhood")
        self.assertEqual(response.status_code, 301)

    def test_redirect_detail(self):
        """Check the neighborhood detail redirect"""
        rand = random.randint(1, 5)
        response = self.client.get("/neighborhood/%s" % rand)
        self.assertEqual(response.status_code, 301)

    def test_valid_api(self):
        """Make sure the neighborhood detail api is working"""
        rand = random.randint(1, 5)
        response = self.client.get("/neighborhood/%s.json" % rand)
        data = json.loads(response.content)

        self.assertIsInstance(data, list)

class StreetTest(TestCase):
    """Test the street pages"""
    fixtures = ['test.json']
    def test_success_list(self):
        """Check that the street list works"""
        response = self.client.get("/street/")
        self.assertEqual(response.status_code, 200)

    def test_success_detail(self):
        """Check that the street detail is working"""
        rand = random.randint(2, 50)
        response = self.client.get("/street/%s/" % rand)
        self.assertEqual(response.status_code, 200)

    def test_success_api(self):
        """Check that the street api is working"""
        rand = random.randint(2, 50)
        response = self.client.get("/street/%s.json" % rand)
        self.assertEqual(response.status_code, 200)

    def test_template_list(self):
        """Check the street list templates"""
        response = self.client.get("/street/")
        self.assertTemplateUsed(response, "street_list.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_template_detail(self):
        """Check the street detail templates"""
        rand = random.randint(2, 50)
        response = self.client.get("/street/%s/" % rand)
        self.assertTemplateUsed(response, "geo_detail.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_redirect_list(self):
        """Check street list redirect"""
        response = self.client.get("/street")
        self.assertEqual(response.status_code, 301)

    def test_redirect_detail(self):
        """Check street detail redirect"""
        rand = random.randint(2, 50)
        response = self.client.get("/street/%s" % rand)
        self.assertEqual(response.status_code, 301)

    def test_valid_api(self):
        """Check that the API is valid"""
        rand = random.randint(2, 50)
        response = self.client.get("/street/%s.json" % rand)
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

class SearchTest(TestCase):
    """Test the search"""

    def test_success_search(self):
        """Check for success rendering the status page"""
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)

    def test_template_search(self):
        """Check the template rendered on the search page"""
        response = self.client.get("/search/")
        self.assertTemplateUsed(response, "search.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_redirect_search(self):
        """Check the redirect on the search page"""
        response = self.client.get("/search")
        self.assertEqual(response.status_code, 301)

class MapTest(TestCase):
    def test_success_map(self):
        """Check that the map page works"""
        response = self.client.get("/map/")
        self.assertEqual(response.status_code, 200)

    def test_template_map(self):
        """Check the templates rendered on the map page"""
        response = self.client.get("/map/")
        self.assertTemplateUsed(response, "map.html")
        self.assertTemplateUsed(response, "base/main.html")

    def test_redirect_map(self):
        """Check that the redirect works on the map page"""
        response = self.client.get("/map")
        self.assertEqual(response.status_code, 301)

########NEW FILE########
__FILENAME__ = unit_tests
import datetime
import unittest
from dateutil import parser
from unittest import TestCase, main
from management.commands.utilities import *

class _TestUpdateDb(unittest.TestCase):

    def test_validate_dt_value(self):
        # test that a "proper" datetime does not throw exception
        test_time = datetime.datetime(2012, 3, 14, 0, 0, 0)
        result = validate_dt_value(test_time)
        self.assertEqual(None, result) 

        # test that ValueError is raised if microseconds is non-zero
        with self.assertRaises(ValueError) as context_manager:
            test_time = datetime.datetime(2012, 3, 14, 0, 0, 0, 100)
            validate_dt_value(test_time)

        ex = context_manager.exception
        self.assertEqual('Microseconds on datetime must ' \
            'be 0: 2012-03-14 00:00:00.000100', ex.message)

        # test that ValueError is raised if tzinfo is not None 
        with self.assertRaises(ValueError) as context_manager:
            test_time = parser.parse("2012-02-21T10:57:47-05:00") 
            validate_dt_value(test_time)

        ex = context_manager.exception
        self.assertEqual('Tzinfo on datetime must be None: ' \
            '2012-02-21 10:57:47-05:00', ex.message)

    def test_transform_date(self):
        # transform an ISO 8601 string that represents 2/21/2012 at 10:57:47
        # with a 5 hour offset 
        d = transform_date("2012-02-21T10:57:47-05:00")
        # expect to recieve a string formatted with just YYYY-MM-DD HH:MM
        self.assertEqual("2012-02-21 10:57", d) 
         
    def test_get_time_range(self):
       # if we create a start date of 3/14
       start_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # our expected start and end dates are as follows
       expected_start_date = start_date - datetime.timedelta(days=1)
       expected_end_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # call the method and assert we get what we expect
       start, end = get_time_range(start_date)
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

       # same as above but make sure that a start_date passed in
       # as NOT midnight gets set to midnight 
       start_date = datetime.datetime(2012, 3, 14, 1, 30, 30) 
       # our expected start and end dates are as follows
       expected_start_date = start_date.replace(hour=0, minute=0, second=0, 
           microsecond=0) - datetime.timedelta(days=1)
       expected_end_date = datetime.datetime(2012, 3, 14, 0, 0, 0) 
       # call the method and assert we get what we expect
       start, end = get_time_range(start_date)
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

       # same as above but pass None and check that default
       # behavior works as intended 
       # our expected start and end dates are as follows
       expected_end_date = datetime.datetime.utcnow().replace(hour=0, minute=0,
           second=0, microsecond=0) - datetime.timedelta(days=1)
       expected_start_date = expected_end_date - datetime.timedelta(days=1)
       # call the method and assert we get what we expect
       start, end = get_time_range()
       self.assertEqual(end, expected_end_date) 
       self.assertEqual(start, expected_start_date) 

if __name__ == '__main__':
	suite = unittest.TestLoader().loadTestsFromTestCase(_TestUpdateDb)
	unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = utils
import datetime

import qsstats
from io import StringIO
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import smart_unicode
from django.utils.simplejson import dumps
from django.contrib.gis.db.models.fields import GeometryField
from django.utils import simplejson
from django.http import HttpResponse
from django.db.models import Count

def run_stats(request_obj, **kwargs):
    """

    Returns stats on a given request set.


    """
    stats = {}


    try:
        # Average response time.
        stats['average_response'] = request_obj.filter(status="Closed") \
            .extra({"average": "avg(updated_datetime - requested_datetime)"}) \
            .values("average")
        stats['average_response'] = stats['average_response'][0]["average"].days

        # Total request count.
        stats['request_count'] = request_obj.count()

        # Request types.
        if kwargs.has_key('request_types') is False:
            stats['request_types'] = request_obj.values('service_name') \
                    .annotate(count=Count('service_name')).order_by('-count')[:10]

        # Opened requests by day (limit: 30)
        time_delta = datetime.timedelta(days=30)
        latest = request_obj.latest('requested_datetime')
        qss = qsstats.QuerySetStats(request_obj, 'requested_datetime')
        time_series = qss.time_series(latest.requested_datetime - time_delta,
               latest.requested_datetime)
        stats['opened_by_day'] = [t[1] for t in time_series]

        # Open request count.
        stats['open_request_count'] = request_obj.filter(status="Open").count()

        # Closed request count.
        stats['closed_request_count'] = request_obj.filter(status="Closed").count()

        # Recently opened requests.
        if kwargs.has_key('open_requests') is False:
            stats['open_requests'] = request_obj.filter(status="Open") \
                    .order_by('-requested_datetime')[:10]

    except:
      stats['average_response'] = 0
      stats['request_count'] = 0
      stats['request_types'] = []
      stats['open_request_count'] = 0
      stats['closed_request_count'] = 0
      stats['opened_by_day'] = [0]

    # Return
    return stats

def calculate_delta(new, old):
    try:
        delta = int(round(((float(new) / old)-1) * 100))
    except:
        delta = 100

    return delta

# Handle string/date conversion.
def str_to_day(date):
    """Convert a YYYY-MM-DD string to a datetime object"""
    return datetime.datetime.strptime(date, '%Y-%m-%d')

def day_to_str(date):
    """Convert a datetime object into a YYYY-MM-DD string"""
    return datetime.datetime.strftime(date, '%Y-%m-%d')

def date_range(begin, end=None):
    """Returns a tuple of datetimes spanning the given range"""
    if end == None:
        date = str_to_day(begin)
        begin = datetime.datetime.combine(date, datetime.time.min)
        end = datetime.datetime.combine(date, datetime.time.max)
    else:
        begin = str_to_day(begin)
        end = str_to_day(end)

    return (begin, end)

def dt_handler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return None

##
# Taken from http://geodjango-basic-apps.googlecode.com/svn/trunk/projects/alpha_shapes/clustr/shortcuts.py
##
def render_to_geojson(query_set, geom_field=None, mimetype='text/plain', pretty_print=True, exclude=[]):
    '''

    Shortcut to render a GeoJson FeatureCollection from a Django QuerySet.
    Currently computes a bbox and adds a crs member as a sr.org link

    '''
    collection = {}

    # Find the geometry field
    # qs.query._geo_field()

    fields = query_set.model._meta.fields
    geo_fields = [f for f in fields if isinstance(f, GeometryField)]

    #attempt to assign geom_field that was passed in
    if geom_field:
        geo_fieldnames = [x.name for x in geo_fields]
        try:
            geo_field = geo_fields[geo_fieldnames.index(geom_field)]
        except:
            raise Exception('%s is not a valid geometry on this model' % geom_field)
    else:
        geo_field = geo_fields[0] # no support yet for multiple geometry fields

    #remove other geom fields from showing up in attributes
    if len(geo_fields) > 1:
        for gf in geo_fields:
            if gf.name not in exclude: exclude.append(gf.name)
        exclude.remove(geo_field.name)

    # Gather the projection information
    crs = {}
    crs['type'] = "link"
    crs_properties = {}
    crs_properties['href'] = 'http://spatialreference.org/ref/epsg/%s/' % geo_field.srid
    crs_properties['type'] = 'proj4'
    crs['properties'] = crs_properties
    collection['crs'] = crs

    # Build list of features
    features = []
    if query_set:
      for item in query_set:
         feat = {}
         feat['type'] = 'Feature'
         d= item.__dict__.copy()
         g = getattr(item,geo_field.name)
         d.pop(geo_field.name)
         for field in exclude:
             d.pop(field)
         feat['geometry'] = simplejson.loads(g.geojson)
         feat['properties'] = d
         features.append(feat)
    else:
        pass #features.append({'type':'Feature','geometry': {},'properties':{}})

    # Label as FeatureCollection and add Features
    collection['type'] = "FeatureCollection"
    collection['features'] = features

    # Attach extent of all features
    #if query_set:
    #    #collection['bbox'] = [x for x in query_set.extent()]
    #    agg = query_set.unionagg()
    #    collection['bbox'] = [agg.extent]
    #    collection['centroid'] = [agg.point_on_surface.x,agg.point_on_surface.y]

    # Return response
    response = HttpResponse()
    if pretty_print:
        response.write('%s' % simplejson.dumps(collection, indent=1))
    else:
        response.write('%s' % simplejson.dumps(collection))
    response['Content-length'] = str(len(response.content))
    response['Content-Type'] = mimetype
    return response

##
# JSON SERIALIZER FROM:
##
class UnableToSerializeError(Exception):
    """ Error for not implemented classes """
    def __init__(self, value):
        self.value = value
        Exception.__init__(self)

    def __str__(self):
        return repr(self.value)

class JSONSerializer():
    boolean_fields = ['BooleanField', 'NullBooleanField']
    datetime_fields = ['DatetimeField', 'DateField', 'TimeField']
    number_fields = ['IntegerField', 'AutoField', 'DecimalField', 'FloatField', 'PositiveSmallIntegerField']

    def serialize(self, obj, **options):
        self.options = options

        self.stream = options.pop("stream", StringIO())
        self.selectedFields = options.pop("fields", None)
        self.ignoredFields = options.pop("ignored", None)
        self.use_natural_keys = options.pop("use_natural_keys", False)
        self.currentLoc = ''

        self.level = 0

        self.start_serialization()

        self.handle_object(obj)

        self.end_serialization()
        return self.getvalue()

    def get_string_value(self, obj, field):
        """Convert a field's value to a string."""
        return smart_unicode(field.value_to_string(obj))

    def start_serialization(self):
        """Called when serializing of the queryset starts."""
        pass

    def end_serialization(self):
        """Called when serializing of the queryset ends."""
        pass

    def start_array(self):
        """Called when serializing of an array starts."""
        self.stream.write(u'[')
    def end_array(self):
        """Called when serializing of an array ends."""
        self.stream.write(u']')

    def start_object(self):
        """Called when serializing of an object starts."""
        self.stream.write(u'{')

    def end_object(self):
        """Called when serializing of an object ends."""
        self.stream.write(u'}')

    def handle_object(self, object):
        """ Called to handle everything, looks for the correct handling """
        if isinstance(object, dict):
            self.handle_dictionary(object)
        elif isinstance(object, list):
            self.handle_list(object)
        elif isinstance(object, Model):
            self.handle_model(object)
        elif isinstance(object, QuerySet):
            self.handle_queryset(object)
        elif isinstance(object, bool):
            self.handle_simple(object)
        elif isinstance(object, int) or isinstance(object, float) or isinstance(object, long):
            self.handle_simple(object)
        elif isinstance(object, basestring):
            self.handle_simple(object)
        else:
            raise UnableToSerializeError(type(object))

    def handle_dictionary(self, d):
        """Called to handle a Dictionary"""
        i = 0
        self.start_object()
        for key, value in d.iteritems():
            self.currentLoc += key+'.'
            #self.stream.write(unicode(self.currentLoc))
            i += 1
            self.handle_simple(key)
            self.stream.write(u': ')
            self.handle_object(value)
            if i != len(d):
                self.stream.write(u', ')
            self.currentLoc = self.currentLoc[0:(len(self.currentLoc)-len(key)-1)]
        self.end_object()

    def handle_list(self, l):
        """Called to handle a list"""
        self.start_array()

        for value in l:
            self.handle_object(value)
            if l.index(value) != len(l) -1:
                self.stream.write(u', ')

        self.end_array()

    def handle_model(self, mod):
        """Called to handle a django Model"""
        self.start_object()

        for field in mod._meta.local_fields:
            if field.rel is None:
                if self.selectedFields is None or field.attname in self.selectedFields or field.attname:
                    if self.ignoredFields is None or self.currentLoc + field.attname not in self.ignoredFields:
                        self.handle_field(mod, field)
            else:
                if self.selectedFields is None or field.attname[:-3] in self.selectedFields:
                    if self.ignoredFields is None or self.currentLoc + field.attname[:-3] not in self.ignoredFields:
                        self.handle_fk_field(mod, field)
        for field in mod._meta.many_to_many:
            if self.selectedFields is None or field.attname in self.selectedFields:
                if self.ignoredFields is None or self.currentLoc + field.attname not in self.ignoredFields:
                    self.handle_m2m_field(mod, field)
        self.stream.seek(self.stream.tell()-2)
        self.end_object()

    def handle_queryset(self, queryset):
        """Called to handle a django queryset"""
        self.start_array()
        it = 0
        for mod in queryset:
            it += 1
            self.handle_model(mod)
            if queryset.count() != it:
                self.stream.write(u', ')
        self.end_array()

    def handle_field(self, mod, field):
        """Called to handle each individual (non-relational) field on an object."""
        self.handle_simple(field.name)
        if field.get_internal_type() in self.boolean_fields:
            if field.value_to_string(mod) == 'True':
                self.stream.write(u': true')
            elif field.value_to_string(mod) == 'False':
                self.stream.write(u': false')
            else:
                self.stream.write(u': undefined')
        else:
            self.stream.write(u': ')
            self.handle_simple(field.value_to_string(mod))
        self.stream.write(u', ')

    def handle_fk_field(self, mod, field):
        """Called to handle a ForeignKey field."""
        related = getattr(mod, field.name)
        if related is not None:
            if field.rel.field_name == related._meta.pk.name:
                # Related to remote object via primary key
                pk = related._get_pk_val()
            else:
                # Related to remote object via other field
                pk = getattr(related, field.rel.field_name)
            d = {
                    'pk': pk,
                }
            if self.use_natural_keys and hasattr(related, 'natural_key'):
                d.update({'natural_key': related.natural_key()})
            if type(d['pk']) == str and d['pk'].isdigit():
                d.update({'pk': int(d['pk'])})

            self.handle_simple(field.name)
            self.stream.write(u': ')
            self.handle_object(d)
            self.stream.write(u', ')

    def handle_m2m_field(self, mod, field):
        """Called to handle a ManyToManyField."""
        if field.rel.through._meta.auto_created:
            self.handle_simple(field.name)
            self.stream.write(u': ')
            self.start_array()
            hasRelationships = False
            for relobj in getattr(mod, field.name).iterator():
                hasRelationships = True
                pk = relobj._get_pk_val()
                d = {
                        'pk': pk,
                    }
                if self.use_natural_keys and hasattr(relobj, 'natural_key'):
                    d.update({'natural_key': relobj.natural_key()})
                if type(d['pk']) == str and d['pk'].isdigit():
                    d.update({'pk': int(d['pk'])})

                self.handle_simple(d)
                self.stream.write(u', ')
            if hasRelationships:
                self.stream.seek(self.stream.tell()-2)
            self.end_array()
            self.stream.write(u', ')

    def handle_simple(self, simple):
        """ Called to handle values that can be handled via simplejson """
        self.stream.write(unicode(dumps(simple)))

    def getvalue(self):
        """Return the fully serialized object (or None if the output stream is  not seekable).sss """
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

def json_response_from(response):
    jsonSerializer = JSONSerializer()
    return HttpResponse(jsonSerializer.serialize(response, use_natural_keys=True), mimetype='application/json')

########NEW FILE########
__FILENAME__ = views
import datetime
import qsstats
import time
import json
import urllib
import urllib2

from django.template import Context
from django.shortcuts import render, redirect
from django.db.models import Count
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance as D

from dashboard.models import Request, City, Geography, Street
from dashboard.decorators import ApiHandler
from dashboard.utils import str_to_day, day_to_str, \
    date_range, dt_handler, render_to_geojson, run_stats, calculate_delta, \
    json_response_from


def index(request, geography=None, is_json=False):
    """
    Homepage view. Can also return json for the city or neighborhoods.
    """
    if geography is None:
        requests = Request.objects.all()
    else:
        neighborhood = Geography.objects.get(pk=geography)
        requests = Request.objects.filter(geo_point__contained=neighborhood.geo)

    total_open = requests.filter(status="Open").count()
    most_recent = requests.latest('requested_datetime')
    minus_7 = most_recent.requested_datetime-datetime.timedelta(days=7)
    minus_14 = most_recent.requested_datetime-datetime.timedelta(days=14)

    this_week = requests.filter(requested_datetime__range= \
            (minus_7, most_recent.requested_datetime))
    last_week = requests.filter(requested_datetime__range= \
            (minus_14, minus_7))

    this_week_stats = run_stats(this_week, request_types=False,
            open_requests=False)
    last_week_stats = run_stats(last_week, request_types=False,
            open_requests=False)

    # Calculate deltas
    delta = {}
    delta['count'] = calculate_delta(this_week_stats['request_count'],
            last_week_stats['request_count'])
    delta['closed_count'] = calculate_delta( \
            this_week_stats['closed_request_count'],
            last_week_stats['closed_request_count'])
    delta['opened_count'] = calculate_delta( \
            this_week_stats['open_request_count'],
            last_week_stats['open_request_count'])
    delta['time'] = calculate_delta(this_week_stats['average_response'],
            last_week_stats['average_response'])

    # Put everything in a dict so we can do what we want with it.
    c_dict = {
        'open_tickets': total_open,
        'this_week_stats': this_week_stats,
        'last_week_stats': last_week_stats,
        'delta': delta,
    }

    if is_json is False:
        neighborhoods = Geography.objects.all()
        c_dict['neighborhoods'] = neighborhoods
        c_dict['latest'] = most_recent.requested_datetime
        c = Context(c_dict)
        return render(request, 'index.html', c)
    else:
        data = json.dumps(c_dict, True)
        return HttpResponse(data, content_type='application/json')


# Neighborhood specific pages.
def neighborhood_list(request):
    """
    List the neighborhoods.
    """
    neighborhoods = Geography.objects.all()

    c = Context({
        'neighborhoods': neighborhoods
        })

    return render(request, 'neighborhood_list.html', c)


def neighborhood_detail(request, neighborhood_id):
    """

    Show detail for a specific neighborhood. Uses templates/geo_detail.html

    """
    neighborhood = Geography.objects.get(pk=neighborhood_id)
    nearby = Geography.objects.all().distance(neighborhood.geo) \
            .exclude(name=neighborhood.name).order_by('distance')[:5]

    # Get the requests inside the neighborhood, run the stats
    requests = Request.objects.filter(geo_point__contained=neighborhood.geo)
    stats = run_stats(requests)

    title = neighborhood.name

    neighborhood.geo.transform(4326)
    simple_shape = neighborhood.geo.simplify(.0003,
            preserve_topology=True)

    c = Context({
        'title': title,
        'geometry': simple_shape.geojson,
        'centroid': [simple_shape.centroid[0], simple_shape.centroid[1]],
        'extent': simple_shape.extent,
        'stats': stats,
        'nearby': nearby,
        'type': 'neighborhood',
        'id': neighborhood_id
        })

    return render(request, 'geo_detail.html', c)


def neighborhood_detail_json(request, neighborhood_id):
    """

    Download JSON of the requests that built the page. Caution: slow!

    TODO: Speed it up.

    """
    neighborhood = Geography.objects.get(pk=neighborhood_id)
    requests = Request.objects.filter(geo_point__contained=neighborhood.geo)
    return json_response_from(requests)


# Street specific pages.
def street_list(request):
    """

    List the top 10 streets by open service requests.

    """
    streets = Street.objects.filter(request__status="Open") \
            .annotate(count=Count('request__service_request_id')) \
            .order_by('-count')[:10]

    c = Context({
        'top_streets': streets
    })

    return render(request, 'street_list.html', c)


def street_view(request, street_id):
    """
    View details for a specific street. Renders geo_detail.html like
    neighborhood_detail does.
    """
    street = Street.objects.get(pk=street_id)
    nearby = Street.objects.all().distance(street.line) \
            .exclude(street_name=street.street_name).order_by('distance')[:5]
    neighborhood = Geography.objects.all() \
            .distance(street.line).order_by('distance')[:1]

    # Max/min addresses
    addresses = [street.left_low_address, street.left_high_address,
                 street.right_low_address, street.right_high_address]
    addresses.sort()

    title = "%s %i - %i" % (street.street_name, addresses[0], addresses[3])

    # Requests
    requests = Request.objects.filter(street=street_id)
    stats = run_stats(requests)

    street.line.transform(4326)

    c = Context({
        'title': title,
        'geometry': street.line.geojson,
        'centroid': [street.line.centroid[0], street.line.centroid[1]],
        'extent': street.line.extent,
        'stats': stats,
        'nearby': nearby,
        'neighborhood': neighborhood[0],
        'type': 'street',
        'id': street_id
        })

    return render(request, 'geo_detail.html', c)


def street_view_json(request, street_id):
    """

    Download the JSON for the requests that built the page.

    """
    requests = Request.objects.filter(street=street_id)
    return json_response_from(requests)


# Search for an address!
def street_search(request):
    """
    Do a San Francisco specific geocode and then match that against our street
    centerline data.
    """
    query = request.GET.get('q')
    lat = request.GET.get('lat')
    lon = request.GET.get('lng')
    if not query:
        # They haven't searched for anything.
        return render(request, 'search.html')
    elif query and not lat:
        # Lookup the search string with Yahoo!
        url = "http://where.yahooapis.com/geocode"
        params = {"addr": query,
                "line2": "San Francisco, CA",
                "flags": "J",
                "appid": "1I9Jh.3V34HMiBXzxZRYmx.DO1JfVJtKh7uvDTJ4R0dRXnMnswRHXbai1NFdTzvC" }

        query_params = urllib.urlencode(params)
        data = urllib2.urlopen("%s?%s" % (url, query_params)).read()

        print data

        temp_json = json.loads(data)

        if temp_json['ResultSet']['Results'][0]['quality'] > 50:
            lon = temp_json['ResultSet']['Results'][0]["longitude"]
            lat = temp_json['ResultSet']['Results'][0]["latitude"]
        else:
            lat, lon = None, None

    if lat and lon:
        point = Point(float(lon), float(lat))
        point.srid = 4326
        point.transform(900913)
        nearest_street = Street.objects \
                               .filter(line__dwithin=(point, D(m=100))) \
                               .distance(point).order_by('distance')[:1]
        try:
            return redirect(nearest_street[0])
        except IndexError:
            pass
    c = Context({'error': True})
    return render(request, 'search.html', c)


def map(request):
    """
    Simply render the map.

    TODO: Get the centroid and bounding box of the city and set that. (See
    neighborhood_detail and geo_detail.html for how this would look)
    """
    return render(request, 'map.html')

# Admin Pages
@login_required
def admin(request):
    """

    Admin home page. Just list the cities.

    """
    cities = City.objects.all()
    c = Context({'cities': cities})
    return render(request, 'admin/index.html', c)

@login_required
def city_admin(request, shortname=None):
    """

    Administer a specific city (and associated data)

    """
    city = City.objects.get(short_name=shortname)
    geographies = Geography.objects.filter(city=city.id).count()
    streets = Street.objects.filter(city=city.id).count()
    requests = Request.objects.filter(city=city.id).count()

    c = Context({
        'city': city,
        'geographies': geographies,
        'streets': streets,
        'requests': requests
        })

    return render(request, 'admin/city_view.html', c)

@login_required
def city_add(request):
    """

    Add a new city.

    """
    return render(request, 'admin/city_add.html')

# API Views
@ApiHandler
def ticket_days(request, ticket_status="open", start=None, end=None,
                num_days=None):
    '''Returns JSON with the number of opened/closed tickets in a specified
    date range'''

    # If no start or end variables are passed, do the past 30 days. If one is
    # passed, check if num_days and do the past num_days. If num_days isn't
    # passed, just do one day. Else, do the range.
    if start is None and end is None:
        num_days = int(num_days) if num_days is not None else 29

        end = datetime.date.today()
        start = end - datetime.timedelta(days=num_days)
    elif end is not None and num_days is not None:
        num_days = int(num_days) - 1
        end = str_to_day(end)
        start = end - datetime.timedelta(days=num_days)
    elif end is not None and start is None:
        end = str_to_day(end)
        start = end
    else:
        start = str_to_day(start)
        end = str_to_day(end)

    if ticket_status == "open":
        request = Request.objects.filter(status="Open") \
            .filter(requested_datetime__range=date_range(day_to_str(start),
                                                         day_to_str(end)))
        stats = qsstats.QuerySetStats(request, 'requested_datetime')
    elif ticket_status == "closed":
        request = Request.objects.filter(status="Closed")
        stats = qsstats.QuerySetStats(request, 'updated_datetime') \
            .filter(requested_datetime__range=date_range(day_to_str(start),
                                                         day_to_str(end)))
    elif ticket_status == "both":
        request_opened = Request.objects.filter(status="Open") \
            .filter(requested_datetime__range=date_range(day_to_str(start),
                                                         day_to_str(end)))
        stats_opened = qsstats.QuerySetStats(request_opened,
                                             'requested_datetime')

        request_closed = Request.objects.filter(status="Closed") \
            .filter(requested_datetime__range=date_range(day_to_str(start),
                                                         day_to_str(end)))
        stats_closed = qsstats.QuerySetStats(request_closed,
                                             'updated_datetime')

    data = []

    try:
        raw_data = stats.time_series(start, end)

        for row in raw_data:
            temp_data = {'date': int(time.mktime(row[0].timetuple())), 'count': row[1]}
            data.append(temp_data)
    except:
        opened_data = stats_opened.time_series(start, end)
        closed_data = stats_closed.time_series(start, end)
        for i in range(len(opened_data)):
            temp_data = {
                'date': int(time.mktime(opened_data[i][0].timetuple())),
                'open_count': opened_data[i][1],
                'closed_count': closed_data[i][1],
            }
            data.append(temp_data)
    return data

@ApiHandler
def ticket_day(request, begin=day_to_str(datetime.date.today()), end=None):
    """

    Get service_name stats for a range of dates.

    """
    if end == None:
        key = begin
    else:
        key = "%s - %s" % (begin, end)

    # Request and group by service_name.
    requests = Request.objects \
            .filter(requested_datetime__range=date_range(begin, end)) \
            .values('service_name').annotate(count=Count('service_name')) \
            .order_by('-count')

    data = {key: [item for item in requests]}
    return data

# List requests in a given date range
@ApiHandler
def list_requests(request, begin=day_to_str(datetime.date.today()), end=None):
    """

    List requests opened in a given date range

    """
    requests = Request.objects \
        .filter(requested_datetime__range=date_range(begin,end))

    data = [item for item in requests.values()]
    return data

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Set PATH
import os
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# Django settings for open311dashboard project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'CHANGEME'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
        os.path.join(SITE_ROOT, 'dashboard/templates')
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.gis',
    'django.contrib.humanize',
    'dashboard',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

###
# Login URL
###
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/admin/'

###
# Local Settings
###
from settings_local import *

########NEW FILE########
__FILENAME__ = settings_local.example
# Django local settings
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# SECRET KEY
SECRET_KEY = ''

# Enable Geographic data
ENABLE_GEO = True

# Open311 City
# See http://wiki.open311.org/GeoReport_v2/Servers
CITY = {
  'URL': 'https://open311.sfgov.org/dev/Open311/v2/requests.xml',
  'PAGINATE': True,
  'JURISDICTION': 'sfgov.org'
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'dashboard.views.index'),
    url(r'^map/$', 'dashboard.views.map'),

    url(r'^street/$', 'dashboard.views.street_list'),
    url(r'^street/(?P<street_id>\d+)/$',
        'dashboard.views.street_view'),
    url(r'^street/(?P<street_id>\d+).json',
        'dashboard.views.street_view_json'),

    url(r'^neighborhood/$',
        'dashboard.views.neighborhood_list'),
    url(r'^neighborhood/(?P<neighborhood_id>\d+)/$',
        'dashboard.views.neighborhood_detail'),
    url(r'^neighborhood/(?P<neighborhood_id>\d+).json$',
        'dashboard.views.neighborhood_detail_json'),

    url(r'^search/$',
        'dashboard.views.street_search'),

    # API Calls
    url(r'^api/home/(?P<geography>\d+).json$',
        'dashboard.views.index', {'is_json': True}),

)

########NEW FILE########
