__FILENAME__ = server
#!/usr/bin/env python

import os
import sys
import socket
import random
from optparse import OptionParser
from wsgiref.simple_server import make_server

parser = OptionParser(usage="""
    python server.py [options]
    """)

parser.add_option('-i', '--ip', default='0.0.0.0', dest='host',
    help='Specify an ip to listen on (defaults to 0.0.0.0/localhost)'
    )

parser.add_option('-p', '--port', default=8000, dest='port', type='int',
    help='Specify a custom port to run on: eg. 8080'
    )

def print_url(options):
    sys.stderr.write("Listening on %s:%s...\n" % (options.host,options.port))
    sys.stderr.write("To access locally view: http://localhost:%s\n" % options.port)
    remote = "To access remotely view: http://%s" % socket.getfqdn()
    if not options.port == 80:
        remote += ":%s" % options.port
    try:
        remote += "\nor view: http://%s" % socket.gethostbyname(socket.gethostname())
    except: pass # breaks on some wifi networks
    if not options.port == 80:
        remote += ":%s" % options.port
    sys.stderr.write('%s\n' % remote)

def run(process):
    try:
        process.serve_forever()
    except KeyboardInterrupt:
        process.server_close()
        sys.exit(0)

def random_geojson():
    start = '{ "type": "FeatureCollection", "features": ['
    end = ']}'
    feature_template = '''
      { "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [%(lon)s,%(lat)s]},
      "properties": {"feat_id": %(feat_id)d,"size":%(size)d}
      }
    '''
    features = ''
    limit = 20
    for feat_id in xrange(0,limit):
        # random points roughly within oregon
        lat = random.randrange(40,46)
        lon = random.randrange(-130,-115)
        size = random.randrange(2,30)
        features += feature_template % locals()
        if feat_id < limit-1:
            features += ','
    return start + features + end

def application(environ, start_response):
    response_status = "200 OK"
    mime_type = 'text/plain'
    response = random_geojson()
    start_response(response_status,[('Content-Type', mime_type)])
    yield response

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    httpd = make_server(options.host, options.port, application)        
    print_url(options)
    run(httpd)

########NEW FILE########
__FILENAME__ = convert
# -*- coding: utf-8 -*-

import os
import mapnik

# usage:
# python update.py

# download latest osm for bbox
#os.system('wget -O pdx-poi.osm "http://www.overpass-api.de/api/xapi?node[bbox=-122.68732,45.52028,-122.65217,45.53982][amenity=*]"')

# read in with mapnik
ds = mapnik.Datasource(**{'type':'osm','file':'pdx-poi.osm'})

# loop over all features
# and write out a csv file
fs = ds.all_features()
csv_features = []
for feat in fs:
  if feat.has_key('name'):
      json = feat.geometries().to_geojson()
      name = feat['name']
      # work around bug
      if name == True:
          name = ''
      csv_features.append(""""%s",%d,"%s",'%s'""" % (name,feat.id(),feat['amenity'],json))

osm_out = open('pdx-poi.csv','w+')
# write headers
osm_out.write('name,osm_id,amenity,geojson\n')
# write data rows
osm_out.write('\n'.join(csv_features).encode('utf8'))
osm_out.close()

########NEW FILE########
__FILENAME__ = convert
import os
import mapnik

# usage:
# python update.py

# download latest osm for bbox
#os.system('wget -O nacis.osm "http://api.openstreetmap.org/api/0.6/map?bbox=-122.656771,45.529472,-122.652377,45.53208"')

# read in with mapnik
ds = mapnik.Datasource(**{'type':'osm','file':'nacis.osm'})

# loop over all features
# and write out a csv file
fs = ds.all_features()
csv_features = []
for feat in fs:
  if feat.has_key('name'):
      json = feat.geometries().to_geojson()
      name = feat['name']
      # work around bug
      if name == True:
          name = ''
      csv_features.append(""""%s",%d,'%s'""" % (name,feat.id(),json))

osm_out = open('osm.csv','w+')
# write headers
osm_out.write('name,osm_id,geojson\n')
# write data rows
osm_out.write('\n'.join(csv_features))
osm_out.close()

########NEW FILE########
