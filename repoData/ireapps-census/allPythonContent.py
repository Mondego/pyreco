__FILENAME__ = help_text
help_text = {
    "TRACTS": """
Can vary in size but averages 4,000 people. Designed to remain relatively
stable across decades to allow statistical comparisons. Boundaries defined
by local officials using Census Bureau rules.
    """,
    
    "PLACES": """
1. What most people call cities or towns. A locality incorporated under
state law that acts as a local government.<br/>
2. An unincorporated area that is well-known locally. Defined by state
officals under Census Bureau rules and called a "census designated place."
"CDP" is added to the end of name.
    """,
    
    "COUNTIES": """
The primary subdivisions of states. To cover the full country, this includes
Virginia's cities and Baltimore, St. Louis and Carson City, Nev., which
sit outside counties; the District of Columbia; and the boroughs, census
areas and related areas in Alaska.
    """,
    
    "COUSUBS": """
There are 2 basic kinds:

1. In 29 states, they have at least some governmental powers and are called minor civil divisions (MCDs). Their names may include variations on "township," "borough," "district," "precinct," etc. In 12 of those 29 states, they operate as full-purpose local governments: CT, MA, ME, MI, MN, NH, NJ, NY, PA, RI, VT, WI.

2. In states where there are no MCDs, county subdivisions are primarily statistical entities known as census county divisions. Their names end in "CCD."
    """
}

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = mongoutils
from django.conf import settings

from pymongo import Connection

def get_labels_collection():
    connection = Connection()
    db = connection[settings.LABELS_DB] 
    return db[settings.LABELS_COLLECTION]

def get_labelset():
    labels = get_labels_collection()
    labelset = labels.find_one({ 'dataset': settings.DATASET })

    return labelset


########NEW FILE########
__FILENAME__ = helpertags
from django import template
from django.conf import settings
from urlparse import urljoin
from urllib import quote_plus
import api.help_text
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.simple_tag
def build_media_url(uri):
    """
       Take a bit of url (uri) and put it together with the media url
       urljoin doesn't work like you think it would work. It likes to
       throw bits of the url away unless things are just right.
    """
    uri = "/".join(map(quote_plus,uri.split("/")))
    if getattr(settings,'MEDIA_URL',False):
        if uri.startswith('/'):
            return urljoin(settings.MEDIA_URL,uri[1:])
        else:
            return urljoin(settings.MEDIA_URL,uri)
    else:
        return uri
        
@register.simple_tag
def help_text(key):
    return api.help_text.help_text[key]

@register.filter
def percent(val):
    try:
        return float(val)*100.0
    except ValueError:
        return ""

########NEW FILE########
__FILENAME__ = tests
from django.utils import unittest
from django.test.client import Client
from django.test.simple import DjangoTestSuiteRunner
from django.core.urlresolvers import get_resolver, Resolver404
import simplejson
import logging
import mongoutils


class TestRunner(DjangoTestSuiteRunner):
    def setup_databases(self,**kwargs):
        pass

    def teardown_databases(self,old_config, **kwargs):
        pass

class DataTest(unittest.TestCase):
    # Stub. More mongoutils tests here.
    log = logging.getLogger('DataTests')
    def test_mongo_delaware(self):
        self.log.debug('test_mongo_delaware')
        g = mongoutils.get_geography("10")
        self.assertEqual(g['geoid'], "10")
        self.assertEqual(g['metadata']["NAME"], "Delaware")

class ViewTest(unittest.TestCase):
    log = logging.getLogger('ViewTests')
    def test_json_api(self):
        self.log.debug('test_json_api')
        geoids = '10,10001,10001040100'
        geoids = geoids.split(',')
        test = []
        c = Client()
        while geoids:
            test.append(geoids.pop())
            path = "/data/%s.json" % ",".join(test)
            self.log.debug("asking for %s" % path)
            r = c.get(path)
            json_response = simplejson.loads(r.content)
            self.assertEqual(len(test),len(json_response))
            print '.',

    def test_html_api(self):
        self.log.debug('test_html_api')
        geoids = '10,10001,10001040100'
        geoids = geoids.split(',')
        test = []
        c = Client()
        while geoids:
            test.append(geoids.pop())
            path = "/data/%s.html" % ",".join(test)
            self.log.debug("asking for %s" % path)
            r = c.get(path)
            print '.',

class UrlTest(unittest.TestCase):
    log = logging.getLogger('UrlTest')
    def test_resolution(self):
        r = get_resolver(None)
        geoids = '10,10001,10002,10003,10001040100'
        extensions = ["html", "csv", "json"]
        geoids = geoids.split(',')
        test = []
        while geoids:
            test.append(geoids.pop())
            geoid_str = ",".join(test)
            for extension in extensions:
                path = "/data/%s.%s" % (geoid_str, extension)
                self.log.debug("asking for %s" % path)
                match = r.resolve(path)
                self.assertEquals(1,len(match.kwargs))
                self.assertEquals(geoid_str,match.kwargs['geoids'])
        
        # A couple paths that should fail.
        self.assertRaises(
            Resolver404,
            r.resolve,
            "/data/10.foo"
        )
        self.assertRaises(
            Resolver404,
            r.resolve,
            "/data/bunk.html"
        )
        

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from api import views
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # The Homepage.
    (r'^$', views.homepage),

    # Data
    #/data/10.html
    #/data/10001.html
    #/data/10001041500.html
    #/data/10,10001,10001041500.html
    url(r'^data/(?P<geoids>[,\d]+)\.json$', views.data_as_json, name="data_as_json"),
    url(r'^data/(?P<geoids>[,\d]+)\.csv$', views.data_as_csv, name="data_as_csv"),
    url(r'^data/(?P<geoids>[,\d]+)\.(?P<format>kml|kmz)$', views.data_as_kml, name="data_as_kml"),
    url(r'^data/(?P<geoids>[,\d]+)\.html$', views.generic_view, { "template": "data.html" }, name="data"),
    url(r'^data/bulkdata.html$', views.generic_view, { "template": "bulkdata.html" }, name="bulkdata"),
    url(r'^map/$', views.generic_view, { "template": "map.html" }, name="map"),
    url(r'^map/(?P<geoids>[,\d]+)\.html$', views.generic_view, { "template": "map.html" }, name="map-with-geoids"),
    url(r'^map/contains$', views.map_contains, name="map_contains"),
    url(r'^profile/(?P<geoid>[\d]+)\.html$', views.generic_view, { "template": "profile.html" }, name="profile"),
    url(r'^docs/json.html$', views.generic_view, { "template": "docs/json.html" }, name="json-doc"),
    url(r'^docs/boundary.html$', views.generic_view, { "template": "docs/boundary.html" }, name="boundary-documentation"),
    url(r'^docs/javascript-library.html$', views.generic_view, { "template": "docs/javascript-library.html" }, name="js-lib-documentation"),
    url(r'^util/create_table/(?P<aggregate>(all_files|all_tables))\.sql$', views.generate_sql, name="generate_sql"), # order matters. keep this first to catch only numbers before tables
    url(r'^util/create_table/(?P<file_ids>[,\d{1,2}]+)\.sql$', views.generate_sql, name="generate_sql"), # order matters. keep this first to catch only numbers before tables
    url(r'^util/create_table/(?P<table_ids>[,\w]+)\.sql$', views.generate_sql, name="generate_sql"),

    # Generate CSV/JSON for all elements in a given region (used from within Query Builder)
    #/internal/download_data_for_region/10.csv (or .json)
    (r'^internal/download_data_for_region/(?P<sumlev>\d{3})-(?P<containerlev>\d{3})-(?P<container>\d+)\.(?P<datatype>csv|json)$', views.download_data_for_region),
)

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

import simplejson

from sqlalchemy import Column, MetaData, Table
from sqlalchemy import Float, Integer, String
from sqlalchemy.schema import CreateTable

from api import mongoutils

from django.conf import settings
import requests

def strip_callback(data):
    return data[data.index('(') + 1:-1]

def _api_fetch(url):
    r = requests.get(url)
    content = strip_callback(r.content)
    return simplejson.loads(content)

def fetch_tracts_by_state(state):
    url = '%s/%s/tracts.jsonp' % (settings.API_URL, state)
    return _api_fetch(url)

def fetch_tracts_by_county(county):
    state = county[0:2]
    url = '%s/%s/tracts_%s.jsonp' % (settings.API_URL, state, county)
    return _api_fetch(url)

def fetch_county_subdivisions_by_county(county):
    state = county[0:2]
    url = '%s/%s/county_subdivisions_%s.jsonp' % (settings.API_URL, state, county)
    return _api_fetch(url)

def fetch_counties_by_state(state):
    url = '%s/%s/counties.jsonp' % (settings.API_URL, state)
    return _api_fetch(url)

def fetch_county_subdivisions_by_state(state):
    url = '%s/%s/county_subdivisions.jsonp' % (settings.API_URL, state)
    return _api_fetch(url)

def fetch_places_by_state(state):
    url = '%s/%s/places.jsonp' % (settings.API_URL, state)
    return _api_fetch(url)

def fetch_geography(geoid):
    state = geoid[0:2]
    url = '%s/%s/%s.jsonp' % (settings.API_URL, state, geoid)
    return _api_fetch(url)

def fetch_geographies(geoids):
    return [fetch_geography(geoid) for geoid in geoids]

def fetch_labels(dataset):
    url = '%s/%s_labels.jsonp' % (settings.API_URL, dataset)
    return _api_fetch(url)

LINKING_COLUMNS = [
    ('FILEID',6),
    ('STUSAB',2),
    ('CHARITER',3),
    ('CIFSN',3),
    ('LOGRECNO',7),
]    

def generate_create_sql_by_file(file_numbers=None):
    if file_numbers is None:
        file_numbers = range(1,48)

    statements = []
    for file_number in file_numbers:
        sql_table = _create_base_table(_table_name_for_number(file_number))
        for table in SF1_FILE_SEGMENTS[file_number]:
            _add_sql_columns_for_table(sql_table,table)
        statements.append(unicode(CreateTable(sql_table).compile(dialect=None)).strip() + ';')

    return "\n\n".join(statements)

def _table_name_for_number(file_number):
    return 'sf1_%02i' % file_number

def generate_sql_by_table(table_codes=None):
    statements = []
    if table_codes is None:
        table_codes = []
        for f in SF1_FILE_SEGMENTS[1:]:
            table_codes.extend(f)

    statements = []
    for table_code in table_codes:
        sql_table = _create_base_table(table_code)
        _add_sql_columns_for_table(sql_table,table_code)
        statements.append(unicode(CreateTable(sql_table).compile(dialect=None)).strip() + ';')
    
    return "\n\n".join(statements)

def generate_views_by_table(table_codes=None):
    labels = mongoutils.get_labelset()

    statements = []
    if table_codes is None:
        table_codes = []
        for f in SF1_FILE_SEGMENTS[1:]:
            table_codes.extend(f)

    statements = []
    for table_code in table_codes:
        table_name = _table_name_for_number(FILE_NUMBER_BY_TABLE_CODE[table_code])
        columns = ['"%s"' % x[0] for x in LINKING_COLUMNS]
        for label in sorted(labels['tables'][table_code]['labels']):
            columns.append('"%s"' % label)

        columns = ',\n'.join(columns)
        statements.append('CREATE VIEW sf1_%s as SELECT %s from %s;' % (table_code,columns,table_name))
    
    return "\n\n".join(statements)

def _create_base_table(name):
    metadata = MetaData()
    sql_table = Table(name, metadata)
    for name,length in LINKING_COLUMNS:
        sql_table.append_column(Column(name, String(length=length), nullable=False))

    return sql_table

def _add_sql_columns_for_table(sql_table,code):
    labels = mongoutils.get_labelset()
    table_labels = labels['tables'][code]
    if table_labels['name'].find('AVERAGE') != -1 or table_labels['name'].find('MEDIAN') != -1:
        col_type = Float
    else:
        col_type = Integer
    for label in sorted(table_labels['labels']):
        sql_table.append_column(Column(label, col_type(), nullable=False))

SF1_FILE_SEGMENTS = [
    [ 'no file zero, this is a place_holder'],
    ['P1'], # file 1
    ['P2'], # file 2
    ['P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'], # file 3
    ['P10', 'P11', 'P12', 'P13', 'P14'], # file 4
    ['P15', 'P16', 'P17', 'P18', 'P19', 'P20', 'P21', 'P22', 'P23', 'P24', 'P25', 'P26', 'P27', 'P28', 'P29', 'P30'], # file 5
    ['P31', 'P32', 'P33', 'P34', 'P35', 'P36', 'P37', 'P38', 'P39', 'P40', 'P41', 'P42', 'P43', 'P44', 'P45', 'P46', 'P47', 'P48', 'P49'], # file 6
    ['P50', 'P51', 'P12A', 'P12B', 'P12C', 'P12D', 'P12E'], # file 7
    ['P12F', 'P12G', 'P12H', 'P12I', 'P13A', 'P13B', 'P13C', 'P13D', 'P13E', 'P13F', 'P13G', 'P13H', 'P13I', 'P16A', 'P16B', 'P16C', 'P16D', 'P16E', 'P16F', 'P16G', 'P16H', 'P16I', 'P17A'], # file 8
    ['P17B', 'P17C', 'P17D', 'P17E', 'P17F', 'P17G', 'P17H', 'P17I', 'P18A', 'P18B', 'P18C', 'P18D', 'P18E', 'P18F', 'P18G', 'P18H', 'P18I', 'P28A', 'P28B', 'P28C', 'P28D', 'P28E', 'P28F', 'P28G', 'P28H', 'P28I'], # file 9
    ['P29A', 'P29B', 'P29C', 'P29D', 'P29E', 'P29F', 'P29G', 'P29H', 'P29I'], # file 10
    ['P31A', 'P31B', 'P31C', 'P31D', 'P31E', 'P31F', 'P31G', 'P31H', 'P31I', 'P34A', 'P34B', 'P34C', 'P34D', 'P34E'], # file 11
    ['P34F', 'P34G', 'P34H', 'P34I', 'P35A', 'P35B', 'P35C', 'P35D', 'P35E', 'P35F', 'P35G', 'P35H', 'P35I', 'P36A', 'P36B', 'P36C', 'P36D', 'P36E', 'P36F', 'P36G', 'P36H', 'P36I', 'P37A', 'P37B', 'P37C', 'P37D', 'P37E', 'P37F', 'P37G', 'P37H', 'P37I', 'P38A', 'P38B', 'P38C', 'P38D', 'P38E'], # file 12
    ['P38F', 'P38G', 'P38H', 'P38I', 'P39A', 'P39B', 'P39C', 'P39D', 'P39E', 'P39F', 'P39G', 'P39H'], # file 13
    ['P39I'], # file 14
    ['PCT1', 'PCT2', 'PCT3', 'PCT4', 'PCT5', 'PCT6', 'PCT7', 'PCT8'], # file 15
    ['PCT9', 'PCT10', 'PCT11'], # file 16
    ['PCT12'], # file 17
    ['PCT13', 'PCT14', 'PCT15', 'PCT16', 'PCT17', 'PCT18', 'PCT19', 'PCT20'], # file 18
    ['PCT21','PCT22'], # file 19
    ['PCT12A'], # file 20
    ['PCT12B'], # file 21
    ['PCT12C'], # file 22
    ['PCT12D'], # file 23
    ['PCT12E'], # file 24
    ['PCT12F'], # file 25
    ['PCT12G'], # file 26
    ['PCT12H'], # file 27
    ['PCT12I'], # file 28
    ['PCT12J'], # file 29
    ['PCT12K'], # file 30
    ['PCT12L'], # file 31
    ['PCT12M'], # file 32
    ['PCT12N'], # file 33
    ['PCT12O'], # file 34
    ['PCT13A','PCT13B','PCT13C','PCT13D','PCT13E'], # file 35
    ['PCT13F','PCT13G','PCT13H','PCT13I','PCT14A','PCT14B','PCT14C','PCT14D','PCT14E','PCT14F','PCT14G','PCT14H','PCT14I','PCT19A','PCT19B'], # file 36
    ['PCT19C','PCT19D','PCT19E','PCT19F','PCT19G','PCT19H','PCT19I','PCT20A','PCT20B','PCT20C','PCT20D','PCT20E'], # file 37
    ['PCT20F','PCT20G','PCT20H','PCT20I','PCT22A','PCT22B','PCT22C','PCT22D','PCT22E','PCT22F'], # file 38
    ['PCT22G','PCT22H','PCT22I'], # file 39
    ['PCO1','PCO2','PCO3','PCO4','PCO5','PCO6'], # file 40
    ['PCO7','PCO8','PCO9','PCO10'], # file 41
    ['H1'], # file 42
    ['H2'], # file 43
    ['H3','H4','H5','H6','H7','H8','H9','H10','H11','H12','H13','H14','H15','H16','H17','H18','H19','H20','H21','H22','H11A','H11B', 'H11C','H11D', 'H11E','H11F'], # file 44
    ['H11G','H11H','H11I','H12A','H12B','H12C','H12D','H12E','H12F','H12G','H12H','H12I','H16A','H16B','H16C','H16D','H16E','H16F','H16G','H16H','H16I','H17A','H17B','H17C'], # file 45
    ['H17D','H17E','H17F','H17G','H17H','H17I'], # file 46
    ['HCT1','HCT2','HCT3','HCT4'], # file 47
]

