__FILENAME__ = render_all
#!/usr/bin/python

import fileinput
from math import pi,cos,sin,log,exp,atan
from subprocess import call

DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi

def minmax (a,b,c):
	a = max(a,b)
	a = min(a,c)
	return a

class GoogleProjection:
	def __init__(self,levels=18):
		self.Bc = []
		self.Cc = []
		self.zc = []
		self.Ac = []
		c = 256
		for d in range(0,levels):
			e = c/2;
			self.Bc.append(c/360.0)
			self.Cc.append(c/(2 * pi))
			self.zc.append((e,e))
			self.Ac.append(c)
			c *= 2
				
	def fromLLtoPixel(self,ll,zoom):
		 d = self.zc[zoom]
		 e = round(d[0] + ll[0] * self.Bc[zoom])
		 f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
		 g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
		 return (e,g)
	 
	def fromPixelToLL(self,px,zoom):
		 e = self.zc[zoom]
		 f = (px[0] - e[0])/self.Bc[zoom]
		 g = (px[1] - e[1])/-self.Cc[zoom]
		 h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
		 return (f,h)


import os
from PIL.Image import fromstring, new
from PIL.ImageDraw import Draw
from StringIO import StringIO
from mapnik import *


mapfile = "/home/steve/osm.xml"
tile_dir = '/tmp/tiles/'
maxZoom = 18

gprj = GoogleProjection(maxZoom+1)
m = Map(2 * 256,2 * 256)
load_map(m,mapfile)
prj = Projection("+proj=merc +datum=WGS84")



def dotile(z,x,y):
	x_str = "%s" % x
	y_str = "%s" % y
	z_str = "%s" % z

	p0 = gprj.fromPixelToLL((x * 256, (y+1) * 256),z)
	p1 = gprj.fromPixelToLL(((x+1) * 256, y*  256),z)

	print z,x,y,p0,p1
	# render a new tile and store it on filesystem
	c0 = prj.forward(Coord(p0[0],p0[1]))
	c1 = prj.forward(Coord(p1[0],p1[1]))
			
	bbox = Envelope(c0.x,c0.y,c1.x,c1.y)
	bbox.width(bbox.width() * 2)
	bbox.height(bbox.height() * 2)
	m.zoom_to_box(bbox)

	if not os.path.isdir(tile_dir + z_str):
			os.mkdir(tile_dir + z_str)
	if not os.path.isdir(tile_dir + z_str + '/' + x_str):
		os.mkdir(tile_dir + z_str + '/' + x_str)

	tile_uri = tile_dir + z_str + '/' + x_str + '/' + y_str + '.png'
	im = Image(512, 512)
	render(m, im)
	im = fromstring('RGBA', (512, 512), rawdata(im))
	im = im.crop((128,128,512-128,512-128))
	fh = open(tile_uri,'w+b')
	im.save(fh, 'PNG', quality=100)
	command = "convert  -colors 255 %s %s" % (tile_uri,tile_uri)
	call(command, shell=True)

for line in fileinput.input():
	tile_data = line.rstrip('\n').split(':')
	dotile(eval(tile_data[0]), eval(tile_data[1]), eval(tile_data[2]))



########NEW FILE########
__FILENAME__ = osm2pgsl
#!/opt/python-2_5/bin/python

import sys,xml.sax
from xml.sax.handler import ContentHandler
from cElementTree import Element, SubElement, ElementTree
from optparse import OptionParser

exportTags = [ ("name","varchar(64)"),
               ("place","varchar(32)"),
               ("landuse","varchar(32)"),
               ("leisure","varchar(32)"),
               ("waterway","varchar(32)"),
               ("highway","varchar(32)"),
               ("amenity","varchar(32)"),
               ("tourism","varchar(32)"),
               ("learning","varchar(32)")
               ]
segments = {}
table_name = "planet_osm"

class osm2sql (ContentHandler):
    def __init__(self,fh):
        ContentHandler.__init__(self)
        self.fh = fh
    def startDocument (self):
        self.node = {}
        self.stack = []
    def startElement(self,name,attr):
        if name == 'node':
            self.node[attr["id"]] = (attr["lon"], attr["lat"])
            self.stack.append({'type':'node','id':attr["id"],'tags':{}})
        elif name == 'segment':
            from_node = self.node[attr["from"]]
            to_node   = self.node[attr["to"]]
            segments[attr["id"]] = from_node,to_node
        elif name == 'tag':
            k = attr['k'].replace(":","_").replace(" ","_")
            v = attr['v']
            self.stack.append((k,v))
        elif name == 'way':
            self.stack.append({'type':'way','id':attr["id"],'segs': [],'tags':{}})
        elif name == 'seg':
            self.stack[-1]['segs'].append(attr["id"])
            
    def endElement (self,name):
        if name == 'segment':
            pass
        elif name == 'node':
            node = self.stack.pop()
            osm_id = node['id']
            fields = ",".join(["%s" % f[0] for f in exportTags])
            values = []
            count=0
            for tag in exportTags:
                if tag[0] in node['tags']:
                    values.append("$$%s$$" % node['tags'][tag[0]])
                    count+=1
                else:
                    values.append("$$$$")
                
            if count > 0: # only create POINT feature if node has some tags
                values = ",".join(values)
                #values = values.encode("UTF-8")
                wkt = 'POINT(%s %s)' % (self.node[osm_id])
                sql = "insert into %s (osm_id,%s,way) values (%s,%s,GeomFromText('%s',4326));" % (table_name,fields,osm_id,values,wkt)
                print sql.encode("UTF-8")
                
        elif name == 'tag':
            tag = self.stack.pop()
            if len(self.stack) > 0 :
                if 'type' in self.stack[-1] and ( self.stack[-1]['type'] == 'way' or self.stack[-1]['type'] == 'node') :
                    self.stack[-1]['tags'][tag[0]] = tag[1]
                
        elif name == 'way':
            way = self.stack.pop()
            osm_id = way['id']
            fields = ",".join(["%s" % f[0] for f in exportTags])
            polygon = False
            values = []
            for tag in exportTags:
                if tag[0] in way['tags']:
                    if tag[0] == 'landuse' or tag[0] == 'leisure':
                        polygon = True
                    values.append("$$%s$$" % way['tags'][tag[0]])
                else:
                    values.append("$$$$")
            values = ",".join(values)

            wkt,status = self.WKT(way,polygon)
            if status :
                sql = "insert into %s (osm_id,%s,way) values (%s,%s,GeomFromText('%s',4326));" % (table_name,fields,osm_id,values,wkt)
                print sql.encode("UTF-8")
            else:
                for s in way['segs']:
                    try:
                        from_node,to_node = segments[s]
                        wkt = 'LINESTRING(%s %s,%s %s)' % (from_node[0],from_node[1],to_node[0],to_node[1]) 
                        sql = "insert into %s (osm_id,%s,way) values (%s,%s,GeomFromText('%s',4326));" % (table_name,fields,osm_id,
values,wkt)
                        print sql.encode("UTF-8")
                    except:
                        pass
            
    def WKT(self,way, polygon=False):
        first = True
        wkt = ""

        max = len(way['segs']) * len(way['segs'])
        i = 0
        while way['segs'] and i < max:
            id = way['segs'].pop()
            i+=1
            if id in segments:
                from_node,to_node = segments[id]
                x0 = from_node[0]
                y0 = from_node[1]
                x1 = to_node[0]
                y1 = to_node[1]
            
                if first:
                    first = False
                    start_x = x0
                    start_y = y0
                    end_x = x1
                    end_y = y1
                    wkt = '%s %s,%s %s' % (x0,y0,x1,y1)
                else:
                    if (start_x == x0) and (start_y == y0) :
                        start_x = x1
                        start_y = y1
                        wkt ='%s %s,' % (x1,y1) + wkt
                    elif (start_x == x1) and (start_y == y1) :
                        start_x = x0
                        start_y = y0
                        wkt ='%s %s,' % (x0,y0) + wkt
                    elif (end_x == x0) and (end_y == y0) :
                        end_x = x1
                        end_y = y1
                        wkt += ',%s %s' % (x1,y1)
                    elif (end_x == x1) and (end_y == y1) :
                        end_x = x0
                        end_y = y0
                        wkt += ',%s %s' % (x0,y0)
                    else:
                        way['segs'].insert(0,id)
            
        if polygon:
            wkt = wkt + ",%s %s" % (start_x,start_y)
            wkt = 'POLYGON ((%s))' % wkt
        else:
            wkt = 'LINESTRING (%s)' % wkt
        if way['segs']:
            return wkt,False
        else:
            return wkt,True
            
