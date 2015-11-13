__FILENAME__ = app
import os, sys

BASEDIR = os.path.join(os.path.dirname(__file__), '../..')
ROOTDIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(ROOTDIR)
sys.path.append(BASEDIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'wtfimb.settings'



import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = mobile_app
import os, sys

BASEDIR = os.path.join(os.path.dirname(__file__), '../..')
ROOTDIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(ROOTDIR)
sys.path.append(BASEDIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'wtfimb.mobile_settings'



import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('api.views',
        (r'^routes/$', 'all_routes'),
        (r'^autocomplete/stages$', 'autocomplete_stages'),
        (r'^route/(?P<route_name>\w+)/$', 'single_route'),
        )

########NEW FILE########
__FILENAME__ = views
# Create your views here.

from stages.models import *
from routes.models import *
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.utils import simplejson

def all_routes(request, city):
    stages = Stage.objects.filter(city=city)
    data = dict([ (s.id, 
        {'display_name': s.display_name,
         'latitude': s.location.y,
         'longitude': s.locaton.x}
        ) for s in stages])
    return HttpResponse(simplejson.dumps(data))

def single_route(request, city, route_name):
    r = Route.objects.filter(city=city).get(display_name__iexact=route_name)
    return HttpResponse(simplejson.dumps(
            {
            'name': r.display_name,
            'stages': [ { 'name': s.display_name,
                          'latitude': s.location.y,
                          'longitude': s.location.x                          
                        }
                        for s in r.stages.all()]
                        }))

def autocomplete_stages(request, city):
    stages = Stage.objects.filter(city=city)
    data = dict( [ (s.display_name, s.id) for s in stages] )
    return HttpResponse(simplejson.dumps(data))

########NEW FILE########
__FILENAME__ = parser
from BeautifulSoup import BeautifulSoup, NavigableString
import urllib2
import simplejson as json
import sys
def strip_tags(html, invalid_tags):
  soup = BeautifulSoup(html)
  for tag in soup.findAll(True):
    if tag.name in invalid_tags:
      s = ""
      for c in tag.contents:
        if not isinstance(c, NavigableString):
          c = strip_tags(unicode(c), invalid_tags)
        s += unicode(c)
        tag.replaceWith(s)
  return soup

def getHtml(url):
    user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
    headers = { 'User-Agent' : user_agent }
    request = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(request)
    html = response.read()
    return html

def parseHtml(html):
    soup = strip_tags(html, ['span'])
    trs = soup.findAll('tr')[5:-1]
    routes = []
    for tr in trs:
        tds = [x.contents[0] for x in tr.findAll('td')[:12]]
        route = {
            "from_stage" : tds[3].strip(),
            "to_stage" : tds[4].strip(),
            "via" : [x.strip() for x in tds[5].split(',')],
            "frequency_peak" : tds[10],
            "frequency_slack" : tds[11]
        }
        if type(tds[1]).__name__ == 'Tag':
            part1 = tds[1].contents[0].strip()
        else:
            part1 = tds[1].strip()
        if type(tds[2]).__name__ == 'Tag':
            part2 = tds[2].contents[0].strip()
        else:
            part2 = tds[2].strip()
        route["route_id"] = part1 + part2
        routes.append(route)
    return routes

if __name__ == "__main__":
    #url = 'http://apsrtc.gov.in/About%20Us/Route-Network/TIME%20TABLE-HCZ.htm'
    #html = getHtml(url)
    html = open('TIME TABLE-HCZ_debugged.htm','r').read()
    routes = parseHtml(html)
    json.dump(routes, sys.stdout, indent=2)


########NEW FILE########
__FILENAME__ = unique_stops
import simplejson as json
import csv
import sys

parsed_routes = json.load(open('parsed_routes.json', 'r'))

def add_stop(unprocessed_stop):
    stop = unprocessed_stop.replace("\n","")
    stop = stop.replace("\r","")
    stop = stop.replace("&nbsp","")
    stop = stop.replace("  ", " ")
    unique_stops.add((unprocessed_stop, stop))

unique_stops = set()
for route in parsed_routes:
    add_stop(route["from_stage"])
    add_stop(route["to_stage"])
    [add_stop(x) for x in route["via"]]

stops = list(unique_stops)
stops.sort(key=lambda x: x[0].lower())

writer = csv.writer(sys.stdout)
writer.writerows(stops)

########NEW FILE########
__FILENAME__ = 001_get_stages
from BeautifulSoup import BeautifulSoup
import urllib2
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Get the Page from the server ( contains two select boxes populated with stage names )
mtc_stages_url = 'http://www.mtcbus.org/Places.asp'
request = urllib2.Request(mtc_stages_url, None, headers)
response = urllib2.urlopen(request)
the_page = response.read()

# Save the page
filename = 'stages.html'
f = open(filename, "w")
f.write(the_page)
f.close()

# Load the page
filename = 'stages.html'
f = open(filename, "r")
the_page = f.read()
f.close()

# Parse the HTML
soup = BeautifulSoup(the_page)
options = soup.select.findAll('option')[1:]

# Output the Stages list to json file
filename = 'stages.json'
f = open(filename, "w")
f.write(json.dumps([ option.contents[0] for option in options ], indent=4))
f.close()

# Output the Stages list to stdout as json
print json.dumps([ option.contents[0] for option in options ], indent=4)

########NEW FILE########
__FILENAME__ = 002_get_routes_index
from BeautifulSoup import BeautifulSoup
import urllib2
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Get the Page from the server ( contains one select box with route numbers )
mtc_routes_url = 'http://www.mtcbus.org/Routes.asp'
request = urllib2.Request(mtc_routes_url, None, headers)
response = urllib2.urlopen(request)
the_page = response.read()

# Save the page
filename = 'routes_index.html'
f = open(filename, "w")
f.write(the_page)
f.close()

# Load the page
filename = 'routes_index.html'
f = open(filename, "r")
the_page = f.read()
f.close()

# Parse the HTML
soup = BeautifulSoup(the_page)
options = soup.select.findAll('option')

# Output the Routes index list to json file
filename = 'routes_index.json'
f = open(filename, "w")
f.write(json.dumps([ option.contents[0] for option in options ], indent=4))
f.close()

# Output the Routes index list to stdout as json
print json.dumps([ option.contents[0] for option in options ], indent=4)

########NEW FILE########
__FILENAME__ = 003_scrape_routes_detail
from BeautifulSoup import BeautifulSoup
import urllib2
import urllib
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Load routes_index from file
routes_index = json.load(open('routes_index.json','r'))

# Scrape the stage information for every route in routes_index
routes_detail = {}
pf = open("partial_file", "w")
pf.write("{\n")
for route in routes_index:
   
   # GET the routedetails from the server
   params = urllib.urlencode({'cboRouteCode': route, 'submit':'Search'})
   url = "http://www.mtcbus.org/Routes.asp?%s" % params
   request = urllib2.Request( url, None, headers)
   response = urllib2.urlopen(request)
   html = response.read()
   
   # Cleanup bad HTML
   html = html.replace("'top'BGColor=''", "'top' BGColor=''")
   html = html.replace("JPG'Align", "JPG' Align")
   html = html.replace("OnClick=window.open(", "OnClick=\"window.open(")
   html = html.replace("')>View Route Map", "')\">View Route Map")

   '''
   # Save the page
   filename = 'temp.html'
   f = open(filename, "w")
   f.write(html)
   f.close()
   
   # Load the page
   filename = 'temp.html'
   f = open(filename, "r")
   html = f.read()
   f.close()
   '''
   
   # Parse the HTML   
   soup = BeautifulSoup(html)
   tds = soup.find('table', {'border':"1"}).findAll('td', {'align':'left'})[1:]
   text = []
   for td in tds:
      if len(td.contents) == 0:
         text.append(None)
      else:
         text.append(td.contents[0])
   # Store in the dictionary
   route_detail = {
        'service_type' : text[1], 
        'source' : text[2],
        'destination' : text[3],
        'stages' : text[4:]
   }
   routes_detail[route] = route_detail
   pf.write("\"%s\" :\n" % route)
   pf.write(json.dumps(route_detail, indent=4))
   pf.write(",\n") #FIXME: Don't include this for last element
   pf.flush()
pf.write("}")
pf.close()
# Output the Dictionary to json file
f = open('routes_detail.json','w')
f.write(json.dumps(routes_detail, indent=4, sort_keys=True))
f.close()

'''
# Output the Dictionary to stdout as json
print json.dumps(routes_detail, indent=4, sort_keys=True)
'''

########NEW FILE########
__FILENAME__ = 004_load_stages
import simplejson as json
import os
import sys

CITY = 'chennai' # For different city, change here

def setup_env():
   pathname = os.path.dirname(sys.argv[0])
   sys.path.append(os.path.abspath(pathname))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../')))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../../')))
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_env()

def main():
   sjs = json.load(open('stages.json', 'r'))
   from stages.models import Stage
   
   for s in Stage.objects.filter(city=CITY):
      s.city = CITY + '_old'
      s.save()

   # For every stage name in the list
   for sj in sjs:
      try:
         s = Stage.objects.get(city__contains=CITY, mtc_name = sj)
         s_old = Stage()
         s_old.display_name = s.display_name
         s_old.city = s.city
         s_old.mtc_name = s.mtc_name
         s_old.save()
      except Stage.DoesNotExist:
         s = Stage()
      s.display_name = sj.title()
      s.city = CITY
      s.mtc_name = sj
      # Save the stage
      s.save()

if __name__ == "__main__":
   setup_env()
   main()

########NEW FILE########
__FILENAME__ = 005_load_routes
import simplejson as json
import os
import sys
from django.template.defaultfilters import slugify
from mappings import *

CITY = 'chennai' # For different city, change here

MTC_TYPE_REVERSE_MAP = {
   'Ordinary': 'ORD',
   'Night Service': 'NGT',
   'LSS': 'LSS',
   'M-Route': 'MSVC',
   'Delux': 'DLX',
   'Air Condition': 'AC',
   'Express': 'EXP'
}

def setup_env():
   pathname = os.path.dirname(sys.argv[0])
   sys.path.append(os.path.abspath(pathname))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../')))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../../')))
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_env()

def resolve_route_name(name):
    display_name = name
    dlx_flag = False
    ac_flag = False
    for p in PREFIX_LIST:
        if display_name.startswith(p):
            if not p in PREFIX_KEEPERS:
               display_name = display_name.lstrip(p)
            if p == 'W':
               ac_flag = True
               display_name = display_name.rstrip('V')
            if p == 'S':
               dlx_flag = True
            break
    slug = slugify(display_name)
    for s in SUFFIX_LIST:
        if display_name.endswith(s):
            if not s in SUFFIX_KEEPERS: display_name = display_name.rstrip(s)
            slug = slugify(display_name)
            if s in EXT_ALIASES: display_name = display_name.replace(s," Ext")
            if s in CUT_ALIASES: display_name = display_name.replace(s," Cut")
            break
    if dlx_flag:
        display_name = display_name + " Dlx"
        slug = "s" + slug
    if ac_flag:
        display_name = display_name + " AC"
        slug = "w" + slug
    return (display_name, slug)

def main():
   rds = json.load(open('routes_detail.json', 'r'))
   from routes.models import Route, RouteStage, ROUTE_TYPE_MAPPING
   from stages.models import Stage
   
   for r in Route.objects.filter(city=CITY):
      r.city = CITY + '_old'
      r.save()

   # For every route number in the dictionary
   for mtc_name in rds:
      display_name, slug = resolve_route_name(mtc_name)
      rd = rds[mtc_name]
      if rd["source"] is None or rd["destination"] is None or len(rd["stages"]) == 0:
         #print "Route %s skipped (Reason: Incomplete)" % mtc_name
         continue # Skipping Incomplete routes
      service_type = rd["service_type"]
      s_type = MTC_TYPE_REVERSE_MAP[service_type]
      
      # if the route is present already, edit it
      if not Route.objects.filter(city=CITY).filter(slug=slug):
         r = Route()
      else:
         r = Route.objects.filter(city=CITY).get(slug=slug)
         
      # Add/Reset details of the route
      r.display_name = display_name
      r.city = CITY
      r.mtc_name = mtc_name
      if r.types is None or r.types == "":
         r.types = s_type
      elif s_type not in r.types.split(','):
         r.types = r.types + "," + s_type
      r.fare = -1 #TODO: Remove fare data
      r.time = -1 #TODO: Remove time data
      r.slug = slugify(slug)

      # Add new/existing stage object as route's start stage
      sstage = rd["source"]
      try:
         ssobj = Stage.objects.get(city=CITY, mtc_name = sstage)
      except Stage.DoesNotExist:
         ssobj = Stage()
         ssobj.display_name = sstage.title()
         ssobj.city = CITY
         ssobj.mtc_name = sstage
         ssobj.save()
      r.start = ssobj
      
      # Add new/existing stage object as route's end stage
      estage = rd["destination"]
      try:
         esobj = Stage.objects.get(city=CITY, mtc_name = estage)
      except Stage.DoesNotExist:
         esobj = Stage()
         esobj.display_name = estage.title()
         esobj.city = CITY
         esobj.mtc_name = estage
         esobj.save()
      r.end = esobj
      
      # Save the route
      r.save()
      
      # Add RouteStage object for every stage in route
      sequence = 100
      for stage in rd["stages"]:
         
         # Get or create stage object
         try:
            sobj = Stage.objects.get(city=CITY, mtc_name = stage)
         except Stage.DoesNotExist:
            sobj = Stage()
            sobj.display_name = stage.title()
            sobj.city = CITY
            sobj.mtc_name = stage
            sobj.save()
         
         # Get or create RouteStage object
         try:
            rs = RouteStage.objects.filter(route=r).get(stage=sobj)
         except RouteStage.DoesNotExist:
            rs = RouteStage()
         rs.route = r
         rs.stage = sobj
         rs.sequence = sequence
         rs.save()
         
         # Increment sequence of stage
         sequence += 100

if __name__ == "__main__":
   setup_env()
   main()

########NEW FILE########
__FILENAME__ = mappings
#Prefixes and their meanings.

PREFIX_LIST = ['M', # M-Route
               'S', # Deluxe
               'X', # Express
               'L', # LSS
               'W'] # AC Volvo

SUFFIX_LIST = ['EXT','EX','ET','XT','EXN','X', # Extension
               'CUT','CU','CT','CUNS', # Cut Service
               'NS','NH', # Night Service
               'FS']

#Prefixes and suffixes that should not be removed from display name
SUFFIX_KEEPERS = ['EXT','EX','EX','ET','XT','EXN','X',
                  'CUT','CU','CT']
PREFIX_KEEPERS = ['M']

#Aliases To Ext And Cut That Should Be Replaced By ' Ext' And ' Cut'
EXT_ALIASES = ['EXT','EX','EX','ET','XT','EXN','X']
CUT_ALIASES = ['CUT','CU','CT']

########NEW FILE########
__FILENAME__ = 001_get_stages
from BeautifulSoup import BeautifulSoup
import urllib2
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Get the Page from the server ( contains two select boxes populated with stage names )
dtc_stages_url = 'http://delhigovt.nic.in/dtcbusroute/dtc/Find_Route/getroute.asp'
request = urllib2.Request(dtc_stages_url, None, headers)
response = urllib2.urlopen(request)
the_page = response.read()

# Clean the bad HTML code
form_start_pos = the_page.rfind('<form')
form_end_pos = the_page.rfind('</form>')
the_page = "<html>\n\t<body>\n\t\t" + the_page[form_start_pos:form_end_pos + 7] + "\n\t</body>\n</html>"

# Save the page
filename = 'stages.html'
f = open(filename, "w")
f.write(the_page)
f.close()

# Load the page
filename = 'stages.html'
f = open(filename, "r")
the_page = f.read()
f.close()

# Parse the HTML
soup = BeautifulSoup(the_page)
options = soup.select.findAll('option')[1:]

# Output the Stages list to json file
filename = 'stages.json'
f = open(filename, "w")
f.write(json.dumps([ option.contents[0] for option in options ], indent=4))
f.close()

# Output the Stages list to stdout as json
print json.dumps([ option.contents[0] for option in options ], indent=4)

########NEW FILE########
__FILENAME__ = 002_get_routes_index
from BeautifulSoup import BeautifulSoup
import urllib2
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Get the Page from the server ( contains one select box with route numbers )
dtc_viewmap_url = 'http://delhigovt.nic.in/dtcbusroute/dtc/Find_Route/viewmap.asp'
request = urllib2.Request(dtc_viewmap_url, None, headers)
response = urllib2.urlopen(request)
the_page = response.read()

# Clean the bad HTML code
form_start_pos = the_page.rfind('<form')
form_end_pos = the_page.rfind('</form>')
the_page = "<html>\n\t<body>\n\t\t" + the_page[form_start_pos:form_end_pos + 7] + "\n\t</body>\n</html>"

# Save the page
filename = 'routes_index.html'
f = open(filename, "w")
f.write(the_page)
f.close()

# Load the page
filename = 'routes_index.html'
f = open(filename, "r")
the_page = f.read()
f.close()

# Parse the HTML
soup = BeautifulSoup(the_page)
options = soup.select.findAll('option')[1:]

# Output the Routes index list to json file
filename = 'routes_index.json'
f = open(filename, "w")
f.write(json.dumps([ option.contents[0] for option in options ], indent=4))
f.close()

# Output the Routes index list to stdout as json
print json.dumps([ option.contents[0] for option in options ], indent=4)

########NEW FILE########
__FILENAME__ = 003_scrape_routes_detail
from BeautifulSoup import BeautifulSoup
import urllib2
import urllib
import simplejson as json

user_agent = 'Mozilla/5 (Ubuntu 10.04) Gecko'
headers = { 'User-Agent' : user_agent }

# Load routes_index from file
routes_index = json.load(open('routes_index.json','r'))