FILE_NUMBER_BY_TABLE_CODE = {}
for i,x in enumerate(SF1_FILE_SEGMENTS):
    if i > 0:
        for table_code in x:
            FILE_NUMBER_BY_TABLE_CODE[table_code] = i


########NEW FILE########
__FILENAME__ = views
import simplejson

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect

from django.shortcuts import render_to_response
from django.contrib.gis.shortcuts import render_to_kml, render_to_kmz
from django.contrib.gis.geos import Point
from django.template import RequestContext, Template, Context
from django.core.urlresolvers import reverse

from boundaryservice.models import Boundary,BoundarySet

import csv
import help_text
import mongoutils
import utils
from datetime import datetime

DATA_ALTERNATIVES = ['2000', '2010', 'delta', 'pct_change']

BOUNDARY_TYPES = [x[0] for x in BoundarySet.objects.values_list('slug').distinct()]

def homepage(request):
    return render_to_response('homepage.html', {
            'help_text': help_text,
            'settings': settings,
        },
        context_instance=RequestContext(request))
    
def generic_view(request, template=None, **kwargs):
    return render_to_response(template, { 'settings': settings }, context_instance=RequestContext(request))


def download_data_for_region(request, sumlev='', containerlev='', container='', datatype=''):
    print sumlev, containerlev
    if sumlev == '140' and containerlev == '040':
        geo_list = utils.fetch_tracts_by_state(container)
    elif sumlev == '140' and containerlev == '050':
        geo_list = utils.fetch_tracts_by_county(container)
    elif sumlev == '060' and containerlev == '050':
        geo_list = utils.fetch_county_subdivisions_by_county(container)
    elif sumlev == '160' and containerlev == '040':
        geo_list = utils.fetch_places_by_state(container)
    elif sumlev == '050' and containerlev == '040':
        geo_list = utils.fetch_counties_by_state(container)
    elif sumlev == '060' and containerlev == '040':
        geo_list = utils.fetch_county_subdivisions_by_state(container)

    geoids = ','.join([g[1] for g in geo_list])

    if datatype == 'csv':
        return data_as_csv(request, geoids)
    elif datatype == 'json':
        return data_as_json(request, geoids)

def get_tables_for_request(request):
    tables = request.GET.get("tables", None)

    if tables:
        tables = tables.split(",")
    else:
        tables = settings.DEFAULT_TABLES 

    return tables

# --- JSON ---
def data_as_json(request, geoids):
    tables = get_tables_for_request(request) 

    geographies = {}

    geoids_list = filter(lambda g: bool(g), geoids.split(','))

    for g in utils.fetch_geographies(geoids_list):
        del g['xrefs']

        for table in g["data"]["2010"].keys():
            if table not in tables:
                del g["data"]["2010"][table]

                # Not all data has 2000 values
                try:
                    del g["data"]["2000"][table]
                    del g["data"]["delta"][table]
                    del g["data"]["pct_change"][table]
                except KeyError:
                    continue

        geographies[g['geoid']] = g
        
    return HttpResponse(simplejson.dumps(geographies), mimetype='application/json')

# --- CSV ---
def data_as_csv(request, geoids):
    tables = get_tables_for_request(request) 
    labelset = mongoutils.get_labelset()

    response = HttpResponse(mimetype="text/csv")
    w = csv.writer(response)
    w.writerow(_csv_row_header(tables, labelset))

    geoids_list = filter(lambda g: bool(g), geoids.split(','))

    for g in utils.fetch_geographies(geoids_list):
        csvrow = _csv_row_for_geography(g, tables, labelset)
        w.writerow(csvrow)

    now = datetime.now()
    date_string = "%s-%s-%s-%s" % (now.year, now.month, now.day, now.microsecond)
    response['Content-Disposition'] = "attachment; filename=ire-census-%s.csv" % date_string

    return response

def _csv_row_header(tables, labelset):
    row = ["sumlev", "geoid", "name"]

    for table in tables:
        # Fail gracefully if a table isn't loaded (as in test
        try:
            labels = labelset['tables'][table]['labels']
        except KeyError:
            continue

        for statistic in sorted(labels.keys()):
            for alternative in DATA_ALTERNATIVES:
                if alternative == '2010':
                    row.append(statistic)
                else:
                    row.append("%s.%s" % (statistic,alternative))

    return row
    
def _csv_row_for_geography(geography, tables, labelset):
    row = [
        geography['sumlev'],
        geography['geoid'],
        geography['metadata']['NAME']
    ]

    for table in tables:
        # Fail gracefully if a table isn't loaded (as in test
        try:
            labels = labelset['tables'][table]['labels']
        except KeyError:
            continue

        for statistic in sorted(labels.keys()):
            for alternative in DATA_ALTERNATIVES:
                try:
                    row.append( geography['data'][alternative][table][statistic] )
                except KeyError:
                    row.append('')

    return row

# --- KML ---
def data_as_kml(request, geoids, format='kml'):
    tables = get_tables_for_request(request) 

    geoid_list = filter(lambda g: bool(g), geoids.split(','))
    boundaries = dict((b.external_id, b) for b in Boundary.objects.filter(external_id__in=geoid_list))
    json_data = dict((j['geoid'], j) for j in utils.fetch_geographies(geoid_list))
    labelset = mongoutils.get_labelset()
    
    placemarks = [
        _create_placemark_dict(boundaries[geoid], json_data[geoid], tables, labelset) for geoid in geoid_list
    ] 

    if format == 'kmz':
        render = render_to_kmz
    else:
        render = render_to_kml

    return render('gis/kml/placemarks.kml', {'places' : placemarks})            

def _create_placemark_dict(b, j, tables, labelset):
    """
    Each placemark should have a name, a description, and kml which includes <ExtraData>
    """
    p = {
       'name': b.display_name,
       'description': 'Summary Level: %(sumlev)s; GeoID: %(geoid)s' % (j),
    }

    kml_context = _build_kml_context_for_template(b, j, tables, labelset)
    shape = b.simple_shape.transform(4326, clone=True)
    p['kml'] = shape.kml + KML_EXTENDED_DATA_TEMPLATE.render(Context(kml_context))
    
    return p

KML_EXTENDED_DATA_TEMPLATE = Template("""
<ExtendedData>
    {% for datum in data %}
  <Data name="{{datum.name}}">{% if datum.display_name %}
    <displayName><![CDATA[{{datum.display_name}}]]></displayName>{% endif %}
    <value><![CDATA[{{datum.value}}]]></value>
  </Data>
  {% endfor %}
</ExtendedData>""")

def _build_kml_context_for_template(b, j, tables, labelset):
    kml_context = { 'data': [] }

    for table in tables:
        # Fail gracefully if a table isn't loaded (as in test
        try:
            labels = labelset['tables'][table]['labels']
        except KeyError:
            continue

        for statistic in sorted(labels.keys()):
            for alternative in DATA_ALTERNATIVES:
                #print "t: %s, a: %s, s: %s" % (table, alternative, statistic)
                try: 
                    datum = {
                        'value': j['data'][alternative][table][statistic]
                    }

                    if alternative == '2010':
                        datum['name'] = statistic
                    else:
                        datum['name'] = "%s.%s" % (statistic, alternative)

                    datum['display_name'] = labels[statistic]['text']
                    kml_context['data'].append(datum)

                except KeyError:
                    pass

    return kml_context
    
def generate_sql(request, file_ids=None, table_ids=None, aggregate=None):
    if aggregate == 'all_files':
        sql = utils.generate_create_sql_by_file()
        return HttpResponse(sql,mimetype='text/plain')
    elif aggregate == 'all_tables':
        sql = utils.generate_sql_by_table()
        return HttpResponse(sql,mimetype='text/plain')
    elif aggregate == 'all_table_views':
        sql = utils.generate_views_by_table()
        return HttpResponse(sql,mimetype='text/plain')
    elif aggregate is not None:
        return HttpResponseNotFound()

    if file_ids:
        ids = map(int,file_ids.split(','))
        sql = utils.generate_create_sql_by_file(file_numbers=ids)
        return HttpResponse(sql,mimetype='text/plain')

    if table_ids:    
        table_ids = table_ids.split(',')
        sql = utils.generate_sql_by_table(table_ids)
        return HttpResponse(sql,mimetype='text/plain')

    return HttpResponseNotFound()

def map_contains(request):
    point = request.REQUEST.get('point',None)
    try:
        lat,lng = point.split(',',1)
        point = Point(float(lng),float(lat))
    except:
        raise TypeError("A point must be provided as a comma-separated string, 'lat,lng'")

    types = request.REQUEST.get('types',[])
    if types:
        types = [x for x in types.split(',') if x in BOUNDARY_TYPES]
        if not types: raise ValueError("None of the specified types are valid. Use one or more of (%s) separated by commas." % ','.join(BOUNDARY_TYPES))
    else:
        types = BOUNDARY_TYPES

    boundaries = Boundary.objects.filter(shape__contains=point,set__slug__in=types)
    geoids = sorted(x[0] for x in boundaries.values_list('external_id'))
    geoids = ','.join(geoids)
    url = reverse('map',kwargs={'geoids': geoids}) + "#%.6f,%.6f" % (point.y,point.x)
    return HttpResponseRedirect(url)
    

########NEW FILE########
__FILENAME__ = settings
from config.settings import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Database
DATABASES['default']['HOST'] = 'census.ire.org'
DATABASES['default']['PORT'] = '5433'
DATABASES['default']['USER'] = 'censusweb'
DATABASES['default']['PASSWORD'] = 'Xy9XKembdu'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://censusmedia.ire.org/censusweb/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://censusmedia.ire.org/censusweb/admin_media/'

# Predefined domain
MY_SITE_DOMAIN = 'census.ire.org'
GEO_API_ROOT = "%s/geo" % MY_SITE_DOMAIN

# Email
EMAIL_HOST = 'mail'
EMAIL_PORT = 25

# Caching
CACHE_BACKEND = 'memcached://cache:11211/'

# S3
AWS_S3_URL = 's3://censusmedia.ire.org/censusweb/'

# Application settings
API_URL = 'http://censusdata.ire.org'

# Internal IPs for security
INTERNAL_IPS = ()

# logging
import logging.config
LOG_FILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logger.conf')
logging.config.fileConfig(LOG_FILENAME)


########NEW FILE########
__FILENAME__ = settings
import logging
import os

import django

# Base paths
DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Debugging
DEBUG = True 
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'censusweb',                      # Or path to database file if using sqlite3.
        'USER': 'censusweb',                      # Not used with sqlite3.
        'PASSWORD': 'Xy9XKembdu',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '5432',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time
TIME_ZONE = 'America/Chicago'

# Local language
LANGUAGE_CODE = 'en-us'

# Site framework
SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
MEDIA_ROOT = os.path.join(SITE_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'kljdfagjkldfjklgsf;lj098w3r09eoifjfw09u39j'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.media',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'config.urls'

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates')
)

INSTALLED_APPS = (
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    # 'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    'django.contrib.humanize',
    'django.contrib.gis',
    'django.contrib.sitemaps',
    'boundaryservice',
    'api',
)

# Predefined domain
MY_SITE_DOMAIN = 'localhost:8000'
GEO_API_ROOT = "%s/geo" % MY_SITE_DOMAIN

# Email
# run "python -m smtpd -n -c DebuggingServer localhost:1025" to see outgoing
# messages dumped to the terminal
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
DEFAULT_FROM_EMAIL = 'do.not.reply@censusweb.ire.org'

# Caching
CACHE_MIDDLEWARE_KEY_PREFIX='censusweb'
CACHE_MIDDLEWARE_SECONDS=90 * 60 # 90 minutes
CACHE_BACKEND="dummy:///"

# Site configuration
LABELS_DB = 'census_labels'
LABELS_COLLECTION = 'labels'

# Application settings
DATASET = 'SF1'
API_URL = 'http://s3.amazonaws.com/census-test' 
DEFAULT_TABLES = ['P1', 'P2', 'P3', 'P5', 'P6', 'P12', 'P13', 'P29', 'P37', 'P38', 'H4', 'H5', 'H12']

TEST_RUNNER='api.tests.TestRunner'

# Logging
logging.basicConfig(
    level=logging.INFO,
)

# Allow for local (per-user) override
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings
from config.settings import *

DEBUG = True 
TEMPLATE_DEBUG = DEBUG

# Database
DATABASES['default']['HOST'] = 'censusweb.beta.tribapps.com'
DATABASES['default']['PORT'] = '5433'
DATABASES['default']['USER'] = 'censusweb'
DATABASES['default']['PASSWORD'] = 'Xy9XKembdu'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://media-beta.tribapps.com/censusweb/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://media-beta.tribapps.com/censusweb/admin_media/'

# Predefined domain
MY_SITE_DOMAIN = 'censusweb.beta.tribapps.com'
GEO_API_ROOT = "%s/geo" % MY_SITE_DOMAIN

# Email
EMAIL_HOST = 'mail'
EMAIL_PORT = 25

# Caching
CACHE_BACKEND = 'memcached://cache:11211/'

# S3
AWS_S3_URL = 's3://media-beta.tribapps.com/censusweb/'

# Internal IPs for security
INTERNAL_IPS = ()

# logging
import logging.config
LOG_FILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logger.conf')
logging.config.fileConfig(LOG_FILENAME)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import redirect_to
from django.core.urlresolvers import reverse

urlpatterns = patterns('',
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.MEDIA_ROOT }),
    (r'^geo/$', redirect_to, { 'url': "/docs/boundary.html"}),
#    (r'^geo/$', redirect_to, { 'url': reverse("boundary-documentation")}),
    (r'^geo/', include('boundaryservice.urls')),
    (r'^', include('api.urls')),
)

########NEW FILE########
__FILENAME__ = definitions
"""
Configuration describing the shapefiles to be loaded.
"""
from datetime import date

class simple_namer():
    """
    Name features with a joined combination of attributes, optionally passing the result through a normalizing function.
    """
    def __init__(self, attribute_names, seperator=' ', normalizer=None):
        self.attribute_names = attribute_names
        self.seperator = seperator
        self.normalizer = normalizer

    def __call__(self, feature):
        attribute_values = map(str, map(feature.get, self.attribute_names))
        name = self.seperator.join(attribute_values).strip()
    
        if self.normalizer:
            normed = self.normalizer(name)
            if not normed:
                raise ValueError('Failed to normalize \"%s\".' % name)
            else:
                name = normed

        return name

