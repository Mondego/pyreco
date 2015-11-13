__FILENAME__ = dbfUtils
import struct, datetime, decimal, itertools

def dbfreader(f):
    """Returns an iterator over records in a Xbase DBF file.

    The first row returned contains the field names.
    The second row contains field specs: (type, size, decimal places).
    Subsequent rows contain the data records.
    If a record is marked as deleted, it is skipped.

    File should be opened for binary reads.

    """
    # See DBF format spec at:
    #     http://www.pgts.com.au/download/public/xbase.htm#DBF_STRUCT

    numrec, lenheader = struct.unpack('<xxxxLH22x', f.read(32))    
    numfields = (lenheader - 33) // 32

    fields = []
    for fieldno in xrange(numfields):
        name, typ, size, deci = struct.unpack('<11sc4xBB14x', f.read(32))
        name = name.replace('\0', '')       # eliminate NULs from string   
        fields.append((name, typ, size, deci))
    yield [field[0] for field in fields]
    yield [tuple(field[1:]) for field in fields]

    terminator = f.read(1)
    assert terminator == '\r'

    fields.insert(0, ('DeletionFlag', 'C', 1, 0))
    fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in fields])
    fmtsiz = struct.calcsize(fmt)
    for i in xrange(numrec):
        record = struct.unpack(fmt, f.read(fmtsiz))
        if record[0] != ' ':
            continue                        # deleted record
        result = []
        for (name, typ, size, deci), value in itertools.izip(fields, record):
            if name == 'DeletionFlag':
                continue
            if typ == "N":
                value = value.replace('\0', '').lstrip()
                if value == '':
                    value = 0
                elif deci:
                    value = decimal.Decimal(value)
                else:
                    value = int(value)
            elif typ == 'D':
                y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                value = datetime.date(y, m, d)
            elif typ == 'L':
                value = (value in 'YyTt' and 'T') or (value in 'NnFf' and 'F') or '?'
            result.append(value)
        yield result


def dbfwriter(f, fieldnames, fieldspecs, records):
    """ Return a string suitable for writing directly to a binary dbf file.

    File f should be open for writing in a binary mode.

    Fieldnames should be no longer than ten characters and not include \x00.
    Fieldspecs are in the form (type, size, deci) where
        type is one of:
            C for ascii character data
            M for ascii character memo data (real memo fields not supported)
            D for datetime objects
            N for ints or decimal objects
            L for logical values 'T', 'F', or '?'
        size is the field width
        deci is the number of decimal places in the provided decimal object
    Records can be an iterable over the records (sequences of field values).
    
    """
    # header info
    ver = 3
    now = datetime.datetime.now()
    yr, mon, day = now.year-1900, now.month, now.day
    numrec = len(records)
    numfields = len(fieldspecs)
    lenheader = numfields * 32 + 33
    lenrecord = sum(field[1] for field in fieldspecs) + 1
    hdr = struct.pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
    f.write(hdr)
                      
    # field specs
    for name, (typ, size, deci) in itertools.izip(fieldnames, fieldspecs):
        name = name.ljust(11, '\x00')
        fld = struct.pack('<11sc4xBB14x', name, typ, size, deci)
        f.write(fld)

    # terminator
    f.write('\r')

    # records
    for record in records:
        f.write(' ')                        # deletion flag
        for (typ, size, deci), value in itertools.izip(fieldspecs, record):
            if typ == "N":
                value = str(value).rjust(size, ' ')
            elif typ == 'D':
                value = value.strftime('%Y%m%d')
            elif typ == 'L':
                value = str(value)[0].upper()
            else:
                value = str(value)[:size].ljust(size, ' ')
            assert len(value) == size
            f.write(value)

    # End of file
    f.write('\x1A')

########NEW FILE########
__FILENAME__ = gen_json
import datetime
import os
import re
import pytz
import shpUtils
import simplejson
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
import time
import sys

