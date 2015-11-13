__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
from mysite.polls.models import Poll
from django.contrib import admin
from mysite.polls.models import Choice

class ChoiceInline(admin.TabularInline):

    model = Choice
    extra = 3

class PollAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]

admin.site.register(Poll, PollAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
import datetime

class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    def __unicode__(self):
        return self.question
    def was_published_today(self):
        return self.pub_date.date() == datetime.date.today()
	
 
class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()
    def __unicode__(self):
        return self.choice

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('mysite.polls.views',
    (r'^$', 'index'),
    (r'^(?P<poll_id>\d+)/$', 'detail'),
    (r'^(?P<poll_id>\d+)/results/$', 'results'),
    (r'^(?P<poll_id>\d+)/vote/$', 'vote'),
    (r'^(?P<poll_id>\d+)/edit/$', 'edit'),
    (r'^(?P<poll_id>\d+)/editpole/$', 'editpole'),
    (r'^(?P<poll_id>\d+)/editpole1/$', 'editpole1'),
    (r'^addpole/$', 'addpole'),
    (r'^add/$', 'add'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from mysite.polls.models import Choice, Poll
import datetime


def index(request):
    latest_poll_list = Poll.objects.all().order_by('-pub_date')[:5]
    return render_to_response('polls/index.html', {'latest_poll_list': latest_poll_list})
    
def detail(request, poll_id):
        p = get_object_or_404(Poll, pk=poll_id)
        return render_to_response('polls/detail.html', {'poll': p},
                                   context_instance=RequestContext(request))

def results(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('polls/results.html', {'poll': p})

def vote(request, poll_id):
        p = get_object_or_404(Poll, pk=poll_id)
        try:
            selected_choice = p.choice_set.get(pk=request.POST['choice'])
        except (KeyError, Choice.DoesNotExist):
            # Redisplay the poll voting form.
            return render_to_response('polls/detail.html', {
                'poll': p,
                'error_message': "You didn't select a choice.",
            }, context_instance=RequestContext(request))
        else:
            selected_choice.votes += 1
            selected_choice.save()
            # Always return an HttpResponseRedirect after successfully dealing
            # with POST data. This prevents data from being posted twice if a
            # user hits the Back button.
            return HttpResponseRedirect(reverse('mysite.polls.views.results', args=(p.id,)))

def add(request):
    return render_to_response('polls/add.html',context_instance=RequestContext(request))
    
def addpole(request):
    p = Poll(question=request.POST['text'], pub_date=datetime.datetime.now())
    p.save()
    return HttpResponseRedirect(reverse('mysite.polls.views.index'))
 
def editpole(request,poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    p.choice_set.create(choice=request.POST['text1'], votes=0)
    p.save()
    return HttpResponseRedirect(reverse('mysite.polls.views.detail',args=(p.id,)))
    
def editpole1(request,poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    p.question=request.POST['text2']
    p.save()
    return HttpResponseRedirect(reverse('mysite.polls.views.index'))

def edit(request, poll_id):
    p = get_object_or_404(Poll, pk=poll_id)
    return render_to_response('polls/edit.html', {'poll': p},context_instance=RequestContext(request))
    
########NEW FILE########
__FILENAME__ = settings
# Django settings for mysite project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'testdatabase.db',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'America/Boston'

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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '%((j6s74=g9u#!3m881*a5zh(98*@)sd4e&$z)$_m#-&%3_%^-'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'mysite.urls'

TEMPLATE_DIRS = ("/Users/badar/Desktop/UROP/django/mysite/templates"
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
	'mysite.polls',
	'django.contrib.admin'
	
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
)

CACHE_BACKEND = 'locmem://'

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('mysite.temperatures.views',
    (r'^display', 'display'),
  

)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from sqlalchemy import create_engine, MetaData, select,and_, or_, not_, Integer, cast
from sqlalchemy.sql import func
import json

# this is the database address that sqlalchemy uses to connect.
DB_URI='sqlite:////home/marcua/data/repos/decsoc/ssql/test.db'
#DB_URI='sqlite:////Users/badar/Desktop/UROP/ssql/test.db'
# this is the latitude/longitude grid size of squares displayed on map
GRANULARITY=1.0
# An alpha transparency value from 0-255 for the transparency level of the
# squares on the map
ALPHA = hex(200)[2:]

def generate_style_kml():
    blue=255
    red=0
    delta=5
    linewidth=0
    list_styles=[]
    list_styles.append(generate_style(ALPHA + 'FF0000',0,linewidth))
    for id in range(1,52):
        blue=blue-delta
        red=red+delta
        hexa=convert_to_hex(blue,red)
        list_styles.append(generate_style(hexa,id,linewidth))
    return "".join(list_styles)
        
def convert_to_hex(blue,red):
    b=hex(blue)[2:]
    if blue<=15:
        b='0'+b
    r=hex(red)[2:]
    if red<=15:
        r='0'+r
    return ALPHA+b+'00'+r


def generate_style(hexa,id,linewidth):
    style='''    
<Style id="style%d">
  <LineStyle>
    <width>%f</width>
  </LineStyle>
  <PolyStyle>
    <color>%s</color>
  </PolyStyle>
</Style>
'''
    style = style % (id, linewidth, hexa)
    return style

def generate_placemarks_kml(temperature_table, db_conn):
    yesterday = datetime.today()-timedelta(hours=48)
    where_clause = and_(temperature_table.c.latitude != None,
                        temperature_table.c.longitude != None, 
                        temperature_table.c.temperature != None,
                        temperature_table.c.temperature > 0.0,
                        temperature_table.c.temperature < 120.0, 
                        temperature_table.c.meandevs < 2, 
                        temperature_table.c.meandevs > 0, 
                        temperature_table.c.created_at > yesterday)
    latcol = cast(temperature_table.c.latitude, Integer).label('latitude')
    longcol = cast(temperature_table.c.longitude, Integer).label('longitude')
    data_query = select([latcol, longcol, 
                         func.avg(temperature_table.c.temperature).label('temperature')],
                        where_clause).\
                       group_by(latcol, longcol)
    maxT_query = select([func.max(temperature_table.c.temperature)], where_clause)
    minT_query = select([func.min(temperature_table.c.temperature)], where_clause)

    minT_result = db_conn.execute(minT_query)
    minT = minT_result.scalar()
    minT_result.close()
    maxT_result = db_conn.execute(maxT_query)
    maxT = maxT_result.scalar()
    maxT_result.close()
    deltaT = maxT-minT
    a = (51/deltaT)
    
    list_placemarks=[]
    cursor = db_conn.execute(data_query) 
    for row in cursor:
        p=float(row["temperature"])-minT
        normalize_temp=a*p
        color=round(normalize_temp)
        latlng=lat_lng(row)
        list_placemarks.append(generate_placemarks(row,color,latlng))
    cursor.close()
    return "".join(list_placemarks)


def lat_lng(row):
    """
        Calculates the (lat,lon) of the four points of the square grid based on the granularity
        that is colored and displayed on google maps. For example, point (20.3,20) with a granularity 
        of 0.5 will have points [(20,20),(20,20.5),(20.5,20.5),(20.5,20)]. 
    """
    lat = row["latitude"]
    lng = row["longitude"]
    n = int(lat/GRANULARITY)
    nlat_start = n * GRANULARITY
    nlat_end = nlat_start + GRANULARITY
    nlg=int(lng/GRANULARITY)
    nlng_start = nlg * GRANULARITY
    nlng_end = nlng_start + GRANULARITY
    latlng=[(nlat_start,nlng_start), (nlat_start,nlng_end), (nlat_end,nlng_end), (nlat_end,nlng_start)]
    return latlng

def generate_placemarks(row,color,latlng):
    placemark='''   
<Placemark>
<name>%s</name>
    <styleUrl>#style%d</styleUrl>
<Polygon>
  <extrude>1</extrude>
  <altitudeMode>relativeToGround</altitudeMode>
  <outerBoundaryIs>
    <LinearRing>
      <coordinates>
        %f,%f,20
        %f,%f,20
        %f,%f,20
        %f,%f,20
      </coordinates>
    </LinearRing>
  </outerBoundaryIs>
  
</Polygon>
</Placemark>
'''
    placemark=placemark % (row["temperature"], color,
                           latlng[0][1], latlng[0][0], latlng[1][1], latlng[1][0],
                           latlng[2][1], latlng[2][0], latlng[3][1], latlng[3][0])
    return placemark

def begin_kml():
    
    begin='''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
'''
    return begin



def end_kml():
    end='''
  <ScreenOverlay>
    <name>Absolute Positioning: Top left</name>
    <visibility>1</visibility>
    <Icon>
      <href>http://web.mit.edu/badar/www/temperatures.png</href>
    </Icon>
    <overlayXY x=".95" y=".1" xunits="fraction" yunits="fraction"/>
    <screenXY x=".95" y=".1" xunits="fraction" yunits="fraction"/>
    <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
    <size x="0" y="0" xunits="fraction" yunits="fraction"/>
  </ScreenOverlay>
</Document>
</kml>'''
    return end
    
def generate_weather_kml():
    engine = create_engine(DB_URI, echo=True)
    meta = MetaData()
    meta.reflect(bind=engine)
    temperature = meta.tables['weather_meandev']
    conn = engine.connect()
    
    kml_body = [begin_kml(),generate_style_kml(),generate_placemarks_kml(temperature, conn), end_kml()]
    return "".join(kml_body)

def display(request):
    content = cache.get("content")
    if content == None:
        content = generate_weather_kml()
        cache.set("content", content, 60)
    return HttpResponse(content,content_type="application\vnd.google-earth.kml+xml")    

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^polls/', include('mysite.polls.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^temperatures/', include('mysite.temperatures.urls')),
)

########NEW FILE########
__FILENAME__ = tweeql-programmatic
from tweeql.exceptions import TweeQLException
from tweeql.query_runner import QueryRunner

runner = QueryRunner()
runner.run_query("SELECT text FROM twitter_sample;", False)
#runner.stop_query()

########NEW FILE########
__FILENAME__ = tweeql-udf
from tweeql.exceptions import TweeQLException
from tweeql.field_descriptor import ReturnType
from tweeql.function_registry import FunctionInformation, FunctionRegistry
from tweeql.query_runner import QueryRunner

class StringLength():
    return_type = ReturnType.INTEGER

    @staticmethod
    def factory():
        return StringLength().strlen

    def strlen(self, tuple_data, val):
        """ 
            Returns the length of val, which is a string
        """
        return len(val)

fr = FunctionRegistry()
fr.register("stringlength", FunctionInformation(StringLength.factory, StringLength.return_type))

runner = QueryRunner()
runner.run_query("SELECT stringlength(text) AS len FROM twitter_sample;", False)

########NEW FILE########
__FILENAME__ = compare_dates
#!/usr/bin/env python

from Weather.data import rows as station_rows
from Weather.data import calcDist

def get_temperatures():
    engine = create_engine(DB_URI, echo=True)
    meta = MetaData()
    meta.reflect(bind=engine)
    temperature = meta.tables['weather_meandev']
    conn = engine.connect()
    yesterday = datetime.today()-timedelta(hours=48)
    where_clause = and_(temperature_table.c.latitude != None,
                        temperature_table.c.longitude != None, 
                        temperature_table.c.temperature != None,
                        temperature_table.c.temperature > 0.0,
                        temperature_table.c.temperature < 120.0, 
                        temperature_table.c.meandevs < 2, 
                        temperature_table.c.meandevs > 0, 
                        temperature_table.c.created_at > yesterday)
    latcol = cast(temperature_table.c.latitude, Integer).label('latitude')
    longcol = cast(temperature_table.c.longitude, Integer).label('longitude')
    data_query = select([latcol, longcol, 
                         func.avg(temperature_table.c.temperature).label('temperature')],
                        where_clause).\
                       group_by(latcol, longcol)
    cursor = db_conn.execute(data_query)

    return cursor

def latlong2station(latitude, longitude):
    best,result = 99999999,[]
    for row in station_rows():
        test_point = map(float, (row[2],row[3]))
        
        distance = calcDist(latitude, longitude, test_point[0], test_point[1])
        if distance < best:
            best,result = distance,row
    station = None
    if best < MAX_DISTANCE:
        station = result[0]
    return station

def get_nws_temp(latitude, longitude):
    station_name = latlong2station(latitude, longitude)
    temperature = None
    if station_name != None:
        station = Weather.Station(station_name)
        temperature = station['temp_f']
    return temperature

def compare_temperatures(cursor):
    for row in cursor:
        tweet_temp = float(row["temperature"])
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        nws_temp = get_nws_temp(latitude, longitude)
        print "ours: ", tweet_temp, "nws: ", nws_temp

########NEW FILE########
__FILENAME__ = globals
from urllib import urlretrieve
from threading import Thread
from os import path,getcwd

# Please replace this with your own key in a production environment!
API_KEY = 'ABQIAAAAtGw1MDAVWMO6QjAEb2-w_hQCULP4XOMyhPd8d_NrQQEO8sT8XBR4nl1tfW8GUiQ2uIWU8ASwZR6mXA'

OBSURL = 'http://www.weather.gov/data/current_obs/all_xml.zip'
WURL = 'http://www.weather.gov/data/current_obs/%s.xml'
BASE = path.dirname(__file__)
ZFILE = path.join(BASE,'all_xml.zip')

class Fetch(Thread):
    """Thread fetching"""
    def run(self):
        fetch()

def fetch(thread=False):
    """
    Fetch observation base to a zipfile
    @param thread: Runs fetch in a separate thread if True
    """
    if thread:
        Fetch.start()
    else:
        urlretrieve(OBSURL,ZFILE)


########NEW FILE########
__FILENAME__ = interface
"""
A very simple WSGI interface to the module
"""

from Weather import *
from urllib import unquote
from datetime import datetime
import os

titler = lambda x: ' '.join(map(lambda y: y.title(), x.split('_')))


def html(station):
    """
    Yields HTML source for given station
    """
    yield '<html><head><title>%s</title></head><body>'%station
    yield '<table><tr><td><h2>%s</h2><p><b>%s</b></p></td>'%\
        (station,station.data.get('weather',''))
    yield '<td><img src="%s"></td></tr>'%station.icon()
    yield '<tr><td><p>Currently: %s  -  '%\
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    yield 'Time of observation: %s</p></td></tr>'%station.datetime()
    yield '</table><hr><table><tr><th><h3>URLs</h3></th><th><h3>Metrics</h3></th><th><h3>Info</h3></th></tr>'
    urls,metrics,info = [],[],[]
    for k,v in station.items():
        if not v: continue
        k = titler(k)
        tr = '<tr><th align="right">%s</th><td>%s</td></tr>'
        if type(v) == type(0.):
            metrics.append(tr%(k,'%.3f'%v))
        elif v.startswith('http'):
            urls.append(tr%(k,'<a href="%s">%s</a>'%(v,filter(None,v.split('/'))[-1])))
        else:
            info.append(tr%(k,v))
    r = ['<td valign="top"><table>%s</table></td>'%''.join(locals()[x]) \
          for x in ('urls','metrics','info')]
    yield '<tr>%s</tr></table>'%''.join(r)
    yield '</body></html>'


def detail(environ, response):
    response('200 OK', [('Content-type','text/html')])
    return html(Station(environ['QUERY_STRING']))

def zip(environ, response):
    response('200 OK', [('Content-type','text/html')])
    return html(zip2station(environ['QUERY_STRING']))

def location(environ, response):
    response('200 OK', [('Content-type','text/html')])
    return html(location2station(unquote(environ['QUERY_STRING'])))

def list(environ, response):
    response('200 OK', [('Content-type','text/html')])
    yield '<ul>'
    for station in stations():
        yield '<li><a href="detail?%s">%s</a></li>'%(station,station)
    yield '</ul>'

def dispatch(environ, response):
    return eval(environ['PATH_INFO'][1:])(environ, response)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print "Serving HTTP on port 8000..."
    make_server('', 8000, dispatch).serve_forever()


########NEW FILE########
__FILENAME__ = station
import os
import zipfile
from sgmllib import SGMLParser
from UserDict import UserDict
from urllib import urlopen,quote
from datetime import datetime
from Weather.data import rows
from Weather.globals import *

class Station(SGMLParser,UserDict):
    """
    SGMLParser and dictionary for NOAA XML weather data by station name

    @param station: The NOAA station identifier to search, eg KMTN
    @param force: Boolean for whether an update should be forced
    """
    def __init__(self, station):
        SGMLParser.__init__(self)
        UserDict.__init__(self)
        self.tag = None
        self.station = station.upper()
        self.update()

    def update(self, live=False):
        self.data = {}
        # csv update
        keys = ('latitude','longitude','city','state','zipcode')
        for row in rows():
            if self.station == row[0]:
                UserDict.update(self, dict(zip(keys,row[2:-1])))
                break
        if not self.data:
            raise AttributeError,'Station %s not found'%self.station
        # sgmllib update
        self.reset()
        if os.path.isfile(ZFILE) and not live:
            zfile = zipfile.ZipFile(ZFILE,'r')
            for name in zfile.namelist():
                if name.endswith('%s.xml'%self.station):
                    SGMLParser.feed(self, zfile.read(name))
                    del zfile
                    break
        else:
            #Fetch().start()
            SGMLParser.feed(self, urlopen(WURL%self.station).read())
        self.close()


    def unknown_starttag(self, tag, attrs):
        self.tag = tag
        self.data[tag] = None

    def handle_data(self, text):
        text = text.rstrip()
        if self.tag and text:
            if text in ('None','NA') or not text:
                value = None
            else:
                try: value = float(text)
                except ValueError:
                    try: value = int(text)
                    except ValueError:
                        value = str(text)
            self.data[self.tag] = value

    def datetime(self):
        """
        Parses and returns the observation datetime object (if possible)
        """
        if 'observation_time_rfc822' in self.data \
           and self.data['observation_time_rfc822']:
            tstr = self.data['observation_time_rfc822']
            tstr = ' '.join(tstr.split(' ')[:-2])
            return datetime.strptime(tstr, '%a, %d %b %Y %H:%M:%S')
        elif 'observation_time' in self.data:
            return datetime.strptime(self.data['observation_time'] \
                +' %s'%datetime.now().year,
                'Last Updated on %b %d, %H:%M %p %Z %Y')
        return ''


    def icon(self):
        """
        Returns URL of weather icon if it exists
        """
        try:
            return self.data['icon_url_base']+self.data['icon_url_name']
        except KeyError:
            return ''

    def location(self):
        """
        Returns location string usually in `StationName,State` format
        """
        try:
            return self.data['location']
        except KeyError:
            return self.data['station_name']

    def pprint(self):
        """
        Pretty print the weather items (for debugging)
        """
        for i in self.items():
            print '%s => %r'%i

    def __repr__(self):
        return '<Weather.Station %s>'%self

    def __str__(self):
        return '%s: %s'%(self.station,self.location())

def stations():
    """
    Returns iterator of station tuples
    """
    for row in rows():
        yield tuple(row)

def state2stations(state):
    """
    Translate a state identifier (ie DC) into a list of
    Station tuples from that state
    """
    state = state[:2].upper()
    for row in rows():
        if row[5]==state:
            yield tuple(row)

def location2station(location):
    """
    Translate full location into Station tuple by closest match
    Locations can be in any Google friendly form like
    "State St, Troy, NY", "2nd st & State St, Troy, NY" and "7 State St, Troy, NY"
    """
    # just forget it, use google
    location = quote(str(location))
    geo_url = 'http://maps.google.com/maps/geo?key=%s&q=%s&sensor=false&output=csv'%(API_KEY,location)
    point = map(float,urlopen(geo_url).readline().split(',')[-2:])
    best,result = 99999999,[]
    for row in rows():
        test_point = map(float, (row[2],row[3]))
        distance = ((test_point[0]-point[0])**2 + (test_point[1]-point[1])**2)**.5
        if distance < best:
            best,result = distance,row
    return tuple(result)

if __name__ == '__main__':
    print Station('KMTN')
    print location2station('Baltimore, MD')
    print location2station(21204)
    print location2station('Dulaney Valley rd, towson MD')
    print len([x for x in stations()])
########NEW FILE########
__FILENAME__ = stats
from Weather.data import rows

class DistStats:
    def __init__(self,outlier=1000):
        self.sequence = []
        for x in rows():
            d = float(x[-1])
            if d > outlier: continue
            self.sequence.append(d)
    def median(self):
        self.sequence.sort()
        return self.sequence[len(self.sequence) // 2]
    def avg(self):
        return sum(self.sequence) / len(self.sequence)
    def stdev(self):
        sd = sum([(i - self.avg()) ** 2 for i in self.sequence])
        return (sd / (len(self.sequence) - 1)) ** .5
    def min(self): return min(self.sequence)
    def max(self): return max(self.sequence)
    def __repr__(self):
        return '%.3f/%.3f/%.3f/%.3f/%.3f'% \
            (self.min(),self.median(),self.max(),self.avg(),self.stdev())

if __name__ == '__main__':
    print DistStats()
########NEW FILE########
__FILENAME__ = client
import datetime
import errno
import socket
import threading
import warnings
from redis.exceptions import ConnectionError, ResponseError, InvalidResponse
from redis.exceptions import RedisError, AuthenticationError

class ConnectionManager(threading.local):
    "Manages a list of connections on the local thread"
    def __init__(self):
        self.connections = {}
        
    def make_connection_key(self, host, port, db):
        "Create a unique key for the specified host, port and db"
        return '%s:%s:%s' % (host, port, db)
        
    def get_connection(self, host, port, db, password):
        "Return a specific connection for the specified host, port and db"
        key = self.make_connection_key(host, port, db)
        if key not in self.connections:
            self.connections[key] = Connection(host, port, db, password)
        return self.connections[key]
        
    def get_all_connections(self):
        "Return a list of all connection objects the manager knows about"
        return self.connections.values()
        
connection_manager = ConnectionManager()

class Connection(object):
    "Manages TCP communication to and from a Redis server"
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._sock = None
        self._fp = None
        
    def connect(self, redis_instance):
        "Connects to the Redis server is not already connected"
        if self._sock:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
        except socket.error, e:
            raise ConnectionError("Error %s connecting to %s:%s. %s." % \
                (e.args[0], self.host, self.port, e.args[1]))
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self._sock = sock
        self._fp = sock.makefile('r')
        redis_instance._setup_connection()
        
    def disconnect(self):
        "Disconnects from the Redis server"
        if self._sock is None:
            return
        try:
            self._sock.close()
        except socket.error:
            pass
        self._sock = None
        self._fp = None
        
    def send(self, command, redis_instance):
        "Send ``command`` to the Redis server. Return the result."
        self.connect(redis_instance)
        try:
            self._sock.sendall(command)
        except socket.error, e:
            if e.args[0] == errno.EPIPE:
                self.disconnect()
            raise ConnectionError("Error %s while writing to socket. %s." % \
                e.args)
                
    def read(self, length=None):
        """
        Read a line from the socket is length is None,
        otherwise read ``length`` bytes
        """
        try:
            if length is not None:
                return self._fp.read(length)
            return self._fp.readline()
        except socket.error, e:
            self.disconnect()
            if e.args and e.args[0] == errno.EAGAIN:
                raise ConnectionError("Error while reading from socket: %s" % \
                    e.args[1])
        return ''
        
def list_or_args(command, keys, args):
    # returns a single list combining keys and args
    # if keys is not a list or args has items, issue a
    # deprecation warning
    oldapi = bool(args)
    try:
        i = iter(keys)
        # a string can be iterated, but indicates
        # keys wasn't passed as a list
        if isinstance(keys, basestring):
            oldapi = True
    except TypeError:
        oldapi = True
        keys = [keys]
    if oldapi:
        warnings.warn(DeprecationWarning(
            "Passing *args to Redis.%s has been deprecated. "
            "Pass an iterable to ``keys`` instead" % command
        ))
        keys.extend(args)
    return keys
    
def timestamp_to_datetime(response):
    "Converts a unix timestamp to a Python datetime object"
    if not response:
        return None
    try:
        response = int(response)
    except ValueError:
        return None
    return datetime.datetime.fromtimestamp(response)
    
def string_keys_to_dict(key_string, callback):
    return dict([(key, callback) for key in key_string.split()])

def dict_merge(*dicts):
    merged = {}
    [merged.update(d) for d in dicts]
    return merged
    
def parse_info(response):
    "Parse the result of Redis's INFO command into a Python dict"
    info = {}
    def get_value(value):
        if ',' not in value:
            return value
        sub_dict = {}
        for item in value.split(','):
            k, v = item.split('=')
            try:
                sub_dict[k] = int(v)
            except ValueError:
                sub_dict[k] = v
        return sub_dict
    for line in response.splitlines():
        key, value = line.split(':')
        try:
            info[key] = int(value)
        except ValueError:
            info[key] = get_value(value)
    return info
    
def zset_score_pairs(response, **options):
    """
    If ``withscores`` is specified in the options, return the response as
    a list of (value, score) pairs
    """
    if not response or not options['withscores']:
        return response
    return zip(response[::2], map(float, response[1::2]))
    
    
class Redis(threading.local):
    """
    Implementation of the Redis protocol.
    
    This abstract class provides a Python interface to all Redis commands
    and an implementation of the Redis protocol.
    
    Connection and Pipeline derive from this, implementing how
    the commands are sent and received to the Redis server
    """
    RESPONSE_CALLBACKS = dict_merge(
        string_keys_to_dict(
            'AUTH DEL EXISTS EXPIRE MOVE MSETNX RENAMENX SADD SISMEMBER SMOVE '
            'SETNX SREM ZADD ZREM',
            bool
            ),
        string_keys_to_dict(
            'DECRBY INCRBY LLEN SCARD SDIFFSTORE SINTERSTORE SUNIONSTORE '
            'ZCARD ZREMRANGEBYSCORE',
            int
            ),
        string_keys_to_dict(
            # these return OK, or int if redis-server is >=1.3.4
            'LPUSH RPUSH',
            lambda r: isinstance(r, int) and r or r == 'OK'
            ),
        string_keys_to_dict('ZSCORE ZINCRBY',
            lambda r: r is not None and float(r) or r),
        string_keys_to_dict(
            'FLUSHALL FLUSHDB LSET LTRIM MSET RENAME '
            'SAVE SELECT SET SHUTDOWN',
            lambda r: r == 'OK'
            ),
        string_keys_to_dict('SDIFF SINTER SMEMBERS SUNION',
            lambda r: r and set(r) or r
            ),
        string_keys_to_dict('ZRANGE ZRANGEBYSCORE ZREVRANGE', zset_score_pairs),
        {
            'BGSAVE': lambda r: r == 'Background saving started',
            'INFO': parse_info,
            'LASTSAVE': timestamp_to_datetime,
            'PING': lambda r: r == 'PONG',
            'RANDOMKEY': lambda r: r and r or None,
            'TTL': lambda r: r != -1 and r or None,
        }
        )
    
    def __init__(self, host='localhost', port=6379,
                db=0, password=None,
                charset='utf-8', errors='strict'):
        self.encoding = charset
        self.errors = errors
        self.select(host, port, db, password)
        
    #### Legacty accessors of connection information ####
    def _get_host(self):
        return self.connection.host
    host = property(_get_host)
    
    def _get_port(self):
        return self.connection.port
    port = property(_get_port)
    
    def _get_db(self):
        return self.connection.db
    db = property(_get_db)
    
    def pipeline(self):
        return Pipeline(self.connection, self.encoding, self.errors)
        
    #### COMMAND EXECUTION AND PROTOCOL PARSING ####
    def _execute_command(self, command_name, command, **options):
        self.connection.send(command, self)
        return self.parse_response(command_name, **options)

    def execute_command(self, command_name, command, **options):
        "Sends the command to the Redis server and returns it's response"
        try:
            return self._execute_command(command_name, command, **options)
        except ConnectionError:
            self.connection.disconnect()
            return self._execute_command(command_name, command, **options)
        
    def _parse_response(self, command_name, catch_errors):
        conn = self.connection
        response = conn.read().strip()
        if not response:
            self.connection.disconnect()
            raise ConnectionError("Socket closed on remote end")
            
        # server returned a null value
        if response in ('$-1', '*-1'):
            return None
        byte, response = response[0], response[1:]
        
        # server returned an error
        if byte == '-':
            if response.startswith('ERR '):
                response = response[4:]
            raise ResponseError(response)
        # single value
        elif byte == '+':
            return response
        # int value
        elif byte == ':':
            return int(response)
        # bulk response
        elif byte == '$':
            length = int(response)
            if length == -1:
                return None
            response = length and conn.read(length) or ''
            conn.read(2) # read the \r\n delimiter
            return response
        # multi-bulk response
        elif byte == '*':
            length = int(response)
            if length == -1:
                return None
            if not catch_errors:
                return [self._parse_response(command_name, catch_errors) 
                    for i in range(length)]
            else:
                # for pipelines, we need to read everything, including response errors.
                # otherwise we'd completely mess up the receive buffer
                data = []
                for i in range(length):
                    try:
                        data.append(
                            self._parse_response(command_name, catch_errors)
                            )
                    except Exception, e:
                        data.append(e)
                return data
            
        raise InvalidResponse("Unknown response type for: %s" % command_name)
        
    def parse_response(self, command_name, catch_errors=False, **options):
        "Parses a response from the Redis server"
        response = self._parse_response(command_name, catch_errors)
        if command_name in self.RESPONSE_CALLBACKS:
            return self.RESPONSE_CALLBACKS[command_name](response, **options)
        return response
        
    def encode(self, value):
        "Encode ``value`` using the instance's charset"
        if isinstance(value, str):
            return value
        if isinstance(value, unicode):
            return value.encode(self.encoding, self.errors)
        # not a string or unicode, attempt to convert to a string
        return str(value)
        
    def format_inline(self, *args, **options):
        "Formats a request with the inline protocol"
        cmd = '%s\r\n' % ' '.join([self.encode(a) for a in args])
        return self.execute_command(args[0], cmd, **options)
        
    def format_bulk(self, *args, **options):
        "Formats a request with the bulk protocol"
        bulk_value = self.encode(args[-1])
        cmd = '%s %s\r\n%s\r\n' % (
            ' '.join([self.encode(a) for a in args[:-1]]),
            len(bulk_value),
            bulk_value,
            )
        return self.execute_command(args[0], cmd, **options)
        
    def format_multi_bulk(self, *args, **options):
        "Formats the request with the multi-bulk protocol"
        cmd_count = len(args)
        cmds = []
        for i in args:
            enc_value = self.encode(i)
            cmds.append('$%s\r\n%s\r\n' % (len(enc_value), enc_value))
        return self.execute_command(
            args[0],
            '*%s\r\n%s' % (cmd_count, ''.join(cmds)),
            **options
            )
        
    #### CONNECTION HANDLING ####
    def get_connection(self, host, port, db, password):
        "Returns a connection object"
        conn = connection_manager.get_connection(host, port, db, password)
        # if for whatever reason the connection gets a bad password, make
        # sure a subsequent attempt with the right password makes its way
        # to the connection
        conn.password = password
        return conn
        
    def _setup_connection(self):
        """
        After successfully opening a socket to the Redis server, the
        connection object calls this method to authenticate and select
        the appropriate database.
        """
        if self.connection.password:
            if not self.format_inline('AUTH', self.connection.password):
                raise AuthenticationError("Invalid Password")
        self.format_inline('SELECT', self.connection.db)
        
    def select(self, host, port, db, password=None):
        """
        Switch to a different database on the current host/port
        
        Note this method actually replaces the underlying connection object
        prior to issuing the SELECT command.  This makes sure we protect
        the thread-safe connections
        """
        self.connection = self.get_connection(host, port, db, password)
        
    #### SERVER INFORMATION ####
    def bgsave(self):
        """
        Tell the Redis server to save its data to disk.  Unlike save(),
        this method is asynchronous and returns immediately.
        """
        return self.format_inline('BGSAVE')
        
    def dbsize(self):
        "Returns the number of keys in the current database"
        return self.format_inline('DBSIZE')
        
    def delete(self, *names):
        "Delete one or more keys specified by ``names``"
        return self.format_inline('DEL', *names)
    __delitem__ = delete
    
    def flush(self, all_dbs=False):
        warnings.warn(DeprecationWarning(
            "'flush' has been deprecated. "
            "Use Redis.flushdb() or Redis.flushall() instead"))
        if all_dbs:
            return self.flushall()
        return self.flushdb()
        
    def flushall(self):
        "Delete all keys in all databases on the current host"
        return self.format_inline('FLUSHALL')
        
    def flushdb(self):
        "Delete all keys in the current database"
        return self.format_inline('FLUSHDB')
        
    def info(self):
        "Returns a dictionary containing information about the Redis server"
        return self.format_inline('INFO')
        
    def lastsave(self):
        """
        Return a Python datetime object representing the last time the
        Redis database was saved to disk
        """
        return self.format_inline('LASTSAVE')
        
    def ping(self):
        "Ping the Redis server"
        return self.format_inline('PING')
        
    def save(self):
        """
        Tell the Redis server to save its data to disk,
        blocking until the save is complete
        """
        return self.format_inline('SAVE')
        
    #### BASIC KEY COMMANDS ####
    def decr(self, name, amount=1):
        """
        Decrements the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as 0 - ``amount``
        """
        return self.format_inline('DECRBY', name, amount)
        
    def exists(self, name):
        "Returns a boolean indicating whether key ``name`` exists"
        return self.format_inline('EXISTS', name)
    __contains__ = exists
        
    def expire(self, name, time):
        "Set an expire on key ``name`` for ``time`` seconds"
        return self.format_inline('EXPIRE', name, time)
        
    def get(self, name):
        """
        Return the value at key ``name``, or None of the key doesn't exist
        """
        return self.format_inline('GET', name)
    __getitem__ = get
    
    def getset(self, name, value):
        """
        Set the value at key ``name`` to ``value`` if key doesn't exist
        Return the value at key ``name`` atomically
        """
        return self.format_bulk('GETSET', name, value)
        
    def incr(self, name, amount=1):
        """
        Increments the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as ``amount``
        """
        return self.format_inline('INCRBY', name, amount)
        
    def keys(self, pattern='*'):
        "Returns a list of keys matching ``pattern``"
        return self.format_inline('KEYS', pattern)
        
    def mget(self, keys, *args):
        """
        Returns a list of values ordered identically to ``keys``
        
        * Passing *args to this method has been deprecated *
        """
        keys = list_or_args('mget', keys, args)
        return self.format_inline('MGET', *keys)
        
    def mset(self, mapping):
        "Sets each key in the ``mapping`` dict to its corresponding value"
        items = []
        [items.extend(pair) for pair in mapping.iteritems()]
        return self.format_multi_bulk('MSET', *items)
        
    def msetnx(self, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value if
        none of the keys are already set
        """
        items = []
        [items.extend(pair) for pair in mapping.iteritems()]
        return self.format_multi_bulk('MSETNX', *items)
        
    def move(self, name, db):
        "Moves the key ``name`` to a different Redis database ``db``"
        return self.format_inline('MOVE', name, db)
        
    def randomkey(self):
        "Returns the name of a random key"
        return self.format_inline('RANDOMKEY')

    def rename(self, src, dst, **kwargs):
        """
        Rename key ``src`` to ``dst``

        * The following flags have been deprecated *
        If ``preserve`` is True, rename the key only if the destination name
            doesn't already exist
        """
        if kwargs:
            if 'preserve' in kwargs:
                warnings.warn(DeprecationWarning(
                    "preserve option to 'rename' is deprecated, "
                    "use Redis.renamenx instead"))
                if kwargs['preserve']:
                    return self.renamenx(src, dst)
        return self.format_inline('RENAME', src, dst)
        
    def renamenx(self, src, dst):
        "Rename key ``src`` to ``dst`` if ``dst`` doesn't already exist"
        return self.format_inline('RENAMENX', src, dst)
        
        
    def set(self, name, value, **kwargs):
        """
        Set the value at key ``name`` to ``value``
        
        * The following flags have been deprecated *
        If ``preserve`` is True, set the value only if key doesn't already
        exist
        If ``getset`` is True, set the value only if key doesn't already exist
        and return the resulting value of key
        """
        if kwargs:
            if 'getset' in kwargs:
                warnings.warn(DeprecationWarning(
                    "getset option to 'set' is deprecated, "
                    "use Redis.getset() instead"))
                if kwargs['getset']:
                    return self.getset(name, value)
            if 'preserve' in kwargs:
                warnings.warn(DeprecationWarning(
                    "preserve option to 'set' is deprecated, "
                    "use Redis.setnx() instead"))
                if kwargs['preserve']:
                    return self.setnx(name, value)
        return self.format_bulk('SET', name, value)
    __setitem__ = set
    
    def setnx(self, name, value):
        "Set the value of key ``name`` to ``value`` if key doesn't exist"
        return self.format_bulk('SETNX', name, value)
        
    def ttl(self, name):
        "Returns the number of seconds until the key ``name`` will expire"
        return self.format_inline('TTL', name)
        
    def type(self, name):
        "Returns the type of key ``name``"
        return self.format_inline('TYPE', name)
        
        
    #### LIST COMMANDS ####
    def blpop(self, keys, timeout=0):
        """
        LPOP a value off of the first non-empty list
        named in the ``keys`` list.
        
        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.
        
        If timeout is 0, then block indefinitely.
        """
        keys = list(keys)
        keys.append(timeout)
        return self.format_inline('BLPOP', *keys)
        
    def brpop(self, keys, timeout=0):
        """
        RPOP a value off of the first non-empty list
        named in the ``keys`` list.
        
        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.
        
        If timeout is 0, then block indefinitely.
        """
        keys = list(keys)
        keys.append(timeout)
        return self.format_inline('BRPOP', *keys)
        
    def lindex(self, name, index):
        """
        Return the item from list ``name`` at position ``index``
        
        Negative indexes are supported and will return an item at the
        end of the list
        """
        return self.format_inline('LINDEX', name, index)
        
    def llen(self, name):
        "Return the length of the list ``name``"
        return self.format_inline('LLEN', name)
        
    def lpop(self, name):
        "Remove and return the first item of the list ``name``"
        return self.format_inline('LPOP', name)
    
    def lpush(self, name, value):
        "Push ``value`` onto the head of the list ``name``"
        return self.format_bulk('LPUSH', name, value)
        
    def lrange(self, name, start, end):
        """
        Return a slice of the list ``name`` between
        position ``start`` and ``end``
        
        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.format_inline('LRANGE', name, start, end)
        
    def lrem(self, name, value, num=0):
        """
        Remove the first ``num`` occurrences of ``value`` from list ``name``
        
        If ``num`` is 0, then all occurrences will be removed
        """
        return self.format_bulk('LREM', name, num, value)
        
    def lset(self, name, index, value):
        "Set ``position`` of list ``name`` to ``value``"
        return self.format_bulk('LSET', name, index, value)
        
    def ltrim(self, name, start, end):
        """
        Trim the list ``name``, removing all values not within the slice
        between ``start`` and ``end``
        
        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.format_inline('LTRIM', name, start, end)
        
    def pop(self, name, tail=False):
        """
        Pop and return the first or last element of list ``name``
        
        * This method has been deprecated,
          use Redis.lpop or Redis.rpop instead *
        """
        warnings.warn(DeprecationWarning(
            "Redis.pop has been deprecated, "
            "use Redis.lpop or Redis.rpop instead"))
        if tail:
            return self.rpop(name)
        return self.lpop(name)
    
    def push(self, name, value, head=False):
        """
        Push ``value`` onto list ``name``.
        
        * This method has been deprecated,
          use Redis.lpush or Redis.rpush instead *
        """
        warnings.warn(DeprecationWarning(
            "Redis.push has been deprecated, "
            "use Redis.lpush or Redis.rpush instead"))
        if head:
            return self.lpush(name, value)
        return self.rpush(name, value)
        
    def rpop(self, name):
        "Remove and return the last item of the list ``name``"
        return self.format_inline('RPOP', name)
        
    def rpoplpush(self, src, dst):
        """
        RPOP a value off of the ``src`` list and atomically LPUSH it
        on to the ``dst`` list.  Returns the value.
        """
        return self.format_inline('RPOPLPUSH', src, dst)
        
    def rpush(self, name, value):
        "Push ``value`` onto the tail of the list ``name``"
        return self.format_bulk('RPUSH', name, value)
        
    def sort(self, name, start=None, num=None, by=None, get=None,
            desc=False, alpha=False, store=None):
        """
        Sort and return the list, set or sorted set at ``name``.
        
        ``start`` and ``num`` allow for paging through the sorted data
        
        ``by`` allows using an external key to weight and sort the items.
            Use an "*" to indicate where in the key the item value is located
            
        ``get`` allows for returning items from external keys rather than the
            sorted data itself.  Use an "*" to indicate where int he key
            the item value is located
            
        ``desc`` allows for reversing the sort
        
        ``alpha`` allows for sorting lexicographically rather than numerically
        
        ``store`` allows for storing the result of the sort into 
            the key ``store``
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        
        pieces = [name]
        if by is not None:
            pieces.append('BY %s' % by)
        if start is not None and num is not None:
            pieces.append('LIMIT %s %s' % (start, num))
        if get is not None:
            pieces.append('GET %s' % get)
        if desc:
            pieces.append('DESC')
        if alpha:
            pieces.append('ALPHA')
        if store is not None:
            pieces.append('STORE %s' % store)
        return self.format_inline('SORT', *pieces)
        
    
    #### SET COMMANDS ####
    def sadd(self, name, value):
        "Add ``value`` to set ``name``"
        return self.format_bulk('SADD', name, value)
        
    def scard(self, name):
        "Return the number of elements in set ``name``"
        return self.format_inline('SCARD', name)
        
    def sdiff(self, keys, *args):
        "Return the difference of sets specified by ``keys``"
        keys = list_or_args('sdiff', keys, args)
        return self.format_inline('SDIFF', *keys)
        
    def sdiffstore(self, dest, keys, *args):
        """
        Store the difference of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sdiffstore', keys, args)
        return self.format_inline('SDIFFSTORE', dest, *keys)
        
    def sinter(self, keys, *args):
        "Return the intersection of sets specified by ``keys``"
        keys = list_or_args('sinter', keys, args)
        return self.format_inline('SINTER', *keys)
        
    def sinterstore(self, dest, keys, *args):
        """
        Store the intersection of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sinterstore', keys, args)
        return self.format_inline('SINTERSTORE', dest, *keys)
        
    def sismember(self, name, value):
        "Return a boolean indicating if ``value`` is a member of set ``name``"
        return self.format_bulk('SISMEMBER', name, value)
        
    def smembers(self, name):
        "Return all members of the set ``name``"
        return self.format_inline('SMEMBERS', name)
        
    def smove(self, src, dst, value):
        "Move ``value`` from set ``src`` to set ``dst`` atomically"
        return self.format_bulk('SMOVE', src, dst, value)
        
    def spop(self, name):
        "Remove and return a random member of set ``name``"
        return self.format_inline('SPOP', name)
        
    def srandmember(self, name):
        "Return a random member of set ``name``"
        return self.format_inline('SRANDMEMBER', name)
        
    def srem(self, name, value):
        "Remove ``value`` from set ``name``"
        return self.format_bulk('SREM', name, value)
        
    def sunion(self, keys, *args):
        "Return the union of sets specifiued by ``keys``"
        keys = list_or_args('sunion', keys, args)
        return self.format_inline('SUNION', *keys)
        
    def sunionstore(self, dest, keys, *args):
        """
        Store the union of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sunionstore', keys, args)
        return self.format_inline('SUNIONSTORE', dest, *keys)
        
    
    #### SORTED SET COMMANDS ####
    def zadd(self, name, value, score):
        "Add member ``value`` with score ``score`` to sorted set ``name``"
        return self.format_bulk('ZADD', name, score, value)
        
    def zcard(self, name):
        "Return the number of elements in the sorted set ``name``"
        return self.format_inline('ZCARD', name)
        
    def zincr(self, key, member, value=1):
        "This has been deprecated, use zincrby instead"
        warnings.warn(DeprecationWarning(
            "Redis.zincr has been deprecated, use Redis.zincrby instead"
            ))
        return self.zincrby(key, member, value)
        
    def zincrby(self, name, value, amount=1):
        "Increment the score of ``value`` in sorted set ``name`` by ``amount``"
        return self.format_bulk('ZINCRBY', name, amount, value)
        
    def zrange(self, name, start, end, desc=False, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in ascending order.
        
        ``start`` and ``end`` can be negative, indicating the end of the range.
        
        ``desc`` indicates to sort in descending order.
        
        ``withscores`` indicates to return the scores along with the values.
            The return type is a list of (value, score) pairs
        """
        if desc:
            return self.zrevrange(name, start, end, withscores)
        pieces = ['ZRANGE', name, start, end]
        if withscores:
            pieces.append('withscores')
        return self.format_inline(*pieces, **{'withscores': withscores})
        
    def zrangebyscore(self, name, min, max, start=None, num=None, withscores=False):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max``.
        
        If ``start`` and ``num`` are specified, then return a slice of the range.
        
        ``withscores`` indicates to return the scores along with the values.
            The return type is a list of (value, score) pairs
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        pieces = ['ZRANGEBYSCORE', name, min, max]
        if start is not None and num is not None:
            pieces.extend(['LIMIT', start, num])
        if withscores:
            pieces.append('withscores')
        return self.format_inline(*pieces, **{'withscores': withscores})
        
    def zrem(self, name, value):
        "Remove member ``value`` from sorted set ``name``"
        return self.format_bulk('ZREM', name, value)
        
    def zremrangebyscore(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with scores
        between ``min`` and ``max``
        """
        return self.format_inline('ZREMRANGEBYSCORE', name, min, max)
        
    def zrevrange(self, name, start, num, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``num`` sorted in descending order.
        
        ``start`` and ``num`` can be negative, indicating the end of the range.
        
        ``withscores`` indicates to return the scores along with the values
            as a dictionary of value => score
        """
        pieces = ['ZREVRANGE', name, start, num]
        if withscores:
            pieces.append('withscores')
        return self.format_inline(*pieces, **{'withscores': withscores})
        
    def zscore(self, name, value):
        "Return the score of element ``value`` in sorted set ``name``"
        return self.format_bulk('ZSCORE', name, value)
        
    
    #### HASH COMMANDS ####
    def hget(self, name, key):
        "Return the value of ``key`` within the hash ``name``"
        return self.format_bulk('HGET', name, key)
        
    def hset(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name``
        Returns 1 if HSET created a new field, otherwise 0
        """
        return self.format_multi_bulk('HSET', name, key, value)
        
    
class Pipeline(Redis):
    """
    Pipelines provide a way to transmit multiple commands to the Redis server
    in one transmission.  This is convenient for batch processing, such as
    saving all the values in a list to Redis.
    
    All commands executed within a pipeline are wrapped with MULTI and EXEC
    calls. This guarantees all commands executed in the pipeline will be
    executed atomically.
    
    Any command raising an exception does *not* halt the execution of
    subsequent commands in the pipeline. Instead, the exception is caught
    and its instance is placed into the response list returned by execute().
    Code iterating over the response list should be able to deal with an
    instance of an exception as a potential value. In general, these will be
    ResponseError exceptions, such as those raised when issuing a command
    on a key of a different datatype.
    """
    def __init__(self, connection, charset, errors):
        self.connection = connection
        self.encoding = charset
        self.errors = errors
        self.reset()
        
    def reset(self):
        self.command_stack = []
        self.format_inline('MULTI')
        
    def execute_command(self, command_name, command, **options):
        """
        Stage a command to be executed when execute() is next called
        
        Returns the current Pipeline object back so commands can be
        chained together, such as:
        
        pipe = pipe.set('foo', 'bar').incr('baz').decr('bang')
        
        At some other point, you can then run: pipe.execute(), 
        which will execute all commands queued in the pipe.
        """
        # if the command_name is 'AUTH' or 'SELECT', then this command
        # must have originated after a socket connection and a call to
        # _setup_connection(). run these commands immediately without
        # buffering them.
        if command_name in ('AUTH', 'SELECT'):
            return super(Pipeline, self).execute_command(
                command_name, command, **options)
        else:
            self.command_stack.append((command_name, command, options))
        return self
        
    def _execute(self, commands):
        # build up all commands into a single request to increase network perf
        all_cmds = ''.join([c for _1, c, _2 in commands])
        self.connection.send(all_cmds, self)
        # we only care about the last item in the response, which should be
        # the EXEC command
        for i in range(len(commands)-1):
            _ = self.parse_response('_')
        # tell the response parse to catch errors and return them as
        # part of the response
        response = self.parse_response('_', catch_errors=True)
        # don't return the results of the MULTI or EXEC command
        commands = [(c[0], c[2]) for c in commands[1:-1]]
        if len(response) != len(commands):
            raise ResponseError("Wrong number of response items from "
                "pipline execution")
        # Run any callbacks for the commands run in the pipeline
        data = []
        for r, cmd in zip(response, commands):
            if not isinstance(r, Exception):
                if cmd[0] in self.RESPONSE_CALLBACKS:
                    r = self.RESPONSE_CALLBACKS[cmd[0]](r, **cmd[1])
            data.append(r)
        return data
        
    def execute(self):
        "Execute all the commands in the current pipeline"
        self.format_inline('EXEC')
        stack = self.command_stack
        self.reset()
        try:
            return self._execute(stack)
        except ConnectionError:
            self.connection.disconnect()
            return self._execute(stack)
            
    def select(self, host, port, db):
        raise RedisError("Cannot select a different database from a pipeline")
        

########NEW FILE########
__FILENAME__ = exceptions
"Core exceptions raised by the Redis client"

class RedisError(Exception):
    pass
    
class AuthenticationError(RedisError):
    pass
    
class ConnectionError(RedisError):
    pass
    
class ResponseError(RedisError):
    pass
    
class InvalidResponse(RedisError):
    pass
    
class InvalidData(RedisError):
    pass
    
########NEW FILE########
__FILENAME__ = streambulkloader
#!/usr/bin/env python

import csv
import os
import sys
import psycopg2
import psycopg2.extensions
import redis
import settings
import tempfile
import time

from tweepy.api import API
from tweepy.utils import convert_to_utf8_str
from tweepy.utils import import_simplejson
from tweepy.models import Status

api = API()
json = import_simplejson()

def gen_tuple(jsontweet):
    tweet = Status.parse(api, json.loads(jsontweet))
    retweeted = (getattr(tweet, 'retweeted_status', None) != None)
    return (tweet.author.id, tweet.created_at, convert_to_utf8_str(tweet.text), retweeted)
    
def bulk_load(listkey, tweets, db):
    print "bulk-loading %d tweets from '%s'" % (len(tweets), listkey)
    insert_cmd = "INSERT INTO tweets (author_id, created_at, tweet, retweeted) VALUES (%s, %s, %s, %s);"
    cur = db.cursor()
    cur.executemany(insert_cmd, (gen_tuple(jsontweet) for jsontweet in tweets))
    db.commit()

def poll_data(r, db):
    listkey = r.rpoplpush(settings.TO_INDEX, settings.CONSUMED_INDICES)
    if listkey != None:
        tweets = r.lrange(listkey, 0, -1)
        bulk_load(listkey, tweets, db)
        r.lrem(settings.CONSUMED_INDICES, listkey, 0)
        r.delete(listkey)

def main():
    r = redis.Redis(host=settings.REDIS_HOSTNAME, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    conn_str = "dbname='%s' user='%s' host='%s' password='%s'" % (settings.DATABASE_NAME, settings.DATABASE_USER, settings.DATABASE_HOST, settings.DATABASE_PASSWORD)
    db = psycopg2.connect(conn_str);
    db.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
    while True:
        poll_data(r, db)
        time.sleep(settings.POLL_TIME)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nGoodbye!'

########NEW FILE########
__FILENAME__ = streamfilewriter
#!/usr/bin/env python

import settings
import csv
import redis
import tempfile
import time

from tweepy.api import API
from tweepy.models import Status
from tweepy.utils import import_simplejson
from tweepy.utils import convert_to_utf8_str

api = API()
json = import_simplejson()

def bulk_load(listkey, tweets):
    with open('/home/marcua/data/tweets/%s' % (listkey), 'w') as tmpfile:
        print "file %s" % (tmpfile.name)
        for jsontweet in tweets:
            tweet = Status.parse(api, json.loads(jsontweet))
            tmpfile.write(convert_to_utf8_str(tweet.text) + "\n")

def poll_data(r):
    listkey = r.rpoplpush(settings.TO_INDEX, settings.CONSUMED_INDICES)
    if listkey != None:
        tweets = r.lrange(listkey, 0, -1)
        bulk_load(listkey, tweets)
        r.lrem(settings.CONSUMED_INDICES, listkey, 0)
        r.delete(listkey)

def main():
    r = redis.Redis(host=settings.REDIS_HOSTNAME, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    while True:
        poll_data(r)
        time.sleep(settings.POLL_TIME)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nGoodbye!'

########NEW FILE########
__FILENAME__ = streamgrabber
#!/usr/bin/env python

import getpass
import redis
import tweepy
import settings

class StreamGrabberListener(tweepy.StreamListener):
    """
    Manages tweets to be processed in redis.  Redis variables:
       - variable TWEET_GROUP_ID keeps track of the largest tweet group id issued yet
       - variable TO_INDEX is a list that stores the ids of tweet groups to be processed.
       - variables 'tweet-group:%d" are lists of tweets to be processed (tweet groups)
    """

    def __init__(self):
        tweepy.StreamListener.__init__(self)
        self.redis = redis.Redis(host=settings.REDIS_HOSTNAME, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        self.increment_tweet_group_id()
        
    def increment_tweet_group_id(self):
        self.tweet_group_id = self.redis.incr(settings.TWEET_GROUP_ID)
        self.tweet_group_listkey = 'tweet-group:%d' % (self.tweet_group_id)
        
    def on_data(self, data):
        """
        Push data into redis
        """
        if 'in_reply_to_status_id' in data:
            self.keep_or_update_tgid()
            self.insert_data(data)

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'
    
    def keep_or_update_tgid(self):
        if self.redis.llen(self.tweet_group_listkey) >= settings.MAX_MESSAGES:
            print 'grabbed another %d tweets in %s' % (settings.MAX_MESSAGES, self.tweet_group_listkey)
            self.redis.lpush(settings.TO_INDEX, self.tweet_group_listkey)
            self.increment_tweet_group_id()
    
    def insert_data(self, data):
        self.redis.rpush(self.tweet_group_listkey, data)

def main():
    # Prompt for login credentials and setup stream object
    username = raw_input('Twitter username: ')
    password = getpass.getpass('Twitter password: ')
    stream = tweepy.Stream(username, password, StreamGrabberListener(), timeout=None)

    stream.sample()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nGoodbye!'

########NEW FILE########
__FILENAME__ = streamwatcher
#!/usr/bin/env python

import time
from getpass import getpass
from textwrap import TextWrapper

import tweepy


class StreamWatcherListener(tweepy.StreamListener):

    status_wrapper = TextWrapper(width=60, initial_indent='    ', subsequent_indent='    ')

    def on_status(self, status):
        try:
            print self.status_wrapper.fill(status.text)
            print '\n %s  %s  via %s\n' % (status.author.screen_name, status.created_at, status.source)
        except:
            # Catch any unicode errors while printing to console
            # and just ignore them to avoid breaking application.
            pass

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'


def main():
    # Prompt for login credentials and setup stream object
    username = raw_input('Twitter username: ')
    password = getpass('Twitter password: ')
    stream = tweepy.Stream(username, password, StreamWatcherListener(), timeout=None)

    # Prompt for mode of streaming
    valid_modes = ['sample', 'filter']
    while True:
        mode = raw_input('Mode? [sample/filter] ')
        if mode in valid_modes:
            break
        print 'Invalid mode! Try again.'

    if mode == 'sample':
        stream.sample()

    elif mode == 'filter':
        follow_list = raw_input('Users to follow (comma separated): ').strip()
        track_list = raw_input('Keywords to track (comma seperated): ').strip()
        if follow_list:
            follow_list = [u for u in follow_list.split(',')]
        else:
            follow_list = None
        if track_list:
            track_list = [k for k in track_list.split(',')]
        else:
            track_list = None

        stream.filter(follow_list, track_list)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nGoodbye!'


########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
import tweeql.builtin_functions
import random
from tweeql.builtin_functions import MeanOutliers
from tweeql.builtin_functions import NormalOutliers

if __name__ == "__main__":
#    print(tweeql.builtin_functions.Temperature.temperature_f(None, u"Adelaide: Tue 25 May 3:30 AM - Rain Shower -  Temp. 13.0\u00B0C RH 100% Wind SW (230 degrees) at 6 km/h http://bit.ly/9Vkpg4"))
#    print(tweeql.builtin_functions.Temperature.temperature_f(None, "Temp. 13.0mC RH 100% Wind SW (230 degrees) at 6 km/h http://bit.ly/9Vkpg4"))
#    print(tweeql.builtin_functions.Temperature.temperature_f(None, "Temp. 13.0dC RH 100% Wind SW (230 degrees) at 6 km/h http://bit.ly/9Vkpg4"))
#    print repr(u"(\d+(\.\d+)?)\s+°C")
#    print repr(ur"(\d+(\.\d+)?)\s*°C")
    """
    print MeanOutliers.nummeandevs(None, 5, 1, 2)
    print MeanOutliers.nummeandevs(None, 6, 1, 2)
    print MeanOutliers.nummeandevs(None, 3, 1, 2)
    print MeanOutliers.nummeandevs(None, 2, 1, 2)
    print MeanOutliers.nummeandevs(None, 4, 1, 2)
    print MeanOutliers.nummeandevs(None, 4, 1, 2)
    print MeanOutliers.nummeandevs(None, 10, 1, 2)
    print MeanOutliers.nummeandevs(None, 40, 1, 2)
    print MeanOutliers.nummeandevs(None, 5, 1, 2)
    
    print MeanOutliers.nummeandevs(None, 60, 2, 2)
    print MeanOutliers.nummeandevs(None, 80, 2, 2)
    print MeanOutliers.nummeandevs(None, 75, 2, 2)
    print MeanOutliers.nummeandevs(None, 80, 2, 2)
    print MeanOutliers.nummeandevs(None, 90, 2, 2)
    print MeanOutliers.nummeandevs(None, 63, 2, 2)
    print MeanOutliers.nummeandevs(None, 72, 2, 2)
    print MeanOutliers.nummeandevs(None, 40, 2, 2)
    print MeanOutliers.nummeandevs(None, 120, 2, 2)
    
    print MeanOutliers.nummeandevs(None, 90, 2, 3)
    print MeanOutliers.nummeandevs(None, 20, 2, 3)
    print MeanOutliers.nummeandevs(None, 21, 2, 3)
    print MeanOutliers.nummeandevs(None, 23, 2, 3)
    print MeanOutliers.nummeandevs(None, 25, 2, 3)
    print MeanOutliers.nummeandevs(None, 15, 2, 3)
    print MeanOutliers.nummeandevs(None, 20, 2, 3)
    print MeanOutliers.nummeandevs(None, 25, 2, 3)
    print MeanOutliers.nummeandevs(None, 25, 2, 3)
    print MeanOutliers.nummeandevs(None, 25, 2, 3)
    print MeanOutliers.nummeandevs(None, 60, 2, 3)
    """
    meansum = 0.0
    meandevsum = 0.0
    count = 0
    std = 40
    incount = 0
    for i in range(1,10000):
        val = random.gauss(0,std)
        if abs(val) < 2*std:
            incount += 1
        meansum += 1.0*val
        count += 1
        meandevsum += abs(1.0*(val - meansum/count))
        MeanOutliers.nummeandevs(None, val, 2, 3)
    print meansum/count, meandevsum/count
    print "incount", incount
    print MeanOutliers.nummeandevs(None, 80, 2, 3)
    pass

########NEW FILE########
__FILENAME__ = aggregation
from datetime import timedelta
from datetime import datetime
from tweeql.query import QueryTokens 
from tweeql.exceptions import QueryException
from threading import RLock

class Aggregator():
    def __init__(self, aggregates, groupby, windowsize):
        self.aggregates = aggregates
        self.groupby = groupby
        self.tuple_descriptor = None
        self.buckets = {}
        self.update_lock = RLock()
        kwargs = {windowsize[1]: int(windowsize[0])}
        self.windowsize = timedelta(**kwargs)
        self.window = None
        self.emptylist = []
    def update(self, updates):
        self.update_lock.acquire()
        output = self.emptylist
        for update in updates:
            if self.window == None:
                self.window = AggregateWindow(update.created_at, update.created_at + self.windowsize)
            # ignore all entries before the window
            test = self.window.windowtest(update.created_at)
            if test == AggregateWindowResult.AFTER:
                if output is self.emptylist:
                    output = []
                for bucket, aggs in self.buckets.items():
                    bucket.set_tuple_descriptor(self.tuple_descriptor)
                    for k,v in aggs.items():
                        setattr(bucket, k, v.value())
                    output.append(bucket)
                self.buckets = {}
                while self.window.windowtest(update.created_at) != AggregateWindowResult.IN:
                    self.window.advance(self.windowsize)
                test = AggregateWindowResult.IN
            if test == AggregateWindowResult.IN:
                bucket = update.generate_from_descriptor(self.groupby)
                if bucket not in self.buckets:
                    aggs = dict()
                    for aggregate in self.aggregates:
                        factory = aggregate.aggregate_factory
                        underlying = aggregate.underlying_fields
                        aggs[aggregate.alias] = factory(underlying)
                    self.buckets[bucket] = aggs
                for aggregate in self.buckets[bucket].values():
                    aggregate.update(update)
        self.update_lock.release()
        return output

class AggregateWindow():
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def windowtest(self, timeval):
        if timeval < self.start:
            return AggregateWindowResult.BEFORE
        if timeval < self.end:
            return AggregateWindowResult.IN
        return AggregateWindowResult.AFTER
    def advance(self, windowsize):
        self.start = self.end
        self.end = self.end + windowsize

class AggregateWindowResult():
    BEFORE = 1
    IN = 2
    AFTER = 3

class Aggregate():
    def __init__(self, underlying_fields):
        self.underlying_fields = underlying_fields
        self.reset()
    def update(self, t):
        raise  NotImplementedError()
    def value(self):
        raise NotImplementedError()
    def reset(self):
        raise NotImplementedError()

def get_aggregate_factory(agg_func):
    if agg_func == QueryTokens.AVG:
        return Avg.create
    elif agg_func == QueryTokens.COUNT:
        return Count.create
    elif agg_func == QueryTokens.SUM:
        return Sum.create
    elif agg_func == QueryTokens.MIN:
        return Min.create
    elif agg_func == QueryTokens.MAX:
        return Max.create
    else:
        return None

class Avg(Aggregate):
    @classmethod
    def create(cls, underlying_fields):
        return Avg(underlying_fields)
    def update(self, t):
        self.sum += getattr(t, self.underlying_fields[0])
        self.count += 1
    def value(self):
        return self.sum/self.count
    def reset(self):
        self.sum = 0
        self.count = 0

class Count(Aggregate):
    @classmethod
    def create(cls, underlying_fields):
        return Count(underlying_fields)
    def update(self, t):
        self.count += 1
    def value(self):
        return self.count
    def reset(self):
        self.count = 0

class Sum(Aggregate):
    @classmethod
    def create(cls, underlying_fields):
        return Sum(underlying_fields)
    def update(self, t):
        self.sum += getattr(t, self.underlying_fields[0])
    def value(self):
        return self.sum
    def reset(self):
        self.sum = 0

class Min(Aggregate):
    @classmethod
    def create(cls, underlying_fields):
        return Min(underlying_fields)
    def update(self, t):
        val = getattr(t, self.underlying_fields[0])
        if (self.min is None) or (val < self.min):
            self.min = val
    def value(self):
        return self.min
    def reset(self):
        self.min = None

class Max(Aggregate):
    @classmethod
    def create(cls, underlying_fields):
        return Max(underlying_fields)
    def update(self, t):
        val = getattr(t, self.underlying_fields[0])
        if (self.max is None) or (val > self.max):
            self.max = val
    def value(self):
        return self.max
    def reset(self):
        self.max = None

########NEW FILE########
__FILENAME__ = tweeql-command-line
#!/usr/bin/env python

from tweeql.exceptions import TweeQLException
from tweeql.query_runner import QueryRunner

import settings
import traceback
import readline
try:
    import pyreadline as readline
except:
    pass

def main():
    runner = QueryRunner()
    try:
        while True:
            cmd = raw_input("tweeql> ");
            process_command(runner, cmd)
    except (KeyboardInterrupt, EOFError):
        print '\nGoodbye!'

def process_command(runner, cmd):
    try:
        runner.run_query(cmd, False)
    except KeyboardInterrupt:
        runner.stop_query()
    except TweeQLException, e:
        runner.stop_query()
        if settings.DEBUG:
            traceback.print_exc()
        else:
            print e

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = builtin_functions
# -*- coding: utf-8 -*-

from tweeql.field_descriptor import ReturnType
from tweeql.function_registry import FunctionInformation
from tweeql.function_registry import FunctionRegistry
from geopy import geocoders
from ordereddict import OrderedDict
from pkg_resources import resource_filename
from threading import RLock
from urllib2 import URLError

import gzip
import math
import re
import os
import pickle
import sys

class Temperature():
    fahr = re.compile(ur"(^| )(\-?\d+([.,]\d+)?)\s*\u00B0?(F$|F |Fahr)", re.UNICODE)
    celcius = re.compile(ur"(^| )(\-?\d+([.,]\d+)?)\s*\u00B0?(C$|C |Celsius)", re.UNICODE)
    return_type = ReturnType.FLOAT

    @staticmethod
    def factory():
        return Temperature().temperature_f

    def temperature_f(self, tuple_data, status):
        """ 
            Returns the temperature found in 'status' in Fahrenheit.  Captures
            both systems of temperature and then converts to Fahrenheit.
        """
        fahr_search = Temperature.fahr.search(status)
        temperature = None
        try:
            if fahr_search != None:
                temperature = fahr_search.group(2).replace(",", ".")
                temperature = float(temperature)
            else:
                celcius_search = Temperature.celcius.search(status)
                if celcius_search != None:
                    temperature = celcius_search.group(2).replace(",", ".")
                    temperature = float(temperature)
                    temperature = ((9.0/5) * temperature) + 32
        except ValueError:
            print "Encoding error on '%s'" % (status)
        return temperature

class Sentiment:
    classifier = None
    classinfo = None
    return_type = ReturnType.FLOAT
    constructor_lock = RLock()
    
    @staticmethod
    def factory():
        Sentiment.constructor_lock.acquire()
        if Sentiment.classifier == None:
            # Only import analysis if we have to: this means people who
            # don't use sentiment analysis don't have to install nltk.
            import tweeql.extras.sentiment
            import tweeql.extras.sentiment.analysis
            Sentiment.analysis = tweeql.extras.sentiment.analysis
            fname = resource_filename(tweeql.extras.sentiment.__name__, 'sentiment.pkl.gz')
            fp = gzip.open(fname)
            classifier_dict = pickle.load(fp)
            fp.close()
            Sentiment.classifier = classifier_dict['classifier']
            Sentiment.classinfo = { classifier_dict['pos_label'] :
                                      { 'cutoff': classifier_dict['pos_cutoff'],
                                        'value' : 1.0/classifier_dict['pos_recall'] },
                                    classifier_dict['neg_label'] :
                                      { 'cutoff': classifier_dict['neg_cutoff'],
                                        'value': -1.0/classifier_dict['neg_recall'] }
                                  }
        Sentiment.constructor_lock.release()
        return Sentiment().sentiment

    def sentiment(self, tuple_data, text):
        words = Sentiment.analysis.words_in_tweet(text)
        features = Sentiment.analysis.word_feats(words)
        dist = Sentiment.classifier.prob_classify(features)
        retval = 0
        maxlabel = dist.max()
        classinfo = Sentiment.classinfo[maxlabel]
        if dist.prob(maxlabel) > classinfo['cutoff']:
            retval = classinfo['value']
        return retval

class StringLength():
    return_type = ReturnType.INTEGER

    @staticmethod
    def factory():
        return StringLength().strlen

    def strlen(self, tuple_data, val):
        """ 
            Returns the length of val, which is a string
        """
        return len(val)
         
class Rounding():
    return_type = ReturnType.FLOAT

    @staticmethod
    def factory():
        return Rounding().floor

    def floor(self, tuple_data, val, nearest = 1):
        """ 
            Returns the largest integer multiple of 'nearest' that is less than or equal to val.
            If nearest is less than 1, you may see funny results because of floating 
            point arithmetic.
        """
        retval = val - (val % nearest) if val != None else None
        return retval

class Location:
    class LruDict(OrderedDict):
        def __setitem__(self, key, value):
            self.pop(key, None)
            OrderedDict.__setitem__(self, key, value)
        def compact_to_size(self, size):
            while len(self) > size:
                self.popitem(last=False)

    from tweeql.settings_loader import get_settings
    settings = get_settings()
    gn = geocoders.GeoNames(country_bias=None, username=settings.GEONAMES_USERNAME, timeout=None, proxies=None)
	
    return_type = ReturnType.FLOAT
    LATLNG = "__LATLNG"
    LAT = "lat"
    LNG = "lng"
    cache = LruDict()
    cache_lock = RLock()

    @staticmethod
    def factory():
        return Location().get_latlng

    def get_latlng(self, tuple_data, lat_or_long):
        if not Location.LATLNG in tuple_data:
            tuple_data[Location.LATLNG] = Location.extract_latlng(tuple_data)
        val = None
        if tuple_data[Location.LATLNG] != None:
            if lat_or_long == Location.LAT:
                val = tuple_data[Location.LATLNG][0]
            elif lat_or_long == Location.LNG:
                val = tuple_data[Location.LATLNG][1]
        return val
    
    @staticmethod
    def extract_latlng(tuple_data):
        latlng = None
        if tuple_data["coordinates"] != None:
            coords = tuple_data["coordinates"]["coordinates"]
            latlng = (coords[1], coords[0])
        if latlng == None:
            loc = tuple_data["user"].location
            if (loc != None) and (loc != ""):
                loc = loc.lower()
                Location.cache_lock.acquire()
                latlng = Location.cache.get(loc, None)
                Location.cache_lock.release()
                if latlng == None:
                    latlng = Location.geonames_latlng(loc)
                Location.cache_lock.acquire()
                Location.cache[loc] = latlng
                Location.cache.compact_to_size(10000)
                Location.cache_lock.release()
        return latlng

    @staticmethod
    def geonames_latlng(loc):
        latlng = None
        try:
            g = Location.gn.geocode(loc.encode('utf-8'), exactly_one=False)
            if g is not None:
                for place, (lat, lng) in g:
                    latlng = (lat, lng)
                    break
        except URLError:
            e = sys.exc_info()[1]
            print "Unable to connect to GeoNames: %s" % (e)
        return latlng

class MeanOutliers():
    return_type = ReturnType.FLOAT

    class MeanGroup():
        def __init__(self):
            self.n = 0
            self.ewma = 0.0 # exponentially weighted moving avgerage
            self.ewmmd = 0.0 # exponentially weighted moving mean deviation
        def update_and_calculate(self, value):
            """
                Returns the number of mean deviations from the EWMA if
                the number of values previously recorded is >= 5.  Otherwise,
                returns -1.

                Updates the EWMA and EWMMD after calculating how many median deviations
                away the result is.
            """
            retval = -1
            diff = abs(self.ewma - value)
            if self.n >= 5: # only calculate meandevs if collected > 5 data pts.
                if self.ewmmd > 0:
                    meandevs = diff/self.ewmmd
                else:
                    meandevs = diff/.00001
                retval = meandevs
            
            # update ewma/ewmmd
            self.n += 1
            if self.n > 1:
                if self.n > 2:
                    self.ewmmd = (.125*diff) + (.875*self.ewmmd)
                else:
                    self.ewmmd = diff
                self.ewma = (.125*value) + (.875*self.ewma)
            else:
                self.ewma = value
            return retval 

    @staticmethod
    def factory():
        return MeanOutliers().nummeandevs

    def __init__(self):
        self.groups = dict()

    def nummeandevs(self, tuple_data, value, *group):
        """ 
            Calculates how many mean deviations from the exponentially 
            weighted moving average value is, given the other values that have been 
            given for the elements of this group.

            Uses the method TCP utilizes to estimate the round trip time 
            and mean deviation time of a potentially congested packet:
            http://tools.ietf.org/html/rfc2988

            The return value will be greater than or equal to 0 
            if it represents the number of mean deviations the value was away
            from the exponentially weighted moving average.
            If it is less than 0, the group does not have enough data to
            calculate mean deviations.

            What is a good outlier value?  If your data is normally distributed, then
            I experimentally found that 1 mean deviation is .8 standard deviations.
            For normally distributed data, 68% of values are within 1 standard
            deviation, 95% of values are within 2, and nearly 100% are within 3.
            Thus, 68% of values are within 1.25 mean deviations, 95% are within
            2.5 mean deviations, and almost 100% are within 3.75 mean deviations.
            A good mean deviation cutoff for legitimate values is thus in the range
            2.5-3.75.
        """
        mean_group = self.groups.get(group, None)
        if mean_group == None:
            mean_group = MeanOutliers.MeanGroup()
            self.groups[group] = mean_group

        return mean_group.update_and_calculate(value)

def register_default_functions():
    fr = FunctionRegistry()
    fr.register("temperatureF", FunctionInformation(Temperature.factory, Temperature.return_type))
    fr.register("tweetLatLng", FunctionInformation(Location.factory, Location.return_type))
    fr.register("floor", FunctionInformation(Rounding.factory, Rounding.return_type))
    fr.register("strlen", FunctionInformation(StringLength.factory, StringLength.return_type))
    fr.register("meanDevs", FunctionInformation(MeanOutliers.factory, MeanOutliers.return_type))
    fr.register("sentiment", FunctionInformation(Sentiment.factory, Sentiment.return_type))


########NEW FILE########
__FILENAME__ = exceptions
class TweeQLException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class QueryException(TweeQLException):
    pass

class DbException(TweeQLException):
    pass

class SettingsException(TweeQLException):
    pass

########NEW FILE########
__FILENAME__ = analysis
from nltk.classify import NaiveBayesClassifier
from nltk.corpus import movie_reviews, stopwords
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist

import gzip
import os
import pickle
import re
import nltk

POSITIVE = "4"
NEGATIVE = "0"
NEUTRAL = "2"

mention_re = re.compile(ur"\@\S+", re.UNICODE)
url_re = re.compile(ur"((mailto\:|(news|(ht|f)tp(s?))\://){1}\S+)", re.UNICODE)
emoticon_re = re.compile(ur"\:\)|\:\-\)|\: \)|\:D|\=\)|\:\(\:\-\(\: \(", re.UNICODE)
tokenizer = nltk.RegexpTokenizer(r'\w+')

def word_feats(words):
    return dict([(word, True) for word in words])

def words_in_tweet(inputstr):
    outputstr = inputstr
    outputstr = mention_re.sub("MENTION_TOKEN", outputstr)
    outputstr = url_re.sub("URL_TOKEN", outputstr)
    outputstr = emoticon_re.sub("", outputstr)
    outputstr = outputstr.lower()
    return tokenizer.tokenize(outputstr)

# from http://groups.google.com/group/nltk-users/browse_thread/thread/be28ed12f87384ea
# Save Classifier 
def save_classifier(classifier): 
    fModel = open('BayesModel.pkl',"wb") 
    pickle.dump(classifier, fModel,1) 
    fModel.close() 
    os.system("rm BayesModel.pkl.gz") 
    os.system("gzip BayesModel.pkl") 
# Load Classifier
def load_classifier(): 
    os.system("gunzip BayesModel.pkl.gz") 
    fModel = open('BayesModel.pkl',"rb") 
    classifier = pickle.load(fModel) 
    fModel.close() 
    os.system("gzip BayesModel.pkl") 
    return classifier
# Package classifier for actual use
def package_classifier(to_pickle):
    fp = gzip.open('sentiment.pkl.gz', 'wb')
    pickle.dump(to_pickle, fp, 1)
    fp.close()

########NEW FILE########
__FILENAME__ = package
from analysis import load_classifier, package_classifier, POSITIVE, NEUTRAL, NEGATIVE

classifier = load_classifier()
package_classifier({"classifier": classifier,
                    "pos_cutoff": 0.84,
                    "neg_cutoff": 0.66,
                    "pos_label": POSITIVE,
                    "neut_label": NEUTRAL,
                    "neg_label": NEGATIVE,
                    "pos_recall": 0.462963,
                    "pos_precision": 0.793651,
                    "neg_recall": 0.653333,
                    "neg_precision": 0.790323,
                   })

########NEW FILE########
__FILENAME__ = test-nltk
from analysis import load_classifier, words_in_tweet, POSITIVE, NEGATIVE, NEUTRAL, word_feats
import collections
import datetime
import nltk

def drange(start, stop, step):
    r = start
    while r <= stop:
        yield r
        r += step

testfile = open('testdata.manual.2009.05.25')

print "Loading classifier"
classifier = load_classifier()

print "Running test"
print "prob, pos prec, pos rec, neg prec, neg rec"
for prob in drange(0.5, 1.0, .01):
    right = 0
    wrong = 0
    refsets = collections.defaultdict(set)
    testsets = collections.defaultdict(set)
    testfile.seek(0)
    count = 0
    for line in testfile:
        parts = line.split(";;")
        dist = classifier.prob_classify(word_feats(words_in_tweet(parts[5])))
        if dist.prob(dist.max()) > prob:
            realguess = dist.max()
        else:
            realguess = NEUTRAL
        refsets[parts[0]].add(count)
        testsets[realguess].add(count)
        count += 1
    print "%f, %f, %f, %f, %f" % (prob, nltk.metrics.precision(refsets[POSITIVE], testsets[POSITIVE]), nltk.metrics.recall(refsets[POSITIVE],testsets[POSITIVE]), nltk.metrics.precision(refsets[NEGATIVE], testsets[NEGATIVE]), nltk.metrics.recall(refsets[NEGATIVE], testsets[NEGATIVE]))

########NEW FILE########
__FILENAME__ = train-nltk
from analysis import save_classifier, words_in_tweet, POSITIVE, NEGATIVE, NEUTRAL
from nltk.metrics.association import BigramAssocMeasures

import collections, itertools
import datetime
import nltk
import nltk.classify.util, nltk.metrics
import os
import pickle
import re


# lots of stuff from http://streamhacker.com/2010/06/16/text-classification-sentiment-analysis-eliminate-low-information-features/
# and http://nltk.googlecode.com/svn/trunk/doc/book/ch06.html

#smilefile = open('smiley.txt.processed.2009.05.25')
#frownfile = open('frowny.txt.processed.2009.05.25')
smilefile = open('happy.txt')
frownfile = open('sad.txt')

def features(feat_func, handle, label):
    print "Generating features for '%s'" % (label)
    print datetime.datetime.now()
    return [((feat_func(words_in_tweet(line))), label) for line in handle]

def update_wordcount(word_fd, label_word_fd, handle, label):
    print "Counting '%s'" % (label)
    print datetime.datetime.now()
    for line in handle:
        for word in words_in_tweet(line):
            word_fd.inc(word)
            label_word_fd[label].inc(word)
    handle.seek(0)

word_fd = nltk.probability.FreqDist()
label_word_fd = nltk.probability.ConditionalFreqDist()
update_wordcount(word_fd, label_word_fd, smilefile, POSITIVE)
update_wordcount(word_fd, label_word_fd, frownfile, NEGATIVE)

pos_word_count = label_word_fd[POSITIVE].N()
neg_word_count = label_word_fd[NEGATIVE].N()
total_word_count = pos_word_count + neg_word_count

print "Finding top words"
word_scores = {}
for word, freq in word_fd.iteritems():
    pos_score = BigramAssocMeasures.chi_sq(label_word_fd[POSITIVE][word],
        (freq, pos_word_count), total_word_count)
    neg_score = BigramAssocMeasures.chi_sq(label_word_fd[NEGATIVE][word],
        (freq, neg_word_count), total_word_count)
    word_scores[word] = pos_score + neg_score

best = sorted(word_scores.iteritems(), key=lambda (w,s): s, reverse=True)[:10000]
bestwords = set([w for w, s in best])
print "Best words"
#print bestwords
def best_word_feats(words):
    return dict([(word, True) for word in words if word in bestwords])

posfeats = features(best_word_feats, smilefile, POSITIVE)
negfeats = features(best_word_feats, frownfile, NEGATIVE)
classifier = nltk.NaiveBayesClassifier.train(posfeats + negfeats)
save_classifier(classifier)

########NEW FILE########
__FILENAME__ = field_descriptor
class FieldType():
    AGGREGATE = "AGGREGATE"  # Returns an aggregate
    FUNCTION = "FUNCTION"    # Returns a function over a field
    FIELD = "FIELD"          # Returns a field from the tuple
    LITERAL = "LITERAL"      # Returns a literal (string, int, or float)
    UNDEFINED = "UNDEFINED"  # Not a legitimate field---shouldn't appear in parsed query

class ReturnType():
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    DATETIME = "DATETIME"
    UNDEFINED = "UNDEFINED"  # Not a legitimate type---shouldn't appear in parsed query

class FieldDescriptor():
    def __init__(self, alias, underlying_fields, field_type, return_type, aggregate_factory=None, func_factory=None, literal_value=None):
        self.alias = alias
        self.underlying_fields = underlying_fields
        self.field_type = field_type
        self.return_type = return_type
        self.aggregate_factory = aggregate_factory
        self.func_factory = func_factory
        self.function = None
        if func_factory != None:
            self.function = func_factory()
        self.literal_value = literal_value
        self.visible = True
    def __eq__(self, other):
        if isinstance(other, FieldDescriptor):
            return (self.alias == other.alias) and \
               (self.underlying_fields == other.underlying_fields) and \
               (self.field_type == other.field_type) and \
               (self.return_type == other.return_type) and \
               (self.aggregate_factory == other.aggregate_factory) and \
               (self.func_factory == other.func_factory) and \
               (self.literal_value == other.literal_value)
        else:
            return NotImplemented
    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result

########NEW FILE########
__FILENAME__ = function_registry
from tweeql.exceptions import QueryException

class FunctionInformation():
    def __init__(self, func_factory, return_type):
        self.func_factory = func_factory
        self.return_type = return_type

class FunctionRegistry():
    __shared_dict = dict()
    def __init__(self):
        self.__dict__ = self.__shared_dict
        if len(self.__shared_dict.keys()) == 0:
            self.__functions = dict()
    def register(self, alias, function_information):
        if alias in self.__functions:
            raise QueryException("'%s' has already been registered" % (alias))
        self.__functions[alias] = function_information
    def get_function(self, alias):
        if alias not in self.__functions:
            raise QueryException("'%s' is not a registered function" % (alias))
        return self.__functions[alias]

########NEW FILE########
__FILENAME__ = operators
from aggregation import Aggregator
from field_descriptor import FieldDescriptor
from query import QueryTokens
from twitter_fields import TwitterFields

class StatusSource(object):
    TWITTER_FILTER = 1
    TWITTER_SAMPLE = 2

class QueryOperator(object):
    """
        QueryOperator represents an operator in the stream query plan.
        Anyone who implements this class should implement the filter method,
        which takes a list of updates on the stream and returns the ones
        which match the filter.
    """
    def __init__(self):
        pass
    def filter(self, updates, return_passes, return_fails):
        raise  NotImplementedError()
    def filter_params(self):
        """
            Returns a tuple with lists: (follow_ids, track_words)
        """
        raise  NotImplementedError()
    def assign_descriptor(self, tuple_descriptor):
        raise NotImplementedError()
    def can_query_stream(self):
        return False
    def get_tuple_descriptor(self):
        return self.tuple_descriptor

class AllowAll(QueryOperator):
    """
        Allows all updates to pass this filter
    """
    def __init__(self):
        QueryOperator.__init__(self)
    def filter(self, updates, return_passes, return_fails):
        passes = updates
        for update in passes:
            update.set_tuple_descriptor(self.tuple_descriptor)
        fails = []
        if not return_passes:
            passes = None
        if not return_fails:
            fails = None
        return (passes, fails)
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor

class And(QueryOperator):
    """
        Logical AND between the operators that make up its children.
    """
    def __init__(self, children):
        QueryOperator.__init__(self)
        self.children = children
        self.can_query_stream_cache = self.can_query_stream_impl()
    def filter(self, updates, return_passes, return_fails):
        passes = updates
        fails = []
        for child in self.children:
            (passes, fails_local) = child.filter(passes, True, return_fails)
            if return_fails:
                fails.extend(fails_local)
        if not return_passes:
            passes = None
        if not return_fails:
            fails = None
        return (passes, fails)
    def filter_params(self):
        for child in self.children:
            if child.can_query_stream():
                return child.filter_params()
    def can_query_stream(self):
        return self.can_query_stream_cache
    def can_query_stream_impl(self):
        for child in self.children:
            if child.can_query_stream():
                return True
        return False
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor
        for child in self.children:
            child.assign_descriptor(tuple_descriptor)

class Or(QueryOperator):
    """
        Logical OR between the operators that make up its children.
    """
    def __init__(self, children):
        QueryOperator.__init__(self)
        self.children = children
        self.can_query_stream_cache = self.can_query_stream_impl()
    def filter(self, updates, return_passes, return_fails):
        passes = []
        fails = updates
        for child in self.children:
            (passes_local, fails) = child.filter(fails, return_passes, True)
            if return_passes:
                passes.extend(passes_local)
        if not return_passes:
            passes = None
        if not return_fails:
            fails = None
        return (passes, fails)
    def filter_params(self):
        (follow_ids, track_words) = ([], []) 
        for child in self.children:
            if child.can_query_stream():
                (follow_local, track_local) = child.filter_params()
                if follow_local != None:
                    follow_ids.extend(follow_local)
                if track_local != None:
                    track_words.extend(track_local)
        return (follow_ids, track_words)
    def can_query_stream(self):
        return self.can_query_stream_cache
    def can_query_stream_impl(self):
        for child in self.children:
            if not child.can_query_stream():
                return False
        return True
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor
        for child in self.children:
            child.assign_descriptor(tuple_descriptor)

class Not(QueryOperator):
    """
        Logical NOT on the child operator.
    """
    def __init__(self, child):
        QueryOperator.__init__(self)
        self.child = child
    def filter(self, updates, return_passes, return_fails):
        (passes, fails) = self.child.filter(updates, return_fails, return_passes)
        return (fails, passes)
    def filter_params(self):
        return self.child.filter_params()
    def can_query_stream(self):
        return self.child.can_query_stream()
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor
        self.child.assign_descriptor(tuple_descriptor)

class Follow(QueryOperator):
    """
        Passes updates which contain people in the follower list.
    """
    def __init__(self, ids):
        QueryOperator.__init__(self)
        self.ids = set(ids)
    def filter(self, updates, return_passes, return_fails):
        passes = [] if return_passes else None
        fails = [] if return_fails else None
        for update in updates:
            update.set_tuple_descriptor(self.tuple_descriptor)
            if update.author in self.ids:
                if return_passes:
                    passes.append(update.author)
            elif return_fails:
                fails.append(update.author)
        return (passes, fails)
    def filter_params(self):
        return (self.ids, None)
    def can_query_stream(self):
        return True 
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor

class Contains(QueryOperator):
    """
        Passes updates which contain the desired term.  Matching is case-insensitive.
    """
    def __init__(self, field_alias, term):
        QueryOperator.__init__(self)
        self.alias = field_alias
        self.term = term.lower()
    def filter(self, updates, return_passes, return_fails):
        passes = [] if return_passes else None
        fails = [] if return_fails else None
        for update in updates:
            update.set_tuple_descriptor(self.tuple_descriptor)
            if self.term in getattr(update, self.alias).lower():
                if return_passes:
                    passes.append(update)
            elif return_fails:
                fails.append(update)
        return (passes, fails)
    def filter_params(self):
        return (None, [self.term])
    def can_query_stream(self):
        if self.alias == TwitterFields.TEXT:
            return True
        else:
            return False
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor

class Equals(QueryOperator):
    """
        Passes updates which equal the desired term.  Matching is case-sensitive.
    """
    def __init__(self, field_alias, term):
        QueryOperator.__init__(self)
        self.alias = field_alias
        self.term = term
    def filter(self, updates, return_passes, return_fails):
        passes = [] if return_passes else None
        fails = [] if return_fails else None
        for update in updates:
            update.set_tuple_descriptor(self.tuple_descriptor)
            if self.term == getattr(update, self.alias):
                if return_passes:
                    passes.append(update)
            elif return_fails:
                fails.append(update)
        return (passes, fails)
    def filter_params(self):
        return (None, [self.term])
    def can_query_stream(self):
        if self.alias == TwitterFields.TEXT:
            return True
        else:
            return False
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor

class Location(QueryOperator):
    """
        Passes updates which are located in a geographic bounding box
    """
    def __init__(self, xmin, xmax, ymin, ymax):
        QueryOperator.__init__(self)
        (self.xmin, self.xmax, self.ymin, self.ymax) = (xmin, xmax, ymin, ymax)
    def filter(self, updates, return_passes, return_fails):
        passes = [] if return_passes else None
        fails = [] if return_fails else None
        for update in updates:
            update.set_tuple_descriptor(self.tuple_descriptor)
            x = update.geo.x
            y = update.geo.y
            if x >= xmin and x <= xmax and y >= ymin and y <= ymax:
                if return_passes:
                    passes.append(update)
            elif return_fails:
                fails.append(update)
        return (passes, fails)
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor

class GroupBy(QueryOperator):
    """
        Groups results from child by some set of fields, and runs the aggregate 
        function(s) over them, emitting results and resetting buckets every
        window seconds.
    """
    def __init__(self, child, groupby, aggregates, window):
        QueryOperator.__init__(self)
        self.child = child
        self.can_query_stream_cache = self.can_query_stream_impl()
        self.groupby = groupby
        self.aggregates = aggregates
        self.window = window
        self.aggregator = Aggregator(self.aggregates, self.groupby, self.window)
    def filter(self, updates, return_passes, return_fails):
        if return_passes:
            (passes, fails) = self.child.filter(updates, return_passes, return_fails)
            new_emissions = []
            new_emissions.extend(self.aggregator.update(passes))
            return (new_emissions, None)
        else:
            return (None, None)
    def filter_params(self):
        return self.child.filter_params()
    def can_query_stream(self):
        return self.can_query_stream_cache
    def can_query_stream_impl(self):
        return self.child.can_query_stream()
    def assign_descriptor(self, tuple_descriptor):
        self.tuple_descriptor = tuple_descriptor
        self.aggregator.tuple_descriptor = tuple_descriptor
        with_aggregates = self.groupby.duplicate()
        for aggregate in self.aggregates:
            with_aggregates.add_descriptor(aggregate)
        with_aggregates.add_descriptor(TwitterFields.created_field)
        for alias, fd in tuple_descriptor.descriptors.items():
            with_aggregates.add_descriptor(fd)
        self.child.assign_descriptor(with_aggregates)

########NEW FILE########
__FILENAME__ = query
class Query():
    def __init__(self, query_tree, source, handler):
        self.query_tree = query_tree
        self.source = source
        self.handler = handler
    def get_tuple_descriptor(self):
        return self.query_tree.get_tuple_descriptor()

class QueryTokens:
    SELECT = "SELECT"
    FROM = "FROM"
    WHERE = "WHERE"
    GROUPBY = "GROUP BY"
    INTO = "INTO"
    WINDOW = "WINDOW"
    TWITTER = "TWITTER"
    TWITTER_SAMPLE = "TWITTER_SAMPLE"
    LPAREN = "("
    RPAREN = ")"
    AND = "AND"
    OR = "OR"
    CONTAINS = "CONTAINS"
    AS = "AS"
    IN = "IN"
    AVG = "AVG"
    COUNT = "COUNT"
    SUM = "SUM"
    MIN = "MIN"
    MAX = "MAX"
    STDOUT = "STDOUT"
    TABLE = "TABLE"
    STREAM = "STREAM"
    EQUALS = "="
    DOUBLE_EQUALS = "=="
    EXCLAIM_EQUALS = "!="
    NULL = "NULL"
    EMPTY_STRING = ""
    STRING_LITERAL = "$$$STRING_LITERAL$$$"
    INTEGER_LITERAL = "$$$INTEGER_LITERAL$$$"
    FLOAT_LITERAL = "$$$FLOAT_LITERAL$$$"
    NULL_TOKEN = "$$$NULL_TOKEN$$$"
    WHERE_CONDITION = "$$$WHERE_CONDITION$$$"
    FUNCTION_OR_AGGREGATE = "$$$FUNCTION_OR_AGGREGATE$$$"
    COLUMN_NAME = "$$$COLUMN_NAME$$$"

########NEW FILE########
__FILENAME__ = query_builder
from itertools import chain
from pyparsing import ParseException
from tweeql import operators
from tweeql.aggregation import get_aggregate_factory
from tweeql.operators import StatusSource
from tweeql.exceptions import QueryException
from tweeql.exceptions import DbException
from tweeql.field_descriptor import FieldDescriptor
from tweeql.field_descriptor import FieldType
from tweeql.field_descriptor import ReturnType
from tweeql.function_registry import FunctionRegistry
from tweeql.query import Query
from tweeql.query import QueryTokens
from tweeql.tweeql_parser import gen_parser
from tweeql.status_handlers import PrintStatusHandler
from tweeql.status_handlers import DbInsertStatusHandler
from tweeql.tuple_descriptor import TupleDescriptor
from tweeql.twitter_fields import twitter_tuple_descriptor

def gen_query_builder():
    return QueryBuilder()

class QueryBuilder:
    """
        Generates a query from a declarative specification in a SQL-like syntax.
        This class is not thread-safe
    """
    def __init__(self):
        self.parser = gen_parser()
        self.function_registry = FunctionRegistry()
        self.unnamed_operator_counter = 0
        self.twitter_td = twitter_tuple_descriptor()
    def build(self, query_str):
        """
            Takes a Unicode string query_str, and outputs a query tree
        """
        try:
            parsed = self.parser.parseString(query_str)
        except ParseException,e:
            raise QueryException(e)

        source = self.__get_source(parsed)
        tree = self.__get_tree(parsed)
        handler = self.__get_handler(parsed)
        query = Query(tree, source, handler)
        return query
    def __get_source(self, parsed):
        source = parsed.sources[0]
        if source == QueryTokens.TWITTER:
            return StatusSource.TWITTER_FILTER
        elif source.startswith(QueryTokens.TWITTER_SAMPLE):
            return StatusSource.TWITTER_SAMPLE
        else:
            raise QueryException('Unknown query source: %s' % (source))
    def __get_tree(self, parsed):
        select = parsed.select.asList()[1:][0]
        where_clause = parsed.where.asList()
        groupby = parsed.groupby.asList()
        window = parsed.window.asList()
        window = None if window == [''] else window[1:]
        (tree, where_fields) = self.__parse_where(where_clause)
        tree = self.__add_select_and_aggregate(select, groupby, where_fields, window, tree)
        return tree
    def __get_handler(self, parsed):
        into = parsed.into.asList()
        handler = None
        if (into == ['']) or (into[1] == QueryTokens.STDOUT):
            handler = PrintStatusHandler(1)
        elif (len(into) == 3) and (into[1] == QueryTokens.TABLE):
            handler = DbInsertStatusHandler(1000, into[2])
        elif (len(into) == 3) and (into[1] == QueryTokens.STREAM):
            raise DbException("Putting results into a STREAM is not yet supported")
        else:
            raise QueryException("Invalid INTO clause")
        return handler
    def __parse_where(self, where_clause):
        tree = None
        where_fields = []
        if where_clause == ['']: # no where predicates
            tree = operators.AllowAll() 
        else:
            tree = self.__parse_clauses(where_clause[0][1:], where_fields)
        return (tree, where_fields)
    def __parse_clauses(self, clauses, where_fields):
        """
            Parses the WHERE clauses in the query.  Adds any fields it discovers to where_fields
        """
        self.__clean_list(clauses)
        if type(clauses) != list: # This is a token, not an expression 
            return clauses
        elif clauses[0] == QueryTokens.WHERE_CONDITION: # This is an operator expression
            return self.__parse_operator(clauses[1:], where_fields)
        else: # This is a combination of expressions w/ AND/OR
            # ands take precedent over ors, so 
            # A and B or C and D -> (A and B) or (C and D)
            ands = []
            ors = []
            i = 0
            while i < len(clauses):
                ands.append(self.__parse_clauses(clauses[i], where_fields))
                if i+1 == len(clauses):
                    ors.append(self.__and_or_single(ands))
                else:
                    if clauses[i+1] == QueryTokens.OR:
                        ors.append(self.__and_or_single(ands))
                        ands = []
                    elif clauses[i+1] == QueryTokens.AND:
                        pass
                i += 2
            # TODO: rewrite __and_or_single to handle the ors below just
            # like it does the ands above 
            if len(ors) == 1:
                return ors[0]
            else:
                return operators.Or(ors)
    def __parse_operator(self, clause, where_fields):
        if len(clause) == 3 and clause[1] == QueryTokens.CONTAINS:
            alias = self.__where_field(clause[0], where_fields)
            return operators.Contains(alias, self.__parse_rval(clause[2], allow_null=False))
        elif len(clause) == 3 and ((clause[1] == QueryTokens.EQUALS) or (clause[1] == QueryTokens.DOUBLE_EQUALS)):
            alias = self.__where_field(clause[0], where_fields)
            return operators.Equals(alias, self.__parse_rval(clause[2], allow_null=True))
        elif len(clause) == 3 and clause[1] == QueryTokens.EXCLAIM_EQUALS:
            alias = self.__where_field(clause[0], where_fields)
            return operators.Not(operators.Equals(alias, self.__parse_rval(clause[2], allow_null=True)))
    def __parse_rval(self, val, allow_null):
        if val == QueryTokens.NULL_TOKEN:
            if allow_null:
                return None
            else:
                raise QueryException("NULL appears in clause where it should not.")
        else:
            return val
    def __where_field(self, field, where_fields):
        (field_descriptors, verify) = self.__parse_field(field, self.twitter_td, False, False)
        alias = field_descriptors[0].alias
        # name the field whatever alias __parse_field gave it so it can be
        # passed to __parse_field in the future and have a consistent name
        if not ((len(field) >= 4) and (field[-2] == QueryTokens.AS)):
            field.append(QueryTokens.AS)
            field.append(alias)
        where_fields.append(field)
        return alias
    def __clean_list(self, list):
        self.__remove_all(list, QueryTokens.LPAREN)
        self.__remove_all(list, QueryTokens.RPAREN)

    def __remove_all(self, list, token):
        while token in list:
            list.remove(token)
    def __and_or_single(self, ands):
        if len(ands) == 1:
            return ands[0]
        else:
            return operators.And(ands)
    def __add_select_and_aggregate(self, select, groupby, where, window, tree):
        """
            select, groupby, and where are a list of unparsed fields
            in those respective clauses
        """
        tuple_descriptor = TupleDescriptor()
        fields_to_verify = []
        all_fields = chain(select, where)
        if groupby != ['']:
            groupby = groupby[1:][0]
            all_fields = chain(all_fields, groupby)
        self.__remove_all(groupby, QueryTokens.EMPTY_STRING)     
        for field in all_fields:
            (field_descriptors, verify) = self.__parse_field(field, self.twitter_td, True, False)
            fields_to_verify.extend(verify)
            tuple_descriptor.add_descriptor_list(field_descriptors)
        for field in fields_to_verify:
            self.__verify_and_fix_field(field, tuple_descriptor)
        
        # at this point, tuple_descriptor should contain a tuple descriptor
        # with fields/aliases that are correct (we would have gotten an
        # exception otherwise.  built select_descriptor/group_descriptor
        # from it
        select_descriptor = TupleDescriptor()
        group_descriptor = TupleDescriptor()
        aggregates = []
        for field in select:
            (field_descriptors, verify) = self.__parse_field(field, tuple_descriptor, True, True)
            select_descriptor.add_descriptor_list(field_descriptors)
            if field_descriptors[0].field_type == FieldType.AGGREGATE:
                aggregates.append(field_descriptors[0])
        # add WHERE clause fields as invisible attributes
        for field in where:
            (field_descriptors, verify) = self.__parse_field(field, tuple_descriptor, True, False)
            select_descriptor.add_descriptor_list(field_descriptors)
        if len(aggregates) > 0:
            if window == None:
                raise QueryException("Aggregate expression provided with no WINDOW parameter")
            for field in groupby:
                (field_descriptors, verify) = self.__parse_field(field, tuple_descriptor, True, True)
                group_descriptor.add_descriptor_list(field_descriptors)
            for alias in select_descriptor.aliases:
                select_field = select_descriptor.get_descriptor(alias)
                group_field = group_descriptor.get_descriptor(alias)
                if group_field == None and \
                   select_field.field_type != FieldType.AGGREGATE and \
                   select_field.visible:
                    raise QueryException("'%s' appears in the SELECT but is is neither an aggregate nor a GROUP BY field" % (alias))
            tree = operators.GroupBy(tree, group_descriptor, aggregates, window)
        tree.assign_descriptor(select_descriptor)
        return tree
    def __parse_field(self, field, tuple_descriptor, alias_on_complex_types, make_visible):
        """
            Returns a tuple containing (field_descriptors, fieldnames_to_verify)

            The first field in field_descriptors is the one requested to be parsed by this
            function call.  If the field turns out to be an aggregate or a user-defined
            function call, then field_descriptors will contain those parsed field descriptors
            as well, with their visible flag set to False.  

            fieldnames_to_verify is a list of field names that should be verified in order
            to ensure that at some point their alias is defined in an AS clause.
        """
        alias = None
        field_type = None
        return_type = None
        underlying_fields = None
        aggregate_factory = None
        literal_value = None
        func_factory = None
        fields_to_verify = []
        parsed_fds = []
        field_backup = list(field)
        self.__clean_list(field)
        
        # parse aliases if they exist
        if (len(field) >= 4) and (field[-2] == QueryTokens.AS):
            alias = field[-1]
            field = field[:-2]
        if (field[0] == QueryTokens.STRING_LITERAL) or \
           (field[0] == QueryTokens.INTEGER_LITERAL) or \
           (field[0] == QueryTokens.FLOAT_LITERAL): 
            alias = self.unnamed_operator_name()
            underlying_fields = []
            field_type = FieldType.LITERAL
            literal_value = field[1]
            if field[0] == QueryTokens.STRING_LITERAL:
                return_type = ReturnType.STRING
            elif field[0] == QueryTokens.INTEGER_LITERAL:
                return_type = ReturnType.INTEGER
                literal_value = int(literal_value)
            elif field[0] == QueryTokens.FLOAT_LITERAL:
                return_type = ReturnType.FLOAT
                literal_value = float(literal_value)
        elif field[0] == QueryTokens.COLUMN_NAME: # field or alias
            if alias == None:
                alias = field[1]
            field_descriptor = tuple_descriptor.get_descriptor(field[1])
            if field_descriptor == None: # underlying field not yet defined.  mark to check later
                field_type = FieldType.UNDEFINED
                underlying_fields = [field[1]]
                # check alias and underlying once this process is done to
                # find yet-undefined fields
                fields_to_verify.append(field[1])
                fields_to_verify.append(alias)
            else: # field found, copy information
                field_type = field_descriptor.field_type
                return_type = field_descriptor.return_type
                underlying_fields = field_descriptor.underlying_fields
                aggregate_factory = field_descriptor.aggregate_factory
                func_factory = field_descriptor.func_factory
        elif field[0] == QueryTokens.FUNCTION_OR_AGGREGATE: # function or aggregate  
            if alias == None:
                if alias_on_complex_types:
                    raise QueryException("Must specify alias (AS clause) for '%s'" % (field[1]))
                else:
                    alias = self.unnamed_operator_name()
            underlying_field_list = field[2:]
            underlying_fields = []
            for underlying in underlying_field_list:
                (parsed_fd_list, parsed_verify) = self.__parse_field(underlying, tuple_descriptor, False, False)
                for parsed_fd in parsed_fd_list:
                    parsed_fd.visible = False
                fields_to_verify.extend(parsed_verify)
                parsed_fds.extend(parsed_fd_list)
                underlying_fields.append(parsed_fd_list[0].alias)
            aggregate_factory = get_aggregate_factory(field[1])
            if aggregate_factory != None: # found an aggregate function
                field_type = FieldType.AGGREGATE
                return_type = ReturnType.FLOAT
            else:
                function_information = self.function_registry.get_function(field[1])
                if function_information != None:
                    field_type = FieldType.FUNCTION
                    func_factory = function_information.func_factory
                    return_type = function_information.return_type
                else:
                    raise QueryException("'%s' is neither an aggregate or a registered function" % (field[1]))
        else:
            raise QueryException("Empty field clause found: %s" % ("".join(field_backup)))
        fd = FieldDescriptor(alias, underlying_fields, field_type, return_type, aggregate_factory, func_factory, literal_value)
        fd.visible = make_visible
        parsed_fds.insert(0, fd)
        return (parsed_fds, fields_to_verify)
    
    def __verify_and_fix_field(self, field, tuple_descriptor):
        field_descriptor = tuple_descriptor.get_descriptor(field)
        error = False
        if field_descriptor == None:
            error = True
        elif field_descriptor.field_type == FieldType.UNDEFINED:
            if field == field_descriptor.underlying_fields[0]:
                error = True
            else:
                referenced_field_descriptor = \
                    self.__verify_and_fix_field(field_descriptor.underlying_fields[0],
                                                tuple_descriptor)
                field_descriptor.underlying_fields = referenced_field_descriptor.underlying_fields
                field_descriptor.field_type = referenced_field_descriptor.field_type
                field_descriptor.return_type = referenced_field_descriptor.return_type
                field_descriptor.aggregate_factory = referenced_field_descriptor.aggregate_factory
                field_descriptor.func_factory = referenced_field_descriptor.func_factory
                field_descriptor.function = referenced_field_descriptor.function
        if error:
            raise QueryException("Field '%s' is neither a builtin field nor an alias" % (field))
        else:
            return field_descriptor
    def unnamed_operator_name(self):
        self.unnamed_operator_counter += 1
        return "operand%d" % (self.unnamed_operator_counter)

########NEW FILE########
__FILENAME__ = query_runner
from getpass import getpass
from tweeql.builtin_functions import register_default_functions
from tweeql.exceptions import QueryException
from tweeql.exceptions import DbException
from tweeql.operators import StatusSource
from tweeql.query_builder import gen_query_builder
from tweeql.settings_loader import get_settings
from tweeql.tuple_descriptor import Tuple
from threading import RLock
from threading import Thread
from tweepy import Stream
from tweepy import StreamListener
from tweepy.auth import OAuthHandler

import time

settings = get_settings()

class QueryRunner(StreamListener):
    def __init__(self):
        register_default_functions()
        StreamListener.__init__(self)
        try:
			self.consumer_key = settings.CONSUMER_KEY
			self.consumer_secret = settings.CONSUMER_SECRET
			self.access_token = settings.ACCESS_TOKEN
			self.access_token_secret = settings.ACCESS_TOKEN_SECRET
        except AttributeError:
            print "Check if CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, and ACCESS_TOKEN_SECRET are defined in settings.py"
            self.consumer_key = raw_input('Consumer key: ')
            self.consumer_secret = getpass('Consumer secret: ')
            self.access_token = raw_input('Access token: ')
            self.access_token_secret = getpass('Access token secret: ')
        self.status_lock = RLock()
        self.statuses = []
        self.query_builder = gen_query_builder()
        self.stream = None
    def build_stream(self):
        if self.stream != None:
            self.stop_query()
            time.sleep(.01) # make sure old stream has time to disconnect
        oauth = OAuthHandler(self.consumer_key, self.consumer_secret)
        oauth.set_access_token(self.access_token, self.access_token_secret)
        self.stream = Stream(oauth, # do OAuthentication for stream
                             self, # this object implements StreamListener
                             timeout = 600, # reconnect if no messages in 600s
                             retry_count = 20, # try reconnecting 20 times
                             retry_time = 10.0, # wait 10s if no HTTP 200
                             snooze_time = 1.0) # wait 1s if timeout in 600s
    def run_built_query(self, query_built, async):
        self.build_stream()
        self.query = query_built
        self.query.handler.set_tuple_descriptor(self.query.get_tuple_descriptor())
        if self.query.source == StatusSource.TWITTER_FILTER:
            no_filter_exception = QueryException("You haven't specified any filters that can query Twitter.  Perhaps you want to query TWITTER_SAMPLE?")
            try:
                (follow_ids, track_words) = self.query.query_tree.filter_params()
                if (follow_ids == None) and (track_words == [None]):
                    raise no_filter_exception
                self.stream.filter(follow_ids, track_words, async)
            except NotImplementedError:
                raise no_filter_exception
        elif self.query.source == StatusSource.TWITTER_SAMPLE:
            self.stream.sample(None, async)
    def run_query(self, query_str, async):
        if isinstance(query_str, str):
            query_str = unicode(query_str, 'utf-8')
        query_built = self.query_builder.build(query_str)
        self.run_built_query(query_built, async)
    def stop_query(self):
        if self.stream != None:
            self.stream.disconnect()
            self.flush_statuses()
    def filter_statuses(self, statuses, query):
        (passes, fails) = query.query_tree.filter(statuses, True, False)
        query.handler.handle_statuses(passes)
    def flush_statuses(self):
        self.status_lock.acquire()
        if len(self.statuses) > 0:
            filter_func = lambda s=self.statuses, q=self.query: self.filter_statuses(s,q)
            t = Thread(target = filter_func)
            t.start()
            self.statuses = []
        self.status_lock.release()

    """ StreamListener methods """
    def on_status(self, status):
        self.status_lock.acquire()
        t = Tuple()
        t.set_tuple_descriptor(None)
        t.set_data(status.__dict__)
        self.statuses.append(t)
        if len(self.statuses) >= self.query.handler.batch_size:
            self.flush_statuses()
        self.status_lock.release()
    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True # keep stream alive
    def on_timeout(self):
        print 'Snoozing Zzzzzz'
    def on_limit(self, limit_data):
        print "Twitter rate-limited this query.  Since query start, Twitter dropped %d messages." % (limit_data)

########NEW FILE########
__FILENAME__ = settings_loader
import os
import sys

settings_cache = None

def get_settings():
    global settings_cache
    if settings_cache == None:
        sys.path.insert(0, os.getcwd())
        try:
            import settings
        except ImportError, e:
            print "It looks like you don't have a settings.py with basic project settings."
            sys.exit(-1)
        settings_cache = settings
        sys.path.pop(0)
    return settings_cache

########NEW FILE########
__FILENAME__ = status_handlers
from tweeql.exceptions import DbException
from tweeql.field_descriptor import ReturnType
from tweeql.exceptions import SettingsException
from tweeql.settings_loader import get_settings
from sqlalchemy import create_engine, Table, Column, Integer, Unicode, Float, DateTime, MetaData
from sqlalchemy.exc import ArgumentError, InterfaceError

settings = get_settings()

class StatusHandler(object):
    def __init__(self, batch_size):
        self.batch_size = batch_size
    def handle_statuses(self, statuses):
        raise NotImplementedError()
    def set_tuple_descriptor(self, descriptor):
        self.tuple_descriptor = descriptor

class PrintStatusHandler(StatusHandler):
    def __init__(self, batch_size):
        super(PrintStatusHandler, self).__init__(batch_size)
        try:
            self.delimiter = settings.DELIMITER
        except AttributeError as ae:
            self.delimiter = u"|"

    def handle_statuses(self, statuses):
        td = self.tuple_descriptor
        for status in statuses:
            vals = (unicode(val) for (alias, val) in status.as_iterable_visible_pairs())
            print self.delimiter.join(vals) + "\n"

class DbInsertStatusHandler(StatusHandler):
    engine = None

    def __init__(self, batch_size, tablename):
        super(DbInsertStatusHandler, self).__init__(batch_size)
        if DbInsertStatusHandler.engine == None:
            try:
                dburi = settings.DATABASE_URI
                dbconfig = None
                try:
                    dbconfig = settings.DATABASE_CONFIG
                except AttributeError:
                    pass
                kwargs = {'echo': False}
                if not dburi.startswith("sqlite"):
                    kwargs['pool_size'] = 1                    
                if dbconfig != None:
                    kwargs['connect_args'] = dbconfig
                DbInsertStatusHandler.engine = create_engine(dburi, **kwargs)
            except AttributeError, e:
                raise e
                raise SettingsException("To put results INTO a TABLE, please specify a DATABASE_URI in settings.py") 
            except ArgumentError, e:
                raise DbException(e)
        self.tablename = tablename

    def set_tuple_descriptor(self, descriptor):
        StatusHandler.set_tuple_descriptor(self, descriptor)
        metadata = MetaData()
        columns = []
        for alias in descriptor.aliases:
            desc = descriptor.get_descriptor(alias)
            if desc.visible:
                columns.append(self.db_col(alias, descriptor))
        columns.insert(0, Column('__id', Integer, primary_key=True))
        self.table = Table(self.tablename, metadata, *columns)
        try:
            metadata.create_all(bind=DbInsertStatusHandler.engine)
        except InterfaceError:
            raise SettingsException("Unable to connect to database.  Did you configure the connection properly?  Check DATABASE_URI and DATABASE_CONFIG in settings.py") 


        test = metadata.tables[self.tablename]
        self.verify_table()
   
    def db_col(self, alias, descriptor):
        return_type = descriptor.get_descriptor(alias).return_type
        type_val = None
        if return_type == ReturnType.INTEGER:
            type_val = Integer
        elif return_type == ReturnType.FLOAT:
            type_val = Float
        elif return_type == ReturnType.STRING:
            type_val = Unicode
        elif return_type == ReturnType.DATETIME:
            type_val = DateTime
        else:
            raise DbException("Unknown field return type: %s" % (return_type))
        return Column(alias, type_val)

    def verify_table(self):
        """
            Makes sure the table's schema is not different from the one in the database.
            This might happen if you try to load a query into a table which already
            exists and has a different schema.
        """
        metadata = MetaData()
        metadata.reflect(bind = DbInsertStatusHandler.engine)
        mine = str(self.table.columns)
        verified = str(metadata.tables[self.tablename].columns)
        if mine != verified:
            raise DbException("Table '%s' in the database has schema %s whereas the query's schema is %s" % (self.tablename, verified, mine)) 
 
    def handle_statuses(self, statuses):
        #from datetime import datetime
        #now = datetime.now()
        #print "handle called ", now 
        dicts = [dict(status.as_iterable_visible_pairs()) for status in statuses]
        conn = DbInsertStatusHandler.engine.connect()
        conn.execute(self.table.insert(), dicts)
        conn.close()
        #print "handle started ", now, " ended ", datetime.now()

########NEW FILE########
__FILENAME__ = tuple_descriptor
import copy
from field_descriptor import FieldDescriptor
from field_descriptor import FieldType
from field_descriptor import ReturnType
from tweeql.exceptions import QueryException

# fix deepcopy on instance methods
# see http://bugs.python.org/issue1515
import copy
import types

def _deepcopy_method(x, memo):
    return type(x)(x.im_func, copy.deepcopy(x.im_self, memo), x.im_class)
copy._deepcopy_dispatch[types.MethodType] = _deepcopy_method

class Tuple():
    def __init__(self):
        self.__tuple_descriptor = None
        self.__data = None
    def set_data(self, data):
        self.__data = data
    def set_tuple_descriptor(self, tuple_descriptor):
        self.__tuple_descriptor = tuple_descriptor
    def get_tuple_descriptor(self):
        return self.__tuple_descriptor
    def __getattr__(self, attr):
        field_descriptor = self.__tuple_descriptor.get_descriptor(attr)
        result = None
        if field_descriptor.field_type == FieldType.FUNCTION:
            uf = field_descriptor.underlying_fields
            func = field_descriptor.function
            args = [getattr(self, field) for field in uf]
            args.insert(0, self.__data)
            result = func(*args)
        elif field_descriptor.field_type == FieldType.LITERAL:
            result = field_descriptor.literal_value
        elif field_descriptor.underlying_fields[0] in self.__data:
            result = self.__data[field_descriptor.underlying_fields[0]]
        else:
            raise QueryException("Attribute not defined: %s" % (attr))
        if (field_descriptor.return_type == ReturnType.STRING) and isinstance(result, str):
            result = unicode(result)
        setattr(self, attr, result)
        return result
    def as_iterable_visible_pairs(self):
        for alias in self.__tuple_descriptor.aliases:
            if self.__tuple_descriptor.get_descriptor(alias).visible:
                yield (alias, getattr(self, alias))
    def generate_from_descriptor(self, tuple_descriptor):
        """
            Builds a new tuple from this one based on the tuple_descriptor that
            is passed in.
        """
        t = Tuple()
        d = {}
        t.set_data(d)
        for alias in tuple_descriptor.aliases:
            fields = self.__tuple_descriptor.get_descriptor(alias).underlying_fields
            for field in fields:
                setattr(t, field, getattr(self, field))
            setattr(t, alias, getattr(self, alias))
        t.set_tuple_descriptor(tuple_descriptor)
        return t
    def __hash__(self):
        if not self:
            return 0
        value = -1
        for alias in self.__tuple_descriptor.aliases:
            if self.__tuple_descriptor.get_descriptor(alias).visible:
                fieldval = hash(getattr(self, alias))
                if value == -1:
                    value = fieldval << 7
                else:
                    value = self.c_mul(1000003, value) ^ fieldval
        return value
    def __eq__(self, other):
        if isinstance(other, Tuple):
            if self.__tuple_descriptor is other.__tuple_descriptor: # strict object equality
                for alias in self.__tuple_descriptor.aliases:
                    if self.__tuple_descriptor.get_descriptor(alias).visible:
                        if getattr(self, alias) != getattr(other, alias):
                            return False
                return True
            else:
                return False
        else:
            return NotImplemented
    def c_mul(self, a, b):
        return eval(hex((long(a) * b) & 0xFFFFFFFFL)[:-1])

class TupleDescriptor():
    def __init__(self, field_descriptors = []):
        self.aliases = []
        self.descriptors = {}
        for descriptor in field_descriptors:
            self.add_descriptor(descriptor)
    def get_descriptor(self, alias):
        return self.descriptors.get(alias)
    def duplicate(self):
        return copy.deepcopy(self)
    def add_descriptor_list(self, descriptors):
        for descriptor in descriptors:
            self.add_descriptor(descriptor)
    def add_descriptor(self, descriptor):
        visible = descriptor.visible
        copy_descriptor = True
        if descriptor.alias in self.descriptors:
            if (self.descriptors[descriptor.alias].field_type != FieldType.UNDEFINED) and \
               (descriptor.field_type != FieldType.UNDEFINED) and \
               (self.descriptors[descriptor.alias] != descriptor):
                raise QueryException("The alias '%s' appears more than once in your query" % (descriptor.alias))
            # if one of the descriptors is visible, mark the stored one as
            # visible.
            visible = self.descriptors[descriptor.alias].visible or descriptor.visible
            if descriptor.field_type == FieldType.UNDEFINED:
                copy_descriptor = False
        else:
            self.aliases.append(descriptor.alias)
        if copy_descriptor:
            self.descriptors[descriptor.alias] = descriptor #copy.deepcopy(descriptor)
        self.descriptors[descriptor.alias].visible = visible

########NEW FILE########
__FILENAME__ = tweeql_parser
# Started with http://pyparsing.wikispaces.com/file/view/simpleSQL.py 
# ( Copyright (c) 2003, Paul McGuire ) and extended from there
#
from pyparsing import Literal, CaselessLiteral, Word, upcaseTokens, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, restOfLine, Keyword, removeQuotes, downcaseTokens
from tweeql.query import QueryTokens

def gen_parser():
    # define SQL tokens
    selectStmt = Forward()
    selectToken = Keyword(QueryTokens.SELECT, caseless=True)
    fromToken   = Keyword(QueryTokens.FROM, caseless=True)
    intoToken   = Keyword(QueryTokens.INTO, caseless=True)
    groupByToken   = Keyword(QueryTokens.GROUPBY, caseless=True)
    windowToken   = Keyword(QueryTokens.WINDOW, caseless=True)
    asToken = Keyword(QueryTokens.AS, caseless=True).setParseAction(upcaseTokens)
    nullToken = Keyword(QueryTokens.NULL, caseless=False).setParseAction(replace(QueryTokens.NULL_TOKEN))
    
    # Math operators
    E = CaselessLiteral("E")
    binop = oneOf("= != < > >= <= == eq ne lt le gt ge %s" % (QueryTokens.CONTAINS), caseless=True).setParseAction(upcaseTokens)
    arithSign = Word("+-",exact=1)
    realNum = Combine( Optional(arithSign) + ( Word( nums ) + "." + Optional( Word(nums) )  |
                ( "." + Word(nums) ) ) + 
            Optional( E + Optional(arithSign) + Word(nums) ) )
    intNum = Combine( Optional(arithSign) + Word( nums ) + 
            Optional( E + Optional("+") + Word(nums) ) )

    ident          = Word( alphas, alphanums + "_$" ).setName("identifier")
    columnName     = delimitedList( ident, ".", combine=True )
    columnName.setParseAction(label(QueryTokens.COLUMN_NAME))
    aliasName     = delimitedList( ident, ".", combine=True )
    stringLiteral = Forward()
    stringLiteral << quotedString
    stringLiteral.setParseAction(label(QueryTokens.STRING_LITERAL))
    intLiteral = Forward()
    intLiteral << intNum
    intLiteral.setParseAction(label(QueryTokens.INTEGER_LITERAL))
    floatLiteral = Forward()
    floatLiteral << realNum
    floatLiteral.setParseAction(label(QueryTokens.FLOAT_LITERAL))
    columnExpression = Forward()
    columnFunction = Word(alphas, alphanums) + "(" + Optional(delimitedList(Group( floatLiteral ) | Group ( stringLiteral ) | Group( intLiteral ) | columnExpression)) + ")" 
    columnFunction.setParseAction(label(QueryTokens.FUNCTION_OR_AGGREGATE))
    columnExpression << Group ( (columnFunction | columnName) + Optional( asToken + aliasName ) )
    columnExpressionList = Group( delimitedList( columnExpression ) )
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction(upcaseTokens)
    tableNameList  = Group( delimitedList( tableName ) )
    timeExpression = Word( nums ) + oneOf("seconds minutes hours days", caseless=True).setParseAction(downcaseTokens)
   
    stdoutToken = Keyword(QueryTokens.STDOUT, caseless=True).setParseAction(upcaseTokens)
    tableToken = Keyword(QueryTokens.TABLE, caseless=True).setParseAction(upcaseTokens)
    streamToken = Keyword(QueryTokens.STREAM, caseless=True).setParseAction(upcaseTokens)
    intoLocation = stdoutToken | ( tableToken + ident ) | ( streamToken + ident ) 

    whereExpression = Forward()
    and_ = Keyword(QueryTokens.AND, caseless=True).setParseAction(upcaseTokens)
    or_ = Keyword(QueryTokens.OR, caseless=True).setParseAction(upcaseTokens)
    in_ = Keyword(QueryTokens.IN, caseless=True).setParseAction(upcaseTokens)

    columnRval = realNum | intNum | nullToken | columnExpression | quotedString.setParseAction(removeQuotes)
    whereCondition = Group(
            ( columnExpression + binop + columnRval ).setParseAction(label(QueryTokens.WHERE_CONDITION)) |
            ( columnExpression + in_ + "(" + delimitedList( columnRval ) + ")" ).setParseAction(label(QueryTokens.WHERE_CONDITION)) |
            ( columnExpression + in_ + "(" + selectStmt + ")" ).setParseAction(label(QueryTokens.WHERE_CONDITION)) |
            ( "(" + whereExpression + ")" )
            )
    whereExpression << whereCondition + ZeroOrMore( ( and_ | or_ ) + whereExpression ) 

    # define the grammar
    selectStmt      << (  
            Group ( selectToken + columnExpressionList ).setResultsName( "select" ) + 
            fromToken + 
            tableNameList.setResultsName( "sources" ) + 
            Optional(intoToken + intoLocation, "").setResultsName("into") + 
            Optional( Group( CaselessLiteral(QueryTokens.WHERE) + whereExpression ), "" ).setResultsName("where") +
            Optional ( groupByToken + columnExpressionList, "").setResultsName("groupby") +
            Optional ( windowToken + timeExpression, "").setResultsName("window")
            )

    parser = selectStmt

    # define Oracle comment format, and ignore them
    oracleSqlComment = "--" + restOfLine
    parser.ignore( oracleSqlComment )
    
    return parser

def test( str ):
    print str,"->"
    parser = gen_parser()
    try:
        tokens = parser.parseString( str )
        print "tokens = ",        tokens
        print "tokens.fields =", tokens.fields
        print "tokens.sources =",  tokens.sources
        print "tokens.where =", tokens.where
    except ParseException, err:
        print " "*err.loc + "^\n" + err.msg
        print err
    print

def label(l):
    """
        Returns a parseaction which prepends the tokens with the label l
    """
    def action(string, loc, tokens):
        newlist = [l]
        newlist.extend(tokens)
        return newlist
    return action

def replace(l):
    """
        Returns a parseaction which replaces the tokens with the token l
    """
    def action(string, loc, tokens):
        return [l]
    return action

def runtests():
    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select A,B,C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select &&& frox Sys.dual" )
    test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE')" )
    test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)" )
    test( "Select A from Sys.dual where (a in ('RED','GREEN','BLUE') and b in (10,20,30)) OR (b in (10,20,30))" )
    test( "Select A,b from table1,table2 where table1.id eq table2.id -- test out comparison operators" )

if __name__ == '__main__':
    runtests()

"""
Test output:
>pythonw -u simpleSQL.py
SELECT * from XYZZY, ABC ->
tokens =  ['select', '*', 'from', ['XYZZY', 'ABC']]
tokens.fields = *
tokens.sources = ['XYZZY', 'ABC']

select * from SYS.XYZZY ->
tokens =  ['select', '*', 'from', ['SYS.XYZZY']]
tokens.fields = *
tokens.sources = ['SYS.XYZZY']

Select A from Sys.dual ->
tokens =  ['select', ['A'], 'from', ['SYS.DUAL']]
tokens.fields = ['A']
tokens.sources = ['SYS.DUAL']

Select A,B,C from Sys.dual ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL']]
tokens.fields = ['A', 'B', 'C']
tokens.sources = ['SYS.DUAL']

Select A, B, C from Sys.dual ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL']]
tokens.fields = ['A', 'B', 'C']
tokens.sources = ['SYS.DUAL']

Select A, B, C from Sys.dual, Table2    ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL', 'TABLE2']]
tokens.fields = ['A', 'B', 'C']
tokens.sources = ['SYS.DUAL', 'TABLE2']

Xelect A, B, C from Sys.dual ->
^
Expected 'select'
Expected 'select' (0), (1,1)

Select A, B, C frox Sys.dual ->
               ^
Expected 'from'
Expected 'from' (15), (1,16)

Select ->
      ^
Expected '*'
Expected '*' (6), (1,7)

Select &&& frox Sys.dual ->
       ^
Expected '*'
Expected '*' (7), (1,8)

>Exit code: 0
"""

########NEW FILE########
__FILENAME__ = twitter_fields
from datetime import datetime
from field_descriptor import FieldDescriptor
from field_descriptor import FieldType
from field_descriptor import ReturnType
from tuple_descriptor import TupleDescriptor

def twitter_user_data_extractor(field):
    def factory():
        def extract(data):
            return getattr(data[TwitterFields.USER], field)
        return extract
    return factory

class TwitterFields:
    TEXT = "text"
    USER = "user"
    SSQL_USER_ID = "user_id"
    TWITTER_USER_ID = "id"
    SCREEN_NAME = "screen_name"
    LOCATION = "location"
    LANG = "lang"
    CREATED_AT = "created_at"
    PROFILE_IMAGE_URL = "profile_image_url"
    
# built here so we can refer to this field in the GroupBy operator. 
TwitterFields.created_field = FieldDescriptor(TwitterFields.CREATED_AT, [TwitterFields.CREATED_AT], FieldType.FIELD, ReturnType.DATETIME)

def twitter_tuple_descriptor():
    fields = [
        FieldDescriptor(TwitterFields.TEXT, [TwitterFields.TEXT], FieldType.FIELD, ReturnType.STRING),
        FieldDescriptor(TwitterFields.LOCATION, [], FieldType.FUNCTION, ReturnType.STRING, None, twitter_user_data_extractor(TwitterFields.LOCATION)),
        FieldDescriptor(TwitterFields.LANG, [], FieldType.FUNCTION, ReturnType.STRING, None, twitter_user_data_extractor(TwitterFields.LANG)),
        FieldDescriptor(TwitterFields.PROFILE_IMAGE_URL, [], FieldType.FUNCTION, ReturnType.STRING, None, twitter_user_data_extractor(TwitterFields.PROFILE_IMAGE_URL)),
        FieldDescriptor(TwitterFields.SSQL_USER_ID, [], FieldType.FUNCTION, ReturnType.INTEGER, None, twitter_user_data_extractor(TwitterFields.TWITTER_USER_ID)),
        FieldDescriptor(TwitterFields.SCREEN_NAME, [], FieldType.FUNCTION, ReturnType.STRING, None, twitter_user_data_extractor(TwitterFields.SCREEN_NAME)),
        TwitterFields.created_field,
    ]
    return TupleDescriptor(fields)


########NEW FILE########