SHAPEFILES = {
    # This key should be the plural name of the boundaries in this set
    'States': {
        # Path to a shapefile, relative to /data
        'file': 'STATE/',
        # Generic singular name for an boundary of from this set
        'singular': 'State',
        # Should the singular name come first when creating canonical identifiers for this set?
        # (e.g. True in this case would result in "Neighborhood South Austin" rather than "South Austin Neighborhood")
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': simple_namer(['GEOID10']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': simple_namer(['NAME10']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'U.S. Census Bureau, Geography Division',
        # Geographic extents which the boundary set encompasses
        'domain': 'United States',
        # Last time the source was checked for new data
        'last_updated': date(2011, 05, 21),
        # A url to the source of the data
        'href': 'http://www.census.gov/cgi-bin/geo/shapefiles2010/main',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': 'latin-1'
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        #'srid': ''
    },
    # This key should be the plural name of the boundaries in this set
    'Counties': {
        # Path to a shapefile, relative to /data
        'file': 'COUNTY/',
        # Generic singular name for an boundary of from this set
        'singular': 'County',
        # Should the singular name come first when creating canonical identifiers for this set?
        # (e.g. True in this case would result in "Neighborhood South Austin" rather than "South Austin Neighborhood")
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': simple_namer(['GEOID10']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': simple_namer(['NAME10']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'U.S. Census Bureau, Geography Division',
        # Geographic extents which the boundary set encompasses
        'domain': 'United States',
        # Last time the source was checked for new data
        'last_updated': date(2011, 05, 21),
        # A url to the source of the data
        'href': 'http://www.census.gov/cgi-bin/geo/shapefiles2010/main',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': 'latin-1'
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        #'srid': ''
    },
    # This key should be the plural name of the boundaries in this set
    'Places': {
        # Path to a shapefile, relative to /data
        'file': 'PLACE/',
        # Generic singular name for an boundary of from this set
        'singular': 'Place',
        # Should the singular name come first when creating canonical identifiers for this set?
        # (e.g. True in this case would result in "Neighborhood South Austin" rather than "South Austin Neighborhood")
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': simple_namer(['GEOID10']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': simple_namer(['NAME10']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'U.S. Census Bureau, Geography Division',
        # Geographic extents which the boundary set encompasses
        'domain': 'United States',
        # Last time the source was checked for new data
        'last_updated': date(2011, 06, 23),
        # A url to the source of the data
        'href': 'http://www.census.gov/cgi-bin/geo/shapefiles2010/main',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': 'latin-1'
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        #'srid': ''
    },
    # This key should be the plural name of the boundaries in this set
    'Tracts': {
        # Path to a shapefile, relative to /data
        'file': 'TRACT/',
        # Generic singular name for an boundary of from this set
        'singular': 'Tract',
        # Should the singular name come first when creating canonical identifiers for this set?
        # (e.g. True in this case would result in "Neighborhood South Austin" rather than "South Austin Neighborhood")
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': simple_namer(['GEOID10']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': simple_namer(['NAME10']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'U.S. Census Bureau, Geography Division',
        # Geographic extents which the boundary set encompasses
        'domain': 'United States',
        # Last time the source was checked for new data
        'last_updated': date(2011, 06, 23),
        # A url to the source of the data
        'href': 'http://www.census.gov/cgi-bin/geo/shapefiles2010/main',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': 'latin-1'
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        #'srid': ''
    },
    # This key should be the plural name of the boundaries in this set
    'County Subdivisions': {
        # Path to a shapefile, relative to /data
        'file': 'COUSUB/',
        # Generic singular name for an boundary of from this set
        'singular': 'County Subdivision',
        # Should the singular name come first when creating canonical identifiers for this set?
        # (e.g. True in this case would result in "Neighborhood South Austin" rather than "South Austin Neighborhood")
        'kind_first': False,
        # Function which each feature wall be passed to in order to extract its "external_id" property
        # The utils module contains several generic functions for doing this
        'ider': simple_namer(['GEOID10']),
        # Function which each feature will be passed to in order to extract its "name" property
        'namer': simple_namer(['NAME10']),
        # Authority that is responsible for the accuracy of this data
        'authority': 'U.S. Census Bureau, Geography Division',
        # Geographic extents which the boundary set encompasses
        'domain': 'United States',
        # Last time the source was checked for new data
        'last_updated': date(2011, 06, 23),
        # A url to the source of the data
        'href': 'http://www.census.gov/cgi-bin/geo/shapefiles2010/main',
        # Notes identifying any pecularities about the data, such as columns that were deleted or files which were merged
        'notes': '',
        # Encoding of the text fields in the shapefile, i.e. 'utf-8'. If this is left empty 'ascii' is assumed
        'encoding': 'latin-1'
        # SRID of the geometry data in the shapefile if it can not be inferred from an accompanying .prj file
        # This is normally not necessary and can be left undefined or set to an empty string to maintain the default behavior
        #'srid': ''
    },
}

########NEW FILE########
__FILENAME__ = fabfile
# Chicago Tribune News Applications fabfile
# No copying allowed

from fabric.api import *

"""
Base configuration
"""
#name of the deployed site if different from the name of the project
env.site_name = 'censusweb'

env.project_name = 'censusweb'
env.database_password = 'Xy9XKembdu'
env.site_media_prefix = "site_media"
env.admin_media_prefix = "admin_media"
env.path = '/home/ubuntu/sites/%(project_name)s' % env
env.log_path = '/home/ubuntu/logs' % env
env.env_path = '/home/ubuntu/sites/virtualenvs/%(project_name)s' % env
env.repo_path = '%(path)s' % env
env.site_path = '%(repo_path)s/censusweb' % env
env.dataprocessing_path = '%(repo_path)s/dataprocessing' % env
env.apache_config_path = '/home/ubuntu/apache/%(project_name)s' % env
env.python = 'python2.7'
env.repository_url = "git@github.com:ireapps/census.git"
env.memcached_server_address = "cache"
env.multi_server = False

"""
Environments
"""
def production():
    """
    Work on production environment
    """
    #TKTK
    env.settings = 'production'
    env.hosts = ['census.ire.org']
    env.user = 'ubuntu'
    env.s3_bucket = 'censusmedia.ire.org'
    env.site_domain = 'census.ire.org'    
    env.cache_server = 'census.ire.org'

def staging():
    """
    Work on staging environment
    """
    env.settings = 'staging'
    env.hosts = ['census.tribapps.com'] 
    env.user = 'ubuntu'
    env.s3_bucket = 'media-beta.tribapps.com'
    env.site_domain = 'census.tribapps.com'
    env.cache_server = 'census.tribapps.com'
    
"""
Branches
"""
def stable():
    """
    Work on stable branch.
    """
    env.branch = 'stable'

def master():
    """
    Work on development branch.
    """
    env.branch = 'master'

def branch(branch_name):
    """
    Work on any specified branch.
    """
    env.branch = branch_name
    
"""
Commands - setup
"""
def setup():
    """
    Setup a fresh virtualenv, install everything we need, and fire up the database.
    
    Does NOT perform the functions of deploy().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    setup_directories()
    setup_virtualenv()
    clone_repo()
    checkout_latest()
    install_requirements()
    destroy_database()
    create_database()
    load_data()
    install_apache_conf()
    deploy_requirements_to_s3()

def setup_directories():
    """
    Create directories necessary for deployment.
    """
    run('mkdir -p %(path)s' % env)
    
def setup_virtualenv():
    """
    Setup a fresh virtualenv.
    """
    run('virtualenv -p %(python)s --no-site-packages %(env_path)s;' % env)
    run('source %(env_path)s/bin/activate; easy_install -U setuptools; easy_install -U pip;' % env)

def clone_repo():
    """
    Do initial clone of the git repository.
    """
    run('git clone %(repository_url)s %(repo_path)s' % env)

def checkout_latest():
    """
    Pull the latest code on the specified branch.
    """
    run('cd %(repo_path)s; git checkout %(branch)s; git pull origin %(branch)s' % env)

def install_requirements():
    """
    Install the required packages using pip.
    """
    run('source %(env_path)s/bin/activate; pip install -q -r %(site_path)s/requirements.txt' % env)

def install_apache_conf():
    """
    Install the apache site config file.
    """
    sudo('cp %(site_path)s/config/%(settings)s/apache %(apache_config_path)s' % env)

def deploy_requirements_to_s3():
    """
    Deploy the admin media to s3.
    """
    with settings(warn_only=True):
        run('s3cmd del --recursive s3://%(s3_bucket)s/%(project_name)s/%(admin_media_prefix)s/' % env)
    run('s3cmd -P --guess-mime-type --rexclude-from=%(site_path)s/s3exclude sync %(env_path)s/src/django/django/contrib/admin/media/ s3://%(s3_bucket)s/%(project_name)s/%(admin_media_prefix)s/' % env)

"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    
    Does not perform the functions of load_new_data().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    with settings(warn_only=True):
        maintenance_up()
        
    checkout_latest()
    gzip_assets()
    deploy_to_s3()
    maintenance_down()
    clear_cache()
    
def maintenance_up():
    """
    Install the Apache maintenance configuration.
    """
    sudo('cp %(site_path)s/config/%(settings)s/apache_maintenance %(apache_config_path)s' % env)
    reboot()

def gzip_assets():
    """
    GZips every file in the media directory and places the new file
    in the gzip directory with the same filename.
    """
    run('cd %(site_path)s; python gzip_assets.py' % env)

def deploy_to_s3():
    """
    Deploy the latest project site media to S3.
    """
    env.gzip_path = '%(site_path)s/gzip_media/' % env
    run(('s3cmd -P --add-header=Content-encoding:gzip --guess-mime-type --rexclude-from=%(site_path)s/s3exclude sync %(gzip_path)s s3://%(s3_bucket)s/%(project_name)s/%(site_media_prefix)s/') % env)
       
def reboot(): 
    """
    Restart the Apache2 server.
    """
    if env.multi_server:
        run('bounce-apaches-for-cluster')
    else:
        sudo('service apache2 restart')
    
def maintenance_down():
    """
    Reinstall the normal site configuration.
    """
    install_apache_conf()
    reboot()
    
"""
Commands - rollback
"""
def rollback(commit_id):
    """
    Rolls back to specified git commit hash or tag.
    
    There is NO guarantee we have committed a valid dataset for an arbitrary
    commit hash.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    maintenance_up()
    checkout_latest()
    git_reset(commit_id)
    gzip_assets()
    deploy_to_s3()
    maintenance_down()
    
def git_reset(commit_id):
    """
    Reset the git repository to an arbitrary commit hash or tag.
    """
    env.commit_id = commit_id
    run("cd %(repo_path)s; git reset --hard %(commit_id)s" % env)

"""
Commands - data
"""
def load_new_data():
    """
    Erase the current database and load new data from the SQL dump file.
    """
    require('settings', provided_by=[production, staging])
    
    maintenance_up()
    pgpool_down()
    destroy_database()
    create_database()
    load_data()
    pgpool_up()
    maintenance_down()
    
def create_database(func=run):
    """
    Creates the user and database for this project.
    """
    func('createuser -s %(project_name)s' % env)
    func('echo "ALTER USER %(project_name)s with password %(database_password)s" | psql postgres' % env)
    func('echo "GRANT ALL PRIVILEGES TO %(project_name)s;" | psql postgres' % env)
    func('createdb -O %(project_name)s %(project_name)s -T template_postgis' % env)
    
def destroy_database(func=run):
    """
    Destroys the user and database for this project.
    
    Will not cause the fab to fail if they do not exist.
    """
    with settings(warn_only=True):
        func('dropdb %(project_name)s' % env)
        func('dropuser %(project_name)s' % env)
        
def load_data():
    """
    Loads data from the repository into PostgreSQL.
    """
    run('psql -q %(project_name)s < %(site_path)s/data/psql/dump.sql' % env)
    
def pgpool_down():
    """
    Stop pgpool so that it won't prevent the database from being rebuilt.
    """
    sudo('/etc/init.d/pgpool stop')
    
def pgpool_up():
    """
    Start pgpool.
    """
    sudo('/etc/init.d/pgpool start')

"""
Commands - Data Processing
"""
def run_unattended_batch_command(command, command_log):
    # Make sure log exists
    run("touch %s" % command_log)

    with cd(env.dataprocessing_path):
        run("source %s/bin/activate; nohup %s >> %s < /dev/null &" % (env.env_path, command, command_log))

def batch_sf(state, fake=''):
    """
    Kick off the SF 2000 data loader for a state.
    """
    command = './batch_sf.sh %s %s %s' % (state, env.settings, fake)
    loader_log = '%s/census.load.%s.log' % (env.log_path, state)
    run_unattended_batch_command(command, loader_log)

def batch_sf_everything(fake=''):
    """
    Kick off the SF data loaders for all states.

    USE WITH CAUTION!
    """
    command = 'python batch_sf_everything.py %s %s' % (env.settings, fake)
    loader_log = '%s/census.load.everything.log' % (env.log_path)
    run_unattended_batch_command(command, loader_log)

def batch_test():
    """
    Kick off the test data loader.

    USE WITH CAUTION!
    """
    loader_log = '%(log_path)s/census.load.test.log' % env
    run_unattended_batch_command('./batch_test.sh %s' % env.settings, loader_log)

def make_state_public(state):
    """
    Make a state's data public.
    """
    loader_log = '%(log_path)s/census.make_public.log' % env
    run_unattended_batch_command('python make_state_public.py %s %s' % (env.settings, state), loader_log)

"""
Commands - miscellaneous
"""
    
def clear_cache():
    """
    Restart memcache, wiping the current cache.
    """
    if env.multi_server:
        run('bounce-memcaches-for-cluster')
    else:
        sudo('service memcached restart')

    run('curl -X PURGE -H "Host: %(site_domain)s" http://%(cache_server)s/' % env)
    
def echo_host():
    """
    Echo the current host to the command line.
    """
    run('echo %(settings)s; echo %(hosts)s' % env)

"""
Deaths, destroyers of worlds
"""
def shiva_the_destroyer():
    """
    Remove all directories, databases, etc. associated with the application.
    """
    with settings(warn_only=True):
        run('rm -Rf %(path)s' % env)
        run('rm -Rf %(env_path)s' % env)
        pgpool_down()
        run('dropdb %(project_name)s' % env)
        run('dropuser %(project_name)s' % env)
        pgpool_up()
        sudo('rm %(apache_config_path)s' % env)
        reboot()
        run('s3cmd del --recursive s3://%(s3_bucket)s/' % env)

def local_shiva():
    destroy_database(local)

def local_bootstrap():
    create_database(local)

    # Normal bootstrap
    local('python manage.py syncdb --noinput')

def local_load_geodata():
    local('mkdir -p /tmp/geofetch')
    local('./fetch_geodata.sh /tmp/geofetch 10')
    local('cp data/shapefiles/definitions.py /tmp/geofetch')
    local('./manage.py load_shapefiles -c -d /tmp/geofetch')
    
"""
Utility functions (not to be called directly)
"""
def _execute_psql(query):
    """
    Executes a PostgreSQL command using the command line interface.
    """
    env.query = query
    run(('cd %(site_path)s; psql -q %(project_name)s -c "%(query)s"') % env)
    
def _confirm_branch():
    if (env.settings == 'production' and env.branch != 'stable'):
        answer = prompt("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env, default="Not at all")
        if answer not in ('y','Y','yes','Yes','buzz off','screw you'):
            exit()

########NEW FILE########
__FILENAME__ = gzip_assets
#!/usr/bin/env python

import os
import gzip
import shutil

class FakeTime:
    def time(self):
        return 1261130520.0

# Hack to override gzip's time implementation
# See: http://stackoverflow.com/questions/264224/setting-the-gzip-timestamp-from-python
gzip.time = FakeTime()

shutil.rmtree('gzip_media', ignore_errors=True)
shutil.copytree('media', 'gzip_media')

for path, dirs, files in os.walk('gzip_media'):
    for filename in files:
        file_path = os.path.join(path, filename)

        f_in = open(file_path, 'rb')
        contents = f_in.read()
        f_in.close()
        f_out = gzip.open(file_path, 'wb')
        f_out.write(contents)
        f_out.close();


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
from django.core.management import execute_manager

if not os.environ.has_key("DJANGO_SETTINGS_MODULE"):
    if not os.environ.has_key("DEPLOYMENT_TARGET"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    else:
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.%s.settings" % os.environ["DEPLOYMENT_TARGET"]

settings_module = os.environ["DJANGO_SETTINGS_MODULE"]

try:
    settings = __import__(settings_module, globals(), locals(), ['settings'], -1)
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file '%s.py'.\n" % settings_module)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = batch_sf_everything
#!/usr/bin/env python

import subprocess
import sys

from get_state_abbr import STATE_ABBRS

if len(sys.argv) > 1 and sys.argv[1] == 'FAKE':
    FAKE = 'FAKE'
else:
    FAKE = ''

for state in sorted(STATE_ABBRS.keys()):
    subprocess.call(['./batch_sf.sh', state, FAKE]) 


########NEW FILE########
__FILENAME__ = compute_deltas_sf
#!/usr/bin/env python

import sys

from pymongo import objectid

import utils

QUERY = {}

if len(sys.argv) > 1:
    QUERY = { 'sumlev': sys.argv[1] }

collection = utils.get_geography_collection()

row_count = 0
computations = 0

for geography in collection.find(QUERY, fields=['data']):
    row_count += 1

    if 'delta' not in geography['data']:
        geography['data']['delta'] = {} 

    if 'pct_change' not in geography['data']:
        geography['data']['pct_change'] = {}

    # Skip geographies which did not have data in 2000 (e.g. newly established places)
    if '2000' not in geography['data']:
        continue

    for table in geography['data']['2010']:
        # Skip tables with no equivalent in 2000
        if table not in geography['data']['2000']:
            continue

        if table not in geography['data']['delta']:
            geography['data']['delta'][table] = {}
        
        if table not in geography['data']['pct_change']:
            geography['data']['pct_change'][table] = {}

        for k, v in geography['data']['2010'][table].items():
            if k not in geography['data']['2000'][table]:
                continue

            value_2010 = float(v)
            value_2000 = float(geography['data']['2000'][table][k])

            if value_2000 == 0:
                continue

            geography['data']['delta'][table][k] = str(value_2010 - value_2000)
            geography['data']['pct_change'][table][k] = str((value_2010 - value_2000) / value_2000)

    collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'data': geography['data'] } }, safe=True)
    computations += 1

print ' Row count: %i' % row_count
print ' Computations: %i' % computations



########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python

# Geocomp value declaring a row is not a geographic compontent
GEOCOMP_COMPLETE = '00'

# Summary level constants
SUMLEV_NATION = '010'
SUMLEV_STATE = '040'
SUMLEV_COUNTY = '050'
SUMLEV_COUNTY_SUBDIVISION = '060'
SUMLEV_TRACT = '140'
SUMLEV_PLACE = '160'
SUMLEV_BLOCK = '101'

# Summary levels to load
SUMLEVS = [SUMLEV_NATION, SUMLEV_STATE, SUMLEV_COUNTY, SUMLEV_COUNTY_SUBDIVISION, SUMLEV_PLACE, SUMLEV_TRACT]

def filter_geographies(row_dict):
    """
    This callback gets fired for every geography that is loaded.

    The argument is a dictionary of columns from the geography
    headers file.

    If it returns true the geography will be loaded, otherwise
    it will be skipped.

    This is useful for limiting data to a county/city/whatever.
    """
    return True 

# Mongo
CENSUS_DB = 'census'
LABELS_DB = 'census_labels'
GEOGRAPHIES_COLLECTION = 'geographies'
GEOGRAPHIES_2000_COLLECTION = 'geographies_2000'
LABELS_COLLECTION = 'labels'

# S3
S3_BUCKETS = {
    'staging': 'census-test',
    'production': 'censusdata.ire.org',
}

########NEW FILE########
__FILENAME__ = create_custom_sumlev
#!/usr/bin/env python

"""
Script for generating custom summary levels:

Note: You must have already run batch_sf.sh before using this script. If you want
to aggregate blocks (the normal case), you'll need to have added SUMLEV_BLOCK to
SUMLEVS in config.py before running the batch.

Aggregate geoids (usually of blocks) to a custom summary level, such as wards,
community areas, or neighborhoods. Takes a CSV mapping existing census geoids to
new features ID as an input. Example:

    150030084051004,1
    150030101004058,1
    150030102013031,2

In this case the first two blocks would be rolled up to form a new feature
with a unique id of "1". The third block would be copied into a new feature
with a unique id of "2".

A name must also be provided for the new summary level, this will also be
prefixed to each new geoid in order to prevent namespace collisions with
existing census geographies. For example, if the new summary level had been
named "test" in the previous example, then the newly created geographies
would have had geoids of "test_1" and "test_2".

Example usage:

    python create_custom_sumlev.py mapping_2000.csv sumlev_name 2000
    python create_custom_sumlev.py mapping_2010.csv sumlev_name 2010

Once this script has been run you can rerun the crosswalk and delta computation
scripts for only the new summary level:

    python crosswalk.py test
    python compute_deltas_sf.py test
"""

import csv
import sys

import utils

def make_custom_geoid(sumlev, feature_id):
    """
    Generate a unique geoid for the given feature.
    """
    return '%s_%s' % (sumlev, feature_id)

def create_custom_sumlev(collection, filename, new_sumlev, year):
    """
    Create a custom summary level by aggregating blocks
    according to a pre-generated mapping.
    """
    # Destroy any previous aggregations for this summary level
    collection.remove({ 'sumlev': new_sumlev }, safe=True)

    count_allocated = 0
    count_new_features = 0

    mapping = csv.reader(open(filename, 'rU'))

    for row in mapping:
        geoid, feature_id = row

        new_geoid = make_custom_geoid(new_sumlev, feature_id)

        old_geography = collection.find_one({ 'geoid': geoid })
        new_geography = collection.find_one({ 'geoid': new_geoid })

        # Create an aggregating geography if it doesn't exist
        if not new_geography:
            new_geography = {
                'sumlev': new_sumlev,
                'geoid': new_geoid,
                'metadata': {
                    'NAME': str(feature_id),
                },
                'data': {
                    year: {},
                }
            }

            count_new_features += 1
            
        # Update new geography with values from constituent block
        for table in old_geography['data'][year]:
            if table not in new_geography['data'][year]:
                new_geography['data'][year][table] = {}

            for field, value in old_geography['data'][year][table].items():
                if field not in new_geography['data'][year][table]:
                    new_geography['data'][year][table][field] = 0

                new_geography['data'][year][table][field] = float(new_geography['data'][year][table][field]) + float(value)

        collection.save(new_geography, safe=True) 

        count_allocated += 1

    print 'Allocated: %i' % count_allocated
    print 'New Features: %i' % count_new_features

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit('You must provide the filename of a CSV mapping census geoids to new unique feature ids and name for the new summary level and a year.')

    filename = sys.argv[1]
    new_sumlev = sys.argv[2]
    year = sys.argv[3]

    if year == '2010':
        collection = utils.get_geography_collection()
    elif year == '2000':
        collection = utils.get_geography2000_collection()
    else:
        sys.exit('Invalid year: "%s"' % year)

    create_custom_sumlev(collection, filename, new_sumlev, year)


########NEW FILE########
__FILENAME__ = crosswalk
#!/usr/bin/env python

import csv
import sys

from pymongo import objectid

import config
import utils

QUERY = {}

if len(sys.argv) > 1:
    QUERY = { 'sumlev': sys.argv[1] }

collection = utils.get_geography_collection()
collection_2000 = utils.get_geography2000_collection()

row_count = 0
inserts = 0

KEY_MAPPINGS = {}
CROSSWALK_FIELDS_BY_TABLE = {}

# Maps 2010 field names to their 2000 equivalents
with open('field_mappings_2000_2010.csv', 'rU') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # Skip fields that don't map
        if not row['field_2000'].strip():
            continue

        if not row['field_2010'].strip():
            continue

        # TODO - skipping computed fields
        if '-' in row['field_2000'] or '+' in row['field_2000']:
            continue

        if '-' in row['field_2010'] or '+' in row['field_2010']:
            continue

        # Fields in 2000 may map to multiple fields in 2010 (e.g. P001001 -> P001001 and P004001)
        if row['field_2000'] not in KEY_MAPPINGS:
            KEY_MAPPINGS[row['field_2000']] = []

        KEY_MAPPINGS[row['field_2000']].append(row['field_2010'])

# Load crosswalk lookup table
with open('sf_crosswalk_key.csv') as f:
    reader = csv.reader(f)

    for row in reader:
        CROSSWALK_FIELDS_BY_TABLE[row[0]] = row[1]

for geography in collection.find(QUERY, fields=['data', 'geoid', 'metadata.NAME', 'sumlev', 'xwalk']):
    row_count += 1
    
    data = {}

    # TRACTS & BLOCKS - require true crosswalk
    if geography['sumlev'] in [config.SUMLEV_TRACT, config.SUMLEV_BLOCK]:
        geography_2000s = list(utils.find_geographies_for_xwalk(collection_2000, geography, fields=['data', 'geoid']))

        # Tract is new
        if not geography_2000s:
            continue

        for table in geography_2000s[0]['data']['2000']:
            crosswalk_field = CROSSWALK_FIELDS_BY_TABLE[table]

            # Table contains medians or other values that can't be crosswalked
            if not crosswalk_field:
                continue

            for k, v in geography_2000s[0]['data']['2000'][table].items():
                try:
                    keys_2010 = KEY_MAPPINGS[k]
                except KeyError:
                    # Skip 2000 fields that don't exist in 2010
                    continue

                # Skip 2000 fields that don't have an equivalent in 2010
                if not keys_2010:
                    continue

                # Copy value to all 2010 fields which are comparable to this field in 2000
                for key_2010 in keys_2010:
                    table_2010 = utils.parse_table_from_key(key_2010)

                    if table_2010 not in data:
                        data[table_2010] = {}

                    parts = []

                    for g in geography_2000s:
                        value = float(g['data']['2000'][table][k])
                        pct = geography['xwalk'][g['geoid']][crosswalk_field]

                        parts.append(value * pct)

                    data[table_2010][key_2010] = int(sum(parts))

    # OTHER SUMLEVS - can be directly compared by geoid
    else:
        geography_2000 = collection_2000.find_one({ 'geoid': geography['geoid'] }, fields=['data'])

        if not geography_2000:
            print 'Couldn\'t find matching 2000 geography for %s' % (geography['geoid'])

            continue

        for table in geography_2000['data']['2000']:
            for k, v in geography_2000['data']['2000'][table].items():
                try:
                    keys_2010 = KEY_MAPPINGS[k]
                except KeyError:
                    # Skip 2000 fields that don't exist in 2010
                    continue

                # Skip 2000 fields that don't have an equivalent in 2010
                if not keys_2010:
                    continue

                # Copy value to all 2010 fields which are comparable to this field in 2000
                for key_2010 in keys_2010:
                    table_2010 = utils.parse_table_from_key(key_2010)

                    if table_2010 not in data:
                        data[table_2010] = {}

                    parts = []

                    data[table_2010][key_2010] = geography_2000['data']['2000'][table][k] 

    geography['data']['2000'] = data

    collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'data': geography['data'] } }, safe=True)
    inserts += 1