def collate_zones(shape_file):
    # First collate the polygons by zone name
    print "Loading SHP file..."
    rows = shpUtils.loadShapefile(shape_file)
    collated = {}
    for row in rows:
        name = row["dbf_data"]["TZID"].strip()
        if name == "uninhabited":
            continue

        sys.stderr.write("Processing row for '%s'\n" % name)
        collated[name] = collated.get(name, [])
        for p in row["shp_data"]["parts"]:
            collated[name].append({
                "points": p["points"],
            })

    # Then add some information and try to simplify/reduce the polygons
    zones = {}
    collation_now = time.time()
    for name, shp_data in collated.iteritems():
        sys.stderr.write("Simpifying %s\n" % name)
        transition_info = []
        tz = pytz.timezone(name)
        if "_utc_transition_times" in dir(tz):
            last_info = [sys.maxint, 0, '']
            for i, transition_time in enumerate(tz._utc_transition_times):
                transition_time = int(time.mktime(transition_time.timetuple()))
                td = tz._transition_info[i][0]
                info = [
                    transition_time,
                    timedelta_to_minutes(td),
                    tz._transition_info[i][2]
                ]

                if transition_time < collation_now:
                    last_info = info
                    continue

                # Include the last timezone prior to now
                if last_info[0] < collation_now:
                    transition_info.append(last_info)

                transition_info.append(info)
                last_info = info

        if len(transition_info) == 0:
            # Assume no daylight savings
            now = datetime.datetime.now()
            td = tz.utcoffset(now)
            transition_info.append([0, timedelta_to_minutes(td),
                                     tz.tzname(now)])


        # calculate a collation key based on future timezone transitions
        collation_key = ''
        for t in transition_info:
            if t[0] >= collation_now:
                collation_key += "%d>%d," % (t[0], t[1])

        # for non-daylight savings regions, just use the utc_offset
        if len(collation_key) == 0:
            collation_key = "0>%d" % transition_info[-1][1]

        zones[collation_key] = zones.get(collation_key, {
            "bounding_box": {
                "xmin": sys.maxint,
                "ymin": sys.maxint,
                "xmax":-sys.maxint - 1,
                "ymax":-sys.maxint - 1
            },
            "polygons": [],
            "transitions": {},
            "name": name
        })

        zones[collation_key]["transitions"][name] = transition_info

        polygons = reduce_polygons(shp_data, 0.1, 0.01, 4, 5000, 0, 0.05)

        for part in polygons:
            polygonInfo = simplify(part["points"])
            polygonInfo["name"] = name
            zones[collation_key]["polygons"].append(polygonInfo)

            b = zones[collation_key]["bounding_box"]
            b["xmin"] = min(b["xmin"], polygonInfo["bounds"][0])
            b["ymin"] = min(b["ymin"], polygonInfo["bounds"][1])
            b["xmax"] = max(b["xmax"], polygonInfo["bounds"][2])
            b["ymax"] = max(b["ymax"], polygonInfo["bounds"][3])
            del polygonInfo["bounds"]

    return zones

def convert_points(polygons):
    # Convert {x,y} to [lat,lng], for more compact JSON
    for polygon in polygons:
        polygon["points"] = reduce(lambda x, y: x + [y["y"], y["x"]],
                                   polygon["points"], [])
    return polygons

def reduce_json(jsonString, maxPrecision=6):
    reduced_precision = re.sub(
        r'(\d)\.(\d{' + str(maxPrecision) + r'})(\d+)', r'\1.\2',
        jsonString
    )

    return re.sub(r'\s', '', reduced_precision)

def reduce_polygons(polygonData, hullAreaThreshold, bufferDistance,
                   bufferResolution, numThreshold, areaThreshold,
                   simplifyThreshold):
    polygons = []
    for p in polygonData:
        polygon = Polygon(map(lambda x: (x["x"], x["y"]),
                              p["points"]))

        # For very small regions, use a convex hull
        if polygon.area < hullAreaThreshold:
            polygon = polygon.convex_hull
        # Also buffer by a small distance to aid the cascaded union
        polygon = polygon.buffer(bufferDistance, bufferResolution)

        polygons.append(polygon)

    # Try to merge some polygons
    polygons = cascaded_union(polygons)

    # Normalize the Polygon or MultiPolygon into an array
    if "exterior" in dir(polygons):
        polygons = [polygons]
    else:
        polygons = [p for p in polygons]

    region = []
    # Sort from largest to smallest to faciliate dropping of small regions
    polygons.sort(key=lambda x:-x.area)
    for p in polygons:
        # Try to include regions that are big enough, once we have a
        # few representative regions
        if len(region) > numThreshold and p.area < areaThreshold:
            break

        p = p.simplify(simplifyThreshold)
        region.append({
            "points": map(lambda x: {"x": x[0], "y": x[1]},
                          p.exterior.coords)
        })

    return region