# Scrape the stage information for every route in routes_index
routes_detail = {}
for route in routes_index:
   
   # Post the 'BUSNO' to the server and get HTML output
   url = "http://delhigovt.nic.in/dtcbusroute/dtc/find_route/busnodetails.asp"
   data = { 'BUSNO': route }
   data_encoded = urllib.urlencode(data)
   request = urllib2.urlopen( url, data_encoded )
   html = request.read()
 
   # Clean the bad HTML code
   table_start_pos = html.rfind('<table')
   table_end_pos = html.rfind('</table>')
   html = "<html>\n\t<body>\n\t\t" + html[table_start_pos:table_end_pos + 8] + "\n\t</body>\n</html>"

   # Parse the HTML   
   soup = BeautifulSoup(html)
   tds = soup.table.findAll('td')
   
   # Clean the td
   tds = tds[:-1] # remove last blank td element
   tds = [str(td.contents[0]).strip() for td in tds] # Strip leading white space

   # Store in the dictionary
   routes_detail[route] = tds
   
# Output the Dictionary to json file
f = open('routes_detail.json','w')
f.write(json.dumps(routes_detail, indent=4))
f.close()

# Output the Dictionary to stdout as json
json.dumps(routes_detail, indent=4)

########NEW FILE########
__FILENAME__ = 004_load_stages
import simplejson as json
import os
import sys

def setup_env():
   pathname = os.path.dirname(sys.argv[0])
   sys.path.append(os.path.abspath(pathname))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../')))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../../')))
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_env()

def main():
   sjs = json.load(open('stages.json', 'r'))
   from stages.models import Stage
   
   # For every stage name in the list
   for sj in sjs:
      # if the stage is present already, do nothing
      if Stage.objects.filter(city='delhi').filter(mtc_name=sj):
         continue
      new_stage = Stage()
      new_stage.display_name = sj
      new_stage.city = 'delhi'
      new_stage.mtc_name = sj
      
      # Save the stage
      new_stage.save()
   
if __name__ == "__main__":
   setup_env()
   main()

########NEW FILE########
__FILENAME__ = 005_load_routes
import simplejson as json
import os
import sys
from django.template.defaultfilters import slugify
def setup_env():
   pathname = os.path.dirname(sys.argv[0])
   sys.path.append(os.path.abspath(pathname))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../')))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../../')))
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_env()

def main():
   rjs = json.load(open('routes_detail.json', 'r'))
   from routes.models import Route, RouteStage
   from stages.models import Stage
   
   # For every route number in the dictionary
   for rj in rjs:
      
      # if the route is present already, edit it
      if not Route.objects.filter(city='delhi').filter(mtc_name=rj):
         new_route = Route()
      else:
         new_route = Route.objects.filter(city='delhi').get(mtc_name=rj)
         
      # Add/Reset details of the route
      new_route.display_name = rj
      new_route.city = 'delhi'
      new_route.mtc_name = rj
      new_route.types = "O" #FIXME: Classify routes under appropriate types
      new_route.fare = -1 #TODO: Scrape fare data
      new_route.time = -1 #TODO: Scrape time data
      new_route.slug = slugify(rj)

      # Add new/existing stage object as route's start stage
      try:
         sstage = rjs[rj][0]
         ssobj = Stage.objects.filter(city='delhi').get(mtc_name=sstage)
      except Stage.DoesNotExist:
         ssobj = Stage()
         ssobj.mtc_name = sstage
         ssobj.display_name = sstage
         ssobj.city = 'delhi'
         ssobj.save()
      new_route.start = ssobj
      
      # Add new/existing stage object as route's end stage
      try:
         estage = rjs[rj][-1]
         esobj = Stage.objects.filter(city='delhi').get(mtc_name=estage)
      except Stage.DoesNotExist:
         esobj = Stage()
         esobj.mtc_name = estage
         esobj.display_name = estage
         esobj.city = 'delhi'
         esobj.save()
      new_route.end = esobj

      # Save the route
      new_route.save()
      
      # Add RouteStage object for every stage in route
      sequence = 100
      for stage in rjs[rj]:
         
         # Get or create stage object
         try:
            sobj = Stage.objects.filter(city='delhi').get(mtc_name=stage)
         except Stage.DoesNotExist:
            sobj = Stage()
            sobj.mtc_name = stage
            sobj.display_name = stage
            sobj.city = 'delhi'
            sobj.save()
         
         # Get or create RouteStage object
         try:
            rs = RouteStage.objects.filter(route=new_route).get(stage__display_name=stage)
         except RouteStage.DoesNotExist:
            rs = RouteStage()
         rs = RouteStage()
         rs.route = new_route
         rs.stage = sobj
         rs.sequence = sequence
         rs.save()
         
         # Increment sequence of stage
         sequence += 100

if __name__ == "__main__":
   setup_env()
   main()

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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

from django.contrib import admin
from django_authopenid.models import UserAssociation


class UserAssociationAdmin(admin.ModelAdmin):
    """User association admin class"""
admin.site.register(UserAssociation, UserAssociationAdmin)
########NEW FILE########
__FILENAME__ = context_processors
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#


def authopenid(request):
    """
    Returns context variables required by apps that use django-authopenid.
    """
    if hasattr(request, 'openid'):
        openid = request.openid
    else:
        openid = None
        
    if hasattr(request, 'openids'):
        openids = request.openids
    else:
        openids = []
        
    if hasattr(request, 'associated_openids'):
        associated_openids = request.associated_openids
    else:
        associated_openids = []
        
    return {
        "openid": openid,
        "openids": openids,
        "associated_openids": associated_openids,
        "signin_with_openid": (openid is not None),
        "has_openids": (len(associated_openids) > 0)
    }
########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#
import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.conf import settings
# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri
    
from django_authopenid.models import UserAssociation

    
class OpenidSigninForm(forms.Form):
    """ signin form """
    openid_url = forms.CharField(max_length=255, 
            widget=forms.widgets.TextInput(attrs={'class': 'required openid'}))
            
    def clean_openid_url(self):
        """ test if openid is accepted """
        if 'openid_url' in self.cleaned_data:
            openid_url = self.cleaned_data['openid_url']
            if xri.identifierScheme(openid_url) == 'XRI' and getattr(
                settings, 'OPENID_DISALLOW_INAMES', False
                ):
                raise forms.ValidationError(_('i-names are not supported'))
            return self.cleaned_data['openid_url']

attrs_dict = { 'class': 'required login' }
username_re = re.compile(r'^\w+$')

class OpenidRegisterForm(forms.Form):
    """ openid signin form """
    username = forms.CharField(max_length=30, 
            widget=forms.widgets.TextInput(attrs=attrs_dict))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, 
        maxlength=200)), label=u'Email address')
        
    def __init__(self, *args, **kwargs):
        super(OpenidRegisterForm, self).__init__(*args, **kwargs)
        self.user = None
    
    def clean_username(self):
        """ test if username is valid and exist in database """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_("Usernames can only contain \
                    letters, numbers and underscores"))
            try:
                user = User.objects.get(
                        username__exact = self.cleaned_data['username']
                )
            except User.DoesNotExist:
                return self.cleaned_data['username']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that username. Please try \
                    another.')
            self.user = user
            raise forms.ValidationError(_("This username is already \
                taken. Please choose another."))
            
    def clean_email(self):
        """For security reason one unique email in database"""
        if 'email' in self.cleaned_data:
            try:
                user = User.objects.get(email = self.cleaned_data['email'])
            except User.DoesNotExist:
                return self.cleaned_data['email']
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(u'There is already more than one \
                    account registered with that e-mail address. Please try \
                    another.')
            raise forms.ValidationError(_("This email is already \
                registered in our database. Please choose another."))
                
                
class AssociateOpenID(forms.Form):
    """ new openid association form """
    openid_url = forms.CharField(max_length=255, 
            widget=forms.widgets.TextInput(attrs={'class': 'required openid'}))

    def __init__(self, user, *args, **kwargs):
        super(AssociateOpenID, self).__init__(*args, **kwargs)
        self.user = user
            
    def clean_openid_url(self):
        """ test if openid is accepted """
        if 'openid_url' in self.cleaned_data:
            openid_url = self.cleaned_data['openid_url']
            if xri.identifierScheme(openid_url) == 'XRI' and getattr(
                settings, 'OPENID_DISALLOW_INAMES', False
                ):
                raise forms.ValidationError(_('i-names are not supported'))
                
            try:
                rel = UserAssociation.objects.get(openid_url__exact=openid_url)
            except UserAssociation.DoesNotExist:
                return self.cleaned_data['openid_url']
            
            if rel.user != self.user:
                raise forms.ValidationError(_("This openid is already \
                    registered in our database by another account. Please choose another."))
                    
            raise forms.ValidationError(_("You already associated this openid to your account."))
            
class OpenidDissociateForm(OpenidSigninForm):
    """ form used to dissociate an openid. """
    openid_url = forms.CharField(max_length=255, widget=forms.widgets.HiddenInput())
########NEW FILE########
__FILENAME__ = cleanupassociations
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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

from django.core.management.base import NoArgsCommand

from django_authopenid import DjangoOpenIDStore

class Command(NoArgsCommand):
    help = "Delete expired openid associations"
    
    def handle_noargs(self, **options):
        openid = DjangoOpenIDStore()
        openid.cleanupAssociations()
########NEW FILE########
__FILENAME__ = cleanupnonces
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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

from django.core.management.base import NoArgsCommand

from django_authopenid import DjangoOpenIDStore

class Command(NoArgsCommand):
    help = "Delete expired openid nonces"
    
    def handle_noargs(self, **options):
        openid = DjangoOpenIDStore()
        openid.cleanupNonce()
########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#

from django_authopenid.utils.mimeparse import best_match
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from django_authopenid.models import UserAssociation
from django_authopenid.views import xrdf

__all__ = ["OpenIDMiddleware"]

class OpenIDMiddleware(object):
    """
    Populate request.openid. This comes either from cookie or from
    session, depending on the presence of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openid = request.session.get('openid', None)
        request.openids = request.session.get('openids', [])
        
        rels = UserAssociation.objects.filter(user__id=request.user.id)
        request.associated_openids = [rel.openid_url for rel in rels]
    
    def process_response(self, request, response):
        if response.status_code != 200 or len(response.content) < 200:
            return response
        path = request.get_full_path()
        if path == "/" and request.META.has_key('HTTP_ACCEPT') and \
                best_match(['text/html', 'application/xrds+xml'], 
                    request.META['HTTP_ACCEPT']) == 'application/xrds+xml':
            response = xrdf(request)
        return response
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#

import os
import random
import sys
import time
try:
    from hashlib import md5 as _md5
except ImportError:
    import md5
    _md5 = md5.new


from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_authopenid.signals import oid_associate

__all__ = ['Nonce', 'Association', 'UserAssociation']

class Nonce(models.Model):
    """ openid nonce """
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=40)
    
    def __unicode__(self):
        return u"Nonce: %s" % self.id

class Association(models.Model):
    """ association openid url and lifetime """
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)
    
    def __unicode__(self):
        return u"Association: %s, %s" % (self.server_url, self.handle)

class UserAssociation(models.Model):
    """ 
    model to manage association between openid and user 
    """
    openid_url = models.CharField(primary_key=True, blank=False,
                            max_length=255, verbose_name=_('OpenID URL'))
    user = models.ForeignKey(User, verbose_name=_('User'))
    
    def __unicode__(self):
        return "Openid %s with user %s" % (self.openid_url, self.user)
        
    def save(self, send_email=True):
        super(UserAssociation, self).save()
        if send_email:
            from django.core.mail import send_mail
            current_site = Site.objects.get_current()
            subject = render_to_string('authopenid/associate_email_subject.txt',
                                       { 'site': current_site,
                                         'user': self.user})
            message = render_to_string('authopenid/associate_email.txt',
                                       { 'site': current_site,
                                         'user': self.user,
                                         'openid': self.openid_url
                                        })

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, 
                    [self.user.email], fail_silently=True)
        oid_associate.send(sender=self, user=self.user, openid=self.openid_url)
        

    class Meta:
        verbose_name = _('user association')
        verbose_name_plural = _('user associations')

########NEW FILE########
__FILENAME__ = openid_store
# -*- coding: utf-8 -*-
# Copyright 2007, 2008, 2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#

import base64
import operator
import time
import urllib
try:
    from hashlib import md5 as _md5
except ImportError:
    import md5
    _md5 = md5.new
   
from django.db.models.query import Q
from django.conf import settings
from openid.association import Association as OIDAssociation
import openid.store.interface
import openid.store

from django_authopenid.models import Association, Nonce
from django_authopenid.utils import OpenID

class DjangoOpenIDStore(openid.store.interface.OpenIDStore):
    def __init__(self):
        self.max_nonce_age = 6 * 60 * 60 # Six hours
    
    def storeAssociation(self, server_url, association):
        assoc = Association(
            server_url = server_url,
            handle = association.handle,
            secret = base64.encodestring(association.secret),
            issued = association.issued,
            lifetime = association.lifetime,
            assoc_type = association.assoc_type
        )
        assoc.save()
    
    def getAssociation(self, server_url, handle=None):
        assocs = []
        if handle is not None:
            assocs = Association.objects.filter(
                server_url = server_url, handle = handle
            )
        else:
            assocs = Association.objects.filter(
                server_url = server_url
            )
        if not assocs:
            return None
        associations = []
        expired = []
        for assoc in assocs:
            association = OIDAssociation(
                assoc.handle, base64.decodestring(assoc.secret), assoc.issued,
                assoc.lifetime, assoc.assoc_type
            )
            if association.getExpiresIn() == 0:
                expired.append(assoc)
            else:
                associations.append((association.issued, association))
                
        for assoc in expired:
            assoc.delete()
        if not associations:
            return None
        associations.sort()
        return associations[-1][1]
    
    def removeAssociation(self, server_url, handle):
        assocs = list(Association.objects.filter(
            server_url = server_url, handle = handle
        ))
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > openid.store.nonce.SKEW:
            return False
        
        query = [
                Q(server_url__exact=server_url),
                Q(timestamp__exact=timestamp),
                Q(salt__exact=salt),
        ]
        try:
            ononce = Nonce.objects.get(reduce(operator.and_, query))
        except Nonce.DoesNotExist:
            ononce = Nonce(
                    server_url=server_url,
                    timestamp=timestamp,
                    salt=salt
            )
            ononce.save()
            return True

        return False
   
    def cleanupNonces(self, _now=None):
        if _now is None:
            _now = int(time.time())
        expired = Nonce.objects.filter(timestamp__lt=(_now - openid.store.nonce.SKEW))
        count = expired.count()
        if count:
            expired.delete()
        return count

    def cleanupAssociations(self):
        now = int(time.time())
        expired = Association.objects.extra(
            where=['issued + lifetime < %d' % now])
        count = expired.count()
        if count:
            expired.delete()
        return count

    def getAuthKey(self):
        # Use first AUTH_KEY_LEN characters of md5 hash of SECRET_KEY
        return _md5(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]
    
    def isDumb(self):
        return False
########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
from django.dispatch import Signal


# a new user has been registered
oid_register = Signal(providing_args=['openid'])

# a new openid has been associated
oid_associate = Signal(providing_args=["user", "openid"])
########NEW FILE########
__FILENAME__ = test_store
#!/usr/bin/env python
# django-openid-auth -  OpenID integration for django.contrib.auth
#
# Copyright (C) 2009 Canonical Ltd.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import time
import unittest

from django.conf import settings
from django.test import TestCase
from openid.association import Association as OIDAssociation
from openid.store.nonce import SKEW

from django_authopenid.models import Association, Nonce
from django_authopenid.openid_store import DjangoOpenIDStore


class OpenIDStoreTests(TestCase):

    def setUp(self):
        super(OpenIDStoreTests, self).setUp()
        self.store = DjangoOpenIDStore()

    def test_storeAssociation(self):
        assoc = OIDAssociation('handle', 'secret', 42, 600, 'HMAC-SHA1')
        self.store.storeAssociation('server-url', assoc)

        dbassoc = Association.objects.get(
            server_url='server-url', handle='handle')
        self.assertEquals(dbassoc.server_url, 'server-url')
        self.assertEquals(dbassoc.handle, 'handle')
        self.assertEquals(dbassoc.secret, 'secret'.encode('base-64'))
        self.assertEquals(dbassoc.issued, 42)
        self.assertEquals(dbassoc.lifetime, 600)
        self.assertEquals(dbassoc.assoc_type, 'HMAC-SHA1')

    def test_getAssociation(self):
        timestamp = int(time.time())
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle', 'secret', timestamp, 600,
                                         'HMAC-SHA1'))
        assoc = self.store.getAssociation('server-url', 'handle')
        self.assertTrue(isinstance(assoc, OIDAssociation))

        self.assertEquals(assoc.handle, 'handle')
        self.assertEquals(assoc.secret, 'secret')
        self.assertEquals(assoc.issued, timestamp)
        self.assertEquals(assoc.lifetime, 600)
        self.assertEquals(assoc.assoc_type, 'HMAC-SHA1')

    def test_getAssociation_unknown(self):
        assoc = self.store.getAssociation('server-url', 'unknown')
        self.assertEquals(assoc, None)

    def test_getAssociation_expired(self):
        lifetime = 600
        timestamp = int(time.time()) - 2 * lifetime
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle', 'secret', timestamp,
                                         lifetime, 'HMAC-SHA1'))

        # The association is not returned, and is removed from the database.
        assoc = self.store.getAssociation('server-url', 'handle')
        self.assertEquals(assoc, None)
        self.assertRaises(Association.DoesNotExist, Association.objects.get,
                          server_url='server-url', handle='handle')

    def test_getAssociation_no_handle(self):
        timestamp = int(time.time())

        self.store.storeAssociation(
            'server-url', OIDAssociation('handle1', 'secret', timestamp + 1,
                                         600, 'HMAC-SHA1'))
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle2', 'secret', timestamp,
                                         600, 'HMAC-SHA1'))

        # The newest handle is returned.
        assoc = self.store.getAssociation('server-url', None)
        self.assertNotEquals(assoc, None)
        self.assertEquals(assoc.handle, 'handle1')
        self.assertEquals(assoc.issued, timestamp + 1)

    def test_removeAssociation(self):
        self.assertEquals(
            self.store.removeAssociation('server-url', 'unknown'), False)

        timestamp = int(time.time())
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle', 'secret', timestamp, 600,
                                         'HMAC-SHA1'))
        self.assertEquals(
            self.store.removeAssociation('server-url', 'handle'), True)
        self.assertEquals(
            self.store.getAssociation('server-url', 'handle'), None)

    def test_useNonce(self):
        timestamp = time.time()
        # The nonce can only be used once.
        self.assertEqual(
            self.store.useNonce('server-url', timestamp, 'salt'), True)
        self.assertEqual(
            self.store.useNonce('server-url', timestamp, 'salt'), False)
        self.assertEqual(
            self.store.useNonce('server-url', timestamp, 'salt'), False)

    def test_useNonce_expired(self):
        timestamp = time.time() - 2 * SKEW
        self.assertEqual(
            self.store.useNonce('server-url', timestamp, 'salt'), False)

    def test_useNonce_future(self):
        timestamp = time.time() + 2 * SKEW
        self.assertEqual(
            self.store.useNonce('server-url', timestamp, 'salt'), False)

    def test_cleanupNonces(self):
        timestamp = time.time()
        self.assertEqual(
            self.store.useNonce('server1', timestamp, 'salt1'), True)
        self.assertEqual(
            self.store.useNonce('server2', timestamp, 'salt2'), True)
        self.assertEqual(
            self.store.useNonce('server3', timestamp, 'salt3'), True)
        self.assertEqual(Nonce.objects.count(), 3)

        self.assertEqual(
            self.store.cleanupNonces(_now=timestamp + 2 * SKEW), 3)
        self.assertEqual(Nonce.objects.count(), 0)

        # The nonces have now been cleared:
        self.assertEqual(
            self.store.useNonce('server1', timestamp, 'salt1'), True)
        self.assertEqual(
            self.store.cleanupNonces(_now=timestamp + 2 * SKEW), 1)
        self.assertEqual(
            self.store.cleanupNonces(_now=timestamp + 2 * SKEW), 0)

    def test_cleanupAssociations(self):
        timestamp = int(time.time()) - 100
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle1', 'secret', timestamp,
                                         50, 'HMAC-SHA1'))
        self.store.storeAssociation(
            'server-url', OIDAssociation('handle2', 'secret', timestamp,
                                         200, 'HMAC-SHA1'))


        self.assertEquals(self.store.cleanupAssociations(), 1)

        # The second (non-expired) association is left behind.
        self.assertNotEqual(self.store.getAssociation('server-url', 'handle2'),
                            None)


def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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

from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

# views
from django.contrib.auth import views as auth_views
from django_authopenid import views as oid_views
from registration import views as reg_views


urlpatterns = patterns('',
    # django registration activate
    url(r'^activate/(?P<activation_key>\w+)/$', reg_views.activate, name='registration_activate'),
    
    # user profile
    
    url(r'^password/reset/$', auth_views.password_reset,  name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        name='auth_password_reset_complete'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        name='auth_password_reset_done'),
    url(r'^password/$',oid_views.password_change, name='auth_password_change'),
    
    # manage account registration
    url(r'^associate/complete/$', oid_views.complete_associate, name='user_complete_associate'),
    url(r'^associate/$', oid_views.associate, name='user_associate'),
    url(r'^dissociate/$', oid_views.dissociate, name='user_dissociate'),
    url(r'^register/$', oid_views.register, name='user_register'),
    url(r'^signout/$', oid_views.signout, name='user_signout'),
    url(r'^signin/complete/$', oid_views.complete_signin, name='user_complete_signin'),
    url(r'^signin/$', oid_views.signin, name='user_signin'),
    url(r'^signup/$', reg_views.register, name='registration_register'),
    url(r'^signup/complete/$',direct_to_template, 
        {'template': 'registration/registration_complete.html'},
        name='registration_complete'),
        
    # yadis uri
    url(r'^yadis.xrdf$', oid_views.xrdf, name='oid_xrdf'),
)

########NEW FILE########
__FILENAME__ = importlib
# From django project. See LICENSE_DJANGO for license.
# Taken from Python 2.7 with permission from/by the original author.

import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = mimeparse
"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of 
the HTTP specification [RFC 2616] for a complete explaination.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Contents:
    - parse_mime_type():   Parses a mime-type into it's component parts.
    - parse_media_range(): Media-ranges are mime-types with wild-cards and a 
    'q' quality parameter.
    - quality():           Determines the quality ('q') of a mime-type when 
    compared against a list of media-ranges.
    - quality_parsed():    Just like quality() except the second parameter must
     be pre-parsed.
    - best_match():        Choose the mime-type with the highest quality ('q')
     from a list of candidates. 
"""