print ' Row count: %i' % row_count
print ' Inserted: %i' % inserts


########NEW FILE########
__FILENAME__ = deploy_csv
#!/usr/bin/env python
"""
If data for a state is loaded into the Mongo DB (as in during the normal data processing pipeline), this script
can generate CSV exports collecting data for a specific SF1 table for all geographies of a given SUMLEV for a state.
Normally writes directly to S3, but is factored so that it shouldn't be hard to use to generate files on a local
file system.
"""
import sys

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from cStringIO import StringIO

import config
import utils
import gzip

import eventlet
eventlet.monkey_patch()

from csvkit.unicsv import UnicodeCSVWriter

POLICIES = ['public-read', 'private'] # should we add others?

def get_2000_top_level_counts(geography):
    try:
        pop2000 = geography['data']['2000']['P1']['P001001']
        hu2000 = geography['data']['2000']['H1']['H001001']
        return pop2000,hu2000
    except KeyError:
        return '',''
METADATA_HEADERS = ['STATE','COUNTY', 'CBSA', 'CSA', 'NECTA', 'CNECTA', 'NAME', 'POP100', 'HU100']

def deploy_table(state_fips, sumlev, table_id, policy='private'):

    if policy not in POLICIES:
        policy = 'private'
    s = StringIO()
    gz = gzip.GzipFile(fileobj=s, mode='wb')
    write_table_data(gz,state_fips,sumlev, table_id)
    gz.close()
    tokens = {'sumlev': sumlev, 'state': state_fips, 'table_id': table_id }
    c = S3Connection()
    bucket = c.get_bucket(config.S3_BUCKETS[ENVIRONMENT])
    k = Key(bucket)
    k.key = '%(state)s/all_%(sumlev)s_in_%(state)s.%(table_id)s.csv' % (tokens)
    k.set_contents_from_string(s.getvalue(), headers={ 'Content-encoding': 'gzip', 'Content-Type': 'text/csv' }, policy=policy)
    print "S3: wrote ",k.key," to ", ENVIRONMENT, " using policy ", policy

def write_table_data(flo, state_fips, sumlev, table_id):
    """Given a File-Like Object, write a table to it"""
    w = UnicodeCSVWriter(flo)

    metadata = fetch_table_label(table_id)

    header = ['GEOID', 'SUMLEV'] + METADATA_HEADERS + ['POP100.2000','HU100.2000']
    for key in sorted(metadata['labels']):
        header.extend([key,"%s.2000" % key])
    w.writerow(header)

    query = {'sumlev': sumlev, 'metadata.STATE': state_fips }
    collection = utils.get_geography_collection()
    for geography in collection.find(query):
        row = [geography['geoid'],geography['sumlev']]

        for h in METADATA_HEADERS:
            row.append(geography['metadata'][h])

        pop2000,hu2000 = get_2000_top_level_counts(geography)
        row.extend([pop2000,hu2000])

        for key in sorted(metadata['labels']):
            try:
                row.append(geography['data']['2010'][table_id][key])
            except KeyError, e:
                if table_id.startswith('PCO'):
                    print "No data for %s at %s" % (table_id, sumlev)
                    return
                raise e # don't otherwise expect this error, so raise it...
            try:
                row.append(geography['data']['2000'][table_id][key])
            except KeyError:
                row.append('')
        w.writerow(row)
    

def fetch_tables_and_labels():
    lc = utils.get_label_collection()
    return lc.find_one({'dataset': 'SF1'},fields=['tables'])['tables']

def fetch_table_label(table_id):
    return fetch_tables_and_labels()[table_id]

# BEGIN MAIN OPERATION
if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('You must specify 3 or 4 arguments to this script.\n%% %s [2 digit state FIPS code] [3 digit summary level] [staging|production] [policy (opt string default \'private\')]' % sys.argv[0])

    STATE_FIPS = sys.argv[1]
    SUMLEV = sys.argv[2]
    ENVIRONMENT = sys.argv[3]
    try:
        policy = sys.argv[4]
        if policy not in POLICIES:
            policy = 'private'
    except:
        policy='private'

    if SUMLEV not in config.SUMLEVS:
        sys.exit("Second argument must be a valid summary level as defined in config.SUMLEVS")

    # TODO 
    # this needs to be findable... ${DATAPROCESSING_DIR}/sf1_2010_data_labels.csv
    # reduce duplication between make_sf_data_2010_headers.py and utils.py
    # import a padded_label from utils... 
    tables = fetch_tables_and_labels()

    # non-eventlety
    for table_id in sorted(tables):
        deploy_table(STATE_FIPS, SUMLEV, table_id,policy)
        
    # eventlety
    # pile = eventlet.GreenPile(64)
    # for table_id in sorted(tables):
    #     pile.spawn(deploy_table, STATE_FIPS, SUMLEV, table_id,policy)
    # # Wait for all greenlets to finish
    # list(pile)

########NEW FILE########
__FILENAME__ = deploy_data
#!/usr/bin/env python