def simplify(points):
    polygon = Polygon(map(lambda x: (x["x"], x["y"]), points))
    polygon = polygon.simplify(0.05)

    return {
        "points": map(lambda x: {"x": x[0], "y": x[1]},
            polygon.exterior.coords),
        "centroid": (polygon.centroid.x, polygon.centroid.y),
        "bounds": polygon.bounds,
        "area": polygon.area
    }

def timedelta_to_minutes(td):
    return td.days * 24 * 60 + td.seconds / 60

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage: python gen_json.py <shape_file> <output_dir>'
        sys.exit(1)

    zones = collate_zones(sys.argv[1])
    boxes = []
    hovers = []

    output_dir = sys.argv[2]
    os.mkdir(os.path.join(output_dir, "polygons"))
    for key, zone in zones.iteritems():
        # calculate a hover region
        sys.stderr.write('Calculating hover region for %s\n' % zone["name"])
        hover_region = reduce_polygons(zone["polygons"], 1, 0.1, 4, 3, 0.5,
                                       0.05)

        # Merge transitions information for all contained timezones
        hoverTransitions = []
        zone_transitions = zone["transitions"].values()
        for i, transition in enumerate(zone_transitions[0]):
            tzNames = {}
            for zone_transition in zone_transitions:
                tzNames[zone_transition[i][2]] = tzNames.get(
                    zone_transition[i][2], 0) + 1

            hoverTransitions.append([
                transition[0],
                transition[1],
                map(lambda x: x[0],
                    sorted(tzNames.iteritems(), key=lambda x:-x[1]))
            ])

        hovers.append({
            "name": zone["name"],
            "hoverRegion": convert_points(hover_region),
            "transitions": hoverTransitions
        })

        # Get a centroid for the largest polygon in each zone
        zone_centroids = {}
        for polygon in zone["polygons"]:
            zone_centroid = zone_centroids.get(polygon["name"], {
                "centroid": (0, 0),
                "area": 0
            })

            if polygon["area"] > zone_centroid["area"]:
                zone_centroids[polygon["name"]] = {
                    "centroid": polygon["centroid"],
                    "area": polygon["area"]
                }

            # Don't need this anymore, so purge it to save some JSON space
            del polygon["area"]

        boxes.append({
            "name": zone["name"],
            "boundingBox": zone["bounding_box"],
            "zoneCentroids": dict(map(
                lambda x: (x[0], x[1]["centroid"]), zone_centroids.iteritems()
            ))
        })

        filename = re.sub(r'[^a-z0-9]+', '-', zone["name"].lower())
        out_file = os.path.join(output_dir, "polygons", "%s.json" % filename)
        open(out_file, "w").write(
            reduce_json(simplejson.dumps({
                "name": zone["name"],
                "polygons": convert_points(zone["polygons"]),
                "transitions": zone["transitions"]
            }), 5))

    open(os.path.join(output_dir, "bounding_boxes.json"), "w").write(
        reduce_json(simplejson.dumps(boxes), 2)
    )
    open(os.path.join(output_dir, "hover_regions.json"), "w").write(
        reduce_json(simplejson.dumps(hovers), 2)
    )

########NEW FILE########
__FILENAME__ = shpUtils
from struct import unpack
import dbfUtils, math
XY_POINT_RECORD_LENGTH = 16
db = []

def loadShapefile(file_name):
        global db
        shp_bounding_box = []
        shp_type = 0
        file_name = file_name
        records = []
        # open dbf file and get records as a list
        dbf_file = file_name[0:-4] + '.dbf'
        dbf = open(dbf_file, 'rb')
        db = list(dbfUtils.dbfreader(dbf))
        dbf.close()
        fp = open(file_name, 'rb')
        
        # get basic shapefile configuration
        fp.seek(32)
        shp_type = readAndUnpack('i', fp.read(4))                
        shp_bounding_box = readBoundingBox(fp)
        
        # fetch Records
        fp.seek(100)
        while True:
                shp_record = createRecord(fp)
                if shp_record == False:
                        break
                records.append(shp_record)
        
        return records    

record_class = {0:'RecordNull', 1:'RecordPoint', 8:'RecordMultiPoint', 3:'RecordPolyLine', 5:'RecordPolygon'}