if __name__ == "__main__":
    parser = osm2sql(sys.stdout)
    fields = ",".join(["%s %s" % (tag[0],tag[1]) for tag in exportTags])
    print "drop table %s ;" % table_name
    print "create table %s ( osm_id int4,%s );" % (table_name,fields)
    print "select AddGeometryColumn('%s', 'way', 4326, 'GEOMETRY', 2 );" % table_name
    print "begin;"
    xml.sax.parse(sys.stdin,parser)
    print "commit;"
    print "vacuum analyze %s;" % table_name

########NEW FILE########
__FILENAME__ = generate_image
#!/usr/bin/env python

try:
    import mapnik2 as mapnik
except:
    import mapnik

import sys, os

# Set up projections
# spherical mercator (most common target map projection of osm data imported with osm2pgsql)
merc = mapnik.Projection('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over')

# long/lat in degrees, aka ESPG:4326 and "WGS 84" 
longlat = mapnik.Projection('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
# can also be constructed as:
#longlat = mapnik.Projection('+init=epsg:4326')

# ensure minimum mapnik version
if not hasattr(mapnik,'mapnik_version') and not mapnik.mapnik_version() >= 600:
    raise SystemExit('This script requires Mapnik >=0.6.0)')

if __name__ == "__main__":
    try:
        mapfile = os.environ['MAPNIK_MAP_FILE']
    except KeyError:
        mapfile = "osm.xml"
    
    map_uri = "image.png"

    #---------------------------------------------------
    #  Change this to the bounding box you want
    #
    bounds = (-6.5, 49.5, 2.1, 59)
    #---------------------------------------------------

    z = 10
    imgx = 500 * z
    imgy = 1000 * z

    m = mapnik.Map(imgx,imgy)
    mapnik.load_map(m,mapfile)
    
    # ensure the target map projection is mercator
    m.srs = merc.params()

    if hasattr(mapnik,'Box2d'):
        bbox = mapnik.Box2d(*bounds)
    else:
        bbox = mapnik.Envelope(*bounds)

    # Our bounds above are in long/lat, but our map
    # is in spherical mercator, so we need to transform
    # the bounding box to mercator to properly position
    # the Map when we call `zoom_to_box()`
    transform = mapnik.ProjTransform(longlat,merc)
    merc_bbox = transform.forward(bbox)
    
    # Mapnik internally will fix the aspect ratio of the bounding box
    # to match the aspect ratio of the target image width and height
    # This behavior is controlled by setting the `m.aspect_fix_mode`
    # and defaults to GROW_BBOX, but you can also change it to alter
    # the target image size by setting aspect_fix_mode to GROW_CANVAS
    #m.aspect_fix_mode = mapnik.GROW_CANVAS
    # Note: aspect_fix_mode is only available in Mapnik >= 0.6.0
    m.zoom_to_box(merc_bbox)
    
    # render the map to an image
    im = mapnik.Image(imgx,imgy)
    mapnik.render(m, im)
    im.save(map_uri,'png')
    
    sys.stdout.write('output image to %s!\n' % map_uri)
    
    # Note: instead of creating an image, rendering to it, and then 
    # saving, we can also do this in one step like:
    # mapnik.render_to_file(m, map_uri,'png')
    
    # And in Mapnik >= 0.7.0 you can also use `render_to_file()` to output
    # to Cairo supported formats if you have Mapnik built with Cairo support
    # For example, to render to pdf or svg do:
    # mapnik.render_to_file(m, "image.pdf")
    #mapnik.render_to_file(m, "image.svg")
    


########NEW FILE########
__FILENAME__ = generate_tiles
#!/usr/bin/env python
from math import pi,cos,sin,log,exp,atan
from subprocess import call
import sys, os
from Queue import Queue

import threading

try:
    import mapnik2 as mapnik
except:
    import mapnik

DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi

# Default number of rendering threads to spawn, should be roughly equal to number of CPU cores available
NUM_THREADS = 4


def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a

class GoogleProjection:
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
                
    def fromLLtoPixel(self,ll,zoom):
         d = self.zc[zoom]
         e = round(d[0] + ll[0] * self.Bc[zoom])
         f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
         return (e,g)
     
    def fromPixelToLL(self,px,zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)



class RenderThread:
    def __init__(self, tile_dir, mapfile, q, printLock, maxZoom):
        self.tile_dir = tile_dir
        self.q = q
        self.m = mapnik.Map(256, 256)
        self.printLock = printLock
        # Load style XML
        mapnik.load_map(self.m, mapfile, True)
        # Obtain <Map> projection
        self.prj = mapnik.Projection(self.m.srs)
        # Projects between tile pixel co-ordinates and LatLong (EPSG:4326)
        self.tileproj = GoogleProjection(maxZoom+1)


    def render_tile(self, tile_uri, x, y, z):

        # Calculate pixel positions of bottom-left & top-right
        p0 = (x * 256, (y + 1) * 256)
        p1 = ((x + 1) * 256, y * 256)

        # Convert to LatLong (EPSG:4326)
        l0 = self.tileproj.fromPixelToLL(p0, z);
        l1 = self.tileproj.fromPixelToLL(p1, z);

        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = self.prj.forward(mapnik.Coord(l0[0],l0[1]))
        c1 = self.prj.forward(mapnik.Coord(l1[0],l1[1]))

        # Bounding box for the tile
        if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 800:
            bbox = mapnik.Box2d(c0.x,c0.y, c1.x,c1.y)
        else:
            bbox = mapnik.Envelope(c0.x,c0.y, c1.x,c1.y)
        render_size = 256
        self.m.resize(render_size, render_size)
        self.m.zoom_to_box(bbox)
        if(self.m.buffer_size < 128):
            self.m.buffer_size = 128

        # Render image with default Agg renderer
        im = mapnik.Image(render_size, render_size)
        mapnik.render(self.m, im)
        im.save(tile_uri, 'png256')


    def loop(self):
        while True:
            #Fetch a tile from the queue and render it
            r = self.q.get()
            if (r == None):
                self.q.task_done()
                break
            else:
                (name, tile_uri, x, y, z) = r

            exists= ""
            if os.path.isfile(tile_uri):
                exists= "exists"
            else:
                self.render_tile(tile_uri, x, y, z)
            bytes=os.stat(tile_uri)[6]
            empty= ''
            if bytes == 103:
                empty = " Empty Tile "
            self.printLock.acquire()
            print name, ":", z, x, y, exists, empty
            self.printLock.release()
            self.q.task_done()



def render_tiles(bbox, mapfile, tile_dir, minZoom=1,maxZoom=18, name="unknown", num_threads=NUM_THREADS, tms_scheme=False):
    print "render_tiles(",bbox, mapfile, tile_dir, minZoom,maxZoom, name,")"

    # Launch rendering threads
    queue = Queue(32)
    printLock = threading.Lock()
    renderers = {}
    for i in range(num_threads):
        renderer = RenderThread(tile_dir, mapfile, queue, printLock, maxZoom)
        render_thread = threading.Thread(target=renderer.loop)
        render_thread.start()
        #print "Started render thread %s" % render_thread.getName()
        renderers[i] = render_thread

    if not os.path.isdir(tile_dir):
         os.mkdir(tile_dir)

    gprj = GoogleProjection(maxZoom+1) 

    ll0 = (bbox[0],bbox[3])
    ll1 = (bbox[2],bbox[1])

    for z in range(minZoom,maxZoom + 1):
        px0 = gprj.fromLLtoPixel(ll0,z)
        px1 = gprj.fromLLtoPixel(ll1,z)

        # check if we have directories in place
        zoom = "%s" % z
        if not os.path.isdir(tile_dir + zoom):
            os.mkdir(tile_dir + zoom)
        for x in range(int(px0[0]/256.0),int(px1[0]/256.0)+1):
            # Validate x co-ordinate
            if (x < 0) or (x >= 2**z):
                continue
            # check if we have directories in place
            str_x = "%s" % x
            if not os.path.isdir(tile_dir + zoom + '/' + str_x):
                os.mkdir(tile_dir + zoom + '/' + str_x)
            for y in range(int(px0[1]/256.0),int(px1[1]/256.0)+1):
                # Validate x co-ordinate
                if (y < 0) or (y >= 2**z):
                    continue
                # flip y to match OSGEO TMS spec
                if tms_scheme:
                    str_y = "%s" % ((2**z-1) - y)
                else:
                    str_y = "%s" % y
                tile_uri = tile_dir + zoom + '/' + str_x + '/' + str_y + '.png'
                # Submit tile to be rendered into the queue
                t = (name, tile_uri, x, y, z)
                try:
                    queue.put(t)
                except KeyboardInterrupt:
                    raise SystemExit("Ctrl-c detected, exiting...")

    # Signal render threads to exit by sending empty request to queue
    for i in range(num_threads):
        queue.put(None)
    # wait for pending rendering jobs to complete
    queue.join()
    for i in range(num_threads):
        renderers[i].join()



if __name__ == "__main__":
    home = os.environ['HOME']
    try:
        mapfile = os.environ['MAPNIK_MAP_FILE']
    except KeyError:
        mapfile = home + "/svn.openstreetmap.org/applications/rendering/mapnik/osm-local.xml"
    try:
        tile_dir = os.environ['MAPNIK_TILE_DIR']
    except KeyError:
        tile_dir = home + "/osm/tiles/"

    if not tile_dir.endswith('/'):
        tile_dir = tile_dir + '/'

    #-------------------------------------------------------------------------
    #
    # Change the following for different bounding boxes and zoom levels
    #
    # Start with an overview
    # World
    bbox = (-180.0,-90.0, 180.0,90.0)

    render_tiles(bbox, mapfile, tile_dir, 0, 5, "World")

    minZoom = 10
    maxZoom = 16
    bbox = (-2, 50.0,1.0,52.0)
    render_tiles(bbox, mapfile, tile_dir, minZoom, maxZoom)

    # Muenchen
    bbox = (11.4,48.07, 11.7,48.22)
    render_tiles(bbox, mapfile, tile_dir, 1, 12 , "Muenchen")

    # Muenchen+
    bbox = (11.3,48.01, 12.15,48.44)
    render_tiles(bbox, mapfile, tile_dir, 7, 12 , "Muenchen+")

    # Muenchen++
    bbox = (10.92,47.7, 12.24,48.61)
    render_tiles(bbox, mapfile, tile_dir, 7, 12 , "Muenchen++")

    # Nuernberg
    bbox=(10.903198,49.560441,49.633534,11.038085)
    render_tiles(bbox, mapfile, tile_dir, 10, 16, "Nuernberg")

    # Karlsruhe
    bbox=(8.179113,48.933617,8.489252,49.081707)
    render_tiles(bbox, mapfile, tile_dir, 10, 16, "Karlsruhe")

    # Karlsruhe+
    bbox = (8.3,48.95,8.5,49.05)
    render_tiles(bbox, mapfile, tile_dir, 1, 16, "Karlsruhe+")

    # Augsburg
    bbox = (8.3,48.95,8.5,49.05)
    render_tiles(bbox, mapfile, tile_dir, 1, 16, "Augsburg")

    # Augsburg+
    bbox=(10.773251,48.369594,10.883834,48.438577)
    render_tiles(bbox, mapfile, tile_dir, 10, 14, "Augsburg+")

    # Europe+
    bbox = (1.0,10.0, 20.6,50.0)
    render_tiles(bbox, mapfile, tile_dir, 1, 11 , "Europe+")

########NEW FILE########
__FILENAME__ = generate_tiles_multiprocess
#!/usr/bin/env python
from math import pi,cos,sin,log,exp,atan
from subprocess import call
import sys, os
import multiprocessing

try:
    import mapnik2 as mapnik
except:
    import mapnik

DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi

# Default number of rendering threads to spawn, should be roughly equal to number of CPU cores available
NUM_THREADS = 4


def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a

class GoogleProjection:
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
                
    def fromLLtoPixel(self,ll,zoom):
         d = self.zc[zoom]
         e = round(d[0] + ll[0] * self.Bc[zoom])
         f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
         return (e,g)
     
    def fromPixelToLL(self,px,zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)



class RenderThread:
    def __init__(self, tile_dir, mapfile, q, printLock, maxZoom):
        self.tile_dir = tile_dir
        self.q = q
        self.mapfile = mapfile
        self.maxZoom = maxZoom
        self.printLock = printLock

    def render_tile(self, tile_uri, x, y, z):
        # Calculate pixel positions of bottom-left & top-right
        p0 = (x * 256, (y + 1) * 256)
        p1 = ((x + 1) * 256, y * 256)

        # Convert to LatLong (EPSG:4326)
        l0 = self.tileproj.fromPixelToLL(p0, z);
        l1 = self.tileproj.fromPixelToLL(p1, z);

        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = self.prj.forward(mapnik.Coord(l0[0],l0[1]))
        c1 = self.prj.forward(mapnik.Coord(l1[0],l1[1]))

        # Bounding box for the tile
        if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 800:
            bbox = mapnik.Box2d(c0.x,c0.y, c1.x,c1.y)
        else:
            bbox = mapnik.Envelope(c0.x,c0.y, c1.x,c1.y)
        render_size = 256
        self.m.resize(render_size, render_size)
        self.m.zoom_to_box(bbox)
        if(self.m.buffer_size < 128):
            self.m.buffer_size = 128

        # Render image with default Agg renderer
        im = mapnik.Image(render_size, render_size)
        mapnik.render(self.m, im)
        im.save(tile_uri, 'png256')


    def loop(self):
        
        self.m = mapnik.Map(256, 256)
        # Load style XML
        mapnik.load_map(self.m, self.mapfile, True)
        # Obtain <Map> projection
        self.prj = mapnik.Projection(self.m.srs)
        # Projects between tile pixel co-ordinates and LatLong (EPSG:4326)
        self.tileproj = GoogleProjection(self.maxZoom+1)
                
        while True:
            #Fetch a tile from the queue and render it
            r = self.q.get()
            if (r == None):
                self.q.task_done()
                break
            else:
                (name, tile_uri, x, y, z) = r

            exists= ""
            if os.path.isfile(tile_uri):
                exists= "exists"
            else:
                self.render_tile(tile_uri, x, y, z)
            bytes=os.stat(tile_uri)[6]
            empty= ''
            if bytes == 103:
                empty = " Empty Tile "
            self.printLock.acquire()
            print name, ":", z, x, y, exists, empty
            self.printLock.release()
            self.q.task_done()



def render_tiles(bbox, mapfile, tile_dir, minZoom=1,maxZoom=18, name="unknown", num_threads=NUM_THREADS):
    print "render_tiles(",bbox, mapfile, tile_dir, minZoom,maxZoom, name,")"

    # Launch rendering threads
    queue = multiprocessing.JoinableQueue(32)
    printLock = multiprocessing.Lock()
    renderers = {}
    for i in range(num_threads):
        renderer = RenderThread(tile_dir, mapfile, queue, printLock, maxZoom)
        render_thread = multiprocessing.Process(target=renderer.loop)
        render_thread.start()
        #print "Started render thread %s" % render_thread.getName()
        renderers[i] = render_thread

    if not os.path.isdir(tile_dir):
         os.mkdir(tile_dir)

    gprj = GoogleProjection(maxZoom+1) 

    ll0 = (bbox[0],bbox[3])
    ll1 = (bbox[2],bbox[1])

    for z in range(minZoom,maxZoom + 1):
        px0 = gprj.fromLLtoPixel(ll0,z)
        px1 = gprj.fromLLtoPixel(ll1,z)

        # check if we have directories in place
        zoom = "%s" % z
        if not os.path.isdir(tile_dir + zoom):
            os.mkdir(tile_dir + zoom)
        for x in range(int(px0[0]/256.0),int(px1[0]/256.0)+1):
            # Validate x co-ordinate
            if (x < 0) or (x >= 2**z):
                continue
            # check if we have directories in place
            str_x = "%s" % x
            if not os.path.isdir(tile_dir + zoom + '/' + str_x):
                os.mkdir(tile_dir + zoom + '/' + str_x)
            for y in range(int(px0[1]/256.0),int(px1[1]/256.0)+1):
                # Validate x co-ordinate
                if (y < 0) or (y >= 2**z):
                    continue
                str_y = "%s" % y
                tile_uri = tile_dir + zoom + '/' + str_x + '/' + str_y + '.png'
                # Submit tile to be rendered into the queue
                t = (name, tile_uri, x, y, z)
                queue.put(t)

    # Signal render threads to exit by sending empty request to queue
    for i in range(num_threads):
        queue.put(None)
    # wait for pending rendering jobs to complete
    queue.join()
    for i in range(num_threads):
        renderers[i].join()



if __name__ == "__main__":
	
    home = os.environ['HOME']
    try:
        mapfile = os.environ['MAPNIK_MAP_FILE']
    except KeyError:
        mapfile = home + "/svn.openstreetmap.org/applications/rendering/mapnik/osm-local.xml"
    try:
        tile_dir = os.environ['MAPNIK_TILE_DIR']
    except KeyError:
        tile_dir = home + "/osm/tiles/"

    if not tile_dir.endswith('/'):
        tile_dir = tile_dir + '/'

    #-------------------------------------------------------------------------
    #
    # Change the following for different bounding boxes and zoom levels
    #
    # Start with an overview
    # World
    bbox = (-180.0,-90.0, 180.0,90.0)

    render_tiles(bbox, mapfile, tile_dir, 0, 5, "World")

    minZoom = 10
    maxZoom = 16
    bbox = (-2, 50.0,1.0,52.0)
    render_tiles(bbox, mapfile, tile_dir, minZoom, maxZoom)

    # Muenchen
    bbox = (11.4,48.07, 11.7,48.22)
    render_tiles(bbox, mapfile, tile_dir, 1, 12 , "Muenchen")

    # Muenchen+
    bbox = (11.3,48.01, 12.15,48.44)
    render_tiles(bbox, mapfile, tile_dir, 7, 12 , "Muenchen+")

    # Muenchen++
    bbox = (10.92,47.7, 12.24,48.61)
    render_tiles(bbox, mapfile, tile_dir, 7, 12 , "Muenchen++")

    # Nuernberg
    bbox=(10.903198,49.560441,49.633534,11.038085)
    render_tiles(bbox, mapfile, tile_dir, 10, 16, "Nuernberg")

    # Karlsruhe
    bbox=(8.179113,48.933617,8.489252,49.081707)
    render_tiles(bbox, mapfile, tile_dir, 10, 16, "Karlsruhe")

    # Karlsruhe+
    bbox = (8.3,48.95,8.5,49.05)
    render_tiles(bbox, mapfile, tile_dir, 1, 16, "Karlsruhe+")

    # Augsburg
    bbox = (8.3,48.95,8.5,49.05)
    render_tiles(bbox, mapfile, tile_dir, 1, 16, "Augsburg")

    # Augsburg+
    bbox=(10.773251,48.369594,10.883834,48.438577)
    render_tiles(bbox, mapfile, tile_dir, 10, 14, "Augsburg+")

    # Europe+
    bbox = (1.0,10.0, 20.6,50.0)
    render_tiles(bbox, mapfile, tile_dir, 1, 11 , "Europe+")

########NEW FILE########
__FILENAME__ = generate_xml
#!/usr/bin/env python

import os
import re
import sys
import glob
import optparse
import platform
import tempfile

__version__ = '0.1.0'

REASONABLE_DEFAULTS = {
        'epsg':'900913', # default osm2pgsql import srid
        'world_boundaries':'world_boundaries', # relative path
        'symbols':'symbols', # relative path
        'prefix':'planet_osm', # default osm2pgsql table prefix
        'extent':'-20037508,-19929239,20037508,19929239', # world in merc
        'inc':'inc/*.template', # search path for inc templates to parse
        'estimate_extent':'false',   
        'extent':'-20037508,-19929239,20037508,19929239',   
        }

def color_text(color, text):
    if os.name == 'nt':
        return text
    return "\033[9%sm%s\033[0m" % (color,text)

class Params:
    def __init__(self,params,accept_none):
        self.params = params
        self.accept_none = accept_none
        self.missing = []
    
    def blend_with_env(self,opts):
        d = {}
        
        for p in self.params:
            env_var_name = 'MAPNIK_%s' % p.upper()

            # first pull from passed options...
            if not opts.get(p) is None:
                d[p] = opts[p]

            # then try to pull from environment settings
            elif not os.environ.get(env_var_name) is None:
                d[p] = os.environ[env_var_name]

            # then assign any reasonable default values...
            elif p in REASONABLE_DEFAULTS.keys():
                d[p] = REASONABLE_DEFAULTS[p]
            # if --accept-none is passed then we assume
            # its a paramater that mapnik likely does not need
            # and will ignore if it is an empty string (e.g. db values)
            elif self.accept_none:
                d[p] = ''
            else:
                self.missing.append(p)
        return d

def generate_help_text(var,default):
    if var == 'host':
        return 'Set postgres database host %s' % default
    elif var == 'port':
        return 'Set postgres database host %s' % default
    return "Set value of '%s' %s" % (var,default)
    
def serialize(xml,options):
    try:
        import mapnik
    except:
        try:
            import mapnik2 as mapnik
        except:
            sys.exit(color_text(1,'Error: saving xml requires Mapnik python bindings to be installed'))
    m = mapnik.Map(1,1)
    if options.from_string:
        mapnik.load_map_from_string(m,xml,True)
    else:
        mapnik.load_map(m,xml,True)
    if options.output:
        mapnik.save_map(m,options.output)
    else:
        if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 700:
            print mapnik.save_map_to_string(m)
        else:
            sys.exit(color_text(1,'Minor error: printing XML to stdout requires Mapnik >=0.7.0, please provide a second argument to save the output to a file'))

def validate(params,parser):
    if not os.path.exists(params['world_boundaries']):
        parser.error("Directory '%s' used for param '%s' not found" % (params['world_boundaries'],'world_boundaries'))
    supported_srs = [900913,4326]
    if not int(params['epsg']) in supported_srs:
        parser.error('Sorry only supported projections are: %s' % supported_srs)
    if not params['estimate_extent'] == 'false':
        params['extent'] = ''

# set up parser...
parser = optparse.OptionParser(usage="""%prog [template xml] <output xml> <parameters>

Full help:
 $ %prog -h (or --help for possible options)

Read 'osm.xml' and modify '/inc' files in place, pass dbname and user, accept empty string for other options
 $ %prog --dbname osm --user postgres --accept-none

Read template, save output xml, and pass variables as options
 $ %prog osm.xml my_osm.xml --dbname spain --user postgres --host ''""", version='%prog ' + __version__)


if __name__ == '__main__':

    # custom parse of includes directory if supplied...
    if '--inc' in sys.argv:
        idx = sys.argv.index('--inc')
        if not len(sys.argv) > (idx+1) or '--' in sys.argv[idx+1]:
            parser.error("--inc argument requires a path to a directory as an argument")
        else:
            search_path = os.path.join(sys.argv[idx+1],'*.template')
    else:
        search_path = REASONABLE_DEFAULTS['inc']
    
    inc_dir = os.path.dirname(search_path)
    parser.add_option('--inc', dest='inc', help="Includes dir (default: '%s')" % inc_dir )
    
    parser.add_option('--accept-none', dest='accept_none', action='store_true', help="Interpret lacking value as unneeded")
    
    if not os.path.exists(inc_dir):
        parser.error("The 'inc' path you gave is bogus!")
        
    # get all the includes
    includes = glob.glob(search_path)
    
    if not includes:
        parser.error("Can't find include templates, please provide search path using '--inc' , currently using '%s'" % search_path)

    p = re.compile('.*%\((\w+)\)s.*')
    
    text = ''
    for xml in includes:
        text += file(xml,'rb').read()
    
    # find all variables in template includes
    matches = p.findall(text)
    
    if not matches:
        parser.error(color_text(1,"Can't properly parse out variables in include templates.\nMake sure they are all wrapped like '%(variable)s'"))
    
    # look ahead and build up --help text...
    p = Params(matches,accept_none=False)
    blended = p.blend_with_env({})
    c_opts = []
    for var in matches:
        if not var in c_opts:
            msg = "(default: '%(" + var + ")s')"
            if var in blended:
                default = msg % blended
            else:
                default = ''#msg % {var:'None'}
            help = generate_help_text(var,default)
            parser.add_option('--%s' % var, dest=var,help=generate_help_text(var,default))
            c_opts.append(var)

    # now, actually run the tool...
    (options, args) = parser.parse_args()
    p = Params(matches,options.accept_none)
    blended = p.blend_with_env(options.__dict__)
    
    help_text = "\n\nNote: use --accept-none to pass blank values for other parameters "
    if p.missing:
        parser.error(color_text(1,"\nPlease provide the following parameters values (or set as env variables):\n%s" % ''.join([" --%s 'value' " % v for v in p.missing]) + help_text))
    
    validate(blended,parser)
    
    for xml in includes:
        template = file(xml,'rb')
        new_name = xml.replace('.template','')
        new_file = file(new_name,'wb')
        try:
            new_file.write(template.read() % blended)
        except ValueError, e:
            parser.error(color_text(1,"\n%s (found in %s)" % (e,xml)))
        template.close()
        new_file.close()
        
    options.output = None
    options.from_string = False
    template_xml = None
    # accepting XML as stream...
    if not sys.stdin.isatty():
        template_xml = sys.stdin.read()
        options.from_string = True
        if len(args) > 0:
            options.output = args[0]
    elif len(args) == 0:
        template_xml = None
        options.output = None
    else:
        template_xml = args[0]
        if len(args) > 1:
            options.output = args[1]

    if template_xml:
        serialize(template_xml,options)
    else:
        print 'Include files written successfully! Pass the osm.xml file as an argument if you want to serialize a new version or test reading the XML'

########NEW FILE########
__FILENAME__ = legend
#!/usr/bin/python

"""A simple script to help visualize the Mapnik stylesheet. This file puts
   out poly/line symbols into an HTML file, with their associated filters.
   Not particularly complex at the moment, but a useful visualization tool if
   you're hacking on the osm.xml file. Works against the osm.xml
   at the moment."""

__author__ = "Christopher Schmidt"
__license__ = "Public Domain"


import xml.dom.minidom as m

def run():
    """Parses the osm.xml file, and write an HTML table.""" 
    #doc = m.parse("osm-template.xml")
    doc = m.parse("osm.xml")
    styles = doc.getElementsByTagName("Style")
    for style in styles:
        table_started = False
        for r in style.getElementsByTagName("Rule"):

            filters = r.getElementsByTagName("Filter")
            text = ""
            if len(filters):
                text = filters[0].firstChild.nodeValue

            polys = r.getElementsByTagName("PolygonSymbolizer")     
            poly_text = [] 
            poly_style = {}
            if len(polys):
                css = polys[0].getElementsByTagName("CssParameter")
                for c in css:
                    poly_style[ c.getAttribute("name") ] = c.firstChild.nodeValue

            pfill = r.getElementsByTagName("PolygonPatternSymbolizer")
            if len(pfill):
                pfill = pfill[0]
                poly_style['fill'] = '<img src="symbols/%s" title="%s"/>' % (pfill.getAttribute("file"), pfill.getAttribute("file"))
            for key, value in poly_style.items():
                poly_text.append("%s: %s" % (key, value))
            poly_text = "<br />".join(poly_text)

            lines = r.getElementsByTagName("LineSymbolizer")     
            line_text = [] 
            line_style = {}
            if len(lines):
                css = lines[0].getElementsByTagName("CssParameter")
                for c in css:
                    line_style[ c.getAttribute("name") ] = c.firstChild.nodeValue
                for key, value in line_style.items():
                    line_text.append("%s: %s" % (key, value))
            line_text = "<br />".join(line_text)

            if text and (poly_text or line_text):
                if not table_started:
                    print "<h2>%s</h2>" % style.getAttribute("name").title()
                    print "<table><tr><td>filter</td><td>poly</td><td>stroke</td></tr>"
                    table_started = True
                print "<tr><td>%s</td>" % text
                print "<td style='background-color: %s'>%s</td>" % (poly_style.get('fill', ''),  poly_text)    
                print "<td style='background-color: %s'>%s</td></tr>" % (line_style.get('stroke', ''),  line_text)    
    
        if table_started:
            print "</table>"
if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = render_single_tile
#!/usr/bin/python
#
# render a single tile using mapnik
import math
import sys
try:
  import mapnik2 as mapnik
except:
  import mapnik
        

def TileToMeters(tx, ty, zoom):
  initialResolution = 20037508.342789244 * 2.0 / 256.0
  originShift = 20037508.342789244
  tileSize = 256.0
  zoom2 = (2.0**zoom)
  res = initialResolution / zoom2
  mx = (res*tileSize*(tx+1))-originShift
  my = (res*tileSize*(zoom2-ty))-originShift
  return mx, my

def TileToBBox(x,y,z):
  x1,y1=TileToMeters(x-1,y+1,z)
  x2,y2=TileToMeters(x,y,z) 
  return x1,y1,x2,y2

if __name__ == "__main__":
  if len(sys.argv) != 5:
    sys.stderr.write("usage: render_single_tile.py <stylefile> z x y\n")
    sys.exit(1)
  mapfile = sys.argv[1]
  z=int(sys.argv[2])
  x=int(sys.argv[3])
  y=int(sys.argv[4])

  m = mapnik.Map(256, 256)
  mapnik.load_map(m, mapfile)
  bba=TileToBBox(x,y,z)
  bbox=mapnik.Box2d(bba[0],bba[1],bba[2],bba[3])
  m.zoom_to_box(bbox)
  im = mapnik.Image(256, 256)
  mapnik.render(m, im)
  sys.stdout.write(im.tostring('png'));
  

########NEW FILE########
__FILENAME__ = polytiles
#!/usr/bin/python
# -*- coding: utf-8 -*-

# this file is based on generate_tiles_multiprocess.py
# run it without arguments to see options list

from math import pi,cos,sin,log,exp,atan
from subprocess import call
import sys, os
import mapnik2 as mapnik
import multiprocessing
import psycopg2
from shapely.geometry import Polygon
from shapely.wkb import loads
import ogr
import sqlite3
import getpass
import argparse

DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi
TILE_SIZE = 256


def box(x1,y1,x2,y2):
    return Polygon([(x1,y1), (x2,y1), (x2,y2), (x1,y2)])

def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a

class GoogleProjection:
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
                
    def fromLLtoPixel(self,ll,zoom):
         d = self.zc[zoom]
         e = round(d[0] + ll[0] * self.Bc[zoom])
         f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
         return (e,g)
     
    def fromPixelToLL(self,px,zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)


class ListWriter:
    def __init__(self, f):
        self.f = f

    def __str__(self):
        return "ListWriter({0})".format(self.f.name)

    def write_poly(self, poly):
        self.f.write("BBox: {0}\n".format(poly.bounds))

    def write(self, x, y, z):
        self.f.write("{0}/{1}/{2}\n".format(z,x,y))

    def exists(self, x, y, z):
        return False

    def need_image(self):
        return False

    def multithreading(self):
        return False

    def close(self):
        self.f.close()

class FileWriter:
    def __init__(self, tile_dir):
        self.tile_dir = tile_dir
        if not self.tile_dir.endswith('/'):
            self.tile_dir = self.tile_dir + '/'
        if not os.path.isdir(self.tile_dir):
            os.mkdir(self.tile_dir)

    def __str__(self):
        return "FileWriter({0})".format(self.tile_dir)

    def write_poly(self, poly):
        pass

    def tile_uri(self, x, y, z):
        return '{0}{1}/{2}/{3}.png'.format(self.tile_dir, z, x, y)

    def exists(self, x, y, z):
        return os.path.isfile(self.tile_uri(x, y, z))

    def write(self, x, y, z, image):
        uri = self.tile_uri(x, y, z)
        try:
            os.makedirs(os.path.dirname(uri))
        except OSError:
            pass
        image.save(uri, 'png256')

    def need_image(self):
        return True

    def multithreading(self):
        return True

    def close(self):
        pass

class TMSWriter(FileWriter):
    def tile_uri(self, x, y, z):
        return '{0}{1}/{2}/{3}.png'.format(self.tile_dir, z, x, 2**z-1-y)

    def __str__(self):
        return "TMSWriter({0})".format(self.tile_dir)

# https://github.com/mapbox/mbutil/blob/master/mbutil/util.py
class MBTilesWriter:
    def __init__(self, filename, setname, overlay=False, version=1, description=None):
        self.filename = filename
        if not self.filename.endswith('.mbtiles'):
            self.filename = self.filename + '.mbtiles'
        self.con = sqlite3.connect(self.filename)
        self.cur = self.con.cursor()
        self.cur.execute("""PRAGMA synchronous=0""")
        self.cur.execute("""PRAGMA locking_mode=EXCLUSIVE""")
        #self.cur.execute("""PRAGMA journal_mode=TRUNCATE""")
        self.cur.execute("""create table if not exists tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);""")
        self.cur.execute("""create table if not exists metadata (name text, value text);""")
        self.cur.execute("""create unique index if not exists name on metadata (name);""")
        self.cur.execute("""create unique index if not exists tile_index on tiles (zoom_level, tile_column, tile_row);""")
        metadata = [ ('name', setname), ('format', 'png'), ('type', 'overlay' if overlay else 'baselayer'), ('version', version) ]
        if description:
            metadata.append(('description', description))
        for name, value in metadata:
            self.cur.execute('insert or replace into metadata (name, value) values (?, ?)', (name, value))

    def __str__(self):
        return "MBTilesWriter({0})".format(self.filename)

    def write_poly(self, poly):
        bbox = poly.bounds
        self.cur.execute("""select value from metadata where name='bounds'""")
        result = self.cur.fetchone
        if result:
            b = result['value'].split(',')
            oldbbox = box(int(b[0]), int(b[1]), int(b[2]), int(b[3]))
            bbox = bbox.union(oldbbox).bounds
        self.cur.execute("""insert or replace into metadata (name, value) values ('bounds', ?)""", ','.join(bbox))

    def exists(self, x, y, z):
        self.cur.execute("""select 1 from tiles where zoom_level = ? and tile_column = ? and tile_row = ?""", (z, x, 2**z-1-y))
        return self.cur.fetchone()

    def write(self, x, y, z, image):
        self.cur.execute("""insert or replace into tiles (zoom_level, tile_column, tile_row, tile_data) values (?, ?, ?, ?);""", (z, x, 2**z-1-y, sqlite3.Binary(image.tostring('png256'))))

    def need_image(self):
        return True

    def multithreading(self):
        return False

    def close(self):
        self.cur.execute("""ANALYZE;""")
        self.cur.execute("""VACUUM;""")
        self.cur.close()
        self.con.close()


# todo: make queue-based writer
class ThreadedWriter:
    def __init__(self, writer):
        self.writer = writer
        self.queue = multiprocessing.Queue(10)

    def __str__(self):
        return "Threaded{0}".format(self.writer)

    def write_poly(self, poly):
        pass

    def exists(self, x, y, z):
        pass

    def write(self, x, y, z, image):
        pass

    def need_image(self):
        return writer.need_image()

    def multithreading(self):
        return True

    def close(self):
        writer.close()


class RenderThread:
    def __init__(self, writer, mapfile, q, printLock, verbose=True):
        self.writer = writer
        self.q = q
	self.mapfile = mapfile
        self.printLock = printLock
        self.verbose = verbose

    def render_tile(self, x, y, z):
        # Calculate pixel positions of bottom-left & top-right
        p0 = (x * TILE_SIZE, (y + 1) * TILE_SIZE)
        p1 = ((x + 1) * TILE_SIZE, y * TILE_SIZE)

        # Convert to LatLong (EPSG:4326)
        l0 = self.tileproj.fromPixelToLL(p0, z);
        l1 = self.tileproj.fromPixelToLL(p1, z);

        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = self.prj.forward(mapnik.Coord(l0[0],l0[1]))
        c1 = self.prj.forward(mapnik.Coord(l1[0],l1[1]))

        # Bounding box for the tile
        if hasattr(mapnik,'mapnik_version') and mapnik.mapnik_version() >= 800:
            bbox = mapnik.Box2d(c0.x,c0.y, c1.x,c1.y)
        else:
            bbox = mapnik.Envelope(c0.x,c0.y, c1.x,c1.y)
        render_size = TILE_SIZE
        self.m.resize(render_size, render_size)
        self.m.zoom_to_box(bbox)
        self.m.buffer_size = 128

        # Render image with default Agg renderer
        im = mapnik.Image(render_size, render_size)
        mapnik.render(self.m, im)
        self.writer.write(x, y, z, im)


    def loop(self):
        self.m = mapnik.Map(TILE_SIZE, TILE_SIZE)
        # Load style XML
        mapnik.load_map(self.m, self.mapfile, True)
        # Obtain <Map> projection
        self.prj = mapnik.Projection(self.m.srs)
        # Projects between tile pixel co-ordinates and LatLong (EPSG:4326)
        self.tileproj = GoogleProjection()

        while True:
            #Fetch a tile from the queue and render it
            r = self.q.get()
            if (r == None):
                self.q.task_done()
                break
            else:
                (x, y, z) = r

            exists= ""
            if self.writer.exists(x, y, z):
                exists= "exists"
            elif self.writer.need_image():
                self.render_tile(x, y, z)
            else:
                self.writer.write(x, y, z)
            empty = ''
            #if os.path.exists(tile_uri):
            #    bytes=os.stat(tile_uri)[6]
            #    empty= ''
            #    if bytes == 103:
            #        empty = " Empty Tile "
            #else:
            #    empty = " Missing "
            if self.verbose:
                self.printLock.acquire()
                print z, x, y, exists, empty
                self.printLock.release()
            self.q.task_done()

class ListGenerator:
    def __init__(self, f):
        self.f = f

    def __str__(self):
        return "ListGenerator({0})".format(self.f.name)

    def generate(self, queue):
        import re
        for line in self.f:
            m = re.search(r"(\d{1,2})\D+(\d+)\D+(\d+)", line)
            if m:
                queue.put((int(m.group(2)), int(m.group(3)), int(m.group(1))))


class PolyGenerator:
    def __init__(self, poly, zooms):
        self.poly = poly
        self.zooms = zooms
        self.zooms.sort()

    def __str__(self):
        return "PolyGenerator({0}, {1})".format(self.poly.bounds, self.zooms)

    def generate(self, queue):
        gprj = GoogleProjection(self.zooms[-1]+1) 

        bbox = self.poly.bounds
        ll0 = (bbox[0], bbox[3])
        ll1 = (bbox[2], bbox[1])

        for z in self.zooms:
            px0 = gprj.fromLLtoPixel(ll0, z)
            px1 = gprj.fromLLtoPixel(ll1, z)

            for x in range(int(px0[0]/float(TILE_SIZE)), int(px1[0]/float(TILE_SIZE))+1):
                # Validate x co-ordinate
                if (x < 0) or (x >= 2**z):
                    continue
                for y in range(int(px0[1]/float(TILE_SIZE)), int(px1[1]/float(TILE_SIZE))+1):
                    # Validate x co-ordinate
                    if (y < 0) or (y >= 2**z):
                        continue

                    # Calculate pixel positions of bottom-left & top-right
                    tt_p0 = (x * TILE_SIZE, (y + 1) * TILE_SIZE)
                    tt_p1 = ((x + 1) * TILE_SIZE, y * TILE_SIZE)

                    # Convert to LatLong (EPSG:4326)
                    tt_l0 = gprj.fromPixelToLL(tt_p0, z);
                    tt_l1 = gprj.fromPixelToLL(tt_p1, z);

                    tt_p = box(tt_l0[0], tt_l1[1], tt_l1[0], tt_l0[1])
                    if not self.poly.intersects(tt_p):
                        continue

                    # Submit tile to be rendered into the queue
                    t = (x, y, z)
		    queue.put(t)


def render_tiles(generator, mapfile, writer, num_threads=1, verbose=True):
    if verbose:
        print "render_tiles(",generator, mapfile, writer, ")"

    # Launch rendering threads
    queue = multiprocessing.JoinableQueue(32 if writer.multithreading() else 0)
    printLock = multiprocessing.Lock()
    renderers = {}
    if writer.multithreading():
        for i in range(num_threads):
            renderer = RenderThread(writer, mapfile, queue, printLock, verbose=verbose)
            render_thread = multiprocessing.Process(target=renderer.loop)
            render_thread.start()
            #print "Started render thread %s" % render_thread.getName()
            renderers[i] = render_thread

    generator.generate(queue)

    if writer.multithreading():
        # Signal render threads to exit by sending empty request to queue
        for i in range(num_threads):
            queue.put(None)
        # wait for pending rendering jobs to complete
        queue.join()
        for i in range(num_threads):
            renderers[i].join()
    else:
        renderer = RenderThread(writer, mapfile, queue, printLock, verbose=verbose)
        queue.put(None)
        renderer.loop()


def poly_parse(fp):
    poly = []
    data = False
    for l in fp:
        l = l.strip()
        if not l: continue
        if l == 'END': break
        if l == '1':
            data = True
            continue
        if not data: continue
        poly.append(map(lambda x: float(x.strip()), l.split()[:2]))
    return poly


def project(geom, from_epsg=900913, to_epsg=4326):
    # source: http://hackmap.blogspot.com/2008/03/ogr-python-projection.html
    to_srs = ogr.osr.SpatialReference()
    to_srs.ImportFromEPSG(to_epsg)

    from_srs = ogr.osr.SpatialReference()
    from_srs.ImportFromEPSG(from_epsg)

    ogr_geom = ogr.CreateGeometryFromWkb(geom.wkb)
    ogr_geom.AssignSpatialReference(from_srs)

    ogr_geom.TransformTo(to_srs)
    return loads(ogr_geom.ExportToWkb())

def read_db(db, osm_id=0):
    # Zero for DB bbox
    cur = db.cursor()
    if osm_id:
        cur.execute("""SELECT way FROM planet_osm_polygon WHERE osm_id = %s;""", (osm_id,))
    else:
        cur.execute("""SELECT ST_ConvexHull(ST_Collect(way)) FROM planet_osm_polygon;""")
    way = cur.fetchone()[0]
    cur.close()
    poly = loads(way.decode('hex'))
    return project(poly)

def read_cities(db, osm_id=0):
    cur = db.cursor()
    if osm_id:
        cur.execute("""SELECT ST_Union(pl.way) FROM planet_osm_polygon pl, planet_osm_polygon b WHERE b.osm_id = %s AND pl.place IN ('town', 'city') AND ST_Area(pl.way) < 500*1000*1000 AND ST_Contains(b.way, pl.way);""", (osm_id,))
    else:
        cur.execute("""SELECT ST_Union(way) FROM planet_osm_polygon WHERE place IN ('town', 'city') AND ST_Area(way) < 500*1000*1000;""")
    result = cur.fetchone()
    poly = loads(result[0].decode('hex')) if result else Polygon()
    if osm_id:
        cur.execute("""SELECT ST_Union(ST_Buffer(p.way, 5000)) FROM planet_osm_point p, planet_osm_polygon b WHERE b.osm_id=%s AND ST_Contains(b.way, p.way) AND p.place IN ('town', 'city') AND NOT EXISTS(SELECT 1 FROM planet_osm_polygon pp WHERE pp.name=p.name AND ST_Contains(pp.way, p.way));""", (osm_id,))
    else:
        cur.execute("""SELECT ST_Union(ST_Buffer(p.way, 5000)) FROM planet_osm_point p WHERE p.place in ('town', 'city') AND NOT EXISTS(SELECT 1 FROM planet_osm_polygon pp WHERE pp.name=p.name AND ST_Contains(pp.way, p.way));""")
    result = cur.fetchone()
    if result:
        poly = poly.union(loads(result[0].decode('hex')))
    return project(poly)


if __name__ == "__main__":
    try:
        mapfile = os.environ['MAPNIK_MAP_FILE']
    except KeyError:
        mapfile = os.getcwd() + '/osm.xml'

    default_user = getpass.getuser()

    parser = argparse.ArgumentParser(description='Generate mapnik tiles for OSM polygon')
    apg_input = parser.add_argument_group('Input')
    apg_input.add_argument("-b", "--bbox", nargs=4, type=float, metavar=('X1', 'Y1', 'X2', 'Y2'), help="generate tiles inside a bounding box")
    apg_input.add_argument('-p', '--poly', type=argparse.FileType('r'), help='use a poly file for area')
    apg_input.add_argument("-a", "--area", type=int, metavar='OSM_ID', help="generate tiles inside an OSM polygon: positive for polygons, negative for relations, 0 for whole database")
    apg_input.add_argument("-c", "--cities", type=int, metavar='OSM_ID', help='generate tiles for all towns inside a polygon')
    apg_input.add_argument('-l', '--list', type=argparse.FileType('r'), metavar='TILES.LST', help='process tile list')
    apg_output = parser.add_argument_group('Output')
    apg_output.add_argument('-t', '--tiledir', metavar='DIR', help='output tiles to directory (default: {0}/tiles)'.format(os.getcwd()))
    apg_output.add_argument('--tms', action='store_true', help='write files in TMS order', default=False)
    apg_output.add_argument('-m', '--mbtiles', help='generate mbtiles file')
    apg_output.add_argument('--name', help='name for mbtiles', default='Test MBTiles')
    apg_output.add_argument('--overlay', action='store_true', help='if this layer is an overlay (for mbtiles metadata)', default=False)
    apg_output.add_argument('-x', '--export', type=argparse.FileType('w'), metavar='TILES.LST', help='save tile list into file')
    apg_output.add_argument('-z', '--zooms', type=int, nargs=2, metavar=('ZMIN', 'ZMAX'), help='range of zoom levels to render (default: 6 12)', default=(6, 12))
    apg_other = parser.add_argument_group('Settings')
    apg_other.add_argument('-s', '--style', help='style file for mapnik (default: {0})'.format(mapfile), default=mapfile)
    apg_other.add_argument('--threads', type=int, metavar='N', help='number of threads (default: 2)', default=2)
    apg_other.add_argument('-q', '--quiet', dest='verbose', action='store_false', help='do not print any information',  default=True)
    apg_db = parser.add_argument_group('Database (for poly/cities)')
    apg_db.add_argument('-d', '--dbname', metavar='DB', help='database (default: gis)', default='gis')
    apg_db.add_argument('--host', help='database host', default='localhost')
    apg_db.add_argument('--port', type=int, help='database port', default='5432')
    apg_db.add_argument('-u', '--user', help='user name for db (default: {0})'.format(default_user), default=default_user)
    apg_db.add_argument('-w', '--password', action='store_true', help='ask for password', default=False)
    options = parser.parse_args()

    # check for required argument
    if options.bbox == None and options.poly == None and options.cities == None and options.list == None and options.area == None:
        parser.print_help()
        sys.exit()

    # writer
    if options.tiledir:
        writer = FileWriter(options.tiledir) if not options.tms else TMSWriter(options.tiledir)
    elif options.mbtiles:
        writer = MBTilesWriter(options.mbtiles, options.name, overlay=options.overlay)
    elif options.export:
        writer = ListWriter(options.export)
    else:
        writer = FileWriter(os.getcwd() + '/tiles') if not options.tms else TMSWriter(os.getcwd() + '/tiles')

    # input and process
    poly = None
    if options.bbox:
        b = options.bbox
        tpoly = box(b[0], b[1], b[2], b[3])
        poly = tpoly if not poly else poly.intersection(tpoly)
    if options.poly:
        tpoly = Polygon(poly_parse(options.poly))
        poly = tpoly if not poly else poly.intersection(tpoly)
    if options.area != None or options.cities != None:
        passwd = ""
        if options.password:
            passwd = getpass.getpass("Please enter your password: ")

        try:
            db = psycopg2.connect(database=options.dbname, user=options.user, password=passwd, host=options.host, port=options.port)
	    if options.area != None:
		tpoly = read_db(db, options.area)
		poly = tpoly if not poly else poly.intersection(tpoly)
	    if options.cities != None:
		tpoly = read_cities(db, options.cities)
		poly = tpoly if not poly else poly.intersection(tpoly)
	    db.close()
        except Exception, e:
            print "Error connecting to database: ", e.pgerror
            sys.exit(1)

    if options.list:
        generator = ListGenerator(options.list)
    elif poly:
        generator = PolyGenerator(poly, range(options.zooms[0], options.zooms[1] + 1))
    else:
        print "Please specify a region for rendering."
        sys.exit()

    render_tiles(generator, options.style, writer, num_threads=options.threads, verbose=options.verbose)
    writer.close()


########NEW FILE########