__version__ = "0.1.1"
__author__ = 'Joe Gregorio'
__email__ = "joe@bitworking.org"
__credits__ = ""

def parse_mime_type(mime_type):
    """Carves up a mime_type and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/xhtml;q=0.5' would
       get parsed into:

       ('application', 'xhtml', {'q', '0.5'})
       """
    parts = mime_type.split(";")
    params = dict([tuple([s.strip() for s in param.split("=")])\
            for param in parts[1:] ])
    (type, subtype) = parts[0].split("/")
    return (type.strip(), subtype.strip(), params)

def parse_media_range(range):
    """Carves up a media range and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/*;q=0.5' would
       get parsed into:

       ('application', '*', {'q', '0.5'})

       In addition this function also guarantees that there 
       is a value for 'q' in the params dictionary, filling it
       in with a proper default if necessary.
       """
    (type, subtype, params) = parse_mime_type(range)
    if not params.has_key('q') or not params['q'] or \
            not float(params['q']) or float(params['q']) > 1\
            or float(params['q']) < 0:
        params['q'] = '1'
    return (type, subtype, params)

def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a given mime_type against 
       a list of media_ranges that have already been 
       parsed by parse_media_range(). Returns the 
       'q' quality parameter of the best match, 0 if no
       match was found. This function bahaves the same as quality()
       except that 'parsed_ranges' must be a list of
       parsed media ranges. """
    best_fitness = -1 
    best_match = ""
    best_fit_q = 0
    (target_type, target_subtype, target_params) =\
            parse_media_range(mime_type)
    for (type, subtype, params) in parsed_ranges:
        param_matches = reduce(lambda x, y: x+y, [1 for (key, value) in \
                target_params.iteritems() if key != 'q' and \
                params.has_key(key) and value == params[key]], 0)
        if (type == target_type or type == '*' or target_type == '*') and \
                (subtype == target_subtype or subtype == '*' or target_subtype == '*'):
            fitness = (type == target_type) and 100 or 0
            fitness += (subtype == target_subtype) and 10 or 0
            fitness += param_matches
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']
            
    return float(best_fit_q)
    
def quality(mime_type, ranges):
    """Returns the quality 'q' of a mime_type when compared
    against the media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7, text/html;level=1, '
    'text/html;level=2;q=0.4, */*;q=0.5')
    0.7
    
    """ 
    parsed_ranges = [parse_media_range(r) for r in ranges.split(",")]
    return quality_parsed(mime_type, parsed_ranges)

def best_match(supported, header):
    """Takes a list of supported mime-types and finds the best
    match for all the media-ranges listed in header. The value of
    header must be a string that conforms to the format of the 
    HTTP Accept: header. The value of 'supported' is a list of
    mime-types.
    
    >>> best_match(['application/xbel+xml', 'text/xml'], 'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    parsed_header = [parse_media_range(r) for r in header.split(",")]
    weighted_matches = [(quality_parsed(mime_type, parsed_header), mime_type)\
            for mime_type in supported]
    weighted_matches.sort()
    return weighted_matches[-1][0] and weighted_matches[-1][1] or ''

if __name__ == "__main__":
    import unittest

    class TestMimeParsing(unittest.TestCase):

        def test_parse_media_range(self):
            self.assert_(('application', 'xml', {'q': '1'}) == parse_media_range('application/xml;q=1'))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml'))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml;q='))
            self.assertEqual(('application', 'xml', {'q': '1'}), parse_media_range('application/xml ; q='))
            self.assertEqual(('application', 'xml', {'q': '1', 'b': 'other'}), parse_media_range('application/xml ; q=1;b=other'))
            self.assertEqual(('application', 'xml', {'q': '1', 'b': 'other'}), parse_media_range('application/xml ; q=2;b=other'))

        def test_rfc_2616_example(self):
            accept = "text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5"
            self.assertEqual(1, quality("text/html;level=1", accept))
            self.assertEqual(0.7, quality("text/html", accept))
            self.assertEqual(0.3, quality("text/plain", accept))
            self.assertEqual(0.5, quality("image/jpeg", accept))
            self.assertEqual(0.4, quality("text/html;level=2", accept))
            self.assertEqual(0.7, quality("text/html;level=3", accept))

        def test_best_match(self):
            mime_types_supported = ['application/xbel+xml', 'application/xml']
            # direct match
            self.assertEqual(best_match(mime_types_supported, 'application/xbel+xml'), 'application/xbel+xml')
            # direct match with a q parameter
            self.assertEqual(best_match(mime_types_supported, 'application/xbel+xml; q=1'), 'application/xbel+xml')
            # direct match of our second choice with a q parameter
            self.assertEqual(best_match(mime_types_supported, 'application/xml; q=1'), 'application/xml')
            # match using a subtype wildcard
            self.assertEqual(best_match(mime_types_supported, 'application/*; q=1'), 'application/xml')
            # match using a type wildcard
            self.assertEqual(best_match(mime_types_supported, '*/*'), 'application/xml')

            mime_types_supported = ['application/xbel+xml', 'text/xml']
            # match using a type versus a lower weighted subtype
            self.assertEqual(best_match(mime_types_supported, 'text/*;q=0.5,*/*; q=0.1'), 'text/xml')
            # fail to match anything
            self.assertEqual(best_match(mime_types_supported, 'text/html,application/atom+xml; q=0.9'), '')

        def test_support_wildcards(self):
            mime_types_supported = ['image/*', 'application/xml']
            # match using a type wildcard
            self.assertEqual(best_match(mime_types_supported, 'image/png'), 'image/*')
            # match using a wildcard for both requested and supported 
            self.assertEqual(best_match(mime_types_supported, 'image/*'), 'image/*')

    unittest.main() 
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import *
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context


from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

from django.utils.http import urlquote_plus
from django.core.mail import send_mail

from openid.consumer.consumer import Consumer, \
    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg, ax
# needed for some linux distributions like debian
try:
    from openid.yadis import xri
except ImportError:
    from yadis import xri

import re
import urllib

from django_authopenid import DjangoOpenIDStore
from django_authopenid.forms import *
from django_authopenid.models import UserAssociation
from django_authopenid.signals import oid_register
from django_authopenid.utils import *

def _build_context(request, extra_context=None):
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return context    
    
def ask_openid(request, openid_url, redirect_to, on_failure=None):
    """ basic function to ask openid and return response """
    on_failure = on_failure or signin_failure
    sreg_req = None
    ax_req = None
    
    trust_root = getattr(
        settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
    )
    if xri.identifierScheme(openid_url) == 'XRI' and getattr(
            settings, 'OPENID_DISALLOW_INAMES', False
    ):
        msg = _("i-names are not supported")
        return on_failure(request, msg)
    consumer = Consumer(request.session, DjangoOpenIDStore())
    try:
        auth_request = consumer.begin(openid_url)
    except DiscoveryFailure:
        msg = _("The OpenID %s was invalid") % openid_url
        return on_failure(request, msg)
    
    # get capabilities
    use_ax, use_sreg = discover_extensions(openid_url)
    if use_sreg:
        # set sreg extension
        # we always ask for nickname and email
        sreg_attrs = getattr(settings, 'OPENID_SREG', {})
        sreg_attrs.update({ "optional": ['nickname', 'email'] })
        sreg_req = sreg.SRegRequest(**sreg_attrs)
    if use_ax:
        # set ax extension
        # we always ask for nickname and email
        ax_req = ax.FetchRequest()
        ax_req.add(ax.AttrInfo('http://schema.openid.net/contact/email', 
                                alias='email', required=True))
        ax_req.add(ax.AttrInfo('http://schema.openid.net/namePerson/friendly', 
                                alias='nickname', required=True))
                      
        # add custom ax attrs          
        ax_attrs = getattr(settings, 'OPENID_AX', [])
        for attr in ax_attrs:
            if len(attr) == 2:
                ax_req.add(ax.AttrInfo(attr[0], required=alias[1]))
            else:
                ax_req.add(ax.AttrInfo(attr[0]))
       
    if sreg_req is not None:
        auth_request.addExtension(sreg_req)
    if ax_req is not None:
        auth_request.addExtension(ax_req)
    
    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
    return HttpResponseRedirect(redirect_url)

def complete(request, on_success=None, on_failure=None, return_to=None, 
    **kwargs):
    """ complete openid signin """
    on_success = on_success or default_on_success
    on_failure = on_failure or default_on_failure
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    # make sure params are encoded in utf8
    params = dict((k,smart_unicode(v)) for k, v in request.GET.items())
    openid_response = consumer.complete(params, return_to)
            
    if openid_response.status == SUCCESS:
        return on_success(request, openid_response.identity_url,
                openid_response, **kwargs)
    elif openid_response.status == CANCEL:
        return on_failure(request, 'The request was canceled', **kwargs)
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message, **kwargs)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, 'Setup needed', **kwargs)
    else:
        assert False, "Bad openid status: %s" % openid_response.status

def default_on_success(request, identity_url, openid_response, **kwargs):
    """ default action on openid signin success """
    request.session['openid'] = from_openid_response(openid_response)
    return HttpResponseRedirect(clean_next(request.GET.get('next')))

def default_on_failure(request, message, **kwargs):
    """ default failure action on signin """
    return render('openid_failure.html', {
        'message': message
    })


def not_authenticated(func):
    """ decorator that redirect user to next page if
    he is already logged."""
    def decorated(request, *args, **kwargs):
        if request.user.is_authenticated():
            next = request.GET.get("next", "/")
            return HttpResponseRedirect(next)
        return func(request, *args, **kwargs)
    return decorated

def signin_success(request, identity_url, openid_response,
        redirect_field_name=REDIRECT_FIELD_NAME, **kwargs):
    """
    openid signin success.

    If the openid is already registered, the user is redirected to 
    url set par next or in settings with OPENID_REDIRECT_NEXT variable.
    If none of these urls are set user is redirectd to /.

    if openid isn't registered user is redirected to register page.
    """

    openid_ = from_openid_response(openid_response)
    
    openids = request.session.get('openids', [])
    openids.append(openid_)
    request.session['openids'] = openids
    request.session['openid'] = openid_
    try:
        rel = UserAssociation.objects.get(openid_url__exact = str(openid_))
    except:
        # try to register this new user
        redirect_to = request.REQUEST.get(redirect_field_name, '')
        if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
            redirect_to = settings.LOGIN_REDIRECT_URL
        return HttpResponseRedirect(
            "%s?%s" % (reverse('user_register'),
            urllib.urlencode({ redirect_field_name: redirect_to }))
        )
    user_ = rel.user
    if user_.is_active:
        user_.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user_)
        
    redirect_to = request.GET.get(redirect_field_name, '')
    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL
    return HttpResponseRedirect(redirect_to)
    
def signin_failure(request, message, template_name='authopenid/signin.html',
        redirect_field_name=REDIRECT_FIELD_NAME, openid_form=OpenidSigninForm, 
        auth_form=AuthenticationForm, extra_context=None, **kwargs):
    """
    falure with openid signin. Go back to signin page.
    
    :attr request: request object
    :attr template_name: string, name of template to use, default is 
    'authopenid/signin.html'
    :attr redirect_field_name: string, field name used for redirect. by default
    'next'
    :attr openid_form: form use for openid signin, by default `OpenidSigninForm`
    :attr auth_form: form object used for legacy authentification. 
    by default AuthentificationForm form auser auth contrib.
    :attr extra_context: A dictionary of variables to add to the template 
    context. Any callable object in this dictionary will be called to produce 
    the end result which appears in the context.
    """
    return render(template_name, {
        'msg': message,
        'form1': openid_form(),
        'form2': auth_form(),
        redirect_field_name: request.REQUEST.get(redirect_field_name, '')
    }, context_instance=_build_context(request, extra_context))


@not_authenticated
def signin(request, template_name='authopenid/signin.html', 
        redirect_field_name=REDIRECT_FIELD_NAME, openid_form=OpenidSigninForm,
        auth_form=AuthenticationForm, on_failure=None, extra_context=None):
    """Signin page. It manage the legacy authentification (user/password)  
    and authentification with openid.

    :attr request: request object
    :attr template_name: string, name of template to use
    :attr redirect_field_name: string, field name used for redirect. by 
    default 'next'
    :attr openid_form: form use for openid signin, by default 
    `OpenidSigninForm`
    :attr auth_form: form object used for legacy authentification. 
    By default AuthentificationForm form auser auth contrib.
    :attr extra_context: A dictionary of variables to add to the 
    template context. Any callable object in this dictionary will 
    be called to produce the end result which appears in the context.
    """
    if on_failure is None:
        on_failure = signin_failure
        
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    form1 = openid_form()
    form2 = auth_form()
    if request.POST:
        if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
            redirect_to = settings.LOGIN_REDIRECT_URL     
        if 'openid_url' in request.POST.keys():
            form1 = openid_form(data=request.POST)
            if form1.is_valid():
                redirect_url = "%s%s?%s" % (
                        get_url_host(request),
                        reverse('user_complete_signin'), 
                        urllib.urlencode({ redirect_field_name: redirect_to })
                )
                return ask_openid(request, 
                        form1.cleaned_data['openid_url'], 
                        redirect_url, 
                        on_failure=on_failure)
        else:
            # perform normal django authentification
            form2 = auth_form(data=request.POST)
            if form2.is_valid():
                login(request, form2.get_user())
                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()
                return HttpResponseRedirect(redirect_to)
    return render(template_name, {
        'form1': form1,
        'form2': form2,
        redirect_field_name: redirect_to,
        'msg':  request.GET.get('msg','')
    }, context_instance=_build_context(request, extra_context=extra_context))