def createRecord(fp):
        # read header
        record_number = readAndUnpack('>L', fp.read(4))
        if record_number == '':
                print 'doner'
                return False
        content_length = readAndUnpack('>L', fp.read(4))
        record_shape_type = readAndUnpack('<L', fp.read(4))

        shp_data = readRecordAny(fp,record_shape_type)
        dbf_data = {}
        for i in range(0,len(db[record_number+1])):
                dbf_data[db[0][i]] = db[record_number+1][i]
        
        return {'shp_data':shp_data, 'dbf_data':dbf_data}       
        
# Reading defs

def readRecordAny(fp, type):
        if type==0:
                return readRecordNull(fp)
        elif type==1:
                return readRecordPoint(fp)
        elif type==8:
                return readRecordMultiPoint(fp)
        elif type==3 or type==5:
                return readRecordPolyLine(fp)
        else:
                return False

def readRecordNull(fp):
        data = {}
        return data

point_count = 0
def readRecordPoint(fp):
        global point_count
        data = {}
        data['x'] = readAndUnpack('d', fp.read(8))
        data['y'] = readAndUnpack('d', fp.read(8))
        point_count += 1
        return data

    
def readRecordMultiPoint(fp):
        data = readBoundingBox(fp)
        data['numpoints'] = readAndUnpack('i', fp.read(4))        
        for i in range(0,data['numpoints']):
                data['points'].append(readRecordPoint(fp))
        return data

    
def readRecordPolyLine(fp):
        data = readBoundingBox(fp)
        data['numparts']  = readAndUnpack('i', fp.read(4))
        data['numpoints'] = readAndUnpack('i', fp.read(4))
        data['parts'] = []
        for i in range(0, data['numparts']):
                data['parts'].append(readAndUnpack('i', fp.read(4)))
        points_initial_index = fp.tell()
        points_read = 0
        for part_index in range(0, data['numparts']):
                point_index = data['parts'][part_index]
                
                # if(!isset(data['parts'][part_index]['points']) or !is_array(data['parts'][part_index]['points'])):
                data['parts'][part_index] = {}
                data['parts'][part_index]['points'] = []
                
                # while( ! in_array( points_read, data['parts']) and points_read < data['numpoints'] and !feof(fp)):
                checkPoint = []
                while (points_read < data['numpoints']):
                        currPoint = readRecordPoint(fp)
                        data['parts'][part_index]['points'].append(currPoint)
                        points_read += 1
                        if points_read == 0 or checkPoint == []:
                                checkPoint = currPoint
                        elif currPoint == checkPoint:
                                checkPoint = []
                                break
                        
        fp.seek(points_initial_index + (points_read * XY_POINT_RECORD_LENGTH))
        return data

# General defs
    
def readBoundingBox(fp):
        data = {}
        data['xmin'] = readAndUnpack('d',fp.read(8))
        data['ymin'] = readAndUnpack('d',fp.read(8))
        data['xmax'] = readAndUnpack('d',fp.read(8))
        data['ymax'] = readAndUnpack('d',fp.read(8))
        return data

def readAndUnpack(type, data):
        if data=='': return data
        return unpack(type, data)[0]


####
#### additional functions
####

def getCentroids(records, projected=False):
        # for each feature
        if projected:
                points = 'projectedPoints'
        else:
                points = 'points'
                
        for feature in records:
                numpoints = cx = cy = 0
                for part in feature['shp_data']['parts']:
                        for point in part[points]:
                                numpoints += 1
                                cx += point['x']
                                cy += point['y']
                cx /= numpoints
                cy /= numpoints
                feature['shp_data']['centroid'] = {'x':cx, 'y':cy}
                                
                
def getBoundCenters(records):
        for feature in records:
                cx = .5 * (feature['shp_data']['xmax']-feature['shp_data']['xmin']) + feature['shp_data']['xmin']
                cy = .5 * (feature['shp_data']['ymax']-feature['shp_data']['ymin']) + feature['shp_data']['ymin']
                feature['shp_data']['boundCenter'] = {'x':cx, 'y':cy}
        