import json
import sys

from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config
import utils

POLICIES = ['public-read', 'private'] # should we add others?
if len(sys.argv) < 2:
    sys.exit('You must specify "staging" or "production" as an argument to this script. You may optionally specify an S3 policy as the next arg')

ENVIRONMENT = sys.argv[1]

try:
    policy = sys.argv[2]
except:
    policy='private'

if policy not in POLICIES:
    print "invalid policy option; using 'private'"
    policy = 'private'


collection = utils.get_geography_collection()

row_count = 0
deployed = 0

c = S3Connection()
bucket = c.get_bucket(config.S3_BUCKETS[ENVIRONMENT])

for geography in collection.find():
    row_count += 1

    del geography['_id']

    k = Key(bucket)
    k.key = '%s/%s.jsonp' % (geography['metadata']['STATE'], geography['geoid'])
    jsonp = 'geoid_%s(%s)' % (geography['geoid'], json.dumps(geography))
    compressed = utils.gzip_data(jsonp)

    k.set_contents_from_string(compressed, headers={ 'Content-encoding': 'gzip', 'Content-Type': 'application/javascript' }, policy=policy)

    if row_count % 100 == 0:
        print ' Deployed %i...' % row_count

    deployed += 1

print '  Row count: %i' % row_count
print '  Deployed: %i' % deployed


########NEW FILE########
__FILENAME__ = deploy_labels
#!/usr/bin/env python

import json
import sys

from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must specify "staging" or "production" as an argument to this script.')

ENVIRONMENT = sys.argv[1]

collection = utils.get_label_collection()

row_count = 0
deployed = 0

c = S3Connection()
bucket = c.get_bucket(config.S3_BUCKETS[ENVIRONMENT])

for dataset in collection.find():
    row_count += 1

    del dataset['_id']

    print dataset['dataset']

    k = Key(bucket)
    k.key = '%s_labels.jsonp' % dataset['dataset']
    jsonp = 'labels_%s(%s)' % (dataset['dataset'], json.dumps(dataset))
    compressed = utils.gzip_data(jsonp)

    k.set_contents_from_string(compressed, headers={ 'Content-encoding': 'gzip', 'Content-Type': 'application/json' }, policy='public-read')

    deployed += 1

print 'deploy_labels:'
print ' Row count: %i' % row_count
print ' Deployed: %i' % deployed


########NEW FILE########
__FILENAME__ = deploy_lookups
#!/usr/bin/env python

import json
import sys

from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must specify "staging" or "production" as an argument to this script.')

ENVIRONMENT = sys.argv[1]

collection = utils.get_geography_collection()

row_count = 0
deployed = 0

c = S3Connection()
bucket = c.get_bucket(config.S3_BUCKETS[ENVIRONMENT])

def push(state, slug, obj):
    k = Key(bucket)
    k.key = '%s/%s.jsonp' % (state, slug)
    data = json.dumps(obj)
    jsonp = '%s(%s)' % (slug, data) 
    compressed = utils.gzip_data(jsonp)

    k.set_contents_from_string(compressed, headers={ 'Content-encoding': 'gzip', 'Content-Type': 'application/javascript' }, policy='public-read')

state = collection.find_one()['metadata']['STATE']

print 'Deploying counties lookup'
counties = collection.find({ 'sumlev': config.SUMLEV_COUNTY }, fields=['geoid', 'metadata.NAME', 'metadata.COUNTY'], sort=[('metadata.NAME', 1)]) 
counties = [(c['metadata']['NAME'], c['geoid']) for c in counties]
push(state, 'counties', counties)

print 'Deploying county subdivisions lookup'
county_subdivisions = collection.find({ 'sumlev': config.SUMLEV_COUNTY_SUBDIVISION }, fields=['geoid', 'metadata.NAME', 'metadata.COUNTY_SUBDIVISION'], sort=[('metadata.NAME', 1)]) 
county_subdivisions = [(c['metadata']['NAME'], c['geoid']) for c in county_subdivisions]
push(state, 'county_subdivisions', county_subdivisions)

print 'Deploying places lookup'
places = collection.find({ 'sumlev': config.SUMLEV_PLACE }, fields=['geoid', 'metadata.NAME'], sort=[('metadata.NAME', 1)]) 
places = [(c['metadata']['NAME'], c['geoid']) for c in places]
push(state, 'places', places)

counties = collection.find({ 'sumlev': config.SUMLEV_COUNTY }, fields=['geoid', 'metadata.NAME', 'metadata.COUNTY'], sort=[('metadata.NAME', 1)]) 

print 'Deploying tracts lookup'
tracts = collection.find({ 'sumlev': config.SUMLEV_TRACT }, fields=['geoid', 'metadata.NAME'], sort=[('metadata.NAME', 1)]) 
tracts = [(c['metadata']['NAME'], c['geoid']) for c in tracts]
push(state, 'tracts', tracts)

counties = collection.find({ 'sumlev': config.SUMLEV_COUNTY }, fields=['geoid', 'metadata.NAME', 'metadata.COUNTY'], sort=[('metadata.NAME', 1)]) 

for county in counties:
    print 'Deploying county subdivisions lookup for %s' % county['geoid']
    county_subdivisions = collection.find({ 'sumlev': config.SUMLEV_COUNTY_SUBDIVISION, 'metadata.COUNTY': county['metadata']['COUNTY'] }, fields=['geoid', 'metadata.NAME', 'metadata.COUNTY_SUBDIVISION'], sort=[('metadata.NAME', 1)]) 
    county_subdivisions = [(c['metadata']['NAME'], c['geoid']) for c in county_subdivisions]
    push(state, 'county_subdivisions_%s' % county['geoid'], county_subdivisions)

    print 'Deploying tracts lookup for %s' % county['geoid']
    tracts = collection.find({ 'sumlev': config.SUMLEV_TRACT, 'metadata.COUNTY': county['metadata']['COUNTY'] }, fields=['geoid', 'metadata.NAME'], sort=[('metadata.NAME', 1)]) 
    tracts = [(c['metadata']['NAME'], c['geoid']) for c in tracts]
    push(state, 'tracts_%s' % county['geoid'], tracts)


########NEW FILE########
__FILENAME__ = get_state_abbr
#!/usr/bin/env python

import sys

STATE_ABBRS = {
    'Alabama': 'al',
    'Alaska': 'ak',
    'Arizona': 'az',
    'Arkansas': 'ar',
    'California': 'ca',
    'Colorado': 'co',
    'Connecticut': 'ct',
    'Delaware': 'de',
    'District of Columbia': 'dc',
    'Florida': 'fl',
    'Georgia': 'ga',
    'Hawaii': 'hi',
    'Idaho': 'id',
    'Illinois': 'il',
    'Indiana': 'in',
    'Iowa': 'ia',
    'Kansas': 'ks',
    'Kentucky': 'ky',
    'Louisiana': 'la',
    'Maine': 'me',
    'Maryland': 'md',
    'Massachusetts': 'ma',
    'Michigan': 'mi',
    'Minnesota': 'mn',
    'Mississippi': 'ms',
    'Missouri': 'mo',
    'Montana': 'mt',
    'Nebraska': 'ne',
    'Nevada': 'nv',
    'New Hampshire': 'nh',
    'New Jersey': 'nj',
    'New Mexico': 'nm',
    'New York': 'ny',
    'North Carolina': 'nc',
    'North Dakota': 'nd',
    'Ohio': 'oh',
    'Oklahoma': 'ok',
    'Oregon': 'or',
    'Pennsylvania': 'pa',
    'Puerto Rico': 'pr',
    'Rhode Island': 'ri',
    'South Carolina': 'sc',
    'South Dakota': 'sd',
    'Tennessee': 'tn',
    'Texas': 'tx',
    'Utah': 'ut',
    'Vermont': 'vt',
    'Virginia': 'va',
    'Washington': 'wa',
    'West Virginia': 'wv',
    'Wisconsin': 'wi',
    'Wyoming': 'wy'
}

if __name__ == "__main__":
    print STATE_ABBRS[sys.argv[1]]

########NEW FILE########
__FILENAME__ = get_state_fips
#!/usr/bin/env python

import sys 

STATE_FIPS = {
    'Alabama': '01',
    'Alaska': '02',
    'Arizona': '04',
    'Arkansas': '05',
    'California': '06',
    'Colorado': '08',
    'Connecticut': '09',
    'Delaware': '10',
    'District of Columbia': '11',
    'Florida': '12',
    'Georgia': '13',
    'Hawaii': '15',
    'Idaho': '16',
    'Illinois': '17',
    'Indiana': '18',
    'Iowa': '19',
    'Kansas': '20',
    'Kentucky': '21',
    'Louisiana': '22',
    'Maine': '23',
    'Maryland': '24',
    'Massachusetts': '25',
    'Michigan': '26',
    'Minnesota': '27',
    'Mississippi': '28',
    'Missouri': '29',
    'Montana': '30',
    'Nebraska': '31',
    'Nevada': '32',
    'New Hampshire': '33',
    'New Jersey': '34',
    'New Mexico': '35',
    'New York': '36',
    'North Carolina': '37',
    'North Dakota': '38',
    'Ohio': '39',
    'Oklahoma': '40',
    'Oregon': '41',
    'Pennsylvania': '42',
    'Puerto Rico': '72',
    'Rhode Island': '44',
    'South Carolina': '45',
    'South Dakota': '46',
    'Tennessee': '47',
    'Texas': '48',
    'Utah': '49',
    'Vermont': '50',
    'Virginia': '51',
    'Washington': '53',
    'West Virginia': '54',
    'Wisconsin': '55',
    'Wyoming': '56'
}        

if __name__ == "__main__":
    print STATE_FIPS[sys.argv[1]]

########NEW FILE########
__FILENAME__ = load_crosswalk
#!/usr/bin/env python

import sys

from csvkit.unicsv import UnicodeCSVReader
from pymongo import objectid

import utils

if len(sys.argv) < 2:
    sys.exit('You must provide a state fips code and the filename of a CSV as an argument to this script.')

STATE_FIPS = sys.argv[1]
FILENAME = sys.argv[2]

collection = utils.get_geography_collection()

inserts = 0
row_count = 0

# Create dummy 2000->2010 crosswalk
if FILENAME == 'FAKE':
    for geography in collection.find({}, fields=['geoid', 'xwalk']):
        if 'xwalk' not in geography:
            geography['xwalk'] = {} 

        geography['xwalk'][geography['geoid']] = {
            'POPPCT00': 1.0,
            'HUPCT00': 1.0
        }

        collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'xwalk': geography['xwalk'] } }, safe=True) 
        row_count += 1
        inserts += 1
else:
    with open(FILENAME) as f:
        rows = UnicodeCSVReader(f)
        headers = rows.next()

        for row in rows:
            row_count += 1
            row_dict = dict(zip(headers, row))

            if row_dict['STATE10'] != STATE_FIPS:
                continue
            
            geography = collection.find_one({ 'geoid': row_dict['GEOID10'] }, fields=['xwalk'])

            if not geography:
                continue

            pop_pct_2000 = float(row_dict['POPPCT00']) / 100
            house_pct_2000 = float(row_dict['HUPCT00']) / 100

            if 'xwalk' not in geography:
                geography['xwalk'] = {} 

            geography['xwalk'][row_dict['GEOID00']] = {
                'POPPCT00': pop_pct_2000,
                'HUPCT00': house_pct_2000
            }

            collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'xwalk': geography['xwalk'] } }, safe=True) 
            inserts += 1

print "State: %s" % STATE_FIPS
print "File: %s" % FILENAME
print ' Row count: %i' % row_count
print ' Inserted: %i' % inserts


########NEW FILE########
__FILENAME__ = load_crosswalk_blocks
#!/usr/bin/env python

import sys

from csvkit.unicsv import UnicodeCSVReader
from pymongo import objectid

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must provide a state fips code and the filename of a CSV as an argument to this script.')

STATE_FIPS = sys.argv[1]
FILENAME = sys.argv[2]

collection = utils.get_geography_collection()

inserts = 0
row_count = 0

if config.SUMLEV_BLOCK not in config.SUMLEVS:
    print 'Skipping block crosswalk.'
    sys.exit()

with open(FILENAME) as f:
    rows = UnicodeCSVReader(f)
    headers = rows.next()

    for row in rows:
        row_count += 1
        row_dict = dict(zip(headers, row))

        geoid00 = ''.join([
            row_dict['STATE_2000'].rjust(2, '0'),
            row_dict['COUNTY_2000'].rjust(3, '0'),
            row_dict['TRACT_2000'].rjust(6, '0'),
            row_dict['BLK_2000'].rjust(4, '0')
            ])
        geoid10 = ''.join([
            row_dict['STATE_2010'].rjust(2, '0'),
            row_dict['COUNTY_2010'].rjust(3, '0'),
            row_dict['TRACT_2010'].rjust(6, '0'),
            row_dict['BLK_2010'].rjust(4, '0')
            ])

        geography = collection.find_one({ 'geoid': geoid10 }, fields=['xwalk'])

        if not geography:
            continue

        if row_dict['AREALAND_INT'] == '0':
            pct = 0
        else:
            pct = float(row_dict['AREALAND_INT']) / float(row_dict['AREALAND_2000'])

        #pop_pct_2000 = float(row_dict['POPPCT00']) / 100
        #house_pct_2000 = float(row_dict['HUPCT00']) / 100

        if 'xwalk' not in geography:
            geography['xwalk'] = {} 

        geography['xwalk'][geoid00] = {
            'POPPCT00': pct,
            'HUPCT00': pct
        }

        collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'xwalk': geography['xwalk'] } }, safe=True) 
        inserts += 1

print "State: %s" % STATE_FIPS
print "File: %s" % FILENAME
print ' Row count: %i' % row_count
print ' Inserted: %i' % inserts


########NEW FILE########
__FILENAME__ = load_sf_data_2000
#!/usr/bin/env python

import re
import sys

from csvkit.unicsv import UnicodeCSVReader
from pymongo import objectid

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must provide the filename of a CSV as an argument to this script.')

FILENAME = sys.argv[1]

YEAR = '2000'

collection = utils.get_geography2000_collection()

with open(FILENAME) as f:
    rows = UnicodeCSVReader(f)
    headers = rows.next()

    updates = 0
    row_count = 0

    for row in rows:
        row_count += 1
        row_dict = dict(zip(headers, row))

        xref = utils.xref_from_row_dict(row_dict)

        geography = utils.find_geography_by_xref(collection, xref) 
        if not geography:
            continue

        if YEAR not in geography['data']:
            geography['data'][YEAR] = {}

        tables = {}

        for k, v in row_dict.items():
            # Format table names to match labels
            t = utils.parse_table_from_key(k) 

            if t not in tables:
                tables[t] = {}

            tables[t][k] = v

        for k, v in tables.items():
            geography['data'][YEAR][k] = v 

        collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'data': geography['data'] } }, safe=True)
        updates += 1

print "File: %s" % FILENAME
print ' Row count: %i' % row_count
print ' Updated: %i' % updates


########NEW FILE########
__FILENAME__ = load_sf_data_2010
#!/usr/bin/env python

import sys

from csvkit.unicsv import UnicodeCSVReader
from pymongo import objectid 

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must provide the filename of a CSV as an argument to this script.')

FILENAME = sys.argv[1]

YEAR = '2010'

collection = utils.get_geography_collection()

with open(FILENAME) as f:
    rows = UnicodeCSVReader(f)
    headers = rows.next()

    updates = 0
    row_count = 0

    for row in rows:
        row_count += 1
        row_dict = dict(zip(headers, row))

        xref = utils.xref_from_row_dict(row_dict)

        geography = utils.find_geography_by_xref(collection, xref, fields=['data']) 
        if not geography:
            continue

        if YEAR not in geography['data']:
            geography['data'][YEAR] = {}

        tables = {}

        for k, v in row_dict.items():
            # Format table names to match labels
            t = utils.parse_table_from_key(k) 
            
            if t not in tables:
                tables[t] = {}

            tables[t][k] = v

        for k, v in tables.items():
            geography['data'][YEAR][k] = v 

        collection.update({ '_id': objectid.ObjectId(geography['_id']) }, { '$set': { 'data': geography['data'] } }, safe=True)
        updates += 1