def complete_signin(request, redirect_field_name=REDIRECT_FIELD_NAME,  
        openid_form=OpenidSigninForm, auth_form=AuthenticationForm, 
        on_success=signin_success, on_failure=signin_failure, 
        extra_context=None):
    """
    in case of complete signin with openid 

    :attr request: request object
    :attr openid_form: form use for openid signin, by default 
    `OpenidSigninForm`
    :attr auth_form: form object used for legacy authentification. 
    by default AuthentificationForm form auser auth contrib.
    :attr on_success: callbale, function used when openid auth success
    :attr on_failure: callable, function used when openid auth failed.
    :attr extra_context: A dictionary of variables to add to the template 
    context.
    Any callable object in this dictionary will be called to produce the
    end result which appears in the context.  
    """
    return complete(request, on_success, on_failure,
            get_url_host(request) + reverse('user_complete_signin'),
            redirect_field_name=redirect_field_name, openid_form=openid_form, 
            auth_form=auth_form, extra_context=extra_context)

def is_association_exist(openid_url):
    """ test if an openid is already in database """
    is_exist = True
    try:
        uassoc = UserAssociation.objects.get(openid_url__exact = str(openid_url))
    except:
        is_exist = False
    return is_exist
    
def register_account(form, _openid):
    """ create an account """
    user = User.objects.create_user(form.cleaned_data['username'], 
                            form.cleaned_data['email'])
    user.backend = "django.contrib.auth.backends.ModelBackend"
    oid_register.send(sender=user, openid=_openid)
    return user

@not_authenticated
def register(request, template_name='authopenid/complete.html', 
            redirect_field_name=REDIRECT_FIELD_NAME, 
            register_form=OpenidRegisterForm, auth_form=AuthenticationForm, 
            register_account=register_account, send_email=True, 
            extra_context=None):
    """
    register an openid.

    If user is already a member he can associate its openid with 
    its account.

    A new account could also be created and automaticaly associated
    to the openid.

    :attr request: request object
    :attr template_name: string, name of template to use, 
    'authopenid/complete.html' by default
    :attr redirect_field_name: string, field name used for redirect. by default 
    'next'
    :attr register_form: form use to create a new account. By default 
    `OpenidRegisterForm`
    :attr auth_form: form object used for legacy authentification. 
    by default `OpenidVerifyForm` form auser auth contrib.
    :attr register_account: callback used to create a new account from openid. 
    It take the register_form as param.
    :attr send_email: boolean, by default True. If True, an email will be sent 
    to the user.
    :attr extra_context: A dictionary of variables to add to the template 
    context. Any callable object in this dictionary will be called to produce 
    the end result which appears in the context.
    """
    is_redirect = False
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    openid_ = request.session.get('openid', None)
    if openid_ is None or not openid_:
        return HttpResponseRedirect("%s?%s" % (reverse('user_signin'),
                                urllib.urlencode({ 
                                redirect_field_name: redirect_to })))

    nickname = ''
    email = ''
    if openid_.sreg is not None:
        nickname = openid_.sreg.get('nickname', '')
        email = openid_.sreg.get('email', '')
    if openid_.ax is not None and not nickname or not email:
        if openid_.ax.get('http://schema.openid.net/namePerson/friendly', False):
            nickname = openid_.ax.get('http://schema.openid.net/namePerson/friendly')[0]
        if openid_.ax.get('http://schema.openid.net/contact/email', False):
            email = openid_.ax.get('http://schema.openid.net/contact/email')[0]
        
    
    form1 = register_form(initial={
        'username': nickname,
        'email': email,
    }) 
    form2 = auth_form(initial={ 
        'username': nickname,
    })
    
    if request.POST:
        user_ = None
        if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
            redirect_to = settings.LOGIN_REDIRECT_URL
        if 'email' in request.POST.keys():
            form1 = register_form(data=request.POST)
            if form1.is_valid():
                user_ = register_account(form1, openid_)
        else:
            form2 = auth_form(data=request.POST)
            if form2.is_valid():
                user_ = form2.get_user()
        if user_ is not None:
            # associate the user to openid
            uassoc = UserAssociation(
                        openid_url=str(openid_),
                        user_id=user_.id
            )
            uassoc.save(send_email=send_email)
            login(request, user_)    
            return HttpResponseRedirect(redirect_to) 
    
    return render(template_name, {
        'form1': form1,
        'form2': form2,
        redirect_field_name: redirect_to,
        'nickname': nickname,
        'email': email
    }, context_instance=_build_context(request, extra_context=extra_context))

@login_required
def signout(request, next_page=None, template_name='registration/logged_out.html'):
    """
    signout from the website. Remove openid from session and kill it.
    :attr request: request object
    :attr next_page: default redirect page after logout
    :attr template_name: string, name of template to use when next_page isn't set, 
    'registration/logged_out.html' by default
    """
    try:
        del request.session['openid']
    except KeyError:
        pass
    next = request.GET.get('next')
    logout(request)
    if next is not None:
        return HttpResponseRedirect(next)
    
    if next_page is None:
        return render(template_name, {
            'title': _('Logged out')}, context_instance=RequestContext(request))
            
    return HttpResponseRedirect(next_page or request.path)
    
def xrdf(request, template_name='authopenid/yadis.xrdf'):
    """ view used to process the xrdf file"""
    
    url_host = get_url_host(request)
    return_to = [
        "%s%s" % (url_host, reverse('user_complete_signin'))
    ]
    response = render(template_name, { 
        'return_to': return_to 
        }, context_instance=RequestContext(request))
        
        
    response['Content-Type'] = "application/xrds+xml"
    response['X-XRDS-Location']= request.build_absolute_uri(reverse('oid_xrdf'))
    return response    
        
@login_required
def password_change(request, 
        template_name='authopenid/password_change_form.html', 
        set_password_form=SetPasswordForm, 
        change_password_form=PasswordChangeForm, post_change_redirect=None, 
        extra_context=None):
    """
    View that allow a user to add a password to its account or change it.

    :attr request: request object
    :attr template_name: string, name of template to use, 
    'authopenid/password_change_form.html' by default
    :attr set_password_form: form use to create a new password. By default 
    ``django.contrib.auth.forms.SetPasswordForm``
    :attr change_password_form: form objectto change passworf. 
    by default `django.contrib.auth.forms.SetPasswordForm.PasswordChangeForm` 
    form auser auth contrib.
    :attr post_change_redirect: url used to redirect user after password change.
    It take the register_form as param.
    :attr extra_context: A dictionary of variables to add to the template context. 
    Any callable object in this dictionary will be called to produce the
    end result which appears in the context.
    """
    if post_change_redirect is None:
        post_change_redirect = settings.LOGIN_REDIRECT_URL

    set_password = False
    if request.user.has_usable_password():
        change_form = change_password_form
    else:
        set_password = True
        change_form = set_password_form

    if request.POST:
        form = change_form(request.user, request.POST)
        if form.is_valid():
            form.save()
            msg = urllib.quote(_("Password changed"))
            redirect_to = "%s?%s" % (post_change_redirect, 
                                urllib.urlencode({ "msg": msg }))
            return HttpResponseRedirect(redirect_to)
    else:
        form = change_form(request.user)

    return render(template_name, {
        'form': form,
        'set_password': set_password
    }, context_instance=_build_context(request, extra_context=extra_context))

@login_required
def associate_failure(request, message, 
        template_failure="authopenid/associate.html", 
        openid_form=AssociateOpenID, redirect_name=None, 
        extra_context=None, **kwargs):
        
    """ function used when new openid association fail"""
    
    return render(template_failure, {
        'form': openid_form(request.user),
        'msg': message,
    }, context_instance=_build_context(request, extra_context=extra_context))

@login_required
def associate_success(request, identity_url, openid_response,
        redirect_field_name=REDIRECT_FIELD_NAME, send_email=True, **kwargs):
    """ 
    function used when new openid association success. redirect the user
    """
    openid_ = from_openid_response(openid_response)
    openids = request.session.get('openids', [])
    openids.append(openid_)
    request.session['openids'] = openids
    uassoc = UserAssociation(
                openid_url=str(openid_),
                user_id=request.user.id
    )
    uassoc.save(send_email=send_email)
    
    redirect_to = request.GET.get(redirect_field_name, '')
    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL
    return HttpResponseRedirect(redirect_to)

@login_required
def complete_associate(request, redirect_field_name=REDIRECT_FIELD_NAME,
        template_failure='authopenid/associate.html', 
        openid_form=AssociateOpenID, redirect_name=None, 
        on_success=associate_success, on_failure=associate_failure,
        send_email=True, extra_context=None):
        
    """ in case of complete association with openid """
        
    return complete(request, on_success, on_failure,
            get_url_host(request) + reverse('user_complete_associate'),
            redirect_field_name=redirect_field_name, openid_form=openid_form, 
            template_failure=template_failure, redirect_name=redirect_name, 
            send_email=send_email, extra_context=extra_context)
    
@login_required
def associate(request, template_name='authopenid/associate.html', 
        openid_form=AssociateOpenID, redirect_field_name=REDIRECT_FIELD_NAME,
        on_failure=associate_failure, extra_context=None):
        
    """View that allow a user to associate a new openid to its account.
    
    :attr request: request object
    :attr template_name: string, name of template to use, 
    'authopenid/associate.html' by default
    :attr openid_form: form use enter openid url. By default 
    ``django_authopenid.forms.AssociateOpenID``
    :attr redirect_field_name: string, field name used for redirect. 
    by default 'next'
    :attr on_success: callbale, function used when openid auth success
    :attr on_failure: callable, function used when openid auth failed. 
    by default ``django_authopenid.views.associate_failure`
    :attr extra_context: A dictionary of variables to add to the template
    context. A callable object in this dictionary will be called to produce 
    the end result which appears in the context.
    """
    
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if request.POST:            
        form = openid_form(request.user, data=request.POST)
        if form.is_valid():
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            redirect_url = "%s%s?%s" % (
                    get_url_host(request),
                    reverse('user_complete_associate'),
                    urllib.urlencode({ redirect_field_name: redirect_to })
            )
            return ask_openid(request, 
                    form.cleaned_data['openid_url'], 
                    redirect_url, 
                    on_failure=on_failure)
    else:
        form = openid_form(request.user)
    return render(template_name, {
        'form': form,
        redirect_field_name: redirect_to
    }, context_instance=_build_context(request, extra_context=extra_context))     
    
@login_required
def dissociate(request, template_name="authopenid/dissociate.html",
        dissociate_form=OpenidDissociateForm, 
        redirect_field_name=REDIRECT_FIELD_NAME, 
        default_redirect=settings.LOGIN_REDIRECT_URL, extra_context=None):
        
    """ view used to dissociate an openid from an account """
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = default_redirect
        
    # get list of associated openids
    rels = UserAssociation.objects.filter(user__id=request.user.id)
    associated_openids = [rel.openid_url for rel in rels]
    if len(associated_openids) == 1 and not request.user.has_usable_password():
        msg = _("You can't remove this openid. "
        "You should set a password first.")
        return HttpResponseRedirect("%s?%s" % (redirect_to,
            urllib.urlencode({ "msg": msg })))
    
    if request.POST:
        form = dissociate_form(request.POST)
        if form.is_valid():
            openid_url = form.cleaned_data['openid_url']
            msg = ""
            if openid_url not in associated_openids:
                msg = _("%s is not associated to your account") % openid_url
            
            if not msg:
                UserAssociation.objects.get(openid_url__exact=openid_url).delete()
                if openid_url == request.session.get('openid_url'):
                    del request.session['openid_url']
                msg = _("openid removed.")
            return HttpResponseRedirect("%s?%s" % (redirect_to,
                urllib.urlencode({ "msg": msg })))
    else:
        openid_url = request.GET.get('openid_url', '')
        if not openid_url:
            msg = _("Invalid OpenID url.")
            return HttpResponseRedirect("%s?%s" % (redirect_to,
                urllib.urlencode({ "msg": msg })))
        form = dissociate_form(initial={ 'openid_url': openid_url })
    return render(template_name, {
            "form": form,
            "openid_url": openid_url
    }, context_instance=_build_context(request, extra_context=extra_context))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('home.views',
        (r'^$', 'home'),
        )

########NEW FILE########
__FILENAME__ = views
from django.views.generic.simple import direct_to_template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect

def select_city(request):
    return direct_to_template(request, "select_city.html")

def home(request, city):
    return direct_to_template(request, city+"_home.html", {'city':city})

@login_required
def settings(request):
    return direct_to_template(request, "authopenid/settings.html")


########NEW FILE########
__FILENAME__ = forms
from django import forms

class CreateSoftlinkForm(forms.Form):
   softlink_id = forms.IntegerField()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('janitor.views',
        url(r'^inconsistent/routes/(?P<maxdist>\d+)?$', 'inconsistent_routes'),
        url(r'^nearby/stage/(?P<stage_id>\d+)?/$','softlinking_stages',name='softlinking_stages'),
        )

########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse

from routes.models import *
from django.views.generic.simple import direct_to_template
from django.contrib.admin.views.decorators import staff_member_required
from stages.models import *
from forms import CreateSoftlinkForm

from math import *
import marshal
import os
CUR_DIR = os.path.dirname(__file__)
class Inconsistency():
    pass

def find_inconsistencies(max_distance, city):
    routes = Route.objects.filter(city=city)
    D = marshal.load(open(os.path.abspath(os.path.join(CUR_DIR, '../distancegraph')),'rb'))
    fixables = []
    for r in routes:
        stages = r.stages.all()
        for i in xrange(0, len(stages) - 1):
            if stages[i].location and stages[i+1].location:
                dist = D[stages[i].id][stages[i+1].id]
                if dist > max_distance:
                    ic = Inconsistency()
                    ic.route = r
                    ic.stage = stages[i+1]
                    ic.distance = ceil(dist)
                    fixables.append(ic)
                    break
    return fixables

def inconsistent_routes(request, maxdist, city):
    if not maxdist:
        maxdist = 5
    incs = find_inconsistencies(int(maxdist),city)
    incs.sort(key=lambda x: x.distance,reverse=True)
    return direct_to_template   (
            request, 
            'janitor/routes.html', 
            {
                'inconsistencies':incs,
                'city': city
                })

@staff_member_required
def softlinking_stages(request, city, stage_id):

   if request.method == 'POST':
      form = CreateSoftlinkForm(request.POST)
      if form.is_valid():
         cd = form.cleaned_data
         newSoftlink = Stage.objects.get(id=cd['softlink_id'])
         s = Stage.objects.get(id=stage_id)
         s.softlinks.add(newSoftlink)
         s.save()
         for st in s.softlinks.exclude(id=s.id).exclude(id=newSoftlink.id):
            st.softlinks.add(newSoftlink)
            st.save()
      return HttpResponseRedirect(reverse('softlinking_stages', args=(city, stage_id,)))
   form = CreateSoftlinkForm()
   stage = Stage.objects.get(pk=stage_id)
   if not stage.location:
      return HttpResponse("Stage doesn't have a location yet")
   D = marshal.load(open(os.path.abspath(os.path.join(CUR_DIR, '../distancegraph')),'rb'))
   softlinks = stage.softlinks.all()
   nearby_stages = []
   for st in Stage.objects.filter(city=city).exclude(id=stage.id):
      if st.location and D[stage.id][st.id]<1:
         nearby_stages.append(st)
   return direct_to_template (
      request,'janitor/softlinking.html',
      {
         'stage':stage,
         'city': city, 
         'softlinks':softlinks,
         'form':form,
         'nearby_stages':nearby_stages
      }
   )

########NEW FILE########
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
__FILENAME__ = mobile_settings
from settings import *
MEDIA_ROOT = os.path.join(ROOT_DIR, 'static_mobile')
TEMPLATE_DIRS = (
        os.path.join(ROOT_DIR, 'templates_mobile'),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from registration.models import RegistrationProfile


class RegistrationAdmin(admin.ModelAdmin):
    actions = ['activate_users', 'resend_activation_email']
    list_display = ('user', 'activation_key_expired')
    raw_id_fields = ['user']
    search_fields = ('user__username', 'user__first_name')

    def activate_users(self, request, queryset):
        """
        Activates the selected users, if they are not alrady
        activated.
        
        """
        for profile in queryset:
            RegistrationProfile.objects.activate_user(profile.activation_key)
    activate_users.short_description = _("Activate users")

    def resend_activation_email(self, request, queryset):
        """
        Re-sends activation emails for the selected users.

        Note that this will *only* send activation emails for users
        who are eligible to activate; emails will not be sent to users
        whose activation keys have expired or who have already
        activated.
        
        """
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)

        for profile in queryset:
            if not profile.activation_key_expired():
                profile.send_activation_email(site)
    resend_activation_email.short_description = _("Re-send activation emails")


admin.site.register(RegistrationProfile, RegistrationAdmin)

########NEW FILE########
__FILENAME__ = auth_urls
"""
URL patterns for the views included in ``django.contrib.auth``.

Including these URLs (via the ``include()`` directive) will set up the
following patterns based at whatever URL prefix they are included
under:

* User login at ``login/``.

* User logout at ``logout/``.

* The two-step password change at ``password/change/`` and
  ``password/change/done/``.

* The four-step password reset at ``password/reset/``,
  ``password/reset/confirm/``, ``password/reset/complete/`` and
  ``password/reset/done/``.

The default registration backend already has an ``include()`` for
these URLs, so under the default setup it is not necessary to manually
include these views. Other backends may or may not include them;
consult a specific backend's documentation for details.

"""

from django.conf.urls.defaults import *

from django.contrib.auth import views as auth_views


urlpatterns = patterns('',
                       url(r'^login/$',
                           auth_views.login,
                           {'template_name': 'registration/login.html'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'registration/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/$',
                           auth_views.password_change,
                           name='auth_password_change'),
                       url(r'^password/change/done/$',
                           auth_views.password_change_done,
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           auth_views.password_reset,
                           name='auth_password_reset'),
                       url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           auth_views.password_reset_confirm,
                           name='auth_password_reset_confirm'),
                       url(r'^password/reset/complete/$',
                           auth_views.password_reset_complete,
                           name='auth_password_reset_complete'),
                       url(r'^password/reset/done/$',
                           auth_views.password_reset_done,
                           name='auth_password_reset_done'),
)

