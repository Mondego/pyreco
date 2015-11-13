__FILENAME__ = form_station_graph
import networkx as nx
import json

out = {}

G = nx.Graph()

"""
stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station
"""
stops = {}
stop_names = {}
with open('stops.txt') as fh:
    fh.next()
    for line in fh:
        d = line.split(',')
        stop_id = d[0]
        parent_id = d[9].strip()
        location_type = int(d[8])
        stop_name = d[2]
        if location_type == 0:
              stops[stop_id] = parent_id
        else:
            stop_names[stop_id] = stop_name


"""
trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,drop_off_type,shape_dist_traveled
"""
prev_stop_id = None
with open('stop_times.txt') as fh:
    fh.next()
    for line in fh:
        d = line.split(',')
        stop_id = stops.get(d[3], d[3])
        stop_seq = int(d[4])
        if stop_seq != 1:
            G.add_edge(
                stop_names[prev_stop_id], 
                stop_names[stop_id]
            )
        prev_stop_id = stop_id

nodes = G.nodes()

out['nodes'] = [{'name': node} for node in nodes]
out['links'] = [{'source': nodes.index(source), 'target': nodes.index(target)} for source, target in G.edges()]

json.dump(out, open('../viz/data/stations_graph.json','w'))
########NEW FILE########
__FILENAME__ = interarrival_time
import json
import csv
import numpy as np

def time_delta(date1,date2):
    """
    we have to write a tiny little script to calcualte time differences
    it's assumed that date1 is later than date2
    """
    f = lambda d: map(int,d.split(":"))
    h,m,s = (d[0] - d[1] for d in zip(f(date1), f(date2)))
    return h*60*60 + m*60 + s
    
with open('trips.txt') as fh:
    """
    route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id
    """
    reader = csv.reader(fh)
    reader.next()
    trip_id_2_route_id = {}
    for line in reader:
        trip_id_2_route_id[line[2]] = line[0]
       
route_ids = ["C", "G", "1", "F", "L"]

out = dict([(route_id, []) for route_id in route_ids])


with open('stop_times.txt') as fh:
    """
    trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,drop_off_type,shape_dist_traveled
    """
    reader = csv.reader(fh)
    reader.next() 
    stop_times = dict([(rid,{}) for rid in route_ids])
    for line in reader:
        route_id = trip_id_2_route_id[line[0]]
        stop_id = line[3]
        if route_id in stop_times:
            h,m,s = tuple(map(int,line[1].split(":")))
            times = stop_times[route_id].get(stop_id,[])
            times.append(h*60*60 + m*60 + s)
            stop_times[route_id][stop_id] = times
    
out = {}
for route_id, stops in stop_times.items():
    out[route_id] = []
    for stop, times in stops.items():
        deltas = np.diff(np.array(times))
        deltas = [d/60. for d in deltas if d > 0]
        out[route_id].extend(deltas)

out = [
    {
        "route_id": route_id,
        "interarrival_times": times
    }
    for route_id, times in out.items()
]

json.dump(out, open('../viz/data/interarrival_times.json','w'), indent=True)
########NEW FILE########
__FILENAME__ = parse_performance
import xml.dom.minidom
import json
dom = xml.dom.minidom.parse('Performance_MTABUS.xml')
indicators = dom.documentElement.getElementsByTagName('INDICATOR')

pull = {
    'x':'Mean Distance Between Failures - MTA Bus',
    'y':'Collisions with Injury Rate - MTA Bus',
    'c':'Customer Accident Injury Rate - MTA Bus'
}

x = []
y = []
c = []

for indicator in indicators:
    try:
        name = indicator.getElementsByTagName('INDICATOR_NAME')[0].childNodes[0].data
        actual = indicator.getElementsByTagName('MONTHLY_ACTUAL')[0].childNodes[0].data
        actual = float(''.join(actual.split(',')))
    except IndexError:
        actual = None    
    
    if actual == 0.0:
        actual = None
    
    if name == pull['x']:
        x.append(actual)
    elif name == pull['y']:
        y.append(actual)
    elif name == pull['c']:
        c.append(actual)