print "File: %s" % FILENAME
print ' Row count: %i' % row_count
print ' Updated: %i' % updates


########NEW FILE########
__FILENAME__ = load_sf_geographies_2000
#!/usr/bin/env python

import sys

from csvkit.unicsv import UnicodeCSVReader

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must provide the filename of a CSV as an argument to this script.')

FILENAME = sys.argv[1]

collection = utils.get_geography2000_collection()

with open(FILENAME) as f:
    rows = UnicodeCSVReader(f)
    headers = rows.next()

    inserts = 0
    updates = 0
    row_count = 0

    for row in rows:
        row_count += 1

        geography = {
            #'sumlev': '',
            #'geoid': '',
            #'metadata': {},
            #'xrefs': [],
            #'data': {}
            #'xwalk': {}
        }
        row_dict = dict(zip(headers, row))

        if row_dict['SUMLEV'] not in config.SUMLEVS:
            continue

        if row_dict['GEOCOMP'] != config.GEOCOMP_COMPLETE:
            continue

        if not config.filter_geographies(row_dict):
            continue

        geography['sumlev'] = row_dict.pop('SUMLEV')
        geography['geoid'] = utils.GEOID_COMPUTERS[geography['sumlev']](row_dict)

        xref = utils.xref_from_row_dict(row_dict) 

        existing = collection.find_one(geography)
        if existing:
            if xref not in existing['xrefs']:
                existing['xrefs'].append(xref)
                collection.save(existing)

                updates += 1

            continue

        geography['xrefs'] = [xref]
        geography['data'] = {}
        geography['metadata'] = row_dict

        collection.save(geography, safe=True)
        inserts += 1

print 'File: %s' % FILENAME
print ' Row count: %i' % row_count
print ' Inserted: %i' % inserts
print ' Updated: %i' % updates


########NEW FILE########
__FILENAME__ = load_sf_geographies_2010
#!/usr/bin/env python

import sys

from csvkit.unicsv import UnicodeCSVReader

import config
import utils

if len(sys.argv) < 2:
    sys.exit('You must provide the filename of a CSV as an argument to this script.')

FILENAME = sys.argv[1]

collection = utils.get_geography_collection()

with open(FILENAME) as f:
    rows = UnicodeCSVReader(f)
    headers = rows.next()

    inserts = 0
    updates = 0
    row_count = 0

    for row in rows:
        row_count += 1

        geography = {
            #'sumlev': '',
            #'geoid': '',
            #'metadata': {},
            #'xrefs': [],
            #'data': {}
            #'xwalk': {}
        }
        row_dict = dict(zip(headers, row))

        if row_dict['SUMLEV'] not in config.SUMLEVS:
            continue

        # Ignore that is not for complete geographies
        if row_dict['GEOCOMP'] != config.GEOCOMP_COMPLETE:
            continue

        if not config.filter_geographies(row_dict):
            continue

        geography['sumlev'] = row_dict.pop('SUMLEV')
        geography['geoid'] = utils.GEOID_COMPUTERS[geography['sumlev']](row_dict)

        xref = utils.xref_from_row_dict(row_dict) 

        existing = collection.find_one(geography)
        if existing:
            if xref not in existing['xrefs']:
                existing['xrefs'].append(xref)
                collection.save(existing)

                updates += 1

            continue

        geography['xrefs'] = [xref]
        geography['data'] = {}
        geography['metadata'] = row_dict

        collection.save(geography, safe=True)
        inserts += 1

print 'File: %s' % FILENAME
print ' Row count: %i' % row_count
print ' Inserted: %i' % inserts
print ' Updated: %i' % updates


########NEW FILE########
__FILENAME__ = load_sf_labels_2010
#!/usr/bin/env python

import csv
import re
import sys

from csvkit.unicsv import UnicodeCSVReader

import config, utils
import logging

TABLE_NAME_PATTERN = re.compile(r'^(?P<name>.+)\s+\[(?P<size>\d+)\].*$')


KEY_MAPPINGS = {}

with open('field_mappings_2000_2010.csv', 'rU') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # Skip fields that don't map
        if not row['field_2000']:
            continue

        if not row['field_2010']:
            continue

        # TODO - skipping computed fields
        if '-' in row['field_2000'] or '+' in row['field_2000']:
            continue

        if '-' in row['field_2010'] or '+' in row['field_2010']:
            continue

        KEY_MAPPINGS[row['field_2010']] = row['field_2000']

YEAR = '2010'

def is_skipworthy_row(row):
    chk = set(row)
    if len(chk) == 1 and '' in chk:
        return True
    if row[:3] == ['','',''] and row[3].startswith('NOTE'):
        return True
    if row[1] and not row[0]: # section header
        return True
    return False