def getTrueCenters(records, projected=False):
        #gets the true polygonal centroid for each feature (uses largest ring)
        #should be spherical, but isn't

        if projected:
                points = 'projectedPoints'
        else:
                points = 'points'
                
        for feature in records:
                maxarea = 0
                for ring in feature['shp_data']['parts']:
                        ringArea = getArea(ring, points)
                        if ringArea > maxarea:
                                maxarea = ringArea
                                biggest = ring
                #now get the true centroid
                tempPoint = {'x':0, 'y':0}
                if biggest[points][0] != biggest[points][len(biggest[points])-1]:
                        print "mug", biggest[points][0], biggest[points][len(biggest[points])-1]
                for i in range(0, len(biggest[points])-1):
                        j = (i + 1) % (len(biggest[points])-1)
                        tempPoint['x'] -= (biggest[points][i]['x'] + biggest[points][j]['x']) * ((biggest[points][i]['x'] * biggest[points][j]['y']) - (biggest[points][j]['x'] * biggest[points][i]['y']))
                        tempPoint['y'] -= (biggest[points][i]['y'] + biggest[points][j]['y']) * ((biggest[points][i]['x'] * biggest[points][j]['y']) - (biggest[points][j]['x'] * biggest[points][i]['y']))
                        
                tempPoint['x'] = tempPoint['x'] / ((6) * maxarea)
                tempPoint['y'] = tempPoint['y'] / ((6) * maxarea)
                feature['shp_data']['truecentroid'] = tempPoint
                

def getArea(ring, points):
        #returns the area of a polygon
        #needs to be spherical area, but isn't
        area = 0
        for i in range(0,len(ring[points])-1):
                j = (i + 1) % (len(ring[points])-1)
                area += ring[points][i]['x'] * ring[points][j]['y']
                area -= ring[points][i]['y'] * ring[points][j]['x']
                        
        return math.fabs(area/2)
        

def getNeighbors(records):
        
        #for each feature
        for i in range(len(records)):
                #print i, records[i]['dbf_data']['ADMIN_NAME']
                if not 'neighbors' in records[i]['shp_data']:
                        records[i]['shp_data']['neighbors'] = []
                
                #for each other feature
                for j in range(i+1, len(records)):
                        numcommon = 0
                        #first check to see if the bounding boxes overlap
                        if overlap(records[i], records[j]):
                                #if so, check every single point in this feature to see if it matches a point in the other feature
                                
                                #for each part:
                                for part in records[i]['shp_data']['parts']:
                                        
                                        #for each point:
                                        for point in part['points']:
                                                
                                                for otherPart in records[j]['shp_data']['parts']:
                                                        if point in otherPart['points']:
                                                                numcommon += 1
                                                                if numcommon == 2:
                                                                        if not 'neighbors' in records[j]['shp_data']:
                                                                                records[j]['shp_data']['neighbors'] = []
                                                                        records[i]['shp_data']['neighbors'].append(j)
                                                                        records[j]['shp_data']['neighbors'].append(i)
                                                                        #now break out to the next j
                                                                        break
                                                if numcommon == 2:
                                                        break
                                        if numcommon == 2:
                                                break
                                
                                                                        
                                                                
                                                                
def projectShapefile(records, whatProjection, lonCenter=0, latCenter=0):
        print 'projecting to ', whatProjection
        for feature in records:
                for part in feature['shp_data']['parts']:
                        part['projectedPoints'] = []
                        for point in part['points']:
                                tempPoint = projectPoint(point, whatProjection, lonCenter, latCenter)
                                part['projectedPoints'].append(tempPoint)

def projectPoint(fromPoint, whatProjection, lonCenter, latCenter):
        latRadians = fromPoint['y'] * math.pi/180
        if latRadians > 1.5: latRadians = 1.5
        if latRadians < -1.5: latRadians = -1.5
        lonRadians = fromPoint['x'] * math.pi/180
        lonCenter = lonCenter * math.pi/180
        latCenter = latCenter * math.pi/180
        newPoint = {}
        if whatProjection == "MERCATOR":
                newPoint['x'] = (180/math.pi) * (lonRadians - lonCenter)
                newPoint['y'] = (180/math.pi) * math.log(math.tan(latRadians) + (1/math.cos(latRadians)))
                if newPoint['y'] > 200:
                        newPoint['y'] = 200
                if newPoint['y'] < -200:
                        newPoint['y'] = 200
                return newPoint
        if whatProjection == "EQUALAREA":
                newPoint['x'] = 0
                newPoint['y'] = 0
                return newPoint
                

def overlap(feature1, feature2):
        if (feature1['shp_data']['xmax'] > feature2['shp_data']['xmin'] and feature1['shp_data']['ymax'] > feature2['shp_data']['ymin'] and feature1['shp_data']['xmin'] < feature2['shp_data']['xmax'] and feature1['shp_data']['ymin'] < feature2['shp_data']['ymax']):
                return True
        else:
                return False

########NEW FILE########