out = []

for xi,yi,ci in zip(x,y,c):
    if xi is None or yi is None or ci is None:
        continue

    out.append({
        "dist_between_fail": xi,
        "collision_with_injury": yi,
        "customer_accident_rate": ci
    })

json.dump(out, open("../viz/data/bus_perf.json",'w'))

########NEW FILE########
__FILENAME__ = parse_waittime
import xml.dom.minidom
import json
import pandas
import datetime
from operator import itemgetter
import time

# For this example we had to load and parse the NYCT Performance XML file.

# Essentially, we need to parse the XML, pull out the indicators we want, and
# then save them to a JSON which is much easier to play with in javascript.

# For this particular example, we are actually using two JSON files, which will
# be loaded separately. The second JSON is the mean of data in the first, so we
# need only parse the XML once.

# data available at http://www.mta.info/developers/data/Performance_XML_Data.zip

# use the minidom to parse the XML.
dom = xml.dom.minidom.parse('Performance_NYCT.xml')
# pull out all the indicators in the XML
indicators = dom.documentElement.getElementsByTagName('INDICATOR')

# this is a little function that just gets the data out of a particular indicator.
# it just saves us a bit of typing...
def get(indicator, name):
    return indicator.getElementsByTagName(name)[0].childNodes[0].data

# we only want those wait assessments associated with a specific line, so
# we include that extra "-" which doesn't appear in other indicator names
to_pull = 'Subway Wait Assessment -'
# initialise the list that we will dump to a JSON
out = []
for indicator in indicators:
    # if this is the right sort of indicator...
    if to_pull in indicator.getElementsByTagName('INDICATOR_NAME')[0].childNodes[0].data:
        try:
            # we get the name first as we need to use it for display, but reverse 
            # it for the #id
            name = get(indicator, 'INDICATOR_NAME').split('-')[1].strip()
            # we can't use CSS selectors that start with a number! So we gotta
            # make something like line_2 instead of 2_line.
            line_id = name.split(' ')
            line_id.reverse()
            line_id = '_'.join(line_id)
            # the time index here is month and year, which are in separate tags for
            # some reason, making our lives uncessarily complicated
            month = get(indicator, 'PERIOD_MONTH')
            year = get(indicator, 'PERIOD_YEAR')
            # note that the timestamp is in microseconds for javascript
            timestamp = int(time.mktime(
                datetime.datetime.strptime(month+year,"%m%Y").timetuple()
            )) * 1000 
            out.append({
                "line_name": name,
                "line_id": line_id,
                "late_percent": float(get(indicator, 'MONTHLY_ACTUAL')),
                "time": timestamp,
            })
        except IndexError:
            # sometimes a tag is empty, so we just chuck out that month
            pass

# filter out zero entries
out = [
    o for o in out if o['late_percent'] 
    if 'S' not in o['line_name']
    if 'V' not in o['line_name']
    if 'W' not in o['line_name']
]
# dump the data
json.dump(out, open('../viz/data/subway_wait.json','w'))

# compute the mean per line (easy with pandas!)
# build the data frame
df = pandas.DataFrame(out)
# groupby line and take the mean
df_mean = df.groupby('line_name').mean()['late_percent']
# build up the JSON object (one day pandas will have .to_json())
out = [
    {"line_id":'_'.join(reversed(d[0].split(' '))), "line_name":d[0], "mean": d[1]} 
    for d in df_mean.to_dict().items()
]
out.sort(key=itemgetter('line_name'))
# dump the data
json.dump(out, open('../viz/data/subway_wait_mean.json','w'))
########NEW FILE########
__FILENAME__ = plaza_traffic
import pandas
import json
import numpy as np

# import the data into a pandas table
df = pandas.read_csv('TBTA_DAILY_PLAZA_TRAFFIC.csv')

# make a little function that takes the terrible string
# in the CASH and ETC columns and converts them to an int
toint = lambda x: int(x.replace(',',''))