def dictify_row(row):
    row = map(unicode.strip,row)
    if is_skipworthy_row(row): return None
    table_id, line, indent = row[0:3]
    continuation = not table_id and not line and not indent
    if table_id:
        if table_id.endswith('.'): table_id = table_id[:-1]
    if indent:
        indent = int(indent)
    if line:
        line = int(line)
    return { 
        'table_id': table_id,
        'line': line,
        'indent': indent,
        'labels': row[3:9],
        'continuation': continuation
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('You must provide the filename of a CSV as an argument to this script.')

    FILENAME = sys.argv[1]

    with open(FILENAME) as f:
        rows = UnicodeCSVReader(f, encoding='latin-1')
        headers = rows.next()

        inserts = 0
        row_count = 0
        skipped = 0

        table = None 
        tables = {}
        hierarchy = []
        last_key = ''
        last_indent = 0

        for row in rows:
            row_count += 1
            if not row: continue
            row = map(unicode.strip,row)
            row = dictify_row(row)
            if row:
                if row['continuation']:
                    idx = last_processed['indent'] + 1
                    fragment = row['labels'][idx]
                    last_processed['text'] += ' %s' % fragment
                    continue

                table = tables.setdefault(row['table_id'],{ 'key': row['table_id'], 'year': '2010', 'labels': {} })

                if not row['line']: # we probably have a table name or a universe
                    if row['labels'][0].startswith("Universe:"):
                        parts = row['labels'][0].split(":", 2)
                        table['universe'] = parts[1].strip()
                    else:
                        # we know that they have extra labels for "indents" for avg/median that we just want to skip
                        if not row['labels'][0].startswith('Average') and not row['labels'][0].startswith('Median'): 
                            match = TABLE_NAME_PATTERN.match(row['labels'][0])
                            if not match:
                                if not row['labels'][0]: continue
                                fix_row = rows.next()
                                dfr = dictify_row(fix_row)
                                row['labels'][0] += ' %s' % dfr['labels'][1]
                                match = TABLE_NAME_PATTERN.match(row['labels'][0])
                                if not match:
                                    logging.warn( "Expected a table name at row %i [%s]" % ( row_count, row['labels'][0]  ) )
                                    continue
                            name_dict = match.groupdict()
                            table['name'] = name_dict['name']
                            table['size'] = int(name_dict['size'])
                else: # there's a line number
                    key = utils.generate_stat_key(row['table_id'],row['line'])
                    parent = parent_key = None
                    if row['indent'] > 0:
                        chk_line = row['line']
                        while parent is None and chk_line > 1:
                            chk_line -= 1
                            parent_key = utils.generate_stat_key(row['table_id'],chk_line)
                            chk_parent = table['labels'][parent_key]
                            if chk_parent['indent'] == row['indent'] - 1:
                                parent = chk_parent
                                parent['has_children'] = True
                                parent_key = parent['key']

                    last_processed = {
                        'key': key,
                        'text': row['labels'][row['indent']],
                        'indent': row['indent'],
                        'parent': parent_key,
                        'has_children': False, #maybe! we'll reset this later in the loop if we discover otherwise. look up.
                        'key_2000': KEY_MAPPINGS[key] if key in KEY_MAPPINGS else None,
                    } # keep it around for later

                    table['labels'][key] = last_processed # but also save it...
    # Save final table
    # sanity check:
    for k,v in tables.items():
        if not k:
            print "still have an empty key!"
        else:    
            if k != v['key']:
                raise AssertionError("Keys don't match for k=%s" % k)
            try:
                if len(v['labels']) != v['size']:
                    raise AssertionError("Not enough labels for k=%s expected %i got %i" % (k,v['size'],len(v['labels'])))
            except KeyError:
                print "Unexpectedly missing size for table %s keys: %s" % (k, ','.join(v.keys()))

    collection = utils.get_label_collection()
    collection.remove({ 'dataset': 'SF1' }, safe=True)
    collection.save({ 'dataset': 'SF1', 'tables': tables}, safe=True)

    print 'load_sf_labels_2010:'
    print ' Row count: %i' % row_count
    print ' Skipped: %i' % skipped
    print ' Tables: %i' % len(tables)


########NEW FILE########
__FILENAME__ = make_sf_data_2010_headers
#!/usr/bin/env python

import csv
import re
import sys

import utils

TABLE_REGEX = re.compile('([A-Z]+)([0-9]+)([A-Z]?)')

FIXED_HEADERS = ['FILEID', 'STUSAB', 'CHARITER', 'CIFSN', 'LOGRECNO']

# Values are tuples of (first table in file, total number of data cells in file)
# The latter is for a sanity check
FILES_TO_FIRST_TABLE_MAP = {
    1: ('P1', 1),
    2: ('P2', 6),
    3: ('P3', 194),
    4: ('P10', 239),
    5: ('P15', 245),
    6: ('P31', 254),
    7: ('P50', 251),
    8: ('P12F', 253),
    9: ('P17B', 249),
    10: ('P29A', 252),
    11: ('P31A', 254),
    12: ('P34F', 251),
    13: ('P38F', 240),
    14: ('P39I', 20),
    15: ('PCT1', 251),
    16: ('PCT9', 59),
    17: ('PCT12', 209),
    18: ('PCT13', 188),
    19: ('PCT21', 216),
    20: ('PCT12A', 209),
    21: ('PCT12B', 209),
    22: ('PCT12C', 209),
    23: ('PCT12D', 209),
    24: ('PCT12E', 209),
    25: ('PCT12F', 209),
    26: ('PCT12G', 209),
    27: ('PCT12H', 209),
    28: ('PCT12I', 209),
    29: ('PCT12J', 209),
    30: ('PCT12K', 209),
    31: ('PCT12L', 209),
    32: ('PCT12M', 209),
    33: ('PCT12N', 209),
    34: ('PCT12O', 209),
    35: ('PCT13A', 245),
    36: ('PCT13F', 245),
    37: ('PCT19C', 237),
    38: ('PCT20F', 254),
    39: ('PCT22G', 63),
    40: ('PCO1', 234),
    41: ('PCO7', 156),
    42: ('H1', 1),
    43: ('H2', 6),
    44: ('H3', 249),
    45: ('H11G', 255),
    46: ('H17D', 126),
    47: ('HCT1', 74)
}

FIELD_INDEX = sys.argv[1]

current_file = 1
headers = []

with open(FIELD_INDEX, 'r') as f:
    rows = csv.reader(f)

    # burn headers
    rows.next()
    rows.next()
    rows.next()
    
    for row in rows:
        table_name = row[0]
        field_num = row[1]

        # Skip table header rows
        if not field_num or field_num.startswith('POPULATION SUBJECTS') or field_num.startswith('HOUSING SUBJECTS'):
            continue

        # Final table contains all remaining
        if current_file != 47:
            # Have we switched files?
            if table_name.strip('.') == FILES_TO_FIRST_TABLE_MAP[current_file + 1][0]:
                if len(headers) != FILES_TO_FIRST_TABLE_MAP[current_file][1]:
                    raise AssertionError('Only found %i/%i headers for file %i' % (len(headers), FILES_TO_FIRST_TABLE_MAP[current_file + 1][1], current_file))

                with open('sf_data_2010_headers_%i.csv' % current_file, 'w') as f:
                    f.write(','.join(FIXED_HEADERS))
                    f.write(',')
                    f.write(','.join(headers))
                    f.write('\n')
                
                current_file += 1
                headers = []

                print 'Switched to file %i at table %s' % (current_file, table_name)
        
        parts = TABLE_REGEX.match(table_name)

        key = utils.generate_stat_key(table_name,field_num)
        headers.append(key)

    # Write final file
    with open('sf_data_2010_headers_%i.csv' % current_file, 'w') as f:
        f.write(','.join(FIXED_HEADERS))
        f.write(',')
        f.write(','.join(headers))
        f.write('\n')


########NEW FILE########
__FILENAME__ = make_state_public
#!/usr/bin/env python

import sys

from boto.s3.connection import S3Connection

import config
import get_state_fips
import update_state_list

if len(sys.argv) < 3:
    sys.exit('You must "staging" or "production" and a state name as arguments to this script.')

ENVIRONMENT = sys.argv[1]
STATE = sys.argv[2]
STATE_FIPS = get_state_fips.STATE_FIPS[STATE]

c = S3Connection()
bucket = c.get_bucket(config.S3_BUCKETS[ENVIRONMENT])

for i, k in enumerate(bucket.list('%s/' % STATE_FIPS)):
    k.make_public()
    
    if i % 100 == 0:
        print 'Processed %i...' % i

# Update available states list 
update_state_list.update_state_list(ENVIRONMENT, STATE)

########NEW FILE########
__FILENAME__ = sf1_labels2csv
#!/usr/bin/env python

from pymongo import objectid 

from csvkit.unicsv import UnicodeCSVWriter

import sys
import re

import config
import utils

TABLE_CODE_PATTERN = re.compile('^(\D+)(\d+)(\D+)?$')

def compare_table_codes(a,b):
    a_type,a_number,a_subtype = TABLE_CODE_PATTERN.match(a).groups()
    b_type,b_number,b_subtype = TABLE_CODE_PATTERN.match(b).groups()
    a_number = int(a_number)
    b_number = int(b_number)
    if a_type != b_type:
        if a_type[0] != b_type[0]:
            return cmp(a_type[0],b_type[0]) * -1 # Sort P before H to match tech docs
        return cmp(a_type,b_type)
    if a_number != b_number:
        return cmp(a_number,b_number)
    return cmp(a_subtype,b_subtype)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('You must provide the filename for the CSV output as an argument to this script.')

    FILENAME = sys.argv[1]
    with open(FILENAME,"w") as f:
        collection = utils.get_label_collection()

        labelset = collection.find_one({ 'dataset': 'SF1' })

        w = UnicodeCSVWriter(f)
        w.writerow(['table_code','table_desc','table_universe','table_size','col_code','col_desc','indent','parent','has_children','col_code_2000'])
        for table_code in sorted(labelset['tables'],cmp=compare_table_codes):
            t = labelset['tables'][table_code]
            row_base = [table_code,t['name'],t['universe'],t['size']]
            for label_code in sorted(t['labels']):
                l = t['labels'][label_code]
                row = row_base[:]
                if l['parent'] is None: parent = ''
                else: parent = l['parent']
                if l['key_2000'] is None: key_2000 = ''
                else: key_2000 = l['key_2000']
                row.extend([l['key'],l['text'],l['indent'],parent,l['has_children'],key_2000])
                w.writerow(row)

########NEW FILE########
__FILENAME__ = tests_sf
#!/usr/bin/env python

from django.utils import unittest

import config
import utils

class TestSimpleGeographies(unittest.TestCase):
    def setUp(self):
        self.geographies = utils.get_geography_collection()

    def _test_totalpop(self, obj, known_2000, known_2010):
        """
        Shortcut to test "total population" field from the P1 (race)
        table since this table exists for both 2000 and 2010.
        """
        known_delta = known_2010 - known_2000
        known_pct = float(known_delta) / float(known_2000)

        self.assertEqual(float(obj['data']['2000']["P1"]['P001001']), known_2000)
        self.assertEqual(float(obj['data']['2010']["P1"]['P001001']), known_2010)
        self.assertEqual(float(obj['data']['delta']["P1"]['P001001']), known_delta)
        self.assertAlmostEqual(
            float(obj['data']['pct_change']["P1"]['P001001']),
            known_pct
        )

    def test_only_complete_geographies(self):
        geos = self.geographies.find({ 'metadata.GEOCOMP': { '$ne': '00' }})
        self.assertEqual(geos.count(), 0)

    def test_state_count(self):
        states = self.geographies.find({ 'sumlev': '040' })

        self.assertEqual(states.count(), 1)
    
    def test_state(self):
        """
        Data import test against known values that Hawaii should have.
        """
        states = self.geographies.find({ 'geoid': config.SUMLEV_STATE })

        self.assertEqual(states.count(), 1)

        state = states[0]

        self.assertEqual(state['sumlev'], config.SUMLEV_STATE)
        self.assertEqual(state['metadata']['NAME'], 'Hawaii')
        self.assertEqual(state['metadata']['STATE'], '15')

        pop_2000 = 1211537
        pop_2010 = 1360301
        self._test_totalpop(state, pop_2000, pop_2010)

    def test_county_count(self):
        counties = self.geographies.find({ 'sumlev': config.SUMLEV_COUNTY })

        self.assertEqual(counties.count(), 5)

    def test_county(self):
        """
        Data import test against known values that Maui County, HI should have.
        """
        counties = self.geographies.find({ 'geoid': '15009' })

        self.assertEqual(counties.count(), 1)

        county = counties[0]

        self.assertEqual(county['sumlev'], config.SUMLEV_COUNTY)
        self.assertEqual(county['metadata']['NAME'], 'Maui County')
        self.assertEqual(county['metadata']['STATE'], '15')
        self.assertEqual(county['metadata']['COUNTY'], '009')

        pop_2000 = 128094 
        pop_2010 = 154834
        self._test_totalpop(county, pop_2000, pop_2010)

    def test_county_subdivision_count(self):
        county_subdivisions = self.geographies.find({ 'sumlev': config.SUMLEV_COUNTY_SUBDIVISION })

        self.assertEqual(county_subdivisions.count(), 44)

    def test_county_subdivision(self):
        """
        Data import test against known values that Hilo CCD County Subdivision, HI should have.
        """
        counties = self.geographies.find({ 'geoid': '1500190630' })

        self.assertEqual(counties.count(), 1)

        county = counties[0]

        self.assertEqual(county['sumlev'], config.SUMLEV_COUNTY_SUBDIVISION)
        self.assertEqual(county['metadata']['NAME'], 'Hilo CCD')
        self.assertEqual(county['metadata']['STATE'], '15')
        self.assertEqual(county['metadata']['COUNTY'], '001')

        pop_2000 = 42425 
        pop_2010 = 45714 
        self._test_totalpop(county, pop_2000, pop_2010)

    def test_place_count(self):
        places = self.geographies.find({ 'sumlev': config.SUMLEV_PLACE })

        self.assertEqual(places.count(), 151)

    def test_place(self):
        """
        Data import test against known values that Pearl City CDP, HI should have.
        """
        places = self.geographies.find({ 'geoid': '1562600' })

        self.assertEqual(places.count(), 1)

        place = places[0]

        self.assertEqual(place['sumlev'], config.SUMLEV_PLACE)
        self.assertEqual(place['metadata']['NAME'], 'Pearl City CDP')
        self.assertEqual(place['metadata']['STATE'], '15')
        self.assertEqual(place['metadata']['PLACE'], '62600')

        pop_2000 = 30976
        pop_2010 = 47698 
        self._test_totalpop(place, pop_2000, pop_2010)

    def test_tract_count(self):
        tracts = self.geographies.find({ 'sumlev': config.SUMLEV_TRACT })

        self.assertEqual(tracts.count(), 351)

    def test_simple_tract(self): 
        """
        Data import test against known values that Tract 405, HI should have.
        """
        tracts = self.geographies.find({ 'geoid': '15007040500' })

        self.assertEqual(tracts.count(), 1)

        tract = tracts[0]

        self.assertEqual(tract['sumlev'], config.SUMLEV_TRACT)
        self.assertEqual(tract['metadata']['NAME'], 'Census Tract 405')
        self.assertEqual(tract['metadata']['STATE'], '15')
        self.assertEqual(tract['metadata']['COUNTY'], '007')

        pop_2000 = 5162 
        pop_2010 = 5943 
        self._test_totalpop(tract, pop_2000, pop_2010)

    def test_block_count(self):
        if config.SUMLEV_BLOCK not in config.SUMLEVS:
            pass
        
        blocks = self.geographies.find({ 'sumlev': config.SUMLEV_BLOCK })

        self.assertEqual(blocks.count(), 25016)

    def test_simple_block(self):
        """
        Data import test against known values for Block 3029 in Tract 210.05, HI.
        
        Note: The test block had the same geography but a different name in 2000.
        It was geoid 150010210011277 in that census.
        """
        if config.SUMLEV_BLOCK not in config.SUMLEVS:
            pass

        blocks = self.geographies.find({ 'geoid': '150010210053029' })

        self.assertEqual(blocks.count(), 1)

        block = blocks[0]

        self.assertEqual(block['sumlev'], config.SUMLEV_BLOCK)
        self.assertEqual(block['metadata']['NAME'], 'Block 3029')
        self.assertEqual(block['metadata']['STATE'], '15')
        self.assertEqual(block['metadata']['COUNTY'], '001')
        self.assertEqual(block['metadata']['TRACT'], '021005')

        pop_2000 = 33 
        pop_2010 = 93 
        self._test_totalpop(block, pop_2000, pop_2010)

class TestTracts(unittest.TestCase):
    def setUp(self):
        self.geographies = utils.get_geography_collection()

    def test_tract_split(self):
        """
        Verify that a split tract is crosswalked correctly.
        """
        # Check that split tract does not exist in 2010
        split_tract = self.geographies.find({ 'geoid': '15003003500' })
        self.assertEqual(split_tract.count(), 0)

        # Validate first new tract from the split tract
        # Tract 35.01
        tract1 = self.geographies.find({ 'geoid': '15003003501' })
        self.assertEqual(tract1.count(), 1)
        tract1 = tract1[0]
        
        split_tract_pop_2000 = 5834
        tract1_pop_pct = 0.3706 
        tract1_pop_2000 = int(tract1_pop_pct * split_tract_pop_2000)
        tract1_pop_2010 = 2282 
        tract1_pop_delta = tract1_pop_2010 - tract1_pop_2000
        tract1_pop_pct_change = float(tract1_pop_delta) / tract1_pop_2000

        self.assertAlmostEqual(tract1['xwalk']['15003003500']['POPPCT00'], tract1_pop_pct, places=4)
        self.assertAlmostEqual(tract1['data']['2000']['P1']['P001001'], tract1_pop_2000)
        self.assertAlmostEqual(float(tract1['data']['2010']['P1']['P001001']), tract1_pop_2010)
        self.assertAlmostEqual(float(tract1['data']['delta']['P1']['P001001']), tract1_pop_delta)
        self.assertAlmostEqual(float(tract1['data']['pct_change']['P1']['P001001']), tract1_pop_pct_change)
        
        # Validate second new part from the split tract
        # Tract 35.02
        tract2 = self.geographies.find({ 'geoid': '15003003502' })
        self.assertEqual(tract2.count(), 1)
        tract2 = tract2[0]

        tract2_pop_pct = 0.6294
        tract2_pop_2000 = int(tract2_pop_pct * split_tract_pop_2000)
        tract2_pop_2010 = 3876
        tract2_pop_delta = tract2_pop_2010 - tract2_pop_2000
        tract2_pop_pct_change = float(tract2_pop_delta) / tract2_pop_2000 
        
        self.assertAlmostEqual(tract2['xwalk']['15003003500']['POPPCT00'], tract2_pop_pct, places=4)
        self.assertAlmostEqual(tract2['data']['2000']['P1']['P001001'], tract2_pop_2000)
        self.assertAlmostEqual(float(tract2['data']['2010']['P1']['P001001']), tract2_pop_2010)
        self.assertAlmostEqual(float(tract2['data']['delta']['P1']['P001001']), tract2_pop_delta)
        self.assertAlmostEqual(float(tract2['data']['pct_change']['P1']['P001001']), tract2_pop_pct_change)

        # Verify that no other tracts got crosswalk allocations from the split tract
        allocated = self.geographies.find({ 'xwalk.15003003500': { '$exists': True } })
        self.assertEqual(allocated.count(), 2)

    def test_tract_split_housing(self):
        """
        Verify that a split tract is crosswalked correctly.
        """
        # Validate first new tract from the split tract
        # Tract 35.01
        tract1 = self.geographies.find({ 'geoid': '15003003501' })
        self.assertEqual(tract1.count(), 1)
        tract1 = tract1[0]
        
        split_tract_house_2000 = 3370 
        tract1_house_pct = 0.383 
        tract1_house_2000 = int(tract1_house_pct * split_tract_house_2000)
        tract1_house_2010 = 1353 
        tract1_house_delta = tract1_house_2010 - tract1_house_2000
        tract1_house_pct_change = float(tract1_house_delta) / tract1_house_2000

        self.assertAlmostEqual(tract1['xwalk']['15003003500']['HUPCT00'], tract1_house_pct, places=4)
        self.assertAlmostEqual(tract1['data']['2000']['H1']['H001001'], tract1_house_2000)
        self.assertAlmostEqual(float(tract1['data']['2010']['H1']['H001001']), tract1_house_2010)
        self.assertAlmostEqual(float(tract1['data']['delta']['H1']['H001001']), tract1_house_delta)
        self.assertAlmostEqual(float(tract1['data']['pct_change']['H1']['H001001']), tract1_house_pct_change)

        # Validate second new part from the split tract
        # Tract 35.02
        tract2 = self.geographies.find({ 'geoid': '15003003502' })
        self.assertEqual(tract2.count(), 1)
        tract2 = tract2[0]

        tract2_house_pct = 0.617
        tract2_house_2000 = int(tract2_house_pct * split_tract_house_2000)
        tract2_house_2010 = 2180 
        tract2_house_delta = tract2_house_2010 - tract2_house_2000
        tract2_house_pct_change = float(tract2_house_delta) / tract2_house_2000 
        
        self.assertAlmostEqual(tract2['xwalk']['15003003500']['HUPCT00'], tract2_house_pct, places=4)
        self.assertAlmostEqual(tract2['data']['2000']['H1']['H001001'], tract2_house_2000)
        self.assertAlmostEqual(float(tract2['data']['2010']['H1']['H001001']), tract2_house_2010)
        self.assertAlmostEqual(float(tract2['data']['delta']['H1']['H001001']), tract2_house_delta)
        self.assertAlmostEqual(float(tract2['data']['pct_change']['H1']['H001001']), tract2_house_pct_change)

    def test_tract_merged(self):
        """
        Verify that a merged tract is crosswalked correctly.

        TODO - test housing
        """
        # Verify that the first dissolved tract no longer exists
        tract1 = self.geographies.find({ 'geoid': '15003008607' })
        self.assertEqual(tract1.count(), 0)

        tract2 = self.geographies.find({ 'geoid': '15003008608' })
        self.assertEqual(tract2.count(), 0)

        tract3 = self.geographies.find({ 'geoid': '15003008500' })
        self.assertEqual(tract3.count(), 0)

        # Compute crosswalked values
        tract1_pop_2000 = 1544 
        tract2_pop_2000 = 0 
        tract3_pop_2000 = 1311
        merged_pop_2000 = tract1_pop_2000 # only this tract contributed population
        merged_pop_2010 = 5493 
        merged_pop_delta = merged_pop_2010 - merged_pop_2000
        merged_pop_pct_change = float(merged_pop_delta) / merged_pop_2000

        # Verify that the merged tract is correct
        merged_tract = self.geographies.find({ 'geoid': '15003011500' })
        self.assertEqual(merged_tract.count(), 1)        
        merged_tract = merged_tract[0]

        self.assertEqual(len(merged_tract['xwalk']), 3)
        self.assertEqual(merged_tract['xwalk']['15003008607']['POPPCT00'], 1.0)
        self.assertEqual(merged_tract['xwalk']['15003008608']['POPPCT00'], 1.0)
        self.assertEqual(merged_tract['xwalk']['15003008500']['POPPCT00'], 0.0)

        self.assertEqual(float(merged_tract['data']['2000']['P1']['P001001']), merged_pop_2000)
        self.assertEqual(float(merged_tract['data']['2010']['P1']['P001001']), merged_pop_2010)
        self.assertEqual(float(merged_tract['data']['delta']['P1']['P001001']), merged_pop_delta)
        self.assertAlmostEqual(float(merged_tract['data']['pct_change']['P1']['P001001']), merged_pop_pct_change)
        
        self.assertEqual(merged_tract['xwalk']['15003008607']['HUPCT00'], 1.0)
        self.assertEqual(merged_tract['xwalk']['15003008608']['HUPCT00'], 1.0)
        self.assertEqual(merged_tract['xwalk']['15003008500']['HUPCT00'], 0.0)

    def test_tract_complex_merge(self):
        # Verify state of 2010 status of tracts which contributed to the merged tract
        tract1 = self.geographies.find({ 'geoid': '15001021300' })
        self.assertEqual(tract1.count(), 1)

        tract2 = self.geographies.find({ 'geoid': '15001021400' })
        self.assertEqual(tract2.count(), 0)

        tract3 = self.geographies.find({ 'geoid': '15001021503' })
        self.assertEqual(tract3.count(), 0)

        # Compute crosswalked values
        tract1_house_2000 = 2269 
        tract1_house_2000_pct = 0.0065
        tract2_house_2000 = 1245
        tract2_house_2000_pct = 0.9938
        tract3_house_2000 = 2991
        tract3_house_2000_pct = 0.0351
        merged_house_2000 = int(sum([
            tract1_house_2000 * tract1_house_2000_pct,
            tract2_house_2000 * tract2_house_2000_pct,
            tract3_house_2000 * tract3_house_2000_pct
        ]))
        merged_house_2010 = 1586 
        merged_house_delta = merged_house_2010 - merged_house_2000
        merged_house_pct_change = float(merged_house_delta) / merged_house_2000

        # Verify that the merged tract is correct
        merged_tract = self.geographies.find({ 'geoid': '15001021402' })
        self.assertEqual(merged_tract.count(), 1)        
        merged_tract = merged_tract[0]

        self.assertEqual(len(merged_tract['xwalk']), 3)
        self.assertAlmostEqual(merged_tract['xwalk']['15001021300']['HUPCT00'], tract1_house_2000_pct)
        self.assertAlmostEqual(merged_tract['xwalk']['15001021400']['HUPCT00'], tract2_house_2000_pct)
        self.assertAlmostEqual(merged_tract['xwalk']['15001021503']['HUPCT00'], tract3_house_2000_pct)

        self.assertEqual(float(merged_tract['data']['2000']['H1']['H001001']), merged_house_2000)
        self.assertEqual(float(merged_tract['data']['2010']['H1']['H001001']), merged_house_2010)
        self.assertEqual(float(merged_tract['data']['delta']['H1']['H001001']), merged_house_delta)
        self.assertAlmostEqual(float(merged_tract['data']['pct_change']['H1']['H001001']), merged_house_pct_change)

class TestBlocks(unittest.TestCase):
    def setUp(self):
        self.geographies = utils.get_geography_collection()

    def test_block_sum(self):
        """
        Verify that the total population of all blocks adds up to the expected amount.
        """
        blocks = self.geographies.find({ 'sumlev': config.SUMLEV_BLOCK })

        pop_2010 = sum([int(block['data']['2010']['P1']['P001001']) for block in blocks])

        self.assertEqual(pop_2010, 1360301) 

    def test_block_split(self):
        """
        Verify that a split block is crosswalked correctly.
        """
        block1 = self.geographies.find({ 'geoid': '150010210051016' }) 
        self.assertEqual(block1.count(), 1)
        block1 = block1[0]

        split_block_pop = 448 
        block1_land_pct = float(184458) / 587158  # AREALAND_INT / AREALAND_2000
        block1_pop_2000 = int(block1_land_pct * split_block_pop)
        block1_pop_2010 = 22 
        block1_pop_delta = block1_pop_2010 - block1_pop_2000
        block1_pop_pct_change = float(block1_pop_delta) / block1_pop_2000

        self.assertAlmostEqual(block1['xwalk']['150010210011337']['POPPCT00'], block1_land_pct, places=4)
        self.assertAlmostEqual(block1['xwalk']['150010210011337']['HUPCT00'], block1_land_pct, places=4)
        self.assertAlmostEqual(block1['data']['2000']['P1']['P001001'], block1_pop_2000)
        self.assertAlmostEqual(float(block1['data']['2010']['P1']['P001001']), block1_pop_2010)
        self.assertAlmostEqual(float(block1['data']['delta']['P1']['P001001']), block1_pop_delta)
        self.assertAlmostEqual(float(block1['data']['pct_change']['P1']['P001001']), block1_pop_pct_change)

    def test_block_merged(self):
        """
        Verify that a merged block is crosswalked correctly.
        150010210011329 + 150010210011331 -> 150010210051009
        """
        # Compute crosswalked values
        block1_pop_2000 = 12  # 150010210011329
        block2_pop_2000 = 27  # 150010210011331
        merged_pop_2000 = block1_pop_2000 + block2_pop_2000
        merged_pop_2010 = 78 
        merged_pop_delta = merged_pop_2010 - merged_pop_2000
        merged_pop_pct_change = float(merged_pop_delta) / merged_pop_2000

        # Verify that the merged block is correct
        merged_block = self.geographies.find({ 'geoid': '150010210051009' })
        self.assertEqual(merged_block.count(), 1)        
        merged_block = merged_block[0]

        self.assertEqual(len(merged_block['xwalk']), 2)
        self.assertEqual(merged_block['xwalk']['150010210011329']['POPPCT00'], 1.0)
        self.assertEqual(merged_block['xwalk']['150010210011331']['POPPCT00'], 1.0)

        self.assertEqual(float(merged_block['data']['2000']['P1']['P001001']), merged_pop_2000)
        self.assertEqual(float(merged_block['data']['2010']['P1']['P001001']), merged_pop_2010)
        self.assertEqual(float(merged_block['data']['delta']['P1']['P001001']), merged_pop_delta)
        self.assertAlmostEqual(float(merged_block['data']['pct_change']['P1']['P001001']), merged_pop_pct_change)

class TestFieldCrosswalk(unittest.TestCase):
    def setUp(self):
        self.geographies = utils.get_geography_collection()

    def test_exact_same_name(self):
        state = self.geographies.find_one({ 'geoid': '15' })

        urban_and_rural_pop_2000 = 1211537
        urban_and_rural_pop_2010 = 1360301
        delta = urban_and_rural_pop_2010 - urban_and_rural_pop_2000
        pct_change = float(urban_and_rural_pop_2010 - urban_and_rural_pop_2000) / urban_and_rural_pop_2000

        self.assertEqual(float(state['data']['2000']['P2']['P002001']), urban_and_rural_pop_2000)
        self.assertEqual(float(state['data']['2010']['P2']['P002001']), urban_and_rural_pop_2010)
        self.assertEqual(float(state['data']['delta']['P2']['P002001']), delta)
        self.assertAlmostEqual(float(state['data']['pct_change']['P2']['P002001']), pct_change)

    def test_different_tables(self):
        state = self.geographies.find_one({ 'geoid': '15' })

        pacific_islanders_2000 = 113539
        pacific_islanders_2010 = 135422
        delta = pacific_islanders_2010 - pacific_islanders_2000
        pct_change = float(pacific_islanders_2010 - pacific_islanders_2000) / pacific_islanders_2000

        # 2000 field P007006
        self.assertEqual(float(state['data']['2000']['P3']['P003006']), pacific_islanders_2000)
        self.assertEqual(float(state['data']['2010']['P3']['P003006']), pacific_islanders_2010)
        self.assertEqual(float(state['data']['delta']['P3']['P003006']), delta)
        self.assertAlmostEqual(float(state['data']['pct_change']['P3']['P003006']), pct_change)

    def test_different_everything(self):
        state = self.geographies.find_one({ 'geoid': '15' })

        unmarried_partner_households_2000 = 23516 
        unmarried_partner_households_2010 = 33068 
        delta = unmarried_partner_households_2010 - unmarried_partner_households_2000
        pct_change = float(unmarried_partner_households_2010 - unmarried_partner_households_2000) / unmarried_partner_households_2000

        # 2000 field PCT014002
        self.assertEqual(float(state['data']['2000']['PCT15']['PCT015013']), unmarried_partner_households_2000)
        self.assertEqual(float(state['data']['2010']['PCT15']['PCT015013']), unmarried_partner_households_2010)
        self.assertEqual(float(state['data']['delta']['PCT15']['PCT015013']), delta)
        self.assertAlmostEqual(float(state['data']['pct_change']['PCT15']['PCT015013']), pct_change)

class TestLabels(unittest.TestCase):
    def setUp(self):
        self.labels = utils.get_label_collection()
        self.geographies = utils.get_geography_collection()

    def test_table_count(self):
        labels = self.labels.find_one({ 'dataset': 'SF1' })

        self.assertEqual(len(labels['tables']), 331)

    def test_table(self):
        """
        Header rows from input file:
        P12F.,,0,SEX BY AGE (SOME OTHER RACE ALONE) [49],,,,,,,,2000 SF1 P12F.
        P12F.,,0,Universe:  People who are Some Other Race alone,,,,,,,,
        """
        table = self.labels.find_one({ 'dataset': 'SF1' })['tables']['P12F']

        self.assertEqual(table['name'], 'SEX BY AGE (SOME OTHER RACE ALONE)')
        self.assertEqual(table['size'], 49)
        self.assertEqual(table['universe'], 'People who are Some Other Race alone')

    def test_label(self):
        """
        P12F.,1,0,Total:,,,,,,,,
        """
        table = self.labels.find_one({ 'dataset': 'SF1' })['tables']['P12F']
        label = table['labels']['P012F001']

        self.assertEqual(label['text'], 'Total:')
        self.assertEqual(label['parent'], None)
        self.assertEqual(label['indent'], 0)
        
    def test_labels_match_geographies(self):
        """
        Hawaii should have a key for every label.
        Every label should have a key for Hawaii.
        """
        geo = self.geographies.find_one({ 'geoid': '15' })
        labels = self.labels.find_one({ 'dataset': 'SF1' })

        geo_tables = geo['data']['2010']
        labels_tables = labels['tables']

        self.assertEqual(sorted(geo_tables.keys()), sorted(labels_tables.keys()))

        # Test table has labels
        for table_name, geo_keys in geo_tables.items():
            label_keys = labels_tables[table_name]['labels']

            self.assertEqual(sorted(geo_keys.keys()), sorted(label_keys.keys()))

        for table_name, label_data in labels_tables.items():
            label_keys = label_data['labels']
            geo_keys = geo_tables[table_name]

            self.assertEqual(sorted(geo_keys.keys()), sorted(label_keys.keys()))

    def test_table_sizes(self):
        """
        Test that the tables documented size matches its actual label count.
        """
        labels_tables = self.labels.find_one({ 'dataset': 'SF1' })['tables']

        for label_data in labels_tables.values():
            self.assertEqual(label_data['size'], len(label_data['labels']))

if __name__ == '__main__':
    unittest.main()
        

########NEW FILE########
__FILENAME__ = update_state_list
#!/usr/bin/env python

import json
import sys

from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import config
import utils

def update_state_list(environment, state, clear=False, remove=False):
    c = S3Connection()
    bucket = c.get_bucket(config.S3_BUCKETS[environment])

    k = Key(bucket)
    k.key = 'states.jsonp'

    try:
        data = k.get_contents_as_string()

        # No existing file 
        if not data:
            raise S3ResponseError()
        
        # Strip off jsonp wrapper
        contents = utils.gunzip_data(data)
        data = contents[7:-1]

        states = json.loads(data)
    except S3ResponseError:
        states = []
    if remove:
        states.remove(state)
        print 'Removed %s from list of available states' % state
    elif clear:
        states = [state]
        print 'Reset list of available states and added %s' % state
    else:
        if state not in states:
            states.append(state)

            print '%s added to available state list' % state
        else:
            print '%s is already available' % state
    
    states.sort()
    jsonp = 'states(%s)' % json.dumps(states)
    compressed = utils.gzip_data(jsonp)

    k.set_contents_from_string(compressed, headers={ 'Content-encoding': 'gzip', 'Content-Type': 'application/json' }, policy='public-read')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('You must specify either "staging" or "production" and a state as arguments to this script.')

    ENVIRONMENT = sys.argv[1]
    STATE = sys.argv[2]
    try:
        OPERATION = sys.argv[3]
    except:
        OPERATION = None

    update_state_list(ENVIRONMENT, STATE, (OPERATION == 'CLEAR'), (OPERATION == 'REMOVE'))

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

from StringIO import StringIO
import gzip
import re

from pymongo import Connection

import config

TABLE_NAME_REGEX = re.compile('([A-Z1-9]+?)0*([\d]+)([A-Z]?)')
TABLE_ID_PATTERN = re.compile(r'^(?P<letter>[A-Z]+)(?P<number>\d+)(?P<suffix>[A-Z])?')

_MONGO_CONNECTION = Connection()

def parse_table_id(table_id):
    return TABLE_ID_PATTERN.match(table_id).groupdict()

def generate_stat_key(table_id, line):
    """Pad and connect table and line number to get a standard identifier for a statistic."""
    d = parse_table_id(table_id)
    if d['suffix'] is None: d['suffix'] = ''
    d['number'] = int(d['number'])
    d['line'] = int(line)
    return "%(letter)s%(number)03i%(suffix)s%(line)03i" % d
        
def geoid_nation(r):
    # TODO
    return ''

def geoid_state(r):
    return r['STATE']

def geoid_county(r):
    return r['STATE'] + r['COUNTY']

def geoid_county_subdivision(r):
    return r['STATE'] + r['COUNTY'] + r['COUSUB']

def geoid_tract(r):
    return r['STATE'] + r['COUNTY'] + r['TRACT']

def geoid_place(r):
    return r['STATE'] + r['PLACE']

def geoid_block(r):
    return r['STATE'] + r['COUNTY'] + r['TRACT'] + r['BLOCK']

GEOID_COMPUTERS = {
    config.SUMLEV_NATION: geoid_nation,
    config.SUMLEV_STATE: geoid_state,
    config.SUMLEV_COUNTY: geoid_county,
    config.SUMLEV_COUNTY_SUBDIVISION: geoid_county_subdivision,
    config.SUMLEV_TRACT: geoid_tract,
    config.SUMLEV_PLACE: geoid_place,
    config.SUMLEV_BLOCK: geoid_block,
}

def parse_table_from_key(key):
    t = key[0:-3]
    match = TABLE_NAME_REGEX.match(t)
    return ''.join(match.groups())

def find_geography_by_xref(collection, xref, fields=None):
    return collection.find_one({ 'xrefs.FILEID': xref['FILEID'], 'xrefs.STUSAB': xref['STUSAB'], 'xrefs.LOGRECNO': xref['LOGRECNO'] }, fields=fields)

def find_geographies_for_xwalk(collection, geography, fields=None):
    return collection.find({ 'geoid': { '$in': geography['xwalk'].keys() } }, fields=fields)

def xref_from_row_dict(d):
    # Strip off unncessary attrs
    d.pop('CHARITER')
    d.pop('CIFSN')

    return { 
        'FILEID': d.pop('FILEID'),
        'STUSAB': d.pop('STUSAB'),
        'LOGRECNO': d.pop('LOGRECNO')
    }

def gzip_data(d):
    s = StringIO()
    gz = gzip.GzipFile(fileobj=s, mode='wb')
    gz.write(d)
    gz.close()

    return s.getvalue()

def gunzip_data(d):
    s = StringIO(d)
    gz = gzip.GzipFile(fileobj=s, mode='rb')
    
    content = gz.read()
    gz.close()

    return content

def get_label_collection():
    db = _MONGO_CONNECTION[config.LABELS_DB]
    return db[config.LABELS_COLLECTION]

def get_geography_collection():
    db = _MONGO_CONNECTION[config.CENSUS_DB]
    return db[config.GEOGRAPHIES_COLLECTION]

def get_geography2000_collection():
    db = _MONGO_CONNECTION[config.CENSUS_DB] 
    return db[config.GEOGRAPHIES_2000_COLLECTION]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# IRE-Census documentation build configuration file, created by
# sphinx-quickstart on Fri Jun 10 11:26:35 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'IRE-Census'
copyright = u'2011, IRE'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1'
# The full version, including alpha/beta/rc tags.
release = '1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'IRE-Censusdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'IRE-Census.tex', u'IRE-Census Documentation',
   u'IRE', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'ire-census', u'IRE-Census Documentation',
     [u'IRE'], 1)
]