########NEW FILE########
__FILENAME__ = urls
"""
URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('registration.backends.default.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize the behavior (e.g., by passing extra
arguments to the various views) or split up the URLs, feel free to set
up your own URL patterns for these views instead.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
                       url(r'^activate/complete/$',
                           direct_to_template,
                           { 'template': 'registration/activation_complete.html' },
                           name='registration_activation_complete'),
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           { 'backend': 'registration.backends.default.DefaultBackend' },
                           name='registration_activate'),
                       url(r'^register/$',
                           register,
                           { 'backend': 'registration.backends.default.DefaultBackend' },
                           name='registration_register'),
                       url(r'^register/complete/$',
                           direct_to_template,
                           { 'template': 'registration/registration_complete.html' },
                           name='registration_complete'),
                       url(r'^register/closed/$',
                           direct_to_template,
                           { 'template': 'registration/registration_closed.html' },
                           name='registration_disallowed'),
                       (r'', include('registration.auth_urls')),
                       )

########NEW FILE########
__FILENAME__ = forms
"""
Forms and validation code for user registration.

"""


from django.contrib.auth.models import User
from django import forms
from django.utils.translation import ugettext_lazy as _


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.
    
    """
    username = forms.RegexField(regex=r'^\w+$',
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_("Username"),
                                error_messages={ 'invalid': _("This value must contain only letters, numbers and underscores.") })
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_("Email address"))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_("Password (again)"))
    
    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_("A user with that username already exists."))

    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.
    
    """
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={ 'required': _("You must agree to the terms to register") })


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.
    
    """
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email']


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.
    
    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.
    
    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com',
                   'yahoo.com']
    
    def clean_email(self):
        """
        Check the supplied email address against a list of known free
        webmail domains.
        
        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(_("Registration using free email addresses is prohibited. Please supply a different email address."))
        return self.cleaned_data['email']

########NEW FILE########
__FILENAME__ = cleanupregistration
"""
A management command which deletes expired accounts (e.g.,
accounts which signed up but never activated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""

from django.core.management.base import NoArgsCommand

from registration.models import RegistrationProfile


class Command(NoArgsCommand):
    help = "Delete expired user registrations from the database"

    def handle_noargs(self, **options):
        RegistrationProfile.objects.delete_expired_users()

########NEW FILE########
__FILENAME__ = models
import datetime
import random
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _


SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activation_key = self.model.ACTIVATED
                profile.save()
                return user
        return False
    
    def create_inactive_user(self, username, email, password,
                             site, send_email=True):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.save()

        registration_profile = self.create_profile(new_user)

        if send_email:
            registration_profile.send_activation_email(site)

        return new_user
    create_inactive_user = transaction.commit_on_success(create_inactive_user)

    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        activation_key = sha_constructor(salt+user.username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)
        
    def delete_expired_users(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    ACTIVATED = u"ALREADY_ACTIVATED"
    
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"Registration information for %s" % self.user
    
    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.

        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True

    def send_activation_email(self, site):
        """
        Send an activation email to the user associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:

        ``registration/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.

        ``registration/activation_email.txt``
            This template will be used for the body of the email.

        These templates will each receive the following context
        variables:

        ``activation_key``
            The activation key for the new account.

        ``expiration_days``
            The number of days remaining during which the account may
            be activated.

        ``site``
            An object representing the site on which the user
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.

        """
        ctx_dict = { 'activation_key': self.activation_key,
                     'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                     'site': site }
        subject = render_to_string('registration/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        message = render_to_string('registration/activation_email.txt',
                                   ctx_dict)
        
        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
    

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


# A new user has registered.
user_registered = Signal(providing_args=["user", "request"])

# A user has activated his or her account.
user_activated = Signal(providing_args=["user", "request"])

########NEW FILE########
__FILENAME__ = backends
import datetime

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIRequest
from django.test import Client
from django.test import TestCase

from registration import forms
from registration import signals
from registration.admin import RegistrationAdmin
from registration.backends import get_backend
from registration.backends.default import DefaultBackend
from registration.models import RegistrationProfile


class _MockRequestClient(Client):
    """
    A ``django.test.Client`` subclass which can return mock
    ``HttpRequest`` objects.
    
    """
    def request(self, **request):
        """
        Rather than issuing a request and returning the response, this
        simply constructs an ``HttpRequest`` object and returns it.
        
        """
        environ = {
            'HTTP_COOKIE':      self.cookies,
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REMOTE_ADDR':       '127.0.0.1',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       '',
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       '80',
            'SERVER_PROTOCOL':   'HTTP/1.1',
            'wsgi.version':      (1,0),
            'wsgi.url_scheme':   'http',
            'wsgi.errors':       self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread':  False,
            'wsgi.run_once':     False,
            }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


def _mock_request():
    """
    Construct and return a mock ``HttpRequest`` object; this is used
    in testing backend methods which expect an ``HttpRequest`` but
    which are not being called from views.
    
    """
    return _MockRequestClient().request()


class BackendRetrievalTests(TestCase):
    """
    Test that utilities for retrieving the active backend work
    properly.

    """
    def test_get_backend(self):
        """
        Verify that ``get_backend()`` returns the correct value when
        passed a valid backend.

        """
        self.failUnless(isinstance(get_backend('registration.backends.default.DefaultBackend'),
                                   DefaultBackend))

    def test_backend_error_invalid(self):
        """
        Test that a nonexistent/unimportable backend raises the
        correct exception.

        """
        self.assertRaises(ImproperlyConfigured, get_backend,
                          'registration.backends.doesnotexist.NonExistentBackend')

    def test_backend_attribute_error(self):
        """
        Test that a backend module which exists but does not have a
        class of the specified name raises the correct exception.
        
        """
        self.assertRaises(ImproperlyConfigured, get_backend,
                          'registration.backends.default.NonexistentBackend')


class DefaultRegistrationBackendTests(TestCase):
    """
    Test the default registration backend.

    Running these tests successfull will require two templates to be
    created for the sending of activation emails; details on these
    templates and their contexts may be found in the documentation for
    the default backend.

    """
    def setUp(self):
        """
        Create an instance of the default backend for use in testing,
        and set ``ACCOUNT_ACTIVATION_DAYS``.

        """
        from registration.backends.default import DefaultBackend
        self.backend = DefaultBackend()
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        """
        Restore the original value of ``ACCOUNT_ACTIVATION_DAYS``.

        """
        settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_registration(self):
        """
        Test the registration process: registration creates a new
        inactive account and a new profile with activation key,
        populates the correct account data and sends an activation
        email.

        """
        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')

        # Details of the returned user must match what went in.
        self.assertEqual(new_user.username, 'bob')
        self.failUnless(new_user.check_password('secret'))
        self.assertEqual(new_user.email, 'bob@example.com')

        # New user must not be active.
        self.failIf(new_user.is_active)

        # A registration profile was created, and an activation email
        # was sent.
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_no_sites(self):
        """
        Test that registration still functions properly when
        ``django.contrib.sites`` is not installed; the fallback will
        be a ``RequestSite`` instance.
        
        """
        Site._meta.installed = False

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')

        self.assertEqual(new_user.username, 'bob')
        self.failUnless(new_user.check_password('secret'))
        self.assertEqual(new_user.email, 'bob@example.com')

        self.failIf(new_user.is_active)

        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        
        Site._meta.installed = True

    def test_valid_activation(self):
        """
        Test the activation process: activating within the permitted
        window sets the account's ``is_active`` field to ``True`` and
        resets the activation key.

        """
        valid_user = self.backend.register(_mock_request(),
                                           username='alice',
                                           email='alice@example.com',
                                           password1='swordfish')

        valid_profile = RegistrationProfile.objects.get(user=valid_user)
        activated = self.backend.activate(_mock_request(),
                                          valid_profile.activation_key)
        self.assertEqual(activated.username, valid_user.username)
        self.failUnless(activated.is_active)

        # Fetch the profile again to verify its activation key has
        # been reset.
        valid_profile = RegistrationProfile.objects.get(user=valid_user)
        self.assertEqual(valid_profile.activation_key,
                         RegistrationProfile.ACTIVATED)

    def test_invalid_activation(self):
        """
        Test the activation process: trying to activate outside the
        permitted window fails, and leaves the account inactive.

        """
        expired_user = self.backend.register(_mock_request(),
                                             username='bob',
                                             email='bob@example.com',
                                             password1='secret')

        expired_user.date_joined = expired_user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_user.save()
        expired_profile = RegistrationProfile.objects.get(user=expired_user)
        self.failIf(self.backend.activate(_mock_request(),
                                          expired_profile.activation_key))
        self.failUnless(expired_profile.activation_key_expired())

    def test_allow(self):
        """
        Test that the setting ``REGISTRATION_OPEN`` appropriately
        controls whether registration is permitted.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = True
        self.failUnless(self.backend.registration_allowed(_mock_request()))

        settings.REGISTRATION_OPEN = False
        self.failIf(self.backend.registration_allowed(_mock_request()))
        settings.REGISTRATION_OPEN = old_allowed

    def test_form_class(self):
        """
        Test that the default form class returned is
        ``registration.forms.RegistrationForm``.

        """
        self.failUnless(self.backend.get_form_class(_mock_request()) is forms.RegistrationForm)

    def test_post_registration_redirect(self):
        """
        Test that the default post-registration redirect is the named
        pattern ``registration_complete``.

        """
        self.assertEqual(self.backend.post_registration_redirect(_mock_request(), User()),
                         ('registration_complete', (), {}))

    def test_registration_signal(self):
        """
        Test that registering a user sends the ``user_registered``
        signal.
        
        """
        def receiver(sender, **kwargs):
            self.failUnless('user' in kwargs)
            self.assertEqual(kwargs['user'].username, 'bob')
            self.failUnless('request' in kwargs)
            self.failUnless(isinstance(kwargs['request'], WSGIRequest))
            received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_registered.connect(receiver, sender=self.backend.__class__)

        self.backend.register(_mock_request(),
                              username='bob',
                              email='bob@example.com',
                              password1='secret')

        self.assertEqual(len(received_signals), 1)
        self.assertEqual(received_signals, [signals.user_registered])

    def test_activation_signal_success(self):
        """
        Test that successfully activating a user sends the
        ``user_activated`` signal.
        
        """
        def receiver(sender, **kwargs):
            self.failUnless('user' in kwargs)
            self.assertEqual(kwargs['user'].username, 'bob')
            self.failUnless('request' in kwargs)
            self.failUnless(isinstance(kwargs['request'], WSGIRequest))
            received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_activated.connect(receiver, sender=self.backend.__class__)

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')
        profile = RegistrationProfile.objects.get(user=new_user)
        self.backend.activate(_mock_request(), profile.activation_key)

        self.assertEqual(len(received_signals), 1)
        self.assertEqual(received_signals, [signals.user_activated])

    def test_activation_signal_failure(self):
        """
        Test that an unsuccessful activation attempt does not send the
        ``user_activated`` signal.
        
        """
        receiver = lambda sender, **kwargs: received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_activated.connect(receiver, sender=self.backend.__class__)

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()
        profile = RegistrationProfile.objects.get(user=new_user)
        self.backend.activate(_mock_request(), profile.activation_key)

        self.assertEqual(len(received_signals), 0)

    def test_email_send_action(self):
        """
        Test re-sending of activation emails via admin action.
        
        """
        admin_class = RegistrationAdmin(RegistrationProfile, admin.site)
        
        alice = self.backend.register(_mock_request(),
                                      username='alice',
                                      email='alice@example.com',
                                      password1='swordfish')
        
        admin_class.resend_activation_email(_mock_request(),
                                            RegistrationProfile.objects.all())
        self.assertEqual(len(mail.outbox), 2) # One on registering, one more on the resend.
        
        RegistrationProfile.objects.filter(user=alice).update(activation_key=RegistrationProfile.ACTIVATED)
        admin_class.resend_activation_email(_mock_request(),
                                            RegistrationProfile.objects.all())
        self.assertEqual(len(mail.outbox), 2) # No additional email because the account has activated.

    def test_activation_action(self):
        """
        Test manual activation of users view admin action.
        
        """
        admin_class = RegistrationAdmin(RegistrationProfile, admin.site)

        alice = self.backend.register(_mock_request(),
                                      username='alice',
                                      email='alice@example.com',
                                      password1='swordfish')

        admin_class.activate_users(_mock_request(),
                                   RegistrationProfile.objects.all())
        self.failUnless(User.objects.get(username='alice').is_active)

########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.models import User
from django.test import TestCase

from registration import forms


class RegistrationFormTests(TestCase):
    """
    Test the default registration forms.

    """
    def test_registration_form(self):
        """
        Test that ``RegistrationForm`` enforces username constraints
        and matching passwords.

        """
        # Create a user so we can verify that duplicate usernames aren't
        # permitted.
        User.objects.create_user('alice', 'alice@example.com', 'secret')

        invalid_data_dicts = [
            # Non-alphanumeric username.
            {'data': {'username': 'foo/bar',
                      'email': 'foo@example.com',
                      'password1': 'foo',
                      'password2': 'foo'},
            'error': ('username', [u"This value must contain only letters, numbers and underscores."])},
            # Already-existing username.
            {'data': {'username': 'alice',
                      'email': 'alice@example.com',
                      'password1': 'secret',
                      'password2': 'secret'},
            'error': ('username', [u"A user with that username already exists."])},
            # Mismatched passwords.
            {'data': {'username': 'foo',
                      'email': 'foo@example.com',
                      'password1': 'foo',
                      'password2': 'bar'},
            'error': ('__all__', [u"The two password fields didn't match."])},
            ]

        for invalid_dict in invalid_data_dicts:
            form = forms.RegistrationForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

        form = forms.RegistrationForm(data={'username': 'foo',
                                            'email': 'foo@example.com',
                                            'password1': 'foo',
                                            'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_tos(self):
        """
        Test that ``RegistrationFormTermsOfService`` requires
        agreement to the terms of service.

        """
        form = forms.RegistrationFormTermsOfService(data={'username': 'foo',
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['tos'],
                         [u"You must agree to the terms to register"])

        form = forms.RegistrationFormTermsOfService(data={'username': 'foo',
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo',
                                                          'tos': 'on'})
        self.failUnless(form.is_valid())

    def test_registration_form_unique_email(self):
        """
        Test that ``RegistrationFormUniqueEmail`` validates uniqueness
        of email addresses.

        """
        # Create a user so we can verify that duplicate addresses
        # aren't permitted.
        User.objects.create_user('alice', 'alice@example.com', 'secret')

        form = forms.RegistrationFormUniqueEmail(data={'username': 'foo',
                                                       'email': 'alice@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['email'],
                         [u"This email address is already in use. Please supply a different email address."])

        form = forms.RegistrationFormUniqueEmail(data={'username': 'foo',
                                                       'email': 'foo@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_no_free_email(self):
        """
        Test that ``RegistrationFormNoFreeEmail`` disallows
        registration with free email addresses.

        """
        base_data = {'username': 'foo',
                     'password1': 'foo',
                     'password2': 'foo'}
        for domain in forms.RegistrationFormNoFreeEmail.bad_domains:
            invalid_data = base_data.copy()
            invalid_data['email'] = u"foo@%s" % domain
            form = forms.RegistrationFormNoFreeEmail(data=invalid_data)
            self.failIf(form.is_valid())
            self.assertEqual(form.errors['email'],
                             [u"Registration using free email addresses is prohibited. Please supply a different email address."])

        base_data['email'] = 'foo@example.com'
        form = forms.RegistrationFormNoFreeEmail(data=base_data)
        self.failUnless(form.is_valid())

########NEW FILE########
__FILENAME__ = models
import datetime
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core import management
from django.test import TestCase
from django.utils.hashcompat import sha_constructor

from registration.models import RegistrationProfile


class RegistrationModelTests(TestCase):
    """
    Test the model and manager used in the default backend.
    
    """
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}
    
    def setUp(self):
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_profile_creation(self):
        """
        Creating a registration profile for a user populates the
        profile with the correct user and a SHA1 hash to use as
        activation key.
        
        """
        new_user = User.objects.create_user(**self.user_info)
        profile = RegistrationProfile.objects.create_profile(new_user)

        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(profile.user.id, new_user.id)
        self.failUnless(re.match('^[a-f0-9]{40}$', profile.activation_key))
        self.assertEqual(unicode(profile),
                         "Registration information for alice")

    def test_activation_email(self):
        """
        ``RegistrationProfile.send_activation_email`` sends an
        email.
        
        """
        new_user = User.objects.create_user(**self.user_info)
        profile = RegistrationProfile.objects.create_profile(new_user)
        profile.send_activation_email(Site.objects.get_current())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_info['email']])

    def test_user_creation(self):
        """
        Creating a new user populates the correct data, and sets the
        user's account inactive.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        self.assertEqual(new_user.username, 'alice')
        self.assertEqual(new_user.email, 'alice@example.com')
        self.failUnless(new_user.check_password('swordfish'))
        self.failIf(new_user.is_active)

    def test_user_creation_email(self):
        """
        By default, creating a new user sends an activation email.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_creation_no_email(self):
        """
        Passing ``send_email=False`` when creating a new user will not
        send an activation email.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    send_email=False,
                                                                    **self.user_info)
        self.assertEqual(len(mail.outbox), 0)

    def test_unexpired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``False``
        within the activation window.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        self.failIf(profile.activation_key_expired())

    def test_expired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``True``
        outside the activation window.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()
        profile = RegistrationProfile.objects.get(user=new_user)
        self.failUnless(profile.activation_key_expired())

    def test_valid_activation(self):
        """
        Activating a user within the permitted window makes the
        account active, and resets the activation key.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        activated = RegistrationProfile.objects.activate_user(profile.activation_key)

        self.failUnless(isinstance(activated, User))
        self.assertEqual(activated.id, new_user.id)
        self.failUnless(activated.is_active)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.assertEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_expired_activation(self):
        """
        Attempting to activate outside the permitted window does not
        activate the account.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()

        profile = RegistrationProfile.objects.get(user=new_user)
        activated = RegistrationProfile.objects.activate_user(profile.activation_key)

        self.failIf(isinstance(activated, User))
        self.failIf(activated)

        new_user = User.objects.get(username='alice')
        self.failIf(new_user.is_active)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.assertNotEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_activation_invalid_key(self):
        """
        Attempting to activate with a key which is not a SHA1 hash
        fails.
        
        """
        self.failIf(RegistrationProfile.objects.activate_user('foo'))

    def test_activation_already_activated(self):
        """
        Attempting to re-activate an already-activated account fails.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        RegistrationProfile.objects.activate_user(profile.activation_key)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.failIf(RegistrationProfile.objects.activate_user(profile.activation_key))

    def test_activation_nonexistent_key(self):
        """
        Attempting to activate with a non-existent key (i.e., one not
        associated with any account) fails.
        
        """
        # Due to the way activation keys are constructed during
        # registration, this will never be a valid key.
        invalid_key = sha_constructor('foo').hexdigest()
        self.failIf(RegistrationProfile.objects.activate_user(invalid_key))

    def test_expired_user_deletion(self):
        """
        ``RegistrationProfile.objects.delete_expired_users()`` only
        deletes inactive users whose activation window has expired.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        expired_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                        username='bob',
                                                                        password='secret',
                                                                        email='bob@example.com')
        expired_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        expired_user.save()

        RegistrationProfile.objects.delete_expired_users()
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(User.DoesNotExist, User.objects.get, username='bob')

    def test_management_command(self):
        """
        The ``cleanupregistration`` management command properly
        deletes expired accounts.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        expired_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                        username='bob',
                                                                        password='secret',
                                                                        email='bob@example.com')
        expired_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        expired_user.save()

        management.call_command('cleanupregistration')
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(User.DoesNotExist, User.objects.get, username='bob')

########NEW FILE########
__FILENAME__ = urls
"""
URLs used in the unit tests for django-registration.

You should not attempt to use these URLs in any sort of real or
development environment; instead, use
``registration/backends/default/urls.py``. This URLconf includes those
URLs, and also adds several additional URLs which serve no purpose
other than to test that optional keyword arguments are properly
handled.

"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
                       # Test the 'activate' view with custom template
                       # name.
                       url(r'^activate-with-template-name/(?P<activation_key>\w+)/$',
                           activate,
                           {'template_name': 'registration/test_template_name.html',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_template_name'),
                       # Test the 'activate' view with
                       # extra_context_argument.
                       url(r'^activate-extra-context/(?P<activation_key>\w+)/$',
                           activate,
                           {'extra_context': {'foo': 'bar', 'callable': lambda: 'called'},
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_extra_context'),
                       # Test the 'activate' view with success_url argument.
                       url(r'^activate-with-success-url/(?P<activation_key>\w+)/$',
                           activate,
                           {'success_url': 'registration_test_custom_success_url',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_success_url'),
                       # Test the 'register' view with custom template
                       # name.
                       url(r'^register-with-template-name/$',
                           register,
                           {'template_name': 'registration/test_template_name.html',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_template_name'),
                       # Test the'register' view with extra_context
                       # argument.
                       url(r'^register-extra-context/$',
                           register,
                           {'extra_context': {'foo': 'bar', 'callable': lambda: 'called'},
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_extra_context'),
                       # Test the 'register' view with custom URL for
                       # closed registration.
                       url(r'^register-with-disallowed-url/$',
                           register,
                           {'disallowed_url': 'registration_test_custom_disallowed',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_disallowed_url'),
                       # Set up a pattern which will correspond to the
                       # custom 'disallowed_url' above.
                       url(r'^custom-disallowed/$',
                           direct_to_template,
                           {'template': 'registration/registration_closed.html'},
                           name='registration_test_custom_disallowed'),
                       # Test the 'register' view with custom redirect
                       # on successful registration.
                       url(r'^register-with-success_url/$',
                           register,
                           {'success_url': 'registration_test_custom_success_url',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_success_url'
                           ),
                       # Pattern for custom redirect set above.
                       url(r'^custom-success/$',
                           direct_to_template,
                           {'template': 'registration/test_template_name.html'},
                           name='registration_test_custom_success_url'),
                       (r'', include('registration.backends.default.urls')),
                       )

########NEW FILE########
__FILENAME__ = views
import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from registration import forms
from registration.models import RegistrationProfile


class RegistrationViewTests(TestCase):
    """
    Test the registration views.

    """
    urls = 'registration.tests.urls'

    def setUp(self):
        """
        Set ``REGISTRATION_BACKEND`` to the default backend, and store
        the original value to be restored later.

        """
        self.old_backend = getattr(settings, 'REGISTRATION_BACKEND', None)
        settings.REGISTRATION_BACKEND = 'registration.backends.default.DefaultBackend'
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        """
        Restore the original value of ``REGISTRATION_BACKEND``.

        """
        settings.REGISTRATION_BACKEND = self.old_backend
        settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_registration_view_initial(self):
        """
        A ``GET`` to the ``register`` view uses the appropriate
        template and populates the registration form into the context.

        """
        response = self.client.get(reverse('registration_register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'registration/registration_form.html')
        self.failUnless(isinstance(response.context['form'],
                                   forms.RegistrationForm))

    def test_registration_view_success(self):
        """
        A ``POST`` to the ``register`` view with valid data properly
        creates a new user and issues a redirect.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response,
                             'http://testserver%s' % reverse('registration_complete'))
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_view_failure(self):
        """
        A ``POST`` to the ``register`` view with invalid data does not
        create a user, and displays appropriate error messages.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'bob',
                                          'email': 'bobe@example.com',
                                          'password1': 'foo',
                                          'password2': 'bar'})
        self.assertEqual(response.status_code, 200)
        self.failIf(response.context['form'].is_valid())
        self.assertFormError(response, 'form', field=None,
                             errors=u"The two password fields didn't match.")
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_view_closed(self):
        """
        Any attempt to access the ``register`` view when registration
        is closed fails and redirects.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_disallowed')

        response = self.client.get(reverse('registration_register'))
        self.assertRedirects(response, closed_redirect)

        # Even if valid data is posted, it still shouldn't work.
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, closed_redirect)
        self.assertEqual(RegistrationProfile.objects.count(), 0)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_template_name(self):
        """
        Passing ``template_name`` to the ``register`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_register_template_name'))
        self.assertTemplateUsed(response,
                                'registration/test_template_name.html')

    def test_registration_extra_context(self):
        """
        Passing ``extra_context`` to the ``register`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_register_extra_context'))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')

    def test_registration_disallowed_url(self):
        """
        Passing ``disallowed_url`` to the ``register`` view will
        result in a redirect to that URL when registration is closed.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_test_custom_disallowed')

        response = self.client.get(reverse('registration_test_register_disallowed_url'))
        self.assertRedirects(response, closed_redirect)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_success_url(self):
        """
        Passing ``success_url`` to the ``register`` view will result
        in a redirect to that URL when registration is successful.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        response = self.client.post(reverse('registration_test_register_success_url'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, success_redirect)

    def test_valid_activation(self):
        """
        Test that the ``activate`` view properly handles a valid
        activation (in this case, based on the default backend's
        activation window).

        """
        success_redirect = 'http://testserver%s' % reverse('registration_activation_complete')
        
        # First, register an account.
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        self.failUnless(User.objects.get(username='alice').is_active)

    def test_invalid_activation(self):
        """
        Test that the ``activate`` view properly handles an invalid
        activation (in this case, based on the default backend's
        activation window).

        """
        # Register an account and reset its date_joined to be outside
        # the activation window.
        self.client.post(reverse('registration_register'),
                         data={'username': 'bob',
                               'email': 'bob@example.com',
                               'password1': 'secret',
                               'password2': 'secret'})
        expired_user = User.objects.get(username='bob')
        expired_user.date_joined = expired_user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_user.save()

        expired_profile = RegistrationProfile.objects.get(user=expired_user)
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': expired_profile.activation_key}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['activation_key'],
                         expired_profile.activation_key)
        self.failIf(User.objects.get(username='bob').is_active)

    def test_activation_success_url(self):
        """
        Passing ``success_url`` to the ``activate`` view and
        successfully activating will result in that URL being used for
        the redirect.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_test_activate_success_url',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        
    def test_activation_template_name(self):
        """
        Passing ``template_name`` to the ``activate`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_activate_template_name',
                                   kwargs={'activation_key': 'foo'}))
        self.assertTemplateUsed(response, 'registration/test_template_name.html')

    def test_activation_extra_context(self):
        """
        Passing ``extra_context`` to the ``activate`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_activate_extra_context',
                                           kwargs={'activation_key': 'foo'}))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')

########NEW FILE########
__FILENAME__ = urls
"""
Backwards-compatible URLconf for existing django-registration
installs; this allows the standard ``include('registration.urls')`` to
continue working, but that usage is deprecated and will be removed for
django-registration 1.0. For new installs, use
``include('registration.backends.default.urls')``.

"""

import warnings

warnings.warn("include('registration.urls') is deprecated; use include('registration.backends.default.urls') instead.",
              PendingDeprecationWarning)

from registration.backends.default.urls import *

########NEW FILE########
__FILENAME__ = views
"""
Views which allow users to create and activate accounts.

"""


from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from registration.backends import get_backend


def activate(request, backend,
             template_name='registration/activate.html',
             success_url=None, extra_context=None, **kwargs):
    """
    Activate a user's account.

    The actual activation of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    the backend's ``activate()`` method will be called, passing any
    keyword arguments captured from the URL, and will be assumed to
    return a ``User`` if activation was successful, or a value which
    evaluates to ``False`` in boolean context if not.

    Upon successful activation, the backend's
    ``post_activation_redirect()`` method will be called, passing the
    ``HttpRequest`` and the activated ``User`` to determine the URL to
    redirect the user to. To override this, pass the argument
    ``success_url`` (see below).

    On unsuccessful activation, will render the template
    ``registration/activate.html`` to display an error message; to
    override thise, pass the argument ``template_name`` (see below).

    **Arguments**

    ``backend``
        The dotted Python import path to the backend class to
        use. Required.

    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context. Optional.

    ``success_url``
        The name of a URL pattern to redirect to on successful
        acivation. This is optional; if not specified, this will be
        obtained by calling the backend's
        ``post_activation_redirect()`` method.
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``registration/activate.html``.

    ``\*\*kwargs``
        Any keyword arguments captured from the URL, such as an
        activation key, which will be passed to the backend's
        ``activate()`` method.
    
    **Context:**
    
    The context will be populated from the keyword arguments captured
    in the URL, and any extra variables supplied in the
    ``extra_context`` argument (see above).
    
    **Template:**
    
    registration/activate.html or ``template_name`` keyword argument.
    
    """
    backend = get_backend(backend)
    account = backend.activate(request, **kwargs)

    if account:
        if success_url is None:
            to, args, kwargs = backend.post_activation_redirect(request, account)
            return redirect(to, *args, **kwargs)
        else:
            return redirect(success_url)

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              kwargs,
                              context_instance=context)


def register(request, backend, success_url=None, form_class=None,
             disallowed_url='registration_disallowed',
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register an account.

    The actual registration of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    it will be used as follows:

    1. The backend's ``registration_allowed()`` method will be called,
       passing the ``HttpRequest``, to determine whether registration
       of an account is to be allowed; if not, a redirect is issued to
       the view corresponding to the named URL pattern
       ``registration_disallowed``. To override this, see the list of
       optional arguments for this view (below).

    2. The form to use for account registration will be obtained by
       calling the backend's ``get_form_class()`` method, passing the
       ``HttpRequest``. To override this, see the list of optional
       arguments for this view (below).

    3. If valid, the form's ``cleaned_data`` will be passed (as
       keyword arguments, and along with the ``HttpRequest``) to the
       backend's ``register()`` method, which should return the new
       ``User`` object.

    4. Upon successful registration, the backend's
       ``post_registration_redirect()`` method will be called, passing
       the ``HttpRequest`` and the new ``User``, to determine the URL
       to redirect the user to. To override this, see the list of
       optional arguments for this view (below).
    
    **Required arguments**
    
    None.
    
    **Optional arguments**

    ``backend``
        The dotted Python import path to the backend class to use.

    ``disallowed_url``
        URL to redirect to if registration is not permitted for the
        current ``HttpRequest``. Must be a value which can legally be
        passed to ``django.shortcuts.redirect``. If not supplied, this
        will be whatever URL corresponds to the named URL pattern
        ``registration_disallowed``.
    
    ``form_class``
        The form class to use for registration. If not supplied, this
        will be retrieved from the registration backend.
    
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.

    ``success_url``
        URL to redirect to after successful registration. Must be a
        value which can legally be passed to
        ``django.shortcuts.redirect``. If not supplied, this will be
        retrieved from the registration backend.
    
    ``template_name``
        A custom template to use. If not supplied, this will default
        to ``registration/registration_form.html``.
    
    **Context:**
    
    ``form``
        The registration form.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/registration_form.html or ``template_name`` keyword
    argument.
    
    """
    backend = get_backend(backend)
    if not backend.registration_allowed(request):
        return redirect(disallowed_url)
    if form_class is None:
        form_class = backend.get_form_class(request)

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = backend.register(request, **form.cleaned_data)
            if success_url is None:
                to, args, kwargs = backend.post_registration_redirect(request, new_user)
                return redirect(to, *args, **kwargs)
            else:
                return redirect(success_url)
    else:
        form = form_class()
    
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              { 'form': form },
                              context_instance=context)

########NEW FILE########
__FILENAME__ = admin
from models import Route, RouteStage
from django.contrib.gis import admin
from django.core.urlresolvers import reverse

from reversion.admin import VersionAdmin

class RouteStageInline(admin.TabularInline):
    model = RouteStage 
    extra = 1 
    ordering = ['stage__display_name']

class RouteAdmin(admin.OSMGeoAdmin,VersionAdmin):
    ordering = ['city','display_name']
    list_display = ('display_name', 'route_view_link', 'types', 'city',  'start', 'end', 'has_unmapped_stages')

    def has_unmapped_stages(self, obj):
        for s in obj.stages.all():
            if not s.location:
                return True
        return False
    has_unmapped_stages.boolean = True

    def route_view_link(self, obj):
        return "<a href='%s'>View Link</a>" % reverse('show-route', args=[obj.city, obj.slug])

    route_view_link.allow_tags = True
    route_view_link.short_description = "Link to Site"

    inlines = (RouteStageInline, )

    prepopulated_fields = {"slug": ("display_name",)}

admin.site.register(Route, RouteAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Route'
        db.create_table('routes_route', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(default='', max_length=64, db_index=True)),
            ('mtc_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('types', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('start', self.gf('django.db.models.fields.related.ForeignKey')(related_name='start_for_routes', to=orm['stages.Stage'])),
            ('end', self.gf('django.db.models.fields.related.ForeignKey')(related_name='end_for_routes', to=orm['stages.Stage'])),
            ('time', self.gf('django.db.models.fields.FloatField')()),
            ('fare', self.gf('django.db.models.fields.FloatField')()),
            ('type', self.gf('django.db.models.fields.CharField')(default='B', max_length=1)),
        ))
        db.send_create_signal('routes', ['Route'])

        # Adding model 'RouteStage'
        db.create_table('routes_routestage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('route', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['routes.Route'])),
            ('stage', self.gf('django.db.models.fields.related.ForeignKey')(related_name='routelinks', to=orm['stages.Stage'])),
            ('sequence', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('routes', ['RouteStage'])


    def backwards(self, orm):
        
        # Deleting model 'Route'
        db.delete_table('routes_route')

        # Deleting model 'RouteStage'
        db.delete_table('routes_routestage')


    models = {
        'routes.route': {
            'Meta': {'object_name': 'Route'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'end': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'end_for_routes'", 'to': "orm['stages.Stage']"}),
            'fare': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '64', 'db_index': 'True'}),
            'stages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['stages.Stage']", 'through': "orm['routes.RouteStage']", 'symmetrical': 'False'}),
            'start': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_for_routes'", 'to': "orm['stages.Stage']"}),
            'time': ('django.db.models.fields.FloatField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'B'", 'max_length': '1'}),
            'types': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'routes.routestage': {
            'Meta': {'object_name': 'RouteStage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'route': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['routes.Route']"}),
            'sequence': ('django.db.models.fields.IntegerField', [], {}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'routelinks'", 'to': "orm['stages.Stage']"})
        },
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'softlinks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['stages.Stage']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['routes']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_route_city
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Route.city'
        db.add_column('routes_route', 'city', self.gf('django.db.models.fields.CharField')(default='chennai', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Route.city'
        db.delete_column('routes_route', 'city')


    models = {
        'routes.route': {
            'Meta': {'object_name': 'Route'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'end': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'end_for_routes'", 'to': "orm['stages.Stage']"}),
            'fare': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '64', 'db_index': 'True'}),
            'stages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['stages.Stage']", 'through': "orm['routes.RouteStage']", 'symmetrical': 'False'}),
            'start': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_for_routes'", 'to': "orm['stages.Stage']"}),
            'time': ('django.db.models.fields.FloatField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'B'", 'max_length': '1'}),
            'types': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'routes.routestage': {
            'Meta': {'object_name': 'RouteStage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'route': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['routes.Route']"}),
            'sequence': ('django.db.models.fields.IntegerField', [], {}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'routelinks'", 'to': "orm['stages.Stage']"})
        },
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'softlinks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['stages.Stage']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['routes']

########NEW FILE########
__FILENAME__ = 0003_changedMTCRouteTypesNotation
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

MTC_TYPE_MIGRATION_MAP = {
    'M': 'MSVC',
    'O': 'ORD',
    'D': 'DLX',
    'X': 'EXP',
    'N': 'NGT',
    'LSS N': 'LSS,NGT',
    'M N': 'MSVC,NGT',
    'X N': 'EXP,NGT',
}

MTC_TYPE_MIGRATION_REVERSE_MAP = {
    'MSVC': 'M',
    'ORD': 'O',
    'DLX': 'D',
    'EXP': 'X',
    'NGT': 'N',
}

class Migration(DataMigration):

    def forwards(self, orm):
        for r in orm.Route.objects.filter(city__contains='chennai'):
            type_tags = [ tag.strip() for tag in r.types.split(',')]
            new_type_tags = []
            for type_tag in type_tags:
                try:
                    new_type_tags.append(MTC_TYPE_MIGRATION_MAP[type_tag])
                except KeyError:
                    new_type_tags.append(type_tag)
            r.types = ','.join(new_type_tags)
            r.save()

    def backwards(self, orm):
        for r in orm.Route.objects.filter(city__contains='chennai'):
            type_tags = [ tag.strip() for tag in r.types.split(',')]
            new_type_tags = []
            for type_tag in type_tags:
                try:
                    new_type_tags.append(MTC_TYPE_MIGRATION_REVERSE_MAP[type_tag])
                except KeyError:
                    new_type_tags.append(type_tag)
            r.types = ','.join(new_type_tags)
            r.save()

    models = {
        'routes.route': {
            'Meta': {'object_name': 'Route'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'end': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'end_for_routes'", 'to': "orm['stages.Stage']"}),
            'fare': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '64', 'db_index': 'True'}),
            'stages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['stages.Stage']", 'through': "orm['routes.RouteStage']", 'symmetrical': 'False'}),
            'start': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_for_routes'", 'to': "orm['stages.Stage']"}),
            'time': ('django.db.models.fields.FloatField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'B'", 'max_length': '1'}),
            'types': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'routes.routestage': {
            'Meta': {'object_name': 'RouteStage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'route': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['routes.Route']"}),
            'sequence': ('django.db.models.fields.IntegerField', [], {}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'routelinks'", 'to': "orm['stages.Stage']"})
        },
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'softlinks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['stages.Stage']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['routes']

########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models
from django.template.defaultfilters import slugify

ROUTE_TYPE_CHOICES = (
    ('T', 'Train'),
    ('B', 'Bus'),
    )
    
ROUTE_TYPE_MAPPING = {
        'DLX': 'Deluxe',
        'AC': 'Air Conditioned',
        'EXP': 'Express',
        'NGT': 'Night Service',
        'MSVC': 'M Service',
        'ORD': 'Ordinary',
        'LSS': 'Limited Stop Service',
        'VAJ': 'Vajra',
        'BIAS': 'BIAS - Vayu Vajra',
        'B10': 'Big 10',
        }
class Route(models.Model):
    display_name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, default='')
    mtc_name = models.CharField(max_length=64)
    types = models.CharField(max_length=64)
    start = models.ForeignKey('stages.Stage', related_name='start_for_routes')
    end = models.ForeignKey('stages.Stage', related_name='end_for_routes')
    stages = models.ManyToManyField('stages.Stage', through="RouteStage")
    time = models.FloatField()
    fare = models.FloatField()
    type = models.CharField(max_length=1, choices=ROUTE_TYPE_CHOICES, default='B')
    city = models.CharField(max_length=255)

    class Meta:
       ordering = ['slug',]
    def __unicode__(self):
        return self.display_name

class RouteStage(models.Model):
    route = models.ForeignKey(Route)
    stage = models.ForeignKey('stages.Stage', related_name='routelinks')
    sequence = models.IntegerField()

    def __unicode__(self):
        return (str)(self.route)+'|'+(str)(self.sequence)+'.'+(str)(self.stage)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('routes.views',        
                       url(r'^route/(?P<name>[\w\s-]+)/$', 'show_route', name='show-route'),        
                       url(r'^unmapped/routes', 'show_unmapped_routes'),
                       url(r'^routes/type/(?P<type>\w+)/$', 'show_routes_with_type'),
                       )

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, Http404
from routes.models import *
from django.views.generic.simple import direct_to_template
from django.shortcuts import get_object_or_404

def show_route(request, city, name):
    try:									
       r = Route.objects.filter(city=city).get(slug=slugify(name))
    except Route.DoesNotExist:
       raise Http404
    return direct_to_template   (
            request, 
            'routes/show_route.html', 
            {
                'route':r,
                'stages':r.stages.order_by('routelinks__sequence'),
                'city': city
                })

def show_unmapped_routes(request, city):
    unmapped = Route.objects.filter(city=city).filter(stages__location=None).distinct()
    return direct_to_template(request, 'routes/show_unmapped_routes.html',
            { 'city': city, 'unmapped_routes':unmapped})

def show_routes_with_type(request, city, type):
    routes = Route.objects.filter(city=city).filter(types__contains=type)
    return direct_to_template(request, "routes/show_routes_with_type.html",
            {"routes": routes, 'city': city,  "type": ROUTE_TYPE_MAPPING[type]})

########NEW FILE########
__FILENAME__ = a_star
import marshal
import os
import sys
from datetime import datetime
from django.conf import settings
from math import *

def setup_environment():
   PARENT_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
   ROOT_DIR = os.path.normpath(os.path.join(PARENT_DIR,'../'))
   PARENT_ROOT_DIR = os.path.normpath(os.path.join(ROOT_DIR,'../'))
   sys.path.append(PARENT_DIR)
   sys.path.append(ROOT_DIR)
   sys.path.append(PARENT_ROOT_DIR)
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_environment()
from stages.models import Stage

H = marshal.load(open(os.path.join(settings.ROOT_DIR, 'distancegraph'),'rb'))
G = marshal.load(open(os.path.join(settings.ROOT_DIR, 'adjacencygraph'),'rb'))

came_from = {}                    # A linked list structure that remembers the path built
# DM = Multiplier of Distance when computing heuristic
# 'change overs is minimized' < DM < 'distance is minimized'
DM = 1
# IM = Multiplier of Importance when computing heuristic
# 'Changeover can be any stage' < IM < 'Important stages are preferred for changeovers'
IM = 0.0005
# RM = Multiplier of Route_Count when computing heuristic
# 'Naive routing' < RM < 'Stages that are strongly connected are preferred'
RM = 0.0005
  
def get_heuristic(start_stage, end_stage):
   if not H[start_stage].has_key(end_stage):
      return 100000 # Some large value, ideally Infinity
   elif not G[start_stage].has_key(end_stage):
      route_count = 0
   else:
      route_count = G[start_stage][end_stage]
   dist = H[start_stage][end_stage]
   heuristic = DM*dist - IM*(Stage.objects.get(pk=start_stage).importance) - RM*route_count
   return heuristic   

def get_distance(stage1,stage2):
   if not H[stage1].has_key(stage2):
      return 100000 # Some large value, ideally Infinity
   return H[stage1][stage2]

def A_star(start, goal):
   closedset = []                 # The set of nodes already evaluated.     
   openset = [start]              # The set of tentative nodes to be evaluated.
   g_score = {}                   # Distance from start along optimal path.
   h_score = {}                   # Heuristic distance to goal.
   f_score = {}                   # Estimated total distance from start to goal through y.
   g_score[start] = 0 
   h_score[start] = get_heuristic(start,goal)     
   f_score[start] = h_score[start]
   while openset:
      #Finding the node in openset having the lowest f_score[] value
      x = openset[0]
      for stage_id in openset:
         if f_score[x] > f_score[stage_id]:
            x = stage_id            
      if x == goal:
         path = []
         current_node = goal
         while current_node != start:
            path.append(current_node)
            current_node = came_from[current_node]
         for s in path:
            H[s]
         path.append(start)
         path.reverse()   
         return path
         
      openset.remove(x)
      closedset.append(x)
         
      for y in G[x]:
         if y in closedset:
            continue
         tentative_g_score = g_score[x] + get_distance(x,y) 

         if y not in openset:
            openset.append(y)
            tentative_is_better = True
         elif tentative_g_score < g_score[y]:
            tentative_is_better = True
         else:
            tentative_is_better = False

         if tentative_is_better == True:
            came_from[y] = x
            g_score[y] = tentative_g_score
            h_score[y] = get_heuristic(y, goal)
            f_score[y] = g_score[y] + h_score[y] 
   return None

if __name__ == "__main__":
   setup_environment()
   from stages.models import Stage
   G = marshal.load(open(os.path.join(settings.ROOT_DIR,'adjacencygraph'),'rb'))
   H = marshal.load(open(os.path.join(settings.ROOT_DIR,'distancegraph'),'rb'))
   path = A_star(int(sys.argv[1]),int(sys.argv[2]))
   print [Stage.objects.get(pk=sid) for sid in path]

########NEW FILE########
__FILENAME__ = dijkstra
# Dijkstra's algorithm for shortest paths
# David Eppstein, UC Irvine, 4 April 2002

# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/117228
from priodict import priorityDictionary

G = {}

def Dijkstra(G,start,end=None,weighted=True):
    """
    Find shortest paths from the start vertex to all
    vertices nearer than or equal to the end.

    The input graph G is assumed to have the following
    representation: A vertex can be any object that can
    be used as an index into a dictionary.  G is a
    dictionary, indexed by vertices.  For any vertex v,
    G[v] is itself a dictionary, indexed by the neighbors
    of v.  For any edge v->w, G[v][w] is the length of
    the edge.  This is related to the representation in
    <http://www.python.org/doc/essays/graphs.html>
    where Guido van Rossum suggests representing graphs
    as dictionaries mapping vertices to lists of neighbors,
    however dictionaries of edges have many advantages
    over lists: they can store extra information (here,
    the lengths), they support fast existence tests,
    and they allow easy modification of the graph by edge
    insertion and removal.  Such modifications are not
    needed here but are important in other graph algorithms.
    Since dictionaries obey iterator protocol, a graph
    represented as described here could be handed without
    modification to an algorithm using Guido's representation.

    Of course, G and G[v] need not be Python dict objects;
    they can be any other object that obeys dict protocol,
    for instance a wrapper in which vertices are URLs
    and a call to G[v] loads the web page and finds its links.
    
    The output is a pair (D,P) where D[v] is the distance
    from start to v and P[v] is the predecessor of v along
    the shortest path from s to v.
    
    Dijkstra's algorithm is only guaranteed to work correctly
    when all edge lengths are positive. This code does not
    verify this property for all edges (only the edges seen
    before the end vertex is reached), but will correctly
    compute shortest paths even for some graphs with negative
    edges, and will raise an exception if it discovers that
    a negative edge has caused it to make a mistake.
    """

    D = {}  # dictionary of final distances
    P = {}  # dictionary of predecessors
    Q = priorityDictionary()   # est.dist. of non-final vert.
    Q[start] = 0
    
    for v in Q:
        D[v] = Q[v]
        if v == end: break

        for w in G[v]:
            if weighted:
                vwLength = D[v] + G[v][w]
            else:
                vwLength = D[v] + 1
            if w in D:
                if vwLength < D[w]:
                    raise ValueError, \
  "Dijkstra: found better path to already-final vertex"
            elif w not in Q or vwLength < Q[w]:
                Q[w] = vwLength
                P[w] = v
    
    return (D,P)
            
def shortestPath(G,start,end,weighted=True):
    """
    Find a single shortest path from the given start vertex
    to the given end vertex.
    The input has the same conventions as Dijkstra().
    The output is a list of the vertices in order along
    the shortest path.
    """

    D,P = Dijkstra(G,start,end,weighted)
    Path = []
    while 1:
        Path.append(end)
        if end == start: break
        end = P[end]
    Path.reverse()
    return Path
    
def shortest_route(from_, to):
    import marshal

    G = marshal.load(open('cache/graph', 'rb'))
    
    route_path = []

    path = shortestPath(G, from_, to, weighted=True)

    if len(path) > 2:
        path2 = shortestPath(G, from_, to, weighted=False)

        if len(path2) < len(path):
            path = path2
    
    for i in range(0, len(path) - 1):
        route_path.append((path[i], path[i+1]))
        
    return route_path

cursor = None
routes = None

def routes_between(a, b):
    x = cursor.execute("SELECT route_id FROM route_stop " \
            "WHERE stop_id = %s AND route_id IN " \
            "(SELECT route_id FROM route_stop WHERE stop_id = %s)", (a, b))
    
    return [row[0] for row in cursor.fetchall()]

def test():
    import marshal
    
    G = marshal.load(open('cache/graph', 'rb'))

    #print shortestPath(G, 153, 358)
    for i in range(100, 200, 10):
        for j in range(300, 500, 10):
            path = shortestPath(G, i, j, weighted=True)
            path2 = shortestPath(G, i, j, weighted=False)

            print "%d, %d" % (len(path), len(path2))

    #print routes_between(153, 152), routes_between(152,  358)

if __name__ == "__main__":
    import sys
    sys.path.append('')
    import MySQLdb
    import config

    conn = MySQLdb.connect(user=config.db.user, passwd=config.db.password, \
                            db=config.db.db)
    cursor = conn.cursor()

    import cProfile
    cProfile.run("test()")

########NEW FILE########
__FILENAME__ = priodict
# Priority dictionary using binary heaps
# David Eppstein, UC Irvine, 8 Mar 2002

from __future__ import generators

class priorityDictionary(dict):
    def __init__(self):
        '''Initialize priorityDictionary by creating binary heap
of pairs (value,key).  Note that changing or removing a dict entry will
not remove the old pair from the heap until it is found by smallest() or
until the heap is rebuilt.'''
        self.__heap = []
        dict.__init__(self)

    def smallest(self):
        '''Find smallest item after removing deleted items from heap.'''
        if len(self) == 0:
            raise IndexError, "smallest of empty priorityDictionary"
        heap = self.__heap
        while heap[0][1] not in self or self[heap[0][1]] != heap[0][0]:
            lastItem = heap.pop()
            insertionPoint = 0
            while 1:
                smallChild = 2*insertionPoint+1
                if smallChild+1 < len(heap) and \
                        heap[smallChild] > heap[smallChild+1]:
                    smallChild += 1
                if smallChild >= len(heap) or lastItem <= heap[smallChild]:
                    heap[insertionPoint] = lastItem
                    break
                heap[insertionPoint] = heap[smallChild]
                insertionPoint = smallChild
        return heap[0][1]
    
    def __iter__(self):
        '''Create destructive sorted iterator of priorityDictionary.'''
        def iterfn():
            while len(self) > 0:
                x = self.smallest()
                yield x
                del self[x]
        return iterfn()
    
    def __setitem__(self,key,val):
        '''Change value stored in dictionary and add corresponding
pair to heap.  Rebuilds the heap if the number of deleted items grows
too large, to avoid memory leakage.'''
        dict.__setitem__(self,key,val)
        heap = self.__heap
        if len(heap) > 2 * len(self):
            self.__heap = [(v,k) for k,v in self.iteritems()]
            self.__heap.sort()  # builtin sort likely faster than O(n) heapify
        else:
            newPair = (val,key)
            insertionPoint = len(heap)
            heap.append(None)
            while insertionPoint > 0 and \
                    newPair < heap[(insertionPoint-1)//2]:
                heap[insertionPoint] = heap[(insertionPoint-1)//2]
                insertionPoint = (insertionPoint-1)//2
            heap[insertionPoint] = newPair
    
    def setdefault(self,key,val):
        '''Reimplement setdefault to call our customized __setitem__.'''
        if key not in self:
            self[key] = val
        return self[key]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('routing.views',
        (r'^(?P<start>\d+)/(?P<end>\d+)/$', 'show_shortest_path'),
        )

########NEW FILE########
__FILENAME__ = views
from stages.models import *
from routes.models import *
from django.views.generic.simple import direct_to_template
from django.http import HttpResponse
import marshal

import os

from dijkstra import shortestPath
from a_star import A_star

class ChangeOver:
    def __init__(self, start_stage, end_stage, routes):
        self.start_stage = start_stage
        self.end_stage = end_stage
        self.routes = routes

def soft_routes_between(start, end):
    return Route.objects.filter(stages__id__in=[s.id for s in start.softlinks.all()]).filter(stages__id__in=[s.id for s in end.softlinks.all()])

def direct_routes_between(start, end):
    return Route.objects.filter(stages__id=start.id).filter(stages__id=end.id)  

def find_distance(path):
    distance = 0
    for i in range(1,len(path)):
        distance = distance + H[path[i-1]][path[i]]
    return distance

def sort_route(route):
    return 
        

def show_shortest_path(request, city, start, end):
    path = A_star(int(start), int(end))
    if not path:
        return HttpResponse("Path not found")
    stages = [Stage.objects.get(id=sid) for sid in path]
    changeovers = []
    for i in xrange(0,len(stages) - 1):
        startStage = stages[i]
        endStage = stages[i+1]
        rc = ChangeOver(
            start_stage = startStage,
            end_stage = endStage,
            routes=direct_routes_between(startStage, endStage))
        changeovers.append(rc)

    return direct_to_template(request, "show_shortest_path.html",
                              {'changeovers': changeovers,
                               'city': city, 
                               'start_stage':Stage.objects.get(id=start),
                               'end_stage':Stage.objects.get(id=end)})

########NEW FILE########
__FILENAME__ = calculateimportance
import os,sys

def setup_environment():
    pathname = os.path.dirname(sys.argv[0])
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '..')))
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../..')))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

if __name__ == "__main__":
   setup_environment()
   from wtfimb.stages.models import Stage
   from wtfimb.routes.models import Route
   for stage in Stage.objects.all():
      importance = stage.routelinks.count()
      importance = importance + stage.start_for_routes.count()*4
      importance = importance + stage.end_for_routes.count()*4
      if stage.is_terminus:
         importance = importance * 2
      stage.importance = importance
      stage.save()

########NEW FILE########
__FILENAME__ = processing_excel
from __init__ import *

if __name__ == "__main__":
   import marshal
   from stages.models import Stage
   cg = marshal.load(open('../citygraph','r'))
   nj = set([stage_id for stage_id in cg.keys() if len(cg[stage_id]) <= 2]) # Non-junction stops
   j = set([stage_id for stage_id in cg.keys() if len(cg[stage_id]) > 2]) # Junction stops
   t = set([stage.id for stage in Stage.objects.filter(city='chennai') if stage.start_for_routes.count() + stage.end_for_routes.count() > 0]) # Terminal stops
   nt = set([stage.id for stage in Stage.objects.filter(city='chennai') if stage.start_for_routes.count() + stage.end_for_routes.count() == 0]) # Non-terminal stops
   shortlist = j | (nj & t) # stops that will make it to the worksheet
   hitlist = nj & nt # stops that will be hunted down
   # Remove all the non-terminal non-junction stops and re-wire citygraph
   # Assuming cg has consistent data for both directions of travel
   for prey in hitlist:
      if len(cg[prey]) == 1:
         del cg[cg[prey].keys()[0]][prey]
      else: # if len(cg[prey]) == 2:
         left = cg[prey].keys()[0]
         if left not in cg:
            raise Exception("left %d not in cg" % left)
         right = cg[prey].keys()[1]
         if right not in cg:
            raise Exception("right %d not in cg" % right)
         if left not in cg[right]:
            cg[left][right] = cg[right][left] = [cg[left][prey][0],# cg[left][prey]==cg[prey][right]
                              cg[left][prey][1] + cg[prey][right][1]] # Adding the distance
         else:
            cg[left][right][0] += cg[left][prey][0]
            cg[right][left][0] = cg[left][right][0]
      del cg[prey]
   shortlisted_stages = Stage.objects.filter(id__in=shortlist)

   print 'j =', len(j)
   print 't =', len(t)
   print 'nt =', len(nt)
   print 'nj =', len(nj)
   print 'jt =', len(j & t)
   print 'jnt =', len(j & nt)
   print 'njt =', len(nj & t)
   print 'njnt =', len(nj & nt)

   from xlwt import *
   from django.db.models import Count
   wb = Workbook()
   heading_style = easyxf("font: bold on; align: wrap on, vert center, horiz center")

   # STAGES WORKSHEET
   ws_stages = wb.add_sheet("stages")
   ws_stages.write(0, 0, "ID", heading_style)
   ws_stages.write(0, 1, "STAGE", heading_style)
   ws_stages.write(0, 2, "LAT", heading_style)
   ws_stages.write(0, 3, "LON", heading_style)
   ws_stages.write(0, 4, "TERMINAL_SERVICES", heading_style)
   ws_stages.write(0, 5, "TOTAL_SERVICES", heading_style)
   i = 0
   for stage in shortlisted_stages.annotate(total_services=Count('routelinks')).order_by('-total_services'):
      i += 1
      ws_stages.write(i, 0, stage.id)
      ws_stages.write(i, 1, stage.display_name)
      if stage.location:
         ws_stages.write(i, 2, stage.location.y)
         ws_stages.write(i, 3, stage.location.x)
      else:
         ws_stages.write(i, 2, 0)
         ws_stages.write(i, 3, 0)
      ws_stages.write(i, 4, stage.start_for_routes.count() + stage.end_for_routes.count())
      ws_stages.write(i, 5, stage.total_services)

   # ROUTES WORKSHEET
   from routes.models import Route
   qs_routes = Route.objects.filter(city='chennai')
   ws_routes = wb.add_sheet("routes")
   ws_routes.write(0, 0, "ID", heading_style)
   ws_routes.write(0, 1, "ROUTE", heading_style)
   ws_routes.write(0, 2, "TYPE", heading_style)
   ws_routes.write(0, 3, "STAGES ARRAY", heading_style)
   i = 0
   for route in qs_routes.order_by('id'):
      for service_type in route.types.split(','):
         i += 1
         ws_routes.write(i, 0, route.id) # FIXME: Ids are not unique because of service types
         ws_routes.write(i, 1, route.display_name)
         ws_routes.write(i, 2, service_type)
         j = 2
         for routestage in route.routestage_set.order_by('sequence'):
            if routestage.stage_id not in shortlist:
               continue
            j += 1
            ws_routes.write(i, j, routestage.stage_id)

   # SEGMENTS WORKSHEET
   ws_segments = wb.add_sheet("segments")
   ws_segments.write(0, 0, "ID", heading_style)
   ws_segments.write(0, 1, "SEGMENT", heading_style)
   ws_segments.write(0, 2, "STAGE_A", heading_style)
   ws_segments.write(0, 3, "STAGE_B", heading_style)
   ws_segments.write(0, 4, "STAGE_A_TERMINAL_ROUTES", heading_style)
   ws_segments.write(0, 5, "STAGE_B_TERMINAL_ROUTES", heading_style)
   ws_segments.write(0, 6, "ROUTES ARRAY")
   i = 0
   for src in cg.keys():
      src_stage = Stage.objects.get(id=src)
      for dest in cg[src].keys():
         if src > dest: continue # Guess writing only one direction of the segment is enough
         dest_stage = Stage.objects.get(id=dest)
         i += 1
         ws_segments.write(i, 0, i)
         ws_segments.write(i, 1, "%s - %s" % (src_stage.display_name, dest_stage.display_name))
         ws_segments.write(i, 2, src)
         ws_segments.write(i, 3, dest)
         ws_segments.write(i, 4, src_stage.start_for_routes.count() + src_stage.end_for_routes.count())
         ws_segments.write(i, 5, dest_stage.start_for_routes.count() + dest_stage.end_for_routes.count())
         j = 5
         for route in Route.objects.filter(stages=src).filter(stages=dest).order_by('id'):
            j += 1
            ws_segments.write(i, j, route.id)
   wb.save('processing_input.xls')

########NEW FILE########
__FILENAME__ = swap_stages
import os
import sys
def setup_env():
   pathname = os.path.dirname(sys.argv[0])
   sys.path.append(os.path.abspath(pathname))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '..')))
   sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../..')))
   os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_env()

def copy_stage(dest, src):
   dest.display_name = src.display_name
   dest.location = src.location
   dest.mtc_name = src.mtc_name
   dest.is_terminus = src.is_terminus
   dest.city = src.city
   dest.save()
   for rl in src.routelinks.all():
      rl.stage = dest
      rl.save()

   for sr in src.start_for_routes.all():
      sr.start = dest
      sr.save()

   for er in src.end_for_routes.all():
      er.end = dest
      er.save()

from stages.models import Stage
if len(sys.argv) != 3:
   print "Usage: python %s <stageid1> <stageid2>" % sys.argv[0]

st1 = Stage.objects.get(id=int(sys.argv[1]))
st2 = Stage.objects.get(id=int(sys.argv[2]))

temp = Stage()
temp.display_name = 'Delete me'
temp.city = 'wonderland'
temp.save()

copy_stage(temp, st1)
copy_stage(st1, st2)
copy_stage(st2, temp)
temp.delete()

########NEW FILE########
__FILENAME__ = updateadjacencygraph
import marshal
import os
import sys
from datetime import datetime
from math import *

def setup_environment():
    pathname = os.path.dirname(sys.argv[0])
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '..')))
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../..')))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

def update_adjacency_graph():
   adjacencygraph = {}
   from stages.models import Stage
   from routes.models import Route
   for src in Stage.objects.order_by('id'):
      if not adjacencygraph.has_key(src.id):
         adjacencygraph[src.id] = {}
      for adj in Stage.objects.filter(route__in=src.route_set.all()).filter(id__gt=src.id).distinct():
         if not adjacencygraph.has_key(adj.id):
            adjacencygraph[adj.id] = {}
         adjacencygraph[src.id][adj.id] = adjacencygraph[adj.id][src.id] = Route.objects.filter(stages__id=src.id).filter(stages__id=adj.id).count()
   marshal.dump(adjacencygraph, open("../adjacencygraph", "wb"))

if __name__ == "__main__":
    setup_environment()
    starttime = datetime.now()
    update_adjacency_graph()
    timedelta = datetime.now() - starttime
    print 'Executed in %d seconds'%timedelta.seconds

########NEW FILE########
__FILENAME__ = updatecitygraph
from __init__ import *
import marshal
from stages.models import Stage
from routes.models import Route

def get_distance(sid1, sid2):
   s1 = Stage.objects.get(id=sid1)
   s2 = Stage.objects.get(id=sid2)
   if s1.location is None or s2.location is None:
      return None
   return round(s1.location.distance(s2.location) * 111.195101192, 2) # distance in degrees * (pi / 180) * Radius of earth(6371.01)

def update_city_graph():
   citygraph = {}
   for city in ['chennai']:
      for route in Route.objects.filter(city=city):
         prev_rs = None
         for rs in route.routestage_set.order_by('sequence'):
            if not rs.stage_id in citygraph:
               citygraph[rs.stage_id] = {}
            if prev_rs is None:
               prev_rs = rs
               continue
            if not prev_rs.stage_id in citygraph[rs.stage_id]:
               dist = get_distance(prev_rs.stage_id, rs.stage_id)
               citygraph[rs.stage_id][prev_rs.stage_id] = [1, dist]
               citygraph[prev_rs.stage_id][rs.stage_id] = [1, dist]
            else:
               citygraph[rs.stage_id][prev_rs.stage_id][0] += 1
               citygraph[prev_rs.stage_id][rs.stage_id][0] += 1
   marshal.dump(citygraph, open(os.path.join(ROOT_DIR,"citygraph"), "wb"))

if __name__ == "__main__":
    update_city_graph()

########NEW FILE########
__FILENAME__ = updatedistancegraph
import marshal
import os
import sys
from datetime import datetime
from math import *

def setup_environment():
    pathname = os.path.dirname(sys.argv[0])
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '..')))
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../..')))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

setup_environment()
from stages.models import Stage

def update_distance_graph():
   distancegraph = {}
   for stage in Stage.objects.all():
      distancegraph[stage.id] = {}
      distancegraph[stage.id][stage.id] = 0
   for src in Stage.objects.all():
      if src.location is None:
         continue
      for adj in Stage.objects.filter(id__gt=src.id).distinct():
         if adj.location:
            distancegraph[src.id][adj.id] = distancegraph[adj.id][src.id] = src.location.distance(adj.location)*111.195101192 # distance in degrees * (pi / 180) * Radius of earth(6371.01)
   marshal.dump(distancegraph, open("../distancegraph", "wb"))

if __name__ == "__main__":
    setup_environment()
    starttime = datetime.now()
    print 'Updatedistancegraph started at', starttime
    update_distance_graph()
    timedelta = datetime.now() - starttime
    print 'Executed in %d seconds'%timedelta.seconds

########NEW FILE########
__FILENAME__ = settings
# Django settings for wtfimb project.
import os.path
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

ROOT_DIR = os.path.dirname(__file__)

import localsettings

DEBUG = localsettings.DEBUG
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS


DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = localsettings.DATABASE_NAME             # Or path to database file if using sqlite3.
DATABASE_USER = localsettings.DATABASE_USER             # Not used with sqlite3.
DATABASE_PASSWORD = localsettings.DATABASE_PASSWORD         # Not used with sqlite3.
DATABASE_HOST = localsettings.DATABASE_HOST             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = localsettings.DATABASE_PORT             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Asia/Calcutta'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOT_DIR, 'static')
MOBILE_MEDIA_ROOT = os.path.join(ROOT_DIR, 'static_mobile')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static'
MOBILE_MEDIA_URL = '/static_mobile'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin-media/'
MOBILE_ADMIN_MEDIA_PREFIX = '/static_mobile/admin-media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = localsettings.SECRET_KEY

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
        'django.core.context_processors.auth',
        'django.core.context_processors.debug',
        'django.core.context_processors.i18n',
        'django.core.context_processors.media',
        'django.core.context_processors.request',
        'django_authopenid.context_processors.authopenid',
        )

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_authopenid.middleware.OpenIDMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',

)

ROOT_URLCONF = 'wtfimb.urls'
ACCOUNT_ACTIVATION_DAYS = 10
OPENID_SREG = {
    "required": ['fullname', 'country']
}

TEMPLATE_DIRS = (
        os.path.join(ROOT_DIR, 'templates'),
)
LOGIN_URL = '/account/signin'
LOGOUT_URL = '/account/signout'
LOGIN_REDIRECT_URL = '/'

ACCOUNT_ACTIVATION_DAYS = 30

OPENID_SREG = {
    "required": ['fullname', 'country']
}


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.gis',

    'wtfimb.routing',
    'wtfimb.home',
    'wtfimb.stages',
    'wtfimb.routes',
    'wtfimb.api',
    'wtfimb.janitor',
    
    'registration',
    'django_authopenid',
    'south',
    'reversion',
    'django_extensions',
)

GRAPH_CACHE = os.path.join(ROOT_DIR, 'distancegraph')

# Email Settings

EMAIL_HOST = localsettings.EMAIL_HOST

DEFAULT_FROM_EMAIL = 'no-reply@busroutes.in'

# Caching
CACHE_BACKEND = localsettings.CACHE_BACKEND


########NEW FILE########
__FILENAME__ = admin
from models import Stage
from django.contrib.gis import admin
from reversion.admin import VersionAdmin
from routes.models import RouteStage
from django.core.urlresolvers import reverse

class RouteStageInline(admin.TabularInline):
    model = RouteStage 
    extra = 1 
    ordering = ['stage__display_name']

class StageAdmin(admin.OSMGeoAdmin,VersionAdmin):
    list_display = ('display_name',
                    'view_stage_link',
                    'city',
                    'location', 
                    )
    ordering = ['city', 'display_name']
    def view_stage_link(self, obj):
        return "<a href='%s'>View</a>" % reverse('show-stage', args=[obj.city, obj.id])

    view_stage_link.allow_tags = True
    view_stage_link.short_description = "Link to Site"

    inlines = (RouteStageInline, )

    search_fields = ['display_name']


admin.site.register(Stage, StageAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms

class EditStageForm(forms.Form):
    latitude = forms.FloatField()
    longitude = forms.FloatField()


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Stage'
        db.create_table('stages_stage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('latitude', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('longitude', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('location', self.gf('django.contrib.gis.db.models.fields.PointField')(null=True, blank=True)),
            ('mtc_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('importance', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('is_terminus', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('stages', ['Stage'])


    def backwards(self, orm):
        
        # Deleting model 'Stage'
        db.delete_table('stages_stage')


    models = {
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stages']

########NEW FILE########
__FILENAME__ = 0002_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding M2M table for field softlinks on 'Stage'
        db.create_table('stages_stage_softlinks', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_stage', models.ForeignKey(orm['stages.stage'], null=False)),
            ('to_stage', models.ForeignKey(orm['stages.stage'], null=False))
        ))
        db.create_unique('stages_stage_softlinks', ['from_stage_id', 'to_stage_id'])


    def backwards(self, orm):
        
        # Removing M2M table for field softlinks on 'Stage'
        db.delete_table('stages_stage_softlinks')


    models = {
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'softlinks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['stages.Stage']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stages']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_stage_city
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Stage.city'
        db.add_column('stages_stage', 'city', self.gf('django.db.models.fields.CharField')(default='chennai', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Stage.city'
        db.delete_column('stages_stage', 'city')


    models = {
        'stages.stage': {
            'Meta': {'object_name': 'Stage'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'is_terminus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mtc_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'softlinks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['stages.Stage']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stages']

########NEW FILE########
__FILENAME__ = models
from django.contrib.gis.db import models

class Stage(models.Model):
    display_name = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location = models.PointField(null=True, blank=True)
    mtc_name = models.CharField(max_length=255, null=True, blank=True)
    importance = models.FloatField(null=True, blank=True)
    is_terminus = models.BooleanField(default=False)
    softlinks = models.ManyToManyField('stages.Stage', null=True, blank=True)
    city = models.CharField(max_length=255)
    
    objects = models.GeoManager()
    
    class Meta:
        ordering = ['display_name',]
    def __unicode__(self):
        return self.display_name

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('stages.views',
                       url(r'^stage/(?P<id>\d+)/$', 'show_stage', name='show-stage'),
                       url(r'^unmapped/stages', 'show_unmapped_stages'),
                       url(r'^mapped/stages', 'show_mapped_stages'),
        )

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse,HttpResponseRedirect, Http404

from models import *
from django.views.generic.simple import direct_to_template
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404

from forms import EditStageForm

def show_stage(request, city, id):
    if request.method == 'POST':
        form = EditStageForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            s = Stage.objects.get(id=id)
            s.location = Point(cd['longitude'], cd['latitude'])
            s.save()
        return HttpResponseRedirect('.')
    else:
        s = get_object_or_404(Stage, id=id)
        if s.city != city:
            raise Http404
        if s.location!=None:
            form = EditStageForm(
                initial = {'latitude': s.location.y,
                           'longitude': s.location.x}
            )
        else:
            form = EditStageForm()
        default_map = {'zoom':12}
        if city == "chennai":
            default_map["lat"] = 13.0456;
            default_map["lon"] = 80.232;
        elif city == "bangalore":
            default_map["lat"] = 12.9832;
            default_map["lon"] = 77.5915;
        elif city == "delhi":
            default_map["lat"] = 28.6038;
            default_map["lon"] = 77.2134;
        else:
            default_map["lat"] = 13.0456;
            default_map["lon"] = 80.232;
        nearby_stages = Stage.objects.filter(city=city).filter(location__distance_lte=(s.location, D(km=2))).exclude(pk=s.id)
        return direct_to_template(request, 'stages/show_stage.html', {'form':form, 'city': city, 'default_map': default_map, 'stage':s, 'nearby_stages':nearby_stages})

def show_unmapped_stages(request, city):
    unmapped = Stage.objects.filter(city=city).filter(location=None)
    return direct_to_template(request,"stages/show_unmapped_stages.html", 
            { 'city': city, 'unmapped_stages':unmapped})

def show_mapped_stages(request, city):
    mapped = Stage.objects.filter(city=city).filter(location__isnull=False)
    return direct_to_template(request, "stages/show_mapped_stages.html",
            { 'city': city, 'mapped_stages':mapped})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

from django.views.generic.simple import redirect_to

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
                       (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                        {'document_root': settings.MEDIA_ROOT}),
                       (r'^static_mobile/(?P<path>.*)$', 'django.views.static.serve',
                        {'document_root': settings.MOBILE_MEDIA_ROOT}),
                       url(r'^account/signup/$', 'registration.views.register', {'backend':'registration.backends.default.DefaultBackend' },
    name='registration_register'),
                       (r'^account/', include('django_authopenid.urls')),
                       (r'^account/settings','home.views.settings'),
                       (r'^account/password_change/$', 'django.contrib.auth.views.password_change'),
                       (r'^account/password_change/done/$', 'django.contrib.auth.views.password_change_done'),
                       (r'^admin/', include(admin.site.urls)),
                       (r'^robots.txt$', lambda req: redirect_to(req,'/static/robots.txt')),
                       (r'^(?P<city>\w+)/api/', include('api.urls')),
                       (r'^(?P<city>\w+)/path/', include('routing.urls')),
                       (r'^(?P<city>\w+)/janitor/', include('janitor.urls')),
                       (r'^(?P<city>\w+)/', include('stages.urls')),
                       (r'^(?P<city>\w+)/', include('routes.urls')),
                       (r'^(?P<city>\w+)/$', include('home.urls')),
                       (r'^$', lambda req: redirect_to(req,'/chennai'))
                       #(r'^$', 'home.views.select_city'),
        
)

########NEW FILE########