# convert both columns
df['ETC'] = df['ETC'].apply(toint)
df['CASH'] = df['CASH'].apply(toint)

# calculate the mean number of people paying cash
mean_cash = df.groupby("PLAZAID")['CASH'].aggregate(np.mean)
mean_etc = df.groupby("PLAZAID")['ETC'].aggregate(np.mean)

# build the key
key = { 
    1 : "Robert F. Kennedy Bridge Bronx Plaza",
    2 : "Robert F. Kennedy Bridge Manhattan Plaza",
    3 : "Bronx-Whitestone Bridge",
    4 : "Henry Hudson Bridge",
    5 : "Marine Parkway-Gil Hodges Memorial Bridge",
    6 : "Cross Bay Veterans Memorial Bridge",
    7 : "Queens Midtown Tunnel",
    8 : "Brooklyn-Battery Tunnel",
    9 : "Throgs Neck Bridge",
    11 : "Verrazano-Narrows Bridge"
}
# output to JSON we can use in d3
cash =  [
    {"id":d[0], "count":d[1], "name":key[d[0]]} 
    for d in mean_cash.to_dict().items()
]
electronic = [
    {"id":d[0], "count":d[1], "name":key[d[0]]} 
    for d in mean_etc.to_dict().items()
]

out = {
    "cash": cash, 
    "electronic": electronic 
}

json.dump(out, open('../viz/data/plaza_traffic.json', 'w'))

########NEW FILE########
__FILENAME__ = service_status
import json
import xmltodict as xml

# the xml file is available at http://www.mta.info/status/serviceStatus.txt
s = open("code/status.xml").read()
# we convert it to a dictionary
d = xml.xmltodict(s)
# and then dump the subway section into a JSON file to visualise
json.dump(d['subway'][0]['line'], open("../viz/data/service_status.json",'w'))
########NEW FILE########
__FILENAME__ = station_distances
import csv
import numpy as np
import json
import scipy.spatial

with open('stops.txt') as fh:
    reader = csv.reader(fh)
    lats = []
    lons = []
    names = []
    for line in reader:
        if 'Times' in line[2]:
            lats.append(float(line[4]))
            lons.append(float(line[5]))
            names.append(line[0])

positions = np.vstack([lats,lons]).T

D = scipy.spatial.distance_matrix(positions, positions)

out = {
    "matrix": [list(row) for row in D],
    "names": names
}

json.dump(out, open('../viz/data/station_distances.json','w'))
########NEW FILE########
__FILENAME__ = station_locations
import pandas
import json
df = pandas.read_csv('StationEntrances.txt')
df['Latitude'] = df['Latitude'] / 1000000.0
df['Longitude'] = df['Longitude'] / 1000000.0

json.dump(
    [{"lat": lat, "lon": lon, "ada": ada} for lat, lon, ada in zip(df['Latitude'], df['Longitude'], df['ADA'])],    
    open("../viz/data/station_entrances.json",'w')
)
########NEW FILE########
__FILENAME__ = turnstile_traffic
import json
import datetime
import pandas

"""
This is the cleaning code for the turnstile data. 

The turnstile data was strangely hard to parse, and oddly frustrating. This code therefore, should be viewed with caution. Please do report any bugs you find!

"""

def foo(x,audit_type):
    """
    filters out non-REGULAR samples
    """
    return [x for x,a in zip(x,audit_type) if a == "REGULAR"]

def bar(d):
    """
    converts the date bits stored in the text file into ms since the epoch
    """
    return int(datetime.datetime(d[2]+2000, d[0], d[1], d[3], d[4], d[5]).strftime("%s"))*1000

def process_line(line):
    """
    processes a single line of the text file
    """
    data = {}
    audit_type = line[3:][2::5]        
    counts = foo(line[3:][3::5], audit_type)
    counts = [int(c) for c in counts]
    times = foo(line[3:][1::5], audit_type)
    dates = foo(line[3:][0::5], audit_type)
    date_bits = [d.split("-") + t.split(":") for d,t in zip(dates,times)]
    timestamps = [bar([int(di) for di in d]) for d in date_bits]
    for t,c in zip(timestamps, counts):
        data[t] = c
    return data