########NEW FILE########
__FILENAME__ = generate_export_ddl
#!/usr/bin/env python
"""
Generate SQL "Create table" files for all of the SF1 tables, with column format compatible with
the bulk download files available at http://census.ire.org/data/bulkdata.html

Note that all table names and column names will be forced to lowercase for maximum interoperability
between databases.
"""
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import Float, Integer, String
from sqlalchemy.schema import CreateTable

import json

import os.path
import sys

LABELS = json.load(open("../metadata/sf1_labels.json"))

def _create_base_table(name):
    """Provide the common columns for all of our exports"""
    metadata = MetaData()
    sql_table = Table(name.lower(), metadata)
    sql_table.append_column(Column('geoid', String(length=11), primary_key=True))
    sql_table.append_column(Column('sumlev', String(length=3), nullable=False))
    sql_table.append_column(Column('state', String(length=2), nullable=False))
    sql_table.append_column(Column('county', String(length=3)))
    sql_table.append_column(Column('cbsa', String(length=5)))
    sql_table.append_column(Column('csa', String(length=3)))
    sql_table.append_column(Column('necta', String(length=5)))
    sql_table.append_column(Column('cnecta', String(length=3)))
    sql_table.append_column(Column('name', String(length=90), nullable=False))
    sql_table.append_column(Column('pop100', Integer, nullable=False))
    sql_table.append_column(Column('hu100', Integer, nullable=False))
    sql_table.append_column(Column('pop100_2000', Integer, nullable=True))
    sql_table.append_column(Column('hu100_2000', Integer, nullable=True))
    return sql_table

def sqlalchemy_for_table(table_code,table_name_prefix='ire_'):
    table_labels = LABELS[table_code]
    if table_labels['name'].find('AVERAGE') != -1 or table_labels['name'].find('MEDIAN') != -1:
        col_type = Float
    else:
        col_type = Integer
    sql_table = _create_base_table("%s%s" % (table_name_prefix,table_code))    
    for label in sorted(table_labels['labels']):
        sql_table.append_column(Column(label.lower(), col_type))
        sql_table.append_column(Column("%s_2000" % label.lower(), col_type))
    return sql_table

def sql_for_table(table_code,table_name_prefix='ire_'):
    sql_table = sqlalchemy_for_table(table_code,table_name_prefix)
    return unicode(CreateTable(sql_table).compile(dialect=None)).strip()

if __name__ == "__main__":
    try:
        output_dir = sys.argv[1]
    except:
        output_dir = '.'

    table_name_prefix = 'ire_'

    for table_code in sorted(LABELS):
        table_name = LABELS[table_code]['name']
        fn = os.path.join(output_dir,"%s%s.sql" % (table_name_prefix,table_code))
        with open(fn,"w") as f:
            f.write("-- %s. %s\n" % (table_code,table_name))
            f.write("-- designed to work with the IRE Census bulk data exports\n")
            f.write("-- see http://census.ire.org/data/bulkdata.html\n")
            f.write(sql_for_table(table_code))
            f.write(';\n')

########NEW FILE########