# these are the locations that correspond to times square and grand central
ts_locns =  ['R145', 'A021','R143','R151','R148','R147']
gc_locns =  ['R236', 'R238','R237','R240','R237B','R241A']

# first we parse the file into some dictionaries
ts_data = {}
gc_data = {}

with open('turnstile_120211.txt') as fh:
    for line in fh:
        line = line.strip().split(',')
        locn = line[0]
        key = '_'.join(line[:3])
        if locn in ts_locns:
            try:
                ts_data[key].update(process_line(line))
            except KeyError:
                ts_data[key] = process_line(line)
        if locn in gc_locns:
            try:
                gc_data[key].update(process_line(line))
            except KeyError:
                gc_data[key] = process_line(line)

# then we go through and extract the times and the counts, discarding points
# that are equal to zero, and are not of a specific length
times_square = {}
ts_times = set()
for key in ts_data:
    d = ts_data[key]
    if len(d) != 42:
        continue
    times_square[key] = [{"time":t, "count":c} for t,c in d.items() if c != 0]
    for ai in times_square[key]:
        ts_times.add(ai['time'])
ts_times = list(ts_times)
ts_times.sort()
ts_columns = []
for i in range(len(times_square)):
    ts_columns.append("ts_%s"%i)

grand_central = {}
gc_times = set()
for key in gc_data:
    d = gc_data[key]
    if len(d) != 43:
        continue
    grand_central[key] = [{"time":t, "count":c} for t,c in d.items() if c != 0]
    for ai in grand_central[key]:
        gc_times.add(ai['time'])
gc_times = list(gc_times)
gc_times.sort()   
gc_columns = []
for i in range(len(grand_central)):
    gc_columns.append("gc_%s"%i)

# build some data frames
ts_df = pandas.DataFrame(index=ts_times, columns=ts_columns)
gc_df = pandas.DataFrame(index=gc_times, columns=gc_columns)

for i,k in enumerate(times_square):
    for ai in times_square[k]:
        ts_df["ts_%s"%i][ai['time']] = ai['count']

for i,k in enumerate(grand_central):
    for ai in grand_central[k]:
        gc_df["gc_%s"%i][ai['time']] = ai['count']

# take the differences between the cumulative counts
ts_df = ts_df.diff()
gc_df = gc_df.diff()

# find their mean
ts = ts_df.mean(1)
gc = gc_df.mean(1)

# kick out any null rows
ts = ts[pandas.notnull(ts)]
gc = gc[pandas.notnull(gc)]

# dump the json
json.dump(
    {
        "times_square": [{"time":t, "count":c} for t,c in zip(ts.index, ts)], 
        "grand_central": [{"time":t, "count":c} for t,c in zip(gc.index, gc)]
    },
    open('../viz/data/turnstile_traffic.json','w')
)



########NEW FILE########
__FILENAME__ = xmltodict
import xml.dom.minidom

def xmltodict(xmlstring):
	doc = xml.dom.minidom.parseString(xmlstring)
	remove_whilespace_nodes(doc.documentElement)
	return elementtodict(doc.documentElement)

def elementtodict(parent):
	child = parent.firstChild
	if (not child):
		return None
	elif (child.nodeType == xml.dom.minidom.Node.TEXT_NODE):
		return child.nodeValue
	
	d={}
	while child is not None:
		if (child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE):
			try:
				d[child.tagName]
			except KeyError:
				d[child.tagName]=[]
			d[child.tagName].append(elementtodict(child))
		child = child.nextSibling
	return d

def remove_whilespace_nodes(node, unlink=True):
	remove_list = []
	for child in node.childNodes:
		if child.nodeType == xml.dom.Node.TEXT_NODE and not child.data.strip():
			remove_list.append(child)
		elif child.hasChildNodes():
			remove_whilespace_nodes(child, unlink)
	for node in remove_list:
		node.parentNode.removeChild(node)
		if unlink:
			node.unlink()
########NEW FILE########
